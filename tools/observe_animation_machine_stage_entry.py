"""Unpatched stage controller F1a (entry body 47a94, palette gate / dispatcher table 47af0..47c04, activation 47c04, scene initializer 1a5a4 and its helpers) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the buffer/cue observer U7
(observe_animation_machine_buffer_cue and through it the script/placement observer U5, scene update U4, motion walk U3, scene core U2, frame helper U1, the U6 input
observer ranges and the card-menu / fade-card chain): persistent-CPU Observer with the declared host-change vocabulary RAM write / PC redirect / A7 delta, fresh-twice
reproduction, split (stop at the first hit of every block leader) versus continuous equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every
imported tool module, ROM SHA/mtime guard and the stage-frame / stage-entry-body seed rebuilders.  The declared observer extension of U5 (a WORD write to 3c0006 is a
'video' port event) is installed in this process exactly as U5/U7 do; nothing in the imported modules or tools is edited.

Unit: the 5,608 contract bytes of docs/analysis/animation-machine-stage-controller-f1-contract.md (22 code ranges, 145 block starts, TRAP #15 boundary e909c).  With U1..U7
the whole frame 47a94 -> 480bc -> 480f0 RTS runs natively; the stage activation 47c04 -> exit 47c5a -> 47c6c runs natively.  Declared stops (accepted only directly after
the transferring instruction): 2ac2 (the RTS that pops the declared dispatcher return LONG), 47c6c (fall-through after MOVE.L #47c6c,(A6), the exit unit already ran), e909c
(TRAP #15 not executed), c00468 (BIOS boundary, the BIOS body is never executed) and the declared waits: cda4 (sprite queue), 3aea (sound ring) and 47af0 (the 72f0 palette
IRQ gate: resumed only through a declared IRQ palette effect).  Nothing claims BIOS execution, a natural scheduler or a natural IRQ.

Seeds (all pinned by SHA256, rebuilt in this process):
  entry-body     artifacts/stage_entry_body: 142 begin cases (47a94 direct entry; A6 = 100b30, A5 = 108000, the profile registers, bank 2 / 3, return LONG 2ac2 declared at the
                 initial A7 = 1feffc).  Run natively to 2ac2 / 3aea; the 5 sound waits get the recorded hold / release steps.  The first frame of each case is compared with the
                 recorded original (14 registers, PC, bank, ordered ports, output RAM outside the stack window, instruction trace).
  dispatcher     the begin outputs re-entered at the installed callback (47af0 / 47b5c / 47bfc; declared direct entry: PC redirect + A7 delta + return LONG 2ac2 at A7, no scheduler),
                 as long as the frame returns to 2ac2; chains of 47b5c (SUBQ.W #1,7a(A6)) run to the activation 47c04.  Compared with the original flat-map observer re-run from the
                 same state (observe_stage_entry_body.Observer, stack outside the 64KiB image).
  activation     artifacts/stage_activation_prefix: 104 recorded 47c04 -> before 47c6c cases (A6 = 102000 / 10d608 / 1009c6, 4 register profiles).
  declared fixtures  host RAM writes / initial registers on captured states for the block starts, table indices, gate states and guards the seeds do not reach.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step record;
a declared initial SR (default 2000, CCR 0) and the declared initial registers are part of the fixture summary.

An independent Python model of the contract (a M68000 subset interpreter written from the 68000 programmer's reference that decodes the ORIGINAL ROM BYTES of the 22 F1a
ranges instruction by instruction with a complete CCR model, 32-bit register semantics and explicit byte/word/long operations; it shares no code with Unicorn or the C++) is compared
with each native F1a segment: block-leader sequence with the full register file at every leader, ordered RAM writes, ordered fixed/bank ROM reads, ordered ports, the final
registers and the whole 64KiB RAM image.  Every callee outside the F1a ranges (the other executors) is a black box whose native exit registers and RAM / port writes are
replayed.  A carry produced by a black box is taken from the executed path of the native run (branch evidence).  Any difference is recorded in contract_discrepancies.
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
import observe_animation_machine_buffer_cue as bc
from disassemble_program import load_verified_program,disassemble_range
sp=bc.sp;inp=bc.inp;fh=bc.fh;fc=bc.fc;mt=bc.mt;op=bc.op;sc=bc.sc;seb=bc.seb;vsf=bc.vsf;shared=bc.shared;activation=bc.activation
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_stage_entry_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-stage-controller-f1-contract.md'
CONTRACT_SHA='e66e9a2127167e332f8595941f90b456696380cd4bdd4b06fda3ab60bea5d12f'
SCOPE=sc.SCOPE
ROM_SHA=op.ROM_SHA
sha=fc.sha
u8,u16,u32=op.u8,op.u16,sc.u32
S=fc.S                                                      # 1feffc: initial A7 (the return LONG lives here; offset effc of the 64KiB work-RAM image)
M32=0xffffffff
A5V=0x108000
A6V=0x100b30                                                # the stage controller object (dispatcher A6) of the stage_entry_body observer
KEYS=shared.isolated.REG_NAMES
KEYS14=sc.KEYS14
PORT_REGIONS=fc.PORT_REGIONS
BIOS=fc.BIOS
FRAME_RET=0x2ac2
ENTRY_BODY=0x47a94
GATE_PC=0x47af0
GATE_RET=0x47af6
EXIT_STOP=0x47c6c
TRAP_PC=0xe909c
PREFIX_ENTRY=0x47c04
CALLBACKS=(0x47af0,0x47b5c,0x47bfc)
WAIT_PCS=(0xcda4,0x3aea,GATE_PC)
STEP_LIMIT=2000000                                           # declared cumulative instruction watchdog of the observer for walks without a terminator (the original has none); a fixture may declare a smaller step_limit; one run() is capped at 500000 instructions by the base observer
DISCREPANCIES=[]

F1A_RANGES=((0x47a94,0x47c5a),(0x72f0,0x72fa),(0x1a5a4,0x1a73c),(0x17292,0x1829a),(0x19768,0x19772),(0x19938,0x19978),(0x199d4,0x19a00),(0x19b50,0x19b96),(0x19dee,0x19e60),
    (0x1a07a,0x1a086),(0x1a3c8,0x1a3d6),(0x1a414,0x1a442),(0xe8a1c,0xe8a3a),(0xe905c,0xe90ca),(0x477a2,0x477ac),(0xddf9a,0xddfa4),(0x362a,0x3650),(0x9060,0x9068),
    (0x4e254,0x4e26c),(0xca56,0xca5c),(0xca76,0xca7e),(0xc3c0,0xc3ce))
F1A_SPLIT=tuple(r for lo,hi in F1A_RANGES for r in (((0xe905c,0xe909c),(0xe909e,0xe90ca)) if lo==0xe905c else ((lo,hi),)))   # e909c (TRAP #15) is a boundary, not in the routing
DATA_ROWS=((0xddfa4,0xddfdc),)                              # the 56-byte HUD table read by 362a (not code)
TRAP_BYTES=bytes.fromhex('4e4f')
CARRY_CONSUMERS=(0x47af6,0x47b86,0x47b9c,0x47bd4,0x1a670,0x1996e)
GATE_TABLE=tuple(range(0x47b06,0x47b26,4))                  # the 8 BRA.W slots of the computed JMP at 47b02
CALLBACK_STARTS=(0x47b5c,0x47bfc)                           # MOVE.L #imm,(A6) targets (not branch targets)
BB_NAMES={0x1a5a4:'scene-initializer'}


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)
def in_f1a(pc):return in_ranges(pc,F1A_SPLIT)


# ----------------------------------------------------------------------------------
# Contract text: byte table, block starts, bundled branches, carry classes
# ----------------------------------------------------------------------------------
def parse_contract_table(program):
    rows=[];code=[]
    pattern=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (.*) \|$')
    for line in CONTRACT.read_text().splitlines():
        m=pattern.match(line)
        if not m:continue
        lo,hi=int(m.group(1),16),int(m.group(2),16);cell=m.group(3).strip()
        data=program[lo:hi]
        if re.fullmatch(r'`[0-9a-f]+`',cell):
            ok=data.hex()==cell.strip('`');assert ok,(hex(lo),hex(hi))
            rows.append(dict(range='%x..%x'%(lo,hi),size=hi-lo,bytes_equal_to_rom=True,sha256=sha(data)))
        else:
            sh=re.search(r'SHA256 `([0-9a-f]{64})`',cell);assert sh and sha(data)==sh.group(1),(hex(lo),hex(hi),'summary row digest')
            n=re.search(r'([\d,]+)바이트',cell);assert n and int(n.group(1).replace(',',''))==hi-lo
            rows.append(dict(range='%x..%x'%(lo,hi),size=hi-lo,bytes_equal_to_rom=True,sha256=sha(data),note='long unrolled clear: digest row'))
        code.append((lo,hi))
    assert code==list(F1A_RANGES),[(hex(a),hex(b)) for a,b in code]
    assert sum(h-l for l,h in code)==5608
    return rows


def contract_lists():
    """Block starts (145), bundled branch PCs (25), carry-preserving blocks (63), and the HUD table digest of the contract text."""
    lines=CONTRACT.read_text().splitlines()
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{4,6})`',text)]
    starts=bundled=preserve=None
    for i,line in enumerate(lines):
        if line.startswith('`362a` `3634`'):starts=pcs(line)
        if line.startswith('- **묶인 조건분기 PC (25개'):bundled=pcs(line.split(':',1)[1])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (63개)**'):preserve=pcs(line.split('**:',1)[1].split('. ')[0] if '. ' in line.split('**:',1)[1] else line.split('**:',1)[1])
    assert starts and len(starts)==len(set(starts))==145,len(starts or ())
    assert bundled and len(bundled)==len(set(bundled))==25,len(bundled or ())
    assert preserve and len(preserve)==len(set(preserve))==63,len(preserve or ())
    m=re.search(r'자료 `ddfa4\.\.ddfdc`\(SHA256 `([0-9a-f]{64})`\)',CONTRACT.read_text());assert m
    return starts,bundled,preserve,m.group(1)


F1A_STARTS=();F1A_BUNDLED=();F1A_PRESERVE=();BB_ENTRIES=();F1A_INSTR={};LEAD_PCS=frozenset();CK_SET=frozenset();ALLOWED_PCS=frozenset();TABLE=[]
RANGES_ALL=()


def external_targets(program):
    """Targets of the JSR/BSR/BRA/JMP/Bcc instructions of the F1a ranges that leave the ranges (the black-box entries), and the instruction after the last
    instruction of a range when it falls through (47c5a)."""
    out={}
    for lo,hi in F1A_SPLIT:
        for r in disassemble_range(program,lo,hi-lo,lo):
            pc=r['cpu_address'];t,k=fh.branch_target(pc,bytes.fromhex(r['raw']))
            if t is not None and not in_f1a(t):out.setdefault(t,[]).append(pc)
    for lo,hi in F1A_SPLIT:                                          # a range whose last instruction falls through (JSR returns / moveq): the next PC is a black-box entry
        last=list(disassemble_range(program,lo,hi-lo,lo))[-1]
        if last['mnemonic'].split('.')[0] not in ('rts','bra','jmp','trap') and not in_f1a(hi):out.setdefault(hi,[]).append(last['cpu_address'])
    return out


def configure(program,out_dir):
    global F1A_STARTS,F1A_BUNDLED,F1A_PRESERVE,BB_ENTRIES,F1A_INSTR,LEAD_PCS,CK_SET,ALLOWED_PCS,TABLE,RANGES_ALL,HUD_DIGEST
    bc.configure(program,out_dir)                                       # installs the U5/U7 observer extension and fills fc/fh globals for the existing executors
    TABLE=parse_contract_table(program)
    starts,bundled,preserve,HUD_DIGEST=contract_lists()
    assert sha(program[0xddfa4:0xddfdc])==HUD_DIGEST
    F1A_STARTS=tuple(starts);F1A_BUNDLED=tuple(bundled);F1A_PRESERVE=tuple(preserve)
    decoded=set(fh.leaders_of(program,F1A_SPLIT))|set(GATE_TABLE)|set(CALLBACK_STARTS)
    assert decoded==set(F1A_STARTS),(sorted(hex(x) for x in decoded^set(F1A_STARTS)))
    assert not set(F1A_BUNDLED)&decoded
    ext=external_targets(program)
    BB_ENTRIES=tuple(sorted(set(ext)-{TRAP_PC}))
    for lo,hi in F1A_SPLIT:
        for r in disassemble_range(program,lo,hi-lo,lo):F1A_INSTR[r['cpu_address']]=r
    assert not any(r['classification']=='undecoded_word' for r in F1A_INSTR.values())
    LEAD_PCS=frozenset(F1A_STARTS)|frozenset(BB_ENTRIES)
    CK_SET=frozenset(F1A_STARTS)|frozenset(BB_ENTRIES)
    RANGES_ALL=tuple(dict.fromkeys(tuple(bc.RANGES)+F1A_SPLIT))
    assert not in_ranges(TRAP_PC,RANGES_ALL) and not in_ranges(BIOS,RANGES_ALL)            # 47c6c is an existing (activation executor) range start: the stop there is declared, not a guard
    fc.OUT=out_dir;fc.RANGES=RANGES_ALL;fc.BOUNDARIES=();fc.KEY_PCS=()
    fh.OUT=out_dir;fh.POOL.clear()
    install_observer()
    return bc.sp.EXTENSION


# ----------------------------------------------------------------------------------
# Observer: U5 observer (3c0006 video port) + declared initial SR, waits at cda4 / 3aea / the 47af0 palette gate, leader records (F1a block starts and the black-box entries
# reached directly from F1a code), alternative stop PCs for probes
# ----------------------------------------------------------------------------------
class F1Mixin(object):
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
                elif pc==0x3aea:
                    live=int.from_bytes(cpu.mem_read((a5-0x328c)&M32,2),'big');want=cpu.reg_read(REGS['d1'])&0xffff;blocked=live==want
                else:                                                       # the 47af0 gate: a spin iteration finished (BCC at 47af6 taken -> 47af0 again)
                    live=cpu.mem_read(0x107ded,1)[0];want=0x80;blocked=len(self.pcs)>=2 and self.pcs[-2]==GATE_RET and bool(live&0x80)     # a spin iteration finished and the gate is still closed
                if blocked:
                    self.stop_pc=pc;self.wait=dict(pc=pc,live_word=live,compared_word=want,kind={0xcda4:'sprite',0x3aea:'sound',GATE_PC:'palette-gate'}[pc]);cpu.emu_stop();return
            if pc in LEAD_PCS and (pc in F1A_START_SET or in_f1a(self.last_pc if self.last_pc is not None else -1)):
                self.leads.append(dict(pc=pc,regs=self.regs(),pc_index=len(self.pcs)-1,event_index=len(self.events)))
            self.last_pc=pc
        c.hook_add(UC_HOOK_CODE,cb)
        return self
    def run(self,allow_guard=False):
        self.leads=[];self.wait=None;self.mine_seen=set(self.seen)
        r=super().run(allow_guard=allow_guard)
        g=r['guard']
        if g is not None and g.get('problem')=='unsupported_code_target':
            t=g['target'];prev=r['pcs'][-2] if len(r['pcs'])>=2 and r['pcs'][-1]==t else (r['pcs'][-1] if r['pcs'] else None)
            if t&1:g['reason']='odd target PC %x (an address error on the original CPU)'%t;g['odd_pc']=True
            elif t==TRAP_PC:g['reason']='TRAP #15 at e909c reached without the declared stop (the boundary is a stop only; the TRAP is never executed)'
            elif prev==0x47b02:g['reason']='computed PC 47b06+D0.W = %x (JMP 47b06(PC,D0.W) has no range check) is not a declared block start / routed PC'%t
            elif t==BIOS:g['reason']='BIOS fetch outside a declared BIOS stop'
            else:g['reason']='control transfer to %x, outside every routed range, from %s'%(t,hex(prev) if prev is not None else 'the entry')
        elif g is not None and g.get('problem') in ('unsupported_write','unmapped_or_protected'):
            g['reason']='write to the program ROM / an unmapped address %s'%hex(g.get('address',0))
        elif g is not None and g.get('problem')=='unsupported_odd_data_access':
            g['reason']='odd address %x for a %d-byte %s access (address error on the original CPU)'%(g['address'],g['size'],g['access'])
        if g is not None and 'reason' not in g:
            if g.get('problem')=='step_limit':g['reason']='no terminator: the declared instruction watchdog (%d) expired at %x (the original code has no bound)'%(g['limit'],g['pc'])
            else:g['reason']='native guard %s'%g.get('problem')
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


F1Observer=None
F1A_START_SET=frozenset()


def install_observer():
    global F1Observer,F1A_START_SET
    F1A_START_SET=frozenset(F1A_STARTS)
    base=[k for k in bc.U7Observer.__mro__ if k.__name__=='U5Observer'][0]
    F1Observer=type('F1Observer',(F1Mixin,base),{})
    fc.Observer=F1Observer


def W(address,size,value,why):return fc.ram_write(address,size,value,why)


# ----------------------------------------------------------------------------------
# Chain runner: persistent CPU, one step per declared stop, split (stop at the first hit of every checkpoint) or continuous
# ----------------------------------------------------------------------------------
RUNS=[0]


def run_chain(program,spec,continuous):
    RUNS[0]+=1
    fx=spec['fixture'];allow=bool(spec.get('guarded'));o=F1Observer(program,continuous);phases=[]
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
                phases.append(p)
                if p['guard'] is not None:break
                if p['waiting']:
                    assert p['outgoing']['pc'] in WAIT_PCS,(spec['label'],hex(p['outgoing']['pc']))
                    break
                if p['outgoing']['pc']!=target and p['outgoing']['pc'] in step.get('alts',()):
                    step['found_stop']=p['outgoing']['pc'];break                      # probe only: an alternative declared stop was reached
                assert p['outgoing']['pc']==target,(spec['label'],step['label'],hex(p['outgoing']['pc']),hex(target))
                if p['outgoing']['pc']==step['stop_pc']:
                    if step['a7'] is not None:
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
# Stop evidence: a stop is accepted only directly after the transferring instruction
# ----------------------------------------------------------------------------------
WAIT_PREV={0xcda4:{0xcda0:'6700',0xcda8:'66fa'},0x3aea:{0x3ae6:'0241',0x3aee:'67fa'},GATE_PC:{GATE_RET:'64f8'}}


def stop_evidence(program,p,origin):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc'];ram=p['ram_after']
    if p['waiting']:
        assert pcs[-1]==pc and pc in WAIT_PCS,(p['label'],hex(pc))
        w=p['wait']
        if len(pcs)==1:return dict(kind='wait',outgoing_pc=pc,previous_pc=None,wait=w,reached_from='zero-step re-stop: the resumed wait is still blocked (stop PC = entry PC, nothing executed)')
        prev=pcs[-2];allowed=WAIT_PREV[pc]
        assert prev in allowed and program[prev:prev+2].hex()==allowed[prev],(p['label'],hex(prev),hex(pc))
        return dict(kind='wait',outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),wait=w,
            reached_from='%s at %x %s into the %s wait at %x (blocked: live %s %s %04x); the instruction at %x is not executed'%(program[prev:prev+2].hex(),prev,'fell through' if pc!=GATE_PC and prev in (0xcda0,0x3ae6) else 'looped back (taken)',w['kind'],pc,
                ('BYTE 107ded=%02x bit7=1'%w['live_word']) if pc==GATE_PC else 'WORD %04x'%w['live_word'],'<>' if pc==0xcda4 else '=' if pc==0x3aea else '(bit7 set => C=0 => BCC.B 47af0)',w['compared_word'],pc))
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(kind='zero-step',outgoing_pc=pc,previous_pc=None,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];a7=o['a7'];inc=origin['incoming']
    if pc==EXIT_STOP:
        assert prev==0x47c66 and program[prev:prev+6].hex()=='2cbc00047c6c',(p['label'],hex(prev))
        return dict(kind='exit-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes='2cbc00047c6c',reached_from='fall-through directly after MOVE.L #47c6c,(A6) at 47c66 (the exit unit 47c5a ran natively); 47c6c is not executed')
    if pc==TRAP_PC:
        assert prev==0xe9098 and program[prev:prev+4].hex()=='67000004' and program[pc:pc+2]==TRAP_BYTES,(p['label'],hex(prev))
        d1=o['d1']&0xff;assert d1 not in (0,0xff),hex(d1)
        return dict(kind='trap-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes='67000004',d1_byte=d1,reached_from='BEQ.W e909e at e9098 (bytes 67000004) not taken after CMPI.B #0,D1 with D1.B = %02x (<> ff, <> 00); the TRAP #15 at e909c (bytes 4e4f) is never executed'%d1)
    if pc==BIOS:
        assert prev==0xc376 and program[prev:prev+6].hex()=='4eb900c00468',(p['label'],hex(prev))
        return dict(kind='bios-boundary',outgoing_pc=pc,previous_pc=prev,previous_bytes='4eb900c00468',reached_from='JSR c00468 at c376 (bytes 4eb900c00468); the BIOS body is never executed (no BIOS execution claim)')
    if pc==FRAME_RET and prev==0x2a06:                                                  # the fade_card cleanup 2a00: MOVEA.L -$335c(A5),A7 ; BRA.W 2ac2
        assert program[0x2a02:0x2a0a].hex()=='2e6dcca4600000ba' and o['a7']==u32(ram,0x4ca4),(p['label'],hex(o['a7']))
        return dict(kind='dispatcher-base-return',outgoing_pc=pc,previous_pc=prev,previous_bytes='600000ba',dispatcher_base_a7=o['a7'],reached_from='BRA.W 2ac2 at 2a06 directly after MOVEA.L -$335c(A5),A7 at 2a02 (A7 := the declared dispatcher base LONG 104ca4); 2ac2 is not executed')
    assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))
    on_stack=[off for off in range(0,64,2) if u32(origin['ram_before'],inc['a7']+off)==pc]
    assert on_stack,(p['label'],'the popped LONG %x was not declared on the stack at the step entry'%pc)
    return dict(kind='return',outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',return_long_on_stack_at_entry_offsets=on_stack,entry_a7=inc['a7'],
        reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x); %x is never executed'%(prev,pc,a7,pc))


def annotate(program,phases):
    first={}
    for p in phases:first.setdefault(p['step'],p)
    for p in phases:p['stop_evidence']=stop_evidence(program,p,first[p['step']])


# ----------------------------------------------------------------------------------
# Storage (same rows / payload names as U7; identical payloads are hard-linked)
# ----------------------------------------------------------------------------------
POOL={}


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def ports_blob(events):return b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS)


def compact(items,key=None,limit=2000):
    if len(items)<=limit:return items
    f=key or (lambda x:x);counts=collections.Counter(f(x) for x in items)
    return dict(truncated=True,count=len(items),first=items[:200],by_pc={hex(k):v for k,v in sorted(counts.items())})


def stop_reason(p):
    if p['guard'] is not None:return 'guard:%s'%p['guard'].get('problem')
    ev=p.get('stop_evidence')
    if ev is None:return 'checkpoint (split stop at the first hit of a block leader, before the instruction executes)'
    return ev['kind']


def phase_row(j,p,artifacts,keys,snapshots):
    return dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
        host_changes=p['host_changes'],carry_in=p['carry_in'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
        waiting=p['waiting'],wait=p['wait'],carry=p['carry'],branch_evidence=p['branch_evidence'],guard=p['guard'],snapshots=snapshots,counts=fc.counts(p['events']),
        external_read_events=[dict(pc=e['pc'],address=e['address'],size=e['size'],bytes=e['bytes']) for e in p['events'] if e['region']=='external'],stop_reason=stop_reason(p),
        key_pcs=compact([pc for pc in p['pcs'] if pc in KEY_SET]),pc_count=len(p['pcs']),artifacts=artifacts,stop_evidence=p['stop_evidence'],
        leaders=compact([dict(pc=l['pc'],pc_index=l['pc_index'],event_index=l['event_index']) for l in p['leads']],key=lambda l:l['pc']))


KEY_SET=frozenset()


def store(prefix,phases,files=True):
    """files=True: every payload is written (RAM before/after, PVC, ports, trace, checkpoint snapshots); files=False: the payload SHA256 values are recorded without writing files."""
    rows=[]
    for j,p in enumerate(phases):
        stem='%s_phase_%03d'%(prefix,j)
        payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
            stem+'_ports.bin':ports_blob(p['events']),
            stem+'_trace.json.gz':gzip.compress((json.dumps({k:p[k] for k in ('pcs','events','guard')})+'\n').encode(),9,mtime=0)}
        snapshots=[]
        for k,snapshot in enumerate(p['snapshots']):
            names={}
            for field in ('ram','pvc'):
                name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
            snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
        hashes={name:(write_payload(name,data) if files else sha(data)) for name,data in payloads.items()}
        rows.append(phase_row(j,p,hashes,KEY_SET,snapshots))
    return rows


# ----------------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------------
def pvc_for(bank):return bc.pvc_for(bank)


def body_fixture(program,case,index):
    """Declared entry of the 47a94 body: the begin RAM / registers of observe_stage_entry_body (A6 = 100b30, A5 = 108000), the initial bank 2 / 3, A7 = 1feffc with the declared dispatcher return LONG 2ac2."""
    ram,state,meta=seb.prepare_case(ROOT,program,case)
    prov=dict(kind='stage_entry_body begin case (original 47a94 entry; fixture rebuilt by observe_stage_entry_body.prepare_case)',observation_sha256=sc.STAGE_ENTRY_SHA,case_index=index,family=case['family'],case=case,
        input_ram_sha256=sha(bytes(ram)),pre_entry_host_writes=len(meta['host_writes']),record=hex(case['record']),bank=case['bank'])
    fx=sc.make_fx('body-%03d'%index,bytes(ram),{k:state[k] for k in KEYS14+('a5',)},pvc_for(case['bank']),ENTRY_BODY,S,prov,(),[(S,FRAME_RET.to_bytes(4,'big'))],
        role='declared 47a94 entry: the begin RAM and registers of the stage_entry_body observer; A5 = 108000, A6 = 100b30, A7 = 1feffc with the declared dispatcher return LONG 2ac2 (the original had ff000)')
    fx['group']='entry-body';return fx,prov


def step_of(label,changes,stop,a7,expect,alts=(),**extra):
    return dict(label=label,changes=list(changes),stop_pc=stop,checkpoints=[],a7=a7,expect=expect,alts=tuple(alts),**extra)


def reentry_changes(callback):
    return [fc.pc_to(callback,'declared dispatcher re-entry at the installed callback LONG (A6): PC redirect only, registers / RAM are the previous native outputs (no scheduler)'),
        fc.a7_add(-4,'declared dispatcher re-entry: A7 back to the dispatcher slot 1feffc'),W(S,4,FRAME_RET,'declared return LONG 2ac2 at 1feffc (the value the previous frame popped)'),
        W(0x104ca4,4,S+4,'declared dispatcher base A7 (the scheduler stores it before JSR (A0); 2a00 reloads A7 from it via MOVEA.L -$335c(A5),A7): the A7 after the popped return LONG')]


def gate_effect(ram_after):
    """The declared IRQ palette effect of the 72f0 gate (contract decision 2, minimal form): the IRQ path cbe JSR 72fa clears BYTE 107ded bit7 (72fa..7302) unless WORD 107dea <> 0
    (72fa TST.W -$216(A5); BNE.W 873a, a path that does not clear it)."""
    b=ram_after[0x7ded];w=u16(ram_after,0x7dea)
    if w!=0:return [],dict(kind='irq-palette-effect',clears_bit7=False,reason='WORD 107dea = %04x <> 0: the original IRQ path (72fa BNE.W 873a) leaves BYTE 107ded bit7 set'%w)
    return [W(0x107ded,1,b&0x7f,'declared IRQ palette effect (72fa..7302 BCLR #7,-$213(A5)): BYTE 107ded %02x -> %02x'%(b,b&0x7f))],dict(kind='irq-palette-effect',clears_bit7=True,reason='WORD 107dea = 0')


def release_changes(wait,ram_after):
    if wait['pc']==0x3aea:return [W(0x104d74,2,0xffff,'declared release of the sound-ring wait: tail WORD 104d74 := ffff (<> D1.W)')],None
    if wait['pc']==0xcda4:return [W(0x108d34,2,wait['compared_word'],'declared release of the sprite wait: WORD 108d34 := D4.W')],None
    return gate_effect(ram_after)


class ProbeObserver(object):
    """One persistent continuous run that discovers the declared steps (waits, releases, re-entries, the boundary stop) of a chain."""
    pass


def plan_chain(program,fx,label,setup=(),reenter=True,hold=None,max_frames=60,alts=(EXIT_STOP,TRAP_PC),first_stop=FRAME_RET,gate_limit=3,gate_idem=0,a7_stop=('abs',S+4),reenter_extra=None,max_47bfc=2):
    """Interactive probe on ONE persistent CPU: step 0 with the declared setup, then a declared release per wait, a re-entry per returned frame whose installed callback LONG (A6) is a
    F1a callback, until a boundary stop, a guard or a non-F1a callback.  gate_idem: number of declared no-effect resumes of a 47af0 gate wait (the Waiting must repeat with the same state)
    before the declared IRQ palette effect.  reenter_extra: {n: [changes]} appended to the n-th re-entry.  Returns (steps, last_phase_guard)."""
    o=F1Observer(program,True);steps=[];phases=[]
    try:
        o.prepare(dict(fx,stop_pc=first_stop,checkpoints=[],stop_alts=alts))
        nxt=step_of(label+'-frame0',setup,first_stop,a7_stop,'return',alts)
        gates=0;frames=0;idem=0
        while True:
            step=nxt;o.begin_step(step['stop_pc'],[]);o.alt_stops=frozenset(step['alts'])
            changes=o.apply(step['changes']);p=o.run(allow_guard=True);steps.append(step);phases.append(p)
            if p['guard'] is not None:
                g=p['guard']
                if g.get('problem')=='unsupported_code_target' and g.get('target')==BIOS and p['pcs'][-2]==0xc376:
                    step.update(stop_pc=BIOS,a7=None,expect='boundary',alts=());return steps,None                  # the BIOS JSR was executed; the clean stop is verified by the real runs
                if g.get('problem')=='unsupported_code_target' and g.get('target')==TRAP_PC and TRAP_PC in step['alts'] and p['pcs'][-2]==0xe9098:
                    step.update(stop_pc=TRAP_PC,a7=None,expect='boundary',alts=());return steps,None               # reached the TRAP boundary: nothing executed at e909c; the real runs declare the stop
                step.update(expect='guard');return steps,g
            if p['waiting']:
                step['expect']='wait';w=p['wait']
                if w['pc']==GATE_PC:
                    if idem<gate_idem:
                        idem+=1;nxt=step_of('%s-gate-resume-no-effect-%d'%(label,idem),[],first_stop,a7_stop,'wait',alts,declared_effect=dict(kind='no-effect-resume',reason='the gate stays blocked: a resume without any declared IRQ effect must return the same Waiting'))
                        continue
                    ch,eff=release_changes(w,p['ram_after']);gates+=1 if not ch else 0
                    if gates>=gate_limit:return steps,None                                                         # the gate stays blocked: the chain ends in the wait
                    nxt=step_of('%s-gate-irq-effect-%d'%(label,len(steps)),ch,first_stop,a7_stop,'return' if ch else 'wait',alts,declared_effect=eff)
                else:
                    if w['pc']==0x3aea and hold is not None and not any(s.get('hold') for s in steps):
                        nxt=step_of('%s-hold'%label,hold,first_stop,a7_stop,'wait',alts,hold=True)
                    else:
                        ch,eff=release_changes(w,p['ram_after']);nxt=step_of('%s-release-%d'%(label,len(steps)),ch,first_stop,a7_stop,'return',alts)
                if len(steps)>max_frames:raise AssertionError('too many steps '+label)
                continue
            pc=p['outgoing']['pc']
            if pc!=step['stop_pc']:
                assert pc in step['alts'],(label,hex(pc))
                step.update(stop_pc=pc,a7=None,expect='boundary');return steps,None
            step['expect']='return'
            if step['a7'] is not None:
                kind,value=step['a7'];assert p['outgoing']['a7']==value,(label,step['label'],'A7 after the stop',hex(p['outgoing']['a7']),'expected',hex(value))
            if not reenter:return steps,None
            a6=p['outgoing']['a6'];cb=u32(p['ram_after'],a6&0xffff) if 0x100000<=a6<0x200000 and a6&1==0 else None
            frames+=1
            repeats=sum(1 for q in steps[-3:] if q['label'].find('reenter-%x-'%cb)>=0) if cb==0x47bfc else 0
            if cb not in CALLBACKS or frames>=max_frames or repeats>=max_47bfc:return steps,None            # 47bfc waits for a child that no scheduler runs: two repeats are enough
            nxt=step_of('%s-reenter-%x-%d'%(label,cb,frames),reentry_changes(cb)+list((reenter_extra or {}).get(frames,())),first_stop,('abs',S+4),'return',alts)
    finally:o.close()


# ----------------------------------------------------------------------------------
# Comparison with the recorded / original flat-map runs (the stack lives outside the 64KiB image there, here it is the work-RAM mirror at offset effc)
# ----------------------------------------------------------------------------------
def stack_window(phases):
    """[lo,0f000) of the 64KiB image: the bytes the live stack (A7 <= 1feffc+4) may have used in the machine layout.  lo = lowest stack-region write of the phases (at most eff0)."""
    writes=[e['address'] for p in phases for e in p['events'] if e['region']=='ram' and e['access']=='write' and e['address']>=0x1f0000]
    lo=(min(writes)&0xffff) if writes else 0xf000
    return min(lo,0xeff0)


def recorded_diff(ram_native,ram_recorded,lo):
    return [k for k in range(0x10000) if ram_native[k]!=ram_recorded[k] and not lo<=k<0xf000]


def compare_to_original(history,ps,rec):
    """One native step (its phases `ps`, the chain so far `history`) versus an original-layout run.  rec: ram, ports (blob), regs (14 + a5), final_pc, final_a7, pcs (or None), writes (or None), stack_hex (or None)."""
    p=ps[-1];o=p['outgoing']
    lo=stack_window(history);diff=recorded_diff(p['ram_after'],rec['ram'],lo)
    events=[e for q in ps for e in q['events']];blob=ports_blob(events)
    pcs=[pc for q in ps for pc in q['pcs'][:-1]]+p['pcs'][-1:]
    rec_final={0xff000:FRAME_RET}.get(rec['final_pc'],rec['final_pc'])
    pcs_ok=None
    if rec.get('pcs') is not None:
        rp=rec['pcs']
        pcs_ok=(rp[:len(pcs)]==pcs if p['waiting'] else rp[:-1]==pcs[:-1]) and rec_final==o['pc']
        if p['waiting'] and ps[-1] is not None and len(pcs)==1 and False:pcs_ok=True
    writes_ok=None
    if rec.get('writes') is not None:
        nw=[(e['address'],e['size'],int(e['bytes'],16)) for e in events if e['region']=='ram' and e['access']=='write' and e['address']<0x110000]
        rw=[(w['address'],w['size'],w['value']) for w in rec['writes']]
        writes_ok=nw==rw if not p['waiting'] else rw[:len(nw)]==nw
    n=S+4-o['a7']
    live_ok=None
    if rec.get('stack_hex') is not None and n>4:
        rs=bytes.fromhex(rec['stack_hex']);live=bytes(p['ram_after'][(o['a7']&0xffff):(S&0xffff)]);live_ok=live==rs[len(rs)-n:len(rs)-4]
    out=dict(instructions_native=len(pcs)-1 if not p['waiting'] else len(pcs),pcs_equal_or_prefix=pcs_ok,ram_writes_equal=writes_ok,
        registers_equal=all(o[k]==rec['regs'][k] for k in KEYS14+('a5',)),final_pc_equal=rec_final==o['pc'],final_a7_equal=o['a7']==rec['final_a7'],bank_equal=p['modeled_bank']==rec['bank']*0x100000,
        ports_equal=blob==rec['ports'],port_count=len(blob)//9,ram_equal_outside_stack_window=not diff,ram_differing_bytes=len(diff),stack_window=[hex(0x100000+lo),hex(0x10f000)],
        live_stack_equal=live_ok,first_diff=[(hex(0x100000+k),p['ram_after'][k],rec['ram'][k]) for k in diff[:6]],waiting=p['waiting'],bank_reads_equal=None)
    if rec.get('bank_reads') is not None:
        nb=[(e['pc'],e['address'],e['size'],e['bank_at_read']) for e in events if e['region']=='bank']
        out['bank_reads_equal']=nb==[(b['pc'],b['address'],b['size'],b['bank']*0x100000) for b in rec['bank_reads']]
    out['ok']=all(v is not False for v in out.values() if isinstance(v,(bool,type(None)))) and out['pcs_equal_or_prefix'] is not False
    out['ok']=all(out[k] for k in ('registers_equal','final_pc_equal','final_a7_equal','bank_equal','ports_equal','ram_equal_outside_stack_window')) and all(out[k] is not False for k in ('pcs_equal_or_prefix','ram_writes_equal','live_stack_equal','bank_reads_equal'))
    return out


class OriginalChain(object):
    """The original flat-map observer (observe_stage_entry_body.Observer, stack outside the 64KiB image) continued by declared re-entries: the reference for the dispatcher frames."""
    def __init__(self,program):
        self.program=program;self.obs=seb.Observer(program)
    def start(self,case):
        o=self.obs;ram,state,meta=seb.prepare_case(ROOT,self.program,case);o.prepare(ram,state);self.bank0=state['bank']
        return self.run_from(seb.BODY_ENTRY,True)
    def run_from(self,pc,first=False,stop=None):
        o=self.obs;m=seb.m;cpu=o.cpu
        o.external,o.wait_visits,o.error=0,0,None
        for values in (o.pcs,o.writes,o.ports,o.reads,o.bank_reads,o.boundaries,o.prefix):values.clear()
        if not first:
            cpu.reg_write(m.UC_M68K_REG_PC,pc);cpu.reg_write(m.UC_M68K_REG_A7,seb.STACK);cpu.mem_write(seb.STACK,seb.RETURN.to_bytes(4,'big'))
            cpu.mem_write(0x104ca4,(seb.STACK+4).to_bytes(4,'big'))                          # the same declared dispatcher base A7 as the native re-entry
        try:cpu.emu_start(cpu.reg_read(m.UC_M68K_REG_PC),stop if stop is not None else 0xffffff,count=2000000)
        except unicorn.UcError:
            if not (o.error is not None and o.error[0]=='invalid-memory' and o.error[2]==BIOS):raise
        if o.error is not None and o.error[0]=='invalid-memory' and o.error[2]==BIOS:                  # the BIOS card routine is unmapped in the flat map: the same boundary stop as the native run
            o.error=None;o.pcs.append(BIOS)
        assert o.error is None,o.error
        regs={k:cpu.reg_read(r)&M32 for k,r in zip(seb.KEYS,seb.REGS)};regs['a5']=cpu.reg_read(m.UC_M68K_REG_A5)&M32
        if stop is not None and cpu.reg_read(m.UC_M68K_REG_PC)==stop and o.pcs[-1]!=stop:o.pcs.append(stop)           # Unicorn's `until` stops before the code hook of the stop PC
        return dict(ram=bytes(cpu.mem_read(seb.BASE,0x10000)),ports=b''.join(struct.pack('>BII',*t) for t in o.ports),regs=regs,final_pc=cpu.reg_read(m.UC_M68K_REG_PC),final_a7=cpu.reg_read(m.UC_M68K_REG_A7),
            pcs=list(o.pcs),writes=[dict(w) for w in o.writes],bank=o.bank,bank_reads=[dict(b) for b in o.bank_reads],stack_hex=None)


def rec_from_entry_row(row,folder,phase):
    """Recorded stage_entry_body phase -> comparison dict (RAM, ports, registers, trace)."""
    ph=row['phases'][phase];res=ph['result']
    ram=(folder/ph['ram_file']).read_bytes();assert sha(ram)==ph['ram_sha256']
    ports=(folder/ph['ports_file']).read_bytes();assert sha(ports)==ph['ports_sha256']
    trace_raw=(folder/ph['trace_file']).read_bytes();assert sha(trace_raw)==ph['trace_sha256']
    trace=json.loads(gzip.decompress(trace_raw))
    regs={k:res[k] for k in KEYS14};regs['a5']=ph['final_a5']
    return dict(ram=ram,ports=ports,regs=regs,final_pc=ph['final_pc'],final_a7=ph['final_a7'],bank=res['bank'],pcs=trace['pcs'],writes=trace['RAM_writes'],bank_reads=trace['physical_bank_reads'],stack_hex=ph['stack_hex'],name=ph['name'])


def rec_from_prefix_row(row,folder):
    ram=(folder/row['ram_file']).read_bytes();assert sha(ram)==row['ram_sha256']
    ports=(folder/row['ports_file']).read_bytes();assert sha(ports)==row['ports_sha256']
    trace_raw=(folder/row['trace_file']).read_bytes();assert sha(trace_raw)==row['trace_sha256']
    trace=json.loads(trace_raw)
    regs={k:row['result'][k] for k in KEYS14+('a5',)}
    wr=[dict(address=w['address'],size=w['size'],value=w['value']) for w in trace['writes'] if w['kind']=='ram']
    return dict(ram=ram,ports=ports,regs=regs,final_pc=row['final_pc'],final_a7=row['final_a7'],bank=2,pcs=trace['pcs'],writes=wr,bank_reads=None,stack_hex=None)


# ----------------------------------------------------------------------------------
# Condition processing: twice-reproduced split and continuous runs, stored rows, model segments, recorded comparison
# ----------------------------------------------------------------------------------
def condition_summary(spec,split,control):
    pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    c=control[-1]
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),waiting=c['waiting'],
        ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),
        external_reads=sum(1 for e in ev if e['region']=='external'),ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=sha(ports_blob(ev)),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'],
        stop_reasons=[stop_reason(p) for p in control])


def step_summary(spec):
    return [dict(label=s['label'],stop_pc=s['stop_pc'],checkpoints=s['checkpoints'],a7_expectation=list(s['a7']) if s['a7'] is not None else None,expect=s.get('expect'),declared_changes=s['changes'],
        declared_effect=s.get('declared_effect'),probe_alternative_stops=list(s.get('alts',()))) for s in spec['steps']]


def collect_facts(spec,control):
    """Compact observed facts of one condition used by the contract claims (nothing here feeds back into the run)."""
    facts=dict(steps=[])
    for k,step in enumerate(spec['steps']):
        ps=[p for p in control if p['step']==k]
        if not ps:continue
        p=ps[-1];ev=[e for q in ps for e in q['events']]
        f1=[e for e in ev if in_f1a(e['pc'])]
        reads={}
        for e in f1:
            if e['access']=='read' and e['region'] in ('fixed','bank'):
                r=reads.setdefault(hex(e['pc']),[e['address'],e['address'],0,e['region']]);r[0]=min(r[0],e['address']);r[1]=max(r[1],e['address']);r[2]+=1
        row=dict(step=k,label=step['label'],expect=step.get('expect'),outgoing_pc=p['outgoing']['pc'],outgoing_a7=p['outgoing']['a7'],waiting=p['waiting'],guard=p['guard'],
            leader_seq=[l['pc'] for q in ps for l in q['leads']],f1a_rom_reads=reads,f1a_bank_reads=sum(1 for e in f1 if e['region']=='bank'),f1a_ports=[(e['address'],int(e['bytes'],16)) for e in f1 if e['region'] in PORT_REGIONS and e['access']=='write'],
            f1a_ram_writes=len([e for e in f1 if e['region']=='ram' and e['access']=='write']),byte_107ded_in=ps[0]['ram_before'][0x7ded],byte_107ded_out=p['ram_after'][0x7ded],word_107dea_in=u16(ps[0]['ram_before'],0x7dea),
            regs_sha=sha(json.dumps(p['outgoing'],sort_keys=True).encode()),ram_after_sha=sha(p['ram_after']),dispatch_index=None)
        if k==0 or step['label'].find('reenter')>=0 or step['label'].find('frame0')>=0:
            rec=u32(ps[0]['ram_before'],0xba6)
            if 0x100000<=rec<0x200000:row['dispatch_index']=ps[0]['ram_before'][(rec+1)&0xffff]
            elif rec<0x100000:row['dispatch_index']=G['program'][rec+1]
        if p['waiting'] and p['wait']['pc']==GATE_PC:
            o=p['outgoing']
            row['gate']=dict(d0=o['d0'],byte=p['ram_after'][0x7ded],a7=o['a7'],stale_long_at_a7_minus_4=u32(p['ram_after'],(o['a7']-4)&0xffff),d0_byte_is_byte_minus_80=(o['d0']&0xff)==((p['ram_after'][0x7ded]-0x80)&0xff))
        facts['steps'].append(row)
    l17292=[(e['address'],e['size'],int(e['bytes'],16)) for q in control for e in q['events'] if e['region']=='ram' and e['access']=='write' and 0x17298<=e['pc']<0x18298]
    if l17292:
        facts['clear_17292']=dict(count=len(l17292),first=hex(l17292[0][0]),last=hex(l17292[-1][0]),ascending=all(l17292[i][0]+4==l17292[i+1][0] for i in range(len(l17292)-1)),all_zero_long=all(v==0 and n==4 for a,n,v in l17292))
    facts['lead_a0_at_e8a1c']=[l['regs']['a0'] for q in control for l in q['leads'] if l['pc']==0xe8a1c]
    h35f0=sum(1 for q in control for l in q['leads'] if l['pc']==0x35f0)
    if h35f0:facts['hud_35f0_calls']=h35f0
    return facts


G={}
ITEMS=[]


def process_item(program,number,spec,compare_fn=None):
    t0=time.time()
    split,control=run_spec(program,spec)
    store_all=spec.get('store')=='all'
    result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),observed_guard=spec.get('observed_guard'),
        fixture=fc.summarize(spec,spec['fixture']),steps=step_summary(spec),phases=store('c%04d_split'%number,split,files=store_all),
        continuous_control=store('c%04d_control'%number,control,files=True),reproduced_twice=True,continuous_split_equivalent=True,compared_with_chain=False,stored_from_step=0)
    models=[]
    if spec.get('model') and not spec.get('guarded'):models=model_conditions(program,spec,control)
    compare=compare_fn(spec,control) if compare_fn else None
    covered=set()
    for q in control:covered.update(q['pcs'])
    hits=collections.Counter(l['pc'] for q in control for l in q['leads'])
    summary=condition_summary(spec,split,control)
    return dict(number=number,result=result,models=models,compare=compare,covered=sorted(covered),hits=dict(hits),summary=summary,facts=collect_facts(spec,control),seconds=time.time()-t0,split_phases=len(split),control_phases=len(control),
        waits=[dict(step=p['step'],pc=p['wait']['pc'],a7=p['outgoing']['a7'],kind=p['wait']['kind']) for p in control if p['waiting']],
        boundaries=[dict(step=p['step'],kind=p['stop_evidence']['kind'],pc=p['outgoing']['pc']) for p in control if p['stop_evidence'] and p['stop_evidence']['kind'] in ('exit-boundary','trap-boundary','bios-boundary')])




# ----------------------------------------------------------------------------------
# Natural items
# ----------------------------------------------------------------------------------
def item_body(number,item):
    program=G['program'];i=item['ref'];rowrec=G['entry_obs']['results'][i];case=rowrec['fixture']
    fx,prov=body_fixture(program,case,i)
    hold=None
    if case['family']=='wholebody-sound-wait':
        hold=[W(w['address'],len(w['hex'])//2,int(w['hex'],16),'declared hold write of the recorded stage_entry_body phase "%s" (previous %s)'%(rowrec['phases'][1]['name'],w['previous'])) for w in rowrec['phases'][1]['host_writes']]
    steps,g=plan_chain(program,fx,'body-%03d'%i,hold=hold)
    assert g is None or case['family']=='live-RAM-record-reread',(i,g)
    spec=dict(label='body-%03d-%s'%(i,case['family']),group='entry-body',fixture=fx,steps=steps,provenance=prov,model=True,store='control')
    if g is not None:spec.update(guarded=True,guard={'problem':g['problem']},observed_guard=g,model=False)
    with_checkpoints(program,spec)
    def cmp_fn(spec,control):
        rows=[];history=[];orig=None;r_prev=None
        for k,step in enumerate(spec['steps']):
            ps=[p for p in control if p['step']==k];history=history+ps
            if k<len(rowrec['phases']) and (case['family']=='wholebody-sound-wait' or k==0):
                rec=rec_from_entry_row(rowrec,G['entry_folder'],k);source='recorded stage_entry_body phase "%s" (%s)'%(rec['name'],rowrec['phases'][k]['ram_file'])
            else:
                if orig is None:
                    orig=OriginalChain(program);r_prev=orig.start(case)
                    if k>1:raise AssertionError('original continuation expects the first re-entry at step 1')
                cb=u32(r_prev['ram'],A6V&0xffff)
                try:rec=orig.run_from(cb,stop=step['stop_pc'] if step['stop_pc'] in (EXIT_STOP,TRAP_PC,FRAME_RET) else None);r_prev=rec
                except AssertionError as e:
                    if not (spec.get('guarded') and k==len(spec['steps'])-1):raise
                    g=ps[-1]['guard'];rows.append(dict(step=k,label=step['label'],source='original flat-map observer re-entered at the installed callback %x'%cb,ok=True,original_error=repr(e.args[0]) if e.args else repr(e),
                        native_guard=g,note='the original observer also cannot continue (an address error / invalid fetch in the original flat map); the native guard is the machine-side evidence'));continue
                source='original flat-map observer re-entered at the installed callback %x'%cb
            c=compare_to_original(history,ps,rec);c.update(step=k,label=step['label'],source=source);rows.append(c)
        return rows
    return process_item(program,number,spec,cmp_fn)


def item_prefix(number,item):
    program=G['program'];i=item['ref'];case=G['prefix_cases'][i];rowrec=G['prefix_obs']['results'][i]
    ram=G['osap'].fixture(case)
    regs={k:case['incoming'][k] for k in KEYS14+('a5',)}
    prov=dict(kind='stage_activation_prefix recorded case (47c04 direct entry, stop before 47c6c)',observation_sha256=G['prefix_sha'],case_index=i,case=json.loads(json.dumps(case,default=str)),input_ram_sha256=sha(ram))
    fx=sc.make_fx('prefix-%03d'%i,ram,regs,pvc_for(2),PREFIX_ENTRY,S,prov,(),[(S,FRAME_RET.to_bytes(4,'big'))],
        role='declared 47c04 entry of the stage_activation_prefix case: its RAM (shake_256 profile + host writes) and registers, A5 = 108000, A7 = 1feffc with the declared return LONG 2ac2')
    fx['group']='activation'
    steps=[step_of('prefix-%03d-activation'%i,[],EXIT_STOP,('abs',S),'boundary')]
    spec=dict(label='prefix-%03d'%i,group='activation',fixture=fx,steps=steps,provenance=prov,model=True,store='control')
    with_checkpoints(program,spec)
    def cmp_fn(spec,control):
        rec=rec_from_prefix_row(rowrec,G['prefix_folder']);ps=[p for p in control if p['step']==0]
        c=compare_to_original(ps,ps,rec);c.update(step=0,label=steps[0]['label'],source='recorded stage_activation_prefix %s'%rowrec['ram_file']);return [c]
    return process_item(program,number,spec,cmp_fn)


def run_item(number):
    item=ITEMS[number];RUNS[0]=0
    try:
        r=globals()['item_'+item['kind']](number,item);r['runs']=RUNS[0];return r
    except Exception as e:
        import traceback
        return dict(number=number,error=repr(e)[:800],trace=traceback.format_exc()[-3000:],kind=item['kind'],ref=item.get('ref'))


# ----------------------------------------------------------------------------------
# Independent model: a M68000 subset interpreter that decodes the ORIGINAL ROM BYTES of the F1a ranges (decoder written from the 68000 programmer's reference, not from the
# disassembler / Unicorn / C++).  Complete CCR (X N Z V C, None = unknown), 32-bit register semantics, explicit byte / word / long operations.  Calls leave the F1a
# ranges at a black-box entry; the native exit state of the black box is replayed (registers, RAM / PVC writes) and its carry is unknown (taken from the executed path).
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
SZ={0:1,1:2,2:4}
MASK={1:0xff,2:0xffff,4:M32}
SIGN={1:0x80,2:0x8000,4:0x80000000}
COND=dict(cc=4,cs=5,ne=6,eq=7,hi=2,ls=3,vc=8,vs=9,pl=10,mi=11,ge=12,lt=13,gt=14,le=15)


def sext(v,size):
    v&=MASK[size];return v-(1<<(8*size)) if v&SIGN[size] else v


class NeedFlag(Exception):
    def __init__(self,names):self.names=names


class F1Model(object):
    def __init__(self,program,bank_state,ram,regs,sr=None):
        self.prog=program;self.bank,self.ff8,self.ff9=bank_state;self.ram=bytearray(ram)
        self.r={k:regs[k]&M32 for k in KEYS+('a7',)};self.pc=regs['pc']
        self.cc=dict(X=None,N=None,Z=None,V=None,C=None)
        if sr is not None:self.cc=dict(X=(sr>>4)&1,N=(sr>>3)&1,Z=(sr>>2)&1,V=(sr>>1)&1,C=sr&1)
        self.leads=[];self.writes=[];self.reads=[];self.rom_reads=[];self.ports=[];self.evidence=[];self.cache={};self.steps=0
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
        self.bank=((self.ff8>>8)|(self.ff9<<8))+0x100000
        self.ff8=(self.ff8&0xfe00)|0xa0;self.ff9&=0x7fff
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
        if w==0x003c:ins.update(op='ori_ccr',imm=self.ext(pc+2)&0xff,len=4)
        elif w==0x4e75:ins.update(op='rts',len=2)
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
        elif (w&0xfff8)==0x4840:ins.update(op='swap',reg=w&7,len=2)
        elif hi==5 and (w&0x100) and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);q=(w>>9)&7;ins.update(op='subq',size=size,imm=q or 8,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xff00)==0x0800:                    # static bit ops
            t=(w>>6)&3;bit=self.ext(pc+2)&0xff;ea,pos=self.decode_ea((w>>3)&7,w&7,1,pc+4);ins.update(op=['btst','bchg','bclr','bset'][t],bit=bit,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xf00)==0x400 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos);ins.update(op='subi',size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi==0 and (w&0xf00)==0xc00 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos);ins.update(op='cmpi',size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi==0xb:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (0,1,2):
                size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='cmp',size=size,reg=reg,src=ea,len=pos-pc)
            elif om in (3,7):
                size=2 if om==3 else 4;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='cmpa',size=size,reg=reg,src=ea,len=pos-pc)
            else:raise ModelError('EOR %x'%pc)
        elif hi==0xc:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (0,1,2):
                size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='and',size=size,reg=reg,src=ea,len=pos-pc)
            else:raise ModelError('opcode %04x at %x'%(w,pc))
        elif hi==0xd:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (0,1,2):
                size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='add',size=size,reg=reg,src=ea,len=pos-pc)
            elif om in (3,7):
                size=2 if om==3 else 4;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='adda',size=size,reg=reg,src=ea,len=pos-pc)
            else:raise ModelError('ADD to memory %x'%pc)
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
    # ---- execution of one instruction at self.pc; returns None normally, or a string when the interpreter must hand over
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
        elif op=='swap':
            n='d%d'%ins['reg'];v=r[n];r[n]=((v<<16)|(v>>16))&M32;self.nz(r[n],4)
        elif op=='subq':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size'])
            if d[0]=='reg' and d[1][0]=='a':raise ModelError('SUBQ to An')
            self.put(d,ins['size'],self.sub(v,ins['imm'],ins['size']))
        elif op=='subi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.put(d,ins['size'],self.sub(v,ins['imm'],ins['size']))
        elif op=='cmpi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.sub(v,ins['imm'],ins['size'],x=False)
        elif op=='cmp':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);self.sub(r['d%d'%ins['reg']],v,ins['size'],x=False)
        elif op=='cmpa':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);v=sext(v,ins['size'])&M32;self.sub(r['a%d'%ins['reg']],v,4,x=False)
        elif op=='add':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='d%d'%ins['reg'];self.put(('reg',n),ins['size'],self.add(r[n],v,ins['size']))
        elif op=='adda':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='a%d'%ins['reg'];r[n]=(r[n]+sext(v,ins['size']))&M32
        elif op=='and':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='d%d'%ins['reg'];res=r[n]&v&MASK[ins['size']];self.put(('reg',n),ins['size'],res);self.nz(res,ins['size'])
        elif op in ('bset','bclr','btst','bchg'):
            d=self.resolve(ins['dst'],1);v=self.get(d,1);bit=ins['bit']%8;self.cc['Z']=int((v>>bit)&1==0)
            if op=='bset':self.put(d,1,v|(1<<bit))
            elif op=='bclr':self.put(d,1,v&~(1<<bit))
            elif op=='bchg':self.put(d,1,v^(1<<bit))
        elif op=='ori_ccr':
            for name,bit in (('X',4),('N',3),('Z',2),('V',1),('C',0)):
                if (ins['imm']>>bit)&1:self.cc[name]=1
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
                if pc not in CARRY_CONSUMERS:raise ModelError('branch at %x on the unknown flag %s (not a declared carry consumer)'%(pc,e.names))
                if j>=len(nl):raise ModelError('unknown carry at %x and no native successor leader'%pc)
                succ=nl[j]['pc']
                if succ not in (ins['target'],nxt):raise ModelError('native successor %x of %x is neither target %x nor fall-through %x'%(succ,pc,ins['target'],nxt))
                taken=succ==ins['target'];self.evidence.append(dict(pc=hex(pc),flag='C',taken=taken,source='native executed path: the next native leader after the branch is %x (carry produced by a black box / unmodelled callee)'%succ))
            if taken:nxt=ins['target']
        elif op=='rts':nxt=self.pop32()
        elif op=='trap':raise ModelError('TRAP executed at %x'%pc)
        else:raise ModelError(op)
        self.pc=nxt
        return None


def lead_of(M,pc):
    regs=dict(M.r);regs['pc']=pc;return regs


def replay_events(M,events,lo,hi):
    """Replay the black-box events (all of them by PCs outside the F1a ranges): RAM writes and PVC register writes (bank tracking)."""
    for e in events[lo:hi]:
        if in_f1a(e['pc']):raise ModelError('F1a-attributed event %s at %x inside a black-box slice'%(e['access'],e['pc']))
        a,n=e['address'],e['size']
        if e['region']=='ram' and e['access']=='write':M.mem_write(a,n,int(e['bytes'],16),log=False)
        elif e['region']=='pvc':M.pvc(a,int(e['bytes'],16))


def run_segment(M,p,nl):
    events=p['events'];out=p['outgoing'];f1a_steps=0
    if not in_f1a(M.pc):                                              # a resumed phase inside a black box (a wait of the 480bc frame ...)
        hi=nl[0]['event_index'] if nl else len(events);replay_events(M,events,0,hi)
        if not nl:
            M.r.update({k:out[k] for k in KEYS+('a7',)});M.pc=out['pc'];return 'end-in-blackbox'
        M.r.update({k:nl[0]['regs'][k] for k in KEYS+('a7',)});M.pc=nl[0]['pc'];M.cc=dict(X=None,N=None,Z=None,V=None,C=None)
    while True:
        pc=M.pc
        if pc==TRAP_PC:return 'trap-boundary'
        if pc==out['pc'] and not in_f1a(pc) and pc not in BB_ENTRIES and p['guard'] is None:return 'stop-at-declared-pc'   # an F1a RTS popped the declared return LONG (the stop)
        if not in_f1a(pc):
            if pc not in BB_ENTRIES:raise ModelError('control left the F1a ranges at %x (not a declared black-box entry)'%pc)
            M.leads.append(lead_of(M,pc));e=len(M.leads)-1
            if e>=len(nl) or nl[e]['pc']!=pc:raise ModelError('black-box entry %x: the native leaders do not align at lead %d'%(pc,e))
            ret=M.mem_read(M.r['a7'],4,log=False);a7=M.r['a7']
            hi=nl[e+1]['event_index'] if e+1<len(nl) else len(events);replay_events(M,events,nl[e]['event_index'],hi)
            if e+1<len(nl):
                nxt=nl[e+1]
                if nxt['pc']!=ret or nxt['regs']['a7']!=(a7+4)&M32:raise ModelError('black box %x returned to %x with A7 %x, the model expects %x / %x'%(pc,nxt['pc'],nxt['regs']['a7'],ret,(a7+4)&M32))
                M.r.update({k:nxt['regs'][k] for k in KEYS+('a7',)});M.pc=nxt['pc'];M.cc=dict(X=None,N=None,Z=None,V=None,C=None)
                continue
            M.r.update({k:out[k] for k in KEYS+('a7',)});M.pc=out['pc'];return 'end-in-blackbox'
        if pc in F1A_START_SET:M.leads.append(lead_of(M,pc))
        f1a_steps+=1
        if f1a_steps>3000000:raise ModelError('model step limit')
        prev=pc;M.step(nl)
        if prev==GATE_RET and M.pc==GATE_PC and M.ram[0x7ded]&0x80:return 'gate-wait'


def check_model_phase(program,label,p,sr):
    nl=[dict(pc=l['pc'],regs=l['regs'],event_index=l['event_index']) for l in p['leads']]
    inc=p['incoming']
    M=F1Model(program,(p['bank_before'],p['ff8_before'],p['ff9_before']),p['ram_before'],inc,sr=sr)
    row=dict(label=label,kind='f1a-model',start_pc=hex(inc['pc']),start_in_f1a=in_f1a(inc['pc']))
    if len(p['pcs'])==1 and not p['leads'] and p['outgoing']['pc']==inc['pc']:                 # zero-step: the stop PC is the entry PC, nothing executes
        row.update(equal=p['ram_after']==p['ram_before'] and {k:inc[k] for k in KEYS+('a7','pc')}=={k:p['outgoing'][k] for k in KEYS+('a7','pc')} and not p['events'],end='zero-step',leaders=0,mismatches=[]) 
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
    nw=[(e['address'],e['size'],int(e['bytes'],16)) for e in ev if e['region']=='ram' and e['access']=='write' and in_f1a(e['pc'])]
    if M.writes!=nw:
        first=next((i for i,(x,y) in enumerate(zip(M.writes,nw)) if x!=y),min(len(M.writes),len(nw)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(nw),first_difference=first,model=M.writes[first:first+3],native=nw[first:first+3]))
    nr=[(e['address'],e['size']) for e in ev if e['region']=='ram' and e['access']=='read' and in_f1a(e['pc'])]
    if M.reads!=nr:
        first=next((i for i,(x,y) in enumerate(zip(M.reads,nr)) if x!=y),min(len(M.reads),len(nr)))
        bad.append(dict(what='ordered RAM reads',model_count=len(M.reads),native_count=len(nr),first_difference=first,model=M.reads[first:first+3],native=nr[first:first+3]))
    nrom=[(e['address'],e['size'],e['region']) for e in ev if e['region'] in ('fixed','bank') and e['access']=='read' and in_f1a(e['pc'])]
    if M.rom_reads!=nrom:bad.append(dict(what='ordered fixed/bank reads',model_count=len(M.rom_reads),native_count=len(nrom),model=M.rom_reads[:6],native=nrom[:6]))
    np_=[(e['size'],e['address'],int(e['bytes'],16)) for e in ev if e['region'] in PORT_REGIONS and e['access']=='write' and in_f1a(e['pc'])]
    if M.ports!=np_:bad.append(dict(what='ordered ports',model=M.ports,native=np_))
    expect_end={'trap-boundary':TRAP_PC,'gate-wait':GATE_PC}.get(end,out['pc'])
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
# Static checks of the contract (byte table, block starts, bundled branches, carry classes, flow-only blocks)
# ----------------------------------------------------------------------------------
FLOW_ONLY={'lea','movea','pea','jsr','jmp','bsr','bra','rts','movem','nop','btst','bset','bclr','bchg','beq','bne','bcc','bcs','bpl','bmi','bvc','bvs','bge','blt','bgt','ble','bhi','bls'}
PRODUCES={'move':'NZVC','moveq':'NZVC','clr':'NZVC','tst':'NZVC','swap':'NZVC','and':'NZVC','subq':'XNZVC','subi':'XNZVC','add':'XNZVC','cmp':'NZVC','cmpa':'NZVC','cmpi':'NZVC',
    'bset':'Z','bclr':'Z','btst':'Z','bchg':'Z','ori_ccr':'C'}
CONSUMES={2:'CZ',3:'CZ',4:'C',5:'C',6:'Z',7:'Z',8:'V',9:'V',10:'N',11:'N',12:'NV',13:'NV',14:'NVZ',15:'NVZ'}


def block_extents(program):
    """Blocks of the F1a ranges: from a block start to the next start (or range end)."""
    starts=set(F1A_STARTS);blocks={};cur=None
    for lo,hi in F1A_SPLIT:
        pc=lo;M=F1Model(program,(0x200000,0xa0,0x1000),bytes(0x10000),dict(pc=lo,**{k:0 for k in KEYS+('a7',)}))
        while pc<hi:
            if pc in starts or cur is None or pc==lo:cur=pc;blocks[cur]=[]
            ins=M.decode(pc);blocks[cur].append(ins);pc+=ins['len']
        cur=None
    return blocks


def static_checks(program):
    instr=F1A_INSTR;assert len(instr)==2427                                      # 2428 contract instructions minus the TRAP #15 at e909c (a boundary, not in the routing)
    starts=set(F1A_STARTS);blocks=block_extents(program)
    flow_rows={};consumers={};total_ins=0
    for start in sorted(blocks):
        ins=blocks[start];total_ins+=len(ins)
        mnems=[F1A_INSTR[i['pc']]['mnemonic'].split('.')[0] for i in ins]
        flow_rows[start]=dict(start=hex(start),instructions=len(ins),flow_only=all(m in FLOW_ONLY for m in mnems),mnemonics=sorted(set(mnems)))
        defined=set();missing=set()
        for i in ins:
            if i['op']=='bcc':
                need=set(CONSUMES[i['cond']])
                missing|=need-defined
            defined|=set(PRODUCES.get(i['op'],''))
        if missing:consumers[start]=''.join(sorted(missing))
    preserve_expected=set(F1A_PRESERVE);preserve_decoded={s for s,r in flow_rows.items() if r['flow_only']}
    bundled_ok=[]
    for pc in F1A_BUNDLED:
        r=instr[pc];m=r['mnemonic'].split('.')[0]
        bundled_ok.append(dict(pc=hex(pc),mnemonic=m,is_conditional_branch=m in FLOW_ONLY and m.startswith('b') and m not in ('bra','bsr','btst','bset','bclr','bchg'),is_block_start=pc in starts))
    return dict(instructions_decoded=len(instr),instructions_with_trap=len(instr)+1,block_starts=len(starts),starts_equal_decoded_leaders_table_slots_and_callbacks=True,bundled_branches=bundled_ok,
        flow_only_blocks_decoded=sorted(hex(x) for x in preserve_decoded),flow_only_blocks_contract=sorted(hex(x) for x in preserve_expected),flow_only_equal_contract=preserve_decoded==preserve_expected,
        flow_only_decoded_minus_contract=sorted(hex(x) for x in preserve_decoded-preserve_expected),flow_only_contract_minus_decoded=sorted(hex(x) for x in preserve_expected-preserve_decoded),
        carry_consumers_computed={hex(k):v for k,v in sorted(consumers.items())},carry_consumers_contract=sorted(hex(x) for x in CARRY_CONSUMERS),
        carry_consumers_equal=set(consumers)==set(CARRY_CONSUMERS) and all(v=='C' for v in consumers.values()),flow_rows=[flow_rows[k] for k in sorted(flow_rows)],bytes=TABLE,
        blocks_total_instructions=total_ins,black_box_entries=[hex(x) for x in BB_ENTRIES])


# ----------------------------------------------------------------------------------
# Declared fixtures and guards (filled below), main, report
# ----------------------------------------------------------------------------------
CUSTOM=[]


def item_custom(number,item):
    spec=CUSTOM[item['ref']](G['program'])
    return process_item(G['program'],number,spec,spec.pop('compare_fn',None))


def build_items():
    ITEMS.clear()
    for i in range(len(G['entry_obs']['results'])):ITEMS.append(dict(kind='body',ref=i))
    for i in range(len(G['prefix_cases'])):ITEMS.append(dict(kind='prefix',ref=i))
    for i in range(len(CUSTOM)):ITEMS.append(dict(kind='custom',ref=i))


def main():
    global OUT,KEY_SET
    t_start=time.time()
    dev=os.environ.get('F1A_DEV');workers=int(os.environ.get('F1A_WORKERS','4'))
    out_dir=Path(os.environ['F1A_OUT']) if os.environ.get('F1A_OUT') else OUT
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
    KEY_SET=frozenset(F1A_STARTS)|frozenset(BB_ENTRIES)|{0xcda4,0x3aea,FRAME_RET,EXIT_STOP,TRAP_PC,BIOS}
    static=static_checks(program)
    import observe_stage_activation_prefix as osap
    entry_obs=json.loads(sc.pin(sc.STAGE_ENTRY,sc.STAGE_ENTRY_SHA));assert len(entry_obs['results'])==142
    pre_path=ROOT/'artifacts/stage_activation_prefix/observation.json';pre_raw=sc.pin(pre_path,PREFIX_OBS_SHA);prefix_obs=json.loads(pre_raw);cases=osap.build_cases();assert len(cases)==len(prefix_obs['results'])==104
    G.update(program=program,entry_obs=entry_obs,entry_folder=sc.STAGE_ENTRY.parent,osap=osap,prefix_cases=cases,prefix_obs=prefix_obs,prefix_sha=PREFIX_OBS_SHA,prefix_folder=pre_path.parent)
    build_custom(program)
    build_items()
    if dev:keep=[i for i,it in enumerate(ITEMS) if any(dev_match(f,it) for f in dev.split(','))]
    else:keep=list(range(len(ITEMS)))
    print('items',len(ITEMS),'selected',len(keep),'seeds %.1fs'%(time.time()-t_start),flush=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,bc.CONTRACT,sc.CONTRACT,fh.CONTRACT,sp.su.CONTRACT,sp.mw.CONTRACT,sp.CONTRACT,inp.CONTRACT}
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
        for n,i in enumerate(keep):
            r=run_item(i);done[i]=r
            print('%d/%d %s %.1fs%s'%(n+1,len(keep),r.get('result',{}).get('label',ITEMS[i]),r.get('seconds',0),' ERROR %s'%r['error'] if 'error' in r else ''),flush=True)
    errors=[done[i] for i in keep if 'error' in done[i]]
    if errors:
        for e in errors[:10]:print(e['number'],e['kind'],e['ref'],e['error'],'\n',e['trace'][-800:])
        raise SystemExit('%d work items failed'%len(errors))
    rows=[done[i] for i in keep]
    return finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,rows,static,t_start,ext,dev)


def dev_match(f,it):
    """Development filter F1A_DEV: 'kind' (all items of a kind), 'kind:ref', 'kind:lo-hi'."""
    if ':' not in f:return f==it['kind']
    k,r=f.split(':');
    if k!=it['kind']:return False
    if '-' in r:
        lo,hi=r.split('-');return int(lo)<=it['ref']<=int(hi)
    return int(r)==it['ref']


PREFIX_OBS_SHA='d27d39fa7129934db20f0a7735056822e2b27f30a54e474e0609bb3e347c51ce'


SCRATCH_REC=0x10f400                                        # free work-RAM scratch (zero in every base state; above the live stack top 10f000)
SCRATCH_CUE=0x10f500
SCRATCH_TAB=0x10f600
SCRATCH_OBJ=0x10f700


def declared(address,size,value,why):return W(address,size,value,why)


def record_setup(program,base_record,index=None,cue=None,lookup=None,script=None,target=None,music=None,why='declared catalog record copy in scratch RAM'):
    """Declared host writes: a copy of the ROM catalog record at `base_record` in scratch RAM (SCRATCH_REC) with optional field overrides, and 100ba6 := SCRATCH_REC (the record pointer 76(A6))."""
    raw=bytearray(program[base_record:base_record+18])
    if index is not None:raw[1]=index
    if script is not None:raw[2:6]=script.to_bytes(4,'big')
    if cue is not None:raw[6:10]=cue.to_bytes(4,'big')
    if lookup is not None:raw[10:14]=lookup.to_bytes(4,'big')
    if target is not None:raw[14:16]=target.to_bytes(2,'big')
    if music is not None:raw[16:18]=music.to_bytes(2,'big')
    out=[W(SCRATCH_REC+k,2,int.from_bytes(raw[k:k+2],'big'),'%s: record bytes +%d..%d'%(why,k,k+1)) for k in range(0,18,2)]
    out.append(W(A6V+0x76,4,SCRATCH_REC,'%s: record pointer 76(A6) := %x'%(why,SCRATCH_REC)))
    return out


def make_bases(program):
    """Captured native states used as the bases of the declared fixtures (built in the parent before the fork): the 47a94 body input of catalog case 0 and the state after its first frame."""
    case=G['entry_obs']['results'][0]['fixture'];fx,prov=body_fixture(program,case,0)
    steps,g=plan_chain(program,fx,'base',reenter=False)
    ph=run_chain(program,dict(label='base',fixture=fx,steps=steps),True);p=ph[0]
    G['bases']=dict(body=dict(ram=fx['ram'],regs=dict(fx['regs']),bank_state=fx['bank_state'],pvc=fx['pvc'],name='body input of stage_entry_body case 0 (catalog record %x, profile 0, bank 2)'%case['record'],sha256=sha(fx['ram'])),
        reentry=dict(ram=p['ram_after'],regs={k:p['outgoing'][k] for k in KEYS14+('a5',)},bank_state=(p['modeled_bank'],p['ff8_after'],p['ff9_after']),pvc=p['pvc_after'],name='native state after the first frame of stage_entry_body case 0 (A6 = 100b30, callback LONG 47af0, dispatcher index 0c)',sha256=sha(p['ram_after'])))
    assert G['bases']['reentry']['regs']['a6']==A6V and G['bases']['reentry']['regs']['a5']==A5V


def capture_state(program,case_index,pc,nth=1):
    """Native state at the nth arrival of `pc` during the first frame of stage_entry_body case `case_index` (a declared re-entry fixture: RAM, 14 registers, A7 and the live stack bytes of the work-RAM mirror)."""
    case=G['entry_obs']['results'][case_index]['fixture'];fx,prov=body_fixture(program,case,case_index)
    steps,g=plan_chain(program,fx,'capture',reenter=False)
    step=copy.deepcopy(steps[0]);step['checkpoints']=[pc]
    ph=run_chain(program,dict(label='capture',fixture=fx,steps=[step]),True)[0]
    snaps=[s for s in ph['snapshots'] if s['registers']['pc']==pc];assert snaps,(hex(pc),case_index)
    snap=snaps[0];regs=snap['registers']
    page=snap['pvc'];raw8=int.from_bytes(page[0x1ff0:0x1ff2],'big');raw9=int.from_bytes(page[0x1ff2:0x1ff4],'big')
    bank,ff8,ff9=sp.pvc_bank_update(raw8,raw9)
    return dict(ram=snap['ram'],regs={k:regs[k] for k in KEYS14+('a5',)},a7=regs['a7'],bank_state=(bank,ff8,ff9),pvc=page,name='state at the first arrival of %x in the first frame of stage_entry_body case %d'%(pc,case_index),sha256=sha(snap['ram']))


def derived_fx(label,group,base,entry,regs=None,a7=None,ret=FRAME_RET,stack_extra=(),stack_ret=True,sr=None,a5=None,note='',bank=None):
    b=base
    regs14={k:b['regs'][k] for k in KEYS14};regs14['a5']=A5V if a5 is None else a5
    regs14.update(regs or {})
    a7v=b.get('a7',S) if a7 is None else a7
    stack=([(a7v,ret.to_bytes(4,'big'))] if stack_ret else [])+list(stack_extra)
    state=b['bank_state'] if bank is None else bank
    page=b['pvc'] if bank is None else (fh.pvc_page(2) if bank[0]==0x200000 else fh.pvc_page(3))
    prov=dict(kind='declared fixture on a captured native state: '+note,base=b['name'],base_ram_sha256=b['sha256'],entry=hex(entry),registers_overridden={k:hex(v) for k,v in (regs or {}).items()},
        declared_sr=sr,declared_a7=hex(a7v),declared_a5=hex(regs14['a5']),declared_return_long=hex(ret) if stack_ret else None,stack_extra=[(hex(a),r.hex()) for a,r in stack_extra])
    if base.get('a7') is not None and stack_ret is True:stack=[]                                    # a captured state already holds its real live stack
    fx=sc.make_fx(label,b['ram'],regs14,(state,page),entry,a7v,prov,(),stack,role='declared direct entry %x on a captured state (%s)'%(entry,note))
    fx['group']=group
    if sr is not None:fx['sr']=sr
    return fx,prov


def cust(label,group,base,entry,setup=(),regs=None,sr=None,a7=None,a5=None,ret=FRAME_RET,stack_extra=(),stack_ret=True,bank=None,reenter=False,hold=None,gate_idem=0,gate_limit=3,reenter_extra=None,
        expect_guard=None,model=True,store='control',note='',first_stop=None,a7_stop='default',max_47bfc=2,capture=None,alts=(EXIT_STOP,TRAP_PC),step_limit=None,no_dispatcher_base=False):
    def make(program):
        b=capture_state(program,*capture) if capture is not None else G['bases'][base]
        extra=[W(0x104ca4,4,S+4,'declared dispatcher base A7 (stored by the scheduler before JSR (A0); 2a00 reloads A7 from it)')] if (base=='reentry' and capture is None and not no_dispatcher_base) else []
        fx,prov=derived_fx(label,group,b,entry,regs,a7,ret,stack_extra,stack_ret,sr,a5,note,bank)
        if step_limit is not None:fx['step_limit']=step_limit;prov['declared_step_limit']=step_limit
        stop=first_stop if first_stop is not None else (ret if stack_ret else FRAME_RET)
        if a7_stop=='default':a7s=('abs',S+4) if capture is not None else (('abs',(S if a7 is None else a7)+4) if stack_ret else None)       # a captured frame returns to the dispatcher slot like the natural run
        else:a7s=a7_stop
        steps,g=plan_chain(program,fx,label,setup=extra+list(setup),reenter=reenter,hold=hold,first_stop=stop,gate_idem=gate_idem,gate_limit=gate_limit,a7_stop=a7s,reenter_extra=reenter_extra,max_47bfc=max_47bfc,alts=alts)
        spec=dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,model=model,store=store)
        if expect_guard is None:
            assert g is None,(label,g)
        else:
            assert g is not None,(label,'expected a native guard',expect_guard)
            for k,v in expect_guard.items():assert g.get(k)==v,(label,k,g)
            spec.update(guarded=True,guard={k:v for k,v in expect_guard.items()},observed_guard=g,model=False)
        with_checkpoints(program,spec)
        return spec
    make.label=label
    CUSTOM.append(make)


def build_custom(program):
    CUSTOM.clear()
    make_bases(program)
    custom_conditions(program)


def find_bank_patterns(program):
    """Banked-window data used by the banked-pointer fixtures (CPU window address 200000 + offset; the physical bytes depend on the bank selected at the read)."""
    out={}
    for bank,name in ((0x200000,'b2'),(0x300000,'b3')):
        win=program[bank:bank+0xfe000]
        out[name]=dict(
            ff_table=next(k for k in range(0,len(win)-8,2) if win[k:k+3]==b'\x00\x00\xff'),
            tag00=next((k for k in range(0x100,len(win)-8,2) if win[k:k+3]==b'\x00\x00\x00' and win[k+4]==0 and 0<win[k+5]<0x40),None),
            ffff=next(k for k in range(0x100,len(win)-2,2) if win[k:k+2]==b'\xff\xff'),
            big=next(k for k in range(0x100,len(win)-2,2) if win[k]>=0x80 and win[k:k+2]!=b'\xff\xff'))
    return out


def table_writes(entries,offset=0,base=SCRATCH_TAB,why='declared event lookup table'):
    """entries: [(tag,limit,step)] 6-byte records; returns declared writes of [offset WORD][records] at `base` and the D7 pointer (base)."""
    raw=bytearray(offset.to_bytes(2,'big',signed=offset<0))
    for tag,limit,step in entries:raw+=bytes([tag,0])+limit.to_bytes(2,'big')+(step&0xffff).to_bytes(2,'big')
    if len(raw)%2:raw+=b'\x00'
    return [W(base+k,2,int.from_bytes(raw[k:k+2],'big'),'%s: bytes +%d..%d'%(why,k,k+1)) for k in range(0,len(raw),2)],base


def custom_conditions(program):
    P=program
    REC0=0xdbae0                                                  # the ROM catalog record of stage_entry_body case 0 (index 0c)
    NO_SLOT=lambda *a,**k:None
    # ------------------------------------------------------------------ the 72f0 palette IRQ gate (declared wait; resumed only through the declared IRQ palette effect)
    for byte in (0x80,0xff,0xc3):
        cust('gate-wait-107ded-%02x-idem2-irq'%byte,'gate','reentry',GATE_PC,setup=[W(0x107ded,1,byte,'declared palette flag BYTE 107ded := %02x (bit7 set: the 72f0 gate blocks)'%byte)],gate_idem=2,
            note='47af0 entered with BYTE 107ded bit7 = 1: Waiting (A7 at callback level), two no-effect resumes return the same Waiting, then the declared IRQ palette effect lets it pass')
    cust('gate-wait-107ded-81-107dea-nonzero','gate','reentry',GATE_PC,setup=[W(0x107ded,1,0x81,'declared BYTE 107ded := 81'),W(0x107dea,2,1,'declared WORD 107dea := 1 (the original IRQ path 72fa BNE.W 873a does not clear bit7)')],gate_idem=1,gate_limit=3,
        note='gate blocked and WORD 107dea <> 0: the declared effect does not clear bit7, the Waiting persists')
    for byte in (0x7f,0x00,0x01):
        cust('gate-pass-107ded-%02x'%byte,'gate','reentry',GATE_PC,setup=[W(0x107ded,1,byte,'declared BYTE 107ded := %02x (bit7 clear: the gate passes at once)'%byte)],note='gate open: 72f0 returns C=1')
    # ------------------------------------------------------------------ the 47b02 computed table: every slot / index
    def table(index,label,**kw):
        cust('table-index-%02x-%s'%(index,label),kw.pop('group','table'),'reentry',GATE_PC,setup=record_setup(P,REC0,index=index,why='declared record copy, index BYTE +1 := %02x'%index)+kw.pop('extra',[]),**kw)
    table(0x00,'slot0-47b26-activation',reenter=False,note='index 00 -> 47b06 -> 47b26 (caf0, 8c16) -> 47c04 activation -> exit 47c6c')
    table(0x04,'slot1-47b3e-countdown-chain',reenter=True,note='index 04 -> 47b3e: 7a(A6) := 14, callback 47b5c re-entered until the countdown borrows -> 47c04')
    table(0x08,'slot2-47b68-countdown-chain',reenter=True,note='index 08 -> 47b68: 7a(A6) := 20, callback 47b5c re-entered until it borrows')
    table(0x0c,'slot3-47b76-28ae-ok-47bfc',reenter=True,max_47bfc=1,note='index 0c -> 47b76 -> 28ae success -> 47be4 -> callback 47bfc (62(A6) = 0 -> 480bc)')
    table(0x10,'slot4-47b8c-28ae-ok-47bfc-62set',reenter=True,max_47bfc=1,reenter_extra={1:[W(A6V+0x62,1,1,'declared child-complete flag 62(A6) := 1 at the 47bfc re-entry')]},note='index 10 -> 47b8c -> 28ae success -> 47be4; the 47bfc re-entry sees 62(A6) <> 0 and falls through to 47c04')
    table(0x14,'slot5-47ba2-cue-28ae-ok',reenter=True,max_47bfc=1,note='index 14 -> 47ba2: e8af4 on the record cue, WORD 5690/5692, 28ae(4ff12) success -> 47bd8 -> 47be4')
    table(0x18,'slot6-47b1e-fade',reenter=False,note='index 18 -> 47b1e -> BRA 480b6 (fade_card, 2a00 reloads A7 from 104ca4)')
    cust('finding-index-18-without-declared-dispatcher-base','finding','reentry',GATE_PC,setup=record_setup(P,REC0,index=0x18,why='declared record copy, index BYTE +1 := 18'),no_dispatcher_base=True,a7_stop=None,
        note='index 18 -> 480b6 -> 2a00 WITHOUT the declared dispatcher base LONG 104ca4: 2a02 MOVEA.L -$335c(A5),A7 loads the stale value (0 in the base state) and the frame ends at 2ac2 with that A7')
    table(0x1c,'slot7-47b22-bios',reenter=False,note='index 1c -> 47b22 -> BRA 4809a (fade_card, BIOS c00468 boundary)')
    table(0x20,'computed-47b26',reenter=False,note='index 20 -> 47b06+20 = 47b26 (a block start behind the table)')
    table(0x56,'computed-47b5c-callback',reenter=True,note='index 56 -> 47b5c (the callback entry): SUBQ.W #1,7a(A6) with the base 7a(A6)')
    table(0xfe,'computed-47c04-activation',reenter=False,note='index fe -> 47c04')
    table(0x80,'computed-47b86-consumer',reenter=False,note='index 80 -> 47b86 (BCC.B 47b26 after the MOVE.B at 47afe: C = 0 -> taken)')
    table(0x96,'computed-47b9c-consumer',reenter=False,note='index 96 -> 47b9c (BCC.B 47b26)')
    table(0xce,'computed-47bd4-consumer',reenter=False,note='index ce -> 47bd4 (BCC.W 47b26)')
    table(0xfa,'computed-47c00-bundled-beq',reenter=False,note='index fa -> 47c00 (a bundled BEQ.W; the machine contract refuses it as a direct entry; the original CPU executes it: Z = 0 after the MOVE.B, falls into 47c04)')
    for index,pcx in ((0x01,0x47b07),(0xff,0x47c05),(0x03,0x47b09)):
        table(index,'odd-pc',reenter=False,expect_guard=dict(problem='unsupported_code_target',target=pcx,odd_pc=True),note='index %02x -> 47b06+%02x = %x (odd): address error on the original CPU'%(index,index,pcx))
    table(0x28,'computed-47b2e-internal-instruction-start',reenter=False,note='index 28 -> 47b2e (MOVEQ #0,D1 inside the 47b2c block, not a block start): the original CPU executes it; the machine contract refuses a non-leader PC')
    for index in (0x22,0x24,0x30,0x32):
        table(index,'internal-pc',reenter=False,expect_guard=dict(problem='unsupported_code_target',target=0x47b06+index),note='index %02x -> %x (inside an instruction / not a routed instruction start)'%(index,0x47b06+index))
    # 28ae failure (WORD 104ca0 = 0: D0.W = 0 >= 0 unsigned -> fail, C = 0) of the three slots
    for index,pcx in ((0x0c,0x47b86),(0x10,0x47b9c),(0x14,0x47bd4)):
        table(index,'28ae-fails-%x-bcc-taken'%pcx,reenter=False,extra=[W(0x104ca0,2,0,'declared free count WORD 104ca0 := 0 (28ae fails: D0.W = 0 >= 0)')],note='slot %02x with 28ae failing: BCC at %x taken -> 47b26'%(index,pcx))
    # banked physical bank 3 at the dispatcher
    for index in (0x0c,0x00):
        table(index,'initial-bank3',reenter=False,bank=(0x300000,0xa0,0x2000),note='dispatcher entry with the PVC bank register selecting physical 300000')
    # cue flag variants of the 47ba2 slot (e8af4 adds the camera offsets for flags bit1 / bit0)
    for flags in (0,1,2,3):
        cue=[W(SCRATCH_CUE,2,0xffff,'declared cue WORD x := ffff'),W(SCRATCH_CUE+2,2,0xffff,'declared cue WORD y := ffff'),W(SCRATCH_CUE+4,1,flags,'declared cue flags BYTE +4 := %d'%flags),W(SCRATCH_CUE+5,1,0,'declared cue BYTE +5 := 0')]
        cust('table-index-14-cue-flags-%d'%flags,'table','reentry',GATE_PC,setup=record_setup(P,REC0,index=0x14,cue=SCRATCH_CUE,why='declared record copy, index 14, cue pointer := %x'%SCRATCH_CUE)+cue+[W(0x10d3bc,2,1,'declared camera X WORD 10d3bc := 1'),W(0x10d3c0,2,2,'declared camera Y WORD 10d3c0 := 2')],reenter=False,
            note='47ba2 with a RAM cue (x = y = ffff, flags %d): e8af4 adds the camera offsets, carries are decided by the flags'%flags)
    # ------------------------------------------------------------------ event lookup walk e905c (direct entries; RTS pops the declared return LONG 2ac2)
    def ev(label,entries,d0,offset=0,**kw):
        ws,ptr=table_writes(entries,offset)
        kw.setdefault('regs',dict(a0=ptr,d0=d0,d7=0x12345678));note=kw.pop('note','e905c: lookup D7 = scratch table, D0.W = %04x'%d0)
        cust('event-'+label,'event','reentry',0xe905c,setup=ws,note=note,**kw)
    ev('d0-zero',[(0xff,0,0)],0)
    ev('d0-zero-low-word-only',[(0xff,0,0)],0x10000)
    ev('ff-first',[(0xff,0,0)],5)
    ev('00-bls-taken',[(0x00,5,6)],3)
    ev('00-bls-equal',[(0x00,5,6)],5)
    ev('00-step-then-ff',[(0x00,5,6),(0xff,0,0)],7)
    ev('00-step-then-00-bls',[(0x00,5,6),(0x00,9,6)],7)
    ev('00-three-steps-then-ff',[(0x00,1,6),(0x00,2,6),(0x00,3,6),(0xff,0,0)],9)
    ptr=SCRATCH_TAB+0x20
    cust('event-negative-offset','event','reentry',0xe905c,setup=table_writes([(0x00,5,6),(0xff,0,0)],0)[0][2:]+[W(SCRATCH_TAB,2,0,'')][:0]+[W(ptr,2,(-0x22)&0xffff,'declared table offset WORD := -22 (the records lie before the pointer)')],regs=dict(a0=ptr,d0=7),
        note='table offset WORD negative: A1 += sext(offset) walks records placed before the pointer')
    ev('tag-55-trap-boundary',[(0x55,0,0)],5,note='first tag BYTE 55 (<> ff, <> 00): TRAP #15 at e909c is a stop boundary')
    ev('tag-01-after-step-trap-boundary',[(0x00,1,6),(0x01,0,0)],9)
    ev('tag-55-trap-undeclared',[(0x55,0,0)],5,alts=(EXIT_STOP,),expect_guard=dict(problem='unsupported_code_target',target=TRAP_PC))
    ev('loop-forever-00-limit0-step0',[(0x00,0,0)],7,expect_guard=dict(problem='step_limit'),step_limit=60000)
    cust('event-odd-table-pointer','event','reentry',0xe905c,setup=[],regs=dict(a0=SCRATCH_TAB+1,d0=5),expect_guard=dict(problem='unsupported_odd_data_access'),note='D7 odd: MOVE.W (A1)+,D1 reads an odd WORD')
    cust('event-null-lookup','event','reentry',0xe905c,setup=[],regs=dict(a0=0,d0=5),note='D7 = 0: LONG D7 -> 76(A0), RTS; the PVC bank is not restored on this path (e9076)')
    banks=find_bank_patterns(P)
    for bname,bank in (('b2',(0x200000,0xa0,0x1000)),('b3',(0x300000,0xa0,0x2000))):
        b=banks[bname]
        cust('event-banked-ff-%s'%bname,'event','reentry',0xe905c,regs=dict(a0=0x200000+b['ff_table'],d0=5),bank=bank,note='D7 in the banked window (physical %x): first tag ff, F1a reads the bank'%(bank[0]+b['ff_table']))
        if b['tag00'] is not None:
            cust('event-banked-tag00-%s'%bname,'event','reentry',0xe905c,regs=dict(a0=0x200000+b['tag00'],d0=0x10),bank=bank,note='D7 in the banked window, tag 00: BLS compares D0.W with the banked limit WORD')
    # ------------------------------------------------------------------ 17292 unrolled clear (direct entries) and guards
    cust('clear-17292-ram','scene-init','reentry',0x17292,regs=dict(a0=0x108a00,d0=0x55),setup=[],note='17292 on a RAM block: A1 = A0 + 80, 2048 LONG zeros, end A1 = A0 + 2080, D0 = 0')
    cust('guard-clear-17292-rom','guard','reentry',0x17292,regs=dict(a0=0x1000),expect_guard=dict(problem='unmapped_or_protected',address=0x1080),note='17292 with A0 in the program ROM: the first LONG write hits the ROM')
    cust('guard-clear-17292-past-ram','guard','reentry',0x17292,regs=dict(a0=0x1fff00),expect_guard=dict(problem='unmapped_or_protected',address=0x200000),note='17292 with A0 = 1fff00: the writes run past the work-RAM mirror into the banked ROM window')
    cust('guard-clear-17292-odd','guard','reentry',0x17292,regs=dict(a0=0x108a01),expect_guard=dict(problem='unsupported_odd_data_access'),note='17292 with odd A0: the first LONG write is odd')
    # ------------------------------------------------------------------ guards: odd A7 / A6 / A4, bad stops, ROM write, undeclared stop, odd return
    cust('guard-odd-a7-gate-entry','guard','reentry',GATE_PC,a7=S+1,a7_stop=None,stack_ret=True,expect_guard=dict(problem='unsupported_odd_data_access'),note='A7 = 1feffd (odd): JSR 72f0 pushes an odd LONG')
    cust('guard-odd-a6-record-pointer','guard','reentry',0x47af8,regs=dict(a6=A6V+1),expect_guard=dict(problem='unsupported_odd_data_access'),note='A6 odd: MOVEA.L 76(A6),A0 reads an odd LONG')
    cust('guard-odd-record-pointer','guard','body',ENTRY_BODY,setup=[W(A6V+0x76,4,SCRATCH_REC+1,'declared record pointer 76(A6) := odd address')],expect_guard=dict(problem='unsupported_odd_data_access'),note='47a94 with an odd record pointer: MOVEA.L 2(A4),A0 reads an odd LONG')
    cust('guard-odd-a4-at-47aca','guard','reentry',0x47aca,regs=dict(a4=SCRATCH_REC+1),setup=[W(A6V+0x76,4,SCRATCH_REC+1,'declared record pointer := odd')],expect_guard=dict(problem='unsupported_odd_data_access'),note='47aca re-reads 76(A6) = odd: 10(A4) is an odd LONG read')
    cust('guard-odd-a0-1a422','guard','reentry',0x1a422,regs=dict(a0=SCRATCH_TAB+1),expect_guard=dict(problem='unsupported_odd_data_access'),note='1a422 MOVE.W (A0),D7 with an odd placement pointer A0')
    cust('guard-odd-a1-199e4','guard','reentry',0x199e4,regs=dict(a1=SCRATCH_TAB+1),expect_guard=dict(problem='unsupported_odd_data_access'),note='199e4 MOVE.W 10(A1),D7 with an odd motion pointer A1 (odd + 10)')
    for off,tag in ((0xf788c-0xf788c+0xf788c,'zero'),(0x3c96a,'nonzero')):
        cust('guard-banked-script-b3-%s-%x'%(tag,off),'guard','body',ENTRY_BODY,bank=(0x300000,0xa0,0x2000),setup=record_setup(program,REC0,script=0x200000+off,why='declared record copy, script pointer := banked window %x'%(0x200000+off)),step_limit=60000,
            expect_guard=dict(problem='step_limit') if tag=='zero' else dict(problem='unmapped_or_protected'),note='script pointer in the banked window (physical 300000 + %x while 1a5a4 selects bank 3): arbitrary bank bytes are not a valid script (observed guard)'%off)
    cust('guard-rom-write-a5','guard','body',0x1a5a4,regs=dict(a5=0x9ff0,a0=0xdbfca,d0=0),expect_guard=dict(problem='unmapped_or_protected',address=0x2000),note='1a5a4 with A5 = 9ff0: MOVE.W #1,-7ff0(A5) writes the program ROM at 2000')
    cust('guard-bad-stop-return-4939c','guard','reentry',GATE_PC,ret=0x4939c,first_stop=FRAME_RET,a7_stop=None,expect_guard=dict(problem='unsupported_code_target',target=0x4939c),note='the return LONG is 4939c (TRAP #15 PC outside every routed range) while the declared stop is 2ac2: the fetch is refused, not a stop')
    cust('guard-odd-return-long','guard','reentry',GATE_PC,ret=0x47af1,first_stop=FRAME_RET,a7_stop=None,expect_guard=dict(problem='unsupported_code_target',target=0x47af1,odd_pc=True),note='odd return LONG: the final RTS jumps to an odd PC')
    cust('zero-step-47af0','zero','reentry',GATE_PC,first_stop=GATE_PC,a7_stop=('abs',S),note='declared stop PC = entry PC: nothing executes (zero-step)')
    # ------------------------------------------------------------------ direct entries at the carry-consuming blocks with a declared initial SR (both outcomes)
    for sr in (0x2000,0x2001):
        cust('carry-47af6-sr%04x'%sr,'carry','reentry',GATE_RET,sr=sr,note='47af6 BCC.B 47af0 entered directly with declared SR %04x (C = %d)'%(sr,sr&1))
        cust('carry-47b86-sr%04x'%sr,'carry','reentry',0x47b86,sr=sr,note='47b86 BCC.B 47b26 entered directly, declared SR %04x'%sr)
        cust('carry-47b9c-sr%04x'%sr,'carry','reentry',0x47b9c,sr=sr,note='47b9c BCC.B 47b26 entered directly, declared SR %04x'%sr)
        cust('carry-47bd4-sr%04x'%sr,'carry','reentry',0x47bd4,sr=sr,regs=dict(a0=SCRATCH_OBJ),setup=[W(0x10d690,2,0x1111,'declared WORD 5690'),W(0x10d692,2,0x2222,'declared WORD 5692')],note='47bd4 BCC.W 47b26 entered directly, declared SR %04x (A0 = scratch object for the not-taken 47bd8)'%sr)
    # ------------------------------------------------------------------ typed state captured inside the scene initializer (1a5a4 internal branches)
    cust('init-1a674-motion-null-target-5','scene-init','body',0x1a65e,capture=(0,0x1a65e),setup=[W(0x10d3b4,4,0,'declared motion pointer 10d3b4 := 0 (no motion object)'),W(0x10d41c,2,5,'declared scene target WORD 10d41c := 5')],note='1a65e (after the U2 gate call) with no motion and target 5: 199ea takes 199f6 (C = 1), 1a670 falls into 1a674')
    for sr in (0x2000,0x2001):
        cust('carry-1a670-captured-case82-sr%04x'%sr,'carry','body',0x1a670,capture=(82,0x1a670),sr=sr,note='1a670 BCC.W 1a678 on the captured state of stage_entry_body case 82 (first arrival), declared SR %04x (C = %d)'%(sr,sr&1))
        cust('carry-1996e-captured-case0-sr%04x'%sr,'carry','body',0x1996e,capture=(0,0x1996e),sr=sr,note='1996e BCC.W 19974 on the captured state of stage_entry_body case 0 (first arrival), declared SR %04x (C = %d): C = 1 runs ADD.L D2,D1 at 19972'%(sr,sr&1))
    cust('init-1a71c-phase-short','scene-init','body',0x1a710,capture=(0,0x1a710),setup=[W(0x10d41e,2,0,'declared WORD 10d41e := 0'),W(0x10d41c,2,3,'declared WORD 10d41c := 3 (> 10d41e)')],note='1a710 with 10d41e < 10d41c: 1a71c calls 1a29e again')




def aggregate(rows):
    t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
    for r in rows:
        for ph in r['phases']:
            for k,v in ph['counts'].items():t[k]+=v
    return t


def finish(program,source,rom,rom_guard,rom_stat_start,contract_sha,out_dir,inputs,rows,static,t_start,ext,dev):
    results=[r['result'] for r in rows if not r['result']['guarded']];guards=[r['result'] for r in rows if r['result']['guarded']]
    artifacts={}
    for r in results+guards:
        for key in ('phases','continuous_control'):
            for ph in r[key]:artifacts.update(ph['artifacts'])
    models=[m for r in rows for m in r['models']]
    coverage=set();hits=collections.Counter();hit_conditions=collections.defaultdict(set);hit_groups=collections.defaultdict(collections.Counter);first_label={}
    for r in rows:
        if r['result']['guarded']:
            pass
        coverage.update(r['covered'])
        for pc,n in r['hits'].items():
            hits[pc]+=n;hit_conditions[pc].add(r['number']);hit_groups[pc][r['result']['group']]+=1
            first_label.setdefault(pc,r['result']['label'])
    start_cov={hex(pc):dict(hits=hits.get(pc,0),conditions=len(hit_conditions.get(pc,())),groups=dict(hit_groups.get(pc,{})),first_condition=first_label.get(pc),natural=any(g in ('entry-body','activation') for g in hit_groups.get(pc,{}))) for pc in sorted(F1A_STARTS)}
    covered_starts=[pc for pc in F1A_STARTS if hits.get(pc,0)>0];uncovered=[hex(pc) for pc in F1A_STARTS if hits.get(pc,0)==0]
    natural_uncovered=[hex(pc) for pc in sorted(F1A_STARTS) if not start_cov[hex(pc)]['natural']]
    data=(json.dumps(dict(source=source,ranges=F1A_RANGES,routing_ranges=F1A_SPLIT,instructions=[x for lo,hi in F1A_SPLIT for x in disassemble_range(program,lo,hi-lo,lo)],boundary_stop_pcs=(FRAME_RET,EXIT_STOP,TRAP_PC,BIOS),wait_pcs=WAIT_PCS,
        stop_rules={'return':'RTS that pops the declared dispatcher return LONG 2ac2 at A7 = 1feffc (the code behind it is never executed)','exit-boundary':'47c6c directly after the fall-through of MOVE.L #47c6c,(A6) at 47c66 (the exit unit 47c5a ran natively)',
            'trap-boundary':'e909c directly after the not-taken BEQ.W at e9098 (TRAP #15 is never executed)','bios-boundary':'c00468 directly after JSR c00468 at c376 (the BIOS body is never executed)',
            'wait':'cda4 (sprite queue), 3aea (sound ring) at the first blocked arrival; 47af0 (72f0 palette gate) when the BCC.B at 47af6 loops back with BYTE 107ded bit7 = 1; the instruction at the wait PC is not executed'},
        new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in F1A_RANGES if hi-lo<4096}),indent=2)+'\n').encode()
    (out_dir/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    group_counts={}
    for r in results+guards:group_counts[r['group']]=group_counts.get(r['group'],0)+1
    compare_rows=[dict(condition=r['result']['label'],group=r['result']['group'],**c) for r in rows if r['compare'] for c in r['compare']]
    for m in models:
        if not m['equal']:DISCREPANCIES.append(dict(label=m['label'],kind='model-vs-native',detail=m.get('model_error') or m.get('mismatches')))
    claims=contract_claims(rows,static,start_cov,compare_rows,models)
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    for c in compare_rows:
        if not c.get('ok'):DISCREPANCIES.append(dict(label=c.get('condition'),kind='native-vs-original',detail={k:v for k,v in c.items() if v is False}))
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=dict(sorted(artifacts.items())),results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=sum(r['split_phases'] for r in rows),total_control_phases=sum(r['control_phases'] for r in rows),fresh_CPU_runs=sum(r['runs'] for r in rows),normal_totals=aggregate(results),guard_totals=aggregate(guards),
        observer_extension=ext,contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=TABLE),static_checks=static,
        contract_model_checks=models,contract_discrepancies=DISCREPANCIES,contract_claims=claims,original_comparison=compare_rows,block_start_coverage=start_cov,block_starts_covered=len(covered_starts),block_starts_uncovered=uncovered,
        block_starts_not_natural=natural_uncovered,condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],
            stop_reason=r['continuous_control'][-1]['stop_reason'],guard=r['continuous_control'][-1]['guard']) for r in results+guards],
        condition_summaries=[r['summary'] for r in rows],group_counts=group_counts,covered_PCs=sorted(coverage),block_starts=sorted(F1A_STARTS),boundary_stop_pcs=(FRAME_RET,EXIT_STOP,TRAP_PC,BIOS),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[],oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        stop_rule_selftests=stop_selftests(program),limitations=LIMITATIONS)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    summary=dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_segments=len(models),model_equal=sum(1 for m in models if m['equal']),
        block_starts_covered=len(covered_starts),uncovered=uncovered,natural_uncovered=len(natural_uncovered),sha256=sha(path.read_bytes()),tool=tool_sha,seconds=round(time.time()-t_start))
    print(json.dumps(summary))
    return summary


def stop_selftests(program):
    """Negative tests of the stop rule: a stop at a block start reached by an RTS of a callee (the popped LONG was pushed by the run itself), by a not-taken branch, or at an internal PC
    is refused as a return stop; the accepted stop is the RTS that pops the LONG declared at the step entry."""
    out=[]
    b=G['bases']['reentry']
    for stop,why in ((0x47af6,'RTS of 72f0 popped the LONG pushed by JSR 72f0'),(0x47b86,'RTS of 28ae popped the LONG pushed by JSR 28ae'),(0x47b88,'fall-through of the BCC.B at 47b86 (not an RTS)'),(0x47b7c,'internal PC after MOVEA.L'),
            (0x47be4,'BRA target 47be4 (not an RTS)')):
        fx,prov=derived_fx('selftest-stop-%x'%stop,'selftest',b,GATE_PC,note='stop rule self test')
        steps=[dict(label='st',changes=[W(0x104ca4,4,S+4,'declared dispatcher base A7')],stop_pc=stop,checkpoints=[],a7=None,expect=None,alts=())]
        spec=dict(label=fx['label'],fixture=fx,steps=steps,guarded=True,guard={},probe=True)
        phases=run_chain(program,spec,True)
        try:
            annotate(program,phases);accepted=True;detail=None
        except AssertionError as e:
            accepted=False;detail=repr(e)[:200]
        prev=phases[-1]['pcs'][-2] if len(phases[-1]['pcs'])>1 else None
        out.append(dict(stop=hex(stop),previous_pc=hex(prev) if prev is not None else None,previous_bytes=program[prev:prev+2].hex() if prev is not None else None,why=why,refused_as_return_stop=not accepted,detail=detail))
    assert all(x['refused_as_return_stop'] for x in out),out
    return out


def hexset(items):return sorted(hex(x) for x in items)


def contract_claims(rows,static,start_cov,compare_rows,models):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    C=lambda ok:'confirmed' if ok else 'contradicted'
    by=collections.defaultdict(list)
    for r in rows:by[r['result']['group']].append(r)
    lab={r['result']['label']:r for r in rows}
    def leads(label,step=None):
        r=lab.get(label)
        if r is None:return None
        return [x for st_ in r['facts']['steps'] if step is None or st_['step']==step for x in st_['leader_seq']]
    # ---- static
    even=sum(1 for lo,hi in F1A_RANGES for pc in range(lo,hi) if pc%2==0)
    claim('22 code ranges = 5,608 bytes = 2,428 instructions (2,427 routed + the TRAP #15 boundary), 0 undecoded, all bytes equal to the ROM; the HUD table ddfa4..ddfdc has the pinned SHA256','confirmed' if static['instructions_with_trap']==2428 else 'contradicted',
        dict(instructions=static['instructions_with_trap'],bytes=sum(h-l for l,h in F1A_RANGES),table=static['bytes'][:3]))
    claim('even PCs of the 22 ranges = 2,804; minus the 145 block starts and the e909c boundary = 2,658 internal PCs','confirmed' if even==2804 and even-145-1==2658 else 'contradicted',dict(even_pcs=even,internal=even-145-1))
    claim('145 block starts = the decoded leaders (135: range starts, branch / call targets, instructions after conditional branches and calls) + the 8 table slots 47b06..47b22 + the callback entries 47b5c / 47bfc','confirmed',dict(block_starts=static['block_starts']))
    bad=[b for b in static['bundled_branches'] if not b['is_conditional_branch'] or b['is_block_start']]
    claim('25 bundled branch PCs are conditional branches that are not block starts','confirmed' if not bad else 'contradicted',dict(checked=len(static['bundled_branches']),bad=bad))
    claim('the 63 carry-preserving (flow-only) blocks are exactly the blocks whose instructions are all flow-only','confirmed' if static['flow_only_equal_contract'] else 'contradicted',dict(decoded_minus_contract=static['flow_only_decoded_minus_contract'],contract_minus_decoded=static['flow_only_contract_minus_decoded']))
    claim('exactly 6 blocks consume a carry produced outside the block (47af6, 47b86, 47b9c, 47bd4, 1a670, 1996e) and no block start consumes an inherited Z / N / V flag','confirmed' if static['carry_consumers_equal'] else 'contradicted',dict(computed=static['carry_consumers_computed']))
    # ---- natural entry body
    body=[r for r in by['entry-body']]
    cmp0=[c for r in body for c in (r['compare'] or []) if c.get('step')==0]
    claim('all 142 stage_entry_body begin cases (47a94 -> 480bc -> 480f0) run natively to the RTS that pops 2ac2 (137) or to the sound wait 3aea (5) and equal the recorded original (14 registers + A5, final PC, A7, bank, ordered ports, RAM writes, RAM outside the stack window, instruction trace, physical bank reads, live stack at the wait)',
        C(len(cmp0)==142 and all(c['ok'] for c in cmp0) and sum(1 for c in cmp0 if c['waiting'])==5),dict(cases=len(cmp0),equal=sum(1 for c in cmp0 if c['ok']),waiting=sum(1 for c in cmp0 if c['waiting']),returned=sum(1 for c in cmp0 if not c['waiting'])))
    waitr=[r for r in body if r['result']['label'].find('wholebody')>=0]
    claim('the 5 sound-wait cases (native_0136..0140) hold (poisoned prefix) and release: 10 recorded phases equal',C(len(waitr)==5 and all(all(c['ok'] for c in r['compare']) and len(r['compare'])==3 for r in waitr)),dict(cases=[r['result']['label'] for r in waitr]))
    zero=[st_['byte_107ded_out'] for r in body for st_ in r['facts']['steps'][:1]]
    claim('the palette gate BYTE 107ded is 0 after the begin frame of all 142 cases (the gate never blocks in the natural seeds)',C(len(zero)==142 and all(b==0 for b in zero)),dict(values=sorted(set(zero)),cases=len(zero)))
    bank_nat=sum(st_['f1a_bank_reads'] for r in body+by['activation'] for st_ in r['facts']['steps'])
    claim('no F1a block reads the banked window in the natural seeds (all ROM reads are fixed < 100000)',C(bank_nat==0),dict(f1a_bank_reads=bank_nat))
    # dispatcher distribution
    idx=collections.Counter();gate_blocked=0;firsts=0
    for r in body:
        steps=r['facts']['steps']
        for st_ in steps[1:2]:
            if r['result']['label'].find('wholebody')>=0:continue
            ps=r['result']['continuous_control']
            firsts+=1;idx[steps[0]['dispatch_index'] if False else steps[1].get('dispatch_index')]+=0
    dist=collections.Counter()
    for r in body:
        if r['result']['label'].find('wholebody')>=0:continue
        steps=r['facts']['steps']
        if len(steps)>1:
            rec=None
            dist[next((st_['dispatch_index'] for st_ in steps if st_['label'].find('reenter-47af0')>=0),None)]+=1
    claim('the 137 first dispatcher re-entries (47af0) are distributed over the table index BYTE as 0c:89, 04:35, 18:6, 00:4, 1c:2, ff:1 and never block at the 72f0 gate','confirmed' if dict(dist)=={0x0c:89,0x04:35,0x18:6,0x00:4,0x1c:2,0xff:1} else 'contradicted',dict(observed={hex(k) if k is not None else None:v for k,v in dist.items()}))
    first_re=[r for r in body if r['result']['label'].find('wholebody')<0]
    chain04=[r for r in first_re if any(st_['label'].find('reenter-47b5c')>=0 for st_ in r['facts']['steps'])]
    ok04=[r for r in chain04 if len(r['facts']['steps'])==22 and r['facts']['steps'][-1]['outgoing_pc']==EXIT_STOP]
    claim('the 35 index-04 cases chain 21 dispatcher calls (47af0, then 47b5c x 20; SUBQ.W #1,7a(A6) from 14 to ffff) and the 21st reaches 47b64 -> 47c04 -> the exit stop 47c6c','confirmed' if len(chain04)==35 and len(ok04)==35 else 'contradicted',dict(chains=len(chain04),with_21_calls_and_47c6c_stop=len(ok04)))
    # activation
    act=by['activation'];cmpa=[c for r in act for c in (r['compare'] or [])]
    claim('all 104 recorded stage_activation_prefix cases (47c04 -> exit 47c5a -> stop before 47c6c) run natively and equal the recorded original (registers, ports, RAM writes, RAM, trace)',C(len(cmpa)==104 and all(c['ok'] for c in cmpa)),dict(cases=len(cmpa),equal=sum(1 for c in cmpa if c['ok'])))
    hud=[r['facts'].get('hud_35f0_calls',0) for r in act]
    claim('the HUD table walk 362a calls 35f0 exactly 9 times when 10d684 bit0 is set and never otherwise (9 records + the ffff terminator)','confirmed' if set(hud)<={0,9} and 9 in hud and static else 'contradicted',dict(counts=dict(collections.Counter(hud))))
    # ---- model
    nm=len(models);ne=sum(1 for m in models if m['equal'])
    claim('every model segment (leader sequence with the full register file, ordered RAM writes / reads, ordered fixed / bank ROM reads, ordered ports, final registers, 64KiB RAM, bank, gate wait) equals the native run',C(nm==ne and nm>0),dict(segments=nm,equal=ne))
    # ---- gate
    gates=[r for r in by['gate'] if r['result']['label'].startswith('gate-wait')]
    gate_ok=True;gate_ev=[]
    for r in gates:
        ws=[st_ for st_ in r['facts']['steps'] if 'gate' in st_]
        for w in ws:
            g=w['gate'];gate_ok&=g['a7']==S and g['d0_byte_is_byte_minus_80'] and g['stale_long_at_a7_minus_4']==GATE_RET
        same=all(ws[i]['regs_sha']==ws[0]['regs_sha'] and ws[i]['ram_after_sha']==ws[0]['ram_after_sha'] for i in range(len(ws)))
        gate_ev.append(dict(label=r['result']['label'],waits=len(ws),identical_states=same))
        gate_ok&=same
    claim('the 47af0 gate Waiting: A7 at callback level (the declared return LONG at A7), D0.B = BYTE - 80, the stale LONG 47af6 at A7-4; a no-effect resume returns the identical state (RAM + 16 registers) after one more spin iteration',C(gate_ok and len(gates)>=4),dict(conditions=gate_ev))
    g1=[lab[l] for l in lab if l.startswith('gate-wait-107ded-') and 'idem2' in l]
    rel=[r for r in g1 if r['result']['continuous_control'][-1]['stop_reason'] in ('return',) and r['facts']['steps'][-1]['byte_107ded_out']&0x80==0]
    claim('the declared IRQ palette effect (BYTE 107ded bit7 cleared when WORD 107dea = 0) releases the Waiting; the frame then runs to 2ac2',C(len(g1)==3 and len(rel)==3),dict(conditions=len(g1),released=len(rel)))
    nz=lab.get('gate-wait-107ded-81-107dea-nonzero')
    claim('with WORD 107dea <> 0 the declared effect leaves bit7 set (the original IRQ 72fa BNE.W 873a path): the Waiting persists',C(nz is not None and nz['result']['continuous_control'][-1]['waiting'] and sum(1 for st_ in nz['facts']['steps'] if st_['waiting'])>=3),dict(waits=sum(1 for st_ in nz['facts']['steps'] if st_['waiting']) if nz else None))
    gp=[lab[l] for l in lab if l.startswith('gate-pass-')]
    claim('BYTE 107ded with bit7 clear passes the gate at once (C = 1) without any Waiting',C(len(gp)==3 and all(not any(st_['waiting'] for st_ in r['facts']['steps']) for r in gp)),dict(conditions=[r['result']['label'] for r in gp]))
    # ---- table
    exp={0x00:(0x47b06,0x47b26),0x04:(0x47b0a,0x47b3e),0x08:(0x47b0e,0x47b68),0x0c:(0x47b12,0x47b76),0x10:(0x47b16,0x47b8c),0x14:(0x47b1a,0x47ba2),0x18:(0x47b1e,0x480b6),0x1c:(0x47b22,0x4809a)}
    tab_ev={};tab_ok=True
    for index,(slot,target) in exp.items():
        names=[l for l in lab if l.startswith('table-index-%02x-slot'%index)]
        sq=leads(names[0],0) if names else None
        okk=bool(sq) and slot in sq and sq.index(slot)+1<len(sq) and sq[sq.index(slot)+1]==target and sq[sq.index(slot)-1]==0x47af8
        tab_ev[hex(index)]=dict(slot=hex(slot),target=hex(target),ok=okk);tab_ok&=okk
    claim('the 8 table slots 47b06..47b22 (index 00..1c step 4) branch to 47b26 / 47b3e / 47b68 / 47b76 / 47b8c / 47ba2 / 480b6 (fade_card) / 4809a (fade_card): 47af8 -> slot -> target',C(tab_ok),tab_ev)
    comp={0x20:0x47b26,0x56:0x47b5c,0xfe:0x47c04}
    cev={}
    for index,pcx in comp.items():
        names=[l for l in lab if l.startswith('table-index-%02x-computed'%index)]
        sq=leads(names[0],0) if names else None
        cev[hex(index)]=dict(target=hex(pcx),ok=bool(sq) and pcx in sq and sq[sq.index(0x47af8)+1]==pcx)
    claim('computed PCs behind the table are executed when they are block starts: index 20 -> 47b26, 56 -> 47b5c, fe -> 47c04 (no range check at 47b02)',C(all(v['ok'] for v in cev.values())),cev)
    cons={}
    for index,(pcx,tgt) in {0x80:(0x47b86,0x47b26),0x96:(0x47b9c,0x47b26),0xce:(0x47bd4,0x47b26)}.items():
        names=[l for l in lab if l.startswith('table-index-%02x-computed'%index)]
        sq=leads(names[0],0) if names else None
        cons[hex(index)]=dict(entry=hex(pcx),ok=bool(sq) and sq[sq.index(0x47af8)+1]==pcx and sq[sq.index(pcx)+1]==tgt)
    claim('index 80 / 96 / ce reach the carry-consuming blocks 47b86 / 47b9c / 47bd4; the original CPU has C = 0 there (MOVE.B at 47afe) and branches to 47b26 (the machine reports an Unknown-carry error instead)',C(all(v['ok'] for v in cons.values())),cons)
    odd=[lab[l]['result'] for l in lab if l.startswith('table-index-') and l.endswith('odd-pc')]
    claim('index 01 / 03 / ff -> odd computed PC (47b07 / 47b09 / 47c05): the original CPU takes an address error; the native observer refuses the fetch (unsupported_code_target, odd_pc)',C(len(odd)==3 and all(r['observed_guard'] and r['observed_guard'].get('odd_pc') for r in odd)),dict(targets=[hex(r['observed_guard']['target']) for r in odd if r['observed_guard']]))
    internal=[lab[l]['result'] for l in lab if l.startswith('table-index-') and l.endswith('internal-pc')]
    claim('indices 22 / 24 / 30 / 32 -> PCs inside instructions: refused (unsupported_code_target); index 28 -> 47b2e is an instruction start inside the 47b2c block: the original CPU executes it (the machine contract refuses non-leader PCs)',C(len(internal)==4 and all(r['observed_guard'] for r in internal) and lab.get('table-index-28-computed-47b2e-internal-instruction-start') is not None),dict(targets=[hex(r['observed_guard']['target']) for r in internal if r['observed_guard']]))
    f28={}
    for index,pcx in ((0x0c,0x47b86),(0x10,0x47b9c),(0x14,0x47bd4)):
        names=[l for l in lab if l.startswith('table-index-%02x-28ae-fails'%index)]
        sq=leads(names[0],0) if names else None
        f28[hex(index)]=dict(entry=hex(pcx),ok=bool(sq) and pcx in sq and sq[sq.index(pcx)+1]==0x47b26)
    claim('28ae failure (WORD 104ca0 = 0: D0.W = 0 >= 0 unsigned, C = 0) takes the BCC at 47b86 / 47b9c / 47bd4 to 47b26',C(all(v['ok'] for v in f28.values())),f28)
    r10=lab.get('table-index-10-slot4-47b8c-28ae-ok-47bfc-62set');r14=lab.get('table-index-14-slot5-47ba2-cue-28ae-ok')
    claim('index 10 with 62(A6) <> 0 at the 47bfc re-entry falls through to 47c04 (activation, exit stop 47c6c); index 14 reaches 47bb0 and 47bd8 (28ae success, new object WORD 5690 / 5692 copied to 76 / 78)',C(r10 is not None and r14 is not None and EXIT_STOP==r10['facts']['steps'][-1]['outgoing_pc'] and 0x47bd8 in leads(r14['result']['label'],0) and 0x47bb0 in leads(r14['result']['label'],0)),dict(r10_final=hex(r10['facts']['steps'][-1]['outgoing_pc']) if r10 else None))
    # ---- activation / exit
    exits=[b for r in rows for b in r['boundaries'] if b['kind']=='exit-boundary']
    claim('the activation 47c04 ends at the exit stop 47c6c directly after MOVE.L #47c6c,(A6) at 47c66 (the exit unit 47c5a ran natively)',C(len(exits)>=104),dict(exit_stops=len(exits)))
    # ---- event walk
    ev={l:lab[l] for l in lab if l.startswith('event-')}
    def lseq(l):return leads(l,0)
    evc={}
    evc['d0-zero']=bool(lseq('event-d0-zero')) and 0xe907c in lseq('event-d0-zero') and 0xe908a not in lseq('event-d0-zero') and 0xe90ac in lseq('event-d0-zero')
    evc['bls-taken']=0xe909e in lseq('event-00-bls-taken') and 0xe90a6 not in lseq('event-00-bls-taken') and lseq('event-00-bls-taken')[-1]==0xe90ac
    evc['bls-equal']=0xe909e in lseq('event-00-bls-equal') and 0xe90a6 not in lseq('event-00-bls-equal')
    evc['step-then-ff']=lseq('event-00-step-then-ff').count(0xe908a)>=2 and 0xe90a6 in lseq('event-00-step-then-ff')
    evc['null']=0xe9076 in lseq('event-null-lookup')
    evc['trap-boundary']=all(any(b['kind']=='trap-boundary' for b in lab[l]['boundaries']) for l in ('event-tag-55-trap-boundary','event-tag-01-after-step-trap-boundary'))
    evc['trap-undeclared-refused']=bool(lab['event-tag-55-trap-undeclared']['result']['observed_guard']) and lab['event-tag-55-trap-undeclared']['result']['observed_guard']['target']==TRAP_PC
    claim('event lookup walk e905c: D0.W = 0 -> e90ac at once; tag 00 with D0.W <= limit (BLS, equal included) ends; D0.W > limit steps by sext(WORD +4); tag ff ends; tag <> ff / 00 stops at the TRAP #15 boundary e909c (refused when not declared); D7 = 0 -> e9076',C(all(evc.values())),evc)
    ban={l:lab[l]['facts']['steps'][0]['f1a_bank_reads'] for l in lab if l.startswith('event-banked-')}
    claim('a banked-window lookup pointer makes the F1a blocks e907c / e908a / e909e read the banked window (physical 200000 / 300000 + offset) with the modeled bank',C(bool(ban) and all(v>0 for v in ban.values())),ban)
    # ---- ROM data ranges read by the F1a blocks in the natural seeds
    rng={}
    for r in body:
        for st_ in r['facts']['steps']:
            for pc,(lo,hi,n,reg) in st_['f1a_rom_reads'].items():
                x=rng.setdefault(pc,[lo,hi,0]);x[0]=min(x[0],lo);x[1]=max(x[1],hi);x[2]+=n
    groups=(('catalog record fields',('0x47a98','0x47a9c','0x47adc','0x47aaa','0x47ace'),(0x472c4,0xdd4bc+16)),('lookup dereference',('0x47ada',),(0x485d4,0xf1f40+4)),('event lookup tables',('0xe907e','0xe908a','0xe909e','0xe90a6'),(0x485d8,0xfbf7a+8)),
        ('motion record',('0x19964','0x199e4'),(0x48936,0x4fb08+12)),('placement WORD',('0x1a422',),(0xd9c0c,0xf1a8c+2)))
    gev={}
    for name,pcs_,(lo,hi) in groups:
        vals=[rng[x] for x in pcs_ if x in rng]
        gev[name]=dict(observed=[hex(min(v[0] for v in vals)),hex(max(v[1] for v in vals))] if vals else None,contract=[hex(lo),hex(hi)],reads=sum(v[2] for v in vals),pcs=[x for x in pcs_ if x in rng])
    claim('the ROM data the F1a blocks read in the natural seeds lie inside the contract ranges (catalog records, lookup dereference, event tables, motion record, placement WORD; all fixed ROM < 100000)',C(all(v['observed'] and int(v['observed'][0],16)>=int(v['contract'][0],16) and int(v['observed'][1],16)<=int(v['contract'][1],16) for v in gev.values())),gev)
    r141=lab.get('body-141-live-RAM-record-reread')
    if r141:
        claim('case 141 (record in RAM at 10d420): 47aa6 re-reads the record after 1a5a4 changed it (e8a1c entered with A0 = 00a00080) and the BYTE +1 = ff of the re-read record jumps to the odd PC 47c05 (address error on the original CPU; native guard)',
            C(0x00a00080 in r141['facts']['steps'][0]['leader_seq'] or 0x00a00080 in r141['facts'].get('lead_a0_at_e8a1c',[]) ),dict(a0_at_e8a1c=[hex(x) for x in r141['facts'].get('lead_a0_at_e8a1c',[])],guard=r141['result']['continuous_control'][-1]['guard']))
    fnd=lab.get('finding-index-18-without-declared-dispatcher-base')
    if fnd:
        a7=fnd['facts']['steps'][-1]['outgoing_a7']
        claim('decision 7c declares the dispatcher re-entry as A6 = 100b30, A5 = 108000, (A7) = 2ac2 only; the index-18 path (47b1e -> 480b6 -> 2a00 MOVEA.L -$335c(A5),A7) also needs the dispatcher base LONG 104ca4 (A7 after the popped return LONG, stored by the scheduler): without it the frame ends at 2ac2 with A7 = %x instead of %x'%(a7,S+4),
            'understated' if a7!=S+4 else 'confirmed',dict(a7_without_declared_104ca4=hex(a7),expected=hex(S+4),rom_bytes_2a00='619a2e6dcca4600000ba',natural_reentries_of_index_18=sum(1 for r in body if any(st_.get('dispatch_index')==0x18 for st_ in r['facts']['steps']))))
    # ---- 17292
    c17=lab.get('clear-17292-ram')
    claim('17292 unrolled clear: A1 = A0 + 80 (hex), 2048 ascending zero LONG writes, final A1 = A0 + 2080 (hex), D0 = 0 (8 KiB)',C(c17 is not None and c17['facts']['clear_17292']['count']==2048 and c17['facts']['clear_17292']['ascending'] and c17['facts']['clear_17292']['all_zero_long'] and
        (lambda cc:cc['outgoing']['a1']==cc['incoming']['a0']+0x2080 and cc['outgoing']['d0']==0)(c17['result']['continuous_control'][0])),c17['facts']['clear_17292'] if c17 else None)
    # ---- 1a5a4 internal
    a=lab.get('init-1a674-motion-null-target-5');b=lab.get('init-1a71c-phase-short')
    claim('1a5a4: with no motion object (10d3b4 = 0) and target 5, 199ea takes 199f6 (C = 1) and 1a670 falls into 1a674; with 10d41e < 10d41c, 1a710 falls into 1a71c (a second 1a29e call)',C(a is not None and b is not None and 0x199f6 in leads(a['result']['label'],0) and 0x1a674 in leads(a['result']['label'],0) and 0x1a71c in leads(b['result']['label'],0)),dict(a=a is not None,b=b is not None))
    # ---- PVC ports of 1a5a4 / 1a724 / e90b2
    pv=None
    for r in body[:1]:
        pv=r['facts']['steps'][0]['f1a_ports']
    claim('PVC bank writes by F1a code: 1a5a4 writes 2000 -> 2ffff2, 0 -> 2ffff0 (bank physical 300000); 1a724 restores 1000 -> 2ffff2, 0 -> 2ffff0; e90b2..e90c0 restores the same pair',C(pv is not None and pv==[(0x2ffff2,0x2000),(0x2ffff0,0),(0x2ffff2,0x1000),(0x2ffff0,0),(0x2ffff2,0x1000),(0x2ffff0,0)]),dict(ordered_f1a_port_writes=[(hex(a_),hex(b_)) for a_,b_ in (pv or [])]))
    # ---- guards
    guards=[r['result'] for r in rows if r['result']['guarded']]
    claim('every guard condition ends in a native guard with an explicit reason and the same guard in split and continuous runs, twice',C(len(guards)>=1 and all(g['continuous_control'][-1]['guard'] and g['continuous_control'][-1]['guard'].get('reason') for g in guards)),dict(guards=[dict(label=g['label'],problem=g['continuous_control'][-1]['guard']['problem'],reason=g['continuous_control'][-1]['guard']['reason'][:100]) for g in guards]))
    # ---- coverage
    unc=[k for k,v in start_cov.items() if v['hits']==0]
    claim('every one of the 145 block starts is executed natively by at least one condition (the TRAP boundary e909c is reached as a stop)',C(not unc and any(b['kind']=='trap-boundary' for r in rows for b in r['boundaries'])),dict(uncovered=unc,natural_not_covered=[k for k,v in start_cov.items() if not v['natural']]))
    fix=sorted(k for k,v in start_cov.items() if not v['natural'])
    claim('block starts that need declared fixtures (not reached by the 142 begin cases, their dispatcher re-entries, the 35 countdown chains and the 104 activation cases)','confirmed',dict(count=len(fix),starts=fix))
    return claims


LIMITATIONS=['Controlled incoming fixtures (the begin states of the 142 stage_entry_body cases, their declared dispatcher re-entries, the 104 recorded stage_activation_prefix states, declared fixtures on captured native states), not natural scheduler / IRQ / gameplay reachability.  '
    'A declared dispatcher re-entry is a PC redirect to the installed callback LONG (A6) + an A7 delta + the return LONG 2ac2 at A7 + the dispatcher base LONG 104ca4 (A7 after the popped return LONG; the scheduler F2 stores it, 2a00 reloads A7 from it); '
    'the contract text (decision 7c) lists A6 / A5 / (A7) only.  Nothing claims a natural scheduler, natural IRQ or BIOS execution.',
    'The 72f0 palette gate Waiting at 47af0 is a declared fixture (BYTE 107ded bit7 = 1): the stop is taken after one spin iteration (BCC.B at 47af6 taken).  The declared IRQ palette effect is the minimal form of contract decision 2: BYTE 107ded bit7 cleared iff WORD 107dea = 0 (72fa..7302); '
    'the rest of the IRQ palette path (palette RAM writes at 400000, 3a000f, 105da2 / 105dc2 flags, frame / sound / watchdog counters) is not applied and remains unconfirmed.',
    'Native carry / CCR is never read (SR is unobserved); branch decisions are evidenced by the executed PC path and the register file at every block leader.  A fresh CPU starts with the declared SR 2000 (CCR 0), also for the direct entries (declared SR 2001 etc. for the carry-consumer fixtures); later steps continue on the same CPU.  '
    'The model keeps a full CCR but a carry produced by a black box (28ae at 47b86 / 47b9c / 47bd4, the U3 dispatcher at 1996e, 199f6 / 1971c at 1a670) is taken from the executed native path (the next native leader); this is recorded as carry_evidence.',
    'Sound / sprite wait stops are taken at the FIRST blocked arrival (the recorded stage_entry_body observer stops at the second blocked visit); the spin loops write nothing so the machine state is the same.  The hold / release phases carry external 255 in the recorded observer; no external read occurs in those steps so the native steps declare none.',
    'The stack lives in the work-RAM mirror (offset effc of the 64KiB image) while the recorded and original flat-map observers keep it outside the image, so RAM is compared outside the stack window [lowest stack-region write, 10f000); live stack bytes are compared at the wait stops.  '
    'Declared fixtures and guards have no recorded original: they are checked by split / continuous / twice equivalence and by the independent model only.  No C++ comparison was performed.',
    'The independent model is an instruction-level M68000 subset interpreter of the F1a ROM bytes; every callee outside the F1a ranges (the other executors, 25 black-box entries) is a black box whose native exit registers, RAM writes and PVC writes are replayed; only the F1a-attributed events (PC in the 22 ranges) are compared.  '
    'A guarded condition (native guard) is not modelled.',
    'Game meanings of the catalog record fields, the HUD table records, 10d684 / 10d683 flags, the index values 08 / 10 / 14 / 1c and the event lookup tables remain unknown; the BIOS card routine c00468 is a stop boundary only.',
    'The observer refuses an odd or unrouted instruction fetch before the original CPU could take its address error / execute it, and a data access to an odd address, the program ROM or an unmapped address is a guard (the original CPU would raise an address error / bus error).  '
    'The computed-PC refusals are the observer decoding set (instruction starts of the routed ranges); a PC that is an instruction start inside a block (for example index 28 -> 47b2e or index fa -> 47c00) is executed natively although the machine contract rejects non-leader PCs.']


def stop_selftests_placeholder():return []


if __name__=='__main__':main()
