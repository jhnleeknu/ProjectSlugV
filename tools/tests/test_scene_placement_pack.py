"""Placement packaging guards use only synthetic bytes, never a ROM fixture."""
import copy
import json
import struct
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pack_scene_placements as pack


def record(gate=0, count=0, bounds=0, callback=0xffffffff):
    return struct.pack('>4H2I', gate, count, 0x8000, 0xffff, bounds, callback)


class PlacementPackTests(unittest.TestCase):
    def test_exact_terminal_and_raw_negative_gate(self):
        payload = record(0x8000)+record(0xfffe, 2)+b'\x12\x34\xff\xff'
        rows = pack.decode_payload(payload, 0x200)
        self.assertEqual([r.get('gate_word') for r in rows[:-1]], [0x8000, 0xfffe])
        self.assertEqual(rows[1]['inline_raw_hex'], '1234')
        self.assertEqual(rows[0]['callback_pointer_long'], 0xffffffff)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(pack.decode_payload(b'\xff\xff', 0x200)), 1)

    def test_invalid_record_spans(self):
        bad = [b'', b'\x80\x00', record(), record(0, 2)+b'\x12',
               record(0, 1)+b'\0\0\xff\xff', record(0, 0x8000),
               b'\xff\xff\0\0', b'\xff\xff\0', record(bounds=0x400)]
        for data in bad:
            with self.subTest(data=data.hex()), self.assertRaises(ValueError):
                pack.decode_payload(data, 0x200)

    def test_address_bounds(self):
        for cpu in (-2, 1, 0xfffff, 0x100000):
            with self.subTest(cpu=cpu), self.assertRaises(ValueError):
                pack.decode_payload(b'\xff\xff', cpu)
        path = dict(root_cpu_address=-2, root_rom_offset=-2, errors=[], status='raw_candidates')
        with self.assertRaises(ValueError):
            pack.placement_payload(b'\xff\xff', path)

    def test_container_identity_crc_and_size(self):
        good = pack.wrap(record()+b'\xff\xff', 0x200)
        self.assertEqual(pack.validate_container(good, 0x200), good[32:])
        for offset in (0, 4, 8, 12, 16, 20, 24, 28, 32):
            bad = bytearray(good); bad[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                pack.validate_container(bytes(bad), 0x200)

    def fixture(self):
        program = bytearray(0x400)
        program[0x100:0x108] = struct.pack('>HIH', 0xc, 0x200, 0xffff)
        payload = record(0x8000, 2)+b'\x12\x34\xff\xff'
        program[0x200:0x200+len(payload)] = payload
        source = {'sha256': pack.sha(program)}
        manifest = json.dumps(dict(source=source, scripts=[dict(source_cpu_address=0x100,
            source_rom_offset=0x100, end_exclusive=0x108,
            payload_sha256=pack.sha(program[0x100:0x108]))])).encode()
        refs = [dict(script_cpu_address=0x100, command_cpu_address=0x100,
            command_rom_offset=0x100, operand_raw_hex='00000200', root_pointer_long=0x200)]
        path = dict(root_cpu_address=0x200, root_rom_offset=0x200,
            rows=pack.decode_payload(payload, 0x200), errors=[], status='raw_candidates',
            end_cpu_address_exclusive=0x200+len(payload), references=refs)
        inventory = dict(source=source, program_code_modified=False, error_count=0,
            scene_scripts_manifest_sha256=pack.sha(manifest), references=refs, paths=[path],
            reference_count=1, unique_root_count=1, unique_record_count=1,
            unique_terminal_count=1, bounds_pointers=[])
        return program, source, inventory, manifest

    def test_independent_source_reference_and_rows(self):
        program, source, inv, manifest = self.fixture()
        with patch.object(pack, 'SOURCE_SHA256', source['sha256']), patch.object(pack, 'CANONICAL_COUNTS', (1, 1, 1, 1)):
            files, metadata = pack.build(program, source, inv, manifest)
            self.assertEqual(files['placement_000200.ms5d'][32:], program[0x200:0x214])
            self.assertEqual(metadata[0]['id'], 'scene-placement:00000200')
            variants = []
            bad = copy.deepcopy(inv); bad['paths'].append(copy.deepcopy(bad['paths'][0])); variants.append(bad)
            bad = copy.deepcopy(inv); bad['paths'] = []; variants.append(bad)
            bad = copy.deepcopy(inv); bad['paths'][0]['rows'][0]['word_at_4'] = 1; variants.append(bad)
            bad = copy.deepcopy(inv); bad['references'][0]['operand_raw_hex'] = '00000202'; variants.append(bad)
            bad = copy.deepcopy(inv); bad['unique_record_count'] = 2; variants.append(bad)
            bad = copy.deepcopy(inv); bad['bounds_pointers'] = [0x400]; variants.append(bad)
            bad = copy.deepcopy(inv); bad['scene_scripts_manifest_sha256'] = '0'*64; variants.append(bad)
            for index, bad in enumerate(variants):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    pack.build(program, source, bad, manifest)


if __name__ == '__main__':
    unittest.main()
