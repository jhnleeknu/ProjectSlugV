"""F5 frame head e4a/e74 native observation (D1 protocol): H (frame head) + declared controller skip + N (F2 node pass), native Unicorn M68000, original ROM never modified.

Scope: docs/analysis/animation-machine-frame-head-f5-scope.md (main decisions D1..D10).  This tool is an observation, not natural game execution: no BIOS execution, no natural IRQ,
no natural scheduler is claimed; every re-entry and host write is a DECLARED step recorded in the observation.

Frame protocol per seed (frame 0 starts from the RNG-prepared seed state exactly like observe_animation_machine_scheduler_rng.py):
  N0  the F2 pass (PC 2ac2, A6 1008e4, A7 SPd 1ff000) stops directly after the JSR (A0) that enters the frame head callback LONG (100820) (e4a or e74);
  for frame k >= 1:
  H_k   the frame head runs natively from that pass-end state (A6 100820, A7 SPd-4, LONG(SPd-4) = 2ac2) through its RTS to 2ac2; the dispatcher (2ac2..2ac6, 2ab8) loads the next node
        A6 = 1008e4 and the segment stops directly after the JSR (A0) at 2ac0 that transfers to the controller callback LONG (1008e4) (c52a / c66a).  The controller body is never executed;
  skip  declared controller skip: PC := 2ac2, A7 += 4 (the RTS the controller would execute), SR := 2000 (CCR 0, never read; the same declaration normalises the CCR at the H start);
  N_k   the existing F2 pass from that state (A6 is already 1008e4, A7 SPd): identical to the F2/F3/F4 pass of the recorded observers.
Segment stops are accepted only directly after the transferring instruction (checked A6/A7/return LONG).

Declared steps inside H (stop before the instruction, release is a host write, the same segment continues; every one is recorded with its address, live value and released value):
  ef2    vblank wait  (BYTE 100016 < BYTE 100017):   BYTE 100016 := BYTE 100017   (D2; IRQ c8c itself is F6)
  16bd0  sprite flush wait (WORD 108d34 <> D0.W = WORD 108d36): WORD 108d34 := D0.W   (D5)
  3aea   sound ring wait  (existing vocabulary): WORD 104d74 := ffff   (D6)
  72f0 / cda4 / c00468(c376) as in the F2/F4 observers (never reached by the head on natural states; kept for typed fixtures)
External reads (D3/D4): 3c0006 WORD (raster), 300000 / 340000 / 380000 BYTE (inputs) are served from a DECLARED per-frame queue (defaults: raster 0, inputs ff); an empty queue is the
checked stop 'external-read-queue-empty'; the consumed values are recorded in order.  Watchdog 300001, 3c0000/3c0004 and PVC 2ffff0/2 are ordered port events (D7).
Guards (checked stops, state preserved): aux callback f3c (100896 <> 0), menu callback 931a (107df6 <> 0), TRAP #15 at fee, undeclared device read, any BIOS fetch (c00444 / c00450 /
c00468 other than the declared card resume) 'bios-boundary', odd PC / data, unmapped access, the instruction watchdog.

The independent checks, the fresh-CPU split versus continuous comparison (each twice), the full dumps and the typed fixtures are documented in the observation scope text.
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
import struct
import subprocess
import sys
import time
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_BLOCK,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_scheduler_rng as R
import observe_animation_machine_scheduler as S
import observe_animation_machine_pvc_banks as PB

ROOT=S.ROOT
OUT=ROOT/'artifacts/animation_machine_frame_head_native'
SCOPE_DOC=ROOT/'docs/analysis/animation-machine-frame-head-f5-scope.md'
SCOPE_SHA='ea30912'
SCOPE_DOC_SHA='642e2cc5e52db3f27bb532a4fc66d3ce13e990fdf299bf6d07229fe305a00f60'
ROUTING_FILE=ROOT/'engine/src/animation_machine.cpp'
ROUTING_SHA='36cb03c8e257208e0685cdb93a071867920bba256320f2dc2e1612c8ee506da0'
SCHED_TOOL_SHA='62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c'
RNG_TOOL_SHA='659f8636'
PVC_TOOL_SHA='86ebf962'
RNG_OBS=ROOT/'artifacts/animation_machine_scheduler_rng_native/observation.json'
RNG_OBS_SHA='413052978cbf85fa1eedbaaa0ca93bc20b9996c131bba032a6e8db22bc27d6d7'
LEADERS_FILE=ROOT/'docs/analysis/data/animation-machine-frame-head-leaders.json'
LEADERS_SHA='6bda408618578fa6dfc3f62585259dd3321c0b2b03d8d7017bed092dd774a6cf'
M32=0xffffffff
UC_REG=S.UC_REG
sha=S.sha
stable=R.stable
FRAMES=400
H_LIMIT=S.PASS_LIMIT
SPD=S.SPD
CONTROLLER=S.CONTROLLER
FRAME_HEAD=S.FRAME_HEAD
PASS_PC=S.PASS_PC
VISIT_PC=S.VISIT_PC
JSR_PC=0x2ac0
ADDR_VBL_WAIT=0xef2
ADDR_SPR_FLUSH=0x16bd0
ADDR_TRAP=0xfee
ADDR_AUX=0xf3c
ADDR_MENU=0x931a
RASTER_ADDR=0x3c0006
INPUT_ADDRS=(0x300000,0x340000,0x380000)
EXT_ADDRS=INPUT_ADDRS+(RASTER_ADDR,)
EXT_SIZE={0x300000:1,0x340000:1,0x380000:1,0x3c0006:2}
WAIT_KIND=dict(S.WAIT_KIND);WAIT_KIND.update({ADDR_VBL_WAIT:'vblank',ADDR_SPR_FLUSH:'sprite-flush'})
FULL_DUMP_SEEDS=8
NVARIANT_SEEDS=6
FIELDS=((0x10000e,2,'frame counter 10000e'),(0x100012,1,'bios mode copy 100012'),(0x100016,1,'irq count 100016'),(0x100017,1,'irq want 100017'),(0x100018,1,'raster 100018'),(0x10001a,1,'irq snapshot 10001a'),
    (0x10001b,1,'flags 10001b'),(0x104cd4,1,'input mode 104cd4'),(0x10fdae,1,'bios request 10fdae'),(0x10fdaf,1,'bios mode 10fdaf'),(0x107dea,2,'palette wait 107dea'),(0x10fd82,1,'credit 10fd82'),
    (0x108d34,2,'sprite consumer 108d34'),(0x108d36,2,'sprite producer 108d36'),(0x108d3c,1,'sprite dir 108d3c'),(0x10f000,1,'debug 10f000'),(0x100b30,4,'stage controller node cb 100b30'))


# ----------------------------------------------------------------------------------
# Declared external-read scripts (D3 raster, D4 inputs)
# ----------------------------------------------------------------------------------
QLEN=32


def prand(*key):
    h=hashlib.sha256(('F5|'+'|'.join(str(k) for k in key)).encode()).digest();return h


def script_queue(name,case,frame):
    """Per-frame declared external-read queue {address: [values]} (a queue shorter than the consumption is the checked error).  Defaults: raster 0, inputs ff (active-low: nothing pressed)."""
    q={0x3c0006:[0]*QLEN,0x300000:[0xff]*QLEN,0x340000:[0xff]*QLEN,0x380000:[0xff]*QLEN}
    if name=='default':return q
    if name=='empty-raster':q[0x3c0006]=[];return q
    if name=='empty-input':q[0x300000]=[];return q
    if name=='short-raster':q[0x3c0006]=[0];return q
    h=prand(name,case,frame)
    if name=='raster-hi':                      # >= 8000: the clamp (BCC) is not taken; the two reads differ
        a=0x8000+((h[0]<<8|h[1])&0x3fff);b=0x8000+((h[2]<<8|h[3])&0x7fff)
        if frame%5==4:a=(h[0]<<8|h[1])&0x7fff                          # a low first read now and then (clamped branch)
        q[0x3c0006]=[a,b]*(QLEN//2)
    elif name=='raster-mixed':
        q[0x3c0006]=[((h[i%24]<<8|h[i%24+1])&0xffff) for i in range(0,QLEN)]
    elif name=='input-rand':                   # random active-low bytes on every read
        q[0x300000]=[h[i%8] for i in range(0,QLEN)];q[0x340000]=[h[8+i%8] for i in range(0,QLEN)];q[0x380000]=[h[16+i%8] for i in range(0,QLEN)]
    elif name=='input-all':                    # everything pressed
        for a in INPUT_ADDRS:q[a]=[0x00]*QLEN
    elif name=='input-start':                  # start / coin bits of 380000 low on every 3rd frame, P1 direction toggling
        s=0xfe if frame%3==0 else (0xfd if frame%3==1 else 0xff)
        q[0x380000]=[s]*QLEN;q[0x300000]=[0xf7 if frame&1 else 0xef]*QLEN;q[0x340000]=[0xff]*QLEN
    else:raise ValueError(name)
    return q


# ----------------------------------------------------------------------------------
# Independent model: a M68000 integer interpreter written from the 68000 Programmer's Reference Manual instruction formats.  It decodes the ORIGINAL ROM BYTES of every
# instruction the frame head (and the already routed callees it calls) executes, with the complete CCR (X N Z V C), 32-bit register semantics and explicit byte / word / long
# operations.  It shares no code with Unicorn, capstone or the C++.  The only shared data is the PVC bank formula (address_map.pvc_bank_update).  Unknown opcode /
# addressing form = ModelError (counted, never guessed).  The model replays the declared protocol itself: external-read queue, vblank / sprite-flush / sound wait releases,
# controller-entry stop (two instructions after the dispatcher visit at 2abe).
# ----------------------------------------------------------------------------------
from address_map import pvc_bank_update as pvc_formula

MASK={1:0xff,2:0xffff,4:M32}
SIGN={1:0x80,2:0x8000,4:0x80000000}
BITS={1:8,2:16,4:32}


class ModelError(Exception):pass


def sx(v,size):
    v&=MASK[size];return v-(1<<(8*size)) if v&SIGN[size] else v


class M68(object):
    def __init__(self,prog,ram,regs,bank,queue,waits_cfg=True):
        self.prog=prog;self.ram=bytearray(ram);self.d=[regs['d%d'%i]&M32 for i in range(8)];self.a=[regs['a%d'%i]&M32 for i in range(8)]
        self.base,self.ff8,self.ff9=bank;self.page={0x2ffff0:self.ff8,0x2ffff2:self.ff9}
        self.x=self.n=self.z=self.v=self.c=0                      # declared SR 2000: CCR 0
        self.queue={a:list(v) for a,v in queue.items()};self.ext=[];self.ports=[];self.wr=[];self.waits=[];self.steps=0;self.cache={}
    # ---- memory
    def rd(self,a,n):
        a&=M32
        if n>1 and a&1 and a<0x300000:raise ModelError('odd read %x'%a)
        if a<0x100000:return int.from_bytes(self.prog[a:a+n],'big')
        if a<0x200000:
            o=a&0xffff
            if o+n<=0x10000:return int.from_bytes(self.ram[o:o+n],'big')
            return int.from_bytes(bytes((self.ram[(o+i)&0xffff]) for i in range(n)),'big')
        if a<0x2fe000:
            ph=self.base+a-0x200000
            if ph+n>len(self.prog):raise ModelError('bank read outside rom %x'%a)
            return int.from_bytes(self.prog[ph:ph+n],'big')
        if a<0x300000:
            return int.from_bytes(bytes(self.page_byte(a+i) for i in range(n)),'big')
        if a in EXT_SIZE:
            if EXT_SIZE[a]!=n:raise ModelError('external read size %x/%d'%(a,n))
            q=self.queue.get(a)
            if not q:raise ModelError('external-read-queue-empty %x'%a)
            v=q.pop(0)&MASK[n];self.ext.append((a,n,v));return v
        raise ModelError('read %x'%a)
    def page_byte(self,a):
        w=self.page.get(a&~1,0);return (w>>8)&0xff if not a&1 else w&0xff
    def wrt(self,a,n,v):
        a&=M32;v&=MASK[n]
        if n>1 and a&1 and a<0x300000:raise ModelError('odd write %x'%a)
        if 0x100000<=a<0x200000:
            for i,b in enumerate(v.to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
            self.wr.append((a,n,v));return
        if 0x2fe000<=a<0x300000:
            if n!=2 or a not in (0x2ffff0,0x2ffff2):raise ModelError('pvc page write %x/%d'%(a,n))
            self.page[a]=v                                         # the page memory keeps the raw written word; the bank state takes the formula's normalised words
            if a==0x2ffff0:self.ff8=v
            else:self.ff9=v
            self.ports.append((1,a,2,v));self.base,self.ff8,self.ff9=pvc_formula(self.ff8,self.ff9);return
        if 0x300000<=a<0x400000:
            self.ports.append((2,a,n,v));return
        raise ModelError('write %x/%d'%(a,n))
    def fetch(self,a):
        if a&1:raise ModelError('odd pc %x'%a)
        if a>=0x100000:raise ModelError('fetch %x'%a)
        return (self.prog[a]<<8)|self.prog[a+1]
    # ---- ea decode: returns (desc, new_pos)
    def dea(self,mode,reg,size,pos):
        f=self.fetch
        if mode==0:return ('d',reg),pos
        if mode==1:return ('a',reg),pos
        if mode==2:return ('ind',reg),pos
        if mode==3:return ('post',reg),pos
        if mode==4:return ('pre',reg),pos
        if mode==5:return ('disp',reg,sx(f(pos),2)),pos+2
        if mode==6:
            e=f(pos);return ('idx',reg,sx(e,1),(e>>12)&7,(e>>15)&1,(e>>11)&1),pos+2
        if reg==0:return ('abs',sx(f(pos),2)&M32),pos+2
        if reg==1:return ('abs',(f(pos)<<16)|f(pos+2)),pos+4
        if reg==2:return ('abs',(pos+sx(f(pos),2))&M32),pos+2          # (d16,PC): PC = address of the extension word
        if reg==3:
            e=f(pos);return ('absx',(pos+sx(e,1))&M32,(e>>12)&7,(e>>15)&1,(e>>11)&1),pos+2
        if reg==4:
            if size==4:return ('imm',(f(pos)<<16)|f(pos+2)),pos+4
            if size==2:return ('imm',f(pos)),pos+2
            return ('imm',f(pos)&0xff),pos+2
        raise ModelError('ea mode %d reg %d'%(mode,reg))
    def xn(self,idx,isa,islong):
        v=self.a[idx] if isa else self.d[idx]
        return v if islong else sx(v,2)
    def res(self,d,size):
        k=d[0]
        if k=='d':return ('d',d[1])
        if k=='a':return ('a',d[1])
        if k=='imm':return ('i',d[1])
        a=self.a
        if k=='ind':return ('m',a[d[1]])
        if k=='post':
            r=d[1];ad=a[r];a[r]=(ad+(2 if (r==7 and size==1) else size))&M32;return ('m',ad)
        if k=='pre':
            r=d[1];a[r]=(a[r]-(2 if (r==7 and size==1) else size))&M32;return ('m',a[r])
        if k=='disp':return ('m',(a[d[1]]+d[2])&M32)
        if k=='idx':return ('m',(a[d[1]]+d[2]+self.xn(d[3],d[4],d[5]))&M32)
        if k=='abs':return ('m',d[1])
        if k=='absx':return ('m',(d[1]+self.xn(d[2],d[3],d[4]))&M32)
        raise ModelError(k)
    def get(self,loc,size):
        k=loc[0]
        if k=='d':return self.d[loc[1]]&MASK[size]
        if k=='a':return self.a[loc[1]]&MASK[size]
        if k=='i':return loc[1]&MASK[size]
        return self.rd(loc[1],size)
    def put(self,loc,size,v):
        v&=MASK[size];k=loc[0]
        if k=='d':i=loc[1];self.d[i]=(self.d[i]&~MASK[size]&M32)|v;return
        if k=='a':self.a[loc[1]]=sx(v,size)&M32 if size==2 else v;return
        if k=='m':self.wrt(loc[1],size,v);return
        raise ModelError('put '+k)
    # ---- flags
    def logic(self,v,size):
        self.n=1 if v&SIGN[size] else 0;self.z=1 if v==0 else 0;self.v=0;self.c=0
    def add(self,d,s,size,xin=0,keepz=False):
        m=MASK[size];t=(d&m)+(s&m)+xin;r=t&m;self.c=self.x=1 if t>m else 0
        self.v=1 if (~(d^s))&(d^r)&SIGN[size] else 0;self.n=1 if r&SIGN[size] else 0
        self.z=(self.z if r==0 else 0) if keepz else (1 if r==0 else 0);return r
    def sub(self,d,s,size,xin=0,keepz=False,setx=True):
        m=MASK[size];d&=m;s&=m;r=(d-s-xin)&m;c=1 if (s+xin)>d else 0;self.c=c
        if setx:self.x=c
        self.v=1 if (d^s)&(d^r)&SIGN[size] else 0;self.n=1 if r&SIGN[size] else 0
        self.z=(self.z if r==0 else 0) if keepz else (1 if r==0 else 0);return r
    def cond(self,c):
        n,z,v,cc=self.n,self.z,self.v,self.c
        if c==0:return True
        if c==1:return False
        if c==2:return not (cc or z)
        if c==3:return bool(cc or z)
        if c==4:return not cc
        if c==5:return bool(cc)
        if c==6:return not z
        if c==7:return bool(z)
        if c==8:return not v
        if c==9:return bool(v)
        if c==10:return not n
        if c==11:return bool(n)
        if c==12:return n==v
        if c==13:return n!=v
        if c==14:return (not z) and n==v
        return bool(z or n!=v)
    def push(self,v):
        self.a[7]=(self.a[7]-4)&M32;self.wrt(self.a[7],4,v)
    def pop(self):
        v=self.rd(self.a[7],4);self.a[7]=(self.a[7]+4)&M32;return v
    # ---- shifts
    def shift(self,kind,left,v,cnt,size):
        m=MASK[size];bits=BITS[size];v&=m
        if kind==0:                                               # AS
            sv=sx(v,size)
            if left:
                r=(v<<cnt)&m if cnt<64 else 0
                c=((v>>(bits-cnt))&1) if 0<cnt<=bits else 0
                ov=1 if cnt and sx(r,size)!=(sv<<cnt) else 0
            else:
                r=(sv>>min(cnt,bits))&m;c=((sv>>(cnt-1))&1) if 0<cnt<=bits else (1 if (cnt>bits and sv<0) else 0);ov=0
            if cnt==0:c=0;ov=0
            self.n=1 if r&SIGN[size] else 0;self.z=1 if r==0 else 0;self.v=ov;self.c=c
            if cnt:self.x=c
            return r
        if kind==1:                                               # LS
            if left:
                r=(v<<cnt)&m if cnt<=bits else 0;c=((v>>(bits-cnt))&1) if 0<cnt<=bits else 0
            else:
                r=v>>cnt if cnt<=bits else 0;c=((v>>(cnt-1))&1) if 0<cnt<=bits else 0
            self.n=1 if r&SIGN[size] else 0;self.z=1 if r==0 else 0;self.v=0;self.c=c
            if cnt:self.x=c
            return r
        if kind==3:                                               # RO
            k=cnt%bits
            if left:r=((v<<k)|(v>>(bits-k)))&m if k else v;c=(r&1) if cnt else 0
            else:r=((v>>k)|(v<<(bits-k)))&m if k else v;c=(1 if r&SIGN[size] else 0) if cnt else 0
            self.n=1 if r&SIGN[size] else 0;self.z=1 if r==0 else 0;self.v=0;self.c=c
            return r
        # ROX
        k=cnt%(bits+1);x=self.x;wide=(x<<bits)|v;full=(1<<(bits+1))-1
        if left:wide=((wide<<k)|(wide>>(bits+1-k)))&full if k else wide
        else:wide=((wide>>k)|(wide<<(bits+1-k)))&full if k else wide
        r=wide&m;x=(wide>>bits)&1
        self.x=x;self.c=x;self.n=1 if r&SIGN[size] else 0;self.z=1 if r==0 else 0;self.v=0
        return r
    # ---- decode + execute
    def decode(self,pc):
        w=self.fetch(pc);hi=w>>12;pos=pc+2;ins=None
        def ea(mode,reg,size):
            nonlocal pos
            d,pos=self.dea(mode,reg,size,pos);return d
        SZ={0:1,1:2,2:4}
        if hi in (1,2,3):
            size={1:1,3:2,2:4}[hi];src=ea((w>>3)&7,w&7,size);dm=(w>>6)&7;dr=(w>>9)&7
            if dm==1:
                if size==1:raise ModelError('movea.b')
                ins=('movea',size,src,dr)
            else:
                dst=ea(dm,dr,size);ins=('move',size,src,dst)
        elif hi==7:
            if w&0x100:raise ModelError('moveq form')
            ins=('moveq',(w>>9)&7,sx(w&0xff,1))
        elif hi==6:
            c=(w>>8)&15;d8=w&0xff
            if d8==0:disp=sx(self.fetch(pos),2);pos+=2
            elif d8==0xff:raise ModelError('68020 long branch')
            else:disp=sx(d8,1)
            tgt=(pc+2+disp)&M32
            ins=('bra',tgt) if c==0 else (('bsr',tgt) if c==1 else ('bcc',c,tgt))
        elif hi==5:
            if (w&0xc0)==0xc0:
                if ((w>>3)&7)==1:
                    disp=sx(self.fetch(pos),2);pos+=2;ins=('dbcc',(w>>8)&15,w&7,(pc+2+disp)&M32)
                else:
                    dst=ea((w>>3)&7,w&7,1);ins=('scc',(w>>8)&15,dst)
            else:
                size=SZ[(w>>6)&3];dst=ea((w>>3)&7,w&7,size);q=(w>>9)&7 or 8
                ins=('subq' if w&0x100 else 'addq',size,q,dst)
        elif hi==0:
            if w&0x100 or (w&0xf00)==0x800:
                if (w&0x38)==0x8 and w&0x100:raise ModelError('movep')
                typ=(w>>6)&3
                if w&0x100:
                    dst=ea((w>>3)&7,w&7,1);ins=('bit',typ,('dyn',(w>>9)&7),dst)
                else:
                    bn=self.fetch(pos)&0xff;pos+=2;dst=ea((w>>3)&7,w&7,1);ins=('bit',typ,('imm',bn),dst)
            else:
                op=(w>>9)&7;size=SZ[(w>>6)&3] if ((w>>6)&3)!=3 else None
                if size is None:raise ModelError('cmp2/chk2')
                if (w&0x3f)==0x3c:
                    if size!=1 or ((w>>9)&7) not in (0,1,5):raise ModelError('imm to sr')
                    ins=('ccrop',{0:'or',1:'and',5:'eor'}[(w>>9)&7],self.fetch(pos)&0xff);pos+=2
                    return ins,pos-pc
                imm=ea(7,4,size);dst=ea((w>>3)&7,w&7,size)
                names={0:'ori',1:'andi',2:'subi',3:'addi',5:'eori',6:'cmpi'}
                if op not in names:raise ModelError('imm op %d'%op)
                ins=(names[op],size,imm[1],dst)
        elif hi==4:
            if w==0x4e75:ins=('rts',)
            elif (w&0xfff0)==0x4e40:ins=('trap',w&15)
            elif (w&0xfff8)==0x4e50:
                disp=sx(self.fetch(pos),2);pos+=2;ins=('link',w&7,disp)
            elif (w&0xfff8)==0x4e58:ins=('unlk',w&7)
            elif (w&0xffc0)==0x4e80:ins=('jsr',ea((w>>3)&7,w&7,4))
            elif (w&0xffc0)==0x4ec0:ins=('jmp',ea((w>>3)&7,w&7,4))
            elif (w&0xf1c0)==0x41c0:ins=('lea',(w>>9)&7,ea((w>>3)&7,w&7,4))
            elif (w&0xffc0)==0x4840 and ((w>>3)&7)!=0:ins=('pea',ea((w>>3)&7,w&7,4))
            elif (w&0xfff8)==0x4880:ins=('ext',2,w&7)
            elif (w&0xfff8)==0x48c0:ins=('ext',4,w&7)
            elif (w&0xfff8)==0x4840:ins=('swap',w&7)
            elif (w&0xfb80)==0x4880:
                size=4 if w&0x40 else 2;mask=self.fetch(pos);pos+=2;e=ea((w>>3)&7,w&7,size);ins=('movem',(w>>10)&1,size,mask,e)
            elif (w&0xff00) in (0x4000,0x4200,0x4400,0x4600,0x4a00) and (w&0xc0)!=0xc0:
                size=SZ[(w>>6)&3];e=ea((w>>3)&7,w&7,size);ins=({0x4000:'negx',0x4200:'clr',0x4400:'neg',0x4600:'not',0x4a00:'tst'}[w&0xff00],size,e)
            else:raise ModelError('opcode %04x'%w)
        elif hi in (8,0xc):
            om=(w>>6)&7;reg=(w>>9)&7
            if om==3 and hi==8:ins=('divu',reg,ea((w>>3)&7,w&7,2))
            elif om==7 and hi==8:ins=('divs',reg,ea((w>>3)&7,w&7,2))
            elif om==3:ins=('mulu',reg,ea((w>>3)&7,w&7,2))
            elif om==7:ins=('muls',reg,ea((w>>3)&7,w&7,2))
            elif (w&0x1f0)==0x100:raise ModelError('bcd %04x'%w)
            elif hi==0xc and (w&0x130)==0x100:
                m=w&0xf8
                if m==0x40:ins=('exg',0,reg,w&7)
                elif m==0x48:ins=('exg',1,reg,w&7)
                elif m==0x88:ins=('exg',2,reg,w&7)
                else:raise ModelError('exg form')
            else:
                size=SZ[om&3];e=ea((w>>3)&7,w&7,size);ins=('logic','or' if hi==8 else 'and',size,reg,e,bool(om&4))
        elif hi in (9,0xd):
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (3,7):ins=('suba' if hi==9 else 'adda',2 if om==3 else 4,reg,ea((w>>3)&7,w&7,2 if om==3 else 4))
            elif om>=4 and (w&0x30)==0:
                size=SZ[om&3]
                ins=('subx' if hi==9 else 'addx',size,w&7,reg,bool(w&8))
            else:
                size=SZ[om&3];e=ea((w>>3)&7,w&7,size);ins=('arith','sub' if hi==9 else 'add',size,reg,e,bool(om&4))
        elif hi==0xb:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (3,7):ins=('cmpa',2 if om==3 else 4,reg,ea((w>>3)&7,w&7,2 if om==3 else 4))
            elif om<3:size=SZ[om];ins=('cmp',size,reg,ea((w>>3)&7,w&7,size))
            elif ((w>>3)&7)==1:ins=('cmpm',SZ[om&3],w&7,reg)
            else:size=SZ[om&3];ins=('eor',size,reg,ea((w>>3)&7,w&7,size))
        elif hi==0xe:
            if (w&0xc0)==0xc0:
                if w&0x800:raise ModelError('bitfield')
                kind=(w>>9)&3;e=ea((w>>3)&7,w&7,2);ins=('shiftm',kind,bool(w&0x100),e)
            else:
                size=SZ[(w>>6)&3];kind=(w>>3)&3;left=bool(w&0x100);cnt=(w>>9)&7
                ins=('shiftr',kind,left,size,bool(w&0x20),cnt if w&0x20 else (cnt or 8),w&7)
        else:raise ModelError('opcode %04x'%w)
        return ins,pos-pc
    def step(self):
        pc=self.pc;ent=self.cache.get(pc)
        if ent is None:ent=self.decode(pc);self.cache[pc]=ent
        ins,ln=ent;op=ins[0];nxt=(pc+ln)&M32;self.steps+=1
        if op=='move':
            _,size,src,dst=ins;v=self.get(self.res(src,size),size);self.put(self.res(dst,size),size,v);self.logic(v,size)
        elif op=='movea':
            _,size,src,dr=ins;v=self.get(self.res(src,size),size);self.a[dr]=sx(v,size)&M32
        elif op=='moveq':
            _,dr,v=ins;self.d[dr]=v&M32;self.logic(v&M32,4)
        elif op=='lea':
            self.a[ins[1]]=self.res(ins[2],4)[1]
        elif op=='pea':
            self.push(self.res(ins[1],4)[1])
        elif op=='bra':nxt=ins[1]
        elif op=='bsr':self.push(nxt);nxt=ins[1]
        elif op=='bcc':
            if self.cond(ins[1]):nxt=ins[2]
        elif op=='dbcc':
            _,c,r,tgt=ins
            if not self.cond(c):
                cnt=(self.d[r]-1)&0xffff;self.d[r]=(self.d[r]&0xffff0000)|cnt
                if cnt!=0xffff:nxt=tgt
        elif op=='scc':
            _,c,dst=ins;loc=self.res(dst,1);self.put(loc,1,0xff if self.cond(c) else 0)
        elif op=='rts':nxt=self.pop()
        elif op=='jsr':
            t=self.res(ins[1],4)[1];self.push(nxt);nxt=t
        elif op=='jmp':nxt=self.res(ins[1],4)[1]
        elif op=='trap':raise ModelStop('trap',ins[1])
        elif op=='link':
            self.push(self.a[ins[1]]);self.a[ins[1]]=self.a[7];self.a[7]=(self.a[7]+ins[2])&M32
        elif op=='unlk':
            self.a[7]=self.a[ins[1]];self.a[ins[1]]=self.pop()
        elif op in ('addq','subq'):
            _,size,q,dst=ins;loc=self.res(dst,size)
            if loc[0]=='a':
                self.a[loc[1]]=(self.a[loc[1]]+(q if op=='addq' else -q))&M32
            else:
                v=self.get(loc,size);r=self.add(v,q,size) if op=='addq' else self.sub(v,q,size);self.put(loc,size,r)
        elif op=='ccrop':
            ccr=(self.x<<4)|(self.n<<3)|(self.z<<2)|(self.v<<1)|self.c;m=ins[2]
            ccr=(ccr|m) if ins[1]=='or' else ((ccr&m) if ins[1]=='and' else (ccr^m))
            self.x,self.n,self.z,self.v,self.c=(ccr>>4)&1,(ccr>>3)&1,(ccr>>2)&1,(ccr>>1)&1,ccr&1
        elif op in ('ori','andi','eori','addi','subi','cmpi'):
            _,size,imm,dst=ins;loc=self.res(dst,size);v=self.get(loc,size)
            if op=='ori':r=v|imm;self.logic(r&MASK[size],size);self.put(loc,size,r)
            elif op=='andi':r=v&imm;self.logic(r&MASK[size],size);self.put(loc,size,r)
            elif op=='eori':r=v^imm;self.logic(r&MASK[size],size);self.put(loc,size,r)
            elif op=='addi':self.put(loc,size,self.add(v,imm,size))
            elif op=='subi':self.put(loc,size,self.sub(v,imm,size))
            else:self.sub(v,imm,size,setx=False)
        elif op=='bit':
            _,typ,bsrc,dst=ins;bn=(self.d[bsrc[1]] if bsrc[0]=='dyn' else bsrc[1])
            loc=self.res(dst,1)
            if loc[0]=='d':bn&=31;v=self.d[loc[1]]
            else:bn&=7;v=self.get(loc,1)
            self.z=0 if (v>>bn)&1 else 1
            if typ:
                if typ==1:v^=1<<bn
                elif typ==2:v&=~(1<<bn)
                else:v|=1<<bn
                if loc[0]=='d':self.d[loc[1]]=v&M32
                else:self.put(loc,1,v)
        elif op=='clr':
            _,size,dst=ins;self.put(self.res(dst,size),size,0);self.n=0;self.z=1;self.v=0;self.c=0
        elif op=='tst':
            _,size,dst=ins;self.logic(self.get(self.res(dst,size),size),size)
        elif op=='not':
            _,size,dst=ins;loc=self.res(dst,size);r=(~self.get(loc,size))&MASK[size];self.put(loc,size,r);self.logic(r,size)
        elif op=='neg':
            _,size,dst=ins;loc=self.res(dst,size);v=self.get(loc,size);r=self.sub(0,v,size);self.put(loc,size,r)
        elif op=='negx':
            _,size,dst=ins;loc=self.res(dst,size);v=self.get(loc,size);r=self.sub(0,v,size,xin=self.x,keepz=True);self.put(loc,size,r)
        elif op=='ext':
            _,size,r=ins
            if size==2:v=sx(self.d[r],1)&0xffff;self.d[r]=(self.d[r]&0xffff0000)|v;self.logic(v,2)
            else:v=sx(self.d[r],2)&M32;self.d[r]=v;self.logic(v,4)
        elif op=='swap':
            r=ins[1];v=((self.d[r]<<16)|(self.d[r]>>16))&M32;self.d[r]=v;self.logic(v,4)
        elif op=='exg':
            _,k,rx,ry=ins
            if k==0:self.d[rx],self.d[ry]=self.d[ry],self.d[rx]
            elif k==1:self.a[rx],self.a[ry]=self.a[ry],self.a[rx]
            else:self.d[rx],self.a[ry]=self.a[ry],self.d[rx]
        elif op=='movem':
            _,direction,size,mask,e=ins;regs=[('d',i) for i in range(8)]+[('a',i) for i in range(8)]
            if direction==0:                                       # registers to memory
                if e[0]=='pre':
                    r=e[1];ad=self.a[r]
                    for i in range(16):
                        if mask>>i&1:
                            k,n=regs[15-i];ad=(ad-size)&M32
                            val=self.a[n] if k=='a' else self.d[n]
                            if k=='a' and n==r:val=self.a[r]                       # 68000: the initial value is stored
                            self.wrt(ad,size,val&MASK[size])
                    self.a[r]=ad
                else:
                    ad=self.res(e,size)[1]
                    for i in range(16):
                        if mask>>i&1:
                            k,n=regs[i];self.wrt(ad,size,(self.a[n] if k=='a' else self.d[n])&MASK[size]);ad=(ad+size)&M32
            else:
                if e[0]=='post':
                    r=e[1];ad=self.a[r]
                    for i in range(16):
                        if mask>>i&1:
                            k,n=regs[i];v=self.rd(ad,size);ad=(ad+size)&M32
                            v=sx(v,size)&M32 if size==2 else v
                            if k=='a':self.a[n]=v
                            else:self.d[n]=v
                    self.a[r]=ad
                else:
                    ad=self.res(e,size)[1]
                    for i in range(16):
                        if mask>>i&1:
                            k,n=regs[i];v=self.rd(ad,size);ad=(ad+size)&M32
                            v=sx(v,size)&M32 if size==2 else v
                            if k=='a':self.a[n]=v
                            else:self.d[n]=v
        elif op in ('logic','arith'):
            _,kind,size,reg,e,todst=ins;loc=self.res(e,size)
            if todst:                                               # <ea> is the destination (memory)
                dv=self.get(loc,size);sv=self.d[reg]&MASK[size]
                if kind=='or':r=dv|sv;self.logic(r&MASK[size],size)
                elif kind=='and':r=dv&sv;self.logic(r&MASK[size],size)
                elif kind=='add':r=self.add(dv,sv,size)
                else:r=self.sub(dv,sv,size)
                self.put(loc,size,r)
            else:
                sv=self.get(loc,size);dv=self.d[reg]&MASK[size]
                if kind=='or':r=dv|sv;self.logic(r&MASK[size],size)
                elif kind=='and':r=dv&sv;self.logic(r&MASK[size],size)
                elif kind=='add':r=self.add(dv,sv,size)
                else:r=self.sub(dv,sv,size)
                self.put(('d',reg),size,r)
        elif op in ('adda','suba','cmpa'):
            _,size,reg,e=ins;v=sx(self.get(self.res(e,size),size),size)&M32
            if op=='adda':self.a[reg]=(self.a[reg]+v)&M32
            elif op=='suba':self.a[reg]=(self.a[reg]-v)&M32
            else:self.sub(self.a[reg],v,4,setx=False)
        elif op=='cmp':
            _,size,reg,e=ins;v=self.get(self.res(e,size),size);self.sub(self.d[reg],v,size,setx=False)
        elif op=='cmpm':
            _,size,ax,ay=ins;s=self.get(self.res(('post',ax),size),size);d=self.get(self.res(('post',ay),size),size);self.sub(d,s,size,setx=False)
        elif op=='eor':
            _,size,reg,e=ins;loc=self.res(e,size);r=(self.get(loc,size)^self.d[reg])&MASK[size];self.put(loc,size,r);self.logic(r,size)
        elif op in ('addx','subx'):
            _,size,rx,ry,mem=ins
            if mem:
                s=self.get(self.res(('pre',rx),size),size);dl=self.res(('pre',ry),size);d=self.get(dl,size)
            else:
                s=self.d[rx]&MASK[size];dl=('d',ry);d=self.d[ry]&MASK[size]
            r=self.add(d,s,size,xin=self.x,keepz=True) if op=='addx' else self.sub(d,s,size,xin=self.x,keepz=True)
            self.put(dl,size,r)
        elif op in ('mulu','muls'):
            _,reg,e=ins;s=self.get(self.res(e,2),2);dd=self.d[reg]&0xffff
            r=(s*dd) if op=='mulu' else (sx(s,2)*sx(dd,2))
            r&=M32;self.d[reg]=r;self.logic(r,4)
        elif op in ('divu','divs'):
            _,reg,e=ins;s=self.get(self.res(e,2),2);dd=self.d[reg]
            if s==0:raise ModelStop('divide-by-zero',0)
            if op=='divu':q=dd//s;rm=dd%s;ovf=q>0xffff
            else:
                sd=sx(dd,4);ss=sx(s,2);q=abs(sd)//abs(ss);q=-q if (sd<0)!=(ss<0) else q;rm=sd-q*ss;ovf=not (-0x8000<=q<=0x7fff)
            if ovf:self.v=1;self.c=0
            else:
                self.d[reg]=((rm&0xffff)<<16)|(q&0xffff);self.n=1 if q&0x8000 else 0;self.z=1 if (q&0xffff)==0 else 0;self.v=0;self.c=0
        elif op=='shiftr':
            _,kind,left,size,reg_cnt,cnt,r=ins
            if reg_cnt:cnt=self.d[cnt]&63
            out=self.shift(kind,left,self.d[r]&MASK[size],cnt,size)
            self.d[r]=(self.d[r]&~MASK[size]&M32)|out
        elif op=='shiftm':
            _,kind,left,e=ins;loc=self.res(e,2);out=self.shift(kind,left,self.get(loc,2),1,2);self.put(loc,2,out)
        else:raise ModelError('exec '+op)
        self.pc=nxt
    # ---- declared protocol
    def run_head(self,pc,limit=H_LIMIT):
        """Run from the frame head callback to the controller transfer.  Returns (status, info)."""
        self.pc=pc;a6_ctrl=False
        while True:
            pc=self.pc
            if pc==ADDR_VBL_WAIT:
                live=self.rd(0x100016,1);want=self.rd(0x100017,1)
                if live<want:
                    self.waits.append(dict(pc=pc,kind='vblank',live=live,compared=want,released=[[0x100016,1,want]]));self.wrt(0x100016,1,want);self.wr.pop()
            elif pc==ADDR_SPR_FLUSH:
                live=self.rd((self.a[5]+0xd34)&M32,2);want=self.d[0]&0xffff
                if live!=want:
                    self.waits.append(dict(pc=pc,kind='sprite-flush',live=live,compared=want,released=[[0x108d34,2,want]]));self.wrt(0x108d34,2,want);self.wr.pop()
            elif pc==0x3aea:
                live=self.rd((self.a[5]-0x328c)&M32,2);want=self.d[1]&0xffff
                if live==want:
                    self.waits.append(dict(pc=pc,kind='sound',live=live,compared=want,released=[[0x104d74,2,0xffff]]));self.wrt(0x104d74,2,0xffff);self.wr.pop()
            elif pc in (0xcda4,0x47af0,0x478de,ADDR_TRAP,ADDR_AUX,ADDR_MENU):
                if pc==0xcda4:
                    live=self.rd((self.a[5]+0xd34)&M32,2);want=self.d[4]&0xffff
                    if live!=want:
                        self.waits.append(dict(pc=pc,kind='sprite',live=live,compared=want,released=[[0x108d34,2,want]]));self.wrt(0x108d34,2,want);self.wr.pop()
                else:raise ModelStop('guard-pc',pc)
            elif pc==VISIT_PC:
                if self.a[6]!=CONTROLLER:raise ModelStop('head-next-node-not-controller',self.a[6])
                self.step();self.step();return 'controller'
            self.step()
            if self.steps>limit:raise ModelStop('step-limit',self.steps)


class ModelStop(Exception):
    def __init__(self,why,arg):Exception.__init__(self,why);self.why=why;self.arg=arg


def model_head(program,pre_ram,pre_regs,bank,queue,pc):
    """Run the independent model on the H start state.  Returns dict(status, ...)."""
    m=M68(program,pre_ram,pre_regs,bank,queue)
    try:st=m.run_head(pc)
    except ModelStop as e:return dict(status='stop:'+e.why,arg=e.arg,m=m)
    except ModelError as e:return dict(status='error',error=str(e),m=m,pc=m.pc)
    return dict(status=st,m=m)


def compare_head(program,pre_ram,pre_regs,bank,queue,start_pc,hrec,end_state,nports,nwrites,nat_ports,nat_ext,nat_writes):
    """Compare the model with the native H segment (native stop 'controller').  Returns (ok, record)."""
    r=model_head(program,pre_ram,pre_regs,bank,queue,start_pc);m=r['m'];rec=dict(status=r['status'],steps=m.steps)
    if r['status']!='controller':
        rec.update(ok=False,detail={k:v for k,v in r.items() if k!='m'});return rec
    diffs=[]
    regs=end_state['regs']
    for i in range(8):
        if m.d[i]!=regs['d%d'%i]:diffs.append('d%d %x/%x'%(i,m.d[i],regs['d%d'%i]))
        if m.a[i]!=regs['a%d'%i]:diffs.append('a%d %x/%x'%(i,m.a[i],regs['a%d'%i]))
    if m.pc!=end_state['pc']:diffs.append('pc %x/%x'%(m.pc,end_state['pc']))
    if bytes(m.ram)!=end_state['ram']:
        ad=[i for i,(x,y) in enumerate(zip(m.ram,end_state['ram'])) if x!=y];diffs.append('ram %d bytes first %x'%(len(ad),0x100000+ad[0]))
    if m.ports!=nat_ports:diffs.append('ports %d/%d'%(len(m.ports),len(nat_ports)))
    if m.ext!=nat_ext:diffs.append('ext')
    if m.wr!=nat_writes:
        if sorted(m.wr)==sorted(nat_writes):rec['write_order_only']=True
        else:diffs.append('writes %d/%d'%(len(m.wr),len(nat_writes)))
    if (m.base,m.ff8,m.ff9)!=tuple(end_state['bank']):diffs.append('bank')
    mw=[(w['pc'],w['live'],w['compared'],w['released']) for w in m.waits];nw=[(w['pc'],w['live'],w['compared'],[list(x) for x in w['released']]) for w in hrec['waits']]
    if mw!=nw:diffs.append('waits %s/%s'%(mw,nw))
    rec.update(ok=not diffs,detail=diffs,wr=len(m.wr),ports=len(m.ports))
    return rec


# ----------------------------------------------------------------------------------
# One seed run: H + declared skip + N
# ----------------------------------------------------------------------------------
class HeadRun(R.RngRun):
    def __init__(self,*a,**kw):
        self.cfg=kw.pop('cfg');self.tbset=kw.pop('tbset',None);self.keep_all=kw.pop('keep_all',False);self.case=kw.pop('case',0);self.do_model=kw.pop('do_model',False)
        R.RngRun.__init__(self,*a,**kw)
        self.phase='N';self.last_h=None;self.h_ctrl=False;self.h_step=False;self.h_tbs=0;self.queue={};self.ext_log=[];self.skip_bad=0;self.h_stop_count=collections.Counter();self.h_lists={}
        self.tbcount=collections.Counter() if self.tbset is not None else None;self.model_rows=collections.Counter();self.model_bad=[];self.model_log=[];self.wlog=[];self.seen_kinds=set()
    # ---- machine
    def build(self,snap):
        mach=S.SeedRun.build(self,snap);c=mach.cpu
        for base in (0x340000,0x380000):c.mem_map(base,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)      # inputs: mapped like the 300000 page; N-phase reads are stopped by h_ext
        c.hook_add(UC_HOOK_CODE,self.h_vbl,begin=ADDR_VBL_WAIT,end=ADDR_VBL_WAIT);c.hook_add(UC_HOOK_CODE,self.h_sprflush,begin=ADDR_SPR_FLUSH,end=ADDR_SPR_FLUSH)
        c.hook_add(UC_HOOK_CODE,self.h_trapf,begin=ADDR_TRAP,end=ADDR_TRAP);c.hook_add(UC_HOOK_CODE,self.h_aux,begin=ADDR_AUX,end=ADDR_AUX);c.hook_add(UC_HOOK_CODE,self.h_menu,begin=ADDR_MENU,end=ADDR_MENU)
        c.hook_add(UC_HOOK_MEM_READ,self.h_ext,begin=0x300000,end=0x3fffff);c.hook_add(UC_HOOK_MEM_WRITE,self.h_wlog,begin=0x100000,end=0x1fffff)
        return mach
    # ---- hooks (phase aware)
    def h_visit(self,uc,pc,size,user):
        if self.phase=='N':return S.SeedRun.h_visit(self,uc,pc,size,user)
        if self.h_step:return
        a6=uc.reg_read(UC_REG['a6'])
        if a6==CONTROLLER:self.h_ctrl=True;uc.emu_stop()
        else:self.request_stop('head-next-node-not-controller',a6=a6,cb=self.m.long(a6) if RAM_OK(a6) else None)
    def h_head(self,uc,pc,size,user):
        if self.phase=='N':return S.SeedRun.h_head(self,uc,pc,size,user)
    def h_block(self,uc,addr,size,user):
        if self.phase=='N':return S.SeedRun.h_block(self,uc,addr,size,user)
        self.h_tbs+=1
        if self.tbset is not None:
            self.tbset.add((addr,size));self.tbcount[(addr,size)]+=1
        if addr&1 and self.stop is None:self.request_stop('odd-pc',pc=addr)
    def h_vbl(self,uc,pc,size,user):
        if self.phase!='H':return
        live=self.m.byte(0x100016);want=self.m.byte(0x100017)
        if live<want:self.wait_stop(pc,live=live,compared=want)
    def h_sprflush(self,uc,pc,size,user):
        if self.phase!='H':return
        a5=uc.reg_read(UC_REG['a5']);live=self.m.word((a5+0xd34)&M32);want=uc.reg_read(UC_REG['d0'])&0xffff
        if live!=want:self.wait_stop(pc,live=live,compared=want)
    def h_trapf(self,uc,pc,size,user):
        if self.phase=='H':self.request_stop('trap-boundary',pc=pc,head_7e=self.m.word(FRAME_HEAD+0x7e),frame_counter=self.m.word(0x10000e))
    def h_aux(self,uc,pc,size,user):
        if self.phase=='H':self.request_stop('frame-head-aux-callback',pc=pc,callback=self.m.long(FRAME_HEAD+0x76))
    def h_menu(self,uc,pc,size,user):
        if self.phase=='H':self.request_stop('frame-head-menu-callback',pc=pc,callback=uc.reg_read(UC_REG['a0']))
    def h_ext(self,uc,access,address,size,value,user):
        if self.phase!='H':
            if address in (0x340000,0x380000) and self.m.invalid is None:
                self.m.invalid=dict(access='read-unmapped',address=address,size=size,pc=uc.reg_read(UC_REG['pc']));uc.emu_stop()
            return
        if address not in EXT_SIZE:self.request_stop('undeclared-device-read',address=address,size=size);return
        q=self.queue.get(address)
        if size!=EXT_SIZE[address]:self.request_stop('external-read-size',address=address,size=size);return
        if not q:self.request_stop('external-read-queue-empty',address=address,size=size,consumed=len(self.ext_log));return
        v=q.pop(0)&((1<<(8*size))-1);uc.mem_write(address,v.to_bytes(size,'big'));self.ext_log.append((address,size,v))
    def h_wlog(self,uc,access,address,size,value,user):
        if self.phase=='H':self.wlog.append((address,size,value&((1<<(8*size))-1)))
    def wait_stop(self,pc,live,compared):
        self.waiting=dict(pc=pc,kind=WAIT_KIND[pc],live=live,compared=compared);self.m.cpu.emu_stop()
    def release_wait(self,w):
        mach=self.m;pc=w['pc']
        if pc==ADDR_VBL_WAIT:changes=[(0x100016,1,w['compared'])]
        elif pc==ADDR_SPR_FLUSH:changes=[(0x108d34,2,w['compared'])]
        else:return S.SeedRun.release_wait(self,w)
        for a,s,v in changes:mach.put(a,s,v)
        return changes
    # ---- H segment
    def apply_host_writes(self,frame):
        out=[]
        for lo,hi,a,s,v,mode in self.cfg.get('writes',()):
            if lo<=frame<=hi:
                old=int.from_bytes(self.m.read(a,s),'big');mk=(1<<(8*s))-1
                nv={'set':v,'or':old|v,'and':old&v,'xor':old^v}[mode]&mk
                self.m.put(a,s,nv);out.append([a,s,old,nv,mode])
        return out
    def run_head(self,frame):
        mach=self.m;c=mach.cpu
        self.phase='H';self.stop=None;self.waiting=None;self.h_ctrl=False;self.h_step=False;self.h_tbs=0;self.cur=None;self.head_visit=False
        sr=self.cfg.get('script_range');sname=self.cfg.get('script','default') if (sr is None or sr[0]<=frame<=sr[1]) else 'default'
        self.queue={a:list(v) for a,v in script_queue(sname,self.case,frame).items()};self.ext_log=[]
        head_cb=mach.long(FRAME_HEAD);start_digest=mach.digest();hw=self.apply_host_writes(frame)
        pre=mach.ram();pre_regs=mach.regs();pre_bank=(mach.bank,mach.ff8,mach.ff9);pre_pc=mach.pc();pre_queue={a:list(v) for a,v in self.queue.items()};self.wlog=[]
        ports0=len(mach.ports);devr0=len(mach.dev_reads);waits=[];reached=None
        while True:
            mach.fetch_unmapped=None;mach.odd=None;mach.invalid=None;mach.intr=None
            try:c.emu_start(mach.pc(),0xffffff,count=H_LIMIT);ended=True
            except unicorn.UcError as e:ended=False;uc_error=str(e)
            if self.waiting is not None and self.stop is None:
                w=self.waiting;self.waiting=None
                changes=self.release_wait(w);rec=dict(pc=w['pc'],kind=w['kind'],live=w['live'],compared=w['compared'],released=[list(x) for x in changes])
                waits.append(rec);self.waits_total[w['kind']]+=1
                if len(waits)>S.WAIT_LIMIT or not changes:self.stop=dict(reason='wait-not-released',wait=rec);break
                continue
            a7=self.card_wait()
            if a7 is not None:
                saved_a6=mach.long(a7+4)
                c.reg_write(UC_REG['pc'],R.CARD_RET);c.reg_write(UC_REG['a7'],(a7+4)&M32);mach.put(R.CARD_ANSWER,1,self.answer)
                rec=dict(pc=R.CARD_BIOS,kind='bios-card',live=R.CARD_RET,compared=self.answer,released=[['pc',R.CARD_RET],['a7',4],['ram',R.CARD_ANSWER,1,self.answer]],a7_at_stop=a7,saved_a6=saved_a6)
                waits.append(rec);self.waits_total['bios-card']+=1
                if len(waits)>S.WAIT_LIMIT:self.stop=dict(reason='wait-not-released',wait=rec);break
                continue
            if self.h_ctrl and self.stop is None and mach.odd is None and mach.invalid is None:
                # directly after the transferring instruction: MOVEA.L (A6),A0 and JSR (A0) at 2abe / 2ac0 executed as exactly two instructions
                self.h_step=True
                try:c.emu_start(mach.pc(),0xffffff,count=2);ok2=True
                except unicorn.UcError as e:ok2=False;uc_error=str(e)
                self.h_step=False;self.h_ctrl=False
                if ok2 and mach.odd is None and mach.invalid is None and self.stop is None:reached=mach.pc()
                else:ended=ok2
            break
        reason=self.stop
        if reason is None:
            if reached is not None:
                regs=mach.regs();cb=mach.long(CONTROLLER);ok=(regs['a6']==CONTROLLER and regs['a5']==S.A5V and regs['a7']==SPD-4 and mach.long(SPD-4)==PASS_PC and reached==cb and regs['a0']==cb)
                if ok:reason=dict(reason='controller',pc=reached)
                else:reason=dict(reason='controller-entry-check-failed',pc=reached,a6=regs['a6'],a7=regs['a7'],ret=mach.long(regs['a7']))
            elif mach.odd:reason=dict(reason='odd-data-access',**mach.odd)
            elif mach.invalid:reason=dict(reason='invalid-memory-access',**mach.invalid)
            elif mach.fetch_unmapped is not None:
                a=mach.fetch_unmapped
                reason=dict(reason='bios-boundary' if S.BIOS_LO<=a<S.BIOS_LO+0x100000 else 'fetch-unmapped',address=a,odd=bool(a&1),sp=mach.regs()['a7'])
            elif mach.intr:reason=dict(reason='cpu-exception',**mach.intr,odd_pc=bool(mach.intr['pc']&1))
            elif not ended:reason=dict(reason='unicorn-error',error=uc_error,pc=mach.pc())
            else:reason=dict(reason='step-limit',limit=H_LIMIT,pc=mach.pc())
        end_state=mach.state();end_state['pc']=mach.pc()
        ports=mach.ports[ports0:];ext=list(self.ext_log)
        left={('%x'%a):len(v) for a,v in self.queue.items() if v}
        kinds=collections.Counter(('%x/%d'%(e[1],e[2])) if e[0]!=1 else 'pvc/%x'%e[1] for e in ports)
        fields={n:int.from_bytes(end_state['ram'][a&0xffff:(a&0xffff)+s],'big') for a,s,n in FIELDS}
        rec=dict(frame=frame,start=start_digest,head_cb=head_cb,stop=reason['reason'],end=S.state_blob_digest(end_state['ram'],end_state['regs'],end_state['pc'],end_state['bank']),
            ctrl_cb=mach.long(CONTROLLER),tbs=self.h_tbs,ports=len(ports),ports_sha=S.ports_digest(ports),port_kinds=dict(kinds),ext=[list(e) for e in ext],ext_sha=sha(stable(ext).encode())[:16],
            ext_left=left,waits=waits,host_writes=hw,dev_reads=len(mach.dev_reads)-devr0,fields=fields,ram_changed=sum(1 for a,b in zip(pre,end_state['ram']) if a!=b),
            writes=len(self.wlog),writes_sha=sha(stable(self.wlog).encode())[:16])
        return reason,rec,end_state,ports,ext,dict(ram=pre,regs=pre_regs,bank=pre_bank,pc=pre_pc,queue=pre_queue,writes=list(self.wlog))
    # ---- the whole seed
    def run(self):
        snap=self.snap;mach=self.build(snap);frame=0
        self.declared.append(dict(kind='ram-write',address=S.BASE_LONG,size=4,value=SPD,why='declared dispatcher base LONG 104ca4 = SPd (2ab2 MOVE.L A7,104ca4 is never executed in a seed RAM)'))
        self.declared.append(dict(kind='protocol',why='D1: H (frame head to LONG (1008e4) transfer) + controller skip (PC := 2ac2, A7 += 4, SR := 2000, carry Unknown) + N (F2 pass)'))
        self.declared.append(dict(kind='external-reads',script=self.cfg.get('script','default'),why='D3/D4 declared per-frame queues; defaults raster 0, inputs ff; empty queue = checked stop'))
        for w in self.cfg.get('writes',()):self.declared.append(dict(kind='host-write',frames=[w[0],w[1]],address=w[2],size=w[3],value=w[4],mode=w[5],why=self.cfg.get('why','')))
        self.limit=self.frames_limit;buffer={}
        if self.sink is not None:
            if self.prep_dump is not None:self.dump_rows.append(self.dump_state(self.prep_dump,'prep-entry',frame=-2))
            self.dump_rows.append(self.dump_state(mach.state(),'seed-start',frame=-1))
        prev_state=None;self.h_records=[]
        while frame<self.limit:
            self.frame=frame;mach=self.m;c=mach.cpu;hrec=None;hend=None
            if frame>0:
                if self.mode=='split':
                    st=prev_state;st['regs']=dict(st['regs']);mach=self.build(st);c=mach.cpu
                else:c.reg_write(UC_REG['sr'],0x2000)
                hreason,hrec,hend_state,hports,hext,hpre=self.run_head(frame);self.h_records.append(hrec);self.h_stop_count[hreason['reason']]+=1;self.last_h=(hpre,hend_state,hports,hext,hrec)
                new_kind=[w['kind'] for w in hrec['waits'] if ('H',w['kind']) not in self.seen_kinds];self.seen_kinds.update(('H',k) for k in new_kind)
                if hreason['reason']=='controller':
                    if self.do_model:
                        mm=compare_head(self.program,hpre['ram'],hpre['regs'],hpre['bank'],hpre['queue'],hpre['pc'],hrec,hend_state,len(hports),len(hpre['writes']),list(hports),[tuple(e) for e in hext],hpre['writes'])
                        self.model_rows[mm['status'] if mm['status']!='controller' else ('ok' if mm['ok'] else 'mismatch')]+=1;self.model_log.append(dict(frame=frame,status=mm['status'],ok=mm['ok'],steps=mm['steps'],order_only=bool(mm.get('write_order_only'))))
                        if not mm['ok']:self.model_bad.append(dict(frame=frame,case=self.case,detail=mm['detail']))
                    # declared controller skip
                    if self.mode=='split':
                        st=copy.deepcopy(hend_state);st['pc']=PASS_PC;st['regs']['a7']=(st['regs']['a7']+4)&M32
                        mach=self.build(st);c=mach.cpu
                    else:
                        c.reg_write(UC_REG['sr'],0x2000);c.reg_write(UC_REG['pc'],PASS_PC);c.reg_write(UC_REG['a7'],(c.reg_read(UC_REG['a7'])+4)&M32)
                    regs=mach.regs()
                    if regs['a6']!=CONTROLLER or regs['a7']!=SPD:self.skip_bad+=1
                    hrec['skip']=mach.digest(PASS_PC)
                    for a in EXT_ADDRS:                                # normalise the device pages so that continuous and fresh-CPU runs read the same page content in N
                        mach.cpu.mem_write(a,b'\x00'*EXT_SIZE[a])
                else:
                    end_state=hend_state
                    prec=dict(frame=frame,h=hrec,n=None,stop='head:'+hreason['reason'],ctrl_skipped=True)
                    self.pass_records.append(prec);self.digest.update(json.dumps(prec,sort_keys=True,default=str).encode())
                    if self.sink is not None:buffer[frame]=(hend_state,hend_state,True,None)
                    self.stop=dict(hreason,frame=frame,segment='H');break
            self.phase='N'
            reason,walk,start_digest,waits,ports0=self.run_pass()
            end_state=mach.state();partial=None
            if reason['reason']=='frame-head':
                end_state['pc']=reason['pc'];self.end_pcs.append(reason['pc'])
                regs=end_state['regs'];ok=(regs['a6']==S.FRAME_HEAD and regs['a5']==S.A5V and regs['a7']==SPD-4 and mach.long(SPD-4)==PASS_PC and end_state['pc'] in S.HEAD_STOPS and regs['a0']==end_state['pc'])
                if not ok:self.head_bad+=1
            else:
                partial=self.cur
                if partial is not None:self.cur=None;self.finish_node(partial,end_state,True)
            visited=[n['a6'] for n in self.pass_nodes];ws=set(walk);vs=set(visited)
            ports=mach.ports[ports0:]
            cbs=tuple(n['cb'] for n in self.pass_nodes)
            covA=all(n['rec']['rA'] for n in self.pass_nodes)
            nrec=dict(start=start_digest,end=S.state_blob_digest(end_state['ram'],end_state['regs'],end_state['pc'],end_state['bank']),stop=reason['reason'],list_len=len(walk),
                visited=len(visited),walk=walk,nodes=[n['rec'] for n in self.pass_nodes],inserted=[a for a in visited if a not in ws],deleted=[a for a in walk if a not in vs],revisited=len(visited)-len(vs),
                waits=waits,ports=len(ports),ports_sha=S.ports_digest(ports),flags=dict(self.pass_flags),covA=covA,config=sha(repr(cbs).encode())[:16])
            prec=dict(frame=frame,h=hrec,n=nrec,stop=reason['reason'],ctrl_skipped=True)
            self.max_tbs=max(self.max_tbs,sum(n['rec']['tbs'] for n in self.pass_nodes));self.max_nodes=max(self.max_nodes,len(self.pass_nodes))
            self.pass_records.append(prec);self.digest.update(json.dumps(prec,sort_keys=True,default=str).encode())
            first_config=cbs not in self.configs;self.configs.add(cbs)
            if self.sink is not None:
                new_n=[('N',w['kind']) for w in waits if ('N',w['kind']) not in self.seen_kinds];self.seen_kinds.update(new_n)
                first_write=bool(hrec is not None and hrec['host_writes'] and ('W',) not in self.seen_kinds)
                if first_write:self.seen_kinds.add(('W',))
                keep=(frame in (0,1,2,20,21)) or first_config or reason['reason']!='frame-head' or frame+1>=self.limit or bool(new_n) or (hrec is not None and (bool(new_kind) or first_write or frame in self.cfg.get('dump_frames',())))
                if self.full_dump or keep or self.keep_all:
                    buffer[frame]=(hend_state if frame>0 else None,end_state,keep or self.full_dump,(hports,hext) if frame>0 else None)
            self.covered_prefix=self.covered_prefix and covA;prev_state=end_state
            if reason['reason']!='frame-head':
                self.stop=dict(reason,frame=frame);break
            frame+=1
        else:
            self.stop=dict(reason='frame-limit',frame=frame-1,frames=frame)
        self.frames_done=len(self.pass_records);self.fully_covered=self.covered_prefix
        if self.sink is not None:
            for f in sorted(buffer):
                hs,st,keep,lists=buffer[f]
                if hs is not None:self.dump_rows.append(self.dump_state(hs,'head-end',frame=f,full_seed=bool(self.full_dump)))
                if lists is not None and (self.full_dump or keep):self.h_lists[f]=dict(ports=[list(p) for p in lists[0]],ext=[list(e) for e in lists[1]])
                if st is not hs:self.dump_rows.append(self.dump_state(st,'pass-end',frame=f,full_seed=bool(self.full_dump)))
        return self


def RAM_OK(a):return 0x100000<=a<0x200000 and not a&1


# ----------------------------------------------------------------------------------
# Workers
# ----------------------------------------------------------------------------------
G=R.G
FRAMES_CFG=R.FRAMES_CFG


def prepared(case):return R.prepared(case)


def make_run(carried,mode,sink,answer,cfg,case,tbset=None,full_dump=False,prep_dump=None,frames=None,keep_all=False,do_model=False):
    snap={k:v for k,v in carried.items() if k!='prep_entry_state'}
    return HeadRun(G['program'],G['fixed'],G['levels'],snap,mode,frames or cfg.get('frames') or FRAMES_CFG[0],heavy=False,plan=None,sink=sink,extend=False,answer=answer,full_dump=full_dump,prep_dump=prep_dump,cfg=cfg,case=case,tbset=tbset,keep_all=keep_all,do_model=do_model)


def summarize(run,cfg):
    hs=run.h_records
    done=[p for p in run.pass_records if p['n'] is not None]
    return dict(digest=run.digest.hexdigest(),stop=run.stop,frames_done=run.frames_done,frames_complete=sum(1 for p in done if p['stop']=='frame-head'),covered=run.fully_covered,
        card=run.card_waits,waits=dict(run.waits_total),max_tbs=run.max_tbs,max_nodes=run.max_nodes,a7_bad=run.a7_bad,head_bad=run.head_bad,skip_bad=run.skip_bad,
        h_stops=dict(run.h_stop_count),h_tbs=sum(h['tbs'] for h in hs),h_ports=sum(h['ports'] for h in hs),h_ext=sum(len(h['ext']) for h in hs),
        h_head_cbs=dict(collections.Counter('%x'%h['head_cb'] for h in hs)),h_ctrl_cbs=dict(collections.Counter('%x'%h['ctrl_cb'] for h in hs)),
        h_waits=dict(collections.Counter(w['kind'] for h in hs for w in h['waits'])),h_ext_left=sum(1 for h in hs if h['ext_left']),
        port_kinds=dict(sum((collections.Counter(h['port_kinds']) for h in hs),collections.Counter())),ext_patterns=dict(collections.Counter(' '.join('%x/%d'%(e[0],e[1]) for e in h['ext']) for h in hs)),
        fields=field_hist(hs),ram_changed_hist=minmaxavg(h['ram_changed'] for h in hs),ports_hist=minmaxavg(h['ports'] for h in hs),tbs_hist=minmaxavg(h['tbs'] for h in hs),writes_hist=minmaxavg(h['writes'] for h in hs),
        model=dict(run.model_rows),model_bad=run.model_bad[:20],model_steps=sum(m['steps'] for m in run.model_log),
        end_tail=[p['n']['end'] for p in done][-3:],ctrl_idle_first=first_idle(run),
        h_port_max=max([h['ports'] for h in hs] or [0]),h_tbs_max=max([h['tbs'] for h in hs] or [0]),ram_changed_max=max([h['ram_changed'] for h in hs] or [0]),
        )


def first_idle(run):
    for p in run.pass_records:
        h=p['h'] or {}
        f=h.get('fields')
        if f and f['stage controller node cb 100b30']==0x270e:return p['frame']
    return None


def work_a(arg):
    case,answer,cfg=arg
    sd,snap,meta,rec,carried=prepared(case)
    run=make_run(carried,'continuous',None,answer,cfg,case).run()
    out=summarize(run,cfg);out.update(case=case,kind=sd['kind'],family=sd['family'],bank=sd['bank'],cfg=cfg['name'],prep=R.prep_summary(rec),answer=answer)
    return out


def write_h_lists(out_dir,rel,case,run):
    return None


def work_b(arg):
    case,answer,out_dir,rel,full,cfg=arg;out_dir=Path(out_dir)
    sd,snap,meta,rec,carried=prepared(case)
    tbset=set()
    run=make_run(carried,'continuous',{},answer,cfg,case,tbset=tbset,full_dump=full,prep_dump=carried['prep_entry_state'],keep_all=cfg.get('keep_all',False),do_model=True).run()
    for d,b in run.blobs.items():S.write_blob(out_dir,d,b)
    prep_doc=R.prep_summary(rec);prep_doc['writes']=rec['writes'];prep_doc['reads']=rec['reads']
    doc=dict(case=case,kind=sd['kind'],family=sd['family'],meta=meta,cfg=cfg,prep=prep_doc,answer=answer,declared=run.declared+[dict(kind='seed-prep',why='original 49a1a run natively with D0=0 on the seed RAM before pass 0 (F4 decision 1); RAM change only',
        entry=rec['entry_digest'],exit=rec['exit_digest'],ram_diff=rec['ram_diff'])],card_waits=run.card_waits,stop=run.stop,frames_done=run.frames_done,covered=run.fully_covered,frames=run.pass_records,
        head_lists={str(k):v for k,v in sorted(run.h_lists.items())},dumps=run.dump_rows,model_bad=run.model_bad[:50])
    gz_sha,gz_size=R.write_gz(out_dir/rel/('seed_%04d.json.gz'%case),doc)
    r=dict(case=case,digest=run.digest.hexdigest(),file=str(Path(rel)/('seed_%04d.json.gz'%case)),file_sha256=gz_sha,file_size=gz_size,blobs=len(run.blobs),dumps=len(run.dump_rows),
        stop=run.stop,frames_done=run.frames_done,prep_exit=rec['exit_digest'],summary=summarize(run,cfg),**finish_b(run,tbset))
    for tag in ('split1','split2'):
        sr=make_run(carried,'split',None,answer,cfg,case).run();r[tag]=sr.digest.hexdigest();r[tag+'_frames']=sr.frames_done;r[tag+'_stop']=sr.stop
    return r


# ----------------------------------------------------------------------------------
# Static leaders / coverage
# ----------------------------------------------------------------------------------
def load_leaders():
    data=LEADERS_FILE.read_bytes();assert sha(data)==LEADERS_SHA,'leader export changed'
    d=json.loads(data);return d


def unit_of(units,pc):
    for u in units:
        for lo,hi in u['ranges']:
            if lo<=pc<=hi:return u['unit']
    return 'other'


def covered_leaders(tbs,leaders,entries=()):
    """A block leader is covered when it lies inside the byte range of an executed translation block (TB start/size from the block hook).  An `entries` address (a Duff computed-jump entry
    inside a straight-line run) is covered only when a translation block STARTS there (the JMP d(PC,D3.W) transfers control to it)."""
    import bisect
    iv=sorted(set(tbs));out=set();starts=[a for a,s_ in iv];startset=set(starts);ends=[]
    for l in leaders:
        i=bisect.bisect_right(starts,l)-1;steps=0
        while i>=0 and steps<8:
            a,s_=iv[i]
            if a<=l<a+s_:out.add(l);break
            i-=1;steps+=1
    for e in entries:
        if e in startset:out.add(e)
    return out


def dir_sizes(out_dir):return R.dir_sizes(out_dir)


# ----------------------------------------------------------------------------------
# Variants and typed fixtures (declared host writes / scripts on natural seeds)
# ----------------------------------------------------------------------------------
BASE_CFG=dict(name='base',script='default',writes=[])


def variant_cfgs():
    out=[]
    out.append(dict(name='vblank1',script='default',writes=[(1,FRAMES-1,0x100017,1,1,'set')],why='D2: BYTE 100017 := 1 at every H start (declared IRQ want count); ef2 waits once per frame and is released by 100016 := 100017'))
    out.append(dict(name='vblank2',script='default',writes=[(1,FRAMES-1,0x100017,1,2,'set')],why='D2: BYTE 100017 := 2'))
    out.append(dict(name='raster-hi',script='raster-hi',writes=[],why='D3: raster >= 8000 (clamp not taken), two reads differ, an occasional low first read'))
    out.append(dict(name='raster-mixed',script='raster-mixed',writes=[],why='D3: pseudo-random 16-bit raster reads'))
    out.append(dict(name='input-rand',script='input-rand',writes=[],why='D4: pseudo-random active-low input bytes on every read'))
    out.append(dict(name='input-all',script='input-all',writes=[],why='D4: every input bit pressed (00) on every read'))
    out.append(dict(name='input-start',script='input-start',writes=[],why='D4: start/coin bits on 380000 low every 3rd frame, P1 direction toggle'))
    out.append(dict(name='combo',script='input-rand',writes=[(1,FRAMES-1,0x100017,1,1,'set')],why='vblank 1 + random inputs'))
    return out


PATH_PCS=collections.OrderedDict([('first-frame e4a body',0xe4a),('head callback install e6e',0xe6e),('palette frame call e9e',0xe9e),('raster1 eaa',0xeaa),('raster clamp eba',0xeba),('debug check ec4',0xec4),('debug call eda',0xeda),
    ('vblank wait ef2',0xef2),('raster2 efc',0xefc),('irq snapshot f12',0xf12),('input sampler call f24',0xf24),('bios mode call f2a',0xf2a),('aux callback f3c',0xf3c),('aux palette f46',0xf46),('aux signal wait f4c',0xf4c),
    ('pause request f54',0xf54),('pause exit loop f6e',0xf6e),('pause bg 8bbc f8e',0xf8e),('pause back to ec4 fb4',0xfb4),('pause else fbc',0xfbc),('frame counter fe2',0xfe6),('TRAP fee',0xfee),('rts 1000',0x1000),
    ('sprite flush 16bba',0x16bba),('sprite flush wait 16bd0',0x16bd0),('writer select 16be4',0x16be4),('forward path 16bec',0x16bec),('reverse path 16c6a',0x16c6a),('sound flush 3c08',0x3c08),('input mode0 3292',0x3292),
    ('input mode1 334e',0x334e),('input mode>1 3406',0x3406),('menu 9136',0x9136),('menu callback 931a',0x931a),('bg snapshot 1ae56',0x1ae56),('palette 5728',0x5728),('b68',0xb68)])


def path_hits(tbcount):
    items=sorted((a,s_,n) for (a,s_),n in tbcount.items());out={}
    for name,pc in PATH_PCS.items():
        out[name]=sum(n for a,s_,n in items if a<=pc<a+s_)
    return out


def finish_b(run,tbset):
    return dict(tbset=sorted(tbset),path_hits=path_hits(run.tbcount) if run.tbcount is not None else {})


def stop_category(st):
    r=st['reason']
    if r=='head:controller':return r
    return R.stop_category(st)


def routing_from_git(ref):
    rev=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',ref],close_fds=False).decode().strip()
    data=subprocess.check_output(['git','-C',str(ROOT),'show','%s:engine/src/animation_machine.cpp'%ref],close_fds=False)
    return data.decode(),dict(source='git',tree=str(ROOT),ref=ref,commit=rev,sha256=sha(data),length=len(data))


def scope_from_git(ref):
    data=subprocess.check_output(['git','-C',str(ROOT),'show','%s:docs/analysis/animation-machine-frame-head-f5-scope.md'%ref],close_fds=False);return sha(data)


def tool_pins(routing_info):
    pins={}
    for name in ('observe_animation_machine_scheduler.py','observe_animation_machine_scheduler_rng.py','observe_animation_machine_pvc_banks.py','address_map.py','disassemble_program.py'):pins['tools/'+name]=sha((ROOT/'tools'/name).read_bytes())
    for path in (S.F2_CONTRACT,S.F3_CONTRACT,S.SEED_OBS,RNG_OBS,LEADERS_FILE,FIXTURES_FILE):
        try:pins[str(path.relative_to(ROOT))]=sha(path.read_bytes())
        except ValueError:pins[str(path)]=sha(path.read_bytes())
    pins['routing']=routing_info
    return pins


def spread(lst,n):
    if not lst:return []
    if len(lst)<=n:return list(lst)
    return [lst[round(i*(len(lst)-1)/(n-1))] for i in range(n)] if n>1 else [lst[0]]


def hist(vals):
    c=collections.Counter(vals);return {str(k):v for k,v in sorted(c.items(),key=lambda kv:str(kv[0]))}


def minmaxavg(vals):
    vals=list(vals)
    if not vals:return dict(n=0)
    return dict(n=len(vals),min=min(vals),max=max(vals),avg=round(sum(vals)/len(vals),2))


def field_hist(rows):
    out={}
    for h in rows:
        for k,v in h['fields'].items():out.setdefault(k,collections.Counter())[v]+=1
    return {k:dict((('%x'%a),n) for a,n in c.most_common(12)) for k,c in out.items()}


def load_old_seed(case):
    return json.load(gzip.open(R.BASE_OBS.parent.parent/'animation_machine_scheduler_rng_native'/('seeds/seed_%04d.json.gz'%case)))


def work_old(arg):
    """Baseline reproduction: the recorded F4 decision-1 observer (declared model, head and controller skipped) in this process."""
    case,answer=arg
    return dict(case=case,**{k:v for k,v in R.work_a((case,answer)).items() if k in ('digest','stop','frames_done','frames_complete','end_tail')})


def work_run(arg):
    kind,case,answer,out_dir,rel,full,cfg=arg
    if kind=='a':return work_a((case,answer,cfg))
    return work_b((case,answer,out_dir,rel,full,cfg))


BIOS_SITES=((0xc598,0xc00444,'JMP c00444 (SYSTEM_RETURN, controller boot)'),(0xc5a6,0xc00444,'JMP c00444'),(0xc6c8,0xc00444,'JMP c00444'),(0xc7c0,0xc00444,'JMP c00444'),(0xc982,0xc00444,'JMP c00444'),
    (0xc310,0xc00468,'JSR c00468 (card BIOS request; the declared fade_card resume only exists for the call at c376)'),(0x4a98c,0xc00450,'JSR c00450 (BIOS credit request, 4a98c, reached only when 10fd82 <> 0)'))


def bios_sites(case):
    """BIOS boundaries named by the scope (D9): declared PC redirect of the pass-end state to the call site, native execution of the one transferring instruction, stop at the unmapped BIOS fetch.
    The BIOS body is never executed; each probe is run twice on a fresh CPU and must agree."""
    sd,snap,meta,rec,carried=prepared(case)
    base={k:v for k,v in carried.items() if k!='prep_entry_state'};out=[]
    for site,target,text in BIOS_SITES:
        raw=G['program'][site:site+6];ins_ok=raw[:2] in (b'\x4e\xf9',b'\x4e\xb9') and int.from_bytes(raw[2:6],'big')==target
        runs=[]
        for rep in range(2):
            st=copy.deepcopy(base);st['pc']=site;st['regs']['a7']=SPD-4
            mach=S.Machine(G['program'],G['fixed'],st);mach.install_basic_hooks();c=mach.cpu
            err=None
            try:c.emu_start(site,0xffffff,count=8)
            except unicorn.UcError as e:err=str(e)
            a7=c.reg_read(UC_REG['a7']);ret=mach.long(a7) if err is not None and a7>=0x100000 else None
            runs.append(dict(fetch_unmapped=mach.fetch_unmapped,a7=a7,pc=mach.pc(),stack_top=ret,ram=sha(mach.ram()),ports=len(mach.ports),error=err))
        out.append(dict(site=site,target=target,text=text,instruction_matches_rom=ins_ok,expected_stop=target,stop_ok=runs[0]['fetch_unmapped']==target,repeat_equal=runs[0]==runs[1],run=runs[0]))
    return out


def self_tests(case):
    """Negative controls of the independent model: a correct native tuple compares ok; every single perturbation of the native result is reported."""
    sd,snap,meta,rec,carried=prepared(case)
    run=make_run(carried,'continuous',None,R.DEFAULT_ANSWER,dict(BASE_CFG),case,frames=4,do_model=False).run()
    hpre,hend,hports,hext,hrec=run.last_h
    def cmp(end=None,ports=None,ext=None,wr=None,rec_=None):
        return compare_head(G['program'],hpre['ram'],hpre['regs'],hpre['bank'],hpre['queue'],hpre['pc'],rec_ or hrec,end or hend,len(hports),len(hpre['writes']),ports if ports is not None else list(hports),
            ext if ext is not None else [tuple(e) for e in hext],wr if wr is not None else hpre['writes'])
    out=[]
    base=cmp();out.append(dict(name='unperturbed',expected_ok=True,ok=base['ok'],steps=base['steps']))
    e=copy.deepcopy(hend);ram=bytearray(e['ram']);ram[0x1234]^=1;e['ram']=bytes(ram);r=cmp(end=e);out.append(dict(name='one RAM bit flipped',expected_ok=False,ok=r['ok'],detail=r['detail']))
    e=copy.deepcopy(hend);e['regs']['d3']^=1;r=cmp(end=e);out.append(dict(name='D3 bit flipped',expected_ok=False,ok=r['ok'],detail=r['detail']))
    e=copy.deepcopy(hend);e['regs']['a2']^=2;r=cmp(end=e);out.append(dict(name='A2 changed',expected_ok=False,ok=r['ok'],detail=r['detail']))
    e=copy.deepcopy(hend);e['pc']^=2;r=cmp(end=e);out.append(dict(name='PC changed',expected_ok=False,ok=r['ok'],detail=r['detail']))
    p=list(hports);p[len(p)//2]=(p[len(p)//2][0],p[len(p)//2][1],p[len(p)//2][2],p[len(p)//2][3]^1);r=cmp(ports=p);out.append(dict(name='one port value changed',expected_ok=False,ok=r['ok'],detail=r['detail']))
    r=cmp(ports=list(hports)[:-1]);out.append(dict(name='last port dropped',expected_ok=False,ok=r['ok'],detail=r['detail']))
    x=[tuple(e_) for e_ in hext];x[0]=(x[0][0],x[0][1],x[0][2]^1);r=cmp(ext=x);out.append(dict(name='external read value changed',expected_ok=False,ok=r['ok'],detail=r['detail']))
    w=list(hpre['writes']);w[len(w)//2]=(w[len(w)//2][0],w[len(w)//2][1],w[len(w)//2][2]^1);r=cmp(wr=w);out.append(dict(name='one RAM write value changed',expected_ok=False,ok=r['ok'],detail=r['detail']))
    r=cmp(wr=w[:-1]);out.append(dict(name='last RAM write dropped',expected_ok=False,ok=r['ok'],detail=r['detail']))
    h2=copy.deepcopy(hrec);h2['waits']=h2['waits']+[dict(pc=0xef2,live=0,compared=1,released=[[0x100016,1,1]])];r=cmp(rec_=h2);out.append(dict(name='spurious wait record',expected_ok=False,ok=r['ok'],detail=r['detail']))
    q=copy.deepcopy(hpre['queue']);q[0x300000]=[0xff]*0;hp2=dict(hpre);r=compare_head(G['program'],hpre['ram'],hpre['regs'],hpre['bank'],q,hpre['pc'],hrec,hend,len(hports),len(hpre['writes']),list(hports),[tuple(e_) for e_ in hext],hpre['writes'])
    out.append(dict(name='empty input queue (model must stop)',expected_ok=False,ok=r['ok'],status=r['status']))
    return out


def progress(msg,t0):print('[%6.0fs] %s'%(time.time()-t0,msg),file=sys.stderr,flush=True)


def run_main(args,out_dir,t0):
    rom_start=S.rom_stat();assert rom_start['sha256']==S.ROM_SHA
    assert sha((ROOT/'tools/observe_animation_machine_scheduler.py').read_bytes())==SCHED_TOOL_SHA,'scheduler observer changed'
    assert sha((ROOT/'tools/observe_animation_machine_scheduler_rng.py').read_bytes()).startswith(RNG_TOOL_SHA),'rng observer changed'
    assert sha((ROOT/'tools/observe_animation_machine_pvc_banks.py').read_bytes()).startswith(PVC_TOOL_SHA),'pvc observer changed'
    assert sha(RNG_OBS.read_bytes())==RNG_OBS_SHA,'recorded rng observation changed'
    assert scope_from_git(SCOPE_SHA)==SCOPE_DOC_SHA,'scope document at the pinned commit changed'
    if out_dir.exists() and any(out_dir.iterdir()):raise SystemExit('output directory is not empty: %s'%out_dir)
    (out_dir/'blobs').mkdir(parents=True,exist_ok=True);(out_dir/'seeds').mkdir(exist_ok=True)
    text,routing_info=routing_from_git(args.routing_ref)
    if args.routing_ref==SCOPE_SHA:assert routing_info['sha256']==ROUTING_SHA
    R.setup(text);S.load_seeds();pins=tool_pins(routing_info);leaders=load_leaders()
    program=G['program']
    cases=sorted(S.SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    old=json.loads(RNG_OBS.read_text());old_by={r['case']:r for r in old['seeds']}
    ctx=multiprocessing.get_context('fork');base=dict(BASE_CFG)
    sections=collections.OrderedDict()
    with ctx.Pool(args.workers) as pool:
        a_list=pool.map(work_run,[('a',c,R.DEFAULT_ANSWER,None,None,False,base) for c in cases],chunksize=1);a_by={a['case']:a for a in a_list}
        progress('phase A done',t0)
        naturals=[c for c in cases if a_by[c]['kind']=='natural'];full=set(R.pick_full_dump(naturals,a_by))
        b_list=pool.map(work_run,[('b',c,R.DEFAULT_ANSWER,str(out_dir),'seeds',c in full,base) for c in cases],chunksize=1);b_by={b['case']:b for b in b_list}
        progress('phase B done',t0)
        old_list=pool.map(work_old,[(c,R.DEFAULT_ANSWER) for c in cases],chunksize=1);old_run={o['case']:o for o in old_list}
        progress('baseline reproduction done',t0)
        # variants (declared scripts / host writes) on a spread of natural seeds that complete the frame limit
        good=[c for c in naturals if a_by[c]['stop']['reason']=='frame-limit']
        vseeds=spread(good,args.variant_seeds) if not args.no_variants else []
        vcfgs=variant_cfgs();va_jobs=[];vb_jobs=[]
        for cfg in vcfgs:
            for c in vseeds:
                va_jobs.append(('a',c,R.DEFAULT_ANSWER,None,None,False,cfg));vb_jobs.append(('b',c,R.DEFAULT_ANSWER,str(out_dir),'variants/'+cfg['name'],False,cfg))
        va_list=pool.map(work_run,va_jobs,chunksize=1) if va_jobs else [];vb_list=pool.map(work_run,vb_jobs,chunksize=1) if vb_jobs else []
        progress('variants done',t0)
        fx_rows=[]
        if not args.no_fixtures:
            fa_jobs=[];fb_jobs=[]
            for fx in fixture_cfgs(a_by,good):
                fa_jobs.append(('a',fx['case'],R.DEFAULT_ANSWER,None,None,False,fx));fb_jobs.append(('b',fx['case'],R.DEFAULT_ANSWER,str(out_dir),'fixtures/'+fx['name'],False,fx))
            fa_list=pool.map(work_run,fa_jobs,chunksize=1) if fa_jobs else [];fb_list=pool.map(work_run,fb_jobs,chunksize=1) if fb_jobs else []
            fx_rows=fixture_rows(fa_list,fb_list,fixture_cfgs(a_by,good))
    # ---- per seed rows
    seed_rows=[]
    for c in cases:
        a=a_by[c];b=b_by[c];sm=b['summary']
        eq=dict(continuous_twice=a['digest']==b['digest'],split_first=a['digest']==b['split1'],split_second=a['digest']==b['split2'],frames=b['split1_frames']==a['frames_done']==b['frames_done'],
            stop=b['split1_stop']==a['stop']==b['stop'],prep_exit=a['prep']['exit_digest']==b['prep_exit'])
        assert all(eq.values()),(c,eq)
        o=old_by[c];orun=old_run[c]
        base_rep=dict(old_digest_recorded=o['run_digest'],old_digest_here=orun['digest'],digest_equal=o['run_digest']==orun['digest'],pass_end_tail_equal=o['pass_end_tail']==orun['end_tail'],reproduced=o['pass_end_tail']==orun['end_tail'] and o['frames_complete']==orun['frames_complete'],
            old_frames_complete=o['frames_complete'],old_stop=o['stop_category'],note='the recorded run_digest includes the routing coverage flags of the old input worktree; the executed state (last three pass-end state digests, frames) is the comparison')
        seed_rows.append(dict(case=c,kind=a['kind'],family=a['family'],bank=a['bank'],stop=a['stop'],stop_category=stop_category(a['stop']),frames_done=a['frames_done'],frames_complete=a['frames_complete'],
            h_stops=a['h_stops'],h_head_cbs=a['h_head_cbs'],h_ctrl_cbs=a['h_ctrl_cbs'],h_waits=a['h_waits'],h_ext_left=a['h_ext_left'],h_port_max=a['h_port_max'],h_tbs_max=a['h_tbs_max'],ram_changed_max=a['ram_changed_max'],
            model=sm['model'],model_bad=sm['model_bad'],model_steps=sm['model_steps'],ctrl_idle_first=a['ctrl_idle_first'],card=[dict(frame=x['frame'],node=x['node']) for x in a['card']],waits=a['waits'],
            a7_bad=a['a7_bad'],head_bad=a['head_bad'],skip_bad=a['skip_bad'],max_tbs=a['max_tbs'],max_nodes=a['max_nodes'],run_digest=a['digest'],equal=eq,file=b['file'],file_sha256=b['file_sha256'],file_size=b['file_size'],
            dumps=b['dumps'],blobs=b['blobs'],full_dump=c in full,prep=a['prep'],baseline=base_rep,path_hits=b['path_hits'],tb_count=len(b['tbset']),end_tail=a['end_tail']))
    return finish(args,out_dir,t0,rom_start,pins,routing_info,leaders,cases,seed_rows,a_by,b_by,full,vseeds,vcfgs,va_list,vb_list,fx_rows,old_by)




# ----------------------------------------------------------------------------------
# Typed fixtures: declared host writes / scripts on natural seeds
# ----------------------------------------------------------------------------------
def fixture_cfgs(a_by,good):
    return FIXTURES(a_by,good)


def fixture_rows(fa_list,fb_list,cfgs):
    rows=[]
    for a,b,fx in zip(fa_list,fb_list,cfgs):
        eq=dict(continuous_twice=a['digest']==b['digest'],split_first=a['digest']==b['split1'],split_second=a['digest']==b['split2'],frames=b['split1_frames']==a['frames_done']==b['frames_done'],stop=b['split1_stop']==a['stop']==b['stop'])
        sm=b['summary'];ex=fx.get('expect',{});checks={}
        for k,v in ex.items():
            if k=='h_stop':checks[k]=(v in a['h_stops'])
            elif k=='stop_reason':checks[k]=a['stop']['reason']==v
            elif k=='waits':checks[k]=all(a['h_waits'].get(kk,0)>=vv for kk,vv in v.items())
            elif k=='no_model_bad':checks[k]=not sm['model_bad']
            elif k=='model_ok_min':checks[k]=sm['model'].get('ok',0)>=v
            elif k=='pc_hits':checks[k]=all(b['path_hits'].get(kk,0)>=vv for kk,vv in v.items())
            else:raise ValueError(k)
        rows.append(dict(name=fx['name'],case=fx['case'],why=fx.get('why',''),frames=fx.get('frames'),writes=[list(w) for w in fx.get('writes',())],script=fx.get('script','default'),expect=ex,checks=checks,
            ok=all(eq.values()) and all(checks.values()),equal=eq,stop=a['stop'],frames_done=a['frames_done'],frames_complete=a['frames_complete'],h_stops=a['h_stops'],h_waits=a['h_waits'],model=sm['model'],model_bad=sm['model_bad'][:5],
            path_hits={k:v for k,v in b['path_hits'].items() if v},file=b['file'],file_sha256=b['file_sha256'],file_size=b['file_size'],run_digest=a['digest'],tbset=b['tbset']))
    return rows


FIXTURES_FILE=ROOT/'docs/analysis/data/animation-machine-frame-head-fixtures.json'
FIXTURES_SHA='3bbff977498251f89e82c0b1768753d98a2fc918e8f023c7c5986fc832c723e5'


def FIXTURES(a_by,good):
    """Typed fixtures: a hand-written guard / path set on the first full-length natural seed plus the coverage fixtures synthesised by a coverage-guided search (explicit case / frame / writes, replayed here)."""
    out=[];c0=good[0] if good else sorted(a_by)[0];F0=6
    def fx(name,why,writes,script='default',frame=F0,case=None,expect=None,extra=None):
        d=dict(name=name,case=c0 if case is None else case,why=why,frame=frame,frames=frame+2,script=script,script_range=(frame,frame),writes=[(frame,frame,a,s_,v,m) for a,s_,v,m in writes],
            expect=expect or {},dump_frames=(frame-1,frame,frame+1))
        if extra:d.update(extra)
        out.append(d)
    fx('guard-trap-fee','head +7e (WORD 10089e) <> WORD 10000e: TRAP #15 at fee is a checked boundary',[(0x10089e,2,0x1234,'set')],expect={'h_stop':'trap-boundary'})
    fx('guard-aux-callback','aux callback LONG 100896 <> 0: f3c is a checked guard',[(0x100896,4,0x2a00,'set')],expect={'h_stop':'frame-head-aux-callback'})
    fx('guard-queue-empty-raster','declared raster queue empty: checked stop',[],script='empty-raster',expect={'h_stop':'external-read-queue-empty'})
    fx('guard-queue-empty-input','declared 300000 queue empty: checked stop',[],script='empty-input',expect={'h_stop':'external-read-queue-empty'})
    fx('path-raster-short-queue','raster queue of one value: the second read (efc) stops the segment',[],script='short-raster',expect={'h_stop':'external-read-queue-empty'})
    fx('path-debug-3a70','10f000 bit0 and head +84 <> 0: the ec4 debug output call 3a70',[(0x10f000,1,1,'or'),(0x1008a4,1,1,'set')],expect={'h_stop':'controller','pc_hits':{'debug call eda':1}})
    fx('path-sprite-forward','BYTE 108d3c bit7 set: the forward sprite writers',[(0x108d3c,1,0x80,'or')],expect={'h_stop':'controller'})
    fx('path-vblank-wait-1','BYTE 100017 := 1: ef2 vblank wait released by 100016 := 100017',[(0x100017,1,1,'set')],expect={'h_stop':'controller','waits':{'vblank':1}})
    fx('path-vblank-wait-2','BYTE 100017 := 2',[(0x100017,1,2,'set')],expect={'h_stop':'controller','waits':{'vblank':1}})
    fx('path-raster-high','raster >= 8000',[],script='raster-hi',expect={'h_stop':'controller'})
    fx('path-input-all','all inputs pressed',[],script='input-all',expect={'h_stop':'controller'})
    fx('path-input-mode1','BYTE 104cd4 := 1 (replay mode)',[(0x104cd4,1,1,'set')],expect={'h_stop':'controller'})
    fx('path-input-mode2','BYTE 104cd4 := 2',[(0x104cd4,1,2,'set')],expect={'h_stop':'controller'})
    if FIXTURES_FILE.exists():
        data=FIXTURES_FILE.read_bytes();assert sha(data)==FIXTURES_SHA,'fixture file changed'
        for e in json.loads(data)['fixtures']:
            fx(e['name'],e['why'],[tuple(w) for w in e['writes']],script=e['script'],frame=e['frame'],case=e['case'],expect=e.get('expect'))
    return out


GUARD_TEXT={
    'head:controller':'H reached the controller transfer (not a stop)',
    'bios-boundary':'a BIOS address was fetched (c00444 / c00450 / c00468 outside the declared card resume): terminal boundary, the BIOS body is never executed',
    'write-to-program-ROM':'a store to 0..fffff (the RNG pointer / a pointer still outside RAM): the program ROM is write-protected in this observer',
    'odd-data-access':'a WORD/LONG data access at an odd address (the 68000 address error); stopped, not emulated',
    'trap-boundary':'TRAP #15 at fee (head +7e <> WORD 10000e): checked boundary, not executed',
    'external-read-queue-empty':'the declared external-read queue ran out (checked error)',
    'undeclared-device-read':'a read from a device address that has no declared queue',
    'frame-head-aux-callback':'aux callback f3c (100896 <> 0): checked guard',
    'frame-head-menu-callback':'menu callback 931a (107df6 <> 0): checked guard',
    'head-next-node-not-controller':'the dispatcher reached a node other than 1008e4 after the head',
    'step-limit':'the declared instruction watchdog expired',
    'wait-not-released':'a declared wait could not be released',
}


def merge_counter_dicts(items):
    c=collections.Counter()
    for d in items:
        for k,v in d.items():c[k]+=v
    return c


def finish(args,out_dir,t0,rom_start,pins,routing_info,leaders,cases,seed_rows,a_by,b_by,full,vseeds,vcfgs,va_list,vb_list,fx_rows,old_by):
    nat=[r for r in seed_rows if r['kind']=='natural'];gua=[r for r in seed_rows if r['kind']!='natural']
    complete=[r for r in nat if r['stop']['reason']=='frame-limit']
    cat=collections.Counter(r['stop_category'] for r in seed_rows)
    horizon=hist(r['frames_done'] for r in nat)
    inc=[dict(case=r['case'],frames_done=r['frames_done'],stop=r['stop'],category=r['stop_category'],explanation=GUARD_TEXT.get(r['stop_category'],GUARD_TEXT.get(r['stop']['reason'],''))) for r in seed_rows if r['stop']['reason']!='frame-limit']
    # ---- variants
    vrows=[]
    for cfg in vcfgs:
        for c in vseeds:
            a=[x for x in va_list if x['case']==c and x['cfg']==cfg['name']][0];b=[x for x in vb_list if x['case']==c and x['file'].startswith('variants/%s/'%cfg['name'])][0]
            eq=dict(continuous_twice=a['digest']==b['digest'],split_first=a['digest']==b['split1'],split_second=a['digest']==b['split2'],frames=b['split1_frames']==a['frames_done']==b['frames_done'],stop=b['split1_stop']==a['stop']==b['stop'])
            assert all(eq.values()),(cfg['name'],c,eq)
            vrows.append(dict(variant=cfg['name'],case=c,why=cfg.get('why',''),stop=a['stop'],stop_category=stop_category(a['stop']),frames_done=a['frames_done'],frames_complete=a['frames_complete'],h_stops=a['h_stops'],h_waits=a['h_waits'],
                ext_patterns=a['ext_patterns'],ext_left=a['h_ext_left'],model=b['summary']['model'],model_bad=b['summary']['model_bad'][:5],run_digest=a['digest'],equal=eq,differs_from_base=a['digest']!=a_by[c]['digest'],
                file=b['file'],file_sha256=b['file_sha256'],file_size=b['file_size'],path_hits={k:v for k,v in b['path_hits'].items() if v},tb_count=len(b['tbset'])))
    # ---- coverage of the static leaders
    ldr=leaders['leaders'];duff=leaders['duff'];units=leaders['units']
    def tbs_of(rows):
        out=set()
        for b in rows:out.update((a,sz) for a,sz in b['tbset'])
        return out
    nat_tbs=set()
    for r in nat:nat_tbs.update(tuple(x) for x in b_by[r['case']]['tbset'])
    var_tbs=set()
    for b in vb_list:var_tbs.update(tuple(x) for x in b['tbset'])
    fx_tbs=set()
    for f in fx_rows:fx_tbs.update(tuple(x) for x in f['tbset'])
    cov_nat=covered_leaders(nat_tbs,ldr,duff);cov_var=covered_leaders(var_tbs,ldr,duff)-cov_nat;cov_fx=covered_leaders(fx_tbs,ldr,duff)-cov_nat-cov_var
    uncovered=sorted(set(ldr+duff)-cov_nat-cov_var-cov_fx)
    ucount=collections.Counter(unit_of(units,x) for x in uncovered);ltotal=collections.Counter(unit_of(units,x) for x in ldr);dtotal=collections.Counter(unit_of(units,x) for x in duff)
    cnat=collections.Counter(unit_of(units,x) for x in cov_nat if x in set(ldr));cdnat=collections.Counter(unit_of(units,x) for x in cov_nat if x in set(duff))
    covrows={u['unit']:dict(leaders=ltotal.get(u['unit'],0),duff=dtotal.get(u['unit'],0),natural=cnat.get(u['unit'],0),natural_duff=cdnat.get(u['unit'],0),
        variants_new=sum(1 for x in cov_var if unit_of(units,x)==u['unit']),fixtures_new=sum(1 for x in cov_fx if unit_of(units,x)==u['unit']),uncovered=ucount.get(u['unit'],0)) for u in units}
    fx_marg=[]
    seen=set(cov_nat)|set(cov_var)
    for f in fx_rows:
        c=covered_leaders(set(tuple(x) for x in f['tbset']),ldr,duff);new=c-seen;seen|=c
        fx_marg.append(dict(name=f['name'],covered=len(c),new_vs_previous=len(new),new_by_unit=dict(collections.Counter(unit_of(units,x) for x in new))))
    for f in fx_rows:f.pop('tbset')
    # ---- head paths
    ph=collections.Counter();phs=collections.Counter()
    for r in nat:
        for k,v in r['path_hits'].items():
            ph[k]+=v
            if v:phs[k]+=1
    ports_kinds=merge_counter_dicts(a_by[r['case']]['port_kinds'] for r in nat);ext_pat=merge_counter_dicts(a_by[r['case']]['ext_patterns'] for r in nat)
    waits_h=merge_counter_dicts(a_by[r['case']]['h_waits'] for r in nat);ctrl_cb=merge_counter_dicts(a_by[r['case']]['h_ctrl_cbs'] for r in nat);head_cb=merge_counter_dicts(a_by[r['case']]['h_head_cbs'] for r in nat)
    fields=collections.OrderedDict()
    for r in nat:
        for k,d in a_by[r['case']]['fields'].items():
            c=fields.setdefault(k,collections.Counter())
            for v,n in d.items():c[v]+=n
    fields={k:dict(c.most_common(16)) for k,c in fields.items()}
    idle=hist(r['ctrl_idle_first'] for r in nat)
    model_tot=merge_counter_dicts(r['model'] for r in seed_rows)
    model_bad=[m for r in seed_rows for m in r['model_bad']]
    reproduced=sum(1 for r in seed_rows if r['baseline']['reproduced'])
    # frame-0 / frame-1 cross check against the recorded F4 decision-1 observation (8 full-dump seeds)
    cross=[]
    for c in sorted(full):
        old=load_old_seed(c);mine=json.load(gzip.open(out_dir/b_by[c]['file']))
        o0=old['passes'][0];m0=mine['frames'][0];m1=mine['frames'][1] if len(mine['frames'])>1 else None
        cross.append(dict(case=c,frame0_n_end_equal=o0['end']==m0['n']['end'],frame0_n_start_equal=o0['start']==m0['n']['start'],frame1_h_start_equal_old_pass0_end=(m1 is not None and m1['h']['start']==o0['end']),
            frame1_h_start=None if m1 is None else m1['h']['start'],old_pass0_end=o0['end'],old_frames_complete=old_by[c]['frames_complete'],new_frames_complete=a_by[c]['frames_complete']))
    st=self_tests(cases[0] if cases[0] in S.SEEDS else sorted(S.SEEDS)[0]);bios=bios_sites(cases[0] if cases[0] in S.SEEDS else sorted(S.SEEDS)[0])
    rom_end=S.rom_stat();assert rom_end==rom_start,(rom_start,rom_end)
    sizes=dir_sizes(out_dir)
    totals=dict(seeds=len(cases),natural=len(nat),guard_rows=len(gua),n_passes=sum(r['frames_done'] for r in seed_rows),h_segments=sum(sum(r['h_stops'].values()) for r in seed_rows),
        natural_frame_limit_seeds=len(complete),natural_complete_cases=[r['case'] for r in complete],horizon_hist=horizon,stop_categories=dict(cat),incomplete=inc,
        a7_bad=sum(r['a7_bad'] for r in seed_rows),head_bad=sum(r['head_bad'] for r in seed_rows),skip_bad=sum(r['skip_bad'] for r in seed_rows),
        fresh_split_equal_all=all(all(r['equal'].values()) for r in seed_rows),baseline_reproduced=reproduced,baseline_total=len(seed_rows),
        baseline_old_frame_limit=sum(1 for r in nat if r['baseline']['old_stop']=='frame-limit'),
        h_stop_totals=dict(merge_counter_dicts(r['h_stops'] for r in seed_rows)),bios_card_seeds=[r['case'] for r in nat if r['card']],
        model=dict(model_tot),model_mismatches=model_bad[:50],model_steps=sum(r['model_steps'] for r in seed_rows),head_callbacks=dict(head_cb),controller_callbacks_at_transfer=dict(ctrl_cb),
        h_waits=dict(waits_h),port_kinds_per_h_total=dict(ports_kinds),external_read_patterns=dict(ext_pat),stage_controller_idle_first_frame_hist=idle,field_values_at_controller_transfer=fields)
    report=dict(schema_version=1,tool='tools/observe_animation_machine_frame_head.py',scope=SCOPE_TEXT,inputs=pins,rom_stat_start=rom_start,rom_stat_end=rom_end,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library_sha256=sha(Path(S.uclib._name).read_bytes())),
        declared_model=dict(spd=SPD,protocol='D1: H = frame head from e4a/e74 to the JSR (A0) transfer to LONG (1008e4); skip = PC 2ac2, A7 += 4, SR 2000; N = F2 pass',frames=FRAMES_CFG[0],h_limit=H_LIMIT,
            external_reads=dict(raster=dict(address=RASTER_ADDR,size=2,default=0),inputs=dict(addresses=list(INPUT_ADDRS),size=1,default=255),empty_queue='checked stop external-read-queue-empty'),
            waits=dict(vblank='BYTE 100016 < BYTE 100017 at ef2: BYTE 100016 := BYTE 100017',sprite_flush='WORD 108d34 <> D0.W (= WORD 108d36) at 16bd0: WORD 108d34 := D0.W',sound='WORD 104d74 := ffff',
                bios_card='fade_card contract resume (PC c37c, A7 += 4, BYTE 10fdc6)'),seed_prep='49a1a with D0 = 0 (F4 decision 1)'),
        routing=dict(info=routing_info,rules=len(G['names']),routed_pcs=sum(1 for x in G['bm'] if x)),
        totals=totals,seeds=seed_rows,variants=vrows,fixtures=fx_rows,fixture_marginal_coverage=fx_marg,
        head_paths=dict(path_pc_hits_total=dict(ph),path_pc_seeds=dict(phs)),
        leader_coverage=dict(units=covrows,total_leaders=len(ldr),total_duff=len(duff),natural=len(cov_nat),variants_new=len(cov_var),fixtures_new=len(cov_fx),uncovered=len(uncovered),
            uncovered_hex=['%x'%x for x in uncovered],method='a leader is covered when it lies inside the byte range of an executed translation block of an H segment (block hook); variants/fixtures count only when they add'),
        cross_check_recorded_observation=cross,model_self_tests=st,bios_boundary_sites=bios,seed_prep_note='identical preparation to observe_animation_machine_scheduler_rng.py',output_sizes=sizes,limitations=LIMITATIONS)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(seeds=len(cases),natural=len(nat),complete=len(complete),passes=totals['n_passes'],h_segments=totals['h_segments'],stop_categories=dict(cat),model=dict(model_tot),reproduced='%d/%d'%(reproduced,len(seed_rows)),
        variants=len(vrows),fixtures=len(fx_rows),fixtures_ok=sum(1 for f in fx_rows if f['ok']),uncovered=len(uncovered),size_mb=round(sizes['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True))
    return summary


SCOPE_TEXT=('Native Unicorn M68000 observation of the original ROM (F5 scope D1 protocol).  Per frame: H (the frame head e4a/e74 natively to the JSR (A0) that transfers to LONG (1008e4)), a declared '
    'controller skip (PC := 2ac2, A7 += 4, SR := 2000), then N (the F2 pass).  Not natural game execution: no BIOS execution, no natural IRQ, no natural scheduler is claimed; vblank / sprite-flush / sound waits '
    'are declared releases, raster and input reads come from declared queues.  The ROM is never modified; no ROM or extracted data is added to Git.  The 137 stage_entry_body begin outputs (with the F4 decision-1 '
    'RNG preparation) are the natural seeds; the 5 release outputs are guard rows.')
LIMITATIONS=[
    'The controller body (c52a / c66a) is never executed (D1 segment 2 is a declaration); the observation says nothing about controller effects.',
    'Natural seeds carry 100017 = 0, 104cd4 = 0, 100012 = 10fdaf = 0 (seed RAM is a host API product); the vblank wait only appears in the declared variants / fixtures.',
    'External read values are declared (inputs ff, raster 0 by default); real LSPC raster values and real input timing are unconfirmed.',
    'The independent model is an interpreter written from the 68000 programmer reference; it shares only the PVC bank formula (address_map.pvc_bank_update) with the native side.  It covers the head and the routed callees it calls; BCD, bit-field, CHK, MOVEP and 68020 forms are ModelError.',
    'Coverage of the static leader set is by translation-block byte range, not by instruction-level hit counts.',
    'Leaders left uncovered after natural seeds, variants and fixtures are listed in leader_coverage.uncovered_hex.  Facts: the input recorder 349c..3520 (called from 3360 / 3364) is reached only when ROM WORD 000180 <> 0 and that word is 0 in the original ROM, so it is unreachable in this ROM; the pause / menu request 9086..932e (BYTE 100012 = 2 game mode with start edges) and the menu callback guard 931a, the aux callback tail f44..f52 and the TRAP fee are reachable only as guards or through multi-frame input state that the declared single-frame edits did not produce.',
    'The typed coverage fixtures were synthesised by a coverage-guided search of structured host edits on captured natural H-start states (scratch f5obs/explore.py, not part of the deliverable); they are explicit (case, frame, writes, script) in the pinned fixtures file and are replayed here with the same split / continuous / model checks as the natural seeds.  Their RAM edits are not claimed to be reachable game states.',
    'CCR at the H start is declared 0 (SR 2000) in all runs; a head that read the incoming CCR would differ from a model started with CCR 0 only if the native CCR were used (it is not).',
]


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(OUT));ap.add_argument('--workers',type=int,default=3);ap.add_argument('--cases',default='');ap.add_argument('--frames',type=int,default=FRAMES)
    ap.add_argument('--variant-seeds',type=int,default=NVARIANT_SEEDS);ap.add_argument('--no-variants',action='store_true');ap.add_argument('--no-fixtures',action='store_true');ap.add_argument('--routing-ref',default=SCOPE_SHA)
    args=ap.parse_args(argv);out_dir=Path(args.out).resolve();t0=time.time();FRAMES_CFG[0]=args.frames;R.FRAMES_CFG[0]=args.frames
    return run_main(args,out_dir,t0)


if __name__=='__main__':main()
