"""Compare original 9430 (including actual 9086) with C++ header update."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

import unicorn

from unicorn.m68k_const import UC_M68K_REG_A2, UC_M68K_REG_A5
from disassemble_program import load_verified_program
from verify_control_request import model as request_model
from verify_object_reset import make_cpu
from verify_palette_state import call


def model(ram, a2):
    expected = bytearray(ram)
    request = request_model(ram)
    selected = ((ram[0x7df0] & 1 and request & 2) or
                (ram[0x7df0] & 2 and request & 8))
    if selected:
        expected[0x7dfa:0x7dfc] = b'\x00\x01'
        expected[0x7f1b] = 2
        a2 = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
    return expected, a2, bool(selected)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    folder = root / 'artifacts/menu_header'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder / 'verification.json'
    if report_path.exists():
        report_path.unlink()
    inp, out = folder / 'input.bin', folder / 'output.bin'
    count = 0
    selected_counts = {False: 0, True: 0}

    def base():
        return bytearray(hashlib.shake_256(
            b'menu-header-v1' + count.to_bytes(4, 'big')).digest(65536))

    def verify(ram):
        nonlocal count
        a2 = (0, 0x107efe, 0xdeadbeef, 0xffffffff)[count % 4]
        expected, expected_a2, selected = model(ram, a2)
        cpu.mem_write(0x100000, bytes(ram))
        cpu.reg_write(UC_M68K_REG_A2, a2)
        call(cpu, 0x9430)
        if (bytes(cpu.mem_read(0x100000, 65536)) != expected or
                cpu.reg_read(UC_M68K_REG_A2) != expected_a2):
            raise ValueError(f'Original header/model mismatch in case {count}')
        inp.write_bytes(ram)
        result = subprocess.run([str(root / 'build/update_menu_header'),
                                 str(inp), str(out), hex(a2)],
                                check=True, capture_output=True, text=True)
        if out.read_bytes() != expected or json.loads(result.stdout) != {'a2': expected_a2}:
            raise ValueError(f'C++ header mismatch in case {count}')
        count += 1
        selected_counts[selected] += 1

    # Exhaust low request/enable bits, with unrelated high bits also set.
    for request, enabled in itertools.product(range(16), range(16)):
        ram = base()
        ram[0x12] = 2
        ram[0xfd82] = 0
        ram[0xfdb6] = ram[0xfdb7] = 1
        ram[0x4cb5] = request | 0xf0
        ram[0x7df0] = enabled | 0xf0
        verify(ram)
    # Real selector paths: masks, flags, status gates, and noncanonical mode.
    for mode, gate, live, flags, mask, status in itertools.product(
            (0, 2, 255), (0, 1, 255), (0, 255),
            ((0, 0), (128, 127), (127, 128), (255, 255)),
            (0, 2, 8, 255), ((0, 3), (255, 1))):
        ram = base()
        ram[0x12], ram[0xfd82], ram[0xf002] = mode, gate, live
        ram[0x4cb9], ram[0x4cbf] = flags
        ram[0x4cb4] = mask
        ram[0xfdb6], ram[0xfdb7] = status
        ram[0x7df0] = (0, 1, 2, 3, 0xfc, 0xfd, 0xfe, 0xff)[count % 8]
        verify(ram)
    for unused in range(128):
        verify(base())
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original program memory was modified')
    report = {
        'source': source, 'entry_cpu_address': 0x9430, 'entry_rom_offset': 0x9430,
        'actual_nested_request_entry': 0x9086, 'cases': count,
        'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
        'mapped_original_program_unmodified': True,
        'all_ram_bytes_equal': True, 'a2_equal': True,
        'selected_cases': selected_counts[True],
        'preserved_cases': selected_counts[False],
        'scope': 'Original 9430 and nested 9086 versus model and C++. All 65536 RAM '
                 'bytes and A2, including randomized exit word, mode, current, head '
                 'and invalid head values. No head dereference, CPU flag equivalence, '
                 'physical input acquisition, or full menu behavior claimed.'
    }
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('Menu header original/C++ match:', count, 'cases')


if __name__ == '__main__':
    main()
