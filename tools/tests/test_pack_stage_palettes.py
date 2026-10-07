"""Synthetic table/whole-program pinning and MS5D integrity regression checks."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_stage_palettes as palettes
from tools import pack_palettes as catalog


class StagePaletteTests(unittest.TestCase):
    def setUp(self):
        self.expected = ((2,0x101,2,0),(3,0x102,2,0),(4,0x103,2,0),(5,0x104,2,0))
        self.data = b''.join(struct.pack('>HHBB',*row) for row in self.expected)+b'\xff\xff'
        self.program = bytearray(8*1024*1024)
        self.program[palettes.BASE:palettes.END] = self.data
        for name,value in (('EXPECTED',self.expected),('PAYLOAD_SHA256',hashlib.sha256(self.data).hexdigest()),
                           ('PROGRAM_SHA256',hashlib.sha256(self.program).hexdigest())):
            substitute = patch.object(palettes,name,value)
            substitute.start(); self.addCleanup(substitute.stop)

    def test_complete_fields_and_exact_container_roundtrip(self):
        self.assertEqual(palettes.verify_program(self.program),self.data)
        records = palettes.validate_payload(self.data)
        self.assertEqual([(r['slot'],r['source_id'],r['flags'],r['sixth_byte']) for r in records],list(self.expected))
        packed = palettes.pack_payload(self.data)
        self.assertEqual(len(packed),58)
        self.assertEqual(struct.unpack_from('<4s7I',packed),(b'MS5D',1,1,palettes.BASE,palettes.BASE,26,zlib.crc32(self.data),0))
        self.assertEqual(palettes.validate_container(packed),self.data)

    def test_truncated_program_and_payload_extents(self):
        for size in (0,palettes.BASE,palettes.END-1):
            with self.subTest(size=size),self.assertRaisesRegex(ValueError,'Truncated'):
                palettes.extract(self.program[:size])
        for data in (self.data[:-1],self.data+b'\0'):
            with self.assertRaises(ValueError): palettes.pack_payload(data)
        with self.assertRaisesRegex(ValueError,'canonical'): palettes.verify_program(self.program[:-1])

    def test_reviewed_slot_source_flags_sixth_and_terminator(self):
        for offset in (0,2,4,5,24,25):
            changed = bytearray(self.data); changed[offset] ^= 1
            with self.subTest(offset=offset),self.assertRaises(ValueError): palettes.validate_payload(changed)

    def test_whole_program_mutation_and_payload_hash_pin(self):
        self.program[100] ^= 1
        with self.assertRaisesRegex(ValueError,'SHA256'): palettes.verify_program(self.program)
        with patch.object(palettes,'PAYLOAD_SHA256','0'*64):
            with self.assertRaisesRegex(ValueError,'pinned'): palettes.validate_payload(self.data)

    def test_header_schema_rejection(self):
        packed = palettes.pack_payload(self.data)
        for offset in (0,4,8,12,16,20,28):
            changed = bytearray(packed); changed[offset] ^= 1
            with self.subTest(offset=offset),self.assertRaisesRegex(ValueError,'header'):
                palettes.validate_container(changed)

    def test_crc_length_and_recomputed_crc_native_mutation(self):
        packed = palettes.pack_payload(self.data)
        changed = bytearray(packed); changed[34] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'): palettes.validate_container(changed)
        struct.pack_into('<I',changed,24,zlib.crc32(changed[32:]))
        with self.assertRaisesRegex(ValueError,'reviewed'): palettes.validate_container(changed)
        for raw in (packed[:20],packed[:-1],packed+b'\0'):
            with self.assertRaises(ValueError): palettes.validate_container(raw)

    def test_palette_catalog_consumes_four_grounded_ids(self):
        with patch.object(catalog,'BINDING_TABLES',(palettes.BASE,)), patch.object(catalog,'DYNAMIC_REQUESTS',()), \
             patch.object(catalog,'extract_record',return_value=(b'a',b'b',0,[])) as extract_record:
            records,bindings = catalog.extract(self.program)
        self.assertEqual(set(records),{row[1] for row in self.expected})
        self.assertEqual(len(bindings),4)
        self.assertEqual([row['sixth_byte'] for row in bindings],[0]*4)
        self.assertEqual(extract_record.call_count,4)

    def test_palette_catalog_checks_pinned_table_before_color_reads(self):
        self.program[palettes.BASE+5] ^= 1
        with patch.object(catalog,'BINDING_TABLES',(palettes.BASE,)), patch.object(catalog,'DYNAMIC_REQUESTS',()), \
             patch.object(catalog,'extract_record') as extract_record:
            with self.assertRaisesRegex(ValueError,'reviewed'): catalog.extract(self.program)
            extract_record.assert_not_called()

    def test_surrounding_bytes_do_not_extend_window(self):
        self.program[palettes.BASE-1] = 0xaa; self.program[palettes.END] = 0xbb
        self.assertEqual(palettes.extract(self.program),self.data)


if __name__ == '__main__': unittest.main()
