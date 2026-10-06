#!/usr/bin/env python3
"""Inventory a ZIP ROM set without extracting or modifying its contents.

Size, CRC32 and SHA1 are required in the reference; SHA256 is compared when
provided, and is always computed for both the archive and decompressed files.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import zlib


CHUNK_SIZE = 1024 * 1024


def hash_stream(stream):
    size = 0
    crc32 = 0
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        crc32 = zlib.crc32(chunk, crc32)
        sha1.update(chunk)
        sha256.update(chunk)
    return {
        "size": size,
        "crc32": "%08x" % (crc32 & 0xffffffff),
        "sha1": sha1.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def load_reference(path):
    with path.open("r", encoding="utf-8") as stream:
        reference = json.load(stream)
    if not isinstance(reference, dict) or reference.get("schema_version") != 1:
        raise ValueError("reference must have schema_version 1")
    if reference.get("set") != "mslug5":
        raise ValueError("reference set must be mslug5")
    if not isinstance(reference.get("files"), list):
        raise ValueError("reference files must be a list")
    expected = {}
    for entry in reference["files"]:
        if not isinstance(entry, dict):
            raise ValueError("reference file entry must be an object")
        name = entry.get("name")
        if not isinstance(name, str) or not name or name in expected:
            raise ValueError("reference file names must be nonempty and unique")
        size = entry.get("size")
        if type(size) is not int or size < 0:
            raise ValueError("reference size must be a nonnegative integer: " + name)
        normalized = {"name": name, "size": size, "region": entry.get("region")}
        for key, width in (("crc32", 8), ("sha1", 40), ("sha256", 64)):
            if key == "sha256" and key not in entry:
                continue
            value = entry.get(key)
            if (not isinstance(value, str) or len(value) != width
                    or any(char not in "0123456789abcdefABCDEF" for char in value)):
                raise ValueError("invalid reference " + key + ": " + name)
            normalized[key] = value.lower()
        expected[name] = normalized
    return reference, expected


def inspect_archive(archive_path, reference_path):
    reference, expected = load_reference(reference_path)
    report = {
        "schema_version": 1,
        "set": reference["set"],
        "archive": {"path": str(archive_path), "sha256": None},
        "reference": {"path": str(reference_path), "source": reference.get("source", {})},
        "files": [],
        "missing": [],
        "extra": [],
        "duplicates": [],
        "errors": [],
        "ok": False,
    }
    seen = set()
    try:
        with archive_path.open("rb") as stream:
            report["archive"]["sha256"] = hash_stream(stream)["sha256"]
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = archive.infolist()
            counts = {}
            for entry in entries:
                counts[entry.filename] = counts.get(entry.filename, 0) + 1
            report["duplicates"] = sorted(name for name in counts if counts[name] > 1)
            # Stable sorting preserves the archive order of duplicate entries.
            for entry in sorted(entries, key=lambda item: item.filename):
                name = entry.filename
                seen.add(name)
                target = expected.get(name)
                result = {
                    "name": name,
                    "region": target.get("region") if target else None,
                    "actual": None,
                    "expected": target,
                    "comparison": {},
                    "zip_crc32": "%08x" % entry.CRC,
                    "errors": [],
                    "ok": False,
                }
                try:
                    with archive.open(entry, "r") as stream:
                        actual = hash_stream(stream)
                    result["actual"] = actual
                    result["comparison"]["zip_crc32"] = actual["crc32"] == result["zip_crc32"]
                    result["comparison"]["zip_size"] = actual["size"] == entry.file_size
                    if target:
                        for key in ("size", "crc32", "sha1", "sha256"):
                            if key in target:
                                result["comparison"][key] = actual[key] == target[key]
                    result["ok"] = (target is not None and counts[name] == 1
                                    and all(result["comparison"].values()))
                except (OSError, EOFError, RuntimeError, NotImplementedError,
                        zipfile.BadZipFile, zlib.error) as error:
                    result["errors"].append(type(error).__name__ + ": " + str(error))
                report["files"].append(result)
    except (OSError, EOFError, RuntimeError, NotImplementedError,
            zipfile.BadZipFile, zlib.error) as error:
        report["errors"].append(type(error).__name__ + ": " + str(error))
    report["missing"] = sorted(set(expected) - seen)
    report["extra"] = sorted(seen - set(expected))
    report["ok"] = (not report["errors"] and not report["missing"]
                    and not report["extra"] and not report["duplicates"]
                    and all(entry["ok"] for entry in report["files"]))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=Path("mslug5.zip"))
    parser.add_argument("--reference", type=Path, default=Path("config/mslug5_mame.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/rom_inventory.json"))
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.archive.resolve(), args.reference.resolve()):
        parser.error("output must not overwrite the archive or reference")
    try:
        report = inspect_archive(args.archive, args.reference)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    except (OSError, ValueError) as error:
        print("inspect_rom: " + str(error), file=sys.stderr)
        return 2
    print("ROM inventory %s: %s" % ("verified" if report["ok"] else "failed", args.output))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
