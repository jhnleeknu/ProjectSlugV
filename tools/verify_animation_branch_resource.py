"""Run the extracted two-way ROM animation through original and C++ CPUs."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from analyze_animation_wait import put
from pack_animation_branch import extract


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    base, script, commands = extract(program)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0xff100, bytes.fromhex('55f900105900'))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.mem_write(0x100000, bytes(65536))
    call(cpu, 0xccd6)
    initial = bytes(cpu.mem_read(0x100000, 65536))
    folder = root/'artifacts/animation_branch_resource'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, status = [folder/name for name in ('input.bin', 'output.bin', 'status.bin')]
    resources = root/'extracted/runtime'
    rows = []
    for index in range(17):
        for timer in (0, 0xffff):
            for speed in (128, 256):
                state = bytearray(initial)
                obj = 0x2000
                struct.pack_into('>I', state, obj+0x26, base)
                struct.pack_into('>I', state, obj+0x12, 0xffff1500 | (index&3))
                put(state, obj+0x2a, timer)
                put(state, obj+0x2c, speed)
                put(state, obj+0x42, 160)
                put(state, obj+0x46, 384)
                state[obj+0x7c] = index
                state[obj+0x7d] = index % 5
                for frame in range(24):
                    # External object state changes force transitions both ways.
                    state[obj+0x7e] = (frame//6) % 2
                    cpu.mem_write(0x100000, bytes(state))
                    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
                    cpu.reg_write(UC_M68K_REG_A6, 0x102000)
                    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
                    cpu.mem_write(0x1feffc, struct.pack('>I', 0xff100))
                    cpu.emu_start(0x49fc6, 0xff106, count=20000)
                    if cpu.reg_read(UC_M68K_REG_PC) != 0xff106: raise ValueError('Original did not return')
                    expected = bytearray(cpu.mem_read(0x100000, 65536))
                    carry = int(expected[0x5900] != 0)
                    expected[0x5900] = 0
                    inp.write_bytes(state)
                    subprocess.run([str(root/'build/step_animation_resource'), str(inp),
                        str(resources/'animation_065f56.ms5a'), str(out), str(status), str(obj),
                        str(resources/'data_04a76c.ms5d'), str(resources/'branch_data_06431a.ms5d')], check=True)
                    state = bytearray(out.read_bytes())
                    if state != expected or status.read_bytes() != struct.pack('>I', carry):
                        raise ValueError('Branch resource mismatch '+repr((index, timer, speed, frame)))
                    rows.append({'index': index, 'initial_timer': timer, 'speed': speed, 'frame': frame,
                                 'pointer': int.from_bytes(state[obj+0x26:obj+0x2a], 'big'),
                                 'ram_sha256': hashlib.sha256(state).hexdigest()})
    (folder/'verification.json').write_text(json.dumps({'source': source, 'sequences': 68,
        'steps': len(rows), 'all_ram_carry_equal': True,
        'scope': 'Actual ROM script and native MS5A/MS5D resources with controlled object state and forced branch transitions. Sprite producer queue is compared; rendering, natural object group and gameplay reachability are not established.',
        'results': rows}, indent=2)+'\n')
    print('Two-way ROM animation resources match:', len(rows), 'steps')


if __name__ == '__main__': main()
