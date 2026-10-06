"""Pack evidence-backed palette IDs, retaining source words and normal lookup output.

This sparse catalog is incomplete. It contains IDs from reviewed fixed-slot
binding tables, not a guessed ROM extent or the entire palette catalog.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program

BINDING_TABLES = (0xcb78, 0x4e47a, 0xddf08)


def extract(program):
    source_base = int.from_bytes(program[0x200004:0x200008], 'big')
    lookup_base = int.from_bytes(program[0x200008:0x20000c], 'big')
    records = {}
    bindings = []
    for table in BINDING_TABLES:
        offset = table
        for _ in range(256):
            slot = int.from_bytes(program[offset:offset+2], 'big')
            if slot == 0xffff:
                break
            if slot > 255:
                raise ValueError('Invalid fixed destination slot')
            palette_id = int.from_bytes(program[offset+2:offset+4], 'big')
            flags = program[offset+4]
            bindings.append({'table_rom_offset': table, 'record_rom_offset': offset,
                             'slot': slot, 'source_id': palette_id, 'flags': flags})
            address = source_base + palette_id*32
            if not 0x200000 <= address <= 0x2fdfdf:
                raise ValueError('Palette source outside established bank mapping')
            raw = program[address:address+32]
            converted = bytearray(32)
            lookup_offsets = []
            for color in range(1, 16):
                word = int.from_bytes(raw[color*2:color*2+2], 'big')
                displacement = (word*2) & 0xffff
                if displacement & 0x8000:
                    displacement -= 0x10000
                lookup = lookup_base + displacement
                if not 0x200000 <= lookup <= 0x2fdffe:
                    raise ValueError('Lookup outside established bank mapping')
                converted[color*2:color*2+2] = program[lookup:lookup+2]
                lookup_offsets.append(lookup)
            records[palette_id] = (raw, bytes(converted), address, lookup_offsets)
            offset += 6
        else:
            raise ValueError('Binding table missing terminator')
    return records, bindings


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    records, bindings = extract(program)
    payload = b''.join(struct.pack('<I', palette_id)+records[palette_id][0]+records[palette_id][1]
                       for palette_id in sorted(records))
    packed = struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload), zlib.crc32(payload), 0, 0)+payload
    destination = root/'extracted/runtime'
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'palettes.ms5p').write_bytes(packed)
    manifest = {'schema_version': 1, 'id': 'mslug5.palettes', 'format': 'MS5P', 'version': 1,
                'file': 'palettes.ms5p', 'size': len(packed), 'sha256': hashlib.sha256(packed).hexdigest(),
                'source': source, 'catalog_status': 'incomplete_sparse', 'bank_base': 0x200000,
                'conversion': 'normal lookup helper 0x4718; word0 cleared as upload flag; no RGB conversion',
                'bindings': bindings, 'records': [
                    {'id': palette_id, 'source_rom_offset': records[palette_id][2],
                     'lookup_rom_offsets': records[palette_id][3], 'usage': 'referenced_by_fixed_binding_table'}
                    for palette_id in sorted(records)]}
    (destination/'palettes.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Packed %d grounded palette IDs, %d bytes; catalog incomplete' % (len(records), len(packed)))


if __name__ == '__main__':
    main()
