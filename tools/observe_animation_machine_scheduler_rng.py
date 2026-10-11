"""F4 decision 1 + 2: RNG-initialised seed variant of the F2 scheduler frame-pass observation (native Unicorn M68000, original ROM never modified).

What is new relative to tools/observe_animation_machine_scheduler.py (imported in-process, never edited):

  * decision 1 (docs/analysis/animation-machine-object-callbacks-f4-scope.md): all 142 stage_entry_body seed RAMs have the RNG pointer LONG 10d722 = 0 and a zeroed ring
    10d6b4..10d721 because the seed fixtures never ran the boot path c574 (MOVEQ #0,D0) / c576 (JSR 49a1a).  This tool adds a DECLARED SEED PREPARATION step before the first
    frame pass: the original 49a1a runs natively on the seed RAM with D0 = 0 (entry 49a1a, stopped directly before its RTS at 49a56, so no stack is touched), every instruction
    count / RAM write / register is recorded, the post-preparation RAM becomes the pass-0 input (registers stay the seed's registers: the preparation is a declared RAM change
    only) and the F2 frame-pass protocol (contract main decisions 2..4: PC 2ac2, A6 1008e4, A7 SPd 1ff000, LONG 104ca4 = SPd declared, stop at LONG (100820), declared waits) follows;
  * decision 2: the BIOS CARD request c00468 (JSR at c376 from c364, reached via 48090 -> caf0 -> c364) is a declared "bios-card" wait inside the pass.  The JSR is executed
    natively (it pushes the return address c37c and the saved A6); the pass stops at the unmapped fetch c00468; the declared resume is the fade_card contract resume
    (PC = c37c, A7 += 4 [the BIOS RTS pop], BYTE 10fdc6 = response) and the same pass continues.  No BIOS execution is claimed; the CCR after the BIOS is unknown and never read.
    Default response 80; a few seeds are repeated with response 00.

The frame pass remains a declared model, not natural game execution: no BIOS execution, no natural IRQ, no natural scheduler is claimed.  Per-pass MS5-SCHED-STATE-1 and
per-node MS5-SCHED-PORTS-1 digests, fresh-CPU split vs continuous (each twice), full dumps for 8 natural seeds and boundary frames follow the scheduler observer record format.
The coverage classification uses the routing chain of engine/src/animation_machine.cpp of the worktree /Users/start/Workspce/metalslug-input (git ref, default HEAD),
parsed by this tool (the scheduler observer's routing parser does not parse the newest chain).
"""
import argparse
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
import subprocess
import sys
import time
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_scheduler as S
import observe_animation_machine_pvc_banks as PB       # importing it replaces S.Machine by PvcMachine: every PVC-selectable bank (banks 4/5 included) is modeled

ROOT=S.ROOT
OUT=ROOT/'artifacts/animation_machine_scheduler_rng_native'
INPUT_TREE=Path('/Users/start/Workspce/metalslug-input')
F4_SCOPE=ROOT/'docs/analysis/animation-machine-object-callbacks-f4-scope.md'
SCHED_TOOL_SHA='62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c'
BASE_OBS=ROOT/'artifacts/animation_machine_scheduler_native/observation.json'
BASE_OBS_SHA='c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff'
M32=0xffffffff
KEYS=S.KEYS
UC_REG=S.UC_REG
FRAMES=400
PREP_ENTRY=0x49a1a                 # original RNG initialiser (boot c576 JSR 49a1a with MOVEQ #0,D0 at c574)
PREP_STOP=0x49a56                  # its RTS: the preparation stops directly before it (the stack is never touched)
RING_LO,RING_HI,PTR_ADDR=0x10d6b4,0x10d722,0x10d722
CARD_BIOS=0xc00468
CARD_JSR=0xc376
CARD_RET=0xc37c
CARD_ANSWER=0x10fdc6
DEFAULT_ANSWER=0x80
VARIANT_ANSWER=0x00
FULL_DUMP_SEEDS=8
NVARIANTS=6
BOOT_PROBES=((0x10f004,1,'f004.byte (c57c MOVE.B #3)'),(0x10f02c,2,'f02c.word (49a1a counter, untouched for D0=0)'),(0x10fdae,1,'fdae.byte (c58a loop flag)'),(0x107def,1,'7def.byte (c52a path)'),
    (0x107dea,2,'7dea.word (palette gate counter)'),(0x10de26,4,'de26.long (e8a1c)'),(0x10de2e,2,'de2e.word (e8a1c)'),(0x10d680,2,'d680.word (4823a)'),(0x10de14,4,'de14.long (4755e)'),
    (0x10de1c,4,'de1c.long (4755e)'),(0x1008e4,4,'1008e4 controller callback LONG'),(0x100820,4,'100820 frame head callback LONG'),(0x10d722,4,'d722.long RNG pointer'))


def sha(b):return hashlib.sha256(b).hexdigest()
def stable(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),default=str)


# ----------------------------------------------------------------------------------
# Routing of the input worktree (git ref) -> bitmap with the owner rule index
# ----------------------------------------------------------------------------------
STAGE_EVENT_OPS_TRAPS=(0xe93d8,0xe9528,0xe9530,0xe957a,0xe96d4,0xe9702,0xe9780,0xe9788)


def routing_source(ref,file_path):
    if file_path:
        data=Path(file_path).read_bytes();return data.decode(),dict(source='file',path=str(file_path),sha256=sha(data))
    rev=subprocess.check_output(['git','-C',str(INPUT_TREE),'rev-parse',ref],close_fds=False).decode().strip()
    data=subprocess.check_output(['git','-C',str(INPUT_TREE),'show','%s:engine/src/animation_machine.cpp'%rev],close_fds=False)
    return data.decode(),dict(source='git',tree=str(INPUT_TREE),ref=ref,commit=rev,sha256=sha(data))


def build_routing(text):
    """Bitmap (index pc>>1 over the fixed 1MiB) -> rule number (1-based) of the first matching `ok=animation_*` rule of the dispatch chain, 0 = unsupported."""
    body=text[text.index('bool ok=false;'):text.index('else return am_error(c,"unsupported animation machine PC")')]
    rules=re.findall(r'if \((.*?)\)ok=(animation_\w+)\(c\);',body,re.S)
    comp=[];names=[]
    for cond,fn in rules:
        e=cond.replace('next.pc','pc').replace('!stage_event_ops_trap(pc)','(pc not in TRAPS)').replace('&&',' and ').replace('||',' or ').replace('\n',' ')
        assert '!' not in e.replace('!=',''),e
        comp.append(compile(e,'<rule>','eval'));names.append(fn)
    nums=sorted(set(int(x,16) for x in re.findall(r'0x[0-9a-f]+',body))|set(STAGE_EVENT_OPS_TRAPS))
    pts=sorted(set([0]+[n&~1 for n in nums]+[(n+2)&~1 for n in nums]+[0x100000]))
    bm=bytearray(0x80000);env=dict(TRAPS=frozenset(STAGE_EVENT_OPS_TRAPS))
    def owner(pc):
        env['pc']=pc
        for i,code in enumerate(comp):
            if eval(code,env):return i+1
        return 0
    for i in range(len(pts)-1):
        lo,hi=pts[i],pts[i+1]
        if hi<=lo:continue
        first=owner(lo)
        if first:bm[lo>>1]=first
        if hi-lo>2:
            second=owner(lo+2)
            if second:
                for p in range(lo+2,hi,2):bm[p>>1]=second
    # self check on a deterministic sample against direct evaluation of the chain
    for pc in list(range(0,0x100000,0x1c6))+[0x2ab8,0x2ac6,0x2ac8,0x2a00,0x2a06,0x2a0a,0x4d7f0,0x38c8,0xa63c,0x47f04,0xe93d8,0xe93da,0xb4d7e,0xc6a90,0xe585c,0xdbdb6]:
        pc&=~1;assert bm[pc>>1]==owner(pc),hex(pc)
    return bm,names


def make_levels(bm):
    """The scheduler observer's SeedRun.routable() reads levels['A'] / levels['B']: both are the HEAD routing (this chain already contains F1..F3 and U01..)."""
    return dict(A=bm,B=bm)


# ----------------------------------------------------------------------------------
# Declared seed preparation: the original 49a1a with D0 = 0, run natively
# ----------------------------------------------------------------------------------
def rng_model(d1_in):
    """Independent Python model of 49a1a for D0 = 0 (hand decode of the ROM bytes: `3200` MOVE.W D0,D1 once before the loop; loop body 06417925 ADDI.W #7925,D1; d240 ADD.W D0,D1;
    c2c1 MULU.W D1,D1; e089 LSR.L #8,D1; c340 EXG D1,D0; 30c0 MOVE.W D0,(A0)+; 51cffff0 DBRA D7 back to the ADDI.W, D7 = 0x36 -> 55 passes)."""
    d0=0;d1=d1_in&M32;words=[]
    d1=(d1&0xffff0000)|(d0&0xffff)                           # MOVE.W D0,D1 (once)
    for _ in range(0x37):
        d1=(d1&0xffff0000)|((d1+0x7925)&0xffff)              # ADDI.W #7925,D1
        d1=(d1&0xffff0000)|((d1+d0)&0xffff)                  # ADD.W D0,D1
        d1=((d1&0xffff)*(d1&0xffff))&M32                     # MULU.W D1,D1
        d1=d1>>8                                              # LSR.L #8,D1
        d0,d1=d1,d0                                           # EXG D1,D0
        words.append(d0&0xffff)                               # MOVE.W D0,(A0)+
    ring=b''.join(w.to_bytes(2,'big') for w in words)
    return dict(ring=ring,pointer=RING_HI-2,d0=d0,d1=d1,d7=0xffff,a0=RING_HI-2,a5=0x108000)


def run_prep(program,fixed,snap):
    """Run 49a1a natively on the seed RAM.  Returns (record, exit_state).  Entry: PC 49a1a, D0 = 0, the seed's other registers, SR 2000 (CCR never read)."""
    ps=copy.deepcopy(snap);ps['regs']['d0']=0;ps['pc']=PREP_ENTRY
    entry_digest=S.state_blob_digest(ps['ram'],ps['regs'],PREP_ENTRY,ps['bank'])
    mach=S.Machine(program,fixed,ps);mach.install_basic_hooks();c=mach.cpu
    writes=[];reads=[];steps=[0];stopped=[None]
    def wr(uc,access,address,size,value,user):writes.append((address,size,value&((1<<(8*size))-1)))
    def rd(uc,access,address,size,value,user):reads.append((address,size))
    def step(uc,pc,size,user):steps[0]+=1
    def stop(uc,pc,size,user):stopped[0]=pc;uc.emu_stop()
    c.hook_add(UC_HOOK_MEM_WRITE,wr,begin=0x100000,end=0x1fffff);c.hook_add(UC_HOOK_MEM_READ,rd,begin=0x100000,end=0x1fffff)
    c.hook_add(UC_HOOK_CODE,step,begin=PREP_ENTRY,end=PREP_STOP-1);c.hook_add(UC_HOOK_CODE,stop,begin=PREP_STOP,end=PREP_STOP)
    err=None
    try:c.emu_start(PREP_ENTRY,0xffffff,count=5000)
    except unicorn.UcError as e:err=str(e)
    assert err is None and stopped[0]==PREP_STOP and mach.odd is None and mach.invalid is None,(err,stopped,mach.odd,mach.invalid)
    ex=mach.state();ex['pc']=PREP_STOP
    exit_digest=S.state_blob_digest(ex['ram'],ex['regs'],PREP_STOP,ex['bank'])
    # RAM difference ranges
    a,b=snap['ram'],ex['ram'];diff=[];i=0
    while i<len(a):
        if a[i]!=b[i]:
            j=i
            while j+1<len(a) and a[j+1]!=b[j+1]:j+=1
            diff.append((0x100000+i,0x100000+j+1));i=j+1
        else:i+=1
    # independent model
    mdl=rng_model(snap['regs']['d1'])
    model_ok=(ex['ram'][RING_LO&0xffff:RING_HI&0xffff]==mdl['ring'] and ex['ram'][PTR_ADDR&0xffff:(PTR_ADDR&0xffff)+4]==mdl['pointer'].to_bytes(4,'big')
        and all(ex['regs'][k]==v for k,v in (('d0',mdl['d0']),('d1',mdl['d1']),('d7',mdl['d7']),('a0',mdl['a0']),('a5',mdl['a5']))))
    ring_pre=snap['ram'][RING_LO&0xffff:(PTR_ADDR&0xffff)+4];ring_post=ex['ram'][RING_LO&0xffff:(PTR_ADDR&0xffff)+4]
    rec=dict(entry_pc=PREP_ENTRY,exit_pc=PREP_STOP,entry_regs=ps['regs'],exit_regs=ex['regs'],entry_digest=entry_digest,exit_digest=exit_digest,instructions=steps[0],
        writes=[list(w) for w in writes],write_count=len(writes),reads=[list(r) for r in reads],ram_diff=[[hex(x),hex(y)] for x,y in diff],
        ring_pre_sha256=sha(ring_pre),ring_post_sha256=sha(ring_post),model_ok=model_ok,rts_executed=False,
        pre_pointer=int.from_bytes(snap['ram'][PTR_ADDR&0xffff:(PTR_ADDR&0xffff)+4],'big'),post_pointer=int.from_bytes(ex['ram'][PTR_ADDR&0xffff:(PTR_ADDR&0xffff)+4],'big'))
    carried=copy.deepcopy(snap);carried['ram']=ex['ram']                    # registers stay the seed's: the preparation is a declared RAM change only
    carried['prep_entry_state']=ps
    return rec,carried


# ----------------------------------------------------------------------------------
# Frame pass run with the declared bios-card wait
# ----------------------------------------------------------------------------------
class RngRun(S.SeedRun):
    def __init__(self,*a,**kw):
        self.answer=kw.pop('answer',DEFAULT_ANSWER);self.full_dump=kw.pop('full_dump',False);self.prep_dump=kw.pop('prep_dump',None)
        S.SeedRun.__init__(self,*a,**kw);self.card_waits=[]
    def card_wait(self):
        """Declared bios-card wait: the native JSR at c376 pushed c37c (and the saved A6 below it) and the fetch at c00468 is unmapped."""
        mach=self.m
        if self.stop is not None or mach.fetch_unmapped!=CARD_BIOS or mach.pc()!=CARD_BIOS:return None
        a7=mach.cpu.reg_read(UC_REG['a7'])
        if mach.long(a7)!=CARD_RET or self.program[CARD_JSR:CARD_JSR+6]!=bytes.fromhex('4eb900c00468'):return None
        return a7
    def run_pass(self):
        mach=self.m;c=mach.cpu
        self.pass_nodes=[];self.cur=None;self.head_visit=False;self.waiting=None;self.stop=None;self.pass_flags=collections.Counter()
        walk=self.list_walk();ports0=len(mach.ports);start_digest=mach.digest(S.PASS_PC)
        waits=[]
        while True:
            mach.fetch_unmapped=None;mach.odd=None;mach.invalid=None;mach.intr=None
            try:c.emu_start(mach.pc(),0xffffff,count=self.pass_limit);ended=True
            except unicorn.UcError as e:ended=False;uc_error=str(e)
            if self.waiting is not None and self.stop is None:
                w=self.waiting;self.waiting=None;cur=self.cur
                changes=self.release_wait(w);rec=dict(pc=w['pc'],kind=w['kind'],live=w['live'],compared=w['compared'],released=[list(x) for x in changes],node=cur['seq'] if cur else None)
                waits.append(rec);self.waits_total[w['kind']]+=1
                if cur is not None:cur['waits'].append(rec)
                if len(waits)>S.WAIT_LIMIT or not changes:self.stop=dict(reason='wait-not-released',wait=rec);break
                continue
            a7=self.card_wait()
            if a7 is not None:
                cur=self.cur;saved_a6=mach.long(a7+4)
                c.reg_write(UC_REG['pc'],CARD_RET);c.reg_write(UC_REG['a7'],(a7+4)&M32);mach.put(CARD_ANSWER,1,self.answer)
                rec=dict(pc=CARD_BIOS,kind='bios-card',live=CARD_RET,compared=self.answer,released=[['pc',CARD_RET],['a7',4],['ram',CARD_ANSWER,1,self.answer]],node=cur['seq'] if cur else None,
                    a7_at_stop=a7,saved_a6=saved_a6,node_a6=cur['a6'] if cur else None)
                waits.append(rec);self.waits_total['bios-card']+=1;self.card_waits.append(dict(frame=self.frame,**rec))
                if cur is not None:cur['waits'].append(rec)
                if len(waits)>S.WAIT_LIMIT:self.stop=dict(reason='wait-not-released',wait=rec);break
                continue
            break
        reason=self.stop
        if reason is None:
            if mach.odd:reason=dict(reason='odd-data-access',**mach.odd)
            elif mach.invalid:reason=dict(reason='invalid-memory-access',**mach.invalid)
            elif mach.fetch_unmapped is not None:
                a=mach.fetch_unmapped
                reason=dict(reason='bios-boundary' if S.BIOS_LO<=a<S.BIOS_LO+0x100000 else 'fetch-unmapped',address=a,odd=bool(a&1),**{'from':self.last_node_hint()})
            elif mach.intr:reason=dict(reason='cpu-exception',**mach.intr,odd_pc=bool(mach.intr['pc']&1))
            elif not ended:reason=dict(reason='unicorn-error',error=uc_error,pc=mach.pc())
            else:reason=dict(reason='step-limit',limit=self.pass_limit,pc=mach.pc())
        return reason,walk,start_digest,waits,ports0
    def run(self):
        snap=self.snap;mach=self.build(snap);frame=0
        self.declared.append(dict(kind='ram-write',address=S.BASE_LONG,size=4,value=S.SPD,why='declared dispatcher base LONG 104ca4 = SPd (2ab2 MOVE.L A7,104ca4 is never executed in a seed RAM)'))
        self.limit=self.frames_limit;buffer={}
        if self.sink is not None:
            if self.prep_dump is not None:self.dump_rows.append(self.dump_state(self.prep_dump,'prep-entry',frame=-2))
            self.dump_rows.append(self.dump_state(mach.state(),'seed-start',frame=-1))
        prev_state=None
        while frame<self.limit:
            self.frame=frame;mach=self.m;c=mach.cpu
            if self.mode=='split' and frame>0:
                st=prev_state;st['regs']=dict(st['regs']);st['regs']['a6']=S.CONTROLLER;st['regs']['a7']=S.SPD;st['pc']=S.PASS_PC;mach=self.build(st);c=mach.cpu
            elif frame>0:
                c.reg_write(UC_REG['sr'],0x2000);c.reg_write(UC_REG['pc'],S.PASS_PC);c.reg_write(UC_REG['a6'],S.CONTROLLER);c.reg_write(UC_REG['a7'],S.SPD)
            reason,walk,start_digest,waits,ports0=self.run_pass()
            end_state=mach.state();partial=None
            if reason['reason']=='frame-head':
                end_state['pc']=reason['pc'];self.end_pcs.append(reason['pc'])
                regs=end_state['regs'];ok=(regs['a6']==S.FRAME_HEAD and regs['a5']==S.A5V and regs['a7']==S.SPD-4 and mach.long(S.SPD-4)==S.PASS_PC and end_state['pc'] in S.HEAD_STOPS and regs['a0']==end_state['pc'])
                if not ok:self.head_bad+=1
            else:
                partial=self.cur
                if partial is not None:self.cur=None;self.finish_node(partial,end_state,True)
            visited=[n['a6'] for n in self.pass_nodes];ws=set(walk);vs=set(visited)
            ports=mach.ports[ports0:]
            cbs=tuple(n['cb'] for n in self.pass_nodes)
            covA=all(n['rec']['rA'] for n in self.pass_nodes)
            prec=dict(frame=frame,start=start_digest,end=S.state_blob_digest(end_state['ram'],end_state['regs'],end_state['pc'],end_state['bank']),stop=reason['reason'],list_len=len(walk),
                visited=len(visited),walk=walk,nodes=[n['rec'] for n in self.pass_nodes],inserted=[a for a in visited if a not in ws],deleted=[a for a in walk if a not in vs],revisited=len(visited)-len(vs),
                waits=waits,ports=len(ports),ports_sha=S.ports_digest(ports),flags=dict(self.pass_flags),covA=covA,config=S.sha(repr(cbs).encode())[:16],ctrl_skipped=True)
            self.max_tbs=max(self.max_tbs,sum(n['rec']['tbs'] for n in self.pass_nodes));self.max_nodes=max(self.max_nodes,len(self.pass_nodes))
            self.pass_records.append(prec);self.digest.update(json.dumps(prec,sort_keys=True,default=str).encode())
            first_config=cbs not in self.configs;self.configs.add(cbs)
            if self.sink is not None:
                keep=(frame in (0,1,20,21)) or first_config or reason['reason']!='frame-head' or frame+1>=self.limit or bool(waits)
                if self.full_dump or keep:buffer[frame]=(end_state,keep)
            self.covered_prefix=self.covered_prefix and covA;prev_state=end_state
            if reason['reason']!='frame-head':
                self.stop=dict(reason,frame=frame);break
            frame+=1
        else:
            self.stop=dict(reason='frame-limit',frame=frame-1,frames=frame)
        self.frames_done=len(self.pass_records);self.fully_covered=self.covered_prefix
        if self.sink is not None:
            for f in sorted(buffer):
                st,keep=buffer[f]
                self.dump_rows.append(self.dump_state(st,'pass-end',frame=f,full_seed=bool(self.full_dump)))
        return self


# ----------------------------------------------------------------------------------
# Worker functions
# ----------------------------------------------------------------------------------
G={}


def prepared(case):
    sd=S.SEEDS[case];snap,meta=S.seed_snap(sd)
    rec,carried=run_prep(G['program'],G['fixed'],snap)
    rec2,carried2=run_prep(G['program'],G['fixed'],snap)                       # a second fresh-CPU preparation: must be identical
    assert rec2['exit_digest']==rec['exit_digest'] and rec2['writes']==rec['writes'] and carried2['ram']==carried['ram'],case
    return sd,snap,meta,rec,carried


def prep_summary(rec):
    return {k:v for k,v in rec.items() if k not in ('writes','reads')}|dict(write_count=rec['write_count'],read_count=len(rec['reads']))


def make_run(carried,mode,heavy,sink,answer,plan=None,full_dump=False,prep_dump=None):
    snap={k:v for k,v in carried.items() if k!='prep_entry_state'}
    return RngRun(G['program'],G['fixed'],G['levels'],snap,mode,FRAMES_CFG[0],heavy=heavy,plan=plan,sink=sink,extend=False,answer=answer,full_dump=full_dump,prep_dump=prep_dump)


FRAMES_CFG=[FRAMES]
HEAVY_CFG=[False]


def uncovered_info(run):
    """First node callback without an executor under the routing, plus the distinct uncovered callbacks (entry PC level)."""
    first=None;distinct=collections.OrderedDict();covered_prefix_passes=0;prefix_open=True
    for p in run.pass_records:
        pass_ok=True
        for n in p['nodes']:
            if not n['rA']:
                pass_ok=False
                if first is None:first=dict(frame=p['frame'],seq=n['seq'],a6=n['a6'],cb=n['cb'])
                key=n['cb']
                if key not in distinct:distinct[key]=dict(frame=p['frame'],seq=n['seq'])
        if prefix_open:
            if pass_ok:covered_prefix_passes+=1
            else:prefix_open=False
    return first,distinct,covered_prefix_passes


def work_a(arg):
    case,answer=arg
    sd,snap,meta,rec,carried=prepared(case)
    run=make_run(carried,'continuous',HEAVY_CFG[0] and sd['kind']=='natural',None,answer).run()
    first,distinct,prefix=uncovered_info(run)
    return dict(case=case,kind=sd['kind'],family=sd['family'],bank=sd['bank'],answer=answer,prep=prep_summary(rec),digest=run.digest.hexdigest(),stop=run.stop,frames_done=run.frames_done,
        frames_complete=sum(1 for p in run.pass_records if p['stop']=='frame-head'),covered=run.fully_covered,first_uncovered=first,uncovered_distinct=[dict(cb=k,**v) for k,v in distinct.items()],
        covered_prefix_passes=prefix,cb_counts=dict(run.cb_counts),waits=dict(run.waits_total),card=run.card_waits,max_tbs=run.max_tbs,max_nodes=run.max_nodes,a7_bad=run.a7_bad,head_bad=run.head_bad,
        f3_digest=S.f3_digest(run),model_count=dict(run.model_count),model_mismatch=run.model_mismatch[:50],f3_summary=dict(collections.Counter(
            (f['cb'],f['replay_status'],f['replay_exit_equal'],f['replay_ports_equal']) for f in run.f3_records)),
        f3_keys=[(f['frame'],f['seq'],f['cb'],f['leaders'],f['idx']) for f in run.f3_records],end_tail=[p['end'] for p in run.pass_records][-3:])


def write_gz(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);data=gzip.compress((stable(obj)+'\n').encode(),6,mtime=0);path.write_bytes(data);return sha(data),len(data)


def work_b(arg):
    case,answer,out_dir,rel,full,plan=arg;out_dir=Path(out_dir)
    sd,snap,meta,rec,carried=prepared(case)
    heavy=HEAVY_CFG[0] and sd['kind']=='natural'
    run=make_run(carried,'continuous',heavy,{},answer,plan=plan,full_dump=full,prep_dump=carried['prep_entry_state']).run()
    for d,b in run.blobs.items():S.write_blob(out_dir,d,b)
    prep_doc=prep_summary(rec);prep_doc['writes']=rec['writes'];prep_doc['reads']=rec['reads']
    doc=dict(case=case,kind=sd['kind'],family=sd['family'],meta=meta,prep=prep_doc,answer=answer,declared=run.declared+[dict(kind='seed-prep',why='original 49a1a run natively with D0=0 on the seed RAM before pass 0 (decision 1); RAM change only, registers stay the seed registers',
        entry=rec['entry_digest'],exit=rec['exit_digest'],ram_diff=rec['ram_diff'])],card_waits=run.card_waits,stop=run.stop,frames_done=run.frames_done,covered=run.fully_covered,passes=run.pass_records,
        f3=run.f3_records,dumps=run.dump_rows,model_rows=run.model_rows,model_mismatch=run.model_mismatch[:50])
    gz_sha,gz_size=write_gz(out_dir/rel/('seed_%04d.json.gz'%case),doc)
    r=dict(case=case,f3=run.f3_records,digest=run.digest.hexdigest(),f3_digest=S.f3_digest(run),file=str(Path(rel)/('seed_%04d.json.gz'%case)),file_sha256=gz_sha,file_size=gz_size,blobs=len(run.blobs),dumps=len(run.dump_rows),
        stop=run.stop,frames_done=run.frames_done,prep_exit=rec['exit_digest'],prep_second=None)
    for tag in ('split1','split2'):
        sr=make_run(carried,'split',False,None,answer).run();r[tag]=sr.digest.hexdigest();r[tag+'_frames']=sr.frames_done;r[tag+'_stop']=sr.stop
    return r


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def setup(routing_text):
    program=S.load_rom();S.G['program']=program;G['program']=program
    fixed=(ctypes.c_ubyte*0x100000).from_buffer_copy(program[:0x100000]);S.G['fixed']=fixed;G['fixed']=fixed
    bm,names=build_routing(routing_text);levels=make_levels(bm);G['levels']=levels;G['names']=names;G['bm']=bm;S.G['levels']=levels
    f3a,f3b,traps,f3a_rows,f3b_rows=S.f3_contract_lists()
    S.LEAD_SET=frozenset(S.F2_LEADERS)|frozenset(f3a)|frozenset(f3b);S.TRAP_SET=frozenset(traps)
    assert not (S.LEAD_SET&S.TRAP_SET)
    return program


def boot_path_evidence(program):
    """Decode of the boot path c560..c5a0 and 49a1a..49a58 from the ROM bytes (capstone via the shared disassembler; the bytes are also shown as hex)."""
    rows=[]
    for lo,hi in ((0xc52a,0xc5a8),(0x49a1a,0x49a58)):
        for r in S.disassemble_range(program,lo,hi-lo,0):
            rows.append(dict(address=hex(r['rom_offset']),raw=r['raw'],mnemonic=r['mnemonic'],op=r['op_str']))
    return rows


def dir_sizes(out_dir):
    total=0;files=0;blobs=0;blob_bytes=0
    for p in sorted(out_dir.rglob('*')):
        if p.is_file() and p.name!='observation.json':
            n=p.stat().st_size;total+=n;files+=1
            if p.parent.name=='blobs':blobs+=1;blob_bytes+=n
    return dict(files=files,total_bytes=total,blobs=blobs,blob_bytes=blob_bytes)


def stop_category(st):
    r=st['reason']
    if r=='invalid-memory-access':
        if st.get('kind')=='bank':return 'unsupported-bank-mapping'
        if st.get('kind')=='bank-read-outside-rom':return 'bank-read-outside-rom'
        if st.get('access')=='write-protected':return 'write-to-program-ROM'
        return 'invalid-memory-access:'+str(st.get('access'))
    return r


def tool_pins(routing_info):
    pins={}
    for name in ('observe_animation_machine_scheduler.py','observe_animation_machine_pvc_banks.py','observe_animation_machine_scheduler_rng.py')+S.IMPORTED_TOOLS:pins['tools/'+name]=sha((ROOT/'tools'/name).read_bytes())
    for path in (S.F2_CONTRACT,S.F3_CONTRACT,F4_SCOPE,S.SEED_OBS,BASE_OBS):pins[str(path.relative_to(ROOT))]=sha(path.read_bytes())
    pins['routing']=routing_info
    return pins


def pick_full_dump(naturals,a_by):
    """8 natural seeds with full pass dumps: 2 that pass the bios-card wait, 3 that reach the frame limit without it, 3 others; deterministic by case number."""
    card=[c for c in naturals if a_by[c]['card']];lim=[c for c in naturals if not a_by[c]['card'] and a_by[c]['stop']['reason']=='frame-limit'];oth=[c for c in naturals if c not in card and c not in lim]
    def spread(lst,n):
        if not lst:return []
        if len(lst)<=n:return list(lst)
        return [lst[round(i*(len(lst)-1)/(n-1))] for i in range(n)] if n>1 else [lst[0]]
    pick=spread(card,2)+spread(lim,3)+spread(oth,3)
    for c in naturals:
        if len(pick)>=FULL_DUMP_SEEDS:break
        if c not in pick:pick.append(c)
    return sorted(set(pick))[:FULL_DUMP_SEEDS]


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(OUT));ap.add_argument('--workers',type=int,default=3);ap.add_argument('--cases',default='');ap.add_argument('--frames',type=int,default=FRAMES)
    ap.add_argument('--heavy',action='store_true');ap.add_argument('--routing-ref',default='HEAD');ap.add_argument('--routing-file',default='');ap.add_argument('--variants',type=int,default=NVARIANTS)
    args=ap.parse_args(argv);out_dir=Path(args.out).resolve();t0=time.time();FRAMES_CFG[0]=args.frames;HEAVY_CFG[0]=args.heavy
    rom_start=S.rom_stat();assert rom_start['sha256']==S.ROM_SHA
    assert S.sha(S.F2_CONTRACT.read_bytes())==S.F2_SHA and S.sha(S.F3_CONTRACT.read_bytes())==S.F3_SHA
    assert sha((ROOT/'tools/observe_animation_machine_scheduler.py').read_bytes())==SCHED_TOOL_SHA,'scheduler observer changed'
    assert sha(BASE_OBS.read_bytes())==BASE_OBS_SHA,'base scheduler observation changed'
    if out_dir.exists() and any(out_dir.iterdir()):raise SystemExit('output directory is not empty: %s'%out_dir)
    (out_dir/'blobs').mkdir(parents=True,exist_ok=True);(out_dir/'seeds').mkdir(exist_ok=True)
    text,routing_info=routing_source(args.routing_ref,args.routing_file)
    setup(text);S.load_seeds();pins=tool_pins(routing_info)
    program=G['program']
    cases=sorted(S.SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    base=json.loads(BASE_OBS.read_text());base_by={r['case']:r for r in base['seeds']}
    ctx=multiprocessing.get_context('fork')
    with ctx.Pool(args.workers) as pool:
        a_list=pool.map(work_a,[(c,DEFAULT_ANSWER) for c in cases],chunksize=1)
        a_by={a['case']:a for a in a_list}
        naturals=[c for c in cases if a_by[c]['kind']=='natural']
        full=set(pick_full_dump(naturals,a_by))
        first={}
        if args.heavy:
            for a in a_list:
                if a['kind']!='natural':continue
                for frame,seq,cb,leaders,idx in a['f3_keys']:
                    for key in [('L',pc) for pc in leaders]+[('I',pc,v) for pc,v in idx]:
                        ident=(a['case'],frame,seq)
                        if key not in first or ident<first[key]:first[key]=ident
        plan=collections.defaultdict(set)
        for (case,frame,seq) in first.values():plan[case].add((frame,seq))
        b_list=pool.map(work_b,[(c,DEFAULT_ANSWER,str(out_dir),'seeds',c in full,frozenset(plan.get(c,()))) for c in cases],chunksize=1)
        b_by={b['case']:b for b in b_list}
        card_cases=[c for c in naturals if a_by[c]['card']][:max(0,args.variants)]
        va_list=pool.map(work_a,[(c,VARIANT_ANSWER) for c in card_cases],chunksize=1) if card_cases else []
        vb_list=pool.map(work_b,[(c,VARIANT_ANSWER,str(out_dir),'variants_answer00',False,frozenset()) for c in card_cases],chunksize=1) if card_cases else []
    va_by={a['case']:a for a in va_list};vb_by={b['case']:b for b in vb_list}
    f3_index=[]
    for c in cases:
        for f in b_by[c]['f3']:f3_index.append(dict(case=c,**f))
    f3_file=None
    if args.heavy:
        f3_sha,f3_size=write_gz(out_dir/'f3_node_seeds.json.gz',dict(note='F3 decision 10 node seeds of the RNG-prepared seed variant (entry = state at 2abe with PC replaced by 2ab8, A6 = node; expected = 2ac2; e94fe = fresh-CPU stop before e94fe); dumps reference blobs/<sha>.bin',records=f3_index))
        f3_file=dict(file='f3_node_seeds.json.gz',sha256=f3_sha,size=f3_size,records=len(f3_index),with_dumps=sum(1 for f in f3_index if 'dumps' in f))
    for b in b_list+vb_list:b.pop('f3',None)
    model_total=collections.Counter();f3_total=collections.Counter()
    for a in a_list:
        if a['kind']!='natural':continue
        for k,v in a['model_count'].items():model_total[tuple(k)]+=v
        for k,v in a['f3_summary'].items():f3_total[tuple(k)]+=v
    mism=[m for a in a_list for m in a['model_mismatch']]
    # comparisons
    seed_rows=[]
    for c in cases:
        a=a_by[c];b=b_by[c]
        eq=dict(continuous_twice=a['digest']==b['digest'] and a['f3_digest']==b['f3_digest'],split_first=a['digest']==b['split1'],split_second=a['digest']==b['split2'],
            frames=b['split1_frames']==a['frames_done']==b['frames_done'],stop=b['split1_stop']==a['stop']==b['stop'],prep_exit=a['prep']['exit_digest']==b['prep_exit'])
        assert all(eq.values()),(c,eq)
        bs=base_by[c]
        prog=dict(base_stop=bs['stop_category'],base_frames_done=bs['frames_done'],base_frames_complete=bs['frames_complete'])
        seed_rows.append(dict(case=c,kind=a['kind'],family=a['family'],bank=a['bank'],stop=a['stop'],stop_category=stop_category(a['stop']),frames_complete=a['frames_complete'],frames_done=a['frames_done'],
            covered_prefix_passes=a['covered_prefix_passes'],all_callbacks_routed=a['covered'],first_uncovered=a['first_uncovered'],uncovered_distinct=a['uncovered_distinct'],
            card=[dict(frame=x['frame'],node=x['node'],a7=x['a7_at_stop'],saved_a6=x['saved_a6'],answer=x['compared']) for x in a['card']],waits=a['waits'],prep=a['prep'],
            run_digest=a['digest'],equal=eq,file=b['file'],file_sha256=b['file_sha256'],file_size=b['file_size'],dumps=b['dumps'],blobs=b['blobs'],full_dump=c in full,
            max_tbs=a['max_tbs'],max_nodes=a['max_nodes'],a7_bad=a['a7_bad'],head_bad=a['head_bad'],baseline=prog,pass_end_tail=a['end_tail']))
    variant_rows=[]
    for c in card_cases:
        a=va_by[c];b=vb_by[c];ma=a_by[c]
        eq=dict(continuous_twice=a['digest']==b['digest'],split_first=a['digest']==b['split1'],split_second=a['digest']==b['split2'],frames=b['split1_frames']==a['frames_done']==b['frames_done'],stop=b['split1_stop']==a['stop']==b['stop'])
        assert all(eq.values()),(c,eq)
        variant_rows.append(dict(case=c,answer=VARIANT_ANSWER,stop=a['stop'],stop_category=stop_category(a['stop']),frames_done=a['frames_done'],frames_complete=a['frames_complete'],first_uncovered=a['first_uncovered'],
            uncovered_distinct=a['uncovered_distinct'],card=[dict(frame=x['frame'],node=x['node'],answer=x['compared']) for x in a['card']],cb_counts={'%x'%k:v for k,v in sorted(a['cb_counts'].items())},
            run_digest=a['digest'],equal=eq,file=b['file'],file_sha256=b['file_sha256'],file_size=b['file_size'],differs_from_answer80=a['digest']!=ma['digest'],
            answer80_cb_counts={'%x'%k:v for k,v in sorted(ma['cb_counts'].items())}))
    # aggregates
    nat=[r for r in seed_rows if r['kind']=='natural'];gua=[r for r in seed_rows if r['kind']!='natural']
    base_rng=[r for r in seed_rows if r['baseline']['base_stop']=='write-to-program-ROM']
    past=[r for r in base_rng if r['stop_category']!='write-to-program-ROM']
    horizon=collections.Counter(r['frames_done'] for r in nat)
    cat=collections.Counter(r['stop_category'] for r in seed_rows)
    first_cb=collections.Counter(r['first_uncovered']['cb'] for r in nat if r['first_uncovered'])
    first_by_cb=collections.defaultdict(list)
    for r in nat:
        if r['first_uncovered']:first_by_cb[r['first_uncovered']['cb']].append(r['case'])
    distinct_all=collections.Counter()
    for r in nat:
        for d in r['uncovered_distinct']:distinct_all[d['cb']]+=1
    boot={}
    for c in cases:
        sd=S.SEEDS[c];data=(S.SEED_DIR/sd['ram_file']).read_bytes()
        for addr,n,label in BOOT_PROBES:
            v=int.from_bytes(data[addr&0xffff:(addr&0xffff)+n],'big');boot.setdefault('%x %s'%(addr,label),collections.Counter())['%x'%v]+=1
    boot_tbl={k:dict(sorted(v.items())) for k,v in boot.items()}
    prep_all=[r['prep'] for r in seed_rows]
    prep_facts=dict(seeds=len(prep_all),model_ok=sum(1 for p in prep_all if p['model_ok']),instructions=sorted(set(p['instructions'] for p in prep_all)),write_count=sorted(set(p['write_count'] for p in prep_all)),
        ram_diff=sorted(set(stable(p['ram_diff']) for p in prep_all)),pre_pointer=sorted(set(p['pre_pointer'] for p in prep_all)),post_pointer=sorted(set(p['post_pointer'] for p in prep_all)),
        ring_pre_sha256=sorted(set(p['ring_pre_sha256'] for p in prep_all)),ring_post_sha256=sorted(set(p['ring_post_sha256'] for p in prep_all)),reads=sorted(set(p['read_count'] for p in prep_all)),
        exit_regs_sample=prep_all[0]['exit_regs'])
    sizes=dir_sizes(out_dir)
    rom_end=S.rom_stat();assert rom_end==rom_start,(rom_start,rom_end)
    card_rows=[r for r in nat if r['card']]
    report=dict(schema_version=1,tool='tools/observe_animation_machine_scheduler_rng.py',scope=SCOPE_TEXT,inputs=pins,rom_stat_start=rom_start,rom_stat_end=rom_end,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library_sha256=sha(Path(S.uclib._name).read_bytes())),
        declared_model=dict(spd=S.SPD,base_long=S.BASE_LONG,frames=FRAMES_CFG[0],heavy=args.heavy,pass_input=dict(pc=S.PASS_PC,a6=S.CONTROLLER,a7=S.SPD,sr='2000 (CCR 0, never read)'),
            seed_prep=dict(entry=PREP_ENTRY,stop_before=PREP_STOP,d0=0,effect='RAM only (registers stay the seed registers); RTS not executed; stack untouched'),
            bios_card=dict(wait_pc=CARD_BIOS,jsr=CARD_JSR,resume_pc=CARD_RET,a7_delta=4,answer_byte=CARD_ANSWER,default_answer=DEFAULT_ANSWER,variant_answer=VARIANT_ANSWER,carry='Unknown (BIOS CCR effect unmodeled)'),
            wait_release=dict(sound='WORD 104d74 := ffff',sprite='WORD 108d34 := D4.W',gate='BYTE 107ded bit7 cleared unless WORD 107dea <> 0')),
        routing=dict(info=routing_info,rules=len(G['names']),routed_pcs=sum(1 for x in G['bm'] if x),rule_names=G['names']),
        boot_path_decode=boot_path_evidence(program),seed_boot_state=boot_tbl,prep=prep_facts,
        seeds=seed_rows,variants_answer00=variant_rows,
        totals=dict(seeds=len(cases),natural=len(nat),guard_rows=len(gua),passes=sum(r['frames_done'] for r in seed_rows),complete_passes=sum(r['frames_complete'] for r in seed_rows),
            stop_categories=dict(cat),frame_limit_seeds=sum(1 for r in nat if r['stop']['reason']=='frame-limit'),horizon_hist={str(k):v for k,v in sorted(horizon.items())},
            base_rng_guard_seeds=len(base_rng),base_rng_guard_seeds_past_guard=len(past),base_rng_guard_seeds_still_rng=len(base_rng)-len(past),
            past_guard_stop_categories=dict(collections.Counter(r['stop_category'] for r in past)),past_guard_frames={str(r['case']):r['frames_done'] for r in past},
            bios_card_seeds=[r['case'] for r in card_rows],bios_card_waits=sum(len(r['card']) for r in card_rows),
            all_callbacks_routed_seeds=sorted(r['case'] for r in nat if r['all_callbacks_routed']),
            first_uncovered_by_cb={('%x'%cb):dict(seeds=len(v),cases=v) for cb,v in sorted(first_by_cb.items())},
            first_uncovered_none=sorted(r['case'] for r in nat if not r['first_uncovered']),
            uncovered_distinct_by_cb={('%x'%cb):n for cb,n in sorted(distinct_all.items())},
            a7_bad=sum(r['a7_bad'] for r in seed_rows),head_bad=sum(r['head_bad'] for r in seed_rows),
            fresh_split_equal_all=all(all(r['equal'].values()) for r in seed_rows)),
        f3_node_replay=dict(executions=sum(f3_total.values()),exit_and_ports_equal=sum(v for k,v in f3_total.items() if k[1]=='2ac2' and k[2] and k[3]),by_class={('%x/%s/%s/%s'%k):v for k,v in sorted(f3_total.items())}),
        model_compare={('%x/%s/%s/ok=%s'%k):v for k,v in sorted(model_total.items())},model_mismatches=mism[:50],f3_node_seed_index=f3_file,
        output_sizes=sizes,limitations=LIMITATIONS)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(seeds=len(cases),natural=len(nat),guards=len(gua),passes=report['totals']['passes'],stop_categories=report['totals']['stop_categories'],past_guard='%d/%d'%(len(past),len(base_rng)),
        card_seeds=len(card_rows),variants=len(variant_rows),size_mb=round(sizes['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True))
    return summary


SCOPE_TEXT=('Native Unicorn M68000 observation of the original ROM.  Seed variant of the F2 declared frame-pass model: before pass 0 the original 49a1a runs natively with D0 = 0 on the seed RAM '
    '(declared seed preparation, RAM change only; the boot path c574/c576 that initialises the RNG ring was never run by the stage_entry_body seed fixtures), and the BIOS CARD request c00468 '
    '(c376) is a declared bios-card wait with the fade_card resume (PC=c37c, A7+=4, BYTE 10fdc6=answer).  Not natural game execution: no BIOS execution, no natural IRQ, no natural scheduler '
    'is claimed.  The ROM is never modified; no ROM or extracted data is added to Git.  The 137 stage_entry_body begin outputs are the natural seeds; the 5 release outputs are guard rows (100b30 = deadbeef).')
LIMITATIONS=[
    'Coverage classification is by callback entry PC under the routing chain of the input worktree git ref (the contract method); executors own their internal blocks.',
    'The program ROM is write-protected in this tool: a store to 0..fffff stops the pass.',
    'The split mode rebuilds the CPU at pass boundaries only; the bios-card wait is resumed on the same CPU inside the pass (the resume is a plain declared host change).',
    'PVC bank mapping: the full MAME formula model of tools/observe_animation_machine_pvc_banks.py (PvcMachine, any producible base; a read of the window past the 8 MiB image is the guard bank-read-outside-rom).',
    'Only the BIOS call c00468 whose JSR is the one at c376 (return c37c) is a declared wait; any other c00468 caller stays a bios-boundary stop.',
    'The seed preparation changes RAM only; 49a1a also sets D0/D1/D7/A0/A5 which the declared preparation does not carry (they are recorded).  Other boot initialisation skipped by the seeds (c56e e7bf4 palette steps, 10f004, 47570 ...) is not applied.',
    '104ca2 (zombie counter) is never cleared in the declared pass; frame head e74 and controller c52a/c66a are skipped (F2 decision 3).',
]


if __name__=='__main__':main()
