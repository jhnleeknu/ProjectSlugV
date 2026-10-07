"""Input status preservation, bounds, pinned bytes and MS5D integrity."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib

from tools import pack_input_status as status


class InputStatusTests(unittest.TestCase):
    def setUp(self):
        # Synthetic content avoids storing ROM bytes in tracked test sources.
        # Only its pinned digest is substituted; production validation remains.
        self.data = bytes((index * 29 + 11) & 255 for index in range(256))
        self.program = bytearray(status.END)
        self.program[status.BASE:status.END] = self.data
        digest = patch.object(status, 'PAYLOAD_SHA256', hashlib.sha256(self.data).hexdigest())
        digest.start()
        self.addCleanup(digest.stop)

    def test_complete_window_including_code_overlap(self):
        data = status.extract(self.program)
        self.assertEqual(data, self.data)
        self.assertEqual(len(data), 256)
        self.assertEqual(data[0xb68 - status.BASE:], self.program[0xb68:status.END])
        self.assertEqual(data[-1], self.program[status.END - 1])

    def test_ms5d_header_and_payload_crc(self):
        packed = status.pack_payload(status.extract(self.program))
        self.assertEqual(len(packed), 288)
        self.assertEqual(struct.unpack('<4s7I', packed[:32]),
                         (b'MS5D', 1, 1, status.BASE, status.BASE,
                          256, zlib.crc32(self.data), 0))
        self.assertEqual(packed[32:], self.data)
        altered = bytearray(packed)
        altered[32 + 0x80] ^= 1
        self.assertNotEqual(struct.unpack_from('<I', altered, 24)[0],
                            zlib.crc32(altered[32:]))

    def test_reject_truncated_program(self):
        for end in (0, status.BASE, status.END - 1):
            with self.subTest(end=end), self.assertRaisesRegex(ValueError, 'Truncated'):
                status.extract(self.program[:end])

    def test_reject_incorrect_payload_extent(self):
        for data in (b'', self.data[:-1], self.data + b'\0'):
            with self.subTest(size=len(data)), self.assertRaisesRegex(ValueError, 'complete'):
                status.pack_payload(data)

    def test_reject_changed_lookup_and_code_bytes(self):
        for offset in (0, 15, 16, 0x80, 255):
            altered = bytearray(self.program)
            altered[status.BASE + offset] ^= 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'native bytes'):
                status.extract(altered)
        altered = bytearray(self.data)
        altered[-1] ^= 1
        with self.assertRaises(ValueError):
            status.pack_payload(altered)

    def test_surrounding_program_bytes_do_not_change_window(self):
        altered = self.program + b'outside native window'
        altered[status.BASE - 1] = 0xff
        self.assertEqual(status.extract(altered), self.data)


if __name__ == '__main__':
    unittest.main()
