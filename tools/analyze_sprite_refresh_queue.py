"""Verify the full normal-rectangle refresh dispatcher, queue state and cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from analyze_sprite_sort import word, put


def model(root, directory, initial):
    ram = bytearray(initial)
    ready = ram[0x8d3d] & 128
    ram[0x8d3d] &= 127
    writes = []
    if not ready:
        return ram, writes
    forward = bool(ram[0x8d3c] & 128)
    ram[0x8d3c] ^= 128
    start, end = word(ram, 0x8d34), word(ram, 0x8d36)
    for pool in (0x8d3e, 0x8d46):
        put(ram, pool+(4 if forward else 6), word(ram, pool+(0 if forward else 2)))
    cursor = start if forward else end
    while cursor != (end if forward else start):
        if not forward:
            cursor = (cursor-2)&0x1fe
        record = 0x7f34+word(ram, 0x8b34+cursor)
        if forward:
            cursor = (cursor+2)&0x1fe
        style = word(ram, record+6)
        pool = 0x8d46 if style & 4 else 0x8d3e
        style &= ~4
        if word(ram, record+4) != 0xffff or style & 252:
            raise ValueError('Outside supported normal dispatcher path')
        packed = int.from_bytes(ram[record+8:record+12], 'big')
        identifier = packed & 0x7fffff
        u = word(ram, record+2) >> 6
        v = (packed >> 23) & 511
        if ram[pool:pool+8] == bytes([255])*8:
            continue
        output = directory/'composition.bin'
        resource = root/'extracted/runtime'/('composition_%06x.ms5c' % identifier)
        first = word(ram, pool+(4 if forward else 6))
        limit = word(ram, pool+(2 if forward else 0))
        cached = word(ram, pool+(6 if forward else 4))
        subprocess.run([str(root/'build/emit_sprite_resource'), str(resource), str(output),
                        str(u), str(v), str(style), str(first), str(limit), str(cached),
                        'forward' if forward else 'reverse'], check=True)
        result = output.read_bytes()
        next_slot = int.from_bytes(result[:4], 'big')
        put(ram, pool+(4 if forward else 6), next_slot)
        writes.extend(struct.unpack('>%dI' % ((len(result)-4)//4), result[4:]))
    for pool in (0x8d3e, 0x8d46):
        left, right = word(ram, pool+4), word(ram, pool+6)
        if forward:
            first = max(left, right)
            for slot in range(first, word(ram, pool+2)):
                writes.append(((0x8201+slot)<<16)|0x8000)
        else:
            first = min(left, right)
            for slot in range(first, word(ram, pool), -1):
                writes.append(((0x8200+slot)<<16)|0x8000)
    put(ram, 0x10, 0)
    put(ram, 0x8d34, end)
    return ram, writes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp", action="store_true")
    parser.add_argument("--disabled-pool", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program')
    directory = root/('artifacts/sprite_refresh_disabled' if args.disabled_pool else 'artifacts/sprite_refresh_queue')
    directory.mkdir(parents=True, exist_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x400000:0x500000])
    writes = []
    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video access')
            writes.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    results = []
    for forward in (False, True):
        for ready in (False, True):
            for count in (0, 1, 4, 20):
                for start in (0, 0x1fc):
                    for cache in (0, 95, 190):
                        ram = bytearray(65536)
                        ram[0x8d3c] = 0x21 | (128 if forward else 0)
                        ram[0x8d3d] = 0x35 | (128 if ready else 0)
                        put(ram, 0x10, 0xbeef)
                        put(ram, 0x8d34, start)
                        put(ram, 0x8d36, (start+2*count)&0x1fe)
                        for pool, lower, upper in ((0x8d3e, 0, 190), (0x8d46, 190, 380)):
                            ram[pool:pool+8] = struct.pack('>4H', lower, upper, lower+cache, lower+cache)
                        if args.disabled_pool:
                            ram[0x8d46:0x8d4e] = bytes([255])*8
                        for index in range(count):
                            offset = 12*(index+1)
                            put(ram, 0x8b34+((start+index*2)&0x1fe), offset)
                            identifier = 0x2152 if index % 2 == 0 else 0x2952
                            style = 0xffff1500 | (4 if index % 2 else 0)
                            packed = (384<<23)|identifier
                            record = 0x7f34+offset
                            ram[record:record+12] = struct.pack('>III', (160<<6), style, packed)
                        expected_ram, expected_writes = model(root, directory, ram)
                        cpu.mem_write(0x100000, bytes(ram))
                        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
                        cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
                        writes.clear()
                        cpu.emu_start(0x16cfa, 0xff000, count=1000000)
                        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
                            raise ValueError('Dispatcher failed to return')
                        actual_ram = bytes(cpu.mem_read(0x100000, 65536))
                        if actual_ram != expected_ram:
                            at = next(i for i in range(65536) if actual_ram[i] != expected_ram[i])
                            raise ValueError('Dispatcher RAM mismatch at %x' % (0x100000+at))
                        if writes != expected_writes:
                            raise ValueError('Dispatcher video mismatch forward%d ready%d count%d cache%d' % (forward, ready, count, cache))
                        if args.cpp:
                            (directory/'input.bin').write_bytes(ram)
                            subprocess.run([str(root/'build/refresh_sprite_queue'), str(directory/'input.bin'),
                                            str(directory/'cpp_ram.bin'), str(directory/'cpp_writes.bin'),
                                            str(root/'extracted/runtime/composition_002152.ms5c'),
                                            str(root/'extracted/runtime/composition_002952.ms5c')], check=True)
                            expected_trace = struct.pack('>I', int(ready))+b''.join(struct.pack('>I', w) for w in writes)
                            if (directory/'cpp_ram.bin').read_bytes() != actual_ram or (directory/'cpp_writes.bin').read_bytes() != expected_trace:
                                raise ValueError('C++ dispatcher differs from original CPU')
                        results.append({'forward': forward, 'ready': ready, 'count': count, 'start': start,
                                        'cache': cache, 'writes': len(writes), 'ram_sha256': hashlib.sha256(actual_ram).hexdigest(),
                                        'video_sha256': hashlib.sha256(b''.join(struct.pack('>I', w) for w in writes)).hexdigest()})
    (directory/'analysis.json').write_text(json.dumps({'source_program_sha256': source['sha256'],
        'entry': 0x16cfa, 'cpp_verified': args.cpp, 'disabled_pool': args.disabled_pool, 'cases': len(results), 'all_ram_and_video_equal': True,
        'scope': 'Python dispatcher model using verified C++ MS5C emitters; first normal rectangular dispatch path, two pools and ring wrap. C++ dispatcher additionally checked with --cpp; no timed hardware claim.', 'results': results}, indent=2)+'\n')
    print('Full refresh dispatcher RAM and video match:', len(results), 'cases')


if __name__ == '__main__':
    main()
