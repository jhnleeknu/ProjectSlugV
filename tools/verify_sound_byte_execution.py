"""Original3ac8/3aea full registers, unchanged same-CPU wait and actual CLI resume."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from disassemble_program import load_verified_program,disassemble_range
from musashi_oracle import MusashiOracle
from pack_stage_input import SOURCE_SHA256
from observe_scene_motion_pair import oracle_provenance
from observe_stage_region_frame import KEYS,BASE,STACK,RETURN
ENTRY,WAIT=0x3ac8,0x3aea

def sha(b):return hashlib.sha256(b).hexdigest()
def fixture(command,tail,head,profile=1):
    ram=bytearray(hashlib.shake_256(b'sound-byte-execution').digest(65536));struct.pack_into('>HH',ram,0x4d74,head,tail)
    regs=[(0xabcd0000+i*0x10203)&0xffffffff for i in range(14)] if profile else [0]*14
    regs[0]=(regs[0]&0xffffff00)|command
    return ram,regs

def provenance(root):
    names=('build/execute_sound_byte','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_byte_execution.h','engine/tools/execute_sound_byte.cpp','engine/include/ms5/scene_map_transfer.h','tools/verify_sound_byte_execution.py','tools/disassemble_program.py')
    return [dict(file=f,sha256=sha((root/f).read_bytes())) for f in names]
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;inputs=provenance(root);oracle=oracle_provenance(root);cpu=MusashiOracle();cpu.load(0,program[:BASE]);folder=root/'artifacts/sound_byte_execution';folder.mkdir(parents=True,exist_ok=True);rows=[];writes=[];pcs=[]
    listing=disassemble_range(program,ENTRY,0x3af8-ENTRY,ENTRY)
    assert next(r for r in listing if r['cpu_address']==WAIT)['op_str']=='-$328c(a5), d1'
    def code(pc):pcs.append(pc)
    def write(pc,address,size,value):
        assert BASE<=address and address+size<=BASE+65536 or STACK-64<=address and address+size<=STACK+4
        if BASE<=address<BASE+65536:writes.append(dict(pc=pc,address=address,size=size,value=value&((1<<(size*8))-1)))
    cpu.set_instruction_hook(code);cpu.set_write_hook(write)
    def prepare(ram,regs):
        cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for k,v in zip(KEYS,regs):cpu.set_reg(k,v)
        cpu.set_reg('pc',ENTRY)
    def compare(ram,regs,waiting,label,external=None):
        writes.clear();pcs.clear()
        if not waiting:
            stop=RETURN if regs[0]&255==3 else WAIT
            status=cpu.run(50,stop);assert status['status']=='sentinel',status
        if cpu.get_reg('pc')==WAIT:
            if cpu.get_reg('d1')&65535==int.from_bytes(cpu.read(BASE+0x4d74,2),'big'):
                cpu.run(2,RETURN);assert cpu.get_reg('pc')==WAIT and pcs[-2:]==[WAIT,0x3aee]
            else:
                status=cpu.run(50,RETURN);assert status['status']=='sentinel',status
        pending=cpu.get_reg('pc')==WAIT
        assert cpu.get_reg('pc') in (WAIT,RETURN) and cpu.get_reg('a7')==(STACK if pending else STACK+4)
        expected=cpu.read(BASE,65536);result={k:cpu.get_reg(k) for k in KEYS};result['waiting']=pending
        replay=ram.copy()
        for w in writes:
            at=w['address']-BASE;replay[at:at+w['size']]=w['value'].to_bytes(w['size'],'big')
        assert replay==expected and cpu.read(0,BASE)==program[:BASE]
        inp,out=folder/'input.bin',folder/'cpp.bin';inp.write_bytes(ram)
        p=subprocess.run([str(root/'build/execute_sound_byte')]+list(map(str,regs))+[str(int(waiting)),str(inp),str(out)],capture_output=True,text=True)
        assert p.returncode==0 and inp.read_bytes()==ram and out.read_bytes()==expected and json.loads(p.stdout)==result,(label,p.stderr,p.stdout,result)
        name='native_%04d.bin'%len(rows);(folder/name).write_bytes(expected)
        rows.append(dict(label=label,incoming=dict(zip(KEYS,regs),waiting=waiting),external_RAM_writes=external or [],input_sha256=sha(ram),result=result,ram_file=name,ram_sha256=sha(expected),pcs=pcs.copy(),RAM_writes=writes.copy(),final_pc=cpu.get_reg('pc'),final_a7=cpu.get_reg('a7')))
        return bytearray(expected),[result[k] for k in KEYS],pending
    for command in range(256):
        for tail in (0,127):
            ram,regs=fixture(command,tail,((tail+1)&127)^1,tail!=0);prepare(ram,regs);_,_,pending=compare(ram,regs,False,'all-byte-commands-and-wrap');assert not pending
    for tail in (0xb30c,0xffff,0x80,0x81,0x82,0x83,0x7fff):
        for command in (0,3,255):
            ram,regs=fixture(command,tail,0xffff);prepare(ram,regs);_,_,pending=compare(ram,regs,False,'signed-tail-live-alias');assert not pending
    for tail in (0,127,0xffff,0x80,0x82,0xb30c,0x7fff):
        ram,regs=fixture(0x55,tail,(tail+1)&127);prepare(ram,regs);ram,regs,pending=compare(ram,regs,False,'wait-start');assert pending
        # Preserve CPU and captured A0/D1. Change only the externally visible tail.
        changes=[dict(address=BASE+0x4d76,raw_hex='8000')];ram[0x4d76:0x4d78]=bytes.fromhex('8000');cpu.load(BASE+0x4d76,bytes.fromhex('8000'))
        ram,regs,pending=compare(ram,regs,True,'wait-hold-changed-tail',changes);assert pending
        changes=[dict(address=BASE+0x4d74,raw_hex='ffff')];ram[0x4d74:0x4d76]=bytes.fromhex('ffff');cpu.load(BASE+0x4d74,bytes.fromhex('ffff'))
        ram,regs,pending=compare(ram,regs,True,'wait-ready-captured-address',changes);assert not pending
    # CMP.W must distinguish equal low bytes with different upper bytes.
    for tail in (0,127,0xffff):
        for high in (0x0100,0x8000):
            head=((tail+1)&127)|high
            ram,regs=fixture(0x55,tail,head);prepare(ram,regs)
            _,_,pending=compare(ram,regs,False,'head-high-byte-fresh');assert not pending
    for high in (0x0100,0x8000):
        ram,regs=fixture(0x55,0,1);prepare(ram,regs)
        ram,regs,pending=compare(ram,regs,False,'head-high-byte-wait-start');assert pending
        raw=(1|high).to_bytes(2,'big');ram[0x4d74:0x4d76]=raw;cpu.load(BASE+0x4d74,raw)
        changes=[dict(address=BASE+0x4d74,raw_hex=raw.hex())]
        _,_,pending=compare(ram,regs,True,'head-high-byte-release',changes);assert not pending
    negatives=[]
    inp,out=folder/'input.bin',folder/'cpp.bin'
    for waiting,address,tail in ((0,0,0x8000),(1,0xfffff,0),(1,0x110000,0),(1,0xffffffff,0)):
        ram,regs=fixture(0x55,tail,0xffff);regs[8]=address;inp.write_bytes(ram);out.write_bytes(b'preserved')
        p=subprocess.run([str(root/'build/execute_sound_byte')]+list(map(str,regs))+[str(waiting),str(inp),str(out)],capture_output=True,text=True)
        assert p.returncode and not p.stdout and inp.read_bytes()==ram and out.read_bytes()==b'preserved';negatives.append(dict(waiting=waiting,address=address,tail=tail))
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==source['sha256']
    branches=collections.defaultdict(collections.Counter)
    for row in rows:
        trace=row['pcs']+[row['final_pc']]
        for pc,nextpc in zip(trace,trace[1:]):
            if pc in (0x3acc,0x3aee):branches[pc][nextpc]+=1
    assert all(len(branches[pc])==2 for pc in (0x3acc,0x3aee))
    report=dict(branches={hex(pc):{hex(n):v for n,v in counts.items()} for pc,counts in branches.items()},source=source,inputs=inputs,oracle=oracle,instructions=listing,cases=len(rows),pending_chains=9,actual_CLI_resumes=16,negative_cases=negatives,results=rows,scope='Whole unmodified3ac8 or same-CPU3aea continuation; fullRAM14registers/waiting. Native ordered writes replayed, fixedROM immutable, no in-hookSR read. Explicit host tail/head changes only. No IRQ timing or fullsound-frame claim.')
    p=folder/'verification.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),sha256=sha(p.read_bytes()))))
if __name__=='__main__':main()
