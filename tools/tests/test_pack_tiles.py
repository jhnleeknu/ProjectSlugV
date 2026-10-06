"""MS5T boundary and header checks with synthetic fixed-layer data."""
import struct
import unittest
import zlib
from tools.pack_tiles import pack_payload


class PackTilesTests(unittest.TestCase):
    def test_header_and_payload(self):
        pixels = bytes(range(16)) * (4096*64//16)
        packed = pack_payload(pixels, 2, 8, 8, 4096)
        self.assertEqual(struct.unpack('<4s7I', packed[:32]),
                         (b'MS5T', 1, 2, 8, 8, 4096, len(pixels), zlib.crc32(pixels)))
        self.assertEqual(packed[32:], pixels)

    def test_reject_bad_catalog(self):
        for kind, width, height, count in [(0,8,8,4096),(2,16,8,4096),(2,8,8,1)]:
            with self.subTest(kind=kind,width=width,count=count), self.assertRaises(ValueError):
                pack_payload(b'',kind,width,height,count)

    def test_reject_bad_length_or_pixel(self):
        for payload in (b'', b'\x10'+bytes(4096*64-1)):
            with self.assertRaises(ValueError):
                pack_payload(payload,2,8,8,4096)


if __name__ == '__main__':
    unittest.main()
