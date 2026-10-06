"""Verify the original 9086 request-bit selector without assigning UI semantics."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def model(ram):
    buttons = (2 if ram[0x4cb9] & 128 else 0) | (8 if ram[0x4cbf] & 128 else 0)
    if ram[0x12] != 2:
        return buttons if ram[0xf002] else 0
    if not ram[0xfd82]:
        value = ram[0x4cb5]
    else:
        value = (buttons & ram[0x4cb4] & 10) if ram[0xf002] else 0
    if ram[0xfdb6] in (0, 3):
        value &= 253
    if ram[0xfdb7] in (0, 3):
        value &= 247
    return value


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    folder = root / 'artifacts/control_request'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out = folder / 'input.bin', folder / 'output.bin'
    count = 0
    seen = set()

    def verify(ram):
        nonlocal count
        expected = model(ram)
        cpu.mem_write(0x100000, bytes(ram))
        cpu.reg_write(UC_M68K_REG_D0, 0xdeadbeef)
        call(cpu, 0x9086)
        actual = cpu.reg_read(UC_M68K_REG_D0)
        if actual != expected or bytes(cpu.mem_read(0x100000, 65536)) != ram:
            raise ValueError('Original selector/model mismatch')
        inp.write_bytes(ram)
        subprocess.run([str(root / 'build/read_control_request'), str(inp), str(out)], check=True)
        if out.read_bytes() != bytes([expected]):
            raise ValueError('C++ selector mismatch')
        count += 1
        seen.add(expected)

    statuses = ((0, 0), (0, 1), (1, 0), (1, 1), (3, 3), (255, 255))
    for value, status in itertools.product(range(256), statuses):
        ram = bytearray(65536)
        ram[0x12] = 2
        ram[0x4cb5] = value
        ram[0xfdb6], ram[0xfdb7] = status
        verify(ram)
    flags = ((0, 0), (128, 0), (0, 128), (128, 128), (127, 255), (255, 127))
    for mode, pair, enabled, mask, status in itertools.product(
            (0, 2), flags, (0, 1), (0, 2, 8, 10, 255), statuses):
        ram = bytearray(65536)
        ram[0x12] = mode
        ram[0xfd82] = 255
        ram[0xf002] = enabled
        ram[0x4cb9], ram[0x4cbf] = pair
        ram[0x4cb4] = mask
        ram[0xfdb6], ram[0xfdb7] = status
        verify(ram)
    for seed in range(128):
        ram = bytearray(hashlib.shake_256(bytes([seed])).digest(65536))
        # Exercise noncanonical mode/gate/status bytes and untouched RAM.
        verify(ram)
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'entry_cpu_and_rom_offset': 0x9086, 'cases': count,
        'original_ram_unchanged': True, 'all_results_equal': True,
        'distinct_results': len(seen),
        'scope': 'Original routine, model, and C++ selector. Raw bit semantics only; '
                 'physical input acquisition and full caller state machine remain unverified.'
    }, indent=2) + '\n')
    print('Control request original/C++ match:', count, 'cases;', len(seen), 'distinct results')


if __name__ == '__main__':
    main()
