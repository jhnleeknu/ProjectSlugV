"""Unpatched stage event interpreter F3a (e9150 / e9176 core, opcodes 00..07, expression evaluator e97c8 with the e97e4 table, helpers 48502 / 1a910 / 1a93e) native observation.

Native Unicorn M68000 observation of the original ROM (write-protected, never modified).  It reuses, by import and without editing them, the machinery of the buffer/cue
observer U7 (observe_animation_machine_buffer_cue and through it the script/placement observer U5, scene update U4, motion walk U3, scene core U2, frame helper U1, the U6 input
observer ranges and the card-menu / fade-card chain): persistent-CPU Observer with the declared host-change vocabulary RAM write / PC redirect / A7 delta, fresh-twice reproduction,
split (stop at the first hit of every block leader) versus continuous equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every imported tool
module and the ROM SHA/mtime guard.  The scheduler observer (observe_animation_machine_scheduler) is imported to regenerate the natural F3 node entry states in this process
exactly as it recorded them (its SeedRun with the f3_replay hook replaced by this tool; nothing in the imported modules or tools is edited).  The declared observer extension of
U5 (a WORD write to 3c0006 is a 'video' port event) is installed in this process exactly as U5/U7 do.

Unit: the 1,124 contract bytes of docs/analysis/animation-machine-stage-event-f3-contract.md, F3a half (7 code ranges 1a910..1a91a 1a93e..1a952 48502..4855c e9150..e9350
e9444..e94fe e9768..e9774 e97c8..e98ee, 324 instructions, 134 block starts).  The F3b boundary e94fe (BSR e94fe at e91ac) and the five branch targets of the bundled evaluator
return (e9428 e939a e93a2 e96b4 e96b8) are STOPS only: they are never executed.  Main decisions of the contract implemented here as observation rules:
  * decision 10: one machine run = ONE node execution.  PC = 2ab8, A6 = node (100bf4), A7 = SPd (1ff000), LONG 104ca4 = SPd (the dispatcher base); the run ends at 2ac2 (the RTS that
    pops the return LONG pushed by the dispatcher JSR (A0) at 2ac0) or at e94fe (directly after the BSR at e91ac), whichever comes first.  Typed direct entries (PC = a block start,
    a declared return LONG 2ac2 at A7) are a second form; their stop is the RTS that pops the declared LONG.
  * decision 3 (option A, bundled): the e98ea block pops the BYTE (Z), then the return LONG R; when R is one of the four known callers (e9392 e939a e94bc e96ac) the branch at
    e9396 / e939e / e94c0 / e96b0 is part of the same block.  e94c0 is in F3a (BNE.W e9768 / fall-through e94c4); e9396 / e939e / e96b0 are F3b callers: the observer routes those
    three BEQ.W instructions as bundled branches and stops at their targets (e9428 e939a e93a2 e96b4 e96b8).  Any other R is simply the new PC.
  * decision 2: the unbounded table JMP e97e4(PC,D1.W) at e97e0 is checked BEFORE the jump: a target that is a F3a block start executes natively, any other target is refused
    (guard unsupported_code_target, refused_before_jump).
  * decision 5: the evaluator stack is BYTE pushes/pops with A7 -/+ 2 (68000 byte on A7); written natively and compared with the independent model.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step
record; a declared initial SR (default 2000, CCR 0) and the declared initial registers are part of the fixture summary.  Nothing claims BIOS execution, a natural IRQ or a natural
scheduler: the natural node entry states are the states of the DECLARED frame pass model of the scheduler observer (docs/analysis/animation-machine-scheduler-shell-f2-contract.md).

Seeds (all pinned by SHA256):
  natural   artifacts/animation_machine_scheduler_native: observation.json (pinned) and f3_node_seeds.json.gz (recorded entry/exit state digests of every F3 node execution).  The
            137 natural stage_entry_body seeds are re-run in this process by the scheduler's own SeedRun (120 / 400 declared frame passes); every e9150 / e9176 node execution is run
            here from its entry state (PC 2ab8) and its entry digest must equal the recorded one; the exit digest (2ac2) or the e94fe digest must equal the recorded one too.
  typed     declared fixtures on recorded dump states of the same seed file (blobs pinned by SHA256): event streams in scratch RAM at 10f400.. (pointer 76(A6)), expression bytes
            of every evaluator operator and every operand class, node variable settings, list-walk chains, player flags, direct entries at block starts, planted return LONGs.
An independent Python model of the contract (a M68000 subset interpreter written from the 68000 programmer's reference that decodes the ORIGINAL ROM BYTES of the 7 F3a ranges
instruction by instruction with a complete CCR model, 32-bit register semantics and explicit byte/word/long operations; it shares no code with Unicorn, the disassembler or the
C++) is compared with each native F3a segment: block-leader sequence with the full register file at every leader, ordered RAM writes / reads, ordered fixed/bank ROM reads and
ports of the F3a code, the final registers, PC and the whole 64KiB RAM image.  Every callee outside the F3a ranges (43e34, 49392, 4d7a6, the dispatcher shell) is a black box
whose native exit registers and RAM / port writes are replayed; a carry produced by a black box is taken from the executed path (branch evidence).  Any difference is recorded in
contract_discrepancies.
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
import observe_animation_machine_scheduler as sched
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
sp=bc.sp;inp=bc.inp;fh=bc.fh;fc=bc.fc;mt=bc.mt;op=bc.op;sc=bc.sc;seb=bc.seb;vsf=bc.vsf;shared=bc.shared;activation=bc.activation
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_stage_event_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-stage-event-f3-contract.md'
CONTRACT_SHA='bba912176899ab0c21a0b9d54800c5f987f8fdcad9c592b714b8a713d5376c95'
SEED_DIR=ROOT/'artifacts/animation_machine_scheduler_native'
SEED_OBS=SEED_DIR/'observation.json'
SEED_OBS_SHA='c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff'
SEED_FILE=SEED_DIR/'f3_node_seeds.json.gz'
SCOPE=sc.SCOPE
ROM_SHA=op.ROM_SHA
sha=fc.sha
u8,u16,u32=op.u8,op.u16,sc.u32
M32=0xffffffff
S=fc.S                                                      # 1feffc
SPD=0x1ff000                                                # declared dispatcher level A7 of a node run (F2 decision 4)
BASE_LONG=0x104ca4
A5V=0x108000
NODE=0x100bf4                                               # the stage event node (A6 of every F3a node execution)
KEYS=shared.isolated.REG_NAMES                              # d0..d7 a0..a6
KEYS14=sc.KEYS14
REG16=tuple('d%d'%i for i in range(8))+tuple('a%d'%i for i in range(8))
PORT_REGIONS=fc.PORT_REGIONS
NODE_PC=0x2ab8
FRAME_RET=0x2ac2
F3B_ENTRY=0xe94fe
EVAL_JMP=0xe97e0                                            # JMP e97e4(PC,D1.W)
EVAL_TABLE=0xe97e4
EVAL_ENTRY=0xe97c8
MAIN_JSR=0xe91ba                                            # JSR e91e4(PC,D7.W)
MAIN_TABLE=0xe91e4
BUNDLED_BRANCH=((0xe9396,0xe9428,0xe939a),(0xe939e,0xe9428,0xe93a2),(0xe96b0,0xe96b8,0xe96b4))      # (BEQ.W PC, target when Z, fall-through) of the F3b callers
F3B_STOP_PCS=(0xe94fe,0xe9428,0xe939a,0xe93a2,0xe96b4,0xe96b8)
F3B_BOUNDARY_PCS=(0xe9350,0xe9362,0xe96cc,0xe96f8,0xe93d8,0xe9528,0xe9530,0xe957a,0xe96d4,0xe9702,0xe9780,0xe9788)      # F3b callback entries and TRAP #15 sites: stops when declared as the step stop, refused (guard) when reached undeclared
STEP_LIMIT=300000                                           # declared per-run instruction watchdog of the observer (the original has none); a fixture may declare a smaller step_limit
DISCREPANCIES=[]
INFO=[]

F3A_RANGES=((0x1a910,0x1a91a),(0x1a93e,0x1a952),(0x48502,0x4855c),(0xe9150,0xe9350),(0xe9444,0xe94fe),(0xe9768,0xe9774),(0xe97c8,0xe98ee))
EXTRA_RANGES=((0x43e34,0x43e38),)                           # the cleanup LEA entry (43e34 LEA 2e(A6),A0 falls into the existing 43e38): a black-box entry, not yet in the cleanup observer ranges
BUNDLED_RANGES=tuple((pc,pc+4) for pc,_,_ in BUNDLED_BRANCH)
STOP_RANGES=tuple((pc,pc+2) for pc in F3B_STOP_PCS)         # pseudo ranges: the stop PCs pass the base observer's routed-PC check and are stopped by this tool (never executed)
TABLE_SLOTS=tuple(MAIN_TABLE+4*k for k in range(8))+tuple(EVAL_TABLE+4*k for k in range(34))
CALLBACK_STARTS=(0xe9150,0xe9176)                           # MOVE.L #imm,(A6) install / node entry
SEED_KINDS=('natural',)


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)
def in_f3a(pc):return in_ranges(pc,F3A_RANGES)
def sext(v,size):
    m=(1<<(8*size))-1;v&=m
    return v-(1<<(8*size)) if v&(1<<(8*size-1)) else v


# ----------------------------------------------------------------------------------
# Contract text: byte table, block starts (134), bundled branch PCs (22), FLOW_ONLY (60), carry consumers (2)
# ----------------------------------------------------------------------------------
def expand_pcs(text):
    """PC tokens of a contract line; `a`..`b`(n slot) expands to the 4-byte table slots."""
    out=[]
    for m in re.finditer(r'`([0-9a-f]{4,6})`(?:\.\.`([0-9a-f]{4,6})`\((\d+)[^)]*\))?',text):
        a=int(m.group(1),16)
        if m.group(2):
            b=int(m.group(2),16);n=int(m.group(3));assert (b-a)//4+1==n,(m.group(0),n);out.extend(range(a,b+1,4))
        else:out.append(a)
    return out


def parse_contract(program):
    lines=CONTRACT.read_text().splitlines()
    rows=[];code=[];sect=None
    pat=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (.*) \|$')
    for line in lines:
        if line=='**F3a**':sect='a';continue
        if line=='**F3b**':sect='b';continue
        if sect!='a':continue
        m=pat.match(line)
        if not m:continue
        lo,hi=int(m.group(1),16),int(m.group(2),16);cell=m.group(3);data=program[lo:hi]
        ticks=re.findall(r'`([0-9a-f]+)`',cell);digest=re.search(r'SHA256 `([0-9a-f]{64})`',cell)
        assert ticks and ticks[-1]==data.hex(),(hex(lo),hex(hi),'byte table row')
        if digest:assert sha(data)==digest.group(1),(hex(lo),hex(hi))
        rows.append(dict(range='%x..%x'%(lo,hi),size=hi-lo,bytes_equal_to_rom=True,sha256=sha(data),summary_digest_in_contract=bool(digest)));code.append((lo,hi))
    assert code==list(F3A_RANGES),[(hex(a),hex(b)) for a,b in code]
    assert sum(h-l for l,h in code)==1124
    starts=bundled=preserve=consumers=None;seen_a=False
    for line in lines:
        if line.startswith('**F3a (134 block 시작)**'):starts=expand_pcs(line.split(':',1)[1]);seen_a=True
        elif line.startswith('**F3b (109 block 시작'):seen_a=False
        elif seen_a and line.startswith('- 묶인 PC 22개:'):bundled=expand_pcs(line.split(':',1)[1])
        elif seen_a and line.startswith('- FLOW_ONLY 60개:'):preserve=expand_pcs(line.split(':',1)[1])
        elif seen_a and line.startswith('- carry 소비 block 2개:'):consumers=expand_pcs(line.split(':',1)[1].split('(')[0])
    assert starts and len(starts)==len(set(starts))==134,len(starts or ())
    assert bundled and len(bundled)==len(set(bundled))==22,len(bundled or ())
    assert preserve and len(preserve)==len(set(preserve))==60,len(preserve or ())
    assert consumers==[0xe9248,0xe9258],consumers
    return rows,starts,bundled,preserve,consumers


STARTS=();BUNDLED=();PRESERVE=();CONSUMERS=();TABLE=[];F3A_INSTR={};BB_ENTRIES=();LEAD_PCS=frozenset();CK_SET=frozenset();START_SET=frozenset();RANGES_ALL=()
EVEN_PCS=();INTERIOR=();DECODED_LEADERS=frozenset()
DECODE_CACHE={}


def install_decode_cache():
    """Declared in-process speed-up (no semantic change): the base Observer.prepare decodes every routed range with capstone for each new CPU; the identical result is memoized."""
    original=fc.disassemble_range
    def cached(program,start,size,base):
        key=(id(program),start,size,base)
        if key not in DECODE_CACHE:DECODE_CACHE[key]=list(original(program,start,size,base))
        return DECODE_CACHE[key]
    fc.disassemble_range=cached


def external_targets(program):
    """Targets of the JSR/JMP/BSR/BRA/Bcc instructions of the F3a ranges that leave the ranges (the black-box entries and the F3b boundary)."""
    out={}
    for lo,hi in F3A_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):
            pc=r['cpu_address'];raw=bytes.fromhex(r['raw']);t,k=fh.branch_target(pc,raw)
            if raw[:2] in (b'\x4e\xf9',b'\x4e\xb9'):t=int.from_bytes(raw[2:6],'big')
            if t is not None and not in_f3a(t):out.setdefault(t,[]).append(pc)
    return out


def configure(program,out_dir):
    global STARTS,BUNDLED,PRESERVE,CONSUMERS,TABLE,F3A_INSTR,BB_ENTRIES,LEAD_PCS,CK_SET,START_SET,RANGES_ALL,EVEN_PCS,INTERIOR,DECODED_LEADERS
    ext=bc.configure(program,out_dir)                                   # installs the U5/U7 observer extension and fills fc/fh globals for the existing executors
    rows,starts,bundled,preserve,consumers=parse_contract(program)
    TABLE=rows;STARTS=tuple(starts);BUNDLED=tuple(bundled);PRESERVE=tuple(preserve);CONSUMERS=tuple(consumers)
    for lo,hi in F3A_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):F3A_INSTR[r['cpu_address']]=r
    assert not any(r['classification']=='undecoded_word' for r in F3A_INSTR.values())
    assert len(F3A_INSTR)==324,len(F3A_INSTR)
    decoded=set(fh.leaders_of(program,F3A_RANGES))
    full=decoded|set(TABLE_SLOTS)|set(CALLBACK_STARTS)
    raw_diff=(sorted(hex(x) for x in full-set(STARTS)),sorted(hex(x) for x in set(STARTS)-full))
    # two documented differences of the generic leader rule (fh.leaders_of): e94c0 follows the BSR e97c8 but is a bundled PC by decision 3 (the evaluator return branch); e91be follows the
    # computed JSR e91e4(PC,D7.W) (opcode 4ebb), a call form the generic rule does not decode, but it is the return address and a block start of the contract.
    full=(full-{0xe94c0})|{0xe91be}
    DECODED_LEADERS=frozenset(full)
    INFO.append(dict(label='static',kind='generic-leader-rule-differences',raw_decoded_minus_contract=raw_diff[0],raw_contract_minus_decoded=raw_diff[1],
        explanation='e94c0: bundled PC by decision 3 (BNE.W after the evaluator return); e91be: return address of JSR e91e4(PC,D7.W) (opcode 4ebb is not decoded by fh.leaders_of)'))
    if full!=set(STARTS):
        DISCREPANCIES.append(dict(label='static',kind='block-start-set',decoded_minus_contract=sorted(hex(x) for x in full-set(STARTS)),contract_minus_decoded=sorted(hex(x) for x in set(STARTS)-full)))
    assert not set(BUNDLED)&set(STARTS)
    ext_t=external_targets(program)
    assert F3B_ENTRY in ext_t and ext_t[F3B_ENTRY]==[0xe91ac],ext_t.get(F3B_ENTRY)
    BB_ENTRIES=tuple(sorted(set(ext_t)-{F3B_ENTRY}))
    EVEN_PCS=tuple(p for lo,hi in F3A_RANGES for p in range(lo,hi,2))
    INTERIOR=tuple(p for p in EVEN_PCS if p not in set(STARTS))
    START_SET=frozenset(STARTS);LEAD_PCS=frozenset(STARTS)|frozenset(BB_ENTRIES);CK_SET=frozenset(LEAD_PCS)
    RANGES_ALL=tuple(dict.fromkeys(tuple(bc.RANGES)+F3A_RANGES+EXTRA_RANGES+BUNDLED_RANGES+STOP_RANGES))
    for lo,hi in F3A_RANGES:
        assert not any(l2<hi and lo<h2 for l2,h2 in bc.RANGES),(hex(lo),hex(hi))
    fc.OUT=out_dir;fc.RANGES=RANGES_ALL;fc.BOUNDARIES=();fc.KEY_PCS=()
    fh.OUT=out_dir;fh.POOL.clear()
    install_observer();install_decode_cache()
    return ext


# ----------------------------------------------------------------------------------
# Observer: U5 observer (3c0006 video port) + declared initial SR, F3b boundary stops, the pre-jump computed-PC check, leader records (F3a block starts and the black-box
# entries reached directly from F3a code)
# ----------------------------------------------------------------------------------
class F3Mixin(object):
    def prepare(self,fx):
        super().prepare(fx)
        c=self.cpu;REGS=fc.REGS
        if fx.get('sr') is not None:c.reg_write(REGS['sr'],fx['sr'])
        self.leads=[];self.mine_seen=set();self.total=0;self.last_pc=None;self.alt_stops=frozenset(fx.get('stop_alts',()));self.step_limit=fx.get('step_limit',STEP_LIMIT);self.computed=[]
        def cb(cpu,pc,size,user):
            if self.guard is not None:
                if pc&1 and self.guard.get('problem')=='unsupported_code_target' and self.guard.get('target')==pc:self.guard['odd_pc']=True
                return
            first_cp=pc in self.checkpoints and pc not in self.mine_seen
            if first_cp:self.mine_seen.add(pc)
            stopping=pc==self.stop_pc or (first_cp and not self.continuous)
            if stopping:return
            if pc in F3B_STOP_PCS or pc in self.alt_stops:                        # declared boundary: a stop only, never executed (accepted by stop_evidence only directly after the transferring instruction)
                self.stop_pc=pc;cpu.emu_stop();return
            if pc==EVAL_JMP:                                                    # JMP e97e4(PC,D1.W): checked BEFORE the jump (decision 2)
                t=(EVAL_TABLE+sext(cpu.reg_read(REGS['d1'])&0xffff,2))&M32
                self.computed.append(dict(pc=pc,index=cpu.reg_read(REGS['d1'])&0xffff,target=t))
                if t&1 or t not in START_SET:
                    self.guard=dict(problem='unsupported_code_target',pc=pc,target=t,odd_pc=bool(t&1),refused_before_jump=True);cpu.emu_stop();return
            elif pc==MAIN_JSR:
                t=(MAIN_TABLE+sext(cpu.reg_read(REGS['d7'])&0xffff,2))&M32
                self.computed.append(dict(pc=pc,index=cpu.reg_read(REGS['d7'])&0xffff,target=t))
                if t&1 or t not in START_SET:
                    self.guard=dict(problem='unsupported_code_target',pc=pc,target=t,odd_pc=bool(t&1),refused_before_jump=True);cpu.emu_stop();return
            if in_f3a(pc) and pc not in START_SET:                                  # a transfer into the middle of a block (or a direct entry at a non-start PC) is refused before it executes
                lp=self.last_pc
                if not ((lp is not None and in_f3a(lp) and pc==lp+F3A_INSTR[lp]['size']) or (pc==0xe94c0 and lp==0xe98ec)):
                    self.guard=dict(problem='unsupported_code_target',pc=lp if lp is not None else pc,target=pc,odd_pc=False,refused_before_execution=True,entry=lp is None);cpu.emu_stop();return
            self.total+=1
            if self.total>self.step_limit:
                self.guard=dict(problem='step_limit',pc=pc,steps=self.total,limit=self.step_limit);cpu.emu_stop();return
            if pc in LEAD_PCS and (pc in START_SET or in_f3a(self.last_pc if self.last_pc is not None else -1)):
                self.leads.append(dict(pc=pc,regs=self.regs(),pc_index=len(self.pcs)-1,event_index=len(self.events)))
            self.last_pc=pc
        c.hook_add(UC_HOOK_CODE,cb)
        return self
    def begin_step(self,stop_pc,checkpoints):
        super().begin_step(stop_pc,checkpoints);self.total=0           # the instruction watchdog counts per step (all split phases of a step together), so that split and continuous agree
    def run(self,allow_guard=False):
        self.leads=[];self.mine_seen=set(self.seen);self.computed=[]
        r=super().run(allow_guard=allow_guard)
        g=r['guard']
        if g is not None and g.get('problem')=='unsupported_code_target':
            t=g['target'];prev=r['pcs'][-2] if len(r['pcs'])>=2 and r['pcs'][-1]==t else (r['pcs'][-1] if r['pcs'] else None)
            if t&1:g['reason']='odd target PC %x (an address error on the original CPU)'%t;g['odd_pc']=True
            elif g.get('refused_before_jump'):g['reason']='computed PC %x from JMP/JSR table %x at %x is not a F3a block start (unsupported animation stage event PC); refused before the jump'%(t,EVAL_TABLE if g['pc']==EVAL_JMP else MAIN_TABLE,g['pc'])
            elif t in F3B_BOUNDARY_PCS:g['reason']='F3b boundary PC %x (callback entry / TRAP #15 site) reached without the declared stop: a stop only, never executed (unsupported animation stage event PC)'%t
            elif g.get('refused_before_execution'):g['reason']=('direct entry at %x, which is not a F3a block start'%t) if g.get('entry') else ('transfer from %x into the middle of a block at %x (not a F3a block start: unsupported animation stage event PC); refused before it executes'%(g['pc'],t))
            else:g['reason']='control transfer to %x, outside every routed range, from %s'%(t,hex(prev) if prev is not None else 'the entry')
        elif g is not None and g.get('problem') in ('unsupported_write','unmapped_or_protected'):
            g['reason']='write to the program ROM or a data access to an unmapped address %s (bus error on the original CPU)'%hex(g.get('address',0))
        elif g is not None and g.get('problem')=='unsupported_TRAP':
            g['reason']=('F3b TRAP #15 boundary %x reached without the declared stop: a stop only, never executed'%r['pcs'][-1]) if r['pcs'][-1] in F3B_BOUNDARY_PCS else 'TRAP #15 at %x inside a callee outside the F3a ranges (a TRAP boundary of that unit, never executed by the observer)'%r['pcs'][-1]
        elif g is not None and g.get('problem') in ('unsupported_data_device','unsupported_PVC_read_or_write'):
            g['reason']='data access to the device region at %x (size %d): only the permitted ports are modeled (a stream / list pointer there is not valid)'%(g.get('address',0),g.get('size',0))
        elif g is not None and g.get('problem')=='unsupported_odd_data_access':
            g['reason']='odd address %x for a %d-byte %s access (address error on the original CPU)'%(g['address'],g['size'],g['access']);g['reason_kind']='odd_word_access'
        elif g is not None and g.get('problem')=='step_limit':
            g['reason']='no terminator: the declared instruction watchdog (%d) expired at %x (the original code has no bound; the machine rolls back at its block budget)'%(g['limit'],g['pc']);g['reason_kind']='no_terminator'
        if g is not None and 'reason' not in g:g['reason']='native guard %s'%g.get('problem')
        r.update(leads=self.leads,wait=None,waiting=False,computed=self.computed)
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


F3Observer=None


def install_observer():
    global F3Observer
    base=[k for k in bc.U7Observer.__mro__ if k.__name__=='U5Observer'][0]
    F3Observer=type('F3Observer',(F3Mixin,base),{})
    fc.Observer=F3Observer


def W(address,size,value,why):return fc.ram_write(address,size,value,why)


# ----------------------------------------------------------------------------------
# Chain runner: persistent CPU, one step per run (one step = one node execution or one direct entry), split (stop at the first hit of every checkpoint) or continuous
# ----------------------------------------------------------------------------------
RUNS=[0]


def run_chain(program,spec,continuous,sink=None):
    RUNS[0]+=1
    fx=spec['fixture'];allow=bool(spec.get('guarded'));o=F3Observer(program,continuous);phases=[]
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
                if p['outgoing']['pc']!=target and p['outgoing']['pc'] in step.get('alts',()):
                    step['found_stop']=p['outgoing']['pc'];break                      # a declared F3b boundary stop was reached (a stop only, never executed)
                assert p['outgoing']['pc']==target,(spec['label'],step['label'],hex(p['outgoing']['pc']),hex(target))
                if p['outgoing']['pc']==step['stop_pc']:
                    if step.get('a7') is not None:
                        kind,value=step['a7']
                        want=(first['a7']+value)&M32 if kind=='entry' else value
                        assert p['outgoing']['a7']==want,(spec['label'],step['label'],hex(p['outgoing']['a7']),hex(want))
                    break
                assert p['phase_in_step']<400,(spec['label'],step['label'])
            if phases[-1]['guard'] is not None:
                assert allow,(spec['label'],phases[-1]['guard']);assert index==len(spec['steps'])-1
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
    """Probe: one continuous run without checkpoints discovers the order of the first hits of the block leaders (the split stops) and the declared end of every step."""
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
        order=[];entry=phases[index]['pcs'][0];end=phases[index]['outgoing']['pc']
        for pc in phases[index]['pcs'][1:]:
            if pc in CK_SET and pc not in order and pc!=entry and pc!=step['stop_pc'] and pc not in step.get('alts',()):order.append(pc)
        step['checkpoints']=order
        step['observed_end']=end if phases[index]['guard'] is None else None
        if spec.get('expect_end') is not None and not spec.get('guarded'):assert end==spec['expect_end'],(spec['label'],hex(end),hex(spec['expect_end']))
    return spec


def jdump(x):return json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()


def phase_digest(p):
    """SHA256 of the complete native record of one phase (every field that two reproductions must agree on)."""
    h=hashlib.sha256()
    for key in ('incoming','outgoing','pvc_before','pvc_after','ram_before','ram_after','guard','waiting','wait','host_changes','modeled_bank','bank_before','ff8_before','ff9_before','ff8_after','ff9_after','label','step','phase_in_step','stop_pc','step_stop_pc'):
        v=p[key];h.update(key.encode());h.update(v if isinstance(v,(bytes,bytearray)) else jdump(v))
    h.update(struct.pack('>%dI'%len(p['pcs']),*p['pcs']));h.update(jdump(p['events']));h.update(jdump(lead_key(p)));h.update(jdump(p['computed']))
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
    assert [p['stop_evidence'] for p in split if p['stop_evidence'] is not None]==[p['stop_evidence'] for p in control if p['stop_evidence'] is not None]
    return split,control,d_split,d_control


# ----------------------------------------------------------------------------------
# Stop evidence: a stop is accepted only directly after the transferring instruction
# ----------------------------------------------------------------------------------
def stop_evidence(program,p,origin,steppcs):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc'];ram=p['ram_after']
    if pc!=p['step_stop_pc'] and pc not in F3B_STOP_PCS:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(kind='zero-step',outgoing_pc=pc,previous_pc=None,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];a7=o['a7'];inc=origin['incoming']
    if pc==F3B_ENTRY and prev==0xe98ec:
        assert program[prev:prev+2].hex()=='4e75' and u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
        return dict(kind='f3b-boundary-via-return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',popped_return_long=pc,
            reached_from='RTS of the evaluator block e98ea popped the return LONG e94fe (R = the F3b entry, decision 3: PC := R); e94fe is never executed')
    if pc==F3B_ENTRY:
        assert prev==0xe91ac and program[prev:prev+4].hex()=='61000350',(p['label'],hex(prev))
        assert u32(ram,a7)==0xe91b0,(p['label'],hex(u32(ram,a7)))
        return dict(kind='f3b-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes='61000350',pushed_return_long=0xe91b0,
            reached_from='BSR.W e94fe at e91ac (bytes 61000350) pushed the return LONG e91b0 (A7 = %x); the F3b entry e94fe is never executed'%a7)
    for br,tz,tn in BUNDLED_BRANCH:
        if pc in (tz,tn) and prev==br:
            raw=program[br:br+4].hex();assert raw.startswith('6700'),raw
            return dict(kind='bundled-branch-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes=raw,taken=pc==tz,d0_byte=o['d0']&0xff,
                reached_from='BEQ.W at %x (bytes %s, the decision-3 bundled branch of the evaluator return) %s with D0.B = %02x; %x is never executed'%(br,raw,'taken' if pc==tz else 'not taken',o['d0']&0xff,pc))
    if pc in F3B_BOUNDARY_PCS:
        if prev==0xe98ec:
            assert program[prev:prev+2].hex()=='4e75' and u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
            return dict(kind='f3b-boundary-via-return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',popped_return_long=pc,
                reached_from='RTS of the evaluator block e98ea popped the return LONG %x (a F3b PC: callback entry or TRAP #15 site, declared as the stop); %x is never executed'%(pc,pc))
        assert prev==0x2ac0 and program[prev:prev+2].hex()=='4e90' and u32(ram,a7)==FRAME_RET,(p['label'],hex(prev))
        return dict(kind='f3b-callback-entry',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e90',pushed_return_long=FRAME_RET,
            reached_from='JSR (A0) at 2ac0 of the dispatcher entered the F3b child callback %x (declared as the stop; the return LONG 2ac2 is on the stack); %x is never executed'%(pc,pc))
    if pc==FRAME_RET:
        assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
        assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
        pushed=[i for i,x in enumerate(steppcs) if x==0x2ac0]
        if pushed and program[0x2ac0:0x2ac2].hex()=='4e90':
            return dict(kind='return-dispatcher',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',entry_a7=inc['a7'],dispatcher_jsr_pc=0x2ac0,
                reached_from='RTS at %x popped the return LONG 2ac2 pushed by the dispatcher JSR (A0) at 2ac0 inside this run (A7 after = %x); 2ac2 is never executed'%(prev,a7))
        on_stack=[off for off in range(0,64,2) if u32(origin['ram_before'],inc['a7']+off)==pc]
        assert on_stack,(p['label'],'the popped LONG %x was not declared on the stack at the step entry'%pc)
        return dict(kind='return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',return_long_on_stack_at_entry_offsets=on_stack,entry_a7=inc['a7'],
            reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x); %x is never executed'%(prev,pc,a7,pc))
    raise AssertionError((p['label'],'a stop at %x (reached from %x) is not a declared stop of this tool'%(pc,prev)))


def annotate(program,phases):
    first={};allpcs=collections.defaultdict(list)
    for p in phases:
        first.setdefault(p['step'],p);allpcs[p['step']].extend(p['pcs'])
    for p in phases:p['stop_evidence']=stop_evidence(program,p,first[p['step']],allpcs[p['step']])


# ----------------------------------------------------------------------------------
# Storage: content-addressed payloads (identical payloads share one file)
# ----------------------------------------------------------------------------------
BLOBS=None


def put_blob(data,ext='bin'):
    digest=sha(data);target=BLOBS/(digest+'.'+ext)
    if not target.exists():
        tmp=BLOBS/(digest+'.tmp%d'%os.getpid());tmp.write_bytes(data);os.replace(tmp,target)
    return digest


def ports_blob(events):return b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS)


def stop_reason(p):
    if p['guard'] is not None:return 'guard:%s'%p['guard'].get('problem')
    ev=p.get('stop_evidence')
    if ev is None:return 'checkpoint (split stop at the first hit of a block leader, before the instruction executes)'
    return ev['kind']


def compact(items,key=None,limit=2000):
    if len(items)<=limit:return items
    f=key or (lambda x:x);counts=collections.Counter(f(x) for x in items)
    return dict(truncated=True,count=len(items),first=items[:200],by_pc={hex(k):v for k,v in sorted(counts.items())})


def phase_row(j,p,artifacts,snapshots):
    return dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
        host_changes=p['host_changes'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
        guard=p['guard'],snapshots=snapshots,counts=fc.counts(p['events']),external_read_events=[dict(pc=e['pc'],address=e['address'],size=e['size'],bytes=e['bytes']) for e in p['events'] if e['region']=='external'],
        stop_reason=stop_reason(p),pc_count=len(p['pcs']),artifacts=artifacts,stop_evidence=p['stop_evidence'],computed_pc=p['computed'],
        leaders=compact([dict(pc=l['pc'],pc_index=l['pc_index'],event_index=l['event_index']) for l in p['leads']],key=lambda l:l['pc']))


def store(phases,files):
    """files=True: every payload is written as a content-addressed blob (RAM before/after, PVC, ports, trace); files=False: only the payload SHA256 values are recorded."""
    rows=[]
    for j,p in enumerate(phases):
        payloads=dict(ram_before=p['ram_before'],ram_after=p['ram_after'],pvc_before=p['pvc_before'],pvc_after=p['pvc_after'],ports=ports_blob(p['events']),
            trace=gzip.compress(jdump({k:p[k] for k in ('pcs','events','guard')})+b'\n',9,mtime=0))
        hashes={name:(put_blob(data,'json.gz' if name=='trace' else 'bin') if files else sha(data)) for name,data in payloads.items()}
        snapshots=[dict(registers=s['registers'],ram_sha256=sha(s['ram']),pvc_sha256=sha(s['pvc'])) for s in p['snapshots']]
        rows.append(phase_row(j,p,hashes,snapshots))
    return rows


def state_digest_of(p):
    """The scheduler observer's state digest (64KiB RAM, 16 registers, PC, bank, PVC words) of the OUTGOING state of a phase: comparable with the recorded seed digests."""
    o=p['outgoing'];return sched.state_blob_digest(p['ram_after'],{k:o[k] for k in REG16},o['pc'],(p['modeled_bank'],p['ff8_after'],p['ff9_after']))


def entry_digest_of(p):
    o=p['incoming'];return sched.state_blob_digest(p['ram_before'],{k:o[k] for k in REG16},o['pc'],(p['bank_before'],p['ff8_before'],p['ff9_before']))


def sched_ports_digest(events):
    """The scheduler observer's ordered port digest (kind 1 = PVC bank words, kind 2 = other device writes) of the events of a phase."""
    out=[]
    for e in events:
        if e['region']=='pvc':out.append((1,e['address'],e['size'],int(e['bytes'],16)))
        elif e['region'] in ('video','watchdog'):out.append((2,e['address'],e['size'],int(e['bytes'],16)))
    return sched.ports_digest(out)


# ----------------------------------------------------------------------------------
# Independent model: a M68000 subset interpreter that decodes the ORIGINAL ROM BYTES of the F3a ranges (decoder written from the 68000 programmer's reference by instruction format, not
# from the disassembler / Unicorn / C++).  Complete CCR (X N Z V C; None = unknown, a branch on an unknown flag is an error unless it is a declared carry consumer), 32-bit register
# semantics, explicit byte / word / long operations.  Calls leave the F3a ranges at a black-box entry; the native exit state of the black box is replayed (registers, RAM / PVC writes)
# and its carry is unknown (taken from the executed path).
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
SZ={0:1,1:2,2:4}
MASK={1:0xff,2:0xffff,4:M32}
SIGN={1:0x80,2:0x8000,4:0x80000000}
CONDS=('t','f','hi','ls','cc','cs','ne','eq','vc','vs','pl','mi','ge','lt','gt','le')


class NeedFlag(Exception):
    def __init__(self,names):self.names=names


class F3Model(object):
    def __init__(self,program,bank_state,ram,regs,sr=None):
        self.prog=program;self.bank,self.ff8,self.ff9=bank_state;self.ram=bytearray(ram)
        self.r={k:regs[k]&M32 for k in REG16};self.pc=regs['pc']
        self.cc=dict(X=None,N=None,Z=None,V=None,C=None)
        if sr is not None:self.cc=dict(X=(sr>>4)&1,N=(sr>>3)&1,Z=(sr>>2)&1,V=(sr>>1)&1,C=sr&1)
        self.leads=[];self.writes=[];self.reads=[];self.rom_reads=[];self.ports=[];self.evidence=[];self.cache={};self.steps=0
    # ---- memory (data accesses; instruction fetch decodes the ROM bytes directly and is not logged)
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
    def mem_write(self,a,n,v,log=True):
        a&=M32
        if n>1 and a&1:raise ModelError('odd write %x'%a)
        if a in (0x2ffff0,0x2ffff2) and n==2:
            if log:self.ports.append((2,a,v&0xffff))
            self.pvc(a,v&0xffff);return
        if not 0x100000<=a<0x200000:raise ModelError('write %x'%a)
        v&=MASK[n]
        for i,b in enumerate(v.to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
        if log:self.writes.append((a,n,v))
    def pvc(self,a,v):
        if a==0x2ffff0:self.ff8=v
        else:self.ff9=v
        self.bank,self.ff8,self.ff9=pvc_bank_update(self.ff8,self.ff9)
    # ---- decode (from the ROM bytes)
    def ext(self,pos):return int.from_bytes(self.prog[pos:pos+2],'big')
    def decode_ea(self,mode,reg,size,pos):
        """-> (descriptor, next extension position).  Descriptors are resolved at execution time."""
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
        elif hi==7 and not w&0x100:ins.update(op='moveq',reg=(w>>9)&7,imm=w&0xff,len=2)
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
        elif (w&0xfff8)==0x4880:ins.update(op='ext',size=2,reg=w&7,len=2)
        elif (w&0xfff8)==0x48c0:ins.update(op='ext',size=4,reg=w&7,len=2)
        elif (w&0xfff8)==0x4840:ins.update(op='swap',reg=w&7,len=2)
        elif hi==5 and (w&0xc0)==0xc0 and ((w>>3)&7)!=1:
            ea,pos=self.decode_ea((w>>3)&7,w&7,1,pc+2);ins.update(op='scc',cond=(w>>8)&15,dst=ea,len=pos-pc)
        elif hi==5 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);q=(w>>9)&7
            ins.update(op='subq' if w&0x100 else 'addq',size=size,imm=q or 8,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xff00)==0x0800:                    # static bit ops
            t=(w>>6)&3;bit=self.ext(pc+2)&0xff;ea,pos=self.decode_ea((w>>3)&7,w&7,1,pc+4);ins.update(op=['btst','bchg','bclr','bset'][t],bit=bit,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xf00) in (0x000,0x200,0x400,0x600,0xa00,0xc00) and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos)
            ins.update(op={0x000:'ori',0x200:'andi',0x400:'subi',0x600:'addi',0xa00:'eori',0xc00:'cmpi'}[w&0xf00],size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi in (8,9,0xb,0xc,0xd):
            om=(w>>6)&7;reg=(w>>9)&7
            if hi==0xb:
                if om in (0,1,2):
                    size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='cmp',size=size,reg=reg,src=ea,len=pos-pc)
                elif om in (3,7):
                    size=2 if om==3 else 4;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='cmpa',size=size,reg=reg,src=ea,len=pos-pc)
                else:raise ModelError('EOR/CMPM %x'%pc)
            elif om in (3,7):
                if hi in (9,0xd):
                    size=2 if om==3 else 4;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='suba' if hi==9 else 'adda',size=size,reg=reg,src=ea,len=pos-pc)
                else:raise ModelError('MUL/DIV %x'%pc)
            else:
                name={8:'or',9:'sub',0xc:'and',0xd:'add'}[hi]
                if om in (0,1,2):
                    size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op=name,size=size,reg=reg,src=ea,to='dn',len=pos-pc)
                elif om in (4,5,6):
                    size=SZ[om-4];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op=name,size=size,reg=reg,dst=ea,to='ea',len=pos-pc)
                else:raise ModelError('opcode %04x at %x'%(w,pc))
        elif hi==0xe and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];typ=(w>>3)&3;left=(w>>8)&1;cnt=(w>>9)&7;ir=(w>>5)&1
            if typ!=1:raise ModelError('shift type %d at %x'%(typ,pc))
            ins.update(op='lsl' if left else 'lsr',size=size,reg=w&7,count=cnt or 8,ir=ir,creg=cnt,len=2)
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
        if c==0:return True
        if c==1:return False
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
    def step(self,nl):
        pc=self.pc;ins=self.decode(pc);op=ins['op'];nxt=(pc+ins['len'])&M32;r=self.r
        if op=='move':
            s=self.resolve(ins['src'],ins['size']);v=self.get(s,ins['size']);d=self.resolve(ins['dst'],ins['size']);self.put(d,ins['size'],v);self.nz(v,ins['size'])
        elif op=='movea':
            s=self.resolve(ins['src'],ins['size']);v=self.get(s,ins['size']);r['a%d'%ins['dst'][1]]=sext(v,ins['size'])&M32
        elif op=='moveq':
            v=sext(ins['imm'],1)&M32;r['d%d'%ins['reg']]=v;self.nz(v,4)
        elif op=='lea':
            loc=self.resolve(ins['src'],4);r['a%d'%ins['reg']]=loc[1]
        elif op=='clr':
            d=self.resolve(ins['dst'],ins['size']);self.put(d,ins['size'],0);self.cc.update(N=0,Z=1,V=0,C=0)
        elif op=='tst':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);self.nz(v,ins['size'])
        elif op=='ext':
            n='d%d'%ins['reg'];half=ins['size']//2;v=sext(r[n],half)&MASK[ins['size']];self.put(('reg',n),ins['size'],v);self.nz(v,ins['size'])
        elif op=='swap':
            n='d%d'%ins['reg'];v=r[n];r[n]=((v<<16)|(v>>16))&M32;self.nz(r[n],4)
        elif op=='scc':
            d=self.resolve(ins['dst'],1);self.put(d,1,0xff if self.cond(ins['cond']) else 0)
        elif op in ('addq','subq'):
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size'])
            if d[0]=='reg' and d[1][0]=='a':raise ModelError('ADDQ/SUBQ to An')
            self.put(d,ins['size'],self.add(v,ins['imm'],ins['size']) if op=='addq' else self.sub(v,ins['imm'],ins['size']))
        elif op in ('subi','addi','ori','andi','eori'):
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);s=ins['imm']&MASK[ins['size']]
            if op=='subi':res=self.sub(v,s,ins['size'])
            elif op=='addi':res=self.add(v,s,ins['size'])
            else:
                res={'ori':v|s,'andi':v&s,'eori':v^s}[op];self.nz(res,ins['size'])
            self.put(d,ins['size'],res)
        elif op=='cmpi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.sub(v,ins['imm'],ins['size'],x=False)
        elif op=='cmp':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);self.sub(r['d%d'%ins['reg']],v,ins['size'],x=False)
        elif op=='cmpa':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);v=sext(v,ins['size'])&M32;self.sub(r['a%d'%ins['reg']],v,4,x=False)
        elif op in ('add','sub','and','or'):
            n='d%d'%ins['reg']
            if ins['to']=='dn':
                v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);a=r[n]&MASK[ins['size']]
                res={'add':lambda:self.add(a,v,ins['size']),'sub':lambda:self.sub(a,v,ins['size']),'and':lambda:a&v,'or':lambda:a|v}[op]()
                if op in ('and','or'):self.nz(res,ins['size'])
                self.put(('reg',n),ins['size'],res)
            else:
                d=self.resolve(ins['dst'],ins['size']);m=self.get(d,ins['size']);a=r[n]&MASK[ins['size']]
                res={'add':lambda:self.add(m,a,ins['size']),'sub':lambda:self.sub(m,a,ins['size']),'and':lambda:m&a,'or':lambda:m|a}[op]()
                if op in ('and','or'):self.nz(res,ins['size'])
                self.put(d,ins['size'],res)
        elif op in ('adda','suba'):
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='a%d'%ins['reg'];v=sext(v,ins['size'])
            r[n]=(r[n]+v)&M32 if op=='adda' else (r[n]-v)&M32
        elif op in ('lsl','lsr'):
            n='d%d'%ins['reg'];size=ins['size'];m=MASK[size];bits=8*size
            cnt=ins['count'] if not ins['ir'] else r['d%d'%ins['creg']]&63
            v=r[n]&m
            if cnt==0:self.nz(v,size);self.cc['C']=0
            else:
                if op=='lsl':res=(v<<cnt)&m;c=(v>>(bits-cnt))&1 if cnt<=bits else 0
                else:res=v>>cnt if cnt<bits else 0;c=(v>>(cnt-1))&1 if cnt<=bits else 0
                self.nz(res,size);self.cc.update(C=c,X=c);v=res
            self.put(('reg',n),size,v)
        elif op in ('bset','bclr','btst','bchg'):
            d=self.resolve(ins['dst'],1);v=self.get(d,1);bit=ins['bit']%8;self.cc['Z']=int((v>>bit)&1==0)
            if op=='bset':self.put(d,1,v|(1<<bit))
            elif op=='bclr':self.put(d,1,v&~(1<<bit))
            elif op=='bchg':self.put(d,1,v^(1<<bit))
        elif op=='jsr':
            loc=self.resolve(ins['src'],4);self.push32(nxt);nxt=loc[1]
        elif op=='jmp':
            loc=self.resolve(ins['src'],4);nxt=loc[1]
        elif op=='bsr':self.push32(nxt);nxt=ins['target']
        elif op=='bra':nxt=ins['target']
        elif op=='bcc':
            try:taken=self.cond(ins['cond'])
            except NeedFlag as e:
                j=len(self.leads)
                if pc not in CONSUMERS:raise ModelError('branch at %x on the unknown flag %s (not a declared carry consumer)'%(pc,e.names))
                if j>=len(self.nl):raise ModelError('unknown carry at %x and no native successor leader'%pc)
                succ=self.nl[j]['pc']
                if succ not in (ins['target'],nxt):raise ModelError('native successor %x of %x is neither target %x nor fall-through %x'%(succ,pc,ins['target'],nxt))
                taken=succ==ins['target'];self.evidence.append(dict(pc=hex(pc),flag='C',taken=taken,source='native executed path: the next native leader after the branch is %x (carry produced by a black box 49392)'%succ))
            if taken:nxt=ins['target']
        elif op=='rts':nxt=self.pop32()
        elif op=='trap':raise ModelError('TRAP executed at %x'%pc)
        else:raise ModelError(op)
        self.pc=nxt


def lead_of(M,pc):
    regs=dict(M.r);regs['pc']=pc;return regs


def replay_events(M,events,lo,hi):
    """Replay the black-box events (all of them by PCs outside the F3a ranges): RAM writes and PVC register writes (bank tracking)."""
    for e in events[lo:hi]:
        if in_f3a(e['pc']):raise ModelError('F3a-attributed event %s at %x inside a black-box slice'%(e['access'],e['pc']))
        a,n=e['address'],e['size']
        if e['region']=='ram' and e['access']=='write':M.mem_write(a,n,int(e['bytes'],16),log=False)
        elif e['region']=='pvc':M.pvc(a,int(e['bytes'],16))


BUNDLED_PCS=frozenset(pc for pc,_,_ in BUNDLED_BRANCH)


def run_segment(M,p,nl):
    events=p['events'];out=p['outgoing'];steps=0;M.nl=nl
    if not in_f3a(M.pc):                                              # entry outside F3a (the dispatcher shell 2ab8 .. 2ac0 and the JSR (A0)): replayed up to the first native leader
        hi=nl[0]['event_index'] if nl else len(events);replay_events(M,events,0,hi)
        if not nl:
            M.r.update({k:out[k] for k in REG16});M.pc=out['pc'];return 'end-in-blackbox'
        M.r.update({k:nl[0]['regs'][k] for k in REG16});M.pc=nl[0]['pc'];M.cc=dict(X=None,N=None,Z=None,V=None,C=None)
    while True:
        pc=M.pc
        if pc in F3B_STOP_PCS and pc==out['pc'] and p['guard'] is None:return 'stop-at-declared-pc'
        if pc==out['pc'] and not in_f3a(pc) and pc not in BB_ENTRIES and pc not in BUNDLED_PCS and p['guard'] is None:return 'stop-at-declared-pc'
        if not in_f3a(pc) and pc not in BUNDLED_PCS:
            if pc not in BB_ENTRIES:raise ModelError('control left the F3a ranges at %x (not a declared black-box entry)'%pc)
            M.leads.append(lead_of(M,pc));e=len(M.leads)-1
            if e>=len(nl) or nl[e]['pc']!=pc:raise ModelError('black-box entry %x: the native leaders do not align at lead %d'%(pc,e))
            ret=M.mem_read(M.r['a7'],4,log=False);a7=M.r['a7']
            hi=nl[e+1]['event_index'] if e+1<len(nl) else len(events);replay_events(M,events,nl[e]['event_index'],hi)
            if e+1<len(nl):
                nxt=nl[e+1]
                if nxt['pc']!=ret or nxt['regs']['a7']!=(a7+4)&M32:raise ModelError('black box %x returned to %x with A7 %x, the model expects %x / %x'%(pc,nxt['pc'],nxt['regs']['a7'],ret,(a7+4)&M32))
                M.r.update({k:nxt['regs'][k] for k in REG16});M.pc=nxt['pc'];M.cc=dict(X=None,N=None,Z=None,V=None,C=None)
                continue
            M.r.update({k:out[k] for k in REG16});M.pc=out['pc'];return 'end-in-blackbox'
        if pc in START_SET:M.leads.append(lead_of(M,pc))
        steps+=1
        if steps>3000000:raise ModelError('model step limit')
        M.step(nl)


def check_model_phase(program,label,p,sr):
    nl=[dict(pc=l['pc'],regs=l['regs'],event_index=l['event_index']) for l in p['leads']]
    inc=p['incoming']
    M=F3Model(program,(p['bank_before'],p['ff8_before'],p['ff9_before']),p['ram_before'],inc,sr=sr)
    row=dict(label=label,kind='f3a-model',start_pc=hex(inc['pc']),start_in_f3a=in_f3a(inc['pc']))
    if len(p['pcs'])==1 and not p['leads'] and p['outgoing']['pc']==inc['pc']:
        row.update(equal=p['ram_after']==p['ram_before'] and {k:inc[k] for k in REG16+('pc',)}=={k:p['outgoing'][k] for k in REG16+('pc',)} and not p['events'],end='zero-step',leaders=0,mismatches=[])
        if not row['equal']:DISCREPANCIES.append(dict(label=label,kind='zero-step-changed-state'))
        return row
    try:end=run_segment(M,p,nl)
    except (ModelError,AssertionError,KeyError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=label,kind='model-could-not-follow-native',detail=repr(e)));return row
    ev=p['events'];out=p['outgoing'];bad=[]
    ml=[(l['pc'],{k:v for k,v in l.items() if k!='pc'}) for l in M.leads];nlk=[(l['pc'],{k:v for k,v in l['regs'].items() if k!='pc'}) for l in nl]
    if len(ml)!=len(nlk):bad.append(dict(what='leader count',model=len(ml),native=len(nlk)))
    for i,(a,b) in enumerate(zip(ml,nlk)):
        if a!=b:bad.append(dict(what='leader %d'%i,model_pc=hex(a[0]),native_pc=hex(b[0]),differing_registers={k:(hex(a[1][k]),hex(b[1][k])) for k in a[1] if a[1][k]!=b[1].get(k)}));break
    inr=lambda pc:in_f3a(pc) or pc in BUNDLED_PCS
    nw=[(e['address'],e['size'],int(e['bytes'],16)) for e in ev if e['region']=='ram' and e['access']=='write' and inr(e['pc'])]
    if M.writes!=nw:
        first=next((i for i,(x,y) in enumerate(zip(M.writes,nw)) if x!=y),min(len(M.writes),len(nw)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(nw),first_difference=first,model=M.writes[first:first+3],native=nw[first:first+3]))
    nr=[(e['address'],e['size']) for e in ev if e['region']=='ram' and e['access']=='read' and inr(e['pc'])]
    if M.reads!=nr:
        first=next((i for i,(x,y) in enumerate(zip(M.reads,nr)) if x!=y),min(len(M.reads),len(nr)))
        bad.append(dict(what='ordered RAM reads',model_count=len(M.reads),native_count=len(nr),first_difference=first,model=M.reads[first:first+3],native=nr[first:first+3]))
    nrom=[(e['address'],e['size'],e['region']) for e in ev if e['region'] in ('fixed','bank') and e['access']=='read' and inr(e['pc'])]
    if M.rom_reads!=nrom:bad.append(dict(what='ordered fixed/bank reads',model_count=len(M.rom_reads),native_count=len(nrom),model=M.rom_reads[:6],native=nrom[:6]))
    np_=[(e['size'],e['address'],int(e['bytes'],16)) for e in ev if e['region'] in PORT_REGIONS and e['access']=='write' and inr(e['pc'])]
    if M.ports!=np_:bad.append(dict(what='ordered ports',model=M.ports,native=np_))
    if M.pc!=out['pc']:bad.append(dict(what='final PC',model=hex(M.pc),native=hex(out['pc']),end=end))
    final=dict(M.r)
    if final!={k:out[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(out[k])) for k in final if final[k]!=out[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if (M.bank,M.ff8,M.ff9)!=(p['modeled_bank'],p['ff8_after'],p['ff9_after']):bad.append(dict(what='bank',model=(hex(M.bank),M.ff8,M.ff9),native=(hex(p['modeled_bank']),p['ff8_after'],p['ff9_after'])))
    row.update(equal=not bad,end=end,leaders=len(M.leads),leader_pcs_distinct=len({l['pc'] for l in M.leads}),ordered_ram_writes=len(M.writes),ordered_ram_reads=len(M.reads),ordered_rom_reads=len(M.rom_reads),ordered_ports=len(M.ports),
        ram_bytes_compared=0x10000,final_registers_compared=sorted(final),carry_evidence=M.evidence,model_leader_pcs=sorted({hex(l['pc']) for l in M.leads}),mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=label,kind='model-vs-native',mismatches=bad[:4]))
    return row


def model_conditions(program,spec,control):
    out=[];fx=spec['fixture']
    for k,p in enumerate(control):
        sr=fx.get('sr',0x2000) if (p['step']==0 and p['phase_in_step']==0) else None
        out.append(check_model_phase(program,'%s#phase%d'%(spec['label'],k),p,sr))
    return out


# ----------------------------------------------------------------------------------
# Static checks of the contract (byte table, block starts, bundled branches, carry classes, flow-only blocks, computed-PC tables)
# ----------------------------------------------------------------------------------
FLOW_OPS={'lea','movea','jsr','jmp','bsr','bra','rts','btst','bset','bclr','bchg','bcc'}
PRODUCES={'move':'NZVC','moveq':'NZVC','clr':'NZVC','tst':'NZVC','swap':'NZVC','ext':'NZVC','and':'NZVC','or':'NZVC','subq':'XNZVC','addq':'XNZVC','subi':'XNZVC','addi':'XNZVC','add':'XNZVC','sub':'XNZVC',
    'cmp':'NZVC','cmpa':'NZVC','cmpi':'NZVC','ori':'NZVC','andi':'NZVC','eori':'NZVC','lsl':'XNZVC','lsr':'XNZVC','bset':'Z','bclr':'Z','btst':'Z','bchg':'Z'}
CONSUMES={2:'CZ',3:'CZ',4:'C',5:'C',6:'Z',7:'Z',8:'V',9:'V',10:'N',11:'N',12:'NV',13:'NV',14:'NVZ',15:'NVZ'}
COND_USERS=('bcc','scc')


def block_extents(program):
    """Blocks of the F3a ranges: from a block start to the next start (or range end)."""
    starts=set(STARTS);blocks={};M=F3Model(program,(0x200000,0xa0,0x1000),bytes(0x10000),dict(pc=0,**{k:0 for k in REG16}))
    for lo,hi in F3A_RANGES:
        pc=lo;cur=None
        while pc<hi:
            if pc in starts or cur is None:cur=pc;blocks[cur]=[]
            ins=M.decode(pc);blocks[cur].append(ins);pc+=ins['len']
        assert pc==hi,(hex(lo),hex(hi),hex(pc))
    return blocks


def static_checks(program):
    starts=set(STARTS);blocks=block_extents(program);M=F3Model(program,(0x200000,0xa0,0x1000),bytes(0x10000),dict(pc=0,**{k:0 for k in REG16}))
    flow_rows={};consumers={};total_ins=0;lens_ok=True
    for start in sorted(blocks):
        ins=blocks[start];total_ins+=len(ins)
        for i in ins:
            if i['len']!=F3A_INSTR[i['pc']]['size']:lens_ok=False
        flow_rows[start]=dict(start=hex(start),instructions=len(ins),flow_only=all(i['op'] in FLOW_OPS for i in ins),mnemonics=sorted(set(i['op'] for i in ins)))
        defined=set();missing=set()
        for i in ins:
            if i['op'] in COND_USERS and i['cond'] in CONSUMES:missing|=set(CONSUMES[i['cond']])-defined
            defined|=set(PRODUCES.get(i['op'],''))
        if missing:consumers[start]=''.join(sorted(missing))
    preserve_expected=set(PRESERVE);preserve_decoded={s for s,r in flow_rows.items() if r['flow_only']}
    bundled_ok=[]
    for pc in BUNDLED:
        ins=M.decode(pc);bundled_ok.append(dict(pc=hex(pc),op=ins['op'],is_conditional_branch=ins['op']=='bcc',is_block_start=pc in starts,
            inside_range=in_f3a(pc),preceded_by_block=any(pc in [i['pc'] for i in blocks[s]] for s in blocks)))
    table={}
    for name,base,n in (('e91e4',MAIN_TABLE,8),('e97e4',EVAL_TABLE,34)):
        slots=[]
        for k in range(n):
            pc=base+4*k;ins=M.decode(pc);slots.append(dict(slot=hex(pc),op=ins['op'],target=hex(ins['target']),target_is_start=ins['target'] in starts))
        table[name]=slots
    # the e97e0 table reach: index (op-80)*4, every op value 80..ff
    reach=[]
    for opb in range(0x80,0x100):
        t=EVAL_TABLE+4*(opb-0x80)
        if t in starts and opb<0xa2:cls='table-slot'
        elif t in starts:cls='block-start'
        elif t in F3A_INSTR:cls='interior-instruction-start'
        elif in_f3a(t):cls='inside-instruction'
        else:cls='outside-F3a'
        reach.append(dict(op=opb,target=t,cls=cls))
    return dict(instructions_decoded=len(F3A_INSTR),block_starts=len(starts),model_decoder_lengths_equal_disassembler=lens_ok,decoded_leaders_equal_contract=DECODED_LEADERS==starts,
        bundled_branches=bundled_ok,flow_only_blocks_decoded=sorted(hex(x) for x in preserve_decoded),flow_only_blocks_contract=sorted(hex(x) for x in preserve_expected),flow_only_equal_contract=preserve_decoded==preserve_expected,
        flow_only_decoded_minus_contract=sorted(hex(x) for x in preserve_decoded-preserve_expected),flow_only_contract_minus_decoded=sorted(hex(x) for x in preserve_expected-preserve_decoded),
        carry_consumers_computed={hex(k):v for k,v in sorted(consumers.items())},carry_consumers_contract=sorted(hex(x) for x in CONSUMERS),
        carry_consumers_equal={k for k,v in consumers.items() if 'C' in v}==set(CONSUMERS) and all(v=='C' for k,v in consumers.items() if k in CONSUMERS),
        non_carry_consumers={hex(k):v for k,v in consumers.items() if k not in CONSUMERS},flow_rows=[flow_rows[k] for k in sorted(flow_rows)],bytes=TABLE,
        blocks_total_instructions=total_ins,black_box_entries=[hex(x) for x in BB_ENTRIES],tables=table,e97e0_reach=reach,even_pcs=len(EVEN_PCS),interior_pcs=len(INTERIOR))


# ----------------------------------------------------------------------------------
# Seeds, bases and fixtures
# ----------------------------------------------------------------------------------
G={}
SCR=0x10f400                                                # free work-RAM scratch above the live stack top (10f000): event streams / expressions (zero in every base state)
SCR2=0x10f500
SCRN=0x10f600                                               # fake list nodes
SCRB=0x10f800
CUSTOM=[]


def pvc_page_for(bank_state):
    page=bytearray(8192);page[0x1ff0:0x1ff2]=bank_state[1].to_bytes(2,'big');page[0x1ff2:0x1ff4]=bank_state[2].to_bytes(2,'big');return bytes(page)


def bank_tuple(n):return (0x200000,0xa0,0x1000) if n==2 else (0x300000,0xa0,0x2000)


def load_records():
    raw=SEED_FILE.read_bytes();seed_obs=SEED_OBS.read_bytes()
    assert sha(seed_obs)==SEED_OBS_SHA,'scheduler observation.json changed'
    obs=json.loads(seed_obs);idx=obs['f3_node_seed_index'];assert idx['sha256']==sha(raw),'f3_node_seeds.json.gz changed'
    recs=json.loads(gzip.decompress(raw))['records'];assert len(recs)==idx['records']==9987
    G['seed_file_sha']=sha(raw);G['records']=recs
    G['rec_by_key']={(r['case'],r['frame'],r['seq']):r for r in recs}
    return recs


def dump_state(rec,kind):
    dm=rec['dumps'][kind];data=(SEED_DIR/'blobs'/(dm['ram']+'.bin')).read_bytes()
    assert len(data)==0x10000 and sha(data)==dm['ram'],dm['ram']
    return dict(ram=data,regs=dict(dm['regs']),bank=tuple(dm['bank']),digest=dm['state'],record=(rec['case'],rec['frame'],rec['seq']),cb=rec['cb'])


def make_bases():
    recs=G['records']
    r9176=next(r for r in recs if r['cb']==0xe9176 and 'dumps' in r and not r.get('e94fe'))
    r9150=next(r for r in recs if r['cb']==0xe9150 and 'dumps' in r)
    G['bases']={}
    for name,rec in (('e9176',r9176),('e9150',r9150)):
        b=dump_state(rec,'entry');b['name']='recorded F3 node entry dump (seed %d frame %d seq %d, cb %x)'%(rec['case'],rec['frame'],rec['seq'],rec['cb']);b['sha256']=sha(b['ram'])
        assert b['regs']['a6']==NODE and b['regs']['a7']==SPD and b['regs']['a5']==A5V and u32(b['ram'],BASE_LONG)==SPD
        assert not any(b['ram'][0xf000:0x10000]),'scratch area is not zero'
        G['bases'][name]=b


def node_fixture(label,base,regs=None,a7=None,bank=None,sr=None,entry=NODE_PC,stack=(),note=''):
    b=G['bases'][base];r=dict(b['regs']);r.update(regs or {})
    a7v=b['regs']['a7'] if a7 is None else a7
    bk=b['bank'] if bank is None else bank_tuple(bank)
    regs14={k:r[k] for k in KEYS14};regs14['a5']=r['a5']
    prov=dict(kind='declared fixture on a recorded F3 node entry state: '+note,base=b['name'],base_ram_sha256=b['sha256'],base_state_digest=b['digest'],entry=hex(entry),registers_overridden={k:hex(v) for k,v in (regs or {}).items()},
        declared_sr=sr,declared_a7=hex(a7v),declared_bank=[hex(bk[0]),bk[1],bk[2]],stack=[(hex(a),x.hex()) for a,x in stack])
    fx=sc.make_fx(label,b['ram'],regs14,(bk,pvc_page_for(bk)),entry,a7v,prov,(),list(stack),role='declared %s entry %x (%s)'%('node' if entry==NODE_PC else 'direct',entry,note))
    fx['group']='typed'
    if sr is not None:fx['sr']=sr
    return fx,prov


def wbytes(address,data,why):
    """Declared host writes of a byte string (WORD writes where the address is even and two bytes remain, BYTE writes otherwise)."""
    out=[];i=0
    while i<len(data):
        if (address+i)%2==0 and i+1<len(data):out.append(W(address+i,2,int.from_bytes(data[i:i+2],'big'),'%s: bytes +%d..%d'%(why,i,i+1)));i+=2
        else:out.append(W(address+i,1,data[i],'%s: byte +%d'%(why,i)));i+=1
    return out


def stream_ptr(addr=SCR):return W(NODE+0x76,4,addr,'declared stream pointer 76(A6) := %x'%addr)


def step_of(label,changes,stop,a7,alts=F3B_STOP_PCS,**extra):
    return dict(label=label,changes=list(changes),stop_pc=stop,checkpoints=[],a7=a7,expect=None,alts=tuple(alts),**extra)


def cust(label,group,base='e9176',setup=(),regs=None,sr=None,a7=None,bank=None,entry='node',stack_ret=True,stack_extra=(),ret=FRAME_RET,expect_guard=None,expect_end=None,step_limit=None,model=True,store='control',note='',
        alts=F3B_STOP_PCS,first_stop=None,a7_stop='default',dump=True,meta=None):
    def make(program):
        if entry=='node':
            fx,prov=node_fixture(label,base,regs,a7,bank,sr,NODE_PC,(),note);stop=FRAME_RET if first_stop is None else first_stop
            a7s=('abs',fx['initial_a7']) if stop==FRAME_RET else (None if a7_stop=='default' else a7_stop)
        else:
            a7v=(SPD-4) if a7 is None else a7
            stack=([(a7v,ret.to_bytes(4,'big'))] if stack_ret else [])+list(stack_extra)
            fx,prov=node_fixture(label,base,regs,a7v,bank,sr,entry,stack,note);stop=ret if first_stop is None else first_stop;a7s=('abs',a7v+4) if (stack_ret and a7_stop=='default') else (None if a7_stop=='default' else a7_stop)
        if step_limit is not None:fx['step_limit']=step_limit;prov['declared_step_limit']=step_limit
        step=step_of(label,setup,stop,a7s,alts)
        spec=dict(label=label,group=group,fixture=fx,steps=[step],provenance=prov,model=model,store=store,dump=dump,note=note,meta=meta or {})
        if expect_guard is not None:
            spec.update(guarded=True,guard=dict(expect_guard),model=False)
        if expect_end is not None:spec['expect_end']=expect_end
        with_checkpoints(program,spec)
        if expect_guard is not None:
            assert spec['steps'][0]['observed_end'] is None,(label,'expected a guard, the run ended at %x'%spec['steps'][0]['observed_end'])
        return spec
    make.label=label;CUSTOM.append(make)


def op_stream(ops,extra=(),ptr=SCR):
    """Declared event stream bytes at `ptr` (RAM scratch) and 76(A6) := ptr (+ extra declared writes)."""
    return [stream_ptr(ptr)]+wbytes(ptr,bytes(ops),'declared event stream at %x'%ptr)+list(extra)


def expr_stream(expr,tail=bytes([7,2,0x10])):
    """Opcode 05 with the expression `expr` (operator bytes, a0 appended): true -> advance L to `tail` (op07 clears 80(A6), terminator 10); false -> A0 += L + 2 (skips the op07: the frame ends)."""
    body=bytes(expr)+b'\xa0';L=4+len(body);off=L+2
    return bytes([5,L,off>>8,off&0xff])+body+tail


def class_bytes(**kw):
    return [W(0x10de30+k,1,v,'declared class counter BYTE 10de%02x := %02x'%(0x30+k,v)) for k,v in sorted((int(k[1:]),v) for k,v in kw.items())]


def chain_nodes(classes,depths=None,base=SCRN,stride=0x80):
    """Declared fake list nodes at base+i*stride: 100bf4 -> N0 -> N1 .. -> terminator node (depth 0).  classes: BYTE 6b of each node (None = terminator)."""
    out=[];prev=NODE
    for i,c in enumerate(classes+[None]):
        a=base+stride*i
        out.append(W(prev+8,4,a,'declared list link 8(%x) := %x'%(prev,a)))
        if c is None:
            out.append(W(a+0x10,2,0,'declared terminator node %x: depth WORD 10(node) := 0'%a));break
        d=1 if depths is None else depths[i]
        out+= [W(a+0x10,2,d,'declared node %x: depth WORD 10(node) := %d'%(a,d)),W(a+0x6b,1,c,'declared node %x: class BYTE 6b(node) := %02x'%(a,c))]
        prev=a
    return out


def dense_chain(classes,base=0x105da0,stride=0x14):
    """Declared fake list nodes packed at `stride` bytes (the fields 8 / 10 / 6b of different nodes never overlap for stride 14): 100bf4 -> N0 -> ... -> terminator (depth 0); used for the 255 / 256 / 257 node counter wrap."""
    out=[];prev=NODE
    for i,c in enumerate(list(classes)+[None]):
        a=base+stride*i
        out.append(W(prev+8,4,a,'declared list link 8(%x) := %x'%(prev,a)))
        if c is None:
            out.append(W(a+0x10,2,0,'declared terminator node %x: depth WORD 10(node) := 0'%a));break
        out+=[W(a+0x10,2,1,'declared node %x: depth WORD 10(node) := 1'%a),W(a+0x6b,1,c,'declared node %x: class BYTE 6b(node) := %02x'%(a,c))]
        prev=a
    return out


def player_setup(mask,p0=None,p1=None):
    """Declared presence mask BYTE 10d68e (bit p = player p) and the player object positions WORD 42 / 46 of 100cb8 (p0 = (x,y)) and 100da8 (p1)."""
    out=[W(0x10d68e,1,mask,'declared player presence mask BYTE 10d68e := %02x'%mask)]
    for base,pos,name in ((0x100cb8,p0,'player 0'),(0x100da8,p1,'player 1')):
        if pos is not None:out+=[W(base+0x42,2,pos[0],'declared %s x WORD 42(%x) := %04x'%(name,base,pos[0])),W(base+0x46,2,pos[1],'declared %s y WORD 46(%x) := %04x'%(name,base,pos[1]))]
    return out


def input_setup(player,index,active=1):
    """Declared player input state for 4d7a6 (D0 = player): the player object callback LONG := 123456 (not 270e: 289e returns C = 1 and 4d7a6 goes on), the state WORD (A4) := active, BYTE 27(A4) := index."""
    obj=0x100cb8 if player==0 else 0x100da8;a4=0x10dcba if player==0 else 0x10dce6
    return [W(obj,4,0x123456,'declared player %d object callback LONG := 123456 (not 270e: 289e C = 1)'%player),W(a4,2,active,'declared player %d input state WORD %x := %04x'%(player,a4,active)),
        W(a4+0x27,1,index,'declared player %d input state BYTE 27(%x) := %02x'%(player,a4,index))]


def find_bank_streams(program):
    """Banked-window stream positions (CPU window address 200000 + offset; the physical bytes depend on the bank selected at the read): an op07 chain ending in a terminator, a bare terminator, an op 08..0f."""
    out={}
    for bank,name in ((0x200000,'b2'),(0x300000,'b3')):
        win=program[bank:bank+0xfe000];d={}
        d['op07']=next(k for k in range(0x100,len(win)-8,2) if win[k]==7 and win[k+1]==2 and win[k+2]>=0x10)
        d['term']=next(k for k in range(0x100,len(win)-8,2) if 0x10<=win[k]<=0x7f)
        d['f3b']=next(k for k in range(0x100,len(win)-8,2) if 8<=win[k]<=0xf)
        out[name]=d
    return out


# ----------------------------------------------------------------------------------
# Independent high-level expectation of the evaluator (contract execution semantics 7): used only for claims, not for any run
# ----------------------------------------------------------------------------------
def s8(v):return v-256 if v&0x80 else v


def expect_expr(expr,ram,n80):
    """Value (BYTE) the evaluator pops for the operator bytes `expr` (+ a0), the contract's semantics: <80 push value; 80..8b 8d..95 push BYTE 10de30+(op-80); 8c refreshes 10de3c (sum of the BYTES 10de30..10de37)
    and pushes it; 96 ff, 97 00, 98 80(A6); 99..9d a = pop, top = Scc(a - top) (EQ GT GE LT LE, signed); 9e / 9f top &=/|= (pop != 0 ? ff : 0); a1 top += pop; None = unbalanced / unsupported."""
    st=[];cls=lambda k:ram[(0x10de30+k)&0xffff]
    for b in list(expr)+[0xa0]:
        if b<0x80:st.append(b)
        elif b<=0x95 and b!=0x8c:st.append(cls(b-0x80))
        elif b==0x8c:st.append(sum(cls(k) for k in range(8))&0xff)
        elif b==0x96:st.append(0xff)
        elif b==0x97:st.append(0)
        elif b==0x98:st.append(n80)
        elif 0x99<=b<=0x9d:
            if len(st)<2:return None
            a=st.pop();t=st[-1];d=s8(a)-s8(t)
            st[-1]=0xff if {0x99:a==t,0x9a:d>0,0x9b:d>=0,0x9c:d<0,0x9d:d<=0}[b] else 0
        elif b in (0x9e,0x9f):
            if len(st)<2:return None
            a=st.pop();m=0xff if a else 0;st[-1]=(st[-1]&m) if b==0x9e else (st[-1]|m)
        elif b==0xa1:
            if len(st)<2:return None
            a=st.pop();st[-1]=(st[-1]+a)&0xff
        elif b==0xa0:
            return st.pop() if len(st)==1 else None
        else:return None
    return None


# ----------------------------------------------------------------------------------
# Typed fixtures
# ----------------------------------------------------------------------------------
SIGN_VALUES=(0x00,0x01,0x7f,0x80,0x81,0xff)
PLAYER_X=((0x200,0x300),(0x10,0x200),(0x200,0x10),(0x10,0x20))        # (x0, x1) -> D4.W = 0000 / ff00 / 00ff / ffff after the two SLT of e92e6 (thresholds WORD 10de46 = a0)
PLAYER_Y=((0x200,0x300),(0x10,0x200),(0x200,0x10),(0x10,0x20))        # (y0, y1) -> D5.W patterns with the threshold WORD 10de48 = 80 (y relative = y - 100)


def define_typed(program):
    CUSTOM.clear()
    banks=find_bank_streams(program);G['bank_streams']=banks
    A=cust
    # ------------------------------------------------------------------ stream end / null / F3b boundary
    A('stream-null','core',setup=[W(NODE+0x76,4,0,'declared 76(A6) := 0 (no stream)')],note='e9194: D7 = 0 -> RTS without a bank restore (no port write)')
    for b in (0x10,0x11,0x3f,0x7f,0x80,0xff):
        A('stream-terminator-%02x'%b,'core',setup=op_stream([b,0]),note='first BYTE %02x >= 10: e91c6 stores the pointer, restores the PVC bank (3 port writes) and returns; the pointer does not advance'%b)
    A('stream-terminator-bank3','core',setup=op_stream([0x10,0]),bank=3,note='terminator with the initial PVC bank 3: the three restore writes 0 -> 100010, 1000 -> 2ffff2, 0 -> 2ffff0 select the bank 2 window')
    A('stream-null-bank3','core',setup=[W(NODE+0x76,4,0,'declared 76(A6) := 0')],bank=3,note='null stream with the initial bank 3: no restore, the bank stays 3')
    for b in range(8,16):
        A('stream-f3b-boundary-%02x'%b,'boundary',setup=op_stream([b,0,0,0]),expect_end=F3B_ENTRY,note='first BYTE %02x in 08..0f: BSR e94fe at e91ac -> the F3b entry is a stop (never executed)'%b)
    A('stream-op07-then-f3b','boundary',setup=op_stream([7,2,0x0a,0]),expect_end=F3B_ENTRY,note='op07 then BYTE 0a: the loop returns to e9198 and reaches the F3b entry in the second iteration')
    for bank_ in (2,3):
        d=banks['b%d'%bank_]
        A('stream-banked-op07-b%d'%bank_,'bank',setup=[stream_ptr(0x200000+d['op07'])],bank=bank_,note='stream pointer in the banked window (physical %x + %x): op07 chain read through the modeled bank (ordered bank reads)'%(0x100000*bank_,d['op07']))
        A('stream-banked-terminator-b%d'%bank_,'bank',setup=[stream_ptr(0x200000+d['term'])],bank=bank_,note='stream pointer in the banked window: terminator read through the bank')
        A('stream-banked-f3b-b%d'%bank_,'bank',setup=[stream_ptr(0x200000+d['f3b'])],bank=bank_,expect_end=F3B_ENTRY,note='stream pointer in the banked window: an opcode 08..0f BYTE reaches the F3b stop')
    A('stream-fixed-rom','bank',setup=[stream_ptr(0xf72a0)],note='the natural stream of the recorded seed in fixed ROM (BYTE 00 wait)')
    # ------------------------------------------------------------------ opcode 00 / 01 waits
    for cur,lim in ((0,1),(1,1),(2,1),(0,0),(0xffff,0x8000),(0x7fff,0x8000),(0x8000,0x7fff),(0x8000,0x8000),(5,0xffff)):
        A('op00-cur%04x-lim%04x'%(cur,lim),'op',setup=op_stream([0,4,lim>>8,lim&0xff,7,2,0x10],[W(0x10d418,2,cur,'declared scroll WORD 10d418 := %04x'%cur)]),meta=dict(op=0,cur=cur,lim=lim),
            note='op00 wait: BCC (unsigned) cur %04x >= lim %04x -> %s'%(cur,lim,'advance (e9768)' if cur>=lim else '81(A6) := ff, frame end'))
    for cur,v2,v4 in ((0,5,2),(5,5,2),(9,5,2),(0xffff,0xffff,0),(0x8000,0x7fff,0x8001),(9,0,0xffff)):
        A('op01-cur%04x-v2%04x-v4%04x'%(cur,v2,v4),'op',setup=op_stream([1,6,v2>>8,v2&0xff,v4>>8,v4&0xff,0x10],[W(0x10d418,2,cur,'declared scroll WORD 10d418 := %04x'%cur),W(NODE+0x80,1,0x55,'declared saturating counter BYTE 80(A6) := 55')]),
            meta=dict(op=1,cur=cur,v2=v2,v4=v4),note='op01: same wait; on pass CLR.B 80(A6), 1a93e(D0 = 0) clears WORD 10d44c, 1a910(D1 = %04x, D0 = D1 - %04x) writes 10d442 / 10d440'%(v2,v4))
    A('op01-preset-d44c','op',setup=op_stream([1,6,0,1,0,0,0x10],[W(0x10d418,2,5,'declared scroll WORD 10d418 := 5'),W(0x10d44c,2,0x1234,'declared WORD 10d44c := 1234')]),note='op01 pass clears a non-zero WORD 10d44c (1a94c)')
    # ------------------------------------------------------------------ opcode 02 .. 04 (1a910 / 1a93e)
    for v in (0,1,0x7fff,0x8000,0xffff):
        A('op02-%04x'%v,'op',setup=op_stream([2,4,v>>8,v&0xff,0x10]),meta=dict(op=2,v=v),note='op02: D0 = D1 = WORD 2(op) -> 1a910 -> WORD 10d442 / 10d440')
        A('op04-%04x'%v,'op',setup=op_stream([4,4,v>>8,v&0xff,0x10]),meta=dict(op=4,v=v),note='op04: D0 = WORD 2(op), D1 = ffff -> 1a910')
    for pre in (0,0x1234):
        A('op03-d44c-%04x'%pre,'op',setup=op_stream([3,2,0x10],[W(0x10d44c,2,pre,'declared WORD 10d44c := %04x'%pre)]),meta=dict(op=3,pre=pre),note='op03: D0 = ff -> 1a93e takes 1a944: WORD 10d44c := 0200')
    # ------------------------------------------------------------------ opcode 05 (expression) shape
    A('op05-false-offset-pos','op',setup=op_stream(expr_stream([0x97])),note='op05 false: A0 += sext(WORD 2(op)) = L + 2 (skips the op07), 81(A6) := ff')
    A('op05-true','op',setup=op_stream(expr_stream([0x96])),note='op05 true: advance by the length BYTE, then op07 clears 80(A6)')
    A('op05-false-offset-neg','op',setup=op_stream([0x10,0,0,0,5,6,0xff,0xfc,0x97,0xa0,0x10],[stream_ptr(SCR+4)]),note='op05 false with a negative WORD offset (fffc): A0 moves backwards to the terminator (sign extension of the WORD)')
    A('op05-false-offset-zero','op',setup=op_stream([5,6,0,0,0x97,0xa0,0x10]),note='op05 false with offset 0: A0 unchanged, 81(A6) := ff; the loop ends on the flag')
    # ------------------------------------------------------------------ opcode 06 (counter)
    for cnt,v2 in ((0,5),(1,5),(2,5),(3,5),(0xffff,5),(0,0),(0,0xffff)):
        A('op06-cnt%04x-v%04x'%(cnt,v2),'op',setup=op_stream([6,4,v2>>8,v2&0xff,0x10],[W(NODE+0x7e,2,cnt,'declared counter WORD 7e(A6) := %04x'%cnt)]),meta=dict(op=6,cnt=cnt,v2=v2),
            note='op06: 7e(A6) = %04x: %s'%(cnt,'set to WORD 2(op) and end the frame' if cnt==0 else 'SUBQ.W #1: zero -> advance, else frame end'))
    # ------------------------------------------------------------------ opcode 07 and lengths
    A('op07-len2','op',setup=op_stream([7,2,0x10]),note='op07: CLR.B 80(A6), advance by the length BYTE 2')
    A('op07-len20','op',setup=op_stream([7,0x20]+[0]*30+[0x10]),note='op07 with the length BYTE 20 (advance 32 bytes, LEA (A0,D0.W))')
    A('op07-len-ff','op',setup=op_stream([7,0xff]+[0]*253+[0x10]),note='op07 with the length BYTE ff (D0.W = 00ff: no sign extension)')
    A('chain-ops','op',setup=op_stream([2,4,0,1,3,2,4,4,0,2,6,4,0,3,7,2,0x10],[W(NODE+0x7e,2,1,'declared counter WORD 7e(A6) := 1')]),note='op02 op03 op04 op06 (counter 1 -> 0 advance) op07 then the terminator: six dispatches through e91ba in one frame')
    A('chain-wait-stops','op',setup=op_stream([7,2,0,4,0xff,0xff,7,2,0x10],[W(0x10d418,2,3,'declared scroll WORD 10d418 := 3')]),note='op07 then op00 with limit ffff (cur 3 < ffff): 81(A6) := ff ends the frame before the second op07')
    A('op-len0-loop','guard',setup=op_stream([7,0,0x10]),expect_guard=dict(problem='step_limit'),step_limit=40000,note='op07 with the length BYTE 0: A0 never advances, e9198 repeats forever (no terminator; the machine rolls back at its block budget)')
    A('op-odd-length-then-word','guard',setup=op_stream([7,3,0,0,4,0,0,0x10]),expect_guard=dict(problem='unsupported_odd_data_access'),note='op07 with an odd length: the next op00 at an odd address reads WORD 2(op) at an odd address (address error on the original CPU)')
    A('op-odd-length-then-byte-ops','op',setup=op_stream([7,3,0,7,2,0x10]),note='op07 with an odd length followed by op07 at an odd address: BYTE reads at odd addresses are allowed, the stream stays aligned for BYTE accesses only')
    # ------------------------------------------------------------------ evaluator: literals, class counters, constants
    # NOTE: e9176 runs e9204 first, which clears and recomputes 10de30..45 from the node list / the players; the class operators therefore read values produced by the declared list / player / screen / input states.
    def pushv(v):
        if v<0x80:return [v]
        if v==0xff:return [0x96]
        return [0x7f,v-0x7f,0xa1]                                              # values >= 80 are not literals (an operator byte): 7f + (v - 7f)
    def ev(label,expr,setup=(),group='eval',note='',n80=None,**kw):
        pre=list(setup)
        if n80 is not None:pre.append(W(NODE+0x80,1,n80,'declared saturating counter BYTE 80(A6) := %02x'%n80))
        A(label,group,setup=op_stream(expr_stream(expr),pre),meta=dict(kind='eval',expr=list(expr),n80=n80),note=note,**kw)
    def screen_state(xi,yi):return player_setup(3,(PLAYER_X[xi][0],0x100+PLAYER_Y[yi][0]),(PLAYER_X[xi][1],0x100+PLAYER_Y[yi][1]))
    for v in (0,1,0x7f):
        ev('eval-literal-%02x'%v,[v],note='operator byte %02x < 80 is a literal push'%v)
    for k in list(range(0,12))+list(range(13,22)):
        if k<12:states=[('base',[]),('n2',chain_nodes([k,k]))]
        elif k in (13,14):states=[('mask0',player_setup(0)),('mask1',player_setup(1,(0x40,0x120))),('mask3',player_setup(3,(0x40,0x120),(0x180,0x1a0)))]
        elif k==15:states=[('input0',[]),('input1',input_setup(0,3)),('input2',input_setup(0,3)+input_setup(1,5))]
        else:
            f=k-16;st_on=next((xi,yi) for xi in range(4) for yi in range(4) if screen_expect(xi,yi)[f]==0xff);st_off=next((xi,yi) for xi in range(4) for yi in range(4) if screen_expect(xi,yi)[f]==0)
            states=[('on',screen_state(*st_on)),('off',screen_state(*st_off))]
        for name,setup in states:
            ev('eval-class-%02x-%s'%(0x80+k,name),[0x80+k],setup=setup,note='operator %02x pushes BYTE 10de%02x (the value e9204 / e9298 computed for the declared state %s)'%(0x80+k,0x30+k,name))
    for label,classes in (('zero',[]),('sum',[0,3,3,7]),('upper-ignored',[8,9,11,12]),('eight-classes',[0,1,2,3,4,5,6,7,0,1])):
        ev('eval-8c-sum-%s'%label,[0x8c],setup=chain_nodes(classes),note='operator 8c: BSR e932c refreshes BYTE 10de3c (sum of the BYTES 10de30..10de37) and pushes it; list classes %s'%classes)
    for label,expr in (('96-ff',[0x96]),('97-00',[0x97])):
        ev('eval-%s'%label,expr,note='constant push')
    for n in (0,1,0x80,0xff):
        ev('eval-98-n80-%02x'%n,[0x98],n80=n,note='operator 98 pushes BYTE 80(A6) = %02x'%n)
    # ------------------------------------------------------------------ evaluator: comparisons (99..9d), logic (9e 9f), add (a1) with the sign boundary values
    def pair(opb,name,x,y):
        ev('eval-%02x-%s-%02x-%02x'%(opb,name,x,y),pushv(x)+pushv(y)+[opb],note='push %02x, push %02x, operator %02x (%s): a = %02x (popped), b = %02x (top)'%(x,y,opb,name,y,x))
    for opb,name in ((0x99,'eq'),(0x9a,'gt'),(0x9b,'ge'),(0x9c,'lt'),(0x9d,'le')):
        for x in SIGN_VALUES:
            for y in SIGN_VALUES:pair(opb,name,x,y)
    for opb,name in ((0x9e,'and'),(0x9f,'or')):
        for x in (0,1,0x80,0xff):
            for y in (0,1,0x80,0xff):pair(opb,name,x,y)
    for x,y in ((0,0),(1,0xff),(0x7f,1),(0x80,0x80),(0xff,0xff),(0x12,0x34),(0x40,0x40)):pair(0xa1,'add',x,y)
    ev('eval-deep-8-and-chain',[1,2,3,4,5,6,7,8,0x9e,0x9e,0x9e,0x9e,0x9e,0x9e,0x9e],note='eight pushes then seven AND operators: the BYTE stack grows 8 slots (A7 - 2 each) and shrinks back')
    ev('eval-deep-mixed',[0x80,0x81,0x82,0x99,0x9e,0x83,0x9f,0x96,0x9a,0x84,0xa1],setup=chain_nodes([0,1,1,2,2,2,3,4,4]),note='mixed class / compare / logic / add operators with several stack depths')
    # ------------------------------------------------------------------ evaluator: table-external operator bytes a2..ff (computed PC beyond the 34-slot table, no range check)
    reach={r['op']:r for r in static_checks(program)['e97e0_reach']}
    for opb in range(0xa2,0x100):
        r=reach[opb]
        if r['cls']=='block-start':
            ev('eval-oob-%02x-block-start-%x'%(opb,r['target']),[1,2,opb] if opb in (0xae,0xb3,0xb8,0xbd) else [opb],group='eval-oob',note='operator %02x: computed PC %x = e97e4 + 4*(%02x - 80) is a block start: executed as the original code does'%(opb,r['target'],opb))
        else:
            ev('eval-oob-%02x-%s-%x'%(opb,r['cls'],r['target']),[opb],group='eval-oob',expect_guard=dict(problem='unsupported_code_target',target=r['target'],refused_before_jump=True),
                note='operator %02x: computed PC %x (%s) is not a block start: refused before the jump'%(opb,r['target'],r['cls']))
    # evaluator edge cases of the stack
    A('eval-unbalanced-underflow','eval-unbalanced',setup=op_stream(expr_stream([])),expect_guard=dict(problem='unsupported_code_target',target=0x94c0000e),meta=dict(kind='unbalanced'),
        note='expression a0 with an empty stack: pops the high BYTE of the return LONG e94c0 (00), RTS pops 94c0 000e (fetch from an unmapped address)')
    A('eval-unbalanced-extra-push','eval-unbalanced',setup=op_stream(expr_stream([0x96])[:0]+bytes([5,7,0,9,0x96,0x96,0xa0,0x10])),expect_guard=dict(problem='unsupported_code_target'),meta=dict(kind='unbalanced'),
        note='expression 96 96 a0: one value stays on the stack, RTS pops [ff, stale BYTE][000e] (fetch from an unmapped address)')
    # ------------------------------------------------------------------ evaluator return R (decision 3): direct entry at e97c8 with a planted return LONG
    a7=SPD-0x20
    def rplant(label,R,val,second=FRAME_RET,note='',**kw):
        A(label,'eval-return',entry=EVAL_ENTRY,regs=dict(a1=SCR2,a0=SCR),a7=a7,stack_ret=False,stack_extra=[(a7,R.to_bytes(4,'big')),(a7+4,second.to_bytes(4,'big'))],
            setup=wbytes(SCR2,bytes([val,0xa0]),'declared expression')+wbytes(SCR,bytes([5,6,0,8,0x97,0xa0,0x10,0]),'declared op05 bytes at A0'),note=note,meta=dict(kind='rplant',R=R,val=val),**kw)
    for R,end_true,end_false,name in ((0xe94c0,None,None,'e94c0'),(0xe9396,0xe9428,0xe939a,'e9396'),(0xe939e,0xe9428,0xe93a2,'e939e'),(0xe96b0,0xe96b8,0xe96b4,'e96b0')):
        rplant('eval-return-%s-z1'%name,R,0x97,expect_end=end_true if end_true else FRAME_RET,note='R = %x (decision 3): D0.B = 0 (Z = 1): %s'%(R,'the BEQ.W taken / BNE.W not taken (bundled branch evaluated in the e98ea block)'))
        rplant('eval-return-%s-z0'%name,R,0x96,expect_end=end_false if end_false else FRAME_RET,note='R = %x (decision 3): D0.B = ff (Z = 0)'%R)
    rplant('eval-return-e9768-z0',0xe9768,0x96,note='R = e9768 (a F3a block start that is not one of the four known callers): PC := R, no branch evaluated')
    rplant('eval-return-e94c4-z1',0xe94c4,0x97,note='R = e94c4 (the BNE.W fall-through block start): PC := R')
    rplant('eval-return-e94fe',0xe94fe,0x97,expect_end=F3B_ENTRY,note='R = e94fe (the F3b entry): PC := R is a stop')
    rplant('eval-return-interior-e94c8',0xe94c8,0x97,expect_guard=dict(problem='unsupported_code_target',target=0xe94c8,refused_before_execution=True),note='R = e94c8 (an instruction start inside a block): refused (unsupported animation stage event PC)')
    rplant('eval-return-garbage',0x01234568,0x97,expect_guard=dict(problem='unsupported_code_target',target=0x1234568),note='R = 01234568: outside every routed range')
    rplant('eval-return-odd',0xe94c1,0x97,expect_guard=dict(problem='unsupported_code_target',target=0xe94c1,odd_pc=True),note='R = e94c1 (odd): address error on the original CPU')
    # ------------------------------------------------------------------ e9204 list walk / class counters
    A('walk-classes-all','walk',setup=op_stream([0x10],chain_nodes(list(range(12)))),meta=dict(kind='walk',classes=list(range(12))),note='fake list: one node of every class 0..b (BYTE 6b < 0c): each counter 10de30..3b = 1')
    A('walk-classes-skip','walk',setup=op_stream([0x10],chain_nodes([0,0xc,0xff,5,0xb,0x80])),meta=dict(kind='walk',classes=[0,0xc,0xff,5,0xb,0x80]),note='classes >= 0c (BCC unsigned) are not counted')
    for n in (255,256,257):
        A('walk-counter-wrap-%d-nodes'%n,'walk',setup=op_stream([0x10],dense_chain([2]*n)),meta=dict(kind='walk',classes=[2]*n),note='%d nodes of class 2 (dense list at 105da0, stride 14): ADDQ.B #1 on the BYTE counter 10de32 wraps (no saturation): %d'%(n,n&0xff))
    A('walk-many-same','walk',setup=op_stream([0x10],chain_nodes([4]*9)),meta=dict(kind='walk',classes=[4]*9),note='nine nodes of class 4')
    A('walk-circular','guard',setup=op_stream([0x10],[W(NODE+8,4,SCRN,'declared link 8(100bf4) := scratch node'),W(SCRN+8,4,SCRN,'declared self link'),W(SCRN+0x10,2,1,'declared depth 1'),W(SCRN+0x6b,1,1,'declared class 1')]),
        expect_guard=dict(problem='step_limit'),step_limit=40000,note='list walk over a node linked to itself with depth <> 0: e921c .. e9234 never terminates (the original has no bound)')
    A('walk-odd-link','guard',setup=op_stream([0x10],[W(NODE+8,4,SCRN+1,'declared link 8(100bf4) := odd address')]),expect_guard=dict(problem='unsupported_odd_data_access'),note='odd list link: TST.W 10(A1) reads an odd address')
    # ------------------------------------------------------------------ players: 49392 carry (10d68e bit p), 48502 rectangle, e9298 screen flags, 4d7a6 input
    for mask in (0,1,2,3):
        A('players-mask%d'%mask,'player',setup=op_stream([0x10],player_setup(mask,(0x40,0x120),(0x180,0x1a0))),meta=dict(kind='players',mask=mask),note='10d68e = %02x: 49392 returns C = bit p (e9248 / e9258), 48502 chooses the rectangle'%mask)
    for xi,(x0,x1) in enumerate(PLAYER_X):
        for yi,(y0,y1) in enumerate(PLAYER_Y):
            A('screen-x%d-y%d'%(xi,yi),'screen',setup=op_stream([0x10],player_setup(3,(x0,0x100+y0),(x1,0x100+y1))),meta=dict(kind='screen',xi=xi,yi=yi),
                note='both players: x0 = %03x x1 = %03x (D4.W pattern %d), y0 = %03x y1 = %03x (D5.W pattern %d): the SLT / SEQ / SCS / SCC flags 10de40..45'%(x0,x1,xi,y0,y1,yi))
    A('screen-thresholds-neg','screen',setup=op_stream([0x10],player_setup(3,(0x10,0x110),(0x20,0x120))+[W(0x10de46,2,0x8000,'declared threshold WORD 10de46 := 8000'),W(0x10de48,2,0x7fff,'declared threshold WORD 10de48 := 7fff')]),note='negative signed threshold: SLT is a signed word compare')
    A('screen-one-player-p0','screen',setup=op_stream([0x10],player_setup(1,(0x10,0x110))),meta=dict(kind='screen',mask=1),note='only player 0: the rectangle is its position twice (48502: D2 = D0, D3 = D1)')
    A('screen-one-player-p1','screen',setup=op_stream([0x10],player_setup(2,None,(0x10,0x110))),meta=dict(kind='screen',mask=2),note='only player 1: 4853a -> 48556 (D0 = D2, D1 = D3)')
    for i0 in (0,1):
        for i1 in (0,1):
            A('input-p0-%d-p1-%d'%(i0,i1),'input',setup=op_stream([0x10],(input_setup(0,3) if i0 else [])+(input_setup(1,5) if i1 else [])),meta=dict(kind='input',i0=i0,i1=i1),note='4d7a6 for D0 = 0 / 1 returns D0.B = BYTE 27(A4) when the player object callback is not 270e (289e: C = 1) and the state WORD is non-zero: e9280 / e9292 count them')
    A('input-trap-index-zero','guard',setup=op_stream([0x10],input_setup(0,0)),expect_guard=dict(problem='unsupported_TRAP'),note='4d7a6: BYTE 27(A4) = 0 -> TRAP #15 at 4d7f0 (outside F3a; the black box refuses it)')
    A('input-cb-is-270e','input',setup=op_stream([0x10],[W(0x10dcba,2,1,'declared state WORD := 1'),W(0x100cb8,4,0x270e,'declared player 0 object callback LONG := 270e')]),note='state WORD set but the player object callback is 270e: 289e C = 0, the zero-input path 4d7d0')
    A('input-state-zero','input',setup=op_stream([0x10],[W(0x100cb8,4,0x123456,'declared player 0 object callback LONG := 123456'),W(0x10dcba,2,0,'declared state WORD := 0')]),note='callback not 270e but the state WORD is zero: the zero-input path 4d7d0')
    # ------------------------------------------------------------------ direct entries (a declared return LONG 2ac2 at A7 = 1feffc): helpers, the loop re-entry after the F3b return, zero-step
    A('direct-e91b0-after-f3b-return','direct',entry=0xe91b0,regs=dict(a0=SCR),setup=op_stream([7,2,0x10]),note='e91b0 is the first block after the BSR e94fe returns (the F3b unit is not run): MOVE.L A0,D7 / store 76(A6) / back to the loop e9198 -> op07 -> terminator')
    for d0 in (0,1,0x80,0xff,0x100):
        A('direct-1a93e-d0-%02x'%d0,'direct',entry=0x1a93e,regs=dict(d0=d0),note='1a93e: TST.B D0 (low BYTE %02x): %s'%(d0&0xff,'zero -> 1a94c CLR.W 10d44c' if d0&0xff==0 else 'non-zero -> 1a944 WORD 10d44c := 0200'))
    A('direct-1a910','direct',entry=0x1a910,regs=dict(d0=0x1234abcd,d1=0x55556789),note='1a910: WORD 10d442 := D0.W, WORD 10d440 := D1.W (the upper words are ignored)')
    for mask in (0,1,2,3):
        A('direct-48502-mask%d'%mask,'direct',entry=0x48502,setup=player_setup(mask,(0x11,0x22),(0x33,0x44)),note='48502 direct: rectangle D0..D3 and D7 for the presence mask %d'%mask)
    A('direct-e932c-sum','direct',entry=0xe932c,regs=dict(a0=0x12345678,d0=0xabcd),setup=class_bytes(c0=3,c4=4,c7=5),note='e932c: pushes A0 (LONG) and D0.W, sums the BYTES 10de30..10de37 into 10de3c, pops both back (live stack)')
    A('direct-e9298','direct',entry=0xe9298,setup=player_setup(3,(0x10,0x110),(0x20,0x120)),note='e9298 direct (the screen flag block)')
    A('direct-e9768-advance','direct',entry=0xe9768,regs=dict(a0=SCR),setup=wbytes(SCR,bytes([7,0x12,0,0]),'declared op bytes'),note='e9768: A0 += BYTE 1(A0) (LEA (A0,D0.W), D0.W = 0012)')
    A('zero-step-e9176','zero',entry=0xe9176,first_stop=0xe9176,a7_stop=('abs',SPD-4),note='declared stop PC = entry PC: nothing executes (zero-step)')
    A('zero-step-e97c8','zero',entry=EVAL_ENTRY,first_stop=EVAL_ENTRY,a7_stop=('abs',SPD-4),note='declared stop PC = entry PC at the evaluator entry: nothing executes')
    # e9150 variants: another node as A6 (the callback LONG of that node declared as e9150)
    for a6 in (NODE,0x100cb8,0x101020):
        insp=[(a6,4),(a6+0x3e,4),(a6+0x7e,2),(a6+0x80,1),(a6+0x81,1),(0x10de46,2),(0x10de48,2)]
        A('e9150-node-%x'%a6,'e9150',base='e9150',regs=dict(a6=a6),setup=[W(a6,4,0xe9150,'declared callback LONG (%x) := e9150'%a6)] if a6!=NODE else [],meta=dict(kind='e9150',a6=a6,inspect=insp),
            note='e9150 on node %x: 3e(A6) := 10d38e, CLR.W 7e, CLR.B 80 / 81, WORD 10de46 := a0, WORD 10de48 := 80, callback LONG (A6) := e9176, then e9176 runs in the same execution'%a6)
    A('e9150-bank3','e9150',base='e9150',bank=3,note='e9150 with the initial PVC bank 3 (no port write, the bank stays 3)')
    # ------------------------------------------------------------------ carry consumers entered directly with a declared SR (both outcomes) and F3b entries reached by a planted return LONG / a callback install
    for sr in (0x2000,0x2001):
        A('carry-e9248-sr%04x'%sr,'carry',entry=0xe9248,sr=sr,note='e9248 BCC.W entered directly with the declared SR %04x (C = %d): the carry produced by 49392 in the original flow'%(sr,sr&1),meta=dict(kind='carry',pc=0xe9248,sr=sr))
        A('carry-e9258-sr%04x'%sr,'carry',entry=0xe9258,sr=sr,note='e9258 BCC.W entered directly with the declared SR %04x (C = %d)'%(sr,sr&1),meta=dict(kind='carry',pc=0xe9258,sr=sr))
    for R in F3B_BOUNDARY_PCS:
        rplant('f3b-return-%x-undeclared'%R,R,0x97,expect_guard=dict(problem='unsupported_code_target',target=R),
            note='R = %x (a F3b %s) reached without the declared stop: refused, never executed (the F3b executor would own it)'%(R,'TRAP #15 site' if R in (0xe93d8,0xe9528,0xe9530,0xe957a,0xe96d4,0xe9702,0xe9780,0xe9788) else 'callback entry'))
        rplant('f3b-return-%x-declared-stop'%R,R,0x97,expect_end=R,first_stop=R,note='R = %x declared as the stop: the evaluator return stops directly after the RTS of e98ea (the F3b PC is never executed)'%R)
    for cbk in (0xe9350,0xe9362):
        A('node-callback-%x-undeclared'%cbk,'f3b-callback',setup=[W(NODE,4,cbk,'declared callback LONG (A6) := %x'%cbk)],expect_guard=dict(problem='unsupported_code_target',target=cbk),note='the dispatcher JSR (A0) enters the F3b child callback %x without a declared stop: refused'%cbk)
        A('node-callback-%x-declared-stop'%cbk,'f3b-callback',setup=[W(NODE,4,cbk,'declared callback LONG (A6) := %x'%cbk)],first_stop=cbk,expect_end=cbk,note='the dispatcher JSR (A0) enters the F3b child callback %x declared as the stop: a stop directly after the JSR (A0) at 2ac0'%cbk)
    # ------------------------------------------------------------------ guards
    A('guard-odd-a7-node','guard',a7=SPD+1,expect_guard=dict(problem='unsupported_odd_data_access'),note='A7 odd: the dispatcher JSR (A0) pushes an odd LONG')
    A('guard-odd-a6-node','guard',regs=dict(a6=NODE+1),expect_guard=dict(problem='unsupported_odd_data_access'),note='A6 odd: MOVEA.L (A6),A0 of the dispatcher reads an odd LONG')
    A('guard-rom-write-e9150','guard',entry=0xe9150,regs=dict(a6=0x2000),expect_guard=dict(problem='unmapped_or_protected'),note='e9150 with A6 in the program ROM: MOVE.L #10d38e,3e(A6) writes the ROM')
    A('guard-bank-window-write','guard',entry=0xe9150,regs=dict(a6=0x200000),expect_guard=dict(problem='unmapped_or_protected'),note='e9150 with A6 in the banked ROM window: the write is refused')
    A('guard-stack-below-ram','guard',a7=0x100018,setup=op_stream(expr_stream([1]*10)),expect_guard=dict(problem='unmapped_or_protected'),note='A7 near the start of the work RAM: the BYTE pushes of the evaluator run below 100000 (program ROM, write protected)')
    A('guard-stream-unmapped','guard',setup=[stream_ptr(0x500000)],expect_guard=dict(problem='unmapped_or_protected'),note='stream pointer in an unmapped region')
    A('guard-stream-device','guard',setup=[stream_ptr(0x3c0000)],expect_guard=dict(problem='unsupported_data_device'),note='stream pointer at the video port region: not a permitted read')
    A('guard-stream-pvc','guard',setup=[stream_ptr(0x2ffff0)],expect_guard=dict(problem='unsupported_PVC_read_or_write'),note='stream pointer at the PVC register page: a read is refused')
    A('guard-stream-odd-op00','guard',setup=op_stream([0,4,0,5,0x10],[stream_ptr(SCR+1)]),expect_guard=dict(problem='unsupported_odd_data_access'),note='stream pointer odd, first BYTE 00 at an odd address (read as BYTE 00 of the shifted stream): WORD 2(op) odd')


# ----------------------------------------------------------------------------------
# Condition processing (typed fixtures and natural nodes)
# ----------------------------------------------------------------------------------
def fx_summary(fx):
    meta={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')}
    meta['initial_regs']=fx['regs'];meta['initial_RAM_sha256']=sha(fx['ram']);meta['initial_PVC_sha256']=sha(fx['pvc'])
    return json.loads(json.dumps(meta,default=lambda x:list(x) if isinstance(x,tuple) else str(x)))


def step_summary(spec):
    return [dict(label=s['label'],stop_pc=s['stop_pc'],checkpoints=s['checkpoints'],a7_expectation=list(s['a7']) if s['a7'] is not None else None,declared_changes=s['changes'],
        boundary_stop_pcs=list(s.get('alts',())),observed_end=s.get('observed_end')) for s in spec['steps']]


def condition_facts(spec,control):
    p=control[-1];ram=p['ram_after'];rb=p['ram_before'];o=p['outgoing']
    leads=[l['pc'] for q in control for l in q['leads']]
    f=dict(end=o['pc'],a7=o['a7'],leader_seq=leads,instructions=sum(len(q['pcs'])-1 for q in control),computed=[c for q in control for c in q['computed']],
        eval_false_path=0xe94c4 in leads,flags_10de30_48=ram[0xde30:0xde49].hex(),flags_before=rb[0xde30:0xde49].hex(),node_after=dict(p76=u32(ram,0xbf4+0x76),w7e=u16(ram,0xbf4+0x7e),b80=ram[0xbf4+0x80],b81=ram[0xbf4+0x81],p76_before=u32(rb,0xbf4+0x76),
        b80_before=rb[0xbf4+0x80],w7e_before=u16(rb,0xbf4+0x7e)),globals_after=dict(w10d442=u16(ram,0xd442),w10d440=u16(ram,0xd440),w10d44c=u16(ram,0xd44c),w10d418=u16(ram,0xd418),b10d68e=ram[0xd68e]),
        ports=[(e['address'],int(e['bytes'],16)) for q in control for e in q['events'] if e['region'] in PORT_REGIONS],guard=p['guard'],regs_after={k:o[k] for k in REG16},
        f3a_reads=sorted({(e['region']) for q in control for e in q['events'] if e['access']=='read' and e['region'] in ('fixed','bank') and in_f3a(e['pc'])}),
        bank_reads=sum(1 for q in control for e in q['events'] if e['region']=='bank'),modeled_bank=p['modeled_bank'],
        eval_byte_writes=[e['address'] for q in control for e in q['events'] if e['region']=='ram' and e['access']=='write' and e['size']==1 and EVAL_ENTRY<=e['pc']<0xe98ee],
        bank_restore_ram_write=[(e['address'],int(e['bytes'],16)) for q in control for e in q['events'] if e['region']=='ram' and e['access']=='write' and 0xe91c6<=e['pc']<=0xe91e2 and e['size']==2 and e['address']==0x100010])
    for addr,size in (spec_meta_inspect(spec) if spec else ()):
        f.setdefault('inspect',{})['%x/%d'%(addr,size)]=(int.from_bytes(bytes(rb[(addr+i)&0xffff] for i in range(size)),'big'),int.from_bytes(bytes(ram[(addr+i)&0xffff] for i in range(size)),'big'))
    return f


def spec_meta_inspect(spec):return (spec.get('meta') or {}).get('inspect',())


def process_item(program,number,spec):
    t0=time.time()
    split,control,d_split,d_control=run_spec(program,spec)
    dump=bool(spec.get('dump'))
    result=dict(index=number,label=spec['label'],group=spec['group'],note=spec.get('note',''),provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),meta=spec.get('meta'),
        fixture=fx_summary(spec['fixture']),steps=step_summary(spec),phases=store(split,files=False),continuous_control=store(control,files=dump),reproduced_twice=True,continuous_split_equivalent=True,
        phase_digests_split=d_split,phase_digests_control=d_control)
    models=[] if spec.get('guarded') or not spec.get('model',True) else model_conditions(program,spec,control)
    covered=set()
    for q in control:covered.update(q['pcs'])
    hits=collections.Counter(l['pc'] for q in control for l in q['leads'])
    facts=condition_facts(spec,control)
    p=control[-1]
    summary=dict(label=spec['label'],group=spec['group'],end_pc=hex(p['outgoing']['pc']),stop_kind=(p['stop_evidence'] or {}).get('kind') if p['guard'] is None else 'guard:%s'%p['guard'].get('problem'),instructions=facts['instructions'],split_phases=len(split),
        state_digest=state_digest_of(p),entry_digest=entry_digest_of(control[0]),ordered_ports_sha256=sha(ports_blob(p['events'])),
        control_phase_digest=d_control[-1],guard=p['guard'],reason=p['guard'].get('reason') if p['guard'] else None)
    return dict(number=number,result=result,models=models,covered=sorted(covered),hits=dict(hits),summary=summary,facts=facts,seconds=time.time()-t0,split_phases=len(split),control_phases=len(control),
        boundaries=[dict(kind=q['stop_evidence']['kind'],pc=q['outgoing']['pc']) for q in control if q['stop_evidence'] and q['stop_evidence']['kind'] in ('f3b-boundary','bundled-branch-boundary','zero-step')],
        computed=facts['computed'],kind='typed')


def run_typed(number):
    mk=CUSTOM[number];RUNS[0]=0
    try:
        spec=mk(G['program']);r=process_item(G['program'],number,spec);r['runs']=RUNS[0];return r
    except Exception as e:
        import traceback
        return dict(number=number,error=repr(e)[:800],trace=traceback.format_exc()[-3000:],kind='typed',label=mk.label)


# ---- natural nodes
def natural_fx(label,ram,regs,bank,prov):
    regs14={k:regs[k] for k in KEYS14};regs14['a5']=regs['a5']
    bk=tuple(bank)
    fx=sc.make_fx(label,ram,regs14,(bk,pvc_page_for(bk)),NODE_PC,regs['a7'],prov,(),(),role='recorded F3 node entry: PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd (F3 decision 10)')
    fx['group']='natural'
    return fx


def natural_node(case,frame,node,first_seen,dump_all):
    """One natural e9150 / e9176 node execution: entry state of the scheduler's declared frame pass, run to 2ac2 / e94fe on fresh CPUs (split and continuous, twice), independent model, comparison with the recorded digests."""
    program=G['program'];seq=node['seq'];key=(case,frame,seq);rec=G['rec_by_key'][key]
    label='nat-%03d-f%03d-s%02d'%(case,frame,seq)
    fx=natural_fx(label,node['entry_ram'],node['entry_regs'],node['entry_bank'],dict(kind='scheduler declared-pass node entry (seed %d frame %d seq %d cb %x)'%(case,frame,seq,node['cb']),record=key))
    step=step_of(label,[],FRAME_RET,('abs',SPD))
    spec=dict(label=label,group='natural',fixture=fx,steps=[step],provenance=fx['seed'],model=True,store='control')
    with_checkpoints(program,spec)
    split,control,d_split,d_control=run_spec(program,spec)
    models=model_conditions(program,spec,control)
    p=control[-1];assert p['guard'] is None,(label,p['guard'])
    end=p['outgoing']['pc'];ev=p['stop_evidence']
    entry_ok=entry_digest_of(control[0])==rec['entry']
    sd=state_digest_of(p)
    if end==FRAME_RET:state_ok=sd==rec['exit'];ports_ok=sched_ports_digest(p['events'])==rec['ports_sha'];assert ev['kind']=='return-dispatcher'
    else:
        assert end==F3B_ENTRY and ev['kind']=='f3b-boundary',(label,hex(end))
        state_ok=sd==rec.get('e94fe');ports_ok=sum(1 for e in p['events'] if e['region'] in PORT_REGIONS)==rec.get('e94fe_ports')
    leads=[l['pc'] for q in control for l in q['leads']];lead_set=sorted(set(leads))
    my_idx=[(c['pc'],c['index']) for q in control for c in q['computed']];pub_idx=[(a,b) for a,b in rec['idx'] if a in (MAIN_JSR,EVAL_JMP)]
    idx_ok=my_idx==pub_idx if end==FRAME_RET else pub_idx[:len(my_idx)]==my_idx
    pub_leads=set(rec['leaders'])&START_SET;my_leads=set(lead_set)&START_SET
    lead_ok=my_leads==pub_leads if end==FRAME_RET else my_leads<=pub_leads
    new=[pc for pc in lead_set if ('L',pc) not in first_seen]
    idx=[(c['pc'],c['index']) for q in control for c in q['computed']]
    new_idx=[i for i in idx if ('I',)+i not in first_seen]
    first_seen.update(('L',pc) for pc in lead_set);first_seen.update(('I',)+i for i in idx)
    dump=bool(dump_all or new or new_idx or end==F3B_ENTRY or (frame==0 and node['cb']==0xe9150))
    stored=store(control,files=dump) if dump else None
    row=dict(case=case,frame=frame,seq=seq,cb=node['cb'],end=end,entry=rec['entry'],state=sd,control_digest=d_control[-1],split_digest=sha(jdump(d_split)),entry_ok=entry_ok,state_ok=state_ok,ports_ok=ports_ok,idx_ok=idx_ok,lead_ok=lead_ok,
        model_equal=all(m['equal'] for m in models),instr=sum(len(q['pcs'])-1 for q in control),phases=len(split),leaders=len(leads),lead_set=lead_set,idx=idx,dump=dump,blobs=stored[-1]['artifacts'] if stored else None,
        model_segments=len(models),carry_evidence=[e for m in models for e in m.get('carry_evidence',())],bank_reads=sum(1 for e in p['events'] if e['region']=='bank'),ports=sum(1 for e in p['events'] if e['region'] in PORT_REGIONS),
        a7=p['outgoing']['a7'])
    return row,models


def run_natural(case):
    """One natural seed: the scheduler's SeedRun (declared frame passes, continuous, as it recorded them) with the f3_replay hook replaced by this tool's node run."""
    t0=time.time();n0=len(DISCREPANCIES);RUNS[0]=0
    try:
        sd=sched.SEEDS[case];snap,meta=sched.seed_snap(sd)
        rows=[];first_seen=set();dump_all=case in G['dump_seeds']
        def hook(self,node):
            if node['cb'] not in (0xe9150,0xe9176):return
            row,models=natural_node(case,self.frame,node,first_seen,dump_all)
            rows.append(row)
        def noop(self,node):pass
        sched.SeedRun.f3_replay=hook;sched.SeedRun.model_node=noop
        run=sched.SeedRun(sched.G['program'],sched.G['fixed'],sched.G['levels'],snap,'continuous',sched.FRAMES_BASE,heavy=True,sink=None).run()
        return dict(number=('natural',case),kind='natural',case=case,rows=rows,frames_done=run.frames_done,stop=run.stop,run_digest=run.digest.hexdigest(),family=sd['family'],bank=sd['bank'],
            discrepancies=DISCREPANCIES[n0:],seconds=time.time()-t0,runs=RUNS[0])
    except Exception as e:
        import traceback
        return dict(number=('natural',case),error=repr(e)[:800],trace=traceback.format_exc()[-3000:],kind='natural',case=case)


PROBE_CHUNKS=12


def probe_addresses():
    rows=[]
    for lo,hi in F3A_RANGES:
        for pc in range(lo,hi):
            rows.append((pc,'start-zero-step' if pc in START_SET else ('interior-even' if pc%2==0 else 'odd')))
    return rows


def run_probe(k):
    """Direct-entry probes at every address of the 7 ranges: block starts as a zero-step (stop PC = entry PC: nothing executes, state unchanged); every other address (428 interior even PCs, 562 odd addresses) must be refused before it executes.  Each probe runs twice."""
    t0=time.time();RUNS[0]=0
    try:
        addr=probe_addresses();mine=addr[k::PROBE_CHUNKS];rows=[]
        for pc,kind in mine:
            if kind=='odd':                                   # refused by the harness before emu_start: Unicorn aborts (SIGABRT) while translating some odd addresses, so an odd entry PC is never handed to the emulator
                rows.append(dict(pc=pc,kind=kind,guard='unsupported_code_target',reason='odd entry PC %x (an address error on the original CPU); refused by the harness before emu_start (Unicorn aborts while translating some odd addresses)'%pc,
                    refused_before_execution=True,harness_refusal=True,instructions=0,twice_equal=True));continue
            fx,prov=node_fixture('probe-%x'%pc,'e9176',None,SPD-4,None,None,pc,[(SPD-4,FRAME_RET.to_bytes(4,'big'))],'entry probe %s'%kind)
            stop=pc if kind=='start-zero-step' else FRAME_RET
            step=step_of('probe',[],stop,None)
            spec=dict(label=fx['label'],fixture=fx,steps=[step],guarded=kind!='start-zero-step',guard={},probe=True)
            ph1=run_chain(program_of(),spec,True);ph2=run_chain(program_of(),spec,True)
            a,b=ph1[-1],ph2[-1]
            same=(a['guard'],a['outgoing'],a['ram_after'],a['pcs'])==(b['guard'],b['outgoing'],b['ram_after'],b['pcs'])
            if kind=='start-zero-step':
                annotate(program_of(),ph1)
                rows.append(dict(pc=pc,kind=kind,guard=a['guard'] and a['guard'].get('problem'),instructions=len(a['pcs'])-1,state_unchanged=a['ram_after']==a['ram_before'] and {x:a['incoming'][x] for x in REG16+('pc',)}=={x:a['outgoing'][x] for x in REG16+('pc',)},
                    evidence=(a['stop_evidence'] or {}).get('kind'),twice_equal=same))
            else:
                g=a['guard'] or {}
                rows.append(dict(pc=pc,kind=kind,guard=g.get('problem'),reason=g.get('reason'),refused_before_execution=bool(g.get('refused_before_execution')) or bool(g.get('odd_pc')),instructions=len(a['pcs'])-1,twice_equal=same))
        return dict(number=('probe',k),kind='probe',rows=rows,seconds=time.time()-t0,runs=RUNS[0],discrepancies=[])
    except Exception as e:
        import traceback
        return dict(number=('probe',k),error=repr(e)[:800],trace=traceback.format_exc()[-3000:],kind='probe')


def program_of():return G['program']


def run_item(item):
    if item[0]=='natural':return run_natural(item[1])
    if item[0]=='probe':return run_probe(item[1])
    n0=len(DISCREPANCIES);r=run_typed(item[1])
    r['discrepancies']=DISCREPANCIES[n0:]
    return r


# ----------------------------------------------------------------------------------
# Stop-rule self tests: a stop is accepted only directly after the transferring instruction
# ----------------------------------------------------------------------------------
def stop_selftests(program):
    out=[]
    for stop,why in ((0xe91be,'RTS of a table handler popped the LONG pushed by JSR e91e4(PC,D7.W)'),(0xe918c,'RTS of the cleanup 43e34 popped the LONG pushed by JSR 43e34'),(0xe9198,'fall-through / BRA target e9198 (not an RTS)'),
            (0xe91c6,'BEQ.B fall-through (not an RTS)'),(0xe9764,'internal PC (never reached)')):
        fx,prov=node_fixture('selftest-stop-%x'%stop,'e9176',None,None,None,None,NODE_PC,(),'stop rule self test');fx['step_limit']=30000
        step=dict(label='st',changes=op_stream([7,2,0x10]),stop_pc=stop,checkpoints=[],a7=None,expect=None,alts=())
        spec=dict(label=fx['label'],fixture=fx,steps=[step],guarded=True,guard={},probe=True)
        try:phases=run_chain(program,spec,True)
        except AssertionError as e:
            out.append(dict(stop=hex(stop),why=why,not_reached=True,detail=repr(e)[:160],refused_as_return_stop=True));continue
        try:
            annotate(program,phases);accepted=True;detail=None
        except AssertionError as e:
            accepted=False;detail=repr(e)[:200]
        ev=phases[-1].get('stop_evidence')
        refused=(not accepted) or (ev is None) or ev['kind'] not in ('return','return-dispatcher')
        prev=phases[-1]['pcs'][-2] if len(phases[-1]['pcs'])>1 else None
        out.append(dict(stop=hex(stop),previous_pc=hex(prev) if prev is not None else None,previous_bytes=program[prev:prev+2].hex() if prev is not None else None,why=why,refused_as_return_stop=refused,detail=detail,evidence_kind=ev['kind'] if ev else None))
    assert all(x['refused_as_return_stop'] for x in out),out
    return out


# ----------------------------------------------------------------------------------
# Main, report
# ----------------------------------------------------------------------------------
def dump_seed_cases():
    """8 natural seeds with the full per-node dumps: one per (family, bank) group in case order (restricted to seeds with at least 50 recorded e9176 nodes), filled up to 8 with evenly spaced candidates."""
    counts=collections.Counter(r['case'] for r in G['records'] if r['cb']==0xe9176)
    cand=[c for c in sorted(sched.SEEDS) if sched.SEEDS[c]['kind']=='natural' and counts[c]>=50]
    chosen=[];seen=set()
    for c in cand:
        g=(sched.SEEDS[c]['family'],sched.SEEDS[c]['bank'])
        if g not in seen:seen.add(g);chosen.append(c)
    k=0
    while len(chosen)<8 and k<len(cand):
        c=cand[(k*len(cand))//8]
        if c not in chosen:chosen.append(c)
        k+=1
    return sorted(chosen[:8])


def main():
    global OUT,BLOBS,CONDDIR
    t_start=time.time()
    dev=os.environ.get('F3_DEV');workers=int(os.environ.get('F3_WORKERS','3'))
    out_dir=Path(os.environ['F3_OUT']) if os.environ.get('F3_OUT') else OUT
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
    G['program']=program;load_records();make_bases()
    sched.setup();sched.load_seeds();G['published']=json.loads(SEED_OBS.read_text())
    routing_sha=sha(sched.ROUTING_SRC.read_bytes());pub_routing=G['published']['inputs'].get('engine/src/animation_machine.cpp')
    if routing_sha!=pub_routing:
        DISCREPANCIES.append(dict(label='inputs',kind='routing-source-changed',detail='engine/src/animation_machine.cpp sha256 %s differs from the %s recorded by the scheduler observation: the SeedRun coverage flags (rA / rB) feed the run digest, regenerated run digests may differ from the published ones'%(routing_sha,pub_routing)))
    G['dump_seeds']=set(dump_seed_cases())
    define_typed(program)
    naturals=sorted(c for c in sched.SEEDS if sched.SEEDS[c]['kind']=='natural')
    assert len(naturals)==137
    items=[('natural',c) for c in naturals]+[('typed',i) for i in range(len(CUSTOM))]+[('probe',k) for k in range(PROBE_CHUNKS)]
    if dev:
        keep=[it for it in items if any((f=='natural' and it[0]=='natural') or (f=='typed' and it[0]=='typed') or (f=='probe' and it[0]=='probe') or (it[0]=='natural' and f=='n%d'%it[1]) or (it[0]=='typed' and f in CUSTOM[it[1]].label) for f in dev.split(','))]
    else:keep=items
    print('items',len(items),'selected',len(keep),'workers',workers,'typed',len(CUSTOM),'dump seeds',sorted(G['dump_seeds']),flush=True)
    input_paths={Path(__file__).resolve(),sched.ROUTING_SRC,rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SEED_OBS,SEED_FILE,sched.SEED_OBS,sched.F2_CONTRACT,sched.F3_CONTRACT,SCOPE,bc.CONTRACT,sc.CONTRACT,fh.CONTRACT,inp.CONTRACT,sp.CONTRACT}
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
                if (n+1)%25==0 or 'error' in r:print('%d/%d %.0fs%s'%(n+1,len(keep),time.time()-t_start,' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    else:
        for n,it in enumerate(keep):
            r=run_item(it);done[r['number']]=r
            print('%d/%d %s %.1fs%s'%(n+1,len(keep),it,r.get('seconds',0),' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    errors=[done[k] for k in done if 'error' in done[k]]
    if errors:
        for e in errors[:10]:print(e['number'],e['kind'],e['error'],'\n',e['trace'][-800:])
        raise SystemExit('%d work items failed'%len(errors))
    nat=[done[('natural',c)] for c in naturals if ('natural',c) in done]
    typed=[done[i] for i in range(len(CUSTOM)) if i in done]
    probes=[done[('probe',k)] for k in range(PROBE_CHUNKS) if ('probe',k) in done]
    return finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,nat,typed,static,t_start,ext,dev,probes)


def write_gz(path,obj):
    data=gzip.compress(jdump(obj)+b'\n',6,mtime=0);path.write_bytes(data);return sha(data),len(data)


def dir_size(path):
    return sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())


EVAL_EXPECT_TARGETS={**{0x80+k:0xe986c for k in range(0x16) if k!=0xc},0x8c:0xe9878,0x96:0xe9884,0x97:0xe988c,0x98:0xe9894,0x99:0xe989c,0x9a:0xe98a6,0x9b:0xe98b0,0x9c:0xe98ba,0x9d:0xe98c4,0x9e:0xe98ce,0x9f:0xe98d8,0xa0:0xe98ea,0xa1:0xe98e2}
CONTRACT_OOB_STARTS=(0xa2,0xa5,0xa6,0xa8,0xaa,0xac,0xae,0xb3,0xb8,0xbd)


def screen_expect(xi,yi):
    """Contract / byte expectation of the flags 10de40..45 for both players (mask 3) at the base camera: D0 = x0, D2 = x1, D1 = y0, D3 = y1 relative values, thresholds a0 / 80."""
    x0,x1=PLAYER_X[xi];y0,y1=PLAYER_Y[yi];t46,t48=0xa0,0x80
    def pat(a,b,t):return (0xff00 if a<t else 0)|(0xff if b<t else 0)
    out=[0]*6
    d4=pat(x0,x1,t46);d5=pat(y0,y1,t48)
    out[1]=0xff if d4==0 else 0
    if d4:
        out[0]=0xff if d4==0xffff else 0;out[2]=0 if d4==0xffff else 0xff
    out[4]=0xff if d5==0 else 0
    if d5:
        out[3]=0xff if d5==0xffff else 0;out[5]=0 if d5==0xffff else 0xff
    return out


def finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,nat,typed,static,t_start,ext,dev,probes):
    for r in nat+typed+probes:DISCREPANCIES.extend(r.get('discrepancies',[]))
    pub=G['published'];pubseed={s['case']:s for s in pub['seeds']}
    # ---------------- storage of the per-condition records and the natural node rows
    cond_files={}
    for r in typed:
        sh,sz=write_gz(CONDDIR/('c%04d.json.gz'%r['number']),dict(result=r['result'],models=r['models'],facts=r['facts']));cond_files[r['number']]=dict(file='conditions/c%04d.json.gz'%r['number'],sha256=sh,size=sz)
    rows=[row for r in nat for row in r['rows']]
    rows.sort(key=lambda x:(x['case'],x['frame'],x['seq']))
    nat_sha,nat_size=write_gz(out_dir/'natural_nodes.json.gz',dict(note='one row per natural e9150 / e9176 node execution (entry = recorded digest, state = scheduler-form state digest of the outgoing state, control_digest = digest of the complete native record)',rows=rows))
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    prows=sorted((row for r in probes for row in r['rows']),key=lambda x:x['pc'])
    pk=collections.Counter(x['kind'] for x in prows)
    probe_sum=dict(addresses=len(prows),by_kind=dict(pk),zero_step_ok=sum(1 for x in prows if x['kind']=='start-zero-step' and x['state_unchanged'] and x['instructions']==0 and x['evidence']=='zero-step' and x['guard'] is None),
        refused_ok=sum(1 for x in prows if x['kind']!='start-zero-step' and x['guard']=='unsupported_code_target' and x['instructions']<=0),twice_equal=sum(1 for x in prows if x['twice_equal']),
        refused_before_execution=sum(1 for x in prows if x['kind']=='interior-even' and x.get('refused_before_execution')),odd=sum(1 for x in prows if x['kind']=='odd' and x.get('refused_before_execution')))
    probe_file=write_gz(out_dir/'entry_probes.json.gz',dict(note='direct entries at every address of the 7 F3a ranges',rows=prows))
    probe_sum.update(file='entry_probes.json.gz',file_sha256=probe_file[0],file_size=probe_file[1])
    eng=(ROOT/'engine/src/animation_machine_cleanup.cpp')
    if eng.exists() and '43e04/43e34' in eng.read_text():
        DISCREPANCIES.append(dict(label='engine',kind='contract-vs-engine',claim='contract: 43e34 (cleanup LEA entry) and 43e38 are existing cleanup executors',
            evidence='engine/src/animation_machine_cleanup.cpp: "43e04/43e34 (LEA 2e(A6),A0 entries) stay unsupported"; the observer routes 43e34 as a black-box entry (LEA 2e(A6),A0 then the existing 43e38)'))
    # ---------------- natural summary
    keys=set((r['case'],r['frame'],r['seq']) for r in rows)
    rec_keys=set(k for k,r in G['rec_by_key'].items() if r['cb'] in (0xe9150,0xe9176))
    full_run=not dev
    seed_cmp=[]
    for r in nat:
        p=pubseed[r['case']]
        seed_cmp.append(dict(case=r['case'],family=r['family'],bank=r['bank'],frames_done=r['frames_done'],stop=r['stop']['reason'],run_digest_equal=r['run_digest']==p['run_digest'],frames_equal=r['frames_done']==p['frames_done'],
            stop_equal=json.loads(json.dumps(r['stop'],sort_keys=True,default=str))==json.loads(json.dumps(p['stop'],sort_keys=True,default=str)),nodes=len(r['rows'])))
    by_cb=collections.Counter(hex(x['cb']) for x in rows);by_end=collections.Counter((hex(x['cb']),hex(x['end'])) for x in rows)
    nat_hits=collections.Counter();idx_hist=collections.Counter()
    for x in rows:
        for pc in x['lead_set']:nat_hits[pc]+=1
        for pc,i in x['idx']:idx_hist[(pc,i)]+=1
    nat_summary=dict(nodes=len(rows),by_callback=dict(by_cb),by_callback_and_end={'%s/%s'%k:v for k,v in by_end.items()},entry_digest_equal_recorded=sum(1 for x in rows if x['entry_ok']),state_digest_equal_recorded=sum(1 for x in rows if x['state_ok']),
        ports_equal_recorded=sum(1 for x in rows if x['ports_ok']),computed_pc_equal_recorded=sum(1 for x in rows if x['idx_ok']),leader_sets_consistent_with_recorded=sum(1 for x in rows if x['lead_ok']),model_segments_equal=sum(1 for x in rows if x['model_equal']),node_keys_equal_recorded=keys==rec_keys if full_run else None,recorded_keys=len(rec_keys),
        dumped_nodes=sum(1 for x in rows if x['dump']),seeds=len(nat),seed_run_digest_equal_published=sum(1 for c in seed_cmp if c['run_digest_equal']),seed_frames_equal=sum(1 for c in seed_cmp if c['frames_equal']),seed_stop_equal=sum(1 for c in seed_cmp if c['stop_equal']),
        bank_reads=sum(x['bank_reads'] for x in rows),port_events=sum(x['ports'] for x in rows),instructions=sum(x['instr'] for x in rows),split_phases=sum(x['phases'] for x in rows),dump_seeds=sorted(G['dump_seeds']),
        computed_pc_index_histogram={'%x:%x'%k:v for k,v in sorted(idx_hist.items())},carry_evidence=sum(len(x['carry_evidence']) for x in rows),file='natural_nodes.json.gz',file_sha256=nat_sha,file_size=nat_size)
    for x in rows:
        if not (x['entry_ok'] and x['state_ok'] and x['ports_ok'] and x['model_equal'] and x['idx_ok'] and x['lead_ok']):DISCREPANCIES.append(dict(label='nat-%d-%d-%d'%(x['case'],x['frame'],x['seq']),kind='natural-node-mismatch',detail={k:x[k] for k in ('entry_ok','state_ok','ports_ok','model_equal','idx_ok','lead_ok')}))
    for c in seed_cmp:
        if not (c['run_digest_equal'] and c['frames_equal'] and c['stop_equal']):DISCREPANCIES.append(dict(label='seed-%d'%c['case'],kind='seed-regeneration-differs-from-published',detail=c))
    # ---------------- typed summaries and coverage
    models=[m for r in typed for m in r['models']]
    for m in models:
        if not m['equal']:DISCREPANCIES.append(dict(label=m['label'],kind='model-vs-native',detail=m.get('model_error') or m.get('mismatches')))
    typed_hits=collections.Counter();typed_groups=collections.defaultdict(collections.Counter);first_label={}
    for r in typed:
        for pc,n in r['hits'].items():typed_hits[pc]+=n;typed_groups[pc][r['result']['group']]+=1;first_label.setdefault(pc,r['result']['label'])
    start_cov={hex(pc):dict(natural_nodes=nat_hits.get(pc,0),typed_hits=typed_hits.get(pc,0),typed_conditions=sum(typed_groups[pc].values()),typed_groups=dict(typed_groups[pc]),first_typed_condition=first_label.get(pc),needs_typed_fixture=nat_hits.get(pc,0)==0) for pc in sorted(STARTS)}
    uncovered=[hex(pc) for pc in STARTS if not nat_hits.get(pc) and not typed_hits.get(pc)]
    need_fixture=[hex(pc) for pc in sorted(STARTS) if not nat_hits.get(pc)]
    lab={r['result']['label']:r for r in typed}
    group_counts=dict(collections.Counter(r['result']['group'] for r in typed))
    claims=contract_claims(program,typed,lab,rows,nat_summary,static,start_cov,idx_hist,seed_cmp,models,probe_sum) if (not dev or os.environ.get('F3_CLAIMS')) else []
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    guards=[dict(label=r['result']['label'],problem=r['summary']['guard']['problem'],reason=r['summary']['guard'].get('reason'),target=r['summary']['guard'].get('target'),refused_before_jump=r['summary']['guard'].get('refused_before_jump',False),
        refused_before_execution=r['summary']['guard'].get('refused_before_execution',False),odd_pc=r['summary']['guard'].get('odd_pc',False)) for r in typed if r['summary']['guard']]
    oob=[]
    for rr in static['e97e0_reach']:
        if rr['op']<0xa2:continue
        names=[l for l in lab if l.startswith('eval-oob-%02x-'%rr['op'])];r=lab[names[0]] if names else None
        oob.append(dict(op=rr['op'],target=rr['target'],cls=rr['cls'],condition=names[0] if names else None,executed=bool(r) and r['summary']['guard'] is None,end=r['summary']['end_pc'] if r else None,guard=(r['summary']['guard'] or {}).get('reason') if r else None))
    report=dict(schema_version=1,source=source,inputs=inputs,seed_inputs=dict(f3_node_seeds_sha256=G['seed_file_sha'],scheduler_observation_sha256=SEED_OBS_SHA,stage_entry_body_observation_sha256=sched.SEED_SHA,records=len(G['records'])),
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=TABLE),static_checks=static,generic_leader_rule_info=INFO,
        natural=nat_summary,natural_seeds=seed_cmp,entry_probes=probe_sum,conditions=[dict(number=r['number'],**r['summary'],file=cond_files[r['number']]) for r in typed],condition_count=len(typed),group_counts=group_counts,
        split_steps=sum(r['split_phases'] for r in typed),control_steps=sum(r['control_phases'] for r in typed),natural_split_phases=nat_summary['split_phases'],
        fresh_CPU_runs=sum(r.get('runs',0) for r in nat+typed+probes),model=dict(typed_segments=len(models),typed_equal=sum(1 for m in models if m['equal']),natural_segments=sum(x['model_segments'] for x in rows),natural_equal=sum(x['model_segments'] for x in rows if x['model_equal']),
            carry_evidence_total=sum(len(m.get('carry_evidence',())) for m in models)+nat_summary['carry_evidence']),
        contract_discrepancies=DISCREPANCIES,contract_claims=claims,block_start_coverage=start_cov,block_starts_covered=len(STARTS)-len(uncovered),block_starts_uncovered=uncovered,block_starts_need_typed_fixture=need_fixture,
        block_starts_natural=len(STARTS)-len(need_fixture),computed_pc=dict(e97e0_out_of_table=oob,natural_index_histogram=nat_summary['computed_pc_index_histogram']),guards=guards,boundary_stop_pcs=list(F3B_STOP_PCS),f3b_boundary_pcs=list(F3B_BOUNDARY_PCS),
        stop_rule_selftests=stop_selftests(program),bank_streams={k:{kk:hex(vv) for kk,vv in v.items()} for k,v in G['bank_streams'].items()},
        rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,
        Cpp_comparison_performed=False,oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),observer_extension=ext,limitations=LIMITATIONS,
        blobs=len(list(BLOBS.iterdir())),output_size_bytes=dir_size(out_dir),dev_filter=dev)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2,default=str,sort_keys=True)+'\n')
    report['output_size_bytes']=dir_size(out_dir)
    summary=dict(typed=len(typed),natural_nodes=len(rows),natural_ok=sum(1 for x in rows if x['entry_ok'] and x['state_ok'] and x['ports_ok'] and x['model_equal'] and x['idx_ok'] and x['lead_ok']),discrepancies=len(DISCREPANCIES),model_typed=report['model']['typed_segments'],
        model_typed_equal=report['model']['typed_equal'],block_starts_covered=report['block_starts_covered'],need_fixture=len(need_fixture),uncovered=uncovered,claims={v:sum(1 for c in claims if c['verdict']==v) for v in set(c['verdict'] for c in claims)},
        sha256=sha(path.read_bytes()),tool=tool_sha,size_mb=round(dir_size(out_dir)/1e6,1),seconds=round(time.time()-t_start))
    print(json.dumps(summary))
    return summary


def contract_claims(program,typed,lab,rows,nat,static,start_cov,idx_hist,seed_cmp,models,probe_sum):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    C=lambda ok:'confirmed' if ok else 'contradicted'
    def L(label):return lab[label]['facts']['leader_seq'] if label in lab else []
    def F(label):return lab[label]['facts']
    def M(r):return r['result']['meta'] or {}
    # ---- static
    claim('F3a: 7 code ranges = 1,124 bytes = 324 instructions (0 undecoded), every byte equal to the ROM; the model decoder lengths equal the disassembler',C(static['instructions_decoded']==324 and static['model_decoder_lengths_equal_disassembler'] and sum(h-l for l,h in F3A_RANGES)==1124),
        dict(instructions=static['instructions_decoded'],bytes=sum(h-l for l,h in F3A_RANGES),rows=[r['range'] for r in static['bytes']]))
    claim('even PCs of the ranges = 562, of which 134 block starts and 428 interior PCs',C(static['even_pcs']==562 and static['interior_pcs']==428 and static['block_starts']==134),dict(even=static['even_pcs'],interior=static['interior_pcs']))
    claim('the 134 block starts = the decoded leaders (generic rule without the bundled e94c0, plus the return address e91be of the computed JSR e91e4(PC,D7.W)), the 8 + 34 table slots and the callback entries e9150 / e9176',C(static['decoded_leaders_equal_contract']),
        dict(info=INFO))
    bad=[b for b in static['bundled_branches'] if not b['is_conditional_branch'] or b['is_block_start'] or not b['inside_range']]
    claim('the 22 bundled PCs are conditional branches inside the ranges that are not block starts',C(not bad),dict(checked=len(static['bundled_branches']),bad=bad))
    claim('the 60 carry-preserving (FLOW_ONLY) blocks are exactly the blocks whose instructions are all flow-only',C(static['flow_only_equal_contract']),dict(decoded_minus_contract=static['flow_only_decoded_minus_contract'],contract_minus_decoded=static['flow_only_contract_minus_decoded']))
    claim('exactly 2 blocks consume a carry produced outside the block (e9248, e9258: the BCC.W after JSR 49392); the only other flag consumed from outside a block is Z by the bundled BNE.W e94c0 (block e94b8, produced by the evaluator return, decision 3)',
        C(static['carry_consumers_equal'] and list(static['non_carry_consumers'])==['0xe94b8']),dict(carry=static['carry_consumers_computed'],non_carry=static['non_carry_consumers']))
    exp_main=['0xe9444','0xe9458','0xe948c','0xe949c','0xe94a8','0xe94b8','0xe94d0','0xe94f6']
    claim('the 8 slots of the main table e91e4 are BRA.W to the opcode handlers e9444 e9458 e948c e949c e94a8 e94b8 e94d0 e94f6',C([s['target'] for s in static['tables']['e91e4']]==exp_main),dict(targets=[s['target'] for s in static['tables']['e91e4']]))
    got={0x80+k:int(s['target'],16) for k,s in enumerate(static['tables']['e97e4'])}
    claim('the 34 slots of the evaluator table e97e4 (operators 80..a1) are BRA.W to e986c (class push, 80..8b 8d..95), e9878 (8c), e9884 (96), e988c (97), e9894 (98), e989c .. e98c4 (99..9d), e98ce (9e), e98d8 (9f), e98ea (a0), e98e2 (a1)',
        C(got==EVAL_EXPECT_TARGETS),dict(got={hex(k):hex(v) for k,v in got.items() if EVAL_EXPECT_TARGETS.get(k)!=v}))
    odd=[r for r in static['e97e0_reach'] if r['target']&1]
    claim('the computed PC e97e4 + 4 * (op - 80) of JMP e97e4(PC,D1.W) is always even (op 80..ff): an odd computed PC cannot occur',C(not odd and len(static['e97e0_reach'])==128),dict(odd=len(odd),values=len(static['e97e0_reach'])))
    cls=collections.Counter(r['cls'] for r in static['e97e0_reach'] if r['op']>=0xa2)
    landing=sorted(r['op'] for r in static['e97e0_reach'] if r['cls']=='block-start')
    claim('operator bytes a2..ff are not range checked: exactly 10 of the 94 values land on a block start (a2 a5 a6 a8 aa ac ae b3 b8 bd) and are executed as the original code does',C(landing==sorted(CONTRACT_OOB_STARTS)),dict(landing=[hex(x) for x in landing],counts=dict(cls)))
    unsup=cls['interior-instruction-start']+cls['inside-instruction']+cls['outside-F3a']
    claim('the remaining operator byte values land inside instructions or in other routines (the contract counts 76; unsupported)',
        C(unsup==76),dict(observed_unsupported=unsup,breakdown=dict(cls),note='94 values - 10 block starts = 84: 18 land on an instruction start inside a block (the native CPU would run them, the machine contract refuses non-block-start PCs), 5 inside an instruction, 61 outside the F3a ranges (c3..ff from e98ee on)'))
    ex=[o for o in lab if o.startswith('eval-oob-')]
    okb=[l for l in ex if M(lab[l]).get('kind')=='eval']
    claim('every table-external operator byte fixture ends as classified: the 10 block-start landings run to 2ac2, the other 84 are refused before the jump (unsupported_code_target, refused_before_jump)',
        C(len(ex)==94 and all((lab[l]['summary']['guard'] is None)==(int(l.split('-')[2],16) in CONTRACT_OOB_STARTS) for l in ex)),dict(fixtures=len(ex),executed=sum(1 for l in ex if lab[l]['summary']['guard'] is None)))
    # ---- natural
    claim('natural F3a node executions (the declared frame pass model of the scheduler observer, 137 seeds): every e9150 / e9176 node run from its recorded entry state reproduces the recorded entry digest, the 2ac2 exit digest (or the e94fe split digest), the ordered port digest and the computed-PC / leader records',
        C(nat['nodes']>0 and nat['entry_digest_equal_recorded']==nat['nodes']==nat['state_digest_equal_recorded']==nat['ports_equal_recorded']==nat['computed_pc_equal_recorded']==nat['leader_sets_consistent_with_recorded'] and nat['node_keys_equal_recorded'] in (True,None)),
        dict(nodes=nat['nodes'],by_callback_and_end=nat['by_callback_and_end'],entry=nat['entry_digest_equal_recorded'],state=nat['state_digest_equal_recorded'],ports=nat['ports_equal_recorded'],idx=nat['computed_pc_equal_recorded'],leaders=nat['leader_sets_consistent_with_recorded']))
    claim('every natural node run equals the independent model (leader sequence + registers at every leader, ordered RAM writes / reads / ROM reads / ports, final registers and the whole RAM)',C(nat['model_segments_equal']==nat['nodes']),dict(equal=nat['model_segments_equal'],nodes=nat['nodes'],carry_evidence=nat['carry_evidence']))
    claim('the regenerated seeds reproduce the published run digests, frame counts and stop reasons',C(nat['seed_run_digest_equal_published']==nat['seed_frames_equal']==nat['seed_stop_equal']==nat['seeds']),dict(seeds=nat['seeds'],digest=nat['seed_run_digest_equal_published']))
    e94=sum(1 for x in rows if x['end']==F3B_ENTRY)
    claim('node runs that reach the F3b boundary e94fe (contract: 101 in its own probe; the scheduler records: 97) stop directly after the BSR.W at e91ac with the return LONG e91b0 pushed',C(e94>0 and all(x['end'] in (FRAME_RET,F3B_ENTRY) for x in rows)),dict(e94fe_nodes=e94,published_records=sum(1 for r in G['records'] if r['cb'] in (0xe9150,0xe9176) and r.get('e94fe'))))
    f3=sum(1 for x in rows if x['end']==FRAME_RET)
    claim('F3a-only node executions (contract: 11,391 = 11,352 e9176 + 39 e9150 in its 142-seed 120-frame probe; this tool: the scheduler observer records)',
        'differs' if f3!=11391 else 'confirmed',dict(f3a_only=f3,e9176_only=sum(1 for x in rows if x['cb']==0xe9176 and x['end']==FRAME_RET),e9150_only=sum(1 for x in rows if x['cb']==0xe9150 and x['end']==FRAME_RET),
        note='the counts depend on the declared frame pass model and the write-protected ROM guards (51 of 142 seeds stop early in the scheduler observation); not a semantic discrepancy'))
    # ---- reachability
    nn=[k for k,v in start_cov.items() if v['needs_typed_fixture']]
    claim('natural reachability of the F3a block starts (contract probe: 86 of 134 reached)',
        'differs' if len(STARTS)-len(nn)!=86 else 'confirmed',dict(natural=len(STARTS)-len(nn),need_typed_fixture=len(nn),starts=nn))
    claim('every one of the 134 block starts is executed natively by at least one natural node or typed condition (e94fe and the bundled stops are stops, never executed)',C(all(v['natural_nodes']>0 or v['typed_hits']>0 for v in start_cov.values())),dict(uncovered=[k for k,v in start_cov.items() if v['natural_nodes']==0 and v['typed_hits']==0]))
    # ---- opcodes
    bad=[];n=0
    for l,r in lab.items():
        m=M(r)
        if r['summary']['guard'] or not m.get('op') and m.get('op')!=0:continue
        f=F(l);lead=f['leader_seq'];g=f['globals_after'];nd=f['node_after'];op_=m['op'];n+=1;ok=True
        if op_==0:ok=(0xe9450 in lead)==(m['cur']<m['lim']) and (0xe9768 in lead)==(m['cur']>=m['lim'])
        elif op_==1:
            wait=0xe9464 in lead;ok=wait==(m['cur']<m['v2'])
            if not wait:ok&=nd['b80']==0 and g['w10d44c']==0 and g['w10d440']==m['v2'] and g['w10d442']==(m['v2']-m['v4'])&0xffff
        elif op_==2:ok=g['w10d442']==m['v'] and g['w10d440']==m['v']
        elif op_==4:ok=g['w10d442']==m['v'] and g['w10d440']==0xffff
        elif op_==3:ok=g['w10d44c']==0x200
        elif op_==6:
            c=m['cnt'];v=m['v2']
            if c==0:ok=nd['w7e']==v and 0xe94d8 in lead
            else:ok=nd['w7e']==(c-1)&0xffff and (0xe94ee in lead)==(c-1!=0)
        if not ok:bad.append(l)
    claim('opcodes 00..04 and 06: 00/01 wait with the unsigned BCC (WORD 10d418 >= WORD 2(op)), 01 clears 80(A6) / 10d44c and writes 10d442 = v2 - v4, 10d440 = v2; 02 writes both = v; 04 writes v / ffff; 03 writes 0200 to 10d44c; 06 sets / decrements 7e(A6)',C(not bad and n>0),dict(checked=n,bad=bad[:10]))
    bad=[]
    for l in ('op05-true','op05-false-offset-pos'):
        f=F(l);want_true=l=='op05-true'
        if (f['node_after']['b80']==0)!=want_true:bad.append(l)
    for l,want in (('op05-false-offset-neg',SCR),('op05-false-offset-zero',SCR)):
        if F(l)['node_after']['p76']!=want:bad.append(l)
    claim('opcode 05: a true expression advances by the length BYTE (the following op07 clears 80(A6)); a false one moves A0 by the sign-extended WORD 2(op) (negative and zero offsets) and sets 81(A6) := ff',C(not bad),dict(bad=bad))
    claim('opcode 07: CLR.B 80(A6) and advance by the length BYTE (length 2, 20, ff); a length 0 op07 never terminates (observer step limit); an odd length leaves a BYTE-aligned stream (BYTE reads at odd addresses are allowed, an odd WORD operand is an address error)',
        C(F('op07-len2')['node_after']['b80']==0 and F('op07-len20')['node_after']['p76']==SCR+0x20 and F('op07-len-ff')['node_after']['p76']==SCR+0xff and lab['op-len0-loop']['summary']['guard']['problem']=='step_limit' and lab['op-odd-length-then-word']['summary']['guard']['problem']=='unsupported_odd_data_access'
            and F('op-odd-length-then-byte-ops')['node_after']['p76']==SCR+5),dict(p76_len20=hex(F('op07-len20')['node_after']['p76']),p76_lenff=hex(F('op07-len-ff')['node_after']['p76'])))
    ports=[(0x2ffff2,0x1000),(0x2ffff0,0)]
    tl=[l for l in lab if l.startswith('stream-terminator-') and not l.endswith('bank3')]
    claim('a stream terminator (first BYTE >= 10) stores the pointer without advancing, writes WORD 100010 := 0 and restores the PVC bank (1000 -> 2ffff2, 0 -> 2ffff0); the null stream returns without any write to the bank register',
        C(all(F(l)['ports']==ports and F(l)['bank_restore_ram_write']==[(0x100010,0)] and F(l)['node_after']['p76']==SCR for l in tl) and F('stream-null')['ports']==[] and F('stream-null-bank3')['modeled_bank']==0x300000 and F('stream-terminator-bank3')['modeled_bank']==0x200000),
        dict(terminators=len(tl),bank3_after=hex(F('stream-terminator-bank3')['modeled_bank']),null_bank3_after=hex(F('stream-null-bank3')['modeled_bank'])))
    f3b=[l for l in lab if l.startswith('stream-f3b-boundary-')]
    claim('first BYTE 08..0f (and an op07 chain that reaches one) stops directly after BSR.W e94fe at e91ac (the F3b entry is never executed)',C(len(f3b)==8 and all(F(l)['end']==F3B_ENTRY and lab[l]['result']['continuous_control'][-1]['stop_evidence']['kind']=='f3b-boundary' for l in f3b) and F('stream-op07-then-f3b')['end']==F3B_ENTRY),dict(fixtures=len(f3b)))
    bk=[l for l in lab if l.startswith('stream-banked-')]
    claim('streams in the banked ROM window are read through the modeled bank (ordered bank reads); the physical bank 2 / 3 windows give the model-checked results',C(len(bk)==6 and all(F(l)['bank_reads']>0 for l in bk)),dict(fixtures=len(bk)))
    # ---- evaluator
    bad=[];n=0
    for l,r in lab.items():
        m=M(r)
        if m.get('kind')!='eval' or r['summary']['guard']:continue
        f=F(l);ram=bytearray(0x10000);ram[0xde30:0xde30+len(bytes.fromhex(f['flags_10de30_48']))]=bytes.fromhex(f['flags_10de30_48'])
        want=expect_expr(m['expr'],ram,f['node_after']['b80_before'])
        if want is None:continue
        n+=1
        if (want!=0)==f['eval_false_path']:bad.append((l,want,f['eval_false_path']))
    claim('evaluator operators (literals, class pushes 80..95, 8c sum, 96 97 98, comparisons 99..9d as signed Scc(a-b), and/or 9e 9f on (a<>0 ? ff : 0), add a1) reproduce the contract semantics on every fixture, including the 7f / 80 sign boundary',C(not bad and n>=250),dict(checked=n,mismatches=bad[:10]))
    s8c=[(l,F(l)['flags_10de30_48']) for l in lab if l.startswith('eval-8c-sum-')]
    sumok8=all(int(bytes.fromhex(h)[0xc])==(sum(bytes.fromhex(h)[k] for k in range(8))&0xff) for l,h in s8c)
    sumok12=all(int(bytes.fromhex(h)[0xc])==(sum(bytes.fromhex(h)[k] for k in range(12))&0xff) for l,h in s8c)
    claim('operator 8c refreshes BYTE 10de3c with the sum of the class counters (the contract text: "class counters 10de30..3b (12), 10de3c = sum")',
        'understated' if (sumok8 and not sumok12) else C(sumok12),dict(sum_of_first_8_bytes_10de30_37=sumok8,sum_of_12_bytes=sumok12,evidence=[(l,h[:26]) for l,h in s8c],note='e932c adds only 8 BYTEs (ADD.B (A0)+,D0 x 8): 10de30..10de37'))
    ev_ops=set()
    for l,r in lab.items():
        m=M(r)
        if m.get('kind')=='eval' and not r['summary']['guard']:ev_ops.update(m['expr']);ev_ops.add(0xa0)
    claim('fixtures execute all 34 table operators 80..a1 (a0 as the terminator of every expression) and the literal pushes < 80',C(set(range(0x80,0xa2))<=ev_ops),dict(missing=[hex(x) for x in sorted(set(range(0x80,0xa2))-ev_ops)]))
    # ---- stack
    deep=F('eval-deep-8-and-chain')['eval_byte_writes']
    claim('the evaluator stack is BYTE pushes with A7 - 2 (one BYTE written per push, descending in steps of 2)',C(len(deep)>=8 and all(deep[i]-deep[i+1]==2 for i in range(7))),dict(addresses=[hex(a) for a in deep[:10]]))
    # ---- unbalanced / return LONG
    un=[l for l in lab if l.startswith('eval-unbalanced-')]
    claim('unbalanced expressions (empty stack / extra value): the RTS of e98ea pops a wrong LONG and jumps to an unmapped address (the observer refuses the fetch; nothing in the stream or the RAM is defined there)',C(len(un)==2 and all(lab[l]['summary']['guard'] for l in un)),dict(reasons=[lab[l]['summary']['guard']['reason'] for l in un]))
    rp={'eval-return-e94c0-z1':(FRAME_RET,0xe94c4),'eval-return-e94c0-z0':(FRAME_RET,0xe9768),'eval-return-e9396-z1':(0xe9428,None),'eval-return-e9396-z0':(0xe939a,None),'eval-return-e939e-z1':(0xe9428,None),'eval-return-e939e-z0':(0xe93a2,None),
        'eval-return-e96b0-z1':(0xe96b8,None),'eval-return-e96b0-z0':(0xe96b4,None),'eval-return-e9768-z0':(FRAME_RET,0xe9768),'eval-return-e94c4-z1':(FRAME_RET,0xe94c4),'eval-return-e94fe':(F3B_ENTRY,None)}
    bad=[l for l,(end,lead) in rp.items() if F(l)['end']!=end or (lead is not None and lead not in L(l))]
    bk_ev=[lab[l]['result']['continuous_control'][-1]['stop_evidence'] for l in rp if rp[l][0] in (0xe9428,0xe939a,0xe93a2,0xe96b8,0xe96b4)]
    claim('decision 3 (bundled): the e98ea return LONG R = e94c0 / e9396 / e939e / e96b0 evaluates the caller branch in the same block (BNE.W e9768 / BEQ.W taken or not); R = e9768 or e94c4 simply continues; R = e94fe stops; any other R (interior instruction start, garbage, odd) is refused',
        C(not bad and all(e and e['kind']=='bundled-branch-boundary' for e in bk_ev) and all(lab[l]['summary']['guard'] for l in ('eval-return-interior-e94c8','eval-return-garbage','eval-return-odd'))),dict(bad=bad,bundled_stops=len(bk_ev),
        guards={l:lab[l]['summary']['guard']['reason'] for l in ('eval-return-interior-e94c8','eval-return-garbage','eval-return-odd')}))
    # ---- e9150
    e50=[l for l in lab if l.startswith('e9150-node-')]
    ok=True;ev_=[]
    for l in e50:
        a6=M(lab[l])['a6'];ins=F(l)['inspect'];g=lambda off,size:ins['%x/%d'%(a6+off,size)][1] if off else ins['%x/%d'%(a6,size)][1]
        r_=dict(cb=g(0,4),w3e=g(0x3e,4),w10de46=ins['10de46/2'][1],w10de48=ins['10de48/2'][1]);ev_.append((l,{k:hex(v) for k,v in r_.items()}))
        ok&=r_['cb']==0xe9176 and r_['w3e']==0x10d38e and r_['w10de46']==0xa0 and r_['w10de48']==0x80
    claim('e9150: 3e(A6) := 10d38e, WORD 10de46 := a0, WORD 10de48 := 80, callback LONG (A6) := e9176 (then e9176 runs in the same execution), on three different nodes',C(ok and len(e50)==3),dict(nodes=ev_))
    # ---- list walk / classes
    bad=[]
    for l in [x for x in lab if x.startswith('walk-') and lab[x]['result']['meta'] and lab[x]['result']['meta'].get('kind')=='walk' and not lab[x]['summary']['guard']]:
        m=M(lab[l]);fl=bytes.fromhex(F(l)['flags_10de30_48']);want=[0]*12
        for k,v in (m.get('pre') or {}).items():want[int(k)]=v
        for c in m['classes']:
            if c<12:want[c]=(want[c]+1)&0xff
        if list(fl[:12])!=want:bad.append((l,list(fl[:12]),want))
    claim('e9204: the walk from the node after 100bf4 to the first node with WORD 10(node) = 0 counts BYTE 6b < 0c into 10de30..3b (BYTE wrap, classes >= 0c ignored)',C(not bad),dict(bad=bad[:5]))
    # ---- players / input / screen
    pl=[(m_,l) for l in lab for m_ in [M(lab[l])] if m_.get('kind')=='players']
    claim('JSR 49392 carry: bit p of BYTE 10d68e = C for player p (e9248 falls to e924c iff bit 0, e9258 to e925c iff bit 1)',C(all((0xe924c in L(l))==bool(m_['mask']&1) and (0xe925c in L(l))==bool(m_['mask']&2) for m_,l in pl) and len(pl)==4),dict(masks=[m_['mask'] for m_,l in pl]))
    inp=[(M(lab[l]),l) for l in lab if M(lab[l]).get('kind')=='input']
    claim('4d7a6 (player callback <> 270e, state WORD <> 0, BYTE 27(A4) <> 0) returns non-zero: e9280 / e9292 count the players with input',C(len(inp)==4 and all((0xe9280 in L(l))==bool(m_['i0']) and (0xe9292 in L(l))==bool(m_['i1']) for m_,l in inp)),dict(fixtures=len(inp)))
    bad=[]
    for l in [x for x in lab if x.startswith('screen-x')]:
        m=M(lab[l]);want=screen_expect(m['xi'],m['yi']);got=list(bytes.fromhex(F(l)['flags_10de30_48'])[0x10:0x16])
        if got!=want:bad.append((l,got,want))
    claim('e9298: the SLT / SEQ / SCS / SCC flags 10de40..45 follow the signed word compares of the player rectangle (relative to the camera) with the thresholds 10de46 / 10de48',C(not bad),dict(fixtures=16,bad=bad[:5]))
    # ---- guards
    gl=[l for l in lab if lab[l]['result']['guarded']]
    claim('every guard condition ends in a native guard with an explicit reason, identical in split / continuous runs, twice',C(len(gl)>=1 and all(lab[l]['summary']['guard'] and lab[l]['summary']['guard'].get('reason') for l in gl)),dict(guards=len(gl)))
    fb=[l for l in lab if l.startswith('f3b-return-') and l.endswith('-declared-stop')];fu=[l for l in lab if l.startswith('f3b-return-') and l.endswith('-undeclared')]
    nc=[l for l in lab if l.startswith('node-callback-')]
    claim('the 12 F3b PCs reached from F3a code (callback entries e9350 e9362 e96cc e96f8 and the TRAP #15 sites e93d8 e9528 e9530 e957a e96d4 e9702 e9780 e9788): stops when declared (directly after the RTS of e98ea / the JSR (A0) of the dispatcher, never executed), refused when undeclared',
        C(len(fb)==12 and len(fu)==12 and len(nc)==4 and all(F(l)['end']==int(l.split('-')[2],16) for l in fb) and all(lab[l]['summary']['guard'] for l in fu) and all(lab[l]['summary']['stop_kind'] in ('f3b-boundary-via-return','f3b-callback-entry') for l in fb+[x for x in nc if x.endswith('declared-stop')])),
        dict(declared=len(fb),undeclared=len(fu),callbacks=len(nc),kinds=sorted({lab[l]['summary']['stop_kind'] for l in fb+nc})))
    claim('a transfer into the middle of a block and a direct entry at a non-start PC are refused before they execute (the observer rule that mirrors the machine contract)',C(lab['eval-return-interior-e94c8']['summary']['guard'].get('refused_before_execution')),dict(reason=lab['eval-return-interior-e94c8']['summary']['guard']['reason']))
    claim('direct entries at every address of the 7 ranges: the 134 block starts as a declared zero-step execute nothing and leave the state unchanged; the 428 interior even PCs and the 562 odd addresses are refused before they execute (unsupported_code_target)',
        C(probe_sum['addresses']==1124 and probe_sum['zero_step_ok']==134 and probe_sum['refused_ok']==990 and probe_sum['twice_equal']==1124),dict(probe_sum))
    claim('every model segment (typed + natural) equals the native run',C(all(m['equal'] for m in models) and nat['model_segments_equal']==nat['nodes']),dict(typed_segments=len(models),natural_segments=nat['nodes']))
    return claims


LIMITATIONS=['Controlled incoming states (the natural node entry states of the scheduler observer\'s DECLARED frame pass model, declared fixtures on recorded dump states), not natural scheduler / IRQ / gameplay reachability; nothing claims BIOS execution.  A node run starts at 2ab8 with A6 = node, A7 = SPd (1ff000), LONG 104ca4 = SPd (F3 decision 10).',
    'F3b (e94fe and everything behind it) is never executed: e94fe, e9428 e939a e93a2 e96b4 e96b8 are stops directly after the transferring instruction.  The three F3b caller branches e9396 e939e e96b0 are routed here only as the bundled branch of the evaluator return (decision 3).',
    'Native carry / CCR is never read (SR is unobserved); branch decisions are evidenced by the executed PC path and the register file at every block leader.  A fresh CPU starts with the declared SR 2000 (CCR 0).  The model keeps a full CCR but a carry produced by the black box 49392 (e9248 / e9258) is taken from the executed native path (carry_evidence).',
    'The observer refuses a transfer into the middle of a block, a direct entry at a non-block-start PC, and the unbounded computed JMP e97e0 target that is not a block start BEFORE the instruction executes (the machine contract: unsupported animation stage event PC); Unicorn would execute instruction starts inside blocks natively.  Unknown-carry rejection is a C++ property, not observable natively.',
    'The cleanup LEA entry 43e34 (LEA 2e(A6),A0; falls into the existing 43e38) is routed here as a black-box entry (the cleanup observer / executor lists 43e04 / 43e34 as unsupported); the black boxes 43e34, 49392, 4d7a6 (and the dispatcher shell 2ab8..2ac2) are replayed in the model from their native exit state.',
    'In-process observer extensions: 3c0006 video port (U5), a memoized capstone decode of the routed ranges (identical results) and the replacement of the scheduler observer\'s SeedRun.f3_replay / model_node hooks (same SeedRun, same continuous run, digests asserted equal to the published run digests); no shared tool file is edited.',
    'The Python model is an instruction-level M68000 subset interpreter of the F3a ROM bytes; only the F3a-attributed events (PC in the 7 ranges) are compared; native Unicorn data events are the oracle (no dummy reads of CLR / Scc / MOVE).',
    'Game meanings of the opcodes, evaluator operators and the class / flag bytes remain inferred (contract unknown items).']


if __name__=='__main__':main()
