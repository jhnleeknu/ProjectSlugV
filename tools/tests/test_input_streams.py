"""Native stream bounds/table/selector checks and binary container integrity."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib

from tools import pack_input_streams as streams


class InputStreamsTests(unittest.TestCase):
    def setUp(self):
        # Synthetic bytes keep extracted ROM data out of version control. Patch
        # only the pinned digest; exercise the production checks themselves.
        self.data = bytearray((index * 17 + 23) & 255
                              for index in range(streams.END - streams.BASE))
        for address, targets in streams.TABLES:
            struct.pack_into('>II', self.data, address - streams.BASE, *targets)
        self.program = bytearray(streams.END)
        self.program[streams.BASE:streams.END] = self.data
        self.digest = patch.object(streams, 'PAYLOAD_SHA256',
                                   hashlib.sha256(self.data).hexdigest())
        self.digest.start()
        self.addCleanup(self.digest.stop)

    def test_complete_native_window_preserved(self):
        self.assertEqual(streams.extract(self.program), bytes(self.data))
        self.assertEqual(len(self.data), 4 * 0x600 + 16)
        for address in streams.BUFFER_ADDRESSES:
            at = address - streams.BASE
            self.assertEqual(streams.extract(self.program)[at:at + 0x600],
                             self.data[at:at + 0x600])

    def test_header_payload_and_crc(self):
        packed = streams.pack_payload(streams.extract(self.program))
        self.assertEqual(struct.unpack('<4s7I', packed[:32]),
                         (b'MS5D', 1, 1, streams.BASE, streams.BASE,
                          len(self.data), zlib.crc32(self.data), 0))
        self.assertEqual(packed[32:], bytes(self.data))
        damaged = bytearray(packed)
        damaged[-1] ^= 1
        self.assertNotEqual(struct.unpack_from('<I', damaged, 24)[0],
                            zlib.crc32(damaged[32:]))

    def test_reject_truncated_program_and_payload(self):
        for end in (0, streams.SELECTOR + 1, streams.BASE, streams.END - 1):
            with self.subTest(end=end), self.assertRaises(ValueError):
                streams.extract(self.program[:end])
        for data in (self.data[:-1], self.data + b'\0', b''):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                streams.pack_payload(data)

    def test_reject_each_malformed_pointer(self):
        for table, _ in streams.TABLES:
            for displacement in (0, 4):
                altered = bytearray(self.program)
                struct.pack_into('>I', altered, table + displacement, streams.BASE + 1)
                with self.subTest(table=table, displacement=displacement), self.assertRaisesRegex(
                        ValueError, 'pointer table'):
                    streams.extract(altered)

    def test_reject_selector_change(self):
        for word in (1, 0x100, 0xffff):
            altered = bytearray(self.program)
            struct.pack_into('>H', altered, streams.SELECTOR, word)
            with self.subTest(word=word), self.assertRaisesRegex(ValueError, 'selector'):
                streams.extract(altered)

    def test_reject_record_or_unused_byte_changes(self):
        for address in streams.BUFFER_ADDRESSES:
            for displacement in (0, 1, 0x2ff, 0x5ff):
                altered = bytearray(self.program)
                altered[address + displacement] ^= 1
                with self.subTest(address=address, displacement=displacement), self.assertRaisesRegex(
                        ValueError, 'native bytes'):
                    streams.extract(altered)
        altered = bytearray(self.data)
        altered[3] ^= 1
        with self.assertRaises(ValueError):
            streams.pack_payload(altered)


if __name__ == '__main__':
    unittest.main()
