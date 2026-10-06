"""Compare the unmodified 9136 inactive entry with C++ RAM and return byte."""
import hashlib
import json
from pathlib import Path
import subprocess

import unicorn
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root / 'artifacts/control_activation'
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / 'verification.json'
    report.unlink(missing_ok=True)
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    inp, out = folder / 'input.bin', folder / 'output.bin'
    command = [str(root / 'build/activate_control'), str(inp), str(out)]
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
            cpu.mem_write(0x100000, bytes(ram))
            cpu.reg_write(UC_M68K_REG_D0, 0xdeadbeef)
            call(cpu, 0x9136)
            original_ram = bytes(cpu.mem_read(0x100000, 65536))
            original_status = cpu.reg_read(UC_M68K_REG_D0) & 255
            inp.write_bytes(ram)
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            status = json.loads(result.stdout)['status']
            if out.read_bytes() != original_ram or status != original_status:
                raise ValueError('Original/C++ control activation mismatch: ' +
                                 repr((pending, configuration)))
            counts['activated' if status == 0 else 'idle'] += 1

    # Failure paths must preserve existing outputs, and aliases preserve input.
    sentinel = b'output sentinel'
    ram[0x7df0] = 1
    inp.write_bytes(ram)
    out.write_bytes(sentinel)
    if subprocess.run(command, capture_output=True).returncode == 0 or out.read_bytes() != sentinel:
        raise ValueError('Active-state rejection did not preserve output')
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        if subprocess.run(command, capture_output=True).returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Invalid-size rejection did not preserve output')
    ram[0x7df0] = 0
    inp.write_bytes(ram)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        result = subprocess.run([command[0], str(inp), str(alias)], capture_output=True)
        if result.returncode == 0 or inp.read_bytes() != ram:
            raise ValueError('Input/output alias was not safely rejected')
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped ROM bytes changed during verification')
    report.write_text(json.dumps({
        'source': source, 'entry_cpu_and_rom_offset': 0x9136,
        'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
        'cases': sum(counts.values()), 'counts': counts,
        'original_rom_unmodified': True, 'all_ram_and_return_byte_equal': True,
        'cli_failure_and_alias_preservation': True,
        'scope': 'Inactive entry only. Active state is explicitly rejected; '
                 'CPU register state, physical input and full game reachability remain unverified.'
    }, indent=2) + '\n')
    print('Control activation original/C++ match:', sum(counts.values()), 'cases;', counts)


if __name__ == '__main__':
    main()
