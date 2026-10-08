"""Unpatched map columns, clipping and transfer on coherent shared stack.

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
import observe_animation_machine_palette_bind as palette_native
import observe_animation_machine_scene as scene_native
import observe_animation_machine_cleanup as cleanup_native
import inventory_scene_setup as scene_inventory
from pack_scene_scripts import command_span
from pack_stage_catalog import decode_group,INDEX,COUNT
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
OUT=ROOT/'artifacts/animation_machine_map_transfer_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=palette_native.RANGES+((0x16f0e,0x16f9a),(0x183c6,0x184d2),(0x18530,0x185fa),(0x1861a,0x18656),(0x18702,0x1879c),(0x48042,0x4804e),(0x17012,0x1701a))+((0x47ff2,0x48042),(0x8cda,0x8d34),(0x8da2,0x8eb6),(0xe7bf4,0xe7c44),(0x3ef2,0x3f98),(0x16fac,0x16fee),(0x16ff8,0x17012))+((0x47fe8,0x47ff2),(0x43efa,0x43f7e),(0x43f92,0x43fb8),(0x43fcc,0x43fe0),(0x43ff8,0x4404e),(0x44066,0x44096),(0x440c8,0x4411e),(0xccd6,0xcd52),(0x1ad9a,0x1adf8),(0x16f9a,0x16fac),(0x1829a,0x182d0),(0x1701a,0x1724c),(0x182d0,0x1831c))
BOUNDARIES=palette_native.BOUNDARIES+(0x48042,0x48048,0x16f0e,0x16f94,0x16f98,0x183c6,0x18424,0x18496,0x18530,0x18568,0x185a6,0x185ee,0x185f4,0x1861a,0x18742,0x1874a,0x18758,0x18764,0x1877c,0x18784,0x17012)+(0x47ff2,0x47ff8,0x4801e,0x48024,0x48030,0x4803c,0x8da2,0x8dde,0x8dec,0x8dfe,0x8e2a,0x8e48,0x8e82,0x8ea6,0x8eb4,0x16fac,0x16ff8,0x17010)+(0x47fe8,0x47fec,0x43ffc,0x44002,0x44004,0x44008,0x4400a,0x44012,0x44032,0x4403c,0x44040,0x44066,0x44072,0x44078,0x4407c,0x4407e,0x44082,0x44086,0x44094,0x43f5c,0x43f60,0x43f70,0x43f74,0x43faa,0x43fae,0x43fcc,0x43fce,0x43fd2,0x43fd4,0x43ff8,0x43ffa,0x440c8,0x4410c,0xccd6,0xccfc,0xcd1c,0xcd48,0x1ad9a,0x1adb0,0x1add8,0x1adee,0x16f9a,0x1829a,0x182b4,0x1701a,0x1704a,0x1724a,0x182d0,0x182da,0x1831a,0x43efa,0x43f1a)
sha,put=extended.sha,extended.put

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
        self.bank_backing=(ctypes.c_ubyte*0xfe000).from_buffer_copy(self.program[0x200000:0x2fe000]);c._bank_backing=self.bank_backing
        c.mem_map_ptr(0x200000,0xfe000,unicorn.UC_PROT_READ,ctypes.addressof(self.bank_backing))
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
            if region=='bank' and self.bank not in (0x200000,0x300000):stop('unsupported_bank_mapping',bank=self.bank);return
            if size>1 and address&1:stop('unsupported_odd_data_access',address=address,size=size);return
            before=bytes(c.mem_read(address,size));data=before if kind=='read' else (value&((1<<(size*8))-1)).to_bytes(size,'big')
            item=dict(pc=self.pc,hook_pc=c.reg_read(REGS['pc']),access=kind,address=address,size=size,bytes=data.hex(),before=before.hex(),region=region)
            if region=='bank':
                physical=self.bank+address-0x200000
                assert data==self.program[physical:physical+size]
                item.update(bank_at_read=self.bank,physical_rom_offset=physical)
            if region=='pvc':
                v=int.from_bytes(data,'big')
                if address==0x2ffff0:self.ff8=v
                else:self.ff9=v
                self.bank,self.ff8,self.ff9=pvc_bank_update(self.ff8,self.ff9)
                item.update(bank_after=self.bank,ff8_after=self.ff8,ff9_after=self.ff9)
                if self.bank in (0x200000,0x300000):ctypes.memmove(ctypes.addressof(self.bank_backing),self.program[self.bank:self.bank+0xfe000],0xfe000)
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
        assert bytes(self.cpu.mem_read(0x200000,0xfe000))==self.program[self.bank:self.bank+0xfe000]
        assert all(bytes(self.cpu.mem_read(RAM+i*SIZE,SIZE))==bytes(self.backing) for i in range(16))
        replay(self.program,result)
        return result
    def mutate(self,changes):
        before=self.regs()
        for change in changes:self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
        assert self.regs()==before
    def close(self):self.cpu=None;self.backing=None;self.bank_backing=None




PREPARATION_CACHE={}

def prepared(program,profile=1):
    key=(sha(program),profile)
    if key in PREPARATION_CACHE:return PREPARATION_CACHE[key]
    initial,prior=palette_native.prepared(program,False)
    fx=scene_native.fixture(program,dict(group='scene',label='map-valid-slot-preparer',entry_pc=0x47fe8,descriptor=0x48108,profile=profile))
    fx.update(ram=initial,entry_pc=0x47fe8,stop_pc=0x48042,checkpoints=[],expected_final_a7=S)
    results=[]
    for repeat in range(2):
        o=Observer(program).prepare(fx)
        try:r=o.run()
        finally:o.close()
        results.append(r)
    assert results[0]==results[1];r=results[0]
    slot=int.from_bytes(r['ram_after'][0xd27c:0xd27e],'big');assert slot<0x8000
    details=dict(steps=prior,scene_palette=dict(entry_pc=0x47fe8,stop_pc=0x48042,incoming=r['incoming'],outgoing=r['outgoing'],RAM_before_sha256=sha(r['ram_before']),RAM_after_sha256=sha(r['ram_after']),ports_sha256=sha(b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in r['events'] if e['region'] in ('video','pvc','watchdog'))),ports=sum(e['region'] in ('video','pvc','watchdog') for e in r['events']),fresh_twice_equal=True,actual_slot=slot))
    result=(r['ram_after'],r['outgoing'],details,fx);PREPARATION_CACHE[key]=result;return result


def matrix(program):
    rows=[]
    def add(group,label,entry,**fields):rows.append(dict(group=group,label=label,entry_pc=entry,**fields))
    for profile in (0,1):
        add('whole','whole-valid-slot-%d'%profile,0x48042,profile=profile)
        add('connected','connected-scene-palette-map-%d'%profile,0x47fe8,profile=profile)
    for entry in (0x1861a,0x18702,0x183c6):add('primary','primary-direct-%x'%entry,entry)
    for kind in ('null','negative','records','backtrack','live-record'):
        for x in (0,2,0xffff):add('columns','columns-%s-%x'%(kind,x),0x16f0e,kind=kind,x=x,count=3)
    add('columns','columns-zero-count-full65536',0x16f0e,kind='null',x=0,count=0,width=0)
    add('columns','columns-pointer-lowWORDzero-nonnull',0x16f0e,kind='lowword-zero',count=2)
    add('primary','primary-mirrored-node',0x183c6,node=0x1f6000)
    for flags in (0,8,16,24):
        for xy in ((0,0),(7,11)):add('wrap','wrap-%x-%d-%d'%(flags,*xy),0x18702,flags=flags,x=xy[0],y=xy[1])
    for xy in ((0,0),(2,4),(0xffff,0xffff),(3,0),(0,5),(0x8000,0),(0,0x8000)):
        add('clip','clip-%x-%x'%xy,0x183c6,x=xy[0],y=xy[1])
    for mode in ('skip','normal','empty','overlap'):
        add('secondary','secondary-'+mode,0x183c6,secondary=mode)
    for negative in (False,True):add('primary','primary-slot-%d'%negative,0x183c6,negative=negative)
    add('alias','transfer-MOVEM-node-flags',0x183c6,movem_flags=True)
    add('alias','transfer-MOVEM-shadow-live-D5',0x183c6,shadow_alias=True,sp=0x100012)
    add('alias','transfer-MOVEM-header-width',0x183c6,movem_header=True)
    add('alias','wrap-MOVEM-live-D0-restoration',0x18702,stack_return=True)
    add('alias','column-write-overwrites-BSR-return',0x18702,stack_guard=True,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x16f98,guard_address=0x218742)
    add('wrap','wrap-zero-width-divisor',0x18702,flags=8,x=7,width=0,guarded=True,guard_problem='CPU_exception',guard_pc=0x1871a,guard_number=5)
    add('wrap','wrap-zero-height-divisor',0x18702,flags=16,y=11,height=0,guarded=True,guard_problem='CPU_exception',guard_pc=0x18738,guard_number=5)
    add('columns','column-record-odd',0x16f0e,kind='odd',guarded=True,guard_problem='unsupported_odd_data_access',guard_pc=0x16f4e,guard_address=0x103001)
    add('primary','primary-node-flag-bank-write',0x183c6,node=0x1fff86,negative=True,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x185e8,guard_address=0x200000)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    ram0,out,preparation,prep_fx=prepared(program,row.get('profile',1));ram=bytearray(ram0);regs={k:out[k] for k in shared.isolated.REG_NAMES};sp=row.get('sp',S);entry=row['entry_pc'];stop=row.get('stop',RETURN);checkpoints=[];expected=sp+4;writes=[]
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,('fixture_nonRAM',hex(at),size)
        value&=(1<<(8*size))-1;put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    setup(sp,4,RETURN)
    group=row['group'];node=row.get('node',0x106000);header=0x104000
    if group=='connected':
        ram=bytearray(prep_fx['ram']);regs=dict(prep_fx['regs']);preparation=dict(steps=preparation['steps'],role='Only original3ef2 prepares incomingRAM; scene/palette/map execute in this same mainCPU from47fe8');stop=0x4804e;expected=sp;checkpoints=[0x47ff2,0x48042,0x18424,0x18530,0x185ee,0x48048]
    elif group=='whole':
        stop=0x4804e;expected=sp;checkpoints=[0x18424,0x18530,0x185ee,0x48048]
    else:
        width=row.get('width',3);height=row.get('height',5)
        regs.update(a0=node,a1=header,a5=0x108000,d0=0xabcd0000|row.get('x',0),d1=0x76540000|row.get('y',0),d2=0x43210002,d3=0x65430002,d4=0x87650000,d5=0x98760000)
        for off,size,val in ((0,2,0x3c),(2,2,0),(4,2,width),(6,2,height)):setup(header+off,size,val)
        for off,size,val in ((0x14,2,0),(0x18,2,0),(0x26,2,0xffff if row.get('negative') else 0),(0x2e,4,header),(0x32,2,0),(0x34,2,0),(0x36,4,0),(0x7a,1,row.get('flags',0))):
            if node+off+size<=0x200000:setup(node+off,size,val)
            else:assert row.get('guarded'),('fixture_nonRAM',hex(node+off))
        for i in range(32):setup(node+0x3a+2*i,2,0x21)
        if group=='columns':
            regs['d2']=(regs['d2']&0xffff0000)|row.get('count',1);kind=row['kind'];pointer=0x100000 if kind=='lowword-zero' else 0 if kind=='null' else 0xffffffff if kind=='negative' else 0x103001 if kind=='odd' else 0x103000
            setup(node+0x36,4,pointer)
            if kind=='lowword-zero':setup(0x100000,2,0);setup(0x100002,2,0x0141);setup(0x100004,2,0xffff)
            if kind in ('records','backtrack','live-record'):
                for i,(x,y,code) in enumerate(((0,1,0x41),(2,2,0x52),(0xffff,3,0x63))):setup(0x103000+4*i,2,x);setup(0x103002+4*i,1,y);setup(0x103003+4*i,1,code)
                if kind=='backtrack':setup(node+0x36,4,0x103004)
                if kind=='live-record':setup(node+0x36,4,node+0x3a);setup(node+0x3a,2,0);setup(node+0x3c,2,0xffff)
            checkpoints=[0x16f94]
        elif group=='secondary':
            mode=row['secondary']
            if mode!='skip':
                setup(header+2,2,0x3000);setup(0x1fe04a,4,0xffffffff if mode=='empty' else node+0x80 if mode=='overlap' else 0x103000)
                if mode!='empty':
                    source=node+0x80 if mode=='overlap' else 0x103000
                    for i in range(4):setup(source+2*i,2,0x40)
                    for i in range(8):setup(source+0x40+2*i,2,0x1230+2*i)
            checkpoints=[0x18424,0x18530,0x185ee]
        elif entry==0x183c6:checkpoints=[0x18424,0x18530,0x185ee] if group not in ('clip','alias') else []
        elif entry==0x18702:checkpoints=[0x18742,0x1874a]
        elif entry==0x1861a:checkpoints=[0x18742,0x1874a]
        if row.get('movem_flags'):sp=node+0x7c;setup(sp,4,RETURN);checkpoints=[]
        if row.get('movem_header'):sp=header+8;setup(sp,4,RETURN);checkpoints=[]
        if row.get('stack_return'):sp=node+0x86;setup(sp,4,RETURN);checkpoints=[]
        if row.get('stack_guard'):sp=node+0x40;setup(sp,4,RETURN);checkpoints=[]
        if row.get('guarded'):checkpoints=[]
    return dict(prep_fx,ram=bytes(ram),regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,expected_final_a7=(sp+4 if group not in ('whole','connected') else expected),checkpoints=checkpoints,initial_host_writes=writes,group=group,preparation=preparation,return_pc=RETURN,initial_shared_stack=dict(prep_fx['initial_shared_stack'],return_address=sp,return_value=int.from_bytes(bytes(ram[(sp+i)&65535] for i in range(4)),'big'),slot_role='initial_RTS_frame'),branch_oracles={},bank_mapping='CPU200000..2fdfff readonly canonicalbank2/3 with dynamicactualPVCwrites;rawPVCseparate',raw_PVC_storage=True)


flattened=transition.flattened
compare_control=screen_native.compare_control


def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);o=Observer(program,continuous);phases=[]
    try:
        o.prepare(fx)
        while True:
            remaining=[pc for pc in fx['checkpoints'] if pc not in o.seen];target=fx['stop_pc'] if continuous or not remaining else remaining[0]
            p=o.run(allow_guard=row.get('guarded',False));assert not p['waiting']
            p.update(label='begin' if not phases else 'after-checkpoint-%x'%phases[-1]['outgoing']['pc'],host_changes=[],stop_pc=target,carry=None,branch_evidence=[]);phases.append(p)
            if p['guard'] is None:assert p['outgoing']['pc']==target,(row,p['outgoing'],hex(target))
            if p['guard'] is not None or p['outgoing']['pc']==fx['stop_pc']:break
            assert len(phases)<30
        pcs,events,_=flattened(phases)
        if row['group'] in ('whole','connected'):
            assert pcs.count(0x18496)==320 and sum(e['region']=='video' and e['pc'] in (0x1849a,0x184a8) for e in events)==640
            assert p['ram_after'][0xd2d0]&0x87==0x87
        if row.get('movem_flags'):
            assert p['outgoing']['d5']==31
            assert any(e['pc']==0x18530 and e['access']=='read' and e['address']==0x10607a and e['bytes']=='001f' for e in events)
        if row.get('shadow_alias'):
            assert p['outgoing']['d5']==1
            assert any(e['pc']==0x18530 and e['access']=='read' and e['address']==0x100010 and e['bytes']=='0001' for e in events)
        if row.get('movem_header'):
            assert any(e['pc']==0x1843e and e['access']=='read' and e['address']==0x104000 and e['bytes']=='0002' for e in events)
            assert any(e['pc']==0x1844e and e['access']=='read' and e['address']==0x104006 and e['bytes']=='001f' for e in events)
        if row.get('stack_return'):assert p['outgoing']['d0']==0xffff8000
        if row.get('secondary')=='overlap':assert any(e['pc']==0x1857c and e['access']=='read' and e['address']==0x106082 and e['bytes']=='1236' for e in events)
        if row['label']=='columns-zero-count-full65536':assert pcs.count(0x16f1a)==65536 and p['outgoing']['d6']&65535==65535
        if row.get('guarded'):
            assert p['guard']['problem']==row['guard_problem'] and p['guard']['pc']==row['guard_pc'],(row,p['guard'])
            if 'guard_number' in row:assert p['guard']['number']==row['guard_number']
            if 'guard_address' in row:assert p['guard']['address']==row['guard_address'],(row,p['guard'])
        return row,fx,phases
    finally:o.close()


def replay(program,result):
    ram=bytearray(result['ram_before']);pvc=bytearray(result['pvc_before']);bank=result['bank_before'];ff8=result['ff8_before'];ff9=result['ff9_before']
    for e in result['events']:
        assert e['pc']==e['hook_pc'];a,n=e['address'],e['size'];data=bytes.fromhex(e['bytes'])
        if e['region']=='ram':
            before=bytes(ram[(a+i)&65535] for i in range(n));assert before.hex()==e['before']
            if e['access']=='read':assert before==data
            else:
                for i,b in enumerate(data):ram[(a+i)&65535]=b
        elif e['region']=='pvc':
            assert e['access']=='write';assert bytes(pvc[a-PVC:a-PVC+n]).hex()==e['before'];pvc[a-PVC:a-PVC+n]=data
            if a==0x2ffff0:ff8=int.from_bytes(data,'big')
            else:ff9=int.from_bytes(data,'big')
            bank,ff8,ff9=pvc_bank_update(ff8,ff9);assert (bank,ff8,ff9)==(e['bank_after'],e['ff8_after'],e['ff9_after'])
        elif e['region']=='fixed':assert e['access']=='read' and data==program[a:a+n]
        elif e['region']=='bank':
            physical=bank+a-0x200000;assert e['bank_at_read']==bank and e['physical_rom_offset']==physical and data==program[physical:physical+n]
        elif e['region']=='video':assert e['access']=='write' and (a==0x3c0000 and n in (2,4) or a==0x3c0004 and n==2)
        elif e['region']=='watchdog':assert e['access']=='write' and a==0x300001 and n==1
        else:assert e['access']=='read' and a==EXTERNAL
    assert bytes(ram)==result['ram_after'] and bytes(pvc)==result['pvc_after'] and bank==result['modeled_bank']


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),ROOT/'docs/analysis/animation-machine-map-transfer-contract.md'}
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
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,map_bank_data=dict(primary_root_physical=0x300004,primary_lookup_physical=0x3000f8,map_physical=0x3a4e10,map_raw_size=1284)),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),phases=sum(len(r['phases']) for r in results),continuous_control_phases=sum(len(r['continuous_control']) for r in results),
        total_split_phases=split_count,total_control_phases=control_count,fresh_CPU_runs=len(selections)*4,phase_executions=(split_count+control_count)*2,covered_PCs=sorted(coverage),failure=None,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability.',
            'Original3ef2 and47fe8→48042 produce declared fresh preparation; no after-begin PC/register/SR/context injection.',
            'Whole48042 stops4804e before timer/palette continuation; connected47fe8 group runs originalscene/palette/map in one CPU.',
            'Full64KiBRAM/16R/PC/liveA7, readonlybank2/3 data,rawPVC separate; no banked code/PVCreads or ROMpatch.',
            'Every bankread checked at actualphysicaloffset; orderedvideo ports are instruction accesses, not physicalbuscycles/pixel output.',
            'Nativecarry unobserved;185ee/185f4 are source-known writers, not SR measurements.',
            'Synthetic RAMheaders/column records/secondary pointers are declared inputs; immutable lookup root used even when signedoffset reaches RAMmirror.',
            'Nativeguards record partial effects separately from checked APIrollback; no generalCCR/IRQ/timing/fullgame completion.'

])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
