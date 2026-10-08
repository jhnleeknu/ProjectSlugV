"""Synthetic MS5D kind3 validation; no canonical/extracted ROM fixture bytes."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from tools import pack_physical_program as physical


class PhysicalProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program = bytes((i*19+7) & 255 for i in range(256))*32768
        cls.digest = physical.sha(cls.program)
        cls.directory = tempfile.TemporaryDirectory(prefix='ms5-physical-program-test-')
        cls.root = Path(cls.directory.name)
        (cls.root/'synthetic.bin').write_bytes(cls.program)
        (cls.root/'tools').mkdir()
        repo = Path(__file__).resolve().parents[2]
        for name in ('pack_physical_program.py', 'disassemble_program.py'):
            (cls.root/'tools'/name).write_bytes((repo/'tools'/name).read_bytes())
        cls.source = dict(path='synthetic.bin', size=len(cls.program), byte_order='big', sha256=cls.digest)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def build(self, responses=None):
        with patch.object(physical, 'SOURCE_SHA256', self.digest), patch.object(physical, 'load_verified_program',
                side_effect=responses or [(self.program, self.source), (self.program, self.source)]):
            return physical.build(self.root)

    def test_header_exact_and_roundtrip(self):
        raw = b'\x01\x23\x45'
        packed = physical.wrap(raw, 0x123)
        self.assertEqual(struct.unpack_from('<4s7I', packed),
            (b'MS5D', 1, 3, 0xffffffff, 0x123, 3, zlib.crc32(raw), 0))
        self.assertEqual(physical.validate_container(packed), raw)

    def test_odd_span_and_last_BYTE(self):
        for rom, raw in ((1, b'abc'), (0x7fffff, b'Z'), (0x7ffff1, bytes(range(15)))):
            with self.subTest(rom=rom):
                self.assertEqual(physical.validate_container(physical.wrap(raw, rom)), raw)

    def test_complete_final112_bytes_can_be_represented(self):
        for bank in range(1, 8):
            rom = (bank+1)*0x100000-16
            self.assertEqual(physical.validate_container(physical.wrap(bytes(range(16)), rom)), bytes(range(16)))

    def test_payload_range_and_type_errors(self):
        for rom, raw in ((-1, b'x'), (0x800000, b'x'), (0x7fffff, b'xy'),
                         (0, b''), (0, b'x'*(0x100000+1)), (True, b'x'), (1.0, b'x')):
            with self.subTest(rom=rom, size=len(raw)), self.assertRaises(ValueError):
                physical.wrap(raw, rom)

    def test_header_identity_corruption(self):
        packed = physical.wrap(b'0123', 0x10)
        for at in (0, 4, 8, 12, 28):
            changed = bytearray(packed);changed[at] ^= 1
            with self.subTest(offset=at), self.assertRaises(ValueError):physical.validate_container(changed)

    def test_header_range_and_length_corruption(self):
        packed = physical.wrap(b'0123', 0x10)
        for at, value in ((16, 0x800000), (16, 0x7ffffe), (20, 0), (20, 0x100001)):
            changed = bytearray(packed);struct.pack_into('<I', changed, at, value)
            with self.subTest(offset=at, value=value), self.assertRaises(ValueError):physical.validate_container(changed)
        for changed in (packed[:31], packed[:-1], packed+b'\0'):
            with self.assertRaises(ValueError):physical.validate_container(changed)

    def test_crc_mismatch(self):
        changed = bytearray(physical.wrap(b'0123', 3));changed[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'CRC32'):physical.validate_container(changed)

    def test_general_format_allows_new_payload_with_valid_crc(self):
        changed = bytearray(physical.wrap(b'0123', 3));changed[-1] ^= 1
        struct.pack_into('<I', changed, 24, zlib.crc32(changed[32:]))
        self.assertEqual(physical.validate_container(changed), bytes(changed[32:]))

    def test_full_synthetic_coverage_and_metadata(self):
        files, manifest = self.build()
        resources = manifest['resources']
        self.assertEqual(len(resources), 8)
        self.assertEqual(b''.join(physical.validate_container(files[x['file']]) for x in resources), self.program)
        self.assertEqual([r['source_rom_offset'] for r in resources], list(range(0, 0x800000, 0x100000)))
        self.assertEqual(manifest['counts'], dict(resources=8, total_payload_bytes=0x800000, total_container_bytes=0x800100))
        self.assertEqual(manifest['legacy_kind2_tail_coverage']['bytes'], 112)
        self.assertEqual(len(manifest['legacy_kind2_tail_coverage']['ranges']), 7)
        self.assertEqual(json.loads(files['manifest.json']), manifest)
        for row in resources:
            self.assertIsNone(row['cpu_binding'])
            self.assertEqual(row['header_cpu_field'], 0xffffffff)
            self.assertEqual(row['id'], 'physical-program:%08x' % row['source_rom_offset'])
            self.assertEqual(physical.sha(files[row['file']]), row['sha256'])
            self.assertEqual(physical.sha(files[row['file']][32:]), row['payload_sha256'])

    def test_deterministic_regeneration(self):
        self.assertEqual(self.build(), self.build())

    def test_coverage_gap_overlap_reorder_and_missing_tail_rejected(self):
        _, manifest = self.build()
        for action in ('gap', 'overlap', 'reorder', 'missing'):
            resources = copy.deepcopy(manifest['resources'])
            if action == 'gap':resources[1]['source_rom_offset'] += 1
            elif action == 'overlap':resources[1]['source_rom_offset'] -= 1
            elif action == 'reorder':resources[0], resources[1] = resources[1], resources[0]
            else:resources.pop()
            with self.subTest(action=action), self.assertRaises(ValueError):physical.coverage(resources)

    def test_source_hash_size_and_byte_order_checked(self):
        bad = bytearray(self.program);bad[0] ^= 1
        for p, s in ((bytes(bad), self.source), (self.program, dict(self.source, sha256='0'*64)),
                     (self.program[:-1], dict(self.source, size=len(self.program)-1)),
                     (self.program, dict(self.source, byte_order='little'))):
            with self.subTest(source=s), self.assertRaises(ValueError):self.build([(p, s)])

    def test_changed_source_between_reads_rejected(self):
        changed = bytearray(self.program);changed[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.build([(self.program, self.source), (bytes(changed), self.source)])

    def test_changed_source_stat_rejected(self):
        with patch.object(physical, 'source_snapshot', side_effect=[('first', self.digest), ('changed', self.digest)]):
            with self.assertRaisesRegex(ValueError, 'hash/stat changed'):self.build()


if __name__ == '__main__':
    unittest.main()
