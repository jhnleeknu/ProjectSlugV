"""Compare shared text measurement with original38e8, including non-ASCII bytes."""
import json
from pathlib import Path
import struct
import subprocess
import zlib
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_D3, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from pack_control_menu import extract


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    folder = root / 'artifacts/text_measure'
    folder.mkdir(parents=True, exist_ok=True)
    resource = folder / 'fixture.ms5d'
    cpu = make_cpu(program)
    rows = []

    def compare(data, address, style, line, label, path=None):
        if path is None:
            resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, address, address,
                                             len(data), zlib.crc32(data), 0) + data)
            path = resource
            cpu.mem_write(address, data)
        cpu.reg_write(UC_M68K_REG_A0, address)
        cpu.reg_write(UC_M68K_REG_D1, 0xdead0000 | style)
        cpu.reg_write(UC_M68K_REG_D3, 0xbeef0000 | line)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        cpu.emu_start(0x38e8, 0xff000, count=2000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original did not return: ' + label)
        expected = {'glyph_count': cpu.reg_read(UC_M68K_REG_D0) & 65535,
                    'style': cpu.reg_read(UC_M68K_REG_D1) & 65535,
                    'line': cpu.reg_read(UC_M68K_REG_D3) & 65535,
                    'end_cpu_address': cpu.reg_read(UC_M68K_REG_A0)}
        result = subprocess.run([str(root / 'build/measure_fixed_text'), str(path),
                                 str(address), str(style), str(line)], check=True,
                                text=True, capture_output=True)
        if json.loads(result.stdout) != expected:
            raise ValueError('Text measurement mismatch: ' + label)
        rows.append({'label': label, **expected})

    _, pointers = extract(program)
    for pointer in pointers:
        compare(None, pointer, 0, 0x7000, hex(pointer), root / 'extracted/runtime/control_menu.ms5d')
    base = 0x60000
    for glyph in range(1, 256):
        raw = bytes([glyph]) if glyph != 92 else b'\\\\'
        compare(b'\\c\x00\\p\xff' + raw + b'\0garbage', base, 0xabcd, 0x7000, 'glyph-' + str(glyph))
    for x in range(40):
        for y in (0, 31, 255):
            compare(b'\\l' + bytes([x, y]) + b'A\\rB\0', base, 0xffff, 0x7400,
                    'location-%d-%d' % (x, y))
    for line in (0, 0x7000, 0x74fe, 65535):
        compare(b'\\nA\0', base, 0x1234, line, 'newline-' + str(line))
    compare(b'\\\0A\0', base, 0x1234, 0x7000, 'escaped-zero')
    compare(b'A' * 65536 + b'\0', base, 0x61, 0x7000, 'word-count-wrap')
    if rows[-1]['glyph_count'] != 0:
        raise ValueError('Count did not wrap at16 bits')
    # These input errors intentionally reject rather than emulate a CPU trap.
    for data in (b'', b'A', b'\\', b'\\c', b'\\l\x00', b'\\l\x28\x00\0', b'\\n\0'):
        resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, base, base,
                                         len(data), zlib.crc32(data), 0) + data)
        result = subprocess.run([str(root / 'build/measure_fixed_text'), str(resource),
                                 str(base), '0', str(0x74ff)], capture_output=True)
        if result.returncode == 0:
            raise ValueError('Invalid/trapping text was accepted')
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'cases': len(rows), 'rejected_cases': 7, 'results': rows,
        'scope': '38e8 count, style, line and consumed address; all byte glyphs. '
                 'No rendering or glyph mapping claim for non-ASCII/font variants.'
    }, indent=2) + '\n')
    print('Text measurement original/C++ match:', len(rows), 'cases; 7 rejected inputs')


if __name__ == '__main__':
    main()
