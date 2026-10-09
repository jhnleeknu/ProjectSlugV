"""Unpatched post-map fade, timer, frame re-entry and BIOS-card boundary observation.

Native Unicorn M68000 observation of the original ROM from the connected 47fe8
scene/palette/map chain onward: 4804e fade, 4806a/48090 timers, 4809a screen reset,
c364 BIOS-card request (stop boundary c00468; the BIOS body is never executed),
declared BIOS-return resume (c37c), 28ae child allocation, 2a00 cleanup and the
2ab8 dispatcher. No SR reads, ROM patches, stubs, register injection after
execution begins, stack masking or expected-register injection. Every host change is
declared in the step record. This is a native observation, not C++ comparison.
"""
import copy
import ctypes
import json
from pathlib import Path
import struct
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_map_transfer as mt
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
import observe_animation_machine_screen as screen_native
import observe_animation_machine_transition as transition
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_fade_card_native'
RAM,SIZE,PVC,S,RETURN=mt.RAM,mt.SIZE,mt.PVC,mt.S,mt.RETURN
REGS,EXTERNAL,CAP=mt.REGS,mt.EXTERNAL,mt.CAP
sha,put=mt.sha,mt.put
BIOS=0xc00468
DISPATCH_RETURN=0x2ac2
RANGES=mt.RANGES+((0x4804e,0x480bc),(0xc364,0xc3c0),(0x28ae,0x2918),(0x2a00,0x2a0a),(0x2ab8,0x2ac8))
BOUNDARIES=mt.BOUNDARIES+(0x4804e,0x4805e,0x4806a,0x48074,0x48084,0x48090,0x4809a,0x480a0,0x480a6,0x480ac,0x480b6,0xc364,0xc37c,0xc38e,0xc3a2,0xc3b8,0x28ae,0x290e,0x2a00,0x2a02,0x2ab8,0x2ac2)
PORT_REGIONS=('pvc','video','watchdog')
A6_FADE=0x102000
FREE_HEAD,FREE_COUNT,STACK_BASE=0x104c9c,0x104ca0,0x104ca4


class Observer:
    """Persistent CPU; one run() per declared step/phase. Layout follows the map-transfer observer."""
    def __init__(self,program,continuous=False):
        self.program=program;self.cpu=None;self.backing=None;self.continuous=continuous;self.seen=set();self.checkpoints=();self.stop_pc=None
    def regs(self):return {key:self.cpu.reg_read(REGS[key]) for key in shared.isolated.REG_NAMES+('a7','pc')}
    def begin_step(self,stop_pc,checkpoints):self.stop_pc=stop_pc;self.checkpoints=tuple(checkpoints);self.seen=set()
    def prepare(self,fx):
        self.begin_step(fx['stop_pc'],fx['checkpoints'])
        self.backing=(ctypes.c_ubyte*SIZE).from_buffer_copy(fx['ram'])
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._ram_backing=self.backing
        c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        c.mem_map(0,RAM,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(0,self.program[:RAM])
        for i in range(16):c.mem_map_ptr(RAM+i*SIZE,SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        bank,ff8,ff9=fx.get('bank_state',(0x200000,0xa0,0x1000))
        self.bank_backing=(ctypes.c_ubyte*0xfe000).from_buffer_copy(self.program[bank:bank+0xfe000]);c._bank_backing=self.bank_backing
        c.mem_map_ptr(0x200000,0xfe000,unicorn.UC_PROT_READ,ctypes.addressof(self.bank_backing))
        c.mem_map(PVC,8192,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(PVC,fx['pvc'])
        c.mem_map(0x300000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0x3c0000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0xd00000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(EXTERNAL,bytes([fx['external']]))
        self.cpu=c;self.bank=bank;self.ff8=ff8;self.ff9=ff9
        self.boundary_set=set(BOUNDARIES)
        allowed=set()
        for lo,hi in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(self.program,lo,hi-lo,lo))
        assert BIOS not in allowed
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
            if size>1 and address&1:
                # The write hook runs before the store and emu_stop does not cancel it: remember the old bytes so run() can restore them.
                if kind=='write':self.odd_write=(address,bytes(c.mem_read(address,size)))
                stop('unsupported_odd_data_access',address=address,size=size,access=kind);return
            before=bytes(c.mem_read(address,size));data=before if kind=='read' else (value&((1<<(size*8))-1)).to_bytes(size,'big')
            if region in ('video','watchdog'):before=bytes(size)   # write-only device: the emulated page's old bytes are not machine state, normalized to zero
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
        def bad(cpu,access,address,size,value,user):
            if access==unicorn.UC_MEM_FETCH_UNMAPPED:
                # Nothing is mapped at c00468 (BIOS): reaching the declared stop boundary is a clean stop, any other unmapped fetch is a guard.
                self.pcs.append(address)
                if address==self.stop_pc==BIOS and self.pc==0xc376 and self.program[0xc376:0xc37c]==bytes.fromhex('4eb900c00468'):self.fetch_stop=True;cpu.emu_stop();return False
                stop('unsupported_code_target',target=address,unmapped_fetch=True);return False
            stop('unmapped_or_protected',address=address,size=size);return False
        def interrupt(cpu,number,user):stop('CPU_exception',number=number)
        for hook,callback in ((unicorn.UC_HOOK_CODE,code),(unicorn.UC_HOOK_MEM_READ,read),(unicorn.UC_HOOK_MEM_WRITE,write),(unicorn.UC_HOOK_MEM_INVALID,bad),(unicorn.UC_HOOK_INTR,interrupt)):c.hook_add(hook,callback)
        c.reg_write(REGS['sr'],0x2000);c.reg_write(REGS['a7'],fx['initial_a7'])
        for key in shared.isolated.REG_NAMES:c.reg_write(REGS[key],fx['regs'][key])
        c.reg_write(REGS['pc'],fx['entry_pc'])
        return self
    def run(self,allow_guard=False):
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0;self.snapshots=[];self.fetch_stop=False;self.odd_write=None
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        try:self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
        except unicorn.UcError:
            if not self.fetch_stop and (not allow_guard or self.guard is None):raise
        if self.odd_write is not None:
            address,old_bytes=self.odd_write;took=bytes(self.cpu.mem_read(address,len(old_bytes)))!=old_bytes
            self.cpu.mem_write(address,old_bytes)   # undo the unlogged odd store; the guard records that it was attempted
            self.guard.update(odd_write_took_effect_before_restore=took,odd_write_restored=True)
        outgoing=self.regs()
        if not allow_guard:assert self.guard is None,self.guard
        if self.guard is None:assert outgoing['pc']==self.stop_pc or outgoing['pc'] in self.checkpoints,('timeout_or_stop',outgoing)
        if self.fetch_stop:assert outgoing['pc']==self.stop_pc==BIOS and self.guard is None
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=False,snapshots=self.snapshots,guard=self.guard,modeled_bank=self.bank,
            bank_before=bank_before,ff8_before=ff8_before,ff9_before=ff9_before,ff8_after=self.ff8,ff9_after=self.ff9)
        assert bytes(self.cpu.mem_read(0,RAM))==self.program[:RAM]
        assert bytes(self.cpu.mem_read(0x200000,0xfe000))==self.program[self.bank:self.bank+0xfe000]
        assert all(bytes(self.cpu.mem_read(RAM+i*SIZE,SIZE))==bytes(self.backing) for i in range(16))
        mt.replay(self.program,result)
        return result
    def apply(self,changes):
        """Declared host changes: RAM writes, PC redirect, A7 delta. All other registers must be unchanged."""
        before=self.regs();expected=dict(before);done=[]
        for change in changes:
            kind=change['kind']
            if kind=='ram':
                self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
            elif kind=='pc':
                self.cpu.reg_write(REGS['pc'],change['to']);expected['pc']=change['to']
            elif kind=='a7_add':
                expected['a7']=(before['a7']+change['delta'])&0xffffffff;self.cpu.reg_write(REGS['a7'],expected['a7'])
            else:raise AssertionError(kind)
            done.append(dict(change,pc_before=before['pc'],a7_before=before['a7']))
        assert self.regs()==expected
        return done
    def close(self):self.cpu=None;self.backing=None;self.bank_backing=None


# ----------------------------------------------------------------------------------
# Declared-change helpers
# ----------------------------------------------------------------------------------
def ram_write(address,size,value,why):
    assert RAM<=address and address+size<=0x200000,hex(address)
    return dict(kind='ram',address=address,size=size,value=value&((1<<(8*size))-1),why=why)
def pc_to(pc,why):return dict(kind='pc',to=pc,why=why)
def a7_add(delta,why):return dict(kind='a7_add',delta=delta,why=why)

def u(ram,address,size):
    return int.from_bytes(bytes(ram[(address+i)&0xffff] for i in range(size)),'big')


def frame_step(label,stop=DISPATCH_RETURN,checkpoints=(),a7=('entry',0),**extra):
    return dict(label=label,changes=[pc_to(0x2ab8,'frame re-entry: PC only; A6/A7 are the previous real outputs')],stop_pc=stop,checkpoints=list(checkpoints),a7=a7,**extra)


# ----------------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------------
def connected_fixture(program,return_value=DISPATCH_RETURN):
    ram0,out,preparation,prep_fx=mt.prepared(program,1)
    fx=mt.fixture(program,dict(group='connected',label='connected-scene-palette-map-1',entry_pc=0x47fe8,profile=1))
    ram=bytearray(fx['ram']);put(ram,S,4,return_value)
    writes=list(fx['initial_host_writes'])+[dict(address=S,size=4,value=return_value,why='declared callback return LONG at initial A7 (dispatcher return 2ac2 in place of historical ff000)')]
    fx.update(ram=bytes(ram),initial_host_writes=writes,stop_pc=DISPATCH_RETURN,checkpoints=[],expected_final_a7=S+4,bank_state=(0x200000,0xa0,0x1000))
    fx['preparation']=dict(steps=preparation['steps'],role='Only original 3ef2 prepares incoming RAM; scene/palette/map and 4804e..4806a execute in this same mainCPU from 47fe8')
    fx['initial_shared_stack']=dict(fx['initial_shared_stack'],return_value=return_value)
    return fx


def state_fixture(base,phase,pc,label):
    """Fresh CPU from a recorded real output (declared initial state, PC redirected by the declared change)."""
    fx=dict(base);o=phase['outgoing']
    fx.update(ram=phase['ram_after'],pvc=phase['pvc_after'],regs={k:o[k] for k in shared.isolated.REG_NAMES},initial_a7=o['a7'],entry_pc=pc,
        bank_state=(phase['modeled_bank'],phase['ff8_after'],phase['ff9_after']),initial_host_writes=[],
        preparation=dict(role='state copied from %s output'%label,source_pc=o['pc'],declared_pc=pc))
    return fx


# ----------------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------------
def expected_a7(step,first_incoming,phase):
    kind,value=step['a7']
    if kind=='entry':return (first_incoming['a7']+value)&0xffffffff
    if kind=='mem32':return u(phase['ram_after'],value,4)
    raise AssertionError(kind)


def run_condition(program,spec,continuous):
    fx=spec['fixture'];o=Observer(program,continuous);phases=[];allow=bool(spec.get('guarded'))
    try:
        o.prepare(dict(fx,stop_pc=spec['steps'][0]['stop_pc'],checkpoints=spec['steps'][0]['checkpoints']))
        for index,step in enumerate(spec['steps']):
            o.begin_step(step['stop_pc'],step['checkpoints']);first=None;pending=step['changes']
            while True:
                remaining=[pc for pc in step['checkpoints'] if pc not in o.seen]
                target=step['stop_pc'] if continuous or not remaining else remaining[0]
                changes=o.apply(pending);pending=[]
                p=o.run(allow_guard=allow)
                if first is None:first=p['incoming']
                p.update(label=step['label'] if not phases or phases[-1]['step']!=index else '%s+after-%x'%(step['label'],phases[-1]['outgoing']['pc']),step=index,host_changes=changes,stop_pc=target,
                    carry=None,carry_in=(step.get('carry_in') if not any(q['step']==index for q in phases) else None),branch_evidence=[],step_stop_pc=step['stop_pc'],phase_in_step=sum(q['step']==index for q in phases))
                phases.append(p)
                if p['guard'] is not None:break
                assert p['outgoing']['pc']==target,(spec['label'],step['label'],p['outgoing'],hex(target))
                if p['outgoing']['pc']==step['stop_pc']:
                    want=expected_a7(step,first,p);assert p['outgoing']['a7']==want,(spec['label'],step['label'],hex(p['outgoing']['a7']),hex(want))
                    break
                assert p['phase_in_step']<40
            if phases[-1]['guard'] is not None:
                assert allow,(spec['label'],phases[-1]['guard']);assert index==len(spec['steps'])-1
        if allow:check_guard(spec,phases[-1])
        else:assert all(p['guard'] is None for p in phases)
        return phases
    finally:o.close()


def check_guard(spec,p):
    g=p['guard'];assert g is not None,spec['label']
    for key,value in (spec['guard'] or {}).items():assert g.get(key)==value,(spec['label'],key,g)


def compare_steps(split,control):
    steps=sorted({p['step'] for p in split});assert steps==sorted({p['step'] for p in control})
    for index in steps:
        a=[p for p in split if p['step']==index];b=[p for p in control if p['step']==index]
        assert len(b)==1
        screen_native.compare_control(None,a,b)
        assert [p['host_changes'] for p in a][0]==b[0]['host_changes']


# ----------------------------------------------------------------------------------
# Conditions
# ----------------------------------------------------------------------------------
CONNECTED_CK=[0x47ff2,0x48042,0x18424,0x18530,0x185ee,0x48048,0x4804e,0x4805e,0x4806a]
TRANSITION_FRAME=127
LAST_FRAME=158
FRAME_CK={1:[0x4806a],TRANSITION_FRAME:[0x4806a,0x48074,0x48084,0x48090],LAST_FRAME:[0x48090,0x4809a,0x480a0,0xc364]}
KEY_PCS=(0x47fe8,0x4804e,0x4805e,0x4806a,0x4806e,0x48072,0x48074,0x48084,0x48090,0x48094,0x48098,0x4809a,0x480a0,0x480a6,0x480ac,0x480b0,0x480b4,0x480b6,0xc364,0xc37c,0xc38a,0xc38e,0xc3a2,0xc3b8,0x28ae,0x290e,0x2900,0x2a00,0x2a02,0x2ab8,0x2abe,0x2ac0,0x2ac2,0x8c16,0xcaf0,BIOS)
CLEAN=[ram_write(A6_FADE+0x10,2,0,'cleanup fixture: depth 0 (no child loop at 29b6)'),ram_write(A6_FADE+0x1d,1,0,'cleanup fixture: palette-reference count 0'),
    ram_write(A6_FADE+0x6c,1,0xff,'cleanup fixture: no coordinate slot'),ram_write(STACK_BASE,4,S+4,'dispatcher base A7 = A7 at frame entry (S+4)')]


def alloc_setup(count=3,head=0x104800,nxt=0x104900,sibling=0x103000,depth=3):
    writes=[ram_write(FREE_COUNT,2,count,'28ae free count'),ram_write(FREE_HEAD,4,head,'28ae free-list head')]
    if head:writes.append(ram_write(head+8,4,nxt,'8(head): next free'))
    return writes+[ram_write(A6_FADE+8,4,sibling,'parent 8(A6) sibling'),ram_write(A6_FADE+0x10,2,depth,'parent depth 10(A6)')]


def frame_steps(count_from,count_to,checkpoints=FRAME_CK):
    steps=[]
    for i in range(count_from,count_to+1):
        last=i==LAST_FRAME
        steps.append(frame_step('frame-%03d'%i,stop=BIOS if last else DISPATCH_RETURN,checkpoints=checkpoints.get(i,[]),a7=('entry',-16 if last else 0)))
    return steps


def step_end(phases,index):
    return [p for p in phases if p['step']==index][-1]


def bios_step(answer,extra=(),checkpoints=(),a7=('entry',12),stop=DISPATCH_RETURN):
    changes=[pc_to(0xc37c,'BIOS RTS effect: PC=c37c'),a7_add(4,'BIOS RTS effect: A7+=4 (pop of c37c)'),ram_write(0x10fdc6,1,answer,'declared BIOS answer BYTE at 10fdc6')]+list(extra)
    return dict(label='bios-resume-answer-%02x'%answer,carry_in='Unknown',carry_in_reason='BIOS c00468 CCR effect is unmodeled/unknown; SR is never read',changes=changes,stop_pc=stop,checkpoints=list(checkpoints),a7=a7)


def conditions(program,connected,chain_phases):
    """Derived conditions; all start from the real chain outputs. Returns list of condition specs."""
    specs=[];base_connected=connected
    end0=step_end(chain_phases,0);end126=step_end(chain_phases,TRANSITION_FRAME-1);end127=step_end(chain_phases,TRANSITION_FRAME);end157=step_end(chain_phases,LAST_FRAME-1);endlast=step_end(chain_phases,LAST_FRAME)
    for end in (end0,end126,end127,end157):assert end['outgoing']['pc']==DISPATCH_RETURN
    assert endlast['outgoing']['pc']==BIOS
    def fresh(label,end,end_label,steps,group,provenance,**extra):
        fx=state_fixture(base_connected,end,end['outgoing']['pc'],end_label)
        specs.append(dict(label=label,group=group,fixture=fx,steps=steps,provenance=provenance,**extra))
    # fresh representative frames (equal to the chain frames)
    for number,end,end_label in ((1,end0,'chain step 0 (connected)'),(TRANSITION_FRAME,end126,'chain step 126'),(LAST_FRAME,end157,'chain step 157')):
        fresh('fresh-frame-%03d'%number,end,end_label,frame_steps(number,number),'fresh-frame','fresh CPU started from the recorded real output of '+end_label+'; only declared change is PC=2ab8',chain_frame=number)
    # timer boundaries
    w7a=lambda v,why:ram_write(A6_FADE+0x7a,2,v,why)
    def timer(label,end,end_label,value,checkpoints,last=False):
        step=frame_step('timer-7a-%04x'%value,stop=BIOS if last else DISPATCH_RETURN,checkpoints=checkpoints,a7=('entry',-16 if last else 0))
        step['changes'].append(w7a(value,'declared host change: 7a(A6) WORD'))
        fresh(label,end,end_label,[step],'timer-boundary','fresh state from '+end_label+'; declared host changes: PC=2ab8 and 7a(A6) WORD=%04x'%value)
    timer('timer1-7a-0000-wrap',end0,'chain step 0',0,[0x4806a])
    timer('timer1-7a-0001-expire',end0,'chain step 0',1,FRAME_CK[TRANSITION_FRAME])
    timer('timer1-7a-0100-word-only',end0,'chain step 0',0x100,[0x4806a])
    timer('timer2-7a-0000-wrap',end127,'chain step 127',0,[0x48090])
    timer('timer2-7a-0001-expire',end127,'chain step 127',1,FRAME_CK[LAST_FRAME],last=True)
    fresh('transition-frame-127-D3-high-word',end126,'chain step 126',frame_steps(TRANSITION_FRAME,TRANSITION_FRAME),'timer-boundary',
        'fresh state from chain step 126 with a declared initial D3=abcd1234 at the fresh start (not injected after begin): 4807a MOVE.W #20,D3 must preserve the high WORD')
    specs[-1]['fixture']['regs']=dict(specs[-1]['fixture']['regs'],d3=0xabcd1234)
    # BIOS resume from the c00468 stop
    def bios(label,answer,group,provenance,extra=(),ck=(),a7=('entry',12),follow=True,**kw):
        steps=[bios_step(answer,extra,ck,a7)]
        if follow:steps.append(frame_step('followup-frame-480ac',checkpoints=[0x480ac]))
        fresh(label,endlast,'chain step %d (stop c00468)'%LAST_FRAME,steps,group,provenance,**kw)
    SUCCESS_CK=[0xc38e,0x28ae,0xc3a2,0x480a6]
    bios('bios-answer-80',0x80,'bios-80','declared BIOS return (PC=c37c, A7+=4, 10fdc6=80) plus declared cleanup-object fixture; 62=ff path through 2a00/299c/2a02',
        extra=CLEAN,ck=[0xc3b8,0x480a6,0x480b6,0x2a00,0x2a02],a7=('mem32',STACK_BASE),follow=False)
    for answer in (0x00,0x01,0x7f,0x81,0xff):
        bios('bios-answer-%02x-alloc'%answer,answer,'bios-alloc','declared BIOS return + declared 28ae pool/parent fixture; follow-up frame at 480ac',extra=alloc_setup(),ck=SUCCESS_CK)
    bios('bios-alloc-last-free',0x00,'bios-alloc','declared BIOS return + pool with one free entry',extra=alloc_setup(count=1),ck=SUCCESS_CK)
    bios('bios-alloc-depth-ffff',0x00,'bios-alloc','declared BIOS return + parent depth 10(A6)=ffff (D0.W wraps to 0)',extra=alloc_setup(depth=0xffff),ck=SUCCESS_CK)
    bios('bios-fail-count0',0x00,'bios-fail','declared BIOS return + 104ca0=0: unsigned D0.W(0)>=count -> 290e',extra=alloc_setup(count=0),ck=[0xc38e,0x28ae,0x290e,0xc3a2,0x480a6])
    bios('bios-fail-count0-answer-ff',0xff,'bios-fail','same as bios-fail-count0 with answer ff',extra=alloc_setup(count=0),ck=[0xc38e,0x28ae,0x290e,0xc3a2,0x480a6])
    # 28ae live aliases (earlier write changes a later operand)
    bios('bios-alloc-alias-child-over-parent-10',0x00,'bios-alias','head = A6+4: c(A0)=A6 lands on 10(A6), so D0.W=10(A6)+1 reads the written high WORD',
        extra=alloc_setup(head=A6_FADE+4),ck=SUCCESS_CK)
    bios('bios-alloc-alias-child-over-parent-8',0x00,'bios-alias','head = A6-4: c(A0)=A6 lands on 8(A6), so A1=8(A6) reads A6 itself',extra=alloc_setup(head=A6_FADE-4),ck=SUCCESS_CK)
    bios('bios-alloc-alias-pushed-A0',0x00,'bios-alias','head = (A7 after push of A0) - 0xc and parent depth ffff: c(A0)=A6 overwrites the pushed A0 slot, 10(A0)=0000 leaves the return LONG intact, the later pop returns A6',
        extra=alloc_setup(head=endlast['outgoing']['a7']-0xc,depth=0xffff),ck=SUCCESS_CK)
    replaced=0x103400
    bios('bios-alloc-saved-A6-replaced',0x00,'bios-alias','declared RAM write replaces the pushed A6 slot (live pop at c37c) by an object at 103400',
        extra=[ram_write(endlast['outgoing']['a7']+4,4,replaced,'replace saved A6 slot'),ram_write(replaced+8,4,0x103800,'replacement parent 8(A6)'),ram_write(replaced+0x10,2,5,'replacement parent depth'),
            ram_write(FREE_COUNT,2,3,'28ae free count'),ram_write(FREE_HEAD,4,0x104800,'28ae free-list head'),ram_write(0x104808,4,0x104900,'8(head)')],ck=SUCCESS_CK)
    # guards
    def guard_fresh(label,end,end_label,steps,guard,provenance,regs=None):
        fx=state_fixture(base_connected,end,end['outgoing']['pc'],end_label)
        if regs:
            regs=dict(regs)
            if 'a7' in regs:fx['initial_a7']=regs.pop('a7')
            fx['regs']=dict(fx['regs'],**regs)
        specs.append(dict(label=label,group='guard',guarded=True,guard=guard,fixture=fx,steps=steps,provenance=provenance))
    guard_fresh('guard-odd-A6',end0,'chain step 0',[frame_step('frame',a7=('entry',0))],dict(problem='unsupported_odd_data_access',pc=0x2abe,address=A6_FADE+1,size=4),
        'fresh state from chain step 0 with declared initial A6 register odd (102001); MOVEA.L (A6),A0 at 2abe',regs=dict(a6=A6_FADE+1))
    guard_fresh('guard-odd-A7-push',end0,'chain step 0',[frame_step('frame',a7=('entry',0))],dict(problem='unsupported_odd_data_access',pc=0x2ac0,address=0x1ff001-4,size=4,access='write',odd_write_restored=True),
        'fresh state from chain step 0 with declared initial A7=1ff001 (odd); JSR (A0) at 2ac0 pushes the return LONG to an odd address (write-first odd access)',regs=dict(a7=0x1ff001))
    step=frame_step('frame-odd-callback');step['changes'].append(ram_write(A6_FADE,4,0x4806b,'declared odd callback pointer'))
    guard_fresh('guard-odd-callback-target',end0,'chain step 0',[step],dict(problem='unsupported_code_target',pc=0x4806b,target=0x4806b),'fresh state from chain step 0 with (A6)=4806b; JSR (A0) at 2ac0')
    step=frame_step('frame-480bc');step['changes'].append(ram_write(A6_FADE,4,0x480bc,'declared callback pointer into the out-of-scope 480bc frame helper'))
    guard_fresh('guard-callback-480bc',end0,'chain step 0',[step],dict(problem='unsupported_code_target',pc=0x480bc,target=0x480bc),'fresh state from chain step 0 with (A6)=480bc')
    step=frame_step('frame-past-c00468',stop=DISPATCH_RETURN,checkpoints=[0x48090,0x4809a,0x480a0,0xc364],a7=('entry',-16))
    guard_fresh('guard-past-c00468',end157,'chain step 157',[step],dict(problem='unsupported_code_target',pc=0xc376,target=BIOS,unmapped_fetch=True),
        'last timer frame with stop 2ac2 instead of c00468: executing past the BIOS boundary is attempted and refused')
    bios('guard-alloc-return-clobbered',0x00,'guard','same pushed-A0 alias with depth 3: MOVE.W D0,10(A0) overwrites the high WORD of the 28ae return LONG (c3a2 -> 0004c3a2); RTS then targets unsupported code',
        extra=alloc_setup(head=endlast['outgoing']['a7']-0xc,depth=3),ck=[0xc38e,0x28ae],follow=False,guarded=True,guard=dict(problem='unsupported_code_target',pc=0x4c3a2,target=0x4c3a2))
    bios('guard-alloc-head-zero',0x00,'guard','declared BIOS return + free-list head 104c9c=0: 8(A0) reads ROM address 8, c(A0)=A6 writes ROM address c (native fault, partial effects)',
        extra=alloc_setup(head=0),ck=[0xc38e,0x28ae],follow=False,guarded=True,
        guard=dict(problem='unmapped_or_protected',pc=0x28de,address=0xc,size=4))
    return specs


# ----------------------------------------------------------------------------------
# Storage, audit and report
# ----------------------------------------------------------------------------------
def counts(events):
    c=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
    for e in events:
        r=e['region']
        if r=='ram':c['ram_reads' if e['access']=='read' else 'ram_writes']+=1
        elif r=='bank':c['bank_reads']+=1
        elif r=='fixed':c['fixed_reads']+=1
        elif r=='external':c['external_reads']+=1
        else:c[r]+=1
    return c


def summarize(spec,fx):
    meta={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')}
    meta['initial_regs']=fx['regs'];meta['initial_RAM_sha256']=sha(fx['ram']);meta['initial_PVC_sha256']=sha(fx['pvc'])
    return json.loads(json.dumps(meta,default=lambda x:list(x) if isinstance(x,tuple) else str(x)))


def store(prefix,phases):
    rows=[]
    for j,p in enumerate(phases):
        stem='%s_phase_%03d'%(prefix,j);events=p['events'];ports=[e for e in events if e['region'] in PORT_REGIONS]
        payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
            stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
            stem+'_trace.json':(json.dumps({k:p[k] for k in ('pcs','events','boundaries','guard')},indent=2)+'\n').encode()}
        snapshots=[]
        for k,snapshot in enumerate(p['snapshots']):
            names={}
            for field in ('ram','pvc'):
                name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
            snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
        hashes={}
        for name,data in payloads.items():(OUT/name).write_bytes(data);hashes[name]=sha(data)
        rows.append(dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
            host_changes=p['host_changes'],carry_in=p['carry_in'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
            waiting=p['waiting'],carry=p['carry'],branch_evidence=p['branch_evidence'],guard=p['guard'],snapshots=snapshots,counts=counts(events),
            key_pcs=[pc for pc in p['pcs'] if pc in KEY_PCS],pc_count=len(p['pcs']),artifacts=hashes))
    return rows


def step_summary(spec):
    return [dict(label=s['label'],carry_in=s.get('carry_in'),stop_pc=s['stop_pc'],checkpoints=s['checkpoints'],a7_expectation=list(s['a7']),declared_changes=s['changes']) for s in spec['steps']]


def run_twice(program,spec):
    split,fixed_split=run_condition(program,spec,False),None
    assert split==run_condition(program,spec,False),spec['label']
    control=run_condition(program,spec,True)
    assert control==run_condition(program,spec,True),spec['label']
    compare_steps(split,control)
    return split,control


def audit_return_slot(program):
    """The initial callback LONG at S is only consumed by the final RTS: historical ff000 and dispatcher 2ac2 runs differ only there."""
    a=connected_fixture(program,DISPATCH_RETURN);b=connected_fixture(program,RETURN)
    runs=[]
    for fx,stop in ((a,DISPATCH_RETURN),(b,RETURN)):
        spec=dict(label='audit',fixture=fx,steps=[dict(label='connected',changes=[],stop_pc=stop,checkpoints=[],a7=('entry',4))])
        runs.append(run_condition(program,spec,True)[0])
    x,y=runs;mask=lambda r:r[:0xeffc]+r[0xf000:]
    assert mask(x['ram_after'])==mask(y['ram_after']) and x['pvc_after']==y['pvc_after']
    assert x['pcs'][:-1]==y['pcs'][:-1] and x['outgoing']['pc']==DISPATCH_RETURN and y['outgoing']['pc']==RETURN
    assert [e for e in x['events'] if e['address']!=S]==[e for e in y['events'] if e['address']!=S]
    return dict(equal_except_S_slot=True,S=S,S_after_2ac2=x['ram_after'][0xeffc:0xf000].hex(),S_after_ff000=y['ram_after'][0xeffc:0xf000].hex(),
        regs_equal_except_pc=all(x['outgoing'][k]==y['outgoing'][k] for k in x['outgoing'] if k!='pc'))


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():old.unlink()
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),ROOT/'docs/analysis/animation-machine-fade-card-contract.md',ROOT/'docs/analysis/animation-machine-map-transfer-contract.md'}
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0)
    audit=audit_return_slot(program)
    connected=connected_fixture(program)
    steps=[dict(label='connected-47fe8',changes=[],stop_pc=DISPATCH_RETURN,checkpoints=CONNECTED_CK,a7=('entry',4))]+frame_steps(1,LAST_FRAME)
    chain=dict(label='chain-47fe8-to-c00468',group='chain',fixture=connected,steps=steps,provenance='connected 47fe8 fixture (callback return LONG 2ac2 declared at S) then %d frame re-entries (PC=2ab8 only) to the c00468 stop'%LAST_FRAME)
    connected_only=dict(label='connected-47fe8-to-2ac2',group='connected',fixture=connected,steps=steps[:1],provenance='connected 47fe8 scene/palette/map chain continued through 4804e fade and 4806a RTS')
    chain_split,chain_control=run_twice(program,chain)
    specs=[connected_only,chain]+conditions(program,connected,chain_split)
    cache={chain['label']:(chain_split,chain_control)}
    for number,spec in enumerate(specs):
        split,control=cache.get(spec['label']) or run_twice(program,spec)
        if spec['group']=='fresh-frame':   # fresh start from the recorded state equals the long-lived chain frame
            frame=spec['chain_frame'];original=[p for p in chain_split if p['step']==frame]
            assert len(original)==len(split),spec['label']
            for a,b in zip(split,original):
                for key in ('incoming','outgoing','ram_before','ram_after','pvc_before','pvc_after','pcs','events','boundaries','snapshots','modeled_bank','bank_before','ff8_before','ff9_before','ff8_after','ff9_after','stop_pc','guard'):
                    assert a[key]==b[key],(spec['label'],a['label'],key)
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=summarize(spec,spec['fixture']),steps=step_summary(spec),
            phases=store('c%03d_split'%number,split),continuous_control=store('c%03d_control'%number,control),reproduced_twice=True,continuous_split_equivalent=True)
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else ''),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,boundary_stop_pc=BIOS),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    def aggregate(rows):
        t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
        for r in rows:
            for ph in r['phases']:
                for k,v in ph['counts'].items():t[k]+=v
        return t
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=len(specs)*4,normal_totals=aggregate(results),guard_totals=aggregate(guards),
        return_slot_audit=audit,covered_PCs=sorted(coverage),failure=None,rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; frame re-entry is a declared PC-only change (A6 stays the previous real object; no other object callbacks, IRQ or VBlank).',
            'c00468 (BIOS) is a stop boundary only: never executed, nothing mapped there. The BIOS resume is a declared host change (PC=c37c, A7+=4, BYTE 10fdc6); other BIOS effects (card RAM, register clobber) are unmodeled/unknown.',
            'Declared RAM fixtures (cleanup object fields, 28ae pool/parent fields, 104ca4 base A7) are inputs, not original-measured preparation; scene/palette/map/fade/timer/screen-reset run natively from 47fe8.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native carry is unobserved (SR never read); 28ae ORI/ANDI CCR writers are source-known only.',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
