"""Synthetic fixtures only: no game data is needed for these checks."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile
import zlib


SCRIPT = Path(__file__).resolve().parents[1] / "inspect_rom.py"
SPEC = importlib.util.spec_from_file_location("inspect_rom", SCRIPT)
inspect_rom = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect_rom)


class InspectRomTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.archive = self.directory / "mslug5.zip"
        self.reference = self.directory / "reference.json"
        self.output = self.directory / "inventory.json"
        self.payload = b"synthetic ROM data\x00\xff"
        self.expected = {
            "name": "test-p1.bin",
            "size": len(self.payload),
            "crc32": "%08x" % (zlib.crc32(self.payload) & 0xffffffff),
            "sha1": hashlib.sha1(self.payload).hexdigest(),
            "region": "maincpu",
        }

    def write_fixture(self, entries=None, expected=None):
        if entries is None:
            entries = [(self.expected["name"], self.payload)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_STORED) as archive:
                for name, payload in entries:
                    archive.writestr(name, payload)
        manifest = {
            "schema_version": 1,
            "set": "mslug5",
            "source": {"type": "synthetic fixture"},
            "files": [expected if expected is not None else self.expected],
        }
        self.reference.write_text(json.dumps(manifest), encoding="utf-8")

    def run_cli(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = inspect_rom.main([
                str(self.archive), "--reference", str(self.reference),
                "--output", str(self.output),
            ])
        return code, json.loads(self.output.read_text(encoding="utf-8"))

    def test_matching_and_deterministic_report_preserves_archive(self):
        self.write_fixture()
        original = self.archive.read_bytes()
        code, report = self.run_cli()
        first = self.output.read_bytes()
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["archive"]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(report["files"][0]["actual"]["sha256"], hashlib.sha256(self.payload).hexdigest())
        self.run_cli()
        self.assertEqual(first, self.output.read_bytes())
        self.assertEqual(original, self.archive.read_bytes())

    def test_each_required_hash_and_size_mismatch(self):
        for key, bad in (("size", 0), ("crc32", "00000000"), ("sha1", "0" * 40)):
            with self.subTest(key=key):
                expected = dict(self.expected)
                expected[key] = bad
                self.write_fixture(expected=expected)
                code, report = self.run_cli()
                self.assertEqual(code, 1)
                self.assertFalse(report["files"][0]["comparison"][key])

    def test_optional_sha256_is_compared(self):
        expected = dict(self.expected, sha256="0" * 64)
        self.write_fixture(expected=expected)
        code, report = self.run_cli()
        self.assertEqual(code, 1)
        self.assertFalse(report["files"][0]["comparison"]["sha256"])
        expected["sha256"] = hashlib.sha256(self.payload).hexdigest()
        self.write_fixture(expected=expected)
        self.assertEqual(self.run_cli()[0], 0)

    def test_missing(self):
        self.write_fixture(entries=[])
        code, report = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(report["missing"], [self.expected["name"]])

    def test_extra(self):
        self.write_fixture(entries=[(self.expected["name"], self.payload), ("extra.bin", b"extra")])
        code, report = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(report["extra"], ["extra.bin"])
        self.assertIsNone(report["files"][0]["expected"])

    def test_duplicate_names_are_not_collapsed(self):
        self.write_fixture(entries=[(self.expected["name"], self.payload)] * 2)
        code, report = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(report["duplicates"], [self.expected["name"]])
        self.assertEqual(len(report["files"]), 2)
        self.assertTrue(all(not entry["ok"] for entry in report["files"]))

    def test_corrupt_decompressed_entry(self):
        self.write_fixture()
        data = self.archive.read_bytes()
        self.assertEqual(data.count(self.payload), 1)
        self.archive.write_bytes(data.replace(self.payload, b"X" + self.payload[1:]))
        code, report = self.run_cli()
        self.assertEqual(code, 1)
        self.assertTrue(report["files"][0]["errors"])

    def test_invalid_archive_reports_failure(self):
        self.write_fixture()
        self.archive.write_bytes(b"not a zip archive")
        code, report = self.run_cli()
        self.assertEqual(code, 1)
        self.assertTrue(report["errors"])

    def test_output_cannot_overwrite_archive(self):
        self.write_fixture()
        original = self.archive.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            inspect_rom.main([str(self.archive), "--reference", str(self.reference),
                              "--output", str(self.archive)])
        self.assertEqual(original, self.archive.read_bytes())


if __name__ == "__main__":
    unittest.main()
