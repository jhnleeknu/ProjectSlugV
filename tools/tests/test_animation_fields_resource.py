"""Synthetic MS5A fixtures; no extracted ROM script bytes are stored here."""
import copy
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

from tools import pack_animation_fields as fields


class AnimationFieldsResourceTests(unittest.TestCase):
    def setUp(self):
        self.spec = copy.deepcopy(fields.SPEC)
        data = bytearray(self.spec['end']+16)
        data[fields.CALLER:fields.CALLER+len(fields.CALLER_RAW)] = fields.CALLER_RAW
        for number,(at,opcode) in enumerate(fields.COMMANDS):
            if opcode == 0x0c:
                raw = bytes((opcode,255))+struct.pack('>HI',0x2f,0x3e832)
            elif opcode == 0x18:
                raw = bytes((opcode,0x35 if at<0x3e832 else 0x49))+struct.pack('>H',0x34)
            elif opcode == 4:
                raw = bytes((4,0x81,number,0x29))+struct.pack('>I',0xdead0000+number)
            elif opcode == 0:
                raw = bytes((0,1))
            else:
                raw = bytes((8,0x93))+struct.pack('>I',0x3e810 if at<0x3e832 else 0x3e832)
            data[at:at+len(raw)] = raw
        self.program = bytes(data)
        self.payload = self.program[self.spec['cpu']:self.spec['end']]
        self.spec.update(payload_sha256=fields.sha(self.payload),crc32=zlib.crc32(self.payload))
        self.packed = struct.pack('<4s7I',b'MS5A',1,1,self.spec['cpu'],self.spec['cpu'],
                                  len(self.payload),self.spec['crc32'],0)+self.payload
        self.spec['container_sha256'] = fields.sha(self.packed)
        self.digest = fields.sha(self.program)
        self.source = dict(path='synthetic.bin',size=len(self.program),byte_order='big',sha256=self.digest)
        p = patch.object(fields,'SPEC',self.spec)
        p.start();self.addCleanup(p.stop)

    def build(self,responses=None):
        with patch.object(fields,'SOURCE_SHA256',self.digest),patch.object(fields,'load_verified_program',
            side_effect=responses or [(self.program,self.source),(self.program,self.source)]):
            return fields.build(Path('.'))

    def test_roundtrip_header_and_size(self):
        self.assertEqual(fields.wrap(self.payload),self.packed)
        self.assertEqual(fields.validate_container(self.packed),self.payload)
        self.assertEqual(len(self.packed),108)
        self.assertEqual(struct.unpack('<4s7I',self.packed[:32]),
            (b'MS5A',1,1,self.spec['cpu'],self.spec['cpu'],76,self.spec['crc32'],0))

    def test_header_and_extent_rejection(self):
        for at in (0,4,8,12,16,20,28):
            data=bytearray(self.packed);data[at]^=1
            with self.subTest(at=at),self.assertRaises(ValueError):fields.validate_container(data)
        for data in (self.packed[:20],self.packed[:-1],self.packed+b'\0'):
            with self.assertRaises(ValueError):fields.validate_container(data)

    def test_crc_and_recomputed_crc_cannot_bypass_pin(self):
        data=bytearray(self.packed);data[40]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):fields.validate_container(data)
        struct.pack_into('<I',data,24,zlib.crc32(data[32:]))
        with self.assertRaisesRegex(ValueError,'payload SHA'):fields.validate_container(data)

    def test_payload_and_container_pins(self):
        for payload in (self.payload[:-1],self.payload+b'\0',b'\xff'+self.payload[1:]):
            with self.assertRaises(ValueError):fields.wrap(payload)
        with patch.dict(self.spec,crc32=0):
            with self.assertRaisesRegex(ValueError,'CRC'):fields.wrap(self.payload)
        with patch.dict(self.spec,container_sha256='0'*64):
            with self.assertRaisesRegex(ValueError,'container SHA'):fields.wrap(self.payload)

    def test_commands_and_target_boundaries(self):
        payload,rows=fields.extract(self.program)
        self.assertEqual(payload,self.payload)
        self.assertEqual([(r['cpu_address'],r['opcode']) for r in rows],list(fields.COMMANDS))
        self.assertEqual(sum(r['size'] for r in rows),76)
        boundaries={r['cpu_address'] for r in rows}
        self.assertTrue(all(r['target'] in boundaries for r in rows if 'target' in r))
        self.assertEqual(rows[-1]['cpu_address']+rows[-1]['size'],0x3e854)

    def test_caller_command_branch_and_jump_rejection(self):
        for at in (fields.CALLER,0x3e808,0x3e809,0x3e80b,0x3e80f,0x3e811,0x3e813,0x3e82d+4):
            data=bytearray(self.program);data[at]^=1
            with self.subTest(at=at),self.assertRaises(ValueError):fields.extract(bytes(data))

    def test_deterministic_metadata_and_resource_mapping(self):
        files,manifest=self.build()
        self.assertEqual((files,manifest),self.build())
        self.assertEqual(manifest['counts'],dict(resources=1,commands=15,field_writes=4,
            draw_commands=4,payload_bytes=76,container_bytes=108))
        self.assertEqual(set(files),{self.spec['file'],'manifest.json'})
        r=manifest['resources'][0]
        self.assertEqual((r['source_cpu_address'],r['source_rom_offset'],r['end_cpu_address_exclusive']),
                         (0x3e808,0x3e808,0x3e854))
        self.assertEqual(manifest['caller']['call_cpu_address'],0x3d2ec)
        self.assertIn('no2c',manifest['scope'])
        self.assertEqual(set(manifest['provenance']['inputs']),
                         {'tools/pack_animation_fields.py','tools/disassemble_program.py'})

    def test_source_hash_size_and_byte_order(self):
        for values in ({'sha256':'0'*64},{'size':1},{'byte_order':'little'}):
            source=dict(self.source,**values)
            with self.subTest(values=values),self.assertRaises(ValueError):
                self.build([(self.program,source),(self.program,source)])

    def test_source_immutability_recheck(self):
        data=self.program[:-1]+b'\x01'
        with self.assertRaisesRegex(ValueError,'changed during packing'):
            self.build([(self.program,self.source),(data,self.source)])


if __name__ == '__main__':
    unittest.main()
