"""Synthetic rawlookup, MS5D corruption and immutable-source packaging inputs."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_stage_hud_counter as block

# Synthetic records keep extracted game data out of version control.
RAW = b''.join(struct.pack('>H', 0x1200+i*13) for i in range(16))


class StageHudCounterResourceTests(unittest.TestCase):
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
        self.assertEqual(len(packed), 64)
        self.assertEqual(block.sha(packed), block.CONTAINER_SHA256)
        self.assertEqual(block.validate_container(packed), RAW)
        self.assertEqual(struct.unpack_from('<4s7I',packed),
            (b'MS5D',1,1,block.CPU,block.CPU,32,zlib.crc32(RAW),0))

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

    def test_payload_extent_and_mutation_rejected(self):
        for changed in (RAW[:-1],RAW+b'\0',RAW[:-2]+b'\0\0'):
            with self.assertRaises(ValueError): block.wrap(changed)

    def test_deterministic_metadata_and_original_read_mapping(self):
        files, manifest = self.build()
        self.assertEqual((files,manifest),self.build())
        self.assertEqual(json.loads(files['manifest.json']),manifest)
        self.assertEqual(manifest['source'],self.source)
        self.assertEqual(manifest['counts'],dict(resources=1,word_reads=16,
            total_payload_bytes=32,total_container_bytes=64))
        r = manifest['resources'][0]
        self.assertEqual(r['id'],'stage-hud-counter-raw-lookup')
        self.assertEqual(r['file'],'lookup.ms5d')
        self.assertEqual(r['payload_crc32'],zlib.crc32(RAW))
        self.assertEqual(r['sha256'],block.CONTAINER_SHA256)
        self.assertEqual(r['payload_sha256'],block.PAYLOAD_SHA256)
        self.assertEqual(r['end_cpu_address_exclusive'],block.END)
        self.assertEqual(r['end_rom_offset_exclusive'],block.END)
        self.assertEqual(r['nominal_digit_entries'],10)
        self.assertEqual(r['code_bytes_begin_cpu'],0x4e286)
        for i, read in enumerate(r['word_reads']):
            self.assertEqual(read['id'],'stage-hud-counter-lookup-word:%02d'%i)
            self.assertEqual(read['source_cpu_address'],block.CPU+2*i)
            self.assertEqual(read['source_rom_offset'],block.CPU+2*i)
            self.assertEqual(read['payload_offset'],2*i)
            self.assertEqual(read['value'],struct.unpack_from('>H',RAW,2*i)[0])
            self.assertEqual(read['nominal_digit_entry'],i<10)

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
