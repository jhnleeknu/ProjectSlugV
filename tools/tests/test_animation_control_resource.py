"""Synthetic animation control windows; no extracted ROM bytes in tests."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

from tools import pack_animation_control as control


class AnimationControlResourceTests(unittest.TestCase):
    def setUp(self):
        self.specs = copy.deepcopy(control.SPECS)
        self.payloads = {}
        program = bytearray(0x64836+16)
        for number,spec in enumerate(self.specs):
            payload = bytes((i*13+number*71+17)&255 for i in range(spec['end']-spec['cpu']))
            packed = struct.pack('<4s7I',b'MS5D',1,1,spec['cpu'],spec['cpu'],len(payload),zlib.crc32(payload),0)+payload
            spec.update(payload_sha256=hashlib.sha256(payload).hexdigest(),crc32=zlib.crc32(payload),
                        container_sha256=hashlib.sha256(packed).hexdigest())
            self.payloads[spec['cpu']] = payload
            program[spec['cpu']:spec['end']] = payload
        self.program = bytes(program)
        self.digest = control.sha(self.program)
        self.source = dict(path='synthetic.bin',size=len(self.program),byte_order='big',sha256=self.digest)
        p = patch.object(control,'SPECS',self.specs);p.start();self.addCleanup(p.stop)

    def build(self,responses=None):
        with patch.object(control,'SOURCE_SHA256',self.digest),patch.object(control,'load_verified_program',
                side_effect=responses or [(self.program,self.source),(self.program,self.source)]):
            return control.build(Path('.'))

    def test_exact_header_and_roundtrip_both_windows(self):
        for spec in self.specs:
            raw = self.payloads[spec['cpu']];packed = control.wrap(raw,spec['cpu'])
            self.assertEqual(struct.unpack_from('<4s7I',packed),
                (b'MS5D',1,1,spec['cpu'],spec['cpu'],len(raw),zlib.crc32(raw),0))
            self.assertEqual(control.validate_container(packed),raw)
            self.assertEqual(len(packed),len(raw)+32)

    def test_header_fields_and_lengths_rejected(self):
        packed = control.wrap(self.payloads[self.specs[0]['cpu']],self.specs[0]['cpu'])
        for offset in (0,4,8,12,16,20,28):
            changed = bytearray(packed);changed[offset] ^= 1
            with self.subTest(offset=offset),self.assertRaises(ValueError):control.validate_container(changed)
        for changed in (packed[:20],packed[:-1],packed+b'\0'):
            with self.assertRaises(ValueError):control.validate_container(changed)

    def test_crc_and_recomputed_crc_do_not_bypass_pins(self):
        spec=self.specs[0];packed=bytearray(control.wrap(self.payloads[spec['cpu']],spec['cpu']))
        packed[40] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'):control.validate_container(packed)
        struct.pack_into('<I',packed,24,zlib.crc32(packed[32:]))
        with self.assertRaisesRegex(ValueError,'Pinned payload'):control.validate_container(packed)

    def test_payload_extent_and_independent_pins(self):
        spec=self.specs[0];raw=self.payloads[spec['cpu']]
        for changed in (raw[:-1],raw+b'\0',bytes([raw[0]^1])+raw[1:]):
            with self.assertRaises(ValueError):control.wrap(changed,spec['cpu'])
        with patch.dict(spec,crc32=0):
            with self.assertRaisesRegex(ValueError,'CRC'):control.wrap(raw,spec['cpu'])
        with patch.dict(spec,container_sha256='0'*64):
            with self.assertRaisesRegex(ValueError,'container SHA'):control.wrap(raw,spec['cpu'])
        with self.assertRaises(ValueError):control.wrap(raw,0)

    def test_deterministic_metadata_counts_and_mapping(self):
        files,manifest=self.build()
        self.assertEqual((files,manifest),self.build())
        self.assertEqual(json.loads(files['manifest.json']),manifest)
        self.assertEqual(manifest['source'],self.source)
        self.assertEqual(manifest['counts'],dict(resources=2,total_payload_bytes=66844,
            total_container_bytes=66908,opcode0c_selector_inputs=65536,opcode0c_distinct_word_positions=32768,
            opcode14_callback_positions=256,known_operand_bases=8))
        self.assertEqual(set(files),{s['file'] for s in self.specs}|{'manifest.json'})
        for spec,r in zip(self.specs,manifest['resources']):
            self.assertEqual(r['source_cpu_address'],spec['cpu'])
            self.assertEqual(r['source_rom_offset'],spec['cpu'])
            self.assertEqual(r['end_cpu_address_exclusive'],spec['end'])
            self.assertEqual(r['end_rom_offset_exclusive'],spec['end'])
            self.assertEqual(r['payload_sha256'],spec['payload_sha256'])
            self.assertEqual(r['sha256'],spec['container_sha256'])
            self.assertIn('not a logical table',r['scope'])
        self.assertEqual(set(manifest['provenance']['inputs']),
            {'tools/pack_animation_control.py','tools/disassemble_program.py',control.CONTRACT})

    def test_role_domains_and_operand_union(self):
        _,m=self.build();branch,dispatch=m['resources'][0]['roles']
        self.assertEqual((branch['raw_span_start'],branch['raw_span_end_exclusive']),(0x4276c,0x5276c))
        offsets={((s*2)&65535)-65536 if (s*2)&32768 else (s*2)&65535 for s in range(65536)}
        self.assertEqual(len(offsets),32768)
        self.assertEqual((min(offsets),max(offsets)),(-32768,32766))
        self.assertEqual((dispatch['raw_span_start'],dispatch['raw_span_end_exclusive']),(0x4a500,0x4a900))
        roles=m['resources'][1]['roles'];self.assertEqual(len(roles),8)
        for i,r in enumerate(roles):
            self.assertEqual(r['source_cpu_address'],control.OPERAND_BASES[i])
            self.assertEqual(r['source_rom_offset'],control.OPERAND_BASES[i])
            self.assertEqual(r['raw_span_end_exclusive'],control.OPERAND_BASES[i]+1024)
            self.assertEqual(r['known_callback_selector'],0x1e if i<4 else 0x1d)
        self.assertEqual(min(r['raw_span_start'] for r in roles),self.specs[1]['cpu'])
        self.assertEqual(max(r['raw_span_end_exclusive'] for r in roles),self.specs[1]['end'])

    def test_source_hash_and_metadata_rejected(self):
        altered=bytearray(self.program);altered[0]^=1
        for program,source in ((bytes(altered),self.source),(self.program,dict(self.source,sha256='0'*64)),
                (self.program,dict(self.source,size=len(self.program)-1)),
                (self.program,dict(self.source,byte_order='little'))):
            with self.subTest(source=source),self.assertRaisesRegex(ValueError,'source'):
                self.build([(program,source)])

    def test_source_valid_hash_cannot_replace_payload_pin(self):
        altered=bytearray(self.program);altered[self.specs[0]['cpu']]^=1
        digest=control.sha(altered)
        with patch.object(control,'SOURCE_SHA256',digest),patch.object(control,'load_verified_program',
                return_value=(bytes(altered),dict(self.source,sha256=digest))):
            with self.assertRaisesRegex(ValueError,'Pinned payload'):control.build(Path('.'))

    def test_source_or_metadata_changes_during_build_rejected(self):
        altered=bytearray(self.program);altered[-1]^=1
        for program,source in ((bytes(altered),self.source),(self.program,dict(self.source,path='changed.bin'))):
            with self.assertRaisesRegex(ValueError,'changed during packing'):
                self.build([(self.program,self.source),(program,source)])

    def test_overlapping_window_spec_rejected(self):
        with patch.dict(self.specs[1],cpu=self.specs[0]['cpu']+2):
            with self.assertRaisesRegex(ValueError,'nonoverlapping'):self.build()


if __name__ == '__main__':unittest.main()
