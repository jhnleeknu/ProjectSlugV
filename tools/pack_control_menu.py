"""Preserve the verified 93e0 menu descriptor and referenced text in MS5D."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program


BASE = 0x937e
MENU = 0x93e0
END = 0x9430


def extract(program):
    if program[0x92da:0x92ec] != bytes.fromhex('41fa0104303c0004323c00084eb90000a29c'):
        raise ValueError('Menu initialization caller changed')
    title, width, height, callback6, callback10, flags = struct.unpack_from('>IBBIIH', program, MENU)
    items = []
    cursor = MENU + 16
    while cursor + 4 <= END:
        text = int.from_bytes(program[cursor:cursor + 4], 'big')
        if text == 0xffffffff:
            cursor += 4
            break
        if cursor + 10 > END:
            raise ValueError('Truncated menu item')
        pointer, callback, argument = struct.unpack_from('>IIH', program, cursor)
        items.append({'source_cpu_address': cursor, 'title_address': pointer,
                      'callback': callback, 'argument': argument})
        cursor += 10
    if cursor != END or len(items) != 6:
        raise ValueError('Menu extent changed')
    pointers = [title] + [item['title_address'] for item in items]
    if sorted(pointers) != pointers or pointers[0] != BASE or pointers[-1] >= MENU:
        raise ValueError('Text pointer window changed')
    return {'source_cpu_address': MENU, 'title_address': title,
            'min_width': width, 'min_height': height, 'callback6': callback6,
            'callback10': callback10, 'flags': flags, 'end_cpu_address': END,
            'items': items}, pointers


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    descriptor, pointers = extract(program)
    data = program[BASE:END]
    packed = struct.pack('<4s7I', b'MS5D', 1, 1, BASE, BASE, len(data), zlib.crc32(data), 0) + data
    folder = root / 'extracted/runtime'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'control_menu.ms5d').write_bytes(packed)
    (folder / 'control_menu.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'menu:000093e0', 'format': 'MS5D', 'version': 1,
        'file': 'control_menu.ms5d', 'source': source, 'source_cpu_address': BASE,
        'source_rom_offset': BASE, 'size': len(packed), 'sha256': hashlib.sha256(packed).hexdigest(),
        'descriptor': descriptor, 'text_addresses': pointers,
        'text_encoding': 'Original 386e byte/control stream, retained without Unicode conversion',
        'scope': 'One caller-backed menu descriptor and adjacent referenced text; callbacks remain code addresses. '
                 'Not a complete menu catalog or executable menu state machine.'
    }, indent=2) + '\n')
    print('Packed menu 93e0:', len(descriptor['items']), 'items;', len(packed), 'bytes')


if __name__ == '__main__':
    main()
