"""Compare complete normal sprite preparation to original CPU entry 0x16bba."""
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
from verify_sprite_composition import resolve
from analyze_sprite_sort import word, put, expected_sort
from analyze_sprite_radix import model as radix_model


def model(root, directory, initial):
    ram = radix_model(expected_sort(initial, 0))
    start, end = word(ram, 0x8d36), word(ram, 0x8d3a)
    if word(ram, 0x8d34) != start:
        raise ValueError('Consumer still active')
    forward = bool(ram[0x8d3c] & 128)
    current = 4 if forward else 6
    for pool in (0x8d3e, 0x8d46):
        put(ram, pool+current, word(ram, pool+(0 if forward else 2)))
    writes = []
    cursor = start if forward else end
    while cursor != (end if forward else start):
        if not forward:
            cursor = (cursor-2)&510
        record = 0x7f34+word(ram, 0x8b34+cursor)
        if forward:
            cursor = (cursor+2)&510
        style = word(ram, record+6)
        pool = 0x8d46 if style & 4 else 0x8d3e
        style &= ~4
        if word(ram, record+4) != 0xffff or style & 255:
            raise ValueError('Unsupported dispatch')
        identifier = int.from_bytes(ram[record+8:record+12], 'big')&0x7fffff
        if ram[pool:pool+8] == bytes([255])*8:
            continue
        path = directory/('%06x.raw.bin' % identifier)
        output = directory/'emission.bin'
        first, limit = word(ram, pool+current), word(ram, pool+(6 if forward else 4))
        if forward:
            command = [str(root/'build/emit_composition'), str(path), str(output),
                       str(word(ram, record+2)>>6), str(style), str(first), str(limit)]
        else:
            command = [str(root/'build/emit_composition_reverse'), str(path), str(output),
                       str(word(ram, record+2)>>6), '0', str(style), str(first), str(limit), '0', 'normal']
        subprocess.run(command, check=True)
        data = output.read_bytes()
        put(ram, pool+current, int.from_bytes(data[:4], 'big'))
        writes.extend(struct.unpack('>%dI' % ((len(data)-4)//4), data[4:]))
    put(ram, 0x10, 0)
    put(ram, 0x8d36, end)
    put(ram, 0x8d38, end)
    ram[0x8d3d] = 255
    return ram, writes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpp', action='store_true')
    parser.add_argument('--disabled-pool', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory = root/('artifacts/sprite_prepare_disabled' if args.disabled_pool else 'artifacts/sprite_prepare_queue')
    directory.mkdir(parents=True, exist_ok=True)
    for identifier in (0x2152, 0x2952):
        _, _, data = resolve(program, identifier)
        (directory/('%06x.raw.bin' % identifier)).write_bytes(data)
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
        for count in (0, 1, 4, 20):
            for deferred in (False, True):
                for start in (0, 510):
                    for cache in (0, 95, 190):
                        ram = bytearray(65536)
                        ram[0x8d3c] = 0x21 | (128 if forward else 0)
                        ram[0x8d3d] = 0x35
                        put(ram, 0x10, 0xbeef)
                        for at in (0x8d34, 0x8d36):
                            put(ram, at, start)
                        end = (start+count*2)&510
                        put(ram, 0x8d3a, end)
                        put(ram, 0x9150, 0x1234)
                        for pool, lower, upper in ((0x8d3e, 0, 190), (0x8d46, 190, 380)):
                            ram[pool:pool+8] = struct.pack('>4H', lower, upper, lower+cache, lower+cache)
                        if args.disabled_pool:
                            ram[0x8d46:0x8d4e] = bytes([255])*8
                        normal_count = delayed_count = 0
                        for index in range(count):
                            offset = 12*(index+1)
                            is_deferred = deferred and index % 2 == 0
                            if is_deferred:
                                put(ram, 0x8f4e+delayed_count*2, offset)
                                delayed_count += 1
                            else:
                                put(ram, 0x8b34+((start+normal_count*2)&510), offset)
                                normal_count += 1
                            identifier = 0x2152 if index % 2 == 0 else 0x2952
                            style = 0xffff1500 | (4 if index % 2 else 0)
                            key = (count-index)*17
                            record = 0x7f34+offset
                            ram[record:record+12] = struct.pack('>III', (key<<16)|(160<<6), style, (384<<23)|identifier)
                        put(ram, 0x8d38, (start+normal_count*2)&510)
                        put(ram, 0x914e, delayed_count*2)
                        expected_ram, expected_writes = model(root, directory, ram)
                        cpu.mem_write(0x100000, bytes(ram))
                        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
                        cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
                        writes.clear()
                        cpu.emu_start(0x16bba, 0xff000, count=1000000)
                        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
                            raise ValueError('Preparation failed to return')
                        actual_ram = bytes(cpu.mem_read(0x100000, 65536))
                        if actual_ram != expected_ram or writes != expected_writes:
                            raise ValueError('Preparation mismatch forward%d count%d deferred%d cache%d' % (forward, count, deferred, cache))
                        if args.cpp:
                            (directory/'input.bin').write_bytes(ram)
                            subprocess.run([str(root/'build/prepare_sprite_queue'), str(directory/'input.bin'),
                                            str(directory/'cpp_ram.bin'), str(directory/'cpp_writes.bin'),
                                            str(root/'extracted/runtime/composition_002152.ms5c'),
                                            str(root/'extracted/runtime/composition_002952.ms5c')], check=True)
                            expected_trace = b''.join(struct.pack('>I', w) for w in writes)
                            if (directory/'cpp_ram.bin').read_bytes() != actual_ram or (directory/'cpp_writes.bin').read_bytes() != expected_trace:
                                raise ValueError('C++ preparation differs from original')
                            cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
                            cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
                            writes.clear()
                            cpu.emu_start(0x16cfa, 0xff000, count=1000000)
                            if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
                                raise ValueError('Follow-up refresh did not return')
                            subprocess.run([str(root/'build/refresh_sprite_queue'), str(directory/'cpp_ram.bin'),
                                            str(directory/'cpp_refreshed_ram.bin'), str(directory/'cpp_refreshed_writes.bin'),
                                            str(root/'extracted/runtime/composition_002152.ms5c'),
                                            str(root/'extracted/runtime/composition_002952.ms5c')], check=True)
                            if (directory/'cpp_refreshed_ram.bin').read_bytes() != bytes(cpu.mem_read(0x100000, 65536)):
                                raise ValueError('Prepare/refresh chain RAM mismatch')
                            if (directory/'cpp_refreshed_writes.bin').read_bytes() != struct.pack('>I', 1)+b''.join(struct.pack('>I', w) for w in writes):
                                raise ValueError('Prepare/refresh chain video mismatch')
                            writes[:] = expected_writes
                        results.append({'forward': forward, 'count': count, 'deferred': deferred, 'start': start,
                                        'cache': cache, 'writes': len(writes), 'ram_sha256': hashlib.sha256(actual_ram).hexdigest(),
                                        'video_sha256': hashlib.sha256(b''.join(struct.pack('>I', w) for w in writes)).hexdigest()})
    (directory/'analysis.json').write_text(json.dumps({'source_program_sha256': source['sha256'], 'entry': 0x16bba,
        'cases': len(results), 'cpp_verified': args.cpp, 'disabled_pool': args.disabled_pool, 'cpp_prepare_refresh_chain_verified': args.cpp, 'all_ram_and_video_equal': True,
        'scope': 'Complete preparation for normal rectangles with synchronized consumer; no concurrent wait, CPU flags or timed device claim.', 'results': results}, indent=2)+'\n')
    print('Preparation RAM and video match:', len(results), 'cases')


if __name__ == '__main__':
    main()
