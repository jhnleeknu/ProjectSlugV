#!/usr/bin/env python3
"""Verify and assemble encrypted mslug5 regions; no decryption is performed.

Program assembly explicitly preserves each source two-byte word and alternates
p1 and p2 words. The correspondence to MAME loader semantics is verified
separately; this module never infers CPU instruction meaning from those bytes.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

try:
    from tools import inspect_rom
except ModuleNotFoundError:
    import inspect_rom


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PROJECT_ROOT / "config/mslug5_mame.json"


def assemble_program_le(p1, p2):
    """Alternate unswapped 16-bit words: p1[0:2], p2[0:2], p1[2:4], ..."""
    if len(p1) != len(p2) or len(p1) % 2:
        raise ValueError("program inputs must have equal, even lengths")
    result = bytearray(len(p1) + len(p2))
    result[0::4] = p1[0::2]
    result[1::4] = p1[1::2]
    result[2::4] = p2[0::2]
    result[3::4] = p2[1::2]
    return bytes(result)


def swap_words(data):
    """Swap the two bytes of each word; reject a trailing partial word."""
    if len(data) % 2:
        raise ValueError("word swapping requires an even length")
    result = bytearray(len(data))
    result[0::2] = data[1::2]
    result[1::2] = data[0::2]
    return bytes(result)


def interleave_bytes(a, b):
    """Alternate bytes from equally sized inputs, beginning with a."""
    if len(a) != len(b):
        raise ValueError("byte interleave inputs must have equal lengths")
    result = bytearray(len(a) + len(b))
    result[0::2] = a
    result[1::2] = b
    return bytes(result)


def _checked_output(output_dir, archive_path):
    directory = Path(output_dir).resolve()
    extracted = PROJECT_ROOT.resolve() / "extracted"
    # Resolve both sides to detect a symlink redirecting extracted outside the
    # project. A resolved child must remain under the literal project path.
    if directory == extracted or extracted not in directory.parents:
        raise ValueError("output directory must be strictly under project extracted/")
    names = ("maincpu.encrypted.le.bin", "sprites.encrypted.bin",
             "audiocrypt.encrypted.bin", "adpcma.encrypted.bin", "manifest.json")
    for name in names:
        destination = directory / name
        if destination.is_symlink() or destination.resolve() == archive_path.resolve():
            raise ValueError("output must not follow symlinks or overwrite the archive")
        if destination.exists() and destination.stat().st_nlink > 1:
            raise ValueError("output must not overwrite a hard-linked file")
    return directory


def _source(name, offset, group_size=1, stride=1):
    return {"name": name, "source_offset": 0, "region_offset": offset,
            "group_size": group_size, "stride": stride, "swap_bytes": False}


def assemble_regions(zip_path, output_dir):
    """Validate the whole archive before creating any assembled output.

    Each source mapping copies group_size consecutive bytes, then advances
    the output by stride bytes. Input offsets are ZIP-member byte offsets;
    region offsets describe storage bytes, not CPU addresses.
    """
    archive_path = Path(zip_path)
    directory = _checked_output(output_dir, archive_path)
    report = inspect_rom.inspect_archive(archive_path, REFERENCE_PATH)
    if not report["ok"]:
        raise ValueError("ROM archive failed reference validation; no output written")
    source_hashes = {entry["name"]: entry["actual"] for entry in report["files"]}
    manifest = {"schema_version": 1, "set": "mslug5", "encrypted": True,
                "archive": report["archive"], "reference": report["reference"],
                "regions": []}
    with zipfile.ZipFile(archive_path, "r") as archive:
        program = assemble_program_le(archive.read("268-p1cr.p1"), archive.read("268-p2cr.p2"))
        sprites = bytearray()
        sprite_sources = []
        for index in range(1, 9, 2):
            first = "268-c%dc.c%d" % (index, index)
            second = "268-c%dc.c%d" % (index + 1, index + 1)
            offset = len(sprites)
            sprites.extend(interleave_bytes(archive.read(first), archive.read(second)))
            sprite_sources.extend((_source(first, offset, 1, 2),
                                   _source(second, offset + 1, 1, 2)))
        regions = [
            ("maincpu", "maincpu.encrypted.le.bin", program, 8 * 1024 * 1024,
             "little-endian-16", [_source("268-p1cr.p1", 0, 2, 4),
                                  _source("268-p2cr.p2", 2, 2, 4)]),
            ("sprites", "sprites.encrypted.bin", sprites, 64 * 1024 * 1024,
             "byte-stream", sprite_sources),
            ("audiocrypt", "audiocrypt.encrypted.bin", archive.read("268-m1.m1"),
             512 * 1024, "byte-stream", [_source("268-m1.m1", 0)]),
            ("adpcma", "adpcma.encrypted.bin",
             archive.read("268-v1c.v1") + archive.read("268-v2c.v2"),
             16 * 1024 * 1024, "byte-stream",
             [_source("268-v1c.v1", 0), _source("268-v2c.v2", 8 * 1024 * 1024)]),
        ]
    for region, filename, data, size, byte_order, sources in regions:
        if len(data) != size:
            raise ValueError("unexpected assembled region size: " + region)
        for source in sources:
            source.update(source_hashes[source["name"]])
        manifest["regions"].append({"name": region, "file": filename,
                                    "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                    "byte_order": byte_order, "sources": sources})
    directory.mkdir(parents=True, exist_ok=True)
    for region, filename, data, size, byte_order, sources in regions:
        (directory / filename).write_bytes(data)
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=Path("mslug5.zip"))
    parser.add_argument("--output", type=Path, default=Path("extracted/regions"))
    args = parser.parse_args(argv)
    try:
        assemble_regions(args.archive, args.output)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, KeyError) as error:
        print("assemble_regions: " + str(error), file=sys.stderr)
        return 1
    print("Encrypted ROM regions assembled: " + str(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
