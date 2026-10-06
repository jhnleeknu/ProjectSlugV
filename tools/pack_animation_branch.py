"""Pack the reviewed two-way animation loop and bounded callback data."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from verify_sprite_blocks import resolve_blocks


GROUP = 0xf2
GROUP_SETUP_ADDRESSES = (0x2b6e6, 0x2b7ce)


def extract(program):
    for address in GROUP_SETUP_ADDRESSES:
        if program[address:address+6] != bytes.fromhex('3d7c00f20020'):
            raise ValueError('Composition group setup changed at '+hex(address))
    if program[0x2bb06:0x2bb16] != bytes.fromhex('227c00065f56303c01004eb900049f8c'):
        raise ValueError('Animation caller changed')
    start, end = 0x65f56, 0x662c2
    cursor = start
    rows = []
    while cursor < end:
        at = cursor
        op = program[at]
        row = {'address': at, 'opcode': op}
        if op == 12:
            row.update(desired=program[at+1], selector=int.from_bytes(program[at+2:at+4], 'big'),
                       target=int.from_bytes(program[at+4:at+8], 'big'))
            if row['selector'] != 31 or row['target'] not in (start, 0x6604c):
                raise ValueError('Unexpected branch')
            cursor += 8
        elif op == 20:
            row.update(selector=program[at+1], table=int.from_bytes(program[at+2:at+6], 'big'))
            if row['selector'] not in (29, 30): raise ValueError('Unexpected callback')
            cursor += 6
        elif op == 16:
            selector = program[at+1]
            length = int.from_bytes(program[at+2:at+4], 'big')
            if (selector, length) not in ((30, 40), (29, 136)):
                raise ValueError('Unexpected indexed list')
            items = []
            for offset in range(0, length, 8):
                item = at+4+offset
                if program[item] != 4: raise ValueError('Non-draw list item')
                items.append({'address': item, 'identifier_operand': int.from_bytes(program[item+4:item+8], 'big')})
            row.update(selector=selector, length=length, items=items)
            cursor += 4+length
        elif op == 0:
            if program[at+1] != 1: raise ValueError('Unexpected duration')
            cursor += 2
        elif op == 8:
            row['target'] = int.from_bytes(program[at+2:at+6], 'big')
            if row['target'] not in (start, 0x6604c): raise ValueError('Unexpected loop target')
            cursor += 6
        else: raise ValueError('Unsupported opcode at '+hex(at))
        rows.append(row)
    if cursor != end or len(rows) != 34: raise ValueError('Script boundary changed')
    for index, row in enumerate(rows):
        if row['opcode'] != 20: continue
        following = rows[index+1]
        if following['opcode'] != 16 or following['selector'] != row['selector']:
            raise ValueError('Callback/list selection mismatch')
        count = len(following['items'])
        if row['table'] < 0x6431a or row['table']+count*4 > 0x6447a:
            raise ValueError('Callback data window is incomplete')
        row['list_bounded_data_bytes'] = count*4
    return start, program[start:end], rows


def pack(magic, base, data):
    return struct.pack('<4s7I', magic, 1, 1, base, base, len(data), zlib.crc32(data), 0)+data


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    base, data, rows = extract(program)
    identifiers = set()
    for row in rows:
        for item in row.get('items', []):
            operand = item['identifier_operand']
            if operand != 0x7ff800:
                identifiers.add(operand | GROUP)
    if len(identifiers) != 57:
        raise ValueError('Composition dependency count changed')
    destination = root/'extracted/runtime'
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for name, magic, at, payload in (
        ('animation_065f56.ms5a', b'MS5A', base, data),
        ('branch_data_06431a.ms5d', b'MS5D', 0x6431a, program[0x6431a:0x6447a])):
        packed = pack(magic, at, payload)
        (destination/name).write_bytes(packed)
        files.append({'file': name, 'source_cpu_address': at, 'source_rom_offset': at,
                      'payload_size': len(payload), 'sha256': hashlib.sha256(packed).hexdigest()})
    compositions = []
    for identifier in sorted(identifiers):
        bank, offset, payload, blocks = resolve_blocks(program, identifier)
        packed = struct.pack('<4s7I', b'MS5C', 1, 2, identifier, offset, len(payload),
                             zlib.crc32(payload), 0)+payload
        name = 'composition_%06x.ms5c'%identifier
        (destination/name).write_bytes(packed)
        compositions.append({'packed_id': identifier, 'file': name, 'bank_base': bank,
                             'source_rom_offset': offset, 'source_cpu_address': offset-bank+0x200000,
                             'blocks': len(blocks), 'payload_size': len(payload),
                             'sha256': hashlib.sha256(packed).hexdigest()})
    manifest = {'source': source, 'schema_version': 1, 'files': files, 'commands': rows,
                'field_data': 'data_04a76c.ms5d', 'caller': 0x2bb10,
                'group': GROUP,
                'group_evidence': [{'source_cpu_address': address, 'source_rom_offset': address,
                                    'instruction_bytes': '3d7c00f20020'}
                                   for address in GROUP_SETUP_ADDRESSES],
                'compositions': compositions,
                'scope': 'Two connected four-frame loops with statically connected initializer group 0xf2 and 57 composition dependencies. Callback data covers list-bounded indices 0..4 and 0..16; no claim that other indices are impossible. Controlled runtime behavior is verified separately. Natural gameplay reachability and palette binding remain unverified.'}
    (destination/'animation_branch.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Packed two-way animation:', len(data), 'bytes;', len(rows), 'commands;',
          len(compositions), 'composition dependencies')


if __name__ == '__main__': main()
