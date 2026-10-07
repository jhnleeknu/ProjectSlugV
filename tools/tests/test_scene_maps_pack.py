"""Synthetic MS5D/map/path checks; no ROM patch execution."""
from pathlib import Path
import hashlib
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pack_scene_maps import wrap,validate_container,map_payload,path_payload,validate_references
from inventory_scene_paths import walk

class SceneMapsPackTests(unittest.TestCase):
    def test_empty_payload_rejected(self):
        for cpu,rom,kind in ((2,2,1),(0x200100,0x300100,2)):
            with self.assertRaisesRegex(ValueError,'Empty'):wrap(b'',cpu,rom,kind)

    def test_reference_metadata_root_membership_and_duplicates(self):
        program=bytes(2)+struct.pack('>HHI',0x24,3,20)
        ref=dict(command_cpu_address=2,selector_word=3,pointer_long=20,operand_raw_hex=program[4:10].hex())
        paths=dict(paths=[dict(root_cpu_address=20,references=[ref])],references=[ref])
        validate_references(program,paths)
        import copy
        for change in ('selector','pointer','duplicate','wrongroot','pathref'):
            bad=copy.deepcopy(paths)
            if change=='selector':bad['references'][0]['selector_word']=4
            elif change=='pointer':bad['references'][0]['pointer_long']=22;bad['paths'][0]['root_cpu_address']=22
            elif change=='duplicate':bad['paths'].append(copy.deepcopy(bad['paths'][0]))
            elif change=='wrongroot':bad['paths'][0]['root_cpu_address']=24
            else:bad['paths'][0]['references'][0]['pointer_long']=22
            with self.assertRaises(ValueError):validate_references(program,bad)

    def test_fixed_and_bank_container_crc(self):
        for cpu,rom,kind in ((2,2,1),(0x200100,0x300100,2)):
            payload=b'\x01\x02\x03\x04';packed=wrap(payload,cpu,rom,kind)
            self.assertEqual(validate_container(packed,cpu,rom,kind),payload)
            damaged=bytearray(packed);damaged[-1]^=1
            with self.assertRaisesRegex(ValueError,'CRC'):validate_container(damaged,cpu,rom,kind)
            with self.assertRaises(ValueError):validate_container(packed[:-1],cpu,rom,kind)
            with self.assertRaises(ValueError):validate_container(packed[:31],cpu,rom,kind)

    def test_bad_mapping_and_pvc_tail(self):
        for cpu,rom,kind in ((2,4,1),(0x200100,0x200100,2),(0x2fffec,0x3fffec,2),(3,3,1),(2,2,3)):
            with self.assertRaises(ValueError):wrap(bytes(8),cpu,rom,kind)

    def map_fixture(self):
        program=bytearray(0x300120);raw=struct.pack('>HH',2,3)+bytes(range(24));program[0x300100:0x30011c]=raw
        entry=dict(source_cpu_address=0x200100,source_rom_offset=0x300100,width=2,height=3,raw_span_size=28,sha256=hashlib.sha256(raw).hexdigest(),end_cpu_address=0x20011c,end_rom_offset=0x30011c)
        return program,entry,raw

    def test_map_preserves_full_header_cells(self):
        program,entry,raw=self.map_fixture();self.assertEqual(map_payload(program,entry),raw)

    def test_map_wrong_extent_metadata_and_truncation(self):
        program,entry,raw=self.map_fixture()
        for field,value in (('width',3),('raw_span_size',24),('end_rom_offset',0x300118),('source_rom_offset',0x300102),('sha256','0'*64)):
            bad=dict(entry);bad[field]=value
            with self.assertRaises(ValueError):map_payload(program,bad)
        with self.assertRaises(ValueError):map_payload(program[:0x300110],entry)

    def test_path_exact_terminal_and_metadata(self):
        program=bytes(2)+struct.pack('>H2H',0,1,2)+b'\xff\xff'+b'\xaa\xbb';path=walk(program,2);path['references']=[]
        self.assertEqual(path_payload(program,path),program[2:10])
        path['rows'][-1]['size']=4
        with self.assertRaises(ValueError):path_payload(program,path)

    def test_noncontiguous_branch_not_extractable(self):
        program=bytearray(34);program[2:16]=struct.pack('>5HI',8,0,0,0,0,32);program[16:18]=b'\xff\xff';program[32:34]=b'\xff\xff'
        with self.assertRaisesRegex(ValueError,'contiguous|terminal'):path_payload(program,walk(program,2))

if __name__=='__main__':unittest.main()
