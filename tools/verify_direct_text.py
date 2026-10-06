"""Verify3918/3650 direct glyph rendering including address-only port writes."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A7,
                               UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from pack_control_menu import extract
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    events = []
    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            # Unicorn may sign-extend word writes in its callback; only
            # size bytes reach the port. Preserve the actual bus value.
            events.append((size, address, value & ((1 << (size * 8)) - 1)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    folder = root / 'artifacts/direct_text'
    folder.mkdir(parents=True, exist_ok=True)
    resource, output = folder / 'fixture.ms5d', folder / 'writes.bin'
    rows = []

    def compare(path, address, cursor, style, label):
        for reg, value in ((UC_M68K_REG_A0, address), (UC_M68K_REG_A1, 0x3650),
                           (UC_M68K_REG_D0, cursor), (UC_M68K_REG_D1, style)):
            cpu.reg_write(reg, value)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        events.clear()
        cpu.emu_start(0x3918, 0xff000, count=2000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original text did not return')
        expected = b''.join(struct.pack('>BII', *event) for event in events)
        subprocess.run([str(root / 'build/trace_direct_text'), str(path), str(address),
                        str(cursor), str(style), str(output)], check=True)
        if output.read_bytes() != expected:
            raise ValueError('Direct text port mismatch: ' + label)
        if any(event != (2, 0x3c0000, 0x8200) for event in events[1::2]):
            raise ValueError('Address reset sequence changed')
        rows.append({'label': label, 'style': style, 'initial_cursor': cursor,
                     'port_events': len(events), 'sha256': hashlib.sha256(expected).hexdigest()})

    _, pointers = extract(program)
    for pointer in pointers:
        for style in (3, 0x103, 0x603, 0xb03):
            compare(root / 'extracted/runtime/control_menu.ms5d', pointer, 0x7088, style,
                    'menu-%x' % pointer)
    glyphs = b''.join(bytes([g]) if g != 92 else b'\\\\' for g in range(1, 256)) + b'\0'
    base = 0x60000
    def fixture(data):
        cpu.mem_write(base, data)
        resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, base, base,
                                         len(data), zlib.crc32(data), 0) + data)
    fixture(glyphs)
    for index in range(256):
        style = (((index * 7) & 255) << 8) | index
        compare(resource, base, 0x7000, style, 'all-glyphs-' + str(index))
    for cursor in (0, 0x7000, 0x74ff, 0xffe0, 0xffff):
        compare(resource, base, cursor, 0xffff, 'cursor-' + str(cursor))
    fixture(b'\\c\xff\\p\xffA\\l\x27\xffB\\rC\0')
    compare(resource, base, 0x7000, 0, 'control-sequence')
    fixture(b'\0')
    compare(resource, base, 0x7000, 0, 'empty')
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'cases': len(rows), 'all_ordered_port_events_equal': True,
        'glyph_style_combinations': 256 * 255, 'results': rows,
        'scope': '3918/3650 port address, width, value and order, including 8200 resets. '
                 'Actual menu strings included; no full menu layout, palette binding, pixel or timing claim.'
    }, indent=2) + '\n')
    print('Direct text original/C++ match:', len(rows), 'streams; 65280 glyph/style combinations')


if __name__ == '__main__':
    main()
