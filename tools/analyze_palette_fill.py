"""Verify palette-bank1 fill and the setup routine's signed word addressing."""
import argparse
import subprocess
import hashlib
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cpp',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    if program[0x8752:0x8b52] != bytes.fromhex('48e0ff00')*256:raise ValueError('Fill sequence changed')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);cpu.mem_write(0x200000,program[0x200000:0x300000]);cpu.reg_write(UC_M68K_REG_A5,0x108000)
    selections=[]
    def hook(cpu,access,address,size,value,user):
        if address in (0x3a000f,0x3a001f):selections.append(0 if address==0x3a000f else 1)
    cpu.hook_add(UC_HOOK_MEM_WRITE,hook)
    folder=root/'artifacts/palette_fill';folder.mkdir(parents=True,exist_ok=True)
    inp,colors,out,outcolors,bank=[folder/name for name in ('input.bin','banks.bin','output.bin','output_banks.bin','display.bin')]
    rows=[]
    for seed in range(16):
        for display in (0,255):
            ram=bytearray(65536);pattern=hashlib.sha256(bytes((seed,))).digest()
            ram[0x7da2:0x7dc2]=pattern;ram[0x7dea:0x7dec]=bytes.fromhex('2000');ram[0x7dec]=display;ram[0x7ded]=255
            expected=bytearray(ram);expected[0x7dea:0x7dec]=b'\0\0'
            cpu.mem_write(0x100000,bytes(ram));cpu.mem_write(0x400000,bytes([0xa5])*8192);selections.clear();call(cpu,0x72fa)
            palette=b'\0\0'+(pattern*256)[2:]
            if bytes(cpu.mem_read(0x100000,65536))!=expected or bytes(cpu.mem_read(0x400000,8192))!=palette or selections!=[1,int(display!=0)]:raise ValueError('Fill mismatch')
            if args.cpp:
                bank0=hashlib.shake_256(bytes((seed,display))).digest(8192)
                inp.write_bytes(ram);colors.write_bytes(bank0+bytes([0xa5])*8192)
                subprocess.run([str(root/'build/transfer_palette_banks'),str(inp),str(colors),str(out),str(outcolors),str(bank)],check=True)
                if out.read_bytes()!=expected or outcolors.read_bytes()!=bank0+palette or bank.read_bytes()!=bytes([int(display!=0)]):raise ValueError('C++ special fill mismatch')
                # Next call resumes the normal path and must leave filled bank1 intact.
                normal=bytearray(expected);normal[0x5da2:0x5dc2]=bytes.fromhex('8000')+bytes([seed])*30
                cpu.mem_write(0x100000,bytes(normal));cpu.mem_write(0x400000,bank0);selections.clear();call(cpu,0x72fa)
                normal_expected=bytes(cpu.mem_read(0x100000,65536));normal_bank0=bytes(cpu.mem_read(0x400000,8192))
                inp.write_bytes(normal);colors.write_bytes(bank0+palette)
                subprocess.run([str(root/'build/transfer_palette_banks'),str(inp),str(colors),str(out),str(outcolors),str(bank)],check=True)
                if out.read_bytes()!=normal_expected or outcolors.read_bytes()!=normal_bank0+palette or bank.read_bytes()!=bytes([int(display!=0)]):raise ValueError('C++ fill-to-normal transition mismatch')
            rows.append({'seed':seed,'display':display,'palette_sha256':hashlib.sha256(palette).hexdigest()})
    base=int.from_bytes(program[0x200004:0x200008],'big');lookup=int.from_bytes(program[0x200008:0x20000c],'big');setups=[]
    identifiers=list(range(2048))+[2048,4096,65535] if args.cpp else (0,1,15,1023,1024,2047,2048,0x897,65535)
    for identifier in identifiers:
        ram=bytearray(65536);ram[0x7da2:0x7dc2]=bytes([0xa5])*32;ram[0x10:0x12]=b'\xbe\xef'
        expected=bytearray(ram);offset=(identifier*32)&65535;offset=offset if offset<32768 else offset-65536
        address=base+offset
        for color in range(1,16):
            word=int.from_bytes(program[address+color*2:address+color*2+2],'big');delta=(word*2)&65535;delta=delta if delta<32768 else delta-65536
            expected[0x7da2+color*2:0x7da4+color*2]=program[lookup+delta:lookup+delta+2]
        expected[0x7dea:0x7dec]=bytes.fromhex('2000');expected[0x10:0x12]=b'\0\0'
        cpu.mem_write(0x100000,bytes(ram));cpu.reg_write(UC_M68K_REG_D0,identifier);call(cpu,0x8b64)
        if bytes(cpu.mem_read(0x100000,65536))!=expected:raise ValueError('Fill setup mismatch')
        if args.cpp:
            inp.write_bytes(ram)
            subprocess.run([str(root/'build/setup_palette_fill'),str(inp),str(root/'extracted/runtime/palette_fill.ms5p'),str(out),str(identifier)],check=True)
            if out.read_bytes()!=expected:raise ValueError('C++ resource-backed fill setup mismatch')
        setups.append({'input_id':identifier,'source_rom_offset':address,'source_displacement':offset})
    folder=root/'artifacts/palette_fill';folder.mkdir(parents=True,exist_ok=True)
    (folder/'verification.json').write_text(json.dumps({'source':source,'fill_cases':len(rows),'cpp_verified':args.cpp,'cpp_normal_transition_cases':len(rows) if args.cpp else 0,'setup_cases':len(setups),'all_ram_palette_equal':True,
        'scope':'Verified initializer counter2000 and logical bank1 mapped at400000. Setup word displacement is verified, not assumed identical to normal source ID addressing. C++ mode checks all 2048 canonical fill resource selectors and three aliases. Optional C++ comparison covers both banks and following normal transfers. Other counter values and device timing pending.', 'fill_results':rows,'setup_results':setups},indent=2)+'\n')
    print('Original palette fill matches:',len(rows),'fills;',len(setups),'setups')


if __name__=='__main__':main()
