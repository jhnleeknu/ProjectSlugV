"""Whole original 3c44, full RAM/registers and all three byte wait stages."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from disassemble_program import load_verified_program, disassemble_range
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from observe_stage_region_frame import KEYS, BASE, STACK, RETURN
from pack_stage_input import SOURCE_SHA256
ENTRY, WAIT = 0x3c44, 0x3aea

def sha(data): return hashlib.sha256(data).hexdigest()
def put(ram, at, value): struct.pack_into('>H', ram, at, value)
def fixture(command, head=0, tail=6, byte_head=0xffff, byte_tail=0):
    ram=bytearray(hashlib.shake_256(b'sound-cancel').digest(65536))
    for i in range(4): put(ram,0x4d82+2*i,command if i%2==0 else command^0x100)
    put(ram,0x4d8a,head);put(ram,0x4d8c,tail)
    put(ram,0x4d74,byte_head);put(ram,0x4d76,byte_tail)
    regs=[(0xabcd0000+i*0x10203)&0xffffffff for i in range(14)]
    regs[0]=(regs[0]&0xffff0000)|command
    return ram,regs

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    names=['build/execute_sound_cancel','engine/src/sound_cancel_execution.cpp','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_cancel_execution.h','engine/include/ms5/sound_byte_execution.h','engine/tools/execute_sound_cancel.cpp','tools/verify_sound_cancel_execution.py']
    inputs={f:sha((root/f).read_bytes()) for f in names};oracle=oracle_provenance(root)
    folder=root/'artifacts/sound_cancel_execution';folder.mkdir(parents=True,exist_ok=True)
    cpu=MusashiOracle();cpu.load(0,program[:BASE]);rows=[];pcs=[];writes=[]
    def write(pc,address,size,value):
        assert BASE<=address and address+size<=BASE+65536 or STACK-64<=address and address+size<=STACK+4
        if BASE<=address<BASE+65536:writes.append(dict(pc=pc,address=address,size=size,value=value&((1<<(8*size))-1)))
    cpu.set_instruction_hook(lambda pc:pcs.append(pc));cpu.set_write_hook(write)
    def prepare(ram,regs):
        cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for k,v in zip(KEYS,regs):cpu.set_reg(k,v)
        cpu.set_reg('pc',ENTRY)
    def compare(ram,regs,phase=0,saved=0,label='',changes=None):
        pcs.clear();writes.clear();original_word=regs[0]&65535 if phase==0 else saved
        for step in range(2000):
            pc=cpu.get_reg('pc')
            if pc==RETURN:break
            if pc==WAIT and (cpu.get_reg('d1')&65535)==int.from_bytes(cpu.read(BASE+0x4d74,2),'big'):
                cpu.run(2,RETURN);assert pcs[-2:]==[WAIT,0x3aee] and cpu.get_reg('pc')==WAIT;break
            cpu.run(1,RETURN)
        else:raise AssertionError('native loop failed to return/wait')
        waiting=cpu.get_reg('pc')==WAIT
        outphase=0
        if waiting:
            sp=cpu.get_reg('a7');ret=int.from_bytes(cpu.read(sp,4),'big')
            outphase={0x3c70:1,0x3c76:2,RETURN:3}[ret]
            assert sp==(STACK if outphase==3 else STACK-6)
            if outphase!=3:assert int.from_bytes(cpu.read(sp+4,2),'big')==original_word
        else:assert cpu.get_reg('a7')==STACK+4
        assert cpu.get_reg('a5')==0x108000
        expected=cpu.read(BASE,65536);result={k:cpu.get_reg(k) for k in KEYS}
        result.update(waiting=waiting,phase=outphase,saved_word=original_word if waiting else 0)
        replay=ram.copy()
        for w in writes:
            at=w['address']-BASE;replay[at:at+w['size']]=w['value'].to_bytes(w['size'],'big')
        assert replay==expected and cpu.read(0,BASE)==program[:BASE]
        inp,out=folder/'input.bin',folder/'cpp.bin';inp.write_bytes(ram)
        args=[str(root/'build/execute_sound_cancel')]+list(map(str,regs))+[str(int(phase!=0)),str(phase),str(saved),str(inp),str(out)]
        p=subprocess.run(args,capture_output=True,text=True)
        assert p.returncode==0 and inp.read_bytes()==ram and out.read_bytes()==expected and json.loads(p.stdout)==result,(label,p.stderr,p.stdout,result)
        name='native_%04d.bin'%len(rows);(folder/name).write_bytes(expected)
        rows.append(dict(label=label,incoming=dict(zip(KEYS,regs),phase=phase,saved_word=saved),changes=changes or [],result=result,pcs=pcs.copy(),writes=writes.copy(),ram_file=name,ram_sha256=sha(expected),input_sha256=sha(ram)))
        return bytearray(expected),[result[k] for k in KEYS],outphase,result['saved_word']
    for command in (0,3,0x300,0x303,0x1d28,0xffff):
        for head in (0,2,4,6):
            for tail in (0,2,4,6):
                ram,regs=fixture(command,head,tail);prepare(ram,regs);assert compare(ram,regs,label='queue-and-command')[2]==0
    for command in range(256):
        ram,regs=fixture((command<<8)|0x28);prepare(ram,regs);assert compare(ram,regs,label='all-high-bytes')[2]==0
        ram,regs=fixture(0x1d00|command);prepare(ram,regs);assert compare(ram,regs,label='all-low-bytes')[2]==0
    for head in (0xb27e,0xfffe,8,10,0x7ffc):
        # signed arbitrary initial index followed by the masked four-slot ring.
        ram,regs=fixture(0x1d28,head,6)
        if head not in (8,10):put(ram,(0x4d82+(head if head<0x8000 else head-65536)),0x1d28)
        prepare(ram,regs);assert compare(ram,regs,label='signed-head-alias')[2]==0
    ram,regs=fixture(6,10,6);prepare(ram,regs)
    assert compare(ram,regs,label='clear-live-tail-alias')[2]==0
    chains=0
    for target in (1,2,3):
        for tail in (0,125,127):
            ram,regs=fixture(0x1d28,byte_tail=tail,byte_head=(tail+target)&127);prepare(ram,regs)
            ram,regs,phase,saved=compare(ram,regs,label='wait-start');assert phase==target;chains+=1
            # Poison queue and producer tail; continuation must not scan again.
            changes=[(0x4d76,0x8000),(0x4d8a,0x8001),(0x4d8c,0xffff)]
            for at,value in changes:put(ram,at,value);cpu.load(BASE+at,value.to_bytes(2,'big'))
            ram,regs,phase,saved=compare(ram,regs,phase,saved,'wait-hold',changes);assert phase==target
            put(ram,0x4d74,0xffff);cpu.load(BASE+0x4d74,b'\xff\xff')
            ram,regs,phase,saved=compare(ram,regs,phase,saved,'wait-release',[(0x4d74,0xffff)]);assert phase==0
    # One invocation passes through all three pending stages without CPU reset.
    ram,regs=fixture(0x1d28,byte_head=1);prepare(ram,regs)
    ram,regs,phase,saved=compare(ram,regs,label='three-stage-start');assert phase==1;chains+=1
    for head,expected_phase in ((2,2),(3,3),(4,0)):
        put(ram,0x4d74,head);cpu.load(BASE+0x4d74,head.to_bytes(2,'big'))
        ram,regs,phase,saved=compare(ram,regs,phase,saved,'three-stage-resume',[(0x4d74,head)]);assert phase==expected_phase
    negatives=[]
    for head,tail,btail,phase,waiting in ((1,0,0,0,0),(0x8000,0,0,0,0),(0,1,0,0,0),(0,2,0x8000,0,0),(0,0,0,0,1),(0,0,0,1,0),(0,0,0,3,0)):
        ram,regs=fixture(0x1d28,head,tail,byte_tail=btail)
        inp,out=folder/'input.bin',folder/'cpp.bin';inp.write_bytes(ram);out.write_bytes(b'preserved')
        args=[str(root/'build/execute_sound_cancel')]+list(map(str,regs))+[str(waiting),str(phase),'0',str(inp),str(out)]
        p=subprocess.run(args,capture_output=True,text=True)
        assert p.returncode and not p.stdout and inp.read_bytes()==ram and out.read_bytes()==b'preserved'
        negatives.append(dict(head=head,tail=tail,byte_tail=btail,phase=phase,waiting=waiting))
    branches=collections.defaultdict(set)
    for row in rows:
        trace=row['pcs']+[WAIT if row['result']['waiting'] else RETURN]
        for a,b in zip(trace,trace[1:]):
            if a in (0x3c52,0x3c62,0x3acc,0x3aee):branches[a].add(b)
    assert all(len(branches[a])==2 for a in (0x3c52,0x3c62,0x3acc,0x3aee))
    assert inputs=={f:sha((root/f).read_bytes()) for f in names} and oracle_provenance(root)==oracle
    report=dict(source=source,inputs=inputs,oracle=oracle,instructions=disassemble_range(program,ENTRY,0x3c7c-ENTRY,ENTRY),cases=len(rows),chains=chains,negative_cases=negatives,branches={hex(a):sorted(b) for a,b in branches.items()},results=rows)
    dest=folder/'verification.json';dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),sha256=sha(dest.read_bytes()))))
if __name__=='__main__':main()
