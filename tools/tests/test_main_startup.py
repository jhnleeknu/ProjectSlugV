"""Startup window integrity and disabled palette binding extraction."""
import hashlib
import struct
import unittest
from unittest.mock import patch
import zlib
from tools import pack_main_startup as startup
from tools import pack_palettes as palettes


class StartupTests(unittest.TestCase):
    def setUp(self):
        expected = tuple((index, 0x100+index, index & 3) for index in range(11)) + (
            (11,0x100,0),(12,0x101,0),(13,0xffff,2),(14,0xffff,2),(15,0xffff,2),(16,0xffff,2))
        self.data = b''.join(struct.pack('>HHBB', *record, 0) for record in expected)+b'\xff\xff'
        self.program = bytearray(startup.END)
        self.program[startup.BASE:startup.END] = self.data
        for name, value in (('EXPECTED', expected), ('PAYLOAD_SHA256', hashlib.sha256(self.data).hexdigest())):
            substitute = patch.object(startup, name, value)
            substitute.start(); self.addCleanup(substitute.stop)

    def test_complete_records_and_disabled_metadata(self):
        self.assertEqual(startup.extract(self.program), self.data)
        records = startup.validate_payload(self.data)
        self.assertEqual(len(records), 17)
        self.assertEqual(sum(record['disabled'] for record in records), 4)
        self.assertEqual(len({record['source_id'] for record in records if not record['disabled']}), 11)
        self.assertTrue(all(record['sixth_byte'] == 0 for record in records))

    def test_container_crc_and_exact_payload(self):
        packed = startup.pack_payload(self.data)
        self.assertEqual(struct.unpack('<4s7I', packed[:32]),
            (b'MS5D',1,1,startup.BASE,startup.BASE,104,zlib.crc32(self.data),0))
        self.assertEqual(packed[32:], self.data)
        changed = bytearray(packed); changed[-3] ^= 1
        self.assertNotEqual(zlib.crc32(changed[32:]), struct.unpack_from('<I', changed, 24)[0])

    def test_truncation_and_wrong_extent(self):
        for size in (0, startup.BASE, startup.END-1):
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, 'Truncated'):
                startup.extract(self.program[:size])
        for data in (self.data[:-1], self.data+b'\0'):
            with self.assertRaises(ValueError): startup.pack_payload(data)

    def test_reviewed_fields_and_sixth_byte_and_terminator(self):
        for offset in (0,2,4,5,102,103):
            changed = bytearray(self.data); changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError): startup.validate_payload(changed)

    def test_surrounding_data_does_not_extend_payload(self):
        changed = self.program+b'trailing code'
        changed[startup.BASE-1] = 0xab
        self.assertEqual(startup.extract(changed), self.data)


class PaletteBindingTests(unittest.TestCase):
    def test_disabled_source_is_binding_not_palette_and_sixth_preserved(self):
        program = bytearray(0x20000c)
        program[0x100:0x10e] = struct.pack('>HHBBHHBBH', 1,0xffff,2,0xa5,2,0x62,2,0x5a,0xffff)
        with patch.object(palettes, 'BINDING_TABLES', (0x100,)), patch.object(palettes, 'DYNAMIC_REQUESTS', ()), patch.object(palettes, 'extract_record', return_value=(b'a',b'b',0,[])) as record:
            extracted, bindings = palettes.extract(program)
        self.assertEqual(set(extracted), {0x62})
        record.assert_called_once_with(program, 0, 0, 0x62)
        self.assertTrue(bindings[0]['disabled'])
        self.assertEqual(bindings[0]['source_id'], 0xffff)
        self.assertEqual([binding['sixth_byte'] for binding in bindings], [0xa5,0x5a])

    def test_truncated_record_and_missing_terminator(self):
        for data in (b'\0', b'\0\1\xff\xff\2', struct.pack('>HHBB', 1,0xffff,2,0)):
            with self.subTest(data=data.hex()), self.assertRaisesRegex(ValueError, 'Truncated'):
                palettes.extract_bindings(data, 0)

    def test_invalid_slot_and_record_limit(self):
        with self.assertRaisesRegex(ValueError, 'destination'):
            palettes.extract_bindings(struct.pack('>HHBBH',256,1,0,0,0xffff),0)
        data = struct.pack('>HHBB',1,0xffff,2,0)*256+b'\xff\xff'
        with self.assertRaisesRegex(ValueError, 'missing terminator'):
            palettes.extract_bindings(data,0)


if __name__ == '__main__': unittest.main()
