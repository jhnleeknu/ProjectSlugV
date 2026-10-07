"""Synthetic bounds and inline-byte preservation for scene script extraction."""
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pack_scene_scripts import command_span, motion_span, descriptor_span, palette_lookup_address, palette_binding_span, PALETTE_BANK_START, wrap, OPERANDS


class SceneScriptPackTests(unittest.TestCase):
    def scan(self, payload):
        return command_span(bytes(2) + payload, 2)

    def test_every_operand_length_and_terminator(self):
        payload = b''.join(struct.pack('>H', op * 4) + bytes(size)
                           for op, size in enumerate(OPERANDS)) + b'\xff\xff'
        end, rows, term = self.scan(payload)
        self.assertEqual((end, term), (len(payload) + 2, len(payload)))
        self.assertEqual(len(rows), 20)
        self.assertEqual([len(bytes.fromhex(r['operand_hex'])) for r in rows], list(OPERANDS))

    def test_inline_bytes_are_not_commands(self):
        payload = bytes.fromhex('002c0001000200048000ffff00480003ffff')
        end, rows, term = self.scan(payload)
        self.assertEqual([r['opcode'] for r in rows], [0x2c, 0x48])
        self.assertEqual(rows[0]['inline_hex'], '8000ffff')
        self.assertEqual(end, len(payload) + 2)

    def test_negative_and_odd_inline_skip(self):
        for skip in (0xffff, 1, 3):
            with self.assertRaisesRegex(ValueError, 'negative or odd'):
                self.scan(struct.pack('>4H', 0x2c, 1, 2, skip) + bytes(10))

    def test_truncated_operands_inline_and_terminator(self):
        for payload in (b'', b'\0', b'\x00\x00\0', bytes.fromhex('002c000000000004aabb'),
                        bytes.fromhex('00480001')):
            with self.assertRaises(ValueError):
                self.scan(payload)

    def test_bad_opcode_and_address(self):
        for opcode in (1, 0x50, 0x7fff):
            with self.assertRaisesRegex(ValueError, 'opcode'):
                self.scan(struct.pack('>H', opcode) + bytes(10))
        for address in (0, 1, 0x100000):
            with self.assertRaises(ValueError):
                command_span(bytes(16), address)

    def test_span_excludes_following_bytes_and_header_crc(self):
        program = bytes.fromhex('000000480003ffff12345678')
        end, rows, term = command_span(program, 2)
        self.assertEqual(end, 8)
        raw = wrap(program[2:end], 2)
        self.assertEqual(struct.unpack('<4s7I', raw[:32]),
                         (b'MS5D', 1, 1, 2, 2, 6, zlib.crc32(raw[32:]), 0))
        self.assertEqual(raw[32:], bytes.fromhex('00480003ffff'))


class MotionSpanTests(unittest.TestCase):
    def scan(self, payload):
        return motion_span(bytes(2) + payload, 2)

    def test_type_is_second_word_not_time(self):
        for time, kind in ((1, 0x14), (0xffff, 0x64), (3, 0x80)):
            ordinary = struct.pack('>5H', time, kind, 2, 3, 4)
            end, records, first_type, terminal = self.scan(ordinary + struct.pack('>HH', 9, 0xffff) + b'ignored')
            self.assertEqual((end, records, first_type, terminal), (16, 1, kind, 12))
        for kind in (0x90, 1, 0x7fff):
            with self.assertRaisesRegex(ValueError, 'first type'):
                self.scan(struct.pack('>5H', 0, kind, 2, 3, 4) + struct.pack('>HH', 0, 0xffff))

    def test_terminal_prefix_and_subsequent_type_are_raw(self):
        raw = struct.pack('>5H', 1, 0x14, 2, 3, 4) + struct.pack('>5H', 2, 0xdead, 5, 6, 7)
        terminal = struct.pack('>HH', 0xbeef, 0xffff)
        end, records, kind, at = self.scan(raw + terminal + b'not-included')
        self.assertEqual((end, records, kind, at), (26, 2, 0x14, 22))
        packed = wrap((bytes(2) + raw + terminal)[2:end], 2)
        self.assertEqual(packed[32:], raw + terminal)
        self.assertEqual(zlib.crc32(packed[32:]), struct.unpack('<4s7I', packed[:32])[6])

    def test_first_terminal_and_truncated_records_rejected(self):
        for raw in (struct.pack('>HH', 1, 0xffff), struct.pack('>HH', 1, 0x14),
                    struct.pack('>5H', 1, 0x14, 2, 3, 4), b'\x00'):
            with self.assertRaises(ValueError):
                self.scan(raw)


class PaletteDependencyTests(unittest.TestCase):
    def program(self, payload):
        return bytes(PALETTE_BANK_START) + payload

    def test_lookup_shift_wrap_and_signed_offset(self):
        self.assertEqual(palette_lookup_address(0x2003d0, 1), (0x2003d4, 4, 4))
        self.assertEqual(palette_lookup_address(0x2003d0, 0xffff), (0x2003cc, 0xfffc, -4))
        self.assertEqual(palette_lookup_address(0x2003d0, 0x4000), (0x2003d0, 0, 0))
        self.assertEqual(palette_lookup_address(0x208000, 0x2000), (0x200000, 0x8000, -32768))
        for root, selector in ((0x200000, 0xffff), (0x2fffec, 1), (0x200001, 0)):
            with self.assertRaises(ValueError):
                palette_lookup_address(root, selector)

    def test_slot_first_word_and_sixth_byte_preserved(self):
        raw = bytes.fromhex('0001ffffa55a00ff0065037effff1234')
        end, records, terminal = palette_binding_span(self.program(raw), PALETTE_BANK_START)
        self.assertEqual((end, terminal), (PALETTE_BANK_START + 14, PALETTE_BANK_START + 12))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['slot_word'], 1)
        self.assertEqual(records[0]['source_word'], 0xffff)
        self.assertEqual(records[0]['sixth_byte'], 0x5a)
        self.assertEqual(records[1]['slot_word'], 255)
        self.assertEqual(records[1]['raw_hex'], '00ff0065037e')
        packed = wrap(self.program(raw)[PALETTE_BANK_START:end], PALETTE_BANK_START, kind=2)
        self.assertEqual(packed[32:], raw[:14])
        self.assertEqual(struct.unpack('<4s7I', packed[:32])[:5], (b'MS5D', 1, 2, PALETTE_BANK_START, PALETTE_BANK_START))
        self.assertEqual(struct.unpack('<4s7I', packed[:32])[6], zlib.crc32(raw[:14]))
        self.assertEqual(palette_binding_span(self.program(b'\xff\xff'), PALETTE_BANK_START)[1], [])

    def test_binding_bad_slot_truncation_and_bank_bound(self):
        for payload in (bytes.fromhex('010000000000ffff'), bytes.fromhex('00010000'), bytes.fromhex('000100000000')):
            with self.assertRaises(ValueError):
                palette_binding_span(self.program(payload), PALETTE_BANK_START)
        with self.assertRaises(ValueError):
            palette_binding_span(self.program(bytes(12)), PALETTE_BANK_START + 1)
        with self.assertRaises(ValueError):
            palette_binding_span(bytes(0x300000), 0x2ffff0)
        near_end = bytearray(0x2ffff0)
        near_end[0x2fffec:0x2ffff0] = bytes.fromhex('00010000')
        with self.assertRaises(ValueError):
            palette_binding_span(near_end, 0x2fffec)


class DescriptorSpanTests(unittest.TestCase):
    def scan(self, payload):
        return descriptor_span(bytes(2) + payload, 2)

    def test_prefix_suffix_gap_and_terminal_raw_window(self):
        payload = struct.pack('>3H',8,1,64) + b'AB' + struct.pack('>2H',6,0) + b'CD' + struct.pack('>2HI',8,2,0x109156) + struct.pack('>2H',0,3)
        end, rows = self.scan(payload + b'following')
        self.assertEqual(end,len(payload)+2)
        self.assertEqual([r['phase'] for r in rows],['prefix','prefix','suffix','suffix'])
        self.assertEqual([r['type_word'] for r in rows],[1,0,2,3])
        self.assertEqual(wrap(payload,2)[32:],payload)
        for terminal_word in (0, 1, 0xffff, 0x8000):
            end, terminal_rows = self.scan(struct.pack('>2H',terminal_word,3))
            self.assertEqual(end,6)
            self.assertEqual(terminal_rows[0]['type_word'],3)

    def test_bad_stride_type_suffix_and_truncation(self):
        cases = [struct.pack('>3H',v,1,64) for v in (0,4,7,0xfffe)]
        cases += [struct.pack('>2H',4,4),struct.pack('>2H',4,0)+struct.pack('>2H',4,0),
                  struct.pack('>2H',4,2),struct.pack('>2H',4,0)]
        for raw in cases:
            with self.assertRaises(ValueError):self.scan(raw)
        for address in (0,1,0x100000):
            with self.assertRaises(ValueError):descriptor_span(bytes(16),address)


if __name__ == '__main__':
    unittest.main()
