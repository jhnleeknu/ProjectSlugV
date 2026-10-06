"""Package the two reviewed sprite rectangles for direct C++ runtime use."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from verify_sprite_composition import resolve
from pack_palettes import extract


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    _, bindings = extract(program)
    destination = root/'extracted/runtime'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for identifier, style, caller in ((0x2152, 0x1500, 0xde170), (0x2952, 0x1600, 0xde18e)):
        bank, offset, data = resolve(program, identifier)
        binding = [b for b in bindings if b['table_rom_offset'] == 0xddf08 and b['slot'] == style >> 8]
        if len(binding) != 1:
            raise ValueError('Expected exactly one reviewed palette binding')
        packed = struct.pack('<4s7I', b'MS5C', 1, 1, identifier, offset, len(data), zlib.crc32(data), 0)+data
        filename = 'composition_%06x.ms5c' % identifier
        (destination/filename).write_bytes(packed)
        records.append({'id': 'mslug5.composition.%06x' % identifier, 'packed_id': identifier,
                        'file': filename, 'size': len(packed), 'sha256': hashlib.sha256(packed).hexdigest(),
                        'source_rom_offset': offset, 'source_cpu_address': offset-bank+0x200000,
                        'bank_base': bank, 'group': (identifier>>3)&255, 'item': (identifier>>11)&4095,
                        'payload_sha256': hashlib.sha256(data).hexdigest(),
                        'width': data[6], 'height': data[7],
                        'observed_call': {'rom_offset': caller, 'style': style, 'palette_binding': binding[0]}})
    manifest = {'schema_version': 1, 'format': 'MS5C', 'version': 1, 'kind': 'normal_single_rectangle',
                'source': source, 'catalog_status': 'incomplete_sparse',
                'scope': 'Two reviewed compositions; palette bindings are caller context, not intrinsic composition properties.',
                'records': records}
    (destination/'compositions.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Packed', len(records), 'C++ composition resources; catalog incomplete')


if __name__ == '__main__':
    main()
