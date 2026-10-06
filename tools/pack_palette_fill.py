"""Pack the normalized selectors of the verified 0x8b64 fill setup.

MS5P IDs in this file are fill selectors, in a distinct catalog namespace.
This exhausts the setup's signed-word address aliases, not the game's palette
catalog or naturally reachable fill inputs. Source word zero is retained;
converted word zero is the MS5P placeholder, and setup preserves RAM word zero.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib

from disassemble_program import load_verified_program
from pack_palettes import extract_record

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
SELECTOR_COUNT = 2048


def extract(program):
    evidence = ((0xc550, '303c00004eb900008b64'),
                (0x8b7a, '207900200004267900200008'),
                (0x8b8a, '0240ffffeb8841f000006100bb82'))
    for offset, expected_hex in evidence:
        expected = bytes.fromhex(expected_hex)
        if program[offset:offset + len(expected)] != expected:
            raise ValueError('Fill setup evidence mismatch at ROM offset 0x%x' % offset)
    source_base = int.from_bytes(program[0x200004:0x200008], 'big')
    lookup_base = int.from_bytes(program[0x200008:0x20000c], 'big')
    records = {}
    for selector in range(SELECTOR_COUNT):
        # Rebase the shared normal-source helper to the signed-word window.
        # The selector remains the on-disk ID; helper_id is only address math.
        helper_id = (selector + 1024) & 0x7ff
        record = extract_record(program, source_base - 32768, lookup_base, helper_id)
        displacement = (selector * 32) & 0xffff
        if displacement & 0x8000:
            displacement -= 65536
        if record[2] != source_base + displacement:
            raise ValueError('Fill selector source address mismatch')
        records[selector] = record
    return records, source_base, lookup_base


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported program revision')
    records, source_base, lookup_base = extract(program)
    payload = b''.join(struct.pack('<I', selector) + records[selector][0] + records[selector][1]
                       for selector in range(SELECTOR_COUNT))
    packed = struct.pack('<4s7I', b'MS5P', 1, SELECTOR_COUNT, 68, len(payload),
                         zlib.crc32(payload), 0, 0) + payload
    destination = root / 'extracted/runtime'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'palette_fill.ms5p').write_bytes(packed)
    manifest = {
        'schema_version': 1, 'id': 'mslug5.palette-fill-selectors',
        'format': 'MS5P', 'version': 1, 'file': 'palette_fill.ms5p',
        'size': len(packed), 'sha256': hashlib.sha256(packed).hexdigest(),
        'source': source, 'catalog_status': 'complete_normalized_fill_selector_domain',
        'catalog_scope': 'All 2048 address aliases of setup 0x8b64; not the full game palette catalog',
        'lookup_profile': 'fill_signed_word', 'bank_base': 0x200000,
        'source_base_rom_offset': source_base, 'source_base_pointer_rom_offset': 0x200004,
        'lookup_base_rom_offset': lookup_base, 'lookup_base_pointer_rom_offset': 0x200008,
        'input_normalization': 'selector = input_id & 0x7ff',
        'source_address_formula': 'source_base + signed16((selector * 32) & 0xffff)',
        'id_namespace': 'palette-fill:<three lowercase hexadecimal digits>',
        'conversion': '0x4718 lookup for words 1..15; MS5P converted word0 is zero; no RGB conversion',
        'setup_word0': '0x8b64 preserves the destination RAM word0, rather than using source word0',
        'setup': {'cpu_address': 0x8b64, 'rom_offset': 0x8b64,
                  'signed_index_cpu_address': 0x8b90, 'signed_index_rom_offset': 0x8b90},
        'direct_requests': [{'instruction_cpu_address': 0xc550,
                             'instruction_rom_offset': 0xc550, 'input_id': 0,
                             'selector': 0, 'call_cpu_address': 0xc554,
                             'call_rom_offset': 0xc554}],
        'natural_usage': 'unknown for all selectors; a static direct caller requests selector 0',
        'records': [
            {'id': selector, 'stable_key': 'palette-fill:%03x' % selector,
             'source_rom_offset': records[selector][2],
             'source_cpu_address': records[selector][2],
             'source_bank': 'established bank base 0x200000',
             'lookup_rom_offsets': records[selector][3],
             'usage': 'referenced_by_direct_setup_request' if selector == 0 else 'unknown',
             'natural_usage': 'unknown'}
            for selector in range(SELECTOR_COUNT)]}
    (destination / 'palette_fill.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Packed %d fill selectors, %d bytes; natural usage unknown' % (SELECTOR_COUNT, len(packed)))


if __name__ == '__main__':
    main()
