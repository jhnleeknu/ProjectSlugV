"""Unpatched stage controller F1c1 (stage catalog 477e4 / 477ee, music compare, entry-effect table 478a8, dispatcher callbacks 478de 4790a 4798e, child allocation 47934 4794c 47964, cut at the callback 479b0) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the buffer/cue observer U7
(observe_animation_machine_buffer_cue and through it the script/placement observer U5, scene update U4, motion walk U3, scene core U2, frame helper U1, the U6 input
observer ranges and the card-menu / fade-card chain): persistent-CPU Observer with the declared host-change vocabulary RAM write / PC redirect / A7 delta,
fresh-twice reproduction, split (stop at the first hit of every checkpoint) versus continuous equivalence, ordered port events, banked reads with the modeled bank,
SHA pins of every imported tool module, ROM SHA/mtime guard.  The declared observer extension of U5 (a WORD write to 3c0006 is a 'video' port event) is installed in
this process exactly as U5/U7 do; nothing in the imported modules or tools is edited.  The F1a observer module (observe_animation_machine_stage_entry) is imported only for
its F1A_SPLIT range constants (the routed F1a ranges 72f0 / 1a5a4 ... that F1c1 calls); the F1b observer is NOT imported (the F1b ranges are re-declared here from the F1b contract).

Unit: the 564 contract bytes of docs/analysis/animation-machine-stage-catalog-f1c-contract.md, F1c1 half (7 code ranges 3d58..3d62 3d6a..3d7c ca8a..ca9e 474e2..474f4
47540..4755e 477e4..479b0 4814e..48156, 67 block starts, TRAP #15 boundary 478a6, cut at the callback 479b0 = F1c2).  Main decisions of the contract implemented here as the
observation rules:
  * one machine run = ONE frame.  A frame ends at the 480f0 RTS that pops the declared dispatcher return LONG 2ac2 (stop 2ac2, A7 = 1feffc + 4).  The next frame is a declared
    direct re-entry: A6 = 100b30, A5 = 108000 (the previous native registers), PC := the callback LONG at (A6), A7 := 1feffc, LONG 2ac2 at (A7), LONG 104ca4 := 1ff000 (the
    declared dispatcher base): PC redirect + A7 delta + RAM writes, nothing else.  No scheduler is run: the children 4fcb8 / 4fd0a / 4ff4c are never executed.
  * the cut: 479b0 is the F1c2 entry; it is a stop only (never routed, never executed): the BRA.W at 478ec / 47918 reaching it is a stop directly after the transferring
    instruction, a frame that installs the callback 479b0 (479a6 MOVE.L #479b0,(A6)) is followed by a declared zero-step re-entry at 479b0.
  * 478a6 (TRAP #15) is a stop only: the fall-through directly after the BCS.W at 478a2 that was not taken (record +0 >= 18).  478a8 is the computed JMP 478ac(PC,D0.W): D0 =
    index; the slots 00 04 08 0c 10 14 execute, the BRA.W displacement WORDs (02 06 ..) and odd PCs are refused fetches, >= 18 reaches the TRAP boundary.
  * 478de gate (JSR 72f0; BCC.B 478de): Waiting, like the F1a 47af0 gate: the stop is taken at the arrival at 478de after the BCC.B at 478e4 was taken with BYTE 107ded bit7 set;
    the only resume is the declared IRQ palette effect (clear bit7 of 107ded unless WORD 107dea <> 0).  62(A6) child completion: declared host write between frames.
  * 49a58 and everything from 479b0 on is F1c2: not routed here.  ROM data are read from the physical window only.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step
record; a declared initial SR (default 2000, CCR 0) and the declared initial registers are part of the fixture summary.  Nothing claims BIOS execution or a natural
scheduler / natural IRQ.

Seeds (all pinned by SHA256):
  natural   artifacts/stage_entry_body/observation.json (pinned): the 137 begin outputs of the original 47a94 body runs (the 5 release-poisoned-prefix outputs are guard rows:
            WORD 104d8a = 8001 makes U1 3c60 CMP.W (A1),D0 read an odd address).  Direct entry at 47da4 with the declared dispatcher return LONG 2ac2 at A7 = 1feffc, one frame per
            machine run, the declared host write 10dd44 := ff after frame 188 (F1b contract), through 477ee and the F1c1 frames to the stop 479b0: 238 frames per seed.
  runtime   the 236 fixtures of the contract (original 2790 -> 3ef2 -> 49a1a(D0 = 0) on a zero RAM, host writes 10d680 / 10d681 / 10d683 / 10d686 / 104d74 / 104d76 and the F1b frame
            base RAM: player nodes 100cb8 / 100da8, U7 buffer rows, U2/U3 node records): 59 catalog records x music same/different x entry 477ee / 477e4.
  transition  cases 66..69 of artifacts/animation_machine_transition_native (the 477ee boundary states, fill RAM) run to the stop 47934.
  typed     declared variants / direct entries for every block start, 478a8 index, gate state, 28ae failure, stage >= 13, area 7f retry, the empty-group loop (guard), music same /
            different / 19c1, sound ring wait, and guards.
Every condition is run as a fresh-CPU chain, split (stop at the first hit of every checkpoint of every frame) and continuous, each twice; the two are compared per frame and the
reproductions by SHA of the complete native record.  Every frame that executes F1c1 code (and every frame of the dump seeds and boundary frames) is additionally replayed on a FRESH CPU
from its recorded input state (the C++ one-run-one-frame view).  Every frame records the full state SHA256; full dumps are stored for 8 natural seeds, the boundary frames of all
natural seeds and all frames of all non-natural conditions.

An independent Python model of the contract (a M68000 subset interpreter written from the 68000 programmer's reference that decodes the ORIGINAL ROM BYTES of the 7 F1c1 ranges
instruction by instruction with a complete CCR model, 32-bit register semantics, explicit byte/word/long operations; it shares no code with Unicorn, the disassembler or the C++) is
compared with each native F1c1 segment: block-leader sequence with the full register file at every leader, ordered RAM writes / RAM reads / fixed-ROM reads of the F1c1 code, ordered
ports, the final registers, PC and the whole 64KiB RAM image.  Every callee outside the F1c1 ranges is a black box whose native exit registers and RAM / port writes are replayed; the
carry of 72f0 and 28ae is computed by the model from the contract formulas (not taken from the native run).  Any difference is recorded in contract_discrepancies.
"""
import collections
import copy
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import time
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_buffer_cue as bc
import observe_animation_machine_stage_entry as f1a_mod
from disassemble_program import load_verified_program,disassemble_range
sp=bc.sp;inp=bc.inp;fh=bc.fh;fc=bc.fc;mt=bc.mt;op=bc.op;sc=bc.sc;seb=bc.seb;vsf=bc.vsf;shared=bc.shared;activation=bc.activation
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_stage_catalog_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-stage-catalog-f1c-contract.md'
CONTRACT_SHA='f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575'
SCOPE=sc.SCOPE
ROM_SHA=op.ROM_SHA
TRANSITION=ROOT/'artifacts/animation_machine_transition_native/observation.json'
TRANSITION_SHA='edf1f5e7248601d2a708cbc7ebfb8a89c62bfdb5dcef018cb94a2c5fa26aaba4'
sha=fc.sha
u8,u16,u32=op.u8,op.u16,sc.u32
S=fc.S                                                      # 1feffc: A7 at a frame entry (the dispatcher return LONG lives here; offset effc of the 64KiB work-RAM image)
M32=0xffffffff
A5V=0x108000
A6V=0x100b30                                                # the stage controller node (dispatcher A6) of the stage_entry_body observer
KEYS=shared.isolated.REG_NAMES                              # d0..d7 a0..a6
KEYS14=sc.KEYS14
REG16=tuple('d%d'%i for i in range(8))+tuple('a%d'%i for i in range(8))
PORT_REGIONS=fc.PORT_REGIONS
FRAME_RET=0x2ac2
CUT_STOP=0x479b0                                            # F1c2 entry: stop only
TRAP_STOP=0x478a6                                           # TRAP #15 of the 478a8 table range check: stop only
GATE_PC=0x478de
GATE_RET=0x478e4
TABLE_BASE=0x478ac
TABLE_JMP=0x478a8
TRANS_STOP=0x47934                                          # transition seeds: the 28ae-garbage child allocation follows
CALLBACKS=(0x478de,0x4790a,0x4798e,CUT_STOP)
WAIT_PCS=(0xcda4,0x3aea,GATE_PC)
STEP_LIMIT=400000                                           # declared per-run instruction watchdog of the observer (the original has none); a fixture may declare a smaller step_limit
CONTRACT_RANGES=((0x3d58,0x3d62),(0x3d6a,0x3d7c),(0xca8a,0xca9e),(0x474e2,0x474f4),(0x47540,0x4755e),(0x477e4,0x479b0),(0x4814e,0x48156))
F1C1_RANGES=((0x3d58,0x3d62),(0x3d6a,0x3d7c),(0xca8a,0xca9e),(0x474e2,0x474f4),(0x47540,0x4755e),(0x477e4,0x478a6),(0x478a8,0x479b0),(0x4814e,0x48156))     # routed: the TRAP at 478a6 is a boundary
F1B_RANGES=((0x47da4,0x47eac),(0x4b6e4,0x4b6f4),(0x1c5b0,0x1c5ea),(0x1bee4,0x1bef8),(0xca48,0xca50),(0x9056,0x9060))     # F1b contract ranges (re-declared; the F1b observer is not imported)
F1A_ROUTED=tuple(f1a_mod.F1A_SPLIT)
BOUNDARY_FRAMES=(0,29,188,189,235,236,237)
DUMP_SEEDS=(0,60,117,118,134,126,135,141)                  # natural seeds with the full per-frame dumps (every family / bank / live-record case)
DISCREPANCIES=[]
INFO=[]


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)
def in_f1c1(pc):return in_ranges(pc,F1C1_RANGES)


# ----------------------------------------------------------------------------------
# Contract text: byte table, block starts, bundled branches, carry classes
# ----------------------------------------------------------------------------------
def parse_contract(program):
    lines=CONTRACT.read_text().splitlines()
    rows=[];code=[]
    pat_r=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| `([0-9a-f]+)` \|$')
    sect=None
    for line in lines:
        if line.startswith('**F1c1**'):sect='f1c1'
        elif line.startswith('**F1c2**'):sect='f1c2'
        if sect!='f1c1':continue
        m=pat_r.match(line)
        if m:
            lo,hi=int(m.group(1),16),int(m.group(2),16);data=program[lo:hi]
            assert data.hex()==m.group(3),(hex(lo),hex(hi));rows.append(dict(range='%x..%x'%(lo,hi),size=hi-lo,bytes_equal_to_rom=True,sha256=sha(data)));code.append((lo,hi))
    assert code==list(CONTRACT_RANGES),code
    assert sum(h-l for l,h in code)==564
    joined=b''.join(program[l:h] for l,h in code)
    assert sha(joined)=='40c8dfbe9abc0fad2f65abae38cabb7670caa53f125b079b9fdeb8d06d7d25ef',sha(joined)
    lists={}
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',text)]
    for line in lines:
        m=re.match(r'^\s*- F1c1\((\d+)\):(.*)$',line)
        if m:lists[int(m.group(1))]=pcs(m.group(2))
    starts,bundled,preserve=lists.get(67),lists.get(9),lists.get(32)
    assert starts and len(starts)==len(set(starts))==67,len(starts or ())
    assert bundled and len(bundled)==len(set(bundled))==9
    assert preserve and len(preserve)==len(set(preserve))==32
    cons=None
    for line in lines:
        if re.match(r'^\s*- F1c1: `478e4`',line):cons=pcs(line)
    assert cons
    return rows,starts,bundled,cons,preserve


STARTS=();BUNDLED=();CONSUMERS=();PRESERVE=();TABLE=[];F1C1_INSTR={};BB_ENTRIES=();LEAD_PCS=frozenset();CK_SET=frozenset();START_SET=frozenset();RANGES_ALL=()
EVEN_PCS=();INTERIOR=();TABLE_SLOTS=tuple(TABLE_BASE+4*k for k in range(6))
CALLBACK_STARTS=(0x477e4,0x4790a,0x4798e,GATE_PC)           # node callback entry / MOVE.L #imm,(A6) installs / the BCC.B loop target
DECODE_CACHE={}


def install_decode_cache():
    """Declared in-process speed-up (no semantic change): the base Observer.prepare decodes every routed range with capstone for each new CPU; the identical result is memoized so that the
    per-frame fresh-CPU runs do not repeat it."""
    original=fc.disassemble_range
    def cached(program,start,size,base):
        key=(id(program),start,size,base)
        if key not in DECODE_CACHE:DECODE_CACHE[key]=list(original(program,start,size,base))
        return DECODE_CACHE[key]
    fc.disassemble_range=cached


def external_targets(program):
    """Targets of the JSR/JMP/BSR/BRA/Bcc instructions of the F1c1 ranges that leave the ranges (the black-box entries)."""
    out={}
    for lo,hi in F1C1_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):
            pc=r['cpu_address'];raw=bytes.fromhex(r['raw']);t,k=fh.branch_target(pc,raw)
            if raw[:2] in (b'\x4e\xf9',b'\x4e\xb9'):t=int.from_bytes(raw[2:6],'big')            # JMP / JSR abs.l
            if t is not None and not in_f1c1(t):out.setdefault(t,[]).append(pc)
    return out


def configure(program,out_dir):
    global STARTS,BUNDLED,CONSUMERS,PRESERVE,TABLE,F1C1_INSTR,BB_ENTRIES,LEAD_PCS,CK_SET,START_SET,RANGES_ALL,EVEN_PCS,INTERIOR
    ext=bc.configure(program,out_dir)                                   # installs the U5/U7 observer extension and fills fc/fh globals for the existing executors
    rows,starts,bundled,cons,preserve=parse_contract(program)
    TABLE=rows;STARTS=tuple(starts);BUNDLED=tuple(bundled);PRESERVE=tuple(preserve)
    for lo,hi in F1C1_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):F1C1_INSTR[r['cpu_address']]=r
    assert not any(r['classification']=='undecoded_word' for r in F1C1_INSTR.values())
    CONSUMERS=tuple(x for x in cons if x in set(STARTS) and F1C1_INSTR[x]['mnemonic'].split('.')[0] in ('bcc','bcs','bne','beq'))
    assert sorted(CONSUMERS)==[0x478e4,0x47944,0x4795c,0x47974],[hex(x) for x in CONSUMERS]
    decoded=set(fh.leaders_of(program,F1C1_RANGES))
    full=decoded|set(TABLE_SLOTS)|set(CALLBACK_STARTS)
    assert full==set(STARTS),(sorted(hex(x) for x in full^set(STARTS)))
    assert not set(BUNDLED)&set(STARTS)
    ext_t=external_targets(program)
    assert CUT_STOP in ext_t and sorted(ext_t.pop(CUT_STOP))==[0x478ec,0x47918]                # the F1c2 entry (BRA.W at 478ec / 47918) is a stop, not a callee
    BB_ENTRIES=tuple(sorted(ext_t))
    assert BB_ENTRIES==tuple(sorted((0x1a5a4,0xca48,0x1c5b0,0x9056,0xca7e,0x4e24e,0x3ac8,0xca9e,0xcaf0,0x8c16,0x480bc,0x72f0,0x35a2,0x28ae))),[hex(x) for x in BB_ENTRIES]
    EVEN_PCS=tuple(p for lo,hi in CONTRACT_RANGES for p in range(lo,hi,2))
    INTERIOR=tuple(p for p in EVEN_PCS if p not in set(STARTS) and p!=TRAP_STOP)
    assert len(EVEN_PCS)==282,len(EVEN_PCS)
    assert len(INTERIOR)==214,len(INTERIOR)
    START_SET=frozenset(STARTS);LEAD_PCS=frozenset(STARTS)|frozenset(BB_ENTRIES);CK_SET=frozenset(LEAD_PCS)
    RANGES_ALL=tuple(dict.fromkeys(tuple(bc.RANGES)+F1B_RANGES+F1A_ROUTED+F1C1_RANGES))
    assert not in_ranges(CUT_STOP,RANGES_ALL) and not in_ranges(TRAP_STOP,RANGES_ALL)      # 479b0 (F1c2) and 478a6 (TRAP) are boundaries, not routed
    fc.OUT=out_dir;fc.RANGES=RANGES_ALL;fc.BOUNDARIES=();fc.KEY_PCS=()
    fh.OUT=out_dir;fh.POOL.clear()
    install_observer();install_decode_cache()
    return ext


# ----------------------------------------------------------------------------------
# Observer: U5 observer (3c0006 video port) + declared initial SR, wait stops at cda4 / 3aea / the 478de palette gate, leader records (F1c1 block starts and the black-box entries
# reached directly from F1c1 code), alternative stop PCs for probes
# ----------------------------------------------------------------------------------
class F1c1Mixin(object):
    def prepare(self,fx):
        super().prepare(fx)
        c=self.cpu;REGS=fc.REGS
        if fx.get('sr') is not None:c.reg_write(REGS['sr'],fx['sr'])
        self.leads=[];self.wait=None;self.mine_seen=set();self.total=0;self.last_pc=None;self.alt_stops=frozenset(fx.get('stop_alts',()));self.step_limit=fx.get('step_limit',STEP_LIMIT)
        def cb(cpu,pc,size,user):
            if self.guard is not None:
                if pc&1 and self.guard.get('problem')=='unsupported_code_target' and self.guard.get('target')==pc:self.guard['odd_pc']=True
                return
            first_cp=pc in self.checkpoints and pc not in self.mine_seen
            if first_cp:self.mine_seen.add(pc)
            stopping=pc==self.stop_pc or (first_cp and not self.continuous)
            if stopping:return
            if pc in self.alt_stops:
                self.stop_pc=pc;cpu.emu_stop();return
            if pc==TABLE_JMP:                                               # JMP 478ac(PC,D0.W): an odd computed PC is refused BEFORE the jump (Unicorn aborts while translating some odd addresses)
                t=(TABLE_BASE+sext(cpu.reg_read(REGS['d0'])&0xffff,2))&M32
                if t&1:
                    self.guard=dict(problem='unsupported_code_target',pc=pc,target=t,odd_pc=True,refused_before_jump=True);cpu.emu_stop();return
            self.total+=1
            if self.total>self.step_limit:
                self.guard=dict(problem='step_limit',pc=pc,steps=self.total,limit=self.step_limit);cpu.emu_stop();return
            if pc in WAIT_PCS:
                a5=cpu.reg_read(REGS['a5'])
                if pc==0xcda4:
                    live=int.from_bytes(cpu.mem_read((a5+0xd34)&M32,2),'big');want=cpu.reg_read(REGS['d4'])&0xffff;blocked=live!=want
                elif pc==0x3aea:
                    live=int.from_bytes(cpu.mem_read((a5-0x328c)&M32,2),'big');want=cpu.reg_read(REGS['d1'])&0xffff;blocked=live==want
                else:                                                       # the 478de gate: a spin iteration finished (BCC.B at 478e4 taken -> 478de again)
                    live=cpu.mem_read(0x107ded,1)[0];want=0x80;blocked=len(self.pcs)>=2 and self.pcs[-2]==GATE_RET and bool(live&0x80)
                if blocked:
                    self.stop_pc=pc;self.wait=dict(pc=pc,live_word=live,compared_word=want,kind={0xcda4:'sprite',0x3aea:'sound',GATE_PC:'palette-gate'}[pc]);cpu.emu_stop();return
            if pc in LEAD_PCS and (pc in START_SET or (self.last_pc is not None and in_f1c1(self.last_pc))):
                self.leads.append(dict(pc=pc,regs=self.regs(),pc_index=len(self.pcs)-1,event_index=len(self.events)))
            self.last_pc=pc
        c.hook_add(UC_HOOK_CODE,cb)
        return self
    def begin_step(self,stop_pc,checkpoints):
        super().begin_step(stop_pc,checkpoints);self.total=0           # the instruction watchdog counts per step (all split phases of a step together), so that split and continuous agree
    def run(self,allow_guard=False):
        self.leads=[];self.wait=None;self.mine_seen=set(self.seen)
        r=super().run(allow_guard=allow_guard)
        g=r['guard']
        if g is not None and g.get('problem')=='unsupported_code_target':
            t=g['target'];prev=r['pcs'][-2] if len(r['pcs'])>=2 and r['pcs'][-1]==t else (r['pcs'][-1] if r['pcs'] else None)
            if t&1:g['reason']='odd target PC %x (an address error on the original CPU)'%t;g['odd_pc']=True
            elif t==CUT_STOP:g['reason']='479b0 (F1c2 entry) reached without the declared stop (the cut is a stop only; F1c2 is not routed)'
            elif t==TRAP_STOP:g['reason']='TRAP #15 at 478a6 reached without the declared stop (the boundary is a stop only; the TRAP is never executed)'
            elif prev==TABLE_JMP:g['reason']='computed PC 478ac+D0.W = %x (JMP 478ac(PC,D0.W) has a range check only for D0.W < 18, not for the 4-byte slot alignment) is not a routed instruction start'%t
            else:g['reason']='control transfer to %x, outside every routed range, from %s'%(t,hex(prev) if prev is not None else 'the entry')
        elif g is not None and g.get('problem') in ('unsupported_write','unmapped_or_protected'):
            g['reason']='write to the program ROM / an unmapped address %s'%hex(g.get('address',0))
        elif g is not None and g.get('problem')=='unsupported_odd_data_access':
            g['reason']='odd address %x for a %d-byte %s access (address error on the original CPU)'%(g['address'],g['size'],g['access']);g['reason_kind']='odd_word_access'
        elif g is not None and g.get('problem')=='step_limit':
            g['reason']='no terminator: the declared instruction watchdog (%d) expired at %x (the original code has no bound; the machine rolls back at its block budget)'%(g['limit'],g['pc']);g['reason_kind']='no_terminator'
        if g is not None and 'reason' not in g:g['reason']='native guard %s'%g.get('problem')
        r.update(leads=self.leads,wait=self.wait,waiting=self.wait is not None)
        return r
    def apply(self,changes):
        before=self.regs();expected=dict(before);done=[]
        for change in changes:
            kind=change['kind']
            if kind=='ram':self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
            elif kind=='pc':self.cpu.reg_write(fc.REGS['pc'],change['to']);expected['pc']=change['to'];self.last_pc=None
            elif kind=='a7_add':
                expected['a7']=(before['a7']+change['delta'])&M32;self.cpu.reg_write(fc.REGS['a7'],expected['a7'])
            else:raise AssertionError(kind)
            done.append(dict(change,pc_before=before['pc'],a7_before=before['a7']))
        assert self.regs()==expected
        return done


F1c1Observer=None


def install_observer():
    global F1c1Observer
    base=[k for k in bc.U7Observer.__mro__ if k.__name__=='U5Observer'][0]
    F1c1Observer=type('F1c1Observer',(F1c1Mixin,base),{})
    fc.Observer=F1c1Observer


def W(address,size,value,why):return fc.ram_write(address,size,value,why)




# ----------------------------------------------------------------------------------
# Chain runner: persistent CPU, one step per declared stop (one step = one frame, or the release of a wait), split (stop at the first hit of every checkpoint) or continuous
# ----------------------------------------------------------------------------------
RUNS=[0]


def run_chain(program,spec,continuous,sink=None):
    RUNS[0]+=1
    fx=spec['fixture'];allow=bool(spec.get('guarded'));o=F1c1Observer(program,continuous);phases=[]
    try:
        first_step=spec['steps'][0]
        o.prepare(dict(fx,stop_pc=first_step['stop_pc'],checkpoints=first_step['checkpoints'],stop_alts=first_step.get('alts',())))
        for index,step in enumerate(spec['steps']):
            o.begin_step(step['stop_pc'],step['checkpoints']);o.alt_stops=frozenset(step.get('alts',()));first=None;pending=step['changes']
            while True:
                remaining=[pc for pc in step['checkpoints'] if pc not in o.seen]
                target=step['stop_pc'] if continuous or not remaining else remaining[0]
                changes=o.apply(pending);pending=[]
                p=o.run(allow_guard=allow)
                if first is None:first=p['incoming']
                p.update(label=step['label'] if not phases or phases[-1]['step']!=index else '%s+after-%x'%(step['label'],phases[-1]['outgoing']['pc']),step=index,host_changes=changes,stop_pc=target,
                    carry=None,carry_in=None,branch_evidence=[],step_stop_pc=step['stop_pc'],phase_in_step=sum(q['step']==index for q in phases))
                if sink is not None:sink(p)
                else:phases.append(p)
                if sink is not None:phases.append(dict(step=index,outgoing=p['outgoing'],guard=p['guard'],waiting=p['waiting'],phase_in_step=p['phase_in_step']))
                if p['guard'] is not None:break
                if p['waiting']:
                    assert p['outgoing']['pc'] in WAIT_PCS,(spec['label'],hex(p['outgoing']['pc']))
                    break
                if p['outgoing']['pc']!=target and p['outgoing']['pc'] in step.get('alts',()):
                    step['found_stop']=p['outgoing']['pc'];break                      # probe only: an alternative declared stop was reached
                assert p['outgoing']['pc']==target,(spec['label'],step['label'],hex(p['outgoing']['pc']),hex(target))
                if p['outgoing']['pc']==step['stop_pc']:
                    if step.get('a7') is not None:
                        kind,value=step['a7']
                        want=(first['a7']+value)&M32 if kind=='entry' else value
                        assert p['outgoing']['a7']==want,(spec['label'],step['label'],hex(p['outgoing']['a7']),hex(want))
                    break
                assert p['phase_in_step']<300,(spec['label'],step['label'])
            if phases[-1]['guard'] is not None:
                assert allow,(spec['label'],phases[-1]['guard']);assert index==len(spec['steps'])-1
            else:
                expect=step.get('expect')
                if expect=='wait':assert phases[-1]['waiting'],(spec['label'],step['label'],'expected a wait stop, got',hex(phases[-1]['outgoing']['pc']))
                if expect in ('return','boundary'):assert not phases[-1]['waiting'],(spec['label'],step['label'],'expected a stop, got a wait at',hex(phases[-1]['outgoing']['pc']))
        last=phases[-1]
        if allow:
            if last['guard'] is not None or not spec.get('probe'):
                g=last['guard'];assert g is not None,spec['label']
                for key,value in (spec.get('guard') or {}).items():assert g.get(key)==value,(spec['label'],key,g)
        else:assert all(p['guard'] is None for p in phases)
        return phases
    finally:o.close()


def lead_key(p):return [(l['pc'],l['regs']) for l in p['leads']]


def compare_steps(split,control):
    steps=sorted({p['step'] for p in split});assert steps==sorted({p['step'] for p in control})
    for index in steps:
        a=[p for p in split if p['step']==index];b=[p for p in control if p['step']==index]
        assert len(b)==1
        pcs=[];events=[];changes=[];leads=[]
        for p in a:pcs.extend(p['pcs'][:-1]);events.extend(p['events']);changes.extend(p['host_changes']);leads.extend(lead_key(p))
        pcs+=a[-1]['pcs'][-1:]
        assert (pcs,events,changes,leads)==(b[0]['pcs'],b[0]['events'],b[0]['host_changes'],lead_key(b[0])),(index,'split/continuous differ')
        for key in ('outgoing','ram_after','pvc_after','guard','waiting','wait'):assert a[-1][key]==b[0][key],(index,key)
        checkpoints={p['outgoing']['pc']:(p['outgoing'],p['ram_after'],p['pvc_after']) for p in a[:-1] if not p['waiting'] and p['guard'] is None}
        seen=set()
        for snap in b[0]['snapshots']:
            regs=snap['registers'];assert checkpoints[regs['pc']]==(regs,snap['ram'],snap['pvc']);seen.add(regs['pc'])
        assert seen==set(checkpoints),(index,sorted(map(hex,seen^set(checkpoints))))


def with_checkpoints(program,spec):
    probe=copy.deepcopy(spec)
    for s in probe['steps']:s['checkpoints']=[]
    try:phases=run_chain(program,probe,True)
    except Exception as e:
        diag=copy.deepcopy(probe);diag['guarded']=True;diag['guard']={}
        try:last=run_chain(program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
        except Exception as e2:info=repr(e2)
        raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(spec['label'],e,info))
    assert len(phases)==len(spec['steps']),(spec['label'],len(phases),len(spec['steps']))
    for index,step in enumerate(spec['steps']):
        order=[];entry=phases[index]['pcs'][0]
        for pc in phases[index]['pcs'][1:]:
            if pc in CK_SET and pc not in order and pc!=entry and pc!=step['stop_pc']:order.append(pc)
        step['checkpoints']=order
    return spec


def jdump(x):return json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()


def phase_digest(p):
    """SHA256 of the complete native record of one phase (every field that two reproductions must agree on)."""
    h=hashlib.sha256()
    for key in ('incoming','outgoing','pvc_before','pvc_after','ram_before','ram_after','guard','waiting','wait','host_changes','modeled_bank','bank_before','ff8_before','ff9_before','ff8_after','ff9_after','label','step','phase_in_step','stop_pc','step_stop_pc'):
        v=p[key];h.update(key.encode());h.update(v if isinstance(v,(bytes,bytearray)) else jdump(v))
    h.update(struct.pack('>%dI'%len(p['pcs']),*p['pcs']));h.update(jdump(p['events']));h.update(jdump(lead_key(p)))
    h.update(jdump([(s['registers'],sha(s['ram']),sha(s['pvc'])) for s in p['snapshots']]))
    return h.hexdigest()


def run_digests(program,spec,continuous):
    out=[]
    run_chain(program,spec,continuous,sink=lambda p:out.append(phase_digest(p)))
    return out


def run_spec(program,spec):
    split=run_chain(program,spec,False)
    d_split=[phase_digest(p) for p in split]
    assert run_digests(program,spec,False)==d_split,('split not reproduced',spec['label'])
    control=run_chain(program,spec,True)
    d_control=[phase_digest(p) for p in control]
    assert run_digests(program,spec,True)==d_control,('continuous not reproduced',spec['label'])
    compare_steps(split,control)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc'] or p['waiting']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc'] or p['waiting']]
    return split,control,hashlib.sha256(''.join(d_split).encode()).hexdigest(),hashlib.sha256(''.join(d_control).encode()).hexdigest()




# ----------------------------------------------------------------------------------
# Stop evidence: a stop is accepted only directly after the transferring instruction
# ----------------------------------------------------------------------------------
WAIT_PREV={0xcda4:{0xcda0:'6700',0xcda8:'66fa'},0x3aea:{0x3ae6:'0241',0x3aee:'67fa'},GATE_PC:{GATE_RET:'64f8'}}


def decode_one(program,pc):
    r=list(disassemble_range(program,pc,8,pc))[0];assert r['cpu_address']==pc
    return r


def transfer_kind(program,prev,pc):
    """How the instruction at `prev` (bytes read from the ROM) hands control to `pc`: 'return' (RTS), 'branch' (BRA/JMP), 'branch-taken' / 'branch-not-taken' (Bcc), 'fallthrough' (any other instruction)."""
    r=decode_one(program,prev);raw=bytes.fromhex(r['raw']);w=int.from_bytes(raw[:2],'big');n=r['size']
    if w==0x4e75:return 'return',raw
    if (w&0xf000)==0x6000:
        cond=(w>>8)&15;d=w&0xff
        disp=int.from_bytes(raw[2:4],'big',signed=True) if d==0 else (d-256 if d&0x80 else d)
        target=prev+2+disp
        if cond==0:return ('branch' if target==pc else 'none'),raw
        if cond==1:return ('branch' if target==pc else 'none'),raw
        if target==pc:return 'branch-taken',raw
        return ('branch-not-taken' if prev+n==pc else 'none'),raw
    if w in (0x4ef9,0x4eb9):return ('branch' if int.from_bytes(raw[2:6],'big')==pc else 'none'),raw
    return ('fallthrough' if prev+n==pc else 'none'),raw


def stop_evidence(program,p,origin,group=()):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc'];ram=p['ram_after']
    if p['waiting']:
        assert pcs[-1]==pc and pc in WAIT_PCS,(p['label'],hex(pc))
        w=p['wait']
        if len(pcs)==1:return dict(kind='wait',outgoing_pc=pc,previous_pc=None,wait=w,reached_from='zero-step re-stop: the resumed wait is still blocked (stop PC = entry PC, nothing executed)')
        prev=pcs[-2];allowed=WAIT_PREV[pc]
        assert prev in allowed and program[prev:prev+2].hex()==allowed[prev],(p['label'],hex(prev),hex(pc))
        if pc==GATE_PC:
            return dict(kind='wait',outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),wait=w,
                reached_from='BCC.B 478de at 478e4 (bytes 64f8) taken after JSR 72f0 returned C = 0 (BYTE 107ded = %02x, bit7 set => C = 0); the Waiting is taken at the arrival at 478de, the JSR there is not executed again'%w['live_word'])
        return dict(kind='wait',outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),wait=w,
            reached_from='%s at %x %s into the %s wait at %x (blocked: live WORD %04x %s %04x); the instruction at %x is not executed'%(program[prev:prev+2].hex(),prev,'fell through' if prev in (0xcda0,0x3ae6) else 'looped back (taken)',w['kind'],pc,w['live_word'],'<>' if pc==0xcda4 else '=',w['compared_word'],pc))
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(kind='zero-step',outgoing_pc=pc,previous_pc=None,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];a7=o['a7'];inc=origin['incoming']
    kind,raw=transfer_kind(program,prev,pc)
    if kind=='return' and pc==FRAME_RET:
        assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
        on_stack=[off for off in range(0,64,2) if u32(origin['ram_before'],inc['a7']+off)==pc]
        pushed=[e['pc'] for q in group for e in q['events'] if e['region']=='ram' and e['access']=='write' and e['size']==4 and int(e['bytes'],16)==pc]
        assert on_stack or pushed or any(e['region']=='ram' and e['access']=='write' and e['size']==4 and int(e['bytes'],16)==pc and e['address']==a7-4 for e in p['events']),(p['label'],'the popped LONG %x was neither declared on the stack at the step entry nor pushed by a JSR of the step'%pc)
        return dict(kind='return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',return_long_on_stack_at_entry_offsets=on_stack,entry_a7=inc['a7'],
            reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x); %x is never executed'%(prev,pc,a7,pc))
    assert kind in ('branch','branch-taken','branch-not-taken','fallthrough','return'),(p['label'],hex(prev),hex(pc),kind)
    if kind=='return':
        assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
        return dict(kind='return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',entry_a7=inc['a7'],reached_from='RTS at %x popped the return LONG %x; %x is not executed'%(prev,pc,pc))
    name={'branch':'branch-boundary','branch-taken':'branch-boundary','branch-not-taken':'fallthrough-boundary','fallthrough':'fallthrough-boundary'}[kind]
    how={'branch':'%s at %x (bytes %s) transferred control to %x','branch-taken':'conditional branch %s at %x (bytes %s) taken to %x','branch-not-taken':'conditional branch %s at %x (bytes %s) not taken, fell through to %x','fallthrough':'%s at %x (bytes %s) fell through to %x'}[kind]
    mn=decode_one(program,prev)['mnemonic'].split('.')[0].upper()
    return dict(kind=name,outgoing_pc=pc,previous_pc=prev,previous_bytes=raw.hex(),reached_from=(how%(mn,prev,raw.hex(),pc))+'; the instruction at %x is not executed'%pc)


def annotate(program,phases):
    first={};group=collections.defaultdict(list)
    for p in phases:first.setdefault(p['step'],p);group[p['step']].append(p)
    for p in phases:p['stop_evidence']=stop_evidence(program,p,first[p['step']],group[p['step']])


# ----------------------------------------------------------------------------------
# Independent model: a M68000 subset interpreter that decodes the ORIGINAL ROM BYTES of the F1c1 ranges (decoder written from the 68000 programmer's reference, not from the
# disassembler / Unicorn / C++).  Complete CCR (X N Z V C, None = unknown), 32-bit register semantics, explicit byte / word / long operations.  Calls leave the F1c1
# ranges at a black-box entry; the native exit state of the black box is replayed (registers, RAM / PVC writes); the carry of 72f0 and 28ae is computed from the contract formulas.
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
SZ={0:1,1:2,2:4}
MASK={1:0xff,2:0xffff,4:M32}
SIGN={1:0x80,2:0x8000,4:0x80000000}


def sext(v,size):
    v&=MASK[size];return v-(1<<(8*size)) if v&SIGN[size] else v


class NeedFlag(Exception):
    def __init__(self,names):self.names=names


class FM(object):
    def __init__(self,program,bank_state,ram,regs,sr=None):
        self.prog=program;self.bank,self.ff8,self.ff9=bank_state;self.ram=bytearray(ram)
        self.r={k:regs[k]&M32 for k in KEYS+('a7',)};self.pc=regs['pc']
        self.cc=dict(X=None,N=None,Z=None,V=None,C=None)
        if sr is not None:self.cc=dict(X=(sr>>4)&1,N=(sr>>3)&1,Z=(sr>>2)&1,V=(sr>>1)&1,C=sr&1)
        self.leads=[];self.writes=[];self.reads=[];self.rom_reads=[];self.ports=[];self.cache={};self.bb_writes=0;self.exec_pcs=set()
    # ---- memory
    def mem_read(self,a,n,log=True):
        a&=M32
        if n>1 and a&1:raise ModelError('odd read %x'%a)
        if a<0x100000:
            if log:self.rom_reads.append((a,n,'fixed'))
            return int.from_bytes(self.prog[a:a+n],'big')
        if a<0x200000:
            if log:self.reads.append((a,n))
            return int.from_bytes(bytes(self.ram[(a+i)&0xffff] for i in range(n)),'big')
        if 0x200000<=a<0x2fe000:
            ph=self.bank+a-0x200000
            if log:self.rom_reads.append((a,n,'bank'))
            return int.from_bytes(self.prog[ph:ph+n],'big')
        raise ModelError('read %x'%a)
    def put_ram(self,a,n,v):
        for i,b in enumerate((v&MASK[n]).to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
    def mem_write(self,a,n,v):
        a&=M32
        if n>1 and a&1:raise ModelError('odd write %x'%a)
        if not 0x100000<=a<0x200000:raise ModelError('write %x'%a)
        v&=MASK[n];self.put_ram(a,n,v);self.writes.append((a,n,v))
    def pvc(self,a,v):
        if a==0x2ffff0:self.ff8=v
        else:self.ff9=v
        self.bank=((self.ff8>>8)|(self.ff9<<8))+0x100000
        self.ff8=(self.ff8&0xfe00)|0xa0;self.ff9&=0x7fff
    # ---- decode (from the ROM bytes)
    def ext(self,pos):return int.from_bytes(self.prog[pos:pos+2],'big')
    def decode_ea(self,mode,reg,size,pos):
        if mode==0:return ('dn',reg),pos
        if mode==1:return ('an',reg),pos
        if mode==2:return ('ind',reg),pos
        if mode==3:return ('postinc',reg),pos
        if mode==4:return ('predec',reg),pos
        if mode==5:return ('disp',reg,sext(self.ext(pos),2)),pos+2
        if mode==6:
            e=self.ext(pos);return ('idx',reg,sext(e&0xff,1),(e>>12)&7,(e>>15)&1,(e>>11)&1),pos+2
        if reg==0:return ('abs',sext(self.ext(pos),2)&M32),pos+2
        if reg==1:return ('abs',(self.ext(pos)<<16)|self.ext(pos+2)),pos+4
        if reg==2:return ('abs',(pos+sext(self.ext(pos),2))&M32),pos+2
        if reg==3:
            e=self.ext(pos);return ('pcidx',pos,sext(e&0xff,1),(e>>12)&7,(e>>15)&1,(e>>11)&1),pos+2
        if reg==4:
            if size==4:return ('imm',(self.ext(pos)<<16)|self.ext(pos+2)),pos+4
            if size==2:return ('imm',self.ext(pos)),pos+2
            return ('imm',self.ext(pos)&0xff),pos+2
        raise ModelError('ea mode %d reg %d'%(mode,reg))
    def decode(self,pc):
        if pc in self.cache:return self.cache[pc]
        w=self.ext(pc);hi=w>>12;ins=dict(pc=pc)
        if w==0x4e75:ins.update(op='rts',len=2)
        elif (w&0xfff0)==0x4e40:ins.update(op='trap',len=2)
        elif hi in (1,2,3):
            size={1:1,3:2,2:4}[hi];src,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);dm=(w>>6)&7;dr=(w>>9)&7
            dst,pos=self.decode_ea(dm,dr,size,pos)
            ins.update(op='movea' if dm==1 else 'move',size=size,src=src,dst=dst,len=pos-pc)
        elif hi==7:ins.update(op='moveq',reg=(w>>9)&7,imm=w&0xff,len=2)
        elif hi==6:
            c=(w>>8)&15;d=w&0xff
            if d==0:disp=sext(self.ext(pc+2),2);ln=4
            elif d==0xff:raise ModelError('68020 long branch')
            else:disp=sext(d,1);ln=2
            ins.update(op={0:'bra',1:'bsr'}.get(c,'bcc'),cond=c,target=(pc+2+disp)&M32,len=ln)
        elif (w&0xf1c0)==0x41c0:
            ea,pos=self.decode_ea((w>>3)&7,w&7,4,pc+2);ins.update(op='lea',reg=(w>>9)&7,src=ea,len=pos-pc)
        elif (w&0xffc0)==0x4e80:
            ea,pos=self.decode_ea((w>>3)&7,w&7,4,pc+2);ins.update(op='jsr',src=ea,len=pos-pc)
        elif (w&0xffc0)==0x4ec0:
            ea,pos=self.decode_ea((w>>3)&7,w&7,4,pc+2);ins.update(op='jmp',src=ea,len=pos-pc)
        elif (w&0xff00)==0x4200 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='clr',size=size,dst=ea,len=pos-pc)
        elif (w&0xff00)==0x4a00 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='tst',size=size,src=ea,len=pos-pc)
        elif hi==5 and (w&0xc0)==0xc0 and ((w>>3)&7)!=1:
            ea,pos=self.decode_ea((w>>3)&7,w&7,1,pc+2);ins.update(op='scc',cond=(w>>8)&15,dst=ea,len=pos-pc)
        elif hi==5 and (w&0x100) and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);q=(w>>9)&7;ins.update(op='subq',size=size,imm=q or 8,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xff00)==0x0800:                    # static bit ops
            t=(w>>6)&3;bit=self.ext(pc+2)&0xff;ea,pos=self.decode_ea((w>>3)&7,w&7,1,pc+4);ins.update(op=['btst','bchg','bclr','bset'][t],bit=bit,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xff00)==0x0600 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos);ins.update(op='addi',size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi==0 and (w&0xf00)==0xc00 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos);ins.update(op='cmpi',size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi==0xb:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (0,1,2):
                size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='cmp',size=size,reg=reg,src=ea,len=pos-pc)
            elif om in (3,7):
                size=2 if om==3 else 4;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='cmpa',size=size,reg=reg,src=ea,len=pos-pc)
            else:raise ModelError('EOR %x'%pc)
        elif hi==0x8:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (0,1,2):
                size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='or',size=size,reg=reg,src=ea,len=pos-pc)
            else:raise ModelError('opcode %04x at %x'%(w,pc))
        elif hi==0xe and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];typ=(w>>3)&3
            if (w&0x20) or typ!=1:raise ModelError('shift/rotate form %04x at %x'%(w,pc))
            ins.update(op='lsl' if (w&0x100) else 'lsr',size=size,count=((w>>9)&7) or 8,reg=w&7,len=2)
        else:raise ModelError('opcode %04x at %x'%(w,pc))
        self.cache[pc]=ins;return ins
    # ---- operands
    def index_value(self,xr,xa,xl):
        v=self.r[('a%d' if xa else 'd%d')%xr]
        return v&M32 if xl else sext(v,2)
    def resolve(self,d,size):
        k=d[0]
        if k=='dn':return ('reg','d%d'%d[1])
        if k=='an':return ('reg','a%d'%d[1])
        if k=='imm':return ('imm',d[1])
        if k=='ind':return ('mem',self.r['a%d'%d[1]])
        if k=='postinc':
            n='a%d'%d[1];a=self.r[n];self.r[n]=(a+(2 if (d[1]==7 and size==1) else size))&M32;return ('mem',a)
        if k=='predec':
            n='a%d'%d[1];self.r[n]=(self.r[n]-(2 if (d[1]==7 and size==1) else size))&M32;return ('mem',self.r[n])
        if k=='disp':return ('mem',(self.r['a%d'%d[1]]+d[2])&M32)
        if k=='idx':return ('mem',(self.r['a%d'%d[1]]+d[2]+self.index_value(d[3],d[4],d[5]))&M32)
        if k=='abs':return ('mem',d[1])
        if k=='pcidx':return ('mem',(d[1]+d[2]+self.index_value(d[3],d[4],d[5]))&M32)
        raise ModelError(k)
    def get(self,loc,size):
        if loc[0]=='reg':return self.r[loc[1]]&MASK[size]
        if loc[0]=='imm':return loc[1]&MASK[size]
        return self.mem_read(loc[1],size)
    def put(self,loc,size,v):
        v&=MASK[size]
        if loc[0]=='reg':
            n=loc[1]
            if n[0]=='a':self.r[n]=sext(v,size)&M32 if size==2 else v;return
            self.r[n]=(self.r[n]&~MASK[size])&M32|v;return
        self.mem_write(loc[1],size,v)
    def nz(self,v,size):self.cc.update(N=int(bool(v&SIGN[size])),Z=int(v&MASK[size]==0),V=0,C=0)
    def push32(self,v):
        self.r['a7']=(self.r['a7']-4)&M32;self.mem_write(self.r['a7'],4,v)
    def pop32(self):
        v=self.mem_read(self.r['a7'],4);self.r['a7']=(self.r['a7']+4)&M32;return v
    def flag(self,n):
        if self.cc[n] is None:raise NeedFlag([n])
        return self.cc[n]
    def cond(self,c):
        f=self.flag
        if c==2:return not (f('C') or f('Z'))
        if c==3:return bool(f('C') or f('Z'))
        if c==4:return not f('C')
        if c==5:return bool(f('C'))
        if c==6:return not f('Z')
        if c==7:return bool(f('Z'))
        if c==8:return not f('V')
        if c==9:return bool(f('V'))
        if c==10:return not f('N')
        if c==11:return bool(f('N'))
        if c==12:return f('N')==f('V')
        if c==13:return f('N')!=f('V')
        if c==14:return (not f('Z')) and f('N')==f('V')
        if c==15:return bool(f('Z') or f('N')!=f('V'))
        raise ModelError('cond %d'%c)
    # ---- arithmetic with the CCR
    def sub(self,d,s,size,x=True):
        m=MASK[size];d&=m;s&=m;r=(d-s)&m;c=int(d<s)
        self.cc.update(N=int(bool(r&SIGN[size])),Z=int(r==0),V=int(bool((d^s)&(d^r)&SIGN[size])),C=c)
        if x:self.cc['X']=c
        return r
    def add(self,d,s,size):
        m=MASK[size];d&=m;s&=m;r=(d+s)&m;c=int(d+s>m)
        self.cc.update(X=c,N=int(bool(r&SIGN[size])),Z=int(r==0),V=int(bool((~(d^s))&(d^r)&SIGN[size])),C=c);return r
    # ---- execution of one instruction at self.pc
    def step(self):
        pc=self.pc;ins=self.decode(pc);op_=ins['op'];nxt=(pc+ins['len'])&M32;r=self.r;self.exec_pcs.add(pc)
        if op_=='move':
            s=self.resolve(ins['src'],ins['size']);v=self.get(s,ins['size']);d=self.resolve(ins['dst'],ins['size']);self.put(d,ins['size'],v);self.nz(v,ins['size'])
        elif op_=='movea':
            s=self.resolve(ins['src'],ins['size']);v=self.get(s,ins['size']);r['a%d'%ins['dst'][1]]=sext(v,ins['size'])&M32
        elif op_=='moveq':
            v=sext(ins['imm'],1)&M32;r['d%d'%ins['reg']]=v;self.nz(v,4)
        elif op_=='lea':
            loc=self.resolve(ins['src'],4);r['a%d'%ins['reg']]=loc[1]
        elif op_=='clr':
            d=self.resolve(ins['dst'],ins['size']);self.put(d,ins['size'],0);self.cc.update(N=0,Z=1,V=0,C=0)
        elif op_=='tst':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);self.nz(v,ins['size'])
        elif op_=='subq':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size'])
            if d[0]=='reg' and d[1][0]=='a':raise ModelError('SUBQ to An')
            self.put(d,ins['size'],self.sub(v,ins['imm'],ins['size']))
        elif op_=='addi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.put(d,ins['size'],self.add(v,ins['imm'],ins['size']))
        elif op_=='cmpi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.sub(v,ins['imm'],ins['size'],x=False)
        elif op_=='cmp':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);self.sub(r['d%d'%ins['reg']],v,ins['size'],x=False)
        elif op_=='cmpa':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);v=sext(v,ins['size'])&M32;self.sub(r['a%d'%ins['reg']],v,4,x=False)
        elif op_=='or':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='d%d'%ins['reg'];res=(r[n]|v)&MASK[ins['size']];self.put(('reg',n),ins['size'],res);self.nz(res,ins['size'])
        elif op_ in ('lsl','lsr'):
            n='d%d'%ins['reg'];size=ins['size'];bits=8*size;v=r[n]&MASK[size];cnt=ins['count']
            if op_=='lsl':
                c=(v>>(bits-cnt))&1;res=(v<<cnt)&MASK[size]
            else:
                c=(v>>(cnt-1))&1;res=v>>cnt
            self.put(('reg',n),size,res);self.cc.update(X=c,C=c,V=0,N=int(bool(res&SIGN[size])),Z=int(res==0))
        elif op_=='scc':
            d=self.resolve(ins['dst'],1);self.put(d,1,0xff if self.cond(ins['cond']) else 0)
        elif op_ in ('bset','bclr','btst','bchg'):
            d=self.resolve(ins['dst'],1);v=self.get(d,1);bit=ins['bit']%8;self.cc['Z']=int((v>>bit)&1==0)
            if op_=='bset':self.put(d,1,v|(1<<bit))
            elif op_=='bclr':self.put(d,1,v&~(1<<bit))
            elif op_=='bchg':self.put(d,1,v^(1<<bit))
        elif op_=='jsr':
            loc=self.resolve(ins['src'],4);self.push32(nxt);nxt=loc[1]
        elif op_=='jmp':
            loc=self.resolve(ins['src'],4);nxt=loc[1]
        elif op_=='bsr':self.push32(nxt);nxt=ins['target']
        elif op_=='bra':nxt=ins['target']
        elif op_=='bcc':
            if self.cond(ins['cond']):nxt=ins['target']
        elif op_=='rts':nxt=self.pop32()
        elif op_=='trap':raise ModelError('TRAP executed at %x'%pc)
        else:raise ModelError(op_)
        self.pc=nxt


def lead_of(M,pc):
    regs=dict(M.r);regs['pc']=pc;return regs


def replay_events(M,events,lo,hi):
    """Replay the black-box events (all of them by PCs outside the F1c1 ranges): RAM writes and PVC register writes (bank tracking)."""
    for e in events[lo:hi]:
        if in_f1c1(e['pc']):raise ModelError('F1c1-attributed event %s at %x inside a black-box slice'%(e['access'],e['pc']))
        a,n=e['address'],e['size']
        if e['region']=='ram' and e['access']=='write':M.put_ram(a,n,int(e['bytes'],16));M.bb_writes+=1
        elif e['region']=='pvc' and e['access']=='write':M.pvc(a,int(e['bytes'],16))


def bb_carry(M,entry):
    """The carry the contract assigns to a black box (None = not consumed by F1c1): 72f0 (SUBI.B #80 on BYTE 107ded: C = 1 iff bit7 clear) and 28ae (success iff D0.W < WORD 104ca0 and A0 <> 0)."""
    if entry==0x72f0:return int(M.ram[0x7ded]<0x80)
    if entry==0x28ae:
        d0w=M.r['d0']&0xffff;count=int.from_bytes(M.ram[0x4ca0:0x4ca2],'big')
        return 1 if (d0w<count and M.r['a0']!=0) else 0
    return None


def run_segment(M,p,nl,declared_stop):
    events=p['events'];out=p['outgoing'];steps=0;prev=None
    if not in_f1c1(M.pc):                                              # entry outside F1c1: F1b code of the frame (47e92 ...) or a resumed phase inside a black box (a wait of the 480bc frame ...)
        hi=nl[0]['event_index'] if nl else len(events);replay_events(M,events,0,hi)
        if not nl:
            M.r.update({k:out[k] for k in KEYS+('a7',)});M.pc=out['pc'];return 'end-in-blackbox'
        M.r.update({k:nl[0]['regs'][k] for k in KEYS+('a7',)});M.pc=nl[0]['pc'];M.cc=dict(X=None,N=None,Z=None,V=None,C=None)
    while True:
        pc=M.pc
        if p['guard'] is None and not p['waiting'] and pc==declared_stop and (len(M.leads)>0 or prev is not None):return 'stop-at-declared-pc'
        if not in_f1c1(pc):
            if pc==out['pc'] and pc not in BB_ENTRIES and p['guard'] is None:return 'stop-at-declared-pc'
            if pc not in BB_ENTRIES:raise ModelError('control left the F1c1 ranges at %x (not a declared black-box entry)'%pc)
            M.leads.append(lead_of(M,pc));e=len(M.leads)-1
            if e>=len(nl) or nl[e]['pc']!=pc:raise ModelError('black-box entry %x: the native leaders do not align at lead %d'%(pc,e))
            ret=M.mem_read(M.r['a7'],4,log=False);a7=M.r['a7'];carry=bb_carry(M,pc)
            hi=nl[e+1]['event_index'] if e+1<len(nl) else len(events);replay_events(M,events,nl[e]['event_index'],hi)
            if e+1<len(nl):
                nxt=nl[e+1]
                if nxt['pc']!=ret or nxt['regs']['a7']!=(a7+4)&M32:raise ModelError('black box %x returned to %x with A7 %x, the model expects %x / %x'%(pc,nxt['pc'],nxt['regs']['a7'],ret,(a7+4)&M32))
                M.r.update({k:nxt['regs'][k] for k in KEYS+('a7',)});M.pc=nxt['pc'];M.cc=dict(X=None,N=None,Z=None,V=None,C=carry)
                continue
            M.r.update({k:out[k] for k in KEYS+('a7',)});M.pc=out['pc'];return 'end-in-blackbox'
        if pc in START_SET:M.leads.append(lead_of(M,pc))
        steps+=1
        if steps>3000000:raise ModelError('model step limit')
        prev=pc;M.step()
        if prev==GATE_RET and M.pc==GATE_PC and M.ram[0x7ded]&0x80:return 'gate-wait'


def model_applicable(p):return bool(p['leads']) or in_f1c1(p['incoming']['pc'])


def check_model_phase(program,label,p,sr):
    nl=[dict(pc=l['pc'],regs=l['regs'],event_index=l['event_index']) for l in p['leads']]
    inc=p['incoming']
    row=dict(label=label,kind='f1c1-model',start_pc=hex(inc['pc']),start_in_f1c1=in_f1c1(inc['pc']))
    if not model_applicable(p):
        row.update(equal=None,end='not-applicable',leaders=0,mismatches=[],note='no F1c1 instruction was executed in this phase (the F1b frame code is the F1b unit)');return row
    M=FM(program,(p['bank_before'],p['ff8_before'],p['ff9_before']),p['ram_before'],inc,sr=sr)
    if len(p['pcs'])==1 and not p['leads'] and p['outgoing']['pc']==inc['pc']:                 # zero-step: the stop PC is the entry PC, nothing executes
        row.update(equal=p['ram_after']==p['ram_before'] and {k:inc[k] for k in KEYS+('a7','pc')}=={k:p['outgoing'][k] for k in KEYS+('a7','pc')} and not p['events'],end='zero-step',leaders=0,mismatches=[])
        if not row['equal']:DISCREPANCIES.append(dict(label=label,kind='zero-step-changed-state'))
        return row
    declared_stop=p['step_stop_pc'] if p['step_stop_pc'] in START_SET else None
    try:end=run_segment(M,p,nl,declared_stop)
    except (ModelError,NeedFlag,AssertionError,KeyError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=label,kind='model-could-not-follow-native',detail=repr(e)));return row
    ev=p['events'];out=p['outgoing'];bad=[]
    ml=[(l['pc'],{k:v for k,v in l.items() if k!='pc'}) for l in M.leads];nlk=[(l['pc'],{k:v for k,v in l['regs'].items() if k!='pc'}) for l in nl]
    if len(ml)!=len(nlk):bad.append(dict(what='leader count',model=len(ml),native=len(nlk)))
    for i,(a,b) in enumerate(zip(ml,nlk)):
        if a!=b:bad.append(dict(what='leader %d'%i,model_pc=hex(a[0]),native_pc=hex(b[0]),differing_registers={k:(hex(a[1][k]),hex(b[1][k])) for k in a[1] if a[1][k]!=b[1].get(k)}));break
    nw=[(e['address'],e['size'],int(e['bytes'],16)) for e in ev if e['region']=='ram' and e['access']=='write' and in_f1c1(e['pc'])]
    if M.writes!=nw:
        first=next((i for i,(x,y) in enumerate(zip(M.writes,nw)) if x!=y),min(len(M.writes),len(nw)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(nw),first_difference=first,model=M.writes[first:first+3],native=nw[first:first+3]))
    nr=[(e['address'],e['size']) for e in ev if e['region']=='ram' and e['access']=='read' and in_f1c1(e['pc'])]
    if M.reads!=nr:
        first=next((i for i,(x,y) in enumerate(zip(M.reads,nr)) if x!=y),min(len(M.reads),len(nr)))
        bad.append(dict(what='ordered RAM reads',model_count=len(M.reads),native_count=len(nr),first_difference=first,model=M.reads[first:first+3],native=nr[first:first+3]))
    nrom=[(e['address'],e['size'],e['region']) for e in ev if e['region'] in ('fixed','bank') and e['access']=='read' and in_f1c1(e['pc'])]
    if M.rom_reads!=nrom:bad.append(dict(what='ordered fixed/bank reads',model_count=len(M.rom_reads),native_count=len(nrom),model=M.rom_reads[:6],native=nrom[:6]))
    np_=[(e['size'],e['address'],int(e['bytes'],16)) for e in ev if e['region'] in PORT_REGIONS and e['access']=='write' and in_f1c1(e['pc'])]
    if M.ports!=np_:bad.append(dict(what='ordered ports',model=M.ports,native=np_))
    ext_=[(e['pc'],e['region']) for e in ev if e['region']=='external' and in_f1c1(e['pc'])]
    if ext_:bad.append(dict(what='external reads of F1c1 code (the contract says none)',native=ext_[:4]))
    expect_end=out['pc']
    if M.pc!=out['pc'] or M.pc!=expect_end:bad.append(dict(what='final PC',model=hex(M.pc),native=hex(out['pc']),end=end))
    final=dict(M.r)
    if final!={k:out[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(out[k])) for k in final if final[k]!=out[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if M.bank!=p['modeled_bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(p['modeled_bank'])))
    expect_wait=end=='gate-wait'
    if expect_wait!=(p['waiting'] and p['wait']['pc']==GATE_PC):bad.append(dict(what='gate wait',model=end,native_wait=p['wait']))
    row.update(equal=not bad,end=end,leaders=len(M.leads),leader_pcs_distinct=len({l['pc'] for l in M.leads}),ordered_ram_writes=len(M.writes),ordered_ram_reads=len(M.reads),ordered_rom_reads=len(M.rom_reads),ordered_ports=len(M.ports),
        ram_bytes_compared=0x10000,blackbox_ram_writes=M.bb_writes,exec_pcs=sorted(M.exec_pcs),model_leader_pcs=sorted({hex(l['pc']) for l in M.leads}),mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=label,kind='model-vs-native',mismatches=bad[:4]))
    return row


# ----------------------------------------------------------------------------------
# Static checks of the contract (byte table, block starts, bundled branches, carry classes, flow-only blocks)
# ----------------------------------------------------------------------------------
FLOW_ONLY={'lea','movea','pea','jsr','jmp','bsr','bra','rts','movem','nop','btst','bset','bclr','bchg','beq','bne','bcc','bcs','bpl','bmi','bvc','bvs','bge','blt','bgt','ble','bhi','bls'}
PRODUCES={'move':'NZVC','moveq':'NZVC','clr':'NZVC','tst':'NZVC','and':'NZVC','or':'NZVC','subq':'XNZVC','subi':'XNZVC','addi':'XNZVC','add':'XNZVC','lsl':'XNZVC','lsr':'XNZVC','cmp':'NZVC','cmpa':'NZVC','cmpi':'NZVC',
    'bset':'Z','bclr':'Z','btst':'Z','bchg':'Z'}
CONSUMES={2:'CZ',3:'CZ',4:'C',5:'C',6:'Z',7:'Z',8:'V',9:'V',10:'N',11:'N',12:'NV',13:'NV',14:'NVZ',15:'NVZ'}


def block_extents(program):
    """Blocks of the F1c1 ranges: from a block start to the next start (or range end)."""
    starts=set(STARTS);blocks={};cur=None
    M=FM(program,(0x200000,0xa0,0x1000),bytes(0x10000),dict(pc=0,**{k:0 for k in KEYS+('a7',)}))
    for lo,hi in F1C1_RANGES:
        pc=lo
        while pc<hi:
            if pc in starts or cur is None or pc==lo:cur=pc;blocks[cur]=[]
            ins=M.decode(pc);blocks[cur].append(ins);pc+=ins['len']
        cur=None
    return blocks


def static_checks(program):
    instr=F1C1_INSTR
    starts=set(STARTS);blocks=block_extents(program)
    flow_rows={};consumers={};total_ins=0
    for start in sorted(blocks):
        ins=blocks[start];total_ins+=len(ins)
        mnems=[F1C1_INSTR[i['pc']]['mnemonic'].split('.')[0] for i in ins]
        flow_rows[start]=dict(start=hex(start),instructions=len(ins),flow_only=all(m in FLOW_ONLY for m in mnems),mnemonics=sorted(set(mnems)))
        defined=set();missing=set()
        for i in ins:
            if i['op']=='bcc':
                need=set(CONSUMES[i['cond']])
                missing|=need-defined
            defined|=set(PRODUCES.get(i['op'],''))
        if missing:consumers[start]=''.join(sorted(missing))
    preserve_expected=set(PRESERVE);preserve_decoded={s for s,r in flow_rows.items() if r['flow_only']}
    bundled_ok=[]
    for pc in BUNDLED:
        r=F1C1_INSTR[pc];m=r['mnemonic'].split('.')[0]
        bundled_ok.append(dict(pc=hex(pc),mnemonic=m,is_conditional_branch=m in FLOW_ONLY and m.startswith('b') and m not in ('bra','bsr','btst','bset','bclr','bchg'),is_block_start=pc in starts))
    traps=[hex(r['cpu_address']) for lo,hi in CONTRACT_RANGES for r in disassemble_range(program,lo,hi-lo,lo) if r['mnemonic'].startswith('trap')]
    return dict(instructions_decoded=len(instr),block_starts=len(starts),starts_equal_decoded_leaders_table_slots_and_callbacks=True,bundled_branches=bundled_ok,even_pcs=len(EVEN_PCS),interior_pcs=len(INTERIOR),
        flow_only_blocks_decoded=sorted(hex(x) for x in preserve_decoded),flow_only_blocks_contract=sorted(hex(x) for x in preserve_expected),flow_only_equal_contract=preserve_decoded==preserve_expected,
        flow_only_decoded_minus_contract=sorted(hex(x) for x in preserve_decoded-preserve_expected),flow_only_contract_minus_decoded=sorted(hex(x) for x in preserve_expected-preserve_decoded),
        carry_consumers_computed={hex(k):v for k,v in sorted(consumers.items())},carry_consumers_contract=sorted(hex(x) for x in CONSUMERS),
        carry_consumers_equal=set(consumers)==set(CONSUMERS) and all(v=='C' for v in consumers.values()),flow_rows=[flow_rows[k] for k in sorted(flow_rows)],bytes=TABLE,
        blocks_total_instructions=total_ins,trap_instructions_in_contract_range=traps,black_box_entries=[hex(x) for x in BB_ENTRIES])

# ----------------------------------------------------------------------------------
# Storage: content-addressed payloads (blobs/<sha256>.bin / .json.gz), written atomically; the per-condition frame records are gzip files
# ----------------------------------------------------------------------------------
BLOBS=None
BLOB_SEEN=set()


def write_blob(data,suffix='.bin'):
    digest=sha(data);name=digest+suffix
    if name in BLOB_SEEN:return name
    target=BLOBS/name
    if not target.exists():
        tmp=BLOBS/('.tmp.%d.%s'%(os.getpid(),digest[:12]))
        tmp.write_bytes(data);os.replace(tmp,target)
    BLOB_SEEN.add(name);return name


def write_json_gz(path,obj):
    data=gzip.compress((json.dumps(obj,sort_keys=True,separators=(',',':'),default=str)+'\n').encode(),9,mtime=0)
    tmp=path.with_name('.tmp.%d.%s'%(os.getpid(),path.name));tmp.write_bytes(data);os.replace(tmp,path);return sha(data)


def ports_blob(events):return b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS)



# ----------------------------------------------------------------------------------
# Declared steps: re-entry, host-write rules, release of waits, planning (one persistent probe CPU discovers the frames of a chain)
# ----------------------------------------------------------------------------------
def step_of(label,changes,stop,a7,expect,alts=(),**extra):
    return dict(label=label,changes=list(changes),stop_pc=stop,checkpoints=[],a7=a7,expect=expect,alts=tuple(alts),**extra)


def reentry_changes(callback):
    return [fc.pc_to(callback,'declared direct re-entry at the installed callback LONG (A6): PC redirect only, registers / RAM are the previous native outputs (no scheduler, no children)'),
        fc.a7_add(-4,'declared direct re-entry: A7 back to the dispatcher slot 1feffc'),W(S,4,FRAME_RET,'declared return LONG 2ac2 at (A7) (the value the previous frame popped)'),
        W(0x104ca4,4,S+4,'declared dispatcher base A7 (the scheduler stores it before JSR (A0); 2a00 reloads A7 from it): the A7 after the popped return LONG')]


def gate_effect(ram_after):
    """The declared IRQ palette effect of the 72f0 gate (F1 decision 2, minimal form): the IRQ path cbe JSR 72fa clears BYTE 107ded bit7 (72fa..7302) unless WORD 107dea <> 0
    (72fa TST.W -$216(A5); BNE.W 873a, a path that does not clear it)."""
    b=ram_after[0x7ded];w=u16(ram_after,0x7dea)
    if w!=0:return [],dict(kind='irq-palette-effect',clears_bit7=False,reason='WORD 107dea = %04x <> 0: the original IRQ path (72fa BNE.W 873a) leaves BYTE 107ded bit7 set'%w)
    return [W(0x107ded,1,b&0x7f,'declared IRQ palette effect (72fa..7302 BCLR #7,-$213(A5)): BYTE 107ded %02x -> %02x'%(b,b&0x7f))],dict(kind='irq-palette-effect',clears_bit7=True,reason='WORD 107dea = 0')


def release_changes(wait,ram_after=None):
    if wait['pc']==0x3aea:return [W(0x104d74,2,0xffff,'declared release of the sound-ring wait: tail WORD 104d74 := ffff (<> D1.W)')],None
    if wait['pc']==0xcda4:return [W(0x108d34,2,wait['compared_word'],'declared release of the sprite wait: WORD 108d34 := D4.W')],None
    return gate_effect(ram_after)


def r_after(n,writes):
    def rule(done,ram,cb,o):return list(writes) if done==n else []
    return rule


def r_dd44(extra=(),value=0xff):
    """Declared 10dd44 := ff (the area end object ST.B 5d44(A5)) in the first frame boundary at which the 47e70 poll is installed and 10dd44 is 0 (frame 188 for the natural seeds)."""
    st=dict(fired=False)
    def rule(done,ram,cb,o):
        if st['fired'] or cb!=0x47e70 or ram[0xdd44]!=0:return []
        st['fired']=True;return [W(0x10dd44,1,value,'declared host write: BYTE 10dd44 := %02x (the area end object, not executed)'%value)]+list(extra)
    return rule


def r_child62(delay=0,value=1):
    """Declared completion of the child (62(A6) := value) after `delay` further waiting frames at the 4798e callback (the child 4fcb8 / 4fd0a / 4ff4c is never executed)."""
    st=dict(waits=0,fired=False)
    def rule(done,ram,cb,o):
        if st['fired'] or cb!=0x4798e or ram[0xb92]!=0:return []
        if st['waits']<delay:
            st['waits']+=1;return []
        st['fired']=True;return [W(0x100b92,1,value,'declared host write: child completion BYTE 62(A6) := %02x (the child callback object, not executed)'%value)]
    return rule


PLAN_PCS=[]                                                       # instruction PCs of every step of the last plan (the continuous probe run); the split checkpoints are derived from them


def plan_frames(program,fx,label,setup=(),rules=(),max_frames=400,frames=None,first_stop=FRAME_RET,first_a7=('abs',S+4),end_alts=(CUT_STOP,TRAP_STOP),allow_guard=False,gate_idem=0,gate_limit=3,hold=None,reenter=True,cut_reenter=True,on_run=None):
    """Interactive probe on ONE persistent CPU: frame 0 with the declared setup, then a declared release per wait and a declared re-entry per returned frame (callback LONG at (A6)),
    host-write rules evaluated after every returned frame, until a boundary stop (479b0 / 478a6 / an alternative routed stop), the declared zero-step re-entry at the callback 479b0, `frames`
    frames, a persistent Waiting or a guard.  gate_idem: number of declared no-effect resumes of a 478de gate wait before the declared IRQ palette effect; gate_limit: Waitings after which a
    gate whose effect does not clear it ends the chain.  Returns (steps, last_phase, frame_count)."""
    o=F1c1Observer(program,True);steps=[];frame=0;idem=0;stuck=0;PLAN_PCS.clear()
    try:
        o.prepare(dict(fx,stop_pc=first_stop,checkpoints=[],stop_alts=end_alts))
        step=step_of('%s-frame0'%label,setup,first_stop,first_a7,'return',end_alts)
        while True:
            o.begin_step(step['stop_pc'],[]);o.alt_stops=frozenset(step['alts'])
            o.apply(step['changes']);p=o.run(allow_guard=True);steps.append(step);PLAN_PCS.append(p['pcs'])
            pc=p['outgoing']['pc']
            g=p['guard']
            if g is not None and g.get('problem')=='unsupported_code_target' and g.get('target') in end_alts and not in_ranges(g['target'],RANGES_ALL):
                # probe only: the alternative boundary stop (479b0 / 478a6) is not routed, so the probe CPU reports it as the refused fetch; the declared step stops there
                step['stop_pc']=g['target'];step['a7']=('abs',p['outgoing']['a7']);step['expect']='boundary';p=dict(p,guard=None)
                if on_run:on_run(len(steps)-1,step,p)
                return steps,p,frame+1
            if on_run and not (g is None and not p['waiting'] and pc in end_alts and pc!=step['stop_pc']) and not (g is None and not p['waiting'] and pc==step['stop_pc']!=FRAME_RET):on_run(len(steps)-1,step,p)
            if g is not None:
                assert allow_guard,(label,g);step['expect']='guard';return steps,p,frame
            if p['waiting']:
                step['expect']='wait';w=p['wait']
                if w['pc']==GATE_PC:
                    if idem<gate_idem:
                        idem+=1;step=step_of('%s-gate-resume-no-effect-%d'%(label,idem),[],first_stop,('abs',S+4),'wait',end_alts,declared_effect=dict(kind='no-effect-resume',reason='the gate stays blocked: a resume without any declared IRQ effect must return the same Waiting'));continue
                    ch,eff=release_changes(w,p['ram_after'])
                    if not ch:
                        stuck+=1
                        if stuck>=gate_limit:return steps,p,frame            # the gate stays blocked: the chain ends in the wait
                    step=step_of('%s-gate-irq-effect-%d'%(label,len(steps)),ch,first_stop,('abs',S+4),'return' if ch else 'wait',end_alts,declared_effect=eff);continue
                if w['pc']==0x3aea and hold is not None and not any(s.get('hold') for s in steps):
                    step=step_of('%s-hold'%label,hold,first_stop,('abs',S+4),'wait',end_alts,hold=True);continue
                step=step_of('%s-frame%d-release%d'%(label,frame,sum(1 for s in steps if s['label'].startswith('%s-frame%d-release'%(label,frame)))+1),release_changes(w)[0],first_stop,('abs',S+4),'return',end_alts);continue
            if pc in end_alts and pc!=step['stop_pc']:
                step['stop_pc']=pc;step['a7']=('abs',p['outgoing']['a7']);step['expect']='boundary'
                if on_run:on_run(len(steps)-1,step,p)
                return steps,p,frame+1
            if pc==step['stop_pc']!=FRAME_RET:                                  # a declared routed boundary stop (transition seeds: 47934)
                step['a7']=('abs',p['outgoing']['a7']);step['expect']='boundary'
                if on_run:on_run(len(steps)-1,step,p)
                return steps,p,frame+1
            assert pc==step['stop_pc']==FRAME_RET,(label,hex(pc))
            o_=p['outgoing'];assert o_['a6']==A6V or fx.get('free_a6'),(label,hex(o_['a6']));assert o_['a5']==A5V,(label,hex(o_['a5']))
            ram=p['ram_after'];cb=u32(ram,o_['a6']&0xffff)
            frame+=1
            if frames is not None and frame>=frames:return steps,p,frame
            if frame>=max_frames:raise AssertionError('too many frames '+label)
            if not reenter:return steps,p,frame
            host=[c for rule in rules for c in rule(frame-1,ram,cb,o_)]
            if cb==CUT_STOP and CUT_STOP in end_alts and cut_reenter:
                # the installed callback is the cut: the declared re-entry stops at once at 479b0 (zero-step boundary)
                step=step_of('%s-frame%d-cut-reentry'%(label,frame),host+reentry_changes(cb),CUT_STOP,('abs',S),'boundary',());steps.append(step)
                return steps,dict(p,outgoing=dict(p['outgoing'],pc=CUT_STOP),guard=None),frame+1
            step=step_of('%s-frame%d'%(label,frame),host+reentry_changes(cb),FRAME_RET,('abs',S+4),'return',end_alts)
    finally:o.close()


def clean_steps(steps):
    for s in steps:s['alts']=();s.pop('found_stop',None)
    return steps


# ----------------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------------
def apply_writes(ram,writes):
    ram=bytearray(ram);rec=[]
    for w in writes:
        assert w['kind']=='ram'
        ram[w['address']&0xffff:(w['address']&0xffff)+w['size']]=w['value'].to_bytes(w['size'],'big')
        rec.append(dict(address=w['address'],size=w['size'],hex='%0*x'%(w['size']*2,w['value']),why=w['why']))
    return bytes(ram),rec


def derive_fx(base,label,writes=(),entry=None,regs=None,sr=None,a7=None,a5=None,stack_ret=True,stack_extra=(),ret=FRAME_RET,external=None,note='',bank=None):
    """A declared fixture derived from a base fixture: declared initial RAM writes (recorded), declared initial registers / SR / A7 / A5 / entry PC."""
    ram,rec=apply_writes(base['ram'],writes)
    r=dict(base['regs']);r.update(regs or {})
    if a5 is not None:r['a5']=a5
    a7=base['initial_a7'] if a7 is None else a7
    bstate,page=(base['bank_state'],base['pvc']) if bank is None else bank
    fx=sc.make_fx(label,ram,{k:r[k] for k in KEYS14},(bstate,page),entry if entry is not None else base['entry_pc'],a7,dict(base['seed'],derived_from=base['label'],note=note),
        list(base.get('initial_host_writes',[]))+rec,([(a7,ret.to_bytes(4,'big'))] if stack_ret else [])+list(stack_extra),external=base['external'] if external is None else external,role='declared fixture: '+note)
    fx['regs']['a5']=r['a5'];fx['group']='f1c1'
    if sr is not None:fx['sr']=sr
    return fx


def seed_fixture(index):
    s=G['seeds'][index]
    prov=dict(kind='stage_entry_body final ff000 RAM output (recorded original 47a94 body run)',observation_sha256=sc.STAGE_ENTRY_SHA,case_index=index,family=s['family'],phase=s['phase'],ram_file=s['ram_file'],ram_sha256=s['ram_sha256'],
        bank=s['bank'],registers={k:hex(v) for k,v in s['regs'].items()})
    fx=sc.make_fx('seed-%03d'%index,s['ram'],s['regs'],bc.pvc_for(s['bank']),0x47da4,S,prov,(),[(S,FRAME_RET.to_bytes(4,'big'))],
        role='declared 47da4 direct entry: the recorded final RAM and registers of the original stage_entry_body run (SR 2000, A6 = 100b30, A5 = 108000), A7 = 1feffc with the declared dispatcher return LONG 2ac2 at (A7) (the original had ff000)')
    fx['regs']['a5']=A5V;fx['group']='f1c1'
    return fx


G={}
ITEMS=[]
# ----------------------------------------------------------------------------------
# Frame records
# ----------------------------------------------------------------------------------
def core_digest(p):
    h=hashlib.sha256()
    for key in ('incoming','outgoing','pvc_before','pvc_after','ram_before','ram_after','guard','waiting','wait','modeled_bank','bank_before','ff8_before','ff9_before','ff8_after','ff9_after'):
        v=p[key];h.update(key.encode());h.update(v if isinstance(v,(bytes,bytearray)) else jdump(v))
    h.update(struct.pack('>%dI'%len(p['pcs']),*p['pcs']));h.update(jdump(p['events']));h.update(jdump(lead_key(p)))
    return h.hexdigest()


def fresh_equal(program,fx,p,declared_sr):
    """The C++ one-run-one-frame view: a FRESH CPU (SR 2000, CCR 0, no history) from the recorded input state of the frame must produce the identical native record."""
    inc=p['incoming'];f=dict(fx)
    f.update(ram=p['ram_before'],pvc=p['pvc_before'],regs={k:inc[k] for k in KEYS},initial_a7=inc['a7'],entry_pc=inc['pc'],bank_state=(p['bank_before'],p['ff8_before'],p['ff9_before']),stop_pc=p['step_stop_pc'],checkpoints=[],stop_alts=())
    f.pop('sr',None)
    if declared_sr is not None:f['sr']=declared_sr
    o=F1c1Observer(RUNPROGRAM[0],True)
    try:
        o.prepare(f);q=o.run(allow_guard=bool(p['guard']))
    finally:o.close()
    return core_digest(q)==core_digest(p)


RUNPROGRAM=[None]


def state_sha(p):
    o=p['outgoing'];ports=ports_blob(p['events'])
    h=hashlib.sha256();h.update(b'F1C1-FRAME-STATE-v1');h.update(p['ram_after']);h.update(struct.pack('>16I',*[o[k] for k in REG16]));h.update(struct.pack('>II',o['pc'],p['modeled_bank']>>20))
    h.update(struct.pack('>I',len(ports)//9));h.update(ports);return h.hexdigest()


def hex_leads(p):return ['%x'%l['pc'] for l in p['leads']]


def change_row(c):
    if c['kind']=='ram':return ['ram','%x'%c['address'],c['size'],'%0*x'%(c['size']*2,c['value'])]
    if c['kind']=='pc':return ['pc','%x'%c['to']]
    return ['a7_add',c['delta']]


def dump_blobs(p):
    names=dict(ram_before=write_blob(p['ram_before']),ram_after=write_blob(p['ram_after']),pvc_before=write_blob(p['pvc_before']),pvc_after=write_blob(p['pvc_after']),ports=write_blob(ports_blob(p['events'])))
    names['trace']=write_blob(gzip.compress((json.dumps(dict(pcs=p['pcs'],events=p['events'],guard=p['guard'],leaders=[dict(pc=l['pc'],regs=l['regs']) for l in p['leads']]),sort_keys=True,separators=(',',':'))+'\n').encode(),9,mtime=0),'.json.gz')
    return names


def want_fresh(spec,p):
    if spec.get('fresh')=='all' or spec.get('dump')=='all':return True
    return model_applicable(p) or p['step'] in BOUNDARY_FRAMES


def frame_rows(program,spec,split,control,models,fresh):
    fx=spec['fixture'];rows=[];nsplit=collections.Counter(p['step'] for p in split)
    dump_all=spec.get('dump')=='all'
    for j,p in enumerate(control):
        inc=p['incoming'];o=p['outgoing'];ev=p['events']
        step=spec['steps'][p['step']]
        ports=ports_blob(ev)
        row=dict(step=p['step'],label=step['label'],in_pc='%x'%inc['pc'],in_a7='%x'%inc['a7'],out_pc='%x'%o['pc'],out_a7='%x'%o['a7'],stop_kind=(p['stop_evidence']['kind'] if p['stop_evidence'] else ('guard:'+p['guard']['problem'] if p['guard'] else 'checkpoint')),
            host_changes=[change_row(c) for c in p['host_changes']],instructions=len(p['pcs'])-1,split_phases=nsplit[p['step']],leaders=hex_leads(p),leader_regs_sha256=sha(jdump(lead_key(p))),
            regs16={k:'%08x'%o[k] for k in REG16},pc='%x'%o['pc'],bank=p['modeled_bank']>>20,ff8='%x'%p['ff8_after'],ff9='%x'%p['ff9_after'],ram_sha256=sha(p['ram_after']),pvc_sha256=sha(p['pvc_after']),
            ports_sha256=sha(ports),port_count=len(ports)//9,external_reads=sum(1 for e in ev if e['region']=='external'),trace_sha256=sha(jdump(dict(pcs=p['pcs'],events=ev))),state_sha256=state_sha(p),
            callback_after='%x'%u32(p['ram_after'],o['a6']&0xffff),w7a_after='%04x'%u16(p['ram_after'],(o['a6']+0x7a)&0xffff),waiting=p['waiting'],
            f1c1_instructions=sum(1 for pc in p['pcs'][:-1] if in_f1c1(pc)),f1c1_event_regions=dict(collections.Counter('%s/%s'%(e['region'],e['access']) for e in ev if in_f1c1(e['pc']))),
            fresh_equal=fresh[j],model_equal=models[j]['equal'] if models[j] is not None else None)
        if p['guard'] is not None:row['guard']=p['guard']
        if p['wait'] is not None:row['wait']=p['wait']
        dumped=dump_all or (spec.get('dump')=='boundary' and p['step'] in BOUNDARY_FRAMES)
        if dumped:row['dump']=dump_blobs(p)
        rows.append(row)
    return rows


def process_item(program,number,spec):
    t0=time.time()
    RUNPROGRAM[0]=program
    split,control,d_split,d_control=run_spec(program,spec)
    fx=spec['fixture'];models=[None]*len(control);model_rows=[]
    if spec.get('model'):
        for j,p in enumerate(control):
            declared=fx.get('sr') if (p['step']==0 and p['phase_in_step']==0) else None
            row=check_model_phase(program,'%s#phase%d'%(spec['label'],j),p,declared)
            models[j]=row;model_rows.append(row)
    fresh=[]
    for j,p in enumerate(control):
        declared=fx.get('sr') if (p['step']==0 and p['phase_in_step']==0) else None
        fresh.append(fresh_equal(program,fx,p,declared) if want_fresh(spec,p) else None)
    rows=frame_rows(program,spec,split,control,models,fresh)
    hits=collections.Counter(l['pc'] for q in control for l in q['leads'])
    covered=set()
    for q in control:covered.update(q['pcs'])
    cfile=CONDDIR/('%04d-%s.json.gz'%(number,re.sub(r'[^A-Za-z0-9_.-]','_',spec['label'])))
    steps_compact=[dict(label=s['label'],stop_pc='%x'%s['stop_pc'],a7=list(s['a7']) if s.get('a7') else None,expect=s.get('expect'),checkpoints=['%x'%c for c in s['checkpoints']],changes=[change_row(c) for c in s['changes']]) for s in spec['steps']]
    fsha=write_json_gz(cfile,dict(label=spec['label'],steps=steps_compact,frames=rows))
    last=control[-1]
    facts=condition_facts(spec,control,rows)
    unequal=[r['step'] for r in rows if r['fresh_equal'] is False];mun=[r['step'] for r in rows if r['model_equal'] is False]
    res=dict(number=number,label=spec['label'],group=spec['group'],note=spec.get('note',''),provenance=spec['provenance'],fixture=fc.summarize(spec,fx),guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),
        observed_guard=spec.get('observed_guard'),steps=len(spec['steps']),split_phases=len(split),control_phases=len(control),frames=len([s for s in spec['steps'] if '-release' not in s['label'] and 'gate-' not in s['label'] and '-hold' not in s['label']]),
        final_pc='%x'%last['outgoing']['pc'],final_stop_kind=rows[-1]['stop_kind'],reproduced_twice=True,continuous_split_equivalent=True,split_digest_sha256=d_split,control_digest_sha256=d_control,condition_file=cfile.name,condition_file_sha256=fsha,
        fresh_frames=len(rows),fresh_checked=sum(1 for x in fresh if x is not None),fresh_frames_equal=sum(1 for x in fresh if x),
        model_frames=sum(1 for m in models if m is not None and m.get('equal') is not None),model_frames_equal=sum(1 for m in models if m is not None and m.get('equal')),model_frames_not_applicable=sum(1 for m in models if m is not None and m.get('equal') is None),
        f1c1_frames=sum(1 for r in rows if r['f1c1_instructions']),
        host_writes=[dict(step=i,changes=[change_row(c) for c in s['changes'] if c['kind']=='ram' and c['address'] not in (S,0x104ca4)]) for i,s in enumerate(spec['steps']) if any(c['kind']=='ram' and c['address'] not in (S,0x104ca4) for c in s['changes'])],
        instructions=sum(len(p['pcs'])-1 for p in control),dumped_frames=sum(1 for r in rows if 'dump' in r),state_sha256_last=rows[-1]['state_sha256'])
    mexec=set()
    for m in model_rows:mexec.update(m.get('exec_pcs',()))
    for m in model_rows:m.pop('exec_pcs',None)
    return dict(number=number,result=res,hits=dict(hits),covered=sorted(covered),facts=facts,seconds=time.time()-t0,runs=RUNS[0],fresh_unequal=unequal,model_unequal=mun,model_exec=sorted(mexec),
        model_discrepancies=[m for m in model_rows if m.get('equal') is False][:3])


CONTRACT_WINDOWS=((0x474f4,0x47540),(0xd99e2,0xdd4be),(0x472be,0x474e0))           # group pointer table, groups 0..4, groups 5..18 (contract "ROM 자료 window")
ROM_WINDOWS=[]                                                                       # table + the 19 group extents of the ROM catalog (filled by main() before the workers fork)


def condition_facts(spec,control,rows):
    """Per-condition facts used by the contract claims."""
    first=control[0];last=control[-1];prog=G['program']
    f=dict(frames=len(control),stops=dict(collections.Counter(r['stop_kind'] for r in rows)))
    ro=last['ram_after']
    rec=u32(ro,(A6V+0x76)&0xffff)
    f['exit']=dict(d680=ro[0xd680],d681=ro[0xd681],d683=ro[0xd683],d684=ro[0xd684],d686=u16(ro,0xd686),d68c=u16(ro,0xd68c),cb=u32(ro,0xb30),r76=rec,c7c=ro[0xbac],c7d=ro[0xbad],w7a=u16(ro,0xbaa),g62=ro[0xb92],h107ded=ro[0x7ded],h104ca0=u16(ro,0x4ca0))
    if 0<=rec<0x100000:f['record']=dict(addr=rec,index=prog[rec],music=int.from_bytes(prog[rec+16:rec+18],'big'))
    f['entry']=dict(d680=first['ram_before'][0xd680],d681=first['ram_before'][0xd681],d686=u16(first['ram_before'],0xd686),h107ded=first['ram_before'][0x7ded],h107dea=u16(first['ram_before'],0x7dea))
    seq=[]
    for i,r in enumerate(rows):
        starts=[x for x in r['leaders'] if int(x,16) in START_SET]
        if starts or r['f1c1_instructions']:seq.append(dict(frame=i,leaders=starts,stop=r['stop_kind'],callback_after=r['callback_after'],out_pc=r['out_pc'],w7a_after=r['w7a_after']))
    f['f1c1_frames']=seq
    ev=last.get('stop_evidence')
    f['final_evidence']=dict(kind=ev['kind'],previous_pc=ev.get('previous_pc'),previous_bytes=ev.get('previous_bytes'),outgoing_pc=ev['outgoing_pc']) if ev else None
    f['wait_rows']=[dict(step=p['step'],pc=p['wait']['pc'],state=state_sha(p),a7=p['outgoing']['a7'],byte_107ded=p['ram_after'][0x7ded],word_107dea=u16(p['ram_after'],0x7dea),d0=p['outgoing']['d0']) for p in control if p['waiting']]
    f['stack_bytes_after']=last['ram_after'][(S&0xffff)-8:(S&0xffff)+8].hex()
    f['stack_bytes_before']=first['ram_before'][(S&0xffff)-8:(S&0xffff)+8].hex()
    reg=collections.Counter()
    for r in rows:
        for k,v in r['f1c1_event_regions'].items():reg[k]+=v
    f['f1c1_regions']=dict(reg)
    rr={}
    for p in control:
        for e in p['events']:
            if e['region']=='fixed' and e['access']=='read' and in_f1c1(e['pc']):
                w=next((k for k,(a,b) in enumerate(ROM_WINDOWS) if a<=e['address'] and e['address']+e['size']<=b),-1)
                oc=not any(a<=e['address'] and e['address']+e['size']<=b for a,b in CONTRACT_WINDOWS)
                r_=rr.setdefault('%x'%e['pc'],dict(size=e['size'],low=e['address'],high=e['address']+e['size']-1,reads=0,windows={},outside_contract=0,outside_max=0))
                r_['low']=min(r_['low'],e['address']);r_['high']=max(r_['high'],e['address']+e['size']-1);r_['reads']+=1;r_['windows'][str(w)]=r_['windows'].get(str(w),0)+1
                if oc:r_['outside_contract']+=1;r_['outside_max']=max(r_['outside_max'],e['address']+e['size']-1)
    f['f1c1_rom_reads']=rr
    return f


def build_spec(program,fx,label,group,prov,steps=None,setup=(),rules=(),frames=None,expect_guard=None,note='',model=True,dump='all',max_frames=400,end_alts=(CUT_STOP,TRAP_STOP),first_stop=FRAME_RET,first_a7=('abs',S+4),guard_ok=False,expect_guard_keys=None,
        gate_idem=0,gate_limit=3,hold=None,reenter=True,fresh=None):
    guard=None
    if steps is None:
        steps,last,nframes=plan_frames(program,fx,label,setup,rules,max_frames=max_frames,frames=frames,allow_guard=expect_guard is not None or guard_ok,end_alts=end_alts,first_stop=first_stop,first_a7=first_a7,gate_idem=gate_idem,gate_limit=gate_limit,hold=hold,reenter=reenter)
        guard=last['guard'];plan_pcs=list(PLAN_PCS)
    else:
        plan_pcs=None
        spec=dict(label=label,fixture=fx,steps=steps,guarded=True,guard={},probe=True);ph=run_chain(program,spec,True);guard=ph[-1]['guard']
        for st,p in zip(steps,ph):st.setdefault('expect','wait' if p['waiting'] else ('guard' if p['guard'] is not None else 'return'))
    clean_steps(steps)
    spec=dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,model=model and guard is None,dump=dump,note=note)
    if fresh:spec['fresh']=fresh
    if guard_ok and guard is None:expect_guard=None
    elif guard_ok:expect_guard=dict(expect_guard_keys or {})
    if expect_guard is not None:
        assert guard is not None,(label,'expected a native guard',expect_guard)
        for k,v in expect_guard.items():assert guard.get(k)==v,(label,k,guard)
        spec.update(guarded=True,guard=dict(expect_guard),observed_guard=guard,model=False)
    else:assert guard is None,(label,guard)
    if plan_pcs is not None:
        # the checkpoints are taken from the continuous probe run of the plan (the same persistent-CPU run that discovered the steps; identical rule to with_checkpoints)
        for index,step in enumerate(spec['steps']):
            order=[]
            if index<len(plan_pcs):
                entry=plan_pcs[index][0]
                for pc in plan_pcs[index][1:]:
                    if pc in CK_SET and pc not in order and pc!=entry and pc!=step['stop_pc']:order.append(pc)
            step['checkpoints']=order
    else:with_checkpoints(program,spec)
    return spec


# ----------------------------------------------------------------------------------
# Natural seeds: the 142 final ff000 RAM outputs of the recorded original stage_entry_body runs (137 begin + 5 release guard rows)
# ----------------------------------------------------------------------------------
def load_seeds():
    obs=json.loads(sc.pin(sc.STAGE_ENTRY,sc.STAGE_ENTRY_SHA));folder=sc.STAGE_ENTRY.parent;seeds=[]
    assert obs['cases']==obs['completed_cases']==len(obs['results'])==142 and obs['failure'] is None
    for i,r in enumerate(obs['results']):
        assert r['case_index']==i
        ph=[p for p in r['phases'] if p['final_pc']==0xff000];assert len(ph)==1 and ph[0]['name'] in ('begin','release-poisoned-prefix'),(i,[p['name'] for p in r['phases']])
        release=ph[0]['name']!='begin'
        p=ph[0];ram=sc.pin(folder/p['ram_file'],p['ram_sha256']);assert len(ram)==0x10000
        res=p['result'];regs={k:res[k] for k in KEYS14+('a5',)}
        assert regs['a6']==A6V and regs['a5']==A5V and p['final_a5']==A5V,(i,hex(regs['a6']))
        seeds.append(dict(index=i,release=release,family=r['fixture']['family'],phase=p['name'],ram=ram,ram_file=p['ram_file'],ram_sha256=p['ram_sha256'],regs=regs,bank=res['bank']))
    assert sum(1 for x in seeds if not x['release'])==137 and sum(1 for x in seeds if x['release'])==5
    return seeds


def transition_fixture(index):
    """Cases 66..69 of the transition observation: the state at the 477ee boundary (A6 = 102000, A7 = 1feffc, fill RAM)."""
    obs=json.loads(sc.pin(TRANSITION,TRANSITION_SHA));row=[x for x in obs['results'] if x['index']==index];assert len(row)==1
    ph=row[0]['phases'][-1];assert ph['stop_pc']==0x477ee
    folder=TRANSITION.parent;names={k:v for k,v in ph['artifacts'].items() if k.endswith('_ram_after.bin') or k.endswith('_pvc_after.bin')}
    ram=pvc=None
    for name,digest in names.items():
        data=sc.pin(folder/name,digest)
        if name.endswith('_ram_after.bin'):ram=data
        else:pvc=data
    o=ph['outgoing'];assert o['pc']==0x477ee and o['a6']==0x102000 and o['a7']==S and ph['modeled_bank']==0x200000
    regs={k:o[k] for k in KEYS14+('a5',)}
    prov=dict(kind='transition observation case %d (%s) state at the 477ee boundary'%(index,row[0]['selection']['label']),observation_sha256=TRANSITION_SHA,case_index=index,ram_sha256=sha(ram),pvc_sha256=sha(pvc),
        registers={k:hex(v) for k,v in o.items()},long_at_a7='%08x'%u32(ram,S&0xffff),note='fill RAM (garbage object pool): only the run to the stop 47934 is meaningful; the 28ae call at 47934 follows the garbage pool')
    fx=sc.make_fx('transition-case%d'%index,ram,regs,((0x200000,0xa0,0x1000),pvc),0x477ee,S,prov,(),[],role='declared 477ee entry: the recorded transition case %d output state (A6 = 102000, A7 = 1feffc)'%index)
    fx['regs']['a5']=A5V;fx['group']='f1c1';return fx


# ----------------------------------------------------------------------------------
# Runtime fixtures: zero RAM -> original 2790 -> 3ef2 -> 49a1a(D0 = 0) (Unicorn, the isolated 1feffc call stack of verify_palette_state.call), then declared host writes
# ----------------------------------------------------------------------------------
RT_CACHE={}


def rt_base_ram():
    if 'ram' not in RT_CACHE:
        import verify_object_reset as vor
        import verify_palette_state as vps
        from unicorn import m68k_const as m
        cpu=vor.make_cpu(G['program']);cpu.mem_write(0x100000,bytes(65536));vps.call(cpu,0x2790);vps.call(cpu,0x3ef2)
        cpu.reg_write(m.UC_M68K_REG_D0,0);vps.call(cpu,0x49a1a);RT_CACHE['ram']=bytes(cpu.mem_read(0x100000,65536))
    return RT_CACHE['ram']


def catalog_groups(program):
    """Group tables and record addresses of the ROM catalog (stage group pointers at 474f4)."""
    W_=lambda a:int.from_bytes(program[a:a+2],'big');L_=lambda a:int.from_bytes(program[a:a+4],'big');out=[]
    for g in range(19):
        a=L_(0x474f4+4*g)+2;recs=[]
        while True:
            s=W_(a);a+=2
            if s==0:break
            recs.append(a);a+=s if s<0x8000 else s-0x10000
        out.append(recs)
    return out


def catalog_extents(program):
    """[start, end) of the 19 catalog groups of the ROM (end = after the zero size WORD that ends the record list)."""
    W_=lambda a:int.from_bytes(program[a:a+2],'big');L_=lambda a:int.from_bytes(program[a:a+4],'big');out=[]
    for g in range(19):
        base=L_(0x474f4+4*g);a=base+2
        while True:
            s=W_(a);a+=2
            if s==0:break
            a+=s if s<0x8000 else s-0x10000
        out.append((base,a))
    return out


def frame_base_writes():
    """The F1b frame base RAM the 480bc frames of the F1c1 paths need (player nodes, U7 buffer rows, U2/U3 node records); declared fixture RAM, nothing is executed."""
    p=[(0x100cb8,4,0),(0x100cb8+0x61,1,0x7f),(0x100da8,4,0x2710),(0x100da8+0x61,1,0x80),(0x10d68e,1,0xfc),(0x10dc88,4,0x10db88),(0x10db84,4,0x11a5225a),(0x10de2e,1,1)]
    for i in range(32):p.append((0x10db88+2*i,2,(0x8001+i*0x1357)&0xffff))
    for i in range(8):p.append((0x10d4e6+0x2c*i+0x26,4,0xffff0000))
    for b in (0x10d746,0x10d918):p+=[(b,4,0xdeadbeef),(b+0xcc,4,0x01020304),(b+0xd0,2,0x5555),(b+0x1ce,2,0x6666),(b+0x1d0,2,0x7777)]
    return [W(a,n,v,'declared F1b frame base RAM (player nodes, U7 buffer rows, U2/U3 node records): %x'%a) for a,n,v in p]


def rt_fixture(label,stage,area,music,entry,extra=(),bank=2,regs=None,note=''):
    """Declared runtime fixture: base RAM (original 2790 -> 3ef2 -> 49a1a) + frame base + the host writes of the contract (10d680 = group, 10d681 = area, 10d683 = ff, 10d686 = music, 104d74 = 104d76 = 0)."""
    writes=frame_base_writes()+[W(0x10d680,1,stage,'declared host write: BYTE 10d680 (stage group) := %02x'%stage),W(0x10d681,1,area,'declared host write: BYTE 10d681 (area) := %02x'%area),W(0x10d683,1,0xff,'declared host write: BYTE 10d683 := ff'),
        W(0x10d686,2,music&0xffff,'declared host write: WORD 10d686 (current music) := %04x'%(music&0xffff)),W(0x104d74,2,0,'declared host write: WORD 104d74 := 0'),W(0x104d76,2,0,'declared host write: WORD 104d76 := 0')]+list(extra)
    ram,rec=apply_writes(rt_base_ram(),writes)
    r=dict((k,0) for k in KEYS14);r.update(a5=A5V,a6=A6V);r.update(regs or {})
    prov=dict(kind='runtime fixture (contract "시작 상태 2"): original 2790 -> 3ef2 -> 49a1a(D0 = 0) on a zero RAM + declared host writes',base_ram_sha256=sha(rt_base_ram()),stage=stage,area=area,music='%04x'%(music&0xffff),entry=hex(entry),note=note,host_writes=rec)
    fx=sc.make_fx(label,ram,r,bc.pvc_for(bank),entry,S,prov,(),[(S,FRAME_RET.to_bytes(4,'big'))],role='declared %x entry on the runtime fixture RAM (A5 = 108000, A6 = 100b30, A7 = 1feffc with the return LONG 2ac2 at (A7))'%entry)
    fx['regs']['a5']=A5V;fx['group']='f1c1';return fx


NAT_CAP=235                                                 # the last frame of the F1b prefix: its output is the declared entry state of the F1c1 stage of a staged seed


def light_row(program,index,step,p):
    """One recorded frame of a staged natural seed's F1b prefix (the full-fidelity conditions are the F1c1 frames; the prefix frames are recorded by one continuous run reproduced by a second run)."""
    o=p['outgoing'];ev=p['events'];ports=ports_blob(ev);pcs=p['pcs'];prev=pcs[-2] if len(pcs)>=2 else None
    ok=o['pc']==FRAME_RET and prev is not None and program[prev:prev+2]==b'\x4e\x75' and u32(p['ram_after'],o['a7']-4)==FRAME_RET
    return dict(step=index,label=step['label'],in_pc='%x'%p['incoming']['pc'],in_a7='%x'%p['incoming']['a7'],out_pc='%x'%o['pc'],out_a7='%x'%o['a7'],stop_kind='return' if ok else ('guard:'+p['guard']['problem'] if p['guard'] else 'other'),
        previous_pc=None if prev is None else '%x'%prev,host_changes=[change_row(c) for c in step['changes']],instructions=len(pcs)-1,regs16={k:'%08x'%o[k] for k in REG16},pc='%x'%o['pc'],bank=p['modeled_bank']>>20,
        ram_sha256=sha(p['ram_after']),pvc_sha256=sha(p['pvc_after']),ports_sha256=sha(ports),port_count=len(ports)//9,leaders=hex_leads(p),state_sha256=state_sha(p),callback_after='%x'%u32(p['ram_after'],o['a6']&0xffff),
        w7a_after='%04x'%u16(p['ram_after'],(o['a6']+0x7a)&0xffff),core_digest=core_digest(p))


def item_natural(number,item):
    """A natural seed.  The DUMP_SEEDS get the full treatment over all 238 frames (split / continuous, each twice, fresh-CPU frames, model, full dumps).  Every other seed runs the F1b prefix (frames 0..235, no F1c1
    code: the F1b unit) as ONE continuous probe run reproduced by a second continuous run (core digests of all frames compared), records the full-state SHA of every frame, dumps the boundary frames, and runs the
    F1c1 stage (frames 236, 237: the declared direct state = the output of frame 235 plus the recorded step-236 host/re-entry changes) with the full treatment; its final state SHA must equal the one of the chain."""
    i=item['ref'];program=G['program'];fx=seed_fixture(i)
    if i in DUMP_SEEDS:
        spec=build_spec(program,fx,'natural-%03d'%i,'natural',fx['seed'],rules=[r_dd44(),r_child62()],dump='all',note='%s seed %d (full treatment over all frames)'%(G['seeds'][i]['family'],i))
        return process_item(program,number,spec)
    RUNPROGRAM[0]=program;label='natural-%03d'%i
    rows=[];digests=[];cap={}
    def on_run(index,step,p):
        r=light_row(program,index,step,p);rows.append(r);digests.append(r['core_digest'])
        if index in BOUNDARY_FRAMES:r['dump']=dump_blobs(p)
        if index==NAT_CAP:cap.update(outgoing=dict(p['outgoing']),ram_after=p['ram_after'],pvc_after=p['pvc_after'],bank=(p['modeled_bank'],p['ff8_after'],p['ff9_after']))
    steps,last,nframes=plan_frames(program,fx,label,rules=[r_dd44(),r_child62()],on_run=on_run)
    assert nframes==238 and len(rows)==238 and cap,(label,nframes,len(rows))
    plan_steps=clean_steps(copy.deepcopy(steps))
    for st in plan_steps:st['checkpoints']=[]
    specA=dict(label=label,fixture=fx,steps=plan_steps,provenance=fx['seed'],guarded=False,model=False)
    digests2=[];run_chain(program,specA,True,sink=lambda p:digests2.append(core_digest(p)))
    assert digests2==digests,(label,'prefix chain not reproduced')
    o=cap['outgoing'];setup_b=steps[NAT_CAP+1]['changes']
    fxb=dict(fx);fxb.update(label=label+'-f1c1',ram=cap['ram_after'],pvc=cap['pvc_after'],regs={k:o[k] for k in KEYS},initial_a7=o['a7'],entry_pc=o['pc'],bank_state=cap['bank'],stop_pc=FRAME_RET,checkpoints=[],initial_host_writes=[],
        seed=dict(fx['seed'],captured_from='the output of frame 235 of the natural chain (declared direct state: registers, RAM and PVC page of the recorded frame; the step-236 changes are re-applied)'),
        preparation=dict(role='captured native state at the end of frame 235 of %s'%label,source_pc=o['pc']))
    prov=dict(fx['seed'],stage='F1c1 frames 236, 237 of the natural chain',prefix_frames=NAT_CAP+1)
    specB=build_spec(program,fxb,label,'natural',prov,rules=[r_child62()],setup=setup_b,dump='all',note='%s seed %d: F1c1 stage (frames 236, 237) of the natural chain'%(G['seeds'][i]['family'],i))
    r=process_item(program,number,specB)
    res=r['result']
    assert res['frames']==2,(label,res['frames'])
    # continuity: the F1c1 stage reproduces the frames 236, 237 of the chain exactly (full-state SHA of every frame)
    cond=json.loads(gzip.decompress((CONDDIR/res['condition_file']).read_bytes()))
    sb=[x['state_sha256'] for x in cond['frames']]
    assert sb==[rows[236]['state_sha256'],rows[237]['state_sha256']],(label,'F1c1 stage state SHA differs from the chain',sb)
    pre=rows[:NAT_CAP+1]
    pfile=CONDDIR/('%04d-%s-prefix.json.gz'%(number,label))
    psha=write_json_gz(pfile,dict(label=label,note='F1b prefix frames 0..235 of the natural chain: one continuous run reproduced by a second continuous run (core digests of every frame equal); no F1c1 code executes in these frames (no split checkpoint exists)',frames=pre))
    res.update(label=label,frames=238,steps=len(steps),instructions=res['instructions']+sum(x['instructions'] for x in pre),prefix=dict(frames=len(pre),reproduced_twice=True,digest_sha256=sha(''.join(digests).encode()),state_sha_chain_sha256=sha(''.join(x['state_sha256'] for x in rows).encode()),
        prefix_file=pfile.name,prefix_file_sha256=psha,all_stop_at_2ac2_by_rts_480f0=all(x['stop_kind']=='return' and x['previous_pc']=='480f0' for x in pre),boundary_dumps=[x['step'] for x in pre if 'dump' in x]),
        host_writes=[dict(step=k,changes=[change_row(c) for c in st['changes'] if c['kind']=='ram' and c['address'] not in (S,0x104ca4)]) for k,st in enumerate(steps) if any(c['kind']=='ram' and c['address'] not in (S,0x104ca4) for c in st['changes'])])
    f=r['facts'];f['f1c1_frames']=[dict(e,frame=e['frame']+NAT_CAP+1) for e in f['f1c1_frames']]
    f['stops']=dict(collections.Counter([x['stop_kind'] for x in pre]+[x['stop_kind'] for x in cond['frames']]))
    return r


def item_release(number,item):
    """The 5 release-poisoned-prefix outputs are NOT natural seeds (contract decision 12): WORD 104d8a = 8001 makes the frame helper U1 3c60 CMP.W (A1),D0 read an odd address (an address error on a real 68000).  They are guard rows."""
    i=item['ref'];program=G['program'];fx=seed_fixture(i);prov=dict(fx['seed'],role='guard row (contract decision 12), not a natural seed')
    spec=build_spec(program,fx,'release-guard-%03d'%i,'release-guard',prov,rules=[r_dd44(),r_child62()],guard_ok=True,expect_guard_keys=dict(problem='unsupported_odd_data_access'),note='release-poisoned-prefix output %d: odd WORD access expected'%i)
    return process_item(program,number,spec)


def item_runtime(number,item):
    g,ar,mm,entry=item['ref'];program=G['program'];rec=G['groups'][g][ar];mu=int.from_bytes(program[rec+16:rec+18],'big')
    music=mu if mm=='same' else mu^0xffff
    label='rt-g%02d-a%02d-%s-%x'%(g,ar,mm,entry)
    fx=rt_fixture(label,g,ar,music,entry,note='catalog record %x (index %02x, record music %04x), 10d686 %s'%(rec,program[rec],mu,'= record music' if mm=='same' else '= complement'))
    spec=build_spec(program,fx,label,'runtime',fx['seed'],rules=[r_child62(0,0xff)],dump='all',note=fx['seed']['note'])
    return process_item(program,number,spec)


def item_transition(number,item):
    index,mode=item['ref'];program=G['program'];fx=transition_fixture(index)
    if mode=='stop':
        spec=build_spec(program,fx,'transition-%d-to-47934'%index,'transition',fx['seed'],end_alts=(),first_stop=TRANS_STOP,first_a7=('abs',S),dump='all',note='477ee entry of the transition case %d, run to the stop 47934 (BRA.W at 478b8, index 0c)'%index)
    else:
        spec=build_spec(program,fx,'transition-%d-past-47934'%index,'transition-guard',fx['seed'],end_alts=(),guard_ok=True,dump='all',note='the same run without the 47934 stop: the 28ae call follows the garbage object pool (negative case; the machine contract needs a checked error and full rollback)')
    return process_item(program,number,spec)


def item_typed(number,item):
    spec=G['typed'][item['ref']](G['program'])
    return process_item(G['program'],number,spec)


def run_item(number):
    item=ITEMS[number];RUNS[0]=0;DISCREPANCIES.clear();BLOB_SEEN.clear()
    try:
        r=globals()['item_'+item['kind']](number,item);r['runs']=RUNS[0];r['discrepancies']=list(DISCREPANCIES);return r
    except Exception as e:
        import traceback
        return dict(number=number,error=repr(e)[:1500],trace=traceback.format_exc()[-3500:],kind=item['kind'],ref=item.get('ref'))


# ----------------------------------------------------------------------------------
# Typed conditions
# ----------------------------------------------------------------------------------
TYPED=[]


def typed(label,group,make_base,writes=(),entry=None,regs=None,sr=None,a7=None,a5=None,stack_ret=True,stack_extra=(),ret=FRAME_RET,external=None,setup=(),rules=(),frames=None,expect_guard=None,guard_ok=False,steps=None,
        note='',model=True,max_frames=400,end_alts=(CUT_STOP,TRAP_STOP),first_stop=FRAME_RET,first_a7=('abs',S+4),bank=None,free_a6=False,gate_idem=0,gate_limit=3,hold=None,reenter=True,step_limit=None,dump='all',fresh=None):
    """make_base: callable (program) -> a base fixture dict; the condition is derived from it by declared writes / registers."""
    def make(program):
        b=make_base()
        fx=derive_fx(b,label,writes,entry,regs,sr,a7,a5,stack_ret,stack_extra,ret,external,note,bank)
        if free_a6:fx['free_a6']=True
        if step_limit is not None:fx['step_limit']=step_limit
        prov=dict(kind='declared typed fixture',note=note,base=b['label'],base_provenance=b['seed'],declared_initial_writes=[dict(address=hex(w['address']),size=w['size'],value=hex(w['value']),why=w['why']) for w in writes],
            declared_registers={k:hex(v) for k,v in (regs or {}).items()},declared_sr=sr,declared_a7=a7,declared_a5=a5,entry=hex(fx['entry_pc']),return_long=hex(ret) if stack_ret else None,declared_step_limit=step_limit)
        st=steps(program,fx) if steps is not None else None
        rl=rules() if callable(rules) else list(rules)
        return build_spec(program,fx,label,group,prov,st,setup,rl,frames,expect_guard if not guard_ok else None,note,model,dump,max_frames,end_alts,first_stop,first_a7,guard_ok=guard_ok,expect_guard_keys=expect_guard,
            gate_idem=gate_idem,gate_limit=gate_limit,hold=hold,reenter=reenter,fresh=fresh)
    make.label=label;TYPED.append(make)


SCRATCH_REC=0x10e900                                         # declared RAM catalog record (free in the runtime base RAM: asserted)


def rec_music(g,a,mm):
    """Music WORD of the ROM catalog record (g,a) for 10d686: the record's own music ('same') or its complement ('diff')."""
    program=G['program'];rec=G['groups'][g][a];mu=int.from_bytes(program[rec+16:rec+18],'big');return mu if mm=='same' else mu^0xffff


def rtb(stage,area,music,entry=0x477ee,extra=(),bank=2,regs=None,note=''):
    """make_base for typed(): a runtime fixture."""
    def make():
        fx=rt_fixture('rtbase-%02x-%02x-%04x-%x'%(stage,area,music,entry),stage,area,music,entry,extra,bank,regs,note)
        return fx
    return make


def ram_record(idx,music,addr=SCRATCH_REC,why='declared RAM catalog record'):
    """Declared writes of a RAM record (BYTE +0 = entry-effect index, WORD +10 = music) and the record pointer LONG 76(A6)."""
    return [W(addr,1,idx,'%s: BYTE +0 (entry-effect index) := %02x'%(why,idx)),W(addr+0x10,2,music,'%s: WORD +10 (music) := %04x'%(why,music)),W(A6V+0x76,4,addr,'declared record pointer LONG 76(A6) := %x'%addr)]


def r_at_cb(cb,writes,once=True):
    """Declared host writes at the first frame boundary at which the installed callback LONG (A6) is `cb`."""
    st=dict(fired=False)
    def rule(done,ram,c,o):
        if c!=cb or (once and st['fired']):return []
        st['fired']=True;return list(writes)
    return rule


def define_typed():
    TYPED.clear()
    C62=lambda:[r_child62(0,0xff)]
    # ---- stage / area / group variants of the catalog walk (474e2 47540)
    for stage in (0x13,0x21,0xff):
        typed('stage-%02x-474ea'%stage,'catalog',rtb(stage,0,rec_music(0,0,'diff')),rules=C62,note='stage %02x >= 13: 474e2 CMPI.W #13 BCS fails, 474ea MOVEQ #0,D0 selects group 0'%stage)
    typed('stage-12-last-group','catalog',rtb(0x12,0,rec_music(18,0,'diff')),rules=C62,note='stage 12 (the last group): CMPI.W #13 passes, group table index 12')
    typed('area-7f-retry','catalog',rtb(0,0x7f,rec_music(0,0,'diff')),rules=C62,note='area 7f: 47540 walks the whole list, 4754a MOVEA.W #0,A0 returns null, 4781a CLR.B 7d(A6) and BRA 477fa retry with area 0')
    typed('area-0b-retry','catalog',rtb(0,11,rec_music(0,0,'diff')),rules=C62,note='area 0b = the record count of group 0: the walk ends at the zero size WORD, null, retry with area 0')
    typed('area-0a-last-record','catalog',rtb(0,10,rec_music(0,10,'diff')),rules=C62,note='area 0a = the last record of group 0')
    typed('area-ff-stage1-retry','catalog',rtb(1,0xff,rec_music(1,0,'diff')),rules=C62,note='area ff on group 1: retry with area 0')
    for stage in (9,0x0a,0x0f):
        typed('empty-group-%02x-loop'%stage,'catalog-guard',rtb(stage,0,0x1234),expect_guard=dict(problem='step_limit'),step_limit=30000,
            note='stage %02x selects an empty group: 47540 returns null for every area, 4781a CLR.B 7d(A6) / BRA 477fa loop forever (contract decision 7); the observer stops at its declared instruction watchdog (the machine rolls back at the block budget)'%stage)
    # ---- 72f0 palette gate at 478de (Waiting, declared IRQ palette effect)
    gate_base=lambda **kw:rtb(1,0,rec_music(1,0,'same'),extra=kw.get('extra',()),bank=kw.get('bank',2))
    for byte in (0x80,0xff,0xc3):
        typed('gate-wait-107ded-%02x-idem2-irq'%byte,'gate',gate_base(extra=[W(0x107ded,1,byte,'declared palette flag BYTE 107ded := %02x (bit7 set: the 72f0 gate blocks)'%byte)]),rules=C62,gate_idem=2,
            note='record index 00: 478de entered with BYTE 107ded bit7 = 1: Waiting at 478de, two no-effect resumes return the same Waiting, then the declared IRQ palette effect lets it pass')
    typed('gate-wait-107ded-81-107dea-nonzero','gate',gate_base(extra=[W(0x107ded,1,0x81,'declared BYTE 107ded := 81'),W(0x107dea,2,1,'declared WORD 107dea := 1 (the original IRQ path 72fa BNE.W 873a does not clear bit7)')]),rules=C62,gate_idem=1,gate_limit=3,
        note='gate blocked and WORD 107dea <> 0: the declared effect does not clear bit7, the Waiting persists')
    for byte in (0x7f,0x00,0x01):
        typed('gate-pass-107ded-%02x'%byte,'gate',gate_base(extra=[W(0x107ded,1,byte,'declared BYTE 107ded := %02x (bit7 clear: the gate passes at once)'%byte)]),rules=C62,note='gate open: 72f0 returns C=1')
    typed('gate-wait-bank3','gate',gate_base(extra=[W(0x107ded,1,0x80,'declared palette flag BYTE 107ded := 80')],bank=3),rules=C62,gate_idem=1,note='gate wait with the PVC bank register selecting physical 300000')
    typed('natural-gate-0','gate',lambda:seed_fixture(0),entry=None,rules=lambda:[r_dd44(),r_at_cb(0x478de,[W(0x107ded,1,0x80,'declared palette flag BYTE 107ded := 80 (set between the frames that install and enter 478de)')])],gate_idem=1,
        note='natural seed 0 chain (47da4 .. 477ee): BYTE 107ded := 80 declared after the frame that installs 478de: Waiting, one no-effect resume, the declared IRQ effect, 479b0',dump='boundary')
    # ---- 478a8 computed table on a RAM record (direct entry 47896), every slot / index
    def tbl(idx,label,music=0x1234,extra=(),rules=C62,**kw):
        typed('table-%02x-%s'%(idx,label),kw.pop('group','table'),rtb(0,0,music,entry=0x47896),writes=ram_record(idx,music)+list(extra),entry=0x47896,rules=rules,**kw)
    tbl(0x00,'slot0-478c4-gate',note='index 00 -> 478ac -> 478c4 (8c16, callback 478de, gate, ca8a, 479b0)')
    tbl(0x04,'slot1-478f0-countdown-16',note='index 04 -> 478f0: 7a(A6) := 10, callback 4790a re-entered until the countdown borrows -> ca8a -> 479b0')
    tbl(0x08,'slot2-4791c-countdown-60',note='index 08 -> 4791c: caf0, 7a(A6) := 3c, D0..D2 = 1f, D3 = 1e, BRA 478fe; 61 frames')
    tbl(0x0c,'slot3-47934-28ae-ok',note='index 0c -> 47934: 28ae(4fcb8) success -> 47984 -> callback 4798e (62(A6) cleared) -> declared child completion -> 479a6 -> callback 479b0')
    tbl(0x10,'slot4-4794c-28ae-ok',note='index 10 -> 4794c: 28ae(4fd0a) success -> 47960 -> 47984')
    tbl(0x14,'slot5-47964-28ae-ok-47978',note='index 14 -> 47964: 28ae(4ff4c) success -> 47978 (WORD 5690 / 5692 into 76 / 78 of the new object) -> 47984')
    for idx in (0x0c,0x10,0x14):
        tbl(idx,'28ae-fails-bcc-taken-478c4',extra=[W(0x104ca0,2,0,'declared free count WORD 104ca0 := 0 (28ae fails: D0.W = 0 >= 0 unsigned, C = 0)')],note='slot %02x with 28ae failing: BCC at 47944 / 4795c / 47974 taken -> 478c4 (index 00 path with the gate)'%idx)
    tbl(0x14,'child-wait3',rules=lambda:[r_child62(3,1)],note='index 14: the 4798e callback waits 3 further frames (62(A6) = 0) before the declared child completion')
    tbl(0x0c,'child-62-already-set',extra=[W(A6V+0x62,1,0x77,'declared RAM: BYTE 62(A6) := 77 (cleared by 47984 before the callback)')],note='47984 CLR.B 62(A6) clears the stale value')
    for idx in (0x02,0x06,0x0a,0x0e,0x12,0x16):
        tbl(idx,'interior-pc',group='table-guard',expect_guard=dict(problem='unsupported_code_target',target=TABLE_BASE+idx),note='index %02x -> 478ac+%02x = %x: the BRA.W displacement WORD of a table slot (inside an instruction); the machine contract: unsupported error and rollback'%(idx,idx,TABLE_BASE+idx))
    for idx in (0x01,0x03,0x05,0x07,0x09,0x0b,0x0d,0x0f,0x11,0x13,0x15,0x17):
        tbl(idx,'odd-pc',group='table-guard',expect_guard=dict(problem='unsupported_code_target',target=TABLE_BASE+idx,odd_pc=True),note='index %02x -> odd PC %x: an address error on the original CPU'%(idx,TABLE_BASE+idx))
    for idx in (0x18,0x19,0x1a,0x40,0x80,0xff):
        tbl(idx,'trap-boundary-478a6',group='table-boundary',note='record index %02x >= 18: CMPI.W #18,D0 BCS not taken, the TRAP #15 at 478a6 is a stop boundary (never executed)'%idx)
    tbl(0x18,'trap-478a6-undeclared',group='table-guard',expect_guard=dict(problem='unsupported_code_target',target=TRAP_STOP),end_alts=(),note='index 18 without the declared 478a6 stop: the refused fetch of the TRAP')
    # ---- the music compare 47842 .. 47890 on a RAM record (direct entry 47842)
    def mus(label,rec_mus,cur,**kw):
        typed('music-%s'%label,'music',rtb(0,0,cur,entry=0x47842),writes=ram_record(0x00,rec_mus),entry=0x47842,rules=C62,**kw)
    mus('equal',0x19d2,0x19d2,note='record music = current music: BEQ.W 47890, no sound, no 4814e')
    mus('different-19c1-record',0x19c1,0x0001,note='record music 19c1: 47872 CMPI.W #19c1 equal -> 4787a D0.W := 38 -> 3d58 (pushes the code, sound 0a, then 58) -> 4814e')
    mus('different-other',0x19d2,0x0001,note='record music <> current, <> 19c1: 47882 D0.W := 80 -> 3d58 -> 4814e')
    mus('different-19c0',0x19c0,0x19c1,note='record music 19c0')
    # ---- the sound ring at 3ac8 inside 3d58 / 3d6a / 3d78
    snd=lambda g,a,extra:rtb(g,a,rec_music(g,a,'diff'),extra=extra)
    typed('sound-wait-first-call','sound',snd(1,0,[W(0x104d74,2,1,'declared sound ring tail WORD 104d74 := 1'),W(0x104d76,2,0,'declared sound ring head WORD 104d76 := 0')]),rules=C62,
        note='ring full at the first 3ac8 call (3d6a BSR): Waiting at 3aea, the declared release (tail := ffff) lets it continue')
    typed('sound-wait-second-call','sound',snd(1,0,[W(0x104d74,2,2,'declared sound ring tail WORD 104d74 := 2'),W(0x104d76,2,0,'declared sound ring head WORD 104d76 := 0')]),rules=C62,
        note='the first 3ac8 (code 0a) passes, the tail call BRA 3ac8 at 3d78 finds the ring full: Waiting at 3aea inside the tail call')
    typed('sound-wait-19c1-record','sound',snd(1,5,[W(0x104d74,2,1,'declared sound ring tail WORD 104d74 := 1'),W(0x104d76,2,0,'declared sound ring head WORD 104d76 := 0')]),rules=C62,note='ring full on the record with music 19c1 (code 38 -> 58)')
    for code in (0x00,0x38,0x80,0xdf,0xe0,0xff):
        typed('push-pop-3d58-code-%02x'%code,'sound',rtb(0,0,0x1234,entry=0x3d58),writes=[W(S-2,2,0xa55a,'declared stack sentinel WORD at A7-2 (A7+1 bytes are the A7-1 neighbours): a5 5a'),W(S+4,2,0xc3d2,'declared stack sentinel WORD above the return LONG (A7+4)')],
            regs=dict(d0=0x12340000|code,d1=0x00ab0000),entry=0x3d58,reenter=False,note='BYTE push / pop of 3d58 / 3d6e on code %02x: A7-2 gets the BYTE only (A7-1 keeps its value), ADDI.B #20 / SCS / OR.W decide the sound WORD'%code)
    # ---- the dispatcher callbacks as direct entries
    typed('cb478de-gate-entry','callback',rtb(1,0,rec_music(1,0,'same')),writes=[W(A6V,4,0x478de,'declared RAM: callback LONG (A6) := 478de')],entry=0x478de,rules=C62,frames=3,note='callback 478de entered directly')
    for v in (1,2,0):
        typed('cb4790a-7a%d'%v,'callback',rtb(0,0,0x1234,entry=0x4790a),writes=[W(A6V,4,0x4790a,'declared RAM: callback LONG (A6) := 4790a'),W(A6V+0x7a,2,v,'declared RAM: WORD 7a(A6) := %04x'%v)],entry=0x4790a,frames=3,note='callback 4790a entered directly, countdown 7a = %d (1 -> 0 no borrow, 2 -> 1, 0 -> ffff borrow -> ca8a -> 479b0)'%v)
    for v in (0,1,0xff):
        typed('cb4798e-62-%02x'%v,'callback',rtb(0,0,0x1234,entry=0x4798e),writes=[W(A6V,4,0x4798e,'declared RAM: callback LONG (A6) := 4798e'),W(A6V+0x62,1,v,'declared RAM: BYTE 62(A6) := %02x'%v)],entry=0x4798e,rules=lambda:[],frames=3,note='callback 4798e entered directly, child completion BYTE 62 = %02x (0 waits, <> 0 -> 47996 .. 479a6 callback 479b0)'%v)
    # ---- guards
    typed('guard-odd-a7-477ee','guard',rtb(1,0,rec_music(1,0,'same')),entry=0x477ee,a7=S+1,stack_ret=False,expect_guard=dict(problem='unsupported_odd_data_access'),note='A7 odd at the entry: the first BSR (47800 -> 474e2) pushes an odd LONG')
    typed('guard-odd-a6-477ee','guard',rtb(1,0,rec_music(1,0,'same')),entry=0x477ee,regs=dict(a6=A6V+1),free_a6=True,expect_guard=dict(problem='unsupported_odd_data_access'),note='A6 odd: the BYTE accesses at 477ee pass, the LONG write 76(A6) at 47820 is odd')
    typed('guard-odd-record-47842','guard',rtb(0,0,0x1234,entry=0x47842),writes=ram_record(0x00,0x19d2,SCRATCH_REC+1),entry=0x47842,expect_guard=dict(problem='unsupported_odd_data_access'),note='odd record pointer: WORD 10(A0) is an odd read')
    typed('guard-odd-record-47896-byte-ok','guard',rtb(0,0,0x1234,entry=0x47896),writes=ram_record(0x00,0x19d2,SCRATCH_REC+1),entry=0x47896,rules=C62,note='odd record pointer at 47896: only BYTE (A0) is read; the BYTE access at an odd address is allowed (index 00 path)')
    typed('guard-undeclared-cut-479b0','guard',rtb(1,0,rec_music(1,0,'same')),rules=C62,end_alts=(),expect_guard=dict(problem='unsupported_code_target',target=CUT_STOP),note='the F1c2 entry 479b0 reached without the declared stop is a refused fetch (the cut is never routed)')
    # ---- zero-step at every block start (the stop PC equals the entry PC: nothing executes, the state is unchanged)
    for pc in sorted(STARTS):
        typed('zero-step-%x'%pc,'zero-step',rtb(1,0,rec_music(1,0,'same'),entry=pc),entry=pc,steps=(lambda program,fx,pc=pc:[step_of('zero-step-%x'%pc,[],pc,('abs',S),'boundary')]),
            note='zero-step at the block start %x: stop PC = entry PC, nothing executes (no register / RAM change)'%pc)


# ----------------------------------------------------------------------------------
# Claims of the contract checked against the native results
# ----------------------------------------------------------------------------------
EXPECT_F236=['477ee','477fa','474e2','474ec','47804','47540','47544','47550','47556','47812','47820','4782a','47830','47836','4783c','47842','47872','47882','47886','3d58','3d6a','3d6e','4788c','4814e','47890','47896','478a8','478ac','478c4','478d4']
EXPECT_F237=['478de','478e4','478e6','ca8a','478ec']
CONTRACT_RUNTIME_UNVISITED=['474ea','4754a','4781a','478b4','478bc','4791c','47922','4794c','4795c','47960']      # contract "시작 상태 2": the 12 unvisited blocks, F1c1 half


def contract_claims(rows,static,start_cov):
    claims=[]
    def claim(text,ok,evidence,verdict=None):
        claims.append(dict(claim=text,verdict=verdict or ('confirmed' if ok else 'contradicted'),evidence=evidence))
    by={r['result']['label']:r for r in rows}
    nat=[r for r in rows if r['result']['group']=='natural'];rt=[r for r in rows if r['result']['group']=='runtime'];tr=[r for r in rows if r['result']['group']=='transition']
    P=G['program']
    # ---- static
    claim('7 code ranges, 564 bytes (SHA256 40c8dfbe...), 0 undecoded instructions, equal to the ROM bytes of the contract table; the only TRAP #15 in the contract ranges is 478a6',
        static['trap_instructions_in_contract_range']==['0x478a6'] and static['instructions_decoded']>0,dict(table=static['bytes'],instructions_routed=static['instructions_decoded'],traps=static['trap_instructions_in_contract_range']))
    claim('67 block starts = decoded leaders + 6 table slots 478ac..478c0 + 4 callback entries (477e4 478de 4790a 4798e); 282 even PCs, 214 interior PCs (without the TRAP 478a6); the 9 bundled conditional-branch PCs are conditional branches and not block starts',
        static['even_pcs']==282 and static['interior_pcs']==214 and all(b['is_conditional_branch'] and not b['is_block_start'] for b in static['bundled_branches']) and static['block_starts']==67,dict(bundled=static['bundled_branches'],even=static['even_pcs'],interior=static['interior_pcs']))
    claim('the 32 carry-preserving (flow-only) blocks are exactly the blocks whose instructions are all LEA/MOVEA/JSR/JMP/BSR/BRA/RTS/BTST/BSET/BCLR/Bcc; the 4 carry consumers (blocks whose first Bcc has no flag producer before it) are 478e4 47944 4795c 47974',
        static['flow_only_equal_contract'] and static['carry_consumers_equal'],dict(decoded_minus_contract=static['flow_only_decoded_minus_contract'],contract_minus_decoded=static['flow_only_contract_minus_decoded'],consumers=static['carry_consumers_computed']))
    regs=aggregate_regions(rows)
    claim('F1c1 code has no PVC / video / watchdog / external access and reads only RAM and fixed ROM (no banked-window read): only the callees touch ports (all conditions)',
        set(regs)<= {'ram/read','ram/write','fixed/read'},dict(f1c1_event_regions=regs))
    rr={}
    for r in rows:
        for pc,v in r['facts'].get('f1c1_rom_reads',{}).items():
            q=rr.setdefault(pc,dict(size=v['size'],low=v['low'],high=v['high'],reads=0,windows={},outside_contract=0,outside_max=0))
            q['low']=min(q['low'],v['low']);q['high']=max(q['high'],v['high']);q['reads']+=v['reads'];q['outside_contract']+=v['outside_contract'];q['outside_max']=max(q['outside_max'],v['outside_max'])
            for k,n in v['windows'].items():q['windows'][k]=q['windows'].get(k,0)+n
    ext=G['extents']
    claim('F1c1 reads ROM data only through the physical fixed window, only at the contract places: the group pointer table 474f4..47540 (PC-relative LONG at 474ee; digest f404ca58...), and inside the 19 catalog group extents (ROM group list + records) at 47544 (size WORDs), 47804 (flags BYTE), 47864 (record +10 WORD) and 4789c (record +0 BYTE); never the banked window',
        sha(P[0x474f4:0x47540])=='f404ca58a5bb5d1a3a19b7bd571847076bf72225c2d97a6d6f794124d9765b94' and all('-1' not in v['windows'] for v in rr.values()) and set(rr)<={'474ee','47544','47804','47864','4789c'} and set(rr.get('474ee',{}).get('windows',{}))<={'0'},
        dict(rom_reads_by_pc={pc:dict(low='%x'%v['low'],high='%x'%v['high'],reads=v['reads'],size=v['size']) for pc,v in sorted(rr.items())},group_extents=['%x..%x'%w for w in ext]))
    outside={pc:dict(reads=v['outside_contract'],max_address='%x'%v['outside_max']) for pc,v in rr.items() if v['outside_contract']}
    claim('the contract data windows "group 0~4: d99e2..dd4be, group 5~18: 472be..474e0" cover every F1c1 data read (the actual extent of group 4 is %x..%x: its last record dd4ae..dd4ce is read at +10 by 47864 up to dd4bf)'%tuple(ext[4]),not outside,dict(reads_outside_contract_windows=outside,contract_windows=['%x..%x'%w for w in CONTRACT_WINDOWS],group_extents=['%x..%x'%w for w in ext]))
    # ---- natural seeds
    sig=collections.Counter()
    for r in nat:
        sig[json.dumps([(e['frame'],[x for x in e['leaders']],e['stop'],e['callback_after'],e['out_pc']) for e in r['facts']['f1c1_frames']])]+=1
    ok=len(sig)==1
    claim('137 natural seeds (begin outputs): every seed runs 238 frames, frames 0..236 stop at 2ac2 (RTS at 480f0), frame 237 at the cut 479b0 (BRA.W 478ec, bytes 600000c2); no Waiting, no guard',
        len(nat)==137 and all(r['result']['frames']==238 and r['result']['final_pc']=='479b0' and r['facts']['final_evidence'] and r['facts']['final_evidence']['kind']=='branch-boundary' and r['facts']['final_evidence']['previous_pc']==0x478ec and r['facts']['final_evidence']['previous_bytes']=='600000c2'
            and not r['result']['guarded'] and r['facts']['stops']=={'return':237,'branch-boundary':1} for r in nat),dict(seeds=len(nat),frames=sum(r['result']['frames'] for r in nat)))
    only=[r for r in nat if [h['step'] for h in r['result']['host_writes']]==[189] and [c[1:] for h in r['result']['host_writes'] for c in h['changes']]==[['10dd44',1,'ff']]]
    claim('the only declared host write of a natural seed is BYTE 10dd44 := ff after frame 188 (the F1b contract); no 62(A6) write (the 4798e callback is never installed on the natural path)',len(only)==len(nat),dict(seeds_with_exactly_that_write=len(only)))
    first=json.loads(next(iter(sig))) if sig else []
    claim('all natural seeds take ONE F1c1 path: frame 236 = 477ee 477fa 474e2 474ec 47804 47540 47544 47550 47556 47812 47820 4782a 47830 47836 4783c 47842 47872 47882 47886 3d58 3d6a 3d6e 4788c 4814e 47890 47896 478a8 478ac 478c4 478d4 (stop 2ac2, callback 478de), frame 237 = 478de 478e4 478e6 ca8a 478ec (stop 479b0)',
        ok and len(first)==2 and [x for x in first[0][1] if int(x,16) in START_SET]==EXPECT_F236 and [x for x in first[1][1] if int(x,16) in START_SET]==EXPECT_F237 and first[0][0]==236 and first[1][0]==237 and first[0][3]=='478de',dict(distinct_paths=len(sig),first=first))
    ex_ok=all(r['facts']['exit']['d680']==1 and r['facts']['exit']['d681']==0 and r['facts']['exit']['d684']==0 and r['facts']['exit']['r76']==0xdcd18 and r['facts']['record']==dict(addr=0xdcd18,index=0,music=0x19c0) and r['facts']['exit']['c7c']==1 and r['facts']['exit']['c7d']==0 for r in nat)
    claim('natural seeds: stage 10d680 = 1, area 10d681 = 0 at the F1c1 entry (group 1, record dcd18: entry-effect index 00, music 19c0), group flags 10d684 = 00; the music differs from 10d686 (= 0): 3d58 runs with D0 = 80 (47882), 4814e sets WORD 10d68c := 1',
        ex_ok,dict(r76=sorted({hex(r['facts']['exit']['r76']) for r in nat}),d686=sorted({hex(r['facts']['exit']['d686']) for r in nat}),d68c=sorted({hex(r['facts']['exit']['d68c']) for r in nat})))
    allhit=set()
    for r in rows:
        if not r['result']['guarded']:allhit.update(r['hits'])
    claim('the natural seeds execute %d of the 67 block starts; the rest are reached by the runtime fixtures, the transition seeds and the typed fixtures'%sum(1 for k,v in start_cov.items() if v['in_natural_seeds']),True,dict(natural=[k for k,v in start_cov.items() if v['in_natural_seeds']],not_natural=[k for k,v in start_cov.items() if not v['in_natural_seeds']]))
    staged=[r for r in nat if r['result'].get('prefix')]
    claim('natural seed treatment: the %d DUMP_SEEDS get the full treatment over all 238 frames (split / continuous each twice, fresh-CPU frames, model, full dumps); the other %d seeds record the F1b prefix (frames 0..235, no F1c1 code) with one continuous run reproduced by a second run (core digests of all frames equal, every frame stops at 2ac2 by the RTS at 480f0) and run the F1c1 frames 236, 237 with the full treatment from the captured frame-235 state, whose full-state SHA equals the chain'%(len(nat)-len(staged),len(staged)),
        len(nat)-len(staged)==len(DUMP_SEEDS) and all(r['result']['prefix']['reproduced_twice'] and r['result']['prefix']['all_stop_at_2ac2_by_rts_480f0'] and r['result']['prefix']['frames']==236 for r in staged),dict(dump_seeds=list(DUMP_SEEDS),staged=len(staged)))
    # ---- release guard rows
    rel=[r for r in rows if r['result']['group']=='release-guard']
    claim('the 5 release-poisoned-prefix outputs are guard rows (WORD 104d8a = 8001: an odd WORD read at fcd83 in the U1 frame helper (3c60 CMP.W (A1),D0 in frame 0 for 3 outputs; 3bb2 in frame 29 for 2 outputs), an address error on a real 68000; Unicorn does not fault)',
        len(rel)==5 and all(r['result']['guarded'] and r['result']['observed_guard'].get('reason_kind')=='odd_word_access' and r['result']['observed_guard'].get('address')==0xfcd83 and r['result']['observed_guard'].get('size')==2 for r in rel),
        dict(rows=[dict(label=r['result']['label'],frames=r['result']['frames'],pc=r['result']['observed_guard'].get('pc'),address=r['result']['observed_guard'].get('address'),size=r['result']['observed_guard'].get('size'),access=r['result']['observed_guard'].get('access')) for r in rel]))
    pcs_rel=sorted({r['result']['observed_guard'].get('pc') for r in rel})
    if any(p!=0x3c60 for p in pcs_rel):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-text-differs',claim='contract decision 12: the 5 release outputs read the odd WORD at U1 3c60',evidence=dict(guard_pcs={r['result']['label']:'%x'%r['result']['observed_guard'].get('pc') for r in rel},remark='3 outputs (136 137 138) fault at 3c60 in frame 0; 2 outputs (139 140, the wholebody-sound-wait cases) fault at 3bb2 in frame 29 (another U1 CMP.W reading fcd83); the address, size and the guard-row conclusion are unchanged')))
    # ---- runtime fixtures
    cnt=collections.Counter();fr=collections.defaultdict(collections.Counter);runtime_cov=set()
    for r in rt:
        rec=r['facts']['record']
        # the record index is the one read at 47896; its frame count is the number of steps
        cnt[rec['index']]+=1;fr[rec['index']][r['result']['frames']]+=1
    claim('236 runtime fixtures (59 catalog records x music same / different x entry 477ee / 477e4): every one reaches the cut 479b0 (stop directly after BRA.W 478ec / 47918 or the declared zero-step re-entry at the callback 479b0); no Waiting, no guard, no ROM write',
        len(rt)==236 and all(not r['result']['guarded'] and r['result']['final_pc']=='479b0' and not any(w for w in [r['facts']['wait_rows']]) for r in rt),dict(count=len(rt),stop_kinds=dict(collections.Counter(r['result']['final_stop_kind'] for r in rt))))
    claim('record entry-effect indices of the ROM catalog: 00 x4, 04 x10, 0c x42, 14 x3 records (x4 fixtures each); 08 and 10 do not occur in the ROM catalog',
        dict(cnt)=={0:16,4:40,12:168,20:12},dict(index_counts={hex(k):v for k,v in cnt.items()}))
    claim('frames per fixture (steps to the cut): index 00 = 2, index 0c / 14 = 3 (callback 4798e, then the zero-step re-entry at 479b0), index 04 = 17 (47904 falls through into 4790a in frame 0: SUBQ.W #1,7a(A6) from 10 down to ffff = 17 executions of 4790a, 16 of them returning to 480bc)',
        fr[0]=={2:16} and fr[12]=={3:168} and fr[20]=={3:12} and set(fr[4])=={17},dict(frames={hex(k):dict(v) for k,v in fr.items()}),
        verdict=None)
    for r in rt:
        for pc,v in r['hits'].items():runtime_cov.add(pc)
    unv=sorted('%x'%pc for pc in STARTS if pc not in runtime_cov)
    claim('the F1c1 blocks the runtime fixtures do not visit are exactly the contract list 474ea 4754a 4781a 478b4 478bc 4791c 47922 4794c 4795c 47960 (plus the contract-visited blocks stay visited)',sorted(unv)==sorted(CONTRACT_RUNTIME_UNVISITED),dict(unvisited_by_runtime=unv,contract=CONTRACT_RUNTIME_UNVISITED))
    # ---- transition seeds
    for t in tr:
        pass
    ts=[r for r in tr if r['result']['label'].endswith('to-47934')]
    claim('transition cases 66..69 (A6 = 102000, fill RAM, stage 21 / area 0 and 7f): 477ee -> stop 47934 (stop directly after BRA.W 478b8, bytes 6000007a, index 0c through the table slot 478b8), passing 474ea, 4754a / 4781a (area 7f), 3d58, 4814e, ca9e, 478a8',
        len(ts)==4 and all(r['result']['final_pc']=='47934' and r['facts']['final_evidence'] and r['facts']['final_evidence']['previous_pc']==0x478b8 and r['facts']['final_evidence']['previous_bytes']=='6000007a' for r in ts),
        dict(rows=[dict(label=r['result']['label'],frames=r['result']['frames'],leaders=r['facts']['f1c1_frames']) for r in ts]))
    past=[r for r in rows if r['result']['group']=='transition-guard']
    claim('transition cases 66..69 run past 47934 (28ae follows the garbage object pool): negative case, native guard (the machine contract needs a checked error and full rollback)',
        len(past)==4 and all(r['result']['guarded'] for r in past),dict(rows=[dict(label=r['result']['label'],guard=r['result']['observed_guard']) for r in past]))
    # ---- typed
    def tf(label):return by.get(label)
    for label,text in (('stage-13-474ea','stage 13 (>= 13): 474ea selects group 0'),('stage-21-474ea','stage 21: 474ea'),('stage-ff-474ea','stage ff: 474ea')):
        r=tf(label)
        if r:
            ls=[x for e in r['facts']['f1c1_frames'] for x in e['leaders']]
            claim(text+' (CMPI.W #13 BCS fails, MOVEQ #0,D0)',r['result']['final_pc']=='479b0' and '474ea' in ls and r['facts']['record']['addr']==G['groups'][0][0],dict(frames=r['result']['frames'],record=hex(r['facts']['record']['addr'])))
    for label in ('area-7f-retry','area-0b-retry','area-ff-stage1-retry'):
        r=tf(label)
        if r:
            ls=[x for e in r['facts']['f1c1_frames'] for x in e['leaders']]
            g=1 if 'stage1' in label else 0
            claim(label+': the walk returns null (4754a MOVEA.W #0,A0), 4781a CLR.B 7d(A6) retries with area 0 (record = first record of the group)',r['result']['final_pc']=='479b0' and '4754a' in ls and '4781a' in ls and r['facts']['record']['addr']==G['groups'][g][0],dict(record=hex(r['facts']['record']['addr']),leaders=sorted(set(ls))[:60]))
    for stage in (9,10,15):
        r=tf('empty-group-%02x-loop'%stage)
        if r:claim('empty group (stage %02x): 4781a CLR.B 7d(A6) / BRA 477fa never terminates (decision 7): native guard step_limit (the machine: block-budget rollback)'%stage,r['result']['guarded'] and r['result']['observed_guard']['problem']=='step_limit',dict(guard=r['result']['observed_guard']))
    # gate
    for byte in (0x80,0xff,0xc3):
        r=tf('gate-wait-107ded-%02x-idem2-irq'%byte)
        if r:
            w=r['facts']['wait_rows']
            claim('gate 478de with BYTE 107ded = %02x: Waiting at 478de (after BCC.B 478e4 taken), two no-effect resumes return the same Waiting (identical full state), the declared IRQ effect (clear bit7) lets the frame finish: 479b0 (stop kinds %s)'%(byte,dict(r['facts']['stops'])),
                len(w)==3 and all(x['pc']==GATE_PC for x in w) and len({x['state'] for x in w})==1 and r['result']['final_pc']=='479b0',dict(waits=w))
    r=tf('gate-wait-107ded-81-107dea-nonzero')
    if r:
        w=r['facts']['wait_rows']
        claim('gate with WORD 107dea <> 0: the declared IRQ effect does not clear bit7, the Waiting persists (chain ends in the wait, state unchanged)',len(w)>=3 and all(x['pc']==GATE_PC for x in w) and len({x['state'] for x in w})==1 and r['result']['final_pc']=='478de',dict(waits=w,final=r['result']['final_pc']))
    for byte in (0x7f,0x00,0x01):
        r=tf('gate-pass-107ded-%02x'%byte)
        if r:claim('gate with BYTE 107ded = %02x passes at the first check (72f0 C = 1): no Waiting'%byte,not r['facts']['wait_rows'] and r['result']['final_pc']=='479b0',dict(stops=r['facts']['stops']))
    r=tf('natural-gate-0')
    if r:
        w=r['facts']['wait_rows']
        claim('natural seed 0 with BYTE 107ded := 80 between frames 236 and 237: Waiting at 478de, one no-effect resume, the declared effect, the cut 479b0',len(w)==2 and all(x['pc']==GATE_PC for x in w) and r['result']['final_pc']=='479b0',dict(waits=w,frames=r['result']['frames']))
    # table
    for idx,leaders_expected in ((0x00,['478ac','478c4']),(0x04,['478b0','478f0','4790a']),(0x08,['478b4','4791c','47922','478fe']),(0x0c,['478b8','47934','47944','47984','4798e','47996','479a6']),(0x10,['478bc','4794c','4795c','47960','47984','4798e']),(0x14,['478c0','47964','47974','47978','47984','4798e'])):
        r=tf('table-%02x-slot%d-%s'%(idx,{0:0,4:1,8:2,12:3,16:4,20:5}[idx],{0:'478c4-gate',4:'478f0-countdown-16',8:'4791c-countdown-60',12:'47934-28ae-ok',16:'4794c-28ae-ok',20:'47964-28ae-ok-47978'}[idx]))
        if r:
            ls=set(x for e in r['facts']['f1c1_frames'] for x in e['leaders'])
            claim('table index %02x on a RAM record: slot %s executes (%s), ends at the cut 479b0'%(idx,hex(0x478ac+idx),' '.join(leaders_expected)),r['result']['final_pc']=='479b0' and set(leaders_expected)<=ls,dict(frames=r['result']['frames'],leaders_seen=sorted(ls)))
    for idx in (0x0c,0x10,0x14):
        r=tf('table-%02x-28ae-fails-bcc-taken-478c4'%idx)
        if r:
            ls=set(x for e in r['facts']['f1c1_frames'] for x in e['leaders'])
            bcc={0x0c:'47944',0x10:'4795c',0x14:'47974'}[idx]
            claim('table index %02x with 28ae failing (WORD 104ca0 = 0): BCC at %s taken -> 478c4 (index 00 path with the gate), 47984 / 4798e not reached'%(idx,bcc),r['result']['final_pc']=='479b0' and bcc in ls and '478c4' in ls and '478de' in ls and '4798e' not in ls,dict(leaders=sorted(ls)))
    ri=[tf('table-%02x-interior-pc'%i) for i in (2,6,10,14,18,22)]
    claim('table indices 02 06 0a 0e 12 16 -> 478ac+index = the BRA.W displacement WORD of a table slot (inside an instruction): refused (unsupported_code_target; the machine contract: unsupported error and rollback)',
        all(r and r['result']['guarded'] and r['result']['observed_guard']['problem']=='unsupported_code_target' and r['result']['observed_guard']['target']==TABLE_BASE+i for r,i in zip(ri,(2,6,10,14,18,22))),dict(rows=[(r['result']['label'],r['result']['observed_guard']) for r in ri if r]))
    ro=[tf('table-%02x-odd-pc'%i) for i in range(1,0x18,2)]
    claim('odd table indices 01..17 -> odd PC (an address error on the original CPU): refused (unsupported_code_target, odd_pc)',all(r and r['result']['guarded'] and r['result']['observed_guard'].get('odd_pc') and r['result']['observed_guard']['target']==TABLE_BASE+i for r,i in zip(ro,range(1,0x18,2))) and len(ro)==12,dict(count=len(ro)))
    rb=[tf('table-%02x-trap-boundary-478a6'%i) for i in (0x18,0x19,0x1a,0x40,0x80,0xff)]
    claim('record index >= 18 (18 19 1a 40 80 ff, also odd): CMPI.W #18,D0 BCS.W not taken, stop at 478a6 directly after the BCS.W at 478a2 (bytes 65000004); the TRAP #15 is never executed',
        all(r and r['result']['final_pc']=='478a6' and r['facts']['final_evidence']['kind']=='fallthrough-boundary' and r['facts']['final_evidence']['previous_pc']==0x478a2 and r['facts']['final_evidence']['previous_bytes']=='65000004' for r in rb),dict(rows=[(r['result']['label'],r['facts']['final_evidence']) for r in rb if r]))
    r=tf('table-18-trap-478a6-undeclared')
    if r:claim('index 18 without the declared 478a6 stop: the refused fetch of the TRAP (never executed)',r['result']['guarded'] and r['result']['observed_guard']['target']==TRAP_STOP,dict(guard=r['result']['observed_guard']))
    # music
    for label,text,leaders in (('music-equal','record music = current music: BEQ.W 47890 (no sound, no 4814e)',['47842','47890']),('music-different-19c1-record','record music 19c1: 4787a (D0.W := 38) -> 3d58 -> 4814e',['47872','4787a','47886','3d58','4788c','4814e']),
            ('music-different-other','record music other: 47882 (D0.W := 80) -> 3d58 -> 4814e',['47872','47882','47886','3d58','4814e']),('music-different-19c0','record music 19c0 (<> 19c1): 47882',['47882','3d58'])):
        r=tf(label)
        if r:
            ls=set(x for e in r['facts']['f1c1_frames'] for x in e['leaders']);ok=set(leaders)<=ls and (label!='music-equal' or ('3d58' not in ls and '4814e' not in ls))
            claim('music compare: '+text,ok and r['result']['final_pc']=='479b0',dict(leaders=sorted(ls),d68c=hex(r['facts']['exit']['d68c'])))
    # sound
    for label,text in (('sound-wait-first-call','ring full at the first 3ac8 call (BSR 3d6a)'),('sound-wait-second-call','ring full at the tail call BRA 3ac8 (3d78)'),('sound-wait-19c1-record','ring full on the 19c1 record')):
        r=tf(label)
        if r:
            w=r['facts']['wait_rows']
            claim('sound ring: %s -> Waiting at 3aea, the declared release (tail := ffff) resumes'%text,len(w)==1 and w[0]['pc']==0x3aea and r['result']['final_pc']=='479b0',dict(waits=w))
    for code in (0x00,0x38,0x80,0xdf,0xe0,0xff):
        r=tf('push-pop-3d58-code-%02x'%code)
        if r:
            sb=r['facts']['stack_bytes_after'];sb0=r['facts']['stack_bytes_before']
            # stack window = [S-8, S+8): index 6 is S-2, 7 is S-1, 8 is S
            claim('3d58 with code %02x: BYTE push at A7-2 only (A7-1 keeps 5a), A7 restored by the pop; the frame returns to 2ac2'%code,sb[12:14]!='' and sb[14:16]=='5a' and r['result']['final_stop_kind']=='return',dict(stack_before=sb0,stack_after=sb))
    # coverage
    allhit=set()
    for r in rows:
        if not r['result']['guarded']:allhit.update(r['hits'])
    claim('every one of the 67 block starts is executed by at least one native condition',all(pc in allhit for pc in STARTS),dict(not_hit=['%x'%x for x in STARTS if x not in allhit],needing_typed=[k for k,v in start_cov.items() if v['needs_typed_fixture']]))
    zs=[r for r in rows if r['result']['group']=='zero-step']
    claim('zero-step at each of the 67 block starts leaves the state unchanged (stop PC = entry PC)',len(zs)==67 and all(r['result']['final_stop_kind']=='zero-step' for r in zs),dict(count=len(zs)))
    claim('the independent model executed every one of the %d routed F1c1 instructions at least once over all conditions'%len(F1C1_INSTR),G.get('model_cov',0)==len(F1C1_INSTR),dict(executed=G.get('model_cov',0),total=len(F1C1_INSTR)))
    tot=dict(conditions=len(rows),frames=sum(r['result']['fresh_frames'] for r in rows),fresh_checked=sum(r['result']['fresh_checked'] for r in rows),fresh_equal=sum(r['result']['fresh_frames_equal'] for r in rows),model_frames=sum(r['result']['model_frames'] for r in rows),model_equal=sum(r['result']['model_frames_equal'] for r in rows))
    claim('every checked frame: the fresh-CPU one-run-one-frame replay equals the chain frame, and the independent model equals the native frame (every frame that executes F1c1 code)',tot['fresh_checked']==tot['fresh_equal'] and tot['model_frames']==tot['model_equal'],tot)
    for c in claims:
        if c['verdict'] in ('contradicted','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    return claims,tot


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def label_of(it):
    k=it['kind']
    if k=='natural':return 'natural-%03d'%it['ref']
    if k=='release':return 'release-guard-%03d'%it['ref']
    if k=='runtime':
        g,ar,mm,entry=it['ref'];return 'rt-g%02d-a%02d-%s-%x'%(g,ar,mm,entry)
    if k=='transition':return 'transition-%d-%s'%it['ref']
    return TYPED[it['ref']].label


def main():
    global OUT,BLOBS,CONDDIR
    t_start=time.time()
    dev=os.environ.get('SC_DEV');workers=int(os.environ.get('SC_WORKERS','3'))
    out_dir=Path(os.environ['SC_OUT']) if os.environ.get('SC_OUT') else OUT
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file() or old.is_symlink():old.unlink()
        else:shutil.rmtree(old)
    OUT=out_dir;BLOBS=out_dir/'blobs';CONDDIR=out_dir/'conditions';BLOBS.mkdir();CONDDIR.mkdir()
    ext=configure(program,out_dir)
    static=static_checks(program)
    G['program']=program;G['seeds']=load_seeds();G['groups']=catalog_groups(program);G['extents']=catalog_extents(program)
    ROM_WINDOWS[:]=[(0x474f4,0x47540)]+G['extents']
    assert [len(g) for g in G['groups']]==[11,6,14,5,9,3,3,3,2,0,0,0,0,0,0,0,1,1,1],[len(g) for g in G['groups']]
    define_typed();G['typed']=TYPED
    ITEMS.clear()
    for s in G['seeds']:ITEMS.append(dict(kind='release' if s['release'] else 'natural',ref=s['index']))
    for g in range(19):
        for ar in range(len(G['groups'][g])):
            for mm in ('same','diff'):
                for entry in (0x477ee,0x477e4):ITEMS.append(dict(kind='runtime',ref=(g,ar,mm,entry)))
    for index in (66,67,68,69):
        ITEMS.append(dict(kind='transition',ref=(index,'stop')));ITEMS.append(dict(kind='transition',ref=(index,'past')))
    for i in range(len(TYPED)):ITEMS.append(dict(kind='typed',ref=i))
    keep=[i for i,it in enumerate(ITEMS) if not dev or any(f in label_of(it) for f in dev.split(','))]
    print('items',len(ITEMS),'selected',len(keep),'workers',workers,flush=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,TRANSITION,sc.STAGE_ENTRY,sc.CONTRACT,fh.CONTRACT,bc.CONTRACT,inp.CONTRACT,sp.CONTRACT}
    input_paths.update(Path(p) for p in sc.SEED_FILES)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin_ref=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin_ref['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    done={}
    if workers>1:
        ctx=multiprocessing.get_context('fork')
        with ctx.Pool(workers) as pool:
            for n,r in enumerate(pool.imap_unordered(run_item,keep,chunksize=1)):
                done[r['number']]=r
                if (n+1)%10==0 or 'error' in r:print('%d/%d %.0fs%s'%(n+1,len(keep),time.time()-t_start,' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    else:
        for n,i in enumerate(keep):
            r=run_item(i);done[i]=r
            print('%d/%d %s %.1fs%s'%(n+1,len(keep),label_of(ITEMS[i]),r.get('seconds',0),' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    errors=[done[i] for i in keep if 'error' in done[i]]
    if errors:
        for e in errors[:10]:print(e['number'],e['kind'],e['ref'],e['error'],'\n',e['trace'][-800:])
        raise SystemExit('%d work items failed'%len(errors))
    rows=[done[i] for i in keep]
    return finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,rows,static,t_start,ext,dev)


def aggregate_regions(rows):
    t=collections.Counter()
    for r in rows:
        for k,v in r['facts'].get('f1c1_regions',{}).items():t[k]+=v
    return dict(t)


LIMITATIONS=['Controlled incoming fixtures (the recorded final RAM of the 137 original stage_entry_body begin runs, the runtime fixtures built by the original 2790 / 3ef2 / 49a1a on a zero RAM, the transition cases 66..69, declared typed variants), not natural scheduler / gameplay reachability; one machine run is one frame and the next frame is a declared direct re-entry (no scheduler, no children, no IRQ).',
    'Native carry / CCR is never read (SR is unobserved); the carry of 72f0 and 28ae is computed by the model from the contract formulas and checked by the executed branch path.  Unknown-carry rejection is a C++ property (a CPU always has a CCR): it is not observable natively; known Clear / Set entries are observed with a declared SR.',
    'Wait stops are taken at the FIRST blocked arrival at cda4 / 3aea (spin loops write nothing) and at the arrival at 478de after the BCC.B at 478e4 was taken with BYTE 107ded bit7 set; the only resume is a declared host effect (sound/sprite release writes, the declared IRQ palette effect).  Frame re-entry and host writes are declared steps.',
    'The 5 release-poisoned-prefix outputs are guard rows: the observer refuses odd WORD/LONG data accesses (guard unsupported_odd_data_access, reason_kind odd_word_access); Unicorn would not fault.',
    'IRQ effects between frames (frame counter, watchdog, palette) are not modelled.  The ordered video / watchdog / PVC port events are instruction accesses, not physical bus cycles.',
    'In-process observer extensions: 3c0006 video port (U5) and a memoized capstone decode of the routed ranges (identical results); no shared tool file is edited.  The F1a observer module is imported for its range constants only.',
    'The model treats every callee outside the 7 F1c1 ranges (F1b blocks ca48 1c5b0 9056, exit, sound, screen, transition, fade_card, readiness, the 480bc frame helper, the F1a blocks 1a5a4 / 72f0) as a replayed black box (native exit registers / RAM / PVC writes); only the F1c1 code and the 72f0 / 28ae carry are modelled independently.  The F1b frame code of the natural chain is not re-modelled (F1b unit).',
    'F1c2 (479b0 and everything behind it, including 49a58) is never executed; the stop at 479b0 is a boundary only.  The 478a6 TRAP is never executed.',
    'Meaning of the entry-effect indices, group flags 10d684, the 476bc table and the sound codes remains unknown (contract unknown items).']


def finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,rows,static,t_start,ext,dev):
    for r in rows:DISCREPANCIES.extend(r.get('discrepancies',[]))
    rows=sorted(rows,key=lambda r:r['number'])
    results=[r['result'] for r in rows]
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    hits=collections.Counter();hit_cond=collections.defaultdict(set);first={};groups=collections.defaultdict(collections.Counter);coverage=set()
    for r in rows:
        if r['result']['guarded']:continue
        coverage.update(r['covered'])
        for pc,n in r['hits'].items():
            hits[pc]+=n;hit_cond[pc].add(r['number']);groups[pc][r['result']['group']]+=1;first.setdefault(pc,r['result']['label'])
    base_groups=('natural','runtime','transition')
    start_cov={hex(pc):dict(hits=hits.get(pc,0),conditions=len(hit_cond.get(pc,())),groups=dict(groups.get(pc,{})),first_condition=first.get(pc),in_natural_seeds=groups[pc].get('natural',0)>0,
        in_runtime_fixtures=groups[pc].get('runtime',0)>0,in_transition_seeds=groups[pc].get('transition',0)>0,needs_typed_fixture=not any(groups[pc].get(g,0) for g in base_groups)) for pc in sorted(STARTS)}
    unc=[hex(pc) for pc in STARTS if not hits.get(pc)]
    mexec=set()
    for r in rows:mexec.update(r.get('model_exec',()))
    G['model_cov']=len(mexec)
    model_instr=dict(executed_by_model=len(mexec),instructions_in_routed_ranges=len(F1C1_INSTR),not_executed_by_model=sorted(hex(pc) for pc in F1C1_INSTR if pc not in mexec))
    claims,tot=[],{}
    if not dev or os.environ.get('SC_CLAIMS'):
        try:claims,tot=contract_claims(rows,static,start_cov)
        except Exception:
            import traceback
            DISCREPANCIES.append(dict(label='claims',kind='claims-code-error',detail=traceback.format_exc()[-2500:]))
    by_group=collections.Counter(r['group'] for r in results)
    artifacts={}
    for f in sorted(CONDDIR.iterdir()):artifacts['conditions/'+f.name]=sha(f.read_bytes())
    blob_count=sum(1 for _ in BLOBS.iterdir())
    report=dict(schema_version=1,source=source,inputs=inputs,contract=dict(path=str(CONTRACT),sha256=contract_sha,byte_table_check=TABLE),static_checks=static,
        frame_state_sha256_definition='sha256(b"F1C1-FRAME-STATE-v1" || RAM-after(65536) || D0..D7,A0..A7 as 16 big-endian LONGs || PC (LONG) || bank number (LONG) || count of ordered port events (LONG) || ordered port events (BYTE size, LONG address, LONG value each))',
        conditions=len(results),groups=dict(by_group),results=results,condition_files=artifacts,blob_count=blob_count,
        totals=dict(frames=sum(r['fresh_frames'] for r in results),split_phases=sum(r['split_phases'] for r in results),control_phases=sum(r['control_phases'] for r in results),fresh_CPU_chain_runs=sum(r['runs'] for r in rows),
            instructions=sum(r['instructions'] for r in results),dumped_frames=sum(r['dumped_frames'] for r in results),fresh_checked=sum(r['fresh_checked'] for r in results),fresh_frames_equal=sum(r['fresh_frames_equal'] for r in results),
            f1c1_frames=sum(r['f1c1_frames'] for r in results),model_frames=sum(r['model_frames'] for r in results),model_frames_equal=sum(r['model_frames_equal'] for r in results),model_frames_not_applicable=sum(r['model_frames_not_applicable'] for r in results)),
        block_start_coverage=start_cov,block_starts_not_hit=unc,block_starts_needing_typed_fixtures=[k for k,v in start_cov.items() if v['needs_typed_fixture']],covered_PCs=sorted(coverage),block_starts=sorted(STARTS),model_instruction_coverage=model_instr,
        contract_claims=claims,contract_discrepancies=DISCREPANCIES,natural_seed_policy=dict(natural=137,release_guard_rows=5,note='contract decision 12: the 5 release-poisoned-prefix outputs are guard rows; the F1c contract text counts 142 seeds in its scratch replay (superseded: 137 natural + 5 guard rows)'),
        dump_seeds=list(DUMP_SEEDS),boundary_frames=list(BOUNDARY_FRAMES),rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,observer_extension=ext,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),limitations=LIMITATIONS,failure=None)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    summary=dict(conditions=len(results),groups=dict(by_group),totals=report['totals'],discrepancies=len(DISCREPANCIES),not_hit=unc,claims={v:sum(1 for c in claims if c['verdict']==v) for v in ('confirmed','contradicted','not-reproduced')} if claims else None,
        sha256=sha(path.read_bytes()),tool=tool_sha,seconds=round(time.time()-t_start))
    print(json.dumps(summary))
    return summary


if __name__=='__main__':main()
