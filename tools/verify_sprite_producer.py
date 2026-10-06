"""Verify default-callback queue initialization and producer memory/status effects."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D5, UC_M68K_REG_D7
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from analyze_sprite_sort import word, put


def initialize(initial):
    ram = bytearray(initial)
    ram[0x9152:0x9156] = struct.pack('>I', 0xcd50)
    ram[0x8d3d] = 0
    ram[0x8d34:0x8d3c] = bytes(8)
    ram[0x914e:0x9152] = bytes(4)
    for i in range(256):
        put(ram, 0x8b34+i*2, i*12)
    ram[0x8d3e:0x8d4e] = bytes([255])*16
    return ram


def model(initial, d0, d1, d5, d7):
    ram = bytearray(initial)
    u, v = d0>>16, d0&65535
    if ((v-64)&65535)>=640 or ((u+352)&65535)>=1024:
        return ram, 1
    next_index = (word(ram, 0x8d3a)+2)&510
    if next_index == word(ram, 0x8d34):
        return ram, 2 if word(ram, 0x8d36)==word(ram, 0x8d34) else 3
    offset = word(ram, 0x8b34+next_index)
    put(ram, 0x8d3a, next_index)
    if d1&64:
        at = word(ram, 0x914e)
        put(ram, 0x914e, at+2)
        put(ram, 0x8f4e+at, offset)
    else:
        at = word(ram, 0x8d38)
        put(ram, 0x8b34+at, offset)
        put(ram, 0x8d38, (at+2)&510)
    record = 0x7f34+offset
    ram[record:record+12] = struct.pack('>III', ((d5&65535)<<16)|((u<<6)&65535),
                                     d1&0xffffff07, d7|((v<<23)&0xffffffff))
    return ram, 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpp', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory = root/'artifacts/sprite_producer'
    directory.mkdir(parents=True, exist_ok=True)
    cpu = make_cpu(program)
    waiting = [False]
    def code(cpu, address, size, user):
        if address == 0xcda4:
            waiting[0] = True
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, code)
    rng = random.Random(0xcd58)
    initializations = []
    for index in range(8):
        original = hashlib.shake_256(b'sprite-init'+bytes([index])).digest(65536)
        expected = initialize(original)
        cpu.mem_write(0x100000, original)
        cpu.reg_write(UC_M68K_REG_A5, 0x108000)
        call(cpu, 0xccd6)
        actual = bytes(cpu.mem_read(0x100000, 65536))
        if actual != expected:
            raise ValueError('Initialization differs')
        if args.cpp:
            (directory/'input.bin').write_bytes(original)
            subprocess.run([str(root/'build/produce_sprite_queue'), 'init', str(directory/'input.bin'), str(directory/'cpp.bin')], check=True)
            if (directory/'cpp.bin').read_bytes() != actual:
                raise ValueError('C++ initialization differs')
        initializations.append(hashlib.sha256(actual).hexdigest())
    results = []
    for state in ('empty', 'wrap', 'full', 'waiting'):
        for u in (0xfe9f, 0xfea0, 0xffff, 0, 0x29f, 0x2a0):
            for v in (63, 64, 703, 704):
                for deferred in (False, True):
                    ram = initialize(hashlib.shake_256(b'sprite-producer').digest(65536))
                    if state == 'wrap':
                        for at in (0x8d34, 0x8d36):
                            put(ram, at, 2)
                        put(ram, 0x8d38, 510); put(ram, 0x8d3a, 510)
                    if state in ('full', 'waiting'):
                        put(ram, 0x8d34, 2)
                        put(ram, 0x8d36, 2 if state == 'full' else 4)
                    d0, d1, d5, d7 = (u<<16)|v, (rng.getrandbits(32)&~64)|(64 if deferred else 0), rng.getrandbits(32), rng.getrandbits(32)
                    expected, status = model(ram, d0, d1, d5, d7)
                    cpu.mem_write(0x100000, bytes(ram))
                    for reg, value in ((UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_D0, d0), (UC_M68K_REG_D1, d1), (UC_M68K_REG_D5, d5), (UC_M68K_REG_D7, d7), (UC_M68K_REG_A7, 0x1feffc)):
                        cpu.reg_write(reg, value)
                    cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
                    waiting[0] = False
                    cpu.emu_start(0xcd58, 0xff000, count=20000)
                    if waiting[0] != (status == 3) or (not waiting[0] and cpu.reg_read(UC_M68K_REG_PC) != 0xff000):
                        raise ValueError('Unexpected return/wait state')
                    actual = bytes(cpu.mem_read(0x100000, 65536))
                    if actual != expected:
                        raise ValueError('Producer memory differs')
                    if args.cpp:
                        (directory/'input.bin').write_bytes(ram)
                        subprocess.run([str(root/'build/produce_sprite_queue'), 'submit', str(directory/'input.bin'), str(directory/'cpp.bin'), str(directory/'status.bin'), str(d0), str(d1), str(d5), str(d7)], check=True)
                        if (directory/'cpp.bin').read_bytes() != actual or (directory/'status.bin').read_bytes() != struct.pack('>I', status):
                            raise ValueError('C++ producer differs')
                    results.append({'state': state, 'd0': d0, 'd1': d1, 'd5': d5, 'd7': d7, 'status': status, 'ram_sha256': hashlib.sha256(actual).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({'source_program_sha256': source['sha256'], 'initialization_cases': initializations,
        'producer_cases': len(results), 'cpp_verified': args.cpp, 'all_ram_equal': True,
        'scope': 'Default RTS callback only. Waiting cases stop original on first spin entry; no wait resumption/IRQ timing equivalence claim.', 'results': results}, indent=2)+'\n')
    print('Initialization and producer RAM match:', len(initializations), '+', len(results), 'cases')


if __name__ == '__main__':
    main()
