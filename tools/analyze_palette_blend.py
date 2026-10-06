"""Verify original table-driven palette blending and exact word arithmetic."""
import hashlib
import json
from pathlib import Path
import random
import struct
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_D0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def signed(value):
    return value if value < 0x8000 else value-0x10000


def model(program, first, second, weight, lookup):
    if weight == 0: packed = first
    elif weight >= 31: packed = second
    else:
        components = []
        for shift in (0, 5, 10):
            a = first >> shift
            b = second >> shift
            if shift != 10: a &= 31; b &= 31
            difference = (b-a)&0xffff
            byte = program[0x3f78+weight*64+signed(difference)]
            # MOVE.B replaces only the lower byte of the difference register.
            component = (((difference&0xff00)|byte)+a)&0xffff
            components.append(component)
        packed = (components[2]<<5)&0xffff
        packed |= components[1]&255
        packed = (packed<<5)&0xffff
        packed |= components[0]&255
    displacement = signed((packed*2)&0xffff)
    return program[lookup+displacement:lookup+displacement+2]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    lookup = int.from_bytes(program[0x200008:0x20000c], 'big')
    # Establish the actual signed table values instead of assuming a rounding rule.
    table_checks = 0
    for weight in range(1, 31):
        for difference in range(-31, 32):
            expected = (abs(difference)*weight//31) * (-1 if difference < 0 else 1)
            if program[0x3f78+weight*64+difference] != expected&255:
                raise ValueError('Blend table differs from truncation toward zero')
            table_checks += 1
    for value in range(32768):
        displacement = signed((value*2)&0xffff)
        actual = int.from_bytes(program[lookup+displacement:lookup+displacement+2], 'big')
        hardware = ((value&1)<<12)|((value&0x20)<<8)|((value&0x400)<<4)|((value>>1)&15)|((value>>2)&0xf0)|((value>>3)&0xf00)
        if actual != hardware: raise ValueError('Hardware lookup formula mismatch')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    rng = random.Random(0x4c40)
    rows = []
    for case in range(64):
        first = [rng.randrange(32768) for _ in range(16)]
        second = [rng.randrange(32768) for _ in range(16)]
        if case < 4:
            first = [[0]*16, [32767]*16, [31]*16, [1024]*16][case]
            second = [[32767]*16, [0]*16, [0]*16, [0]*16][case]
        for weight in list(range(32))+[255]:
            ram = bytearray(65536)
            ram[0x2000:0x2020] = struct.pack('>16H', *first)
            ram[0x2100:0x2120] = struct.pack('>16H', *second)
            ram[0x2200:0x2220] = bytes([0xa5])*32
            expected = bytearray(ram)
            expected[0x2202:0x2220] = b''.join(model(program, a, b, weight, lookup) for a,b in zip(first[1:],second[1:]))
            cpu.mem_write(0x100000, bytes(ram))
            for reg, value in ((UC_M68K_REG_A0,0x102000),(UC_M68K_REG_A1,0x102100),
                (UC_M68K_REG_A2,0x104d92),(UC_M68K_REG_A3,lookup),(UC_M68K_REG_A4,0x102200),(UC_M68K_REG_D0,weight)):
                cpu.reg_write(reg,value)
            call(cpu,0x4c40)
            actual = bytes(cpu.mem_read(0x100000,65536))
            if actual != expected or cpu.reg_read(UC_M68K_REG_A4) != 0x102200 or cpu.reg_read(UC_M68K_REG_A2) != 0x104d92:
                raise ValueError('Blend mismatch '+repr((case,weight)))
            rows.append({'case':case,'weight':weight,'output_sha256':hashlib.sha256(actual[0x2200:0x2220]).hexdigest()})
    destination = root/'artifacts/palette_blend'
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'entry':0x4c40,
        'lookup_words_verified':32768,'table_entries_verified':table_checks,'cases':len(rows),'all_ram_equal':True,
        'scope':'Controlled pairs of 15-bit source palettes, all weights0..31 plus255. Exact original table and lookup words; Separate C++ preparation verifier covers integration; active effect blending504c remains pending.',
        'results':rows},indent=2)+'\n')
    print('Original palette blend matches:',len(rows),'cases;',table_checks,'table entries')


if __name__ == '__main__': main()
