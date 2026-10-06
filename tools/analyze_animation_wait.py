"""Ground animation wait/end state transitions against the original interpreter."""
import argparse
import subprocess
import hashlib
import json
from pathlib import Path
import struct
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def word(ram,at): return int.from_bytes(ram[at:at+2],'big')
def put(ram,at,value): ram[at:at+2]=(value&65535).to_bytes(2,'big')
def signed(value): return value-65536 if value&32768 else value


def model(initial,obj):
    ram=bytearray(initial)
    state=obj+0x26
    pointer=int.from_bytes(ram[state:state+4],'big')
    put(ram,0x10,0)
    if pointer==0:
        return ram,1,0
    ram[0xd742]=0
    if 0<ram[obj+0x17]<128: ram[obj+0x17]-=1
    cursor=pointer
    for steps in range(10000):
        opcode=ram[cursor-0x100000];cursor+=1
        timer=word(ram,state+4)
        if opcode==0x28:
            if signed(timer)<0:
                put(ram,state+4,0);cursor=pointer;continue
            ram[state+4]=0
            return ram,1,steps+1
        if opcode!=0:
            raise ValueError('Outside wait/end subset')
        ram[0xd742]=(ram[0xd742]+1)&255
        duration=ram[cursor-0x100000];cursor+=1
        if duration==0:
            if signed(timer)<0:
                put(ram,state+4,0);cursor=pointer;continue
            return ram,0,steps+1
        old=timer
        if signed(old)<=0:
            timer=((((timer>>8)+duration)&255)<<8)|(timer&255)
        if signed(old)>=0:
            timer=(timer-word(ram,state+6))&65535
        put(ram,state+4,timer)
        if signed(timer)>0: cursor=pointer
        ended=ram[cursor-0x100000]==0x28
        if ended: cursor=pointer
        if signed(old)<0: continue
        ram[state:state+4]=cursor.to_bytes(4,'big')
        return ram,int(ended),steps+1
    raise ValueError('Model instruction limit')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cpp',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    # SCS absolute long captures the actual CPU carry flag after RTS.
    cpu.mem_write(0xff100,bytes.fromhex('55f900105900'))
    destination=root/'artifacts/animation_wait';destination.mkdir(parents=True,exist_ok=True)
    def check_cpp(initial,expected,carry):
        if not args.cpp: return
        (destination/'input.bin').write_bytes(initial)
        (destination/'script.bin').write_bytes(initial[0x5800:0x5806])
        subprocess.run([str(root/'build/step_animation'),str(destination/'input.bin'),str(destination/'script.bin'),
            str(destination/'output.bin'),str(destination/'status.bin'),'8192','0x105800'],check=True)
        if (destination/'output.bin').read_bytes()!=expected or (destination/'status.bin').read_bytes()!=struct.pack('>I',carry):
            raise ValueError('C++ wait mismatch')
    results=[]
    for timer in (0,1,255,256,32767,32768,0xff00,0xffff):
        for speed in (0,1,256,65535):
            for duration in (0,1,2,127,128,255):
                for tail in (0,0x28):
                    for countdown in (0,1,127,128,255):
                        ram=bytearray(65536);obj=0x2000;state=obj+0x26
                        ram[state:state+4]=(0x105800).to_bytes(4,'big')
                        put(ram,state+4,timer);put(ram,state+6,speed)
                        ram[obj+0x17]=countdown;ram[0xd742]=201;put(ram,0x10,3)
                        ram[0x5800:0x5806]=bytes((0,duration,tail,0,0x28,0))
                        expected,carry,steps=model(ram,obj)
                        cpu.mem_write(0x100000,bytes(ram))
                        cpu.reg_write(UC_M68K_REG_A5,0x108000);cpu.reg_write(UC_M68K_REG_A6,0x102000)
                        cpu.reg_write(UC_M68K_REG_A7,0x1feffc)
                        cpu.mem_write(0x1feffc,(0xff100).to_bytes(4,'big'))
                        cpu.emu_start(0x49fc6,0xff106,count=20000)
                        if cpu.reg_read(UC_M68K_REG_PC)!=0xff106:
                            raise ValueError('Wait did not return')
                        actual=bytearray(cpu.mem_read(0x100000,65536))
                        if actual[0x5900] != (255 if carry else 0):
                            raise ValueError('Wait return carry mismatch')
                        actual[0x5900]=ram[0x5900]
                        if actual!=expected:
                            diffs=[hex(i) for i in range(65536) if actual[i]!=expected[i]]
                            raise ValueError('Wait state mismatch '+repr((timer,speed,duration,tail,countdown,diffs[:12])))
                        check_cpp(ram,expected,carry)
                        results.append({'timer':timer,'speed':speed,'duration':duration,'tail':tail,'countdown':countdown,
                                        'model_steps':steps,'ram_sha256':hashlib.sha256(actual).hexdigest()})
    for kind in ('inactive','end'):
        for timer in (0,1,255,256,32767,32768,0xff00,0xffff):
            for countdown in (0,1,127,128,255):
                ram=bytearray(65536);obj=0x2000;state=obj+0x26
                pointer=0 if kind=='inactive' else 0x105800
                ram[state:state+4]=pointer.to_bytes(4,'big')
                put(ram,state+4,timer);put(ram,state+6,256)
                ram[obj+0x17]=countdown;ram[0xd742]=201;put(ram,0x10,3)
                ram[0x5800]=0x28
                expected,carry,steps=model(ram,obj)
                cpu.mem_write(0x100000,bytes(ram))
                cpu.reg_write(UC_M68K_REG_A5,0x108000);cpu.reg_write(UC_M68K_REG_A6,0x102000)
                cpu.reg_write(UC_M68K_REG_A7,0x1feffc)
                cpu.mem_write(0x1feffc,(0xff100).to_bytes(4,'big'))
                cpu.emu_start(0x49fc6,0xff106,count=20000)
                if cpu.reg_read(UC_M68K_REG_PC)!=0xff106:
                    raise ValueError('End/inactive did not return')
                actual=bytearray(cpu.mem_read(0x100000,65536))
                if actual[0x5900]!=(255 if carry else 0):
                    raise ValueError('End/inactive carry mismatch')
                actual[0x5900]=ram[0x5900]
                if actual!=expected:
                    raise ValueError('End/inactive RAM mismatch')
                check_cpp(ram,expected,carry)
                results.append({'kind':kind,'timer':timer,'countdown':countdown,
                                'model_steps':steps,'ram_sha256':hashlib.sha256(actual).hexdigest()})
    destination=root/'artifacts/animation_wait';destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'cases':len(results),'cpp_verified':args.cpp,'all_ram_equal':True,'return_carry_equal':True,
        'scope':'Wait/end-only controlled RAM scripts through original interpreter. Return carry checked through original CPU SCS. Draw opcodes, natural scripts and timing not verified.','results':results},indent=2)+'\n')
    print('Animation wait/end RAM matches:',len(results),'cases')


if __name__=='__main__': main()
