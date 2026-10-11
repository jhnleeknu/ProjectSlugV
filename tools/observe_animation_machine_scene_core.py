"""Unpatched 480bc frame helper bundle U2 (scene core 1a73c and its callees) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the frame helper observer U1
(observe_animation_machine_frame_helpers and through it the card menu close / fade-card chain: persistent-CPU Observer with the declared host-change
vocabulary RAM write / PC redirect / A7 delta / register write at a step boundary, fresh-twice reproduction, split (stop at the first hit of every block leader)
versus continuous equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every imported tool module, ROM SHA/mtime guard).

Observed unit: the 1724 contract bytes of docs/analysis/animation-machine-scene-core-u2-contract.md (20 ranges around 1a73c, the pre-existing 289e is the only
callee outside them).  Boundary stops (option A of the contract): the BSR targets 1a0b6 / 1a470 / 1a7a8 and the non-null motion branch targets 19812 / 19844 /
19910.  A stop is accepted only directly after the transferring instruction; the boundary code is never executed.  The first boundary a run reaches is found by a
declared guarded probe run (the guard names the first PC outside the observed ranges); the real conditions then use that PC as the stop.

Seeds (all pinned by SHA256, rebuilt in this process):
  scene_frame  artifacts/scene_frame_execution: 594 cases rebuilt from artifacts/scene_general_initialization + host writes / carried native outputs, every
               input RAM checked against input_ram_sha256; all 594 are probed for their first U2 boundary, the 22 full-path cases and a representative sample of the
               19812 / 19844 / 1a0b6 stop cases are observed in full (direct 1a73c entry, A7 = 1feffc, return LONG ff000, bank 2 page as in the original observer).
  stage_frame  artifacts/stage_frame/verification.json: the stage-0 cases whose original trace enters 1a73c are rebuilt (smoke seeds + host writes, or the previous
               recorded native output) and run natively from 480bc through U1 into 1a73c (the U1 natural path).
  stage_entry  artifacts/stage_entry_body: the original 47a94 body is re-executed by the original observer until 1a73c; the RAM and registers at that point are the
               declared 1a73c-entry fixture (direct 1a73c entry).
  re-entries   native states captured at 1a78c 1a296 19bca 19d2c 1a776 1997c 19da0 19c22 from the original full-frame run (the captured RAM/registers/stack bytes are
               declared fixtures; execution then starts at that PC).
  fixtures     declared host RAM writes on a full-path seed for paths no seed executes (rect test, 197e6, 1a28a, condition indexes, shake, clamps, BVC, ADD.L carry).
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step
record; declared initial registers/stack LONGs are part of the fixture summary.

An independent Python model of the contract (a basic-block machine transcribed instruction by instruction from the original bytes of the contract table, 32-bit
register semantics, explicit word/byte operations and signed compares, NOT the C++) is compared with each native normal condition: block-leader sequence with the
full register file at every leader, the ordered RAM writes, the ordered port writes, ordered fixed/bank ROM reads, the final registers and the whole 64KiB RAM image.
Any difference is recorded in contract_discrepancies.
"""
import collections
import copy
import gzip
import json
import os
from pathlib import Path
import re
import struct
import sys
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_frame_helpers as fh
import observe_scene_frame_execution as sfe
import observe_stage_entry_body as seb
from disassemble_program import load_verified_program,disassemble_range
fc=fh.fc;close=fh.close;menu=fh.menu;op=fh.op;activation=fh.activation;shared=fh.shared;vsf=fh.vsf
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_scene_core_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-scene-core-u2-contract.md'
CONTRACT_SHA='f71a0727a4e09290f257bc93ef72a5ac426ba82d2ebf0cc825b7aaa14111097a'
SCOPE=ROOT/'docs/analysis/animation-machine-480bc-scope.md'
U1_CONTRACT=ROOT/'docs/analysis/animation-machine-frame-helpers-u1-contract.md'
ROM_SHA=op.ROM_SHA
sha=fc.sha
u8,u16,u32=op.u8,op.u16,close.u32
S=fc.S                                                      # 1feffc: initial A7 (the return LONG lives here)
A5V=0x108000
ENTRY_1A73C=0x1a73c
RETURN_FF000=0xff000                                        # return LONG of the original full-frame observer at A7 = 1feffc
KEYS=shared.isolated.REG_NAMES                              # d0..d7 a0..a6
KEYS14=tuple(vsf.KEYS)                                      # d0..d7 a0..a4 a6 (the 14 registers of the original observers)
PORT_REGIONS=fc.PORT_REGIONS
M32=0xffffffff
SCENE_OBS=ROOT/'artifacts/scene_frame_execution/observation.json'
SCENE_OBS_SHA='fc060d8c4d74b43d8bdb424f07d99478da6534f86db1426d4d7e3bd93ddac9f2'
SCENE_SEED=ROOT/'artifacts/scene_general_initialization/observation.json'
SCENE_SEED_SHA='7cf8f965dd1b774eafff1ad73400eab54dca1a8373f8a75ce6cb14557ddffa6e'
STAGE_ENTRY=ROOT/'artifacts/stage_entry_body/observation.json'
STAGE_ENTRY_SHA='1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207'
STAGE_FRAME=fh.STAGE_VERIFICATION
STAGE_FRAME_SHA='47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5'
BOUNDARY_BSR={0x1a0b6:(0x1a292,0x1a296),0x1a470:(0x1a466,0x1a46a),0x1a7a8:(0x1a788,0x1a78c)}       # stop PC -> (BSR.W PC, pushed return LONG)
BOUNDARY_BNE={0x19812:0x1980a,0x19844:0x1983a,0x19910:0x198f6}                                       # stop PC -> BNE.W PC (A1 <> 0 at 10d3b4)
BOUNDARY_CALLERS={0x19812:(0x1a776,0x19bca,0x19d2c),0x19844:(0x19c22,),0x19910:(0x1997c,0x19da0)}   # return LONG expected on the stack at the motion stop
BOUNDARIES_U2=tuple(sorted(list(BOUNDARY_BSR)+list(BOUNDARY_BNE)))
DISCREPANCIES=[]
INFO=[]

# U2 ranges are read from the contract table (and byte-checked against the ROM in main()); 289e is the only pre-existing callee
U2_RANGES=()
EXISTING_RANGES=((0x289e,0x28ae),)
EXTRA_LEADERS=(0x1a2c6,0x1a2d4,0x1a2d8,0x1a2dc)               # JSR d8(pc,Xn) return address and the three table slots (reached by the computed JSR)


def parse_contract_ranges(program):
    ranges=[];table=[]
    for line in CONTRACT.read_text().splitlines():
        if line.startswith('| `') and '..' in line:
            cells=[c.strip().strip('`') for c in line.strip('|').split('|')]
            lo,hi=(int(x,16) for x in cells[0].split('..'))
            ok=program[lo:hi].hex()==cells[1];table.append(dict(range='%x..%x'%(lo,hi),bytes_equal_to_rom=ok,size=hi-lo));assert ok,cells[0]
            ranges.append((lo,hi))
    assert len(ranges)==20 and sum(h-l for l,h in ranges)==1724
    return tuple(ranges),table


def contract_lists():
    """Block start list (215 PCs) and the bundled-branch list (84 PCs) of the contract text."""
    lines=CONTRACT.read_text().splitlines()
    pcs=lambda text:set(int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',text))
    starts=bundled=None
    for i,line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (215개)**'):starts=pcs(lines[i+2])
        if line.startswith('- **묶인 조건분기 PC (84개'):bundled=pcs(lines[i+2])
    assert starts and bundled and len(starts)==215 and len(bundled)==84
    return starts,bundled


def sx16(v):
    v&=0xffff;return v-0x10000 if v&0x8000 else v


def sx32(v):
    v&=M32;return v-(1<<32) if v&0x80000000 else v


# ----------------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------------
def W(address,size,value,why):return fc.ram_write(address,size,value,why)


def pvc_page(ff8,ff9):
    """Raw PVC page with the last two register writes the original code made (2ffff0 then 2ffff2)."""
    page=bytearray(8192);page[0x1ff0:0x1ff2]=ff8.to_bytes(2,'big');page[0x1ff2:0x1ff4]=ff9.to_bytes(2,'big');return bytes(page)


BANK2=((0x200000,0xa0,0x1000),fh.pvc_page(2))                # initial state of the original full-frame observer (bank 1000 selected)
BANK3_MID=((0x300000,0xa0,0x2000),pvc_page(0,0x2000))        # state inside 1a73c after 1a742 / 1a74a (WORD 2000 -> 2ffff2, WORD 0 -> 2ffff0)


def make_fx(name,ram,regs,bank,entry,a7,prov,host_writes=(),stack=(),external=0,role=''):
    """Declared fixture.  `regs`: d0..d7 a0..a4 a6 (and optionally a5; default 108000).  `stack`: [(address,bytes)] declared stack bytes written into the RAM image
    (the mirror of the work RAM: 1feffc is offset effc of the 64KiB image).  `bank`: (bank_state,pvc_page)."""
    ram=bytearray(ram);assert len(ram)==0x10000
    writes=list(host_writes)
    for address,raw in stack:
        assert (address&0xffff)+len(raw)<=0x10000
        ram[address&0xffff:(address&0xffff)+len(raw)]=raw
        writes.append(dict(address=address,size=len(raw),hex=bytes(raw).hex(),why='declared stack bytes at %x (work RAM mirror offset %04x)'%(address,address&0xffff)))
    r={k:regs[k]&M32 for k in KEYS14};r['a5']=regs.get('a5',A5V)&M32
    state,page=bank
    return dict(group='scene-core',label=name,entry_pc=entry,ram=bytes(ram),pvc=page,external=external,regs=r,initial_a7=a7,bank_state=state,stop_pc=entry,checkpoints=[],expected_final_a7=a7,
        initial_host_writes=writes,seed=prov,bank={0x200000:2,0x300000:3}[state[0]],preparation=dict(role=role or 'declared fixture %s (entry %x, A7 %x)'%(name,entry,a7)))


def direct_fx(name,ram,regs,prov,host_writes=(),role=''):
    """Direct 1a73c entry exactly as the original full-frame observer: A7 = 1feffc, return LONG ff000, initial bank 2 page."""
    return make_fx(name,ram,regs,BANK2,ENTRY_1A73C,S,prov,host_writes,[(S,RETURN_FF000.to_bytes(4,'big'))],role=role or 'direct 1a73c entry with the seed RAM, 14 seed registers, A5 = 108000, A7 = 1feffc, return LONG ff000, initial PVC bank 2')


def natural_fx(name,ram,regs14,bank,prov,host_writes,external=0):
    """stage-frame seed at 480bc (U1 natural path): A5 = 108000, A7 = 1feffc, return LONG 2ac2 at A7 (fh.make_fixture)."""
    f=fh.make_fixture(name,ram,regs14,bank,prov,host_writes);f['external']=external;f['group']='scene-core'
    f['preparation']=dict(role='stage-frame seed %s at 480bc entry (U1 natural path into 1a73c); A5=108000, A7=1feffc, return LONG 2ac2'%name);return f


# ----------------------------------------------------------------------------------
# Seeds
# ----------------------------------------------------------------------------------
SEED_FILES={}


def pin(path,expect=None):
    data=Path(path).read_bytes();digest=sha(data)
    if expect is not None:assert digest==expect,(str(path),digest)
    SEED_FILES[str(path)]=digest;return data


def scene_inputs(program):
    """The 594 scene_frame_execution input states: (case row, input RAM, 14 registers).  Rebuilt from artifacts/scene_general_initialization (initializer RAM
    of the seed index), the case host writes (sfe.prepare) or, for carried frames, the previous recorded native output; every RAM is checked against the recorded
    input_ram_sha256."""
    obs=json.loads(pin(SCENE_OBS,SCENE_OBS_SHA));seeds=json.loads(pin(SCENE_SEED,SCENE_SEED_SHA))
    assert obs['cases']==obs['completed_cases']==len(obs['results'])==594 and obs['failure'] is None
    folder=SCENE_SEED.parent;out=[];last={}
    for index,row in enumerate(obs['results']):
        case=row['fixture'];assert row['case_index']==index and row['returned']
        if case.get('sequence_position',0)>0:
            prev=obs['results'][index-1];assert prev['fixture'].get('sequence')==case['sequence']
            ram=bytearray(pin(SCENE_OBS.parent/prev['ram_file'],prev['ram_sha256']))
        else:
            seed=seeds['results'][case['seed_index']];ram=bytearray(pin(folder/seed['ram_file'],seed['ram_sha256']))
        sfe.prepare(case,ram);assert sha(ram)==row['input_ram_sha256'] and len(ram)==0x10000,index
        out.append((row,bytes(ram),{k:row['incoming'][k] for k in KEYS14}))
    return obs,out


def stage_frame_inputs(program):
    """Stage-0 cases of artifacts/stage_frame/verification.json whose original trace enters 1a73c, rebuilt from the verifier smoke() seeds / carried native
    outputs / host writes; every RAM checked against input_sha256."""
    ver=json.loads(pin(STAGE_FRAME,STAGE_FRAME_SHA));rows=ver['results'];assert len(rows)==96
    seed_rams={}
    out=[]
    for index,row in enumerate(rows):
        if row['incoming']['stage']!=0:continue
        if not any(b['pc']==ENTRY_1A73C for b in row['boundaries']):continue
        sha_in=row['input_sha256'];ram=None;how=None
        if index>0 and rows[index-1]['ram_sha256']==sha_in:
            ram=pin(STAGE_FRAME.parent/rows[index-1]['ram_file'],sha_in);how='previous recorded native output %s'%rows[index-1]['ram_file']
        else:
            for seed in (0,4,25,34):
                if seed not in seed_rams:seed_rams[seed]=sfe.fixture(ROOT,dict(seed_index=seed))
                base=bytearray(seed_rams[seed][0])
                for w in row['host_writes']:
                    at=w['address']-0x100000;raw=bytes.fromhex(w['hex']);base[at:at+len(raw)]=raw
                if sha(base)==sha_in:ram=bytes(base);how='initializer seed %d + %d recorded host writes'%(seed,len(row['host_writes']));break
        assert ram is not None,(index,row['label'])
        assert sha(ram)==sha_in
        out.append((index,row,ram,how))
    return ver,out


# ----------------------------------------------------------------------------------
# Independent model: a basic-block machine.  Every block below is the transcription of the original instructions between two block leaders (see the
# disassembly of the contract table bytes); a block ends with exactly one control transfer and returns the next PC (calls push the return LONG, RTS pops it,
# so call/return pairing is checked by the live stack exactly as on the CPU).  A PC that is not a block start is a stop (boundary, declared return) or an error.
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
BLK={}
LEADERS=frozenset()


def blk(*pcs):
    def deco(fn):
        for pc in pcs:
            assert pc not in BLK,hex(pc);BLK[pc]=fn
        return fn
    return deco


def sub16(d,s):
    d&=0xffff;s&=0xffff;r=(d-s)&0xffff
    return r,r>>15,1 if r==0 else 0,(((d^s)&(d^r))>>15)&1,1 if d<s else 0      # result, N, Z, V, C


def add16(d,s):
    d&=0xffff;s&=0xffff;r=(d+s)&0xffff
    return r,r>>15,1 if r==0 else 0,(((~(d^s))&(d^r))>>15)&1,1 if d+s>0xffff else 0


def sub32(d,s):
    d&=M32;s&=M32;r=(d-s)&M32
    return r,r>>31,1 if r==0 else 0,(((d^s)&(d^r))>>31)&1,1 if d<s else 0


def add32(d,s):
    d&=M32;s&=M32;r=(d+s)&M32
    return r,r>>31,1 if r==0 else 0,(((~(d^s))&(d^r))>>31)&1,1 if d+s>M32 else 0


def asr(v,n,bits):
    mask=(1<<bits)-1;v&=mask;neg=v>>(bits-1)
    r=v>>n
    if neg:r|=(mask<<(bits-n))&mask
    return r&mask


def lt(n,v):return n!=v                      # BLT / BGE use N^V
def le(n,z,v):return z==1 or n!=v


class U2Machine(fh.Machine):
    def __init__(self,program,bank_state,ram,regs):
        super().__init__(program,bank_state[0],ram,regs,{})
        self.ff8,self.ff9=bank_state[1],bank_state[2];self.ports=[];self.pcpath=[]
    def lead(self,pc):
        assert pc in LEADERS,hex(pc)
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)
    def port(self,address,value):
        """A WORD write to the PVC bank registers (2ffff0 / 2ffff2): bank = (ff8>>8 | ff9<<8) + 100000 from the words before the register side effects."""
        self.ports.append((2,address,value))
        if address==0x2ffff0:self.ff8=value
        elif address==0x2ffff2:self.ff9=value
        else:raise ModelError('port %x'%address)
        self.bank=((self.ff8>>8)|(self.ff9<<8))+0x100000
        self.ff8=(self.ff8&0xfe00)|0xa0;self.ff9&=0x7fff
    def rts(self):return self.pop32()
    def call(self,target,ret):self.push32(ret);return target
    def a(self,off):return self.a5(off)
    def rw(self,off):return self.rd(self.a5(off),2)
    def rl(self,off):return self.rd(self.a5(off),4)
    def ww(self,off,v):self.wr(self.a5(off),2,v)
    def wl(self,off,v):self.wr(self.a5(off),4,v)
    def need_c(self):
        if self.C is None:raise ModelError('unknown carry consumed')
        return self.C


# ---- 1a73c
@blk(0x1a73c)
def b1a73c(M):
    M.ww(-0x7ff0,1);M.port(0x2ffff2,0x2000);M.port(0x2ffff0,0);return M.call(0x1a2b4,0x1a756)
@blk(0x1a756)
def b1a756(M):return 0x1a75e if M.need_c()==0 else 0x1a75a
@blk(0x1a75a)
def b1a75a(M):return M.call(0x1a26a,0x1a75e)
@blk(0x1a75e)
def b1a75e(M):return M.call(0x1a526,0x1a762)
@blk(0x1a762)
def b1a762(M):return M.call(0x19b96,0x1a766)
@blk(0x1a766)
def b1a766(M):return M.call(0x19d08,0x1a76a)
@blk(0x1a76a)
def b1a76a(M):
    M.r['d0']=M.rl(0x53bc);M.r['d1']=M.rl(0x53c0);return M.call(0x19802,0x1a776)
@blk(0x1a776)
def b1a776(M):
    d7=M.r['d7'];M.r['d7']=((d7<<16)|(d7>>16))&M32                                   # SWAP D7
    r,n,z,v,c=sub16(M.r['d7'],M.rw(0x5418));return 0x1a784 if c else 0x1a780          # CMP.W 5418(A5),D7 ; BCS
@blk(0x1a780)
def b1a780(M):M.ww(0x5418,M.r['d7']);return 0x1a784
@blk(0x1a784)
def b1a784(M):return M.call(0x1a3d6,0x1a788)
@blk(0x1a788)
def b1a788(M):return M.call(0x1a7a8,0x1a78c)
@blk(0x1a78c)
def b1a78c(M):return M.call(0x1a442,0x1a790)
@blk(0x1a790)
def b1a790(M):
    M.ww(-0x7ff0,0);M.port(0x2ffff2,0x1000);M.port(0x2ffff0,0);return M.rts()


# ---- 1a2b4 condition
@blk(0x1a2b4)
def b1a2b4(M):
    M.r['a1']=M.rl(0x5422);return 0x1a2cc if M.r['a1']==0 else 0x1a2c0
@blk(0x1a2c0)
def b1a2c0(M):
    a1=M.r['a1'];M.lw('d0',M.rd(a1,2));M.r['a1']=(a1+2)&M32
    target=(0x1a2d4+sx16(M.r['d0']))&M32                                                 # JSR 1a2d4(PC,D0.W): the computed target, no range check
    return M.call(target,0x1a2c6)
@blk(0x1a2c6)
def b1a2c6(M):return 0x1a2d2 if M.need_c()==0 else 0x1a2ca
@blk(0x1a2ca)
def b1a2ca(M):return M.call(0x1a29e,0x1a2cc)
@blk(0x1a2cc)
def b1a2cc(M):M.C=1;return M.rts()
@blk(0x1a2d2)
def b1a2d2(M):return M.rts()
@blk(0x1a2d4)
def b1a2d4(M):return 0x1a2e0
@blk(0x1a2d8)
def b1a2d8(M):return 0x1a334
@blk(0x1a2dc)
def b1a2dc(M):return 0x1a2f2
@blk(0x1a29e)
def b1a29e(M):M.wl(0x5422,0);return M.call(0x197da,0x1a2a6)
@blk(0x1a2a6)
def b1a2a6(M):
    M.ww(0x541e,M.r['d7']);M.ww(0x5420,M.r['d7']);M.ww(0x543e,0);return M.rts()
@blk(0x1a2e0)
def b1a2e0(M):
    a1=M.r['a1'];v=M.rd(a1,2);M.r['a1']=(a1+2)&M32;M.ww(0x543e,v)
    M.lw('d0',M.rw(0x5418));r,n,z,vv,c=sub16(M.r['d0'],M.rw(0x541e));M.C=c^1             # CMP.W 541e(A5),D0 ; EORI #1,CCR
    return M.rts()
@blk(0x1a2f2)
def b1a2f2(M):return 0x1a3a0 if M.rd(M.a5(0x568e),1)==0 else 0x1a2fa
@blk(0x1a2fa)
def b1a2fa(M):M.r['a0']=M.a5(-0x7348);return M.call(0x1a34c,0x1a302)
@blk(0x1a302)
def b1a302(M):return 0x1a314 if M.need_c()==0 else 0x1a306
@blk(0x1a306)
def b1a306(M):M.r['a0']=M.a5(-0x7258);return M.call(0x1a34c,0x1a30e)
@blk(0x1a30e)
def b1a30e(M):return 0x1a314 if M.need_c()==0 else 0x1a312
@blk(0x1a312)
def b1a312(M):return M.rts()
@blk(0x1a314)
def b1a314(M):
    M.r['a1']=(M.r['a1']+8)&M32;M.r['a0']=M.a5(-0x7348);return M.call(0x1a34c,0x1a320)
@blk(0x1a320)
def b1a320(M):return 0x1a332 if M.need_c()==0 else 0x1a324
@blk(0x1a324)
def b1a324(M):M.r['a0']=M.a5(-0x7258);return M.call(0x1a34c,0x1a32c)
@blk(0x1a32c)
def b1a32c(M):return 0x1a332 if M.need_c()==0 else 0x1a330
@blk(0x1a330)
def b1a330(M):return M.rts()
@blk(0x1a332)
def b1a332(M):return M.rts()
@blk(0x1a334)
def b1a334(M):return 0x1a3a0 if M.rd(M.a5(0x568e),1)==0 else 0x1a33c
@blk(0x1a33c)
def b1a33c(M):M.r['a0']=M.a5(-0x7348);return M.call(0x1a34c,0x1a344)
@blk(0x1a344)
def b1a344(M):return 0x1a3a0 if M.need_c()==0 else 0x1a348
@blk(0x1a348)
def b1a348(M):M.r['a0']=M.a5(-0x7258);return 0x1a34c                                  # falls into 1a34c (no push: the RTS returns to the 1a2c6 caller)
@blk(0x1a34c)
def b1a34c(M):return M.call(0x289e,0x1a352)
@blk(0x1a352)
def b1a352(M):return 0x1a35c if M.need_c()==1 else 0x1a356
@blk(0x1a356)
def b1a356(M):M.C=1;return M.rts()
@blk(0x1a35c)
def b1a35c(M):return 0x1a3a0 if M.rd(M.r['a0']+0x15,1)&0x80==0 else 0x1a366
@blk(0x1a366)
def b1a366(M):
    a1=M.r['a1'];d4=M.rd(a1,4);d5=M.rd(a1+4,4)
    M.r['d4']=d4;M.r['d5']=add32(d5,d4)[0]                                               # ADD.L D4,D5: the carry of the low WORD sum propagates into the high WORD
    a0=M.r['a0'];M.lw('d0',M.rd(a0+0x42,2));M.lw('d1',M.rd(a0+0x46,2))
    M.lw('d0',sub16(M.r['d0'],M.rw(0x53a2))[0]);M.lw('d1',sub16(M.r['d1'],M.rw(0x53a6))[0])
    r,n,z,v,c=sub16(M.r['d1'],M.r['d4']);return 0x1a3a0 if n!=v else 0x1a384
@blk(0x1a384)
def b1a384(M):
    r,n,z,v,c=sub16(M.r['d1'],M.r['d5']);return 0x1a3a0 if n==v else 0x1a38a
@blk(0x1a38a)
def b1a38a(M):
    for k in ('d4','d5'):d=M.r[k];M.r[k]=((d<<16)|(d>>16))&M32
    r,n,z,v,c=sub16(M.r['d0'],M.r['d4']);return 0x1a3a0 if n!=v else 0x1a394
@blk(0x1a394)
def b1a394(M):
    r,n,z,v,c=sub16(M.r['d0'],M.r['d5']);return 0x1a3a0 if n==v else 0x1a39a
@blk(0x1a39a)
def b1a39a(M):M.C=1;return M.rts()
@blk(0x1a3a0)
def b1a3a0(M):M.C=0;return M.rts()
@blk(0x289e)
def b289e(M):
    if M.rd(M.r['a0'],4)==0x270e:M.C=0;return 0x28ac
    return 0x28a8
@blk(0x28a8)
def b28a8(M):M.C=1;return 0x28ac
@blk(0x28ac)
def b28ac(M):return M.rts()


# ---- 1a26a script gate
@blk(0x1a26a)
def b1a26a(M):
    M.r['a1']=M.rl(0x5412);return 0x1a278 if M.r['a1'] else 0x1a276
@blk(0x1a276)
def b1a276(M):return M.rts()
@blk(0x1a278)
def b1a278(M):
    M.lw('d0',M.rw(0x5418));r,n,z,v,c=sub16(M.r['d0'],M.rw(0x5416));return 0x1a29c if c else 0x1a284
@blk(0x1a284)
def b1a284(M):return 0x1a28a if M.rd(M.r['a1'],2)&0x8000 else 0x1a292                    # TST.W (A1) ; BPL 1a292
@blk(0x1a28a)
def b1a28a(M):M.ww(0x5416,0xffff);return M.rts()
@blk(0x1a292)
def b1a292(M):return M.call(0x1a0b6,0x1a296)
@blk(0x1a296)
def b1a296(M):M.wl(0x5412,M.r['a1']);return 0x1a278
@blk(0x1a29c)
def b1a29c(M):return M.rts()


# ---- 197da motion record scan / 19802 19832 198ee null paths
@blk(0x197da)
def b197da(M):
    M.r['a1']=M.rl(0x53b4);return 0x197ec if M.r['a1'] else 0x197e6
@blk(0x197e6)
def b197e6(M):M.lw('d7',0x7fff);return M.rts()
@blk(0x197ec)
def b197ec(M):return 0x197fc if M.rd(M.r['a1']+2,2)==0xffff else 0x197f6
@blk(0x197f6)
def b197f6(M):M.r['a1']=(M.r['a1']+sx16(0xa))&M32;return 0x197ec
@blk(0x197fc)
def b197fc(M):M.lw('d7',M.rd(M.r['a1'],2));M.lw('d7',M.r['d7']-1);return M.rts()
@blk(0x19802)
def b19802(M):
    M.r['a1']=M.rl(0x53b4);return 0x19812 if M.r['a1'] else 0x1980e
@blk(0x1980e)
def b1980e(M):M.r['d7']=0;return M.rts()
@blk(0x19832)
def b19832(M):
    M.r['a1']=M.rl(0x53b4);return 0x19844 if M.r['a1'] else 0x1983e
@blk(0x1983e)
def b1983e(M):M.r['d6']=0;M.r['d7']=0;return M.rts()
@blk(0x198ee)
def b198ee(M):
    M.r['a1']=M.rl(0x53b4);return 0x19910 if M.r['a1'] else 0x198fa
@blk(0x198fa)
def b198fa(M):
    M.r['d0']=0;M.r['d1']=0;M.lw('d0',M.rw(0x53b8));M.lw('d1',M.rw(0x53ba))
    for k in ('d0','d1'):d=M.r[k];M.r[k]=((d<<16)|(d>>16))&M32
    M.r['d2']=0;M.r['d3']=0;return M.rts()


# ---- 19978 camera target merge
@blk(0x19978)
def b19978(M):return M.call(0x198ee,0x1997c)
@blk(0x1997c)
def b1997c(M):return 0x1998e if M.r['a1'] else 0x19984                                 # CMPA.W #0,A1 ; BNE
@blk(0x19984)
def b19984(M):M.wl(0x53c4,M.r['d0']);M.wl(0x53c8,M.r['d1']);return M.rts()
@blk(0x1998e)
def b1998e(M):
    M.r['d3']=add32(M.r['d3'],M.r['d1'])[0]                                              # ADD.L D1,D3 (LONG, carries between the WORD halves)
    r,n,z,v,c=sub32(M.r['d3'],M.r['d1']);return 0x19998 if n==0 else 0x19996             # CMP.L D1,D3 ; BPL (N only)
@blk(0x19996)
def b19996(M):M.r['d1'],M.r['d3']=M.r['d3'],M.r['d1'];return 0x19998                      # EXG.L D1,D3
@blk(0x19998)
def b19998(M):
    r,n,z,v,c=sub32(M.r['d1'],M.rl(0x53c8));M.r['d1']=r;return 0x199a4 if n else 0x199a0 # SUB.L 53c8(A5),D1 ; BMI
@blk(0x199a0)
def b199a0(M):M.wl(0x53c8,add32(M.rl(0x53c8),M.r['d1'])[0]);return 0x199a4
@blk(0x199a4)
def b199a4(M):
    r,n,z,v,c=sub32(M.r['d3'],M.rl(0x53c8));M.r['d3']=r;return 0x199b0 if n==0 else 0x199ac # SUB.L 53c8(A5),D3 ; BPL
@blk(0x199ac)
def b199ac(M):M.wl(0x53c8,add32(M.rl(0x53c8),M.r['d3'])[0]);return 0x199b0
@blk(0x199b0)
def b199b0(M):
    M.r['d2']=add32(M.r['d2'],M.r['d0'])[0]
    r,n,z,v,c=sub32(M.r['d2'],M.r['d0']);return 0x199ba if n==0 else 0x199b8
@blk(0x199b8)
def b199b8(M):M.r['d0'],M.r['d2']=M.r['d2'],M.r['d0'];return 0x199ba
@blk(0x199ba)
def b199ba(M):
    r,n,z,v,c=sub32(M.r['d0'],M.rl(0x53c4));M.r['d0']=r;return 0x199c6 if n else 0x199c2
@blk(0x199c2)
def b199c2(M):M.wl(0x53c4,add32(M.rl(0x53c4),M.r['d0'])[0]);return 0x199c6
@blk(0x199c6)
def b199c6(M):
    r,n,z,v,c=sub32(M.r['d2'],M.rl(0x53c4));M.r['d2']=r;return 0x199d2 if n==0 else 0x199ce
@blk(0x199ce)
def b199ce(M):M.wl(0x53c4,add32(M.rl(0x53c4),M.r['d2'])[0]);return 0x199d2
@blk(0x199d2)
def b199d2(M):return M.rts()


# ---- 19a40 / 19ac8 X / Y camera bounds
def make_bounds(base,w0,w1,sub,addo,c0,c1,lim,prev,final):
    """19a40 (X: w0=53ce w1=53d2 sub=53d6 add=53da c0=2c c1=114 lim=53e6, ends with the average against 53de) and 19ac8 (Y, ends by storing 53e2 first)."""
    @blk(base)
    def b0(M):
        M.lw('d0',M.rw(w0));M.lw('d1',M.rw(w1));M.r['d7']=0;M.lw('d7',M.r['d0']);M.lw('d7',add16(M.r['d7'],M.r['d1'])[0])
        M.lw('d7',asr(M.r['d7'],1,16));M.lw('d7',sub16(M.r['d7'],M.rw(sub))[0])
        M.lw('d6',M.r['d7']);M.lw('d5',M.rw(addo));r,n,z,v,c=add16(M.r['d6'],M.r['d5']);M.lw('d6',r)
        return base+0x22 if n else base+0x20                                           # BMI 19a62
    @blk(base+0x20)
    def b20(M):M.r['d6']=0;return base+0x22
    @blk(base+0x22)
    def b22(M):
        r,n,z,v,c=sub16(M.r['d7'],M.r['d5']);M.lw('d7',r);return base+0x2a if n==0 else base+0x28   # BPL 19a6a
    @blk(base+0x28)
    def b28(M):M.r['d7']=0;return base+0x2a
    @blk(base+0x2a)
    def b2a(M):
        M.lw('d7',add16(M.r['d7'],M.r['d6'])[0]);r,n,z,v,c=sub16(M.r['d0'],c0);M.lw('d0',r)
        return base+0x36 if n==0 else base+0x34                                        # BPL 19a76
    @blk(base+0x34)
    def b34(M):M.r['d0']=0;return base+0x36
    @blk(base+0x36)
    def b36(M):
        r,n,z,v,c=sub16(M.r['d7'],M.r['d0']);return base+0x3e if le(n,z,v) else base+0x3c        # CMP.W D0,D7 ; BLE
    @blk(base+0x3c)
    def b3c(M):M.lw('d7',M.r['d0']);return base+0x3e
    @blk(base+0x3e)
    def b3e(M):
        r,n,z,v,c=sub16(M.r['d1'],c1);M.lw('d1',r);return base+0x48 if n else base+0x46          # SUBI.W #114,D1 ; BMI 19a88
    @blk(base+0x46)
    def b46(M):M.r['d1']=0;return base+0x48
    @blk(base+0x48)
    def b48(M):
        r,n,z,v,c=sub16(M.r['d7'],M.r['d1']);return base+0x50 if n==v else base+0x4e              # CMP.W D1,D7 ; BGE
    @blk(base+0x4e)
    def b4e(M):M.lw('d7',M.r['d1']);return base+0x50
    @blk(base+0x50)
    def b50(M):
        d=M.r['d7'];M.r['d7']=((d<<16)|(d>>16))&M32                                    # SWAP D7 ; TST.L D7 ; BMI 19a9a
        return base+0x5a if M.r['d7']>>31 else base+0x58
    @blk(base+0x58)
    def b58(M):M.r['d7']=add32(M.r['d7'],7)[0];return base+0x5a                        # ADDQ.L #7
    @blk(base+0x5a)
    def b5a(M):
        M.r['d7']=asr(M.r['d7'],3,32);M.r['d0']=M.rl(lim)                              # ASR.L #3 ; MOVE.L lim,D0
        r,n,z,v,c=sub32(M.r['d7'],M.r['d0']);return base+0x68 if le(n,z,v) else base+0x66        # CMP.L D0,D7 ; BLE
    @blk(base+0x66)
    def b66(M):M.r['d7']=M.r['d0'];return base+0x68
    @blk(base+0x68)
    def b68(M):
        r,n,z,v,c=add32(M.r['d0'],M.r['d7']);M.r['d0']=r;return base+0x70 if n==v else base+0x6e # ADD.L D7,D0 ; BGE
    @blk(base+0x6e)
    def b6e(M):M.r['d7']=sub32(M.r['d7'],M.r['d0'])[0];return base+0x70                # SUB.L D0,D7
    if final=='x':
        @blk(base+0x70)
        def b70(M):
            r,n,z,v,c=sub32(M.r['d7'],M.rl(prev));M.r['d7']=r;return base+0x7c if n else base+0x7a  # SUB.L 53de(A5),D7 ; TST ; BMI 19abc
        @blk(base+0x7a)
        def b7a(M):M.r['d7']=add32(M.r['d7'],1)[0];return base+0x7c
        @blk(base+0x7c)
        def b7c(M):
            M.r['d7']=asr(M.r['d7'],1,32);M.r['d7']=add32(M.r['d7'],M.rl(prev))[0];M.wl(prev,M.r['d7']);return M.rts()
    else:
        @blk(base+0x70)
        def b70(M):
            M.wl(prev,M.r['d7'])                                                      # MOVE.L D7,53e2(A5) first, then the average against the stored value
            r,n,z,v,c=sub32(M.r['d7'],M.rl(prev));M.r['d7']=r;return base+0x80 if n else base+0x7e
        @blk(base+0x7e)
        def b7e(M):M.r['d7']=add32(M.r['d7'],1)[0];return base+0x80
        @blk(base+0x80)
        def b80(M):
            M.r['d7']=asr(M.r['d7'],1,32);M.r['d7']=add32(M.r['d7'],M.rl(prev))[0];return M.rts()


make_bounds(0x19a40,0x53ce,0x53d2,0x53d6,0x53da,0x2c,0x114,0x53e6,0x53de,'x')
make_bounds(0x19ac8,0x53d0,0x53d4,0x53d8,0x53dc,0x18,0xb8,0x53ea,0x53e2,'y')


# ---- 19b96 camera / bounds / motion merge
@blk(0x19b96)
def b19b96(M):
    M.lw('d4',M.rw(0x53bc));M.lw('d5',M.rw(0x53c0))
    M.lw('d4',add16(M.r['d4'],M.rw(0x53a2))[0]);M.lw('d5',add16(M.r['d5'],M.rw(0x53a6))[0])
    for off,reg in ((0x53ce,'d4'),(0x53d0,'d5'),(0x53d2,'d4'),(0x53d4,'d5')):M.ww(off,sub16(M.rw(off),M.r[reg])[0])   # SUB.W Dn,mem
    return 0x19bda if M.rw(0x53fa)==0 else 0x19bbe
@blk(0x19bbe)
def b19bbe(M):M.r['d0']=M.rl(0x53bc);M.r['d1']=M.rl(0x53c0);return M.call(0x19802,0x19bca)
@blk(0x19bca)
def b19bca(M):
    M.r['d6']=M.r['d7'];M.r['d7']=0;M.lw('d7',M.rw(0x53fa));M.r['d7']=(M.r['d7']<<8)&M32;M.r['d7']=add32(M.r['d7'],M.r['d6'])[0];return 0x19c28
@blk(0x19bda)
def b19bda(M):return 0x19bf0 if M.rd(M.a5(0x53cc),1)&1 else 0x19be4
@blk(0x19be4)
def b19be4(M):M.r['d7']=M.rl(0x53fc);M.wl(0x53de,M.r['d7']);return 0x19bf4
@blk(0x19bf0)
def b19bf0(M):return M.call(0x19a40,0x19bf4)
@blk(0x19bf4)
def b19bf4(M):
    M.r['d7']=add32(M.r['d7'],M.rl(0x53bc))[0];M.wl(0x53c4,M.r['d7'])
    return 0x19c12 if M.rd(M.a5(0x53cc),1)&2 else 0x19c06
@blk(0x19c06)
def b19c06(M):M.r['d7']=M.rl(0x5400);M.wl(0x53e2,M.r['d7']);return 0x19c16
@blk(0x19c12)
def b19c12(M):return M.call(0x19ac8,0x19c16)
@blk(0x19c16)
def b19c16(M):
    M.r['d7']=add32(M.r['d7'],M.rl(0x53c0))[0];M.wl(0x53c8,M.r['d7']);return M.call(0x19832,0x19c22)
@blk(0x19c22)
def b19c22(M):
    r,n,z,v,c=sub32(M.r['d7'],M.r['d6']);return 0x19c44 if c else 0x19c28                  # CMP.L D6,D7 ; BCS
@blk(0x19c28)
def b19c28(M):
    M.r['d5']=0;M.lw('d5',M.rw(0x53ee));d=M.r['d5'];M.r['d5']=((d<<16)|(d>>16))&M32
    r,n,z,v,c=sub32(M.r['d7'],M.r['d5']);return 0x19c40 if c else 0x19c36                  # CMP.L D5,D7 ; BCS 19c40
@blk(0x19c36)
def b19c36(M):
    r,n,z,v,c=sub32(M.r['d6'],M.r['d5']);return 0x19c3e if c else 0x19c3c                  # CMP.L D5,D6 ; BCS 19c3e
@blk(0x19c3c)
def b19c3c(M):M.r['d5']=M.r['d6'];return 0x19c3e
@blk(0x19c3e)
def b19c3e(M):M.r['d7']=M.r['d5'];return 0x19c40
@blk(0x19c40)
def b19c40(M):return 0x19c5c
@blk(0x19c44)
def b19c44(M):
    M.r['d5']=0;M.lw('d5',M.rw(0x53f0));d=M.r['d5'];M.r['d5']=((d<<16)|(d>>16))&M32
    r,n,z,v,c=sub32(M.r['d7'],M.r['d5']);return 0x19c5c if c==0 else 0x19c52                # CMP.L D5,D7 ; BCC 19c5c
@blk(0x19c52)
def b19c52(M):
    r,n,z,v,c=sub32(M.r['d6'],M.r['d5']);return 0x19c5a if c==0 else 0x19c58                # CMP.L D5,D6 ; BCC 19c5a
@blk(0x19c58)
def b19c58(M):M.r['d5']=M.r['d6'];return 0x19c5a
@blk(0x19c5a)
def b19c5a(M):M.r['d7']=M.r['d5'];return 0x19c5c
@blk(0x19c5c)
def b19c5c(M):return M.call(0x19978,0x19c60)
@blk(0x19c60)
def b19c60(M):return 0x19cd6 if M.rw(0x53fa)!=0 else 0x19c68
@blk(0x19c68)
def b19c68(M):return 0x19c72 if M.rd(M.a5(0x53cc),1)&1 else 0x19ca0
@blk(0x19c72)
def b19c72(M):
    M.lw('d1',M.rw(0x53c4));r,n,z,v,c=sub16(M.r['d1'],M.rw(0x53bc));M.lw('d1',r)
    return 0x19ca0 if z else 0x19c7e                                                        # SUB.W 53bc(A5),D1 ; BEQ 19ca0
@blk(0x19c7e)
def b19c7e(M):return 0x19c92 if (M.r['d1']>>15)&1 else 0x19c82                               # BMI on the N of the SUB.W (D1 unchanged since)
@blk(0x19c82)
def b19c82(M):
    M.lw('d0',M.rw(0x53ce));r,n,z,v,c=sub16(M.r['d0'],0x2c);M.lw('d0',r);return 0x19ce6 if n else 0x19c8e
@blk(0x19c8e)
def b19c8e(M):return 0x19ca0
@blk(0x19c92)
def b19c92(M):
    M.lw('d0',M.rw(0x53d2));M.lw('d0',sub16(M.r['d0'],0x114)[0]);r,n,z,v,c=add16(M.r['d0'],M.r['d1']);M.lw('d0',r)
    return 0x19ce6 if n==0 else 0x19ca0                                                     # ADD.W D1,D0 ; BPL 19ce6
@blk(0x19ca0)
def b19ca0(M):return 0x19caa if M.rd(M.a5(0x53cc),1)&2 else 0x19cd6
@blk(0x19caa)
def b19caa(M):
    M.lw('d1',M.rw(0x53c8));r,n,z,v,c=sub16(M.r['d1'],M.rw(0x53c0));M.lw('d1',r)
    return 0x19cd6 if z else 0x19cb6
@blk(0x19cb6)
def b19cb6(M):return 0x19cca if (M.r['d1']>>15)&1 else 0x19cba
@blk(0x19cba)
def b19cba(M):
    M.lw('d0',M.rw(0x53d0));r,n,z,v,c=sub16(M.r['d0'],0x18);M.lw('d0',r);return 0x19ce6 if n else 0x19cc6
@blk(0x19cc6)
def b19cc6(M):return 0x19cd6
@blk(0x19cca)
def b19cca(M):
    M.lw('d0',M.rw(0x53d4));r,n,z,v,c=sub16(M.r['d0'],0xb8);M.lw('d0',r);return 0x19ce6 if n==0 else 0x19cd6
@blk(0x19cd6)
def b19cd6(M):M.wl(0x53bc,M.rl(0x53c4));M.wl(0x53c0,M.rl(0x53c8));return 0x19cee
@blk(0x19ce6)
def b19ce6(M):M.wl(0x53de,0);M.wl(0x53e2,0);return 0x19cee
@blk(0x19cee)
def b19cee(M):
    M.ww(0x53ce,0x7fff);M.ww(0x53d2,0x8000);M.ww(0x53d0,0x7fff);M.ww(0x53d4,0x8000);return M.rts()


# ---- 19d08 / 19d98 object bounding box
@blk(0x19d08)
def b19d08(M):
    M.ww(0x53f2,0x7fff);M.ww(0x53f6,0x7fff);M.ww(0x53f4,0x8000);M.ww(0x53f8,0x8000)
    M.r['d0']=M.rl(0x53bc);M.r['d1']=M.rl(0x53c0);return M.call(0x19802,0x19d2c)
@blk(0x19d2c)
def b19d2c(M):
    d=M.r['d7'];M.r['d7']=((d<<16)|(d>>16))&M32;M.push16(M.r['d7'])                         # SWAP D7 ; MOVE.W D7,-(A7)
    M.lw('d6',M.rw(0x5418));r,n,z,v,c=sub16(M.r['d6'],M.rw(0x53ee));return 0x19d40 if c else 0x19d3c   # CMP.W 53ee(A5),D6 ; BCS
@blk(0x19d3c)
def b19d3c(M):M.lw('d6',M.rw(0x53ee));return 0x19d40
@blk(0x19d40)
def b19d40(M):
    r,n,z,v,c=sub16(M.r['d7'],M.r['d6']);return 0x19d48 if c==0 else 0x19d46                # CMP.W D6,D7 ; BCC
@blk(0x19d46)
def b19d46(M):M.lw('d7',M.r['d6']);return 0x19d48
@blk(0x19d48)
def b19d48(M):return M.call(0x19d98,0x19d4c)
@blk(0x19d4c)
def b19d4c(M):
    M.lw('d7',M.pop16());r,n,z,v,c=sub16(M.r['d7'],M.rw(0x53f0));return 0x19d5a if c else 0x19d56   # MOVE.W (A7)+,D7 ; CMP.W 53f0(A5),D7 ; BCS
@blk(0x19d56)
def b19d56(M):M.lw('d7',M.rw(0x53f0));return 0x19d5a
@blk(0x19d5a)
def b19d5a(M):return M.call(0x19d98,0x19d5e)
@blk(0x19d5e)
def b19d5e(M):
    M.lw('d0',M.rw(0x53a2));M.ww(0x53f2,add16(M.rw(0x53f2),M.r['d0'])[0])
    M.lw('d0',add16(M.r['d0'],0x140)[0]);r,n,z,v,c=add16(M.r['d0'],M.rw(0x53f4));M.lw('d0',r)
    return 0x19d76 if v==0 else 0x19d72                                                      # BVC
@blk(0x19d72)
def b19d72(M):M.lw('d0',0x7fff);return 0x19d76
@blk(0x19d76)
def b19d76(M):
    M.ww(0x53f4,M.r['d0']);M.lw('d1',M.rw(0x53a6));M.ww(0x53f6,add16(M.rw(0x53f6),M.r['d1'])[0])
    M.lw('d1',add16(M.r['d1'],0x100)[0]);r,n,z,v,c=add16(M.r['d1'],M.rw(0x53f8));M.lw('d1',r)
    return 0x19d92 if v==0 else 0x19d8e
@blk(0x19d8e)
def b19d8e(M):M.lw('d1',0x7fff);return 0x19d92
@blk(0x19d92)
def b19d92(M):M.ww(0x53f8,M.r['d1']);return M.rts()
@blk(0x19d98)
def b19d98(M):
    d=M.r['d7'];M.r['d7']=((d<<16)|(d>>16))&M32;M.lw('d7',0);return M.call(0x198ee,0x19da0)
@blk(0x19da0)
def b19da0(M):
    for k in ('d0','d1','d2','d3'):d=M.r[k];M.r[k]=((d<<16)|(d>>16))&M32
    M.lw('d2',add16(M.r['d2'],M.r['d0'])[0]);M.lw('d3',add16(M.r['d3'],M.r['d1'])[0])
    r,n,z,v,c=sub16(M.r['d2'],M.r['d0']);return 0x19db4 if n==v else 0x19db2                  # CMP.W D0,D2 ; BGE
@blk(0x19db2)
def b19db2(M):M.r['d0'],M.r['d2']=M.r['d2'],M.r['d0'];return 0x19db4
@blk(0x19db4)
def b19db4(M):
    r,n,z,v,c=sub16(M.r['d3'],M.r['d1']);return 0x19dbc if n==v else 0x19dba
@blk(0x19dba)
def b19dba(M):M.r['d1'],M.r['d3']=M.r['d3'],M.r['d1'];return 0x19dbc
@blk(0x19dbc)
def b19dbc(M):
    r,n,z,v,c=sub16(M.r['d0'],M.rw(0x53f2));return 0x19dc8 if n==v else 0x19dc4               # CMP.W 53f2(A5),D0 ; BGE
@blk(0x19dc4)
def b19dc4(M):M.ww(0x53f2,M.r['d0']);return 0x19dc8
@blk(0x19dc8)
def b19dc8(M):
    r,n,z,v,c=sub16(M.r['d1'],M.rw(0x53f6));return 0x19dd4 if n==v else 0x19dd0
@blk(0x19dd0)
def b19dd0(M):M.ww(0x53f6,M.r['d1']);return 0x19dd4
@blk(0x19dd4)
def b19dd4(M):
    r,n,z,v,c=sub16(M.r['d2'],M.rw(0x53f4));return 0x19de0 if le(n,z,v) else 0x19ddc           # CMP.W 53f4(A5),D2 ; BLE
@blk(0x19ddc)
def b19ddc(M):M.ww(0x53f4,M.r['d2']);return 0x19de0
@blk(0x19de0)
def b19de0(M):
    r,n,z,v,c=sub16(M.r['d3'],M.rw(0x53f8));return 0x19dec if le(n,z,v) else 0x19de8
@blk(0x19de8)
def b19de8(M):M.ww(0x53f8,M.r['d3']);return 0x19dec
@blk(0x19dec)
def b19dec(M):return M.rts()


# ---- 1a3d6 shake / 1a442 placement gate / 1a526 limits
@blk(0x1a3d6)
def b1a3d6(M):
    d0=M.rl(0x5408);d1=asr(d0,4,32);M.r['d1']=d1;d0=(-d0)&M32;d0=add32(d0,d1)[0];M.wl(0x5408,d0)
    d0=add32(d0,0x8000)[0];M.r['d0']=((d0<<16)|(d0>>16))&M32                                  # ADDI.L #8000 ; SWAP D0
    r,n,z,v,c=sub16(M.r['d0'],8);return 0x1a3f8 if le(n,z,v) else 0x1a3f6                      # CMPI.W #8,D0 ; BLE
@blk(0x1a3f6)
def b1a3f6(M):M.r['d0']=8;return 0x1a3f8
@blk(0x1a3f8)
def b1a3f8(M):
    r,n,z,v,c=sub16(M.r['d0'],0xfff8);return 0x1a402 if n==v else 0x1a400                      # CMPI.W #fff8,D0 ; BGE
@blk(0x1a400)
def b1a400(M):M.r['d0']=0xfffffff8;return 0x1a402
@blk(0x1a402)
def b1a402(M):M.ww(0x5406,M.rw(0x5404));M.ww(0x5404,M.r['d0']);return M.rts()
@blk(0x1a442)
def b1a442(M):
    M.r['a0']=M.rl(0x540e);return 0x1a450 if M.r['a0'] else 0x1a44e
@blk(0x1a44e)
def b1a44e(M):return M.rts()
@blk(0x1a450)
def b1a450(M):
    M.lw('d7',M.rd(M.r['a0'],2));return 0x1a45c if M.r['d7']&0xffff!=0xffff else 0x1a45a
@blk(0x1a45a)
def b1a45a(M):return M.rts()
@blk(0x1a45c)
def b1a45c(M):
    r,n,z,v,c=sub16(M.r['d7'],M.rw(0x5418));return 0x1a466 if (c or z) else 0x1a464           # CMP.W 5418(A5),D7 ; BLS
@blk(0x1a464)
def b1a464(M):return M.rts()
@blk(0x1a466)
def b1a466(M):return M.call(0x1a470,0x1a46a)
@blk(0x1a46a)
def b1a46a(M):M.wl(0x540e,M.r['a0']);return M.rts()
@blk(0x1a526)
def b1a526(M):
    M.lw('d0',M.rw(0x541e));M.lw('d1',M.rw(0x5420));M.lw('d2',M.rw(0x5440))
    r,n,z,v,c=sub16(M.r['d0'],M.r['d2']);return 0x1a53a if c else 0x1a538                       # CMP.W D2,D0 ; BCS
@blk(0x1a538)
def b1a538(M):M.lw('d0',M.r['d2']);return 0x1a53a
@blk(0x1a53a)
def b1a53a(M):
    M.lw('d2',M.rw(0x5442));r,n,z,v,c=sub16(M.r['d1'],M.r['d2']);return 0x1a546 if c else 0x1a544
@blk(0x1a544)
def b1a544(M):M.lw('d1',M.r['d2']);return 0x1a546
@blk(0x1a546)
def b1a546(M):
    M.ww(0x53ee,M.r['d0']);M.ww(0x53f0,M.r['d1']);M.lw('d0',M.rw(0x5444));M.lw('d1',M.rw(0x5448))
    return 0x1a566 if M.r['d0']&0xffff!=0x8000 else 0x1a55e                                     # CMPI.W #8000,D0 ; BNE
@blk(0x1a55e)
def b1a55e(M):M.lw('d0',M.rw(0x5426));M.lw('d1',M.rw(0x542a));return 0x1a566
@blk(0x1a566)
def b1a566(M):
    M.ww(0x53d6,M.r['d0']);M.ww(0x53da,M.r['d1']);M.lw('d0',M.rw(0x5446));M.lw('d1',M.rw(0x544a))
    return 0x1a586 if M.r['d0']&0xffff!=0x8000 else 0x1a57e
@blk(0x1a57e)
def b1a57e(M):M.lw('d0',M.rw(0x5428));M.lw('d1',M.rw(0x542c));return 0x1a586
@blk(0x1a586)
def b1a586(M):
    M.ww(0x53d8,M.r['d0']);M.ww(0x53dc,M.r['d1']);M.lw('d0',M.rw(0x543e))
    r,n,z,v,c=sub16(M.r['d0'],M.rw(0x544c));return 0x1a59e if c==0 else 0x1a59a                 # CMP.W 544c(A5),D0 ; BCC
@blk(0x1a59a)
def b1a59a(M):M.lw('d0',M.rw(0x544c));return 0x1a59e
@blk(0x1a59e)
def b1a59e(M):M.ww(0x53fa,M.r['d0']);return M.rts()


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
# Configuration (observer globals), probe, stop evidence
# ----------------------------------------------------------------------------------
U1_NEEDED=((0x480bc,0x480f2),(0x47642,0x47672))               # the natural entry chain: 480bc -> JSR 47642 (289e twice) -> JSR 1a73c
RANGES=();RANGE_TABLE=[];LEADERS_U1=frozenset();LEADERS_U2=frozenset();BLOCKS=()
POOL=fh.POOL
PROBE_STOP=0x3ffffe                                            # never executed (outside every mapped code range): the probe ends at the first guard


def configure(program,out_dir):
    global RANGES,RANGE_TABLE,LEADERS,LEADERS_U1,LEADERS_U2,BLOCKS,U2_RANGES,KEYS_PCS
    U2_RANGES,RANGE_TABLE=parse_contract_ranges(program)
    RANGES=U1_NEEDED+EXISTING_RANGES+U2_RANGES
    LEADERS_U1=frozenset(fh.leaders_of(program,U1_NEEDED+((0x289e,0x28ae),)))
    LEADERS_U2=frozenset(fh.leaders_of(program,U2_RANGES+EXISTING_RANGES))|frozenset(EXTRA_LEADERS)
    LEADERS=frozenset(LEADERS_U1|LEADERS_U2);BLOCKS=tuple(sorted(LEADERS))
    KEYS_PCS=tuple(sorted(LEADERS|set(BOUNDARIES_U2)))
    fc.OUT=out_dir;fc.RANGES=RANGES;fc.BOUNDARIES=BLOCKS;fc.KEY_PCS=KEYS_PCS
    fh.OUT=out_dir;POOL.clear()
    for lo,hi in U2_RANGES:                                                      # boundary stops are outside the observed ranges
        assert not any(lo<=pc<hi for pc in BOUNDARIES_U2),hex(lo)
    missing=sorted(hex(pc) for pc in LEADERS_U2 if pc not in BLK)
    assert not missing,'model has no block for leaders %s'%missing
    extra=sorted(hex(pc) for pc in BLK if pc not in LEADERS)
    assert not extra,'model has blocks that are not leaders %s'%extra


def u32at(ram,address):return u32(ram,address)


def zero_phase_pc(p):return p['pcs'][0]


def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(outgoing_pc=pc,previous_pc=None,is_step_stop=True,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];ram=p['ram_after'];a7=o['a7'];raw=program[prev:prev+4]
    if pc in BOUNDARY_BSR:
        bsr,ret=BOUNDARY_BSR[pc]
        assert prev==bsr and raw[:2].hex()=='6100' and bsr+2+int.from_bytes(raw[2:4],'big',signed=True)==pc,(p['label'],hex(prev),hex(pc))
        assert u32(ram,a7)==ret,(p['label'],hex(u32(ram,a7)))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=raw.hex(),is_step_stop=True,
            reached_from='BSR.W at %x (bytes %s) pushed the return LONG %x at A7=%x; %x is never executed'%(prev,raw.hex(),ret,a7,pc))
    if pc in BOUNDARY_BNE:
        bne=BOUNDARY_BNE[pc]
        assert prev==bne and raw[:2].hex()=='6600' and bne+2+int.from_bytes(raw[2:4],'big',signed=True)==pc,(p['label'],hex(prev),hex(pc))
        caller=u32(ram,a7);assert caller in BOUNDARY_CALLERS[pc] and o['a1']!=0 and o['a1']==u32(ram,0x10d3b4),(p['label'],hex(caller),hex(o['a1']))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=raw.hex(),is_step_stop=True,caller_return=caller,motion_pointer=o['a1'],
            reached_from='BNE.W taken at %x (bytes %s) after CMPA.W #0,A1 (A1 = LONG 10d3b4 = %x <> 0); the caller return LONG %x is on the stack at A7=%x; %x is never executed'%(prev,raw.hex(),o['a1'],caller,a7,pc))
    assert program[prev:prev+2].hex()=='4e75' and pc==RETURN_FF000 and a7==S+4 and u32(ram,S)==RETURN_FF000,(p['label'],hex(prev),hex(pc),hex(a7))
    return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),is_step_stop=True,reached_from='RTS at %x popped the declared return LONG %x at 1feffc (A7 after = %x): the frame is fully unwound'%(prev,pc,a7))


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


def plan(program,fx,setup=()):
    """Guarded probe: run the declared condition to its first guard and report where it ended.  The first_stop is the first PC outside the observed ranges
    (a boundary of the unit), the a7 delta the live stack depth at that point and the ordered first-hit leaders the split checkpoints."""
    spec=dict(label=fx['label'],group='probe',fixture=fx,steps=[dict(label='probe',changes=list(setup),stop_pc=PROBE_STOP,checkpoints=[],a7=('entry',0))],provenance='probe',guarded=True,guard={})
    try:phases=fc.run_condition(program,spec,True)
    except AssertionError as e:return dict(error=repr(e)[:300],first_stop=None)
    p=phases[-1];g=p['guard'];pcs=p['pcs'];entry=pcs[0]
    order=[];last=pcs[-1]
    for pc in pcs[1:]:
        if pc in LEADERS and pc not in order and pc!=entry and pc!=last:order.append(pc)
    return dict(error=None,guard=g,first_stop=(g or {}).get('target') if (g or {}).get('problem')=='unsupported_code_target' else None,
        a7_delta=(p['outgoing']['a7']-p['incoming']['a7'])&M32,instructions=len(pcs)-1,checkpoints=order,last_pc=last,incoming_a7=p['incoming']['a7'],outgoing_a7=p['outgoing']['a7'],
        leader_hits=dict(collections.Counter(pc for pc in pcs[:-1] if pc in LEADERS)))


def a7_delta_signed(v):return v-(1<<32) if v&0x80000000 else v


# ----------------------------------------------------------------------------------
# Model comparison
# ----------------------------------------------------------------------------------
def run_model(program,fx,control,stop):
    p=control[0];assert len(control)==1
    M=U2Machine(program,fx['bank_state'],p['ram_before'],p['incoming'])
    entry=p['incoming']['pc']
    if entry==0x480bc:
        M.lead(0x480bc);fh.jsr(M,fh.m47642,0x480c0);M.push32(0x480c6);pc=ENTRY_1A73C
    else:pc=entry
    final=run_blocks(M,pc,stop)
    M.r['pc']=final
    return M


def check_model(program,spec,control):
    fx=spec['fixture'];stop=spec['steps'][-1]['stop_pc'];row=dict(label=spec['label'],kind='scene-core-model')
    try:M=run_model(program,fx,control,stop)
    except (ModelError,fh.ModelError,fh.StopAt,KeyError,AssertionError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=spec['label'],kind='model-could-not-follow-native',detail=repr(e)));return row
    p=control[0];o=p['outgoing'];bad=[]
    nb=p['boundaries']
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
    ports=[(e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write']
    if M.ports!=ports:bad.append(dict(what='ordered port writes',model=M.ports,native=ports))
    reads=[(e['address'],e['size'],e['region']) for e in p['events'] if e['region'] in ('fixed','bank') and e['access']=='read']
    if M.rom_reads!=reads:bad.append(dict(what='ordered fixed/bank reads',model=M.rom_reads[:6],native=reads[:6],model_count=len(M.rom_reads),native_count=len(reads)))
    final=dict(M.r)
    if final!={k:o[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(o[k])) for k in final if final[k]!=o[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if M.bank!=p['modeled_bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(p['modeled_bank'])))
    row.update(equal=not bad,leaders=len(M.leads),leader_pcs_distinct=len({m['pc'] for m in M.leads}),ordered_ram_writes=len(M.writes),ordered_port_writes=len(M.ports),ordered_rom_reads=len(M.rom_reads),
        ram_bytes_compared=0x10000,final_registers_compared=sorted(final),model_leader_pcs=sorted({hex(m['pc']) for m in M.leads}),final_bank=hex(M.bank),mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=spec['label'],kind='model-vs-native',mismatches=bad[:4]))
    return row


# ----------------------------------------------------------------------------------
# Condition builder
# ----------------------------------------------------------------------------------
class Builder:
    def __init__(self,program):
        self.program=program;self.specs=[];self.models=[];self.censuses={}
    def add(self,label,group,prov,fx,setup=(),stop=None,model=True,guard=None,expect=None):
        """stop=None: observe to the first boundary the guarded probe finds (the probe result is recorded as the census entry of the condition and must be a
        declared boundary or an RTS-free boundary stop).  stop=PC with guard: a declared-bad stop, the real run must end in that guard."""
        fx=dict(fx);fx['label']=label
        info=plan(self.program,fx,setup);self.censuses[label]=dict(first_stop=hex(info['first_stop']) if info['first_stop'] else None,error=info['error'],guard=info.get('guard'),
            instructions=info.get('instructions'),a7_delta=a7_delta_signed(info['a7_delta']) if info.get('a7_delta') is not None else None,leaders=set((info.get('leader_hits') or {})))
        if guard is None:
            assert info['error'] is None and info['first_stop'] is not None,(label,info)
            if stop is None:stop=info['first_stop']
            assert expect is None or stop==expect,(label,hex(stop),hex(expect))
            if info['first_stop']==stop:delta=a7_delta_signed(info['a7_delta'])
            else:delta=0                                                                      # declared stop that is not the first boundary: the real run must then fail
        else:
            assert stop is not None;delta=0
        cps=list(info['checkpoints']) if info.get('checkpoints') is not None else []
        if stop==fx['entry_pc']:cps=[];delta=0                                                  # zero-step: the stop PC is the entry PC, nothing runs
        steps=[dict(label=label,changes=list(setup),stop_pc=stop,checkpoints=cps,a7=('entry',delta))]
        extra=dict(guarded=True,guard=guard) if guard is not None else {}
        spec=dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,**extra)
        self.specs.append(spec)
        if model and guard is None:self.models.append(label)
        return spec


# ----------------------------------------------------------------------------------
# stage_entry_body seeds: the original 47a94 body re-executed by the original observer up to the JSR 1a73c (480c0); RAM / registers there are the declared fixture
# ----------------------------------------------------------------------------------
BANK3_ENTRY=((0x300000,0xa0,0x2000),fh.pvc_page(3))


class EntryCapture:
    def __init__(self,program):
        self.program=program;self.obs=seb.Observer(program)
        def stopper(cpu,address,size,user):cpu.emu_stop()
        self.obs.cpu.hook_add(UC_HOOK_CODE,stopper,begin=ENTRY_1A73C,end=ENTRY_1A73C)
    def capture(self,case):
        ram,state,meta=seb.prepare_case(ROOT,self.program,case);o=self.obs;o.prepare(ram,state)
        cpu=o.cpu;o.external,o.wait_visits,o.error=0,0,None
        for values in (o.pcs,o.writes,o.ports,o.reads,o.bank_reads,o.boundaries,o.prefix):values.clear()
        cpu.emu_start(cpu.reg_read(seb.m.UC_M68K_REG_PC),0xffffff,count=2000000)
        pc=cpu.reg_read(seb.m.UC_M68K_REG_PC);a7=cpu.reg_read(seb.m.UC_M68K_REG_A7)
        assert o.error is None and pc==ENTRY_1A73C and o.pcs[-1]==ENTRY_1A73C and o.pcs[-2]==0x480c0,(case,o.error,hex(pc))
        assert a7==seb.STACK-4 and int.from_bytes(cpu.mem_read(a7,4),'big')==0x480c6 and int.from_bytes(cpu.mem_read(seb.STACK,4),'big')==seb.RETURN
        assert cpu.reg_read(seb.m.UC_M68K_REG_A5)==A5V
        regs={k:cpu.reg_read(r)&M32 for k,r in zip(seb.KEYS,seb.REGS)}
        image=bytes(cpu.mem_read(seb.BASE,0x10000))
        return dict(ram=image,regs=regs,bank=o.bank,ports=list(o.ports),instructions=len(o.pcs),input_ram_sha256=sha(ram),ram_sha256=sha(image),host_writes=len(meta['host_writes']))


def stage_entry_inputs(program):
    obs=json.loads(pin(STAGE_ENTRY,STAGE_ENTRY_SHA));rows=obs['results'];assert len(rows)==142 and obs['failure'] is None
    cap=EntryCapture(program);out=[]
    for row in rows:
        c=cap.capture(row['fixture']);c['case_index']=row['case_index'];c['family']=row['fixture']['family'];c['fixture']=row['fixture']
        # the recorded original begin phase must start from the very same RAM
        assert c['input_ram_sha256']==row['phases'][0]['input_ram_sha256'],row['case_index']
        out.append(c)
    return obs,out


def entry_fx(name,c,prov):
    bank=BANK2 if c['bank']==2 else BANK3_ENTRY
    return make_fx(name,c['ram'],c['regs'],bank,ENTRY_1A73C,S-4,prov,(),[(S,RETURN_FF000.to_bytes(4,'big')),(S-4,(0x480c6).to_bytes(4,'big'))],
        role='declared 1a73c entry state captured from the original 47a94 body run (A7 = 1feff8 with the JSR return LONG 480c6, return LONG ff000 at 1feffc)')


# ----------------------------------------------------------------------------------
# Re-entry states captured from the original full-frame observer (scene_frame_execution.Observer): the first (or second) time the original run executes
# the target PC, the 64KiB RAM, the 14 registers, A7 and the live stack bytes up to the return LONG at 1feffc are taken as a declared fixture.
# ----------------------------------------------------------------------------------
REENTRY_PCS=(0x1a78c,0x1a296,0x19bca,0x19d2c,0x1a776,0x1997c,0x19da0,0x19c22,0x1a46a)


class ReentryCapture:
    def __init__(self,program):
        self.program=program;self.obs=sfe.Observer(program);self.hits=collections.Counter();self.want={};self.taken={};self.small={};self.motion=collections.defaultdict(list)
        for pc in REENTRY_PCS:self.obs.cpu.hook_add(UC_HOOK_CODE,self.hit,begin=pc,end=pc)
    def hit(self,cpu,address,size,user):
        self.hits[address]+=1;n=self.hits[address]
        self.motion[address].append(int.from_bytes(cpu.mem_read(0x10d3b4,4),'big')!=0)       # is the motion pointer (LONG 10d3b4) non-null at this hit
        if address==0x1a78c:                                                           # cheap facts for the 1a442 gate classes
            ptr=int.from_bytes(cpu.mem_read(0x10d40e,4),'big');first=int.from_bytes(cpu.mem_read(ptr,2),'big') if ptr and ptr<0x100000 else None
            self.small['gate']=dict(ptr=ptr,first_word=first,phase=int.from_bytes(cpu.mem_read(0x10d418,2),'big'))
        if (address,n) in self.want:
            c=cpu;a7=c.reg_read(sfe.m.UC_M68K_REG_A7)
            self.taken[(address,n)]=dict(pc=address,hit=n,ram=bytes(c.mem_read(sfe.BASE,0x10000)),regs={k:c.reg_read(r)&M32 for k,r in zip(sfe.KEYS,sfe.REGS)},a7=a7,
                stack=bytes(c.mem_read(a7,sfe.STACK+4-a7)),bank=self.obs.bank,ports=len(self.obs.ports))
    def run(self,ram,regs,want=()):
        self.hits.clear();self.motion.clear();self.want={w:1 for w in want};self.taken={};self.small={}
        output,result,ports,info=self.obs.run(ram,[regs[k] for k in KEYS14])
        return output,result,info


def reentry_survey(program,inputs):
    """Pass 1: per scene case which re-entry PCs the original full-frame run executes (hit counts) and the 1a442 gate facts."""
    cap=ReentryCapture(program);survey=[]
    for index,(row,ram,regs) in enumerate(inputs):
        output,result,info=cap.run(ram,regs)
        assert info['returned'] and info['error'] is None and sha(output)==row['ram_sha256'],index                     # the original run reproduces the recorded output
        survey.append(dict(case=index,hits={hex(pc):cap.hits[pc] for pc in REENTRY_PCS if cap.hits[pc]},nonnull={hex(pc):list(cap.motion[pc]) for pc in REENTRY_PCS if cap.motion[pc]},gate=dict(cap.small.get('gate',{})),calls=dict(info['calls'])))
    return survey


def reentry_states(program,inputs,wanted):
    """Pass 2: take the declared states.  wanted: [(case index, pc, hit number)]."""
    cap=ReentryCapture(program);out={};by_case=collections.defaultdict(list)
    for case,pc,hit in wanted:by_case[case].append((pc,hit))
    for case in sorted(by_case):
        row,ram,regs=inputs[case];cap.run(ram,regs,by_case[case])
        for key in by_case[case]:
            assert key in cap.taken,(case,key);out[(case,)+key]=cap.taken[key]
    return out


def reentry_fx(name,state,prov):
    st=state['stack'];a7=state['a7']
    fx=make_fx(name,state['ram'],state['regs'],BANK3_MID,state['pc'],a7,prov,(),[(a7,st)],
        role='declared re-entry at %x (hit %d) from the original full-frame run: RAM, 14 registers, A7 = %x and the %d live stack bytes up to the return LONG; PVC bank 3 as after 1a742/1a74a'%(state['pc'],state['hit'],a7,len(st)))
    return fx


# ----------------------------------------------------------------------------------
# Sampling helpers (deterministic)
# ----------------------------------------------------------------------------------
def spread(items,k):
    items=list(items)
    if k>=len(items):return items
    if k<=1:return items[:k]
    return [items[round(i*(len(items)-1)/(k-1))] for i in range(k)]


def stratified(items,key,k):
    """k items: one from the middle of every group first (families are all represented), the rest evenly spread over the remaining items."""
    items=list(items);groups=collections.OrderedDict()
    for it in items:groups.setdefault(key(it),[]).append(it)
    chosen=[g[len(g)//2] for g in groups.values()]
    rest=[it for it in items if it not in chosen]
    chosen+=spread(rest,max(0,k-len(chosen)))
    return sorted(chosen,key=items.index)


def hit_counts(pcs):
    c=collections.Counter(pc for pc in pcs if pc in LEADERS);return c


# ----------------------------------------------------------------------------------
# Census: the guarded probe of every available seed (first boundary the original code reaches)
# ----------------------------------------------------------------------------------
def census_entry(info):
    return dict(first_stop=hex(info['first_stop']) if info['first_stop'] else None,error=info['error'],guard=info.get('guard'),instructions=info.get('instructions'),
        a7_delta=a7_delta_signed(info['a7_delta']) if info.get('a7_delta') is not None else None,leaders=sorted(hex(pc) for pc in (info.get('leader_hits') or {})),
        leader_hits={hex(pc):n for pc,n in sorted((info.get('leader_hits') or {}).items()) if n>1})


def build_census(program,scene_in,stage_in,entry_in):
    cen=dict(scene_frame=[],stage_frame=[],stage_entry=[])
    for i,(row,ram,regs) in enumerate(scene_in):
        info=plan(program,direct_fx('scene-%04d'%i,ram,regs,{}))
        cen['scene_frame'].append(dict(case=i,family=row['fixture']['family'],**census_entry(info)))
    for index,row,ram,how in stage_in:
        info=plan(program,stage_natural_fx('stage-%02d'%index,row,ram,how))
        cen['stage_frame'].append(dict(case=index,label=row['label'],**census_entry(info)))
    for c in entry_in:
        info=plan(program,entry_fx('entry-%03d'%c['case_index'],c,{}))
        cen['stage_entry'].append(dict(case=c['case_index'],family=c['family'],**census_entry(info)))
    return cen


def stage_natural_fx(name,row,ram,how):
    inc=row['incoming'];regs=[inc[k] for k in KEYS14];bank=inc['bank'];assert bank in (2,3)
    hw=[dict(address=w['address'],size=len(w['hex'])//2,value=int(w['hex'],16),previous=w['previous'],why='recorded host write of the stage-frame verifier case %s'%row['label']) for w in row['host_writes']]
    prov=dict(kind='stage-frame verifier case',verification_label=row['label'],input_sha256=row['input_sha256'],input_rebuilt_from=how,bank=bank,registers=[hex(x) for x in regs],verification_file=str(STAGE_FRAME),verification_sha256=STAGE_FRAME_SHA)
    return natural_fx(name,ram,regs,bank,prov,hw,row['external'])


def scene_prov(i,row,ram):
    return dict(kind='scene_frame_execution case',case=i,family=row['fixture']['family'],sequence=row['fixture'].get('sequence'),sequence_position=row['fixture'].get('sequence_position'),seed_index=row['fixture'].get('seed_index'),
        input_ram_sha256=sha(ram),recorded_input_ram_sha256=row['input_ram_sha256'],original_instructions=row['instructions'],original_calls=row['calls'],observation_sha256=SCENE_OBS_SHA,initializer_observation_sha256=SCENE_SEED_SHA)


def natural_conditions(B,scene_in,stage_in,entry_in,cen,counts):
    first={i:c['first_stop'] for i,c in enumerate(cen['scene_frame'])}
    by_stop=collections.defaultdict(list)
    for i,f in first.items():by_stop[f].append(i)
    fam=lambda i:(scene_in[i][0]['fixture']['family'],scene_in[i][0]['fixture'].get('sequence'))
    chosen=dict(full=by_stop['0x1a7a8'],g1a0b6=by_stop['0x1a0b6'],g19812=stratified(by_stop['0x19812'],fam,counts['19812']),g19844=stratified(by_stop['0x19844'],fam,counts['19844']))
    for i,(row,ram,regs) in enumerate(scene_in):
        if row['fixture']['family'] not in ('canonical-post-initialization-frame','actual-cli-carried-frames'):
            key={'0x1a7a8':'full','0x1a0b6':'g1a0b6','0x19812':'g19812','0x19844':'g19844'}[first[i]]
            if i not in chosen[key]:chosen[key].append(i)
    names=dict(full=('0x1a7a8','natural-scene-full-path'),g1a0b6=('0x1a0b6','natural-scene-script-gate'),g19812=('0x19812','natural-scene-motion-19812'),g19844=('0x19844','natural-scene-motion-19844'))
    for key in ('full','g1a0b6','g19812','g19844'):
        stop,group=names[key]
        for i in chosen[key]:
            row,ram,regs=scene_in[i]
            fx=direct_fx('scene-%04d'%i,ram,regs,scene_prov(i,row,ram))
            B.add('%s-%04d'%(group,i),group,'scene_frame_execution case %d (%s): direct 1a73c entry on the rebuilt seed, first boundary %s'%(i,row['fixture']['family'],stop),fx,expect=int(stop,16))
    for index,row,ram,how in stage_in:
        fx=stage_natural_fx('stage-%02d'%index,row,ram,how)
        B.add('natural-stage-frame-%02d'%index,'natural-stage-frame','stage_frame verification case %d %s: natural 480bc -> JSR 47642 -> JSR 1a73c -> U2 to the first boundary'%(index,row['label']),fx,expect=0x19844)
    by_entry=collections.defaultdict(list)
    for k,c in enumerate(cen['stage_entry']):by_entry[c['first_stop']].append(k)
    pick=by_entry['0x1a7a8']+stratified(by_entry['0x19844'],lambda k:entry_in[k]['family'],counts['entry19844'])
    for k in pick:
        c=entry_in[k];stop=cen['stage_entry'][k]['first_stop']
        prov=dict(kind='stage_entry_body case',case=c['case_index'],family=c['family'],fixture=c['fixture'],input_ram_sha256=c['input_ram_sha256'],ram_at_1a73c_sha256=c['ram_sha256'],ports_before_1a73c=len(c['ports']),
            instructions_to_1a73c=c['instructions'],observation_sha256=STAGE_ENTRY_SHA)
        B.add('natural-stage-entry-%03d'%c['case_index'],'natural-stage-entry','stage_entry_body case %d (%s): 1a73c entry state of the original 47a94 body run, first boundary %s'%(c['case_index'],c['family'],stop),
            entry_fx('entry-%03d'%c['case_index'],c,prov),expect=int(stop,16))


# ----------------------------------------------------------------------------------
# Report helpers
# ----------------------------------------------------------------------------------
CALLED_PCS=(0x1a2b4,0x1a29e,0x1a26a,0x1a526,0x19b96,0x19a40,0x19ac8,0x19d08,0x19d98,0x19802,0x19832,0x198ee,0x19978,0x197da,0x1a3d6,0x1a442,0x1a2e0,0x1a334,0x1a2f2,0x1a34c,0x289e,0x1a278,0x1a28a,0x197e6,0x19cd6,0x19ce6)


EVIDENCE={}
SCENE_ROWS=[]


def ub(ram,addr,n):return int.from_bytes(bytes(ram[(addr+k)&0xffff] for k in range(n)),'big')


def snapshot_fields(ram,d7):
    return dict(phase=ub(ram,0xd418,2),condition=ub(ram,0xd422,4),script=ub(ram,0xd412,4),script_wait=ub(ram,0xd416,2),force=ub(ram,0xd3fa,2),fixed_delta=[ub(ram,0xd3fc,4),ub(ram,0xd400,4)],camera_flags=ub(ram,0xd3cc,1),
        motion=ub(ram,0xd3b4,4),placement=ub(ram,0xd40e,4),camera=[ub(ram,0xd3bc,4),ub(ram,0xd3c0,4)],paths=[ub(ram,at,4) for at in (0xd356,0xd364,0xd372,0xd380)],shake=ub(ram,0xd404,2),shake_amplitude=ub(ram,0xd408,4),d7=d7)


def collect_evidence(spec,split,control):
    label=spec['label'];p=control[0];pcs=p['pcs'];lead=collections.Counter(pc for pc in pcs if pc in LEADERS)
    ev=dict(group=spec['group'],first_stop=hex(p['outgoing']['pc']) if p['guard'] is None else None,leaders=sorted(hex(pc) for pc in lead),instructions=len(pcs)-1)
    if p['guard'] is None:
        ev['stop_evidence']=p['stop_evidence']
        if label.startswith('natural-scene-full-path-'):
            i=int(label.split('-')[-1]);row=SCENE_ROWS[i][0];snaps={b['pc']:b for b in row['boundaries']}
            native=snapshot_fields(p['ram_after'],p['outgoing']['d7']);original=snaps[0x1a788]
            diff={k:(native[k],original[k]) for k in native if native[k]!=original[k]}
            ev['original_1a788_snapshot']=dict(equal=not diff,compared_fields=sorted(native),differences=diff)
            if diff:DISCREPANCIES.append(dict(label=label,kind='original-full-frame-snapshot-at-1a788-differs',detail=diff))
        if 0x19ab0 in lead:
            b=[x for x in p['boundaries'] if x['pc']==0x19ab0][0];prev=ub(p['ram_before'],0xd3de,4)
            res=[int(e['bytes'],16) for e in p['events'] if e['region']=='ram' and e['access']=='write' and e['pc']==0x19ac2][0]
            diff=sx32((b['registers']['d7']-prev)&M32);ev['x_average']=dict(d7_before_sub=b['registers']['d7'],previous_53de=prev,difference=diff,result=res,result_minus_previous=sx32((res-prev)&M32))
        if 0x19b38 in lead:
            b=[x for x in p['boundaries'] if x['pc']==0x19b38][0]
            ev['y_store_first']=dict(d7_at_19b38=b['registers']['d7'],ram_53e2_after=ub(p['ram_after'],0xd3e2,4),later_clear=0x19ce6 in lead)
        if 0x19d72 in lead:ev['bvc_x']=dict(written_53f4=ub(p['ram_after'],0xd3f4,2))
        if 0x19d8e in lead:ev['bvc_y']=dict(written_53f8=ub(p['ram_after'],0xd3f8,2))
        if 0x1a3d6 in lead:ev['shake']=dict(amplitude_before=ub(p['ram_before'],0xd408,4),amplitude_after=ub(p['ram_after'],0xd408,4),word_5404=ub(p['ram_after'],0xd404,2),word_5406=ub(p['ram_after'],0xd406,2),clamp_hi=0x1a3f6 in lead,clamp_lo=0x1a400 in lead)
    EVIDENCE[label]=ev


def condition_summary(spec,split,control):
    c=control[-1];pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    called={hex(pc):pcs.count(pc) for pc in CALLED_PCS if pc in pcs}
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),
        called=called,ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_reads=[dict(pc=hex(e['pc']),address=hex(e['address']),size=e['size'],bank=hex(e['bank_at_read']),physical=hex(e['physical_rom_offset'])) for e in ev if e['region']=='bank'][:16],
        bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),external_reads=sum(1 for e in ev if e['region']=='external'),
        ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=fh.ordered_ports_sha(ev),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'])


def reentry_wanted(survey):
    """Deterministic selection of the declared re-entry states: (case, pc, hit number, label tag)."""
    w=[];gate=collections.defaultdict(list)
    for x in survey:
        g=x['gate']
        if not g:continue
        k='null' if not g['ptr'] else ('ffff' if g['first_word']==0xffff else ('call' if '0x1a470' in x['calls'] else 'nocall'))
        gate[k].append(x['case'])
    for k,n in (('null',3),('ffff',3),('nocall',3),('call',6)):
        for c in spread(gate[k],n):w.append((c,0x1a78c,1,'gate-'+k))
    g1a296=[x for x in survey if '0x1a296' in x['hits']]
    for x in g1a296:w.append((x['case'],0x1a296,1,'script-loop-first'))
    later=[x for x in g1a296 if x['hits']['0x1a296']>=3]
    for x in spread(later,4):w.append((x['case'],0x1a296,2,'script-loop-second'))
    for x in spread(later,4):w.append((x['case'],0x1a296,x['hits']['0x1a296'],'script-loop-last'))
    for c in spread(gate['call'],3):w.append((c,0x1a46a,1,'after-1a470'))
    for pc,hit,n in ((0x19bca,1,10),(0x19c22,1,10),(0x19d2c,1,8),(0x1a776,1,8),(0x1997c,1,10),(0x19da0,1,8),(0x19da0,2,8)):
        cand=[x['case'] for x in survey if hex(pc) in x['nonnull'] and len(x['nonnull'][hex(pc)])>=hit and x['nonnull'][hex(pc)][hit-1]]
        for c in spread(cand,n):w.append((c,pc,hit,'nonnull-motion'))
    return w


def reentry_conditions(B,program,scene_in,survey):
    wanted=reentry_wanted(survey);states=reentry_states(program,scene_in,[(c,pc,hit) for c,pc,hit,tag in wanted])
    out=[]
    for c,pc,hit,tag in wanted:
        st=states[(c,pc,hit)];row=scene_in[c][0]
        prov=dict(kind='declared re-entry from the original full-frame run',case=c,family=row['fixture']['family'],pc=hex(pc),hit=hit,tag=tag,ram_sha256=sha(st['ram']),a7=hex(st['a7']),stack_hex=st['stack'].hex(),
            registers={k:hex(v) for k,v in st['regs'].items()},scene_input_ram_sha256=row_sha(scene_in[c]),observation_sha256=SCENE_OBS_SHA)
        label='reentry-%x-hit%d-case%04d'%(pc,hit,c)
        fx=reentry_fx(label,st,prov)
        B.add(label,'reentry-%x'%pc,'declared re-entry at %x (hit %d, %s) captured from the original full-frame run of scene case %d'%(pc,hit,tag,c),fx)
        out.append(label)
    return out


import random


def writes_of(d):
    """{address: (size, value)} -> declared RAM writes."""
    return [W(a,sz,v,'declared host RAM write %x (%d bytes) = %x'%(a,sz,v&((1<<(8*sz))-1))) for a,(sz,v) in sorted(d.items())]


def model_run(program,fx,setup=(),regs=None):
    ram=bytearray(fx['ram'])
    for c in setup:
        a=c['address'];ram[a&0xffff:(a&0xffff)+c['size']]=c['value'].to_bytes(c['size'],'big')
    r=dict(fx['regs'])
    if regs:r.update(regs)
    r['a7']=fx['initial_a7'];r['pc']=fx['entry_pc']
    M=U2Machine(program,fx['bank_state'],ram,r)
    try:final=run_blocks(M,fx['entry_pc'],None)
    except (ModelError,KeyError,AssertionError):return None
    return M,final


def model_cover(program,fx,setup=(),regs=None):
    """Instruction-faithful model only (no native run): the set of leaders and the final PC.  Used to choose declared fixtures that reach block starts no seed reaches;
    the native run (and the model comparison) of every chosen fixture is done afterwards."""
    r=model_run(program,fx,setup,regs)
    if r is None:return None
    M,final=r;return set(m['pc'] for m in M.leads),final


P0,P1=0x100cb8,0x100da8
REC=0x10e400
REC2=0x10e500
POOL_W=(0,1,2,3,7,8,0x10,0x30,0x7f,0x80,0x100,0x1ff,0x2c,0x114,0x18,0xb8,0x7ffe,0x7fff,0x8000,0x8001,0xfff0,0xffff,0xff00,0xff80,0xfe00,0x4000,0xc000,0x0140,0x0100)


def rect_words(xmin,ymin,w,h):return xmin<<16|ymin,w<<16|h


def rect_record(index,rects):
    raw=index.to_bytes(2,'big')
    for r in rects:
        a,b=rect_words(*r);raw+=a.to_bytes(4,'big')+b.to_bytes(4,'big')
    return raw


def put_bytes(base,raw):
    """Declared RAM bytes as WORD/BYTE writes."""
    out={}
    assert len(raw)%2==0
    for k in range(0,len(raw),2):out[base+k]=(2,int.from_bytes(raw[k:k+2],'big'))
    return out


def player_state(p,mode,rect,off=(0,0x100)):
    """RAM for one player object: callback LONG (270e = marker), bit 7 of byte 15, WORDs 42/46 relative to the rect (A0 + 42 / A0 + 46 minus 53a2 / 53a6 = off)."""
    base=P0 if p==0 else P1;xmin,ymin,w,h=rect;d={}
    def xy(x,y):d[base+0x42]=(2,(x+off[0])&0xffff);d[base+0x46]=(2,(y+off[1])&0xffff)
    ymax=(ymin+h)&0xffff;xmax=(xmin+w+((ymin+h)>>16))&0xffff
    cx,cy=(xmin+w//2)&0xffff,(ymin+h//2)&0xffff
    if mode=='marker':d[base]=(4,0x270e)
    else:
        d[base]=(4,0x1234+p);d[base+0x15]=(1,0x00 if mode=='inactive' else 0x80 if True else 0)
        if mode=='inactive':xy(cx,cy)
        elif mode=='in':xy(cx,cy)
        elif mode=='x-lo-in':xy(xmin,cy)
        elif mode=='x-hi-out':xy(xmax,cy)
        elif mode=='x-below':xy((xmin-1)&0xffff,cy)
        elif mode=='x-above':xy((xmax+5)&0xffff,cy)
        elif mode=='y-lo-in':xy(cx,ymin)
        elif mode=='y-hi-out':xy(cx,ymax)
        elif mode=='y-below':xy(cx,(ymin-1)&0xffff)
        elif mode=='y-above':xy(cx,(ymax+5)&0xffff)
        else:raise AssertionError(mode)
    return d


def condition_fixtures(B,scene_in):
    base182=scene_in[182];base36=scene_in[36]
    def fx_of(i):
        row,ram,regs=scene_in[i];return direct_fx('scene-%04d-fixture'%i,ram,regs,scene_prov(i,row,ram),role='direct 1a73c entry on the rebuilt scene seed %d; the condition fixture is declared as step RAM writes'%i)
    fx182=fx_of(182);fx36=fx_of(36)
    def add(label,group,desc,d,fx=None,**kw):
        B.add(label,group,desc,fx or fx182,setup=writes_of(d),**kw)
    rect=(0x20,0x30,0x40,0x40)
    # index 0 / c (WORD compare) -------------------------------------------------------------
    for idx,name in ((0,'0'),(0xc,'c')):
        for tag,e41,ph in (('clear',0x7fff,0),('set',0,0),('equal',0x1234,0x1234),('set-high',0xffff,0xffff),('clear-by-one',0x0001,0),('set-by-one',0x0001,2)):
            d={0x10d422:(4,REC)};d.update(put_bytes(REC,idx.to_bytes(2,'big')+(0x0042).to_bytes(2,'big')));d[0x10d41e]=(2,e41);d[0x10d418]=(2,ph)
            add('cond-index-%s-%s'%(name,tag),'fixture-condition','condition record at 10d422 with index WORD %x: C = (phase >= WORD 10d41e); phase %x, 10d41e %x'%(idx,ph,e41),d)
    # out-of-range index: the JSR target is the computed 1a2d4+sext(index)
    d={0x10d422:(4,REC)};d.update(put_bytes(REC,(0x40).to_bytes(2,'big')+rect_record(0,[rect,rect])[2:]));d[0x10d68e]=(1,0);
    add('cond-index-0040-lands-in-1a2f2-block-start-1a314','fixture-condition','index 0040: the JSR lands on 1a314 (a block start inside the index-8 handler); executed as the original does',d)
    # index 4 / 8 ------------------------------------------------------------------------------
    def players(p0,p1,rects):
        d={};d.update(player_state(0,p0,rects[0]));d.update(player_state(1,p1,rects[1]));return d
    def i4(label,desc,p0,p1,flags=3,rects=(rect,rect),extra=None,rec=None):
        d={0x10d422:(4,REC),0x10d68e:(1,flags)};d.update(put_bytes(REC,rec or rect_record(4,[rects[0]])));d.update(players(p0,p1,rects))
        if extra:d.update(extra)
        add(label,'fixture-condition-4',desc,d)
    i4('cond-index-4-flags0','index 4 with 10d68e = 0 (Clear at once)','in','in',flags=0)
    for p0 in ('marker','inactive','in','x-lo-in','x-hi-out','x-below','x-above','y-lo-in','y-hi-out','y-below','y-above'):
        i4('cond-index-4-p0-%s-p1-in'%p0,'index 4: player 0 %s, player 1 in the rect'%p0,p0,'in')
    for p1 in ('marker','inactive','x-lo-in','x-hi-out','x-below','x-above','y-lo-in','y-hi-out','y-below','y-above'):
        i4('cond-index-4-p0-in-p1-%s'%p1,'index 4: player 0 in the rect, player 1 %s'%p1,'in',p1)
    i4('cond-index-4-both-marker','index 4: both callbacks 270e (Set without any rect test)','marker','marker')
    carry=(0x0010,0xfff0,0x0020,0x0020)         # ymin+h = 0x10010: the low WORD sum carries into the high WORD (xmax + 1)
    i4('cond-index-4-add-carry-x-in-by-carry','index 4 rect ymin fff0 h 0020 (ADD.L carry): x == xmin+w exactly is inside only because of the carry','x-lo-in','x-lo-in',rects=(carry,carry),
        extra={P0+0x42:(2,0x0030),P1+0x42:(2,0x0030),P0+0x46:(2,(0xfff8+0x100)&0xffff),P1+0x46:(2,(0xfff8+0x100)&0xffff)})
    i4('cond-index-4-add-carry-y-hi-edge-out','index 4 same carry rect: y = 0x10 equals the wrapped ymax (BGE out)','in','in',rects=(carry,carry),
        extra={P0+0x42:(2,0x0020),P1+0x42:(2,0x0020),P0+0x46:(2,0x0110),P1+0x46:(2,0x0110)})
    r1=(0x20,0x30,0x40,0x40);r2=(0x30,0x40,0x40,0x40)
    def pos(p,where):
        # inside rect1 only / rect2 only / both / none (rects overlap in x 30..60, y 40..70)
        pts={'r1':(0x25,0x35),'r2':(0x65,0x75),'both':(0x40,0x50),'none':(0x200,0x200)}
        x,y=pts[where];base=P0 if p==0 else P1
        return {base:(4,0x1234+p),base+0x15:(1,0x80),base+0x42:(2,x),base+0x46:(2,(y+0x100)&0xffff)}
    for w0 in ('r1','r2','both','none'):
        for w1 in ('r1','r2','both','none'):
            d={0x10d422:(4,REC),0x10d68e:(1,3)};d.update(put_bytes(REC,rect_record(8,[r1,r2])));d.update(pos(0,w0));d.update(pos(1,w1))
            add('cond-index-8-p0-%s-p1-%s'%(w0,w1),'fixture-condition-8','index 8: player 0 in %s, player 1 in %s (rect1 20/30 40x40, rect2 30/40 40x40)'%(w0,w1),d)
    d={0x10d422:(4,REC),0x10d68e:(1,0)};d.update(put_bytes(REC,rect_record(8,[r1,r2])));add('cond-index-8-flags0','fixture-condition-8','index 8 with 10d68e = 0',d)
    d={0x10d422:(4,REC),0x10d68e:(1,1)};d.update(put_bytes(REC,rect_record(8,[r1,r2])));d.update(players('marker','marker',(r1,r2)))
    add('cond-index-8-flags1-both-marker','fixture-condition-8','index 8: both callbacks 270e, 10d68e = 1',d)
    # script gate ----------------------------------------------------------------------------------
    def scr(label,desc,word,wait,phase=0,fx=None):
        d={0x10d412:(4,REC2),0x10d416:(2,wait),0x10d418:(2,phase)};d.update(put_bytes(REC2,word.to_bytes(2,'big')+bytes(4)))
        add(label,'fixture-script',desc,d,fx=fx or fx36)
    scr('script-negative-word-1a28a','script word 8000 (negative): 1a28a stores ffff into the wait WORD and returns',0x8000,0)
    scr('script-negative-word-ffff-wait-equal-phase','script word ffff, wait == phase (BCS not taken)',0xffff,5,5)
    scr('script-positive-word-1a0b6','script word 0012, wait 0 <= phase: BSR 1a0b6 boundary',0x0012,0)
    scr('script-wait-greater-than-phase','script wait 0005 > phase 0: 1a29c RTS at once',0x0012,5,0)
    scr('script-wait-unsigned-ffff-phase-ffff','script wait ffff == phase ffff, positive word: 1a0b6',0x0001,0xffff,0xffff)
    # shake ---------------------------------------------------------------------------------------
    for amp in (0x00080000,0xfff80000,0x7fffffff,0x80000000,0,0x00007fff,0x12345678,0xedcba988,0x00010000,0xffff0000,0x0007ffff,0xfff80001):
        add('shake-amplitude-%08x'%amp,'fixture-shake','10d408 = %08x on a full-path seed: 1a3d6 amplitude decay and clamp'%amp,{0x10d408:(4,amp),0x10d404:(2,0x1111)})


def pick_w(rng):
    r=rng.random()
    if r<0.5:return rng.choice(POOL_W)
    if r<0.8:return rng.randrange(0,0x400)
    return rng.randrange(0,0x10000)


def pick_l(rng):
    r=rng.random()
    if r<0.3:return rng.choice((0,0x8000,0x10000,0x60000,0x7fff0000,0x80000000,0xffff0000,0x00018000,0xfffe8000,0x00010001))
    if r<0.7:return (pick_w(rng)<<16)&M32
    return rng.randrange(0,1<<32)


BOUNDS_WORDS=(0x10d3ce,0x10d3d0,0x10d3d2,0x10d3d4,0x10d444,0x10d448,0x10d446,0x10d44a,0x10d426,0x10d42a,0x10d428,0x10d42c,0x10d3a2,0x10d3a6,0x10d3b8,0x10d3ba,0x10d440,0x10d442,0x10d41e,0x10d420,0x10d43e,0x10d44c,0x10d418)
BOUNDS_LONGS=(0x10d3bc,0x10d3c0,0x10d3e6,0x10d3ea,0x10d3de,0x10d3e2,0x10d3fc,0x10d400)


def bounds_candidate(rng):
    d={0x10d3cc:(1,rng.choice((0,1,2,3,3,3)))}
    for a in BOUNDS_WORDS:
        if rng.random()<0.75:d[a]=(2,pick_w(rng))
    for a in BOUNDS_LONGS:
        if rng.random()<0.75:d[a]=(4,pick_l(rng))
    if rng.random()<0.35:d[0x10d44c]=(2,0);d[0x10d43e]=(2,0)                # no force: the 19bda bounds branch
    return d


def search_fixtures(program,base_fx,make,targets,seed,budget,limit,already):
    """Deterministic coverage-guided choice of declared fixtures: candidates come from a seeded generator, the independent model decides which candidate reaches
    block starts not yet covered; the chosen candidates are then observed natively."""
    rng=random.Random(seed);covered=set(already);chosen=[]
    for k in range(budget):
        cand=make(rng);r=model_cover(program,base_fx,writes_of(cand[0]) if isinstance(cand,tuple) else writes_of(cand))
        d=cand[0] if isinstance(cand,tuple) else cand
        if r is None:continue
        cov,final=r
        if final not in BOUNDARIES_U2 and final!=RETURN_FF000:continue
        new=(cov&targets)-covered
        if new:
            covered|=new;chosen.append((k,d,sorted(new)))
            if len(chosen)>=limit or not (targets-covered):break
    return chosen,covered


def reg_candidate(rng):
    regs={}
    for k in ('d0','d1','d2','d3','d6','d7'):
        if rng.random()<0.8:regs[k]=pick_l(rng)
    d={}
    for a in (0x10d3c4,0x10d3c8,0x10d3de,0x10d3e2,0x10d3bc,0x10d3c0):
        if rng.random()<0.6:d[a]=(4,pick_l(rng))
    for a in (0x10d3ee,0x10d3f0,0x10d3f2,0x10d3f4,0x10d3f6,0x10d3f8,0x10d418,0x10d3fa,0x10d3a2,0x10d3a6):
        if rng.random()<0.6:d[a]=(2,pick_w(rng))
    for a in (0x10d3cc,):d[a]=(1,rng.choice((0,1,2,3)))
    return d,regs


def search_reg(program,base_fx,targets,seed,budget,limit,already):
    rng=random.Random(seed);covered=set(already);chosen=[]
    for k in range(budget):
        d,regs=reg_candidate(rng);r=model_cover(program,base_fx,writes_of(d),regs)
        if r is None:continue
        cov,final=r
        if final not in BOUNDARIES_U2 and final!=RETURN_FF000:continue
        new=(cov&targets)-covered
        if new:
            covered|=new;chosen.append((k,d,regs,sorted(new)))
            if len(chosen)>=limit or not (targets-covered):break
    return chosen,covered


def search_conditions(B,program,scene_in):
    covered=set()
    for c in B.censuses.values():covered|=c['leaders']
    fx182=[s for s in B.specs if s['label']=='cond-index-0-clear'][0]['fixture']
    targets=set(LEADERS_U2)
    chosen,cov=search_fixtures(program,fx182,bounds_candidate,targets,20260101,12000,40,covered)
    for k,d,new in chosen:
        B.add('fixture-bounds-%04d'%k,'fixture-bounds','declared RAM fixture (coverage-guided by the independent model, candidate %d) on scene seed 182: camera flags / bounding box / limits / force; new block starts %s'%(k,[hex(x) for x in new]),fx182,setup=writes_of(d))
    covered=cov
    bases={}
    for s in list(B.specs):
        if s['label'].startswith('reentry-'):
            pc=int(s['label'].split('-')[1],16);hit=s['label'].split('-')[2]
            bases.setdefault((pc,hit),s)
    for (pc,hit),s in sorted(bases.items()):
        if pc not in (0x19c22,0x1997c,0x19da0,0x19bca,0x19d2c):continue
        base=s['fixture'];chosen,cov=search_reg(program,base,targets,20260102+pc,4000,12,covered)
        for k,d,regs,new in chosen:
            fx=dict(base);fx['regs']=dict(base['regs'],**regs)
            fx['preparation']=dict(role='%s with declared initial register variant %s (the other registers, A7 and the stack bytes are the captured native state)'%(base['preparation']['role'],{a:hex(v) for a,v in regs.items()}))
            B.add('fixture-reg-%x-%s-%04d'%(pc,hit,k),'fixture-reg-%x'%pc,'declared register/RAM variant of the re-entry state at %x (coverage-guided by the independent model, candidate %d); new block starts %s'%(pc,k,[hex(x) for x in new]),fx,setup=writes_of(d))
        covered|=cov
    return covered


def rom_pointer_fixtures(B,program,scene_in):
    """Condition / script / placement pointers into fixed ROM and into the banked window (bank 3 is active after 1a742): the WORDs are read from the original ROM."""
    row,ram,regs=scene_in[182];fx182=direct_fx('scene-0182-rom',ram,regs,scene_prov(182,row,ram));row,ram,regs=scene_in[36];fx36=direct_fx('scene-0036-rom',ram,regs,scene_prov(36,row,ram))
    def find(base,lo,hi,pred):
        for a in range(lo,hi,2):
            w=int.from_bytes(program[base+a:base+a+2],'big')
            if pred(w):return a
    fixed=find(0,0x30000,0x80000,lambda w:w==0 and int.from_bytes(program[0x30000:0x30002],'big')>=0)
    fixed_c=find(0,0x31000,0x80000,lambda w:w==0xc)
    bank0=find(0x300000,0x1000,0x80000,lambda w:w==0)
    bankp=find(0x300000,0x2000,0x80000,lambda w:0<w<0x7fff)
    for tag,addr in (('fixed-rom',fixed),('bank3-window',0x200000+bank0)):
        B.add('rom-pointer-condition-%s'%tag,'fixture-rom-pointer','10d422 = %x (%s): the index WORD (0) and its data WORD are read from the original ROM'%(addr,tag),fx182,setup=writes_of({0x10d422:(4,addr)}))
    B.add('rom-pointer-condition-index-c-fixed-rom','fixture-rom-pointer','10d422 = %x: ROM WORD 000c -> JSR 1a2e0'%fixed_c,fx182,setup=writes_of({0x10d422:(4,fixed_c)}))
    B.add('rom-pointer-script-bank3-window','fixture-rom-pointer','10d412 = %x (bank 3 window), wait 0: the script WORD is read from banked ROM (BPL -> BSR 1a0b6)'%(0x200000+bankp),fx36,setup=writes_of({0x10d412:(4,0x200000+bankp),0x10d416:(2,0),0x10d418:(2,0)}))
    B.add('rom-pointer-script-fixed-rom','fixture-rom-pointer','10d412 = %x (fixed ROM), wait 0'%fixed,fx36,setup=writes_of({0x10d412:(4,fixed),0x10d416:(2,0),0x10d418:(2,0)}))
    gate=[s['fixture'] for s in B.specs if s['label'].startswith('reentry-1a78c-hit1-')][0]
    for tag,addr in (('fixed-rom',fixed),('bank3-window',0x200000+bankp)):
        B.add('rom-pointer-placement-%s'%tag,'fixture-rom-pointer','re-entry at 1a78c with 10d40e = %x (%s): the placement WORD is read from ROM'%(addr,tag),gate,setup=writes_of({0x10d40e:(4,addr)}))


def rounding_fixtures(B,program,scene_in):
    """19ab0 averages D7 with the previous 10d3de: odd positive differences round up, odd negative ones down.  Candidates come from a seeded generator, the model picks them."""
    s0=[s for s in B.specs if s['label']=='cond-index-0-clear'][0]['fixture']
    for sign,name in ((1,'positive'),(-1,'negative')):
        rng=random.Random(777+sign)
        for k in range(30000):
            d=bounds_candidate(rng);d[0x10d3cc]=(1,1);d[0x10d44c]=(2,0);d[0x10d43e]=(2,0);prev=rng.choice((1,3,5,0x1001,0x2001,0x7fff,0x12345))*sign;d[0x10d3de]=(4,prev&M32)
            r=model_run(program,s0,writes_of(d))
            if r is None or r[1] not in BOUNDARIES_U2:continue
            M,final=r;lead=[m for m in M.leads if m['pc']==0x19ab0]
            if not lead:continue
            diff=sx32((lead[0]['d7']-prev)&M32)
            if diff&1 and (diff>0)==(sign>0) and abs(diff)<(1<<30):
                B.add('fixture-average-odd-%s-difference'%name,'fixture-bounds','declared RAM fixture (candidate %d): 10d3de = %d, odd %s difference %d at 19ab0'%(k,prev,name,diff),s0,setup=writes_of(d));break
        else:raise AssertionError('no rounding candidate '+name)


def guard_conditions(B,program,scene_in):
    def fx_of(i,**kw):
        row,ram,regs=scene_in[i];return direct_fx('scene-%04d-guard'%i,ram,regs,scene_prov(i,row,ram),role='direct 1a73c entry on the rebuilt scene seed %d (guard condition)'%i)
    fx182=fx_of(182);fx36=fx_of(36);fx0=fx_of(0)
    reentry=lambda prefix:[s['fixture'] for s in B.specs if s['label'].startswith(prefix)][0]
    ok=lambda **kv:dict(problem='unsupported_odd_data_access',**kv)
    def g(label,desc,guard,fx,setup=(),stop=None,**kw):
        B.add(label,'guard',desc,fx,setup=setup,stop=PROBE_STOP if stop is None else stop,guard=guard,model=False,**kw)
    d={0x10d422:(4,REC+1)};g('guard-odd-A1-condition-pointer','10d422 = odd: MOVE.W (A1)+,D0 at 1a2c0 reads an odd WORD',ok(pc=0x1a2c0,address=REC+1+0x100000-0x100000,size=2,access='read'),fx182,writes_of(d))
    d={0x10d412:(4,REC2+1),0x10d416:(2,0),0x10d418:(2,0)};g('guard-odd-A1-script-pointer','10d412 = odd, wait 0: TST.W (A1) at 1a284 reads an odd WORD',ok(pc=0x1a284,address=REC2+1,size=2,access='read'),fx36,writes_of(d))
    d={0x10d422:(4,REC),0x10d68e:(1,0),0x10d41e:(2,0),0x10d418:(2,0),0x10d3b4:(4,0x10e601)};d2=put_bytes(REC,(0).to_bytes(2,'big')+(0x42).to_bytes(2,'big'));d.update(d2)
    g('guard-odd-A1-motion-record','condition index 0 Set then 197da with 10d3b4 = odd: CMPI.W #ffff,2(A1) at 197ec reads an odd WORD',ok(pc=0x197ec,address=0x10e603,size=2,access='read'),fx182,writes_of(d))
    base=reentry('reentry-1a78c-hit1-')
    g('guard-odd-A0-placement-pointer','re-entry at 1a78c with 10d40e = odd: MOVE.W (A0),D7 at 1a450 reads an odd WORD',ok(pc=0x1a450,address=0x10e601,size=2,access='read'),base,writes_of({0x10d40e:(4,0x10e601)}))
    f=dict(fx182);f['regs']=dict(f['regs'],a5=0x108001);f['preparation']=dict(role='direct 1a73c entry with declared initial A5 = 108001 (odd)')
    g('guard-odd-A5-first-write','A5 = 108001: MOVE.W #1,-7ff0(A5) at 1a73c writes an odd WORD',ok(pc=0x1a73c,address=0x108001-0x7ff0,size=2,access='write',odd_write_restored=True),f)
    f=dict(fx182);f['initial_a7']=S+1;f['preparation']=dict(role='direct 1a73c entry with declared initial A7 = 1feffd (odd)')
    g('guard-odd-A7-bsr-push','A7 = 1feffd: the first BSR (1a752) pushes an odd LONG',ok(pc=0x1a752,address=S+1-4,size=4,access='write',odd_write_restored=True),f)
    f=dict(base);f['entry_pc']=0x1a44e;f['initial_a7']=base['initial_a7']+1;f['preparation']=dict(role=base['preparation']['role']+'; declared entry at 1a44e (RTS) with declared A7 + 1 (odd)')
    g('guard-odd-A7-rts','declared entry at 1a44e (RTS) with an odd A7: the RTS reads an odd LONG',ok(pc=0x1a44e,address=f['initial_a7'],size=4,access='read'),f)
    f=dict(fx182);f['regs']=dict(f['regs'],a5=0x8ff0);f['preparation']=dict(role='direct 1a73c entry with declared initial A5 = 8ff0')
    g('guard-rom-write-A5','A5 = 8ff0: MOVE.W #1,-7ff0(A5) at 1a73c writes ROM address 1000',dict(problem='unmapped_or_protected',pc=0x1a73c,address=0x1000,size=2),f)
    f=dict(fx182);f['initial_a7']=0x1100;f['preparation']=dict(role='direct 1a73c entry with declared initial A7 = 1100 (ROM)')
    g('guard-rom-write-A7-push','A7 = 1100 (ROM): the first BSR pushes its return LONG into ROM',dict(problem='unmapped_or_protected',pc=0x1a752,address=0x10fc,size=4),f)
    # index outside the table: the computed JSR target is followed
    for tag,idx,guard in (('2000',0x2000,dict(problem='unsupported_code_target',target=0x1a2d4+0x2000)),('odd-0001',1,dict(problem='unsupported_code_target',target=0x1a2d5)),('negative-8000',0x8000,dict(problem='unsupported_code_target',target=(0x1a2d4-0x8000)&M32))):
        d={0x10d422:(4,REC)};d.update(put_bytes(REC,idx.to_bytes(2,'big')+bytes(6)))
        g('guard-cond-index-%s'%tag,'condition index %04x: the JSR target 1a2d4+sext(index) is %x'%(idx,(0x1a2d4+sx16(idx))&M32),guard,fx182,writes_of(d))
    # bad stops
    g('guard-bad-stop-1a7a8-on-19844-seed','scene seed 0 reaches 19844 first: stop declared 1a7a8',dict(problem='unsupported_code_target',target=0x19844),fx0,stop=0x1a7a8)
    g('guard-bad-stop-19844-on-full-path-seed','scene seed 36 reaches 1a7a8: stop declared 19844',dict(problem='unsupported_code_target',target=0x1a7a8),fx36,stop=0x19844)
    g('guard-bad-stop-19812-on-19844-seed','scene seed 0 reaches 19844 first: stop declared 19812',dict(problem='unsupported_code_target',target=0x19844),fx0,stop=0x19812)
    g('guard-bad-stop-1a0b6-on-full-path-seed','scene seed 36 reaches 1a7a8 (script wait ffff): stop declared 1a0b6',dict(problem='unsupported_code_target',target=0x1a7a8),fx36,stop=0x1a0b6)
    g('guard-bad-stop-1a470-on-full-path-seed','scene seed 36: stop declared 1a470',dict(problem='unsupported_code_target',target=0x1a7a8),fx36,stop=0x1a470)
    B.add('boundary-zero-step','boundary','zero-step: the stop PC equals the entry PC 1a73c; nothing is executed',fx36,stop=ENTRY_1A73C)


def row_sha(item):return sha(item[1])


def contract_claims(cen,scene_in,entry_in,stage_in):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    by=collections.defaultdict(list)
    for c in cen['scene_frame']:by[c['first_stop']].append(c['case'])
    full=[36,38,86,88,91,94,95,96,172,173,176,177]+list(range(182,192));g1a0b6=[237,424,437,479,502,509,514,564,577,588,589,590,591]
    claim('scene_frame_execution 594 cases partition by first U2 boundary (option A): 1a7a8 22, 19844 207, 19812 352, 1a0b6 13',
        'confirmed' if (len(by['0x1a7a8']),len(by['0x19844']),len(by['0x19812']),len(by['0x1a0b6']))==(22,207,352,13) and by['0x1a7a8']==full and by['0x1a0b6']==g1a0b6 else 'contradicted',
        {k:len(v) for k,v in by.items()}|dict(full_path_cases=by['0x1a7a8'],script_gate_cases=by['0x1a0b6']))
    st=cen['stage_frame']
    claim('stage_frame: 64 cases enter 1a73c, all execute 19a40 and 19ac8 and stop at 19844',
        'confirmed' if len(st)==64 and all(c['first_stop']=='0x19844' and '0x19a40' in c['leaders'] and '0x19ac8' in c['leaders'] for c in st) else 'contradicted',dict(cases=len(st)))
    en=cen['stage_entry'];e1=[c['case'] for c in en if c['first_stop']=='0x1a7a8']
    claim('stage_entry_body: 142 traces enter 1a73c; 22 (0090 0091 0094 0095 0100 0101 0106..0111 0118..0126 0141) reach 1a7a8, 120 stop at 19844',
        'confirmed' if len(en)==142 and e1==[90,91,94,95,100,101]+list(range(106,112))+list(range(118,127))+[141] and sum(1 for c in en if c['first_stop']=='0x19844')==120 else 'contradicted',dict(to_1a7a8=e1))
    seq=['0x1a2cc','0x1a26a','0x1a526','0x19b96','0x19832','0x19c28','0x19c40','0x19978','0x198ee','0x19c68','0x19ca0','0x19cd6','0x19d08','0x19802','0x19d98','0x1a776','0x1a780','0x1a3d6','0x1a3f8','0x1a402']
    fullc=[c for c in cen['scene_frame'] if c['first_stop']=='0x1a7a8']
    claim('full path 1a73c..1a7a8 visits 1a2cc 1a26a 1a526 19b96 19832 19c28 19c40 19978 198ee 19c68 19ca0 19cd6 19d08 19802 19d98 1a776 1a780 1a3d6 1a3f8 1a402 (8 cases with script wait ffff via 1a278 -> 1a29c, 14 with script null 1a276)',
        'confirmed' if all(all(x in c['leaders'] for x in seq) for c in fullc) and sum(1 for c in fullc if '0x1a29c' in c['leaders'])==8 and sum(1 for c in fullc if '0x1a276' in c['leaders'])==14 else 'contradicted',
        dict(cases=len(fullc),with_1a29c=sum(1 for c in fullc if '0x1a29c' in c['leaders']),with_1a276=sum(1 for c in fullc if '0x1a276' in c['leaders'])))
    sc=cen['scene_frame']
    n4=[c['case'] for c in sc if '0x1a334' in c['leaders'] and '0x1a3a0' in c['leaders'] and '0x1a33c' not in c['leaders']]
    n8=[c['case'] for c in sc if '0x1a2f2' in c['leaders'] and '0x1a3a0' in c['leaders'] and '0x1a2fa' not in c['leaders']]
    i0=[c['case'] for c in sc if '0x1a2e0' in c['leaders']]
    claim('condition handlers in the seeds: index 4 -> 1a3a0 (10d68e=0) 17 cases, index 8 -> 1a3a0 7 cases, index 0 1a2e0 Clear 586 / Set 587, 585 index 4 with both 270e markers (1a356 -> 1a29e -> 197da loop)',
        'confirmed' if (len(n4),len(n8))==(17,7) and i0==[586,587] and '0x1a29e' not in sc[586]['leaders'] and '0x1a29e' in sc[587]['leaders'] and all(x in sc[585]['leaders'] for x in ('0x1a356','0x1a29e','0x197ec')) else 'contradicted',
        dict(index4_clear=len(n4),index8_clear=len(n8),index0=i0))
    never=['0x1a35c','0x1a366','0x1a39a','0x1a2fa','0x1a302','0x1a306','0x1a30e','0x1a312','0x1a314','0x1a320','0x1a324','0x1a32c','0x1a330','0x1a332','0x197e6','0x1a28a']
    seen=[x for x in never if any(x in c['leaders'] for c in sc+st+en)]
    claim('rect test 1a35c..1a39a, 1a2fa..1a332, 197e6 and 1a28a are executed by no seed (594 scene + 64 stage_frame + 142 stage_entry)','confirmed' if not seen else 'contradicted',dict(executed_by_seeds=seen))
    labels=EVIDENCE
    def conds(prefix):return {k:v for k,v in labels.items() if k.startswith(prefix)}
    for tag,pcs in (('rect-test + both rect handlers',['0x1a35c','0x1a366','0x1a39a','0x1a2fa','0x1a312','0x1a330','0x1a332']),('197e6 (motion null)',['0x197e6']),('1a28a',['0x1a28a']),('shake clamps',['0x1a3f6','0x1a400']),('BVC saturation 19d72/19d8e',['0x19d72','0x19d8e']),
        ('index 0 Clear/Set + index c',['0x1a2e0','0x1a29e']),('ADD.L carry blocks 1998e..199d2',['0x1998e','0x199d2']),('19c44..19c5a unsigned compare tail',['0x19c44','0x19c5a']),('19db2/19dba EXG',['0x19db2','0x19dba']),('19a40/19ac8 clamps',['0x19a60','0x19a74','0x19a7c','0x19aa6','0x19aae','0x19ae8','0x19afc','0x19b04','0x19b2e','0x19b36'])):
        hit={pc:[k for k,v in labels.items() if pc in v['leaders']][:3] for pc in pcs}
        claim('declared fixtures execute %s natively (all block starts %s reached)'%(tag,pcs),'confirmed' if all(hit.values()) else 'not-reproduced',hit)
    c0=conds('cond-index-0-');cc=conds('cond-index-c-')
    claim('condition index c lands on 1a2e0 directly (no 1a2d4 BRA hop) and behaves like index 0','confirmed' if cc and all('0x1a2d4' not in v['leaders'] and '0x1a2e0' in v['leaders'] for v in cc.values()) and c0 and all('0x1a2d4' in v['leaders'] for v in c0.values()) else 'contradicted',
        dict(index_c=sorted(cc),index_0=sorted(c0)))
    c40=EVIDENCE.get('cond-index-0040-lands-in-1a2f2-block-start-1a314')
    claim('condition index 0040 follows the computed JSR target 1a314 (a block start inside the index-8 handler)','confirmed' if c40 and '0x1a314' in c40['leaders'] and '0x1a2f2' not in c40['leaders'] else 'contradicted',c40)
    x=[(k,v['x_average']) for k,v in labels.items() if 'x_average' in v]
    pos=[a for k,a in x if a['difference']>0 and a['difference']&1];neg=[a for k,a in x if a['difference']<0 and a['difference']&1]
    claim('19ab0 average: ASR after +1 for >= 0 only (all 32-bit wrapped): odd positive differences round up (ceil), odd negative differences round down (floor); a difference of 7fffffff wraps through the ADDQ to c0000000',
        'confirmed' if pos and neg and all(a['result_minus_previous']==sx32(((a['difference']+1)&M32))>>1 for a in pos) and all(a['result_minus_previous']==a['difference']>>1 for a in neg) else ('not-observable' if not (pos and neg) else 'contradicted'),
        dict(odd_positive_examples=pos[:3],odd_negative_examples=neg[:3],x_average_conditions=len(x)))
    y=[(k,v['y_store_first']) for k,v in labels.items() if 'y_store_first' in v]
    claim('19ac8 stores 10d3e2 = D7 first, so the Y result is not averaged with the previous value (final D7 == new 10d3e2 unless 19ce6 clears it)','confirmed' if y and all(a['later_clear'] or a['d7_at_19b38']==a['ram_53e2_after'] for _,a in y) else ('not-observable' if not y else 'contradicted'),dict(conditions=len(y),examples=[a for _,a in y[:3]]))
    bx=[v['bvc_x'] for v in labels.values() if 'bvc_x' in v];by_=[v['bvc_y'] for v in labels.values() if 'bvc_y' in v]
    claim('19d72 / 19d8e: a signed overflow of the last ADD.W saturates the box edge to 7fff','confirmed' if bx and by_ and all(a['written_53f4']==0x7fff for a in bx) and all(a['written_53f8']==0x7fff for a in by_) else ('not-observable' if not (bx and by_) else 'contradicted'),dict(x_conditions=len(bx),y_conditions=len(by_)))
    sh={k:v['shake'] for k,v in labels.items() if 'shake' in v and k.startswith('shake-amplitude')}
    claim('1a3d6: amplitude decay d0 = -d0 + d0>>4, shake word = clamp((d0+8000)>>16, -8..8), previous word moved to 5406','confirmed' if sh and all((a['word_5404']==0x0008 if sh_k.endswith('80000000') else True) for sh_k,a in sh.items()) and any(a['clamp_hi'] for a in sh.values()) and any(a['clamp_lo'] for a in sh.values()) else 'contradicted',sh)
    ports=set();
    claim('port writes occur only at 1a742 1a74a 1a796 1a79e (all other writes are RAM)','confirmed' if PORT_PCS.issubset({0x1a742,0x1a74a,0x1a796,0x1a79e}) and PORT_PCS else 'contradicted',sorted(hex(x) for x in PORT_PCS))
    claim('block start list: observer decode gives 217 block starts + 3 for 289e = 220; the contract lists 215 (observer additionally splits 19c7e and 19cb6, which the contract bundles into the preceding block)','info',
        dict(observer_extra_over_contract=sorted(hex(x) for x in (LEADERS_U2-{0x289e,0x28a8,0x28ac})-CONTRACT_STARTS),contract_not_in_observer=sorted(hex(x) for x in CONTRACT_STARTS-LEADERS_U2)))
    claim('CCR/carry values themselves (known Set/Clear/Unknown), the Unknown-carry API error and the internal-PC rejection of the API','not-observable','SR is never read; branch decisions are evidenced by the executed PC paths and the register file at every block start')
    return claims


PORT_PCS=set()
CONTRACT_STARTS=set()


def negative_checks(program,B):
    """Tool-level negative checks: a stop that is not directly after the transferring instruction must be refused by the stop evidence."""
    out=[]
    fx=[s for s in B.specs if s['label'].startswith('natural-scene-full-path-0036')][0]['fixture']
    for label,stop in (('internal-return-address-1a75e',0x1a75e),('mid-routine-leader-1a76a',0x1a76a)):
        spec=dict(label=label,group='negative',fixture=dict(fx,label=label),steps=[dict(label=label,changes=[],stop_pc=stop,checkpoints=[],a7=('entry',0))],provenance='negative stop check')
        phases=fc.run_condition(program,spec,True);p=phases[-1];assert p['guard'] is None and p['outgoing']['pc']==stop
        try:stop_evidence(program,p);refused=False;err=None
        except AssertionError as e:refused=True;err=repr(e)[:200]
        out.append(dict(label=label,stop=hex(stop),native_run_stopped_there=True,stop_evidence_refused=refused,error=err))
        assert refused,label
    return out


def main():
    global SCENE_ROWS,CONTRACT_STARTS
    dev_filter=sys.argv[1] if len(sys.argv)>1 else None
    out_dir=OUT if dev_filter is None else Path('/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/u2/dev_out')
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    configure(program,out_dir)
    CONTRACT_STARTS,contract_bundled=contract_lists()
    scene_obs,scene_in=scene_inputs(program);SCENE_ROWS=scene_in;stage_ver,stage_in=stage_frame_inputs(program);entry_obs,entry_in=stage_entry_inputs(program)
    print('seeds',len(scene_in),len(stage_in),len(entry_in),flush=True)
    cen=build_census(program,scene_in,stage_in,entry_in);print('census done',flush=True)
    B=Builder(program)
    natural_conditions(B,scene_in,stage_in,entry_in,cen,dict(**{'19812':24,'19844':24,'entry19844':20}))
    survey=reentry_survey(program,scene_in);reentry_conditions(B,program,scene_in,survey)
    condition_fixtures(B,scene_in);covered=search_conditions(B,program,scene_in);guard_conditions(B,program,scene_in);rom_pointer_fixtures(B,program,scene_in);rounding_fixtures(B,program,scene_in)
    print('conditions',len(B.specs),'model-covered',len(covered&LEADERS_U2),'of',len(LEADERS_U2),'missing',sorted(hex(x) for x in LEADERS_U2-covered),flush=True)
    specs=B.specs
    if dev_filter:specs=[s for s in specs if dev_filter in s['label']]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,fh.CONTRACT,STAGE_FRAME}
    input_paths.update(Path(p) for p in SEED_FILES)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin_ref=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin_ref['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);model_checks=[];summaries=[]
    for number,spec in enumerate(specs):
        split,control=run_spec(program,spec)
        if spec['label'] in B.models and spec.get('guarded') is None:model_checks.append(check_model(program,spec,control))
        summaries.append(condition_summary(spec,split,control));collect_evidence(spec,split,control)
        for q in control:
            for e in q['events']:
                if e['region'] in PORT_REGIONS and e['access']=='write':PORT_PCS.add(e['pc'])
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=fh.store('c%03d_split'%number,split,KEYS_PCS),continuous_control=fh.store('c%03d_control'%number,control,KEYS_PCS),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=False,stored_from_step=0)
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else '',
            ' MODEL %s'%('ok' if model_checks[-1]['equal'] else 'MISMATCH') if spec['label'] in B.models and not spec.get('guarded') else ''),flush=True)
    negatives=negative_checks(program,B)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,u2_ranges=U2_RANGES,existing_ranges=EXISTING_RANGES,u1_entry_ranges=U1_NEEDED,instructions=instructions,boundary_stop_pcs=BOUNDARIES_U2,
        stop_rules={'bsr_boundaries':{hex(k):dict(bsr_pc=hex(v[0]),return_long=hex(v[1])) for k,v in BOUNDARY_BSR.items()},'motion_boundaries':{hex(k):dict(bne_pc=hex(v),callers=[hex(x) for x in BOUNDARY_CALLERS[k]]) for k,v in BOUNDARY_BNE.items()},
            'declared return':'RTS popping the declared return LONG at A7 (ff000)'},new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in U2_RANGES}),indent=2)+'\n').encode()
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
    claims=contract_claims(cen,scene_in,entry_in,stage_in) if not dev_filter else []
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    missing_native=sorted(hex(x) for x in LEADERS_U2-coverage)
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=0,variant_child_layouts=[],guard_reports=guard_reports,negative_stop_checks=negatives,bank_reads_by_condition=[dict(label=s['label'],bank_read_count=s['bank_read_count'],reads=s['bank_reads']) for s in summaries if s['bank_read_count']],bank_descriptor_search=[],
        new_ranges=U2_RANGES,existing_ranges=EXISTING_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=RANGE_TABLE,contract_block_starts=len(CONTRACT_STARTS),contract_bundled_branches=len(contract_bundled),observer_block_starts_u2=len(LEADERS_U2)),
        contract_model_checks=model_checks,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=EVIDENCE,
        first_boundary_census=dict(scene_frame=cen['scene_frame'],stage_frame=cen['stage_frame'],stage_entry=cen['stage_entry'],counts={k:dict(collections.Counter(c['first_stop'] for c in v)) for k,v in cen.items()}),
        seed_provenance=dict(files=SEED_FILES,scene_frame=dict(observation_sha256=SCENE_OBS_SHA,initializer_observation_sha256=SCENE_SEED_SHA,cases=len(scene_in)),stage_frame=dict(verification_sha256=STAGE_FRAME_SHA,rebuilt_cases=len(stage_in),cases=[dict(index=i,label=r['label'],input_sha256=r['input_sha256'],rebuilt_from=how) for i,r,_,how in stage_in]),
            stage_entry=dict(observation_sha256=STAGE_ENTRY_SHA,cases=len(entry_in),captured=[dict(case=c['case_index'],family=c['family'],input_ram_sha256=c['input_ram_sha256'],ram_at_1a73c_sha256=c['ram_sha256'],instructions=c['instructions'],bank=c['bank']) for c in entry_in]),
            reentry_survey=[dict(case=x['case'],hits=x['hits'],nonnull=x['nonnull'],gate=x['gate']) for x in survey],
            note='Declared initial fixtures: rebuilt scene_frame inputs (sha-checked), rebuilt stage_frame inputs (sha-checked), the 1a73c entry state of the original 47a94 body run, native states captured from the original full-frame run, and declared host RAM/register variants.  A5=108000, return LONG ff000 at A7=1feffc (2ac2 for the natural 480bc runs).'),
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=summaries,group_counts=group_counts,covered_PCs=sorted(coverage),uncovered_u2_block_starts=missing_native,block_starts=BLOCKS,boundary_stop_pcs=BOUNDARIES_U2,failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures (rebuilt original seeds, captured native states, declared RAM/register variants), not natural scheduler/gameplay reachability; direct entries at internal PCs and re-entries are declared fixtures (entry PC, A7, stack bytes, registers, bank page), never applied after execution begins.',
            'Boundary stops (1a0b6 1a470 1a7a8 19812 19844 19910) are accepted only directly after the transferring instruction; the code behind them (U3 non-null motion, U4 1a7a8, U5 1a0b6/1a470) is never executed by this unit; it is executed only inside the captured native states of the original full-frame run.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path and the register file at every block start.  The Unknown-carry API error and internal-PC rejection are API-level checks, not observed here.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; the PVC page holds only the two bank registers; ordered port writes are instruction accesses, not physical bus cycles.',
            'The work RAM is mirrored (1feffc is offset effc of the 64KiB image) unlike the flat map of the original observers; stack LONGs are declared inside the image.',
            'Index values outside the table other than c (0040 -> 1a314, 2000, 0001, 8000) are observed only as native behavior of the computed JSR; mid-block targets are not modelled.',
            'The game meaning of the RAM fields, the 1a7a8 / 1a0b6 / 1a470 bodies and U3 remain unknown.'])
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_checks=len(model_checks),
        model_equal=sum(1 for m in model_checks if m['equal']),uncovered=missing_native,sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
