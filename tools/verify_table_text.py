"""Compare font6b e84c8 glyph mapping through original3918 stream parser."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A7,
                               UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_menu_event import SOURCE_SHA256


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    folder = root / 'artifacts/table_text'
    folder.mkdir(parents=True, exist_ok=True)
    resource, output = folder / 'fixture.ms5d', folder / 'writes.bin'
    font = root / 'extracted/runtime/menu_font_6b.ms5d'
    base = 0x60000
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows = [], []
    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)

    def glyph(byte):
        if byte == 92:
            return b'\\\\'
        if byte == 64:
            return b'@`@'
        return bytes([byte])

    def compare(data, cursor=0x7000, style=0x6b, label='stream'):
        cpu.mem_write(base, data)
        resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, base, base,
                                        len(data), zlib.crc32(data), 0) + data)
        for reg, value in ((UC_M68K_REG_A0, base), (UC_M68K_REG_A1, 0xe84c8),
                           (UC_M68K_REG_D0, cursor), (UC_M68K_REG_D1, style),
                           (UC_M68K_REG_A7, 0x1feffc)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(0x3918, 0xff000, count=2000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original did not return: ' + label)
        expected = b''.join(struct.pack('>BII', *write) for write in writes)
        result = subprocess.run([str(root / 'build/trace_table_text'), str(resource), str(base),
                                 str(cursor), str(style), str(output), str(font)],
                                 capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected ' + label + ': ' + result.stderr)
        actual_line = json.loads(result.stdout)
        expected_line = {'line': cpu.reg_read(UC_M68K_REG_D3) & 65535}
        if output.read_bytes() != expected or actual_line != expected_line:
            actual = output.read_bytes()
            mismatch = next((i for i in range(min(len(actual), len(expected))) if actual[i] != expected[i]), None)
            raise ValueError('Table text mismatch: ' + repr((label, cursor, style, len(expected)//9, len(actual)//9, mismatch, expected_line, actual_line)))
        rows.append({'label': label, 'initial_cursor': cursor, 'style': style,
                     'final_line': expected_line['line'], 'port_events': len(writes),
                     'ports_sha256': hashlib.sha256(expected).hexdigest()})

    glyphs = b''.join(glyph(byte) + b' ' for byte in range(1, 256)) + b'\0'
    for palette in range(16):
        compare(glyphs, style=(palette << 8) | 0x6b, label='all-glyphs-palette-' + str(palette))
    for mark in (0xde, 0xdf):
        data = b''.join(glyph(byte) + bytes([mark]) + b' ' for byte in range(1, 256)) + b'\0'
        compare(data, style=0xf6b, label='all-glyphs-mark-' + hex(mark))
    for selector in b'.:~-au eox`':
        # @ selectors consume a following byte; zero is data there, not terminator.
        for byte in (0, 1, ord('a'), ord('u'), ord('e'), ord('o'), 255):
            compare(b'@' + bytes([selector, byte]) + b'A\0', label='at-%02x-%02x' % (selector, byte))
    for data, label in ((b'\\c\x6b\\p\x00A\\p\xffB\0', 'font-palette-controls'),
                        (b'\\l\x00\x00A\\nB\\rC\0', 'zero-location-newline-return'),
                        (b'\\l\x27\xffA\\rB\0', 'location-boundary'),
                        (b'\\\0A\0', 'escaped-zero'), (b'\0', 'empty')):
        compare(data, style=0xf6b, label=label)
    for cursor in (0, 0x74ff, 0xffe0, 0xffff):
        compare(b'A\\rB\0', cursor=cursor, style=0xf6b, label='cursor-' + str(cursor))
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn', 'parser_entry_cpu_address': 0x3918,
        'renderer_cpu_address': 0xe84c8, 'font_table_cpu_address': 0xe80c8,
        'cases': len(rows), 'all_ordered_ports_and_final_line_equal': True, 'results': rows,
        'scope': 'Font6b through unmodified3918/e84c8, all nonzero glyphs and 16 palettes, '
                 'DE/DF lookahead combinations, @ selectors, zero operands, c/p/l/n/r stream '
                 'controls and word cursor wrapping. Only ports and D3 low word compared; '
                 'other fonts, pixels, hardware timing and CPU registers/flags outside scope.'
    }, indent=2) + '\n')
    print('Table text original/C++ match:', len(rows), 'streams')


if __name__ == '__main__':
    main()
