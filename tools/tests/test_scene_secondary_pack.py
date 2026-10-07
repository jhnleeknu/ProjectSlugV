"""Synthetic interval/format tests, not modified-ROM execution."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pack_scene_secondary import merge_intervals,wrap,validate_container,build
from inventory_scene_secondary import column_candidates

class SceneSecondaryPackTests(unittest.TestCase):
    def test_self_relative_signed_offsets_and_alias(self):
        program=bytearray(0x200040)
        struct.pack_into('>4H',program,0x200020,0xfff0,0xffee,8,10)
        candidates=column_candidates(program,0x200020,2,1)
        rows=candidates['columns']
        self.assertEqual(candidates['errors'],[])
        self.assertEqual([r['signed_offset']for r in rows],[-16,-18,8,10])
        self.assertEqual([r['cell_start_cpu_address']for r in rows],[0x200010,0x200010,0x20002c,0x200030])
        self.assertEqual(rows[0]['identical_cell_window_column_indices'],[1])
        self.assertEqual(rows[1]['identical_cell_window_column_indices'],[0])

    def test_column_candidate_bounds_diagnostics(self):
        program=bytearray(0x200010)
        struct.pack_into('>2H',program,0x200000,0xfffe,0)
        result=column_candidates(program,0x200000,1,1)
        self.assertEqual(result['status'],'unsupported_bounds')
        self.assertFalse(result['columns'][0]['bounds_valid'])
        self.assertEqual(result['errors'][0]['error'],'cell_window_outside_or_unaligned_bank2')
        self.assertEqual(column_candidates(program,0x2ffff0,1,1)['errors'][0]['error'],'offset_word_outside_or_unaligned_bank2')

    def test_merge_overlap_adjacency_duplicates_keep_holes(self):
        self.assertEqual(merge_intervals([(0x200008,0x200010),(0x200000,0x200008),(0x200004,0x20000c),(0x200000,0x200008),(0x200014,0x200018)]),[(0x200000,0x200010),(0x200014,0x200018)])

    def test_invalid_intervals(self):
        for start,end in ((0x200000,0x200000),(0x200004,0x200002),(0x200001,0x200006),(0x1ffffe,0x200002),(0x2fffee,0x2ffff2)):
            with self.assertRaises(ValueError):merge_intervals([(start,end)])

    def test_kind2_bank2_header_crc(self):
        data=b'\x12\x34\xab\xcd';packed=wrap(data,0x200010)
        self.assertEqual(struct.unpack('<4s7I',packed[:32])[:6],(b'MS5D',1,2,0x200010,0x200010,4))
        self.assertEqual(validate_container(packed,0x200010),data)
        bad=bytearray(packed);bad[-1]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):validate_container(bad,0x200010)

    def test_empty_truncated_wrong_mapping(self):
        with self.assertRaises(ValueError):wrap(b'',0x200000)
        packed=wrap(bytes(4),0x200000)
        for bad in (packed[:31],packed[:-1]):
            with self.assertRaises(ValueError):validate_container(bad,0x200000)
        bad=bytearray(packed);struct.pack_into('<I',bad,16,0x300000)
        with self.assertRaises(ValueError):validate_container(bad,0x200000)

    def test_sentinel_only_preserves_root_and_lookup(self):
        program=bytearray(0x200030);program[0x200010:0x200014]=b'abcd';program[0x200020:0x200024]=b'\xff'*4
        report=dict(root=dict(cpu_address=0x200010),column_bounds_error_count=0,descriptors=[dict(descriptor_cpu_address=2,secondary_selector_word=1,lookup_cpu_address=0x200020,column_candidates=dict(status='sentinel'))])
        files,rows=build(program,report)
        self.assertEqual([r['payload_size']for r in rows],[4,4]);self.assertEqual(len(files),2)
        with self.assertRaises(ValueError):build(program[:0x200022],report)

    def test_bounds_error_refuses_build(self):
        with self.assertRaises(ValueError):build(bytes(4),dict(root=dict(cpu_address=0x200010),column_bounds_error_count=1,descriptors=[]))

if __name__=='__main__':unittest.main()
