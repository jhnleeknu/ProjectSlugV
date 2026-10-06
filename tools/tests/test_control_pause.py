"""Pinned pause text bytes, native callers, stream boundaries, and MS5D header."""
import struct
import unittest
import zlib

from tools.pack_control_pause import BASE, CLEAR, END, extract, pack_payload


class ControlPauseTests(unittest.TestCase):
    def setUp(self):
        self.program = bytearray(0x9250)
        self.data = bytes.fromhex('5c6c121a5c70005c6303504155534500005c6c121a5c6303202020202000')
        self.program[BASE:END] = self.data
        self.program[0x9238:0x923c] = bytes.fromhex('41fafe3f')
        self.program[0x924c:0x9250] = bytes.fromhex('41fafe1a')

    def test_extract_pinned_bytes(self):
        self.assertEqual(extract(self.program), self.data)
        self.assertEqual(len(self.data), 30)

    def test_stream_split_and_padding(self):
        data = extract(self.program)
        self.assertEqual(data[:CLEAR - BASE],
                         bytes.fromhex('5c6c121a5c70005c630350415553450000'))
        self.assertEqual(data[CLEAR - BASE:],
                         bytes.fromhex('5c6c121a5c6303202020202000'))
        self.assertEqual(data[0x9077 - BASE:0x9079 - BASE], b'\0\0')
        self.assertEqual(data[-1], 0)

    def test_ms5d_header_and_payload(self):
        packed = pack_payload(extract(self.program))
        self.assertEqual(struct.unpack('<4s7I', packed[:32]),
                         (b'MS5D', 1, 1, BASE, BASE, 30, zlib.crc32(self.data), 0))
        self.assertEqual(packed[32:], self.data)
        self.assertEqual(len(packed), 62)

    def test_reject_truncation(self):
        for end in (BASE, END - 1, END, 0x923b, 0x924f):
            with self.subTest(end=end), self.assertRaises(ValueError):
                extract(self.program[:end])

    def test_reject_mutated_callers(self):
        for address in (0x9238, 0x923a, 0x923b, 0x924c, 0x924e, 0x924f):
            changed = bytearray(self.program)
            changed[address] ^= 1
            with self.subTest(address=address), self.assertRaises(ValueError):
                extract(changed)

    def test_reject_mutated_stream_or_padding(self):
        for address in (BASE, 0x9077, 0x9078, CLEAR, END - 1):
            changed = bytearray(self.program)
            changed[address] ^= 1
            with self.subTest(address=address), self.assertRaises(ValueError):
                extract(changed)
        for data in (self.data[:-1], self.data + b'\0', bytes(30)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                pack_payload(data)


if __name__ == '__main__':
    unittest.main()
