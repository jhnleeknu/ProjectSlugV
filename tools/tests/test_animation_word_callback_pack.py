"""Synthetic word-callback prefix packing; no extracted ROM bytes in tests."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from tools import pack_animation_word_callback as word


REAL_PREFIX_SHA = word.SPEC['container_sha256']


class AnimationWordCallbackPackTests(unittest.TestCase):
    def setUp(self):
        specs = [dict(s) for s in word.SPECS]
        program = bytearray(0x100000)
        self.payloads = []
        for n,spec in enumerate(specs):
            payload = bytes((i*29+7+n*13)&255 for i in range(spec['end']-spec['cpu']))
            packed = struct.pack('<4s7I',b'MS5D',1,1,spec['cpu'],spec['cpu'],len(payload),zlib.crc32(payload),0)+payload
            spec.update(payload_sha256=hashlib.sha256(payload).hexdigest(),crc32=zlib.crc32(payload),
                        container_sha256=hashlib.sha256(packed).hexdigest())
            program[spec['cpu']:spec['end']] = payload
            self.payloads.append(payload)
        spec = specs[0]
        self.payload = self.payloads[0]
        evidence = bytearray()
        for cpu,hexbytes,_ in word.EVIDENCE:
            program[cpu:cpu+len(hexbytes)//2] = bytes.fromhex(hexbytes)
        span = word.EVIDENCE_SPAN
        self.evidence_sha = hashlib.sha256(bytes(program[span[0]:span[1]])).hexdigest()
        self.program = bytes(program)
        self.digest = word.sha(self.program)
        self.source = dict(path='synthetic.bin',size=len(self.program),byte_order='big',sha256=self.digest)
        self.spec = spec;self.specs = specs
        for p in (patch.object(word,'SPEC',spec),patch.object(word,'SPECS',tuple(specs)),
                  patch.object(word,'EVIDENCE_SHA256',self.evidence_sha)):
            p.start();self.addCleanup(p.stop)
        self.root = Path(tempfile.mkdtemp());self.addCleanup(lambda: __import__('shutil').rmtree(self.root))
        for name in ('tools/pack_animation_word_callback.py','tools/disassemble_program.py',word.CONTRACT):
            (self.root/name).parent.mkdir(parents=True,exist_ok=True);(self.root/name).write_bytes(name.encode())

    def build(self,responses=None,program=None):
        program = program or self.program
        source = dict(self.source,size=len(program),sha256=word.sha(program))
        with patch.object(word,'SOURCE_SHA256',word.sha(program)),patch.object(word,'load_verified_program',
                side_effect=responses or [(program,source),(program,source)]):
            return word.build(self.root)

    def test_exact_header_and_roundtrip(self):
        packed = word.wrap(self.payload)
        self.assertEqual(struct.unpack_from('<4s7I',packed),
            (b'MS5D',1,1,0x42500,0x42500,len(self.payload),zlib.crc32(self.payload),0))
        self.assertEqual(word.validate_container(packed),self.payload)
        self.assertEqual(len(self.payload),0x26c)
        self.assertEqual(len(packed),652)

    def test_boundary_operand_headers_roundtrip_and_pins(self):
        for spec,payload in zip(self.specs[1:],self.payloads[1:]):
            packed = word.wrap(payload,spec['cpu'])
            self.assertEqual(struct.unpack_from('<4s7I',packed),
                (b'MS5D',1,1,spec['cpu'],spec['cpu'],1024,zlib.crc32(payload),0))
            self.assertEqual((len(payload),len(packed)),(1024,1056))
            self.assertEqual(word.validate_container(packed,spec['cpu']),payload)
            with self.assertRaisesRegex(ValueError,'different window'):
                word.validate_container(packed,self.spec['cpu'])
            with self.assertRaises(ValueError):word.wrap(payload,self.spec['cpu'])
            for changed in (payload[:-1],payload+b'\0',bytes([payload[0]^1])+payload[1:]):
                with self.assertRaises(ValueError):word.wrap(changed,spec['cpu'])
            bad = bytearray(packed);bad[100] ^= 1
            with self.assertRaisesRegex(ValueError,'CRC'):word.validate_container(bad)
            struct.pack_into('<I',bad,24,zlib.crc32(bad[32:]))
            with self.assertRaisesRegex(ValueError,'Pinned payload'):word.validate_container(bad)
        with self.assertRaisesRegex(ValueError,'Unknown'):word.wrap(self.payloads[1],0x1000)

    def test_real_pins_are_independent_and_consistent(self):
        real = word.OPERAND_SPECS
        self.assertEqual([(s['cpu'],s['end'],s['file']) for s in real],
            [(0,0x400,'operands_000000.ms5d'),(0xffc00,0x100000,'operands_0ffc00.ms5d')])
        self.assertEqual(len({s['container_sha256'] for s in word.SPECS}),3)
        self.assertEqual(REAL_PREFIX_SHA,'3d5d1bd37897a4cfaa69482c01aaf40c06fafb07877be018db7db4f7c9cb0082')

    def test_header_fields_and_lengths_rejected(self):
        packed = word.wrap(self.payload)
        for offset in (0,4,8,12,16,20,28):
            changed = bytearray(packed);changed[offset] ^= 1
            with self.subTest(offset=offset),self.assertRaises(ValueError):word.validate_container(changed)
        for changed in (packed[:20],packed[:-1],packed+b'\0'):
            with self.assertRaises(ValueError):word.validate_container(changed)

    def test_crc_and_recomputed_crc_do_not_bypass_pins(self):
        packed = bytearray(word.wrap(self.payload));packed[40] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'):word.validate_container(packed)
        struct.pack_into('<I',packed,24,zlib.crc32(packed[32:]))
        with self.assertRaisesRegex(ValueError,'Pinned payload'):word.validate_container(packed)

    def test_payload_extent_and_independent_pins(self):
        for changed in (self.payload[:-1],self.payload+b'\0',bytes([self.payload[0]^1])+self.payload[1:]):
            with self.assertRaises(ValueError):word.wrap(changed)
        with patch.dict(self.spec,crc32=0),self.assertRaisesRegex(ValueError,'CRC'):word.wrap(self.payload)
        with patch.dict(self.spec,container_sha256='0'*64),self.assertRaisesRegex(ValueError,'container SHA'):
            word.wrap(self.payload)
        with self.assertRaises(ValueError):word.wrap(self.payload,0)

    def test_metadata_mapping_roles_and_nonoverlap(self):
        files,manifest = self.build()
        self.assertEqual((files,manifest),self.build())
        self.assertEqual(json.loads(files['manifest.json']),manifest)
        self.assertEqual(set(files),{'prefix_042500.ms5d','operands_000000.ms5d','operands_0ffc00.ms5d','manifest.json'})
        self.assertEqual([x['resource_role'] for x in manifest['resources']],
            [word.PREFIX_ROLE,word.OPERAND_ROLE,word.OPERAND_ROLE])
        self.assertEqual(manifest['counts']['resources'],3)
        self.assertEqual((manifest['counts']['boundary_operand_resources'],manifest['counts']['total_payload_bytes']),
            (2,0x26c+2048))
        for res,payload in zip(manifest['resources'],self.payloads):
            self.assertEqual(files[res['file']],word.wrap(payload,res['source_cpu_address']))
            self.assertEqual(res['sha256'],word.sha(files[res['file']]))
        for res in manifest['resources'][1:]:
            op = res['roles'][0]
            self.assertEqual((op['index_count'],op['stride'],op['long_slots'],op['read_size']),(256,4,256,4))
            self.assertIn('not a known naturally used logical table',op['natural_use'])
        self.assertIn('BIOS/cart vector selection is not modeled',manifest['resources'][1]['roles'][0]['cartridge_view'])
        self.assertIn('canonical cartridge ROM view',manifest['scope'])
        self.assertIn('not known naturally used logical tables',manifest['scope'])
        self.assertNotIn('operands_06431a.ms5d',files)
        self.assertEqual(manifest['source'],self.source)
        r = manifest['resources'][0]
        self.assertEqual((r['source_cpu_address'],r['source_rom_offset'],r['end_cpu_address_exclusive']),(0x42500,0x42500,0x4276c))
        self.assertLessEqual(r['end_cpu_address_exclusive'],0x4276c)
        role = r['roles'][0]
        self.assertEqual((role['full_raw_span_start'],role['full_raw_span_end_exclusive']),(0x42500,0x52500))
        self.assertEqual((role['distinct_long_slots'],role['selectors_per_slot'],role['prefix_long_slots']),(16384,4,155))
        self.assertEqual((role['second_selector_span_start'],role['second_selector_span_end_exclusive']),(0x4276c,0x5276c))
        self.assertIn('not a logical function table',role['scope'])
        self.assertIn('natural reachability',manifest['scope'])
        self.assertEqual(manifest['provenance']['inputs']['tools/pack_animation_word_callback.py'],
                         word.sha(b'tools/pack_animation_word_callback.py'))
        self.assertEqual(len(manifest['provenance']['instruction_evidence']['instructions']),len(word.EVIDENCE))

    def test_source_verification_failures(self):
        with self.assertRaisesRegex(ValueError,'Unsupported canonical source'):
            with patch.object(word,'load_verified_program',return_value=(self.program,self.source)):word.build(self.root)
        bad = dict(self.source,byte_order='little')
        with self.assertRaisesRegex(ValueError,'metadata'):
            self.build([(self.program,bad),(self.program,bad)])
        other = bytearray(self.program);other[0x4a314] ^= 1
        with self.assertRaisesRegex(ValueError,'3c instruction|span SHA'):self.build(program=bytes(other))
        other = bytearray(self.program);other[0x42500] ^= 1
        with self.assertRaisesRegex(ValueError,'Pinned payload'):self.build(program=bytes(other))

    def test_source_or_input_change_during_pack_and_overlap(self):
        changed = bytearray(self.program);changed[0] ^= 1
        with self.assertRaisesRegex(ValueError,'changed during packing'):
            self.build([(self.program,self.source),(bytes(changed),self.source)])
        with patch.dict(self.spec,end=0x4276d),self.assertRaisesRegex(ValueError,'overlap'):self.build()
        for index,patches in ((1,dict(end=0x401)),(2,dict(cpu=0xffbfc)),(1,dict(end=0x400,cpu=0x42504))):
            with self.subTest(index=index,patches=patches),patch.dict(self.specs[index],**patches),\
                 self.assertRaises(ValueError):self.build()
        with patch.dict(self.specs[2],cpu=0x6431a,end=0x6471a),self.assertRaisesRegex(ValueError,'overlap'):self.build()
        with patch.dict(self.specs[2],cpu=0x4276c,end=0x42b6c),self.assertRaisesRegex(ValueError,'overlap'):self.build()
        with patch.dict(self.specs[2],file=self.specs[1]['file']),self.assertRaisesRegex(ValueError,'Duplicate'):self.build()
        other = bytearray(self.program);other[0x10] ^= 1
        with self.assertRaisesRegex(ValueError,'Pinned payload'):self.build(program=bytes(other))
        other = bytearray(self.program);other[0xfffff] ^= 1
        with self.assertRaisesRegex(ValueError,'Pinned payload'):self.build(program=bytes(other))
        with patch.object(word,'load_verified_program',side_effect=[(self.program,self.source),(self.program,self.source)]),\
             patch.object(word,'SOURCE_SHA256',self.digest):
            real = Path.read_bytes
            seen = {'n':0}
            def flip(path):
                data = real(path)
                if path.name == Path(word.CONTRACT).name:
                    seen['n'] += 1
                    if seen['n'] == 2:return data+b'!'
                return data
            with patch.object(Path,'read_bytes',flip),self.assertRaisesRegex(ValueError,'Provenance input'):
                word.build(self.root)


if __name__ == '__main__':
    unittest.main()
