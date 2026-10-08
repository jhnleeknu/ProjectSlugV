"""Unpatched object cleanup, traversal and nested wrappers on coherent shared stack.

Controlled incoming fixtures; coherent16work-RAM mirrors and live shared stack.
No SR reads, ROM patches, stubs or register injection after execution begins.
"""
import collections
import copy
import ctypes
import hashlib
import inspect
import json
from pathlib import Path
import struct
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_screen as screen_native
import observe_animation_machine_exit as exit_native
import observe_animation_machine_transition as transition
import observe_animation_machine_callers as callers
import observe_animation_machine_activation as activation
import observe_stage_readiness as readiness
import observe_stage_hud_counter as hud
import observe_animation_machine_hud as hud_machine
import observe_animation_machine_readiness as readiness_machine
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_cleanup_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=screen_native.RANGES+((0x271c,0x2790),(0x287e,0x288c),(0x299c,0x2a00),(0x2a0a,0x2a24),(0x2a28,0x2aac),(0x8ff4,0x9038),(0x8e4a,0x8e82),(0x8eb6,0x8ebe),(0xc3dc,0xc402),(0x43dcc,0x43e04),(0x43e38,0x43ea4),(0x46eec,0x46f2e),(0x4aa06,0x4aa30),(0xe90ca,0xe90d8),(0x477c2,0x477e4),(0x8bbc,0x8bc2),(0x3dce,0x3de6),(0x47fe4,0x47fe8))
BOUNDARIES=screen_native.BOUNDARIES+(0x299c,0x29ac,0x29c0,0x29c4,0x29c8,0x29ce,0x29de,0x29ec,0x29fe,0x2a0a,0x2a16,0x2a1e,0x2a28,0x2a40,0x2a42,0x2a44,0x2a48,0x2a5c,0x2a60,0x2a80,0x2a84,0x2aa4,0x2aa8,0x271c,0x2782,0x8ff4,0x8e4a,0xc3fa,0x46ef4,0x43e38,0x43e70,0x43e7a,0x43dcc,0x43dda,0xc3dc,0x4aa06,0xe90ca,0x46eec,0x477c2,0x477c8,0x477d4,0x477e2,0x8bbc,0x3dce,0x47fe4)
sha,put=extended.sha,extended.put
BRANCHES={0x29c4:(0x29c8,0x29fe),0x2a16:(0x2a1e,0x2a1a)}

class Observer:
    def __init__(self,program,continuous=False):self.program=program;self.cpu=None;self.backing=None;self.continuous=continuous;self.seen=set()
    def regs(self):return {key:self.cpu.reg_read(REGS[key]) for key in shared.isolated.REG_NAMES+('a7','pc')}
    def prepare(self,fx):
        self.stop_pc=fx['stop_pc'];self.checkpoints=tuple(fx['checkpoints']);self.expected_a7=fx['expected_final_a7']
        self.backing=(ctypes.c_ubyte*SIZE).from_buffer_copy(fx['ram'])
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._ram_backing=self.backing
        c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        c.mem_map(0,RAM,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(0,self.program[:RAM])
        for i in range(16):c.mem_map_ptr(RAM+i*SIZE,SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        c.mem_map(0x200000,0xfe000,unicorn.UC_PROT_READ);c.mem_write(0x200000,self.program[0x200000:0x2fe000])
        c.mem_map(PVC,8192,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(PVC,fx['pvc'])
        c.mem_map(0x300000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0x3c0000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0xd00000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(EXTERNAL,bytes([fx['external']]))
        self.cpu=c;self.bank=0x200000;self.ff8=0xa0;self.ff9=0x1000
        self.boundary_set=set(BOUNDARIES)
        allowed=set()
        for lo,hi in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(self.program,lo,hi-lo,lo))
        def stop(problem,**fields):self.guard=dict(problem=problem,pc=self.pc,**fields);c.emu_stop()
        def code(cpu,pc,size,user):
            self.pc=pc;self.pcs.append(pc)
            if pc==self.stop_pc:cpu.emu_stop();return
            if pc in self.checkpoints and pc not in self.seen:
                self.seen.add(pc)
                self.snapshots.append(dict(registers=self.regs(),ram=bytes(self.backing),pvc=bytes(c.mem_read(PVC,8192))))
                if not self.continuous:cpu.emu_stop();return
            if pc not in allowed:stop('unsupported_code_target',target=pc);return
            opcode=int.from_bytes(cpu.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:stop('unsupported_TRAP',opcode=opcode);return
            if pc==0xcd5c and cpu.reg_read(REGS['a0'])!=0xcd50:stop('unsupported_sprite_callback');return
            if pc in (0x4a43c,0x4a352) and cpu.reg_read(REGS['a1']) not in (0x3679e,0x2b3e8,0x2b3fa,0x47672):stop('unsupported_animation_callback');return
            if pc in self.boundary_set:
                self.boundaries.append(dict(pc=pc,registers=self.regs(),stack_address=S-40,stack=bytes(cpu.mem_read(S-40,44)).hex()))
            if pc in (0xcda4,0x3aea):
                if pc==0xcda4:
                    waiting=int.from_bytes(cpu.mem_read((cpu.reg_read(REGS['a5'])+0xd34)&0xffffffff,2),'big')!=(cpu.reg_read(REGS['d4'])&65535)
                else:waiting=int.from_bytes(cpu.mem_read((cpu.reg_read(REGS['a5'])-0x328c)&0xffffffff,2),'big')==(cpu.reg_read(REGS['d1'])&65535)
                if waiting:
                    self.visits+=1
                    if self.visits==2:cpu.emu_stop();return
                else:self.visits=0
        def event(kind,address,size,value=None):
            if RAM<=address and address+size<=0x200000:region='ram'
            elif address<RAM and address+size<=RAM:region='fixed'
            elif 0x200000<=address and address+size<=PVC:region='bank'
            elif PVC<=address and address+size<=0x300000:region='pvc'
            elif address==EXTERNAL and size==1:region='external'
            elif (address==0x3c0000 and size in (2,4) or address==0x3c0004 and size==2) and kind=='write':region='video'
            elif address==0x300001 and size==1 and kind=='write':region='watchdog'
            else:stop('unsupported_data_device',address=address,size=size);return
            if kind=='write' and region not in ('ram','pvc','video','watchdog'):stop('unsupported_write',address=address,size=size);return
            if region=='pvc' and (kind!='write' or size!=2 or address not in (0x2ffff0,0x2ffff2)):
                stop('unsupported_PVC_read_or_write',address=address,size=size);return
            if region=='bank' and self.bank!=0x200000:stop('bank_mapping_requires_different_bank',bank=self.bank);return
            if size>1 and address&1:stop('unsupported_odd_data_access',address=address,size=size);return
            before=bytes(c.mem_read(address,size));data=before if kind=='read' else (value&((1<<(size*8))-1)).to_bytes(size,'big')
            item=dict(pc=self.pc,hook_pc=c.reg_read(REGS['pc']),access=kind,address=address,size=size,bytes=data.hex(),before=before.hex(),region=region)
            if region=='pvc':
                v=int.from_bytes(data,'big')
                if address==0x2ffff0:self.ff8=v
                else:self.ff9=v
                self.bank,self.ff8,self.ff9=pvc_bank_update(self.ff8,self.ff9)
                item.update(bank_after=self.bank,ff8_after=self.ff8,ff9_after=self.ff9)
            self.events.append(item)
        def read(cpu,access,address,size,value,user):event('read',address,size)
        def write(cpu,access,address,size,value,user):event('write',address,size,value)
        def bad(cpu,access,address,size,value,user):stop('unmapped_or_protected',address=address,size=size);return False
        def interrupt(cpu,number,user):stop('CPU_exception',number=number)
        for hook,callback in ((unicorn.UC_HOOK_CODE,code),(unicorn.UC_HOOK_MEM_READ,read),(unicorn.UC_HOOK_MEM_WRITE,write),(unicorn.UC_HOOK_MEM_INVALID,bad),(unicorn.UC_HOOK_INTR,interrupt)):c.hook_add(hook,callback)
        c.reg_write(REGS['sr'],0x2000);c.reg_write(REGS['a7'],fx['initial_a7'])
        for key in shared.isolated.REG_NAMES:c.reg_write(REGS[key],fx['regs'][key])
        c.reg_write(REGS['pc'],fx['entry_pc'])
        return self
    def run(self,allow_guard=False):
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0;self.snapshots=[]
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        try:self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
        except unicorn.UcError:
            if not allow_guard or self.guard is None:raise
        outgoing=self.regs()
        if not allow_guard:assert self.guard is None,self.guard
        if self.guard is None:assert outgoing['pc']==self.stop_pc or outgoing['pc'] in self.checkpoints or outgoing['pc'] in (0xcda4,0x3aea) and self.visits==2,('timeout_or_stop',outgoing)
        if outgoing['pc']==self.stop_pc:assert outgoing['a7']==self.expected_a7,(outgoing,self.expected_a7)
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=self.guard is None and outgoing['pc'] in (0xcda4,0x3aea),snapshots=self.snapshots,guard=self.guard,modeled_bank=self.bank,
            bank_before=bank_before,ff8_before=ff8_before,ff9_before=ff9_before)
        assert bytes(self.cpu.mem_read(0,RAM))==self.program[:RAM]
        assert bytes(self.cpu.mem_read(0x200000,0xfe000))==self.program[0x200000:0x2fe000]
        assert all(bytes(self.cpu.mem_read(RAM+i*SIZE,SIZE))==bytes(self.backing) for i in range(16))
        replay(self.program,result)
        return result
    def mutate(self,changes):
        before=self.regs()
        for change in changes:self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
        assert self.regs()==before
    def close(self):self.cpu=None;self.backing=None



def matrix(program):
    rows=[]
    def add(group,label,entry,**extra):rows.append(dict(group=group,label=label,entry_pc=entry,**extra))
    for count in (0,1,2,4,5):
        for ref in (0,1,2,0xffff):add('static','static-count%d-ref%04x'%(count,ref),0x299c,count=count,reference=ref)
    for coord in range(8):add('coordinate','coordinate-%d'%coord,0x299c,count=1,reference=1,coord=coord,parent=0x104000 if coord&1 else 0,stamp=0 if coord&2 else 0x55)
    for parent in ('self','object','stamp'):
        add('coordinate','coordinate-parent-'+parent,0x299c,count=2,reference=1,coord=0,parent=parent,stamp=0x55)
    for depth,previous,marked in ((1,0,False),(1,2,False),(0xffff,0x8000,False),(0x8000,0xffff,False),(1,0,True)):
        add('linked','linked-%04x-%04x-%s'%(depth,previous,marked),0x299c,depth=depth,previous=previous,marked=marked,children=2,count=1,reference=1)
    for children in (0,1,2,3):add('traverse','traverse-%d'%children,0x2a0a,children=children)
    for entry in (0x2a28,0x2a48,0x2a60,0x2a84):
        for children in (0,2):add('wrapper','wrapper-%x-%d'%(entry,children),entry,children=children,callback=0x87654320)
    for left,right in ((0,0),(0,1),(1,0),(0x7fff,0x8000),(0x8000,0x7fff),(0xffff,0xffff)):
        add('compare','compare-%04x-%04x'%(left,right),0x287e,left=left,right=right)
    for entry in (0x477c2,0x47fe4):
        for children in (0,2):add('whole','whole-%x-%d'%(entry,children),entry,children=children)
    add('static','duplicate-palette-live-reference',0x299c,count=4,reference=2,duplicate=True)
    add('static','mirrored-object',0x299c,count=2,reference=1,a6=0x1f2000)
    add('wrapper','wrapper-stack-overlap-live-return-guard',0x2a28,children=0,callback=0x87654320,stack_alias=True,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x278e,guard_address=0xff0029ac)
    add('coordinate','coordinate-index8-TRAP',0x299c,coord=8,guarded=True,guard_problem='unsupported_TRAP',guard_pc=0x46f06)
    add('wrapper','wrapper-depth-TRAP',0x2a48,children=0,object_depth=1,guarded=True,guard_problem='unsupported_TRAP',guard_pc=0x2a52)
    for xcarry in (0,1):
        for ycarry in (0,1):add('position','position-carry-X%d-Y%d'%(xcarry,ycarry),0x43e38,xcarry=xcarry,ycarry=ycarry,stamp=0)
    for stamp in (0,0x55,0x77):add('position','position-self-stamp%02x'%stamp,0x43e38,parent='self',stamp=stamp)
    add('position','position-live-global-stamp-alias',0x43e38,a0=0x10d47c,stamp=0,global_alias=True)
    add('wrapper','wrapper-live-saved-A6-pop',0x2a28,children=0,callback=0x12340000,live_pop_alias=True)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    base=exit_native.fixture(program,dict(group='players',label='cleanup-base',entry_pc=0x1c63c,first=0x270e,second=0x270e))
    ram=bytearray(base['ram']);regs=dict(base['regs']);writes=[];sp=S;entry=row['entry_pc'];group=row['group'];a6=row.get('a6',0x102000)
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,('fixture_nonRAM',hex(at),size)
        value&=(1<<(size*8))-1;put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    def object(at,depth=0,previous=None,next_object=None,marker=0x1234):
        for offset,size,value in ((0,4,marker),(4,4,at if next_object is None else next_object),(8,4,at if previous is None else previous),(0xc,4,0),(0x10,2,depth),(0x1d,1,0),(0x6c,1,0xff)):
            setup(at+offset,size,value)
    regs.update(a5=0x108000,a6=a6,a0=a6,a1=row.get('callback',0x8123fedc))
    # Controlled independent self-linked active palette slots and empty free-ring
    # sentinel. Cleanup alone performs all actual unlink/append operations.
    for index in range(256):
        at=0x104d92+index*16
        for off,size,value in ((0,2,index*16),(2,2,index*16),(8,2,row.get('reference',0)),(0xa,2,0x1234),(0xc,2,0x5678),(0xf,1,0x81)):setup(at+off,size,value)
    setup(0x105d92,2,0x1000);setup(0x105d94,2,0x1000)
    object(a6,row.get('depth',0));count=row.get('count',0)
    for index in range(count):setup(a6+0x19+index,1,7 if row.get('duplicate') else index)
    setup(a6+0x1d,1,count);coord=row.get('coord',0xff);setup(a6+0x6c,1,coord);setup(0x10d494,1,0x55)
    if coord<8 or row.get('stack_alias'):
        at=0x10d4e6+(coord if coord<8 else 0)*0x2c;parent=row.get('parent',0)
        if parent=='self':parent=at
        elif parent=='object':parent=a6+0x2e
        elif parent=='stamp':parent=0x10d480
        for off,size,value in ((0,4,0xffff8000),(4,4,0x7fffffff),(0x10,4,parent),(0x14,4,0x80000001),(0x18,4,0xffff0001),(0x24,1,row.get('stamp',0)),(0x25,1,0xa0)):
            setup(at+off,size,value)
        if parent:
            setup(parent+0x14,4,0xffff8001);setup(parent+0x18,4,0x7fffffff);setup(parent+0x25,1,0xc3)
    setup(0x104c9c,4,0x106800);setup(0x104ca0,2,7);object(0x106800)
    children=row.get('children',0);root=S-0x16 if row.get('live_pop_alias') else 0x103000;sentinel=0x103c00
    def chain(start,number):
        nodes=[sentinel]+[0x103100+i*0x100 for i in range(number)]+[start]
        for i,at in enumerate(nodes):object(at,0 if i in (0,len(nodes)-1) else i,previous=nodes[i-1],next_object=nodes[(i+1)%len(nodes)],marker=0x1234)
        return nodes
    checkpoints=[];stop=RETURN;ret=RETURN;expected=sp+4
    if group=='linked':
        previous=0x103000;next_obj=0x103100;tail=0x103c00
        object(previous,row['previous'],previous=tail,next_object=a6)
        object(a6,row['depth'],previous=previous,next_object=next_obj)
        object(next_obj,row['depth'],previous=a6,next_object=tail,marker=0x270e if row['marked'] else 0x1234)
        object(tail,0,previous=next_obj,next_object=previous,marker=0x270e if row['marked'] else 0x1234)
        checkpoints=[0x29c4]
    elif group in ('traverse','wrapper','whole'):
        nodes=chain(root,children)
        if group=='traverse':regs['a6']=root;checkpoints=[0x2a16]
        elif group=='wrapper':
            regs.update(a0=root,a6=0x102000);object(regs['a6'])
            setup(root+0x10,2,row.get('object_depth',0))
            checkpoints={0x2a28:[0x2a40,0x2a42,0x2a44],0x2a48:[0x2a5c],0x2a60:[0x2a16,0x2a80],0x2a84:[0x2a16,0x2aa4,0x2aa8]}[entry]
            if row.get('live_pop_alias'):
                regs['a6']=0x103456;object(regs['a6']);stop=0x2a46;expected=sp;checkpoints=[0x2a40,0x2a42,0x2a44]
            if row.get('stack_alias'):
                # The nested BSR return at object+6c changes coord ff to00.
                # 46ef4 then writes ff into that live return's high BYTE.
                sp=root+0x80;expected=sp+4
        else:
            regs['a6']=root;object(0x100bf4)
            checkpoints=[0x2a16,0x477c8,0x2aa4,0x477d4]
            if entry==0x47fe4:stop=0x47fe8;expected=sp
    elif group=='position':
        at=row.get('a0',0x104500);regs['a0']=at;parent=at if row.get('parent')=='self' else 0 if row.get('global_alias') else 0x104000
        for off,size,value in ((0,4,0xffff0000|(0xffff if row.get('xcarry') else 0)),(4,4,0x81551122 if row.get('global_alias') else 0x80000000|(0xffff if row.get('ycarry') else 0)),(0x10,4,parent),(0x14,4,0x00010001),(0x18,4,0xffff0001),(0x24,1,row['stamp']),(0x25,1,0)):
            setup(at+off,size,value)
        if parent and parent!=at:
            setup(parent+0x14,4,0x00010001);setup(parent+0x18,4,0xffff0001);setup(parent+0x25,1,0)
    elif group=='compare':
        object(a6,row['left'],previous=root);object(root,row['right']);ret=0x29c4
        stop=0x29fe if row['left']<row['right'] else 0x29c8;checkpoints=[0x29c4]
    if row.get('guarded'):checkpoints=[]
    setup(sp,4,ret)
    return dict(base,ram=bytes(ram),regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,expected_final_a7=expected,checkpoints=checkpoints,initial_host_writes=writes,group=group,return_pc=ret,initial_shared_stack=dict(base['initial_shared_stack'],return_address=sp,return_value=ret),branch_oracles={str(pc):list(pair) for pc,pair in BRANCHES.items()},synthetic_palette_self_linked_slots=True)

replay=transition.replay
flattened=transition.flattened
compare_control=screen_native.compare_control


def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program,continuous);phases=[]
    try:
        obs.prepare(fx)
        def take(label):
            remaining=[pc for pc in fx['checkpoints'] if pc not in obs.seen]
            target=fx['stop_pc'] if continuous or not remaining else remaining[0]
            p=obs.run(allow_guard=row.get('guarded',False))
            assert not p['waiting'],('unexpected_cleanup_wait',row)
            if p['guard'] is None:assert p['outgoing']['pc']==target,(row,p['outgoing'],hex(target))
            p.update(label=label,host_changes=[],stop_pc=target,carry=None);phases.append(p);return p
        p=take('begin')
        while p['guard'] is None and p['outgoing']['pc']!=fx['stop_pc']:
            assert len(phases)<20;p=take('after-checkpoint-%x'%p['outgoing']['pc'])
        pcs,events,_=flattened(phases);evidence=[];decisions={}
        for i,(pc,nxt) in enumerate(zip(pcs,pcs[1:])):
            if pc in BRANCHES:
                assert nxt in BRANCHES[pc];carry=1 if nxt==BRANCHES[pc][0] else 2
                decisions[i]=carry;evidence.append(dict(index=i,pc=pc,successor=nxt,carry=carry))
        cursor=0
        for q in phases:
            cursor+=len(q['pcs'])-1
            if q['outgoing']['pc'] in BRANCHES:q['carry']=decisions[cursor]
            elif q is phases[-1] and row['group']=='compare':q['carry']=decisions[cursor-1]
            q['branch_evidence']=evidence
        if row['group']=='linked':
            removed=0 if row['depth']<row['previous'] else 2 if row['marked'] else 1
            assert pcs.count(0x29ce)==removed and pcs.count(0x29c0)==(2 if row['marked'] and removed else 1)
            assert [d['carry'] for d in evidence]==([2] if not removed else [1]*removed)
        if row['group']=='traverse':
            assert pcs.count(0x29ce)==row['children'] and pcs.count(0x29c0)==row['children']
            assert [d['carry'] for d in evidence if d['pc']==0x2a16]==[2]*row['children']+[1]
        if row['group']=='position' and 'xcarry' in row:
            assert p['outgoing']['d7']==2*row['ycarry']+row['xcarry']
        if row.get('global_alias'):
            published=[e for e in events if e['access']=='write' and e['address']==0x10d494 and e['size']==4]
            reads=[e for e in events if e['access']=='read' and e['address']==0x10d494 and e['size']==1]
            assert len(published)==len(reads)==1 and published[0]['bytes'][:2]==reads[0]['bytes']=='81'
            assert events.index(published[0])<events.index(reads[0])
        if row.get('live_pop_alias'):
            assert p['outgoing']['a6']==0xffff3400 and p['outgoing']['pc']==0x2a46
            assert any(e['access']=='read' and e['address']==S-4 and e['bytes']=='ffff3400' for e in events)
        if row.get('guarded'):
            assert p['guard']['problem']==row['guard_problem'] and p['guard']['pc']==row['guard_pc'],(row,p['guard'])
            if 'guard_address' in row:assert p['guard']['address']==row['guard_address'],(row,p['guard'])
        return row,fx,phases
    finally:obs.close()

def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name)}
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];coverage=set();split_count=control_count=0
    def store(index,phases,group):
        rows=[]
        for j,p in enumerate(phases):
            coverage.update(p['pcs']);stem='%s_%03d_phase_%02d'%(group,index,j)
            events=p['events'];ports=[e for e in events if e['region'] in ('pvc','video','watchdog')]
            payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
                stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
                stem+'_trace.json':(json.dumps({k:p[k] for k in ('pcs','events','boundaries','guard')},indent=2)+'\n').encode()}
            snapshots=[]
            for k,snapshot in enumerate(p['snapshots']):
                names={}
                for field in ('ram','pvc'):
                    name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
                snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
            for name,data in payloads.items():(OUT/name).write_bytes(data);artifacts[name]=sha(data)
            rows.append(dict(label=p['label'],stop_pc=p['stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],waiting=p['waiting'],carry=p['carry'],branch_evidence=p['branch_evidence'],host_changes=p['host_changes'],modeled_bank=p['modeled_bank'],guard=p['guard'],snapshots=snapshots,
                external_reads=sum(e['region']=='external' for e in events),artifacts={name:sha(data) for name,data in payloads.items()}))
        return rows
    selections=matrix(program)
    for i,row in enumerate(selections):
        actual,fx,split=run_case(program,row);assert (actual,fx,split)==run_case(program,row)
        other,other_fx,control=run_case(program,row,True);assert (other,other_fx,control)==run_case(program,row,True)
        assert actual==other and fx==other_fx;compare_control(actual,split,control)
        result=dict(index=i,selection=actual,fixture={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')},phases=store(i,split,'case'),continuous_control=store(i,control,'control'),reproduced_twice=True,continuous_split_equivalent=True)
        (guards if row.get('guarded') else results).append(result)
        split_count+=len(split);control_count+=len(control)
        print('%d/%d %s %d phases%s'%(i+1,len(selections),row['label'],len(split),' guarded' if row.get('guarded') else ''),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,raw_lookup_30ec=dict(cpu_start=0x30ec,end_exclusive=0x30f4,sha256=sha(program[0x30ec:0x30f4]),raw=program[0x30ec:0x30f4].hex())),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),phases=sum(len(r['phases']) for r in results),continuous_control_phases=sum(len(r['continuous_control']) for r in results),
        total_split_phases=split_count,total_control_phases=control_count,fresh_CPU_runs=len(selections)*4,phase_executions=(split_count+control_count)*2,covered_PCs=sorted(coverage),failure=None,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled original cleanup/traversal/wrapper inputs, not natural object allocation or scheduler reachability.',
            'No SR/context reads after init or expected-register injection. Known C only actual29c4BCS/2a16BCC occurrence successors; all other endpoints unobserved.',
            'Direct287e returns to original29c4 under a declared controlledcaller adapter. It is not a naturalcaller claim.',
            'Coherent16RAMmirrors, CPU-owned backing, actualJSR/BSR/RTS and liveLONG stack without stack masking.',
            'Synthetic independent self-linked palette slots and explicit empty free-ring sentinel; no original palette resource bytes or legacyexpected-state masking.',
            'All freshcontinuous controls execute identical immutableprogram uninterrupted through checkpoints.',
            'Actualkind3bytes equalcanonicalROM; nativebankmappingbank2only; unsupported devices/PVCreads/targets/TRAP/timeouts guarded.',
            'The live-A6pop alias stops before2a46 RTS: reset also changes the outer return, so complete return success is not claimed.',
            '47fe8 stops before LEA48108/43ffc continuation. No complete game/CCR/IRQ/video/audio/timing model or nativefaultrollback equivalence.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
