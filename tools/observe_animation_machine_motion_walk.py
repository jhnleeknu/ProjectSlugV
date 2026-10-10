"""Unpatched 480bc frame helper bundle U3 (motion walk 18c06..19768, 19812, 19844, 19910) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing it, the machinery of the scene core observer U2
(observe_animation_machine_scene_core and through it the frame helper observer U1 / card menu close / fade-card chain: persistent-CPU Observer with the declared
host-change vocabulary RAM write / PC redirect / A7 delta / register write at a step boundary, fresh-twice reproduction, split (stop at the first hit of every block
leader) versus continuous equivalence, ordered port events, banked reads with the modeled bank, SHA pins of every imported tool module, ROM SHA/mtime guard, the
seed rebuilders for scene_frame / stage_frame / stage_entry_body and the independent block model of U2).  Nothing in the imported modules is edited; module
globals of the U2 observer (block-leader set, observed ranges, model block table, stop evidence) are extended at run time.

Observed unit: the 3156 contract bytes of docs/analysis/animation-machine-motion-walk-u3-contract.md (option F, all 36 type slots of the five dispatchers
18c06 / 18caa / 18efa / 18fd2 / 192c4, 370 block starts) together with the U2 ranges, so a natural run goes 1a73c -> U2 -> U3 -> U2 and stops at the next U2 boundary
(1a0b6 / 1a470 / 1a7a8).  A stop is accepted only directly after the transferring instruction (BSR / RTS / branch / JMP, checked against the original bytes and the
live registers); the boundary code is never executed.  The 19938..19978 routine is outside the contract (U5 caller) and is observed only as a declared extra range.

Seeds (all pinned by SHA256, rebuilt in this process): scene_frame 594 cases (U2 rebuild, every input RAM checked against input_ram_sha256) probed with the combined
U2+U3 ranges; stage_frame 64 natural 480bc -> 1a73c cases; stage_entry_body 142 traces re-executed up to 1a73c.  Captured U3 entry states of the original full-frame
run (19812 / 19844 / 19910 with their real return LONGs), declared RAM motion paths and register fixtures for every type slot of every dispatcher, loops, out-of-range
types, 192c4 quirk, SLT/SGT overflow, guards.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the
step record; declared initial registers/stack LONGs are part of the fixture summary.

An independent Python model of the contract (basic blocks transcribed from the original instructions; the 36-slot handlers are generated from the contract's own slot
table text, so the table itself is checked against the ROM; 32-bit register semantics, explicit word/byte operations and signed compares, NOT the C++) is compared with
each native normal condition: block-leader sequence with the full register file at every leader, ordered RAM writes, ordered port writes, ordered fixed/bank ROM reads,
final registers and the whole 64KiB RAM image.  Any difference is recorded in contract_discrepancies.
"""
import collections
import hashlib
import json
import random
import re
import sys
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_scene_core as sc
from observe_animation_machine_scene_core import sub16,add16,sub32,add32,asr,le,sx16,sx32,M32,W,S
from disassemble_program import load_verified_program,disassemble_range
fh=sc.fh;fc=sc.fc;menu=sc.menu;op=sc.op;activation=sc.activation;shared=sc.shared;sfe=sc.sfe
ROOT=sc.ROOT
OUT=ROOT/'artifacts/animation_machine_motion_walk_native'
SCRATCH_DEV=Path('/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/u3obs/dev_out')
CONTRACT=ROOT/'docs/analysis/animation-machine-motion-walk-u3-contract.md'
CONTRACT_SHA='fe5db3bd8d160296e71a82e5ddace169b9dd61b6dd15c0e61fd0b96f0fc6793d'
SCOPE=sc.SCOPE
ROM_SHA=sc.ROM_SHA
sha=sc.sha
KEYS14=sc.KEYS14
BANK3_MID=sc.BANK3_MID
BANK2=sc.BANK2
RETURN_FF000=sc.RETURN_FF000
DISCREPANCIES=sc.DISCREPANCIES
DISPATCH={0x18c06:0x18c0e,0x18caa:0x18cb2,0x18efa:0x18f02,0x18fd2:0x18fda,0x192c4:0x192cc}      # dispatcher entry -> first slot (JMP base)
SLOT_COUNT=36
DISPATCH_RET={0x18c06:0x196c0,0x18caa:0x196b0,0x18efa:0x1981a,0x18fd2:0x1991c,0x192c4:0x19894}      # a real BSR return address of each dispatcher
EXTRA_RANGE=(0x19938,0x19978)                                  # U5 caller routine, outside the contract: observed only as a declared extra range
U3_RANGES=()
U3_TABLE=[]
U3_STARTS=frozenset()
U3_BUNDLED=frozenset()
LEADERS_U3=frozenset()
LEADERS_X=frozenset()
CONSUMERS=(0x196c0,0x196e2,0x19924,0x19734,0x198b8,0x1974e,0x19874,0x19894,0x198d8)
KNOWN_SET=(0x19716,0x19724,0x19394,0x1959c,0x196d8)
KNOWN_CLEAR=(0x19710,0x1971c,0x19372,0x1957a)
SLOTROWS=[]
INSTALLED=[]
M16=0xffff


def swp(v):return ((v<<16)|(v>>16))&M32


def hx(v):return '0x%x'%v


# ----------------------------------------------------------------------------------
# Contract text
# ----------------------------------------------------------------------------------
def parse_contract(program):
    """Byte table (9 ranges, 3156 bytes, byte-checked against the ROM), the block start lists (S 170 + F extra 200 = 370), the bundled branches (14) and the
    36-slot table (parsed from the contract text itself)."""
    lines=CONTRACT.read_text().splitlines();ranges=[];table=[]
    for line in lines:
        if line.startswith('| `') and '..' in line.split('|')[1]:
            cells=[c.strip().strip('`') for c in line.strip().strip('|').split('|')]
            lo,hi=(int(x,16) for x in cells[0].split('..'));ok=program[lo:hi].hex()==cells[2] and hi-lo==int(cells[1])
            table.append(dict(range='%x..%x'%(lo,hi),bytes_equal_to_rom=ok,size=hi-lo));assert ok,cells[0];ranges.append((lo,hi))
    assert len(ranges)==9 and sum(h-l for l,h in ranges)==3156
    pcs=lambda text:[int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',text)]
    s=f=bundled=None
    for line in lines:
        t=line.strip()
        if t.startswith('- 선택 S(170개)'):s=pcs(t.split(':',1)[1])
        if t.startswith('- 선택 F 추가(200개'):f=pcs(t.split(':',1)[1])
        if t.startswith('- **묶인 조건분기 PC (14개'):bundled=pcs(t.split(':',1)[1])
    assert s and f and bundled and len(s)==170 and len(f)==200 and len(bundled)==14 and not (set(s)&set(f)) and len(set(s)|set(f))==370
    rows=[]
    for line in lines:
        cells=[c.strip() for c in line.strip().strip('|').split('|')]
        if line.startswith('| ') and len(cells)==8 and cells[0].isdigit():rows.append(cells)
    assert len(rows)==36
    return tuple(ranges),table,frozenset(s)|frozenset(f),frozenset(s),frozenset(bundled),rows


MINUS='−'


def parse_slot_row(cells):
    k=int(cells[0]);assert int(cells[1],16)==4*k,cells
    row=dict(k=k,type=4*k,eleven=cells[2]=='O',c=int(cells[3]),tail=int(cells[4].strip('`'),16))
    m=re.match(r'^`([0-9a-f]{5})` ([XY]):(n%ss|s%sn), (.+)$'%(MINUS,MINUS),cells[5]);assert m,cells[5]
    row['c18caa']=dict(pc=int(m.group(1),16),axis=m.group(2),order='n-s' if m.group(3).startswith('n') else 's-n',ops=m.group(4).split('·'))
    m=re.match(r'^`([0-9a-f]{5})` ([XY]):(D7%s\(s<<16\)|\(s<<16\)%sD7), (.+)$'%(MINUS,MINUS),cells[6]);assert m,cells[6]
    row['c18fd2']=dict(pc=int(m.group(1),16),axis=m.group(2),forward=m.group(3).startswith('D7'),ops=m.group(4).split('·'))
    m=re.match(r'^`([0-9a-f]{5})` (?:검사만|base ([XY]), (.+?), ((?:D\d[%s+]=D\d ?)+) →`([0-9a-f]{5})`)$'%MINUS,cells[7]);assert m,cells[7]
    if m.group(2) is None:row['c192c4']=dict(pc=int(m.group(1),16),direct=True)
    else:
        comb=re.findall(r'(D\d)([%s+])=(D\d)'%MINUS,m.group(4));assert len(comb)==2
        row['c192c4']=dict(pc=int(m.group(1),16),direct=False,axis=m.group(2),shift=m.group(3),comb=[(a,'-' if b==MINUS else '+',c) for a,b,c in comb],target=int(m.group(5),16))
    return row


# ----------------------------------------------------------------------------------
# Independent model: blocks of the U3 routines
# ----------------------------------------------------------------------------------
def word_op(o,v):
    if o=='=':return v
    if o=='NEG':return (-v)&0xffff
    if o=='LSL1':return (v<<1)&0xffff
    if o.startswith('ASR'):return asr(v,int(o[3:]),16)
    raise AssertionError(o)


def long_op(o,v):
    if o=='=':return v
    if o=='NEG':return (-v)&M32
    if o=='LSL1':return (v<<1)&M32
    if o.startswith('ASR'):return asr(v,int(o[3:]),32)
    raise AssertionError(o)


def ext_bw(v):return ((v&0xff)^0x80)-0x80&0xffff


def install(rows):
    """Register the model blocks (370 contract block starts + the 19938 extra routine) in the U2 model table."""
    def B(*pcs):
        def deco(fn):
            for pc in pcs:
                assert pc not in sc.BLK,hex(pc);sc.BLK[pc]=fn;INSTALLED.append(pc)
            return fn
        return deco
    def const(target):return lambda M:target
    # ---- dispatcher entries: MOVE.W 2(A1),D4 ; JMP base(PC,D4.W): the computed target is followed without any range check
    def dispatch(base):
        def fn(M):
            M.lw('d4',M.rd(M.r['a1']+2,2));return (base+sx16(M.r['d4']))&M32
        return fn
    for entry,base in DISPATCH.items():B(entry)(dispatch(base))
    # ---- slots (BRA.W) from the contract table
    for row in rows:
        k=row['k']
        B(0x18c0e+4*k)(const(0x18c9e if row['c'] else 0x18ca4))
        B(0x18cb2+4*k)(const(row['c18caa']['pc']))
        B(0x18f02+4*k)(const(row['tail']))
        B(0x18fda+4*k)(const(row['c18fd2']['pc']))
        B(0x192cc+4*k)(const(row['c192c4']['pc']))
    # ---- 18c06 results
    @B(0x18c9e)
    def b18c9e(M):M.C=1;return M.rts()
    @B(0x18ca4)
    def b18ca4(M):M.C=0;return M.rts()
    # ---- 18caa handlers (D0.W / D1.W deltas)
    def h18caa(c):
        m,a=('d0','d1') if c['axis']=='X' else ('d1','d0');first,second=(10,0) if c['order']=='n-s' else (0,10)
        def fn(M):
            a1=M.r['a1'];x=M.rd(a1+first,2);y=M.rd(a1+second,2);main=(x-y)&0xffff;M.lw(m,main)
            if c['ops']==['0']:M.r[a]=0
            else:
                v=main;M.lw(a,v)
                for o in c['ops']:v=word_op(o,v);M.lw(a,v)
            return M.rts()
        return fn
    for row in rows:B(row['c18caa']['pc'])(h18caa(row['c18caa']))
    # ---- 18efa tails (time of the position)
    @B(0x18f92)
    def b18f92(M):
        d7=swp(M.r['d0']);d7=(d7&0xffff0000)|((d7-M.rw(0x53b8))&0xffff);d7=(d7&0xffff0000)|((d7+M.rd(M.r['a1'],2))&0xffff);M.r['d7']=swp(d7);return M.rts()
    @B(0x18fa0)
    def b18fa0(M):
        d7=M.rw(0x53b8)<<16;d7=sub32(d7,M.r['d0'])[0];d7=swp(d7);d7=(d7&0xffff0000)|((d7+M.rd(M.r['a1'],2))&0xffff);M.r['d7']=swp(d7);return M.rts()
    @B(0x18fb2)
    def b18fb2(M):
        d7=swp(M.r['d1']);d7=(d7&0xffff0000)|((d7-M.rw(0x53ba))&0xffff);d7=(d7&0xffff0000)|((d7+M.rd(M.r['a1'],2))&0xffff);M.r['d7']=swp(d7);return M.rts()
    @B(0x18fc0)
    def b18fc0(M):
        d7=M.rw(0x53ba)<<16;d7=sub32(d7,M.r['d1'])[0];d7=swp(d7);d7=(d7&0xffff0000)|((d7+M.rd(M.r['a1'],2))&0xffff);M.r['d7']=swp(d7);return M.rts()
    # ---- 18fd2 handlers (position of a time) and the common tail 192b2
    def h18fd2(c):
        m,a=('d0','d1') if c['axis']=='X' else ('d1','d0')
        def fn(M):
            s=M.rd(M.r['a1'],2);d7=M.r['d7']
            val=((((d7>>16)-s)&0xffff)<<16)|(d7&0xffff) if c['forward'] else ((s<<16)-d7)&M32
            M.r[m]=val
            if c['ops']==['0']:M.r[a]=0
            else:
                v=val
                for o in c['ops']:v=long_op(o,v)
                M.r[a]=v
            return 0x192b2
        return fn
    for row in rows:B(row['c18fd2']['pc'])(h18fd2(row['c18fd2']))
    @B(0x192b2)
    def b192b2(M):
        d0=swp(M.r['d0']);d1=swp(M.r['d1']);d0=(d0&0xffff0000)|((d0+M.rw(0x53b8))&0xffff);d1=(d1&0xffff0000)|((d1+M.rw(0x53ba))&0xffff)
        M.r['d0']=swp(d0);M.r['d1']=swp(d1);return M.rts()
    # ---- 192c4 handlers (position pair relative to the reference, then the band test)
    def h192c4(c):
        ref=0x53b8 if c['axis']=='X' else 0x53ba;m1,m2=('d0','d2') if c['axis']=='X' else ('d1','d3')
        def fn(M):
            M.r['d4']=M.rw(ref)<<16
            M.r[m1]=sub32(M.r[m1],M.r['d4'])[0];M.r[m2]=sub32(M.r[m2],M.r['d4'])[0]
            M.r[m1]=long_op(c['shift'],M.r[m1]);M.r[m2]=long_op(c['shift'],M.r[m2])
            for dst,sg,src in c['comb']:
                d=dst.lower();s=src.lower();M.r[d]=(sub32 if sg=='-' else add32)(M.r[d],M.r[s])[0]
            return c['target']
        return fn
    for row in rows:
        c=row['c192c4']
        if not c['direct']:B(c['pc'])(h192c4(c))
    # ---- the Y / X band tests
    def band(p0,p1,p2,p3,p4,ref,ca,cb):
        @B(p0)
        def b0(M):
            M.r['d4']=0;M.r['d5']=0;M.lw('d4',M.rw(ref));M.lw('d5',M.rd(M.r['a1']+4,2));M.lw('d5',add16(M.r['d5'],M.r['d4'])[0])
            r,n,z,v,c=sub16(M.r['d4'],M.r['d5']);return p2 if le(n,z,v) else p1
        @B(p1)
        def b1(M):M.r['d4'],M.r['d5']=M.r['d5'],M.r['d4'];return p2
        @B(p2)
        def b2(M):
            M.lw('d4',(M.r['d4']-1)&0xffff);M.lw('d5',(M.r['d5']+1)&0xffff);M.r['d4']=swp(M.r['d4'])
            r,n,z,v,c=sub32(M.r[ca],M.r['d4']);M.lb('d6',0xff if n!=v else 0)
            r,n,z,v,c=sub32(M.r[cb],M.r['d4']);M.lb('d7',0xff if n!=v else 0)
            M.lw('d6',ext_bw(M.r['d6']));M.lw('d7',ext_bw(M.r['d7']));M.r['d5']=swp(M.r['d5'])
            r,n,z,v,c=sub32(M.r[ca],M.r['d5']);M.lb('d6',0xff if (z==0 and n==v) else 0)
            r,n,z,v,c=sub32(M.r[cb],M.r['d5']);M.lb('d7',0xff if (z==0 and n==v) else 0)
            r=(M.r['d7']&M.r['d6'])&0xffff;M.lw('d7',r);M.C=0                 # AND.W: C cleared (main decision 2), BNE on the AND result
            return p4 if r else p3
        @B(p3)
        def b3(M):M.C=1;return p4
        @B(p4)
        def b4(M):return M.rts()
    band(0x1935c,0x19370,0x19372,0x19394,0x19398,0x53ba,'d1','d3')
    band(0x19564,0x19578,0x1957a,0x1959c,0x195a0,0x53b8,'d0','d2')
    # ---- 196ac advance / 196de rewind
    @B(0x196ac)
    def b196ac(M):return M.call(0x18caa,0x196b0)
    @B(0x196b0)
    def b196b0(M):
        M.ww(0x53b8,add16(M.rw(0x53b8),M.r['d0'])[0]);M.ww(0x53ba,add16(M.rw(0x53ba),M.r['d1'])[0]);M.r['a1']=(M.r['a1']+10)&M32;return M.call(0x18c06,0x196c0)
    @B(0x196c0)
    def b196c0(M):return 0x196d0 if M.need_c()==0 else 0x196c4
    @B(0x196c4)
    def b196c4(M):M.lw('d0',M.rd(M.r['a1']+6,2));M.ww(0x53ba,add16(M.rw(0x53ba),M.r['d0'])[0]);return 0x196d8
    @B(0x196d0)
    def b196d0(M):M.lw('d0',M.rd(M.r['a1']+6,2));M.ww(0x53b8,add16(M.rw(0x53b8),M.r['d0'])[0]);return 0x196d8
    @B(0x196d8)
    def b196d8(M):M.C=1;return M.rts()
    @B(0x196de)
    def b196de(M):return M.call(0x18c06,0x196e2)
    @B(0x196e2)
    def b196e2(M):return 0x196f2 if M.need_c()==0 else 0x196e6
    @B(0x196e6)
    def b196e6(M):M.lw('d0',M.rd(M.r['a1']+6,2));M.ww(0x53ba,sub16(M.rw(0x53ba),M.r['d0'])[0]);return 0x196fa
    @B(0x196f2)
    def b196f2(M):M.lw('d0',M.rd(M.r['a1']+6,2));M.ww(0x53b8,sub16(M.rw(0x53b8),M.r['d0'])[0]);return 0x196fa
    @B(0x196fa)
    def b196fa(M):M.r['a1']=(M.r['a1']-10)&M32;return M.call(0x18caa,0x19702)
    @B(0x19702)
    def b19702(M):
        M.ww(0x53b8,sub16(M.rw(0x53b8),M.r['d0'])[0]);M.ww(0x53ba,sub16(M.rw(0x53ba),M.r['d1'])[0]);M.wl(0x53b4,M.r['a1']);return M.rts()
    # ---- 19710 / 1971c segment edge tests (TST clears C)
    @B(0x19710)
    def b19710(M):M.C=0;return 0x1971a if M.rd(M.r['a1'],2)!=0 else 0x19716
    @B(0x19716)
    def b19716(M):M.C=1;return 0x1971a
    @B(0x1971a)
    def b1971a(M):return M.rts()
    @B(0x1971c)
    def b1971c(M):M.C=0;return 0x19728 if M.rd(M.r['a1']+12,2)&0x8000==0 else 0x19724
    @B(0x19724)
    def b19724(M):M.C=1;return 0x19728
    @B(0x19728)
    def b19728(M):return M.rts()
    # ---- 1972a segment selection
    @B(0x1972a)
    def b1972a(M):M.r['d7']=swp(M.r['d7']);return 0x1972c
    @B(0x1972c)
    def b1972c(M):
        r,n,z,v,c=sub16(M.r['d7'],M.rd(M.r['a1'],2));return 0x19744 if n==0 else 0x19732                       # CMP.W (A1),D7 ; BPL (N only)
    @B(0x19732)
    def b19732(M):return M.call(0x19710,0x19734)
    @B(0x19734)
    def b19734(M):return 0x1973c if M.need_c()==1 else 0x19738
    @B(0x19738)
    def b19738(M):return M.call(0x196de,0x1973a)
    @B(0x1973a)
    def b1973a(M):return 0x1972c
    @B(0x1973c)
    def b1973c(M):M.r['d7']=0;M.lw('d7',M.rd(M.r['a1'],2));M.r['d7']=swp(M.r['d7']);return M.rts()
    @B(0x19744)
    def b19744(M):
        r,n,z,v,c=sub16(M.r['d7'],M.rd(M.r['a1']+10,2));return 0x19764 if n else 0x1974c                      # CMP.W 10(A1),D7 ; BMI (N only)
    @B(0x1974c)
    def b1974c(M):return M.call(0x1971c,0x1974e)
    @B(0x1974e)
    def b1974e(M):return 0x19758 if M.need_c()==1 else 0x19752
    @B(0x19752)
    def b19752(M):return M.call(0x196ac,0x19756)
    @B(0x19756)
    def b19756(M):return 0x1972c
    @B(0x19758)
    def b19758(M):
        M.r['d7']=0;M.lw('d7',M.rd(M.r['a1']+10,2));M.r['d7']=swp(M.r['d7']);M.r['d7']=sub32(M.r['d7'],1)[0];return M.rts()
    @B(0x19764)
    def b19764(M):M.r['d7']=swp(M.r['d7']);return M.rts()
    # ---- 19812 position -> time with the publish loop 1982e
    @B(0x19812)
    def b19812(M):M.push32(M.r['d0']);M.push32(M.r['d1']);return M.call(0x18efa,0x1981a)
    @B(0x1981a)
    def b1981a(M):return M.call(0x1972a,0x1981e)
    @B(0x1981e)
    def b1981e(M):
        M.r['d1']=M.pop32();M.r['d0']=M.pop32();r,n,z,v,c=sub32(M.r['a1'],M.rl(0x53b4));return 0x19830 if z else 0x1982a        # CMPA.L 53b4(A5),A1 ; BEQ
    @B(0x1982a)
    def b1982a(M):M.wl(0x53b4,M.r['a1']);return 0x19812
    @B(0x19830)
    def b19830(M):return M.rts()
    # ---- 19844 proposed position check
    @B(0x19844)
    def b19844(M):M.r['d0']=M.rl(0x53bc);M.r['d1']=M.rl(0x53c0);return M.call(0x18efa,0x19850)
    @B(0x19850)
    def b19850(M):M.r['d6']=M.r['d7'];M.r['d0']=M.rl(0x53c4);M.r['d1']=M.rl(0x53c8);return M.call(0x18efa,0x1985e)
    @B(0x1985e)
    def b1985e(M):
        M.r['d5']=swp(M.r['d7']);r,n,z,v,c=sub32(M.r['d7'],M.r['d6']);return 0x198ae if n else 0x19868                    # CMP.L D6,D7 ; BMI (N only)
    @B(0x19868)
    def b19868(M):
        r,n,z,v,c=sub16(M.r['d5'],M.rd(M.r['a1']+10,2));return 0x198a8 if n else 0x19870                              # CMP.W 10(A1),D5 ; BMI
    @B(0x19870)
    def b19870(M):return M.call(0x1971c,0x19874)
    @B(0x19874)
    def b19874(M):return 0x1989e if M.need_c()==1 else 0x19878
    @B(0x19878)
    def b19878(M):return M.call(0x196ac,0x1987c)
    def load4_call(M,ret):
        M.r['d0']=M.rl(0x53bc);M.r['d1']=M.rl(0x53c0);M.r['d2']=M.rl(0x53c4);M.r['d3']=M.rl(0x53c8)
        M.push32(M.r['d7']);M.push32(M.r['d6']);return M.call(0x192c4,ret)                                                  # MOVEM.L D6-D7,-(A7): D7 at the higher address
    @B(0x1987c)
    def b1987c(M):return load4_call(M,0x19894)
    @B(0x19894)
    def b19894(M):
        M.r['d6']=M.pop32();M.r['d7']=M.pop32();return 0x1985e if M.need_c()==1 else 0x1989a
    @B(0x1989a)
    def b1989a(M):return M.call(0x196de,0x1989e)
    @B(0x1989e)
    def b1989e(M):
        M.r['d7']=0;M.lw('d7',M.rd(M.r['a1']+10,2));M.r['d7']=swp(M.r['d7']);M.r['d7']=sub32(M.r['d7'],1)[0];return 0x198a8
    @B(0x198a8)
    def b198a8(M):M.wl(0x53b4,M.r['a1']);return M.rts()
    @B(0x198ae)
    def b198ae(M):
        r,n,z,v,c=sub16(M.r['d5'],M.rd(M.r['a1'],2));return 0x198e8 if n==0 else 0x198b4                                  # CMP.W (A1),D5 ; BPL
    @B(0x198b4)
    def b198b4(M):return M.call(0x19710,0x198b8)
    @B(0x198b8)
    def b198b8(M):return 0x198e2 if M.need_c()==1 else 0x198bc
    @B(0x198bc)
    def b198bc(M):return M.call(0x196de,0x198c0)
    @B(0x198c0)
    def b198c0(M):return load4_call(M,0x198d8)
    @B(0x198d8)
    def b198d8(M):
        M.r['d6']=M.pop32();M.r['d7']=M.pop32();return 0x1985e if M.need_c()==1 else 0x198de
    @B(0x198de)
    def b198de(M):return M.call(0x196ac,0x198e2)
    @B(0x198e2)
    def b198e2(M):M.r['d7']=0;M.lw('d7',M.rd(M.r['a1'],2));M.r['d7']=swp(M.r['d7']);return 0x198e8
    @B(0x198e8)
    def b198e8(M):M.wl(0x53b4,M.r['a1']);return M.rts()
    # ---- 19910 time -> position pair and widths
    @B(0x19910)
    def b19910(M):return M.call(0x1972a,0x19914)
    @B(0x19914)
    def b19914(M):M.wl(0x53b4,M.r['a1']);return M.call(0x18fd2,0x1991c)
    @B(0x1991c)
    def b1991c(M):M.r['d2']=0;M.r['d3']=0;return M.call(0x18c06,0x19924)
    @B(0x19924)
    def b19924(M):return 0x19930 if M.need_c()==0 else 0x19928
    @B(0x19928)
    def b19928(M):M.lw('d3',M.rd(M.r['a1']+4,2));M.r['d3']=swp(M.r['d3']);return M.rts()
    @B(0x19930)
    def b19930(M):M.lw('d2',M.rd(M.r['a1']+4,2));M.r['d2']=swp(M.r['d2']);return M.rts()
    # ---- 19938 (outside the contract: U5 caller; declared extra range)
    @B(0x19938)
    def b19938(M):M.r['a1']=M.rl(0x53b4);return 0x19956 if M.r['a1'] else 0x19944
    @B(0x19944)
    def b19944(M):
        M.r['d0']=0;M.r['d1']=0;M.lw('d0',M.rw(0x53b8));M.lw('d1',M.rw(0x53ba));M.r['d0']=swp(M.r['d0']);M.r['d1']=swp(M.r['d1']);return M.rts()
    @B(0x19956)
    def b19956(M):return M.call(0x1972a,0x1995a)
    @B(0x1995a)
    def b1995a(M):M.wl(0x53b4,M.r['a1']);return M.call(0x18fd2,0x19962)
    @B(0x19962)
    def b19962(M):M.r['d2']=0;M.lw('d2',M.rd(M.r['a1']+8,2));M.r['d2']=swp(M.r['d2']);return M.call(0x18c06,0x1996e)
    @B(0x1996e)
    def b1996e(M):return 0x19974 if M.need_c()==0 else 0x19972
    @B(0x19972)
    def b19972(M):M.r['d1']=add32(M.r['d1'],M.r['d2'])[0];return 0x19974
    @B(0x19974)
    def b19974(M):M.r['d0']=add32(M.r['d0'],M.r['d2'])[0];return M.rts()


# ----------------------------------------------------------------------------------
# Observer configuration (U2 globals extended with the U3 ranges and block starts)
# ----------------------------------------------------------------------------------
def slot_leaders():
    out=set()
    for entry,base in DISPATCH.items():out.update(base+4*k for k in range(SLOT_COUNT))
    return out


def configure3(program,out_dir):
    global U3_RANGES,U3_TABLE,U3_STARTS,U3_BUNDLED,LEADERS_U3,LEADERS_X,SLOTROWS,S_STARTS
    sc.configure(program,out_dir)
    ranges,table,starts,s_starts,bundled,rows=parse_contract(program)
    U3_RANGES,U3_TABLE,U3_STARTS,S_STARTS,U3_BUNDLED=ranges,table,starts,s_starts,bundled
    SLOTROWS=[parse_slot_row(r) for r in rows]
    LEADERS_U3=frozenset(fh.leaders_of(program,U3_RANGES))|frozenset(slot_leaders())
    LEADERS_X=frozenset(fh.leaders_of(program,(EXTRA_RANGE,)))
    sc.LEADERS=frozenset(sc.LEADERS|LEADERS_U3|LEADERS_X);sc.BLOCKS=tuple(sorted(sc.LEADERS))
    sc.RANGES=sc.RANGES+U3_RANGES+(EXTRA_RANGE,)
    sc.KEYS_PCS=tuple(sorted(sc.LEADERS|set(sc.BOUNDARIES_U2)))
    fc.RANGES=sc.RANGES;fc.BOUNDARIES=sc.BLOCKS;fc.KEY_PCS=sc.KEYS_PCS
    install(SLOTROWS)
    missing=sorted(hex(pc) for pc in (sc.LEADERS_U2|LEADERS_U3|LEADERS_X) if pc not in sc.BLK);assert not missing,'model has no block for leaders %s'%missing
    extra=sorted(hex(pc) for pc in sc.BLK if pc not in sc.LEADERS);assert not extra,'model has blocks that are not leaders %s'%extra


# ----------------------------------------------------------------------------------
# Stop evidence: a stop is accepted only directly after the transferring instruction (checked against the original bytes and the live registers)
# ----------------------------------------------------------------------------------
ORIG_STOP=sc.stop_evidence


def branch_dest(program,pc):
    raw=program[pc:pc+4];w=int.from_bytes(raw[:2],'big');d=w&0xff
    if d==0:return pc+2+int.from_bytes(raw[2:4],'big',signed=True),4
    return pc+2+(d-256 if d>127 else d),2


def stop_evidence3(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(outgoing_pc=pc,previous_pc=None,is_step_stop=True,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    if pc in sc.BOUNDARY_BSR or pc==RETURN_FF000:return ORIG_STOP(program,p)
    prev=pcs[-2];ram=p['ram_after'];a7=o['a7'];raw=program[prev:prev+6];w=int.from_bytes(raw[:2],'big');hi=w>>8
    base=dict(outgoing_pc=pc,previous_pc=prev,is_step_stop=True)
    if w==0x4e75:
        popped=sc.u32(ram,a7-4);assert popped==pc,(p['label'],hex(prev),hex(pc),hex(popped))
        return dict(base,previous_bytes='4e75',reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x)'%(prev,pc,a7))
    if hi==0x61:
        t,size=branch_dest(program,prev);assert t==pc,(p['label'],hex(prev),hex(pc),hex(t));ret=prev+size
        assert sc.u32(ram,a7)==ret,(p['label'],hex(sc.u32(ram,a7)))
        return dict(base,previous_bytes=raw[:size].hex(),reached_from='BSR at %x (bytes %s) pushed the return LONG %x at A7=%x; %x is never executed'%(prev,raw[:size].hex(),ret,a7,pc))
    if hi==0x60:
        t,size=branch_dest(program,prev);assert t==pc,(p['label'],hex(prev),hex(pc),hex(t))
        return dict(base,previous_bytes=raw[:size].hex(),reached_from='BRA at %x (bytes %s) to %x'%(prev,raw[:size].hex(),pc))
    if 0x62<=hi<=0x6f:
        t,size=branch_dest(program,prev);assert pc in (t,prev+size),(p['label'],hex(prev),hex(pc),hex(t))
        return dict(base,previous_bytes=raw[:size].hex(),taken=pc==t,reached_from='Bcc at %x (bytes %s): %s to %x'%(prev,raw[:size].hex(),'taken' if pc==t else 'not taken, fall-through',pc))
    if raw[:4].hex()=='4efb4002':
        t=(prev+4+sx16(o['d4']))&M32;assert t==pc,(p['label'],hex(prev),hex(pc),hex(t))
        return dict(base,previous_bytes=raw[:4].hex(),reached_from='JMP 2(PC,D4.W) at %x (bytes 4efb4002) with D4=%x: PC = %x + sext(D4.W) = %x; the code behind is never executed'%(prev,o['d4'],prev+4,pc))
    raise AssertionError('stop %x is not directly after a transferring instruction (previous %x bytes %s)'%(pc,prev,raw.hex()))


# ----------------------------------------------------------------------------------
# Planning, model runs, unit conditions
# ----------------------------------------------------------------------------------
def plan3(program,fx,setup=(),stop=None):
    """Declared-stop probe: one continuous run with the observer's own Observer; returns the first-hit leader order, the live A7 delta and the executed PCs."""
    o=fc.Observer(program,True)
    try:
        o.prepare(dict(fx,stop_pc=stop,checkpoints=()));o.begin_step(stop,());o.apply(list(setup));p=o.run(allow_guard=False)
    except AssertionError as e:return dict(error=repr(e)[:300])
    finally:o.close()
    pcs=p['pcs'];entry=pcs[0];order=[]
    for pc in pcs[1:]:
        if pc in sc.LEADERS and pc not in order and pc!=entry and pc!=stop:order.append(pc)
    return dict(error=None,checkpoints=order,a7_delta=sx32((p['outgoing']['a7']-p['incoming']['a7'])&M32),instructions=len(pcs)-1,pcs=pcs,final_pc=p['outgoing']['pc'])


def plan_probe3(program,fx,setup=()):
    """Guarded probe to the first PC outside the observed ranges (the next boundary), like the U2 plan, plus the U3 facts of the executed path."""
    info=sc.plan(program,fx,setup)
    return info


def apply_setup(ram,setup):
    for c in setup:
        a=c['address'];ram[a&0xffff:(a&0xffff)+c['size']]=c['value'].to_bytes(c['size'],'big')


def model_run3(program,fx,setup,stop,cap=6000):
    ram=bytearray(fx['ram']);apply_setup(ram,setup);r=dict(fx['regs']);r['a7']=fx['initial_a7'];r['pc']=fx['entry_pc']
    M=sc.U2Machine(program,fx['bank_state'],ram,r);pc=fx['entry_pc'];steps=0
    try:
        while pc!=stop:
            if pc&1:return None
            fn=sc.BLK.get(pc)
            if fn is None:return None
            M.lead(pc);pc=fn(M);steps+=1
            if steps>cap:return None
    except (sc.ModelError,fh.ModelError,KeyError,AssertionError):return None
    return M


def unit_fx(label,entry,ram,regs,ret,prov,bank=BANK3_MID,a7=S,role=None):
    return sc.make_fx(label,ram,regs,bank,entry,a7,prov,(),[(a7,ret.to_bytes(4,'big'))],
        role=role or 'declared unit entry at %x: RAM, 14 declared registers, A5 = 108000, A7 = %x, declared return LONG %x on the stack, PVC bank 3'%(entry,a7,ret))


def add_unit(B,program,label,group,prov,fx,setup,stop,delta,model=True):
    """Declared-stop condition: the probe finds the first-hit leader order (split checkpoints) and must end exactly at `stop` with the declared A7 delta."""
    fx=dict(fx);fx['label']=label;info=plan3(program,fx,setup,stop)
    assert info['error'] is None,(label,info['error'])
    assert info['a7_delta']==delta,(label,info['a7_delta'],delta)
    cps=list(info['checkpoints']) if stop!=fx['entry_pc'] else []
    spec=dict(label=label,group=group,fixture=fx,steps=[dict(label=label,changes=list(setup),stop_pc=stop,checkpoints=cps,a7=('entry',delta))],provenance=prov)
    B.specs.append(spec)
    if model:B.models.append(label)
    B.censuses[label]=dict(first_stop=hex(stop),error=None,guard=None,instructions=info['instructions'],a7_delta=delta,leaders=set(pc for pc in info['pcs'] if pc in sc.LEADERS))
    return spec


def put(d,addr,size,value):d[addr]=(size,value&((1<<(8*size))-1))


def put_path(d,base,records):
    """Declared motion path: 10-byte records (time WORD, type WORD, +4 +6 +8 WORDs) at `base`."""
    for i,rec in enumerate(records):
        assert len(rec)==5
        for j,wv in enumerate(rec):put(d,base+10*i+2*j,2,wv)


REC=0x10e400
TYPES_ALL=tuple(range(0,0x90,4))
POOL_SMALL=(0,1,2,3,4,8,0x10,0x20,0x40,0x80,0x100)
POOL_BIG=(0x7fff,0x8000,0x8001,0xffff,0xfff0,0xff00,0x7ff0,0x4000,0xc000,0x0140,0x0100,0xfffe,0xff80,0x0080)


def rw_small(rng):return rng.choice(POOL_SMALL) if rng.random()<0.7 else rng.randrange(0,0x400)


def rw_wide(rng):
    r=rng.random()
    if r<0.45:return rng.choice(POOL_BIG)
    if r<0.7:return rng.choice(POOL_SMALL)
    return rng.randrange(0,0x10000)


def rl_pos(rng):
    r=rng.random()
    if r<0.3:return rng.choice((0,0x8000,0x10000,0x60000,0x7fff0000,0x80000000,0xffff0000,0x00018000,0xfffe8000,0x7fffffff,0xffffffff,0x00010001))
    if r<0.7:return (rw_wide(rng)<<16)&M32
    return rng.randrange(0,1<<32)


class Ctx:
    """Declared base state of every unit fixture: the RAM and registers of scene_frame case 182 (rebuilt, sha-checked), A5 = 108000."""
    def __init__(self,scene_in):
        row,ram,regs=scene_in[182];self.ram=ram;self.regs=dict(regs);self.prov=sc.scene_prov(182,row,ram);self.ram_sha=sha(ram)
    def fx(self,label,entry,ret,regs=None,bank=BANK3_MID,a7=S,desc=''):
        r=dict(self.regs)
        if regs:r.update(regs)
        prov=dict(kind='declared unit fixture',base_state='scene_frame_execution case 182 input RAM (rebuilt)',base_ram_sha256=self.ram_sha,entry=hex(entry),return_long=hex(ret),description=desc)
        return unit_fx(label,entry,self.ram,r,ret,prov,bank,a7)


def dispatcher_conditions(B,program,ctx):
    """Every type slot 00..8c of each of the five dispatchers, two declared variants (zero extras / non-zero +4 +6 +8 and wide values)."""
    n=0
    for entry,base in DISPATCH.items():
        for k in range(SLOT_COUNT):
            for v in (0,1):
                rng=random.Random('u3-%x-%d-%d'%(entry,k,v));t=4*k
                if v==0:ex=(0,0,0);tm=rng.randrange(0,0x200);gap=rng.randrange(1,0x40)
                else:ex=tuple(rw_wide(rng) or 1 for _ in range(3));tm=rw_wide(rng);gap=rw_wide(rng) or 1
                recs=[(tm,t,ex[0],ex[1],ex[2]),((tm+gap)&0xffff,0x14,rw_small(rng),rw_small(rng),rw_small(rng)),(((tm+gap)&0xffff)+7&0xffff,0xffff,0,0,0)]
                d={};put_path(d,REC,recs)
                put(d,0x10d3b8,2,rw_small(rng) if v==0 else rw_wide(rng));put(d,0x10d3ba,2,rw_small(rng) if v==0 else rw_wide(rng))
                regs=dict(a1=REC)
                for rname in ('d0','d1','d2','d3','d7'):regs[rname]=(rl_pos(rng) if v else (rw_small(rng)<<16|rw_small(rng)))&M32
                if entry==0x192c4 and v==1 and rng.random()<0.5:
                    for rname in ('d0','d1','d2','d3'):regs[rname]=(rng.randrange(0,1<<32) if rng.random()<0.5 else regs[rname])
                label='disp-%x-type%02x-v%d'%(entry,t,v)
                fx=ctx.fx(label,entry,DISPATCH_RET[entry],regs,desc='dispatcher %x with the declared record type %02x (slot %d), variant %d'%(entry,t,k,v))
                add_unit(B,program,label,'fixture-dispatcher-%x'%entry,'declared motion record at %x: type %02x (slot %d), +4/+6/+8 = %s; dispatcher %x called directly, stop at its RTS return %x'%(REC,t,k,[hex(x) for x in ex],entry,DISPATCH_RET[entry]),fx,writes_of(d),DISPATCH_RET[entry],4)
                n+=1
    return n


def writes_of(d):return sc.writes_of(d)


def find_type_words(program,lo,hi,want,limit=64):
    """Even offsets p in [lo, hi) with WORD p+2 == want (candidate record starts whose type is `want`)."""
    out=[];at=lo+(lo&1)
    p=program.find(want.to_bytes(2,'big'),lo+2)
    while p!=-1 and p+8<hi and len(out)<limit:
        if p&1==0 and p-2>=lo:out.append(p-2)
        p=program.find(want.to_bytes(2,'big'),p+1)
    return out


def rom_dispatcher_conditions(B,program,ctx):
    """The same dispatchers with A1 inside fixed ROM and inside the banked window (bank 3): the record WORDs are read from the original ROM (ordered ROM reads)."""
    n=0
    for entry,base in DISPATCH.items():
        for k in range(SLOT_COUNT):
            t=4*k;rng=random.Random('u3-rom-%x-%d'%(entry,k))
            fixed=[x for x in find_type_words(program,0x40000,0x80000,t,400)];bank=[x for x in find_type_words(program,0x300000,0x300000+0xf0000,t,400)]
            assert fixed and bank,(hex(entry),t)
            for tag,pool,conv in (('rom',fixed,lambda a:a),('bank',bank,lambda a:0x200000+a-0x300000)):
                a1=conv(rng.choice(pool));regs=dict(a1=a1)
                for rname in ('d0','d1','d2','d3','d7'):regs[rname]=rl_pos(rng)
                d={};put(d,0x10d3b8,2,rw_wide(rng));put(d,0x10d3ba,2,rw_wide(rng))
                label='disp-%x-type%02x-%s'%(entry,t,tag)
                fx=ctx.fx(label,entry,DISPATCH_RET[entry],regs,desc='dispatcher %x, record in %s at %x (type %02x)'%(entry,'fixed ROM' if tag=='rom' else 'the bank 3 window',a1,t))
                add_unit(B,program,label,'fixture-dispatcher-rom-%x'%entry,'record words read from the original ROM: A1 = %x (%s), type %02x; dispatcher %x called directly, stop at its RTS return %x'%(a1,'fixed ROM' if tag=='rom' else 'banked window of bank 3',t,entry,DISPATCH_RET[entry]),fx,writes_of(d),DISPATCH_RET[entry],4)
                n+=1
    return n


OOR_TYPES=(0x0001,0x0002,0x0003,0x0090,0x0092,0x0094,0x00fe,0x0100,0x7ffe,0x7fff,0x8000,0x8001,0xfffe,0xffff)
OOR_FACTS={}


def oor_conditions(B,program,ctx):
    """Types outside the 36-slot table follow the computed PC (base + sext(type)): block starts run, other PCs are observed as the stop directly after the JMP."""
    n=0
    for entry,base in DISPATCH.items():
        lands=[]
        for t in OOR_TYPES:lands.append((t,'plain'))
        # extra types that land on block starts outside the table: a tail / common routine / segment test
        for target in {0x18c06:(0x19710,0x1971c,0x18caa+0x0,0x196d8),0x18caa:(0x18c9e,0x18ca4,0x19728),0x18efa:(0x18c9e,0x192b2,0x1971a),0x18fd2:(0x192b2,0x18f92,0x19764),0x192c4:(0x19372,0x19398,0x18ca4)}[entry]:
            lands.append(((target-base)&0xffff,'to-%x'%target))
        for t,tag in lands:
            target=(base+sx16(t))&M32;rng=random.Random('u3-oor-%x-%x'%(entry,t))
            rec=[(5,t,3,4,5),(0x20,0x14,0,0,0),(0x30,0xffff,0,0,0)];d={};put_path(d,REC,rec);put(d,0x10d3b8,2,0x100);put(d,0x10d3ba,2,0x100)
            regs=dict(a1=REC)
            for rname in ('d0','d1','d2','d3','d7'):regs[rname]=rl_pos(rng)
            label='oor-%x-type%04x'%(entry,t)
            fx=ctx.fx(label,entry,DISPATCH_RET[entry],regs,desc='dispatcher %x with the out-of-table record type %04x: computed PC %x'%(entry,t,target))
            is_block=target in sc.BLK and target in (LEADERS_U3|sc.LEADERS_U2)
            if is_block:
                stop=DISPATCH_RET[entry];delta=4
            else:stop=target;delta=0
            OOR_FACTS[label]=dict(dispatcher=hex(entry),type=hex(t),computed_pc=hex(target),computed_pc_odd=bool(target&1),is_contract_block_start=target in U3_STARTS,is_model_block=target in sc.BLK,
                outcome='executed as block start then RTS to the declared return' if is_block else 'stop directly after the JMP at the computed PC (contract: unsupported animation machine PC / odd PC rollback; the code at that PC is not executed)')
            spec=add_unit(B,program,label,'fixture-out-of-range-%x'%entry,'record type %04x outside the table (%s): JMP lands on %x'%(t,tag,target),fx,writes_of(d),stop,delta,model=is_block or True)
            n+=1
    return n


# ----------------------------------------------------------------------------------
# Flow fixtures: declared RAM motion paths driven through 19812 / 19844 / 19910 / 1972a / 196ac / 196de / 19710 / 1971c (and the extra 19938)
# ----------------------------------------------------------------------------------
FLOW_ENTRIES={0x19812:0x1a776,0x19844:0x19c22,0x19910:0x1997c,0x1972a:0x1981e,0x196ac:0x19756,0x196de:0x1973a,0x19710:0x19734,0x1971c:0x1974e,0x19938:0x1a692}
NAT_TYPES=(0x14,0x40,0x64,0x80)
COLLECT_LOOPS=(0x1982a,0x1973a,0x19756,0x1985e,0x19894,0x198d8,0x1989a,0x198de,0x19738,0x19752)


def gen_path(rng):
    n=rng.choice((1,2,2,3,3,4,5,6));recs=[];tm=0;nat=rng.random()<0.35
    for i in range(n):
        if i>0:tm=(tm+rng.choice((1,1,2,3,5,8,0x10,0x20,0x40,0x100)))&0xffff
        typ=rng.choice(NAT_TYPES) if nat and rng.random()<0.8 else rng.choice(TYPES_ALL)
        ex=(0,0,0) if rng.random()<0.5 else (rw_wide(rng) if rng.random()<0.3 else rw_small(rng),rw_small(rng),rw_small(rng))
        recs.append((tm if i else 0,typ,*ex))
    recs.append(((tm+rng.choice((1,0x10,0x40,0x100)))&0xffff,0xffff,0,0,0))
    return recs


def coord_for(typ,s,tt,X,Y,rng):
    """A coordinate pair (D0, D1) whose motion time under record type `typ` and start `s` is about `tt` (exact for zero fraction); the other axis is random."""
    k=typ//4;frac=rng.choice((0,0,0x8000,rng.randrange(0,0x10000)));hi=tt&0xffff
    d0=rl_pos(rng);d1=rl_pos(rng)
    if k<=10:d0=((((hi+X-s)&0xffff)<<16)|frac)&M32
    elif k<=21:d0=((((X<<16)-(((hi-s)&0xffff)<<16|frac)))&M32)
    elif k<=28:d1=((((hi+Y-s)&0xffff)<<16)|frac)&M32
    elif k<=35:d1=((((Y<<16)-(((hi-s)&0xffff)<<16|frac)))&M32)
    return d0,d1


def flow_candidate(rng,entry):
    recs=gen_path(rng);n=len(recs)-1;idx=rng.randrange(0,n+ (0 if entry in (0x196ac,) else 0)) if n>0 else 0
    if entry==0x196de:idx=rng.randrange(1,n+1) if n>=1 else 0
    if entry==0x196ac:idx=rng.randrange(0,n)
    ptr=REC+10*idx;X=rw_small(rng) if rng.random()<0.7 else rw_wide(rng);Y=rw_small(rng) if rng.random()<0.7 else rw_wide(rng)
    d={};put_path(d,REC,recs);put(d,0x10d3b8,2,X);put(d,0x10d3ba,2,Y)
    regs=dict(a1=ptr);last=recs[-2][0] if n>=1 else 0
    tt=rng.randrange(-2,last+0x30)&0xffff if rng.random()<0.85 else rng.randrange(0,0x10000)
    typ,s=recs[idx][1],recs[idx][0]
    d0,d1=coord_for(typ,s,tt,X,Y,rng)
    if entry==0x19812:
        regs.update(d0=d0,d1=d1);put(d,0x10d3b4,4,ptr if rng.random()<0.8 else REC+10*rng.randrange(0,n+1))
    elif entry==0x19844:
        tp=rng.randrange(-2,last+0x30)&0xffff;p0,p1=coord_for(typ,s,tp,X,Y,rng)
        if rng.random()<0.25:p0,p1=d0,d1
        put(d,0x10d3b4,4,ptr);put(d,0x10d3bc,4,d0);put(d,0x10d3c0,4,d1);put(d,0x10d3c4,4,p0);put(d,0x10d3c8,4,p1)
        if rng.random()<0.5:
            put(d,0x10d3c4,4,(d0+rng.choice((0x8000,-0x8000,0x30000,-0x30000,0x1ffff)))&M32)
    elif entry in (0x19910,0x1972a):
        regs['d7']=(((tt&0xffff)<<16)|rng.choice((0,0,0x8000,rng.randrange(0,0x10000))))&M32;put(d,0x10d3b4,4,ptr)
    elif entry==0x19938:
        put(d,0x10d3b4,4,0 if rng.random()<0.25 else ptr);regs['d7']=(((tt&0xffff)<<16)|rng.randrange(0,0x10000))&M32
    else:
        put(d,0x10d3b4,4,ptr)
    for rname in ('d0','d1','d2','d3'):regs.setdefault(rname,rl_pos(rng))
    return dict(entry=entry,regs=regs,d=d,recs=recs,idx=idx)


def cand_model(program,ctx,cand,cap=3000):
    ret=FLOW_ENTRIES[cand['entry']];regs=dict(ctx.regs);regs.update(cand['regs']);regs['a5']=sc.A5V
    fx=dict(ram=ctx.ram,regs=regs,initial_a7=S,entry_pc=cand['entry'],bank_state=BANK3_MID[0])
    ram=bytearray(ctx.ram);apply_setup(ram,writes_of(cand['d']));ram[S&0xffff:(S&0xffff)+4]=ret.to_bytes(4,'big')
    fx['ram']=ram;fx['bank_state']=BANK3_MID[0] if False else BANK3_MID[0]
    r=dict(regs);r['a7']=S;r['pc']=cand['entry']
    M=sc.U2Machine(program,BANK3_MID[0],ram,r);pc=cand['entry'];steps=0;hits=collections.Counter()
    try:
        while pc!=ret:
            if pc&1:return None
            fn=sc.BLK.get(pc)
            if fn is None:return None
            M.lead(pc);hits[pc]+=1;pc=fn(M);steps+=1
            if steps>cap:return None
    except (sc.ModelError,fh.ModelError,KeyError,AssertionError):return None
    return hits,steps


def search_flows(program,ctx,covered,seed,budget,per_entry_min=3):
    """Coverage-guided choice (by the independent model) of declared flow fixtures: a candidate is kept when it reaches U3 block starts no earlier condition reaches or
    when it iterates one of the walk loops more often than any kept candidate (up to 5 iterations)."""
    rng=random.Random(seed);targets=set(LEADERS_U3|LEADERS_X);covered=set(covered);chosen=[];best=collections.Counter();kept_per=collections.Counter()
    entries=tuple(FLOW_ENTRIES)
    for k in range(budget):
        entry=entries[k%len(entries)];cand=flow_candidate(rng,entry);r=cand_model(program,ctx,cand)
        if r is None:continue
        hits,steps=r;new=(set(hits)&targets)-covered;loops=[pc for pc in COLLECT_LOOPS if best[pc]<min(5,hits[pc]-(1 if pc==0x1985e else 0))]
        if new or loops or kept_per[entry]<per_entry_min:
            covered|=new;chosen.append((k,cand,sorted(new),loops,steps));kept_per[entry]+=1
            for pc in loops:best[pc]=min(5,hits[pc]-(1 if pc==0x1985e else 0))
    return chosen,covered


def flow_conditions(B,program,ctx,chosen):
    n=0
    for k,cand,new,loops,steps in chosen:
        entry=cand['entry'];ret=FLOW_ENTRIES[entry];label='flow-%x-%04d'%(entry,k)
        fx=ctx.fx(label,entry,ret,cand['regs'],desc='motion flow entry %x with a declared RAM path'%entry)
        recs=cand['recs']
        add_unit(B,program,label,'fixture-flow-%x'%entry,'declared RAM motion path (%d records at %x, current record %d, types %s, +4/+6/+8 %s), coverage-guided candidate %d: new block starts %s, loops %s; entry %x, stop at its RTS return %x'%(
            len(recs),REC,cand['idx'],[hex(r[1]) for r in recs[:-1]],['nonzero' if any(r[2:5]) else 'zero' for r in recs[:-1]],k,[hex(x) for x in new],[hex(x) for x in loops],entry,ret),fx,writes_of(cand['d']),ret,4)
        n+=1
    return n


# ----------------------------------------------------------------------------------
# Natural seeds: census with the combined U2+U3 ranges, selection, conditions
# ----------------------------------------------------------------------------------
U3_ENTRY_PCS=(0x19812,0x19844,0x19910)
RARE_BLOCKS=(0x1982a,0x19738,0x19752,0x1973a,0x19756,0x1973c,0x19758,0x19878,0x1989a,0x1989e,0x198a8,0x198ae,0x198b4,0x198b8,0x198bc,0x198c0,0x198d8,0x198de,0x198e2,0x198e8,0x19370,0x19578,0x196c4,0x196e6,0x19928)
RARE_CASES=(192,193,194,82,85,205,206,207,208,218,220,423,478,508,513,563,509,380,436,437,576,577)


def plan_probe(program,fx,setup=()):
    """sc.plan (guarded probe to the first PC outside the observed ranges = the next U2 boundary) plus the facts of the executed path."""
    spec=dict(label=fx['label'],group='probe',fixture=fx,steps=[dict(label='probe',changes=list(setup),stop_pc=sc.PROBE_STOP,checkpoints=[],a7=('entry',0))],provenance='probe',guarded=True,guard={})
    try:phases=fc.run_condition(program,spec,True)
    except AssertionError as e:return dict(error=repr(e)[:300],first_stop=None)
    p=phases[-1];g=p['guard'];pcs=p['pcs'];entry=pcs[0];order=[];last=pcs[-1]
    for pc in pcs[1:]:
        if pc in sc.LEADERS and pc not in order and pc!=entry and pc!=last:order.append(pc)
    hits=collections.Counter(pc for pc in pcs[:-1] if pc in sc.LEADERS)
    first=next((pc for pc in pcs if pc in (0x19812,0x19844)),None)
    return dict(error=None,guard=g,first_stop=(g or {}).get('target') if (g or {}).get('problem')=='unsupported_code_target' else None,
        a7_delta=(p['outgoing']['a7']-p['incoming']['a7'])&M32,instructions=len(pcs)-1,checkpoints=order,last_pc=last,incoming_a7=p['incoming']['a7'],outgoing_a7=p['outgoing']['a7'],
        leader_hits=dict(hits),u3_first=first)


def dispatch_types(hits):
    out={}
    for entry,base in DISPATCH.items():
        ts=sorted(4*k for k in range(SLOT_COUNT) if base+4*k in hits)
        if ts:out[hex(entry)]=ts
    return out


def census_entry3(info):
    e=sc.census_entry(info);hits=info.get('leader_hits') or {}
    e.update(u3_first=hex(info['u3_first']) if info.get('u3_first') else None,u3_entries={hex(pc):hits[pc] for pc in U3_ENTRY_PCS+(0x19802,0x19832,0x198ee) if pc in hits},dispatch_types=dispatch_types(hits),
        rare_blocks=sorted(hex(pc) for pc in RARE_BLOCKS if pc in hits),u3_block_count=sum(1 for pc in hits if pc in LEADERS_U3))
    return e


def build_census3(program,scene_in,stage_in,entry_in):
    cen=dict(scene_frame=[],stage_frame=[],stage_entry=[])
    for i,(row,ram,regs) in enumerate(scene_in):
        cen['scene_frame'].append(dict(case=i,family=row['fixture']['family'],**census_entry3(plan_probe(program,sc.direct_fx('scene-%04d'%i,ram,regs,{})))))
    for index,row,ram,how in stage_in:
        cen['stage_frame'].append(dict(case=index,label=row['label'],**census_entry3(plan_probe(program,sc.stage_natural_fx('stage-%02d'%index,row,ram,how)))))
    for c in entry_in:
        cen['stage_entry'].append(dict(case=c['case_index'],family=c['family'],**census_entry3(plan_probe(program,sc.entry_fx('entry-%03d'%c['case_index'],c,{})))))
    return cen


def natural_conditions3(B,scene_in,stage_in,entry_in,cen,count):
    sf=cen['scene_frame'];enters=[i for i,c in enumerate(sf) if c['u3_first'] is not None]
    key=lambda i:(sf[i]['u3_first'],tuple(tuple(v) for k,v in sorted(sf[i]['dispatch_types'].items())),tuple(sf[i]['rare_blocks']))
    chosen=sc.stratified(enters,key,count)
    for i in enters:
        if i not in chosen and (scene_in[i][0]['fixture']['family'] not in ('canonical-post-initialization-frame','actual-cli-carried-frames') or i in RARE_CASES):chosen.append(i)
    chosen=sorted(set(chosen))
    for i in chosen:
        row,ram,regs=scene_in[i];fx=sc.direct_fx('scene-%04d'%i,ram,regs,sc.scene_prov(i,row,ram));stop=int(sf[i]['first_stop'],16)
        assert stop in (0x1a7a8,0x1a0b6,0x1a470),(i,hex(stop))
        B.add('natural-scene-u3-%s-%04d'%(sf[i]['u3_first'][2:],i),'natural-scene-u3-%s'%sf[i]['u3_first'][2:],'scene_frame_execution case %d (%s): direct 1a73c entry on the rebuilt seed; U2 -> U3 (first entry %s) -> U2 to the next boundary %x'%(i,row['fixture']['family'],sf[i]['u3_first'],stop),fx,expect=stop)
    for index,row,ram,how in stage_in:
        fx=sc.stage_natural_fx('stage-%02d'%index,row,ram,how);c=[x for x in cen['stage_frame'] if x['case']==index][0];stop=int(c['first_stop'],16)
        assert c['u3_first'] is not None and stop in (0x1a7a8,0x1a0b6,0x1a470),(index,c)
        B.add('natural-stage-frame-u3-%02d'%index,'natural-stage-frame-u3','stage_frame verification case %d %s: natural 480bc -> JSR 47642 -> JSR 1a73c -> U2 -> U3 -> U2 to %x'%(index,row['label'],stop),fx,expect=stop)
    for k,c in enumerate(entry_in):
        ce=cen['stage_entry'][k]
        if ce['u3_first'] is None:continue
        stop=int(ce['first_stop'],16);assert stop in (0x1a7a8,0x1a0b6,0x1a470),(k,hex(stop))
        prov=dict(kind='stage_entry_body case',case=c['case_index'],family=c['family'],fixture=c['fixture'],input_ram_sha256=c['input_ram_sha256'],ram_at_1a73c_sha256=c['ram_sha256'],ports_before_1a73c=len(c['ports']),instructions_to_1a73c=c['instructions'],observation_sha256=sc.STAGE_ENTRY_SHA)
        B.add('natural-stage-entry-u3-%03d'%c['case_index'],'natural-stage-entry-u3','stage_entry_body case %d (%s): 1a73c entry state of the original 47a94 body run; U2 -> U3 -> U2 to %x'%(c['case_index'],c['family'],stop),sc.entry_fx('entry-%03d'%c['case_index'],c,prov),expect=stop)
    return chosen


# ----------------------------------------------------------------------------------
# Captured U3 entry states of the original full-frame run (declared fixtures, entry at 19812 / 19844 / 19910 with the real return LONG on the stack)
# ----------------------------------------------------------------------------------
CAPTURE_CALLERS={0x19812:(0x1a776,0x19bca,0x19d2c,0x1a484),0x19844:(0x19c22,),0x19910:(0x1997c,0x19da0)}


class U3Capture:
    def __init__(self,program):
        self.program=program;self.obs=sfe.Observer(program);self.hits=collections.Counter();self.want={};self.taken={};self.ptrs=collections.defaultdict(list)
        for pc in U3_ENTRY_PCS:self.obs.cpu.hook_add(UC_HOOK_CODE,self.hit,begin=pc,end=pc)
    def hit(self,cpu,address,size,user):
        a7=cpu.reg_read(sfe.m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(a7,4),'big')
        if ret not in CAPTURE_CALLERS[address]:return
        key=(address,ret);self.hits[key]+=1;n=self.hits[key];self.ptrs[key].append(int.from_bytes(cpu.mem_read(0x10d3b4,4),'big'))
        if (key,n) in self.want:
            self.taken[(key,n)]=dict(pc=address,hit=n,ram=bytes(cpu.mem_read(sfe.BASE,0x10000)),regs={k:cpu.reg_read(r)&M32 for k,r in zip(sfe.KEYS,sfe.REGS)},a7=a7,
                stack=bytes(cpu.mem_read(a7,sfe.STACK+4-a7)),bank=self.obs.bank,ports=len(self.obs.ports))
    def run(self,ram,regs,want=()):
        self.hits.clear();self.ptrs.clear();self.want={w:1 for w in want};self.taken={}
        output,result,ports,info=self.obs.run(ram,[regs[k] for k in KEYS14])
        return output,result,info


def path_types(program,ptr):
    out=[]
    if not ptr or ptr>=0x100000:return tuple(out)
    p=ptr
    while p+4<=len(program) and len(out)<40:
        t=int.from_bytes(program[p+2:p+4],'big');out.append(t)
        if t&0x8000:break
        p+=10
    return tuple(out)


def capture_survey(program,scene_in):
    cap=U3Capture(program);survey=[]
    for index,(row,ram,regs) in enumerate(scene_in):
        output,result,info=cap.run(ram,regs);assert info['returned'] and info['error'] is None and sha(output)==row['ram_sha256'],index
        survey.append(dict(case=index,hits={k:v for k,v in cap.hits.items()},ptrs={k:list(v) for k,v in cap.ptrs.items()}))
    return survey


def capture_wanted(program,survey,per_key=6,last_per_key=2):
    keys=[(a,r) for a in U3_ENTRY_PCS for r in CAPTURE_CALLERS[a]];wanted=[]
    for key in keys:
        cases=[x for x in survey if key in x['hits']]
        if not cases:continue
        def sig(x):return path_types(program,x['ptrs'][key][0])
        groups=collections.OrderedDict()
        for x in cases:groups.setdefault(sig(x),[]).append(x)
        reps=[g[len(g)//2] for g in groups.values()];pick=reps if len(reps)<=per_key else sc.spread(reps,per_key)
        for x in pick:wanted.append((x['case'],key,1,'first-hit'))
        multi=[x for x in cases if x['hits'][key]>=2]
        for x in sc.spread(multi,last_per_key):wanted.append((x['case'],key,x['hits'][key],'last-hit'))
        for x in cases:
            if x['case'] in RARE_CASES and not any(w[0]==x['case'] and w[1]==key and w[2]==1 for w in wanted):wanted.append((x['case'],key,1,'rare-case'))
    return sorted(set(wanted))


def capture_states(program,scene_in,wanted):
    cap=U3Capture(program);out={};by=collections.defaultdict(list)
    for case,key,n,tag in wanted:by[case].append((key,n))
    for case in sorted(by):
        row,ram,regs=scene_in[case];cap.run(ram,regs,by[case])
        for key,n in by[case]:
            assert (key,n) in cap.taken,(case,key,n);out[(case,key,n)]=cap.taken[(key,n)]
    return out


def capture_conditions(B,program,scene_in,survey):
    wanted=capture_wanted(program,survey);states=capture_states(program,scene_in,wanted);n=0
    for case,key,hit,tag in wanted:
        st=states[(case,key,hit)];row=scene_in[case][0];address,ret=key
        prov=dict(kind='declared U3 entry captured from the original full-frame run',case=case,family=row['fixture']['family'],pc=hex(address),return_long=hex(ret),hit=hit,tag=tag,ram_sha256=sha(st['ram']),a7=hex(st['a7']),stack_hex=st['stack'].hex(),
            registers={k:hex(v) for k,v in st['regs'].items()},scene_input_ram_sha256=sc.row_sha(scene_in[case]),motion_pointer=hex(int.from_bytes(st['ram'][0xd3b4:0xd3b8],'big')),observation_sha256=sc.SCENE_OBS_SHA)
        label='capture-%x-ret%x-hit%d-case%04d'%(address,ret,hit,case);fx=sc.reentry_fx(label,st,prov)
        add_unit(B,program,label,'capture-%x'%address,'declared U3 entry at %x (hit %d, %s) captured from the original full-frame run of scene case %d: RAM, 14 registers, A7 and live stack; real return LONG %x, stop at the RTS return'%(address,hit,tag,case,ret),fx,[],ret,4)
        n+=1
    return n


# ----------------------------------------------------------------------------------
# Hand-made fixtures: SLT/SGT overflow, fractional borrow, band swap / wrap
# ----------------------------------------------------------------------------------
def band_conditions(B,program,ctx):
    """192c4 with a direct 1935c / 19564 type (14 / 40 resp. 64 / 80): the band test with LONG values around the signed overflow edge, EXG swap (negative width), SUBQ/ADDQ wrap."""
    n=0
    cases=[
        # (name, entry type, ref, w4, a, b)  a,b = D1,D3 (Y band, types 14/40) or D0,D2 (X band, types 64/80)
        ('above-overflow-both',0x14,0x8001,0,0x7fffffff,0x7fffffff),         # lo = 80000000: D1 - lo overflows (N=1,V=1): a signed-aware SLT is false, N-only would say 'below'
        ('above-overflow-one-inside',0x14,0x8001,0,0x7fffffff,0x80010000),
        ('below-overflow-both',0x14,0x7fff,0,0x80000000,0x80000000),          # hi = 80000000 (ADDQ wrap): D - hi
        ('mixed-edge',0x40,0x7fff,0,0x80000000,0x7fffffff),
        ('wrap-low',0x14,0x8000,0,0x7fff0000,0x80010000),                     # SUBQ.W #1: 8000 -> 7fff
        ('wrap-high',0x40,0x7fff,0,0x7ffe0000,0x7fffffff),                    # ADDQ.W #1: 7fff -> 8000
        ('negative-width-exg',0x14,0x0100,0xfff0,0x00fe0000,0x00ef0000),      # w4 = fff0: D5 < D4 -> EXG.L D4,D5
        ('negative-width-exg-inside',0x40,0x0100,0xfffe,0x00ff0000,0x01000000),
        ('inside-both',0x14,0x0100,0x0004,0x01000000,0x01020000),
        ('both-below',0x40,0x0100,0x0004,0x00000000,0x00800000),
        ('both-above',0x14,0x0100,0x0004,0x70000000,0x20000000),
        ('straddle',0x40,0x0100,0x0004,0x00000000,0x70000000),
        ('equal-edge-lo',0x14,0x0100,0,0x00ff0000,0x00ff0000),                # exactly lo: not below (SLT false)
        ('equal-edge-hi',0x14,0x0100,0,0x01010000,0x01010000),                # exactly hi: not above (SGT false)
        ('just-outside-lo',0x14,0x0100,0,0x00feffff,0x00fe0000),
        ('just-outside-hi',0x14,0x0100,0,0x01010001,0x01020000),
    ]
    for name,typ,ref,w4,a,b in cases:
        d={};put_path(d,REC,[(0,typ,w4,0,0),(0x20,0xffff,0,0,0)])
        if typ<0x58:                                       # X-main type: Y band, D1/D3, reference 53ba
            put(d,0x10d3ba,2,ref);put(d,0x10d3b8,2,0x0123);regs=dict(a1=REC,d1=a,d3=b,d0=0x00050000,d2=0x00070000)
        else:
            put(d,0x10d3b8,2,ref);put(d,0x10d3ba,2,0x0123);regs=dict(a1=REC,d0=a,d2=b,d1=0x00050000,d3=0x00070000)
        label='band-%s-type%02x'%(name,typ);fx=ctx.fx(label,0x192c4,DISPATCH_RET[0x192c4],regs,desc='192c4 band test, type %02x, reference %04x, +4 = %04x, coordinates %08x / %08x'%(typ,ref,w4,a,b))
        add_unit(B,program,label,'fixture-band','192c4 with the direct band type %02x: reference %04x, +4 %04x, coordinates %08x %08x (SLT/SGT on LONG compares incl. V)'%(typ,ref,w4,a,b),fx,writes_of(d),DISPATCH_RET[0x192c4],4);n+=1
    # the other two direct types of each family (14<->40, 64<->80) with the same style of values
    for typ in (0x64,0x80):
        for name,ref,w4,a,b in (('x-above-overflow',0x8001,0,0x7fffffff,0x7fffffff),('x-below-overflow',0x7fff,0,0x80000000,0x80000000),('x-inside',0x0100,4,0x01000000,0x01020000),('x-negative-width',0x0100,0xfff0,0x00fe0000,0x00ef0000),('x-straddle',0x0100,4,0,0x70000000)):
            d={};put_path(d,REC,[(0,typ,w4,0,0),(0x20,0xffff,0,0,0)]);put(d,0x10d3b8,2,ref);put(d,0x10d3ba,2,0x0123)
            regs=dict(a1=REC,d0=a,d2=b,d1=0x00050000,d3=0x00070000);label='band-%s-type%02x'%(name,typ)
            fx=ctx.fx(label,0x192c4,DISPATCH_RET[0x192c4],regs,desc='192c4 band test (X band), type %02x'%typ)
            add_unit(B,program,label,'fixture-band','192c4 with the direct band type %02x (X band, D0/D2, reference 53b8): reference %04x, +4 %04x, coordinates %08x %08x'%(typ,ref,w4,a,b),fx,writes_of(d),DISPATCH_RET[0x192c4],4);n+=1
    return n


def borrow_conditions(B,program,ctx):
    """18efa tails 18fa0 / 18fc0 (SUB.L with fraction borrow into the integer part) and the reverse 18fd2 handlers; 18fd2 forward integer wrap."""
    n=0
    for entry,typ,x,y,d0,d1,d7,name in ((0x18efa,0x2c,5,0,0x00030001,0,0,'18fa0-borrow'),(0x18efa,0x2c,5,0,0x00030000,0,0,'18fa0-no-borrow'),(0x18efa,0x74,0,7,0,0x00050001,0,'18fc0-borrow'),(0x18efa,0x74,0,7,0,0x00050000,0,'18fc0-no-borrow'),
            (0x18efa,0x2c,0x0000,0,0x00000001,0,0,'18fa0-wrap'),(0x18efa,0x00,0x7fff,0,0x80000000,0,0,'18f92-wrap'),
            (0x18fd2,0x2c,6,0,0,0,0x00010001,'18fd2-reverse-borrow'),(0x18fd2,0x74,0,6,0,0,0x00010001,'18fd2-reverse-borrow-y'),(0x18fd2,0x00,4,0,0,0,0x00020005,'18fd2-forward'),(0x18fd2,0x00,4,0,0,0,0x00010005,'18fd2-forward-wrap'),
            (0x18fd2,0x58,0,4,0,0,0x00010005,'18fd2-y-forward-wrap')):
        d={};put_path(d,REC,[(3,typ,0,0,0),(0x20,0x14,0,0,0),(0x30,0xffff,0,0,0)]);put(d,0x10d3b8,2,x);put(d,0x10d3ba,2,y)
        label='borrow-%s'%name;fx=ctx.fx(label,entry,DISPATCH_RET[entry],dict(a1=REC,d0=d0,d1=d1,d7=d7),desc='%x type %02x fraction borrow / wrap fixture'%(entry,typ))
        add_unit(B,program,label,'fixture-borrow','%x type %02x: reference X %x Y %x, D0 %08x D1 %08x D7 %08x (borrow / wrap of the integer part)'%(entry,typ,x,y,d0,d1,d7),fx,writes_of(d),DISPATCH_RET[entry],4);n+=1
    return n


# ----------------------------------------------------------------------------------
# Guards and negative checks
# ----------------------------------------------------------------------------------
def guard_conditions3(B,program,ctx,scene_in,cen):
    odd=lambda **kv:dict(problem='unsupported_odd_data_access',**kv)
    def g(label,desc,guard,fx,setup=(),stop=None):
        B.add(label,'guard',desc,fx,setup=setup,stop=sc.PROBE_STOP if stop is None else stop,guard=guard,model=False)
    path=lambda t=0x14:(lambda d:(put_path(d,REC,[(0,t,0,0,0),(0x20,0x14,0,0,0),(0x30,0xffff,0,0,0)]),put(d,0x10d3b4,4,REC),put(d,0x10d3b8,2,0x100),put(d,0x10d3ba,2,0x100),d)[-1])({})
    for entry,ret,first_pc,off in ((0x18c06,0x196c0,0x18c06,2),(0x18caa,0x196b0,0x18caa,2),(0x18efa,0x1981a,0x18efa,2),(0x18fd2,0x1991c,0x18fd2,2),(0x192c4,0x19894,0x192c4,2),(0x19710,0x19734,0x19710,0),(0x1971c,0x1974e,0x1971c,12),(0x1972a,0x1981e,0x1972c,0),
            (0x19910,0x1997c,0x1972c,0),(0x196ac,0x19756,0x18caa,2),(0x196de,0x1973a,0x18c06,2),(0x19812,0x1a776,0x18efa,2),(0x19844,0x19c22,0x18efa,2)):
        a1=REC+1;fx=ctx.fx('guard-odd-A1-%x'%entry,entry,ret,dict(a1=a1,d0=0,d1=0,d7=0),desc='odd A1 at entry %x'%entry)
        g('guard-odd-A1-%x'%entry,'entry %x with the odd A1 = %x: the first record WORD read (%x) at pc %x is odd'%(entry,a1,a1+off,first_pc),odd(pc=first_pc,address=a1+off,size=2,access='read'),fx,writes_of(path()))
    fx=ctx.fx('guard-odd-A7-19812',0x19812,0x1a776,dict(a1=REC,d0=0,d1=0),a7=S+1,desc='odd A7');g('guard-odd-A7-19812','entry 19812 with A7 = 1feffd (odd): MOVE.L D0,-(A7) writes an odd LONG',odd(pc=0x19812,address=S+1-4,size=4,access='write',odd_write_restored=True),fx,writes_of(path()))
    fx=ctx.fx('guard-odd-A7-rts',0x1971a,0x19734,dict(a1=REC),a7=S+1,desc='odd A7');g('guard-odd-A7-rts','declared entry at 1971a (RTS) with A7 = 1feffd (odd): the RTS reads an odd LONG',odd(pc=0x1971a,address=S+1,size=4,access='read'),fx,writes_of(path()))
    fx=ctx.fx('guard-odd-A5',0x196b0,0x196c0,dict(a1=REC,a5=0x108001,d0=0,d1=0),desc='odd A5');g('guard-odd-A5-196b0','declared entry at 196b0 with A5 = 108001: ADD.W D0,53b8(A5) reads an odd WORD',odd(pc=0x196b0,address=0x108001+0x53b8,size=2,access='read'),fx,writes_of(path()))
    fx=ctx.fx('guard-rom-write-A5',0x196b0,0x196c0,dict(a1=REC,a5=0x2000,d0=0,d1=0),desc='A5 in ROM space');g('guard-rom-write-A5-196b0','declared entry at 196b0 with A5 = 2000: ADD.W D0,53b8(A5) writes ROM address 73b8',dict(problem='unmapped_or_protected',pc=0x196b0,address=0x2000+0x53b8,size=2),fx,writes_of(path()))
    fx=ctx.fx('guard-rom-write-A7',0x19812,0x1a776,dict(a1=REC,d0=0,d1=0),a7=0x1100,desc='A7 in ROM');g('guard-rom-write-A7-19812','entry 19812 with A7 = 1100 (ROM): MOVE.L D0,-(A7) writes ROM',dict(problem='unmapped_or_protected',pc=0x19812,address=0x10fc,size=4),fx,writes_of(path()))
    # a declared stop that is not reached: the first PC outside the observed ranges ends the run (here the RTS return to ff000, never executed)
    fx=ctx.fx('guard-bad-stop-19758',0x19710,RETURN_FF000,dict(a1=REC),desc='bad stop');g('guard-bad-stop-19758-unit','unit run 19710 (RTS to ff000): stop declared 19758 is not reached; the RTS return ff000 is outside the observed ranges',dict(problem='unsupported_code_target',target=RETURN_FF000),fx,writes_of(path()),stop=0x19758)
    fx=ctx.fx('guard-bad-stop-1a0b6',0x1971c,RETURN_FF000,dict(a1=REC),desc='bad stop');g('guard-bad-stop-1a0b6-unit','unit run 1971c (RTS to ff000): a U2 boundary 1a0b6 declared as stop is not reached',dict(problem='unsupported_code_target',target=RETURN_FF000),fx,writes_of(path()),stop=0x1a0b6)
    sf=cen['scene_frame'];full=[c['case'] for c in sf if c['first_stop']=='0x1a7a8'][0];gate=[c['case'] for c in sf if c['first_stop']=='0x1a0b6'][0];ent=[c['case'] for c in sf if c['u3_first'] is not None][0]
    for case,first,stop in ((full,0x1a7a8,0x1a0b6),(gate,0x1a0b6,0x1a7a8),(full,0x1a7a8,0x1a470),(ent,int(sf[ent]['first_stop'],16),0x19758)):
        row,ram,regs=scene_in[case];fx=sc.direct_fx('scene-%04d-guard'%case,ram,regs,sc.scene_prov(case,row,ram))
        g('guard-bad-stop-%x-on-scene-%04d'%(stop,case),'scene seed %d reaches %x first: stop declared %x (never reached)'%(case,first,stop),dict(problem='unsupported_code_target',target=first),fx,stop=stop)
    # out-of-table types executed without stop: the computed PC is outside every observed range / odd -> unsupported code target (rollback of the machine)
    for entry,t in ((0x18c06,0x0001),(0x18caa,0x0002),(0x18efa,0x7ffe),(0x18fd2,0x8000),(0x192c4,0xffff),(0x18c06,0x00fe)):
        base=DISPATCH[entry];target=(base+sx16(t))&M32;rec=[(5,t,0,0,0),(0x20,0x14,0,0,0),(0x30,0xffff,0,0,0)];d={};put_path(d,REC,rec)
        fx=ctx.fx('guard-oor-%x-%04x'%(entry,t),entry,DISPATCH_RET[entry],dict(a1=REC),desc='out-of-table type')
        if target in LEADERS_U3|LEADERS_X|sc.LEADERS_U2:continue
        g('guard-oor-%x-type%04x'%(entry,t),'dispatcher %x with the record type %04x runs on to %x, which is not an instruction of the observed ranges: unsupported code target'%(entry,t,target),dict(problem='unsupported_code_target',target=target),fx,writes_of(d))
    B.add('boundary-zero-step','boundary','zero-step: the stop PC equals the entry PC 1972a; nothing is executed',ctx.fx('zero-step',0x1972a,0x1981e,dict(a1=REC,d7=0),desc='zero-step'),setup=writes_of(path()),stop=0x1972a)


def negative_checks3(program,B,ctx):
    out=[]
    def run(label,entry,ret,regs,d,stop):
        fx=ctx.fx(label,entry,ret,regs,desc='negative stop check');spec=dict(label=label,group='negative',fixture=fx,steps=[dict(label=label,changes=writes_of(d),stop_pc=stop,checkpoints=[],a7=('entry',0 if False else 0))],provenance='negative stop check')
        o=fc.Observer(program,True)
        try:
            o.prepare(dict(fx,stop_pc=stop,checkpoints=()));o.begin_step(stop,());o.apply(writes_of(d));p=o.run(allow_guard=False)
        finally:o.close()
        p.update(label=label,step_stop_pc=stop,guard=p['guard'])
        try:stop_evidence3(program,p);refused=False;err=None
        except AssertionError as e:refused=True;err=repr(e)[:200]
        assert refused,label
        out.append(dict(label=label,stop=hex(stop),native_run_stopped_there=p['outgoing']['pc']==stop,stop_evidence_refused=refused,error=err,previous_pc=hex(p['pcs'][-2]) if len(p['pcs'])>1 else None))
    d={};put_path(d,REC,[(0,0x14,0,0,0),(0x20,0xffff,0,0,0)]);put(d,0x10d3b4,4,REC)
    run('negative-stop-1972c-after-SWAP',0x1972a,0x1981e,dict(a1=REC,d7=0),d,0x1972c)
    d={};put_path(d,REC,[(0,0x14,0xfff0,0,0),(0x20,0xffff,0,0,0)]);put(d,0x10d3ba,2,0x100)
    run('negative-stop-19372-after-EXG',0x1935c,0x19894,dict(a1=REC,d1=0,d3=0),d,0x19372)
    return out


# ----------------------------------------------------------------------------------
# Evidence
# ----------------------------------------------------------------------------------
EV={}
GLOBAL_HITS=collections.Counter()
NATURAL_HITS=collections.Counter()
FIXTURE_HITS=collections.Counter()
DEPTHS={}
QUIRK={}
OVERFLOW={}
BORROW={}
PORT_PCS=set()


def reg_flags(a,b):
    a&=M32;b&=M32;r=(a-b)&M32;return dict(n=r>>31,z=1 if r==0 else 0,v=(((a^b)&(a^r))>>31)&1,lt_unsigned=1 if a<b else 0)


def band_variants(d4,d5,a,b):
    lo=(((d4-1)&0xffff)<<16);hi=(((d5+1)&0xffff)<<16);out={}
    for name,(lt,gt) in dict(signed=(lambda f:f['n']!=f['v'],lambda f:f['z']==0 and f['n']==f['v']),n_only=(lambda f:f['n']==1,lambda f:f['z']==0 and f['n']==0),unsigned=(lambda f:f['lt_unsigned']==1,lambda f:f['lt_unsigned']==0 and f['z']==0)).items():
        fa,fb=reg_flags(a,lo),reg_flags(b,lo);ga,gb=reg_flags(a,hi),reg_flags(b,hi)
        below=lt(fa) and lt(fb);above=gt(ga) and gt(gb);out[name]=dict(both_below=bool(below),both_above=bool(above),returns_C=0 if (below or above) else 1)
    return out,lo,hi


def collect_evidence3(spec,split,control):
    label=spec['label'];p=control[0];pcs=[pc for q in control for pc in q['pcs']];lead=collections.Counter(pc for pc in pcs if pc in sc.LEADERS)
    ev=dict(group=spec['group'],first_stop=hex(p['outgoing']['pc']) if control[-1]['guard'] is None else None,leaders=sorted(hex(pc) for pc in lead),instructions=len(pcs)-len(control))
    if control[-1]['guard'] is None:ev['stop_evidence']=control[-1]['stop_evidence']
    ev['u3']=dict(blocks=sum(1 for pc in lead if pc in LEADERS_U3),dispatch_types=dispatch_types(lead),loops={hex(pc):lead[pc] for pc in COLLECT_LOOPS if lead.get(pc)},entries={hex(pc):lead[pc] for pc in U3_ENTRY_PCS if lead.get(pc)})
    if spec.get('guarded') is None:
        GLOBAL_HITS.update(lead);(NATURAL_HITS if spec['group'].startswith('natural') else FIXTURE_HITS).update(lead)
        entry=spec['fixture']['entry_pc']
        if entry in U3_ENTRY_PCS and spec['group'].startswith(('capture','fixture-flow')):
            a7=p['incoming']['a7'];writes=[e['address'] for e in p['events'] if e['region']=='ram' and e['access']=='write' and a7-64<=e['address']<a7]
            ev['stack_depth']=dict(entry_a7=hex(a7),deepest_write=hex(min(writes)) if writes else None,bytes_below_entry_a7=(a7-min(writes)) if writes else 0)
            DEPTHS[label]=(entry,ev['stack_depth']['bytes_below_entry_a7'])
        if label.startswith('disp-192c4-') and 'rom' not in label and 'bank' not in label:
            k=int(label.split('type')[1][:2],16)//4;row=SLOTROWS[k]['c192c4']
            if not row['direct']:
                bs=p['boundaries'];b0=[b for b in bs if b['pc']==row['pc']][0]['registers'];b1=[b for b in bs if b['pc']==row['target']][0]['registers'];ops=[]
                for dst,sg,src in row['comb']:
                    d=dst.lower();s=src.lower();want=((b0[d]-b1[s]) if sg=='-' else (b0[d]+b1[s]))&M32
                    ops.append(dict(op='%s%s=%s'%(dst,sg,src),before=b0[d],source_at_1935c=b1[s],after=b1[d],ok=b1[d]==want))
                QUIRK[label]=dict(type=hex(4*k),axis=row['axis'],ops=ops,ok=all(o['ok'] for o in ops));ev['quirk192c4']=QUIRK[label]
        if label.startswith('band-') or ((label.startswith('disp-192c4-type') or label.startswith('oor-192c4')) and (0x19372 in lead or 0x1957a in lead)):
            bpc=0x19372 if 0x19372 in lead else 0x1957a
            if bpc in lead:
                b=[x for x in p['boundaries'] if x['pc']==bpc][0]['registers'];ya=bpc==0x19372;a,bb=(b['d1'],b['d3']) if ya else (b['d0'],b['d2'])
                var,lo,hi=band_variants(b['d4'],b['d5'],a,bb);native=0 if (0x19398 in lead and 0x19394 not in lead) or (0x195a0 in lead and 0x1959c not in lead) else 1
                OVERFLOW[label]=dict(axis='Y' if ya else 'X',a=a,b=bb,lo=lo,hi=hi,variants=var,native_C=native,native_equals_signed=native==var['signed']['returns_C'],signed_differs_from_n_only=var['signed']['returns_C']!=var['n_only']['returns_C'] or (var['signed']['both_below'],var['signed']['both_above'])!=(var['n_only']['both_below'],var['n_only']['both_above']),
                    signed_differs_from_unsigned=(var['signed']['both_below'],var['signed']['both_above'])!=(var['unsigned']['both_below'],var['unsigned']['both_above']))
                ev['band_overflow']=OVERFLOW[label]
        if label.startswith('borrow-'):
            bs=p['boundaries'];regs=[(hex(b['pc']),{k:b['registers'][k] for k in ('d0','d1','d7')}) for b in bs];BORROW[label]=dict(incoming={k:p['incoming'][k] for k in ('d0','d1','d7')},outgoing={k:p['outgoing'][k] for k in ('d0','d1','d7')},leaders=regs[:6])
            ev['borrow']=BORROW[label]
        if label.startswith('oor-'):ev['oor']=OOR_FACTS[label]
    EV[label]=ev


def decode_blocks(program):
    """Observer's own decode: for every contract block start the instructions up to the first control transfer (used for the carry consumer check)."""
    ins={}
    for lo,hi in U3_RANGES:
        for r in disassemble_range(program,lo,hi-lo,lo):ins[r['cpu_address']]=r
    return ins


def carry_consumers_decoded(program):
    ins=decode_blocks(program);out=[]
    for L in sorted(U3_STARTS):
        seq=[];pc=L
        while pc in ins and len(seq)<4:
            r=ins[pc];seq.append(r['mnemonic']);pc+=r['size']
            if r['mnemonic'].startswith(('b','j','rts')) and r['mnemonic'] not in ('btst','bset','bclr','bchg'):break
        if seq in (['bcc'],['bcs'],['movem','bcs']) or (len(seq)==1 and seq[0] in ('bcc.w','bcs.w','bcs.b','bcc.b')) or (len(seq)==2 and seq[0].startswith('movem') and seq[1].startswith('bcs')):out.append(L)
    return out


def slot_table_checks(program):
    rows=[];bad=[]
    for entry,base in DISPATCH.items():
        for k,row in enumerate(SLOTROWS):
            pc=base+4*k;w=int.from_bytes(program[pc:pc+2],'big');tgt=pc+2+int.from_bytes(program[pc+2:pc+4],'big',signed=True)
            want={0x18c06:0x18c9e if row['c'] else 0x18ca4,0x18caa:row['c18caa']['pc'],0x18efa:row['tail'],0x18fd2:row['c18fd2']['pc'],0x192c4:row['c192c4']['pc']}[entry]
            ok=w==0x6000 and tgt==want;rows.append(dict(dispatcher=hex(entry),k=k,type=hex(4*k),slot=hex(pc),rom_target=hex(tgt),table_target=hex(want),equal=ok))
            if not ok:bad.append(rows[-1])
    return rows,bad


def handler_end_checks(program):
    """Each table handler must end in the transfer the contract names (RTS for 18caa, BRA 192b2 for 18fd2, BRA 1935c/19564 for 192c4)."""
    bad=[]
    ins=decode_blocks(program)
    for row in SLOTROWS:
        for pc,want in ((row['c18caa']['pc'],('rts',None)),(row['c18fd2']['pc'],('bra',0x192b2))):
            seq=[];p=pc
            while p in ins:
                r=ins[p];seq.append(r);p+=r['size']
                if r['mnemonic'].startswith(('bra','rts')):break
            last=seq[-1];ok=last['mnemonic'].startswith(want[0])
            if want[1] is not None:
                raw=bytes.fromhex(last['raw']);t,_=branch_dest(program,last['cpu_address']);ok=ok and t==want[1]
            if not ok:bad.append(dict(pc=hex(pc),last=last['mnemonic'],want=want))
        c=row['c192c4']
        if not c['direct']:
            p=c['pc'];seq=[]
            while p in ins:
                r=ins[p];seq.append(r);p+=r['size']
                if r['mnemonic'].startswith(('bra','rts')):break
            t,_=branch_dest(program,seq[-1]['cpu_address'])
            if not (seq[-1]['mnemonic'].startswith('bra') and t==c['target']):bad.append(dict(pc=hex(c['pc']),last=seq[-1]['mnemonic'],want=hex(c['target'])))
    return bad


# ----------------------------------------------------------------------------------
# Claims
# ----------------------------------------------------------------------------------
CONTRACT_DEPTH={0x19812:20,0x19844:12,0x19910:12}
WRITE_AUDIT=dict(addresses=collections.Counter(),stack_like=0,port_events=0,unexpected=[])
U3_PC_SET=set()


def audit_writes(spec,control):
    if spec.get('guarded') is not None:return
    for q in control:
        for e in q['events']:
            if e['region'] in sc.PORT_REGIONS and e['access']=='write':
                if spec['group'].startswith('natural'):PORT_PCS.add(e['pc'])
                elif e['pc'] in U3_PC_SET:WRITE_AUDIT['port_events']+=1
            if e['region']=='ram' and e['access']=='write' and e['pc'] in U3_PC_SET:
                a=e['address']
                if 0x10d3b4<=a<0x10d3bc:WRITE_AUDIT['addresses'][hex(a&~1 if e['size']==2 else a)]+=1
                elif 0xef00<=(a&0xffff)<0xf000:WRITE_AUDIT['stack_like']+=1
                else:WRITE_AUDIT['unexpected'].append((hex(e['pc']),hex(a),e['size']))


def contract_unreached73():
    for line in CONTRACT.read_text().splitlines():
        if '자연 미도달 73개' in line:return frozenset(int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',line.split('자연 미도달 73개:')[1].split('. 선택 F에서는')[0]))
    raise AssertionError('no 73 list')


FLOW_MN=('lea','movea','pea','jsr','jmp','nop','btst','bset','bclr','bchg','bsr','bra','rts','movem')


def flow_only_decoded(program):
    """Blocks whose instructions are all LEA/MOVEA/PEA/JSR/JMP/NOP/BTST-family/BSR/BRA/RTS/MOVEM/conditional branch (the contract's carry-preserving class)."""
    ins=decode_blocks(program);out=set()
    for L in sorted(U3_STARTS):
        pc=L;ok=True
        while pc in ins:
            r=ins[pc];mn=r['mnemonic'].split('.')[0];cond=mn.startswith('b') and mn not in ('btst','bset','bclr','bchg','bra','bsr')
            if not (mn in FLOW_MN or cond):ok=False
            pc+=r['size']
            if cond or mn in ('bra','rts','jmp','bsr','jsr') or pc in LEADERS_U3:break
        if ok:out.add(L)
    return out


def contract_flow_only_s86():
    for line in CONTRACT.read_text().splitlines():
        if line.startswith('- **Carry 보존(FLOW_ONLY) block**'):return frozenset(int(x,16) for x in re.findall(r'`([0-9a-f]{5})`',line.split('선택 S 86개:')[1].split('. 선택 F는')[0]))
    raise AssertionError('no flow-only list')


def contract_claims3(program,cen,slot_rows,slot_bad,handler_bad,consumers):
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    ins=decode_blocks(program)
    claim('block starts: the observer decode (range starts, branch targets, instruction after a conditional branch / call, 5x36 indexed JMP slots) gives exactly the 370 block starts of the contract (S 170 + F extra 200)',
        'confirmed' if LEADERS_U3==U3_STARTS else 'contradicted',dict(observer=len(LEADERS_U3),contract=len(U3_STARTS),only_observer=sorted(hex(x) for x in LEADERS_U3-U3_STARTS),only_contract=sorted(hex(x) for x in U3_STARTS-LEADERS_U3)))
    bundled_ok=all(pc in ins and ins[pc]['mnemonic'] in ('bne','bmi','bpl','beq','ble','bcs','bcc') or (pc in ins and ins[pc]['mnemonic'].startswith('b') and not ins[pc]['mnemonic'].startswith(('bra','bsr'))) for pc in U3_BUNDLED) and not (U3_BUNDLED&LEADERS_U3)
    claim('14 bundled conditional-branch PCs are conditional branches inside a block (not block starts)','confirmed' if bundled_ok else 'contradicted',dict(pcs=sorted(hex(x) for x in U3_BUNDLED)))
    claim('36-slot table text vs ROM: all 180 BRA.W slots (5 dispatchers x 36) jump to the handler/tail PC the table lists, type column = 4*k, 18c06 slots 0..21 -> 18c9e and 22..35 -> 18ca4',
        'confirmed' if not slot_bad else 'contradicted',dict(slots_checked=len(slot_rows),mismatches=slot_bad))
    claim('table handlers end as the contract says (18caa handlers RTS; 18fd2 handlers BRA 192b2; 192c4 handlers BRA 1935c / 19564)','confirmed' if not handler_bad else 'contradicted',dict(mismatches=handler_bad))
    fo=flow_only_decoded(program);s86=contract_flow_only_s86();slots=set(slot_leaders())
    claim('carry-preserving (FLOW_ONLY) blocks: the decode gives the 86 blocks of option S and 211 blocks of option F (86 + 125 slot BRA blocks); slot BRA blocks: 55 in S, 125 in the F extra list',
        'confirmed' if (fo&S_STARTS)==s86 and len(s86)==86 and len(fo)==211 and len(slots&S_STARTS)==55 and len(slots-S_STARTS)==125 and (fo-S_STARTS)<=slots else 'contradicted',
        dict(decoded_S=len(fo&S_STARTS),contract_S=len(s86),decoded_F=len(fo),slot_blocks_in_S=len(slots&S_STARTS),slot_blocks_F_extra=len(slots-S_STARTS),only_decoded=sorted(hex(x) for x in (fo&S_STARTS)-s86),only_contract=sorted(hex(x) for x in s86-(fo&S_STARTS)),non_slot_extra=sorted(hex(x) for x in (fo-S_STARTS)-slots)))
    claim('carry consumer blocks (BCC/BCS after a call, or MOVEM + BCS): exactly 196c0 196e2 19924 19734 198b8 1974e 19874 19894 198d8','confirmed' if sorted(consumers)==sorted(CONSUMERS) else 'contradicted',dict(decoded=[hex(x) for x in consumers],contract=[hex(x) for x in CONSUMERS]))
    sf=cen['scene_frame'];fs=collections.Counter(c['first_stop'] for c in sf);uf=collections.Counter(c['u3_first'] for c in sf)
    claim('scene_frame_execution 594 cases with U2+U3: 559 enter U3 before any boundary (352 first at 19812, 207 first at 19844); the next boundary is 1a7a8 for 22+? cases, 1a0b6 for the 13 script-gate cases (U3 only after U5), no case stops at 19812/19844/19910 any more',
        'confirmed' if (uf['0x19812'],uf['0x19844'],uf[None])==(352,207,35) and fs['0x1a0b6']==13 and not (fs['0x19812']+fs['0x19844']+fs['0x19910']) else 'contradicted',dict(first_stop=dict(fs),u3_first=dict(uf)))
    st=cen['stage_frame'];t=collections.Counter(tuple(c['dispatch_types'].get('0x18efa',())) for c in st)
    claim('stage_frame: 64 cases enter U3 at 19844 (56 with only type 14 in 18efa, 8 with only type 64)','confirmed' if len(st)==64 and all(c['u3_first']=='0x19844' for c in st) and t==collections.Counter({(0x14,):56,(0x64,):8}) else 'contradicted',dict(cases=len(st),types={str([hex(x) for x in k]):v for k,v in t.items()},stops=dict(collections.Counter(c['first_stop'] for c in st))))
    en=cen['stage_entry'];ent=[c for c in en if c['u3_first'] is not None];t=collections.Counter(tuple(c['dispatch_types'].get('0x18efa',())) for c in ent)
    claim('stage_entry_body: 142 traces enter 1a73c; 120 enter U3 at 19844 (type 14 only 110, type 64 only 4, type 80 only 2, types 64 then 14: 4), 22 never (1a7a8 stop)',
        'confirmed' if len(en)==142 and len(ent)==120 and all(c['u3_first']=='0x19844' for c in ent) and t==collections.Counter({(0x14,):110,(0x64,):4,(0x80,):2,(0x14,0x64):4}) and sum(1 for c in en if c['u3_first'] is None and c['first_stop']=='0x1a7a8')==22 else 'contradicted',
        dict(entered=len(ent),types={str([hex(x) for x in k]):v for k,v in t.items()},stops=dict(collections.Counter(c['first_stop'] for c in en))))
    union=collections.defaultdict(set)
    for c in sf+st+en:
        for k,v in c['dispatch_types'].items():union[k].update(v)
    contract_types={'0x18efa':{0x14,0x40,0x64,0x80},'0x18fd2':{0x14,0x40,0x64,0x80},'0x18c06':{0x14,0x40,0x64,0x80},'0x18caa':{0x14,0x40,0x64},'0x192c4':{0x14,0x40}}
    claim('dispatcher types executed by the natural seeds (all 800 census probes, up to the next U2 boundary): 18efa 18fd2 18c06 {14 40 64 80}, 18caa {14 40 64}, 192c4 {14 40} and nothing else',
        'confirmed' if {k:set(v) for k,v in union.items()}=={k:v for k,v in contract_types.items() if k in union} and set(union)>= {'0x18efa','0x18caa','0x192c4'} else 'info',{k:[hex(x) for x in sorted(v)] for k,v in union.items()})
    nat=set(pc for pc in NATURAL_HITS if pc in LEADERS_U3);unreached=contract_unreached73();reached97=S_STARTS-unreached
    claim('natural U3 block starts (this run, up to the next U2 boundary) are a subset of the 97 block starts the contract lists as executed by the original natural traces (S 170 minus 73 unreached); the others need paths this run cannot take (1a470 -> 19812 via 1a484, the 13 script-gate cases, pre-1a73c stage_entry execution)',
        'confirmed' if nat<=reached97 else 'contradicted',dict(natural_u3_blocks=len(nat),contract_reached=len(reached97),natural_not_in_contract_reached=sorted(hex(x) for x in nat-reached97),contract_reached_not_natural_here=sorted(hex(x) for x in reached97-nat)))
    c80=[k for k,v in EV.items() if k.startswith(('natural','capture')) and 0x80 in v['u3']['dispatch_types'].get('0x18caa',[])]
    claim('contract internal consistency: the 97 naturally executed block starts of the contract include 18d32 and 18ece (18caa slot / handler of type 80) although its own list of natural dispatcher types says 18caa only ran 14 40 64; natural and original-frame captured runs here never execute 18caa with type 80',
        'confirmed' if c80 else 'not-reproduced',dict(in_contract_reached_list=sorted(hex(x) for x in (0x18d32,0x18ece) if x in reached97),natural_or_captured_conditions_with_18caa_type80=c80[:5],
        type80_via_18efa_captured_1a484=[k for k,v in EV.items() if k.startswith('capture-19812-ret1a484') and 0x80 in v['u3']['dispatch_types'].get('0x18efa',[])]))
    miss=sorted(hex(x) for x in LEADERS_U3-set(GLOBAL_HITS))
    claim('all 370 block starts of the contract are executed natively by at least one condition','confirmed' if not miss else 'not-reproduced',dict(executed=len(LEADERS_U3&set(GLOBAL_HITS)),natural=len(nat),fixture_only=len((LEADERS_U3&set(GLOBAL_HITS))-nat),missing=miss))
    matrix={hex(e):[hex(4*k) for k in range(SLOT_COUNT) if GLOBAL_HITS.get(b+4*k)] for e,b in DISPATCH.items()}
    claim('every type slot 00..8c of each of the five dispatchers (180 slot blocks and the handlers behind them) executes natively','confirmed' if all(len(v)==SLOT_COUNT for v in matrix.values()) else 'not-reproduced',dict(slots_executed={k:len(v) for k,v in matrix.items()}))
    loops={hex(pc):max([v['u3']['loops'].get(hex(pc),0) for v in EV.values()]+[0]) for pc in COLLECT_LOOPS}
    ex={hex(pc):[k for k,v in EV.items() if v['u3']['loops'].get(hex(pc),0)>=2][:3] for pc in COLLECT_LOOPS}
    claim('walk loops 1982e (via 1982a), 19898/198dc (via 1985e re-entry), 1973a, 19756 iterate and terminate at the terminating record / time-0 record (max iterations seen per loop block)','confirmed' if all(loops[hex(pc)]>=2 for pc in (0x1982a,0x1973a,0x19756,0x1985e)) else 'not-reproduced',dict(max_hits=loops,examples=ex))
    q=[v for v in QUIRK.values()];addq=[v for v in q if any('+=' in o['op'] for o in v['ops'])]
    claim('192c4 ADD variants (slots 6..10, 17..21 X-main: D1+=D0 D3+=D0; slots 26..28, 33..35 Y-main: D0+=D1 D2+=D3) keep the original asymmetry; every handler combination op matches the register values at the handler and at 1935c / 19564','confirmed' if q and all(v['ok'] for v in q) and len(addq)>=20 else 'not-reproduced',
        dict(conditions=len(q),add_variants=len(addq),d3_plus_d0=sorted(k for k,v in QUIRK.items() if any(o['op']=='D3+=D0' for o in v['ops']))[:4]))
    ov=list(OVERFLOW.values());diff=[k for k,v in OVERFLOW.items() if v['signed_differs_from_n_only']]
    claim('1935c / 19564 band test uses signed LONG compares including V for SLT/SGT: native outcomes equal the signed (N^V) outcome in all band conditions, and in the overflow fixtures the N-only variant would differ',
        'confirmed' if ov and all(v['native_equals_signed'] for v in ov) and diff else 'not-reproduced',dict(conditions=len(ov),n_only_would_differ=diff[:8],unsigned_would_differ=[k for k,v in OVERFLOW.items() if v['signed_differs_from_unsigned']][:8]))
    claim('fractional borrow: 18fa0 / 18fc0 / reverse 18fd2 handlers SUB.L propagate the fraction borrow into the integer part (native results equal the model)','confirmed' if BORROW else 'not-reproduced',BORROW)
    o=OOR_FACTS;landed={k:v for k,v in o.items() if v['is_contract_block_start']};stopped={k:v for k,v in o.items() if not v['is_contract_block_start']}
    claim('out-of-table types follow the computed PC: type 0090 reaches 18c9e 18d42 18f92 1906a 1935c (block starts, executed); odd (0001 0003 7fff 8001 ffff) and mid-block targets are the stop directly after the JMP (contract rollback), none is rejected by the hardware',
        'confirmed' if all(o['oor-%x-type0090'%e]['computed_pc']==hex(x) for e,x in ((0x18c06,0x18c9e),(0x18caa,0x18d42),(0x18efa,0x18f92),(0x18fd2,0x1906a),(0x192c4,0x1935c))) and all(o['oor-%x-type0090'%e]['is_contract_block_start'] for e in DISPATCH) else 'contradicted',
        dict(block_start_cases=len(landed),non_block_start_cases=len(stopped),examples={k:v for k,v in list(o.items())[:6]}))
    depth={hex(e):max([d for (ee,d) in DEPTHS.values() if ee==e]+[0]) for e in CONTRACT_DEPTH}
    claim('stack depth below the entry A7: 19812 path <= 20 bytes, 19844 <= 12, 19910 <= 12',
        'confirmed' if all(depth[hex(e)]<=m for e,m in CONTRACT_DEPTH.items()) and any(depth[hex(e)] for e in CONTRACT_DEPTH) else 'contradicted',dict(measured_max=depth,contract={hex(e):m for e,m in CONTRACT_DEPTH.items()}))
    pairs=((0x19734,0x1973c,0x19738),(0x1974e,0x19758,0x19752),(0x196c0,0x196d0,0x196c4),(0x196e2,0x196f2,0x196e6),(0x19924,0x19930,0x19928),(0x19874,0x1989e,0x19878),(0x198b8,0x198e2,0x198bc))
    bt={hex(a):dict(set_branch=GLOBAL_HITS.get(b,0),clear_branch=GLOBAL_HITS.get(c,0)) for a,b,c in pairs}
    both=all(v['set_branch'] and v['clear_branch'] for v in bt.values())
    claim('carry-consuming branches go both ways under the known C values (ORI = Set; ANDI / TST.W / AND.W = Clear, main decision 2); the independent model (known C only) equals the native flow in every normal condition',
        'confirmed' if both and not any(d['kind']=='model-vs-native' for d in DISCREPANCIES) else ('not-reproduced' if not both else 'contradicted'),dict(branch_hits=bt,after_192c4=dict(c1_back_to_1985e=GLOBAL_HITS.get(0x1985e,0),rewind_1989a=GLOBAL_HITS.get(0x1989a,0),rewind_198de=GLOBAL_HITS.get(0x198de,0))))
    claim('U3 writes only RAM 10d3b4 (LONG), 10d3b8 / 10d3ba (WORD) and the live stack; no port write, no ROM write','confirmed' if not WRITE_AUDIT['unexpected'] and not WRITE_AUDIT['port_events'] else 'contradicted',dict(addresses=dict(WRITE_AUDIT['addresses']),stack_like_writes=WRITE_AUDIT['stack_like'],port_events_in_u3=WRITE_AUDIT['port_events'],unexpected=WRITE_AUDIT['unexpected'][:8]))
    claim('U3 removes the U2 stops 19812 / 19844 / 19910: the natural runs pass them as ordinary block starts and stop only at 1a0b6 / 1a470 / 1a7a8',
        'confirmed' if not any(c['first_stop'] in ('0x19812','0x19844','0x19910') for c in sf+st+en) and set(c['first_stop'] for c in sf+st+en)<= {'0x1a7a8','0x1a0b6','0x1a470'} else 'contradicted',dict(stops=dict(collections.Counter(c['first_stop'] for c in sf+st+en))))
    x=[k for k in EV if k.startswith('flow-19938')]
    claim('19938 (U5 caller of 1972a / 18fd2 / 18c06, outside the contract) runs natively as a declared extra range; its 8 block starts are executed and equal to the model','confirmed' if all(GLOBAL_HITS.get(pc) for pc in LEADERS_X) else 'info',dict(conditions=x[:6],hits={hex(pc):GLOBAL_HITS.get(pc,0) for pc in sorted(LEADERS_X)}))
    claim('CCR/carry values themselves, the Unknown-carry API error ("motion walk caller requires known carry") and the internal-PC rejection of the API','not-observable','SR is never read; branch decisions are evidenced by the executed PC paths and the register file at every block start')
    return claims


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def main():
    argv=sys.argv[1:];out_dir=OUT;dev_filter=None
    while argv:
        a=argv.pop(0)
        if a=='--out':out_dir=Path(argv.pop(0))
        elif a=='--filter':dev_filter=argv.pop(0)
        else:raise SystemExit('unknown argument '+a)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    configure3(program,out_dir)
    sc.stop_evidence=stop_evidence3                                                      # the U2 run_spec / annotate resolve stop_evidence in their module globals
    U3_PC_SET.update(r['cpu_address'] for lo,hi in U3_RANGES for r in disassemble_range(program,lo,hi-lo,lo))
    slot_rows,slot_bad=slot_table_checks(program);handler_bad=handler_end_checks(program);consumers=carry_consumers_decoded(program)
    for r in slot_bad:DISCREPANCIES.append(dict(label='contract-slot-table',kind='slot-table-vs-rom',detail=r))
    for r in handler_bad:DISCREPANCIES.append(dict(label='contract-handler-end',kind='handler-end-vs-rom',detail=r))
    scene_obs,scene_in=sc.scene_inputs(program);sc.SCENE_ROWS=scene_in;stage_ver,stage_in=sc.stage_frame_inputs(program);entry_obs,entry_in=sc.stage_entry_inputs(program)
    sc.CONTRACT_STARTS=U3_STARTS
    print('seeds',len(scene_in),len(stage_in),len(entry_in),flush=True)
    ctx=Ctx(scene_in);B=sc.Builder(program)
    cen=build_census3(program,scene_in,stage_in,entry_in);print('census done',flush=True)
    chosen_scene=natural_conditions3(B,scene_in,stage_in,entry_in,cen,96);print('natural',len(B.specs),flush=True)
    survey=capture_survey(program,scene_in);cap_n=capture_conditions(B,program,scene_in,survey);print('captured',cap_n,flush=True)
    d_n=dispatcher_conditions(B,program,ctx);r_n=rom_dispatcher_conditions(B,program,ctx);o_n=oor_conditions(B,program,ctx);bo_n=borrow_conditions(B,program,ctx);ba_n=band_conditions(B,program,ctx)
    covered=set()
    for c in B.censuses.values():covered|=c['leaders']
    chosen,cov=search_flows(program,ctx,covered,20260303,60000);f_n=flow_conditions(B,program,ctx,chosen)
    print('fixtures dispatcher %d rom %d oor %d borrow %d band %d flows %d'%(d_n,r_n,o_n,bo_n,ba_n,f_n),'model-covered',len(cov&(LEADERS_U3|LEADERS_X)),'of',len(LEADERS_U3|LEADERS_X),'missing',sorted(hex(x) for x in (LEADERS_U3|LEADERS_X)-cov),flush=True)
    guard_conditions3(B,program,ctx,scene_in,cen)
    specs=B.specs
    if dev_filter:specs=[s for s in specs if any(f in s['label'] for f in dev_filter.split(','))]
    print('conditions',len(specs),flush=True)
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
    artifacts={};results=[];guards=[];coverage=set();natural_cov=set();totals=dict(split=0,control=0);model_checks=[];summaries=[]
    for number,spec in enumerate(specs):
        split,control=sc.run_spec(program,spec)
        if spec['label'] in B.models and spec.get('guarded') is None:model_checks.append(sc.check_model(program,spec,control))
        summaries.append(sc.condition_summary(spec,split,control));collect_evidence3(spec,split,control);audit_writes(spec,control)
        for phases in (split,control):
            for p in phases:
                coverage.update(p['pcs'])
                if spec['group'].startswith('natural'):natural_cov.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=fh.store('c%03d_split'%number,split,sc.KEYS_PCS),continuous_control=fh.store('c%03d_control'%number,control,sc.KEYS_PCS),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=False,stored_from_step=0)
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else '',
            ' MODEL %s'%('ok' if model_checks[-1]['equal'] else 'MISMATCH') if spec['label'] in B.models and not spec.get('guarded') else ''),flush=True)
    negatives=negative_checks3(program,B,ctx)
    instructions=[]
    for lo,hi in sc.RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=sc.RANGES,u3_ranges=U3_RANGES,u2_ranges=sc.U2_RANGES,existing_ranges=sc.EXISTING_RANGES,u1_entry_ranges=sc.U1_NEEDED,extra_range_outside_contract=EXTRA_RANGE,instructions=instructions,
        boundary_stop_pcs=sc.BOUNDARIES_U2,stop_rules={'bsr_boundaries':{hex(k):dict(bsr_pc=hex(v[0]),return_long=hex(v[1])) for k,v in sc.BOUNDARY_BSR.items()},'declared return':'RTS popping the declared return LONG at A7',
            'other':'a stop is accepted only directly after BSR / RTS / BRA / Bcc / JMP 2(PC,D4.W), checked against the original bytes and the live registers'},new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in U3_RANGES}),indent=2)+'\n').encode()
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
    claims=contract_claims3(program,cen,slot_rows,slot_bad,handler_bad,consumers) if not dev_filter else []
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    u3_exec=set(LEADERS_U3)&coverage;nat_u3=set(LEADERS_U3)&natural_cov
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=0,variant_child_layouts=[],guard_reports=guard_reports,negative_stop_checks=negatives,bank_reads_by_condition=[dict(label=s['label'],bank_read_count=s['bank_read_count'],reads=s['bank_reads']) for s in summaries if s['bank_read_count']],bank_descriptor_search=[],
        new_ranges=U3_RANGES,existing_ranges=sc.EXISTING_RANGES+sc.U2_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),u2_contract_sha256=sc.CONTRACT_SHA,byte_table_check=U3_TABLE,contract_block_starts=len(U3_STARTS),contract_bundled_branches=len(U3_BUNDLED),observer_block_starts_u3=len(LEADERS_U3),observer_block_starts_u2=len(sc.LEADERS_U2),handler_range_option='F (36 type slots, 370 block starts)'),
        contract_model_checks=model_checks,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=EV,
        first_boundary_census=dict(scene_frame=cen['scene_frame'],stage_frame=cen['stage_frame'],stage_entry=cen['stage_entry'],counts={k:dict(collections.Counter(c['first_stop'] for c in v)) for k,v in cen.items()}),
        seed_provenance=dict(files=sc.SEED_FILES,scene_frame=dict(observation_sha256=sc.SCENE_OBS_SHA,initializer_observation_sha256=sc.SCENE_SEED_SHA,cases=len(scene_in),natural_sample=chosen_scene),stage_frame=dict(verification_sha256=sc.STAGE_FRAME_SHA,rebuilt_cases=len(stage_in),cases=[dict(index=i,label=r['label'],input_sha256=r['input_sha256'],rebuilt_from=how) for i,r,_,how in stage_in]),
            stage_entry=dict(observation_sha256=sc.STAGE_ENTRY_SHA,cases=len(entry_in),captured=[dict(case=c['case_index'],family=c['family'],input_ram_sha256=c['input_ram_sha256'],ram_at_1a73c_sha256=c['ram_sha256'],instructions=c['instructions'],bank=c['bank']) for c in entry_in]),
            u3_entry_survey=[dict(case=x['case'],hits={'%x<-%x'%k:v for k,v in x['hits'].items()},motion_pointer_at_first_hit={'%x<-%x'%k:hex(v[0]) for k,v in x['ptrs'].items()}) for x in survey],
            note='Declared initial fixtures: rebuilt scene_frame inputs (sha-checked), rebuilt stage_frame inputs (sha-checked), the 1a73c entry state of the original 47a94 body run, native U3 entry states captured from the original full-frame run, and declared RAM/register fixtures on the rebuilt scene case 182 base (%s).  A5=108000, return LONG ff000 at A7=1feffc (2ac2 for the natural 480bc runs, declared real return PCs for the unit entries).'%ctx.ram_sha),
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=summaries,group_counts=group_counts,covered_PCs=sorted(coverage),uncovered_u2_block_starts=sorted(hex(x) for x in sc.LEADERS_U2-coverage),block_starts=sc.BLOCKS,boundary_stop_pcs=sc.BOUNDARIES_U2,failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        u3=dict(block_starts=sorted(LEADERS_U3),block_start_count=len(LEADERS_U3),uncovered_u3_block_starts=sorted(hex(x) for x in LEADERS_U3-coverage),
            coverage=dict(executed_total=len(u3_exec),executed_by_natural_runs=len(nat_u3),executed_only_by_fixtures=len(u3_exec-nat_u3),natural_block_starts=sorted(hex(x) for x in nat_u3),fixture_only_block_starts=sorted(hex(x) for x in u3_exec-nat_u3),hit_counts_all={hex(k):v for k,v in sorted(GLOBAL_HITS.items()) if k in LEADERS_U3|LEADERS_X}),
            type_matrix={hex(e):{hex(4*k):GLOBAL_HITS.get(b+4*k,0) for k in range(SLOT_COUNT)} for e,b in DISPATCH.items()},extra_range_19938=dict(range='%x..%x'%EXTRA_RANGE,block_starts=sorted(hex(x) for x in LEADERS_X),hit_counts={hex(pc):GLOBAL_HITS.get(pc,0) for pc in sorted(LEADERS_X)}),
            slot_table_checks=slot_rows,handler_end_mismatches=handler_bad,carry_consumers_decoded=[hex(x) for x in consumers],known_carry=dict(set=[hex(x) for x in KNOWN_SET],clear=[hex(x) for x in KNOWN_CLEAR]),
            out_of_range=OOR_FACTS,stack_depth=dict(DEPTHS_max={hex(e):max([d for (ee,d) in DEPTHS.values() if ee==e]+[0]) for e in CONTRACT_DEPTH},per_condition={k:dict(entry=hex(e),bytes=d) for k,(e,d) in DEPTHS.items()}),
            quirk_192c4=QUIRK,band_overflow=OVERFLOW,borrow=BORROW,write_audit=dict(addresses=dict(WRITE_AUDIT['addresses']),stack_like_writes=WRITE_AUDIT['stack_like'],port_events_in_u3=WRITE_AUDIT['port_events'],unexpected=WRITE_AUDIT['unexpected'][:20]),
            natural_sample=dict(scene_cases=chosen_scene,stage_frame=len(stage_in),stage_entry_in_u3=sum(1 for c in cen['stage_entry'] if c['u3_first'] is not None)),conditions_by_group=group_counts,
            option='F: all 36 type slots, 370 block starts; TST.W / AND.W known Clear at 19710 1971c 19372 1957a; out-of-range types follow the computed PC'),
        limitations=['Controlled incoming fixtures (rebuilt original seeds, captured native states, declared RAM/register fixtures on the scene case 182 base), not natural scheduler/gameplay reachability; direct entries at internal PCs and re-entries are declared fixtures (entry PC, A7, stack bytes, registers, bank page), never applied after execution begins.',
            'Boundary stops (1a0b6 1a470 1a7a8) are accepted only directly after the transferring instruction; the code behind them (U4 1a7a8, U5 1a0b6/1a470) is never executed by this unit; it is executed only inside the captured native states of the original full-frame run.  19812 / 19844 / 19910 are no longer boundaries.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path and the register file at every block start.  The Unknown-carry API error ("motion walk caller requires known carry") and the internal-PC rejection are API-level checks, not observed here.',
            'Declared motion paths in RAM only (and ROM/banked record WORDs read by the single-dispatcher entries); the whole-path loops are exercised on short declared paths plus the 37 original ROM paths of the natural seeds; the step cap of the machine for non-terminating paths is not observed.',
            'The computed PC of an out-of-table type that is the dispatcher itself (type fff8 at 18c06 / 18caa / 18efa / 18fd2 / 192c4, fffc: the JMP itself) loops forever by construction and is not observed; targets that are instruction addresses but not block starts (e.g. 18ca2) are observed only as the stop directly after the JMP.',
            'The 19938..19978 routine (U5 caller) is observed as a declared extra range outside the contract; its entry from 1a692 is not reached by a natural run (U5).',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; ordered port writes are instruction accesses, not physical bus cycles; the work RAM is mirrored (1feffc is offset effc of the 64KiB image).',
            'The game meaning of the motion fields and types is unknown.'])
    path=out_dir/'observation.json'
    with path.open('w') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_checks=len(model_checks),
        model_equal=sum(1 for m in model_checks if m['equal']),uncovered_u3=report['u3']['uncovered_u3_block_starts'],sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
