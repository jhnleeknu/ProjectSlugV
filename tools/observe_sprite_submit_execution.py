"""Original cd58 snapshots, ordered native writes and same-CPU cda4 resumes."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from pack_stage_input import SOURCE_SHA256

BASE,STACK,RETURN,WAIT_PC = 0x100000,0x1feffc,0xff000,0xcda4
KEYS = tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
NORMAL_INDICES = (0,2,0x1fe,0x200,0x202,0x204,0x206,0x8000,0x8002,0xfffe)
DEFERRED_INDICES = (0,2,0x1fe,0x200,0x8000,0x8002,0xfffe,0x70b0)
BRANCHES = (0xcd66,0xcd78,0xcd94,0xcda0,0xcda8,0xcdb2)
OFFSETS = (0,2,12,0xc02,0xe00,0xe06,0x121a,0x121e,0x80cc,0x80ce,0xfffe,0x7ffe)


def sha(data):return hashlib.sha256(data).hexdigest()


def provenance(root):
    names=('build/execute_sprite_submit','engine/src/sprite_submit_execution.cpp',
        'engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h','engine/tools/execute_sprite_submit.cpp',
        'tools/observe_sprite_submit_execution.py','tools/verify_sprite_submit_execution.py',
        'tools/disassemble_program.py')
    return [dict(file=n,sha256=sha((root/n).read_bytes())) for n in names]


def build_cases():
    cases=[]
    def add(family,**kw):
        c=dict(family=family,x=0,y=0x40,profile=1,deferred=False,producer=0,
            consumer=0x100,prepared=0x80,normal=0,count=0,offset=12,pending=False)
        c.update(kw);cases.append(c)
    for x,y,profile in itertools.product((0,1,0x29f,0x2a0,0xfea0,0xfe9f,0xffff,0x8000,0x7fff),
            (0,0x3f,0x40,0x2bf,0x2c0,0xffff),range(2)):
        add('clip-both-dimensions-WORD-wrap-highbits',x=x,y=y,profile=profile)
    for deferred,index,offset,profile in itertools.product((False,True),NORMAL_INDICES,OFFSETS,range(2)):
        if deferred and index not in DEFERRED_INDICES:continue
        add('accepted-wide-signed-index-record-alias-WORD-wrap',deferred=deferred,
            normal=index,count=index,offset=offset,profile=profile,
            x=(0xfea0,0x29f)[profile],y=(0x40,0x2bf)[profile])
    # Deferred last valid destination is not a normal signed-index destination.
    for offset,profile in itertools.product(OFFSETS,range(2)):
        add('deferred-last-valid-RAM-WORD',deferred=True,count=0x70b0,offset=offset,profile=profile)
    for producer,profile in itertools.product((0,1,0x1fc,0x1fe,0x7fff,0x8000,0xfffe,0xffff),range(2)):
        nxt=(producer+2)&0x1fe
        add('full-preserves-other-cursors-with-native-register-effects',producer=producer,
            consumer=nxt,prepared=nxt,normal=0xffff,count=0xffff,profile=profile)
    for deferred,producer,prepared,profile in itertools.product((False,True),(0,0x1fc,0xfffe),(0,2,0x1fe,0x7fff,0x8000,0xffff),range(2)):
        nxt=(producer+2)&0x1fe
        if prepared==nxt:continue
        add('actual-begin-wait-hold-consumer-ready-chain',deferred=deferred,producer=producer,
            consumer=nxt,prepared=prepared,profile=profile,pending=True,
            normal=(0x206,0x8000)[profile],count=(0x200,0xfffe)[profile],
            offset=(0xe00,0x80cc)[profile],x=(0xffff,0x29f)[profile],y=(0x40,0x2bf)[profile])
    return cases


def fixture(case):
    ram=bytearray(hashlib.shake_256(b'sprite-submit-execution'+bytes([case['profile']])).digest(65536))
    regs=[0]*14 if case['profile']==0 else [(0x89abcdef+i*0x1020304)&0xffffffff for i in range(14)]
    regs[0]=(case['x']<<16)|case['y']
    regs[1]=(regs[1]&~0x40)|(0x40 if case['deferred'] else 0)
    regs[5]=(0xffff0000|(0x8000 if case['profile']==0 else 0xffff))
    regs[7]=(0x12345678,0xffffffff)[case['profile']]
    struct.pack_into('>I',ram,0x9152,0xcd50)
    for i in range(256):struct.pack_into('>H',ram,0x8b34+i*2,i*12)
    struct.pack_into('>4H',ram,0x8d34,case['consumer'],case['prepared'],case['normal'],case['producer'])
    struct.pack_into('>H',ram,0x914e,case['count'])
    nxt=(case['producer']+2)&0x1fe
    struct.pack_into('>H',ram,0x8b34+nxt,case['offset'])
    return ram,regs


class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE])
        self.pcs=[];self.writes=[]
        def code(pc):
            self.pcs.append(pc)
            if pc==0xcd5c:assert self.cpu.get_reg('a0')==0xcd50,'Unsupported callback would execute'
            word=int.from_bytes(self.cpu.read(pc,2),'big')
            assert word!=0x4afc and not 0x4e40<=word<=0x4e4f,(pc,word)
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(pc,address,size,value)
            if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)
    def prepare(self,ram,regs):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000)
        cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in zip(KEYS,regs):cpu.set_reg(key,value)
        cpu.set_reg('pc',0xcd58)
    def run(self,stop=RETURN,budget=2000):
        self.pcs.clear();self.writes.clear()
        result=self.cpu.run(budget,stop)
        assert self.cpu.read(0,BASE)==self.program[:BASE]
        assert result['status'] in ('sentinel','budget_exhausted'),result
        return result,self.cpu.read(BASE,65536),{k:self.cpu.get_reg(k) for k in KEYS},self.pcs.copy(),self.writes.copy()
    def mutate(self,writes):
        for item in writes:self.cpu.load(item['address'],bytes.fromhex(item['raw_hex']))


def assert_native_writes(status,writes,deferred):
    if status!=0:
        assert not writes
        return
    assert [r['pc'] for r in writes]==([0xcdaa,0xcdd8,0xcde0] if deferred else [0xcdaa,0xcdbe,0xcdc8])+[0xcdfc]*3,writes
    assert [r['size'] for r in writes]==[2,2,2,4,4,4],writes
    assert writes[0]['address']==0x108d3a
    if deferred:assert writes[1]['address']==0x10914e
    else:assert writes[2]['address']==0x108d38
    pool=writes[3]['address']
    assert [r['address'] for r in writes[3:]]==[pool,pool+4,pool+8]


def branch_counts(rows):
    counts=collections.defaultdict(collections.Counter)
    for row in rows:
        for phase in row['phases']:
            pcs=phase['pcs']+[phase['native']['pc']]
            for at,following in zip(pcs,pcs[1:]):
                if at in BRANCHES:counts[at][following]+=1
    assert set(counts)==set(BRANCHES) and all(len(counts[at])==2 for at in BRANCHES)
    return {hex(k):{hex(a):n for a,n in sorted(v.items())} for k,v in sorted(counts.items())}


def external_writes():
    return [dict(address=0x109152,raw_hex='00106000',purpose='Callback pointer changed while waiting; resume must not invoke it'),
        dict(address=0x108d36,raw_hex='dead',purpose='Prepared cursor changed; captured D4 remains authoritative'),
        dict(address=0x108d3a,raw_hex='beef',purpose='Producer cursor changed; captured D6 remains authoritative')]


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    inputs,oracle=provenance(root),oracle_provenance(root.resolve())
    folder=root/'artifacts/sprite_submit_execution';folder.mkdir(parents=True,exist_ok=True)
    observer=Observer(program);rows=[];cases=build_cases()
    for index,case in enumerate(cases):
        ram,regs=fixture(case);observer.prepare(ram,regs)
        result,output,values,pcs,writes=observer.run(WAIT_PC if case['pending'] else RETURN)
        if case['pending']:
            assert result['status']=='sentinel' and result['pc']==WAIT_PC and observer.cpu.get_reg('a7')==STACK
            status,waiting=3,True
            assert values['d4']&65535==case['prepared'] and values['d6']&65535==((case['producer']+2)&0x1fe)
        else:
            assert result['status']=='sentinel' and result['pc']==RETURN and observer.cpu.get_reg('a7')==STACK+4
            status,waiting=(0 if 0xcdaa in pcs else 2 if 0xcd82 in pcs else 1),False
        assert_native_writes(status,writes,case['deferred'])
        name='native_%04d_begin.bin'%index;(folder/name).write_bytes(output)
        phases=[dict(phase='begin',waiting_in=False,status_in=2,input_ram_sha256=sha(ram),incoming=dict(zip(KEYS,regs)),
            result=values,waiting=waiting,status=status,ram_file=name,ram_sha256=sha(output),native=result,
            final_a7=observer.cpu.get_reg('a7'),pcs=pcs,RAM_writes=writes,external_RAM_writes=[],mmio_writes=0)]
        if case['pending']:
            captured=values.copy();changes=external_writes();observer.mutate(changes)
            hold_input=observer.cpu.read(BASE,65536)
            held,holdout,holdregs,holdpcs,holdwrites=observer.run(RETURN,2)
            assert held['status']=='budget_exhausted' and held['pc']==WAIT_PC and holdpcs==[0xcda4,0xcda8]
            assert holdregs==captured and holdout==hold_input and not holdwrites and observer.cpu.get_reg('a7')==STACK
            name='native_%04d_hold.bin'%index;(folder/name).write_bytes(holdout)
            phases.append(dict(phase='hold',waiting_in=True,status_in=3,input_ram_sha256=sha(hold_input),incoming=captured,
                result=holdregs,waiting=True,status=3,ram_file=name,ram_sha256=sha(holdout),native=held,
                final_a7=STACK,pcs=holdpcs,RAM_writes=holdwrites,external_RAM_writes=changes,mmio_writes=0))
            ready=[dict(address=0x108d34,raw_hex=(captured['d4']&65535).to_bytes(2,'big').hex(),
                purpose='Consumer reaches original captured D4 target')]
            observer.mutate(ready);ready_input=observer.cpu.read(BASE,65536)
            done,readyout,readyregs,readypcs,readywrites=observer.run()
            assert done['status']=='sentinel' and done['pc']==RETURN and observer.cpu.get_reg('a7')==STACK+4
            assert 0xcd58 not in readypcs and 0xcd5c not in readypcs and 0xcd82 not in readypcs and 0xcd98 not in readypcs
            assert_native_writes(0,readywrites,case['deferred'])
            assert readywrites[0]['value']==captured['d6']&65535
            name='native_%04d_ready.bin'%index;(folder/name).write_bytes(readyout)
            phases.append(dict(phase='ready',waiting_in=True,status_in=3,input_ram_sha256=sha(ready_input),incoming=holdregs,
                result=readyregs,waiting=False,status=0,ram_file=name,ram_sha256=sha(readyout),native=done,
                final_a7=STACK+4,pcs=readypcs,RAM_writes=readywrites,external_RAM_writes=ready,mmio_writes=0))
        rows.append(dict(case_index=index,fixture=case,phases=phases))
    assert provenance(root)==inputs and oracle_provenance(root.resolve())==oracle
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(cases),phases=sum(len(r['phases']) for r in rows),
        pending_chains=sum(c['pending'] for c in cases),branch_successor_counts=branch_counts(rows),results=rows,program_code_modified=False,failure=None,
        counts_by_status=dict(sorted(collections.Counter(p['status'] for r in rows for p in r['phases']).items())),
        scope='Original unmodified cd58/defaultcd50 continuously executed to RTS or firstcda4 boundary. Actual begin-wait-hold-ready chains reuse the SAME nativeCPU without reset or register writes. '
              'Hold executes exactly CMP+BNE for2instructions back to cda4. Only explicitly recorded consumer/callback/prepared/producer RAM writes occur between phases, outside hooks. '
              'Full64KiB RAM/14 general registers including A6 and ordered native RAM writes retained. No SR read in hooks, flags patched, ROM changes or unsupported callbacks executed. '
              'Wide signed normal/deferred cursors and record offsets are valid source-computed begin paths, not typed queue invariants. '
              'Native write sequence is source-order evidence; C++ finalRAM/alias comparisons do not expose an independent C++write trace. No natural scheduler/cycle/reachability claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),phases=report['phases'],pending_chains=report['pending_chains'],counts_by_status=report['counts_by_status'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
