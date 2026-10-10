"""Unpatched card menu YES selection (c1c4 event 3 -> bd26 card save with three BIOS boundaries -> 9f36/a71a result menu push) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the card menu input and close observers
(observe_animation_machine_card_menu_input, observe_animation_machine_card_menu_close) and through them the open / push / card child / fade-card observers:
the BIOS-resume chain is re-derived to the a29c stop, a29c to the a370 stop, the open unit frames and the first input frame of the input unit (cursor 3 = NO, e=ff,
7e(A6)=012b).  That real output is continued by declared PC=2ab8 frame re-entries (A6 = card child, (A6) = c2ba) with declared input bytes:
frame 2 P1 bit0 (up: cursor 3 -> 2 = YES, c1c4 event 0), frame 3 P1 bit4 (select: event 3 -> c1c4 -> c1de D0.W==3 -> BSR bd26: name copy bbb8, checksum bb74 over
107f1c..107f31 -> 107f32, BIOS parameter bytes 10fdc4/10fdce/10fdd0, JSR c00468 stop #1), declared BIOS resume #1 (PC=bd60, A7+=4) -> BIOS parameter bytes
10fdc4/10fdce/10fdd0/10fdc8/10fdcc, JSR c00468 stop #2, declared resume #2 (PC=bd90, A7+=4) -> be0c BYTE 10fdc2, JSR c0046e stop #3, declared resume #3
(PC=be1c, A7+=4, BYTE 10fdc6 = 0 SAVE OK / <> 0 NO SAVE) -> be24 TST.B / be2e ORI CCR #1 or be34 ANDI CCR #fe -> c1ea BCC -> 9f36 -> a71a -> a0a0 nested push of
the result descriptor c214/c232 (a0f8 -ee <- 107efe, 9b58, a100 BSR 9e1a redraw of the old menu, new record 107eee) -> 3af8(1adb) -> c212 RTS -> ... -> 2ac2.
BIOS c00468 (twice) and c0046e are stops only: never executed, nothing mapped there; a stop is accepted only directly after the JSR at bd5a / bd8a / be16.
Host changes (all declared in the step record): PC=2ab8 re-entries, the input BYTE fixtures 104cba/104cc0 (and 10fdb6/10fdb7 in frame 1 as the input observer),
the BIOS resumes (PC = JSR return, A7 += 4, BYTE 10fdc6) and fixture RAM writes of fresh conditions.  Fresh conditions start from recorded real chain outputs with
declared host changes (RAM writes, PC redirect, initial registers); nothing is injected after execution begins.  The carry that the BIOS leaves is Unknown
(SR is never read); be2e / be34 carry is evidenced by the executed PC path only.
No SR reads, ROM patches, stubs, register injection after execution begins, stack masking or expected-register injection.
This is a native observation, not a C++ comparison.  An independent Python model of the contract (not of the C++) is compared with the native results;
any difference is recorded in contract_discrepancies.
"""
import copy
import ctypes
import json
import os
from pathlib import Path
import struct
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_card_menu_input as inp
import observe_animation_machine_card_menu_close as cl
import observe_animation_machine_card_menu_open as op
import observe_animation_machine_card_menu as menu
import observe_animation_machine_card_child as cc
import observe_animation_machine_fade_card as fc
import observe_animation_machine_map_transfer as mt
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_menu_save_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-save-contract.md'
CONTRACT_SHA='d8d67ebb51671e4603cc8632268dedfb4e94bd0cb89fbd71354231f269b72a79'
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=cc.u32
u8,u16=op.u8,op.u16
DISPATCH=0x2ac2
BIOS1,BIOS3=0xc00468,0xc0046e
JSR1,JSR2,JSR3=0xbd5a,0xbd8a,0xbe16
BD26,BD34,BD3C,BD60,BD90,BE0C,BE1C,C1EA=0xbd26,0xbd34,0xbd3c,0xbd60,0xbd90,0xbe0c,0xbe1c,0xc1ea
A2R=op.A2                         # record 107efe (first/only menu record of the chain)
TOPREC=0x107eee                   # new (result) record
F2,EE,E5=0x107f0e,0x107f12,op.E5
NAME,CHK,TAIL=0x107f1c,0x107f32,0x107f30
BIOS_AREA=0x10fdc2                # 10fdc2..10fdd1 BIOS parameter bytes
B_C6=0x10fdc6
RESULT_OK,RESULT_NO=0xc214,0xc232
SRC_NAME=0xbb8e
SCRATCH=0x10e000                  # declared scratch RAM of direct-entry fixtures (not used by the recorded chain)

# ----------------------------------------------------------------------------------
# Ranges: the input unit's executable set plus exactly the contract table
# ----------------------------------------------------------------------------------
SAVE_RANGES=((0x9f36,0x9f78),(0xa71a,0xa72c),(0xbb74,0xbb8e),(0xbbb8,0xbbd4),(0xbd26,0xbd96),(0xbe0c,0xbe3a))
RANGES=inp.RANGES+SAVE_RANGES
SAVE_BLOCK_TEXT='9f36 9f48 9f4e 9f50 a100 a71a a720 a72a bb74 bb76 bb82 bb84 bb8c bbb8 bbba bbc0 bbc4 bbca bbd0 bd26 bd34 bd3c bd60 bd90 be0c be1c be2e be34 c1ea'
SAVE_BLOCKS=tuple(int(x,16) for x in SAVE_BLOCK_TEXT.split())
assert len(SAVE_BLOCKS)==len(set(SAVE_BLOCKS))==29
BLOCKS=tuple(sorted(set(inp.BLOCKS)|set(SAVE_BLOCKS)))
BLOCK_SET=frozenset(BLOCKS)
EXTRA_KEY=(0xc1ee,0xc202,0xc212,0xa0a0,0xa0f8,0xa104,0xa1d6,0xa1e0,0x9b58,0x9e1a,0xa5ce,0xc2c0,BIOS1,BIOS3,0x3af8)
RET9F36=(0xc1f4,0xc208)          # returns of JSR 9f36 at c1ee (SAVE OK) / c202 (NO SAVE): registers of 9f36 are recorded here
BOUNDARIES=inp.BOUNDARIES+tuple(pc for pc in SAVE_BLOCKS+RET9F36 if pc not in inp.BOUNDARIES)
KEY_PCS=inp.KEY_PCS+tuple(pc for pc in SAVE_BLOCKS+EXTRA_KEY+RET9F36 if pc not in inp.KEY_PCS)
# FETCH-stop table: BIOS target -> {JSR instruction PC: return PC}.  c376 is the JSR of the fade/card unit (re-derived prefix chain only).
FETCH_SITES={BIOS1:{JSR1:BD60,JSR2:BD90,0xc376:0xc37c},BIOS3:{JSR3:BE1C}}
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
op.PHASE_LIMIT=6000
PORT_REGIONS=fc.PORT_REGIONS
INPUT_REPORT=cl.INPUT_REPORT
DISCREPANCIES=[]
INFO=[]
ALLOWED={}


def allowed_pcs(program):
    key=tuple(fc.RANGES)
    if key not in ALLOWED:
        allowed=set()
        for lo,hi in key:allowed.update(r['cpu_address'] for r in disassemble_range(program,lo,hi-lo,lo))
        ALLOWED[key]=frozenset(allowed)
    return ALLOWED[key]


# ----------------------------------------------------------------------------------
# Observer: the close observer (declared register changes at step boundaries) with the BIOS fetch stop generalised from "c00468 after the JSR at c376"
# to the three JSR sites of this unit.  prepare()/run() are copies of fade_card.Observer with exactly two differences (marked FETCH): the
# unmapped-fetch handler and the final fetch-stop assertion.  Nothing is mapped at c00468/c0046e; the BIOS bodies are never executed.
# ----------------------------------------------------------------------------------
class SaveObserver(cl.CloseObserver):
    def prepare(self,fx):
        self.begin_step(fx['stop_pc'],fx['checkpoints'])
        self.backing=(ctypes.c_ubyte*fc.SIZE).from_buffer_copy(fx['ram'])
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._ram_backing=self.backing
        c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        RAM,SIZE,PVC,EXTERNAL,REGS=fc.RAM,fc.SIZE,fc.PVC,fc.EXTERNAL,fc.REGS
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
        self.boundary_set=set(fc.BOUNDARIES)
        allowed=allowed_pcs(self.program)
        assert not any(k in allowed for k in FETCH_SITES)
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
                self.boundaries.append(dict(pc=pc,registers=self.regs(),stack_address=fc.S-40,stack=bytes(cpu.mem_read(fc.S-40,44)).hex()))
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
                if kind=='write':self.odd_write=(address,bytes(c.mem_read(address,size)))
                stop('unsupported_odd_data_access',address=address,size=size,access=kind);return
            before=bytes(c.mem_read(address,size));data=before if kind=='read' else (value&((1<<(size*8))-1)).to_bytes(size,'big')
            if region in ('video','watchdog'):before=bytes(size)
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
                self.pcs.append(address)
                sites=FETCH_SITES.get(address)      # FETCH: accepted only for the declared stop PC, directly after a JSR abs.L at one of the declared sites
                if sites is not None and address==self.stop_pc and self.pc in sites and self.program[self.pc:self.pc+6]==bytes.fromhex('4eb9')+address.to_bytes(4,'big'):
                    self.fetch_stop=True;cpu.emu_stop();return False
                stop('unsupported_code_target',target=address,unmapped_fetch=True);return False
            stop('unmapped_or_protected',address=address,size=size);return False
        def interrupt(cpu,number,user):stop('CPU_exception',number=number)
        for hook,callback in ((unicorn.UC_HOOK_CODE,code),(unicorn.UC_HOOK_MEM_READ,read),(unicorn.UC_HOOK_MEM_WRITE,write),(unicorn.UC_HOOK_MEM_INVALID,bad),(unicorn.UC_HOOK_INTR,interrupt)):c.hook_add(hook,callback)
        c.reg_write(REGS['sr'],0x2000);c.reg_write(REGS['a7'],fx['initial_a7'])
        for key in shared.isolated.REG_NAMES:c.reg_write(REGS[key],fx['regs'][key])
        c.reg_write(REGS['pc'],fx['entry_pc'])
        return self
    def run(self,allow_guard=False):
        RAM=fc.RAM;SIZE=fc.SIZE;PVC=fc.PVC
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0;self.snapshots=[];self.fetch_stop=False;self.odd_write=None
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        try:self.cpu.emu_start(incoming['pc'],0xffffff,count=fc.CAP)
        except unicorn.UcError:
            if not self.fetch_stop and (not allow_guard or self.guard is None):raise
        if self.odd_write is not None:
            address,old_bytes=self.odd_write;took=bytes(self.cpu.mem_read(address,len(old_bytes)))!=old_bytes
            self.cpu.mem_write(address,old_bytes)
            self.guard.update(odd_write_took_effect_before_restore=took,odd_write_restored=True)
        outgoing=self.regs()
        if not allow_guard:assert self.guard is None,self.guard
        if self.guard is None:assert outgoing['pc']==self.stop_pc or outgoing['pc'] in self.checkpoints,('timeout_or_stop',outgoing)
        if self.fetch_stop:assert outgoing['pc']==self.stop_pc and outgoing['pc'] in FETCH_SITES and self.guard is None     # FETCH
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=False,snapshots=self.snapshots,guard=self.guard,modeled_bank=self.bank,
            bank_before=bank_before,ff8_before=ff8_before,ff9_before=ff9_before,ff8_after=self.ff8,ff9_after=self.ff9)
        assert bytes(self.cpu.mem_read(0,RAM))==self.program[:RAM]
        assert bytes(self.cpu.mem_read(0x200000,0xfe000))==self.program[self.bank:self.bank+0xfe000]
        assert all(bytes(self.cpu.mem_read(RAM+i*SIZE,SIZE))==bytes(self.backing) for i in range(16))
        mt.replay(self.program,result)
        return result


fc.Observer=SaveObserver
reentry=op.reentry
wr=fc.ram_write


# ----------------------------------------------------------------------------------
# Stop evidence: a BIOS stop is accepted only directly after the JSR abs.L at its declared site; other stops as the close / input observers
# ----------------------------------------------------------------------------------
def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc==p['step_stop_pc'] and pc in FETCH_SITES:
        assert len(pcs)>=2 and pcs[-1]==pc,(p['label'],pcs[-3:])
        prev=pcs[-2];sites=FETCH_SITES[pc];ram=p['ram_after']
        assert prev in sites and program[prev:prev+6]==bytes.fromhex('4eb9')+pc.to_bytes(4,'big'),(p['label'],hex(prev),program[prev:prev+6].hex())
        assert u32(ram,o['a7'])==sites[prev],(p['label'],hex(u32(ram,o['a7'])))
        extra=''
        if prev!=0xc376:
            assert u32(ram,o['a7']+4)==o['a6'],(p['label'],hex(u32(ram,o['a7']+4)),hex(o['a6']))
            extra='; saved A6 (%x) at A7+4 (MOVE.L A6,-(A7) before the JSR)'%o['a6']
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,
            reached_from='JSR %x.l at %x (bytes %s) after the BIOS parameter BYTE/WORD stores; return LONG %x on the stack at A7=%x%s; the BIOS body is not executed (nothing is mapped there)'%(pc,prev,program[prev:prev+6].hex(),sites[prev],o['a7'],extra))
    return cl.stop_evidence(program,p)


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Storage (same rows/artifact names as the input / close observers; identical payloads are hard-linked)
# ----------------------------------------------------------------------------------
POOL={}


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def store(prefix,phases,min_step=0):
    rows=[]
    for j,p in enumerate(phases):
        if p['step']<min_step:continue
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
        hashes={name:write_payload(name,data) for name,data in payloads.items()}
        rows.append(dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
            host_changes=p['host_changes'],carry_in=p['carry_in'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
            waiting=p['waiting'],carry=p['carry'],branch_evidence=p['branch_evidence'],guard=p['guard'],snapshots=snapshots,counts=fc.counts(events),
            key_pcs=[pc for pc in p['pcs'] if pc in KEY_PCS],pc_count=len(p['pcs']),artifacts=hashes,stop_evidence=p['stop_evidence']))
    return rows


# ----------------------------------------------------------------------------------
# Checkpoint probe (first hit of each contract block start per step, entry PC excluded), same rule as the open / input / close observers
# ----------------------------------------------------------------------------------
def with_checkpoints(program,spec,first=0):
    probe=copy.deepcopy(spec)
    for s in probe['steps'][first:]:s['checkpoints']=[]
    try:phases=fc.run_condition(program,probe,True)
    except Exception as e:
        diag=copy.deepcopy(probe);diag['guarded']=True;diag['guard']={}
        try:last=fc.run_condition(program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
        except Exception as e2:info=repr(e2)
        raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(spec['label'],e,info))
    for index,step in enumerate(spec['steps']):
        if index<first:continue
        if index>=len(phases):break
        order=[];entry=phases[index]['pcs'][0]
        for pc in phases[index]['pcs'][1:]:
            if pc in BLOCK_SET and pc not in order and pc!=entry:order.append(pc)
        step['checkpoints']=order
    return spec


# ----------------------------------------------------------------------------------
# Declared steps
# ----------------------------------------------------------------------------------
def frame1_step():
    """The input unit's first input frame (cursor 3 = NO, hook: 7e 012c -> 012b, d(A2)=1 from 10fdb6=1): declared re-entry + card bytes 10fdb6/10fdb7 + input bytes 104cba/104cc0 = 00."""
    return dict(label='input-f001',changes=[reentry()]+inp.card_writes(1,0,'frame 1 card bytes')+inp.input_writes(0,0,'frame 1'),stop_pc=DISPATCH,checkpoints=[],a7=('entry',0))


def input_step(label,p1,p2,why,stop=DISPATCH,off=0,extra=()):
    return dict(label=label,changes=[reentry()]+inp.input_writes(p1,p2,why)+list(extra),stop_pc=stop,checkpoints=[],a7=('entry',off))


def bios_resume(label,ret_pc,stop,off,extra=(),why=''):
    return dict(label=label,carry_in='Unknown',carry_in_reason='BIOS c00468/c0046e CCR effect is unmodeled/unknown; SR is never read',
        changes=[fc.pc_to(ret_pc,'BIOS RTS effect: PC=%x (the JSR return)%s'%(ret_pc,why)),fc.a7_add(4,'BIOS RTS effect: A7+=4 (pop of the JSR return LONG)')]+list(extra),stop_pc=stop,checkpoints=[],a7=('entry',off))


def answer_write(v):return wr(B_C6,1,v,'declared BIOS answer BYTE at 10fdc6 = %02x (0: SAVE OK, <> 0: NO SAVE)'%v)


def chain_steps(answer=0,p1_sel=0x10):
    """frames 2..: up (cursor YES), select (-> stop c00468 #1), resume #1 (-> stop c00468 #2), resume #2 (-> stop c0046e), resume #3 (-> 2ac2).  Offsets from the A7 at frame entry / at the resume."""
    return [input_step('save-f002-up',1,0,'frame 2: P1 bit0 (up) moves the cursor 3 -> 2 (YES)'),
        input_step('save-f003-select',p1_sel,0,'frame 3: P1 bit4 (select): event 3 -> c1c4 -> BSR bd26 -> JSR c00468 #1',stop=BIOS1,off=-28),
        bios_resume('save-bios1-resume',BD60,BIOS1,-4,why=' (bd60)'),
        bios_resume('save-bios2-resume',BD90,BIOS3,-4,why=' (bd90)'),
        bios_resume('save-bios3-resume',BE1C,DISPATCH,24,extra=[answer_write(answer)],why=' (be1c)')]


# ----------------------------------------------------------------------------------
# Independent model of the contract (python, from the contract text and the ROM bytes quoted there; not the C++).
# ----------------------------------------------------------------------------------
def sext8(v):return v-0x100 if v&0x80 else v


def m_bbb8(rb,a0,a1,d7):
    """bbb8: PUSH A0; loop SUBQ.W #1,D7 (BCS: borrow when D7.W was 0); MOVE.B (A1)+,(A0)+ (Z=moved BYTE==0, BNE repeat); then zero fill (SUBQ.W/BCS) ; POP A0; RTS.
    Returns (writes, a0, a1, d7.W)."""
    start=a0;writes=[];d=d7&0xffff
    while True:
        borrow=d==0;d=(d-1)&0xffff
        if borrow:break
        b=rb(a1);a1=(a1+1)&0xffffffff;writes.append((a0,b));a0=(a0+1)&0xffffffff
        if b!=0:continue
        while True:
            borrow=d==0;d=(d-1)&0xffff
            if borrow:break
            writes.append((a0,0));a0=(a0+1)&0xffffffff
        break
    return writes,start,a1,d


def m_bb74(rb,a0,d7):
    """bb74: D0=0 (32bit); loop D7.W times: D1.B=(A0)+; EXT.W D1; ADD.W D1,D0; ADD.W D0,D0 (C = WORD carry); no carry: skip; carry: NOT.W D0; ADDI.W #3c5b,D0; SUBQ.W #1,D7; BNE.
    Returns (D0, a0, d1.W)."""
    d0=0;d1=0;d=d7&0xffff
    while True:
        d1=sext8(rb(a0))&0xffff;a0=(a0+1)&0xffffffff
        d0=(d0+d1)&0xffff
        carry=(d0>>15)&1;d0=(d0<<1)&0xffff
        if carry:d0=(~d0)&0xffff
        d0=(d0+0x3c5b)&0xffff
        d=(d-1)&0xffff
        if d==0:break
    return d0,a0,d1


def ram_reader(program,ram):
    def rb(a):
        a&=0xffffffff
        if a<fc.RAM:return program[a]
        assert a<0x200000,hex(a)
        return ram[a&0xffff]
    return rb


def m_bd26(program,ram,a5=0x108000):
    """bd26..bd3c on the RAM image `ram`: returns the expected name bytes, checksum, registers and the bytes of 107f1c..107f33 afterwards."""
    rb=ram_reader(program,ram);buf=bytearray(ram)
    a0=(a5-0xe4)&0xffffffff
    writes,a0r,a1,d7=m_bbb8(rb,a0,SRC_NAME,0x14)
    for a,v in writes:buf[a&0xffff]=v
    rb2=ram_reader(program,buf)
    d0,a0e,d1=m_bb74(rb2,a0r,0x16)
    chk=d0
    buf[(a5-0xce)&0xffff]=chk>>8;buf[((a5-0xce)+1)&0xffff]=chk&0xff
    return dict(buf=buf,name=bytes(buf[(a0&0xffff)+i] for i in range(20)),tail=bytes(ram[(a0+20+i)&0xffff] for i in range(2)),checksum=chk,regs=dict(a0=a0e,a1=a1,d0=chk,d1w=d1,d7=0),copy_writes=writes)


def u8r(ram,a):return ram[a&0xffff]


def check_bd26_stop1(program,p,fx_ram_before):
    """Compare the BIOS #1 stop (step end phase) with the model."""
    ram_b=fx_ram_before;ram_a=p['ram_after'];o=p['outgoing']
    mdl=m_bd26(program,ram_b)
    got_name=bytes(ram_a[(NAME+i)&0xffff] for i in range(20));got_tail=bytes(ram_a[(TAIL+i)&0xffff] for i in range(2));got_chk=u16(ram_a,CHK)
    exp=dict(name=mdl['name'].hex(),tail=mdl['tail'].hex(),checksum=mdl['checksum'],
        bios=dict(c4=4,ce=0x0268,d0=0),regs=dict(a0=mdl['regs']['a0'],a1=mdl['regs']['a1'],d0=mdl['regs']['d0'],d1w=mdl['regs']['d1w'],d7=0),pc=BIOS1)
    got=dict(name=got_name.hex(),tail=got_tail.hex(),checksum=got_chk,bios=dict(c4=u8(ram_a,0x10fdc4),ce=u16(ram_a,0x10fdce),d0=u8(ram_a,0x10fdd0)),
        regs=dict(a0=o['a0'],a1=o['a1'],d0=o['d0'],d1w=o['d1']&0xffff,d7=o['d7']),pc=o['pc'])
    return exp,got


def check_bios2(p):
    ram_a=p['ram_after'];o=p['outgoing']
    exp=dict(c4=3,ce=0x0268,d0=0,c8=NAME,cc=0x18,pc=BIOS1)
    got=dict(c4=u8(ram_a,0x10fdc4),ce=u16(ram_a,0x10fdce),d0=u8(ram_a,0x10fdd0),c8=u32(ram_a,0x10fdc8),cc=u16(ram_a,0x10fdcc),pc=o['pc'])
    return exp,got


def check_bios3(p):
    ram_a=p['ram_after'];o=p['outgoing']
    return dict(c2=0,pc=BIOS3),dict(c2=u8(ram_a,0x10fdc2),pc=o['pc'])


# ----------------------------------------------------------------------------------
# The real chain prefix: BIOS resume -> card child -> push -> open unit -> input frame 1 (re-derived with the input / close observer machinery)
# ----------------------------------------------------------------------------------
def build_prefix(program):
    connected=fc.connected_fixture(program)
    base_steps=[dict(label='connected-47fe8',changes=[],stop_pc=cc.DISPATCH_RETURN,checkpoints=fc.CONNECTED_CK,a7=('entry',4))]+fc.frame_steps(1,fc.LAST_FRAME)
    prev_chain=dict(label='fade-card-chain-47fe8-to-c00468',group='chain',fixture=connected,steps=base_steps,provenance='fade/card unit chain, re-run to obtain the c00468 stop output')
    fade_split=fc.run_condition(program,prev_chain,False);assert fade_split==fc.run_condition(program,prev_chain,False)
    endlast=fc.step_end(fade_split,fc.LAST_FRAME);assert endlast['outgoing']['pc']==fc.BIOS
    child_steps=cc.connection_steps(0x00)+cc.child_steps();n_child=len(child_steps)
    child_spec=cc.fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'card-child-chain-to-a29c',child_steps,'chain','card child chain (declared BIOS resume) to the a29c stop')
    child_split=fc.run_condition(program,child_spec,False);assert child_split==fc.run_condition(program,child_spec,False)
    a29c_end=fc.step_end(child_split,n_child-1);assert a29c_end['outgoing']['pc']==menu.A29C and a29c_end['outgoing']['a7']==0x1feff8
    end_label='card child chain step %d (stop a29c)'%(n_child-1)
    push_step=dict(label='menu-a29c-to-a370',changes=[],stop_pc=menu.A370,checkpoints=[],a7=('entry',0))
    push_spec=cc.fresh_spec(connected,a29c_end,end_label,'menu-push-a29c-to-a370',[push_step],'connected','push unit a29c -> a370 (re-derived)')
    push_a=fc.run_condition(program,push_spec,True);assert push_a==fc.run_condition(program,push_spec,True)
    s0=push_a[-1];assert s0['outgoing']['pc']==op.A370 and u32(s0['ram_after'],s0['outgoing']['a7'])==op.C2C0 and u32(s0['ram_after'],s0['outgoing']['a7']+4)==DISPATCH
    byte4,byte5,cval=u8(s0['ram_after'],A2R+4),u8(s0['ram_after'],A2R+5),u8(s0['ram_after'],A2R+0xc)
    n0,_=op.growth_model(byte4,byte5,cval);open_steps=op.open_steps(n0)
    s0_label='push unit a370 stop (after card child chain step %d, a29c executed)'%(n_child-1)
    open_spec=cc.fresh_spec(connected,s0,s0_label,'connected-a370-to-open',open_steps,'connected','open unit continuation (re-derived)',chain_offset=None)
    open_a=fc.run_condition(program,open_spec,True);assert open_a==fc.run_condition(program,open_spec,True)
    end=open_a[-1];o=end['outgoing']
    assert o['pc']==DISPATCH and o['a7']==0x1ff000 and u32(end['ram_after'],o['a6'])==0xc2ba and u16(end['ram_after'],o['a6']+0x7e)==0x12c
    first_open=n_child+1;n_open_end=first_open+n0
    prefix_steps=child_steps+[copy.deepcopy(push_step)]+copy.deepcopy(open_steps)
    assert len(prefix_steps)==n_open_end
    return dict(connected=connected,endlast=endlast,child_steps=child_steps,n_child=n_child,push_step=push_step,s0=s0,end=end,n0=n0,first_open=first_open,n_open_end=n_open_end,prefix_steps=prefix_steps,
        fade_split=fade_split,child_split=child_split,push_a=push_a,open_a=open_a)


# ----------------------------------------------------------------------------------
# Native frame summaries (sound calls generalised: JSR abs.L callers; ordered ports; record / BIOS bytes)
# ----------------------------------------------------------------------------------
REGK=tuple('d%d'%i for i in range(8))+tuple('a%d'%i for i in range(7))+('a7','pc')
IN1,IN2,CD6,CD7=inp.IN1,inp.IN2,inp.CD6,inp.CD7


def ph(control,i):
    ps=[p for p in control if p['step']==i];assert len(ps)==1,(i,len(ps));return ps[0]


def sound_calls2(program,p):
    """3af8 calls of one continuous phase: caller PC (JSR abs.L), D0.W at the call, executed instruction count, RAM writes of the call (instruction-level events)."""
    pcs=p['pcs'];assigned=inp.assign_events(pcs,p['events']);calls=[];k=0;bs=[b for b in p['boundaries'] if b['pc']==0x3af8]
    for i,pc in enumerate(pcs):
        if pc!=0x3af8:continue
        caller=pcs[i-1];assert program[caller:caller+2]==bytes.fromhex('4eb9'),hex(caller)
        ret=caller+6;j=next(x for x in range(i+1,len(pcs)) if pcs[x]==ret)
        evs=[e for (x,e) in assigned if i<=x<j]
        calls.append(dict(caller_pc=caller,d0_w=bs[k]['registers']['d0']&0xffff,instruction_count=j-i,path=[hex(x) for x in pcs[i:j]],
            ram_writes=[dict(pc=e['pc'],address=hex(e['address']),size=e['size'],bytes=e['bytes'],before=e['before']) for e in evs if e['region']=='ram' and e['access']=='write'],
            ram_read_count=sum(1 for e in evs if e['region']=='ram' and e['access']=='read'),other_events=[dict(region=e['region'],access=e['access'],address=hex(e['address']),size=e['size'],bytes=e['bytes']) for e in evs if e['region']!='ram']));k+=1
    assert k==len(bs),(k,len(bs))
    return calls


def ranges_of(a,b,limit=64):
    out=[];i=0;n=len(a)
    while i<n:
        if a[i]!=b[i]:
            j=i
            while j+1<n and a[j+1]!=b[j+1]:j+=1
            out.append((0x100000+i,0x100000+j));i=j+1
        else:i+=1
    return dict(count=len(out),ranges=[dict(first=hex(x),last=hex(y)) for x,y in out[:limit]])


def hexb(ram,address,n):return bytes(ram[(address+i)&0xffff] for i in range(n)).hex()


def frame_rows(program,split,control,steps):
    rows=[]
    for index in sorted({p['step'] for p in split}):
        ps=[p for p in split if p['step']==index];first,last=ps[0],ps[-1];events=[e for p in ps for e in p['events']]
        cps=[p for p in control if p['step']==index];assert len(cps)==1 and cps[0]['events']==events,(index,)
        c=cps[0];pcs=c['pcs'];ports=op.ports_of(events);rb,ra=first['ram_before'],last['ram_after']
        row=dict(step=index,label=steps[index]['label'],outgoing_pc=hex(last['outgoing']['pc']),outgoing_a6=hex(last['outgoing']['a6']),outgoing_a7=hex(last['outgoing']['a7']),
            split_phases=len(ps),pc_count_continuous=len(pcs),counts=fc.counts(events),
            ordered_port_writes=len(ports),ordered_ports_sha256=sha(b''.join(struct.pack('>BII',s,a,v) for s,a,v in ports)),
            video_long_writes=sum(1 for s,a,v in ports if a in (0x3c0000,0x3c0004) and s==4),video_word_writes=sum(1 for s,a,v in ports if a in (0x3c0000,0x3c0004) and s==2),
            pvc_writes=sum(1 for s,a,v in ports if a>=0x2ffff0),watchdog_writes=sum(1 for e in events if e['region']=='watchdog'),
            ordered_ports=[dict(size=s,address=hex(a),value=hex(v)) for s,a,v in ports] if len(ports)<=200 else 'sha256 only (%d writes)'%len(ports),
            sound_calls=sound_calls2(program,c),sound_queue_ram_104d82_12_before=hexb(rb,0x104d82,12),sound_queue_ram_104d82_12_after=hexb(ra,0x104d82,12),
            name_107f1c_20_after=hexb(ra,NAME,20),tail_107f30_2_after=hexb(ra,TAIL,2),checksum_107f32_after=u16(ra,CHK),
            bios_area_10fdc2_16_before=hexb(rb,BIOS_AREA,16),bios_area_10fdc2_16_after=hexb(ra,BIOS_AREA,16),answer_10fdc6_after=u8(ra,B_C6),
            record_107eee_after=hexb(ra,TOPREC,16),record_107efe_before=hexb(rb,A2R,16),record_107efe_after=hexb(ra,A2R,16),
            f2_before=hex(u32(rb,F2)),f2_after=hex(u32(ra,F2)),ee_before=hex(u32(rb,EE)),ee_after=hex(u32(ra,EE)),e5_before=u8(rb,E5),e5_after=u8(ra,E5),
            reached={'bd26':BD26 in pcs,'bbb8':0xbbb8 in pcs,'bb74':0xbb74 in pcs,'bd60':BD60 in pcs,'bd90':BD90 in pcs,'be0c':BE0C in pcs,'be1c':BE1C in pcs,'be2e_ori_ccr_set':0xbe2e in pcs,'be34_andi_ccr_clear':0xbe34 in pcs,
                'c1ea':C1EA in pcs,'c1ee_save_ok':0xc1ee in pcs,'c202_no_save':0xc202 in pcs,'9f36':0x9f36 in pcs,'a71a':0xa71a in pcs,'a0a0':0xa0a0 in pcs,'a0f8_nested':0xa0f8 in pcs,'9b58':0x9b58 in pcs,'9e1a':0x9e1a in pcs,'a1d6':0xa1d6 in pcs,'3af8':0x3af8 in pcs,'c212':0xc212 in pcs},
            ram_changed=ranges_of(rb,ra),stop_evidence=last['stop_evidence'])
        rows.append(row)
    return rows


def path_evidence(pcs):
    """Carry is Unknown after the BIOS (SR is never read): the known carry of be2e / be34 and its consumption by c1ea BCC are evidenced by the executed PC path only."""
    seq=[pc for pc in pcs if pc in (0xbe1c,0xbe24,0xbe2e,0xbe34,C1EA,0xc1ee,0xc202)]
    return [hex(x) for x in seq]


# ----------------------------------------------------------------------------------
# Model checks
# ----------------------------------------------------------------------------------
CHECK_ROWS=[]


def record(label,step,kind,exp,got,**extra):
    row=dict(label=label,step=step,kind=kind,model=exp,native=got,equal=exp==got,**extra)
    if not row['equal']:DISCREPANCIES.append(dict(label=label,step=step,kind=kind,model=exp,native=got))
    CHECK_ROWS.append(row);return row


def ram_apply(ram,writes):
    ram=bytearray(ram)
    for a,size,v in writes:
        for i,b in enumerate(v.to_bytes(size,'big')):ram[(a+i)&0xffff]=b
    return ram


def diff_list(a,b,limit=16):
    out=[(i,a[i],b[i]) for i in range(len(a)) if a[i]!=b[i]]
    return dict(count=len(out),first=[dict(address=hex(0x100000+i),model=x,native=y) for i,x,y in out[:limit]])


def regs_unchanged(inc,out,skip=()):return {k:(hex(inc[k]),hex(out[k])) for k in REGK if k not in skip and inc[k]!=out[k]}


def step_inputs(step):
    p1=p2=None
    for c in step['changes']:
        if c['kind']=='ram' and c['address']==IN1:p1=c['value']
        if c['kind']=='ram' and c['address']==IN2:p2=c['value']
    return p1,p2


def input_model_row(program,spec,i,p,stop_pc):
    """Frame i against the input unit model (inp.model_frame): cursor, events, sound, state bytes.  stop_pc: the native stop that corresponds to the model's 'bd26' event."""
    child=p['outgoing']['a6'];ram=p['ram_before'];p1,p2=step_inputs(spec['steps'][i])
    S=inp.read_state(ram,[list(x) for x in inp.REAL_ITEMS],True,child)
    oc=inp.model_frame(S,p1,p2,u8(ram,CD6),u8(ram,CD7))
    exp=dict(c4=S['c4'],c5=S['c5'],c7=S['c7'],c8=S['c8'],e=S['e'],f=S['f'],d=S['d'],e6=S['e6'],e5=S['e5'],w7e=S['w7e'],b80=S['b80'],sounds=oc['sounds'],pc={None:DISPATCH,'bd26':stop_pc}[oc['stop']])
    ra=p['ram_after'];calls=sound_calls2(program,p)
    got=dict(c4=u8(ra,A2R+4),c5=u8(ra,A2R+5),c7=u8(ra,A2R+7),c8=u8(ra,A2R+8),e=u8(ra,A2R+0xe),f=u8(ra,A2R+0xf),d=u8(ra,A2R+0xd),e6=u8(ra,inp.E6),e5=u8(ra,E5),w7e=u16(ra,child+0x7e),b80=u8(ra,child+0x80),sounds=[c['d0_w'] for c in calls],pc=p['outgoing']['pc'])
    return record(spec['label'],i,'input-unit-model',exp,got,p1=p1,p2=p2,model_event=oc['e6_event'],model_stop=oc['stop'])


def sel_row(program,spec,i,p):
    """bd26 .. JSR c00468 #1 (select step or direct bd26 entry): name copy, checksum, tail bytes, BIOS parameter bytes, registers, stack words."""
    a5=p['incoming']['a5'];ram_b=p['ram_before']
    mdl=m_bd26(program,ram_b,a5);o=p['outgoing'];ra=p['ram_after']
    dest=(a5-0xe4)&0xffffffff
    exp=dict(name=mdl['name'].hex(),tail=mdl['tail'].hex(),checksum=mdl['checksum'],c4=4,ce=0x0268,d0=0,pc=BIOS1,
        regs=dict(a0=mdl['regs']['a0'],a1=mdl['regs']['a1'],d0=mdl['regs']['d0'],d1w=mdl['regs']['d1w'],d7=0),stack_ret=BD60,stack_a6=o['a6'])
    got=dict(name=hexb(ra,dest,20),tail=hexb(ra,dest+20,2),checksum=u16(ra,(a5-0xce)&0xffffffff),c4=u8(ra,0x10fdc4),ce=u16(ra,0x10fdce),d0=u8(ra,0x10fdd0),pc=o['pc'],
        regs=dict(a0=o['a0'],a1=o['a1'],d0=o['d0'],d1w=o['d1']&0xffff,d7=o['d7']),stack_ret=u32(ra,o['a7']),stack_a6=u32(ra,o['a7']+4))
    return record(spec['label'],i,'bd26-name-checksum-bios1',exp,got,a5=hex(a5),dest=hex(dest),copy_write_count=len(mdl['copy_writes']),checksum_hex='%04x'%mdl['checksum'],
        name_ascii=mdl['name'].decode('latin1'),tail_hex=mdl['tail'].hex())


def bios2_row(spec,i,p):
    """resume #1: bd60.. BIOS parameter bytes, LONG 107f1c, WORD 0018, JSR #2 -> stop; RAM model is exact (declared PC/A7 changes are in ram_before/incoming)."""
    o=p['outgoing'];inc=p['incoming']
    writes=[(0x10fdc4,1,3),(0x10fdce,2,0x0268),(0x10fdd0,1,0),(0x10fdc8,4,NAME),(0x10fdcc,2,0x18),(o['a7'],4,BD90)]
    model=ram_apply(p['ram_before'],writes)
    exp=dict(ram_diff=0,regs_changed={},pc=BIOS1,a7=(inc['a7']-4)&0xffffffff,params=dict(c4=3,ce=0x0268,d0=0,c8=NAME,cc=0x18))
    ra=p['ram_after']
    got=dict(ram_diff=diff_list(model,ra)['count'],regs_changed=regs_unchanged(inc,o,('pc','a7')),pc=o['pc'],a7=o['a7'],params=dict(c4=u8(ra,0x10fdc4),ce=u16(ra,0x10fdce),d0=u8(ra,0x10fdd0),c8=u32(ra,0x10fdc8),cc=u16(ra,0x10fdcc)))
    return record(spec['label'],i,'bios1-resume-to-bios2',exp,got,ram_diff_detail=diff_list(model,ra))


def bios3_row(spec,i,p):
    """resume #2: bd90 A6 pop, BRA be0c, A6 push, BYTE 10fdc2 = 0, JSR c0046e -> stop."""
    o=p['outgoing'];inc=p['incoming']
    writes=[(o['a7']+4,4,o['a6']),(0x10fdc2,1,0),(o['a7'],4,BE1C)]
    model=ram_apply(p['ram_before'],writes);ra=p['ram_after']
    exp=dict(ram_diff=0,regs_changed={},pc=BIOS3,a7=(inc['a7']-4)&0xffffffff,c2=0)
    got=dict(ram_diff=diff_list(model,ra)['count'],regs_changed=regs_unchanged(inc,o,('pc','a7')),pc=o['pc'],a7=o['a7'],c2=u8(ra,0x10fdc2))
    return record(spec['label'],i,'bios2-resume-to-bios3',exp,got,ram_diff_detail=diff_list(model,ra))


def model_9f36(program,ram,rb,r32):
    """9f36: A2=-ee; A3=(A2); D0 = (2 if (e(A3) AND e)==0 else 0) + 9(A2) + 1 (BYTE adds); D1 = a(A2) + 1 + 8(A2) (BYTE adds); D2 = 8(A2); D7 = D2*10; A0 = LONG (A0+D7.W) with A0 = (A3)+10."""
    a2=r32(EE);a3=r32(a2)
    fl=((rb(a3+0xe)<<8)|rb(a3+0xf))&0xe
    d0=(2 if fl==0 else 0);d0=(d0+rb(a2+9))&0xff;d0=(d0+1)&0xff
    d2=rb(a2+8);d1=(rb(a2+0xa)+1)&0xff;d1=(d1+d2)&0xff
    d7=(d2*10)&0xffffffff
    a0=r32(((r32(a2)+0x10)&0xffffffff)+(d7&0xffff if d7&0xffff<0x8000 else (d7&0xffff)-0x10000))
    return dict(a2=a2,a3=a3,d0=d0,d1=d1,d2=d2,d7=d7,a0=a0)


def final_row(program,spec,i,p,answer):
    """resume #3 .. c1ea .. a0a0 nested push .. 2ac2: carry path, 9f36 registers, the new record 107eee, -f2/-ee/-e5, old record byte 8, sound call 3af8 1adb."""
    ram_b=p['ram_before'];ra=p['ram_after'];pcs=p['pcs'];bank=p['modeled_bank']
    rb,r32=menu.reader(program,ram_b,bank)
    ok=answer==0;desc=RESULT_OK if ok else RESULT_NO
    g=model_9f36(program,ram_b,rb,r32)
    m=menu.model_menu(rb,r32,desc,dict(d0=g['d0'],d1=g['d1'],d2=0,d3=0,d7=0))
    f2b=r32(F2);eeb=r32(EE);newrec=(f2b-0x10)&0xffffffff
    saved_a2=r32(p['incoming']['a7']+12)       # A2 pushed at a5b4 (E0-12, E0 = A7 at frame entry = incoming A7 + 24): a5c6 MOVEA.L (A7)+,A2 / a5c8 MOVE.L A2,-ee(A5) restores -ee after the callbacks
    overflow=newrec<0x107e0e
    rec={0:desc>>24,1:(desc>>16)&0xff,2:(desc>>8)&0xff,3:desc&0xff,4:0,5:rb(newrec+5),6:m['rec'][6],7:0,8:0,9:g['d0'],0xa:g['d1'],0xb:m['rec'][0xb],0xc:m['rec'][0xc],0xd:3,0xe:0xff,0xf:0}
    oldrec=bytearray(rb(f2b+k) for k in range(16))
    if rb(f2b+4)!=0 and rb(f2b+6)>0:oldrec[8]=(rb(f2b+6)-1)&0xff       # 9e1a: MOVE.B D0,8(A2) per drawn item; the last index stays
    exp=dict(pc=DISPATCH,carry_path=(['be1c','be24','be2e','c1ea','c1ee'] if ok else ['be1c','be24','be34','c1ea','c202']),
        record_new=bytes(rec[k] for k in range(16)).hex(),f2=newrec,ee=saved_a2,e5=1,record_old=bytes(oldrec).hex(),desc=desc,
        a0a0_regs=dict(d0=g['d0'],d1=g['d1'],d2=g['d2'],d7=g['d7'],a0=desc,a2=g['a2'],a3=g['a3']),sound=[0x1adb],
        ret_9f36=dict(pc=(0xc1f4 if ok else 0xc208),d0=g['d0'],d1=g['d1'],d2=g['d2'],d7=g['d7'],a0=g['a0'],a2=g['a2'],a3=g['a3']))
    br=[b for b in p['boundaries'] if b['pc'] in RET9F36];rr=br[0]['registers'] if br else {}
    bs=[b for b in p['boundaries'] if b['pc']==0xa0a0]
    r=bs[0]['registers'] if bs else {}
    calls=sound_calls2(program,p)
    got=dict(pc=p['outgoing']['pc'],carry_path=[x for x in path_evidence(pcs)],record_new=hexb(ra,newrec,16),f2=u32(ra,F2),ee=u32(ra,EE),e5=u8(ra,E5),record_old=hexb(ra,f2b,16),desc=r.get('a0'),
        a0a0_regs=dict(d0=r.get('d0'),d1=r.get('d1'),d2=r.get('d2'),d7=r.get('d7'),a0=r.get('a0'),a2=r.get('a2'),a3=r.get('a3')),sound=[c['d0_w'] for c in calls],
        ret_9f36=dict(pc=br[0]['pc'] if br else None,d0=rr.get('d0'),d1=rr.get('d1'),d2=rr.get('d2'),d7=rr.get('d7'),a0=rr.get('a0'),a2=rr.get('a2'),a3=rr.get('a3')))
    got['carry_path']=[x[2:] for x in got['carry_path']]
    return record(spec['label'],i,'save-result-menu-push',exp,got,answer=answer,new_record_address=hex(newrec),ee_before=hex(eeb),model_rec_fields={hex(k):v for k,v in m['rec'].items()},model_count=m['count'],model_max_width=m['maxw'],stack_overflow_model=overflow)


# ----------------------------------------------------------------------------------
# Direct-entry fixtures (internal PCs, declared stack and registers)
# ----------------------------------------------------------------------------------
X=0x1fe800                         # declared initial A7 of direct entries (return LONG 2ac2 stored there)


def ret_slot(x=X):return wr(x,4,DISPATCH,'declared return LONG 2ac2 at the initial A7 %x (consumed by the final RTS; stop 2ac2)'%x)


def direct_pc(pc):return fc.pc_to(pc,'declared direct entry at %x (internal PC, not a frame re-entry)'%pc)


def bytes_at(address,data,why):return menu.ram_bytes(address,bytes(data),why)


def bbb8_row(program,spec,meta,control):
    p=ph(control,0);ram_b=p['ram_before'];rb=ram_reader(program,ram_b);o=p['outgoing'];inc=p['incoming']
    writes,a0,a1,d7=m_bbb8(rb,meta['a0'],meta['a1'],meta['d7'])
    model=bytearray(ram_b)
    model=ram_apply(model,[(inc['a7']-4,4,meta['a0'])])
    for a,v in writes:model[a&0xffff]=v
    d7full=(meta['d7']&0xffff0000)|d7
    exp=dict(ram_diff=0,a0=a0,a1=a1,d7=d7full,a7=inc['a7']+4,pc=DISPATCH,other_regs_changed={})
    ra=p['ram_after']
    got=dict(ram_diff=diff_list(model,ra)['count'],a0=o['a0'],a1=o['a1'],d7=o['d7'],a7=o['a7'],pc=o['pc'],other_regs_changed=regs_unchanged(inc,o,('a0','a1','d7','a7','pc')))
    return record(spec['label'],0,'bbb8-copy-zero-fill',exp,got,copied_bytes=len(writes),written=[hex(a)+'='+'%02x'%v for a,v in writes[:40]],ram_diff_detail=diff_list(model,ra))


def bb74_row(program,spec,meta,control):
    p=ph(control,0);rb=ram_reader(program,p['ram_before']);o=p['outgoing'];inc=p['incoming']
    d0,a0,d1w,stat=m_bb74_stat(rb,meta['a0'],meta['d7'])
    exp=dict(d0=d0,a0=a0,d1=(inc['d1']&0xffff0000)|d1w,d7=meta['d7']&0xffff0000,a7=inc['a7']+4,pc=DISPATCH,ram_diff=0,other_regs_changed={})
    got=dict(d0=o['d0'],a0=o['a0'],d1=o['d1'],d7=o['d7'],a7=o['a7'],pc=o['pc'],ram_diff=diff_list(p['ram_before'],p['ram_after'])['count'],other_regs_changed=regs_unchanged(inc,o,('d0','a0','d1','d7','a7','pc')))
    return record(spec['label'],0,'bb74-checksum',exp,got,checksum_hex='%04x'%d0,iterations=stat['iterations'],carry_not_iterations=stat['not_iterations'],plain_iterations=stat['plain_iterations'])


def m_bb74_stat(rb,a0,d7):
    d0=0;d1=0;d=d7&0xffff;stat=dict(iterations=0,not_iterations=0,plain_iterations=0)
    while True:
        d1=sext8(rb(a0))&0xffff;a0=(a0+1)&0xffffffff
        d0=(d0+d1)&0xffff
        carry=(d0>>15)&1;d0=(d0<<1)&0xffff
        stat['iterations']+=1
        if carry:d0=(~d0)&0xffff;stat['not_iterations']+=1
        else:stat['plain_iterations']+=1
        d0=(d0+0x3c5b)&0xffff
        d=(d-1)&0xffff
        if d==0:break
    return d0,a0,d1,stat


def be0c_rows(program,spec,control,answer):
    rows=[]
    p=ph(control,0);o=p['outgoing'];inc=p['incoming']
    model=ram_apply(p['ram_before'],[(inc['a7']-4,4,inc['a6']),(0x10fdc2,1,0),(inc['a7']-8,4,BE1C)])
    exp=dict(ram_diff=0,pc=BIOS3,a7=inc['a7']-8,regs_changed={},c2=0)
    got=dict(ram_diff=diff_list(model,p['ram_after'])['count'],pc=o['pc'],a7=o['a7'],regs_changed=regs_unchanged(inc,o,('pc','a7')),c2=u8(p['ram_after'],0x10fdc2))
    rows.append(record(spec['label'],0,'be0c-bios3-stop',exp,got))
    q=ph(control,1);o=q['outgoing'];inc=q['incoming'];first=p['incoming']
    exp=dict(ram_diff=0,pc=DISPATCH,a7=first['a7']+4,a5=0x108000,a6=first['a6'],answer=answer,carry_path=(['be1c','be24','be2e'] if answer==0 else ['be1c','be24','be34']),other_regs_changed={})
    got=dict(ram_diff=diff_list(q['ram_before'],q['ram_after'])['count'],pc=o['pc'],a7=o['a7'],a5=o['a5'],a6=o['a6'],answer=u8(q['ram_after'],B_C6),carry_path=[x[2:] for x in path_evidence(q['pcs'])],
        other_regs_changed=regs_unchanged(inc,o,('pc','a7','a5')))
    rows.append(record(spec['label'],1,'be0c-resume-ori-andi-rts',exp,got,answer=answer))
    return rows


def bd26_direct_rows(program,spec,meta,control):
    """direct bd26 entry: exact RAM model of the whole of bd26 .. JSR #1, the two resumes, and the final RTS."""
    rows=[]
    a5=meta['a5'];p=ph(control,0);inc=p['incoming'];o=p['outgoing'];rbram=p['ram_before']
    mdl=m_bd26(program,rbram,a5);buf=bytearray(rbram)
    dest=(a5-0xe4)&0xffffffff
    for a,v in mdl['copy_writes']:buf[a&0xffff]=v
    buf=ram_apply(buf,[(a5-0xce,2,mdl['checksum']),(0x10fdc4,1,4),(0x10fdce,2,0x0268),(0x10fdd0,1,0),(inc['a7']-4,4,inc['a6']),(inc['a7']-8,4,BD60)])
    exp=dict(ram_diff=0,pc=BIOS1,a7=inc['a7']-8,regs=dict(a0=mdl['regs']['a0'],a1=mdl['regs']['a1'],d0=mdl['regs']['d0'],d1w=mdl['regs']['d1w'],d7=0,a5=a5,a6=inc['a6']),checksum=mdl['checksum'],name=mdl['name'].hex())
    ra=p['ram_after']
    got=dict(ram_diff=diff_list(buf,ra)['count'],pc=o['pc'],a7=o['a7'],regs=dict(a0=o['a0'],a1=o['a1'],d0=o['d0'],d1w=o['d1']&0xffff,d7=o['d7'],a5=o['a5'],a6=o['a6']),checksum=u16(ra,(a5-0xce)&0xffffffff),name=hexb(ra,dest,20))
    rows.append(record(spec['label'],0,'bd26-direct-exact',exp,got,checksum_hex='%04x'%mdl['checksum'],ram_diff_detail=diff_list(buf,ra),tail_hex=mdl['tail'].hex()))
    rows.append(bios2_row(spec,1,ph(control,1)));rows.append(bios3_row(spec,2,ph(control,2)))
    q=ph(control,3);o=q['outgoing'];inc3=q['incoming'];answer=meta['answer']
    exp=dict(ram_diff=0,pc=DISPATCH,a7=inc['a7']+4,a5=0x108000,a6=inc['a6'],carry_path=(['be1c','be24','be2e'] if answer==0 else ['be1c','be24','be34']),other_regs_changed={})
    got=dict(ram_diff=diff_list(q['ram_before'],q['ram_after'])['count'],pc=o['pc'],a7=o['a7'],a5=o['a5'],a6=o['a6'],carry_path=[x[2:] for x in path_evidence(q['pcs'])],other_regs_changed=regs_unchanged(inc3,o,('pc','a7','a5')))
    rows.append(record(spec['label'],3,'bd26-direct-resume3-ori-andi-rts',exp,got,answer=answer))
    return rows


# ----------------------------------------------------------------------------------
# Condition construction
# ----------------------------------------------------------------------------------
def chain_check(kinds):
    def run(program,spec,split,control):
        rows=[]
        for i,k in enumerate(kinds):
            p=ph(control,i)
            if k=='up':rows.append(input_model_row(program,spec,i,p,DISPATCH))
            elif k=='sel':rows.append(input_model_row(program,spec,i,p,BIOS1));rows.append(sel_row(program,spec,i,p))
            elif k=='r1':rows.append(bios2_row(spec,i,p))
            elif k=='r2':rows.append(bios3_row(spec,i,p))
            elif k=='r3':
                answer=[c['value'] for c in spec['steps'][i]['changes'] if c['kind']=='ram' and c['address']==B_C6][0]
                rows.append(final_row(program,spec,i,p,answer))
            else:raise AssertionError(k)
        return rows
    return run


def check_call(fn):return fn


class Save:
    def __init__(self,program,connected,bases,full_steps,K):
        self.program=program;self.connected=connected;self.bases=bases;self.full_steps=full_steps;self.K=K;self.specs=[];self.checks={};self.meta={}
    def make(self,label,group,prov,base,steps,regs=None,guard=None,check=None,checkpoints=True,meta=None,**extra):
        E,lab=self.bases[base]
        if guard is not None:extra.update(guarded=True,guard=guard)
        spec=cc.fresh_spec(self.connected,E,lab,label,steps,group,'fresh state from the recorded %s; '%lab+prov,regs=regs,**extra)
        if checkpoints:with_checkpoints(self.program,spec)
        self.specs.append(spec)
        if check is not None:self.checks[label]=check
        if meta is not None:self.meta[label]=meta
        return spec
    def chain_steps(self,first,last):
        return [copy.deepcopy(s) for s in self.full_steps[self.K[first]:self.K[last]+1]]


def build_conditions(S,ends):
    K=S.K;P=S.program
    # ---- fresh representative copies of the chain steps (identical declared changes and checkpoints)
    S.make('connected-input-f1-to-save-ok','connected','declared input frames and BIOS resumes as in the persistent chain; frames: up (cursor YES), select (-> stop c00468 #1), resume #1 (-> stop c00468 #2), resume #2 (-> stop c0046e), resume #3 with BYTE 10fdc6=00 (SAVE OK) -> 2ac2',
        'f1',S.chain_steps('up','r3'),check=chain_check(['up','sel','r1','r2','r3']),checkpoints=False,chain_offset=K['up'])
    S.make('fresh-save-select-from-up','fresh-frame','the select frame and the three BIOS resumes',
        'f2',S.chain_steps('sel','r3'),check=chain_check(['sel','r1','r2','r3']),checkpoints=False,chain_offset=K['sel'])
    S.make('fresh-save-resume1-from-bios1','fresh-frame','resume #1 (bd60) to the second c00468 stop','b1',S.chain_steps('r1','r1'),check=chain_check(['r1']),checkpoints=False,chain_offset=K['r1'])
    S.make('fresh-save-resume2-from-bios2','fresh-frame','resume #2 (bd90) to the c0046e stop','b2',S.chain_steps('r2','r2'),check=chain_check(['r2']),checkpoints=False,chain_offset=K['r2'])
    S.make('fresh-save-resume3-from-bios3','fresh-frame','resume #3 (be1c, 10fdc6=00 SAVE OK) to 2ac2','b3',S.chain_steps('r3','r3'),check=chain_check(['r3']),checkpoints=False,chain_offset=K['r3'])
    # ---- second chain: 10fdc6 <> 0 (NO SAVE, c232)
    nosave=S.chain_steps('up','r2')+[bios_resume('save-bios3-resume',BE1C,DISPATCH,24,extra=[answer_write(1)],why=' (be1c)')]
    S.make('connected-input-f1-to-no-save','connected','same declared frames; resume #3 declares BYTE 10fdc6=01 (NO SAVE): be24 TST.B / BNE.W -> be34 ANDI CCR #fe -> c1ea BCC taken -> c202 -> result descriptor c232 "NO SAVE."',
        'f1',nosave,check=chain_check(['up','sel','r1','r2','r3']),meta=dict(prefix_equal_steps=4),chain_offset=K['up'])
    # ---- BIOS answer variants of resume #3 (SAVE OK / NO SAVE branch by the BYTE)
    for v in (1,2,0x7f,0x80,0xff):
        S.make('bios3-answer-%02x'%v,'answer','declared BYTE 10fdc6=%02x at resume #3 (nonzero: NO SAVE c232)'%v,'b3',[bios_resume('save-bios3-resume',BE1C,DISPATCH,24,extra=[answer_write(v)],why=' (be1c)')],check=chain_check(['r3']))
    # ---- 107f30/31 values (the 22-byte checksum range includes them)
    for a,b in ((0,0),(0xff,0xff),(0x80,0x7f),(0x7f,0x80),(0x01,0x00),(0x00,0x01),(0x81,0x53)):
        ex=[wr(TAIL,1,a,'declared BYTE 107f30=%02x (checksum byte 21 of 22; not written by the name copy)'%a),wr(TAIL+1,1,b,'declared BYTE 107f31=%02x (checksum byte 22 of 22)'%b)]
        S.make('tail-107f30-%02x-107f31-%02x'%(a,b),'checksum','select frame with declared 107f30=%02x 107f31=%02x, then resume #1'%(a,b),'f2',
            [input_step('save-f003-select',0x10,0,'frame 3: P1 bit4 (select): event 3 -> c1c4 -> BSR bd26 -> JSR c00468 #1',stop=BIOS1,off=-28,extra=ex),bios_resume('save-bios1-resume',BD60,BIOS1,-4,why=' (bd60)')],
            check=chain_check(['sel','r1']))
    # ---- initial name area bytes (overwritten by the 20 copied characters; 107f30/31 stay)
    junk=[wr(NAME+i,1,0xa5 if i%2 else 0x5a,'declared BYTE %x (old name area content)'%(NAME+i)) for i in range(0,20)]
    S.make('name-area-prefilled','checksum','select frame with declared old content in 107f1c..107f2f (all 20 bytes are replaced by the copy)','f2',
        [input_step('save-f003-select',0x10,0,'frame 3: P1 bit4 (select)',stop=BIOS1,off=-28,extra=junk)],check=chain_check(['sel']))
    # ---- nested stack limit (-f2 / -ee declared; the old top record is a copy of 107efe)
    ram2=ends[K['r2']]['ram_after']
    def nested(label,R,prov,guard=None):
        rec=bytearray(ram2[(A2R+i)&0xffff] for i in range(16))
        ex=menu.ram_bytes(R,bytes(rec),'declared old top record at %x (copy of the real record 107efe)'%R)+[wr(F2,4,R,'declared -f2(A5) = %x (old top record)'%R),wr(EE,4,R,'declared -ee(A5) = %x'%R)]
        st=bios_resume('save-bios3-resume',BE1C,DISPATCH,24,extra=[answer_write(0)]+ex,why=' (be1c)')
        S.make(label,'nested-limit' if guard is None else 'guard',prov,'b3',[st],check=(chain_check(['r3']) if guard is None else None),guard=guard)
    nested('nested-limit-top-107e1e-ok',0x107e1e,'declared old top record 107e1e: a0b2 A2=107e0e, CMPA.L #107e0e,A2 BCC taken (A2 >= limit): the new record is 107e0e')
    nested('nested-limit-top-107efe-real',0x107efe,'control: the real top record 107efe given again as a declared fixture (identical to the chain)')
    nested('guard-nested-overflow-top-107e1c',0x107e1c,'declared old top record 107e1c: A2=107e0c < 107e0e, BCC not taken, a0c2 RTS pops the pushed -ee LONG (107e1c) as the return address: execution would continue in RAM (fetch refused)',guard=GUARD['nested-overflow-1c'])
    nested('guard-nested-overflow-top-107e0e',0x107e0e,'declared old top record 107e0e: A2=107dfe, a0c2 RTS pops 0000107e0e (RAM) as return address',guard=GUARD['nested-overflow-0e'])
    # ---- stops other than BIOS (refused) and wrong BIOS stop
    def st_sel(stop,off):return [input_step('save-f003-select',0x10,0,'frame 3: P1 bit4 (select)',stop=stop,off=off)]
    S.make('guard-select-stop-2ac2','guard','stop 2ac2 instead of c00468: JSR c00468 at bd5a transfers to the unmapped BIOS, the fetch is refused (partial effects: name copy, checksum, BIOS parameter bytes)','f2',st_sel(DISPATCH,0),guard=GUARD['sel-2ac2'])
    S.make('guard-select-stop-c0046e','guard','stop c0046e instead of c00468: the JSR at bd5a targets c00468 (not the declared stop): refused','f2',st_sel(BIOS3,-28),guard=GUARD['sel-c0046e'])
    S.make('guard-resume1-stop-2ac2','guard','resume #1 with stop 2ac2: JSR c00468 at bd8a refused','b1',[bios_resume('save-bios1-resume',BD60,DISPATCH,0,why=' (bd60)')],guard=GUARD['r1-2ac2'])
    S.make('guard-resume1-stop-c0046e','guard','resume #1 with stop c0046e: JSR c00468 at bd8a is not the declared stop','b1',[bios_resume('save-bios1-resume',BD60,BIOS3,-4,why=' (bd60)')],guard=GUARD['r1-c0046e'])
    S.make('guard-resume2-stop-2ac2','guard','resume #2 with stop 2ac2: JSR c0046e at be16 refused','b2',[bios_resume('save-bios2-resume',BD90,DISPATCH,0,why=' (bd90)')],guard=GUARD['r2-2ac2'])
    S.make('guard-resume2-stop-c00468','guard','resume #2 with stop c00468: JSR c0046e at be16 is not the declared stop','b2',[bios_resume('save-bios2-resume',BD90,BIOS1,-4,why=' (bd90)')],guard=GUARD['r2-c00468'])
    # ---- odd -ee (A2 of 9f36), odd (A2) (A3 of 9f36)
    st3=lambda ex:bios_resume('save-bios3-resume',BE1C,DISPATCH,24,extra=[answer_write(0)]+ex,why=' (be1c)')
    S.make('guard-odd-ee-9f36','guard','declared -ee(A5)=107eff (odd): 9f36 MOVEA.L (A2),A3 reads an odd LONG','b3',[st3([wr(EE,4,0x107eff,'declared -ee(A5) odd')])],guard=GUARD['odd-ee'])
    S.make('guard-odd-descriptor-9f36','guard','declared LONG (107efe)=0000c189 (odd descriptor pointer): 9f36 MOVE.W e(A3),D0 reads an odd WORD','b3',[st3([wr(A2R,4,0xc189,'declared LONG (A2) = c189 (odd)')])],guard=GUARD['odd-a3'])
    # ---- descriptor flags of the old menu (9f36: D0 base 2 only when (e(A3) AND e) == 0): the real descriptor c188 copied to RAM with another WORD e(A3)
    DESC_RAM=op.DESC
    def flags_case(label,flags,prov,guard=None):
        raw=bytearray(P[0xc188:0xc188+0x3c]);raw[0xe]=flags>>8;raw[0xf]=flags&0xff
        ex=menu.ram_bytes(DESC_RAM,bytes(raw),'declared RAM copy of the real descriptor c188 (0x3c bytes: header, 4 items, terminator) with WORD e(descriptor)=%04x'%flags)+[wr(A2R,4,DESC_RAM,'declared LONG (107efe) = %x (record -> RAM descriptor copy)'%DESC_RAM)]
        S.make(label,'descriptor-flags' if guard is None else 'guard',prov,'b3',[st3(ex)],check=(chain_check(['r3']) if guard is None else None),guard=guard)
    assert P[0xc188+0x3c-4:0xc188+0x3c]==bytes.fromhex('ffffffff')
    for f in (0x0002,0x0004,0x0008,0x000e,0x0100,0x00f0):
        flags_case('desc-flags-%04x'%f,f,'old menu descriptor copy with WORD e=%04x: (e AND e) %s -> 9f36 D0 base %s (9f4e MOVEQ #0)'%(f,'<> 0' if f&0xe else '== 0','0' if f&0xe else '2 (9f48)'))
    flags_case('guard-desc-flags-0001-9e94',0x0001,'old menu descriptor copy with WORD e=0001: the nested a0fc BSR 9b58 AND.W e(A3),D0 is nonzero -> BNE.W 9e94 (close unit code, not in this unit\'s ranges): refused',guard=GUARD['flags-0001'])
    # ---- direct entries
    def sc(n):return SCRATCH+n
    def bbb8_case(label,prov,src,a0,a1,d7,fill=0xaa,fill_len=0x40,dest_off=0x100):
        ex=[]
        if src is not None:ex+=bytes_at(SCRATCH,src,'declared source string at %x'%SCRATCH)
        ex+=bytes_at(SCRATCH+dest_off-0x10,bytes([fill])*fill_len,'declared destination pre-fill %02x'%fill)
        ex.append(ret_slot())
        steps=[dict(label='direct-bbb8',changes=[direct_pc(0xbbb8)]+ex,stop_pc=DISPATCH,checkpoints=[],a7=('entry',4))]
        S.make(label,'direct-bbb8','declared direct entry PC=bbb8, initial A0=%x A1=%x D7=%x, initial A7=%x with return LONG 2ac2: '%(a0,a1,d7,X)+prov,'f2',steps,regs=dict(a0=a0,a1=a1,d7=d7,a7=X),meta=dict(a0=a0,a1=a1,d7=d7),
            check=lambda program,spec,split,control,m=dict(a0=a0,a1=a1,d7=d7):[bbb8_row(program,spec,m,control)])
    D=sc(0x100)
    bbb8_case('bbb8-real-name-d7-14','the contract copy: A1=bb8e (ROM), 20 characters, the NUL is not reached',None,D,SRC_NAME,0x14)
    bbb8_case('bbb8-d7-0','D7.W=0: SUBQ.W borrows at once, nothing is copied, A0 restored',b'ABC\x00',D,SCRATCH,0)
    bbb8_case('bbb8-short-string-fill','"AB" NUL, D7=8: A,B,NUL copied (3 of 8), 5 zero bytes follow',b'AB\x00',D,SCRATCH,8)
    bbb8_case('bbb8-exact-no-nul','"ABC" NUL, D7=3: three characters copied, the NUL is not copied (borrow)',b'ABC\x00',D,SCRATCH,3)
    bbb8_case('bbb8-nul-last-d7-4','"ABC" NUL, D7=4: the NUL is the last copied byte, no fill',b'ABC\x00',D,SCRATCH,4)
    bbb8_case('bbb8-empty-string-d7-6','empty string, D7=6: NUL copied then 5 zero bytes',b'\x00',D,SCRATCH,6)
    bbb8_case('bbb8-d7-1','D7=1: one character',b'ABC\x00',D,SCRATCH,1)
    bbb8_case('bbb8-d7-high-word','D7=abcd0004: only the low WORD is counted, the high WORD is preserved',b'AB\x00',D,SCRATCH,0xabcd0004)
    bbb8_case('bbb8-dest-odd','A0 odd (BYTE accesses only)',b'ABCDEF\x00',D+1,SCRATCH,5)
    bbb8_case('bbb8-src-odd','A1 odd (BYTE accesses only)',b'xABCDEF\x00',D,SCRATCH+1,5)
    bbb8_case('bbb8-bytes-ff-80-not-zero','source bytes ff 80 7f 00: Z is the moved BYTE value (ff, 80 are nonzero)',bytes([0xff,0x80,0x7f,0x00,0x11]),D,SCRATCH,6)
    bbb8_case('bbb8-empty-d7-20','empty string, D7=20: 20 zero bytes',b'\x00',D,SCRATCH,0x14)
    bbb8_case('bbb8-fill-256','"A" NUL, D7=256: 254 zero bytes of fill',b'A\x00',D,SCRATCH,0x100,fill_len=0x140)
    def bb74_case(label,prov,data,d7,a0_off=0x200,a0=None,d0=0xffffffff,d1=0x12340000):
        a0v=SCRATCH+a0_off if a0 is None else a0
        ex=bytes_at(SCRATCH+0x1f0,bytes([0x33])*0x10,'declared fill before the buffer')+bytes_at(SCRATCH+0x200,bytes([0x33])*0x40,'declared buffer fill')+bytes_at(SCRATCH+0x200,bytes(data),'declared checksum buffer bytes')+[ret_slot()]
        steps=[dict(label='direct-bb74',changes=[direct_pc(0xbb74)]+ex,stop_pc=DISPATCH,checkpoints=[],a7=('entry',4))]
        S.make(label,'direct-bb74','declared direct entry PC=bb74, initial A0=%x D7=%x D0=%x D1=%x, initial A7=%x with return LONG 2ac2: '%(a0v,d7,d0,d1,X)+prov,'f2',steps,regs=dict(a0=a0v,d7=d7,d0=d0,d1=d1,a7=X),
            check=lambda program,spec,split,control,m=dict(a0=a0v,d7=d7):[bb74_row(program,spec,m,control)])
    chain_name=b'METAL SLUG V3       '+bytes([0x81,0x53])
    bb74_case('bb74-name-22','the chain bytes: name + 81 53, D7=16 (22)',chain_name,0x16)
    bb74_case('bb74-zeros-22','22 zero bytes: both paths (plain, then carry/NOT)',bytes(22),0x16)
    bb74_case('bb74-ff-22','22 bytes ff (EXT.W -> ffff): the NOT path from the first byte',bytes([0xff])*22,0x16)
    bb74_case('bb74-7f-22','22 bytes 7f',bytes([0x7f])*22,0x16)
    bb74_case('bb74-80-22','22 bytes 80 (EXT.W -> ff80)',bytes([0x80])*22,0x16)
    bb74_case('bb74-ramp-22','bytes 00 0b 16 .. (mixed signs)',bytes([(i*0x0b)&0xff for i in range(22)]),0x16)
    bb74_case('bb74-single-ff','D7=1, byte ff: NOT path, D0=ffff -> carry',bytes([0xff]),1)
    bb74_case('bb74-single-01','D7=1, byte 01: plain path',bytes([0x01]),1)
    bb74_case('bb74-single-00','D7=1, byte 00',bytes([0x00]),1)
    bb74_case('bb74-d7-2','D7=2',bytes([0x40,0xc0]),2)
    bb74_case('bb74-d7-high-word','D7=00030005: the loop counts the low WORD, D0 initial ffffffff is cleared (MOVEQ), D1 high WORD 1234 is preserved (EXT.W)',bytes([1,2,3,4,5,6,7]),0x30005)
    bb74_case('bb74-a0-odd','A0 odd (BYTE reads)',bytes([0x10,0x20,0x30,0x40,0x50,0x60,0x70,0x80,0x90]),9,a0=SCRATCH+0x201)
    # direct bd26 (stack declared) with answers
    def bd26_case(label,prov,answer,a5=0x108000,ex=(),regs_extra=None):
        r3=bios_resume('save-bios3-resume',BE1C,DISPATCH,8,extra=[answer_write(answer)],why=' (be1c)')
        steps=[dict(label='direct-bd26',changes=[direct_pc(BD26)]+list(ex)+[ret_slot()],stop_pc=BIOS1,checkpoints=[],a7=('entry',-8)),bios_resume('save-bios1-resume',BD60,BIOS1,-4,why=' (bd60)'),
            bios_resume('save-bios2-resume',BD90,BIOS3,-4,why=' (bd90)'),r3]
        regs=dict(a7=X,a5=a5);regs.update(regs_extra or {})
        S.make(label,'direct-bd26','declared direct entry PC=bd26 (BSR target), initial A5=%x, initial A7=%x with return LONG 2ac2 (the final RTS returns there instead of c1ea): '%(a5,X)+prov,'f2',steps,regs=regs,
            check=lambda program,spec,split,control,m=dict(a5=a5,answer=answer):bd26_direct_rows(program,spec,m,control))
    bd26_case('bd26-direct-answer-00','10fdc6=00 (SAVE OK path through be2e ORI CCR #1)',0)
    bd26_case('bd26-direct-answer-01','10fdc6=01 (be34 ANDI CCR #fe)',1)
    bd26_case('bd26-direct-answer-80','10fdc6=80',0x80)
    for a,b in ((0,0),(0xff,0xff),(0x80,0x7f)):
        bd26_case('bd26-direct-tail-%02x%02x'%(a,b),'declared 107f30=%02x 107f31=%02x'%(a,b),0,ex=[wr(TAIL,1,a,'declared BYTE 107f30'),wr(TAIL+1,1,b,'declared BYTE 107f31')])
    bd26_case('bd26-direct-a5-108100','A5=108100 (even): LEA -e4(A5) copies the name to 10801c and the checksum is stored at 108032; the BIOS parameter LONG stays the constant 107f1c',0,a5=0x108100)
    # direct be0c with the declared BYTE
    for v in (0,1,2,0x7f,0x80,0xff):
        steps=[dict(label='direct-be0c',changes=[direct_pc(BE0C),ret_slot()],stop_pc=BIOS3,checkpoints=[],a7=('entry',-8)),
            bios_resume('save-bios3-resume',BE1C,DISPATCH,8,extra=[answer_write(v)],why=' (be1c)')]
        S.make('be0c-direct-answer-%02x'%v,'direct-be0c','declared direct entry PC=be0c (BIOS card poll helper), initial A7=%x with return LONG 2ac2, resume #3 BYTE 10fdc6=%02x: %s'%(X,v,'be2e ORI CCR #1 RTS' if v==0 else 'be34 ANDI CCR #fe RTS'),
            'f2',steps,regs=dict(a7=X),check=lambda program,spec,split,control,v=v:be0c_rows(program,spec,control,v))
    # ---- odd A5 / odd A7 (direct bd26)
    ex=[ret_slot()]
    steps=[dict(label='direct-bd26',changes=[direct_pc(BD26)]+ex,stop_pc=BIOS1,checkpoints=[],a7=('entry',-8))]
    S.make('guard-odd-A5-direct-bd26','guard','declared initial A5=108001 (odd): LEA -e4(A5),A0 -> 107f1d (BYTE copy and BYTE checksum reads are legal), MOVE.W D0,-ce(A5) writes the checksum WORD at the odd 107f33','f2',steps,regs=dict(a7=X,a5=0x108001),guard=GUARD['odd-a5'])
    S.make('guard-odd-A7-direct-bd26','guard','declared initial A7=%x (odd): BSR bbb8 at bd30 pushes an odd LONG'%(X+1),'f2',[dict(label='direct-bd26',changes=[direct_pc(BD26)],stop_pc=BIOS1,checkpoints=[],a7=('entry',-8))],regs=dict(a7=X+1),guard=GUARD['odd-a7'])
    return S


GUARD={'nested-overflow-1c':dict(problem='unmapped_or_protected',pc=0xa0c2,address=0x107e1c,size=2),'nested-overflow-0e':dict(problem='unmapped_or_protected',pc=0xa0c2,address=0x107e0e,size=2),
    'sel-2ac2':dict(problem='unsupported_code_target',pc=JSR1,target=BIOS1,unmapped_fetch=True),'sel-c0046e':dict(problem='unsupported_code_target',pc=JSR1,target=BIOS1,unmapped_fetch=True),
    'r1-2ac2':dict(problem='unsupported_code_target',pc=JSR2,target=BIOS1,unmapped_fetch=True),'r1-c0046e':dict(problem='unsupported_code_target',pc=JSR2,target=BIOS1,unmapped_fetch=True),
    'r2-2ac2':dict(problem='unsupported_code_target',pc=JSR3,target=BIOS3,unmapped_fetch=True),'r2-c00468':dict(problem='unsupported_code_target',pc=JSR3,target=BIOS3,unmapped_fetch=True),
    'odd-ee':dict(problem='unsupported_odd_data_access',pc=0x9f3a,address=0x107eff,size=4,access='read'),'odd-a3':dict(problem='unsupported_odd_data_access',pc=0x9f3c,address=0xc197,size=2,access='read'),
    'flags-0001':dict(problem='unsupported_code_target',pc=0x9e94,target=0x9e94),
    'odd-a5':dict(problem='unsupported_odd_data_access',pc=BD3C,address=0x107f33,size=2,access='write',odd_write_restored=True),
    'odd-a7':dict(problem='unsupported_odd_data_access',pc=0xbd30,address=X+1-4,size=4,access='write',odd_write_restored=True)}


# ----------------------------------------------------------------------------------
# Contract table (ROM bytes quoted by the contract) against the ROM
# ----------------------------------------------------------------------------------
def contract_byte_rows(program):
    import re
    rows=[]
    for line in CONTRACT.read_text().splitlines():
        mt_=re.match(r'\|\s*`([0-9a-f]+)\.\.([0-9a-f]+)`[^|]*\|\s*`([0-9a-f]+)`\s*\|',line)
        if not mt_:continue
        lo,hi=int(mt_.group(1),16),int(mt_.group(2),16);quoted=mt_.group(3);rom=program[lo:hi].hex()
        rows.append(dict(range='%x..%x'%(lo,hi),contract_bytes=quoted,rom_bytes=rom,equal=quoted==rom))
        if quoted!=rom:DISCREPANCIES.append(dict(label='contract-bytes',range='%x..%x'%(lo,hi),contract=quoted,rom=rom))
    return rows


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():old.unlink()
    POOL.clear();DISCREPANCIES.clear();CHECK_ROWS.clear()
    allowed=allowed_pcs(program)
    assert all(pc in allowed for pc in SAVE_BLOCKS),[hex(pc) for pc in SAVE_BLOCKS if pc not in allowed]
    assert BIOS1 not in allowed and BIOS3 not in allowed and 0xbd26 in allowed
    contract_rows=contract_byte_rows(program)
    reports=[ROOT/'artifacts/animation_machine_fade_card_native/observation.json',ROOT/'artifacts/animation_machine_card_child_native/observation.json',ROOT/'artifacts/animation_machine_card_menu_native/observation.json',inp.OPEN_REPORT,INPUT_REPORT]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,inp.CONTRACT,op.CONTRACT,op.PUSH_CONTRACT,cl.CONTRACT,ROOT/'docs/analysis/animation-machine-card-child-contract.md',
        ROOT/'docs/analysis/animation-machine-fade-card-contract.md',ROOT/'docs/analysis/animation-machine-map-transfer-contract.md'}
    for report in reports:
        if report.exists():input_paths.add(report)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    # ---- chain: BIOS resume -> card child -> push -> open unit -> input frame 1 -> save frames (one persistent CPU)
    C=build_prefix(program);connected=C['connected'];endlast=C['endlast'];n_child=C['n_child'];n_open_end=C['n_open_end']
    K=dict(f1=n_open_end,up=n_open_end+1,sel=n_open_end+2,r1=n_open_end+3,r2=n_open_end+4,r3=n_open_end+5)
    full_steps=C['prefix_steps']+[frame1_step()]+chain_steps(0)
    assert len(full_steps)==K['r3']+1
    prefix_label='fade/card chain step %d (stop c00468)'%fc.LAST_FRAME
    full=cc.fresh_spec(connected,endlast,prefix_label,'chain-full-bios-resume-to-save',full_steps,'chain',
        'fade/card native chain output at c00468; declared BIOS return and 28ae fixture; card child chain, a29c, a370 and the open unit frames as in the open observer; input frame 1 as in the input observer '
        '(declared 104cba/104cc0 = 00, 10fdb6 = 01, 10fdb7 = 00); then frame 2 (declared P1 bit0: cursor 3 -> 2 YES), frame 3 (declared P1 bit4: event 3 -> c1c4 -> bd26 -> stop c00468 #1), declared BIOS resume #1 (PC=bd60, A7+=4) -> stop c00468 #2, '
        'resume #2 (PC=bd90, A7+=4) -> stop c0046e, resume #3 (PC=be1c, A7+=4, BYTE 10fdc6=00) -> c1ea .. 9f36 .. a71a .. a0a0 nested push .. 3af8(1adb) .. 2ac2')
    with_checkpoints(program,full,first=C['first_open'])
    full_split,full_control=run_spec(program,full)
    ends={p['step']:p for p in full_control}
    chain_cross=cl.crosscheck_input(full_split,n_open_end+1,n_open_end)
    assert chain_cross['performed'] is False or chain_cross['equal'],chain_cross
    cross=cc.crosscheck_fade_card(full_split);cross_child=menu.crosscheck_card_child(full_split,n_child);cross_push=op.crosscheck_push(full_split,n_child+1);cross_open=inp.crosscheck_open(full_split,n_open_end)
    for step in range(K['r3']+1):
        q=fc.step_end(full_split,step);e=ends[step];assert sha(q['ram_after'])==sha(e['ram_after']) and sha(q['pvc_after'])==sha(e['pvc_after']) and q['outgoing']==e['outgoing'],step
    bases={'f1':(ends[K['f1']],'chain input frame 1 output (step %d, cursor 3 NO, e=ff, 7e=012b, stop 2ac2)'%K['f1']),
        'f2':(ends[K['up']],'chain frame 2 output (step %d, cursor 2 YES, stop 2ac2)'%K['up']),
        'b1':(ends[K['sel']],'chain frame 3 output (step %d, stop c00468 #1)'%K['sel']),
        'b2':(ends[K['r1']],'chain resume #1 output (step %d, stop c00468 #2)'%K['r1']),
        'b3':(ends[K['r2']],'chain resume #2 output (step %d, stop c0046e)'%K['r2']),
        'end':(ends[K['r3']],'chain resume #3 output (step %d, stop 2ac2)'%K['r3'])}
    S=Save(program,connected,bases,full['steps'],K)
    build_conditions(S,ends)
    specs=S.specs
    all_specs=[full]+specs
    cache={full['label']:(full_split,full_control)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;frames={};model_rows={};partial_compare={}
    for number,spec in enumerate(all_specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if spec.get('chain_offset') is not None:
            if spec['label']=='connected-input-f1-to-no-save':
                k=S.meta[spec['label']]['prefix_equal_steps'];sub=[p for p in split if p['step']<k]
                sp=dict(spec,steps=spec['steps'][:k]);partial_compare[spec['label']]=cc.compare_with_chain(sp,sub,full_split);compared_total+=partial_compare[spec['label']]
            else:compared_total+=cc.compare_with_chain(spec,split,full_split)
        if spec['label'] in S.checks and spec.get('guard') is None:
            model_rows[spec['label']]=S.checks[spec['label']](program,spec,split,control)
        elif spec['label']=='chain-full-bios-resume-to-save':
            model_rows[spec['label']]=chain_check(['up','sel','r1','r2','r3'])(program,dict(spec,steps=spec['steps'][K['up']:]),[p for p in split if p['step']>=K['up']],[dict(p,step=p['step']-K['up']) for p in control if p['step']>=K['up']])
        min_step=K['f1'] if spec['label']=='chain-full-bios-resume-to-save' else 0
        if spec['label']=='chain-full-bios-resume-to-save':
            frames[spec['label']]=frame_rows(program,[p for p in split if p['step']>=min_step],[p for p in control if p['step']>=min_step],spec['steps'])
        elif spec.get('guard') is None:
            frames[spec['label']]=frame_rows(program,split,control,spec['steps'])
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=store('c%03d_split'%number,split,min_step),continuous_control=store('c%03d_control'%number,control,min_step),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=bool(spec.get('chain_offset') is not None),stored_from_step=min_step)
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s'%(number+1,len(all_specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else ''),flush=True)
        cache.pop(spec['label'],None)
    instructions=[]
    for lo,hi in SAVE_RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,save_ranges=SAVE_RANGES,instructions=instructions,boundary_stop_pcs=(BIOS1,BIOS3),boundary_stop_sites=dict((hex(k),{hex(a):hex(r) for a,r in v.items()}) for k,v in FETCH_SITES.items()),
        stop_rules={'0xc00468':'JSR c00468.l at bd5a (return bd60) or bd8a (return bd90) (and c376 of the fade/card unit); accepted only as the declared step stop directly after the JSR; never executed (nothing mapped)',
            '0xc0046e':'JSR c0046e.l at be16 (return be1c); same rule'},
        save_bytes={hex(lo):program[lo:hi].hex() for lo,hi in SAVE_RANGES},contract_byte_rows=contract_rows),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    def aggregate(rows):
        t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
        for r in rows:
            for ph_ in r['phases']:
                for k,v in ph_['counts'].items():t[k]+=v
        return t
    guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard']) for g in guards]
    chain_rows=frames['chain-full-bios-resume-to-save']
    row_by_step={r['step']:r for r in chain_rows}
    fin=row_by_step[K['r3']]
    save_summary=dict(checksum_107f32=row_by_step[K['sel']]['checksum_107f32_after'],checksum_hex='%04x'%row_by_step[K['sel']]['checksum_107f32_after'],name_107f1c_20=row_by_step[K['sel']]['name_107f1c_20_after'],
        name_ascii=bytes.fromhex(row_by_step[K['sel']]['name_107f1c_20_after']).decode('latin1'),tail_107f30_31=row_by_step[K['sel']]['tail_107f30_2_after'],
        bios_area_10fdc2_16_at_stop1=row_by_step[K['sel']]['bios_area_10fdc2_16_after'],bios_area_at_stop2=row_by_step[K['r1']]['bios_area_10fdc2_16_after'],bios_area_at_stop3=row_by_step[K['r2']]['bios_area_10fdc2_16_after'],
        result_record_107eee=fin['record_107eee_after'],old_record_107efe_before=fin['record_107efe_before'],old_record_107efe_after=fin['record_107efe_after'],f2_after=fin['f2_after'],ee_after=fin['ee_after'],e5_after=fin['e5_after'],
        sound_queue_before=fin['sound_queue_ram_104d82_12_before'],sound_queue_after=fin['sound_queue_ram_104d82_12_after'],sound_calls=fin['sound_calls'],
        ports_by_step={r['label']:r['ordered_port_writes'] for r in chain_rows},instructions_by_step={r['label']:r['pc_count_continuous'] for r in chain_rows},
        stops={r['label']:r['outgoing_pc'] for r in chain_rows},final_a7=fin['outgoing_a7'])
    checks_equal=all(r['equal'] for r in CHECK_ROWS)
    grouped={}
    for r in CHECK_ROWS:grouped.setdefault(r['label'],[]).append(r)
    model_checks=[dict(label=lab,kind='save',frames=[dict(frame=r['step']+1,check=r['kind'],model=r['model'],native=r['native'],equal=r['equal'],**{k:v for k,v in r.items() if k not in ('label','step','kind','model','native','equal')}) for r in rows_],equal=all(r['equal'] for r in rows_)) for lab,rows_ in grouped.items()]
    child=C['end']['outgoing']['a6'];parent=u32(C['end']['ram_after'],child+0xc)
    def state(e):
        ram=e['ram_after'];o=e['outgoing']
        return dict(step=e['step'],a6=hex(o['a6']),a7=hex(o['a7']),pc=hex(o['pc']),objects_from_parent=cl.object_list(ram,parent),child_object=cl.object_list(ram,child,1),f2=hex(u32(ram,F2)),ee=hex(u32(ram,EE)),e5=u8(ram,E5),
            cursor_7_107efe=u8(ram,A2R+7),cursor_8_107efe=u8(ram,A2R+8),e_107efe=u8(ram,A2R+0xe),w7e=u16(ram,child+0x7e),b80=u8(ram,child+0x80),record_107efe=hexb(ram,A2R,16),record_107eee=hexb(ram,TOPREC,16))
    final_state=dict(after_input_frame_1=state(ends[K['f1']]),after_frame_2_up=state(ends[K['up']]),at_bios_stop_1=state(ends[K['sel']]),at_bios_stop_2=state(ends[K['r1']]),at_bios_stop_3=state(ends[K['r2']]),after_resume_3=state(ends[K['r3']]))
    assert final_state['after_input_frame_1']['cursor_7_107efe']==3 and final_state['after_input_frame_1']['e_107efe']==0xff and final_state['after_frame_2_up']['cursor_7_107efe']==2,final_state['after_input_frame_1']
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,partial_chain_comparison=partial_compare,fade_card_crosscheck=cross,card_child_crosscheck=cross_child,card_menu_push_crosscheck=cross_push,card_menu_open_crosscheck=cross_open,card_menu_input_crosscheck=chain_cross,
        child_address=hex(C['end']['outgoing']['a6']),variant_child_layouts=[],guard_reports=guard_reports,bank_reads_by_condition=[],bank_descriptor_search=[],new_ranges=SAVE_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha),contract_byte_rows=contract_rows,contract_model_checks=model_checks,model_check_rows=len(CHECK_ROWS),model_checks_all_equal=checks_equal,save_frames=frames,save_summary=save_summary,final_state=final_state,child_frames=cc.child_frame_summary(full_split,C['end']['outgoing']['a6'],full['steps'][:n_child]),parent_address=hex(parent),contract_discrepancies=DISCREPANCIES,
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence'],guard=r['phases'][-1]['guard']) for r in results+guards],
        covered_PCs=sorted(coverage),block_starts=BLOCKS,save_block_starts=SAVE_BLOCKS,existing_block_starts=inp.BLOCKS,boundary_stop_pcs=(BIOS1,BIOS3),boundary_stop_sites=dict((hex(k),{hex(a):hex(r) for a,r in v.items()}) for k,v in FETCH_SITES.items()),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; frames after the first are declared PC=2ab8 re-entries (A6 = card child); the input bytes 104cba/104cc0 (and 10fdb6/10fdb7 in frame 1) are declared RAM fixtures as in the input observer.',
            'BIOS c00468 (command 4 / command 3) and c0046e are never executed and nothing is mapped there: a stop is accepted only as the declared step stop directly after the JSR at bd5a / bd8a / be16; the card write, the BIOS register effects and the meaning of 10fdc4..10fdd0 are unobserved.',
            'The BIOS resume is a declared host change (PC = JSR return, A7 += 4, BYTE 10fdc6 only at resume #3); the carry that the BIOS leaves is Unknown and SR is never read; be2e (ORI CCR #1) / be34 (ANDI CCR #fe) carry and its consumption by c1ea BCC are evidenced by the executed PC path only. '
            'The contract condition "Unknown carry at c1ea is an error" is a property of the C++ carry tracking and cannot be observed natively.',
            'The frame after the nested push (the result menu frames, -e5=1, a698 nested return, a6da) is not observed; the old menu record byte 8(107efe) is left at count-1 by the 9e1a redraw (native fact, not in the contract).',
            'Declared fixtures of the fresh conditions: scratch RAM %x.., initial A7=%x with the return LONG 2ac2, initial registers; the direct entries (bbb8, bb74, bd26, be0c) are internal PCs: the C++ API rejection of internal PCs is not a native guard.'%(SCRATCH,X),
            'Split checkpoints are the first hit of each contract block start (input unit blocks plus the 29 save blocks; execution order, entry PC excluded); loop re-visits are not split again. The continuous run is the control.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path only. The models compare RAM bytes, registers, ports counts/hashes and record fields, not CCR.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],model_checks=len(CHECK_ROWS),model_checks_all_equal=checks_equal,discrepancies=len(DISCREPANCIES),sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
