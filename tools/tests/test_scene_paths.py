"""Synthetic bytearray syntax tests only; no modified-ROM native execution."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inventory_scene_paths import walk

class ScenePathTests(unittest.TestCase):
    def conditional(self,opcode,target):
        return struct.pack('>5HI',opcode,2,3,4,5,target)

    def test_all_conditional_types_follow_both_edges(self):
        for opcode in (8,12,16,20):
            program=bytearray(64)
            program[2:16]=self.conditional(opcode,32)
            program[16:18]=b'\xff\xff';program[32:34]=b'\x80\x00'
            result=walk(program,2)
            self.assertEqual(result['errors'],[])
            self.assertEqual([r['cpu_address']for r in result['rows']],[2,16,32])
            self.assertEqual({(e['kind'],e['to_cpu_address'])for e in result['edges']},{('sequential',16),('branch',32)})
            row=result['rows'][0]
            self.assertEqual((row['condition_offset_word'],row['flags_word'],row['word_at_operand_4'],row['word_at_operand_6']),(2,3,4,5))

    def test_cycle_stops_at_visited_cursor(self):
        program=bytearray(18);program[2:16]=self.conditional(8,2);program[16:18]=b'\xff\xff'
        result=walk(program,2)
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['reachable_row_count'],2)
        self.assertEqual(result['cycle_edges'],[{'from_cpu_address':2,'to_cpu_address':2,'kind':'branch'}])

    def test_branch_inside_operand_is_overlap_error(self):
        program=bytearray(18);program[2:16]=self.conditional(8,4);program[16:18]=b'\xff\xff'
        result=walk(program,2)
        self.assertIn('overlapping_instruction',[e['error']for e in result['errors']])

    def test_payload_lengths_and_descriptor_fields(self):
        program=bytearray(2)+struct.pack('>H2H',0,1,2)+struct.pack('>H4HI',4,7,9,11,13,0x10d356)+struct.pack('>H3H',24,1,2,3)+struct.pack('>H2H',28,4,5)+b'\xff\xff'
        result=walk(program,2)
        self.assertEqual(result['errors'],[])
        self.assertEqual([r['size']for r in result['rows']],[6,14,8,6,2])
        row=result['rows'][1]
        self.assertEqual((row['map_selector_word'],row['secondary_selector_word'],row['width_word'],row['height_word'],row['column_pointer_long']),(7,9,11,13,0x10d356))
        self.assertEqual(result['descriptor_addresses'],[10])

    def test_truncated_opcode_and_operand(self):
        for program,expected in ((bytes(3),'truncated_opcode'),(bytes(2)+b'\x00\x04\x00','truncated_command')):
            self.assertEqual(walk(program,2)['errors'][0]['error'],expected)
        program=bytearray(0x100000);program[-2:]=b'\x00\x04'
        self.assertEqual(walk(program,0xffffe)['errors'][0]['error'],'truncated_command')

    def test_long_sequential_path_uses_no_python_recursion(self):
        program=bytes(2)+struct.pack('>H2H',0,0,0)*1500+b'\xff\xff'
        result=walk(program,2)
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['reachable_row_count'],1501)

    def test_odd_outside_and_unknown(self):
        for address in (1,-2,0x100000):
            self.assertEqual(walk(bytes(16),address)['errors'][0]['error'],'unaligned_or_outside_fixed_ROM')
        for opcode in (1,0x20,0x7fff):
            self.assertEqual(walk(bytes(2)+struct.pack('>H',opcode),2)['errors'][0]['error'],'unknown_opcode')

if __name__=='__main__':unittest.main()
