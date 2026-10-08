"""Unpatched scene reset, descriptor allocation and node helpers on coherent shared stack.

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
OUT=ROOT/'artifacts/animation_machine_scene_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=cleanup_native.RANGES+((0x47fe8,0x47ff2),(0x43efa,0x43f7e),(0x43f92,0x43fb8),(0x43fcc,0x43fe0),(0x43ff8,0x4404e),(0x44066,0x44096),(0x440c8,0x4411e),(0xccd6,0xcd52),(0x1ad9a,0x1adf8),(0x16f9a,0x16fac),(0x1829a,0x182d0),(0x1701a,0x1724c),(0x182d0,0x1831c))
BOUNDARIES=cleanup_native.BOUNDARIES+(0x47fe8,0x47fec,0x43ffc,0x44002,0x44004,0x44008,0x4400a,0x44012,0x44032,0x4403c,0x44040,0x44066,0x44072,0x44078,0x4407c,0x4407e,0x44082,0x44086,0x44094,0x43f5c,0x43f60,0x43f70,0x43f74,0x43faa,0x43fae,0x43fcc,0x43fce,0x43fd2,0x43fd4,0x43ff8,0x43ffa,0x440c8,0x4410c,0xccd6,0xccfc,0xcd1c,0xcd48,0x1ad9a,0x1adb0,0x1add8,0x1adee,0x16f9a,0x1829a,0x182b4,0x1701a,0x1704a,0x1724a,0x182d0,0x182da,0x1831a,0x43efa,0x43f1a)
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




def canonical_descriptors(program):
    addresses=set()
    for address in struct.unpack_from('>%dI'%COUNT,program,INDEX):
        for record in decode_group(program,address)['records']:
            pointer=struct.unpack_from('>I',program,record['source_cpu_address']+2)[0]
            if not pointer:continue
            _,commands,_=command_span(program,pointer)
            for command in commands:
                if command['opcode']==8:addresses.add(struct.unpack('>I',bytes.fromhex(command['operand_hex']))[0])
    return sorted(addresses)


def matrix(program):
    rows=[]
    def add(group,label,entry,**extra):rows.append(dict(group=group,label=label,entry_pc=entry,**extra))
    for profile in (0,1):
        add('scene','scene-null-%d'%profile,0x43ffc,descriptor=0,profile=profile)
        add('scene','upper-48108-%d'%profile,0x47fe8,descriptor=0x48108,profile=profile)
    for descriptor in canonical_descriptors(program):
        for profile in (0,1):add('scene','canonical-%06x-%d'%(descriptor,profile),0x43ffc,descriptor=descriptor,profile=profile)
    for kind in ('prefix','suffix','both','negative-stride'):
        for profile in (0,1):add('synthetic','synthetic-'+kind+'-%d'%profile,0x43ffc,layout=kind,profile=profile)
    add('synthetic','suffix-node-clear-saved-D7-WORD-alias',0x43ffc,layout='suffix-word-alias',stop=0x44086)
    add('synthetic','suffix-node-slot-saved-D7-WORD-alias',0x43ffc,layout='suffix-slot-alias',stop=0x44086)
    add('synthetic','RAM-descriptor-lowWORDzero-fullpointer',0x43ffc,layout='prefix',descriptor=0x100000)
    add('synthetic','RAM-descriptor-mirror',0x43ffc,layout='both',descriptor=0x1f4000)
    add('record','record-type1-no-slot-TRAP',0x43f5c,kind=1,request=0x17d,guarded=True,guard_problem='unsupported_TRAP',guard_pc=0x43f7c)
    add('record','record-type2-no-slot-TRAP',0x43f5c,kind=2,limit=16,guarded=True,guard_problem='unsupported_TRAP',guard_pc=0x43fb6)
    add('synthetic','suffix-type0-collected-then-TRAP',0x43ffc,layout='zero-suffix',guarded=True,guard_problem='unsupported_TRAP',guard_pc=0x43fde)
    for upper in (0,1):
        for current,limit,request in ((0,0x17c,0),(0,0x17c,0x20),(0x17b,0x17c,0x20),(0xfff0,0xffff,0x20),(0x8000,0x7fff,0xffff),(0xffff,0,1)):
            add('slot','slot-%d-%04x-%04x-%04x'%(upper,current,limit,request),0x440c8,upper=upper,current=current,limit=limit,request=request)
    for count in (0,1,0xffff):add('word-loop','queue-WORD-loop-%04x'%count,0xccfc,count=count,stop=0xcd06)
    for entry in (0x43f1a,0x182b4):
        for count in (0,1):add('video-loop','video-loop-%x-%04x'%(entry,count),entry,count=count)
    for slot in (0,1,0x7fff,0x8000,0xffff):add('node','node-slot-%04x'%slot,0x16f9a,slot=slot)
    for entry in (0xccd6,0x43f3e,0x1ad9a):add('reset','reset-%x'%entry,entry)
    add('clear','node-WORD-clear-mirror',0x182d0,node=0x1f2000)
    add('clear','node-WORD-clear-return-alias',0x182d0,node=S-0x3a,stop=0)
    add('scene','saved-A0-reset-clear-alias',0x43ffc,descriptor=0x48108,sp=0x109198,guarded=True,guard_problem='unsupported_code_target',guard_pc=0)
    add('scene','saved-A0-reset-clear-live-pop',0x43ffc,descriptor=0x48108,sp=0x109194,stop=0x4400a,a0_pop_alias=True)
    add('record','record-type2-live-WORD-operand-alias',0x43f5c,operand_alias=True)
    add('record','record-type1-PEA-return-alias',0x43f5c,pea_alias=True,kind=1)
    add('suffix-pop','suffix-D7-live-WORD-pop',0x44082,live_d7=True)
    for kind,pc in ((4,0x43fde),(0,0x43fde)):
        add('record','record-invalid-type%d'%kind,0x43f5c,kind=kind,guarded=True,guard_problem='unsupported_TRAP',guard_pc=pc)
    add('synthetic','suffix-invalid-type4',0x43ffc,layout='bad-suffix',guarded=True,guard_problem='unsupported_TRAP',guard_pc=0x4404c)
    add('clear','node-clear-late-bank-guard',0x182d0,node=0x1fffc0,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x182e0,guard_address=0x200000)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    base=exit_native.fixture(program,dict(group='players',label='scene-base',entry_pc=0x1c63c,first=0x270e,second=0x270e))
    ram=bytearray(base['ram']);regs=dict(base['regs']);writes=[];sp=row.get('sp',S);entry=row['entry_pc'];group=row['group'];stop=row.get('stop',RETURN);expected=sp+4
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,('fixture_nonRAM',hex(at),size)
        value&=(1<<(size*8))-1;put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    regs.update(a5=0x108000,a0=row.get('descriptor',0x104000),a6=0x102000)
    if not row.get('profile',1):
        for key in shared.isolated.REG_NAMES:regs[key]=0
        regs['a5']=0x108000;regs['a0']=row.get('descriptor',0x104000)
    setup(0x10d496,2,0);setup(0x10d498,2,0x17c);setup(0x10d49a,1,0)
    for node in (0x109156,0x10b1d6,0x10d256,0x10d2d6,0x106000):
        setup(node+0x26,2,0xffff);setup(node+0x7a,1,0xff)
    checkpoints=[]
    if group in ('scene','synthetic'):
        checkpoints=[0x1adb0,0x1adee,0x44008]
        if entry==0x47fe8:stop=0x47ff2;expected=sp
        if row.get('a0_pop_alias'):expected=sp
        if group=='synthetic':
            a=row.get('descriptor',0x104000);regs['a0']=a;layout=row['layout']
            # Header and all records are controlled liveRAM bytes, not ROM patches.
            if layout=='prefix':records=((6,1,3),(4,3,None))
            elif layout=='suffix':records=((4,0,None),(6,1,3),(4,3,None))
            elif layout=='both':records=((6,1,2),(4,0,None),(8,2,0x106000),(6,1,3),(4,3,None))
            elif layout=='zero-suffix':records=((4,0,None),(4,0,None),(4,3,None))
            elif layout in ('suffix-word-alias','suffix-slot-alias'):
                records=((4,0,None),(6,1,1),(8,2,S-(0x40 if layout=='suffix-word-alias' else 0x2c)),(4,3,None))
                stop=0x44086;expected=sp-4;checkpoints.append(0x44082)
            elif layout=='negative-stride':
                records=((0xfffa,1,1),)
                setup(a-6,2,0);setup(a-4,2,3) # Actual negative prefix stride reaches this terminal.
            else:records=((4,0,None),(4,4,None),(4,3,None))
            cursor=a
            for stride,kind,operand in records:
                setup(cursor,2,stride);setup(cursor+2,2,kind)
                if operand is not None:setup(cursor+4,4 if kind==2 else 2,operand)
                cursor+=8 if kind==2 else 6 if kind==1 else 4
    elif group=='slot':
        regs['d0']=(regs['d0']&0xffff0000)|row['request'];setup(0x10d49a,1,row['upper'])
        setup(0x10d496,2,row['current']);setup(0x10d498,2,row['limit'])
    elif group=='word-loop':
        regs['a0']=0x107000;regs['d0']=0xabcd0003;regs['d7']=0x87650000|row['count'];expected=sp
    elif group=='video-loop':
        regs.update(a4=0x3c0000,a1=0x3c0000,d4=0x10000,d5=0x8001ffff,d6=0x8401f000,d7=0x82010000)
        if entry==0x43f1a:regs['d0']=0xabcd0000|row['count']
        else:regs['d6']=0xabcd0000|row['count']
    elif group in ('node','clear'):
        regs['a0']=row.get('node',0x106000)
        if group=='node':regs['d0']=(regs['d0']&0xffff0000)|row['slot']
    elif group=='record':
        a=0x104000;regs['a0']=a;setup(0x10d49a,1,0);setup(0x10d498,2,row.get('limit',0x17c));kind=row.get('kind',2)
        setup(a,2,8 if kind==2 else 6);setup(a+2,2,kind);setup(a+4,4 if kind==2 else 2,0x106000 if kind==2 else row.get('request',1))
        checkpoints=[0x43f60,0x43ff8]
        if row.get('operand_alias'):
            sp=a+10;expected=sp+4;checkpoints=[0x43fcc,0x43fce,0x43fd2,0x43fd4];stop=0x43fd4;expected=sp-4
            # PEA atS-4 and nestedBSR stack overlap the live descriptor; actual
            # effects are observed rather than assuming its original type.
        if row.get('pea_alias'):
            sp=a+4;stop=0x43f64;expected=sp-4;checkpoints=[]
    elif group=='suffix-pop':
        setup(sp,2,0);regs['d7']=0xabcd5678;stop=0x44086;expected=sp+2
    if row.get('guarded'):checkpoints=[]
    if not row.get('live_d7'):setup(sp,4,RETURN)
    return dict(base,ram=bytes(ram),regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,expected_final_a7=expected,checkpoints=checkpoints,initial_host_writes=writes,group=group,return_pc=None if row.get('live_d7') else RETURN,initial_shared_stack=dict(base['initial_shared_stack'],return_address=sp,return_value=int.from_bytes(bytes(ram[(sp+i)&65535] for i in range(4)),'big'),slot_role='WORD_pop_input_not_RTS_frame' if row.get('live_d7') else 'initial_RTS_frame',WORD_pop_value=0 if row.get('live_d7') else None),branch_oracles={},bank_mapping='CPU200000..2fdfff dynamically maps declaredbank2/3 canonicalbytes; PVCseparate',raw_PVC_storage=True)


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


flattened=transition.flattened
compare_control=screen_native.compare_control


def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program,continuous);phases=[]
    try:
        obs.prepare(fx)
        while True:
            remaining=[pc for pc in fx['checkpoints'] if pc not in obs.seen];target=fx['stop_pc'] if continuous or not remaining else remaining[0]
            p=obs.run(allow_guard=row.get('guarded',False));assert not p['waiting'],('unexpected_scene_wait',row)
            p.update(label='begin' if not phases else 'after-checkpoint-%x'%phases[-1]['outgoing']['pc'],host_changes=[],stop_pc=target,carry=None,branch_evidence=[]);phases.append(p)
            if p['guard'] is None:assert p['outgoing']['pc']==target,(row,p['outgoing'],hex(target))
            if p['guard'] is not None or p['outgoing']['pc']==fx['stop_pc']:break
            assert len(phases)<25
        pcs,events,_=flattened(phases)
        pvc_writes=[e for e in events if e['region']=='pvc']
        if row['group'] in ('scene','synthetic') or row['entry_pc'] in (0x43f3e,0x1ad9a):
            assert [(e['address'],e['bytes'],e['bank_after']) for e in pvc_writes]==[(0x2ffff2,'2000',0x300000),(0x2ffff0,'0000',0x300000),(0x2ffff2,'1000',0x200000),(0x2ffff0,'0000',0x200000)]
            for q in phases:
                if q['outgoing']['pc']==0x1adb0:assert q['modeled_bank']==0x300000
                if q['outgoing']['pc']==0x1adee:assert q['modeled_bank']==0x200000
        if row['group']=='word-loop':
            assert pcs.count(0xccfc)==row['count']+1 and p['outgoing']['a0']==0x107000+2*(row['count']+1) and p['outgoing']['d7']==0x8765ffff
        if row['group']=='video-loop':assert pcs.count(row['entry_pc'])==row['count']+1
        if row.get('a0_pop_alias'):assert p['outgoing']['a0']==0 and p['outgoing']['pc']==0x4400a
        if row.get('layout') in ('suffix-word-alias','suffix-slot-alias'):
            popped=next(q for q in phases if q['outgoing']['pc']==0x44082) if not continuous else None
            if popped is not None:assert popped['ram_after'][(S-6)&65535:((S-6)&65535)+2]==b'\x00\x00'
            assert p['outgoing']['d7']&65535==0 and p['outgoing']['pc']==0x44086 and p['outgoing']['a7']==S-4
            assert any(e['access']=='read' and e['pc']==0x44082 and e['address']==S-6 and e['bytes']=='0000' for e in events)
        if row.get('operand_alias'):assert p['outgoing']['a0']==0x10 and p['outgoing']['pc']==0x43fd4
        if row.get('guarded'):
            assert p['guard']['problem']==row['guard_problem'] and p['guard']['pc']==row['guard_pc'],(row,p['guard'])
            if 'guard_address' in row:assert p['guard']['address']==row['guard_address'],(row,p['guard'])
        return row,fx,phases
    finally:obs.close()



def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),ROOT/'docs/analysis/animation-machine-scene-contract.md'}
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
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,scene_entry_descriptor=dict(cpu_start=0x48108,end_exclusive=0x48114,sha256=sha(program[0x48108:0x48114]))),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),phases=sum(len(r['phases']) for r in results),continuous_control_phases=sum(len(r['continuous_control']) for r in results),
        total_split_phases=split_count,total_control_phases=control_count,fresh_CPU_runs=len(selections)*4,phase_executions=(split_count+control_count)*2,covered_PCs=sorted(coverage),failure=None,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled original scene inputs, not natural scene scheduling or gameplay reachability.',
            'No SR/context reads or expected-register injection; all new endpoint carry unobserved.',
            'Coherent16RAM mirrors and live shared A7; no stack masking or metadata restore.',
            'Readonly CPU-owned bank backing follows each actual PVCwrite through pinned model; only bank2/3 data mappings supported. No banked code or PVCreads.',
            'Raw nativePVC snapshots are not hardware side-effect storage; independent devicefold is required for C++ comparison.',
            'RAM descriptors and host mutations are declared controlled input; original fixed descriptors and ROM remain unchanged.',
            'Directccfc lowffff executes65536actualWORD iterations and stopscd06 before affected return bytes are consumed; it is not fullcaller success.',
            'Alias proofs stop at4400a/43f64/43fd4/44086 before unsupported or altered continuation; normal fixtures separately cover fullRTS.',
            'This scene closure has no actualbankROMdatareads; bankbuffer readiness is separate synthetic backend evidence, not a claimed observedbank3read.',
            '47ff2 stops before unsupported e7c36 call. Original guards are separate from API rollback. No generalCCR/IRQ/timing/video/audio/fullgame proof.'
])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
