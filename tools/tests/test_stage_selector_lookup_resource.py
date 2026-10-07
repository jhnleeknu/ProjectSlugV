"""Synthetic raw-window source/evidence pins and MS5D schema/CRC checks."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_stage_selector_lookup as lookup


class SelectorLookupTests(unittest.TestCase):
    def setUp(self):
        self.data=bytes((i*37+9)&255 for i in range(128))
        self.program=bytearray(8*1024*1024);self.program[lookup.BASE:lookup.END]=self.data
        self.evidence=b'\x12\x34';self.program[lookup.EVIDENCE_ADDRESS:lookup.EVIDENCE_ADDRESS+2]=self.evidence
        for name,value in (('EVIDENCE',self.evidence),('PAYLOAD_SHA256',hashlib.sha256(self.data).hexdigest()),
                           ('PROGRAM_SHA256',hashlib.sha256(self.program).hexdigest())):
            substitute=patch.object(lookup,name,value);substitute.start();self.addCleanup(substitute.stop)

    def test_full_source_and_exact_container_roundtrip(self):
        lookup.verify_program(self.program);self.assertEqual(lookup.extract(self.program),self.data)
        raw=lookup.pack_payload(self.data);self.assertEqual(len(raw),160)
        self.assertEqual(struct.unpack_from('<4s7I',raw),(b'MS5D',1,1,lookup.BASE,lookup.BASE,128,zlib.crc32(self.data),0))
        self.assertEqual(lookup.validate_container(raw),self.data)

    def test_truncated_source_evidence_and_payload_extent(self):
        for size in (0,lookup.BASE,lookup.END-1,lookup.EVIDENCE_ADDRESS+1):
            with self.assertRaisesRegex(ValueError,'Truncated'):lookup.extract(self.program[:size])
        for data in (self.data[:-1],self.data+b'\0'):
            with self.assertRaises(ValueError):lookup.pack_payload(data)

    def test_native_payload_and_instruction_pins(self):
        changed=bytearray(self.data);changed[-1]^=1
        with self.assertRaisesRegex(ValueError,'pinned'):lookup.validate_payload(changed)
        self.program[lookup.EVIDENCE_ADDRESS]^=1
        with self.assertRaisesRegex(ValueError,'evidence'):lookup.extract(self.program)

    def test_whole_source_size_and_sha(self):
        with self.assertRaises(ValueError):lookup.verify_program(self.program[:-1])
        self.program[10]^=1
        with self.assertRaisesRegex(ValueError,'SHA256'):lookup.verify_program(self.program)

    def test_header_schema_all_fields_and_length(self):
        raw=lookup.pack_payload(self.data)
        for offset in (0,4,8,12,16,20,28):
            changed=bytearray(raw);changed[offset]^=1
            with self.assertRaisesRegex(ValueError,'header'):lookup.validate_container(changed)
        for data in (raw[:20],raw[:-1],raw+b'\0'):
            with self.assertRaises(ValueError):lookup.validate_container(data)

    def test_crc_and_recomputed_crc_pin(self):
        changed=bytearray(lookup.pack_payload(self.data));changed[-1]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):lookup.validate_container(changed)
        struct.pack_into('<I',changed,24,zlib.crc32(changed[32:]))
        with self.assertRaisesRegex(ValueError,'pinned'):lookup.validate_container(changed)

    def test_surrounding_data_preserved_outside_payload(self):
        self.program[lookup.BASE-1]=0xaa;self.program[lookup.END]=0xbb
        self.assertEqual(lookup.extract(self.program),self.data)


if __name__=='__main__':unittest.main()
