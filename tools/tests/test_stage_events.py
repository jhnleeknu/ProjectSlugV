"""Synthetic MS5D and event read-boundary checks; no ROM test fixture."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pack_stage_events as pack
from inventory_stage_event_contexts import walk_gates


class StageEventTests(unittest.TestCase):
    def fixture(self):
        program = bytearray(0x120)
        # Opaque bytes contain a tempting ff and invalid marker; jump skips both.
        raw = b'\x00\x04\xff\x07\xaa\xbb'+struct.pack('>3H', 0, 0x8000, 8)+b'\x42\x99\xff'
        program[0x100:0x100+len(raw)] = raw
        return program, raw

    def test_odd_payload_preserves_opaque_bytes_and_exact_ff_boundary(self):
        program, raw = self.fixture()
        program[0x111:0x115] = b'\x00\x00\x00\x00'
        payload, chain = pack.stream_payload(program, 0x100)
        self.assertEqual(payload, raw)
        self.assertEqual(len(payload), 15)
        self.assertEqual(chain['terminal']['cpu_address'], 0x10e)
        self.assertEqual(chain['gates'][0]['raw_hex'], '000080000008')
        self.assertEqual(pack.validate_container(pack.wrap(payload, 0x100), 0x100), payload)

    def test_target_zero_does_not_follow_header_and_positive_target_unsigned(self):
        program, _ = self.fixture()
        zero = walk_gates(program, 0x100, 0)
        self.assertEqual(zero['selected_cursor_cpu_address'], 0x102)
        self.assertEqual(zero['gates'], [])
        equal = walk_gates(program, 0x100, 0x8000)
        self.assertEqual(equal['status'], 'selected_gate')
        self.assertEqual(equal['selected_cursor_cpu_address'], 0x106)
        later = walk_gates(program, 0x100, 0x8001)
        self.assertEqual(later['status'], 'selected_terminal_ff')
        self.assertEqual(later['selected_cursor_cpu_address'], 0x10e)

    def test_container_identity_crc_size_and_extra_bytes(self):
        packed = pack.wrap(b'\x00\x00\xff', 0x100)
        for offset in (0, 4, 8, 12, 16, 20, 24, 28, 32):
            corrupted = bytearray(packed)
            corrupted[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                pack.validate_container(bytes(corrupted), 0x100)
        for corrupted in (packed[:31], packed[:-1], packed+b'\0'):
            with self.subTest(size=len(corrupted)), self.assertRaises(ValueError):
                pack.validate_container(corrupted, 0x100)
        with self.assertRaises(ValueError):
            pack.validate_container(packed, 0x102)

    def test_fixed_rom_payload_end_boundary(self):
        payload = b'\x00\x00\xff'
        packed = pack.wrap(payload, 0xffffc)
        self.assertEqual(pack.validate_container(packed, 0xffffc), payload)
        for cpu in (-2, 0, 1, 0xffffe, 0x100000):
            with self.subTest(cpu=cpu), self.assertRaises(ValueError):
                pack.wrap(payload, cpu)
        with self.assertRaises(ValueError):
            pack.wrap(b'', 0x100)
        program = bytearray(0x100000)
        program[0xffffc:0xfffff] = payload
        self.assertEqual(pack.stream_payload(program, 0xffffc)[0], payload)
        program[0xffffe:] = b'\x00\x00'
        with self.assertRaises(ValueError):
            pack.stream_payload(program, 0xffffe)

    def test_monotonic_guards_reject_backward_header_and_gate(self):
        program = bytearray(0x120)
        program[0x100:0x102] = b'\xff\xfe'
        with self.assertRaises(ValueError):
            pack.stream_payload(program, 0x100)
        program, _ = self.fixture()
        program[0x104] = 0xff
        program[0x10a:0x10c] = b'\xff\xfe'
        # Raw walker can reach this ff; packaging requires positive gate jumps.
        self.assertEqual(walk_gates(program, 0x100)['status'], 'terminal_ff')
        with self.assertRaises(ValueError):
            pack.stream_payload(program, 0x100)
        program, _ = self.fixture()
        program[0x10a:0x10c] = b'\x00\x00'
        self.assertEqual(walk_gates(program, 0x100)['status'], 'unsupported_cycle')
        with self.assertRaises(ValueError):
            pack.stream_payload(program, 0x100)

    def test_unsupported_marker_alignment_and_truncated_reads(self):
        program, _ = self.fixture()
        program[0x106] = 7
        self.assertEqual(walk_gates(program, 0x100)['status'], 'unsupported_trap_marker')
        with self.assertRaises(ValueError):
            pack.stream_payload(program, 0x100)
        program, _ = self.fixture()
        for address in (0, 0x101, 0x120):
            with self.subTest(address=address), self.assertRaises(ValueError):
                pack.stream_payload(program, address)
        truncated = program[:0x10b]
        with self.assertRaises(ValueError):
            pack.stream_payload(truncated, 0x100)

    def test_report_exact_and_partial_overlaps_without_merging(self):
        resources = [dict(id='a', source_cpu_address=0x100, end_cpu_address_exclusive=0x110),
                     dict(id='b', source_cpu_address=0x100, end_cpu_address_exclusive=0x110),
                     dict(id='c', source_cpu_address=0x108, end_cpu_address_exclusive=0x118),
                     dict(id='d', source_cpu_address=0x118, end_cpu_address_exclusive=0x120)]
        rows = pack.overlaps(resources)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['classification'], 'exact_duplicate_span')
        self.assertEqual(rows[1]['classification'], 'partial_overlap')
        self.assertEqual(len(resources), 4)


if __name__ == '__main__':
    unittest.main()
