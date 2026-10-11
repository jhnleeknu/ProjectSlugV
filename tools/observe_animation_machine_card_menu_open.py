"""Unpatched card menu opening frames (a370 -> a5d2/a348/9b58 box growth -> a5ea first full draw and callbacks) native observation.

Native Unicorn M68000 observation of the original ROM, reusing the hardened machinery of the card menu push observer
(observe_animation_machine_card_menu) and, through it, the card child / fade-card observers: the BIOS-resume chain is
re-derived to the a29c stop, a29c is executed natively to the a370 stop (JSR a370 at c2ba, c2c0 above 2ac2 on the stack),
then a370 is executed in the same frame (opening frame 1, stop 2ac2 after c2c0 TST/RTS) and later frames are declared
PC=2ab8 re-entries (A6 = card child, (A6) = c2ba) through the box growth frames to the a5ea frame (cursor search, 9b58,
9e1a full draw with 9d3a/9cd4/9f7c/3918/e84c8->3650, 9b3e callbacks D0=5/6/0: c1c4 YES -> 7e=12c, JMP a216 cursor move;
bf94 NO; a73e D0=0 -> 3af8 sound) -> a65e RTS -> c2c0 -> 2ac2 stop.
Boundary stops (9e94, a2be, a406, a662, a70a, bd26, e84d6, a63c TRAP, c2c8, hook targets) are stops only: each is
accepted only directly after the transferring instruction, never executed.  Boundary conditions are fresh conditions from the recorded a370
stop output with declared host changes (initial registers, RAM fixture writes, PC redirect), each recorded in the step record.
No SR reads, ROM patches, stubs, register injection after execution begins, stack masking or expected-register injection.
This is a native observation, not a C++ comparison.
"""
import copy
import json
import os
from pathlib import Path
import struct
import sys
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_card_menu as menu
import observe_animation_machine_card_child as cc
import observe_animation_machine_fade_card as fc
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_menu_open_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-open-contract.md'
CONTRACT_SHA='1eb6c80ebcbef6a2f8c6488c23342ee4a85dae1c0acbf9037ad3ccb280549c4b'
PUSH_CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-push-contract.md'
ROM_SHA='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
sha=fc.sha
u32=cc.u32
A370,A348,A5D2,A5EA,A61C,A216,B9B58,C2C0,C2C8,DISPATCH=0xa370,0xa348,0xa5d2,0xa5ea,0xa61c,0xa216,0x9b58,0xc2c0,0xc2c8,0x2ac2
A2,E2,F2,EA=0x107efe,0x107f12,0x107f0e,0x107f16     # first menu record (-f2 after the push minus 0x10), -ee(A5), -f2(A5), -ea(A5)
E5=0x107f1b                                         # -e5(A5)
DESC,STRS=menu.DESC,menu.STRS
CARD_CHILD_CB=0xc2ba

# ----------------------------------------------------------------------------------
# Ranges: exactly the contract table (boundary PCs are outside every range), plus the c2c0 TST/BNE/RTS head of the caller return
# ----------------------------------------------------------------------------------
OPEN_RANGES=((0x9b26,0x9b58),(0x9b58,0x9bbc),(0x9bbc,0x9cd4),(0x9cd4,0x9d3a),(0x9d3a,0x9e1a),(0x9e1a,0x9e94),(0x9f7c,0x9fc4),(0xa008,0xa080),(0xa216,0xa280),
    (0xa348,0xa370),(0xa370,0xa3e2),(0xa3e2,0xa406),(0xa5d2,0xa662),(0xa73e,0xa75a),(0xbf94,0xbfbe),(0xc1c4,0xc214),(0xc2c0,0xc2c8),(0x3918,0x392c),(0x3650,0x3670),(0xe84c8,0xe84d6))
RANGES=menu.RANGES+OPEN_RANGES
BLOCK_TEXT='''3650 3918 391a 391e 3926 3928 392a 9b26 9b3e 9b42 9b54 9b56 9b58 9b64 9b66 9b78 9b7a 9b82 9b8a 9b8e 9ba6 9baa 9bbc 9bc0 9bc8 9bcc 9bd0 9be2 9be6 9bea 9bee 9c00 9c08 9c10 9c14 9c26 9c2a 9c32 9c36 9c3a 9c4c 9c50 9c54 9c58 9c6a 9c6e 9c76 9c7a 9c8c 9c90 9c98 9c9c 9ca0 9cb2 9cb6 9cba 9cbe 9cd0 9cd4 9cd8 9cdc 9cee 9cf0 9cf8 9cfc 9d00 9d12 9d16 9d1e 9d22 9d26 9d38 9d3a 9d4a 9d4c 9d86 9d92 9d96 9d9a 9da0 9dae 9db6 9dba 9dc0 9dc4 9dce 9dd6 9dda 9de8 9dea 9df2 9df6 9dfe 9e02 9e08 9e14 9e1a 9e26 9e28 9e34 9e3a 9e5e 9e66 9e6e 9e72 9e78 9e7a 9e82 9e8a 9e92 9f7c 9f84 9f90 9f96 9fac 9fb8 9fbe a008 a00c a010 a016 a018 a03a a040 a04a a058 a066 a06c a076 a216 a21e a22c a236 a238 a23c a242 a246 a252 a258 a262 a26e a278 a348 a350 a36a a36e a370 a380 a388 a396 a3a0 a3a8 a3ac a3b4 a3b8 a3c6 a3c8 a3d0 a3de a3e2 a3f2 a3fa a402 a5d2 a5e2 a5e6 a5ea a5f4 a5fe a606 a614 a616 a61c a624 a628 a63e a64c a65e a73e a74a a754 bf94 bf9a bfa2 bfa8 bfb0 bfbc c1c4 c1ca c1d2 c1de c1e6 c1ee c1f4 c1fe c202 c208 c212 e84c8 e84d0 c2c0 c2c6'''
BLOCKS=tuple(int(x,16) for x in BLOCK_TEXT.split())
BLOCK_SET=frozenset(BLOCKS)
assert len(BLOCKS)==len(BLOCK_SET)==202
BOUNDARY_PCS=(0x9e94,0x9f36,0xa2be,0xa406,0xa662,0xa6da,0xa70a,0xa71a,0xbd26,0xe84d6,0xa63c)   # contract boundaries (a63c TRAP)
STOP_BOUNDARIES=(0x9e94,0xa2be,0xa406,0xa662,0xa70a,0xbd26,0xe84d6,0xa63c,C2C8)       # reachable by a transferring instruction in these conditions
HOOK_STOPS=set()                                                                              # hook targets (JSR (A4) at a3c6), filled while building the conditions
NEW_BOUNDARIES=(0xa370,0xa3b8,0xa3c6,0xa3d0,0xa3e2,0xa5d2,0xa5ea,0xa61c,0xa348,0x9b58,0x9e1a,0x9d3a,0x9cd4,0x9f7c,0x9e08,0xa216,0xa26e,0xa008,0x3918,0xe84c8,0x3650,0xa63e,0xa64c,0xa65e,0xa73e,0xc1c4,0xbf94,C2C0,C2C8)
BOUNDARIES=menu.BOUNDARIES+NEW_BOUNDARIES+STOP_BOUNDARIES
KEY_PCS=menu.KEY_PCS+NEW_BOUNDARIES+STOP_BOUNDARIES+(DISPATCH,0x3af8,0xa076,0xa06c)
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
PORT_REGIONS=fc.PORT_REGIONS


# ----------------------------------------------------------------------------------
# Condition driver: identical to fade_card.run_condition (same Observer, same checks) except that the per-step split-phase limit is
# raised from 40 to 400 (the a5ea frame has about a hundred first-hit contract block starts).  The imported module is not edited.
# ----------------------------------------------------------------------------------
PHASE_LIMIT=400


def open_run_condition(program,spec,continuous):
    menu.RUNS['n']+=1
    fx=spec['fixture'];o=fc.Observer(program,continuous);phases=[];allow=bool(spec.get('guarded'))
    try:
        o.prepare(dict(fx,stop_pc=spec['steps'][0]['stop_pc'],checkpoints=spec['steps'][0]['checkpoints']))
        for index,step in enumerate(spec['steps']):
            o.begin_step(step['stop_pc'],step['checkpoints']);first=None;pending=step['changes']
            while True:
                remaining=[pc for pc in step['checkpoints'] if pc not in o.seen]
                target=step['stop_pc'] if continuous or not remaining else remaining[0]
                changes=o.apply(pending);pending=[]
                p=o.run(allow_guard=allow)
                if first is None:first=p['incoming']
                p.update(label=step['label'] if not phases or phases[-1]['step']!=index else '%s+after-%x'%(step['label'],phases[-1]['outgoing']['pc']),step=index,host_changes=changes,stop_pc=target,
                    carry=None,carry_in=(step.get('carry_in') if not any(q['step']==index for q in phases) else None),branch_evidence=[],step_stop_pc=step['stop_pc'],phase_in_step=sum(q['step']==index for q in phases))
                phases.append(p)
                if p['guard'] is not None:break
                assert p['outgoing']['pc']==target,(spec['label'],step['label'],p['outgoing'],hex(target))
                if p['outgoing']['pc']==step['stop_pc']:
                    want=fc.expected_a7(step,first,p);assert p['outgoing']['a7']==want,(spec['label'],step['label'],hex(p['outgoing']['a7']),hex(want))
                    break
                assert p['phase_in_step']<PHASE_LIMIT
            if phases[-1]['guard'] is not None:
                assert allow,(spec['label'],phases[-1]['guard']);assert index==len(spec['steps'])-1
        if allow:fc.check_guard(spec,phases[-1])
        else:assert all(p['guard'] is None for p in phases)
        return phases
    finally:o.close()


fc.run_condition=open_run_condition


def hx(v):return hex(v)


# ----------------------------------------------------------------------------------
# Stop evidence: a boundary stop is accepted only directly after the transferring instruction
# ----------------------------------------------------------------------------------
BOUNDARY_RULES={
    0x9e94:dict(prev=0x9b74,bytes='6600031e',how='BNE.W taken at 9b74 after AND.W e(A3),D0 (low bit set: D0.W=1)'),
    0xa2be:dict(prev=0xa3a8,bytes='6100ff14',how='BSR a2be at a3a8, return a3ac on the stack',ret=0xa3ac),
    0xa406:dict(prev=0xa3fe,bytes='67000006',how='BEQ.W taken at a3fe (CMPI.B #0,D0 with D0.B=-e5=0)'),
    0xa662:dict(prev=0xa3f6,bytes='6700026a',how='BEQ.W taken at a3f6 (CMPI.B #2,D0 with D0.B=-e5=2)'),
    0xa70a:dict(prev=0xbfb6,bytes='4ef90000a70a',how='JMP a70a at bfb6 after MOVE.B #ff,80(A6) (D0.W=3)'),
    0xbd26:dict(prev=0xc1e6,bytes='6100fb3e',how='BSR bd26 at c1e6, return c1ea on the stack',ret=0xc1ea),
    0xe84d6:dict(prev=0xe84cc,bytes='64000008',how='BCC.W taken at e84cc after CMPI.B #10,D1 (D1.B >= 10)'),
    0xa63c:dict(prev=0xa638,bytes='66000004',how='fall-through of BNE.W at a638 after CMPI.L #ffffffff,(A3): (A3)==ffffffff; TRAP #f not executed'),
    C2C8:dict(prev=0xc2c2,bytes='66000004',how='BNE.W taken at c2c2 after TST.B D0 at c2c0 (D0.B != 0)')}


def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if not (pc==p['step_stop_pc'] and (pc in BOUNDARY_RULES or pc in HOOK_STOPS)):
        return menu.stop_evidence(program,p)
    assert len(pcs)>=2 and pcs[-1]==pc,(p['label'],pcs[-3:])
    prev=pcs[-2];ram=p['ram_after']
    if pc in HOOK_STOPS:
        assert prev==0xa3c6 and program[0xa3c6:0xa3c8].hex()=='4e94',(p['label'],hex(prev))
        assert u32(ram,o['a7'])==0xa3c8 and o['a4']==pc,(p['label'],hex(u32(ram,o['a7'])),hex(o['a4']))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,reached_from='JSR (A4) at a3c6 (bytes 4e94), hook target A4=%x from LONG a(A3)<>0; return LONG a3c8 on the stack at A7=%x; hook not executed'%(pc,o['a7']))
    rule=BOUNDARY_RULES[pc];n=len(rule['bytes'])//2
    assert prev==rule['prev'] and program[prev:prev+n].hex()==rule['bytes'],(p['label'],hex(prev),program[prev:prev+n].hex())
    if 'ret' in rule:assert u32(ram,o['a7'])==rule['ret'],(p['label'],hex(u32(ram,o['a7'])))
    if pc==0x9e94:assert o['d0']&0xffff==1,(p['label'],hex(o['d0']))
    if pc==0xa406:assert o['d0']&0xff==0
    if pc==0xa662:assert o['d0']&0xff==2
    if pc in (0xa70a,0xbd26):assert o['d0']&0xffff==3,(p['label'],hex(o['d0']))
    if pc==0xe84d6:assert (o['d1']&0xff)>=0x10,(p['label'],hex(o['d1']))
    if pc==C2C8:assert o['d0']&0xff!=0,(p['label'],hex(o['d0']))
    if pc==0xa63c:
        rb,r32=menu.reader(program,ram,p['modeled_bank']);assert r32(o['a3'])==0xffffffff,(p['label'],hex(o['a3']))
    return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,reached_from=rule['how']+('; return LONG %x on the stack at A7=%x'%(rule['ret'],o['a7']) if 'ret' in rule else ''))


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


POOL={}      # sha256 -> first written file; identical payloads (ram_before of a phase == ram_after of the previous one, snapshots, unchanged PVC) are hard-linked


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def store(prefix,phases):
    """Same rows/artifact names/hashes as fade_card.store; identical payload files are hard-linked instead of copied."""
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


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Declared fixtures
# ----------------------------------------------------------------------------------
def rec_write(offset,size,value,why):return fc.ram_write(A2+offset,size,value,why)
def w32(address,value,why):return fc.ram_write(address,4,value,why)


def descriptor_writes(title,items,minw=0,minh=0,flags=0,hook=0,desc=DESC,strs=STRS):
    """Declared descriptor + string fixture (same layout as the push observer); hook = LONG at +a (A4 of a3ba)."""
    pool=bytearray();placed={}
    def ptr(x):
        if x is None:return 0
        if isinstance(x,int):return x
        if x not in placed:placed[x]=strs+len(pool);pool.extend(x+b'\x00')
        return placed[x]
    head=bytearray(0x10)
    head[0:4]=ptr(title).to_bytes(4,'big');head[4]=minw;head[5]=minh;head[0xa:0xe]=hook.to_bytes(4,'big');head[0xe:0x10]=flags.to_bytes(2,'big')
    body=bytearray()
    for item in items:
        s,cb,w=item if isinstance(item,tuple) else (item,0,0)
        body+=ptr(s).to_bytes(4,'big')+cb.to_bytes(4,'big')+w.to_bytes(2,'big')
    body+=(0xffffffff).to_bytes(4,'big')
    writes=menu.ram_bytes(desc,bytes(head+body),'declared descriptor fixture')
    if pool:writes+=menu.ram_bytes(strs,bytes(pool),'declared string fixture')
    return writes


def apply_writes(ram,writes):
    ram=bytearray(ram)
    for c in writes:
        if c['kind']=='ram':
            for i,b in enumerate(c['value'].to_bytes(c['size'],'big')):ram[(c['address']+i)&0xffff]=b
    return ram


def retarget(program,s0,record,title,items,why,minw=0,minh=0,flags=0,hook=0):
    """Declared writes that point the menu record at `record` to the RAM descriptor DESC and set 6(count)/b(width)/c(height) as the push model
    computes them for this descriptor (push model = menu.model_menu, an independent model of the push unit); x/y/byte-4/5/7.. keep the real S0 values."""
    writes=descriptor_writes(title,items,minw,minh,flags,hook)
    ram=apply_writes(s0['ram_after'],writes)
    rb,r32=menu.reader(program,ram,s0['modeled_bank'])
    o=s0['outgoing'];m=menu.model_menu(rb,r32,DESC,dict(d0=o['d0'],d1=o['d1'],d2=0,d3=0,d7=0))   # D0/D1 only supply x,y which are not rewritten
    out=list(writes)+[w32(record,DESC,'declared record pointer (A2) -> RAM descriptor: '+why)]
    out+=[fc.ram_write(record+6,1,m['rec'][6],'declared count 6(A2) of the fixture descriptor'),fc.ram_write(record+0xb,1,m['rec'][0xb],'declared width b(A2) of the fixture descriptor'),
          fc.ram_write(record+0xc,1,m['rec'][0xc],'declared height c(A2) of the fixture descriptor')]
    return out,m


def u8(ram,a):return ram[a&0xffff]
def u16(ram,a):return (ram[a&0xffff]<<8)|ram[(a+1)&0xffff]


def growth_model(byte4,byte5,c):
    """Contract items 3/4: frames until a5ea. Returns (frames, word after each frame). Terminal frame (byte4>=c) leaves the word unchanged."""
    w=(byte4<<8)|byte5;hist=[]
    for n in range(1,2000):
        if (w>>8)>=c:hist.append(w);return n,hist
        w=(w+((c<<6)&0xffff))&0xffff;lim=(c<<8)&0xffff
        if lim<w:w=lim
        hist.append(w)
    raise AssertionError('no termination')


# ----------------------------------------------------------------------------------
# Steps
# ----------------------------------------------------------------------------------
def reentry(why='frame re-entry: PC only; A6/A7 are the previous real outputs (A6 = card child, (A6)=c2ba)'):return fc.pc_to(0x2ab8,why)


def open_steps(n,first_changes=(),stop=DISPATCH,depth=8,label='open-frame-%02d'):
    """n frames. Frame 1 continues the a370 stop (changes = declared host changes only); frames 2..n are PC=2ab8 re-entries.
    The last frame stops at `stop` with live A7 = a370-entry A7 + depth (frame 1) / depth-8 relative to the re-entry A7."""
    steps=[]
    for k in range(1,n+1):
        last=k==n
        changes=list(first_changes) if k==1 else [reentry()]
        steps.append(dict(label=label%k,changes=changes,stop_pc=stop if last else DISPATCH,checkpoints=[],a7=('entry',(depth if k==1 else depth-8) if last else (8 if k==1 else 0))))
    return steps


# ----------------------------------------------------------------------------------
# Conditions
# ----------------------------------------------------------------------------------
def build_specs(program,connected,s0,s0_label):
    specs=[];models={}
    ram0=s0['ram_after'];o0=s0['outgoing']
    byte4,byte5,cval=u8(ram0,A2+4),u8(ram0,A2+5),u8(ram0,A2+0xc)
    def with_checkpoints(spec):
        probe=copy.deepcopy(spec)
        for s in probe['steps']:s['checkpoints']=[]
        try:phases=fc.run_condition(program,probe,True)
        except Exception as e:
            diag=copy.deepcopy(probe);diag['guarded']=True;diag['guard']={}
            try:last=fc.run_condition(program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
            except Exception as e2:info=repr(e2)
            raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(spec['label'],e,info))
        for index,step in enumerate(spec['steps']):
            if index>=len(phases):break
            order=[]
            entry=phases[index]['pcs'][0]
            for pc in phases[index]['pcs'][1:]:
                if pc in BLOCK_SET and pc not in order and pc!=entry:order.append(pc)    # the entry PC itself is never a split point (it would stop before executing anything)
            step['checkpoints']=order
        return spec
    def make(label,group,prov,steps,regs=None,guard=None,model=None,fixture_edit=None,**extra):
        if guard is not None:extra.update(guarded=True,guard=guard)
        spec=cc.fresh_spec(connected,s0,s0_label,label,steps,group,prov,regs=regs,**extra)
        if fixture_edit:fixture_edit(spec['fixture'])
        with_checkpoints(spec);specs.append(spec)
        if model is not None and guard is None:models[label]=model
        return spec
    base_prov='fresh state from the recorded a370 stop output (live A7 holds c2c0 above 2ac2); '
    # ---- connected: a370 stop output -> opening frames -> a5ea frame -> a65e RTS -> c2c0 -> 2ac2
    n0,hist0=growth_model(byte4,byte5,cval)
    connected_spec=cc.fresh_spec(connected,s0,s0_label,'connected-a370-to-open',open_steps(n0+0),'connected',
        'fresh CPU started from the recorded push-unit a370 stop output; no host change in frame 1; frames 2..%d are declared PC=2ab8 re-entries (A6 = card child, (A6)=c2ba); last frame is the a5ea frame (cursor search, 9b58, 9e1a, callbacks) -> a65e RTS -> c2c0 -> 2ac2'%n0,chain_offset=None)
    with_checkpoints(connected_spec);models['connected-a370-to-open']=dict(kind='growth',byte4=byte4,byte5=byte5,c=cval,frames=n0,real_descriptor=True)
    # ---- residual byte 5(A2)
    for v in (0x00,0x40,0xc0,0xff):
        n,_=growth_model(byte4,v,cval)
        make('residual-byte5-%02x'%v,'open-residual',base_prov+'declared RAM write 5(A2)=%02x (push leaves the byte unwritten: original memory value 88 in the connected chain); word 4(A2) += c<<6 keeps byte 5'%v,
            open_steps(n,[rec_write(5,1,v,'declared residual BYTE 5(A2) (not written by the push)')]),model=dict(kind='growth',byte4=byte4,byte5=v,c=cval,frames=n))
    for c_,v in ((1,0x00),(1,0xff),(2,0x00),(2,0x80),(2,0xff),(3,0x00),(3,0xff)):
        n,_=growth_model(byte4,v,c_)
        make('residual-byte5-%02x-c%d'%(v,c_),'open-residual',base_prov+'declared RAM writes 5(A2)=%02x and c(A2)=%02x (small box: the residual byte changes the number of growth frames)'%(v,c_),
            open_steps(n,[rec_write(5,1,v,'declared residual BYTE 5(A2)'),rec_write(0xc,1,c_,'declared height c(A2)')]),model=dict(kind='growth',byte4=byte4,byte5=v,c=c_,frames=n))
    # ---- b/c small and large boxes (declared record fields)
    for name,b,c in (('c0',None,0),('c1',None,1),('c2',None,2),('b0',0,None),('b2',2,None),('b3',3,None),('b2-c1',2,1),('b0-c0',0,0),('b30-c18',0x30,0x18),('c-ff',None,0xff),('b-ff',0xff,None)):
        ch=[];cc_=cval
        if b is not None:ch.append(rec_write(0xb,1,b,'declared width b(A2)'))
        if c is not None:ch.append(rec_write(0xc,1,c,'declared height c(A2)'));cc_=c
        n,_=growth_model(byte4,byte5,cc_)
        make('box-%s'%name,'open-box',base_prov+'declared record fields %s'%', '.join(x for x in ('b(A2)=%02x'%b if b is not None else '','c(A2)=%02x'%c if c is not None else '') if x),
            open_steps(n,ch),model=dict(kind='growth',byte4=byte4,byte5=byte5,c=cc_,frames=n))
    # ---- RAM descriptor fixtures (record pointer retargeted)
    cb_yes,cb_no=0xc1c4,0xbf94
    def desc_spec(label,title,items,prov,group='open-descriptor',minw=0,minh=0,flags=0,extra_writes=(),frames=None,stop=DISPATCH,depth=8,regs=None,expect=None,guard=None,fixture_edit=None,start7=0):
        writes,m=retarget(program,s0,A2,title,items,prov,minw,minh,flags)
        writes=writes+list(extra_writes)+([rec_write(7,1,start7,'declared BYTE 7(A2) (cursor start)')] if start7 else [])
        c=m['rec'][0xc]
        n,_=growth_model(byte4,byte5,c) if frames is None else (frames,None)
        make(label,group,base_prov+'declared descriptor fixture at %x (strings %x), record (A2) -> %x: %s'%(DESC,STRS,DESC,prov),open_steps(n,writes,stop=stop,depth=depth),regs=regs,guard=guard,fixture_edit=fixture_edit,
            model=dict(kind='descriptor',title=title,items=items,frames=n,c=c,rec=m['rec'],expect=expect or {},start7=start7,flags=flags))
    YES=(b' YES ',cb_yes,0);NO=(b' NO ',cb_no,0)
    desc_spec('desc-title-present',b' DATA MENU ',[YES,NO],'title string present, items YES(c1c4)/NO(bf94)')
    desc_spec('desc-title-wider-than-items',b' A VERY LONG MENU TITLE ',[YES,NO],'title wider than the items (title centered by 38e8 width, ASR.B #1)')
    desc_spec('desc-title-escape-newline',b'T\\r\\n',[YES,NO],'title with escapes (38e8 width excludes them)')
    desc_spec('desc-null-and-separator-first',None,[None,0xfffffffe,YES,NO],'items null(0), separator(fffffffe), YES, NO: the a5ea cursor search skips two callback-less items')
    desc_spec('desc-separator-between',None,[YES,0xfffffffe,None,NO],'items YES, separator, null, NO: a216 skips the separator and the null item')
    desc_spec('desc-plain-first-item-nocallback',b' T ',[(b' INFO ',0,0),YES,NO],'first item without callback (cursor search 1 step)')
    desc_spec('desc-cursor-wrap-a614',None,[YES,(b' A ',0,0),(b' B ',0,0)],'items YES, plain, plain with declared BYTE 7(A2)=1: the a5ea cursor search runs 1 -> 2 -> wraps to 0 (a614)',start7=1)
    desc_spec('desc-single-item-yes',None,[YES],'single YES item: a216 cycles back to the same item')
    desc_spec('desc-single-item-no',None,[NO],'single NO item only (D0=6 does nothing in bf94; D0=0 plays the sound)')
    desc_spec('desc-flags-0002',None,[YES,NO],'WORD e(A3)=0002: width gets no +2 in the push model, e bit1 is not bit0',flags=0x0002)
    desc_spec('desc-minw-minh',b'T',[YES,NO],'min width 30 / min height 10 (push model sizes the box)',minw=0x30,minh=0x10)
    desc_spec('desc-wide-menu',None,[(b'A'*40,cb_yes,0),(b'B'*2,cb_no,0)],'wide item (40 chars)')
    desc_spec('desc-many-items',None,[(b' ITEM %d '%i if i<9 else b' ITEM ',cb_yes if i==3 else 0,0) for i in range(12)],'12 items, only item 3 has a callback')
    desc_spec('desc-esc-color-escape',None,[(b'\\c\x07 YES ',cb_yes,0),NO],'item string with \\c escape D1.B=07 (< 10: e84c8 passes to 3650)')
    # ---- banked reads: title/item pointers into the banked area (CPU 200000.., physical offset = bank + address - 200000); no existing descriptor in the bank (see bank_descriptor_search)
    b2=menu.find_bank_only(program,0x200000);b23=menu.find_bank_strings(program)
    bt,bi=b2[0][0],b2[1][0]
    def desc_bank(label,title,items,prov,fixture_edit=None):
        desc_spec(label,title,items,prov,group='open-bank',fixture_edit=fixture_edit)
    desc_bank('bank-strings-title-and-items',bt,[(bi,cb_yes,0),(bt,cb_no,0)],'title and item pointers into the banked area (%x, %x) read through the CURRENT bank (200000: physical offset == CPU address)'%(bt,bi))
    sa=b23[0][0]
    desc_bank('bank-200000-address-differs-from-300000',sa,[(sa,cb_yes,0),NO],'title/item pointer %x read in bank 200000 (len %d); the next condition reads the same address through bank 300000 (len %d)'%(sa,b23[0][1],b23[0][2]))
    def to_300000(fx):
        pvc=bytearray(fx['pvc']);pvc[0x1ff0:0x1ff4]=(0x0000).to_bytes(2,'big')+(0x2000).to_bytes(2,'big');fx['pvc']=bytes(pvc);fx['bank_state']=(0x300000,0xa0,0x2000)
    desc_bank('bank-300000-same-address',sa,[(sa,cb_yes,0),NO],'declared bank state 300000 (modeled ff8=00a0 ff9=2000, raw PVC words 2ffff0/2ffff2 = 0000/2000 consistent with pvc_bank_update) at the fresh start; title/item pointer %x read through bank 300000'%sa,fixture_edit=to_300000)
    # e84c8 with D1.B >= 10 -> stop e84d6
    desc_spec('desc-e84c8-d1-0x20-item',None,[(b'\\c\x20 YES ',cb_yes,0),NO],'item with \\c escape D1.B=20: e84c8 CMPI.B #10,D1 BCC -> stop e84d6 (item draw: 9e1a -> 9d3a -> 3918 -> JSR (A1))',group='open-boundary-stop',stop=0xe84d6,depth=-16)
    desc_spec('desc-e84c8-d1-0x10-item',None,[(b'\\c\x10 YES ',cb_yes,0),NO],'item with \\c escape D1.B=10 (equal: BCC taken -> stop e84d6)',group='open-boundary-stop',stop=0xe84d6,depth=-16)
    desc_spec('desc-e84c8-d1-0x0f-item',None,[(b'\\c\x0f YES ',cb_yes,0),NO],'item with \\c escape D1.B=0f (< 10: no stop, 3650 draws)')
    desc_spec('desc-e84c8-d1-0xff-title',b'\\c\xff T',[YES,NO],'title with \\c escape D1.B=ff: stop e84d6 in the title draw (one call level less)',group='open-boundary-stop',stop=0xe84d6,depth=-12)
    # descriptor e bit0 -> 9e94 boundary; stop in frame 2 (first 9b58 with 4(A2)<>0)
    desc_spec('desc-flags-0001-9e94',None,[YES,NO],'WORD e(A3)=0001: 9b58 AND.W e(A3),D0 nonzero -> BNE 9e94 (first 9b58 with 4(A2)<>0 is frame 2)',group='open-boundary-stop',flags=0x0001,frames=2,stop=0x9e94,depth=-8)
    desc_spec('desc-flags-ffff-9e94',None,[YES,NO],'WORD e(A3)=ffff: bit0 set -> 9e94',group='open-boundary-stop',flags=0xffff,frames=2,stop=0x9e94,depth=-8)
    # first item ffffffff -> a63c TRAP boundary (zero items; the word after the terminator is declared nonzero so the a5ea cursor search ends)
    ch=[fc.ram_write(DESC+0x14,4,0x0000c1c4,'declared LONG 4(A3) of the terminator row: nonzero so TST.L 4(A3) ends the a5ea cursor search at once')]
    writes,m=retarget(program,s0,A2,None,[],'zero items',0,0,0)
    nz,_=growth_model(byte4,byte5,m['rec'][0xc]);zero_w=writes+ch
    make('desc-zero-items-a63c','open-boundary-stop',base_prov+'declared descriptor fixture with first item ffffffff at %x (zero items) plus declared LONG c1c4 at %x; the a5ea frame reaches a628..a638 (first item ffffffff) and stops at a63c, the TRAP #f is not executed'%(DESC+0x10,DESC+0x14),
        open_steps(nz,writes+ch,stop=0xa63c,depth=0),model=dict(kind='descriptor',title=None,items=[],frames=nz,c=m['rec'][0xc],rec=m['rec'],expect={}))
    # ---- -e5 / -f2 / hook / two-frame loop
    make('state-e5-0-a406','open-boundary-stop',base_prov+'declared RAM write -e5(A5)=00: a3e6..a3fe BEQ.W a406 (input path, no implementation) -> stop a406',open_steps(1,[fc.ram_write(E5,1,0,'declared -e5(A5)')],stop=0xa406,depth=0))
    make('state-e5-2-a662','open-boundary-stop',base_prov+'declared RAM write -e5(A5)=02: a3f6 BEQ.W a662 (close path) -> stop a662',open_steps(1,[fc.ram_write(E5,1,2,'declared -e5(A5)')],stop=0xa662,depth=0))
    for v in (3,0x7f,0xff):
        make('state-e5-%02x-a402-rts-ff'%v,'open-boundary-stop',base_prov+'declared RAM write -e5(A5)=%02x: a402 MOVEQ -1,D0 RTS -> c2c0 TST.B D0 / BNE.W c2c8 taken -> stop c2c8 (c2c8 is outside the contract)'%v,
            open_steps(1,[fc.ram_write(E5,1,v,'declared -e5(A5)')],stop=C2C8,depth=4))
    make('state-f2-ge-107f0e-a3de-rts-ff','open-boundary-stop',base_prov+'declared -f2(A5)=107f0e: A2=107efe <u -f2 -> a3d0, A2=-f2>=107f0e -> a3de MOVEQ -1,D0 RTS -> c2c0 BNE.W c2c8 -> stop c2c8',
        open_steps(1,[w32(F2,0x107f0e,'declared -f2(A5)')],stop=C2C8,depth=4))
    make('state-f2-ffff0000-a3de','open-boundary-stop',base_prov+'declared -f2(A5)=ffff0000 (unsigned larger): a3de RTS ff',open_steps(1,[w32(F2,0xffff0000,'declared -f2(A5)')],stop=C2C8,depth=4))
    # hook at a(A3): older record (real push record) retargeted so that its descriptor has A4<>0; the stop is the hook target
    for name,target in (('9000',0x9000),('c2c0',0xc2c0),('fff00',0xfff00)):
        HOOK_STOPS.add(target)
        writes,m=retarget(program,s0,A2,None,[YES,NO],'hook',0,0,0,hook=target)
        n=1
        make('hook-a4-nonzero-%s'%name,'open-boundary-stop',base_prov+'declared descriptor fixture with LONG a(A3)=%x: a3ba A4<>0 -> a3c6 JSR (A4) -> stop at the hook target (return a3c8 on the stack)'%target,
            open_steps(1,writes,stop=target,depth=-8))
    # two-frame loop: an older record at 107efe and a newer declared record at 107eee (copy of the S0 record), -f2=107eee
    rec_new=A2-0x10
    copy_rec=menu.ram_bytes(rec_new,bytes(ram0[(A2+i)&0xffff] for i in range(16)),'declared newer menu record = copy of the real record')
    two=copy_rec+[w32(F2,rec_new,'declared -f2(A5) = newer record')]
    make('loop-two-frames-no-hook','open-loop',base_prov+'declared newer record at %x (copy of the real record), -f2=%x: a370 loops over both (older: A2<>-f2, f bit0=0 -> a3b8; newer: A2==-f2), a3d0 selects the newer record, then a5d2 frames as usual'%(rec_new,rec_new),
        open_steps(n0,two),model=dict(kind='growth',byte4=byte4,byte5=byte5,c=cval,frames=n0,top=rec_new))
    for target in (0x9000,):
        HOOK_STOPS.add(target)
        writes,m=retarget(program,s0,A2,None,[YES,NO],'older record hook',0,0,0,hook=target)
        make('loop-two-frames-hook-older','open-loop',base_prov+'older record -> RAM descriptor with hook %x, newer record at %x: the first loop iteration (a3b8) stops at the hook target'%(target,rec_new),
            open_steps(1,copy_rec+[w32(F2,rec_new,'declared -f2(A5) = newer record')]+writes,stop=target,depth=-8))
    # newer record whose f bit0=1 and byte4<>0 -> a3a8 BSR a2be (boundary) when the OLDER record is not the top: older gets 4(A2)<>0, f bit0=1
    make('loop-older-f-bit0-byte4-a2be','open-boundary-stop',base_prov+'newer record at %x as above, older record f=01 and 4(A2)=03: loop iteration 1 (A2<>-f2, f bit0 set, 4(A2)<>0) -> a3a8 BSR a2be -> stop a2be'%rec_new,
        open_steps(1,copy_rec+[w32(F2,rec_new,'declared -f2(A5) = newer record'),rec_write(0xf,1,1,'declared f(A2) bit0'),rec_write(4,1,3,'declared BYTE 4(A2)')],stop=0xa2be,depth=-8))
    # ---- occlusion (a018 C=1): direct entries at a348 / a61c, -ee = older record, -f2 = newer (occluding) record
    def occ_writes(x=None,y=None,b=None,h=None,f=0,newer_c=None):
        w=list(copy_rec)+[w32(F2,rec_new,'declared -f2(A5) = newer (occluding) record')]
        for off,v,nm in ((9,x,'x 9'),(0xa,y,'y a'),(0xb,b,'width b'),(4,h,'height byte 4'),(0xf,f,'f')):
            if v is not None:w.append(fc.ram_write(rec_new+off,1,v,'declared newer record %s'%nm))
        return w
    ox,oy=u8(ram0,A2+9),u8(ram0,A2+0xa)
    ee_older=w32(E2,A2,'declared -ee(A5) = older record (a370 would have stored it; direct entry skips a370)')
    older_open=[ee_older,rec_write(4,1,3,'declared BYTE 4(A2)=03 (older record: box grown by 3 rows so 9b58 draws)')]
    def occ(label,prov,ow,entry=A348,**kw):
        make(label,'open-occlusion',base_prov+'declared PC=%x (direct entry; -ee=%x older record, -f2=%x newer record): '%(entry,A2,rec_new)+prov,
            open_steps(1,[fc.pc_to(entry,'declared direct entry from the a370 stop output')]+older_open+ow,depth=8),**kw)
    occ('occlude-a348-none','newer record elsewhere (x+40): no cell occluded (a018 C=0 only)',occ_writes(x=(ox+0x20)&0xff))
    occ('occlude-a348-top-rows','newer record same x,y,b with height 2: first two rows occluded (C=1 -> tile skipped)',occ_writes(h=2))
    occ('occlude-a348-all','newer record covers everything (x=0,y=0,b=ff,height ff)',occ_writes(x=0,y=0,b=0xff,h=0xff))
    occ('occlude-a348-f-bit0','newer record covers everything but f bit0=1: BTST #0,f(A0) nonzero -> not occluding',occ_writes(x=0,y=0,b=0xff,h=0xff,f=1))
    occ('occlude-a348-width-outside','newer record covers rows but its width b=0 (D6-x >= 0): a054 BCC -> not occluding',occ_writes(x=ox,y=0,b=0,h=0xff))
    occ('occlude-a348-height-outside','newer record covers columns but its height byte 4 = 0: a062 BCS not taken -> not occluding',occ_writes(x=0,y=oy,b=0xff,h=0))
    # a61c direct entry: full draw of the older record under the newer one (9b58 + 9e1a + callbacks incl. a216 through a008)
    full_open=[ee_older,rec_write(4,1,cval,'declared BYTE 4(A2)=c (box fully open)'),rec_write(7,1,2,'declared BYTE 7(A2)=2 (YES, cursor search done)')]
    def occ61(label,prov,ow):
        make(label,'open-occlusion',base_prov+'declared PC=a61c (direct entry; -ee=%x older record, -f2=%x newer record): '%(A2,rec_new)+prov,
            open_steps(1,[fc.pc_to(A61C,'declared direct entry from the a370 stop output')]+full_open+ow,depth=8))
    occ61('occlude-a61c-none','newer record elsewhere: older record drawn fully (A2<>-f2 palette variants), callbacks YES/NO',occ_writes(x=(ox+0x20)&0xff))
    occ61('occlude-a61c-all','newer record covers everything: a018 C=1 for every cell (box tiles skipped; a216 text cells skipped by a008)',occ_writes(x=0,y=0,b=0xff,h=0xff))
    occ61('occlude-a61c-first-rows','newer record covers the first two rows',occ_writes(h=2))
    tw,tm=retarget(program,s0,A2,b' MENU ',[YES,NO],'older record with a title')
    make('occlude-a61c-title-older','open-occlusion',base_prov+'declared PC=a61c (direct entry; -ee=%x older record with a title descriptor, -f2=%x newer record elsewhere): 9e1a title branch with A2<>-f2 (D1=0603 at 9e6e)'%(A2,rec_new),
        open_steps(1,[fc.pc_to(A61C,'declared direct entry from the a370 stop output'),ee_older]+tw+[rec_write(4,1,tm['rec'][0xc],'declared BYTE 4(A2)=c (box fully open)'),rec_write(7,1,0,'declared BYTE 7(A2)=0 (YES is item 0 of the fixture descriptor)')]+occ_writes(x=(ox+0x20)&0xff),depth=8))
    # ---- callbacks entered directly with declared D0 (stack top c2c0 from the a370 stop output)
    def cb(label,entry,d0,stop,depth,prov,extra=()):
        make(label,'open-callback',base_prov+'declared PC=%x (direct entry) and declared initial D0=%08x: '%(entry,d0)+prov,
            open_steps(1,[fc.pc_to(entry,'declared direct entry from the a370 stop output')]+list(extra),stop=stop,depth=depth),regs=dict(d0=d0))
    cb('callback-c1c4-d0-3-bd26',0xc1c4,3,0xbd26,-4,'c1de CMPI.W #3: BSR bd26 -> stop bd26')
    cb('callback-bf94-d0-3-a70a',0xbf94,3,0xa70a,0,'bfa8 CMPI.W #3: MOVE.B #ff,80(A6), JMP a70a -> stop a70a')
    cb('callback-bf94-d0-6-c2c8',0xbf94,6,C2C8,4,'bf9e: 7e(A6)=1e, RTS -> c2c0 TST.B D0 (06) BNE.W c2c8 -> stop c2c8')
    cb('callback-c1c4-d0-0-sound',0xc1c4,0,DISPATCH,8,'a73e D0.W=0 -> JSR 3af8 sound with D0.W=1a6c; D0 restored 0; RTS -> c2c0 -> 2ac2')
    cb('callback-bf94-d0-0-sound',0xbf94,0,DISPATCH,8,'bf94 with D0.W=0 -> sound 3af8; RTS -> c2c0 -> 2ac2')
    cb('callback-c1c4-d0-5',0xc1c4,5,C2C8,4,'D0.W=5 (the 9e08 call value): no sound, no 7e write, RTS -> c2c0 TST.B D0 (05) BNE.W c2c8 -> stop c2c8')
    cb('callback-c1c4-d0-6-a216-reverse',0xc1c4,6,C2C8,4,'7e(A6)=012c, JMP a216 with declared f(A2) bit1: the cursor moves backwards (a23c SUBQ.B #1) and borrows past item 0 (a242 ADD.B 6(A2))',[ee_older,rec_write(7,1,2,'declared BYTE 7(A2)=2'),rec_write(4,1,cval,'declared BYTE 4(A2)=c'),rec_write(0xf,1,2,'declared f(A2) bit1')])
    cb('callback-c1c4-d0-6-a216',0xc1c4,6,C2C8,4,'7e(A6)=012c, JMP a216: cursor moves from the record -ee; a216 RTS -> c2c0 BNE c2c8 (D0.B nonzero) stop c2c8',[ee_older,rec_write(7,1,2,'declared BYTE 7(A2)=2'),rec_write(4,1,cval,'declared BYTE 4(A2)=c')])
    # ---- guards (native partial effects; the C++ implementation must later error with a full rollback)
    gp='fresh state from the recorded a370 stop output with '
    odd_rec=[fc.ram_write(0x107ef3,1,1,'declared BYTE 4 of the odd record = 01'),fc.ram_write(0x107efb,1,5,'declared BYTE c of the odd record = 05')]
    make('guard-odd-f2-A2','guard',gp+'declared -f2(A5)=107eef (odd) and declared bytes 4/c of the odd record: a3d0 A2=-f2=107eef, a3e2 -ee<-A2, a5d2 4(A2)<c(A2) -> a348 -> 9b58 MOVEA.L (A2),A3 reads an odd LONG',
        open_steps(1,[w32(F2,0x107eef,'declared -f2(A5) odd')]+odd_rec),guard=dict(problem='unsupported_odd_data_access',pc=0x9b66,address=0x107eef,size=4,access='read'))
    make('guard-odd-ee-direct-a348','guard',gp+'declared PC=a348 and -ee(A5)=107eef (odd) with declared bytes 4/c: 9b58 loads A2=-ee odd, MOVEA.L (A2),A3 reads an odd LONG',
        open_steps(1,[fc.pc_to(A348,'declared direct entry'),w32(E2,0x107eef,'declared -ee(A5) odd')]+odd_rec),guard=dict(problem='unsupported_odd_data_access',pc=0x9b66,address=0x107eef,size=4,access='read'))
    make('guard-odd-descriptor-A3-a3ba','guard',gp+'declared record pointer (A2)=%x (odd descriptor): a3b8 A3 odd, a3ba MOVEA.L a(A3),A4 reads an odd LONG'%(DESC+1),
        open_steps(1,[w32(A2,DESC+1,'declared record pointer odd')]),guard=dict(problem='unsupported_odd_data_access',pc=0xa3ba,address=DESC+1+0xa,size=4,access='read'))
    make('guard-odd-descriptor-A3-9b58','guard',gp+'declared PC=a348, record pointer (A2)=%x (odd) and BYTE 4(A2)=03: 9b66 A3 odd, 9b6c AND.W e(A3),D0 reads an odd WORD'%(DESC+1),
        open_steps(1,[fc.pc_to(A348,'declared direct entry'),ee_older,w32(A2,DESC+1,'declared record pointer odd'),rec_write(4,1,3,'declared BYTE 4(A2)')]),guard=dict(problem='unsupported_odd_data_access',pc=0x9b6c,address=DESC+1+0xe,size=2,access='read'))
    make('guard-odd-A7','guard',gp+'declared initial A7=%x (odd): a388 MOVE.L A2,-(A7) writes an odd LONG'%(o0['a7']+1),open_steps(1),regs=dict(a7=o0['a7']+1),
        guard=dict(problem='unsupported_odd_data_access',pc=0xa388,address=o0['a7']+1-4,size=4,access='write',odd_write_restored=True))
    make('guard-e5-0-without-stop','guard',gp+'declared -e5(A5)=00 with stop 2ac2 instead of a406: BEQ.W a406 is taken and the fetch at a406 is refused',open_steps(1,[fc.ram_write(E5,1,0,'declared -e5(A5)')]),
        guard=dict(problem='unsupported_code_target',pc=0xa406,target=0xa406))
    make('guard-e5-3-c2c8-without-stop','guard',gp+'declared -e5(A5)=03 with stop 2ac2: a402 RTS ff -> c2c0 BNE.W c2c8, the fetch at c2c8 is refused',open_steps(1,[fc.ram_write(E5,1,3,'declared -e5(A5)')]),
        guard=dict(problem='unsupported_code_target',pc=C2C8,target=C2C8))
    make('guard-a63c-without-stop','guard',gp+'zero-item descriptor with stop 2ac2 instead of a63c: the TRAP #f at a63c is reached and refused (not executed as an exception)',
        open_steps(nz,zero_w),guard=dict(problem='unsupported_TRAP',pc=0xa63c,opcode=0x4e4f))
    esc_w,esc_m=retarget(program,s0,A2,None,[(b'\\c\x20 YES ',cb_yes,0),NO],'x')
    make('guard-d1-ge-10-without-stop','guard',gp+'item with \\c escape D1.B=20 with stop 2ac2: BCC.W to e84d6 is taken and the fetch at e84d6 is refused',
        open_steps(growth_model(byte4,byte5,esc_m['rec'][0xc])[0],esc_w),guard=dict(problem='unsupported_code_target',pc=0xe84d6,target=0xe84d6))
    return connected_spec,specs,models


def ram_diff(a,b,limit=16):
    out=[(i,a[i],b[i]) for i in range(len(a)) if a[i]!=b[i]]
    return dict(count=len(out),first=[dict(address=hex(0x100000+i),a=x,b=y) for i,x,y in out[:limit]])


def ports_of(events):
    return [(e['size'],e['address'],int(e['bytes'],16)) for e in events if e['region'] in PORT_REGIONS]


def frame_rows(phases,control,steps,record=A2):
    """Per-step summary of an open_steps run: word 4(A2) before/after, record fields, ordered video ports, a018 outcomes.
    Events/RAM come from the split phases; PC-derived counts from the continuous control (split phases repeat the checkpoint PC at each boundary)."""
    rows=[];child=phases[0]['outgoing']['a6']
    for index in sorted({p['step'] for p in phases}):
        ps=[p for p in phases if p['step']==index];first,last=ps[0],ps[-1];events=[e for p in ps for e in p['events']]
        cps=[p for p in control if p['step']==index];assert len(cps)==1 and cps[0]['events']==events,(index,)
        pcs=cps[0]['pcs']
        ports=ports_of(events);video=[x for x in ports if x[1] in (0x3c0000,0x3c0004)]
        rec=lambda ram,off,n:int.from_bytes(bytes(ram[(record+off+i)&0xffff] for i in range(n)),'big')
        rows.append(dict(step=index,label=steps[index]['label'],word4_before=rec(first['ram_before'],4,2),word4_after=rec(last['ram_after'],4,2),field_7_after=rec(last['ram_after'],7,1),field_8_after=rec(last['ram_after'],8,1),
            field_e_after=rec(last['ram_after'],0xe,1),child_7e_after=int.from_bytes(bytes(last['ram_after'][(child+0x7e+i)&0xffff] for i in range(2)),'big'),child_80_after=last['ram_after'][(child+0x80)&0xffff],outgoing_pc=hex(last['outgoing']['pc']),outgoing_a7=hex(last['outgoing']['a7']),pc_count_continuous=len(pcs),split_phases=len(ps),counts=fc.counts(events),
            video_long_writes=sum(1 for s,a,v in video if s==4),video_word_writes=sum(1 for s,a,v in video if s==2),video_word_8200_writes=sum(1 for s,a,v in video if s==2 and v==0x8200),
            ordered_port_writes=len(ports),ordered_ports_sha256=sha(b''.join(struct.pack('>BII',s,a,v) for s,a,v in ports)),
            a018_calls=pcs.count(0xa018),a018_clear_returns=pcs.count(0xa06c),a018_set_returns=pcs.count(0xa076),a5ea_reached=0xa5ea in pcs,e84c8_calls=pcs.count(0xe84c8),sound_3af8_calls=pcs.count(0x3af8),
            stop_evidence=last['stop_evidence']))
    return rows


# ----------------------------------------------------------------------------------
# Independent checks of the native results against the contract model
# ----------------------------------------------------------------------------------
def check_models(program,spec,meta,split,control):
    res=dict(label=spec['label'],kind=meta['kind'])
    top=meta.get('top',A2)
    rows=frame_rows(split,control,spec['steps'],top)
    if meta['kind']=='growth':
        assert len(rows)==meta['frames'],(spec['label'],len(rows),meta['frames'])
        _,hist=growth_model(meta['byte4'],meta['byte5'],meta['c'])
        got=[r['word4_after'] for r in rows]
        assert got==hist,(spec['label'],[hex(x) for x in got],[hex(x) for x in hist])
        assert rows[-1]['a5ea_reached'] and not any(r['a5ea_reached'] for r in rows[:-1]),spec['label']
        res.update(word4_progression=[hex(x) for x in got],frames=len(rows))
    else:
        c=meta['c'];n=meta['frames']
        assert len(rows)==n,(spec['label'],len(rows),n)
        res.update(frames=n,record=meta['rec'],record_c=c)
        items=meta['items'];cbs=[(it[1] if isinstance(it,tuple) else 0) for it in items];ptrs=[(it[0] if isinstance(it,tuple) else it) for it in items]
        last=split[-1]
        if last['outgoing']['pc']==DISPATCH and items:
            # cursor search (contract item 9): first item with a nonzero callback; a216 move after YES (c1c4, item 17)
            cnt=len(items);idx=meta.get('start7',0)
            for _ in range(cnt+1):
                if cbs[idx]!=0:break
                idx=(idx+1)%cnt
            else:raise AssertionError('no callback item')
            first_idx=idx;after=idx
            if cbs[idx]==0xc1c4:
                j=idx
                while True:
                    j=(j+1)%cnt
                    if cbs[j]!=0 and ptrs[j]!=0xfffffffe:break
                after=j
            ram=last['ram_after']
            assert u8(ram,A2+7)==after and u8(ram,A2+8)==after,(spec['label'],u8(ram,A2+7),after)
            pcs=[pc for p in control if p['step']==rows[-1]['step'] for pc in p['pcs']]
            sound=pcs.count(0x3af8);want_sound=1 if cbs[after] in (0xc1c4,0xbf94) else 0
            assert sound==want_sound,(spec['label'],sound,want_sound)
            title=meta['title']
            if isinstance(title,bytes) and b'\\' not in title and len(title)>0:
                # contract item 10: title centered with NEG.B / ADD.B b / ASR.B #1 / ADD.B 9 / ANDI.W ff / LSL.W #5 / ADD.B a / ADDI.W 7000 at the first 3918 call (D1=0103 since A2==-f2)
                bounds=[b for p in control if p['step']==rows[-1]['step'] for b in p['boundaries'] if b['pc']==0x3918]
                regs=bounds[0]['registers'];bw,x,y=u8(ram,A2+0xb),u8(ram,A2+9),u8(ram,A2+0xa)
                d=(-len(title)+bw)&0xff;d=((d>>1)|(d&0x80))&0xff;d=(d+x)&0xff;d=(d<<5)&0xffff;d=(d&0xff00)|(((d&0xff)+y)&0xff);d=(d+0x7000)&0xffff
                assert regs['d0']&0xffff==d and regs['d1']&0xffff==0x0103,(spec['label'],hex(regs['d0']),hex(d),hex(regs['d1']))
                res.update(title_position_d0=hex(d),title_d1=hex(regs['d1']&0xffff),title_width=len(title),box_width=bw,x=x,y=y)
            # contract item 11 (amended): 9f7c D1 = 0603 if A2<>-f2 and 7<>8, else (e&e)==2 and 7<>8 -> 0b03, else 0003; rows draw with A2==-f2 here
            nonnull=[i for i,ptr in enumerate(ptrs) if ptr is not None and ptr!=0xfffffffe]
            bounds3918=[b for p in control if p['step']==rows[-1]['step'] for b in p['boundaries'] if b['pc']==0x3918]
            has_title=meta['title'] is not None
            want=([0x0103] if has_title else [])+[(0x0b03 if (meta.get('flags',0)&0xe)==2 and i!=first_idx else 0x0003) for i in nonnull]
            got=[b['registers']['d1']&0xffff for b in bounds3918[:len(want)]]
            assert got==want,(spec['label'],[hex(x) for x in got],[hex(x) for x in want])
            res.update(palette_d1_sequence=[hex(x) for x in got])
            res.update(model_cursor_first=first_idx,model_cursor_after_yes=after,native_7=u8(ram,A2+7),native_8=u8(ram,A2+8),sound_3af8_calls=sound)
    return res


def crosscheck_push(chain_phases,steps_before):
    path=ROOT/'artifacts/animation_machine_card_menu_native/observation.json'
    if not path.exists():return dict(performed=False,reason='card menu push report not present')
    d=json.loads(path.read_text());r=next(x for x in d['results'] if x['label']=='chain-full-bios-resume-to-a370')
    last=[q for q in r['phases'] if q['step']==steps_before-1][-1];mine=fc.step_end(chain_phases,steps_before-1)
    ref_ram=next(v for k,v in last['artifacts'].items() if k.endswith('_ram_after.bin'));ref_pvc=next(v for k,v in last['artifacts'].items() if k.endswith('_pvc_after.bin'))
    assert sha(mine['ram_after'])==ref_ram and sha(mine['pvc_after'])==ref_pvc and mine['outgoing']==last['outgoing']
    return dict(performed=True,reference_report=str(path),reference_report_sha256=sha(path.read_bytes()),reference_tool_sha256=d['tool_sha256'],condition='chain-full-bios-resume-to-a370',step=steps_before-1,label=last['label'],
        ram_after_sha256=ref_ram,pvc_after_sha256=ref_pvc,outgoing_pc=hex(last['outgoing']['pc']),equal=True)


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
    reports=[ROOT/'artifacts/animation_machine_fade_card_native/observation.json',ROOT/'artifacts/animation_machine_card_child_native/observation.json',ROOT/'artifacts/animation_machine_card_menu_native/observation.json']
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,PUSH_CONTRACT,ROOT/'docs/analysis/animation-machine-card-child-contract.md',
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
    # ---- the card child chain (fade/card machinery, reproduced) to the a29c stop, then a29c executed natively to the a370 stop (push unit machinery)
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
    s0=push_a[-1];assert s0['outgoing']['pc']==A370 and u32(s0['ram_after'],s0['outgoing']['a7'])==C2C0 and u32(s0['ram_after'],s0['outgoing']['a7']+4)==DISPATCH
    s0_label='push unit a370 stop (after card child chain step %d, a29c executed)'%(n_child-1)
    connected_spec,specs,models=build_specs(program,connected,s0,s0_label)
    # ---- full chain: BIOS-resume -> ... -> a29c -> a370 stop -> opening frames (one persistent CPU)
    full_steps=child_steps+[copy.deepcopy(push_step)]+copy.deepcopy(connected_spec['steps'])
    connected_spec['chain_offset']=n_child+1
    full=cc.fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'chain-full-bios-resume-to-open',full_steps,'chain',
        'fade/card native chain output at c00468; declared BIOS return (PC=c37c, A7+=4, 10fdc6=00) + declared 28ae pool/parent fixture; natural parent frame, child c250, declared PC=2ab8 child frame re-entries to the a29c stop (card child unit), a29c executed without host change to the a370 stop (push unit), then a370 executed in the same frame (opening frame 1) and declared PC=2ab8 re-entries through the box growth frames to the a5ea frame and the 2ac2 stop')
    full_split,full_control=run_spec(program,full)
    mid=fc.step_end(full_split,n_child)
    assert mid['outgoing']==s0['outgoing'] and mid['ram_after']==s0['ram_after'] and mid['pvc_after']==s0['pvc_after']
    cross=cc.crosscheck_fade_card(full_split);cross_child=menu.crosscheck_card_child(full_split,n_child);cross_push=crosscheck_push(full_split,n_child+1)
    all_specs=[full,connected_spec]+specs;cache={full['label']:(full_split,full_control)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;model_checks=[];open_frames={}
    for number,spec in enumerate(all_specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if spec.get('chain_offset') is not None:compared_total+=cc.compare_with_chain(spec,split,full_split)
        if spec['label'] in models and spec.get('guard') is None:model_checks.append(check_models(program,spec,models[spec['label']],split,control))
        if spec['label']=='chain-full-bios-resume-to-open':
            open_frames[spec['label']]=frame_rows([p for p in split if p['step']>n_child],[p for p in control if p['step']>n_child],full_steps)
        elif spec['label']=='connected-a370-to-open':open_frames[spec['label']]=frame_rows(split,control,spec['steps'])
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
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,open_ranges=OPEN_RANGES,instructions=instructions,boundary_stop_pcs=STOP_BOUNDARIES,hook_stop_pcs=sorted(HOOK_STOPS),block_starts=BLOCKS,
        stop_rules={hex(k):v['how'] for k,v in BOUNDARY_RULES.items()},
        open_bytes={hex(lo):program[lo:hi].hex() for lo,hi in OPEN_RANGES}),indent=2)+'\n').encode()
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
    child_addr=fc.step_end(full_split,3)['outgoing']['a6']
    bank_reads=[dict(label=r['label'],bank_reads=sum(p['counts']['bank_reads'] for p in r['phases'])) for r in results if r['group']=='open-bank']
    bank_search=[menu.scan_bank_descriptors(program,0x200000),menu.scan_bank_descriptors(program,0x300000)]
    condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards]
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,fade_card_crosscheck=cross,card_child_crosscheck=cross_child,card_menu_push_crosscheck=cross_push,child_address=hex(child_addr),
        child_frames=cc.child_frame_summary(full_split,child_addr,full_steps),c266_frame_evidence=cc.c266_evidence(full_split),variant_child_layouts=[],guard_reports=guard_reports,
        bank_reads_by_condition=bank_reads,bank_descriptor_search=bank_search,new_ranges=OPEN_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha),contract_model_checks=model_checks,open_frames=open_frames,condition_table=condition_table,
        covered_PCs=sorted(coverage),block_starts=BLOCKS,boundary_stop_pcs=STOP_BOUNDARIES,failure=None,rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; the card child chain (declared BIOS resume, declared PC=2ab8 child frame re-entries) and the push unit a29c -> a370 are re-derived, a370 is then executed natively; frames after the first are declared PC=2ab8 re-entries only (parent/other objects omitted).',
            'Boundary stops (9e94, a2be, a406, a662, a70a, bd26, e84d6, a63c TRAP, c2c8, hook targets of JSR (A4) at a3c6) are never executed and are not executable ranges: each is accepted only directly after the transferring instruction. 9f36, a71a and the c1ee..c208 block are reachable only through bd26 (not executed) and are not observed. c2c8 (BNE.W target of c2c2 when D0.B<>0 at c2c0) is a contract boundary (amended contract); it is reached naturally by the RTS-ff paths (a3de, a402) and by callbacks that leave D0.B<>0.',
            'Boundary conditions and direct entries (a348, a61c, c1c4, bf94 with declared D0) are fresh CPUs started from the recorded a370 stop output with declared initial registers, declared RAM fixture writes (descriptor %x, strings %x, newer menu record %x) and declared PC redirects; nothing is injected after execution begins. The RAM image is the pseudo-random prepared image, so every byte a fixture relies on is a declared write.'%(DESC,STRS,A2-0x10),
            'Occlusion (a018 C=1) cannot occur on the a370 -> a5d2 path (the top record has -ee == -f2, so no frame lies above it); it is observed through declared direct entries at a348/a61c with -ee = older record and -f2 = a declared newer record.',
            'Split checkpoints are the first hit of each contract block start (execution order, entry PC excluded); loop re-visits are not split again. The continuous run is the control.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path only (a018 outcome by the a06c/a076 return PCs).',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output (tile/palette meaning of the port values is not interpreted).',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion; direct entry at bundled-branch or internal PCs has no native guard (API-level rejection).'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
