"""Verify original a29c reset/first-menu initialization with native MS5D input."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
                               UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    folder = root / 'artifacts/menu_init'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, resource = [folder / name for name in ('input.bin', 'output.bin', 'fixture.ms5d')]
    cases = 0
    rows = []

    def compare(path, address, x, y, line, label):
        nonlocal cases
        ram = hashlib.shake_256(str(cases).encode()).digest(65536)
        cpu.mem_write(0x100000, ram)
        for reg, value in ((UC_M68K_REG_A0, address), (UC_M68K_REG_D0, x),
                           (UC_M68K_REG_D1, y), (UC_M68K_REG_D3, line)):
            cpu.reg_write(reg, value)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        cpu.emu_start(0xa29c, 0xff000, count=3000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original initialization did not return')
        expected = bytes(cpu.mem_read(0x100000, 65536))
        inp.write_bytes(ram)
        subprocess.run([str(root / 'build/init_menu'), str(inp), str(path), str(out),
                        str(address), str(x), str(y), str(line)], check=True)
        if out.read_bytes() != expected:
            changed = [i for i, (a, b) in enumerate(zip(out.read_bytes(), expected)) if a != b]
            raise ValueError('C++ menu initialization mismatch: ' + repr((label, changed[:20])))
        if expected[0x7f03] != ram[0x7f03] or expected[0x7f12:0x7f16] != ram[0x7f12:0x7f16]:
            raise ValueError('Original preservation assumption changed')
        rows.append({'label': label, 'slot': expected[0x7efe:0x7f0e].hex()})
        cases += 1

    for x, y in itertools.product((0, 4, 255, 65535), (0, 8, 255, 65535)):
        compare(root / 'extracted/runtime/control_menu.ms5d', 0x93e0, x, y, 0x7000, 'actual-menu')

    def fixture(count, flags, minimum, text, second=None):
        base, title = 0x60000, 0x62000
        data = bytearray(0x2000)
        struct.pack_into('>IBBIIH', data, 0, title, minimum, minimum, 0, 0, flags)
        for index in range(count):
            ptr = (0, 0xfffffffe, title)[index % 3]
            if second is not None:
                ptr = title + len(text)
            struct.pack_into('>IIH', data, 16 + index * 10, ptr, 0, 0)
        struct.pack_into('>I', data, 16 + count * 10, 0xffffffff)
        data.extend(text)
        if second is not None:
            data.extend(second)
        resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, base, base,
                                         len(data), zlib.crc32(data), 0) + data)
        cpu.mem_write(base, bytes(data))
        return base

    for count, flags, minimum, length in itertools.product(
            (0, 1, 6, 254, 255), (0, 2, 14), (0, 16, 255), (0, 1, 252, 253, 254, 255, 256, 257)):
        base = fixture(count, flags, minimum, b'A' * length + b'\0')
        compare(resource, base, 4, 8, 0x7000, 'bounds-%d-%d-%d-%d' % (count, flags, minimum, length))
    base = fixture(1, 0, 0, b'\\l\0\0A\0', b'\\nB\0')
    compare(resource, base, 65535, 65535, 0x74ff, 'line-state-across-strings')
    base = fixture(0, 0, 0, b'A' * 65535 + b'\0')
    compare(resource, base, 4, 8, 0x7000, 'word-width-wrap')
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'cases': cases, 'all_ram_equal': True, 'results': rows,
        'scope': 'Original a29c reset and first allocation. Native menu plus synthetic descriptor '
                 'boundaries; no nested push, menu rendering, callbacks or complete frame loop.'
    }, indent=2) + '\n')
    print('Menu initialization original/C++ whole RAM match:', cases, 'cases')


if __name__ == '__main__':
    main()
