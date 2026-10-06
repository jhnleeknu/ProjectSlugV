"""Preserve the control menu and its three statically referenced child menus."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from pack_control_menu import extract

BASE = 0x937e
END = 0x9a98
MENUS = (0x93e0, 0x958a, 0x978a, 0x99ee)


def catalog(program):
    extract(program)  # Original root caller/extent check.
    edges = ((0x94aa, 0x958a), (0x94c8, 0x978a), (0x94e4, 0x99ee))
    for caller, target in edges:
        if (program[caller:caller+2] != bytes.fromhex('41fa') or
                caller + 2 + int.from_bytes(program[caller+2:caller+4], 'big', signed=True) != target or
                program[caller+4:caller+10] != bytes.fromhex('4ef90000a0a0')):
            raise ValueError('Child-menu caller changed')
    result = []
    for menu in MENUS:
        title, width, height, callback6, callback10, flags = struct.unpack_from('>IBBIIH', program, menu)
        items = []
        cursor = menu + 16
        while cursor + 4 <= END:
            pointer = struct.unpack_from('>I', program, cursor)[0]
            if pointer == 0xffffffff:
                cursor += 4
                break
            if cursor + 10 > END or len(items) >= 255:
                raise ValueError('Menu exceeds expected window')
            pointer, callback, argument = struct.unpack_from('>IIH', program, cursor)
            items.append({'source_cpu_address': cursor, 'title_address': pointer,
                          'callback': callback, 'argument': argument})
            cursor += 10
        else:
            raise ValueError('Missing menu terminator')
        for pointer in [title] + [item['title_address'] for item in items]:
            if pointer not in (0, 0xfffffffe) and not BASE <= pointer < END:
                raise ValueError('Text outside preserved data window')
        result.append({'id': 'menu:%08x' % menu, 'source_cpu_address': menu,
                       'title_address': title, 'min_width': width, 'min_height': height,
                       'callback6': callback6, 'callback10': callback10, 'flags': flags,
                       'end_cpu_address': cursor, 'items': items})
    if [len(d['items']) for d in result] != [6, 10, 10, 15] or result[-1]['end_cpu_address'] != END:
        raise ValueError('Menu catalog profile changed')
    return result, [{'caller_cpu_address': a, 'child_cpu_address': b} for a, b in edges]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    descriptors, edges = catalog(program)
    data = program[BASE:END]
    packed = struct.pack('<4s7I', b'MS5D', 1, 1, BASE, BASE, len(data), zlib.crc32(data), 0) + data
    folder = root / 'extracted/runtime'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'control_menu_tree.ms5d').write_bytes(packed)
    (folder / 'control_menu_tree.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'menu-tree:000093e0', 'format': 'MS5D', 'version': 1,
        'file': 'control_menu_tree.ms5d', 'source': source,
        'source_cpu_address': BASE, 'source_rom_offset': BASE, 'size': len(packed),
        'sha256': hashlib.sha256(packed).hexdigest(), 'descriptors': descriptors,
        'static_child_references': edges,
        'scope': 'Four menu descriptors and their text in one unchanged fixed-ROM window. '
                 'Intervening code/data bytes are retained as opaque source bytes; not executed by the loader. '
                 'Callback bodies are not reconstructed by packing. Child rendering and event behavior remain separate work.'
    }, indent=2) + '\n')
    print('Packed control menu tree:', len(descriptors), 'menus;', len(packed), 'bytes')


if __name__ == '__main__':
    main()
