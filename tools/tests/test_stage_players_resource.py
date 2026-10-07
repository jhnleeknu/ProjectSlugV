"""Synthetic stage-player address spans, source pins and MS5D integrity."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_stage_players as players


class StagePlayersTests(unittest.TestCase):
    def setUp(self):
        self.data = bytearray((i*13+7)&255 for i in range(players.END-players.BASE))
        for i,pair in enumerate(players.PAIRS): struct.pack_into('>HH',self.data,i*4,*pair)
        struct.pack_into('>3I',self.data,20,*players.POINTERS)
        self.program = bytearray(8*1024*1024); self.program[players.BASE:players.END] = self.data
        self.evidence = {players.BASE+32:b'\x12\x34\x56\x78'}
        self.program[players.BASE+32:players.BASE+36] = self.evidence[players.BASE+32]
        self.data = self.program[players.BASE:players.END]
        for name,value in (('EVIDENCE',self.evidence),('PAYLOAD_SHA256',hashlib.sha256(self.data).hexdigest()),
                           ('PROGRAM_SHA256',hashlib.sha256(self.program).hexdigest())):
            substitute=patch.object(players,name,value);substitute.start();self.addCleanup(substitute.stop)

    def test_exact_extract_and_container(self):
        players.verify_program(self.program)
        self.assertEqual(players.extract(self.program),self.data)
        packed=players.pack_payload(self.data)
        self.assertEqual(len(packed),1072)
        self.assertEqual(players.validate_container(packed),self.data)

    def test_all_byte_address_pairs_and_maximum_extent(self):
        for stage in range(256):
            pointer=players.POINTERS[stage-6] if 6<=stage<=8 else players.POINTERS[0]
            for area in (0,1,255):
                address,pair=players.address_pair(self.data,stage,area)
                self.assertEqual(address,pointer+area*4)
                self.assertEqual(pair,struct.unpack_from('>HH',self.data,address-players.BASE))
        self.assertEqual(players.address_pair(self.data,8,255)[0]+4,players.END)
        for stage,area in ((-1,0),(256,0),(0,-1),(0,256)):
            with self.assertRaises(ValueError): players.address_pair(self.data,stage,area)

    def test_truncation_and_wrong_payload_extent(self):
        for size in (0,players.BASE,players.END-1):
            with self.assertRaisesRegex(ValueError,'Truncated'): players.extract(self.program[:size])
        for data in (self.data[:-1],self.data+b'\0'):
            with self.assertRaises(ValueError): players.pack_payload(data)

    def test_pairs_pointers_code_bytes_and_evidence_pins(self):
        for at in (0,2,20,31,1000):
            changed=bytearray(self.data);changed[at]^=1
            with self.assertRaises(ValueError): players.validate_payload(changed)
        self.program[players.BASE+32]^=1
        with self.assertRaisesRegex(ValueError,'evidence'): players.extract(self.program)

    def test_whole_source_size_hash_pin(self):
        with self.assertRaises(ValueError): players.verify_program(self.program[:-1])
        self.program[100]^=1
        with self.assertRaisesRegex(ValueError,'SHA256'): players.verify_program(self.program)

    def test_container_header_and_length(self):
        packed=players.pack_payload(self.data)
        for offset in (0,4,8,12,16,20,28):
            changed=bytearray(packed);changed[offset]^=1
            with self.assertRaisesRegex(ValueError,'header'): players.validate_container(changed)
        for raw in (packed[:30],packed[:-1],packed+b'\0'):
            with self.assertRaises(ValueError): players.validate_container(raw)

    def test_crc_and_recomputed_crc_do_not_bypass_native_pin(self):
        changed=bytearray(players.pack_payload(self.data));changed[-1]^=1
        with self.assertRaisesRegex(ValueError,'CRC'): players.validate_container(changed)
        struct.pack_into('<I',changed,24,zlib.crc32(changed[32:]))
        with self.assertRaisesRegex(ValueError,'pinned'): players.validate_container(changed)


if __name__ == '__main__': unittest.main()
