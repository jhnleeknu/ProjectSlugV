"""Object callback group G2 (F4 units U17, U18, U19, U20a, U20b, N01) native observation.

Native Unicorn M68000 observation of the original ROM (never modified; write protected in the model).  Nothing here claims BIOS execution, a natural IRQ or a natural scheduler:
the frame passes of artifacts/animation_machine_scheduler_native (base, 120 frames) and artifacts/animation_machine_scheduler_rng_native (RNG initialised by the original 49a1a,
400 frames, bios-card answer 80 and the 00 variants) are DECLARED MODELS re-used in-process from tools/observe_animation_machine_scheduler.py and
tools/observe_animation_machine_scheduler_rng.py (not edited), and every typed fixture is a DECLARED state (a captured natural state plus a recorded list of register / RAM / SR edits).

The observer is independent of the C++ executors (engine/src/animation_machine_objects_*.cpp) and of the core workers' scratch fixture generators; the unit block lists, code ranges and
carry classifications come from the six pinned contracts docs/analysis/animation-machine-objects-{u17,u18,u19,u20,u20b,n01}-contract.md (U20 = the U20a part: the three code ranges of its
"원본 바이트 근거" table).  The generic machinery (independent M68000 subset model, fresh-CPU flows, coverage guided fixture search) is imported from
tools/observe_animation_machine_objects_g1.py (not edited); only the unit configuration, the contract parser, the natural stage over BOTH natural records, the group specific typed
fixtures (jump table 44ade, carry consumers / producers, bank sweeps, guards) and the report are written here.

PVC banks.  The scheduler Machine is replaced (in-process, by import of tools/observe_animation_machine_pvc_banks.py) by PvcMachine: every bank the MAME formula can produce is a state,
a read of the banked window past the 8 MiB image is the only bank guard (bank-read-outside-rom).  The independent model uses the same formula (address_map.pvc_bank_update) and guard.

Natural evidence.  Every node (of the 142 base seeds x 120 frames, the 142 RNG seeds x 400 frames and the 6 RNG answer-00 variants) that executed at least one instruction inside a G2
code range is replayed natively from its recorded entry state (PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd; write protected ROM; the scheduler's RNG / bank guards) on a FRESH CPU:
reference (one run, no pause), continuous (one CPU, paused at every piece boundary) and split (a fresh CPU rebuilt from the captured boundary state at every piece boundary; a sample
that includes the first node of every distinct callback / block path).  A piece is a maximal run of instructions that stay in one unit (or outside all units: a black box callee).
Entry / exit digests, ordered block-leader traces, exits and guards are recorded; the recorded scheduler exit digest must be reproduced.

Independent model.  The G1 Python M68000 subset interpreter (written from the programmer's reference by instruction format; shares no code with Unicorn, capstone, the C++ or the
scheduler observer) runs every unit piece from the native piece-start state and is compared with the native piece: per instruction PC + 16 registers (sampled nodes: PC), ordered data
reads and writes, ports, final RAM / registers, final CCR at the piece boundary (read exactly with a MOVE SR,D0 probe; the plain Unicorn SR is stale), guards.

Typed fixtures.  Every contract block start that no natural node reaches gets a declared fixture (coverage guided search over a captured natural state, recorded as a minimized edit
list; direct entry only as the last resort and flagged "entry-self"); the fixtures also cover the contract minimum conditions: the 44ade jump table (all 96 indexes), carry consumers
with a declared CCR (the branch outcome of the native run is the evidence, never the Unicorn SR), producer -> consumer chains through real producers, PVC bank sweeps of every
bank-window block, odd / ROM-write / unmapped / bank guards.  Fixtures run reference / continuous / split, twice each.
"""
import argparse
import collections
import copy
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_objects_g1 as G1      # generic machinery; never edited here (imports the scheduler observer S and the PVC bank machine)
import observe_animation_machine_scheduler as S
import observe_animation_machine_scheduler_rng as R
import observe_animation_machine_pvc_banks as PB       # replaces S.Machine by PvcMachine (any PVC-selectable bank)
import unicorn
from unicorn import UC_HOOK_CODE
from address_map import pvc_bank_update

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_objects_g2_native'
ROM_SHA=S.ROM_SHA
CONTRACT_DIR=ROOT/'docs/analysis'
SCHED_DIR=ROOT/'artifacts/animation_machine_scheduler_native'
RNG_DIR=ROOT/'artifacts/animation_machine_scheduler_rng_native'
M32=0xffffffff
KEYS=S.KEYS
UC_REG=S.UC_REG
SPD=S.SPD
PASS_PC=S.PASS_PC
hx=S.hx
sha=S.sha
GLOBAL=G1.GLOBAL
sjson=G1.sjson

# unit id (byte value of the unit map) -> name, contract file, pinned contract SHA256, expected counts (summary of the contract itself)
UNITS=collections.OrderedDict([
    (17,dict(name='U17',file='u17',sha='e91a946220814dd7d025a3147cc12561db36c6078cb81fe904afc62c878d2894',starts=109,insns=252,ranges=9,bytes=1186,even=593)),
    (18,dict(name='U18',file='u18',sha='ee88bd6cb3834a7ec9b1040d6fd984ee92fc2b81a7d8aae9460bef070830f3b7',starts=158,insns=365,ranges=13,bytes=1568,even=784)),
    (19,dict(name='U19',file='u19',sha='f7ac9c28c24a42c450ceb36edddf33a1393c9b1cf94f9bc9072a028c7bbf8ca3',starts=174,insns=460,ranges=11,bytes=2144,even=1072)),
    (20,dict(name='U20a',file='u20',sha='c4000688b7a02546b6ff0202d872af61c5c52632678390fef8ff794be1594cb0',starts=177,insns=504,ranges=3,bytes=1712,even=856)),
    (21,dict(name='U20b',file='u20b',sha='d0aa57cf84335ab0b89f67daab204125e64d80a1400e47d6895c6629e12f3827',starts=92,insns=186,ranges=3,bytes=944,even=472)),
    (22,dict(name='N01',file='n01',sha='f9aecd66299a1533c23e278fa2b33059821e07306982eb881ddc789177f3523c',starts=74,insns=273,ranges=3,bytes=1210,even=605))])
UIDS=tuple(UNITS)
NAMES={u:UNITS[u]['name'] for u in UNITS}
# boundary PCs named by the contracts that no G2 code range contains.  kind: callee (a JSR / BSR target without executor in the F4 line), written (an installed callback / child
# callback body that the unit only writes into the node and never executes)
BOUNDARY_NAMED={17:dict(written=(0xbc08c,)),
    18:dict(callee=(0x4970a,0xb7dd6),written=(0xb67b2,0xb6ba0,0xb7742,0xea85a,0xeaa00,0xd1f68)),
    19:dict(callee=(0xb7b30,0xd83c0,0xe9112),written=(0xb7100,0xb749c,0x4841a)),
    20:dict(),21:dict(written=(0x85c6c,)),22:dict()}
# G2 stage invariants of the contracts: expected number of sentinel hand fixtures etc. are produced from the code, not hard coded.


# ----------------------------------------------------------------------------------
# Contracts: code ranges, block starts, carry classification lists (pinned)
# ----------------------------------------------------------------------------------
def contract_path(u):return CONTRACT_DIR/('animation-machine-objects-%s-contract.md'%UNITS[u]['file'])


def hexes(s):return [int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`',s)]


def section(t,head,nxt=None):
    i=t.index(head);j=t.index('\n## ',i+5) if nxt is None else t.index(nxt,i+5)
    return t[i:j]


def parse_ranges(t):
    sec=section(t,'## 원본 바이트 근거');rows=[];started=False
    for ln in sec.splitlines():
        m=re.match(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| ([0-9,]+) \| `([0-9a-f]{64})` \|',ln)
        if m:started=True;rows.append((int(m.group(1),16),int(m.group(2),16),int(m.group(3).replace(',','')),m.group(4)))
        elif started and not ln.startswith('|'):break
    return rows


def parse_starts(u,t):
    """Block starts listed by the contract (the block list section).  Returns (starts, notes).  Compressed lines of the contract are expanded here."""
    sec=section(t,'## block 목록');out=[];notes=[]
    toks=re.findall(r'(?:^- |/ |; |^\| |\*\* )`([0-9a-f]{3,6})`(?: \([^)]*\))?:',sec,re.M)
    out.extend(int(x,16) for x in toks)
    if u==18:
        m=re.search(r'^- `([0-9a-f]+)`~`([0-9a-f]+)` 6:[^\n]*\(([^;)]*);',sec,re.M)
        assert m,'U18 compressed 46cbe line not found'
        out.extend(hexes(m.group(3)));notes.append('U18 46cbe..46cfa expanded from the contract parenthesis')
    if u==20:
        base=0x44ae2
        for k in range(0x60):out.append(base+4*k)
        notes.append('44ae2+4k (k=0..5f) = 96 table entries')
        for ln in sec.splitlines():
            if ln.startswith('|') and not ln.startswith('| ---') and not ln.startswith('| 진입') and not ln.startswith('| 머리'):
                cells=[c.strip() for c in ln.strip().strip('|').split('|')]
                m=re.match(r'^`([0-9a-f]{5})`$',cells[0])
                if m:
                    out.append(int(m.group(1),16))
                    if len(cells)>=7:                               # range head / tail table: head | k | lim | branch | tail | shift | combine
                        m2=re.match(r'^`([0-9a-f]{5})`$',cells[4])
                        if m2:out.append(int(m2.group(1),16))
        notes.append('slope leaves, range heads and tails from the two U20a tables')
    return out,notes


def parse_lists(u,t):
    """Carry classification lists of the contract: flow-only, producers (Clear / Set), consumers.  Returns dict with the parsed lists and the stated counts."""
    sec=section(t,'## 구현 범위와 규약');res=dict(flow=None,flow_n=None,producers={},producers_n=None,consumers=None,consumers_n=None)
    m=re.search(r'^- \*\*FLOW_ONLY (\d+)개\*\*[^\n]*',sec,re.M)
    if m:res['flow_n']=int(m.group(1));res['flow']=hexes(re.sub(r'\([^)`]*\)','',m.group(0)))
    if u==20:                                                       # "44ade(JMP), 표 entry 96(BRA.W), 492d0, 497b4"
        res['flow']=[0x44ade]+[0x44ae2+4*k for k in range(0x60)]+[0x492d0,0x497b4]
    m=re.search(r'^- \*\*known carry 생산[^\n]*',sec,re.M)
    if m:
        line=m.group(0);mn=re.search(r'생산 (\d+)개',line);res['producers_n']=int(mn.group(1)) if mn else 0
        head=line.split('. ')[0]
        for seg in re.split(r', ',head):
            ws=re.findall(r'(Clear|Set)',seg)
            if ws:
                w=ws[-1]
                for p in hexes(seg):res['producers'][p]=w
        if res['producers_n']==0 and 'known carry 생산 0개' in line:res['producers']={}
    # consumers: summary line "C 소비 block **N개**: `pc BCC` ..." (parenthesised references removed; spans that start with a hex pc)
    summ=section(t,'## 요약')
    m=re.search(r'C 소비 block \**(\d+)개\**[^\n]*',summ)
    if m:
        res['consumers_n']=int(m.group(1));line=m.group(0);line=line[line.index(':',line.index('개')):] if ':' in line[line.index('개'):] else line
        line=re.sub(r'\([^)]*\)','',line)
        res['consumers']=[int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})(?: [^`]*)?`',line)]
    elif u==20:res['consumers_n']=0;res['consumers']=[]
    elif u==22:
        m=re.search(r'carry\*\*: 소비 block (\d+)개 `([0-9a-f]+)` `([0-9a-f]+)`',summ);res['consumers_n']=int(m.group(1));res['consumers']=[int(m.group(2),16),int(m.group(3),16)]
    if u==18 and res['consumers']:
        res['flow']=sorted(set(res['flow'])|set(res['consumers']))             # "FLOW_ONLY 69 = 41 + 14 + the 14 consumers"
    return res


def parse_contract2(u,program):
    p=contract_path(u);data=p.read_bytes();cfg=UNITS[u]
    assert sha(data)==cfg['sha'],('contract changed',cfg['name'],sha(data))
    t=data.decode('utf-8');rows=parse_ranges(t)
    assert len(rows)==cfg['ranges'],(cfg['name'],len(rows))
    for a,b,n,h in rows:
        assert b-a==n and sha(program[a:b])==h,(cfg['name'],hex(a),hex(b))
    ranges=[(a,b) for a,b,_,_ in rows];total=sum(b-a for a,b in ranges)
    m=re.search(r'합계 ([\d,]+)바이트[^`]*`([0-9a-f]{64})`',t);assert int(m.group(1).replace(',',''))==total==cfg['bytes']
    assert sha(b''.join(program[a:b] for a,b in ranges))==m.group(2),cfg['name']
    starts,notes=parse_starts(u,t)
    dup=sorted({x for x in starts if starts.count(x)>1})
    lists=parse_lists(u,t)
    ex=re.search(r'\[F\] (\d+) block',section(t,'## block 목록'))
    return dict(unit=u,name=cfg['name'],sha=cfg['sha'],ranges=ranges,bytes=total,starts=sorted(set(starts)),parsed_starts=len(starts),duplicates=dup,notes=notes,lists=lists,
        stated_blocks=int(ex.group(1)) if ex else None,text=t)


class Env2(G1.Env):
    """G1.Env over the six G2 contracts (unit ids 17..22).  The interface used by the generic machinery: program, fixed, contracts, unit, starts, traps, boundary, range_list, unit_of."""
    def __init__(self):
        self.program=S.load_rom();self.fixed=(G1.ctypes.c_ubyte*0x100000).from_buffer_copy(self.program[:0x100000])
        self.contracts={u:parse_contract2(u,self.program) for u in UIDS}
        self.unit=bytearray(0x80000);self.starts={};self.traps={};self.range_of={}
        for u,c in self.contracts.items():
            c['merged']=[]
            for lo,hi in c['ranges']:
                for pc in range(lo,hi,2):
                    assert self.unit[pc>>1]==0,hex(pc)
                    self.unit[pc>>1]=u
            for pc in c['starts']:
                assert any(lo<=pc<hi for lo,hi in c['ranges']),(u,hex(pc))
                self.starts[pc]=u
            c['traps']=[]
        self.boundary={}
        self.range_list=sorted((lo,hi,u) for u,c in self.contracts.items() for lo,hi in c['ranges'])
        for u,d in BOUNDARY_NAMED.items():
            for pc in d.get('callee',()):
                assert self.unit_of(pc)==0,hex(pc);self.boundary[pc]=u


# ----------------------------------------------------------------------------------
# Natural stage over both natural records
# ----------------------------------------------------------------------------------
NAT_LIMIT=G1.NAT_LIMIT
BASE_FRAMES=S.FRAMES_BASE
RNG_FRAMES=R.FRAMES
CASE_BASE=0                      # case ids: base seeds 0..141, RNG seeds 1000+seed (answer 80), RNG answer-00 variants 2000+seed
CASE_RNG=1000
CASE_RNG00=2000
RNG00_SEEDS=(0,1,2,3,4,5)
RNG_ROUTING_REF='88833c9bdf66e3c3477a99e63f0b9f8c79e2e7bc'


class UnitMixin(object):
    """Passive code hook on the unit ranges: every node that executed unit code is handed to `node_task` (same contract as G1.G1Run, cooperative super())."""
    def __init__(self,*a,**k):
        super(UnitMixin,self).__init__(*a,**k);self.node_task=None;self.unit_nodes=0;self.node_rows=[];self.ipcs=set();self.case_id=None
    def build(self,snap):
        mach=super(UnitMixin,self).build(snap);env=GLOBAL['env']
        for lo,hi,u in env.range_list:mach.cpu.hook_add(UC_HOOK_CODE,self.h_unit,begin=lo,end=hi-1)
        return mach
    def h_unit(self,uc,pc,size,user):
        n=self.cur
        if n is None:return
        h=n.get('hits')
        if h is None:h=n['hits']={}
        if pc in GLOBAL['env'].starts:h[pc]=h.get(pc,0)+1
        n['unit']=True
    def finish_node(self,node,exit_state,partial):
        super(UnitMixin,self).finish_node(node,exit_state,partial)
        if node.get('unit'):
            self.unit_nodes+=1
            self.node_rows.append(self.node_task(self,node,exit_state,partial))


class BaseRun(UnitMixin,S.SeedRun):pass
class RngRun(UnitMixin,R.RngRun):pass


def case_info(case):
    if case<CASE_RNG:return 'base',case,None
    if case<CASE_RNG00:return 'rng',case-CASE_RNG,R.DEFAULT_ANSWER
    return 'rng00',case-CASE_RNG00,R.VARIANT_ANSWER


def setup_sched():
    """Scheduler / RNG tool setup WITHOUT the routing source parse: the routing bitmaps only feed coverage flags (and the 120 -> 400 extension rule, which is replaced by the frame
    counts of the recorded artifact), never the executed trajectory.  The recorded artifacts' pass-end digests are compared instead (see natural_check)."""
    program=S.load_rom();S.G['program']=program;fixed=(G1.ctypes.c_ubyte*0x100000).from_buffer_copy(program[:0x100000]);S.G['fixed']=fixed
    f3a,f3b,traps,_,_=S.f3_contract_lists()
    ones=bytes([1])*0x80000;levels=dict(A=ones,B=ones,f3a_starts=f3a,f3b_starts=f3b,traps=traps)
    S.G['levels']=levels
    S.LEAD_SET=frozenset(S.F2_LEADERS)|frozenset(f3a)|frozenset(f3b);S.TRAP_SET=frozenset(traps)
    R.G['program']=program;R.G['fixed']=fixed;R.G['levels']=R.make_levels(ones)
    S.load_seeds()
    return program


def load_records():
    """Recorded natural artifacts (read only): per case frames / stop / last pass-end digests and callback counts per seed."""
    base=json.loads((SCHED_DIR/'observation.json').read_text());rng=json.loads((RNG_DIR/'observation.json').read_text())
    rec=dict(base={x['case']:x for x in base['seeds']},rng={x['case']:x for x in rng['seeds']},rng00={x['case']:x for x in rng['variants_answer00']},
        base_sha=sha((SCHED_DIR/'observation.json').read_bytes()),rng_sha=sha((RNG_DIR/'observation.json').read_bytes()))
    return rec


def make_run(case):
    """(run object, sd, meta, prep record or None) for a case id."""
    kind,seed,ans=case_info(case)
    if kind=='base':
        sd=S.SEEDS[seed];snap,meta=S.seed_snap(sd);frames=GLOBAL['records']['base'][seed]['frames_done']
        frames=S.FRAMES_FULL if frames>BASE_FRAMES else BASE_FRAMES                  # the scheduler rule extends 120 -> 400 frames when every pass was covered; the recorded frame count decides
        run=BaseRun(GLOBAL['program'],S.G['fixed'],S.G['levels'],snap,'continuous',frames,heavy=False,sink=None,extend=False);return run,sd,meta,None
    sd,snap0,meta,prep,carried=R.prepared(seed)
    snap={k:v for k,v in carried.items() if k!='prep_entry_state'}
    run=RngRun(R.G['program'],R.G['fixed'],R.G['levels'],snap,'continuous',RNG_FRAMES,heavy=False,sink=None,extend=False,answer=ans);return run,sd,meta,prep


def case_list():
    return [CASE_BASE+c for c in sorted(S.SEEDS)]+[CASE_RNG+c for c in sorted(S.SEEDS)]+[CASE_RNG00+c for c in RNG00_SEEDS]


def pass_a_task(case):
    """Cheap pass: which nodes execute which unit block starts (no replay)."""
    run,sd,meta,prep=make_run(case)
    run.node_task=lambda r,node,ex,partial:(r.frame,node['seq'],node['cb'],sorted(node.get('hits',{})),bool(partial))
    run.run()
    return dict(case=case,kind=sd['kind'],stop=run.stop,frames_done=run.frames_done,cb=dict(run.cb_counts),unit_nodes=run.unit_nodes,nodes=run.node_rows)


def write_blob(data):return G1.write_blob(data)
dump_state=G1.dump_state


def consumer_pairs(env,leaders):
    """Native branch outcomes of the carry consumers in an ordered leader sequence: key 'cons>next' and,
    'prod>cons>next' when one of the contract's known producers ran in the previous 2 leaders (the producer -> consumer chain through a REAL producer; the exact C is then the producer's)."""
    out=collections.Counter();cons=env.consumers;prods=env.producers
    for i,pc in enumerate(leaders):
        if pc in cons:
            nxt='%x'%leaders[i+1] if i+1<len(leaders) else '-'
            out['%x>%s'%(pc,nxt)]+=1
            for j in range(i-1,max(-1,i-3),-1):                    # the consumer is the return point of the producer's function: at most one block (RTS) in between
                if leaders[j] in prods:out['p%x>%x>%s'%(leaders[j],pc,nxt)]+=1;break
    return out


def process_node(run,node,exit_state,partial):
    env=GLOBAL['env'];plan=GLOBAL['plan'].get((run.case_id,run.frame,node['seq']))
    entry=dict(ram=node['entry_ram'],regs=dict(node['entry_regs']),pc=0x2ab8,bank=tuple(node['entry_bank']),ccr=0)
    sample=bool(plan and plan.get('sample'))
    split=sample or (run.frame*7+node['seq'])%4==0
    twice=sample or (run.frame*131+node['seq'])%8==0
    res,f,models=G1.node_replay(env,entry,(PASS_PC,),NAT_LIMIT,twice and split,node['exit_digest'],True,split)
    c=f['cont']
    run.ipcs.update(x[0] for p in c.pieces for x in p['trace'])
    hits=node.get('hits',{});run_hits=sum(hits.values())
    row=dict(frame=run.frame,seq=node['seq'],a6=node['a6'],cb=node['cb'],depth=node['depth'],partial=bool(partial),split=split,twice=twice,entry=node['entry_digest'],exit=node['exit_digest'],
        pieces=res['pieces'],insns=res['insns'],eq=res['eq'],model_ok=res['model_ok'],sched_exit_eq=res.get('sched_exit_eq'),final=res['final'],guard=res['guard'],waits=res['waits'],
        bank=c.states[-1]['bank'][0],banks_seen=sorted({s['bank'][0] for s in c.states}|set(G1.pvc_banks_of(c))),bank_changes=sum(1 for p in c.pieces for x in p['ports'] if x[0]==1),
        leader_sha=sha(repr(res['leaders']).encode())[:16],leader_len=len(res['leaders']),run_hits=run_hits,hits_eq=(run_hits==len(res['leaders']) and sorted(hits)==sorted(set(res['leaders']))),
        succ=dict(consumer_pairs(env,res['leaders'])),config=sha(repr((node['cb'],sorted(hits))).encode())[:16])
    if not res['model_ok']:row['model_diffs']=res['model_diffs']
    first=[];seen=set()
    for pc in res['leaders']:
        if pc not in seen:seen.add(pc);first.append(pc)
    row['leaders_first']=first
    row['xfers']=[[p['unit'],p['trace'][-1][0] if p['trace'] else None,c.states[p['end']]['pc']] for p in c.pieces if p['unit']]
    if plan:
        row['captures']={}
        if plan.get('full'):
            row['dumps']=dict(entry=dump_state(entry),states=[dump_state(s) for s in c.states],exit=dump_state(c.states[-1]))
        for pc in plan.get('starts',()):
            fl=G1.Flow(env,entry,'ref',(pc,),NAT_LIMIT).run()
            if fl.final['kind']=='stop' and fl.final['detail']['pc']==pc:row['captures'][pc]=dump_state(fl.states[-1])
        if plan.get('entry'):row['entry_dump']=dump_state(entry)
    return row


def rec_of(case):
    kind,seed,ans=case_info(case);r=GLOBAL['records']
    return r['base'][seed] if kind=='base' else (r['rng'][seed] if kind=='rng' else r['rng00'][seed])


def recorded_cb_counts(case):
    """Callback counts of the recorded artifact's per-seed file (all passes) as {int callback: count}."""
    kind,seed,ans=case_info(case)
    path={'base':SCHED_DIR/'seeds'/('seed_%04d.json.gz'%seed),'rng':RNG_DIR/'seeds'/('seed_%04d.json.gz'%seed),'rng00':RNG_DIR/'variants_answer00'/('seed_%04d.json.gz'%seed)}[kind]
    doc=json.loads(gzip.decompress(path.read_bytes()));c=collections.Counter()
    for p in doc['passes']:
        for n in p['nodes']:c[n['cb']]+=1
    return dict(c)


def recorded_first_pass_cbs(case):
    kind,seed,ans=case_info(case)
    path={'base':SCHED_DIR/'seeds'/('seed_%04d.json.gz'%seed),'rng':RNG_DIR/'seeds'/('seed_%04d.json.gz'%seed),'rng00':RNG_DIR/'variants_answer00'/('seed_%04d.json.gz'%seed)}[kind]
    doc=json.loads(gzip.decompress(path.read_bytes()))
    return [n['cb'] for n in doc['passes'][0]['nodes']]


EXEMPT_CASES={58:'seed 58 (U06 seed, PVC bank 4/5): the recorded scheduler Machine stops in pass 0 (unsupported bank mapping); the PVC bank model of this observer runs on to the frame limit - only the recorded pass-0 prefix is compared',
    59:'seed 59 (U06 seed, PVC bank 4/5): same as seed 58'}


def pass_b_task(case):
    kind,seed,ans=case_info(case)
    run,sd,meta,prep=make_run(case);run.case_id=case;run.node_task=process_node;run.run()
    rr=rec_of(case);tail=[p['end'] for p in run.pass_records][-3:]
    mine0=[n['cb'] for n in run.pass_records[0]['nodes']]
    if kind=='base' and seed in EXEMPT_CASES:
        rec0=recorded_first_pass_cbs(case)
        check=dict(frames=(run.frames_done,rr['frames_done']),tail_eq=None,stop_eq=True,cb_eq=True,first_pass_prefix_eq=(mine0[:len(rec0)]==rec0),exempt=EXEMPT_CASES[seed])
        check['stop_eq']=check['cb_eq']=bool(check['first_pass_prefix_eq']);check['frames']=(1,1)
    else:
        check=dict(frames=(run.frames_done,rr['frames_done']),tail_eq=(tail==rr['pass_end_tail']) if 'pass_end_tail' in rr else None,
            stop_eq=run.stop.get('reason')==rr['stop'].get('reason') and run.stop.get('frame')==rr['stop'].get('frame'),cb_eq=recorded_cb_counts(case)==dict(run.cb_counts))
    return dict(case=case,record=kind,seed=seed,kind=sd['kind'],family=sd['family'],stop=run.stop,frames_done=run.frames_done,run_digest=run.digest.hexdigest(),cb=dict(run.cb_counts),
        unit_nodes=run.unit_nodes,nodes=run.node_rows,meta=meta,prep=(R.prep_summary(prep) if prep else None),ipcs=sorted(run.ipcs),waits=dict(run.waits_total),check=check)


def stage_natural(env,args,out_dir,cases):
    ctx=multiprocessing.get_context('fork')
    GLOBAL.update(plan={})
    with ctx.Pool(args.workers) as pool:a_list=pool.map(pass_a_task,cases,chunksize=1)
    plan=collections.defaultdict(lambda:dict(starts=[],full=False,entry=False,sample=False))
    first_start={};cb_nodes=collections.defaultdict(list);configs=set();used_seeds=collections.Counter();seed_cb={}
    for a in a_list:
        kind=case_info(a['case'])[0];seen_cb=set()
        for frame,seq,cb,hits,partial in a['nodes']:
            for pc in hits:
                if pc not in first_start:first_start[pc]=(a['case'],frame,seq)
            if len(cb_nodes[cb])<2:cb_nodes[cb].append((a['case'],frame,seq))
            cfg=(cb,tuple(hits))
            if cfg not in configs:configs.add(cfg);plan[(a['case'],frame,seq)]['sample']=True
            if a['kind']=='natural' and cb not in seen_cb and used_seeds[kind]<8:seen_cb.add(cb);cb_nodes.setdefault(('seed',a['case']),[]).append((a['case'],frame,seq))
        if a['kind']=='natural' and a['nodes'] and used_seeds[kind]<8:used_seeds[kind]+=1
    for pc,ref in sorted(first_start.items()):plan[ref]['starts'].append(pc)
    for k,v in cb_nodes.items():
        for ref in v:plan[ref]['full']=True;plan[ref]['entry']=True
    GLOBAL['plan']=dict(plan)
    with ctx.Pool(args.workers) as pool:b_list=pool.map(pass_b_task,cases,chunksize=1)
    return a_list,b_list,first_start


# ----------------------------------------------------------------------------------
# Static analysis of the contract blocks (decoder = the G1 model decoder; no capstone)
# ----------------------------------------------------------------------------------
Model=G1.Model


def new_model(env,ccr=None):
    return Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0,ccr=ccr)


def abs_bank_operands(ins):
    """Absolute addresses of an instruction that fall into the banked window 200000..2fdfff."""
    out=[]
    for ea in (ins.src,ins.dst):
        if ea and ea[0]=='abs' and 0x200000<=ea[1]<0x2fe000:out.append(ea[1])
    return out


def block_flag_analysis(env,cfg,s):
    """Independent-model flag experiment for one block: executes the block's own instructions from s with ALL flags unknown.  Returns dict(consumes=<flag named by the first
    MUnknownFlag or None>, c_written=<C is 0/1 after the block's straight line (None = untouched)>, ops=[...], indeterminate=<guard kind or None>).  Registers point into work RAM."""
    c=cfg[s];mdl=new_model(env);mdl.pc=s
    for i in range(8):mdl.r[8+i]=0x100400+0x40*i
    for i in range(8):mdl.r[i]=2*i+2
    mdl.r[15]=0x10f000;mdl.r[13]=0x108000;mdl.r[14]=0x100600
    res=dict(consumes=None,c_written=None,ops=[],indeterminate=None,mem=set());ndone=0
    for pc in c['insns']:
        if mdl.pc!=pc:break
        ins=mdl.decode(pc);res['ops'].append(ins.op)
        for ea in (ins.src,ins.dst):
            if ea:
                k=ea[0]
                if k in('ind','post','pre','d16','idx'):res['mem'].add((k,ea[1]))
        try:mdl.step();ndone+=1
        except G1.MUnknownFlag as e:res['consumes']=str(e);break
        except G1.MGuard as e:res['indeterminate']=e.kind;break
        except G1.MUnsupported as e:res['indeterminate']='unsupported:'+str(e);break
        if ins.op in ('rts','jsr','jmp','bsr','bra','bcc','dbcc'):break
    res['c_written']=mdl.cc['C'];res['flags_after']={k:v for k,v in mdl.cc.items()}
    return res


def analyze_units(env):
    """CFG, flag consumers (model), bank-window blocks, memory kinds, computed jumps per start."""
    cfg=G1.build_cfg(env);ana={}
    for s in sorted(env.starts):
        a=block_flag_analysis(env,cfg,s)
        mdl=new_model(env);bank=[];jsr28=False;calls=[];installs=[];ops=[]
        for pc in cfg[s]['insns']:
            ins=mdl.decode(pc);bank+=abs_bank_operands(ins);ops.append(ins.op)
            if ins.op in('jsr','bsr') and ins.src is None and ins.target is not None:calls.append(ins.target)
            if ins.op=='jsr' and ins.src[0] in ('abs','pcd16'):
                calls.append(ins.src[1])
                if ins.src[1]==0x28ae:jsr28=True
            if ins.op=='move' and ins.size==4 and ins.src[0]=='imm' and ins.dst==('ind',6):installs.append(ins.src[1])
        children=[]
        ext=set()
        u0=env.starts[s];own=env.contracts[u0]['ranges']
        mdl2=new_model(env)
        for pc in cfg[s]['insns']:
            ins=mdl2.decode(pc)
            if ins.op=='movea' and ins.size==4 and ins.src[0]=='imm' and ins.dst==('an',0):children.append(ins.src[1])
            tg=None
            if ins.op in('bra','bsr','bcc','dbcc'):tg=ins.target
            elif ins.op in('jsr','jmp') and ins.src[0] in('abs','pcd16'):tg=ins.src[1]
            if tg is not None and not any(lo<=tg<hi for lo,hi in own):ext.add(tg)
        a.update(bank=bank,calls=calls,installs=installs,children=children,external=sorted(ext),jsr28ae=jsr28,unit=env.starts[s],nins=len(cfg[s]['insns']),last=cfg[s]['insns'][-1])
        ana[s]=a
    env.cfg=cfg;env.ana=ana
    mdl0=new_model(env);env.cfg_all_ins={u:{} for u in UIDS}
    for u,c in env.contracts.items():
        for lo,hi in c['ranges']:
            pc=lo
            while pc<hi:
                ins=mdl0.decode(pc);env.cfg_all_ins[u][pc]=ins.op;pc+=ins.len
    contract_cons={s for c in env.contracts.values() for s in (c['lists']['consumers'] or [])}
    model_cons={s for s,a in ana.items() if a['consumes']=='C'}
    env.consumers=contract_cons|model_cons
    env.producers={s for c in env.contracts.values() for s in c['lists']['producers']}
    env.model_consumers=model_cons;env.contract_consumers=contract_cons
    return ana


# ----------------------------------------------------------------------------------
# Fixture machinery (declared states = captured natural state + recorded edits)
# ----------------------------------------------------------------------------------
STACK_TOP=SPD-4                                          # declared re-entry form: A7 = SPd-4, LONG (A7) = 2ac2 (the dispatcher JSR return)


def cand_json2(c):
    d=G1.cand_json(c)
    if 'bank' in c:d['bank']=[G1.hx(c['bank'][0]),G1.hx(c['bank'][1]),G1.hx(c['bank'][2])]
    if c.get('a6fn'):d['a6_family']=c['a6fn']
    if c.get('a7odd'):d['a7_odd']=True
    if c.get('copy'):d['copy']=[[rn,o,sz,sr,sh] for rn,o,sz,sr,sh in c['copy']]
    if c.get('mem'):d['mem']=[[rn,o,sz,G1.hx(v)] for rn,o,sz,v in c['mem']]
    if c.get('a6mem'):d['a6_mem']=[[G1.hx(o),sz,G1.hx(v)] for o,sz,v in c['a6mem']]
    return d


def apply_cand2(origin,cand):
    st=G1.apply_cand(origin,cand)
    if 'bank' in cand:st['bank']=tuple(cand['bank'])
    return st


def entry_cand(target,regs=None,ram=None,ccr=0,bank=None):
    """Declared node-level entry at `target`: the origin must be a node entry dump (PC 2ab8); A7 := SPd-4 with LONG 2ac2 on the stack (the F2 re-entry protocol of the frame pass)."""
    r={'a7':STACK_TOP};r.update(regs or {})
    m={(STACK_TOP&0xffff)+i:b for i,b in enumerate(PASS_PC.to_bytes(4,'big'))};m.update(ram or {})
    c=dict(regs=r,ram=m,ccr=ccr,pc=target)
    if bank is not None:c['bank']=bank
    return c


def apply_post(st,post):
    post=dict(post);regs=dict(post.get('regs') or {})
    if post.get('a6fn'):regs['a6']=dict((n,fn) for n,gk,fn in GUARD_FAMILIES)[post['a6fn']](st['regs']['a6'])
    if post.get('a7odd'):regs['a7']=st['regs']['a7']|1
    post['regs']=regs
    st=apply_cand2(st,post)
    if post.get('a6mem'):
        ram=bytearray(st['ram']);a6=st['regs']['a6']
        for off,size,val in post['a6mem']:
            for i,b in enumerate((val&((1<<(8*size))-1)).to_bytes(size,'big')):ram[(a6+off+i)&0xffff]=b
        st=dict(st,ram=bytes(ram))
    if post.get('a6long'):
        ram=bytearray(st['ram']);off,val=post['a6long'];a6=st['regs']['a6']
        for i,b in enumerate((val&M32).to_bytes(4,'big')):ram[(a6+off+i)&0xffff]=b
        st=dict(st,ram=bytes(ram))
    if post.get('copy'):                                  # (dst register, displacement, size, src register, shift): memory at dst + displacement := (src >> shift) of the current state
        ram=bytearray(st['ram'])
        for rn,off,size,src,sh in post['copy']:
            base=st['regs'][rn];val=(st['regs'][src]>>sh)&((1<<(8*size))-1)
            for i,b in enumerate(val.to_bytes(size,'big')):ram[(base+off+i)&0xffff]=b
        st=dict(st,ram=bytes(ram))
    if post.get('mem'):                                   # (register name, displacement, size, value): memory at register + displacement
        ram=bytearray(st['ram'])
        for rn,off,size,val in post['mem']:
            base=st['regs'][rn]
            for i,b in enumerate((val&((1<<(8*size))-1)).to_bytes(size,'big')):ram[(base+off+i)&0xffff]=b
        st=dict(st,ram=bytes(ram))
    return st


def build_start2(env,fx,origin):
    """origin + cand edits; optionally run to the block `at` (reference flow, stop directly before it) and apply `post`; `then` = further (pc, post) waypoints."""
    st=apply_cand2(origin,fx['cand'])
    steps=[]
    if fx.get('at') is not None:steps.append((fx['at'],fx.get('post')))
    steps+=list(fx.get('then') or [])
    for pc,post in steps:
        fl=G1.Flow(env,st,'ref',set(G1.fix_stops(env))|{pc},NAT_LIMIT).run()
        if fl.final['kind']!='stop' or fl.final['detail']['pc']!=pc:return None,fl
        st=fl.states[-1]
        if post:st=apply_post(st,post)
    return st,None


def flow_summary(res,f,models):
    c=f['cont']
    d=dict(eq=res['eq'],model_ok=res['model_ok'],final=res['final'],final_detail=json.loads(sjson(c.final['detail'])),insns=res['insns'],pieces=res['pieces'],waits=res['waits'],
        leader_len=len(res['leaders']),leader_sha=sha(repr(res['leaders']).encode())[:16],xfers=[[p['unit'],p['trace'][-1][0] if p['trace'] else None,c.states[p['end']]['pc']] for p in c.pieces if p['unit']],
        ports_sha=G1.ports_sha(c.ports_all),ports=len(c.ports_all),pvc_banks=G1.pvc_banks_of(c),succ=dict(consumer_pairs(GLOBAL['env'],res['leaders'])))
    seen=set();first=[]
    for pc in res['leaders']:
        if pc not in seen:seen.add(pc);first.append(pc)
    d['leaders_first']=first;d['leaders']=res['leaders'][:4000]
    if not res['model_ok']:d['model_diffs']=res['model_diffs']
    d['reached']=sorted(set(first)|({c.final['detail']['pc']} if c.final['kind']=='stop' else set()))
    d['ok']=all(res['eq'].values()) and res['model_ok']
    return d


def fixture_task(arg):
    env=GLOBAL['env'];fx,origin_row=arg
    origin=G1.load_state(origin_row) if origin_row else None
    st,fail=build_start2(env,fx,origin)
    row=dict(name=fx['name'],kind=fx['kind'],unit=fx.get('unit'),targets=sorted(fx.get('targets',())),origin=fx.get('origin_ref'),edits=cand_json2(fx['cand']),at=fx.get('at') and G1.hx(fx['at']),
        post=fx.get('post') and cand_json2(fx['post']),why=fx.get('why',''),jump_target=fx.get('jump_target'),tag=fx.get('tag'),then=[[G1.hx(pc),cand_json2(pp)] for pc,pp in (fx.get('then') or [])])
    if st is None:
        row.update(ok=bool(fx.get('optional')),skipped=bool(fx.get('optional')),error='state-at not reached (%s)'%fail.final['kind'],final='state-not-reached',final_detail={},reached=[],leaders_first=[],xfers=[],succ={},pieces=[],insns=0);return row
    stops=tuple(sorted(G1.fix_stops(env)))
    res,f,models=G1.node_replay(env,st,stops,GLOBAL['fix_limit'],True)
    main=flow_summary(res,f,models);c=f['cont']
    row.update({k:v for k,v in main.items() if k!='leaders'});row['leaders_head']=main['leaders'][:64]
    row['start']=G1.dump_state(st);row['dumps']=[G1.dump_state(s) for s in c.states[1:]]
    if c.final['kind']=='stop' and c.final['detail']['pc'] in env.boundary:
        stops2=tuple(sorted(set(stops)-set(env.boundary)))
        r2,f2,m2=G1.node_replay(env,st,stops2,GLOBAL['fix_limit'],True);th=flow_summary(r2,f2,m2)
        th['dumps']=[G1.dump_state(s) for s in f2['cont'].states[1:]];th.pop('leaders',None);row['through']=th
        row['reached']=sorted(set(row['reached'])|set(th['reached']))
        row['ok']=row['ok'] and th['ok']
    row['bank_start']=[G1.hx(st['bank'][0]),G1.hx(st['bank'][1]),G1.hx(st['bank'][2])]
    return row


def recipe_fixture2(name,kind,rc,unit=None,targets=(),why=''):
    row,ref=rc['origin']
    return dict(name=name,kind=kind,unit=unit,targets=list(targets),cand=rc['cand'],origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=rc['origin_pc'],how=rc['kind']),why=why)


def cfg_check(env,cfg):
    """CFG derived (decoder) in-unit branch / fall-through / call targets against the contract block starts."""
    extra=collections.defaultdict(set);derived=collections.defaultdict(set)
    for s,b in cfg.items():
        u=b['unit']
        for k,t in b['succ']:
            if t is None:continue
            if env.unit_of(t)==u:
                derived[u].add(t)
                if t not in env.starts:extra[u].add(t)
    entries={u:sorted(set(env.contracts[u]['starts'])-derived[u]) for u in UIDS}
    return {u:sorted(extra[u]) for u in UIDS},entries


# ----------------------------------------------------------------------------------
# Hand fixtures: the 44ade jump table, carry consumers, PVC bank sweeps, guards, 28ae failures
# ----------------------------------------------------------------------------------
def pvc_state(ff8raw,ff9raw):
    base,ff8,ff9=pvc_bank_update(ff8raw,ff9raw);return (base,ff8,ff9)


BANK_SWEEP=[('n%d'%n,pvc_state(0,(n-1)*0x1000)) for n in range(2,10)]+[('unaligned+12',pvc_state(0x1200,0x1000)),('odd-base',pvc_state(0x0100,0x1000)),('edge-7fe000',pvc_state(0,0x6fe0)),('hi-a00000',pvc_state(0,0x9000))]


def unit_entries(b_list,env):
    """unit -> (node entry dump row, ref) of the first natural node that executed the unit; plus 'any'."""
    ent={};anyent=None
    for b in b_list:
        for n in b['nodes']:
            e=n.get('entry_dump')
            if not e:continue
            ref=(b['case'],n['frame'],n['seq'])
            if anyent is None:anyent=(e,ref)
            for pc in n['leaders_first']:
                u=env.starts.get(pc)
                if u and u not in ent:ent[u]=(e,ref)
    ent['any']=anyent
    return ent


def decode_block(env,s):
    mdl=new_model(env);return [mdl.decode(pc) for pc in env.cfg[s]['insns']]


def range_leaf_params(env,t):
    """For a 44ade range-judging head: (k0, lim, cond) or None."""
    k0=0;lim=None;cond=None
    for ins in decode_block(env,t):
        if ins.op=='subi' and ins.dst==('dn',4):k0=ins.imm
        if ins.op=='cmpi' and ins.dst==('dn',4):lim=ins.imm
        if ins.op=='bcc' and lim is not None:cond=ins.cond
    return (k0,lim,cond) if lim is not None and cond in (4,5) else None


def d1_candidates(k0,lim,cond):
    """D1 values (low 19 bits matter) that stay in range / leave the range of a 44ade range-judging head (computed from the head's own operands)."""
    def out_of_range(v):
        d4=(v&0x7ffff);d4=(d4-k0)&M32
        return (d4>=lim) if cond==4 else (d4<lim)          # BCC: D4 >= lim -> 44c62 ; BCS: D4 < lim -> 44c62
    pool={0,1,2,3,0x7ffff,0x7fffe,0x40000,0x3ffff,0x20000,0x1ffff,0x10000,0xffff,0x8000,0x30000,0x50000,0x60000,0x70000,k0&0x7ffff,(k0-1)&0x7ffff,(k0+1)&0x7ffff,
        (k0+lim)&0x7ffff,(k0+lim-1)&0x7ffff,(k0+lim+1)&0x7ffff,(lim)&0x7ffff,(lim-1)&0x7ffff,(lim+1)&0x7ffff}
    ins=sorted(v for v in pool if not out_of_range(v));outs=sorted(v for v in pool if out_of_range(v))
    if len(ins)<2:
        for v in range(0,0x80000,0x200):
            if not out_of_range(v):ins.append(v)
            if len(ins)>=3:break
    return ins[:3],outs[:2]


def jump_table_fixtures(env,ent):
    """All 96 indexes of the 44ade jump table (D7.W = 4k) with data variants, plus the out-of-table D7 edge values."""
    out=[];row,ref=ent.get(20) or ent['any']
    mdl=new_model(env)
    def fx(name,kind,cand,why,tag=None):
        return dict(name=name,kind=kind,unit=20,targets=[],cand=cand,origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=0x2ab8,how='node-entry'),why=why,tag=tag)
    A5=0x108000
    for k in range(0x60):
        idx=4*k;ent_pc=0x44ae2+idx;bra=mdl.decode(ent_pc);assert bra.op=='bra',hex(ent_pc);t=bra.target
        variants=[]
        rp=range_leaf_params(env,t)
        if rp:
            ins,outs=d1_candidates(*rp)
            for v in ins:variants.append(('in%05x'%v,dict(d0=0x89abcdef,d1=0xfff00000|v,d2=0x11111111,d4=0x5a5a5a5a),0))
            for v in outs:variants.append(('out%05x'%v,dict(d0=0x00123456,d1=0x00300000|v,d2=0x80000000,d4=0xa5a5a5a5),0))
        else:
            variants.append(('a',dict(d0=0x89abcdef,d1=0xfff54321,d2=0x11111111,d4=0x5a5a5a5a),0))
            variants.append(('b',dict(d0=0xffffffff,d1=0xffffffff,d2=0x80000000,d4=0),0))
            variants.append(('c',dict(d0=0x7ffff,d1=0x7ffff,d2=0,d4=0xffffffff),1))
            variants.append(('d',dict(d0=0x00040001,d1=0x00000000,d2=0xffffffff,d4=0x7ffff),1))
        for tag,rg,b549e in variants:
            regs=dict(rg);regs['d7']=idx
            ram={(A5+0x549e)&0xffff:b549e}
            out.append(fx('jump-table idx=%02x -> %x %s'%(k,t,tag),'jump-table',entry_cand(0x44ade,regs,ram),'44ade with D7.W := %04x: JMP 44ae2(PC,D7.W) reaches the table entry %x (BRA.W -> %x)'%(idx,ent_pc,t),tag='idx%02x'%k))
    for d7,why in ((0x180,'D7.W = 180: 44ae2+180 = 44c62 (the common no-height block, first byte after the 96 entries)'),(0x1,'odd D7.W: the computed PC is odd (address error)'),(0xfffc,'D7.W = fffc: 44ae2-4 = 44ade, the table function jumps to itself (watchdog)')):
        out.append(fx('jump-table-edge d7=%04x'%d7,'jump-table-edge',entry_cand(0x44ade,dict(d7=d7,d0=0x1234,d1=0x5678,d2=0)),why,tag='edge'))
    return out


CONSUMER_CCR=(0x00,0x01,0x1e,0x1f)
A5R=0x108000
# known-carry producers and the consumers the contracts name for them (the native outcome of a REAL chain must equal the declared-CCR outcome of the claimed C)
PRODUCER_CONSUMERS={0x46d08:(0xea650,0xea678),0x46d12:(0xea650,0xea678),0xb7e64:(0xb67a4,0xb6414),0xea67a:(0xea792,),0x484ec:(0xb7b52,),0x484f2:(0xb7b52,),0xb7bb6:(0xb76c4,),0xb7bbc:(0xb76c4,),
    0x497a6:(0x8592c,),0x497b0:(0x8592c,)}
CHAIN_FIXTURES=[
    (0x85926,'U20b 85926 JSR 497a6 -> 8592c BCC: U20a 497a6 (BYTE 10fd92 <> 0: Clear) / 497b0 (= 0: Set)',[('10fd92=00',dict(ram={0xfd92:0})),('10fd92=01',dict(ram={0xfd92:1}))]),
    (0xb7b4c,'U19 b7b4c JSR 484e2 -> b7b52 BCS: U19 484ec (BYTE 5683(A5) bit0 = 1: Set) / 484f2 (= 0: Clear)',[('5683=00',dict(ram={(A5R+0x5683)&0xffff:0})),('5683=01',dict(ram={(A5R+0x5683)&0xffff:1}))]),
    (0xb76bc,'U18 b76bc BSR b7b4c -> b76c4 BCC: U19 b7b4c result (Set b7bb6 / Clear b7bbc) through 484e2 (BYTE 5683(A5) bit0)',[('5683=00',dict(ram={(A5R+0x5683)&0xffff:0})),('5683=01',dict(ram={(A5R+0x5683)&0xffff:1}))]),
    (0xb67a0,'U18 b67a0 JSR b7e5c -> b67a4 BCC: b7e64 (WORD 8c(A6) <> 0: Clear) / 4b54e (= 0: U01 result)',[('8c=0000',dict(a6mem=[(0x8c,2,0)])),('8c=0002',dict(a6mem=[(0x8c,2,2)]))])]
# optional chains with a second waypoint: (start block, why, [(tag, first post, [(waypoint pc, waypoint post)])])
CHAIN_THEN=[
    (0x46cb0,'U18 46cb0 (after 447be): WORD 54d8(A5) := D7 high word, so CMP.W 54d8(A5),D7 after SWAP D7 is equal and BEQ takes 46d12 (Set) -> RTS to the 46c68 caller consumer (ea650 / ea678)',[('54d8=D7.hi',dict(ram={},copy=[('a5',0x54d8,2,'d7',16)]),[])]),
    (0xb76bc,'U18 b76bc BSR b7b4c -> b76c4 BCC through U19 b7ba6: D1 = 100cb8 (BEQ) -> b7bb6 (Set)',[('5683=00,D1=100cb8',dict(ram={(A5R+0x5683)&0xffff:0}),[(0xb7ba6,dict(regs={'d1':0x100cb8},ram={},ccr=None))]),
        ('5683=00,D1=100da8',dict(ram={(A5R+0x5683)&0xffff:0}),[(0xb7ba6,dict(regs={'d1':0x100da8},ram={},ccr=None))]),
        ('5683=00,popped LONG negative',dict(ram={(A5R+0x5683)&0xffff:0}),[(0xb7b9a,dict(regs={},ram={},ccr=None,mem=[('a7',0,4,0x80000000)]))])])]
GUARD_FAMILIES=(('a6-odd','odd',lambda a6:a6|1),('a6-rom','rom',lambda a6:0x2000),('a6-unmapped','unmapped',lambda a6:0x400000))


def memory_kinds(env,s):
    """Static memory-access kinds of a block: 'a6' (d16(A6) access), 'push' (JSR / BSR / MOVEM pre-decrement), 'pop' (RTS / MOVEM post-increment), 'a5'."""
    k=set();mdl=new_model(env)
    for pc in env.cfg[s]['insns']:
        ins=mdl.decode(pc)
        for ea in (ins.src,ins.dst):
            if ea and ea[0] in('d16','ind','idx','post','pre') and ea[1]==6:k.add('a6')
            if ea and ea[0] in('d16','ind') and ea[1]==5:k.add('a5')
        if ins.op in('jsr','bsr'):k.add('push')
        if ins.op=='rts':k.add('pop')
    return k


def hand_fixtures(env,fs):
    rec=fs['recipes'];out=[];ana=env.ana
    # H1 carry consumers: declared CCR at the consumer; the native branch outcome is the evidence
    for s in sorted(env.consumers):
        rc=rec.get(s)
        if rc is None:continue
        u=env.starts[s]
        for ccr in CONSUMER_CCR:
            fx=recipe_fixture2('carry-consumer %x ccr=%02x'%(s,ccr),'carry-consumer',rc,u,[s],'consumer %x reads C from its caller: declared CCR %02x at the block start (branch outcome of the native run)'%(s,ccr))
            fx['at']=s;fx['post']=dict(regs={},ram={},ccr=ccr);fx['tag']='ccr%02x'%ccr;out.append(fx)
    # H2 producer -> consumer chains through REAL producers (the producer block runs natively, the consumer branch outcome is the evidence)
    for s0,why,variants in CHAIN_FIXTURES:
        rc=rec.get(s0)
        if rc is None:continue
        u=env.starts[s0]
        for tag,post in variants:
            fx=recipe_fixture2('producer-chain %x %s'%(s0,tag),'producer-chain',rc,u,[s0],'%s: %s'%(why,tag))
            fx['at']=s0;fx['post']=dict(regs={},ram=post.get('ram',{}),ccr=None,a6mem=post.get('a6mem'),copy=post.get('copy'),mem=post.get('mem'));fx['tag']=tag;out.append(fx)
    for s0,why,variants in CHAIN_THEN:
        rc=rec.get(s0)
        if rc is None:continue
        u=env.starts[s0]
        for tag,post,then in variants:
            fx=recipe_fixture2('producer-chain %x %s'%(s0,tag),'producer-chain',rc,u,[s0],'%s: %s'%(why,tag))
            fx['at']=s0;fx['post']=dict(regs={},ram=post.get('ram',{}),ccr=None,copy=post.get('copy'),mem=post.get('mem'));fx['then']=list(then);fx['tag']=tag;fx['optional']=True;out.append(fx)
    # H4 PVC bank sweep of every bank-window block
    for s in sorted(env.starts):
        if not ana[s]['bank']:continue
        rc=rec.get(s)
        if rc is None:continue
        u=env.starts[s]
        for bn,bank in BANK_SWEEP:
            fx=recipe_fixture2('bank %x %s'%(s,bn),'pvc-bank',rc,u,[s],'block %x reads the banked window %s: declared PVC bank %x (ff8 %04x ff9 %04x, MAME formula)'%(s,'/'.join('%x'%x for x in ana[s]['bank']),bank[0],bank[1],bank[2]))
            fx['at']=s;fx['post']=dict(regs={},ram={},ccr=None,bank=bank);fx['tag']=bn;out.append(fx)
    # H5 guard families: per unit the first block of each static memory kind
    seen=set()
    for s in sorted(env.starts):
        u=env.starts[s];kinds=memory_kinds(env,s);rc=rec.get(s)
        if rc is None:continue
        for kd in ('a6','push','pop','a5'):
            if kd in kinds and (u,kd) not in seen:
                seen.add((u,kd))
                if kd=='a6':
                    for gname,gk,fn in GUARD_FAMILIES:
                        fx=recipe_fixture2('guard %s u%s %x'%(gname,NAMES[u],s),'guard-family',rc,u,[],'block %x of %s: declared A6 := %s (guard family %s)'%(s,NAMES[u],gname,gk))
                        fx['at']=s;fx['post']=dict(regs={},ram={},ccr=None,a6fn=gname);fx['tag']=gname;out.append(fx)
                elif kd in ('push','pop'):
                    fx=recipe_fixture2('guard a7-odd u%s %x'%(NAMES[u],s),'guard-family',rc,u,[],'block %x of %s: declared A7 := odd (stack %s at an odd address)'%(s,NAMES[u],kd))
                    fx['at']=s;fx['post']=dict(regs={},ram={},ccr=None,a7odd=True);fx['tag']='a7-odd';out.append(fx)
    # H6 28ae child creation failure / success at the JSR 28ae blocks
    for s in sorted(env.starts):
        if not ana[s]['jsr28ae']:continue
        rc=rec.get(s)
        if rc is None:continue
        u=env.starts[s]
        for v,nm in ((0,'fail'),(0x7fff,'ok')):
            fx=recipe_fixture2('28ae-%s %x'%(nm,s),'28ae-%s'%nm,rc,u,[s],'JSR 28ae block %x with WORD 104ca0 := %04x (child creation %s)'%(s,v,'fails (D0.W >= 104ca0)' if v==0 else 'succeeds'))
            fx['at']=s;fx['post']=dict(regs={},ram={0x4ca0:v>>8,0x4ca1:v&0xff},ccr=None);fx['tag']=nm;out.append(fx)
    return out


# ----------------------------------------------------------------------------------
# Fixture stage: phase 0 (jump table), coverage guided search for the remaining block starts, declared entries as the last resort, hand fixtures, verification
# ----------------------------------------------------------------------------------
crc=G1.crc


def run_fixtures(ctx,args,fixtures):
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:rows=pool.map(fixture_task,[(fx,fx['origin_row']) for fx in fixtures],chunksize=1)
    return rows


def stage_fixtures(env,args,b_list,out_dir):
    ctx=multiprocessing.get_context('fork')
    origins={};entries={}
    for b in b_list:
        for n in b['nodes']:
            for pc,row in n.get('captures',{}).items():origins.setdefault(pc,(row,(b['case'],n['frame'],n['seq'])))
            if n.get('entry_dump') and n['cb'] not in entries:entries[n['cb']]=(n['entry_dump'],(b['case'],n['frame'],n['seq']))
    ent=unit_entries(b_list,env)
    nat=set();nat_xfer_to=set()
    for b in b_list:
        for n in b['nodes']:
            nat.update(n['leaders_first'])
            for u,last,to in n['xfers']:nat_xfer_to.add(to)
    ana=env.ana;cfg=env.cfg
    GLOBAL['dvals']=sorted(set(v for u in UIDS for v in G1.dict_values(env,u)));GLOBAL['htab']=G1.hint_table(env)
    # phase 0: the 44ade jump table (all indexes) from a declared node-level entry
    jt=jump_table_fixtures(env,ent);GLOBAL['fix_limit']=20_000
    jt_rows=run_fixtures(ctx,args,jt)
    jt_reached=set()
    for r in jt_rows:
        if r['ok']:jt_reached.update(r['reached'])
    targets=[pc for pc in sorted(env.starts) if pc not in nat and pc not in jt_reached]
    dist={t:G1.cfg_distance(cfg,t) for t in targets}
    recipes={}
    for pc in sorted(env.starts):
        if pc in nat and pc in origins:recipes[pc]=dict(kind='natural',origin_pc=pc,origin=origins[pc],cand=G1.empty_cand())
    rounds=[];pending=list(targets);pseudo={}
    extra,entries_by_unit=cfg_check(env,cfg)
    entry_set={e for u in entries_by_unit for e in entries_by_unit[u]}|G1.install_entries(env)
    unit_origins=collections.defaultdict(list)
    for o in sorted(origins):unit_origins[env.starts.get(o,0)].append(o)
    for rnd in range(5):
        if rnd==2:
            for tt in sorted(pending):
                if tt in entry_set and tt not in pseudo:
                    u=env.starts[tt];o=(unit_origins.get(u) or sorted(origins))[0];row,ref=origins[o]
                    pseudo[tt]=(dict(row,pc=tt),ref,o)
        allo=dict(origins)
        for e,(row,ref,o) in pseudo.items():allo[e]=(row,ref)
        groups=collections.defaultdict(list)
        for tt in pending:
            if tt in pseudo:continue
            cands=sorted((d,o) for o in allo for d in [dist[tt].get(o)] if d is not None)
            k=rnd if rnd<2 else 0
            if k<len(cands):groups[cands[k][1]].append(tt)
        tasks=[(allo[o][0],o,sorted(ts),crc('c2',o,rnd),args.budget) for o,ts in sorted(groups.items())]
        GLOBAL['plan']={}
        with ctx.Pool(args.workers) as pool:res=pool.map(G1.campaign_task,tasks,chunksize=1)
        for r in res:
            for tt,cand in sorted(r['found'].items()):
                if tt not in recipes:
                    if r['origin_pc'] in pseudo:
                        row,ref,o=pseudo[r['origin_pc']];recipes[tt]=dict(kind='path-from-entry',origin_pc=r['origin_pc'],origin=(row,ref),cand=cand,round=rnd)
                    else:recipes[tt]=dict(kind='path',origin_pc=r['origin_pc'],origin=origins[r['origin_pc']],cand=cand,round=rnd)
            rounds.append(dict(round=rnd,origin=G1.hx(r['origin_pc']),asked=[G1.hx(x) for x in r['asked']],found=[G1.hx(x) for x in sorted(r['found'])],stats=r['stats']))
        pending=[tt for tt in pending if tt not in recipes and tt not in pseudo]
        if not pending and rnd>=2:break
    # rounds 5 and 6: blocks reached by typed paths become origins (their captured states) for the blocks that are still pending
    for rnd in (5,6):
        pend=[tt for tt in pending if tt not in recipes and tt not in pseudo]
        if not pend:break
        new_orig={}
        for tt,rc in sorted(recipes.items()):
            if rc['kind'] in('path','path-from-entry','path2') and tt not in origins and tt not in new_orig:
                st,fail=build_start2(env,dict(cand=rc['cand'],at=tt),G1.load_state(rc['origin'][0]))
                if st is not None:new_orig[tt]=(G1.dump_state(st),('typed:'+G1.hx(rc['origin_pc']),0,0))
        allo=dict(origins);allo.update(new_orig)
        groups=collections.defaultdict(list)
        for tt in pend:
            cands=sorted((d,o) for o in allo for d in [dist[tt].get(o)] if d is not None and o in new_orig)
            if cands:groups[cands[0][1]].append(tt)
        tasks=[(allo[o][0],o,sorted(ts),crc('c3',o,rnd),args.budget) for o,ts in sorted(groups.items())]
        GLOBAL['plan']={}
        with ctx.Pool(args.workers) as pool:res=pool.map(G1.campaign_task,tasks,chunksize=1)
        for r in res:
            for tt,cand in sorted(r['found'].items()):
                if tt not in recipes:recipes[tt]=dict(kind='path2',origin_pc=r['origin_pc'],origin=allo[r['origin_pc']],cand=cand,round=rnd)
            rounds.append(dict(round=rnd,origin=G1.hx(r['origin_pc']),asked=[G1.hx(x) for x in r['asked']],found=[G1.hx(x) for x in sorted(r['found'])],stats=r['stats']))
        pending=[tt for tt in pending if tt not in recipes and tt not in pseudo]
    for e,(row,ref,o) in sorted(pseudo.items()):
        if e not in recipes:recipes[e]=dict(kind='entry-self',origin_pc=o,origin=origins[o],cand=dict(regs={},ram={},ccr=0,pc=e))
    # last resort: declared node-level entry at the block (A7 = SPd-4, LONG 2ac2) from a node entry dump of the unit
    for tt in pending:
        u=env.starts.get(tt) or 0
        erow,eref=ent.get(u) or ent['any']
        recipes[tt]=dict(kind='entry-declared',origin_pc=0x2ab8,origin=(erow,eref),cand=entry_cand(tt))
    fallback=sorted(tt for tt,rc in recipes.items() if rc['kind'] in ('entry-self','entry-declared'))
    # recipes for starts reached only by the jump-table fixtures (the hand fixtures that need a recipe replay the table fixture's own declared edits)
    for fxd,r in zip(jt,jt_rows):
        if not r['ok']:continue
        for tt in r['reached']:
            if tt in env.starts and tt not in recipes and tt not in nat:
                erow,eref=ent.get(20) or ent['any'];recipes[tt]=dict(kind='jump-table',origin_pc=0x2ab8,origin=(erow,eref),cand=fxd['cand'])
    return dict(origins=origins,entries=entries,ent=ent,nat=nat,nat_xfer_to=nat_xfer_to,cfg=cfg,recipes=recipes,rounds=rounds,fallback=fallback,targets=targets,jt_rows=jt_rows,jt_reached=jt_reached,extra=extra,entries_by_unit=entries_by_unit)


def stage_verify(env,args,fs,b_list,out_dir):
    ctx=multiprocessing.get_context('fork');origins=fs['origins']
    gtasks=[];by_unit=collections.defaultdict(list)
    for o in sorted(origins):
        u=env.starts.get(o)
        if u:by_unit[u].append(o)
    for u in sorted(by_unit):
        lst=by_unit[u];pick=lst[::max(1,len(lst)//3)][:3]
        for o in pick:gtasks.append((origins[o][0],o,crc('g2',o),args.budget//2))
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:gres=pool.map(G1.guard_task,gtasks,chunksize=1)
    fixtures=[];groups=collections.OrderedDict()
    for tt,rc in sorted(fs['recipes'].items()):
        if rc['kind'] in ('natural','jump-table'):continue
        key=(rc['origin_pc'],sjson(cand_json2(rc['cand'])),rc['kind'])
        groups.setdefault(key,[]).append((tt,rc))
    for i,(key,lst) in enumerate(groups.items()):
        rc=lst[0][1];ts=[tt for tt,_ in lst];u=env.starts.get(ts[0])
        fixtures.append(recipe_fixture2('reach-%s-%03d'%(rc['kind'],i),rc['kind'],rc,u,ts,'search result: the minimized edit list reaches '+' '.join('%x'%x for x in ts)))
    fixtures+=hand_fixtures(env,fs)
    gi=0
    for r in gres:
        row,ref=origins[r['origin_pc']]
        for (u,kind,pc),cand in sorted(r['guards'].items()):
            fixtures.append(dict(name='guard-%s-u%s-%x-%03d'%(kind,NAMES.get(u,u),pc,gi),kind='guard',unit=u,targets=[],cand=cand,origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=r['origin_pc'],how='natural+edits'),
                why='search result: %s at %x inside unit %s'%(kind,pc,NAMES.get(u,u))));gi+=1
    rows=run_fixtures(ctx,args,fixtures)
    return rows,fixtures,gres


# ----------------------------------------------------------------------------------
# Native one-block carry experiment (C_in 0 / 1 x register variants; the exact CCR is read with the MOVE SR,D0 probe at the stop)
# ----------------------------------------------------------------------------------
def native_block(env,st,s,ccr):
    """Run the block starting at s natively with a declared CCR until the first instruction of another block / outside the unit.  Returns (C_out or None, stop pc, guard kind or None)."""
    st=dict(st,ccr=ccr,pc=s);m=G1.make_machine(env,st);c=m.cpu;u=env.starts[s];state=dict(n=0,stop=None)
    def hook(uc,pc,size,user):
        if state['n']>0 and (pc in env.starts or env.unit_of(pc)!=u):state['stop']=pc;uc.emu_stop();return
        state['n']+=1
        if state['n']>300:uc.emu_stop()
    c.hook_add(UC_HOOK_CODE,hook,begin=0,end=0xfffff)
    err=None
    try:c.emu_start(s,0xffffff,count=2000)
    except unicorn.UcError as e:err=str(e)
    g=G1.guard_of(m)
    if g or err or state['stop'] is None:return None,state['stop'],(g[0] if g else (err or 'no-stop'))
    v=G1.probe_ccr(m)
    return (None if v is None else v&1),state['stop'],None


def carry_native_task(arg):
    env=GLOBAL['env'];s,row,cand,seed=arg
    origin=G1.load_state(row);fx=dict(cand=cand,at=s)
    st,fail=build_start2(env,fx,origin)
    if st is None:return dict(start=s,cls=None,why='state-at not reached')
    rng=random.Random(seed);obs=[];stops=set();guards=collections.Counter()
    variants=[dict()]+[dict((('d%d'%i),rng.choice((0,1,2,0xff,0x7fff,0x8000,0xffff,rng.getrandbits(32)))) for i in range(8)) for _ in range(7)]
    for var in variants:
        for cin in (0,1):
            regs=dict(st['regs']);regs.update(var)
            c_out,stop,g=native_block(env,dict(st,regs=regs),s,cin)
            if g:guards[g]+=1
            if c_out is not None:obs.append((cin,c_out));stops.add(stop)
    if not obs:return dict(start=s,cls=None,why='no completed variant',guards=dict(guards))
    if all(o==i for i,o in obs):cls='preserve'
    elif all(o==0 for i,o in obs):cls='clear'
    elif all(o==1 for i,o in obs):cls='set'
    else:cls='data'
    return dict(start=s,cls=cls,runs=len(obs),guards=dict(guards),stops=sorted(stops)[:4])


def stage_carry(env,args,fs):
    ctx=multiprocessing.get_context('fork');tasks=[]
    for s,rc in sorted(fs['recipes'].items()):
        if s in env.starts:tasks.append((s,rc['origin'][0],rc['cand'],crc('carry2',s)))
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:res=pool.map(carry_native_task,tasks,chunksize=4)
    obs={r['start']:r for r in res}
    rep=dict(per_unit={});disc=[]
    for u in UIDS:
        c=env.contracts[u];L=c['lists'];starts=c['starts'];flow=set(L['flow'] or []);prod=L['producers']
        bad=[];row=dict(observed=dict(collections.Counter(str(obs[s]['cls']) for s in starts if s in obs)),unobserved=[G1.hx(s) for s in starts if s not in obs or obs[s]['cls'] is None])
        for s in sorted(flow):
            o=obs.get(s)
            if o and o['cls'] not in(None,'preserve'):bad.append(dict(what='contract FLOW_ONLY block does not preserve C (native)',start=G1.hx(s),observed=o['cls']))
        for s,w in sorted(prod.items()):
            o=obs.get(s);want=w.lower()
            if o and o['cls'] not in(None,want):bad.append(dict(what='contract known %s producer (native)'%w,start=G1.hx(s),observed=o['cls']))
        row['preserve_not_in_contract_flow']=[G1.hx(s) for s in starts if s in obs and obs[s]['cls']=='preserve' and s not in flow and s not in prod]
        row['model_vs_native']=[dict(start=G1.hx(s),model=('preserve' if env.ana[s]['c_written'] is None else 'written'),native=obs[s]['cls']) for s in starts if s in obs and obs[s]['cls'] is not None and
            ((env.ana[s]['c_written'] is None)!=(obs[s]['cls']=='preserve'))]
        row['contract_flow_n']=L['flow_n'];row['contract_flow_listed']=len(flow);row['discrepancies']=bad
        rep['per_unit'][u]=row
        for b in bad:disc.append(dict(id='%s-carry'%NAMES[u],claim='contract carry classification vs native one-block experiment (C_in 0/1 x 8 register variants, exact CCR probe)',detail=b))
        if L['flow_n'] is not None and len(flow)!=L['flow_n']:disc.append(dict(id='%s-flow-count'%NAMES[u],claim='contract FLOW_ONLY count vs listed pcs',detail=dict(stated=L['flow_n'],listed=len(flow))))
        if L['consumers_n'] is not None and len(L['consumers'])!=L['consumers_n']:disc.append(dict(id='%s-consumer-count'%NAMES[u],claim='contract consumer count vs listed pcs',detail=dict(stated=L['consumers_n'],listed=len(L['consumers']))))
    rep['observed_classes']=dict(collections.Counter(str(r['cls']) for r in res))
    return rep,disc,obs


# ----------------------------------------------------------------------------------
# Contract data claims that can be checked against the ROM bytes (banked window values, fixed ROM tables) and the contract numbers
# ----------------------------------------------------------------------------------
def rom_long(prog,addr):return int.from_bytes(prog[addr:addr+4],'big')
def rom_word(prog,addr):return int.from_bytes(prog[addr:addr+2],'big')


def bank_long(prog,base,addr):
    """LONG read at CPU address `addr` with the program bank `base` selected: fixed ROM below 100000, the banked window 200000..2fdfff otherwise (None = outside the image)."""
    if addr<0x100000:return rom_long(prog,addr)
    if 0x200000<=addr<0x2fe000:
        ph=base+addr-0x200000
        return rom_long(prog,ph) if ph+4<=len(prog) else None
    return None


def data_checks(prog):
    out=[]
    def chk(unit,what,expected,actual):out.append(dict(unit=unit,what=what,expected=expected,actual=actual,ok=expected==actual))
    def chain(unit,base,hub,first,offs,exps):
        v=bank_long(prog,base,hub);chk(unit,'bank %x LONG %x'%(base,hub),first,v)
        if v is None:return
        for o,e in zip(offs,exps):chk(unit,'bank %x LONG %x + %x'%(base,hub,o),e,bank_long(prog,base,v+o))
    # U17 (contract 결정 3)
    chain('U17',0x200000,0x200140,0x002bc424,(0xd4,),(0x002bd5ea,))
    chain('U17',0x200000,0x200088,0x00296528,(0x64,0x68,0x6c),(0x0029699a,0x002969ec,0x00296a86))
    chain('U17',0x300000,0x200140,0x00008260,(0xd4,),(0x000719c0,))
    chain('U17',0x300000,0x200088,0x0025aaf8,(0x64,),(0x01000000,))
    chain('U17',0x400000,0x200140,0x00223818,(0xd4,),(0x00000100,))
    chain('U17',0x400000,0x200088,0x002000b0,(0x64,),(0x002236b4,))
    # U18 (결정 6)
    chain('U18',0x200000,0x2001a8,0x002d0086,(0x10,),(0x002d024a,))
    chain('U18',0x200000,0x2001ac,0x002d0e90,(0x10,),(0x002d0f8a,))
    for base,a,b in ((0x300000,0x03959560,0x03c78860),(0x400000,0x00223b70,0x00223b88)):
        chk('U18','bank %x LONG 2001a8'%base,a,bank_long(prog,base,0x2001a8));chk('U18','bank %x LONG 2001ac'%base,b,bank_long(prog,base,0x2001ac))
    chk('U18','fixed LONG table b7f54',[4,8,0xb,9,0xc,0xb,0xf,1],[rom_long(prog,0xb7f54+4*i) for i in range(8)])
    chk('U18','fixed WORD table b7f14',[0x0d89,0x0d8c,0x0d88,0x0d8c,0,1],[rom_word(prog,0xb7f14+2*i) for i in range(6)])
    chk('U18','fixed LONG table ea742',[0xeab42,0xeab70,0xeab9e,0xeabcc],[rom_long(prog,0xea742+4*i) for i in range(4)])
    chk('U18','fixed LONG table ea752',[0xeab42,0xeab70,0xeab9e,0xeabfa],[rom_long(prog,0xea752+4*i) for i in range(4)])
    # U19 (결정 3)
    chain('U19',0x200000,0x2001a8,0x002d0086,(),());chain('U19',0x200000,0x2001ac,0x002d0e90,(),())
    for hub,v2,v3,v4 in ((0x2001c0,0x00028260,0x00223c00,0x002cdeaa),(0x2001cc,0x01258260,0x00223c48,0x002cf71a),(0x2001d4,0x01e78260,0x00223c70,0x002d49d8)):
        chk('U19','bank 200000 LONG %x'%hub,v4,bank_long(prog,0x200000,hub));chk('U19','bank 300000 LONG %x'%hub,v2,bank_long(prog,0x300000,hub));chk('U19','bank 400000 LONG %x'%hub,v3,bank_long(prog,0x400000,hub))
    for base,a,b in ((0x300000,0x03959560,0x03c78860),(0x400000,0x00223b70,0x00223b88)):
        chk('U19','bank %x LONG 2001a8'%base,a,bank_long(prog,base,0x2001a8));chk('U19','bank %x LONG 2001ac'%base,b,bank_long(prog,base,0x2001ac))
    chk('U19','fixed WORD table b7f18',[0x0d88,0x0d8c],[rom_word(prog,0xb7f18+2*i) for i in range(2)])
    for t,lst in ((0xb7f1c,[1,4,8,5]),(0xb7f24,[8,5,2,6]),(0xb7f3c,[0x11,3,9,7]),(0xb7f6c,[0xf,1,0xf,2]),(0xb7f74,[0xf,2,0x10,0xd])):
        chk('U19','fixed LONG table %x'%t,lst,[rom_long(prog,t+4*i) for i in range(4)])
    chk('U19','fixed WORD table d841a',[0x03ab,0x00cf],[rom_word(prog,0xd841a+2*i) for i in range(2)])
    # U20b
    for base,v in ((0x200000,0x002b3388),(0x300000,0x0029f3c8),(0x400000,0x0022351c)):chk('U20b','bank %x LONG 2000e0'%base,v,bank_long(prog,base,0x2000e0))
    chk('U20b','fixed WORD table 84976',[0x0c5f,0x0c62,0x0c63,0x0c64,0x0c65,0x0c67],[rom_word(prog,0x84976+2*i) for i in range(6)])
    chk('U20b','84982 rectangle LONGs (ffe0fff0 00400040)',[0xffe0fff0,0x00400040],[rom_long(prog,0x84982),rom_long(prog,0x84986)])
    # N01
    chk('N01','5205e records',[0x00e0,0x00d0,0x00052156,0x00b0,0x0090,0x0005216a],[rom_word(prog,0x5205e),rom_word(prog,0x52060),rom_long(prog,0x52062),rom_word(prog,0x52066),rom_word(prog,0x52068),rom_long(prog,0x5206a)])
    chk('N01','5206e WORD table',[0x0e72,0x0e73,0x0e74,0x0e75,0x0e76,0x0e77,0x0e78,0x0e79,0x0e7a,0x0e7b,0xffff,0xffff,0xffff,0xffff],[rom_word(prog,0x5206e+2*i) for i in range(14)])
    chk('N01','e5e80 WORD table',[6,7,0xb,0xc,0x10,0x11,0x16,0x17],[rom_word(prog,0xe5e80+2*i) for i in range(8)])
    chk('N01','e5e90 WORD table',[4,5,9,0xa,0xe,0xf,0x14,0x15],[rom_word(prog,0xe5e90+2*i) for i in range(8)])
    chk('N01','e5fbe first record (0030 0001 0e1f)',[0x30,1,0xe1f],[rom_word(prog,0xe5fbe+2*i) for i in range(3)])
    # U20a
    chk('U20a','44ade JMP 44ae2(PC,D7.W) opcode',[0x4efb,0x7002],[rom_word(prog,0x44ade),rom_word(prog,0x44ae0)])
    chk('U20a','table 44ae2..44c62 = 96 BRA.W (opcode 6000)',[0x6000]*96,[rom_word(prog,0x44ae2+4*k) for k in range(96)])
    chk('U20a','44ae2+160 = 44c42 is BRA.W 44c62',[0x6000,0x44c62],[rom_word(prog,0x44c42),0x44c44+sx16(rom_word(prog,0x44c44))])
    return out


def sx16(v):return v-0x10000 if v&0x8000 else v


def contract_unreached_list(u,env):
    t=env.contracts[u]['text'];starts=set(env.contracts[u]['starts'])
    m=re.search(r'미도달 (\d+)개\(([^)]*)\)',t) or re.search(r'자연 미도달 (\d+)개:([^\n]*)',t)
    if not m:return None
    body=m.group(2);out=set()
    for a,b in re.findall(r'`([0-9a-f]{3,6})`~`([0-9a-f]{3,6})`',body):
        lo,hi=int(a,16),int(b,16);out.update(x for x in starts if lo<=x<=hi)
    body2=re.sub(r'`[0-9a-f]{3,6}`~`[0-9a-f]{3,6}`','',body)
    out.update(int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`',body2))
    return dict(stated=int(m.group(1)),pcs=sorted(out))


# ----------------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------------
GUARD_TEXT=dict(G1.GUARD_TEXT)
LIMITATIONS=[
    'The frame passes (base 120 / 400 frames and RNG-initialised 400 frames), the node entry form (PC 2ab8, A6 = node, A7 = SPd, CCR 0) and the declared waits / bios-card answers are the scheduler observers declared models, not natural execution; no BIOS, IRQ or scheduler is claimed.',
    'The routing source parse of the scheduler observer cannot read the newest routing chain: the coverage flags use an all-routed bitmap and the 120 -> 400 frame extension is taken from the recorded base artifact (frames_done > 120); the recorded pass-end digests, stop reasons and frame counts of all 290 cases are compared with the artifacts (check.* in natural.seed_rows).',
    'An illegal opcode ABORTS the Unicorn m68k translator (process abort); the fixture search therefore runs in a forked child and poisons the aborting candidate (counted in the search rounds).',
    'The Unicorn SR read is stale for V / C (lazy flags); the observer reads the exact CCR with a MOVE SR,D0 probe at 500000 at every piece boundary and never from the Unicorn SR.',
    'Natural nodes: reference / continuous / independent model (PC + 16 registers per instruction) for every node, split for the sampled nodes (first node of every distinct callback / block path and a modular sample), twice for the sampled subset; the whole tool is run twice and the outputs are compared.',
    'The carry classification experiments run the block natively from a captured state with a declared CCR; blocks with no completed variant are listed as unobserved.',
    'Typed fixtures are declared states (natural capture + recorded edit list); kind entry-self / entry-declared means the search did not reach the block by a path within the budget and the fixture enters the block directly (entry-declared: node level form A7 = SPd-4, LONG 2ac2).',
    'The 44ade out-of-table D7 values 1 and fffc are guard probes (odd PC, watchdog); the model is compared only for the unit pieces.']


def claim(cid,text,expected,observed,verdict,note=''):return G1.claim(cid,text,expected,observed,verdict,note)


def dir_sizes(out_dir):return G1.dir_sizes(out_dir)


def build_report(env,args,a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,out_dir,t0,rom_start,dchk):
    cases=[b['case'] for b in b_list];nat=fs['nat'];cfg=fs['cfg'];ana=env.ana
    node_rows=[(b['case'],case_info(b['case'])[0],n) for b in b_list for n in b['nodes']]
    eqc=collections.Counter();modelc=collections.Counter();finalc=collections.Counter();guardc=collections.Counter();pieces=0;insns=0;xf=collections.Counter()
    nat_by_rec=collections.defaultdict(collections.Counter);hits_eq=collections.Counter();succ_nat=collections.defaultdict(collections.Counter)
    for case,rk,n in node_rows:
        for k,v in n['eq'].items():eqc[(k,v)]+=1
        modelc[n['model_ok']]+=1;finalc[n['final']]+=1;pieces+=len(n['pieces']);insns+=n['insns'];hits_eq[n['hits_eq']]+=1
        if n['guard']:guardc[n['guard']]+=1
        for pc in n['leaders_first']:nat_by_rec[rk][pc]+=1
        for u,last,to in n['xfers']:xf[(u,last,to)]+=1
        for k,v in n['succ'].items():succ_nat[rk][k]+=v
    sched_exit=collections.Counter(n['sched_exit_eq'] for case,rk,n in node_rows)
    banks=collections.Counter(G1.hx(n['bank']) for case,rk,n in node_rows);banks_seen=collections.Counter(G1.hx(b) for case,rk,n in node_rows for b in n['banks_seen']);pvc_nodes=sum(1 for case,rk,n in node_rows if n['bank_changes'])
    sampled=dict(nodes=len(node_rows),split=sum(1 for c,r,n in node_rows if 'cont_split' in n['eq']),twice=sum(1 for c,r,n in node_rows if 'cont_twice' in n['eq']),regtrace_all=True)
    ipcs=set()
    for b in b_list:ipcs.update(b['ipcs'])
    cb_total=G1.merge_counters(b['cb'] for b in b_list)
    seed_rows=[]
    for b in b_list:
        seed_rows.append(dict(case=b['case'],record=b['record'],seed=b['seed'],kind=b['kind'],family=b['family'],stop=b['stop'],frames_done=b['frames_done'],unit_nodes=b['unit_nodes'],run_digest=b['run_digest'],check=b['check'],
            prep=(b['prep'] and {k:b['prep'][k] for k in ('model_ok','instructions','exit_digest','write_count') if k in b['prep']}),
            eq_bad=sum(1 for n in b['nodes'] if not all(n['eq'].values())),model_bad=sum(1 for n in b['nodes'] if not n['model_ok']),exit_bad=sum(1 for n in b['nodes'] if not n['sched_exit_eq']),hits_bad=sum(1 for n in b['nodes'] if not n['hits_eq'])))
    rec_check=collections.Counter()
    for r in seed_rows:rec_check[(r['record'],bool(r['check']['tail_eq'] is not False and r['check']['stop_eq'] and r['check']['cb_eq'] and r['check']['frames'][0]==r['check']['frames'][1]))]+=1
    ok_rows=[r for r in rows if r['ok']];typed=set()
    for r in ok_rows:typed.update(r['reached'])
    kinds=collections.Counter(r['kind'] for r in rows)
    nat_guard_by_unit=collections.defaultdict(collections.Counter);typed_guard_by_unit=collections.defaultdict(collections.Counter)
    for case,rk,n in node_rows:
        if n['guard']:
            for uu in {env.starts[pc] for pc in n['leaders_first'] if pc in env.starts}:nat_guard_by_unit[uu][n['guard']]+=1
    for r in ok_rows:
        if r['final']=='guard':typed_guard_by_unit[r['unit']][r['final_detail']['kind']]+=1
    seg=collections.defaultdict(lambda:dict(natural_pieces=0,natural_insns=0,natural_bad=0,typed_pieces=0,typed_insns=0,typed_bad=0))
    for case,rk,n in node_rows:
        for pu,a,last,b,ni,ok in n['pieces']:
            d=seg[pu];d['natural_pieces']+=1;d['natural_insns']+=ni;d['natural_bad']+=0 if ok else 1
    for r in rows:
        for pu,a,last,b,ni,ok in r.get('pieces') or []:
            d=seg[pu];d['typed_pieces']+=1;d['typed_insns']+=ni;d['typed_bad']+=0 if ok else 1
    counts=G1.count_ranges(env);extra_derived,entries=fs['extra'],fs['entries_by_unit']
    units=[];discrep=[]
    for u in UIDS:
        c=env.contracts[u];st=c['starts'];cfgu=UNITS[u]
        nat_u=[pc for pc in st if pc in nat];typ_u=[pc for pc in st if pc in typed and pc not in nat];un=[pc for pc in st if pc not in nat and pc not in typed]
        mine_un=sorted(pc for pc in st if pc not in nat)
        by_rec={rk:len([pc for pc in st if pc in nat_by_rec[rk]]) for rk in ('base','rng','rng00')}
        union_rng=len([pc for pc in st if pc in nat_by_rec['rng'] or pc in nat_by_rec['rng00']])
        cu=contract_unreached_list(u,env);cmpu=None
        if cu is not None:
            only_c=sorted(set(cu['pcs'])-set(mine_un));only_m=sorted(set(mine_un)-set(cu['pcs']))
            cmpu=dict(stated=cu['stated'],listed=len(cu['pcs']),observed_unreached=len(mine_un),only_in_contract_list=[G1.hx(x) for x in only_c],only_in_observed=[G1.hx(x) for x in only_m],
                natural_records_of_contract_only={G1.hx(x):sorted(rk for rk in nat_by_rec if nat_by_rec[rk][x]) for x in only_c})
            if only_c or only_m or cu['stated']!=len(cu['pcs']):discrep.append(dict(id='%s-natural-unreached'%NAMES[u],claim='contract natural-unreached list (TB based scratch replay of the 142 base + RNG-80 seeds) vs instruction level replay of base + RNG + RNG answer-00',detail=cmpu))
        instr_ok=counts[u][0]==cfgu['insns']
        if not instr_ok:discrep.append(dict(id='%s-instructions'%NAMES[u],claim='contract instruction count vs model decoder',detail=dict(contract=cfgu['insns'],decoded=counts[u][0])))
        ops=counts[u][1];mul=ops.get('mulu',0)+ops.get('muls',0)
        want_mul=2 if u==17 else 0
        if mul!=want_mul:discrep.append(dict(id='%s-mul'%NAMES[u],claim='contract MULS / MULU count',detail=dict(contract=want_mul,rom=mul)))
        if u==17:
            muls_pcs=[pc for pc in sorted(env.cfg_all_ins[u]) if env.cfg_all_ins[u][pc]=='muls']
            if muls_pcs!=[0x443f8,0x443fc]:discrep.append(dict(id='U17-muls-pcs',claim='contract: MULS at 443f8 and 443fc',detail=[G1.hx(x) for x in muls_pcs]))
        if ops.get('trap',0):discrep.append(dict(id='%s-trap'%NAMES[u],claim='contract: no TRAP',detail=ops.get('trap')))
        evenpcs=sum((b-a)//2 for a,b in c['ranges'])
        if evenpcs!=cfgu['even']:discrep.append(dict(id='%s-even-pcs'%NAMES[u],claim='contract routing even PC count',detail=dict(contract=cfgu['even'],computed=evenpcs)))
        ex=extra_derived[u]
        if ex:discrep.append(dict(id='%s-cfg-leaders-not-in-contract'%NAMES[u],claim='decoder derived branch / fall-through / call targets inside the unit that the contract does not list as block starts',detail=[G1.hx(x) for x in ex]))
        trap_rows={};bnd={}
        for kind,pcs in BOUNDARY_NAMED.get(u,{}).items():
            for pc in pcs:
                fx_hit=[r['name'] for r in ok_rows if (r['final']=='stop' and r['final_detail'].get('pc')==pc) or any(x[2]==pc for x in r['xfers']) or any(x[2]==pc for x in (r.get('through') or {}).get('xfers',[]))][:3]
                installs=[s for s in st if pc in ana[s]['installs'] or pc in ana[s]['children']]
                bnd[G1.hx(pc)]=dict(kind=kind,natural_transfer=pc in fs['nat_xfer_to'],typed_fixtures=fx_hit,install_blocks=[G1.hx(s) for s in installs],
                    install_blocks_reached=[G1.hx(s) for s in installs if s in nat or s in typed])
        ext=collections.defaultdict(list)
        for s0 in st:
            for tg in ana[s0]['external']:ext[tg].append(s0)
        ext_rows={G1.hx(tg):dict(callers=[G1.hx(x) for x in sorted(v)],target_unit=NAMES.get(env.unit_of(tg),'outside the G2 units')) for tg,v in sorted(ext.items())}
        for kind,pcs in BOUNDARY_NAMED.get(u,{}).items():
            for pc in pcs:
                found=(pc in ext) if kind=='callee' else any(pc in ana[s0]['installs'] or pc in ana[s0]['children'] for s0 in st)
                if not found:discrep.append(dict(id='%s-boundary-%x'%(NAMES[u],pc),claim='contract names %x as a %s boundary of the unit; no instruction of the unit transfers to / installs it'%(pc,kind),detail=G1.hx(pc)))
        cons=sorted(s for s in env.consumers if env.starts[s]==u);prods=sorted(c['lists']['producers'])
        units.append(dict(unit=NAMES[u],contract=contract_path(u).name,contract_sha=c['sha'],ranges=[[G1.hx(a),G1.hx(b)] for a,b in c['ranges']],code_bytes=c['bytes'],instructions=counts[u][0],instructions_contract=cfgu['insns'],
            ops=counts[u][1],blocks_expected=cfgu['starts'],blocks_parsed=len(st),blocks_stated=c['stated_blocks'],parse_notes=c['notes'],natural_reached=len(nat_u),natural_reached_by_record=by_rec,natural_reached_rng_union=union_rng,typed_only_reached=len(typ_u),
            model_segments=dict(seg[u]),guards=dict(natural=dict(nat_guard_by_unit[u]),typed=dict(typed_guard_by_unit[u])),union_reached=len(nat_u)+len(typ_u),unreached=[G1.hx(x) for x in un],natural_unreached=[G1.hx(x) for x in mine_un],typed_by_kind={},boundary=bnd,compare_contract_unreached=cmpu,
            cfg_entries_not_derived=[G1.hx(x) for x in entries[u]],external_targets=ext_rows,flow_only=len(c['lists']['flow'] or []),producers={G1.hx(k):v for k,v in c['lists']['producers'].items()},consumers=[G1.hx(x) for x in cons],
            natural_nodes_per_start={G1.hx(pc):sum(nat_by_rec[rk][pc] for rk in nat_by_rec) for pc in nat_u}))
    for r in ok_rows:
        for pc in r['reached']:
            u=env.starts.get(pc)
            if u and pc not in nat:
                d=units[UIDS.index(u)]['typed_by_kind'];d.setdefault(r['kind'],[]).append(G1.hx(pc))
    for d in units:
        for k in d['typed_by_kind']:d['typed_by_kind'][k]=sorted(set(d['typed_by_kind'][k]))
    # jump table summary
    jt=[r for r in rows if r['kind']=='jump-table'];jt_idx=sorted({int(r['tag'][3:],16) for r in jt if r['ok']})
    jt_summary=dict(fixtures=len(jt),ok=sum(1 for r in jt if r['ok']),indexes_ok=len(jt_idx),entries_reached=len({0x44ae2+4*k for k in jt_idx}&{p for r in jt if r['ok'] for p in r['reached']}),
        leaf_targets_reached=len({p for r in jt if r['ok'] for p in r['reached'] if env.starts.get(p)==20 and not (0x44ae2<=p<0x44c62 and (p-0x44ae2)%4==0)}),
        edge=[dict(name=r['name'],final=r['final'],final_detail=r['final_detail'],ok=r['ok']) for r in rows if r['kind']=='jump-table-edge'])
    # consumers: declared CCR outcomes, natural and typed real-producer pairs
    cons_rows=[];succ_typed=collections.Counter();succ_nat_all=collections.Counter()
    for rk in succ_nat:succ_nat_all.update(succ_nat[rk])
    for r in ok_rows:
        if r['kind']!='carry-consumer':
            for k,v in r['succ'].items():succ_typed[k]+=v
            for k,v in ((r.get('through') or {}).get('succ') or {}).items():succ_typed[k]+=v
    declared=collections.defaultdict(dict)
    for r in rows:
        if r['kind']=='carry-consumer':
            s=r['targets'][0];ccr=int(r['tag'][3:],16);nxt=[k.split('>')[1] for k in r['succ'] if k.startswith('%x>'%s)]
            declared[s][ccr]=dict(next=(nxt[0] if nxt else None),final=r['final'],ok=r['ok'])
    for s in sorted(env.consumers):
        d=declared.get(s,{});c0=d.get(0x00,{}).get('next');c1=d.get(0x01,{}).get('next');c2=d.get(0x1e,{}).get('next');c3=d.get(0x1f,{}).get('next')
        nat_pairs={k:v for k,v in succ_nat_all.items() if k.startswith('%x>'%s)}
        typed_pairs={k:v for k,v in succ_typed.items() if k.startswith('%x>'%s)}
        chain={k:succ_nat_all.get(k,0)+succ_typed.get(k,0) for k in set(succ_nat_all)|set(succ_typed) if k.startswith('p') and k.split('>')[1]=='%x'%s}
        row=dict(consumer=G1.hx(s),unit=NAMES[env.starts[s]],declared={('%02x'%k):v for k,v in sorted(d.items())},c_only_dependence=(c0==c2 and c1==c3),outcomes_differ=(c0!=c1),
            contract_listed=s in env.contract_consumers,model_derived=s in env.model_consumers,natural_pairs=nat_pairs,typed_real_producer_pairs=typed_pairs,producer_chains=chain)
        cons_rows.append(row)
        if not row['c_only_dependence'] or not row['outcomes_differ']:discrep.append(dict(id='%s-consumer-%x'%(NAMES[env.starts[s]],s),claim='consumer outcome depends on C only (declared CCR 00/01/1e/1f, native branch)',detail=row['declared']))
    # list differences of consumers between the contract and the independent model
    for s in sorted(env.model_consumers-env.contract_consumers):discrep.append(dict(id='%s-consumer-unlisted'%NAMES[env.starts[s]],claim='model finds a C consumer the contract does not list',detail=G1.hx(s)))
    for s in sorted(env.contract_consumers-env.model_consumers):discrep.append(dict(id='%s-consumer-not-model'%NAMES[env.starts[s]],claim='contract lists a consumer the model does not find',detail=G1.hx(s)))
    # other flags consumed from the caller
    oth=[(G1.hx(s),a['consumes']) for s,a in sorted(ana.items()) if a['consumes'] not in(None,'C')]
    if oth:discrep.append(dict(id='flags-consumed-from-caller',claim='blocks that read N/Z/V before writing them (contract: every block makes and uses its own flags)',detail=oth))
    u20sem,u20disc=u20_semantic_check(env,rows);discrep.extend(u20disc)
    btext,bdisc=block_text_check(env);discrep.extend(bdisc)
    csstats,csdisc=call_site_check(env);discrep.extend(csdisc)
    xrows,xdisc=xref_check(env.program);discrep.extend(xdisc)
    nvc,nvdisc=natural_vs_contract(env,nat_by_rec);discrep.extend(nvdisc)
    # producer chains: observed (natural + typed) outcomes per known producer, checked against the declared-CCR outcome of the consumer for the producer's claimed C
    chain_obs=collections.defaultdict(collections.Counter)
    for k,v in list(succ_nat_all.items())+list(succ_typed.items()):
        if k.startswith('p'):
            a,b,c3=k.split('>');chain_obs[(int(a[1:],16),int(b,16))][c3]+=v
    producer_chains=[]
    for u in UIDS:
        for p,w in sorted(env.contracts[u]['lists']['producers'].items()):
            row=dict(producer=G1.hx(p),unit=NAMES[u],claim=w,consumers=[])
            for cs in PRODUCER_CONSUMERS.get(p,()):
                dec=declared.get(cs,{});want=dec.get(0x00 if w=='Clear' else 0x01,{}).get('next');seen=dict(chain_obs.get((p,cs),{}))
                allowed={want};lastins=new_model(env).decode(env.cfg[cs]['insns'][-1])
                if lastins.op=='dbcc' and ((lastins.cond==5 and w=='Clear') or (lastins.cond==4 and w=='Set')):
                    allowed.add(dec.get(0x01 if w=='Clear' else 0x00,{}).get('next'))                 # DBcc with a false condition: the counter decides between the loop and the fall-through
                row['consumers'].append(dict(consumer=G1.hx(cs),expected_next=sorted(x for x in allowed if x),observed=seen,evidence=sum(seen.values()),consistent=all(k in allowed for k in seen),dbcc_counter=lastins.op=='dbcc'))
                if seen and not all(k in allowed for k in seen):discrep.append(dict(id='%s-producer-%x'%(NAMES[u],p),claim='known carry producer %x claims C=%s: the native branch outcome at consumer %x through the real producer differs from the declared-CCR outcome'%(p,w,cs),detail=dict(expected=sorted(x for x in allowed if x),observed=seen)))
            producer_chains.append(row)
    # bank sweep
    bank_rows=[r for r in rows if r['kind']=='pvc-bank'];bsum=collections.defaultdict(collections.Counter)
    for r in bank_rows:bsum[r['tag']]['%s%s'%(r['final'],('/'+r['final_detail'].get('kind','')) if r['final']=='guard' else '')]+=1
    # guards
    gsum=collections.Counter()
    for r in ok_rows:
        if r['final']=='guard':gsum[(NAMES.get(r['unit'],r['unit']),r['final_detail']['kind'])]+=1
    gfam=collections.Counter()
    for r in rows:
        if r['kind']=='guard-family':gfam[(r['tag'],r['final'],r['final_detail'].get('kind') if r['final']=='guard' else '')]+=1
    # claims
    claims=[]
    for u in UIDS:
        c=env.contracts[u];n=UNITS[u]['name'];e=UNITS[u]['starts']
        claims.append(claim('%s-blocks'%n,'contract block start count (parsed block list)',e,len(c['starts']),'matches' if len(c['starts'])==e==c['stated_blocks'] else 'differs'))
        claims.append(claim('%s-instructions'%n,'contract instruction count decoded by the observer model decoder',UNITS[u]['insns'],counts[u][0],'matches' if counts[u][0]==UNITS[u]['insns'] else 'differs'))
    claims.append(claim('NAT-record','recorded scheduler artifacts reproduced: frames, stop reason, callback counts and (where recorded) the last pass-end digests of every case',len(seed_rows),sum(v for (rk,ok),v in rec_check.items() if ok),'matches' if all(ok for (rk,ok) in rec_check) else 'differs'))
    claims.append(claim('NAT-nodes','every natural unit node: fresh-CPU ref == continuous (all), == split (%d nodes), twice (%d), scheduler exit reproduced, model equal on every unit piece (PC + registers per instruction), run-hook hits == replay leaders'%(sampled['split'],sampled['twice']),len(node_rows),
        dict(ref_cont=eqc[('ref_cont',True)],cont_split=eqc[('cont_split',True)],sched_exit=sched_exit[True],model=modelc[True],hits=hits_eq[True]),
        'matches' if all(eqc[(k,False)]==0 for k in ('ref_cont','cont_split','cont_twice','split_twice')) and sched_exit[False]==0 and modelc[False]==0 and hits_eq[False]==0 else 'differs'))
    claims.append(claim('TYPED-all-blocks','every contract block start reached naturally or by a typed fixture','0 unreached',sum(len(d['unreached']) for d in units),'matches' if not any(d['unreached'] for d in units) else 'differs'))
    claims.append(claim('TYPED-fixtures','typed fixtures: fresh-CPU ref == continuous == split, each twice, model equal on every unit piece',len(rows),len(ok_rows),'matches' if len(ok_rows)==len(rows) else 'differs',
        json.dumps([r['name'] for r in rows if not r['ok']][:20])))
    claims.append(claim('TYPED-jump-table','all 96 indexes of the 44ade table reached by a native fixture',96,jt_summary['indexes_ok'],'matches' if jt_summary['indexes_ok']==96 else 'differs'))
    claims.append(claim('DATA-contract-values','contract data values (banked LONGs, fixed tables) equal the ROM bytes',len(dchk),sum(1 for x in dchk if x['ok']),'matches' if all(x['ok'] for x in dchk) else 'differs'))
    for x in dchk:
        if not x['ok']:discrep.append(dict(id='%s-data'%x['unit'],claim='contract data value vs ROM bytes',detail=x))
    sizes=dir_sizes(out_dir)
    report=dict(schema_version=1,tool='tools/observe_animation_machine_objects_g2.py',scope=__doc__,rom_stat_start=rom_start,limitations=LIMITATIONS,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000'),
        declared_model=dict(spd=SPD,pass_pc=PASS_PC,node_entry='PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd, CCR 0',stops='2ac2 (natural) / 2ac2, 2a00 and the boundary callees (fixtures; boundary stops are followed by a through run)',nat_limit=NAT_LIMIT,fix_limit=GLOBAL['fix_limit'],
            probe='CCR probe: MOVE SR,D0 at 500000 (exact flags; a plain SR read is stale for V / C)',waits='sound 3aea / sprite cda4 declared releases as the scheduler observer; bios-card answer 80 (RNG record) and 00 (variants of seeds 0..5)',
            bank_model='observe_animation_machine_pvc_banks.PvcMachine (any PVC selectable bank; bank-read-outside-rom guard)',records=dict(base_frames=BASE_FRAMES,rng_frames=RNG_FRAMES,base_artifact=GLOBAL['records']['base_sha'],rng_artifact=GLOBAL['records']['rng_sha']),
            rng_seed_prep='original 49a1a natively with D0 = 0 (R.run_prep, declared RAM change; registers stay the seed registers)'),
        inputs=dict(contracts={contract_path(u).name:UNITS[u]['sha'] for u in UIDS},tools={n:sha((ROOT/'tools'/n).read_bytes()) for n in ('observe_animation_machine_objects_g2.py','observe_animation_machine_objects_g1.py','observe_animation_machine_scheduler.py','observe_animation_machine_scheduler_rng.py','observe_animation_machine_pvc_banks.py','address_map.py','disassemble_program.py')}),
        units=units,
        natural=dict(cases=len(cases),by_record=dict(collections.Counter(b['record'] for b in b_list)),seed_stop_reasons={'%s/%s'%k:v for k,v in sorted(collections.Counter((b['record'],b['stop'].get('reason')) for b in b_list).items())},unit_nodes=len(node_rows),unit_nodes_by_record=dict(collections.Counter(rk for c,rk,n in node_rows)),replays=sampled,record_check={'%s/%s'%k:v for k,v in sorted(rec_check.items())},
            final_banks=dict(banks),banks_selected_by_pvc_writes_natural=dict(banks_seen),banks_selected_by_pvc_writes_typed=dict(collections.Counter(G1.hx(b) for r in rows for b in r.get('pvc_banks',[]))),nodes_with_pvc_writes=pvc_nodes,
            guard_explanations=GUARD_TEXT,pieces=pieces,unit_instructions=insns,distinct_unit_instruction_pcs=len(ipcs),total_unit_instructions=sum(counts[u][0] for u in counts),eq={('%s=%s'%k):v for k,v in sorted(eqc.items())},
            model_ok=dict(modelc),sched_exit_eq=dict(sched_exit),hits_eq=dict(hits_eq),final=dict(finalc),guards=dict(guardc),callbacks_hex=S.hexkeys(cb_total),seed_rows=seed_rows,
            consumer_pairs_natural={rk:dict(v) for rk,v in succ_nat.items()},xfers=[dict(unit=NAMES.get(u,u),last=G1.hx(l) if l else None,to=G1.hx(t),count=n) for (u,l,t),n in sorted(xf.items(),key=lambda kv:(kv[0][0],kv[0][1] or 0,kv[0][2]))]),
        typed=dict(fixtures=len(rows),ok=len(ok_rows),skipped_optional=[r['name'] for r in rows if r.get('skipped')],by_kind=dict(kinds),jump_table=jt_summary,u20a_semantics=u20sem,block_text_vs_rom=btext,call_sites_vs_rom=csstats,static_callers_vs_rom=xrows,natural_vs_contract=nvc,producer_chains=producer_chains,consumers=cons_rows,bank_sweep={k:dict(v) for k,v in sorted(bsum.items())},bank_sweep_banks=[[n,G1.hx(b[0]),G1.hx(b[1]),G1.hx(b[2])] for n,b in BANK_SWEEP],
            guards_by_unit_kind={('%s/%s'%k):v for k,v in sorted(gsum.items(),key=lambda kv:str(kv[0]))},guard_families={('%s|%s|%s'%k):v for k,v in sorted(gfam.items())},
            failure_28ae=[dict(name=r['name'],final=r['final'],leaders=[G1.hx(x) for x in r['leaders_first'][:12]]) for r in rows if r['kind'].startswith('28ae')],
            search_rounds=fs['rounds'],fallback_entry=[G1.hx(x) for x in fs['fallback']],jump_table_reached_starts=len(fs['jt_reached'])),
        carry_classification=carry,data_checks=dchk,discrepancies=discrep+cdisc,claims=claims,output_sizes=sizes)
    return report


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(OUT));ap.add_argument('--workers',type=int,default=3);ap.add_argument('--cases',default='')
    ap.add_argument('--budget',type=int,default=6000);ap.add_argument('--natural-only',action='store_true')
    ap.add_argument('--stash',default='',help='development: pickle the stage results here');ap.add_argument('--load-stash',default='',help='development: skip the stages, load a stash and build the report only')
    args=ap.parse_args(argv);out_dir=Path(args.out).resolve();t0=time.time()
    rom_start=S.rom_stat();assert rom_start['sha256']==ROM_SHA
    if out_dir.exists() and any(out_dir.iterdir()):raise SystemExit('output directory is not empty: %s'%out_dir)
    (out_dir/'blobs').mkdir(parents=True,exist_ok=True);(out_dir/'seeds').mkdir(exist_ok=True)
    program=setup_sched();env=Env2();records=load_records();analyze_units(env)
    GLOBAL.update(env=env,program=program,out=out_dir,fix_limit=20_000,plan={},twice=False,records=records)
    cases=case_list() if not args.cases else [int(x) for x in args.cases.split(',')]
    if args.load_stash:
        import pickle
        with open(args.load_stash,'rb') as f:a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,fx_sha,fx_size=pickle.load(f)
    else:
        a_list,b_list,first_start=stage_natural(env,args,out_dir,cases)
        print('natural done',round(time.time()-t0),sum(b['unit_nodes'] for b in b_list),flush=True)
        for b in b_list:
            doc=dict(case=b['case'],record=b['record'],seed=b['seed'],kind=b['kind'],family=b['family'],stop=b['stop'],frames_done=b['frames_done'],meta=b['meta'],prep=b['prep'],run_digest=b['run_digest'],check=b['check'],nodes=b['nodes'],waits=b['waits'],
                cb=S.hexkeys(b['cb']),unit_nodes=b['unit_nodes'],ipcs=b['ipcs'])
            S.write_gz(out_dir/'seeds'/('case_%04d.json.gz'%b['case']),doc)
        if args.natural_only:return a_list,b_list
        fs=stage_fixtures(env,args,b_list,out_dir)
        print('fixture search done',round(time.time()-t0),len(fs['recipes']),'fallback',len(fs['fallback']),'jump table fixtures',len(fs['jt_rows']),flush=True)
        rows,fixtures,gres=stage_verify(env,args,fs,b_list,out_dir)
        rows=fs['jt_rows']+rows
        print('fixtures done',round(time.time()-t0),len(rows),sum(1 for r in rows if r['ok']),flush=True)
        fx_sha,fx_size=S.write_gz(out_dir/'fixtures.json.gz',dict(note='typed fixtures: declared edits over captured natural states, results of ref / continuous / split (each twice) and the model',fixtures=rows))
        carry,cdisc,cobs=stage_carry(env,args,fs)
        print('carry done',round(time.time()-t0),flush=True)
        if args.stash:
            import pickle
            with open(args.stash,'wb') as f:pickle.dump((a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,fx_sha,fx_size),f,protocol=4)
    dchk=data_checks(program)
    report=build_report(env,args,a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,out_dir,t0,rom_start,dchk)
    rom_end=S.rom_stat();assert rom_end==rom_start
    report['rom_stat_end']=rom_end;report['fixtures_file']=dict(file='fixtures.json.gz',sha256=fx_sha,size=fx_size)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(units=[(d['unit'],d['blocks_parsed'],d['natural_reached'],d['typed_only_reached'],len(d['unreached'])) for d in report['units']],nodes=report['natural']['unit_nodes'],fixtures=(report['typed']['fixtures'],report['typed']['ok']),
        claims_differ=[c['id'] for c in report['claims'] if c['verdict']=='differs'],discrepancies=len(report['discrepancies']),size_mb=round(dir_sizes(out_dir)['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True))
    return summary



# ----------------------------------------------------------------------------------
# U20a contract semantics (tables of the contract text) as an algorithmic model of the 76 jump-table leaves, compared with the native fixtures
# ----------------------------------------------------------------------------------
def parse_u20_tables(env):
    t=env.contracts[20]['text'];sec=section(t,'## 점프 표 `44ade`와 index 상한(결정 4)')
    targets={}
    for m in re.finditer(r'^\s*- `([0-9a-f]{2})\.\.([0-9a-f]{2})`: ([^\n]*)',sec,re.M):
        lo=int(m.group(1),16);vals=[int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',m.group(3))]
        for i,v in enumerate(vals):targets[lo+i]=v
    sec2=section(t,'## block 목록과 실행 의미')
    slope={};rng={}
    def imm(c):
        c=c.strip().strip('`');return None if c in('없음','') else int(c,16)
    for ln in sec2.splitlines():
        if not ln.startswith('|'):continue
        cells=[c.strip() for c in ln.strip().strip('|').split('|')]
        m=re.match(r'^`([0-9a-f]{5})`$',cells[0])
        if not m:continue
        pc=int(m.group(1),16)
        if len(cells)==4:slope[pc]=dict(sub=imm(cells[1]),asr=None if cells[2]=='없음' else int(cells[2]),comb=cells[3])
        elif len(cells)==7:rng[pc]=dict(sub=imm(cells[1]),lim=imm(cells[2]),br=cells[3],tail=int(cells[4].strip('`'),16),lsl=int(cells[5]),comb=cells[6])
    return targets,slope,rng


def u20_leaf_model(env,tables,t,d0,d1,d2,a549e):
    """Expected (D6, D4 or None, ends_at) of the leaf at table target t from the contract tables.  d0/d1/d2: LONG register values.  Returns None for a leaf the tables do not describe."""
    targets,slope,rng=tables;M=M32
    if t==0x44c62:return (0x80000000,None,'44c62')
    if t==0x44c6a:
        if d2&0x80000000:return u20_leaf_model(env,tables,0x44c80,d0,d1,d2,a549e)
        return u20_leaf_model(env,tables,0x44c70,d0,d1,d2,a549e)
    if t==0x44c70:return (0x80000000,None,'44c62') if a549e else (d0&0x7ffff,None,'44c76')
    if t==0x44c76:return (d0&0x7ffff,None,'44c76')
    if t==0x44c80:
        if a549e:return (0x80000000,None,'44c62')
        d4=0xfff80000;return (((d0&0x7ffff)+d4)&M,d4,'44c86')
    if t in slope:
        p=slope[t];d4=d1&0x7ffff
        if p['sub'] is not None:d4=(d4-p['sub'])&M
        if p['asr']:
            d4=((d4 if d4<0x80000000 else d4-(1<<32))>>p['asr'])&M
        d6=(d0&0x7ffff);d6=(d6-d4)&M if p['comb']=='SUB' else (d6+d4)&M
        return (d6,d4,'slope')
    if t in rng:
        p=rng[t];d4=d1&0x7ffff
        if p['sub'] is not None:d4=(d4-p['sub'])&M
        out=(d4>=p['lim']) if p['br']=='BCC' else (d4<p['lim'])
        if out:return (0x80000000,d4,'44c62')   # the head branches to 44c62: D6 := 80000000, D4 keeps the head value
        d4=(d4<<p['lsl'])&M
        d6=0x7ffff&d0;d6=(d6-d4)&M if p['comb']=='SUB' else (d6+d4)&M
        return (d6,d4,'tail')
    return None


def u20_semantic_check(env,rows):
    """Compare the contract's jump-table targets and leaf formulas with the native fixtures.  Returns (summary, discrepancies)."""
    tables=parse_u20_tables(env);targets,slope,rng=tables;disc=[];mdl=new_model(env)
    rom_targets={k:mdl.decode(0x44ae2+4*k).target for k in range(0x60)}
    bad_t=[(k,G1.hx(targets.get(k) or 0),G1.hx(rom_targets[k])) for k in range(0x60) if targets.get(k)!=rom_targets[k]]
    if len(targets)!=0x60 or bad_t:disc.append(dict(id='U20a-table-targets',claim='contract index -> target lists vs the BRA.W of the ROM table',detail=dict(parsed=len(targets),mismatch=bad_t[:10])))
    n=0;bad=[];cmp_n=0;seen_leaf=set()
    for r in rows:
        if r['kind']!='jump-table' or not r['ok']:continue
        k=int(r['tag'][3:],16);t=rom_targets[k];seen_leaf.add(t)
        st_regs=r['edits']['regs'];fin=r['dumps'][-1]['regs'] if r.get('dumps') else None
        if fin is None:continue
        d0=int(st_regs.get('d0','0'),16);d1=int(st_regs.get('d1','0'),16);d2=int(st_regs.get('d2','0'),16)
        a549e=None
        for a,v in r['edits']['ram']:
            if int(a,16)==(0x108000+0x549e)&0xffff:a549e=v
        exp=u20_leaf_model(env,tables,t,d0,d1,d2,a549e or 0)
        n+=1
        if exp is None:bad.append((r['name'],'no formula'));continue
        cmp_n+=1
        d6=fin['d6'];
        if d6!=exp[0] or (exp[1] is not None and fin['d4']!=exp[1]):bad.append((r['name'],dict(d6=G1.hx(d6),exp_d6=G1.hx(exp[0]),d4=G1.hx(fin['d4']),exp_d4=None if exp[1] is None else G1.hx(exp[1]))))
    if bad:disc.append(dict(id='U20a-leaf-formulas',claim='contract leaf formulas (slope / range tables) vs native D6 / D4 of the jump-table fixtures',detail=bad[:20]))
    return dict(parsed_targets=len(targets),slope_leaves=len(slope),range_heads=len(rng),fixtures_compared=cmp_n,mismatches=len(bad),leaf_targets_seen=len(seen_leaf)),disc


# ----------------------------------------------------------------------------------
# Contract block text vs the decoded ROM instructions (mnemonic + size of every instruction of every block whose contract line spells the instructions out)
# ----------------------------------------------------------------------------------
CONDS=('T','F','HI','LS','CC','CS','NE','EQ','VC','VS','PL','MI','GE','LT','GT','LE')
SZCH={1:'B',2:'W',4:'L'}
MACRO_BANK_T=['LEA','MOVE.W','MOVE.L','MOVEA.L','ADD.W','ADD.W','MOVE.L','MOVEA.L','ADD.W','ADD.W','MOVEA.L','MOVE.W','JSR']
MACRO_BANK_D=['LEA','MOVE.W','MOVE.L','MOVE.W','LEA','MOVEA.L','MOVEA.L','JSR']
MACRO_ANIM_INDEX=['LEA','MOVE.W','MOVE.L','LEA','@MOVE.W','ADD.W','ADD.W','MOVEA.L','MOVEA.L','MOVE.W','JSR']


def render_ins(ins):
    op=ins.op;sz=ins.size
    simple={'move':'MOVE','movea':'MOVEA','moveq':'MOVEQ','lea':'LEA','jsr':'JSR','jmp':'JMP','rts':'RTS','bsr':'BSR','bra':'BRA','addq':'ADDQ','subq':'SUBQ','addi':'ADDI','subi':'SUBI','cmpi':'CMPI','andi':'ANDI','ori':'ORI','eori':'EORI',
        'add':'ADD','sub':'SUB','cmp':'CMP','and':'AND','or':'OR','eor':'EOR','adda':'ADDA','suba':'SUBA','cmpa':'CMPA','mulu':'MULU','muls':'MULS','neg':'NEG','not':'NOT','clr':'CLR','tst':'TST','swap':'SWAP','ext':'EXT','exg':'EXG','movem':'MOVEM','trap':'TRAP'}
    if op in simple:
        if op in('jsr','jmp','rts','lea','swap','moveq','exg','trap'):return simple[op],None
        if op in('bsr','bra'):return simple[op],('W' if ins.len==4 else 'B')
        return simple[op],SZCH.get(sz)
    if op=='bcc':return 'B'+CONDS[ins.cond],('W' if ins.len==4 else 'B')
    if op=='dbcc':return 'DB'+CONDS[ins.cond],None
    if op=='scc':return 'S'+CONDS[ins.cond],'B'
    if op=='bit':return ('BTST','BCHG','BCLR','BSET')[ins.aux],'B'
    if op=='shift':return ('AS','LS')[ins.aux]+('L' if ins.imm else 'R'),SZCH.get(ins.size)
    if op in('andccr','orccr','eorccr'):return {'andccr':'ANDI','orccr':'ORI','eorccr':'EORI'}[op],'B'
    return op.upper(),None


def parse_block_texts(u,t):
    """pc -> list of 'MNEMONIC[.SZ]' strings (None entries: skipped)."""
    sec=section(t,'## block 목록');out={}
    for ln in sec.splitlines():
        parts=list(re.finditer(r'`([0-9a-f]{3,6})`(?: \([^)]*\))?: ',ln))
        for i,m in enumerate(parts):
            pc=int(m.group(1),16);seg=ln[m.end():(parts[i+1].start() if i+1<len(parts) else len(ln))]
            sp=re.match(r'^`([^`]*)`',seg)
            macro=None
            for nm,exp in (('bankT(',MACRO_BANK_T),('bankD(',MACRO_BANK_D),('animation-index(',MACRO_ANIM_INDEX),('animation(',MACRO_BANK_D)):
                if nm in seg:macro=exp;break
            if macro is not None:
                pre=[x.strip() for x in sp.group(1).split(';') if x.strip()] if (sp and not seg.startswith(('bank','animation'))) else []
                exp=[('MOVE.W' if x=='@MOVE.W' else x) for x in macro if not (x=='@MOVE.W' and 'MOVE.W D0,D1' not in seg)]
                out[pc]=[mn_of(x) for x in pre]+exp
            elif sp and ('와 같' not in seg):
                out[pc]=[mn_of(x) for x in sp.group(1).split(';') if x.strip()]
    return out


def mn_of(x):
    x=x.strip();m=re.match(r'^([A-Z]+)(?:\.([BWL]))?',x)
    if not m:return '?'
    return m.group(1)+('.'+m.group(2) if m.group(2) else '')


def block_text_check(env):
    """Returns (per-unit stats, discrepancies)."""
    stats={};disc=[]
    for u in UIDS:
        c=env.contracts[u];texts=parse_block_texts(u,c['text']);cmp_n=0;bad=[]
        for s in c['starts']:
            if s not in texts:continue
            mdl=new_model(env);dec=[render_ins(mdl.decode(pc)) for pc in env.cfg[s]['insns']]
            exp=texts[s]
            if '?' in exp:continue                                    # shorthand lines ("same as ..."): not comparable
            # the contract may describe a block with its fall-through / split Bcc lines (e.g. one line for two ROM blocks): only equal length lists are compared strictly
            def eq(e,d):
                mn,sz=d
                if e==mn:return True
                if '.' in e:
                    en,es=e.split('.');return en==mn and (sz is None or es==sz)
                return False
            got=[mn+('.'+sz if sz else '') for mn,sz in dec]
            ok=len(exp)==len(dec) and all(eq(e,d) for e,d in zip(exp,dec))
            cmp_n+=1
            if not ok:bad.append(dict(start=G1.hx(s),contract=exp,rom=got))
        stats[NAMES[u]]=dict(blocks_with_text=len(texts),compared=cmp_n,mismatches=len(bad))
        if bad:disc.append(dict(id='%s-block-text'%NAMES[u],claim='contract block line (mnemonic + size per instruction) vs the instructions decoded from the ROM bytes',detail=bad[:40]))
    return stats,disc


# ----------------------------------------------------------------------------------
# Static caller counts of the contracts ("참조": N곳) against a scan of the whole fixed program ROM for JSR / JMP / BSR / BRA to the target
# ----------------------------------------------------------------------------------
XREF_EXPECT=[(17,0x1c5ea,1),(17,0x482c0,6),(17,0x4c020,3),(17,0x443ea,16),(17,0x491c4,79),(17,0x4929e,16),(17,0x4bfa4,105),
    (18,0x46c68,2),(18,0x4be2c,145),(18,0xb7bc2,8),(18,0xb7cfa,12),(18,0xb7e06,9),(18,0xb7e5c,3),(18,0xea5e0,4),(18,0xea65a,3),(18,0xea762,4),(18,0xb76d2,12),
    (19,0x484e2,3),(19,0xb7b4c,2),(19,0xb7c9e,1),(19,0xb7b30,2),(19,0xd83c0,1),(19,0xe9112,48),(20,0x492d0,56),(20,0x497a6,23),(20,0x44ade,2),(21,0x849f4,18)]


def xref_scan(prog):
    cnt=collections.defaultdict(collections.Counter)
    for o in range(0,0x100000-6,2):
        w=(prog[o]<<8)|prog[o+1]
        if w in(0x4eb9,0x4ef9):cnt[int.from_bytes(prog[o+2:o+6],'big')]['jsr.l' if w==0x4eb9 else 'jmp.l']+=1
        elif w in(0x4eba,0x4efa):cnt[(o+2+sx16((prog[o+2]<<8)|prog[o+3]))&M32]['jsr.pc' if w==0x4eba else 'jmp.pc']+=1
        elif (w>>8) in(0x60,0x61):
            d=w&0xff
            if d==0xff:continue
            if d==0:t=o+2+sx16((prog[o+2]<<8)|prog[o+3]);k='w'
            else:t=o+2+(d-256 if d&0x80 else d);k='b'
            cnt[t][('bsr' if (w>>8)==0x61 else 'bra')+'.'+k]+=1
    return cnt


def xref_check(prog):
    cnt=xref_scan(prog);rows=[];disc=[]
    for u,t,n in XREF_EXPECT:
        c=cnt[t];tot=sum(c.values());rows.append(dict(unit=NAMES[u],target=G1.hx(t),contract=n,rom=tot,forms=dict(c),ok=tot==n))
        if tot!=n:disc.append(dict(id='%s-xref-%x'%(NAMES[u],t),claim='contract static caller count vs scan of the fixed program ROM (JSR/JMP/BSR/BRA forms)',detail=rows[-1]))
    return rows,disc



# ----------------------------------------------------------------------------------
# Contract call-site lists ("기존 실행부로 나가는 호출") vs the control transfers found in the ROM bytes
# ----------------------------------------------------------------------------------
def parse_call_sites(t):
    """target -> dict(group=<targets sharing the list>, sites=<pcs>, count=<stated 'N곳' or None>, fall=<'fall-through' note>)."""
    m=re.search(r'^- \[F\] 기존 실행부로 나가는 호출[^\n]*',t,re.M)
    if not m:return None
    line=m.group(0)
    for k in ('U17 안 호출','U18 안 호출','U19 안 호출'):
        if k in line:line=line[:line.index(k)]
    out={};pending=[]
    for mt in re.finditer(r'`([0-9a-f]{3,6})`(?:\(([^)]*)\))?',line):
        tg=int(mt.group(1),16)
        if mt.group(2) is None:pending.append(tg);continue
        body=mt.group(2);sites=[int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})(?: [^`]*)?`',body)];cm=re.search(r'(\d+)곳',body)
        grp=pending+[tg]
        for q in grp:out[q]=dict(group=grp,sites=set(sites),count=int(cm.group(1)) if cm else None,fall='fall-through' in body)
        pending=[]
    return out


def call_site_check(env):
    blk={}
    for s,b in env.cfg.items():
        for pc in b['insns']:blk[pc]=s
    actual=collections.defaultdict(lambda:collections.defaultdict(set))
    for s,b in env.cfg.items():
        u=b['unit'];mdl=new_model(env)
        for pc in b['insns']:
            ins=mdl.decode(pc);tg=None
            if ins.op in('bra','bsr','bcc','dbcc'):tg=ins.target
            elif ins.op in('jsr','jmp') and ins.src[0] in('abs','pcd16'):tg=ins.src[1]
            if tg is not None:actual[u][tg].add(pc)
    stats={};disc=[]
    for u in UIDS:
        cs=parse_call_sites(env.contracts[u]['text'])
        if cs is None:stats[NAMES[u]]=dict(parsed=False);continue
        bad=[];ok=0;done=set()
        for tg,info in sorted(cs.items()):
            if tg in done:continue
            grp=[q for q in info['group']];done.update(grp)
            cb={blk.get(x,x) for x in info['sites']};ab={blk[x] for q in grp for x in actual[u].get(q,())}
            if info['fall']:                                  # "(4be2c fall-through)": the contract names a block that falls through into the target, not a transfer
                ok+=1;continue
            if not info['sites'] and info['count'] is not None:
                if info['count']==len(ab):ok+=1
                else:bad.append(dict(target='/'.join(G1.hx(q) for q in grp),contract_count=info['count'],rom_blocks=len(ab),rom_blocks_list=sorted(G1.hx(x) for x in ab)))
                continue
            if cb==ab:ok+=1
            else:bad.append(dict(target='/'.join(G1.hx(q) for q in grp),contract_only=sorted(G1.hx(x) for x in cb-ab),rom_only=sorted(G1.hx(x) for x in ab-cb)))
        stats[NAMES[u]]=dict(parsed=True,targets=len(cs),equal=ok,different=len(bad))
        if bad:disc.append(dict(id='%s-call-sites'%NAMES[u],claim='contract list of calls out of the unit (target and call-site blocks, or the stated count) vs the control transfers decoded from the ROM bytes (blocks containing the transfer)',detail=bad))
    return stats,disc



# ----------------------------------------------------------------------------------
# Natural reach statements of the contracts (TB based scratch replay) vs the instruction level replay of the three natural records
# ----------------------------------------------------------------------------------
def natural_vs_contract(env,nat_by_rec):
    rows=[];disc=[]
    def mine(u,rks):return sorted({pc for pc in env.contracts[u]['starts'] for rk in rks if nat_by_rec[rk][pc]})
    # counts stated by the contracts (base record / RNG record with answer 80)
    stated={17:(89,89),18:(90,90),19:(94,95),21:(39,39),22:(0,56)}
    for u,(b,r) in stated.items():
        mb=len(mine(u,('base',)));mr=len(mine(u,('rng',)))
        rows.append(dict(unit=NAMES[u],contract_base=b,mine_base=mb,contract_rng80=r,mine_rng80=mr,equal=(b==mb and r==mr)))
        if not (b==mb and r==mr):disc.append(dict(id='%s-natural-counts'%NAMES[u],claim='contract natural block start counts (base / RNG+80, TB based) vs instruction level replay',detail=rows[-1]))
    # U20a: the contract sentence lists the natural starts of the base record
    t=env.contracts[20]['text'];m=re.search(r'base\(`dyn`\)에서 ([^은]*)은 seed 36·37, `492d0`은[^,]*, `497a6` `497b0`은',t)
    if m:
        want=set(hexes(m.group(1)))|{0x492d0,0x497a6,0x497b0};got=set(mine(20,('base',)))
        rows.append(dict(unit='U20a',contract_base_list=sorted(G1.hx(x) for x in want),mine_base=sorted(G1.hx(x) for x in got),contract_only=sorted(G1.hx(x) for x in want-got),mine_only=sorted(G1.hx(x) for x in got-want)))
        if want!=got:disc.append(dict(id='U20a-natural-list',claim='contract natural starts of the base record vs instruction level replay (mine-only blocks are TB merged in the contract)',detail=rows[-1]))
    # U20b: the contract states "85984..85b3a natural unreached" (the 78(A6)=0 path); the exact TB start list is a range label and is not compared
    t=env.contracts[21]['text']
    if '`85984`~`85b3a`' in t:
        got=set(mine(21,('base','rng')));inner=sorted(x for x in got if 0x85984<=x<=0x85b3a)
        rows.append(dict(unit='U20b',natural_in_85984_85b3a=[G1.hx(x) for x in inner]))
        if inner:disc.append(dict(id='U20b-natural-85984-85b3a',claim='contract: 85984..85b3a natural unreached',detail=rows[-1]))
    return rows,disc


if __name__=='__main__':main()
