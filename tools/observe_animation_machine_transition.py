"""Unpatched shared-stack transition gates, pending sound and fill callers.

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
OUT=ROOT/'artifacts/animation_machine_transition_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=hud_machine.RANGES+((0x47d24,0x47d3e),(0x47d46,0x47da4),(0x477ac,0x477c2),(0x35a2,0x35f0),(0x4e216,0x4e24e),(0xbee,0xc36))
BOUNDARIES=hud_machine.BOUNDARIES+(0x47d24,0x47d2a,0x47d2e,0x47d34,0x47d38,0x47d46,0x47d58,0x47d60,0x47d72,0x47d8a,0x47d92,0x47d98,0x47d9c,0x477ac,0x35a2,0x35cc,0x35e0,0x35ee,0x4e216,0x4e242,0x4e248,0xbee,0xbf4,0xc2a,0xc28,0xc34)
sha,put=extended.sha,extended.put
BRANCHES={0x47d2a:(0x47d3e,0x47d2e),0x47d34:(0x47d38,0x47d3e),0x47d42:(0x47d72,0x47d46)}

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
        self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
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
    statuses=(0,1,2,5,6,255)
    for first in statuses:
        for second in statuses:add('gate','gate-%02x-%02x'%(first,second),0x4e216,first=first,second=second)
    for request in (0,0x55,255):
        for first,second in ((0,0),(1,0),(2,255),(255,1),(255,2),(255,255)):
            add('request','request-%02x-%02x-%02x'%(request,first,second),0xbee,request=request,first=first,second=second)
    add('request','request-live-RTS-restored',0xbee,request=0x7d,first=1,second=0,initial_a7=0x10f002,return_alias=True)
    add('request','request-live-RTS-consumed-guard',0xbee,request=0x7d,first=0,second=0,initial_a7=0x10f002,return_alias=True,guarded=True)
    for first,second,status0,status1 in ((0,0,0,0),(0,5,1,0),(5,0,0,2),(5,5,0,0),(1,0,0,0),(2,5,0,0),(255,255,0,0),(0,1,0,0),(6,6,0,0),(0,0,255,255)):
        add('caller','caller-gates-%02x-%02x-%02x-%02x'%(first,second,status0,status1),0x47d24,first=first,second=second,status0=status0,status1=status1)
    for flag in (0,0x7f,0x80,255):
        for fill in (0,1):add('signed','signed-%02x-fill%d'%(flag,fill),0x47d46,flag=flag,fill=fill)
    for gate in (0,1):
        for bit in (0,1):add('negative','negative-gate%d-bit%d'%(gate,bit),0x47d60,negative_gate=gate,negative_bit=bit)
    for pending,timer,previous in ((0,0,0),(0x1ac3,1,0),(0x1ac3,0xffff,0),(0x1ac3,0,0x1ac3),(0x1ac3,0,0),(0x55,0,0)):
        add('pending','pending-%04x-timer%04x-prev%04x'%(pending,timer,previous),0x47d72,pending=pending,timer=timer,previous=previous)
    for wait in (1,2,3):add('pending','pending-sound-wait%d'%wait,0x47d72,pending=0x1ac3,sound_wait=wait)
    for width,height,coord,tile in ((0,0,0xffff,0xabff),(0,3,0xffff,0x1234),(1,0,0x749f,0xffff),(2,0,0x7500,0),(1,1,0x7243,0xc9ff),(2,3,0x7162,0x00ff),(18,8,0x7162,0x00ff),(3,2,0x7400,0xabc0)):
        add('fill','fill-%d-%d-%04x'%(width,height,coord),0x35a2,width=width,height=height,coord=coord,tile=tile)
    add('fill','fill-TRAP-first',0x35a2,width=1,height=1,coord=0x7500,tile=0,guarded=True)
    add('fill','fill-TRAP-after-first-port',0x35a2,width=1,height=2,coord=0x74ff,tile=0,guarded=True)
    add('fill','actual-477ac-wrapper',0x477ac)
    for index in (110,112,113,116,118,119,120,121):
        add('upper','upper-HUD-selection%d'%index,0x47c6c,hud_selection=copy.deepcopy(hud_machine.matrix(program)[index]))
    add('gate_alias','actual-JSR-overwrites-first-gate',0x47d24,a5=S-4+0x75bc,first=2,second=5)
    add('gate','gate-odd-mirrored-A5',0x4e216,a5=0x1f8001,first=0,second=5)
    add('request','request-unused-opaque-A5',0xbee,a5=0xffffffff,request=255,first=2,second=0)
    add('fill','fill-unused-opaque-A5',0x35a2,a5=0xffffffff,width=2,height=1,coord=0x7162,tile=0xffff)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    selection=row.get('hud_selection')
    base=hud_machine.fixture(program,selection) if selection else readiness_machine.fixture(program,readiness_machine.matrix(program)[0])
    ram=bytearray(base['ram']);regs=dict(base['regs']);writes=[];a5=row.get('a5',0x108000);regs['a5']=a5
    sp=row.get('initial_a7',S);entry=row['entry_pc'];checkpoints=[];stop=0x480bc;ret=RETURN
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,(at,size)
        put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    first=row.get('first',0);second=row.get('second',0)
    if row['group'] not in ('request','fill'):
        setup(a5-0x75bc,1,first);setup(a5-0x74f8,1,second)
    if row['group']!='upper':
        setup(0x10f004,1,row.get('request',0x55));setup(0x10fdb6,1,row.get('status0',first if row['group']=='request' else 0));setup(0x10fdb7,1,row.get('status1',second if row['group']=='request' else 0))
    if row['group'] not in ('gate','gate_alias','request','fill'):
        for at,size,value in ((a5+0x5681,1,row.get('flag',0x80)),(a5+0x568e,1,row.get('negative_gate',0)),(a5+0x5683,1,row.get('negative_bit',0)),(a5+0x5688,2,row.get('pending',0)),(a5+0x568a,2,row.get('timer',0)),(a5+0x5686,2,row.get('previous',0))):setup(at,size,value)
        if row['group']!='upper':
            setup(a5+0x5684,1,row.get('fill',0))
            for at,size,value in ((0x100012,1,0),(0x104d7e,1,0),(0x10f001,1,0),(a5-0x3276,2,0),(a5-0x3274,2,0)):setup(at,size,value)
    if row['group']=='gate':
        ret=0x47d2a;checkpoints=[ret];stop=0x47d2e if first in (0,5) and second in (0,5) else 0x47d3e
    elif row['group']=='gate_alias':checkpoints=[0x47d2a];stop=0x47d2e
    elif row['group']=='request':
        ret=0x47d34;checkpoints=[ret];stop=0x47d3e if first in (1,2) or second in (1,2) else 0x47d38
        if row.get('guarded'):checkpoints=[]
    elif row['group']=='caller':
        checkpoints=[0x47d2a]
        if first in (0,5) and second in (0,5):checkpoints.append(0x47d34)
        if first in (0,5) and second in (0,5) and row.get('status0') not in (1,2) and row.get('status1') not in (1,2):stop=0x47f4a
        else:checkpoints.append(0x47d42)
    elif row['group']=='signed':
        stop=0x477ee if row['flag']<128 else 0x480bc
    elif row['group']=='negative':stop=0x47da4 if row['negative_gate'] and row['negative_bit'] else 0x480bc
    elif row['group']=='fill':
        stop=RETURN
        if entry==0x35a2:
            regs.update(d0=0xabcd0000|row['coord'],d1=0xbcde0000|row['tile'],d2=0xcdef0000|row['width'],d3=0xdef00000|row['height'])
    elif row['group']=='upper':
        checkpoints=list(base['checkpoints'])
        # Original HUD branch outcomes are used only as incoming fixture choices;
        # new transition bodies below have their own explicit state.
        if selection['stop'] in (0x47eac,0x47d24):
            if selection['stop']==0x47eac:stop=0x47eac
            else:
                checkpoints.extend([0x47d2a,0x47d34]);stop=0x47f4a
                if selection.get('status') in (1,2):checkpoints.append(0x47d42);stop=0x480bc
        else:stop=0x480bc
    if row.get('sound_wait'):
        for at,value in ((a5-0x3276,0),(a5-0x3274,6),(a5-0x328c,2 if row['sound_wait']==2 else 1),(a5-0x328a,0),(a5-0x327e,0x0455),(a5-0x327c,0x0566),(a5-0x327a,0x0677),(a5-0x3278,0x0788)):setup(at,2,value)
    setup(sp,4,ret)
    return dict(ram=bytes(ram),pvc=base['pvc'],regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,expected_final_a7=sp+4 if row['group'] in ('gate','request','fill') else sp,bank_base=0x200000,external=0,checkpoints=checkpoints,initial_host_writes=writes,group=row['group'],return_pc=ret,branch_oracles={str(pc):list(pair) for pc,pair in BRANCHES.items()},actual_initial_request=ram[0xf004],hud_sound_wait=selection.get('sound_wait',0) if selection else 0)
def replay(program,result):
    ram=bytearray(result['ram_before']);pvc=bytearray(result['pvc_before'])
    for e in result['events']:
        assert e['pc']==e['hook_pc'];a,n=e['address'],e['size'];data=bytes.fromhex(e['bytes'])
        if e['region']=='ram':
            before=bytes(ram[(a+i)&65535] for i in range(n));assert before.hex()==e['before']
            if e['access']=='read':assert before==data
            else:
                for i,b in enumerate(data):ram[(a+i)&65535]=b
        elif e['region']=='pvc':
            assert bytes(pvc[a-PVC:a-PVC+n]).hex()==e['before'];pvc[a-PVC:a-PVC+n]=data
        elif e['region'] in ('fixed','bank'):assert e['access']=='read' and data==program[a:a+n]
        elif e['region']=='video':assert e['access']=='write' and (a==0x3c0000 and n in (2,4) or a==0x3c0004 and n==2)
        elif e['region']=='watchdog':assert e['access']=='write' and a==0x300001 and n==1
        else:assert e['access']=='read' and a==EXTERNAL
    assert bytes(ram)==result['ram_after'] and bytes(pvc)==result['pvc_after']


def flattened(phases):
    pcs=[];events=[];changes=[]
    for p in phases:pcs.extend(p['pcs'][:-1]);events.extend(p['events']);changes.extend(p['host_changes'])
    return pcs+phases[-1]['pcs'][-1:],events,changes


def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program,continuous);phases=[]
    try:
        obs.prepare(fx)
        def take(label,changes=()):
            obs.mutate(changes);remaining=[pc for pc in fx['checkpoints'] if pc not in obs.seen]
            target=fx['stop_pc'] if continuous or not remaining else remaining[0]
            p=obs.run(allow_guard=row.get('guarded',False))
            if p['guard'] is None and not p['waiting']:assert p['outgoing']['pc']==target,(row,p['outgoing'],target)
            p.update(label=label,host_changes=list(changes),stop_pc=target,carry=None);phases.append(p);return p
        p=take('begin');waits=0
        while p['guard'] is None and p['outgoing']['pc']!=fx['stop_pc']:
            if p['waiting']:
                assert p['outgoing']['pc']==0x3aea,('unexpected_sprite_wait',row)
                waits+=1;assert waits<=2
                high=int.from_bytes(obs.cpu.mem_read(p['outgoing']['a7'],4),'big')==0x3c00
                changes=[]
                if waits==1:
                    if fx['hud_sound_wait']:
                        changes=[dict(address=fx['initial_a7']-6,size=2,value=0x0f01),dict(address=0x10dd1f,size=1,value=0),dict(address=0x10dd20,size=1,value=0xee)]
                    else:
                        changes=[dict(address=0x10d688,size=2,value=0x1bc4),dict(address=0x10d68a,size=2,value=3),dict(address=0x10d686,size=2,value=0xabcd)]
                    if high:changes.append(dict(address=p['outgoing']['a7']+4,size=1,value=0x77))
                before=p;p=take('sound-hold-live-stack-and-prefix-poison' if waits==1 else 'sound-low-hold',changes)
                assert p['waiting'] and p['outgoing']==before['outgoing'] and p['ram_before']==p['ram_after']
                waitkind=row.get('sound_wait',fx['hud_sound_wait']);head=((p['outgoing']['d1']&65535)+1)&0x7f if waitkind==3 and waits==1 else 0xffff
                p=take('sound-release%d'%waits,[dict(address=0x104d74,size=2,value=head)])
                if waitkind==3 and waits==1:assert p['waiting']
            else:
                assert p['outgoing']['pc'] in fx['checkpoints'];p=take('after-checkpoint-%x'%p['outgoing']['pc'])
        pcs,events,_=flattened(phases)
        known={}
        for i,pc in enumerate(pcs[:-1]):
            if pc in BRANCHES:
                successor=pcs[i+1];assert successor in BRANCHES[pc]
                carry=1 if successor==BRANCHES[pc][0] else 2
                assert pc not in known;known[pc]=dict(successor=successor,carry=carry)
        for q in phases:
            pc=q['outgoing']['pc']
            if pc in known:q['carry']=known[pc]['carry']
            elif q is phases[-1] and row['group'] in ('gate','request') and not q['guard']:
                oracle=0x47d2a if row['group']=='gate' else 0x47d34;q['carry']=known[oracle]['carry']
            q['branch_evidence']=known
        if row['label']=='request-live-RTS-restored':
            writes=[e for e in events if e['address']==0x10f004 and e['access']=='write']
            assert [(e['pc'],e['bytes']) for e in writes]==[(0xbf4,'00'),(0xc2a,'7d')]
            assert any(e['pc']==0xc34 and e['address']==0x10f002 and e['bytes']=='00047d34' for e in events)
        if row['label']=='request-live-RTS-consumed-guard':
            assert p['guard']==dict(problem='unsupported_code_target',pc=0x40034,target=0x40034)
            assert any(e['pc']==0xc28 and e['address']==0x10f002 and e['bytes']=='00040034' for e in events)
        if row['label'].startswith('fill-TRAP'):
            assert p['guard']==dict(problem='unsupported_TRAP',pc=0x35ca,opcode=0x4e4f)
        if row['group']=='gate_alias':
            assert any(e['pc']==0x47d24 and e['access']=='write' and e['address']==S-4 and e['bytes']=='00047d2a' for e in events)
            assert any(e['pc']==0x4e216 and e['access']=='read' and e['address']==S-4 and e['bytes']=='00' for e in events)
            assert known[0x47d2a]['carry']==2
        if row.get('sound_wait'):
            assert waits==(2 if row['sound_wait']==3 else 1)
            assert any(e['pc']==0x47d8a and e['access']=='write' for e in events)
            assert int.from_bytes(p['ram_after'][0xd688:0xd68a],'big')==0x1bc4
            assert int.from_bytes(p['ram_after'][0xd68a:0xd68c],'big')==3
            assert int.from_bytes(p['ram_after'][0xd686:0xd688],'big')==0xabcd
        return row,fx,phases
    finally:obs.close()


def compare_control(row,split,control):
    assert flattened(split)==flattened(control)
    for key in ('outgoing','ram_after','pvc_after','guard','branch_evidence'):assert split[-1][key]==control[-1][key]
    checkpoints={p['outgoing']['pc']:(p['outgoing'],p['ram_after'],p['pvc_after']) for p in split if not p['waiting'] and p['outgoing']['pc']!=split[-1]['outgoing']['pc']}
    seen=set()
    for phase in control:
        for snapshot in phase['snapshots']:
            regs=snapshot['registers'];assert checkpoints[regs['pc']]==(regs,snapshot['ram'],snapshot['pvc']);seen.add(regs['pc'])
    assert seen==set(checkpoints)
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
    # Prior exhaustive BCD evidence is pinned provenance, not reused as native output.
    for name in ('artifacts/stage_counter_bcd/verification.json','artifacts/stage_counter/unicorn/observation.json'):
        path=ROOT/name
        if path.is_file():input_paths.add(path)
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
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,raw_HUD_window=dict(cpu_start=0x4e272,end_exclusive=0x4e292,sha256=sha(program[0x4e272:0x4e292]))),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),phases=sum(len(r['phases']) for r in results),continuous_control_phases=sum(len(r['continuous_control']) for r in results),
        total_split_phases=split_count,total_control_phases=control_count,fresh_CPU_runs=len(selections)*4,phase_executions=(split_count+control_count)*2,covered_PCs=sorted(coverage),failure=None,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled originaltransition gates/request/pending-sound/fill/upperHUD fixtures, not natural scheduler reachability or whole game completion.',
            'No SR/context reads after init or result injection. Known C tags derived only from immediate executed original47d2aBCC/47d34BCS/47d42BCC successors; other endpoints unobserved.',
            'Standalone4e216/bee freshcallerreturn to originalBCC/BCS is a declaredcontrolledadapter, not proof of naturalcaller relationship.',
            'Coherent16RAMmirrors, CPU-owned backing, livecallerA7/JSR/RTS and savedBYTE/WORD stack, fullRAM/PVC event replay withoutstackmask.',
            'Freshcontinuous controls execute same immutableprogram through checkpoints uninterrupted; waits resume sameCPU with declaredRAMhostchanges only.',
            'Actualkind3program bytes equalcanonicalROM; nativebankROM mappingbank2only; PVCreads/otherbanks/MMIO/unsupportedtargets/alignment/TRAP/timeouts guarded.',
            'Fill BYTE300001/WORD3c0004/LONG3c0000 outputs are raw ordered port events separatefromPVC; no complete watchdog/video/VRAM/timing model.',
            '35a2 zeroWORDwidth/height skiploops; tileD1BYTE remainsunchanged. Actual35bc flagdependentbranch executes afternativewriter, never supplied as isolatedcheckpoint/input.',
            'Request consumed alias changesactualRTS to00040034; guards are not normal returns or nativefaultrollback equivalence. Upper47eac/47f4a/477ee/480bc/47da4 bodies stop beforeexecution.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
