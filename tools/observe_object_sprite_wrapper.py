"""Unpatched 16ea4 tail-call submission and continuous native cda4 resumes."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program, disassemble_range
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from observe_sprite_submit_execution import (BASE, STACK, RETURN, WAIT_PC,
    fixture as sprite_fixture, assert_native_writes, branch_counts, external_writes)
from pack_stage_input import SOURCE_SHA256

KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(7))
ENTRY=0x16ea4
RANGES=((ENTRY,0x16ed2),(0xcd50,0xce02))

def sha(data):return hashlib.sha256(data).hexdigest()

def cases():
    result=[]
    def add(family,**values):
        case=dict(family=family,x=0,y=0x40,profile=1,deferred=False,producer=0,
            consumer=0x100,prepared=0x80,normal=0,count=0,offset=12,pending=False,
            flag=0,x_offset=0,y_offset=0,a6=0x102000,a5=0xffffffff)
        case.update(values);result.append(case)
    pairs=((0,0x40,0,0),(0xffff,0xffff,1,0x41),(0,0,0xffff,0xffff),
        (0x7fff,0x8000,1,0x8000),(0x8000,0x7fff,0x8000,1),
        (0x29f,0x2bf,0,0),(0xfea0,0x40,0,0),(1,1,0xffff,0xffff))
    for flag,pair in itertools.product((0,1,2,3,0x7c,0x81,0xfe,0xff),pairs):
        x,y,dx,dy=pair
        add('SWAP-WORD-wrap-LSR-X-highbits',x=x,y=y,x_offset=dx,y_offset=dy,flag=flag,
            a5=(0,0xffffffff,0x108002)[len(result)%3],a6=(0x102000,0x100000,0x10ffac)[len(result)%3])
    for deferred,kind,index in itertools.product((False,True),('normal','clip','full'),range(4)):
        producer=(0,0x1fc,0xfffe,0xffff)[index];nxt=(producer+2)&0x1fe
        add('queue-'+kind,deferred=deferred,producer=producer,
            consumer=nxt if kind=='full' else 0x100,
            prepared=nxt if kind=='full' else 0x80,
            normal=(0,2,0x200,0x8000)[index],count=(0,2,0x200,0xfffe)[index],
            x=0x2a0 if kind=='clip' else (0,0xffff,0x29f,0xfea0)[index],
            y=(0x40,0x2bf,0x40,0x2bf)[index],flag=(0,1,2,3)[index],
            x_offset=index&1,y_offset=(index>>1)&1)
    for deferred,index in itertools.product((False,True),range(4)):
        producer=(0,0x1fc,0xfffe,0xffff)[index];nxt=(producer+2)&0x1fe
        add('same-CPU-object-poison-wait-hold-ready',deferred=deferred,pending=True,
            producer=producer,consumer=nxt,prepared=(0,0x80,0x8000,0xffff)[index],
            normal=0x206,count=0x200,offset=(12,0xe00,0x80cc,0xfffe)[index],
            flag=(0,1,2,3)[index],x=0xffff,y=0x40,x_offset=index&1,y_offset=(index>>1)&1)
    assert len(result)==96
    return result

def fixture(case,index):
    ram,old=sprite_fixture(case)
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    for i in range(8):regs['d'+str(i)]=old[i]
    regs.update(a5=case['a5'],a6=case['a6'])
    regs['d2']=0xabcd1200|(index&255)
    at=case['a6']-BASE
    struct.pack_into('>I',ram,at+0x12,old[1])
    struct.pack_into('>H',ram,at+0x1e,old[5]&65535)
    struct.pack_into('>H',ram,at+0x42,case['x_offset'])
    struct.pack_into('>H',ram,at+0x46,case['y_offset'])
    ram[at+0x53]=case['flag']
    return bytes(ram),regs

def expected_prefix(ram,regs):
    expected=regs.copy();at=regs['a6']-BASE;flag=ram[at+0x53]
    x=((regs['d0']>>16)+int.from_bytes(ram[at+0x42:at+0x44],'big')-(flag&1))&65535
    y=((regs['d0']&65535)+int.from_bytes(ram[at+0x46:at+0x48],'big')-((flag>>1)&1))&65535
    expected.update(a5=0x108000,d3=0,d0=(x<<16)|y,
        d2=(regs['d2']&0xffffff00)|(flag>>2),d1=int.from_bytes(ram[at+0x12:at+0x16],'big'),
        d5=(regs['d5']&0xffff0000)|int.from_bytes(ram[at+0x1e:at+0x20],'big'))
    return expected

class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE])
        self.pcs=[];self.events=[];self.snapshots=[]
        def code(pc):
            self.pcs.append(pc)
            assert ENTRY<=pc<0x16ed2 or 0xcd50<=pc<0xce02,(pc,'unexpected code')
            if pc==0xcd58:self.snapshots.append(dict(pc=pc,registers=self.regs(),a7=self.cpu.get_reg('a7')))
            if pc==0xcd5c:assert self.cpu.get_reg('a0')==0xcd50,'unsupported callback'
            word=int.from_bytes(self.cpu.read(pc,2),'big')
            assert word!=0x4afc and not 0x4e40<=word<=0x4e4f,(pc,word)
        def write(pc,address,size,value):
            kind='ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK-4096<=address and address+size<=STACK+4 else None
            assert kind is not None,(pc,address,size,value)
            self.events.append(dict(pc=pc,address=address,size=size,value=value,kind=kind))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)
    def regs(self):return {key:self.cpu.get_reg(key) for key in KEYS}
    def prepare(self,ram,regs):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,ram);cpu.load(STACK-4096,b'\x5a'*4100)
        cpu.set_reg('sr',0x2000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in regs.items():cpu.set_reg(key,value)
        cpu.set_reg('pc',ENTRY)
    def mutate(self,writes):
        for item in writes:self.cpu.load(item['address'],bytes.fromhex(item['raw_hex']))
    def run(self,stop=RETURN,budget=2000):
        before=self.cpu.read(BASE,65536)
        self.pcs.clear();self.events.clear();self.snapshots.clear()
        native=self.cpu.run(budget,stop)
        assert native['status'] in ('sentinel','budget_exhausted'),native
        assert self.cpu.read(0,BASE)==self.program[:BASE]
        assert self.cpu.read(STACK,4)==RETURN.to_bytes(4,'big')
        lowest=min([e['address'] for e in self.events if e['kind']=='stack']+[STACK-4])
        # Callback JSR can leave stale bytes below SP between phases; the guard
        # below STACK-4 remains untouched in every phase of these tail-call paths.
        assert self.cpu.read(STACK-4096,lowest-(STACK-4096))==b'\x5a'*(lowest-(STACK-4096))
        replay=bytearray(before)
        for event in self.events:
            if event['kind']=='ram':
                at=event['address']-BASE;replay[at:at+event['size']]=event['value'].to_bytes(event['size'],'big')
        output=self.cpu.read(BASE,65536);assert bytes(replay)==output
        return native,output,self.regs(),self.pcs.copy(),self.events.copy(),self.snapshots.copy()

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    names=('tools/observe_object_sprite_wrapper.py','tools/observe_sprite_submit_execution.py',
        'tools/disassemble_program.py','tools/musashi_oracle.py','tools/observe_scene_motion_pair.py')
    inputs=[dict(file=name,sha256=sha((root/name).read_bytes())) for name in names]
    oracle=oracle_provenance(root);folder=root/'artifacts/object_sprite_wrapper';folder.mkdir(parents=True,exist_ok=True)
    instructions=[]
    for start,end in RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions),indent=2)+'\n')
    observer=Observer(program);rows=[]
    for index,case in enumerate(cases()):
        ram,regs=fixture(case,index);observer.prepare(ram,regs)
        native,output,values,pcs,events,snapshots=observer.run(WAIT_PC if case['pending'] else RETURN)
        assert len(snapshots)==1 and snapshots[0]['registers']==expected_prefix(ram,regs)
        assert snapshots[0]['a7']==STACK
        phases=[]
        def save(phase,before,incoming,native,output,values,pcs,events,snapshots,status,changes):
            name='native_%04d_%s.bin'%(index,phase);(folder/name).write_bytes(output)
            phases.append(dict(phase=phase,input_ram_sha256=sha(before),incoming=incoming,result=values,
                waiting=status==3,status=status,native=native,final_a7=observer.cpu.get_reg('a7'),
                ram_file=name,ram_sha256=sha(output),pcs=pcs,RAM_writes=[e for e in events if e['kind']=='ram'],
                ordered_writes=events,boundary_snapshots=snapshots,external_RAM_writes=changes,mmio_writes=0))
        if case['pending']:
            assert native['status']=='sentinel' and native['pc']==WAIT_PC and observer.cpu.get_reg('a7')==STACK
            status=3
            assert values['d4']&65535==case['prepared'] and values['d6']&65535==((case['producer']+2)&0x1fe)
        else:
            assert native['status']=='sentinel' and native['pc']==RETURN and observer.cpu.get_reg('a7')==STACK+4
            status=0 if 0xcdaa in pcs else 2 if 0xcd82 in pcs else 1
        assert_native_writes(status,[e for e in events if e['kind']=='ram'],case['deferred'])
        save('begin',ram,regs,native,output,values,pcs,events,snapshots,status,[])
        if case['pending']:
            captured=values.copy();changes=external_writes()
            for offset,raw in ((0x53,'ff'),(0x42,'1234'),(0x46,'abcd'),(0x12,'deadbeef'),(0x1e,'2468')):
                changes.append(dict(address=case['a6']+offset,raw_hex=raw,purpose='Poison object prefix input after actual wait'))
            observer.mutate(changes);before=observer.cpu.read(BASE,65536)
            native,output,values,pcs,events,snapshots=observer.run(RETURN,2)
            assert native['status']=='budget_exhausted' and native['pc']==WAIT_PC and pcs==[WAIT_PC,0xcda8]
            assert values==captured and output==before and not events and not snapshots and observer.cpu.get_reg('a7')==STACK
            save('hold',before,captured,native,output,values,pcs,events,snapshots,3,changes)
            changes=[dict(address=0x108d34,raw_hex=(captured['d4']&65535).to_bytes(2,'big').hex(),purpose='Consumer reaches captured prepared target')]
            observer.mutate(changes);before=observer.cpu.read(BASE,65536)
            native,output,values,pcs,events,snapshots=observer.run()
            assert native['status']=='sentinel' and native['pc']==RETURN and observer.cpu.get_reg('a7')==STACK+4
            assert not snapshots and not any(ENTRY<=pc<0x16ed2 or pc in (0xcd58,0xcd5c,0xcd82,0xcd98) for pc in pcs)
            writes=[e for e in events if e['kind']=='ram'];assert_native_writes(0,writes,case['deferred'])
            assert writes[0]['value']==captured['d6']&65535
            assert values['a5']==0x108000 and values['a6']==captured['a6']
            save('ready',before,captured,native,output,values,pcs,events,snapshots,0,changes)
        rows.append(dict(case_index=index,fixture=case,phases=phases))
    assert all(sha((root/item['file']).read_bytes())==item['sha256'] for item in inputs)
    assert oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,entry=ENTRY,cases=len(rows),
        phases=sum(len(row['phases']) for row in rows),pending_chains=sum(row['fixture']['pending'] for row in rows),
        counts_by_status=dict(sorted(collections.Counter(p['status'] for row in rows for p in row['phases']).items())),
        branch_successor_counts=branch_counts(rows),results=rows,program_code_modified=False,failure=None,
        scope='Unpatched original 16ea4 tail-JMP cd58/default cd50, full 64KiB RAM and 15 general registers. '
        'Approved prefix conversion is asserted only at native cd58 boundary; final outcomes and writes are native. '
        'Actual cda4 wait/hold/ready reuse the same CPU without reset or register changes. Object fields and queue/callback poisoning are recorded host writes outside hooks. '
        'SR is set before A7 and never read or modified in hooks. Native RAM/stack writes are traced and RAM replayed; immutable program and stack guard checked. '
        'No C++ comparison, arbitrary callback, natural scheduler/IRQ, physical mirror or full CCR claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=report['pending_chains'],counts_by_status=report['counts_by_status'],sha256=sha(path.read_bytes()))))

if __name__=='__main__':main()
