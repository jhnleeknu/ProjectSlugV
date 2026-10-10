"""Unpatched 480bc frame helper bundle U4 (scene update 1a7a8 and its callees 1724c / 1726c / 1728c / 43ea8 / 1afda / 1b016 / 19e64 / 18656) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the scene core observer U2
(observe_animation_machine_scene_core and through it the frame helper observer U1 and the card menu close / fade-card chain: persistent-CPU Observer with the
declared host-change vocabulary RAM write / PC redirect / A7 delta / register write at a step boundary, fresh-twice reproduction, split (stop at the first hit of
every block leader) versus continuous equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every imported tool module, ROM SHA/mtime guard).

Observed unit: the contract bytes of docs/analysis/animation-machine-scene-update-u4-contract.md (main decision option D: debug path 1b016..1b126 implemented, 118 block
starts; X flag local to its block; 43e08/43e22 deferred to U5; path opcode 19e86 follows the computed PC).  The unit runs from 1a7a8 (BSR.W at 1a788, return LONG
1a78c) or from 1a69e (BSR.W at 1a69e, return LONG 1a6a2) to its RTS at 1a90e.  Existing executors are black boxes inside the unit and are observed natively only:
43e38 (cleanup coordinate, tail of 43ea8), 16ff8 (palette bind), 1861a (map transfer), 18702 (map transfer) and caf0 (screen, tail JMP of 1b00e).  A stop is accepted only
directly after the transferring instruction (the RTS at 1a90e popping the declared return LONG); the code behind it is never executed.

Seeds (all pinned by SHA256, rebuilt in this process):
  scene_frame  artifacts/scene_frame_execution (594 cases rebuilt from artifacts/scene_general_initialization + host writes / carried native outputs, every input RAM
               checked against input_ram_sha256).  The 22 full-path cases run natively from the direct 1a73c entry through U2 (step 1, accepted stop 1a7a8 directly after
               the BSR at 1a788) into U4 (step 2, stop 1a78c).  The first 1a7a8 state of ALL 594 original full-frame runs is captured (declared re-entry fixture: RAM, 14
               registers, A7 and the live stack bytes) and probed natively; the cases with a debug path / grid draw / path nodes / non-default axis masks are observed in full.
  stage_entry  artifacts/stage_entry_body: the original 47a94 body is re-executed by the original observer; the 22 cases that reach 1a7a8 natively through U2 are run
               like the scene cases, the 1a7a8 frame states and the 1a69e initialization states of all 142 cases are captured (declared fixtures) and sampled.
  fixtures     declared host RAM writes (applied before the first instruction of the condition) on captured states for the paths no seed executes.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step
record; declared initial registers/stack LONGs are part of the fixture summary.

An independent Python model of the contract (a basic-block machine transcribed instruction by instruction from the original bytes, 32-bit register semantics, explicit
word/byte operations, X/SUBX, MULU/MULS, ASR.L, ROL.W and DBRA, NOT the C++) is compared with each native normal condition: block-leader sequence with the full register
file at every leader, the ordered RAM writes, the ordered port writes, ordered fixed/bank ROM reads, the final registers and the whole 64KiB RAM image.  The existing
executors are black boxes: their entry registers are compared as a leader, their native exit registers, RAM writes and bank changes are replayed into the model (A7
discipline checked).  Any difference is recorded in contract_discrepancies.
"""
import collections
import copy
import gzip
import json
import os
from pathlib import Path
import random
import re
import struct
import sys
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_scene_core as sc
import observe_animation_machine_frame_helpers as fh
import observe_animation_machine_map_transfer as mt
import observe_animation_machine_cleanup as cleanup_native
import observe_animation_machine_screen as screen_native
import observe_scene_frame_execution as sfe
import observe_stage_entry_body as seb
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
fc=sc.fc;close=sc.close;menu=sc.menu;op=sc.op;activation=sc.activation;shared=sc.shared;vsf=sc.vsf
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_scene_update_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-scene-update-u4-contract.md'
CONTRACT_SHA='68855b9567d285c4bcd6d3ae3e1024d304384ed03e4b1fc3401dfe0b5a1637dc'
SCOPE=sc.SCOPE
U2_CONTRACT=sc.CONTRACT
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=sc.u32
S=fc.S                                                      # 1feffc: initial A7 (the return LONG lives here)
A5V=0x108000
M32=0xffffffff
KEYS=sc.KEYS
KEYS14=sc.KEYS14
PORT_REGIONS=fc.PORT_REGIONS
ENTRY_FRAME=0x1a7a8                                         # BSR.W at 1a788, return LONG 1a78c
ENTRY_INIT=0x1a69e                                          # BSR.W at 1a69e (initialization), return LONG 1a6a2
RET_FRAME=0x1a78c
RET_INIT=0x1a6a2
RTS_PC=0x1a90e                                              # the RTS of the unit
RETURN_FF000=sc.RETURN_FF000
DISCREPANCIES=[]
INFO=[]

# Code of the unit (contract table), the debug table (data) and the stop-bearing caller BSR of the init entry.  Existing executors: the closure ranges of the
# earlier map transfer / cleanup / screen observers (43e38, 16ff8, 1861a, 18702, caf0 and what they call).
U4_RANGES=((0x1a7a8,0x1a910),(0x1724c,0x17292),(0x43ea8,0x43eb8),(0x1afda,0x1b016),(0x19e64,0x1a07a),(0x18656,0x18702),(0x1b016,0x1b128))
DATA_RANGES=((0x1af12,0x1afd2),(0x1afd2,0x1afda))            # debug table A (96 WORDs) and B (4 WORDs); read through the live bus
INIT_CALL=(0x1a69e,0x1a6a2)                                  # BSR.W 1a7a8 of the initialization entry
EXISTING_RANGES=tuple(sorted(set(mt.RANGES)|set(cleanup_native.RANGES)|set(screen_native.RANGES)))
BB_ENTRIES=(0x43e38,0x16ff8,0x1861a,0x18702,0xcaf0)
BB_NAMES={0x43e38:'cleanup-43e38',0x16ff8:'palette-bind-16ff8',0x1861a:'map-transfer-1861a',0x18702:'map-transfer-18702',0xcaf0:'screen-caf0'}
EXTRA_LEADERS=(0x19e8a,0x19e8e,0x19e92,0x19e96,0x19e9a,0x19e9e,0x19ea2,0x19ea6)      # the eight BRA.W slots of the computed JMP at 19e86
U2_RANGES_FOR_NATURAL=()
PROBE_STOP=0x3ffffe
# net A7 change from an entry to the final RTS: a declared entry at 1a7a8 / 1a8ce has the return LONG on top (+4); at 1afda one more return LONG (1a8ce) lies above it (+8);
# the 1a69e entry executes the BSR itself (push -4, RTS +4 = 0)
ENTRY_DELTA={0x1a69e:0,0x1afda:8,0x19e64:8}


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)


def in_u4(pc):return in_ranges(pc,U4_RANGES) or INIT_CALL[0]<=pc<INIT_CALL[1]


# ----------------------------------------------------------------------------------
# Contract tables
# ----------------------------------------------------------------------------------
def parse_contract_table(program):
    rows=[];code=[]
    pattern=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)`(\([^)]*\))? \| (\d+) \| `([0-9a-f]+)` \|')
    for line in CONTRACT.read_text().splitlines():
        m=pattern.match(line)
        if not m:continue
        lo,hi=int(m.group(1),16),int(m.group(2),16);size=int(m.group(4));raw=m.group(5)
        ok=program[lo:hi].hex()==raw and hi-lo==size
        assert ok,(hex(lo),hex(hi))
        rows.append(dict(range='%x..%x'%(lo,hi),note=m.group(3) or '',size=size,bytes_equal_to_rom=ok))
        code.append((lo,hi))
    assert len(rows)==10,len(rows)
    return rows


def contract_lists():
    """Block start list (118 = 102 selection G + 16 selection D) and the bundled-branch list (46 = 37 + 9) of the contract text."""
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',text)]
    g=d=bg=bd=None
    for line in CONTRACT.read_text().splitlines():
        if line.startswith('  - 선택 G(102개):'):g=pcs(line)
        if line.startswith('  - 선택 D 추가(16개):'):d=pcs(line)
        if line.startswith('- **묶인 분기 PC(직접 진입 거부)**'):
            head,tail=line.split('선택 D 추가')
            bg=pcs(head);bd=pcs(tail)
    assert g and d and bg and bd and (len(g),len(d),len(bg),len(bd))==(102,16,37,9),(len(g or ()),len(d or ()),len(bg or ()),len(bd or ()))
    assert len(set(g)|set(d))==118
    return set(g),set(d),set(bg),set(bd)


# ----------------------------------------------------------------------------------
# Independent model: a basic-block machine (transcription of the original instructions; every block ends with exactly one control transfer)
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
BLK={}
LEADERS=frozenset()
sub16,add16,sub32,add32,asr=sc.sub16,sc.add16,sc.sub32,sc.add32,sc.asr
sx16,sx32=sc.sx16,sc.sx32


def blk(*pcs):
    def deco(fn):
        for pc in pcs:
            assert pc not in BLK,hex(pc);BLK[pc]=fn
        return fn
    return deco


def swap(v):return ((v<<16)|(v>>16))&M32


class U4Machine(fh.Machine):
    def __init__(self,program,bank,ram,regs,env):
        super().__init__(program,bank,ram,regs,env)
        self.ports=[]
    def lead(self,pc):
        assert pc in LEADERS,hex(pc)
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)
    def call(self,target,ret):self.push32(ret);return target
    def rts(self):return self.pop32()
    def rw(self,off):return self.rd(self.a5(off),2)
    def rl(self,off):return self.rd(self.a5(off),4)
    def rb(self,off):return self.rd(self.a5(off),1)
    def ww(self,off,v):self.wr(self.a5(off),2,v)
    def wl(self,off,v):self.wr(self.a5(off),4,v)
    def wb(self,off,v):self.wr(self.a5(off),1,v)
    def bclr(self,addr,bit):
        """BCLR #bit,mem (byte): the byte is written back whether or not the bit was set; returns the old bit (Z = not old)."""
        old=self.rd(addr,1);self.wr(addr,1,old&~(1<<bit)&0xff);return (old>>bit)&1
    def addw_mem(self,addr,v):self.wr(addr,2,(self.rd(addr,2)+v)&0xffff)
    def subw_mem(self,addr,v):self.wr(addr,2,(self.rd(addr,2)-v)&0xffff)


def blackbox(M,entry):
    """Existing executor: the entry registers are compared as a leader; the native exit registers, RAM writes and bank changes are replayed.  The return LONG is on the
    stack top (JSR/BSR pushed it, or the caller's return LONG for the tail JMP/BRA entries); the RTS of the callee pops it."""
    M.lead(entry);env=M.env;k=len(M.leads);nb=env['nb']
    if not (k<len(nb) and nb[k-1]['pc']==entry):raise ModelError('%s black box: native boundaries do not align at lead %d'%(BB_NAMES[entry],k))
    ret=M.rd(M.r['a7'],4);a7=M.r['a7']
    if nb[k]['pc']!=ret:raise ModelError('%s black box returned to %x, the model expects %x'%(BB_NAMES[entry],nb[k]['pc'],ret))
    call=env['bb_calls'];env['bb_calls']+=1
    if call>=len(env['bb_groups']):raise ModelError('%s black box: no native event group %d'%(BB_NAMES[entry],call))
    group=env['bb_groups'][call]
    for a,n,v in group['writes']:M.wr(a,n,v);M.writes.pop()
    for bank in group['banks']:M.bank=bank
    exit_regs=nb[k]['registers']
    if exit_regs['a7']!=(a7+4)&M32:raise ModelError('%s changed the stack depth (native exit A7 %x, entry A7 %x)'%(BB_NAMES[entry],exit_regs['a7'],a7))
    for key in fh.REGN+('a7',):M.r[key]=exit_regs[key]
    env['bb_log'].append(dict(callee=BB_NAMES[entry],call=call,a0=nb[k-1]['registers']['a0'],writes=len(group['writes']),bank_changes=len(group['banks'])))
    return ret


def bb_call(M,entry,ret):
    """JSR/BSR into an existing executor: the return LONG is pushed by the modelled instruction, the callee is the black box."""
    M.push32(ret);return blackbox(M,entry)


# ---- 1a69e (initialization entry) and the 1a7a8 body
@blk(0x1a69e)
def b1a69e(M):return M.call(0x1a7a8,0x1a6a2)


@blk(0x1a7a8)
def b1a7a8(M):
    a0=M.a5(0x538e);M.r['a0']=a0
    d0=add32(M.rl(0x53bc),M.rd(a0,4))[0];d1=add32(M.rl(0x53c0),M.rd(a0+4,4))[0];d1=sub32(d1,0x01000000)[0]
    d0=(-d0)&M32;d1=(-d1)&M32;M.r['d0']=d0;M.r['d1']=d1
    M.wr(a0+8,4,d0);M.wr(a0+12,4,d1);return M.call(0x43ea8,0x1a7d2)


@blk(0x1a7d2)
def b1a7d2(M):
    M.lw('d0',M.rw(0x5404));M.addw_mem(M.r['a0']+0x18,M.r['d0']&0xffff);M.r['a0']=0x109156
    return 0x1a7f4 if (M.rb(0x540c)>>0)&1 else 0x1a7ea
@blk(0x1a7ea)
def b1a7ea(M):M.r['d0']=M.rl(0x5396);return M.call(0x1724c,0x1a7f4)
@blk(0x1a7f4)
def b1a7f4(M):return 0x1a808 if (M.rb(0x540c)>>1)&1 else 0x1a7fe
@blk(0x1a7fe)
def b1a7fe(M):M.r['d1']=M.rl(0x539a);return M.call(0x1726c,0x1a808)
@blk(0x1a808)
def b1a808(M):return M.call(0x1728c,0x1a80e)
@blk(0x1a80e)
def b1a80e(M):
    M.lw('d0',M.rw(0x5404));M.addw_mem(M.r['a0']+0x18,M.r['d0']&0xffff);M.r['a0']=0x10b1d6
    return 0x1a830 if (M.rb(0x540c)>>2)&1 else 0x1a826
@blk(0x1a826)
def b1a826(M):M.r['d0']=M.rl(0x5396);return M.call(0x1724c,0x1a830)
@blk(0x1a830)
def b1a830(M):return 0x1a844 if (M.rb(0x540c)>>3)&1 else 0x1a83a
@blk(0x1a83a)
def b1a83a(M):M.r['d1']=M.rl(0x539a);return M.call(0x1726c,0x1a844)
@blk(0x1a844)
def b1a844(M):return M.call(0x1728c,0x1a84a)
@blk(0x1a84a)
def b1a84a(M):
    M.lw('d0',M.rw(0x5404));M.addw_mem(M.r['a0']+0x18,M.r['d0']&0xffff);M.r['a0']=0x10d256
    return 0x1a86c if (M.rb(0x540c)>>4)&1 else 0x1a862
@blk(0x1a862)
def b1a862(M):M.r['d0']=M.rl(0x5396);return M.call(0x1724c,0x1a86c)
@blk(0x1a86c)
def b1a86c(M):return 0x1a880 if (M.rb(0x540c)>>5)&1 else 0x1a876
@blk(0x1a876)
def b1a876(M):M.r['d1']=M.rl(0x539a);return M.call(0x1726c,0x1a880)
@blk(0x1a880)
def b1a880(M):return M.call(0x1728c,0x1a886)
@blk(0x1a886)
def b1a886(M):
    M.lw('d0',M.rw(0x5404));M.addw_mem(M.r['a0']+0x18,M.r['d0']&0xffff);M.r['a0']=0x10d2d6
    return 0x1a8a8 if (M.rb(0x540c)>>6)&1 else 0x1a89e
@blk(0x1a89e)
def b1a89e(M):M.r['d0']=M.rl(0x5396);return M.call(0x1724c,0x1a8a8)
@blk(0x1a8a8)
def b1a8a8(M):return 0x1a8bc if (M.rb(0x540c)>>7)&1 else 0x1a8b2
@blk(0x1a8b2)
def b1a8b2(M):M.r['d1']=M.rl(0x539a);return M.call(0x1726c,0x1a8bc)
@blk(0x1a8bc)
def b1a8bc(M):return M.call(0x1728c,0x1a8c2)
@blk(0x1a8c2)
def b1a8c2(M):
    M.lw('d0',M.rw(0x5404));M.addw_mem(M.r['a0']+0x18,M.r['d0']&0xffff);return M.call(0x1afda,0x1a8ce)
@blk(0x1a8ce)
def b1a8ce(M):M.r['a0']=0x109156;M.r['a1']=0x10d356;return M.call(0x19e64,0x1a8de)
@blk(0x1a8de)
def b1a8de(M):M.r['a0']=0x10b1d6;M.r['a1']=0x10d364;return M.call(0x19e64,0x1a8ee)
@blk(0x1a8ee)
def b1a8ee(M):M.r['a0']=0x10d256;M.r['a1']=0x10d372;return M.call(0x19e64,0x1a8fe)
@blk(0x1a8fe)
def b1a8fe(M):M.r['a0']=0x10d2d6;M.r['a1']=0x10d380;return M.call(0x19e64,0x1a90e)
@blk(0x1a90e)
def b1a90e(M):return M.rts()


# ---- 1724c / 1726c / 1728c / 43ea8: coordinate velocity scale with the byte fraction accumulator (X flag local to the block)
def scale_axis(M,src,scale_off,acc_off,out_off):
    """MOVE.W scale,D7; MOVE.W Dsrc,D6; MULU.W D7,D6; ADD.B D6,acc(A0) [X=C]; SUBX.L D5,D5; ASR.L #8,D6; SUB.L D5,D6; SWAP Dsrc; MULS.W D7,Dsrc; LSL.L #8,Dsrc;
    ADD.L D6,Dsrc; MOVE.L Dsrc,out(A0); RTS."""
    a0=M.r['a0'];M.lw('d7',M.rd(a0+scale_off,2));M.lw('d6',M.r[src]&0xffff)
    product=((M.r['d6']&0xffff)*(M.r['d7']&0xffff))&M32;M.r['d6']=product                  # MULU.W (unsigned 16 x 16 -> 32)
    old=M.rd(a0+acc_off,1);total=old+(product&0xff);M.wr(a0+acc_off,1,total&0xff);x=1 if total>0xff else 0   # ADD.B D6,mem: X = carry of the byte add
    M.env.setdefault('axis',[]).append(dict(src=src,scale=M.r['d7']&0xffff,product=product,x=x,bit31=product>>31,negative_scale=(M.r['d7']>>15)&1,high_negative=(M.r[src]>>31)&1))
    M.r['d5']=(0-0-x)&M32                                                                    # SUBX.L D5,D5 = -X
    M.r['d6']=asr(M.r['d6'],8,32)                                                            # ASR.L #8: arithmetic, the sign of the 32-bit product fills
    M.r['d6']=sub32(M.r['d6'],M.r['d5'])[0]                                                  # SUB.L D5,D6 = D6 + X
    M.r[src]=swap(M.r[src]);hi=sx16(M.r[src]);lo=sx16(M.r['d7'])
    M.r[src]=(hi*lo)&M32                                                                     # MULS.W (signed 16 x 16 -> 32)
    M.r[src]=(M.r[src]<<8)&M32;M.r[src]=add32(M.r[src],M.r['d6'])[0]
    M.wr(a0+out_off,4,M.r[src]);return M.rts()


@blk(0x1724c)
def b1724c(M):return scale_axis(M,'d0',0x28,0x2c,0x8)
@blk(0x1726c)
def b1726c(M):return scale_axis(M,'d1',0x2a,0x2d,0xc)
@blk(0x1728c)
def b1728c(M):return 0x43ea8
@blk(0x43ea8)
def b43ea8(M):
    a0=M.r['a0'];M.r['d0']=M.rd(a0+8,4);M.wr(a0,4,add32(M.rd(a0,4),M.r['d0'])[0])
    M.r['d0']=M.rd(a0+0xc,4);M.wr(a0+4,4,add32(M.rd(a0+4,4),M.r['d0'])[0])
    return blackbox(M,0x43e38)


# ---- 1afda display / debug decision and the non-debug tail
@blk(0x1afda)
def b1afda(M):
    M.r['d7']=0;M.r['d6']=0
    return 0x1afec if (M.rd(0x10f000,1)>>3)&1==0 else 0x1afea
@blk(0x1afea)
def b1afea(M):M.r['d7']=M32;return 0x1afec                                                  # MOVEQ #-1,D7
@blk(0x1afec)
def b1afec(M):return 0x1affa if (M.rd(0x10f000,1)>>4)&1==0 else 0x1aff8
@blk(0x1aff8)
def b1aff8(M):M.r['d7']=M32;return 0x1affa
@blk(0x1affa)
def b1affa(M):return 0x1b016 if M.r['d7']&0xff else 0x1b000
@blk(0x1b000)
def b1b000(M):
    M.lb('d6',M.rb(0x544e));M.wb(0x544e,M.r['d7']&0xff);return 0x1b00e if M.r['d6']&0xff else 0x1b014
@blk(0x1b00e)
def b1b00e(M):return blackbox(M,0xcaf0)                                                      # JMP caf0: its RTS returns to the caller of 1afda (1a8ce)
@blk(0x1b014)
def b1b014(M):return M.rts()


# ---- debug path 1b016..1b126 (selection D)
@blk(0x1b016)
def b1b016(M):
    M.r['d6']=0xfff80000
    for off in (0x53a2,0x53a6,0x116a,0x116e,0x31ea,0x31ee):M.wl(off,M.rl(off)&M.r['d6'])
    M.lb('d6',M.rb(0x544e));M.wb(0x544e,M.r['d7']&0xff);return 0x1b042 if M.r['d6']&0xff else 0x1b07c


def sub_pair(M,a0):
    """MOVE.L 14,18,1c,20(A0) into D0..D3; SUB.L D0,D2; SUBX.L D1,D3: Z = (SUB.L result == 0) AND (SUBX result == 0) (the SUBX Z rule); returns the BNE decision."""
    M.r['d0']=M.rd(a0+0x14,4);M.r['d1']=M.rd(a0+0x18,4);M.r['d2']=M.rd(a0+0x1c,4);M.r['d3']=M.rd(a0+0x20,4)
    r,n,z,v,c=sub32(M.r['d2'],M.r['d0']);M.r['d2']=r;x=c;z_sub=z                              # X = C = borrow of SUB.L
    d3=(M.r['d3']-M.r['d1']-x)&M32;M.r['d3']=d3
    zero=(z_sub==1 and d3==0)
    return not zero


@blk(0x1b042)
def b1b042(M):
    a0=M.a5(0x1156);M.r['a0']=a0
    return 0x1b07c if sub_pair(M,a0) else 0x1b05e
@blk(0x1b05e)
def b1b05e(M):
    M.r['a1']=M.a5(0x31d6)                                                                   # A1 is loaded, but the four MOVE.L still read A0 (quirk of the original)
    return 0x1b07c if sub_pair(M,M.r['a0']) else 0x1b07a
@blk(0x1b07a)
def b1b07a(M):return M.rts()
@blk(0x1b07c)
def b1b07c(M):M.lw('d2',0x27);M.lw('d3',0x1f);return 0x1b084
@blk(0x1b084)
def b1b084(M):
    M.lw('d4',M.r['d2']&0xffff);M.lw('d4',((M.r['d4']&0xffff)<<5)&0xffff);M.lw('d4',add16(M.r['d4'],M.r['d3'])[0]);M.lw('d4',add16(M.r['d4'],0x7000)[0])
    M.r['d4']=swap(M.r['d4']);M.lw('d4',0x320);M.r['a1']=0x1af12;M.r['a2']=0x1afd2
    return 0x1b0b8 if (M.rd(0x10f000,1)>>3)&1==0 else 0x1b0a8
@blk(0x1b0a8)
def b1b0a8(M):M.r['a0']=M.a5(0x1156);return M.call(0x1b0e0,0x1b0b0)
@blk(0x1b0b0)
def b1b0b0(M):return 0x1b0b8 if M.r['d4']&0xffff==0x320 else 0x1b0cc
@blk(0x1b0b8)
def b1b0b8(M):return 0x1b0cc if (M.rd(0x10f000,1)>>4)&1==0 else 0x1b0c4
@blk(0x1b0c4)
def b1b0c4(M):M.r['a0']=M.a5(0x31d6);return M.call(0x1b0e0,0x1b0cc)
@blk(0x1b0cc)
def b1b0cc(M):
    M.ports.append((4,0x3c0000,M.r['d4']))                                                   # MOVE.L D4,3c0000.L: one LONG port write
    M.lw('d2',M.r['d2']-1);return 0x1b084 if M.r['d2']&0xffff!=0xffff else 0x1b0d6         # DBRA D2
@blk(0x1b0d6)
def b1b0d6(M):
    M.lw('d2',0x27);M.lw('d3',M.r['d3']-1);return 0x1b084 if M.r['d3']&0xffff!=0xffff else 0x1b0de   # DBRA D3
@blk(0x1b0de)
def b1b0de(M):return M.rts()
@blk(0x1b0e0)
def b1b0e0(M):
    a0=M.r['a0']
    M.lw('d0',M.r['d2']&0xffff);M.lw('d0',((M.r['d0']&0xffff)<<3)&0xffff);M.lw('d0',sub16(M.r['d0'],M.rd(a0+0x14,2))[0])
    M.lw('d1',M.r['d3']&0xffff);M.lw('d1',((M.r['d1']&0xffff)<<3)&0xffff);M.lw('d1',add16(M.r['d1'],M.rd(a0+0x18,2))[0])
    M.lw('d0',M.r['d0']&0x1f8);M.lw('d1',M.r['d1']&0x1f8);M.lw('d1',(M.r['d1']&0xffff)>>2);M.lw('d0',((M.r['d0']&0xffff)<<4)&0xffff)
    M.lw('d0',add16(M.r['d0'],M.r['d1'])[0]);M.lw('d0',add16(M.r['d0'],0x80)[0])
    M.lw('d7',M.rd((a0+sx16(M.r['d0']))&M32,2))                                              # MOVE.W (A0,D0.W),D7
    M.lb('d7',(M.r['d7']+0x58)&0xff)                                                         # ADDI.B #58,D7
    M.r['d6']=0;M.lb('d6',M.r['d7']&0xff);M.lw('d6',(M.r['d6']&0xffff)*2)                    # MOVEQ 0,D6; MOVE.B D7,D6; ADD.W D6,D6
    M.lw('d4',M.rd((M.r['a1']+sx16(M.r['d6']))&M32,2))                                       # MOVE.W (A1,D6.W),D4
    return 0x1b126 if M.r['d4']&0xffff==0x320 else 0x1b11c
@blk(0x1b11c)
def b1b11c(M):
    M.lw('d7',M.r['d7']&0xc000);d=M.r['d7']&0xffff;M.lw('d7',((d<<3)|(d>>13))&0xffff)       # ANDI.W #c000; ROL.W #3
    M.lw('d4',(M.r['d4']&0xffff)|M.rd((M.r['a2']+sx16(M.r['d7']))&M32,2));return 0x1b126     # OR.W (A2,D7.W),D4
@blk(0x1b126)
def b1b126(M):return M.rts()


# ---- 19e64 path walk
@blk(0x19e64)
def b19e64(M):
    M.r['a2']=M.rd(M.r['a1'],4);return 0x19e70 if M.r['a2']!=0 else 0x19e6e
@blk(0x19e6e)
def b19e6e(M):return M.rts()
@blk(0x19e70)
def b19e70(M):
    M.push32(M.r['a2']);M.push32(M.r['a1'])                                                  # MOVEM.L A1-A2,-(A7): (A7)=A1, 4(A7)=A2 (A2 is stored first)
    return M.call(0x18656,0x19e7a)
@blk(0x19e7a)
def b19e7a(M):
    M.r['a1']=M.rd(M.r['a7'],4);M.r['a2']=M.rd(M.r['a7']+4,4);M.r['a7']=(M.r['a7']+8)&M32;return 0x19e7e
@blk(0x19e7e)
def b19e7e(M):
    w=M.rd(M.r['a2'],2);M.lw('d7',w);M.r['a2']=(M.r['a2']+2)&M32
    return 0x19e84 if w&0x8000 else 0x19e86
@blk(0x19e84)
def b19e84(M):return M.rts()
@blk(0x19e86)
def b19e86(M):return (0x19e8a+sx16(M.r['d7']))&M32                                           # JMP 19e8a(PC,D7.W): no range check
for _slot,_target in ((0x19e8a,0x19eaa),(0x19e8e,0x19ed0),(0x19e92,0x19f9e),(0x19e96,0x19fc4),(0x19e9a,0x19ff4),(0x19e9e,0x1a01c),(0x19ea2,0x1a068),(0x19ea6,0x19ec2)):
    def _mk(t):
        def f(M):return t
        return f
    BLK[_slot]=_mk(_target)


def next_word(M):
    w=M.rd(M.r['a2'],2);M.r['a2']=(M.r['a2']+2)&M32;return w


@blk(0x19eaa)
def b19eaa(M):
    a1=M.r['a1'];M.wr(a1+0xc,1,0x10);M.wr(a1+4,2,next_word(M));M.wr(a1+6,2,next_word(M));M.wr(a1+8,2,0);M.wr(a1+0xa,2,0);return 0x19e7e
@blk(0x19ec2)
def b19ec2(M):
    a1=M.r['a1']
    M.lw('d0',next_word(M));M.addw_mem(a1+4,M.r['d0']&0xffff);M.lw('d0',next_word(M));M.addw_mem(a1+6,M.r['d0']&0xffff);return 0x19e7e
@blk(0x19ed0)
def b19ed0(M):
    M.r['a3']=M.rd(M.r['a0']+0x2e,4);return 0x19edc if M.r['a3']!=0 else 0x19f00
@blk(0x19edc)
def b19edc(M):return 0x19ee6 if M.bclr(M.r['a1']+0xc,1) else 0x19eee
@blk(0x19ee6)
def b19ee6(M):M.lw('d0',M.rd(M.r['a3']+4,2));M.addw_mem(M.r['a1']+4,M.r['d0']&0xffff);return 0x19eee
@blk(0x19eee)
def b19eee(M):return 0x19ef8 if M.bclr(M.r['a1']+0xc,3) else 0x19f00
@blk(0x19ef8)
def b19ef8(M):M.lw('d0',M.rd(M.r['a3']+6,2));M.subw_mem(M.r['a1']+6,M.r['d0']&0xffff);return 0x19f00
@blk(0x19f00)
def b19f00(M):return 0x19f0a if M.bclr(M.r['a1']+0xc,0) else 0x19f12
@blk(0x19f0a)
def b19f0a(M):M.lw('d0',M.rd(M.r['a2']+4,2));M.subw_mem(M.r['a1']+4,M.r['d0']&0xffff);return 0x19f12
@blk(0x19f12)
def b19f12(M):return 0x19f1c if M.bclr(M.r['a1']+0xc,2) else 0x19f24
@blk(0x19f1c)
def b19f1c(M):M.lw('d0',M.rd(M.r['a2']+6,2));M.addw_mem(M.r['a1']+6,M.r['d0']&0xffff);return 0x19f24
@blk(0x19f24)
def b19f24(M):
    a1=M.r['a1']
    M.lw('d0',M.rd(a1+8,2));M.addw_mem(a1+4,M.r['d0']&0xffff);M.lw('d0',M.rd(a1+0xa,2));M.addw_mem(a1+6,M.r['d0']&0xffff)
    M.lb('d7',M.rd(M.r['a0']+0x7a,1));M.lb('d7',M.r['d7']&0xe7)
    return 0x19f4a if not M.bclr(a1+0xc,5) else 0x19f46
@blk(0x19f46)
def b19f46(M):M.r['d7']|=1<<3;return 0x19f4a
@blk(0x19f4a)
def b19f4a(M):return 0x19f54 if M.bclr(M.r['a1']+0xc,6) else 0x19f58
@blk(0x19f54)
def b19f54(M):M.r['d7']|=1<<4;return 0x19f58
@blk(0x19f58)
def b19f58(M):
    a1=M.r['a1'];M.wr(M.r['a0']+0x7a,1,M.r['d7']&0xff)
    M.lw('d0',M.rd(a1+4,2));M.lw('d1',M.rd(a1+6,2))
    M.push32(M.r['a2']);M.push32(a1);M.r['a1']=M.r['a2'];M.r['a2']=M.rd(M.r['a1']+8,4)
    return bb_call(M,0x16ff8,0x19f74)
@blk(0x19f74)
def b19f74(M):
    M.r['a1']=M.rd(M.r['a7'],4);return 0x19f8a if M.bclr(M.r['a1']+0xc,4) else 0x19f80
@blk(0x19f80)
def b19f80(M):return M.call(0x18656,0x19f86)
@blk(0x19f86)
def b19f86(M):return 0x19f90
@blk(0x19f8a)
def b19f8a(M):M.push32(0x19f90);return blackbox(M,0x1861a)
@blk(0x19f90)
def b19f90(M):
    M.r['a1']=M.pop32();M.r['a2']=M.pop32();M.r['a2']=(M.r['a2']+0xc)&M32;M.wr(M.r['a1'],4,M.r['a2']);return 0x19e7e


@blk(0x19f9e)
def b19f9e(M):
    M.lw('d7',next_word(M));M.lw('d0',M.rd(M.r['a0']+0x14,2));M.lw('d1',M.rd(M.r['a0']+0x1c,2))
    r,n,z,v,c=sub16(M.r['d1'],M.r['d0']);M.lw('d1',r);return 0x1a060 if n==0 else 0x19fae
@blk(0x19fae)
def b19fae(M):
    a0=M.r['a0'];M.lw('d1',M.rd(a0+0x32,2));M.lw('d1',add16(M.r['d1'],M.r['d7'])[0]);M.lw('d1',((M.r['d1']&0xffff)<<4)&0xffff)
    M.lw('d0',add16(M.r['d0'],M.r['d1'])[0]);r,n,z,v,c=sub16(M.r['d0'],0xffa0);M.lw('d0',r)
    return 0x1a04a if n==0 else 0x19fc0
@blk(0x19fc0)
def b19fc0(M):return 0x1a060
@blk(0x19fc4)
def b19fc4(M):
    a0=M.r['a0'];M.lw('d7',next_word(M));M.lw('d0',M.rd(a0+0x14,2));M.lw('d1',M.rd(a0+0x1c,2))
    r,n,z,v,c=sub16(M.r['d1'],M.r['d0']);M.lw('d1',r)                                         # SUB.W D0,D1; TST.W D1: V = C = 0, so BLE = Z or N
    return 0x1a060 if (z or n) else 0x19fd6
@blk(0x19fd6)
def b19fd6(M):
    a0=M.r['a0'];M.r['a3']=M.rd(a0+0x2e,4);M.lw('d1',M.rd(a0+0x32,2));M.lw('d1',add16(M.r['d1'],M.rd(M.r['a3']+4,2))[0]);M.lw('d1',add16(M.r['d1'],M.r['d7'])[0])
    M.lw('d1',((M.r['d1']&0xffff)<<4)&0xffff);M.lw('d0',add16(M.r['d0'],M.r['d1'])[0]);r,n,z,v,c=sub16(M.r['d0'],0x1a1);M.lw('d0',r)
    return 0x1a04a if n else 0x19ff0
@blk(0x19ff0)
def b19ff0(M):return 0x1a060
@blk(0x19ff4)
def b19ff4(M):
    a0=M.r['a0'];M.lw('d7',next_word(M));M.lw('d0',M.rd(a0+0x18,2));M.lw('d1',M.rd(a0+0x20,2))
    r,n,z,v,c=sub16(M.r['d1'],M.r['d0']);M.lw('d1',r)
    return 0x1a060 if (z or n) else 0x1a006
@blk(0x1a006)
def b1a006(M):
    a0=M.r['a0'];M.lw('d1',M.rd(a0+0x34,2));M.lw('d1',add16(M.r['d1'],M.r['d7'])[0]);M.lw('d1',((M.r['d1']&0xffff)<<4)&0xffff)
    M.lw('d0',add16(M.r['d0'],M.r['d1'])[0]);r,n,z,v,c=sub16(M.r['d0'],0x270);M.lw('d0',r)
    return 0x1a04a if n else 0x1a018
@blk(0x1a018)
def b1a018(M):return 0x1a060
@blk(0x1a01c)
def b1a01c(M):
    a0=M.r['a0'];M.lw('d7',next_word(M));M.lw('d0',M.rd(a0+0x18,2));M.lw('d1',M.rd(a0+0x20,2))
    r,n,z,v,c=sub16(M.r['d1'],M.r['d0']);M.lw('d1',r)
    return 0x1a060 if n==0 else 0x1a02c
@blk(0x1a02c)
def b1a02c(M):
    a0=M.r['a0'];M.r['a3']=M.rd(a0+0x2e,4);M.lw('d1',M.rd(a0+0x34,2));M.lw('d1',sub16(M.r['d1'],M.rd(M.r['a3']+6,2))[0]);M.lw('d1',add16(M.r['d1'],M.r['d7'])[0])
    M.lw('d1',((M.r['d1']&0xffff)<<4)&0xffff);M.lw('d0',add16(M.r['d0'],M.r['d1'])[0]);r,n,z,v,c=sub16(M.r['d0'],0x71);M.lw('d0',r)
    return 0x1a04a if n==0 else 0x1a046
@blk(0x1a046)
def b1a046(M):return 0x1a060
@blk(0x1a04a)
def b1a04a(M):
    a1=M.r['a1'];M.lw('d0',next_word(M));M.wr(a1+0xc,2,M.rd(a1+0xc,2)|(M.r['d0']&0xffff));M.wr(a1+8,2,next_word(M));M.wr(a1+0xa,2,next_word(M))
    M.r['a2']=M.rd(M.r['a2'],4);M.wr(a1,4,M.r['a2']);return 0x19e7e
@blk(0x1a060)
def b1a060(M):M.r['a2']=(M.r['a2']+0xa)&M32;return 0x19e7e
@blk(0x1a068)
def b1a068(M):
    a1=M.r['a1'];M.lw('d0',next_word(M));M.wr(a1+0xc,2,M.rd(a1+0xc,2)|(M.r['d0']&0xffff));M.wr(a1+8,2,next_word(M));M.wr(a1+0xa,2,next_word(M));return 0x19e7e


# ---- 18656 movement map refresh
def asrw(v):return asr(v&0xffff,4,16)


@blk(0x18656)
def b18656(M):
    M.r['a1']=M.rd(M.r['a0']+0x2e,4);return 0x18700 if M.r['a1']==0 else 0x18662
@blk(0x18662)
def b18662(M):return 0x186b2 if (M.rd(M.r['a0']+0x7a,1)>>1)&1==0 else 0x1866c
@blk(0x1866c)
def b1866c(M):
    a0=M.r['a0'];M.lw('d2',asrw(M.rd(a0+0x14,2)));M.lw('d3',asrw(M.rd(a0+0x1c,2)))
    r,n,z,v,c=sub16(M.r['d2'],M.r['d3']);M.lw('d2',r);return 0x186b2 if z else 0x1867e
@blk(0x1867e)
def b1867e(M):
    M.r['d4']=0xfffffffa;M.lw('d4',sub16(M.r['d4'],M.r['d3'])[0]);M.lw('d4',sub16(M.r['d4'],M.r['d2'])[0])
    return 0x18692 if (M.r['d2']&0xffff)>>15==0 else 0x1868a                                  # TST.W D2 ; BPL
@blk(0x1868a)
def b1868a(M):
    M.lw('d4',add16(M.r['d4'],0x20)[0]);M.lw('d4',add16(M.r['d4'],M.r['d2'])[0]);M.lw('d2',(-(M.r['d2']&0xffff))&0xffff);return 0x18692
@blk(0x18692)
def b18692(M):
    a0=M.r['a0'];M.lw('d5',0x27);M.lw('d3',asrw(M.rd(a0+0x18,2)));M.lw('d5',sub16(M.r['d5'],M.r['d3'])[0]);M.r['d3']=0x20
    M.lw('d0',M.r['d4']&0xffff);M.lw('d1',M.r['d5']&0xffff)
    M.lw('d0',sub16(M.r['d0'],M.rd(a0+0x32,2))[0]);M.lw('d1',sub16(M.r['d1'],M.rd(a0+0x34,2))[0]);M.lw('d1',(-(M.r['d1']&0xffff))&0xffff)
    return bb_call(M,0x18702,0x186b2)
@blk(0x186b2)
def b186b2(M):return 0x18700 if (M.rd(M.r['a0']+0x7a,1)>>2)&1==0 else 0x186bc
@blk(0x186bc)
def b186bc(M):
    a0=M.r['a0'];M.lw('d3',asrw(M.rd(a0+0x18,2)));M.lw('d2',asrw(M.rd(a0+0x20,2)))
    r,n,z,v,c=sub16(M.r['d3'],M.r['d2']);M.lw('d3',r);return 0x18700 if z else 0x186ce
@blk(0x186ce)
def b186ce(M):
    M.r['d5']=7;M.lw('d5',sub16(M.r['d5'],M.r['d2'])[0]);return 0x186e0 if (M.r['d3']&0xffff)>>15==0 else 0x186d8
@blk(0x186d8)
def b186d8(M):
    M.lw('d3',(-(M.r['d3']&0xffff))&0xffff);M.lw('d5',add16(M.r['d5'],0x20)[0]);M.lw('d5',add16(M.r['d5'],M.r['d3'])[0]);return 0x186e0
@blk(0x186e0)
def b186e0(M):
    a0=M.r['a0'];M.lw('d2',asrw(M.rd(a0+0x14,2)));M.lw('d4',0xfffa);M.lw('d4',sub16(M.r['d4'],M.r['d2'])[0]);M.r['d2']=0x20
    M.lw('d0',M.r['d4']&0xffff);M.lw('d1',M.r['d5']&0xffff)
    M.lw('d0',sub16(M.r['d0'],M.rd(a0+0x32,2))[0]);M.lw('d1',sub16(M.r['d1'],M.rd(a0+0x34,2))[0]);M.lw('d1',(-(M.r['d1']&0xffff))&0xffff)
    return bb_call(M,0x18702,0x18700)
@blk(0x18700)
def b18700(M):return M.rts()


def run_blocks(M,pc,stop):
    """Run the block machine from `pc` until the next PC is `stop` (not executed) or a PC without a block; returns the final PC."""
    steps=0
    while pc!=stop:
        if pc&1:raise ModelError('odd PC %x'%pc)
        fn=BLK.get(pc)
        if fn is None:return pc
        M.lead(pc);pc=fn(M);steps+=1
        if steps>2000000:raise ModelError('model step limit')
    return pc


# ----------------------------------------------------------------------------------
# Configuration, stop evidence
# ----------------------------------------------------------------------------------
RANGES=();RANGE_TABLE=[];BLOCKS=();U2_RANGES=();KEYS_PCS=();CONTRACT_G=set();CONTRACT_D=set();CONTRACT_BUNDLED=set()
POOL=fh.POOL


def configure(program,out_dir):
    global RANGES,RANGE_TABLE,BLOCKS,U2_RANGES,KEYS_PCS,LEADERS,CONTRACT_G,CONTRACT_D,CONTRACT_BUNDLED
    RANGE_TABLE=parse_contract_table(program)
    U2_RANGES,_=sc.parse_contract_ranges(program)
    CONTRACT_G,CONTRACT_D,bg,bd=contract_lists();CONTRACT_BUNDLED=bg|bd
    decoded=set(fh.leaders_of(program,U4_RANGES))|set(EXTRA_LEADERS)
    assert decoded==CONTRACT_G|CONTRACT_D,(sorted(hex(x) for x in decoded^(CONTRACT_G|CONTRACT_D)))
    LEADERS=frozenset(decoded|{ENTRY_INIT}|set(BB_ENTRIES))
    missing=sorted(hex(pc) for pc in decoded|{ENTRY_INIT} if pc not in BLK)
    assert not missing,'model has no block for %s'%missing
    extra=sorted(hex(pc) for pc in BLK if pc not in LEADERS)
    assert not extra,'model has blocks that are not leaders %s'%extra
    RANGES=U4_RANGES+(INIT_CALL,)+U2_RANGES+sc.EXISTING_RANGES+EXISTING_RANGES
    BLOCKS=tuple(sorted(LEADERS));KEYS_PCS=BLOCKS
    fc.OUT=out_dir;fc.RANGES=RANGES;fc.BOUNDARIES=BLOCKS;fc.KEY_PCS=KEYS_PCS
    fh.OUT=out_dir;POOL.clear()
    for lo,hi in U4_RANGES:assert not any(lo<=pc<hi for pc in (RET_FRAME,RET_INIT)),hex(lo)


def stop_evidence(program,p,origin=None):
    """`origin`: the first phase of the same step (split runs: the stop phase starts at a checkpoint, the step entry state is that of the first phase)."""
    origin=origin or p
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(outgoing_pc=pc,previous_pc=None,is_step_stop=True,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    if pc in sc.BOUNDARY_BSR:return sc.stop_evidence(program,p)                                  # U2 step: 1a7a8 directly after the BSR.W at 1a788
    prev=pcs[-2];ram=p['ram_after'];a7=o['a7'];inc=origin['incoming']
    assert pc in (RET_FRAME,RET_INIT) and prev==RTS_PC and program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))                                    # the popped return LONG still lies below A7
    if pc==RET_INIT and inc['pc']==ENTRY_INIT:
        assert program[0x1a69e:0x1a6a2].hex()=='6100'+'%04x'%((0x1a7a8-0x1a6a0)&0xffff) and a7==inc['a7'],(p['label'],hex(inc['pc']))
        origin='the BSR.W at 1a69e (bytes %s) pushed the return LONG %x and the RTS at 1a90e popped it (A7 after = A7 at the entry = %x)'%(program[0x1a69e:0x1a6a2].hex(),pc,a7)
    else:
        assert a7==(inc['a7']+ENTRY_DELTA.get(inc['pc'],4))&M32 and u32(origin['ram_before'],a7-ENTRY_DELTA.get(inc['pc'],4)) in (pc,0x1a8ce),(p['label'],hex(a7),hex(inc['a7']))
        origin='the return LONG %x was on the stack at the declared entry %x (A7=%x) and the RTS at 1a90e popped it (A7 after = %x)'%(pc,inc['pc'],inc['a7'],a7)
    return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),is_step_stop=True,
        reached_from='RTS at %x popped the declared return LONG %x: %s; %x is never executed'%(prev,pc,origin,pc))


def annotate(program,phases):
    first={}
    for p in phases:first.setdefault(p['step'],p)
    for p in phases:p['stop_evidence']=stop_evidence(program,p,first[p['step']])


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Native evidence for the black boxes
# ----------------------------------------------------------------------------------
def blackbox_partition(p):
    """Native evidence of the existing executors in one control phase: the boundary list without the interior of the black boxes (nested leaders have a deeper A7),
    and one event group per black-box call (consecutive events whose instruction lies outside the unit): ordered RAM writes and PVC bank changes."""
    nb=[];skip=None
    for b in p['boundaries']:
        if skip is not None:
            if b['registers']['a7']==(skip+4)&M32 and b['pc'] in LEADERS and b['pc'] not in BB_ENTRIES:skip=None;nb.append(b)
            continue
        nb.append(b)
        if b['pc'] in BB_ENTRIES:skip=b['registers']['a7']
    groups=[];cur=None
    for e in p['events']:
        if in_u4(e['pc']):cur=None;continue
        if cur is None:cur=dict(writes=[],banks=[],events=0,pcs=set());groups.append(cur)
        cur['events']+=1;cur['pcs'].add(e['pc'])
        if e['region']=='ram' and e['access']=='write':cur['writes'].append((e['address'],e['size'],int(e['bytes'],16)))
        elif e['region']=='pvc' and e['access']=='write':cur['banks'].append(e['bank_after'])
    pcs=p['pcs'][:-1];segments=0;inside=False
    for pc in pcs:
        out=not in_u4(pc)
        if out and not inside:segments+=1
        inside=out
    return nb,groups,segments


def run_model(program,p,stop):
    nb,groups,segments=blackbox_partition(p)
    if segments!=len(groups):raise ModelError('black-box segments %d <> native event groups %d'%(segments,len(groups)))
    env=dict(nb=nb,bb_groups=groups,bb_calls=0,bb_log=[],segments=segments)
    M=U4Machine(program,p['bank_before'],p['ram_before'],p['incoming'],env)
    final=run_blocks(M,p['incoming']['pc'],stop)
    M.r['pc']=final
    if env['bb_calls']!=len(groups):raise ModelError('model called %d black boxes, native has %d groups'%(env['bb_calls'],len(groups)))
    return M,nb


def check_model(program,spec,control):
    stop=spec['steps'][-1]['stop_pc'];row=dict(label=spec['label'],kind='scene-update-model')
    phases=[q for q in control if q['step']==len(spec['steps'])-1];assert len(phases)==1
    p=phases[0]
    try:M,nb=run_model(program,p,stop)
    except (ModelError,fh.ModelError,fh.StopAt,KeyError,AssertionError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=spec['label'],kind='model-could-not-follow-native',detail=repr(e)));return row
    o=p['outgoing'];bad=[]
    if M.r['pc']!=stop:bad.append(dict(what='model final PC',model=hex(M.r['pc']),native=hex(o['pc'])))
    if len(M.leads)!=len(nb):bad.append(dict(what='leader count',model=len(M.leads),native=len(nb)))
    for i,(m,n) in enumerate(zip(M.leads,nb)):
        got=dict(n['registers'])
        if m!=got:
            bad.append(dict(what='leader %d'%i,model_pc=hex(m['pc']),native_pc=hex(got['pc']),differing_registers={k:(hex(m[k]),hex(got[k])) for k in m if m[k]!=got.get(k)}));break
    ram_writes=[(e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region']=='ram' and e['access']=='write' and in_u4(e['pc'])]
    if M.writes!=ram_writes:
        first=next((i for i,(a,b) in enumerate(zip(M.writes,ram_writes)) if a!=b),min(len(M.writes),len(ram_writes)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(ram_writes),first_difference=first,model=M.writes[first:first+3],native=ram_writes[first:first+3]))
    ports=[(e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write' and in_u4(e['pc'])]
    if M.ports!=ports:bad.append(dict(what='ordered port writes',model=M.ports[:6],native=ports[:6],model_count=len(M.ports),native_count=len(ports)))
    reads=[(e['address'],e['size'],e['region']) for e in p['events'] if e['region'] in ('fixed','bank') and e['access']=='read' and in_u4(e['pc'])]
    if M.rom_reads!=reads:bad.append(dict(what='ordered fixed/bank reads',model=M.rom_reads[:6],native=reads[:6],model_count=len(M.rom_reads),native_count=len(reads)))
    final=dict(M.r)
    if final!={k:o[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(o[k])) for k in final if final[k]!=o[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if M.bank!=p['modeled_bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(p['modeled_bank'])))
    axis=M.env.get('axis',[]);entry_a7=p['incoming']['a7']
    base_a7=next((m['a7'] for m in M.leads if m['pc']==ENTRY_FRAME),entry_a7)                    # depth is measured against the A7 of the 1a7a8 level (the 1a69e entry has pushed the BSR already there)
    row.update(equal=not bad,leaders=len(M.leads),leader_pcs_distinct=len({m['pc'] for m in M.leads}),ordered_ram_writes=len(M.writes),ordered_port_writes=len(M.ports),ordered_rom_reads=len(M.rom_reads),
        ram_bytes_compared=0x10000,final_registers_compared=sorted(final),blackbox=M.env['bb_log'],model_leader_pcs=sorted({hex(m['pc']) for m in M.leads}),final_bank=hex(M.bank),
        axis_calls=len(axis),axis_x_carry=sum(a['x'] for a in axis),axis_product_bit31=sum(a['bit31'] for a in axis),axis_negative_scale=sum(a['negative_scale'] for a in axis),axis_negative_high=sum(a['high_negative'] for a in axis),
        axis_scales=sorted({a['scale'] for a in axis}),max_unit_stack_depth=max(sx32(base_a7-m['a7']) for m in M.leads if in_u4(m['pc']) or m['pc'] in BB_ENTRIES),
        max_path_stack_depth=max([(base_a7-m['a7'])&M32 for m in M.leads if in_ranges(m['pc'],((0x19e64,0x1a07a),(0x18656,0x18702))) or m['pc'] in (0x18702,0x16ff8,0x1861a)] or [0]),
        max_debug_stack_depth=max([(base_a7-m['a7'])&M32 for m in M.leads if in_ranges(m['pc'],((0x1b016,0x1b128),)) or m['pc']==0x1afda] or [0]),mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=spec['label'],kind='model-vs-native',mismatches=bad[:4]))
    return row


# ----------------------------------------------------------------------------------
# Captured declared entry states (RAM, 14 registers, A7, live stack bytes) of the ORIGINAL runs
# ----------------------------------------------------------------------------------
def last_pvc_words(ports,initial_bank=2):
    """Raw words of the last WORD writes to the PVC bank registers 2ffff0 / 2ffff2 of an original run (initial words 0 / 1000 or 0 / 2000 when it wrote none)."""
    w={0x2ffff0:0,0x2ffff2:0x1000 if initial_bank==2 else 0x2000}
    for size,address,value in ports:
        if address in w:w[address]=value
    return w[0x2ffff0],w[0x2ffff2]


class SceneStates:
    """First 1a7a8 state of the original uninterrupted full-frame run (scene_frame_execution observer) of a rebuilt seed."""
    def __init__(self,program):
        self.obs=sfe.Observer(program);self.state=None
        self.obs.cpu.hook_add(UC_HOOK_CODE,self.hit,begin=ENTRY_FRAME,end=ENTRY_FRAME)
    def hit(self,cpu,address,size,user):
        if self.state is not None:return
        a7=cpu.reg_read(sfe.m.UC_M68K_REG_A7)
        self.state=dict(pc=address,hit=1,ram=bytes(cpu.mem_read(sfe.BASE,0x10000)),regs={k:cpu.reg_read(r)&M32 for k,r in zip(sfe.KEYS,sfe.REGS)},a7=a7,
            stack=bytes(cpu.mem_read(a7,sfe.STACK+4-a7)),bank=self.obs.bank,ports=len(self.obs.ports),pvc_raw=last_pvc_words(self.obs.ports))
    def capture(self,ram,regs):
        self.state=None
        output,result,ports,info=self.obs.run(ram,[regs[k] for k in KEYS14])
        return output,info


class SebStates:
    """1a7a8 (frame call and initialization call) and 1a69e states of the original 47a94 body + 480bc tail run (stage_entry_body observer, 'begin' phase)."""
    def __init__(self,program):
        self.program=program;self.obs=seb.Observer(program);self.states=[]
        for pc in (ENTRY_INIT,ENTRY_FRAME):self.obs.cpu.hook_add(UC_HOOK_CODE,self.hit,begin=pc,end=pc)
    def hit(self,cpu,address,size,user):
        a7=cpu.reg_read(seb.m.UC_M68K_REG_A7)
        self.states.append(dict(pc=address,hit=sum(1 for s in self.states if s['pc']==address)+1,ram=bytes(cpu.mem_read(seb.BASE,0x10000)),regs={k:cpu.reg_read(r)&M32 for k,r in zip(seb.KEYS,seb.REGS)},
            a7=a7,stack=bytes(cpu.mem_read(a7,seb.STACK+4-a7)),bank=self.obs.bank,pvc_raw=last_pvc_words(self.obs.ports,self.initial_bank),a5=cpu.reg_read(seb.m.UC_M68K_REG_A5)&M32,instruction=len(self.obs.pcs),ret=int.from_bytes(cpu.mem_read(a7,4),'big')))
    def capture(self,case):
        ram,state,meta=seb.prepare_case(ROOT,self.program,case);o=self.obs;o.prepare(ram,state);self.states=[];self.initial_bank=state['bank']
        cpu=o.cpu;o.external,o.wait_visits,o.error=0,0,None
        for values in (o.pcs,o.writes,o.ports,o.reads,o.bank_reads,o.boundaries,o.prefix):values.clear()
        cpu.emu_start(cpu.reg_read(seb.m.UC_M68K_REG_PC),0xffffff,count=2000000)
        assert o.error is None,(case,o.error)
        return list(self.states),len(o.pcs)


def seb_state_fx(name,st,prov):
    """Declared entry fixture from a captured stage_entry_body state: PC (1a7a8 or 1a69e), A7 and the live stack bytes of the original run."""
    assert st['a5']==A5V and st['bank'] in (2,3),(st['a5'],st['bank'])
    raw8,raw9=st['pvc_raw'];bank,ff8,ff9=pvc_bank_update(raw8,raw9);assert bank==st['bank']*0x100000,(hex(bank),st['bank'])
    return sc.make_fx(name,st['ram'],st['regs'],((bank,ff8,ff9),sc.pvc_page(raw8,raw9)),st['pc'],st['a7'],prov,(),[(st['a7'],st['stack'])],
        role='declared entry at %x from the original 47a94 body + 480bc tail run (hit %d, instruction %d): RAM, 14 registers, A5 = 108000, A7 = %x and the %d live stack bytes (return LONG %x); PVC bank %d'%(
            st['pc'],st['hit'],st['instruction'],st['a7'],len(st['stack']),st['ret'],st['bank']))


def scene_state_fx(name,st,prov):
    """Declared 1a7a8 entry from the original full-frame run: the PVC bank state is derived from the last bank register writes of that run."""
    assert st['pc']==ENTRY_FRAME and int.from_bytes(st['stack'][:4],'big')==RET_FRAME
    raw8,raw9=st['pvc_raw'];bank,ff8,ff9=pvc_bank_update(raw8,raw9);assert bank==st['bank'],(hex(bank),hex(st['bank']))
    return sc.make_fx(name,st['ram'],st['regs'],((bank,ff8,ff9),sc.pvc_page(raw8,raw9)),ENTRY_FRAME,st['a7'],prov,(),[(st['a7'],st['stack'])],
        role='declared entry at 1a7a8 (first hit) from the original uninterrupted full-frame run: RAM, 14 registers, A5 = 108000, A7 = %x and the %d live stack bytes (return LONG 1a78c, then ff000); PVC bank %x, raw bank words %x / %x of the last bank register writes'%(
            st['a7'],len(st['stack']),bank,raw8,raw9))


# ----------------------------------------------------------------------------------
# Condition builder
# ----------------------------------------------------------------------------------
def a7_of(delta):return ('entry',delta)


def spec_for(label,group,prov,fx,setup,stop,natural,guard,checkpoints=(),delta=None):
    fx=dict(fx);fx['label']=label
    if natural:
        steps=[dict(label=label+'-u2',changes=list(setup),stop_pc=ENTRY_FRAME,checkpoints=[],a7=a7_of(-4)),
            dict(label=label,changes=[],stop_pc=stop,checkpoints=list(checkpoints),a7=a7_of(4))]
    else:
        if delta is None:delta=0 if stop==fx['entry_pc'] else ENTRY_DELTA.get(fx['entry_pc'],4)
        steps=[dict(label=label,changes=list(setup),stop_pc=stop,checkpoints=list(checkpoints),a7=a7_of(delta))]
    extra=dict(guarded=True,guard=guard) if guard is not None else {}
    return dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,**extra)


def default_stop(fx):return RET_INIT if fx['entry_pc']==ENTRY_INIT else RET_FRAME


class Builder:
    def __init__(self,program):
        self.program=program;self.specs=[];self.models=[];self.census={}
    def probe(self,label,group,prov,fx,setup,stop,natural,delta=None):
        spec=spec_for(label,group,prov,fx,setup,stop,natural,None,(),delta)
        try:phases=fc.run_condition(self.program,spec,True)
        except Exception as e:
            diag=copy.deepcopy(spec);diag['guarded']=True;diag['guard']={}
            try:last=fc.run_condition(self.program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
            except Exception as e2:info=repr(e2)
            raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(label,e,info))
        return phases
    def add(self,label,group,prov,fx,setup=(),stop=None,natural=False,guard=None,model=True,delta=None):
        fx=dict(fx);fx['label']=label
        if stop is None:stop=ENTRY_FRAME if False else default_stop(fx)
        if guard is not None:
            spec=spec_for(label,group,prov,fx,setup,stop,natural,guard,(),delta if delta is not None else 0)
            self.specs.append(spec);return spec
        phases=self.probe(label,group,prov,fx,setup,stop,natural,delta)
        last=phases[-1];pcs=last['pcs'];entry=pcs[0];order=[]
        zero=stop==fx['entry_pc'] and not natural
        if not zero:
            for pc in pcs[1:]:
                if pc in LEADERS and pc not in order and pc!=entry and pc!=pcs[-1]:order.append(pc)
        spec=spec_for(label,group,prov,fx,setup,stop,natural,None,order,delta)
        leaders=collections.Counter(pc for pc in pcs if pc in LEADERS)
        self.census[label]=dict(instructions=len(pcs)-1,leaders=set(leaders),outgoing_a7=last['outgoing']['a7'],final_pc=last['outgoing']['pc'])
        self.specs.append(spec)
        if model and not zero:self.models.append(label)
        return spec


# ----------------------------------------------------------------------------------
# Declared states captured from a native run of this unit (stop at a leader inside the unit) and declared host RAM writes
# ----------------------------------------------------------------------------------
def run_to(program,fx,setup,stop_pc):
    """One continuous native phase from the declared fixture (declared RAM writes first) to the first execution of `stop_pc`; returns the phase."""
    o=fc.Observer(program,True)
    try:
        o.prepare(dict(fx,stop_pc=stop_pc,checkpoints=[]))
        o.begin_step(stop_pc,[]);o.apply(list(setup));p=o.run()
    finally:o.close()
    assert p['guard'] is None and p['outgoing']['pc']==stop_pc,(fx['label'],p['guard'],hex(p['outgoing']['pc']))
    return p


def state_from(program,base,setup,pc,label,role):
    """A declared entry at the internal leader `pc` taken from the native state a run of `base` (with the declared `setup` writes) has when it reaches `pc`."""
    p=run_to(program,base,setup,pc)
    fx=fc.state_fixture(base,p,pc,label)
    fx['preparation']=dict(role=role,base=base['label'],base_setup_writes=len(setup),source_state_pc=pc,ram_sha256=sha(p['ram_after']),a7=hex(p['outgoing']['a7']),instructions_from_base_entry=len(p['pcs'])-1)
    fx['label']=label;fx['stop_pc']=pc;fx['expected_final_a7']=p['outgoing']['a7']
    return fx


def W(address,size,value,why=None):
    return fc.ram_write(address,size,value,why or 'declared host RAM write %x (%d bytes) = %x'%(address,size,value&((1<<(8*size))-1)))


def writes_of(d):
    """{address: (size, value)} -> declared RAM writes in address order."""
    return [W(a,sz,v) for a,(sz,v) in sorted(d.items())]


def block_writes(base,raw,why):
    """Declared RAM bytes as WORD writes (16 bytes per declared change are not needed: every WORD is one declared write)."""
    assert len(raw)%2==0 and base%2==0
    return [W(base+k,2,int.from_bytes(raw[k:k+2],'big')) for k in range(0,len(raw),2)]


# ----------------------------------------------------------------------------------
# Declared fixtures (host RAM writes before the first instruction of the condition, on states captured from the original runs / native runs of this unit)
# ----------------------------------------------------------------------------------
NODES=(0x109156,0x10b1d6,0x10d256,0x10d2d6)                  # four layer nodes (A0 of the four groups)
PATHS=(0x10d356,0x10d364,0x10d372,0x10d380)                  # their 14-byte path states (A1): +0 cursor LONG, +4/+6 reference WORD, +8/+a movement WORD, +c flags
STREAM=0x10e000                                              # declared path stream / descriptor area (zero in every base state, checked)
STREAM_LEN=0x400
POOL_W=(0,1,2,3,5,7,8,0x10,0x20,0x7f,0x80,0xff,0x100,0x140,0x1ff,0x200,0x7ffe,0x7fff,0x8000,0x8001,0xc000,0xfff0,0xfffe,0xffff,0xff00,0x4000)


def be(size,value):return (value&((1<<(8*size))-1)).to_bytes(size,'big')


def check_free(base_fx,address,length):
    ram=base_fx['ram'];assert not any(ram[address&0xffff:(address&0xffff)+length]),(base_fx['label'],hex(address))


def stream_writes(address,raw,why):
    """A declared byte block as declared WORD RAM writes (the block starts at an even address)."""
    assert address%2==0 and len(raw)%2==0
    return [W(address+k,2,int.from_bytes(raw[k:k+2],'big'),'%s: declared stream word at %x'%(why,address+k)) for k in range(0,len(raw),2)]


def axis_inputs(dx,dy):
    """Declared inputs so that 1a7a8 hands D0 = dx to 1724c and D1 = dy to 1726c (D0 = -(53bc + (538e)), D1 = -(53c0 + 4(538e) - 1000000))."""
    return {0x10d3bc:(4,0),0x10d38e:(4,(-dx)&M32),0x10d3c0:(4,0),0x10d392:(4,(0x01000000-dy)&M32)}


def axis_nodes(scales,accs):
    d={}
    for node,(sx,sy),(ax,ay) in zip(NODES,scales,accs):d[node+0x28]=(2,sx);d[node+0x2a]=(2,sy);d[node+0x2c]=(1,ax);d[node+0x2d]=(1,ay)
    return d


def axis_fixtures(B,base,prov):
    full=lambda tag,desc,d:B.add('fixture-axis-%s'%tag,'fixture-axis',desc,base,setup=writes_of(d))
    for mask in (0x01,0x02,0x03,0x40,0x80,0xc0,0xff,0x55,0xaa,0x3c,0xc3,0x10,0x20):
        full('mask-%02x'%mask,'10d40c = %02x on a full-path state at 1a7a8: bits 0/1/6/7 (and others) skip the 1724c / 1726c calls of their node (8(A0)/12(A0) keep the previous value)'%mask,{0x10d40c:(1,mask)})
    full('x-carry','ADD.B carry X=1: accumulator bytes ff, scale 0140, D0 = 3 (u16 product 3c0, low byte c0 + ff carries); the SUBX.L gives D5 = ffffffff',
        {**axis_inputs(3,5),**axis_nodes(((0x140,0x140),)*4,((0xff,0xff),)*4)})
    full('mulu-bit31','MULU product bit 31 set (S = ffff, D0.W = ffff): the ASR.L #8 sign-fills; MULS with a positive high word',
        {**axis_inputs(0x0000ffff,0x0000ffff),**axis_nodes(((0xffff,0xffff),)*4,((0x01,0x01),)*4)})
    full('muls-negative','MULS negative operands: S = 8001 (negative as WORD) and a negative high word of D0 / D1',
        {**axis_inputs(0xfffe0003,0x80010005),**axis_nodes(((0x8001,0x8001),)*4,((0x80,0x80),)*4)})
    full('muls-neg-hi-pos-scale','negative high word with the identity scale 0100 and a non-zero fraction accumulator',
        {**axis_inputs(0xfff90123,0xfffa0456),**axis_nodes(((0x100,0x100),)*4,((0x7f,0x81),)*4)})
    full('scale-zero','scale 0000: the product is 0, only the accumulator carry of the zero byte remains',
        {**axis_inputs(0x00123456,0x00654321),**axis_nodes(((0,0),)*4,((0xff,0xff),)*4)})
    rng=random.Random(20260404)
    for k in range(16):
        dx=rng.choice((0,1,0xffff,0x8000,0x7fff,0x10000,0xffff0000,0x80000000,rng.randrange(1<<32),rng.randrange(1<<32)))
        dy=rng.choice((0,1,0xffff,0x8000,0x7fff,0x10000,0xffff0000,0x80000000,rng.randrange(1<<32),rng.randrange(1<<32)))
        scales=tuple((rng.choice(POOL_W),rng.choice(POOL_W)) for _ in range(4));accs=tuple((rng.choice((0,1,0x7f,0x80,0xfe,0xff)),rng.choice((0,1,0x7f,0x80,0xfe,0xff))) for _ in range(4))
        d={**axis_inputs(dx,dy),**axis_nodes(scales,accs),0x10d40c:(1,rng.choice((0,0,0x01,0x02,0x40,0x80)))}
        full('random-%02d'%k,'seeded random inputs dx=%08x dy=%08x, per-node scales / accumulators (seed 20260404, candidate %d)'%(dx,dy,k),d)


def debug_fixtures(B,base):
    def add(tag,desc,d,extra=()):B.add('fixture-debug-%s'%tag,'fixture-debug',desc,base,setup=writes_of(d)+list(extra))
    n0,n1=NODES[0],NODES[1]
    flat=lambda n,l14,l18,l1c,l20:{n+0x14:(4,l14),n+0x18:(4,l18),n+0x1c:(4,l1c),n+0x20:(4,l20)}
    for f000,name in ((0x08,'bit3'),(0x10,'bit4'),(0x18,'both')):
        add('%s-first-frame-draw'%name,'10f000 = %02x, 10d44e = 00 (no previous debug frame): 1b016 masks the coordinates and draws the 1280 LONG grid to 3c0000 at once'%f000,{0x10f000:(1,f000),0x10d44e:(1,0)})
    for f000,name in ((0x08,'bit3'),(0x10,'bit4'),(0x18,'both')):
        add('%s-previous-equal'%name,'10f000 = %02x, 10d44e = ff, node 109156 LONG 14/18 equal 1c/20: the compare of 1b042 finds no difference (1b05e repeats it from A0), RTS without drawing'%f000,{0x10f000:(1,f000),0x10d44e:(1,0xff),**flat(n0,0,0x01000000,0,0x01000000)})
    add('previous-diff-14-1c','LONG 14 <> LONG 1c: SUB.L result <> 0, BNE draws',{0x10f000:(1,0x18),0x10d44e:(1,0xff),**flat(n0,0x00080000,0x01000000,0,0x01000000)})
    add('previous-diff-18-20','LONG 14 = 1c, LONG 18 <> 20: SUB.L result 0, SUBX result <> 0, BNE draws',{0x10f000:(1,0x18),0x10d44e:(1,0xff),**flat(n0,0,0x01000000,0,0x01080000)})
    add('previous-borrow-only','LONG 14 (08...) > 1c: the SUB.L borrow makes the SUBX result 0 (20 - 18 - 1 = 0) but the SUB.L result is non-zero: SUBX leaves Z cleared, BNE draws (sticky Z)',
        {0x10f000:(1,0x18),0x10d44e:(1,0xff),**flat(n0,0x00080000,0,0,1)})
    add('previous-borrow-and-zero','SUB.L result 0 and SUBX result 0 with a borrow chain absent: Z stays set, RTS without drawing',{0x10f000:(1,0x18),0x10d44e:(1,0xff),**flat(n0,0x00080000,0x00080000,0x00080000,0x00080000)})
    add('previous-node1-only-moved','node 10b1d6 differs but node 109156 is equal: the second compare of 1b05e re-reads A0 (109156) and the original draws nothing',
        {0x10f000:(1,0x18),0x10d44e:(1,0xff),**flat(n0,0,0x01000000,0,0x01000000),**flat(n1,0x00080000,0x01000000,0,0x01000000)})
    add('previous-node1-only-moved-bit4','bit4 only, node 10b1d6 differs: still no draw (same A0 quirk)',{0x10f000:(1,0x10),0x10d44e:(1,0xff),**flat(n0,0,0x01000000,0,0x01000000),**flat(n1,0x00080000,0x01000000,0,0x01000000)})
    # cache BYTE patterns: the lookup reads WORD (A0 + d0.w) and (BYTE + 58) * 2 indexes the table at 1af12 (96 WORDs); larger indexes read table B and the code bytes
    def cache(node,pool):
        raw=b''.join(be(2,pool[i%len(pool)]) for i in range(0x1000))
        return [W(node+0x80+k,16,int.from_bytes(raw[k:k+16],'big'),'declared tile cache bytes at %x (16 bytes of the pattern)'%(node+0x80+k)) for k in range(0,len(raw),16)]
    pools=dict(
        out_of_table=(0x0010,0x4010,0x8010,0xc010,0x0020,0x8030,0x00ff,0xc0ff,0x0000,0xc0a8),
        edge_table=(0x00a7,0x00a8,0x0107,0x0060,0x0008,0xc007,0x4008,0x80a7,0x00a8))
    for tag,pool in pools.items():
        add('cache-%s-bit3'%tag,'10f000 = 08, 10d44e = 0, node 109156 tile cache words declared (%s pattern %s): table index beyond 96 WORDs reads table B and code bytes of 1b0..'%(tag,[hex(x) for x in pool]),
            {0x10f000:(1,0x08),0x10d44e:(1,0)},cache(n0,pool))
    add('cache-out_of_table-both','10f000 = 18, both nodes declared with the out-of-table pattern',{0x10f000:(1,0x18),0x10d44e:(1,0)},cache(n0,pools['out_of_table'])+cache(n1,pools['edge_table']))
    add('cache-bit4-only','10f000 = 10, node 10b1d6 tile cache declared with the out-of-table pattern',{0x10f000:(1,0x10),0x10d44e:(1,0)},cache(n1,pools['out_of_table']))
    # non-debug tail
    for prev in (1,0x80,0xff):
        add('nondebug-previous-%02x'%prev,'10f000 = 0, 10d44e = %02x: the first non-debug frame clears the fix screen (1b00e JMP caf0, its RTS returns to 1a8ce)'%prev,{0x10f000:(1,0),0x10d44e:(1,prev)})
    add('nondebug-previous-00','10f000 = 0, 10d44e = 00: RTS at 1b014',{0x10f000:(1,0),0x10d44e:(1,0)})
    add('debug-bit5-only-is-nondebug','10f000 = 20 (bit 5 only, not a debug bit) with 10d44e = 01: non-debug path with caf0',{0x10f000:(1,0x20),0x10d44e:(1,1)})


def op00(x,y):return be(2,0)+be(2,x)+be(2,y)
def op1c(dx,dy):return be(2,0x1c)+be(2,dx)+be(2,dy)
def op18(flags,w8,w10):return be(2,0x18)+be(2,flags)+be(2,w8)+be(2,w10)
def op04(record):return be(2,4)+bytes(record)
TERM=be(2,0x8000)
ROM_RECORD=0xdc5a8                                           # a canonical opcode-04 record / node descriptor of the stage seeds (12 bytes at a fixed ROM address)


def cond_op(op,d7,flags,w8,w10,ptr):
    """Conditional path opcode (08 / 0c / 10 / 14): opcode, parameter, then the 10-byte tail: OR flags, WORD 8, WORD a, LONG next cursor (false skips exactly these 10 bytes)."""
    return be(2,op)+be(2,d7)+be(2,flags)+be(2,w8)+be(2,w10)+be(4,ptr)


def path_setup(stream,address=STREAM,node=None,state=None,node_index=0,why='declared stream'):
    """Declared writes: the stream bytes at `address`, the path state of `node_index` (cursor = address) and node fields {offset: (size, value)}."""
    p=PATHS[node_index];n=NODES[node_index]
    d={p:(4,address)}
    for off,(sz,v) in (state or {}).items():d[p+off]=(sz,v)
    for off,(sz,v) in (node or {}).items():d[n+off]=(sz,v)
    return stream_writes(address,stream,why)+writes_of(d)


def find_words(program,base,lo,hi,pattern):
    """First even address in [lo,hi) of the physical ROM (base + address) where the WORD pattern matches (None = any WORD, 'neg' = bit 15 set)."""
    for a in range(lo,hi,2):
        ok=True
        for k,w in enumerate(pattern):
            v=int.from_bytes(program[base+a+2*k:base+a+2*k+2],'big')
            if w is None:continue
            if w=='neg':
                if not v&0x8000:ok=False;break
            elif v!=w:ok=False;break
        if ok:return a
    return None


def path_fixtures(B,program,base,xbase):
    check_free(base,STREAM,STREAM_LEN)
    n0=NODES[0];T=STREAM+0x40                              # terminator word address inside the stream area
    def add(tag,desc,setup,fx=None,**kw):return B.add('fixture-path-%s'%tag,'fixture-path',desc,fx or base,setup=setup,**kw)
    term=lambda extra=b'':extra+TERM
    # opcodes 00 / 1c / 18 and chains
    add('op00','path opcode 00: BYTE 10 -> 12(A1), WORDs -> 4(A1)/6(A1), 8(A1)/10(A1) cleared',path_setup(op00(0x0123,0x0456)+TERM,why='opcode 00'))
    add('op1c','path opcode 1c: WORD deltas added to 4(A1)/6(A1)',path_setup(op00(0x7ff0,0xfff0)+op1c(0x0020,0x0030)+TERM,state={4:(2,1)},why='opcode 00 then 1c'))
    add('op1c-wrap','opcode 1c wraps the WORD references',path_setup(op00(0xffff,0x8000)+op1c(0x0001,0x8000)+TERM,why='opcode 00 then 1c with wrap'))
    add('op18-flags','path opcode 18: OR.W into the flags WORD 12(A1) and WORDs 8(A1)/10(A1)',path_setup(op18(0x4003,0x0007,0x0009)+TERM,why='opcode 18'))
    add('op18-flags-byte-d','opcode 18 OR.W on the low flags byte d (ff) together with the high byte',path_setup(op18(0x00ff,0xfffe,0x0100)+op18(0x8100,0,0)+TERM,state={0xc:(2,0x0010)},why='opcode 18 twice'))
    add('op-mixed','a stream with opcodes 00, 1c, 18 and the terminator 8000..ffff',path_setup(op00(1,2)+op1c(3,4)+op18(0x0100,5,6)+op1c(0xfffe,0xfffd)+be(2,0xffff),why='mixed opcodes'))
    add('terminator-ffff','stream starts with the terminator ffff: RTS at once after the 18656 call',path_setup(be(2,0xffff),why='terminator ffff'))
    add('index-20-lands-on-handler-00','opcode word 0020: JMP 19e8a+0020 = 19eaa, the handler 00 start (computed PC, no table check)',path_setup(be(2,0x20)+be(2,0x0111)+be(2,0x0222)+TERM,why='opcode 0020'))
    add('index-38-lands-on-handler-1c','opcode word 0038: 19e8a+0038 = 19ec2, the handler 1c start',path_setup(be(2,0x38)+be(2,0x0011)+be(2,0x0022)+TERM,why='opcode 0038'))
    add('index-1d6-lands-on-1a060','opcode word 01d6: 19e8a+01d6 = 1a060 (LEA 10(A2),A2 skip), the A2 stream continues 10 bytes later',path_setup(be(2,0x1d6)+bytes(10)+TERM,why='opcode 01d6'))
    # conditional opcodes
    cp=lambda tag,desc,stream,node,**kw:add(tag,desc,path_setup(stream,node=node,why=tag),**kw)
    end=STREAM+14                                              # cond_op is 14 bytes: the terminator follows at STREAM+14
    ptr=end
    def c08(tag,desc,w14,w1c,d7,w32=0,extra=None):
        node={0x14:(2,w14),0x1c:(2,w1c),0x32:(2,w32),0x7a:(1,0)};node.update(extra or {})
        cp('op08-'+tag,desc,cond_op(8,d7,0x0100,0x0011,0x0022,ptr)+TERM,node)
    c08('false-bpl','08: D1 = w1c-w14 >= 0 (N=0): BPL taken, false (LEA 10(A2),A2)',0x0100,0x0200,0)
    c08('true','08: D1 < 0 then D0 = w14 + ((w32+d7)<<4) - ffa0 >= 0: true branch (flags OR, WORD 8/10, cursor LONG)',0x0200,0x0100,0)
    c08('true-w32','08 true with a non-zero w32 and d7',0x0200,0x0100,0x0005,0x0010)
    c08('false-final-neg','08: first test passes, the final N=1: BRA 1a060 false',0x0200,0x0100,0xff00)
    c08('v1-n1-first','08: SUB.W overflow with N=1 (w14=9000 w1c=7000): N-only BPL does not branch; final value positive: true',0x9000,0x7000,0x0800)
    c08('v1-n1-first-final-neg','08 same first test, final negative: false',0x9000,0x7000,0)
    c08('v1-n0-first','08: SUB.W overflow with N=0 (w14=7000 w1c=9000): N-only BPL branches: false',0x7000,0x9000,0)
    c08('final-v1-n1','08: final SUBI.W overflow (7fb0 + 60 = 8010: N=1 V=1): N-only BPL does not branch: false',0x7fb0,0x0100,0)
    def c0c(tag,desc,w14,w1c,d7,w32=0,a3=None,extra=None):
        node={0x14:(2,w14),0x1c:(2,w1c),0x32:(2,w32),0x7a:(1,0),0x2e:(4,0 if a3 is None else STREAM+0x300)}
        node.update(extra or {})
        s=cond_op(0xc,d7,0x0100,0x0011,0x0022,ptr)+TERM
        setup=path_setup(s,node=node,why='op0c '+tag)
        if a3 is not None:setup=setup+stream_writes(STREAM+0x300,bytes(a3),'descriptor of node 109156 for op0c '+tag)
        add('op0c-'+tag,desc,setup)
    desc_a=lambda a,b:be(2,0)+be(2,0)+be(2,a)+be(2,b)+bytes(4)+bytes(4)
    c0c('false-eq','0c: D1 = 0 (TST.W then BLE: Z): false',0x0100,0x0100,0)
    c0c('false-neg','0c: D1 < 0: BLE taken, false',0x0200,0x0100,0)
    c0c('false-tst-clears-v','0c: SUB.W overflow N=1: TST.W clears V, BLE taken: false',0x9000,0x7000,0)
    c0c('true-bmi-true','0c: D1 > 0, A3 descriptor: D0 final N=1: true',0x0100,0x0200,0,0,desc_a(0,0))
    c0c('true-bmi-true-a3-field','0c with 4(A3) = 0010 and w32 = 0003',0x0100,0x0200,0x0001,3,desc_a(0x10,0))
    c0c('true-bmi-false','0c: D1 > 0, final N=0: false (19ff0)',0x0100,0x0200,0x0020,0,desc_a(0,0))
    c0c('true-final-v1-n0','0c: final SUBI.W overflow N=0 V=1: BMI (N only) not taken: false',0x0100,0x0200,0x0800,0,desc_a(0,0))
    c0c('true-a3-null','0c with node.2e = 0: A3 = 0, WORD 4(A3) read from the fixed ROM vector area',0x0100,0x0200,0)
    def c10(tag,desc,w18,w20,d7,w34=0):
        node={0x18:(2,w18),0x20:(2,w20),0x34:(2,w34),0x7a:(1,0)}
        cp('op10-'+tag,desc,cond_op(0x10,d7,0x0100,0x0011,0x0022,ptr)+TERM,node)
    c10('false-eq','10: w20-w18 = 0: BLE taken, false',0x0100,0x0100,0)
    c10('false-neg','10: w20 < w18: false',0x0200,0x0100,0)
    c10('true','10: w20 > w18 and final N=1: true',0x0100,0x0200,0)
    c10('false-final','10: first test passes, final N=0: false',0x0100,0x0200,0x0030)
    c10('final-v1-n0','10: final SUBI.W overflow (8200-270 = 7f90: N=0 V=1): BMI not taken: false',0x0200,0x0300,0x0800)
    c10('true-w34','10 true with w34 and d7',0x0100,0x0200,0x0002,0x0003)
    def c14(tag,desc,w18,w20,d7,w34=0,a3=None):
        node={0x18:(2,w18),0x20:(2,w20),0x34:(2,w34),0x7a:(1,0),0x2e:(4,0 if a3 is None else STREAM+0x300)}
        s=cond_op(0x14,d7,0x0100,0x0011,0x0022,ptr)+TERM
        setup=path_setup(s,node=node,why='op14 '+tag)
        if a3 is not None:setup=setup+stream_writes(STREAM+0x300,bytes(a3),'descriptor of node 109156 for op14 '+tag)
        add('op14-'+tag,desc,setup)
    c14('false-bpl','14: w20-w18 >= 0: BPL taken, false',0x0100,0x0200,0)
    c14('false-eq','14: w20 = w18: BPL taken, false',0x0100,0x0100,0)
    c14('true','14: w20 < w18, A3 descriptor, final N=0: true',0x0200,0x0100,0,0x0010,desc_a(0,0))
    c14('false-final','14: first test passes, final N=1: false',0x0200,0x0100,0,0,desc_a(0,0x0100))
    c14('true-final-v1-n0','14: final SUBI.W overflow (8040-71 = 7fcf: N=0 V=1): BPL (N only) taken: true',0x0040,0x0000,0,0x0800,desc_a(0,0))
    c14('true-a3-null','14 with node.2e = 0: WORD 6(A3) read from the fixed ROM vector area',0x0200,0x0100,0,0x0010)
    # chains: a true branch follows the cursor LONG into a second stream (opcode 00 + 1c, then the terminator), a false branch skips to the next opcode
    s2=STREAM+0x100
    chain=cond_op(8,0,0x0100,0x0011,0x0022,s2)+TERM
    chain2=op00(0x0300,0x0400)+op1c(1,1)+TERM
    node08={0x14:(2,0x0200),0x1c:(2,0x0100),0x7a:(1,0)}
    add('op08-true-chain','08 true: the cursor LONG points to a second stream (opcode 00, 1c, terminator)',path_setup(chain,node=node08,why='chain')+stream_writes(s2,chain2,'second stream'))
    node08f={0x14:(2,0x0100),0x1c:(2,0x0200),0x7a:(1,0)}
    add('op08-false-then-ops','08 false then opcode 00 and the terminator in the same stream',path_setup(cond_op(8,0,0x0100,0x0011,0x0022,s2)+op00(5,6)+TERM,node=node08f,why='false then ops'))
    # all four nodes get the same stream shape in one frame (each walks its own cursor)
    allfour=[]
    for k in range(4):
        sk=STREAM+0x100*k
        allfour+=path_setup(op00(0x10+k,0x20+k)+op1c(k,k)+TERM,address=sk,node_index=k,why='node %d stream'%k)
    add('all-four-nodes','all four path states get an own stream (opcode 00 then 1c): four walks in one frame',allfour)
    # 18656 with a null descriptor and a banked / fixed ROM stream
    add('null-descriptor-with-cursor','node.2e = 0, 7a bits 1/2 set, cursor non-null with the terminator: 18656 returns at 18700 without the map transfer',
        path_setup(TERM,node={0x2e:(4,0),0x7a:(1,0x06),0x14:(2,0x0200),0x1c:(2,0x0100),0x18:(2,0x0200),0x20:(2,0x0100)},why='null descriptor'))
    fixed=find_words(program,0,0x30000,0x80000,(0,None,None,'neg'))
    bank_off=find_words(program,0x300000,0x1000,0x80000,(0,None,None,'neg'))
    B.add('fixture-path-stream-in-fixed-rom','fixture-path','cursor LONG = %x: opcode 00 stream read from the original fixed ROM (opcode WORD 0000, two WORDs, terminator)'%fixed,base,
        setup=writes_of({PATHS[0]:(4,fixed),n0+0x2e:(4,0)}))
    B.add('fixture-path-stream-in-bank-window','fixture-path','cursor LONG = %x: the same shape read from the banked window (bank 3 active after 1a742)'%(0x200000+bank_off),base,
        setup=writes_of({PATHS[0]:(4,0x200000+bank_off),n0+0x2e:(4,0)}))
    # opcode 04 (descriptor, palette bind, 18656 / 1861a)
    record=program[ROM_RECORD:ROM_RECORD+12]
    for a3_tag,a3 in (('a3null',0),('a3rom',ROM_RECORD)):
        for flags in (0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x7f,0x03,0x0c,0x30,0x5a,0x12):
            node={0x2e:(4,a3),0x7a:(1,0x86)}
            add('op04-%s-flags-%02x'%(a3_tag,flags),'opcode 04 with the canonical record %x copied to RAM, node.2e = %x, flags byte %02x: bits 1/3 use WORD 4/6(A3), bits 0/2 WORD 4/6(A2), bits 5/6 set bits 3/4 of 7a, bit 4 selects 1861a (else 18656)'%(ROM_RECORD,a3,flags),
                path_setup(op04(record)+TERM,node=node,state={0xc:(1,flags),4:(2,0x0010),6:(2,0x0020),8:(2,0x0003),0xa:(2,0xfffe)},why='opcode 04'))


def delta_fixtures(B,base):
    """18656 -> 18702: node 109156 with the canonical descriptor and declared coordinate WORDs so that the X and Y deltas of the map refresh have both signs, zero and larger magnitudes."""
    check_free(base,STREAM,STREAM_LEN)
    def add(tag,desc,node):B.add('fixture-delta-%s'%tag,'fixture-delta',desc,base,setup=path_setup(TERM,node={**{0x2e:(4,ROM_RECORD)},**node},why='delta '+tag))
    def xy(dx,dy,bits,tag,extra=''):
        # asr.w #4 of the WORD coordinates: (w14>>4) - (w1c>>4) = dx, (w18>>4) - (w20>>4) = dy (before the sign handling of 18656)
        node={0x14:(2,(0x0400+dx*16)&0xffff),0x1c:(2,0x0400),0x18:(2,(0x0300+dy*16)&0xffff),0x20:(2,0x0300),0x7a:(1,bits),0x32:(2,0x0010),0x34:(2,0x0020)}
        add('%s-bits%02x'%(tag,bits),'node 109156 canonical descriptor, 7a = %02x, X delta %d, Y delta %d%s'%(bits,dx,dy,extra),node)
    for bits in (0x02,0x04,0x06,0x00,0x80):
        xy(0,0,bits,'zero')
    for dx in (1,-1,2,-2,3,-3,0x1f,-0x1f,0x20,-0x20):
        xy(dx,0,0x02,'x%+d'%dx)
    for dy in (1,-1,2,-2,3,-3,0x1f,-0x1f,0x20,-0x20):
        xy(0,dy,0x04,'y%+d'%dy)
    for dx,dy in ((1,1),(-1,-1),(2,-3),(-3,2),(0x20,-0x20)):
        xy(dx,dy,0x06,'xy%+d%+d'%(dx,dy))
    node={0x14:(2,0x0400),0x1c:(2,0x0400),0x18:(2,0x0300),0x20:(2,0x0300),0x7a:(1,0x06)}
    B.add('fixture-delta-null-descriptor-bits06','fixture-delta','node 109156 2e = 0, 7a = 06, deltas non-zero: 18656 returns at 18700 (null descriptor) without 18702',base,
        setup=path_setup(TERM,node={**node,0x2e:(4,0),0x14:(2,0x0500),0x18:(2,0x0200)},why='null descriptor'))


# ----------------------------------------------------------------------------------
# Census of the captured states (every state is run natively to its return and compared with the model) and the deterministic selection
# ----------------------------------------------------------------------------------
CENSUS_MODEL=dict(runs=0,equal=0,unequal=[],model_errors=[])


def census_run(program,label,fx,stop,delta):
    spec=spec_for(label,'census',{},fx,(),stop,False,None,(),delta)
    phases=fc.run_condition(program,spec,True);p=phases[-1];pcs=p['pcs']
    n_before=len(DISCREPANCIES)
    row=check_model(program,spec,phases)
    CENSUS_MODEL['runs']+=1
    if row['equal']:CENSUS_MODEL['equal']+=1
    elif 'model_error' in row:CENSUS_MODEL['model_errors'].append(dict(label=label,error=row['model_error']))
    else:CENSUS_MODEL['unequal'].append(dict(label=label,mismatches=row['mismatches'][:2]))
    ports_all=sum(1 for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write')
    return dict(label=label,instructions=len(pcs)-1,leaders=collections.Counter(pc for pc in pcs if pc in LEADERS),ports=sum(1 for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write' and in_u4(e['pc'])),ports_all=ports_all,
        model_equal=row['equal'],axis_calls=row.get('axis_calls'),axis_x_carry=row.get('axis_x_carry'),axis_product_bit31=row.get('axis_product_bit31'),axis_negative_scale=row.get('axis_negative_scale'),
        axis_negative_high=row.get('axis_negative_high'),axis_scales=row.get('axis_scales'),max_unit_stack_depth=row.get('max_unit_stack_depth'),max_path_stack_depth=row.get('max_path_stack_depth'),max_debug_stack_depth=row.get('max_debug_stack_depth'),blackbox_calls=len(row.get('blackbox',[])),
        bank_after=hex(p['modeled_bank']),first_pc=hex(pcs[0]))


def seb_stop_delta(st):
    if st['pc']==ENTRY_INIT:return RET_INIT,0
    return (RET_INIT if st['ret']==RET_INIT else RET_FRAME),4


def pick_representatives(items,key,per_signature):
    """Deterministic: for every distinct signature the first, the last and evenly spread members up to `per_signature`."""
    groups=collections.OrderedDict()
    for it in items:groups.setdefault(key(it),[]).append(it)
    out=[]
    for sig,members in groups.items():
        out+=sc.spread(members,per_signature)
    return out


# ----------------------------------------------------------------------------------
# Conditions
# ----------------------------------------------------------------------------------
NATURAL_SCENE=(36,38,86,88,91,94,95,96,172,173,176,177)+tuple(range(182,192))
NATURAL_ENTRY=(90,91,94,95,100,101,106,107,108,109,110,111)+tuple(range(118,127))+(141,)
DEBUG_NATURAL=(173,177,183,185,187,189,191)
DRAW_CASES=(129,153,592,593)
SCENE_ROWS=[]
EVIDENCE={}


def scene_state_prov(i,row,st,ram_in):
    return dict(kind='declared 1a7a8 re-entry from the original full-frame run',case=i,family=row['fixture']['family'],sequence=row['fixture'].get('sequence'),sequence_position=row['fixture'].get('sequence_position'),
        seed_index=row['fixture'].get('seed_index'),input_ram_sha256=sha(ram_in),recorded_input_ram_sha256=row['input_ram_sha256'],ram_at_1a7a8_sha256=sha(st['ram']),a7=hex(st['a7']),stack_hex=st['stack'].hex(),
        registers={k:hex(v) for k,v in st['regs'].items()},bank=hex(st['bank']),pvc_raw_words=[hex(x) for x in st['pvc_raw']],original_instructions=row['instructions'],original_calls=row['calls'],
        observation_sha256=sc.SCENE_OBS_SHA,initializer_observation_sha256=sc.SCENE_SEED_SHA)


def seb_state_prov(name,st,case,family,fixture):
    return dict(kind='declared entry from the original 47a94 body + 480bc tail run',case=case,family=family,fixture=fixture,pc=hex(st['pc']),hit=st['hit'],instruction=st['instruction'],ram_sha256=sha(st['ram']),a7=hex(st['a7']),
        return_long=hex(st['ret']),stack_hex=st['stack'].hex(),registers={k:hex(v) for k,v in st['regs'].items()},bank=st['bank'],pvc_raw_words=[hex(x) for x in st['pvc_raw']],observation_sha256=sc.STAGE_ENTRY_SHA)


def natural_conditions(B,scene_in,entry_in):
    for i in NATURAL_SCENE:
        row,ram,regs=scene_in[i];fx=sc.direct_fx('scene-%04d'%i,ram,regs,sc.scene_prov(i,row,ram))
        B.add('natural-scene-full-path-%04d'%i,'natural-scene-full-path','scene_frame_execution case %d (%s): direct 1a73c entry on the rebuilt seed, U2 to the accepted stop 1a7a8, then U4 to the stop 1a78c'%(i,row['fixture']['family']),fx,natural=True)
    by_case={c['case_index']:c for c in entry_in}
    for k in NATURAL_ENTRY:
        c=by_case[k]
        prov=dict(kind='stage_entry_body case',case=c['case_index'],family=c['family'],fixture=c['fixture'],input_ram_sha256=c['input_ram_sha256'],ram_at_1a73c_sha256=c['ram_sha256'],ports_before_1a73c=len(c['ports']),
            instructions_to_1a73c=c['instructions'],observation_sha256=sc.STAGE_ENTRY_SHA)
        B.add('natural-stage-entry-%04d'%k,'natural-stage-entry','stage_entry_body case %d (%s): 1a73c entry state of the original 47a94 body run, U2 to the accepted stop 1a7a8, then U4 to the stop 1a78c'%(k,c['family']),
            sc.entry_fx('entry-%03d'%k,c,prov),natural=True)


def captured_scene_conditions(B,scene_in,scene_states,census,per_signature):
    ram40c={i:st['ram'][0xd40c] for i,st in enumerate(scene_states)}
    sig=lambda i:(frozenset(census[i]['leaders']),census[i]['ports']>0,census[i]['blackbox_calls']>0)
    chosen=set(pick_representatives(sorted(census),sig,per_signature))
    chosen.update(DRAW_CASES);chosen.update((588,589,590,591))
    seen={}
    for i in sorted(census):
        v=ram40c[i]
        if v and v not in seen:seen[v]=i
    chosen.update(seen.values())
    # 18702 callers of each direction (X+, X-, Y+, Y-) and the debug no-draw seeds not reached natively
    for pcs in ((0x1867e,),(0x1868a,),(0x186ce,),(0x186d8,),(0x18692,0x1868a)):
        pool=[i for i in sorted(census) if all(pc in census[i]['leaders'] for pc in pcs)]
        chosen.update(sc.spread(pool,3))
    chosen-=set(NATURAL_SCENE) if False else set()
    for i in sorted(chosen):
        row,ram,regs=scene_in[i];st=scene_states[i]
        fx=scene_state_fx('scene-%04d-1a7a8'%i,st,scene_state_prov(i,row,st,ram))
        B.add('captured-scene-1a7a8-%04d'%i,'captured-scene-1a7a8','scene_frame_execution case %d (%s): first 1a7a8 state of the original full-frame run (declared entry), U4 to the stop 1a78c'%(i,row['fixture']['family']),fx)
    return sorted(chosen)


def captured_entry_conditions(B,seb_states,census,per_signature):
    items=[]
    for ci,sts,n in seb_states:
        for st in sts:items.append(('e%03d-%x-%d'%(ci,st['pc'],st['hit']),ci,st))
    sig=lambda it:(it[2]['pc'],it[2]['ret'] if it[2]['pc']==ENTRY_FRAME else 0,frozenset(census[it[0]]['leaders']),census[it[0]]['blackbox_calls']>0)
    chosen=pick_representatives(items,sig,per_signature)
    # every initialization entry shape appears with the 1a69e BSR executed natively; keep the 1a69e states first
    names=[]
    for name,ci,st in chosen:
        stop,delta=seb_stop_delta(st)
        fx=seb_state_fx(name,st,seb_state_prov(name,st,ci,None,None));fx['label']=name
        what={ENTRY_INIT:'1a69e (initialization BSR executed natively, return 1a6a2)',ENTRY_FRAME:'1a7a8'}[st['pc']]
        B.add('captured-entry-%s'%name,'captured-entry-%x'%st['pc'],'stage_entry_body case %d: declared entry at %s from the original 47a94 body + 480bc tail run (hit %d), U4 to the stop %x'%(ci,what,st['hit'],stop),fx,stop=stop)
        names.append(name)
    return names


def guard_conditions(B,program,bases):
    b36=bases['b36'];b8ce=bases['b8ce'];bafda=bases['bafda']
    ok=lambda **kv:dict(problem='unsupported_odd_data_access',**kv)
    def g(label,desc,guard,fx,setup=(),stop=None,**kw):
        B.add(label,'guard',desc,fx,setup=setup,stop=PROBE_STOP if stop is None else stop,guard=guard,model=False,**kw)
    def variant(base,role,**changes):
        f=dict(base);regs=dict(base['regs'])
        for k,v in changes.items():
            if k=='initial_a7' or k=='entry_pc':f[k]=v
            else:regs[k]=v
        f['regs']=regs;f['preparation']=dict(role=role);return f
    f=variant(b36,'declared 1a7a8 entry with declared initial A5 = 108001 (odd)',a5=0x108001)
    g('guard-odd-A5-first-read','A5 = 108001: MOVE.L 53bc(A5),D0 at 1a7ac reads an odd LONG',ok(pc=0x1a7ac,address=0x108001+0x53bc,size=4,access='read'),f)
    f=variant(b36,'declared 1a7a8 entry with declared initial A7 = 1feff9 (odd)',initial_a7=b36['initial_a7']+1)
    g('guard-odd-A7-push','A7 = 1feff9: the JSR 43ea8 at 1a7cc pushes an odd LONG',ok(pc=0x1a7cc,address=b36['initial_a7']+1-4,size=4,access='write',odd_write_restored=True),f)
    f=variant(b36,'declared entry at the RTS 1a90e with declared odd A7',entry_pc=RTS_PC,initial_a7=b36['initial_a7']+1)
    g('guard-odd-A7-rts','declared entry at 1a90e (RTS) with an odd A7: the RTS reads an odd LONG',ok(pc=RTS_PC,address=b36['initial_a7']+1,size=4,access='read'),f)
    f=variant(b36,'declared 1a7a8 entry with declared initial A5 = 8ff0 (the A0 object lies in ROM)',a5=0x8ff0)
    g('guard-rom-write-A5','A5 = 8ff0: A0 = e37e (ROM), MOVE.L D0,8(A0) at 1a7c4 writes ROM',dict(problem='unmapped_or_protected',pc=0x1a7c4,address=0x8ff0+0x538e+8,size=4),f)
    f=variant(b36,'declared 1a7a8 entry with declared initial A7 = 1100 (ROM)',initial_a7=0x1100)
    g('guard-rom-write-A7-push','A7 = 1100 (ROM): the JSR 43ea8 pushes its return LONG into ROM',dict(problem='unmapped_or_protected',pc=0x1a7cc,address=0x1100-4,size=4),f)
    # odd path pointers (declared RAM writes)
    odd=STREAM+1
    g('guard-odd-A2-cursor','path cursor LONG = odd: MOVE.W (A2)+,D7 at 19e7e reads an odd WORD',ok(pc=0x19e7e,address=odd,size=2,access='read'),b8ce,writes_of({PATHS[0]:(4,odd)}))
    rec=program[ROM_RECORD:ROM_RECORD+12]
    f=b8ce
    setup=path_setup(op04(rec)+TERM,node={0x2e:(4,STREAM+0x301),0x7a:(1,0)},state={0xc:(1,0x02)},why='opcode 04 with an odd node descriptor')
    g('guard-odd-A3-descriptor','opcode 04 with node.2e odd and the flags bit 1: MOVE.W 4(A3),D0 at 19ee6 reads an odd WORD',ok(pc=0x19ee6,address=STREAM+0x301+4,size=2,access='read'),f,setup)
    f=variant(b8ce,'declared entry at 19e64 with declared A0 = 109156, A1 = 10d357 (odd)',entry_pc=0x19e64,a0=NODES[0],a1=PATHS[0]+1)
    g('guard-odd-A1-path-state','declared entry at 19e64 with A1 odd: MOVEA.L (A1),A2 reads an odd LONG',ok(pc=0x19e64,address=PATHS[0]+1,size=4,access='read'),f)
    f=variant(b8ce,'declared entry at 19e64 with declared A0 = 109157 (odd), A1 = 10d356',entry_pc=0x19e64,a0=NODES[0]+1,a1=PATHS[0])
    g('guard-odd-A0-node','declared entry at 19e64 with A0 odd and a non-null cursor: MOVEA.L 2e(A0),A1 in 18656 reads an odd LONG',ok(pc=0x18656,address=NODES[0]+1+0x2e,size=4,access='read'),f,writes_of({PATHS[0]:(4,STREAM)})+stream_writes(STREAM,TERM,'terminator'))
    f=variant(b36,'declared entry at 1724c with declared A0 = 10d38f (odd)',entry_pc=0x1724c,a0=0x10d38f)
    g('guard-odd-A0-scale','declared entry at 1724c with A0 odd: MOVE.W 28(A0),D7 reads an odd WORD',ok(pc=0x1724c,address=0x10d38f+0x28,size=2,access='read'),f)
    f=variant(b8ce,'declared entry at 1b0e0 with declared A0 = 109157 (odd)',entry_pc=0x1b0e0,a0=NODES[0]+1,a1=0x1af12,a2=0x1afd2)
    g('guard-odd-A0-debug-lookup','declared entry at 1b0e0 (debug lookup) with A0 odd: SUB.W 14(A0),D0 reads an odd WORD',ok(pc=0x1b0e4,address=NODES[0]+1+0x14,size=2,access='read'),f)
    # computed path opcode targets without a block start / odd / far
    for tag,word,target in (('0002-mid-instruction',0x0002,0x19e8c),('0001-odd',0x0001,0x19e8b),('0006-mid-slot',0x0006,0x19e90),('7ffe-far',0x7ffe,0x19e8a+0x7ffe),('7fff-odd-far',0x7fff,0x19e8a+0x7fff)):
        g('guard-path-index-%s'%tag,'path opcode word %04x: JMP 19e8a+%04x = %x is not an executable block start (computed PC, no table check)'%(word,word,target),dict(problem='unsupported_code_target',target=target),b8ce,
            path_setup(be(2,word)+bytes(12)+TERM,why='opcode %04x'%word))
    # bad stops
    g('guard-bad-stop-1a6a2-on-frame-seed','scene seed 36 returns to 1a78c: stop declared 1a6a2, the unit returns into 1a78c (U2 code) and runs on until the declared return LONG ff000 outside every range',dict(problem='unsupported_code_target',target=RETURN_FF000),b36,stop=RET_INIT,delta=4)
    f=bases['entry_1a69e']
    g('guard-bad-stop-1a78c-on-init-entry','declared 1a69e entry returns to 1a6a2: stop declared 1a78c, the RTS lands on 1a6a2 (no executor)',dict(problem='unsupported_code_target',target=RET_INIT),f,stop=RET_FRAME,delta=0)
    B.add('boundary-zero-step','boundary','zero-step: the stop PC equals the entry PC 1a7a8; nothing is executed',b36,stop=ENTRY_FRAME)
    B.add('boundary-zero-step-1a69e','boundary','zero-step at the 1a69e initialization entry: nothing is executed',bases['entry_1a69e'],stop=ENTRY_INIT)


def negative_checks(program,B,b36):
    out=[]
    for label,stop in (('internal-return-address-1a8ce',0x1a8ce),('internal-return-address-1a7d2',0x1a7d2),('block-start-1a8de',0x1a8de)):
        spec=dict(label=label,group='negative',fixture=dict(b36,label=label),steps=[dict(label=label,changes=[],stop_pc=stop,checkpoints=[],a7=('entry',0))],provenance='negative stop check')
        phases=fc.run_condition(program,spec,True);p=phases[-1];assert p['guard'] is None and p['outgoing']['pc']==stop
        try:stop_evidence(program,p);refused=False;err=None
        except AssertionError as e:refused=True;err=repr(e)[:200]
        out.append(dict(label=label,stop=hex(stop),native_run_stopped_there=True,stop_evidence_refused=refused,error=err))
        assert refused,label
    return out


# ----------------------------------------------------------------------------------
# Evidence, claims, report
# ----------------------------------------------------------------------------------
def collect_evidence(spec,split,control,model_row):
    label=spec['label'];p=control[-1];pcs=p['pcs']
    lead=collections.Counter(pc for pc in pcs if pc in LEADERS)
    ev=dict(group=spec['group'],first_stop=hex(p['outgoing']['pc']) if p['guard'] is None else None,leaders=sorted(hex(pc) for pc in lead),leader_hits={hex(pc):n for pc,n in sorted(lead.items())},
        instructions=len(pcs)-1,ports_unit=sum(1 for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write' and in_u4(e['pc'])),
        ports_all=sum(1 for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write'))
    if p['guard'] is None:
        ev['stop_evidence']=p['stop_evidence']
        snaps=[b for b in p['boundaries'] if b['pc']==0x1b0de]
        if snaps:ev['draw']=dict(port_writes_3c0000_long=ev['ports_unit'],d2_at_1b0de=snaps[0]['registers']['d2'],d3_at_1b0de=snaps[0]['registers']['d3'])
        if model_row is not None:
            ev['model']=dict(equal=model_row.get('equal'),axis_calls=model_row.get('axis_calls'),axis_x_carry=model_row.get('axis_x_carry'),axis_product_bit31=model_row.get('axis_product_bit31'),
                axis_negative_scale=model_row.get('axis_negative_scale'),axis_negative_high=model_row.get('axis_negative_high'),max_unit_stack_depth=model_row.get('max_unit_stack_depth'),blackbox=[b['callee'] for b in model_row.get('blackbox',[])])
    EVIDENCE[label]=ev


def condition_summary(spec,split,control):
    c=control[-1];pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    called={hex(pc):pcs.count(pc) for pc in tuple(BB_ENTRIES)+(0x1afda,0x19e64,0x18656,0x1b0e0,0x1724c,0x1726c,0x1728c,0x43ea8) if pc in pcs}
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),
        called=called,ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_reads=[dict(pc=hex(e['pc']),address=hex(e['address']),size=e['size'],bank=hex(e['bank_at_read']),physical=hex(e['physical_rom_offset'])) for e in ev if e['region']=='bank'][:16],
        bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),external_reads=sum(1 for e in ev if e['region']=='external'),
        ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=fh.ordered_ports_sha(ev),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'])


def hexset(s):return sorted(hex(x) for x in s)


def contract_claims(scene_cen,seb_cen,scene_in,scene_states,seb_states,B,executed):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    leaders118=CONTRACT_G|CONTRACT_D
    sc_ok=len(scene_cen)==594 and all(c['instructions']>0 for c in scene_cen.values())
    claim('scene_frame_execution: all 594 cases run natively from their first 1a7a8 state to the return into 1a78c (bank, stack and RAM of the original full-frame run as declared entry)',
        'confirmed' if sc_ok and CENSUS_MODEL['runs']>=594 else 'contradicted',dict(cases=len(scene_cen)))
    n22=[scene_cen[i] for i in NATURAL_SCENE]
    uni=set()
    for c in n22:uni|=set(c['leaders'])&leaders118
    hit=lambda pc,rows:sum(r['leaders'].get(pc,0) for r in rows)
    claim('the 22 full-path cases use 54 block starts of the unit; 1724c / 1726c / 1728c 4x each per case (88 in total), 43e38 5x (110), no 18702 call, no port write; 15 non-debug (1b000 -> 1b014) and 7 debug (1b016 -> 1b042 -> 1b05e -> 1b07a), path cursors: 18 null cases, 4 non-null (38 95 176 177)',
        'confirmed' if (len(uni),hit(0x1724c,n22),hit(0x1726c,n22),hit(0x1728c,n22),hit(0x43e38,n22),hit(0x18702,n22),sum(r['ports_all']-0 for r in n22))==(54,88,88,88,110,0,0)
            and sum(1 for r in n22 if 0x1b000 in r['leaders'])==15 and sum(1 for r in n22 if 0x1b016 in r['leaders'])==7 else 'contradicted',
        dict(union_block_starts=len(uni),h1724c=hit(0x1724c,n22),h1726c=hit(0x1726c,n22),h1728c=hit(0x1728c,n22),h43e38=hit(0x43e38,n22),h18702=hit(0x18702,n22),nondebug=sum(1 for r in n22 if 0x1b000 in r['leaders']),debug=sum(1 for r in n22 if 0x1b016 in r['leaders']),
            ports=sum(r['ports_all'] for r in n22),nonnull_path_cases=[i for i in NATURAL_SCENE if scene_cen[i]['leaders'].get(0x19e70,0)]))
    dbg=sorted(i for i,c in scene_cen.items() if 0x1b016 in c['leaders']);draw=sorted(i for i,c in scene_cen.items() if c['ports']>0)
    claim('68 of 594 scene seeds enter the debug path 1b016, 64 of them end without a draw (1b07a); 4 (129 153 592 593) draw 1280 LONG port writes to 3c0000; 129 592 593 add the same frame 18702 transfers (1380 port events in total)',
        'confirmed' if len(dbg)==68 and draw==[129,153,592,593] and all(scene_cen[i]['ports']==1280 for i in draw) and sorted(i for i in draw if scene_cen[i]['ports_all']==1380)==[129,592,593] else 'contradicted',
        dict(debug_cases=len(dbg),draw_cases=draw,ports_unit={i:scene_cen[i]['ports'] for i in draw},ports_all={i:scene_cen[i]['ports_all'] for i in draw}))
    vals=collections.Counter(st['ram'][0xd40c] for st in scene_states)
    claim('10d40c <> 0 in 24 scene seeds with the values 04 08 14 20 3c; bits 0/1/6/7 skips are not observed by seeds',
        'confirmed' if sum(v for k,v in vals.items() if k)==24 and set(k for k in vals if k)=={0x04,0x08,0x14,0x20,0x3c} else 'contradicted',dict(values={hex(k):v for k,v in vals.items()}))
    cases_18702=[i for i,c in scene_cen.items() if c['leaders'].get(0x18702,0)]
    claim('18702 is called in the U4 interval of 375 scene cases (X delta 1867e 337, negative 1868a 325, Y delta 186ce 114, negative 186d8 80)',
        'confirmed' if (len(cases_18702),sum(1 for c in scene_cen.values() if 0x1867e in c['leaders']),sum(1 for c in scene_cen.values() if 0x1868a in c['leaders']),sum(1 for c in scene_cen.values() if 0x186ce in c['leaders']),sum(1 for c in scene_cen.values() if 0x186d8 in c['leaders']))==(375,337,325,114,80) else 'contradicted',
        dict(cases=len(cases_18702),x=sum(1 for c in scene_cen.values() if 0x1867e in c['leaders']),xneg=sum(1 for c in scene_cen.values() if 0x1868a in c['leaders']),y=sum(1 for c in scene_cen.values() if 0x186ce in c['leaders']),yneg=sum(1 for c in scene_cen.values() if 0x186d8 in c['leaders'])))
    frame=[c for c in seb_cen.values() if c['kind']=='frame']
    init=[c for c in seb_cen.values() if c['kind']=='init']
    claim('stage_entry_body: 142 frame calls 1a788 -> 1a7a8, all non-debug (1b000 -> 1b014 or caf0); 164 initialization calls 1a69e -> 1a7a8 (return 1a6a2) with path opcode 00 x234, 04 x234, 18 x4 and 1861a / 16ff8 x234 each',
        'confirmed' if len(frame)==142 and len(init)==164 and all(0x1b016 not in c['leaders'] for c in frame+init) and (sum(c['leaders'].get(0x19eaa,0) for c in init),sum(c['leaders'].get(0x19ed0,0) for c in init),sum(c['leaders'].get(0x1a068,0) for c in init),
            sum(c['leaders'].get(0x1861a,0) for c in init),sum(c['leaders'].get(0x16ff8,0) for c in init))==(234,234,4,234,234) else 'contradicted',
        dict(frame=len(frame),init=len(init),op00=sum(c['leaders'].get(0x19eaa,0) for c in init),op04=sum(c['leaders'].get(0x19ed0,0) for c in init),op18=sum(c['leaders'].get(0x1a068,0) for c in init),
            h1861a=sum(c['leaders'].get(0x1861a,0) for c in init),h16ff8=sum(c['leaders'].get(0x16ff8,0) for c in init),frame_op00=sum(c['leaders'].get(0x19eaa,0) for c in frame),frame_op04=sum(c['leaders'].get(0x19ed0,0) for c in frame),
            frame_18702=sum(c['leaders'].get(0x18702,0) for c in frame),init_18702=sum(c['leaders'].get(0x18702,0) for c in init)))
    seeds_cov=set()
    for c in list(scene_cen.values())+list(seb_cen.values()):seeds_cov|=set(c['leaders'])
    contract_unreached={0x19e92,0x19e96,0x19e9a,0x19e9e,0x19ea6,0x19ec2,0x19ee6,0x19ef8,0x19f0a,0x19f1c,0x19f46,0x19f54,0x19f80,0x19f86,0x19f9e,0x19fae,0x19fc0,0x19fc4,0x19fd6,0x19ff0,0x19ff4,0x1a006,0x1a018,0x1a01c,0x1a02c,0x1a046,0x1a04a,0x1a060,0x1b00e}
    seeds_missing=leaders118-seeds_cov
    claim('block starts never executed by the seeds (scene 594 + stage_entry 142 frame + 164 initialization states): the 29 listed by the contract (condition opcodes 08/0c/10/14 and 1c, the 04 correction bits, the 04 bit4=0 18656 path, the non-debug caf0 tail)',
        'confirmed' if seeds_missing==contract_unreached else 'contradicted',dict(seeds_missing=hexset(seeds_missing),contract_unreached=hexset(contract_unreached),only_in_seeds_missing=hexset(seeds_missing-contract_unreached),only_in_contract=hexset(contract_unreached-seeds_missing)))
    allc=list(scene_cen.values())+list(seb_cen.values())
    claim('seed X/SUBX facts: ADD.B carry X=1 never occurs and no MULU product has bit 31 set in the seeds; observed scales 0000 0020 0040 0080 0100 0140 0200 only (the model log of every native run)',
        'confirmed' if sum(c['axis_x_carry'] or 0 for c in allc)==0 and sum(c['axis_product_bit31'] or 0 for c in allc)==0 and sum(c['axis_negative_scale'] or 0 for c in allc)==0
            and set().union(*[set(c['axis_scales'] or ()) for c in allc])<={0,0x20,0x40,0x80,0x100,0x140,0x200} else 'contradicted',
        dict(calls=sum(c['axis_calls'] or 0 for c in allc),x_carry=sum(c['axis_x_carry'] or 0 for c in allc),bit31=sum(c['axis_product_bit31'] or 0 for c in allc),negative_scale=sum(c['axis_negative_scale'] or 0 for c in allc),
            scales=hexset(set().union(*[set(c['axis_scales'] or ()) for c in allc])),scene_axis_calls=sum(c['axis_calls'] or 0 for c in scene_cen.values())))
    depth=max(c['max_path_stack_depth'] for c in allc);dbg_depth=max(c['max_debug_stack_depth'] for c in allc)
    claim('stack: the unit itself uses at most 20 bytes below the 1a7a8-level A7 on the path walk (BSR 4 + MOVEM 8 + JSR 4 + BSR 18702 4) and 8 bytes on the debug path (BSR 1afda + BSR 1b0e0)',
        'confirmed' if depth==20 and dbg_depth==8 else 'understated' if depth>20 or dbg_depth>8 else 'not-reproduced',dict(max_path_depth_over_all_seed_runs=depth,max_debug_depth_over_all_seed_runs=dbg_depth,max_unit_depth=max(c['max_unit_stack_depth'] for c in allc)))
    ev=lambda label:EVIDENCE.get(label)
    def fixture_claim(text,labels,predicate):
        rows={l:ev(l) for l in labels}
        ok=all(r is not None for r in rows.values()) and predicate(rows)
        claim(text,'confirmed' if ok else 'not-reproduced',{l:(r and dict(leaders=r['leaders'])) for l,r in rows.items()})
    pc=lambda r,*xs:all(hex(x) in r['leaders'] for x in xs)
    npc=lambda r,*xs:all(hex(x) not in r['leaders'] for x in xs)
    fixture_claim('debug compare: SUBX sticky Z — LONG 14 > LONG 1c with 20-18-borrow = 0 (SUB.L result <> 0): BNE draws (1b07c); equal pairs end at 1b07a; LONG 18 <> 20 only and LONG 14 <> 1c only draw',
        ['fixture-debug-previous-borrow-only','fixture-debug-previous-borrow-and-zero','fixture-debug-previous-diff-14-1c','fixture-debug-previous-diff-18-20','fixture-debug-both-previous-equal'],
        lambda r:pc(r['fixture-debug-previous-borrow-only'],0x1b07c,0x1b0e0) and npc(r['fixture-debug-previous-borrow-only'],0x1b05e) and pc(r['fixture-debug-previous-borrow-and-zero'],0x1b05e,0x1b07a) and npc(r['fixture-debug-previous-borrow-and-zero'],0x1b07c)
            and pc(r['fixture-debug-previous-diff-14-1c'],0x1b07c) and pc(r['fixture-debug-previous-diff-18-20'],0x1b07c) and pc(r['fixture-debug-both-previous-equal'],0x1b07a))
    fixture_claim('1b05e A1/A0 quirk: only the second node (10b1d6) differs -> the repeated compare re-reads A0 (109156) and the original returns at 1b07a without drawing',
        ['fixture-debug-previous-node1-only-moved','fixture-debug-previous-node1-only-moved-bit4'],lambda r:all(pc(v,0x1b05e,0x1b07a) and npc(v,0x1b07c,0x1b0e0) for v in r.values()))
    fixture_claim('debug draw: 1280 LONG port writes to 3c0000, D2.W = 0027 and D3.W = ffff at the final RTS 1b0de; bit3 only, bit4 only and both nodes',
        ['fixture-debug-bit3-first-frame-draw','fixture-debug-bit4-first-frame-draw','fixture-debug-both-first-frame-draw'],
        lambda r:all(v['ports_unit']==1280 and v['draw']['d2_at_1b0de']&0xffff==0x27 and v['draw']['d3_at_1b0de']&0xffff==0xffff for v in r.values()) and pc(r['fixture-debug-bit3-first-frame-draw'],0x1b0a8) and npc(r['fixture-debug-bit3-first-frame-draw'],0x1b0c4)
            and pc(r['fixture-debug-bit4-first-frame-draw'],0x1b0c4) and npc(r['fixture-debug-bit4-first-frame-draw'],0x1b0a8) and pc(r['fixture-debug-both-first-frame-draw'],0x1b0a8,0x1b0c4))
    fixture_claim('debug lookup: a tile cache BYTE whose (BYTE+58) index leaves the 96-WORD table reads table B and the code bytes (1b11c OR from table B executed, fixed ROM reads beyond 1af12+0c0)',
        ['fixture-debug-cache-out_of_table-bit3'],lambda r:pc(r['fixture-debug-cache-out_of_table-bit3'],0x1b11c,0x1b126))
    fixture_claim('non-debug caf0 tail: 10d44e <> 0 with 10f000 bits 3/4 clear: 1b00e JMP caf0 (existing screen executor), its RTS returns to 1a8ce; 10d44e = 0 returns at 1b014; bit 5 only is non-debug',
        ['fixture-debug-nondebug-previous-01','fixture-debug-nondebug-previous-00','fixture-debug-debug-bit5-only-is-nondebug'],
        lambda r:pc(r['fixture-debug-nondebug-previous-01'],0x1b00e,0xcaf0,0x1a8ce) and pc(r['fixture-debug-nondebug-previous-00'],0x1b014) and npc(r['fixture-debug-nondebug-previous-00'],0x1b00e) and pc(r['fixture-debug-debug-bit5-only-is-nondebug'],0x1b00e))
    fixture_claim('path opcode 08 N-only BPL: SUB.W overflow with N=1 does not branch (true when the final value is positive), overflow with N=0 branches (false); the final SUBI.W overflow (N=1,V=1) is false',
        ['fixture-path-op08-v1-n1-first','fixture-path-op08-v1-n1-first-final-neg','fixture-path-op08-v1-n0-first','fixture-path-op08-final-v1-n1'],
        lambda r:pc(r['fixture-path-op08-v1-n1-first'],0x19fae,0x1a04a) and pc(r['fixture-path-op08-v1-n1-first-final-neg'],0x19fae,0x19fc0,0x1a060) and npc(r['fixture-path-op08-v1-n0-first'],0x19fae) and pc(r['fixture-path-op08-v1-n0-first'],0x1a060) and pc(r['fixture-path-op08-final-v1-n1'],0x19fae,0x19fc0))
    fixture_claim('path opcode 0c TST.W then BLE: D1 = 0 and D1 < 0 (also the SUB.W overflow case, TST clears V) go false; BMI is N-only (final overflow N=0 V=1 is false)',
        ['fixture-path-op0c-false-eq','fixture-path-op0c-false-neg','fixture-path-op0c-false-tst-clears-v','fixture-path-op0c-true-bmi-true','fixture-path-op0c-true-bmi-false','fixture-path-op0c-true-final-v1-n0'],
        lambda r:all(npc(r[k],0x19fd6) and pc(r[k],0x1a060) for k in ('fixture-path-op0c-false-eq','fixture-path-op0c-false-neg','fixture-path-op0c-false-tst-clears-v')) and pc(r['fixture-path-op0c-true-bmi-true'],0x19fd6,0x1a04a)
            and pc(r['fixture-path-op0c-true-bmi-false'],0x19fd6,0x19ff0) and pc(r['fixture-path-op0c-true-final-v1-n0'],0x19fd6,0x19ff0))
    fixture_claim('path opcode 10 (TST.W/BLE, BMI) and 14 (BPL, BPL): both outcomes and the final overflow (N-only) cases',
        ['fixture-path-op10-false-eq','fixture-path-op10-true','fixture-path-op10-false-final','fixture-path-op10-final-v1-n0','fixture-path-op14-false-bpl','fixture-path-op14-true','fixture-path-op14-false-final','fixture-path-op14-true-final-v1-n0'],
        lambda r:pc(r['fixture-path-op10-true'],0x1a006,0x1a04a) and pc(r['fixture-path-op10-false-final'],0x1a006,0x1a018) and pc(r['fixture-path-op10-final-v1-n0'],0x1a018) and npc(r['fixture-path-op10-false-eq'],0x1a006)
            and pc(r['fixture-path-op14-true'],0x1a02c,0x1a04a) and pc(r['fixture-path-op14-false-final'],0x1a02c,0x1a046) and pc(r['fixture-path-op14-true-final-v1-n0'],0x1a04a) and npc(r['fixture-path-op14-false-bpl'],0x1a02c))
    fixture_claim('opcodes 0c / 14 with node.2e = 0 do not check A3: the WORD at address 4 / 6 is read from the fixed ROM vector area',
        ['fixture-path-op0c-true-a3-null','fixture-path-op14-true-a3-null'],lambda r:pc(r['fixture-path-op0c-true-a3-null'],0x19fd6) and pc(r['fixture-path-op14-true-a3-null'],0x1a02c))
    fixture_claim('path opcode word policy: 0020 lands on the handler 00 (19eaa), 0038 on the handler 1c (19ec2), 01d6 on the false-skip block 1a060 (no table, no range check)',
        ['fixture-path-index-20-lands-on-handler-00','fixture-path-index-38-lands-on-handler-1c','fixture-path-index-1d6-lands-on-1a060'],
        lambda r:pc(r['fixture-path-index-20-lands-on-handler-00'],0x19e86,0x19eaa) and npc(r['fixture-path-index-20-lands-on-handler-00'],0x19e8a) and pc(r['fixture-path-index-38-lands-on-handler-1c'],0x19ec2) and npc(r['fixture-path-index-38-lands-on-handler-1c'],0x19ea6) and pc(r['fixture-path-index-1d6-lands-on-1a060'],0x1a060))
    guards=[(l,spec) for l,spec in ((s['label'],s) for s in B.specs) if l.startswith('guard-path-index')]
    claim('computed path opcode targets that are not block starts (0002 -> 19e8c, 0006 -> 19e90, 7ffe -> 21e88) or odd (0001, 7fff) stop at the first non-executable PC (unsupported code target guard)','confirmed',[l for l,_ in guards])
    fixture_claim('opcode 04: bit4 set -> 1861a map transfer, bit4 clear -> 18656 (19f80 / 19f86); bits 1 / 3 use WORD 4 / 6 of node.2e (A3), bits 0 / 2 WORD 4 / 6 of the record (A2), bits 5 / 6 set bits 3 / 4 of 7a',
        ['fixture-path-op04-a3rom-flags-00','fixture-path-op04-a3rom-flags-10','fixture-path-op04-a3rom-flags-01','fixture-path-op04-a3rom-flags-02','fixture-path-op04-a3rom-flags-04','fixture-path-op04-a3rom-flags-08','fixture-path-op04-a3rom-flags-20','fixture-path-op04-a3rom-flags-40','fixture-path-op04-a3null-flags-02'],
        lambda r:pc(r['fixture-path-op04-a3rom-flags-00'],0x19f80,0x19f86) and npc(r['fixture-path-op04-a3rom-flags-00'],0x19f8a) and pc(r['fixture-path-op04-a3rom-flags-10'],0x19f8a) and npc(r['fixture-path-op04-a3rom-flags-10'],0x19f80)
            and pc(r['fixture-path-op04-a3rom-flags-01'],0x19f0a) and pc(r['fixture-path-op04-a3rom-flags-04'],0x19f1c) and pc(r['fixture-path-op04-a3rom-flags-02'],0x19ee6) and pc(r['fixture-path-op04-a3rom-flags-08'],0x19ef8)
            and pc(r['fixture-path-op04-a3rom-flags-20'],0x19f46) and pc(r['fixture-path-op04-a3rom-flags-40'],0x19f54) and npc(r['fixture-path-op04-a3null-flags-02'],0x19ee6) and pc(r['fixture-path-op04-a3null-flags-02'],0x19f00))
    claim('node.2e descriptor null (cursor non-null): 18656 returns at 18700 without 18702','confirmed' if ev('fixture-path-null-descriptor-with-cursor') and pc(ev('fixture-path-null-descriptor-with-cursor'),0x18656,0x18700) and npc(ev('fixture-path-null-descriptor-with-cursor'),0x18692,0x186e0,0x18702) else 'not-reproduced',
        dict(leaders=ev('fixture-path-null-descriptor-with-cursor') and ev('fixture-path-null-descriptor-with-cursor')['leaders']))
    xs=[l for l in EVIDENCE if l.startswith('fixture-axis-')]
    claim('axis fixtures: ADD.B carry X=1 (SUBX.L D5 = ffffffff), MULU product bit 31 (ASR.L sign fill) and negative MULS operands are all exercised by declared fixtures (model log of the native runs)','confirmed' if
        sum(EVIDENCE[l]['model']['axis_x_carry'] for l in xs if 'model' in EVIDENCE[l])>0 and sum(EVIDENCE[l]['model']['axis_product_bit31'] for l in xs if 'model' in EVIDENCE[l])>0
        and sum(EVIDENCE[l]['model']['axis_negative_scale'] for l in xs if 'model' in EVIDENCE[l])>0 and sum(EVIDENCE[l]['model']['axis_negative_high'] for l in xs if 'model' in EVIDENCE[l])>0 else 'not-reproduced',
        dict(x_carry=sum(EVIDENCE[l]['model']['axis_x_carry'] for l in xs if 'model' in EVIDENCE[l]),bit31=sum(EVIDENCE[l]['model']['axis_product_bit31'] for l in xs if 'model' in EVIDENCE[l]),
            negative_scale=sum(EVIDENCE[l]['model']['axis_negative_scale'] for l in xs if 'model' in EVIDENCE[l]),negative_high=sum(EVIDENCE[l]['model']['axis_negative_high'] for l in xs if 'model' in EVIDENCE[l]),conditions=len(xs)))
    masks=[l for l in EVIDENCE if l.startswith('fixture-axis-mask-')]
    claim('10d40c bits 0/1/6/7 (and the other bits) skip their 1724c / 1726c call (1728c and 43ea8 always run): every mask fixture hits 1728c 4x and the 1724c / 1726c counts equal the number of clear bits',
        'confirmed' if all(EVIDENCE[l]['leader_hits'].get('0x1728c')==4 for l in masks) and all(EVIDENCE[l]['leader_hits'].get('0x1724c',0)+EVIDENCE[l]['leader_hits'].get('0x1726c',0)==8-bin(int(l[-2:],16)).count('1') for l in masks) else 'contradicted',dict(conditions=len(masks)))
    claim('block start list: the observer decode of the contract bytes (branch / call targets, returns, range starts, the eight BRA.W slots of the computed JMP) gives exactly the 118 block starts of the contract (102 selection G + 16 selection D); none of the 46 bundled branch PCs is a block start',
        'confirmed' if not (CONTRACT_BUNDLED&LEADERS) else 'contradicted',dict(block_starts=len(leaders118),bundled=len(CONTRACT_BUNDLED),bundled_that_are_leaders=hexset(CONTRACT_BUNDLED&LEADERS)))
    claim('CCR/carry values (carry-preserving classification, the Unknown-carry API) and the X flag after a block: SR is never read; the X consumers (17258 17278 1b058 1b074) are checked through register results only (D5 = -X, the SUBX result and the BNE decision)','not-observable','SR is never read')
    claim('block-internal and bundled-branch PC entry rejection of the API','not-observable','the observer allows any decoded instruction PC of the unit as a declared entry; the API rejection is not observable natively')
    return claims


def build_bases(program,scene_in,scene_states,seb_states):
    row,ram,regs=scene_in[36];st=scene_states[36]
    b36=scene_state_fx('scene-0036-1a7a8',st,scene_state_prov(36,row,st,ram));b36['label']='base-scene-36'
    b8ce=state_from(program,b36,[],0x1a8ce,'base-scene-36-at-1a8ce','declared entry at 1a8ce (after the BSR 1afda returned at 1b014): the native state of the original 1a7a8 state of scene case 36, all four path cursors null, node fields and 10f000 / 10d44e as of the seed')
    bafda=state_from(program,b36,[],0x1afda,'base-scene-36-at-1afda','declared entry at 1afda (BSR 1afda from 1a8c2, return LONG 1a8ce on the stack): the native state of the original 1a7a8 state of scene case 36')
    entry_init=None
    for ci,sts,n in seb_states:
        for s in sts:
            if s['pc']==ENTRY_INIT and entry_init is None:
                entry_init=seb_state_fx('entry-%03d-1a69e'%ci,s,seb_state_prov('init',s,ci,None,None));entry_init['label']='base-entry-init'
    assert entry_init is not None
    return dict(b36=b36,b8ce=b8ce,bafda=bafda,entry_1a69e=entry_init)


def main():
    global SCENE_ROWS
    dev_filter=sys.argv[1] if len(sys.argv)>1 else None
    out_dir=OUT if dev_filter is None else Path('/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/u4/dev_out')
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    configure(program,out_dir)
    scene_obs,scene_in=sc.scene_inputs(program);SCENE_ROWS=scene_in
    entry_obs,entry_in=sc.stage_entry_inputs(program)
    print('seeds',len(scene_in),len(entry_in),flush=True)
    cap=SceneStates(program);scene_states=[]
    for i,(row,ram,regs) in enumerate(scene_in):
        output,info=cap.capture(ram,regs);assert sha(output)==row['ram_sha256'] and info['returned'] and cap.state is not None,i
        scene_states.append(cap.state)
    sebcap=SebStates(program);seb_states=[]
    for row in entry_obs['results']:
        sts,n=sebcap.capture(row['fixture'])
        for s in sts:s['case']=row['case_index']
        seb_states.append((row['case_index'],sts,n))
    print('captured',len(scene_states),sum(len(s) for _,s,_ in seb_states),flush=True)
    scene_cen={}
    for i,st in enumerate(scene_states):
        row,ram,regs=scene_in[i]
        fx=scene_state_fx('census-%04d'%i,st,{});scene_cen[i]=census_run(program,'census-scene-%04d'%i,fx,RET_FRAME,4)
    seb_cen={}
    for ci,sts,n in seb_states:
        for st in sts:
            name='e%03d-%x-%d'%(ci,st['pc'],st['hit']);stop,delta=seb_stop_delta(st)
            fx=seb_state_fx(name,st,{});c=census_run(program,'census-'+name,fx,stop,delta)
            c['kind']='init' if st['pc']==ENTRY_INIT else ('frame' if st['ret']==RET_FRAME else 'init-1a7a8');c['case']=ci;seb_cen[name]=c
    print('census done',len(scene_cen),len(seb_cen),'model runs',CENSUS_MODEL['runs'],'equal',CENSUS_MODEL['equal'],flush=True)
    bases=build_bases(program,scene_in,scene_states,seb_states)
    B=Builder(program)
    natural_conditions(B,scene_in,entry_in)
    captured_scene_conditions(B,scene_in,scene_states,scene_cen,3)
    captured_entry_conditions(B,seb_states,seb_cen,3)
    axis_fixtures(B,bases['b36'],{});debug_fixtures(B,bases['bafda']);path_fixtures(B,program,bases['b8ce'],None);delta_fixtures(B,bases['b8ce'])
    guard_conditions(B,program,bases)
    covered=set()
    for c in B.census.values():covered|=c['leaders']
    print('conditions',len(B.specs),'model-covered block starts',len((CONTRACT_G|CONTRACT_D)&covered),'of 118 missing',hexset((CONTRACT_G|CONTRACT_D)-covered),flush=True)
    specs=B.specs
    if dev_filter:specs=[s for s in specs if dev_filter in s['label']]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,sc.CONTRACT,fh.CONTRACT,sc.STAGE_FRAME}
    input_paths.update(Path(p) for p in sc.SEED_FILES)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin_ref=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin_ref['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);model_checks=[];summaries=[];coverage_by=collections.defaultdict(list)
    for number,spec in enumerate(specs):
        split,control=run_spec(program,spec)
        row=None
        if spec['label'] in B.models and spec.get('guarded') is None:row=check_model(program,spec,control);model_checks.append(row)
        summaries.append(condition_summary(spec,split,control));collect_evidence(spec,split,control,row)
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        for pc in set(pc for q in control for pc in q['pcs'])&LEADERS:coverage_by[pc].append(spec['label'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=fh.store('c%03d_split'%number,split,KEYS_PCS),continuous_control=fh.store('c%03d_control'%number,control,KEYS_PCS),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=False,stored_from_step=0)
        for rows in (result['phases'],result['continuous_control']):
            for r in rows:artifacts.update(r['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else '',
            ' MODEL %s'%('ok' if row['equal'] else 'MISMATCH') if row is not None else ''),flush=True)
    negatives=negative_checks(program,B,bases['b36'])
    instructions=[]
    for lo,hi in U4_RANGES+(INIT_CALL,):instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,u4_ranges=U4_RANGES,init_call=INIT_CALL,data_ranges=DATA_RANGES,existing_ranges=EXISTING_RANGES,u2_ranges=U2_RANGES,instructions=instructions,boundary_stop_pcs=(RET_FRAME,RET_INIT),
        stop_rules={'return LONGs':{hex(RET_FRAME):dict(rts_pc=hex(RTS_PC),caller='BSR.W at 1a788 (U2) or the declared caller'),hex(RET_INIT):dict(rts_pc=hex(RTS_PC),caller='BSR.W at 1a69e executed natively')},'u2 step':'1a7a8 directly after the BSR.W at 1a788 (the U2 boundary stop rule)'},
        black_boxes={hex(k):v for k,v in BB_NAMES.items()},new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in U4_RANGES},debug_table={hex(lo):program[lo:hi].hex() for lo,hi in DATA_RANGES}),indent=2)+'\n').encode()
    (out_dir/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    def aggregate(rows):
        t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
        for r in rows:
            for ph in r['phases']:
                for k,v in ph['counts'].items():t[k]+=v
        return t
    guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard']) for g in guards]
    group_counts={}
    for r in results+guards:group_counts[r['group']]=group_counts.get(r['group'],0)+1
    claims=contract_claims(scene_cen,seb_cen,scene_in,scene_states,seb_states,B,EVIDENCE) if not dev_filter else []
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    leaders118=CONTRACT_G|CONTRACT_D
    missing_native=hexset(LEADERS-coverage)
    block_coverage=[dict(pc=hex(pc),in_contract_list=pc in leaders118,selection='G' if pc in CONTRACT_G else ('D' if pc in CONTRACT_D else 'observer-only'),conditions=len(coverage_by.get(pc,())),
        first_condition=(coverage_by.get(pc) or [None])[0],groups=sorted({next(s['group'] for s in specs if s['label']==l) for l in coverage_by.get(pc,())})) for pc in sorted(LEADERS)]
    census_report=dict(scene=[dict(case=i,instructions=c['instructions'],leaders=hexset(c['leaders']),ports_unit=c['ports'],ports_all=c['ports_all'],model_equal=c['model_equal'],blackbox_calls=c['blackbox_calls']) for i,c in sorted(scene_cen.items())],
        stage_entry=[dict(label=k,kind=c['kind'],case=c['case'],instructions=c['instructions'],leaders=hexset(c['leaders']),ports_unit=c['ports'],ports_all=c['ports_all'],model_equal=c['model_equal'],blackbox_calls=c['blackbox_calls']) for k,c in sorted(seb_cen.items())],
        model_runs=CENSUS_MODEL['runs'],model_equal=CENSUS_MODEL['equal'],model_unequal=CENSUS_MODEL['unequal'][:20],model_errors=CENSUS_MODEL['model_errors'][:20])
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=0,variant_child_layouts=[],guard_reports=guard_reports,negative_stop_checks=negatives,bank_reads_by_condition=[dict(label=s['label'],bank_read_count=s['bank_read_count'],reads=s['bank_reads']) for s in summaries if s['bank_read_count']],bank_descriptor_search=[],
        new_ranges=U4_RANGES,existing_ranges=EXISTING_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=RANGE_TABLE,contract_block_starts=len(leaders118),contract_bundled_branches=len(CONTRACT_BUNDLED),
            observer_block_starts_u4=len(leaders118),observer_leaders_with_entry_and_black_boxes=len(LEADERS),u2_contract_sha256=sha(sc.CONTRACT.read_bytes())),
        contract_model_checks=model_checks,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=EVIDENCE,
        first_boundary_census=dict(scene_frame_1a7a8_states=census_report['scene'],stage_entry_states=census_report['stage_entry'],counts=dict(scene=len(scene_cen),stage_entry=len(seb_cen),kinds=dict(collections.Counter(c['kind'] for c in seb_cen.values())))),
        census_model_checks=dict(runs=census_report['model_runs'],equal=census_report['model_equal'],unequal=census_report['model_unequal'],model_errors=census_report['model_errors']),
        seed_provenance=dict(files=sc.SEED_FILES,scene_frame=dict(observation_sha256=sc.SCENE_OBS_SHA,initializer_observation_sha256=sc.SCENE_SEED_SHA,cases=len(scene_in),
                captured_1a7a8_states=[dict(case=i,ram_sha256=sha(s['ram']),a7=hex(s['a7']),bank=hex(s['bank']),pvc_raw_words=[hex(x) for x in s['pvc_raw']]) for i,s in enumerate(scene_states)]),
            stage_entry=dict(observation_sha256=sc.STAGE_ENTRY_SHA,cases=len(entry_in),captured_1a73c=[dict(case=c['case_index'],family=c['family'],input_ram_sha256=c['input_ram_sha256'],ram_at_1a73c_sha256=c['ram_sha256'],instructions=c['instructions'],bank=c['bank']) for c in entry_in],
                captured_states=[dict(case=s['case'],pc=hex(s['pc']),hit=s['hit'],ram_sha256=sha(s['ram']),a7=hex(s['a7']),return_long=hex(s['ret']),bank=s['bank'],instruction=s['instruction']) for _,sts,_ in seb_states for s in sts]),
            note='Declared initial fixtures: rebuilt scene_frame inputs (sha-checked), the 1a73c entry state of the original 47a94 body run, the first 1a7a8 state of every original full-frame run, the 1a7a8 / 1a69e states of the original 47a94 body + 480bc tail run, native states of this unit at 1a8ce / 1afda taken from a declared base, and declared host RAM writes (applied before the first instruction of the condition).  A5=108000, return LONG ff000 at 1feffc (natural 1a73c runs).'),
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=summaries,group_counts=group_counts,covered_PCs=sorted(coverage),uncovered_u2_block_starts=missing_native,uncovered_u4_block_starts=hexset(leaders118-coverage),uncovered_leaders_incl_entry_and_black_boxes=missing_native,
        block_start_coverage=block_coverage,block_starts=BLOCKS,boundary_stop_pcs=(RET_FRAME,RET_INIT),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures (rebuilt original seeds, captured native states of the original runs and of this unit, declared RAM/register variants), not natural scheduler/gameplay reachability; direct entries at 1a7a8 / 1a8ce / 1afda / 19e64 / 1724c / 1b0e0 / 1a90e / 1a69e are declared fixtures (entry PC, A7, stack bytes, registers, bank page), declared RAM writes are applied before the first instruction of the condition only, never after execution begins.',
            'The existing executors 43e38, 16ff8, 1861a, 18702 and caf0 are black boxes of this unit: they are executed natively (their code ranges are the earlier observers closures) but their interior is not modelled here; the model compares their entry registers as a leader and replays their native exit registers, RAM writes and bank changes (A7 discipline asserted).',
            'Stops are accepted only directly after the RTS at 1a90e popped the declared return LONG (1a78c / 1a6a2) or, for the U2 step of the natural conditions, directly after the BSR.W at 1a788; the code behind them is never executed except in the explicit bad-stop guard conditions.',
            'Native carry / X are unobserved (SR never read); the X consumers (SUBX at 17258 17278 1b058 1b074) are evidenced through D5, the SUBX result and the branch decision; the Unknown-carry API error and the internal / bundled PC entry rejection are API-level checks, not observed here.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; the PVC page holds only the two bank registers; ordered port writes are instruction accesses, not physical bus cycles.',
            'The work RAM is mirrored (1feffc is offset effc of the 64KiB image) unlike the flat map of the original observers; stack LONGs are declared inside the image.',
            'Path opcode targets that are not block starts are observed only as native guards (computed PC, no table check); mid-block block-internal targets are not modelled.',
            'The debug tile cache BYTE pattern fixtures and the declared path streams are synthetic; the game meaning of the RAM fields, 10f000 bits 3/4 and 10d44e, and U5 (1a470 / 1a0b6) remain unknown.'])
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_checks=len(model_checks),
        model_equal=sum(1 for m in model_checks if m['equal']),uncovered=missing_native,sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
