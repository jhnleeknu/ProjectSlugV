"""Verify the original stable two-byte display-ring radix sort and scratch RAM."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from analyze_sprite_sort import word, put


def model(initial):
    ram = bytearray(initial)
    start, end = word(ram, 0x8d36), word(ram, 0x8d3a)
    if start == end:
        return ram
    ram[0x8d4e:0x8f4e] = bytes(512)
    cursor = start
    while cursor != end:
        record = 0x7f34+word(ram, 0x8b34+cursor)
        for at in (0x8d4e+ram[record]*2, 0x8d4f+ram[record+1]*2):
            ram[at] = (ram[at]+1)&255
        cursor = (cursor+2)&510
    total = word(ram, 0x8d4e)
    for index in range(1, 256):
        total = (total+word(ram, 0x8d4e+index*2))&65535
        put(ram, 0x8d4e+index*2, total)
    count = total&255
    cursor = end
    for _ in range(count):
        cursor = (cursor-2)&510
        offset = word(ram, 0x8b34+cursor)
        at = 0x8d4f+ram[0x7f35+offset]*2
        ram[at] = (ram[at]-1)&255
        put(ram, 0x8f4e+ram[at]*2, offset)
    for index in range(count-1, -1, -1):
        offset = word(ram, 0x8f4e+index*2)
        at = 0x8d4e+ram[0x7f34+offset]*2
        ram[at] = (ram[at]-1)&255
        put(ram, 0x8b34+((start+ram[at]*2)&510), offset)
    return ram


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpp', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory = root/'artifacts/sprite_radix'
    directory.mkdir(parents=True, exist_ok=True)
    cpu = make_cpu(program)
    rng = random.Random(0x166bc)
    results = []
    for count in (0, 1, 2, 7, 96, 255):
        for pattern in ('ascending', 'descending', 'equal', 'unsigned', 'random', 'duplicates'):
            for start in (0, 510):
                ram = bytearray(hashlib.shake_256(b'radix-scratch').digest(65536))
                put(ram, 0x8d36, start)
                end = (start+count*2)&510
                put(ram, 0x8d3a, end)
                original = []
                for index in range(count):
                    offset = (index % 3 if pattern == 'duplicates' else index)*12
                    key = {'ascending': index, 'descending': count-index, 'equal': 0xabcd,
                           'unsigned': (0xffff, 0x8000, 0, 0x7fff)[index%4], 'random': rng.randrange(65536), 'duplicates': (2, 0, 2)[index%3]}[pattern]
                    put(ram, 0x7f34+offset, key)
                    put(ram, 0x8b34+((start+2*index)&510), offset)
                    original.append((key, offset))
                expected = model(ram)
                cpu.mem_write(0x100000, bytes(ram))
                cpu.reg_write(UC_M68K_REG_A5, 0x108000)
                cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
                cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
                cpu.emu_start(0x166bc, 0xff000, count=1000000)
                if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
                    raise ValueError('Radix sort did not return')
                actual = bytes(cpu.mem_read(0x100000, 65536))
                if actual != expected:
                    at = next(i for i in range(65536) if actual[i] != expected[i])
                    raise ValueError('Radix RAM mismatch at %x' % (0x100000+at))
                ordered = [word(actual, 0x8b34+((start+2*i)&510)) for i in range(count)]
                if ordered != [offset for key, offset in sorted(original, key=lambda pair: pair[0])]:
                    raise ValueError('Original not stable unsigned key sort')
                if args.cpp:
                    (directory/'input.bin').write_bytes(ram)
                    subprocess.run([str(root/'build/radix_sprite_queue'), str(directory/'input.bin'), str(directory/'cpp.bin')], check=True)
                    if (directory/'cpp.bin').read_bytes() != actual:
                        raise ValueError('C++ differs from original radix sort')
                results.append({'count': count, 'pattern': pattern, 'start': start,
                                'ordered_offsets': ordered, 'ram_sha256': hashlib.sha256(actual).hexdigest()})
    (directory/'analysis.json').write_text(json.dumps({'source_program_sha256': source['sha256'],
        'entry': 0x166bc, 'cases': len(results), 'cpp_verified': args.cpp, 'all_ram_equal': True,
        'scope': 'Stable unsigned16 sort of unprepared ring, including scratch arrays. No timing or full frame preparation claim.', 'results': results}, indent=2)+'\n')
    print('Radix sprite sort full RAM matches:', len(results), 'cases')


if __name__ == '__main__':
    main()
