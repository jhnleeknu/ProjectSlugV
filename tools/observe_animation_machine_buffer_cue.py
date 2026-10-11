"""Unpatched 480bc frame helper bundle U7 (buffer 4aa88 / 4b784, cue e8a48 / e8ad0 / e8af4 and the cue wrapper 2986) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the script/placement observer U5
(observe_animation_machine_script_placement and through it the scene update U4, motion walk U3, scene core U2, frame helper U1 and the card menu close / fade-card chain:
persistent-CPU Observer with the declared host-change vocabulary RAM write / PC redirect / A7 delta, fresh-twice reproduction, split (stop at the first hit of every
block leader) versus continuous equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every imported tool module, ROM SHA/mtime guard, the
stage-frame / stage-entry-body seed rebuilders), the U6 input observer (its contract ranges) and, read-only, the typed corpora generators of the stage buffer / stage cue
frame observers (build_cases / fixture).  The declared observer extension of U5 (a WORD write to 3c0006 is a 'video' port event) is installed in this process exactly as
U5 does; nothing in the imported modules or tools is edited.

Unit: the 778 contract bytes of docs/analysis/animation-machine-buffer-cue-u7-contract.md (4aa88..4abc0, 4b784..4b82e, e8a48..e8b5a, 2986..299c; 60 block starts).  This
unit completes 480bc: with U1..U6 the whole frame 480bc -> 480f0 RTS runs natively and every frame below is run to the RTS that pops the declared return LONG 2ac2 (A7 = 1feffc
at entry, the work-RAM mirror) or to a declared wait stop.

Wait stops (declared, accepted only at these PCs): cda4 (sprite queue wait, blocked when WORD 108d34 <> D4.W) and 3aea (sound ring wait, blocked when WORD 104d74 = D1.W).  The
stop is taken at the FIRST arrival with the blocked condition true (the original stage-frame observer stops at the second blocked visit; the spin loops write nothing, so the
state is the same).  A stop is taken before the instruction at that PC executes.  Resuming is a declared step: host RAM writes between steps (the hold / release writes of
the stage-frame verifier), then the same CPU continues at the same PC.  Return stops are accepted only directly after the RTS that popped the declared return LONG.

Seeds (all pinned by SHA256, rebuilt in this process):
  stage_frame  artifacts/stage_frame/verification.json: all 96 rows.  The 64 stage-0 rows are rebuilt (initializer seeds + recorded host writes / previous recorded
               native output, every RAM checked against input_sha256) and grouped into 31 chains of consecutive rows that run on ONE persistent CPU (frame re-entry is a declared PC
               redirect + A7 delta; the carried frames take the previous native output without any host change, which is compared with the recorded input outside the stack
               window); the 32 resume rows are declared steps (the recorded hold / release host writes) of the same chains.  Every frame is rebuilt with A7 = 1feffc and the
               declared return LONG 2ac2; the PVC page is zero apart from the two bank registers.  Each row is compared with the recorded original run (14 registers, PC, A7,
               bank, ordered port stream, output RAM outside the stack window, live stack bytes at wait stops, instruction sequence).
  stage_entry  artifacts/stage_entry_body: the original 47a94 body + 480bc tail is re-executed by the original observer; the state at the first execution of 480bc (RAM, 14
               registers, A5, bank, the last PVC register words) is captured as the declared entry of the minimal 480bc frame (142 cases) and the frame is run natively to 2ac2 or to
               a declared wait stop (a declared release then lets the five sound-wait cases finish).  Each is compared with the original tail.
  typed corpora  tools/observe_stage_buffer_frame.build_cases / fixture and tools/observe_stage_cue_frame.build_cases / fixture: declared entries at 4aa88 (return LONG 480d2)
               and e8a48 (return LONG 480ea) with the stack in the work-RAM mirror, plus declared fixtures for the 60 block starts the seeds do not reach.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step record;
a declared initial SR (default 2000, i.e. CCR 0) and the declared initial registers are part of the fixture summary.  The MOVE SR,-(A7) at 2990 is observed as the WORD it
pushes (ordered RAM write); its X/N/Z/V/C bits and system byte are read from that WORD, never from SR.

An independent Python model of the contract (a basic-block machine transcribed instruction by instruction from the original bytes with a complete CCR model, 32-bit register
semantics, explicit word/byte operations, NOT the C++) is compared with each native U7 segment: block-leader sequence with the full register file at every leader, the ordered
RAM writes (including the pushed SR WORD), ordered fixed/bank ROM reads, ordered ports, the final registers and the whole 64KiB RAM image.  The existing callees cd58 (sprite)
and 43e08 (cleanup) are black boxes whose native exit registers and RAM writes are replayed; 28ae (fade card) is modelled in full because its CCR decides the pushed SR WORD.
Any difference is recorded in contract_discrepancies.
"""
import collections
import copy
import ctypes
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import struct
import sys
import time
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_script_placement as sp
import observe_animation_machine_input as inp
from disassemble_program import load_verified_program,disassemble_range
sc=sp.sc;fh=sp.fh;fc=sp.fc;mt=sp.mt;op=sp.op;menu=sp.menu;activation=sp.activation;shared=sp.shared;sfe=sc.sfe;seb=sc.seb;vsf=sp.vsf
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_buffer_cue_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-buffer-cue-u7-contract.md'
CONTRACT_SHA='75e76e8cfb9ed6c9e18d70b9b5a153f0b54104c0d98f118756c7c67f6955ae09'
SCOPE=sc.SCOPE
ROM_SHA=op.ROM_SHA
sha=fc.sha
u8,u16,u32=op.u8,op.u16,sc.u32
S=fc.S                                                      # 1feffc: initial A7 (the return LONG lives here; offset effc of the 64KiB work-RAM image)
M32=0xffffffff
A5V=0x108000
KEYS=shared.isolated.REG_NAMES                              # d0..d7 a0..a6
KEYS14=sc.KEYS14
PORT_REGIONS=fc.PORT_REGIONS
ENTRY=0x480bc
FRAME_RET=0x2ac2                                            # the dispatcher return LONG at A7 = 1feffc
RET_4AA88=0x480d2                                           # JSR 4aa88 at 480cc
RET_E8A48=0x480ea                                           # JSR e8a48 at 480e4
WAIT_PCS=(0xcda4,0x3aea)
STAGE_VERIFICATION=fh.STAGE_VERIFICATION
DISCREPANCIES=[]
INFO=[]

U7_RANGES=((0x4aa88,0x4abc0),(0x4b784,0x4b82e),(0xe8a48,0xe8b5a),(0x2986,0x299c))
U7_ENTRIES=(0x4aa88,0xe8a48)
BB_RANGES=((0xcd50,0xce02),(0x43e08,0x43ea4))                 # black boxes of the model: sprite cd58 (cd50..ce02), cleanup 43e08 / 43e38
RANGE_28AE=(0x28ae,0x2918)
MARK_PCS=(0x4aa88,RET_4AA88,0xe8a48,RET_E8A48)
DIRECT_ENTRIES=(0x2986,0x298e,0x4b784,0xe8af4,0xe8ad0)             # internal unit PCs entered directly with a declared return LONG (other callers of the same blocks)
BB_ENTRY_PCS=(0xcd58,0x43e08)


# ----------------------------------------------------------------------------------
# Contract text (block starts / bundled branches) and byte tables
# ----------------------------------------------------------------------------------
def parse_contract_table(program):
    rows=[];code=[]
    pattern=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (\d+) \| `([0-9a-f]+)…([0-9a-f]+)` \| `([0-9a-f]+)` \|')
    for line in CONTRACT.read_text().splitlines():
        m=pattern.match(line)
        if not m:continue
        lo,hi=int(m.group(1),16),int(m.group(2),16);size=int(m.group(3));raw=m.group(6)
        data=program[lo:hi];ok=data.hex()==raw and hi-lo==size
        assert ok,(hex(lo),hex(hi))
        digest=sha(data)
        assert digest.startswith(m.group(4)) and digest.endswith(m.group(5)),(hex(lo),digest)
        rows.append(dict(range='%x..%x'%(lo,hi),size=size,bytes_equal_to_rom=ok,sha256=digest));code.append((lo,hi))
    assert code==list(U7_RANGES) and sum(h-l for l,h in code)==778,code
    joined=b''.join(program[lo:hi] for lo,hi in code)
    assert sha(joined)=='aa13f52b624d8da72825a6afb522510763c1bacaf6c75cb448cc523e8653c574',sha(joined)
    return rows


def contract_lists():
    """Block starts (60 = 17 + 13 + 28 + 2), bundled branch PCs (24), carry-preserving block starts (15) of the contract text."""
    lines=CONTRACT.read_text().splitlines()
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',text)]
    starts=[];bundled=[];preserve=[]
    for i,line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (60개)**'):
            j=i+1
            while lines[j].startswith('  - '):starts+=pcs(lines[j].split(':',1)[1]);j+=1
        if line.startswith('- **묶인 분기 PC (24개'):bundled=pcs(lines[i+1])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (15개)**'):preserve=pcs(lines[i+1])
    assert len(starts)==len(set(starts))==60,(len(starts),len(set(starts)))
    assert len(bundled)==len(set(bundled))==24,(len(bundled),len(set(bundled)))
    assert len(preserve)==len(set(preserve))==15,len(preserve)
    return starts,bundled,preserve


# ----------------------------------------------------------------------------------
# Observer: U5 observer (3c0006 video port) + declared initial SR, wait stops at cda4 / 3aea, first-hit marks, leader records with the instruction / event index
# ----------------------------------------------------------------------------------
STEP_LIMIT=30000                                           # declared instruction watchdog of the observer for walks without a terminator (the original has none)


class U7Mixin(object):
    def prepare(self,fx):
        super().prepare(fx)
        c=self.cpu;REGS=fc.REGS
        if fx.get('sr') is not None:c.reg_write(REGS['sr'],fx['sr'])
        self.marks=[];self.leads=[];self.wait=None;self.marks_seen=set();self.mine_seen=set();self.total=0
        def cb(cpu,pc,size,user):
            if self.guard is not None:return
            first_cp=pc in self.checkpoints and pc not in self.mine_seen
            if first_cp:self.mine_seen.add(pc)
            stopping=pc==self.stop_pc or (first_cp and not self.continuous)
            if pc in MARK_PCS and pc not in self.marks_seen:
                self.marks_seen.add(pc)
                self.marks.append(dict(pc=pc,pc_index=len(self.pcs)-1,event_index=len(self.events),lead_index=len(self.leads),regs=self.regs(),ram=bytes(self.backing),pvc=bytes(c.mem_read(fc.PVC,8192)),
                    bank=self.bank,ff8=self.ff8,ff9=self.ff9,stopping=stopping))
            if stopping:return
            self.total+=1
            if self.total>STEP_LIMIT:
                self.guard=dict(problem='step_limit',pc=pc,steps=self.total);cpu.emu_stop();return
            if pc in WAIT_PCS:
                a5=cpu.reg_read(REGS['a5'])
                if pc==0xcda4:
                    live=int.from_bytes(cpu.mem_read((a5+0xd34)&M32,2),'big');want=cpu.reg_read(REGS['d4'])&0xffff;blocked=live!=want
                else:
                    live=int.from_bytes(cpu.mem_read((a5-0x328c)&M32,2),'big');want=cpu.reg_read(REGS['d1'])&0xffff;blocked=live==want
                if blocked:
                    self.stop_pc=pc;self.wait=dict(pc=pc,live_word=live,compared_word=want,kind='sprite' if pc==0xcda4 else 'sound');cpu.emu_stop();return
            if pc in LEAD_PCS:
                self.leads.append(dict(pc=pc,regs=self.regs(),pc_index=len(self.pcs)-1,event_index=len(self.events)))
        c.hook_add(UC_HOOK_CODE,cb)
        return self
    def run(self,allow_guard=False):
        self.marks=[];self.leads=[];self.wait=None;self.marks_seen=set();self.mine_seen=set(self.seen)
        r=super().run(allow_guard=allow_guard)
        r.update(marks=self.marks,leads=self.leads,wait=self.wait,waiting=self.wait is not None)
        return r
    def apply(self,changes):
        before=self.regs();expected=dict(before);done=[]
        for change in changes:
            kind=change['kind']
            if kind=='ram':self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
            elif kind=='pc':self.cpu.reg_write(fc.REGS['pc'],change['to']);expected['pc']=change['to']
            elif kind=='a7_add':
                expected['a7']=(before['a7']+change['delta'])&M32;self.cpu.reg_write(fc.REGS['a7'],expected['a7'])
            else:raise AssertionError(kind)
            done.append(dict(change,pc_before=before['pc'],a7_before=before['a7']))
        assert self.regs()==expected
        return done


U7Observer=None


def install_observer():
    """The declared extension of U5 (3c0006 video port) first, then the U7 observer on top of it (wait stops, marks, leader records)."""
    global U7Observer
    if getattr(fc.Observer,'__name__','')!='U7Observer':
        sp.install_video_3c0006()
        U7Observer=type('U7Observer',(U7Mixin,fc.Observer),{})
        fc.Observer=U7Observer
    else:U7Observer=fc.Observer
    return sp.EXTENSION


RANGES=();LEAD_PCS=frozenset();CK_SET=frozenset();U7_STARTS=();U7_BUNDLED=();U7_PRESERVE=();LEADERS_28AE=frozenset();TABLE=[]


def configure(program,out_dir):
    global RANGES,LEAD_PCS,CK_SET,U7_STARTS,U7_BUNDLED,U7_PRESERVE,LEADERS_28AE,TABLE
    ext=install_observer()
    sp.configure(program,out_dir)
    rows,u6=inp.parse_contract_table(program)
    TABLE=parse_contract_table(program)
    U7_STARTS,U7_BUNDLED,U7_PRESERVE=contract_lists()
    decoded=set(fh.leaders_of(program,U7_RANGES))
    assert decoded==set(U7_STARTS),(sorted(map(hex,decoded^set(U7_STARTS))))
    assert not set(U7_BUNDLED)&decoded
    LEADERS_28AE=frozenset(fh.leaders_of(program,(RANGE_28AE,)))
    RANGES=tuple(dict.fromkeys(tuple(sp.RANGES)+u6+fh.RANGES+U7_RANGES))
    LEAD_PCS=frozenset(U7_STARTS)|LEADERS_28AE|frozenset(BB_ENTRY_PCS)
    CK_SET=frozenset(U7_STARTS)|LEADERS_28AE|frozenset((0xcd58,0x43e08,RET_4AA88,RET_E8A48))
    fc.OUT=out_dir;fc.RANGES=RANGES;fc.BOUNDARIES=();fc.KEY_PCS=()
    fh.OUT=out_dir;fh.POOL.clear()
    return ext


def W(address,size,value,why):return fc.ram_write(address,size,value,why)


# ----------------------------------------------------------------------------------
# Chain runner: the fade-card run_condition with declared wait stops
# ----------------------------------------------------------------------------------
RUNS=[0]


def run_chain(program,spec,continuous):
    RUNS[0]+=1
    fx=spec['fixture'];allow=bool(spec.get('guarded'));o=U7Observer(program,continuous);phases=[]
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
                    carry=None,carry_in=None,branch_evidence=[],step_stop_pc=step['stop_pc'],phase_in_step=sum(q['step']==index for q in phases))
                phases.append(p)
                if p['guard'] is not None:break
                if p['waiting']:
                    assert p['outgoing']['pc'] in WAIT_PCS,(spec['label'],hex(p['outgoing']['pc']))
                    break
                assert p['outgoing']['pc']==target,(spec['label'],step['label'],p['outgoing'],hex(target))
                if p['outgoing']['pc']==step['stop_pc']:
                    kind,value=step['a7']
                    want=(first['a7']+value)&M32 if kind=='entry' else value
                    assert p['outgoing']['a7']==want,(spec['label'],step['label'],hex(p['outgoing']['a7']),hex(want))
                    break
                assert p['phase_in_step']<80
            if phases[-1]['guard'] is not None:
                assert allow,(spec['label'],phases[-1]['guard']);assert index==len(spec['steps'])-1
            else:
                expect=step.get('expect')
                if expect=='wait':assert phases[-1]['waiting'],(spec['label'],step['label'],'expected a wait stop',hex(phases[-1]['outgoing']['pc']))
                if expect=='return':assert not phases[-1]['waiting'],(spec['label'],step['label'],'expected the return stop, got a wait at',hex(phases[-1]['outgoing']['pc']))
        if allow:
            if phases[-1]['guard'] is not None or not spec.get('probe'):fc.check_guard(spec,phases[-1])
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
    firsts=[p for i,p in enumerate(phases)]
    assert len(phases)==len(spec['steps']),(spec['label'],len(phases),len(spec['steps']))
    for index,step in enumerate(spec['steps']):
        order=[];entry=phases[index]['pcs'][0]
        for pc in phases[index]['pcs'][1:]:
            if pc in CK_SET and pc not in order and pc!=entry and pc!=step['stop_pc']:order.append(pc)
        step['checkpoints']=order
    return spec


def run_spec(program,spec):
    split=run_chain(program,spec,False)
    assert split==run_chain(program,spec,False),spec['label']
    control=run_chain(program,spec,True)
    assert control==run_chain(program,spec,True),spec['label']
    compare_steps(split,control)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc'] or p['waiting']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc'] or p['waiting']]
    return split,control


# ----------------------------------------------------------------------------------
# Stop evidence: a return stop only directly after the RTS that popped the declared return LONG, a wait stop only at the declared wait PCs directly after the
# fall-through / spin branch of the wait loop (or as a zero-step re-stop of an unchanged wait)
# ----------------------------------------------------------------------------------
def stop_evidence(program,p,origin):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc'];ram=p['ram_after']
    if p['waiting']:
        assert pcs[-1]==pc and pc in WAIT_PCS,(p['label'],hex(pc))
        w=p['wait']
        if len(pcs)==1:return dict(kind='wait',outgoing_pc=pc,previous_pc=None,wait=w,reached_from='zero-step re-stop: the resumed wait is still blocked (stop PC = entry PC, nothing executed)')
        prev=pcs[-2];allowed={0xcda4:{0xcda0:'6700',0xcda8:'66fa'},0x3aea:{0x3ae6:'0241',0x3aee:'67fa'}}[pc]
        assert prev in allowed and program[prev:prev+2].hex()==allowed[prev],(p['label'],hex(prev),hex(pc))
        return dict(kind='wait',outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),wait=w,
            reached_from='%s at %x %s into the %s wait loop at %x (blocked: live WORD %04x %s %04x); the instruction at %x is not executed'%(program[prev:prev+2].hex(),prev,'fell through' if prev in (0xcda0,0x3ae6) else 'looped back',w['kind'],pc,w['live_word'],'<>' if pc==0xcda4 else '=',w['compared_word'],pc))
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(kind='return',outgoing_pc=pc,previous_pc=None,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];a7=o['a7'];inc=origin['incoming']
    assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
    on_stack=[off for off in range(0,64,4) if u32(origin['ram_before'],inc['a7']+off)==pc]
    return dict(kind='return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',return_long_on_stack_at_entry_offsets=on_stack,entry_a7=inc['a7'],
        reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x; the LONG was on the stack at entry offset %s); %x is never executed'%(prev,pc,a7,on_stack[:1],pc))


def annotate(program,phases):
    first={}
    for p in phases:first.setdefault(p['step'],p)
    for p in phases:p['stop_evidence']=stop_evidence(program,p,first[p['step']])


# ----------------------------------------------------------------------------------
# Storage
# ----------------------------------------------------------------------------------
POOL={}


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def ports_blob(events):return b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS)


def compact(items,key=None,limit=2000):
    """Long loop traces (the unbounded e8ae0 walk) are stored as the first entries plus per-PC counts."""
    if len(items)<=limit:return items
    f=key or (lambda x:x);counts=collections.Counter(f(x) for x in items)
    return dict(truncated=True,count=len(items),first=items[:200],by_pc={hex(k):v for k,v in sorted(counts.items())})


def phase_row(j,p,artifacts,keys,snapshots):
    return dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
        host_changes=p['host_changes'],carry_in=p['carry_in'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
        waiting=p['waiting'],wait=p['wait'],carry=p['carry'],branch_evidence=p['branch_evidence'],guard=p['guard'],snapshots=snapshots,counts=fc.counts(p['events']),
        key_pcs=compact([pc for pc in p['pcs'] if pc in keys]),pc_count=len(p['pcs']),artifacts=artifacts,stop_evidence=p['stop_evidence'],
        marks=[dict(pc=m['pc'],pc_index=m['pc_index'],event_index=m['event_index'],regs=m['regs'],ram_sha256=sha(m['ram']),bank=m['bank']) for m in p['marks']],
        leaders=compact([dict(pc=l['pc'],pc_index=l['pc_index'],event_index=l['event_index']) for l in p['leads']],key=lambda l:l['pc']))


def store(prefix,phases,keys,files=True):
    """files=True: every payload is written (RAM before/after, PVC, ports, trace, checkpoint snapshots); files=False: the payload SHA256 values are recorded without writing files."""
    rows=[]
    for j,p in enumerate(phases):
        stem='%s_phase_%03d'%(prefix,j)
        payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
            stem+'_ports.bin':ports_blob(p['events']),
            stem+'_trace.json':(json.dumps({k:p[k] for k in ('pcs','events','guard')},indent=2)+'\n').encode()}
        snapshots=[]
        for k,snapshot in enumerate(p['snapshots']):
            names={}
            for field in ('ram','pvc'):
                name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
            snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
        hashes={name:(write_payload(name,data) if files else sha(data)) for name,data in payloads.items()}
        rows.append(phase_row(j,p,hashes,keys,snapshots))
    return rows


# ----------------------------------------------------------------------------------
# Comparison with the recorded original runs (flat-map observers: the stack lives outside the 64KiB image, here it is the work-RAM mirror at offset effc)
# ----------------------------------------------------------------------------------
def stack_window(phases,ram_in=None):
    """[lo,0f000) of the 64KiB image: the bytes the live stack (A7 <= 1feffc+4) may have used in the machine layout.  lo = lowest stack-region write of the phases (at most eff0)."""
    writes=[e['address'] for p in phases for e in p['events'] if e['region']=='ram' and e['access']=='write' and e['address']>=0x1f0000]
    lo=(min(writes)&0xffff) if writes else 0xf000
    return min(lo,0xeff0)


def recorded_diff(ram_native,ram_recorded,lo):
    return [k for k in range(0x10000) if ram_native[k]!=ram_recorded[k] and not lo<=k<0xf000]


def compare_stage_row(step_index,history,phases_of_step,row,rowfile_dir):
    """One recorded stage-frame row versus the native step: 14 registers, PC (ff000 -> 2ac2), A7, bank, ordered port stream, output RAM outside the stack window (lowest
    stack-region write of the whole chain so far), live stack bytes below the return slot at a wait, instruction sequence (the recorded run stops at the SECOND blocked
    visit, the native stop is the first: the native PCs are a prefix)."""
    p=phases_of_step[-1];o=p['outgoing'];res=row['result'];rec_ram=(rowfile_dir/row['ram_file']).read_bytes();assert sha(rec_ram)==row['ram_sha256']
    rec_ports=(rowfile_dir/row['ports_file']).read_bytes();assert sha(rec_ports)==row['ports_sha256']
    lo=stack_window(history);diff=recorded_diff(p['ram_after'],rec_ram,lo)
    events=[e for q in phases_of_step for e in q['events']];blob=ports_blob(events)
    pcs=[pc for q in phases_of_step for pc in q['pcs'][:-1]]+p['pcs'][-1:]
    rec_pcs=row['pcs'];rec_final={0xff000:FRAME_RET}.get(row['final_pc'],row['final_pc'])
    if p['waiting']:pcs_ok=rec_pcs[:len(pcs)]==pcs and rec_final==o['pc']
    else:pcs_ok=rec_pcs[:-1]==pcs[:-1] and rec_final==o['pc']
    n=S+4-o['a7'];rec_stack=bytes.fromhex(row['stack_hex'])
    live=bytes(p['ram_after'][(o['a7']&0xffff):(S&0xffff)]) if n>4 else b'';rec_live=rec_stack[len(rec_stack)-n:len(rec_stack)-4] if n>4 else b''
    out=dict(row=step_index,recorded_label=row['label'],instructions_native=len(pcs)-1 if not p['waiting'] else len(pcs),instructions_recorded=len(rec_pcs)-1 if rec_final==FRAME_RET else len(rec_pcs),
        pcs_equal_or_prefix=pcs_ok,registers_equal=all(o[k]==res[k] for k in KEYS14),final_pc_equal=rec_final==o['pc'],final_a7_equal=o['a7']==row['final_a7'],bank_equal=p['modeled_bank']==res['bank']*0x100000,
        ports_equal=blob==rec_ports,port_count=len(blob)//9,ram_equal_outside_stack_window=not diff,ram_differing_bytes=len(diff),stack_window=[hex(0x100000+lo),hex(0x10f000)],
        live_stack_equal=live==rec_live,live_stack_bytes=len(live),first_diff=[(hex(0x100000+k),p['ram_after'][k],rec_ram[k]) for k in diff[:6]],
        waiting=p['waiting'],recorded_stage=res['stage'],incoming_stage=row['incoming']['stage'],return_slot_native=u32(p['ram_after'],S&0xffff),return_slot_recorded=int.from_bytes(rec_stack[-4:],'big'))
    out['ok']=all(out[k] for k in ('pcs_equal_or_prefix','registers_equal','final_pc_equal','final_a7_equal','bank_equal','ports_equal','ram_equal_outside_stack_window','live_stack_equal'))
    return out


# ----------------------------------------------------------------------------------
# Stage-frame seeds -> 31 chains
# ----------------------------------------------------------------------------------
CHAIN_ROWS=[(0,15),(16,19),(20,23),(24,27),(28,31),(32,35),(36,39),(40,40),(41,41),(42,42),(43,46),(47,49),(50,52),(53,53),(54,54),(55,55),(56,56)]+[(57+3*k,59+3*k) for k in range(10)]+[(87,90),(91,93),(94,94),(95,95)]
assert len(CHAIN_ROWS)==31 and sum(b-a+1 for a,b in CHAIN_ROWS)==96


def row_changes(row):
    return [W(w['address'],len(w['hex'])//2,int(w['hex'],16),'declared host write of the stage-frame verifier row "%s" (previous %s)'%(row['label'],w['previous'])) for w in row['host_writes']]


def stage_chain_specs(program):
    ver,rows_in=sc.stage_frame_inputs(program);rows=ver['results'];assert len(rows)==96
    meta=ver['seed_metadata']
    for key in ('frame_inventory','initialization_observation','initialization_verification'):
        f=ROOT/meta[key+'_file'];sc.pin(f,meta[key+'_sha256'])
    ram_of={index:(ram,how) for index,r,ram,how in rows_in};folder=STAGE_VERIFICATION.parent
    specs=[]
    for a,b in CHAIN_ROWS:
        row0=rows[a];assert row0['incoming']['stage']==0 and a in ram_of
        ram,how=ram_of[a];regs14=[row0['incoming'][k] for k in vsf.KEYS];bank=row0['incoming']['bank']
        hw=[dict(address=w['address'],size=len(w['hex'])//2,value=int(w['hex'],16),previous=w['previous'],why='declared host write of the stage-frame verifier (row "%s"), already applied in the rebuilt seed RAM'%row0['label']) for w in row0['host_writes']]
        prov=dict(kind='stage-frame row chain',rows=[a,b],first_label=row0['label'],rebuilt_from=how,input_sha256=row0['input_sha256'],verification_sha256=sc.STAGE_FRAME_SHA,
            registers=[hex(x) for x in regs14],bank=bank,external=row0['external'],labels=[rows[k]['label'] for k in range(a,b+1)])
        fx=fh.make_fixture('rows%02d-%02d'%(a,b),ram,regs14,bank,prov,hw);fx['external']=row0['external'];fx['group']='stage-frame'
        steps=[]
        for k in range(a,b+1):
            r=rows[k];inc=r['incoming'];waiting=r['result']['stage']!=0
            if k==a:changes=[]
            elif inc['stage']==0:changes=[fc.pc_to(ENTRY,'frame re-entry (the carried frame): PC only, registers / RAM / stack are the previous native outputs'),fc.a7_add(-4,'frame re-entry: A7 back to the dispatcher slot 1feffc'),
                W(S,4,FRAME_RET,'declared return LONG 2ac2 at 1feffc (same value the previous frame popped)')]
            else:changes=row_changes(r)
            step=dict(label='row%02d-%s'%(k,r['label']),changes=changes,stop_pc=FRAME_RET,checkpoints=[],a7=('abs',S+4),expect='wait' if waiting else 'return',recorded=k)
            steps.append(step)
        spec=dict(label='rows%02d-%02d-%s'%(a,b,row0['label']),group='stage-frame',fixture=fx,steps=steps,provenance=prov,recorded_rows=list(range(a,b+1)),model=True,store='all')
        specs.append(spec)
    return specs,rows,folder,dict(verification_file=str(STAGE_VERIFICATION),verification_sha256=sc.STAGE_FRAME_SHA,rows=len(rows))


# ----------------------------------------------------------------------------------
# stage_entry_body first frames: capture of the original run at the first execution of 480bc
# ----------------------------------------------------------------------------------
class EntryCapture(object):
    """Original 47a94 body + 480bc tail (observe_stage_entry_body.Observer): the state at the first execution of 480bc and the final state of the tail."""
    def __init__(self,program):
        self.program=program;self.obs=seb.Observer(program);self.entry=None;self.initial_bank=2
        self.obs.cpu.hook_add(UC_HOOK_CODE,self.hit,begin=ENTRY,end=ENTRY)
    def hit(self,cpu,address,size,user):
        if self.entry is not None:return
        m=seb.m;o=self.obs;a7=cpu.reg_read(m.UC_M68K_REG_A7)
        self.entry=dict(ram=bytes(cpu.mem_read(seb.BASE,0x10000)),regs={k:cpu.reg_read(r)&M32 for k,r in zip(seb.KEYS,seb.REGS)},a7=a7,a5=cpu.reg_read(m.UC_M68K_REG_A5)&M32,
            stack=bytes(cpu.mem_read(a7,seb.STACK+4-a7)),bank=o.bank,pvc_raw=sp.su.last_pvc_words(o.ports,self.initial_bank),n_pcs=len(o.pcs),n_ports=len(o.ports),prev_pc=o.pcs[-2])
    def run(self,case):
        o=self.obs;m=seb.m;ram,state,meta=seb.prepare_case(ROOT,self.program,case);self.entry=None;self.initial_bank=state['bank'];o.prepare(ram,state);cpu=o.cpu
        o.external,o.wait_visits,o.error=0,0,None
        for values in (o.pcs,o.writes,o.ports,o.reads,o.bank_reads,o.boundaries,o.prefix):values.clear()
        cpu.emu_start(cpu.reg_read(m.UC_M68K_REG_PC),0xffffff,count=2000000)
        assert o.error is None,o.error
        e=self.entry;assert e is not None and e['a7']==seb.STACK and e['a5']==A5V and e['prev_pc'] is not None and int.from_bytes(e['stack'],'big')==seb.RETURN,(hex(e['a7']),e['stack'].hex())
        end=dict(ram=bytes(cpu.mem_read(seb.BASE,0x10000)),pc=cpu.reg_read(m.UC_M68K_REG_PC),a7=cpu.reg_read(m.UC_M68K_REG_A7),regs={k:cpu.reg_read(r)&M32 for k,r in zip(seb.KEYS,seb.REGS)},
            ports=list(o.ports[e['n_ports']:]),pcs=list(o.pcs[e['n_pcs']-1:]),bank=o.bank,input_sha256=sha(ram))
        return e,end


def entry_fixture(name,st,prov):
    raw8,raw9=st['pvc_raw'];bank,ff8,ff9=sp.pvc_bank_update(raw8,raw9);assert bank==st['bank']*0x100000,(hex(bank),st['bank'])
    fx=sc.make_fx(name,st['ram'],st['regs'],((bank,ff8,ff9),sc.pvc_page(raw8,raw9)),ENTRY,S,prov,(),[(S,FRAME_RET.to_bytes(4,'big'))],
        role='declared 480bc entry captured at the first execution of 480bc of the original 47a94 body + tail run: RAM, 14 registers, A5 = 108000, PVC bank words; A7 = 1feffc with the declared return LONG 2ac2 (the original had ff000)')
    fx['group']='stage-entry';return fx


def release_step(wait):
    """Declared release of a wait stop: the sound ring tail WORD 104d74 := ffff (as the stage-frame verifier release) or the sprite queue consumer WORD 108d34 := D4.W."""
    if wait['pc']==0x3aea:return [W(0x104d74,2,0xffff,'declared release of the sound-ring wait: tail WORD 104d74 := ffff (<> D1.W, as the stage-frame verifier release rows)')]
    return [W(0x108d34,2,wait['compared_word'],'declared release of the sprite wait: WORD 108d34 := D4.W')]


def dynamic_steps(program,fx,label_prefix,limit=8):
    """Probe run: add one declared release step per wait stop until the frame returns."""
    steps=[dict(label=label_prefix+'-frame',changes=[],stop_pc=FRAME_RET,checkpoints=[],a7=('abs',S+4))]
    for _ in range(limit):
        spec=dict(label=label_prefix,fixture=fx,steps=steps)
        ph=run_chain(program,spec,True)
        if not ph[-1]['waiting']:
            for st,p in zip(steps,ph):st['expect']='wait' if p['waiting'] else 'return'
            return steps
        steps.append(dict(label='%s-release-%d'%(label_prefix,len(steps)),changes=release_step(ph[-1]['wait']),stop_pc=FRAME_RET,checkpoints=[],a7=('abs',S+4)))
    raise AssertionError('too many waits '+label_prefix)


def compare_entry(history,p,end):
    o=p['outgoing'];lo=stack_window(history);diff=recorded_diff(p['ram_after'],end['ram'],lo)
    blob=ports_blob(p['events']);rec_blob=b''.join(struct.pack('>BII',*t) for t in end['ports'])
    pcs=p['pcs'];rec_pcs=end['pcs'];rec_final={seb.RETURN:FRAME_RET}.get(end['pc'],end['pc'])
    pcs_ok=(rec_pcs[:len(pcs)]==pcs if p['waiting'] else rec_pcs[:-1]==pcs[:-1]) and rec_final==o['pc']
    n=S+4-o['a7'];rec_stack=None
    out=dict(instructions_native=len(pcs)-1 if not p['waiting'] else len(pcs),instructions_original=len(rec_pcs)-1 if rec_final==FRAME_RET else len(rec_pcs),pcs_equal_or_prefix=pcs_ok,
        registers_equal=all(o[k]==end['regs'][k] for k in KEYS14),final_pc_equal=rec_final==o['pc'],bank_equal=p['modeled_bank']==end['bank']*0x100000,ports_equal=blob==rec_blob,port_count=len(blob)//9,
        ram_equal_outside_stack_window=not diff,ram_differing_bytes=len(diff),stack_window=[hex(0x100000+lo),hex(0x10f000)],first_diff=[(hex(0x100000+k),p['ram_after'][k],end['ram'][k]) for k in diff[:6]],
        final_a7=hex(o['a7']),original_final_a7=hex(end['a7']),waiting=p['waiting'])
    out['ok']=all(out[k] for k in ('pcs_equal_or_prefix','registers_equal','final_pc_equal','bank_equal','ports_equal','ram_equal_outside_stack_window'))
    return out


# ----------------------------------------------------------------------------------
# Independent model: a basic-block machine (transcription of the original instructions between two block leaders; every block ends with exactly one control
# transfer).  A complete CCR is kept (X N Z V C, None = unknown) because the WORD that 2990 pushes is the SR image.  Calls push the return LONG, RTS pops it, so
# call / return pairing is checked by the live stack exactly as on the CPU.  cd58 (sprite) and 43e08 (cleanup) are black boxes: their native exit registers and
# RAM writes are replayed.  28ae (fade card) is modelled in full (its CCR decides the pushed WORD).
# ----------------------------------------------------------------------------------
ModelError=fh.ModelError
BLK7={}


def blk7(*pcs):
    def deco(fn):
        for pc in pcs:
            assert pc not in BLK7,hex(pc);BLK7[pc]=fn
        return fn
    return deco


def bmask(bits):return (1<<bits)-1
def msb(v,bits):return (v>>(bits-1))&1
def sx(v,bits):
    v&=bmask(bits);return v-(1<<bits) if v>>(bits-1) else v


class M7(sc.U2Machine):
    def __init__(self,program,bank_state,ram,regs,env,sr=None):
        super().__init__(program,bank_state,ram,regs)
        self.env=env;self.sys=0x20;self.cc=dict(X=None,N=None,Z=None,V=None,C=None);self.sr_images=[];self.pending_sr=[];self.initial_sr=sr
        if sr is not None:
            self.sys=sr>>8;self.cc=dict(X=(sr>>4)&1,N=(sr>>3)&1,Z=(sr>>2)&1,V=(sr>>1)&1,C=sr&1)
    def lead(self,pc):
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)
    # ---- flags
    def nz(self,v,bits):                               # MOVE / MOVEQ / TST / OR / AND / EORI / SWAP: N Z, V = C = 0
        v&=bmask(bits);self.cc.update(N=msb(v,bits),Z=int(v==0),V=0,C=0)
    def cmpf(self,d,s,bits):                           # CMP / CMPA / CMPI: d - s, X unchanged
        m=bmask(bits);d&=m;s&=m;r=(d-s)&m
        self.cc.update(N=msb(r,bits),Z=int(r==0),V=(((d^s)&(d^r))>>(bits-1))&1,C=int(d<s));return r
    def subf(self,d,s,bits):                           # SUB / SUBI / SUBQ / NEG: X = C = borrow
        m=bmask(bits);d&=m;s&=m;r=(d-s)&m;c=int(d<s)
        self.cc.update(X=c,N=msb(r,bits),Z=int(r==0),V=(((d^s)&(d^r))>>(bits-1))&1,C=c);return r
    def addf(self,d,s,bits):                           # ADD / ADDQ: X = C = carry
        m=bmask(bits);d&=m;s&=m;r=(d+s)&m;c=int(d+s>m)
        self.cc.update(X=c,N=msb(r,bits),Z=int(r==0),V=(((~(d^s))&(d^r))>>(bits-1))&1,C=c);return r
    def testbit(self,v,bit):self.cc['Z']=int((v>>bit)&1==0)
    def lslf(self,v,n,bits):                          # LSL by an immediate: X = C = last bit out, V = the MSB changed during the shifts
        m=bmask(bits);r=v&m;c=0;vf=0
        for _ in range(n):
            c=msb(r,bits);nr=(r<<1)&m
            if msb(nr,bits)!=msb(r,bits):vf=1
            r=nr
        self.cc.update(X=c,C=c,N=msb(r,bits),Z=int(r==0),V=vf);return r
    def flag(self,name):
        v=self.cc[name]
        if v is None:raise ModelError('branch on an unknown %s flag'%name)
        return v
    def sr_word(self):
        word=self.sys<<8;mask=0xffe0                       # bits 5..7 of the CCR byte are always 0
        for name,bit in (('X',4),('N',3),('Z',2),('V',1),('C',0)):
            v=self.cc[name]
            if v is not None:word|=v<<bit;mask|=1<<bit
        return word,mask
    def set_sr(self,word):
        self.sys=word>>8
        for name,bit in (('X',4),('N',3),('Z',2),('V',1),('C',0)):self.cc[name]=(word>>bit)&1
    # ---- helpers
    def rb(self,off):return self.rd(self.a5(off),1)
    def wb(self,off,v):self.wr(self.a5(off),1,v)
    def setb(self,reg,v):self.lb(reg,v)
    def postinc(self,reg,n):
        a=self.r[reg];self.r[reg]=(a+n)&M32;return a


def swap32(v):return ((v<<16)|(v>>16))&M32


# ---- 4aa88 frame buffer
@blk7(0x4aa88)
def m4aa88(M):
    v=M.rd(0x10f001,1);M.testbit(v,7)
    return 0x4aafe if M.flag('Z')==1 else 0x4aa94
@blk7(0x4aa94)
def m4aa94(M):
    M.push32(M.r['a6']);M.nz(M.r['a6'],32)
    M.r['a4']=0x10daf8;M.r['d7']=0;M.nz(0,32);return 0x4aa9e
@blk7(0x4aa9e)
def m4aa9e(M):
    M.r['a6']=M.rd(M.r['a4'],4);M.r['a0']=M.rd((M.r['a4']+4)&M32,4)
    M.cmpf(M.r['a6'],0,32);return 0x4aaee if M.flag('Z') else 0x4aaac
@blk7(0x4aaac)
def m4aaac(M):
    M.cmpf(M.r['a0'],0,32);return 0x4aaee if M.flag('Z') else 0x4aab4
@blk7(0x4aab4)
def m4aab4(M):
    M.lb('d6',M.rd((M.r['a6']+0x6d)&M32,1));M.nz(M.r['d6']&0xff,8)
    M.lb('d6',M.r['d6']&0x0f);M.nz(M.r['d6']&0xff,8)
    M.cmpf(M.r['d7'],M.r['d6'],8);return 0x4aaee if not M.flag('Z') else 0x4aac2
@blk7(0x4aac2)
def m4aac2(M):
    M.push32(M.r['a4']);M.nz(M.r['a4'],32)
    M.push16(M.r['d7']&0xffff);M.nz(M.r['d7'],16)
    M.r['a0']=(M.r['a0']+4)&M32
    M.r['d7']=0x122b;M.nz(0x122b,32)
    return M.call(0x4b784,0x4aad4)
@blk7(0x4aad4)
def m4aad4(M):
    M.lw('d7',M.pop16());M.nz(M.r['d7'],16)
    M.r['a4']=M.pop32()
    M.ww(-0x7ff0,0);M.nz(0,16)
    M.port(0x2ffff2,0x1000);M.nz(0x1000,16)
    M.port(0x2ffff0,0);M.nz(0,16)
    return 0x4aaee
@blk7(0x4aaee)
def m4aaee(M):
    M.lw('d7',M.addf(M.r['d7'],1,16))
    M.r['a4']=(M.r['a4']+8)&M32
    M.cmpf(M.r['a4'],0x10db78,32);return 0x4aa9e if M.flag('C') else 0x4aafc
@blk7(0x4aafc)
def m4aafc(M):
    M.r['a6']=M.pop32();return 0x4aafe
@blk7(0x4aafe)
def m4aafe(M):
    M.r['d7']=0;M.nz(0,32)
    M.r['a0']=M.rl(0x5c88)
    for _ in range(16):
        a=M.r['a0'];w=M.rd(a,2);r=w>>1;M.wr(a,2,r);M.r['a0']=(a+2)&M32
        M.cc.update(X=w&1,C=w&1,N=0,Z=int(r==0),V=0)
    M.cmpf(M.r['a0'],0x10dc88,32);return 0x4ab32 if M.flag('C') else 0x4ab2e
@blk7(0x4ab2e)
def m4ab2e(M):
    M.r['a0']=M.a5(0x5b88);return 0x4ab32
@blk7(0x4ab32)
def m4ab32(M):
    M.wl(0x5c88,M.r['a0']);M.nz(M.r['a0'],32)
    v=M.rb(0x5b85);M.wb(0x5b84,v);M.nz(v,8)
    M.wb(0x5b85,0);M.nz(0,8)
    v=M.rb(0x5b87);M.wb(0x5b86,v);M.nz(v,8)
    M.wb(0x5b87,0);M.nz(0,8)
    M.testbit(M.rd(0x10f001,1),0);return 0x4ab74 if M.flag('Z') else 0x4ab5a
@blk7(0x4ab5a)
def m4ab5a(M):
    M.lb('d0',M.rd(0x104cab,1));M.nz(M.r['d0']&0xff,8)
    M.lb('d0',(M.r['d0']&0xff)|M.rd(0x104cb1,1));M.nz(M.r['d0']&0xff,8)
    M.lb('d0',M.r['d0']&0x80);M.nz(M.r['d0']&0xff,8)
    return 0x4ab74 if M.flag('Z') else 0x4ab6e
@blk7(0x4ab6e)
def m4ab6e(M):
    M.wb(0x5b84,0xff);M.nz(0xff,8);return 0x4ab74
@blk7(0x4ab74)
def m4ab74(M):
    M.r['a4']=M.a5(0x5746);M.r['a3']=M.a5(0x5918)
    a=M.a5(0x5744);v=M.rd(a,1);M.testbit(v,7);M.wr(a,1,v^0x80)
    return 0x4ab88 if not M.flag('Z') else 0x4ab86
@blk7(0x4ab86)
def m4ab86(M):
    M.r['a3'],M.r['a4']=M.r['a4'],M.r['a3'];return 0x4ab88
@blk7(0x4ab88)
def m4ab88(M):
    M.r['d1']=M32;M.nz(M32,32)                                                                            # MOVEQ #-1,D1
    M.wr((M.r['a4']+0x1d0)&M32,2,0);M.nz(0,16)                                                            # CLR.W 1d0(A4)
    for k in range(8):M.r['d%d'%k]=0
    M.nz(0,32)
    M.r['a4']=(M.r['a4']+0xd0)&M32
    for count in (8,8,8,8,8,8,4):                                                                          # MOVEM.L D0-D7,-(A4) x6 ; MOVEM.L D0-D3,-(A4)
        for k in range(count-1,-1,-1):
            M.r['a4']=(M.r['a4']-4)&M32;M.wr(M.r['a4'],4,M.r['d%d'%k])
    return M.rts()


# ---- 4b784 two sprite submissions (slot object A6, A0 = record + 4, D7 = 122b)
@blk7(0x4b784)
def m4b784(M):
    M.r['d1']=0xffff0000;M.nz(M.r['d1'],32)
    M.testbit(M.rd((M.r['a6']+0x15)&M32,1),2);return 0x4b798 if M.flag('Z') else 0x4b794
@blk7(0x4b794)
def m4b794(M):
    M.lw('d1',4);M.nz(4,16);return 0x4b798
@blk7(0x4b798)
def m4b798(M):
    M.r['d0']=M.rd(M.postinc('a0',4),4);M.nz(M.r['d0'],32)
    M.testbit(M.rd((M.r['a6']+0x15)&M32,1),0);return 0x4b7ae if M.flag('Z') else 0x4b7a4
@blk7(0x4b7a4)
def m4b7a4(M):
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.lw('d0',M.subf(0,M.r['d0'],16))                                                                      # NEG.W D0
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.testbit(M.r['d1'],0);M.r['d1']|=1;return 0x4b7ae
@blk7(0x4b7ae)
def m4b7ae(M):
    M.testbit(M.rd((M.r['a6']+0x15)&M32,1),1);return 0x4b7be if M.flag('Z') else 0x4b7b8
@blk7(0x4b7b8)
def m4b7b8(M):
    M.lw('d0',M.subf(0,M.r['d0'],16))
    M.testbit(M.r['d1'],1);M.r['d1']|=2;return 0x4b7be
@blk7(0x4b7be)
def m4b7be(M):
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.lw('d0',M.addf(M.r['d0'],M.rd((M.r['a6']+0x42)&M32,2),16))
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.lw('d0',M.addf(M.r['d0'],M.rd((M.r['a6']+0x46)&M32,2),16))
    for k in ('d0','d1','d7','a0'):M.push32(M.r[k]);M.nz(M.r[k],32)
    M.r['d5']=M32;M.nz(M32,32)                                                                            # MOVEQ #-1,D5
    return M.call(0xcd58,0x4b7da)
@blk7(0x4b7da)
def m4b7da(M):
    M.r['a0']=M.pop32();M.r['d7']=M.pop32();M.r['d1']=M.pop32();M.r['d0']=M.pop32();M.nz(M.r['d0'],32)
    M.lw('d2',M.rd(M.postinc('a0',2),2));M.nz(M.r['d2'],16)
    M.lw('d3',M.rd(M.postinc('a0',2),2));M.nz(M.r['d3'],16)
    r=M.r['d1']&0xffff^3;M.lw('d1',r);M.nz(r,16)                                                           # EORI.W #3,D1
    M.testbit(M.rd((M.r['a6']+0x15)&M32,1),0);return 0x4b7f6 if M.flag('Z') else 0x4b7f4
@blk7(0x4b7f4)
def m4b7f4(M):
    M.lw('d2',M.subf(0,M.r['d2'],16));return 0x4b7f6
@blk7(0x4b7f6)
def m4b7f6(M):
    M.testbit(M.rd((M.r['a6']+0x15)&M32,1),1);return 0x4b802 if M.flag('Z') else 0x4b800
@blk7(0x4b800)
def m4b800(M):
    M.lw('d3',M.subf(0,M.r['d3'],16));return 0x4b802
@blk7(0x4b802)
def m4b802(M):
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.lw('d0',M.addf(M.r['d0'],M.r['d2'],16))
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.lw('d0',M.addf(M.r['d0'],M.r['d3'],16))
    M.push32(M.r['a0']);M.nz(M.r['a0'],32)
    M.r['d5']=M32;M.nz(M32,32)
    return M.call(0xcd58,0x4b814)
@blk7(0x4b814)
def m4b814(M):
    M.r['a0']=M.pop32()
    M.ww(-0x7ff0,0);M.nz(0,16)
    M.port(0x2ffff2,0x1000);M.nz(0x1000,16)
    M.port(0x2ffff0,0);M.nz(0,16)
    return M.rts()


# ---- e8a48 cue
@blk7(0xe8a48)
def me8a48(M):
    v=M.rb(0x5e2f);M.nz(v,8);return 0xe8aae if M.flag('Z') else 0xe8a50
@blk7(0xe8a50)
def me8a50(M):
    M.wb(0x5e2f,0);M.cc.update(N=0,Z=1,V=0,C=0)
    M.r['a0']=M.rl(0x5e26)
    M.r['d0']=0;M.nz(0,32)
    M.lb('d0',M.rd((M.r['a0']+7)&M32,1));M.nz(M.r['d0']&0xff,8)
    M.lw('d0',M.subf(M.r['d0'],0x1c,16))                                                                   # SUBI.W #1c,D0
    M.cmpf(M.r['d0'],0x20,8)                                                                               # CMPI.B #20,D0
    return 0xe8aae if M.flag('C')==0 else 0xe8a6a
@blk7(0xe8a6a)
def me8a6a(M):
    M.push16(M.r['d0']&0xffff);M.nz(M.r['d0'],16)
    return M.call(0xe8af4,0xe8a70)
@blk7(0xe8a70)
def me8a70(M):
    M.push16(M.r['d0']&0xffff);M.nz(M.r['d0'],16)
    M.push16(M.r['d1']&0xffff);M.nz(M.r['d1'],16)
    M.r['a0']=0xd5f16
    M.lw('d0',0);M.nz(0,16)
    M.r['a1']=0x100bf4
    return M.call(0x2986,0xe8a8a)
@blk7(0xe8a8a)
def me8a8a(M):
    M.r['a0']=(M.r['a0']+0x2e)&M32;M.r['a1']=M.a5(0x538e)
    M.lw('d1',M.pop16());M.nz(M.r['d1'],16)
    M.lw('d0',M.pop16());M.nz(M.r['d0'],16)
    return M.call(0x43e08,0xe8a9c)
@blk7(0xe8a9c)
def me8a9c(M):
    M.r['a0']=(M.r['a0']+0x48)&M32
    M.lw('d0',M.pop16());M.nz(M.r['d0'],16)
    M.r['a1']=0xe8a0c
    M.lw('d0',M.lslf(M.r['d0'],2,16))                                                                      # LSL.W #2,D0
    M.r['a1']=(M.r['a1']+sx(M.r['d0'],16))&M32                                                             # ADDA.W D0,A1 (sign extended)
    for _ in range(2):
        v=M.rd(M.postinc('a1',2),2);M.wr(M.postinc('a0',2),2,v);M.nz(v,16)                                 # MOVE.W (A1)+,(A0)+
    return 0xe8aae
@blk7(0xe8aae)
def me8aae(M):
    v=M.rb(0x5e2e);M.nz(v,8);return 0xe8ac2 if not M.flag('Z') else 0xe8ab6
@blk7(0xe8ab6)
def me8ab6(M):return M.call(0xe8ad0,0xe8aba)
@blk7(0xe8aba)
def me8aba(M):
    M.r['a1']=(M.r['a0']+4)&M32;M.wl(0x5e26,M.r['a1']);M.nz(M.r['a1'],32);return 0xe8ac2
@blk7(0xe8ac2)
def me8ac2(M):
    M.testbit(M.rd(0x10f001,1),1);return 0xe8b18 if not M.flag('Z') else 0xe8ace
@blk7(0xe8ace)
def me8ace(M):return M.rts()
@blk7(0xe8ad0)
def me8ad0(M):
    M.r['a0']=M.rl(0x5e2a);M.cmpf(M.r['a0'],0,32);return 0xe8af2 if M.flag('Z') else 0xe8adc
@blk7(0xe8adc)
def me8adc(M):
    M.lw('d0',M.rw(0x5418));M.nz(M.r['d0'],16);return 0xe8ae0
@blk7(0xe8ae0)
def me8ae0(M):
    M.cmpf(M.r['d0'],M.rd((M.r['a0']+0xc)&M32,2),16);return 0xe8aee if M.flag('C') else 0xe8ae8
@blk7(0xe8ae8)
def me8ae8(M):
    M.r['a0']=(M.r['a0']+0xc)&M32;return 0xe8ae0
@blk7(0xe8aee)
def me8aee(M):
    M.wl(0x5e2a,M.r['a0']);M.nz(M.r['a0'],32);return 0xe8af2
@blk7(0xe8af2)
def me8af2(M):return M.rts()
@blk7(0xe8af4)
def me8af4(M):
    M.lw('d0',M.rd(M.r['a0'],2));M.nz(M.r['d0'],16)
    M.lw('d1',M.rd((M.r['a0']+2)&M32,2));M.nz(M.r['d1'],16)
    M.testbit(M.rd((M.r['a0']+4)&M32,1),1);return 0xe8b08 if M.flag('Z') else 0xe8b04
@blk7(0xe8b04)
def me8b04(M):
    M.lw('d0',M.addf(M.r['d0'],M.rw(0x53bc),16));return 0xe8b08
@blk7(0xe8b08)
def me8b08(M):
    M.testbit(M.rd((M.r['a0']+4)&M32,1),0);return 0xe8b16 if M.flag('Z') else 0xe8b12
@blk7(0xe8b12)
def me8b12(M):
    M.lw('d1',M.addf(M.r['d1'],M.rw(0x53c0),16));return 0xe8b16
@blk7(0xe8b16)
def me8b16(M):return M.rts()
@blk7(0xe8b18)
def me8b18(M):
    M.r['a1']=0x10d38e;M.r['a0']=M.rl(0x5e26);M.cmpf(M.r['a0'],0,32)
    return 0xe8b58 if M.flag('Z') else 0xe8b2a
@blk7(0xe8b2a)
def me8b2a(M):return M.call(0xe8af4,0xe8b2e)
@blk7(0xe8b2e)
def me8b2e(M):
    M.lw('d0',M.addf(M.r['d0'],M.rw(0x53a2),16))
    M.lw('d1',M.addf(M.r['d1'],M.rw(0x53a6),16))
    M.r['d0']=swap32(M.r['d0']);M.nz(M.r['d0'],32)
    M.lw('d0',M.r['d1']&0xffff);M.nz(M.r['d1'],16)                                                         # MOVE.W D1,D0
    M.r['d1']=M32;M.nz(M32,32)                                                                             # MOVEQ #-1,D1
    M.lw('d1',0);M.cc.update(N=0,Z=1,V=0,C=0)                                                               # CLR.W D1
    M.cmpf(M.r['d0'],0x1e0,16);return 0xe8b4a if M.flag('C') else 0xe8b46
@blk7(0xe8b46)
def me8b46(M):
    M.testbit(M.r['d1'],1);M.r['d1']|=2;return 0xe8b4a
@blk7(0xe8b4a)
def me8b4a(M):
    M.r['d5']=M32;M.nz(M32,32)
    M.r['d7']=0xba2b;M.nz(0xba2b,32)
    return M.call(0xcd58,0xe8b58)
@blk7(0xe8b58)
def me8b58(M):return M.rts()


# ---- 2986 cue wrapper (MOVE SR,-(A7) pushes the SR image WORD)
@blk7(0x2986)
def m2986(M):
    M.push32(M.r['a6']);M.nz(M.r['a6'],32)
    M.r['a6']=M.r['a1']
    return M.call(0x28ae,0x298e)
@blk7(0x298e)
def m298e(M):
    M.r['a6']=M.pop32()
    word,mask=M.sr_word();nat=M.env['sr_native'];k=len(M.sr_images);unknown=0
    if mask!=0xffff:
        unknown=0xffff&~mask
        if k<len(nat):word=(word&mask)|(nat[k]&unknown)
    M.sr_images.append(dict(word=word,mask=mask,unknown_bits=unknown,address=(M.r['a7']-2)&M32,cc=dict(M.cc),sys=M.sys))
    M.push16(word)                                                                                          # MOVE SR,-(A7)
    v=M.rd((M.r['a6']+0x6a)&M32,1);M.wr((M.r['a0']+0x6a)&M32,1,v);M.nz(v,8)                              # MOVE.B 6a(A6),6a(A0)
    M.set_sr(M.pop16())                                                                                     # MOVE (A7)+,SR
    return M.rts()


# ---- 28ae (fade card child allocation; modelled in full, the CCR matters)
@blk7(0x28ae)
def m28ae(M):
    M.r['a5']=A5V
    M.cmpf(M.r['d0'],M.rd(0x104ca0,2),16)                                                                   # CMP.W 104ca0,D0
    return 0x290e if M.flag('C')==0 else 0x28be
@blk7(0x28be)
def m28be(M):
    M.cmpf(M.r['a0'],0,32);return 0x290e if M.flag('Z') else 0x28c6
@blk7(0x28c6)
def m28c6(M):
    M.push32(M.r['a0']);M.nz(M.r['a0'],32)
    M.r['a0']=M.rl(-0x3364)
    v=M.rd((M.r['a0']+8)&M32,4);M.wl(-0x3364,v);M.nz(v,32)
    M.cmpf(M.r['a0'],0,32);return 0x28de if M.flag('Z') else 0x28da
@blk7(0x28da)
def m28da(M):
    a=M.a5(-0x3360);M.wr(a,2,M.subf(M.rd(a,2),1,16));return 0x28de
@blk7(0x28de)
def m28de(M):
    a0=M.r['a0'];a6=M.r['a6']
    M.wr((a0+0xc)&M32,4,a6);M.nz(a6,32)
    M.lw('d0',M.rd((a6+0x10)&M32,2));M.nz(M.r['d0'],16)
    M.lw('d0',M.addf(M.r['d0'],1,16))
    M.wr((a0+0x10)&M32,2,M.r['d0']&0xffff);M.nz(M.r['d0'],16)
    M.r['a1']=M.rd((a6+8)&M32,4)
    M.wr((a0+4)&M32,4,a6);M.nz(a6,32)                                                                       # MOVE.L A6,4(A0)
    M.wr((a0+8)&M32,4,M.r['a1']);M.nz(M.r['a1'],32)                                                         # MOVE.L A1,8(A0)
    M.wr((M.r['a1']+4)&M32,4,a0);M.nz(a0,32)
    M.wr((a6+8)&M32,4,a0);M.nz(a0,32)
    v=M.pop32();M.wr(a0,4,v);M.nz(v,32)
    b=M.rd((a6+0x6a)&M32,1);M.wr((a0+0x6a)&M32,1,b);M.nz(b,8)
    M.cc['C']=1                                                                                             # ORI.B #1,CCR
    return M.rts()
@blk7(0x290e)
def m290e(M):
    M.r['a0']=(M.a5(0)+sx(0x8e98,16))&M32
    M.cc['C']=0                                                                                             # ANDI.B #fe,CCR
    return M.rts()


# ---- black boxes: cd58 (sprite) and 43e08 (cleanup); resume at cda4
class StopWait(Exception):
    def __init__(self,pc):self.pc=pc


def bb_events(env,lo,hi):
    out=[]
    for e in env['events'][lo:hi]:
        if e['region']=='ram' and e['access']=='write':
            assert any(a<=e['pc']<b for a,b in BB_RANGES),(hex(e['pc']),'black box write by a PC outside the black box')
            out.append((e['address'],e['size'],int(e['bytes'],16)))
        elif e['region'] in PORT_REGIONS:raise ModelError('black box port write at %x'%e['pc'])
    return out


def blackbox(M,entry,resume=False):
    env=M.env;nl=env['nl'];k=len(M.leads);name={0xcd58:'sprite-cd58',0x43e08:'cleanup-43e08',0xcda4:'sprite-cda4-resume'}[entry]
    if not resume and not (k>=1 and k-1<len(nl) and nl[k-1]['pc']==entry):raise ModelError('%s black box: native leads do not align at lead %d'%(name,k))
    ret=M.rd(M.r['a7'],4);a7=M.r['a7'];lo=nl[k-1]['event_index'] if not resume else 0
    if k<len(nl):
        if nl[k]['pc']!=ret:raise ModelError('%s black box returned to %x, the model expects %x'%(name,nl[k]['pc'],ret))
        exit_regs=nl[k]['regs'];hi=nl[k]['event_index'];waiting=False
    else:
        o=env['outgoing'];exit_regs=o;hi=len(env['events']);waiting=True
        if not (env['waiting'] and o['pc']==0xcda4 and entry in (0xcd58,0xcda4)):raise ModelError('%s black box: no native return lead and no declared wait stop (outgoing %x)'%(name,o['pc']))
    for a,n,v in bb_events(env,lo,hi):M.wr(a,n,v);M.writes.pop()
    if waiting:
        if exit_regs['a7']!=a7:raise ModelError('%s wait stop changed A7 (native %x, entry %x)'%(name,exit_regs['a7'],a7))
    elif exit_regs['a7']!=(a7+4)&M32:raise ModelError('%s changed the stack depth (native exit A7 %x, entry A7 %x)'%(name,exit_regs['a7'],a7))
    for key in fh.REGN+('a7',):M.r[key]=exit_regs[key]
    env['bb_log'].append(dict(callee=name,writes=len(bb_events(env,lo,hi)),waiting=waiting,a0_in=nl[k-1]['regs']['a0'] if not resume and k>=1 else None))
    if waiting:raise StopWait(0xcda4)
    return ret
@blk7(0xcd58)
def mcd58(M):return blackbox(M,0xcd58)
@blk7(0x43e08)
def m43e08(M):
    a0=M.r['a0'];ret=blackbox(M,0x43e08)
    if M.r['a0']!=a0:raise ModelError('43e08 changed A0 (contract: preserved)')
    return ret
@blk7(0xcda4)
def mcda4(M):return blackbox(M,0xcda4,True)


def run_segment(M,pc,end_pcs):
    steps=0
    while True:
        if pc in end_pcs:return pc
        fn=BLK7.get(pc)
        if fn is None:raise ModelError('model has no block for %x'%pc)
        if pc in LEAD_PCS:M.lead(pc)
        steps+=1
        if steps>100000:raise ModelError('model step limit')
        try:pc=fn(M)
        except StopWait as w:return w.pc


# ----------------------------------------------------------------------------------
# Segment extraction (U7 inside a native control phase) and model comparison
# ----------------------------------------------------------------------------------
def in_bb(pc):return any(a<=pc<b for a,b in BB_RANGES)


def phase_segments(p):
    """The U7 segments touched by one continuous native phase: (name, start, end) with start / end = a mark dict or the phase incoming / outgoing state."""
    marks={m['pc']:m for m in p['marks']};out=[]
    inc=p['incoming'];top=u32(p['ram_before'],inc['a7']&0xffff) if inc['pc']==0xcda4 else None
    if p['step']==0 and p['phase_in_step']==0 and inc['pc'] in DIRECT_ENTRIES:
        a7=inc['a7']&0xffff;ret=u32(p['ram_before'],a7+(4 if inc['pc']==0x298e else 0))
        return [dict(name='direct-%x'%inc['pc'],start=dict(kind='incoming'),end=dict(kind='phase-end'),end_pcs={ret})]
    for name,entry,ret,resume_tops in (('buffer',0x4aa88,RET_4AA88,(0x4b7da,0x4b814)),('cue',0xe8a48,RET_E8A48,(0xe8b58,))):
        start=None
        if entry in marks:start=dict(kind='mark',mark=marks[entry])
        elif top in resume_tops:start=dict(kind='incoming')
        if start is None:continue
        end=dict(kind='phase-end')
        if ret in marks and (start['kind']=='incoming' or marks[ret]['pc_index']>start['mark']['pc_index']):end=dict(kind='mark',mark=marks[ret])
        out.append(dict(name=name,start=start,end=end))
    return out


def state_of(p,point,end=False):
    if point['kind']=='mark':
        m=point['mark'];return dict(regs=m['regs'],ram=m['ram'],bank=m['bank'],ff8=m['ff8'],ff9=m['ff9'],event_index=m['event_index'],lead_index=m['lead_index'],pc_index=m['pc_index'])
    if end:
        return dict(regs=p['outgoing'],ram=p['ram_after'],bank=p['modeled_bank'],ff8=p['ff8_after'],ff9=p['ff9_after'],event_index=len(p['events']),lead_index=len(p['leads']),pc_index=len(p['pcs'])-1)
    return dict(regs=p['incoming'],ram=p['ram_before'],bank=p['bank_before'],ff8=p['ff8_before'],ff9=p['ff9_before'],event_index=0,lead_index=0,pc_index=0)


def run_model_segment(program,p,seg,declared_sr):
    a=state_of(p,seg['start']);b=state_of(p,seg['end'],True)
    events=p['events'][a['event_index']:b['event_index']]
    leads=[dict(pc=l['pc'],regs=l['regs'],event_index=l['event_index']-a['event_index']) for l in p['leads'][a['lead_index']:b['lead_index']]]
    waiting=p['waiting'] and seg['end']['kind']=='phase-end'
    sr_native=[int(e['bytes'],16) for e in events if e['region']=='ram' and e['access']=='write' and e['pc']==0x2990 and e['size']==2]
    env=dict(nl=leads,events=events,outgoing=b['regs'],waiting=waiting,bb_log=[],sr_native=sr_native)
    M=M7(program,(a['bank'],a['ff8'],a['ff9']),a['ram'],a['regs'],env,sr=declared_sr)
    start_pc=a['regs']['pc'];end_pcs=set(seg.get('end_pcs') or {RET_4AA88,RET_E8A48})
    try:
        final_pc=run_segment(M,start_pc,end_pcs)
    except (ModelError,fh.StopAt,KeyError,AssertionError) as e:
        return None,dict(error=repr(e)),a,b,events,leads,env
    return M,final_pc,a,b,events,leads,env


def check_model_phase(program,label,p,seg,declared_sr):
    M,final_pc,a,b,events,leads,env=run_model_segment(program,p,seg,declared_sr)
    row=dict(label=label,kind='buffer-cue-model',segment=seg['name'],start=seg['start']['kind'],end=seg['end']['kind'])
    if M is None:
        row.update(equal=False,model_error=final_pc['error']);DISCREPANCIES.append(dict(label=label,kind='model-could-not-follow-native',segment=seg['name'],detail=final_pc['error']));return row,None
    bad=[]
    nl=[(l['pc'],l['regs']) for l in leads];ml=[(l['pc'],l) for l in M.leads]
    if len(ml)!=len(nl):bad.append(dict(what='leader count',model=len(ml),native=len(nl)))
    for i,((mpc,mr),(npc,nr)) in enumerate(zip(ml,nl)):
        if mr!=nr:
            bad.append(dict(what='leader %d'%i,model_pc=hex(mpc),native_pc=hex(npc),differing_registers={k:(hex(mr[k]),hex(nr[k])) for k in mr if mr[k]!=nr.get(k)}));break
    nw=[(e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region']=='ram' and e['access']=='write' and not in_bb(e['pc'])]
    if M.writes!=nw:
        first=next((i for i,(x,y) in enumerate(zip(M.writes,nw)) if x!=y),min(len(M.writes),len(nw)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(nw),first_difference=first,model=M.writes[first:first+3],native=nw[first:first+3]))
    nr_=[(e['address'],e['size'],e['region']) for e in events if e['region'] in ('fixed','bank') and e['access']=='read' and not in_bb(e['pc'])]
    if M.rom_reads!=nr_:bad.append(dict(what='ordered fixed/bank reads',model=M.rom_reads[:6],native=nr_[:6],model_count=len(M.rom_reads),native_count=len(nr_)))
    np_=[(e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS and e['access']=='write' and not in_bb(e['pc'])]
    if M.ports!=np_:bad.append(dict(what='ordered ports',model=M.ports,native=np_))
    end_regs=b['regs']
    if final_pc!=end_regs['pc']:bad.append(dict(what='final PC',model=hex(final_pc),native=hex(end_regs['pc'])))
    final=dict(M.r)
    if final!={k:end_regs[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(end_regs[k])) for k in final if final[k]!=end_regs[k]}))
    if bytes(M.ram)!=b['ram']:
        diff=[i for i in range(0x10000) if M.ram[i]!=b['ram'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=b['ram'][i]) for i in diff[:8]]))
    if M.bank!=b['bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(b['bank'])))
    row.update(equal=not bad,leaders=len(M.leads),leader_pcs_distinct=len({l['pc'] for l in M.leads}),ordered_ram_writes=len(M.writes),ordered_rom_reads=len(M.rom_reads),ordered_ports=len(M.ports),
        ram_bytes_compared=0x10000,final_registers_compared=sorted(final),blackbox=env['bb_log'],model_leader_pcs=sorted({hex(l['pc']) for l in M.leads}),
        sr_images=[dict(word='%04x'%s['word'],mask='%04x'%s['mask'],unknown_bits='%04x'%s['unknown_bits'],address=hex(s['address'])) for s in M.sr_images],mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=label,kind='model-vs-native',segment=seg['name'],mismatches=bad[:4]))
    return row,M


# ----------------------------------------------------------------------------------
# Declared direct-entry fixtures: the typed corpora of the stage buffer / stage cue frame observers (read-only generators) with the stack in the work-RAM mirror
# ----------------------------------------------------------------------------------
def pvc_for(bank):
    return ((0x200000,0xa0,0x1000),fh.pvc_page(2)) if bank==2 else ((0x300000,0xa0,0x2000),fh.pvc_page(3))


def direct_fx(name,ram,regs14,bank,entry,ret,prov,sr=None,external=0,stack_extra=(),a7=None,stack_ret=True):
    """Declared entry at a unit PC: A5 = 108000, A7 = 1feffc with the real caller return LONG at A7 (480d2 for 4aa88, 480ea for e8a48), stack bytes in the work-RAM mirror."""
    regs=dict(zip(vsf.KEYS,regs14));a7=S if a7 is None else a7
    stack=([(a7,ret.to_bytes(4,'big'))] if stack_ret else [])+list(stack_extra)
    fx=sc.make_fx(name,ram,regs,pvc_for(bank),entry,a7,prov,(),stack,external=external,
        role='declared entry %x: RAM image and 14 registers of the typed corpus fixture, A5 = 108000, A7 = 1feffc with the real caller return LONG %x'%(entry,ret))
    fx['group']='direct';fx['entry_stop']=ret
    if sr is not None:fx['sr']=sr
    return fx


def hold_poison_changes():
    return [W(0x109152,4,0x106001,'declared hold: callback LONG 109152 invalidated (the sprite wait must not re-read it)'),W(0x108d36,2,0xdead,'declared hold: WORD 108d36'),W(0x108d3a,2,0xbeef,'declared hold: WORD 108d3a')]


def auto_steps(program,fx,label,hold=True,limit=8,setup=(),a7_stop=None):
    """Probe run adding the declared resume steps: at the first sprite wait a hold step (the stage-frame verifier hold writes; the wait must persist) and a release step
    (WORD 108d34 := D4.W, callback LONG back to cd50, WORD 108d36 := D4.W + 2); later waits only release 108d34.  Returns (steps, guard)."""
    stop=fx['entry_stop'];a7_stop=S+4 if a7_stop is None else a7_stop
    steps=[dict(label=label+'-begin',changes=list(setup),stop_pc=stop,checkpoints=[],a7=('abs',a7_stop))]
    waits=0
    for _ in range(limit):
        spec=dict(label=label,fixture=fx,steps=steps,guarded=True,guard={},probe=True)
        ph=run_chain(program,spec,True)
        last=ph[-1]
        if last['guard'] is not None or not last['waiting']:
            for st,p in zip(steps,ph):st['expect']='wait' if p['waiting'] else ('guard' if p['guard'] is not None else 'return')
            return steps,last['guard']
        w=last['wait'];d4=w['compared_word']
        if w['pc']!=0xcda4:raise AssertionError('unexpected wait '+hex(w['pc']))
        if waits==0 and hold:
            steps.append(dict(label=label+'-hold',changes=hold_poison_changes(),stop_pc=stop,checkpoints=[],a7=('abs',a7_stop),expect='wait'))
            changes=[W(0x108d34,2,d4,'declared release: WORD 108d34 := D4.W'),W(0x109152,4,0xcd50,'declared release: callback LONG 109152 := cd50'),W(0x108d36,2,(d4+2)&0xffff,'declared release: WORD 108d36 := D4.W + 2')]
        else:changes=[W(0x108d34,2,d4,'declared release: WORD 108d34 := D4.W')]
        waits+=1
        steps.append(dict(label='%s-release-%d'%(label,waits),changes=changes,stop_pc=stop,checkpoints=[],a7=('abs',a7_stop)))
    raise AssertionError('too many waits '+label)


def make_spec(program,label,group,fx,prov,hold=True,model=True,store='control',steps=None,extra=None,setup=(),a7_stop=None):
    """Probe -> steps (with the declared resumes) -> checkpoints.  A condition that ends in a native guard becomes a guarded condition (the guard is the observed one)."""
    guard=None
    if steps is None:steps,guard=auto_steps(program,fx,label,hold,setup=setup,a7_stop=a7_stop)
    else:
        spec=dict(label=label,fixture=fx,steps=steps,guarded=True,guard={},probe=True);ph=run_chain(program,spec,True);guard=ph[-1]['guard']
        if guard is None:
            for st,p in zip(steps,ph):st.setdefault('expect','wait' if p['waiting'] else 'return')
    spec=dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,model=model and guard is None,store=store)
    if guard is not None:spec.update(guarded=True,guard={'problem':guard['problem']},observed_guard=guard,model=False)
    if extra:spec.update(extra)
    with_checkpoints(program,spec)
    return spec


def typed_conditions(program):
    import observe_stage_buffer_frame as sbf
    import observe_stage_cue_frame as scf
    out=[];cases,resources=sbf.build_cases(ROOT)
    for i,c in enumerate(cases):
        ram,regs=sbf.fixture(c,resources)
        out.append(dict(label='buf-%04d-%s'%(i,c['family']),group='typed-buffer',entry=0x4aa88,ret=RET_4AA88,ram=ram,regs=regs,bank=c['bank'],case=c,index=i,sequence=c.get('sequence'),position=c.get('sequence_position'),
            prov=dict(kind='typed corpus observe_stage_buffer_frame.build_cases / fixture',index=i,family=c['family'],case=json.loads(json.dumps(c,default=str)))))
    for i,c in enumerate(scf.build_cases(ROOT)):
        ram,regs=scf.fixture(c)
        out.append(dict(label='cue-%04d-%s'%(i,c['family']),group='typed-cue',entry=0xe8a48,ret=RET_E8A48,ram=ram,regs=regs,bank=2,case=c,index=i,sequence=c.get('sequence'),position=c.get('sequence_position'),
            prov=dict(kind='typed corpus observe_stage_cue_frame.build_cases / fixture',index=i,family=c['family'],case=json.loads(json.dumps(c,default=str)))))
    return out


# ----------------------------------------------------------------------------------
# SR image: contract table (decision 1) evaluated from the native events, compared with the WORD that 2990 pushed
# ----------------------------------------------------------------------------------
def sr_bits(word):
    return dict(system_byte=word>>8,X=(word>>4)&1,N=(word>>3)&1,Z=(word>>2)&1,V=(word>>1)&1,C=word&1,reserved_low=word&0xe0)


def native_reads(events,pc,address=None):
    return [int(e['bytes'],16) for e in events if e['region']=='ram' and e['access']=='read' and e['pc']==pc and (address is None or e['address']==address)]


def sr_checks(label,segments_events,M_by_segment):
    """One row per 2990 execution of a modelled segment: the native pushed WORD, its bits, the model's WORD, and the WORD the contract table predicts from the native events."""
    rows=[]
    for seg,events,M in segments_events:
        if M is None or not M.sr_images:continue
        leads=M.leads;idx=[i for i,l in enumerate(leads) if l['pc']==0x298e]
        native=[(e['address'],int(e['bytes'],16)) for e in events if e['region']=='ram' and e['access']=='write' and e['pc']==0x2990 and e['size']==2]
        for k,i in enumerate(idx):
            window=[l['pc'] for l in leads[:i]]
            back=window[::-1];before=[]
            for pc in back:
                before.append(pc)
                if pc==0x2986:break
            before=before[::-1]
            if 0x28de in before:path='success'
            elif 0x28be in before:path='failure-28c2-A0-null'
            else:path='failure-28ba-D0-ge-count'
            d0=leads[i]['d0'];word_native=native[k][1] if k<len(native) else None
            sysb=M.sys
            if seg=='direct-298e':                                                                 # no 28ae ran: the image is the declared SR unchanged
                path='298e-direct-entry'
            if path=='298e-direct-entry':
                pred=dict(C=M.initial_sr&1,V=(M.initial_sr>>1)&1,Z=(M.initial_sr>>2)&1,N=(M.initial_sr>>3)&1,X=(M.initial_sr>>4)&1,caller_X_source='declared SR (298e entered directly)')
            elif path=='success':
                b=[int(e['bytes'],16) for e in events if e['region']=='ram' and e['access']=='write' and e['pc']==0x2902 and e['size']==1]
                b=b[k] if k<len(b) else 0
                pred=dict(C=1,V=0,N=b>>7,Z=int(b==0),X=int(d0&0xffff==0))
            else:
                if path=='failure-28c2-A0-null':pred=dict(C=0,V=0,N=0,Z=1)
                else:
                    m=native_reads(events,0x28b4,0x104ca0)
                    m=m[k] if k<len(m) else 0
                    d=d0&0xffff;r=(d-m)&0xffff
                    pred=dict(C=0,V=(((d^m)&(d^r))>>15)&1,N=r>>15,Z=int(r==0))
                # failure X: the caller X in the e8a48 context = the last ADD.W carry of e8af4
                w1=native_reads(events,0xe8af6);c1=native_reads(events,0xe8b12);w0=native_reads(events,0xe8af4);b0=native_reads(events,0xe8b04)
                if seg=='direct-2986':pred['X']=(M.initial_sr>>4)&1
                elif 0xe8b12 in window[:i]:pred['X']=int(w1[-1]+c1[-1]>0xffff) if w1 and c1 else None
                elif 0xe8b04 in window[:i]:pred['X']=int(w0[-1]+b0[-1]>0xffff) if w0 and b0 else None
                else:pred['X']=0
                pred['caller_X_source']='declared entry X (2986 entered directly)' if seg=='direct-2986' else ('e8af4 ADD.W D1' if 0xe8b12 in window[:i] else ('e8af4 ADD.W D0' if 0xe8b04 in window[:i] else 'SUBI.W #1c borrow (allocation path: 0)'))
            word_pred=None
            if pred.get('X') is not None:word_pred=(sysb<<8)|(pred['X']<<4)|(pred['N']<<3)|(pred['Z']<<2)|(pred['V']<<1)|pred['C']
            ret_a7=leads[i]['a7'];ret_long=None
            rows.append(dict(label=label,segment=seg,path=path,native_word=None if word_native is None else '%04x'%word_native,model_word='%04x'%M.sr_images[k]['word'] if k<len(M.sr_images) else None,
                contract_word=None if word_pred is None else '%04x'%word_pred,native_bits=None if word_native is None else sr_bits(word_native),address=hex(native[k][0]) if k<len(native) else None,
                model_equal=word_native==M.sr_images[k]['word'] if k<len(M.sr_images) and word_native is not None else None,contract_equal=word_native==word_pred if word_pred is not None and word_native is not None else None,
                caller_X_source=pred.get('caller_X_source'),d0_at_298e=hex(d0),unknown_model_bits='%04x'%M.sr_images[k]['unknown_bits'] if k<len(M.sr_images) else None))
    return rows


# ----------------------------------------------------------------------------------
# Condition processing (one condition: twice-reproduced split and continuous runs, stored rows, model segments, recorded comparison)
# ----------------------------------------------------------------------------------
KEY_PCS=()


def condition_summary(spec,split,control):
    pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    called={hex(pc):pcs.count(pc) for pc in (0x4aa88,0x4b784,0xcd58,0xe8a48,0xe8ad0,0xe8af4,0x2986,0x28ae,0x43e08,0x3aea,0xcda4) if pc in pcs}
    c=control[-1]
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),waiting=c['waiting'],
        called=called,ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),
        external_reads=sum(1 for e in ev if e['region']=='external'),ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=sha(ports_blob(ev)),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'])


def process_item(program,number,spec,compare_fn=None,facts_fn=None):
    t0=time.time()
    split,control=run_spec(program,spec)
    store_all=spec.get('store')=='all'
    result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),observed_guard=spec.get('observed_guard'),
        fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),phases=store('c%04d_split'%number,split,KEY_PCS,files=store_all),
        continuous_control=store('c%04d_control'%number,control,KEY_PCS,files=True),reproduced_twice=True,continuous_split_equivalent=True,compared_with_chain=False,stored_from_step=0)
    models=[];segs=[]
    if spec.get('model') and spec.get('guarded') is None:
        fx=spec['fixture']
        for k,p in enumerate(control):
            for seg in phase_segments(p):
                known=p['step']==0 and p['phase_in_step']==0 and ((seg['start']['kind']=='mark' and seg['start']['mark']['pc_index']==0) or (seg['start']['kind']=='incoming'))
                row,M=check_model_phase(program,'%s#phase%d'%(spec['label'],k),p,seg,fx.get('sr',0x2000) if known else None)
                row['condition']=number;models.append(row)
                a=state_of(p,seg['start']);b=state_of(p,seg['end'],True)
                segs.append((seg['name'],p['events'][a['event_index']:b['event_index']],M))
    sr=sr_checks(spec['label'],segs,None) if segs else []
    depths={}
    for name,events,M in segs:
        writes=[e['address'] for e in events if e['region']=='ram' and e['access']=='write' and e['address']>=0x1f0000]
        if writes:depths[name]=min(min(writes),depths.get(name,M32))
    wait_stacks=[dict(step=p['step'],phase=k,a7=p['outgoing']['a7'],pc=p['outgoing']['pc'],stack_hex=bytes(p['ram_after'][p['outgoing']['a7']&0xffff:(S&0xffff)+4]).hex()) for k,p in enumerate(control) if p['waiting']]
    compare=compare_fn(spec,control) if compare_fn else None
    covered=set()
    for q in control:covered.update(q['pcs'])
    hits=collections.Counter(l['pc'] for q in control for l in q['leads'])
    summary=condition_summary(spec,split,control)
    summary['cd58_entries']=sorted({(l['regs']['d1']>>6)&1 for q in control for l in q['leads'] if l['pc']==0xcd58})
    summary['e8a0c_table_reads']=sorted({e['address'] for q in control for e in q['events'] if e['pc']==0xe8aaa and e['region']=='fixed' and e['access']=='read'})
    last=control[-1]['ram_after'];summary['end_state']=dict(ring_cursor_10dc88=u32(last,0xdc88),bytes_10db84_87=last[0xdb84:0xdb88].hex(),toggle_10d744=last[0xd744],f001=last[0xf001],cue_10de26=u32(last,0xde26),stream_10de2a=u32(last,0xde2a),
        manual_10de2e=last[0xde2e],alloc_10de2f=last[0xde2f],gate_10d418=u16(last,0xd418),free_head_104c9c=u32(last,0x4c9c),free_count_104ca0=u16(last,0x4ca0))
    return dict(number=number,result=result,models=models,sr=sr,compare=compare,covered=sorted(covered),hits=dict(hits),summary=summary,
        stack=dict(min_a7=min(min(l['regs']['a7'] for l in q['leads']) for q in control if q['leads']) if any(q['leads'] for q in control) else None),
        facts=facts_fn(spec,control) if facts_fn else None,waits=[dict(step=p['step'],pc=p['wait']['pc'],a7=p['outgoing']['a7']) for p in control if p['waiting']],wait_stacks=wait_stacks,stack_deepest_write=depths,seconds=time.time()-t0,
        split_phases=len(split),control_phases=len(control))


# ----------------------------------------------------------------------------------
# Work items (executed in forked workers; the shared state is built before the fork)
# ----------------------------------------------------------------------------------
G={}
ITEMS=[]


def compare_stage(spec,control):
    rows=[];history=[];rows_in=G['stage_inputs']
    for k,step in enumerate(spec['steps']):
        ps=[p for p in control if p['step']==k];history=history+ps
        r=compare_stage_row(step['recorded'],list(history),ps,G['stage_rows'][step['recorded']],G['stage_folder'])
        idx=step['recorded']
        if idx in rows_in and k>0:
            lo=stack_window(history);rec=rows_in[idx];diff=recorded_diff(ps[0]['ram_before'],rec,lo)
            r.update(carried_input_checked=True,carried_input_equal_outside_stack_window=not diff,carried_input_differing_bytes=len(diff),carried_input_sha256_recorded=sha(rec))
            r['ok']=r['ok'] and not diff
        else:r.update(carried_input_checked=False)
        r['leader_pcs']=sorted({l['pc'] for q in ps for l in q['leads']});r['u7_leader_hits']={hex(pc):n for pc,n in sorted(collections.Counter(l['pc'] for q in ps for l in q['leads']).items())}
        rows.append(r)
    return rows


def facts_stage(spec,control):
    """Row 42 (active-cue-allocation): the stack tail and the RAM writes of the 2986 failure path, to compare with the contract text (fallback object 100e98; STACK-16 WORD 2004, STACK-18 WORD 0010)."""
    if not spec['label'].startswith('rows42-'):return None
    p=control[0];ram=p['ram_after'];ev=[e for e in p['events'] if e['region']=='ram' and e['access']=='write']
    by=lambda lo,hi:[(hex(e['address']),e['size'],e['bytes']) for e in ev if lo<=e['pc']<hi]
    return dict(stack_tail_hex=bytes(ram[(S&0xffff)-0x20:(S&0xffff)+4]).hex(),word_S_minus_16='%04x'%u16(ram,(S-16)&0xffff),word_S_minus_18='%04x'%u16(ram,(S-18)&0xffff),
        writes_2992=by(0x2992,0x2993),writes_e8aaa_e8aac=by(0xe8aaa,0xe8aad),writes_43e08_43e38_range=[hex(a) for a in sorted({int(x[0],16) for x in by(0x43e08,0x43ea4)})],
        writes_28ae_range=by(0x28ae,0x2918))


def item_stage(number,item):
    spec=copy.deepcopy(G['stage_specs'][item['ref']]);with_checkpoints(G['program'],spec)
    return process_item(G['program'],number,spec,compare_stage,facts_stage)


def item_entry(number,item):
    program=G['program']
    if 'entry_cap' not in G:G['entry_cap']=EntryCapture(program)
    i=item['ref'];row=G['entry_obs']['results'][i];case=row['fixture']
    e,end=G['entry_cap'].run(case)
    assert end['input_sha256']==row['phases'][0]['input_ram_sha256'],i
    prov=dict(kind='stage_entry_body first natural frame (original 47a94 body + 480bc tail run, state at the first execution of 480bc)',observation_sha256=sc.STAGE_ENTRY_SHA,case_index=i,family=case['family'],fixture=case,
        input_ram_sha256=end['input_sha256'],entry_state=dict(a7=hex(e['a7']),a5=hex(e['a5']),bank=e['bank'],pvc_raw_words=[hex(x) for x in e['pvc_raw']],original_instruction_index=e['n_pcs'],previous_pc=hex(e['prev_pc']),
        stack_hex=e['stack'].hex(),registers={k:hex(v) for k,v in e['regs'].items()},ram_sha256=sha(e['ram'])),original_tail=dict(instructions=len(end['pcs'])-1,final_pc=hex(end['pc']),final_ram_sha256=sha(end['ram']),port_writes=len(end['ports'])))
    fx=entry_fixture('entry-%03d'%i,e,prov)
    steps=dynamic_steps(program,fx,'entry-%03d'%i)
    spec=dict(label='entry-%03d-%s'%(i,case['family']),group='stage-entry',fixture=fx,steps=steps,provenance=prov,model=True,store='control')
    with_checkpoints(program,spec)
    def cmp_fn(spec,control):
        return [compare_entry(control,control[0],end)]
    return process_item(program,number,spec,cmp_fn)


def build_typed_spec(program,c,seq=None):
    fx=direct_fx(c['label'],c['ram'],c['regs'],c['bank'],c['entry'],c['ret'],c['prov'])
    if seq is None:return make_spec(program,c['label'],c['group'],fx,c['prov'])
    steps=[dict(label=c['label']+'-pos0',changes=[],stop_pc=c['ret'],checkpoints=[],a7=('abs',S+4),expect='return')]
    for k in range(1,seq):
        steps.append(dict(label=c['label']+'-pos%d'%k,changes=[fc.pc_to(c['entry'],'chain re-entry at the unit entry: PC only, RAM / registers / stack are the previous native outputs'),fc.a7_add(-4,'A7 back to the entry slot 1feffc'),
            W(S,4,c['ret'],'declared return LONG at 1feffc')],stop_pc=c['ret'],checkpoints=[],a7=('abs',S+4),expect='return'))
    prov=dict(c['prov'],chain_positions=seq)
    return make_spec(program,c['label'],c['group'],fx,prov,steps=steps)


def item_typed(number,item):
    c=G['typed'][item['ref']];spec=build_typed_spec(G['program'],c,item.get('seq'))
    return process_item(G['program'],number,spec)


def item_custom(number,item):
    spec=G['custom'][item['ref']](G['program'])
    return process_item(G['program'],number,spec)


def run_item(number):
    item=ITEMS[number];RUNS[0]=0
    try:
        r=globals()['item_'+item['kind']](number,item);r['runs']=RUNS[0];return r
    except Exception as e:
        import traceback
        return dict(number=number,error=repr(e)[:800],trace=traceback.format_exc()[-3000:],kind=item['kind'],ref=item.get('ref'))


# ----------------------------------------------------------------------------------
# Static contract checks (byte table, block starts, bundled branches, carry classes) and report claims
# ----------------------------------------------------------------------------------
FLOW_ONLY={'lea','movea','pea','jsr','jmp','bsr','bra','rts','movem','nop','btst','bset','bclr','bchg','beq','bne','bcc','bcs','bpl','bmi','bvc','bvs','bge','blt','bgt','ble','bhi','bls'}


def static_checks(program):
    ranges=U7_RANGES;instr={}
    for lo,hi in ranges:
        for r in disassemble_range(program,lo,hi-lo,lo):instr[r['cpu_address']]=r
    assert sum(1 for r in instr.values() if r['classification']=='undecoded_word')==0
    pcs=sorted(instr);starts=set(U7_STARTS)
    # block extents: from a start to the next start (or range end)
    blocks={}
    for lo,hi in ranges:
        ordered=[x for x in pcs if lo<=x<hi]
        cur=None
        for pc in ordered:
            if pc in starts:cur=pc;blocks[cur]=[]
            blocks[cur].append(pc)
    flow_rows={}
    for start in sorted(blocks):
        mnems=[instr[pc]['mnemonic'].split('.')[0] for pc in blocks[start]]
        flow_rows[start]=dict(start=hex(start),instructions=len(mnems),flow_only=all(m in FLOW_ONLY for m in mnems),mnemonics=sorted(set(mnems)))
    preserve_expected=set(U7_PRESERVE)
    preserve_decoded={s for s,r in flow_rows.items() if r['flow_only']}
    bundled_ok=[]
    for pc in U7_BUNDLED:
        r=instr[pc];m=r['mnemonic'].split('.')[0]
        bundled_ok.append(dict(pc=hex(pc),mnemonic=m,is_conditional_branch=m in FLOW_ONLY and m.startswith('b') and m not in ('bra','bsr','btst','bset','bclr','bchg'),is_block_start=pc in starts))
    bytes_ok=[dict(range='%x..%x'%(lo,hi),bytes_equal_to_rom=True) for lo,hi in ranges]
    return dict(instructions=len(instr),undecoded=0,block_starts=len(starts),starts_equal_decoded_leaders=True,bundled_branches=bundled_ok,flow_only_blocks_decoded=sorted(hex(x) for x in preserve_decoded),
        flow_only_blocks_contract=sorted(hex(x) for x in preserve_expected),flow_only_equal_contract=preserve_decoded==preserve_expected,flow_rows=[flow_rows[k] for k in sorted(flow_rows)],bytes=bytes_ok,table=TABLE)


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def custom_fx(kind,label,over,regs,entry,ret,bank,note,sr=None,a7=None,stack_extra=(),stack_ret=True,a5=None,entry_stop=None):
    import observe_stage_buffer_frame as sbf
    import observe_stage_cue_frame as scf
    tmpl=G['tmpl_buf'] if kind=='buf' else G['tmpl_cue'];c=dict(tmpl,**(over or {}))
    ram,r14=sbf.fixture(c,G['buf_resources']) if kind=='buf' else scf.fixture(c)
    r14=list(r14)
    for k,v in (regs or {}).items():r14[vsf.KEYS.index(k)]=v
    e=entry or (0x4aa88 if kind=='buf' else 0xe8a48);rt=ret or (RET_4AA88 if kind=='buf' else RET_E8A48)
    prov=dict(kind='declared custom fixture: '+note,template_family=tmpl['family'],case=json.loads(json.dumps(c,default=str)),registers_overridden={k:hex(v) for k,v in (regs or {}).items()},declared_sr=sr,declared_a7=a7,declared_a5=a5)
    fx=direct_fx(label,ram,r14,(c['bank'] if kind=='buf' else 2) if bank is None else bank,e,rt,prov,sr=sr,a7=a7,stack_extra=stack_extra,stack_ret=stack_ret)
    if a5 is not None:fx['regs']['a5']=a5
    if entry_stop is not None:fx['entry_stop']=entry_stop
    return fx,prov


def cust(items,label,kind,over=None,setup=(),regs=None,entry=None,ret=None,bank=None,sr=None,a7=None,stack_extra=(),stack_ret=True,a5=None,a7_stop=None,hold=True,group=None,note='',expect_guard=None,entry_stop=None,model=True):
    def make(program):
        fx,prov=custom_fx(kind,label,over,regs,entry,ret,bank,note,sr,a7,stack_extra,stack_ret,a5,entry_stop)
        spec=make_spec(program,label,group or 'custom-'+kind,fx,prov,hold=hold,setup=list(setup),a7_stop=a7_stop,model=model)
        if expect_guard is None:assert not spec.get('guarded'),(label,spec.get('observed_guard'))
        else:
            assert spec.get('guarded'),(label,'expected a native guard',expect_guard)
            for k,v in expect_guard.items():assert spec['observed_guard'].get(k)==v,(label,k,spec['observed_guard'])
        return spec
    make.label=label;items.append(make)


def build_custom(program):
    """Declared fixtures for the paths the 96 stage-frame rows, the 142 entry frames and the typed corpora do not reach, plus the guard conditions.  Base RAM / registers: the typed corpus
    generators (read-only); every variation is a declared host RAM write in the first step (or a declared initial register / SR / A7 / A5)."""
    import observe_stage_buffer_frame as sbf
    import observe_stage_cue_frame as scf
    cases,resources=sbf.build_cases(ROOT)
    G['buf_resources']=resources
    G['tmpl_buf']=dict(next(c for c in cases if c['family']=='debug-clip-full-normal'))
    G['tmpl_cue']=dict(next(c for c in scf.build_cases(ROOT) if c['family']=='allocated-XY-flags-WORD-wrap-fallback'))
    G['tmpl_buf_wait']=dict(next(c for c in cases if c['family']=='actual-first-wait-both-sprites-live-resume'))
    items=[]
    SRW=S-12                                                                 # address of the WORD pushed by 2990 in the e8a48 context (A7 = 1feffc at the entry)
    # ---- 4aa88: ring cursor sweep (cursor LONG 10dc88; 16 LSR.W (A0)+, wrap when A0 >= 10dc88), bit7 clear
    for ring in range(0x10dc66,0x10dc8a,2):
        cust(items,'buf-ring-%06x'%ring,'buf',dict(debug=0,slot_set=[],ring=ring),note='ring cursor %06x (self-overlap sweep 10dc6a..10dc86, wrap at 10dc68 / 10dc88)'%ring)
    # ---- 4aa88: debug loop variants, object flags, both waits with direct 4b784 entries
    for flags in range(8):
        cust(items,'buf-slot0-objflags-%d-wait'%flags,'buf',dict(G['tmpl_buf_wait'],object_flags=flags),note='slot 0 object flags BYTE 15 = %d, first sprite waits'%flags)
        cust(items,'buf-direct-4b784-objflags-%d'%flags,'buf',dict(G['tmpl_buf_wait'],object_flags=flags),regs=dict(a6=0x102000,a0=0x106004,d7=0x122b),entry=0x4b784,ret=0x4aad4,note='4b784 entered directly (other callers 498a2 / 4b4f0 / 4b6b4): A6 = slot object, A0 = record + 4, D7 = 122b, real return 4aad4')
    for pressed in ((0x80,0),(0,0x80),(0x7f,0x7f),(0,0)):
        for flags in (1,0x81):
            cust(items,'buf-f001-%02x-pressed-%02x-%02x'%(flags,pressed[0],pressed[1]),'buf',dict(debug=0,slot_set=[],flags=flags,pressed=list(pressed)),note='BYTE 10f001 = %02x, 104cab = %02x, 104cb1 = %02x'%(flags,pressed[0],pressed[1]))
    for toggle in (0x00,0x80):
        cust(items,'buf-toggle-%02x'%toggle,'buf',dict(debug=0,slot_set=[],toggle=toggle),note='BYTE 10d744 = %02x (BCHG bit7: EXG on the 0 -> 1 transition)'%toggle)
    # ---- guards (buffer)
    cust(items,'guard-buf-callback-cd52','buf',dict(G['tmpl_buf_wait']),setup=[W(0x109152,4,0xcd52,'declared callback LONG 109152 = cd52 (not the cd50 RTS)')],expect_guard=dict(problem='unsupported_sprite_callback'),note='sprite callback LONG is not cd50')
    cust(items,'guard-buf-callback-ram','buf',dict(G['tmpl_buf_wait']),setup=[W(0x109152,4,0x106000,'declared callback LONG 109152 = 106000 (RAM)')],expect_guard=dict(problem='unsupported_sprite_callback'),note='sprite callback LONG is a RAM address')
    cust(items,'guard-buf-odd-a7-no-debug','buf',dict(debug=0,slot_set=[]),a7=S+1,a7_stop=S+5,expect_guard=dict(problem='unsupported_odd_data_access'),note='A7 = 1feffd (odd): the final RTS reads an odd LONG')
    cust(items,'guard-buf-odd-a7-debug-push','buf',dict(G['tmpl_buf']),a7=S+1,a7_stop=S+5,expect_guard=dict(problem='unsupported_odd_data_access'),note='A7 = 1feffd (odd): MOVE.L A6,-(A7) at 4aa94 writes an odd LONG')
    cust(items,'guard-buf-odd-object','buf',dict(G['tmpl_buf']),setup=[W(0x10daf8,4,0x102001,'declared slot 0 object = 102001 (odd)'),W(0x102001+0x6d,1,0xf0,'declared BYTE 6d(object) = f0 so the slot filter passes')],expect_guard=dict(problem='unsupported_odd_data_access'),note='odd slot object A6: ADD.W 42(A6),D0 reads an odd WORD')
    cust(items,'guard-buf-odd-record','buf',dict(G['tmpl_buf']),setup=[W(0x10daf8+4,4,0x106001,'declared slot 0 record = 106001 (odd)')],expect_guard=dict(problem='unsupported_odd_data_access'),note='odd record A0: MOVE.L (A0)+,D0 reads an odd LONG')
    cust(items,'guard-buf-odd-cursor','buf',dict(debug=0,slot_set=[],ring=0x10db89),expect_guard=dict(problem='unsupported_odd_data_access'),note='odd ring cursor: LSR.W (A0)+ reads an odd WORD')
    cust(items,'guard-buf-rom-cursor','buf',dict(debug=0,slot_set=[],ring=0x001000),expect_guard=dict(problem='unmapped_or_protected'),note='ring cursor in the program ROM: LSR.W (A0)+ writes ROM')
    cust(items,'guard-buf-a5-zero','buf',dict(debug=0,slot_set=[]),a5=0,expect_guard=dict(problem='unsupported_data_device'),note='declared A5 = 0: MOVEA.L 5c88(A5),A0 reads a ROM LONG as the ring cursor (an address in the 3xxxxx device window) and LSR.W (A0)+ is refused')
    # ---- e8a48: gate boundaries of the e8ad0 stream walk (BYTE 10de2e = 0)
    for allocate in (0,1):
        for phase in (0x000f,0x0010,0x0011,0x001f,0x0020,0x0021,0x002f,0x0030,0x0031,0xffff):
            cust(items,'cue-walk-alloc%d-phase-%04x'%(allocate,phase) if phase!=0xffff else 'guard-cue-walk-alloc%d-phase-ffff-no-terminator'%allocate,'cue',dict(manual=0,allocate=allocate,debug=0,count=4,phase=phase,gates=[0x0010,0x0020,0x0030,0xffff]),
                note='stream walk, gates 0010 0020 0030 ffff, WORD 10d418 = %04x%s'%(phase,' (CMP.W 12(A0),D0 with D0 = ffff never carries: the walk has no terminator)' if phase==0xffff else ''),expect_guard=dict(problem='step_limit') if phase==0xffff else None)
    for phase in (0x0000,0x000b,0x000c):
        cust(items,'cue-walk-long-phase-%04x'%phase,'cue',dict(manual=0,allocate=0,debug=0,phase=phase,gates=list(range(1,13))+[0xffff]),note='stream walk over twelve records, phase %04x'%phase)
    for phase in (0x0000,0x0001,0x0100,0x7fff,0xffff):
        cust(items,'cue-walk-rom-default-phase-%04x'%phase if phase!=0xffff else 'guard-cue-walk-rom-default-phase-ffff-no-terminator','cue',dict(manual=0,allocate=0,debug=0,cue=0xe89e4,stream=0xe89ec,phase=phase),note='default stream e89ec in the program ROM, phase %04x'%phase,expect_guard=dict(problem='step_limit') if phase==0xffff else None)
    cust(items,'cue-walk-null-stream-debug','cue',dict(manual=0,allocate=0,debug=1,stream=0,cue=0x106000),note='10de2a null: e8ad0 returns at once, 10de26 := 4 (null A0 + 4), debug sprite reads that cue')
    cust(items,'guard-cue-walk-unterminated-reaches-PVC','cue',dict(manual=0,allocate=0,debug=0,stream=0x2fdf00,phase=0xffff),expect_guard=dict(problem='unsupported_PVC_read_or_write'),note='stream pointer in the banked window with phase ffff: no BCS ever; the walk runs into the PVC window (no terminator in the original)')
    # ---- 2986 / 28ae outcomes and SR image variants through e8a48
    for depth in (0x0000,0x7fff,0xffff):
        for b in (0x00,0x01,0x80):
            cust(items,'cue-success-parent10-%04x-byte6a-%02x'%(depth,b),'cue',dict(count=4,allocate=1,manual=1,debug=0,depth=depth),setup=[W(0x106100+0x6a,1,b,'declared BYTE 6a(original A6) = %02x'%b)],note='28ae success: parent WORD +10 = %04x (X = ADDQ carry), copied BYTE 6a = %02x (Z / N)'%(depth,b))
    for count in (0,4):
        for flags in (0,1,2,3):
            cust(items,'cue-xcarry-count%d-flags%d-carry'%(count,flags),'cue',dict(count=count,allocate=1,manual=1,debug=0,flags=flags,x=0xffff,y=0xffff,camera_x=1,camera_y=2),note='cue flags %d with a carrying ADD.W (x = ffff + camera 1, y = ffff + camera 2), allocation count %d'%(flags,count))
    # ---- stack aliasing of the re-read cue (cue struct inside the live stack) and of the copied BYTE 6a(A0) over the pushed SR WORD
    for pos in (S-8,S-10,S-12,S-16):
        for flags in (0,3):
            cust(items,'cue-alias-cue-at-S-%x-flags%d'%(S-pos,flags),'cue',dict(allocate=1,manual=1,debug=0,count=4,cue=pos),
                setup=[W(pos,2,0x0123,'declared cue WORD 0'),W(pos+2,2,0x0045,'declared cue WORD 2'),W(pos+4,1,flags,'declared cue BYTE 4 (flags)'),W(pos+7,1,0x1c,'declared cue BYTE 7 (tag 1c)')],
                note='cue struct at S-%x (inside the live stack): the pushes of e8a6a / the BSR return LONG overlap the re-read cue WORDs'%(S-pos))
    for byte in (0x20,0x27):
        cust(items,'guard-cue-overlap-6aA0-over-SR-word-high-byte-%02x'%byte,'cue',dict(allocate=1,manual=1,debug=0,count=4,node=0x10ef86),setup=[W(0x106100+0x6a,1,byte,'declared BYTE 6a(original A6) = %02x, copied over the high byte of the pushed SR WORD'%byte)],
            expect_guard=dict(problem='unsupported_code_target',target=2),
            note='free node 10ef86: 6a(A0) = 10eff0 = the pushed SR WORD (mirror of 1feff0); the copied BYTE %02x replaces the system byte before MOVE (A7)+,SR; the same node also makes e8a9c write the table WORDs 0000 0002 at 76(node) = 1feffc = the return LONG slot, so the final RTS jumps to 00000002'%byte)
    # ---- the wrapper 2986 / 298e entered directly (other callers of the same blocks); declared SR
    for path,over,a0 in (('success',dict(count=4),0xd5f16),('fail-bcc',dict(count=0),0xd5f16),('fail-beq',dict(count=4),0)):
        for ret in (0xe8a8a,0x480ea):
            for sr in (0x2000,0x2010):
                cust(items,'wrapper-2986-%s-ret%05x-sr%04x'%(path,ret,sr),'cue',dict(over,allocate=1,manual=1,debug=0),regs=dict(a0=a0,a1=0x100bf4,d0=0),entry=0x2986,ret=ret,sr=sr,model=True,group='custom-wrapper',
                    note='2986 entered directly: %s, caller return %x, declared initial SR %04x (X = %d)'%(path,ret,sr,(sr>>4)&1))
    for sr in (0x2001,0x2004,0x200f,0x201f):
        cust(items,'wrapper-2986-fail-bcc-sr%04x'%sr,'cue',dict(count=0,allocate=1,manual=1,debug=0),regs=dict(a0=0xd5f16,a1=0x100bf4,d0=0),entry=0x2986,ret=0xe8a8a,sr=sr,group='custom-wrapper',note='2986 failure, declared initial SR %04x'%sr)
    for sr in (0x2000,0x2010,0x2001):
        for a0 in (0x100400,0x100e98):
            cust(items,'wrapper-298e-a0-%06x-sr%04x'%(a0,sr),'cue',dict(count=4,allocate=1,manual=1,debug=0),regs=dict(a0=a0,a6=0x106100),entry=0x298e,ret=0x480ea,sr=sr,stack_ret=False,
                stack_extra=[(S,(0x106100).to_bytes(4,'big')),(S+4,(0x480ea).to_bytes(4,'big'))],a7_stop=S+8,group='custom-wrapper',note='298e entered directly: saved A6 LONG at A7, return LONG 480ea behind it, A0 = %x, declared SR %04x'%(a0,sr))
    # ---- e8af4 / e8ad0 entered directly (other callers 47baa / e8c3c)
    for flags in range(4):
        for cx in (0,1):
            cust(items,'direct-e8af4-flags%d-carry%d'%(flags,cx),'cue',dict(flags=flags,x=0xffff if cx else 0x0010,y=0xffff if cx else 0x0020,camera_x=1,camera_y=2,allocate=0,debug=0),regs=dict(a0=0x106000),entry=0xe8af4,ret=0xe8a70,group='custom-direct',note='e8af4 entered directly: cue flags %d, carrying=%d'%(flags,cx))
    for phase in (0x0000,0x0010,0x0011,0xffff):
        cust(items,'direct-e8ad0-phase-%04x'%phase if phase!=0xffff else 'guard-direct-e8ad0-phase-ffff-no-terminator','cue',dict(manual=0,allocate=0,debug=0,phase=phase,gates=[0x0010,0x0020,0xffff]),entry=0xe8ad0,ret=0xe8aba,group='custom-direct',note='e8ad0 entered directly, phase %04x'%phase,expect_guard=dict(problem='step_limit') if phase==0xffff else None)
    cust(items,'direct-e8ad0-null','cue',dict(manual=0,allocate=0,debug=0,stream=0),entry=0xe8ad0,ret=0xe8aba,group='custom-direct',note='e8ad0 entered directly with 10de2a = 0')
    # ---- bank 3 entry of the cue stage
    for count in (0,4):
        cust(items,'cue-bank3-count%d'%count,'cue',dict(count=count,allocate=1,manual=1,debug=1,consumer=0x100,prepared=0x80),bank=3,note='initial bank 3 at e8a48, allocation count %d, debug sprite submitted'%count)
    # ---- guards (cue)
    cust(items,'guard-cue-odd-a7-push','cue',dict(allocate=1,manual=1,debug=0,count=4),a7=S+1,a7_stop=S+5,expect_guard=dict(problem='unsupported_odd_data_access'),note='A7 = 1feffd (odd): the first push writes an odd WORD')
    cust(items,'guard-cue-odd-cue','cue',dict(allocate=1,manual=1,debug=0,count=4,cue=0x106001),expect_guard=dict(problem='unsupported_odd_data_access'),note='odd cue pointer: MOVE.W (A0),D0 reads an odd WORD')
    cust(items,'guard-cue-odd-stream','cue',dict(manual=0,allocate=0,debug=0,stream=0x106201),expect_guard=dict(problem='unsupported_odd_data_access'),note='odd stream pointer: CMP.W 12(A0),D0 reads an odd WORD')
    cust(items,'guard-cue-a5-zero','cue',dict(allocate=1,manual=1,debug=0,count=4),a5=0,expect_guard=dict(problem='unmapped_or_protected'),note='declared A5 = 0: CLR.B 5e2f(A5) / MOVE.L A1,5e26(A5) write the ROM')
    cust(items,'guard-cue-bad-stop-outside-ranges','cue',dict(allocate=0,manual=1,debug=0),ret=0x4939c,entry_stop=RET_E8A48,expect_guard=dict(problem='unsupported_code_target',target=0x4939c),note='the return LONG is 4939c (TRAP #15 PC outside every observed range) while the declared stop is 480ea: the fetch is refused, not a stop')
    cust(items,'guard-buf-bad-stop-outside-ranges','buf',dict(debug=0,slot_set=[]),ret=0x4939c,entry_stop=RET_4AA88,expect_guard=dict(problem='unsupported_code_target',target=0x4939c),note='the return LONG is 4939c while the declared stop is 480d2: the fetch is refused, not a stop')
    return items


def main():
    global OUT,KEY_PCS
    t_start=time.time()
    dev=os.environ.get('BC_DEV');workers=int(os.environ.get('BC_WORKERS','4'))
    out_dir=OUT if not dev and not os.environ.get('BC_OUT') else Path(os.environ.get('BC_OUT','/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/u7obs/dev_out'))
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    OUT=out_dir
    ext=configure(program,out_dir)
    OUT=out_dir
    KEY_PCS=tuple(sorted(LEAD_PCS|set(MARK_PCS)|{0xcda4,0x3aea,FRAME_RET}))
    static=static_checks(program)
    # ---- seeds
    stage_specs,stage_rows,stage_folder,stage_info=stage_chain_specs(program)
    ver,rows_in=sc.stage_frame_inputs(program)
    entry_obs=json.loads(sc.pin(sc.STAGE_ENTRY,sc.STAGE_ENTRY_SHA));assert len(entry_obs['results'])==142
    typed=typed_conditions(program)
    G.update(program=program,stage_specs=stage_specs,stage_rows=stage_rows,stage_folder=stage_folder,stage_inputs={i:ram for i,r,ram,how in rows_in},entry_obs=entry_obs,typed=typed)
    ITEMS.clear()
    for i in range(len(stage_specs)):ITEMS.append(dict(kind='stage',ref=i))
    for i in range(len(entry_obs['results'])):ITEMS.append(dict(kind='entry',ref=i))
    seq_groups={}
    for i,c in enumerate(typed):
        if c['sequence'] is not None:
            seq_groups.setdefault((c['group'],c['sequence']),[]).append(i)
        else:ITEMS.append(dict(kind='typed',ref=i))
    for key,idxs in sorted(seq_groups.items()):ITEMS.append(dict(kind='typed',ref=idxs[0],seq=len(idxs)))
    G['custom']=build_custom(program)
    for i in range(len(G['custom'])):ITEMS.append(dict(kind='custom',ref=i))
    labels=[None]*len(ITEMS)
    if dev:
        keep=[i for i,it in enumerate(ITEMS) if any(f in '%s-%s-%s'%(it['kind'],it['ref'],(typed[it['ref']]['label'] if it['kind']=='typed' else '')) for f in dev.split(','))]
    else:keep=list(range(len(ITEMS)))
    print('items',len(ITEMS),'selected',len(keep),'seeds %.1fs'%(time.time()-t_start),flush=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,sc.CONTRACT,fh.CONTRACT,sc.STAGE_FRAME,sp.su.CONTRACT,sp.mw.CONTRACT,sp.CONTRACT,inp.CONTRACT}
    input_paths.update(Path(p) for p in sc.SEED_FILES)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin_ref=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin_ref['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    # ---- run
    done={}
    if workers>1:
        ctx=multiprocessing.get_context('fork')
        with ctx.Pool(workers) as pool:
            for n,r in enumerate(pool.imap_unordered(run_item,keep,chunksize=1)):
                done[r['number'] if 'error' not in r else r['number']]=r
                if (n+1)%25==0 or 'error' in r:print('%d/%d %.0fs%s'%(n+1,len(keep),time.time()-t_start,' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    else:
        for n,i in enumerate(keep):
            r=run_item(i);done[i]=r
            print('%d/%d %s %.1fs%s'%(n+1,len(keep),r.get('result',{}).get('label',ITEMS[i]),r.get('seconds',0),' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    errors=[done[i] for i in keep if 'error' in done[i]]
    if errors:
        for e in errors[:10]:print(e['number'],e['kind'],e['ref'],e['error'],'\n',e['trace'][-800:])
        raise SystemExit('%d work items failed'%len(errors))
    rows=[done[i] for i in keep]
    return finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,rows,static,stage_info,t_start,ext,dev)


def aggregate(rows):
    t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
    for r in rows:
        for ph in r['phases']:
            for k,v in ph['counts'].items():t[k]+=v
    return t


def finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,rows,static,stage_info,t_start,ext,dev):
    results=[r['result'] for r in rows if not r['result']['guarded']];guards=[r['result'] for r in rows if r['result']['guarded']]
    artifacts={}
    for r in results+guards:
        for key in ('phases','continuous_control'):
            for ph in r[key]:artifacts.update(ph['artifacts'])
    models=[m for r in rows for m in r['models']];sr_rows=[x for r in rows for x in r['sr']]
    by_group=collections.defaultdict(list)
    for r in rows:by_group[r['result']['group']].append(r)
    coverage=set();hits=collections.Counter();hit_conditions=collections.defaultdict(set);hit_groups=collections.defaultdict(collections.Counter);first_label={}
    for r in rows:
        if r['result']['guarded']:continue
        coverage.update(r['covered'])
        for pc,n in r['hits'].items():
            hits[pc]+=n;hit_conditions[pc].add(r['number']);hit_groups[pc][r['result']['group']]+=1
            first_label.setdefault(pc,r['result']['label'])
    stage_hit=set()
    for r in by_group['stage-frame']:stage_hit.update(r['hits'])
    start_cov={hex(pc):dict(hits=hits.get(pc,0),conditions=len(hit_conditions.get(pc,())),groups=dict(hit_groups.get(pc,{})),first_condition=first_label.get(pc),in_stage_frame_rows=pc in stage_hit,in_machine_entry_frames=any(pc in r['hits'] for r in by_group['stage-entry'])) for pc in sorted(U7_STARTS)}
    covered_starts=[pc for pc in U7_STARTS if hits.get(pc,0)>0];uncovered=[hex(pc) for pc in U7_STARTS if hits.get(pc,0)==0]
    never_stage=sorted(hex(pc) for pc in U7_STARTS if pc not in stage_hit)
    stage_compare=[c for r in by_group['stage-frame'] for c in r['compare']]
    entry_compare=[dict(case=r['result']['label'],**c) for r in by_group['stage-entry'] for c in r['compare']]
    frame_counts=dict(stage_frame_rows=len(stage_compare),stage_frame_rows_equal_recorded=sum(1 for c in stage_compare if c['ok']),stage_frame_rows_returned=sum(1 for c in stage_compare if not c['waiting']),
        stage_frame_rows_wait=sum(1 for c in stage_compare if c['waiting']),stage_frame_rows_wait_cda4=sum(1 for c in stage_compare if c['waiting'] and c['recorded_stage'] in (1,2)),stage_frame_rows_wait_3aea=sum(1 for c in stage_compare if c['waiting'] and c['recorded_stage']==3),
        stage_frame_chains=len(by_group['stage-frame']),carried_inputs_checked=sum(1 for c in stage_compare if c.get('carried_input_checked')),carried_inputs_equal=sum(1 for c in stage_compare if c.get('carried_input_checked') and c.get('carried_input_equal_outside_stack_window')),
        stage_entry_cases=len(entry_compare),stage_entry_equal_original=sum(1 for c in entry_compare if c['ok']),stage_entry_returned_first_step=sum(1 for c in entry_compare if not c['waiting']),stage_entry_wait_first_step=sum(1 for c in entry_compare if c['waiting']),
        stage_entry_conditions_with_waits=sum(1 for r in by_group['stage-entry'] if r['waits']),
        model_segments=len(models),model_segments_equal=sum(1 for m in models if m['equal']),model_by_segment={k:sum(1 for m in models if m['segment']==k) for k in ('buffer','cue')})
    for c in stage_compare+entry_compare:
        if not c['ok']:DISCREPANCIES.append(dict(label=c.get('recorded_label') or c.get('case'),kind='native-vs-recorded-original',detail={k:v for k,v in c.items() if v is False}))
    for r in rows:
        if r['compare'] and r['result']['group'] in ('stage-frame','stage-entry'):pass
    data=(json.dumps(dict(source=source,ranges=U7_RANGES,instructions=[x for lo,hi in U7_RANGES for x in disassemble_range(program,lo,hi-lo,lo)],boundary_stop_pcs=(RET_4AA88,RET_E8A48,FRAME_RET),wait_pcs=WAIT_PCS,
        stop_rules={'return':'RTS that pops the declared return LONG (480d2 for 4aa88, 480ea for e8a48, 2ac2 for the whole frame); the code behind it is never executed','wait':'cda4 (sprite queue, blocked when WORD 108d34 <> D4.W) and 3aea (sound ring, blocked when WORD 104d74 = D1.W): first blocked arrival, before the instruction executes'},
        new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in U7_RANGES}),indent=2)+'\n').encode()
    (out_dir/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard']) for g in guards]
    group_counts={}
    for r in results+guards:group_counts[r['group']]=group_counts.get(r['group'],0)+1
    claims=contract_claims(rows,static,sr_rows,start_cov,stage_hit,frame_counts,models)
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    seeds=dict(stage_frame=stage_info,stage_entry=dict(observation_file=str(sc.STAGE_ENTRY),observation_sha256=sc.STAGE_ENTRY_SHA,cases=142),
        chains=[dict(label=r['result']['label'],rows=r['result']['provenance'].get('rows'),input_sha256=r['result']['provenance'].get('input_sha256'),rebuilt_from=r['result']['provenance'].get('rebuilt_from'),labels=r['result']['provenance'].get('labels')) for r in by_group['stage-frame']],
        entries=[dict(label=r['result']['label'],input_ram_sha256=r['result']['provenance'].get('input_ram_sha256'),entry_ram_sha256=r['result']['provenance']['entry_state']['ram_sha256']) for r in by_group['stage-entry']],
        files=dict(sorted(sc.SEED_FILES.items())),typed=dict(buffer_cases=sum(1 for r in by_group['typed-buffer']),cue_cases=sum(1 for r in by_group['typed-cue']),
        note='tools/observe_stage_buffer_frame.build_cases / fixture and tools/observe_stage_cue_frame.build_cases / fixture (read-only generators): RAM image + 14 registers; entries 4aa88 / e8a48 with the real caller return LONG; the stack lives in the work-RAM mirror'),
        note='Declared initial fixture: the stage-frame verifier smoke() RAM (pinned against artifacts/stage_frame/verification.json input_sha256) or the recorded native outputs with their recorded result registers, A5=108000, A7=1feffc, return LONG 2ac2 at A7, zero PVC page with the two bank registers; the 480bc entry state of the 142 stage_entry_body cases is captured from the original body run.')
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=dict(sorted(artifacts.items())),results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=sum(r['split_phases'] for r in rows),total_control_phases=sum(r['control_phases'] for r in rows),fresh_CPU_runs=sum(r['runs'] for r in rows),normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=0,variant_child_layouts=[],guard_reports=guard_reports,bank_reads_by_condition=[dict(label=r['summary']['label'],bank_read_count=r['summary']['bank_read_count']) for r in rows if r['summary']['bank_read_count']],bank_descriptor_search=[],
        new_ranges=U7_RANGES,existing_ranges=tuple(RANGES_EXISTING()),observer_extension=ext,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=TABLE),static_checks=static,
        contract_model_checks=models,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=observed_facts(rows),sr_images=sr_rows,
        full_frame=dict(counts=frame_counts,stage_frame_row_comparison=stage_compare,stage_entry_comparison=entry_compare),block_start_coverage=start_cov,block_starts_covered=len(covered_starts),block_starts_uncovered=uncovered,
        block_starts_not_in_stage_frame_rows=never_stage,seed_provenance=seeds,condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=[r['summary'] for r in rows],group_counts=group_counts,covered_PCs=sorted(coverage),block_starts=sorted(U7_STARTS),boundary_stop_pcs=(RET_4AA88,RET_E8A48,FRAME_RET),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[],oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        stop_rule_selftests=stop_selftests(program),limitations=LIMITATIONS,wall_seconds=None)
    report.pop('wall_seconds')
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    summary=dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_segments=len(models),model_equal=sum(1 for m in models if m['equal']),
        block_starts_covered=len(covered_starts),uncovered=uncovered,frames=frame_counts,sha256=sha(path.read_bytes()),tool=tool_sha,seconds=round(time.time()-t_start))
    print(json.dumps(summary))
    return summary


def stop_selftests(program):
    """Negative tests of the stop rule: a run that stops at a block start reached by a not-taken branch (e8a50, previous instruction BEQ.W at e8a4c) or at an internal PC after a MOVE is refused as a return stop."""
    out=[]
    import observe_stage_cue_frame as scf
    c=next(c for c in scf.build_cases(ROOT) if c['family']=='allocated-XY-flags-WORD-wrap-fallback');ram_,regs=scf.fixture(c)
    for stop in (0xe8a50,0xe8a6a,0xe8aae):
        fx=direct_fx('selftest-stop-%x'%stop,ram_,regs,2,0xe8a48,RET_E8A48,dict(kind='stop rule self test'))
        steps=[dict(label='st',changes=[],stop_pc=stop,checkpoints=[],a7=('entry',0))]
        spec=dict(label=fx['label'],fixture=fx,steps=steps)
        phases=run_chain(program,spec,True)
        try:
            annotate(program,phases);accepted=True;detail=None
        except AssertionError as e:
            accepted=False;detail=repr(e)[:200]
        prev=phases[-1]['pcs'][-2];out.append(dict(stop=hex(stop),previous_pc=hex(prev),previous_bytes=program[prev:prev+2].hex(),refused_as_return_stop=not accepted,detail=detail))
    assert all(x['refused_as_return_stop'] for x in out),out
    return out


def RANGES_EXISTING():
    return tuple(r for r in RANGES if r not in U7_RANGES)


def observed_facts(rows):
    facts=dict(waits=[],stack=dict(),entry_frame_instruction_counts=collections.Counter())
    for r in rows:
        for w in r['waits']:facts['waits'].append(dict(label=r['result']['label'],**w))
    for r in rows:
        if r['result']['group']=='stage-entry':facts['entry_frame_instruction_counts'][r['summary']['instructions']]+=1
    facts['entry_frame_instruction_counts']=dict(sorted(facts['entry_frame_instruction_counts'].items()))
    return facts


LIMITATIONS=['Controlled incoming fixtures (stage-frame seeds, the 480bc entry states of the original stage_entry_body runs, the typed buffer / cue corpora and declared host variations), not natural scheduler / gameplay reachability; '
    'a declared direct entry at a unit PC with the real caller return LONG is a declared fixture (PC, return LONG, initial registers, RAM), never applied after execution begins.',
    'Native carry / CCR is never read (SR is unobserved); branch decisions are evidenced by the executed PC path and the register file at every block leader.  The one CCR-dependent value, the WORD pushed by MOVE SR,-(A7) at 2990, is observed as an ordered RAM write.  '
    'A fresh CPU starts with the declared SR 2000 (CCR 0), also for the direct entries; the CCR at the capture point of the original run is not known.',
    'Wait stops are taken at the FIRST blocked arrival at cda4 / 3aea (the recorded stage-frame observer stops at the second blocked visit); the spin loops write nothing so the machine state is the same.  The hold / release rows carry external 255 in the recorded verifier; no external read occurs in those steps, so the native steps do not declare it.',
    'Frame re-entry (carried frames) is a declared PC redirect + A7 delta; the stale stack bytes below 1feffc stay in the work-RAM mirror (the recorded observers keep the stack outside the 64KiB image), so output RAM is compared with the recorded run outside the stack window [lowest stack-region write, 10f000).',
    'The model replays the native exit state of the black boxes cd58 (sprite) and 43e08 (cleanup); everything inside them is observed natively only.  28ae is modelled in full only as far as it is reached from 2986 (CCR for the pushed WORD).',
    'Full 64KiB RAM / 16 registers / PC / live A7, readonly bank2/3 data, raw PVC separate; no banked code / PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles / pixel output.',
    'The game meaning of 10f001 bits, the slot table 10daf8, the ring 10db88..10dc87, the double buffer 10d746/10d918, 10de2e/10de2f and the stream records remains unknown (contract unknown items).']


def contract_claims(rows,static,sr_rows,start_cov,stage_hit,frame_counts,models):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    claim('4 code ranges (778 bytes, 219 instructions, 0 undecoded) equal the ROM; their concatenation SHA256 is aa13f52b...c574','confirmed' if static['undecoded']==0 else 'contradicted',dict(instructions=static['instructions'],table=static['table']))
    claim('60 block starts = the leaders decoded from the original opcodes (range starts, branch / call targets, instructions after conditional branches and calls); the contract lists 17+13+28+2','confirmed',dict(block_starts=static['block_starts']))
    bad=[b for b in static['bundled_branches'] if not b['is_conditional_branch'] or b['is_block_start']]
    claim('24 bundled branch PCs are conditional branches that are not block starts','confirmed' if not bad else 'contradicted',dict(checked=len(static['bundled_branches']),bad=bad))
    claim('the 15 carry-preserving (flow-only) blocks are exactly the blocks whose instructions are all in the flow-only class','confirmed' if static['flow_only_equal_contract'] else 'contradicted',dict(decoded=static['flow_only_blocks_decoded'],contract=static['flow_only_blocks_contract']))
    exp17=sorted(['0x4ab5a','0x4ab6e','0x4b794','0x4b7a4','0x4b7b8','0x4b7f4','0x4b800','0xe8ab6','0xe8aba','0xe8ad0','0xe8adc','0xe8ae0','0xe8ae8','0xe8aee','0xe8af2','0xe8b04','0xe8b12'])
    never=sorted(hex(pc) for pc in U7_STARTS if pc not in stage_hit)
    claim('the 96 recorded stage-frame rows execute 43 of the 60 block starts; the 17 never-exercised starts are 4ab5a 4ab6e 4b794 4b7a4 4b7b8 4b7f4 4b800 e8ab6 e8aba e8ad0 e8adc e8ae0 e8ae8 e8aee e8af2 e8b04 e8b12','confirmed' if never==exp17 else 'contradicted',
        dict(native_never_exercised_by_stage_frame_chains=never,expected=exp17,executed=60-len(never)))
    unc=[k for k,v in start_cov.items() if v['hits']==0]
    claim('every one of the 60 block starts is executed by at least one native condition of this observation','confirmed' if not unc else 'not-reproduced',dict(uncovered=unc,covered=60-len(unc)))
    claim('28ae success (2908 ORI #1,CCR) is not executed by any recorded 480bc stage-frame row (28ae fails in row 42: 104ca0 = 0)','confirmed' if 0x28de not in stage_hit else 'contradicted',dict(stage_hit_28de=0x28de in stage_hit))
    claim('every model segment (leader sequence with full registers, ordered RAM writes incl. the pushed SR WORD, ordered ROM reads, ordered ports, final registers, 64KiB RAM, bank) equals the native run','confirmed' if frame_counts['model_segments']==frame_counts['model_segments_equal'] else 'contradicted',
        dict(segments=frame_counts['model_segments'],equal=frame_counts['model_segments_equal'],by_segment=frame_counts['model_by_segment']))
    claim('all 96 recorded stage-frame rows rebuilt with A7 = 1feffc and the return LONG 2ac2 reproduce the recorded original (14 registers, PC, A7, bank, ordered ports, output RAM outside the stack window, live stack, instruction sequence)','confirmed' if frame_counts['stage_frame_rows']==frame_counts['stage_frame_rows_equal_recorded']==96 else 'contradicted',
        dict(rows=frame_counts['stage_frame_rows'],equal=frame_counts['stage_frame_rows_equal_recorded'],returned=frame_counts['stage_frame_rows_returned'],waits=frame_counts['stage_frame_rows_wait']))
    claim('all 142 stage_entry_body first frames reproduce the original tail 480bc -> 480f0 (137 reach the RTS, 5 wait at 3aea)','confirmed' if frame_counts['stage_entry_cases']==frame_counts['stage_entry_equal_original']==142 and frame_counts['stage_entry_wait_first_step']==5 else 'contradicted',
        dict(cases=frame_counts['stage_entry_cases'],equal=frame_counts['stage_entry_equal_original'],returned=frame_counts['stage_entry_returned_first_step'],wait=frame_counts['stage_entry_wait_first_step']))
    if sr_rows:
        by=collections.Counter((x['path'],x['contract_equal']) for x in sr_rows)
        ok=all(x['contract_equal'] in (True,None) for x in sr_rows) and all(x['model_equal'] in (True,None) for x in sr_rows)
        claim('the WORD pushed by MOVE SR,-(A7) at 2990 is (system byte 20) + the CCR image of the contract table: success C=1 V=0 Z/N=BYTE 6a X=ADDQ carry; failure by 28ba C=0 V/N/Z=CMP.W D0.W-WORD 104ca0 X=caller X; failure by 28c2 Z=1 only; caller X in the e8a48 context = the last ADD.W carry of e8af4','confirmed' if ok else 'contradicted',
            dict(images=len(sr_rows),by_path_and_contract_equal={'%s/%s'%k:v for k,v in sorted(by.items(),key=lambda kv:str(kv[0]))},mismatches=[x for x in sr_rows if x['contract_equal'] is False or x['model_equal'] is False][:10]))
    # ---- recorded-row facts (stage-frame chains)
    stage=[r for r in rows if r['result']['group']=='stage-frame'];cmp_rows=[c for r in stage for c in r['compare']]
    by_row={c['row']:c for c in cmp_rows}
    wrap=sorted(k for k,c in by_row.items() if 0x4ab2e in c['leader_pcs'])
    claim('ring wrap (4ab2e) happens in the recorded smoke frames 7 and 15 only','confirmed' if wrap==[7,15] else 'contradicted',dict(rows_with_4ab2e=wrap))
    starts=[k for k,c in by_row.items() if c['incoming_stage']==0]
    exg=sorted(k for k in starts if 0x4ab86 in by_row[k]['leader_pcs'])
    claim('EXG (4ab86) is executed in 42 of the 64 stage-0 start rows (BYTE 10d744 bit7 toggles every frame)','confirmed' if len(starts)==64 and len(exg)==42 else 'contradicted',dict(start_rows=len(starts),rows_with_exg=len(exg)))
    r42=by_row.get(42)
    if r42:
        want={0xe8a50,0xe8a6a,0xe8af4,0xe8a70,0x2986,0x28ae,0x290e,0x298e,0xe8a8a,0x43e08,0xe8a9c,0xe8aae,0xe8ac2,0xe8ace}
        have=set(r42['leader_pcs'])
        sr42=[x for x in sr_rows if x['label'].startswith('rows42-')]
        claim('active-cue-allocation (row 42): e8a50 -> e8a6a -> e8af4 -> e8a70 -> 2986 -> 28ae fails (290e) -> 298e -> e8a8a -> 43e08 -> e8a9c -> e8aae -> e8ac2 -> e8ace and the pushed SR WORD is 2004 at 1fefec (STACK-16)','confirmed' if want<=have and 0x28de not in have and sr42 and sr42[0]['native_word']=='2004' and sr42[0]['address']=='0x1fefec' else 'contradicted',
            dict(missing=sorted(hex(x) for x in want-have),sr=sr42[:1]))
    u7set={0x4aa88,0x4aafe,0x4ab32,0x4ab74,0x4ab86,0x4ab88,0xe8a48,0xe8aae,0xe8ac2,0xe8ace}
    entry=[r for r in rows if r['result']['group']=='stage-entry']
    sets=collections.Counter(tuple(sorted(pc for pc in r['hits'] if pc in set(U7_STARTS))) for r in entry)
    claim('all 142 stage_entry_body first frames take the same U7 path 4aa88 -> 4aafe -> 4ab32 -> 4ab74 -> 4ab86 -> 4ab88 and e8a48 -> e8aae -> e8ac2 -> e8ace','confirmed' if len(sets)==1 and set(next(iter(sets)))==u7set else 'contradicted',
        dict(distinct_paths=len(sets),path=[hex(x) for x in next(iter(sets))] if sets else None,cases=len(entry)))
    ew=sorted(int(r['result']['label'].split('-')[1]) for r in entry if r['waits'])
    claim('the 5 stage_entry_body frames that wait are native_0136..0140 (sound ring wait at 3aea after 2efa6)','confirmed' if ew==[136,137,138,139,140] and all(w['pc']==0x3aea for r in entry for w in r['waits']) else 'contradicted',dict(cases=ew))
    waits={ (r['result']['label'],w['step']):w for r in stage for w in r['waits']}
    first=waits.get(('rows43-46-buffer-first-start',0));second=waits.get(('rows43-46-buffer-first-start',2));cue=waits.get(('rows50-52-cue-start',0))
    ok=bool(first and second and cue and first['a7']==S-38 and second['a7']==S-26 and cue['a7']==S-8 and first['pc']==second['pc']==cue['pc']==0xcda4)
    claim('sprite waits stop at PC cda4 with A7 = U-38 (first sprite, 4b7d4), U-26 (second sprite, 4b80e) and U-8 (debug cue, e8b52), U = A7 at the 480bc entry','confirmed' if ok else 'contradicted',dict(first=first,second=second,cue=cue))
    ws={}
    for r in rows:
        for w in r.get('wait_stacks',[]):
            if r['result']['label'] in ('rows43-46-buffer-first-start','rows50-52-cue-start') and w['step'] in (0,2):ws[(r['result']['label'],w['step'])]=w['stack_hex']
    def longs(hexs,base_a7):
        raw=bytes.fromhex(hexs);return {S-(base_a7+off):int.from_bytes(raw[off:off+4],'big') for off in range(0,len(raw)-3,2)}
    f=ws.get(('rows43-46-buffer-first-start',0))
    if f:
        raw=bytes.fromhex(f);n=len(raw)         # live stack from A7 = S-38 up to S+4
        at=lambda depth,size:int.from_bytes(raw[n-4-depth+0:n-4-depth+size] if False else raw[(S-depth)-(S-38):(S-depth)-(S-38)+size],'big')
        stack=dict(ret_4b7da=at(38,4),a0=at(34,4),d7=at(30,4),d1=at(26,4),d0=at(22,4),ret_4aad4=at(18,4),slot_d7_w=at(14,2),slot_a4=at(12,4),outer_a6=at(8,4),ret_480d2=at(4,4),ret_slot=at(0,4))
        claim('first-sprite wait stack: U-4 480d2, U-8 outer A6, U-12 slot A4, U-14 slot D7.W, U-18 4aad4, U-22 D0, U-26 D1, U-30 D7, U-34 A0, U-38 4b7da','confirmed' if stack['ret_4b7da']==0x4b7da and stack['ret_4aad4']==0x4aad4 and stack['ret_480d2']==0x480d2 else 'contradicted',{k:hex(v) for k,v in stack.items()})
    # ---- stack depth: deepest write below U (frame conditions: U = 1feffc; direct entries: the return slot is U-4, so U = 1feffc + 4)
    by_label={r['result']['label']:r for r in rows}
    def depth_of(label,seg,u=S):
        r=by_label.get(label)
        return None if r is None or seg not in r.get('stack_deepest_write',{}) else u-r['stack_deepest_write'][seg]
    slot=depth_of('rows43-46-buffer-first-start','buffer');dbg=depth_of('rows50-52-cue-start','cue')
    alloc=max([S+4-r['stack_deepest_write']['cue'] for r in rows if r['result']['group']=='typed-cue' and 'cue' in r.get('stack_deepest_write',{}) and 0x28de in r['hits']] or [None])
    claim('deepest stack write below U (U = A7 at the 480bc entry): slot path 42 (cd58 callback JSR, rows 43), allocation path 26 (28ae success push; typed cue conditions with 28de), debug cue path 12 (cd58 callback JSR, row 50)','confirmed' if (slot,alloc,dbg)==(42,26,12) else 'contradicted',
        dict(slot_path=slot,allocation_success_path=alloc,debug_cue_path=dbg,allocation_failure_path_row42=depth_of('rows42-42-active-cue-allocation','cue')))
    d1=sorted({b for r in rows for b in r['summary'].get('cd58_entries',[])});n58=sum(1 for r in rows if r['summary'].get('cd58_entries'))
    claim('D1 bit 6 is always 0 when cd58 is entered from 4b784 / e8b18 (so cdb2 takes the normal branch)','confirmed' if d1==[0] and n58>0 else 'contradicted',dict(distinct_bit6_values=d1,conditions_with_cd58=n58))
    f42=[r['facts'] for r in rows if r.get('facts')]
    if f42:
        f=f42[0];w2992={x[0] for x in f['writes_2992']};wcue={x[0] for x in f['writes_e8aaa_e8aac']}
        claim('row 42 (28ae failure): the stack image has WORD 2004 at STACK-16 and WORD 0010 (high word of the saved A6 00100820) at STACK-18; the copied BYTE 6a and the table WORDs all go to the fallback object 100e98 (100f02, 100f0e, 100f10, 100ec6..100eeb)',
            'confirmed' if f['word_S_minus_16']=='2004' and f['word_S_minus_18']=='0010' and w2992=={'0x100f02'} and wcue=={'0x100f0e','0x100f10'} else 'contradicted',f)
    nulls=[r for r in rows if r['result']['label']=='cue-walk-null-stream-debug']
    if nulls:claim('e8ad0 with a null stream pointer (10de2a = 0) returns at once with A0 = 0, so 10de26 becomes 00000004','confirmed' if nulls[0]['summary']['end_state']['cue_10de26']==4 else 'contradicted',nulls[0]['summary']['end_state'])
    tab=set();exec_tags=set()
    for r in rows:
        tab.update(r['summary'].get('e8a0c_table_reads',[]))
        c=r['result']['provenance'].get('case')
        if r['result']['group']=='typed-cue' and c and c.get('family')=='all256-tags-exact32-allocation-index' and 0xe8a9c in r['hits']:exec_tags.add(c['tag'])
    claim('every e8a0c table index 0..1f is read (WORD pairs at e8a0c + 4*index) and the allocation block e8a9c runs for exactly the tags 1c..3b of the 256 tags','confirmed' if tab==set(0xe8a0c+4*i for i in range(32)) and exec_tags==set(range(0x1c,0x3c)) else 'contradicted',
        dict(table_indices_read=len(tab),missing=[hex(0xe8a0c+4*i) for i in range(32) if 0xe8a0c+4*i not in tab],tags_with_e8a9c=[hex(x) for x in sorted(exec_tags)][:2]+['...']+[hex(x) for x in sorted(exec_tags)][-2:],tag_count=len(exec_tags)))
    return claims


if __name__=='__main__':main()
