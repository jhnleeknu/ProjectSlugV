"""Small synthetic checks; full-image MAME comparison is separate."""

import unittest

from tools import decrypt_sound


class DecryptSoundTests(unittest.TestCase):
    def test_rejects_invalid_m1_size(self):
        for size in (0, 1, decrypt_sound.M1_SIZE - 1, decrypt_sound.M1_SIZE + 1):
            with self.subTest(size=size), self.assertRaises(ValueError):
                decrypt_sound.decrypt_m1(bytes(size))
            with self.subTest(size=size), self.assertRaises(ValueError):
                decrypt_sound.build_audio_region(bytes(size))

    def test_rejects_invalid_sample_size(self):
        for size in (0, 1, decrypt_sound.SAMPLES_SIZE - 1,
                     decrypt_sound.SAMPLES_SIZE + 1):
            with self.subTest(size=size), self.assertRaises(ValueError):
                decrypt_sound.decrypt_samples(bytes(size))

    def test_m1_permutation_known_addresses_without_table_xor(self):
        tables = {"m1_address_0_7_xor": (0,) * 256,
                  "m1_address_8_15_xor": (0,) * 256}
        expected_low = (0x0002, 0x0400, 0x0008, 0x0020,
                        0x2000, 0x0800, 0x0080, 0x0040)
        for block in range(8):
            base = block << 16
            with self.subTest(block=block):
                self.assertEqual(decrypt_sound.m1_address_scramble(base, 0, tables), base)
                self.assertEqual(decrypt_sound.m1_address_scramble(base | 1, 0, tables),
                                 base | expected_low[block])
        self.assertEqual(decrypt_sound.m1_address_scramble(0x100, 0, tables), 0x8000)
        self.assertEqual(decrypt_sound.m1_address_scramble(0, 1, tables), 4)

    def test_m1_xor_order(self):
        low = [0] * 256
        high = [0] * 256
        low[0] = 1
        high[1] = 1
        tables = {"m1_address_0_7_xor": tuple(low),
                  "m1_address_8_15_xor": tuple(high)}
        # First XOR changes the index used by the second XOR.
        self.assertEqual(decrypt_sound.m1_address_scramble(0, 0, tables), 3)

    def test_audio_region_layout(self):
        blocks = [bytes([i]) * 0x10000 for i in range(8)]
        source = b"".join(blocks)
        region = decrypt_sound.build_audio_region(source)
        self.assertEqual(len(region), 0x90000)
        self.assertEqual(region[:0x10000], blocks[0])
        self.assertEqual(region[0x10000:], source)

    def test_pcm2_address_cases(self):
        expected = ((0, 0x04e001, 0xfe2cf6),
                    (1, 0x05e001, 0xfe2cf7),
                    (0x10000, 0x04e000, 0xff2cf6),
                    (0xffffff, 0xfb1ffe, 0xfe2cf5),
                    (0x1d30a, 0x04330a, 0))
        for address, destination, source in expected:
            with self.subTest(address=address):
                self.assertEqual(decrypt_sound.sample_destination_address(address), destination)
                self.assertEqual(decrypt_sound.sample_source_address(address), source)


if __name__ == "__main__":
    unittest.main()
