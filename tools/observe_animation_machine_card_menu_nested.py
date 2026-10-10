"""Unpatched card menu result sub-menu frames and nested return (a5ea -> input frames -> a662 close -> a698 nested return -> a6da redraw -> parent close -> c2c8/2a00) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the card menu save, close, input
and open observers (observe_animation_machine_card_menu_save / _close / _input / _open and through them the push / card child / fade-card observers): the
BIOS-resume chain, the card child, the push and open units, the input frame 1, the YES selection with the three BIOS boundary stops (declared resumes) and the
result menu push are re-derived in one persistent CPU run up to the save unit's SAVE OK output (2ac2, -e5=1, -f2=107eee, -ee=107efe).  That real output is
continued by declared PC=2ab8 frame re-entries (A6 = card child, (A6) = c2ba):
  the result menu opening frames (a348 growth, +c<<6 per frame), the a5ea frame (first callback item bf94: D0=6 -> 7e(A6)=1e, D0=0 -> sound 1a6c), the 30 input frames
  (bf2c countdown, both menu records visited by the a370 loop), the frame in which 7e reaches 0 (e=3 -> bf94 D0=3 -> 80(A6)=ff, a70a sound 1a5b, -e5=2), the result menu
  close frames (a662 -> a2be shrink 6(A2)<<6 = 0040 per frame), the frame that finds BYTE 4(A2)=0 (a67a -> 9e94, -f2 += 10 -> 107efe < 107f0e -> a690 BCS a698), the
  a698 nested return (callbacks D0=7 and D0=0 on the parent's cursor item, sound 1a6c) and the a6da redraw of the parent record, the parent frame (bf2c with 80(A6)<>0 -> a70a),
  the parent close frames, c2c8 fade / 7e=14 timer, the c2e8 child cleanup (2a00 with the declared cleanup fixture 1d/6c/104ca4), and the parent re-entry (declared A6 = parent) -> 480ac ->
  62<>0 -> 2a00 -> 2ac2.  The NO SAVE branch (c232) starts from the recorded BIOS stop #3 output with the declared answer BYTE 10fdc6=01.
Host changes (all declared in the step record): PC=2ab8 re-entries, the BIOS resumes of the save chain (PC = JSR return, A7 += 4, BYTE 10fdc6), the input BYTE fixtures
104cba/104cc0 = 00 at the first nested frame (the previous select edge BYTE from the save chain is not an input of the result menu), A6 = parent at the parent re-entry (a register
change at a step boundary, never inside an instruction), the cleanup fixture of the object that 2a00 releases (1d(A6)=0, 6c(A6)=ff, LONG 104ca4 = dispatcher base A7),
and RAM fixtures of the fresh conditions (descriptor copies, extra records, -f2/-ee, initial registers).  Nothing is injected after execution begins.
No SR reads, ROM patches, stubs, register injection after execution begins, stack masking or expected-register injection.
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
import observe_animation_machine_card_menu_save as sv
import observe_animation_machine_card_menu_close as cl
import observe_animation_machine_card_menu_input as inp
import observe_animation_machine_card_menu_open as op
import observe_animation_machine_card_menu as menu
import observe_animation_machine_card_child as cc
import observe_animation_machine_fade_card as fc
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_menu_nested_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-nested-contract.md'
CONTRACT_SHA='1688616ba2f0ea744c0e37505c208bd2d9f0b8ba1ad066b21d1e65384fdbd27f'
ROM_SHA=op.ROM_SHA
sha=fc.sha
u32=cc.u32
u8,u16=op.u8,op.u16
DISPATCH=0x2ac2
A2R=op.A2                      # record 107efe: the parent menu (YES/NO question) record
TOPREC=0x107eee                # record of the result menu
F2,EE,E5,E6=0x107f0e,0x107f12,op.E5,inp.E6
IN1,IN2,CD6,CD7=inp.IN1,inp.IN2,inp.CD6,inp.CD7
BASE=cl.BASE
STACK_END=0x107f0e             # -f2 of an empty stack
YES,NO=inp.YES,inp.NO
CB_OPEN,CB_TIMER,CB_PARENT,CB_DEAD=cl.CB_OPEN,cl.CB_TIMER,cl.CB_PARENT,cl.CB_DEAD
X=sv.X                         # declared initial A7 of direct entries (return LONG 2ac2 stored there)
DESC_RAM=op.DESC               # declared RAM copy of a descriptor
wr=fc.ram_write
reentry=op.reentry

# ----------------------------------------------------------------------------------
# Ranges: the save observer's executable set + the close unit's ranges + exactly the contract's new range a698..a70a
# ----------------------------------------------------------------------------------
NESTED_RANGES=((0xa698,0xa70a),)
RANGES=tuple(dict.fromkeys(tuple(sv.RANGES)+tuple(cl.CLOSE_RANGES)+NESTED_RANGES))
NESTED_BLOCK_TEXT='a698 a6b2 a6bc a6ce a6d6 a6da a6ea a6f0 a6f8 a6fc a706'
NESTED_BLOCKS=tuple(int(x,16) for x in NESTED_BLOCK_TEXT.split())
assert len(NESTED_BLOCKS)==len(set(NESTED_BLOCKS))==11
BLOCKS=tuple(sorted(set(sv.BLOCKS)|set(cl.CLOSE_BLOCKS)|set(cl.EXISTING_BLOCKS)|set(NESTED_BLOCKS)))
BLOCK_SET=frozenset(BLOCKS)
NESTED_BOUNDARIES=NESTED_BLOCKS+(0x9b3e,0x9b58,0x9e1a,0xa5ea,0xa690,0xa67a,0xa67e,0xc2c0)
BOUNDARIES=tuple(dict.fromkeys(tuple(sv.BOUNDARIES)+tuple(cl.BOUNDARIES)+NESTED_BOUNDARIES))
KEY_PCS=tuple(dict.fromkeys(tuple(sv.KEY_PCS)+tuple(cl.KEY_PCS)+NESTED_BOUNDARIES))
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
op.PHASE_LIMIT=6000
PORT_REGIONS=fc.PORT_REGIONS
DISCREPANCIES=[]
CHECK_ROWS=[]
POOL={}


# ----------------------------------------------------------------------------------
# Storage (same rows/artifact names as the save observer; identical payloads are hard-linked)
# ----------------------------------------------------------------------------------
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


def with_checkpoints(program,spec,first=0):
    """First hit of each contract block start per step (entry PC excluded), same rule as the save / close observers."""
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


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    sv.annotate(program,split);sv.annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Independent model of the contract (python, from the contract text and the ROM bytes quoted there / read from the ROM; not the C++).
# It works on a copy of the 64KiB RAM image (reads below 100000 come from the program image) and models the effects the contract specifies:
# the a698 nested return (callbacks, A2 push/pop compare, a6da loop order), the a5ea frame, the opening growth, the input frames (inp.model_frame, the input unit's model)
# and the close frames (cl.a2be / cl.e94 / cl.fade / cl.timer / cl.cleanup, the close unit's model).  9b58 / 9d3a / a018 tile drawing, 8c16 internals and the 2782 reset are
# executed natively and are compared only through their counts / ports (not modelled byte by byte).
# ----------------------------------------------------------------------------------
Unsupported=cl.Unsupported
Mem=cl.Mem


def rec_bytes(M,a):return bytes(M.u8(a+k) for k in range(16))


def new_out(a6):
    out=cl.new_out(a6)
    out.update(sounds=[],draws=[],calls=[],b9b58=0,e1a=0,a3b4=[],a698=0,kind=None,tag=None,sp_check=[],counts_calls=True)
    return out


def sound(out,d0):out['sounds'].append(d0)


def item_cb_addr(M,rec):
    """9b26: A3 = LONG (A2) + 0x10 + 8(A2)*0xa (MULU.W, ADDA.W sign-extended)."""
    off=(M.u8(rec+8)*10)&0xffff
    if off>=0x8000:off-=0x10000
    return (M.u32(rec)+0x10+off)&0xffffffff


def item_cb(M,rec):return M.u32(item_cb_addr(M,rec)+4)


def call_cb(M,child,d0,out):
    """9b3e: D0.W saved; A2 = -ee; callback of the item 8(A2) with D0 restored (nothing when 4(A3) = 0)."""
    rec=M.u32(EE);cb=item_cb(M,rec)
    out['calls'].append(dict(d0=d0,record=rec,callback=cb))
    if cb==0:return
    run_cb(M,child,cb,d0,out)


def run_cb(M,child,cb,d0,out):
    if cb in (YES,NO):
        if d0==0:sound(out,0x1a6c)                                # a73e: D0.W == 0 -> 3af8 1a6c
        if cb==NO:
            if d0==6:M.w16(child+0x7e,0x1e)
            elif d0==3:M.w8(child+0x80,0xff);sound(out,0x1a5b);M.w8(E5,2)
        else:
            if d0 in (3,6):raise Unsupported('YES callback event %d'%d0)
    elif cb==0x9ff4:M.w8(M.u32(EE)+0xe,d0&0xff)
    elif cb==0x9fc4:M.w8(M.u32(EE)+0xd,d0&0xff)
    elif cb==0xa1ee:M.w8(E5,2)
    elif cb==0xa67e:
        M.w32(F2,(M.u32(F2)+0x10)&0xffffffff);a2=M.u32(F2)
        if a2<STACK_END:a698(M,child,out)                         # BCS a698 (recursion)
    else:raise Unsupported('callback %x'%cb)


def e1a_effect(M,child,a2,out):
    """9e1a (-ee = A2): nothing when BYTE 4(A2) = 0; else for D0 = 0 .. 6(A2)-1: 8(A2) <- D0, 9d3a (the item row is drawn and the callback gets D0=5 when 8(A2)+1 < BYTE 4(A2)), D0 = 8(A2)+1."""
    if M.u8(a2+4)==0:return
    d0=0
    while d0<M.u8(a2+6):
        M.w8(a2+8,d0)
        if ((1+M.u8(a2+8))&0xff)<M.u8(a2+4):call_cb(M,child,5,out)
        d0=(M.u8(a2+8)+1)&0xff


def a6da(M,child,a2,out):
    """a6da: push A2; A2 = 107efe; loop while A2 >= pushed (unsigned, CMPA.L (A7),A2 / BCS): -ee <- A2, 9b58, 9e1a, A2 = -ee - 10."""
    pushed=a2&0xffffffff;a=(STACK_END-0x10)&0xffffffff
    while a>=pushed:
        M.w32(EE,a);out['draws'].append(a);out['b9b58']+=1;out['e1a']+=1;e1a_effect(M,child,a,out)
        a=(M.u32(EE)-0x10)&0xffffffff
    return 0


def a698(M,child,out,a2=None):
    """a698 (new range): BYTE 0 -> -e5; -ee <- A2; 8(A2) <- 7(A2); D0.W=7 callback (A2 pushed); pop; A2 == -f2 -> a6bc: -ee <- A2, 8 <- 7, D0.W=0 callback; a6ce A2 = -ee; a6da."""
    if a2 is None:a2=M.u32(F2)
    out['a698']+=1
    M.w8(E5,0);M.w32(EE,a2);M.w8(a2+8,M.u8(a2+7))
    call_cb(M,child,7,out)
    popped=a2
    if popped==M.u32(F2):
        M.w32(EE,popped);M.w8(popped+8,M.u8(popped+7))
        call_cb(M,child,0,out)
    a2=M.u32(EE);out['a2_final']=a2
    a6da(M,child,a2,out)
    out['pc']=DISPATCH


def a6b2_entry(M,child,out,popped):
    """Direct entry a6b2 with the declared stack LONG `popped` (the A2 that a698 would have pushed): a6b2 pop; a6b4 compare with -f2; a6ce; a6da."""
    if popped==M.u32(F2):
        M.w32(EE,popped);M.w8(popped+8,M.u8(popped+7))
        call_cb(M,child,0,out)
    out['a2_final']=M.u32(EE)
    a6da(M,child,M.u32(EE),out)


def items_of(M,rec):
    d=M.u32(rec);items=[];a=d+0x10
    while M.u32(a)!=0xffffffff:
        items.append((M.u32(a)==0xfffffffe,M.u32(a+4)));a+=10
    return items


def input_frame(M,child,out,rec):
    """inp.model_frame (the input unit's model) on the record `rec` (e5 == 0); fields are written back to the RAM copy."""
    S=dict(c4=M.u8(rec+4),c5=M.u8(rec+5),c=M.u8(rec+0xc),count=M.u8(rec+6),c7=M.u8(rec+7),c8=M.u8(rec+8),e=M.u8(rec+0xe),f=M.u8(rec+0xf),d=M.u8(rec+0xd),
        e6=M.u8(E6),e5=M.u8(E5),w7e=M.u16(child+0x7e),b80=M.u8(child+0x80),items=items_of(M,rec),hook=M.u32(M.u32(rec)+6)!=0)
    hook80=S['b80']!=0
    oc=inp.model_frame(S,M.u8(IN1),M.u8(IN2),M.u8(CD6),M.u8(CD7))
    if oc['stop']:raise Unsupported('input frame stop %s'%oc['stop'])
    for k,a,size in (('c4',rec+4,1),('c5',rec+5,1),('c7',rec+7,1),('c8',rec+8,1),('e',rec+0xe,1),('f',rec+0xf,1),('d',rec+0xd,1),('e6',E6,1),('e5',E5,1),('w7e',child+0x7e,2),('b80',child+0x80,1)):
        old=M.u16(a) if size==2 else M.u8(a)
        if old!=S[k]:(M.w16 if size==2 else M.w8)(a,S[k])
    out['sounds']+=oc['sounds']
    if oc['regrow']:out['b9b58']+=1
    if oc['redraw']:out['e1a']+=1;e1a_effect(M,child,rec,out)
    out['kind']='grow' if oc['regrow'] else (('hook80' if hook80 else 'select') if S['e5']==2 and oc['sounds'] and 0x1a5b in oc['sounds'] else 'input')
    out['model_event']=oc['e6_event']


def a5ea_frame(M,child,out):
    """a5ea (4(A2) >= c(A2)): -e5 <- 0; 8 <- 7; skip items without callback (a606..a61a); 9b58 + 9e1a; TRAP when the first item is the terminator; 8 <- 7 callback D0=6; 8 <- 7 callback D0=0."""
    a2=M.u32(EE)
    M.w8(E5,0);M.w8(a2+8,M.u8(a2+7))
    for _ in range(0x200):
        if M.u32(item_cb_addr(M,a2)+4)!=0:break
        n=(M.u8(a2+7)+1)&0xff
        if n>=M.u8(a2+6):n=0
        M.w8(a2+7,n);M.w8(a2+8,n)
    else:raise Unsupported('no callback item')
    out['b9b58']+=1;out['e1a']+=1;e1a_effect(M,child,a2,out)
    if M.u32(M.u32(a2)+0x10)==0xffffffff:raise Unsupported('TRAP #15')
    M.w8(a2+8,M.u8(a2+7));call_cb(M,child,6,out)
    a2=M.u32(EE);M.w8(a2+8,M.u8(a2+7));call_cb(M,child,0,out)
    out['kind']='a5ea'


def grow(M,a2,out):
    w=M.u16(a2+4);c=M.u8(a2+0xc);w=(w+((c<<6)&0xffff))&0xffff;lim=(c<<8)&0xffff
    if lim<w:w=lim
    M.w16(a2+4,w);out['b9b58']+=1


def a370_loop2(M,child,out):
    """a370: records from 107efe down to -f2: -ee <- A2; lower records (A2 <> -f2) with f bit0 and BYTE 4(A2) <> 0 shrink (a3a8 BSR a2be); BYTE 4 = 0 afterwards -> a3b4 BSR a6da; hook a(A3) must be 0."""
    a2=(STACK_END-0x10)&0xffffffff;f2=M.u32(F2)
    while a2>=f2:
        M.w32(EE,a2)
        if a2!=f2 and (M.u8(a2+0xf)&1) and M.u8(a2+4)!=0:
            cl.a2be(M,a2,out);out['b9b58']+=1
            if M.u8(a2+4)==0:
                a6da(M,child,a2,out);out['a3b4'].append(a2)
        a3=M.u32(a2)
        if M.u32(a3+0xa)!=0:raise Unsupported('descriptor hook at a3c6')
        a2=(a2-0x10)&0xffffffff


def child_frame2(M,child,out):
    cb=M.u32(child)
    if cb==CB_OPEN:
        a370_loop2(M,child,out)
        a2=M.u32(F2)
        if a2>=STACK_END:                                   # a3d4 BCS not taken: D0 = -1 -> c2c0 BNE c2c8 (fade)
            out['kind']='empty-stack'
            cl.fade(M,child,out);cl.timer(M,child,out);out['tag']='empty-stack'
            return
        M.w32(EE,a2)
        e5=M.u8(E5)
        if e5==1:
            if M.u8(a2+4)<M.u8(a2+0xc):grow(M,a2,out);out['kind']='grow';out['tag']='grow'
            else:a5ea_frame(M,child,out);out['tag']='a5ea'
        elif e5==0:
            input_frame(M,child,out,a2);out['tag']=out['kind']
        elif e5==2:
            if M.u8(a2+4)!=0:
                cl.a2be(M,a2,out);out['b9b58']+=1;out['kind']='shrink'
            else:
                cl.e94(M,out);out['kind']='zero'
                M.w32(F2,(M.u32(F2)+0x10)&0xffffffff)
                if M.u32(F2)<STACK_END:
                    a698(M,child,out);out['kind']='nested-a698'
                else:
                    cl.fade(M,child,out);cl.timer(M,child,out);out['kind']='zero' if out['kind']=='zero' else out['kind']
            out['tag']=out['kind']
        else:raise Unsupported('-e5 %d'%e5)
    elif cb==CB_TIMER:
        out['kind']=None;cl.timer(M,child,out);out['tag']=out['kind'] or 'timer'
    else:raise Unsupported('callback %x'%cb)


def parent_frame2(M,parent,out):
    cl.parent_frame(M,parent,out);out['tag']='parent-2a00' if out['cleanup'] is not None else 'parent-480ac'


def model_run(M,phase,child,parent,a6):
    out=new_out(a6)
    if phase=='parent':parent_frame2(M,parent,out)
    else:child_frame2(M,child,out)
    return out


# ----------------------------------------------------------------------------------
# Native frame evidence
# ----------------------------------------------------------------------------------
def hexb(ram,address,n):return bytes(ram[(address+i)&0xffff] for i in range(n)).hex()


def sound_calls(program,p):return sv.sound_calls2(program,p)


def native_frame(program,p,watch_records):
    """Facts of one continuous phase: sound D0 words, a6f0 A2 sequence, 9b3e D0 sequence (WORD) / record (-ee), counts of the drawing calls."""
    pcs=p['pcs'];bs=p['boundaries']
    calls=[dict(d0=b['registers']['d0']&0xffff) for b in bs if b['pc']==0x9b3e]
    return dict(sounds=[c['d0_w'] for c in sound_calls(program,p)],draws=[b['registers']['a2'] for b in bs if b['pc']==0xa6f0],calls=[c['d0'] for c in calls],
        b9b58=pcs.count(0x9b58),e1a=pcs.count(0x9e1a),a698=pcs.count(0xa698),pc=p['outgoing']['pc'],a6=p['outgoing']['a6'])


def record(label,step,kind,exp,got,**extra):
    row=dict(label=label,step=step,kind=kind,model=exp,native=got,equal=exp==got,**extra)
    if not row['equal']:DISCREPANCIES.append(dict(label=label,step=step,kind=kind,model=exp,native=got))
    CHECK_ROWS.append(row);return row


# ----------------------------------------------------------------------------------
# Model-driven frame plan (cl.Close.make pattern): declared changes per frame, the stop and A7 expectation, and the expected outcome
# ----------------------------------------------------------------------------------
def input_zero(why='the result menu has no input edge: the select edge BYTE of the save chain is cleared'):return inp.input_writes(0,0,why)


def plan_frames(program,base,child,parent,base_a7,decl=None,until='end',max_frames=120,label='nested',phase='child',a6=None):
    """Frames are declared PC=2ab8 re-entries; `decl` maps a frame index to declared changes (RAM writes also applied to the model).  until: 'end' (child 2a00 and parent 2a00 frames),
    'cleanup' (child 2a00 frame), 'a698' (the frame that executes a698), or an int (frame count)."""
    decl=decl or {};M=Mem(base['ram_after'],program);steps=[];outcomes=[];a6=base['outgoing']['a6'] if a6 is None else a6
    n_frames=until if isinstance(until,int) else max_frames
    for i in range(n_frames):
        ch=[reentry()]
        if i in decl:ch+=list(decl[i]);M.r=op.apply_writes(M.r,[c for c in decl[i] if c['kind']=='ram'])
        if phase=='parent' and a6!=parent:
            ch.append(cl.reg_set('a6',parent,'declared parent re-entry: A6 = parent object %x (A6 left by 299c is %x)'%(parent,a6)));a6=parent
        probe=model_run(M.copy(),phase,child,parent,a6)
        if probe['cleanup'] is not None:
            fx=cl.cleanup_fixture(probe['cleanup'],base_a7,M.u32(BASE)!=base_a7);ch+=fx;M.r=op.apply_writes(M.r,fx)
        M.touched=set()
        oc=model_run(M,phase,child,parent,a6);oc['frame']=i+1;oc['phase']=phase
        stop=DISPATCH;a7=('entry',0)
        if oc['cleanup'] is not None:a7=('mem32',BASE)
        watch=set(M.touched)
        recs={A2R,TOPREC,(M.u32(F2)-0x10)&0xffffffff,M.u32(F2),M.u32(EE)}
        for r in list(recs):recs.add((r+0x10)&0xffffffff)
        for r in recs:watch.update((r+k)&0xffff for k in range(0x10))
        for ad,n in ((EE,4),(F2,4),(E5,1),(E6,1),(child,4),(child+0x7e,2),(child+0x80,1),(parent+0x62,1),(child+0x62,1),(cl.HEAD,4),(cl.CNT,2),(BASE,4),(cl.W238,6),(cl.B22C,1)):
            watch.update((ad+k)&0xffff for k in range(n))
        oc['ram_exp']={a:M.r[a] for a in sorted(watch)};oc['touched']=sorted(M.touched)
        a6=oc['a6']
        outcomes.append(oc);steps.append(dict(label='%s-f%03d'%(label,i+1),changes=ch,stop_pc=stop,checkpoints=[],a7=a7))
        if until=='a698' and oc['a698']:break
        if oc['cleanup'] is not None:
            if phase=='child' and until=='end':phase='parent';continue
            if until in ('end','cleanup'):break
        if phase=='parent':break
    return steps,outcomes,M


def check_frames(program,spec,outcomes,control,first_step=0,kind_label='nested'):
    """Native control phases (steps first_step ..) against the model outcomes."""
    res=dict(label=spec['label'],kind=kind_label,frames=[]);ok=True;resets=[]
    for i,oc in enumerate(outcomes):
        resets+=oc['resets']
        ps=[p for p in control if p['step']==first_step+i];assert len(ps)==1,(spec['label'],i);p=ps[0];ram=p['ram_after'];o=p['outgoing']
        nf=native_frame(program,p,None);np_=cl.native_ports(p)
        exp=dict(pc=oc['pc'],a6=oc['a6'],sounds=oc['sounds'],draws=oc['draws'],b9b58=oc['b9b58'],e1a=oc['e1a'],a698=oc['a698'],
            clear_ports=oc['clear_ports'],e94_ports=oc['e94_ports'],watchdog=oc['watchdog'],covered=oc['covered'],open_cells=len(oc['clear_ports']))
        got=dict(pc=o['pc'],a6=o['a6'],sounds=nf['sounds'],draws=nf['draws'],b9b58=nf['b9b58'],e1a=nf['e1a'],a698=nf['a698'],
            clear_ports=np_['a32a'],e94_ports=np_['e9eca'],watchdog=np_['watchdog'],covered=np_['a018_covered'],open_cells=np_['a018_open'])
        exact=oc['tag'] in ('a5ea','nested-a698') or (oc['a3b4'] and not oc['sounds'] and oc['tag'] in ('input','grow'))
        if oc['calls'] and exact:
            exp['calls_d0']=[c['d0'] for c in oc['calls']];got['calls_d0']=[c for c in nf['calls']]
        if oc['cleanup'] is not None:
            exp['a7']=oc['a7_base'];got['a7']=o['a7']
        ign={(o_+k)&0xffff for o_ in resets for k in range(0x12,0xc4)}
        bad=[dict(address=hex(0x100000+a),model=v,native=ram[a]) for a,v in oc['ram_exp'].items() if ram[a]!=v and a not in ign]
        if oc['fade_regs'] is not None:
            b=[x for x in p['boundaries'] if x['pc']==0x8c16];exp['fade_regs']=dict(oc['fade_regs'],d3=oc['fade_regs']['d3']&0xff)
            got['fade_regs']=dict(d0=b[0]['registers']['d0'],d1=b[0]['registers']['d1'],d2=b[0]['registers']['d2'],d3=b[0]['registers']['d3']&0xff) if b else None
        equal=(exp==got) and not bad
        row=dict(frame=i+1,step=first_step+i,phase=oc['phase'],kind=oc['kind'],tag=oc['tag'],model=exp,native=got,ram_mismatch=bad,equal=equal,model_calls=oc['calls'],model_a3b4=oc['a3b4'],model_shrinks=oc['shrinks'],
            model_cleanup=oc['cleanup_steps'],model_ram_bytes_compared=len(oc['ram_exp'])-len([a for a in oc['ram_exp'] if a in ign]),unmodelled_reset_bytes_not_compared=[hex(x) for x in resets])
        if not equal:
            ok=False;DISCREPANCIES.append(dict(label=spec['label'],frame=i+1,step=first_step+i,kind=oc['kind'],model=exp,native=got,ram_mismatch=bad[:16]))
        res['frames'].append(row)
    res['equal']=ok
    return res


# ----------------------------------------------------------------------------------
# Frame rows (report): heights, -e5/-f2/-ee, 7e/80, sound queue, ports, a698 / a6da evidence
# ----------------------------------------------------------------------------------
REACHED=dict(a698=0xa698,a6b2=0xa6b2,a6bc=0xa6bc,a6ce=0xa6ce,a6d6=0xa6d6,a6da=0xa6da,a6ea=0xa6ea,a6f0=0xa6f0,a6f8=0xa6f8,a6fc=0xa6fc,a706=0xa706,a5ea=0xa5ea,a662=0xa662,a67a=0xa67a,a690=0xa690,a694=0xa694,
    b9b3e=0x9b3e,b9b58=0x9b58,b9e1a=0x9e1a,a3b4=0xa3b4,a2be=0xa2be,b9e94=0x9e94,c2c8=0xc2c8,b8c16=0x8c16,c2e0=0xc2e0,c2e8=0xc2e8,a2a00=0x2a00,a480ac=0x480ac,a70a=0xa70a,bf2c=0xbf2c,bf94=0xbf94,c1c4=0xc1c4,a73e=0xa73e,a348=0xa348)


def frame_rows(program,split,control,steps,first_step=0,child=None):
    rows=[]
    for index in sorted({p['step'] for p in split}):
        if index<first_step:continue
        ps=[p for p in split if p['step']==index];first,last=ps[0],ps[-1];events=[e for p in ps for e in p['events']]
        cps=[p for p in control if p['step']==index];assert len(cps)==1 and cps[0]['events']==events,(index,)
        c=cps[0];pcs=c['pcs'];ports=op.ports_of(events);rb,ra=first['ram_before'],last['ram_after'];ch=first['incoming']['a6'] if child is None else child
        rows.append(dict(step=index,label=steps[index]['label'],outgoing_pc=hex(last['outgoing']['pc']),outgoing_a6=hex(last['outgoing']['a6']),outgoing_a7=hex(last['outgoing']['a7']),
            split_phases=len(ps),pc_count_continuous=len(pcs),counts=fc.counts(events),
            word4_107eee_before=u16(rb,TOPREC+4),word4_107eee_after=u16(ra,TOPREC+4),word4_107efe_before=u16(rb,A2R+4),word4_107efe_after=u16(ra,A2R+4),
            f2_before=hex(u32(rb,F2)),f2_after=hex(u32(ra,F2)),ee_before=hex(u32(rb,EE)),ee_after=hex(u32(ra,EE)),e5_before=u8(rb,E5),e5_after=u8(ra,E5),e6_after=u8(ra,E6),
            child_callback_before=hex(u32(rb,ch)),child_callback_after=hex(u32(ra,ch)),child_7e_before=u16(rb,ch+0x7e),child_7e_after=u16(ra,ch+0x7e),child_80_before=u8(rb,ch+0x80),child_80_after=u8(ra,ch+0x80),
            record_107eee_before=hexb(rb,TOPREC,16),record_107eee_after=hexb(ra,TOPREC,16),record_107efe_before=hexb(rb,A2R,16),record_107efe_after=hexb(ra,A2R,16),
            ordered_port_writes=len(ports),ordered_ports_sha256=sha(b''.join(struct.pack('>BII',s,a,v) for s,a,v in ports)),
            video_long_writes=sum(1 for s,a,v in ports if a in (0x3c0000,0x3c0004) and s==4),video_word_writes=sum(1 for s,a,v in ports if a in (0x3c0000,0x3c0004) and s==2),
            pvc_writes=sum(1 for s,a,v in ports if a>=0x2ffff0),watchdog_writes=sum(1 for e in events if e['region']=='watchdog'),
            ordered_ports=[dict(size=s,address=hex(a),value=hex(v)) for s,a,v in ports] if len(ports)<=200 else 'sha256 only (%d writes)'%len(ports),
            sound_calls=sv.sound_calls2(program,c),sound_queue_ram_104d82_12_before=hexb(rb,0x104d82,12),sound_queue_ram_104d82_12_after=hexb(ra,0x104d82,12),
            callbacks_9b3e_d0=[b['registers']['d0']&0xffff for b in c['boundaries'] if b['pc']==0x9b3e],a6da_redraw_records=[hex(b['registers']['a2']) for b in c['boundaries'] if b['pc']==0xa6f0],
            call_counts={'9b58':pcs.count(0x9b58),'9e1a':pcs.count(0x9e1a),'a2be':pcs.count(0xa2be),'a6da':pcs.count(0xa6da),'a698':pcs.count(0xa698),'9b3e':pcs.count(0x9b3e),'a370_loop_body_a38a':pcs.count(0xa38a),'a3b4_a6da_entry':pcs.count(0xa3b4)},
            reached={k:pc in pcs for k,pc in REACHED.items()},ram_changed=sv.ranges_of(rb,ra),stop_evidence=last['stop_evidence']))
    return rows


# ----------------------------------------------------------------------------------
# The persistent chain: connected prefix + save unit (SAVE OK) + nested frames (one CPU)
# ----------------------------------------------------------------------------------
def build_chain(program):
    C=sv.build_prefix(program);connected=C['connected'];n_open_end=C['n_open_end']
    K=dict(f1=n_open_end,up=n_open_end+1,sel=n_open_end+2,r1=n_open_end+3,r2=n_open_end+4,r3=n_open_end+5)
    save_steps=C['prefix_steps']+[sv.frame1_step()]+sv.chain_steps(0)
    assert len(save_steps)==K['r3']+1
    prefix_label='fade/card chain step %d (stop c00468)'%fc.LAST_FRAME
    save_spec=cc.fresh_spec(connected,C['endlast'],prefix_label,'chain-save-ok-prefix',save_steps,'chain','fade/card chain, card child, push, open, input frame 1, YES selection with declared BIOS resumes (SAVE OK): the save unit chain')
    save_phases=fc.run_condition(program,save_spec,True);assert save_phases==fc.run_condition(program,save_spec,True)
    ends={p['step']:p for p in save_phases}
    return dict(C=C,connected=connected,K=K,save_steps=save_steps,save_spec=save_spec,ends=ends,endlast=C['endlast'],prefix_label=prefix_label)


# ----------------------------------------------------------------------------------
# Condition construction helpers
# ----------------------------------------------------------------------------------
def desc_copy(program,rom_address,length,patches,record,why):
    """Declared RAM copy of a real ROM descriptor with patched LONGs (offset -> value), and the record's LONG (A2) pointing at the copy."""
    raw=bytearray(program[rom_address:rom_address+length])
    for off,val in patches.items():raw[off:off+4]=val.to_bytes(4,'big')
    return menu.ram_bytes(DESC_RAM,bytes(raw),why)+[wr(record,4,DESC_RAM,'declared LONG (%x) = %x (record -> RAM descriptor copy): %s'%(record,DESC_RAM,why))]


def record_writes(address,data,why):return menu.ram_bytes(address,bytes(data),why)


def direct_step(label,entry,extra,a7_rel):
    return dict(label=label,changes=[sv.direct_pc(entry)]+list(extra),stop_pc=DISPATCH,checkpoints=[],a7=('entry',a7_rel))


class Nest:
    def __init__(self,program,connected,bases,child,parent,base_a7,full_steps,K0):
        self.program=program;self.connected=connected;self.bases=bases;self.child=child;self.parent=parent;self.base_a7=base_a7;self.full_steps=full_steps;self.K0=K0
        self.specs=[];self.checks={};self.meta={}
    def make(self,label,group,prov,base,steps,regs=None,guard=None,check=None,checkpoints=True,meta=None,**extra):
        E,lab=self.bases[base]
        if guard is not None:extra.update(guarded=True,guard=guard)
        spec=cc.fresh_spec(self.connected,E,lab,label,steps,group,'fresh state from the recorded %s; '%lab+prov,regs=regs,**extra)
        if checkpoints:with_checkpoints(self.program,spec)
        self.specs.append(spec)
        if check is not None:self.checks[label]=check
        if meta is not None:self.meta[label]=meta
        return spec
    def frames(self,label,group,prov,base,decl=None,until=2,first_tag=None,**extra):
        E,lab=self.bases[base]
        steps,outcomes,M=plan_frames(self.program,E,self.child,self.parent,self.base_a7,decl=decl,until=until,label=label)
        spec=self.make(label,group,prov,base,steps,check=None,**extra)
        self.checks[label]=lambda program,spec,split,control,o=outcomes:[check_frames(program,spec,o,control)]
        self.meta[label]=dict(outcomes=[dict(frame=o['frame'],tag=o['tag'],kind=o['kind'],pc=o['pc'],sounds=o['sounds'],draws=o['draws'],calls=o['calls'],a3b4=o['a3b4']) for o in outcomes])
        return spec,outcomes
    def chain_steps(self,idx):return copy.deepcopy(self.full_steps[self.K0+idx])


def check_direct(program,spec,control,entry,a2_value,popped=None,callbacks=True):
    """Direct entry at a6da / a6b2 / a698 (internal PC, declared stack and registers): native step against the model of the contract."""
    p=control[0];assert len(control)==1;inc=p['incoming'];o=p['outgoing'];child=inc['a6'];parent=u32(p['ram_before'],child+0xc)
    M=Mem(p['ram_before'],program);out=new_out(child);ra=p['ram_after']
    if entry==0xa6da:
        a6da(M,child,a2_value,out);a2_final=a2_value
    elif entry==0xa6b2:
        a6b2_entry(M,child,out,popped);a2_final=out['a2_final']
    elif entry==0xa698:
        a698(M,child,out,a2=a2_value);a2_final=out['a2_final']
    else:raise AssertionError(hex(entry))
    nf=native_frame(program,p,None)
    stack_pops={0xa6da:4,0xa6b2:8,0xa698:4}[entry]
    exp=dict(pc=DISPATCH,a7=(inc['a7']+stack_pops)&0xffffffff,a2=a2_final,a1=0xa008,sounds=out['sounds'],draws=out['draws'],b9b58=out['b9b58'],e1a=out['e1a'],
        calls_d0=[c['d0'] for c in out['calls']],a698=1 if entry==0xa698 else 0)
    got=dict(pc=o['pc'],a7=o['a7'],a2=o['a2'],a1=o['a1'],sounds=nf['sounds'],draws=nf['draws'],b9b58=nf['b9b58'],e1a=nf['e1a'],calls_d0=nf['calls'],a698=nf['a698'])
    if entry in (0xa698,0xa6b2):
        exp['d0']=0;got['d0']=o['d0']
    watch=set(M.touched)
    for r in (A2R,TOPREC,(TOPREC-0x10)&0xffffffff,(TOPREC-0x20)&0xffffffff):watch.update((r+k)&0xffff for k in range(0x10))
    for ad,n in ((EE,4),(F2,4),(E5,1)):watch.update((ad+k)&0xffff for k in range(n))
    bad=[dict(address=hex(0x100000+a),model=M.r[a],native=ra[a]) for a in sorted(watch) if M.r[a]!=ra[a]]
    equal=exp==got and not bad
    row=dict(frame=1,step=0,phase='direct',kind='direct-%x'%entry,tag='direct',model=exp,native=got,ram_mismatch=bad,equal=equal,model_calls=out['calls'],model_ram_bytes_compared=len(watch))
    if not equal:DISCREPANCIES.append(dict(label=spec['label'],frame=1,kind=row['kind'],model=exp,native=got,ram_mismatch=bad[:16]))
    return [dict(label=spec['label'],kind='nested-direct',frames=[row],equal=equal)]


GUARDS={
    'odd-a2-a698':dict(problem='unsupported_odd_data_access',pc=0x9b2a,address=0x107eff,size=4,access='read'),
    'odd-a7-a698':dict(problem='unsupported_odd_data_access',pc=0xa6ac,address=X+1-4,size=4,access='write',odd_write_restored=True),
    'odd-a7-a6da':dict(problem='unsupported_odd_data_access',pc=0xa6da,address=X+1-4,size=4,access='write',odd_write_restored=True),
    'odd-a7-a6b2':dict(problem='unsupported_odd_data_access',pc=0xa6b2,address=X+1,size=4,access='read'),
    'unsupported-callback':dict(problem='unsupported_code_target',pc=0xe00,target=0xe00),
}


def first_index(outcomes,tag,start=0):return next(i for i,o in enumerate(outcomes) if i>=start and o['tag']==tag)


def build_conditions(N,ends,outcomes,K,B):
    K0=K['r3']+1;P=N.program;child=N.child;parent=N.parent
    # ---- fresh representative copies of the chain frames (identical declared changes and checkpoints; compared with the chain phases)
    reps=[('grow-first',0),('grow-last',first_index(outcomes,'a5ea')-1),('a5ea',first_index(outcomes,'a5ea')),('input-first',first_index(outcomes,'input')),('select-e3',first_index(outcomes,'select')),
        ('shrink-first',first_index(outcomes,'shrink')),('shrink-last',first_index(outcomes,'nested-a698')-1),('a698',first_index(outcomes,'nested-a698')),('parent-hook80',first_index(outcomes,'hook80')),
        ('parent-shrink-first',first_index(outcomes,'shrink',first_index(outcomes,'hook80'))),('parent-zero-c2c8',first_index(outcomes,'zero')),('timer-first',first_index(outcomes,'timer')),
        ('child-cleanup-c2e8',first_index(outcomes,'c2e8')),('parent-cleanup-480ac',first_index(outcomes,'parent-2a00'))]
    for name,idx in reps:
        base=ends[K0+idx-1]
        N.bases['rep-%s'%name]=(base,'chain nested frame %d output (step %d)'%(idx,K0+idx-1) if idx>0 else 'save unit chain output (step %d, SAVE OK, stop 2ac2)'%(K0-1))
        N.make('fresh-nested-%s'%name,'fresh-frame','nested frame %d (%s) replayed on a fresh CPU'%(idx+1,name),'rep-%s'%name,[copy.deepcopy(N.full_steps[K0+idx])],checkpoints=False,chain_offset=K0+idx)
        N.checks['fresh-nested-%s'%name]=lambda program,spec,split,control,o=outcomes[idx]:[check_frames(program,spec,[o],control)]
    idx_a698=first_index(outcomes,'nested-a698')
    N.bases['mid']=(ends[K0+10],'chain nested frame 10 output (step %d, result menu input frame, -e5=0, 7e=0x14)'%(K0+10))
    N.bases['pre_a698']=(ends[K0+idx_a698-1],'chain nested frame %d output (step %d, the result record height word 00c0, -e5=2, the frame before a698)'%(idx_a698,K0+idx_a698-1))
    N.bases['opened']=(ends[K0+first_index(outcomes,'a5ea')],'chain nested a5ea frame output (step %d)'%(K0+first_index(outcomes,'a5ea')))
    N.bases['bios3']=(ends[K['r2']],'chain resume #2 output (step %d, stop c0046e)'%K['r2'])
    ram_mid=ends[K0+10]['ram_after'];rec_mid=bytes((ram_mid[(TOPREC+k)&0xffff]) for k in range(16))
    assert rec_mid[4:6]==bytes([3,0]) and rec_mid[0xe]==0xff,rec_mid.hex()
    def top_closing(rec,w4=0x00c0):
        r=bytearray(rec);r[4]=w4>>8;r[5]=w4&0xff;return bytes(r)
    # ---- NO SAVE branch (c232): recorded BIOS stop #3 output, declared answer BYTE 10fdc6 = 01, then the same nested frames
    resume_no=sv.bios_resume('save-bios3-resume',sv.BE1C,DISPATCH,24,extra=[sv.answer_write(1)],why=' (be1c)')
    Eb,labb=N.bases['bios3']
    spec_r=cc.fresh_spec(N.connected,Eb,labb,'nosave-resume',[resume_no],'connected','resume #3 with the declared answer 01')
    E_no=fc.run_condition(P,spec_r,True)[-1]
    steps_no,outcomes_no,_=plan_frames(P,E_no,child,parent,N.base_a7,decl={0:input_zero()},until='end',label='nosave-nested')
    spec_no=cc.fresh_spec(N.connected,Eb,labb,'connected-bios3-stop-to-no-save-nested',[resume_no]+steps_no,'connected',
        'fresh state from the recorded %s; resume #3 declares BYTE 10fdc6=01 (NO SAVE: result descriptor c232 "NO SAVE.") and the nested frames follow (declared input BYTEs 00 at the first nested frame, cleanup fixtures)'%labb)
    with_checkpoints(P,spec_no,first=1);N.specs.append(spec_no)
    N.checks[spec_no['label']]=lambda program,spec,split,control,o=outcomes_no:[check_frames(program,spec,o,control,first_step=1)]
    N.meta[spec_no['label']]=dict(first_step=1,outcomes=len(outcomes_no),tags=[o['tag'] for o in outcomes_no])
    assert [o['tag'] for o in outcomes_no]==[o['tag'] for o in outcomes]
    # ---- 3-record stack: a698 + a6da loop (2 draws: 107efe, 107eee); 4-record stack (3 draws)
    top=top_closing(rec_mid)
    dec3=[]+record_writes(0x107eee,rec_mid,'declared record at 107eee (copy of the opened result record, height word 0300)')+record_writes(0x107ede,top,'declared top record at 107ede (copy of the opened result record, height word 00c0: BYTE 4 = 0 closes it)')
    dec3+=[wr(F2,4,0x107ede,'declared -f2(A5)=107ede (top of a three record stack)'),wr(EE,4,0x107ede,'declared -ee(A5)=107ede')]
    N.frames('stack3-a698-loop-2','nested-stack','three record stack 107efe/107eee/107ede (top closes): a698 on 107eee, a6da draws 107efe then 107eee; next frame is the 107eee hook frame','pre_a698',decl={0:dec3},until=2)
    dec4=record_writes(0x107eee,rec_mid,'declared record at 107eee (copy of the opened result record)')+record_writes(0x107ede,rec_mid,'declared record at 107ede (copy of the opened result record)')+record_writes(0x107ece,top,'declared top record at 107ece (height word 00c0)')
    dec4+=[wr(F2,4,0x107ece,'declared -f2(A5)=107ece (top of a four record stack)'),wr(EE,4,0x107ece,'declared -ee(A5)=107ece')]
    N.frames('stack4-a698-loop-3','nested-stack','four record stack 107efe/107eee/107ede/107ece (top closes): a698 on 107ede, a6da draws 107efe, 107eee, 107ede (loop 3x)','pre_a698',decl={0:dec4},until=2)
    # ---- a6b4 mismatch: the parent cursor item callback changes -f2 (a67e: ADDI.L #10,-f2 -> 107f0e, no recursion); the D0=0 callback is skipped and a6ce redraws -ee
    c188_cb_off=0x10+2*10+4
    assert u32(P,0xc188+c188_cb_off)==0xc1c4 and P[0xc188+0x3c-4:0xc188+0x3c]==bytes.fromhex('ffffffff')
    def parent_cb(cb,why):return desc_copy(P,0xc188,0x3c,{c188_cb_off:cb},A2R,why)
    N.frames('a6b4-mismatch-callback-a67e','nested-callback','parent descriptor copy whose cursor item callback is a67e (ADDI.L #10,-f2(A5); A2 = -f2; CMPA.L #107f0e BCS not taken; MOVEQ -1; RTS): a6b4 compares the popped A2 107efe with -f2 107f0e: BNE a6ce; the D0=0 callback is skipped; next frame: empty stack -> c2c8 fade',
        'pre_a698',decl={0:parent_cb(0xa67e,'parent cursor item callback = a67e')},until=3)
    N.frames('callback-d0-7-effect-9ff4','nested-callback','parent descriptor copy whose cursor item callback is 9ff4 (A2 = -ee; BYTE D0 -> e(A2)): D0=7 sets e(107efe)=7, the D0=0 callback sets e=0, the a6da draw callbacks (D0=5) set e=5',
        'pre_a698',decl={0:parent_cb(0x9ff4,'parent cursor item callback = 9ff4')},until='a698')
    N.frames('callback-d0-7-effect-9fc4','nested-callback','parent descriptor copy whose cursor item callback is 9fc4 (A2 = -ee; BYTE D0 -> d(A2))','pre_a698',decl={0:parent_cb(0x9fc4,'parent cursor item callback = 9fc4')},until='a698')
    N.frames('callback-d0-7-effect-a1ee','nested-callback','parent descriptor copy whose cursor item callback is a1ee (BYTE 2 -> -e5(A5); A2 = -f2): the callbacks and the draw callbacks leave -e5=2; next frames close the parent','pre_a698',decl={0:parent_cb(0xa1ee,'parent cursor item callback = a1ee')},until=3)
    N.frames('callback-d0-7-none','nested-callback','parent descriptor copy whose cursor item callback is 0 (9b3e returns at once): no sound, a6da redraw only','pre_a698',decl={0:parent_cb(0,'parent cursor item callback = 0')},until='a698')
    # ---- a3b4 -> a6da from an a370 frame: a lower record with f bit0 whose BYTE 4(A2) becomes 0 after the a2be shrink
    par_f=ram_mid[(A2R+0xf)&0xffff]
    def shrink_parent(w4,count=None,why=''):
        d=[wr(A2R+0xf,1,par_f|1,'declared f(107efe)=%02x (bit0: redraw/shrink record)'%(par_f|1)),wr(A2R+4,2,w4,'declared WORD 4(107efe)=%04x%s'%(w4,why))]
        if count is not None:d.append(wr(A2R+6,1,count,'declared BYTE 6(107efe)=%d (a2be shrinks 6(A2)<<6)'%count))
        return d
    N.frames('a3b4-parent-shrinks-to-zero','nested-a3b4','parent record f bit0 and WORD 4=0100: a2be shrinks it to 0000, a3b4 BSR a6da with A2=107efe (one zero-height record: no tile drawing)','mid',decl={0:shrink_parent(0x0100)},until=2)
    N.frames('a3b4-parent-shrinks-borrow','nested-a3b4','parent record f bit0, 6(A2)=8 (shrink 0200) and WORD 4=0180: a2be borrows (a2d0), WORD becomes 0000, a3b4 BSR a6da','mid',decl={0:shrink_parent(0x0180,8)},until=2)
    N.frames('a3b4-parent-shrink-not-zero','nested-a3b4','control: parent record f bit0 and WORD 4=0200: shrinks to 0100 (BYTE 4 <> 0): no a3b4 / a6da','mid',decl={0:shrink_parent(0x0200)},until=2)
    # the middle record keeps its real count 6(A2)=1: a2be shrinks by 6(A2)<<6 = 0040, WORD 0100 -> 00c0: BYTE 4 = 0 (TST.B), the WORD is not 0
    N.frames('a3b4-parent-shrinks-to-0080-byte-zero','nested-a3b4','parent record f bit0, 6(A2)=3 (shrink 00c0) and WORD 4=0140: a2be leaves 0080: BYTE 4 = 0 (TST.B) although the WORD is not 0: a3b4 BSR a6da','mid',decl={0:shrink_parent(0x0140,3)},until=2)
    dec_mid=record_writes(0x107ede,rec_mid,'declared top record at 107ede (copy of the opened result record)')+[wr(F2,4,0x107ede,'declared -f2(A5)=107ede (top of a three record stack)'),wr(EE,4,0x107ede,'declared -ee(A5)=107ede'),
        wr(TOPREC+0xf,1,(rec_mid[0xf]|1),'declared f(107eee)=%02x (bit0)'%(rec_mid[0xf]|1)),wr(TOPREC+4,2,0x0100,'declared WORD 4(107eee)=0100')]
    N.frames('a3b4-middle-record-shrinks-2-draws','nested-a3b4','three record stack, the middle record 107eee (f bit0, WORD 0100) shrinks by 0040 to 00c0 (BYTE 4 = 0): a3b4 BSR a6da with A2=107eee: a6da draws 107efe then 107eee (BYTE 4 = 0: nothing drawn)','mid',decl={0:dec_mid},until=2)

    # ---- result menu input frames (declared P1 edge BYTE 104cba, zero again in the next frame): up / down / bit2 / bit3 / bit5 / select / simultaneous bit0+bit4, from the a5ea frame output
    for p1,name in ((0x01,'up'),(0x02,'down'),(0x04,'bit2'),(0x08,'bit3'),(0x20,'bit5'),(0x11,'up+select')):
        N.frames('result-input-p1-%02x-%s'%(p1,name),'nested-input','result menu input frame with declared P1 edge BYTE 104cba=%02x (%s), zero in the next frame'%(p1,name),'opened',
            decl={0:inp.input_writes(p1,0,'result menu input frame: P1 %02x (%s)'%(p1,name)),1:input_zero('edge BYTE cleared again')},until=3)
    N.frames('result-input-p1-10-select-early','nested-input','result menu input frame with declared P1 bit4 (select) in the first input frame: event 3 -> bf94 D0=3 -> 80(A6)=ff, a70a, -e5=2; then the close frames up to the a698 frame (7e is still 1e)','opened',
        decl={0:inp.input_writes(0x10,0,'result menu input frame: P1 10 (select)'),1:input_zero('edge BYTE cleared again')},until='a698')
    return N


def build_direct_conditions(N,ends,outcomes,K):
    P=N.program;K0=K['r3']+1
    ex=[sv.ret_slot()]
    # ---- a6da direct entries: pushed A2 values (unsigned 32-bit CMPA.L (A7),A2 / BCS), records 107efe and 107eee exist in the base
    values=(0x107efe,0x107eff,0x107efd,0x107eef,0x107eee,0x107ee0,0x107f00,0x107f0e,0x7fffffff,0x80000000,0x80107efe,0xffffffff,0xffff0000)
    for v in values:
        steps=[direct_step('direct-a6da',0xa6da,ex,4)]
        N.make('a6da-direct-pushed-%08x'%v,'direct-a6da','declared direct entry PC=a6da (BSR target), declared A2=%08x (pushed value), initial A7=%x with return LONG 2ac2: a6da loops A2 = 107efe, 107eee, .. while A2 >= pushed (unsigned)'%(v,X),
            'mid',steps,regs=dict(a2=v,a7=X),check=lambda program,spec,split,control,v=v:check_direct(program,spec,control,0xa6da,v))
    # ---- a6b2 direct entries: declared stack LONG (the A2 that a698 pushed) vs -f2 = 107eee
    for v in (0x107eee,0x107efe,0x80107eee,0x00117eee,0x00107eef,0x00107fee,0xffffffff,0):
        steps=[direct_step('direct-a6b2',0xa6b2,ex+[wr(X,4,v,'declared stack LONG at A7 (the A2 pushed by a698) = %08x'%v),wr(X+4,4,DISPATCH,'declared return LONG 2ac2 above it')],8)]
        N.make('a6b2-direct-popped-%08x'%v,'direct-a6b2','declared direct entry PC=a6b2 (JSR 9b3e return), declared stack [A2=%08x][2ac2], -f2=107eee: %s'%(v,'equal: a6bc D0=0 callback' if v==0x107eee else 'unequal: BNE a6ce'),
            'mid',steps,regs=dict(a7=X),check=lambda program,spec,split,control,v=v:check_direct(program,spec,control,0xa6b2,None,popped=v))
    # ---- a698 direct entry (control of the natural frame: -f2=107efe after the close; A2=107efe)
    pre=ex+[wr(F2,4,A2R,'declared -f2(A5)=107efe (the state a67e leaves)'),wr(E5,1,2,'declared -e5=2')]
    N.make('a698-direct-natural','direct-a698','declared direct entry PC=a698 with A2=107efe and -f2=107efe (the state after the result menu is removed)','pre_a698',[direct_step('direct-a698',0xa698,pre,4)],regs=dict(a2=A2R,a7=X),
        check=lambda program,spec,split,control:check_direct(program,spec,control,0xa698,A2R))
    # ---- guards
    N.make('guard-odd-A2-a698','guard','declared A2=107eff (odd): a698 BYTE accesses 7(A2)/8(A2) are legal, JSR 9b3e -> 9b26 MOVEA.L (A2),A3 reads an odd LONG','pre_a698',[direct_step('direct-a698',0xa698,pre,4)],regs=dict(a2=0x107eff,a7=X),guard=GUARDS['odd-a2-a698'])
    N.make('guard-odd-A7-a698','guard','declared initial A7=%x (odd): a698 MOVE.L A2,-(A7) pushes an odd LONG'%(X+1),'pre_a698',[direct_step('direct-a698',0xa698,pre,4)],regs=dict(a2=A2R,a7=X+1),guard=GUARDS['odd-a7-a698'])
    N.make('guard-odd-A7-a6da','guard','declared initial A7=%x (odd): a6da MOVE.L A2,-(A7) pushes an odd LONG'%(X+1),'mid',[direct_step('direct-a6da',0xa6da,ex,4)],regs=dict(a2=0x107efe,a7=X+1),guard=GUARDS['odd-a7-a6da'])
    N.make('guard-odd-A7-a6b2','guard','declared initial A7=%x (odd): a6b2 MOVEA.L (A7)+,A2 reads an odd LONG'%(X+1),'mid',[direct_step('direct-a6b2',0xa6b2,ex,8)],regs=dict(a7=X+1),guard=GUARDS['odd-a7-a6b2'])
    N.make('guard-unsupported-callback','guard','parent cursor item callback = 0e00 (outside the executable ranges): JMP (A0) at the end of 9b3e is refused (partial effects of a698 before it are recorded)','pre_a698',
        [dict(label='nested-a698',changes=[reentry()]+desc_copy(P,0xc188,0x3c,{0x10+2*10+4:0xe00},A2R,'parent cursor item callback = 0e00'),stop_pc=DISPATCH,checkpoints=[],a7=('entry',0))],guard=GUARDS['unsupported-callback'])
    return N


# ----------------------------------------------------------------------------------
# Contract table (ROM bytes quoted by the contract) against the ROM; cross-check against the save observer's report
# ----------------------------------------------------------------------------------
def contract_byte_rows(program):
    import re
    rows=[]
    for line in CONTRACT.read_text().splitlines():
        mt_=re.match(r'\|\s*`([0-9a-f]+)\.\.([0-9a-f]+)`[^|]*\|\s*`([0-9a-f]+)`\s*\|',line)
        if not mt_:continue
        lo,hi=int(mt_.group(1),16),int(mt_.group(2),16);quoted=mt_.group(3);rom=program[lo:hi].hex()
        rows.append(dict(range='%x..%x'%(lo,hi),contract_bytes=quoted,rom_bytes=rom,equal=quoted==rom))
        if quoted!=rom:DISCREPANCIES.append(dict(label='contract-bytes',range='%x..%x'%(lo,hi),contract=quoted,rom=rom))
    return rows


SAVE_REPORT=ROOT/'artifacts/animation_machine_card_menu_save_native/observation.json'


def crosscheck_save(full_split,K):
    """Steps f1 .. r3 of the re-derived chain (input frame 1 .. SAVE OK output) against the save observer's report (RAM/PVC after sha256 and outgoing registers of the last phase of each step)."""
    if not SAVE_REPORT.exists():return dict(performed=False,reason='card menu save report not present')
    d=json.loads(SAVE_REPORT.read_text());r=next(x for x in d['results'] if x['label']=='chain-full-bios-resume-to-save')
    last={}
    for q in r['phases']:last[q['step']]=q
    bad=[];rows=0
    for step in range(K['f1'],K['r3']+1):
        mine=fc.step_end(full_split,step);ref=last[step]
        ref_ram=next(v for k,v in ref['artifacts'].items() if k.endswith('_ram_after.bin'));ref_pvc=next(v for k,v in ref['artifacts'].items() if k.endswith('_pvc_after.bin'))
        if not (sha(mine['ram_after'])==ref_ram and sha(mine['pvc_after'])==ref_pvc and mine['outgoing']==ref['outgoing']):bad.append(step)
        rows+=1
    final=last[K['r3']]
    return dict(performed=True,reference_report=str(SAVE_REPORT),reference_report_sha256=sha(SAVE_REPORT.read_bytes()),reference_tool_sha256=d['tool_sha256'],condition='chain-full-bios-resume-to-save',steps_compared=rows,first_step=K['f1'],
        final_step=K['r3'],final_label=final['label'],final_ram_after_sha256=next(v for k,v in final['artifacts'].items() if k.endswith('_ram_after.bin')),final_outgoing_pc=hex(final['outgoing']['pc']),mismatching_steps=bad,equal=not bad)


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():old.unlink()
    POOL.clear();DISCREPANCIES.clear();CHECK_ROWS.clear()
    allowed=sv.allowed_pcs(program)
    assert all(pc in allowed for pc in NESTED_BLOCKS),[hex(pc) for pc in NESTED_BLOCKS if pc not in allowed]
    assert 0xa698 in allowed
    contract_rows=contract_byte_rows(program)
    reports=[ROOT/'artifacts/animation_machine_fade_card_native/observation.json',ROOT/'artifacts/animation_machine_card_child_native/observation.json',ROOT/'artifacts/animation_machine_card_menu_native/observation.json',inp.OPEN_REPORT,sv.INPUT_REPORT,SAVE_REPORT]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,sv.CONTRACT,inp.CONTRACT,op.CONTRACT,op.PUSH_CONTRACT,cl.CONTRACT,ROOT/'docs/analysis/animation-machine-card-child-contract.md',
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
    # ---- chain: connected prefix + save unit (one persistent CPU) + nested frames
    B=build_chain(program);connected=B['connected'];K=B['K'];K0=K['r3']+1;C=B['C'];n_child=C['n_child'];n_open_end=C['n_open_end']
    E=B['ends'][K['r3']];assert E['outgoing']['pc']==DISPATCH and u32(E['ram_after'],TOPREC)==0xc214
    child=E['outgoing']['a6'];parent=u32(E['ram_after'],child+0xc);base_a7=E['outgoing']['a7']
    assert u8(E['ram_after'],E5)==1 and u32(E['ram_after'],F2)==TOPREC and u32(E['ram_after'],EE)==A2R
    steps,outcomes,_=plan_frames(program,E,child,parent,base_a7,decl={0:input_zero()},until='end',label='nested')
    tags=[o['tag'] for o in outcomes]
    full_steps=B['save_steps']+steps
    full=cc.fresh_spec(connected,B['endlast'],B['prefix_label'],'chain-save-ok-to-nested-removal',full_steps,'chain',
        'fade/card native chain output at c00468; declared BIOS return and 28ae fixture; card child chain, a29c, a370 and the open unit frames; input frame 1; frame 2 (declared P1 bit0: cursor YES), frame 3 (declared P1 bit4: event 3 -> bd26), declared BIOS resumes '
        '#1/#2/#3 (BYTE 10fdc6=00, SAVE OK) -> result menu push -> 2ac2 (the save unit chain, step %d); then %d declared PC=2ab8 frame re-entries: result menu opening frames, a5ea, 30 input frames, select, close frames, a698 nested return with a6da, parent frames, '
        'c2c8 fade, 7e timer, child cleanup (declared 1d/6c/104ca4 fixture), parent re-entry (declared A6 = parent) -> 2a00 -> 2ac2'%(K['r3'],len(steps)))
    with_checkpoints(program,full,first=K0)
    full_split,full_control=run_spec(program,full)
    ends={p['step']:p for p in full_control}
    assert sha(ends[K['r3']]['ram_after'])==sha(E['ram_after']) and ends[K['r3']]['outgoing']==E['outgoing']
    cross_save=crosscheck_save(full_split,K)
    chain_cross=cl.crosscheck_input(full_split,n_open_end+1,n_open_end)
    cross=cc.crosscheck_fade_card(full_split);cross_child=menu.crosscheck_card_child(full_split,n_child);cross_push=op.crosscheck_push(full_split,n_child+1);cross_open=inp.crosscheck_open(full_split,n_open_end)
    assert cross_save['equal'] and (chain_cross['performed'] is False or chain_cross['equal']),(cross_save,chain_cross)
    assert all(x.get('equal',True) for x in (cross,cross_child,cross_push,cross_open)),(cross,cross_child,cross_push,cross_open)
    for step in range(len(full_steps)):
        q=fc.step_end(full_split,step);e=ends[step];assert sha(q['ram_after'])==sha(e['ram_after']) and sha(q['pvc_after'])==sha(e['pvc_after']) and q['outgoing']==e['outgoing'],step
    N=Nest(program,connected,{'save_end':(E,'save unit chain output (step %d, SAVE OK, -e5=1, -f2=107eee, -ee=107efe, stop 2ac2)'%K['r3'])},child,parent,base_a7,full['steps'],K0)
    build_conditions(N,ends,outcomes,K,B)
    build_direct_conditions(N,ends,outcomes,K)
    specs=N.specs
    all_specs=[full]+specs
    cache={full['label']:(full_split,full_control)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;frames={};model_rows={}
    chain_check=check_frames(program,dict(full,steps=full['steps']),outcomes,full_control,first_step=K0)
    model_rows[full['label']]=[chain_check]
    for number,spec in enumerate(all_specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if spec.get('chain_offset') is not None:compared_total+=cc.compare_with_chain(spec,split,full_split)
        if spec['label'] in N.checks and spec.get('guard') is None:
            model_rows[spec['label']]=N.checks[spec['label']](program,spec,split,control)
        min_step=K0 if spec['label']==full['label'] else 0
        if spec['label']==full['label']:
            frames[spec['label']]=frame_rows(program,[p for p in split if p['step']>=min_step],[p for p in control if p['step']>=min_step],spec['steps'],first_step=min_step,child=child)
        elif spec.get('guard') is None:
            frames[spec['label']]=frame_rows(program,split,control,spec['steps'])
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
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
    for lo,hi in NESTED_RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,nested_ranges=NESTED_RANGES,instructions=instructions,nested_bytes={hex(lo):program[lo:hi].hex() for lo,hi in NESTED_RANGES},contract_byte_rows=contract_rows),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    def aggregate(rows):
        t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
        for r in rows:
            for ph_ in r['phases']:
                for k,v in ph_['counts'].items():t[k]+=v
        return t
    guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard']) for g in guards]
    chain_rows=frames[full['label']];row_by_step={r['step']:r for r in chain_rows}
    milestones={}
    for t in ('grow','a5ea','input','select','shrink','nested-a698','hook80','zero','timer','c2e8','parent-2a00'):
        milestones[t]=[K0+i for i,x in enumerate(tags) if x==t]
    a698_row=row_by_step[K0+tags.index('nested-a698')]
    nested_summary=dict(total_chain_frames_nested=len(steps),first_step=K0,last_step=K0+len(steps)-1,total_chain_steps_with_prefix=len(full_steps),frame_tags=tags,milestone_steps=milestones,
        heights_107eee=[r['word4_107eee_after'] for r in chain_rows],heights_107efe=[r['word4_107efe_after'] for r in chain_rows],e5_after=[r['e5_after'] for r in chain_rows],f2_after=[r['f2_after'] for r in chain_rows],ee_after=[r['ee_after'] for r in chain_rows],
        w7e_after=[r['child_7e_after'] for r in chain_rows],w80_after=[r['child_80_after'] for r in chain_rows],sound_by_step={r['step']:[hex(c['d0_w']) for c in r['sound_calls']] for r in chain_rows if r['sound_calls']},
        port_counts_by_step={r['step']:r['ordered_port_writes'] for r in chain_rows},instructions_by_step={r['step']:r['pc_count_continuous'] for r in chain_rows},
        a698_frame=dict(step=a698_row['step'],callbacks_9b3e_d0=a698_row['callbacks_9b3e_d0'],a6da_redraw_records=a698_row['a6da_redraw_records'],sound_calls=a698_row['sound_calls'],reached=a698_row['reached'],
            f2_before=a698_row['f2_before'],f2_after=a698_row['f2_after'],ee_after=a698_row['ee_after'],e5_after=a698_row['e5_after'],record_107efe_before=a698_row['record_107efe_before'],record_107efe_after=a698_row['record_107efe_after']),
        final_a6=chain_rows[-1]['outgoing_a6'],final_a7=chain_rows[-1]['outgoing_a7'],final_pc=chain_rows[-1]['outgoing_pc'])
    checks_equal=all(r['equal'] for rows_ in model_rows.values() for r in rows_)
    model_checks=[dict(label=lab,kind='nested',frames=[f for r in rows_ for f in r['frames']],equal=all(r['equal'] for r in rows_)) for lab,rows_ in model_rows.items()]
    model_frame_rows=sum(len(m['frames']) for m in model_checks)
    final_state=dict(after_save=dict(step=K['r3'],f2=hex(u32(E['ram_after'],F2)),ee=hex(u32(E['ram_after'],EE)),e5=u8(E['ram_after'],E5),record_107eee=hexb(E['ram_after'],TOPREC,16),record_107efe=hexb(E['ram_after'],A2R,16)),
        final=dict(step=K0+len(steps)-1,**{k:chain_rows[-1][k] for k in ('outgoing_pc','outgoing_a6','outgoing_a7','f2_after','ee_after','e5_after')},
            objects_from_parent=cl.object_list(ends[K0+len(steps)-1]['ram_after'],parent),child_object=cl.object_list(ends[K0+len(steps)-1]['ram_after'],child,1)))
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,fade_card_crosscheck=cross,card_child_crosscheck=cross_child,card_menu_push_crosscheck=cross_push,card_menu_open_crosscheck=cross_open,card_menu_input_crosscheck=chain_cross,card_menu_save_crosscheck=cross_save,
        child_address=hex(child),variant_child_layouts=[],guard_reports=guard_reports,bank_reads_by_condition=[],bank_descriptor_search=[],new_ranges=NESTED_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha),contract_byte_rows=contract_rows,contract_model_checks=model_checks,model_check_frames=model_frame_rows,model_checks_all_equal=checks_equal,nested_frames=frames,nested_summary=nested_summary,final_state=final_state,
        child_frames=cc.child_frame_summary(full_split,child,full['steps'][:n_child]),parent_address=hex(parent),contract_discrepancies=DISCREPANCIES,
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence'],guard=r['phases'][-1]['guard']) for r in results+guards],
        covered_PCs=sorted(coverage),block_starts=BLOCKS,nested_block_starts=NESTED_BLOCKS,existing_block_starts=tuple(sorted(set(BLOCKS)-set(NESTED_BLOCKS))),boundary_stop_pcs=(sv.BIOS1,sv.BIOS3),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; frames after the save unit chain are declared PC=2ab8 re-entries (A6 = card child, parent re-entry A6 = parent); the input BYTEs 104cba/104cc0 = 00 are declared at the first nested frame.',
            'Nested frames follow the persistent save unit chain; the BIOS resumes of the save chain are declared host changes (PC = JSR return, A7 += 4, BYTE 10fdc6); the carry that the BIOS leaves is Unknown and SR is never read; branch decisions are evidenced by the executed PC path only.',
            'The cleanup fixture of 2a00 (1d(A6)=0, 6c(A6)=ff of the released objects, LONG 104ca4 = dispatcher base A7) is a declared host change: the pool slot bytes of the card child and parent are not initialized by the original chain (without it 299c -> 2782 -> c3fa -> 46ef4 reaches TRAP #15).',
            'The tile drawing (9b58 / 9d3a / a018 / 3918), the 8c16 fade internals and the 2782 reset are executed natively and compared through counts / ports / the modelled RAM bytes only; the 9d3a item-row callback D0=5 (9e08) is modelled as a callback call.',
            'Direct entries (a6da, a6b2, a698) are internal PCs with declared stack and registers; the C++ API rejection of internal PCs is not a native guard.',
            'Split checkpoints are the first hit of each block start of the executable set (input, save, close and nested blocks; execution order, entry PC excluded) for the nested frames only; the prefix steps are split-free and verified by the earlier observers\' reports (cross-checks).',
            'Native carry is unobserved (SR never read); the models compare RAM bytes, registers, ports counts/hashes and record fields, not CCR.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],model_frames=model_frame_rows,model_checks_all_equal=checks_equal,discrepancies=len(DISCREPANCIES),
        nested_frames=len(steps),sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
