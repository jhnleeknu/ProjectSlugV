"""Unpatched card menu push (a29c -> a0a0 -> 38e8/386e -> a1e0 RTS -> c2a8 -> a2b8 -> c2b4 -> JSR a370) native observation.

Native Unicorn M68000 observation of the original ROM, reusing the hardened machinery of the reviewed card child
observer (observe_animation_machine_card_child) and the fade/card observer under it (observe_animation_machine_fade_card):
the BIOS-resume allocation-success chain is re-derived to the a29c stop (A7 holds c2a8 above 2ac2, reached by the JSR at
c2a2), then a29c is executed natively: a29c -> BRA a0a0 (menu push, descriptor scan through 38e8/386e) -> RTS c2a8 ->
LEA e84c8 / JSR a2b8 / RTS -> c2b4 -> c2ba JSR a370.  a370 (the menu frame) is a stop boundary only (never executed;
accepted only when reached by the JSR at c2ba, or by the a0c2 RTS that pops a pushed 0000a370).  9b58 (nested push),
38c8 and 38e2 (TRAP #f) are likewise stop boundaries accepted only directly after the instruction that transfers there.
Boundary conditions are fresh conditions from the recorded a29c stop output with declared host changes (initial
registers, RAM fixture writes, PC redirect, bank state), each recorded in the step / fixture record.
No SR reads, ROM patches, stubs, register injection after execution begins, stack masking or expected-register
injection.  This is a native observation, not a C++ comparison.
"""
import copy
import json
from pathlib import Path
import sys
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_card_child as cc
import observe_animation_machine_fade_card as fc
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_menu_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-card-menu-push-contract.md'
sha=fc.sha
A29C,A0A0,A370,B9B58,T38C8,T38E2=0xa29c,0xa0a0,0xa370,0x9b58,0x38c8,0x38e2
NEW_RANGES=((0xa0a0,0xa1e2),(0xa29c,0xa2be),(0x386e,0x3902),(0xc2a8,0xc2c0))
RANGES=cc.RANGES+NEW_RANGES
BLOCKS=(0xa29c,0xa0a0,0xa0c2,0xa0c4,0xa0f8,0xa104,0xa158,0xa15e,0xa166,0xa17e,0xa184,0xa18a,0xa18c,0xa198,0xa1a6,0xa1ac,0xa1ae,0xa1ba,0xa1be,0xa1cc,0xa1d0,
    0x386e,0x3878,0x387a,0x38a4,0x38a6,0x38b6,0x38be,0x38ca,0x38ce,0x38e4,0x38e8,0x38ee,0x38f4,0x38fa,0x38fe,0xc2a8,0xa2b8,0xa2bc,0xc2b4,0xc2ba)
BLOCK_SET=frozenset(BLOCKS)
STOPS=(A370,B9B58,T38C8,T38E2)
NEW_BOUNDARIES=(0xa29c,0xa0a0,0xa0c2,0xa0c4,0xa0f8,0xa104,0xa158,0xa198,0xa1d0,0x38e8,0xc2a8,0xa2b8,0xc2b4,0xc2ba)
BOUNDARIES=cc.BOUNDARIES+NEW_BOUNDARIES
KEY_PCS=cc.KEY_PCS+BLOCKS+STOPS
# The fade/card observer reads these module globals when it prepares a CPU / stores a phase: extend them for this unit.
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
RUNS=dict(n=0)
SEARCH=[]
_run_condition=fc.run_condition
def counted_run_condition(program,spec,continuous):
    RUNS['n']+=1;return _run_condition(program,spec,continuous)
fc.run_condition=counted_run_condition
u32=cc.u32
DESC,STRS=0x10b000,0x10d000
REC=0x107efe                 # first menu record: -f2 = 107f0e after a29c, minus 0x10
M2,F2,E2,EA,E6=0x107f0e,0x107f0e,0x107f12,0x107f16,0x107f1a


# ----------------------------------------------------------------------------------
# Stop evidence: a boundary stop is accepted only directly after the transferring instruction
# ----------------------------------------------------------------------------------
def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if not (pc==p['step_stop_pc'] and pc in STOPS):
        return cc.stop_evidence(program,p)
    assert len(pcs)>=2 and pcs[-1]==pc,(p['label'],pcs[-3:])
    prev=pcs[-2];ev=dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True)
    ram=p['ram_after']
    if pc==A370:
        if prev==0xc2ba:
            assert program[0xc2ba:0xc2c0].hex()=='4eb90000a370',(p['label'],)
            assert u32(ram,o['a7'])==0xc2c0,(p['label'],hex(u32(ram,o['a7'])))
            ev['reached_from']='JSR a370 at c2ba (bytes 4eb90000a370); return LONG c2c0 on the stack at A7=%x'%o['a7']
        else:
            assert prev==0xa0c2 and program[0xa0c2:0xa0c4].hex()=='4e75',(p['label'],hex(prev))
            assert u32(ram,o['a7']-4)==A370,(p['label'],hex(u32(ram,o['a7']-4)))
            ev['reached_from']='RTS at a0c2 (menu stack overflow) popped the pushed old -ee LONG 0000a370 (at %x, A7 now %x)'%(o['a7']-4,o['a7'])
    elif pc==B9B58:
        assert prev==0xa0fc and program[0xa0fc:0xa100].hex()=='6100fa5a',(p['label'],hex(prev))
        assert u32(ram,o['a7'])==0xa100,(p['label'],hex(u32(ram,o['a7'])))
        ev['reached_from']='BSR 9b58 at a0fc (bytes 6100fa5a); return LONG a100 on the stack at A7=%x'%o['a7']
    elif pc==T38C8:
        assert prev==0x38c4 and program[0x38c0:0x38c8].hex()=='0c43750065000004',(p['label'],hex(prev))
        assert (o['d3']&0xffff)>=0x7500,(p['label'],hex(o['d3']))
        ev['reached_from']='fall-through of BCS.W at 38c4 after CMPI.W #7500,D3 at 38c0 (D3.W=%04x >= 7500); TRAP #f not executed'%(o['d3']&0xffff)
    else:
        assert prev==0x38de and program[0x38da:0x38e2].hex()=='0c43750065000004',(p['label'],hex(prev))
        assert (o['d3']&0xffff)>=0x7500,(p['label'],hex(o['d3']))
        ev['reached_from']='fall-through of BCS.W at 38de after CMPI.W #7500,D3 at 38da (D3.W=%04x >= 7500); TRAP #f not executed'%(o['d3']&0xffff)
    return ev


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def store(prefix,phases):
    rows=fc.store(prefix,phases)
    for row,p in zip(rows,phases):row['stop_evidence']=p['stop_evidence']
    return rows


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


# ----------------------------------------------------------------------------------
# Declared RAM fixtures
# ----------------------------------------------------------------------------------
def ram_bytes(address,data,why):
    """Declared host RAM writes of a byte string, in aligned chunks of at most 4 bytes."""
    out=[];i=0
    while i<len(data):
        a=address+i;n=len(data)-i
        size=4 if a%4==0 and n>=4 else 2 if a%2==0 and n>=2 else 1
        out.append(fc.ram_write(a,size,int.from_bytes(data[i:i+size],'big'),why));i+=size
    return out


def layout(title,items,minw=0,minh=0,flags=0,desc=DESC,strs=STRS,odd=False):
    """Descriptor + string fixture. title/items entries: bytes (placed in the string area), int (raw pointer) or None (0).
    items: list of string|(string,callback,word)."""
    pool=bytearray(b'\x00' if odd else b'');placed={}
    def ptr(x):
        if x is None:return 0
        if isinstance(x,int):return x
        if x not in placed:placed[x]=strs+len(pool);pool.extend(x+b'\x00')
        return placed[x]
    head=bytearray(0x10)
    head[0:4]=ptr(title).to_bytes(4,'big');head[4]=minw;head[5]=minh;head[0xe:0x10]=flags.to_bytes(2,'big')
    body=bytearray()
    for item in items:
        s,cb,w=item if isinstance(item,tuple) else (item,0,0)
        body+=ptr(s).to_bytes(4,'big')+cb.to_bytes(4,'big')+w.to_bytes(2,'big')
    body+=(0xffffffff).to_bytes(4,'big')
    writes=ram_bytes(desc,bytes(head+body),'declared descriptor fixture')
    if pool:writes+=ram_bytes(strs,bytes(pool),'declared string fixture')
    return writes


# ----------------------------------------------------------------------------------
# Independent model of the contract (execution semantics written from the ROM bytes) to cross-check the native results
# ----------------------------------------------------------------------------------
class Trap(Exception):
    def __init__(self,pc,regs):Exception.__init__(self);self.pc=pc;self.regs=regs


def model_menu(rb,r32,a0,regs):
    """Registers/record after the a29c..a1e0 path for descriptor a0 (reads through rb/r32 in live memory order). Raises Trap."""
    r={k:regs[k] for k in ('d0','d1','d2','d3','d7')}
    def setb(name,v):r[name]=(r[name]&0xffffff00)|(v&0xff)
    def setw(name,v):r[name]=(r[name]&0xffff0000)|(v&0xffff)
    def scan(a):
        count=0
        def raw():
            nonlocal a
            b=rb(a);a=(a+1)&0xffffffff;return b
        def read_d2():
            b=raw();setb('d2',b);return b
        while True:
            d2=read_d2()
            while d2==0x5c:
                b=read_d2()
                if b==0x6e:
                    setw('d3',r['d3']+1)
                    if (r['d3']&0xffff)>=0x7500:raise Trap(T38C8,dict(r))
                    setw('d0',r['d3'])
                elif b==0x72:setw('d0',r['d3'])
                elif b==0x63:
                    r['d1']=(r['d1']&0xffff0000)|(r['d1']&0xff00);setb('d1',raw())
                elif b==0x70:
                    r['d1']=(r['d1']&0xffff0000)|(r['d1']&0xff);setb('d7',raw());setb('d7',r['d7']&0xf);setw('d7',(r['d7']&0xffff)<<8);setw('d1',(r['d1']&0xffff)|(r['d7']&0xffff))
                elif b==0x6c:
                    r['d3']=0;setb('d3',raw());setw('d3',(r['d3']&0xffff)<<5);setb('d3',(r['d3']&0xff)+raw());setw('d3',(r['d3']&0xffff)+0x7000)
                    if (r['d3']&0xffff)>=0x7500:raise Trap(T38E2,dict(r))
                    setw('d0',r['d3'])
                else:d2=b;break          # unknown escape: D2 holds the BYTE and RTS (counted if nonzero)
                d2=read_d2()
            if d2==0:return count
            count+=1
    rec={9:regs['d0']&0xff,0xa:regs['d1']&0xff,0xb:rb(a0+4),0xc:rb(a0+5),6:0}
    r['d0']=0
    title=r32(a0)
    if title!=0:setw('d0',scan(title))
    maxw=r['d0']&0xffff;a3=a0+0x10;count=0
    while True:
        p=r32(a3)
        if p==0xffffffff:break
        if p not in (0,0xfffffffe):
            setw('d0',scan(p))
            if (r['d0']&0xffff)>maxw:maxw=r['d0']&0xffff
        count=(count+1)&0xff;a3+=10
    rec[6]=count
    flags=(rb(a0+0xe)<<8|rb(a0+0xf))&0xe
    r['d0']=2 if flags==0 else 0
    setw('d0',(r['d0']&0xffff)+2);setw('d0',(r['d0']&0xffff)+maxw)
    if (r['d0']&0xff)>rec[0xb]:rec[0xb]=r['d0']&0xff
    setb('d0',count);setw('d0',(r['d0']&0xffff)+2)
    if (r['d0']&0xff)>rec[0xc]:rec[0xc]=r['d0']&0xff
    return dict(regs=r,rec=rec,count=count,maxw=maxw)


def reader(program,ram,bank):
    def rb(a):
        a&=0xffffffff
        if a<fc.RAM:return program[a]
        if a<0x200000:return ram[a&0xffff]
        if a<fc.PVC:return program[bank+a-0x200000]
        raise KeyError(hex(a))
    def r32(a):return int.from_bytes(bytes(rb(a+i) for i in range(4)),'big')
    return rb,r32


def check_model(program,spec,meta,split):
    """Native result vs the contract model for conditions that run to a370 or to a TRAP boundary."""
    fx=spec['fixture'];ram=bytearray(fx['ram'])
    first=spec['steps'][0]
    for c in first['changes']:
        if c['kind']=='ram':
            for i,b in enumerate(c['value'].to_bytes(c['size'],'big')):ram[(c['address']+i)&0xffff]=b
    rb,r32=reader(program,ram,fx['bank_state'][0])
    a0=fx['regs']['a0'];result=dict(label=spec['label'])
    end=split[-1];o=end['outgoing']
    try:
        m=model_menu(rb,r32,a0,fx['regs']);expected_stop=A370
        regs=m['regs']
    except Trap as t:
        m=None;expected_stop=t.pc;regs=t.regs
    assert o['pc']==expected_stop,(spec['label'],hex(o['pc']),hex(expected_stop))
    for k in ('d0','d1','d2','d3','d7'):
        assert o[k]==regs[k],(spec['label'],k,hex(o[k]),hex(regs[k]))
    result.update(model_stop=hex(expected_stop),model_regs={k:hex(v) for k,v in regs.items()})
    if m is not None:
        a2=meta.get('record',REC);after=end['ram_after']
        got={off:after[(a2+off)&0xffff] for off in (4,6,7,8,9,0xa,0xb,0xc,0xd,0xe,0xf)}
        want=dict(m['rec']);want.update({4:0,7:0,8:0,0xd:3,0xe:0xff,0xf:0})
        assert got==want,(spec['label'],got,want)
        assert u32(after,a2)==a0 and u32(after,0x107f16)==0xe84c8,(spec['label'],hex(u32(after,a2)),hex(u32(after,0x107f16)))
        result.update(record_address=hex(a2),record={hex(k):v for k,v in sorted(got.items())},count=m['count'],max_width=m['maxw'])
    return result


# ----------------------------------------------------------------------------------
# Searching existing ROM data for fixtures (deterministic)
# ----------------------------------------------------------------------------------
def cstring_len(program,bank,addr,limit=64):
    n=0
    while n<limit:
        a=addr+n
        if a<0x100000:b=program[a]
        elif 0x200000<=a<fc.PVC:b=program[bank+a-0x200000]
        else:return None
        if b==0x5c:return None
        if b==0:return n
        n+=1
    return None


def find_low_word_pointers(program,bank):
    """Pointers whose low WORD is 0000/fffe/ffff (sign-extended CMPA.W compare traps) with a short plain C string behind them."""
    found={}
    for low in (0xffff,0xfffe,0x0000):
        for n in range(0,0x40):
            a=(n<<16)|low
            if a==0:continue
            if a>=fc.PVC:break
            if 0x100000<=a<0x200000:continue
            length=cstring_len(program,bank,a,48)
            if length is not None and 1<=length<=40:found.setdefault(low,[]).append((a,length))
    return found


def find_bank_strings(program):
    """Logical bank addresses whose bytes form a short plain string in BOTH bank 200000 and 300000 but with different content."""
    out=[]
    for a in range(0x200000,0x2fe000-0x80):
        l2=cstring_len(program,0x200000,a);l3=cstring_len(program,0x300000,a)
        if l2 is not None and l3 is not None and 3<=l2<=24 and 3<=l3<=24 and program[0x200000+a-0x200000:0x200000+a-0x200000+l2]!=program[0x300000+a-0x200000:0x300000+a-0x200000+l3]:
            out.append((a,l2,l3))
            if len(out)>=4:break
    return out


def scan_bank_descriptors(program,bank,max_items=40):
    """Search the whole bank window (CPU 200000..2fdfff, physical = bank + offset) for a terminating descriptor: title LONG (0 or a pointer to a plain
    string readable in fixed ROM / this bank), then LONG string pointers at +10 step 10 (0, fffffffe or a readable plain string) until ffffffff within max_items."""
    def mem(a):
        if a<0x100000:return program[a]
        if 0x200000<=a<fc.PVC:return program[bank+a-0x200000]
        return None
    def u32(a):
        if a<0x100000 or 0x200000<=a<fc.PVC-3:
            return int.from_bytes(bytes(mem(a+i) for i in range(4)),'big') if (a<0x100000-3 or a>=0x200000) else None
        return None
    cache={}
    def plain(a):
        if a in cache:return cache[a]
        n=0;ok=False
        while n<80:
            b=mem(a+n) if (a+n<0x100000 or 0x200000<=a+n<fc.PVC) else None
            if b is None or b==0x5c:break
            if b==0:ok=True;break
            n+=1
        cache[a]=ok;return ok
    candidates=[];examined=0
    for a in range(0x200000,fc.PVC-0x40,2):
        examined+=1;t=u32(a)
        if t is None or (t!=0 and not plain(t)):continue
        for k in range(max_items):
            q=u32(a+0x10+10*k)
            if q is None:break
            if q==0xffffffff:candidates.append(dict(descriptor=hex(a),title=hex(t),items=k));break
            if q not in (0,0xfffffffe) and not plain(q):break
    return dict(bank=hex(bank),offsets_examined=examined,max_items=max_items,terminating_descriptors_found=len(candidates),candidates=candidates[:8])


def find_bank_only(program,bank):
    out=[]
    for a in range(0x200000+0x4000,0x2fe000-0x80):
        l=cstring_len(program,bank,a)
        if l is not None and 8<=l<=20:
            out.append((a,l))
            if len(out)>=3:break
    return out


# ----------------------------------------------------------------------------------
# Conditions
# ----------------------------------------------------------------------------------
def build_specs(program,connected,end,end_label,chain_offset):
    specs=[];models={}
    a2=lambda d:('entry',d)
    def with_checkpoints(spec):
        probe=copy.deepcopy(spec)
        for s in probe['steps']:s['checkpoints']=[]
        phases=fc.run_condition(program,probe,True)
        for index,step in enumerate(spec['steps']):
            if index>=len(phases):break
            pcs=phases[index]['pcs'];order=[]
            for pc in pcs[1:]:
                if pc in BLOCK_SET and pc not in order:order.append(pc)
            step['checkpoints']=order
        return spec
    def make(label,group,prov,changes=(),regs=None,stop=A370,delta=0,guard=None,extra_steps=(),fixture_edit=None,model=False,meta=None,entry_pc=None):
        change_list=list(changes)
        if entry_pc is not None:change_list.insert(0,fc.pc_to(entry_pc,'declared direct entry: PC redirected from the a29c stop output'))
        step=dict(label='menu-%s'%label,changes=change_list,stop_pc=stop,checkpoints=[],a7=('entry',delta))
        extra=dict(guarded=True,guard=guard) if guard is not None else {}
        spec=cc.fresh_spec(connected,end,end_label,label,[step]+list(extra_steps),group,prov,regs=regs,**extra)
        if fixture_edit:fixture_edit(spec['fixture'])
        with_checkpoints(spec);specs.append(spec)
        if model and guard is None:models[label]=dict(meta or {})
        return spec
    D=lambda **kw:dict(a0=DESC,**kw)
    # ---- connected: card child a29c stop output (host change: none) -> a370 stop; compared with the chain run
    chain_step=dict(label='menu-a29c-to-a370',changes=[],stop_pc=A370,checkpoints=[],a7=('entry',0))
    connected_spec=cc.fresh_spec(connected,end,end_label,'connected-a29c-to-a370',[chain_step],'connected',
        'fresh CPU started from the recorded real card child a29c stop output (PC a29c, A7 holds c2a8 above 2ac2); no host change; natural flow a29c -> a0a0 -> 38e8/386e -> RTS c2a8 -> a2b8 -> c2b4 -> JSR a370 stop',chain_offset=chain_offset)
    with_checkpoints(connected_spec);models['connected-a29c-to-a370']={}
    # ---- descriptor fixtures (A0 = RAM descriptor; declared initial A0 register and declared RAM writes)
    base_prov='fresh state from the a29c stop output; declared initial A0=%x (RAM descriptor) and declared RAM fixture writes (descriptor %x, strings %x); '%(DESC,DESC,STRS)
    def desc(label,title,items,prov,minw=0,minh=0,flags=0,regs=None,odd=False,group='menu-descriptor',**kw):
        r=D();r.update(regs or {})
        make(label,group,base_prov+prov,layout(title,items,minw,minh,flags,odd=odd),regs=r,model=True,**kw)
    S=lambda n:b'A'*n
    desc('desc-title-present',b' DATA MENU ',[b' YES ',b' NO '],'title string present')
    desc('desc-title-wider-than-items',b' A VERY LONG MENU TITLE ',[b' A ',b' B '],'title wider than every item')
    desc('desc-title-narrower-than-items',b'T',[b' ITEM ONE ',b' ITEM TWO '],'title narrower than items')
    desc('desc-no-title-two-items',None,[b' ONE ',b' TWO '],'title pointer 0')
    for flags in (0x0002,0x0001,0xfff1,0x0008,0x000e):
        desc('desc-flags-%04x'%flags,None,[b' ABCD '],'WORD e(A3)=%04x (AND #e %s)'%(flags,'nonzero -> D0=0' if flags&0xe else 'zero -> D0=2'),flags=flags)
    # computed width = 2+2+len(' ABCD ')=10 (flags zero), height = 2+1 = 3
    for name,minw in (('bigger',0x30),('smaller',0x01),('equal',10),('plus1',11),('minus1',9),('ff',0xff)):
        desc('desc-minw-%s'%name,None,[b' ABCD '],'min width BYTE 4(A0)=%02x (computed width 10)'%minw,minw=minw)
    for name,minh in (('bigger',0x20),('smaller',0x01),('equal',3),('plus1',4),('minus1',2),('ff',0xff)):
        desc('desc-minh-%s'%name,None,[b' ABCD '],'min height BYTE 5(A0)=%02x (computed height 3)'%minh,minh=minh)
    desc('desc-minw-minh-both-bigger',b'TT',[b' ABCD ',b' EF '],'min width 40 and height 30 both bigger',minw=0x40,minh=0x30)
    desc('desc-width-wrap-253',None,[S(253)],'string of 253 chars: width 2+2+253=0x101 (BYTE compare wraps to 01)')
    desc('desc-width-wrap-252',None,[S(252)],'string of 252 chars: width 0x100 (BYTE compare 00)')
    desc('desc-width-wrap-256-flags2',None,[S(256)],'string of 256 chars with e bit set: width 0+2+256=0x102',flags=0x0002)
    desc('desc-width-wrap-253-minw-ff',None,[S(253)],'string of 253 chars, min width ff: BYTE compare 01<=ff keeps ff',minw=0xff)
    desc('desc-width-254-high-byte-d0',None,[S(254),b' B ',b' C '],'width 0x102 puts 01 in D0.W high byte; MOVE.B 6(A2),D0 replaces only the low byte (count 3)')
    one=b' X '
    desc('desc-count-wrap-255',None,[one]*255,'255 items (BYTE count 6(A2)=ff, height D0.B 01)')
    desc('desc-count-wrap-256',None,[one]*256,'256 items (BYTE count wraps to 00)')
    desc('desc-count-wrap-257',None,[one]*257,'257 items (BYTE count wraps to 01)')
    desc('desc-null-and-separator',None,[b' A ',None,0xfffffffe,b' B '],'items: string, null (0), separator (fffffffe), string: null/separator items count in 6(A2) and add no width')
    desc('desc-only-null-items',b' T ',[None,None],'two null items only')
    desc('desc-only-separators',None,[0xfffffffe,0xfffffffe,0xfffffffe],'three separator items only')
    desc('desc-zero-items-title',b' TITLE ',[],'terminator immediately at +10 (zero items) with a title')
    desc('desc-zero-items',None,[],'terminator immediately at +10, no title')
    desc('desc-items-ascending-width',None,[b'A',b'BB',b'CCCC',b'DDDDDDDD'],'item widths ascending (each replaces the stacked maximum)')
    desc('desc-items-descending-width',None,[b'DDDDDDDD',b'CCCC',b'BB',b'A'],'item widths descending (maximum kept)')
    desc('desc-items-equal-width',None,[b'AAAA',b'BBBB',b'CCCC'],'item widths equal (BLS keeps)')
    desc('desc-empty-strings',b'',[b'',b'',b'X'],'empty title/item strings (first BYTE 0)')
    desc('desc-odd-string-addresses',b'ODD',[b'AB',b'CDE'],'string pointers at odd RAM addresses (byte reads) with an even descriptor',odd=True)
    desc('desc-callback-word-fields',None,[(b' A ',0xdeadbeef,0x1234),(b' B ',0x12345678,0xffff)],'item callback LONG and WORD fields are not read')
    low=find_low_word_pointers(program,0x200000)
    ptr_ffff=low[0xffff][0][0];ptr_fffe=low[0xfffe][0][0];ptr_0000=low[0x0000][0][0]
    desc('desc-ptr-lowword-ffff',None,[ptr_ffff],'item pointer %06x: low WORD ffff, but CMPA.W #ffff compares the sign-extended ffffffff so this is a real string (len %d)'%(ptr_ffff,low[0xffff][0][1]))
    desc('desc-ptr-lowword-fffe',None,[ptr_fffe],'item pointer %06x: low WORD fffe is not the separator fffffffe (len %d)'%(ptr_fffe,low[0xfffe][0][1]))
    desc('desc-ptr-lowword-0000',ptr_0000,[ptr_0000],'title and item pointer %06x: low WORD 0000 is not null (CMPA.W #0 compares the full LONG; len %d)'%(ptr_0000,low[0x0000][0][1]))
    # ---- strings with escapes (declared initial D1/D3/D7 as needed; the D3/D1 effects are visible in the outgoing registers)
    def esc(label,string,prov,regs=None,title=None,items=None,**kw):
        r=D();r.update(regs or {})
        make(label,'menu-string',base_prov+prov,layout(title,[string] if items is None else items),regs=r,model=True,**kw)
    esc('esc-n',b'A\\nBC','escape \\n: D3.W+1 (D3=abcd0010 -> abcd0011), D0.W<-D3; chars counted without the escape',regs=dict(d3=0xabcd0010))
    esc('esc-n-twice-two-items',b'\\n\\nX','two \\n in one string and one more in the second item',items=[b'\\n\\nX',b'Y\\nZ'],regs=dict(d3=0x00000100))
    esc('esc-r',b'A\\rB','escape \\r: D0.W<-D3 only',regs=dict(d3=0x00005a5a,d0=0x11110004))
    esc('esc-c',b'\\cXYZ','escape \\c: D1.W&=ff00 then D1.B<-X (D1=12345678 -> 12345658)',regs=dict(d1=0x12345678))
    esc('esc-p',b'\\p7AB','escape \\p: D1.W&=ff, D7.B<-7&f, D7.W<<8, D1.W|=D7.W (D1=12345678, D7=80700000)',regs=dict(d1=0x12345678,d7=0x80700000))
    esc('esc-p-high-nibble',b'\\pZ!','escape \\p with a nibble above 9 (5a & f = a) and non-zero D7 high word',regs=dict(d1=0xffffffff,d7=0xffffffff))
    esc('esc-l',b'\\l\x05\x80x','escape \\l: D3=0, D3.B=05, D3.W<<5, D3.B+=80 (BYTE add), +7000 -> 7020 below 7500',regs=dict(d3=0xffff1234))
    esc('esc-l-carry-below',b'\\l\x27\xffx','escape \\l (27,ff): BYTE add carry stays in the byte (04df), +7000 = 74df < 7500',regs=dict(d3=0x12345678))
    esc('esc-l-carry-to-zero',b'\\l\x27\x20x','escape \\l (27,20): BYTE add wraps to 00 (0400), +7000 = 7400 < 7500',regs=dict(d3=0))
    esc('esc-unknown',b'A\\xB','unknown escape \\x: RTS with D2=x, counted as a character (A, x, B = 3)')
    esc('esc-trailing-backslash',b'AB\\','trailing backslash before the terminator: D2=0 ends the string (count 2)')
    esc('esc-c-arg-nul',b'\\c\x00QR','\\c whose argument BYTE is the NUL: consumed as D1.B, the scan continues past it (count 2: Q, R)',regs=dict(d1=0x00005555))
    esc('esc-n-d3-ffff-wrap',b'\\nX','\\n with D3.W=ffff: ADDQ.W wraps to 0000 (high word abcd kept), below 7500, no stop',regs=dict(d3=0xabcdffff))
    esc('esc-n-d3-74fe-pass',b'\\nX','\\n with D3.W=74fe: 74ff < 7500, no stop',regs=dict(d3=0x000074fe))
    esc('esc-mixed-title-and-items',b'\\p3\\cA!',' mixed escapes in title and items',title=b'T\\r\\n\\cQ',items=[b'\\p3\\cA!',b'\\lAB'.replace(b'AB',b'\x01\x02')+b'.'],regs=dict(d1=0x12345678,d3=0x0000003c,d7=0x00001234))
    # ---- TRAP boundaries
    def trap(label,string,stop,delta,prov,title=None,items=None,regs=None):
        r=D();r.update(regs or {})
        make(label,'menu-boundary-stop',base_prov+prov,layout(title,[string] if items is None else items),regs=r,stop=stop,delta=delta,model=True)
    trap('trap-38c8-d3-74ff-item',b'A\\nB',T38C8,-16,'\\n with D3.W=74ff -> 7500: stop 38c8 (TRAP #f not executed), inside an item string',regs=dict(d3=0x74ff))
    trap('trap-38c8-d3-abcd74ff-item',b'A\\nB',T38C8,-16,'\\n with D3=abcd74ff (high word ignored) -> stop 38c8',regs=dict(d3=0xabcd74ff))
    trap('trap-38c8-d3-7500-item',b'\\n',T38C8,-16,'\\n with D3.W=7500 -> 7501: stop 38c8',regs=dict(d3=0x7500))
    trap('trap-38c8-d3-8000-item',b'\\n',T38C8,-16,'\\n with D3.W=8000 -> 8001 (unsigned >= 7500): stop 38c8',regs=dict(d3=0x8000))
    trap('trap-38c8-in-title',b'X',T38C8,-14,'\\n with D3.W=74ff inside the TITLE string (one call level less): stop 38c8',title=b'\\nT',items=[b'X'],regs=dict(d3=0x74ff))
    trap('trap-38c8-second-item',b'X',T38C8,-16,'first item normal, second item \\n with D3.W=74ff: stop 38c8',items=[b' OK ',b'\\nX'],regs=dict(d3=0x74ff))
    trap('trap-38e2-l-7500',b'\\l\x28\x00x',T38E2,-16,'\\l (28,00): 0500+7000 = 7500: stop 38e2')
    trap('trap-38e2-l-byte-add-wrap',b'\\l\x41\xf0x',T38E2,-16,'\\l (41,f0): D3.W=0820, BYTE add f0 -> 0810, +7000 = 7810 >= 7500: stop 38e2')
    trap('trap-38e2-in-title',b'X',T38E2,-14,'\\l (28,00) inside the title string: stop 38e2',title=b'\\l\x28\x00',items=[b'X'])
    trap('trap-38e2-after-d1-escapes',b'\\c1\\p2\\l\x7f\x7fx',T38E2,-16,'\\c and \\p before an overflowing \\l (7f,7f): D1 modified before the stop',regs=dict(d1=0x12345678))
    # ---- banked reads (bank 200000 is the current bank of the a29c state: ff8=a0 ff9=1000)
    b2=find_bank_only(program,0x200000);b23=find_bank_strings(program)
    SEARCH.extend([scan_bank_descriptors(program,0x200000),scan_bank_descriptors(program,0x300000)])
    bt,bi=b2[0][0],b2[1][0]
    desc('bank-strings-title-and-items',bt,[bi,bt],'title and item pointers into the banked area (%x, %x) read through the CURRENT bank (200000: physical offset == CPU address); RAM descriptor'%(bt,bi),group='menu-bank')
    sa=b23[0][0]
    desc('bank-200000-address-differs-from-300000',sa,[sa],'title/item pointer %x read in bank 200000 (len %d); same address in the next condition is read through bank 300000 (len %d)'%(sa,b23[0][1],b23[0][2]),group='menu-bank')
    def to_300000(fx):
        pvc=bytearray(fx['pvc']);pvc[0x1ff0:0x1ff4]=(0x0000).to_bytes(2,'big')+(0x2000).to_bytes(2,'big');fx['pvc']=bytes(pvc);fx['bank_state']=(0x300000,0xa0,0x2000)
    desc('bank-300000-same-address',sa,[sa],'declared bank state 300000 (modeled ff8=00a0 ff9=2000, raw PVC words 2ffff0/2ffff2 = 0000/2000 consistent with pvc_bank_update) at the fresh start; title/item pointer %x read through bank 300000'%sa,group='menu-bank',fixture_edit=to_300000)
    sb=b2[2][0]
    desc('bank-string-item-only',None,[sb],'single banked string pointer %x'%sb,group='menu-bank')
    # ---- entry A5 != 108000 (previous A5 used by a29c's -ea/-e6 stores and by a0a0's -ee push)
    def a5(label,value,prov,guard=None,**kw):
        r=D(a5=value);m=[fc.ram_write(value-0xee,4,0x12345678,'declared old -ee(A5) LONG read by a0a0 at its entry')] if guard is None else []
        make(label,'menu-A5',base_prov+prov,layout(b' T ',[b' A ',b' BB '])+m,regs=r,guard=guard,model=True,**kw)
    a5('entry-A5-109000',0x109000,'declared initial A5=109000 (RAM): a29c writes 3650 to 108f16 and 00 to 108f1a (old A5), a0a0 pushes 109000-ee (declared 12345678) and later restores it into -ee(108000)')
    a5('entry-A5-108002',0x108002,'declared initial A5=108002 (even, near 108000)')
    a5('entry-A5-1ffff0',0x1ffff0,'declared initial A5=1ffff0 (RAM top: -ea/-e6/-ee relative to the old A5 stay below it)')
    # ---- direct a0a0 entries (declared PC change from the a29c stop output; A0/D0/D1 are the card child values c188/4/4)
    def direct(label,prov,writes,stop=A370,delta=0,guard=None,regs=None,**kw):
        make(label,'menu-direct-a0a0','fresh state from the a29c stop output; declared PC=a0a0 (a29c is skipped) and declared RAM writes: '+prov,writes,regs=regs,stop=stop,delta=delta,guard=guard,entry_pc=A0A0,**kw)
    W=lambda a,v,why:fc.ram_write(a,4,v,why)
    direct('direct-a0a0-baseline','-f2(A5)=107f0e as a29c would set it',[W(F2,0x107f0e,'declared -f2')],model=True)
    direct('direct-a0a0-overflow-a370','-f2=107e14 (A2-10 = 107e04 < 107e0e) and old -ee=0000a370: a0c2 RTS pops it -> stop a370',[W(F2,0x107e14,'declared -f2 near the menu stack bottom'),W(E2,0xa370,'declared old -ee LONG (pushed by a0a0, popped by the RTS)')])
    direct('direct-a0a0-overflow-107e1c','-f2=107e1c (A2 = 107e0c just below 107e0e) and old -ee=0000a370',[W(F2,0x107e1c,'declared -f2'),W(E2,0xa370,'declared old -ee')])
    direct('direct-a0a0-first-valid-slot-nested-9b58','-f2=107e1e (A2 = 107e0e exactly: BCC taken, last slot) -> A2+10 < 107f0e -> BSR 9b58 stop',[W(F2,0x107e1e,'declared -f2')],stop=B9B58,delta=-20)
    direct('direct-a0a0-nested-9b58','-f2=107efe (menu already pushed once) -> BSR 9b58 stop',[W(F2,0x107efe,'declared -f2')],stop=B9B58,delta=-20)
    direct('direct-a0a0-record-aliases-menu-variables-107f1e','-f2=107f1e (A2 after push = 107f0e = -f2 itself, A2+10=107f1e >= 107f0e -> a104, no BSR): the record at 107f0e overlaps -f2/-ee/-ea(A5) and is written through the live bus in program order',[W(F2,0x107f1e,'declared -f2')])
    # ---- natural nested push: after the first push ends at a370 the live -f2 is 107efe; a declared PC=a0a0 re-entry then reaches 9b58
    re_entry=dict(label='menu-re-entry-a0a0-nested',changes=[fc.pc_to(A0A0,'declared re-entry PC=a0a0 from the a370 stop output; -f2=107efe is the live value left by the first push')],stop_pc=B9B58,checkpoints=[],a7=('entry',-20))
    make('sequence-second-push-nested-9b58','menu-direct-a0a0','fresh state from the a29c stop output; first step the natural a29c -> a370; second step declared PC=a0a0 only: the live -f2=107efe makes the second push nested -> stop 9b58',
        extra_steps=[re_entry],model=False)
    # ---- guards (native partial effects; the C++ implementation must later error with a full rollback)
    guard_prov='fresh state from the a29c stop output with '
    make('guard-A5-in-ROM','guard',guard_prov+'declared initial A5=001000 (ROM): a29c MOVE.L #3650,-ea(A5) writes ROM address f16',regs=dict(a5=0x001000),
        guard=dict(problem='unmapped_or_protected',pc=A29C,address=0x1000-0xea,size=4))
    make('guard-A5-in-bank','guard',guard_prov+'declared initial A5=200100 (read-only bank area): a29c LONG write to 200016 is refused',regs=dict(a5=0x200100),
        guard=dict(problem='unmapped_or_protected',pc=A29C,address=0x200100-0xea,size=4))
    make('guard-odd-descriptor-A0','guard',base_prov+'declared initial A0=%x (odd): BYTE reads 4(A0)/5(A0) succeed, MOVEA.L (A3),A0 at a14e reads an odd LONG'%(DESC+1),layout(b' T ',[b' A ']),regs=dict(a0=DESC+1),
        guard=dict(problem='unsupported_odd_data_access',pc=0xa14e,address=DESC+1,size=4,access='read'))
    make('guard-odd-A7','guard',guard_prov+'declared initial A7=1feff9 (odd): a0a0 MOVE.L -ee(A5),-(A7) pushes to an odd address',regs=dict(a7=0x1feff9),
        guard=dict(problem='unsupported_odd_data_access',pc=A0A0,address=0x1feff9-4,size=4,access='write',odd_write_restored=True))
    make('guard-odd-A2-record','guard',guard_prov+'declared PC=a0a0 and -f2=107f1f (odd): A2 = 107f0f, a104 MOVE.L A0,(A2) writes an odd LONG',[W(F2,0x107f1f,'declared -f2 (odd)')],entry_pc=A0A0,
        guard=dict(problem='unsupported_odd_data_access',pc=0xa110,address=0x107f0f,size=4,access='write',odd_write_restored=True))
    make('guard-overflow-rts-unsupported-target','guard',guard_prov+'declared PC=a0a0, -f2=107e14 and old -ee=00001000: the a0c2 RTS pops 00001000 (not a370)',[W(F2,0x107e14,'declared -f2'),W(E2,0x1000,'declared old -ee')],entry_pc=A0A0,
        guard=dict(problem='unsupported_code_target',pc=0x1000,target=0x1000))
    make('guard-stop-9b58-never-reached','guard',guard_prov+'stop 9b58 instead of a370: the normal flow reaches a370 (no implementation) and is refused; the 9b58 stop is not accepted',stop=B9B58,
        guard=dict(problem='unsupported_code_target',pc=A370,target=A370))
    make('guard-run-past-a370','guard',guard_prov+'stop c2c0 (the return address) instead of a370: JSR a370 executes (return pushed) and the fetch at a370 is refused',stop=0xc2c0,
        guard=dict(problem='unsupported_code_target',pc=A370,target=A370))
    make('guard-trap-reached-without-stop','guard',base_prov+'D3.W=74ff with \\n but stop a370: the 38c8 TRAP #f is reached and refused (not executed as an exception)',layout(None,[b'A\\nB']),regs=dict(a0=DESC,d3=0x74ff),
        guard=dict(problem='unsupported_TRAP',pc=T38C8,opcode=0x4e4f))
    make('guard-stop-38c8-never-reached','guard',base_prov+'stop 38c8 with a string that has no overflowing escape: a370 is reached first and refused',layout(None,[b'AB']),regs=dict(a0=DESC),stop=T38C8,
        guard=dict(problem='unsupported_code_target',pc=A370,target=A370))
    return connected_spec,specs,models


def ram_diff(a,b,limit=16):
    out=[(i,a[i],b[i]) for i in range(len(a)) if a[i]!=b[i]]
    return dict(count=len(out),first=[dict(address=hex(0x100000+i),a=x,b=y) for i,x,y in out[:limit]])


def crosscheck_card_child(chain_phases,steps_before):
    path=ROOT/'artifacts/animation_machine_card_child_native/observation.json'
    if not path.exists():return dict(performed=False,reason='card_child report not present')
    d=json.loads(path.read_text());r=next(x for x in d['results'] if x['label']=='chain-full-bios-resume-to-a29c')
    last=[q for q in r['phases'] if q['step']==steps_before-1][-1];mine=fc.step_end(chain_phases,steps_before-1)
    ref_ram=next(v for k,v in last['artifacts'].items() if k.endswith('_ram_after.bin'));ref_pvc=next(v for k,v in last['artifacts'].items() if k.endswith('_pvc_after.bin'))
    assert sha(mine['ram_after'])==ref_ram and sha(mine['pvc_after'])==ref_pvc and mine['outgoing']==last['outgoing']
    return dict(performed=True,reference_report=str(path),reference_report_sha256=sha(path.read_bytes()),condition='chain-full-bios-resume-to-a29c',step=steps_before-1,label=last['label'],
        ram_after_sha256=ref_ram,pvc_after_sha256=ref_pvc,outgoing_pc=hex(last['outgoing']['pc']),equal=True)


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]=='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha=='0a4d095f741e151f509364118663c6470e527ea7535c1058e8d93161398a81ea',contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():old.unlink()
    fade_report=ROOT/'artifacts/animation_machine_fade_card_native/observation.json'
    child_report=ROOT/'artifacts/animation_machine_card_child_native/observation.json'
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,ROOT/'docs/analysis/animation-machine-card-child-contract.md',
        ROOT/'docs/analysis/animation-machine-fade-card-contract.md',ROOT/'docs/analysis/animation-machine-map-transfer-contract.md'}
    for report in (fade_report,child_report):
        if report.exists():input_paths.add(report)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    # ---- the card child chain (fade/card machinery, reproduced) to the a29c stop
    connected=fc.connected_fixture(program)
    base_steps=[dict(label='connected-47fe8',changes=[],stop_pc=cc.DISPATCH_RETURN,checkpoints=fc.CONNECTED_CK,a7=('entry',4))]+fc.frame_steps(1,fc.LAST_FRAME)
    prev_chain=dict(label='fade-card-chain-47fe8-to-c00468',group='chain',fixture=connected,steps=base_steps,provenance='fade/card unit chain, re-run to obtain the c00468 stop output')
    fade_split=fc.run_condition(program,prev_chain,False);assert fade_split==fc.run_condition(program,prev_chain,False)
    endlast=fc.step_end(fade_split,fc.LAST_FRAME);assert endlast['outgoing']['pc']==fc.BIOS
    child_steps=cc.connection_steps(0x00)+cc.child_steps();n_child=len(child_steps)
    child_spec=cc.fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'card-child-chain-to-a29c',child_steps,'chain','card child chain (declared BIOS resume) to the a29c stop')
    child_split=fc.run_condition(program,child_spec,False);assert child_split==fc.run_condition(program,child_spec,False)
    a29c_end=fc.step_end(child_split,n_child-1);assert a29c_end['outgoing']['pc']==A29C and a29c_end['outgoing']['a7']==0x1feff8
    end_label='card child chain step %d (stop a29c)'%(n_child-1)
    connected_spec,specs,models=build_specs(program,connected,a29c_end,end_label,n_child)
    # ---- full chain: BIOS-resume allocation success -> ... -> a29c stop -> a29c executed -> a370 stop (one persistent CPU)
    full_steps=child_steps+copy.deepcopy(connected_spec['steps'])
    full=cc.fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'chain-full-bios-resume-to-a370',full_steps,'chain',
        'fade/card native chain output at c00468; declared BIOS return (PC=c37c, A7+=4, 10fdc6=00) + declared 28ae pool/parent fixture; natural parent frame, child c250, declared PC=2ab8 child frame re-entries to the a29c stop (card child unit), then a29c executed without host change through a0a0/38e8/386e/a2b8 to the a370 stop')
    full_split,full_control=run_spec(program,full)
    cross=cc.crosscheck_fade_card(full_split);cross_child=crosscheck_card_child(full_split,n_child)
    all_specs=[full,connected_spec]+specs;cache={full['label']:(full_split,full_control)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;model_checks=[]
    for number,spec in enumerate(all_specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if 'chain_offset' in spec:compared_total+=cc.compare_with_chain(spec,split,full_split)
        if spec['label'] in models and spec.get('guard') is None:
            meta=models[spec['label']]
            if spec['label']!='sequence-second-push-nested-9b58':model_checks.append(check_model(program,spec,meta,split))
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=store('c%03d_split'%number,split),continuous_control=store('c%03d_control'%number,control),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=bool('chain_offset' in spec))
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s'%(number+1,len(all_specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else ''),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,new_ranges=NEW_RANGES,instructions=instructions,boundary_stop_pcs=STOPS,block_starts=BLOCKS,
        stop_rule=dict(a370='accepted only when the previous executed PC is c2ba (JSR bytes 4eb90000a370, return c2c0 on the stack) or a0c2 (RTS that popped 0000a370); a370 itself is never executed',
            b9b58='accepted only directly after the BSR at a0fc (bytes 6100fa5a, return a100 on the stack)',
            t38c8='accepted only when reached by the not-taken BCS.W at 38c4 with D3.W>=7500; TRAP #f never executed',
            t38e2='accepted only when reached by the not-taken BCS.W at 38de with D3.W>=7500; TRAP #f never executed'),
        a29c_bytes=program[0xa29c:0xa2be].hex(),a0a0_bytes=program[0xa0a0:0xa1e2].hex(),s386e_bytes=program[0x386e:0x3902].hex(),c2a8_bytes=program[0xc2a8:0xc2c8].hex()),indent=2)+'\n').encode()
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
    bank_reads=[dict(label=r['label'],bank_reads=sum(p['counts']['bank_reads'] for p in r['phases'])) for r in results if r['group']=='menu-bank']
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,fade_card_crosscheck=cross,card_child_crosscheck=cross_child,child_address=hex(child_addr),
        child_frames=cc.child_frame_summary(full_split,child_addr,full_steps),c266_frame_evidence=cc.c266_evidence(full_split),variant_child_layouts=[],guard_reports=guard_reports,
        contract=dict(path=str(CONTRACT),sha256=contract_sha),contract_model_checks=model_checks,bank_reads_by_condition=bank_reads,bank_descriptor_search=SEARCH,
        covered_PCs=sorted(coverage),new_ranges=NEW_RANGES,block_starts=BLOCKS,boundary_stop_pcs=STOPS,failure=None,rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; the card child chain (declared BIOS resume, declared PC=2ab8 child frame re-entries) is the card child unit re-derived, a29c is then executed natively without host change.',
            'a370 (menu frame), 9b58 (nested push), 38c8/38e2 (TRAP #f) are stop boundaries only: each accepted only directly after the transferring instruction, never executed, not executable ranges; a370 menu frame, 9b58/9e1a/9d3a/a018/3918/3650/e84c8 rendering, callbacks c1c4/bf94 and TRAP #f handling are out of scope.',
            'Boundary conditions are fresh CPUs started from the recorded a29c stop output with declared initial registers, declared RAM fixture writes (descriptor %x, strings %x), declared PC=a0a0 redirects or a declared bank state; nothing is injected after execution begins. The RAM image is the pseudo-random prepared image, so every byte a fixture relies on is a declared write.'%(DESC,STRS),
            'Split checkpoints are the first hit of each contract block start (execution order, entry PC excluded); loop re-visits (386e, a166, ...) are not split again. The continuous run is the control.',
            'No descriptor in the banked area: bank_descriptor_search scans every even CPU address 200000..2fdfff in bank 200000 and in bank 300000 for an existing terminating descriptor (title 0/plain string, <=40 items 0/fffffffe/plain string, ffffffff) and records the result; ROM/bank is read-only so a descriptor cannot be constructed there. Banked reads are therefore covered by title/item string pointers into the current bank (and into bank 300000 via a declared bank state), read through the live bus with bank_at_read/physical_rom_offset.',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path only.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion; direct entry at bundled-branch or internal PCs has no native guard (API-level rejection).'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()
