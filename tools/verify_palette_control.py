"""Verify effect setup and per-slot blend controls against original code."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def signed(value):return value if value<32768 else value-65536

def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    if program[0xfa0:0xfb4]!=bytes.fromhex('70fc72fc74fc76044eb900008c164eb900005728'):raise ValueError('Effect setter/frame caller changed')
    cpu=make_cpu(program);folder=root/'artifacts/palette_control';folder.mkdir(parents=True,exist_ok=True)
    inp,out=folder/'input.bin',folder/'output.bin';rows=[]
    def run(ram,expected,kind,args,entry):
        cpu.mem_write(0x100000,bytes(ram));cpu.reg_write(UC_M68K_REG_A5,0x108000)
        for reg,value in zip((UC_M68K_REG_D0,UC_M68K_REG_D1,UC_M68K_REG_D2,UC_M68K_REG_D3),args):cpu.reg_write(reg,value)
        call(cpu,entry);actual=bytes(cpu.mem_read(0x100000,65536))
        if actual!=expected:raise ValueError('Original control model mismatch '+repr((kind,args)))
        inp.write_bytes(ram)
        subprocess.run([str(root/'build/control_palette'),kind,str(inp),str(out)]+[str(v) for v in args],check=True)
        if out.read_bytes()!=expected:raise ValueError('C++ control mismatch '+repr((kind,args)))
        rows.append({'kind':kind,'args':args,'ram_sha256':hashlib.sha256(actual).hexdigest()})
    for value in (0,1,30,31,32,127,32767,32768,65504,65505,65506,65535):
        for current in (0,255,32767,32768,65535,0x1f00,0xe100):
            for duration in (0,1,2,31,128,255):
                ram=bytearray(65536);ram[0x7dce:0x7dd4]=bytes.fromhex('deadbeef1234')
                values=(value,(value+1)&65535,(value-1)&65535)
                for n in range(3):put(ram,0x7dc2+n*2,current)
                expected=bytearray(ram);deltas=[]
                for n,v in enumerate(values):
                    target=max(-31,min(31,signed(v)))*256
                    put(expected,0x7dc8+n*2,target);deltas.append(signed((target-current)&65535))
                ticks=max(1,duration);expected[0x7dd4]=ticks if any(deltas) else 0
                if any(deltas):
                    for n,delta in enumerate(deltas):put(expected,0x7dce+n*2,(abs(delta)//ticks)*(-1 if delta<0 else 1))
                run(ram,expected,'effect',(*values,duration),0x8c16)
    # Exact target equality must preserve the old step words while cancelling timer.
    ram=bytearray(65536);ram[0x7dce:0x7dd4]=bytes.fromhex('deadbeef1234');ram[0x7dd4]=99
    expected=bytearray(ram);expected[0x7dd4]=0
    run(ram,expected,'effect',(0,0,0,255),0x8c16)
    for refs in (0,1,65535):
        for slot in (0,255):
            for previous_target in (0x203,0x87a):
                for target in (0x203,0x87a,65535):
                    for old_weight in (0,32):
                        for weight in (0,1,31,32,33,255):
                            ram=bytearray(65536);node=0x4d92+slot*16
                            put(ram,node+8,refs);put(ram,node+10,0x203);put(ram,node+12,previous_target)
                            ram[node+14]=old_weight;ram[node+15]=3
                            expected=bytearray(ram);capped=min(weight,32)
                            if refs:
                                if target!=previous_target:
                                    put(expected,node+12,target);expected[node+14]=capped;expected[node+15]|=128
                                elif capped!=old_weight:
                                    expected[node+14]=capped
                                    if target!=0x203:expected[node+15]|=128
                            run(ram,expected,'blend',(slot,target,weight),0x8cda)
    refs={}
    for entry in (0x8c16,0x8cda):
        pattern=b'\x4e\xb9'+struct.pack('>I',entry)
        refs[hex(entry)]=[at for at in range(0,0x100000-6,2) if program[at:at+6]==pattern]
    (folder/'verification.json').write_text(json.dumps({'source':source,'cases':len(rows),'all_ram_equal':True,'aligned_jsr_candidates':refs,'verified_set_then_frame_call':{'setup':0xfa0,'set_call':0xfa8,'frame_call':0xfae,'target_signed':[-4,-4,-4],'duration':4},
        'scope':'Original effect setter and blend setter RAM; signed clamp/difference/division, timer minimum, equality preservation, reference gate, byte cap and dirty logic. Aligned JSR candidates are not natural reachability proof.', 'results':rows},indent=2)+'\n')
    print('Palette control original/C++ RAM match:',len(rows),'cases')


if __name__=='__main__':main()
