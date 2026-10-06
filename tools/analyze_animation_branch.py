"""Verify opcode 0c boolean field branch using original selector table words."""
import hashlib
import json
from pathlib import Path
import struct
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from analyze_animation_wait import put


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f': raise ValueError('Unsupported ROM')
    # A reviewed prefix only, not a claim about the complete selector table size.
    offsets=struct.unpack('>32H',program[0x4a76c:0x4a7ac])
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    cpu.mem_write(0xff100,bytes.fromhex('55f900105900'))
    rows=[]
    for selector,offset in enumerate(offsets):
        for desired in (0,1,128,255):
            for actual_value in (0,1,128,255):
                for timer in (0,0x1234,0xffff):
                    ram=bytearray(65536);obj=0x2000;state=obj+0x26
                    ram[obj+offset]=actual_value
                    ram[state:state+4]=struct.pack('>I',0x105800)
                    put(ram,state+4,timer);put(ram,state+6,256)
                    put(ram,0x10,3);ram[0xd742]=201
                    ram[0x5800:0x580e]=struct.pack('>BBHI',12,desired,selector,0x10580c)+bytes((0,0,0,0,0x28,0))
                    taken=bool(desired)==bool(actual_value)
                    expected=bytearray(ram);put(expected,0x10,0)
                    expected[state:state+4]=struct.pack('>I',0x10580c if taken else 0x105808)
                    if taken:
                        expected[0xd742]=0
                        put(expected,state+4,0 if timer&0x8000 else timer&255)
                    else:
                        expected[0xd742]=2 if timer&0x8000 else 1
                        if timer&0x8000: put(expected,state+4,0)
                    cpu.mem_write(0x100000,bytes(ram))
                    cpu.reg_write(UC_M68K_REG_A5,0x108000);cpu.reg_write(UC_M68K_REG_A6,0x102000)
                    cpu.reg_write(UC_M68K_REG_A7,0x1feffc);cpu.mem_write(0x1feffc,struct.pack('>I',0xff100))
                    cpu.emu_start(0x49fc6,0xff106,count=20000)
                    if cpu.reg_read(UC_M68K_REG_PC)!=0xff106:raise ValueError('Original branch did not return')
                    result=bytearray(cpu.mem_read(0x100000,65536));carry=result[0x5900];result[0x5900]=0
                    if result!=expected or carry!=(255 if taken else 0):
                        raise ValueError('Branch mismatch '+repr((selector,desired,actual_value,timer)))
                    rows.append({'selector':selector,'field_offset':offset,'desired':desired,'field_value':actual_value,
                                 'timer':timer,'taken':taken,'ram_sha256':hashlib.sha256(result).hexdigest()})
    destination=root/'artifacts/animation_branch';destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'cases':len(rows),'all_ram_carry_equal':True,
        'selector_table_rom_offset':0x4a76c,'selector_prefix_words':32,
        'scope':'Controlled opcode0c fixtures and a reviewed 32-word table prefix. Full selector extent and natural script references not established.',
        'results':rows},indent=2)+'\n')
    print('Animation field branch RAM/carry match:',len(rows),'cases')


if __name__=='__main__':main()
