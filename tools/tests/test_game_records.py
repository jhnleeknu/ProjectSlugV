"""Synthetic record preservation and fixed-window/instruction/container integrity."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_game_records as records


class GameRecordTests(unittest.TestCase):
    def setUp(self):
        self.data=bytes((index*37+11)&255 for index in range(320))
        # Synthetic instruction windows prevent tracked test fixtures containing ROM.
        self.evidence={0x4d81c:b'lookup-proof',0x481de:b'caller-proof'}
        self.program=bytearray(0x4d84e)
        self.program[records.BASE:records.END]=self.data
        for address,code in self.evidence.items():self.program[address:address+len(code)]=code
        for name,value in (('EVIDENCE',self.evidence),('PAYLOAD_SHA256',hashlib.sha256(self.data).hexdigest())):
            substitute=patch.object(records,name,value);substitute.start();self.addCleanup(substitute.stop)

    def test_record_metadata_and_all_bytes_preserved(self):
        self.assertEqual(records.extract(self.program),self.data)
        rows=records.validate_payload(self.data)
        self.assertEqual([row['id'] for row in rows],list(range(20)))
        for index,row in enumerate(rows):
            raw=self.data[index*16:(index+1)*16]
            self.assertEqual(row['record_cpu_address'],records.BASE+index*16)
            self.assertEqual(row['record_rom_offset'],row['record_cpu_address'])
            self.assertEqual(bytes.fromhex(row['raw_bytes_hex']),raw)
            self.assertEqual(row['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(row['raw_fields'],dict(byte_01=raw[1],byte_02=raw[2],
                word_0a=struct.unpack_from('>H',raw,10)[0],word_0c=struct.unpack_from('>H',raw,12)[0],
                word_0e=struct.unpack_from('>H',raw,14)[0]))

    def test_exact_ms5d_schema_and_crc(self):
        packed=records.pack_payload(self.data)
        self.assertEqual(len(packed),352)
        self.assertEqual(struct.unpack('<4s7I',packed[:32]),
            (b'MS5D',1,1,records.BASE,records.BASE,320,zlib.crc32(self.data),0))
        self.assertEqual(packed[32:],self.data)
        changed=bytearray(packed);changed[32+101]^=1
        self.assertNotEqual(zlib.crc32(changed[32:]),struct.unpack_from('<I',changed,24)[0])

    def test_truncated_program_table_and_evidence(self):
        for size in (0,records.BASE,records.END-1,0x4d81c):
            with self.subTest(size=size),self.assertRaisesRegex(ValueError,'Truncated'):
                records.extract(self.program[:size])

    def test_wrong_record_extent(self):
        for data in (b'',self.data[:-1],self.data+b'\0'):
            with self.assertRaisesRegex(ValueError,'complete'):records.pack_payload(data)

    def test_consumed_and_unconsumed_payload_mutations_rejected(self):
        for offset in (0,1,2,3,9,10,12,14,319):
            changed=bytearray(self.program);changed[records.BASE+offset]^=1
            with self.subTest(offset=offset),self.assertRaisesRegex(ValueError,'native bytes'):
                records.extract(changed)

    def test_instruction_evidence_mutation_rejected(self):
        for address in self.evidence:
            changed=bytearray(self.program);changed[address]^=1
            with self.assertRaisesRegex(ValueError,'instruction evidence'):records.extract(changed)

    def test_surrounding_data_is_not_extracted(self):
        changed=self.program+b'trailing unrelated bytes';changed[records.BASE-1]=0xff
        self.assertEqual(records.extract(changed),self.data)


if __name__=='__main__':unittest.main()
