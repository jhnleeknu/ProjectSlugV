"""Unpatched stage controller F1b (area clear 47da4: prepare / 30 + 160 + 48 frame timers / player survival branch / child allocation / sound / exit fade / next area) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the buffer/cue observer U7
(observe_animation_machine_buffer_cue and through it the script/placement observer U5, scene update U4, motion walk U3, scene core U2, frame helper U1, the U6 input
observer ranges and the card-menu / fade-card chain): persistent-CPU Observer with the declared host-change vocabulary RAM write / PC redirect / A7 delta,
fresh-twice reproduction, split (stop at the first hit of every checkpoint) versus continuous equivalence, ordered port events, banked reads with the modeled bank,
SHA pins of every imported tool module, ROM SHA/mtime guard.  The declared observer extension of U5 (a WORD write to 3c0006 is a 'video' port event) is installed in
this process exactly as U5/U7 do; nothing in the imported modules or tools is edited.  (The F1a observer is NOT imported: it is being written by another worker.)

Unit: the 376 contract bytes of docs/analysis/animation-machine-area-clear-f1b-contract.md (6 code ranges 47da4..47eac 4b6e4..4b6f4 1c5b0..1c5ea 1bee4..1bef8 ca48..ca50
9056..9060, 81 instructions, 39 block starts).  Main decisions of the contract implemented here as the observation rules:
  * one machine run = ONE frame.  A frame ends at the 480f0 RTS that pops the declared dispatcher return LONG 2ac2 (stop 2ac2, A7 = 1feffc + 4); the last frame ends
    at 477ee (the F1c boundary, stop directly after BRA.W at 47ea8, A7 = 1feffc).  There is no Waiting state for the five frame timers / polls.
  * the next frame is a declared direct re-entry (A6 = 100b30, A5 = 108000, the previous native registers, PC := the callback LONG at (A6), A7 := 1feffc, LONG 2ac2 at
    (A7); the work-RAM mirror of 10effc): PC redirect + A7 delta + RAM write, nothing else.  No scheduler is run: the children e4234 / d72fe are never executed
    (the 2ac2 stop prevents it; a run without that stop is a negative test: it faults at the child callback).
  * external producers (62(A6) child completion, 10dd44, 10d68e, 10d683 bit0) only as declared host RAM writes between frames.
  * 47e3a 28ae failure: original behaviour (fallback node 100e98, WORD 100f0e written).
  * every frame of every condition records the full state SHA256 (64KiB RAM, 16 registers D0-D7 A0-A7, PC, bank, ordered ports of the frame); full dumps are stored at
    the boundary frames (0, 29, 188, 189, 236), for all typed conditions and for all frames of 8 natural seeds.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step
record; a declared initial SR (default 2000, CCR 0) and the declared initial registers are part of the fixture summary.  Nothing claims BIOS execution or a natural
scheduler / natural IRQ.

Seeds (all pinned by SHA256):
  natural   artifacts/stage_entry_body/observation.json (pinned): the 142 recorded final RAM outputs of the original 47a94 body runs (phase with final PC ff000: 137 begin +
            5 release-poisoned-prefix), registers as recorded (A6 = 100b30, A5 = 108000, SR 2000), bank 2 / 3.  Direct entry at 47da4 with the declared dispatcher return
            LONG 2ac2 at A7 = 1feffc, one frame per machine run, declared host write 10dd44 := ff after frame 188.  (The contract text says 137 seeds: superseded, 142 are used.)
  typed     declared variants on three natural seeds (alive / fail / half / ...), direct callback entries, player node variants, 8c16 / 3af8 paths, the transition observation
            case 77 (partial run), guards and zero-step entries of all 39 block starts.
Every condition is run as a fresh-CPU chain, split (stop at the first hit of every checkpoint of every frame) and continuous, each twice; the two are compared per frame and the
reproductions by SHA of the complete native record.  Every frame is additionally replayed on a FRESH CPU from its recorded input state (the C++ one-run-one-frame view).

An independent Python model of the contract (a basic-block machine transcribed instruction by instruction from the 39 original block byte strings with a complete CCR model,
32-bit register semantics, explicit byte/word/long operations; it shares no code with Unicorn or the C++) is compared with every native frame: block-leader sequence with the full
register file at every leader, ordered RAM writes of the F1b code, ordered ROM reads / ports of the F1b code (none), the final registers and the whole 64KiB RAM image.  Every
callee outside the six ranges (2a48 289e 49c20 28ae 9060 3af8 8c16 and the frame helper 480bc) is a black box whose native exit registers and RAM / port writes are replayed;
the carry of 289e and 28ae is computed by the model from the contract formulas (not taken from the native run) and checked by the native branch outcome / SCC write.  Any
difference is recorded in contract_discrepancies.
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
from disassemble_program import load_verified_program,disassemble_range
sp=bc.sp;inp=bc.inp;fh=bc.fh;fc=bc.fc;mt=bc.mt;op=bc.op;sc=bc.sc;seb=bc.seb;vsf=bc.vsf;shared=bc.shared;activation=bc.activation
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_area_clear_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-area-clear-f1b-contract.md'
CONTRACT_SHA='6bd2e96395e73814b7d4308f03d027eb1fb7be3c17ef8019491512340f66d4f2'
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
END_STOP=0x477ee
FRAME_RTS=0x480f0
CALLBACKS=(0x47de4,0x47e22,0x47e62,0x47e70,0x47e92)
WAIT_PCS=(0xcda4,0x3aea)
STEP_LIMIT=400000                                           # declared per-run instruction watchdog of the observer (the original has none); a fixture may declare a smaller step_limit
F1B_RANGES=((0x47da4,0x47eac),(0x4b6e4,0x4b6f4),(0x1c5b0,0x1c5ea),(0x1bee4,0x1bef8),(0xca48,0xca50),(0x9056,0x9060))
F1A_CALLEE=((0x9060,0x9068),)                                # F1a block 9060 (CLR.B 107def; RTS): a declared black-box callee of F1b, observed natively only
BOUNDARY_FRAMES=(0,29,188,189,236)
DUMP_SEEDS=(0,60,117,118,134,126,135,141)                  # natural seeds with the full per-frame dumps (every family / bank / release case)
DISCREPANCIES=[]
INFO=[]


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)
def in_f1b(pc):return in_ranges(pc,F1B_RANGES)


# ----------------------------------------------------------------------------------
# Contract text: byte table, block table, block starts, bundled branches, carry classes
# ----------------------------------------------------------------------------------
def parse_contract(program):
    lines=CONTRACT.read_text().splitlines()
    rows=[];code=[];blocks=[]
    pat_r=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| `([0-9a-f]+)` \|$')
    pat_b=re.compile(r'^\| `([0-9a-f]+)` \| `([0-9a-f]+)` \| (.*) \|$')
    for line in lines:
        m=pat_r.match(line)
        if m:
            lo,hi=int(m.group(1),16),int(m.group(2),16);data=program[lo:hi]
            assert data.hex()==m.group(3),(hex(lo),hex(hi));rows.append(dict(range='%x..%x'%(lo,hi),size=hi-lo,bytes_equal_to_rom=True,sha256=sha(data)));code.append((lo,hi))
            continue
        m=pat_b.match(line)
        if m:blocks.append((int(m.group(1),16),bytes.fromhex(m.group(2)),m.group(3)))
    assert code==list(F1B_RANGES),code
    assert sum(h-l for l,h in code)==376
    starts=bundled=preserve=consumers=None
    for i,line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (39개)**'):
            j=i+1
            while not lines[j].startswith('`'):j+=1
            starts=[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',lines[j])]
        if line.startswith('- **묶인 조건분기 PC (6개'):bundled=[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',line.split('**:',1)[1].split('. [F]')[0])]
        if line.startswith('- **Carry 소비 block (3개)**'):consumers=[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',line)]
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (16개)**'):preserve=[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',line.split('**:',1)[1])]
    assert starts and len(starts)==len(set(starts))==39,len(starts or ())
    assert bundled and len(bundled)==len(set(bundled))==6
    assert preserve and len(preserve)==len(set(preserve))==16
    consumers=[x for x in consumers if x in starts];assert sorted(consumers)==[0x1c5bc,0x1c5d8,0x47e0a],consumers
    assert len(blocks)==39 and sorted(b[0] for b in blocks)==sorted(starts),(len(blocks),)
    return rows,starts,bundled,consumers,preserve,blocks


STARTS=();BUNDLED=();CONSUMERS=();PRESERVE=();BLOCK_ROWS=[];TABLE=[];F1B_INSTR={};BB_ENTRIES=();LEAD_PCS=frozenset();CK_SET=frozenset();START_SET=frozenset();RANGES_ALL=()
EVEN_PCS=();INTERIOR=()


def external_targets(program):
    """Targets of the JSR/JMP/BSR/BRA/Bcc instructions of the F1b ranges that leave the ranges (the black-box entries)."""
    out={}
    for lo,hi in F1B_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):
            pc=r['cpu_address'];raw=bytes.fromhex(r['raw']);t,k=fh.branch_target(pc,raw)
            if raw[:2]==b'\x4e\xf9':t=int.from_bytes(raw[2:6],'big')            # JMP abs.l (1bef2)
            if t is not None and not in_f1b(t):out.setdefault(t,[]).append(pc)
    return out


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


def configure(program,out_dir):
    global STARTS,BUNDLED,CONSUMERS,PRESERVE,BLOCK_ROWS,TABLE,F1B_INSTR,BB_ENTRIES,LEAD_PCS,CK_SET,START_SET,RANGES_ALL,EVEN_PCS,INTERIOR
    ext=bc.configure(program,out_dir)                                   # installs the U5/U7 observer extension and fills fc/fh globals for the existing executors
    rows,starts,bundled,consumers,preserve,blocks=parse_contract(program)
    TABLE=rows;STARTS=tuple(starts);BUNDLED=tuple(bundled);CONSUMERS=tuple(consumers);PRESERVE=tuple(preserve);BLOCK_ROWS=blocks
    decoded=set(fh.leaders_of(program,F1B_RANGES))
    assert decoded|set(CALLBACKS)==set(STARTS),(sorted(hex(x) for x in (decoded|set(CALLBACKS))^set(STARTS)))
    assert len(decoded)==34 and not (set(CALLBACKS)&decoded)
    assert not set(BUNDLED)&set(STARTS)
    for lo,hi in F1B_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):F1B_INSTR[r['cpu_address']]=r
    assert len(F1B_INSTR)==81 and not any(r['classification']=='undecoded_word' for r in F1B_INSTR.values())
    ext_t=external_targets(program);assert END_STOP in ext_t and ext_t.pop(END_STOP)==[0x47ea8]          # the F1c boundary (BRA.W at 47ea8) is a stop, not a callee
    BB_ENTRIES=tuple(sorted(ext_t))
    assert BB_ENTRIES==(0x289e,0x28ae,0x2a48,0x3af8,0x8c16,0x9060,0x480bc,0x49c20),[hex(x) for x in BB_ENTRIES]
    EVEN_PCS=tuple(p for lo,hi in F1B_RANGES for p in range(lo,hi,2));INTERIOR=tuple(p for p in EVEN_PCS if p not in set(STARTS))
    assert len(EVEN_PCS)==188 and len(INTERIOR)==149
    START_SET=frozenset(STARTS);LEAD_PCS=frozenset(STARTS)|frozenset(BB_ENTRIES);CK_SET=frozenset(LEAD_PCS)
    RANGES_ALL=tuple(dict.fromkeys(tuple(bc.RANGES)+F1B_RANGES+F1A_CALLEE))
    assert not in_ranges(END_STOP,RANGES_ALL)                            # 477ee (F1c) is a boundary, not routed
    fc.OUT=out_dir;fc.RANGES=RANGES_ALL;fc.BOUNDARIES=();fc.KEY_PCS=()
    fh.OUT=out_dir;fh.POOL.clear()
    install_observer();install_decode_cache()
    return ext


# ----------------------------------------------------------------------------------
# Observer: U5 observer (3c0006 video port) + declared initial SR, wait stops at cda4 / 3aea, leader records (F1b block starts and the black-box entries reached directly from F1b code)
# ----------------------------------------------------------------------------------
class F1bMixin(object):
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
            self.total+=1
            if self.total>self.step_limit:
                self.guard=dict(problem='step_limit',pc=pc,steps=self.total,limit=self.step_limit);cpu.emu_stop();return
            if pc in WAIT_PCS:
                a5=cpu.reg_read(REGS['a5'])
                if pc==0xcda4:
                    live=int.from_bytes(cpu.mem_read((a5+0xd34)&M32,2),'big');want=cpu.reg_read(REGS['d4'])&0xffff;blocked=live!=want
                else:
                    live=int.from_bytes(cpu.mem_read((a5-0x328c)&M32,2),'big');want=cpu.reg_read(REGS['d1'])&0xffff;blocked=live==want
                if blocked:
                    self.stop_pc=pc;self.wait=dict(pc=pc,live_word=live,compared_word=want,kind='sprite' if pc==0xcda4 else 'sound');cpu.emu_stop();return
            if pc in LEAD_PCS and (pc in START_SET or (self.last_pc is not None and in_f1b(self.last_pc))):
                self.leads.append(dict(pc=pc,regs=self.regs(),pc_index=len(self.pcs)-1,event_index=len(self.events)))
            self.last_pc=pc
        c.hook_add(UC_HOOK_CODE,cb)
        return self
    def run(self,allow_guard=False):
        self.leads=[];self.wait=None;self.mine_seen=set(self.seen);self.total=0
        r=super().run(allow_guard=allow_guard)
        g=r['guard']
        if g is not None and g.get('problem')=='unsupported_code_target':
            t=g['target'];prev=r['pcs'][-2] if len(r['pcs'])>=2 and r['pcs'][-1]==t else (r['pcs'][-1] if r['pcs'] else None)
            if t&1:g['reason']='odd target PC %x (an address error on the original CPU)'%t;g['odd_pc']=True
            else:g['reason']='control transfer to %x, outside every routed range, from %s'%(t,hex(prev) if prev is not None else 'the entry')
        elif g is not None and g.get('problem') in ('unsupported_write','unmapped_or_protected'):
            g['reason']='write to the program ROM / an unmapped address %s'%hex(g.get('address',0))
        elif g is not None and g.get('problem')=='unsupported_odd_data_access':
            g['reason']='odd address %x for a %d-byte %s access (address error on the original CPU)'%(g['address'],g['size'],g['access']);g['reason_kind']='odd_word_access'
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


F1bObserver=None


def install_observer():
    global F1bObserver
    base=[k for k in bc.U7Observer.__mro__ if k.__name__=='U5Observer'][0]
    F1bObserver=type('F1bObserver',(F1bMixin,base),{})
    fc.Observer=F1bObserver


def W(address,size,value,why):return fc.ram_write(address,size,value,why)


# ----------------------------------------------------------------------------------
# Chain runner: persistent CPU, one step per declared stop (one step = one frame, or the release of a wait), split (stop at the first hit of every checkpoint) or continuous
# ----------------------------------------------------------------------------------
RUNS=[0]


def run_chain(program,spec,continuous,sink=None):
    RUNS[0]+=1
    fx=spec['fixture'];allow=bool(spec.get('guarded'));o=F1bObserver(program,continuous);phases=[]
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
WAIT_PREV={0xcda4:{0xcda0:'6700',0xcda8:'66fa'},0x3aea:{0x3ae6:'0241',0x3aee:'67fa'}}


def stop_evidence(program,p,origin,group=()):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc'];ram=p['ram_after']
    if p['waiting']:
        assert pcs[-1]==pc and pc in WAIT_PCS,(p['label'],hex(pc))
        w=p['wait']
        if len(pcs)==1:return dict(kind='wait',outgoing_pc=pc,previous_pc=None,wait=w,reached_from='zero-step re-stop: the resumed wait is still blocked (stop PC = entry PC, nothing executed)')
        prev=pcs[-2];allowed=WAIT_PREV[pc]
        assert prev in allowed and program[prev:prev+2].hex()==allowed[prev],(p['label'],hex(prev),hex(pc))
        return dict(kind='wait',outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),wait=w,
            reached_from='%s at %x %s into the %s wait at %x (blocked: live WORD %04x %s %04x); the instruction at %x is not executed'%(program[prev:prev+2].hex(),prev,'fell through' if prev in (0xcda0,0x3ae6) else 'looped back (taken)',w['kind'],pc,w['live_word'],'<>' if pc==0xcda4 else '=',w['compared_word'],pc))
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(kind='zero-step',outgoing_pc=pc,previous_pc=None,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];a7=o['a7'];inc=origin['incoming']
    if pc==END_STOP:
        assert prev==0x47ea8 and program[prev:prev+4].hex()=='6000f944',(p['label'],hex(prev))
        return dict(kind='branch-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes='6000f944',reached_from='BRA.W 477ee at 47ea8 (bytes 6000f944) directly after CLR.B 10d681; 477ee (F1c) is not executed')
    if pc==0x47de4 and prev==0x47dde:
        assert program[prev:prev+6].hex()=='2cbc00047de4',(p['label'],)
        return dict(kind='fallthrough-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes='2cbc00047de4',reached_from='fall-through directly after MOVE.L #47de4,(A6) at 47dde; 47de4 is not executed')
    if pc in (0x47e22,0x47e62,0x47e70,0x47e92,0x47e30,0x47e56,0x47e1c) and program[prev:prev+6].hex()==('2cbc%08x'%pc) and prev+6==pc:
        return dict(kind='fallthrough-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),reached_from='fall-through directly after MOVE.L #%x,(A6) at %x; %x is not executed'%(pc,prev,pc))
    assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
    on_stack=[off for off in range(0,64,2) if u32(origin['ram_before'],inc['a7']+off)==pc]
    pushed=[e['pc'] for q in group for e in q['events'] if e['region']=='ram' and e['access']=='write' and e['size']==4 and int(e['bytes'],16)==pc]
    assert on_stack or pushed or any(e['region']=='ram' and e['access']=='write' and e['size']==4 and int(e['bytes'],16)==pc and e['address']==a7-4 for e in p['events']),(p['label'],'the popped LONG %x was neither declared on the stack at the step entry nor pushed by a JSR of the step'%pc)
    return dict(kind='return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',return_long_on_stack_at_entry_offsets=on_stack,entry_a7=inc['a7'],
        reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x); %x is never executed'%(prev,pc,a7,pc))


def annotate(program,phases):
    first={};group=collections.defaultdict(list)
    for p in phases:first.setdefault(p['step'],p);group[p['step']].append(p)
    for p in phases:p['stop_evidence']=stop_evidence(program,p,first[p['step']],group[p['step']])


# ----------------------------------------------------------------------------------
# Independent model: a basic-block machine (transcription of the original instructions of the 39 block byte strings of the contract table).  A complete CCR is kept
# (X N Z V C, None = unknown) so that a flag consumed without a producer is an error.  Calls push the return LONG, the replayed black boxes pop it, so call / return pairing
# is checked by the live stack exactly as on the CPU.  The carry of 289e (readiness) and 28ae (fade-card allocation) is computed from the contract formulas before the replay.
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
class StopWait(Exception):
    def __init__(self,pc):self.pc=pc
REGN=tuple(KEYS)                                                     # d0..d7 a0..a6
BLK={}


def blk(*pcs):
    def deco(fn):
        for pc in pcs:
            assert pc not in BLK,hex(pc);BLK[pc]=fn
        return fn
    return deco


def msb(v,bits):return (v>>(bits-1))&1


class MM(object):
    def __init__(self,program,bank_state,ram,regs,env,sr=None):
        self.prog=program;self.bank,self.ff8,self.ff9=bank_state;self.ram=bytearray(ram);self.r={k:regs[k]&M32 for k in REGN+('a7',)};self.env=env
        self.leads=[];self.writes=[];self.rom_reads=[];self.ports=[];self.bb_writes=0
        self.cc=dict(X=None,N=None,Z=None,V=None,C=None)
        if sr is not None:self.cc=dict(X=(sr>>4)&1,N=(sr>>3)&1,Z=(sr>>2)&1,V=(sr>>1)&1,C=sr&1)
    # ---- memory: RAM mirrored over 100000..1fffff, fixed ROM below 100000, banked window at 200000
    def rd(self,a,n):
        a&=M32
        if n>1 and a&1:raise ModelError('odd read %x'%a)
        if a<0x100000:
            self.rom_reads.append((a,n,'fixed'));return int.from_bytes(self.prog[a:a+n],'big')
        if a<0x200000:return int.from_bytes(bytes(self.ram[(a+i)&0xffff] for i in range(n)),'big')
        if a<0x2fe000:
            ph=self.bank+a-0x200000;self.rom_reads.append((a,n,'bank'));return int.from_bytes(self.prog[ph:ph+n],'big')
        raise ModelError('read %x'%a)
    def put(self,a,n,v):
        for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
    def wr(self,a,n,v):
        a&=M32
        if n>1 and a&1:raise ModelError('odd write %x'%a)
        if not 0x100000<=a<0x200000:raise ModelError('write %x'%a)
        v&=(1<<(8*n))-1;self.put(a,n,v);self.writes.append((n,a,v))
    def push32(self,v):
        self.r['a7']=(self.r['a7']-4)&M32;self.wr(self.r['a7'],4,v)
    def pop32(self):
        v=self.rd(self.r['a7'],4);self.r['a7']=(self.r['a7']+4)&M32;return v
    def call(self,target,ret):self.push32(ret);return target
    def lw(self,reg,v):self.r[reg]=(self.r[reg]&0xffff0000)|(v&0xffff)
    def lb(self,reg,v):self.r[reg]=(self.r[reg]&0xffffff00)|(v&0xff)
    def a5(self,off):return (self.r['a5']+off)&M32
    def a6(self,off):return (self.r['a6']+off)&M32
    def lead(self,pc):
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)
    # ---- flags
    def nz(self,v,bits):                               # MOVE / MOVEQ / TST / CLR: N Z, V = C = 0 (X unchanged)
        v&=(1<<bits)-1;self.cc.update(N=msb(v,bits),Z=int(v==0),V=0,C=0)
    def subq(self,d,s,bits):                           # SUBQ: X = C = borrow
        m=(1<<bits)-1;d&=m;s&=m;r=(d-s)&m;c=int(d<s)
        self.cc.update(X=c,N=msb(r,bits),Z=int(r==0),V=(((d^s)&(d^r))>>(bits-1))&1,C=c);return r
    def addq(self,d,s,bits):                           # ADDQ: X = C = carry
        m=(1<<bits)-1;d&=m;s&=m;r=(d+s)&m;c=int(d+s>m)
        self.cc.update(X=c,N=msb(r,bits),Z=int(r==0),V=(((~(d^s))&(d^r))>>(bits-1))&1,C=c);return r
    def flag(self,name):
        v=self.cc[name]
        if v is None:raise ModelError('branch on an unknown %s flag'%name)
        return v
    def bit(self,v,n):self.cc['Z']=int((v>>n)&1==0)    # BTST / BSET / BCLR: Z = the tested bit was 0
    def bset(self,a,n):
        v=self.rd(a,1);self.bit(v,n);self.wr(a,1,v|(1<<n))
    def bclr(self,a,n):
        v=self.rd(a,1);self.bit(v,n);self.wr(a,1,v&~(1<<n))


@blk(0x47da4)
def m47da4(M):return M.call(0x4b6e4,0x47daa)                                          # jsr 4b6e4.l
@blk(0x47daa)
def m47daa(M):return M.call(0x4b6ec,0x47db0)
@blk(0x47db0)
def m47db0(M):
    M.r['a0']=M.a5(-0x740c);return M.call(0x2a48,0x47dba)                              # lea.l -740c(a5),a0 ; jsr 2a48.l
@blk(0x47dba)
def m47dba(M):return M.call(0x1c5b0,0x47dc0)
@blk(0x47dc0)
def m47dc0(M):return M.call(0x1bee4,0x47dc6)
@blk(0x47dc6)
def m47dc6(M):
    M.bclr(M.a5(0x5683),5);M.bclr(M.a5(0x5683),1);return M.call(0xca48,0x47dd8)         # bclr.b #5,5683(a5) ; bclr.b #1,5683(a5) ; jsr ca48.l
@blk(0x47dd8)
def m47dd8(M):
    M.wr(M.a6(0x7a),2,0x1e);M.nz(0x1e,16)                                              # move.w #1e,7a(a6)
    M.wr(M.r['a6'],4,0x47de4);M.nz(0x47de4,32);return 0x47de4                          # move.l #47de4,(a6) ; fall through
@blk(0x47de4)
def m47de4(M):
    a=M.a6(0x7a);v=M.subq(M.rd(a,2),1,16);M.wr(a,2,v)                                  # subq.w #1,7a(a6)
    return 0x480bc if M.flag('Z')==0 else 0x47dec                                      # bne.w 480bc
@blk(0x47dec)
def m47dec(M):
    v=M.rd(M.a5(0x568e),1);M.nz(v,8)                                                   # tst.b 568e(a5)
    return 0x47e30 if M.flag('Z') else 0x47df4                                         # beq.w 47e30
@blk(0x47df4)
def m47df4(M):return M.call(0x9056,0x47dfa)
@blk(0x47dfa)
def m47dfa(M):
    M.r['a0']=0xe4234;M.lw('d0',0);M.nz(0,16);return M.call(0x28ae,0x47e0a)            # movea.l #e4234,a0 ; move.w #0,d0 ; jsr 28ae.l
@blk(0x47e0a)
def m47e0a(M):
    c=M.flag('C');M.wr(M.a6(0x62),1,0xff if c==0 else 0)                                # scc.b 62(a6): condition CC (C clear) -> ff, else 00; CCR unchanged
    return 0x47e1c if c==0 else 0x47e12                                                # bcc.w 47e1c
@blk(0x47e12)
def m47e12(M):
    M.r['d0']=0;M.lb('d0',M.rd(M.a6(0x7c),1));M.nz(M.r['d0'],32)                        # moveq #0,d0 ; move.b 7c(a6),d0
    M.wr((M.r['a0']+0x76)&M32,2,M.r['d0']&0xffff);M.nz(M.r['d0'],16);return 0x47e1c    # move.w d0,76(a0)
@blk(0x47e1c)
def m47e1c(M):
    M.wr(M.r['a6'],4,0x47e22);M.nz(0x47e22,32);return 0x47e22                          # move.l #47e22,(a6) ; fall through
@blk(0x47e22)
def m47e22(M):
    v=M.rd(M.a6(0x62),1);M.nz(v,8)                                                     # tst.b 62(a6)
    return 0x480bc if M.flag('Z') else 0x47e2a                                         # beq.w 480bc
@blk(0x47e2a)
def m47e2a(M):return M.call(0x9060,0x47e30)
@blk(0x47e30)
def m47e30(M):
    M.r['a0']=0xd72fe;M.lw('d0',0x14);M.nz(0x14,16);return M.call(0x28ae,0x47e40)      # movea.l #d72fe,a0 ; move.w #14,d0 ; jsr 28ae.l
@blk(0x47e40)
def m47e40(M):
    M.r['d0']=0;M.lb('d0',M.rd(M.a6(0x7c),1));M.nz(M.r['d0'],32)                        # moveq #0,d0 ; move.b 7c(a6),d0
    M.lw('d0',M.addq(M.r['d0'],1,16))                                                  # addq.w #1,d0
    M.wr((M.r['a0']+0x76)&M32,2,M.r['d0']&0xffff);M.nz(M.r['d0'],16)                   # move.w d0,76(a0)
    M.lw('d0',0x19db);M.nz(0x19db,16);return M.call(0x3af8,0x47e56)                    # move.w #19db,d0 ; jsr 3af8.l
@blk(0x47e56)
def m47e56(M):
    M.wr(M.a6(0x7a),2,0xa0);M.wr(M.r['a6'],4,0x47e62);M.nz(0x47e62,32);return 0x47e62  # move.w #a0,7a(a6) ; move.l #47e62,(a6)
@blk(0x47e62)
def m47e62(M):
    a=M.a6(0x7a);v=M.subq(M.rd(a,2),1,16);M.wr(a,2,v);return 0x480bc if M.flag('Z')==0 else 0x47e6a
@blk(0x47e6a)
def m47e6a(M):
    M.wr(M.r['a6'],4,0x47e70);M.nz(0x47e70,32);return 0x47e70
@blk(0x47e70)
def m47e70(M):
    v=M.rd(M.a5(0x5d44),1);M.nz(v,8);return 0x480bc if M.flag('Z') else 0x47e78       # tst.b 5d44(a5) ; beq.w 480bc
@blk(0x47e78)
def m47e78(M):
    for k in ('d0','d1','d2'):M.r[k]=0xffffffe1                                         # moveq #e1 (sign extended to LONG)
    M.r['d3']=0x30;M.nz(0x30,32);return M.call(0x8c16,0x47e86)                         # moveq #30,d3 ; jsr 8c16.l
@blk(0x47e86)
def m47e86(M):
    M.wr(M.a6(0x7a),2,0x30);M.wr(M.r['a6'],4,0x47e92);M.nz(0x47e92,32);return 0x47e92
@blk(0x47e92)
def m47e92(M):
    a=M.a6(0x7a);v=M.subq(M.rd(a,2),1,16);M.wr(a,2,v);return 0x480bc if M.flag('Z')==0 else 0x47e9a
@blk(0x47e9a)
def m47e9a(M):
    a=M.a6(0x7c);v=M.addq(M.rd(a,1),1,8);M.wr(a,1,v)                                   # addq.b #1,7c(a6)
    v=M.rd(a,1);M.wr(M.a5(0x5680),1,v);M.nz(v,8)                                       # move.b 7c(a6),5680(a5)
    M.wr(M.a5(0x5681),1,0);M.nz(0,8);return 0x477ee                                    # clr.b 5681(a5) ; bra.w 477ee
@blk(0x4b6e4)
def m4b6e4(M):
    M.wr(M.a5(0x5b85),1,0xff);M.nz(0xff,8);return M.pop32()
@blk(0x4b6ec)
def m4b6ec(M):
    M.wr(M.a5(0x5b87),1,0xff);M.nz(0xff,8);return M.pop32()
@blk(0x1c5b0)
def m1c5b0(M):
    M.r['a0']=0x100cb8;return M.call(0x289e,0x1c5bc)
@blk(0x1c5bc)
def m1c5bc(M):return 0x1c5cc if M.flag('C')==0 else 0x1c5c0                             # bcc.w 1c5cc
@blk(0x1c5c0)
def m1c5c0(M):
    M.bset((M.r['a0']+0x61)&M32,6);M.bset((M.r['a0']+0xa8)&M32,0);return 0x1c5cc        # bset.b #6,61(a0) ; bset.b #0,a8(a0)
@blk(0x1c5cc)
def m1c5cc(M):
    M.r['a0']=0x100da8;return M.call(0x289e,0x1c5d8)
@blk(0x1c5d8)
def m1c5d8(M):return 0x1c5e8 if M.flag('C')==0 else 0x1c5dc
@blk(0x1c5dc)
def m1c5dc(M):
    M.bset((M.r['a0']+0x61)&M32,6);M.bset((M.r['a0']+0xa8)&M32,0);return 0x1c5e8
@blk(0x1c5e8)
def m1c5e8(M):return M.pop32()
@blk(0x1bee4)
def m1bee4(M):
    M.r['a0']=0x1bec0;M.r['d0']=0;M.nz(0,32);return M.call(0x49c20,0x1bef0)            # lea.l 1bec0(pc),a0 (address only) ; moveq #0,d0 ; jsr 49c20.l
@blk(0x1bef0)
def m1bef0(M):
    M.r['d0']=1;M.nz(1,32);return 0x49c20                                              # moveq #1,d0 ; jmp 49c20.l (no push: the return LONG of the caller of 1bee4 stays)
@blk(0xca48)
def mca48(M):
    M.wr(M.a5(-0x7699),1,0xff);M.nz(0xff,8);return M.pop32()
@blk(0x9056)
def m9056(M):
    M.wr(0x107def,1,0xff);M.nz(0xff,8);return M.pop32()
assert len(BLK)==39 and sorted(BLK)==sorted([0x47da4,0x47daa,0x47db0,0x47dba,0x47dc0,0x47dc6,0x47dd8,0x47de4,0x47dec,0x47df4,0x47dfa,0x47e0a,0x47e12,0x47e1c,0x47e22,0x47e2a,0x47e30,0x47e40,0x47e56,0x47e62,0x47e6a,0x47e70,0x47e78,0x47e86,0x47e92,0x47e9a,
    0x4b6e4,0x4b6ec,0x1c5b0,0x1c5bc,0x1c5c0,0x1c5cc,0x1c5d8,0x1c5dc,0x1c5e8,0x1bee4,0x1bef0,0xca48,0x9056])


def bb_name(pc):return {0x289e:'readiness-289e',0x28ae:'fade-card-28ae',0x2a48:'cleanup-2a48',0x3af8:'sound-3af8',0x480bc:'frame-480bc',0x49c20:'input-49c20',0x8c16:'exit-8c16',0x9060:'F1a-9060',0x3aea:'sound-wait-resume',0xcda4:'sprite-wait-resume'}.get(pc,hex(pc))


def blackbox(M,entry,resume=None):
    """Replay of a callee outside the six ranges: its native exit registers, RAM writes and PVC register writes are replayed; the carry of 289e / 28ae is computed from the contract formulas first."""
    env=M.env;nl=env['nl'];events=env['events'];k=len(M.leads)
    if resume is None:
        if not (k>=1 and k-1<len(nl) and nl[k-1]['pc']==entry):raise ModelError('%s black box: native leads do not align at lead %d'%(bb_name(entry),k))
        ret=M.rd(M.r['a7'],4);a7=M.r['a7'];lo=nl[k-1]['event_index']
    else:
        ret=resume['ret'];a7=resume['a7'];lo=0;k=0
    carry=None
    if resume is None and entry==0x289e:carry=0 if M.rd(M.r['a0'],4)==0x270e else 1
    if resume is None and entry==0x28ae:
        d0w=M.r['d0']&0xffff;count=M.rd(0x104ca0,2);a0=M.r['a0']
        carry=1 if (d0w<count and a0!=0) else 0
        head=M.rd(M.a5(-0x3364),4)
        if carry and head==0:raise ModelError('28ae success with an empty free list head: the original writes through address 0 (ROM)')
        want_a0=head if carry else (M.a5(-0x7168))
    if k<len(nl):
        if nl[k]['pc']!=ret:raise ModelError('%s black box returned to %x, the model expects %x'%(bb_name(entry),nl[k]['pc'],ret))
        exit_regs=nl[k]['regs'];hi=nl[k]['event_index'];ended=False
    else:
        exit_regs=env['outgoing'];hi=len(events);ended=True
    for e in events[lo:hi]:
        if in_f1b(e['pc']):raise ModelError('F1b code executed inside the %s black box interval (pc %x)'%(bb_name(entry),e['pc']))
        if e['region']=='ram' and e['access']=='write':
            M.put(e['address'],e['size'],int(e['bytes'],16));M.bb_writes+=1
        elif e['region']=='pvc' and e['access']=='write':
            M.bank,M.ff8,M.ff9=e['bank_after'],e['ff8_after'],e['ff9_after']
    waiting=False
    if ended:
        if env['waiting']:
            if exit_regs['pc'] not in WAIT_PCS:raise ModelError('%s black box: wait stop at %x is not a declared wait PC'%(bb_name(entry),exit_regs['pc']))
            waiting=True
        elif exit_regs['pc']!=ret:raise ModelError('%s black box ended at %x, the model expects the return PC %x'%(bb_name(entry),exit_regs['pc'],ret))
    if not waiting and exit_regs['a7']!=(a7+4)&M32:raise ModelError('%s black box changed the stack depth (native exit A7 %x, entry A7 %x)'%(bb_name(entry),exit_regs['a7'],a7))
    for key in REGN+('a7',):M.r[key]=exit_regs[key]
    M.cc=dict(X=None,N=None,Z=None,V=None,C=carry)
    if carry is not None and entry==0x28ae and M.r['a0']!=want_a0:raise ModelError('28ae exit A0 %x differs from the contract formula %x (carry %d)'%(M.r['a0'],want_a0,carry))
    env['bb_log'].append(dict(callee=bb_name(entry),events=hi-lo,waiting=waiting,carry=carry))
    if waiting:
        env['pending']=dict(ret=ret,a7=a7,callee=bb_name(entry),entry=entry)
        raise StopWait(exit_regs['pc'])
    return ret


def run_model(M,pc,end_pc,resume):
    steps=0
    if resume is not None:
        pc=blackbox(M,resume['entry'],resume)
    while True:
        if pc==end_pc:return pc
        steps+=1
        if steps>5000:raise ModelError('model step limit')
        if pc in BLK:
            M.lead(pc);pc=BLK[pc](M);continue
        if pc in BB_ENTRIES:
            M.lead(pc)
            try:pc=blackbox(M,pc)
            except StopWait as w:return w.pc
            continue
        raise ModelError('model has no block for %x'%pc)


def model_step(program,p,declared_sr,pending):
    """The independent model of one native control phase (one frame or one wait release step).  Returns (row,pending_after)."""
    inc=p['incoming'];events=p['events'];leads=p['leads']
    env=dict(nl=leads,events=events,outgoing=p['outgoing'],waiting=p['waiting'],bb_log=[],pending=None)
    M=MM(program,(p['bank_before'],p['ff8_before'],p['ff9_before']),p['ram_before'],inc,env,sr=declared_sr)
    resume=None
    if inc['pc'] in WAIT_PCS:
        if pending is None:return dict(equal=False,model_error='resumed wait without a pending black box'),None
        resume=pending
    row=dict(kind='f1b-model')
    try:
        final_pc=run_model(M,inc['pc'],p['outgoing']['pc'],resume)
    except (ModelError,KeyError,AssertionError,IndexError) as e:
        return dict(equal=False,model_error=repr(e)[:300]),None
    bad=[]
    nl=[(l['pc'],l['regs']) for l in leads];ml=[(l['pc'],l) for l in M.leads]
    if len(ml)!=len(nl):bad.append(dict(what='leader count',model=len(ml),native=len(nl)))
    for i,((mpc,mr),(npc,nr)) in enumerate(zip(ml,nl)):
        if mr!=nr:
            bad.append(dict(what='leader %d'%i,model_pc=hex(mpc),native_pc=hex(npc),differing_registers={k:(hex(mr[k]),hex(nr[k])) for k in mr if mr[k]!=nr.get(k)}));break
    nw=[(e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region']=='ram' and e['access']=='write' and in_f1b(e['pc'])]
    if M.writes!=nw:
        first=next((i for i,(x,y) in enumerate(zip(M.writes,nw)) if x!=y),min(len(M.writes),len(nw)))
        bad.append(dict(what='ordered RAM writes of the F1b code',model_count=len(M.writes),native_count=len(nw),first_difference=first,model=M.writes[first:first+3],native=nw[first:first+3]))
    nr_=[(e['address'],e['size'],e['region']) for e in events if e['region'] in ('fixed','bank') and e['access']=='read' and in_f1b(e['pc'])]
    if M.rom_reads!=nr_:bad.append(dict(what='ordered ROM reads of the F1b code',model=M.rom_reads[:6],native=nr_[:6]))
    np_=[(e['pc'],e['region'],e['address']) for e in events if e['region'] in PORT_REGIONS+('external',) and in_f1b(e['pc'])]
    if np_ or M.ports:bad.append(dict(what='port / external accesses of the F1b code (the contract says none)',native=np_[:6]))
    end_regs=p['outgoing']
    if final_pc!=end_regs['pc']:bad.append(dict(what='final PC',model=hex(final_pc),native=hex(end_regs['pc'])))
    final=dict(M.r)
    if final!={k:end_regs[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(end_regs[k])) for k in final if final[k]!=end_regs[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if M.bank!=p['modeled_bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(p['modeled_bank'])))
    row.update(equal=not bad,leaders=len(M.leads),f1b_ram_writes=len(M.writes),blackbox_ram_writes=M.bb_writes,blackbox=env['bb_log'],mismatches=bad)
    return row,env['pending']


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
        fc.a7_add(-4,'declared direct re-entry: A7 back to the dispatcher slot 1feffc'),W(S,4,FRAME_RET,'declared return LONG 2ac2 at (A7) (the value the previous frame popped)')]


def release_changes(wait):
    if wait['pc']==0x3aea:return [W(0x104d74,2,0xffff,'declared release of the sound-ring wait: tail WORD 104d74 := ffff (<> D1.W)')]
    return [W(0x108d34,2,wait['compared_word'],'declared release of the sprite wait: WORD 108d34 := D4.W')]


def r_after(n,writes):
    def rule(done,ram,cb,o):return list(writes) if done==n else []
    return rule


def r_child(delay=0,value=1):
    """Declared completion of the child e4234 (62(A6) := 1) after `delay` further waiting frames at the 47e22 callback."""
    st=dict(waits=0,fired=False)
    def rule(done,ram,cb,o):
        if st['fired'] or cb!=0x47e22 or ram[0xb92]!=0:return []
        if st['waits']<delay:
            st['waits']+=1;return []
        st['fired']=True;return [W(0x100b92,1,value,'declared host write: child completion BYTE 62(A6) := %02x (the child e4234 end e43fe MOVE.B #1,62(A0), not executed)'%value)]
    return rule


def r_dd44(extra=(),value=0xff):
    """Declared 10dd44 := ff (the area end object ST.B 5d44(A5)) in the first frame boundary at which the 47e70 poll is installed and 10dd44 is 0 (frame 188 for the natural seeds)."""
    st=dict(fired=False)
    def rule(done,ram,cb,o):
        if st['fired'] or cb!=0x47e70 or ram[0xdd44]!=0:return []
        st['fired']=True;return [W(0x10dd44,1,value,'declared host write: BYTE 10dd44 := %02x (the area end object, not executed)'%value)]+list(extra)
    return rule


def plan_frames(program,fx,label,setup=(),rules=(),max_frames=400,frames=None,first_stop=FRAME_RET,first_a7=('abs',S+4),end_alts=(END_STOP,),allow_guard=False):
    """Interactive probe on ONE persistent CPU: frame 0 with the declared setup, then a declared release per wait and a declared re-entry per returned frame (callback LONG at (A6)),
    host-write rules evaluated after every returned frame, until the boundary stop 477ee (or `frames` frames, or a guard).  Returns (steps, last_phase, probe_frames)."""
    o=F1bObserver(program,True);steps=[];frame=0
    try:
        o.prepare(dict(fx,stop_pc=first_stop,checkpoints=[],stop_alts=end_alts))
        step=step_of('%s-frame0'%label,setup,first_stop,first_a7,'return',end_alts)
        while True:
            o.begin_step(step['stop_pc'],[]);o.alt_stops=frozenset(step['alts'])
            o.apply(step['changes']);p=o.run(allow_guard=True);steps.append(step)
            pc=p['outgoing']['pc']
            if p['guard'] is not None and p['guard'].get('problem')=='unsupported_code_target' and p['guard'].get('target')==END_STOP and END_STOP in end_alts:
                # probe only: the alternative boundary stop 477ee is not routed, so the probe CPU reports it as the refused fetch; the declared step stops there (stop_pc = 477ee)
                step['stop_pc']=END_STOP;step['a7']=('abs',S);step['expect']='boundary';p=dict(p,guard=None);return steps,p,frame+1
            if p['guard'] is not None:
                assert allow_guard,(label,p['guard']);step['expect']='guard';return steps,p,frame
            if p['waiting']:
                step['expect']='wait'
                step=step_of('%s-frame%d-release%d'%(label,frame,sum(1 for s in steps if s['label'].startswith('%s-frame%d-release'%(label,frame)))+1),release_changes(p['wait']),first_stop,('abs',S+4),'return',end_alts);continue
            if pc==END_STOP and END_STOP in end_alts:
                step['stop_pc']=END_STOP;step['a7']=('abs',S);step['expect']='boundary';return steps,p,frame+1
            assert pc==step['stop_pc']==FRAME_RET,(label,hex(pc))
            o_=p['outgoing'];assert o_['a6']==A6V or fx.get('free_a6'),(label,hex(o_['a6']));assert o_['a5']==A5V,(label,hex(o_['a5']))
            ram=p['ram_after'];cb=u32(ram,o_['a6']&0xffff)
            frame+=1
            if frames is not None and frame>=frames:return steps,p,frame
            if frame>=max_frames:raise AssertionError('too many frames '+label)
            host=[c for rule in rules for c in rule(frame-1,ram,cb,o_)]
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


def derive_fx(base,label,writes=(),entry=None,regs=None,sr=None,a7=None,a5=None,stack_ret=True,stack_extra=(),ret=FRAME_RET,external=None,note=''):
    """A declared fixture derived from a base fixture: declared initial RAM writes (recorded), declared initial registers / SR / A7 / A5 / entry PC."""
    ram,rec=apply_writes(base['ram'],writes)
    r=dict(base['regs']);r.update(regs or {})
    if a5 is not None:r['a5']=a5
    a7=base['initial_a7'] if a7 is None else a7
    fx=sc.make_fx(label,ram,{k:r[k] for k in KEYS14},(base['bank_state'],base['pvc']),entry if entry is not None else base['entry_pc'],a7,dict(base['seed'],derived_from=base['label'],note=note),
        list(base.get('initial_host_writes',[]))+rec,([(a7,ret.to_bytes(4,'big'))] if stack_ret else [])+list(stack_extra),external=base['external'] if external is None else external,role='declared fixture: '+note)
    fx['regs']['a5']=r['a5'];fx['group']='f1b'
    if sr is not None:fx['sr']=sr
    return fx


def seed_fixture(index):
    s=G['seeds'][index]
    prov=dict(kind='stage_entry_body final ff000 RAM output (recorded original 47a94 body run)',observation_sha256=sc.STAGE_ENTRY_SHA,case_index=index,family=s['family'],phase=s['phase'],ram_file=s['ram_file'],ram_sha256=s['ram_sha256'],
        bank=s['bank'],registers={k:hex(v) for k,v in s['regs'].items()})
    fx=sc.make_fx('seed-%03d'%index,s['ram'],s['regs'],bc.pvc_for(s['bank']),0x47da4,S,prov,(),[(S,FRAME_RET.to_bytes(4,'big'))],
        role='declared 47da4 direct entry: the recorded final RAM and registers of the original stage_entry_body run (SR 2000, A6 = 100b30, A5 = 108000), A7 = 1feffc with the declared dispatcher return LONG 2ac2 at (A7) (the original had ff000)')
    fx['regs']['a5']=A5V;fx['group']='f1b'
    return fx


G={}
ITEMS=[]


def build_spec(program,fx,label,group,prov,steps=None,setup=(),rules=(),frames=None,expect_guard=None,note='',model=True,dump='all',max_frames=400,end_alts=(END_STOP,),first_stop=FRAME_RET,first_a7=('abs',S+4),guard_ok=False,expect_guard_keys=None):
    guard=None
    if steps is None:
        steps,last,nframes=plan_frames(program,fx,label,setup,rules,max_frames=max_frames,frames=frames,allow_guard=expect_guard is not None or guard_ok,end_alts=end_alts,first_stop=first_stop,first_a7=first_a7)
        guard=last['guard']
    else:
        spec=dict(label=label,fixture=fx,steps=steps,guarded=True,guard={},probe=True);ph=run_chain(program,spec,True);guard=ph[-1]['guard']
        for st,p in zip(steps,ph):st.setdefault('expect','wait' if p['waiting'] else ('guard' if p['guard'] is not None else 'return'))
    clean_steps(steps)
    spec=dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,model=model and guard is None,dump=dump,note=note)
    if guard_ok and guard is None:expect_guard=None
    elif guard_ok:expect_guard=dict(expect_guard_keys or {})
    if expect_guard is not None:
        assert guard is not None,(label,'expected a native guard',expect_guard)
        for k,v in expect_guard.items():assert guard.get(k)==v,(label,k,guard)
        spec.update(guarded=True,guard=dict(expect_guard),observed_guard=guard,model=False)
    else:assert guard is None,(label,guard)
    with_checkpoints(program,spec)
    return spec


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
    o=F1bObserver(RUNPROGRAM[0],True)
    try:
        o.prepare(f);q=o.run(allow_guard=bool(p['guard']))
    finally:o.close()
    return core_digest(q)==core_digest(p)


RUNPROGRAM=[None]


def state_sha(p):
    o=p['outgoing'];ports=ports_blob(p['events'])
    h=hashlib.sha256();h.update(b'F1B-FRAME-STATE-v1');h.update(p['ram_after']);h.update(struct.pack('>16I',*[o[k] for k in REG16]));h.update(struct.pack('>II',o['pc'],p['modeled_bank']>>20))
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
            f1b_event_regions=dict(collections.Counter('%s/%s'%(e['region'],e['access']) for e in ev if in_f1b(e['pc']))),
            fresh_equal=fresh[j],model_equal=models[j]['equal'] if models[j] is not None else None)
        if p['guard'] is not None:row['guard']=p['guard']
        dumped=dump_all or (spec.get('dump')=='boundary' and p['step'] in BOUNDARY_FRAMES)
        if dumped:row['dump']=dump_blobs(p)
        rows.append(row)
    return rows


def process_item(program,number,spec):
    t0=time.time()
    RUNPROGRAM[0]=program
    split,control,d_split,d_control=run_spec(program,spec)
    fx=spec['fixture'];models=[None]*len(control);pending=None;model_rows=[]
    if spec.get('model'):
        for j,p in enumerate(control):
            declared=fx.get('sr') if (p['step']==0 and p['phase_in_step']==0) else None
            row,pending=model_step(program,p,declared,pending)
            models[j]=row;model_rows.append(row)
            if not row['equal']:DISCREPANCIES.append(dict(label=spec['label'],kind='model-vs-native',step=p['step'],detail=row.get('model_error') or row['mismatches'][:3]))
    fresh=[]
    for j,p in enumerate(control):
        declared=fx.get('sr') if (p['step']==0 and p['phase_in_step']==0) else None
        fresh.append(fresh_equal(program,fx,p,declared))
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
        observed_guard=spec.get('observed_guard'),steps=len(spec['steps']),split_phases=len(split),control_phases=len(control),frames=len([s for s in spec['steps'] if '-release' not in s['label']]),final_pc='%x'%last['outgoing']['pc'],final_stop_kind=rows[-1]['stop_kind'],
        reproduced_twice=True,continuous_split_equivalent=True,split_digest_sha256=d_split,control_digest_sha256=d_control,condition_file=cfile.name,condition_file_sha256=fsha,
        fresh_frames=len(rows),fresh_frames_equal=sum(1 for x in fresh if x),model_frames=sum(1 for m in models if m is not None),model_frames_equal=sum(1 for m in models if m is not None and m['equal']),
        host_writes=[dict(step=i,changes=[change_row(c) for c in s['changes'] if c['kind']=='ram' and c['address']!=S]) for i,s in enumerate(spec['steps']) if any(c['kind']=='ram' and c['address']!=S for c in s['changes'])],
        instructions=sum(len(p['pcs'])-1 for p in control),dumped_frames=sum(1 for r in rows if 'dump' in r),state_sha256_last=rows[-1]['state_sha256'])
    return dict(number=number,result=res,hits=dict(hits),covered=sorted(covered),facts=facts,seconds=time.time()-t0,runs=RUNS[0],fresh_unequal=unequal,model_unequal=mun)


def condition_facts(spec,control,rows):
    """Per-condition facts used by the contract claims (natural seeds: frame table, entry/exit state)."""
    first=control[0];last=control[-1]
    f=dict(frames=len(control),stops=dict(collections.Counter(r['stop_kind'] for r in rows)))
    ri=first['ram_before'];ro=last['ram_after']
    f['entry']=dict(d681=ri[0xd681],d68e=ri[0xd68e],d683=ri[0xd683],dd44=ri[0xdd44],bf4=u32(ri,0xbf4),bf4_type=u16(ri,0xc04),p1=u32(ri,0xcb8),p2=u32(ri,0xda8),c7c=ri[0xbac],cnt104ca0=u16(ri,0x4ca0))
    f['exit']=dict(d680=ro[0xd680],d681=ro[0xd681],c7c=ro[0xbac],d683=ro[0xd683],b85=ro[0xdb85],b87=ro[0xdb87],cb=u32(ro,0xb30),p734=u32(ro,0xd734),p738=u32(ro,0xd738),d967=ro[0x967],f0e=u16(ro,0xf0e),def7=0,cnt=u16(ro,0x4ca0),g62=ro[0xb92],d68e=ro[0xd68e],dd44=ro[0xdd44],w7a=u16(ro,0xbaa))
    # frame table: consecutive frames with the same leader list and the same stop
    table=[];prev=None
    for i,r in enumerate(rows):
        key=(tuple(r['leaders']),r['stop_kind'],r['callback_after'],r['out_pc'])
        if prev is not None and prev[0]==key:prev[1][1]=i
        else:
            prev=[key,[i,i],r['w7a_after']];table.append(prev)
    f['frame_table']=[dict(frames=[a,b],leaders=list(k[0]),stop=k[1],callback_after=k[2],out_pc=k[3],w7a_first=w) for k,(a,b),w in table]
    f['w7a']={str(i):r['w7a_after'] for i,r in enumerate(rows) if i in (0,29,188,189,236)}
    reg=collections.Counter()
    for r in rows:
        for k,v in r['f1b_event_regions'].items():reg[k]+=v
    f['f1b_regions']=dict(reg)
    return f


# ----------------------------------------------------------------------------------
# Natural seeds: the 142 final ff000 RAM outputs of the recorded original stage_entry_body runs
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


def transition77():
    """Case 77 of the transition observation: the state at the 47da4 boundary (A6 = 102000, A7 = 1feffc, return LONG ff000 on the stack)."""
    obs=json.loads(sc.pin(TRANSITION,TRANSITION_SHA));row=[x for x in obs['results'] if x['index']==77];assert len(row)==1
    ph=row[0]['phases'][-1];assert ph['stop_pc']==0x47da4 and row[0]['selection']['label']=='negative-gate1-bit1'
    folder=TRANSITION.parent;names={k:v for k,v in ph['artifacts'].items() if k.endswith('_ram_after.bin') or k.endswith('_pvc_after.bin')}
    ram=pvc=None
    for name,digest in names.items():
        data=sc.pin(folder/name,digest)
        if name.endswith('_ram_after.bin'):ram=data
        else:pvc=data
    o=ph['outgoing'];assert o['pc']==0x47da4 and o['a6']==0x102000 and o['a7']==S and ph['modeled_bank']==0x200000
    regs={k:o[k] for k in KEYS14+('a5',)}
    prov=dict(kind='transition observation case 77 (negative-gate1-bit1) state at the 47da4 boundary',observation_sha256=TRANSITION_SHA,case_index=77,ram_sha256=sha(ram),pvc_sha256=sha(pvc),
        registers={k:hex(v) for k,v in o.items()},note='synthetic fixture: the RAM is mostly zero, only the partial run to 47de4 is meaningful (contract decision 6)')
    fx=sc.make_fx('transition-case77',ram,regs,((0x200000,0xa0,0x1000),pvc),0x47da4,S,prov,(),[],role='declared 47da4 entry: the recorded transition case 77 output state (A6 = 102000, A7 = 1feffc, return LONG ff000)')
    fx['regs']['a5']=A5V;fx['group']='f1b';return fx


def item_natural(number,item):
    i=item['ref'];program=G['program'];fx=seed_fixture(i)
    prov=fx['seed']
    spec=build_spec(program,fx,'natural-%03d'%i,'natural',prov,rules=[r_dd44()],dump='all' if i in DUMP_SEEDS else 'boundary',note='%s seed %d'%(G['seeds'][i]['family'],i))
    return process_item(program,number,spec)


def item_release(number,item):
    """The 5 release-poisoned-prefix outputs are NOT natural seeds (contract decision 7): WORD 104d8a = 8001 makes the frame helper U1 3c60 CMP.W (A1),D0 read an odd address (an address error on a real 68000).  They are guard rows."""
    i=item['ref'];program=G['program'];fx=seed_fixture(i);prov=dict(fx['seed'],role='guard row (contract decision 7), not a natural seed')
    spec=build_spec(program,fx,'release-guard-%03d'%i,'release-guard',prov,rules=[r_dd44()],guard_ok=True,expect_guard_keys=dict(problem='unsupported_odd_data_access'),note='release-poisoned-prefix output %d: odd WORD access expected'%i)
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


def typed(label,group,seed=0,writes=(),entry=None,regs=None,sr=None,a7=None,a5=None,stack_ret=True,stack_extra=(),ret=FRAME_RET,external=None,setup=(),rules=(),frames=None,expect_guard=None,guard_ok=False,steps=None,
        note='',model=True,max_frames=400,end_alts=(END_STOP,),first_stop=FRAME_RET,first_a7=('abs',S+4),base=None,free_a6=False):
    def make(program):
        b=(base() if base is not None else seed_fixture(seed))
        fx=derive_fx(b,label,writes,entry,regs,sr,a7,a5,stack_ret,stack_extra,ret,external,note)
        if free_a6:fx['free_a6']=True
        prov=dict(kind='declared typed fixture',note=note,base=b['label'],base_provenance=b['seed'],declared_initial_writes=[dict(address=hex(w['address']),size=w['size'],value=hex(w['value']),why=w['why']) for w in writes],
            declared_registers={k:hex(v) for k,v in (regs or {}).items()},declared_sr=sr,declared_a7=a7,declared_a5=a5,entry=hex(fx['entry_pc']),return_long=hex(ret) if stack_ret else None)
        st=steps(program,fx) if steps is not None else None
        rl=rules() if callable(rules) else list(rules)
        return build_spec(program,fx,label,group,prov,st,setup,rl,frames,expect_guard if not guard_ok else None,note,model,'all',max_frames,end_alts,first_stop,first_a7,guard_ok=guard_ok,expect_guard_keys=expect_guard)
    make.label=label;TYPED.append(make)


NODE=A6V


def partial(stop,a7,expect='return'):
    def f(program,fx):return [step_of('partial-to-%x'%stop,[],stop,a7,expect)]
    return f


def define_typed():
    TYPED.clear()
    D68E=lambda:W(0x10d68e,1,1,'declared host write: BYTE 10d68e := 01 (a surviving player node: 47642 / 4766a BSET of the frame helper in the original, not executed here)')
    def alive_rules(delay=0):
        return lambda:[r_after(28,[D68E()]),r_child(delay),r_dd44()]
    c0=lambda v:W(0x104ca0,2,v,'declared initial RAM: WORD 104ca0 := %04x (the 28ae allocation count)'%v)
    # ---- full-length variants of three natural seeds (alive / fail / half), contract "typed 변형"
    for s in (0,118,126):
        typed('alive-%d'%s,'variant',s,rules=alive_rules(0),note='player survives (10d68e := 1 after frame 28), child e4234 allocated, 47e22 waits, child completion 62(A6) := 1 after the waiting frame, 10dd44 := ff at the 47e70 poll')
        typed('fail-%d'%s,'variant',s,writes=[c0(0)],rules=alive_rules(0),note='alive with WORD 104ca0 = 0: both 28ae calls fail (47e0a SCC -> ff, fallback node 100e98, WORD 100f0e written)')
        typed('half-%d'%s,'variant',s,writes=[c0(0x14)],rules=alive_rules(0),note='alive with WORD 104ca0 = 14: the first 28ae (D0 = 0) succeeds, the second (D0 = 14) fails')
    typed('alive-child-wait3-0','variant',0,rules=alive_rules(3),note='alive: the 47e22 wait repeats for 3 further frames (no host write) before the child completion write')
    typed('dfail-0','variant',0,writes=[c0(0)],rules=lambda:[r_dd44()],note='not alive, WORD 104ca0 = 0: the single 28ae (d72fe, D0 = 14) fails; 47e40 writes WORD 100f0e (fallback node)')
    typed('dhalf-0','variant',0,writes=[c0(0x14)],rules=lambda:[r_dd44()],note='not alive, WORD 104ca0 = 14: D0 = 14 >= 14, fails (boundary)')
    typed('dgood-0','variant',0,writes=[c0(0x15)],rules=lambda:[r_dd44()],note='not alive, WORD 104ca0 = 15: D0 = 14 < 15, succeeds (boundary)')
    typed('dd44-early-0','variant',0,writes=[W(0x10dd44,1,0xff,'declared initial RAM: BYTE 10dd44 := ff (already set before the 47e70 poll)')],note='10dd44 already set at frame 188: 236 frames in total')
    typed('c7c-ff-0','variant',0,writes=[W(0x100bac,1,0xff,'declared initial RAM: BYTE 7c(A6) := ff')],rules=lambda:[r_dd44()],note='7c(A6) = ff: 76(d72fe child) = WORD 0100, 10d680 = 00 after the wrap')
    typed('c7c-ff-alive-0','variant',0,writes=[W(0x100bac,1,0xff,'declared initial RAM: BYTE 7c(A6) := ff')],rules=alive_rules(0),note='7c(A6) = ff on the alive path: 76(e4234 child) = WORD 00ff, 76(d72fe child) = WORD 0100')
    typed('exit-8c16-equal-0','variant',0,rules=lambda:[r_dd44(extra=[W(0x107dc2,2,0xe100,'declared host write: WORD 107dc2 := e100'),W(0x107dc4,2,0xe100,'declared host write: WORD 107dc4 := e100'),W(0x107dc6,2,0xe100,'declared host write: WORD 107dc6 := e100')])],
        note='8c16 with the three target WORDs equal to the clamped (E1 << 8) values: 8ca0 immediate RTS (the contract fixture for the same-target path); the natural seeds take the DIVS path')
    # ---- callback re-entries (five callbacks x timer / poll / child values)
    for v in (1,2,0):
        for alive in (0,1):
            typed('cb47de4-7a%d-alive%d'%(v,alive),'callback',0,writes=[W(NODE,4,0x47de4,'declared RAM: callback LONG (A6) := 47de4'),W(NODE+0x7a,2,v,'declared RAM: WORD 7a(A6) := %04x'%v)]+([D68E()] if alive else []),entry=0x47de4,frames=3,
                rules=lambda:[r_child(0)],note='callback 47de4 entered directly, timer 7a = %d (1 pass, 2 wait, 0 wraps to ffff and waits), 10d68e = %d'%(v,alive))
    for v in (0,1,0xff):
        typed('cb47e22-62-%02x'%v,'callback',0,writes=[W(NODE,4,0x47e22,'declared RAM: callback LONG (A6) := 47e22'),W(NODE+0x62,1,v,'declared RAM: BYTE 62(A6) := %02x'%v)],entry=0x47e22,frames=3,
            note='callback 47e22 entered directly, child completion BYTE 62 = %02x'%v)
    for v in (1,2,0):
        typed('cb47e62-7a%d'%v,'callback',0,writes=[W(NODE,4,0x47e62,'declared RAM: callback LONG (A6) := 47e62'),W(NODE+0x7a,2,v,'declared RAM: WORD 7a(A6) := %04x'%v)],entry=0x47e62,frames=3,rules=lambda:[r_dd44()],note='callback 47e62 entered directly, timer 7a = %d'%v)
    for v in (0,0xff):
        typed('cb47e70-dd44-%02x'%v,'callback',0,writes=[W(NODE,4,0x47e70,'declared RAM: callback LONG (A6) := 47e70'),W(0x10dd44,1,v,'declared RAM: BYTE 10dd44 := %02x'%v)],entry=0x47e70,frames=3,
            note='callback 47e70 entered directly, 10dd44 = %02x'%v)
    for v in (1,2,0):
        typed('cb47e92-7a%d'%v,'callback',0,writes=[W(NODE,4,0x47e92,'declared RAM: callback LONG (A6) := 47e92'),W(NODE+0x7a,2,v,'declared RAM: WORD 7a(A6) := %04x'%v)],entry=0x47e92,frames=3,note='callback 47e92 entered directly, timer 7a = %d'%v)
    typed('cb47e92-7a1-c7c-ff','callback',0,writes=[W(NODE,4,0x47e92,'declared RAM: callback LONG (A6) := 47e92'),W(NODE+0x7a,2,1,'declared RAM: WORD 7a(A6) := 0001'),W(NODE+0x7c,1,0xff,'declared RAM: BYTE 7c(A6) := ff')],entry=0x47e92,
        note='47e9a with 7c(A6) = ff: ADDQ.B wraps to 00, BYTE 10d680 := 00, CLR 10d681, BRA 477ee')
    # ---- 1c5b0 player nodes (partial runs 47dba -> 47dc0) and full frames
    pn={'a':[W(0x100cb8,4,0,'declared RAM: LONG 100cb8 := 0 (player node 1 not ready)')],'b':[W(0x100da8,4,0,'declared RAM: LONG 100da8 := 0 (player node 2 not ready)')]}
    pn['both']=pn['a']+pn['b']
    pn['a-other']=[W(0x100cb8,4,0x1234,'declared RAM: LONG 100cb8 := 00001234')]
    pn['a-preset']=pn['a']+[W(0x100d19,1,0x40,'declared RAM: BYTE 61(100cb8) := 40 (bit 6 already set)'),W(0x100d60,1,0x01,'declared RAM: BYTE a8(100cb8) := 01 (bit 0 already set)')]
    pn['both-preset']=pn['both']+[W(0x100d19,1,0xbf,'declared RAM: BYTE 61(100cb8) := bf'),W(0x100e09,1,0xff,'declared RAM: BYTE 61(100da8) := ff'),W(0x100e50,1,0xfe,'declared RAM: BYTE a8(100da8) := fe')]
    for k,w in pn.items():
        typed('player-%s-partial'%k,'player',0,writes=w,entry=0x47dba,steps=partial(0x47dc0,('abs',S)),note='1c5b0 with %s: BSET #6 61(node) and BSET #0 a8(node) when LONG (node) <> 270e; partial run 47dba -> RTS 1c5e8 -> 47dc0'%k)
    for k in ('a','both'):
        typed('player-%s-full'%k,'player',0,writes=pn[k],frames=3,guard_ok=True,note='full frames with player node(s) not ready: the frame helper U6 49b0c calls the slot 1bec0 for ready players only; observed (guard allowed)')
    # ---- carry-consuming blocks entered directly with a declared SR
    for c in (0,1):
        typed('direct-1c5bc-c%d'%c,'direct',0,regs=dict(a0=0x100cb8),entry=0x1c5bc,ret=0x47dc0,sr=0x2000|c,steps=partial(0x47dc0,('abs',S+4)),note='1c5bc entered with declared SR %04x (carry %d), A0 = 100cb8, return LONG 47dc0 at (A7); stop directly after the RTS at 1c5e8'%(0x2000|c,c))
        typed('direct-1c5d8-c%d'%c,'direct',0,regs=dict(a0=0x100da8),entry=0x1c5d8,ret=0x47dc0,sr=0x2000|c,steps=partial(0x47dc0,('abs',S+4)),note='1c5d8 entered with declared SR %04x (carry %d), A0 = 100da8, return LONG 47dc0 at (A7)'%(0x2000|c,c))
        typed('direct-47e0a-c%d'%c,'direct',0,regs=dict(a0=0x100e98),entry=0x47e0a,sr=0x2000|c,frames=2,note='47e0a entered with declared SR %04x (carry %d: 28ae %s), A0 = 100e98'%(0x2000|c,c,'succeeded' if c else 'failed'))
    # ---- transition case 77 (A6 = 102000): partial run to 47de4, full frames observed
    T0=W(0x100c04,2,0,'declared initial RAM: WORD 10(100bf4) := 0000 (case 77 holds f2ee: the stage event node type is nonzero, 2a48 would TRAP #15)')
    typed('transition-case77-partial','transition',base=transition77,entry=0x47da4,stack_ret=False,steps=partial(0x47de4,('abs',S)),expect_guard=dict(problem='unsupported_TRAP'),
        note='transition observation case 77 as recorded (A6 = 102000, A7 = 1feffc, return LONG ff000 untouched): the contract expects a partial run 47da4 -> 47de4, but WORD 100c04 = f2ee is nonzero, so 2a48 reaches TRAP #15 (CONTRACT DISCREPANCY)')
    typed('transition-case77-partial-type0','transition',base=transition77,writes=[T0],entry=0x47da4,stack_ret=False,steps=partial(0x47de4,('abs',S)),
        note='case 77 with the declared WORD 100c04 := 0: the partial run 47da4 -> 47de4 (A6 = 102000, return LONG ff000 untouched) completes')
    typed('transition-case77-full','transition',base=transition77,entry=0x47da4,frames=3,expect_guard=dict(problem='unsupported_TRAP'),free_a6=True,note='case 77 state with the declared dispatcher return LONG 2ac2 at (A7): TRAP #15 at 2a52 as above')
    typed('transition-case77-full-type0','transition',base=transition77,writes=[T0],entry=0x47da4,frames=3,guard_ok=True,free_a6=True,note='case 77 with WORD 100c04 := 0 and the declared return LONG 2ac2 at (A7): full frames observed (synthetic random RAM, guard allowed)')
    # ---- 3af8 sound queue (19db): ring full -> 3aea wait + declared release; 100012 = 1 path with the external read d00046
    ring=[W(0x104d7e,1,0,'declared host write: BYTE 104d7e := 00'),W(0x10f001,1,0x00,'declared host write: BYTE 10f001 := 00 (bit 5 clear)'),W(0x100012,1,0,'declared host write: BYTE 100012 := 00'),
        W(0x104d8a,2,2,'declared host write: sound queue head WORD 104d8a := 0002'),W(0x104d8c,2,0,'declared host write: sound queue tail WORD 104d8c := 0000'),
        W(0x104d82,2,0,'declared host write: queue slot 0 := 0000'),W(0x104d84,2,0x0102,'declared host write: queue slot 1 := 0102'),W(0x104d86,2,0x0304,'declared host write: queue slot 2 := 0304'),W(0x104d88,2,0x0506,'declared host write: queue slot 3 := 0506'),
        W(0x104d76,2,0x10,'declared host write: sound ring write index WORD 104d76 := 0010'),W(0x104d74,2,0x11,'declared host write: sound ring read index WORD 104d74 := 0011 (write index + 1: the ring is full)')]
    typed('sound-ring-full-0','sound',0,rules=lambda:[r_after(28,ring),r_dd44()],note='3af8 with the 19db request: the queue fills, 3be4 dequeues into 3ac8 and the full sound ring makes it wait at 3aea; declared release WORD 104d74 := ffff, then the frame finishes')
    ext=[W(0x100012,1,1,'declared host write: BYTE 100012 := 01'),W(0x10fd82,1,1,'declared host write: BYTE 10fd82 := 01'),W(0x10fe80,1,0,'declared host write: BYTE 10fe80 := 00')]
    for e in (0,0xff):
        typed('sound-external-%02x-0'%e,'sound',0,external=e,rules=lambda:[r_after(28,ext),r_dd44()],note='3af8 request 19db with BYTE 100012 = 1, 10fd82 <> 0, 10fe80 = 0: 3b54 TST.B d00046 external read = %02x'%e)
    typed('a6-102000-seed0','transition',0,regs=dict(a6=0x102000),free_a6=True,frames=40,guard_ok=True,note='natural seed 0 with the controller node at 102000 (the transition observation node): 40 frames observed (guard allowed)')
    # ---- zero-step: stop = entry PC for every block start (state unchanged)
    for pc in sorted(STARTS):
        typed('zero-%x'%pc,'zero-step',0,entry=pc,steps=(lambda program,fx,pc=pc:[step_of('zero-step-%x'%pc,[],pc,('entry',0),'return')]),note='zero-step at the block start %x: stop PC = entry PC, nothing executes, the state must be unchanged'%pc)
    # ---- guards
    G_ODD=dict(problem='unsupported_odd_data_access')
    for pc,label in ((0x47dd8,'WORD write 7a(A6)'),(0x47de4,'WORD read-modify-write 7a(A6)'),(0x47e1c,'LONG write (A6)'),(0x47e56,'WORD write 7a(A6)')):
        typed('guard-odd-a6-%x'%pc,'guard',0,regs=dict(a6=0x100b31),entry=pc,free_a6=True,expect_guard=G_ODD,note='odd A6 (100b31): %s -> address error on the original CPU (checked error, rollback)'%label)
    for pc in (0x47e22,0x47e9a):
        typed('observe-odd-a6-byte-%x'%pc,'guard',0,regs=dict(a6=0x100b31),entry=pc,free_a6=True,guard_ok=True,frames=2,note='odd A6 (100b31) with BYTE-only accesses at %x (62(A6) / 7c(A6)): allowed by the contract; observed (a later WORD / LONG access of the frame helper may fault)'%pc)
    for pc in (0x47e12,0x47e40):
        typed('guard-odd-child-a0-%x'%pc,'guard',0,regs=dict(a0=0x100e99),entry=pc,expect_guard=G_ODD,note='odd child node A0 (100e99): WORD write 76(A0) -> address error')
    typed('guard-rom-child-a0-47e12','guard',0,regs=dict(a0=0x1000),entry=0x47e12,expect_guard=dict(problem='unmapped_or_protected'),note='child node A0 = 1000 (program ROM): WORD write 76(A0) is a ROM write')
    typed('guard-rom-a6-47dd8','guard',0,regs=dict(a6=0x1000),entry=0x47dd8,free_a6=True,expect_guard=dict(problem='unmapped_or_protected'),note='A6 = 1000 (program ROM): WORD write 7a(A6) is a ROM write')
    typed('guard-odd-a7-47da4','guard',0,a7=S+1,first_a7=('abs',S+5),expect_guard=G_ODD,note='A7 = 1feffd (odd): the first JSR pushes an odd LONG')
    typed('guard-a5-zero-47da4','guard',0,a5=0,expect_guard=dict(problem='unmapped_or_protected'),note='A5 = 0: BYTE write 5b85(A5) at 4b6e4 is a ROM write')
    typed('guard-stop-not-477ee','guard',0,writes=[W(NODE,4,0x47e92,'declared RAM: callback LONG (A6) := 47e92'),W(NODE+0x7a,2,1,'declared RAM: WORD 7a(A6) := 0001')],entry=0x47e92,
        steps=(lambda program,fx:[step_of('frame-stop-2ac2-only',[],FRAME_RET,('abs',S+4),'return')]),expect_guard=dict(problem='unsupported_code_target',target=0x477ee),
        note='the last frame run with the stop 2ac2 only: BRA.W 477ee at 47ea8 is refused (unsupported animation machine PC, full rollback); 477ee is the F1c boundary')
    typed('guard-no-2ac2-stop-d72fe','guard',0,writes=[W(NODE,4,0x47de4,'declared RAM: callback LONG (A6) := 47de4'),W(NODE+0x7a,2,1,'declared RAM: WORD 7a(A6) := 0001')],entry=0x47de4,
        steps=(lambda program,fx:[step_of('frame-without-2ac2-stop',[],0x4939c,('abs',S+4),'return')]),expect_guard=dict(problem='unsupported_code_target',target=0xd72fe),
        note='a frame whose stop is NOT 2ac2 (28ae d72fe succeeded): 2ac2 -> 2ab8 -> JSR (A0) enters the child callback d72fe, which has no executor (rollback)')
    typed('guard-no-2ac2-stop-e4234','guard',0,writes=[W(NODE,4,0x47de4,'declared RAM: callback LONG (A6) := 47de4'),W(NODE+0x7a,2,1,'declared RAM: WORD 7a(A6) := 0001'),D68E()],entry=0x47de4,
        steps=(lambda program,fx:[step_of('frame-without-2ac2-stop',[],0x4939c,('abs',S+4),'return')]),expect_guard=dict(problem='unsupported_code_target',target=0xe4234),
        note='the alive path without the 2ac2 stop: the child callback e4234 has no executor (rollback)')
    typed('guard-trap15-cleanup-47da4','guard',0,writes=[W(0x100c04,2,1,'declared RAM: WORD 10(100bf4) := 0001 (the stage event node type is nonzero)')],expect_guard=dict(problem='unsupported_TRAP'),
        note='2a48 with a nonzero type WORD at 10(A0): TRAP #15 (checked error animation cleanup original TRAP15: nonzero object type)')
    typed('guard-bad-return-long','guard',0,writes=[W(NODE,4,0x47e92,'declared RAM: callback LONG (A6) := 47e92'),W(NODE+0x7a,2,2,'declared RAM: WORD 7a(A6) := 0002')],entry=0x47e92,ret=0x4939c,expect_guard=dict(problem='unsupported_code_target',target=0x4939c),
        note='the return LONG at (A7) is 4939c instead of 2ac2: the 480f0 RTS jumps outside every routed range (the stop is 2ac2)')
    typed('guard-28ae-pool-null-47e30','guard',0,writes=[W(0x104c9c,4,0,'declared RAM: LONG 104c9c := 0 (empty free list head with a nonzero count)')],entry=0x47e30,expect_guard=dict(),
        note='28ae succeeds by count (D0 14 < 50) but the free list head is NULL: the original writes through address 0 + c (ROM); not covered by the contract text (observed guard)')


# ----------------------------------------------------------------------------------
# Static checks (byte table, block table, block starts, bundled branches, carry classes)
# ----------------------------------------------------------------------------------
FLOW_ONLY={'lea','movea','pea','jsr','jmp','bsr','bra','rts','nop','btst','bset','bclr','bchg','beq','bne','bcc','bcs','bpl','bmi','bvc','bvs','bge','blt','bgt','ble','bhi','bls',
    'scc','scs','seq','sne','sf','st','shi','sls','svc','svs','spl','smi','sge','slt','sgt','sle'}                    # Scc does not change the CCR on the 68000


def static_checks(program):
    instr=F1B_INSTR;starts=set(STARTS);pcs=sorted(instr)
    blocks={};cur=None
    for lo,hi in F1B_RANGES:
        for pc in [x for x in pcs if lo<=x<hi]:
            if pc in starts:cur=pc;blocks[cur]=[]
            blocks[cur].append(pc)
    rows=[];flow={}
    table={b[0]:b for b in BLOCK_ROWS}
    for start in sorted(blocks):
        raw=b''.join(bytes.fromhex(instr[x]['raw']) for x in blocks[start])
        mn=[instr[x]['mnemonic'].split('.')[0] for x in blocks[start]]
        want=table[start]
        ok=raw==want[1] and len(want[2].split('; '))==len(mn)
        flow[start]=all(m in FLOW_ONLY for m in mn)
        rows.append(dict(start='%x'%start,instructions=len(mn),bytes_equal_table=raw==want[1],instruction_count_equal_table=len(want[2].split('; '))==len(mn),flow_only=flow[start],mnemonics=sorted(set(mn))))
        if not ok:DISCREPANCIES.append(dict(label='static',kind='block-table-vs-rom',start=hex(start)))
    preserve_decoded=sorted(s for s,v in flow.items() if v)
    bundled=[]
    for pc in BUNDLED:
        m=instr[pc]['mnemonic'].split('.')[0];bundled.append(dict(pc='%x'%pc,mnemonic=m,is_conditional_branch=m in ('bne','beq','bcc'),is_block_start=pc in starts))
    traps=[hex(pc) for pc in pcs if instr[pc]['mnemonic'].startswith('trap')]
    absolute=sorted({hex(int(x,16)) for pc in pcs for x in re.findall(r'\$([0-9a-f]+)',instr[pc].get('operands',instr[pc].get('op_str',''))) if len(x)>=5 and instr[pc]['mnemonic'].split('.')[0] not in ('jsr','jmp','bra','bne','beq','bcc')})
    return dict(instructions=len(instr),undecoded=0,block_starts=len(starts),decoded_leaders=34,callbacks=len(CALLBACKS),even_pcs=len(EVEN_PCS),interior_pcs=len(INTERIOR),interior_includes_47e0e=0x47e0e in INTERIOR,
        bundled_branches=bundled,flow_only_decoded=['%x'%x for x in preserve_decoded],flow_only_contract=['%x'%x for x in sorted(PRESERVE)],flow_only_equal_contract=preserve_decoded==sorted(PRESERVE),
        carry_consumers=['%x'%x for x in CONSUMERS],trap_instructions=traps,absolute_data_operands=absolute,bb_entries=['%x'%x for x in BB_ENTRIES],table=TABLE,block_rows=rows)


# ----------------------------------------------------------------------------------
# Claims of the contract checked against the native results
# ----------------------------------------------------------------------------------
EXPECT_FRAME0={0x47da4,0x47daa,0x47db0,0x47dba,0x47dc0,0x47dc6,0x47dd8,0x47de4,0x4b6e4,0x4b6ec,0x1c5b0,0x1c5bc,0x1c5cc,0x1c5d8,0x1c5e8,0x1bee4,0x1bef0,0xca48}
EXPECT_TABLE=[((0,0),EXPECT_FRAME0,'1d'),((1,28),{0x47de4},None),((29,29),{0x47de4,0x47dec,0x47e30,0x47e40,0x47e56,0x47e62},'9f'),((30,187),{0x47e62},None),((188,188),{0x47e62,0x47e6a,0x47e70},None),
    ((189,189),{0x47e70,0x47e78,0x47e86,0x47e92},'2f'),((190,235),{0x47e92},None),((236,236),{0x47e92,0x47e9a},None)]
UNCOVERED_BY_NATURAL=sorted([0x1c5c0,0x1c5dc,0x47df4,0x9056,0x47dfa,0x47e0a,0x47e12,0x47e1c,0x47e22,0x47e2a])


def contract_claims(rows,static,start_cov):
    claims=[]
    def claim(text,ok,evidence,verdict=None):
        claims.append(dict(claim=text,verdict=verdict or ('confirmed' if ok else 'contradicted'),evidence=evidence))
    by={r['result']['label']:r for r in rows};nat=[r for r in rows if r['result']['group']=='natural']
    claim('6 code ranges, 376 bytes, 81 instructions, 0 undecoded, equal to the ROM bytes of the contract table',static['undecoded']==0 and static['instructions']==81,dict(table=static['table']))
    claim('39 block starts = 34 leaders decoded from the original opcodes + 5 callback entries (47de4 47e22 47e62 47e70 47e92); the block table bytes / instruction counts equal the ROM',all(x['bytes_equal_table'] and x['instruction_count_equal_table'] for x in static['block_rows']),dict(decoded_leaders=static['decoded_leaders'],callbacks=static['callbacks'],blocks=len(static['block_rows'])))
    claim('188 even PCs, 149 interior PCs (including 47e0e); the 6 bundled conditional-branch PCs are not block starts',static['even_pcs']==188 and static['interior_pcs']==149 and static['interior_includes_47e0e'] and all(b['is_conditional_branch'] and not b['is_block_start'] for b in static['bundled_branches']),dict(bundled=static['bundled_branches']))
    claim('the 16 carry-preserving blocks are exactly the blocks whose instructions are all flow-only (LEA/MOVEA/JSR/JMP/BRA/RTS/BTST/BSET/BCLR/Bcc/Scc); the 3 carry consumers are 1c5bc 1c5d8 47e0a',static['flow_only_equal_contract'],dict(decoded=static['flow_only_decoded'],contract=static['flow_only_contract']))
    claim('F1b has no TRAP, no PVC / port write and no ROM data read: only RAM accesses by the F1b code (all frames of all conditions)',not static['trap_instructions'] and all(set(k.split('/')[0] for k in r['facts'].get('f1b_regions',{}))<={'ram'} for r in rows if r['result']['model_frames']),
        dict(trap_instructions=static['trap_instructions'],absolute_data_operands=static['absolute_data_operands'],f1b_event_regions=aggregate_regions(rows)))
    # ---- natural seeds
    claim('137 natural seeds (begin outputs); every one runs 237 frames: frames 0..235 stop at 2ac2 (RTS at 480f0), frame 236 at 477ee (BRA.W 47ea8); no Waiting, no guard',
        len(nat)==137 and all(r['result']['frames']==237 and r['result']['final_pc']=='477ee' and r['facts']['stops']=={'return':236,'branch-boundary':1} and not r['result']['guarded'] for r in nat),dict(seeds=len(nat),frames=sum(r['result']['frames'] for r in nat)))
    only=[r for r in nat if [h['step'] for h in r['result']['host_writes']]==[189] and [c[1:] for h in r['result']['host_writes'] for c in h['changes']]==[['10dd44',1,'ff']]]
    claim('the only declared host write of a natural seed is BYTE 10dd44 := ff after frame 188 (before frame 189)',len(only)==len(nat),dict(seeds_with_exactly_that_write=len(only)))
    sig=collections.Counter();sts=set(STARTS)
    for r in nat:
        sig[tuple((tuple(e['frames']),tuple(sorted(int(x,16) for x in e['leaders'] if int(x,16) in sts)),e['w7a_first']) for e in r['facts']['frame_table'])]+=1
    want=tuple((ab,tuple(sorted(st)),w) for ab,st,w in EXPECT_TABLE)
    def match(key):
        return len(key)==len(want) and all(k[0]==w[0] and k[1]==w[1] and (w[2] is None or k[2]=='00'+w[2]) for k,w in zip(key,want))
    ok=len(sig)==1 and match(next(iter(sig)))
    claim('the frame table of the contract (0 / 1..28 / 29 / 30..187 / 188 / 189 / 190..235 / 236 with the F1b block starts per segment and 7a = 1d after frame 0, 9f after 29, 2f after 189) holds for all natural seeds',ok,dict(distinct_tables=len(sig),first=[(t[0],['%x'%x for x in t[1]],t[2]) for t in next(iter(sig))] if sig else None))
    def allof(key,val,section):return all(r['facts'][section][key]==val for r in nat)
    ent=dict(d681=0,d68e=0,dd44=0,bf4_type=0,p1=0x270e,p2=0x270e,c7c=0)
    claim('natural input state: 10d681 = 10d68e = 10dd44 = 0, stage node 100bf4 type WORD 0, both player nodes 270e, 7c(A6) = 0, 104ca0 in {50, 4f, 4a}, 10d683 = 2a',
        all(allof(k,v,'entry') for k,v in ent.items()) and all(r['facts']['entry']['cnt104ca0'] in (0x50,0x4f,0x4a) and r['facts']['entry']['d683']==0x2a for r in nat),dict(bf4=sorted({hex(r['facts']['entry']['bf4']) for r in nat}),cnt=sorted({hex(r['facts']['entry']['cnt104ca0']) for r in nat})))
    ex=dict(d680=1,d681=0,c7c=1,d683=8,b85=0,b87=0,p734=0x1bec0,p738=0x1bec0,d967=0xff,cb=0x47e92)
    claim('natural end state: 10d680 = 1, 10d681 = 0, 7c(A6) = 1, 10d683 = 08, 10db85 = 10db87 = 0, 10d734 = 10d738 = 1bec0, 100967 = ff, (A6) = 47e92',all(allof(k,v,'exit') for k,v in ex.items()),dict(distinct={k:sorted({hex(r['facts']['exit'][k]) for r in nat}) for k in ex}))
    hit=collections.Counter()
    for r in nat:
        for pc in r['hits']:hit[pc]+=1
    unc=sorted(pc for pc in STARTS if not any(hit.get(pc) for _ in (0,)))
    claim('the natural seeds execute 29 of the 39 block starts; the 10 never executed are 1c5c0 1c5dc 47df4 9056 47dfa 47e0a 47e12 47e1c 47e22 47e2a',unc==UNCOVERED_BY_NATURAL,dict(uncovered=['%x'%x for x in unc]))
    allhit=set()
    for r in rows:
        if not r['result']['guarded']:allhit.update(r['hits'])
    claim('every one of the 39 block starts is executed by at least one native condition (typed fixtures cover the 10)',all(pc in allhit for pc in STARTS),dict(not_hit=['%x'%x for x in STARTS if x not in allhit]))
    # ---- typed variants
    def tf(label):return by[label]['facts'] if label in by else None
    for s in (0,118,126):
        a=by.get('alive-%d'%s)
        if a:
            ft={tuple(e['frames']):e for e in a['facts']['frame_table']}
            ok=a['result']['frames']==238 and a['result']['final_pc']=='477ee' and {'47df4','9056','47dfa','28ae','47e0a','47e12','47e1c','47e22'}<=set(ft[(29,29)]['leaders']) and ft[(29,29)]['callback_after']=='47e22' and ft[(30,30)]['leaders'][:3]==['47e22','47e2a','9060']
            claim('alive-%d: frame 29 runs 47dec 47df4 9056 47dfa 28ae 47e0a 47e12 47e1c and waits at 47e22 (callback 47e22); frame 30 runs 47e22 47e2a 9060 47e30; 238 frames to 477ee'%s,ok,dict(frames=a['result']['frames'],frame29=ft[(29,29)]['leaders']))
        for kind,frames,w62 in (('fail',237,0xff),('half',238,None)):
            r=by.get('%s-%d'%(kind,s))
            if r:
                claim('%s-%d: 28ae failure keeps going: WORD 100f0e = 0001 (fallback node 100e98), %d frames%s'%(kind,s,frames,', 62(A6) = ff and no 47e22 wait' if kind=='fail' else ''),r['result']['frames']==frames and r['facts']['exit']['f0e']==1 and (w62 is None or r['facts']['exit']['g62']==w62),dict(frames=r['result']['frames'],f0e=r['facts']['exit']['f0e'],g62=r['facts']['exit']['g62']))
    for label,frames,f0e in (('dfail-0',237,1),('dhalf-0',237,1),('dgood-0',237,0)):
        r=by.get(label)
        if r:claim('%s: single 28ae (D0 = 14) %s; WORD 100f0e = %04x'%(label,'succeeds' if f0e==0 else 'fails (boundary: D0 >= count)',f0e),r['result']['frames']==frames and r['facts']['exit']['f0e']==f0e,dict(frames=r['result']['frames'],f0e=r['facts']['exit']['f0e'],count_after=r['facts']['exit']['cnt']))
    r=by.get('dd44-early-0')
    if r:claim('10dd44 already set at frame 188: 236 frames in total (47e70 passes in frame 188)',r['result']['frames']==236,dict(frames=r['result']['frames']))
    r=by.get('c7c-ff-0')
    if r:claim('7c(A6) = ff: ADDQ.B wraps, BYTE 10d680 = 00 after the last frame',r['facts']['exit']['d680']==0 and r['facts']['exit']['c7c']==0,dict(exit=r['facts']['exit']))
    r=by.get('transition-case77-partial')
    if r:claim('transition case 77 (A6 = 102000) runs a partial run 47da4 -> 47de4 (contract decision 6)',r['result']['final_pc']=='47de4',dict(final_pc=r['result']['final_pc'],guard=r['result']['observed_guard'],
        remark='the recorded case 77 RAM holds WORD 100c04 = f2ee (nonzero): 2a48 at 47db0 executes TRAP #15 at 2a52 (checked error); with the declared WORD 100c04 := 0 the partial run reaches 47de4 (transition-case77-partial-type0)'))
    rel=[r for r in rows if r['result']['group']=='release-guard']
    claim('the 5 release-poisoned-prefix outputs are guard rows (WORD 104d8a = 8001: an odd WORD read in U1 3c60 / the sound path, an address error on a real 68000)',len(rel)==5 and all(r['result']['guarded'] and r['result']['observed_guard'].get('reason_kind')=='odd_word_access' for r in rel),
        dict(rows=[dict(label=r['result']['label'],frames=r['result']['frames'],pc=r['result']['observed_guard'].get('pc'),address=r['result']['observed_guard'].get('address'),size=r['result']['observed_guard'].get('size'),access=r['result']['observed_guard'].get('access')) for r in rel]))
    zs=[r for r in rows if r['result']['group']=='zero-step']
    claim('zero-step at each of the 39 block starts leaves the state unchanged (stop PC = entry PC)',len(zs)==39 and all(r['result']['final_stop_kind']=='zero-step' for r in zs),dict(count=len(zs)))
    tot=dict(conditions=len(rows),frames=sum(r['result']['fresh_frames'] for r in rows),fresh_equal=sum(r['result']['fresh_frames_equal'] for r in rows),model_frames=sum(r['result']['model_frames'] for r in rows),model_equal=sum(r['result']['model_frames_equal'] for r in rows))
    claim('every frame of every condition: the fresh-CPU one-run-one-frame replay equals the chain frame, and the independent model equals the native frame',tot['frames']==tot['fresh_equal'] and tot['model_frames']==tot['model_equal'],tot)
    for c in claims:
        if c['verdict'] in ('contradicted','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    return claims,tot


def aggregate_regions(rows):
    t=collections.Counter()
    for r in rows:
        for k,v in r['facts'].get('f1b_regions',{}).items():t[k]+=v
    return dict(t)


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
LIMITATIONS=['Controlled incoming fixtures (the recorded final RAM of the 137 original stage_entry_body begin runs, declared typed variants), not natural scheduler / gameplay reachability; one machine run is one frame and the next frame is a declared direct re-entry (no scheduler, no children).',
    'Native carry / CCR is never read (SR is unobserved); the carry of 289e / 28ae is computed by the model from the contract formulas and checked by the executed branch path and the SCC write.  Unknown-carry rejection is a C++ property (a CPU always has a CCR): it is not observable natively; known Clear / Set entries are observed with a declared SR.',
    'Wait stops are taken at the FIRST blocked arrival at cda4 / 3aea; the spin loops write nothing.  No Waiting exists in the five F1b frame timers / polls (callback return).  Frame re-entry and host writes are declared steps.',
    'The 5 release-poisoned-prefix outputs reach 477ee in plain Unicorn only if the odd WORD address error is ignored; the observer refuses odd WORD/LONG data accesses (guard unsupported_odd_data_access, reason_kind odd_word_access).',
    'IRQ effects between frames (frame counter, watchdog, palette) are not modelled.  The ordered video / watchdog / PVC port events are instruction accesses, not physical bus cycles.',
    'In-process observer extensions: 3c0006 video port (U5) and a memoized capstone decode of the routed ranges (identical results); no shared tool file is edited.',
    'The model treats 2a48 289e 49c20 28ae 9060 3af8 8c16 and 480bc as replayed black boxes (native exit registers / RAM / PVC writes); only F1b code and the 289e / 28ae carry are modelled independently.',
    'Meaning of 10db85/87, 100967, 107def, 10dd44, player node 61 bit6 / a8 bit0 remains unknown (contract unknown items).']


def main():
    global OUT,BLOBS,CONDDIR
    t_start=time.time()
    dev=os.environ.get('AC_DEV');workers=int(os.environ.get('AC_WORKERS','3'))
    out_dir=Path(os.environ['AC_OUT']) if os.environ.get('AC_OUT') else OUT
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
    G['program']=program;G['seeds']=load_seeds()
    define_typed();G['typed']=TYPED
    ITEMS.clear()
    for s in G['seeds']:ITEMS.append(dict(kind='release' if s['release'] else 'natural',ref=s['index']))
    for i in range(len(TYPED)):ITEMS.append(dict(kind='typed',ref=i))
    def label_of(it):
        return ('natural-%03d'%it['ref'] if it['kind']=='natural' else 'release-guard-%03d'%it['ref'] if it['kind']=='release' else TYPED[it['ref']].label)
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
    start_cov={hex(pc):dict(hits=hits.get(pc,0),conditions=len(hit_cond.get(pc,())),groups=dict(groups.get(pc,{})),first_condition=first.get(pc),in_natural_seeds=groups[pc].get('natural',0)>0,needs_typed_fixture=groups[pc].get('natural',0)==0) for pc in sorted(STARTS)}
    unc=[hex(pc) for pc in STARTS if not hits.get(pc)]
    claims,tot=contract_claims(rows,static,start_cov) if not dev else ([],{})
    by_group=collections.Counter(r['group'] for r in results)
    artifacts={}
    for f in sorted(CONDDIR.iterdir()):artifacts['conditions/'+f.name]=sha(f.read_bytes())
    blob_count=sum(1 for _ in BLOBS.iterdir())
    report=dict(schema_version=1,source=source,inputs=inputs,contract=dict(path=str(CONTRACT),sha256=contract_sha,byte_table_check=TABLE),static_checks=static,
        frame_state_sha256_definition='sha256(b"F1B-FRAME-STATE-v1" || RAM-after(65536) || D0..D7,A0..A7 as 16 big-endian LONGs || PC (LONG) || bank number (LONG) || count of ordered port events (LONG) || ordered port events (BYTE size, LONG address, LONG value each))',
        conditions=len(results),groups=dict(by_group),results=results,condition_files=artifacts,blob_count=blob_count,
        totals=dict(frames=sum(r['fresh_frames'] for r in results),split_phases=sum(r['split_phases'] for r in results),control_phases=sum(r['control_phases'] for r in results),fresh_CPU_chain_runs=sum(r['runs'] for r in rows),
            instructions=sum(r['instructions'] for r in results),dumped_frames=sum(r['dumped_frames'] for r in results),fresh_frames_equal=sum(r['fresh_frames_equal'] for r in results),model_frames=sum(r['model_frames'] for r in results),model_frames_equal=sum(r['model_frames_equal'] for r in results)),
        block_start_coverage=start_cov,block_starts_not_hit=unc,block_starts_needing_typed_fixtures=[k for k,v in start_cov.items() if v['needs_typed_fixture']],covered_PCs=sorted(coverage),block_starts=sorted(STARTS),
        contract_claims=claims,contract_discrepancies=DISCREPANCIES,natural_seed_policy=dict(natural=137,release_guard_rows=5,note='contract decision 7: the 5 release-poisoned-prefix outputs are guard rows; the first run of this tool used all 142 seeds'),
        dump_seeds=list(DUMP_SEEDS),boundary_frames=list(BOUNDARY_FRAMES),rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,observer_extension=ext,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),limitations=LIMITATIONS,failure=None)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    summary=dict(conditions=len(results),groups=dict(by_group),totals=report['totals'],discrepancies=len(DISCREPANCIES),not_hit=unc,claims={v:sum(1 for c in claims if c['verdict']==v) for v in ('confirmed','contradicted','not-reproduced')} if claims else None,
        sha256=sha(path.read_bytes()),tool=tool_sha,seconds=round(time.time()-t_start))
    print(json.dumps(summary))
    return summary


if __name__=='__main__':main()
