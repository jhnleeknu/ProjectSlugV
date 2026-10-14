"""Object callback group G3 (F4 units N03..N16a; N02 was folded into G2 as U20b) native observation.

Native Unicorn M68000 observation of the original ROM (never modified; write protected in the model).  Nothing here claims BIOS execution, a natural IRQ or a natural scheduler:
the frame passes of artifacts/animation_machine_scheduler_native (base, 120 frames) and artifacts/animation_machine_scheduler_rng_native (RNG initialised by the original 49a1a,
400 frames, bios-card answer 80 and the 00 variants) are DECLARED MODELS re-used in-process from tools/observe_animation_machine_scheduler.py and
tools/observe_animation_machine_scheduler_rng.py (not edited), and every typed fixture is a DECLARED state (a captured natural state plus a recorded list of register / RAM / SR edits).

The observer is independent of the C++ executors (engine/src/animation_machine_objects_*.cpp); the unit block lists, code ranges and carry classifications come from the 14 pinned
contracts docs/analysis/animation-machine-objects-{n03..n16}-contract.md (N16 = the N16a part of the 7839a family; N02 does not exist as a contract: it was folded into U20b,
the 858d8 family of G2).  The generic machinery (independent M68000 subset model, fresh-CPU flows, coverage guided fixture search, natural stage over both natural records) is
imported from tools/observe_animation_machine_objects_g1.py and tools/observe_animation_machine_objects_g2.py (neither is edited); the independent model is EXTENDED here
(DIVU / DIVS / ADDX / SUBX, undecodable words become an 'unsupported' instruction instead of aborting a scan); the unit configuration, the contract parsers, the typed hand fixtures
(carry consumers / flag readers, arithmetic edge values, PVC bank sweeps, guards, 28ae / 2986 failures) and the report are written here.

PVC banks.  The scheduler Machine is replaced (in-process, by import of tools/observe_animation_machine_pvc_banks.py) by PvcMachine: every bank the MAME formula can produce is a state,
a read of the banked window past the 8 MiB image is the only bank guard (bank-read-outside-rom).  The independent model uses the same formula (address_map.pvc_bank_update) and guard.

Natural evidence.  Every node (of the 142 base seeds x 120 frames, the 142 RNG seeds x 400 frames and the 6 RNG answer-00 variants) that executed at least one instruction inside a G3
code range is replayed natively from its recorded entry state (PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd; write protected ROM; the scheduler's RNG / bank guards) on a FRESH CPU:
reference (one run, no pause), continuous (one CPU, paused at every piece boundary) and split (a fresh CPU rebuilt from the captured boundary state at every piece boundary; a sample
that includes the first node of every distinct callback / block path).  A piece is a maximal run of instructions that stay in one unit (or outside all units: a black box callee).
Entry / exit digests, ordered block-leader traces, exits and guards are recorded; the recorded scheduler exit digest must be reproduced.

Independent model.  The Python M68000 subset interpreter (written from the programmer's reference by instruction format; shares no code with Unicorn, capstone, the C++ or the
scheduler observer) runs every unit piece from the native piece-start state and is compared with the native piece: per instruction PC + 16 registers (sampled nodes: PC), ordered data
reads and writes, ports, final RAM / registers, final CCR at the piece boundary (read exactly with a MOVE SR,D0 probe; the plain Unicorn SR is stale), guards.

Typed fixtures.  Every contract block start that no natural node reaches gets a declared fixture (coverage guided search over a captured natural state, recorded as a minimized edit
list; direct entry only as the last resort and flagged "entry-self" / "entry-declared"); the fixtures also cover the contract minimum conditions: carry consumers with a declared CCR
(the branch outcome of the native run is the evidence, never the Unicorn SR), flag readers at a block start, producer -> consumer chains through real producers (observed in every flow),
arithmetic edge values of the DIVU / ADDX / multiply / shift blocks, PVC bank sweeps of every bank-window block, odd / ROM-write / unmapped / bank guards, 28ae / 2986 failures.
Fixtures run reference / continuous / split, twice each.
"""
import argparse
import collections
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import random
import re
import struct
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_objects_g1 as G1          # generic machinery; never edited here (imports the scheduler observer S and the PVC bank machine)
import observe_animation_machine_objects_g2 as G2          # natural stage / fixture runner re-used (never edited here)
import observe_animation_machine_scheduler as S
import observe_animation_machine_scheduler_rng as R
import observe_animation_machine_pvc_banks as PB           # replaces S.Machine by PvcMachine (any PVC-selectable bank)
import unicorn
from unicorn import UC_HOOK_CODE
from address_map import pvc_bank_update

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/start/Workspce/ms5-scratch/g3obs/out/run')
ROM_SHA=S.ROM_SHA
CONTRACT_DIR=ROOT/'docs/analysis'
M32=0xffffffff
KEYS=S.KEYS
UC_REG=S.UC_REG
SPD=S.SPD
PASS_PC=S.PASS_PC
hx=S.hx
sha=S.sha
GLOBAL=G1.GLOBAL
sjson=G1.sjson
MASK=G1.MASK
SIGN=G1.SIGN
sx=G1.sx

# unit id (byte value of the unit map; 0 = none) -> name, contract file, pinned contract SHA256.  Counts (blocks, instructions, bytes, even PCs) are taken from the contract text itself.
UNITS=collections.OrderedDict([
    (23,dict(name='N03',file='n03',sha='b3305fc97d9e37ca8f7e3f0de8ae82204e70c79c3e6e3f7bc4a31a5fc25f38f8')),
    (24,dict(name='N04',file='n04',sha='3a87155a37c93679aae5f849b1deac3ec766a32f2142a5a1e21743ad6ef6c813')),
    (25,dict(name='N05',file='n05',sha='403b0b6ba157097695918182b971b2411e645072f39802a51b5ca5e728104cf3')),
    (26,dict(name='N06',file='n06',sha='288137925db4b24b13c033e94804c4bb79931957dd82d2696e7017a57d5afee3')),
    (27,dict(name='N07',file='n07',sha='cbbb8fbf769a9cad4b656ff71600a9ffdb85242a76c5c78c253a0fafe23a21d0')),
    (28,dict(name='N08',file='n08',sha='6014ec8f40fc2cd776f4faa38e214dbd09e6aa9e8717a0bee47df1342e21182d')),
    (29,dict(name='N09',file='n09',sha='0ff994e110ef3146cdafaea6aa59be074a024cf487cc43542dbc2e4a5ecee140')),
    (30,dict(name='N10',file='n10',sha='8269006ede74433ce05a3f77569537aa4c72fd72ac7bb6652c33067f35097815')),
    (31,dict(name='N11',file='n11',sha='213f96a02e5b52f62aa4dcbc2787ec2cf1d4aad582c76da9e031d9f8c065d797')),
    (32,dict(name='N12',file='n12',sha='e0f432b4768d3fa7f62e65e899802427275df22bac00fca18c7bd65ded4cc0e9')),
    (33,dict(name='N13',file='n13',sha='e93eeddb8701c3e90216ae1f1c55a047726e3242b3e82959c0d21edc9e29d632')),
    (34,dict(name='N14',file='n14',sha='77bb85f8a3c1b1ddb60daec7f0bc5af62a2cede53ce78e4d7018c95f01423c04')),
    (35,dict(name='N15',file='n15',sha='d197f6f86c2b5471398918af1a78de8638710c86d4ca24e173484b2bb424b252')),
    (36,dict(name='N16',file='n16',sha='0fddf6a12152727e39d4c44adc40bcd4da23a801fc1a613a5c0f84adf317ef66'))])
UIDS=tuple(UNITS)
NAMES={u:UNITS[u]['name'] for u in UNITS}
NAME_UID={v:k for k,v in NAMES.items()}


# ----------------------------------------------------------------------------------
# Independent model extension: DIVU / DIVS / ADDX / SUBX, undecodable words as an 'unsupported' instruction (linear scans of data bytes inside a range never abort)
# ----------------------------------------------------------------------------------
_BaseModel=G1.Model


class Model3(_BaseModel):
    """G1.Model + the instructions the G3 units use that the G1 subset lacks.  Everything else is inherited."""
    def decode1(self,pc):
        w=self.ext(pc)
        try:
            if (w&0xf0c0)==0x80c0 and (w&0x0f00) in (0x000,0x100):          # DIVU <ea>,Dn (1000 rrr 011) / DIVS (1000 rrr 111)
                mode=(w>>3)&7;rm=w&7;reg=(w>>9)&7
                if mode==1:raise G1.MUnsupported('divide by An')
                ea,pos=self.dec_ea(mode,rm,2,pc+2)
                return G1.Ins(op='divs' if (w&0x100) else 'divu',pc=pc,len=pos-pc,reg=reg,src=ea,size=2)
            if (w&0xf130)==0xd100 and (w&0xc0)!=0xc0:                          # ADDX Dy,Dx / -(Ay),-(Ax)   (1101 xxx 1 ss 00 m yyy)
                return G1.Ins(op='addx',pc=pc,len=2,size=G1.SZB[(w>>6)&3],reg=(w>>9)&7,count=w&7,aux=(w>>3)&1)
            if (w&0xf130)==0x9100 and (w&0xc0)!=0xc0:                          # SUBX
                return G1.Ins(op='subx',pc=pc,len=2,size=G1.SZB[(w>>6)&3],reg=(w>>9)&7,count=w&7,aux=(w>>3)&1)
            return _BaseModel.decode1(self,pc)
        except G1.MUnsupported as e:
            return G1.Ins(op='unsupported',pc=pc,len=2,text=str(e))
    def exec_op(self,ins,op,nxt):
        r=self.r;size=ins.size
        if op in('divu','divs'):
            d=self.get(self.resolve(ins.src,2),2);dn=ins.reg;dividend=r[dn]&M32
            if d==0:raise G1.MGuard('zero-divide',vector=5)
            if op=='divu':q,rem=dividend//d,dividend%d;ovf=q>0xffff
            else:
                a=sx(dividend,4);b=sx(d,2);q=abs(a)//abs(b);rem=abs(a)%abs(b)
                if (a<0)!=(b<0):q=-q
                if a<0:rem=-rem
                ovf=not(-0x8000<=q<=0x7fff)
            if ovf:                                                           # 68000: V set, the register is unchanged, N / Z are undefined
                self.cc.update(V=1,C=0,N=None,Z=None)
            else:
                r[dn]=(((rem&0xffff)<<16)|(q&0xffff))&M32;self.cc.update(N=int(bool(q&0x8000)),Z=int((q&0xffff)==0),V=0,C=0)
        elif op in('addx','subx'):
            x=self.flag('X')
            if ins.aux==0:
                dst=('r',ins.reg);src=('r',ins.count)
                s=self.get(src,size);d=self.get(dst,size)
            else:
                sa=(r[8+ins.count]-self.reg_inc(ins.count,size))&M32;r[8+ins.count]=sa;s=self.rd(sa,size)
                da=(r[8+ins.reg]-self.reg_inc(ins.reg,size))&M32;r[8+ins.reg]=da;d=self.rd(da,size);dst=('m',da)
            mk=MASK[size];sg=SIGN[size]
            if op=='addx':
                res=(d+s+x)&mk;c=int(d+s+x>mk);v=int(bool((~(d^s))&(d^res)&sg))
            else:
                res=(d-s-x)&mk;c=int(d<s+x);v=int(bool((d^s)&(d^res)&sg))
            self.put(dst,size,res)
            self.cc['N']=int(bool(res&sg));self.cc['V']=v;self.cc['C']=c;self.cc['X']=c
            if res!=0:self.cc['Z']=0
        else:
            return _BaseModel.exec_op(self,ins,op,nxt)
        return nxt


G1.Model=Model3                # the generic machinery (G1.model_piece, G1.build_cfg, ...) and the G2 helpers build their models through the module level name
G2.Model=Model3
Model=Model3


_orig_model_piece=G1.model_piece


def model_piece3(env,flow,piece):
    """G1.model_piece + the DIVU / DIVS division by zero: Unicorn stops with a cpu-exception (vector 5) at the dividing instruction with registers unchanged; the model raises the same as a guard."""
    ok,diffs,info=_orig_model_piece(env,flow,piece)
    if not ok and info.get('guard')=='zero-divide' and flow.final['kind']=='guard' and flow.final['detail']['kind']=='cpu-exception' and flow.final['detail']['detail'].get('number')==5 and piece['end']==flow.final['idx']:
        diffs=[d for d in diffs if d!='model guard zero-divide, native none']
        return (not diffs),diffs,info
    return ok,diffs,info


G1.model_piece=model_piece3


# ----------------------------------------------------------------------------------
# Contracts: code ranges, block starts, carry lists, named boundaries (pinned)
# ----------------------------------------------------------------------------------
def contract_path(u):return CONTRACT_DIR/('animation-machine-objects-%s-contract.md'%UNITS[u]['file'])


def hexes(s):return [int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`',s)]


def section_of(t,head):
    i=t.index(head);j=t.find('\n## ',i+5)
    return t[i:] if j<0 else t[i:j]


def noparen(s):
    """Text without parenthesised segments (nested one level)."""
    prev=None
    while prev!=s:
        prev=s;s=re.sub(r'\([^()]*\)','',s)
    return s


def group_tokens(s):
    """Hex words (3..6 digits) inside the backtick groups of s, in order."""
    out=[]
    for g in re.findall(r'`([^`]*)`',s):
        out.extend(int(x,16) for x in re.findall(r'(?<![0-9A-Za-z.])[0-9a-f]{3,6}(?![0-9A-Za-z.])',g))
    return out


def first_tokens(s):
    """First hex word of every backtick group of s (the block start of 'pc BCC.W target' style groups)."""
    out=[]
    for g in re.findall(r'`([^`]*)`',s):
        m=re.match(r'^([0-9a-f]{3,6})(?![0-9A-Za-z.])',g)
        if m:out.append(int(m.group(1),16))
    return out


def parse_ranges3(u,t):
    rows=[(int(a,16),int(b,16),int(n.replace(',','')),h) for a,b,n,h in re.findall(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| ([0-9,]+) \| `([0-9a-f]{64})` \|',t,re.M)]
    if not rows:                                                          # N10: one range stated in the summary
        m=re.search(r'코드 1 범위 `([0-9a-f]+)\.\.([0-9a-f]+)` ([0-9,]+)바이트\(SHA256 `([0-9a-f]{64})`\)',t);assert m,u
        rows=[(int(m.group(1),16),int(m.group(2),16),int(m.group(3).replace(',','')),m.group(4))]
    return rows


# producer classification of the contracts, transcribed from the "known carry 생산" lines (counts asserted against the contract numbers in parse_contract3)
# kinds: Clear / Set (C is a constant), Computed (C is a data dependent value the block computes: CMP borrow ...), Invert (EORI #1,CCR; RTS: a known C is flipped, Unknown stays Unknown)
PRODUCERS={
    23:{},
    24:{0x4a48a:'Set',0x4a490:'Clear'},
    25:{0x1abd4:'Clear'},
    26:{0xeb7aa:'Set',0xeb7b0:'Clear'},
    27:{0x9c04c:'Set',0x9c07a:'Set'},
    28:{0x494a6:'Clear',0x494ac:'Clear',0x494b4:'Set',0x4984e:'Computed',0x49862:'Computed'},
    29:dict([(p,'Clear') for p in (0xb01c8,0xb01fa,0xb0320,0xb042e,0xb0358,0xb03d8,0xb041c,0xb0468,0xb047e)]+[(p,'Set') for p in (0xb01d6,0xb01ee,0xb031a,0xb04b6)]+[(p,'Computed') for p in (0xb0406,0xb0412,0xb0434,0xb0462)]),
    30:{},
    31:{0xeb60a:'Set',0xeb610:'Clear'},
    32:{0x53196:'Set',0x5319c:'Clear'},
    33:{},
    34:dict((p,'Set') for p in (0xa5d64,0xa5d9c,0xa5de8,0xa5e54,0xa5faa)),
    35:dict([(p,'Clear') for p in (0x493ee,0x70298,0x702c6,0x70588,0x705fe,0x76fc0,0x76fe6,0x710d2)]+[(p,'Set') for p in (0x493e8,0x702c0,0x7058e,0x705f8)]+[(p,'Computed') for p in (0x493c8,0x493d4,0x7029e)]),
    36:dict([(p,'Set') for p in (0x79212,0x792fe,0x795ac,0x78c96)]+[(p,'Clear') for p in (0x7921c,0x792b2,0x79304,0x795b2,0x79624)]+[(p,'Invert') for p in (0x792ac,0x7961e)])}
PRODUCERS_STATED={23:0,24:2,25:1,26:2,27:2,28:5,29:17,30:0,31:2,32:2,33:0,34:5,35:15,36:11}
# consumers: where the contract text is not a plain "소비자 N개 ... token" bullet, the transcription of its list (asserted against the stated count)
CONSUMERS_OVERRIDE={
    30:[0xc5932],
    29:[0xaf5b0,0xaf64a,0xaf6a4,0xaf938,0xafc92,0xaf738,0xaf74e,0xaf764,0xaf7f4,0xaf970,0xafc78,0xb01ea,0xb0238,0xb02b0,0xb036c,0xb03f0,0xb044a,0xb058a,0xb05aa]}


def parse_starts3(u,t,ins,derived,stated):
    """Block starts of the contract: the backticked pcs followed by a colon in the block list section (plain, `a`/`b`/`c`: lists, the N08 start lists), then - only when the stated
    count is not reached - the derived leaders that the block list names as backticked pcs (compressed spellings).  Returns (starts, notes)."""
    sec=section_of(t,'## block 목록');notes=[]
    toks=[int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`(?: ?\([^)]*\))?: ',sec)]
    for m in re.finditer(r'((?:`[0-9a-f]{3,6}`/)+`[0-9a-f]{3,6}`)(?: ?\([^)]*\))?:',sec):toks.extend(hexes(m.group(1)))
    if u==NAME_UID['N08']:
        for m in re.finditer(r'(g[0-7]) `([0-9a-f ]+)`',sec):toks.extend(int(x,16) for x in m.group(2).split())
        notes.append('N08 128 bit-check starts expanded from the g0..g7 start lists of the contract')
    S0=sorted({x for x in toks if x in ins})
    if len(S0)<stated:
        extra=[x for x in derived if x not in S0 and re.search(r'`%x`'%x,sec) and ins[x].op!='bcc']
        notes.append('%d starts added from derived leaders that the block list names: %s'%(len(extra),' '.join('%x'%x for x in extra[:24])))
        S0=sorted(set(S0)|set(extra))
    return S0,notes,len(set(toks))


def parse_flow3(u,t):
    """FLOW_ONLY list (C preserved): stated count and listed pcs."""
    sec=section_of(t,'## 구현 범위와 규약')
    if '## carry' in t:sec+='\n'+section_of(t,'## carry')
    summ=section_of(t,'## 요약')
    for src in (sec,summ):
        m=re.search(r'\*\*FLOW_ONLY (\d+)(?:개|\s*block)[^\n]*',src) or re.search(r'FLOW_ONLY (\d+)(?:개|\s*block)[^\n]*',src)
        if not m:continue
        line=m.group(0);n=int(m.group(1))
        if '목록:' in line:line=line[line.index('목록:'):]
        else:line=line[len(m.group(0).split(m.group(1),1)[0])+len(m.group(1)):]
        line=re.sub(r'\([^)`]*\)','',line)
        line=re.split(r'\. ',line)[0]
        return n,group_tokens(line)
    return None,[]


def parse_consumers3(u,t):
    if CONSUMERS_OVERRIDE.get(u):
        return len(CONSUMERS_OVERRIDE[u]),list(CONSUMERS_OVERRIDE[u])
    sec=section_of(t,'## 구현 범위와 규약')
    if '## carry' in t:sec+='\n'+section_of(t,'## carry')
    summ=section_of(t,'## 요약')
    for src in (sec,summ):
        m=re.search(r'\*\*소비자 (\d+)개\.?\*\*([^\n]*)',src)
        if m:
            n=int(m.group(1));rest=m.group(2)
            if n==0:return 0,[]
            return n,first_tokens(noparen(rest)) if re.search(r'`[0-9a-f]{3,6} [A-Z]',rest) else group_tokens(re.sub(r'\([^)`]*\)','',rest.split('Unknown')[0]))
    m=re.search(r'\*\*소비 (\d+) block\.\*\*(.*?)(?=\n- \[F\] \*\*known|\n- \[F\] \*\*FLOW)',sec,re.S)
    if m:
        n=int(m.group(1));body=m.group(2)
        toks=[]
        if u==NAME_UID['N16']:toks=[0x792ac,0x7961e]                          # "EORI.B #1,CCR; RTS 2개(결정 4)": they read a known C and flip it
        for ln in body.splitlines():
            if re.match(r'^\s*- `[0-9a-f]{3,6}[ `]',ln) or re.match(r'^\s*- `[0-9a-f]{3,6}`',ln):
                head=ln.split(':')[0]
                toks.extend(first_tokens(noparen(head)) if ' BC' in head or ' SC' in head or ' EORI' in head else group_tokens(noparen(head)))
        return n,toks
    return None,[]


def parse_boundary3(u,t):
    """Boundary callees named by the contract (no executor at the time of the contract) and TRAP pcs."""
    dep=section_of(t,'## 의존·경계') if '## 의존·경계' in t else ''
    trap=[];callee=[]
    for ln in dep.splitlines():
        if '실행부 없는 경계' in ln:
            seg=noparen(ln[ln.index('실행부 없는 경계'):])
            seg=re.split(r'\. |\.$',seg)[0]
            if 'TRAP' in seg:
                a,b=seg.split('TRAP',1);trap=group_tokens(b);callee=group_tokens(a)
            else:callee=group_tokens(seg)
            break
    if not callee:                                                        # summary spelling
        for ln in section_of(t,'## 요약').splitlines():
            if '경계' in ln and '실행부 없' in ln and '없다' not in ln.split('실행부 없')[1][:12]:
                seg=noparen(ln.split('):',1)[1] if '):' in ln else ln);seg=re.split(r'\. ',seg)[0]
                if 'TRAP' in seg:
                    a,b=seg.split('TRAP',1);trap=trap or group_tokens(b);callee=group_tokens(a)
                else:callee=group_tokens(seg)
                break
    return callee,trap


def parse_contract3(u,program):
    p=contract_path(u);data=p.read_bytes();cfg=UNITS[u]
    assert sha(data)==cfg['sha'],('contract changed',cfg['name'],sha(data))
    t=data.decode('utf-8');rows=parse_ranges3(u,t)
    for a,b,n,h in rows:
        assert b-a==n and sha(program[a:b])==h,(cfg['name'],hex(a),hex(b))
    ranges=[(a,b) for a,b,_,_ in rows];total=sum(b-a for a,b in ranges)
    m=re.search(r'합계 ([\d,]+)바이트[^`]*`([0-9a-f]{64})`',t)
    if m:
        assert int(m.group(1).replace(',',''))==total,cfg['name']
        assert sha(b''.join(program[a:b] for a,b in ranges))==m.group(2),cfg['name']
    stated=dict()
    m=re.search(r'\[F\] \*{0,2}(?:N\d+ = )?(\d+) block',section_of(t,'## block 목록'));stated['blocks']=int(m.group(1))
    summ=section_of(t,'## 요약')
    m=re.search(r'(\d+)명령',summ);stated['insns']=int(m.group(1)) if m else None
    m=re.search(r'짝수 PC (?:는 )?([\d,]+)개',t);stated['even']=int(m.group(1).replace(',','')) if m else None
    m=re.search(r'내부 (?:PC )?(\d+)',section_of(t,'## 구현 범위와 규약'));stated['interior']=int(m.group(1)) if m else None
    return dict(unit=u,name=cfg['name'],sha=cfg['sha'],ranges=ranges,bytes=total,stated=stated,text=t,range_rows=rows)


def decode_ranges(prog,ranges):
    """Linear decode of the ranges with the model decoder: pc -> Ins (Model3 turns undecodable words into 'unsupported')."""
    mdl=Model3(prog,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0);ins={}
    for lo,hi in ranges:
        pc=lo
        while pc<hi:
            i=mdl.decode(pc);ins[pc]=i;pc+=i.len
        assert pc==hi,(hex(lo),hex(hi),hex(pc))
    return ins


def derive_leaders(ins,ranges):
    """Control-flow derived leaders inside the ranges: range starts, in-range branch / call targets, instructions after Bcc / BRA / BSR / JSR / JMP / RTS, installed callback entries."""
    inr=lambda x:any(a<=x<b for a,b in ranges)
    lead=set(a for a,b in ranges)
    for pc,i in ins.items():
        nx=pc+i.len
        if i.op in('bcc','dbcc','bra','bsr'):lead.update((i.target,nx))
        elif i.op in('jsr','jmp'):
            if i.src[0] in('abs','pcd16'):lead.add(i.src[1])
            lead.add(nx)
        elif i.op=='rts':lead.add(nx)
        elif i.op=='move' and i.size==4 and i.src[0]=='imm' and i.dst==('ind',6):lead.add(i.src[1])
        elif i.op=='movea' and i.size==4 and i.src[0]=='imm' and i.dst==('an',0):lead.add(i.src[1])
    return sorted(x for x in lead if inr(x) and x in ins)


class Env3(G1.Env):
    """G1.Env over the 14 G3 contracts (unit ids 23..36).  Interface used by the generic machinery: program, fixed, contracts, unit, starts, traps, boundary, range_list, unit_of."""
    def __init__(self):
        self.program=S.load_rom();self.fixed=(G1.ctypes.c_ubyte*0x100000).from_buffer_copy(self.program[:0x100000])
        self.contracts={}
        self.unit=bytearray(0x80000);self.starts={};self.traps={};self.range_of={};self.boundary={}
        for u in UIDS:
            c=parse_contract3(u,self.program);ins=decode_ranges(self.program,c['ranges']);der=derive_leaders(ins,c['ranges'])
            st,notes,ntok=parse_starts3(u,c['text'],ins,der,c['stated']['blocks'])
            fn,fl=parse_flow3(u,c['text']);cn,cl=parse_consumers3(u,c['text']);callee,trap=parse_boundary3(u,c['text'])
            c.update(ins=ins,derived=der,starts=st,parse_notes=notes,parsed_tokens=ntok,flow_n=fn,flow=sorted(set(fl)),flow_listed=len(fl),consumers_n=cn,consumers=sorted(set(cl)),consumers_listed=len(cl),
                producers=dict(PRODUCERS[u]),boundary_named=callee,traps_named=trap)
            self.contracts[u]=c
            for lo,hi in c['ranges']:
                for pc in range(lo,hi,2):
                    assert self.unit[pc>>1]==0,hex(pc)
                    self.unit[pc>>1]=u
            for pc in st:
                assert any(lo<=pc<hi for lo,hi in c['ranges']),(u,hex(pc));self.starts[pc]=u
        for u,c in self.contracts.items():
            c['boundary']=[pc for pc in c['boundary_named'] if self.unit_of(pc)==0]
            c['boundary_in_g3']=[pc for pc in c['boundary_named'] if self.unit_of(pc)!=0]
            c['traps']=[pc for pc in c['traps_named'] if self.unit_of(pc)==0]
            for pc in c['boundary']:self.boundary[pc]=u
            for pc in c['traps']:self.traps[pc]=u
        self.range_list=sorted((lo,hi,u) for u,c in self.contracts.items() for lo,hi in c['ranges'])


# ----------------------------------------------------------------------------------
# Static analysis of the contract blocks
# ----------------------------------------------------------------------------------
new_model=G2.new_model
abs_bank_operands=G2.abs_bank_operands
block_flag_analysis=G2.block_flag_analysis
decode_block=G2.decode_block
CALL_FAIL_TARGETS=(0x28ae,0x2986)                      # child creation (28ae) and the cue wrapper (2986) whose failure path is driven by WORD 104ca0
ARITH_OPS=('divu','divs','addx','subx','mulu','muls')


def analyze_units3(env):
    """CFG, flag consumers (model), bank-window blocks, memory kinds, external targets per start (G2.analyze_units over the G3 units)."""
    cfg=G1.build_cfg(env);ana={}
    for s in sorted(env.starts):
        a=block_flag_analysis(env,cfg,s)
        mdl=new_model(env);bank=[];callfail=False;calls=[];installs=[];children=[];ext=set();arith=[];
        u0=env.starts[s];own=env.contracts[u0]['ranges']
        for pc in cfg[s]['insns']:
            ins=mdl.decode(pc);bank+=abs_bank_operands(ins)
            if ins.op in('jsr','bsr') and ins.src is None and ins.target is not None:calls.append(ins.target)
            if ins.op=='jsr' and ins.src[0] in ('abs','pcd16'):
                calls.append(ins.src[1])
                if ins.src[1] in CALL_FAIL_TARGETS:callfail=True
            if ins.op=='move' and ins.size==4 and ins.src[0]=='imm' and ins.dst==('ind',6):installs.append(ins.src[1])
            if ins.op=='movea' and ins.size==4 and ins.src[0]=='imm' and ins.dst==('an',0):children.append(ins.src[1])
            tg=None
            if ins.op in('bra','bsr','bcc','dbcc'):tg=ins.target
            elif ins.op in('jsr','jmp') and ins.src[0] in('abs','pcd16'):tg=ins.src[1]
            if tg is not None and not any(lo<=tg<hi for lo,hi in own):ext.add(tg)
            if ins.op in ARITH_OPS:arith.append(ins.op)
        a.update(bank=bank,calls=calls,installs=installs,children=children,external=sorted(ext),callfail=callfail,arith=arith,unit=u0,nins=len(cfg[s]['insns']),last=cfg[s]['insns'][-1])
        ana[s]=a
    env.cfg=cfg;env.ana=ana
    contract_cons={s for c in env.contracts.values() for s in c['consumers']}
    model_cons={s for s,a in ana.items() if a['consumes']=='C'}
    env.consumers=contract_cons|model_cons
    env.producers={s for c in env.contracts.values() for s in c['producers']}
    env.model_consumers=model_cons;env.contract_consumers=contract_cons
    return ana


def cfg_check3(env,cfg):
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


_orig_node_replay=G1.node_replay


class ChainList(list):
    """Block-leader list of a replay; .chain is the same sequence with a 0 separator wherever a black box (non unit) piece ran between two unit pieces."""
    chain=None


def node_replay3(*a,**k):
    res,f,models=_orig_node_replay(*a,**k)
    c=f['cont'];ch=[];gap=False
    for p in c.pieces:
        if p['unit']:
            if gap and ch:ch.append(0)
            ch.extend(p['leaders']);gap=False
        else:gap=True
    L=ChainList(res['leaders']);L.chain=ch;res['leaders']=L
    return res,f,models


G1.node_replay=node_replay3


def consumer_pairs3(env,leaders):
    """Native branch outcomes of the carry consumers: key 'cons>next' (next unit block executed) and 'prod>cons>next' when a contract producer ran directly before the consumer with no black box
    piece and at most one block (the RTS) in between (the producer -> consumer chain through a REAL producer; the exact C is then the producer's)."""
    out=collections.Counter();cons=env.consumers;prods=env.producers
    seq=getattr(leaders,'chain',None)
    if seq is None:seq=list(leaders)
    for i,pc in enumerate(seq):
        if pc in cons:
            nxt='-'
            for q in seq[i+1:]:
                if q:nxt='%x'%q;break
            out['%x>%s'%(pc,nxt)]+=1
            for j in range(i-1,max(-1,i-3),-1):
                if seq[j]==0:break
                if seq[j] in prods:out['p%x>%x>%s'%(seq[j],pc,nxt)]+=1;break
    return out


G2.consumer_pairs=consumer_pairs3
consumer_pairs=consumer_pairs3


# ----------------------------------------------------------------------------------
# Natural stage (G2 machinery; the node row additionally carries the full-state SHA of every phase)
# ----------------------------------------------------------------------------------
case_info=G2.case_info
NAT_LIMIT=G1.NAT_LIMIT
dump_state=G1.dump_state
crc=G1.crc


def process_node3(run,node,exit_state,partial):
    """G2.process_node (same replays: reference / continuous / split / twice, independent model, scheduler exit digest) + the full-state SHA and PC of every phase boundary."""
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
        bank=c.states[-1]['bank'][0],banks_seen=sorted({s_['bank'][0] for s_ in c.states}|set(G1.pvc_banks_of(c))),bank_changes=sum(1 for p in c.pieces for x in p['ports'] if x[0]==1),
        leader_sha=sha(repr(res['leaders']).encode())[:16],leader_len=len(res['leaders']),run_hits=run_hits,hits_eq=(run_hits==len(res['leaders']) and sorted(hits)==sorted(set(res['leaders']))),
        succ=dict(consumer_pairs3(env,res['leaders'])),config=sha(repr((node['cb'],sorted(hits))).encode())[:16],
        phase_digests=list(c.digests),phase_pcs=[s_['pc'] for s_ in c.states],phase_ccr=[s_['ccr'] for s_ in c.states],ports_sha=G1.ports_sha(c.ports_all),ports=len(c.ports_all))
    if not res['model_ok']:row['model_diffs']=res['model_diffs']
    first=[];seen=set()
    for pc in res['leaders']:
        if pc not in seen:seen.add(pc);first.append(pc)
    row['leaders_first']=first
    row['xfers']=[[p['unit'],p['trace'][-1][0] if p['trace'] else None,c.states[p['end']]['pc']] for p in c.pieces if p['unit']]
    if plan:
        row['captures']={}
        if plan.get('full'):
            row['dumps']=dict(entry=dump_state(entry),states=[dump_state(s_) for s_ in c.states],exit=dump_state(c.states[-1]))
        for pc in plan.get('starts',()):
            fl=G1.Flow(env,entry,'ref',(pc,),NAT_LIMIT).run()
            if fl.final['kind']=='stop' and fl.final['detail']['pc']==pc:row['captures'][pc]=dump_state(fl.states[-1])
        if plan.get('entry'):row['entry_dump']=dump_state(entry)
    return row


def pass_b_task3(case):
    kind,seed,ans=case_info(case)
    run,sd,meta,prep=G2.make_run(case);run.case_id=case;run.node_task=process_node3;run.run()
    rr=G2.rec_of(case);tail=[p['end'] for p in run.pass_records][-3:]
    mine0=[n['cb'] for n in run.pass_records[0]['nodes']]
    if kind=='base' and seed in G2.EXEMPT_CASES:
        rec0=G2.recorded_first_pass_cbs(case)
        check=dict(frames=(run.frames_done,rr['frames_done']),tail_eq=None,stop_eq=True,cb_eq=True,first_pass_prefix_eq=(mine0[:len(rec0)]==rec0),exempt=G2.EXEMPT_CASES[seed])
        check['stop_eq']=check['cb_eq']=bool(check['first_pass_prefix_eq']);check['frames']=(1,1)
    else:
        check=dict(frames=(run.frames_done,rr['frames_done']),tail_eq=(tail==rr['pass_end_tail']) if 'pass_end_tail' in rr else None,
            stop_eq=run.stop.get('reason')==rr['stop'].get('reason') and run.stop.get('frame')==rr['stop'].get('frame'),cb_eq=G2.recorded_cb_counts(case)==dict(run.cb_counts))
    return dict(case=case,record=kind,seed=seed,kind=sd['kind'],family=sd['family'],stop=run.stop,frames_done=run.frames_done,run_digest=run.digest.hexdigest(),cb=dict(run.cb_counts),
        unit_nodes=run.unit_nodes,nodes=run.node_rows,meta=meta,prep=(R.prep_summary(prep) if prep else None),ipcs=sorted(run.ipcs),waits=dict(run.waits_total),check=check)


def stage_natural3(env,args,out_dir,cases):
    ctx=multiprocessing.get_context('fork')
    GLOBAL.update(plan={})
    with ctx.Pool(args.workers) as pool:a_list=pool.map(G2.pass_a_task,cases,chunksize=1)
    plan=collections.defaultdict(lambda:dict(starts=[],full=False,entry=False,sample=False))
    first_start={};cb_nodes=collections.defaultdict(list);configs=set();used_seeds=collections.Counter()
    for a in a_list:
        kind=case_info(a['case'])[0];seen_cb=set()
        for frame,seq,cb,hits,partial in a['nodes']:
            for pc in hits:
                if pc not in first_start:first_start[pc]=(a['case'],frame,seq)
            if len(cb_nodes[cb])<2:cb_nodes[cb].append((a['case'],frame,seq))
            cfg_=(cb,tuple(hits))
            if cfg_ not in configs:configs.add(cfg_);plan[(a['case'],frame,seq)]['sample']=True
            if a['kind']=='natural' and cb not in seen_cb and used_seeds[kind]<8:seen_cb.add(cb);cb_nodes.setdefault(('seed',a['case']),[]).append((a['case'],frame,seq))
        if a['kind']=='natural' and a['nodes'] and used_seeds[kind]<8:used_seeds[kind]+=1
    for pc,ref in sorted(first_start.items()):plan[ref]['starts'].append(pc)
    for k,v in cb_nodes.items():
        for ref in v:plan[ref]['full']=True;plan[ref]['entry']=True
    GLOBAL['plan']=dict(plan)
    with ctx.Pool(args.workers) as pool:b_list=pool.map(pass_b_task3,cases,chunksize=1)
    return a_list,b_list,first_start


# ----------------------------------------------------------------------------------
# Fixture machinery (declared states = captured natural state + recorded edits); G2 helpers re-used
# ----------------------------------------------------------------------------------
STACK_TOP=G2.STACK_TOP
cand_json2=G2.cand_json2
apply_cand2=G2.apply_cand2
entry_cand=G2.entry_cand
apply_post=G2.apply_post
build_start2=G2.build_start2
recipe_fixture2=G2.recipe_fixture2
run_fixtures=G2.run_fixtures
GUARD_FAMILIES=G2.GUARD_FAMILIES
memory_kinds=G2.memory_kinds
BANK_SWEEP=G2.BANK_SWEEP
CONSUMER_CCR=G2.CONSUMER_CCR
A5R=0x108000
POOL32=(0,1,2,0xff,0x100,0x7fff,0x8000,0xffff,0x10000,0x7fffffff,0x80000000,0xffff0000,0xffffffff,0x12345678,0x4fff,0x5000)


def unit_entries(b_list,env):return G2.unit_entries(b_list,env)


def arith_fixtures(env,rec):
    """Operand edge values for every block that contains DIVU / DIVS / ADDX / SUBX / MULU / MULS: all registers equal to one edge value (7 variants), twelve pseudo random register / CCR / node-WORD
    variants, and for a DIVU / DIVS whose first instruction is the divider the explicit divisor x dividend grid (divide by zero, quotient overflow).  Declared post-edits at the block start."""
    out=[]
    for s in sorted(env.starts):
        ar=env.ana[s]['arith']
        if not ar:continue
        rc=rec.get(s)
        if rc is None:continue
        u=env.starts[s];mdl=new_model(env);insns=[mdl.decode(pc) for pc in env.cfg[s]['insns']]
        a6mem=[]
        for ins in insns:
            for ea in (ins.src,ins.dst):
                if ea and ea[0]=='d16' and ea[1]==6:a6mem.append((ea[2]&0xffff,ins.size or 2))
        def mk(name,tag,regs,ccr,mems,why):
            fx=recipe_fixture2(name,'arith-edge',rc,u,[s],why)
            fx['at']=s;fx['post']=dict(regs=regs,ram={},ccr=ccr,a6mem=mems or None);fx['tag']=tag;return fx
        for v in (0,1,0x8000,0xffff,0xffffffff,0x5000,0x4fff):
            out.append(mk('arith %x all=%x'%(s,v),'all%x'%v,{('d%d'%i):v for i in range(8)},0x10,[(d,sz,v) for d,sz in a6mem],'block %x (%s): every data register and every node field the block reads := %x, X set'%(s,'/'.join(sorted(set(ar))),v)))
        for k in range(12):
            rng=random.Random(crc('arith',s,k));regs={('d%d'%i):rng.choice(POOL32) for i in range(8)};ccr=rng.randrange(32)
            mems=[(d,sz,rng.choice(POOL32)) for d,sz in a6mem]
            out.append(mk('arith %x r%02d'%(s,k),'r%02d'%k,regs,ccr,mems,'block %x (%s): pseudo random edge values (seed crc arith,%x,%d), CCR %02x'%(s,'/'.join(sorted(set(ar))),s,k,ccr)))
        ins0=insns[0]
        if ins0.op in('divu','divs'):
            for dsr in (0,1,0x50,0xffff):
                for dvd in (0xffff,0x10000,0x12345678,0xffffffff,0x7fff0000):
                    regs={('d%d'%ins0.reg):dvd};mems=None
                    if ins0.src[0]=='dn':regs['d%d'%ins0.src[1]]=(dsr if ins0.src[1]!=ins0.reg else dvd)
                    elif ins0.src[0]=='d16' and ins0.src[1]==6:mems=[(ins0.src[2]&0xffff,2,dsr)]
                    out.append(mk('divide %x dsr=%04x dvd=%08x'%(s,dsr,dvd),'div%04x_%08x'%(dsr,dvd),regs,0,mems,'block %x starts with the divider: divisor %04x, dividend %08x'%(s,dsr,dvd)))
    return out


def hand_fixtures3(env,fs):
    rec=fs['recipes'];out=[];ana=env.ana;cfg=env.cfg
    # H1 carry consumers: declared CCR at the consumer; the native branch outcome is the evidence
    for s in sorted(env.consumers):
        rc=rec.get(s)
        if rc is None:continue
        u=env.starts[s]
        for ccr in CONSUMER_CCR:
            fx=recipe_fixture2('carry-consumer %x ccr=%02x'%(s,ccr),'carry-consumer',rc,u,[s],'consumer %x reads C from its caller: declared CCR %02x at the block start (branch outcome of the native run)'%(s,ccr))
            fx['at']=s;fx['post']=dict(regs={},ram={},ccr=ccr);fx['tag']='ccr%02x'%ccr;out.append(fx)
    # H1b other flag readers at a block start (N / Z / V / signed conditions): the contract's N recomputation blocks and the Scc / DBcc blocks; both outcomes of the condition
    mdl=new_model(env)
    for s in G1.carry_consumers(env):
        if s in env.consumers:continue
        rc=rec.get(s)
        if rc is None:continue
        ins=mdl.decode(s);u=env.starts[s]
        for ccr in G1.CCR_VARIANTS.get(ins.cond,(0,1)):
            fx=recipe_fixture2('flag-reader %x ccr=%02x'%(s,ccr),'flag-reader',rc,u,[s],'block %x starts with %s cond %d: flags come from the previous block; declared CCR %02x at the block start'%(s,ins.op,ins.cond,ccr))
            fx['at']=s;fx['post']=dict(regs={},ram={},ccr=ccr);fx['tag']='ccr%02x'%ccr;out.append(fx)
    # H2 arithmetic edge values
    out+=arith_fixtures(env,rec)
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
    # H6 28ae / 2986 child creation failure / success at the JSR blocks
    for s in sorted(env.starts):
        if not ana[s]['callfail']:continue
        rc=rec.get(s)
        if rc is None:continue
        u=env.starts[s]
        for v,nm in ((0,'fail'),(0x7fff,'ok')):
            fx=recipe_fixture2('28ae-%s %x'%(nm,s),'28ae-%s'%nm,rc,u,[s],'JSR 28ae / 2986 block %x with WORD 104ca0 := %04x (child creation %s)'%(s,v,'fails (D0.W >= 104ca0)' if v==0 else 'succeeds'))
            fx['at']=s;fx['post']=dict(regs={},ram={0x4ca0:v>>8,0x4ca1:v&0xff},ccr=None);fx['tag']=nm;out.append(fx)
    return out


def stage_fixtures3(env,args,b_list,out_dir):
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
    cfg=env.cfg
    GLOBAL['dvals']=sorted(set(v for u in UIDS for v in G1.dict_values(env,u)));GLOBAL['htab']=G1.hint_table(env);GLOBAL['fix_limit']=20_000
    targets=[pc for pc in sorted(env.starts) if pc not in nat]
    dist={t:G1.cfg_distance(cfg,t) for t in targets}
    recipes={}
    for pc in sorted(env.starts):
        if pc in nat and pc in origins:recipes[pc]=dict(kind='natural',origin_pc=pc,origin=origins[pc],cand=G1.empty_cand())
    rounds=[];pending=list(targets);pseudo={}
    extra,entries_by_unit=cfg_check3(env,cfg)
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
        tasks=[(allo[o][0],o,sorted(ts),crc('c3a',o,rnd),args.budget) for o,ts in sorted(groups.items())]
        GLOBAL['plan']={}
        with ctx.Pool(args.workers) as pool:res=pool.map(G1.campaign_task,tasks,chunksize=1)
        for r in res:
            for tt,cand in sorted(r['found'].items()):
                if tt not in recipes:
                    if r['origin_pc'] in pseudo:
                        row,ref,o=pseudo[r['origin_pc']];recipes[tt]=dict(kind='path-from-entry',origin_pc=r['origin_pc'],origin=(row,ref),cand=cand,round=rnd)
                    else:recipes[tt]=dict(kind='path',origin_pc=r['origin_pc'],origin=origins[r['origin_pc']],cand=cand,round=rnd)
            rounds.append(dict(round=rnd,origin=hx(r['origin_pc']),asked=[hx(x) for x in r['asked']],found=[hx(x) for x in sorted(r['found'])],stats=r['stats']))
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
                if st is not None:new_orig[tt]=(dump_state(st),('typed:'+hx(rc['origin_pc']),0,0))
        allo=dict(origins);allo.update(new_orig)
        groups=collections.defaultdict(list)
        for tt in pend:
            cands=sorted((d,o) for o in allo for d in [dist[tt].get(o)] if d is not None and o in new_orig)
            if cands:groups[cands[0][1]].append(tt)
        tasks=[(allo[o][0],o,sorted(ts),crc('c3b',o,rnd),args.budget) for o,ts in sorted(groups.items())]
        GLOBAL['plan']={}
        with ctx.Pool(args.workers) as pool:res=pool.map(G1.campaign_task,tasks,chunksize=1)
        for r in res:
            for tt,cand in sorted(r['found'].items()):
                if tt not in recipes:recipes[tt]=dict(kind='path2',origin_pc=r['origin_pc'],origin=allo[r['origin_pc']],cand=cand,round=rnd)
            rounds.append(dict(round=rnd,origin=hx(r['origin_pc']),asked=[hx(x) for x in r['asked']],found=[hx(x) for x in sorted(r['found'])],stats=r['stats']))
        pending=[tt for tt in pending if tt not in recipes and tt not in pseudo]
    for e,(row,ref,o) in sorted(pseudo.items()):
        if e not in recipes:recipes[e]=dict(kind='entry-self',origin_pc=o,origin=origins[o],cand=dict(regs={},ram={},ccr=0,pc=e))
    # last resort: declared node-level entry at the block (A7 = SPd-4, LONG 2ac2) from a node entry dump of the unit
    for tt in pending:
        u=env.starts.get(tt) or 0
        erow,eref=ent.get(u) or ent['any']
        recipes[tt]=dict(kind='entry-declared',origin_pc=0x2ab8,origin=(erow,eref),cand=entry_cand(tt))
    fallback=sorted(tt for tt,rc in recipes.items() if rc['kind'] in ('entry-self','entry-declared'))
    # blocks that natural frames reach but no node dump captured (cannot happen for first_start blocks): none expected; recorded
    missing_origin=sorted(pc for pc in env.starts if pc in nat and pc not in origins)
    return dict(origins=origins,entries=entries,ent=ent,nat=nat,nat_xfer_to=nat_xfer_to,cfg=cfg,recipes=recipes,rounds=rounds,fallback=fallback,targets=targets,extra=extra,entries_by_unit=entries_by_unit,missing_origin=missing_origin)


def stage_verify3(env,args,fs,b_list,out_dir):
    ctx=multiprocessing.get_context('fork');origins=fs['origins']
    gtasks=[];by_unit=collections.defaultdict(list)
    for o in sorted(origins):
        u=env.starts.get(o)
        if u:by_unit[u].append(o)
    for u in sorted(by_unit):
        lst=by_unit[u];pick=lst[::max(1,len(lst)//3)][:3]
        for o in pick:gtasks.append((origins[o][0],o,crc('g3',o),args.budget//2))
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:gres=pool.map(G1.guard_task,gtasks,chunksize=1)
    fixtures=[];groups=collections.OrderedDict()
    for tt,rc in sorted(fs['recipes'].items()):
        if rc['kind']=='natural':continue
        key=(rc['origin_pc'],sjson(cand_json2(rc['cand'])),rc['kind'])
        groups.setdefault(key,[]).append((tt,rc))
    for i,(key,lst) in enumerate(groups.items()):
        rc=lst[0][1];ts=[tt for tt,_ in lst];u=env.starts.get(ts[0])
        fixtures.append(recipe_fixture2('reach-%s-%03d'%(rc['kind'],i),rc['kind'],rc,u,ts,'search result: the minimized edit list reaches '+' '.join('%x'%x for x in ts)))
    fixtures+=hand_fixtures3(env,fs)
    gi=0
    for r in gres:
        row,ref=origins[r['origin_pc']]
        for (u,kind,pc),cand in sorted(r['guards'].items()):
            fixtures.append(dict(name='guard-%s-u%s-%x-%03d'%(kind,NAMES.get(u,u),pc,gi),kind='guard',unit=u,targets=[],cand=cand,origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=r['origin_pc'],how='natural+edits'),
                why='search result: %s at %x inside unit %s'%(kind,pc,NAMES.get(u,u))));gi+=1
    rows=run_fixtures(ctx,args,fixtures)
    return rows,fixtures,gres


# ----------------------------------------------------------------------------------
# Native one-block carry experiment (G2.carry_native_task) and the comparison with the contract classification
# ----------------------------------------------------------------------------------
carry_native_task=G2.carry_native_task
WANT_CLASS={'Clear':('clear',),'Set':('set',),'Computed':('data','clear','set'),'Invert':('data',)}


def stage_carry3(env,args,fs):
    ctx=multiprocessing.get_context('fork');tasks=[]
    for s,rc in sorted(fs['recipes'].items()):
        if s in env.starts:tasks.append((s,rc['origin'][0],rc['cand'],crc('carry3',s)))
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:res=pool.map(carry_native_task,tasks,chunksize=4)
    obs={r['start']:r for r in res}
    rep=dict(per_unit={});disc=[]
    for u in UIDS:
        c=env.contracts[u];starts=c['starts'];flow=set(c['flow']);prod=c['producers']
        bad=[];row=dict(observed=dict(collections.Counter(str(obs[s]['cls']) for s in starts if s in obs)),unobserved=[hx(s) for s in starts if s not in obs or obs[s]['cls'] is None])
        for s in sorted(flow):
            o=obs.get(s)
            if o and o['cls'] not in(None,'preserve'):bad.append(dict(what='contract FLOW_ONLY block does not preserve C (native)',start=hx(s),observed=o['cls']))
        for s,w in sorted(prod.items()):
            o=obs.get(s)
            if o and o['cls'] is not None and o['cls'] not in WANT_CLASS[w]:bad.append(dict(what='contract known %s producer (native)'%w,start=hx(s),observed=o['cls']))
        row['preserve_not_in_contract_flow']=[hx(s) for s in starts if s in obs and obs[s]['cls']=='preserve' and s not in flow and s not in prod]
        row['model_vs_native']=[dict(start=hx(s),model=('preserve' if env.ana[s]['c_written'] is None else 'written'),native=obs[s]['cls']) for s in starts if s in obs and obs[s]['cls'] is not None and
            ((env.ana[s]['c_written'] is None)!=(obs[s]['cls']=='preserve'))]
        row['contract_flow_n']=c['flow_n'];row['contract_flow_listed']=len(flow);row['discrepancies']=bad
        row['observed_by_start']={hx(s):obs[s]['cls'] for s in starts if s in obs}
        rep['per_unit'][u]=row
        for b in bad:disc.append(dict(id='%s-carry'%NAMES[u],claim='contract carry classification vs native one-block experiment (C_in 0/1 x 8 register variants, exact CCR probe)',detail=b))
        if c['flow_n'] is not None and len(flow)!=c['flow_n']:disc.append(dict(id='%s-flow-count'%NAMES[u],claim='contract FLOW_ONLY count vs listed pcs',detail=dict(stated=c['flow_n'],listed=len(flow))))
        if c['consumers_n'] is not None and len(c['consumers'])!=c['consumers_n']:disc.append(dict(id='%s-consumer-count'%NAMES[u],claim='contract consumer count vs listed pcs',detail=dict(stated=c['consumers_n'],listed=len(c['consumers']))))
        if len(prod)!=PRODUCERS_STATED[u]:disc.append(dict(id='%s-producer-count'%NAMES[u],claim='contract known producer count vs transcribed list',detail=dict(stated=PRODUCERS_STATED[u],listed=len(prod))))
    rep['observed_classes']=dict(collections.Counter(str(r['cls']) for r in res))
    return rep,disc,obs


# ----------------------------------------------------------------------------------
# Contract data claims that can be checked against the ROM bytes, contract text vs decoded instructions, call lists
# ----------------------------------------------------------------------------------
def data_checks3(env):
    """Every 'N바이트 ... SHA256 `h`' statement of the contracts that is not the code range table: the nearest preceding backticked fixed-ROM address with the stated size must hash to h."""
    prog=env.program;rows=[];skip=set()
    for u in UIDS:
        c=env.contracts[u];t=c['text']
        skip|={h for _,_,_,h in c['range_rows']}
        m=re.search(r'합계 [\d,]+바이트[^`]*`([0-9a-f]{64})`',t)
        if m:skip.add(m.group(1))
    for u in UIDS:
        t=env.contracts[u]['text']
        for m in re.finditer(r'SHA256 `([0-9a-f]{64})`',t):
            h=m.group(1)
            if h in skip or h==ROM_SHA:continue
            win=t[max(0,m.start()-260):m.start()]
            if not re.search(r'fixed ROM',win[-200:]):continue                 # only statements about fixed ROM data (the other SHA256 values are sources / reports)
            sizes=[int(x.replace(',','')) for x in re.findall(r'([\d,]+)바이트',win)]+[4*int(x) for x in re.findall(r'\((\d+) LONG',win)]+[2*int(x) for x in re.findall(r'\((\d+) WORD',win)]
            addrs=[int(x,16) for x in re.findall(r'`([0-9a-f]{4,6})`',win) if int(x,16)<0x100000]
            ok=None
            for sz in reversed(sizes):
                for a in reversed(addrs):
                    if sha(prog[a:a+sz])==h:ok=(a,sz);break
                if ok:break
            rows.append(dict(unit=NAMES[u],sha=h,matched=bool(ok),address=hx(ok[0]) if ok else None,size=ok[1] if ok else None,sizes=sizes[-2:],addresses=[hx(x) for x in addrs[-3:]],context=win[-80:].replace('\n',' ')))
    return rows


block_texts=G2.parse_block_texts
render_ins=G2.render_ins


def block_text_check3(env):
    stats={};disc=[]
    for u in UIDS:
        c=env.contracts[u];texts=block_texts(u,c['text']);cmp_n=0;bad=[]
        for s in c['starts']:
            if s not in texts:continue
            mdl=new_model(env);dec=[render_ins(mdl.decode(pc)) for pc in env.cfg[s]['insns']]
            exp=texts[s]
            if '?' in exp or 'D' in exp or 'A' in exp:continue
            def eq(e,d):
                mn,sz=d
                if e==mn or (e=='DBRA' and mn=='DBF'):return True
                if '.' in e:
                    en,es=e.split('.');return en==mn and (sz is None or es==sz)
                return False
            got=[mn+('.'+sz if sz else '') for mn,sz in dec]
            ok=len(exp)==len(dec) and all(eq(e,d) for e,d in zip(exp,dec))
            cmp_n+=1
            if not ok:bad.append(dict(start=hx(s),contract=exp,rom=got))
        stats[NAMES[u]]=dict(blocks_with_text=len(texts),compared=cmp_n,mismatches=len(bad))
        if bad:disc.append(dict(id='%s-block-text'%NAMES[u],claim='contract block line (mnemonic + size per instruction) vs the instructions decoded from the ROM bytes (where the line spells the instructions out)',detail=bad[:40]))
    return stats,disc


def call_site_check3(env):
    """Contract 'outgoing calls' bullet: every named target must be reached by a transfer of the unit; where call sites are listed they must be the blocks that contain the transfers."""
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
        t=env.contracts[u]['text'];m=re.search(r'^- \[F\] \*\*나가는 호출[^\n]*',t,re.M)
        if not m:stats[NAMES[u]]=dict(parsed=False);continue
        line=m.group(0);named=0;bad=[];ok=0
        for mt in re.finditer(r'`([0-9a-f]{3,6})`(?:\(([^)]*)\))?',line[line.index(':'):]):
            tg=int(mt.group(1),16)
            if env.unit_of(tg)==u:continue
            named+=1;acts=actual[u].get(tg,set())
            if not acts:bad.append(dict(target=hx(tg),problem='no transfer of the unit goes to this named target'));continue
            body=mt.group(2) or ''
            sites=[int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`',body)]
            if sites:
                cb={blk.get(x,x) for x in sites};ab={blk[x] for x in acts}
                if cb==ab:ok+=1
                else:bad.append(dict(target=hx(tg),contract_only=sorted(hx(x) for x in cb-ab),rom_only=sorted(hx(x) for x in ab-cb)))
            else:ok+=1
        stats[NAMES[u]]=dict(parsed=True,named_targets=named,equal=ok,different=len(bad))
        if bad:disc.append(dict(id='%s-call-sites'%NAMES[u],claim='contract list of outgoing calls (target and call-site blocks) vs the control transfers decoded from the ROM bytes',detail=bad))
    return stats,disc


# ----------------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------------
GUARD_TEXT=dict(G1.GUARD_TEXT)
GUARD_TEXT['cpu-exception']='the Unicorn interrupt hook fired (illegal opcode, DIVU / DIVS by zero = vector 5 at the dividing instruction with registers unchanged, TRAP ...); the model raises zero-divide for the division case'
LIMITATIONS=[
    'The frame passes (base 120 / 400 frames and RNG-initialised 400 frames), the node entry form (PC 2ab8, A6 = node, A7 = SPd, CCR 0) and the declared waits / bios-card answers are the scheduler observers declared models, not natural execution; no BIOS, IRQ or scheduler is claimed.',
    'The routing source parse of the scheduler observer cannot read the newest routing chain: the coverage flags use an all-routed bitmap and the 120 -> 400 frame extension is taken from the recorded base artifact (frames_done > 120); the recorded pass-end digests, stop reasons and frame counts of all 290 cases are compared with the artifacts (check.* in natural.seed_rows).',
    'An illegal opcode ABORTS the Unicorn m68k translator (process abort); the fixture search therefore runs in a forked child and poisons the aborting candidate (counted in the search rounds).',
    'The Unicorn SR read is stale for V / C (lazy flags); the observer reads the exact CCR with a MOVE SR,D0 probe at 500000 at every piece boundary and never from the Unicorn SR.',
    'Natural nodes: reference / continuous / independent model (PC + 16 registers per instruction) for every node, split for the sampled nodes (first node of every distinct callback / block path and a modular sample), twice for the sampled subset; the whole tool is run twice and the outputs are compared.',
    'The carry classification experiments run the block natively from a captured state with a declared CCR; blocks with no completed variant are listed as unobserved.',
    'Typed fixtures are declared states (natural capture + recorded edit list); kind entry-self / entry-declared means the search did not reach the block by a path within the budget and the fixture enters the block directly (entry-declared: node level form A7 = SPd-4, LONG 2ac2).',
    'The model leaves N / Z undefined after a DIVU / DIVS quotient overflow (68000: undefined) and compares only flags it defines; the native flags after an overflow are whatever Unicorn computes.',
    'The undecodable word of a linear scan becomes an op "unsupported" instruction (count reported per unit); executing it is a model "unsupported" guard.']


def claim(cid,text,expected,observed,verdict,note=''):return G1.claim(cid,text,expected,observed,verdict,note)


def piece_entry_kinds(env,node_rows,typed_rows):
    """Unit pieces whose first PC is / is not a contract block start of the unit (interior landings: merged blocks, computed targets)."""
    cnt=collections.defaultdict(collections.Counter);interior=collections.defaultdict(collections.Counter)
    for pu,a,last,b,ni,ok in [p for n in node_rows for p in n['pieces']]+[p for r in typed_rows for p in (r.get('pieces') or [])]:
        if env.starts.get(a)==pu:cnt[pu]['block-start']+=1
        else:cnt[pu]['interior']+=1;interior[pu][a]+=1
    return {NAMES.get(pu,pu):dict(cnt[pu],interior_pcs={hx(a):n for a,n in sorted(interior[pu].items())}) for pu in sorted(cnt)}


def build_report3(env,args,a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,out_dir,t0,rom_start,dchk):
    cases=[b['case'] for b in b_list];nat=fs['nat'];cfg=fs['cfg'];ana=env.ana
    node_rows=[(b['case'],case_info(b['case'])[0],n) for b in b_list for n in b['nodes']]
    eqc=collections.Counter();modelc=collections.Counter();finalc=collections.Counter();guardc=collections.Counter();pieces=0;insns=0;xf=collections.Counter();phases=0
    nat_by_rec=collections.defaultdict(collections.Counter);hits_eq=collections.Counter();succ_nat=collections.defaultdict(collections.Counter);seeds_by_unit=collections.defaultdict(set)
    nodes_by_unit=collections.defaultdict(collections.Counter);phases_by_unit=collections.defaultdict(collections.Counter)
    for case,rk,n in node_rows:
        for k,v in n['eq'].items():eqc[(k,v)]+=1
        modelc[n['model_ok']]+=1;finalc[n['final']]+=1;pieces+=len(n['pieces']);insns+=n['insns'];hits_eq[n['hits_eq']]+=1;phases+=len(n['phase_digests'])-1
        if n['guard']:guardc[n['guard']]+=1
        for pc in n['leaders_first']:nat_by_rec[rk][pc]+=1
        units_in=set()
        for u,last,to in n['xfers']:xf[(u,last,to)]+=1;units_in.add(u)
        for pu,a,last,b,ni,ok in n['pieces']:
            if pu:phases_by_unit[pu][rk]+=1
        for u in units_in:nodes_by_unit[u][rk]+=1;seeds_by_unit[u].add((rk,case_info(case)[1]))
        for k,v in n['succ'].items():succ_nat[rk][k]+=v
    sched_exit=collections.Counter(n['sched_exit_eq'] for case,rk,n in node_rows)
    banks=collections.Counter(hx(n['bank']) for case,rk,n in node_rows);banks_seen=collections.Counter(hx(b) for case,rk,n in node_rows for b in n['banks_seen']);pvc_nodes=sum(1 for case,rk,n in node_rows if n['bank_changes'])
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
    ranges_ins={u:env.contracts[u]['ins'] for u in UIDS}
    extra_derived,entries=fs['extra'],fs['entries_by_unit']
    units=[];discrep=[]
    for u in UIDS:
        c=env.contracts[u];st=c['starts'];nm=NAMES[u];stated=c['stated']
        nat_u=[pc for pc in st if pc in nat];typ_u=[pc for pc in st if pc in typed and pc not in nat];un=[pc for pc in st if pc not in nat and pc not in typed]
        mine_un=sorted(pc for pc in st if pc not in nat)
        by_rec={rk:len([pc for pc in st if pc in nat_by_rec[rk]]) for rk in ('base','rng','rng00')}
        union_rng=len([pc for pc in st if pc in nat_by_rec['rng'] or pc in nat_by_rec['rng00']])
        ops=collections.Counter(i.op for i in ranges_ins[u].values());ninsn=len(ranges_ins[u])
        if stated['blocks']!=len(st):discrep.append(dict(id='%s-blocks'%nm,claim='contract block count vs parsed block starts',detail=dict(stated=stated['blocks'],parsed=len(st),notes=c['parse_notes'])))
        if stated['insns'] is not None and stated['insns']!=ninsn:discrep.append(dict(id='%s-instructions'%nm,claim='contract instruction count vs model decoder',detail=dict(contract=stated['insns'],decoded=ninsn)))
        if ops.get('unsupported',0):discrep.append(dict(id='%s-undecodable'%nm,claim='all code bytes of the ranges decode with the model decoder',detail=sorted(hx(pc) for pc,i in ranges_ins[u].items() if i.op=='unsupported')))
        if ops.get('trap',0):discrep.append(dict(id='%s-trap'%nm,claim='contract: no TRAP inside the ranges',detail=ops.get('trap')))
        evenpcs=sum((b-a)//2 for a,b in c['ranges'])
        if stated['even'] is not None and evenpcs!=stated['even']:discrep.append(dict(id='%s-even-pcs'%nm,claim='contract routing even PC count',detail=dict(contract=stated['even'],computed=evenpcs)))
        if stated['interior'] is not None and stated['even'] is not None and stated['even']-len(st)!=stated['interior']:
            discrep.append(dict(id='%s-interior-pcs'%nm,claim='contract interior PC count = even PCs - block starts',detail=dict(contract=stated['interior'],computed=stated['even']-len(st))))
        ex=extra_derived[u]
        if ex:discrep.append(dict(id='%s-cfg-leaders-not-in-contract'%nm,claim='decoder derived branch / fall-through / call targets inside the unit that the contract does not list as block starts (bound Bcc / merged blocks)',detail=[hx(x) for x in ex]))
        derived_not=[hx(x) for x in c['derived'] if x not in st]
        bnd={};
        for pc in c['boundary']:
            fx_hit=[r['name'] for r in ok_rows if (r['final']=='stop' and r['final_detail'].get('pc')==pc) or any(x[2]==pc for x in r['xfers']) or any(x[2]==pc for x in (r.get('through') or {}).get('xfers',[]))][:3]
            bnd[hx(pc)]=dict(kind='callee',natural_transfer=pc in fs['nat_xfer_to'],typed_fixtures=fx_hit)
        for pc in c['traps']:
            fx_hit=[r['name'] for r in ok_rows if r['final']=='stop' and r['final_detail'].get('pc')==pc][:3]
            bnd[hx(pc)]=dict(kind='trap',natural_transfer=pc in fs['nat_xfer_to'],typed_fixtures=fx_hit)
        ext=collections.defaultdict(list)
        for s0 in st:
            for tg in ana[s0]['external']:ext[tg].append(s0)
        ext_rows={hx(tg):dict(callers=[hx(x) for x in sorted(v)],target_unit=NAMES.get(env.unit_of(tg),'outside the G3 units')) for tg,v in sorted(ext.items())}
        for pc in c['boundary']:
            if pc not in ext:discrep.append(dict(id='%s-boundary-%x'%(nm,pc),claim='contract names %x as a boundary callee of the unit; no instruction of the unit transfers to it'%pc,detail=hx(pc)))
        cons=sorted(s_ for s_ in env.consumers if env.starts[s_]==u);prods=sorted(c['producers'])
        units.append(dict(unit=nm,uid=u,contract=contract_path(u).name,contract_sha=c['sha'],ranges=[[hx(a),hx(b)] for a,b in c['ranges']],code_bytes=c['bytes'],instructions=ninsn,instructions_contract=stated['insns'],ops=dict(ops),
            blocks_stated=stated['blocks'],blocks_parsed=len(st),parse_notes=c['parse_notes'],derived_leaders_not_blocks=derived_not,natural_reached=len(nat_u),natural_reached_by_record=by_rec,natural_reached_rng_union=union_rng,typed_only_reached=len(typ_u),
            model_segments=dict(seg[u]),guards=dict(natural=dict(nat_guard_by_unit[u]),typed=dict(typed_guard_by_unit[u])),union_reached=len(nat_u)+len(typ_u),unreached=[hx(x) for x in un],natural_unreached=[hx(x) for x in mine_un],typed_by_kind={},
            boundary=bnd,boundary_named_inside_g3=[hx(x) for x in c['boundary_in_g3']],cfg_entries_not_derived=[hx(x) for x in entries[u]],external_targets=ext_rows,flow_only=len(c['flow']),flow_only_stated=c['flow_n'],
            producers={hx(k):v for k,v in c['producers'].items()},consumers=[hx(x) for x in cons],consumers_stated=c['consumers_n'],
            natural_nodes=dict(nodes_by_unit[u]),natural_phases=dict(phases_by_unit[u]),natural_seeds={rk:sorted(sd for r_,sd in seeds_by_unit[u] if r_==rk) for rk in ('base','rng','rng00')},
            natural_nodes_per_start={hx(pc):sum(nat_by_rec[rk][pc] for rk in nat_by_rec) for pc in nat_u}))
    for r in ok_rows:
        for pc in r['reached']:
            u=env.starts.get(pc)
            if u and pc not in nat:
                d=units[UIDS.index(u)]['typed_by_kind'];d.setdefault(r['kind'],[]).append(hx(pc))
    for d in units:
        for k in d['typed_by_kind']:d['typed_by_kind'][k]=sorted(set(d['typed_by_kind'][k]))
    # consumers: declared CCR outcomes, natural and typed real-producer pairs
    cons_rows=[];succ_typed=collections.Counter();succ_nat_all=collections.Counter()
    for rk in succ_nat:succ_nat_all.update(succ_nat[rk])
    for r in ok_rows:
        if r['kind'] not in('carry-consumer',):
            for k,v in r['succ'].items():succ_typed[k]+=v
            for k,v in ((r.get('through') or {}).get('succ') or {}).items():succ_typed[k]+=v
    declared=collections.defaultdict(dict)
    for r in rows:
        if r['kind']=='carry-consumer':
            s0=r['targets'][0];ccr=int(r['tag'][3:],16);nxt=[k.split('>')[1] for k in r['succ'] if k.startswith('%x>'%s0)]
            declared[s0][ccr]=dict(next=(nxt[0] if nxt else None),final=r['final'],ok=r['ok'])
    for s0 in sorted(env.consumers):
        d=declared.get(s0,{});c0=d.get(0x00,{}).get('next');c1=d.get(0x01,{}).get('next');c2=d.get(0x1e,{}).get('next');c3=d.get(0x1f,{}).get('next')
        nat_pairs={k:v for k,v in succ_nat_all.items() if k.startswith('%x>'%s0)}
        typed_pairs={k:v for k,v in succ_typed.items() if k.startswith('%x>'%s0)}
        chain={k:succ_nat_all.get(k,0)+succ_typed.get(k,0) for k in set(succ_nat_all)|set(succ_typed) if k.startswith('p') and k.split('>')[1]=='%x'%s0}
        first=new_model(env).decode(s0)
        row=dict(consumer=hx(s0),unit=NAMES[env.starts[s0]],first_op=first.op,declared={('%02x'%k):v for k,v in sorted(d.items())},c_only_dependence=(c0==c2 and c1==c3),outcomes_differ=(c0!=c1),
            contract_listed=s0 in env.contract_consumers,model_derived=s0 in env.model_consumers,natural_pairs=nat_pairs,typed_real_producer_pairs=typed_pairs,producer_chains=chain)
        cons_rows.append(row)
        row['control_flow_consumer']=first.op=='bcc' and first.target!=s0+first.len
        if s0 in env.model_consumers and row['control_flow_consumer'] and (not row['c_only_dependence'] or not row['outcomes_differ']):
            discrep.append(dict(id='%s-consumer-%x'%(NAMES[env.starts[s0]],s0),claim='consumer outcome depends on C only (declared CCR 00/01/1e/1f, native branch)',detail=row['declared']))
    for s0 in sorted(env.model_consumers-env.contract_consumers):
        i0=new_model(env).decode(s0)
        if i0.op=='bcc' and i0.target==s0+i0.len:continue                  # BCC to the next instruction: the contract (N03 decision 3) treats it as a pass-through block, not a consumer
        discrep.append(dict(id='%s-consumer-unlisted'%NAMES[env.starts[s0]],claim='model finds a C consumer the contract does not list',detail=hx(s0)))
    for s0 in sorted(env.contract_consumers-env.model_consumers):discrep.append(dict(id='%s-consumer-not-model'%NAMES[env.starts[s0]],claim='contract lists a consumer the model does not find (data flow into the block through a non-Bcc first instruction, or a flag the block consumes only after other instructions)',detail=hx(s0)))
    oth=[(hx(s0),a['consumes']) for s0,a in sorted(ana.items()) if a['consumes'] not in(None,'C')]
    if oth:discrep.append(dict(id='flags-consumed-from-caller',claim='blocks that read N/Z/V/X before writing them (contract: every block makes and uses its own flags except the named N recompute blocks)',detail=oth))
    btext,bdisc=block_text_check3(env);discrep.extend(bdisc)
    csstats,csdisc=call_site_check3(env);discrep.extend(csdisc)
    # producer chains observed (natural + typed): the native branch outcome at the consumer must equal the declared-CCR outcome for the producer's claimed C
    chain_obs=collections.defaultdict(collections.Counter)
    for k,v in list(succ_nat_all.items())+list(succ_typed.items()):
        if k.startswith('p'):
            a_,b_,c3=k.split('>');chain_obs[(int(a_[1:],16),int(b_,16))][c3]+=v
    producer_chains=[]
    for u in UIDS:
        for p,w in sorted(env.contracts[u]['producers'].items()):
            row=dict(producer=hx(p),unit=NAMES[u],claim=w,consumers=[])
            cs_all=sorted({cs for (pp,cs) in chain_obs if pp==p})
            for cs in cs_all:
                dec=declared.get(cs,{});seen=dict(chain_obs.get((p,cs),{}))
                want=None
                if w in('Clear','Set'):
                    want=dec.get(0x00 if w=='Clear' else 0x01,{}).get('next');allowed={want}
                    lastins=new_model(env).decode(env.cfg[cs]['insns'][-1])
                    if lastins.op=='dbcc' and ((lastins.cond==5 and w=='Clear') or (lastins.cond==4 and w=='Set')):allowed.add(dec.get(0x01 if w=='Clear' else 0x00,{}).get('next'))
                    consistent=all(k in allowed for k in seen)
                    if seen and not consistent:discrep.append(dict(id='%s-producer-%x'%(NAMES[u],p),claim='known carry producer %x claims C=%s: the native branch outcome at consumer %x through the real producer differs from the declared-CCR outcome'%(p,w,cs),detail=dict(expected=sorted(x for x in allowed if x),observed=seen)))
                else:allowed=set();consistent=None
                row['consumers'].append(dict(consumer=hx(cs),expected_next=sorted(x for x in allowed if x),observed=seen,evidence=sum(seen.values()),consistent=consistent))
            row['evidence_total']=sum(sum(c_['observed'].values()) for c_ in row['consumers'])
            producer_chains.append(row)
    bank_rows=[r for r in rows if r['kind']=='pvc-bank'];bsum=collections.defaultdict(collections.Counter)
    for r in bank_rows:bsum[r['tag']]['%s%s'%(r['final'],('/'+r['final_detail'].get('kind','')) if r['final']=='guard' else '')]+=1
    gsum=collections.Counter()
    for r in ok_rows:
        if r['final']=='guard':gsum[(NAMES.get(r['unit'],r['unit']),r['final_detail']['kind'])]+=1
    gfam=collections.Counter()
    for r in rows:
        if r['kind']=='guard-family':gfam[(r['tag'],r['final'],r['final_detail'].get('kind') if r['final']=='guard' else '')]+=1
    div_rows=[dict(name=r['name'],final=r['final'],final_detail=r['final_detail'],ok=r['ok']) for r in rows if r['kind']=='arith-edge' and r['name'].startswith('divide ')]
    claims=[]
    for u in UIDS:
        c=env.contracts[u];n=NAMES[u]
        claims.append(claim('%s-blocks'%n,'contract block start count (parsed block list)',c['stated']['blocks'],len(c['starts']),'matches' if len(c['starts'])==c['stated']['blocks'] else 'differs'))
        if c['stated']['insns'] is not None:claims.append(claim('%s-instructions'%n,'contract instruction count decoded by the observer model decoder',c['stated']['insns'],len(c['ins']),'matches' if len(c['ins'])==c['stated']['insns'] else 'differs'))
    claims.append(claim('NAT-record','recorded scheduler artifacts reproduced: frames, stop reason, callback counts and (where recorded) the last pass-end digests of every case',len(seed_rows),sum(v for (rk,ok),v in rec_check.items() if ok),'matches' if all(ok for (rk,ok) in rec_check) else 'differs'))
    claims.append(claim('NAT-nodes','every natural unit node: fresh-CPU ref == continuous (all), == split (%d nodes), twice (%d), scheduler exit reproduced, model equal on every unit piece (PC + registers per instruction), run-hook hits == replay leaders'%(sampled['split'],sampled['twice']),len(node_rows),
        dict(ref_cont=eqc[('ref_cont',True)],cont_split=eqc[('cont_split',True)],sched_exit=sched_exit[True],model=modelc[True],hits=hits_eq[True]),
        'matches' if all(eqc[(k,False)]==0 for k in ('ref_cont','cont_split','cont_twice','split_twice')) and sched_exit[False]==0 and modelc[False]==0 and hits_eq[False]==0 else 'differs'))
    claims.append(claim('TYPED-all-blocks','every contract block start reached naturally or by a typed fixture','0 unreached',sum(len(d['unreached']) for d in units),'matches' if not any(d['unreached'] for d in units) else 'differs'))
    claims.append(claim('TYPED-fixtures','typed fixtures: fresh-CPU ref == continuous == split, each twice, model equal on every unit piece',len(rows),len(ok_rows),'matches' if len(ok_rows)==len(rows) else 'differs',
        json.dumps([r['name'] for r in rows if not r['ok']][:20])))
    claims.append(claim('DATA-contract-values','contract data statements (N바이트 SHA256 of fixed ROM tables) equal the ROM bytes',len(dchk),sum(1 for x in dchk if x['matched']),'matches' if all(x['matched'] for x in dchk) else 'differs'))
    for x in dchk:
        if not x['matched']:discrep.append(dict(id='%s-data'%x['unit'],claim='contract data SHA256 statement could not be matched to ROM bytes by the heuristic (address, size)',detail=x))
    sizes=G1.dir_sizes(out_dir)
    report=dict(schema_version=1,tool='tools/observe_animation_machine_objects_g3.py',scope=__doc__,rom_stat_start=rom_start,limitations=LIMITATIONS,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000'),
        declared_model=dict(spd=SPD,pass_pc=PASS_PC,node_entry='PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd, CCR 0',stops='2ac2 (natural) / 2ac2, 2a00 and the boundary callees / TRAP pcs (fixtures; boundary stops are followed by a through run)',nat_limit=NAT_LIMIT,fix_limit=GLOBAL['fix_limit'],
            probe='CCR probe: MOVE SR,D0 at 500000 (exact flags; a plain SR read is stale for V / C)',waits='sound 3aea / sprite cda4 declared releases as the scheduler observer; bios-card answer 80 (RNG record) and 00 (variants of seeds 0..5)',
            bank_model='observe_animation_machine_pvc_banks.PvcMachine (any PVC selectable bank; bank-read-outside-rom guard)',records=dict(base_frames=G2.BASE_FRAMES,rng_frames=G2.RNG_FRAMES,base_artifact=GLOBAL['records']['base_sha'],rng_artifact=GLOBAL['records']['rng_sha']),
            rng_seed_prep='original 49a1a natively with D0 = 0 (R.run_prep, declared RAM change; registers stay the seed registers)',n02='N02 has no contract: the rescope (animation-machine-object-callbacks-f4-rescope.md) defined N02 = U20b (the 858d8 family) and it was integrated with U20 as G2 unit U20b'),
        inputs=dict(contracts={contract_path(u).name:UNITS[u]['sha'] for u in UIDS},tools={n:sha((ROOT/'tools'/n).read_bytes()) for n in ('observe_animation_machine_objects_g3.py','observe_animation_machine_objects_g2.py','observe_animation_machine_objects_g1.py','observe_animation_machine_scheduler.py','observe_animation_machine_scheduler_rng.py','observe_animation_machine_pvc_banks.py','address_map.py','disassemble_program.py')}),
        units=units,
        natural=dict(cases=len(cases),by_record=dict(collections.Counter(b['record'] for b in b_list)),seed_stop_reasons={'%s/%s'%k:v for k,v in sorted(collections.Counter((b['record'],b['stop'].get('reason')) for b in b_list).items())},unit_nodes=len(node_rows),unit_nodes_by_record=dict(collections.Counter(rk for c,rk,n in node_rows)),replays=sampled,record_check={'%s/%s'%k:v for k,v in sorted(rec_check.items())},
            final_banks=dict(banks),banks_selected_by_pvc_writes_natural=dict(banks_seen),banks_selected_by_pvc_writes_typed=dict(collections.Counter(hx(b) for r in rows for b in r.get('pvc_banks',[]))),nodes_with_pvc_writes=pvc_nodes,
            guard_explanations=GUARD_TEXT,pieces=pieces,phases=phases,unit_instructions=insns,distinct_unit_instruction_pcs=len(ipcs),total_unit_instructions=sum(len(env.contracts[u]['ins']) for u in UIDS),eq={('%s=%s'%k):v for k,v in sorted(eqc.items())},
            model_ok=dict(modelc),sched_exit_eq=dict(sched_exit),hits_eq=dict(hits_eq),final=dict(finalc),guards=dict(guardc),callbacks_hex=S.hexkeys(cb_total),seed_rows=seed_rows,
            consumer_pairs_natural={rk:dict(v) for rk,v in succ_nat.items()},piece_entries=piece_entry_kinds(env,[n for c,rk,n in node_rows],rows),
            xfers=[dict(unit=NAMES.get(u,u),last=hx(l) if l else None,to=hx(t),count=n) for (u,l,t),n in sorted(xf.items(),key=lambda kv:(kv[0][0],kv[0][1] or 0,kv[0][2]))]),
        typed=dict(fixtures=len(rows),ok=len(ok_rows),skipped_optional=[r['name'] for r in rows if r.get('skipped')],by_kind=dict(kinds),block_text_vs_rom=btext,call_sites_vs_rom=csstats,
            producer_chains=producer_chains,consumers=cons_rows,bank_sweep={k:dict(v) for k,v in sorted(bsum.items())},bank_sweep_banks=[[n,hx(b[0]),hx(b[1]),hx(b[2])] for n,b in BANK_SWEEP],
            guards_by_unit_kind={('%s/%s'%k):v for k,v in sorted(gsum.items(),key=lambda kv:str(kv[0]))},guard_families={('%s|%s|%s'%k):v for k,v in sorted(gfam.items())},divide_fixtures=div_rows,
            failure_28ae=[dict(name=r['name'],final=r['final'],leaders=[hx(x) for x in r['leaders_first'][:12]]) for r in rows if r['kind'].startswith('28ae')],
            search_rounds=fs['rounds'],fallback_entry=[hx(x) for x in fs['fallback']],missing_origin=[hx(x) for x in fs['missing_origin']]),
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
    program=G2.setup_sched();env=Env3();records=G2.load_records();analyze_units3(env)
    GLOBAL.update(env=env,program=program,out=out_dir,fix_limit=20_000,plan={},twice=False,records=records)
    cases=G2.case_list() if not args.cases else [int(x) for x in args.cases.split(',')]
    if args.load_stash:
        import pickle
        with open(args.load_stash,'rb') as f:a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,fx_sha,fx_size=pickle.load(f)
    else:
        a_list,b_list,first_start=stage_natural3(env,args,out_dir,cases)
        print('natural done',round(time.time()-t0),sum(b['unit_nodes'] for b in b_list),flush=True)
        for b in b_list:
            doc=dict(case=b['case'],record=b['record'],seed=b['seed'],kind=b['kind'],family=b['family'],stop=b['stop'],frames_done=b['frames_done'],meta=b['meta'],prep=b['prep'],run_digest=b['run_digest'],check=b['check'],nodes=b['nodes'],waits=b['waits'],
                cb=S.hexkeys(b['cb']),unit_nodes=b['unit_nodes'],ipcs=b['ipcs'])
            S.write_gz(out_dir/'seeds'/('case_%04d.json.gz'%b['case']),doc)
        if args.natural_only:return a_list,b_list
        fs=stage_fixtures3(env,args,b_list,out_dir)
        print('fixture search done',round(time.time()-t0),len(fs['recipes']),'fallback',len(fs['fallback']),flush=True)
        rows,fixtures,gres=stage_verify3(env,args,fs,b_list,out_dir)
        print('fixtures done',round(time.time()-t0),len(rows),sum(1 for r in rows if r['ok']),flush=True)
        fx_sha,fx_size=S.write_gz(out_dir/'fixtures.json.gz',dict(note='typed fixtures: declared edits over captured natural states, results of ref / continuous / split (each twice) and the model',fixtures=rows))
        carry,cdisc,cobs=stage_carry3(env,args,fs)
        print('carry done',round(time.time()-t0),flush=True)
        if args.stash:
            import pickle
            with open(args.stash,'wb') as f:pickle.dump((a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,fx_sha,fx_size),f,protocol=4)
    dchk=data_checks3(env)
    report=build_report3(env,args,a_list,b_list,fs,rows,fixtures,gres,carry,cdisc,cobs,out_dir,t0,rom_start,dchk)
    rom_end=S.rom_stat();assert rom_end==rom_start
    report['rom_stat_end']=rom_end;report['fixtures_file']=dict(file='fixtures.json.gz',sha256=fx_sha,size=fx_size)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(units=[(d['unit'],d['blocks_parsed'],d['natural_reached'],d['typed_only_reached'],len(d['unreached'])) for d in report['units']],nodes=report['natural']['unit_nodes'],fixtures=(report['typed']['fixtures'],report['typed']['ok']),
        claims_differ=[c['id'] for c in report['claims'] if c['verdict']=='differs'],discrepancies=len(report['discrepancies']),size_mb=round(G1.dir_sizes(out_dir)['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True))
    return summary


if __name__=='__main__':main()
