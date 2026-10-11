"""Object callback group G1 (F4 units U01..U07) native observation.

Native Unicorn M68000 observation of the original ROM (never modified; write protected in the model).  Nothing here claims BIOS execution, a natural IRQ or a
natural scheduler: the frame pass of artifacts/animation_machine_scheduler_native is a DECLARED MODEL (re-used in-process from tools/observe_animation_machine_scheduler.py,
which is not edited), and every typed fixture is a DECLARED state (a captured natural state plus a recorded list of register / RAM / SR edits).

The observer is independent of the C++ executors (engine/src/animation_machine_objects_u0*.cpp) and of the core workers' scratch fixture generators; the unit block lists,
code ranges and TRAP boundaries come from the seven pinned contracts docs/analysis/animation-machine-objects-u0{1..7}-contract.md.

PVC banks.  The scheduler Machine is replaced (in-process, by import of tools/observe_animation_machine_pvc_banks.py) by PvcMachine: every bank the MAME formula can produce is a state, a read of
the banked window past the 8 MiB image is the only bank guard (bank-read-outside-rom).  The independent model uses the same formula (address_map.pvc_bank_update) and the same guard.

Natural evidence.  The tool re-runs the 137 natural seeds of the scheduler observation (same SeedRun, same declared pass model, same 120 / 400 frame rule; the callback counts are
compared with the recorded artifact) and treats every node that executed at least one instruction inside a U01..U07 code range as a natural unit node.  Each such node is replayed
natively from its recorded entry state (PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd; write protected ROM; the scheduler's RNG / bank guards) on a FRESH CPU: continuous (one CPU,
no stop) and split (a fresh CPU rebuilt from the captured boundary state at every piece boundary).  A piece is a maximal run of instructions that stay in one unit (or outside all
units: a black box callee).  Entry / exit digests, ordered block-leader traces, computed jump targets, exits and guards are recorded.

Independent model.  A Python M68000 subset interpreter written from the programmer's reference by instruction FORMAT (it shares no code with Unicorn, capstone, the C++ or the
scheduler observer) runs every unit piece from the native piece-start state and is compared with the native piece: per instruction PC + 16 registers, ordered data reads and
writes, ports, final RAM / registers, final CCR at the piece boundary (the boundary is the first instruction of a translation block, where the Unicorn SR read is exact), guards.

Typed fixtures.  Every contract block start (and TRAP boundary) that no natural node reaches gets a declared fixture found by a deterministic coverage guided search over
a captured natural state (register / RAM-byte / SR mutations; recorded as a minimized edit list); the fixtures also cover the contract minimum conditions (TRAP and boundary stops,
computed jumps, carry consumers with declared SR, odd / ROM-write guards, the 2986 failure path).  Fixtures run continuous and split, twice each.
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
import random
import re
import struct
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_scheduler as S
import observe_animation_machine_pvc_banks as PB     # replaces S.Machine by PvcMachine (any PVC-selectable bank); never edited here
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from address_map import pvc_bank_update

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_objects_g1_native'
ROM_PATH=S.ROM_PATH
ROM_SHA=S.ROM_SHA
SCHED_DIR=ROOT/'artifacts/animation_machine_scheduler_native'
SCHED_OBS=SCHED_DIR/'observation.json'
CONTRACT_DIR=ROOT/'docs/analysis'
CONTRACT_SHA={
    1:'5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b',
    2:'b18f52f013f3e4b03eb52b669e567adb01eab5bb0e328810cd3e38cb4945ef94',
    3:'040ed358872ae45fbb5aec13a9e53eade3817c6a5de648b5584ac8095605d21e',
    4:'9c61f228b57bdb3a3b239b3342d437aeaba2d22169caeae3ad9d772d1f405397',
    5:'77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc',
    6:'6d628d0fa1e907e75f06d2906433fb5afbf2d215320be6beee8ebeb6bebd7e63',
    7:'734615e139a6e0577154eace301c66a0ea9fb94137e0e6cf921dd15ff1ab99a9'}
EXPECT_STARTS={1:105,2:133,3:83,4:69,5:71,6:135,7:85}
EXPECT_TRAPS={1:(0xb4db0,0xb4e46),2:(0x39c6,0x3a0c,0x8ec8),3:(),4:(),5:(),6:(),7:()}
# boundary callees named by the contracts (no executor: "unsupported animation machine PC")
BOUNDARY={1:(0xb4e6c,0x482c0,0xdd574),2:(0x36ba,0x3902,0x383e,0x37e2,0x48256,0xe6496),3:(),4:(),5:(0x497a6,0xb975e,0xb97c0),6:(0x3ed2,0xe7562,0xeb9ba,0xeb9e4,0x101c),7:(0x48256,)}
M32=0xffffffff
SPD=S.SPD
PASS_PC=S.PASS_PC
KEYS=S.KEYS
UC_REG=S.UC_REG
sha=S.sha
hx=S.hx
STABLE=S.stable


def sjson(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),default=str)


# ----------------------------------------------------------------------------------
# Contracts: code ranges, block starts, TRAP boundaries (pinned)
# ----------------------------------------------------------------------------------
def contract_path(u):return CONTRACT_DIR/('animation-machine-objects-u%02d-contract.md'%u)


def parse_contract(u,program):
    p=contract_path(u);data=p.read_bytes();assert sha(data)==CONTRACT_SHA[u],('contract changed',u)
    t=data.decode('utf-8')
    sec=t[t.index('## 원본 바이트 근거'):t.index('## block 목록')]
    ranges=[(int(a,16),int(b,16)) for a,b in re.findall(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \|',sec,re.M)]
    if u==3:
        m=re.search(r'코드 1 범위 `([0-9a-f]+)\.\.([0-9a-f]+)`',t);ranges=[(int(m.group(1),16),int(m.group(2),16))]
        assert sha(program[ranges[0][0]:ranges[0][1]])=='0d11139fa93d47dd655b5917de2c9c5e9f35308d67291100e63d7784d9f4ae13'
    # hex byte cells must equal the ROM
    for a,b,cell in re.findall(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| `([0-9a-f]+)` \|',sec,re.M):
        assert program[int(a,16):int(b,16)].hex()==cell,(u,a,b)
    bsec=t[t.index('## block 목록'):];bsec=bsec[:bsec.index('\n## ',5)]
    starts=[]
    for line in bsec.splitlines():
        m=re.match(r'^- ((?:`[0-9a-f]{3,6}`[ ,]*)+):',line)
        if m:starts.extend(int(x,16) for x in re.findall(r'`([0-9a-f]+)`',m.group(1)))
    assert len(starts)==len(set(starts))==EXPECT_STARTS[u],(u,len(starts))
    merged=sorted({int(x,16) for x in re.findall(r'묶음: `([0-9a-f]+)`',bsec)})
    traps=EXPECT_TRAPS[u]
    if traps:
        m=re.search(r'TRAP 경계 \d+개\(([^)]*)\)',t);got=tuple(int(x,16) for x in re.findall(r'`([0-9a-f]+)`',m.group(1)));assert got==traps,(u,got)
        for pc in traps:assert program[pc:pc+2]==b'\x4e\x4f',(u,hex(pc))
    for pc in starts:
        assert any(lo<=pc<hi for lo,hi in ranges),(u,hex(pc))
    return dict(unit=u,sha=CONTRACT_SHA[u],ranges=ranges,starts=sorted(starts),merged=merged,traps=list(traps),bytes=sum(b-a for a,b in ranges))


# ----------------------------------------------------------------------------------
# Independent model: M68000 subset interpreter written by instruction format
# ----------------------------------------------------------------------------------
class MGuard(Exception):
    """A checked machine fault of the model (the native counterpart stops with the same kind)."""
    def __init__(self,kind,**detail):
        Exception.__init__(self,kind);self.kind=kind;self.detail=detail


class MUnsupported(Exception):pass
MASK={1:0xff,2:0xffff,4:M32}
SIGN={1:0x80,2:0x8000,4:0x80000000}
SZB={0:1,1:2,2:4}


def sx(v,size):
    v&=MASK[size];return v-(1<<(8*size)) if v&SIGN[size] else v


class Ins(object):
    __slots__=('op','pc','len','size','src','dst','cond','target','imm','reg','mask','count','bit','auto','aux','text')
    def __init__(self,**kw):
        for k in Ins.__slots__:setattr(self,k,None)
        for k,v in kw.items():setattr(self,k,v)


class Model(object):
    """State: r[0..7]=D0..D7, r[8..15]=A0..A7, pc, ccr (dict X N Z V C; None = unknown), memory view."""
    def __init__(self,program,ram,regs,pc,bank_base,ff8,ff9,ccr=None):
        self.prog=program;self.ram=bytearray(ram);self.r=[regs[k]&M32 for k in KEYS];self.pc=pc;self.bank=bank_base;self.ff8=ff8;self.ff9=ff9
        self.cc=dict(X=None,N=None,Z=None,V=None,C=None)
        if ccr is not None:
            for i,k in enumerate('CVZNX'):self.cc[k]=(ccr>>i)&1
        self.reads=[];self.writes=[];self.ports=[];self.dec={};self.fault_ins=None
    # ---- memory
    def rd(self,a,n):
        a&=M32
        if n>1 and a&1 and a<0x300000:raise MGuard('odd-read',address=a,size=n)
        if 0x200000<=a<0x2fe000 and self.bank+a-0x200000+n>len(self.prog):raise MGuard('bank-read-outside-rom',address=a,size=n,bank=self.bank,physical=self.bank+a-0x200000)
        if a<0x2fe000:
            for i in range(n):self.reads.append(((a+i),))
        if a<0x100000:return int.from_bytes(self.prog[a:a+n],'big')
        if 0x100000<=a<0x200000:return int.from_bytes(bytes(self.ram[(a+i)&0xffff] for i in range(n)),'big')
        if 0x200000<=a<0x2fe000:
            ph=self.bank+a-0x200000
            if ph+n>len(self.prog):raise MGuard('bank-read-outside-rom',address=a,size=n,bank=self.bank,physical=ph)
            return int.from_bytes(self.prog[ph:ph+n],'big')
        raise MGuard('unmapped-read',address=a,size=n)
    def wr(self,a,n,v):
        a&=M32;v&=MASK[n]
        if n>1 and a&1 and a<0x300000:raise MGuard('odd-write',address=a,size=n,value=v)
        if a<0x100000:raise MGuard('rom-write',address=a,size=n)
        if 0x100000<=a<0x200000:
            for i,b in enumerate(v.to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
            for i,b in enumerate(v.to_bytes(n,'big')):self.writes.append((a+i,b))
            return
        if 0x2fe000<=a<0x300000:
            if n!=2 or a not in (0x2ffff0,0x2ffff2):raise MGuard('pvc-page-write',address=a,size=n)
            if a==0x2ffff0:self.ff8=v
            else:self.ff9=v
            self.ports.append((1,a,2,v))
            base,self.ff8,self.ff9=pvc_bank_update(self.ff8,self.ff9);self.bank=base      # MAME get_bank_base: any base is a state (observe_animation_machine_pvc_banks.py model)
            return
        if 0x200000<=a<0x2fe000:
            self.ports.append((2,a,n,v));raise MGuard('rom-write',address=a,size=n)       # the banked window is read only; the native write hook logs the attempt first
        if 0x300000<=a<0x400000 or 0xd00000<=a<0xd01000:
            self.ports.append((2,a,n,v));return
        raise MGuard('unmapped-write',address=a,size=n)
    def ext(self,pos):return int.from_bytes(self.prog[pos:pos+2],'big')
    # ---- effective address decode (static): returns (ea, next position)
    def dec_ea(self,mode,reg,size,pos):
        if mode==0:return ('dn',reg),pos
        if mode==1:return ('an',reg),pos
        if mode==2:return ('ind',reg),pos
        if mode==3:return ('post',reg),pos
        if mode==4:return ('pre',reg),pos
        if mode==5:return ('d16',reg,sx(self.ext(pos),2)),pos+2
        if mode==6:
            w=self.ext(pos);return ('idx',reg,sx(w,1),(w>>12)&7,bool(w&0x8000),bool(w&0x800)),pos+2
        if reg==0:return ('abs',sx(self.ext(pos),2)&M32),pos+2
        if reg==1:return ('abs',(self.ext(pos)<<16)|self.ext(pos+2)),pos+4
        if reg==2:return ('pcd16',(pos+sx(self.ext(pos),2))&M32),pos+2
        if reg==3:
            w=self.ext(pos);return ('pcidx',(pos+sx(w,1))&M32,(w>>12)&7,bool(w&0x8000),bool(w&0x800)),pos+2
        if reg==4:
            if size==4:return ('imm',(self.ext(pos)<<16)|self.ext(pos+2)),pos+4
            if size==2:return ('imm',self.ext(pos)),pos+2
            return ('imm',self.ext(pos)&0xff),pos+2
        raise MUnsupported('ea mode %d reg %d'%(mode,reg))
    def decode(self,pc):
        ins=self.dec.get(pc)
        if ins is not None:return ins
        ins=self.decode1(pc);self.dec[pc]=ins;return ins
    def decode1(self,pc):
        w=self.ext(pc);hi=w>>12;reg=(w>>9)&7;rm=w&7;mode=(w>>3)&7
        if w==0x4e75:return Ins(op='rts',pc=pc,len=2)
        if (w&0xfff0)==0x4e40:return Ins(op='trap',pc=pc,len=2,imm=w&15)
        if hi in (1,2,3):
            size={1:1,3:2,2:4}[hi];src,pos=self.dec_ea(mode,rm,size,pc+2);dst,pos=self.dec_ea((w>>6)&7,reg,size,pos)
            return Ins(op='movea' if ((w>>6)&7)==1 else 'move',pc=pc,len=pos-pc,size=size,src=src,dst=dst)
        if hi==7:
            return Ins(op='moveq',pc=pc,len=2,reg=reg,imm=sx(w&0xff,1))
        if hi==6:
            c=(w>>8)&15;d=w&0xff
            if d==0:disp=sx(self.ext(pc+2),2);ln=4
            elif d==0xff:raise MUnsupported('long branch')
            else:disp=sx(d,1);ln=2
            return Ins(op='bra' if c==0 else 'bsr' if c==1 else 'bcc',pc=pc,len=ln,cond=c,target=(pc+2+disp)&M32)
        if hi==0:
            if w==0x003c or w==0x023c or w==0x0a3c:
                return Ins(op={0x003c:'orccr',0x023c:'andccr',0x0a3c:'eorccr'}[w],pc=pc,len=4,imm=self.ext(pc+2)&0xff)
            if w&0x100:                                              # bit operation, bit number in Dn
                dst,pos=self.dec_ea(mode,rm,1,pc+2)
                return Ins(op='bit',pc=pc,len=pos-pc,aux=(w>>6)&3,reg=reg,dst=dst,bit=None)
            if (w&0xf00)==0x800:
                n=self.ext(pc+2)&0xff;dst,pos=self.dec_ea(mode,rm,1,pc+4)
                return Ins(op='bit',pc=pc,len=pos-pc,aux=(w>>6)&3,reg=None,dst=dst,bit=n)
            kind=(w>>9)&7;sz=(w>>6)&3
            if sz==3:raise MUnsupported('imm op size %04x'%w)
            size=SZB[sz];imm,pos=self.dec_ea(7,4,size,pc+2);dst,pos=self.dec_ea(mode,rm,size,pos)
            name={0:'ori',1:'andi',2:'subi',3:'addi',5:'eori',6:'cmpi'}.get(kind)
            if name is None:raise MUnsupported('imm op %04x'%w)
            return Ins(op=name,pc=pc,len=pos-pc,size=size,imm=imm[1],dst=dst)
        if hi==4:
            if (w&0xf1c0)==0x41c0:
                ea,pos=self.dec_ea(mode,rm,4,pc+2);return Ins(op='lea',pc=pc,len=pos-pc,reg=reg,src=ea)
            if (w&0xffc0)==0x4e80:
                ea,pos=self.dec_ea(mode,rm,4,pc+2);return Ins(op='jsr',pc=pc,len=pos-pc,src=ea)
            if (w&0xffc0)==0x4ec0:
                ea,pos=self.dec_ea(mode,rm,4,pc+2);return Ins(op='jmp',pc=pc,len=pos-pc,src=ea)
            if (w&0xfff8)==0x4840:return Ins(op='swap',pc=pc,len=2,reg=rm)
            if (w&0xfff8)==0x4880:return Ins(op='ext',pc=pc,len=2,reg=rm,size=2)
            if (w&0xfff8)==0x48c0:return Ins(op='ext',pc=pc,len=2,reg=rm,size=4)
            if (w&0xfb80)==0x4880:
                size=4 if w&0x40 else 2;mask=self.ext(pc+2);ea,pos=self.dec_ea(mode,rm,size,pc+4)
                return Ins(op='movem',pc=pc,len=pos-pc,size=size,mask=mask,aux=(w>>10)&1,dst=ea)
            sz=(w>>6)&3
            if sz!=3 and (w&0xff00) in (0x4200,0x4400,0x4600,0x4a00):
                size=SZB[sz];ea,pos=self.dec_ea(mode,rm,size,pc+2)
                return Ins(op={0x4200:'clr',0x4400:'neg',0x4600:'not',0x4a00:'tst'}[w&0xff00],pc=pc,len=pos-pc,size=size,dst=ea)
            raise MUnsupported('opcode %04x'%w)
        if hi==5:
            if ((w>>6)&3)==3:
                c=(w>>8)&15
                if mode==1:
                    disp=sx(self.ext(pc+2),2);return Ins(op='dbcc',pc=pc,len=4,cond=c,reg=rm,target=(pc+2+disp)&M32)
                ea,pos=self.dec_ea(mode,rm,1,pc+2);return Ins(op='scc',pc=pc,len=pos-pc,cond=c,dst=ea)
            size=SZB[(w>>6)&3];ea,pos=self.dec_ea(mode,rm,size,pc+2)
            return Ins(op='subq' if w&0x100 else 'addq',pc=pc,len=pos-pc,size=size,imm=reg or 8,dst=ea)
        if hi in (8,9,0xb,0xc,0xd):
            om=(w>>6)&7
            if hi==0xc and (w&0x1f8) in (0x140,0x148,0x188):
                return Ins(op='exg',pc=pc,len=2,reg=reg,aux={0x140:0,0x148:1,0x188:2}[w&0x1f8],count=rm)
            if hi==0xc and om in (3,7):
                ea,pos=self.dec_ea(mode,rm,2,pc+2);return Ins(op='mulu' if om==3 else 'muls',pc=pc,len=pos-pc,reg=reg,src=ea)
            if hi in (9,0xd) and om in (3,7):
                size=2 if om==3 else 4;ea,pos=self.dec_ea(mode,rm,size,pc+2)
                return Ins(op='suba' if hi==9 else 'adda',pc=pc,len=pos-pc,size=size,reg=reg,src=ea)
            if hi==0xb and om in (3,7):
                size=2 if om==3 else 4;ea,pos=self.dec_ea(mode,rm,size,pc+2)
                return Ins(op='cmpa',pc=pc,len=pos-pc,size=size,reg=reg,src=ea)
            if hi==0xb and om>=4:
                size=SZB[om-4];ea,pos=self.dec_ea(mode,rm,size,pc+2);return Ins(op='eor',pc=pc,len=pos-pc,size=size,reg=reg,dst=ea)
            if om>=4 and hi in (9,0xd) and mode in (0,1):raise MUnsupported('extended arithmetic %04x'%w)
            size=SZB[om&3] if (om&3)<3 else None
            if size is None:raise MUnsupported('opcode %04x'%w)
            ea,pos=self.dec_ea(mode,rm,size,pc+2)
            name={8:'or',9:'sub',0xb:'cmp',0xc:'and',0xd:'add'}[hi]
            if om<4:return Ins(op=name,pc=pc,len=pos-pc,size=size,reg=reg,src=ea,aux=0)
            return Ins(op=name,pc=pc,len=pos-pc,size=size,reg=reg,dst=ea,aux=1)
        if hi==0xe:
            if (w&0xc0)==0xc0:raise MUnsupported('memory shift %04x'%w)
            typ=(w>>3)&3
            if typ not in (0,1):raise MUnsupported('shift type %04x'%w)
            size=SZB[(w>>6)&3]
            return Ins(op='shift',pc=pc,len=2,size=size,reg=rm,aux=typ,bit=bool(w&0x20),imm=bool(w&0x100),count=reg)
        raise MUnsupported('opcode %04x at %x'%(w,pc))
    # ---- operand resolution (dynamic)
    def reg_inc(self,reg,size):return 2 if (reg==7 and size==1) else size
    def resolve(self,ea,size):
        k=ea[0];r=self.r
        if k=='dn':return ('r',ea[1])
        if k=='an':return ('r',8+ea[1])
        if k=='imm':return ('i',ea[1])
        if k=='ind':return ('m',r[8+ea[1]])
        if k=='post':
            a=r[8+ea[1]];r[8+ea[1]]=(a+self.reg_inc(ea[1],size))&M32;return ('m',a)
        if k=='pre':
            a=(r[8+ea[1]]-self.reg_inc(ea[1],size))&M32;r[8+ea[1]]=a;return ('m',a)
        if k=='d16':return ('m',(r[8+ea[1]]+ea[2])&M32)
        if k=='idx':
            xv=r[(8 if ea[4] else 0)+ea[3]];xv=sx(xv,4) if ea[5] else sx(xv,2)
            return ('m',(r[8+ea[1]]+ea[2]+xv)&M32)
        if k=='abs':return ('m',ea[1])
        if k=='pcd16':return ('m',ea[1])
        if k=='pcidx':
            xv=r[(8 if ea[3] else 0)+ea[2]];xv=sx(xv,4) if ea[4] else sx(xv,2)
            return ('m',(ea[1]+xv)&M32)
        raise MUnsupported('ea '+k)
    def get(self,loc,size):
        if loc[0]=='r':return self.r[loc[1]]&MASK[size]
        if loc[0]=='i':return loc[1]&MASK[size]
        return self.rd(loc[1],size)
    def put(self,loc,size,v):
        v&=MASK[size]
        if loc[0]=='r':
            i=loc[1]
            if i>=8:self.r[i]=v if size==4 else sx(v,size)&M32;return
            self.r[i]=(self.r[i]&~MASK[size]&M32)|v;return
        if loc[0]=='i':raise MUnsupported('write to immediate')
        self.wr(loc[1],size,v)
    # ---- flags
    def set_nz(self,v,size):
        v&=MASK[size];self.cc['N']=int(bool(v&SIGN[size]));self.cc['Z']=int(v==0);self.cc['V']=0;self.cc['C']=0
    def f_sub(self,d,s,size,x):
        mk=MASK[size];d&=mk;s&=mk;res=(d-s)&mk;c=int(d<s)
        self.cc['N']=int(bool(res&SIGN[size]));self.cc['Z']=int(res==0);self.cc['V']=int(bool((d^s)&(d^res)&SIGN[size]));self.cc['C']=c
        if x:self.cc['X']=c
        return res
    def f_add(self,d,s,size):
        mk=MASK[size];d&=mk;s&=mk;res=(d+s)&mk;c=int(d+s>mk)
        self.cc['N']=int(bool(res&SIGN[size]));self.cc['Z']=int(res==0);self.cc['V']=int(bool((~(d^s))&(d^res)&SIGN[size]));self.cc['C']=c;self.cc['X']=c
        return res
    def flag(self,n):
        v=self.cc[n]
        if v is None:raise MUnknownFlag(n)
        return v
    def test(self,c):
        f=self.flag
        if c==0:return True
        if c==1:return False
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
        return bool(f('Z') or f('N')!=f('V'))
    def ccr_value(self):
        v=0
        for i,k in enumerate('CVZNX'):
            if self.cc[k] is None:return None
            v|=self.cc[k]<<i
        return v
    def push32(self,v):
        self.r[15]=(self.r[15]-4)&M32;self.wr(self.r[15],4,v)
    # ---- one instruction; returns the instruction.  A guard restores the registers and the pc to the state before the instruction
    def step(self):
        pc=self.pc;ins=self.decode(pc);op=ins.op;nxt=(pc+ins.len)&M32;r=self.r;before=(list(r),dict(self.cc),len(self.ports),self.bank,self.ff8,self.ff9)
        self.fault_ins=ins
        try:nxt=self.exec_op(ins,op,nxt)
        except (MGuard,MUnknownFlag,MUnsupported):
            self.r[:]=before[0];self.cc=before[1];raise
        self.pc=nxt;return ins
    def exec_op(self,ins,op,nxt):
        r=self.r;size=ins.size
        if op=='move':
            v=self.get(self.resolve(ins.src,size),size);d=self.resolve(ins.dst,size);self.put(d,size,v);self.set_nz(v,size)
        elif op=='movea':
            v=self.get(self.resolve(ins.src,size),size);r[8+ins.dst[1]]=sx(v,size)&M32
        elif op=='moveq':
            r[ins.reg]=ins.imm&M32;self.set_nz(ins.imm,4)
        elif op=='lea':
            r[8+ins.reg]=self.resolve(ins.src,4)[1]
        elif op=='swap':
            v=r[ins.reg];r[ins.reg]=((v>>16)|(v<<16))&M32;self.set_nz(r[ins.reg],4)
        elif op=='ext':
            v=r[ins.reg]
            if size==2:r[ins.reg]=(v&0xffff0000)|(sx(v,1)&0xffff);self.set_nz(r[ins.reg],2)
            else:r[ins.reg]=sx(v,2)&M32;self.set_nz(r[ins.reg],4)
        elif op=='clr':
            d=self.resolve(ins.dst,size);self.put(d,size,0);self.cc.update(N=0,Z=1,V=0,C=0)
        elif op=='tst':
            v=self.get(self.resolve(ins.dst,size),size);self.set_nz(v,size)
        elif op=='neg':
            d=self.resolve(ins.dst,size);v=self.get(d,size);self.put(d,size,self.f_sub(0,v,size,True))
        elif op=='not':
            d=self.resolve(ins.dst,size);v=self.get(d,size);self.put(d,size,~v);self.set_nz(~v,size)
        elif op in ('addq','subq'):
            d=self.resolve(ins.dst,size)
            if d[0]=='r' and d[1]>=8:r[d[1]]=(r[d[1]]+(ins.imm if op=='addq' else -ins.imm))&M32
            else:
                v=self.get(d,size);self.put(d,size,self.f_add(v,ins.imm,size) if op=='addq' else self.f_sub(v,ins.imm,size,True))
        elif op in ('addi','subi','cmpi','andi','ori','eori'):
            d=self.resolve(ins.dst,size);v=self.get(d,size);imm=ins.imm&MASK[size]
            if op=='addi':self.put(d,size,self.f_add(v,imm,size))
            elif op=='subi':self.put(d,size,self.f_sub(v,imm,size,True))
            elif op=='cmpi':self.f_sub(v,imm,size,False)
            else:
                res=(v&imm) if op=='andi' else (v|imm) if op=='ori' else (v^imm);self.put(d,size,res);self.set_nz(res,size)
        elif op in ('andccr','orccr','eorccr'):
            for i,k in enumerate('CVZNX'):
                b=(ins.imm>>i)&1
                if op=='andccr':
                    if b==0:self.cc[k]=0
                elif op=='orccr':
                    if b==1:self.cc[k]=1
                else:
                    if b==1:self.cc[k]=None if self.cc[k] is None else self.cc[k]^1
        elif op in ('add','sub','cmp','and','or'):
            if ins.aux==0:
                v=self.get(self.resolve(ins.src,size),size);dn=ins.reg;cur=r[dn]&MASK[size]
                if op=='add':res=self.f_add(cur,v,size)
                elif op=='sub':res=self.f_sub(cur,v,size,True)
                elif op=='cmp':self.f_sub(cur,v,size,False);res=None
                elif op=='and':res=cur&v;self.set_nz(res,size)
                else:res=cur|v;self.set_nz(res,size)
                if res is not None:self.put(('r',dn),size,res)
            else:
                d=self.resolve(ins.dst,size);cur=self.get(d,size);v=r[ins.reg]&MASK[size]
                if op=='add':res=self.f_add(cur,v,size)
                elif op=='sub':res=self.f_sub(cur,v,size,True)
                elif op=='and':res=cur&v;self.set_nz(res,size)
                elif op=='or':res=cur|v;self.set_nz(res,size)
                else:raise MUnsupported('cmp to memory')
                self.put(d,size,res)
        elif op=='eor':
            d=self.resolve(ins.dst,size);cur=self.get(d,size);res=cur^(r[ins.reg]&MASK[size]);self.put(d,size,res);self.set_nz(res,size)
        elif op in ('adda','suba'):
            v=sx(self.get(self.resolve(ins.src,size),size),size);a=8+ins.reg;r[a]=(r[a]+(v if op=='adda' else -v))&M32
        elif op=='cmpa':
            v=sx(self.get(self.resolve(ins.src,size),size),size)&M32;self.f_sub(r[8+ins.reg],v,4,False)
        elif op in ('mulu','muls'):
            v=self.get(self.resolve(ins.src,2),2);cur=r[ins.reg]&0xffff
            res=(v*cur) if op=='mulu' else (sx(v,2)*sx(cur,2))
            r[ins.reg]=res&M32;self.set_nz(res,4)
        elif op=='exg':
            a=ins.reg;b=ins.count
            if ins.aux==0:r[a],r[b]=r[b],r[a]
            elif ins.aux==1:r[8+a],r[8+b]=r[8+b],r[8+a]
            else:r[a],r[8+b]=r[8+b],r[a]
        elif op=='bit':
            n=(r[ins.reg] if ins.reg is not None else ins.bit)
            d=self.resolve(ins.dst,1 if ins.dst[0]!='dn' else 4)
            if d[0]=='r':bits=32;sz=4
            else:bits=8;sz=1
            n%=bits;v=self.get(d,sz);self.cc['Z']=int(((v>>n)&1)==0)
            if ins.aux==1:self.put(d,sz,v^(1<<n))
            elif ins.aux==2:self.put(d,sz,v&~(1<<n))
            elif ins.aux==3:self.put(d,sz,v|(1<<n))
        elif op=='shift':
            cnt=(r[ins.count]&63) if ins.bit else (ins.count or 8);mk=MASK[size];v=r[ins.reg]&mk;sg=SIGN[size];nb=8*size;left=ins.imm;carry=None;ovf=0;res=v
            for _ in range(cnt):
                if left:
                    carry=(res>>(nb-1))&1;new=(res<<1)&mk
                    if ins.aux==0 and ((res^new)&sg):ovf=1
                    res=new
                else:
                    carry=res&1
                    if ins.aux==0:res=(res>>1)|(res&sg)
                    else:res=res>>1
            self.put(('r',ins.reg),size,res)
            self.cc['N']=int(bool(res&sg));self.cc['Z']=int(res==0);self.cc['V']=ovf if (ins.aux==0 and left) else 0
            if cnt==0:self.cc['C']=0
            else:self.cc['C']=carry;self.cc['X']=carry
        elif op=='scc':
            d=self.resolve(ins.dst,1);self.put(d,1,0xff if self.test(ins.cond) else 0)
        elif op=='dbcc':
            if not self.test(ins.cond):
                v=((r[ins.reg]&0xffff)-1)&0xffff;r[ins.reg]=(r[ins.reg]&0xffff0000)|v
                if v!=0xffff:nxt=ins.target
        elif op=='bcc':
            if self.test(ins.cond):nxt=ins.target
        elif op=='bra':nxt=ins.target
        elif op=='bsr':self.push32(nxt);nxt=ins.target
        elif op=='jsr':
            t=self.resolve(ins.src,4)[1];self.push32(nxt);nxt=t
        elif op=='jmp':nxt=self.resolve(ins.src,4)[1]
        elif op=='rts':
            v=self.rd(r[15],4);r[15]=(r[15]+4)&M32;nxt=v
        elif op=='movem':
            regs=list(range(16));ea=ins.dst;sz=ins.size
            if ins.aux==0:                                           # register -> memory
                if ea[0]=='pre':
                    a=r[8+ea[1]];lst=[15-i for i in range(16) if ins.mask>>i&1]
                    vals=[r[x] for x in lst]
                    for x,v in zip(lst,vals):
                        a=(a-sz)&M32;self.wr(a,sz,v&MASK[sz])
                    r[8+ea[1]]=a
                else:
                    a=self.resolve(ea,sz)[1]
                    for i in range(16):
                        if ins.mask>>i&1:self.wr(a,sz,r[i]&MASK[sz]);a=(a+sz)&M32
            else:                                                    # memory -> register
                if ea[0]=='post':a=r[8+ea[1]]
                else:a=self.resolve(ea,sz)[1]
                vals=[]
                for i in range(16):
                    if ins.mask>>i&1:
                        v=self.rd(a,sz);a=(a+sz)&M32;vals.append((i,v))
                for i,v in vals:r[i]=(sx(v,sz) if sz==2 else v)&M32
                if ea[0]=='post':r[8+ea[1]]=a
        elif op=='trap':raise MGuard('trap',vector=ins.imm)
        else:raise MUnsupported(op)
        return nxt


class MUnknownFlag(Exception):pass


# ----------------------------------------------------------------------------------
# Environment: unit maps from the pinned contracts
# ----------------------------------------------------------------------------------
PROBE=0x500000                                   # declared probe window (MOVE SR,D0): the exact CCR read (a plain SR read of Unicorn is stale for V / C)
REGS16=tuple(UC_REG[k] for k in KEYS)
SR_REG=UC_REG['sr'];PC_REG=UC_REG['pc'];D0_REG=UC_REG['d0']


class Env(object):
    def __init__(self):
        self.program=S.load_rom();self.fixed=(ctypes.c_ubyte*0x100000).from_buffer_copy(self.program[:0x100000])
        self.contracts={u:parse_contract(u,self.program) for u in range(1,8)}
        self.unit=bytearray(0x80000);self.starts={};self.traps={};self.range_of={}
        for u,c in self.contracts.items():
            for lo,hi in c['ranges']:
                for pc in range(lo,hi,2):
                    assert self.unit[pc>>1]==0,hex(pc)
                    self.unit[pc>>1]=u
            for pc in c['starts']:self.starts[pc]=u
            for pc in c['traps']:self.traps[pc]=u
        self.boundary={pc:u for u,v in BOUNDARY.items() for pc in v}
        self.range_list=sorted((lo,hi,u) for u,c in self.contracts.items() for lo,hi in c['ranges'])
    def unit_of(self,pc):
        if pc&1 or pc>=0x100000:return 0
        return self.unit[pc>>1]


def g1_digest(st):
    h=hashlib.sha256();h.update(b'MS5-G1-STATE-1');h.update(st['ram']);h.update(struct.pack('>16I',*[st['regs'][k] for k in KEYS]))
    b=st['bank'];h.update(struct.pack('>IIIHHB',st['pc'],b[0],0,b[1]&0xffff,b[2]&0xffff,0xff if st.get('ccr') is None else st['ccr']));return h.hexdigest()


def ports_sha(ports):return S.ports_digest(ports)


def make_machine(env,st):
    snap=dict(ram=st['ram'],regs=st['regs'],pc=st['pc'],bank=st['bank'])
    m=S.Machine(env.program,env.fixed,snap);m.install_basic_hooks()
    c=m.cpu;c.mem_map(PROBE,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(PROBE,bytes.fromhex('40c04e71'))
    a7=c.reg_read(UC_REG['a7'])
    c.reg_write(SR_REG,0x2000|((st.get('ccr') or 0)&0x1f));assert c.reg_read(UC_REG['a7'])==a7
    return m


WAIT_PCS=frozenset((0x3aea,0xcda4,0x47af0,0x478de))


def wait_check(uc,m,pc):
    """Declared waits of the frame-pass model (same predicates as the scheduler observer): sound ring 3aea, sprite queue cda4, palette gate (not supported here: a gate is a guard)."""
    a5=uc.reg_read(UC_REG['a5'])
    if pc==0x3aea:
        live=m.word((a5-0x328c)&M32);want=uc.reg_read(UC_REG['d1'])&0xffff
        return dict(pc=pc,kind='sound',live=live,compared=want) if live==want else None
    if pc==0xcda4:
        live=m.word((a5+0xd34)&M32);want=uc.reg_read(UC_REG['d4'])&0xffff
        return dict(pc=pc,kind='sprite',live=live,compared=want) if live!=want else None
    return None


def release_wait(m,w):
    if w['pc']==0x3aea:ch=[(0x104d74,2,0xffff)]
    else:ch=[(0x108d34,2,w['compared'])]
    for a,s,v in ch:m.put(a,s,v)
    return [list(x) for x in ch]


def probe_ccr(m):
    c=m.cpu;d0=c.reg_read(D0_REG);pc=c.reg_read(PC_REG)
    try:
        c.reg_write(PC_REG,PROBE);c.emu_start(PROBE,PROBE+2,count=4);v=c.reg_read(D0_REG)&0x1f
    except unicorn.UcError:v=None
    c.reg_write(D0_REG,d0);c.reg_write(PC_REG,pc);return v


def capture(m,probe=True):
    return dict(ram=m.ram(),regs=m.regs(),pc=m.pc(),bank=(m.bank,m.ff8,m.ff9),ccr=probe_ccr(m) if probe else None)


def guard_of(m):
    """The native guard (explicit reason) after a run ended without a requested pause, or None."""
    if m.odd:return ('odd-'+m.odd['access'],dict(m.odd))
    if m.invalid:
        k=m.invalid.get('kind') or m.invalid.get('access')
        return (k if k!='write-protected' else 'rom-write',dict(m.invalid))
    if m.fetch_unmapped is not None:return ('fetch-unmapped',dict(address=m.fetch_unmapped,odd=bool(m.fetch_unmapped&1)))
    if m.intr:return ('odd-pc' if m.intr['pc']&1 else 'cpu-exception',dict(m.intr))
    return None


class Flow(object):
    """One native execution from `start` until a stop PC / guard / step limit.  mode 'ref': no pause at all (only the final state); 'cont': one persistent CPU that is paused (emu_stop) at every
    piece boundary to capture the exact state and resumed; 'split': a FRESH CPU rebuilt from the captured boundary state for every piece.  A piece is a maximal run of instructions in one
    unit (or outside all units).  Stops directly BEFORE the instruction at the new PC (after the transferring instruction)."""
    def __init__(self,env,start,mode,stops=(),limit=3_000_000,detail=True,regtrace=True):
        self.regtrace=regtrace;self.env=env;self.mode=mode;self.stops=frozenset(stops);self.limit=limit;self.detail=detail and mode!='ref'
        self.start=start;self.states=[];self.pieces=[];self.final=None;self.n=0;self.waits=[];self.mach=None
    def hooks(self,m):
        c=m.cpu;me=self;self.mach=m
        c.hook_add(UC_HOOK_CODE,self.on_code,begin=0,end=0xfffff)
        if self.detail:
            def rd(uc,access,address,size,value,user):
                if me.cur and address<0x2fe000 and not (0x200000>address>=0x100000 and False):me.piece['reads'].extend(range(address,address+size))
            def wr(uc,access,address,size,value,user):
                if me.cur and 0x100000<=address<0x200000:
                    for i,b in enumerate((value&((1<<(8*size))-1)).to_bytes(size,'big')):me.piece['writes'].append((address+i,b))
            c.hook_add(UC_HOOK_MEM_READ,rd,begin=0,end=0x2fdfff)
            c.hook_add(UC_HOOK_MEM_WRITE,wr,begin=0x100000,end=0x1fffff)
    def on_code(self,uc,pc,size,user):
        self.n+=1
        if self.n>self.limit:self.pause=('step-limit',0);uc.emu_stop();return
        if pc in self.stops:self.pause=('stop',pc);uc.emu_stop();return
        if pc in WAIT_PCS:
            w=wait_check(uc,self.mach,pc)
            if w is not None:self.n-=1;self.pause=('wait',w);uc.emu_stop();return
        if self.mode=='ref':return
        u=0 if pc&1 else self.env.unit[pc>>1]
        if u!=self.cur:self.n-=1;self.pause=('boundary',u);uc.emu_stop();return
        if u and self.detail:
            self.piece['trace'].append((pc,tuple(uc.reg_read(r) for r in REGS16) if self.regtrace else None))
            if pc in self.env.starts:self.piece['leaders'].append(pc)
    def new_piece(self,unit,idx):
        self.cur=unit;self.piece=dict(unit=unit,start=idx,end=None,trace=[],leaders=[],reads=[],writes=[],ports=None)
    def close_piece(self,m,idx):
        p=self.piece;p['end']=idx;p['ports']=[tuple(x) for x in m.ports[self.pmark:]];self.pieces.append(p)
    def run(self):
        env=self.env;st=self.start;self.states.append(st);m=make_machine(env,st);self.hooks(m);self.pmark=0
        self.new_piece(env.unit_of(st['pc']),0);pc=st['pc'];err=None;self.pause=None
        while True:
            self.pause=None;m.fetch_unmapped=None;m.odd=None;m.invalid=None;m.intr=None;err=None
            try:m.cpu.emu_start(pc,0xffffff,count=self.limit+16)
            except unicorn.UcError as e:err=str(e)
            if self.pause is not None and self.pause[0]=='wait':
                w=self.pause[1];changes=release_wait(m,w);self.waits.append(dict(w,released=changes));self.pause=None;pc=m.pc()
                if len(self.waits)>S.WAIT_LIMIT or not changes:self.pause=('wait-not-released',w);break
                continue
            if self.pause is not None and self.pause[0]=='boundary':
                stt=capture(m);self.close_piece(m,len(self.states));self.states.append(stt)
                u=self.pause[1];pc=stt['pc']
                if self.mode=='split':
                    m=make_machine(env,stt);self.hooks(m);self.pmark=0
                else:self.pmark=len(m.ports)
                self.new_piece(u,len(self.states)-1);continue
            break
        pa=self.pause
        if pa is not None:kind=pa[0];detail=dict(pc=pa[1]) if pa[0]=='stop' else (dict(wait=pa[1]) if pa[0]=='wait-not-released' else {})
        else:
            g=guard_of(m)
            if g:kind,detail='guard',dict(kind=g[0],detail=g[1])
            elif err:kind,detail='guard',dict(kind='unicorn-error',detail=dict(error=err))
            else:kind,detail='step-limit',{}
        fin=capture(m)
        if fin['ccr'] is None and kind!='guard':raise RuntimeError('ccr probe failed')
        self.close_piece(m,len(self.states));self.states.append(fin)
        self.final=dict(kind=kind,detail=detail,idx=len(self.states)-1)
        if self.mode=='ref':self.ports_all=[tuple(x) for x in m.ports]
        else:self.ports_all=[tuple(x) for p in self.pieces for x in p['ports']]
        self.digests=[g1_digest(s) for s in self.states]
        return self
    def signature(self):
        """Comparable result of a flow: boundary digests (ref: start + final only), final kind, ordered ports, step count is not part of it."""
        d=self.digests if self.mode!='ref' else [self.digests[0],self.digests[-1]]
        return dict(digests=d,final=dict(kind=self.final['kind'],detail=json.loads(sjson(self.final['detail']))),ports=ports_sha(self.ports_all),waits=json.loads(sjson(self.waits)))


# ----------------------------------------------------------------------------------
# Model vs native piece comparison
# ----------------------------------------------------------------------------------
NATIVE_GUARD_TO_MODEL={'odd-read':'odd-read','odd-write':'odd-write','rom-write':'rom-write','bank-read-outside-rom':'bank-read-outside-rom','read-unmapped':'unmapped-read','write-unmapped':'unmapped-write',
    'pvc-page':'pvc-page-write','odd-pc':'odd-pc'}


def auto_regs(ins):
    s=set()
    for ea in (ins.src,ins.dst):
        if ea and ea[0] in ('post','pre'):s.add(8+ea[1])
    if ins.op in ('rts','jsr','bsr','movem'):s.add(15)
    if ins.op=='movem' and ins.dst and ins.dst[0] in ('post','pre'):s.add(8+ins.dst[1])
    return s


def model_piece(env,flow,piece):
    """Run the model over one unit piece from the native start state and compare.  Returns (ok, diffs, info)."""
    st0=flow.states[piece['start']];st1=flow.states[piece['end']];u=piece['unit']
    b=st0['bank']
    mdl=Model(env.program,st0['ram'],st0['regs'],st0['pc'],b[0],b[1],b[2],ccr=st0['ccr'])
    trace=[];guard=None
    last_is_final=piece['end']==flow.final['idx']
    limit=len(piece['trace'])+(0 if (last_is_final and flow.final['kind']=='step-limit') else 4)
    while True:
        pc=mdl.pc
        if env.unit_of(pc)!=u:break
        if len(trace)>=limit:
            if last_is_final and flow.final['kind']=='step-limit':break
            guard=('model-overrun',{});break
        trace.append((pc,tuple(mdl.r)))
        try:mdl.step()
        except MGuard as e:guard=(e.kind,e.detail);break
        except MUnknownFlag as e:guard=('unknown-flag',dict(flag=str(e)));break
        except MUnsupported as e:guard=('unsupported',dict(why=str(e)));break
    diffs=[]
    ntrace=piece['trace']
    if ntrace and ntrace[0][1] is None:
        if [x[0] for x in trace]!=[x[0] for x in ntrace]:diffs.append('trace-pcs(native %d, model %d)'%(len(ntrace),len(trace)))
    elif trace!=ntrace:
        diffs.append('trace(native %d, model %d)'%(len(ntrace),len(trace)))
    nat_guard=None
    if last_is_final and flow.final['kind']=='guard' and flow.final['detail']['kind'] not in ('fetch-unmapped','fetch-protected','odd-pc','unicorn-error','cpu-exception'):
        nat_guard=NATIVE_GUARD_TO_MODEL.get(flow.final['detail']['kind'],flow.final['detail']['kind'])
    if guard is None and nat_guard:diffs.append('native guard %s, model none'%nat_guard)
    elif guard is not None and nat_guard is None:diffs.append('model guard %s, native none'%guard[0])
    elif guard is not None and guard[0]!=nat_guard:diffs.append('guard kind native %s model %s'%(nat_guard,guard[0]))
    gk=guard[0] if guard else None
    # memory effects
    if gk=='odd-write':
        d=guard[1];v=d['value'].to_bytes(d['size'],'big')
        for i,x in enumerate(v):mdl.ram[(d['address']+i)&0xffff]=x       # the native hook lets the odd store complete
    exempt=set()
    if guard is not None and mdl.pc is not None:
        fi=mdl.dec.get(mdl.pc) or mdl.decode(mdl.pc) if not (mdl.pc&1) else None
        if fi is not None and gk not in ('odd-pc',):exempt=auto_regs(fi)
    nreads=[a for a in piece['reads']];mreads=[a[0] for a in mdl.reads]
    if nreads!=mreads:diffs.append('reads(native %d, model %d)'%(len(nreads),len(mreads)))
    if piece['writes']!=mdl.writes:diffs.append('writes(native %d, model %d)'%(len(piece['writes']),len(mdl.writes)))
    mports=[tuple(x) for x in mdl.ports]
    if [tuple(x) for x in piece['ports']]!=mports:diffs.append('ports')
    if bytes(mdl.ram)!=st1['ram']:diffs.append('ram')
    regs_n=[st1['regs'][k] for k in KEYS]
    bad=[i for i in range(16) if mdl.r[i]!=regs_n[i] and i not in exempt]
    if bad:diffs.append('regs'+str(bad))
    if guard is None or gk in ('odd-pc',):
        if mdl.pc!=st1['pc']:diffs.append('pc')
        if gk is None or gk=='odd-pc':
            mc=mdl.ccr_value()
            if st1['ccr'] is not None:
                for i,k in enumerate('CVZNX'):
                    if mdl.cc[k] is not None and mdl.cc[k]!=(st1['ccr']>>i)&1:diffs.append('ccr.'+k)
    else:
        if mdl.pc!=st1['pc']:diffs.append('guard pc native %x model %x'%(st1['pc'],mdl.pc))
    if (mdl.bank,mdl.ff8,mdl.ff9)!=tuple(st1['bank']):diffs.append('bank')
    return not diffs,diffs,dict(insns=len(trace),guard=guard[0] if guard else None,leaders=[pc for pc,_ in trace if pc in env.starts])


# ----------------------------------------------------------------------------------
# Natural stage: the scheduler observer's seeds, every node that executed unit code
# ----------------------------------------------------------------------------------
GLOBAL={}
NAT_LIMIT=1_500_000
FRAMES=S.FRAMES_BASE


class G1Run(S.SeedRun):
    """The scheduler SeedRun (same declared frame pass) plus a passive code hook on the unit ranges; every node that executed unit code is handed to `node_task`."""
    def __init__(self,*a,**k):
        S.SeedRun.__init__(self,*a,**k);self.node_task=None;self.unit_nodes=0;self.node_rows=[];self.ipcs=set()
    def build(self,snap):
        mach=S.SeedRun.build(self,snap);env=GLOBAL['env']
        for lo,hi,u in env.range_list:mach.cpu.hook_add(UC_HOOK_CODE,self.h_unit,begin=lo,end=hi-1)
        return mach
    def h_unit(self,uc,pc,size,user):
        n=self.cur
        if n is None:return
        h=n.get('hits')
        if h is None:h=n['hits']={}
        if pc in GLOBAL['env'].starts:h[pc]=h.get(pc,0)+1
        elif 'unit' not in n:n['unit']=True
        n['unit']=True
    def finish_node(self,node,exit_state,partial):
        S.SeedRun.finish_node(self,node,exit_state,partial)
        if node.get('unit'):
            self.unit_nodes+=1
            self.node_rows.append(self.node_task(self,node,exit_state,partial))


def pass_a_task(case):
    """Cheap pass: which nodes execute which unit block starts (no replay)."""
    env=GLOBAL['env'];sd=S.SEEDS[case];snap,meta=S.seed_snap(sd)
    run=G1Run(GLOBAL['program'],S.G['fixed'],S.G['levels'],snap,'continuous',FRAMES,heavy=False,sink=None)
    run.node_task=lambda r,node,ex,partial:(r.frame,node['seq'],node['cb'],sorted(node.get('hits',{})),bool(partial))
    run.run()
    return dict(case=case,kind=sd['kind'],stop=run.stop,frames_done=run.frames_done,cb=dict((k,v) for k,v in run.cb_counts.items()),unit_nodes=run.unit_nodes,nodes=run.node_rows,covered=run.fully_covered)


def write_blob(data):
    d=sha(data);S.write_blob(GLOBAL['out'],d,data);return d


def dump_state(st):
    return dict(ram=write_blob(st['ram']),regs=st['regs'],pc=st['pc'],bank=list(st['bank']),ccr=st['ccr'],state=g1_digest(st))


def load_state(row):
    ram=(GLOBAL['out']/'blobs'/(row['ram']+'.bin')).read_bytes()
    return dict(ram=ram,regs=dict(row['regs']),pc=row['pc'],bank=tuple(row['bank']),ccr=row['ccr'])


def flows_equal(a,b):
    return a.signature()==b.signature()


def run_modes(env,st,stops,limit,twice,regtrace=True,split=True):
    ref=Flow(env,st,'ref',stops,limit).run();cont=Flow(env,st,'cont',stops,limit,regtrace=regtrace).run()
    out=dict(ref=ref,cont=cont)
    if split:out['split']=Flow(env,st,'split',stops,limit,regtrace=regtrace).run()
    if twice:
        out['cont2']=Flow(env,st,'cont',stops,limit,regtrace=regtrace).run()
        if split:out['split2']=Flow(env,st,'split',stops,limit,regtrace=regtrace).run()
    return out


def compare_modes(f):
    """Equality flags of the flows of one start state."""
    c=f['cont'];r=f['ref']
    eq=dict(ref_cont=r.digests[0]==c.digests[0] and r.digests[-1]==c.digests[-1] and (r.final['kind'],r.final['detail'])==(c.final['kind'],c.final['detail']) and ports_sha(r.ports_all)==ports_sha(c.ports_all) and r.waits==c.waits,
        )
    if 'split' in f:eq['cont_split']=flows_equal(c,f['split'])
    if 'cont2' in f:eq['cont_twice']=flows_equal(c,f['cont2'])
    if 'split2' in f:eq['split_twice']=flows_equal(f['split'],f['split2'])
    return eq


def pvc_banks_of(flow):
    """Bank bases selected by the PVC register writes of a flow (MAME formula, replayed over the ordered port events of each piece)."""
    out=set()
    for p in flow.pieces:
        st=flow.states[p['start']];ff8,ff9=st['bank'][1],st['bank'][2]
        for x in p['ports']:
            if x[0]!=1:continue
            if x[1]==0x2ffff0:ff8=x[3]
            else:ff9=x[3]
            base,ff8,ff9=pvc_bank_update(ff8,ff9);out.add(base)
    return sorted(out)


def piece_rows(env,flow,models):
    rows=[];first=True
    for p,(ok,diffs,info) in zip([p for p in flow.pieces if p['unit']],models):
        a=flow.states[p['start']];b=flow.states[p['end']]
        rows.append([p['unit'],a['pc'],p['trace'][-1][0] if p['trace'] else a['pc'],b['pc'],len(p['trace']),ok])
    return rows


def node_replay(env,entry,stops,limit,twice,sched_exit=None,regtrace=True,split=True):
    """Fresh-CPU replays of one start state: modes, model per unit piece, sched exit comparison.  Returns (result dict, flows)."""
    f=run_modes(env,entry,stops,limit,twice,regtrace,split);eq=compare_modes(f);c=f['cont']
    models=[model_piece(env,c,p) for p in c.pieces if p['unit']]
    res=dict(eq=eq,model_ok=all(m[0] for m in models),model_diffs=[(i,m[1]) for i,m in enumerate(models) if not m[0]][:3],final=c.final['kind'],
        guard=(c.final['detail'].get('kind') if c.final['kind']=='guard' else None),pieces=piece_rows(env,c,models),insns=sum(len(p['trace']) for p in c.pieces),waits=len(c.waits))
    leaders=[pc for p in c.pieces for pc in p['leaders']]
    res['leaders']=leaders
    if sched_exit is not None:
        fs=c.states[-1];res['sched_exit_eq']=S.state_blob_digest(fs['ram'],fs['regs'],fs['pc'],fs['bank'])==sched_exit
    return res,f,models


def process_node(run,node,exit_state,partial):
    env=GLOBAL['env'];plan=GLOBAL['plan'].get((run.case_id,run.frame,node['seq']))
    entry=dict(ram=node['entry_ram'],regs=dict(node['entry_regs']),pc=0x2ab8,bank=tuple(node['entry_bank']),ccr=0)
    tw=bool(plan) or (run.frame*131+node['seq'])%8==0
    rt=bool(plan) or (run.frame*7+node['seq'])%4==0
    res,f,models=node_replay(env,entry,(PASS_PC,),NAT_LIMIT,tw and rt,node['exit_digest'],rt,rt)
    c=f['cont']
    run.ipcs.update(x[0] for p in c.pieces for x in p['trace'])
    row=dict(frame=run.frame,seq=node['seq'],a6=node['a6'],cb=node['cb'],depth=node['depth'],partial=bool(partial),twice=tw,regtrace=rt,entry=node['entry_digest'][:16],exit=node['exit_digest'][:16],
        pieces=res['pieces'],insns=res['insns'],eq=res['eq'],model_ok=res['model_ok'],sched_exit_eq=res.get('sched_exit_eq'),final=res['final'],guard=res['guard'],waits=res['waits'],bank=c.states[-1]['bank'][0],banks_seen=sorted({s['bank'][0] for s in c.states}|set(pvc_banks_of(c))),bank_changes=sum(1 for p in c.pieces for x in p['ports'] if x[0]==1),
        leader_sha=sha(repr(res['leaders']).encode())[:16],leader_len=len(res['leaders']))
    if not res['model_ok']:row['model_diffs']=res['model_diffs']
    first=[];seen=set()
    for pc in res['leaders']:
        if pc not in seen:seen.add(pc);first.append(pc)
    row['leaders_first']=first
    # transfers out of unit pieces (computed jump targets, exits)
    xs=[]
    for p in c.pieces:
        if p['unit']:
            b=c.states[p['end']];last=p['trace'][-1][0] if p['trace'] else None
            xs.append([p['unit'],last,b['pc']])
    row['xfers']=xs
    if plan:
        row['captures']={}
        if plan.get('full'):
            row['dumps']=dict(entry=dump_state(entry),states=[dump_state(s) for s in c.states],exit=dump_state(c.states[-1]))
        for pc in plan.get('starts',()):
            fl=Flow(env,entry,'ref',(pc,),NAT_LIMIT).run()
            if fl.final['kind']=='stop' and fl.final['detail']['pc']==pc:
                row['captures'][pc]=dump_state(fl.states[-1])
        if plan.get('entry'):row['entry_dump']=dump_state(entry)
    return row


def pass_b_task(arg):
    case=arg;env=GLOBAL['env'];sd=S.SEEDS[case];snap,meta=S.seed_snap(sd)
    run=G1Run(GLOBAL['program'],S.G['fixed'],S.G['levels'],snap,'continuous',FRAMES,heavy=False,sink=None)
    run.case_id=case;run.node_task=process_node;run.run()
    return dict(case=case,kind=sd['kind'],family=sd['family'],stop=run.stop,frames_done=run.frames_done,run_digest=run.digest.hexdigest(),
        cb=dict(run.cb_counts),unit_nodes=run.unit_nodes,nodes=run.node_rows,meta=meta,covered=run.fully_covered,ipcs=sorted(run.ipcs),waits=dict(run.waits_total))


# ----------------------------------------------------------------------------------
# Static CFG of the contract blocks (from the model decoder; no capstone) and the coverage guided search for typed fixtures
# ----------------------------------------------------------------------------------
def build_cfg(env):
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0)
    cfg={};fan=collections.defaultdict(list)
    targets=set(env.starts)|set(env.traps)
    for s in sorted(env.starts):
        pc=s;succ=[];insns=[]
        while True:
            ins=mdl.decode(pc);insns.append(pc);nxt=(pc+ins.len)&M32;op=ins.op
            if op in ('bcc','dbcc'):succ+=[('br',ins.target),('ft',nxt)];break
            if op=='bra':succ.append(('br',ins.target));break
            if op=='jmp':
                if ins.src[0] in ('abs','pcd16'):succ.append(('jmp',ins.src[1]))
                break
            if op=='rts':break
            if op in ('jsr','bsr'):
                if op=='bsr':succ.append(('call',ins.target))
                elif ins.src[0] in ('abs','pcd16'):succ.append(('call',ins.src[1]))
                else:succ.append(('call?',None))
                succ.append(('ret',nxt));break
            if nxt in env.starts or nxt in env.traps or env.unit_of(nxt)!=env.starts[s]:
                succ.append(('ft',nxt));break
            pc=nxt
        cfg[s]=dict(unit=env.starts[s],insns=insns,succ=succ)
    return cfg


def install_entries(env):
    """Callback / child entries: MOVE.L #imm,(A6) and MOVEA.L #imm,A0 (28ae child creation) whose immediate is a contract block start."""
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0);out=set()
    for u,c in env.contracts.items():
        for lo,hi in c['ranges']:
            pc=lo
            while pc<hi:
                ins=mdl.decode(pc)
                if ins.op=='move' and ins.size==4 and ins.src[0]=='imm' and ins.dst==('ind',6) and ins.src[1] in env.starts:out.add(ins.src[1])
                if ins.op=='movea' and ins.size==4 and ins.src[0]=='imm' and ins.dst==('an',0) and ins.src[1] in env.starts:out.add(ins.src[1])
                pc+=ins.len
    return out


def cfg_distance(cfg,target):
    rev=collections.defaultdict(list)
    for s,b in cfg.items():
        for k,t in b['succ']:
            if t is not None:rev[t].append(s)
    dist={target:0};q=collections.deque([target])
    while q:
        x=q.popleft()
        for y in rev.get(x,()):
            if y not in dist:dist[y]=dist[x]+1;q.append(y)
    return dist


def hint_table(env):
    """Compare-with-immediate instructions of the units (CMPI.x #k,Dn / CMPI.x #k,d(An)): the search sets the compared operand to k (comparison guided mutation).  When the Dn was loaded by a
    MOVE.x <mem>,Dn earlier in the same block the memory operand is a hint as well."""
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0);tab={}
    starts=sorted(env.starts)
    for u,c in env.contracts.items():
        for lo,hi in c['ranges']:
            pc=lo;last={}
            while pc<hi:
                ins=mdl.decode(pc)
                if pc in env.starts:last={}
                if ins.op=='cmpi' and ins.dst:
                    d=ins.dst;lst=[]
                    if d[0]=='dn':
                        lst.append(('reg',d[1],ins.size,ins.imm))
                        w=last.get(d[1])
                        if w is not None:
                            src,sz=w
                            if src[0]=='ind':lst.append(('mem',src[1],0,sz,ins.imm))
                            elif src[0]=='post':lst.append(('mem',src[1],-sz,sz,ins.imm))
                            elif src[0]=='d16':lst.append(('mem',src[1],src[2],sz,ins.imm))
                    elif d[0]=='ind':lst.append(('mem',d[1],0,ins.size,ins.imm))
                    elif d[0]=='d16':lst.append(('mem',d[1],d[2],ins.size,ins.imm))
                    if lst:tab[pc]=lst
                if ins.op in ('move','moveq','movea','add','sub','clr','and','or','lea','ext','swap','neg','not','shift','addq','subq','addi','subi','andi','ori','eori','mulu','muls','exg'):
                    if ins.op=='move' and ins.dst and ins.dst[0]=='dn':last[ins.dst[1]]=(ins.src,ins.size)
                    elif ins.dst and ins.dst[0]=='dn':last.pop(ins.dst[1],None)
                    elif ins.op in ('moveq','add','sub','and','or','mulu','muls','ext','swap','neg','not','shift','exg') and ins.reg is not None:last.pop(ins.reg,None)
                pc+=ins.len
    return tab


def dict_values(env,unit):
    """Immediates and displacements of the unit's own instructions (the search dictionary)."""
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0);vals={0,1,2,3,4,7,8,0x10,0x20,0x40,0x7f,0x80,0xff,0x100,0x7fff,0x8000,0xffff,0xffffffff,0x10000,0xffff0000}
    for lo,hi in env.contracts[unit]['ranges']:
        pc=lo
        while pc<hi:
            try:ins=mdl.decode(pc)
            except MUnsupported:pc+=2;continue
            for ea in (ins.src,ins.dst):
                if ea and ea[0]=='imm':vals.add(ea[1])
                if ea and ea[0]=='d16':vals.add(ea[2]&0xffff)
            if ins.imm is not None and isinstance(ins.imm,int) and ins.op not in ('shift','bcc'):vals.add(ins.imm&M32)
            if ins.op=='moveq':vals.add(ins.imm&M32)
            pc+=ins.len
    out=set()
    for v in vals:
        out.add(v&M32);out.add((v+1)&M32);out.add((v-1)&M32)
    return sorted(out)


CNT=None                                         # shared mmap: index of the candidate being executed (an illegal opcode ABORTS Unicorn: the search runs in a forked child and the poisoned candidate is skipped)
FUZZ_STOPS=(PASS_PC,0x2a00)
SCRATCH_PTRS=tuple(0x10e800+0x40*k for k in range(16))   # declared scratch RAM pointers for the search (A-register mutation targets)
FUZZ_REGS=('d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5')


class Fuzzer(object):
    """Reusable CPU from an origin state; run(cand) = origin + declared edits, returns (hits, guard, reads)."""
    def __init__(self,env,origin,watch,stop_pcs,limit=5000):
        self.env=env;self.origin=origin;self.watch=frozenset(watch);self.stop_pcs=frozenset(stop_pcs);self.limit=limit
        self.m=None;self.count=0;self.poison=frozenset();self.hints=[];self.htab=GLOBAL['htab'];self.build()
    def build(self):
        env=self.env;m=make_machine(env,self.origin);self.m=m;c=m.cpu;me=self
        self.hits=[];self.reads=[];self.n=0
        def on_watch(uc,pc,size,user):
            if pc in me.watch:me.hits.append(pc)
            hl=me.htab.get(pc)
            if hl is not None and len(me.hints)<96:
                for h in hl:
                    if h[0]=='reg':me.hints.append(('reg',h[1],h[2],h[3]))
                    else:me.hints.append(('mem',(uc.reg_read(UC_REG['a%d'%h[1]])+h[2])&M32,h[3],h[4]))
        def on_stop(uc,pc,size,user):
            me.stopped=pc;me.hits.append(pc);uc.emu_stop()
        for lo,hi,u in env.range_list:c.hook_add(UC_HOOK_CODE,on_watch,begin=lo,end=hi-1)
        for pc in self.stop_pcs:c.hook_add(UC_HOOK_CODE,on_stop,begin=pc,end=pc)
        def rd(uc,access,address,size,value,user):
            if len(me.reads)<6000:me.reads.append(address)
        c.hook_add(UC_HOOK_MEM_READ,rd,begin=0x100000,end=0x1fffff)
        self.base_ram=self.origin['ram'];self.base_bank=self.origin['bank'][0]
    def run(self,cand):
        o=self.origin;m=self.m
        self.count+=1
        if CNT is not None:CNT[0:8]=struct.pack('>Q',self.count)
        if self.count in self.poison:return set(),None,[]
        if m.bank!=self.base_bank or m.ff8!=o['bank'][1] or m.ff9!=o['bank'][2]:self.build();m=self.m
        c=m.cpu
        ctypes.memmove(m.addr,self.base_ram,0x10000)
        for a,v in cand['ram'].items():ctypes.memset(m.addr+(a&0xffff),v,1)
        regs=dict(o['regs']);regs.update(cand['regs'])
        for k in KEYS:c.reg_write(UC_REG[k],regs[k]&M32)
        c.reg_write(SR_REG,0x2000|(cand['ccr']&0x1f));pc=cand.get('pc',o['pc'])
        m.ports=[];m.odd=None;m.invalid=None;m.intr=None;m.fetch_unmapped=None;self.hits=[];self.reads=[];self.n=0;self.stopped=None;self.hints=[]
        try:c.emu_start(pc,0xffffff,count=self.limit)
        except unicorn.UcError:pass
        g=guard_of(m)
        return set(self.hits),(g[0],m.pc()) if g else None,self.reads


def mutate(rng,cand,origin,dvals,reads,ptrs):
    c=dict(regs=dict(cand['regs']),ram=dict(cand['ram']),ccr=cand['ccr'])
    hints=cand.get('hints') or []
    for _ in range(rng.choice((1,1,2,3))):
        if hints and rng.random()<0.45:
            h=rng.choice(hints);delta=rng.choice((0,0,0,1,-1))
            if h[0]=='reg':
                k='d%d'%h[1];cur=c['regs'].get(k,origin['regs'][k]);mk=MASK[h[2]];c['regs'][k]=((cur&~mk&M32)|((h[3]+delta)&mk))&M32
            else:
                for i,b in enumerate(((h[3]+delta)&MASK[h[2]]).to_bytes(h[2],'big')):c['ram'][(h[1]+i)&0xffff]=b
            continue
        op=rng.randrange(8)
        if op==0 or op==1:
            k=rng.choice(FUZZ_REGS[:8]);cur=c['regs'].get(k,origin['regs'][k]);v=rng.choice(dvals);sz=rng.choice((1,2,4))
            c['regs'][k]=((cur&~MASK[sz])|(v&MASK[sz]))&M32
        elif op==2:
            k=rng.choice(FUZZ_REGS);cur=c['regs'].get(k,origin['regs'][k]);c['regs'][k]=(cur^(1<<rng.randrange(32)))&M32
        elif op==3 and ptrs:
            k=rng.choice(FUZZ_REGS[8:]);c['regs'][k]=rng.choice(ptrs)
        elif op in (4,5) and reads:
            a=rng.choice(reads);v=rng.choice(dvals)
            if op==4:c['ram'][a&0xffff]=v&0xff
            else:
                a&=~1
                for i,b in enumerate((v&0xffff).to_bytes(2,'big')):c['ram'][(a+i)&0xffff]=b
        elif op==6 and reads:
            a=rng.choice(reads)&~1;v=rng.choice(dvals) if (not ptrs or rng.random()<0.5) else rng.choice(ptrs)
            for i,b in enumerate((v&M32).to_bytes(4,'big')):c['ram'][(a+i)&0xffff]=b
        elif op==7:c['ccr']=rng.randrange(32)
        else:
            a=rng.randrange(0x10000);c['ram'][a]=rng.randrange(256)
    return c


def apply_cand(origin,cand):
    st=dict(origin);ram=bytearray(origin['ram'])
    for a,v in cand['ram'].items():ram[a&0xffff]=v
    st['ram']=bytes(ram);regs=dict(origin['regs']);regs.update(cand['regs']);st['regs']=regs
    if cand['ccr'] is not None:st['ccr']=cand['ccr']
    if cand.get('d0w0'):regs['d0']=regs['d0']&0xffff0000
    if 'pc' in cand:st['pc']=cand['pc']
    return st


def minimize(fz,cand,pred):
    """Greedy removal of RAM / register / CCR edits that the predicate does not need."""
    o=fz.origin
    cur=dict(regs=dict(cand['regs']),ram=dict(cand['ram']),ccr=cand['ccr'])
    if 'pc' in cand:cur['pc']=cand['pc']
    for key in sorted(cur['regs']):
        t=dict(cur,regs={k:v for k,v in cur['regs'].items() if k!=key})
        if pred(fz.run(t)):cur=t
    for a in sorted(cur['ram']):
        t=dict(cur,ram={k:v for k,v in cur['ram'].items() if k!=a})
        if pred(fz.run(t)):cur=t
    if cur['ccr']!=(o['ccr'] or 0):
        t=dict(cur,ccr=o['ccr'] or 0)
        if pred(fz.run(t)):cur=t
    return cur


def campaign(env,origin,targets,dvals,seed,budget,watch,stop_pcs,idle=3000,poison=frozenset()):
    """Search from `origin` for candidates that reach every pc in `targets` (a set).  Returns {target: candidate}."""
    rng=random.Random(seed);fz=Fuzzer(env,origin,watch,stop_pcs);fz.poison=poison
    base=dict(regs={},ram={},ccr=origin['ccr'] or 0)
    found={};seen=set();corpus=[base];allreads=[];ptrs=sorted({v for k,v in origin['regs'].items() if 0x100000<=v<0x110000 and not v&1}|set(SCRATCH_PTRS))
    hits,g,reads=fz.run(base);base['hints']=list(fz.hints);seen|=hits;readset=set(reads)|{a+i for a in SCRATCH_PTRS for i in range(0,0x30)};allreads=sorted(readset)
    for t in targets:
        if t in hits:found[t]=base
    last=0;n=0
    while len(found)<len(targets) and n<budget and n-last<idle:
        n+=1;parent=corpus[rng.randrange(len(corpus))]
        cand=mutate(rng,parent,origin,dvals,allreads,ptrs)
        hits,g,reads=fz.run(cand);cand['hints']=list(fz.hints)
        new=hits-seen;nr=set(reads)-readset
        if new or (nr and len(corpus)<300):
            seen|=hits;corpus.append(cand)
            if new:last=n
            readset|=set(reads);allreads=sorted(readset)[:6000]
            for t in new:
                if t in targets and t not in found:found[t]=cand
    out={}
    for t,cand in found.items():
        out[t]=minimize(fz,cand,lambda r,t=t:t in r[0])
    return out,dict(execs=n+1,corpus=len(corpus),seen=len(seen),poisoned=len(poison))


# ----------------------------------------------------------------------------------
# Fixture search tasks and fixture verification
# ----------------------------------------------------------------------------------
FUZZ_LIMIT=6000



import mmap


def isolated(fn,arg):
    """fn(arg) in a forked child (os.fork; pickled result through a pipe).  Returns (ok, result_or_None, last candidate index)."""
    global CNT
    CNT=mmap.mmap(-1,8);CNT[0:8]=struct.pack('>Q',0)
    r,w=os.pipe();pid=os.fork()
    if pid==0:
        try:
            os.close(r);import pickle as _p;data=_p.dumps(fn(arg),protocol=4)
            f=os.fdopen(w,'wb');f.write(data);f.close();os._exit(0)
        except BaseException:
            import traceback;traceback.print_exc();os._exit(3)
    os.close(w);chunks=[];import select,signal;stall=0;lastc=-1;killed=False
    while True:
        rd,_,_=select.select([r],[],[],5.0)
        if rd:
            b=os.read(r,1<<20)
            if not b:break
            chunks.append(b);continue
        c=struct.unpack('>Q',CNT[0:8])[0]
        if c==lastc:
            stall+=1
            if stall>=6:os.kill(pid,signal.SIGKILL);killed=True;break          # one candidate did not finish in 30 s: a hang is poisoned like an abort
        else:stall=0;lastc=c
    os.close(r);_,status=os.waitpid(pid,0)
    if killed:status=-9
    last=struct.unpack('>Q',CNT[0:8])[0]
    if status==0:
        import pickle as _p;return True,_p.loads(b''.join(chunks)),last
    return False,None,last


def with_poison(fn,arg_fn):
    """Retry a deterministic search, skipping (poisoning) the candidate index that aborted the child, until it completes."""
    poison=set();crashes=[]
    for _ in range(60):
        ok,res,last=isolated(fn,arg_fn(frozenset(poison)))
        if ok:
            res['crashes']=sorted(crashes);return res
        poison.add(last);crashes.append(last)
    raise RuntimeError('search keeps aborting')


def fix_stops(env):
    return frozenset(FUZZ_STOPS)|frozenset(env.traps)|frozenset(env.boundary)


def cand_json(c):
    d=dict(regs={k:hx(v) for k,v in sorted(c['regs'].items())},ram=[[hx(a),v] for a,v in sorted(c['ram'].items())],ccr=c['ccr'])
    if c.get('d0w0'):d['d0_word_zero']=True
    if c.get('a6long'):d['a6_long']=[hx(c['a6long'][0]),hx(c['a6long'][1])]
    if 'pc' in c:d['pc']=hx(c['pc'])
    return d


def campaign_inner(arg):
    env=GLOBAL['env'];origin_row,origin_pc,targets,seed,budget,poison=arg
    origin=load_state(origin_row);dv=GLOBAL['dvals']
    watch=set(env.starts)|set(env.traps)|set(env.boundary)
    stops=set(fix_stops(env))
    found,stats=campaign(env,origin,set(targets),dv,seed,budget,watch,stops,poison=poison)
    return dict(origin_pc=origin_pc,found=found,stats=stats,asked=sorted(targets))


def campaign_task(arg):
    origin_row,origin_pc,targets,seed,budget=arg
    res=with_poison(campaign_inner,lambda poison:(origin_row,origin_pc,targets,seed,budget,poison))
    res['stats']['crashes']=res.pop('crashes');return res


def guard_task(arg):
    origin_row,origin_pc,seed,budget=arg
    res=with_poison(guard_inner,lambda poison:(origin_row,origin_pc,seed,budget,poison))
    res.pop('crashes',None);return res


def guard_inner(arg):
    """Search for odd / ROM-write / unmapped guards inside unit code from one origin: returns {(unit,kind,pc): candidate} (minimized)."""
    env=GLOBAL['env'];origin_row,origin_pc,seed,budget,poison=arg
    origin=load_state(origin_row);dv=GLOBAL['dvals'];rng=random.Random(seed)
    watch=set(env.starts)|set(env.traps)|set(env.boundary)
    fz=Fuzzer(env,origin,watch,set(fix_stops(env)));fz.poison=poison
    base=dict(regs={},ram={},ccr=origin['ccr'] or 0)
    hits,g,reads=fz.run(base);allreads=sorted(set(reads));ptrs=sorted({v for v in origin['regs'].values() if 0x100000<=v<0x110000 and not v&1})
    out={}
    for n in range(budget):
        cand=mutate(rng,base,origin,dv,allreads,ptrs)
        # a guard-oriented bias: break one pointer register to an odd / ROM address
        if rng.random()<0.5:
            k=rng.choice(FUZZ_REGS[8:]);cand['regs'][k]=rng.choice((cand['regs'].get(k,origin['regs'][k])|1,0x1000+rng.randrange(0x800)*2,0x1010,0x100001+rng.randrange(0x4000)*2))
        hits,g,reads=fz.run(cand)
        if g and g[0] in ('odd-read','odd-write','rom-write','unmapped-read','unmapped-write','bank-read-outside-rom','fetch-unmapped','odd-pc'):
            u=env.unit_of(g[1]) if g[0] not in ('odd-pc','fetch-unmapped') else 0
            key=(u,g[0],g[1])
            if u and key not in out and sum(1 for k in out if k[:2]==(u,g[0]))<2:out[key]=cand
    res={}
    for key,cand in out.items():
        res[key]=minimize(fz,cand,lambda r,key=key:bool(r[1]) and r[1][0]==key[1] and r[1][1]==key[2])
    return dict(origin_pc=origin_pc,guards=res)


def build_start(env,fx,origin):
    st=apply_cand(origin,fx['cand'])
    if fx.get('at') is not None:
        fl=Flow(env,st,'ref',set(fix_stops(env))|{fx['at']},NAT_LIMIT).run()
        if fl.final['kind']!='stop' or fl.final['detail']['pc']!=fx['at']:return None,fl
        st=fl.states[-1]
        post=fx.get('post')
        if post:
            st=apply_cand(st,post)
            if post.get('a6long'):
                ram=bytearray(st['ram']);off,val=post['a6long'];a6=st['regs']['a6']
                for i,b in enumerate((val&M32).to_bytes(4,'big')):ram[(a6+off+i)&0xffff]=b
                st=dict(st,ram=bytes(ram))
    return st,None


def fixture_task(arg):
    env=GLOBAL['env'];fx,origin_row=arg
    origin=load_state(origin_row) if origin_row else None
    st,fail=build_start(env,fx,origin)
    row=dict(name=fx['name'],kind=fx['kind'],unit=fx.get('unit'),targets=sorted(fx.get('targets',())),origin=fx.get('origin_ref'),edits=cand_json(fx['cand']),at=fx.get('at') and hx(fx['at']),
        post=fx.get('post') and cand_json(fx['post']),why=fx.get('why',''),jump_target=fx.get('jump_target'))
    if st is None:
        row.update(ok=False,error='state-at not reached',final=fail.final['kind']);return row
    res,f,models=node_replay(GLOBAL['env'],st,tuple(sorted(fix_stops(env))),GLOBAL['fix_limit'],True)
    c=f['cont']
    row.update(eq=res['eq'],model_ok=res['model_ok'],final=res['final'],final_detail=json.loads(sjson(c.final['detail'])),insns=res['insns'],pieces=res['pieces'],
        leaders_first=[],waits=res['waits'])
    seen=set()
    for pc in res['leaders']:
        if pc not in seen:seen.add(pc);row['leaders_first'].append(pc)
    row['leader_len']=len(res['leaders']);row['leader_sha']=sha(repr(res['leaders']).encode())[:16]
    if not res['model_ok']:row['model_diffs']=res['model_diffs']
    row['xfers']=[[p['unit'],p['trace'][-1][0],c.states[p['end']]['pc']] for p in c.pieces if p['unit']]
    row['reached']=sorted(set(row['leaders_first'])|({c.final['detail']['pc']} if c.final['kind']=='stop' else set()))
    row['start']=dump_state(st);row['dumps']=[dump_state(s) for s in c.states[1:]]
    row['ports_sha']=ports_sha(c.ports_all);row['ports']=len(c.ports_all);row['pvc_banks']=pvc_banks_of(c)
    row['ok']=all(res['eq'].values()) and res['model_ok']
    return row


# ----------------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------------
def merge_counters(items):
    c=collections.Counter()
    for i in items:c.update(i)
    return c


def computed_jumps(env):
    out=[]
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0)
    for u,c in sorted(env.contracts.items()):
        for lo,hi in c['ranges']:
            pc=lo
            while pc<hi:
                ins=mdl.decode(pc)
                if ins.op in ('jsr','jmp') and ins.src[0] not in ('abs','pcd16'):out.append((u,pc,ins.op,ins.src))
                pc+=ins.len
    return out


def carry_consumers(env):
    """Blocks whose FIRST instruction reads a flag that no instruction of the block set (flags come from the caller / a callee)."""
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0);out=[]
    for s in sorted(env.starts):
        ins=mdl.decode(s)
        if (ins.op in ('bcc','scc','dbcc') and ins.cond not in (0,1)):out.append(s)
    return out


def block_of(cfg,pc):
    for s,b in cfg.items():
        if pc in b['insns']:return s
    return None


def stage_natural(env,args,out_dir,cases):
    ctx=multiprocessing.get_context('fork')
    GLOBAL.update(plan={},twice=False)
    with ctx.Pool(args.workers) as pool:a_list=pool.map(pass_a_task,cases,chunksize=1)
    # plan: first node (seed order) per block start; first two nodes per callback; first node per callback in each of the first 8 natural seeds with unit nodes
    plan=collections.defaultdict(lambda:dict(starts=[],full=False,entry=False))
    first_start={};cb_nodes=collections.defaultdict(list);seed_cb={};used_seeds=0
    for a in a_list:
        seen_cb=set()
        for frame,seq,cb,hits,partial in a['nodes']:
            for pc in hits:
                if pc not in first_start:first_start[pc]=(a['case'],frame,seq)
            if len(cb_nodes[cb])<2:cb_nodes[cb].append((a['case'],frame,seq))
            if a['kind']=='natural' and cb not in seen_cb and used_seeds<8:seen_cb.add(cb);cb_nodes.setdefault(('seed',a['case']),[]).append((a['case'],frame,seq))
        if a['kind']=='natural' and a['nodes'] and used_seeds<8:used_seeds+=1
    for pc,(case,frame,seq) in sorted(first_start.items()):plan[(case,frame,seq)]['starts'].append(pc)
    for k,v in cb_nodes.items():
        for ref in v:plan[ref]['full']=True;plan[ref]['entry']=True
    GLOBAL['plan']=dict(plan)
    GLOBAL['twice']=False
    with ctx.Pool(args.workers) as pool:b_list=pool.map(pass_b_task,cases,chunksize=1)
    return a_list,b_list,first_start


def crc(*xs):return int(sha(repr(xs).encode())[:8],16)


def empty_cand(origin_ccr=0):return dict(regs={},ram={},ccr=origin_ccr or 0)


def stage_fixtures(env,args,b_list,out_dir):
    ctx=multiprocessing.get_context('fork')
    origins={};entries={}
    for b in b_list:
        for n in b['nodes']:
            for pc,row in n.get('captures',{}).items():origins.setdefault(pc,(row,(b['case'],n['frame'],n['seq'])))
            if n.get('entry_dump') and n['cb'] not in entries:entries[n['cb']]=(n['entry_dump'],(b['case'],n['frame'],n['seq']))
    nat=set()
    nat_xfer_to=set()
    for b in b_list:
        for n in b['nodes']:
            nat.update(n['leaders_first'])
            for u,last,to in n['xfers']:nat_xfer_to.add(to)
    cfg=build_cfg(env)
    GLOBAL['dvals']=sorted(set(v for u in range(1,8) for v in dict_values(env,u)));GLOBAL['htab']=hint_table(env)
    targets=[pc for pc in sorted(env.starts) if pc not in nat]
    targets+=[pc for pc in sorted(env.traps)]+[pc for pc in sorted(env.boundary) if pc not in nat_xfer_to]
    dist={t:cfg_distance(cfg,t) for t in targets}
    recipes={}
    for pc in sorted(env.starts):
        if pc in nat:
            if pc in origins:recipes[pc]=dict(kind='natural',origin_pc=pc,origin=origins[pc],cand=empty_cand())
    rounds=[];pending=list(targets);pseudo={}
    _,entries_by_unit=cfg_contract_check(env,cfg)
    entry_set={e for u in entries_by_unit for e in entries_by_unit[u]}|install_entries(env)
    unit_origins=collections.defaultdict(list)
    for o in sorted(origins):unit_origins[env.starts.get(o,0)].append(o)
    for rnd in range(5):
        if rnd==2:
            # callback / function entries the paths could not reach: declared direct entries (state of a natural node of the unit, PC := entry) become origins of their own
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
        tasks=[(allo[o][0],o,sorted(ts),crc('c',o,rnd),args.budget) for o,ts in sorted(groups.items())]
        GLOBAL['plan']={}
        with ctx.Pool(args.workers) as pool:res=pool.map(campaign_task,tasks,chunksize=1)
        for r in res:
            for tt,cand in sorted(r['found'].items()):
                if tt not in recipes:
                    if r['origin_pc'] in pseudo:
                        row,ref,o=pseudo[r['origin_pc']];recipes[tt]=dict(kind='path-from-entry',origin_pc=r['origin_pc'],origin=(row,ref),cand=cand,round=rnd)
                    else:recipes[tt]=dict(kind='path',origin_pc=r['origin_pc'],origin=origins[r['origin_pc']],cand=cand,round=rnd)
            rounds.append(dict(round=rnd,origin=r['origin_pc'],asked=r['asked'],found=sorted(r['found']),stats=r['stats']))
        pending=[tt for tt in pending if tt not in recipes and tt not in pseudo]
        if not pending and rnd>=2:break
    for e,(row,ref,o) in sorted(pseudo.items()):
        if e not in recipes:recipes[e]=dict(kind='entry-self',origin_pc=o,origin=origins[o],cand=dict(regs={},ram={},ccr=0,pc=e))
    # still unreached: declared direct entry at the target on the nearest origin of the same unit
    fallback=[]
    for tt in pending:
        u=env.starts.get(tt) or env.traps.get(tt) or env.boundary.get(tt) or 0
        pool_o=unit_origins.get(u) or sorted(origins)
        o=pool_o[0]
        recipes[tt]=dict(kind='entry-self',origin_pc=o,origin=origins[o],cand=dict(regs={},ram={},ccr=0,pc=tt))
    fallback=sorted(tt for tt,rc in recipes.items() if rc['kind']=='entry-self')
    return dict(origins=origins,entries=entries,nat=nat,nat_xfer_to=nat_xfer_to,cfg=cfg,recipes=recipes,rounds=rounds,fallback=fallback,targets=targets)


def recipe_fixture(name,kind,rc,unit=None,targets=(),why=''):
    row,ref=rc['origin']
    return dict(name=name,kind=kind,unit=unit,targets=list(targets),cand=rc['cand'],origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=rc['origin_pc'],how=rc['kind']),why=why)


CCR_VARIANTS={2:(0,1),3:(0,1),4:(0,1),5:(0,1),6:(0,4),7:(0,4),8:(0,2),9:(0,2),10:(0,8),11:(0,8),12:(0,0x0a),13:(0,0x0a),14:(0,0x0c),15:(0,0x0c)}
JUMP_TARGETS={'a1':(0xe84c8,0x3650,0xe84c9,0xc00468,0x4e184,0x1aaf6),'a0d0':(0xe74f2,0xe74b6,0xe7546,0xe74f8,0xe7562,0xe74f3,0xc00468,0x4e184)}


def hand_fixtures(env,fs,b_list):
    """Fixtures of the contract minimum conditions on top of the search results: carry consumers with declared SR, computed jumps, 2986 failure paths."""
    cfg=fs['cfg'];rec=fs['recipes'];out=[]
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0)
    for s in carry_consumers(env):
        rc=rec.get(s)
        if rc is None:continue
        ins=mdl.decode(s);u=env.starts[s]
        for ccr in CCR_VARIANTS.get(ins.cond,(0,1)):
            fx=recipe_fixture('carry-consumer %x ccr=%02x'%(s,ccr),'carry-consumer',rc,u,[s],'block %x reads flags (cond %d) set by an earlier instruction / callee: declared CCR %02x at the block start'%(s,ins.cond,ccr))
            fx['at']=s;fx['post']=dict(regs={},ram={},ccr=ccr);out.append(fx)
    for u,pc,op,src in computed_jumps(env):
        B=block_of(cfg,pc);rc=rec.get(B)
        if rc is None:continue
        if src[0]=='ind' and src[1]==1:tg=JUMP_TARGETS['a1'];kind='a1'
        else:tg=JUMP_TARGETS['a0d0'];kind='a0d0'
        for T in tg:
            post=dict(regs={},ram={},ccr=None)
            if kind=='a1':post['regs']['a1']=T
            else:post['regs']['a0']=T;post['d0w0']=True       # D0.W := 0 (JSR (A0,D0.W) = A0)
            fx=recipe_fixture('computed-jump %x %s -> %x'%(pc,op,T),'computed-jump',rc,u,[B],'computed %s %s at %x with target %x'%(op,kind,pc,T))
            fx['at']=pc;fx['post']=post;fx['jump_target']=T;out.append(fx)
    # PVC banks: eba3e selects bank 200000 + n * 100000 from the low 3 bits of LONG 80(A6); n = 0..7 reaches the banks 2..9 (6, 7, ... lie beyond the 8 MiB image)
    rc=rec.get(0xeba3e)
    if rc is not None:
        for n in range(8):
            for v in (n,n|0x8):
                fx=recipe_fixture('pvc-bank eba3e LONG80(A6)=%x'%v,'pvc-bank',rc,6,[0xeba3e],'eba3e with LONG 80(A6) := %x: PVC writes select bank base %x (MAME formula, any base is a state)'%(v,0x200000+n*0x100000))
                fx['at']=0xeba3e;fx['post']=dict(regs={},ram={},ccr=None,a6long=(0x80,v));out.append(fx)
    # 2986 / 28ae failure path: child object creation fails when D0.W >= WORD 104ca0
    for cb in (0xe585c,0xe5120,0xd72f2):
        e=fs['entries'].get(cb)
        if not e:continue
        row,ref=e
        c=dict(regs={},ram={0x4ca0:0,0x4ca1:0},ccr=0)
        out.append(dict(name='28ae-failure %x'%cb,kind='28ae-failure',unit=env.unit_of(cb),targets=[],cand=c,origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=0x2ab8,how='node-entry'),
            why='node %x entry with WORD 104ca0 := 0: 28ae fails (D0.W >= 104ca0), the 2986 / 28ae failure path runs natively'%cb))
    return out



def stage_verify(env,args,fs,b_list,out_dir):
    ctx=multiprocessing.get_context('fork');origins=fs['origins']
    # guard search: three natural origins per unit
    gtasks=[]
    by_unit=collections.defaultdict(list)
    for o in sorted(origins):
        u=env.starts.get(o)
        if u:by_unit[u].append(o)
    for u in sorted(by_unit):
        lst=by_unit[u];pick=lst[::max(1,len(lst)//3)][:3]
        for o in pick:gtasks.append((origins[o][0],o,crc('g',o),args.budget//2))
    with ctx.Pool(args.workers) as pool:gres=pool.map(guard_task,gtasks,chunksize=1)
    fixtures=[];groups=collections.OrderedDict()
    for tt,rc in sorted(fs['recipes'].items()):
        if rc['kind']=='natural':continue
        key=(rc['origin_pc'],sjson(cand_json(rc['cand'])),rc['kind'])
        groups.setdefault(key,[]).append((tt,rc))
    for i,(key,lst) in enumerate(groups.items()):
        rc=lst[0][1];ts=[tt for tt,_ in lst];u=env.starts.get(ts[0]) or env.traps.get(ts[0]) or env.boundary.get(ts[0])
        fixtures.append(recipe_fixture('reach-%s-%03d'%(rc['kind'],i),rc['kind'],rc,u,ts,'search result: the minimized edit list reaches '+' '.join('%x'%x for x in ts)))
    fixtures+=hand_fixtures(env,fs,b_list)
    gi=0
    for r in gres:
        row,ref=origins[r['origin_pc']]
        for (u,kind,pc),cand in sorted(r['guards'].items()):
            fixtures.append(dict(name='guard-%s-u%d-%x-%03d'%(kind,u,pc,gi),kind='guard',unit=u,targets=[],cand=cand,origin_row=row,origin_ref=dict(case=ref[0],frame=ref[1],seq=ref[2],pc=r['origin_pc'],how='natural+edits'),
                why='search result: %s at %x inside unit %d'%(kind,pc,u)));gi+=1
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:rows=pool.map(fixture_task,[(fx,fx['origin_row']) for fx in fixtures],chunksize=1)
    return rows,fixtures,gres



GUARD_TEXT={
    'rom-write':'a store into the write protected program ROM (0..fffff) stops the run (the F1c / scheduler RNG-pointer rule: a game callback calls the RNG 49a58 whose ring pointer LONG 10d722 is 0 in the seed RAM); the original hardware would ignore the write',
    'odd-read':'a WORD / LONG read at an odd address (address error on the real 68000); stops before the instruction completes',
    'odd-write':'a WORD / LONG write at an odd address (address error on the real 68000); the Unicorn hook lets the store complete, the model patches it for the RAM compare',
    'odd-pc':'a control transfer to an odd PC (address error on the real 68000)',
    'fetch-unmapped':'an instruction fetch at an unmapped address (BIOS c00468 and similar): the BIOS body is never executed',
    'fetch-protected':'an instruction fetch from RAM (mapped without EXEC)',
    'bank-read-outside-rom':'a read of the banked window beyond the 8 MiB image (PvcMachine)',
    'step-limit':'the declared instruction watchdog expired (the original code has no bound)'}
LIMITATIONS=[
    'The frame pass, the node entry form (PC 2ab8, A6 = node, A7 = SPd, CCR 0) and the declared waits are the scheduler observer declared model, not natural execution; no BIOS, IRQ or scheduler is claimed.',
    'An illegal opcode ABORTS the Unicorn m68k translator (process abort); the fixture search therefore runs in a forked child and poisons the aborting candidate (counted in the search rounds).',
    'The Unicorn SR read is stale for V / C (lazy flags); the observer reads the exact CCR with a MOVE SR,D0 probe at 500000 at every piece boundary.',
    'Natural nodes: ref / continuous / model for every node, split for the sampled nodes (see natural.replays), twice for the sampled subset; the whole tool is run twice and the outputs are compared.',
    'The block carry classification is a MODEL experiment (C_in 0/1 x 6 register variants over the captured state); the model is verified against native on every piece, but the per-block C_out is not read natively.',
    'Typed fixtures are declared states (natural capture + recorded edit list); kind entry-self means the search did not reach the block by a path within the budget and the fixture enters the block directly.']


def claim(cid,text,expected,observed,verdict,note=''):
    return dict(id=cid,claim=text,expected=expected,observed=observed,verdict=verdict,note=note)


def parse_contract_unreached(u):
    t=contract_path(u).read_text()
    m=re.search(r'미도달[^\n:：]*?(\d+)개[^\n:：]*[:：]([^\n]*)',t)
    if not m:return None
    out=sorted({int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`',m.group(2))})
    return out if len(out)==int(m.group(1)) else None


def parse_contract_cb_counts(u):
    t=contract_path(u).read_text()
    if '## 자연 시작 상태' not in t:return None
    s=t[t.index('## 자연 시작 상태'):];s=s[:s.index('\n\n')] if False else s[:s.index('\n- ')] if False else s
    m=re.search(r'U0\d callback node 실행:([^\n]*)',s)
    if not m:return None
    return {int(a,16):int(b.replace(',','')) for a,b in re.findall(r'`([0-9a-f]+)` ([0-9,]+)',m.group(1))}


def count_ranges(env):
    mdl=Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0);out={}
    for u,c in env.contracts.items():
        n=0;ops=collections.Counter()
        for lo,hi in c['ranges']:
            pc=lo
            while pc<hi:
                ins=mdl.decode(pc);n+=1;ops[ins.op]+=1;pc+=ins.len
            assert pc==hi,(u,hex(lo),hex(hi),hex(pc))
        out[u]=(n,dict(ops))
    return out


def cfg_contract_check(env,cfg):
    """CFG-derived leaders (decoder) against the contract block starts."""
    extra=collections.defaultdict(set);derived=collections.defaultdict(set)
    for s,b in cfg.items():
        u=b['unit']
        for k,t in b['succ']:
            if t is None:continue
            if env.unit_of(t)==u:
                derived[u].add(t)
                if t not in env.starts:extra[u].add(t)
    entries={u:sorted(set(env.contracts[u]['starts'])-derived[u]) for u in range(1,8)}
    return {u:sorted(extra[u]) for u in range(1,8)},entries


def sched_cb_counts_excluding(cases):
    """Callback counts of the recorded scheduler artifact restricted to the replayed seeds (per-seed gz files)."""
    c=collections.Counter()
    for case in cases:
        doc=json.loads(gzip.decompress((SCHED_DIR/'seeds'/('seed_%04d.json.gz'%case)).read_bytes()))
        for p in doc['passes']:
            for n in p['nodes']:c[n['cb']]+=1
    return c


def build_report(env,args,a_list,b_list,fs,rows,fixtures,gres,out_dir,t0,rom_start):
    cases=[b['case'] for b in b_list]
    nat=fs['nat'];cfg=fs['cfg']
    node_rows=[(b['case'],n) for b in b_list for n in b['nodes']]
    # ---- natural aggregates
    eqc=collections.Counter();modelc=collections.Counter();finalc=collections.Counter();guardc=collections.Counter();pieces=0;insns=0
    nodes_per_start=collections.Counter();xf=collections.Counter()
    for case,n in node_rows:
        for k,v in n['eq'].items():eqc[(k,v)]+=1
        modelc[n['model_ok']]+=1;finalc[n['final']]+=1;pieces+=len(n['pieces']);insns+=n['insns']
        if n['guard']:guardc[n['guard']]+=1
        for pc in n['leaders_first']:nodes_per_start[pc]+=1
        for u,last,to in n['xfers']:xf[(u,last,to)]+=1
    sched_exit=collections.Counter(n['sched_exit_eq'] for case,n in node_rows)
    banks=collections.Counter(hx(n['bank']) for case,n in node_rows);banks_seen=collections.Counter(hx(b) for case,n in node_rows for b in n['banks_seen']);pvc_nodes=sum(1 for case,n in node_rows if n['bank_changes'])
    sampled=dict(split=sum(1 for c,n in node_rows if 'cont_split' in n['eq']),twice=sum(1 for c,n in node_rows if 'cont_twice' in n['eq']),regtrace=sum(1 for c,n in node_rows if n['regtrace']))
    ipcs=set()
    for b in b_list:ipcs.update(b['ipcs'])
    cb_total=merge_counters(b['cb'] for b in b_list)
    ref_cases=[c for c in cases if c not in (58,59)]
    sched_cb=sched_cb_counts_excluding(ref_cases)
    mine_cb=merge_counters(b['cb'] for b in b_list if b['case'] not in (58,59))
    cb_diff={hx(k):(sched_cb.get(k,0),mine_cb.get(k,0)) for k in sorted(set(sched_cb)|set(mine_cb)) if sched_cb.get(k,0)!=mine_cb.get(k,0)}
    seed_rows=[dict(case=b['case'],kind=b['kind'],family=b['family'],stop=b['stop'],frames_done=b['frames_done'],unit_nodes=b['unit_nodes'],run_digest=b['run_digest'],
        eq_bad=sum(1 for n in b['nodes'] if not all(n['eq'].values())),model_bad=sum(1 for n in b['nodes'] if not n['model_ok']),exit_bad=sum(1 for n in b['nodes'] if not n['sched_exit_eq'])) for b in b_list]
    # ---- typed aggregates
    ok_rows=[r for r in rows if r['ok']];typed=set()
    for r in ok_rows:typed.update(r['reached'])
    kinds=collections.Counter(r['kind'] for r in rows)
    # ---- per unit
    counts=count_ranges(env);extra_derived,entries=cfg_contract_check(env,cfg)
    units=[];discrep=[]
    for u in range(1,8):
        c=env.contracts[u];st=c['starts']
        nat_u=[pc for pc in st if pc in nat];typ_u=[pc for pc in st if pc in typed and pc not in nat];un=[pc for pc in st if pc not in nat and pc not in typed]
        trap_rows={hx(pc):[r['name'] for r in ok_rows if r['final']=='stop' and r['final_detail'].get('pc')==pc][:3] for pc in c['traps']}
        bnd={hx(pc):dict(natural=pc in fs['nat_xfer_to'],fixtures=[r['name'] for r in ok_rows if pc in r['reached'] or any(x[2]==pc for x in r['xfers'])][:3]) for pc in BOUNDARY[u]}
        cu=parse_contract_unreached(u)
        if cu is not None:cu=[x for x in cu if x in env.starts]
        mine_un=sorted(pc for pc in st if pc not in nat)
        cmpu=None
        if cu is not None:
            only_c=sorted(set(cu)-set(mine_un));only_m=sorted(set(mine_un)-set(cu))
            cmpu=dict(contract_unreached=len(cu),observed_unreached=len(mine_un),only_in_contract_list=[hx(x) for x in only_c],only_in_observed=[hx(x) for x in only_m])
            if only_c or only_m:discrep.append(dict(id='U%02d-natural-unreached'%u,claim='contract natural-unreached list (TB based scratch replay) vs instruction level natural replay of the 142 seeds',detail=cmpu))
        ccb=parse_contract_cb_counts(u)
        if ccb:
            mine={k:cb_total.get(k,0) for k in ccb}
            dd={hx(k):(ccb[k],mine[k]) for k in ccb if ccb[k]!=mine[k]}
            if dd:discrep.append(dict(id='U%02d-callback-counts'%u,claim='contract natural callback node counts (scratch replay 120/400 frames) vs observer counts (all seeds incl. 58/59 beyond eba5c)',detail=dd))
        ex=extra_derived[u]
        if ex:discrep.append(dict(id='U%02d-cfg-leaders-not-in-contract'%u,claim='decoder derived branch / fall-through targets inside the unit that the contract does not list as block starts (bound branches excluded below)',detail=[hx(x) for x in ex if x not in c['merged']],bound_in_contract=[hx(x) for x in ex if x in c['merged']]))
        units.append(dict(unit=u,contract=contract_path(u).name,contract_sha=c['sha'],ranges=[[hx(a),hx(b)] for a,b in c['ranges']],code_bytes=c['bytes'],instructions=counts[u][0],blocks_expected=EXPECT_STARTS[u],blocks_parsed=len(st),
            traps=[hx(x) for x in c['traps']],bound_branch_pcs=[hx(x) for x in c['merged']],natural_reached=len(nat_u),typed_only_reached=len(typ_u),union_reached=len(nat_u)+len(typ_u),unreached=[hx(x) for x in un],
            natural_unreached=[hx(x) for x in mine_un],typed_by_kind={},trap_stops=trap_rows,boundary=bnd,compare_contract_unreached=cmpu,cfg_entries_not_derived=[hx(x) for x in entries[u]],
            natural_nodes_per_start={hx(pc):nodes_per_start[pc] for pc in nat_u}))
    # typed by kind
    for r in ok_rows:
        for pc in r['reached']:
            u=env.starts.get(pc)
            if u and pc not in nat:
                d=units[u-1]['typed_by_kind'];d.setdefault(r['kind'],[]).append(hx(pc))
    for d in units:
        for k in d['typed_by_kind']:d['typed_by_kind'][k]=sorted(set(d['typed_by_kind'][k]))
    # ---- guards
    gsum=collections.Counter()
    for r in ok_rows:
        if r['final']=='guard':gsum[(r['unit'],r['final_detail']['kind'])]+=1
    nat_guard_rows=[dict(case=b['case'],stop=b['stop']) for b in b_list if b['stop']['reason']!='frame-limit']
    # ---- claims
    claims=[]
    for u in range(1,8):
        claims.append(claim('U%02d-blocks'%u,'contract block start count',EXPECT_STARTS[u],len(env.contracts[u]['starts']),'matches' if len(env.contracts[u]['starts'])==EXPECT_STARTS[u] else 'differs'))
    exp_ins={1:279,2:395,3:282,4:211,5:169,6:320,7:196}
    for u in range(1,8):claims.append(claim('U%02d-instructions'%u,'contract instruction count decoded by the observer model decoder',exp_ins[u],counts[u][0],'matches' if counts[u][0]==exp_ins[u] else 'differs'))
    claims.append(claim('NAT-nodes','every natural unit node: fresh-CPU ref == continuous (all nodes), == split (%d nodes), twice (%d nodes), scheduler exit state reproduced, model equal on every unit piece (PC + registers per instruction on %d nodes, PC only on the rest)'%(sampled['split'],sampled['twice'],sampled['regtrace']),len(node_rows),
        dict(ref_cont=eqc[('ref_cont',True)],cont_split=eqc[('cont_split',True)],sched_exit=sched_exit[True],model=modelc[True]),'matches' if all(eqc[(k,False)]==0 for k in ('ref_cont','cont_split')) and sched_exit[False]==0 and modelc[False]==0 else 'differs'))
    claims.append(claim('NAT-callbacks','callback counts of the replayed seeds (all except 58/59) vs the recorded scheduler artifact',0,len(cb_diff),'matches' if not cb_diff else 'differs','' if not cb_diff else json.dumps(cb_diff)))
    claims.append(claim('TYPED-all-blocks','every contract block start reached naturally or by a typed fixture','0 unreached',sum(len(d['unreached']) for d in units),'matches' if not any(d['unreached'] for d in units) else 'differs'))
    claims.append(claim('TYPED-fixtures','typed fixtures: fresh-CPU ref == continuous == split, each twice, model equal on every unit piece',len(rows),len(ok_rows),'matches' if len(ok_rows)==len(rows) else 'differs'))
    for d in units:
        if d['traps']:claims.append(claim('U%02d-traps'%d['unit'],'TRAP boundaries stopped before execution by a fixture',d['traps'],[k for k,v in d['trap_stops'].items() if v],'matches' if all(d['trap_stops'].values()) else 'differs'))
    sizes=dir_sizes(out_dir)
    report=dict(schema_version=1,tool='tools/observe_animation_machine_objects_g1.py',scope=__doc__,rom_stat_start=rom_start,limitations=LIMITATIONS,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000'),
        declared_model=dict(spd=SPD,pass_pc=PASS_PC,node_entry='PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd, CCR 0',stops='2ac2 (natural) / 2ac2, 2a00, TRAP and boundary PCs (fixtures)',nat_limit=NAT_LIMIT,fix_limit=GLOBAL['fix_limit'],
            probe='CCR probe: MOVE SR,D0 at 500000 (exact flags; a plain SR read is stale for V / C)',waits='sound 3aea / sprite cda4 declared releases as the scheduler observer',bank_model='observe_animation_machine_pvc_banks.PvcMachine (any PVC selectable bank; bank-read-outside-rom guard)'),
        inputs=dict(contracts={contract_path(u).name:CONTRACT_SHA[u] for u in range(1,8)},scheduler_observation=sha(SCHED_OBS.read_bytes()),
            tools={n:sha((ROOT/'tools'/n).read_bytes()) for n in ('observe_animation_machine_objects_g1.py','observe_animation_machine_scheduler.py','observe_animation_machine_pvc_banks.py','address_map.py','disassemble_program.py')}),
        units=units,
        natural=dict(seeds=len(cases),unit_nodes=len(node_rows),replays=sampled,final_banks=dict(banks),banks_selected_by_pvc_writes_natural=dict(banks_seen),banks_selected_by_pvc_writes_typed=dict(collections.Counter(hx(b) for r in rows for b in r.get('pvc_banks',[]))),nodes_with_pvc_writes=pvc_nodes,guard_explanations=GUARD_TEXT,pieces=pieces,unit_instructions=insns,distinct_unit_instruction_pcs=len(ipcs),total_unit_instructions=sum(counts[u][0] for u in counts),eq={('%s=%s'%k):v for k,v in sorted(eqc.items())},
            model_ok=dict(modelc),sched_exit_eq=dict(sched_exit),final=dict(finalc),guards=dict(guardc),callbacks_hex=S.hexkeys(cb_total),callback_diff_vs_scheduler_artifact=cb_diff,seed_rows=seed_rows,seed_guard_rows=nat_guard_rows,
            xfers=[dict(unit=u,last=hx(l) if l else None,to=hx(t),count=n) for (u,l,t),n in sorted(xf.items(),key=lambda kv:(kv[0][0],kv[0][1] or 0,kv[0][2]))]),
        typed=dict(fixtures=len(rows),ok=len(ok_rows),by_kind=dict(kinds),
            computed_jumps=[dict(name=r['name'],target=hx(r['jump_target']) if r.get('jump_target') is not None else None,final=r['final'],final_detail=r['final_detail'],xfers=[[a,hx(b) if b else None,hx(c)] for a,b,c in r['xfers']]) for r in rows if r['kind']=='computed-jump'],
            carry_consumers=[dict(name=r['name'],block_start=r['targets'],ccr=r['post']['ccr'] if r.get('post') else None,next_blocks=[hx(x) for x in r['leaders_first'][:3]],final=r['final']) for r in rows if r['kind']=='carry-consumer'],
            failure_2986=[dict(name=r['name'],final=r['final'],leaders=[hx(x) for x in r['leaders_first'][:12]]) for r in rows if r['kind']=='28ae-failure'],guards_by_unit_kind={('u%s/%s'%k):v for k,v in sorted(gsum.items(),key=lambda kv:str(kv[0]))},
            search_rounds=fs['rounds'],fallback_entry_self=[hx(x) for x in fs['fallback']]),
        discrepancies=discrep,claims=claims,output_sizes=sizes)
    return report


def dir_sizes(out_dir):
    total=0;files=0;blob=0;nb=0
    for dp,dn,fn in os.walk(out_dir):
        for f in fn:
            s=os.path.getsize(os.path.join(dp,f));total+=s;files+=1
            if os.path.basename(dp)=='blobs':blob+=s;nb+=1
    return dict(total_bytes=total,files=files,blob_bytes=blob,blobs=nb)


def parse_carry_lists(u):
    """The contract's carry classification: FLOW_ONLY (C preserved), known producers (Clear / Set), consumers.  None for a list that is not found."""
    t=contract_path(u).read_text()
    sec=t[t.index('## 구현 범위와 규약'):]
    sec=sec[:sec.index('\n## ',5)] if '\n## ' in sec[5:] else sec
    def toks(s):
        s=re.sub(r'\([^)]*\)','',s)
        return [int(x,16) for x in re.findall(r'`([0-9a-f]{3,6})`',s)]
    out=dict(flow=None,clear=None,set=None,consumers=None)
    m=re.search(r'FLOW_ONLY (\d+)개\*\*[^:]*:(.*?)(?:\. 그 밖|\n)',sec,re.S)
    if m:
        l=toks(m.group(2))
        out['flow']=dict(n=int(m.group(1)),list=l)
    m=re.search(r'known carry 생산 block[^\n]*',sec)
    if m:
        s=re.sub(r'\([^)]*\)','',m.group(0)).split('. ')[0];cl=[];st=[];cur=None
        for tok in re.split(r'(Clear|Set)',s):
            if tok=='Clear':cur=cl
            elif tok=='Set':cur=st
            elif cur is not None:cur.extend(toks(tok.split('(')[0] if False else tok))
        out['clear']=cl;out['set']=st
    m=re.search(r'carry 소비 block (\d+)개\*\*:([^\n]*)',sec)
    if m:out['consumers']=toks(m.group(2))
    return out


def carry_task(arg):
    """Model-only one-block carry experiment at a block start: C_out for C_in 0 / 1 over the captured state and register variants."""
    env=GLOBAL['env'];s,row,cand,seed=arg
    origin=load_state(row);st=apply_cand(origin,cand)
    if st['pc']!=s:
        fl=Flow(env,st,'ref',set(fix_stops(env))|{s},NAT_LIMIT).run()
        if fl.final['kind']!='stop' or fl.final['detail']['pc']!=s:return dict(start=s,cls=None,why='state-at not reached')
        st=fl.states[-1]
    rng=random.Random(seed);u=env.starts[s];obs=[]
    variants=[dict()]+[dict(regs={'d%d'%i:rng.choice((0,1,2,0xff,0x7fff,0x8000,0xffff,rng.getrandbits(32))) for i in range(8)}) for _ in range(5)]
    for var in variants:
        for cin in (0,1):
            regs=dict(st['regs']);regs.update(var.get('regs',{}))
            b=st['bank'];mdl=Model(env.program,st['ram'],regs,s,b[0],b[1],b[2],ccr=cin);first=True;res=None
            for _ in range(2000):
                if not first and (mdl.pc in env.starts or env.unit_of(mdl.pc)!=u):res=(mdl.cc['C'],mdl.pc);break
                first=False
                try:mdl.step()
                except (MGuard,MUnknownFlag,MUnsupported):res=None;break
            if res is not None:obs.append((cin,res[0]))
    if not obs:return dict(start=s,cls=None,why='no completed variant')
    if all(o==i for i,o in obs):cls='preserve'
    elif all(o==0 for i,o in obs):cls='clear'
    elif all(o==1 for i,o in obs):cls='set'
    else:cls='data'
    return dict(start=s,cls=cls,runs=len(obs))


def stage_carry(env,args,fs):
    ctx=multiprocessing.get_context('fork');tasks=[]
    for s,rc in sorted(fs['recipes'].items()):
        if s in env.starts:tasks.append((s,rc['origin'][0],rc['cand'],crc('carry',s)))
    GLOBAL['plan']={}
    with ctx.Pool(args.workers) as pool:res=pool.map(carry_task,tasks,chunksize=4)
    obs={r['start']:r for r in res}
    rep=dict(per_unit={},observed_classes=collections.Counter(r['cls'] for r in res))
    disc=[]
    for u in range(1,8):
        pl=parse_carry_lists(u);starts=env.contracts[u]['starts']
        row=dict(parsed={k:(None if v is None else (len(v['list']) if k=='flow' else len(v))) for k,v in pl.items()},contract_flow_n=pl['flow']['n'] if pl['flow'] else None)
        bad=[]
        if pl['flow']:
            fl=pl['flow']['list']
            if len(fl)!=pl['flow']['n']:bad.append(dict(what='FLOW_ONLY count',stated=pl['flow']['n'],listed=len(fl)))
            for s in fl:
                o=obs.get(s)
                if o and o['cls'] not in ('preserve',):bad.append(dict(what='FLOW_ONLY block does not preserve C',start=hx(s),observed=o['cls']))
        for kind,want in (('clear','clear'),('set','set')):
            for s in pl[kind] or []:
                o=obs.get(s)
                if o and o['cls']!=want:bad.append(dict(what='known %s producer'%kind,start=hx(s),observed=o['cls']))
        if pl['consumers'] is not None:
            mine=[s for s in carry_consumers(env) if env.starts[s]==u and Model(env.program,bytes(65536),{k:0 for k in KEYS},0,0x200000,0,0).decode(s).cond in (2,3,4,5)]
            if sorted(mine)!=sorted(pl['consumers']):bad.append(dict(what='carry consumer blocks (first instruction BCC/BCS/BHI/BLS)',contract=[hx(x) for x in sorted(pl['consumers'])],observed=[hx(x) for x in sorted(mine)]))
        flow_set=set(pl['flow']['list']) if pl['flow'] else set()
        cons_flow=[hx(s) for s in starts if s in obs and obs[s]['cls']=='preserve' and s not in flow_set and s not in (pl['clear'] or []) and s not in (pl['set'] or [])]
        row['observed_preserve_but_unknown_in_contract']=cons_flow
        row['observed']=dict(collections.Counter(str(obs[s]['cls']) for s in starts if s in obs))
        row['unobserved']=[hx(s) for s in starts if s not in obs or obs[s]['cls'] is None]
        row['discrepancies']=bad
        rep['per_unit'][u]=row
        for b in bad:disc.append(dict(id='U%02d-carry'%u,claim='contract carry classification vs model one-block experiment (C_in 0/1 x 6 register variants)',detail=b))
    rep['observed_classes']={str(k):v for k,v in rep['observed_classes'].items()}
    return rep,disc


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(OUT));ap.add_argument('--workers',type=int,default=3);ap.add_argument('--cases',default='')
    ap.add_argument('--budget',type=int,default=8000);ap.add_argument('--natural-only',action='store_true')
    args=ap.parse_args(argv);out_dir=Path(args.out).resolve();t0=time.time()
    rom_start=S.rom_stat();assert rom_start['sha256']==ROM_SHA
    if out_dir.exists() and any(out_dir.iterdir()):raise SystemExit('output directory is not empty: %s'%out_dir)
    (out_dir/'blobs').mkdir(parents=True,exist_ok=True);(out_dir/'seeds').mkdir(exist_ok=True)
    S.setup();S.load_seeds();env=Env()
    GLOBAL.update(env=env,program=S.G['program'],out=out_dir,fix_limit=20_000,plan={},twice=False)
    cases=sorted(S.SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    a_list,b_list,first_start=stage_natural(env,args,out_dir,cases)
    print('natural done',round(time.time()-t0),sum(b['unit_nodes'] for b in b_list),flush=True)
    for b in b_list:
        doc=dict(case=b['case'],kind=b['kind'],family=b['family'],stop=b['stop'],frames_done=b['frames_done'],meta=b['meta'],run_digest=b['run_digest'],nodes=b['nodes'],waits=b['waits'],cb=S.hexkeys(b['cb']),unit_nodes=b['unit_nodes'],ipcs=b['ipcs'],covered=b['covered'])
        S.write_gz(out_dir/'seeds'/('seed_%04d.json.gz'%b['case']),doc)
    if args.natural_only:return a_list,b_list
    fs=stage_fixtures(env,args,b_list,out_dir)
    print('fixture search done',round(time.time()-t0),len(fs['recipes']),'fallback',len(fs['fallback']),flush=True)
    rows,fixtures,gres=stage_verify(env,args,fs,b_list,out_dir)
    print('fixtures done',round(time.time()-t0),len(rows),sum(1 for r in rows if r['ok']),flush=True)
    fx_sha,fx_size=S.write_gz(out_dir/'fixtures.json.gz',dict(note='typed fixtures: declared edits over captured natural states, results of ref / continuous / split (each twice) and the model',fixtures=rows))
    report=build_report(env,args,a_list,b_list,fs,rows,fixtures,gres,out_dir,t0,rom_start)
    carry,cdisc=stage_carry(env,args,fs);report['carry_classification']=carry;report['discrepancies'].extend(cdisc)
    rom_end=S.rom_stat();assert rom_end==rom_start
    report['rom_stat_end']=rom_end;report['fixtures_file']=dict(file='fixtures.json.gz',sha256=fx_sha,size=fx_size)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(units=[(d['unit'],d['blocks_parsed'],d['natural_reached'],d['typed_only_reached'],len(d['unreached'])) for d in report['units']],nodes=report['natural']['unit_nodes'],fixtures=(report['typed']['fixtures'],report['typed']['ok']),
        claims_differ=[c['id'] for c in report['claims'] if c['verdict']=='differs'],discrepancies=len(report['discrepancies']),size_mb=round(report['output_sizes']['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True))
    return summary


if __name__=='__main__':main()
