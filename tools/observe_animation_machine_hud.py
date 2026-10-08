"""Unpatched shared-stack HUD/counter/palette/rectangle and upper callers.

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
import observe_animation_machine_readiness as readiness_machine
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_hud_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=readiness_machine.RANGES+((0x47c6c,0x47cae),(0x4e286,0x4e332),(0x4843c,0x4847c),(0x8cda,0x8d34),(0x35f0,0x362a))
BOUNDARIES=readiness_machine.BOUNDARIES+(0x47c6c,0x47c74,0x47c80,0x47c88,0x47c8c,0x47c92,0x47c98,0x4e286,0x4e2c2,0x4e2c8,0x4e2ce,0x4e2d4,0x4e2e2,0x4e2ea,0x4e2f0,0x4e30c,0x4e312,0x4843c,0x48468,0x4846a,0x8cda,0x8cf2,0x8d32,0x35f0,0x3624,0x3628)
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
        c.mem_map(0x200000,0xfe000,unicorn.UC_PROT_READ);c.mem_write(0x200000,self.program[0x200000:0x2fe000])
        c.mem_map(PVC,8192,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(PVC,fx['pvc'])
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
            elif address==0x3c0000 and size in (2,4) and kind=='write':region='video'
            else:stop('unsupported_data_device',address=address,size=size);return
            if kind=='write' and region not in ('ram','pvc','video'):stop('unsupported_write',address=address,size=size);return
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
    def add(group,label,**extra):rows.append(dict(group=group,label=label,**extra))
    words=(0,1,0x09ff,0x0a00,0x0b00,0x0c00,0x0d00,0x0e00,0x0f00,0x8a00,0x8b00,0x8c00,0x8d00,0x8e00,0x8f00,0x9000,0x9100,0x9200,0x9300,0x9400,0x9500,0x9600,0x9700,0x9800,0x9900,0x99ff,0x9a00,0xffff)
    for word in words:
        for profile in (0,1):add('hud','hud-%04x-profile%d'%(word,profile),word=word,profile=profile,counter=1 if profile==0 else 255)
    for word in (0,0x99ff,0xffff):add('hud','hud-flag0-%04x'%word,word=word,flag=0)
    for wait in (1,2,3):add('hud','hud-sound-wait%d'%wait,word=0x0201,counter=0,sound_wait=wait)
    add('hud','hud-palette-weight-dirty-stack-alias',word=0x1234,profile=1,initial_a7=0x104e62,palette_stack_alias=True,guarded=True)
    add('hud','hud-counter-stack-alias',word=0x0201,counter=1,a5=S-2-0x5d20)
    for high in (0,0x0a,0x10,0x9f,0xa0,0xff):
        for low in (0,1,2,255):add('bcd','bcd-%02x%02x'%(high,low),word=(high<<8)|low)
    for gate,status in ((0,1),(1,0),(1,2),(1,255)):add('bcd','bcd-gate%d-status%d'%(gate,status),word=0x0a01,gate=gate,status=status)
    for ref in (0,1):
        for weight in (0,31,32,255):add('palette','palette-ref%d-weight%d'%(ref,weight),ref=ref,weight=weight,slot=12,target=0x2222)
    for equal,current in ((True,True),(True,False),(False,True),(False,False)):
        add('palette','palette-targetsame-%s-current-%s'%(equal,current),ref=1,weight=31,slot=255,target=0x0a0d if equal else 0x2222,current=0x0a0d if current else 0x3333,old_weight=31 if current else 0)
    for width,height,tile,coord in ((1,1,0x00ff,0x749f),(2,2,0xfff8,0x7243),(4,2,0xff04,0x7283),(1,3,0x7fff,0x7440),(3,1,0xc904,0x0001),(2,1,0xabff,0x7400)):
        add('rectangle','rectangle-%d-%d-%04x'%(width,height,tile),width=width,height=height,tile=tile,coord=coord)
    for flag in (1,255):add('upper','upper-flagbypass-%d'%flag,flag=flag,word=0x1234,stop=0x47d46,branch=True)
    add('upper','upper-counter-zero',word=0,stop=0x47eac)
    for word in (0x0102,0x0a01,0x9a00):add('upper','upper-sourcezero-%04x'%word,word=word,source=0,stop=0x47d24)
    for status in (1,2):add('upper','upper-playerstatus-%d'%status,word=0x1202,source=0x0101,status=status,stop=0x47d24)
    for word in (0x1202,0x0a01):add('upper','upper-activation-readiness-%04x'%word,word=word,source=0x0101,status=0,stop=0x47d72,branch=True)
    for wait in (1,3):add('upper','upper-HUDwait-to-readiness-%d'%wait,word=0x0201,counter=0,source=0x0101,status=0,stop=0x47d72,branch=True,sound_wait=wait)
    add('rectangle','rectangle-TRAP-bound',width=1,height=1,tile=0,coord=0x7500,guarded=True)
    add('upper','upper-odd-WORD-guard',word=0x1234,a5=0x108001,stop=0x47d24,guarded=True)
    add('hud','hud-mirrored-A5',word=0x8f00,counter=1,a5=0x1f8000)
    add('bcd','bcd-odd-A5-byteaccess',word=0xa001,a5=0x108001)
    add('bcd','bcd-mirrored-A5',word=0xff01,a5=0x1f8000)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    base=readiness_machine.fixture(program,readiness_machine.matrix(program)[0]);ram=bytearray(base['ram']);regs=dict(base['regs']);writes=[]
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,(at,size)
        put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    regs['a5']=row.get('a5',0x108000);a5=regs['a5'];regs['a6']=0x102000
    sp=row.get('initial_a7',S);entry={'hud':0x4e286,'bcd':0x4843c,'palette':0x8cda,'rectangle':0x35f0,'upper':0x47c6c}[row['group']]
    stop=row.get('stop',RETURN);checkpoints=[]
    setup(sp,4,RETURN)
    setup(a5+0x5d1f,1,row.get('flag',1));setup(a5+0x5d20,1,row.get('counter',1))
    for at,size,value in ((0x100012,1,0),(0x104d7e,1,0),(0x10f001,1,0),(a5-0x3276,2,0),(a5-0x3274,2,0)):
        setup(at,size,value)
    word=row.get('word',0x1234);regs['d0']=0xabcd0000|word
    slot=row.get('slot',12);node=0x104d92+slot*16
    for at,size,value in ((node+8,2,row.get('ref',row.get('profile',0))), (node+10,2,row.get('current',0x3333)),(node+12,2,row.get('target',0x2222)),(node+14,1,row.get('old_weight',0)),(node+15,1,0x25)):
        setup(at,size,value)
    if row['group']=='hud' and row.get('flag',1) and word<=0x99ff:checkpoints=[0x4e2f0,0x4e312]
    elif row['group']=='palette':
        regs['d0']=0xabcd0000|slot;regs['d1']=0xbcde0a0d;regs['d2']=0xcdef0000|row['weight']
    elif row['group']=='rectangle':
        regs.update(d0=0xabcd0000|row['coord'],d1=0xbcde0000|row['tile'],d2=0xcdef0000|row['width'],d3=0xdef00000|row['height'])
    elif row['group']=='bcd':
        setup(a5+0x5683,1,0x10 if row.get('gate',1) else 0)
        setup(a5+0x7db6,1,row.get('status',1));setup(a5+0x7db7,1,0)
        setup(a5+0x567e,2,word)
    elif row['group']=='upper':
        setup(a5+0x5684,1,row.get('flag',0));setup(a5+0x567e,2,word);setup(a5+0x5683,1,0x10)
        setup(a5+0x7db6,1,row.get('status',0));setup(a5+0x7db7,1,1 if row.get('status')==2 else 0)
        setup(a5-0x76a4,2,row.get('source',0x0101))
        setup(a5+0xd34,2,0x100);setup(a5+0xd38,2,0x80)
        checkpoints=[] if row.get('flag',0) else [0x47c80] if word==0 else [0x47c80,0x47c8c]
        if row.get('branch'):checkpoints.append(0x47d42)
    wait=row.get('sound_wait',0)
    if wait:
        # Full WORD queue reaches actual byte queue; oldest queuedword0455.
        for at,value in ((a5-0x3276,0),(a5-0x3274,6),(a5-0x328c,2 if wait==2 else 1),(a5-0x328a,0),(a5-0x327e,0x0455),(a5-0x327c,0x0566),(a5-0x327a,0x0677),(a5-0x3278,0x0788)):setup(at,2,value)
    return dict(ram=bytes(ram),pvc=base['pvc'],regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,
        expected_final_a7=sp if row['group']=='upper' else sp+4,bank_base=0x200000,external=0,
        checkpoints=checkpoints,initial_host_writes=writes,group=row['group'],initial_shared_stack=base['initial_shared_stack'],
        return_pc=stop,palette_stack_alias=row.get('palette_stack_alias',False))


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
        elif e['region']=='video':assert e['access']=='write' and a==0x3c0000 and n in (2,4)
        else:assert e['access']=='read' and a==EXTERNAL
    assert bytes(ram)==result['ram_after'] and bytes(pvc)==result['pvc_after']
def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program,continuous);phases=[]
    try:
        obs.prepare(fx)
        def take(label,changes=()):
            obs.mutate(changes)
            remaining=[pc for pc in fx['checkpoints'] if pc not in obs.seen]
            intended=fx['stop_pc'] if continuous or not remaining else remaining[0]
            p=obs.run(allow_guard=row.get('guarded',False))
            if p['guard'] is None and not p['waiting']:assert p['outgoing']['pc']==intended,(row,p['outgoing'],intended)
            p.update(label=label,host_changes=list(changes),stop_pc=intended,carry=None);phases.append(p);return p
        p=take('begin');waits=0
        while p['guard'] is None and p['outgoing']['pc']!=fx['stop_pc']:
            if p['waiting']:
                assert p['outgoing']['pc']==0x3aea,('unexpected_sprite_wait',row,p['outgoing'])
                waits+=1;assert waits<=2
                d1=p['outgoing']['d1']&65535;a5=p['outgoing']['a5'];a7=p['outgoing']['a7']
                saved=fx['initial_a7']-(6 if row['group']=='upper' else 2)
                # Host modifies live savedWORD, flags and counter only; no registers.
                changes=[dict(address=a5+0x5d1f,size=1,value=0),dict(address=a5+0x5d20,size=1,value=0xee),dict(address=saved,size=2,value=0x0f01)]
                before=p
                p=take('hold-live-WORD' if waits==1 else 'low-hold',changes if waits==1 else ())
                assert p['waiting'] and p['outgoing']==before['outgoing'] and p['ram_before']==p['ram_after']
                head=(d1+1)&65535 if row.get('sound_wait')==3 and waits==1 else 0xffff
                changes=[dict(address=a5-0x328c,size=2,value=head)]
                p=take('release-%d'%waits,changes)
                if row.get('sound_wait')==3 and waits==1:assert p['waiting'],('expected_lowwait',row,p['outgoing'])
            else:
                assert p['outgoing']['pc'] in fx['checkpoints']
                p=take('after-checkpoint-%x'%p['outgoing']['pc'])
        if row.get('branch'):
            assert p['outgoing']['pc'] in (0x47d72,0x47d46)
            value=1 if p['outgoing']['pc']==0x47d72 else 2
            for q in phases:
                if q['outgoing']['pc'] in (0x47d42,0x47d72,0x47d46):q['carry']=value
        if row['label']=='rectangle-TRAP-bound':assert p['guard']==dict(problem='unsupported_TRAP',pc=0x3608,opcode=0x4e4f)
        if row['label']=='upper-odd-WORD-guard':assert p['guard']==dict(problem='unsupported_odd_data_access',pc=0x47c76,address=0x10d67f,size=2)
        if row.get('palette_stack_alias'):
            assert p['guard']['problem']=='unsupported_code_target' and p['outgoing']['pc']==0x40a0d
            assert any(e['pc']==0x8d32 and e['address']==0x104e5c and e['bytes']=='00040a0d' for q in phases for e in q['events'])
        if row.get('sound_wait'):
            saved=fx['initial_a7']-(6 if row['group']=='upper' else 2)
            assert any(e['pc']==0x4e2d4 and e['address']==saved and e['bytes']=='0f01' for q in phases for e in q['events'])
        return row,fx,phases
    finally:obs.close()


def compare_control(row,split,control):
    assert split[-1]['guard']==control[-1]['guard']
    assert split[-1]['outgoing']==control[-1]['outgoing']
    assert split[-1]['ram_after']==control[-1]['ram_after']
    assert split[-1]['pvc_after']==control[-1]['pvc_after']
    def flatten(phases):
        pcs=[];events=[];changes=[]
        for p in phases:
            pcs.extend(p['pcs'][:-1]);events.extend(p['events']);changes.extend(p['host_changes'])
        pcs.append(phases[-1]['pcs'][-1]);return pcs,events,changes
    assert flatten(split)==flatten(control)
    actual={p['outgoing']['pc']:(p['outgoing'],p['ram_after'],p['pvc_after']) for p in split if not p['waiting'] and p['outgoing']['pc']!=split[-1]['outgoing']['pc']}
    for phase in control:
        for snapshot in phase['snapshots']:
            registers=snapshot['registers'];assert actual[registers['pc']]==(registers,snapshot['ram'],snapshot['pvc'])
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
            events=p['events'];ports=[e for e in events if e['region'] in ('pvc','video')]
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
            rows.append(dict(label=p['label'],stop_pc=p['stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],waiting=p['waiting'],carry=p['carry'],host_changes=p['host_changes'],modeled_bank=p['modeled_bank'],guard=p['guard'],snapshots=snapshots,
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
        limitations=['Controlled originalHUD/BCD/palette/rectangle/47c6c fixtures, not natural scheduler reachability or whole game completion.',
            'No SR/context reads after init or result injection. Carry leaves unobserved; only actual47d42BCC successor gives retrospective C1Clear/C2Set for upper readiness exits.',
            'Coherent16RAMmirrors, CPU-owned backing, live callerA7/WORD pushes/JSR/RTS, fullRAM/PVC read-write replay, no stackmask.',
            'Fresh continuous controls execute identical original code through checkpoints without intermediate stops; actual sameCPU waits and declared RAM-only hostchanges retained.',
            'Actual kind3 program bytes match canonical ROM. Native bankROM mapping is bank2 only; PVC reads/nonbank2 accesses/TRAP/unsupported targets/alignment/timeouts guarded.',
            'Video3c0000 writes size2/4 recorded as raw ordered ports distinctfromPVC; no complete video-device/framebuffer/timing model.',
            'Prior exhaustive BCD and hardware-reference source0 evidence is separate pinned provenance. Representative raw invalid digits observed here without rerunning all65536.',
            'Palette stack alias actual targetwrite corrupts live JSRreturn to00040a0d, recordedguard not normal success. Guards do not claim nativefault/C++rollback equivalence.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
