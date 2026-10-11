"""PVC bank mapping for every bank the MAME formula can produce: F2 frame-pass native observation of the two U06 seeds (58, 59) plus typed eb7b6 / eba3e fixtures.

Native Unicorn M68000 observation of the original ROM (never modified).  This tool IMPORTS tools/observe_animation_machine_scheduler.py (never edits it) and replaces its
`Machine` class (module attribute `Machine`, looked up by SeedRun / replay_node at call time) with `PvcMachine`.  Everything else of the memory map is kept as the scheduler's:
fixed program ROM 0..fffff mapped read-only (a store stops the pass), work RAM 100000..10ffff mirrored 16 times, the PVC page 2fe000..2fffff (only the WORD writes 2ffff0 / 2ffff2
are accepted, every other PVC page write is a guard), the device windows 300000 / 3c0000 / d00000, the declared frame-pass protocol (F2) and its declared waits.

What changes is only the banked window 200000..2fdfff.  Scheduler Machine: the window holds program[base:base+fe000] for base 200000 / 300000 and a PVC write that selects any other
base is a guard ("unsupported-bank-mapping").  PvcMachine: base = 100000 + ((ff8 >> 8) | (ff9 << 8)) after every 2ffff0 / 2ffff2 WORD write (MAME prot_pvc.cpp get_bank_base, with the
two register side effects ff8 = (ff8 & fe00) | a0, ff9 &= 7fff) selects ANY base; the window shows the physical program ROM bytes base .. base + fe000 - 1 of the canonical 8 MiB BE
image.  The bank is an address range, not a mapped resource: a base that selects bytes outside the 8 MiB image is not a write-time guard (the C++ program bus checks at READ time:
"reached program bank physical span outside ROM"), it is a guard when (and only when) a read of the window touches a byte past the image end (kind bank-read-outside-rom).

Per seed: continuous (one persistent CPU) twice and split (fresh CPU per pass from the captured pass-boundary state) twice, every full-state SHA (MS5-SCHED-STATE-1: 64 KiB RAM,
16 registers, PC, bank base, ff8/ff9, per pass and per node entry/exit) compared.  Every pass-end state of the two seeds is dumped (blobs/<sha>.bin).  Typed fixtures: for every one of the
93 entries of the eba9e table, (a) a direct entry at eba3e (the bank-list length function) with 80(A6) = the entry LONG, (b) an object-level pass of node eb81e (captured from the natural
seed) with input BYTE bit 6 so the object itself advances to the entry (eb866 -> eb9e4 -> eba3e), both compared with an independent Python model of the PVC / banked-read semantics
(`pvc_model`, no Unicorn, no capstone, no C++).
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
from unicorn import UC_HOOK_CODE,UC_HOOK_BLOCK,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_HOOK_INTR,UC_HOOK_MEM_INVALID
sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_scheduler as S
from address_map import pvc_bank_update

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_pvc_banks_native'
INPUT_TREE=Path('/Users/start/Workspce/metalslug-input')
INPUT_ROUTING=INPUT_TREE/'engine/src/animation_machine.cpp'
INPUT_BUS=INPUT_TREE/'engine/src/program_bus.cpp'
U06_CONTRACT=ROOT/'docs/analysis/animation-machine-objects-u06-contract.md'
REF_PVC=ROOT/'artifacts/reference/prot_pvc.cpp'
REF_NEOGEO=ROOT/'artifacts/reference/neogeo.cpp'
KEYS=S.KEYS
M32=S.M32
SPD=S.SPD
A5V=S.A5V
PASS_PC=S.PASS_PC
CONTROLLER=S.CONTROLLER
BANK_BASE,BANK_SIZE=S.BANK_BASE,S.BANK_SIZE
PVC,PVC_SIZE=S.PVC,S.PVC_SIZE
ROM_SIZE=0x800000
SEED_CASES=(58,59)
FRAMES=120
TABLE=0xeba9e
OBJ_INIT=0xeb7b6
OBJ_BODY=0xeb81e
BANK_FN=0xeba3e
sha=S.sha


# ----------------------------------------------------------------------------------
# PvcMachine: scheduler Machine with every PVC-selectable bank
# ----------------------------------------------------------------------------------
class PvcMachine(S.Machine):
    """Same constructor contract as S.Machine (program, fixed_buffer, snap).  snap['bank'] = (base, ff8, ff9) with ANY base the formula can produce."""
    def __init__(self,program,fixed_buffer,snap,hooks=True):
        self.program=program
        self.backing=(ctypes.c_ubyte*S.RAM_SIZE).from_buffer_copy(snap['ram']);self.addr=ctypes.addressof(self.backing)
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._keep=[self.backing]
        c.ctl_set_cpu_model(S.m.UC_CPU_M68K_M68000)
        c.mem_map_ptr(0,0x100000,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC,ctypes.addressof(fixed_buffer));c._keep.append(fixed_buffer)
        for i in range(16):c.mem_map_ptr(S.RAM_BASE+i*S.RAM_SIZE,S.RAM_SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        base,ff8,ff9=snap['bank'];self.bank,self.ff8,self.ff9=base,ff8,ff9
        assert base>=0x100000,hex(base)                 # the formula adds 100000: a smaller base is not a producible state
        self.bank_backing=(ctypes.c_ubyte*BANK_SIZE)();c._keep.append(self.bank_backing)
        self.bank_valid=0;self.set_bank(base)
        c.mem_map_ptr(BANK_BASE,BANK_SIZE,unicorn.UC_PROT_READ,ctypes.addressof(self.bank_backing))
        c.mem_map(PVC,PVC_SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        page=bytearray(PVC_SIZE);page[0x1ff0:0x1ff2]=ff8.to_bytes(2,'big');page[0x1ff2:0x1ff4]=ff9.to_bytes(2,'big');c.mem_write(PVC,bytes(page))
        c.mem_map(0x300000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0x3c0000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0xd00000,0x1000,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        self.cpu=c
        c.reg_write(S.UC_REG['sr'],0x2000)
        for k in KEYS:c.reg_write(S.UC_REG[k],snap['regs'][k]&M32)
        c.reg_write(S.UC_REG['pc'],snap['pc'])
        self.ports=[];self.dev_reads=[];self.odd=None;self.invalid=None;self.intr=None;self.bank_reads=0;self.rom_reads=0;self.fetch_unmapped=None
        self.bank_log=None                              # optional list of (address, size, bank) of the banked reads
        self.bank_writes=[]                             # (port index, bank base after the write)
    def set_bank(self,base):
        """Physical program ROM bytes base .. base+fe000-1 become the window; bytes past the 8 MiB image are not exposed (bank_valid counts the exposed prefix)."""
        self.bank=base
        avail=max(0,min(BANK_SIZE,len(self.program)-base))
        ctypes.memset(ctypes.addressof(self.bank_backing),0,BANK_SIZE)
        if avail:ctypes.memmove(ctypes.addressof(self.bank_backing),self.program[base:base+avail],avail)
        self.bank_valid=avail
    def install_basic_hooks(self,odd_check=True,device_events=True):
        c=self.cpu;mach=self
        def mem_read(uc,access,address,size,value,user):
            if size>1 and address&1 and address<0x300000:
                mach.odd=dict(access='read',address=address,size=size,pc=uc.reg_read(S.UC_REG['pc']));uc.emu_stop();return
            if address>=BANK_BASE:
                if address<PVC:
                    mach.bank_reads+=1
                    if mach.bank_log is not None:mach.bank_log.append((address,size,mach.bank))
                    if address-BANK_BASE+size>mach.bank_valid:
                        mach.invalid=dict(access='read',address=address,size=size,kind='bank-read-outside-rom',bank=mach.bank,physical=mach.bank+address-BANK_BASE,pc=uc.reg_read(S.UC_REG['pc']))
                        uc.emu_stop();return
                elif address>=0x300000:mach.dev_reads.append((address,size))
            elif address<0x100000:mach.rom_reads+=1
        def mem_write(uc,access,address,size,value,user):
            if size>1 and address&1 and address<0x300000:
                mach.odd=dict(access='write',address=address,size=size,pc=uc.reg_read(S.UC_REG['pc']),old=bytes(uc.mem_read(address,size)).hex());uc.emu_stop();return
            if address<0x200000:return
            if PVC<=address<0x300000:
                if size!=2 or address not in (0x2ffff0,0x2ffff2):
                    mach.invalid=dict(access='write',address=address,size=size,kind='pvc-page');uc.emu_stop();return
                v=value&0xffff
                if address==0x2ffff0:mach.ff8=v
                else:mach.ff9=v
                mach.ports.append((1,address,2,v))
                base,mach.ff8,mach.ff9=pvc_bank_update(mach.ff8,mach.ff9);mach.set_bank(base);mach.bank_writes.append((len(mach.ports)-1,base))
            else:mach.ports.append((2,address,size,value&((1<<(8*size))-1)))
        def mem_bad(uc,access,address,size,value,user):
            if access==unicorn.UC_MEM_FETCH_UNMAPPED:mach.fetch_unmapped=address
            else:mach.invalid=dict(access={unicorn.UC_MEM_READ_UNMAPPED:'read-unmapped',unicorn.UC_MEM_WRITE_UNMAPPED:'write-unmapped',unicorn.UC_MEM_WRITE_PROT:'write-protected',
                unicorn.UC_MEM_READ_PROT:'read-protected',unicorn.UC_MEM_FETCH_PROT:'fetch-protected'}.get(access,'access-%d'%access),address=address,size=size,pc=uc.reg_read(S.UC_REG['pc']))
            return False
        def intr(uc,number,user):mach.intr=dict(number=number,pc=uc.reg_read(S.UC_REG['pc']));uc.emu_stop()
        c.hook_add(UC_HOOK_MEM_READ,mem_read,begin=0,end=0x3fffff)
        c.hook_add(UC_HOOK_MEM_READ,mem_read,begin=0xd00000,end=0xd00fff)
        c.hook_add(UC_HOOK_MEM_WRITE,mem_write,begin=0x100000,end=0x3fffff)
        c.hook_add(UC_HOOK_MEM_WRITE,mem_write,begin=0xd00000,end=0xd00fff)
        c.hook_add(UC_HOOK_MEM_INVALID,mem_bad)
        c.hook_add(UC_HOOK_INTR,intr)


S.Machine=PvcMachine                                    # SeedRun.build / replay_node / run_until / traced_native look the name up at call time


# ----------------------------------------------------------------------------------
# Independent Python semantics (no Unicorn, no capstone, no C++): the PVC bank register pair and the eba3e bank-list length
# ----------------------------------------------------------------------------------
def be(program,offset,n):return int.from_bytes(program[offset:offset+n],'big')


def pvc_pair(ff8,ff9,which,value):
    """One WORD write to 2ffff0 (which='ff8') or 2ffff2 ('ff9') followed by MAME get_bank_base: returns (ff8', ff9', base)."""
    if which=='ff8':ff8=value&0xffff
    else:ff9=value&0xffff
    base=0x100000+((ff8>>8)|(ff9<<8))
    return (ff8&0xfe00)|0xa0,ff9&0x7fff,base


def eba3e_writes(n):
    """The four PVC WORD writes of eba3e / its tail for bank selector n = 80(A6) & 7: ((n+1)<<12) -> 2ffff2, 0 -> 2ffff0, then 1000 -> 2ffff2, 0 -> 2ffff0."""
    return [(0x2ffff2,((n&7)+1)<<12),(0x2ffff0,0),(0x2ffff2,0x1000),(0x2ffff0,0)]


def bank_sequence(n,ff8=0xa0,ff9=0x1000):
    out=[]
    for addr,val in eba3e_writes(n):
        ff8,ff9,base=pvc_pair(ff8,ff9,'ff8' if addr==0x2ffff0 else 'ff9',val);out.append(dict(address=addr,value=val,base=base,ff8=ff8,ff9=ff9))
    return out


def window_read(program,base,cpu,size):
    """CPU address in 200000..2fdfff -> big-endian value at physical base + cpu - 200000, None when the span is not inside the 8 MiB image (the C++ bus error)."""
    ph=base+cpu-0x200000
    if ph<0 or ph+size>ROM_SIZE:return None
    return be(program,ph,size)


def cpu_read(program,ram,base,cpu,size):
    """The three readable spaces the pointer lists use: fixed ROM, work RAM mirror, banked window.  None when the span is not covered."""
    if size>1 and cpu&1:return None                      # 68000 address error (native: odd-data-access guard)
    if cpu>0xffffff:return None                          # beyond the 24-bit bus: the native machine has no mapping (guard); the 68000 itself would ignore A24..A31
    if cpu<0x100000:return be(program,cpu,size) if cpu+size<=0x100000 else None
    if cpu<0x200000:return int.from_bytes(bytes(ram[(cpu+i)&0xffff] for i in range(size)),'big')
    if cpu<0x2fe000:return window_read(program,base,cpu,size) if cpu+size<=0x2fe000 else None
    return None


def unreadable_kind(cpu,size):
    """The native guard that corresponds to a read the model cannot satisfy."""
    if size>1 and cpu&1:return 'odd-data-access'
    if 0x200000<=cpu<0x2fe000:return 'bank-read-outside-rom'
    return 'read-unmapped'


def eba3e_model(program,ram,long80,ff8=0xa0,ff9=0x1000,max_list=1<<20):
    """Independent model of eba3e: returns dict(n, d2, bank_after_writes, ptr, count, list_bytes_read, ok, why).  `ram` is only used when the list pointer is a work RAM address."""
    n=long80&7;d2=(((long80&0xffff)>>3)<<2)&0xffff       # LSR.W #3 then LSL.W #2 on the low word
    seq=bank_sequence(n,ff8,ff9);base=seq[1]['base']              # the base the banked read uses (after the first two writes)
    res=dict(n=n,d2=d2,seq=seq,base=base,ptr=None,count=None,ok=False,why=None,reads=[])
    sd2=d2-0x10000 if d2&0x8000 else d2                   # MOVEA.L (A1,D2.W),A1 with A1 = 200004: D2.W sign-extended
    cpu=(0x200004+sd2)&0xffffff;first=cpu_read(program,ram,base,cpu,4);res['reads'].append((cpu,4,first))
    if first is None:res['why']='first banked LONG outside the covered spaces';res['guard']=unreadable_kind(cpu,4);return res
    res['ptr']=first;a1=first;d3=0;steps=0
    while True:
        d3=(d3+1)&0xffff;a1=(a1+4)&M32          # ADDQ.W #1,D3 (16-bit) ; ADDQ.L #4,A1
        v=cpu_read(program,ram,base,a1,4);res['reads'].append((a1,4,v))
        if v is None:res['why']='list read outside the covered spaces at %x'%a1;res['count']=d3;res['guard']=unreadable_kind(a1,4);return res
        if v==0:break
        steps+=1
        if steps>max_list:res['why']='list longer than %d'%max_list;return res
    res['count']=(d3-1)&0xffff;res['steps']=steps+1;res['ok']=True;return res


# ----------------------------------------------------------------------------------
# Evidence of the bank formula (pinned sources parsed, not re-typed)
# ----------------------------------------------------------------------------------
def formula_evidence(program):
    ev=dict()
    t=REF_PVC.read_text().splitlines()
    block=t[70:77]
    want=['uint32_t pvc_prot_device::get_bank_base()','{','\tuint32_t bankaddress = ((m_cart_ram[0xff8] >> 8)|(m_cart_ram[0xff9] << 8));','\tm_cart_ram[0xff8] = (m_cart_ram[0xff8] & 0xfe00) | 0x00a0;','\tm_cart_ram[0xff9] &= 0x7fff;','\treturn bankaddress + 0x100000;','}']
    assert block==want,block
    ev['mame_prot_pvc_cpp_71_77']=block
    n=REF_NEOGEO.read_text().splitlines()
    wb=[x for x in n[1230:1242]]
    assert 'write_bankprot_pvc' in wb[0] and 'if (offset >= 0xff8)' in wb[6] and 'm_slots[m_curr_slot]->get_bank_base(data)' in wb[8] and 'get_rom_base() + m_bank_base' in wb[9] and 'protection_w(offset, data, mem_mask)' in wb[3],wb
    ev['mame_neogeo_cpp_1231_1241']=wb
    inst=[x for x in n[1476:1485]]
    assert any('NEOGEO_MSLUG5' in x for x in n[1470:1480])
    ev['mame_neogeo_cpp_1477_1484']=inst
    ev['mame_maincpu_region']=n[9837].strip()
    assert 'ROM_REGION( 0x800000, "cslot1:maincpu"' in n[9837]
    # the Python resolver of the repository (address_map.pvc_bank_update) against the independent pvc_pair on a grid
    mismatches=0;checked=0
    for ff8 in (0,0xa0,0x00ff,0x0100,0x01a0,0xfe00,0xffff):
        for ff9 in list(range(0,0x10000,0x111))+[0x7fff,0x8000,0xffff,0x1000,0x7000]:
            a=pvc_bank_update(ff8,ff9);b=pvc_pair(ff8,ff9,'ff9',ff9)
            checked+=1
            if (a[1],a[2],a[0])!=(b[0],b[1],b[2]):mismatches+=1
    ev['address_map_vs_independent_grid']=dict(checked=checked,mismatches=mismatches);assert mismatches==0
    # C++ text of the input tree
    cpp=INPUT_ROUTING.read_text()
    needle='device.bank_base=0x100000U+((ff8>>8)|(ff9<<8));'
    assert needle in cpp and 'if (index>=0xff8)' in cpp
    ev['cpp_pvc_effects']=dict(file=str(INPUT_ROUTING),sha256=sha(INPUT_ROUTING.read_bytes()),formula=needle,trigger='pvc_effects(device,index): index>=0xff8 (every WORD write at 2ffff0..2fffff)')
    bus=INPUT_BUS.read_text()
    assert 'bus.bank_base<0x100000U || physical+size>0x800000U' in bus and 'bus.bank_base)+(address-0x200000U)' in bus
    ev['cpp_program_bus']=dict(file=str(INPUT_BUS),sha256=sha(INPUT_BUS.read_bytes()),window='physical=bank_base+(address-200000); bank_base<100000 or physical+size>800000 -> "reached program bank physical span outside ROM"; no wrap, no alignment requirement')
    # layout facts of the canonical image
    manifest=json.loads((ROOT/'extracted/program/manifest.json').read_text())
    assert manifest['output']['size']==ROM_SIZE and manifest['output']['sha256']==S.ROM_SHA
    ev['rom_image']=dict(size=ROM_SIZE,sha256=S.ROM_SHA,fixed='CPU 0..fffff = file offset 0..fffff',banked='CPU 200000..2fdfff = file offset bank_base + (cpu - 200000) (bank_base is a BYTE offset: 100000 + ((ff8>>8)|(ff9<<8)))',overlay='CPU 2fe000..2fffff = PVC RAM (never ROM)')
    # table of the aligned banks k = bank_base / 100000 (ff8 high byte 0): which k the formula can produce and what they select
    rows=[]
    for k in range(0,10):
        row=dict(k=k,base=k*0x100000)
        # base = 100000 + (ff9<<8) with ff8>>8 = 0: ff9 = (k-1)<<12; ff9 bit15 cleared by the register side effect AFTER the base was computed
        if k>=1:
            ff9=(k-1)<<12;row['ff9_value']=ff9&0xffff if ff9<=0xffff else None
            row['producible_by_one_ff9_write']=ff9<=0xffff
            row['window_start_offset']=k*0x100000;row['window_end_exclusive']=k*0x100000+BANK_SIZE
            row['inside_8MiB_image']=row['window_end_exclusive']<=ROM_SIZE
        else:
            row['producible_by_one_ff9_write']=False;row['note']='base 0 is not producible: the formula adds 100000'
        rows.append(row)
    ev['aligned_banks']=rows
    # the full producible range
    lo=0x100000;hi=0x100000+0xffff+(0xffff<<8)
    ev['producible_range']=dict(min_base=lo,max_base=hi,note='ff8>>8 is 0..ff and ff9<<8 is 0..ffff00 (BYTE offsets, any alignment); only bases <= 800000 - (window span) leave the whole window inside the image; ff9 bit15 produces bases >= 900000 on the write that sets it (always outside the image)')
    ev['bases_whole_window_inside_image']=dict(max=ROM_SIZE-BANK_SIZE,note='base <= 701fff selects a full 2fe000-byte window inside the image; larger bases up to 7fffff select a partial window (bytes past 800000 are not exposed; a read of them is the guard)')
    return ev


# ----------------------------------------------------------------------------------
# Routing of the newest merged C++ tree (metalslug-input, U01..U06 routed): entry routability by callback PC (the F2 contract method)
# ----------------------------------------------------------------------------------
class _Text(object):
    def __init__(self,text):self.text=text
    def read_text(self):return self.text


def input_routing_bitmap(program):
    src=INPUT_ROUTING.read_text()
    old=') &&\n                !stage_event_ops_trap(next.pc))ok='
    assert src.count(old)==1
    intervals,checks=S.routing_intervals(_Text(src.replace(old,'))ok=')))
    bm=bytearray(0x80000)
    for lo,hi,excl,name in intervals:
        for pc in range(lo&~1,min(hi,0xfffff)+1,2):
            if pc in excl or pc<lo:continue
            bm[pc>>1]=1
    traps=set(S.F3_TRAPS_DECL)
    for t in traps:bm[t>>1]=0                           # stage_event_ops_trap(): the 8 TRAP boundaries are not routed
    owner={}
    for lo,hi,excl,name in intervals:
        for pc in range(lo&~1,min(hi,0xfffff)+1,2):
            if pc not in excl and pc>=lo and pc not in traps:owner.setdefault(pc,name)
    return bm,owner,len(intervals)


def u06_starts():
    """The 135 block starts of the U06 contract (`- `pc`:` lines of the block list section)."""
    text=U06_CONTRACT.read_text();a=text.index('## block 목록과 실행 의미');b=text.index('## 구현 범위와 규약')
    starts=[int(m.group(1),16) for m in re.finditer(r'^- `([0-9a-f]+)`:',text[a:b],re.M)]
    assert len(starts)==len(set(starts))==135,len(starts)
    return starts


U06_RANGES=((0x49be0,0x49bf2),(0xe73f8,0xe74f8),(0xe7546,0xe7562),(0xe7792,0xe7946),(0xeb7b6,0xeb9ba),(0xeba3e,0xeba9e))


def in_u06(pc):return any(lo<=pc<hi for lo,hi in U06_RANGES)


def classify_tbs(tb_pcs):
    """Executed Unicorn TB starts -> routed? owner? U06 range but not a contract block start?"""
    bm=INP['bitmap'];own=INP['owner'];starts=INP['u06_starts']
    out=dict(unrouted=[],u06_not_start=[],owners=collections.Counter())
    for pc in sorted(set(tb_pcs)):
        routed=pc<0x100000 and bool(bm[pc>>1])
        if not routed:out['unrouted'].append(pc);continue
        out['owners'][own.get(pc,'?')]+=1
        if in_u06(pc) and pc not in starts:out['u06_not_start'].append(pc)
    return out


class PvcRun(S.SeedRun):
    """SeedRun whose routability test never rejects (so every pass-end state is dumped and no run is extended); the true entry routability is recorded in self.rt[pc]."""
    def __init__(self,*a,**k):
        S.SeedRun.__init__(self,*a,**k);self.rt={};self.tb_by_cb=collections.defaultdict(collections.Counter)
    def h_block(self,uc,addr,size,user):
        node=self.cur
        if node is not None and node['cb'] in (OBJ_INIT,OBJ_BODY):self.tb_by_cb[node['cb']][addr]+=1
        S.SeedRun.h_block(self,uc,addr,size,user)
    def routable(self,level,pc):
        self.rt.setdefault(pc,{})[level]=S.SeedRun.routable(self,level,pc)
        return True


# ----------------------------------------------------------------------------------
# Seeds: continuous x2 + split x2, full dumps
# ----------------------------------------------------------------------------------
G=S.G
INP={}


def make_run(case,mode,heavy,sink,capture_nodes=None,frames=FRAMES):
    sd=S.SEEDS[case];snap,meta=S.seed_snap(sd)
    run=PvcRun(G['program'],G['fixed'],G['levels'],snap,mode,frames,heavy=heavy,sink=sink,extend=False)
    if capture_nodes:run.capture_nodes=set(capture_nodes)
    return run,meta,sd


def pass_view(run,bitmap):
    """Per pass: callbacks in order with the C++ entry routability of the merged tree (bitmap) and of the main tree (S levels A)."""
    rows=[]
    for p in run.pass_records:
        nodes=[]
        for n in p['nodes']:
            cb=n['cb'];rt=run.rt.get(cb,{})
            nodes.append(dict(seq=n['seq'],a6=n['a6'],cb=cb,entry=n['entry'],exit=n['exit'],routable_input_tree=bool(cb<0x100000 and not cb&1 and bitmap[cb>>1]),routable_main_tree_A=bool(rt.get('A')),
                ports=n['ports'],ports_sha=n['ports_sha'],bank_reads=n['bank_reads'],rom_reads=n['rom_reads'],partial=n['partial'],tbs=n['tbs']))
        rows.append(dict(frame=p['frame'],start=p['start'],end=p['end'],stop=p['stop'],list_len=p['list_len'],ports=p['ports'],ports_sha=p['ports_sha'],nodes=nodes))
    return rows


def seed_task(arg):
    case,out_dir=arg;out_dir=Path(out_dir);bitmap=INP['bitmap']
    run,meta,sd=make_run(case,'continuous',True,{})
    run.run()
    for d,b in run.blobs.items():S.write_blob(out_dir,d,b)
    view=pass_view(run,bitmap)
    doc=dict(case=case,family=sd['family'],seed_bank=sd['bank'],meta=meta,declared=run.declared,stop=run.stop,frames_done=run.frames_done,passes=view,dumps=run.dump_rows,f3=run.f3_records,model_mismatch=run.model_mismatch[:50],model_count={'%x/%s/%s/%s'%k:v for k,v in run.model_count.items()})
    gz_sha,gz_size=S.write_gz(out_dir/'seeds'/('seed_%04d.json.gz'%case),doc)
    r=dict(case=case,family=sd['family'],seed_bank=sd['bank'],stop=run.stop,frames_done=run.frames_done,frames_complete=sum(1 for p in run.pass_records if p['stop']=='frame-head'),
        digest=run.digest.hexdigest(),file='seeds/seed_%04d.json.gz'%case,file_sha256=gz_sha,file_size=gz_size,dumps=len(run.dump_rows),blobs=len(run.blobs),
        cb_counts=S.hexkeys(run.cb_counts),leader_hits=S.hexkeys(run.leader_hits),waits=S.hexkeys(run.waits_total),a7_bad=run.a7_bad,head_bad=run.head_bad,
        model_mismatch=len(run.model_mismatch),model_count={'%x/%s/%s/%s'%k:v for k,v in run.model_count.items()},pass_end_tail=[p['end'] for p in run.pass_records][-3:],
        pass_digests=hashlib.sha256(json.dumps([(p['start'],p['end']) for p in run.pass_records]).encode()).hexdigest(),
        bank_reads_total=sum(n['bank_reads'] for p in run.pass_records for n in p['nodes']),
        tb={'%x'%cb:{'%x'%pc:n for pc,n in sorted(cnt.items())} for cb,cnt in sorted(run.tb_by_cb.items())},
        tb_class={'%x'%cb:dict(unrouted=['%x'%x for x in classify_tbs(cnt)['unrouted']],u06_not_start=['%x'%x for x in classify_tbs(cnt)['u06_not_start']],owners=dict(classify_tbs(cnt)['owners'])) for cb,cnt in sorted(run.tb_by_cb.items())},
        first_uncovered=next(((p['frame'],n['seq'],n['cb']) for p in view for n in p['nodes'] if not n['routable_input_tree']),None),
        first_uncovered_main=next(((p['frame'],n['seq'],n['cb']) for p in view for n in p['nodes'] if not n['routable_main_tree_A']),None))
    for tag in ('continuous2','split1','split2'):
        sr,_,_=make_run(case,'split' if tag.startswith('split') else 'continuous',False,None);sr.run()
        r[tag]=sr.digest.hexdigest();r[tag+'_frames']=sr.frames_done;r[tag+'_stop']=sr.stop
    return r


def init_worker():
    pass


# ----------------------------------------------------------------------------------
# Typed fixtures
# ----------------------------------------------------------------------------------
def table_entries(program):
    out=[];t=TABLE
    while be(program,t,4):
        out.append((be(program,t,4),be(program,t+4,2),be(program,t+6,2)));t+=8
    return out


def run_segment(program,fixed,snap,stops,limit=3_000_000):
    """Fresh PvcMachine from `snap`; runs until the first arrival at one of `stops` (not at the start PC), or a guard.  Returns state, ordered ports, banked reads (address,size,bank), instruction count."""
    mach=PvcMachine(program,fixed,snap);mach.install_basic_hooks();mach.bank_log=[];c=mach.cpu
    res=dict(status=None,stop_pc=None);cnt=[0];tbs=[]
    def block(uc,addr,size,user):tbs.append(addr)
    c.hook_add(UC_HOOK_BLOCK,block)
    def code(uc,pc,size,user):
        cnt[0]+=1
        if res['status'] is None and pc in stops and cnt[0]>1:
            res['status']='stop';res['stop_pc']=pc;uc.emu_stop()
    c.hook_add(UC_HOOK_CODE,code)
    err=None
    try:c.emu_start(snap['pc'],0xffffff,count=limit)
    except unicorn.UcError as e:err=str(e)
    res.update(tbs=tbs,ins=cnt[0]-(1 if res['status']=='stop' else 0),ports=list(mach.ports),bank_log=list(mach.bank_log),bank_writes=list(mach.bank_writes),mach=mach)
    st=mach.state()
    if res['status']=='stop':st['pc']=res['stop_pc']
    res['state']=st
    if res['status'] is None:
        res['status']='guard'
        res['reason']=dict(odd=mach.odd,invalid=mach.invalid,fetch_unmapped=mach.fetch_unmapped,intr=mach.intr,error=err,step_limit=bool(err is None and not (mach.odd or mach.invalid or mach.intr)))
    return res


def seg_digest(r):
    h=hashlib.sha256();h.update(b'MS5-PVCBANK-SEG-1')
    h.update(S.state_blob_digest(r['state']['ram'],r['state']['regs'],r['state']['pc'],r['state']['bank']).encode())
    h.update(S.ports_digest(r['ports']).encode())
    for a,s_,b in r['bank_log']:h.update(struct.pack('>III',a,s_,b))
    h.update(r['status'].encode())
    return h.hexdigest()


def split_run(program,fixed,snap,mid,final):
    """Continuous run to `final` vs run to `mid` (first arrival), a FRESH machine rebuilt from the captured mid state (RAM, 16 registers, PC, bank base / ff8 / ff9) continuing to `final`."""
    a=run_segment(program,fixed,snap,final)
    r1=run_segment(program,fixed,snap,set(final)|{mid})
    if r1['status']!='stop' or r1['stop_pc']!=mid:return a,r1,r1        # the run ended (guard / final stop) before the split point: nothing to resume
    st=copy.deepcopy(r1['state'])
    r2=run_segment(program,fixed,st,final)
    joined=dict(status=r2['status'],state=r2['state'],ports=r1['ports']+r2['ports'],bank_log=r1['bank_log']+r2['bank_log'],ins=r1['ins']+r2['ins'],bank_writes=r1['bank_writes']+r2['bank_writes'])
    return a,r1,joined


def rd(ram,address,n):
    return int.from_bytes(bytes(ram[(address+i)&0xffff] for i in range(n)),'big')


def write_word(ram,address,value):
    ram[(address)&0xffff]=(value>>8)&255;ram[(address+1)&0xffff]=value&255


def expect_eba3e_direct(program,snap_after_edits,a6,long80):
    """Independent expectation of a direct eba3e entry (return LONG 2ac2 at A7): final registers, RAM, ports, bank, banked reads."""
    ram0=bytes(snap_after_edits['ram']);regs0=snap_after_edits['regs']
    ff8,ff9=snap_after_edits['bank'][1],snap_after_edits['bank'][2]
    mdl=eba3e_model(program,ram0,long80,ff8,ff9)
    exp=dict(model=mdl)
    if not mdl['ok']:return exp
    ram=bytearray(ram0);a7=regs0['a7']                   # a7 points at the return LONG
    write_word(ram,a7-2,regs0['d0']&0xffff)              # MOVE.W D0,-(A7)
    write_word(ram,a6+0x7a,mdl['count'])                 # MOVE.W D3,7a(A6)
    write_word(ram,0x100010,0)                           # MOVE.W #0,-7ff0(A5)
    regs=dict(regs0)
    regs['d1']=(long80&0xffff0000)|mdl['n'];regs['d2']=(long80&0xffff0000)|mdl['d2'];regs['d3']=mdl['count']
    regs['a1']=(mdl['ptr']+4*mdl['steps'])&M32;regs['a7']=a7+4
    exp.update(ram=bytes(ram),regs=regs,ports=[(1,addr,2,val) for addr,val in eba3e_writes(mdl['n'])],bank=(0x200000,0xa0,0x1000),
        window_reads=[(a,s_) for a,s_,v in mdl['reads'] if 0x200000<=a<0x2fe000])
    return exp


def stats_of_list(program,mdl):
    vals=[v for a,s_,v in mdl['reads'][1:] if v]
    if not vals:return dict(n=0)
    return dict(n=len(vals),min=min(vals),max=max(vals),all_in_window=all(0x200000<=v<0x2fe000 for v in vals),
        ascending_runs=sum(1 for i in range(1,len(vals)) if vals[i]<vals[i-1])+1,even=all(not v&1 for v in vals))


def mdl_summary(mdl):
    return dict(n=mdl['n'],d2=mdl['d2'],base=mdl['base'],ptr=mdl['ptr'],last_index=mdl['count'],ok=mdl['ok'],why=mdl['why'],guard=mdl.get('guard'),seq=[(x['address'],x['value'],x['base']) for x in mdl['seq']],reads=len(mdl['reads']))


def tb_fields(a):
    cls=classify_tbs(a['tbs'])
    return dict(tb_unrouted=['%x'%x for x in cls['unrouted']],tb_u06_not_start=['%x'%x for x in cls['u06_not_start']],tb_u06_starts=['%x'%x for x in sorted(set(a['tbs'])) if in_u06(x)],tb_owners=dict(cls['owners']))


def direct_fixture(fx,name,i,long80,w84,w86):
    base=fx['entry']['snap'];a6=base['regs']['a6'];snap=copy.deepcopy(base)
    snap['pc']=BANK_FN;ret=SPD-4;snap['regs']['a7']=ret;snap['regs']['d0']=0x1234abcd
    edits=[S.W(ret,4,PASS_PC,'declared return LONG 2ac2 at A7 (the caller JSR push)'),S.W(a6+0x80,4,long80,'80(A6) := eba9e entry LONG'),S.W(a6+0x84,2,w84,'84(A6)'),S.W(a6+0x86,2,w86,'86(A6)')]
    snap,done=S.apply_edits(snap,edits)
    exp=expect_eba3e_direct(fx['program'],snap,a6,long80)
    a,r1,j=split_run(fx['program'],fx['fixed'],snap,0xeba78,{PASS_PC})
    a2=run_segment(fx['program'],fx['fixed'],snap,{PASS_PC})
    row=dict(name=name,group='eba3e-direct',entry_index=i,long80=long80,pc=BANK_FN,edits=done,status=a['status'],ins=a['ins'],model=mdl_summary(exp['model']),list_stats=stats_of_list(fx['program'],exp['model']),
        entry=S.state_blob_digest(snap['ram'],snap['regs'],snap['pc'],snap['bank']),seg=seg_digest(a),seg_twice=seg_digest(a2),seg_split=seg_digest(j) if j else None,
        bank_writes=[(p,b) for p,b in a['bank_writes']],ports=[(k,hex(x),s_,hex(v)) for k,x,s_,v in a['ports']],bank_reads=len(a['bank_log']),**tb_fields(a))
    ok=dict(twice=row['seg']==row['seg_twice'],split=j is not None and row['seg']==row['seg_split'])
    st=a['state']
    if exp['model']['ok']:
        ok['stop_2ac2']=a['status']=='stop' and a['stop_pc']==PASS_PC
        if ok['stop_2ac2']:
            ok['regs']=all(st['regs'][k]==exp['regs'][k] for k in KEYS)
            ok['ram']=st['ram']==exp['ram']
            ok['ports']=a['ports']==exp['ports']
            ok['bank']=tuple(st['bank'])==exp['bank']
            ok['window_reads']=[(x,s_) for x,s_,b in a['bank_log']]==exp['window_reads'] if True else None
            ok['reads_under_selected_bank']=all(b==exp['model']['base'] for x,s_,b in a['bank_log'])
            row['exit']=fx['blob'](st['ram'],st,'direct-exit')
    else:
        # the model says a read is outside the covered spaces: the native run must be a guard
        ok['guard_expected']=a['status']=='guard'
        row['guard']=a.get('reason');row['why']=exp['model']['why']
        r_=a.get('reason') or {};inv=r_.get('invalid') or {}
        row['guard_kind']='odd-data-access' if r_.get('odd') else (inv.get('kind') or inv.get('access'))
        ok['guard_kind']=row['guard_kind']==exp['model'].get('guard')
    row['ok_parts']=ok;row['ok']=all(v for v in ok.values() if v is not None)
    return row


def object_fixture(fx,name,i,long80,w84,w86,count_entries):
    base=fx['entry']['snap'];a6=base['regs']['a6'];snap=copy.deepcopy(base)
    prev=(i-1)%count_entries if i>0 else count_entries-1
    src_byte=fx['entry']['ctl_addr']
    edits=[S.W(a6+0x7c,2,prev,'7c(A6) := entry index - 1 (eb866 ADDQ.W #1 then eb9e4 selects entry i; 0 wraps through 78(A6))'),S.W(a6+0x7e,2,0,'7e(A6) := 0'),S.W(src_byte,1,0x40,'input BYTE -3346(A5) := 40: BTST #6 set, bits 4/5 clear (76(A6)=0)')]
    snap,done=S.apply_edits(snap,edits)
    mdl=eba3e_model(fx['program'],snap['ram'],long80,snap['bank'][1],snap['bank'][2])
    a,r1,j=split_run(fx['program'],fx['fixed'],snap,0xeba78,{PASS_PC})
    a2=run_segment(fx['program'],fx['fixed'],snap,{PASS_PC})
    row=dict(name=name,group='object-eb81e',entry_index=i,long80=long80,pc=0x2ab8,edits=done,status=a['status'],ins=a['ins'],model=mdl_summary(mdl),
        entry=S.state_blob_digest(snap['ram'],snap['regs'],snap['pc'],snap['bank']),seg=seg_digest(a),seg_twice=seg_digest(a2),seg_split=seg_digest(j) if j else None,
        ports=[(k,hex(x),s_,hex(v)) for k,x,s_,v in a['ports']],bank_reads=len(a['bank_log']),**tb_fields(a))
    ok=dict(twice=row['seg']==row['seg_twice'],split=j is not None and row['seg']==row['seg_split'])
    st=a['state'];ram=st['ram']
    ok['stop_2ac2']=a['status']=='stop' and a['stop_pc']==PASS_PC
    if ok['stop_2ac2'] and mdl['ok']:
        w=lambda off:rd(ram,a6+off,2)
        l80=rd(ram,a6+0x80,4)
        ok['7c']=w(0x7c)==i;ok['7e']=w(0x7e)==0;ok['80']=l80==long80;ok['84']=w(0x84)==w84;ok['86']=w(0x86)==w86;ok['7a']=w(0x7a)==mdl['count']
        ok['100010']=rd(ram,0x100010,2)==0
        ok['callback_kept']=rd(ram,a6,4)==0xeb81e
        ok['pvc_ports_first4']=a['ports'][:4]==[(1,addr,2,val) for addr,val in eba3e_writes(mdl['n'])]
        ok['bank_final']=tuple(st['bank'])==(0x200000,0xa0,0x1000)
        sel=[(x,s_) for x,s_,b in a['bank_log'] if b==mdl['base']]
        ok['reads_under_selected_bank']=sel==[(x,s_) for x,s_,v in mdl['reads'] if 0x200000<=x<0x2fe000]
        row['reads_after_restore']=sum(1 for x,s_,b in a['bank_log'] if b!=mdl['base'])
        row['ports_total']=len(a['ports'])
        row['exit']=fx['blob'](ram,st,'object-exit')
    elif not mdl['ok']:
        ok['guard_expected']=a['status']=='guard';row['guard']=a.get('reason')
    row['ok_parts']=ok;row['ok']=all(v for v in ok.values() if v is not None)
    return row


INPUT_VARIANTS=(
    ('up (B1 bit4)',0x104cba,0x10),('down (B1 bit5)',0x104cba,0x20),('right (B1 bit6)',0x104cba,0x40),('left (B1 bit7)',0x104cba,0x80),
    ('B2 bit0',0x104cbe,0x01),('B2 bit1',0x104cbe,0x02),('B2 bit2',0x104cbe,0x04),('B2 bit3',0x104cbe,0x08),
    ('B3 bit4',0x104cc0,0x10),('B3 bit5',0x104cc0,0x20),('B4 bit6',0x104cbf,0x40))


def input_fixture(fx,name,addr,bit):
    """Native-only: node eb81e with one input BYTE bit set (76(A6) = 0).  Records the status, the changed A6 fields and the executed TB starts that the merged C++ tree does not route."""
    base=fx['entry']['snap'];a6=base['regs']['a6']
    assert (base['regs']['a5']-0x3346)&0xffffff==0x104cba
    snap,done=S.apply_edits(copy.deepcopy(base),[S.W(addr,1,bit,'input BYTE := %02x'%bit)])
    a=run_segment(fx['program'],fx['fixed'],snap,{PASS_PC});a2=run_segment(fx['program'],fx['fixed'],snap,{PASS_PC})
    ram0=snap['ram'];st=a['state'];ram=st['ram']
    changed=[(off,rd(ram0,a6+off,2),rd(ram,a6+off,2)) for off in range(0,0xa0,2) if rd(ram0,a6+off,2)!=rd(ram,a6+off,2)]
    row=dict(name=name,group='object-input',pc=0x2ab8,edits=done,status=a['status'],stop_pc=a.get('stop_pc'),ins=a['ins'],seg=seg_digest(a),seg_twice=seg_digest(a2),ports=[(k,hex(x),s_,hex(v)) for k,x,s_,v in a['ports']],
        a6_changed=[(hex(o),hex(x),hex(y)) for o,x,y in changed],bank_final=list(st['bank']),bank_reads=len(a['bank_log']),**tb_fields(a))
    if a['status']=='guard':row['guard']=a.get('reason')
    row['ok_parts']=dict(twice=row['seg']==row['seg_twice'],stop_2ac2=a['status']=='stop' and a['stop_pc']==PASS_PC);row['ok']=all(row['ok_parts'].values())
    return row


def sweep_fixture(fx,n,d2):
    """Generic bank sweep: eba3e with 80(A6) = n | (d2 << 1) so the 200004+D2.W read reaches the bank selected by n (n = 0..7 -> bases 200000 .. 900000 after the first write; the READ base is the one after the 2nd write)."""
    long80=(n&7)|(((d2>>2)<<3)&0xffff)
    return direct_fixture(fx,'sweep-n%d-d2_%x'%(n,d2),-1,long80,0,0)


def fixture_task(arg):
    kind,i,case=arg
    fx=INP['fx'][case]
    ents=INP['entries'];long80,w84,w86=ents[i] if kind in ('direct','object') else (None,0,0)
    if kind=='input':return dict(case=case,**input_fixture(fx,'eb81e-input-%s'%INPUT_VARIANTS[i][0].replace(' ','_'),INPUT_VARIANTS[i][1],INPUT_VARIANTS[i][2]))
    if kind=='direct':return dict(case=case,**direct_fixture(fx,'eba3e-direct-%02d'%i,i,long80,w84,w86))
    if kind=='object':return dict(case=case,**object_fixture(fx,'eb81e-object-%02d'%i,i,long80,w84,w86,len(ents)))
    n,d2=i
    return dict(case=case,**sweep_fixture(fx,n,d2))


# ----------------------------------------------------------------------------------
# Entry capture (natural eb81e node at frame 1 and eb7b6 node at frame 0) and the natural eb7b6 replay
# ----------------------------------------------------------------------------------
def capture_entries(case):
    run,meta,sd=make_run(case,'continuous',False,None,frames=2);run.run()
    out=dict()
    for frame,cb in ((0,OBJ_INIT),(1,OBJ_BODY)):
        seq=[n['seq'] for n in run.pass_records[frame]['nodes'] if n['cb']==cb]
        assert len(seq)==1,(case,frame,hex(cb),seq)
        run2,_,_=make_run(case,'continuous',False,None,capture_nodes=[(frame,seq[0])],frames=2);run2.run()
        ent=run2.captured_nodes[(frame,seq[0])]['entry']
        node=run.pass_records[frame]['nodes'][seq[0]]
        out[cb]=dict(frame=frame,seq=seq[0],snap=ent,entry_digest=node['entry'],exit_digest=node['exit'],ports_sha=node['ports_sha'],a6=ent['regs']['a6'])
    return out


def natural_init_replay(case,ent,program,fixed,entries,blob):
    """Replay the natural eb7b6 node (frame 0) on a fresh CPU from its captured entry state (PC 2ab8) and compare with the seed run's node record and the independent model."""
    e=ent[OBJ_INIT];snap=e['snap'];a6=e['a6']
    r=run_segment(program,fixed,snap,{PASS_PC})
    st=r['state'];ram=st['ram']
    w=lambda off,n=2:rd(ram,a6+off,n)
    long80,w84,w86=entries[0];mdl=eba3e_model(program,snap['ram'],long80,snap['bank'][1],snap['bank'][2])
    ok=dict(stop_2ac2=r['status']=='stop' and r['stop_pc']==PASS_PC)
    if ok['stop_2ac2']:
        ok['exit_digest_equals_seed_node']=S.state_blob_digest(ram,st['regs'],PASS_PC,st['bank'])==e['exit_digest']
        ok['ports_sha_equals_seed_node']=S.ports_digest(r['ports'])==e['ports_sha']
        ok['entry_count_78']=w(0x78)==len(entries)
        ok['7c_7e_88_zero']=(w(0x7c),w(0x7e),w(0x88))==(0,0,0)
        ok['8a']=ram[(a6+0x8a)&0xffff]==2
        ok['80_84_86']=(w(0x80,4),w(0x84),w(0x86))==(long80,w84,w86)
        ok['7a']=w(0x7a)==mdl['count']
        ok['callback_eb81e']=w(0,4)==OBJ_BODY
        ok['100010']=rd(ram,0x100010,2)==0
        ok['ports_pvc4']=[p for p in r['ports'] if p[1] in (0x2ffff0,0x2ffff2)]==[(1,addr,2,val) for addr,val in eba3e_writes(mdl['n'])]
        ok['bank_final']=tuple(st['bank'])==(0x200000,0xa0,0x1000)
        ok['bank_sequence']=[b for p,b in r['bank_writes']]==[x['base'] for x in mdl['seq']]
        sel=[(x,s_) for x,s_,b in r['bank_log'] if b==mdl['base']]
        ok['reads_under_selected_bank']=sel==[(x,s_) for x,s_,v in mdl['reads'] if 0x200000<=x<0x2fe000]
    row=dict(case=case,pc=0x2ab8,ins=r['ins'],ports=len(r['ports']),bank_reads=len(r['bank_log']),bank_base_reads=sorted({b for x,s_,b in r['bank_log']}),model=mdl_summary(mdl),ok_parts=ok,ok=all(ok.values()),
        exit=blob(ram,st,'natural-eb7b6-exit'),entry_digest=e['entry_digest'],exit_digest=e['exit_digest'],reads_ports_after=len(r['ports'])-4)
    return row


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def tool_pins():
    pins={}
    for name in ('observe_animation_machine_scheduler.py',)+S.IMPORTED_TOOLS:pins['tools/'+name]=sha((ROOT/'tools'/name).read_bytes())
    for path in (S.F2_CONTRACT,S.F3_CONTRACT,U06_CONTRACT,S.SEED_OBS,REF_PVC,REF_NEOGEO):pins[str(path.relative_to(ROOT))]=sha(path.read_bytes())
    for path in (INPUT_ROUTING,INPUT_BUS,INPUT_TREE/'engine/src/animation_machine_objects_u06.cpp'):pins['metalslug-input/'+str(path.relative_to(INPUT_TREE))]=sha(path.read_bytes())
    return pins


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(OUT));ap.add_argument('--workers',type=int,default=3)
    args=ap.parse_args(argv);out_dir=Path(args.out).resolve();t0=time.time()
    rom_start=S.rom_stat();assert rom_start['sha256']==S.ROM_SHA
    assert sha(S.F2_CONTRACT.read_bytes())==S.F2_SHA and sha(S.F3_CONTRACT.read_bytes())==S.F3_SHA
    if out_dir.exists() and any(out_dir.iterdir()):raise SystemExit('output directory is not empty: %s'%out_dir)
    (out_dir/'blobs').mkdir(parents=True,exist_ok=True);(out_dir/'seeds').mkdir(exist_ok=True)
    program=S.setup();S.load_seeds();pins=tool_pins()
    bitmap,owner,nrules=input_routing_bitmap(program);INP['bitmap']=bitmap;INP['owner']=owner;INP['u06_starts']=set(u06_starts())
    evidence=formula_evidence(program)
    entries=table_entries(program);assert len(entries)==93
    INP['entries']=entries
    # entry captures + natural eb7b6 replay
    def blob(ram,st,kind):
        d=sha(ram);S.write_blob(out_dir,d,ram)
        return dict(kind=kind,ram=d,pc=st['pc'],bank=list(st['bank']),state=S.state_blob_digest(ram,st['regs'],st['pc'],st['bank']))
    INP['fx']={};natural=[]
    for case in SEED_CASES:
        ent=capture_entries(case)
        snap=ent[OBJ_BODY]['snap'];a6=ent[OBJ_BODY]['a6']
        ctl=(snap['regs']['a5']-0x3346)&0xffffff
        assert rd(snap['ram'],a6+0x76,2)==0,'76(A6) must be 0 in the natural eb81e entry'
        assert snap['ram'][ctl&0xffff]&0x70==0
        INP['fx'][case]=dict(program=program,fixed=S.G['fixed'],entry=dict(snap=snap,ctl_addr=ctl,a6=a6,seq=ent[OBJ_BODY]['seq']),blob=blob)
        natural.append(natural_init_replay(case,ent,program,S.G['fixed'],entries,blob))
    ctx=multiprocessing.get_context('fork')
    tasks=[]
    for case in SEED_CASES:
        for i in range(93):tasks.append(('direct',i,case));tasks.append(('object',i,case))
        for n in range(8):
            for d2 in (0,0x7ffc):tasks.append(('sweep',(n,d2),case))
        for i in range(len(INPUT_VARIANTS)):tasks.append(('input',i,case))
    with ctx.Pool(args.workers) as pool:
        seed_rows=pool.map(seed_task,[(c,str(out_dir)) for c in SEED_CASES],chunksize=1)
        fixture_rows=pool.map(fixture_task,tasks,chunksize=4)
    rows_by_case={c:[r for r in fixture_rows if r['case']==c] for c in SEED_CASES}
    # seed equality of the four executions
    for r in seed_rows:
        r['equal']=dict(continuous_twice=r['digest']==r['continuous2'],split_first=r['digest']==r['split1'],split_second=r['digest']==r['split2'],frames=r['split1_frames']==r['frames_done']==r['split2_frames'],stop=r['split1_stop']==r['stop']==r['split2_stop'])
        assert all(r['equal'].values()),(r['case'],r['equal'])
    sizes=S.dir_sizes(out_dir)
    # bank evidence of the 93 table entries (from the object-level + direct fixtures of the first seed)
    first=SEED_CASES[0]
    direct=sorted([r for r in rows_by_case[first] if r['group']=='eba3e-direct' and r['entry_index']>=0],key=lambda r:r['entry_index'])
    table=[]
    for r in direct:
        m=r['model'];st=r['list_stats']
        table.append(dict(index=r['entry_index'],long80='%x'%r['long80'],n=m['n'],d2='%x'%m['d2'],read_base='%x'%m['base'],physical_first_read='%x'%(m['base']+4+m['d2']),ptr=('%x'%m['ptr']) if m['ptr'] is not None else None,
            last_index=m['last_index'],reads=m['reads'],list_min=('%x'%st['min']) if st.get('n') else None,list_max=('%x'%st['max']) if st.get('n') else None,all_in_window=st.get('all_in_window'),
            ascending_runs=st.get('ascending_runs'),ok=r['ok']))
    bank_counts=collections.Counter(t['read_base'] for t in table)
    fx_total=len(fixture_rows);fx_ok=sum(1 for r in fixture_rows if r['ok'])
    starts=INP['u06_starts'];fam=[pc for pc in sorted(starts) if 0xeb7b6<=pc<0xeb9ba or 0xeba3e<=pc<0xeba9e]
    nat_pcs={int(k,16) for r in seed_rows for d in r['tb'].values() for k in d}&starts
    fix_pcs={int(x,16) for r in fixture_rows for x in r.get('tb_u06_starts',[])}&starts
    not_start=sorted({x for r in fixture_rows for x in r.get('tb_u06_not_start',[])}|{x for r in seed_rows for d in r['tb_class'].values() for x in d['u06_not_start']})
    unrouted=collections.Counter(x for r in fixture_rows for x in r.get('tb_unrouted',[]))
    u06_cov=dict(contract_starts=len(starts),eb7b6_family_starts=len(fam),natural_reached_all=len(nat_pcs),natural_reached_family=len([x for x in fam if x in nat_pcs]),
        fixtures_reached_family=len([x for x in fam if x in fix_pcs]),union_family=len([x for x in fam if x in nat_pcs|fix_pcs]),
        family_not_reached=['%x'%x for x in fam if x not in nat_pcs|fix_pcs],tb_not_contract_start=not_start,
        unrouted_tb_starts_in_fixtures={x:n for x,n in sorted(unrouted.items())})
    checks=[]
    def chk(cid,text,expected,observed):checks.append(dict(id=cid,claim=text,expected=expected,observed=observed,verdict='confirmed' if expected==observed else 'differs'))
    chk('P-1','every fixture (eba3e-direct, object-eb81e, sweep, input) passes its own checks (independent model / twice / fresh-CPU split)',fx_total,fx_ok)
    chk('P-2','seeds 58 and 59 complete 120 frames with the PVC banks of any value',[120,120],[r['frames_complete'] for r in seed_rows])
    chk('P-3','the 93 eba9e entries select read base 400000 (36) and 500000 (57)',{'400000':36,'500000':57},dict(bank_counts))
    chk('P-4','every one of the 93 direct fixtures and 93 object fixtures per seed is in-ROM (model ok, no guard)',[186,186],[sum(1 for r in rows_by_case[c] if r['group']=='eba3e-direct' and r['entry_index']>=0 and r['model']['ok']) + sum(1 for r in rows_by_case[c] if r['group']=='object-eb81e' and r['model']['ok']) for c in SEED_CASES])
    chk('P-5','natural eb7b6 replay (fresh CPU) equals the seed node record (exit SHA, ports SHA) and the independent model',[True,True],[r['ok'] for r in natural])
    chk('P-6','no executed TB start of the two natural nodes is outside the merged-tree routing or off the U06 contract block starts',0,sum(len(d['unrouted'])+len(d['u06_not_start']) for r in seed_rows for d in r['tb_class'].values()))
    rom_end=S.rom_stat();assert rom_end==rom_start,(rom_start,rom_end)
    report=dict(schema_version=1,tool='tools/observe_animation_machine_pvc_banks.py',tool_sha256=sha(Path(__file__).read_bytes()),scope=SCOPE_TEXT,inputs=pins,rom_stat_start=rom_start,rom_stat_end=rom_end,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000'),formula_evidence=evidence,
        memory_map=dict(identical_to='tools/observe_animation_machine_scheduler.py Machine except the banked window',banked_window='program[bank_base : bank_base + fe000] for any bank_base >= 100000 (rebuilt on every 2ffff0 / 2ffff2 WORD write); bytes past 800000 are not exposed, a read of them is the guard bank-read-outside-rom',
            routing_source=pins['metalslug-input/engine/src/animation_machine.cpp'],routing_rules=nrules,routable_pcs=sum(bitmap)),
        seeds=seed_rows,natural_eb7b6_replay=natural,
        fixtures=dict(total=fx_total,ok=fx_ok,by_group={'%s/ok=%s'%k:v for k,v in sorted(collections.Counter((r['group'],r['ok']) for r in fixture_rows).items())},
            rows=sorted(fixture_rows,key=lambda r:(r['case'],r['group'],r['name']))),
        bank_table=table,bank_read_base_counts=dict(bank_counts),u06_block_coverage=u06_cov,checks=checks,output_sizes=sizes,limitations=LIMITATIONS)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=1,sort_keys=True,default=str)+'\n')
    summary=dict(seeds=[(r['case'],r['stop'],r['frames_done'],r['first_uncovered']) for r in seed_rows],checks=[c['verdict'] for c in checks],natural_ok=[r['ok'] for r in natural],fixtures=fx_total,fixtures_ok=fx_ok,
        size_mb=round(sizes['total_bytes']/1e6,1),observation_sha256=sha(path.read_bytes()),seconds=round(time.time()-t0))
    print(json.dumps(summary,sort_keys=True,default=str))
    return summary


SCOPE_TEXT=('Native Unicorn M68000 observation of the original ROM.  The frame pass is the declared F2 model (see tools/observe_animation_machine_scheduler.py): no BIOS execution, no natural IRQ, no natural scheduler is claimed; '
    'the typed fixtures are declared host edits of captured natural states.  The ROM is never modified; no ROM or extracted data is added to Git.  The only change against the scheduler memory map is the banked window 200000..2fdfff.')
LIMITATIONS=[
    'Only the PVC WORD writes 2ffff0 / 2ffff2 are accepted (every other PVC page write is a guard, as in the scheduler Machine); MAME (and the C++ pvc_effects) recompute the bank on every write at 2ffff0..2fffff (word index >= ff8), so a ROM that writes 2ffff4..2fffff would differ.',
    'The PVC page memory keeps the raw written WORD (the PVC register side effects ff8 = (ff8 & fe00) | a0 and ff9 &= 7fff are tracked in the machine fields and the state SHA, not written back into the page): a CPU read of 2ffff0 / 2ffff2 after a write would not return MAME values.  No node executed here reads them.',
    'Odd bank bases (BYTE offsets that are not even) are modeled by the same slice but never produced by eba3e; the physical odd-address CPU behavior is not claimed.',
    'The bank list pointers are read as LONG CPU addresses and walked only inside the covered spaces (fixed ROM, work RAM mirror, banked window); the semantics of the entries (animation scripts / sprite lists) is not analysed here.',
    'Entry routability is by callback PC against the merged tree metalslug-input (HEAD a4e9253, U01..U06 routed, U07 not present); internal blocks of an executor are the executor\'s.',
]


if __name__=='__main__':main()
