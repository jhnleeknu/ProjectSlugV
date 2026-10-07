"""Synthetic scene lookup preservation, evidence and MS5D integrity."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_scene_debug as debug


class SceneDebugPackTests(unittest.TestCase):
    def setUp(self):
        self.program=bytearray(0x1b128)
        self.program[debug.BASE:debug.END]=bytes((index*31+17)&255 for index in range(512))
        # Substitute synthetic instruction evidence, never embed ROM data fixtures.
        self.evidence={0x1b094:b'baseproof',0x1b102:b'lookup-evidence-to-return'}
        for address,code in self.evidence.items():self.program[address:address+len(code)]=code
        self.data=bytes(self.program[debug.BASE:debug.END])
        for name,value in (('EVIDENCE',self.evidence),('PAYLOAD_SHA256',hashlib.sha256(self.data).hexdigest()),
                           ('PROGRAM_SHA256',hashlib.sha256(self.program).hexdigest())):
            substitute=patch.object(debug,name,value);substitute.start();self.addCleanup(substitute.stop)

    def test_exact_window_and_byte_index_extremes(self):
        self.assertEqual(debug.extract(self.program),self.data)
        for index in (0,1,127,128,255):
            self.assertEqual(self.data[index*2:index*2+2],self.program[debug.BASE+index*2:debug.BASE+index*2+2])
        self.assertEqual(self.data[0x1afd2-debug.BASE:0x1afda-debug.BASE],self.program[0x1afd2:0x1afda])
        self.assertEqual(self.data[0x1b094-debug.BASE:],self.program[0x1b094:debug.END])

    def test_header_payload_and_roundtrip(self):
        packed=debug.pack_payload(self.data)
        self.assertEqual(len(packed),544)
        self.assertEqual(struct.unpack('<4s7I',packed[:32]),
            (b'MS5D',1,1,debug.BASE,debug.BASE,512,zlib.crc32(self.data),0))
        self.assertEqual(debug.validate_container(packed),self.data)

    def test_header_schema_rejections(self):
        packed=debug.pack_payload(self.data)
        for field in range(8):
            changed=bytearray(packed)
            if field==0:changed[0]=0
            else:struct.pack_into('<I',changed,field*4,struct.unpack_from('<I',changed,field*4)[0]^1)
            with self.subTest(field=field),self.assertRaises(ValueError):debug.validate_container(changed)

    def test_truncated_program_and_payload_extent(self):
        for end in (0,debug.BASE,debug.END-1,max(a+len(c) for a,c in self.evidence.items())-1):
            with self.subTest(end=end),self.assertRaisesRegex(ValueError,'Truncated'):debug.extract(self.program[:end])
        for data in (b'',self.data[:-1],self.data+b'\0'):
            with self.assertRaisesRegex(ValueError,'complete'):debug.pack_payload(data)

    def test_evidence_and_payload_mutations(self):
        for address in self.evidence:
            changed=bytearray(self.program);changed[address]^=1
            with self.assertRaisesRegex(ValueError,'instruction evidence'):debug.extract(changed)
        for offset in (0,0x80,0xc0,511):
            changed=bytearray(self.data);changed[offset]^=1
            with self.assertRaisesRegex(ValueError,'native payload'):debug.pack_payload(changed)

    def test_crc_length_and_pinned_payload_rejections(self):
        packed=debug.pack_payload(self.data)
        for changed in (packed[:31],packed[:-1],packed+b'\0'):
            with self.assertRaises(ValueError):debug.validate_container(changed)
        changed=bytearray(packed);changed[32]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):debug.validate_container(changed)
        struct.pack_into('<I',changed,24,zlib.crc32(changed[32:]))
        with self.assertRaisesRegex(ValueError,'native payload'):debug.validate_container(changed)

    def test_whole_program_hash_and_surrounding_bytes(self):
        debug.verify_program(self.program)
        changed=bytearray(self.program);changed[debug.BASE-1]^=1
        with self.assertRaisesRegex(ValueError,'SHA256'):debug.verify_program(changed)
        self.assertEqual(debug.extract(changed),self.data)
        with self.assertRaises(ValueError):debug.verify_program(self.program+b'\0')


if __name__=='__main__':unittest.main()
