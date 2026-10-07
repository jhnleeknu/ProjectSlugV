"""Original e905c continuous event cursor initialization and restart cleanup."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
from inventory_stage_event_contexts import inventory as regenerate_inventory
from observe_object_restart_full import fixture as restart_fixture, HIGHS, KEYS, REGS
BASE, STACK, RETURN, ENTRY=0x100000,0x1feffc,0xff000,0xe905c
CALLS=(ENTRY,0x2a28,0x299c,0x8ff4,0x8e4a,0x43e38,0x271c,0xe9076,0xe907a,0xe907e,0xe908a,0xe909e,0xe90a6,0xe90ac,0xe90c8)

def sha(data):return hashlib.sha256(data).hexdigest()
def build_cases(root,program):
    inventory_path=root/'artifacts/stage_event_contexts.json';inventory=json.loads(inventory_path.read_text());regenerated=regenerate_inventory(root)
    assert (json.dumps(regenerated,indent=2)+'\n').encode()==inventory_path.read_bytes() and sha(program)==SOURCE_SHA256
    assert inventory['source']['sha256']==SOURCE_SHA256
    streams=inventory['streams'];assert len(streams)==47 and len(inventory['gate_cpu_addresses'])==612;cases=[]
    def add(family,stream=0,**changes):
        c=dict(family=family,stream=stream,target=0,profile=1,a5=0x108000,count=0,reference=0,coord=255,parent=0,stamp=0);c.update(changes);cases.append(c)
    for stream in streams:
        for target,profile in itertools.product((0,1,0x7fff,0x8000,0xffff),range(2)):add('canonical-all47-target-boundaries',stream['stream_cpu_address'],target=target,profile=profile)
    gates=0
    for stream in streams:
        for gate in stream['gates']:
            for target in ((gate['gate_word']-1)&65535,gate['gate_word'],(gate['gate_word']+1)&65535):add('all612-canonical-gate-minus-equal-plus',stream['stream_cpu_address'],target=target,gate=gate['cpu_address'],gate_word=gate['gate_word'])
            gates+=1
    assert gates==612
    for record in inventory['records']:add('actual59-stage-catalog-input-pairs',record['stream_pointer_long'],target=record['target_word'],record=record['record_cpu_address'])
    for target,profile in itertools.product((0,1,0x7fff,0x8000,0xffff),range(2)):add('null-stream-target-boundaries',target=target,profile=profile)
    first=streams[0]['stream_cpu_address']
    for coord,parent,profile in itertools.product((0,7,0x80,0xff),(0,0x100200,0x10d4e6,0x10d4ea),range(2)):
        add('palette-coordinate-cleanup-high-registers',first,target=0x7fff,profile=profile,count=2,reference=1,coord=coord,parent=parent,stamp=0x55)
    for a5,stream,profile in itertools.product((0x10740c,0x108100,0x108200,0x117348),(0,first),range(2)):add('alternate-valid-input-A5-object-before-reset',stream,a5=a5,profile=profile,target=1)
    for target in (0,1,0xffff):
        add('live-RAM-header-restart-alias-odd-FF-cursor',0x100c5e,target=target,ram_alias=True)
    for target in (0,1,7,8,9,0xffff):add('signed-negative-header-jump-in-RAM',0x106000,target=target,ram_kind='negative-header')
    for target in (1,8,9,10,0xffff):add('signed-negative-next-gate-jump-in-RAM',0x106000,target=target,ram_kind='negative-next')
    for seq,stream in enumerate((first,streams[-1]['stream_cpu_address'])):
        for step,(pointer,target) in enumerate(((stream,0),(stream,0x8000),(0,0xffff))):add('actual-cli-carry-nonnull-target-then-null',pointer,target=target,sequence=str(seq),sequence_position=step)
    assert len(cases)==2443
    return cases

def fixture(program,case):
    obj=(case['a5']-0x740c)&0xffffffff
    settings=dict(family=case['family'],object=obj,count=case['count'],reference=case['reference'],coord=case['coord'],parent=case['parent'],stamp=case['stamp'],profile=case['profile'],callback=0xe9150)
    ram=restart_fixture(program,settings);struct.pack_into('>H',ram,0x10,0xbeef)
    if obj==BASE:struct.pack_into('>H',ram,0x10,0)
    if case.get('ram_alias'):
        struct.pack_into('>H',ram,0xc5e,2);ram[0xd5f]=255
    if case.get('ram_kind')=='negative-header':
        struct.pack_into('>H',ram,0x6000,0xfff6);ram[0x5ff8:0x5ffe]=struct.pack('>B B H H',0,0,8,16);ram[0x6008]=255
    if case.get('ram_kind')=='negative-next':
        struct.pack_into('>H',ram,0x6000,6);ram[0x6008:0x600e]=struct.pack('>B B H H',0,0,8,0xfff0);ram[0x5ff8]=255
    return ram

def values(case,prior=None):
    vals=list(HIGHS[case['profile']] if prior is None else prior);vals[0]=(vals[0]&0xffff0000)|case['target'];vals[8]=case['stream'];vals[13]=case['a5'];return vals

class Observer:
    def __init__(self,program):
        self.cpu=make_cpu(program);self.cpu.mem_map(0x200000,0x300000);self.baseline=self.cpu.context_save();self.program=program;self.calls=collections.Counter();self.ports=[];self.error=None;self.instructions=0;self.reads=[];self.gates=[]
        def code(cpu,address,size,user):
            self.instructions+=1
            if address==RETURN:cpu.emu_stop();return
            if address in CALLS:self.calls[address]+=1
            if address==0xe908a:self.gates.append(cpu.reg_read(m.UC_M68K_REG_A1))
            word=int.from_bytes(cpu.mem_read(address,2),'big')
            if word==0x4afc or 0x4e40<=word<=0x4e4f:self.error=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            if address in (0x300001,0x2ffff2,0x2ffff0):
                self.ports.append((size,address,value&((1<<(size*8))-1)))
                if address==0x2ffff2:
                    assert size==2 and value==0x1000;cpu.mem_write(0x200000,program[0x200000:0x2ffff0])
                return
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
        def read(cpu,access,address,size,value,user):
            if 0x2ffff0<=address<0x500000:self.reads.append((size,address))
        def intr(cpu,number,user):self.error=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read);self.cpu.hook_add(UC_HOOK_INTR,intr)
    def run(self,ram,regs):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,self.program[0x200000:0x2ffff0]);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(REGS,regs):cpu.reg_write(register,value)
        self.calls.clear();self.ports.clear();self.error=None;self.instructions=0;self.reads.clear();self.gates.clear()
        try:cpu.emu_start(ENTRY,0xffffff,count=100000)
        except unicorn.UcError as e:self.error=dict(kind='emulator-error',error=str(e),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=RETURN and self.error is None:self.error=dict(kind='instruction-cap',pc=pc)
        assert not self.reads and bytes(cpu.mem_read(0,0x100000))==self.program[:0x100000]
        if pc==RETURN:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        result=dict(zip(KEYS,(cpu.reg_read(register)&0xffffffff for register in REGS)));output=bytes(cpu.mem_read(BASE,65536));ports=b''.join(struct.pack('>BII',*event) for event in self.ports)
        info=dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),calls={hex(k):v for k,v in self.calls.items()},instructions=self.instructions,error=self.error,mmio_reads=0,visited_gate_cursors=self.gates.copy())
        return output,result,ports,info

def assert_evidence(case,ram,output,result,ports,info,regs):
    if not info['returned']:return
    obj=(regs[13]-0x740c)&0xffffffff;assert result['a0']==obj and result['a5']==0x108000 and result['a6']==regs[14]
    assert result['d0']&65535==case['target'] and output[obj-BASE:obj-BASE+4]==(0xe9150).to_bytes(4,'big')
    cursor=int.from_bytes(output[obj-BASE+0x76:obj-BASE+0x7a],'big');assert cursor==result['d7']
    events=[struct.unpack_from('>BII',ports,i) for i in range(0,len(ports),9)];assert events[0]==(1,0x300001,regs[0]&255)
    if not case['stream']:
        assert len(events)==1 and output[0x10:0x12]==ram[0x10:0x12] and cursor==0 and info['calls'].get('0xe907a')==1
    else:
        assert events[1:]==[(2,0x2ffff2,0x1000),(2,0x2ffff0,0)] and output[0x10:0x12]==b'\0\0'
        if not case['target']:assert cursor==case['stream']+2 and not info['visited_gate_cursors']
    if case.get('ram_alias') and case['target']:assert cursor==0x100d5f and output[0xc5e:0xc60]==b'\0\xff'
    if case['count'] and case['reference']==1 and case.get('sequence_position',0)==0:assert info['calls'].get('0x8e4a',0)>0
    if case['coord']<8 and case.get('sequence_position',0)==0:assert info['calls'].get('0x43e38',0)>0

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/stage_event_initialization';folder.mkdir(parents=True,exist_ok=True);cases=build_cases(root,program);observer=Observer(program);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(program,case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1]);output,result,ports,info=observer.run(ram,regs);assert_evidence(case,ram,output,result,ports,info,regs)
        rf='native_%04d.bin'%index;pf='native_%04d.ports.bin'%index;(folder/rf).write_bytes(output);(folder/pf).write_bytes(ports)
        rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),result=result,input_ram_sha256=sha(ram),ram_file=rf,ram_sha256=sha(output),ports_file=pf,ports_sha256=sha(ports),port_count=len(ports)//9,**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
        if info['error']:break
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,cases=len(cases),completed_cases=sum(r['returned'] for r in rows),results=rows,failure=observer.error,program_code_modified=False,inventory_sha256=sha((root/'artifacts/stage_event_contexts.json').read_bytes()),scope='Continuous originale905c throughoriginal2a28/allcleanupcallees toRTS, no patches/calleecontextreset. Original3ef2 palette seed outsideentry; target/cleanup/alternateA5/liveRAM are controlledfixtures. ByteFFmayselectodd cursor; signedjumps preserved. All15regs andorderedwatchdog/PVC recorded, no MMIOreads. Native-only no callbackexecution/eventopcodegrammar/natural scheduling/CCR claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
