"""Synthetic boundary/state checks for explicit cartridge ROM mapping."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "address_map.py"
SPEC = importlib.util.spec_from_file_location("address_map", SCRIPT)
address_map = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(address_map)


class AddressMapTests(unittest.TestCase):
    def test_vector_selection_and_fixed_rom_boundaries(self):
        for address in (0, 1, 0x7e, 0x7f):
            with self.subTest(address=address):
                self.assertIsNone(address_map.cpu_to_rom_offset(address))
                self.assertEqual(address_map.cpu_to_rom_offset(address, cart_vectors=True), address)
        for address in (0x80, 0x81, 0xffffe, 0xfffff):
            with self.subTest(address=address):
                self.assertEqual(address_map.cpu_to_rom_offset(address), address)

    def test_bank_state_is_required_and_not_mib_aligned(self):
        for address in (0x200000, 0x200001, 0x2fdffe, 0x2fdfff):
            with self.subTest(address=address):
                self.assertIsNone(address_map.cpu_to_rom_offset(address))
                for base in (0, 1, 0x100002, 0x234568):
                    self.assertEqual(address_map.cpu_to_rom_offset(address, base),
                                     base + address - 0x200000)

    def test_pvc_overlay_and_other_regions_are_not_rom(self):
        for address in (0x100000, 0x1fffff, 0x2fe000, 0x2fe001,
                        0x2ffff0, 0x2fffff, 0x300000, 0xc00000, 0xffffff):
            with self.subTest(address=address):
                self.assertIsNone(address_map.cpu_to_rom_offset(address, 0x100000, True))

    def test_rom_bounds_never_wrap(self):
        self.assertEqual(address_map.cpu_to_rom_offset(0x200001, 0x7ffffe), 0x7fffff)
        self.assertIsNone(address_map.cpu_to_rom_offset(0x200002, 0x7ffffe))
        self.assertIsNone(address_map.cpu_to_rom_offset(0x200000, 0x800000))
        self.assertIsNone(address_map.cpu_to_rom_offset(0x200000, 0x1000000))
        self.assertIsNone(address_map.cpu_to_rom_offset(0, cart_vectors=True, rom_size=0))
        self.assertEqual(address_map.cpu_to_rom_offset(0x7f, cart_vectors=True, rom_size=0x80), 0x7f)
        self.assertIsNone(address_map.cpu_to_rom_offset(0x80, rom_size=0x80))
        self.assertIsNone(address_map.cpu_to_rom_offset(0xfffff, rom_size=0xfffff))

    def test_invalid_mapping_inputs(self):
        for value in (-1, 0x1000000, 1.5, "0x80", None, True):
            with self.subTest(cpu_address=value), self.assertRaises(ValueError):
                address_map.cpu_to_rom_offset(value)
        for value in (-2, 1.5, "0x100000", True):
            with self.subTest(bank_base=value), self.assertRaises(ValueError):
                address_map.cpu_to_rom_offset(0x80, bank_base=value)
        for value in (-1, 1.5, None, True):
            with self.subTest(rom_size=value), self.assertRaises(ValueError):
                address_map.cpu_to_rom_offset(0x80, rom_size=value)
        with self.assertRaises(ValueError):
            address_map.cpu_to_rom_offset(0, cart_vectors=1)


class PvcBankUpdateTests(unittest.TestCase):
    def test_formula_and_register_side_effects(self):
        cases = (
            (0x0000, 0x0000, (0x100000, 0x00a0, 0x0000)),
            (0x02ff, 0x1234, (0x223402, 0x02a0, 0x1234)),
            (0xabcd, 0x8001, (0x9001ab, 0xaaa0, 0x0001)),
            (0xffff, 0xffff, (0x10fffff, 0xfea0, 0x7fff)),
        )
        for ff8, ff9, expected in cases:
            with self.subTest(ff8=ff8, ff9=ff9):
                self.assertEqual(address_map.pvc_bank_update(ff8, ff9), expected)

    def test_ff8_low_byte_does_not_change_bank(self):
        self.assertEqual(address_map.pvc_bank_update(0x1234, 0x0056),
                         address_map.pvc_bank_update(0x12ff, 0x0056))

    def test_odd_pvc_bank_base_maps_without_rounding(self):
        base, ff8, ff9 = address_map.pvc_bank_update(0xabcd, 0x0001)
        self.assertEqual(base, 0x1001ab)
        self.assertEqual(address_map.cpu_to_rom_offset(0x200000, base), 0x1001ab)
        self.assertEqual(address_map.cpu_to_rom_offset(0x200001, base), 0x1001ac)

    def test_invalid_words_do_not_truncate_or_wrap(self):
        for value in (-1, 0x10000, 1.5, "0xffff", None, True):
            with self.subTest(word_ff8=value), self.assertRaises(ValueError):
                address_map.pvc_bank_update(value, 0)
            with self.subTest(word_ff9=value), self.assertRaises(ValueError):
                address_map.pvc_bank_update(0, value)


if __name__ == "__main__":
    unittest.main()
