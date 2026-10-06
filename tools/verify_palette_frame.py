"""Compare original effect advancement plus conditional palette preparation."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_write(0x200000,program[0x200000:0x300000]);cpu.reg_write(UC_M68K_REG_A5,0x108000)
    cpu.mem_write(0x100000,bytes(65536));call(cpu,0x3ef2)
    initial=bytes(cpu.mem_read(0x100000,65536));folder=root/'artifacts/palette_frame';folder.mkdir(parents=True,exist_ok=True)
    inp,out=folder/'input.bin',folder/'output.bin';rows=[]
    fixtures=((0,0,0),(0x00ff,1,0x1000),(0x7fff,1,0x8000),(0xffff,1,0),(0x8000,0xffff,0x7fff),(0x1000,0x0080,0xf000),(0x1234,0,0x12ff))
    for timer in (0,1,2,128,255):
        for current,step,target in fixtures:
            for pending in (0,127,128,255):
                state=bytearray(initial)
                for channel in range(3):
                    struct.pack_into('>H',state,0x7dc2+channel*2,(current+channel*0x101)&65535)
                    struct.pack_into('>H',state,0x7dc8+channel*2,(target+channel*0x101)&65535)
                    struct.pack_into('>H',state,0x7dce+channel*2,step)
                state[0x7dd4]=timer;state[0x7ded]=pending
                for slot in range(256):
                    node=0x4d92+slot*16
                    struct.pack_into('>HH',state,node+10,0x203,0x87a if slot&1 else 0x203)
                    state[node+14]=slot&31
                    state[node+15]=(slot&3)|(0x80 if slot%7==0 else 0)
                cpu.mem_write(0x100000,bytes(state));cpu.reg_write(UC_M68K_REG_A5,0x108000)
                cpu.reg_write(UC_M68K_REG_A7,0x1feffc);cpu.mem_write(0x1feffc,struct.pack('>I',0xff000))
                cpu.emu_start(0x5728,0xff000,count=500000)
                if cpu.reg_read(UC_M68K_REG_PC)!=0xff000:raise ValueError('Frame routine did not return')
                expected=bytes(cpu.mem_read(0x100000,65536));inp.write_bytes(state)
                subprocess.run([str(root/'build/step_palette_frame'),str(inp),str(root/'extracted/runtime/palettes.ms5p'),str(out)],check=True)
                if out.read_bytes()!=expected:raise ValueError('Palette frame mismatch '+repr((timer,current,step,target,pending)))
                rows.append({'timer':timer,'current':current,'step':step,'target':target,'pending':pending,'ram_sha256':hashlib.sha256(expected).hexdigest()})
    (folder/'verification.json').write_text(json.dumps({'source':source,'cases':len(rows),'all_ram_equal':True,
        'scope':'Original5728 entry including unrolled dirty marking and7196 preparation when gate permits. Fractional/overflow/terminal timer boundaries, all256 node flags, normal and mixed palette effects. Watchdog/PVC timing and natural frame call site remain outside comparison.', 'results':rows},indent=2)+'\n')
    print('Palette frame original/C++ RAM match:',len(rows),'cases')


if __name__=='__main__':main()
