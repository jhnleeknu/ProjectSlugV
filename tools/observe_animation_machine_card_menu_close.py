"""Unpatched card menu close (a662 -> a2be shrink / 9e94 -> c2c8 fade -> c2e0 timer -> 2a00 child cleanup -> parent 480ac -> 2a00) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the card menu input observer
(observe_animation_machine_card_menu_input) and through it the open / push / card child / fade-card observers: the BIOS-resume chain is re-derived to the
a29c stop, a29c to the a370 stop, the open unit frames, and the 300 declared input frames of the input unit up to its final output (frame 300 done, -e5=2).
That real output is continued by declared PC=2ab8 frame re-entries (A6 = card child, (A6) = c2ba): the close frames a662 -> a2be (word 4(A2) shrinks by
6(A2)<<6 per frame, box redraw through 9b58 and the row clear loop a306), the frame with height 0 (a67a -> 9e94, ADDI.L #10,-f2, a694, c2c8 fade 8c16,
7e(A6)=14, (A6)=c2e0 and the same-frame c2e0 SUBQ), the c2e0 timer frames, the frame that reaches 7e=0 (c2e8: 62(c(A6))=ff, JMP 2a00 -> 299c cleanup ->
A7 <- 104ca4 -> BRA 2ac2 stop) and a declared parent re-entry (PC=2ab8, A6 = parent object) -> 480ac -> 62<>0 -> 480b6 JMP 2a00 -> 2ac2 stop.
Boundary stops (a698, the nested menu return) are stops only: accepted only directly after the transferring instruction (BCS.W at a690), never executed.
Host changes (all declared in the step record): PC=2ab8 re-entries, A6=parent at the parent re-entry (a register change at a step boundary, never inside an
instruction), and RAM fixtures: the cleanup fixture of the object that 2a00 releases (1d(A6) palette-reference count = 0, 6c(A6) coordinate slot = ff, LONG
104ca4 = dispatcher base A7), because the pool slots of the card child and parent are declared fixtures whose 1d/6c bytes are not initialized by the original
chain (without the fixture 299c -> 2782 -> c3fa -> 46ef4 reaches TRAP #15; see the guard condition).  Fresh conditions start from the recorded real chain
outputs with declared host changes (RAM fixture writes, PC redirect, initial registers); nothing is injected after execution begins.
No SR reads, ROM patches, stubs, stack masking or expected-register injection.
This is a native observation, not a C++ comparison.  An independent Python model of the contract (not of the C++) is compared with the native results;
any difference is recorded in contract_discrepancies.
"""
import copy
import json
import os
from pathlib import Path
import struct
import sys
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_card_menu_input as inp
import observe_animation_machine_card_menu_open as op
import observe_animation_machine_card_menu as menu
import observe_animation_machine_card_child as cc
import observe_animation_machine_fade_card as fc
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_menu_close_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-close-contract.md'
CONTRACT_SHA='925c44c1fb66b9489be24073f598b83132d02936a5f0ab46e417fcb145274c38'
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=cc.u32
u8,u16=op.u8,op.u16
DISPATCH=0x2ac2
A662,A698,A2BE,A2D6,A306,N9E94=0xa662,0xa698,0xa2be,0xa2d6,0xa306,0x9e94
A2R=op.A2                      # record 107efe (first/only menu record of the chain)
F2,EE,E5=0x107f0e,0x107f12,op.E5
HEAD,CNT,BASE=0x104c9c,0x104ca0,0x104ca4
W238,W236,W234,B22C=0x107dc8,0x107dca,0x107dcc,0x107dd4
FADE_OLD=(0x107dc2,0x107dc4,0x107dc6)          # -23e,-23c,-23a
FADE_QUO=(0x107dce,0x107dd0,0x107dd2)          # -232,-230,-22e
CB_OPEN,CB_TIMER,CB_PARENT,CB_DEAD=0xc2ba,0xc2e0,0x480ac,0x270e
SINK=0x3c0000

# ----------------------------------------------------------------------------------
# Ranges: exactly the contract table, added to the input unit's ranges (a698 and later are outside every range)
# ----------------------------------------------------------------------------------
CLOSE_RANGES=((0x9e94,0x9ee6),(0xa2be,0xa348),(0xa662,0xa698),(0xc2c8,0xc2fa))
RANGES=inp.RANGES+CLOSE_RANGES
CLOSE_BLOCK_TEXT='9e94 9eb0 9eb8 9ec2 9eca 9eda 9ee4 a2be a2d0 a2d6 a2ec a306 a30e a318 a320 a324 a328 a332 a33c a344 a662 a672 a676 a67a a67e a694 c2c8 c2d6 c2e0 c2e8 c2f8'
CLOSE_BLOCKS=tuple(int(x,16) for x in CLOSE_BLOCK_TEXT.split())
assert len(CLOSE_BLOCKS)==len(set(CLOSE_BLOCKS))==31
EXISTING_BLOCKS=(0x8c16,0x299c,0x2a00,0x2a02,0x480ac,0x480b4,0x480b6)     # fade_card / card child blocks reached by the close path
BLOCKS=tuple(sorted(set(inp.BLOCKS)|set(CLOSE_BLOCKS)|set(EXISTING_BLOCKS)))
BLOCK_SET=frozenset(BLOCKS)
BOUNDARIES=inp.BOUNDARIES+tuple(pc for pc in CLOSE_BLOCKS+EXISTING_BLOCKS if pc not in inp.BOUNDARIES)+(A698,)
KEY_PCS=inp.KEY_PCS+tuple(pc for pc in CLOSE_BLOCKS+EXISTING_BLOCKS+(A698,0xa690,0x2a06) if pc not in inp.KEY_PCS)
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
op.PHASE_LIMIT=2000            # the close frames hit about two hundred first-hit block starts per step (box redraw)
PORT_REGIONS=fc.PORT_REGIONS
INPUT_REPORT=ROOT/'artifacts/animation_machine_card_menu_input_native/observation.json'
DISCREPANCIES=[]
INFO=[]


# ----------------------------------------------------------------------------------
# Observer with one additional declared host change: a register write at a step boundary (parent re-entry A6)
# ----------------------------------------------------------------------------------
class CloseObserver(fc.Observer):
    def apply(self,changes):
        before=self.regs();expected=dict(before);done=[]
        for change in changes:
            kind=change['kind']
            if kind=='ram':self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
            elif kind=='pc':self.cpu.reg_write(fc.REGS['pc'],change['to']);expected['pc']=change['to']
            elif kind=='a7_add':
                expected['a7']=(before['a7']+change['delta'])&0xffffffff;self.cpu.reg_write(fc.REGS['a7'],expected['a7'])
            elif kind=='reg':
                self.cpu.reg_write(fc.REGS[change['name']],change['value']);expected[change['name']]=change['value']
            else:raise AssertionError(kind)
            done.append(dict(change,pc_before=before['pc'],a7_before=before['a7']))
        assert self.regs()==expected
        return done


fc.Observer=CloseObserver


def reg_set(name,value,why):return dict(kind='reg',name=name,value=value&0xffffffff,why=why)
def reentry():return op.reentry()


# ----------------------------------------------------------------------------------
# Stop evidence: boundary stops only directly after the transferring instruction; 2ac2 after the 2a00 chain is reached by BRA.W at 2a06
# ----------------------------------------------------------------------------------
def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc==p['step_stop_pc'] and pc==A698:
        assert len(pcs)>=2 and pcs[-1]==pc,(p['label'],pcs[-3:])
        prev=pcs[-2];assert prev==0xa690 and program[0xa690:0xa694].hex()=='65000006',(p['label'],hex(prev))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,
            reached_from='BCS.W taken at a690 after CMPA.L #107f0e,A2 (A2 = -f2 + 10 < 107f0e: nested menu record below); a698 (nested menu return) is never executed')
    if pc==p['step_stop_pc'] and pc==DISPATCH and len(pcs)>=2 and pcs[-2]==0x2a06:
        prev=0x2a06;assert program[prev:prev+4].hex()=='600000ba' and pcs[-1]==pc,(p['label'],)
        assert u32(p['ram_after'],0)==u32(p['ram_after'],0) and o['a7']==u32(p['ram_after'],BASE),(p['label'],hex(o['a7']),hex(u32(p['ram_after'],BASE)))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,
            reached_from='BRA.W 2ac2 at 2a06 after 2a02 MOVEA.L -335c(A5),A7 (A7=LONG 104ca4=%x)'%o['a7'])
    return inp.stop_evidence(program,p)


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Storage (same rows/artifact names as the input observer; identical payloads are hard-linked)
# ----------------------------------------------------------------------------------
POOL={}


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def store(prefix,phases,min_step=0):
    rows=[]
    for j,p in enumerate(phases):
        if p['step']<min_step:continue
        stem='%s_phase_%03d'%(prefix,j);events=p['events'];ports=[e for e in events if e['region'] in PORT_REGIONS]
        payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
            stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
            stem+'_trace.json':(json.dumps({k:p[k] for k in ('pcs','events','boundaries','guard')},indent=2)+'\n').encode()}
        snapshots=[]
        for k,snapshot in enumerate(p['snapshots']):
            names={}
            for field in ('ram','pvc'):
                name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
            snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
        hashes={name:write_payload(name,data) for name,data in payloads.items()}
        rows.append(dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
            host_changes=p['host_changes'],carry_in=p['carry_in'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
            waiting=p['waiting'],carry=p['carry'],branch_evidence=p['branch_evidence'],guard=p['guard'],snapshots=snapshots,counts=fc.counts(events),
            key_pcs=[pc for pc in p['pcs'] if pc in KEY_PCS],pc_count=len(p['pcs']),artifacts=hashes,stop_evidence=p['stop_evidence']))
    return rows


# ----------------------------------------------------------------------------------
# Checkpoint probe (first hit of each contract block start per step, entry PC excluded), same rule as the open/input observers
# ----------------------------------------------------------------------------------
def with_checkpoints(program,spec,first=0):
    probe=copy.deepcopy(spec)
    for s in probe['steps'][first:]:s['checkpoints']=[]
    try:phases=fc.run_condition(program,probe,True)
    except Exception as e:
        diag=copy.deepcopy(probe);diag['guarded']=True;diag['guard']={}
        try:last=fc.run_condition(program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
        except Exception as e2:info=repr(e2)
        raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(spec['label'],e,info))
    for index,step in enumerate(spec['steps']):
        if index<first:continue
        if index>=len(phases):break
        order=[];entry=phases[index]['pcs'][0]
        for pc in phases[index]['pcs'][1:]:
            if pc in BLOCK_SET and pc not in order and pc!=entry:order.append(pc)
        step['checkpoints']=order
    return spec


# ----------------------------------------------------------------------------------
# Independent model of the contract (python, from the contract text and the ROM bytes quoted there; not the C++).  It works on a copy of the 64KiB RAM image
# (reads below 100000 come from the program image) and only models the effects the contract specifies; 9b58/a018 tile drawing, 8c16 internals, 271c and the
# 2782 reset are executed natively and are compared only through their counts/ports (not modelled byte by byte).
# ----------------------------------------------------------------------------------
class Unsupported(Exception):pass


class Mem:
    def __init__(self,ram,rom):self.r=bytearray(ram);self.rom=rom;self.touched=set()
    def copy(self):
        m=Mem(self.r,self.rom);m.touched=set(self.touched);return m
    def u8(self,a):
        a&=0xffffffff
        if a<0x100000:return self.rom[a]
        if a>=0x200000:raise Unsupported('read outside RAM %x'%a)
        return self.r[a&0xffff]
    def u16(self,a):return (self.u8(a)<<8)|self.u8(a+1)
    def u32(self,a):return (self.u16(a)<<16)|self.u16(a+2)
    def w8(self,a,v):
        a&=0xffffffff
        if a<0x100000 or a>=0x200000:raise Unsupported('write outside RAM %x'%a)
        self.r[a&0xffff]=v&0xff;self.touched.add(a&0xffff)
    def w16(self,a,v):self.w8(a,v>>8);self.w8(a+1,v)
    def w32(self,a,v):self.w16(a,v>>16);self.w16(a+2,v)


def sx16(v):return v-0x10000 if v&0x8000 else v


def a018(M,d0w):
    """a018: True iff a more recent menu record (between -f2 and -ee-10) covers the cell D0.W (C=1)."""
    d7=(d0w-0x7000)&0xffff;d6=d7>>5;d7&=0x1f
    a0=M.u32(EE);a1=M.u32(F2);a0=(a0-0x10)&0xffffffff
    while True:
        if a1>a0:return False
        if (M.u8(a0+0xf)&1)==0:
            d5=((d6&0xff)-M.u8(a0+9))&0xff
            if d5<M.u8(a0+0xb):
                d5=((d7&0xff)-M.u8(a0+0xa))&0xff
                if d5<M.u8(a0+4):return True
        a0=(a0-0x10)&0xffffffff


def a2be(M,a2,out):
    """a2be: shrink 4(A2) by 6(A2)<<6 (WORD, borrow -> a2d0), clear the freed rows (a306 loop, LONG writes to 3c0000)."""
    d0=(M.u8(a2+6)<<6)&0xffff;d1=M.u16(a2+4)
    r=(d1-d0)&0xffff;borrow=d1<d0
    if borrow:d0=(d0+r)&0xffff;d1=0
    else:d1=r
    M.w16(a2+4,d1)
    rows=((((d1&0xff)+d0)&0xffff)>>8)
    p=(M.u8(a2+9)<<5)&0xffff
    p=(p&0xff00)|(((p&0xff)+M.u8(a2+0xa))&0xff)
    p=(p+0x7000)&0xffff
    p=(p&0xff00)|(((p&0xff)+M.u8(a2+4))&0xff)
    out['shrinks'].append(dict(record=a2,borrow=borrow,rows=rows,word4_after=d1,amount=d0))
    counter=rows;lo=p
    while counter!=0:
        saved=lo;d0_32=(0xff<<16)|lo;a2e=M.u32(EE);d7=M.u8(a2e+0xb)
        while d7!=0:
            if a018(M,d0_32&0xffff):out['covered']+=1
            else:
                out['clear_ports'].append(((((d0_32&0xffff)<<16)|(d0_32>>16))&0xffffffff))
            d0_32=(d0_32+0x20)&0xffffffff;d7=(d7-1)&0xff
        lo=(saved+1)&0xffff;counter=(counter-1)&0xffff


def e94(M,out):
    """9e94: A2=-ee; rows 4(A2) times: b(A2) cells LONG (pos<<16)|00ff, pos += 20 per cell (upper WORD), row start +1."""
    a2=M.u32(EE)
    d0=(M.u8(a2+9)<<5)&0xffff
    d0=(d0&0xff00)|(((d0&0xff)+M.u8(a2+0xa))&0xff)
    d0=(d0+0x7000)&0xffff
    d3=d0;d7=M.u8(a2+4);d0_32=d0
    while d7!=0:
        d0_32=((d0_32&0xffff)<<16)|(d0_32>>16);d0_32=(d0_32&0xffff0000)|0xff
        d6=M.u8(a2+0xb)
        while d6!=0:
            out['e94_ports'].append(d0_32);d0_32=(d0_32+0x200000)&0xffffffff;d6=(d6-1)&0xff
        d0_32=((d0_32&0xffff)<<16)|(d0_32>>16);d3=(d3+1)&0xffff;d0_32=(d0_32&0xffff0000)|d3;d7=(d7-1)&0xff


def a370_loop(M,out):
    """a370: records from 107efe down to -f2: -ee<-A2; lower records (A2<>-f2) with f bit0 and 4(A2)<>0 shrink (a3a8 BSR a2be); hook a(A3) must be 0."""
    a2=0x107f0e-0x10;f2=M.u32(F2)
    while a2>=f2:
        M.w32(EE,a2)
        if a2!=f2 and (M.u8(a2+0xf)&1) and M.u8(a2+4)!=0:
            a2be(M,a2,out)
            if M.u8(a2+4)==0:raise Unsupported('a3b4 BSR a6da (lower record height reached 0)')
        a3=M.u32(a2)
        if M.u32(a3+0xa)!=0:raise Unsupported('descriptor hook at a3c6')
        a2=(a2-0x10)&0xffffffff


def fade(M,child,out):
    """c2c8: MOVEQ e1 x3, MOVEQ 14, JSR 8c16 (stores below), c2d6: 7e<-D3, (A6)<-c2e0; c2e0 follows in the same frame."""
    out['fade_regs']=dict(d0=0xffffffe1,d1=0xffffffe1,d2=0xffffffe1,d3=0x14)
    cur=[M.u16(a) for a in FADE_OLD]
    for a in (W238,W236,W234):M.w16(a,0xe100)
    M.w8(B22C,0x14)
    diffs=[(0xe100-c)&0xffff for c in cur]
    if diffs[0]|diffs[1]|diffs[2]:
        for a,df in zip(FADE_QUO,diffs):
            n=sx16(df);q=abs(n)//0x14*(1 if n>=0 else -1);M.w16(a,q&0xffff)
    else:M.w8(B22C,0)
    M.w16(child+0x7e,0x14);M.w32(child,CB_TIMER)


def cleanup(M,a6,out):
    """2a00: 299c (2782 reset, (A6)<-270e, depth/list release loop), A7 <- LONG 104ca4, BRA 2ac2.  Returns the A6 left by 299c."""
    out['watchdog']+=1;out['cleanup_steps']=[]
    M.w32(a6,CB_DEAD)
    if M.u16(a6+0x10)==0:out['resets'].append(a6);out['cleanup_steps'].append(dict(obj=a6,action='depth 0: reset only (29ba -> 271c)'));return a6
    while True:
        a0=M.u32(a6+8);d0=M.u16(a6+0x10)
        if d0<M.u16(a0+0x10):
            out['cleanup_steps'].append(dict(obj=a6,action='kept: next object %x depth %x > %x (29c4 BCS)'%(a0,M.u16(a0+0x10),d0)));return a6
        out['resets'].append(a6);prev=M.u32(a6+4);nxt=M.u32(a6+8)
        M.w32(nxt+4,prev);M.w32(prev+8,nxt);M.w32(a6+8,M.u32(HEAD));M.w32(HEAD,a6);M.w16(CNT,(M.u16(CNT)+1)&0xffff)
        out['cleanup_steps'].append(dict(obj=a6,action='unlinked (prev %x next %x); A6 <- prev'%(prev,nxt)))
        a6=prev
        if M.u32(a6)!=CB_DEAD:return a6
        if M.u16(a6+0x10)==0:return a6


def timer(M,child,out):
    w=(M.u16(child+0x7e)-1)&0xffff;M.w16(child+0x7e,w)
    out['kind']=out['kind'] or 'timer'
    if w!=0:return
    a0=M.u32(child+0xc);M.w8(a0+0x62,0xff);out['kind']='c2e8'
    out['cleanup']=child
    out['a6']=cleanup(M,child,out)
    out['a7_base']=M.u32(BASE)


def child_frame(M,child,out):
    cb=M.u32(child)
    if cb==CB_OPEN:
        a370_loop(M,out)
        a2=M.u32(F2)
        if a2>=0x107f0e:raise Unsupported('a3de -f2 >= 107f0e')
        M.w32(EE,a2)
        if M.u8(E5)!=2:raise Unsupported('-e5 <> 2')
        if M.u8(a2+4)!=0:
            a2be(M,a2,out);out['kind']='shrink'
        else:
            e94(M,out);out['kind']='zero'
            M.w32(F2,(M.u32(F2)+0x10)&0xffffffff)
            if M.u32(F2)<0x107f0e:
                out['pc']=A698;out['kind']='nested-a698';return
            fade(M,child,out);timer(M,child,out);out['kind']='zero' if out['kind']=='zero' else out['kind']
    elif cb==CB_TIMER:
        out['kind']=None;timer(M,child,out)
    else:raise Unsupported('callback %x'%cb)


def parent_frame(M,parent,out):
    if M.u32(parent)!=CB_PARENT:raise Unsupported('parent callback')
    out['kind']='parent'
    if M.u8(parent+0x62)==0:return
    out['cleanup']=parent;out['a6']=cleanup(M,parent,out);out['a7_base']=M.u32(BASE)


def new_out(a6):return dict(kind=None,pc=DISPATCH,a6=a6,shrinks=[],clear_ports=[],e94_ports=[],covered=0,watchdog=0,cleanup=None,fade_regs=None,a7_base=None,cleanup_steps=[],resets=[])


def cleanup_fixture(obj,base_a7,with_base):
    w=[fc.ram_write(obj+0x1d,1,0,'declared cleanup fixture: palette-reference count 1d(A6)=0 of the object released by 2a00 (pool slot bytes are not initialized by the chain)'),
       fc.ram_write(obj+0x6c,1,0xff,'declared cleanup fixture: 6c(A6)=ff (no coordinate slot) of the object released by 2a00')]
    if with_base:w.append(fc.ram_write(BASE,4,base_a7,'declared dispatcher base A7 = LONG 104ca4 (A7 at frame entry; read by 2a02 MOVEA.L -335c(A5),A7)'))
    return w


def object_list(ram,start,limit=8):
    rows=[];a=start
    for _ in range(limit):
        if not (0x100000<=a<0x110000) or a&1:break
        rows.append(dict(address=hex(a),callback=hex(u32(ram,a)),prev=hex(u32(ram,a+4)),next=hex(u32(ram,a+8)),parent_c=hex(u32(ram,a+0xc)),depth=u16(ram,a+0x10),b62=u8(ram,a+0x62)))
        a=u32(ram,a+8)
    return rows


# ----------------------------------------------------------------------------------
# Condition construction
# ----------------------------------------------------------------------------------
def rec_bytes(ram,address):return bytes(ram[(address+i)&0xffff] for i in range(0x10))


def rec_writes(address,data,why):return menu.ram_bytes(address,bytes(data),why)


def wr(address,size,value,why):return fc.ram_write(address,size,value,why)


class Close:
    def __init__(self,program,connected,E,full_split,n_close0,label_E):
        self.program=program;self.connected=connected;self.E=E;self.full_split=full_split;self.n0=n_close0;self.label_E=label_E
        self.child=E['outgoing']['a6'];self.parent=u32(E['ram_after'],self.child+0xc);self.base_a7=E['outgoing']['a7']
        self.specs=[];self.models={}
    def make(self,label,group,prov,base=None,base_label=None,setup=(),decl=None,regs=None,until='parent',max_frames=60,first=None,first_stop=None,direct=None,
            guard=None,model=True,fixture=True,manual=None,parent=None,extra=None,first_a7=None):
        """Model driven condition: frame 1 = declared PC=2ab8 re-entry (or `direct` PC) with `setup` writes; frames follow the model until `until`
        ('parent' = through the parent 2a00 frame, 'zero' = after the height-0 frame, 'cleanup' = after the child 2a00 frame, 'a698' = until the nested stop, int = that many frames)."""
        base=base or self.E;base_label=base_label or self.label_E;decl=dict(decl or {});parent=parent if parent is not None else self.parent
        M=Mem(op.apply_writes(base['ram_after'],list(setup)),self.program)
        steps=[];outcomes=[];a6=base['outgoing']['a6'];phase='child'
        n_frames=until if isinstance(until,int) else max_frames
        for i in range(n_frames):
            ch=[fc.pc_to(direct,'declared direct entry (internal PC, not a frame re-entry)') if (i==0 and direct is not None) else reentry()]
            if i==0:ch+=list(setup)
            if i>0 and (i+1) in decl:
                ch+=list(decl[i+1]);M.r=op.apply_writes(M.r,decl[i+1])
            if i==0 and 1 in decl:
                ch+=list(decl[1]);M.r=op.apply_writes(M.r,decl[1])
            if phase=='parent' and a6!=parent:
                ch.append(reg_set('a6',parent,'declared parent re-entry: A6 = parent object %x (A6 left by 299c is %x)'%(parent,a6)));a6=parent
            stop=DISPATCH;a7=('entry',0)
            if manual is not None:
                oc=None;stop,a7=manual[i]
            elif model:
                def run(MM):
                    out=new_out(a6)
                    if i==0 and first is not None:first(MM,out)
                    elif phase=='parent':parent_frame(MM,parent,out)
                    else:child_frame(MM,self.child,out)
                    return out
                probe=run(M.copy())
                if probe['cleanup'] is not None and fixture:
                    fx=cleanup_fixture(probe['cleanup'],self.base_a7,M.u32(BASE)!=self.base_a7)
                    ch+=fx;M.r=op.apply_writes(M.r,fx)
                M.touched=set()
                oc=run(M)
                oc['frame']=i+1;oc['phase']=phase
                if oc['pc']==A698:stop,a7=A698,('entry',-8)
                elif oc['cleanup'] is not None:a7=('mem32',BASE)
                if first_stop is not None and i==0:stop,a7=first_stop
                watch=set(M.touched)
                for rec in {A2R,(M.u32(F2)-0x10)&0xffffffff,M.u32(F2),M.u32(EE)}:watch.update((rec+k)&0xffff for k in range(0x10))
                for ad,n in ((EE,4),(F2,4),(E5,1),(self.child,4),(self.child+0x7e,2),(self.child+0x80,1),(parent+0x62,1),(self.parent+0x62,1),(HEAD,4),(CNT,2),(BASE,4),(W238,6),(B22C,1)):
                    watch.update((ad+k)&0xffff for k in range(n))
                oc['ram_exp']={a:M.r[a] for a in sorted(watch)};oc['touched']=sorted(M.touched)
                a6=oc['a6']
            else:oc=None
            if first_a7 is not None and i==0:a7=first_a7
            outcomes.append(oc);steps.append(dict(label='%s-f%03d'%(label,i+1),changes=ch,stop_pc=stop,checkpoints=[],a7=a7))
            if oc is None:continue
            if oc['pc']==A698:break
            if oc['cleanup'] is not None:
                if phase=='child' and until=='parent':phase='parent';continue
                if until in ('parent','cleanup'):break
            if phase=='parent':break
            if until=='zero' and oc['kind'] in ('zero',):break
        spec_extra=dict(extra or {})
        if guard is not None:spec_extra.update(guarded=True,guard=guard)
        spec=cc.fresh_spec(self.connected,base,base_label,label,steps,group,prov,regs=regs,**spec_extra)
        with_checkpoints(self.program,spec);self.specs.append(spec)
        if model and manual is None and guard is None:
            self.models[label]=dict(outcomes=outcomes,parent=parent,child=self.child)
        return spec
    def raw(self,label,group,prov,steps,base=None,base_label=None,regs=None,guard=None,extra=None):
        spec_extra=dict(extra or {})
        if guard is not None:spec_extra.update(guarded=True,guard=guard)
        spec=cc.fresh_spec(self.connected,base or self.E,base_label or self.label_E,label,steps,group,prov,regs=regs,**spec_extra)
        with_checkpoints(self.program,spec);self.specs.append(spec)
        return spec


def frame_step(label,changes=None,stop=DISPATCH,a7=('entry',0)):
    return dict(label=label,changes=[reentry()] if changes is None else changes,stop_pc=stop,checkpoints=[],a7=a7)


# ----------------------------------------------------------------------------------
# Native frame outcomes and model comparison
# ----------------------------------------------------------------------------------
def native_ports(p):
    """(video clear-loop LONG values at a32a, 9e94 loop values at 9eca, other video/pvc/watchdog write counts)"""
    ev=p['events']
    return dict(a32a=[int(e['bytes'],16) for e in ev if e['region']=='video' and e['pc']==0xa32a and e['size']==4 and e['address']==SINK],
        e9eca=[int(e['bytes'],16) for e in ev if e['region']=='video' and e['pc']==0x9eca and e['size']==4 and e['address']==SINK],
        watchdog=sum(1 for e in ev if e['region']=='watchdog'),all_ports=sum(1 for e in ev if e['region'] in PORT_REGIONS),
        a018_covered=sum(1 for i in range(len(p['pcs'])-1) if p['pcs'][i]==0xa324 and p['pcs'][i+1]==0xa332),
        a018_open=sum(1 for i in range(len(p['pcs'])-1) if p['pcs'][i]==0xa324 and p['pcs'][i+1]==0xa328))


def check_close_model(spec,meta,split,control):
    res=dict(label=spec['label'],kind='close',frames=[]);ok=True;resets=[]
    for i,oc in enumerate(meta['outcomes'][:len(spec['steps'])]):
        resets+=oc['resets']
        ps=[p for p in control if p['step']==i];assert len(ps)==1;p=ps[0];ram=p['ram_after']
        np_=native_ports(p);o=p['outgoing']
        exp=dict(pc=oc['pc'],a6=oc['a6'],clear_ports=oc['clear_ports'],e94_ports=oc['e94_ports'],watchdog=oc['watchdog'],covered=oc['covered'],open_cells=len(oc['clear_ports']))
        got=dict(pc=o['pc'],a6=o['a6'],clear_ports=np_['a32a'],e94_ports=np_['e9eca'],watchdog=np_['watchdog'],covered=np_['a018_covered'],open_cells=np_['a018_open'])
        if oc['cleanup'] is not None or oc['pc']==A698:
            exp['a7']=oc['a7_base'] if oc['cleanup'] is not None else (p['incoming']['a7']-8)&0xffffffff;got['a7']=o['a7']
        ign={(o_+k)&0xffff for o_ in resets for k in range(0x12,0xc4)}
        bad=[dict(address=hex(0x100000+a),model=v,native=ram[a]) for a,v in oc['ram_exp'].items() if ram[a]!=v and a not in ign]
        if oc['fade_regs'] is not None:
            b=[x for x in p['boundaries'] if x['pc']==0x8c16];exp['fade_regs']=oc['fade_regs']
            got['fade_regs']=dict(d0=b[0]['registers']['d0'],d1=b[0]['registers']['d1'],d2=b[0]['registers']['d2'],d3=b[0]['registers']['d3']&0xff) if b else None
            exp['fade_regs']=dict(oc['fade_regs'],d3=oc['fade_regs']['d3'] & 0xff)
        equal=(exp==got) and not bad
        row=dict(frame=i+1,phase=oc['phase'],kind=oc['kind'],model=exp,native=got,ram_mismatch=bad,equal=equal,model_shrinks=oc['shrinks'],model_cleanup=oc['cleanup_steps'],model_ram_bytes_compared=len(oc['ram_exp'])-len([a for a in oc['ram_exp'] if a in ign]),unmodelled_reset_bytes_not_compared=[hex(o_) for o_ in resets])
        if not equal:
            ok=False;DISCREPANCIES.append(dict(label=spec['label'],frame=i+1,kind=oc['kind'],model=exp,native=got,ram_mismatch=bad[:16]))
        res['frames'].append(row)
    res['equal']=ok
    return res


# ----------------------------------------------------------------------------------
# Frame summaries (per-frame height, ports, timer, fade)
# ----------------------------------------------------------------------------------
def frame_rows(split,control,steps):
    rows=[]
    for index in sorted({p['step'] for p in split}):
        ps=[p for p in split if p['step']==index];first,last=ps[0],ps[-1];events=[e for p in ps for e in p['events']]
        cps=[p for p in control if p['step']==index];assert len(cps)==1 and cps[0]['events']==events,(index,)
        c=cps[0];pcs=c['pcs'];ports=op.ports_of(events);child=first['incoming']['a6']
        rb,ra=first['ram_before'],last['ram_after']
        top=lambda ram:u32(ram,F2)
        rows.append(dict(step=index,label=steps[index]['label'],
            word4_record_107efe_before=u16(rb,A2R+4),word4_record_107efe_after=u16(ra,A2R+4),top_record_before=hex(top(rb)),top_record_after=hex(top(ra)),word4_top_before=u16(rb,top(rb)+4),word4_top_after=u16(ra,top(ra)+4),
            f2_after=hex(u32(ra,F2)),ee_after=hex(u32(ra,EE)),e5_after=u8(ra,E5),child_callback_before=hex(u32(rb,child)),child_callback_after=hex(u32(ra,child)),child_7e_before=u16(rb,child+0x7e),child_7e_after=u16(ra,child+0x7e),
            outgoing_pc=hex(last['outgoing']['pc']),outgoing_a6=hex(last['outgoing']['a6']),outgoing_a7=hex(last['outgoing']['a7']),pc_count_continuous=len(pcs),split_phases=len(ps),counts=fc.counts(events),
            video_long_writes=sum(1 for s,a,v in ports if a in (0x3c0000,0x3c0004) and s==4),video_word_writes=sum(1 for s,a,v in ports if a in (0x3c0000,0x3c0004) and s==2),
            clear_loop_a32a_ports=sum(1 for e in events if e['region']=='video' and e['pc']==0xa32a),e94_loop_ports=sum(1 for e in events if e['region']=='video' and e['pc']==0x9eca),
            watchdog_writes=sum(1 for e in events if e['region']=='watchdog'),ordered_port_writes=len(ports),ordered_ports_sha256=sha(b''.join(struct.pack('>BII',s,a,v) for s,a,v in ports)),
            ordered_ports=[dict(size=s,address=hex(a),value=hex(v)) for s,a,v in ports] if len(ports)<=200 else 'sha256 only (%d writes)'%len(ports),
            a2be_calls=pcs.count(0xa2be),a2d0_borrow=pcs.count(0xa2d0),b9b58_calls=pcs.count(0x9b58),a018_calls=pcs.count(0xa018),a018_set_returns=pcs.count(0xa076),e94_calls=pcs.count(0x9e94),
            reached_c2c8=0xc2c8 in pcs,reached_8c16=0x8c16 in pcs,reached_c2e8=0xc2e8 in pcs,reached_480ac=0x480ac in pcs,a2a00_calls=pcs.count(0x2a00),a299c_calls=pcs.count(0x299c),
            stop_evidence=last['stop_evidence']))
    return rows


# ----------------------------------------------------------------------------------
# The real chain: BIOS resume ... open unit ... 300 input frames (declared fixtures of the input observer) -> recorded output with -e5=2
# ----------------------------------------------------------------------------------
def build_chain(program):
    connected=fc.connected_fixture(program)
    base_steps=[dict(label='connected-47fe8',changes=[],stop_pc=cc.DISPATCH_RETURN,checkpoints=fc.CONNECTED_CK,a7=('entry',4))]+fc.frame_steps(1,fc.LAST_FRAME)
    prev_chain=dict(label='fade-card-chain-47fe8-to-c00468',group='chain',fixture=connected,steps=base_steps,provenance='fade/card unit chain, re-run to obtain the c00468 stop output')
    fade_split=fc.run_condition(program,prev_chain,False);assert fade_split==fc.run_condition(program,prev_chain,False)
    endlast=fc.step_end(fade_split,fc.LAST_FRAME);assert endlast['outgoing']['pc']==fc.BIOS
    child_steps=cc.connection_steps(0x00)+cc.child_steps();n_child=len(child_steps)
    child_spec=cc.fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'card-child-chain-to-a29c',child_steps,'chain','card child chain (declared BIOS resume) to the a29c stop')
    child_split=fc.run_condition(program,child_spec,False);assert child_split==fc.run_condition(program,child_spec,False)
    a29c_end=fc.step_end(child_split,n_child-1);assert a29c_end['outgoing']['pc']==menu.A29C and a29c_end['outgoing']['a7']==0x1feff8
    end_label='card child chain step %d (stop a29c)'%(n_child-1)
    push_step=dict(label='menu-a29c-to-a370',changes=[],stop_pc=menu.A370,checkpoints=[],a7=('entry',0))
    push_spec=cc.fresh_spec(connected,a29c_end,end_label,'menu-push-a29c-to-a370',[push_step],'connected','push unit a29c -> a370 (re-derived)')
    push_a=fc.run_condition(program,push_spec,True);assert push_a==fc.run_condition(program,push_spec,True)
    s0=push_a[-1];assert s0['outgoing']['pc']==op.A370 and u32(s0['ram_after'],s0['outgoing']['a7'])==op.C2C0 and u32(s0['ram_after'],s0['outgoing']['a7']+4)==DISPATCH
    byte4,byte5,cval=u8(s0['ram_after'],A2R+4),u8(s0['ram_after'],A2R+5),u8(s0['ram_after'],A2R+0xc)
    n0,_=op.growth_model(byte4,byte5,cval);open_steps=op.open_steps(n0)
    s0_label='push unit a370 stop (after card child chain step %d, a29c executed)'%(n_child-1)
    open_spec=cc.fresh_spec(connected,s0,s0_label,'connected-a370-to-open',open_steps,'connected','open unit continuation (re-derived)',chain_offset=None)
    open_a=fc.run_condition(program,open_spec,True);assert open_a==fc.run_condition(program,open_spec,True)
    end=open_a[-1];o=end['outgoing']
    assert o['pc']==DISPATCH and o['a7']==0x1ff000 and u32(end['ram_after'],o['a6'])==0xc2ba and u16(end['ram_after'],o['a6']+0x7e)==0x12c
    open_end_label='open unit final output (card child chain step %d a29c, a370 frame 1 and %d growth frames, stop 2ac2)'%(n_child-1,n0)
    saved=(fc.RANGES,fc.BOUNDARIES,fc.KEY_PCS);fc.RANGES,fc.BOUNDARIES,fc.KEY_PCS=inp.RANGES,inp.BOUNDARIES,inp.KEY_PCS
    try:B=inp.build_specs(program,connected,s0,end,open_end_label)      # the input unit's own ranges (its a662 guard conditions need a662 outside the ranges)
    finally:fc.RANGES,fc.BOUNDARIES,fc.KEY_PCS=saved
    chain_spec=next(s for s in B.specs if s['label']=='connected-open-end-to-close')
    input_steps=copy.deepcopy(chain_spec['steps'][:300]);assert len(chain_spec['steps'])==301
    first_open=n_child+1;n_open_end=first_open+n0;n_close0=n_open_end+300
    prefix_steps=child_steps+[copy.deepcopy(push_step)]+copy.deepcopy(open_steps)+input_steps
    assert len(prefix_steps)==n_close0
    return dict(connected=connected,endlast=endlast,child_steps=child_steps,n_child=n_child,push_step=push_step,s0=s0,end=end,n0=n0,open_steps=open_steps,input_steps=input_steps,
        first_open=first_open,n_open_end=n_open_end,n_close0=n_close0,prefix_steps=prefix_steps,open_end_label=open_end_label,B=B,fade_split=fade_split,child_split=child_split,push_a=push_a,open_a=open_a)


# ----------------------------------------------------------------------------------
# Fresh conditions (contract "검증 조건"): declared host changes on the recorded real chain outputs
# ----------------------------------------------------------------------------------
TOP=0x107eee            # a more recent menu record (declared) below the real record 107efe
SIB=0x103000            # the declared "sibling" slot of the card child (alloc_setup), not an object in the chain


def top_record(K,base_ram,height_word,x=None,y=None,w=None,count=None,f=0,why=''):
    """Declared writes: a copy of the real record 107efe at 107eee with changed fields, and -f2(A5)=107eee."""
    rec=bytearray(rec_bytes(base_ram,A2R));rec[4]=height_word>>8;rec[5]=height_word&0xff;rec[0xf]=f
    if x is not None:rec[9]=x
    if y is not None:rec[0xa]=y
    if w is not None:rec[0xb]=w
    if count is not None:rec[6]=count
    return rec_writes(TOP,rec,'declared record at 107eee (copy of 107efe, height word %04x%s)'%(height_word,why))+[wr(F2,4,TOP,'declared -f2(A5)=107eee (the record at 107eee is the top of the menu stack)')]


def build_conditions(K,C,ends,kinds):
    """ends: control phases of the chain by step (index = step); kinds: model kinds of the connected-close frames."""
    n0=K.n0;E=K.E;R=A2R;child=K.child
    idx_zero=kinds.index('zero');idx_c2e8=kinds.index('c2e8')
    E_zero=ends[n0+idx_zero];E_pre=ends[n0+idx_c2e8-1]
    lz='close chain frame %d output (height-0 frame, (A6)=c2e0, 7e=13)'%(idx_zero+1);lp='close chain frame %d output (7e=1, one frame before c2e8)'%idx_c2e8
    ram=E['ram_after']
    def mk(label,group,prov,**kw):return K.make(label,group,'fresh state from the recorded input-unit final output (frame 300, -e5=2, 7e(A6)=0, record 107efe word 0600, 6(A2)=4); '+prov,**kw)
    def mkz(label,group,prov,**kw):return K.make(label,group,'fresh state from the recorded %s; '%lz+prov,base=E_zero,base_label=lz,**kw)
    def mkp(label,group,prov,**kw):return K.make(label,group,'fresh state from the recorded %s; '%lp+prov,base=E_pre,base_label=lp,**kw)
    cnt=lambda v:wr(R+6,1,v,'declared BYTE 6(A2)=%02x (item count; shrink amount 6(A2)<<6)'%v)
    # ---- shrink amount / borrow (a2d0)
    mk('shrink-count6-contract-heights','shrink','declared 6(A2)=6: heights 0600 0480 0300 0180 0000 (the sequence of the first contract draft), then the height-0 frame',setup=[cnt(6)],until='zero')
    for v,u in ((0,3),(1,3),(2,3),(3,'zero'),(5,'zero'),(7,'zero'),(8,'zero'),(0x10,'zero'),(0x80,'zero'),(0xff,'zero')):
        mk('shrink-count-%02x'%v,'shrink','declared 6(A2)=%02x: D0=%04x; borrow path a2d0 when 4(A2) word < D0'%(v,(v<<6)&0xffff),setup=[cnt(v)],until=u)
    for name,w4,v in (('borrow-count8-w4-0100',0x0100,8),('borrow-count8-w4-01ff',0x01ff,8),('exact-count8-w4-0200',0x0200,8),('borrow-count7-w4-0180',0x0180,7),('borrow-count4-never',0x00ff,4),('borrow-count5-w4-0100',0x0100,5),('borrow-count5-w4-0140-exact',0x0140,5)):
        mk(name,'borrow','declared 6(A2)=%02x and word 4(A2)=%04x (byte 4 <> 0 so a662 takes the a2be path)'%(v,w4),setup=[cnt(v),wr(R+4,1,w4>>8,'declared BYTE 4(A2)'),wr(R+5,1,w4&0xff,'declared residual BYTE 5(A2)')],until=3)
    for v in (0x40,0xff,0x01):
        mk('residual-byte5-%02x'%v,'borrow','declared residual BYTE 5(A2)=%02x (word 06%02x): the low byte survives the shrink (WORD SUB) and is added to the freed-row count'%(v,v),setup=[wr(R+5,1,v,'declared residual BYTE 5(A2)')],until='zero')
    # ---- row clear position arithmetic (ADD.B carries are lost), width b
    mk('position-x9-y-f0','position','declared 9(A2)=09 a(A2)=f0: LSL.W #5 gives 0120, ADD.B a(A2) drops the carry out of the byte',setup=[wr(R+9,1,9,'declared BYTE 9(A2)'),wr(R+0xa,1,0xf0,'declared BYTE a(A2)')],until=3)
    mk('position-x-ff-y-ff','position','declared 9(A2)=ff a(A2)=ff',setup=[wr(R+9,1,0xff,'declared BYTE 9(A2)'),wr(R+0xa,1,0xff,'declared BYTE a(A2)')],until=2)
    mk('position-x0-y0','position','declared 9(A2)=00 a(A2)=00',setup=[wr(R+9,1,0,'declared BYTE 9(A2)'),wr(R+0xa,1,0,'declared BYTE a(A2)')],until=2)
    for b in (0,1,2,3,0x30):
        mk('width-b-%02x'%b,'width','declared b(A2)=%02x (b=0: empty row loops in a318 and 9ec2)'%b,setup=[wr(R+0xb,1,b,'declared BYTE b(A2)')],until=3)
    mk('width-b-00-zero-frame','width','declared b(A2)=00 and 4(A2) word 0000 (height-0 frame, 9e94 returns at once)',setup=[wr(R+0xb,1,0,'declared BYTE b(A2)'),wr(R+4,1,0,'declared BYTE 4(A2)'),wr(R+5,1,0,'declared BYTE 5(A2)')],until='zero')
    mk('zero-height-residual-byte5','zero','declared 4(A2) word 0080 (byte 4 = 0: a662 takes a67a although the residual byte is nonzero)',setup=[wr(R+4,1,0,'declared BYTE 4(A2)'),wr(R+5,1,0x80,'declared residual BYTE 5(A2)')],until='zero')
    # ---- nested stack: -f2+10 < 107f0e -> stop a698 (boundary), covered cells through a370's lower-record shrink
    mk('nested-top-height0-stop-a698','nested','declared record at 107eee (word 0000) and -f2=107eee: a67e makes -f2=107efe < 107f0e -> BCS.W a690 -> stop a698 (never executed)',setup=top_record(K,ram,0),until='a698')
    mk('nested-top-height-0200-stop-a698','nested','declared record at 107eee (word 0200, 6(A2)=4): two shrink frames, then the height-0 frame stops at a698',setup=top_record(K,ram,0x0200),until='a698')
    mk('nested-lower-closing-covered','nested','declared record at 107eee (word 0200, x=6 y=5 b=4) above the real record, f(107efe)=01: a370 shrinks the lower record every frame (a3a8 BSR a2be) and a018 reports the cells under the top record as covered (C=1); stop a698 in frame 3',
        setup=top_record(K,ram,0x0200,x=6,y=5,w=4)+[wr(R+0xf,1,1,'declared BYTE f(107efe)=01 (bit0: the lower record is closing)')],until='a698')
    mk('nested-lower-closing-uncovered','nested','same as nested-lower-closing-covered but the top record is far away (x=1c y=1c): no covered cell',
        setup=top_record(K,ram,0x0200,x=0x1c,y=0x1c,w=2)+[wr(R+0xf,1,1,'declared BYTE f(107efe)=01')],until='a698')
    mk('nested-lower-closing-top-f-bit0','nested','top record f=01 (bit0 set: a018 skips it) so nothing is covered although it overlaps; frames until a698',
        setup=top_record(K,ram,0x0200,x=6,y=5,w=4,f=1)+[wr(R+0xf,1,1,'declared BYTE f(107efe)=01')],until=3)
    # ---- direct entries (internal PCs, declared registers/stack; API-level rejection in the C++, native behaviour recorded here)
    assert u32(ram,0x1feffc)==DISPATCH and u32(ram,0x1feff8)==0xc2c0,(hex(u32(ram,0x1feffc)),hex(u32(ram,0x1feff8)))
    def e94_first(MM,out):
        out['kind']='direct-9e94';e94(MM,out)
    for name,h,w_,x,y in (('rows1-b11',1,0x11,None,None),('rows3-b3',3,3,None,None),('rows2-b0',2,0,None,None),('rows4-b1-pos-carry',4,1,9,0xf0)):
        st=[wr(R+4,1,h,'declared BYTE 4(A2) (rows)'),wr(R+0xb,1,w_,'declared BYTE b(A2)')]+([wr(R+9,1,x,'declared BYTE 9(A2)'),wr(R+0xa,1,y,'declared BYTE a(A2)')] if x is not None else [])
        mk('direct-9e94-'+name,'direct','declared direct entry PC=9e94 (A2=-ee=107efe, rows=%d, b=%x), declared initial A7=1feffc so the RTS at 9ee4 pops the 2ac2 LONG left by the frame; stop 2ac2'%(h,w_),
            setup=st,direct=0x9e94,first=e94_first,regs=dict(a7=0x1feffc),until=1,first_a7=('entry',4))
    def a2be_first(MM,out):
        out['kind']='direct-a2be';a2be(MM,R,out)
    stack=[wr(0x1fefF4,4,0xa676,'declared return LONG a676 (BSR a2be at a672) at the initial A7'),wr(0x1fefF8,4,0xc2c0,'declared return LONG c2c0 (JSR a370 at c2ba)'),wr(0x1feffc,4,DISPATCH,'declared return LONG 2ac2 (JSR (A0) at 2ac0)')]
    for name,topw in (('covered',top_record(K,ram,0x0200,x=6,y=5,w=4)),('uncovered',top_record(K,ram,0x0200,x=0x1c,y=0x1c,w=2)),('top-f-bit0',top_record(K,ram,0x0200,x=6,y=5,w=4,f=1)),('top-height0',top_record(K,ram,0x0000,x=6,y=5,w=4))):
        mk('direct-a2be-'+name,'direct','declared direct entry PC=a2be (BSR target) with A2=107efe=-ee, declared stack LONGs a676/c2c0/2ac2 at initial A7=1fefF4 and a higher record at 107eee (-f2): the covering test of a018 sees it; the RTS chain returns to 2ac2',
            setup=topw+stack,direct=0xa2be,first=a2be_first,regs=dict(a7=0x1fefF4),until=1,first_a7=('entry',12))
    # ---- timer entry (7e) from the height-0 frame output
    mkz('timer-7e-0001','timer','declared 7e(A6)=0001: SUBQ.W -> 0, BNE not taken, c2e8 (62(parent)=ff, JMP 2a00); then the parent frame',setup=[wr(child+0x7e,2,1,'declared WORD 7e(A6)=0001')],until='parent')
    mkz('timer-7e-0002','timer','declared 7e(A6)=0002: frame 1 -> 1 (BNE taken), frame 2 -> 0 (c2e8); then the parent frame',setup=[wr(child+0x7e,2,2,'declared WORD 7e(A6)=0002')],until='parent')
    mkz('timer-7e-0000-wrap','timer','declared 7e(A6)=0000: SUBQ.W wraps to ffff, BNE taken (RTS); two more frames fffe fffd',setup=[wr(child+0x7e,2,0,'declared WORD 7e(A6)=0000')],until=3)
    mkz('timer-7e-ffff','timer','declared 7e(A6)=ffff -> fffe, then fffd',setup=[wr(child+0x7e,2,0xffff,'declared WORD 7e(A6)=ffff')],until=2)
    mkz('timer-7e-0100','timer','declared 7e(A6)=0100 (WORD, not BYTE): -> 00ff',setup=[wr(child+0x7e,2,0x100,'declared WORD 7e(A6)=0100')],until=2)
    # ---- parent pointer c(A6) variants (from the frame before c2e8; declared c(A6), 7e=1)
    for name,ptr,prov in (('other-object-103400',0x103400,'c(A6)=103400: 62(103400)=ff, the real parent keeps its own 62'),('self-child',child,'c(A6)=child itself: 62(child)=ff before the cleanup'),('odd-102001',0x102001,'c(A6)=102001 (odd): the BYTE store at 102063 is legal (byte access)'),
            ('ram-end-10ffa0',0x10ffa0,'c(A6)=10ffa0: 62(A0)=110002 is the RAM mirror of 100002')):
        mkp('parent-ptr-'+name,'parent-pointer','declared '+prov+' and 7e(A6)=1 is the recorded value',setup=[wr(child+0xc,4,ptr,'declared LONG c(A6) (parent pointer)')],until='parent')
    mkp('parent-ptr-other-parent62-zero','parent-pointer','c(A6)=103400 and declared 62(real parent)=00: the parent frame 480ac takes RTS (62=0)',setup=[wr(child+0xc,4,0x103400,'declared LONG c(A6)'),wr(K.parent+0x62,1,0,'declared BYTE 62(real parent)=00')],until='parent')
    mkp('parent-ptr-other-parent62-5','parent-pointer','c(A6)=103400 and declared 62(real parent)=05 (nonzero): the parent frame jumps to 2a00',setup=[wr(child+0xc,4,0x103400,'declared LONG c(A6)'),wr(K.parent+0x62,1,5,'declared BYTE 62(real parent)=05')],until='parent')
    # ---- cleanup variants: 299c list release (sibling depth, own depth) after the declared fixture
    sib=lambda d,why:wr(SIB+0x10,2,d,'declared WORD 10(%x)=%04x: %s'%(SIB,d,why))
    mkp('cleanup-sibling-depth-5-kept','cleanup','declared 10(103000)=0005: 4 < 5 -> BCS in 29c4, the child stays in the list with callback 270e',setup=[sib(5,'deeper next object')],until='parent')
    mkp('cleanup-sibling-depth-4-unlink','cleanup','declared 10(103000)=0004: 4 >= 4 -> the child is reset (271c) and unlinked; A6 <- 4(child) = parent; the parent frame follows with A6 already the parent (no register change)',setup=[sib(4,'equal depth')],until='parent')
    mkp('cleanup-sibling-depth-0-unlink','cleanup','declared 10(103000)=0000: the child is unlinked (the parent frame is not run: its predecessor 4(parent) is a garbage pool value)',setup=[sib(0,'shallow next object')],until='cleanup')
    mkp('cleanup-unlink-child-and-parent','cleanup','declared 10(103000)=0003 and 4(parent)=103800: the child is unlinked, then the parent frame unlinks the parent (3 >= 3) with A6 <- 103800',setup=[sib(3,'equal parent depth'),wr(K.parent+4,4,0x103800,'declared LONG 4(parent) (list predecessor) = 103800')],until='parent')
    mkp('cleanup-child-depth-0','cleanup','declared 10(child)=0000: 29b6 BNE not taken, 29ba/29bc reset only (271c), the child stays linked with callback 270e',setup=[wr(child+0x10,2,0,'declared WORD 10(A6)=0')],until='cleanup')
    # ---- guards
    o7=E['outgoing']['a7']
    mkp('guard-cleanup-without-fixture','guard','NO cleanup fixture (1d/6c/104ca4 as left by the chain): 299c -> 2782 -> 8ff4 palette loop -> c3fa -> 46ef4 reads garbage 6c(A6) >= 8 -> TRAP #15 (unsupported_TRAP)',model=False,fixture=False,until=1,guard=dict(problem='unsupported_TRAP',pc=0x46f06,opcode=0x4e4f))
    mk('guard-odd-f2-shrink','guard','declared -f2=107eff (odd record) and BYTE 107f03 (4(A2))=06: a2c6 MOVE.W 4(A2),D1 reads an odd WORD',model=False,until=1,setup=[wr(F2,4,0x107eff,'declared -f2(A5) odd'),wr(0x107f03,1,6,'declared BYTE 4(A2) of the odd record')],
        guard=dict(problem='unsupported_odd_data_access',pc=0xa2c6,address=0x107f03,size=2,access='read'))
    mk('odd-f2-height0','odd','declared -f2=107eff (odd record, 4(A2)=0 so only byte accesses and LONG moves to even addresses): no fault; frames to the height-0 frame',setup=[wr(F2,4,0x107eff,'declared -f2(A5) odd')],until='zero')
    mk('guard-odd-ee-direct-a2be','guard','declared direct entry PC=a2be with A2=107efe, -ee=107eff (odd) and BYTE 107f03=06: 9b58 reads (A2) LONG at the odd -ee',model=False,direct=0xa2be,regs=dict(a7=0x1fefF4),until=1,
        setup=[wr(EE,4,0x107eff,'declared -ee(A5) odd'),wr(0x107f03,1,6,'declared BYTE 4 of the odd record')]+stack,guard=dict(problem='unsupported_odd_data_access',pc=0x9b66,address=0x107eff,size=4,access='read'))
    mk('guard-odd-A7-reentry','guard','declared initial A7=%x (odd) at the 2ab8 re-entry: 2ac0 JSR (A0) writes an odd LONG'%(o7+1),model=False,regs=dict(a7=o7+1),until=1,guard=dict(problem='unsupported_odd_data_access',pc=0x2ac0,address=o7+1-4,size=4,access='write',odd_write_restored=True))
    mk('guard-odd-A7-direct-a2d6','guard','declared direct entry PC=a2d6 with initial A7=1fefF5 (odd): a2e2 MOVE.W D1,-(A7) writes an odd WORD',model=False,direct=A2D6,regs=dict(a7=0x1fefF5),until=1,
        guard=dict(problem='unsupported_odd_data_access',pc=0xa2e2,address=0x1fefF5-2,size=2,access='write',odd_write_restored=True))
    mk('guard-odd-A7-direct-a306','guard','declared direct entry PC=a306 with initial A7=1fefF5 (odd): a306 CMPI.W #0,(A7) reads an odd WORD',model=False,direct=A306,regs=dict(a7=0x1fefF5),until=1,
        guard=dict(problem='unsupported_odd_data_access',pc=0xa306,address=0x1fefF5,size=2,access='read'))
    mk('guard-odd-A6-child','guard','declared initial A6=%x (odd): 2abe MOVEA.L (A6),A0 reads an odd LONG'%(child+1),model=False,regs=dict(a6=child+1),until=1,guard=dict(problem='unsupported_odd_data_access',pc=0x2abe,address=child+1,size=4,access='read'))
    mk('guard-a698-without-stop','guard','the nested configuration with stop 2ac2: BCS.W at a690 transfers to a698, the fetch is refused',model=False,setup=top_record(K,ram,0),until=1,manual=[(DISPATCH,('entry',0))],
        guard=dict(problem='unsupported_code_target',pc=A698,target=A698))
    mk('guard-a6da-lower-reaches-zero','guard','nested configuration with f(107efe)=01 and word 0100: the a370 shrink of the lower record reaches height 0 and a3b4 BSR a6da transfers to a6da (not an executable range)',model=False,until=1,manual=[(DISPATCH,('entry',0))],
        setup=top_record(K,ram,0x0200,x=0x1c,y=0x1c,w=2)+[wr(R+0xf,1,1,'declared BYTE f(107efe)=01'),wr(R+4,1,1,'declared BYTE 4(A2)=01'),wr(R+5,1,0,'declared BYTE 5(A2)=00')],guard=dict(problem='unsupported_code_target',pc=0xa6da,target=0xa6da))
    mkp('guard-parent-ptr-rom0','guard','declared c(A6)=00000000: c2ec MOVE.B #ff,62(A0) writes ROM address 62',model=False,until=1,setup=[wr(child+0xc,4,0,'declared LONG c(A6)=0')],guard=dict(problem='unmapped_or_protected',pc=0xc2ec,address=0x62,size=1))
    mkp('guard-parent-ptr-bank','guard','declared c(A6)=00200000: c2ec writes the read-only bank window at 200062',model=False,until=1,setup=[wr(child+0xc,4,0x200000,'declared LONG c(A6)=200000')],guard=dict(problem='unmapped_or_protected',pc=0xc2ec,address=0x200062,size=1))
    return K


def crosscheck_input(full_split,n_close0,n_open_end):
    """Every step of the re-derived prefix (BIOS resume ... frame 300) against the input observer's report (RAM/PVC after sha256 and outgoing registers of the last phase of the step)."""
    if not INPUT_REPORT.exists():return dict(performed=False,reason='card menu input report not present')
    d=json.loads(INPUT_REPORT.read_text());r=next(x for x in d['results'] if x['label']=='chain-full-bios-resume-to-input')
    last={}
    for q in r['phases']:last[q['step']]=q
    rows=0;bad=[]
    for step in range(n_close0):
        mine=fc.step_end(full_split,step);ref=last[step]
        ref_ram=next(v for k,v in ref['artifacts'].items() if k.endswith('_ram_after.bin'));ref_pvc=next(v for k,v in ref['artifacts'].items() if k.endswith('_pvc_after.bin'))
        if not (sha(mine['ram_after'])==ref_ram and sha(mine['pvc_after'])==ref_pvc and mine['outgoing']==ref['outgoing']):bad.append(step)
        rows+=1
    final=last[n_close0-1]
    return dict(performed=True,reference_report=str(INPUT_REPORT),reference_report_sha256=sha(INPUT_REPORT.read_bytes()),reference_tool_sha256=d['tool_sha256'],condition='chain-full-bios-resume-to-input',steps_compared=rows,first_input_step=n_open_end,
        final_step=n_close0-1,final_label=final['label'],final_ram_after_sha256=next(v for k,v in final['artifacts'].items() if k.endswith('_ram_after.bin')),final_outgoing_pc=hex(final['outgoing']['pc']),mismatching_steps=bad,equal=not bad)


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():old.unlink()
    POOL.clear()
    allowed=set()
    for lo,hi in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(program,lo,hi-lo,lo))
    assert all(pc in allowed for pc in CLOSE_BLOCKS+EXISTING_BLOCKS),[hex(pc) for pc in CLOSE_BLOCKS+EXISTING_BLOCKS if pc not in allowed]
    assert A698 not in allowed and 0xa6da not in allowed
    reports=[ROOT/'artifacts/animation_machine_fade_card_native/observation.json',ROOT/'artifacts/animation_machine_card_child_native/observation.json',ROOT/'artifacts/animation_machine_card_menu_native/observation.json',inp.OPEN_REPORT,INPUT_REPORT]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,inp.CONTRACT,op.CONTRACT,op.PUSH_CONTRACT,ROOT/'docs/analysis/animation-machine-card-child-contract.md',
        ROOT/'docs/analysis/animation-machine-fade-card-contract.md',ROOT/'docs/analysis/animation-machine-map-transfer-contract.md'}
    for report in reports:
        if report.exists():input_paths.add(report)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    # ---- chain prefix: fade/card -> card child -> push -> open -> 300 input frames
    C=build_chain(program);connected=C['connected'];endlast=C['endlast'];n_child=C['n_child'];n_open_end=C['n_open_end'];n_close0=C['n_close0']
    prefix_label='fade/card chain step %d (stop c00468)'%fc.LAST_FRAME
    pre=cc.fresh_spec(connected,endlast,prefix_label,'prefix',C['prefix_steps'],'chain','prefix')
    with_checkpoints(program,pre,first=C['first_open'])
    pre_ph=fc.run_condition(program,pre,True);E300=pre_ph[-1]
    assert E300['step']==n_close0-1 and E300['outgoing']['pc']==DISPATCH and u8(E300['ram_after'],E5)==2 and u16(E300['ram_after'],E300['outgoing']['a6']+0x7e)==0
    e300_label='input unit frame 300 output (re-derived chain step %d, -e5=2, 7e(A6)=0, stop 2ac2)'%(n_close0-1)
    K=Close(program,connected,E300,None,n_close0,e300_label)
    main_spec=K.make('connected-open-end-to-close','connected','fresh CPU started from the recorded input-unit final output (frame 300 done, -e5=2); declared PC=2ab8 re-entries; the cleanup fixture (1d/6c/104ca4) is declared in the frame that reaches 2a00; '
        'the parent re-entry declares A6=parent in addition to PC=2ab8',until='parent')
    kinds=[oc['kind'] for oc in K.models['connected-open-end-to-close']['outcomes']]
    n_close=len(main_spec['steps'])
    # ---- one persistent CPU: BIOS resume -> ... -> input frame 300 -> close frames -> parent 2a00
    full=cc.fresh_spec(connected,endlast,prefix_label,'chain-full-bios-resume-to-close',C['prefix_steps']+copy.deepcopy(main_spec['steps']),'chain',
        'fade/card native chain output at c00468; declared BIOS return and 28ae fixture; card child chain, a29c, a370 and the open unit frames as in the open observer; the 300 declared input frames of the input observer (same declared fixture values); '
        'then the close frames: declared PC=2ab8 re-entries, %d frames (6 shrink frames, the height-0 frame, 7e timer frames, the frame reaching 7e=0 with the declared cleanup fixture) and the declared parent re-entry (PC=2ab8, A6=parent)'%n_close)
    with_checkpoints(program,full,first=C['first_open'])
    for a,b in zip(main_spec['steps'],full['steps'][n_close0:]):
        assert a['changes']==b['changes'] and a['stop_pc']==b['stop_pc'] and a['a7']==b['a7'] and a['checkpoints']==b['checkpoints'],a['label']
    for a,b in zip(C['input_steps'],full['steps'][n_close0-300:n_close0]):
        assert a['changes']==b['changes'] and a['stop_pc']==b['stop_pc'] and a['a7']==b['a7'],a['label']
    ends_ph=fc.run_condition(program,copy.deepcopy(full),True)           # continuous run: outputs by step for the derived conditions
    ends={p['step']:p for p in ends_ph}
    assert sha(ends[n_close0-1]['ram_after'])==sha(E300['ram_after'])
    main_spec['chain_offset']=n_close0
    build_conditions(K,C,ends,kinds)
    specs=K.specs                    # [connected-open-end-to-close, ...conditions]
    # representative fresh frames from the recorded chain outputs (identical steps)
    reps=[]
    def rep(label,after_frame,count):
        src=E300 if after_frame==0 else ends[n_close0+after_frame-1]
        reps.append(cc.fresh_spec(connected,src,e300_label if after_frame==0 else 'close chain frame %d output'%after_frame,label,main_spec['steps'][after_frame:after_frame+count],'fresh-frame',
            'fresh CPU started from the recorded real output of close frame %d; steps are identical to chain close frames %d..%d (declared changes unchanged)'%(after_frame,after_frame+1,after_frame+count),chain_offset=n_close0+after_frame))
    i_zero=kinds.index('zero');i_c2e8=kinds.index('c2e8');i_par=kinds.index('parent')
    rep('fresh-close-frame-001',0,1);rep('fresh-close-frame-002',1,1);rep('fresh-close-frames-005-to-006',4,2);rep('fresh-close-frame-zero-height',i_zero,1);rep('fresh-close-frame-timer-first',i_zero+1,1)
    rep('fresh-close-frame-c2e8',i_c2e8,1);rep('fresh-close-frame-parent',i_par,1);rep('fresh-close-frames-zero-to-parent',i_zero,n_close-i_zero)
    all_specs=[full]+[main_spec]+reps+[s for s in specs if s is not main_spec]
    # ---- run everything
    full_split,full_control=run_spec(program,full)
    chain_cross=crosscheck_input(full_split,n_close0,n_open_end)
    assert chain_cross['performed'] is False or chain_cross['equal'],chain_cross
    cross=cc.crosscheck_fade_card(full_split);cross_child=menu.crosscheck_card_child(full_split,n_child);cross_push=op.crosscheck_push(full_split,n_child+1);cross_open=inp.crosscheck_open(full_split,n_open_end)
    # derived bases equal the persistent chain outputs
    for step,p in ends.items():
        q=fc.step_end(full_split,step);assert sha(p['ram_after'])==sha(q['ram_after']) and sha(p['pvc_after'])==sha(q['pvc_after']) and p['outgoing']==q['outgoing'],step
    cache={full['label']:(full_split,full_control)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;model_checks=[];close_frames={}
    for number,spec in enumerate(all_specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if spec.get('chain_offset') is not None:compared_total+=cc.compare_with_chain(spec,split,full_split)
        if spec['label'] in K.models and spec.get('guard') is None:
            model_checks.append(check_close_model(spec,K.models[spec['label']],split,control))
        if spec['label']=='chain-full-bios-resume-to-close':
            close_frames[spec['label']]=frame_rows([p for p in split if p['step']>=n_close0],[p for p in control if p['step']>=n_close0],full['steps'])
        elif spec.get('guard') is None and spec['group']!='chain':
            close_frames[spec['label']]=frame_rows(split,control,spec['steps'])
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        min_step=n_close0 if spec['label']=='chain-full-bios-resume-to-close' else 0
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=store('c%03d_split'%number,split,min_step),continuous_control=store('c%03d_control'%number,control,min_step),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=bool(spec.get('chain_offset') is not None),stored_from_step=min_step)
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s'%(number+1,len(all_specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else ''),flush=True)
        cache.pop(spec['label'],None)
    instructions=[]
    for lo,hi in CLOSE_RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,close_ranges=CLOSE_RANGES,instructions=instructions,boundary_stop_pcs=(A698,),
        stop_rules={'0xa698':'BCS.W taken at a690 (bytes 65000006) after CMPA.L #107f0e,A2; a698 is never executed and is not in any executable range','0x2ac2 after 2a00':'BRA.W 2ac2 at 2a06 (bytes 600000ba) after 2a02 MOVEA.L -335c(A5),A7'},
        close_bytes={hex(lo):program[lo:hi].hex() for lo,hi in CLOSE_RANGES}),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
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
    chain_rows=close_frames['chain-full-bios-resume-to-close']
    final_ram=fc.step_end(full_split,n_close0+n_close-1)['ram_after'];child_ram=fc.step_end(full_split,n_close0+i_c2e8)['ram_after'];child=K.child;parent=K.parent
    def state(ram,o):
        return dict(a6=hex(o['a6']),a7=hex(o['a7']),pc=hex(o['pc']),objects_from_parent=object_list(ram,parent),child_object=object_list(ram,child,1),free_list_head_104c9c=hex(u32(ram,HEAD)),free_count_104ca0=u16(ram,CNT),dispatcher_base_104ca4=hex(u32(ram,BASE)),
            parent_62=u8(ram,parent+0x62),child_c=hex(u32(ram,child+0xc)),dead_counter_word_104ca2=u16(ram,0x104ca2))
    after_child=fc.step_end(full_split,n_close0+i_c2e8);after_parent=fc.step_end(full_split,n_close0+n_close-1)
    final_state=dict(after_child_2a00=dict(step=n_close0+i_c2e8,**state(child_ram,after_child['outgoing'])),after_parent_2a00=dict(step=n_close0+n_close-1,**state(final_ram,after_parent['outgoing'])),
        before_close_E300=state(E300['ram_after'],E300['outgoing']))
    close_summary=dict(frames=n_close,kinds=kinds,shrink_frames=kinds.count('shrink'),word4_107efe_by_frame=[r['word4_record_107efe_after'] for r in chain_rows],ports_by_frame=[r['ordered_port_writes'] for r in chain_rows],
        clear_loop_ports_by_frame=[r['clear_loop_a32a_ports'] for r in chain_rows],zero_height_frame=i_zero+1,fade_8c16_frame=[i+1 for i,r in enumerate(chain_rows) if r['reached_8c16']],child_7e_after_each_frame=[r['child_7e_after'] for r in chain_rows[:i_c2e8+1]],
        timer_frames_after_zero_height_frame=i_c2e8-i_zero,c2e8_frame=i_c2e8+1,parent_frame=i_par+1,final_stop_pc=chain_rows[-1]['outgoing_pc'],a2d0_borrow_in_chain=sum(r['a2d0_borrow'] for r in chain_rows))
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,fade_card_crosscheck=cross,card_child_crosscheck=cross_child,card_menu_push_crosscheck=cross_push,card_menu_open_crosscheck=cross_open,card_menu_input_crosscheck=chain_cross,
        child_address=hex(child),parent_address=hex(parent),child_frames=cc.child_frame_summary(full_split,child,full['steps'][:n_child]),variant_child_layouts=[],guard_reports=guard_reports,
        bank_reads_by_condition=[],bank_descriptor_search=[],new_ranges=CLOSE_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha),contract_model_checks=model_checks,close_frames=close_frames,close_summary=close_summary,final_state=final_state,contract_discrepancies=DISCREPANCIES,
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        covered_PCs=sorted(coverage),block_starts=BLOCKS,close_block_starts=CLOSE_BLOCKS,existing_block_starts=EXISTING_BLOCKS,boundary_stop_pcs=(A698,),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; frames after the first are declared PC=2ab8 re-entries; the parent re-entry additionally declares A6=parent (a register write at a step boundary, recorded in the step record; never inside an instruction).',
            'The cleanup fixture (1d(A6)=0, 6c(A6)=ff of the object that 2a00 releases, LONG 104ca4 = dispatcher base A7) is a declared RAM fixture: the pool slots of the card child and parent are declared fixtures of earlier observers whose 1d/6c bytes are uninitialized RAM; without it 299c reaches TRAP #15 (guard condition guard-cleanup-without-fixture).',
            'The input fixtures of the 300 prefix frames are the input observer declarations (104cba/104cc0 = 00, 10fdb6 = 01, 10fdb7 = 00); the prefix is re-derived and compared step by step with the input observer report, only the close steps are stored in the chain condition.',
            'Boundary stop a698 is never executed and is not an executable range: it is accepted only directly after the BCS.W at a690. a6da (nested lower record reaching height 0), the nested a698 body and bd26 are not observed (a6da is recorded as a refused fetch).',
            'Split checkpoints are the first hit of each contract block start (open/input unit blocks, the 31 close blocks and 7 existing fade_card/card_child blocks; execution order, entry PC excluded). The continuous run is the control.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path only. The model compares ports, RAM bytes and registers, not CCR.',
            'The 9b58 box redraw, 8c16 internals, 271c reset and 2782/8ff4 palette release are executed natively and only their counts/ports/addresses touched by the contract are modelled.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; direct entries at internal PCs have no native guard of their own (API-level rejection); no general CCR/IRQ/timing/full game completion.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),close_summary=close_summary,sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
