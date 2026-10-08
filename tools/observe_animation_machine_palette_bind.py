"""Unpatched palette binding and node preparation on coherent shared stack.

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
OUT=ROOT/'artifacts/animation_machine_palette_bind_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=scene_native.RANGES+((0x47ff2,0x48042),(0x8cda,0x8d34),(0x8da2,0x8eb6),(0xe7bf4,0xe7c44),(0x3ef2,0x3f98),(0x16fac,0x16fee),(0x16ff8,0x17012))+((0x47fe8,0x47ff2),(0x43efa,0x43f7e),(0x43f92,0x43fb8),(0x43fcc,0x43fe0),(0x43ff8,0x4404e),(0x44066,0x44096),(0x440c8,0x4411e),(0xccd6,0xcd52),(0x1ad9a,0x1adf8),(0x16f9a,0x16fac),(0x1829a,0x182d0),(0x1701a,0x1724c),(0x182d0,0x1831c))
BOUNDARIES=scene_native.BOUNDARIES+(0x47ff2,0x47ff8,0x4801e,0x48024,0x48030,0x4803c,0x8da2,0x8dde,0x8dec,0x8dfe,0x8e2a,0x8e48,0x8e82,0x8ea6,0x8eb4,0x16fac,0x16ff8,0x17010)+(0x47fe8,0x47fec,0x43ffc,0x44002,0x44004,0x44008,0x4400a,0x44012,0x44032,0x4403c,0x44040,0x44066,0x44072,0x44078,0x4407c,0x4407e,0x44082,0x44086,0x44094,0x43f5c,0x43f60,0x43f70,0x43f74,0x43faa,0x43fae,0x43fcc,0x43fce,0x43fd2,0x43fd4,0x43ff8,0x43ffa,0x440c8,0x4410c,0xccd6,0xccfc,0xcd1c,0xcd48,0x1ad9a,0x1adb0,0x1add8,0x1adee,0x16f9a,0x1829a,0x182b4,0x1701a,0x1704a,0x1724a,0x182d0,0x182da,0x1831a,0x43efa,0x43f1a)
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

def prepared(program,prebound):
    key=(sha(program),prebound)
    if key in PREPARATION_CACHE:return PREPARATION_CACHE[key]
    base=scene_native.fixture(program,dict(group='scene',label='palette-list-preparer',entry_pc=0x3ef2,descriptor=0,profile=1))
    base.update(entry_pc=0x3ef2,stop_pc=RETURN,checkpoints=[],expected_final_a7=S+4)
    steps=[]
    for entry in ((0x3ef2,0xe7bf4) if prebound else (0x3ef2,)):
        base['entry_pc']=entry;o=Observer(program).prepare(base)
        try:r=o.run()
        finally:o.close()
        steps.append(dict(entry_pc=entry,incoming=r['incoming'],outgoing=r['outgoing'],ram_before_sha256=sha(r['ram_before']),ram_after_sha256=sha(r['ram_after']),ports=[e for e in r['events'] if e['region'] in ('pvc','watchdog','video')]))
        base['ram']=r['ram_after']
    result=(base['ram'],steps);PREPARATION_CACHE[key]=result;return result


def matrix(program):
    rows=[]
    def add(group,label,entry,**fields):rows.append(dict(group=group,label=label,entry_pc=entry,**fields))
    for profile in (0,1):
        for prebound in (False,True):
            add('whole','whole-%d-%d'%(profile,prebound),0x47ff2,profile=profile,prebound=prebound)
            for entry in (0xe7bf4,0xe7c36):add('wrapper','wrapper-%x-%d-%d'%(entry,profile,prebound),entry,profile=profile,prebound=prebound)
    for ref in (0,1,2,0xffff):add('release','release-reference-%x'%ref,0x8e82,ref=ref)
    add('release','release-prebound17',0x8e82,prebound=True)
    add('binding','binding-empty',0x8da2,empty=True)
    for slot in (0,1,255,0x7ff,0xfff,0x1000,0x7fff,0x8000,0xfffe):
        add('binding','binding-slot-%x'%slot,0x8da2,slot=slot)
    for source in (0,1,0xff,0xffff):
        for flags in (0,0x80,0xff):add('binding','binding-source-%x-flags-%x'%(source,flags),0x8da2,source=source,flags=flags)
    add('binding','binding-skip-splice',0x8da2,skip=True)
    add('binding','binding-two-records',0x8da2,two=True)
    add('binding','binding-live-flags-operand',0x8da2,operand_alias=True)
    add('binding','binding-live-bucket-reload',0x8da2,list_alias=True,source=0x100)
    add('binding','binding-live-RTS-return',0x8da2,stack_alias=True,source=4,sp=0x104d9e,stop=0x4f080)
    add('binding','binding-mirrored-list',0x8da2,table=0x1f4000)
    for value in (0,0x7ff,0x800,0xfff,0x1000,0x7fff,0x8000,0xffff):add('coordinate','coordinates-%x'%value,0x16ff8,value=value)
    for entry in (0x16fac,0x16ff8):
        for node in (0x106000,0x1f6000):add('node','node-%x-%x'%(entry,node),entry,node=node)
    add('coordinate','coordinate-live-return',0x16ff8,return_alias=True,stop=0x40000)
    add('binding','binding-odd-table',0x8da2,table=0x104001,guarded=True,guard_problem='unsupported_odd_data_access',guard_pc=0x8dae,guard_address=0x104001)
    add('binding','binding-signed-negative-ROM-target',0x8da2,slot=0x800,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x8df4,guard_address=0xfcd94)
    add('node','node-final-byte-bank-write',0x16fac,node=0x1fff90,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x16fe6,guard_address=0x20000a)
    add('coordinate','coordinate-second-LONG-bank-write',0x16ff8,node=0x1fffca,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x16ffc,guard_address=0x200000)
    add('binding','binding-missing-device-read',0x8da2,table=0x300000,missing_device=True,guarded=True,guard_problem='unsupported_data_device',guard_pc=0x8dae,guard_address=0x300000)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    initial,steps=prepared(program,row.get('prebound',False))
    base=scene_native.fixture(program,dict(group='scene',label='palette-base',entry_pc=0x43ffc,descriptor=0,profile=row.get('profile',1)))
    ram=bytearray(initial);regs=dict(base['regs']);sp=row.get('sp',S);entry=row['entry_pc'];stop=row.get('stop',RETURN);writes=[]
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,('fixture_nonRAM',hex(at),size)
        value&=(1<<(8*size))-1;put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    setup(sp,4,RETURN);checkpoints=[];expected=sp+4
    if row['group']=='whole':
        stop=0x48042;expected=sp;checkpoints=[0x47ff8,0x4801e,0x48024,0x48030,0x4803c]
    elif row['group']=='release':
        if 'ref' in row:setup(0x104d9a,2,row['ref'])
        checkpoints=[0x8e96,0x8eb4]
    elif row['group']=='binding':
        table=row.get('table',0x104000);slot=row.get('slot',0);source=row.get('source',0x1234);flags=row.get('flags',0)
        if row.get('operand_alias'):table=0x104d9a;stop=0x8e36;expected=sp
        if row.get('missing_device'):pass
        elif row.get('empty'):setup(table,2,0xffff)
        else:
            for off,size,val in ((0,2,slot),(2,2,source),(4,1,flags),(5,1,0x6b),(6,2,0xffff)):setup(table+off,size,val)
            if row.get('two'):
                for off,size,val in ((6,2,1),(8,2,0x4321),(10,1,0xff),(11,1,0x12),(12,2,0xffff)):setup(table+off,size,val)
            offset=(slot<<4)&65535;signed=offset if offset<0x8000 else offset-0x10000;target=0x104d92+signed
            # Explicit valid synthetic list operands for nonstandard reachable nodes.
            if RAM<=target and target+4<=0x200000 and slot not in (0,1,255):setup(target,2,0);setup(target+2,2,0)
            if row.get('list_alias'):setup(0x104d92,2,0);setup(0x104d94,2,6)
            if row.get('skip'):setup(0x104d92+((source&255)<<4)+6,2,offset)
        regs['a0']=table;checkpoints=[] if row.get('guarded') else [0x8dde] if not row.get('empty') and not row.get('skip') else []
    elif row['group'] in ('node','coordinate'):
        node=row.get('node',0x106000);regs.update(a0=node,a1=0x12345678,a2=0x87654321)
        if row.get('value') is not None:regs.update(d0=0xabcd0000|row['value'],d1=0x76540000|((row['value']+1)&65535))
        if row.get('return_alias'):regs.update(a0=sp-0x2e,a1=stop)
        checkpoints=[0x16fb2,0x16fec] if entry==0x16fac else [0x16ffc,0x17010]
        if row.get('guarded'):checkpoints=[]
    return dict(base,ram=bytes(ram),regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,expected_final_a7=expected,checkpoints=checkpoints,initial_host_writes=writes,group=row['group'],return_pc=RETURN,preparation=dict(kind='Separate original CPU fixture preparation; all16R/A7/PC context reset belongs to fresh main input',steps=steps),initial_shared_stack=dict(base['initial_shared_stack'],return_address=sp,return_value=int.from_bytes(bytes(ram[(sp+i)&65535] for i in range(4)),'big'),slot_role='initial_RTS_frame'),branch_oracles={},bank_mapping='CPU200000..2fdfff readonly canonical bank2/3 buffer; rawPVC separate',raw_PVC_storage=True)


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
            assert len(phases)<20
        pcs,events,_=flattened(phases)
        if row['group']=='whole':
            units={(e['address'],e['size']) for e in events if e['region']=='bank'}
            assert units=={(0x20000c,4),(0x2004c0,4),(0x201ec0,2),(0x201ec2,2),(0x201ec4,1),(0x201ec6,2)}
            assert p['outgoing']['a0']==0x10d256 and p['outgoing']['a1']==0x480f2 and p['outgoing']['a2']==0
        if row.get('operand_alias'):
            assert any(e['pc']==0x8e2a and e['access']=='read' and e['address']==0x104d9e and e['bytes']=='12' for e in events)
            assert p['ram_after'][0x4da1]==0x92
        if row.get('prebound') and row['entry_pc'] in (0x47ff2,0xe7bf4,0xe7c36,0x8e82):assert pcs.count(0x8e4a)==17
        if row.get('list_alias'):
            assert any(e['pc']==0x8dec and e['access']=='read' and e['address']==0x104d98 and e['bytes']=='0000' for e in events)
            assert p['outgoing']['d3']&65535==0
        if row.get('stack_alias'):
            assert any(e['pc']==0x8e48 and e['access']=='read' and e['address']==fx['initial_a7'] and e['bytes']=='0004f080' for e in events)
        if row.get('return_alias'):assert p['outgoing']['pc']==0x40000
        if row.get('guarded'):
            assert p['guard']['problem']==row['guard_problem'] and p['guard']['pc']==row['guard_pc'],(row,p['guard'])
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
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),ROOT/'docs/analysis/animation-machine-palette-bind-contract.md'}
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
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,palette_bank_data=dict(root=0x20000c,lookup=0x2004c0,binding=0x201ec0,raw_window_bytes=16,actual_unique_read_bytes=15)),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),phases=sum(len(r['phases']) for r in results),continuous_control_phases=sum(len(r['continuous_control']) for r in results),
        total_split_phases=split_count,total_control_phases=control_count,fresh_CPU_runs=len(selections)*4,phase_executions=(split_count+control_count)*2,covered_PCs=sorted(coverage),failure=None,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled fresh fixtures; original3ef2/e7bf4 preparation is declared, all new entry context is initial input, not midrun injection.',
            'Whole47ff2 stops48042 before1861a map update; no natural scheduler/gameplay or completed rendering claim.',
            'No SR/context reads or expected register injection; all endpoints carry unobserved.',
            'Coherent16RAM mirrors/liveA7 and CPU-owned readonly bank2/3 backing; PVC separate, no banked code/PVCreads.',
            'Every actualbankread checked at current physical offset; raw nativePVC is distinct from independently folded hardware storage.',
            'The live-flags operand alias stops8e36 before a terminator changed by original node flags is fetched; normal fixtures cover complete RTS separately.',
            'Guard native partial effects are separate from checked C++ rollback; no generalCCR/IRQ/timing/fullgame claim.'

])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
