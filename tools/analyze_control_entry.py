"""Verify the inactive-state entry path of 9136; active menu paths remain open."""
import hashlib
import json
from pathlib import Path
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_control_request import model


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    counts = {'activated': 0, 'idle': 0}
    for pending in range(256):
        for configuration in range(32):
            ram = bytearray(hashlib.shake_256(bytes([pending, configuration])).digest(65536))
            ram[0x7df0] = 0
            ram[0x7df1] = pending
            ram[0xf000] = 2 if configuration & 1 else 0
            ram[0x7def] = 255 if configuration & 2 else 0
            ram[0x12] = 2
            ram[0xfd82] = 0
            ram[0x4cb5] = (0, 2, 8, 10)[(configuration >> 2) & 3]
            ram[0xfdb6] = ram[0xfdb7] = 3 if configuration & 16 else 1
            expected = bytearray(ram)
            request = model(ram) if (ram[0xf000] & 2 or not ram[0x7def]) else 0
            selected = pending or (1 if request & 2 else 2 if request & 8 else 0)
            result = 0 if selected else 1
            if selected:
                expected[0x7df0] = selected
                expected[0x7df1] = 0
                expected[0x7df6:0x7dfa] = bytes(4)
                expected[0x4cd2:0x4cd4] = bytes.fromhex('1002')
                expected[0x7df3] = 255
                expected[0x7dfc] = ram[0x4caa]
                expected[0x7dfd] = ram[0x4cb0]
            cpu.mem_write(0x100000, bytes(ram))
            cpu.reg_write(UC_M68K_REG_D0, 0xdeadbeef)
            call(cpu, 0x9136)
            if cpu.reg_read(UC_M68K_REG_D0) != result or bytes(cpu.mem_read(0x100000, 65536)) != expected:
                raise ValueError('Control entry mismatch: ' + repr((pending, configuration)))
            counts['activated' if selected else 'idle'] += 1
    folder = root / 'artifacts/control_request'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'entry_verification.json').write_text(json.dumps({
        'source': source, 'entry_cpu_and_rom_offset': 0x9136, 'counts': counts,
        'all_ram_and_return_equal': True,
        'scope': 'Original inactive-state entry only. No C++ entry-state implementation yet; '
                 'active state, menu dependencies, physical input and full game reachability pending.'
    }, indent=2) + '\n')
    print('Original inactive control entry matches:', counts)


if __name__ == '__main__':
    main()
