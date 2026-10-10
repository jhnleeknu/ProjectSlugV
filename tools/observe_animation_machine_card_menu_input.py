"""Unpatched card menu input frame (a406 -> bf2c hook -> a44e/a5aa event loops -> a472 input decode) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the card menu
opening observer (observe_animation_machine_card_menu_open) and through it the push / card child / fade-card observers: the BIOS-resume
chain is re-derived to the a29c stop, a29c is executed to the a370 stop, a370 and the box growth frames are executed to the
open unit's final 2ac2 output (7e(A6)=012c, cursor 7(A2)=3, e(A2)=0), and that real output is continued by declared PC=2ab8 frame
re-entries (A6 = card child, (A6) = c2ba).  Each frame runs c2ba JSR a370 -> a3e2 -> (-e5=0) a406 -> a41a -> a42c -> hook bf2c (7e countdown,
e=3 at 1 -> 0, 80(A6) -> a70a, d(A2) from 10fdb6/10fdb7) -> a44e event loop -> a472 input decode (104cba/104cc0 by d(A2)) -> a5aa loop -> a5ce ->
c2c0 -> 2ac2.  a70a -> 3af8 (sound 1a5b) -> a1ee sets -e5=2; the next re-entry stops at a662 (accepted only directly after the BEQ.W at a3f6).
Boundary stops (a662, bd26, 9b58-style hook targets of JSR (A3) at a440 that are not bf2c, and the open unit's boundaries) are stops only: each is accepted only
directly after the transferring instruction, never executed.  Input and card state are declared fixtures: 104cba/104cc0 (game input edge BYTEs)
and 10fdb6/10fdb7 (BIOS area BYTEs) RAM writes are declared host changes in the step record.  Nothing here claims that the original input routine or BIOS
produces those values.  Fresh conditions start from the recorded open-unit 2ac2 output with declared host changes (RAM fixture writes, PC redirect,
initial registers); nothing is injected after execution begins.
No SR reads, ROM patches, stubs, register injection after execution begins, stack masking or expected-register injection.
This is a native observation, not a C++ comparison.  Independent Python models of the contract (not of the C++) are compared with the native results; any difference is
recorded in contract_discrepancies.
"""
import copy
import json
import os
from pathlib import Path
import struct
import sys
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_card_menu_open as op
import observe_animation_machine_card_menu as menu
import observe_animation_machine_card_child as cc
import observe_animation_machine_fade_card as fc
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_menu_input_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-input-contract.md'
CONTRACT_SHA='78fe3d1a0c855e1e491d60c66afca710077585edaf8516076bb89386c72ca604'
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=cc.u32
u8,u16=op.u8,op.u16
DISPATCH=0x2ac2
A662,BD26=0xa662,0xbd26
YES,NO=0xc1c4,0xbf94
SEP=0xfffffffe
A2R=op.A2                       # first (top) menu record 107efe
E6,E5=0x107f1a,op.E5            # -e6(A5), -e5(A5)
IN1,IN2,CD6,CD7=0x104cba,0x104cc0,0x10fdb6,0x10fdb7
HOOK_BF2C=0xbf2c

# ----------------------------------------------------------------------------------
# Ranges: exactly the contract table, added to the open unit's ranges (a370..a406 loop, c2c0 return, callbacks, 3af8 sound are already executable)
# ----------------------------------------------------------------------------------
INPUT_RANGES=((0x9fc4,0x9fce),(0x9ff4,0x9ffe),(0xa1ee,0xa1fa),(0xa406,0xa5d2),(0xa70a,0xa71a),(0xbf2c,0xbf94))
RANGES=op.RANGES+INPUT_RANGES
INPUT_BLOCK_TEXT='9fc4 9ff4 a1ee a406 a412 a416 a41a a424 a42a a42c a43e a442 a444 a44e a458 a46a a472 a484 a488 a492 a496 a4b0 a4b8 a4d2 a4da a4f4 a4fc a516 a51e a538 a540 a55a a562 a566 a570 a574 a57e a582 a58c a596 a5a0 a5aa a5b4 a5c6 a5ce a70a a714 bf2c bf34 bf3e bf48 bf50 bf56 bf5c bf6a bf72 bf76 bf82 bf8a bf8e'
INPUT_BLOCKS=tuple(int(x,16) for x in INPUT_BLOCK_TEXT.split())
assert len(INPUT_BLOCKS)==len(set(INPUT_BLOCKS))==60
BLOCKS=tuple(sorted(set(op.BLOCKS)|set(INPUT_BLOCKS)))
BLOCK_SET=frozenset(BLOCKS)
INPUT_BOUNDARIES=(0x3af8,0xa406,0xa412,0xa41a,0xa424,0xa42c,0xa43e,0xa442,0xa444,0xa44e,0xa472,0xa5aa,0xa5ce,0xa70a,0xa714,0xa1ee,0xbf2c,0xbf3e,0xbf48,0xbf5c,0x9fc4,0x9ff4)
STOP_PCS=(A662,BD26)
BOUNDARIES=op.BOUNDARIES+INPUT_BOUNDARIES
KEY_PCS=op.KEY_PCS+INPUT_BOUNDARIES+STOP_PCS
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
PORT_REGIONS=fc.PORT_REGIONS
HOOK_STOPS=set()      # descriptor hook targets (JSR (A3) at a440) that are not bf2c: stops only
OPEN_REPORT=ROOT/'artifacts/animation_machine_card_menu_open_native/observation.json'

REAL_ITEMS=((False,0),(True,0),(False,YES),(False,NO))     # descriptor c188 items: (separator flag, callback)


def reentry():return op.reentry()


# ----------------------------------------------------------------------------------
# Stop evidence
# ----------------------------------------------------------------------------------
def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc==p['step_stop_pc'] and pc in HOOK_STOPS:
        assert len(pcs)>=2 and pcs[-1]==pc,(p['label'],pcs[-3:])
        prev=pcs[-2];ram=p['ram_after']
        assert prev==0xa440 and program[0xa440:0xa442].hex()=='4e93',(p['label'],hex(prev))
        assert cc.u32(ram,o['a7'])==0xa442 and o['a3']==pc,(p['label'],hex(cc.u32(ram,o['a7'])),hex(o['a3']))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,
            reached_from='JSR (A3) at a440 (bytes 4e93), hook target A3=%x from LONG 6(descriptor)<>0 and <>0 word; return LONG a442 on the stack at A7=%x; hook not executed'%(pc,o['a7']))
    return op.stop_evidence(program,p)


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Storage (same rows/artifact names as the open observer; identical payloads are hard-linked)
# ----------------------------------------------------------------------------------
POOL={}


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def store(prefix,phases):
    rows=[]
    for j,p in enumerate(phases):
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
# Checkpoint probe (first hit of each contract block start per step, entry PC excluded), same rule as the open observer
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
# Independent model of the contract (python, from the contract text and the ROM bytes quoted there; not the C++)
# ----------------------------------------------------------------------------------
def read_state(ram,items,hook,child):
    return dict(c4=u8(ram,A2R+4),c5=u8(ram,A2R+5),c=u8(ram,A2R+0xc),count=u8(ram,A2R+6),c7=u8(ram,A2R+7),c8=u8(ram,A2R+8),e=u8(ram,A2R+0xe),f=u8(ram,A2R+0xf),d=u8(ram,A2R+0xd),
        e6=u8(ram,E6),e5=u8(ram,E5),w7e=u16(ram,child+0x7e),b80=u8(ram,child+0x80),items=items,hook=hook)


def cursor_move(S,reverse):
    """a216: move 7(A2) one step (f bit1 selects the direction), repeat while the item has no callback or is the separator; then 8=7 and e=0."""
    cur=S['c7'];n=S['count']
    for _ in range(4*n+4):
        if reverse:
            cur=cur-1 if cur>0 else (0xff+n)&0xff                      # SUBQ.B #1: borrow when cur was 0 -> ADD.B 6(A2)
        else:
            cur=cur+1
            if cur>=n:cur=0
        sep,cb=S['items'][cur]
        if cb!=0 and not sep:break
    else:raise AssertionError('no selectable item')
    S['c7']=cur;S['c8']=cur;S['e']=0


def deliver(S,ev,out):
    sep,cb=S['items'][S['c8']]
    if cb==YES:
        if ev==0:out['sounds'].append(0x1a6c)
        elif ev==6:S['w7e']=0x12c;cursor_move(S,bool(S['f']&2))
        elif ev==3:return 'bd26'
    elif cb==NO:
        if ev==0:out['sounds'].append(0x1a6c)
        elif ev==6:S['w7e']=0x1e
        elif ev==3:S['b80']=0xff;out['sounds'].append(0x1a5b);S['e5']=2
    return None


def event_loop(S,out):
    while S['e']!=0xff:
        ev=S['e'];S['e']=0xff
        r=deliver(S,ev,out)
        if r:return r
    return None


def model_frame(S,p1,p2,fdb6,fdb7):
    out=dict(sounds=[],stop=None,regrow=False,redraw=False,e6_event=None)
    if S['e5']==2:out['stop']='a662';return out
    assert S['e5']==0,S['e5']
    if S['c4']<S['c']:
        # a412 BSR a348: the box growth step of the open unit (word 4(A2) += c<<6 limited to c<<8, see op.growth_model); no hook, no event, D0=0
        w=(S['c4']<<8)|S['c5'];w=(w+((S['c']<<6)&0xffff))&0xffff;lim=(S['c']<<8)&0xffff
        if lim<w:w=lim
        S['c4']=w>>8;S['c5']=w&0xff;out['regrow']=True;return out
    if S['f']&1:S['f']&=~1;out['redraw']=True
    if S['hook']:
        w=S['w7e']
        if w!=0:
            w=(w-1)&0xffff;S['w7e']=w
            if w==0:S['e']=3
        if S['b80']!=0:
            out['sounds'].append(0x1a5b);S['e5']=2;d=0
        else:d=(1 if fdb6 in (1,3) else 0)|(2 if fdb7 in (1,3) else 0)
        S['d']=d
    S['c8']=S['c7']
    r=event_loop(S,out)
    if r:out['stop']=r;return out
    S['e6']=0;d0=p1 if S['d']&1 else 0;d1=p2 if S['d']&2 else 0
    for bit,act in ((0,'up'),(1,'down'),(2,1),(3,2),(5,4),(4,3)):
        v=(1 if (d0>>bit)&1 else 0)|(2 if (d1>>bit)&1 else 0)
        if v:
            S['e6']=v;out['e6_event']=act
            if act=='up':S['f']|=2;cursor_move(S,True)
            elif act=='down':S['f']&=~2;cursor_move(S,False)
            else:S['e']=act
            r=event_loop(S,out)
            if r:out['stop']=r
            break
    return out


# ----------------------------------------------------------------------------------
# Declared fixtures
# ----------------------------------------------------------------------------------
def recw(off,size,value,why):return fc.ram_write(A2R+off,size,value,why)


def input_writes(p1,p2,why):
    return [fc.ram_write(IN1,1,p1,'declared BYTE 104cba (-3346(A5), P1 input edge) = %02x: %s'%(p1,why)),
            fc.ram_write(IN2,1,p2,'declared BYTE 104cc0 (-3340(A5), P2 input edge) = %02x: %s'%(p2,why))]


def card_writes(a,b,why):
    return [fc.ram_write(CD6,1,a,'declared BYTE 10fdb6 (BIOS area) = %02x: %s'%(a,why)),
            fc.ram_write(CD7,1,b,'declared BYTE 10fdb7 (BIOS area) = %02x: %s'%(b,why))]


def start_writes(start,child):
    spec=dict(c4=(A2R+4,1,'BYTE 4(A2)'),cursor=(A2R+7,1,'BYTE 7(A2) (cursor)'),c=(A2R+0xc,1,'BYTE c(A2)'),e=(A2R+0xe,1,'BYTE e(A2)'),f=(A2R+0xf,1,'BYTE f(A2)'),d=(A2R+0xd,1,'BYTE d(A2)'),
        e5=(E5,1,'BYTE -e5(A5)'),w7e=(child+0x7e,2,'WORD 7e(A6)'),b80=(child+0x80,1,'BYTE 80(A6)'))
    return [fc.ram_write(a,s,start[k],'declared %s = %x'%(w,start[k])) for k,(a,s,w) in spec.items() if k in start]


def stop_for(outcome):
    if outcome['stop']=='a662':return A662,-8
    if outcome['stop']=='bd26':return BD26,-20
    return DISPATCH,0


# ----------------------------------------------------------------------------------
# Condition construction
# ----------------------------------------------------------------------------------
class Builder:
    def __init__(self,program,connected,s0,end,end_label):
        self.program=program;self.connected=connected;self.s0=s0;self.end=end;self.end_label=end_label
        self.child=end['outgoing']['a6'];self.specs=[];self.models={}
    def descriptor(self,items,why,hook=HOOK_BF2C):
        """Declared RAM descriptor (op.descriptor_writes layout) + record retarget; LONG 6(descriptor) = hook (the input-frame hook; +a stays 0)."""
        tuples=[]
        for sep,cb,*rest in items:
            tuples.append((SEP if sep else (b' YES ' if cb==YES else b' NO ' if cb==NO else b' ITEM '),cb,0))
        writes,m=op.retarget(self.program,self.s0,A2R,None,tuples,why)
        writes=list(writes)+[fc.ram_write(op.DESC+6,4,hook,'declared LONG 6(descriptor) = %x (input-frame hook; 0 = no hook)'%hook),recw(4,1,m['rec'][0xc],'declared BYTE 4(A2) = c (box fully open: no regrow)')]
        return writes,m
    def make(self,label,group,prov,frames,items=REAL_ITEMS,hook=True,fdb=(1,0),start=None,setup=(),regs=None,guard=None,direct=None,auto_close=True,model=True,manual_stops=None):
        """frames: list of dict(p1,p2,fdb,declare).  The declared changes of frame 1 are the PC redirect, the setup/start writes, the card bytes; every frame declares both input bytes."""
        start=dict(start or {});end=self.end
        setup=list(setup)+start_writes(start,self.child)
        first_fdb=frames[0].get('fdb',fdb)
        ram=op.apply_writes(end['ram_after'],setup+card_writes(first_fdb[0],first_fdb[1],'x'))
        S=read_state(ram,items,hook,self.child);p1=p2=0;cur_fdb=first_fdb
        steps=[];outcomes=[]
        for i,f in enumerate(frames):
            if 'fdb' in f or i==0:cur_fdb=f.get('fdb',cur_fdb)
            p1=f.get('p1',p1);p2=f.get('p2',p2)
            ch=[fc.pc_to(direct,'declared direct entry (internal PC, not a frame re-entry)') if (i==0 and direct is not None) else reentry()]
            if i==0:ch+=list(setup)
            if i==0 or 'fdb' in f:ch+=card_writes(cur_fdb[0],cur_fdb[1],'frame %d card bytes'%(i+1))
            ch+=input_writes(p1,p2,'frame %d'%(i+1))+list(f.get('declare',()))
            if model and guard is None and direct is None and manual_stops is None:
                oc=model_frame(S,p1,p2,cur_fdb[0],cur_fdb[1]);stop,off=stop_for(oc);oc=dict(oc,state=dict(S,items=None),p1=p1,p2=p2,fdb=cur_fdb)
            else:
                oc=None;stop,off=(manual_stops[i] if manual_stops else (DISPATCH,0))
            outcomes.append(oc);steps.append(dict(label='%s-f%03d'%(label,i+1),changes=ch,stop_pc=stop,checkpoints=[],a7=('entry',off)))
            if oc is not None and oc['stop'] is not None:break
        if auto_close and outcomes and outcomes[-1] is not None and outcomes[-1]['stop'] is None and S['e5']==2:
            oc=model_frame(S,p1,p2,cur_fdb[0],cur_fdb[1]);assert oc['stop']=='a662'
            stop,off=stop_for(oc);outcomes.append(dict(oc,state=dict(S,items=None),p1=p1,p2=p2,fdb=cur_fdb))
            steps.append(dict(label='%s-f%03d'%(label,len(steps)+1),changes=[reentry()]+input_writes(p1,p2,'frame %d'%(len(steps)+1)),stop_pc=stop,checkpoints=[],a7=('entry',off)))
        extra={}
        if guard is not None:extra.update(guarded=True,guard=guard)
        spec=cc.fresh_spec(self.connected,end,self.end_label,label,steps,group,prov,regs=regs,**extra)
        with_checkpoints(self.program,spec);self.specs.append(spec)
        if model and guard is None and direct is None and manual_stops is None:self.models[label]=dict(kind='input',outcomes=outcomes,items=[list(x) for x in items],hook=hook,start=start)
        return spec


def f_(p1=None,p2=None,**kw):
    d=dict(kw)
    if p1 is not None:d['p1']=p1
    if p2 is not None:d['p2']=p2
    return d


def build_specs(program,connected,s0,end,end_label):
    B=Builder(program,connected,s0,end,end_label)
    base='fresh state from the recorded open-unit 2ac2 output (7e(A6)=012c, cursor 3, e=0, live A7 = dispatcher base); '
    # ---- connected chain: 300 no-input frames (7e 012c -> 0), the e=3 frame closes (-e5=2), one more re-entry stops at a662
    frames=[f_(0,0)]+[f_() for _ in range(299)]
    B.make('connected-open-end-to-close','connected',base+'declared fixture RAM in frame 1 only: 104cba=00 104cc0=00 10fdb6=01 10fdb7=00; frames 2..300 declare the same input bytes again (unchanged); '
        'frame 300 is the 7e 1->0 frame (e=3 -> NO callback bf94 event 3 -> 80(A6)=ff -> a70a -> 3af8(1a5b) -> a1ee -e5=2); the appended re-entry stops at a662',frames,fdb=(1,0))
    # ---- input bits, one player and both (priority/-e6)
    bits=(0,1,2,3,5,4)
    for who,fdb,mk in (('p1',(1,0),lambda b:(1<<b,0)),('p2',(0,1),lambda b:(0,1<<b)),('both',(1,1),lambda b:(1<<b,1<<b))):
        for b in bits:
            B.make('input-%s-bit%d'%(who,b),'input-bits',base+'frame 1 without input, frame 2 declares the %s input byte(s) with bit %d (d(A2) from 10fdb6=%d 10fdb7=%d)'%(who,b,fdb[0],fdb[1]),
                [f_(0,0),f_(*mk(b))],fdb=fdb)
    # ---- priority and mixed players (bit order 0,1,2,3,5,4)
    for name,p1,p2,fdb in (('p1-3f',0x3f,0,(1,0)),('p1-3e',0x3e,0,(1,0)),('p1-3c',0x3c,0,(1,0)),('p1-38',0x38,0,(1,0)),('p1-30-bit5-before-bit4',0x30,0,(1,0)),('p1-bit4-and-p2-bit0',0x10,0x01,(1,1)),
            ('p1-bit2-and-p2-bit1',0x04,0x02,(1,1)),('p1-and-p2-3f',0x3f,0x3f,(1,1)),('p1-bit3-bit5-and-p2-bit4',0x28,0x10,(1,1)),('p2-ignored-when-d-bit1-clear',0x04,0x01,(1,0)),('p1-ignored-when-d-bit0-clear',0x01,0x04,(0,1))):
        B.make('priority-'+name,'input-priority',base+'frame 1 without input, frame 2 declares P1=%02x P2=%02x with 10fdb6=%d 10fdb7=%d'%(p1,p2,fdb[0],fdb[1]),[f_(0,0),f_(p1,p2)],fdb=fdb)
    # ---- d(A2) masks from 10fdb6/10fdb7 0/1/2/3 (both inputs carry bit2 = event 1)
    for a in range(4):
        for b in range(4):
            B.make('dmask-fdb6-%d-fdb7-%d'%(a,b),'input-dmask',base+'10fdb6=%d 10fdb7=%d (d bit0 iff 10fdb6 in {1,3}; bit1 iff 10fdb7 in {1,3}); frame 2 declares P1=P2=04'%(a,b),[f_(0,0),f_(4,4)],fdb=(a,b))
    # ---- cursor movement on the real descriptor c188 (items: plain, separator, YES, NO): up/down, wrap, skipping callback-less items
    B.make('cursor-real-up-wrap-down','cursor',base+'real descriptor: P1 bit0 (up) x4 from cursor 3 (3,2,wrap 3,2) then bit1 (down) x4 (3,wrap 2,3,2); the callback-less plain item and the separator are skipped',
        [f_(0,0)]+[f_(1,0)]*4+[f_(2,0)]*4,fdb=(1,0))
    B.make('cursor-real-start2-down-up','cursor',base+'declared 7(A2)=2 (YES): down, down, up, up',[f_(0,0)]+[f_(2,0)]*2+[f_(1,0)]*2,fdb=(1,0),start=dict(cursor=2))
    B.make('cursor-real-p2-up-down','cursor',base+'P2 (10fdb7=1): up, down',[f_(0,0),f_(0,1),f_(0,2)],fdb=(0,1))
    # RAM descriptors (LONG 6(descriptor)=bf2c): separator carrying a callback, many callback-less items, single item
    def desc_cond(label,items,prov,frames,cursor,hook=HOOK_BF2C,fdb=(1,0),extra_start=None,group='cursor-descriptor'):
        writes,m=B.descriptor(items,prov,hook)
        start=dict(cursor=cursor,**(extra_start or {}))
        B.make(label,group,base+'declared RAM descriptor %x (strings %x), record (A2) -> %x, LONG 6(descriptor)=%x: %s'%(op.DESC,op.STRS,op.DESC,hook,prov),frames,items=tuple((bool(i[0]),i[1]) for i in items),hook=bool(hook),fdb=fdb,start=start,setup=writes)
    ITEM=lambda sep,cb:(sep,cb)
    desc_cond('desc-separator-with-callback',[ITEM(False,YES),ITEM(True,YES),ITEM(False,NO)],'items YES, separator carrying callback c1c4, NO (a260 skips the separator): down, down, up, up, up',
        [f_(0,0),f_(2,0),f_(2,0),f_(1,0),f_(1,0),f_(1,0)],0)
    desc_cond('desc-plain-skip-multi',[ITEM(False,0),ITEM(False,YES),ITEM(False,0),ITEM(False,NO),ITEM(False,0)],'items plain, YES, plain, NO, plain: down x3 then up x3 (callback-less items skipped, wrap in both directions)',
        [f_(0,0)]+[f_(2,0)]*3+[f_(1,0)]*3,1)
    desc_cond('desc-single-yes-item',[ITEM(False,YES)],'single YES item: down and up return to item 0 (a216 loops back); select bit4 -> bd26',[f_(0,0),f_(2,0),f_(1,0),f_(0x10,0)],0)
    desc_cond('desc-single-no-item',[ITEM(False,NO)],'single NO item: event 0 sound, select bit4 -> 80(A6)=ff, a662',[f_(0,0),f_(0x10,0)],0)
    # ---- select / events on YES and NO
    B.make('select-yes-bit4-p1','select',base+'declared 7(A2)=2 (YES): frame 2 P1 bit4 -> event 3 -> c1c4 -> BSR bd26 -> stop bd26',[f_(0,0),f_(0x10,0)],fdb=(1,0),start=dict(cursor=2))
    B.make('select-yes-bit4-p2','select',base+'declared 7(A2)=2 (YES): frame 2 P2 bit4, 10fdb7=1',[f_(0,0),f_(0,0x10)],fdb=(0,1),start=dict(cursor=2))
    B.make('select-yes-bit4-both','select',base+'declared 7(A2)=2 (YES): both players bit4 (-e6=3)',[f_(0,0),f_(0x10,0x10)],fdb=(1,1),start=dict(cursor=2))
    for b in (2,3,5):
        B.make('events-yes-bit%d'%b,'select',base+'declared 7(A2)=2 (YES): bit %d event delivered to c1c4 (no effect)'%b,[f_(0,0),f_(1<<b,0)],fdb=(1,0),start=dict(cursor=2))
    B.make('select-no-bit4-p1','select',base+'cursor 3 (NO): frame 2 P1 bit4 -> event 3 -> bf94 -> 80(A6)=ff -> a70a -> 3af8(1a5b) -> a1ee -e5=2; frame 3 stops at a662',[f_(0,0),f_(0x10,0)],fdb=(1,0))
    B.make('select-no-bit4-p2','select',base+'cursor 3 (NO): frame 2 P2 bit4, 10fdb7=1',[f_(0,0),f_(0,0x10)],fdb=(0,1))
    B.make('select-no-then-up','select',base+'cursor 3: P1 bit4 (close) then bit0 in the same fixture byte order is not reached; frame 3 stops at a662 before any input',[f_(0,0),f_(0x10,0),f_(1,0)],fdb=(1,0))
    # ---- 7e countdown boundaries and 80(A6)
    B.make('timer-7e-0-entry','timer',base+'declared 7e(A6)=0000: the hook does not decrement (no e=3); two frames',[f_(0,0),f_()],fdb=(1,0),start=dict(w7e=0))
    B.make('timer-7e-1','timer',base+'declared 7e(A6)=0001: frame 1 decrements to 0 -> e=3 -> NO event 3 -> close; frame 2 stops at a662',[f_(0,0)],fdb=(1,0),start=dict(w7e=1))
    B.make('timer-7e-2','timer',base+'declared 7e(A6)=0002: frame 1 -> 1, frame 2 -> 0 -> e=3 close, frame 3 stops at a662',[f_(0,0),f_()],fdb=(1,0),start=dict(w7e=2))
    B.make('timer-7e-1-cursor-yes','timer',base+'declared 7e(A6)=0001, 7(A2)=2 (YES): e=3 -> c1c4 event 3 -> stop bd26 in frame 1',[f_(0,0)],fdb=(1,0),start=dict(w7e=1,cursor=2))
    B.make('timer-7e-1-same-frame-input','timer',base+'declared 7e(A6)=0001 and P1 bit2 in the same frame: e=3 (hook) is delivered first, then the input event 1',[f_(4,0)],fdb=(1,0),start=dict(w7e=1))
    B.make('timer-7e-ffff','timer',base+'declared 7e(A6)=ffff: SUBQ.W #1 -> fffe (no e=3)',[f_(0,0)],fdb=(1,0),start=dict(w7e=0xffff))
    B.make('b80-nonzero-hook','b80',base+'declared 80(A6)=01: the hook takes bf50 JSR a70a (3af8 1a5b, a1ee -e5=2), d=0; frame 2 stops at a662',[f_(0,0)],fdb=(1,0),start=dict(b80=1))
    B.make('b80-nonzero-7e-1','b80',base+'declared 80(A6)=01 and 7e(A6)=1: 7e reaches 0 (e=3) and 80<>0 -> a70a (then NO event 3 as well, sound 1a5b twice)',[f_(0,0)],fdb=(1,0),start=dict(b80=1,w7e=1))
    # ---- f bit0 redraw (a424 -> 9e1a), f bit1 direction
    B.make('redraw-f-bit0','redraw',base+'declared f(A2)=01: a41a BCLR #0,f -> a424 push A2, JSR 9e1a full redraw, pop; then the normal hook/event path',[f_(0,0),f_()],fdb=(1,0),start=dict(f=1))
    B.make('redraw-f-bit0-bit1-then-input','redraw',base+'declared f(A2)=03 (redraw + reverse direction); frame 2 P1 bit1 (down: BCLR #1,f)',[f_(0,0),f_(2,0)],fdb=(1,0),start=dict(f=3))
    # ---- hook 0 descriptor (CMPA.W #0 -> a444), d(A2) stale
    for d_,p1,p2,name in ((1,1,0,'d1-p1'),(2,0,1,'d2-p2'),(3,2,0,'d3-p1-down'),(0,1,1,'d0-ignored')):
        desc_cond('hook0-'+name,[ITEM(False,0),ITEM(True,0),ITEM(False,YES),ITEM(False,NO)],'LONG 6(descriptor)=0 (no hook): d(A2) is the declared %d, 7e(A6) is not decremented; frame 2 P1=%02x P2=%02x (10fdb6/10fdb7 declared 1/1 but unused)'%(d_,p1,p2),
            [f_(0,0),f_(p1,p2)],3,hook=0,fdb=(1,1),extra_start=dict(d=d_),group='hook0')
    # ---- 4<c: a412 BSR a348 regrow
    for v in (0,3,5,0xff):
        B.make('regrow-4-%02x'%v,'regrow',base+'declared 4(A2)=%02x with c(A2)=06: %s'%(v,'BCC taken (4>=c), normal path' if v>=6 else 'a406 CMP.B c(A2) BCC not taken -> a412 BSR a348 (regrow draw), a416 MOVEQ 0 RTS; no hook, no event'),[f_(0,0),f_()],fdb=(1,0),start=dict(c4=v))
    # ---- hook target stops (descriptor LONG 6(A3) not bf2c): stop at the target, return a442 on the stack
    for name,target in (('9000',0x9000),('c2c0',0xc2c0),('fff00',0xfff00)):
        HOOK_STOPS.add(target)
        writes,m=B.descriptor([ITEM(False,0),ITEM(True,0),ITEM(False,YES),ITEM(False,NO)],'hook %x'%target,target)
        B.make('hook-target-%s'%name,'hook-stop',base+'declared RAM descriptor with LONG 6(descriptor)=%x: a42c A3=hook<>0 -> a43e push A2, JSR (A3) at a440 -> stop at the hook target (return a442 on the stack); the hook is not executed'%target,
            [f_(0,0)],items=REAL_ITEMS,hook=True,fdb=(1,0),start=dict(cursor=3),setup=writes,manual_stops=[(target,-16)])
    # ---- guards
    gp=base+'with '
    odd_rec=[fc.ram_write(0x107ef3,1,1,'declared BYTE 4 of the odd record = 01'),fc.ram_write(0x107efb,1,1,'declared BYTE c of the odd record = 01'),fc.ram_write(0x107efe,1,0,'declared BYTE f of the odd record = 00 (bit0 clear)')]
    B.make('guard-odd-ee-A2','guard',gp+'declared -f2(A5)=107eef (odd) and declared bytes 4/c/f of that record: a3d0 A2=-f2, a3e2 -ee<-A2, -e5=0 -> a406 -> a41a -> a42c MOVEA.L (A2),A3 reads an odd LONG',
        [f_(0,0)],setup=[fc.ram_write(op.F2,4,0x107eef,'declared -f2(A5) odd')]+odd_rec,model=False,guard=dict(problem='unsupported_odd_data_access',pc=0xa430,address=0x107eef,size=4,access='read'))
    odd_desc=[fc.ram_write(A2R,4,op.DESC+1,'declared record pointer (A2) odd (odd descriptor)')]
    B.make('guard-odd-descriptor-A3-a42c','guard',gp+'declared PC=a42c (direct entry; A2=107efe from the recorded output) and record pointer (A2)=%x (odd): a430 A3 odd, a432 MOVEA.L 6(A3),A3 reads an odd LONG'%(op.DESC+1),
        [f_(0,0)],setup=odd_desc,model=False,direct=0xa42c,guard=dict(problem='unsupported_odd_data_access',pc=0xa432,address=op.DESC+7,size=4,access='read'))
    o7=end['outgoing']['a7']
    B.make('guard-odd-A7-a43e','guard',gp+'declared PC=a42c and declared initial A7=%x (odd): a43e MOVE.L A2,-(A7) writes an odd LONG'%(o7+1),[f_(0,0)],model=False,direct=0xa42c,regs=dict(a7=o7+1),
        guard=dict(problem='unsupported_odd_data_access',pc=0xa43e,address=o7+1-4,size=4,access='write',odd_write_restored=True))
    B.make('guard-odd-A7-2ac0','guard',gp+'declared initial A7=%x (odd) at the 2ab8 re-entry: 2ac0 JSR (A0) writes an odd LONG'%(o7+1),[f_(0,0)],model=False,regs=dict(a7=o7+1),
        guard=dict(problem='unsupported_odd_data_access',pc=0x2ac0,address=o7+1-4,size=4,access='write',odd_write_restored=True))
    B.make('guard-hook-target-without-stop','guard',gp+'declared RAM descriptor with LONG 6(descriptor)=fff00 and stop 2ac2: JSR (A3) at a440 transfers to fff00 (outside every executable range), the fetch is refused',[f_(0,0)],items=REAL_ITEMS,model=False,
        setup=B.descriptor([ITEM(False,0),ITEM(True,0),ITEM(False,YES),ITEM(False,NO)],'hook fff00',0xfff00)[0]+[fc.ram_write(A2R+7,1,3,'declared BYTE 7(A2)=3')],guard=dict(problem='unsupported_code_target',pc=0xfff00,target=0xfff00))
    B.make('guard-bd26-without-stop','guard',gp+'declared 7(A2)=2, P1 bit4 and stop 2ac2: BSR bd26 at c1e6 transfers to bd26, the fetch is refused',[f_(0,0),f_(0x10,0)],model=False,start=dict(cursor=2),
        guard=dict(problem='unsupported_code_target',pc=BD26,target=BD26))
    B.make('guard-a662-without-stop','guard',gp+'declared -e5(A5)=02 and stop 2ac2: BEQ.W a662 at a3f6 transfers to a662, the fetch is refused',[f_(0,0)],model=False,start=dict(e5=2),
        guard=dict(problem='unsupported_code_target',pc=A662,target=A662))
    return B


# ----------------------------------------------------------------------------------
# Native frame outcomes and model comparison
# ----------------------------------------------------------------------------------
def assign_events(pcs,events):
    """Chronological events -> index of the executed instruction that produced them (every event carries the pc of its instruction)."""
    out=[];j=0
    for i,pc in enumerate(pcs):
        while j<len(events) and events[j]['pc']==pc:
            out.append((i,events[j]));j+=1
    assert j==len(events),(j,len(events))
    return out


def sound_calls(p):
    pcs=p['pcs'];assigned=assign_events(pcs,p['events']);calls=[];k=0;bs=[b for b in p['boundaries'] if b['pc']==0x3af8]
    for i,pc in enumerate(pcs):
        if pc!=0x3af8:continue
        caller=pcs[i-1];assert caller in (0xa70e,0xa74e),hex(caller)
        ret=0xa714 if caller==0xa70e else 0xa754
        j=next(x for x in range(i+1,len(pcs)) if pcs[x]==ret)
        evs=[e for (x,e) in assigned if i<=x<j]
        calls.append(dict(caller_pc=caller,d0_w=bs[k]['registers']['d0']&0xffff,instruction_count=j-i,path=[hex(x) for x in pcs[i:j]],ram_writes=[dict(pc=e['pc'],address=e['address'],size=e['size'],bytes=e['bytes'],before=e['before']) for e in evs if e['region']=='ram' and e['access']=='write'],
            ram_read_count=sum(1 for e in evs if e['region']=='ram' and e['access']=='read'),other_events=[dict(region=e['region'],access=e['access'],address=e['address'],size=e['size'],bytes=e['bytes']) for e in evs if e['region']!='ram']));k+=1
    assert k==len(bs),(k,len(bs))
    return calls


def native_frame(p,child):
    ram=p['ram_after'];sc=sound_calls(p)
    return dict(c4=u8(ram,A2R+4),c5=u8(ram,A2R+5),c7=u8(ram,A2R+7),c8=u8(ram,A2R+8),e=u8(ram,A2R+0xe),f=u8(ram,A2R+0xf),d=u8(ram,A2R+0xd),e6=u8(ram,E6),e5=u8(ram,E5),w7e=u16(ram,child+0x7e),b80=u8(ram,child+0x80),pc=p['outgoing']['pc'],
        sounds=[c['d0_w'] for c in sc],sound_calls=sc)


DISCREPANCIES=[]


def check_input_model(spec,meta,split,control):
    child=control[0]['outgoing']['a6'];res=dict(label=spec['label'],kind='input',frames=[]);ok=True
    steps=spec['steps']
    assert len(meta['outcomes'])==len(steps)
    for i,oc in enumerate(meta['outcomes'][:len(steps)]):
        ps=[p for p in control if p['step']==i];assert len(ps)==1;nf=native_frame(ps[0],child)
        S=oc['state'];exp=dict(c4=S['c4'],c5=S['c5'],c7=S['c7'],c8=S['c8'],e=S['e'],f=S['f'],d=S['d'],e6=S['e6'],e5=S['e5'],w7e=S['w7e'],b80=S['b80'],sounds=oc['sounds'],pc={None:0x2ac2,'a662':A662,'bd26':BD26}[oc['stop']])
        got={k:nf[k] for k in exp}
        row=dict(frame=i+1,model=exp,native=got,equal=got==exp,p1=oc['p1'],p2=oc['p2'],e6_event=oc['e6_event'],regrow=oc['regrow'],redraw=oc['redraw'])
        if got!=exp:
            ok=False;DISCREPANCIES.append(dict(label=spec['label'],frame=i+1,model=exp,native=got))
        res['frames'].append(row)
    res['equal']=ok
    return res


# ----------------------------------------------------------------------------------
# Frame summaries (ports, sound queue, 7e)
# ----------------------------------------------------------------------------------
def frame_summary(split,control,steps,record=A2R):
    rows=op.frame_rows(split,control,steps,record);child=split[0]['outgoing']['a6']
    for r in rows:
        p=[q for q in control if q['step']==r['step']][0]
        ports=op.ports_of(p['events'])
        nf=native_frame(p,child)
        r.update(sound_queue_ram_104d82_12_before=bytes(p['ram_before'][(0x104d82)&0xffff:(0x104d82+12)&0xffff]).hex(),sound_queue_ram_104d82_12_after=bytes(p['ram_after'][(0x104d82)&0xffff:(0x104d82+12)&0xffff]).hex(),sound_calls=nf['sound_calls'],e_after=nf['e'],f_after=nf['f'],d_after=nf['d'],e6_after=nf['e6'],e5_after=nf['e5'],b80_after=nf['b80'],cursor_after=nf['c7'],
            ordered_ports=[dict(size=s,address=hex(a),value=hex(v)) for s,a,v in ports] if len(ports)<=200 else 'sha256 only (%d writes)'%len(ports))
    return rows


def crosscheck_open(full_split,steps_before):
    if not OPEN_REPORT.exists():return dict(performed=False,reason='card menu open report not present')
    d=json.loads(OPEN_REPORT.read_text());r=next(x for x in d['results'] if x['label']=='chain-full-bios-resume-to-open')
    last=[q for q in r['phases'] if q['step']==steps_before-1][-1];mine=fc.step_end(full_split,steps_before-1)
    ref_ram=next(v for k,v in last['artifacts'].items() if k.endswith('_ram_after.bin'));ref_pvc=next(v for k,v in last['artifacts'].items() if k.endswith('_pvc_after.bin'))
    equal=sha(mine['ram_after'])==ref_ram and sha(mine['pvc_after'])==ref_pvc and mine['outgoing']==last['outgoing']
    return dict(performed=True,reference_report=str(OPEN_REPORT),reference_report_sha256=sha(OPEN_REPORT.read_bytes()),reference_tool_sha256=d['tool_sha256'],condition='chain-full-bios-resume-to-open',step=steps_before-1,
        label=last['label'],ram_after_sha256=ref_ram,pvc_after_sha256=ref_pvc,outgoing_pc=hex(last['outgoing']['pc']),equal=equal)


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
    assert all(pc in allowed for pc in INPUT_BLOCKS),[hex(pc) for pc in INPUT_BLOCKS if pc not in allowed]
    assert A662 not in allowed and BD26 not in allowed
    reports=[ROOT/'artifacts/animation_machine_fade_card_native/observation.json',ROOT/'artifacts/animation_machine_card_child_native/observation.json',ROOT/'artifacts/animation_machine_card_menu_native/observation.json',OPEN_REPORT]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,op.CONTRACT,op.PUSH_CONTRACT,ROOT/'docs/analysis/animation-machine-card-child-contract.md',
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
    # ---- the card child chain (fade/card machinery) to a29c, a29c natively to a370, a370 + box growth natively to the open unit's final 2ac2 output
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
    s0_label='push unit a370 stop (after card child chain step %d, a29c executed)'%(n_child-1)
    byte4,byte5,cval=u8(s0['ram_after'],A2R+4),u8(s0['ram_after'],A2R+5),u8(s0['ram_after'],A2R+0xc)
    n0,_=op.growth_model(byte4,byte5,cval)
    open_steps=op.open_steps(n0)
    open_spec=cc.fresh_spec(connected,s0,s0_label,'connected-a370-to-open',open_steps,'connected','open unit continuation (re-derived): a370 frame 1 and the box growth re-entries to the a5ea frame and the 2ac2 stop',chain_offset=None)
    open_a=fc.run_condition(program,open_spec,True);assert open_a==fc.run_condition(program,open_spec,True)
    end=open_a[-1];o=end['outgoing']
    assert o['pc']==DISPATCH and o['a7']==0x1ff000 and u32(end['ram_after'],o['a6'])==0xc2ba and u16(end['ram_after'],o['a6']+0x7e)==0x12c and u8(end['ram_after'],A2R+7)==3 and u8(end['ram_after'],A2R+0xe)==0 and u8(end['ram_after'],E5)==0
    open_end_label='open unit final output (card child chain step %d a29c, a370 frame 1 and %d growth frames, stop 2ac2)'%(n_child-1,n0)
    B=build_specs(program,connected,s0,end,open_end_label)
    specs=B.specs;models=B.models
    chain_label='connected-open-end-to-close'
    chain_spec=next(s for s in specs if s['label']==chain_label)
    # ---- one persistent CPU: BIOS resume -> ... -> a29c -> a370 -> open frames -> input frames -> a662
    open_cp=copy.deepcopy(open_steps)
    full=cc.fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'chain-full-bios-resume-to-input',child_steps+[copy.deepcopy(push_step)]+open_cp+copy.deepcopy(chain_spec['steps']),'chain',
        'fade/card native chain output at c00468; declared BIOS return and 28ae fixture; card child chain, a29c, a370 and the open unit frames as in the open observer; then the input unit frames: declared PC=2ab8 re-entries with declared fixture RAM '
        '(104cba/104cc0 = 00, 10fdb6 = 01, 10fdb7 = 00) in the first input frame, 300 frames until 7e reaches 0 (e=3, NO event 3, 80(A6)=ff, a70a, a1ee -e5=2) and a final re-entry stopping at a662')
    first_open=n_child+1
    with_checkpoints(program,full,first=first_open)
    n_open_end=first_open+n0                         # index of the first input frame
    full_split,full_control=run_spec(program,full)
    mid=fc.step_end(full_split,n_open_end-1)
    assert mid['outgoing']==end['outgoing'] and mid['ram_after']==end['ram_after'] and mid['pvc_after']==end['pvc_after']
    cross=cc.crosscheck_fade_card(full_split);cross_child=menu.crosscheck_card_child(full_split,n_child);cross_push=op.crosscheck_push(full_split,n_child+1);cross_open=crosscheck_open(full_split,n_open_end)
    chain_spec['chain_offset']=n_open_end
    # steps of the connected spec must equal the chain steps (checkpoints from the same probe rule)
    for a,b in zip(chain_spec['steps'],full['steps'][n_open_end:]):
        assert a['changes']==b['changes'] and a['stop_pc']==b['stop_pc'] and a['a7']==b['a7'] and a['checkpoints']==b['checkpoints'],a['label']
    full_steps=full['steps']
    # representative fresh frames from the recorded chain outputs (declared state = real chain output)
    n_in=len(chain_spec['steps']);reps=[]
    def rep(label,after_frame,count):
        """fresh CPU from the recorded output of input frame `after_frame` (0 = the open final output); steps identical to chain frames after_frame+1.."""
        src=end if after_frame==0 else fc.step_end(full_split,n_open_end+after_frame-1)
        spec=cc.fresh_spec(connected,src,'input chain frame %d output'%after_frame if after_frame else open_end_label,label,chain_spec['steps'][after_frame:after_frame+count],'fresh-frame',
            'fresh CPU started from the recorded real output of input frame %d; steps are identical to chain input frames %d..%d (declared changes unchanged)'%(after_frame,after_frame+1,after_frame+count),chain_offset=n_open_end+after_frame)
        reps.append(spec)
    rep('fresh-input-frame-001',0,1);rep('fresh-input-frame-002',1,1);rep('fresh-input-frame-003-to-005',2,3);rep('fresh-input-frame-150',149,1);rep('fresh-input-frame-299',298,1)
    rep('fresh-input-frame-300-e3-close',299,1);rep('fresh-input-frame-301-a662',n_in-1,1);rep('fresh-input-frames-299-to-301',298,3)
    all_specs=[full,chain_spec]+reps+[s for s in specs if s is not chain_spec]
    cache={full['label']:(full_split,full_control)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;model_checks=[];input_frames={}
    for number,spec in enumerate(all_specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if spec.get('chain_offset') is not None:compared_total+=cc.compare_with_chain(spec,split,full_split)
        if spec['label'] in models and spec.get('guard') is None:
            model_checks.append(check_input_model(spec,models[spec['label']],split,control))
        if spec['label']=='chain-full-bios-resume-to-input':
            input_frames[spec['label']]=frame_summary([p for p in split if p['step']>=n_open_end],[p for p in control if p['step']>=n_open_end],full_steps)
        elif spec.get('guard') is None and spec['group']!='chain':
            input_frames[spec['label']]=frame_summary(split,control,spec['steps'])
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=store('c%03d_split'%number,split),continuous_control=store('c%03d_control'%number,control),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=bool(spec.get('chain_offset') is not None))
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s'%(number+1,len(all_specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else ''),flush=True)
        cache.pop(spec['label'],None)
    instructions=[]
    for lo,hi in INPUT_RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,input_ranges=INPUT_RANGES,instructions=instructions,boundary_stop_pcs=STOP_PCS,hook_stop_pcs=sorted(HOOK_STOPS),block_starts=BLOCKS,input_block_starts=INPUT_BLOCKS,
        stop_rules={hex(k):v['how'] for k,v in op.BOUNDARY_RULES.items() if k in (A662,BD26)},input_bytes={hex(lo):program[lo:hi].hex() for lo,hi in INPUT_RANGES}),indent=2)+'\n').encode()
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
    chain_rows=input_frames['chain-full-bios-resume-to-input']
    countdown=dict(frames=len(chain_rows),w7e_start=0x12c,w7e_after_frame_1=chain_rows[0]['child_7e_after'],w7e_after_each_frame=[r['child_7e_after'] for r in chain_rows],
        first_frame_with_7e_zero=next(r['step']-n_open_end+1 for r in chain_rows if r['child_7e_after']==0),b80_after_each_frame_changes=[(r['step']-n_open_end+1,r['b80_after']) for i,r in enumerate(chain_rows) if i==0 or r['b80_after']!=chain_rows[i-1]['b80_after']],
        e5_changes=[(r['step']-n_open_end+1,r['e5_after']) for i,r in enumerate(chain_rows) if i==0 or r['e5_after']!=chain_rows[i-1]['e5_after']],final_stop_pc=chain_rows[-1]['outgoing_pc'],
        sound_calls_by_frame=[(r['step']-n_open_end+1,[c['d0_w'] for c in r['sound_calls']]) for r in chain_rows if r['sound_calls']])
    condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards]
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,fade_card_crosscheck=cross,card_child_crosscheck=cross_child,card_menu_push_crosscheck=cross_push,card_menu_open_crosscheck=cross_open,
        child_address=hex(end['outgoing']['a6']),child_frames=cc.child_frame_summary(full_split,end['outgoing']['a6'],full_steps[:n_child]),c266_frame_evidence=cc.c266_evidence(full_split),variant_child_layouts=[],guard_reports=guard_reports,
        bank_reads_by_condition=[],bank_descriptor_search=[],new_ranges=INPUT_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha),contract_model_checks=model_checks,input_frames=input_frames,open_frames={k:input_frames[k] for k in ('chain-full-bios-resume-to-input','connected-open-end-to-close')},countdown=countdown,contract_discrepancies=DISCREPANCIES,condition_table=condition_table,
        covered_PCs=sorted(coverage),block_starts=BLOCKS,input_block_starts=INPUT_BLOCKS,boundary_stop_pcs=STOP_PCS,hook_stop_pcs=sorted(HOOK_STOPS),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        declared_fixture_values=dict(p1_104cba=0,p2_104cc0=0,card_10fdb6=1,card_10fdb7=0,note='chain: written once in input frame 1 (and re-declared unchanged every frame); fresh conditions declare their values in the step record'),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; frames after the first are declared PC=2ab8 re-entries only (parent/other objects omitted); the open unit output is re-derived natively (and compared with the open observer report when present).',
            'Input bytes 104cba/104cc0 and card bytes 10fdb6/10fdb7 are declared host RAM writes (fixtures); the original input routine and the BIOS meaning of 10fdb6/10fdb7 are not observed or claimed.',
            'Boundary stops (a662, bd26, descriptor hook targets of JSR (A3) at a440 that are not bf2c) are never executed and are not executable ranges: each is accepted only directly after the transferring instruction. a662 close animation, the bd26 BIOS card save and 9f36/a71a (reachable only through bd26) are not observed.',
            'Split checkpoints are the first hit of each contract block start (open unit blocks plus the 60 input blocks; execution order, entry PC excluded); loop re-visits are not split again. The continuous run is the control.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path only.',
            'Sound queue: 3af8 calls are reported with D0.W and the RAM writes of the call (instruction-level events of the calling range 3af8..., not an audio output); 100012=%02x so 3af8 takes the early path recorded per call.'%u8(end['ram_after'],0x100012),
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion; direct entries at internal PCs (a42c) have no native guard (API-level rejection).'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
