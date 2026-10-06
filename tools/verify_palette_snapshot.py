"""Compare palette effect save/restore and subsequent updates with 68000 code."""
import hashlib
import json
from pathlib import Path
import subprocess

from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    for address, expected in ((0xf94, '4eb900008bc8'), (0xfd6, '4eb900008be0')):
        if program[address:address + 6] != bytes.fromhex(expected):
            raise ValueError('Snapshot caller changed')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    folder = root / 'artifacts/palette_snapshot'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out = folder / 'input.bin', folder / 'output.bin'
    counts = {'save': 0, 'restore': 0, 'subsequent_frame': 0, 'temporary_effect_steps': 0}

    def compare(ram, expected, mode):
        cpu.mem_write(0x100000, bytes(ram))
        call(cpu, 0x8bc8 if mode == 'save' else 0x8be0)
        actual = bytes(cpu.mem_read(0x100000, 65536))
        if actual != expected:
            raise ValueError('Original snapshot model mismatch: ' + mode)
        inp.write_bytes(ram)
        subprocess.run([str(root / 'build/snapshot_palette'), mode, str(inp), str(out)], check=True)
        if out.read_bytes() != actual:
            raise ValueError('C++ snapshot mismatch: ' + mode)
        counts[mode] += 1

    for seed in range(16):
        ram = bytearray(hashlib.shake_256(bytes([seed])).digest(65536))
        expected = bytearray(ram)
        expected[0x7dd6:0x7dea] = ram[0x7dc2:0x7dd6]
        compare(ram, expected, 'save')
    for seed in range(2):
        for timer in range(256):
            ram = bytearray(hashlib.shake_256(bytes([seed, timer])).digest(65536))
            ram[0x7de8] = timer
            expected = bytearray(ram)
            expected[0x7dc2:0x7dd6] = ram[0x7dd6:0x7dea]
            if timer == 0:
                expected[0x7dd4] = 1
                for at in (0x7dc2, 0x7dc4, 0x7dc6):
                    expected[at] = ram[at]
            compare(ram, expected, 'restore')
            if timer in (0, 1, 2, 255):
                # The pending gate skips resource preparation: compare the
                # restored effect evolution and dirty flags, not upload.
                state = bytearray(expected)
                state[0x7ded] = 0x80
                cpu.mem_write(0x100000, bytes(state))
                call(cpu, 0x5728)
                actual = bytes(cpu.mem_read(0x100000, 65536))
                inp.write_bytes(state)
                subprocess.run([str(root / 'build/step_palette_frame'), str(inp),
                                str(root / 'extracted/runtime/palettes.ms5p'), str(out)], check=True)
                if out.read_bytes() != actual:
                    raise ValueError('Post-restore frame mismatch')
                counts['subsequent_frame'] += 1
    # Compose the observed save -> (-4,-4,-4,4) effect -> restore calls.
    state = bytearray(65536)
    state[0x7dc2:0x7dce] = bytes.fromhex('0200fd0004000200fd000400')
    state[0x7ded] = 0x80
    steps = ['save', 'effect'] + ['frame'] * 4 + ['restore', 'frame']
    for step in steps:
        cpu.mem_write(0x100000, bytes(state))
        inp.write_bytes(state)
        if step in ('save', 'restore'):
            entry = 0x8bc8 if step == 'save' else 0x8be0
            command = [str(root / 'build/snapshot_palette'), step, str(inp), str(out)]
        elif step == 'effect':
            entry = 0x8c16
            for reg, value in zip((UC_M68K_REG_D0, UC_M68K_REG_D1,
                                   UC_M68K_REG_D2, UC_M68K_REG_D3), (65532, 65532, 65532, 4)):
                cpu.reg_write(reg, value)
            command = [str(root / 'build/control_palette'), 'effect', str(inp), str(out),
                       '65532', '65532', '65532', '4']
        else:
            entry = 0x5728
            command = [str(root / 'build/step_palette_frame'), str(inp),
                       str(root / 'extracted/runtime/palettes.ms5p'), str(out)]
        call(cpu, entry)
        actual = bytes(cpu.mem_read(0x100000, 65536))
        subprocess.run(command, check=True)
        if out.read_bytes() != actual:
            raise ValueError('Temporary effect sequence mismatch: ' + step)
        state = bytearray(actual)
        counts['temporary_effect_steps'] += 1
    if state[0x7dc2:0x7dc8] != bytes.fromhex('0200fd000400') or state[0x7dd4] != 0:
        raise ValueError('Temporary effect did not return to saved targets')
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'counts': counts, 'all_ram_equal': True,
        'callers': {'save': 0xf94, 'restore': 0xfd6},
        'scope': 'Save/restore whole RAM and subsequent effect update with pending gate set. '
                 'Caller bytes verified; complete game reachability and displayed output unverified.'
    }, indent=2) + '\n')
    print('Palette snapshots match:', counts)


if __name__ == '__main__':
    main()
