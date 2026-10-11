"""Unpatched 480bc frame helper bundle U5 (script opcodes and placement: 1a0b6 / 1a470 and their callees 19772 / 19e60 / 1a086 / 1a09e / 1a40e / 16fee / 3d7e / e89fa / 43e08 / 43e22) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the scene update observer U4 and through it
U3 (motion walk), U2 (scene core), U1 and the card menu / fade-card chain: persistent-CPU Observer with the declared host-change vocabulary RAM write / PC redirect /
A7 delta / register write at a step boundary, fresh-twice reproduction, split (stop at the first hit of every block leader) versus continuous equivalence, ordered port
events, banked reads with the modeled bank, SHA pins of every imported tool module, ROM SHA/mtime guard.

Declared observer extension (the only change of the imported machinery, done in this process and recorded in the report): the Observer data-device classification
(fade_card.Observer.prepare) and the event replay check (map_transfer.replay) accept a WORD write to 3c0006 as a 'video' port event, exactly like 3c0000 (2/4) and
3c0004 (2); the two functions are re-created from their own source text with that single condition added (source SHA256 of the originals and of the extended text are
in the report; no tool file is edited).  The contract asks for this (main decision 1: 3d7e writes a WORD to 3c0006).

Observed unit: the 872 contract bytes of docs/analysis/animation-machine-script-placement-u5-contract.md (11 code ranges, 88 block starts).  Existing executors are
black boxes inside the unit and are observed natively only: 18c06 (U3 dispatcher), 197da / 19802 (U2), 8da2 (palette bind), 43ffc (scene), 17012 / 1701a (map transfer /
scene), 28ae (fade card) and 43e38 (cleanup coordinate, tail of 43e08 / 43e22).  43e08 / 43e22 are unit blocks (main decision 2).  A stop is accepted only directly after
the transferring instruction (the RTS that pops the declared return LONG); the code behind it is never executed.

Seeds (all pinned by SHA256, rebuilt in this process):
  scene_frame  artifacts/scene_frame_execution (594 cases rebuilt from artifacts/scene_general_initialization + host writes / carried native outputs, every input RAM checked
               against input_ram_sha256).  FULL FRAME: every case is run natively from the direct 1a73c entry to the RTS that pops the declared return LONG ff000 (U2 + U3 + U4 + U5
               + the existing executors, no boundary left) and compared with the recorded original run (instruction count, output RAM outside the stack window, ordered port
               stream SHA, 14 result registers, bank).  The first / every 1a0b6 and 1a470 state of the original full-frame runs is captured (declared re-entry fixture: RAM, 14 registers,
               A7 and the live stack bytes) and run natively + modelled.
  init         artifacts/scene_general_initialization (221 cases): the original 1a5a4 initializer runs are re-executed by the original observer and every 1a0b6 / 1a470 hit is captured and
               run natively + modelled (census); a deterministic sample is observed in full (split / continuous / twice).
  fixtures     declared host RAM writes (applied before the first instruction of the condition) and declared initial registers on captured states for the paths no seed executes.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the step record;
declared initial registers/stack LONGs are part of the fixture summary.

An independent Python model of the contract (a basic-block machine transcribed instruction by instruction from the original bytes, 32-bit register semantics, explicit
word/byte operations, NOT the C++) is compared with each native normal condition: block-leader sequence with the full register file at every leader, the ordered RAM writes, the
ordered port writes (3c0006 and the PVC bank registers), ordered fixed/bank ROM reads, the final registers and the whole 64KiB RAM image.  The existing executors are black boxes:
their entry registers are compared as a leader, their native exit registers, RAM writes and bank changes are replayed into the model (A7 discipline checked).  Any difference is
recorded in contract_discrepancies.
"""
import collections
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import random
import re
import struct
import sys
import textwrap
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_scene_update as su
import observe_animation_machine_motion_walk as mw
import observe_scene_general_initialization as sgi
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
sc=su.sc;fh=su.fh;fc=su.fc;mt=su.mt;op=su.op;menu=su.menu;activation=su.activation;shared=su.shared;sfe=sc.sfe;seb=sc.seb;vsf=su.vsf
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_script_placement_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-script-placement-u5-contract.md'
CONTRACT_SHA='08f3f1ea9bd6e7344d97fd9bb7a2fa3cd776f40b2d46c1e305f5688ef6c1ff4c'
SCOPE=sc.SCOPE
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=sc.u32
S=fc.S
A5V=0x108000
M32=0xffffffff
KEYS14=sc.KEYS14
PORT_REGIONS=fc.PORT_REGIONS
RETURN_FF000=sc.RETURN_FF000
DISCREPANCIES=[]
FC_RANGES_ORIGINAL=tuple(fc.RANGES)                         # fade_card's own ranges (28ae..2918 ...) before any configure()
sx16,sx32=sc.sx16,sc.sx32
sub16,add16,sub32,add32=sc.sub16,sc.add16,sc.sub32,sc.add32
swap=su.swap
SCRATCH=Path('/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/u5o')

# ----------------------------------------------------------------------------------
# Declared observer extension: WORD write to 3c0006 is a video port event
# ----------------------------------------------------------------------------------
EXTENSION={}


def install_video_3c0006():
    src=textwrap.dedent(inspect.getsource(fc.Observer.prepare))
    old="address==0x3c0004 and size==2) and kind=='write'"
    assert src.count(old)==1
    new_src=src.replace(old,"address==0x3c0004 and size==2 or address==0x3c0006 and size==2) and kind=='write'")
    ns={}
    exec(compile(new_src,'<observer-3c0006>','exec'),fc.__dict__,ns)
    class U5Observer(fc.Observer):pass
    U5Observer.prepare=ns['prepare']
    rsrc=textwrap.dedent(inspect.getsource(mt.replay))
    rold="a==0x3c0004 and n==2)"
    assert rsrc.count(rold)==1
    new_rsrc=rsrc.replace(rold,"a==0x3c0004 and n==2 or a==0x3c0006 and n==2)")
    rns={}
    exec(compile(new_rsrc,'<replay-3c0006>','exec'),mt.__dict__,rns)
    EXTENSION.update(observer_base=fc.Observer.__name__,observer_prepare_source_sha256=sha(src.encode()),observer_prepare_extended_source_sha256=sha(new_src.encode()),
        replay_source_sha256=sha(rsrc.encode()),replay_extended_source_sha256=sha(new_rsrc.encode()),
        condition_added='WORD write to 3c0006 classified as region video (like 3c0000 size 2/4, 3c0004 size 2); replay asserts it',files_edited=[])
    fc.Observer=U5Observer;mt.replay=rns['replay']


# ----------------------------------------------------------------------------------
# Contract tables
# ----------------------------------------------------------------------------------
U5_CODE_RANGES=((0x3d7e,0x3db2),(0x16fee,0x16ff8),(0x19772,0x197da),(0x19e60,0x19e64),(0x1a086,0x1a08e),(0x1a09e,0x1a0a6),(0x1a0b6,0x1a26a),(0x1a40e,0x1a414),(0x1a470,0x1a526),(0xe89fa,0xe8a0c),(0x43e08,0x43e34))
U5_DATA_RANGES=((0x1a08e,0x1a09e),(0x1a0a6,0x1a0b6))
SLOTS=tuple(range(0x1a0bc,0x1a10c,4))                      # the 20 BRA.W slots of the computed JMP at 1a0b8
EXTRA_LEADERS=SLOTS+(0x43e22,)                              # 43e22 is reached only by JMP.L (16ff2, 197d4)
BB_ENTRIES=(0x18c06,0x197da,0x19802,0x8da2,0x43ffc,0x17012,0x1701a,0x28ae,0x43e38)
BB_NAMES={0x18c06:'motion-dispatch-18c06',0x197da:'scene-core-197da',0x19802:'scene-core-19802',0x8da2:'palette-bind-8da2',0x43ffc:'scene-43ffc',0x17012:'map-transfer-17012',0x1701a:'scene-1701a',0x28ae:'fade-card-28ae',0x43e38:'cleanup-43e38'}
LOOP2=(0x1a26a,0x1a276,0x1a278,0x1a284,0x1a28a,0x1a292,0x1a296,0x1a29c,0x1a442,0x1a44e,0x1a450,0x1a45a,0x1a45c,0x1a464,0x1a466,0x1a46a)      # U2 gate blocks around the two U5 entries (model blocks reused from the U2 observer)
ENTRY_SCRIPT=0x1a0b6
ENTRY_PLACE=0x1a470
PROBE_STOP=0x3ffffe


def in_ranges(pc,ranges):return any(lo<=pc<hi for lo,hi in ranges)
def in_u5(pc):return in_ranges(pc,U5_CODE_RANGES)


def parse_contract_table(program):
    rows=[];code=[];data=[]
    pattern=re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)`(\([^)]*\))? \| (\d+) \| `([0-9a-f]+)` \|')
    for line in CONTRACT.read_text().splitlines():
        m=pattern.match(line)
        if not m:continue
        lo,hi=int(m.group(1),16),int(m.group(2),16);size=int(m.group(4));raw=m.group(5)
        ok=program[lo:hi].hex()==raw and hi-lo==size
        assert ok,(hex(lo),hex(hi))
        is_data=bool(m.group(3))
        rows.append(dict(range='%x..%x'%(lo,hi),note=m.group(3) or '',size=size,bytes_equal_to_rom=ok,is_data=is_data))
        (data if is_data else code).append((lo,hi))
    assert sorted(code)==sorted(U5_CODE_RANGES) and sorted(data)==sorted(U5_DATA_RANGES) and len(rows)==13,(code,data)
    assert sum(h-l for l,h in code)==872
    return rows


def contract_lists():
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{4,5})`',text)]
    lines=CONTRACT.read_text().splitlines();starts=bundled=None
    for i,line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (88개)**'):starts=pcs(lines[i+2])
        if line.startswith('- **묶인 분기 PC (13개'):bundled=pcs(line.split('**:',1)[1])
    assert starts and bundled and (len(starts),len(bundled))==(88,13) and len(set(starts))==88,(len(starts or ()),len(bundled or ()))
    return set(starts),set(bundled)


# ----------------------------------------------------------------------------------
# Independent model: a basic-block machine (transcription of the original instructions; every block ends with exactly one control transfer)
# ----------------------------------------------------------------------------------
class ModelError(Exception):pass
BLK={}
LEADERS=frozenset()
MODEL_LEADERS=frozenset()


def blk(*pcs):
    def deco(fn):
        for pc in pcs:
            assert pc not in BLK,hex(pc);BLK[pc]=fn
        return fn
    return deco


class M5(sc.U2Machine):
    """U2 machine (RAM / ROM / banked reads, ordered RAM writes, PVC bank register writes with the side effects) plus the 3c0006 video port and byte helpers."""
    def __init__(self,program,bank_state,ram,regs,env):
        super().__init__(program,bank_state,ram,regs);self.env=env
    def lead(self,pc):
        assert pc in MODEL_LEADERS,hex(pc)
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)
    def rb(self,off):return self.rd(self.a5(off),1)
    def wb(self,off,v):self.wr(self.a5(off),1,v)
    def video(self,address,size,value):
        assert (address,size)==(0x3c0006,2);self.ports.append((size,address,value&0xffff))
    def addw_mem(self,addr,v):self.wr(addr,2,(self.rd(addr,2)+v)&0xffff)
    def peek(self,a,n):
        """Read without logging (used only to derive the carry of a black box from the original bytes of its dispatch word)."""
        a&=M32
        if a<0x100000:return int.from_bytes(self.prog[a:a+n],'big')
        if a<0x200000:return int.from_bytes(bytes(self.ram[(a+i)&0xffff] for i in range(n)),'big')
        raise ModelError('peek %x'%a)


def nw(M):
    v=M.rd(M.r['a1'],2);M.r['a1']=(M.r['a1']+2)&M32;return v
def nl(M):
    v=M.rd(M.r['a1'],4);M.r['a1']=(M.r['a1']+4)&M32;return v
def nb1(M):
    v=M.rd(M.r['a1'],1);M.r['a1']=(M.r['a1']+1)&M32;return v


def blackbox(M,entry):
    """Existing executor: the entry registers are compared as a leader; the native exit registers, RAM writes and bank changes are replayed.  The return LONG is on the stack
    top (JSR/BSR pushed it, or the caller's return LONG for the JMP/BRA entries); the RTS of the callee pops it.  If the return address is the declared stop of the run (no
    boundary is recorded there), the native outgoing registers are the exit registers."""
    M.lead(entry);env=M.env;k=len(M.leads);nb=env['nb']
    if not (k<=len(nb) and nb[k-1]['pc']==entry):raise ModelError('%s black box: native boundaries do not align at lead %d'%(BB_NAMES[entry],k))
    ret=M.rd(M.r['a7'],4);a7=M.r['a7']
    if k<len(nb):
        if nb[k]['pc']!=ret:raise ModelError('%s black box returned to %x, the model expects %x'%(BB_NAMES[entry],nb[k]['pc'],ret))
        exit_regs=nb[k]['registers']
    else:
        o=env['outgoing']
        if o['pc']!=ret:raise ModelError('%s black box ended at %x, the model expects the return %x'%(BB_NAMES[entry],o['pc'],ret))
        exit_regs=o
    call=env['bb_calls'];env['bb_calls']+=1
    if call>=len(env['bb_groups']):raise ModelError('%s black box: no native event group %d'%(BB_NAMES[entry],call))
    group=env['bb_groups'][call]
    for a,n,v in group['writes']:M.wr(a,n,v);M.writes.pop()
    for bank in group['banks']:M.bank=bank
    if exit_regs['a7']!=(a7+4)&M32:raise ModelError('%s changed the stack depth (native exit A7 %x, entry A7 %x)'%(BB_NAMES[entry],exit_regs['a7'],a7))
    for key in fh.REGN+('a7',):M.r[key]=exit_regs[key]
    env['bb_log'].append(dict(callee=BB_NAMES[entry],call=call,a0_in=nb[k-1]['registers']['a0'],writes=len(group['writes']),bank_changes=len(group['banks'])))
    return ret


def bb_call(M,entry,ret):
    M.push32(ret);return blackbox(M,entry)


def carry_18c06(M):
    """C of 18c06: the dispatcher jumps to 18c0e + WORD 2(A1); the slots 0..21 (word 0..54) BRA to ORI #1,CCR; the slots 22..35 (word 58..8c) to ANDI #fe,CCR (U3 contract bytes)."""
    t=M.peek(M.r['a1']+2,2)
    if t%4 or t>0x8c:raise ModelError('18c06 dispatch word %x is not a slot'%t)
    return 1 if t<0x58 else 0


@blk(0x3d7e)
def b3d7e(M):
    old=M.r['d0']&0xffff;M.lw('d0',old-1)                                              # SUBQ.W #1,D0 (BCC taken when there is no borrow)
    return 0x3d84 if old==0 else 0x3d9c
@blk(0x3d84)
def b3d84(M):
    M.wr(0x104d90,1,0)
    a=M.a5(-0x326f);M.wr(a,1,M.rd(a,1)|8)                                              # BSET.B #3 (read-modify-write)
    M.video(0x3c0006,2,M.rw(-0x3270));return M.rts()
@blk(0x3d9c)
def b3d9c(M):
    M.wr(0x104d90,1,M.r['d0']&0xff)
    a=M.a5(-0x326f);M.wr(a,1,M.rd(a,1)&0xf7)                                           # BCLR.B #3
    M.video(0x3c0006,2,M.rw(-0x3270));return M.rts()
@blk(0x16fee)
def b16fee(M):M.wr(M.r['a0']+0x2c,2,0);return 0x43e22
@blk(0x19772)
def b19772(M):
    M.ww(0x53b8,M.r['d0']&0xffff);M.ww(0x53ba,M.r['d1']&0xffff)
    M.r['d0']=(M.r['d0']&0xffff)<<16;M.r['d1']=(M.r['d1']&0xffff)<<16                  # SWAP D0 ; CLR.W D0 ; SWAP D1 ; CLR.W D1
    M.wl(0x53bc,M.r['d0']);M.wl(0x53c0,M.r['d1']);M.wl(0x53b4,M.r['a1'])
    return 0x197ba if M.r['a1']==0 else 0x19796                                          # CMPA.W #0,A1 ; BEQ
@blk(0x19796)
def b19796(M):
    M.lw('d0',M.rd(M.r['a1']+6,2));M.lw('d1',M.rd(M.r['a1']+8,2))
    M.env['carry_18c06']=carry_18c06(M);return bb_call(M,0x18c06,0x197a2)
@blk(0x197a2)
def b197a2(M):
    c=M.env['carry_18c06'];nxt=M.env['nb'][len(M.leads)]['pc'] if len(M.leads)<len(M.env['nb']) else None
    M.env.setdefault('carry_checks',[]).append(dict(model_carry=c,native_successor=nxt))
    return 0x197b2 if c==0 else 0x197a6                                                  # BCC consumes the C returned by 18c06
@blk(0x197a6)
def b197a6(M):
    M.addw_mem(M.a5(0x53ba),M.r['d0']&0xffff);M.addw_mem(M.a5(0x53c0),M.r['d1']&0xffff);return 0x197ba
@blk(0x197b2)
def b197b2(M):
    M.addw_mem(M.a5(0x53b8),M.r['d0']&0xffff);M.addw_mem(M.a5(0x53bc),M.r['d1']&0xffff);return 0x197ba
@blk(0x197ba)
def b197ba(M):
    d0=(-M.rl(0x53bc))&M32;d1=(-M.rl(0x53c0))&M32;d1=(d1+0x01000000)&M32
    M.r['d0']=d0;M.r['d1']=d1;M.r['a0']=M.a5(0x538e);M.r['a1']=0;return 0x43e22
@blk(0x19e60)
def b19e60(M):M.wr(M.r['a1'],4,M.r['a2']);return M.rts()
@blk(0x1a086)
def b1a086(M):M.r['a0']=M.rd((0x1a08e+sx16(M.r['d7']))&M32,4);return M.rts()       # MOVEA.L 6(PC,D7.W): PC + 2 + 6 = 1a08e
@blk(0x1a09e)
def b1a09e(M):M.r['a1']=M.rd((0x1a0a6+sx16(M.r['d7']))&M32,4);return M.rts()
@blk(0x1a0b6)
def b1a0b6(M):
    M.lw('d7',nw(M));return (0x1a0bc+sx16(M.r['d7']))&M32                              # JMP 2(PC,D7.W): PC + 2 + 2 = 1a0bc, no range check
for _slot,_target in zip(SLOTS,(0x1a174,0x1a192,0x1a1c2,0x1a116,0x1a10c,0x1a1d0,0x1a1fa,0x1a20a,0x1a222,0x1a230,0x1a242,0x1a248,0x1a11c,0x1a12e,0x1a146,0x1a150,0x1a156,0x1a15e,0x1a168,0x1a16e)):
    def _mk(t):
        def f(M):return t
        return f
    BLK[_slot]=_mk(_target)
@blk(0x1a10c)
def b1a10c(M):
    M.r['a0']=nl(M);M.r['a0']=M.rd(M.r['a0'],4);return 0xe89fa
@blk(0xe89fa)
def be89fa(M):return 0xe8a06 if M.r['a0']!=0 else 0xe8a02
@blk(0xe8a02)
def be8a02(M):M.r['a0']=0xe89ec;return 0xe8a06
@blk(0xe8a06)
def be8a06(M):M.wl(0x5e2a,M.r['a0']);return M.rts()
@blk(0x1a116)
def b1a116(M):M.r['a0']=nl(M);return 0x1a40e
@blk(0x1a40e)
def b1a40e(M):M.wl(0x540e,M.r['a0']);return M.rts()
@blk(0x1a11c)
def b1a11c(M):
    for off in (0x5426,0x5428,0x542a,0x542c):M.ww(off,nw(M))
    return M.rts()
@blk(0x1a12e)
def b1a12e(M):
    M.lw('d0',nw(M));d=M.r['d0']&0xffff;M.lw('d0',((d<<1)|(d>>15))&0xffff);M.lw('d0',M.r['d0']&3)         # ROL.W #1 ; ANDI.W #3
    M.lb('d1',M.rb(0x53cc));M.lb('d1',M.r['d1']&0xfc);M.lb('d1',(M.r['d1']&0xff)|(M.r['d0']&0xff));M.wb(0x53cc,M.r['d1']&0xff);return M.rts()
@blk(0x1a146)
def b1a146(M):M.wl(0x53fc,nl(M));M.wl(0x5400,nl(M));return M.rts()
@blk(0x1a150)
def b1a150(M):M.ww(0x5432,nw(M));return M.rts()
@blk(0x1a156)
def b1a156(M):M.lw('d0',nw(M));return 0x3d7e
@blk(0x1a15e)
def b1a15e(M):M.ww(0x542e,nw(M));M.ww(0x5430,nw(M));return M.rts()
@blk(0x1a168)
def b1a168(M):M.ww(0x543c,nw(M));return M.rts()
@blk(0x1a16e)
def b1a16e(M):M.wl(0x5434,nl(M));return M.rts()
@blk(0x1a174)
def b1a174(M):
    M.lw('d0',nw(M));M.lw('d1',nw(M));M.r['a2']=nl(M);M.push32(M.r['a1']);M.r['a1']=M.r['a2'];return M.call(0x19772,0x1a182)
@blk(0x1a182)
def b1a182(M):return bb_call(M,0x197da,0x1a186)
@blk(0x1a186)
def b1a186(M):
    M.ww(0x541e,M.r['d7']&0xffff);M.ww(0x5420,M.r['d7']&0xffff);M.r['a1']=M.pop32();return M.rts()
@blk(0x1a192)
def b1a192(M):
    M.lw('d0',nw(M));M.ww(-0x7ff0,0);M.port(0x2ffff2,0x1000);M.port(0x2ffff0,0)
    M.r['a0']=M.rd(0x20000c,4)                                                          # read behind the bank write: the live bank is 1000 (physical 200000)
    M.lw('d0',(M.r['d0']<<2)&0xffff);M.r['a0']=M.rd((M.r['a0']+sx16(M.r['d0']))&M32,4)
    M.push32(M.r['a1']);return bb_call(M,0x8da2,0x1a1be)
@blk(0x1a1be,0x1a1cc,0x1a1f6,0x1a23e)
def bpop_a1_rts(M):M.r['a1']=M.pop32();return M.rts()
@blk(0x1a1c2)
def b1a1c2(M):
    M.r['a0']=nl(M);M.push32(M.r['a1']);return bb_call(M,0x43ffc,0x1a1cc)
@blk(0x1a1d0)
def b1a1d0(M):M.lw('d7',nw(M));return M.call(0x1a086,0x1a1d6)
@blk(0x1a1d6)
def b1a1d6(M):
    M.r['d0']=0;M.r['d1']=0;M.lw('d0',nw(M));M.lw('d1',nw(M));M.r['d0']=swap(M.r['d0']);M.r['d1']=swap(M.r['d1'])
    M.r['d0']=add32(M.r['d0'],M.rl(0x538e))[0];M.r['d1']=add32(M.r['d1'],M.rl(0x5392))[0]
    M.push32(M.r['a1']);M.r['a1']=0;return M.call(0x16fee,0x1a1f6)
@blk(0x1a1fa)
def b1a1fa(M):M.lw('d7',nw(M));return M.call(0x1a086,0x1a200)
@blk(0x1a200)
def b1a200(M):
    M.wr(M.r['a0']+0x28,2,nw(M));M.wr(M.r['a0']+0x2a,2,nw(M));return M.rts()
@blk(0x1a20a)
def b1a20a(M):M.lw('d7',nw(M));return M.call(0x1a086,0x1a210)
@blk(0x1a210)
def b1a210(M):return 0x1a21c if nw(M)==0 else 0x1a216                                   # TST.W (A1)+ ; BEQ
@blk(0x1a216)
def b1a216(M):return blackbox(M,0x17012)                                                 # JMP 17012: its RTS pops the caller's return LONG
@blk(0x1a21c)
def b1a21c(M):return blackbox(M,0x1701a)
@blk(0x1a222)
def b1a222(M):
    M.lb('d7',M.rb(0x540c));M.lb('d7',M.r['d7']&nb1(M));M.lb('d7',M.r['d7']|nb1(M));M.wb(0x540c,M.r['d7']&0xff);return M.rts()
@blk(0x1a230)
def b1a230(M):
    M.lw('d7',nw(M));M.r['a2']=nl(M);M.push32(M.r['a1']);return M.call(0x1a09e,0x1a23a)
@blk(0x1a23a)
def b1a23a(M):return M.call(0x19e60,0x1a23e)
@blk(0x1a242)
def b1a242(M):M.ww(0x5416,nw(M));return M.rts()
@blk(0x1a248)
def b1a248(M):
    w=nw(M);M.lw('d0',w);return 0x1a252 if w&0x8000==0 else 0x1a24e                      # BPL
@blk(0x1a24e)
def b1a24e(M):M.lw('d0',0x7fff);return 0x1a252
@blk(0x1a252)
def b1a252(M):
    M.ww(0x5416,M.r['d0']);M.ww(0x541e,M.r['d0']);M.lw('d0',sub16(M.r['d0'],nw(M))[0]);M.ww(0x5420,M.r['d0'])
    M.lw('d0',nw(M));M.wl(0x5422,M.r['a1']);M.r['a1']=(M.r['a1']+sx16(M.r['d0']))&M32;return M.rts()
@blk(0x1a470)
def b1a470(M):
    M.r['d7']=0;M.lw('d7',M.rd(M.r['a0'],2));M.lw('d0',M.rd(M.r['a0']+4,2));M.lw('d1',M.rd(M.r['a0']+6,2))
    M.r['d0']=swap(M.r['d0']);M.r['d1']=swap(M.r['d1']);return bb_call(M,0x19802,0x1a484)
@blk(0x1a484)
def b1a484(M):
    M.r['d0']=swap(M.r['d0']);M.r['d1']=swap(M.r['d1']);M.r['d7']=swap(M.r['d7'])
    r,n,z,v,c=sub16(M.r['d7'],M.rw(0x5418))                                              # CMP.W 5418(A5),D7 ; BCC (D7 as returned by 19802, upper word after SWAP)
    M.env.setdefault('due_checks',[]).append(dict(d7_word=M.r['d7']&0xffff,phase=M.rw(0x5418),record_time=M.peek(M.r['a0'],2),due=c==0))
    return 0x1a492 if c else 0x1a4da
@blk(0x1a492)
def b1a492(M):
    M.r['d2']=0;M.r['d3']=0;M.r['a1']=M.rd(M.r['a0']+8,4);return 0x1a4a2 if M.r['a1']!=0 else 0x1a4a6
@blk(0x1a4a2)
def b1a4a2(M):M.r['d2']=nl(M);M.r['d3']=nl(M);return 0x1a4a6
@blk(0x1a4a6)
def b1a4a6(M):
    M.lw('d2',add16(M.r['d2'],M.r['d1'])[0]);M.lw('d2',sub16(M.r['d2'],M.rw(0x53a6))[0])
    r,n,z,v,c=sub16(M.r['d2'],M.rw(0x53f8));return 0x1a51c if (z==0 and n==v) else 0x1a4b4          # BGT
@blk(0x1a4b4)
def b1a4b4(M):
    M.lw('d2',add16(M.r['d2'],M.r['d3'])[0]);r,n,z,v,c=sub16(M.r['d2'],M.rw(0x53f6));return 0x1a51c if n!=v else 0x1a4be        # BLT
@blk(0x1a4be)
def b1a4be(M):
    M.r['d2']=swap(M.r['d2']);M.r['d3']=swap(M.r['d3'])
    M.lw('d2',add16(M.r['d2'],M.r['d0'])[0]);M.lw('d2',sub16(M.r['d2'],M.rw(0x53a6))[0])       # the original subtracts 53a6 (the Y cell) here too
    r,n,z,v,c=sub16(M.r['d2'],M.rw(0x53f4));return 0x1a51c if (z==0 and n==v) else 0x1a4d0
@blk(0x1a4d0)
def b1a4d0(M):
    M.lw('d2',add16(M.r['d2'],M.r['d3'])[0]);r,n,z,v,c=sub16(M.r['d2'],M.rw(0x53f2));return 0x1a51c if n!=v else 0x1a4da
@blk(0x1a4da)
def b1a4da(M):
    M.push32(M.r['a0']);M.push16(M.r['d0']);M.push16(M.r['d1']);M.r['a0']=M.rd(M.r['a0']+0xc,4);M.lw('d0',0)
    return bb_call(M,0x28ae,0x1a4ee)
@blk(0x1a4ee)
def b1a4ee(M):
    M.lw('d1',M.pop16());M.lw('d0',M.pop16());M.env.setdefault('a0_after_28ae',[]).append(M.r['a0']);M.r['a0']=(M.r['a0']+0x2e)&M32;M.r['a1']=M.a5(0x538e);return M.call(0x43e08,0x1a500)
@blk(0x43e08)
def b43e08(M):
    M.r['d0']=swap(M.r['d0']);M.r['d1']=swap(M.r['d1']);M.lw('d0',0);M.lw('d1',0)
    a0=M.r['a0'];M.wr(a0+0x10,4,M.r['a1']);M.wr(a0,4,M.r['d0']);M.wr(a0+4,4,M.r['d1']);M.wr(a0+0x24,2,0);return blackbox(M,0x43e38)
@blk(0x43e22)
def b43e22(M):
    a0=M.r['a0'];M.wr(a0+0x10,4,M.r['a1']);M.wr(a0,4,M.r['d0']);M.wr(a0+4,4,M.r['d1']);M.wr(a0+0x24,2,0);return blackbox(M,0x43e38)
@blk(0x1a500)
def b1a500(M):
    M.r['a1']=(M.r['a0']+0x48)&M32;M.r['a0']=M.pop32();M.lw('d0',M.rd(M.r['a0']+2,2));M.r['a0']=(M.r['a0']+0x10)&M32
    return 0x1a51a if M.r['d0']&0xffff==0 else 0x1a514
@blk(0x1a514)
def b1a514(M):
    w=M.rd(M.r['a0'],2);M.r['a0']=(M.r['a0']+2)&M32;M.wr(M.r['a1'],2,w);M.r['a1']=(M.r['a1']+2)&M32
    M.lw('d0',sub16(M.r['d0'],2)[0]);return 0x1a514 if M.r['d0']&0xffff else 0x1a51a
@blk(0x1a51a)
def b1a51a(M):return M.rts()
@blk(0x1a51c)
def b1a51c(M):
    M.lw('d0',M.rd(M.r['a0']+2,2));M.r['a0']=(M.r['a0']+0x10+sx16(M.r['d0']))&M32;return M.rts()


def block_for(pc):
    fn=BLK.get(pc)
    if fn is None and pc in LOOP2:fn=sc.BLK.get(pc)
    return fn


def run_blocks(M,pc,stop):
    """Run the block machine from `pc` until the next PC is `stop` (not executed) or a PC without a block; returns the final PC."""
    steps=0
    while pc!=stop:
        if pc&1:raise ModelError('odd PC %x'%pc)
        fn=block_for(pc)
        if fn is None:return pc
        M.lead(pc);pc=fn(M);steps+=1
        if steps>3000000:raise ModelError('model step limit')
    return pc


# ----------------------------------------------------------------------------------
# Configuration, native evidence of the black boxes, model comparison
# ----------------------------------------------------------------------------------
RANGES=();BLOCKS=();CONTRACT_STARTS=set();CONTRACT_BUNDLED=set();U5_LEADERS=frozenset();ALL_EXISTING=()


def configure(program,out_dir):
    global RANGES,BLOCKS,LEADERS,MODEL_LEADERS,CONTRACT_STARTS,CONTRACT_BUNDLED,U5_LEADERS,ALL_EXISTING
    mw.configure3(program,out_dir)                                                      # U2 + U3 observed ranges / leaders / fc globals
    parse_contract_table(program)
    CONTRACT_STARTS,CONTRACT_BUNDLED=contract_lists()
    decoded=set(fh.leaders_of(program,U5_CODE_RANGES))|set(EXTRA_LEADERS)
    assert decoded==CONTRACT_STARTS,(sorted(hex(x) for x in decoded-CONTRACT_STARTS),sorted(hex(x) for x in CONTRACT_STARTS-decoded))
    assert not (CONTRACT_BUNDLED&decoded),sorted(hex(x) for x in CONTRACT_BUNDLED&decoded)
    U5_LEADERS=frozenset(decoded)
    missing=sorted(hex(pc) for pc in U5_LEADERS if pc not in BLK);assert not missing,'model has no block for %s'%missing
    extra=sorted(hex(pc) for pc in BLK if pc not in U5_LEADERS);assert not extra,'model has blocks that are not leaders %s'%extra
    assert all(pc in sc.BLK for pc in LOOP2),[hex(pc) for pc in LOOP2 if pc not in sc.BLK]
    LEADERS=frozenset(U5_LEADERS)
    MODEL_LEADERS=frozenset(U5_LEADERS|set(BB_ENTRIES)|set(LOOP2))
    BLOCKS=tuple(sorted(MODEL_LEADERS))
    ALL_EXISTING=tuple(dict.fromkeys(tuple(sc.RANGES)+su.U4_RANGES+(su.INIT_CALL,)+su.EXISTING_RANGES+FC_RANGES_ORIGINAL))
    RANGES=ALL_EXISTING+U5_CODE_RANGES
    fc.OUT=out_dir;fc.RANGES=RANGES;fc.BOUNDARIES=BLOCKS;fc.KEY_PCS=tuple(sorted(MODEL_LEADERS|set(sc.BOUNDARIES_U2)))
    fh.OUT=out_dir;fh.POOL.clear()
    LOOP2_INSTR.clear()
    for lo,hi in LOOP2_RANGES:LOOP2_INSTR.update(r['cpu_address'] for r in disassemble_range(program,lo,hi-lo,lo))
    for lo,hi in U5_CODE_RANGES:assert not any(lo<=pc<hi for pc in (0x1a296,0x1a46a,0x1a43c)),hex(lo)


def stop_evidence5(program,p,origin=None):
    """A stop is accepted only directly after the RTS that popped the declared return LONG (or for the zero step)."""
    origin=origin or p
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(outgoing_pc=pc,previous_pc=None,is_step_stop=True,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];ram=p['ram_after'];a7=o['a7'];inc=origin['incoming']
    if pc in sc.BOUNDARY_BSR and program[prev:prev+2].hex()=='6100':return sc.stop_evidence(program,p)       # natural chain: 1a0b6 / 1a470 directly after the BSR.W
    assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    assert u32(ram,a7-4)==pc,(p['label'],hex(u32(ram,a7-4)))                                 # the popped return LONG still lies below A7
    assert u32(origin['ram_before'],inc['a7'])==pc or (pc==RETURN_FF000 and a7==fc.S+4 and u32(origin['ram_before'],fc.S)==pc),(p['label'],'the stop is not the return LONG on top of the declared entry stack',hex(pc))
    on_stack=[off for off in range(0,64,4) if u32(origin['ram_before'],inc['a7']+off)==pc]
    return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes='4e75',is_step_stop=True,return_long_on_stack_at_entry_offsets=on_stack,entry_a7=inc['a7'],
        reached_from='RTS at %x popped the return LONG %x (A7 after = %x; the LONG was on the declared stack at entry offset %s); %x is never executed'%(prev,pc,a7,on_stack[:1],pc))


def annotate(program,phases):
    first={}
    for p in phases:first.setdefault(p['step'],p)
    for p in phases:p['stop_evidence']=stop_evidence5(program,p,first[p['step']])


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


def partition(p):
    """Native evidence of the existing executors in one control phase.  nb: the boundary list without the interior of the black boxes (nested leaders have a deeper A7);
    groups: one event group per black-box call (consecutive instructions outside the unit), built from the executed instruction sequence (the number of data events of an
    instruction is fixed by its encoding): ordered RAM writes and PVC bank changes."""
    nb=[];skip=None
    for b in p['boundaries']:
        if skip is not None:
            if b['registers']['a7']==(skip+4)&M32 and b['pc'] in MODEL_LEADERS and b['pc'] not in BB_ENTRIES:skip=None;nb.append(b)
            continue
        nb.append(b)
        if b['pc'] in BB_ENTRIES:skip=b['registers']['a7']
    pcs=p['pcs'][:-1];events=p['events'];exec_count=collections.Counter(pcs);event_count=collections.Counter(e['pc'] for e in events)
    per={}
    for pc,n in event_count.items():
        if n%exec_count[pc]:raise ModelError('instruction %x has %d events in %d executions'%(pc,n,exec_count[pc]))
        per[pc]=n//exec_count[pc]
    groups=[];cur=None;idx=0
    for pc in pcs:
        n=per.get(pc,0);chunk=events[idx:idx+n];idx+=n
        if in_u5(pc) or pc in LOOP2_INSTR:cur=None;continue
        if cur is None:cur=dict(writes=[],banks=[],events=0,pcs=set());groups.append(cur)
        cur['pcs'].add(pc);cur['events']+=len(chunk)
        for e in chunk:
            if e['region']=='ram' and e['access']=='write':cur['writes'].append((e['address'],e['size'],int(e['bytes'],16)))
            elif e['region']=='pvc' and e['access']=='write':cur['banks'].append(e['bank_after'])
    if idx!=len(events):raise ModelError('event segmentation consumed %d of %d events'%(idx,len(events)))
    return nb,groups


LOOP2_INSTR=set()
LOOP2_RANGES=((0x1a26a,0x1a29e),(0x1a442,0x1a470))


def event_pc_in_unit(pc):return in_u5(pc) or pc in LOOP2_INSTR


def run_model(program,p,stop):
    nb,groups=partition(p)
    env=dict(nb=nb,bb_groups=groups,bb_calls=0,bb_log=[],outgoing=p['outgoing'])
    M=M5(program,(p['bank_before'],p['ff8_before'],p['ff9_before']),p['ram_before'],p['incoming'],env)
    final=run_blocks(M,p['incoming']['pc'],stop)
    M.r['pc']=final
    if env['bb_calls']!=len(groups):raise ModelError('model called %d black boxes, native has %d groups'%(env['bb_calls'],len(groups)))
    return M,nb


def check_model(program,spec,control):
    stop=spec['steps'][-1]['stop_pc'];row=dict(label=spec['label'],kind='script-placement-model')
    phases=[q for q in control if q['step']==len(spec['steps'])-1];assert len(phases)==1
    p=phases[0]
    try:M,nb=run_model(program,p,stop)
    except (ModelError,fh.ModelError,fh.StopAt,KeyError,AssertionError,IndexError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=spec['label'],kind='model-could-not-follow-native',detail=repr(e)));return row
    o=p['outgoing'];bad=[]
    if M.r['pc']!=stop:bad.append(dict(what='model final PC',model=hex(M.r['pc']),native=hex(o['pc'])))
    if len(M.leads)!=len(nb):bad.append(dict(what='leader count',model=len(M.leads),native=len(nb)))
    for i,(m,n) in enumerate(zip(M.leads,nb)):
        got=dict(n['registers'])
        if m!=got:
            bad.append(dict(what='leader %d'%i,model_pc=hex(m['pc']),native_pc=hex(got['pc']),differing_registers={k:(hex(m[k]),hex(got[k])) for k in m if m[k]!=got.get(k)}));break
    ram_writes=[(e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region']=='ram' and e['access']=='write' and event_pc_in_unit(e['pc'])]
    if M.writes!=ram_writes:
        first=next((i for i,(a,b) in enumerate(zip(M.writes,ram_writes)) if a!=b),min(len(M.writes),len(ram_writes)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(ram_writes),first_difference=first,model=M.writes[first:first+3],native=ram_writes[first:first+3]))
    ports=[(e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write' and event_pc_in_unit(e['pc'])]
    if M.ports!=ports:bad.append(dict(what='ordered port writes',model=M.ports[:6],native=ports[:6],model_count=len(M.ports),native_count=len(ports)))
    reads=[(e['address'],e['size'],e['region']) for e in p['events'] if e['region'] in ('fixed','bank') and e['access']=='read' and event_pc_in_unit(e['pc'])]
    if M.rom_reads!=reads:bad.append(dict(what='ordered fixed/bank reads',model=M.rom_reads[:6],native=reads[:6],model_count=len(M.rom_reads),native_count=len(reads)))
    final=dict(M.r)
    if final!={k:o[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(o[k])) for k in final if final[k]!=o[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    if M.bank!=p['modeled_bank']:bad.append(dict(what='bank',model=hex(M.bank),native=hex(p['modeled_bank'])))
    entry_a7=p['incoming']['a7']
    stack_writes=[e['address'] for e in p['events'] if e['region']=='ram' and e['access']=='write' and e['address']>=0x1f0000]
    native_depth=(entry_a7-min(stack_writes)) if stack_writes else 0
    unit_depth=max([(entry_a7-m['a7'])&M32 for m in M.leads] or [0])
    carry=[dict(c) for c in M.env.get('carry_checks',())]
    row.update(equal=not bad,leaders=len(M.leads),leader_pcs_distinct=len({m['pc'] for m in M.leads}),ordered_ram_writes=len(M.writes),ordered_port_writes=len(M.ports),ordered_rom_reads=len(M.rom_reads),
        ram_bytes_compared=0x10000,final_registers_compared=sorted(final),blackbox=M.env['bb_log'],model_leader_pcs=sorted({hex(m['pc']) for m in M.leads}),final_bank=hex(M.bank),
        unit_stack_depth=unit_depth,native_stack_depth=native_depth,carry_18c06=carry,a0_after_28ae=list(M.env.get('a0_after_28ae',())),due_checks=[dict(c) for c in M.env.get('due_checks',())],mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=spec['label'],kind='model-vs-native',mismatches=bad[:4]))
    return row


# ----------------------------------------------------------------------------------
# Captured declared entry states of the ORIGINAL runs (RAM, 14 registers, A7, live stack bytes, PVC register words)
# ----------------------------------------------------------------------------------
CAP_PCS=(0x1a0b6,0x1a470,0x1a26a,0x1a442)


class Capture:
    """Every hit of the given PCs in the original uninterrupted runs of an original observer (scene_frame_execution / scene_general_initialization)."""
    def __init__(self,obs,mod,pcs):
        self.obs=obs;self.mod=mod;self.hits=collections.Counter();self.states=[];self.case=None
        for pc in pcs:obs.cpu.hook_add(UC_HOOK_CODE,self.hit,begin=pc,end=pc)
    def reset(self,case):self.hits.clear();self.case=case
    def hit(self,cpu,address,size,user):
        mod=self.mod;a7=cpu.reg_read(mod.m.UC_M68K_REG_A7);self.hits[address]+=1
        regs={k:cpu.reg_read(r)&M32 for k,r in zip(mod.KEYS,mod.REGS)}
        st=dict(pc=address,hit=self.hits[address],case=self.case,ram=bytes(cpu.mem_read(mod.BASE,0x10000)),regs=regs,a7=a7,stack=bytes(cpu.mem_read(a7,mod.STACK+4-a7)),bank=self.obs.bank,
            pvc_raw=su.last_pvc_words(self.obs.ports),instruction=self.obs.instructions,ports=len(self.obs.ports),ret=int.from_bytes(cpu.mem_read(a7,4),'big'))
        base=regs['a1'] if address==0x1a0b6 else regs['a0']
        try:st['peek']=bytes(cpu.mem_read(base,0x40)) if address in (0x1a0b6,0x1a470) else b''
        except unicorn.UcError:st['peek']=b''
        st['peek_base']=base;self.states.append(st)


def state_fx(name,st,prov,role=None):
    raw8,raw9=st['pvc_raw'];bank,ff8,ff9=pvc_bank_update(raw8,raw9);assert bank==st['bank'],(name,hex(bank),hex(st['bank']))
    return sc.make_fx(name,st['ram'],st['regs'],((bank,ff8,ff9),sc.pvc_page(raw8,raw9)),st['pc'],st['a7'],prov,(),[(st['a7'],st['stack'])],
        role=role or 'declared entry at %x (hit %d of case %s) from the original run: RAM, 14 registers, A5 = 108000, A7 = %x and the %d live stack bytes (return LONG %x); PVC bank %x, raw bank words %x / %x'%(
            st['pc'],st['hit'],st['case'],st['a7'],len(st['stack']),st['ret'],bank,raw8,raw9))


def state_prov(kind,st,extra=None):
    d=dict(kind=kind,case=st['case'],pc=hex(st['pc']),hit=st['hit'],instruction=st['instruction'],ram_sha256=sha(st['ram']),a7=hex(st['a7']),return_long=hex(st['ret']),stack_hex=st['stack'].hex(),
        registers={k:hex(v) for k,v in st['regs'].items()},bank=hex(st['bank']),pvc_raw_words=[hex(x) for x in st['pvc_raw']])
    if extra:d.update(extra)
    return d


def scene_inputs_checked(program):
    scene_obs,scene_in=sc.scene_inputs(program)
    return scene_obs,scene_in


def capture_scene(program,scene_in):
    obs=sfe.Observer(program);cap=Capture(obs,sfe,CAP_PCS);recorded=[]
    for i,(row,ram,regs) in enumerate(scene_in):
        cap.reset(i)
        output,result,ports,info=obs.run(ram,[regs[k] for k in KEYS14])
        assert info['returned'] and info['error'] is None and sha(output)==row['ram_sha256'] and sha(ports)==row['ports_sha256'] and info['instructions']==row['instructions'],i
        recorded.append(dict(case=i,instructions=info['instructions']))
    return cap.states


def init_inputs(program):
    """The 221 scene_general_initialization inputs: (row, input RAM, 14 registers).  Rebuilt by the original observer module (2790 / 3ef2 seed + the case fixture), or from the
    previous recorded native output for carried sequences; every RAM is checked against the recorded input_ram_sha256."""
    obs=json.loads(sc.pin(sc.SCENE_SEED,sc.SCENE_SEED_SHA));folder=sc.SCENE_SEED.parent;out=[]
    assert obs['cases']==obs['completed_cases']==len(obs['results'])==221 and obs['failure'] is None
    for index,row in enumerate(obs['results']):
        case=row['fixture']
        if case.get('sequence_position',0)>0:
            prev=obs['results'][index-1];assert prev['fixture'].get('sequence')==case['sequence']
            ram=bytearray(sc.pin(folder/prev['ram_file'],prev['ram_sha256']))
        else:ram=sgi.fixture(program,case)
        assert sha(ram)==row['input_ram_sha256'],index
        out.append((row,bytes(ram),[row['incoming'][k] for k in sgi.KEYS]))
    return obs,out


def capture_init(program,init_in):
    obs=sgi.Observer(program);cap=Capture(obs,sgi,CAP_PCS)
    for i,(row,ram,regs) in enumerate(init_in):
        cap.reset(i)
        output,result,ports,info=obs.run(ram,regs)
        assert info['returned'] and info['error'] is None and sha(output)==row['ram_sha256'] and sha(ports)==row['ports_sha256'] and info['instructions']==row['instructions'],i
    return cap.states


# ----------------------------------------------------------------------------------
# Condition builder
# ----------------------------------------------------------------------------------
def spec_for(label,group,prov,fx,setup,stop,guard,checkpoints=(),delta=4):
    fx=dict(fx);fx['label']=label
    steps=[dict(label=label,changes=list(setup),stop_pc=stop,checkpoints=list(checkpoints),a7=('entry',delta))]
    extra=dict(guarded=True,guard=guard) if guard is not None else {}
    return dict(label=label,group=group,fixture=fx,steps=steps,provenance=prov,**extra)


def stop_of(fx):return u32(fx['ram'],fx['initial_a7'])


class Builder:
    def __init__(self,program):
        self.program=program;self.specs=[];self.models=[];self.census={}
    def probe(self,label,group,prov,fx,setup,stop,delta):
        spec=spec_for(label,group,prov,fx,setup,stop,None,(),delta)
        try:return fc.run_condition(self.program,spec,True)
        except Exception as e:
            diag=copy.deepcopy(spec);diag['guarded']=True;diag['guard']={}
            try:last=fc.run_condition(self.program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
            except Exception as e2:info=repr(e2)
            raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(label,e,info))
    def add(self,label,group,prov,fx,setup=(),stop=None,guard=None,model=True,delta=None):
        fx=dict(fx);fx['label']=label
        if stop is None:stop=stop_of(fx)
        if delta is None:delta=0 if stop==fx['entry_pc'] else 4
        if guard is not None:
            spec=spec_for(label,group,prov,fx,setup,stop,guard,(),delta);self.specs.append(spec);return spec
        phases=self.probe(label,group,prov,fx,setup,stop,delta)
        last=phases[-1];pcs=last['pcs'];entry=pcs[0];order=[];zero=stop==fx['entry_pc']
        if not zero:
            for pc in pcs[1:]:
                if pc in MODEL_LEADERS and pc not in order and pc!=entry and pc!=pcs[-1]:order.append(pc)
        spec=spec_for(label,group,prov,fx,setup,stop,None,order,delta)
        self.census[label]=dict(instructions=len(pcs)-1,leaders=set(pc for pc in pcs if pc in U5_LEADERS),outgoing_a7=last['outgoing']['a7'],final_pc=last['outgoing']['pc'])
        self.specs.append(spec)
        if model and not zero:self.models.append(label)
        return spec


def _add_auto(self,label,group,prov,fx,setup=(),stop=None,delta=None,model=True):
    """Exploratory condition: a normal observation if the original completes, otherwise a guarded condition whose expected guard is the one the native run reports (recorded as
    observed, not predicted)."""
    try:return self.add(label,group,prov,fx,setup=setup,stop=stop,model=model,delta=delta)
    except AssertionError as e:
        fx=dict(fx);fx['label']=label
        if stop is None:stop=stop_of(fx)
        if delta is None:delta=0 if stop==fx['entry_pc'] else 4
        diag=spec_for(label,group,prov,fx,setup,stop,{},(),delta)
        g=fc.run_condition(self.program,diag,True)[-1]['guard']
        assert g is not None,(label,str(e)[:300])
        expected={k:g[k] for k in ('problem','pc','address','size','target','access') if k in g}
        spec=spec_for(label,'observed-guard',prov,fx,setup,stop,expected,(),delta);spec['observed_guard_not_predicted']=True
        self.specs.append(spec);return spec
Builder.add_auto=_add_auto


CENSUS_MODEL=dict(runs=0,equal=0,unequal=[],model_errors=[])


def census_run(program,label,fx,stop,delta=4,setup=()):
    """One continuous native run of a captured state, compared with the model (no artifacts stored)."""
    spec=spec_for(label,'census',{},fx,setup,stop,None,(),delta)
    phases=fc.run_condition(program,spec,True);p=phases[-1];pcs=p['pcs']
    row=check_model(program,spec,phases)
    CENSUS_MODEL['runs']+=1
    if row['equal']:CENSUS_MODEL['equal']+=1
    elif 'model_error' in row:CENSUS_MODEL['model_errors'].append(dict(label=label,error=row['model_error']))
    else:CENSUS_MODEL['unequal'].append(dict(label=label,mismatches=row['mismatches'][:2]))
    return dict(label=label,instructions=len(pcs)-1,leaders=collections.Counter(pc for pc in pcs if pc in U5_LEADERS),model_equal=row['equal'],blackbox_calls=len(row.get('blackbox',[])),
        unit_stack_depth=row.get('unit_stack_depth'),native_stack_depth=row.get('native_stack_depth'),carry_18c06=row.get('carry_18c06'),due_checks=row.get('due_checks'),a0_after_28ae=row.get('a0_after_28ae'),blackbox_names=[b['callee'] for b in row.get('blackbox',[])],
        bank_after=hex(p['modeled_bank']),ports=[(e['size'],e['address'],e['bytes']) for e in p['events'] if e['region'] in PORT_REGIONS and e['access']=='write' and event_pc_in_unit(e['pc'])],
        ram_writes=sum(1 for e in p['events'] if e['region']=='ram' and e['access']=='write' and event_pc_in_unit(e['pc'])))


# ----------------------------------------------------------------------------------
# Full frame: the direct 1a73c entry of every scene_frame seed to the RTS that pops ff000 (U2 + U3 + U4 + U5 + existing executors, no boundary left)
# ----------------------------------------------------------------------------------
FRAME_LEADERS=frozenset()
FRAME_SCENE=None


def ports_blob(events):
    return b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS and e['access']=='write')


def frame_spec(program,i,row,ram,regs,checkpoints=()):
    prov=sc.scene_prov(i,row,ram)
    fx=sc.direct_fx('frame-%04d'%i,ram,regs,prov)
    return spec_for('frame-%04d'%i,'full-frame',prov,fx,(),RETURN_FF000,None,checkpoints,4)


def compare_recorded(ps,row,ram_in):
    """Native machine-style full frame (one or several consecutive control phases) versus the recorded original (flat-map) run.  The work RAM is mirrored in the machine image,
    so the bytes of the live stack window (the declared stack lives at 1feffc = image offset effc) are not comparable with the flat original; everything else is."""
    folder=sc.SCENE_OBS.parent
    out=sc.pin(folder/row['ram_file'],row['ram_sha256']);rec_ports=sc.pin(folder/row['ports_file'],row['ports_sha256'])
    events=[e for q in ps for e in q['events']];p=ps[-1]
    writes=[e['address'] for e in events if e['region']=='ram' and e['access']=='write' and e['address']>=0x1f0000]
    lo=(min(writes)&0xffff) if writes else 0xf000;lo=min(lo,0xeff0)
    after=p['ram_after'];diff=[k for k in range(0x10000) if after[k]!=out[k] and not (lo<=k<0xf000)]
    window_input_nonzero=sum(1 for k in range(lo,0xf000) if ram_in[k] and not 0xeffc<=k<0xf000)
    o=p['outgoing'];blob=ports_blob(events);instructions=sum(len(q['pcs'])-1 for q in ps)+1
    regs_equal=all(o[k]==row['result'][k] for k in KEYS14)
    return dict(instructions_equal=instructions==row['instructions'],ram_equal_outside_stack_window=not diff,ram_differing_bytes=len(diff),stack_window=[hex(0x100000+lo),hex(0x10f000)],
        stack_window_input_nonzero_bytes=window_input_nonzero,ports_equal=sha(blob)==row['ports_sha256'] and blob==rec_ports,port_count=len(blob)//9,registers_equal=regs_equal,
        bank_equal=p['modeled_bank']==row['final_bank'],final_a7_equal=o['a7']==fc.S+4 and row['final_a7']==fc.S+4,final_pc=hex(o['pc']),first_diff=[(hex(0x100000+k),after[k],out[k]) for k in diff[:6]])


def frame_worker(i):
    try:
        row,ram,regs=FRAME_SCENE[i]
        spec=frame_spec(FRAME_PROGRAM,i,row,ram,regs)
        first=fc.run_condition(FRAME_PROGRAM,spec,True)[-1]
        order=[]
        for pc in first['pcs'][1:-1]:
            if pc in FRAME_LEADERS and pc not in order:order.append(pc)
        spec=frame_spec(FRAME_PROGRAM,i,row,ram,regs,order)
        split,control=run_spec(FRAME_PROGRAM,spec)
        p=control[-1];assert p['guard'] is None
        cmp=compare_recorded([p],row,ram)
        hits=collections.Counter(pc for pc in p['pcs'][:-1] if pc in U5_LEADERS)
        ok=all([cmp['instructions_equal'],cmp['ram_equal_outside_stack_window'],cmp['ports_equal'],cmp['registers_equal'],cmp['bank_equal'],cmp['final_a7_equal']])
        return dict(case=i,family=row['fixture']['family'],ok=ok,reproduced_twice=True,split_phases=len(split),control_phases=len(control),instructions=len(p['pcs'])-1,compare=cmp,
            u5_leader_hits={hex(k):v for k,v in sorted(hits.items())},u5_entries=dict(script=hits.get(0x1a0b6,0),placement=hits.get(0x1a470,0)),stop_evidence=p['stop_evidence'],
            outgoing_ram_sha256=sha(p['ram_after']),ports_sha256=sha(ports_blob(p['events'])),checkpoints=len(order),error=None)
    except Exception as e:
        import traceback
        return dict(case=i,ok=False,error=repr(e)[:600],trace=traceback.format_exc()[-1500:])


FRAME_PROGRAM=None


# ----------------------------------------------------------------------------------
# Declared fixtures: captured states of the original runs + declared host RAM writes / declared initial registers (applied before the first instruction)
# ----------------------------------------------------------------------------------
W=su.W
writes_of=su.writes_of
stream_writes=su.stream_writes
be=su.be
CMD_LEN={0x00:10,0x04:4,0x08:6,0x0c:6,0x10:6,0x14:8,0x18:8,0x1c:6,0x20:4,0x24:8,0x28:4,0x2c:8,0x30:10,0x34:4,0x38:10,0x3c:4,0x40:4,0x44:6,0x48:4,0x4c:6}
AREAS=(0x10e000,0x10e400,0x10e800,0x10dc00,0x10d800,0x10d400)
INIT_ST=[];SCENE_ST=[]
HARV={}


def build_harvest():
    HARV.clear()
    for k,s in enumerate(INIT_ST):
        if s['pc']==0x1a0b6 and len(s['peek'])>=2:HARV.setdefault(int.from_bytes(s['peek'][:2],'big'),[]).append(k)


def example(opcode,bank=None,pred=None,nth=0):
    hits=[INIT_ST[k] for k in HARV[opcode] if (bank is None or INIT_ST[k]['bank']==bank) and (pred is None or pred(INIT_ST[k]))]
    assert len(hits)>nth,(hex(opcode),hex(bank or 0),len(hits))
    return hits[nth]


def zero_area(fx,length,avoid=()):
    ram=fx['ram'];limit=min(fx['initial_a7']&0xffff,0xeff0)
    for base in AREAS:
        a=base&0xffff
        if a+length>limit:continue
        if any(a<hi and lo<a+length for lo,hi in avoid):continue
        if not any(ram[a:a+length]):return base
    raise AssertionError('no zero area of %x bytes in %s'%(length,fx['label']))


def vfx(base,role,regs=None,entry_pc=None,initial_a7=None,bank3=False):
    f=dict(base);f['regs']=dict(base['regs'],**(regs or {}))
    if entry_pc is not None:f['entry_pc']=entry_pc;f['stop_pc']=entry_pc
    if initial_a7 is not None:f['initial_a7']=initial_a7
    if bank3:
        f['bank_state']=sc.BANK3_MID[0];f['pvc']=sc.BANK3_MID[1];f['bank']=3
    f['preparation']=dict(role=role,base=base['label'],declared_initial_registers={k:hex(v) for k,v in (regs or {}).items()},entry_pc=hex(f['entry_pc']),initial_a7=hex(f['initial_a7']),bank3=bank3)
    return f


def base_fx(st,tag):
    return state_fx('base-%s'%tag,st,state_prov('declared entry state of the original run',st))


class Fix:
    """Fixture factory bound to a Builder."""
    def __init__(self,B):self.B=B
    def areas(self,base,lengths):
        out=[];used=[]
        for n in lengths:
            a=zero_area(base,n,used);out.append(a);used.append((a&0xffff,(a&0xffff)+n))
        return out
    def script(self,tag,desc,st,stream,writes=(),regs=None,group='fixture-script',bank3=False,blobs=(),ptrs=None,auto=False,**kw):
        """Entry at 1a0b6 of a captured state with the script stream copied to a RAM area (declared RAM writes, declared initial A1) and optional RAM blobs
        (`ptrs` {stream offset: blob index} writes the blob address as LONG into the stream)."""
        base=base_fx(st,'%s-%x-%d'%(st['case'],st['pc'],st['hit']));stream=bytearray(stream)
        if len(stream)%2:stream+=b'\0'
        blobs=[bytes(b)+(b'\0' if len(b)%2 else b'') for b in blobs]
        areas=self.areas(base,[len(stream)+2]+[len(b)+2 for b in blobs])
        for off,idx in (ptrs or {}).items():stream[off:off+4]=be(4,areas[idx+1])
        role='declared fixture: state at 1a0b6 hit %d of case %s with declared initial A1 = %x (RAM copy of the script command, %d bytes, overrides declared in the step; natural command at %x)'%(st['hit'],st['case'],areas[0],len(stream),st['peek_base'])
        fx=vfx(base,role,dict(a1=areas[0],**(regs or {})),bank3=bank3)
        setup=stream_writes(areas[0],bytes(stream),'script stream for %s'%tag)
        for a,b in zip(areas[1:],blobs):setup+=stream_writes(a,b,'RAM blob for %s'%tag)
        setup+=list(writes)
        label='fixture-%s'%tag
        return (self.B.add_auto if auto else self.B.add)(label,group,desc,fx,setup=setup,**kw)
    def command(self,tag,desc,opcode,patch=None,bank=None,pred=None,nth=0,**kw):
        """Natural command bytes of an init-run example of `opcode`, patched at byte offsets {offset: bytes}."""
        st=example(opcode,bank,pred,nth);raw=bytearray(st['peek'][:CMD_LEN[opcode]])
        for off,val in (patch or {}).items():raw[off:off+len(val)]=val
        return self.script(tag,desc,st,bytes(raw),**kw)


def rom_chain(program,addr):
    """Motion record chain of 10-byte records up to and including the record whose WORD 2 is ffff (the 197da scan terminator)."""
    out=bytearray()
    while True:
        rec=program[addr:addr+10];out+=rec;addr+=10
        if int.from_bytes(rec[2:4],'big')==0xffff:return bytes(out)
        assert len(out)<400


def pick(items,key,per):
    groups=collections.OrderedDict()
    for it in items:groups.setdefault(key(it),[]).append(it)
    out=[]
    for sig,members in groups.items():out+=sc.spread(members,per)
    return out


def le(n,v):return v.to_bytes(n,'big')


def script_fixtures(F,program):
    cm=F.command;sc_=F.script
    nm=lambda s:int.from_bytes(s['peek'][6:10],'big')!=0
    # ---- opcode 00: motion setup (19772 / 197da; 18c06 carry selects the field pair)
    st00=example(0x00,pred=nm);a2=int.from_bytes(st00['peek'][6:10],'big');chain=rom_chain(program,a2)
    cm('op00-motion-null','opcode 00 with operand A2 = 0: 19772 branches to 197ba at once (no 18c06 / 197da side effects of the record)',0x00,{6:le(4,0)},pred=nm)
    for typ in (0x00,0x14,0x54,0x58,0x80,0x8c):
        rec=bytearray(chain);rec[2:4]=le(2,typ)
        cm('op00-ram-chain-type-%02x'%typ,'opcode 00 with a RAM copy of the original record chain %x (%d bytes) whose first record has the dispatch word %02x: 18c06 returns C=%d (word < 58 -> ORI #1,CCR, else ANDI #fe,CCR)'%(a2,len(chain),typ,1 if typ<0x58 else 0),
            0x00,{6:le(4,0)},pred=nm,blobs=[bytes(rec)],ptrs={6:0})
    for typ,(d0,d1) in ((0x14,(0x7fff,0x7fff)),(0x14,(0xffff,0x0001)),(0x80,(0x8000,0x8000)),(0x80,(0xffff,0xffff)),(0x14,(0x0000,0x0000))):
        rec=bytearray(chain);rec[2:4]=le(2,typ);rec[6:8]=le(2,0x7ffe);rec[8:10]=le(2,0x8002)
        cm('op00-deltas-type-%02x-%04x-%04x'%(typ,d0,d1),'opcode 00 with RAM chain type %02x: stream words D0 = %04x, D1 = %04x go to 10d3b8/10d3ba then the record words 7ffe / 8002 are added with WORD wrap to the field pair chosen by C'%(typ,d0,d1),
            0x00,{2:le(2,d0),4:le(2,d1),6:le(4,0)},pred=nm,blobs=[bytes(rec)],ptrs={6:0})
    # ---- opcode 04: bank zero, live 20000c read, LSL.W #2 index
    for idx in (0x0000,0x0001,0x002a,0x004c):
        cm('op04-index-%04x'%idx,'opcode 04 index %04x at bank 1000: WORD 0 -> 100010, bank 1000 / 0 written to the PVC, LONG 20000c read in bank 1000, LSL.W #2, descriptor LONG, 8da2'%idx,0x04,{2:le(2,idx)},bank=0x200000)
    for idx in (0x0000,0x002a,0x004c):
        cm('op04-bank2000-entry-index-%04x'%idx,'opcode 04 index %04x entered with the declared bank 2000 state (PVC words 0 / 2000; no seed enters 1a192 in bank 2000): the three writes make the bank 1000 before the 20000c read'%idx,0x04,{2:le(2,idx)},bank=0x200000,bank3=True,group='fixture-bank')
    for idx in (0x4000,0x8000,0xc000):
        cm('op04-index-%04x-wraps-to-0'%idx,'opcode 04 index %04x: LSL.W #2 keeps only the low WORD (result 0), the same descriptor as index 0'%idx,0x04,{2:le(2,idx)},bank=0x200000)
    for idx in (0x1fff,0x2000,0x6000,0xfffe,0x0100):
        cm('op04-index-%04x-exploratory'%idx,'opcode 04 index %04x: LSL.W #2 -> %04x, sign extended offset %d added to LONG 20000c: observed outcome (table beyond the 77 entries / negative offset)'%(idx,(idx<<2)&0xffff,sx16((idx<<2)&0xffff)),0x04,{2:le(2,idx)},bank=0x200000,auto=True,group='fixture-exploratory')
    # ---- opcode 08 (43ffc)
    cm('op08-ram-copy','opcode 08 natural command copied to RAM (operand LONG = object descriptor of the seed): JSR 43ffc, A1 restored from the stack',0x08)
    cm('op08-ram-copy-2','opcode 08 second natural command (different operand)',0x08,nth=50)
    # ---- opcode 0c: operand LONG to 10d40e
    for tag,val in (('zero',0),('ffffffff',0xffffffff),('odd',0x12345),('rom',0x4f6ac)):
        cm('op0c-%s'%tag,'opcode 0c operand %08x: A0 = LONG, 1a40e stores it to 10d40e (no dereference)'%val,0x0c,{2:le(4,val)})
    # ---- opcode 10: double indirect, e89fa default
    for tag,ptr,blob in (('target-null',None,0),('target-nonnull',None,0x123456),('target-odd-value',None,0x123457),('target-default-address',None,0xe89ec),
            ('pointer-rom-vector',0x4,None),('pointer-banked-20000c',0x20000c,None)):
        if ptr is None:
            cm('op10-%s'%tag,'opcode 10: operand pointer to a RAM LONG %08x; A0 = LONG (LONG pointer): e89fa publishes %s to 10de2a'%(blob,'e89ec (A0 = 0)' if blob==0 else 'A0'),0x10,{2:le(4,0)},blobs=[le(4,blob)],ptrs={2:0})
        else:
            cm('op10-%s'%tag,'opcode 10: operand pointer %x (read through the live bus)'%ptr,0x10,{2:le(4,ptr)})
    cm('op10-bank2000-entry-pointer-20000c','opcode 10: operand pointer 20000c read in the declared bank 2000 state (physical 30000c)',0x10,{2:le(4,0x20000c)},bank3=True,group='fixture-bank')
    # ---- opcode 14 / 18 / 1c / 24: node / path state tables 1a086 / 1a09e
    for idx in (0,4,8,0xc):
        for d0,d1 in ((0,0),(0x0010,0x0020),(0xffff,0x8000)):
            cm('op14-index-%x-%04x-%04x'%(idx,d0,d1),'opcode 14: node table index %x (1a086), WORD offsets %04x / %04x shifted to the high words and added to the node coordinates 10d38e / 10d392, 16fee clears 2c(A0), JMP 43e22 -> 43e38'%(idx,d0,d1),
                0x14,{2:le(2,idx),4:le(2,d0),6:le(2,d1)})
    for idx in (0,4,8,0xc):
        for w28,w2a in ((0x0140,0x0100),(0,0),(0xffff,0x8000)):
            cm('op18-index-%x-%04x-%04x'%(idx,w28,w2a),'opcode 18: node table index %x, scale WORDs %04x / %04x to 28(A0) / 2a(A0)'%(idx,w28,w2a),0x18,{2:le(2,idx),4:le(2,w28),6:le(2,w2a)})
    for idx in (0,4,8,0xc):
        for flag in (0,1,0xffff):
            cm('op1c-index-%x-flag-%04x'%(idx,flag),'opcode 1c: node table index %x, TST.W flag %04x: %s'%(idx,flag,'zero -> JMP 1701a' if flag==0 else 'non-zero -> JMP 17012'),0x1c,{2:le(2,idx),4:le(2,flag)})
    for idx in (0,4,8):
        for tag,a2v in (('zero',0),('even',0x12345678&~1),('rom',0x4896a),('banked',0x200010)):
            cm('op24-index-%x-cursor-%s'%(idx,tag),'opcode 24: path state table index %x (1a09e), cursor LONG %08x stored through 19e60 into the state LONG'%(idx,a2v),0x24,{2:le(2,idx),4:le(4,a2v)})
    for idx in (0x10,0x7ffe):
        cm('op14-index-%x-exploratory'%idx,'opcode 14 with node table index %x: LONG read behind the table (1a08e + %x = code / data bytes), observed outcome'%(idx,idx),0x14,{2:le(2,idx)},auto=True,group='fixture-exploratory')
        cm('op24-index-%x-exploratory'%idx,'opcode 24 with path table index %x: LONG read behind the table, observed outcome'%idx,0x24,{2:le(2,idx)},auto=True,group='fixture-exploratory')
    # ---- opcode 20 / 28 / 2c
    for andv,orv in ((0xff,0x00),(0x00,0xff),(0x0f,0xf0),(0xff,0xff),(0x00,0x00),(0xcf,0x20)):
        for init in (0x00,0xa5):
            cm('op20-and-%02x-or-%02x-init-%02x'%(andv,orv,init),'opcode 20: BYTE 10d40c (declared %02x) AND %02x OR %02x'%(init,andv,orv),0x20,{2:bytes([andv,orv])},writes=writes_of({0x10d40c:(1,init)}))
    for w in (0x0000,0x00a0,0x7fff,0x8000,0xffff):
        cm('op28-%04x'%w,'opcode 28: WORD %04x to 10d416'%w,0x28,{2:le(2,w)})
    for d0,sub,skip in ((0x0100,0x0020,0),(0x0100,0x0200,2),(0x0100,0x0100,0xa),(0x7fff,0x0001,4),(0x8000,0x0010,0),(0xffff,0x0001,6),(0x0000,0x0000,0),(0x08d0,0x0000,3),(0x08d0,0x0000,0xfffe),(0x08d0,0x0000,0x7ffe),(0x0100,0x0001,0x8000),(0x0100,0,1)):
        cm('op2c-d0-%04x-sub-%04x-skip-%04x'%(d0,sub,skip),'opcode 2c: first WORD %04x (%s), subtrahend %04x, skip length %04x added to A1 as a sign-extended WORD (odd / negative skips leave A1 odd / lower)'%(d0,'negative: 7fff substituted' if d0&0x8000 else 'positive',sub,skip),
            0x2c,{2:le(2,d0),4:le(2,sub),6:le(2,skip)},auto=(skip in (3,1,0x8000)),group='fixture-script' if skip not in (3,1,0x8000) else 'fixture-exploratory')
    # ---- opcode 30 / 34 / 38 / 3c / 44 / 48 / 4c
    for ws in ((0,0,0,0),(0xffff,0xffff,0xffff,0xffff),(1,2,3,4),(0x8000,0x7fff,0x1234,0xabcd)):
        cm('op30-%s'%'-'.join('%04x'%w for w in ws),'opcode 30: four WORDs to 10d426 / 10d428 / 10d42a / 10d42c',0x30,{2:b''.join(le(2,w) for w in ws)})
    cm('op30-a5-shifted','opcode 30 with the declared initial A5 = 108020: every d16(A5) write moves by 0x20',0x30,{2:b''.join(le(2,w) for w in (1,2,3,4))},regs={'a5':0x108020})
    for bits in (0x0000,0x0001,0x8000,0x8001,0xffff,0x7ffe,0x4000,0x0002):
        for init in (0x00,0x5a,0xff):
            cm('op34-bits-%04x-init-%02x'%(bits,init),'opcode 34: WORD %04x ROL.W #1 AND #3 -> bits (bit15 << 0 | bit0 << 1)... merged into BYTE 10d3cc (declared %02x) keeping bits 2..7'%(bits,init),0x34,{2:le(2,bits)},writes=writes_of({0x10d3cc:(1,init)}))
    for a,b in ((0,0),(0x00010000,0xffffffff),(0x7fffffff,0x80000000),(0x12345678,0x9abcdef0)):
        cm('op38-%08x-%08x'%(a,b),'opcode 38: two LONGs to 10d3fc / 10d400',0x38,{2:le(4,a)+le(4,b)})
    for w in (0,1,0x8000,0xffff):
        cm('op3c-%04x'%w,'opcode 3c: WORD %04x to 10d432'%w,0x3c,{2:le(2,w)})
    for a,b in ((0,0),(0x0d14,0x0d14),(0xffff,0x8000)):
        cm('op44-%04x-%04x'%(a,b),'opcode 44: WORDs %04x / %04x to 10d42e / 10d430'%(a,b),0x44,{2:le(2,a)+le(2,b)})
    for w in (0,1,0x8000,0xffff):
        cm('op48-%04x'%w,'opcode 48: WORD %04x to 10d43c'%w,0x48,{2:le(2,w)})
    st48=example(0x48,bank=0x200000)
    for v in (0,0xffffffff,0x12345678,0x00010002):
        sc_('op4c-%08x'%v,'opcode 4c (no seed executes it): LONG %08x to 10d434'%v,st48,le(2,0x4c)+le(4,v))
    # ---- opcode 40: LSPC mode WORD, 3c0006 port, 104d90
    for d0 in (0,1,2,5,0xa,0xff,0x100,0x101,0x8000,0xffff):
        for init in (0x00,0x08,0xff):
            cm('op40-d0-%04x-104d91-%02x'%(d0,init),'opcode 40 D0.W = %04x (%s): 3d7e %s; 104d91 declared %02x; WORD 104d90 written to 3c0006'%(d0,'0 -> 3d84: BYTE 0 to 104d90, BSET #3 on 104d91' if d0==0 else 'SUBQ.W #1 -> 3d9c: BYTE %02x to 104d90, BCLR #3 on 104d91'%((d0-1)&0xff),'3d84' if d0==0 else '3d9c',init),
                0x40,{2:le(2,d0)},writes=writes_of({0x104d91:(1,init)}))
    for d0 in (0,5):
        cm('op40-a5-shifted-d0-%04x'%d0,'opcode 40 with the declared initial A5 = 108020: the absolute 104d90 BYTE and the A5 relative 104d91 / WORD source (104db0) are different addresses (original behaviour)',0x40,{2:le(2,d0)},regs={'a5':0x108020})
    # ---- opcode word policy: computed JMP 1a0bc + sext(D7.W), no range check
    ptr=lambda: struct.pack('>I',0xe6e9e)
    for word,tag,desc,body in ((0x50,'0050-lands-on-opcode-10-body','1a10c (opcode 10 body, a block start): executes opcode 10 with the operand that follows',ptr()+bytes(8)),
            (0x5a,'005a-lands-on-opcode-0c-body','1a116 (opcode 0c body)',le(4,0x4f6ac)),(0x60,'0060-lands-on-opcode-30-body','1a11c (opcode 30 body)',b''.join(le(2,w) for w in (1,2,3,4))),
            (0x1ae,'01ae-lands-on-u2-block-1a26a','1a26a (U2 block start: the script gate loop)',bytes(8))):
        sc_('opword-%s'%tag,'script opcode word %04x: JMP 1a0bc+%04x = %x'%(word,word,0x1a0bc+word)+' = '+desc,st48,le(2,word)+body,group='fixture-computed-pc',**(dict(delta=0) if word==0x1ae else {}))
    sc_('opword-0052-mid-block','script opcode word 0052: JMP target 1a10e is the middle of the opcode 10 block (not a block start; the observer executes it natively; the contract policy rejects it): observed outcome',st48,le(2,0x52)+bytes(12),
        group='fixture-computed-pc',auto=True,model=False)
    sc_('opword-fffe-into-jmp-operand','script opcode word fffe: sext = -2 -> 1a0ba (the extension WORD of the JMP itself, MOVEQ #2,D0 when decoded): observed outcome',st48,le(2,0xfffe)+bytes(12),group='fixture-computed-pc',auto=True)


# ----------------------------------------------------------------------------------
# Placement 1a470 fixtures: a RAM copy of a natural placement record (declared RAM writes, declared initial A0) + declared limits / bbox / counts
# ----------------------------------------------------------------------------------
INFO=[]


def rw_state(st,addr):return int.from_bytes(st['ram'][addr&0xffff:(addr&0xffff)+2],'big')
def rl_state(st,addr):return int.from_bytes(st['ram'][addr&0xffff:(addr&0xffff)+4],'big')
def s16(v):return sx16(v&0xffff)


def place(F,tag,desc,st,header=None,payload=None,bbox=None,writes=(),regs=None,auto=False,group='fixture-placement',bank3=False,**kw):
    base=base_fx(st,'%s-%x-%d'%(st['case'],st['pc'],st['hit']))
    hdr=bytearray(st['peek'][:16]);natural_len=int.from_bytes(hdr[2:4],'big')
    for off,val in (header or {}).items():hdr[off:off+len(val)]=val
    body=bytes(payload) if payload is not None else bytes(st['peek'][16:16+natural_len])
    if len(body)%2:body+=b'\0'
    blobs=[bytes(hdr)+body]
    if bbox is not None:blobs.append(bytes(bbox))
    areas=F.areas(base,[len(b)+2 for b in blobs])
    if bbox is not None:hdr[8:12]=be(4,areas[1]);blobs[0]=bytes(hdr)+body
    role='declared fixture: state at 1a470 hit %d of case %s with declared initial A0 = %x (RAM copy of the placement record, natural record at %x, header overrides %s)'%(st['hit'],st['case'],areas[0],st['peek_base'],{hex(k):v.hex() for k,v in (header or {}).items()})
    fx=vfx(base,role,dict(a0=areas[0],**(regs or {})),bank3=bank3)
    setup=[]
    for a,b in zip(areas,blobs):setup+=stream_writes(a,b,'placement fixture blob for %s'%tag)
    setup+=list(writes)
    return (F.B.add_auto if auto else F.B.add)('fixture-%s'%tag,group,desc,fx,setup=setup,**kw)


def census_d7(program,st):
    """D7 as returned by 19802 (upper word after the SWAP) in the native run of the unmodified state (model log of the compare at 1a484)."""
    fx=state_fx('d7probe',st,{});c=census_run(program,'d7probe-%d-%d'%(st['case'],st['hit']),fx,st['ret'])
    return c['due_checks'][0]['d7_word']


OPEN=dict(f8=0x7fff,f6=0x8000,f4=0x7fff,f2=0x8000)                  # compare limits that never skip


def place_fixtures(F,program):
    pl_init=[s for s in INIT_ST if s['pc']==0x1a470];pl_scene=[s for s in SCENE_ST if s['pc']==0x1a470]
    null_mot=[s for s in pl_init if rl_state(s,0x10d3b4)==0];mot=[s for s in pl_init if rl_state(s,0x10d3b4)!=0]
    assert null_mot and mot and pl_scene
    pn=null_mot[0];pm=mot[0];pf=pl_scene[0]
    LIM=lambda **kw:writes_of({0x10d3f8:(2,kw.get('f8',OPEN['f8'])),0x10d3f6:(2,kw.get('f6',OPEN['f6'])),0x10d3f4:(2,kw.get('f4',OPEN['f4'])),0x10d3f2:(2,kw.get('f2',OPEN['f2']))})
    PH=lambda v:writes_of({0x10d418:(2,v)})
    names=[(pn,'null-motion'),(pm,'motion-init'),(pf,'motion-frame')]
    for s_ in pl_init+pl_scene:
        if s_ is pn or s_ is pm or s_ is pf:continue
        if census_d7(program,s_)>0:names.append((s_,'motion-d7-positive'));break
    names=tuple(names)
    # ---- copies of natural records and the 28ae success / failure paths
    for st,name in names:
        place(F,'place-copy-%s'%name,'RAM copy of the natural placement record (%s state): same path as the original run'%name,st)
    d7={name:census_d7(program,st) for st,name in names}
    INFO.append(dict(what='D7 word returned by 19802 in the unmodified natural states (the compare at 1a484 uses it)',value=d7))
    for st,name in names[:2]:
        place(F,'place-28ae-fail-count0-%s'%name,'104ca0 = 0: 28ae compares D0.W (0) >= 0 and fails (A0 = 100e98, carry ignored by 1a4ee): 43e08 writes the coordinates at 100ec6 and the payload is copied to 100f0e',st,writes=writes_of({0x104ca0:(2,0)}),group='fixture-28ae')
        place(F,'place-28ae-fail-callback-null-%s'%name,'record callback LONG (+c) = 0: 28ae sees A0 = 0 and fails (same fallback object 100e98)',st,header={12:le(4,0)},group='fixture-28ae')
        place(F,'place-28ae-last-free-%s'%name,'104ca0 = 1 (last free object): 28ae succeeds with D0.W (0) < 1',st,writes=writes_of({0x104ca0:(2,1)}),group='fixture-28ae')
    # ---- the due decision uses the D7 returned by 19802 (not the record time)
    for st,name in names:
        v=d7[name]
        place(F,'place-due-d7-says-notdue-time-says-due-%s'%name,'phase 10d418 = D7+1 (%d): the D7 returned by 19802 (%04x) is below the phase (BCC not taken, bbox tests), the record time is ffff (>= phase)'%(v+1,v),st,header={0:le(2,0xffff)},writes=PH(v+1)+LIM(),group='fixture-due')
        place(F,'place-due-d7-says-due-%s'%name,'phase 10d418 = D7 (%d): the returned D7 (%04x) is >= phase: BCC taken, generation (1a4da)'%(v,v),st,header={0:le(2,0)},writes=PH(v),group='fixture-due')
        if v>0:
            place(F,'place-due-d7-says-due-time-says-notdue-%s'%name,'phase = D7 (%04x) > 0 with record time 0 (< phase): the compare is still decided by the returned D7'%v,st,header={0:le(2,0)},writes=PH(v),group='fixture-due')
    # ---- bounding box edges (not due: phase = D7 + 1; open limits except the compare under test)
    bb=(0x0010,0x0020,0x0008,0x0004)                                     # y0, x0, yext, xext
    def bbox_bytes(y0,x0,ye,xe):return le(4,(x0<<16)|y0)+le(4,(xe<<16)|ye)
    st=pn;v=d7['null-motion'];ph=PH(v+1)
    X=s16(int.from_bytes(st['peek'][4:6],'big'));Y=s16(int.from_bytes(st['peek'][6:8],'big'))
    for s6tag,s6 in (('s6-0',0),('s6-0100',0x0100)):
        w6=writes_of({0x10d3a6:(2,s6)})
        for bbtag,box in (('bbox-null',None),('bbox-ram',bb),('bbox-wrap',(0x7fff,0x8000,0x0002,0xffff))):
            y0,x0,ye,xe=(0,0,0,0) if box is None else box
            c1=(y0+Y-s6)&0xffff;c2=(c1+ye)&0xffff;c3=(x0+X-s6)&0xffff;c4=(c3+xe)&0xffff
            for cmp_,key,c,deltas in ((1,'f8',c1,(-1,0,1)),(2,'f6',c2,(1,0,-1)),(3,'f4',c3,(-1,0,1)),(4,'f2',c4,(1,0,-1))):
                for dlt in deltas:
                    lim=(c+dlt)&0xffff
                    skip={1:s16(c)>s16(lim),2:s16(c)<s16(lim),3:s16(c)>s16(lim),4:s16(c)<s16(lim)}[cmp_]
                    EXPECT['fixture-place-bbox-%s-%s-cmp%d-lim%+d'%(s6tag,bbtag,cmp_,dlt)]=(cmp_,skip)
                    place(F,'place-bbox-%s-%s-cmp%d-lim%+d'%(s6tag,bbtag,cmp_,dlt),'not due (phase = D7 + 1); %s %s: compare %d (%s) value %04x against the declared limit %04x (%+d): %s expected from the bytes; the other three limits are open; 10d3a6 = %04x'%(
                        bbtag,'' if box is None else box,cmp_,{1:'BGT 53f8',2:'BLT 53f6',3:'BGT 53f4 after subtracting 53a6',4:'BLT 53f2'}[cmp_],c,lim,dlt,'skip (1a51c)' if skip else 'continue',s6),
                        st,bbox=None if box is None else bbox_bytes(*box),writes=ph+w6+LIM(**{key:lim}),group='fixture-bbox')
    # ---- copy lengths of the generation path (due: phase = 0)
    for ln in (0,2,4,8,0x40,0x7ffe,0x8002,0xfffe):
        for st,name in ((pn,'null-motion'),(pf,'motion-frame')):
            place(F,'place-copy-length-%04x-%s'%(ln,name),'due (phase 0): record WORD 2 = %04x, payload copied by the MOVE.W (A0)+,(A1)+ / SUBQ.W #2 loop to object+76 (%s)'%(ln,'length >= 8000: TST.W is non-zero, the count is the unsigned WORD' if ln>=0x8000 else 'even'),
                st,header={2:le(2,ln)},payload=bytes(ln) if ln<=0x40 else b'',writes=PH(0),group='fixture-copy' if ln!=0xfffe else 'fixture-exploratory',auto=ln==0xfffe)
    st=pn;v=d7['null-motion'];c1=(Y-rw_state(st,0x10d3a6))&0xffff
    for ln in (0x8002,0x0003,0x0001,0xfffe,0x7ffe,0x0002,0):
        place(F,'place-skip-length-%04x'%ln,'not due and compare 1 fails (limit c1-1): skip path 1a51c: A0 += 10 + sign-extended record length %04x (%+d)'%(ln,s16(ln)),st,header={2:le(2,ln)},writes=PH(v+1)+LIM(f8=(c1-1)&0xffff),group='fixture-skip')
    # ---- odd length: the copy loop never reaches zero; a free-list head at the top of the work RAM puts the first access error after about 600 iterations
    head=0x1ffb00
    for ln in (1,3):
        place(F,'place-copy-length-odd-%d'%ln,'due, record WORD 2 = %d (odd): SUBQ.W #2 never reaches 0, the copy runs on until an access error; the declared free-list head 104c9c = %x (alias of the work RAM top) and its next pointer 8(head) = 0'%(ln,head),
            pn,header={2:le(2,ln)},payload=bytes(2),writes=PH(0)+writes_of({0x104c9c:(4,head),head+8:(4,0)}),guard=dict(problem='unmapped_or_protected',pc=0x1a514,address=0x200000,size=2),group='fixture-copy')
    place(F,'place-copy-length-odd-3-default-free-list','due, record WORD 2 = 3 (odd) with the unmodified free list (object near 1010xx): the copy loop runs about 520000 iterations until the A1 write reaches the read-only bank window at 200000; heavy condition (not stored): observed to confirm that the end is an access error and not an instruction budget (native budget raised to 4000000)',
        pn,header={2:le(2,3)},payload=bytes(2),writes=PH(0),guard=dict(problem='unmapped_or_protected',pc=0x1a514,address=0x200000,size=2),group='fixture-heavy')
    HEAVY.append(F.B.specs.pop())


# ----------------------------------------------------------------------------------
# U2 gate loops around the two entries (1a26a script loop, 1a442 placement gate), guards, natural chains, negative stops
# ----------------------------------------------------------------------------------
def loop_fixtures(F,program):
    B=F.B
    g26=[s for s in SCENE_ST if s['pc']==0x1a26a and s['ret']==0x1a75e]
    g42=[s for s in SCENE_ST if s['pc']==0x1a442 and s['ret']==0x1a790]
    # --- 1a442 gate: null cursor / terminator ffff / not due / due (record RAM copy of a natural due record)
    st=next(s for s in g42 if rl_state(s,0x10d40e) and rw_state(s,0x10d418)>=int.from_bytes(program[rl_state(s,0x10d40e):rl_state(s,0x10d40e)+2],'big')!=0xffff)
    cur=rl_state(st,0x10d40e);rec=bytes(program[cur:cur+0x20]);ph=rw_state(st,0x10d418)
    base=base_fx(st,'gate-%d'%st['case'])
    def gate(tag,desc,first_word,cursor=None,writes=()):
        area=F.areas(base,[len(rec)+2])[0];r=bytearray(rec);r[0:2]=le(2,first_word)
        cv=area if cursor is None else cursor
        fx=vfx(base,'declared fixture: 1a442 entry state of case %d with a RAM copy of the natural placement record at %x and the cursor LONG 10d40e declared'%(st['case'],area))
        return B.add('fixture-gate-%s'%tag,'fixture-gate',desc,fx,setup=stream_writes(area,bytes(r),'record copy')+writes_of({0x10d40e:(4,cv)})+list(writes))
    gate('cursor-null','10d40e = 0: 1a442 returns at 1a44e (no placement)',0,cursor=0)
    gate('terminator-ffff','first record WORD ffff: 1a45a returns',0xffff)
    gate('not-due','record time = phase+1 (%d): BLS not taken, 1a464 returns'%(ph+1),(ph+1)&0xffff)
    gate('due-equal','record time = phase (%d): BLS taken (equal), 1a466 -> 1a470 -> 1a46a'%ph,ph)
    gate('due-zero','record time 0: due, 1a470 -> 1a46a',0)
    # --- 1a26a script loop with a declared multi-command stream and the natural scripts
    st=g26[0];base=base_fx(st,'loop-%d'%st['case'])
    def loop(tag,desc,cmds,wait=0,phase=None,regs=None):
        raw=b''.join(cmds);area=F.areas(base,[len(raw)+2])[0]
        w={0x10d412:(4,area),0x10d416:(2,wait)}
        if phase is not None:w[0x10d418]=(2,phase)
        fx=vfx(base,'declared fixture: 1a26a entry state of case %d with the script cursor LONG 10d412 declared to a RAM stream at %x (%d bytes)'%(st['case'],area,len(raw)))
        return B.add('fixture-loop-%s'%tag,'fixture-loop',desc,fx,setup=stream_writes(area,raw,'script stream')+writes_of(w))
    term=le(2,0x8000)
    loop('five-commands-then-terminator','1a26a loop: opcodes 30 / 34 / 40 / 38 / 48 then a negative WORD (1a28a sets 10d416 = ffff): five 1a0b6 calls, each returning to 1a296 which publishes A1 to 10d412 and re-tests 1a278',
        [le(2,0x30)+b''.join(le(2,w) for w in (1,2,3,4)),le(2,0x34)+le(2,0x8001),le(2,0x40)+le(2,3),le(2,0x38)+le(4,0x11112222)+le(4,0x33334444),le(2,0x48)+le(2,5),term])
    loop('wait-command','1a26a loop: opcode 2c sets the wait counter above the phase and skips 4 inline bytes, 1a278 then returns at 1a29c',
        [le(2,0x2c)+le(2,0x7fff)+le(2,0x0001)+le(2,4)+bytes(4),le(2,0x30)+bytes(8),term],phase=0)
    loop('wait-already-due','1a26a loop: the wait counter (10d416) is below the phase: the first command runs',[le(2,0x28)+le(2,0),term],wait=0,phase=5)
    loop('wait-not-due','1a26a loop: wait counter above the phase: 1a278 returns at 1a29c without any 1a0b6 call',[le(2,0x28)+le(2,0),term],wait=9,phase=3)
    loop('terminator-only','1a26a loop: the first WORD is negative: 1a28a sets 10d416 = ffff',[term])
    loop('opcode-04-through-gate','1a26a loop: opcode 04 index 0 (bank writes, descriptor, palette bind 8da2) through the gate, then the terminator',[le(2,0x04)+le(2,0),term])


def guard_fixtures(F,program):
    B=F.B
    def gx(label,desc,guard,fx,setup=(),stop=None,delta=None):
        return B.add(label,'guard',desc,fx,setup=setup,stop=PROBE_STOP if stop is None else stop,guard=guard,model=False,delta=0 if delta is None else delta)
    ok=lambda **kv:dict(problem='unsupported_odd_data_access',**kv)
    st30=example(0x30);b30=base_fx(st30,'guard-30');st00=example(0x00,pred=lambda s:int.from_bytes(s['peek'][6:10],'big')!=0);b00=base_fx(st00,'guard-00')
    # odd registers
    f=vfx(b30,'declared initial A1 = 10e001 (odd)',dict(a1=0x10e001))
    gx('guard-odd-A1-1a0b6','A1 odd: MOVE.W (A1)+,D7 at 1a0b6 reads an odd WORD',ok(pc=0x1a0b6,address=0x10e001,size=2,access='read'),f)
    f=vfx(b30,'declared initial A7 = entry A7 + 1 (odd)',initial_a7=b30['initial_a7']+1)
    gx('guard-odd-A7-rts','A7 odd: the RTS of the opcode 30 handler (1a12c) reads an odd LONG',ok(pc=0x1a12c,address=b30['initial_a7']+1,size=4,access='read'),f)
    f=vfx(b00,'declared initial A7 = entry A7 + 1 (odd)',initial_a7=b00['initial_a7']+1)
    gx('guard-odd-A7-push-op00','A7 odd: MOVE.L A1,-(A7) at 1a17a writes an odd LONG',ok(pc=0x1a17a,address=b00['initial_a7']+1-4,size=4,access='write',odd_write_restored=True),f)
    f=vfx(b30,'declared initial A5 = 108001 (odd)',dict(a5=0x108001))
    gx('guard-odd-A5-1a11c','A5 odd: MOVE.W (A1)+,5426(A5) at 1a11c writes an odd WORD',ok(pc=0x1a11c,address=0x108001+0x5426,size=2,access='write',odd_write_restored=True),f)
    f=vfx(b30,'declared initial A5 = 8ff0 (the d16(A5) target lies in ROM)',dict(a5=0x8ff0))
    gx('guard-rom-write-A5-1a11c','A5 = 8ff0: MOVE.W (A1)+,5426(A5) at 1a11c writes ROM e416',dict(problem='unmapped_or_protected',pc=0x1a11c,address=0x8ff0+0x5426,size=2),f)
    f=vfx(b00,'declared initial A7 = 1100 (ROM)',initial_a7=0x1100)
    gx('guard-rom-write-A7-push-op00','A7 = 1100: MOVE.L A1,-(A7) at 1a17a writes ROM',dict(problem='unmapped_or_protected',pc=0x1a17a,address=0x1100-4,size=4),f)
    # odd pointers inside the unit
    st10=example(0x10);b10=base_fx(st10,'guard-10')
    area=F.areas(b10,[16])[0]
    raw=bytearray(st10['peek'][:CMD_LEN[0x10]]);raw[2:6]=le(4,0x10e001)
    f=vfx(b10,'declared initial A1 = %x (RAM copy of opcode 10 with the odd operand pointer 10e001)'%area,dict(a1=area))
    gx('guard-odd-pointer-op10','opcode 10 operand pointer odd: MOVEA.L (A0),A0 at 1a10e reads an odd LONG',ok(pc=0x1a10e,address=0x10e001,size=4,access='read'),f,stream_writes(area,bytes(raw),'script stream'))
    st18=example(0x18);b18=base_fx(st18,'guard-18');area=F.areas(b18,[16])[0]
    raw=bytearray(st18['peek'][:CMD_LEN[0x18]]);raw[2:4]=le(2,1)
    f=vfx(b18,'declared initial A1 = %x (RAM copy of opcode 18 with the odd table index 1)'%area,dict(a1=area))
    gx('guard-odd-table-index-1a086','node table index 1: MOVEA.L 6(PC,D7.W),A0 at 1a086 reads an odd LONG at 1a08f',ok(pc=0x1a086,address=0x1a08f,size=4,access='read'),f,stream_writes(area,bytes(raw),'script stream'))
    # declared entries at internal PCs
    f=vfx(b00,'declared entry at 16fee with declared A0 = 4000 (ROM)',dict(a0=0x4000),entry_pc=0x16fee)
    gx('guard-rom-write-16fee','entry 16fee with A0 in ROM: CLR.W 2c(A0) writes ROM',dict(problem='unmapped_or_protected',pc=0x16fee,address=0x402c,size=2),f)
    f=vfx(b00,'declared entry at 43e22 with declared A0 = 10e001 (odd)',dict(a0=0x10e001),entry_pc=0x43e22)
    gx('guard-odd-A0-43e22','entry 43e22 with odd A0: MOVE.L A1,10(A0) writes an odd LONG',ok(pc=0x43e22,address=0x10e011,size=4,access='write',odd_write_restored=True),f)
    f=vfx(b00,'declared entry at 43e08 with declared A0 = 10e001 (odd)',dict(a0=0x10e001),entry_pc=0x43e08)
    gx('guard-odd-A0-43e08','entry 43e08 with odd A0: MOVE.L A1,10(A0) writes an odd LONG',ok(pc=0x43e10,address=0x10e011,size=4,access='write',odd_write_restored=True),f)
    f=vfx(b00,'declared entry at 19e60 with declared A1 = 10e001 (odd)',dict(a1=0x10e001,a2=0x12345678),entry_pc=0x19e60)
    gx('guard-odd-A1-19e60','entry 19e60 with odd A1: MOVE.L A2,(A1) writes an odd LONG',ok(pc=0x19e60,address=0x10e001,size=4,access='write',odd_write_restored=True),f)
    pl=[s for s in INIT_ST if s['pc']==0x1a470][0];bp=base_fx(pl,'guard-place')
    f=vfx(bp,'declared initial A0 = 10e001 (odd)',dict(a0=0x10e001))
    gx('guard-odd-A0-1a470','A0 odd: MOVE.W (A0),D7 at 1a472 reads an odd WORD',ok(pc=0x1a472,address=0x10e001,size=2,access='read'),f)
    # computed opcode words
    for word,tag in ((0x0001,'odd'),(0x7ffe,'7ffe-far'),(0x7fff,'7fff-odd-far'),(0x8000,'8000-negative-far')):
        target=(0x1a0bc+sx16(word))&M32
        area=F.areas(b30,[16])[0]
        f=vfx(b30,'declared initial A1 = %x (RAM stream with the opcode word %04x)'%(area,word),dict(a1=area))
        gx('guard-opword-%s'%tag,'script opcode word %04x: JMP 1a0bc+sext = %x is not a code address of the machine (computed PC, no range check)'%(word,target),dict(problem='unsupported_code_target',target=target),f,stream_writes(area,le(2,word)+bytes(8),'script stream'))
    # bad / unreachable stops
    st=[s for s in SCENE_ST if s['pc']==0x1a0b6][5];f=base_fx(st,'badstop-frame')
    gx('guard-bad-stop-never-reached-frame','frame state at 1a0b6 with a stop that is never reached: the frame runs on until the RTS pops ff000 (outside every observed range)',dict(problem='unsupported_code_target',target=RETURN_FF000),f,delta=4)
    st=[s for s in INIT_ST if s['pc']==0x1a470][3];f=base_fx(st,'badstop-init')
    gx('guard-bad-stop-never-reached-init','init state at 1a470 with a stop that is never reached: the RTS returns to 1a43c (the initialization routine 1a414.., outside the observed ranges) and the run ends there',dict(problem='unsupported_code_target',target=0x1a43c),f,delta=4)
    st=example(0x30);B.add('boundary-zero-step-1a0b6','boundary','zero-step: stop PC equals the entry PC 1a0b6, nothing is executed',base_fx(st,'zero-1a0b6'),stop=ENTRY_SCRIPT)
    st=[s for s in INIT_ST if s['pc']==0x1a470][0];B.add('boundary-zero-step-1a470','boundary','zero-step: stop PC equals the entry PC 1a470, nothing is executed',base_fx(st,'zero-1a470'),stop=ENTRY_PLACE)


def negative_checks(program,B):
    out=[]
    cases=[(example(0x04,bank=0x200000),0x1a1be,'return address of the JSR 8da2 (opcode 04)'),(example(0x00,pred=lambda s:int.from_bytes(s['peek'][6:10],'big')!=0),0x1a186,'return address of the BSR 197da (opcode 00)'),
        ([s for s in INIT_ST if s['pc']==0x1a470][0],0x1a4ee,'return address of the JSR 28ae'),([s for s in INIT_ST if s['pc']==0x1a470][0],0x1a500,'return address of the JSR 43e08')]
    for st,stop,what in cases:
        fx=state_fx('neg',st,{});label='negative-%x'%stop
        p=su.run_to(program,dict(fx,label=label),[],stop)
        p['step_stop_pc']=stop;p['label']=label
        try:stop_evidence5(program,p);refused=False;err=None
        except AssertionError as e:refused=True;err=repr(e)[:200]
        out.append(dict(label=label,stop=hex(stop),what=what,native_run_stopped_there=True,stop_evidence_refused=refused,error=err))
        assert refused,label
    return out


# ----------------------------------------------------------------------------------
# Natural conditions (declared entries from the original runs), natural chains, selection
# ----------------------------------------------------------------------------------
def sig_script(s):
    pk=s['peek'];op=int.from_bytes(pk[:2],'big');w=lambda k:int.from_bytes(pk[k:k+2],'big')
    x=()
    if op==0:x=(int.from_bytes(pk[6:10],'big')==0,)
    elif op==4:x=(w(2) in (0,0x4c),)
    elif op==0x40:x=(w(2)==0,)
    elif op==0x2c:x=(w(2)>>15,)
    elif op==0x1c:x=(w(4)==0,)
    elif op in (0x14,0x18,0x24):x=(w(2),)
    elif op==0x34:x=(w(2)&0x8001,)
    return (op,s['bank'])+x


def sig_place(s):
    pk=s['peek'];return (int.from_bytes(pk[2:4],'big')>0,int.from_bytes(pk[8:12],'big')!=0,rl_state(s,0x10d3b4)!=0,int.from_bytes(pk[12:16],'big')!=0,s['ret'])


def key_of(s):return '%s-%x-%d'%(s['case'],s['pc'],s['hit'])


def natural_conditions(B,scene_states,init_states):
    chosen=[]
    for s in scene_states:
        if s['pc'] in (0x1a0b6,0x1a470):
            B.add('natural-scene-%s-%s'%('script' if s['pc']==0x1a0b6 else 'placement',key_of(s)),'natural-scene-%s'%('script' if s['pc']==0x1a0b6 else 'placement'),
                state_prov('scene_frame_execution case %d: declared %x entry from the original uninterrupted full-frame run'%(s['case'],s['pc']),s),state_fx('nat-scene-%s'%key_of(s),s,state_prov('scene_frame_execution',s)))
    first={}
    for s in scene_states:
        if s['pc'] in (0x1a26a,0x1a442):first.setdefault((s['case'],s['pc']),s)
    for (case,pc),s in sorted(first.items()):
        if case in NATURAL_SCRIPT_CASES+NATURAL_PLACE_CASES:
            B.add('natural-scene-gate-%s'%key_of(s),'natural-scene-gate',state_prov('scene_frame_execution case %d: first %x entry (the U2 gate that calls U5)'%(case,pc),s),state_fx('nat-gate-%s'%key_of(s),s,state_prov('scene_frame_execution',s)))
    sel=pick([s for s in init_states if s['pc']==0x1a0b6],sig_script,3)
    for s in init_states:
        if s['pc']==0x1a0b6 and int.from_bytes(s['peek'][:2],'big') in (0x10,0x44) and s not in sel:sel.append(s)
    sel+=pick([s for s in init_states if s['pc']==0x1a470],sig_place,4)
    sel+=pick([s for s in init_states if s['pc'] in (0x1a26a,)],lambda s:(s['ret'],s['bank']),6)
    for s in sel:
        grp='natural-init-script' if s['pc']==0x1a0b6 else ('natural-init-placement' if s['pc']==0x1a470 else 'natural-init-gate')
        B.add('natural-init-%s'%key_of(s),grp,state_prov('scene_general_initialization case %d: declared %x entry from the original 1a5a4 run'%(s['case'],s['pc']),s),state_fx('nat-init-%s'%key_of(s),s,state_prov('scene_general_initialization',s)))
    return sel


NATURAL_SCRIPT_CASES=[237,424,437,479,502,509,514,564,577,588,589,590,591]
NATURAL_PLACE_CASES=[380,436,437,508,576,577]


def masked_equal(a,b,lo):
    return all(a[k]==b[k] for k in range(0x10000) if not (min(lo,0xeff0)<=k<0xf000))


def chain_specs(program,scene_in,scene_states):
    """Natural chains: direct 1a73c entry of the rebuilt seed -> first 1a0b6 / 1a470 (accepted stop directly after the BSR) -> U5 to its RTS -> onward to the RTS popping ff000 (one persistent CPU)."""
    out=[]
    for pc,cases in ((0x1a0b6,NATURAL_SCRIPT_CASES),(0x1a470,NATURAL_PLACE_CASES)):
        for case in cases:
            st=next(s for s in scene_states if s['case']==case and s['pc']==pc and s['hit']==1)
            row,ram,regs=scene_in[case];prov=sc.scene_prov(case,row,ram)
            fx=sc.direct_fx('chain-%04d-%x'%(case,pc),ram,regs,prov)
            label='natural-chain-%04d-%x'%(case,pc)
            steps=[dict(label='1a73c-to-%x'%pc,changes=[],stop_pc=pc,checkpoints=[],a7=('entry',st['a7']-fc.S)),dict(label='u5-%x-to-%x'%(pc,st['ret']),changes=[],stop_pc=st['ret'],checkpoints=[],a7=('entry',4)),
                dict(label='onward-to-ff000',changes=[],stop_pc=RETURN_FF000,checkpoints=[],a7=('entry',fc.S-st['a7']))]
            spec=dict(label=label,group='natural-chain',fixture=dict(fx,label=label),steps=steps,provenance=prov,chain_case=case,chain_entry=pc,chain_state_ram_sha256=sha(st['ram']))
            probe=fc.run_condition(program,spec,True)
            assert [q['outgoing']['pc'] for q in probe]==[pc,st['ret'],RETURN_FF000] and probe[0]['outgoing']['a7']==st['a7'] and masked_equal(probe[0]['ram_after'],st['ram'],min([e['address'] for e in probe[0]['events'] if e['region']=='ram' and e['access']=='write' and e['address']>=0x1f0000]+[st['a7']])&0xffff),(label,)
            for k,step in enumerate(steps):
                order=[];entry=probe[k]['pcs'][0]
                for x in probe[k]['pcs'][1:-1]:
                    if x in MODEL_LEADERS and x not in order and x!=entry:order.append(x)
                step['checkpoints']=order
            out.append(spec)
    return out


# ----------------------------------------------------------------------------------
# Evidence, summaries, report
# ----------------------------------------------------------------------------------
EVIDENCE={}
PROGRAM=None
EXPECT={}
HEAVY=[]


def collect_evidence(spec,split,control,model_row):
    label=spec['label'];p=control[-1];pcs=[pc for q in control for pc in q['pcs']];events=[e for q in control for e in q['events']]
    lead=collections.Counter(pc for pc in pcs if pc in U5_LEADERS);gate=collections.Counter(hex(pc) for pc in pcs if pc in LOOP2)
    ev=dict(group=spec['group'],first_stop=hex(p['outgoing']['pc']) if p['guard'] is None else None,leaders=sorted(hex(pc) for pc in lead),leader_hits={hex(pc):n for pc,n in sorted(lead.items())},
        instructions=len(pcs)-len(control),unit_ports=[(e['size'],hex(e['address']),e['bytes']) for e in events if e['region'] in PORT_REGIONS and e['access']=='write' and event_pc_in_unit(e['pc'])],
        bank_reads_unit=[dict(pc=hex(e['pc']),address=hex(e['address']),size=e['size'],bank_at_read=hex(e['bank_at_read']),physical=hex(e['physical_rom_offset']),bytes=e['bytes']) for e in events if e['region']=='bank' and event_pc_in_unit(e['pc'])][:6],
        ram_writes_unit=sum(1 for e in events if e['region']=='ram' and e['access']=='write' and event_pc_in_unit(e['pc'])),guard=p['guard'],gate_hits=sorted(gate),
        entry={k:p0 for k,p0 in control[0]['incoming'].items()},final={k:v for k,v in p['outgoing'].items()},bank_after=hex(p['modeled_bank']),
        writes_43e08=[(hex(e['address']),e['size'],e['bytes']) for e in events if e['region']=='ram' and e['access']=='write' and e['pc'] in (0x43e10,0x43e14,0x43e18,0x43e26,0x43e2a,0x43e2e)][:8],
        copy_dest_first_last=[(hex(e['address']),hex(e['address']+e['size'])) for e in ([x for x in events if x['pc']==0x1a514 and x['access']=='write'][:1]+[x for x in events if x['pc']==0x1a514 and x['access']=='write'][-1:])],
        ram_writes_100010=[e['bytes'] for e in events if e['region']=='ram' and e['access']=='write' and e['address']==0x100010 and event_pc_in_unit(e['pc'])])
    if p['guard'] is None:
        ev['stop_evidence']=p['stop_evidence']
        if model_row is not None:
            ev['model']={k:model_row.get(k) for k in ('equal','unit_stack_depth','native_stack_depth','due_checks','a0_after_28ae')}
            ev['model']['blackbox']=[b['callee'] for b in model_row.get('blackbox',[])];ev['model']['carry_18c06']=model_row.get('carry_18c06')
    EVIDENCE[label]=ev


def condition_summary(spec,split,control):
    c=control[-1];pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    called={hex(pc):pcs.count(pc) for pc in BB_ENTRIES if pc in pcs}
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs)-len(control),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),
        called=called,ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),
        external_reads=sum(1 for e in ev if e['region']=='external'),ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=fh.ordered_ports_sha(ev),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'])


def hexset(s):return sorted(hex(x) for x in s)


def stratified_report(states):
    return [dict(case=s['case'],pc=hex(s['pc']),hit=s['hit'],ram_sha256=sha(s['ram']),a7=hex(s['a7']),bank=hex(s['bank']),pvc_raw_words=[hex(x) for x in s['pvc_raw']],return_long=hex(s['ret'])) for s in states]


CENSUS_ROWS=[]


def run_census(program,states,kind):
    for s in states:
        if s['pc'] not in (0x1a0b6,0x1a470,0x1a26a,0x1a442):continue
        fx=state_fx('census-%s-%s'%(kind,key_of(s)),s,{});c=census_run(program,fx['label'],fx,s['ret'])
        opw=int.from_bytes(s['peek'][:2],'big') if s['pc']==0x1a0b6 and s['peek'] else None
        CENSUS_ROWS.append(dict(kind=kind,case=s['case'],pc=s['pc'],hit=s['hit'],opcode=opw,ret=s['ret'],bank=s['bank'],peek=s['peek'][:0x20].hex(),a1=s['peek_base'],model_equal=c['model_equal'],instructions=c['instructions'],
            leaders={hex(k):v for k,v in c['leaders'].items()},unit_stack_depth=c['unit_stack_depth'],native_stack_depth=c['native_stack_depth'],carry_18c06=c['carry_18c06'],due_checks=c['due_checks'],
            a0_after_28ae=c['a0_after_28ae'],blackbox=c['blackbox_names'],ports=c['ports'],bank_after=c['bank_after'],ram_writes=c['ram_writes'],motion_ptr=rl_state(s,0x10d3b4)))


def init_pool():
    fc.BOUNDARIES=()
    op.PHASE_LIMIT=5000


def run_full_frames(program,scene_in,workers):
    global FRAME_SCENE,FRAME_PROGRAM,FRAME_LEADERS
    FRAME_SCENE=scene_in;FRAME_PROGRAM=program
    ud=set(fh.leaders_of(program,su.U4_RANGES))|set(su.EXTRA_LEADERS)
    FRAME_LEADERS=frozenset(MODEL_LEADERS|set(sc.LEADERS)|ud)
    if workers<=1:
        saved=(fc.BOUNDARIES,op.PHASE_LIMIT);init_pool()
        try:rows=[frame_worker(i) for i in range(len(scene_in))]
        finally:fc.BOUNDARIES,op.PHASE_LIMIT=saved
        return rows
    import multiprocessing
    ctx=multiprocessing.get_context('fork')
    with ctx.Pool(workers,initializer=init_pool) as pool:
        rows=list(pool.imap_unordered(frame_worker,range(len(scene_in)),chunksize=4))
    return sorted(rows,key=lambda r:r['case'])


def main():
    import time
    t_start=time.time()
    dev_filter=sys.argv[1] if len(sys.argv)>1 and sys.argv[1]!='-' else None
    workers=int(os.environ.get('U5_WORKERS','10'))
    skip_frames=os.environ.get('U5_SKIP_FRAMES')=='1'
    out_dir=OUT if dev_filter is None and not os.environ.get('U5_DEV') else SCRATCH/'dev_out'
    global PROGRAM
    program,source=load_verified_program(ROOT);PROGRAM=program;rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    install_video_3c0006();configure(program,out_dir)
    op.PHASE_LIMIT=5000
    scene_obs,scene_in=scene_inputs_checked(program);init_obs,init_in=init_inputs(program)
    print('seeds',len(scene_in),len(init_in),flush=True)
    SCENE_ST[:]=capture_scene(program,scene_in);INIT_ST[:]=capture_init(program,init_in);build_harvest()
    print('captured',len(SCENE_ST),len(INIT_ST),'%.0fs'%(time.time()-t_start),flush=True)
    frame_rows=[]
    if not skip_frames:
        frame_rows=run_full_frames(program,scene_in,workers)
        print('full frames',len(frame_rows),'ok',sum(1 for r in frame_rows if r['ok']),'%.0fs'%(time.time()-t_start),flush=True)
    if os.environ.get('U5_SKIP_CENSUS')!='1':run_census(program,SCENE_ST,'scene');run_census(program,INIT_ST,'init')
    print('census',CENSUS_MODEL['runs'],'equal',CENSUS_MODEL['equal'],'unequal',len(CENSUS_MODEL['unequal']),'errors',len(CENSUS_MODEL['model_errors']),'%.0fs'%(time.time()-t_start),flush=True)
    B=Builder(program);F=Fix(B)
    natural_conditions(B,SCENE_ST,INIT_ST);script_fixtures(F,program);place_fixtures(F,program);loop_fixtures(F,program);guard_fixtures(F,program)
    chains=chain_specs(program,scene_in,SCENE_ST)
    covered=set()
    for c in B.census.values():covered|=c['leaders']
    print('conditions',len(B.specs),'chains',len(chains),'covered U5 block starts',len(covered&U5_LEADERS),'of 88; missing',hexset(U5_LEADERS-covered),'%.0fs'%(time.time()-t_start),flush=True)
    specs=B.specs+chains
    if dev_filter:specs=[s for s in specs if any(f in s['label'] for f in dev_filter.split(','))]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,sc.CONTRACT,fh.CONTRACT,sc.STAGE_FRAME,su.CONTRACT,mw.CONTRACT}
    input_paths.update(Path(p) for p in sc.SEED_FILES)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin_ref=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin_ref['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);model_checks=[];summaries=[];coverage_by=collections.defaultdict(list);chain_rows=[]
    saved_cap=fc.CAP
    for number,spec in enumerate(specs):
        if spec['label'].startswith('fixture-place-copy-length-odd'):fc.CAP=4000000
        split,control=run_spec(program,spec)
        fc.CAP=saved_cap
        row=None
        if spec['label'] in B.models and spec.get('guarded') is None:row=check_model(program,spec,control);model_checks.append(row)
        if spec.get('chain_case') is not None:
            cmp=compare_recorded([q for q in control],scene_in[spec['chain_case']][0],scene_in[spec['chain_case']][1])
            chain_rows.append(dict(label=spec['label'],case=spec['chain_case'],entry=hex(spec['chain_entry']),steps=len(spec['steps']),compare=cmp,
                ok=all([cmp['instructions_equal'],cmp['ram_equal_outside_stack_window'],cmp['ports_equal'],cmp['registers_equal'],cmp['bank_equal'],cmp['final_a7_equal']])))
        summaries.append(condition_summary(spec,split,control));collect_evidence(spec,split,control,row)
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        for pc in set(pc for q in control for pc in q['pcs'])&U5_LEADERS:coverage_by[pc].append(spec['label'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),observed_guard_not_predicted=bool(spec.get('observed_guard_not_predicted')),
            fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),phases=fh.store('c%03d_split'%number,split,fc.KEY_PCS),continuous_control=fh.store('c%03d_control'%number,control,fc.KEY_PCS),
            reproduced_twice=True,continuous_split_equivalent=True,compared_with_chain=False,stored_from_step=0)
        for rows in (result['phases'],result['continuous_control']):
            for r in rows:artifacts.update(r['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else '',
            ' MODEL %s'%('ok' if row['equal'] else 'MISMATCH') if row is not None else ''),flush=True)
    heavy_rows=[]
    for spec in (HEAVY if (not dev_filter or 'default-free-list' in dev_filter) else []):
        fc.CAP=4000000
        split,control=run_spec(program,spec);fc.CAP=saved_cap
        collect_evidence(spec,split,control,None);c=control[-1];h=EVIDENCE[spec['label']]
        heavy_rows.append(dict(label=spec['label'],group=spec['group'],provenance=spec['provenance'],expected_guard=spec['guard'],guard=c['guard'],native_instructions=len(c['pcs'])-1,copy_iterations=h['leader_hits'].get('0x1a514'),
            instruction_budget_native=4000000,reproduced_twice=True,continuous_split_equivalent=True,stored=False,ordered_ports_sha256=fh.ordered_ports_sha(c['events']),ram_after_sha256=sha(c['ram_after']),
            note='events not stored (about one million data events); the guard, the instruction count and the iteration count are recorded'))
        print('heavy',spec['label'],c['guard'],len(c['pcs']),flush=True)
    negatives=negative_checks(program,B)
    instructions=[]
    for lo,hi in U5_CODE_RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,u5_ranges=U5_CODE_RANGES,data_ranges=U5_DATA_RANGES,black_boxes={hex(k):v for k,v in BB_NAMES.items()},instructions=instructions,observer_extension=EXTENSION,
        new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in U5_CODE_RANGES+U5_DATA_RANGES},ranges_all=RANGES),indent=2)+'\n').encode()
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
    group_counts={}
    for r in results+guards:group_counts[r['group']]=group_counts.get(r['group'],0)+1
    claims=[]
    if not dev_filter:
        try:claims=contract_claims(frame_rows,chain_rows,B,specs,negatives)
        except Exception as e:
            import traceback;traceback.print_exc();claims=[dict(claim='contract claims could not be computed',verdict='tool-error',evidence=repr(e)[:500])]
    if os.environ.get('U5_DEV'):
        import pickle;pickle.dump(dict(census=CENSUS_ROWS,evidence=EVIDENCE,frames=frame_rows,chains=chain_rows,negatives=negatives,model_checks=model_checks),open(SCRATCH/'dev_cache.pkl','wb'))
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    missing_native=hexset(U5_LEADERS-coverage)
    block_coverage=[dict(pc=hex(pc),in_contract_list=pc in CONTRACT_STARTS,selection='contract-88',conditions=len(coverage_by.get(pc,())),first_condition=(coverage_by.get(pc) or [None])[0],
        groups=sorted({next(s['group'] for s in specs if s['label']==l) for l in coverage_by.get(pc,())})) for pc in sorted(U5_LEADERS)]
    census_report=[{k:v for k,v in r.items() if k not in ('peek',)} for r in CENSUS_ROWS]
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=0,variant_child_layouts=[],guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard'],observed_not_predicted=g['observed_guard_not_predicted']) for g in guards],
        negative_stop_checks=negatives,bank_reads_by_condition=[dict(label=s['label'],bank_read_count=s['bank_read_count']) for s in summaries if s['bank_read_count']],bank_descriptor_search=[],
        new_ranges=U5_CODE_RANGES,existing_ranges=ALL_EXISTING,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=parse_contract_table(program),contract_block_starts=len(CONTRACT_STARTS),contract_bundled_branches=len(CONTRACT_BUNDLED),
            observer_block_starts_u5=len(U5_LEADERS),observer_leaders_with_black_boxes_and_gate=len(MODEL_LEADERS),u4_contract_sha256=sha(su.CONTRACT.read_bytes()),u3_contract_sha256=sha(mw.CONTRACT.read_bytes()),u2_contract_sha256=sha(sc.CONTRACT.read_bytes())),
        contract_model_checks=model_checks,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=EVIDENCE,observer_extension=EXTENSION,info=INFO,
        full_frame=dict(cases=len(frame_rows),ok=sum(1 for r in frame_rows if r['ok']),rows=frame_rows,workers=workers,note='every scene_frame_execution seed: direct 1a73c entry (A7 = 1feffc, return LONG ff000) to the RTS popping ff000, native machine-style observer (U2+U3+U4+U5+existing executors); fresh-twice and split vs continuous per case; compared with the recorded original run (flat map): instruction count, RAM outside the stack window, ordered port stream, 14 result registers, final bank, final A7'),
        natural_chains=chain_rows,heavy_guard_conditions=heavy_rows,
        first_boundary_census=dict(states=len(CENSUS_ROWS),rows=census_report,scene_frame_1a7a8_states=[r for r in census_report if r['kind']=='scene'],stage_entry_states=[r for r in census_report if r['kind']=='init'],counts=dict(scene=sum(1 for r in census_report if r['kind']=='scene'),stage_entry=sum(1 for r in census_report if r['kind']=='init'),note='stage_entry_states holds the scene_general_initialization states (this unit has no stage_entry seed)')),census_model_checks=dict(runs=CENSUS_MODEL['runs'],equal=CENSUS_MODEL['equal'],unequal=CENSUS_MODEL['unequal'][:20],model_errors=CENSUS_MODEL['model_errors'][:20]),
        seed_provenance=dict(files=sc.SEED_FILES,scene_frame=dict(observation_sha256=sc.SCENE_OBS_SHA,initializer_observation_sha256=sc.SCENE_SEED_SHA,cases=len(scene_in),captured_states=stratified_report(SCENE_ST)),
            scene_general_initialization=dict(observation_sha256=sc.SCENE_SEED_SHA,cases=len(init_in),input_ram_sha256=[r['input_ram_sha256'] for r,_,_ in init_in],captured_states=stratified_report(INIT_ST)),
            note='Declared initial fixtures: rebuilt scene_frame inputs (sha-checked), every 1a0b6 / 1a470 / 1a26a / 1a442 state of the original uninterrupted full-frame runs and of the original 1a5a4 initializer runs (RAM, 14 registers, A5 = 108000, A7, live stack bytes, PVC register words), declared host RAM writes and declared initial registers on those states (applied before the first instruction of the condition only, never after execution begins).'),
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=summaries,group_counts=group_counts,covered_PCs=sorted(coverage),uncovered_u5_block_starts=missing_native,uncovered_u4_block_starts=missing_native,uncovered_u2_block_starts=hexset(MODEL_LEADERS-coverage),uncovered_leaders_incl_entry_and_black_boxes=hexset(MODEL_LEADERS-coverage),
        block_start_coverage=block_coverage,block_starts=BLOCKS,boundary_stop_pcs=(0x1a296,0x1a43c,0x1a46a,0x1a75e,0x1a790,RETURN_FF000),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=LIMITATIONS)
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_checks=len(model_checks),
        model_equal=sum(1 for m in model_checks if m['equal']),uncovered=missing_native,full_frame_ok=report['full_frame']['ok'],sha256=sha(path.read_bytes()),tool=tool_sha,seconds=int(time.time()-t_start))))


LIMITATIONS=['Controlled incoming fixtures (rebuilt original seeds, captured states of the original runs, declared RAM / initial-register variants), not natural scheduler / gameplay reachability; direct entries at 1a0b6 / 1a470 / 1a26a / 1a442 / 16fee / 19e60 / 43e08 / 43e22 are declared fixtures (entry PC, A7, stack bytes, registers, bank page); declared RAM writes are applied before the first instruction of the condition only.',
    'The existing executors 18c06, 197da, 19802, 8da2, 43ffc, 17012, 1701a, 28ae and 43e38 are black boxes of the unit: executed natively (their ranges are the earlier observers closures) but not modelled here; the model compares their entry registers as a leader and replays their native exit registers, RAM writes and bank changes (A7 discipline asserted).  The C of 18c06 (consumed at 197a2) is derived by the model from the dispatch word 2(A1) per the U3 contract bytes and cross-checked with the native successor.',
    'Stops are accepted only directly after the RTS that popped the declared return LONG (or after the BSR.W for the chain steps); the code behind is never executed except in the explicit bad-stop guard conditions.',
    'The machine-style observer mirrors the 64KiB work RAM 16 times (the declared stack at 1feffc is image offset effc), unlike the flat map of the original observers: the full-frame comparison with the recorded original masks the live stack window; a copy that wraps the whole 64KiB image (length fffe) overwrites the stack there (observed).',
    'Native carry is unobserved (SR never read); the Unknown-carry API error, block-internal / bundled PC entry rejection and the contract computed-PC policy are API-level decisions, not observed here (the original executes mid-block targets natively).',
    'The game meaning of the RAM fields, the LSPC meaning of 3c0006 / 104d90 and the origin of the opcode 10 / 24 / 44 operands are not established.  Native video port events are instruction accesses, not physical bus cycles.']


def contract_claims(frame_rows,chain_rows,B,specs,negatives):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    ok_=lambda c:'confirmed' if c else 'contradicted'
    rows=CENSUS_ROWS;sc_rows=[r for r in rows if r['kind']=='scene'];in_rows=[r for r in rows if r['kind']=='init']
    script=lambda rs:[r for r in rs if r['pc']==0x1a0b6];place_=lambda rs:[r for r in rs if r['pc']==0x1a470]
    hexop=lambda v:'%02x'%v
    # --- structure
    claim('88 block starts: the observer decode of the contract bytes (branch / call targets, returns, range starts, the 20 BRA.W slots of the computed JMP 1a0bc(PC,D7.W), 43e22) is exactly the contract list; none of the 13 bundled branch PCs is a block start',
        ok_(U5_LEADERS==CONTRACT_STARTS and not (CONTRACT_BUNDLED&U5_LEADERS)),dict(block_starts=len(U5_LEADERS),bundled=len(CONTRACT_BUNDLED)))
    claim('code bytes: the 11 code ranges (872 bytes) and the two PC-relative tables (32 bytes) equal the ROM','confirmed',dict(ranges=len(U5_CODE_RANGES)+len(U5_DATA_RANGES)))
    claim('census: every 1a0b6 / 1a470 / 1a26a / 1a442 state of the original scene_frame and scene_general_initialization runs, run natively, equals the independent model (leader sequence with all registers, ordered RAM / port / ROM-read events, final registers, 64KiB RAM, bank)',
        ok_(not CENSUS_MODEL['unequal'] and not CENSUS_MODEL['model_errors'] and CENSUS_MODEL['equal']==CENSUS_MODEL['runs'] and CENSUS_MODEL['runs']>=len(rows)),dict(model_runs=CENSUS_MODEL['runs'],equal=CENSUS_MODEL['equal'],states=len(rows),extra_runs='D7 probes of the placement fixtures'))
    # --- full frame
    ff_ok=len(frame_rows)==594 and all(r['ok'] for r in frame_rows)
    claim('U2+U3+U4+U5 cover the whole scene frame: all 594 scene_frame seeds run natively from the direct 1a73c entry to the RTS popping ff000 without a guard, reproduced twice, split == continuous, and equal the recorded original run (instruction count, RAM outside the stack window, ordered ports, 14 registers, bank, A7)',
        'not-observed' if not frame_rows else ok_(ff_ok),dict(cases=len(frame_rows),ok=sum(1 for r in frame_rows if r['ok']),failed=[r['case'] for r in frame_rows if not r['ok']][:20],errors=[r.get('error') for r in frame_rows if r.get('error')][:5]))
    if frame_rows:
        sc_cases=sorted(r['case'] for r in frame_rows if r.get('u5_entries',{}).get('script'));pl_cases=sorted(r['case'] for r in frame_rows if r.get('u5_entries',{}).get('placement'))
        claim('the 13 scene_frame cases that reach 1a0b6 are 237 424 437 479 502 509 514 564 577 588 589 590 591 and the 6 that reach 1a470 are 380 436 437 508 576 577',ok_(sc_cases==NATURAL_SCRIPT_CASES and pl_cases==NATURAL_PLACE_CASES),dict(script=sc_cases,placement=pl_cases))
        claim('natural chains (one persistent CPU: direct 1a73c entry -> first U5 entry -> RTS -> ff000) of the 19 cases equal the recorded original run',ok_(len(chain_rows)==19 and all(r['ok'] for r in chain_rows)),dict(chains=len(chain_rows),failed=[r['label'] for r in chain_rows if not r['ok']]))
    # --- scene seeds: command sequences and totals
    seq=collections.defaultdict(list)
    for r in script(sc_rows):seq[r['case']].append(r['opcode'])
    want={237:'3c 38 34 28',424:'30 1c 28',564:'30 1c 28',437:'38 18 28 34 20',577:'38 18 28 34 20',479:'1c 38 34 28',502:'1c 28',509:'18 34 30 28',514:'3c 38 34 28 30 34 2c',
        588:'48 08 00 14 14 14 14 04 40 30 3c 34 24 1c 1c 1c',589:'08 00 14 14 14 14 04 04 40 30 3c 34 0c 24 24 1c 1c 1c 28',591:'08 00 14 14 14 14 04 04 0c 40 30 3c 34 24 24 1c 1c 1c 28'}
    got={c:' '.join(hexop(x) for x in v) for c,v in seq.items()}
    claim('opcode order of the scene seeds (contract list for 237 424 437 479 502 509 514 564 577 588 589 591)',ok_(all(got.get(c)==w for c,w in want.items())),dict(contract=want,observed={c:got.get(c) for c in want},differences=[c for c,w in want.items() if got.get(c)!=w]))
    a589=[int(x,16) for x in want[589].split()]
    claim('case 590 opcode order: "same as 589, the end is 18 28" (ambiguous text): observed sequence reported',ok_(got.get(590) in (' '.join(hexop(x) for x in a589[:-1]+[0x18,0x28]),' '.join(hexop(x) for x in a589[:-4]+[0x18,0x28]))),dict(observed=got.get(590),case_589=got.get(589)))
    tot=collections.Counter(r['opcode'] for r in script(sc_rows))
    want_tot={0:4,4:7,8:4,0xc:3,0x14:16,0x18:4,0x1c:16,0x20:2,0x24:7,0x28:12,0x2c:1,0x30:8,0x34:11,0x38:5,0x3c:6,0x40:4,0x48:1}
    claim('dispatch totals of the scene seeds: 00 4, 04 7, 08 4, 0c 3, 14 16, 18 4, 1c 16, 20 2, 24 7, 28 12, 2c 1, 30 8, 34 11, 38 5, 3c 6, 40 4, 48 1; 10 / 44 / 4c never',ok_(dict(tot)==want_tot),dict(observed={hexop(k):v for k,v in sorted(tot.items())}))
    op04=[int.from_bytes(bytes.fromhex(r['peek'])[2:4],'big') for r in script(sc_rows) if r['opcode']==4]
    claim('opcode 04 indexes (before LSL) of the scene seeds: 2a 5 6 20 44 2e 35; opcode 04 entered in bank 1000 only (physical 200000)',ok_(op04==[0x2a,5,6,0x20,0x44,0x2e,0x35] and all(r['bank']==0x200000 for r in script(sc_rows) if r['opcode']==4)),dict(indexes=[hex(x) for x in op04]))
    o40=[(int.from_bytes(bytes.fromhex(r['peek'])[2:4],'big'),[x for x in r['ports'] if x[1]==0x3c0006]) for r in script(sc_rows) if r['opcode']==0x40]
    claim('opcode 40 in the scene seeds: D0.W 2 / a / a / 8, one 3c0006 WORD port write each with 0100 / 0900 / 0900 / 0700',ok_([d for d,_ in o40]==[2,0xa,0xa,8] and [x[0][2] for _,x in o40]==['0100','0900','0900','0700'] and all(len(x)==1 and x[0][0]==2 for _,x in o40)),dict(observed=[(d,x) for d,x in o40]))
    pl={r['case']:r for r in place_(sc_rows)}
    claim('scene placements: 380 and 508 skip (1a51c), 380 through 1a4b4 BLT, 508 through 1a4a6 BGT; 436 437 due with 28ae success (A0 != 100e98); 576 577 due with 28ae failure (A0 = 100e98); copy length 0; motion non-null',
        ok_(set(pl)=={380,436,437,508,576,577} and '0x1a51c' in pl[380]['leaders'] and '0x1a4b4' in pl[380]['leaders'] and '0x1a51c' in pl[508]['leaders'] and '0x1a4b4' not in pl[508]['leaders']
            and all('0x1a4da' in pl[c]['leaders'] for c in (436,437,576,577)) and all(pl[c]['a0_after_28ae']!=[0x100e98] for c in (436,437)) and all(pl[c]['a0_after_28ae']==[0x100e98] for c in (576,577)) and all(r['motion_ptr']!=0 for r in pl.values())),
        dict({c:dict(leaders=sorted(r['leaders']),a0_after_28ae=[hex(x) for x in r['a0_after_28ae']]) for c,r in pl.items()}))
    # --- init seeds
    itot=collections.Counter(r['opcode'] for r in script(in_rows))
    want_i={0:199,4:402,8:207,0xc:99,0x10:4,0x14:801,0x18:62,0x1c:631,0x20:24,0x24:388,0x28:113,0x2c:24,0x30:235,0x34:221,0x38:24,0x3c:195,0x40:199,0x44:18,0x48:64}
    claim('scene_general_initialization dispatch totals (221 cases): 00 199, 04 402, 08 207, 0c 99, 10 4, 14 801, 18 62, 1c 631, 20 24, 24 388, 28 113, 2c 24, 30 235, 34 221, 38 24, 3c 195, 40 199, 44 18, 48 64, 4c 0',ok_(dict(itot)==want_i),dict(observed={hexop(k):v for k,v in sorted(itot.items())},total=sum(itot.values())))
    ipl=place_(in_rows);succ=[r for r in ipl if r['a0_after_28ae']!=[0x100e98]];fail=[r for r in ipl if r['a0_after_28ae']==[0x100e98]]
    lens=collections.Counter(int.from_bytes(bytes.fromhex(r['peek'])[2:4],'big') for r in ipl)
    claim('init placements: 102 calls of 1a470, 28ae success 79 / failure 23 (A0 = 100e98), copy length 0 x91 / 2 x11, 23 calls reach the bbox tests (1a492) with a null bbox and no skip',
        ok_(len(ipl)==102 and len(succ)==79 and len(fail)==23 and lens=={0:91,2:11} and sum(1 for r in ipl if '0x1a492' in r['leaders'])==23 and not any('0x1a4a2' in r['leaders'] or '0x1a51c' in r['leaders'] for r in ipl)),
        dict(calls=len(ipl),success=len(succ),failure=len(fail),lengths={hex(k):v for k,v in lens.items()},bbox_path=sum(1 for r in ipl if '0x1a492' in r['leaders']),x_range_blocks=sum(1 for r in ipl if '0x1a4be' in r['leaders'])))
    op10=[r for r in script(in_rows) if r['opcode']==0x10];op44=[r for r in script(in_rows) if r['opcode']==0x44]
    claim('opcode 10 (4 calls): operand pointer e6e9e -> LONG 0 -> e89fa publishes the default e89ec (e8a02 path); opcode 44: 18 calls',ok_(len(op10)==4 and all(int.from_bytes(bytes.fromhex(r['peek'])[2:6],'big')==0xe6e9e and '0xe8a02' in r['leaders'] for r in op10) and len(op44)==18),dict(op10=len(op10),op44=len(op44)))
    idx04=[int.from_bytes(bytes.fromhex(r['peek'])[2:4],'big') for r in script(in_rows) if r['opcode']==4]
    claim('init opcode 04: index 0..4c (LSL.W #2 -> 0..130); no seed enters 1a192 in bank 2000',ok_(min(idx04)==0 and max(idx04)==0x4c and all(r['bank']==0x200000 for r in script(in_rows) if r['opcode']==4)),dict(min=min(idx04),max=max(idx04),count=len(idx04)))
    o40i=sorted({int.from_bytes(bytes.fromhex(r['peek'])[2:4],'big') for r in script(in_rows) if r['opcode']==0x40})
    claim('init opcode 40: D0.W takes 2 3 4 8 a 14 (all >= 1, 3d9c only; 3d84 never)',ok_(o40i==[2,3,4,8,0xa,0x14] and not any('0x3d84' in r['leaders'] for r in rows)),dict(values=[hex(x) for x in o40i]))
    sel=lambda ops:sorted({int.from_bytes(bytes.fromhex(r['peek'])[2:4],'big') for rs in (sc_rows,in_rows) for r in script(rs) if r['opcode'] in ops})
    claim('node table indexes of opcodes 14 / 18 / 1c are 0 4 8 c, path state indexes of opcode 24 are 0 4 8',ok_(sel((0x14,0x18,0x1c))==[0,4,8,0xc] and sel((0x24,))==[0,4,8]),dict(node=sel((0x14,0x18,0x1c)),path=sel((0x24,))))
    cov_all=set();cov_sc=set();cov_in=set()
    for r in rows:
        ls={int(k,16) for k in r['leaders']&set() } if False else {int(k,16) for k in r['leaders']}
        cov_all|=ls;(cov_sc if r['kind']=='scene' else cov_in).update(ls)
    never={0x1a108,0x1a16e,0x1a24e,0x1a4a2,0x3d84}
    claim('88 block starts: 83 are executed by the seeds, the five never executed are 1a108 1a16e (opcode 4c), 1a24e (opcode 2c negative), 1a4a2 (bbox non-null), 3d84 (opcode 40 with 0); init alone leaves 1a108 1a16e 1a24e 1a4a2 1a51c 3d84; scene alone leaves 15 (1a0cc 1a100 1a108 1a10c 1a15e 1a16e 1a24e 1a4a2 1a4be 1a4d0 1a514 3d84 e89fa e8a02 e8a06)',
        ok_(U5_LEADERS-cov_all==never and U5_LEADERS-cov_in=={0x1a108,0x1a16e,0x1a24e,0x1a4a2,0x1a51c,0x3d84} and U5_LEADERS-cov_sc=={0x1a0cc,0x1a100,0x1a108,0x1a10c,0x1a15e,0x1a16e,0x1a24e,0x1a4a2,0x1a4be,0x1a4d0,0x1a514,0x3d84,0xe89fa,0xe8a02,0xe8a06}),
        dict(seed_union=len(cov_all),never=hexset(U5_LEADERS-cov_all),scene_missing=hexset(U5_LEADERS-cov_sc),init_missing=hexset(U5_LEADERS-cov_in)))
    claim('stream and record pointers of all seed states lie in the fixed ROM (below 100000)',ok_(all(r['a1']<0x100000 for r in rows if r['pc'] in (0x1a0b6,0x1a470))),dict(states=sum(1 for r in rows if r['pc'] in (0x1a0b6,0x1a470))))
    # --- stack depth
    d00=[r for r in script(rows) if r['opcode']==0];dother=[r for r in script(rows) if r['opcode'] not in (0,4,8)]
    claim('stack: the unit uses 12 bytes below the entry A7 on the opcode 00 path (push A1 + BSR 19772 + BSR 18c06) and 8 bytes on the other handlers (push A1 + one call), measured at the leaders and black-box entries',
        ok_(max(r['unit_stack_depth'] for r in d00)==12 and max(r['unit_stack_depth'] for r in script(rows) if r['opcode']!=0)==8),dict(op00=max(r['unit_stack_depth'] for r in d00),other=max(r['unit_stack_depth'] for r in script(rows) if r['opcode']!=0)))
    pr=place_(rows);null_gen=[r for r in pr if r['motion_ptr']==0 and '0x1a4da' in r['leaders']];motion_rows=[r for r in pr if r['motion_ptr']!=0];null_nogen=[r for r in pr if r['motion_ptr']==0 and '0x1a4da' not in r['leaders']]
    depth=lambda rs:max([r['native_stack_depth'] for r in rs] or [None])
    claim('stack: the placement path uses 24 bytes below the entry A7 when the motion pointer is non-null (19802 call 4 + U3 19812 path 20); the generation path alone (null motion: 19802 returns at once) uses 16 bytes (push 8 + JSR 4 + 28ae push 4)',
        ok_(depth(null_gen)==16 and depth(motion_rows)==24),dict(generation_null_motion_max=depth(null_gen),generation_null_motion_rows=len(null_gen),motion_non_null_max=depth(motion_rows),motion_non_null_rows=len(motion_rows),null_motion_without_generation_max=depth(null_nogen),null_motion_without_generation_rows=len(null_nogen)))
    # --- D7 of 19802
    dc=[(r['due_checks'][0],r) for r in place_(rows)]
    dif=[(d,r) for d,r in dc if (d['record_time']>=d['phase'])!=(d['d7_word']>=d['phase'])]
    claim('1a470 compares the D7 returned by 19802 (upper word after SWAP D7), not the record time: in every seed call the native branch (1a4da directly = BCC taken) equals (D7.W >= phase); calls where the record-time predictor would differ are listed',
        ok_(all(d['due']==(d['d7_word']>=d['phase']) for d,r in dc) and len(dif)>0 and all(('0x1a492' not in r['leaders'])==d['due'] for d,r in dc)),dict(calls=len(dc),record_time_predictor_differs=len(dif),examples=[dict(d,case=r['case'],pc=hex(r['pc'])) for d,r in dif[:6]]))
    ev=EVIDENCE
    due_fx=[l for l in ev if l.startswith('fixture-place-due-')]
    claim('declared due fixtures: with phase = D7+1 and record time ffff the original is NOT due (BCC not taken: 1a492 bbox tests reached); with phase = D7 and record time 0 it is due (BCC taken: 1a4da without 1a492)',
        ok_(all('0x1a492' in ev[l]['leaders'] for l in due_fx if 'd7-says-notdue' in l) and all(('0x1a4da' in ev[l]['leaders'] and '0x1a492' not in ev[l]['leaders']) for l in due_fx if l.startswith('fixture-place-due-d7-says-due')) and due_fx),dict(conditions=due_fx))
    # --- 28ae failure / fallback
    f28=[l for l in ev if l.startswith('fixture-place-28ae-fail')]
    claim('28ae failure path: carry is ignored (1a4ee MOVE.W), A0 = 100e98: 43e08 writes LONG object+10 / coordinates / WORD 24 at 100ec6.. (A0 + 2e) and the payload goes to 100f0e; reproduced for 104ca0 = 0 and for a null callback',
        ok_(f28 and all(ev[l]['model']['a0_after_28ae']==[0x100e98] and ev[l]['writes_43e08'] and ev[l]['writes_43e08'][0][0]=='0x100ed6' for l in f28 if ev[l].get('model'))),dict(conditions=f28,writes=ev[f28[0]]['writes_43e08'] if f28 else None))
    # --- copy lengths
    cl={l:ev[l] for l in ev if l.startswith('fixture-place-copy-length-') and ev[l]['guard'] is None and ev[l].get('model')}
    def iters(e):return e['leader_hits'].get('0x1a514',0)
    expect_ok=True;rep={}
    for l,e in cl.items():
        ln=int(l.split('-')[4],16) if l.split('-')[4] not in ('odd',) else None
        if ln is None:continue
        want_iters=0 if ln==0 else ln//2
        rep[l]=(hex(ln),iters(e),want_iters)
        if iters(e)!=want_iters:expect_ok=False
    claim('1a514 copy loop: even lengths copy len/2 WORDs (0: 1a51a at once, 8002: 16385 iterations with the unsigned count)',ok_(expect_ok and rep),dict(iterations=rep))
    odd=[l for l in ev if l.startswith('fixture-place-copy-length-odd') and 'default-free-list' not in l]
    claim('1a514 odd record length (1, 3): the loop never reaches zero; the native run ends in an access error (write of the 1a514 MOVE.W (A1)+ to the read-only bank window at 200000, unmapped_or_protected) after the iterations listed, not at an instruction budget',
        ok_(odd and all(ev[l]['guard'] and ev[l]['guard']['problem']=='unmapped_or_protected' and ev[l]['guard']['address']==0x200000 and ev[l]['guard']['pc']==0x1a514 and 100<iters(ev[l])<5000 for l in odd)),dict({l:dict(guard=ev[l]['guard'],iterations=iters(ev[l]),instructions=ev[l]['instructions']) for l in odd}))
    hv=[l for l in ev if 'default-free-list' in l]
    claim('1a514 odd length with the unmodified free list (about 520000 iterations, 1.5 million instructions): the end is the same access error (the A1 write reaches the read-only bank window at 200000), reached before 1,000,000 blocks of the machine budget (one block per iteration)',
        ok_(hv and all(ev[l]['guard'] and ev[l]['guard']['problem']=='unmapped_or_protected' and ev[l]['guard']['address']==0x200000 and ev[l]['leader_hits'].get('0x1a514',0)<1000000 for l in hv)),dict({l:dict(guard=ev[l]['guard'],iterations=ev[l]['leader_hits'].get('0x1a514'),instructions=ev[l]['instructions']) for l in hv}))
    skp={l:ev[l] for l in ev if l.startswith('fixture-place-skip-length-')}
    ok_skip=True;rep={}
    for l,e in skp.items():
        ln=int(l.split('-')[-1],16);a0i=e['entry']['a0'];a0f=e['final']['a0'];want_a0=(a0i+0x10+sx16(ln))&M32;rep[l]=(hex(ln),hex(a0i),hex(a0f),hex(want_a0))
        if a0f!=want_a0:ok_skip=False
    claim('skip path 1a51c: A0 = A0 + 10 + sign-extended record length (8002 moves backwards), whereas the copy path advances by the unsigned length',ok_(ok_skip and skp),dict(rows=rep))
    bb=[l for l in EXPECT if l.startswith('fixture-place-bbox-')];bbok=True;bbrep=collections.Counter()
    nxt={1:'0x1a4b4',2:'0x1a4be',3:'0x1a4d0',4:'0x1a4da'}
    for l in bb:
        cmp_,skip=EXPECT[l];lead=ev[l]['leaders']
        reached_next=nxt[cmp_] in lead;got_skip=not reached_next and ('0x1a51c' in lead)
        if cmp_==4:got_skip=('0x1a4da' not in lead) and ('0x1a51c' in lead)
        if got_skip!=skip or ('0x1a51c' in lead)!=skip:bbok=False
        bbrep[(cmp_,skip)]+=1
    claim('bounding box compares (1a4a6 BGT 53f8, 1a4b4 BLT 53f6, 1a4be BGT 53f4 after SUB 53a6, 1a4d0 BLT 53f2) at the limit -1 / 0 / +1 of the value computed from the declared record, bbox, 10d3a6 = 0 and 0100 and WORD wrap: the native skip decision (1a51c) equals the decision computed from the bytes in all fixtures, independent of the model',
        ok_(bb and bbok),dict(conditions=len(bb),by_compare_and_skip={str(k):v for k,v in sorted(bbrep.items())}))
    lo_=lambda l:ev[l]['gate_hits']
    lp=lambda t:'fixture-loop-'+t;gt=lambda t:'fixture-gate-'+t
    claim('1a296 loop: five commands then a negative WORD run 1a0b6 five times and end at 1a28a; a wait command ends at 1a29c; a wait counter above the phase returns at 1a29c without 1a0b6; a negative first WORD ends at 1a28a',
        ok_(ev[lp('five-commands-then-terminator')]['leader_hits'].get('0x1a0b6')==5 and '0x1a28a' in lo_(lp('five-commands-then-terminator')) and '0x1a29c' in lo_(lp('wait-command')) and '0x1a0b6' not in ev[lp('wait-not-due')]['leaders'] and '0x1a29c' in lo_(lp('wait-not-due'))
            and '0x1a28a' in lo_(lp('terminator-only')) and '0x1a0b6' not in ev[lp('terminator-only')]['leaders']),dict({t:dict(u5=ev[lp(t)]['leader_hits'],gate=ev[lp(t)]['gate_hits']) for t in ('five-commands-then-terminator','wait-command','wait-already-due','wait-not-due','terminator-only','opcode-04-through-gate')}))
    claim('1a442 placement gate: null cursor returns at 1a44e, first WORD ffff at 1a45a, record time above the phase at 1a464, time <= phase calls 1a470 (1a466) and returns through 1a46a',
        ok_('0x1a44e' in lo_(gt('cursor-null')) and '0x1a45a' in lo_(gt('terminator-ffff')) and '0x1a464' in lo_(gt('not-due')) and '0x1a466' in lo_(gt('due-equal')) and '0x1a46a' in lo_(gt('due-equal')) and '0x1a470' in ev[gt('due-zero')]['leaders'] and '0x1a470' not in ev[gt('not-due')]['leaders']),
        dict({t:dict(u5=ev[gt(t)]['leaders'][:3],gate=ev[gt(t)]['gate_hits']) for t in ('cursor-null','terminator-ffff','not-due','due-equal','due-zero')}))
    # --- opcode 04
    o4=[l for l in ev if l.startswith('fixture-op04-index-') and ev[l]['guard'] is None and 'exploratory' not in l or l.startswith('fixture-op04-bank2000')]
    o4ok=True
    for l in o4:
        e=ev[l]
        if e['ram_writes_100010']!=['0000'] or [x for x in e['unit_ports']]!=[(2,'0x2ffff2','1000'),(2,'0x2ffff0','0000')]:o4ok=False
        br=[b for b in e['bank_reads_unit'] if b['address']=='0x20000c']
        if not br or br[0]['bank_at_read']!='0x200000' or br[0]['bytes']!='002003d0':o4ok=False
    claim('opcode 04: WORD 0 -> 100010, WORD 1000 -> 2ffff2 and 0 -> 2ffff0 first; then LONG 20000c is read in bank 1000 (physical 20000c = 002003d0), also when entered in the declared bank 2000 state; bank 1000 persists after the handler',ok_(o4ok and len(o4)>=7),dict(conditions=len(o4),example=ev[o4[0]]['bank_reads_unit'][:2],final_bank={l:ev[l]['bank_after'] for l in o4[:3]}))
    # --- opcode 40
    o40f=[l for l in ev if l.startswith('fixture-op40-d0-')];o40ok=True;rep={}
    for l in o40f:
        parts=l.split('-');d0=int(parts[3],16);init=int(parts[5],16);e=ev[l]
        want_v=((0<<8)|(init|8)) if (d0&0xffff)==0 else ((((d0-1)&0xff)<<8)|(init&0xf7))
        got_p=[x for x in e['unit_ports'] if x[1]=='0x3c0006']
        rep[l]=(want_v,got_p)
        if not (len(got_p)==1 and got_p[0][0]==2 and int(got_p[0][2],16)==want_v):o40ok=False
        if ('0x3d84' in e['leaders'])!=(d0==0) or ('0x3d9c' in e['leaders'])!=(d0!=0):o40ok=False
    claim('opcode 40 (3d7e): D0.W = 0 -> 3d84 (BYTE 0 -> 104d90, BSET #3 on 104d91, WORD 104d90 -> 3c0006), D0.W >= 1 -> 3d9c (BYTE D0-1 -> 104d90, BCLR #3); exactly one WORD video port write 3c0006 = (BYTE << 8 | 104d91) in 30 fixtures; the observer extension classifies it as a video port event',ok_(o40ok and len(o40f)==30),dict(conditions=len(o40f),extension=EXTENSION))
    a5=[l for l in ev if l.startswith('fixture-op40-a5-shifted')]
    claim('opcode 40 with A5 = 108020: the BYTE 104d90 write is absolute while the 104d91 / WORD source are A5 relative (104db1 / 104db0): the port value differs from the unshifted formula',ok_(a5),dict({l:ev[l]['unit_ports'] for l in a5}))
    # --- computed PC
    cp={l:ev[l] for l in ev if l.startswith('fixture-opword-')}
    claim('computed opcode words: 0050 -> 1a10c, 005a -> 1a116, 0060 -> 1a11c, 01ae -> 1a26a run the target block natively; 0052 (mid-block) and fffe (-2) are observed natively; odd / far words (0001, 7ffe, 7fff, 8000) end at the first non-code PC (unsupported_code_target)',
        ok_('0x1a10c' in cp['fixture-opword-0050-lands-on-opcode-10-body']['leaders'] and '0x1a116' in cp['fixture-opword-005a-lands-on-opcode-0c-body']['leaders'] and '0x1a11c' in cp['fixture-opword-0060-lands-on-opcode-30-body']['leaders']),
        dict({l:(e['guard'] or e['leaders']) for l,e in cp.items()},guards={l:ev[l]['guard'] for l in ev if l.startswith('guard-opword')}))
    five={}
    for pc_ in ('0x1a108','0x1a16e','0x1a24e','0x1a4a2','0x3d84'):
        five[pc_]=[l for l,e in ev.items() if pc_ in e['leaders'] and e.get('model') and e['model']['equal']][:3]
    claim('opcode 4c (1a108 1a16e) / 2c negative first WORD (1a24e) / bbox non-null (1a4a2) / opcode 40 with 0 (3d84): the five blocks no seed executes run natively in declared fixtures and equal the model',ok_(all(five.values())),five)
    a5l=[l for l in ev if 'a5-shifted' in l]
    claim('A5 relative accesses use the live A5 (declared A5 = 108020 for opcodes 30 and 40; the model addresses d16(A5) with the live A5 and the absolute 104d90 with its constant): native == model for every shifted fixture',
        ok_(a5l and all(ev[l].get('model') and ev[l]['model']['equal'] for l in a5l)),dict(conditions=a5l))
    bad_mn=sorted({r['mnemonic'] for lo,hi in U5_CODE_RANGES for r in disassemble_range(PROGRAM,lo,hi-lo,lo) if r['mnemonic'].split('.')[0] in ('addx','subx','negx','roxl','roxr','abcd','sbcd','nbcd')})
    claim('X-bit consumers: none in U5 (no ADDX / SUBX / NEGX / ROXx / ABCD / SBCD / NBCD among the decoded instructions of the 11 ranges)',ok_(not bad_mn),dict(found=bad_mn,instructions=sum(len(disassemble_range(PROGRAM,lo,hi-lo,lo)) for lo,hi in U5_CODE_RANGES)))
    claim('carry: the C returned by 18c06 (type word < 58 -> C=1, else 0) selects 197a6 / 197b2; the C of 28ae is not consumed; U5 produces no known carry','confirmed' if all(c['model_carry'] is not None and ((c['native_successor']==0x197a6)==(c['model_carry']==1)) for r in rows for c in (r['carry_18c06'] or []) if c['native_successor'] in (0x197a6,0x197b2)) else 'contradicted',
        dict(checked=sum(len(r['carry_18c06'] or []) for r in rows)))
    claim('negative stop checks: stops at internal return addresses (1a1be 1a186 1a4ee 1a500) are reached natively but refused by the stop evidence','confirmed' if negatives and all(n['stop_evidence_refused'] for n in negatives) else 'contradicted',negatives)
    return claims


if __name__=='__main__':main()
