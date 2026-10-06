"""Verify byte-wrapped effect arithmetic and blend-before-effect ordering."""
import hashlib
import json
from pathlib import Path
import struct
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_D0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def effect(channel, amount):
    value = (channel+amount)&255
    return 0 if value&128 else min(value,31)


def hardware(value):
    return ((value&1)<<12)|((value&0x20)<<8)|((value&0x400)<<4)|((value>>1)&15)|((value>>2)&0xf0)|((value>>3)&0xf00)


def model(a,b,weight,amounts):
    result = 0
    for shift,amount in zip((10,5,0),amounts):
        first=(a>>shift)&31;second=(b>>shift)&31
        if weight>=31: value=second
        else:
            delta=second-first
            value=first+(abs(delta)*weight//31)*(-1 if delta<0 else 1)
        result |= effect(value,amount)<<shift
    return hardware(result)


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_write(0x200000,program[0x200000:0x300000])
    lookup=int.from_bytes(program[0x200008:0x20000c],'big');rows=[]
    def run(first,second,weight,amounts,entry):
        ram=bytearray(65536)
        ram[0x2000:0x2020]=struct.pack('>16H',0xaaaa,*first)
        ram[0x2100:0x2120]=struct.pack('>16H',0xbbbb,*second)
        ram[0x2200:0x2220]=bytes([0xa5])*32
        for address,amount in zip((0x7dc2,0x7dc4,0x7dc6),amounts):ram[address]=amount
        expected=bytearray(ram)
        expected[0x2202:0x2220]=struct.pack('>15H',*[model(a,b,weight,amounts) for a,b in zip(first,second)])
        cpu.mem_write(0x100000,bytes(ram))
        for reg,value in ((UC_M68K_REG_A0,0x102000),(UC_M68K_REG_A1,0x102100),(UC_M68K_REG_A2,0x104d92),(UC_M68K_REG_A3,lookup),(UC_M68K_REG_A4,0x102200),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_D0,weight)):cpu.reg_write(reg,value)
        call(cpu,entry)
        actual=bytes(cpu.mem_read(0x100000,65536))
        if actual!=expected or cpu.reg_read(UC_M68K_REG_A4)!=0x102200 or cpu.reg_read(UC_M68K_REG_A2)!=0x104d92:raise ValueError('Effect mismatch '+repr((entry,weight,amounts)))
        rows.append(hashlib.sha256(actual).hexdigest())
    for channel in range(32):
        value=channel|(channel<<5)|(channel<<10)
        for amount in range(256):run([value]*15,[value]*15,0,(amount,amount,amount),0x479e)
    for index in range(32):
        first=[((index*977+i*811)&32767) for i in range(15)]
        second=[((32767-index*619-i*983)&32767) for i in range(15)]
        amounts=(index*7&255,index*13&255,index*29&255)
        for weight in list(range(32))+[255]:run(first,second,weight,amounts,0x504c)
    destination=root/'artifacts/palette_effect';destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'single_effect_cases':8192,'blend_effect_cases':1056,'all_ram_equal':True,
        'scope':'Every5-bit channel/byte effect combination in original479e, distinct-channel synthetic15-bit palettes in504c. Byte wrap precedes signed-negative zeroing and upper clamp; no natural effect-state lifecycle claim.', 'ram_hashes':rows},indent=2)+'\n')
    print('Original palette effects match:',len(rows),'cases')


if __name__=='__main__':main()
