"""Compare 6b/68 lookup, font30 and direct text against original 3918/e84c8."""
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
    report_path = folder / 'verification.json'
    report_path.unlink(missing_ok=True)
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    packed_font = font.read_bytes()
    font_payload = packed_font[32:]
    expected_header = (b'MS5D', 1, 1, 0xe80c8, 0xe80c8, 1024,
                       zlib.crc32(font_payload), 0)
    if (len(packed_font) != 1056 or struct.unpack_from('<4s7I', packed_font) != expected_header
            or font_payload != program[0xe80c8:0xe84c8]):
        raise ValueError('Combined font resource differs from original ROM slice')
    base = 0x60000
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows = [], []
    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)

    def glyph(byte, direct=False):
        if byte == 92:
            return b'\\\\'
        if byte == 64 and not direct:
            return b'@`@'
        return bytes([byte])

    def compare(data, cursor=0x7000, style=0x6b, label='stream'):
        output.unlink(missing_ok=True)
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

    for font_style in (0x6b, 0x68):
        prefix = '' if font_style == 0x6b else 'font68-'
        glyphs = b''.join(glyph(byte) + b' ' for byte in range(1, 256)) + b'\0'
        for palette in range(16):
            compare(glyphs, style=(palette << 8) | font_style,
                    label=prefix + 'all-glyphs-palette-' + str(palette))
        for mark in (0xde, 0xdf):
            data = b''.join(glyph(byte) + bytes([mark]) + b' '
                            for byte in range(1, 256)) + b'\0'
            compare(data, style=0xf00 | font_style,
                    label=prefix + 'all-glyphs-mark-' + hex(mark))
        for selector in b'.:~-au eox`':
            # @ selectors consume a following byte; zero is data there, not terminator.
            for byte in (0, 1, ord('a'), ord('u'), ord('e'), ord('o'), 255):
                compare(b'@' + bytes([selector, byte]) + b'A\0', style=font_style,
                        label=prefix + 'at-%02x-%02x' % (selector, byte))
        for data, label in ((b'\\c' + bytes([font_style]) + b'\\p\x00A\\p\xffB\0',
                             'font-palette-controls'),
                            (b'\\l\x00\x00A\\nB\\rC\0', 'zero-location-newline-return'),
                            (b'\\l\x27\xffA\\rB\0', 'location-boundary'),
                            (b'\\\0A\0', 'escaped-zero'), (b'\0', 'empty')):
            compare(data, style=0xf00 | font_style, label=prefix + label)
        for cursor in (0, 0x74ff, 0xffe0, 0xffff):
            compare(b'A\\rB\0', cursor=cursor, style=0xf00 | font_style,
                    label=prefix + 'cursor-' + str(cursor))

    direct_glyphs = b''.join(glyph(byte, direct=True) + b' '
                             for byte in range(1, 256)) + b'\0'
    for direct_style in range(16):
        for palette in range(16):
            compare(direct_glyphs, style=(palette << 8) | direct_style,
                    label='direct-%02x-all-glyphs-palette-%d' % (direct_style, palette))
        for mark in (0xde, 0xdf):
            data = b''.join(glyph(byte, direct=True) + bytes([mark]) + b' '
                            for byte in range(1, 256)) + b'\0'
            compare(data, style=0xf00 | direct_style,
                    label='direct-%02x-mark-not-consumed-%02x' % (direct_style, mark))
        compare(b'@.a@`@\\p\x00A\\p\xffB\\l\x27\xffC\\nD\\rE\0',
                style=direct_style, label='direct-%02x-literal-at-controls' % direct_style)
        for cursor in (0, 0x74ff, 0xffe0, 0xffff):
            compare(b'A\\rB\0', cursor=cursor, style=0xf00 | direct_style,
                    label='direct-%02x-cursor-%d' % (direct_style, cursor))
    # Font30 applies shared mark transformations, then calls3650 as direct style3.
    # It returns before the lookup fonts' @ grammar, so @ remains literal.
    for palette in range(16):
        compare(direct_glyphs, style=(palette << 8) | 0x30,
                label='font30-all-glyphs-palette-' + str(palette))
        for mark in (0xde, 0xdf):
            data = b''.join(glyph(byte, direct=True) + bytes([mark]) + b' '
                            for byte in range(1, 256)) + b'\0'
            compare(data, style=(palette << 8) | 0x30,
                    label='font30-all-glyphs-mark-%02x-palette-%d' % (mark, palette))
    compare(b'@.a@`@\\p\x00A\\p\xffB\\l\x27\xffC\\nD\\rE\0',
            style=0xf30, label='font30-literal-at-controls')
    for cursor in (0, 0x74ff, 0xffe0, 0xffff):
        compare(b'A\\rB\0', cursor=cursor, style=0xf30,
                label='font30-cursor-' + str(cursor))
    mixed_scripts = (
        b'A\\ch\xb6\xde@.a\\ck\xca\xdf@:o\\c\x03@.a\xb6\xde\xca\xdf\0',
        b'\\c\x00@`@\\p\xffA\\ch\xb3\xde\\n\\ck\xce\xdf\\rB\\c\x0fC\0',
        b'\\ck\xb6\xde\\ch\xb6\xde\\c\x03\xb6\xde\\ch@`\x00A\0',
        b'\\c0\xb6\xde@.a\xca\xdf\\ch@.a\\ck\xce\xdf\\c\x03@`@\\c0B\0',
    )
    for index, data in enumerate(mixed_scripts):
        for style in (3, 0x68, 0xf6b, 0xf30):
            compare(data, style=style, label='mixed-%d-initial-%04x' % (index, style))

    stage_name_count = 0
    for group, address in enumerate(struct.unpack_from('>19I', program, 0x474f4)):
        position = address + 2
        record_index = 0
        while True:
            length = struct.unpack_from('>h', program, position)[0]
            position += 2
            if length == 0:
                break
            if length < 20 or length & 1 or position + length > 0x100000:
                raise ValueError('Original stage record violates catalog length constraints')
            name_address = position + 18
            data = program[name_address:position + length]
            if 0 not in data:
                raise ValueError('Original stage record name lacks terminator')
            compare(data, style=3, label='stage-name-%02d-%02d' % (group, record_index))
            rows[-1].update(source_name_cpu_address=name_address,
                            source_name_rom_offset=name_address,
                            name_and_padding_hex=data.hex())
            position += length
            record_index += 1
            stage_name_count += 1
    if stage_name_count != 59:
        raise ValueError('Expected 59 actual stage record names')
    report_path.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn', 'parser_entry_cpu_address': 0x3918,
        'renderer_cpu_address': 0xe84c8, 'font_table_cpu_addresses': [0xe80c8, 0xe82c8],
        'font_resource_sha256': hashlib.sha256(packed_font).hexdigest(),
        'font_resource_matches_original_slice': True, 'stage_name_count': stage_name_count,
        'cases': len(rows), 'all_ordered_ports_and_final_line_equal': True, 'results': rows,
        'scope': 'Fonts6b/68/30 and direct styles00..0f through unmodified3918/e84c8/3650, '
                 'all nonzero glyphs and 16 palettes for each style, '
                 'DE/DF lookahead combinations, @ selectors, zero operands, c/p/l/n/r stream '
                 'controls and word cursor wrapping, mixed styles and all59 actual stage names. '
                 'Direct glyphs retain literal @ and marks; font30 combines marks and retains literal @. Only ordered port writes and D3 '
                 'low word compared; pixels, other font styles, hardware timing and other '
                 'CPU registers/flags outside scope.'
    }, indent=2) + '\n')
    print('Table text original/C++ match:', len(rows), 'streams')


if __name__ == '__main__':
    main()
