"""Original uninterrupted cue-control calls in pinned Musashi M68000."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from pack_stage_cue_control import build, SOURCE_SHA256
BASE,STACK,RETURN=0x100000,0x1feffc,0xff000
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
ENTRIES=(0xe89fa,0xe8a1c,0xe8ad0,0xe8af4,0x2986)
BRANCHES=(0xe89fe,0xe8a20,0xe8ad8,0xe8ae4,0xe8b00,0xe8b0e,0x28ba,0x28c2,0x28d6)
def sha(data):return hashlib.sha256(data).hexdigest()
def provenance(root):
    files,manifest=build(root);folder=root/'extracted/runtime/stage_cue_control'
    for name,data in files.items():assert (folder/name).read_bytes()==data
    paths=['build/step_stage_cue_control','engine/src/stage_cue_control.cpp','engine/include/ms5/stage_cue_control.h','engine/tools/step_stage_cue_control.cpp','engine/src/object_allocation.cpp','engine/include/ms5/object_allocation.h','engine/src/fixed_data_resource.cpp','tools/pack_stage_cue_control.py','tools/observe_stage_cue_control.py','tools/verify_stage_cue_control.py']
    paths += [str((folder/name).relative_to(root)) for name in files]
    return [dict(file=p,sha256=sha((root/p).read_bytes())) for p in paths]
def build_cases():
    cases=[]
    def add(family,entry,**kw):
        c=dict(family=family,entry=entry,profile=1,carry=0,pointer=0x106000,phase=0,flags=0,x=1,y=2,cx=0,cy=0,gates=[0,1,0x7fff,0x8000,0xfffe,0xffff],count=4,request=0,callback=0x12345679,parent=0x100200,node=0x100400,successor=0x100800,original=0x106100,depth=0,source_byte=0x5a);c.update(kw);cases.append(c)
    for entry,pointer,carry in itertools.product(ENTRIES[:2],(0,1,0x100000,0x106001,0x80000000,0xffffffff),range(2)):add('setter-null-and-opaque-full-pointer',entry,pointer=pointer,carry=carry)
    for pointer in (0,0xe89ec):
        for phase in (0,1,0x7fff,0x8000,0xfffe):add('stream-null-or-original-default',0xe8ad0,pointer=pointer,phase=phase,carry=phase%2)
    for phase,gates,profile in itertools.product((0,1,2,0x7ffe,0x7fff,0x8000,0xfffd,0xfffe),([0,1,0x7fff,0x8000,0xfffe,0xffff],[0,0,0,1,1,0xffff],[0,8,3,9,2,0xffff]),range(2)):add('stream-unsigned-multiadvance-equality',0xe8ad0,phase=phase,gates=gates,profile=profile,carry=profile)
    for pointer,phase in ((0x10de1e,0),(0x10de1e,16),(0x10de22,0),(0x10de22,0xfffe)):add('stream-live-pointer-publication-overlap',0xe8ad0,pointer=pointer,phase=phase,gates=[0,0xffff,0xffff])
    values=(0,1,0x7fff,0x8000,0xffff)
    for flags,x,camera,profile in itertools.product((0,1,2,3,0xfc,0xff),values,values,range(2)):add('cue-flags-WORD-wrap-highwords',0xe8af4,flags=flags,x=x,y=x^0xffff,cx=camera,cy=camera^0xffff,profile=profile,carry=profile)
    for pointer in (0xe89e4,0x10fffa,0x10d3b8):add('cue-default-edge-and-live-camera-overlap',0xe8af4,pointer=pointer,flags=3,cx=0xffff,cy=0x8000)
    for count,request,callback,carry in itertools.product((0,1,4,0xffff),(0,1,3,4,0xffff),(0,1,0xffffffff),range(2)):add('allocator-threshold-null-callback',0x2986,count=count,request=request,callback=callback,carry=carry)
    for depth,original in itertools.product((0,0x7fff,0xffff),(0x106100,0x106101,0x100200,0x100400,0x104c32,0x104c36,0x1003a6,0x1003a7,0x100396)):add('allocator-original-parent-live-byte-alias',0x2986,depth=depth,original=original)
    for parent,node,successor in ((0x100200,0x100200,0x100800),(0x100200,0x100800,0x100800),(0x100200,0x100400,0x100200),(0x100200,0x104c90,0x100800),(0x10ff94,0x100400,0x100800),(0x100200,0x10ff94,0x100800),(0x100200,0x100400,0x10fff8)):add('allocator-live-list-alias-and-RAM-edge',0x2986,parent=parent,node=node,successor=successor)
    for name,entry,kw in (('allocation',0x2986,{}),('stream',0xe8ad0,dict(gates=[0,1,2,3,4,0xffff])),('cue',0xe8af4,dict(flags=3,cx=0xffff,cy=1))):
        for step in range(4):add('actual-CLI-output-chain',entry,sequence=name,sequence_position=step,**kw)
    assert len(cases)==555
    return cases

def fixture(c):
    ram=bytearray(hashlib.shake_256(b'stage-cue-control'+bytes([c['profile']])).digest(65536));regs=[0]*14 if not c['profile'] else [(0xabcdef01+i*0x1020304)&0xffffffff for i in range(14)]
    regs[8]=c['pointer'];regs[13]=c['original'];struct.pack_into('>HH',ram,0xd3bc,c['cx'],0);struct.pack_into('>H',ram,0xd3c0,c['cy']);struct.pack_into('>H',ram,0xd418,c['phase'])
    if c['entry']==0xe8ad0:
        if BASE<=c['pointer']<BASE+65536:
            for i,gate in enumerate(c['gates']):struct.pack_into('>H',ram,c['pointer']-BASE+12*i,gate)
        struct.pack_into('>I',ram,0xde2a,c['pointer'])
    if c['entry']==0xe8af4 and BASE<=c['pointer']<=BASE+65531:
        at=c['pointer']-BASE;struct.pack_into('>HHB',ram,at,c['x'],c['y'],c['flags'])
    if c['entry']==0x2986:
        regs[0]=(regs[0]&0xffff0000)|c['request'];regs[8]=c['callback'];regs[9]=c['parent']
        struct.pack_into('>IH',ram,0x4c9c,c['node'],c['count'])
        for i in range(4):
            node=c['node']+i*0x100
            if node+12<=BASE+65536:struct.pack_into('>I',ram,node-BASE+8,node+0x100)
        p=c['parent']-BASE;struct.pack_into('>I',ram,p+8,c['successor']);struct.pack_into('>H',ram,p+0x10,c['depth']);ram[p+0x6a]=0xa5
        struct.pack_into('>I',ram,c['successor']-BASE+4,c['parent'])
        # Don't overwrite fields deliberately aliased by original-A6.
        address=c['original']+0x6a
        if address not in (c['parent']+0x6a,c['node']+0x6a,0x104c9c,0x104ca0,c['node']+0x10,c['node']+0x11,c['node']):ram[address-BASE]=c['source_byte']
    return ram,regs,c['carry']
def prepare(c,prior):
    if prior is None:return (*fixture(c),[])
    ram,regs,carry=bytearray(prior[0]),list(prior[1]),prior[2];changes=[]
    if c['sequence']=='allocation':regs[8]=c['callback'];regs[9]=c['parent'];changes=[dict(register='a0',value=regs[8]),dict(register='a1',value=regs[9])]
    if c['sequence']=='stream':struct.pack_into('>H',ram,0xd418,c['sequence_position']);changes=[dict(address=0x10d418,size=2,value=c['sequence_position'])]
    return ram,regs,carry,changes
class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE]);self.pending=None;self.branches=[];self.calls=collections.Counter();self.writes=[];self.copies=[];self.gates=[]
        def code(pc):
            cpu=self.cpu
            if self.pending is not None:self.branches.append(dict(pc=self.pending,next_pc=pc));self.pending=None
            if pc in BRANCHES:self.pending=pc
            if pc in ENTRIES+(0x28ae,0x2908,0x2912,0x2992):self.calls[hex(pc)]+=1
            if pc==0xe8ae0:self.gates.append(dict(address=cpu.get_reg('a0')+12,value=int.from_bytes(cpu.read(cpu.get_reg('a0')+12,2),'big')))
            if pc in (0x2902,0x2992):self.copies.append(dict(pc=pc,source=cpu.get_reg('a6')+0x6a,destination=cpu.get_reg('a0')+0x6a,value=cpu.read(cpu.get_reg('a6')+0x6a,1)[0]))
            opcode=int.from_bytes(cpu.read(pc,2),'big');assert opcode!=0x4afc and not 0x4e40<=opcode<=0x4e4f,(pc,opcode)
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(pc,address,size)
            if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)
    def run(self,c,ram,regs,carry):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000|carry);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for k,v in zip(KEYS,regs):cpu.set_reg(k,v)
        self.pending=None;self.branches.clear();self.calls.clear();self.writes.clear();self.copies.clear();self.gates.clear();cpu.set_reg('pc',c['entry']);status=cpu.run(20000,RETURN)
        assert status['status']=='sentinel' and cpu.get_reg('a7')==STACK+4,status
        assert cpu.read(0,BASE)==self.program[:BASE]
        result={k:cpu.get_reg(k) for k in KEYS};result['allocation_carry']=bool(cpu.get_reg('sr')&1) if c['entry']==0x2986 else bool(carry)
        return cpu.read(BASE,65536),result,dict(returned=True,final_pc=RETURN,final_a7=STACK+4,instructions=status['instructions'],RAM_writes=self.writes.copy(),branch_successors=self.branches.copy(),calls=dict(self.calls),byte_copies=self.copies.copy(),stream_gate_reads=self.gates.copy(),mmio_writes=0)
def assert_evidence(c,ram,regs,carry,out,result,info):
    assert result['a6']==regs[13]
    if c['entry']!=0x2986:assert result['allocation_carry']==bool(carry)
    if c['entry']==0x2986:
        copies=info['byte_copies'];assert copies[-1]['pc']==0x2992 and copies[-1]['source']==regs[13]+0x6a and copies[-1]['destination']==result['a0']+0x6a
        assert out[copies[-1]['destination']-BASE]==copies[-1]['value']
        assert result['allocation_carry']==bool(info['calls'].get('0x2908'))
        assert len(copies)==(2 if result['allocation_carry'] else 1)
    if c['entry']==0xe8ad0:
        if not int.from_bytes(ram[0xde2a:0xde2e],'big'):assert not info['stream_gate_reads'] and out==ram
        else:assert info['stream_gate_reads'][-1]['value']>(result['d0']&65535) and int.from_bytes(out[0xde2a:0xde2e],'big')==result['a0']
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;inputs,oracle=provenance(root),oracle_provenance(root);folder=root/'artifacts/stage_cue_control';folder.mkdir(parents=True,exist_ok=True)
    cases=build_cases();observer=Observer(program);rows=[];previous={};branches=collections.defaultdict(collections.Counter)
    for i,c in enumerate(cases):
        prior=previous.get(c.get('sequence')) if c.get('sequence_position',0)>0 else None;ram,regs,carry,changes=prepare(c,prior);out,result,info=observer.run(c,ram,regs,carry);assert_evidence(c,ram,regs,carry,out,result,info)
        for b in info['branch_successors']:branches[b['pc']][b['next_pc']]+=1
        if 'sequence'in c:previous[c['sequence']]=(out,[result[k] for k in KEYS],result['allocation_carry'])
        name='native_%04d.bin'%i;(folder/name).write_bytes(out);rows.append(dict(case_index=i,fixture=c,incoming=dict(zip(KEYS,regs)),input_carry=bool(carry),host_updates=changes,input_ram_sha256=sha(ram),result=result,ram_file=name,ram_sha256=sha(out),**info))
    assert all(len(branches[p])==2 for p in BRANCHES if p!=0x28d6),dict(branches)
    assert set(branches[0x28d6])=={0x28da} # null freehead not a supported positive allocation graph
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(cases),completed_cases=len(rows),failure=None,results=rows,program_code_modified=False,branch_successor_counts={hex(p):{hex(n):v for n,v in b.items()} for p,b in branches.items()},scope='Original five entrypoints continuously to RTS, full64KiB RAM/14 registers. Only2986 exposes actual final native CCR.C; other four preserve separate incoming allocation_carry API value, without claiming native CCR equality. No ROM patches, callee stubs, in-call resets, MMIO or hook SR reads. Controlled RAM streams have no terminal interpretation. Native-null freehead is excluded; failed C++ reads/allocations checked separately.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
