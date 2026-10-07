"""Synthetic byte-index word spans, prefix/source pins and MS5D integrity."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_player_record_lookup as lookup


class PlayerLookupTests(unittest.TestCase):
    def setUp(self):
        self.program=bytearray(8*1024*1024)
        self.data=bytearray((i*17+3)&255 for i in range(lookup.END-lookup.BASE))
        self.program[lookup.BASE:lookup.END]=self.data
        self.evidence=b'\x12\x34'
        self.program[lookup.EVIDENCE_ADDRESS:lookup.EVIDENCE_ADDRESS+2]=self.evidence
        self.data=self.program[lookup.BASE:lookup.END]
        for name,value in (('EVIDENCE',self.evidence),('RECORD_PREFIX_SHA256',hashlib.sha256(self.data[:320]).hexdigest()),
                           ('PAYLOAD_SHA256',hashlib.sha256(self.data).hexdigest()),('PROGRAM_SHA256',hashlib.sha256(self.program).hexdigest())):
            substitute=patch.object(lookup,name,value);substitute.start();self.addCleanup(substitute.stop)

    def test_full_source_container_roundtrip(self):
        lookup.verify_program(self.program);self.assertEqual(lookup.extract(self.program),self.data)
        raw=lookup.pack_payload(self.data);self.assertEqual(len(raw),4124)
        self.assertEqual(lookup.validate_container(raw),self.data)

    def test_all_index_word_addresses_and_maximum_bound(self):
        for index in range(256):
            address,value=lookup.lookup_word(self.data,index)
            self.assertEqual(address,lookup.BASE+index*16+10)
            self.assertEqual(value,struct.unpack_from('>H',self.data,index*16+10)[0])
        self.assertEqual(lookup.lookup_word(self.data,255)[0]+2,lookup.END)
        for index in (-1,256,True,1.0):
            with self.assertRaises(ValueError):lookup.lookup_word(self.data,index)

    def test_truncated_source_and_wrong_extents(self):
        for size in (0,lookup.BASE,lookup.END-1):
            with self.assertRaisesRegex(ValueError,'Truncated'):lookup.extract(self.program[:size])
        for data in (self.data[:-1],self.data+b'\0'):
            with self.assertRaises(ValueError):lookup.pack_payload(data)

    def test_prefix_and_later_code_bytes_pins(self):
        for offset,reason in ((0,'prefix'),(4000,'pinned')):
            changed=bytearray(self.data);changed[offset]^=1
            with self.assertRaisesRegex(ValueError,reason):lookup.validate_payload(changed)

    def test_instruction_and_whole_source_hash_pins(self):
        self.program[lookup.EVIDENCE_ADDRESS]^=1
        with self.assertRaisesRegex(ValueError,'evidence'):lookup.extract(self.program)
        with self.assertRaisesRegex(ValueError,'SHA256'):lookup.verify_program(self.program)
        with self.assertRaises(ValueError):lookup.verify_program(self.program[:-1])

    def test_header_schema_and_exact_length(self):
        raw=lookup.pack_payload(self.data)
        for offset in (0,4,8,12,16,20,28):
            changed=bytearray(raw);changed[offset]^=1
            with self.assertRaisesRegex(ValueError,'header'):lookup.validate_container(changed)
        for data in (raw[:28],raw[:-1],raw+b'\0'):
            with self.assertRaises(ValueError):lookup.validate_container(data)

    def test_crc_and_recomputed_crc_do_not_bypass_raw_pin(self):
        raw=bytearray(lookup.pack_payload(self.data));raw[-1]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):lookup.validate_container(raw)
        struct.pack_into('<I',raw,24,zlib.crc32(raw[32:]))
        with self.assertRaisesRegex(ValueError,'pinned'):lookup.validate_container(raw)


if __name__ == '__main__':unittest.main()
