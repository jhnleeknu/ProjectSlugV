"""Unpatched 480bc frame helper bundle U6 (input 49b0c and the input callbacks) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the scene update observer U4
(observe_animation_machine_scene_update and through it U3 / U2 / U1 and the card menu close / fade-card chain: persistent-CPU Observer with the declared host-change
vocabulary RAM write / PC redirect / A7 delta at a step boundary, fresh-twice reproduction, split (stop at the first hit of every block leader) versus continuous
equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every imported tool module, ROM SHA/mtime guard) and, read-only, the declared-entry
fixture generator of the stage input loop corpus (observe_stage_input_loop.build_cases / fixture, observe_stage_input_loop.CALLBACKS).

Observed unit: the contract bytes of docs/analysis/animation-machine-input-u6-contract.md (main decisions: U6a + U6b + U6c in one unit, 151 block starts; JSR (A1) follows the
computed PC and a nonzero top BYTE is a checked error in the C++ - natively observed here as the difference to the 24-bit bus; TRAP #15 at 4d7f0 is a boundary without an
executor; 49dd4 / 49e8a are folded into the preceding block; 49f4a is duplicated into its two predecessors and not an entry; ROM data through the physical program ROM).
The unit runs from 49b0c (JSR at 480c6, return LONG 480cc) to the RTS at 49bc8 or, for the declared callback / helper entries, from the entry PC to the RTS that pops the
declared return LONG.  The only existing executor is 289e (readiness, 3 block starts), which is small enough to be modelled inline.  A stop is accepted only directly after the
transferring instruction (the RTS popping the declared return LONG, or the not-taken BNE.W at 4d7ec in front of the TRAP #15 at 4d7f0); the code behind it is never executed.

Seeds (all pinned by SHA256, rebuilt in this process):
  stage_frame  artifacts/stage_frame/verification.json: the 64 stage 0 cases that execute 49b0c are rebuilt by the scene core observer (initializer seeds + recorded host
               writes / carried native outputs, every RAM checked against input_sha256) and re-executed by the ORIGINAL stage-frame observer; the first 49b0c state (RAM, 14
               registers, A5, A7, the live stack bytes, the PVC bank words) is captured as the declared entry (JSR at 480c6, return LONG 480cc) and the original state at
               the first following 480cc is captured for the comparison with the native unit run.
  stage_entry  artifacts/stage_entry_body: the 142 cases are re-executed by the original 47a94 body + 480bc tail observer, 49b0c / 480cc captured the same way.
  stage_input  tools/observe_stage_input_loop.build_cases() / fixture() (read-only): the 49b0c / 4d7a6 / 1da60 declared-entry corpora (3229 conditions) provide the RAM,
               the 14 registers and the slots of the declared fixtures; the return LONG at 1feffc is 480cc (not ff000) and the stop is 480cc.
  fixtures     declared initial RAM/registers/return LONGs (fixture summary) and declared host RAM writes applied before the first instruction of the condition.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step
record; declared initial registers/stack LONGs are part of the fixture summary.  Bus width probe (declared extra instrument): the Musashi M68000 oracle of the repository is
used only to observe what the real 24-bit address bus does with a JSR (A1) target whose top BYTE is nonzero (Unicorn does not wrap).

An independent Python model of the contract (a basic-block machine transcribed instruction by instruction from the original bytes, 32-bit register semantics, explicit word/byte
operations, NOT the C++) is compared with each native normal condition: block-leader sequence with the full register file at every leader, the ordered RAM writes, the
ordered fixed ROM reads, the final registers and the whole 64KiB RAM image.  Any difference is recorded in contract_discrepancies.
"""
import collections
import copy
import ctypes
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
import observe_animation_machine_scene_update as su
import observe_stage_input_loop as sil
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
sc=su.sc;fh=su.fh;fc=su.fc;mt=su.mt;op=su.op;menu=su.menu;activation=su.activation;shared=su.shared;sfe=sc.sfe;seb=sc.seb;vsf=su.vsf
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_input_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-input-u6-contract.md'
CONTRACT_SHA='99ba39b26d652b48189f1ab55251c6a099bad4faa21abb2d5a387522636c98dc'
SCOPE=sc.SCOPE
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=sc.u32
S=fc.S                                                      # 1feffc: initial A7 (the declared return LONG lives here)
A5V=0x108000
M32=0xffffffff
KEYS14=sc.KEYS14
PORT_REGIONS=fc.PORT_REGIONS
ENTRY=0x49b0c
RET_FRAME=0x480cc                                           # JSR 49b0c at 480c6, return LONG 480cc
RET_BYTES=RET_FRAME.to_bytes(4,'big')
TRAP_PC=0x4d7f0
TRAP_PREV=0x4d7ec                                           # BNE.W 4d7f2 (not taken) in front of the TRAP
PRE_ENTRY=0x480c6
RTS_FINAL=0x49bc8
BB_289E=(0x289e,0x28a8,0x28ac)
DISCREPANCIES=[]
INFO=[]

# Code ranges of the contract table (+ the existing executor 289e) and the two data windows (read through the live bus).
EXISTING_RANGES=((0x289e,0x28ae),)
DATA_RANGES=((0x49ab0,0x49ab4),(0x4cf64,0x4df60))
ENTRY_LEADERS=(0x49b0c,0x49b2e,0x49b84,0x49e9c,0x49eba,0x49ef0,0x49f2c)       # entry points and JSR (A1) return addresses that are no branch targets
FOLDED_NZ=(0x49dd4,0x49e8a,0x49f4a)                                          # main decision 4: folded / duplicated, no block start
CALLBACKS19=(0x49d88,0x49de6,0x49e34,0x49e38,0x49e9c,0x49eba,0x49ef0,0x49f2c,0x49f66,0x1bec0,0x1d5ac,0x1d5e2,0x1d61a,0x1d628,0x1d664,0x1d6c2,0x1d8cc,0xe73f2,0x1da60)
U6_RANGES=()
RANGE_TABLE=[]
DEFAULT_MASK=0x49ab0


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)


def in_unit(pc):return in_ranges(pc,U6_RANGES) or in_ranges(pc,EXISTING_RANGES)


# ----------------------------------------------------------------------------------
# Contract tables
# ----------------------------------------------------------------------------------
def parse_contract_table(program):
    """The code rows `| `lo..hi` | unit | size | count | `bytes` |` (plus the data row 49ab0..49ab4): every byte string is compared with the ROM."""
    rows=[];code=[]
    pattern=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)`(\([^)]*\))? \| (\S+) \| (\d+) \| ([^|]*)\| `([0-9a-f]+)` \|')
    for line in CONTRACT.read_text().splitlines():
        m=pattern.match(line)
        if not m:continue
        lo,hi,unit,size,raw=int(m.group(1),16),int(m.group(2),16),m.group(4),int(m.group(5)),m.group(7)
        ok=program[lo:hi].hex()==raw and hi-lo==size
        assert ok,(hex(lo),hex(hi))
        rows.append(dict(range='%x..%x'%(lo,hi),unit=unit,size=size,bytes_equal_to_rom=ok))
        if unit!='자료':code.append((lo,hi))
    assert len(rows)==20 and len(code)==19,(len(rows),len(code))
    return rows,tuple(code)


def contract_lists():
    """Block starts (U6a 34 / U6b 70 / U6c 47 = 151), folded / bundled PCs (9 / 25 / 20 = 54) and the carry consumer list of the contract text."""
    lines=CONTRACT.read_text().splitlines()
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',text)]
    starts={};folded={};section=None
    for line in lines:
        if line.startswith('- **'):section=line
        m=re.match(r'^  - (U6[abc]) (\d+)(\(.*?\))?:(.*)$',line)
        if m and section:
            target=starts if 'Block 시작 PC' in section else folded if '묶인 분기' in section else None
            if target is not None:target[m.group(1)]=pcs(m.group(4))
    assert [len(starts[k]) for k in ('U6a','U6b','U6c')]==[34,70,47] and [len(folded[k]) for k in ('U6a','U6b','U6c')]==[9,25,20]
    allstarts=sum(starts.values(),[]);allfolded=sum(folded.values(),[])
    assert len(set(allstarts))==151 and len(set(allfolded))==54 and not set(allstarts)&set(allfolded)
    return starts,folded


# ----------------------------------------------------------------------------------
# Independent model: a basic-block machine (transcription of the original instructions between two block leaders; a block ends with exactly one control transfer)
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
BLK={}
LEADERS=frozenset()
sub16,add16,sub32,add32=sc.sub16,sc.add16,sc.sub32,sc.add32
sx16,sx32=sc.sx16,sc.sx32


def blk(*pcs):
    def deco(fn):
        for pc in pcs:
            assert pc not in BLK,hex(pc);BLK[pc]=fn
        return fn
    return deco


def swap(v):return ((v<<16)|(v>>16))&M32


class U6Machine(fh.Machine):
    def __init__(self,program,bank,ram,regs,env):
        super().__init__(program,bank,ram,regs,env)
        self.C=None
    def lead(self,pc):
        assert pc in LEADERS,hex(pc)
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)
    def call(self,target,ret):self.push32(ret);return target
    def rts(self):return self.pop32()
    def rw(self,off):return self.rd(self.a5(off),2)
    def rl(self,off):return self.rd(self.a5(off),4)
    def rb(self,off):return self.rd(self.a5(off),1)
    def ww(self,off,v):self.wr(self.a5(off),2,v)
    def wb(self,off,v):self.wr(self.a5(off),1,v)
    def bset_reg(self,reg,bit):self.r[reg]=(self.r[reg]|(1<<(bit&31)))&M32                      # BSET Dn,Dm / #n,Dm: bit number mod 32
    def bclr_reg(self,reg,bit):self.r[reg]=self.r[reg]&~(1<<(bit&31))&M32
    def bset_mem(self,addr,bit):
        old=self.rd(addr,1);self.wr(addr,1,old|(1<<(bit&7)))                                     # memory operand: bit number mod 8, byte written back
    def btst_mem(self,addr,bit):return (self.rd(addr,1)>>(bit&7))&1


# ---- 289e (existing executor, modelled inline): CMPI.L #270e,(A0); BEQ.W 28ac; ORI #1,CCR; RTS
@blk(0x289e)
def b289e(M):
    if M.rd(M.r['a0'],4)==0x270e:M.C=0;return 0x28ac
    return 0x28a8
@blk(0x28a8)
def b28a8(M):M.C=1;return 0x28ac
@blk(0x28ac)
def b28ac(M):return M.rts()


# ---- U6a: single block callbacks, mask / edge helpers and the 49b0c loop
@blk(0x1d8cc)
def b1d8cc(M):return M.rts()
@blk(0x49e34)
def b49e34(M):M.r['d7']=0;return M.rts()
@blk(0xe73f2)
def be73f2(M):M.lw('d7',M.rw(0x5e24));return M.rts()


@blk(0x49ab4)
def b49ab4(M):
    M.r['d7']=0;M.lb('d7',M.r['d0']);M.lb('d7',M.r['d7']&0x0f);M.lb('d6',M.r['d7']);M.r['d2']=4;return 0x49ac0
@blk(0x49ac0)
def b49ac0(M):
    a4=M.r['a4'];M.lb('d5',M.rd(a4,1));M.r['a4']=(a4+1)&M32
    M.lb('d4',M.r['d0']);M.lb('d4',M.r['d4']&M.r['d5'])
    return 0x49ad6 if (M.r['d4']&0xff)!=(M.r['d5']&0xff) else 0x49acc
@blk(0x49acc)
def b49acc(M):
    M.bset_reg('d7',M.r['d2']);M.lb('d4',M.r['d4']&M.r['d1'])
    return 0x49ad6 if (M.r['d4']&0xff)==0 else 0x49ad4
@blk(0x49ad4)
def b49ad4(M):M.bset_reg('d6',M.r['d2']);return 0x49ad6
@blk(0x49ad6)
def b49ad6(M):
    M.lb('d2',(M.r['d2']&0xff)+1)                                                                # ADDQ.B #1,D2 (low byte only)
    return 0x49ac0 if (M.r['d2']&0xff)<8 else 0x49ade                                            # CMPI.B #8,D2 ; BCS
@blk(0x49ade)
def b49ade(M):
    M.r['a4']=(M.r['a4']-4)&M32                                                                  # SUBQ.W #4,A4 (whole register)
    M.lb('d2',M.rd(M.r['a4']+2,1));M.lb('d2',(M.r['d2']&0xff)&M.rd(M.r['a4']+1,1))
    return 0x49afc if (M.r['d2']&0xff)==0 else 0x49aec
@blk(0x49aec)
def b49aec(M):return 0x49afc if (M.r['d6']>>6)&1==0 else 0x49af4
@blk(0x49af4)
def b49af4(M):M.bclr_reg('d7',5);M.bclr_reg('d6',5);return 0x49afc
@blk(0x49afc)
def b49afc(M):return M.rts()
@blk(0x49afe)
def b49afe(M):
    M.lw('d6',M.rd(M.r['a1']+2,2));M.lw('d6',M.r['d6']&0xfff0);M.lw('d6',M.r['d6']^M.r['d7']);M.lw('d6',M.r['d6']&M.r['d7']);return M.rts()


@blk(0x49b0c)
def b49b0c(M):
    M.r['d7']=0;M.r['d6']=0;M.r['a1']=M.rl(0x5734);return 0x49b3a if M.r['a1']==0 else 0x49b1c
@blk(0x49b1c)
def b49b1c(M):M.r['a0']=0x100cb8;return M.call(0x289e,0x49b28)
@blk(0x49b28)
def b49b28(M):
    if M.C is None:raise ModelError('49b28 consumes an unknown carry')
    return 0x49b36 if M.C==0 else 0x49b2c
@blk(0x49b2c)
def b49b2c(M):return M.call(M.r['a1'],0x49b2e)                                                  # JSR (A1): computed PC
@blk(0x49b2e)
def b49b2e(M):M.r['a1']=M.a5(0x5726);return M.call(0x49afe,0x49b36)
@blk(0x49b36)
def b49b36(M):return 0x49b5a
@blk(0x49b3a)
def b49b3a(M):
    M.lb('d0',M.rb(-0x3356));M.lb('d1',M.rb(-0x3355));M.r['a4']=0x10f01c
    return 0x49b56 if M.rb(-0x7fee)==2 else 0x49b52
@blk(0x49b52)
def b49b52(M):M.r['a4']=DEFAULT_MASK;return 0x49b56
@blk(0x49b56)
def b49b56(M):return M.call(0x49ab4,0x49b5a)
@blk(0x49b5a)
def b49b5a(M):M.r['a1']=M.a5(0x5726);return M.call(0x49bb4,0x49b62)
@blk(0x49b62)
def b49b62(M):
    M.r['d7']=0;M.r['d6']=0;M.r['a1']=M.rl(0x5738);return 0x49b90 if M.r['a1']==0 else 0x49b72
@blk(0x49b72)
def b49b72(M):M.r['a0']=0x100da8;return M.call(0x289e,0x49b7e)
@blk(0x49b7e)
def b49b7e(M):
    if M.C is None:raise ModelError('49b7e consumes an unknown carry')
    return 0x49b8c if M.C==0 else 0x49b82
@blk(0x49b82)
def b49b82(M):return M.call(M.r['a1'],0x49b84)
@blk(0x49b84)
def b49b84(M):M.r['a1']=M.a5(0x572c);return M.call(0x49afe,0x49b8c)
@blk(0x49b8c)
def b49b8c(M):return 0x49bb0
@blk(0x49b90)
def b49b90(M):
    M.lb('d0',M.rb(-0x3350));M.lb('d1',M.rb(-0x334f));M.r['a4']=0x10f020
    return 0x49bac if M.rb(-0x7fee)==2 else 0x49ba8
@blk(0x49ba8)
def b49ba8(M):M.r['a4']=DEFAULT_MASK;return 0x49bac
@blk(0x49bac)
def b49bac(M):return M.call(0x49ab4,0x49bb0)
@blk(0x49bb0)
def b49bb0(M):M.r['a1']=M.a5(0x572c);return 0x49bb4
@blk(0x49bb4)
def b49bb4(M):
    M.lw('d0',M.rd(M.r['a1']+4,2));M.wr(M.r['a1']+4,2,0xffff)
    M.lw('d7',M.r['d7']&M.r['d0']);M.lw('d6',M.r['d6']&M.r['d0'])
    M.wr(M.r['a1']+2,2,M.r['d7']&0xffff);M.wr(M.r['a1'],2,M.r['d6']&0xffff);return M.rts()


# ---- U6b: slot helpers 49c20 / 49c32 / 49c66, 49de6, 49f66, the callbacks and the helpers 4836e / 4d7a6
@blk(0x49c20)
def b49c20(M):
    M.lw('d0',M.r['d0']&1);M.lw('d0',(M.r['d0']&0xffff)<<2)                                       # ANDI.W #1,D0 ; LSL.W #2,D0 (low word only)
    M.r['a1']=M.a5(0x5734);M.r['a1']=(M.r['a1']+sx16(M.r['d0']))&M32
    M.wr(M.r['a1'],4,M.r['a0']);return M.rts()
@blk(0x49c32)
def b49c32(M):M.r['a0']=0;return 0x49c20                                                         # MOVEA.W #0,A0 (sign extended); BRA.B
@blk(0x49c66)
def b49c66(M):M.r['a0']=0x49e34;return 0x49c20


@blk(0x49de6)
def b49de6(M):
    M.r['d7']=0;M.lw('d0',M.rd(M.r['a0']+0x78,2))
    return 0x49dfa if M.r['d0']&0xffff else 0x49df0
@blk(0x49df0)
def b49df0(M):M.lw('d1',M.rd(0x10d73c,2));return 0x49e00
@blk(0x49dfa)
def b49dfa(M):M.lw('d1',M.rd(0x10d73e,2));return 0x49e00
@blk(0x49e00)
def b49e00(M):
    a0=M.r['a0']
    M.r['d2']=sub32(M.rd(a0+0x42,4),M.rl(0x53a2))[0];M.r['d3']=sub32(M.rd(a0+0x4a,4),M.rl(0x53aa))[0]
    M.r['d2']=swap(M.r['d2']);M.r['d3']=swap(M.r['d3'])
    r,n,z,v,c=sub16(M.r['d2'],M.r['d1']);M.lw('d2',r)
    return 0x49c66 if z else 0x49e1a
@blk(0x49e1a)
def b49e1a(M):
    M.lw('d3',sub16(M.r['d3'],M.r['d1'])[0]);M.lw('d3',M.r['d3']^M.r['d2'])
    return 0x49c66 if (M.r['d3']>>15)&1 else 0x49e22
@blk(0x49e22)
def b49e22(M):return 0x49e2e if (M.r['d2']>>15)&1 else 0x49e28
@blk(0x49e28)
def b49e28(M):M.bset_reg('d7',2);return M.rts()
@blk(0x49e2e)
def b49e2e(M):M.bset_reg('d7',3);return M.rts()


@blk(0x49f66)
def b49f66(M):
    M.r['d0']=0
    return 0x49f76 if M.r['a0']!=0x100cb8 else 0x49f72
@blk(0x49f72)
def b49f72(M):M.lb('d0',M.rb(-0x3356));return 0x49f76
@blk(0x49f76)
def b49f76(M):return 0x49f84 if M.r['a0']!=0x100da8 else 0x49f80
@blk(0x49f80)
def b49f80(M):M.lb('d0',M.rb(-0x3350));return 0x49f84
@blk(0x49f84)
def b49f84(M):M.r['a4']=DEFAULT_MASK;return 0x49ab4


@blk(0x1bec0)
def b1bec0(M):return 0x1bed8 if (M.rd(M.r['a0']+0x15,1)>>7)&1==0 else 0x1beca
@blk(0x1beca)
def b1beca(M):return 0x1bed8 if (M.rd(M.r['a0']+0xa7,1)>>7)&1 else 0x1bed4
@blk(0x1bed4)
def b1bed4(M):M.r['d7']=0;return M.rts()
@blk(0x1bed8)
def b1bed8(M):return M.call(0x49f66,0x1bede)
@blk(0x1bede)
def b1bede(M):M.lw('d7',M.r['d7']&0xf);return M.rts()

@blk(0x1d5ac)
def b1d5ac(M):return M.call(0x4836e,0x1d5b2)
@blk(0x1d5b2)
def b1d5b2(M):
    if M.C is None:raise ModelError('1d5b2 consumes an unknown carry')
    return 0x1d5c0 if M.C==1 else 0x1d5b6
@blk(0x1d5b6)
def b1d5b6(M):M.lw('d0',M.rd(M.r['a0']+0x78,2));return M.call(0x49c32,0x1d5c0)
@blk(0x1d5c0)
def b1d5c0(M):M.r['d7']=0;return M.rts()

@blk(0x1d5e2)
def b1d5e2(M):return 0x1d5ec if (M.rd(M.r['a0']+0x15,1)>>7)&1==0 else 0x1d628
@blk(0x1d5ec)
def b1d5ec(M):M.r['d7']=0;return 0x1d5fa if (M.rd(M.r['a6']+0x3a,2)>>15)&1 else 0x1d5f6
@blk(0x1d5f6)
def b1d5f6(M):M.lw('d7',8);return 0x1d5fa
@blk(0x1d5fa)
def b1d5fa(M):return M.rts()

@blk(0x1d61a)
def b1d61a(M):return 0x1d624 if (M.rd(M.r['a0']+0x15,1)>>7)&1==0 else 0x1d628
@blk(0x1d624)
def b1d624(M):M.r['d7']=0;return M.rts()
@blk(0x1d628)
def b1d628(M):M.lw('d0',M.rd(M.r['a0']+0x78,2));return M.call(0x49c32,0x1d632)
@blk(0x1d632)
def b1d632(M):return M.call(0x49f66,0x1d638)
@blk(0x1d638)
def b1d638(M):return M.rts()


def axis_block(M,cam,cur_off,zero_target):
    """1d664 / 1d6c2 / 1da60 first block: D7 = 0; D1.W = cur - camera - base; BEQ zero_target (the value is the next PC when D1.W = 0, else None)."""
    M.r['d7']=0;a0=M.r['a0']
    M.lw('d1',M.rd(a0+cur_off,2));M.lw('d1',sub16(M.r['d1'],M.rw(cam))[0]);M.lw('d1',sub16(M.r['d1'],M.rd(a0+0xae,2))[0])
    return zero_target if M.r['d1']&0xffff==0 else None

def axis_sign(M,flag_neg,flag_pos):
    M.lw('d7',M.r['d7']|(flag_neg if (M.r['d1']>>15)&1 else flag_pos))                         # TST.W D1 ; BPL ; ORI.W
def axis_cross(M,cam,prev_off,target,fallthrough):
    a0=M.r['a0']
    M.lw('d2',M.rd(a0+prev_off,2));M.lw('d2',sub16(M.r['d2'],M.rw(cam))[0]);M.lw('d2',sub16(M.r['d2'],M.rd(a0+0xae,2))[0])
    M.lw('d1',M.r['d1']^M.r['d2'])                                                               # EOR.W D2,D1 ; BMI
    return target if (M.r['d1']>>15)&1 else fallthrough

@blk(0x1d664)
def b1d664(M):
    t=axis_block(M,0x53a2,0x42,0x1d628);return t if t is not None else 0x1d674
@blk(0x1d674)
def b1d674(M):return 0x1d682 if (M.r['d1']>>15)&1==0 else 0x1d67a
@blk(0x1d67a)
def b1d67a(M):axis_sign(M,8,0);return 0x1d686
@blk(0x1d682)
def b1d682(M):axis_sign(M,0,4);return 0x1d686
@blk(0x1d686)
def b1d686(M):return axis_cross(M,0x53a2,0x4a,0x1d628,0x1d696)
@blk(0x1d696)
def b1d696(M):return M.rts()

@blk(0x1d6c2)
def b1d6c2(M):
    t=axis_block(M,0x53a6,0x46,0x1d628);return t if t is not None else 0x1d6d4
@blk(0x1d6d4)
def b1d6d4(M):return 0x1d6e2 if (M.r['d1']>>15)&1==0 else 0x1d6da
@blk(0x1d6da)
def b1d6da(M):axis_sign(M,1,0);return 0x1d6e6
@blk(0x1d6e2)
def b1d6e2(M):axis_sign(M,0,2);return 0x1d6e6
@blk(0x1d6e6)
def b1d6e6(M):return axis_cross(M,0x53a6,0x4e,0x1d628,0x1d6f8)
@blk(0x1d6f8)
def b1d6f8(M):return M.rts()

@blk(0x1da60)
def b1da60(M):
    t=axis_block(M,0x53a2,0x42,0x1da98);return t if t is not None else 0x1da72
@blk(0x1da72)
def b1da72(M):return 0x1da80 if (M.r['d1']>>15)&1==0 else 0x1da78
@blk(0x1da78)
def b1da78(M):axis_sign(M,8,0);return 0x1da84
@blk(0x1da80)
def b1da80(M):axis_sign(M,0,4);return 0x1da84
@blk(0x1da84)
def b1da84(M):return axis_cross(M,0x53a2,0x4a,0x1da98,0x1da96)
@blk(0x1da96)
def b1da96(M):return M.rts()
@blk(0x1da98)
def b1da98(M):M.lw('d0',M.rd(M.r['a0']+0x78,2));return M.call(0x4d7a6,0x1daa2)
@blk(0x1daa2)
def b1daa2(M):return 0x1dab8 if M.r['d0']&0xff==0 else 0x1daa8
@blk(0x1daa8)
def b1daa8(M):M.lw('d0',M.rd(M.r['a0']+0x78,2));return M.call(0x49c32,0x1dab2)
@blk(0x1dab2)
def b1dab2(M):return M.call(0x49f66,0x1dab8)
@blk(0x1dab8)
def b1dab8(M):return M.rts()


@blk(0x4836e)
def b4836e(M):return 0x4837e if (M.rb(0x5683)>>2)&1==0 else 0x48378
@blk(0x48378)
def b48378(M):M.C=0;return M.rts()                                                              # ANDI #fe,CCR: known Clear
@blk(0x4837e)
def b4837e(M):M.C=1;return M.rts()                                                              # ORI #1,CCR: known Set


@blk(0x4d7a6)
def b4d7a6(M):return 0x4d7b8 if M.r['d0']&0xff else 0x4d7ac
@blk(0x4d7ac)
def b4d7ac(M):M.r['a4']=M.a5(0x5cba);M.r['a0']=M.a5(-0x7348);return 0x4d7c0
@blk(0x4d7b8)
def b4d7b8(M):M.r['a4']=M.a5(0x5ce6);M.r['a0']=M.a5(-0x7258);return 0x4d7c0
@blk(0x4d7c0)
def b4d7c0(M):return M.call(0x289e,0x4d7c6)
@blk(0x4d7c6)
def b4d7c6(M):
    if M.C is None:raise ModelError('4d7c6 consumes an unknown carry')
    return 0x4d7d0 if M.C==0 else 0x4d7ca
@blk(0x4d7ca)
def b4d7ca(M):return 0x4d7e2 if M.rd(M.r['a4'],2)!=0 else 0x4d7d0
@blk(0x4d7d0)
def b4d7d0(M):
    M.lw('d0',0);M.r['d1']=0;M.r['d2']=0;M.r['d3']=0;M.r['d4']=0;M.r['d5']=M32;M.r['d6']=0;return M.rts()
@blk(0x4d7e2)
def b4d7e2(M):
    M.r['d0']=0;M.lb('d0',M.rd(M.r['a4']+0x27,1))
    return 0x4d7f2 if M.r['d0']&0xffff!=0 else TRAP_PC
@blk(0x4d7f2)
def b4d7f2(M):
    a4=M.r['a4']
    M.lb('d1',M.rd(a4+0x25,1));M.lb('d2',M.rd(a4+0x26,1));M.lw('d3',M.rd(a4+0x1c,2));M.lw('d5',M.rd(a4+0x20,2));M.lb('d6',M.rd(a4+0x2a,1))
    M.lw('d4',M.r['d0']);M.lw('d4',M.r['d4']&0xff);M.r['d4']=((M.r['d4']&0xffff)*0x10)&M32                  # MULU.W #$10,D4 (unsigned 16 x 16 -> LONG)
    M.r['a4']=(0x4cf64+sx16(M.r['d4']))&M32;M.lw('d4',M.rd(M.r['a4']+0xa,2));return M.rts()


# ---- U6c (no installation path found by the contract): 49d88, 49e38, 49e9c, 49eba, 49ef0, 49f2c
@blk(0x49d88)
def b49d88(M):
    a0=M.r['a0'];M.r['d2']=M.rd(a0+0x42,4);M.r['d3']=M.rd(a0+0x4a,4)
    M.r['d2']=sub32(M.r['d2'],M.rl(0x53a2))[0];M.r['d3']=sub32(M.r['d3'],M.rl(0x53aa))[0];M.r['d2']=swap(M.r['d2']);M.r['d3']=swap(M.r['d3'])
    M.lw('d0',M.rd(a0+0x78,2));return 0x49dae if M.r['d0']&0xffff else 0x49da4
@blk(0x49da4)
def b49da4(M):M.lw('d1',M.rd(0x10d73c,2));return 0x49db4
@blk(0x49dae)
def b49dae(M):M.lw('d1',M.rd(0x10d73e,2));return 0x49db4
@blk(0x49db4)
def b49db4(M):
    M.lw('d2',sub16(M.r['d2'],M.r['d1'])[0]);M.lw('d3',sub16(M.r['d3'],M.r['d1'])[0]);M.lw('d3',M.r['d3']^M.r['d2'])
    return 0x49dcc if (M.r['d3']>>15)&1==0 else 0x49dbe
@blk(0x49dbe)
def b49dbe(M):M.push16(M.r['d2']&0xffff);M.push32(M.r['a0']);return M.call(0x49c32,0x49dc6)
@blk(0x49dc6)
def b49dc6(M):
    M.r['a0']=M.pop32();M.lw('d2',M.pop16());M.lw('d2',(-(M.r['d2']&0xffff))&0xffff);return 0x49dcc
@blk(0x49dcc)
def b49dcc(M):
    M.r['d7']=0;d2=M.r['d2']&0xffff                                                              # TST.W D2 ; BEQ 49de4 ; BMI 49de0 (the BMI at 49dd4 is folded)
    if d2==0:return 0x49de4
    return 0x49de0 if d2>>15 else 0x49dd8
@blk(0x49dd8)
def b49dd8(M):M.bset_reg('d7',2);return 0x49de4
@blk(0x49de0)
def b49de0(M):M.bset_reg('d7',3);return 0x49de4
@blk(0x49de4)
def b49de4(M):return M.rts()


@blk(0x49e38)
def b49e38(M):
    a0=M.r['a0'];M.r['d7']=0
    M.lw('d2',M.rd(a0+0x42,2));M.lw('d3',M.rd(a0+0x4a,2));M.lw('d2',sub16(M.r['d2'],M.rw(0x53a2))[0]);M.lw('d3',sub16(M.r['d3'],M.rw(0x53aa))[0])
    M.lw('d0',M.rd(a0+0x78,2));return 0x49e5c if M.r['d0']&0xffff else 0x49e52
@blk(0x49e52)
def b49e52(M):M.lw('d1',M.rd(0x10d73c,2));return 0x49e62
@blk(0x49e5c)
def b49e5c(M):M.lw('d1',M.rd(0x10d73e,2));return 0x49e62
@blk(0x49e62)
def b49e62(M):
    r,n,z,v,c=sub16(M.r['d2'],M.r['d1']);M.lw('d2',r)
    return 0x49e70 if z else 0x49e68
@blk(0x49e68)
def b49e68(M):
    M.lw('d3',sub16(M.r['d3'],M.r['d1'])[0]);M.lw('d3',M.r['d3']^M.r['d2'])
    return 0x49e84 if (M.r['d3']>>15)&1==0 else 0x49e70
@blk(0x49e70)
def b49e70(M):return 0x49e84 if (M.rd(M.r['a0']+0x15,1)>>7)&1==0 else 0x49e7a
@blk(0x49e7a)
def b49e7a(M):M.r['d7']=0;M.r['a0']=0x49f2c;return 0x49c20
@blk(0x49e84)
def b49e84(M):
    d2=M.r['d2']&0xffff                                                                          # TST.W D2 ; BEQ 49e9a ; BMI 49e96 (the BMI at 49e8a is folded)
    if d2==0:return 0x49e9a
    return 0x49e96 if d2>>15 else 0x49e8e
@blk(0x49e8e)
def b49e8e(M):M.bset_reg('d7',2);return 0x49e9a
@blk(0x49e96)
def b49e96(M):M.bset_reg('d7',3);return 0x49e9a
@blk(0x49e9a)
def b49e9a(M):return M.rts()

@blk(0x49e9c)
def b49e9c(M):return M.call(0x49de6,0x49ea0)
@blk(0x49ea0)
def b49ea0(M):
    M.push32(M.r['d0']);M.lw('d0',M.r['d7']);M.lw('d0',M.r['d0']&0xc)
    return 0x49eb4 if M.r['d0']&0xffff else 0x49eae
@blk(0x49eae)
def b49eae(M):M.r['d7']=0;M.bset_reg('d7',5);return 0x49eb4
@blk(0x49eb4)
def b49eb4(M):M.r['d0']=M.pop32();return M.rts()

@blk(0x49eba)
def b49eba(M):
    M.lb('d0',0)
    return 0x49eca if M.rd(0x100cb8,4)==M.r['a0'] else 0x49ec6                                   # CMPA.L 100cb8.L,A0: the LONG at 100cb8
@blk(0x49ec6)
def b49ec6(M):M.lb('d0',1);return 0x49eca
@blk(0x49eca)
def b49eca(M):return 0x49eea if M.btst_mem(M.a5(0x5732),M.r['d0']) else 0x49ed2                  # BTST D0,5732(A5): bit number mod 8
@blk(0x49ed2)
def b49ed2(M):M.bset_mem(M.a5(0x5732),M.r['d0']);return M.call(0x49de6,0x49eda)
@blk(0x49eda)
def b49eda(M):M.push32(M.r['d0']);M.lw('d0',M.r['d7']);M.lw('d0',M.r['d0']|0x20);M.r['d0']=M.pop32();return M.rts()    # the OR result is discarded by the restore
@blk(0x49eea)
def b49eea(M):return M.call(0x49de6,0x49eee)
@blk(0x49eee)
def b49eee(M):return M.rts()

@blk(0x49ef0)
def b49ef0(M):
    M.lb('d0',0)
    return 0x49f00 if M.rd(0x100cb8,4)==M.r['a0'] else 0x49efc
@blk(0x49efc)
def b49efc(M):M.lb('d0',1);return 0x49f00
@blk(0x49f00)
def b49f00(M):return 0x49f10 if M.btst_mem(M.a5(0x5732),M.r['d0'])==0 else 0x49f08
@blk(0x49f08)
def b49f08(M):M.lw('d0',M.rd(M.r['a0']+0x78,2));M.r['d7']=0;return M.rts()
@blk(0x49f10)
def b49f10(M):M.push32(M.r['d0']);return M.call(0x49de6,0x49f18)
@blk(0x49f18)
def b49f18(M):
    M.r['d1']=M.pop32();M.lw('d2',M.r['d7']);M.lw('d2',M.r['d2']&0xc)
    return 0x49f2a if M.r['d2']&0xffff else 0x49f26
@blk(0x49f26)
def b49f26(M):M.bset_mem(M.a5(0x5732),M.r['d1']);return 0x49f2a
@blk(0x49f2a)
def b49f2a(M):return M.rts()

def f2c_tail(M,z_flag):
    """49f4a (duplicated into 49f3e and 49f46): SNE.B D2 ; EOR.B D2,D1 ; BEQ 49f64 (the TST.B D2 ; BNE 49f60 behind it is the block 49f52)."""
    M.lb('d2',0 if z_flag else 0xff);M.lb('d1',M.r['d1']^M.r['d2'])
    return 0x49f64 if M.r['d1']&0xff==0 else 0x49f52
@blk(0x49f52)
def b49f52(M):return 0x49f60 if M.r['d2']&0xff else 0x49f58
@blk(0x49f2c)
def b49f2c(M):
    M.r['d7']=0;M.lb('d1',0xff if (M.rd(M.r['a0']+0x15,1))&1 else 0);M.lw('d0',M.rd(M.r['a0']+0x78,2))
    return 0x49f46 if M.r['d0']&0xffff else 0x49f3e
@blk(0x49f3e)
def b49f3e(M):return f2c_tail(M,M.rb(0x5740)==0)
@blk(0x49f46)
def b49f46(M):return f2c_tail(M,M.rb(0x5741)==0)
@blk(0x49f58)
def b49f58(M):M.bset_reg('d7',3);return 0x49f64
@blk(0x49f60)
def b49f60(M):M.bset_reg('d7',2);return 0x49f64
@blk(0x49f64)
def b49f64(M):return M.rts()


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
RANGES=();BLOCKS=();CONTRACT_STARTS={};CONTRACT_FOLDED={};CONTRACT_ALL=set();CONTRACT_FOLD_ALL=set()
POOL=fh.POOL


def configure(program,out_dir):
    global RANGES,BLOCKS,U6_RANGES,RANGE_TABLE,LEADERS,CONTRACT_STARTS,CONTRACT_FOLDED,CONTRACT_ALL,CONTRACT_FOLD_ALL
    RANGE_TABLE,U6_RANGES=parse_contract_table(program)
    assert sum(hi-lo for lo,hi in U6_RANGES)==1288,sum(hi-lo for lo,hi in U6_RANGES)
    CONTRACT_STARTS,CONTRACT_FOLDED=contract_lists()
    CONTRACT_ALL=set(sum(CONTRACT_STARTS.values(),[]));CONTRACT_FOLD_ALL=set(sum(CONTRACT_FOLDED.values(),[]))
    decoded=set(fh.leaders_of(program,U6_RANGES))|set(ENTRY_LEADERS)
    assert set(FOLDED_NZ)<=decoded and decoded-set(FOLDED_NZ)==CONTRACT_ALL,(sorted(hex(x) for x in decoded^(CONTRACT_ALL|set(FOLDED_NZ))))
    LEADERS=frozenset(CONTRACT_ALL|set(BB_289E))
    missing=sorted(hex(pc) for pc in LEADERS if pc not in BLK and pc!=TRAP_PC)
    assert not missing,'model has no block for %s'%missing
    extra=sorted(hex(pc) for pc in BLK if pc not in LEADERS)
    assert not extra,'model has blocks that are not leaders %s'%extra
    RANGES=U6_RANGES+EXISTING_RANGES
    BLOCKS=tuple(sorted(LEADERS))
    fc.OUT=out_dir;fc.RANGES=RANGES;fc.BOUNDARIES=BLOCKS;fc.KEY_PCS=BLOCKS
    fh.OUT=out_dir;POOL.clear()


def stop_evidence(program,p,origin=None):
    """`origin`: the first phase of the same step (split runs: the stop phase starts at a checkpoint, the step entry state is that of the first phase)."""
    origin=origin or p
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(outgoing_pc=pc,previous_pc=None,is_step_stop=True,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];ram=p['ram_after'];a7=o['a7'];inc=origin['incoming']
    if pc==TRAP_PC:
        assert prev==TRAP_PREV and program[prev:prev+4].hex()=='66000004' and program[pc:pc+2].hex()=='4e4f' and o['d0']&0xffff==0,(p['label'],hex(prev))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+4].hex(),is_step_stop=True,a7_delta_from_entry=sx32(a7-inc['a7']),
            reached_from='BNE.W at 4d7ec (bytes 66000004) not taken after CMPI.W #0,D0 with D0.W = 0 (BYTE 27(A4) = 0); the TRAP #15 at 4d7f0 (bytes 4e4f) is never executed')
    assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    assert u32(ram,a7-4)==pc and a7==(inc['a7']+4)&M32,(p['label'],hex(pc),hex(a7),hex(inc['a7']))
    return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),is_step_stop=True,
        reached_from='RTS at %x popped the declared return LONG %x that was on the stack top at the entry (entry A7 = %x, A7 after = %x); %x is never executed'%(prev,pc,inc['a7'],a7,pc))


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
# Model comparison
# ----------------------------------------------------------------------------------
def run_model(program,p,stop):
    M=U6Machine(program,p['bank_before'],p['ram_before'],p['incoming'],{})
    final=run_blocks(M,p['incoming']['pc'],stop)
    M.r['pc']=final
    return M


def check_model(program,label,p,stop,facts=None):
    row=dict(label=label,kind='input-model')
    try:M=run_model(program,p,stop)
    except (ModelError,fh.ModelError,fh.StopAt,KeyError,AssertionError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=label,kind='model-could-not-follow-native',detail=repr(e)));return row
    o=p['outgoing'];nb=p['boundaries'];bad=[]
    if M.r['pc']!=stop:bad.append(dict(what='model final PC',model=hex(M.r['pc']),native=hex(o['pc'])))
    if len(M.leads)!=len(nb):bad.append(dict(what='leader count',model=len(M.leads),native=len(nb)))
    for i,(m,n) in enumerate(zip(M.leads,nb)):
        got=dict(n['registers'])
        if m!=got:
            bad.append(dict(what='leader %d'%i,model_pc=hex(m['pc']),native_pc=hex(got['pc']),differing_registers={k:(hex(m[k]),hex(got[k])) for k in m if m[k]!=got.get(k)}));break
    ram_writes=[(e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region']=='ram' and e['access']=='write']
    if M.writes!=ram_writes:
        first=next((i for i,(a,b) in enumerate(zip(M.writes,ram_writes)) if a!=b),min(len(M.writes),len(ram_writes)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(ram_writes),first_difference=first,model=M.writes[first:first+3],native=ram_writes[first:first+3]))
    ports=[e for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write']
    if ports:bad.append(dict(what='unexpected port write',count=len(ports)))
    reads=[(e['address'],e['size'],e['region']) for e in p['events'] if e['region'] in ('fixed','bank') and e['access']=='read']
    if M.rom_reads!=reads:bad.append(dict(what='ordered fixed/bank reads',model=M.rom_reads[:6],native=reads[:6],model_count=len(M.rom_reads),native_count=len(reads)))
    final=dict(M.r)
    if final!={k:o[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(o[k])) for k in final if final[k]!=o[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if M.bank!=p['modeled_bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(p['modeled_bank'])))
    entry_a7=p['incoming']['a7']
    row.update(equal=not bad,leaders=len(M.leads),leader_pcs_distinct=len({m['pc'] for m in M.leads}),ordered_ram_writes=len(M.writes),ordered_rom_reads=len(M.rom_reads),ram_bytes_compared=0x10000,
        final_registers_compared=sorted(final),model_leader_pcs=sorted({hex(m['pc']) for m in M.leads}),final_bank=hex(M.bank),max_stack_depth=max([sx32(entry_a7-m['a7']) for m in M.leads] or [0]),
        rom_read_addresses=sorted({hex(a) for a,n,r in M.rom_reads}),mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=label,kind='model-vs-native',mismatches=bad[:4]))
    return row


# ----------------------------------------------------------------------------------
# Captures of the ORIGINAL uninterrupted runs: first 49b0c state (declared entry) and first following 480cc state
# ----------------------------------------------------------------------------------
class Capture:
    """Hooks 49b0c and 480cc on an original observer (stage-frame verifier or 47a94 body + 480bc tail observer); `module` is its module (KEYS / REGS / BASE / STACK / m)."""
    def __init__(self,obs,module):
        self.obs=obs;self.mod=module;self.entry=None;self.back=None;self.initial_bank=2
        obs.cpu.hook_add(UC_HOOK_CODE,self.at_entry,begin=ENTRY,end=ENTRY)
        obs.cpu.hook_add(UC_HOOK_CODE,self.at_back,begin=RET_FRAME,end=RET_FRAME)
    def snap(self,cpu,address):
        m=self.mod;a7=cpu.reg_read(m.m.UC_M68K_REG_A7);o=self.obs
        return dict(pc=address,hit=1,ram=bytes(cpu.mem_read(m.BASE,0x10000)),regs={k:cpu.reg_read(r)&M32 for k,r in zip(m.KEYS,m.REGS)},a7=a7,a5=cpu.reg_read(m.m.UC_M68K_REG_A5)&M32,
            stack=bytes(cpu.mem_read(a7,m.STACK+4-a7)),bank=o.bank,pvc_raw=su.last_pvc_words(o.ports,self.initial_bank),instruction=len(o.pcs),prev_pc=o.pcs[-2] if len(o.pcs)>1 else None,
            ret=int.from_bytes(cpu.mem_read(a7,4),'big'),ports=len(o.ports))
    def at_entry(self,cpu,address,size,user):
        if self.entry is None:self.entry=self.snap(cpu,address)
    def at_back(self,cpu,address,size,user):
        if self.entry is not None and self.back is None:
            self.back=self.snap(cpu,address);cpu.emu_stop()
    def reset(self):self.entry=None;self.back=None
    def check(self,label):
        e=self.entry;b=self.back
        assert e is not None and b is not None,(label,'49b0c / 480cc not reached')
        assert e['prev_pc']==PRE_ENTRY and e['ret']==RET_FRAME and e['a7']==self.mod.STACK-4 and e['a5']==A5V,(label,hex(e['prev_pc'] or 0),hex(e['ret']),hex(e['a7']))
        assert int.from_bytes(e['stack'][4:8],'big')==self.mod.RETURN,label
        assert b['a7']==self.mod.STACK and b['a5']==A5V,(label,hex(b['a7']))
        return e,b


class FrameCapture(Capture):
    """stage-frame verifier observer (verify_stage_frame.Observer)."""
    def __init__(self,program):
        super().__init__(vsf.Observer(program),vsf)
    def run(self,ram,incoming,external,label):
        o=self.obs;self.reset();self.initial_bank=incoming['bank'];o.prepare(ram,incoming);cpu=o.cpu
        o.external,o.wait_visits,o.error=external,0,None
        for values in (o.pcs,o.writes,o.ports,o.reads,o.bank_reads,o.boundaries):values.clear()
        cpu.emu_start(cpu.reg_read(vsf.m.UC_M68K_REG_PC),0xffffff,count=2000000)
        assert o.error is None,(label,o.error)
        return self.check(label)


class EntryBodyCapture(Capture):
    """47a94 body + 480bc tail observer (observe_stage_entry_body.Observer)."""
    def __init__(self,program):
        super().__init__(seb.Observer(program),seb);self.program=program
    def run(self,case,label):
        ram,state,meta=seb.prepare_case(ROOT,self.program,case);o=self.obs;self.reset();self.initial_bank=state['bank'];o.prepare(ram,state);cpu=o.cpu
        o.external,o.wait_visits,o.error=0,0,None
        for values in (o.pcs,o.writes,o.ports,o.reads,o.bank_reads,o.boundaries,o.prefix):values.clear()
        cpu.emu_start(cpu.reg_read(seb.m.UC_M68K_REG_PC),0xffffff,count=2000000)
        assert o.error is None,(label,o.error)
        return self.check(label)+(sha(ram),)


def captured_fx(name,st,prov,role):
    """Declared entry fixture from a captured state of an original run: PC 49b0c, A7 and the live stack bytes (return LONG 480cc, then ff000), PVC bank words."""
    assert st['a5']==A5V and st['bank'] in (2,3) and st['pc']==ENTRY
    raw8,raw9=st['pvc_raw'];bank,ff8,ff9=pvc_bank_update(raw8,raw9);assert bank==st['bank']*0x100000,(hex(bank),st['bank'])
    return sc.make_fx(name,st['ram'],st['regs'],((bank,ff8,ff9),sc.pvc_page(raw8,raw9)),ENTRY,st['a7'],prov,(),[(st['a7'],st['stack'])],role=role)


def brief(st):return dict(ram_sha256=sha(st['ram']),a7=hex(st['a7']),a6=hex(st['regs']['a6']),bank=st['bank'],pvc_raw_words=[hex(x) for x in st['pvc_raw']],instruction=st['instruction'],stack_hex=st['stack'].hex(),
    registers={k:hex(v) for k,v in st['regs'].items()})


# ----------------------------------------------------------------------------------
# Condition runners
# ----------------------------------------------------------------------------------
def probe(program,fx,setup,stop,allow_guard=False):
    """One continuous native phase from the declared fixture (declared RAM writes first) to the first execution of `stop` (or a guard when allowed)."""
    o=fc.Observer(program,True)
    try:
        o.prepare(dict(fx,stop_pc=stop,checkpoints=[]))
        o.begin_step(stop,[]);o.apply(list(setup));p=o.run(allow_guard=allow_guard)
    finally:o.close()
    if not allow_guard:assert p['guard'] is None and p['outgoing']['pc']==stop,(fx['label'],p['guard'],hex(p['outgoing']['pc']))
    return p


# ----------------------------------------------------------------------------------
# Declared fixtures
# ----------------------------------------------------------------------------------
OBJ=(0x100cb8,0x100da8)
SOURCE=(0x10dcba,0x10dce6)
RET_OF={49:0}                       # placeholder to keep the table below readable
RETURN_FOR={0x49ab4:0x49b5a,0x49afe:0x49b36,0x49bb4:0x49b62,0x49c20:0x49b2e,0x49c32:0x49b2e,0x49c66:0x49b2e,0x49f66:0x1d638,0x4836e:0x1d5b2,0x4d7a6:0x1daa2,0x1da60:0x49b2e}


def W(address,size,value,why=None):
    return fc.ram_write(address,size,value,why or 'declared host RAM write %x (%d bytes) = %x'%(address,size,value&((1<<(8*size))-1)))


def writes_of(d,why=None):
    """{address: (size, value)} -> declared RAM writes in address order."""
    return [W(a,sz,v,why) for a,(sz,v) in sorted(d.items())]


def decl_fx(name,ram,regs,entry,ret,prov,role,a7=S,bank=None):
    """Declared entry fixture: RAM image, 14 registers (a5 = 108000), A7 and the declared return LONG on the stack top; PVC bank 2 page."""
    return sc.make_fx(name,ram,regs,bank or sc.BANK2,entry,a7,prov,(),[(a7,ret.to_bytes(4,'big'))],role=role)


def sil_fixture(case):
    ram,regs=sil.fixture(case)
    return ram,dict(zip(sil.KEYS,regs))


def sil_loop_fx(name,i,case):
    ram,regs=sil_fixture(case)
    prov=dict(kind='stage_input_loop corpus case (declared entry, read-only generator)',case_index=i,case=case,ram_sha256=sha(bytes(ram)),registers={k:hex(v) for k,v in regs.items()})
    return decl_fx(name,ram,regs,case['entry'],RETURN_FOR.get(case['entry'],RET_FRAME) if case['entry']!=ENTRY else RET_FRAME,prov,
        role='declared %x entry from the stage input loop corpus: RAM and 14 registers of observe_stage_input_loop.fixture(case), A5 = 108000, A7 = 1feffc with the declared return LONG %x on the stack top, PVC bank 2'%(
            case['entry'],RETURN_FOR.get(case['entry'],RET_FRAME) if case['entry']!=ENTRY else RET_FRAME))


def sil_cb_fx(name,i,case,callback):
    """Direct callback entry (the state JSR (A1) of 49b2c / 49b82 hands over): same RAM as the corpus case, A0 = object, A1 = callback, D6 = D7 = 0, return LONG 49b2e (first slot) / 49b84 (second)."""
    ram,regs=sil_fixture(case);player=case['player'];regs=dict(regs);regs['a0']=OBJ[player];regs['a1']=callback;regs['d6']=0;regs['d7']=0
    ret=0x49b2e if player==0 else 0x49b84
    prov=dict(kind='stage_input_loop corpus case as a direct callback entry',case_index=i,case=case,callback=hex(callback),ram_sha256=sha(bytes(ram)),registers={k:hex(v) for k,v in regs.items()})
    return decl_fx(name,ram,regs,callback,ret,prov,
        role='declared callback entry %x (state at the JSR (A1) of %s): RAM of the corpus case, A0 = %x, A1 = %x, D6 = D7 = 0, A5 = 108000, A7 = 1feffc with the return LONG %x on the stack top'%(callback,'49b2c' if player==0 else '49b82',OBJ[player],callback,ret)),ret


# ----------------------------------------------------------------------------------
# Deterministic randomised declared RAM (host writes applied before the first instruction): geometry / flag / mask / input fields
# ----------------------------------------------------------------------------------
HI_POOL=(0,1,2,0x100,0x7ffe,0xfffe,0xffff,0x1234,0x8000)
DX_POOL=(0,0,1,-1,2,-2,0x7fff,-0x7fff,0x8000)
LO_POOL=(0,0x1234,0xffff,1)


def geometry_writes(rng,player,r78=None):
    """Declared object / camera / flag fields so that the sign / zero / crossing branches of 49de6 49d88 49e38 1d664 1d6c2 1da60 and the flag branches of 1bec0 1d5e2 1d61a 49f2c are reachable."""
    w={};obj=OBJ[player]
    cam=[rng.choice(HI_POOL) for _ in range(3)]                      # 10d3a2, 10d3a6, 10d3aa (hi WORDs)
    if rng.random()<0.5:cam[2]=cam[0]
    base=rng.choice((0,0,0,1,2,0xffff,7))
    r78=rng.choice((0,0,1,2,3,0x100,0x101)) if r78 is None else r78
    d1=[rng.choice((0,0,0,1,0xffff,3)),rng.choice((0,0,0,1,0xffff,3))]
    d1sel=d1[0] if r78&0xffff==0 else d1[1]
    w[0x10d73c]=(2,d1[0]);w[0x10d73e]=(2,d1[1])
    for off,camhi,which in ((0x42,cam[0],0),(0x4a,cam[2],0),(0x46,cam[1],1),(0x4e,cam[1],1)):
        dx=rng.choice(DX_POOL);extra=base if rng.random()<0.5 else d1sel
        hi=(camhi+dx+extra)&0xffff;w[obj+off]=(4,(hi<<16)|rng.choice(LO_POOL))
    for off,c in zip((0xd3a2,0xd3a6,0xd3aa),cam):w[0x100000+off]=(4,(c<<16)|rng.choice(LO_POOL))
    w[obj+0xae]=(2,base);w[obj+0x78]=(2,r78)
    w[obj+0x15]=(1,rng.choice((0,1,0x80,0x81)));w[obj+0xa7]=(1,rng.choice((0,0x80)))
    w[0x10d683]=(1,rng.choice((0,4,0xff,0xfb)));w[0x10d732]=(1,rng.choice((0,0,1,2,3,0xff,0x55)))
    w[0x10d740]=(1,rng.choice((0,1,0xff)));w[0x10d741]=(1,rng.choice((0,1,0xff)));w[0x10de24]=(2,rng.choice((0,0xf0f0,0x1234,0x8000)))
    w[0x10613a]=(2,rng.choice((0,0x8000,0x7fff,1)))                  # WORD 3a(A6) of the corpus A6 = 106100
    return w


def io_writes(rng,mask_choices=True):
    w={}
    w[0x104caa]=(1,rng.choice(BYTE_POOL));w[0x104cab]=(1,rng.choice(BYTE_POOL));w[0x104cb0]=(1,rng.choice(BYTE_POOL));w[0x104cb1]=(1,rng.choice(BYTE_POOL))
    w[0x100012]=(1,rng.choice((0,1,2,2,3,0xff)))
    for a in (0x10f01c,0x10f020):
        for k in range(4):w[a+k]=(1,rng.choice(MASK_BYTES))
    for a in (0x10d726,0x10d72c):
        w[a]=(2,rng.choice(WORD_POOL));w[a+2]=(2,rng.choice(WORD_POOL));w[a+4]=(2,rng.choice((0xffff,0,0x00f0,0x0ff0,0x1234,0xf0f0)))
    return w


BYTE_POOL=(0,0xff,0xf0,0x0f,0x55,0xaa,0x10,0x20,0x40,0x80,0x30,0x60,0xc0,0x90,0x01,0xe0)
MASK_BYTES=(0,0xff,0x10,0x20,0x40,0x80,0x30,0x60,0xc0,0x03,0x70,0xf0)
WORD_POOL=(0,0xffff,0x00f0,0x0ff0,0x1234,0xabcd,0x7ff0,0xff0f,0x8000)
MASK_SETS=((0x10,0x20,0x40,0x80),(0,0,0,0),(0xff,0xff,0xff,0xff),(0x30,0x30,0x60,0xc0),(0x10,0x10,0x10,0x10),(1,2,3,4),(0x10,0x60,0x40,0x80),(0x10,0xe0,0x60,0x80),(0x10,0x20,0x30,0x70),(0xf0,0xf0,0xf0,0xf0),(0x80,0x40,0x20,0x10),(0x55,0xaa,0x66,0x99))


# ----------------------------------------------------------------------------------
# Items (conditions): label, group, provenance, declared fixture, declared RAM writes, stop, storage class
# ----------------------------------------------------------------------------------
class Items:
    def __init__(self):self.items=[];self.labels=set()
    def add(self,label,group,prov,fx,setup=(),stop=RET_FRAME,store=False,guard=None,model=True,delta=None,original=None,facts=None):
        assert label not in self.labels,label
        self.labels.add(label);fx=dict(fx);fx['label']=label;fx['group']='input'
        self.items.append(dict(label=label,group=group,prov=prov,fx=fx,setup=list(setup),stop=stop,store=store,guard=guard,model=model,delta=delta,original=original,facts=facts or {}))


def loop_items(I,cases):
    """The 49b0c declared entries of the stage input loop corpus (1142)."""
    for i,c in enumerate(cases):
        if c['entry']!=ENTRY:continue
        fx=sil_loop_fx('loop-%04d'%i,i,c)
        I.add('loop-%04d-%s'%(i,c['family'][:40]),'loop-corpus','stage_input_loop corpus case %d (%s): 49b0c entry, stop 480cc'%(i,c['family']),fx,store='sig')


def callback_direct_items(I,cases):
    """Every callback entered directly (the JSR (A1) state) with the 228 live-loop corpus states (19 callbacks x 2 players x 6 variants)."""
    for i,c in enumerate(cases):
        if c['family']!='each-player-all19-known-callbacks-live-loop':continue
        cb=c['slots'][c['player']];fx,ret=sil_cb_fx('cb-%04d'%i,i,c,cb)
        I.add('cb-%04d-%x-p%d'%(i,cb,c['player']),'callback-direct','stage_input_loop corpus case %d (%s): direct callback entry %x for player %d, stop %x'%(i,c['family'],cb,c['player'],ret),fx,stop=ret,store='sig')


def helper_corpus_items(I,cases):
    """Declared 4d7a6 (1551) and 1da60 (504) entries of the corpus."""
    for i,c in enumerate(cases):
        if c['entry'] not in (0x4d7a6,0x1da60):continue
        fx=sil_loop_fx('helper-%04d'%i,i,c);ret=RETURN_FOR[c['entry']]
        I.add('helper-%04d-%x'%(i,c['entry']),'helper-corpus','stage_input_loop corpus case %d (%s): entry %x, stop %x'%(i,c['family'],c['entry'],ret),fx,stop=ret,store='sig')


def random_callback_items(I,cases,per=30):
    base_by_player={}
    for i,c in enumerate(cases):
        if c['family']=='each-player-all19-known-callbacks-live-loop' and c['slots'][c['player']]==0x49e34 and c not in base_by_player.values():
            base_by_player.setdefault(c['player'],(i,c))
    for cb in CALLBACKS19:
        for player in (0,1):
            i,c=base_by_player[player];rng=random.Random('u6-callback-%x-%d'%(cb,player));fx,ret=sil_cb_fx('rcb',i,c,cb)
            for k in range(per):
                w=geometry_writes(rng,player);label='rcb-%x-p%d-%02d'%(cb,player,k)
                I.add(label,'callback-random','declared random geometry / flag RAM for the direct callback entry %x (player %d, sample %d, rng u6-callback-%x-%d)'%(cb,player,k,cb,player),fx,writes_of(w),stop=ret,store=False)


def random_loop_items(I,cases,count=600):
    rng=random.Random('u6-loop');bases=[(i,c) for i,c in enumerate(cases) if c['family']=='two-null-slots-default-all-held'][:4]
    cbs=CALLBACKS19
    for k in range(count):
        i,c=bases[k%len(bases)];fx=sil_loop_fx('rloop',i,c)
        w=io_writes(rng);geo=geometry_writes(rng,rng.choice((0,1)))
        for p in (0,1):                                                  # both objects get their own geometry
            for a,v in geometry_writes(rng,p).items():geo.setdefault(a,v);geo[a]=v
        w.update(geo)
        marker=[rng.choice((0,0,0x270e,1)),rng.choice((0,0,0x270e,1))]
        w[OBJ[0]]=(4,marker[0]);w[OBJ[1]]=(4,marker[1])
        s0=rng.choice((0,0,0)+CALLBACKS19);s1=rng.choice((0,0,0)+CALLBACKS19);w[0x10d734]=(4,s0);w[0x10d738]=(4,s1)
        I.add('rloop-%04d'%k,'loop-random','declared random inputs / masks / geometry / slots (%x, %x) / markers on the corpus state %d (%s); rng u6-loop'%(s0,s1,i,c['family']),fx,writes_of(w),store=False)


def base_state(cases,family='two-null-slots-default-all-held',index=0):
    sel=[(i,c) for i,c in enumerate(cases) if c['family']==family]
    return sel[index]


def direct_fx(name,i,c,entry,regs_over,prov_extra,role):
    ram,regs=sil_fixture(c);regs=dict(regs);regs.update(regs_over);ret=RETURN_FOR[entry]
    prov=dict(kind='stage_input_loop corpus state as a declared helper entry',case_index=i,case_family=c['family'],entry=hex(entry),ram_sha256=sha(bytes(ram)),declared_registers={k:hex(v) for k,v in regs_over.items()},**prov_extra)
    return decl_fx(name,ram,regs,entry,ret,prov,role='declared %x entry (%s): RAM of corpus state %d, declared registers %s, A5 = 108000, A7 = 1feffc with the return LONG %x on the stack top'%(entry,role,i,
        {k:hex(v) for k,v in regs_over.items()},ret)),ret


def mask_items(I,cases):
    """49ab4 (held / edge from the masks): ROM default mask 49ab0 and user masks 10f01c / 10f020, 12 mask sets x D0 / D1 pairs (upper bits of D0 / D1 are declared garbage)."""
    i,c=base_state(cases);rng=random.Random('u6-mask')
    pairs=[(a,b) for a in (0,0xff,0xf0,0x0f,0x55,0xaa,0x40,0x10) for b in (0,0xff,0xf0,0x0f,0x40,0xaa)]+[(rng.randrange(256),rng.randrange(256)) for _ in range(12)]
    for kind,a4 in (('rom',DEFAULT_MASK),('user0',0x10f01c),('user1',0x10f020)):
        sets=(None,) if kind=='rom' else MASK_SETS
        for s,m in enumerate(sets):
            for k,(d0,d1) in enumerate(pairs):
                over=dict(d0=(0xabcd0000|(rng.randrange(256)<<8)|d0),d1=(0x12340000|(rng.randrange(256)<<8)|d1),a4=a4)
                fx,ret=direct_fx('mask',i,c,0x49ab4,over,dict(mask_kind=kind),'held / edge from D0.B = %02x, D1.B = %02x with the %s mask'%(d0,d1,kind))
                w=writes_of({a4+j:(1,m[j]) for j in range(4)}) if m is not None else []
                I.add('mask-%s-%02d-%02d'%(kind,s,k),'mask-direct','49ab4 direct entry: %s mask %s, D0.B = %02x, D1.B = %02x, stop %x'%(kind,m if m else 'rom 10204080',d0,d1,ret),fx,w,stop=ret,store=False)


def helper_direct_items(I,cases):
    i,c=base_state(cases);rng=random.Random('u6-helpers')
    # 49afe: previous held WORD 2(A1) -> new button edge
    for a1 in (0x10d726,0x10d72c):
        for k in range(24):
            over=dict(a1=a1,d6=rng.choice(WORD_POOL)|0x12340000,d7=rng.choice(WORD_POOL)|0xabcd0000)
            fx,ret=direct_fx('afe',i,c,0x49afe,over,{},'edge helper');w=writes_of({a1+2:(2,rng.choice(WORD_POOL))})
            I.add('edge-49afe-%x-%02d'%(a1,k),'helper-direct','49afe direct entry: A1 = %x, D7 = %04x, previous held %04x'%(a1,over['d7']&0xffff,w[0]['value']),fx,w,stop=ret)
    # 49bb4: one-shot mask / write back
    for a1 in (0x10d726,0x10d72c):
        for k in range(24):
            over=dict(a1=a1,d6=rng.choice(WORD_POOL)|0x12340000,d7=rng.choice(WORD_POOL)|0xabcd0000,d0=rng.choice(WORD_POOL)|0x55550000)
            fx,ret=direct_fx('bb4',i,c,0x49bb4,over,{},'one-shot mask write back');w=writes_of({a1+4:(2,rng.choice((0xffff,0,0x00f0,0x0ff0,0x1234,0xf0f0)))})
            I.add('write-49bb4-%x-%02d'%(a1,k),'helper-direct','49bb4 direct entry: A1 = %x, one-shot mask %04x, D7 = %04x, D6 = %04x'%(a1,w[0]['value'],over['d7']&0xffff,over['d6']&0xffff),fx,w,stop=ret)
    # slot helpers
    for entry in (0x49c20,0x49c32,0x49c66):
        for k,(d0,a0) in enumerate((d,a) for d in (0,1,2,3,0x10000,0x10001,0xffff,0x8001,0xabcd0100,0xabcd0101) for a in (0,0x49e34,OBJ[0],0x106000)):
            over=dict(d0=d0,a0=a0)
            fx,ret=direct_fx('slot',i,c,entry,over,{},'slot helper')
            I.add('slot-%x-%02d'%(entry,k),'helper-direct','%x direct entry: D0 = %x, A0 = %x'%(entry,d0,a0),fx,[],stop=ret)
    # 49f66: input byte by object
    for a0 in (OBJ[0],OBJ[1],0,0x100cb9,0x100da9,0x106000,0x100cb7):
        for k in range(8):
            over=dict(a0=a0,d0=rng.randrange(1<<32),d1=rng.randrange(1<<32),d6=rng.randrange(1<<32))
            fx,ret=direct_fx('f66',i,c,0x49f66,over,{},'input select');w=writes_of({0x104caa:(1,rng.choice(BYTE_POOL)),0x104cab:(1,rng.choice(BYTE_POOL)),0x104cb0:(1,rng.choice(BYTE_POOL)),0x104cb1:(1,rng.choice(BYTE_POOL))})
            I.add('input-49f66-%x-%02d'%(a0,k),'helper-direct','49f66 direct entry: A0 = %x'%a0,fx,w,stop=ret)
    # 4836e: known carry producer
    for value in (0,4,0xff,0xfb,0x44,1,2,0x80):
        fx,ret=direct_fx('c836e',i,c,0x4836e,{},{},'known carry producer');w=writes_of({0x10d683:(1,value)})
        I.add('carry-4836e-%02x'%value,'helper-direct','4836e direct entry: BYTE 10d683 = %02x -> %s'%(value,'C = 0 (48378)' if (value>>2)&1 else 'C = 1 (4837e)'),fx,w,stop=ret)


def trap_items(I,cases,program=None):
    """4d7a6 index 0: the TRAP #15 at 4d7f0 is the boundary (stop 4d7f0), through the direct entry, through 1da60 and through the live 49b0c slot loop."""
    act=[(i,c) for i,c in enumerate(cases) if c['family']=='active-player-all255-index-byte-select']
    for player in (0,1):
        for d0kind in (0,1,2):
            i,c=[(i,c) for i,c in act if c['player']==player and c['indices'][player]==1][d0kind]
            c0=dict(c,indices=[0,0]);fx=sil_loop_fx('trap',i,c0);fx['entry_pc']=0x4d7a6
            I.add('trap-4d7a6-p%d-d0kind%d'%(player,d0kind),'trap-boundary','4d7a6 direct entry (D0 = %x), source index BYTE 27 = 0: stop at the TRAP #15 4d7f0'%c['input_d0'],fx,[],stop=TRAP_PC,store=True)
    cr=[(i,c) for i,c in enumerate(cases) if c['family']=='crossing-zero-sign-cross-nocross-player-retarget']
    n=0
    for i,c in cr:
        if (c['current'],c['previous']) in ((0,0),(1,-1),(-1,1),(0x8000,0x7fff),(0x7fff,0x8000)):
            c0=dict(c,indices=[0,0],markers=[0,0],active=[1,1]);fx=sil_loop_fx('trap1da60',i,c0)
            I.add('trap-1da60-%04d'%i,'trap-boundary','1da60 direct entry through the zero / crossing test into 4d7a6 with source index 0 (retarget %s): stop at the TRAP #15 4d7f0'%c['retarget'],fx,[],stop=TRAP_PC,store=(n<6))
            n+=1
    loops=[(i,c) for i,c in enumerate(cases) if c['family']=='each-player-all19-known-callbacks-live-loop' and c['slots'][c['player']]==0x1da60 and (c['current'],c['previous']) in ((0,0),(1,-1),(-1,1),(0x8000,0x7fff),(0x7fff,0x8000))]
    for i,c in loops:
        c0=dict(c,indices=[0,0]);fx=sil_loop_fx('traploop',i,c0)
        if program is not None:
            q=probe(program,fx,[],TRAP_PC,allow_guard=True)
            if q['guard'] is not None:continue                                   # this variant never reaches the TRAP (no crossing / inactive source)
        I.add('trap-loop-1da60-%04d'%i,'trap-boundary','49b0c live loop with the slot callback 1da60 (player %d, variant): source index 0 reaches the TRAP #15; stop 4d7f0'%c['player'],fx,[],stop=TRAP_PC,store=True)


PROBE_STOP=0x3ffffe


def natural_items(I,stage_in,entry_obs,program):
    """206 natural frames: the original run's first 49b0c state (declared entry) -> native unit run -> stop 480cc; compared with the original state at the first 480cc."""
    cap=FrameCapture(program);frame_states=[]
    for index,row,ram,how in stage_in:
        e,b=cap.run(ram,row['incoming'],row['external'],row['label'])
        prov=dict(kind='stage_frame natural frame (original stage-frame observer, first 49b0c state)',verification_sha256=sc.STAGE_FRAME_SHA,case_index=index,case_label=row['label'],input_sha256=row['input_sha256'],rebuilt_from=how,
            incoming_stage=row['incoming']['stage'],bank=row['incoming']['bank'],entry_state=brief(e),original_480cc_state=dict(ram_sha256=sha(b['ram']),a7=hex(b['a7']),instruction=b['instruction']),instructions_49b0c_to_480cc=b['instruction']-e['instruction'],
            recorded_boundary_a6=[hex(x['a6']) for x in row['boundaries'] if x['pc']==ENTRY][:1])
        assert [x for x in row['boundaries'] if x['pc']==ENTRY][0]['a7']==e['a7'] and [x for x in row['boundaries'] if x['pc']==ENTRY][0]['a6']==e['regs']['a6']
        fx=captured_fx('nat-frame-%04d'%index,e,prov,'declared 49b0c entry captured at the first execution of 49b0c (JSR at 480c6, return LONG 480cc) of the original stage-frame run of case %d (%s): RAM, 14 registers, A5 = 108000, A7 = %x and the live stack bytes; PVC bank words of the original run'%(index,row['label'],e['a7']))
        I.add('natural-stage-frame-%04d'%index,'natural-stage-frame','stage_frame case %d (%s): 49b0c entry of the original run, stop 480cc'%(index,row['label']),fx,stop=RET_FRAME,store=True,original=b,facts=dict(entry_instruction=e['instruction']))
        frame_states.append((index,e,b))
    ecap=EntryBodyCapture(program);entry_states=[]
    for row in entry_obs['results']:
        e,b,insha=ecap.run(row['fixture'],'entry-%d'%row['case_index'])
        prov=dict(kind='stage_entry_body natural frame (original 47a94 body + 480bc tail run, first 49b0c state)',observation_sha256=sc.STAGE_ENTRY_SHA,case_index=row['case_index'],family=row['fixture']['family'],fixture=row['fixture'],input_ram_sha256=insha,
            recorded_input_ram_sha256=row['phases'][0]['input_ram_sha256'],entry_state=brief(e),original_480cc_state=dict(ram_sha256=sha(b['ram']),a7=hex(b['a7']),instruction=b['instruction']),instructions_49b0c_to_480cc=b['instruction']-e['instruction'])
        assert insha==row['phases'][0]['input_ram_sha256']
        fx=captured_fx('nat-entry-%04d'%row['case_index'],e,prov,'declared 49b0c entry captured at the first execution of 49b0c (JSR at 480c6, return LONG 480cc) of the original 47a94 body + 480bc tail run of case %d (%s): RAM, 14 registers, A5 = 108000, A7 = %x and the live stack bytes'%(row['case_index'],row['fixture']['family'],e['a7']))
        I.add('natural-stage-entry-%04d'%row['case_index'],'natural-stage-entry','stage_entry_body case %d (%s): 49b0c entry of the original run, stop 480cc'%(row['case_index'],row['fixture']['family']),fx,stop=RET_FRAME,store=True,original=b,facts=dict(entry_instruction=e['instruction']))
        entry_states.append((row['case_index'],e,b))
    return frame_states,entry_states


def guard_items(I,cases,program):
    i,c=2963,cases[2963];assert c['family']=='each-player-all19-known-callbacks-live-loop' and c['player']==0 and c['slots'][0]==0x49e34
    j,d=3077,cases[3077];assert d['player']==1 and d['slots'][1]==0x49e34
    L0=sil_loop_fx('g0',i,c);L1=sil_loop_fx('g1',j,d);n=base_state(cases)[1];N0=sil_loop_fx('gn',base_state(cases)[0],n)
    def var(fx,**kw):
        f=dict(fx);regs=dict(f['regs'])
        for k,v in kw.items():
            if k in ('initial_a7','entry_pc'):f[k]=v
            else:regs[k]=v
        f['regs']=regs;return f
    def g(label,desc,guard,fx,setup=(),stop=PROBE_STOP):
        I.add(label,'guard',desc,fx,setup,stop=stop,store=True,guard=guard,model=False,delta=0)
    pc0,pc1=0x49b2c,0x49b82
    for slot,fx,pc,tag in ((0x10d734,L0,pc0,'slot0'),(0x10d738,L1,pc1,'slot1')):
        g('guard-odd-target-%s'%tag,'JSR (A1) with A1 = 49e35 (odd): the Unicorn code hook reports the odd PC; no address error is raised before it',dict(problem='unsupported_code_target',target=0x49e35),fx,writes_of({slot:(4,0x49e35)}))
        g('guard-top-byte-01049e34-%s'%tag,'JSR (A1) with A1 = 01049e34: the Unicorn M68000 core does not fold the PC to 24 bit (fetch at 01049e34 is unmapped); the C++ contract rejects it as a checked error; the real 24-bit bus folds it to 049e34 (Musashi probe)',
            dict(problem='unsupported_code_target',pc=pc,target=0x01049e34,unmapped_fetch=True),fx,writes_of({slot:(4,0x01049e34)}))
        g('guard-top-byte-ff049e34-%s'%tag,'JSR (A1) with A1 = ff049e34 (top BYTE ff)',dict(problem='unsupported_code_target',pc=pc,target=0xff049e34,unmapped_fetch=True),fx,writes_of({slot:(4,0xff049e34)}))
        g('guard-top-byte-80000049-%s'%tag,'JSR (A1) with A1 = 80000049',dict(problem='unsupported_code_target',pc=pc,target=0x80000049,unmapped_fetch=True),fx,writes_of({slot:(4,0x80000049)}))
        g('guard-ram-target-%s'%tag,'JSR (A1) with A1 = 106000 (RAM: not executable in the observer)',dict(problem='unmapped_or_protected',pc=pc,address=0x106000,size=2),fx,writes_of({slot:(4,0x106000)}))
        g('guard-rom-outside-unit-%s'%tag,'JSR (A1) with A1 = 4aa88 (ROM, outside every observed unit)',dict(problem='unsupported_code_target',target=0x4aa88),fx,writes_of({slot:(4,0x4aa88)}))
        g('guard-mid-instruction-%s'%tag,'JSR (A1) with A1 = 49b30 (inside the unit, the second word of the LEA at 49b2e: no instruction start)',dict(problem='unsupported_code_target',target=0x49b30),fx,writes_of({slot:(4,0x49b30)}))
        I.add('target-non-block-start-49e36-%s'%tag,'target-variant','JSR (A1) with A1 = 49e36 (the RTS inside the unit, a decoded instruction that is no block start): executed natively, the RTS pops the return LONG of the JSR; the C++ contract rejects the PC (observation only)',
            fx,writes_of({slot:(4,0x49e36)}),stop=RET_FRAME,store=True,model=False)
    g('guard-odd-A5','A5 = 108001: MOVEA.L 5734(A5),A1 at 49b10 reads an odd LONG',dict(problem='unsupported_odd_data_access',pc=0x49b10,address=0x10d735,size=4,access='read'),var(L0,a5=0x108001))
    g('guard-odd-A7-entry','A7 = 1feffd: the JSR 289e at 49b22 pushes an odd LONG',dict(problem='unsupported_odd_data_access',pc=0x49b22,address=0x1feff9,size=4,access='write',odd_write_restored=True),var(L0,initial_a7=0x1feffd))
    g('guard-rom-write-A7','A7 = 1100 (ROM): the JSR 289e at 49b22 pushes its return LONG into ROM',dict(problem='unmapped_or_protected',pc=0x49b22,address=0x10fc,size=4),var(L0,initial_a7=0x1100))
    cb,ret=sil_cb_fx('g',i,c,0x49de6)
    g('guard-odd-A0-49de6','49de6 entered with A0 = 100cb9 (odd): MOVE.W 78(A0),D0 reads an odd WORD',dict(problem='unsupported_odd_data_access',pc=0x49de8,address=0x100d31,size=2,access='read'),var(cb,a0=0x100cb9),stop=PROBE_STOP)
    cb5,ret5=sil_cb_fx('g',i,c,0x1d5e2)
    g('guard-odd-A6-1d5e2','1d5e2 entered with A6 = 106101 (odd): TST.W 3a(A6) reads an odd WORD',dict(problem='unsupported_odd_data_access',pc=0x1d5ee,address=0x10613b,size=2,access='read'),var(cb5,a6=0x106101),stop=PROBE_STOP)
    f,r=direct_fx('g',i,c,0x49afe,dict(a1=0x10d727),{},'odd A1')
    g('guard-odd-A1-49afe','49afe entered with A1 = 10d727 (odd): MOVE.W 2(A1),D6 reads an odd WORD',dict(problem='unsupported_odd_data_access',pc=0x49afe,address=0x10d729,size=2,access='read'),f)
    f,r=direct_fx('g',i,c,0x49bb4,dict(a1=0x10d727),{},'odd A1')
    g('guard-odd-A1-49bb4','49bb4 entered with A1 = 10d727 (odd): MOVE.W 4(A1),D0 reads an odd WORD',dict(problem='unsupported_odd_data_access',pc=0x49bb4,address=0x10d72b,size=2,access='read'),f)
    f,r=direct_fx('g',i,c,0x49bb4,dict(a1=0x4000),{},'ROM A1')
    g('guard-rom-write-49bb4','49bb4 entered with A1 = 4000 (ROM): the WORD ffff written to 4(A1) at 49bb8 hits ROM',dict(problem='unmapped_or_protected',pc=0x49bb8,address=0x4004,size=2),f)
    f,r=direct_fx('g',i,c,0x49c20,dict(a5=0x8000),{},'A5 in ROM')
    g('guard-rom-write-49c20','49c20 entered with A5 = 8000: the slot LONG address 8000+5734 lies in ROM, MOVE.L A0,(A1) at 49c2e writes ROM',dict(problem='unmapped_or_protected',pc=0x49c2e,address=0xd734,size=4),f)
    f,r=direct_fx('g',i,c,0x49c20,dict(a5=0x108001),{},'odd A5')
    g('guard-odd-slot-write-49c20','49c20 entered with A5 = 108001: the slot LONG address is odd, MOVE.L A0,(A1) at 49c2e writes an odd LONG',dict(problem='unsupported_odd_data_access',pc=0x49c2e,address=0x10d735,size=4,access='write',odd_write_restored=True),f)
    g('guard-bad-stop-49b2e-null-path','stop 49b2e declared on a null-slot run: the run never reaches it and the final RTS returns into 480cc (no executor)',dict(problem='unsupported_code_target',target=RET_FRAME),N0,stop=0x49b2e)
    g('guard-bad-stop-4d7f0-null-path','stop 4d7f0 declared on a null-slot run',dict(problem='unsupported_code_target',target=RET_FRAME),N0,stop=TRAP_PC)
    tf=[it for it in I.items if it['label'].startswith('trap-4d7a6')][0]
    g('guard-trap-reached-without-stop','4d7a6 with source index 0 and the stop declared behind it (1daa2): the TRAP #15 at 4d7f0 is reached and refused',dict(problem='unsupported_TRAP',pc=TRAP_PC,opcode=0x4e4f),tf['fx'],stop=0x1daa2)
    I.add('boundary-zero-step','boundary','zero-step: the stop PC equals the entry PC 49b0c, nothing is executed',N0,stop=ENTRY,store=True,model=False)
    I.add('boundary-zero-step-callback','boundary','zero-step at the callback entry 49de6',cb,stop=0x49de6,store=True,model=False)


# ----------------------------------------------------------------------------------
# Census (one continuous native run + model per condition) and storage
# ----------------------------------------------------------------------------------
STACK_LO=S-0x40
ALLOWED_WRITES=((0x10d726,0x10d732),(0x10d732,0x10d733),(0x10d734,0x10d73c),(STACK_LO,S+4))
FOLDED_PCS=FOLDED_NZ
CENSUS=[];ROWS={}


def stack_window_diff(a,b):
    """Indices of 64KiB-image bytes that differ outside the declared stack window [1feff0,1ff000) (the original observers keep the stack outside their 64KiB window, the unit images mirror it)."""
    lo,hi=(S-0xc)&0xffff,((S+4)&0xffff) or 0x10000
    return [i for i in range(0x10000) if a[i]!=b[i] and not lo<=i<hi]


def census_row(program,it,p):
    pcs=p['pcs'];lead=collections.Counter(pc for pc in pcs if pc in LEADERS);events=p['events']
    writes=[e for e in events if e['region']=='ram' and e['access']=='write']
    stray=sorted({hex(e['address']) for e in writes if not any(lo<=e['address']<hi for lo,hi in ALLOWED_WRITES)})
    reads=[(e['address'],e['size']) for e in events if e['region']=='fixed' and e['access']=='read']
    ram_b=p['ram_before'];ram_a=p['ram_after']
    def lng(ram,addr):return int.from_bytes(ram[addr-0x100000:addr-0x100000+4],'big')
    jsr={}
    for b in p['boundaries']:
        if b['pc'] in (0x49b2c,0x49b82):jsr[hex(b['pc'])]=hex(b['registers']['a1'])
    row=dict(label=it['label'],group=it['group'],instructions=len(pcs)-1,leaders={hex(k):v for k,v in sorted(lead.items())},entry_pc=hex(p['incoming']['pc']),stop_pc=hex(it['stop']),final_pc=hex(p['outgoing']['pc']),
        a7_delta=sx32(p['outgoing']['a7']-p['incoming']['a7']),ram_writes=len(writes),stray_writes=stray,ports=sum(1 for e in events if e['region'] in PORT_REGIONS),fixed_reads=sorted({(hex(a),n) for a,n in reads}),
        slots_before=[hex(lng(ram_b,0x10d734)),hex(lng(ram_b,0x10d738))],slots_after=[hex(lng(ram_a,0x10d734)),hex(lng(ram_a,0x10d738))],jsr_targets=jsr,
        folded_executed=sorted(hex(x) for x in set(pcs)&set(FOLDED_PCS)),
        regs_at_first_49ab4={k:hex(v) for k,v in next((b['registers'] for b in p['boundaries'] if b['pc']==0x49ab4),{}).items() if k in ('d1','d6')},
        entry_regs={k:hex(p['incoming'][k]) for k in ('d1','d6')},mode=ram_b[0x12],inputs=[ram_b[0x4caa],ram_b[0x4cab],ram_b[0x4cb0],ram_b[0x4cb1]],a6=hex(p['incoming']['a6']))
    return row


def run_item(program,it):
    """Normal condition: one continuous native run from the declared fixture to the stop, stop evidence, model comparison; returns (row, phase)."""
    p=probe(program,it['fx'],it['setup'],it['stop'])
    p.update(label=it['label'],step=0,step_stop_pc=it['stop'],phase_in_step=0)
    evidence=stop_evidence(program,p)
    row=census_row(program,it,p);row['stop_evidence']=evidence
    if it['model'] and it['stop']!=p['incoming']['pc']:
        m=check_model(program,it['label'],p,it['stop']);row['model_equal']=m['equal'];row['max_stack_depth']=m.get('max_stack_depth');row['model_leaders']=m.get('leaders')
        if 'model_error' in m:row['model_error']=m['model_error']
    else:row['model_equal']=None
    orig=it.get('original')
    if orig is not None:
        diff=stack_window_diff(p['ram_after'],orig['ram'])
        o=p['outgoing'];regs_equal=all(o[k]==orig['regs'][k] for k in orig['regs']) and o['a7']==orig['a7'] and o['a5']==orig['a5']
        row['original_compare']=dict(ram_equal_outside_stack_window=not diff,differing_bytes=len(diff),registers_a7_a5_equal=regs_equal,bank_equal=p['modeled_bank']==orig['bank']*0x100000,
            ports_equal=True,instructions_native=len(p['pcs'])-1,instructions_original=orig['instruction']-it['facts']['entry_instruction'])
        if diff or not regs_equal or not row['original_compare']['bank_equal']:
            DISCREPANCIES.append(dict(label=it['label'],kind='native-unit-vs-original-run',detail=row['original_compare']))
    return row,p


def build_spec(it,p):
    fx=dict(it['fx']);fx['label']=it['label']
    if it['guard'] is not None:
        step=dict(label=it['label'],changes=list(it['setup']),stop_pc=it['stop'],checkpoints=[],a7=('entry',0))
        return dict(label=it['label'],group=it['group'],fixture=fx,steps=[step],provenance=it['prov'],guarded=True,guard=it['guard'])
    pcs=p['pcs'];entry=pcs[0];order=[]
    if it['stop']!=entry:
        for pc in pcs[1:]:
            if pc in LEADERS and pc not in order and pc!=entry and pc!=pcs[-1]:order.append(pc)
    delta=sx32(p['outgoing']['a7']-p['incoming']['a7'])
    step=dict(label=it['label'],changes=list(it['setup']),stop_pc=it['stop'],checkpoints=order,a7=('entry',delta))
    return dict(label=it['label'],group=it['group'],fixture=fx,steps=[step],provenance=it['prov'])


def condition_summary(spec,split,control):
    c=control[-1];pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),
        ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),external_reads=sum(1 for e in ev if e['region']=='external'),
        ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=fh.ordered_ports_sha(ev),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'])


# ----------------------------------------------------------------------------------
# Bus width probe (declared extra instrument: Musashi M68000 oracle of the repository, 24-bit address bus)
# ----------------------------------------------------------------------------------
def musashi_run(program,fx,setup,budget=3000):
    from musashi_oracle import MusashiOracle
    cpu=MusashiOracle();cpu.reset(clear_memory=True);cpu.load(0,program[:0x100000])
    ram=bytearray(fx['ram'])
    for w in setup:ram[w['address']-0x100000:w['address']-0x100000+w['size']]=w['value'].to_bytes(w['size'],'big')
    cpu.load(0x100000,bytes(ram));cpu.load(fx['initial_a7'],RET_BYTES)
    cpu.set_reg('sr',0x2000);cpu.set_reg('a7',fx['initial_a7'])
    for k,v in fx['regs'].items():cpu.set_reg(k,v)
    cpu.set_reg('pc',fx['entry_pc'])
    res=cpu.run(budget,RET_FRAME)
    return res,cpu.registers(),cpu.read(0x100000,0x10000)


def bus_probe(program,cases):
    i,c=2963,cases[2963];fx=sil_loop_fx('bus',i,c);out=[]
    ref=musashi_run(program,fx,writes_of({0x10d734:(4,0x49e34)}))
    def same(r,mask_slot=True):
        ram_a=bytearray(r[2]);ram_b=bytearray(ref[2])
        for k in range(0xd734-0x0,0xd738):ram_a[k]=0;ram_b[k]=0
        return r[1]==ref[1] and bytes(ram_a)==bytes(ram_b)
    for target in (0x49e34,0x01049e34,0x02049e34,0x80049e34,0xff049e34):
        r=musashi_run(program,fx,writes_of({0x10d734:(4,target)}))
        out.append(dict(target=hex(target),status=r[0]['status'],instructions=r[0]['instructions'],final_pc=hex(r[0]['pc']),equal_to_folded_049e34_registers_and_RAM_except_slot=same(r)))
    r=musashi_run(program,fx,writes_of({0x10d734:(4,0x49e35)}),200)
    out.append(dict(target='0x49e35 (odd)',status=r[0]['status'],instructions=r[0]['instructions'],final_pc=hex(r[0]['pc']),a7=hex(r[1]['a7']),sr=hex(r[1]['sr']),fault_address=hex(r[0]['fault_address']),
        note='odd PC: Musashi takes an address error exception (vector 3), pushes its frame (A7 below the JSR return LONG) and continues at the handler address in BIOS space (outside the mapped harness: memory_fault there)'))
    return out


def hexset(s):return sorted(hex(x) for x in s)
NATURAL16={0x49ab4,0x49ac0,0x49ad6,0x49ade,0x49afc,0x49b0c,0x49b3a,0x49b52,0x49b56,0x49b5a,0x49b62,0x49b90,0x49ba8,0x49bac,0x49bb0,0x49bb4}
INSTALLED11={0x49e34,0x49de6,0x1bec0,0x1d5ac,0x1d5e2,0x1d61a,0x1d664,0x1d6c2,0x1d8cc,0x1da60,0xe73f2}
U6C6={0x49d88,0x49e38,0x49e9c,0x49eba,0x49ef0,0x49f2c}


def contract_claims(R,items,guard_results,bus,coverage_hits):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    rows=list(R.values());by=lambda g:[r for r in rows if r['group']==g]
    nat=by('natural-stage-frame')+by('natural-stage-entry');ibl={it['label']:it for it in items}
    ok=len(by('natural-stage-frame'))==64 and len(by('natural-stage-entry'))==142
    nul=all(r['slots_before']==['0x0','0x0'] and r['mode']!=2 for r in nat)
    sets=set(frozenset(int(k,16) for k in r['leaders'])&frozenset(LEADERS) for r in nat)
    cnt=collections.Counter(r['instructions'] for r in nat)
    claim('206 natural frames (stage_frame 64 + stage_entry_body 142) enter 49b0c from 480c6 with both slots null and 100012 <> 2, execute the 16 listed block starts only (default mask path, no callback, no 289e) and return to 480cc after 125 instructions',
        'confirmed' if ok and nul and len(sets)>=1 and set().union(*sets)<=NATURAL16 and set(cnt)=={125} else 'contradicted',
        dict(frames=len(by('natural-stage-frame')),entries=len(by('natural-stage-entry')),slots_null_mode_not_2=nul,union_block_starts=hexset(set().union(*sets)),not_executed_u6a=hexset({pc for pc in CONTRACT_STARTS['U6a']}-set().union(*sets)),instruction_counts=dict(cnt)))
    hi=all(r['inputs'][0]&0xf0==0 and r['inputs'][2]&0xf0==0 for r in nat)
    claim('49acc is never executed naturally because the input BYTEs 104caa / 104cb0 have bits 4..7 clear in all 206 frames','confirmed' if hi and 0x49acc not in set().union(*sets) else 'contradicted',dict(high_nibble_clear=hi,inputs_distinct=sorted({tuple(r['inputs']) for r in nat})[:8]))
    a6f=collections.Counter(r['a6'] for r in by('natural-stage-frame'));a6e=collections.Counter(r['a6'] for r in by('natural-stage-entry'))
    claim('stage_frame boundary A6 = 100820 (64/64); stage_entry_body A6 is unknown in the contract',('confirmed' if dict(a6f)=={'0x100820':64} else 'contradicted'),dict(stage_frame=dict(a6f),stage_entry_body=dict(a6e),note='stage_entry_body A6 observed natively here'))
    claim('natural frames: no slot (10d734..10d73b) write, no RAM write outside 10d726..10d731 and the live stack, A7 = 1feff8 at entry, stack depth 4','confirmed' if all(not r['stray_writes'] and r['max_stack_depth']==4 for r in nat) else 'contradicted',
        dict(max_depth=max(r['max_stack_depth'] for r in nat),stray=[r['label'] for r in nat if r['stray_writes']][:5]))
    orig=[r['original_compare'] for r in nat]
    claim('the native unit run from the captured 49b0c state reproduces the ORIGINAL uninterrupted run at 480cc (RAM outside the declared stack window, 14 registers + A5 + A7, bank)','confirmed' if len(orig)==206 and all(o['ram_equal_outside_stack_window'] and o['registers_a7_a5_equal'] and o['bank_equal'] and o['instructions_native']==o['instructions_original'] for o in orig) else 'contradicted',dict(compared=len(orig)))
    tgt={'0x49b2c':set(),'0x49b82':set()}
    for r in by('loop-corpus'):
        for k,v in r['jsr_targets'].items():tgt[k].add(int(v,16))
    want=set(sil.CALLBACKS)|{0x1da60}
    claim('JSR (A1) calls each of the 19 known targets from both slots (stage input loop corpus, live loop)','confirmed' if want<=tgt['0x49b2c'] and want<=tgt['0x49b82'] else 'not-reproduced',dict(slot0_missing=hexset(want-tgt['0x49b2c']),slot1_missing=hexset(want-tgt['0x49b82']),other_targets=hexset((tgt['0x49b2c']|tgt['0x49b82'])-want)))
    loop=by('loop-corpus')
    def depth(pred):return max([r['max_stack_depth'] for r in loop if r['model_equal'] and pred(r)] or [0])
    def used(r):return {int(v,16) for v in r['jsr_targets'].values()}
    core=depth(lambda r:not r['jsr_targets']);inst=depth(lambda r:used(r)&INSTALLED11);u6c=depth(lambda r:used(r)&U6C6)
    claim('stack depth below the 49b0c entry A7: core 4, installed callbacks 12, U6c callbacks 14','confirmed' if (core,inst,u6c)==(4,12,14) else 'understated-or-differs',dict(core=core,installed_callbacks=inst,u6c_callbacks=u6c))
    cov=set(coverage_hits)
    claim('all 151 block starts: 150 executed natively + the TRAP boundary 4d7f0 reached as a stop (plus 289e/28a8/28ac for the inline modelled readiness)','confirmed' if (CONTRACT_ALL-{TRAP_PC})<=cov and TRAP_PC in {int(r['final_pc'],16) for r in by('trap-boundary')} else 'not-reproduced',dict(executed=len(CONTRACT_ALL&cov),missing=hexset(CONTRACT_ALL-cov-{TRAP_PC})))
    tr=by('trap-boundary')
    claim('4d7a6 with BYTE 27(source) = 0 stops at 4d7f0 (TRAP #15) with D0.W = 0 directly after the not-taken BNE.W at 4d7ec, through the direct entry, 1da60 and the live slot loop','confirmed' if tr and all(r['final_pc']=='0x4d7f0' and r['model_equal'] for r in tr) else 'contradicted',dict(conditions=len(tr),entries=dict(collections.Counter(r['entry_pc'] for r in tr))))
    idx={}
    known=U6_RANGES+fh.NEW_RANGES+fh.EXISTING_RANGES
    for r in by('helper-corpus'):
        c=ibl[r['label']]['prov']
        m=re.search(r'\(active-player-all255-index-byte-select\)',c)
        if not m:continue
        reads=[int(a,16) for a,n in r['fixed_reads'] if 0x4cf64<=int(a,16)<0x4df60]
        if reads:idx[r['label']]=reads[0]
    code_hits={}
    for lab,a in idx.items():
        k=(a-0x4cf6e)//16
        if any(lo<=a<hi for lo,hi in known):code_hits[k]=hex(a)
    want_idx=set(range(132,139))|set(range(167,170))
    claim('4d7a6 index table reads: indices 132..138 and 167..169 read bytes inside code ranges (4d7a6..4d81c and 4d9d6..4da08); every read lies in 4cf7e..4df60','confirmed' if set(code_hits)==want_idx and idx and all(0x4cf7e<=a<0x4df60 for a in idx.values()) else 'differs',dict(indices_reading_known_code=sorted(code_hits),expected=sorted(want_idx),indices_observed=len(idx),min_read=hex(min(idx.values())) if idx else None,max_read=hex(max(idx.values())) if idx else None))
    fe=set().union(*[set(int(x,16) for x in r['folded_executed']) for r in rows])
    l49=set().union(*[set(int(k,16) for k in r['leaders']) for r in rows])
    claim('49dd4 / 49e8a / 49f4a (not block starts) are executed natively inside their blocks; 49f4a is reached from both 49f3e and 49f46','confirmed' if fe==set(FOLDED_NZ) and {0x49f3e,0x49f46}<=l49 else 'not-reproduced',dict(executed=hexset(fe),predecessors_seen=hexset({0x49f3e,0x49f46}&l49)))
    fr=set()
    for r in rows:
        for a,n in r['fixed_reads']:fr.add(int(a,16))
    claim('ROM data reads only from the default mask 49ab0..49ab3 and the table window 4cf7e..4df60; writes only 10d726..10d731, 10d732, 10d734..10d73b and the stack; no port/PVC/bank write',
        'confirmed' if all(a in range(0x49ab0,0x49ab4) or 0x4cf7e<=a<0x4df60 for a in fr) and not any(r['stray_writes'] or r['ports'] for r in rows) else 'contradicted',dict(rom_read_min=hex(min(fr)),rom_read_max=hex(max(fr)),stray=[r['label'] for r in rows if r['stray_writes']][:5],ports=sum(r['ports'] for r in rows)))
    def ev(label):return R.get(label)
    cl=[r for r in by('loop-corpus') if 'first-callback' in r['label']]
    claim('first callback clears / installs the second slot before the live read: 1d5ac (10d683 bit 2 clear), 1d61a (bit 7 path) clear it, 49de6 tail installs 49e34 in slot (D0.W & 1)',
        'confirmed' if len(cl)==3 and any(r['slots_after'][1]=='0x0' and '0x49b82' not in r['leaders'] for r in cl if 'clears' in r['label']) and any(r['slots_after'][1]=='0x49e34' and '0x49b82' in r['leaders'] for r in cl if 'installs' in r['label']) else 'not-reproduced',
        {r['label']:dict(slots_before=r['slots_before'],slots_after=r['slots_after'],second_jsr='0x49b82' in r['leaders']) for r in cl})
    cr=by('helper-direct');c4=[r for r in cr if r['label'].startswith('carry-4836e')]
    claim('4836e is a known-carry producer: 10d683 bit 2 = 0 -> 4837e (C set), bit 2 = 1 -> 48378 (C clear); the consumer 1d5b2 branches on it (1d5ac callback: release 49c32 only when C = 0)',
        'confirmed' if c4 and all((('0x48378' in r['leaders'])==bool(int(r['label'][-2:],16)>>2&1)) and (('0x4837e' in r['leaders'])==(not (int(r['label'][-2:],16)>>2&1))) for r in c4) else 'contradicted',dict(conditions=len(c4)))
    succ={}
    for pc,(a,b) in {0x49b28:(0x49b36,0x49b2c),0x49b7e:(0x49b8c,0x49b82),0x4d7c6:(0x4d7d0,0x4d7ca),0x1d5b2:(0x1d5c0,0x1d5b6)}.items():
        succ[hex(pc)]=dict(branch_one=any(hex(a) in r['leaders'] and hex(pc) in r['leaders'] for r in rows),branch_two=any(hex(b) in r['leaders'] and hex(pc) in r['leaders'] for r in rows))
    claim('the four carry-consuming blocks 49b28 49b7e 4d7c6 1d5b2 take both outcomes natively',"confirmed" if all(v['branch_one'] and v['branch_two'] for v in succ.values()) else 'not-reproduced',succ)
    f66=[r for r in cr if r['label'].startswith('input-49f66')]
    claim('49f66 does not set D1 and D6 (the values at 49ab4 equal the entry values for D1; D6 is rewritten only in its low byte/word)','confirmed' if f66 and all(r['regs_at_first_49ab4']['d1']==r['entry_regs']['d1'] and int(r['regs_at_first_49ab4']['d6'],16)>>8==int(r['entry_regs']['d6'],16)>>8 for r in f66) else 'contradicted',dict(conditions=len(f66)))
    tb={g['label']:g for g in guard_results}
    top=[g for k,g in tb.items() if 'top-byte' in k or 'odd-target' in k]
    claim('JSR (A1) with a nonzero top BYTE: Unicorn M68000 does not fold the PC (unmapped fetch at the 32-bit value); the 24-bit Musashi bus runs the folded target 049e34 to completion with identical registers/RAM; an odd target raises an address error on Musashi (Unicorn: no exception, observer hook only). The C++ checked error is the deliberate difference.',
        'confirmed (deliberate difference)' if all(b['status']=='sentinel' and b['equal_to_folded_049e34_registers_and_RAM_except_slot'] for b in bus[:5]) and bus[5]['status']=='memory_fault' and len(top)>=8 else 'not-reproduced',dict(bus_width_probe=bus,unicorn_guards=sorted(tb)))
    claim('CCR/carry values and the Unknown-carry API error; block-internal/folded PC entry rejection of the API','not-observable','SR is never read; the API rejection is not observable natively (the observer executes any decoded instruction start)')
    return claims


def select_stored(items,rows):
    """Deterministic storage selection: every `store=True` item; `store='sig'` items: first of every distinct leader signature; other groups: first of every signature, at most 40 per group (evenly spread)."""
    chosen=[];seen=set();per=collections.defaultdict(list)
    for it in items:
        if it['guard'] is not None or it['label'] not in rows:continue
        if it['store'] is True:chosen.append(it['label']);continue
        sig=(it['group'],tuple(rows[it['label']]['leaders']))
        if sig in seen:continue
        seen.add(sig)
        if it['store']=='sig':chosen.append(it['label'])
        else:per[it['group']].append(it['label'])
    for g,labels in per.items():chosen+=sc.spread(labels,40)
    return set(chosen)


def main():
    dev_filter=sys.argv[1] if len(sys.argv)>1 else None
    out_dir=OUT if dev_filter is None else Path('/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/dev_out')
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    configure(program,out_dir)
    cases=sil.build_cases()
    stage_ver,stage_in=sc.stage_frame_inputs(program)
    entry_obs=json.loads(sc.pin(sc.STAGE_ENTRY,sc.STAGE_ENTRY_SHA));assert len(entry_obs['results'])==142
    print('seeds',len(stage_in),len(entry_obs['results']),flush=True)
    I=Items()
    frame_states,entry_states=natural_items(I,stage_in,entry_obs,program)
    loop_items(I,cases);callback_direct_items(I,cases);helper_corpus_items(I,cases);random_callback_items(I,cases);random_loop_items(I,cases)
    mask_items(I,cases);helper_direct_items(I,cases);trap_items(I,cases,program);guard_items(I,cases,program)
    items=I.items;print('items',len(items),flush=True)
    R={};phases={}
    for n,it in enumerate(items):
        if it['guard'] is not None:continue
        row,p=run_item(program,it);R[it['label']]=row
        if n%1000==0:print('census',n,flush=True)
    selected=select_stored(items,R)
    selected|={it['label'] for it in items if it['guard'] is not None}
    if dev_filter:selected={l for l in selected if dev_filter in l}
    print('census done',len(R),'stored',len(selected),'model equal',sum(1 for r in R.values() if r['model_equal']),'unequal',sum(1 for r in R.values() if r['model_equal'] is False),flush=True)
    coverage_hits=set()
    for r in R.values():coverage_hits|={int(k,16) for k in r['leaders']}
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,fh.CONTRACT,sc.STAGE_FRAME,ROOT/'artifacts/dependencies/musashi_oracle_build/libmusashi_oracle.dylib'}
    input_paths.update(Path(p) for p in sc.SEED_FILES)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin_ref=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin_ref['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];summaries=[];model_checks=[];coverage_by=collections.defaultdict(list);totals=dict(split=0,control=0);EV={}
    stored=[it for it in items if it['label'] in selected]
    for number,it in enumerate(stored):
        p=None
        if it['guard'] is None:
            p=probe(program,it['fx'],it['setup'],it['stop'])
        spec=build_spec(it,p)
        split,control=run_spec(program,spec)
        mrow=None
        if it['guard'] is None:
            c=control[-1]
            assert c['ram_after']==p['ram_after'] and c['pcs']==p['pcs'],it['label']
            if it['model'] and it['stop']!=c['incoming']['pc']:mrow=check_model(program,it['label'],c,it['stop']);model_checks.append(mrow)
        summaries.append(condition_summary(spec,split,control))
        for pc in set(pc for q in control for pc in q['pcs'])&LEADERS:coverage_by[pc].append(spec['label'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=fh.store('c%04d_split'%number,split,BLOCKS),continuous_control=fh.store('c%04d_control'%number,control,BLOCKS),reproduced_twice=True,continuous_split_equivalent=True,compared_with_chain=False,stored_from_step=0)
        for rows_ in (result['phases'],result['continuous_control']):
            for r in rows_:artifacts.update(r['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        if number%50==0:print('stored %d/%d %s %d split %d control'%(number+1,len(stored),spec['label'],len(split),len(control)),flush=True)
    bus=bus_probe(program,cases)
    guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard']) for g in guards if g['expected_guard'] is not None]
    claims=contract_claims(R,items,guard_reports,bus,coverage_hits) if not dev_filter else []
    for c in claims:
        if c['verdict'] in ('contradicted','understated-or-differs','not-reproduced','differs'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    instructions=[]
    for lo,hi in U6_RANGES+EXISTING_RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,u6_ranges=U6_RANGES,data_ranges=DATA_RANGES,existing_ranges=EXISTING_RANGES,instructions=instructions,boundary_stop_pcs=(RET_FRAME,TRAP_PC),
        stop_rules={'return LONG':'the RTS that pops the declared return LONG that was on the stack top at the entry (480cc for 49b0c, 49b2e/49b84 for callbacks, the caller address for helpers)','4d7f0':'directly after the not-taken BNE.W at 4d7ec (D0.W = 0); the TRAP #15 is never executed'},
        folded_not_block_starts=hexset(FOLDED_NZ),new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in U6_RANGES}),indent=2)+'\n').encode()
    (out_dir/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    def aggregate(rows_):
        t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
        for r in rows_:
            for ph in r['phases']:
                for k,v in ph['counts'].items():t[k]+=v
        return t
    group_counts=collections.Counter(it['group'] for it in items)
    block_cov=[]
    census_leader_hits=collections.defaultdict(lambda:[0,None])
    for lab,r in R.items():
        for k in r['leaders']:
            h=census_leader_hits[int(k,16)];h[0]+=1;h[1]=h[1] or lab
    for pc in sorted(LEADERS):
        block_cov.append(dict(pc=hex(pc),in_contract_list=pc in CONTRACT_ALL,unit=next((u for u,l in CONTRACT_STARTS.items() if pc in l),'readiness-289e' if pc in BB_289E else None),census_conditions=census_leader_hits[pc][0],first_condition=census_leader_hits[pc][1],
            stored_conditions=len(coverage_by.get(pc,())),executed_natively=pc in coverage_hits or pc==TRAP_PC and any(r['final_pc']==hex(TRAP_PC) for r in R.values()),stop_boundary_only=pc==TRAP_PC))
    census_report=[dict(label=lab,group=r['group'],entry=r['entry_pc'],stop=r['stop_pc'],final=r['final_pc'],instructions=r['instructions'],a7_delta=r['a7_delta'],leaders=r['leaders'],model_equal=r['model_equal'],
        slots_before=r['slots_before'],slots_after=r['slots_after'],jsr_targets=r['jsr_targets'],max_stack_depth=r.get('max_stack_depth'),fixed_reads=r['fixed_reads']) for lab,r in R.items()]
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),chain_vs_fresh_phases_compared=0,variant_child_layouts=[],
        guard_reports=guard_reports,negative_stop_checks=[],bank_reads_by_condition=[],bank_descriptor_search=[],new_ranges=U6_RANGES,existing_ranges=EXISTING_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=RANGE_TABLE,contract_block_starts=len(CONTRACT_ALL),contract_bundled_branches=len(CONTRACT_FOLD_ALL),
            observer_block_starts_u6=len(CONTRACT_ALL),observer_leaders_with_289e=len(LEADERS),u1_contract_sha256=sha(fh.CONTRACT.read_bytes())),
        contract_model_checks=model_checks,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=dict(natural_instruction_counts=dict(collections.Counter(r['instructions'] for r in R.values() if r['group'].startswith('natural')))),
        first_boundary_census=dict(census=census_report,counts=dict(group_counts)),
        census_model_checks=dict(runs=sum(1 for r in R.values() if r['model_equal'] is not None),equal=sum(1 for r in R.values() if r['model_equal']),unequal=[r['label'] for r in R.values() if r['model_equal'] is False][:20],model_errors=[r['label'] for r in R.values() if 'model_error' in r][:20]),
        seed_provenance=dict(files=sc.SEED_FILES,stage_frame=dict(verification_sha256=sc.STAGE_FRAME_SHA,cases=[dict(index=i,label=r['label'],input_sha256=r['input_sha256'],rebuilt_from=how,entry_ram_sha256=sha(e['ram']),original_480cc_ram_sha256=sha(b['ram'])) for (i,r,_,how),(_,e,b) in zip(stage_in,frame_states)]),
            stage_entry=dict(observation_sha256=sc.STAGE_ENTRY_SHA,cases=[dict(index=ci,family=row['fixture']['family'],entry_ram_sha256=sha(e['ram']),original_480cc_ram_sha256=sha(b['ram'])) for row,(ci,e,b) in zip(entry_obs['results'],entry_states)]),
            stage_input_loop=dict(corpus='tools/observe_stage_input_loop.py build_cases()/fixture() (read-only import)',cases=len(cases),tool_sha256=sha((ROOT/'tools/observe_stage_input_loop.py').read_bytes())),
            note='Declared fixtures: the first 49b0c state of each original run (RAM, 14 registers, A5 = 108000, A7 = 1feff8 and the live stack bytes: return LONG 480cc, then ff000; PVC bank words of the original run), the stage input loop corpus states (RAM + 14 registers, A5 = 108000, A7 = 1feffc with the declared return LONG), declared register overrides of helper entries, and declared host RAM writes applied before the first instruction of the condition.'),
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=summaries,group_counts=dict(group_counts),covered_PCs=sorted(set(pc for r in R.values() for pc in (int(k,16) for k in r['leaders']))),uncovered_u6_block_starts=hexset(CONTRACT_ALL-coverage_hits-{TRAP_PC}),
        uncovered_leaders_incl_289e=hexset(LEADERS-coverage_hits-{TRAP_PC}),block_start_coverage=block_cov,block_starts=BLOCKS,boundary_stop_pcs=(RET_FRAME,TRAP_PC),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[],bus_width_probe=bus,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes()),extra_probe='Musashi M68000 oracle (bus width probe only)',
            musashi_library_sha256=sha((ROOT/'artifacts/dependencies/musashi_oracle_build/libmusashi_oracle.dylib').read_bytes())),
        limitations=['Controlled incoming fixtures (the first 49b0c state of the 206 original natural runs, the stage input loop corpus states, declared register/RAM variants), not natural scheduler/gameplay reachability; declared RAM writes are applied before the first instruction of the condition only.',
            'The work RAM is mirrored in the 64KiB image (1feffc is offset effc) unlike the flat map of the original observers; the native-unit versus original-run comparison therefore excludes the declared stack window 1feff0..1ff000.',
            'The census conditions (all except the stored selection) are one continuous native run each plus the model comparison; the stored selection is reproduced fresh twice with split versus continuous equivalence.',
            'Native carry is unobserved (SR never read); the Unknown-carry API error and the block-internal / folded PC entry rejection are API-level checks, not observed here. The observer accepts any decoded instruction start as JSR (A1) target.',
            'Unicorn does not fold a PC to 24 bit and does not raise an address error for an odd PC before the observer hook; the 24-bit/odd-PC hardware behaviour is shown only by the extra Musashi probe (declared extra instrument).',
            'U6c callbacks (49d88 49e38 49e9c 49eba 49ef0 49f2c) have no installation path in the ROM (contract [I]); they are observed through declared slot values only.',
            'Game meanings of the RAM fields and the TRAP #15 handler remain unknown.'])
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),census=len(R),split=report['split_steps'],control=report['control_steps'],discrepancies=len(DISCREPANCIES),model_checks=len(model_checks),
        model_equal=sum(1 for m in model_checks if m['equal']),uncovered=report['uncovered_u6_block_starts'],sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
