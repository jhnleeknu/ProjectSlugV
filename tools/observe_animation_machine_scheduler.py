"""Scheduler shell F2 (dispatcher node list 2aac / 2ab8..2ac6, idle callback 270e..271c, fade child 4fcce..4fda6) and stage-event node seeds (F3) native observation.

Native Unicorn M68000 observation of the original ROM (never modified).  The frame pass is a DECLARED MODEL, not natural game execution: no BIOS execution, no natural IRQ,
no natural scheduler is claimed.  The declared model (docs/analysis/animation-machine-scheduler-shell-f2-contract.md, main decisions 2..4):

  * a pass starts at PC = 2ac2 with A6 = 1008e4 (the controller callback "just returned"), A7 = SPd = 1ff000 (the work RAM mirror of 10f000), SR = 2000 (CCR 0, never read)
    and the dispatcher base LONG 104ca4 = SPd written by a declared host write before the first pass;
  * the original dispatcher 2ac2 -> 2ac6 -> 2ab8 -> 2abe -> 2ac0 follows the real node list (children inserted by 28ae and nodes freed by 299c included) and every
    callback runs natively;
  * the pass stops at the first instruction of the frame head callback LONG (100820) (e4a / e74): nothing of the frame head (e74, IRQ poll, raster read ...) and
    nothing of the controller callback (c52a / c66a) is executed; the next pass restarts from the same input form (PC 2ac2, A6 1008e4, A7 SPd, SR 2000) and nothing else is changed;
  * declared waits (stop before the instruction, release is a declared host write, then the same pass continues): 47af0 / 478de palette gate (72f0 BCC loop), 3aea sound ring, cda4 sprite queue.

Inputs (every one pinned by SHA256 and asserted at run time): the ROM, the F2 and F3 contracts, artifacts/stage_entry_body/observation.json (the 137 begin outputs whose final
PC is ff000 are the natural seeds; the 5 release outputs are guard rows only: 100b30 = deadbeef, and the F1b observation found an odd WORD read at fcd83 from 3c60 for them).

Per seed the tool runs four executions of the whole seed: continuous (one persistent CPU, one run per pass) twice and split (a fresh CPU rebuilt from the captured pass-boundary
state for every pass) twice, and compares the full per-node and per-pass state SHAs of all four.  The state SHA covers the 64KiB work RAM, the 16 registers, PC, the modeled
bank, the PVC register words and the ordered port events of the segment.  Per node the tool records the visit order, the entry state (PC 2ab8, A6 = node: the F3 decision 10
node seed form) and the exit state (2ac2), the covered / uncovered classification of the executed translation blocks against the declared executor levels, and for the F2 / F3
callbacks the block-leader hits, computed-PC index values, banked ROM reads and port events.  Every F3 node execution is replayed on a FRESH CPU from its recorded entry state
(stops at e94fe, the F3a/F3b boundary, and at 2ac2) and compared.  An independent Python model of the four F2 blocks (2aac 270e 2716 271a) and the thirteen 4fcce blocks,
decoded from the original ROM bytes (a M68000 subset interpreter that shares no code with Unicorn, capstone or the C++), is compared with the native segments.
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
import struct
import sys
import time
import unicorn
from unicorn import m68k_const as m
from unicorn import UC_HOOK_CODE,UC_HOOK_BLOCK,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_HOOK_INTR,UC_HOOK_MEM_INVALID
from unicorn.unicorn_py3.unicorn import uclib
sys.path.insert(0,str(Path(__file__).resolve().parent))
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_scheduler_native'
ROM_PATH=ROOT/'extracted/program/maincpu.decrypted.be.bin'
ROM_SHA='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
F2_CONTRACT=ROOT/'docs/analysis/animation-machine-scheduler-shell-f2-contract.md'
F2_SHA='6584431718e82293372350b9fa736b2c949e6947e4f989b85aa60079d52f1c1b'
F3_CONTRACT=ROOT/'docs/analysis/animation-machine-stage-event-f3-contract.md'
F3_SHA='bba912176899ab0c21a0b9d54800c5f987f8fdcad9c592b714b8a713d5376c95'
F1A_CONTRACT=ROOT/'docs/analysis/animation-machine-stage-controller-f1-contract.md'
F1B_CONTRACT=ROOT/'docs/analysis/animation-machine-area-clear-f1b-contract.md'
F1C_CONTRACT=ROOT/'docs/analysis/animation-machine-stage-catalog-f1c-contract.md'
SEED_DIR=ROOT/'artifacts/stage_entry_body'
SEED_OBS=SEED_DIR/'observation.json'
SEED_SHA='1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207'
ROUTING_SRC=ROOT/'engine/src/animation_machine.cpp'
IMPORTED_TOOLS=('address_map.py','disassemble_program.py')

M32=0xffffffff
SPD=0x1ff000                                   # declared dispatcher level A7 (work RAM mirror of 10f000, F2 main decision 4)
A5V=0x108000
BASE_LONG=0x104ca4                             # the dispatcher base A7 LONG stored by 2ab2
FRAME_HEAD=0x100820
CONTROLLER=0x1008e4
PASS_PC=0x2ac2
VISIT_PC=0x2abe
HEAD_STOPS=(0xe4a,0xe74)
BIOS_LO=0xc00000
EXTERNAL=0xd00046
RAM_BASE,RAM_SIZE=0x100000,0x10000
BANK_BASE,BANK_SIZE=0x200000,0xfe000
PVC,PVC_SIZE=0x2fe000,0x2000
KEYS=('d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5','a6','a7')
UC_REG={k:getattr(m,'UC_M68K_REG_'+k.upper()) for k in KEYS}
UC_REG['pc']=m.UC_M68K_REG_PC;UC_REG['sr']=m.UC_M68K_REG_SR
FRAMES_BASE=120                                # frames for every seed
FRAMES_FULL=400                                # frames for the seeds whose every pass is covered by the declared executor level A
PASS_LIMIT=6_000_000                           # declared instruction watchdog of one run() (the original has no bound)
WAIT_LIMIT=16                                  # declared waits released inside one pass before the pass is given up
CALLBACK_F3=(0xe9150,0xe9176,0xe9350,0xe9362)
CALLBACK_F2=(0x270e,0x4fcce,0x4fcda)
CALLBACK_IDLE=0x270e
MODEL_CALLBACKS=frozenset((0x270e,0x4fcce,0x4fcda))
F2_LEADERS=(0x2aac,0x270e,0x2716,0x271a,0x4fcce,0x4fcda,0x4fcee,0x4fcfe,0x4fd58,0x4fd5e,0x4fd6a,0x4fd72,0x4fd7c,0x4fd84,0x4fd8c,0x4fd9e,0x4fda4)
F2_INTERNAL=(0x2ab2,0x2712,0x2714,0x2718,0x2710)
F2_RANGES=((0x2aac,0x2ab8),(0x270e,0x271c),(0x4fcce,0x4fd0a),(0x4fd58,0x4fda6))
SHELL_RANGES=((0x2ab8,0x2ac8),(0x2a00,0x2a0a))          # existing fade_card executor: dispatcher loop and self delete
F3_TRAPS_DECL=(0xe93d8,0xe9528,0xe9530,0xe957a,0xe96d4,0xe9702,0xe9780,0xe9788)
F3_INDEX_PCS={0xe91ba:'d7',0xe93f2:'d7',0xe9534:'d0',0xe978c:'d0',0xe97e0:'d1'}
F3_SPLIT_PC=0xe94fe


def sha(b):return hashlib.sha256(b).hexdigest()
def hx(v):return '%x'%v


# ----------------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------------
def load_rom():
    program,manifest=load_verified_program(ROOT)
    assert sha(program)==ROM_SHA and manifest['sha256']==ROM_SHA
    return program


def rom_stat():
    s=ROM_PATH.stat();return dict(sha256=sha(ROM_PATH.read_bytes()),mtime_ns=s.st_mtime_ns,size=s.st_size)


def contract_rows(path,program):
    """Code ranges of the byte tables (`lo..hi` first cell).  A hex cell must equal the ROM bytes; a summary cell must carry the SHA256 of the ROM bytes."""
    rows=[]
    pattern=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (.*) \|$')
    for line in path.read_text().splitlines():
        match=pattern.match(line)
        if not match:continue
        lo,hi=int(match.group(1),16),int(match.group(2),16);cell=match.group(3).strip();data=program[lo:hi]
        if re.fullmatch(r'`[0-9a-f]+`',cell):assert data.hex()==cell.strip('`'),(path.name,hex(lo),hex(hi))
        else:
            hit=re.search(r'SHA256 `([0-9a-f]{64})`',cell)
            if hit:assert sha(data)==hit.group(1),(path.name,hex(lo),hex(hi))
            else:continue                                  # not a byte-table row (a prose table); ignored
        rows.append((lo,hi))
    return rows


def pcs_of(text):return [int(x,16) for x in re.findall(r'`([0-9a-f]{4,6})`',text)]


def f3_contract_lists():
    """F3a (134) and F3b (109) block starts and the 8 TRAP boundaries, from the contract text."""
    lines=F3_CONTRACT.read_text().splitlines()
    lists={}
    for line in lines:
        for key,tag,count in (('F3a','**F3a (134 block 시작)**',134),('F3b','**F3b (109 block 시작 + TRAP 8)**',109)):
            if line.startswith(tag):
                body=line.split('**:',1)[1].strip()
                out=[]
                for token in re.finditer(r'`([0-9a-f]{4,6})`(?:\.\.`([0-9a-f]{4,6})`\((\d+) slot\))?',body):
                    lo=int(token.group(1),16)
                    if token.group(2):
                        hi=int(token.group(2),16);n=int(token.group(3));assert hi-lo==4*(n-1);out.extend(range(lo,hi+1,4))
                    else:out.append(lo)
                assert len(out)==len(set(out))==count,(key,len(out))
                lists[key]=out
    assert set(lists)=={'F3a','F3b'}
    traps=None
    for line in lines:
        hit=re.search(r'TRAP 8\(([^)]*)\)',line)
        if hit:traps=pcs_of(hit.group(1));break
    assert traps==list(F3_TRAPS_DECL),traps
    f3a_rows=[];f3b_rows=[];mode=None
    for line in lines:
        if line=='**F3a**':mode='a'
        elif line=='**F3b**':mode='b'
        elif line=='**공통**':mode=None
        if mode and line.startswith('| `'):
            r=re.match(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \|',line)
            if r:(f3a_rows if mode=='a' else f3b_rows).append((int(r.group(1),16),int(r.group(2),16)))
    return lists['F3a'],lists['F3b'],traps,f3a_rows,f3b_rows


def routing_intervals(path):
    """Executor ranges of animation_machine.cpp routing (the committed main-tree executors): the `next.pc` conditions of the `ok=animation_*` chain as a list of closed intervals."""
    src=path.read_text()
    body=src[src.index('bool ok=false;'):src.index('else return am_error(c,"unsupported animation machine PC")')]
    rules=re.findall(r'if \((.*?)\)ok=(animation_\w+)\(c\);',body,re.S)
    out=[];checks=[]
    for cond,name in rules:
        expr=cond.replace('next.pc','pc').replace('\n',' ')
        terms=[t.strip() for t in expr.split('||')]
        for term in terms:
            term=term.strip()
            while term.startswith('(') and term.endswith(')'):term=term[1:-1].strip()
            lo,hi,excl=0,0xffffffff,[]
            for atom in [a.strip() for a in term.split('&&')]:
                atom=atom.strip('() ')
                mt=re.fullmatch(r'pc\s*(>=|<=|<|>|==|!=)\s*(0x[0-9a-f]+)',atom)
                assert mt,(name,atom)
                op,v=mt.group(1),int(mt.group(2),16)
                if op=='>=':lo=max(lo,v)
                elif op=='>':lo=max(lo,v+1)
                elif op=='<':hi=min(hi,v-1)
                elif op=='<=':hi=min(hi,v)
                elif op=='==':lo=max(lo,v);hi=min(hi,v)
                else:excl.append(v)
            out.append((lo,hi,tuple(excl),name))
        checks.append((compile(expr.replace('&&',' and ').replace('||',' or '),'<rule>','eval'),name))
    return out,checks


def build_levels(program):
    """Bitmaps (index pc>>1 over the fixed 1MiB) of the declared executor levels.
    A = main-tree routing + F1a + F1b + F1c + F2 (4 blocks + 4fcce) + F3a ; B = A + F3b.  Dispatcher shell 2ab8..2ac6 / 2a00 are part of the routing."""
    intervals,checks=routing_intervals(ROUTING_SRC)
    assert len(checks)==31 or len(checks)>20,len(checks)
    base=bytearray(0x80000)
    for lo,hi,excl,name in intervals:
        for pc in range(lo&~1,min(hi,0xfffff)+1,2):
            if pc in excl or pc<lo:continue
            base[pc>>1]=1
    # self check of the interval form against the C++ condition text on a deterministic PC sample
    for pc in list(range(0,0x100000,0x1c6))+[0x2ab8,0x2ac6,0x2ac8,0x2a00,0x2a06,0x2a0a,0x4d7f0,0x38c8,0xa63c,0x47f04]:
        pc&=~1
        want=any(eval(code,{'pc':pc}) for code,name in checks)
        assert bool(base[pc>>1])==want,hex(pc)
    def mark(bm,ranges):
        for lo,hi in ranges:
            for pc in range(lo,hi,2):bm[pc>>1]=1
    f1a=contract_rows(F1A_CONTRACT,program);f1b=contract_rows(F1B_CONTRACT,program);f1c=contract_rows(F1C_CONTRACT,program)
    f3a_starts,f3b_starts,traps,f3a_rows,f3b_rows=f3_contract_lists()
    assert len(f1a)==22 and sum(h-l for l,h in f1a)==5608,(len(f1a),sum(h-l for l,h in f1a))
    levelA=bytearray(base);mark(levelA,f1a);mark(levelA,f1b);mark(levelA,f1c);mark(levelA,F2_RANGES);mark(levelA,f3a_rows)
    levelB=bytearray(levelA);mark(levelB,f3b_rows)
    return dict(A=levelA,B=levelB,routing_pcs=sum(base),f1a=f1a,f1b=f1b,f1c=f1c,f3a_rows=f3a_rows,f3b_rows=f3b_rows,f3a_starts=f3a_starts,f3b_starts=f3b_starts,traps=traps,
        counts=dict(routing_pcs=sum(base),A_pcs=sum(levelA),B_pcs=sum(levelB),f1a_ranges=len(f1a),f1b_ranges=len(f1b),f1c_ranges=len(f1c),f3a_ranges=len(f3a_rows),f3b_ranges=len(f3b_rows)))


# ----------------------------------------------------------------------------------
# Machine: one Unicorn CPU with the modeled memory map (fixed ROM, 64KiB work RAM mirrored 16 times, banked ROM window, PVC page, devices)
# ----------------------------------------------------------------------------------
class Guard(Exception):pass


def state_blob_digest(ram,regs,pc,bank):
    h=hashlib.sha256();h.update(b'MS5-SCHED-STATE-1');h.update(ram);h.update(struct.pack('>16I',*[regs[k] for k in KEYS]))
    h.update(struct.pack('>IIIHH',pc,bank[0],0,bank[1]&0xffff,bank[2]&0xffff));return h.hexdigest()


def ports_digest(events):
    h=hashlib.sha256();h.update(b'MS5-SCHED-PORTS-1')
    for e in events:h.update(struct.pack('>BIBI',e[0],e[1],e[2],e[3]))
    return h.hexdigest()


class Machine(object):
    """Fresh CPU from a declared state: snap = dict(ram=64KiB bytes, regs={d0..a7}, pc, bank=(base,ff8,ff9))."""
    def __init__(self,program,fixed_buffer,snap,hooks=True):
        self.program=program
        self.backing=(ctypes.c_ubyte*RAM_SIZE).from_buffer_copy(snap['ram']);self.addr=ctypes.addressof(self.backing)
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._keep=[self.backing]
        c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        c.mem_map_ptr(0,0x100000,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC,ctypes.addressof(fixed_buffer));c._keep.append(fixed_buffer)
        for i in range(16):c.mem_map_ptr(RAM_BASE+i*RAM_SIZE,RAM_SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        base,ff8,ff9=snap['bank'];self.bank,self.ff8,self.ff9=base,ff8,ff9
        assert base in (0x200000,0x300000),hex(base)
        self.bank_backing=(ctypes.c_ubyte*BANK_SIZE).from_buffer_copy(program[base:base+BANK_SIZE]);c._keep.append(self.bank_backing)
        c.mem_map_ptr(BANK_BASE,BANK_SIZE,unicorn.UC_PROT_READ,ctypes.addressof(self.bank_backing))
        c.mem_map(PVC,PVC_SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        page=bytearray(PVC_SIZE);page[0x1ff0:0x1ff2]=ff8.to_bytes(2,'big');page[0x1ff2:0x1ff4]=ff9.to_bytes(2,'big');c.mem_write(PVC,bytes(page))
        c.mem_map(0x300000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0x3c0000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0xd00000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        self.cpu=c
        c.reg_write(UC_REG['sr'],0x2000)           # declared SR (CCR 0, supervisor): written first, a later SR write could swap A7
        for k in KEYS:c.reg_write(UC_REG[k],snap['regs'][k]&M32)
        c.reg_write(UC_REG['pc'],snap['pc'])
        self.ports=[];self.dev_reads=[];self.odd=None;self.invalid=None;self.intr=None;self.bank_reads=0;self.rom_reads=0;self.fetch_unmapped=None
    def regs(self):
        c=self.cpu;return {k:c.reg_read(UC_REG[k]) for k in KEYS}
    def pc(self):return self.cpu.reg_read(UC_REG['pc'])
    def ram(self):return bytes(self.backing)
    def read(self,address,n):
        o=address&0xffff
        if o+n<=RAM_SIZE:return ctypes.string_at(self.addr+o,n)
        return ctypes.string_at(self.addr+o,RAM_SIZE-o)+ctypes.string_at(self.addr,n-(RAM_SIZE-o))
    def long(self,address):return int.from_bytes(self.read(address,4),'big')
    def word(self,address):return int.from_bytes(self.read(address,2),'big')
    def byte(self,address):return ctypes.string_at(self.addr+(address&0xffff),1)[0]
    def put(self,address,size,value):
        for i,b in enumerate((value&((1<<(8*size))-1)).to_bytes(size,'big')):ctypes.memset(self.addr+((address+i)&0xffff),b,1)
    def state(self):return dict(ram=self.ram(),regs=self.regs(),pc=self.pc(),bank=(self.bank,self.ff8,self.ff9))
    def digest(self,pc=None):
        return state_blob_digest(self.ram(),self.regs(),self.pc() if pc is None else pc,(self.bank,self.ff8,self.ff9))
    def install_basic_hooks(self,odd_check=True,device_events=True):
        """Port events, banked-window reads, odd data access guard, unmapped access, unmapped fetch (BIOS boundary), exceptions."""
        c=self.cpu;mach=self
        def mem_read(uc,access,address,size,value,user):
            if size>1 and address&1 and address<0x300000:
                mach.odd=dict(access='read',address=address,size=size,pc=uc.reg_read(UC_REG['pc']));uc.emu_stop();return
            if address>=BANK_BASE:
                if address<PVC:mach.bank_reads+=1
                elif address>=0x300000:mach.dev_reads.append((address,size))
            elif address<0x100000:mach.rom_reads+=1
        def mem_write(uc,access,address,size,value,user):
            if size>1 and address&1 and address<0x300000:
                mach.odd=dict(access='write',address=address,size=size,pc=uc.reg_read(UC_REG['pc']),old=bytes(uc.mem_read(address,size)).hex());uc.emu_stop();return
            if address<0x200000:return
            if PVC<=address<0x300000:
                if size!=2 or address not in (0x2ffff0,0x2ffff2):
                    mach.invalid=dict(access='write',address=address,size=size,kind='pvc-page');uc.emu_stop();return
                v=value&0xffff
                if address==0x2ffff0:mach.ff8=v
                else:mach.ff9=v
                mach.ports.append((1,address,2,v))
                base,mach.ff8,mach.ff9=pvc_bank_update(mach.ff8,mach.ff9);mach.bank=base
                if base not in (0x200000,0x300000):
                    mach.invalid=dict(access='write',address=address,size=size,kind='bank',bank=base);uc.emu_stop();return
                ctypes.memmove(ctypes.addressof(mach.bank_backing),mach.program[base:base+BANK_SIZE],BANK_SIZE)
            else:mach.ports.append((2,address,size,value&((1<<(8*size))-1)))
        def mem_bad(uc,access,address,size,value,user):
            if access==unicorn.UC_MEM_FETCH_UNMAPPED:mach.fetch_unmapped=address
            else:mach.invalid=dict(access={unicorn.UC_MEM_READ_UNMAPPED:'read-unmapped',unicorn.UC_MEM_WRITE_UNMAPPED:'write-unmapped',unicorn.UC_MEM_WRITE_PROT:'write-protected',
                unicorn.UC_MEM_READ_PROT:'read-protected',unicorn.UC_MEM_FETCH_PROT:'fetch-protected'}.get(access,'access-%d'%access),address=address,size=size,pc=uc.reg_read(UC_REG['pc']))
            return False
        def intr(uc,number,user):mach.intr=dict(number=number,pc=uc.reg_read(UC_REG['pc']));uc.emu_stop()
        c.hook_add(UC_HOOK_MEM_READ,mem_read,begin=0,end=0x3fffff)
        c.hook_add(UC_HOOK_MEM_READ,mem_read,begin=0xd00000,end=0xd00fff)
        c.hook_add(UC_HOOK_MEM_WRITE,mem_write,begin=0x100000,end=0x3fffff)
        c.hook_add(UC_HOOK_MEM_WRITE,mem_write,begin=0xd00000,end=0xd00fff)
        c.hook_add(UC_HOOK_MEM_INVALID,mem_bad)
        c.hook_add(UC_HOOK_INTR,intr)


# ----------------------------------------------------------------------------------
# Frame pass observation of one seed
# ----------------------------------------------------------------------------------
LEAD_RANGES=((0x270e,0x271c),(0x2aac,0x2ab8),(0x4fcce,0x4fda6),(0xe9150,0xe98ee),(0x48502,0x4855c),(0x1a910,0x1a91a),(0x1a92c,0x1a952),(0x288c,0x289e),(0x49a84,0x49a8e))
GATES={0x47af0:(0x47af6,0x47af8),0x478de:(0x478e4,0x478e6)}      # gate PC -> (BCC PC, fall-out PC) of the 72f0 palette gate loops
WAIT_KIND={0xcda4:'sprite',0x3aea:'sound',0x47af0:'palette-gate',0x478de:'palette-gate'}
TB_CACHE={}


class PassStop(Exception):pass


class SeedRun(object):
    """One execution of one seed (mode 'continuous': one persistent CPU; mode 'split': a fresh CPU per pass rebuilt from the captured pass-boundary state)."""
    def __init__(self,program,fixed,levels,snap0,mode,frames,heavy=False,plan=None,sink=None,label='',extend=True,start_declared=True,check_head=True):
        self.program=program;self.fixed=fixed;self.levels=levels;self.mode=mode;self.frames_limit=frames;self.heavy=heavy;self.plan=plan or {};self.sink=sink
        self.label=label;self.extend=extend;self.check_head=check_head;self.snap=copy.deepcopy(snap0);self.m=None
        self.pass_records=[];self.stop=None;self.cur=None;self.pass_nodes=None;self.blobs={};self.digest=hashlib.sha256()
        self.leader_hits=collections.Counter();self.index_hits=collections.defaultdict(collections.Counter);self.cb_counts=collections.Counter();self.a7_bad=0;self.head_bad=0
        self.f3_records=[];self.model_rows=[];self.model_mismatch=[];self.waits_total=collections.Counter();self.trap_hits=collections.Counter();self.uncovered=collections.Counter()
        self.frame=0;self.covered_prefix=True;self.pending_dumps=[];self.configs=set();self.dump_rows=[];self.declared=[];self.traced_count=collections.Counter();self.model_count=collections.Counter();self.cb120=collections.Counter();self.idle120=collections.Counter();self.leader120=collections.Counter();self.index120=collections.defaultdict(collections.Counter);self.max_tbs=0;self.max_nodes=0;self.end_pcs=[];self.covered0=True;self.capture_frames=set();self.captured={};self.capture_nodes=set();self.captured_nodes={};self.pass_limit=PASS_LIMIT;self.declare_base=True;self.frame0_cbs=[]
    # ---- hooks
    def build(self,snap):
        mach=Machine(self.program,self.fixed,snap);mach.install_basic_hooks();self.m=mach;c=mach.cpu;me=self
        c.hook_add(UC_HOOK_CODE,self.h_visit,begin=VISIT_PC,end=VISIT_PC)
        c.hook_add(UC_HOOK_CODE,self.h_ret,begin=PASS_PC,end=PASS_PC)
        c.hook_add(UC_HOOK_CODE,self.h_head,begin=HEAD_STOPS[0],end=HEAD_STOPS[0])
        c.hook_add(UC_HOOK_CODE,self.h_head,begin=HEAD_STOPS[1],end=HEAD_STOPS[1])
        c.hook_add(UC_HOOK_CODE,self.h_2a00,begin=0x2a00,end=0x2a00)
        for lo,hi in LEAD_RANGES:c.hook_add(UC_HOOK_CODE,self.h_lead,begin=lo,end=hi-1)
        c.hook_add(UC_HOOK_BLOCK,self.h_block)
        for gate,(bcc,out) in GATES.items():
            c.hook_add(UC_HOOK_CODE,self.h_gate_loop,begin=bcc,end=bcc);c.hook_add(UC_HOOK_CODE,self.h_gate_out,begin=out,end=out);c.hook_add(UC_HOOK_CODE,self.h_gate,begin=gate,end=gate)
        c.hook_add(UC_HOOK_CODE,self.h_sound,begin=0x3aea,end=0x3aea)
        c.hook_add(UC_HOOK_CODE,self.h_sprite,begin=0xcda4,end=0xcda4)
        self.gate_flag=False
        return mach
    def request_stop(self,reason,**detail):
        self.stop=dict(reason=reason,**detail);self.m.cpu.emu_stop()
    def h_visit(self,uc,pc,size,user):
        mach=self.m;a6=uc.reg_read(UC_REG['a6']);cb=mach.long(a6)
        if uc.reg_read(UC_REG['a7'])!=SPD or mach.long(BASE_LONG)!=SPD:self.a7_bad+=1;self.pass_flags['a7_bad']+=1
        if a6==FRAME_HEAD:
            if cb in HEAD_STOPS:self.head_visit=True;return
            if self.check_head:self.request_stop('frame-head-callback-rejected',callback=cb);return
        if a6==CONTROLLER:self.request_stop('controller-node-visited',callback=cb);return
        node=dict(seq=len(self.pass_nodes),a6=a6,cb=cb,depth=mach.word(a6+0x10),entry_ram=mach.ram(),entry_regs=mach.regs(),entry_bank=(mach.bank,mach.ff8,mach.ff9),tbs=0,
            ports0=len(mach.ports),bank_reads0=mach.bank_reads,rom_reads0=mach.rom_reads,dev0=len(mach.dev_reads),leaders=collections.Counter(),idx=[],via2a00=None,waits=[])
        node['entry_regs']['a5']=A5V
        self.cur=node
    def h_ret(self,uc,pc,size,user):
        node=self.cur
        if node is None:return
        self.cur=None;st=self.m.state();st['pc']=pc;self.finish_node(node,st,False)
    def h_2a00(self,uc,pc,size,user):
        node=self.cur
        if node is not None and node['cb'] in MODEL_CALLBACKS and node['via2a00'] is None:
            st=self.m.state();st['pc']=pc;st['ports']=len(self.m.ports)-node['ports0'];node['via2a00']=st
        elif node is not None and node['via2a00'] is None:node['via2a00']=True
    def h_head(self,uc,pc,size,user):
        if not self.head_visit:self.request_stop('frame-head-entered-outside-dispatcher',pc=pc);return
        self.request_stop('frame-head',pc=pc)
    def h_lead(self,uc,pc,size,user):
        node=self.cur
        if node is None:return
        if pc in LEAD_SET:node['leaders'][pc]+=1
        if pc in F3_INDEX_PCS:node['idx'].append((pc,uc.reg_read(UC_REG[F3_INDEX_PCS[pc]])&0xffff))
        if pc in TRAP_SET:self.request_stop('trap-boundary',pc=pc)
    def h_block(self,uc,addr,size,user):
        node=self.cur
        if node is not None:node['tbs']+=1
        if addr&1 and self.stop is None:self.request_stop('odd-pc',pc=addr,**{'from':self.last_node_hint()})
    def routable(self,level,pc):
        """Entry routability of a callback PC (the contract's method: the callback PC is an executor entry of the level; internal blocks of an executor are the executor's)."""
        return pc<0x100000 and not pc&1 and bool(self.levels[level][pc>>1])
    # ---- waits (declared release is a host write, then the same pass continues)
    def h_gate_loop(self,uc,pc,size,user):self.gate_flag=True
    def h_gate_out(self,uc,pc,size,user):self.gate_flag=False
    def h_gate(self,uc,pc,size,user):
        flag=self.gate_flag;self.gate_flag=False
        if flag and self.m.byte(0x107ded)&0x80:self.wait_stop(pc,live=self.m.byte(0x107ded),compared=0x80)
    def h_sound(self,uc,pc,size,user):
        a5=uc.reg_read(UC_REG['a5']);live=self.m.word((a5-0x328c)&M32);want=uc.reg_read(UC_REG['d1'])&0xffff
        if live==want:self.wait_stop(pc,live=live,compared=want)
    def h_sprite(self,uc,pc,size,user):
        a5=uc.reg_read(UC_REG['a5']);live=self.m.word((a5+0xd34)&M32);want=uc.reg_read(UC_REG['d4'])&0xffff
        if live!=want:self.wait_stop(pc,live=live,compared=want)
    def wait_stop(self,pc,live,compared):
        self.waiting=dict(pc=pc,kind=WAIT_KIND[pc],live=live,compared=compared);self.m.cpu.emu_stop()
    def release_wait(self,w):
        """Declared release (F1 observer vocabulary): sound ring tail := ffff, sprite queue word := D4.W, gate: BYTE 107ded bit7 cleared unless WORD 107dea <> 0."""
        mach=self.m;pc=w['pc'];changes=[]
        if pc==0x3aea:changes.append((0x104d74,2,0xffff))
        elif pc==0xcda4:changes.append((0x108d34,2,w['compared']))
        else:
            if mach.word(0x107dea)==0:changes.append((0x107ded,1,w['live']&0x7f))
        for a,s,v in changes:mach.put(a,s,v)
        return changes
    # ---- one pass
    def run_pass(self):
        mach=self.m;c=mach.cpu
        self.pass_nodes=[];self.cur=None;self.head_visit=False;self.waiting=None;self.stop=None;self.pass_flags=collections.Counter()
        walk=self.list_walk();ports0=len(mach.ports);start_digest=mach.digest(PASS_PC)
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
                if len(waits)>WAIT_LIMIT or not changes:self.stop=dict(reason='wait-not-released',wait=rec);break
                continue
            break
        reason=self.stop
        if reason is None:
            if mach.odd:reason=dict(reason='odd-data-access',**mach.odd)
            elif mach.invalid:reason=dict(reason='invalid-memory-access',**mach.invalid)
            elif mach.fetch_unmapped is not None:
                a=mach.fetch_unmapped
                reason=dict(reason='bios-boundary' if BIOS_LO<=a<BIOS_LO+0x100000 else 'fetch-unmapped',address=a,odd=bool(a&1),**{'from':self.last_node_hint()})
            elif mach.intr:reason=dict(reason='cpu-exception',**mach.intr,odd_pc=bool(mach.intr['pc']&1))
            elif not ended:reason=dict(reason='unicorn-error',error=uc_error,pc=mach.pc())
            else:reason=dict(reason='step-limit',limit=self.pass_limit,pc=mach.pc())
        return reason,walk,start_digest,waits,ports0
    def last_node_hint(self):
        n=self.cur
        if n is not None:return dict(a6=n['a6'],cb=n['cb'],seq=n['seq'])
        return {}
    def list_walk(self):
        mach=self.m;out=[];a=mach.long(CONTROLLER+8)
        while a!=FRAME_HEAD and len(out)<200 and a!=0:
            out.append(a)
            if a&1 or not RAM_BASE<=a<0x200000:break
            a=mach.long(a+8)
        return out
    # ---- node finish
    def finish_node(self,node,exit_state,partial):
        mach=self.m
        entry_digest=state_blob_digest(node['entry_ram'],node['entry_regs'],0x2ab8,node['entry_bank'])
        exit_digest=state_blob_digest(exit_state['ram'],exit_state['regs'],exit_state['pc'],exit_state['bank'])
        ports=mach.ports[node['ports0']:]
        rec=dict(seq=node['seq'],a6=node['a6'],cb=node['cb'],depth=node['depth'],entry=entry_digest,exit=exit_digest,tbs=node['tbs'],rA=self.routable('A',node['cb']),rB=self.routable('B',node['cb']),rA0=self.routable('A',node['cb']) and not (0x4fcce<=node['cb']<0x4fda6),
            ports=len(ports),ports_sha=ports_digest(ports),bank_reads=mach.bank_reads-node['bank_reads0'],rom_reads=mach.rom_reads-node['rom_reads0'],dev_reads=len(mach.dev_reads)-node['dev0'],
            self_delete=bool(node['via2a00']),waits=len(node['waits']),partial=partial)
        node['rec']=rec;node['exit_state']=exit_state;node['exit_digest']=exit_digest;node['entry_digest']=entry_digest;node['ports_list']=ports
        self.cb_counts[node['cb']]+=1
        for pc,n in node['leaders'].items():self.leader_hits[pc]+=n
        for pc,v in node['idx']:self.index_hits[pc][v]+=1
        if self.frame<FRAMES_BASE:
            self.cb120[node['cb']]+=1
            if node['cb']==CALLBACK_IDLE:self.idle120['zombie' if node['depth'] else 'static']+=1
            for pc,n in node['leaders'].items():self.leader120[pc]+=n
            for pc,v in node['idx']:self.index120[pc][v]+=1
        if self.frame==0 and not partial:self.frame0_cbs.append(node['cb'])
        if (self.frame,node['seq']) in self.capture_nodes:self.captured_nodes[(self.frame,node['seq'])]=dict(entry=dict(ram=node['entry_ram'],regs=node['entry_regs'],pc=0x2ab8,bank=node['entry_bank']),exit=exit_state)
        if node['cb'] in CALLBACK_F3 or node['cb'] in MODEL_CALLBACKS:
            rec['leaders']=sorted(node['leaders']);rec['idx']=node['idx']
        self.pass_nodes.append(node)
        if self.heavy and not partial:
            if node['cb'] in CALLBACK_F3:self.f3_replay(node)
            if node['cb'] in MODEL_CALLBACKS:self.model_node(node)
        self.digest.update(json.dumps([self.frame,rec],sort_keys=True).encode())
    # ---- blobs
    def blob(self,data):
        d=sha(data)
        if self.sink is not None:self.blobs[d]=data
        return d
    def dump_state(self,state,kind,**extra):
        row=dict(kind=kind,ram=self.blob(state['ram']),regs=state['regs'],pc=state['pc'],bank=list(state['bank']),state=state_blob_digest(state['ram'],state['regs'],state['pc'],state['bank']))
        row.update(extra);return row
    # ---- whole seed
    def run(self):
        snap=self.snap;mach=self.build(snap);frame=0
        if self.declare_base:self.declared.append(dict(kind='ram-write',address=BASE_LONG,size=4,value=SPD,why='declared dispatcher base LONG 104ca4 = SPd (2ab2 MOVE.L A7,104ca4 is never executed in a seed RAM)'))
        self.limit=self.frames_limit;buffer={};last_ram=None;dump_all=True;full_prefix=True
        if self.sink is not None:self.dump_rows.append(self.dump_state(mach.state(),'seed-start',frame=-1))
        while frame<self.limit:
            self.frame=frame;mach=self.m;c=mach.cpu
            if self.mode=='split' and frame>0:
                st=prev_state;st['regs']=dict(st['regs']);st['regs']['a6']=CONTROLLER;st['regs']['a7']=SPD;st['pc']=PASS_PC;mach=self.build(st);c=mach.cpu
            elif frame>0:
                c.reg_write(UC_REG['sr'],0x2000);c.reg_write(UC_REG['pc'],PASS_PC);c.reg_write(UC_REG['a6'],CONTROLLER);c.reg_write(UC_REG['a7'],SPD)
            if frame in self.capture_frames:self.captured[frame]=mach.state()
            reason,walk,start_digest,waits,ports0=self.run_pass()
            end_state=mach.state();partial=None
            if reason['reason']=='frame-head':
                end_state['pc']=reason['pc'];self.end_pcs.append(reason['pc'])
                regs=end_state['regs'];ok=(regs['a6']==FRAME_HEAD and regs['a5']==A5V and regs['a7']==SPD-4 and mach.long(SPD-4)==PASS_PC and end_state['pc'] in HEAD_STOPS and regs['a0']==end_state['pc'])
                if not ok:self.head_bad+=1
            else:
                partial=self.cur
                if partial is not None:self.cur=None;self.finish_node(partial,end_state,True)
            visited=[n['a6'] for n in self.pass_nodes];ws=set(walk);vs=set(visited)
            ports=mach.ports[ports0:]
            cbs=tuple(n['cb'] for n in self.pass_nodes)
            covA=all(n['rec']['rA'] for n in self.pass_nodes);covB=all(n['rec']['rB'] for n in self.pass_nodes);cov0=all(n['rec']['rA0'] for n in self.pass_nodes)
            prec=dict(frame=frame,start=start_digest,end=state_blob_digest(end_state['ram'],end_state['regs'],end_state['pc'],end_state['bank']),stop=reason['reason'],list_len=len(walk),
                visited=len(visited),walk=walk,nodes=[n['rec'] for n in self.pass_nodes],inserted=[a for a in visited if a not in ws],deleted=[a for a in walk if a not in vs],revisited=len(visited)-len(vs),
                waits=waits,ports=len(ports),ports_sha=ports_digest(ports),flags=dict(self.pass_flags),covA=covA,covB=covB,cov0=cov0,config=sha(repr(cbs).encode())[:16],ctrl_skipped=True)
            self.max_tbs=max(self.max_tbs,sum(n['rec']['tbs'] for n in self.pass_nodes));self.max_nodes=max(self.max_nodes,len(self.pass_nodes))
            self.pass_records.append(prec);self.digest.update(json.dumps(prec,sort_keys=True,default=str).encode())
            first_config=cbs not in self.configs;self.configs.add(cbs)
            if self.sink is not None:
                keep=(frame in (0,1,20,21)) or first_config or reason['reason']!='frame-head' or frame+1>=self.limit
                if not covA:full_prefix=False;buffer={k:v for k,v in buffer.items() if v[1]}
                if full_prefix:buffer[frame]=(end_state,keep)
                elif keep:buffer[frame]=(end_state,True)
                last_ram=end_state
            self.covered_prefix=self.covered_prefix and covA;self.covered0=self.covered0 and cov0;prev_state=end_state
            if reason['reason']!='frame-head':
                self.stop=dict(reason, frame=frame);break
            frame+=1
            if frame==FRAMES_BASE and self.extend and self.limit<FRAMES_FULL:
                if self.covered_prefix:self.limit=FRAMES_FULL
        else:
            self.stop=dict(reason='frame-limit',frame=frame-1,frames=frame)
        self.frames_done=len(self.pass_records);self.fully_covered=self.covered_prefix
        if self.sink is not None:
            for f in sorted(buffer):
                st,keep=buffer[f]
                if keep or (full_prefix and self.covered_prefix):self.dump_rows.append(self.dump_state(st,'pass-end',frame=f,full_seed=bool(full_prefix and self.covered_prefix)))
        return self


# ----------------------------------------------------------------------------------
# Independent model: a M68000 subset interpreter that decodes the ORIGINAL ROM BYTES of the F2 blocks (2aac 270e 2716 271a), the 4fcce blocks and the dispatcher shell
# (2ab8..2ac6).  The decoder is written from the 68000 programmer's reference by instruction format; it shares no code with Unicorn, capstone or the C++.  Complete CCR
# (X N Z V C; None = unknown, a branch on an unknown flag is an error), 32-bit register semantics, explicit byte / word / long operations.
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
SZ={0:1,1:2,2:4}
MASK={1:0xff,2:0xffff,4:M32}
SIGN={1:0x80,2:0x8000,4:0x80000000}


def sext(v,size):
    v&=MASK[size];return v-(1<<(8*size)) if v&SIGN[size] else v


class Model(object):
    def __init__(self,program,ram,regs,pc,bank):
        self.prog=program;self.ram=bytearray(ram);self.r={k:regs[k]&M32 for k in KEYS};self.pc=pc;self.bank=bank
        self.cc=dict(X=None,N=None,Z=None,V=None,C=None);self.writes=[];self.reads=[];self.ports=[];self.wlog=[];self.trace=[];self.cache={};self.steps=0
    # memory
    def mem_read(self,a,n):
        a&=M32
        if n>1 and a&1:raise ModelError('odd read %x'%a)
        self.reads.append((a,n))
        if a<0x100000:return int.from_bytes(self.prog[a:a+n],'big')
        if 0x100000<=a<0x200000:return int.from_bytes(bytes(self.ram[(a+i)&0xffff] for i in range(n)),'big')
        if 0x200000<=a<0x2fe000:
            ph=self.bank+a-0x200000;return int.from_bytes(self.prog[ph:ph+n],'big')
        raise ModelError('read %x'%a)
    def mem_write(self,a,n,v):
        a&=M32;v&=MASK[n]
        if n>1 and a&1:raise ModelError('odd write %x'%a)
        if 0x100000<=a<0x200000:
            for i,b in enumerate(v.to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
            self.writes.append((a,n,v));self.wlog.append((a,n,v));return
        if 0x300000<=a<0x400000 or 0xd00000<=a<0xd01000:self.ports.append((2,a,n,v));self.wlog.append((a,n,v));return
        raise ModelError('write %x'%a)
    # decode
    def ext(self,pos):return int.from_bytes(self.prog[pos:pos+2],'big')
    def decode_ea(self,mode,reg,size,pos):
        if mode==0:return ('dn',reg),pos
        if mode==1:return ('an',reg),pos
        if mode==2:return ('ind',reg),pos
        if mode==3:return ('postinc',reg),pos
        if mode==4:return ('predec',reg),pos
        if mode==5:return ('disp',reg,sext(self.ext(pos),2)),pos+2
        if mode==6:raise ModelError('indexed ea')
        if reg==0:return ('abs',sext(self.ext(pos),2)&M32),pos+2
        if reg==1:return ('abs',(self.ext(pos)<<16)|self.ext(pos+2)),pos+4
        if reg==4:
            if size==4:return ('imm',(self.ext(pos)<<16)|self.ext(pos+2)),pos+4
            if size==2:return ('imm',self.ext(pos)),pos+2
            return ('imm',self.ext(pos)&0xff),pos+2
        raise ModelError('ea mode %d reg %d'%(mode,reg))
    def decode(self,pc):
        if pc in self.cache:return self.cache[pc]
        w=self.ext(pc);hi=w>>12;ins=dict(pc=pc)
        if w==0x4e75:ins.update(op='rts',len=2)
        elif hi in (1,2,3):
            size={1:1,3:2,2:4}[hi];src,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);dm=(w>>6)&7;dr=(w>>9)&7
            dst,pos=self.decode_ea(dm,dr,size,pos);ins.update(op='movea' if dm==1 else 'move',size=size,src=src,dst=dst,len=pos-pc)
        elif hi==6:
            c=(w>>8)&15;d=w&0xff
            if d==0:disp=sext(self.ext(pc+2),2);ln=4
            elif d==0xff:raise ModelError('long branch')
            else:disp=sext(d,1);ln=2
            ins.update(op={0:'bra',1:'bsr'}.get(c,'bcc'),cond=c,target=(pc+2+disp)&M32,len=ln)
        elif (w&0xf1c0)==0x41c0:
            ea,pos=self.decode_ea((w>>3)&7,w&7,4,pc+2);ins.update(op='lea',reg=(w>>9)&7,src=ea,len=pos-pc)
        elif (w&0xffc0)==0x4e80:
            ea,pos=self.decode_ea((w>>3)&7,w&7,4,pc+2);ins.update(op='jsr',src=ea,len=pos-pc)
        elif (w&0xffc0)==0x4ec0:
            ea,pos=self.decode_ea((w>>3)&7,w&7,4,pc+2);ins.update(op='jmp',src=ea,len=pos-pc)
        elif (w&0xff00)==0x4a00 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='tst',size=size,src=ea,len=pos-pc)
        elif (w&0xff00)==0x4400 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='neg',size=size,dst=ea,len=pos-pc)
        elif (w&0xfb80)==0x4880 and (w&0x38)!=0:                       # MOVEM (register list word follows the opcode)
            size=4 if w&0x40 else 2;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+4);ins.update(op='movem',dir=(w>>10)&1,size=size,mask=self.ext(pc+2),ea=ea,len=pos-pc)
        elif hi==5 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);q=(w>>9)&7
            ins.update(op='subq' if w&0x100 else 'addq',size=size,imm=q or 8,dst=ea,len=pos-pc)
        elif hi==0 and (w&0xf00)==0x600 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos);ins.update(op='addi',size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi==0 and (w&0xf00)==0xc00 and (w&0xc0)!=0xc0:
            size=SZ[(w>>6)&3];imm,pos=self.decode_ea(7,4,size,pc+2);ea,pos=self.decode_ea((w>>3)&7,w&7,size,pos);ins.update(op='cmpi',size=size,imm=imm[1],dst=ea,len=pos-pc)
        elif hi==0xd:
            om=(w>>6)&7;reg=(w>>9)&7
            if om in (0,1,2):
                size=SZ[om];ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='add',size=size,reg=reg,src=ea,len=pos-pc)
            elif om in (3,7):
                size=2 if om==3 else 4;ea,pos=self.decode_ea((w>>3)&7,w&7,size,pc+2);ins.update(op='adda',size=size,reg=reg,src=ea,len=pos-pc)
            else:raise ModelError('ADD to memory %x'%pc)
        elif hi==0xe and (w&0xc0)!=0xc0:                                 # shift / rotate register form
            if (w&0x18)!=0x08 or (w&0x20):raise ModelError('shift form %04x at %x'%(w,pc))
            ins.update(op='lsl' if w&0x100 else 'lsr',size=SZ[(w>>6)&3],count=((w>>9)&7) or 8,reg=w&7,len=2)
        else:raise ModelError('opcode %04x at %x'%(w,pc))
        self.cache[pc]=ins;return ins
    # operands
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
        if k=='abs':return ('mem',d[1])
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
    def push32(self,v):self.r['a7']=(self.r['a7']-4)&M32;self.mem_write(self.r['a7'],4,v)
    def pop32(self):
        v=self.mem_read(self.r['a7'],4);self.r['a7']=(self.r['a7']+4)&M32;return v
    def flag(self,n):
        if self.cc[n] is None:raise ModelError('branch on the unknown flag %s'%n)
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
    def sub(self,d,s,size,x=True):
        mk=MASK[size];d&=mk;s&=mk;r=(d-s)&mk;c=int(d<s)
        self.cc.update(N=int(bool(r&SIGN[size])),Z=int(r==0),V=int(bool((d^s)&(d^r)&SIGN[size])),C=c)
        if x:self.cc['X']=c
        return r
    def add(self,d,s,size):
        mk=MASK[size];d&=mk;s&=mk;r=(d+s)&mk;c=int(d+s>mk)
        self.cc.update(X=c,N=int(bool(r&SIGN[size])),Z=int(r==0),V=int(bool((~(d^s))&(d^r)&SIGN[size])),C=c);return r
    def step(self):
        pc=self.pc;ins=self.decode(pc);op=ins['op'];nxt=(pc+ins['len'])&M32;r=self.r
        if op=='move':
            s=self.resolve(ins['src'],ins['size']);v=self.get(s,ins['size']);d=self.resolve(ins['dst'],ins['size']);self.put(d,ins['size'],v);self.nz(v,ins['size'])
        elif op=='movea':
            s=self.resolve(ins['src'],ins['size']);v=self.get(s,ins['size']);r['a%d'%ins['dst'][1]]=sext(v,ins['size'])&M32
        elif op=='lea':
            loc=self.resolve(ins['src'],4);r['a%d'%ins['reg']]=loc[1]
        elif op=='tst':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);self.nz(v,ins['size'])
        elif op=='neg':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);res=self.sub(0,v,ins['size']);self.put(d,ins['size'],res)
        elif op=='addq':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size'])
            if d[0]=='reg' and d[1][0]=='a':r[d[1]]=(r[d[1]]+ins['imm'])&M32
            else:self.put(d,ins['size'],self.add(v,ins['imm'],ins['size']))
        elif op=='addi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.put(d,ins['size'],self.add(v,ins['imm'],ins['size']))
        elif op=='cmpi':
            d=self.resolve(ins['dst'],ins['size']);v=self.get(d,ins['size']);self.sub(v,ins['imm'],ins['size'],x=False)
        elif op=='add':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='d%d'%ins['reg'];self.put(('reg',n),ins['size'],self.add(r[n],v,ins['size']))
        elif op=='adda':
            v=self.get(self.resolve(ins['src'],ins['size']),ins['size']);n='a%d'%ins['reg'];r[n]=(r[n]+sext(v,ins['size']))&M32
        elif op in ('lsl','lsr'):
            n='d%d'%ins['reg'];size=ins['size'];mk=MASK[size];v=r[n]&mk;cnt=ins['count']
            if op=='lsl':out=(v<<cnt)&mk;carry=(v>>(8*size-cnt))&1
            else:out=v>>cnt;carry=(v>>(cnt-1))&1
            self.put(('reg',n),size,out);self.cc.update(X=carry,C=carry,N=int(bool(out&SIGN[size])),Z=int(out==0),V=0)
        elif op=='movem':
            if ins['dir']!=0 or ins['ea'][0]!='ind':raise ModelError('MOVEM form')
            base=self.resolve(ins['ea'],ins['size'])[1];regs=['d%d'%i for i in range(8)]+['a%d'%i for i in range(8)]
            for i in range(16):                                          # control mode: bit0 = D0 ... bit15 = A7, ascending addresses
                if ins['mask']>>i&1:self.mem_write(base,ins['size'],r[regs[i]]&MASK[ins['size']]);base+=ins['size']
        elif op=='jsr':
            loc=self.resolve(ins['src'],4);self.push32(nxt);nxt=loc[1]
        elif op=='jmp':
            loc=self.resolve(ins['src'],4);nxt=loc[1]
        elif op=='bsr':self.push32(nxt);nxt=ins['target']
        elif op=='bra':nxt=ins['target']
        elif op=='bcc':
            if self.cond(ins['cond']):nxt=ins['target']
        elif op=='rts':nxt=self.pop32()
        else:raise ModelError(op)
        self.pc=nxt
    def run(self,stops,limit=200000,trace=False):
        n=0
        while self.pc not in stops or n==0 and False:
            if trace:self.trace.append((self.pc,tuple(self.r[k] for k in KEYS)))
            self.step();n+=1
            if n>limit:raise ModelError('step limit')
        if trace:self.trace.append((self.pc,tuple(self.r[k] for k in KEYS)))
        return n


# ----------------------------------------------------------------------------------
# Fresh-CPU node replay (the F3 decision 10 node seed form: PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd, stop 2ac2) and the traced native run used by the model comparison
# ----------------------------------------------------------------------------------
def replay_node(program,fixed,snap,split_pc=None,stop_extra=(),limit=PASS_LIMIT):
    """Fresh Machine from snap (PC 2ab8).  Stops at the first 2ac2 (the callback returned) or at the first arrival at split_pc (state captured, then the same CPU continues)."""
    mach=Machine(program,fixed,snap);mach.install_basic_hooks();c=mach.cpu
    out=dict(status=None,split=None,state=None,reason=None)
    def at_ret(uc,pc,size,user):
        if out['status'] is None:out['status']='2ac2';st=mach.state();st['pc']=pc;out['state']=st;uc.emu_stop()
    def at_split(uc,pc,size,user):
        if out['split'] is None and out['status'] is None:
            st=mach.state();st['pc']=pc;out['split']=st;out['split_ports']=len(mach.ports);uc.emu_stop()
    def at_trap(uc,pc,size,user):
        if out['status'] is None:out['status']='trap-boundary';out['reason']=dict(pc=pc);st=mach.state();st['pc']=pc;out['state']=st;uc.emu_stop()
    c.hook_add(UC_HOOK_CODE,at_ret,begin=PASS_PC,end=PASS_PC)
    if split_pc is not None:c.hook_add(UC_HOOK_CODE,at_split,begin=split_pc,end=split_pc)
    for pc in stop_extra:c.hook_add(UC_HOOK_CODE,at_trap,begin=pc,end=pc)
    while True:
        mach.fetch_unmapped=None;mach.odd=None;mach.invalid=None;mach.intr=None;was_split=out['split'] is not None
        try:c.emu_start(out['split']['pc'] if out['split'] is not None else snap['pc'],0xffffff,count=limit);err=None
        except unicorn.UcError as e:err=str(e)
        if out['split'] is not None and not was_split and out['status'] is None:continue
        break
    if out['status'] is None:
        out['status']='guard';out['reason']=dict(odd=mach.odd,invalid=mach.invalid,fetch_unmapped=mach.fetch_unmapped,intr=mach.intr,error=err,step_limit=bool(err is None and not (mach.odd or mach.invalid or mach.intr)))
    out['ports']=list(mach.ports);out['bank_reads']=mach.bank_reads;out['rom_reads']=mach.rom_reads;out['mach']=mach
    return out


def traced_native(program,fixed,snap,stops,limit=2_000_000):
    """Fresh Machine run from snap.pc with a per-instruction record (PC and the 16 registers BEFORE the instruction), ordered data reads and RAM / device writes."""
    mach=Machine(program,fixed,snap);c=mach.cpu
    trace=[];reads=[];writes=[];res=dict(stopped=None)
    def code(uc,pc,size,user):
        regs=tuple(uc.reg_read(UC_REG[k]) for k in KEYS);trace.append((pc,regs))
        if pc in stops:res['stopped']=pc;uc.emu_stop()
    def rd(uc,access,address,size,value,user):reads.append((address,size))
    def wr(uc,access,address,size,value,user):writes.append((address,size,value&((1<<(8*size))-1)))
    c.hook_add(UC_HOOK_CODE,code);c.hook_add(UC_HOOK_MEM_READ,rd,begin=0,end=0x2fffff);c.hook_add(UC_HOOK_MEM_WRITE,wr,begin=0x100000,end=0x3fffff)
    try:c.emu_start(snap['pc'],0xffffff,count=limit)
    except unicorn.UcError as e:res['error']=str(e)
    res.update(trace=trace,reads=reads,writes=writes,mach=mach);return res


def byte_events(events,with_value=True):
    out=[]
    for e in events:
        a,n=e[0],e[1]
        if with_value:
            for i,b in enumerate(e[2].to_bytes(n,'big')):out.append((a+i,b))
        else:
            for i in range(n):out.append(a+i)
    return out


def seed_f3_replay(self,node):
    """Replay one F3 node execution on a fresh CPU from its recorded entry state (PC 2ab8) with a stop at e94fe (the F3a/F3b boundary) and at 2ac2."""
    rec=node['rec'];entry_state=dict(ram=node['entry_ram'],regs=node['entry_regs'],pc=0x2ab8,bank=node['entry_bank'])
    rp=replay_node(self.program,self.fixed,entry_state,split_pc=F3_SPLIT_PC,stop_extra=tuple(sorted(TRAP_SET)))
    st=rp['state'];exit_ok=ports_ok=False
    if rp['status']=='2ac2':
        exit_ok=state_blob_digest(st['ram'],st['regs'],st['pc'],st['bank'])==node['exit_digest']
        ports_ok=ports_digest(rp['ports'])==rec['ports_sha']
    split=rp['split'];split_digest=state_blob_digest(split['ram'],split['regs'],split['pc'],split['bank']) if split else None
    frec=dict(frame=self.frame,seq=node['seq'],a6=node['a6'],cb=node['cb'],depth=node['depth'],entry=node['entry_digest'],exit=node['exit_digest'],ports=rec['ports'],ports_sha=rec['ports_sha'],
        leaders=sorted(node['leaders']),idx=node['idx'],bank_reads=rec['bank_reads'],rom_reads=rec['rom_reads'],replay_status=rp['status'],replay_exit_equal=exit_ok,replay_ports_equal=ports_ok,
        e94fe=split_digest,e94fe_ports=rp.get('split_ports'),self_delete=rec['self_delete'],waits=rec['waits'],rA=rec['rA'],rB=rec['rB'])
    want=(self.frame==0 and node['cb']==0xe9150) or node['cb'] in (0xe9350,0xe9362) or (self.frame,node['seq']) in self.plan
    if self.sink is not None and want:
        frec['dumps']=dict(entry=self.dump_state(entry_state,'f3-entry'),exit=self.dump_state(node['exit_state'],'f3-exit'))
        if split:frec['dumps']['e94fe']=self.dump_state(split,'f3-e94fe')
    self.f3_records.append(frec)
    if not exit_ok or not ports_ok:self.model_mismatch.append(dict(kind='f3-replay',frame=self.frame,seq=node['seq'],cb=node['cb'],status=rp['status'],reason=rp['reason']))


def seed_model_node(self,node):
    """Independent-model comparison for a node whose callback is an F2 / 4fcce block: the model runs from the entry state (PC 2ab8) to 2ac2 / 2a00."""
    cb=node['cb'];mach=self.m
    entry=dict(ram=node['entry_ram'],regs=node['entry_regs'],pc=0x2ab8,bank=node['entry_bank'])
    stops=(PASS_PC,0x2a00);via=node['via2a00'] if isinstance(node['via2a00'],dict) else None
    mdl=Model(self.program,entry['ram'],entry['regs'],0x2ab8,entry['bank'][0])
    row=dict(frame=self.frame,seq=node['seq'],cb=cb,a6=node['a6'],depth=node['depth'],end=None,ok=True,diff=[])
    try:mdl.run(stops)
    except ModelError as e:
        row['ok']=False;row['diff'].append('model error: %s'%e)
    else:
        row['end']=mdl.pc
        if mdl.pc==PASS_PC:
            ref=node['exit_state'];ref_ports=node['ports_list']
        elif via is not None:
            ref=via;ref_ports=mach.ports[node['ports0']:node['ports0']+via['ports']]
        else:
            ref=None;ref_ports=[]
        if ref is None:row['ok']=False;row['diff'].append('model ended at %x without a native counterpart'%mdl.pc)
        else:
            if tuple(mdl.r[k] for k in KEYS)!=tuple(ref['regs'][k] for k in KEYS):row['ok']=False;row['diff'].append('registers')
            if bytes(mdl.ram)!=ref['ram']:row['ok']=False;row['diff'].append('ram')
            nat=byte_events([(a,n,v) for k,a,n,v in ref_ports]);mod=byte_events([(a,n,v) for k,a,n,v in mdl.ports])
            if nat!=mod:row['ok']=False;row['diff'].append('ports')
    key=(cb,'zombie' if (cb==CALLBACK_IDLE and node['depth']) else 'normal')
    traced=False
    if self.heavy and (key[1]=='zombie' or self.traced_count[key]<TRACED_PER_KEY):
        self.traced_count[key]+=1;traced=True;row['traced']=True
        nat=traced_native(self.program,self.fixed,entry,set(stops))
        mdl2=Model(self.program,entry['ram'],entry['regs'],0x2ab8,entry['bank'][0])
        try:mdl2.run(stops,trace=True)
        except ModelError as e:row['ok']=False;row['diff'].append('traced model error: %s'%e)
        else:
            if nat['trace']!=mdl2.trace:row['ok']=False;row['diff'].append('instruction trace (PC + 16 registers before every instruction), native %d vs model %d'%(len(nat['trace']),len(mdl2.trace)))
            if byte_events(nat['writes'])!=byte_events(mdl2.wlog):row['ok']=False;row['diff'].append('ordered writes')
            if byte_events(nat['reads'],False)!=byte_events(mdl2.reads,False):row['ok']=False;row['diff'].append('ordered reads')
            row['instructions']=len(mdl2.trace)-1;row['writes']=len(mdl2.wlog);row['reads']=len(mdl2.reads)
    self.model_count[(cb,key[1],'traced' if traced else 'final',row['ok'])]+=1
    if not row['ok'] and len(self.model_mismatch)<200:self.model_mismatch.append(dict(kind='model',**row))
    if traced and len(self.model_rows)<4000:self.model_rows.append(row)


SeedRun.f3_replay=seed_f3_replay
SeedRun.model_node=seed_model_node
TRACED_PER_KEY=3
LEAD_SET=frozenset();TRAP_SET=frozenset()


# ----------------------------------------------------------------------------------
# Seeds, workers
# ----------------------------------------------------------------------------------
G={}
SEEDS={}


def setup():
    program=load_rom();G['program']=program
    G['fixed']=(ctypes.c_ubyte*0x100000).from_buffer_copy(program[:0x100000])
    levels=build_levels(program);G['levels']=levels
    global LEAD_SET,TRAP_SET
    LEAD_SET=frozenset(F2_LEADERS)|frozenset(levels['f3a_starts'])|frozenset(levels['f3b_starts']);TRAP_SET=frozenset(levels['traps'])
    assert len(LEAD_SET&TRAP_SET)==0
    return program


def load_seeds():
    assert sha(SEED_OBS.read_bytes())==SEED_SHA,'stage_entry_body observation changed'
    obs=json.loads(SEED_OBS.read_text());SEEDS.clear()
    for res in obs['results']:
        for ph in res['phases']:
            if ph['final_pc']!=0xff000:continue
            if ph['name']=='begin':kind='natural'
            elif ph['name']=='release-poisoned-prefix':kind='guard-release'
            else:continue
            SEEDS[res['case_index']]=dict(case=res['case_index'],kind=kind,phase=ph['name'],family=res['fixture']['family'],record=res['fixture'].get('record'),profile=res['fixture'].get('profile'),
                lookup=res['fixture'].get('lookup'),bank=ph['result']['bank'],ram_file=ph['ram_file'],ram_sha256=ph['ram_sha256'],result={k:v for k,v in ph['result'].items() if k in KEYS+('bank',)})
    return SEEDS


def seed_snap(sd):
    data=(SEED_DIR/sd['ram_file']).read_bytes();assert len(data)==RAM_SIZE and sha(data)==sd['ram_sha256'],sd['ram_file']
    ram=bytearray(data);prior=int.from_bytes(ram[0x4ca4:0x4ca8],'big');ram[0x4ca4:0x4ca8]=SPD.to_bytes(4,'big')
    r=sd['result'];regs={k:r[k]&M32 for k in KEYS if k in r};regs['a5']=A5V;regs['a6']=CONTROLLER;regs['a7']=SPD
    for k in KEYS:regs.setdefault(k,0)
    bank=(0x200000,0xa0,0x1000) if sd['bank']==2 else (0x300000,0xa0,0x2000)
    node_check=static_list_check(data)
    return dict(ram=bytes(ram),regs=regs,pc=PASS_PC,bank=bank),dict(seed_ram_sha256=sd['ram_sha256'],prior_104ca4=prior,seed_regs=dict(r),static_list=node_check)


def rl(data,address):
    o=address&0xffff;return int.from_bytes(data[o:o+4],'big')


def static_list_check(ram):
    """The F2 'node structure' facts of the seed RAM: 8 static nodes (c4 apart from 100820), frame head e4a, controller c52a, idle callback 270e of the other six, sentinel 100e98."""
    nodes=[0x100820,0x1008e4,0x1009a8,0x100a6c,0x100b30,0x100bf4,0x100cb8,0x100da8];cbs=[rl(ram,a) for a in nodes]       # the spacing is c4 up to 100cb8, 100da8 is f0 after 100cb8
    walk=[];a=0x100820
    while len(walk)<200:
        walk.append(a);a=rl(ram,a+8)
        if a==0x100820 or not 0x100000<=a<0x200000:break
    order=[x for x in walk if x in nodes]
    return dict(callbacks=[hx(c) for c in cbs],ring_ok=(order==nodes and a==0x100820),parent_zero=all(rl(ram,a+0xc)==0 for a in nodes),
        sentinel=[hx(rl(ram,0x100e98+o)) for o in (0,4,8,0xc)],pool_head=hx(rl(ram,0x104c9c)),free_count=int.from_bytes(ram[0x4ca0:0x4ca2],'big'),zombies=int.from_bytes(ram[0x4ca2:0x4ca4],'big'))


def stable(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),default=str)


def f3_digest(run):
    h=hashlib.sha256()
    for f in run.f3_records:h.update(stable({k:v for k,v in f.items() if k!='dumps'}).encode())
    h.update(stable(sorted((str(k),v) for k,v in run.model_count.items())).encode())
    return h.hexdigest()


def summarize_a(case,sd,meta,run):
    nodes=[n for p in run.pass_records for n in p['nodes']]
    f3=collections.Counter();e94=0
    for f in run.f3_records:
        f3[(f['cb'],f['replay_status'],f['replay_exit_equal'],f['replay_ports_equal'])]+=1
        if f['e94fe']:e94+=1
    first=run.pass_records[0]['nodes'] if run.pass_records else []
    walk=run.pass_records[0]['walk'] if run.pass_records else []
    order_ok=walk[:3]==[0x1009a8,0x100a6c,0x100b30] and walk[-2:]==[0x100cb8,0x100da8] and 0x100bf4 in walk and walk.index(0x100bf4)>walk.index(0x100b30)
    return dict(case=case,kind=sd['kind'],family=sd['family'],bank=sd['bank'],meta=meta,stop=run.stop,frames_done=run.frames_done,frames_complete=sum(1 for p in run.pass_records if p['stop']=='frame-head'),covered=run.fully_covered,covered0=run.covered0,digest=run.digest.hexdigest(),f3_digest=f3_digest(run),
        cb_counts=dict(run.cb_counts),cb120=dict(run.cb120),idle120=dict(run.idle120),leader_hits=dict(run.leader_hits),leader120=dict(run.leader120),
        index_hits={k:dict(v) for k,v in run.index_hits.items()},index120={k:dict(v) for k,v in run.index120.items()},waits=dict(run.waits_total),a7_bad=run.a7_bad,head_bad=run.head_bad,
        model_count=dict(run.model_count),model_mismatch=run.model_mismatch[:50],f3_summary=dict(f3),f3_e94fe=e94,f3_e94fe120=sum(1 for f in run.f3_records if f['e94fe'] and f['frame']<FRAMES_BASE),max_tbs=run.max_tbs,max_nodes=run.max_nodes,frame0_cbs=run.frame0_cbs,
        f3_keys=[(f['frame'],f['seq'],f['cb'],f['leaders'],f['idx']) for f in run.f3_records],
        inserted_passes=sum(1 for p in run.pass_records if p['inserted']),deleted_passes=sum(1 for p in run.pass_records if p['deleted']),revisit_passes=sum(1 for p in run.pass_records if p['revisited']),
        self_delete_nodes=sum(1 for n in nodes if n['self_delete']),wait_passes=sum(1 for p in run.pass_records if p['waits']),first_order_ok=order_ok,
        bank_reads_f3=sum(f['bank_reads'] for f in run.f3_records),rom_reads_f3=sum(f['rom_reads'] for f in run.f3_records),
        first_self_delete=next(((p['frame'],n['seq']) for p in run.pass_records for n in p['nodes'] if n['self_delete']),None),
        pass_end_digests=[p['end'] for p in run.pass_records][-3:],partial_last=bool(run.pass_records and run.pass_records[-1]['nodes'] and run.pass_records[-1]['nodes'][-1]['partial']))


def work_a(case):
    sd=SEEDS[case];snap,meta=seed_snap(sd)
    run=SeedRun(G['program'],G['fixed'],G['levels'],snap,'continuous',FRAMES_BASE,heavy=(sd['kind']=='natural'),sink=None).run()
    return summarize_a(case,sd,meta,run)


def write_blob(out_dir,digest,data):
    target=out_dir/'blobs'/(digest+'.bin')
    if target.exists():return
    tmp=out_dir/'blobs'/(digest+'.tmp%d'%os.getpid());tmp.write_bytes(data);os.replace(tmp,target)


def write_gz(path,obj):
    data=gzip.compress((stable(obj)+'\n').encode(),6,mtime=0);path.write_bytes(data);return sha(data),len(data)


def work_b(arg):
    case,plan,out_dir=arg;out_dir=Path(out_dir);sd=SEEDS[case];snap,meta=seed_snap(sd);heavy=sd['kind']=='natural'
    blobs_written=0
    run=SeedRun(G['program'],G['fixed'],G['levels'],snap,'continuous',FRAMES_BASE,heavy=heavy,sink={},plan=plan,label='B').run()
    for d,b in run.blobs.items():write_blob(out_dir,d,b);blobs_written+=1
    doc=dict(case=case,kind=sd['kind'],family=sd['family'],meta=meta,declared=run.declared,stop=run.stop,frames_done=run.frames_done,covered=run.fully_covered,passes=run.pass_records,f3=run.f3_records,
        dumps=run.dump_rows,model_rows=run.model_rows,model_mismatch=run.model_mismatch[:50])
    gz_sha,gz_size=write_gz(out_dir/'seeds'/('seed_%04d.json.gz'%case),doc)
    r=dict(case=case,f3=run.f3_records,digest=run.digest.hexdigest(),f3_digest=f3_digest(run),file='seeds/seed_%04d.json.gz'%case,file_sha256=gz_sha,file_size=gz_size,blobs=len(run.blobs),dumps=len(run.dump_rows),
        stop=run.stop,frames_done=run.frames_done)
    for tag in ('split1','split2'):
        sr=SeedRun(G['program'],G['fixed'],G['levels'],snap,'split',FRAMES_BASE,heavy=False,sink=None).run();r[tag]=sr.digest.hexdigest();r[tag+'_frames']=sr.frames_done;r[tag+'_stop']=sr.stop
    return r


# ----------------------------------------------------------------------------------
# Typed fixtures: declared host edits of captured natural states (every edit is recorded in the row)
# ----------------------------------------------------------------------------------
def apply_edits(snap,edits):
    snap=copy.deepcopy(snap);ram=bytearray(snap['ram']);done=[]
    for e in edits:
        if e['kind']=='ram':
            a,sz,v=e['address'],e['size'],e['value']
            for i,b in enumerate((v&((1<<(8*sz))-1)).to_bytes(sz,'big')):ram[(a+i)&0xffff]=b
        elif e['kind']=='bytes':
            for i,b in enumerate(e['data']):ram[(e['address']+i)&0xffff]=b
        elif e['kind']=='reg':snap['regs'][e['reg']]=e['value']&M32
        elif e['kind']=='pc':snap['pc']=e['value']
        done.append({k:(v.hex() if isinstance(v,(bytes,bytearray)) else v) for k,v in e.items()})
    snap['ram']=bytes(ram);return snap,done


def W(address,size,value,why):return dict(kind='ram',address=address,size=size,value=value,why=why)
def WB(address,data,why):return dict(kind='bytes',address=address,data=bytes(data),why=why)
def R(reg,value,why):return dict(kind='reg',reg=reg,value=value,why=why)


def run_until(program,fixed,snap,stops,limit=PASS_LIMIT):
    mach=Machine(program,fixed,snap);mach.install_basic_hooks();c=mach.cpu;out=dict(status=None,state=None)
    def at(uc,pc,size,user):
        if out['status'] is None:
            out['status']='stop';out['stop_pc']=pc;st=mach.state();st['pc']=pc;out['state']=st;uc.emu_stop()
    for pc in stops:c.hook_add(UC_HOOK_CODE,at,begin=pc,end=pc)
    try:c.emu_start(snap['pc'],0xffffff,count=limit);err=None
    except unicorn.UcError as e:err=str(e)
    if out['status'] is None:
        out['status']='guard';out['reason']=dict(odd=mach.odd,invalid=mach.invalid,fetch_unmapped=mach.fetch_unmapped,intr=mach.intr,error=err,step_limit=bool(err is None and not (mach.odd or mach.invalid or mach.intr)))
    out['ports']=list(mach.ports);out['mach']=mach;return out


class Fixtures(object):
    def __init__(self,out_dir,seeds_a):
        self.out=Path(out_dir);self.rows=[];self.a=seeds_a;self.program=G['program'];self.fixed=G['fixed'];self.levels=G['levels']
    def blob(self,data):
        d=sha(data);write_blob(self.out,d,data);return d
    def state_ref(self,st,kind):
        return dict(kind=kind,ram=self.blob(st['ram']),regs=st['regs'],pc=st['pc'],bank=list(st['bank']),state=state_blob_digest(st['ram'],st['regs'],st['pc'],st['bank']))
    def add(self,row):self.rows.append(row);return row
    def base_state(self,case,frame):
        sd=SEEDS[case];snap,meta=seed_snap(sd)
        if frame==0:return snap
        run=SeedRun(self.program,self.fixed,self.levels,snap,'continuous',frame+1,heavy=False,sink=None);run.capture_frames={frame};run.run()
        return run.captured[frame]
    def pass_fixture(self,name,snap,edits,frames,expect,declare_base=True,**kw):
        snap2,done=apply_edits(snap,edits)
        run=SeedRun(self.program,self.fixed,self.levels,snap2,'continuous',frames,heavy=False,sink={},extend=False,**{k:v for k,v in kw.items() if k=='check_head'})
        run.declare_base=declare_base
        if 'pass_limit' in kw:run.pass_limit=kw['pass_limit']
        run.run()
        for d,b in run.blobs.items():write_blob(self.out,d,b)
        last=run.pass_records[-1]
        row=dict(name=name,group='pass',edits=done,frames_done=run.frames_done,stop=run.stop,head_bad=run.head_bad,a7_bad=run.a7_bad,waits=run.pass_records[0]['waits'] if run.pass_records else [],
            nodes=[[n['a6'],n['cb'],n['depth'],n['entry'],n['exit'],n['self_delete'],n['partial']] for n in last['nodes']],start=run.pass_records[0]['start'],end=last['end'],
            dumps=run.dump_rows,digest=run.digest.hexdigest(),inserted=last['inserted'],deleted=last['deleted'])
        row['expect']=expect(run,row);row['ok']=bool(row['expect'].get('ok'))
        return self.add(row),run


def direct_entry_fixture(fx,name,base,pc,edits,why):
    """Direct callback entry (A6 = node, A7 = SPd-4 with the declared return LONG 2ac2 at A7), native run to 2ac2 compared with the independent model (final state + the per-instruction trace)."""
    snap=copy.deepcopy(base);ret=SPD-4
    snap['regs']['a7']=ret;snap['pc']=pc
    snap,done=apply_edits(snap,[W(ret,4,PASS_PC,'declared return LONG 2ac2 at A7 (the dispatcher JSR push)')]+edits)
    nat=traced_native(fx.program,fx.fixed,snap,{PASS_PC})
    mdl=Model(fx.program,snap['ram'],snap['regs'],pc,snap['bank'][0]);err=None
    try:mdl.run((PASS_PC,),trace=True)
    except ModelError as e:err=str(e)
    nm=nat['mach'];row=dict(name=name,group='direct-entry',why=why,pc=pc,edits=done,model_error=err,instructions=len(nat['trace'])-1)
    if err is None:
        row['equal']=dict(trace=nat['trace']==mdl.trace,writes=byte_events(nat['writes'])==byte_events(mdl.wlog),reads=byte_events(nat['reads'],False)==byte_events(mdl.reads,False),
            registers=tuple(mdl.r[k] for k in KEYS)==tuple(nm.regs()[k] for k in KEYS),ram=bytes(mdl.ram)==nm.ram(),ports=byte_events([(a,n,v) for k,a,n,v in nm.ports])==byte_events([(a,n,v) for k,a,n,v in mdl.ports]))
    row['ok']=err is None and all(row['equal'].values()) and nat['stopped']==PASS_PC
    row['leaders']=sorted({pc2 for pc2,_ in nat['trace'] if pc2 in LEAD_SET})
    row['entry']=dict(state=state_blob_digest(snap['ram'],snap['regs'],pc,snap['bank']))
    st=nm.state();st['pc']=PASS_PC;row['exit']=fx.state_ref(st,'direct-exit')
    return fx.add(row)


def boot_fixture(fx,name,base,a7,head_cb,why,regs=None):
    snap=copy.deepcopy(base);snap['regs']['a7']=a7;snap['pc']=0x2aac
    edits=[W(FRAME_HEAD,4,head_cb,'declared frame head callback LONG'),W(BASE_LONG,4,0,'the base LONG is written by 2ab2 (cleared so the store is observable)')]+([R(k,v,'declared initial register') for k,v in (regs or {}).items()])
    snap,done=apply_edits(snap,edits)
    rp=run_until(fx.program,fx.fixed,snap,HEAD_STOPS)
    mdl=Model(fx.program,snap['ram'],snap['regs'],0x2aac,snap['bank'][0]);err=None
    try:mdl.run(HEAD_STOPS)
    except ModelError as e:err=str(e)
    row=dict(name=name,group='boot',why=why,edits=done,model_error=err,status=rp['status'])
    if rp['status']=='stop':
        nm=rp['mach'];st=rp['state'];row['stop_pc']=rp['stop_pc']
        row['claims']=dict(base_long_equals_a7=nm.long(BASE_LONG)==a7,a6=st['regs']['a6']==FRAME_HEAD,a5=st['regs']['a5']==A5V,a0=st['regs']['a0']==rp['stop_pc'],a7_minus4=st['regs']['a7']==a7-4,
            return_long=nm.long(a7-4)==PASS_PC)
        if err is None:
            row['equal']=dict(registers=tuple(mdl.r[k] for k in KEYS)==tuple(st['regs'][k] for k in KEYS),ram=bytes(mdl.ram)==st['ram'],pc=mdl.pc==rp['stop_pc'])
        row['exit']=fx.state_ref(st,'boot-stop')
    row['ok']=rp['status']=='stop' and err is None and all(row['claims'].values()) and all(row['equal'].values())
    return fx.add(row)


def f3_child_fixture(fx,name,entry,edits,expect_status,why,limit=PASS_LIMIT,expect_pc=None):
    snap,done=apply_edits(dict(entry,pc=0x2ab8),edits)
    rp=replay_node(fx.program,fx.fixed,snap,stop_extra=tuple(sorted(TRAP_SET)),limit=limit)
    row=dict(name=name,group='f3-node',why=why,edits=done,status=rp['status'],reason=rp['reason'] if rp['status']!='2ac2' else None)
    if rp['state'] is not None:row['stop_state']=fx.state_ref(rp['state'],'f3-fixture-stop')
    ok=rp['status']==expect_status
    if expect_status=='guard' and expect_pc=='step-limit':ok=ok and bool(rp['reason'].get('step_limit'))
    if expect_status=='guard' and expect_pc=='odd':ok=ok and bool(rp['reason'].get('odd'))
    if expect_status=='trap-boundary':ok=ok and rp['reason']['pc']==expect_pc
    row['ok']=ok;row['entry']=dict(state=state_blob_digest(snap['ram'],snap['regs'],snap['pc'],snap['bank']))
    return fx.add(row)


def fixture_suite(fx,a_results):
    base100=fx.base_state(100,0)
    # ---- idle callback 270e: direct entries compared with the model
    idle=0x1009a8
    direct_entry_fixture(fx,'270e-depth0',base100,0x270e,[R('a6',idle,'node'),R('a5',A5V,'A5'),W(idle+0x10,2,0,'depth 0 (static idle node)')],'depth 0: nothing written')
    direct_entry_fixture(fx,'270e-zombie',base100,0x270e,[R('a6',0x100f5c,'pool node'),R('a5',A5V,'A5'),W(0x100f5c+0x10,2,2,'depth 2 (zombie node)'),W(0x104ca2,2,7,'zombie counter 7')],'depth <> 0: 104ca2 + 1')
    direct_entry_fixture(fx,'270e-zombie-wrap',base100,0x270e,[R('a6',0x100f5c,'pool node'),R('a5',A5V,'A5'),W(0x100f5c+0x10,2,1,'depth 1'),W(0x104ca2,2,0xffff,'zombie counter ffff')],'WORD wrap ffff -> 0')
    direct_entry_fixture(fx,'270e-a5-relative',base100,0x270e,[R('a6',0x100f5c,'pool node'),R('a5',A5V+0x100,'A5 108100'),W(0x100f5c+0x10,2,1,'depth 1'),W(0x104da2,2,0x00ff,'counter at -335e(A5) = 104da2'),W(0x104ca2,2,5,'counter at 104ca2 must stay')],'A5-relative address: -335e(A5)')
    # ---- boot 2aac
    boot_fixture(fx,'boot-2aac-e4a',base100,0x1ff800,0xe4a,'2aac: LEA 100820,A6; MOVE.L A7,104ca4; dispatcher; first dispatch enters the frame head callback e4a (stop)',regs={'a0':0x11111111,'d3':0x33333333})
    boot_fixture(fx,'boot-2aac-e74',base100,0x1fef00,0xe74,'same with the frame head callback e74')
    # ---- passes
    static=[W(0x100b30,4,0x270e,'controller node callback := idle 270e (the natural 47af0 is removed)'),W(0x100bf4,4,0x270e,'event node callback := idle 270e (the natural e9150 is removed)')]
    def ex_static(run,row):
        cbs=[n[1] for n in row['nodes']];last=run.pass_records[-1];c=[('six idle nodes then the frame head stop',cbs==[0x270e]*6 and run.stop['reason']=='frame-limit'),('head regs checked by the run (A6/A5/A7/return LONG/A0)',run.head_bad==0),('a7 at dispatcher entry',run.a7_bad==0)]
        return dict(ok=all(v for _,v in c),checks=dict(c))
    fx.pass_fixture('pass-static8',base100,static,1,ex_static)
    def ex_e74(run,row):
        c=[('stops at e74',run.stop['reason']=='frame-limit' and run.end_pcs==[0xe74]),('six idle nodes',[n[1] for n in row['nodes']]==[0x270e]*6)]
        return dict(ok=all(v for _,v in c),checks=dict(c))
    fx.pass_fixture('pass-static8-head-e74',base100,static+[W(FRAME_HEAD,4,0xe74,'frame head callback LONG := e74')],1,ex_e74)
    def ex_rej(run,row):
        c=[('host rejects the frame head callback before any execution',run.stop['reason']=='frame-head-callback-rejected' and run.stop.get('callback')==0x270e)]
        return dict(ok=all(v for _,v in c),checks=dict(c))
    fx.pass_fixture('pass-head-callback-rejected',base100,static+[W(FRAME_HEAD,4,0x270e,'frame head callback LONG := 270e (neither e4a nor e74)')],1,ex_rej)
    def ex_ring(run,row):
        c=[('unchecked: the frame head is an ordinary node, the ring reaches the controller node 1008e4 whose body is skipped by the declared model (the host stops there)',run.stop['reason']=='controller-node-visited')]
        return dict(ok=all(v for _,v in c),checks=dict(c))
    fx.pass_fixture('pass-head-ring-unchecked-step-limit',base100,static+[W(FRAME_HEAD,4,0x270e,'frame head callback LONG := 270e')],1,ex_ring,check_head=False,pass_limit=200000)
    # ---- gate wait
    def ex_gate(run,row):
        w=row['waits'];c=[('declared wait at the 72f0 gate',len(w)==1 and w[0]['kind']=='palette-gate' and w[0]['pc']==0x47af0),('released (BYTE 107ded bit7 cleared) and the pass continued to the frame head stop',run.stop['reason']=='frame-limit'),('node order unchanged',[n[1] for n in row['nodes']][:4]==[0x270e,0x270e,0x47af0,0xe9150])]
        return dict(ok=all(v for _,v in c),checks=dict(c))
    byte107ded=base100['ram'][0x7ded]
    fx.pass_fixture('pass-gate-wait-released',base100,[W(0x107ded,1,byte107ded|0x80,'BYTE 107ded bit7 set: the 72f0 palette gate is closed')],1,ex_gate)
    def ex_gate_stuck(run,row):
        c=[('WORD 107dea <> 0: the original IRQ path does not clear bit7; the declared release is empty and the pass is given up',run.stop['reason']=='wait-not-released')]
        return dict(ok=all(v for _,v in c),checks=dict(c))
    fx.pass_fixture('pass-gate-wait-not-released',base100,[W(0x107ded,1,byte107ded|0x80,'gate closed'),W(0x107dea,2,1,'WORD 107dea <> 0')],1,ex_gate_stuck)
    # ---- dispatcher base LONG 104ca4 (self delete restores A7 from it)
    sd_case=min((a['case'] for a in a_results if a['kind']=='natural' and a['covered'] and a['first_self_delete'] is not None),default=None)
    if sd_case is not None:
        frame=[a for a in a_results if a['case']==sd_case][0]['first_self_delete'][0]
        base=fx.base_state(sd_case,frame)
        def ex_ok(run,row):
            c=[('a node self deletes (2a00) and the pass reaches the frame head stop',any(n[5] for n in row['nodes']) and run.stop['reason']=='frame-limit'),('A7 restored from 104ca4: head regs ok',run.head_bad==0)]
            return dict(ok=all(v for _,v in c),checks=dict(c))
        fx.pass_fixture('pass-self-delete-base-long-spd',base,[],1,ex_ok)
        def ex_zero(run,row):
            c=[('LONG 104ca4 = 0: 2a02 loads A7 = 0 and the next JSR push (fffffc) is outside the RAM: invalid access',run.stop['reason']=='invalid-memory-access' and run.stop.get('address') in (0xfffffffc,0xfffffc))]
            return dict(ok=all(v for _,v in c),checks=dict(c))
        fx.pass_fixture('pass-self-delete-base-long-zero',base,[W(BASE_LONG,4,0,'LONG 104ca4 := 0 (not SPd)')],1,ex_zero,declare_base=False)
        def ex_off(run,row):
            c=[('LONG 104ca4 = SPd-0x20: the pass ends with A7 <> SPd-4 (the host refuses: head regs check fails)',run.head_bad==1 and run.stop['reason']=='frame-limit')]
            return dict(ok=all(v for _,v in c),checks=dict(c))
        fx.pass_fixture('pass-self-delete-base-long-offset',base,[W(BASE_LONG,4,SPD-0x20,'LONG 104ca4 := SPd-0x20')],1,ex_off,declare_base=False)
    # ---- F3 child thread fixtures (TRAP boundary, step limit, odd access) from a captured natural child entry
    child=min(((a['case'],f[0],f[1]) for a in a_results if a['kind']=='natural' for f in a['f3_keys'] if f[2]==0xe9362),default=None)
    if child is not None:
        case,frame,seq=child;snap,meta=seed_snap(SEEDS[case])
        run=SeedRun(fx.program,fx.fixed,fx.levels,snap,'continuous',frame+1,heavy=False,sink=None);run.capture_nodes={(frame,seq)};run.run()
        entry=run.captured_nodes[(frame,seq)]['entry'];a6=entry['regs']['a6'];scratch=0x10ef00
        base_edits=[W(a6+0x7a,4,0,'+7a condition pointer := 0 (skip the WORD / expression checks)'),W(a6+0x76,4,scratch,'+76 stream pointer := scratch'),R('a5',A5V,'A5')]
        pos=lambda b:WB(scratch,bytes(b),'declared event stream bytes')
        f3_child_fixture(fx,'f3-child-trap-op02',entry,base_edits+[pos([0x02,0,0,0,0,0])],'trap-boundary','child opcode 02 (<5): TRAP #15 at e93d8 is a stop boundary, never executed',expect_pc=0xe93d8)
        f3_child_fixture(fx,'f3-child-loop-op10',entry,base_edits+[pos([0x10,0,0,0,0,0])],'guard','child opcode 10: e94fe returns, the pointer is saved and e93a8 repeats forever (no terminator)',limit=300000,expect_pc='step-limit')
        odd_edits=[W(a6+0x7a,4,0,'+7a := 0'),W(a6+0x7e,2,0,'+7e wait counter := 0 (opcode 06 loads it from the WORD operand)'),W(a6+0x76,4,scratch+1,'+76 := odd scratch address'),WB(scratch+1,[6,0,0,0,0,0],'opcode 06 at an odd address: its WORD operand 2(op) is read at an odd address'),R('a5',A5V,'A5')]
        f3_child_fixture(fx,'f3-child-odd-operand',entry,odd_edits,'guard','opcode 06 at an odd address: WORD read at an odd address (address error on the original CPU)',expect_pc='odd')
        fx.child_source=dict(case=case,frame=frame,seq=seq)
    return fx.rows


# ----------------------------------------------------------------------------------
# Aggregation, contract claims, main
# ----------------------------------------------------------------------------------
CONTRACT_FULL_8=(50,51,100,101,106,107,110,111)
CONTRACT_FULL_22=tuple(sorted(CONTRACT_FULL_8+(4,5,10,11,48,49,64,65,66,67,78,79,86,87)))
IDX_EXPECTED={0xe91ba:{0:7622,4:880,8:20,0x10:14,0x14:400,0x1c:21},0xe9534:{0:483,4:14},0xe93f2:{0:180,4:514},0xe97e0:{4:None,8:None,0x2c:None,0x58:None,0x5c:None,0x60:None,0x64:None,0x68:None,0x80:None}}


def merge_counters(items):
    out=collections.Counter()
    for d in items:
        for k,v in d.items():out[k]+=v
    return out


def stop_category(a):
    st=a['stop'];r=st['reason']
    if r=='invalid-memory-access':
        if st.get('kind')=='bank':return 'unsupported-bank-mapping'
        if st.get('access')=='write-protected':return 'write-to-program-ROM'
        return 'invalid-memory-access:'+str(st.get('access'))
    return r


GUARD_TEXT={
    'write-to-program-ROM':'a store to the program ROM (0..fffff) stops the run: a game object callback calls the RNG 49a58 whose ring pointer LONG 10d722 was never initialized in the seed (49a1a not executed); the original hardware would ignore the write, the F1c rule (RNG pointer outside the RAM = checked error) treats it as an error',
    'unsupported-bank-mapping':'a PVC bank write selects a bank base other than the modeled 200000 / 300000',
    'bios-boundary':'JSR c00468 (BIOS card request, c376): the BIOS body is never executed, the run stops at the fetch',
    'fetch-unmapped':'an instruction fetch at an unmapped address (callback LONG deadbeef = odd JSR target, an address error on the real CPU)',
    'odd-pc':'a control transfer to an odd PC (47c05): an address error on the real 68000',
    'odd-data-access':'a WORD / LONG access at an odd address (address error on the real 68000)',
    'trap-boundary':'a F3b TRAP #15 boundary reached (not executed)',
    'step-limit':'the declared instruction watchdog expired (the original code has no bound)',
    'wait-not-released':'a declared wait whose declared release does not unblock it',
    'cpu-exception':'a CPU exception (illegal instruction / TRAP) was raised',
    'frame-head-callback-rejected':'LONG (100820) is neither e4a nor e74: the host refuses the pass before executing it',
    'controller-node-visited':'the dispatcher reached the controller node 1008e4 whose body is skipped by the declared model',
}


def claim(cid,source,text,expected,observed,verdict,note=''):
    return dict(id=cid,source=source,claim=text,expected=expected,observed=observed,verdict=verdict,note=note)


def build_claims(natural,guards,allrows,fixtures,tool_facts,levels):
    out=[]
    cmp=lambda e,o:'confirmed' if e==o else 'differs'
    short=lambda rows:sorted((a['case'],stop_category(a),a['frames_complete']) for a in rows if a['frames_complete']<FRAMES_BASE and a['stop']['reason'] not in ('frame-limit',) and not (a['stop']['reason']=='bios-boundary' and a['frames_complete']>=FRAMES_BASE))
    done120=[a for a in allrows if a['frames_complete']>=FRAMES_BASE]
    early=[a for a in allrows if a['frames_complete']<FRAMES_BASE]
    cats=collections.Counter(stop_category(a) for a in early)
    out.append(claim('F2-1','F2 요약 / 자연 시작 상태','Unicorn frame pass probe, 142 seeds x 120 frames: 134 seeds complete 120 frames','134',len(done120),cmp(134,len(done120)),
        'this tool checks ROM writes (the program ROM is write-protected, an OS-visible guard like the F1c RNG pointer rule) and odd PCs; the scratch probe mapped the ROM writable. Early stops (all rows): %s'%dict(cats)))
    out.append(claim('F2-2','F2 자연 시작 상태','5 seeds deadbeef (wholebody-sound-wait release outputs, odd JSR at frame 0)','5',sum(1 for a in guards if a['stop']['reason']=='fetch-unmapped' and a['stop'].get('address')==0xdeadbeef),
        cmp(5,sum(1 for a in guards if a['stop']['reason']=='fetch-unmapped' and a['stop'].get('address')==0xdeadbeef))))
    bios_early=[a['case'] for a in allrows if a['stop']['reason']=='bios-boundary' and a['frames_complete']<FRAMES_BASE]
    out.append(claim('F2-3','F2 자연 시작 상태','2 seeds reach BIOS c00468 inside 120 frames','2',len(bios_early),cmp(2,len(bios_early)),'cases %s'%bios_early))
    oddpc=[a['case'] for a in allrows if a['stop']['reason']=='odd-pc']
    out.append(claim('F2-4','F2 자연 시작 상태','1 seed (case 141) odd PC 47c05 exception','[141]',oddpc,cmp([141],oddpc)))
    out.append(claim('F2-5','F2 자연 시작 상태','at dispatcher entry A7 <> SPd: 0, Waiting stops: 0, declared host writes: 0 (beyond the declared 104ca4 / SPd)','0/0',
        '%d/%d'%(sum(a['a7_bad'] for a in allrows),sum(sum(a['waits'].values()) for a in allrows)),cmp('0/0','%d/%d'%(sum(a['a7_bad'] for a in allrows),sum(sum(a['waits'].values()) for a in allrows)))))
    full0=sorted(a['case'] for a in natural if a['covered0'] and a['frames_complete']>=FRAMES_BASE)
    full=sorted(a['case'] for a in natural if a['covered'] and a['frames_complete']>=FRAMES_BASE)
    out.append(claim('F2-6','F2 자연 시작 상태','8 seeds whose every pass is inside the executors (F1a F1b F1c F3a F2 without 4fcce): cases 50 51 100 101 106 107 110 111','%s'%list(CONTRACT_FULL_8),full0,cmp(sorted(CONTRACT_FULL_8),full0),
        'covered = every callback PC of every pass is an executor entry of the declared level (entry routability, the contract method); routing = committed engine/src/animation_machine.cpp'))
    out.append(claim('F2-7','F2 자연 시작 상태','with the 4fcce child: 22 seeds (14 more)','%s'%list(CONTRACT_FULL_22),full,cmp(sorted(CONTRACT_FULL_22),full)))
    lim={a['case']:(a['frames_complete'],a['stop']['reason']) for a in natural if a['case'] in CONTRACT_FULL_22}
    exp_frames={c:(400 if c in (100,101,106,107,110,111) else 240 if c in (50,51) else 244) for c in CONTRACT_FULL_22}
    got_frames={c:lim.get(c,(None,None))[0] for c in CONTRACT_FULL_22}
    out.append(claim('F2-8','F2 요약 / 검증 조건','frame counts of the 22 seeds: 400 (6 seeds), 240 (cases 50 51, BIOS c00468), 244 (14 seeds, BIOS c00468)',exp_frames,got_frames,cmp(exp_frames,got_frames)))
    c120=merge_counters(a['cb120'] for a in allrows)
    zombie=sum(a['idle120'].get('zombie',0) for a in allrows);static=sum(a['idle120'].get('static',0) for a in allrows)
    out.append(claim('F2-9','F2 node 구조','270e executions in 120 frames: 70,154 (static 69,638, zombie 516)',[70154,69638,516],[c120[0x270e],static,zombie],cmp([70154,69638,516],[c120[0x270e],static,zombie])))
    f3c=[c120[x] for x in (0xe9150,0xe9176,0xe9350,0xe9362)]
    out.append(claim('F3-1','F3 자연 시작 상태','node executions in 120 frames: e9150 134, e9176 11,358, e9350 14, e9362 662',[134,11358,14,662],f3c,cmp([134,11358,14,662],f3c)))
    f0=[(f[2],f[3]) for a in natural for f in a['f3_keys'] if f[0]==0 and f[2]==0xe9150]
    f3b_set=set(levels['f3b_starts'])|{F3_SPLIT_PC}
    touch=sum(1 for cb,lead in f0 if set(lead)&f3b_set)
    out.append(claim('F3-2','F3 요약','e9150 at frame 0: 134 (39 touch only F3a blocks, 95 reach F3b)',[134,39,95],[len(f0),len(f0)-touch,touch],cmp([134,39,95],[len(f0),len(f0)-touch,touch])))
    e94=sum(a['f3_e94fe120'] for a in natural)
    out.append(claim('F3-3','F3 검증 조건','executions reaching e94fe (F3a stop) in 120 frames: 101',101,e94,cmp(101,e94),'frames < 120; over all frames (400-frame seeds included): %d'%sum(a['f3_e94fe'] for a in natural)))
    traps=tool_facts['trap_hits']
    out.append(claim('F3-4','F3 TRAP 경계','TRAP boundaries reached in the natural replay: 0',0,traps,cmp(0,traps)))
    hit120=merge_counters(a['leader120'] for a in natural)
    f3a=[x for x in levels['f3a_starts'] if hit120[x]];f3bb=[x for x in levels['f3b_starts'] if hit120[x]]
    out.append(claim('F3-5','F3 자연 시작 상태','reached blocks (120 frames): F3a 86/134, F3b 55/109',[86,55],[len(f3a),len(f3bb)],cmp([86,55],[len(f3a),len(f3bb)])))
    br=sum(a['bank_reads_f3'] for a in natural)
    out.append(claim('F3-6','F3 결정 8','banked window reads by F3 nodes: 0',0,br,cmp(0,br)))
    idx={}
    for a in natural:
        for pc,d in a['index120'].items():
            for v,n in d.items():idx.setdefault(pc,collections.Counter())[v]+=n
    for pc,exp in IDX_EXPECTED.items():
        obs=dict(idx.get(pc,{}))
        if exp.get(4,0) is None or all(v is None for v in exp.values()):
            out.append(claim('F3-7-%x'%pc,'F3 자연 시작 상태','computed-PC index set at %x: %s'%(pc,sorted(exp)),sorted(exp),sorted(obs),cmp(sorted(exp),sorted(obs))))
        else:out.append(claim('F3-7-%x'%pc,'F3 자연 시작 상태','computed-PC index distribution at %x'%pc,exp,obs,cmp(exp,obs)))
    full_tb=max((a['max_tbs'] for a in natural if a['case'] in CONTRACT_FULL_22),default=0);all_tb=max(a['max_tbs'] for a in natural)
    out.append(claim('F2-10','F2 block budget','max Unicorn TBs per pass: 191,890 (long tail seed), <= 5,510 for the 22 seeds',[191890,5510],[all_tb,full_tb],'informational','TB counts are Unicorn translation blocks of this tool (all frames up to the run limit; the 400-frame seeds included)'))
    order=sum(1 for a in natural if a['first_order_ok'])
    out.append(claim('F2-11','F2 node 구조','first pass order 1009a8 100a6c 100b30 ... 100bf4 ... 100cb8 100da8 then the frame head',len(natural),order,cmp(len(natural),order)))
    prior=sum(1 for a in allrows if a['meta']['prior_104ca4']==0)
    out.append(claim('F2-12','F2 node 구조','recorded seed RAMs: LONG 104ca4 = 0',len(allrows),prior,cmp(len(allrows),prior)))
    sl=[a['meta']['static_list'] for a in allrows]
    ok_sl=sum(1 for x in sl if x['ring_ok'] and x['parent_zero'] and x['callbacks'][0]=='e4a' and x['callbacks'][1]=='c52a' and x['callbacks'][2]=='270e' and x['callbacks'][3]=='270e' and x['callbacks'][6]=='270e' and x['callbacks'][7]=='270e')
    out.append(claim('F2-13','F2 node 구조','static list: 100820 e4a, 1008e4 c52a, ring of 8 nodes, 1009a8 100a6c 100cb8 100da8 = 270e',len(allrows),ok_sl,cmp(len(allrows),ok_sl)))
    ins=sum(a['inserted_passes'] for a in natural);rev=sum(a['revisit_passes'] for a in natural)
    out.append(claim('F2-14','F2 node list','children inserted by 28ae execute in the same pass; a freed slot can be reallocated and visited twice in one pass (1013f4 d7828 -> bb188)','>0',dict(inserted_passes=ins,slot_revisit_passes=rev),'confirmed' if ins>0 and rev>0 else 'differs'))
    prog=G['program'];table=[int.from_bytes(prog[0x268a+16*i:0x268a+16*i+4],'big') for i in range(8)];cbs=[int.from_bytes(prog[0x268a+16*i+4:0x268a+16*i+8],'big') for i in range(8)]
    gaps=[table[i+1]-table[i] for i in range(7)]
    note='seeds stopped before 120 complete frames: %d of %d (%s)'%(len(early),len(allrows),dict(cats))
    for c in out:
        if c['verdict']=='differs' and c['id'] not in ('F2-15',):c['note']=(c['note']+' | ' if c['note'] else '')+note
    out.append(claim('F2-15','F2 node 구조','static nodes: 8 nodes from 100820 with spacing c4, last 100da8 (init table 268a..270e)',dict(nodes=['%x'%x for x in table],gaps=['c4']*7),dict(nodes=['%x'%x for x in table],gaps=['%x'%g for g in gaps],callbacks=['%x'%c for c in cbs]),
        cmp(['c4']*7,['%x'%g for g in gaps]),'the node size is c4 and the first seven static nodes are c4 apart, but 100da8 is f0 after 100cb8 (100cb8 + c4 = 100d7c is not a node); cosmetic, the list itself is as documented'))
    return out


def hexkeys(d):return {('%x'%k if isinstance(k,int) else str(k)):v for k,v in sorted(d.items(),key=lambda kv:str(kv[0]))}


def tool_pins():
    pins={}
    for name in ('observe_animation_machine_scheduler.py',)+IMPORTED_TOOLS:pins['tools/'+name]=sha((ROOT/'tools'/name).read_bytes())
    for path in (F2_CONTRACT,F3_CONTRACT,F1A_CONTRACT,F1B_CONTRACT,F1C_CONTRACT,ROUTING_SRC,SEED_OBS):pins[str(path.relative_to(ROOT))]=sha(path.read_bytes())
    return pins


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(OUT));ap.add_argument('--workers',type=int,default=3);ap.add_argument('--cases',default='');ap.add_argument('--no-fixtures',action='store_true')
    args=ap.parse_args(argv);out_dir=Path(args.out).resolve();t0=time.time()
    rom_start=rom_stat();assert rom_start['sha256']==ROM_SHA
    assert sha(F2_CONTRACT.read_bytes())==F2_SHA and sha(F3_CONTRACT.read_bytes())==F3_SHA
    if out_dir.exists() and any(out_dir.iterdir()):raise SystemExit('output directory is not empty: %s'%out_dir)
    (out_dir/'blobs').mkdir(parents=True,exist_ok=True);(out_dir/'seeds').mkdir(exist_ok=True)
    setup();load_seeds();pins=tool_pins()
    cases=sorted(SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    ctx=multiprocessing.get_context('fork')
    with ctx.Pool(args.workers) as pool:
        a_list=pool.map(work_a,cases,chunksize=1)
        a_by={a['case']:a for a in a_list}
        # global first covering F3 executions (leaders / computed-PC index values) get node-level dumps
        first={}
        for a in a_list:
            if a['kind']!='natural':continue
            for frame,seq,cb,leaders,idx in a['f3_keys']:
                for key in [('L',pc) for pc in leaders]+[('I',pc,v) for pc,v in idx]:
                    ident=(a['case'],frame,seq)
                    if key not in first or ident<first[key]:first[key]=ident
        plan=collections.defaultdict(set)
        for (case,frame,seq) in first.values():plan[case].add((frame,seq))
        b_list=pool.map(work_b,[(c,frozenset(plan.get(c,())),str(out_dir)) for c in cases],chunksize=1)
    b_by={b['case']:b for b in b_list}
    f3_index=[]
    for c in cases:
        for f in b_by[c]['f3']:f3_index.append(dict(case=c,**f))
    f3_file_sha,f3_file_size=write_gz(out_dir/'f3_node_seeds.json.gz',dict(note='F3 decision 10 node seeds: entry state = state at 2abe with PC replaced by 2ab8 (A6 = node, A7 = SPd 1ff000, LONG 104ca4 = SPd), expected state = 2ac2; e94fe = fresh-CPU stop state before e94fe (F3a/F3b boundary); dumps reference blobs/<sha>.bin',records=f3_index))
    for b in b_list:b.pop('f3')
    natural=[a_by[c] for c in cases if a_by[c]['kind']=='natural'];guards=[a_by[c] for c in cases if a_by[c]['kind']!='natural'];allrows=natural+guards
    # run comparisons
    seed_rows=[]
    for c in cases:
        a=a_by[c];b=b_by[c]
        eq=dict(continuous_twice=a['digest']==b['digest'] and a['f3_digest']==b['f3_digest'],split_first=a['digest']==b['split1'],split_second=a['digest']==b['split2'],
            frames=b['split1_frames']==a['frames_done']==b['frames_done'],stop=b['split1_stop']==a['stop']==b['stop'])
        assert all(eq.values()),(c,eq)
        seed_rows.append(dict(case=c,kind=a['kind'],family=a['family'],bank=a['bank'],stop=a['stop'],stop_category=stop_category(a),frames_complete=a['frames_complete'],frames_done=a['frames_done'],covered_level_A=a['covered'],covered_level_A_without_4fcce=a['covered0'],
            run_digest=a['digest'],equal=eq,file=b['file'],file_sha256=b['file_sha256'],file_size=b['file_size'],dumps=b['dumps'],blobs=b['blobs'],max_tbs=a['max_tbs'],max_nodes=a['max_nodes'],
            waits=a['waits'],inserted_passes=a['inserted_passes'],deleted_passes=a['deleted_passes'],revisit_passes=a['revisit_passes'],self_delete_nodes=a['self_delete_nodes'],f3={('%x/%s/%s/%s'%(k[0],k[1],k[2],k[3])):v for k,v in a['f3_summary'].items()},
            model={('%x/%s/%s/%s'%k):v for k,v in a['model_count'].items()},pass_end_tail=a['pass_end_digests'],seed_meta=a['meta']))
    # fixtures
    fixture_rows=[]
    if not args.no_fixtures:
        fx=Fixtures(out_dir,a_list);fixture_rows=fixture_suite(fx,a_list)
    # aggregates
    levels=G['levels']
    fixture_leaders=set()
    for r in fixture_rows:
        if r.get('group')=='direct-entry' and r['ok']:fixture_leaders.update(r['leaders'])
        if r.get('group')=='boot' and r['ok']:fixture_leaders.add(0x2aac)
    trap_hits=sum(1 for a in allrows if a['stop']['reason']=='trap-boundary')
    leader_all=merge_counters(a['leader_hits'] for a in natural);leader120=merge_counters(a['leader120'] for a in natural)
    f2_cov={('%x'%pc):dict(hits=leader_all.get(pc,0),hits_120=leader120.get(pc,0),typed_fixture=pc in fixture_leaders) for pc in F2_LEADERS}
    f3a_cov={('%x'%pc):dict(hits=leader_all.get(pc,0),hits_120=leader120.get(pc,0)) for pc in levels['f3a_starts']}
    f3b_cov={('%x'%pc):dict(hits=leader_all.get(pc,0),hits_120=leader120.get(pc,0)) for pc in levels['f3b_starts']}
    cb_all=merge_counters(a['cb_counts'] for a in allrows);cb120=merge_counters(a['cb120'] for a in allrows)
    idx_all={}
    for a in natural:
        for pc,d in a['index_hits'].items():
            for v,n in d.items():idx_all.setdefault(pc,collections.Counter())[v]+=n
    idx_tbl={('%x'%pc):{('%x'%v):n for v,n in sorted(d.items())} for pc,d in sorted(idx_all.items())}
    model_total=collections.Counter()
    for a in natural:
        for k,v in a['model_count'].items():model_total[(k[0],k[1],k[2],k[3])]+=v
    f3_total=collections.Counter()
    for a in natural:
        for k,v in a['f3_summary'].items():f3_total[k]+=v
    mism=[m for a in natural for m in a['model_mismatch']]
    tool_facts=dict(trap_hits=trap_hits)
    claims=build_claims(natural,guards,allrows,fixture_rows,tool_facts,levels)
    discrepancies=[dict(id=c['id'],claim=c['claim'],expected=c['expected'],observed=c['observed'],note=c['note']) for c in claims if c['verdict']=='differs']
    for m in mism:discrepancies.append(dict(id='native-vs-model-or-replay',detail=m))
    for r in fixture_rows:
        if not r['ok']:discrepancies.append(dict(id='fixture-expectation',name=r['name'],detail={k:r.get(k) for k in ('expect','equal','claims','status','reason','model_error')}))
    # guards: explicit reasons
    guard_rows=[dict(case=r['case'],kind=r['kind'],family=r['family'],category=r['stop_category'],explanation=GUARD_TEXT.get(r['stop_category'],GUARD_TEXT.get(r['stop']['reason'],'')),stop=r['stop'],frames_complete=r['frames_complete']) for r in seed_rows if r['stop']['reason']!='frame-limit']
    guard_summary=collections.Counter(g['category'] for g in guard_rows)
    f3_nodes=sum(f3_total.values());f3_ok=sum(v for k,v in f3_total.items() if k[1]=='2ac2' and k[2] and k[3])
    sizes=dir_sizes(out_dir)
    rom_end=rom_stat();assert rom_end==rom_start,(rom_start,rom_end)
    report=dict(schema_version=1,tool='tools/observe_animation_machine_scheduler.py',tool_sha256=pins['tools/observe_animation_machine_scheduler.py'],scope=SCOPE_TEXT,inputs=pins,rom_stat_start=rom_start,rom_stat_end=rom_end,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library_sha256=sha(Path(uclib._name).read_bytes())),
        declared_model=dict(spd=SPD,base_long=BASE_LONG,pass_input=dict(pc=PASS_PC,a6=CONTROLLER,a7=SPD,sr='2000 (CCR 0, never read)'),stop='first instruction of the frame head callback LONG (100820): e4a or e74',skipped=['frame head e4a/e74 (everything)','controller c52a/c66a (everything)'],
            frames_base=FRAMES_BASE,frames_full=FRAMES_FULL,pass_limit=PASS_LIMIT,wait_limit=WAIT_LIMIT,wait_release=dict(sound='WORD 104d74 := ffff',sprite='WORD 108d34 := D4.W',gate='BYTE 107ded bit7 cleared unless WORD 107dea <> 0')),
        levels=dict(counts=levels['counts'],definition='entry routability of a callback PC: A = engine/src/animation_machine.cpp routing entries + F1a + F1b + F1c + F2 (4 blocks + 4fcce) + F3a contract code ranges; B = A + F3b; A0 = A without the 4fcce ranges'),
        seeds=seed_rows,guards=guard_rows,guard_summary=dict(guard_summary),
        totals=dict(seeds=len(cases),natural=len(natural),guard_rows=len(guards),passes=sum(r['frames_done'] for r in seed_rows),complete_passes=sum(r['frames_complete'] for r in seed_rows),
            node_visits=sum(cb_all.values()),fully_covered_level_A=sorted(a['case'] for a in natural if a['covered'] and a['frames_complete']>=FRAMES_BASE),fully_covered_without_4fcce=sorted(a['case'] for a in natural if a['covered0'] and a['frames_complete']>=FRAMES_BASE),
            a7_bad=sum(a['a7_bad'] for a in allrows),head_bad=sum(a['head_bad'] for a in allrows),waits=hexkeys(merge_counters(a['waits'] for a in allrows))),
        callbacks=dict(all_frames=hexkeys(cb_all),first_120_frames=hexkeys(cb120)),
        f2_blocks=f2_cov,f3a_blocks=f3a_cov,f3b_blocks=f3b_cov,f3_index_values=idx_tbl,
        f3_node_replay=dict(executions=f3_nodes,exit_and_ports_equal=f3_ok,by_class={('%x/%s/%s/%s'%k):v for k,v in sorted(f3_total.items())}),
        model_compare={('%x/%s/%s/ok=%s'%k):v for k,v in sorted(model_total.items())},model_mismatches=mism[:50],
        fixtures=fixture_rows,f3_node_seed_index=dict(file='f3_node_seeds.json.gz',sha256=f3_file_sha,size=f3_file_size,records=len(f3_index),with_dumps=sum(1 for f in f3_index if 'dumps' in f),by_callback=hexkeys(collections.Counter(f['cb'] for f in f3_index))),claims=claims,contract_discrepancies=discrepancies,output_sizes=sizes,
        limitations=LIMITATIONS)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(seeds=len(cases),natural=len(natural),guards=len(guards),passes=report['totals']['passes'],node_visits=report['totals']['node_visits'],covered=len(report['totals']['fully_covered_level_A']),
        f3_replays=f3_nodes,f3_ok=f3_ok,model=dict((k,v) for k,v in report['model_compare'].items()),fixtures=len(fixture_rows),fixtures_ok=sum(1 for r in fixture_rows if r['ok']),discrepancies=len(discrepancies),
        size_mb=round(sizes['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True))
    return summary


def dir_sizes(out_dir):
    total=0;files=0;blobs=0;blob_bytes=0
    for p in sorted(out_dir.rglob('*')):
        if p.is_file() and p.name!='observation.json':
            n=p.stat().st_size;total+=n;files+=1
            if p.parent.name=='blobs':blobs+=1;blob_bytes+=n
    return dict(files=files,total_bytes=total,blobs=blobs,blob_bytes=blob_bytes)


SCOPE_TEXT=('Native Unicorn M68000 observation of the original ROM.  The frame pass is a declared model (pass input PC 2ac2 / A6 1008e4 / A7 SPd 1ff000 / SR 2000, stop at the frame head callback entry, '
    'frame head and controller bodies skipped, declared waits) - it is not natural game execution: no BIOS execution, no natural IRQ, no natural scheduler is claimed.  The ROM is never modified; '
    'no ROM or extracted data is added to Git.  The 137 stage_entry_body begin outputs are the natural seeds; the 5 release outputs are guard rows (100b30 = deadbeef).')
LIMITATIONS=[
    'Coverage classification is by callback entry PC (the contract method); the executors own their internal blocks, so a covered node is not proof that every internal block is already routed.',
    'The program ROM is write-protected in this tool: a store to 0..fffff stops the pass (the F1c rule "RNG pointer outside the RAM = checked error"); the scratch probe of the F2/F3 contracts mapped the ROM writable.',
    'Bank mapping is limited to bank bases 200000 / 300000 (the modeled bases of the earlier observers); other PVC bank values are a guard.',
    'Odd instruction fetches are detected at translation-block starts; odd data accesses (WORD/LONG) by memory hooks.  Real 68000 address errors are not emulated beyond stopping at them.',
    'Sound ring (3aea) and sprite queue (cda4) waits are detected and released by declared host writes but no natural seed reaches them in a pass; they are not exercised by a typed fixture.',
    'CCR is never read; every pass start declares SR 2000.  A callback that depended on the incoming CCR would show up as a fresh-CPU replay mismatch (none observed if the replay counts are equal).',
    '104ca2 (zombie counter) is never cleared in the declared pass (e74 f1e and 2848 are skipped); its consumers are not analysed here.',
]


if __name__=='__main__':main()
