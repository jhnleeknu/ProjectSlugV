"""Ground deferred sprite ordering and tag replacement against original 68000."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D5, UC_M68K_REG_D7
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def word(ram, at):
    return int.from_bytes(ram[at:at+2], 'big')


def put(ram, at, value):
    ram[at:at+2] = struct.pack('>H', value & 65535)


def expected_sort(initial, new_tag):
    ram = bytearray(initial)
    previous = word(ram, 0x9150)
    put(ram, 0x9150, new_tag)
    remaining = word(ram, 0x914e)
    end = word(ram, 0x8d38)
    while remaining:
        at = 0x8f4e + remaining - 2
        chosen = word(ram, at)
        key = word(ram, 0x7f34 + chosen)
        while at != 0x8f4e:
            at -= 2
            other = word(ram, at)
            other_key = word(ram, 0x7f34 + other)
            if key >= other_key:
                key = other_key
                put(ram, at, chosen)
                chosen = other
        put(ram, 0x7f34 + chosen, previous)
        put(ram, 0x8b34 + end, chosen)
        end = (end + 2) & 0x1fe
        remaining -= 2
    if word(initial, 0x914e):
        put(ram, 0x8d38, end)
        put(ram, 0x914e, 0)
    return ram


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program')
    directory = root/"artifacts/sprite_sort"
    directory.mkdir(parents=True, exist_ok=True)
    cpu = make_cpu(program)
    rng = random.Random(0xce02)
    results = []
    for count in (0, 1, 2, 7, 31, 96, 200, 255):
        for pattern in ('ascending', 'descending', 'equal', 'unsigned', 'random'):
            for start in (0, 0x1fc):
                cpu.mem_write(0x100000, bytes(65536))
                cpu.reg_write(UC_M68K_REG_A5, 0x108000)
                call(cpu, 0xccd6)
                keys = []
                for index in range(count):
                    key = {'ascending': index, 'descending': count-index, 'equal': 7,
                           'unsigned': (0, 0x8000, 0x7fff, 0xffff)[index%4], 'random': rng.randrange(65536)}[pattern]
                    keys.append(key)
                    for register, value in ((UC_M68K_REG_D0, 0x00a00180), (UC_M68K_REG_D1, 0x1540),
                                            (UC_M68K_REG_D5, key), (UC_M68K_REG_D7, 0x2152)):
                        cpu.reg_write(register, value)
                    call(cpu, 0xcd58)
                # Exercise wrapped output index after valid deferred producer calls.
                cpu.mem_write(0x108d38, struct.pack('>H', start))
                cpu.mem_write(0x109150, b'\x89\xab')
                initial = bytes(cpu.mem_read(0x100000, 65536))
                expected = expected_sort(initial, 0x1234)
                cpu.reg_write(UC_M68K_REG_D0, 0x1234)
                # The 200-entry quadratic sort exceeds the common 20k cap.
                from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC
                cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
                cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
                cpu.emu_start(0xce02, 0xff000, count=1000000)
                if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
                    raise ValueError('Sort did not return')
                actual = bytes(cpu.mem_read(0x100000, 65536))
                if actual != expected:
                    at = next(i for i in range(65536) if actual[i] != expected[i])
                    raise ValueError('Sort mismatch at %x' % (0x100000+at))
                if args.cpp:
                    (directory/'input.bin').write_bytes(initial)
                    subprocess.run([str(root/'build/sort_sprite_queue'), str(directory/'input.bin'),
                                    str(directory/'cpp.bin'), '0x1234'], check=True)
                    if (directory/'cpp.bin').read_bytes() != actual:
                        raise ValueError('C++ sort differs from original CPU')
                offsets = [word(actual, 0x8b34+((start+i*2)&0x1fe)) for i in range(count)]
                selected_keys = [keys[offset//12-1] for offset in offsets]
                if selected_keys != sorted(keys):
                    raise ValueError('Output not ascending unsigned keys')
                results.append({'count': count, 'pattern': pattern, 'start': start,
                                'ordered_record_offsets': offsets, 'ram_sha256': hashlib.sha256(actual).hexdigest()})
    directory = root/'artifacts/sprite_sort'
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'analysis.json').write_text(json.dumps({'source_program_sha256': source['sha256'],
        'entry': 0xce02, 'cases': len(results), 'ram_bytes_per_case': 65536,
        'all_ram_equal': True, 'cpp_verified': args.cpp, 'scope': 'Original deferred sort after valid producer calls; controlled output index and tags; no consumer concurrency.', 'results': results}, indent=2)+'\n')
    print('Deferred sprite sort full RAM matches:', len(results), 'cases')


if __name__ == '__main__':
    main()
