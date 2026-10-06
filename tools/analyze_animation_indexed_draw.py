"""Compare opcode10 indexed draw against the original M68000 interpreter."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_A1, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from animation_cpp_check import check
from analyze_animation_wait import put
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpp', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    if program[0x65f64:0x65f68] != bytes.fromhex('101e0028'):
        raise ValueError('Actual indexed-draw prefix changed')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0xff100, bytes.fromhex('55f900105900'))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.mem_write(0x100000, bytes(65536))
    call(cpu, 0xccd6)
    initialized = bytes(cpu.mem_read(0x100000, 65536))
    visits = []
    def hook(cpu, address, size, user):
        visits.append(cpu.reg_read(UC_M68K_REG_A1))
    cpu.hook_add(UC_HOOK_CODE, hook, begin=0x4a10c, end=0x4a10c)
    # Distinct records exercise selected offsets, controls and producer outputs.
    records = b''.join(bytes((4, 0x40 + i, i, i)) + struct.pack('>I', 0x2152 + i*0x800) for i in range(5))
    script = bytes.fromhex('101e0028') + records + bytes.fromhex('0000')
    directory = root/'artifacts/animation_indexed_draw'
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(256):
        for timer in (0, 0x1234, 0xffff):
            ram = bytearray(initialized)
            obj = 0x2000
            struct.pack_into('>I', ram, obj+0x26, 0x105800)
            struct.pack_into('>I', ram, obj+0x12, 0xffff1500 | (index&3))
            put(ram, obj+0x2a, timer)
            put(ram, obj+0x2c, 256)
            put(ram, obj+0x42, 160)
            put(ram, obj+0x46, 384)
            put(ram, obj+0x1e, 0x5678)
            ram[obj+0x7d] = index
            ram[0x5800:0x5800+len(script)] = script
            cpu.mem_write(0x100000, bytes(ram))
            cpu.reg_write(UC_M68K_REG_A5, 0x108000)
            cpu.reg_write(UC_M68K_REG_A6, 0x102000)
            cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
            cpu.mem_write(0x1feffc, struct.pack('>I', 0xff100))
            visits.clear()
            cpu.emu_start(0x49fc6, 0xff106, count=20000)
            if cpu.reg_read(UC_M68K_REG_PC) != 0xff106:
                raise ValueError('Indexed draw did not return')
            expected_visits = [0x105805+index*8] * (2 if timer&0x8000 else 1) if index < 5 else []
            if visits != expected_visits:
                raise ValueError('Selected draw mismatch '+repr((index, timer, visits)))
            actual = bytearray(cpu.mem_read(0x100000, 65536))
            if actual[0x5900] != 0 or actual[obj+0x26:obj+0x2a] != ram[obj+0x26:obj+0x2a]:
                raise ValueError('Unexpected carry or stored pointer change')
            if args.cpp:
                check(root, directory, ram, actual, 0, len(script))
            rows.append({'index': index, 'timer': timer, 'draw_operand_addresses': list(visits),
                         'ram_sha256': hashlib.sha256(actual).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({
        'source': source, 'cases': len(rows), 'cpp_verified': args.cpp,
        'scope': 'Controlled five-record list using actual selector30; all byte indices and three timer states. Does not establish natural gameplay reachability or all signed length/field-offset combinations.',
        'results': rows}, indent=2)+'\n')
    print('Indexed draw selection, RAM and carry match:', len(rows), 'cases; C++:', args.cpp)


if __name__ == '__main__':
    main()
