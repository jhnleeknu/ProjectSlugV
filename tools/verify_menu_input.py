"""Exhaustively compare the two-byte menu decision phase, stopping before actions."""
import hashlib
import json
from pathlib import Path
import subprocess
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A2, UC_M68K_REG_A5, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A2, 0x107efe)
    exits = {0xa566: (1, 0), 0xa574: (2, 0), 0xa596: (3, 1),
             0xa5a0: (3, 2), 0xa58c: (3, 4), 0xa582: (3, 3), 0xa5ce: (0, 0)}
    changes = []
    def stop(cpu, address, size, user):
        if address in exits:
            cpu.emu_stop()
    def changed(cpu, access, address, size, value, user):
        changes.append((address, size, value & 255))
    cpu.hook_add(UC_HOOK_CODE, stop, begin=0xa562, end=0xa5ce)
    cpu.hook_add(UC_HOOK_MEM_WRITE, changed, begin=0x100000, end=0x10ffff)
    table = bytearray()
    for flags in (0, 1, 2, 3, 255):
        cpu.mem_write(0x107f0b, bytes([flags]))
        for first in range(256):
            cpu.mem_write(0x104cba, bytes([first]))
            for second in range(256):
                cpu.mem_write(0x104cc0, bytes([second]))
                changes.clear()
                cpu.emu_start(0xa472, 0xff000, count=200)
                pc = cpu.reg_read(UC_M68K_REG_PC)
                if pc not in exits:
                    raise ValueError('Original did not reach a decision')
                kind, event = exits[pc]
                sources = cpu.mem_read(0x107f1a, 1)[0]
                expected_changes = [(0x107f1a, 1, 0)]
                if kind:
                    expected_changes.append((0x107f1a, 1, sources))
                if changes != expected_changes:
                    raise ValueError('Unexpected original RAM side effect')
                table.extend((kind, event, sources))
    folder = root / 'artifacts/menu_input'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'cpp_table.bin'
    subprocess.run([str(root / 'build/menu_input_table'), str(output)], check=True)
    if output.read_bytes() != table:
        raise ValueError('C++ input decision table differs from original')
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'cases': len(table) // 3, 'sha256': hashlib.sha256(table).hexdigest(),
        'all_decisions_and_ram_changes_equal': True,
        'scope': 'a472 decision phase through first action entry. No navigation, draw or callback executed. '
                 'All 256x256 input pairs for enable masks0/1/2/3/255. C++ full RAM preservation checked.'
    }, indent=2) + '\n')
    print('Menu input original/C++ match:', len(table) // 3, 'decisions')


if __name__ == '__main__':
    main()
