"""Range decoding and provenance validation on synthetic 68000 bytes."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools import disassemble_program as program


class DisassembleProgramTests(unittest.TestCase):
    def test_rts_jump_branch_and_explicit_mapping(self):
        data = bytes.fromhex('ffff4e754ef90000123460000004')
        rows = program.disassemble_range(data, 2, 12, 0x100)
        self.assertEqual([row['rom_offset'] for row in rows], [2, 4, 10])
        self.assertEqual([row['cpu_address'] for row in rows], [0x100, 0x102, 0x108])
        self.assertEqual([row['size'] for row in rows], [2, 6, 4])
        self.assertEqual([row['mnemonic'] for row in rows], ['rts', 'jmp', 'bra.w'])
        self.assertEqual(rows[1]['op_str'], '$1234.l')
        self.assertEqual(rows[2]['op_str'], '$10e')
        self.assertTrue(all(row['classification'] == 'candidate_instruction' for row in rows))
        self.assertEqual(''.join(row['raw'] for row in rows), data[2:].hex())

    def test_invalid_and_truncated_words_preserve_exact_coverage(self):
        for opcode in ('ffff', '4ef9', '0000', '13fc', '6000'):
            with self.subTest(opcode=opcode):
                rows = program.disassemble_range(bytes.fromhex(opcode), 0, 2, 0)
                self.assertEqual(rows, [{'rom_offset': 0, 'cpu_address': 0,
                                        'raw': opcode, 'size': 2, 'mnemonic': 'dc.w',
                                        'op_str': '$' + opcode,
                                        'classification': 'undecoded_word'}])
        data = bytes.fromhex('ffff4e754ef90000')
        rows = program.disassemble_range(data, 0, len(data), 0x200)
        self.assertEqual(sum(row['size'] for row in rows), len(data))
        self.assertEqual(''.join(row['raw'] for row in rows), data.hex())
        self.assertEqual(rows[1]['mnemonic'], 'rts')
        self.assertEqual(rows[2]['classification'], 'undecoded_word')

    def test_range_boundary_does_not_decode_following_operand_bytes(self):
        data = bytes.fromhex('13fc001200001234')
        rows = program.disassemble_range(data, 0, 2, 0)
        self.assertEqual(rows[0]['classification'], 'undecoded_word')
        full = program.disassemble_range(data, 0, len(data), 0)
        self.assertEqual(full[0]['size'], 8)
        self.assertEqual(full[0]['classification'], 'candidate_instruction')
        # ILLEGAL is a real 68000 opcode, unlike an undecodable word.
        self.assertEqual(program.disassemble_range(bytes.fromhex('4afc'), 0, 2, 0)[0]
                         ['classification'], 'candidate_instruction')

    def test_range_validation(self):
        for offset, length, base in ((-2, 2, 0), (1, 2, 0), (0, 1, 0), (0, 0, 0),
                                     (0, 2, 1), (0, 2, -2), (2, 4, 0),
                                     (0, 4, 0xfffffe), (0, 2, 0x1000000)):
            with self.subTest(offset=offset, length=length, base=base):
                with self.assertRaises(ValueError):
                    program.disassemble_range(bytes(4), offset, length, base)
        with self.assertRaises(ValueError):
            program.disassemble_range(bytes(program.MAX_REGION_SIZE + 2), 0, 2, 0)
        self.assertEqual(program.disassemble_range(bytes.fromhex('4e75'), 0, 2, 0xfffffe)[0]
                         ['cpu_address'], 0xfffffe)

    def test_verified_source_json_listing_and_corrupt_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'extracted/program'
            directory.mkdir(parents=True)
            data = bytes.fromhex('4e75ffff')
            source = {'path': 'extracted/program/maincpu.decrypted.be.bin',
                      'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'byte_order': 'big'}
            manifest = {'schema_version': 1, 'output': source}
            binary = directory / 'maincpu.decrypted.be.bin'
            binary.write_bytes(data)
            manifest_path = directory / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            output = root / 'artifacts/disassembly/range.json'
            report = program.write_disassembly(0, 4, 0xc00000, output, root=root)
            self.assertEqual(json.loads(output.read_text()), report)
            self.assertEqual(report['source']['sha256'], source['sha256'])
            self.assertEqual(report['mapping']['basis'], 'explicitly_supplied_by_caller')
            self.assertIn('00000000    c00000', output.with_suffix('.asm').read_text())
            binary.write_bytes(bytes(4))
            rejected = root / 'artifacts/rejected/range.json'
            with self.assertRaisesRegex(ValueError, 'hash'):
                program.write_disassembly(0, 4, 0, rejected, root=root)
            self.assertFalse(rejected.parent.exists())
            binary.write_bytes(bytes(2))
            with self.assertRaisesRegex(ValueError, 'size'):
                program.load_verified_program(root)
            binary.write_bytes(data)
            source['byte_order'] = 'little'
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'big-endian'):
                program.load_verified_program(root)


if __name__ == '__main__':
    unittest.main()
