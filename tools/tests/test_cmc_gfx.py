"""Synthetic CMC50 checks; full-image C++ differential check is separate."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cmc_tables
import decrypt_cmc_gfx


class SizedInput:
    """Check size rejection without allocating near-64 MiB invalid inputs."""
    def __init__(self, size):
        self.size = size

    def __len__(self):
        return self.size


class CmcGfxTests(unittest.TestCase):
    def test_rejects_invalid_sizes(self):
        for size in (0, 1, 0x4000000 - 1, 0x4000000 + 1):
            for function in (decrypt_cmc_gfx.decrypt_graphics, decrypt_cmc_gfx.extract_fixed):
                with self.subTest(size=size, function=function.__name__), self.assertRaises(ValueError):
                    function(SizedInput(size))

    def test_rejects_invalid_keys_before_reading_input(self):
        for key in (-1, 256, "19", None):
            with self.subTest(key=key), self.assertRaises(ValueError):
                decrypt_cmc_gfx.decrypt_graphics(SizedInput(0x4000000), key)

    def test_fixed_permutation(self):
        data = bytearray(decrypt_cmc_gfx.GRAPHICS_SIZE)
        tail_start = len(data) - decrypt_cmc_gfx.FIXED_SIZE
        # Vary both block and in-block byte to catch wrong tail/block offsets.
        for offset in range(decrypt_cmc_gfx.FIXED_SIZE):
            data[tail_start + offset] = ((offset // 32) * 17 + offset % 32) & 0xff
        fixed = decrypt_cmc_gfx.extract_fixed(data)
        self.assertEqual(len(fixed), 0x20000)
        permutation = (2, 6, 10, 14, 18, 22, 26, 30,
                       0, 4, 8, 12, 16, 20, 24, 28,
                       3, 7, 11, 15, 19, 23, 27, 31,
                       1, 5, 9, 13, 17, 21, 25, 29)
        expected = bytes(((block * 17 + source) & 0xff)
                         for block in range(0x20000 // 32) for source in permutation)
        self.assertEqual(fixed, expected)

    def test_tables_are_complete_byte_tuples(self):
        tables = cmc_tables.load_tables()
        self.assertEqual(len(tables), 20)
        self.assertIn("m1_address_8_15_xor", tables)
        self.assertIn("m1_address_0_7_xor", tables)
        for name, values in tables.items():
            with self.subTest(name=name):
                self.assertIsInstance(values, tuple)
                self.assertEqual(len(values), 256)
                self.assertTrue(all(type(value) is int and 0 <= value <= 255 for value in values))

    def test_loader_rejects_modified_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "artifacts/reference").mkdir(parents=True)
            manifest = {"files": [{"path": cmc_tables.SOURCE_PATH,
                                   "sha256": hashlib.sha256(b"original").hexdigest()}]}
            (root / "config/mame_sources.json").write_text(json.dumps(manifest))
            (root / "artifacts/reference/prot_cmc.cpp").write_bytes(b"modified")
            cmc_tables.load_tables.cache_clear()
            try:
                with patch.object(cmc_tables, "ROOT", root), self.assertRaisesRegex(ValueError, "hash mismatch"):
                    cmc_tables.load_tables()
            finally:
                cmc_tables.load_tables.cache_clear()


if __name__ == "__main__":
    unittest.main()
