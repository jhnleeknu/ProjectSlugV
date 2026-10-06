"""Consecutive wait/draw script steps through the original and C++ sprite paths."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from analyze_animation_wait import put


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory=root/'artifacts/animation_pipeline';directory.mkdir(parents=True,exist_ok=True)
    inp,out,status,script_path=[directory/name for name in ('input.bin','output.bin','status.bin','script.bin')]
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    cpu.mem_write(0x200000,program[0x400000:0x500000])
    cpu.mem_write(0xff100,bytes.fromhex('55f900105900'))
    events=[]
    def hook(cpu,access,address,size,value,user):
        if 0x3c0000<=address<0x3c0010:
            if address!=0x3c0000 or size!=4: raise ValueError('Unexpected video write')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE,hook)
    def run(entry):
        cpu.reg_write(UC_M68K_REG_A5,0x108000);cpu.reg_write(UC_M68K_REG_A6,0x102000)
        cpu.reg_write(UC_M68K_REG_A7,0x1feffc);cpu.mem_write(0x1feffc,struct.pack('>I',0xff100))
        events.clear();cpu.emu_start(entry,0xff106,count=1000000)
        if cpu.reg_read(UC_M68K_REG_PC)!=0xff106: raise ValueError('Original did not return')
        result=bytearray(cpu.mem_read(0x100000,65536));carry=int(result[0x5900]!=0)
        result[0x5900]=0;cpu.mem_write(0x105900,b'\x00')
        return result,carry
    script=bytes((4,0,0,0))+struct.pack('>I',0x2152)+bytes((0,2,4,4,1,1))+struct.pack('>I',0x2382a)+bytes((0,1,0x28))
    script_path.write_bytes(script)
    resources=[str(root/'extracted/runtime'/('composition_%06x.ms5c'%i)) for i in (0x2152,0x2382a)]
    rows=[]
    for timer in (0,65535):
        for speed in (128,256):
            for direction in (0,128):
                cpu.mem_write(0x100000,bytes(65536));state,_=run(0xccd6)
                state[0x8d3c]=direction
                state[0x8d3e:0x8d46]=struct.pack('>4H',0,380,0,380)
                obj=0x2000
                struct.pack_into('>I',state,obj+0x12,0xffff1503)
                state[obj+0x19]=21;put(state,obj+0x1e,13)
                put(state,obj+0x42,160);put(state,obj+0x46,384)
                state[obj+0x26:obj+0x2a]=struct.pack('>I',0x105800)
                put(state,obj+0x2a,timer);put(state,obj+0x2c,speed)
                state[0x5800:0x5800+len(script)]=script
                cpu.mem_write(0x100000,bytes(state))
                for frame in range(12):
                    expected,carry=run(0x49fc6)
                    inp.write_bytes(state)
                    subprocess.run([str(root/'build/step_animation'),str(inp),str(script_path),str(out),str(status),str(obj),'0x105800'],check=True)
                    state=out.read_bytes()
                    if state!=expected or status.read_bytes()!=struct.pack('>I',carry):
                        raise ValueError('Animation step mismatch '+repr((timer,speed,direction,frame)))
                    pointer=int.from_bytes(state[obj+0x26:obj+0x2a],'big')
                    remaining=int.from_bytes(state[obj+0x2a:obj+0x2c],'big')
                    for stage,entry in (('prepare',0x16bba),('refresh',0x16cfa)):
                        expected,_=run(entry);inp.write_bytes(state)
                        subprocess.run([str(root/('build/'+stage+'_sprite_queue')),str(inp),str(out),str(status)]+resources,check=True)
                        state=out.read_bytes()
                        trace=(struct.pack('>I',1) if stage=='refresh' else b'')+b''.join(struct.pack('>I',w) for w in events)
                        if state!=expected or status.read_bytes()!=trace:
                            raise ValueError('Animation video pipeline mismatch')
                        rows.append({'initial_timer':timer,'speed':speed,'initial_direction':direction,'frame':frame,
                            'stage':stage,'script_pointer':pointer,'timer':remaining,'ram_sha256':hashlib.sha256(state).hexdigest(),
                            'video_sha256':hashlib.sha256(trace).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({'source':source,'sequences':8,'steps':96,'video_stages':len(rows),
        'all_ram_carry_video_equal':True,'scope':'Controlled script combining draw/wait/boundary. Actual MS5C resources; no natural script or interrupt/timing claim.','results':rows},indent=2)+'\n')
    print('Animation pipeline matches: 96 interpreter steps,',len(rows),'video stages')


if __name__=='__main__': main()
