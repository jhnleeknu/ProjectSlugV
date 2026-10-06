"""Verify opcode14 selector1e callback through the original interpreter."""
import argparse
from animation_cpp_check import check as check_cpp
import hashlib
import json
from pathlib import Path
import struct
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from analyze_animation_wait import put


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cpp',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    if int.from_bytes(program[0x4a578:0x4a57c],'big')!=0x2b3fa:raise ValueError('Callback target changed')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    cpu.mem_write(0xff100,bytes.fromhex('55f900105900'))
    rows=[]
    for index in range(256):
        for timer in (0,0x1234,0xffff):
            for bank_shadow in (0,3):
                ram=bytearray(65536);obj=0x2000;state=obj+0x26
                ram[state:state+4]=struct.pack('>I',0x105800)
                put(ram,state+4,timer);put(ram,state+6,256)
                ram[obj+0x7d]=index;ram[obj+0x78:obj+0x7c]=bytes.fromhex('deadbeef')
                put(ram,0x10,bank_shadow);ram[0xd742]=201
                ram[0x5800:0x5808]=bytes.fromhex('141e0006431a0000')
                expected=bytearray(ram);put(expected,0x10,0)
                expected[state:state+4]=struct.pack('>I',0x105806)
                expected[obj+0x78:obj+0x7c]=program[0x6431a+index*4:0x6431e+index*4]
                expected[0xd742]=2 if timer&0x8000 else 1
                if timer&0x8000:put(expected,state+4,0)
                cpu.mem_write(0x100000,bytes(ram))
                cpu.reg_write(UC_M68K_REG_A5,0x108000);cpu.reg_write(UC_M68K_REG_A6,0x102000)
                cpu.reg_write(UC_M68K_REG_A7,0x1feffc);cpu.mem_write(0x1feffc,struct.pack('>I',0xff100))
                cpu.emu_start(0x49fc6,0xff106,count=20000)
                if cpu.reg_read(UC_M68K_REG_PC)!=0xff106:raise ValueError('Callback script did not return')
                actual=bytearray(cpu.mem_read(0x100000,65536))
                if actual[0x5900]!=0:raise ValueError('Unexpected return carry')
                if actual!=expected:raise ValueError('Callback RAM mismatch '+repr((index,timer,bank_shadow)))
                if args.cpp:
                    check_cpp(root,root/"artifacts/animation_callback",ram,expected,0,8)
                rows.append({'index':index,'timer':timer,'initial_bank_shadow':bank_shadow,
                             'source_read_rom_offset':0x6431a+index*4,'written_value':int.from_bytes(actual[obj+0x78:obj+0x7c],'big'),
                             'ram_sha256':hashlib.sha256(actual).hexdigest()})
    destination=root/'artifacts/animation_callback';destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'cases':len(rows),'cpp_verified':args.cpp,'all_ram_carry_equal':True,
        'scope':'Opcode14 selector1e under controlled object state. Full byte index operation tested, not a declaration of the source table logical extent or naturally used indices.',
        'results':rows},indent=2)+'\n')
    print('Animation callback RAM/carry match:',len(rows),'cases')


if __name__=='__main__':main()
