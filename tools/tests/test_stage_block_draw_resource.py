"""Pinned stream, MS5D corruption and immutable-source publication inputs."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_stage_block_draw as block

# Synthetic records keep extracted game data out of version control.
RAW = b''.join(struct.pack('>HHBB', i*2, 0x1200+i, i+1, 2) for i in range(9))+b'\xff\xff'


class StageBlockDrawResourceTests(unittest.TestCase):
    def setUp(self):
        packed = struct.pack('<4s7I', b'MS5D',1,1,block.CPU,block.CPU,len(RAW),zlib.crc32(RAW),0)+RAW
        for name,value in (('PAYLOAD_SHA256',hashlib.sha256(RAW).hexdigest()),
                ('CONTAINER_SHA256',hashlib.sha256(packed).hexdigest()),('CRC32',zlib.crc32(RAW))):
            patcher=patch.object(block,name,value);patcher.start();self.addCleanup(patcher.stop)
        self.program = bytearray(block.END+16)
        self.program[block.CPU:block.END] = RAW
        self.program = bytes(self.program)
        self.digest = hashlib.sha256(self.program).hexdigest()
        self.source = dict(path='synthetic.bin', size=len(self.program),
            sha256=self.digest, byte_order='big')

    def build(self, responses=None):
        with patch.object(block, 'SOURCE_SHA256', self.digest), patch.object(
                block, 'load_verified_program', side_effect=responses or
                [(self.program,self.source), (self.program,self.source)]):
            return block.build(Path('.'))

    def test_pinned_container_and_exact_header(self):
        packed = block.wrap(RAW)
        self.assertEqual(len(packed), 88)
        self.assertEqual(block.sha(packed), block.CONTAINER_SHA256)
        self.assertEqual(block.validate_container(packed), RAW)
        self.assertEqual(struct.unpack_from('<4s7I',packed),
            (b'MS5D',1,1,block.CPU,block.CPU,56,zlib.crc32(RAW),0))

    def test_all_header_fields_and_file_lengths_rejected(self):
        packed = block.wrap(RAW)
        for offset in (0,4,8,12,16,20,28):
            changed = bytearray(packed); changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError,'header'):
                block.validate_container(changed)
        for changed in (packed[:20],packed[:-1],packed+b'\0'):
            with self.assertRaises(ValueError): block.validate_container(changed)

    def test_crc_corruption_and_recomputed_crc_cannot_replace_pinned_data(self):
        changed = bytearray(block.wrap(RAW)); changed[35] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'): block.validate_container(changed)
        struct.pack_into('<I',changed,24,zlib.crc32(changed[32:]))
        with self.assertRaisesRegex(ValueError,'pinned'): block.validate_container(changed)
        changed = bytearray(block.wrap(RAW)); changed[24] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'): block.validate_container(changed)

    def test_payload_extent_and_sentinel_mutation_rejected(self):
        for changed in (RAW[:-1],RAW+b'\0',RAW[:-2]+b'\0\0'):
            with self.assertRaises(ValueError): block.wrap(changed)

    def test_deterministic_metadata_and_original_field_mapping(self):
        files, manifest = self.build()
        self.assertEqual((files,manifest),self.build())
        self.assertEqual(json.loads(files['manifest.json']),manifest)
        self.assertEqual(manifest['source'],self.source)
        self.assertEqual(manifest['counts'],dict(resources=1,records=9,
            total_payload_bytes=56,total_container_bytes=88))
        r = manifest['resources'][0]
        self.assertEqual(r['payload_crc32'],zlib.crc32(RAW))
        self.assertEqual(r['sha256'],block.CONTAINER_SHA256)
        self.assertEqual(r['payload_sha256'],block.PAYLOAD_SHA256)
        self.assertEqual(r['end_cpu_address_exclusive'],block.END)
        self.assertEqual(r['end_rom_offset_exclusive'],block.END)
        for i, record in enumerate(r['records']):
            self.assertEqual(record['id'],'stage-block-draw-record:%02d'%i)
            self.assertEqual(record['source_cpu_address'],block.CPU+6*i)
            self.assertEqual(record['source_rom_offset'],block.CPU+6*i)
            self.assertEqual(tuple(record[k] for k in ('offset','tile','width','height')),
                struct.unpack_from('>HHBB',RAW,6*i))
        self.assertEqual(r['sentinel'],dict(payload_offset=54,source_cpu_address=block.END-2,
            source_rom_offset=block.END-2,size=2,value=65535))

    def test_source_hash_and_manifest_hash_rejected(self):
        altered = bytearray(self.program); altered[0] ^= 1
        for program, source in ((bytes(altered),self.source),
                (self.program,dict(self.source,sha256='0'*64))):
            with self.assertRaisesRegex(ValueError,'source'):
                self.build([(program,source)])

    def test_source_or_metadata_changes_during_build_rejected(self):
        altered = bytearray(self.program); altered[-1] ^= 1
        for program, source in ((bytes(altered),self.source),
                (self.program,dict(self.source,path='changed.bin'))):
            with self.assertRaisesRegex(ValueError,'changed during packing'):
                self.build([(self.program,self.source),(program,source)])


if __name__ == '__main__': unittest.main()
