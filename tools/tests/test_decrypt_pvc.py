"""Small synthetic checks; full-image comparison is a separate reference check."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "decrypt_pvc.py"
SPEC = importlib.util.spec_from_file_location("decrypt_pvc", SCRIPT)
decrypt_pvc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decrypt_pvc)


class DecryptPvcTests(unittest.TestCase):
    def test_rejects_invalid_image_size(self):
        for size in (0, 1, 0x800000 - 1, 0x800000 + 1):
            with self.subTest(size=size), self.assertRaises(ValueError):
                decrypt_pvc.decrypt_program(bytes(size))

    def test_bitswap_known_patterns(self):
        self.assertEqual(decrypt_pvc.bitswap(0x0400, *decrypt_pvc.WORD_BITS), 0x0800)
        self.assertEqual(decrypt_pvc.bitswap(0x000f, *decrypt_pvc.WORD_BITS), 0x000f)
        self.assertEqual(decrypt_pvc.bitswap(0x01, *decrypt_pvc.FIRST_BLOCK_BITS), 0x04)
        self.assertEqual(decrypt_pvc.bitswap(0x04, *decrypt_pvc.FIRST_BLOCK_BITS), 0x01)
        self.assertEqual(decrypt_pvc.bitswap(0x20, *decrypt_pvc.LATER_BLOCK_BITS), 0x80)
        self.assertEqual(decrypt_pvc.bitswap(0x80, *decrypt_pvc.LATER_BLOCK_BITS), 0x20)

    def test_rejects_invalid_byte_layout(self):
        data = bytes(decrypt_pvc.PROGRAM_SIZE)
        for byte_xor in (-1, 2):
            with self.subTest(byte_xor=byte_xor), self.assertRaises(ValueError):
                decrypt_pvc.decrypt_program(data, byte_xor=byte_xor)


if __name__ == "__main__":
    unittest.main()
