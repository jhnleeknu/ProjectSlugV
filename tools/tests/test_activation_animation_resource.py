"""Synthetic streams/raw LONGs only; no extracted game payload is committed."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

from tools import pack_activation_animation as pack


class ActivationAnimationResourceTests(unittest.TestCase):
    def setUp(self):
        self.raw = {
            0x48980: b''.join(bytes((4, i, 128+i, 255-i))+struct.pack('>I',0x1000+i*8)
                             for i in range(8))+b'\x28',
            0x489c2: b''.join(bytes((4, i+16, 127-i, i))+struct.pack('>I',0x2000+i*8)
                             for i in range(9))+bytes.fromhex('00010800000489c2'),
            0x48a12: b''.join(struct.pack('>I',0x10203040+i*0x010101) for i in range(256)),
        }
        specs = []
        program = bytearray(0x50000)
        for old in pack.SPECS:
            spec = old.copy(); raw = self.raw[spec['cpu']]
            program[spec['cpu']:spec['end']] = raw
            packed = struct.pack('<4s7I',spec['magic'],1,1,spec['cpu'],spec['cpu'],len(raw),zlib.crc32(raw),0)+raw
            spec.update(payload_sha256=pack.sha(raw),crc32=zlib.crc32(raw),container_sha256=pack.sha(packed))
            specs.append(spec)
        for cpu, raw in pack.inspector.CALLERS.items():
            program[cpu:cpu+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        self.program = bytes(program)
        self.source = dict(path='synthetic.bin',size=len(program),sha256=pack.sha(program),byte_order='big')
        for obj, name, value in ((pack,'SPECS',tuple(specs)),
                (pack,'SOURCE_SHA256',self.source['sha256']),
                (pack.inspector,'SOURCE_SHA256',self.source['sha256'])):
            p=patch.object(obj,name,value);p.start();self.addCleanup(p.stop)

    def build(self, responses=None):
        with patch.object(pack,'load_verified_program',side_effect=responses or
                [(self.program,self.source),(self.program,self.source)]):
            return pack.build(Path('.'))

    def test_exact_headers_pins_and_roundtrip(self):
        for spec in pack.SPECS:
            with self.subTest(cpu=spec['cpu']):
                raw=self.raw[spec['cpu']]; packed=pack.wrap(raw,spec['cpu'])
                self.assertEqual(pack.validate_container(packed),raw)
                self.assertEqual(pack.sha(packed),spec['container_sha256'])
                self.assertEqual(struct.unpack_from('<4s7I',packed),
                    (spec['magic'],1,1,spec['cpu'],spec['cpu'],len(raw),zlib.crc32(raw),0))
                self.assertEqual(len(packed),len(raw)+32)

    def test_header_fields_and_lengths(self):
        for spec in pack.SPECS:
            packed=pack.wrap(self.raw[spec['cpu']],spec['cpu'])
            for at in (0,4,8,12,16,20,28):
                bad=bytearray(packed);bad[at]^=1
                with self.subTest(cpu=spec['cpu'],field=at),self.assertRaises(ValueError):
                    pack.validate_container(bad)
            for bad in (packed[:31],packed[:-1],packed+b'\0'):
                with self.assertRaises(ValueError):pack.validate_container(bad)

    def test_crc_and_recomputed_crc_mutation(self):
        for spec in pack.SPECS:
            bad=bytearray(pack.wrap(self.raw[spec['cpu']],spec['cpu']));bad[36]^=1
            with self.assertRaisesRegex(ValueError,'CRC'):pack.validate_container(bad)
            struct.pack_into('<I',bad,24,zlib.crc32(bad[32:]))
            with self.assertRaisesRegex(ValueError,'payload SHA'):pack.validate_container(bad)
            bad=bytearray(pack.wrap(self.raw[spec['cpu']],spec['cpu']));bad[24]^=1
            with self.assertRaisesRegex(ValueError,'CRC'):pack.validate_container(bad)

    def test_independent_pins_and_extents(self):
        for spec in pack.SPECS:
            raw=self.raw[spec['cpu']]
            for bad in (raw[:-1],raw+b'\0',raw[:-1]+bytes([raw[-1]^1])):
                with self.assertRaises(ValueError):pack.wrap(bad,spec['cpu'])
            for name,value in (('crc32',spec['crc32']^1),('container_sha256','0'*64)):
                changed=[s.copy() for s in pack.SPECS]
                next(s for s in changed if s['cpu']==spec['cpu'])[name]=value
                with patch.object(pack,'SPECS',tuple(changed)),self.assertRaises(ValueError):
                    pack.wrap(raw,spec['cpu'])
        with self.assertRaises(ValueError):pack.wrap(b'x',0)

    def test_deterministic_metadata_and_exact_consumed_spans(self):
        files,manifest=self.build()
        self.assertEqual((files,manifest),self.build())
        self.assertEqual(json.loads(files['manifest.json']),manifest)
        self.assertEqual(manifest['source'],self.source)
        self.assertEqual(manifest['counts'],dict(resources=3,scripts=2,draw_commands=17,
            raw_long_positions=256,total_payload_bytes=1169,total_container_bytes=1265))
        for spec,resource in zip(pack.SPECS,manifest['resources']):
            self.assertEqual(resource['source_cpu_address'],spec['cpu'])
            self.assertEqual(resource['source_rom_offset'],spec['cpu'])
            self.assertEqual(resource['end_cpu_address_exclusive'],spec['end'])
            self.assertEqual(resource['end_rom_offset_exclusive'],spec['end'])
            self.assertEqual(resource['payload_sha256'],spec['payload_sha256'])
            self.assertEqual(resource['sha256'],pack.sha(files[spec['file']]))
            self.assertEqual(resource['payload_crc32'],spec['crc32'])
        a,b,table=manifest['resources']
        self.assertEqual(len(files[a['file']]),97)
        self.assertEqual(a['commands'][-1]['opcode'],0x28)
        self.assertEqual(a['excluded_padding']['cpu_address'],0x489c1)
        self.assertEqual(a['excluded_padding']['classification'],
            'outside consumed stream; inferred inter-stream alignment padding')
        self.assertEqual(a['identifier_binding']['local_group_word'],0xea)
        self.assertEqual(b['identifier_binding']['status'],'unresolved')
        self.assertIsNone(b['identifier_binding']['local_group_word'])
        self.assertEqual(b['commands'][-1]['target'],0x489c2)
        self.assertEqual(b['commands'][-1]['skipped_byte'],0)
        self.assertEqual(table['read_layout']['count'],256)
        for i,row in enumerate(table['reads']):
            self.assertEqual(row['id'],'activation-animation-raw-long:%03d'%i)
            self.assertEqual(row['source_cpu_address'],0x48a12+4*i)
            self.assertEqual(row['source_rom_offset'],0x48a12+4*i)
            self.assertEqual(row['payload_offset'],4*i)
            self.assertEqual(row['value'],struct.unpack_from('>I',self.raw[0x48a12],4*i)[0])
        self.assertEqual(len(manifest['provenance']['checked_callers']),4)
        for row in manifest['provenance']['checked_callers']:
            self.assertEqual(row['cpu_address'],row['rom_offset'])
            self.assertEqual(row['sha256'],hashlib.sha256(bytes.fromhex(row['raw'])).hexdigest())
        self.assertFalse(any(name.endswith('.ms5c') for name in files))

    def test_wrong_source_hash_and_metadata(self):
        bad=bytearray(self.program);bad[0]^=1
        for program,source in ((bytes(bad),self.source),(self.program,dict(self.source,sha256='0'*64)),
                (self.program,dict(self.source,size=len(self.program)-1)),
                (self.program,dict(self.source,byte_order='little'))):
            with self.assertRaisesRegex(ValueError,'source'):self.build([(program,source)])

    def test_reviewed_caller_and_padding_mutation_rejected(self):
        for at in (0x47cd0,0x47d0a,0x47ed0,0x4a118,0x489c1):
            bad=bytearray(self.program);bad[at]^=1;digest=pack.sha(bad)
            with patch.object(pack,'SOURCE_SHA256',digest),patch.object(pack.inspector,'SOURCE_SHA256',digest):
                with self.assertRaises(ValueError):self.build([(bytes(bad),dict(self.source,sha256=digest))])

    def test_payload_pin_survives_source_repin(self):
        bad=bytearray(self.program);bad[0x48981]^=1;digest=pack.sha(bad)
        with patch.object(pack,'SOURCE_SHA256',digest),patch.object(pack.inspector,'SOURCE_SHA256',digest):
            with self.assertRaisesRegex(ValueError,'payload SHA'):
                self.build([(bytes(bad),dict(self.source,sha256=digest))])

    def test_source_or_provenance_changes_during_build(self):
        bad=bytearray(self.program);bad[-1]^=1
        for program,source in ((bytes(bad),self.source),(self.program,dict(self.source,path='other.bin'))):
            with self.assertRaisesRegex(ValueError,'changed during packing'):
                self.build([(self.program,self.source),(program,source)])

    def test_stale_tool_provenance_rejected(self):
        inventory=pack.inspector.inspect(self.program,self.source)
        inventory['inputs']['tools/inspect_activation_animation_scripts.py']='0'*64
        with patch.object(pack.inspector,'inspect',return_value=inventory):
            with self.assertRaisesRegex(ValueError,'Tool provenance'):
                self.build()


if __name__ == '__main__':
    unittest.main()
