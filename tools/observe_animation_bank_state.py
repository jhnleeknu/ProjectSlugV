"""Immutable original whole49fc6: 1c01 shadow WORD -> 14/03 actual RTS 3679e -> 30 direct sound waits -> 28.

Native original CPU observation only; no C++ oracle. Each case runs the unpatched canonical program from
49fc6 with A6=100010, so the actual opcode1c field selector01 (ROM WORD[4a76e]=0000) writes the RAM bank
shadow 100010 (-7ff0(A5), A5=108000) without any ROM patch. The actual opcode14 selector03 reads ROM
LONG[4a50c]=0003679e and JSRs the actual RTS; 4a43e restores the pushed shadow WORD and writes the PVC pair.
Opcode30 then calls 3af8; pending runs stop at the actual 3aea byte-queue wait after two equal head visits
and resume on the same Unicorn context. Between phases the host writes only recorded RAM/external changes
(poison, including the RAM shadow, and an explicit byte-queue head release). Nothing patches code or
registers after begin; SR is written before A7 at preparation and read only after RTS to RETURN (carry).

The selected bank is NOT read from the CPU or a device: it is derived from the actual ordered PVC port
writes through the pinned MAME formula (neogeo.cpp:1231 write_bankprot_pvc -> prot_pvc.cpp:71
get_bank_base), with a declared incoming device ff8/ff9/bank state carried across same-CPU phases.
The RAM shadow is recorded only to demonstrate that it does not select the bank.
"""
import collections
import hashlib
import json
from pathlib import Path
import struct
from unicorn import UcError,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from observe_object_sound_lookup import (put,sha,oracle_provenance,make_cpu,load_verified_program,disassemble_range,
    BASE,STACK,STACK_START,RETURN,KEYS,REGS,SOURCE_SHA256)

ENTRY,WAIT,EXTERNAL=0x49fc6,0x3aea,0xd00046
A5,A6,SCRIPT=0x108000,0x100010,0x106000
SHADOW=0x100010          # -7ff0(A5) with A5=108000; equals A6+0 by design (intended alias).
OBJECT_A0=A6+0x26        # 100036 script pointer; A6+2a (10003a) is the 28 timer WORD tested at 4a0e4.
FIELD_SELECTOR,FIELD_ADDRESS=0x01,0x4a76e
CALLBACK_SELECTOR,CALLBACK_SLOT,TARGET=0x03,0x4a50c,0x3679e
CALLBACK_OPERAND=0x8123fedc
SOUND_WORD=0x04a0
HEAD,TAIL,SPECIAL=0x104d74,0x104d76,0x104d7b
WORDQ,READ,WRITE=0x104d82,0x104d8a,0x104d8c
CLEARED_BYTE=0x10d742    # clr.b 5742(A5) at 49fee.
GATES=dict(g100012=(0x100012,1),g10fd82=(0x10fd82,1),g10fe80=(0x10fe80,1),g10fd8d=(0x10fd8d,1),g104d7e=(0x104d7e,1),g10f001=(0x10f001,1))
RANGES=((ENTRY,0x4a104),(0x4a276,0x4a27e),(0x4a294,0x4a2ac),(0x4a2da,0x4a2f2),(0x4a408,0x4a46c),(TARGET,TARGET+2),(0x3ac8,0x3c08))
BOUNDARIES=(ENTRY,0x49ffe,0x4a294,0x4a2a6,0x4a408,0x4a43c,TARGET,0x4a43e,0x4a460,0x4a464,0x4a468,
    0x4a2da,0x4a2e6,0x3af8,0x4a2ec,0x4a2f0,0x4a276,0x4a0e4,0x4a0ca,0x4a0e2)
PVC_PCS=dict(entry=(0x49fd0,0x49fd8),callback_zero=(0x4a42c,0x4a434),callback_restore=(0x4a452,0x4a458),terminal=(0x4a0d0,0x4a0d8))
SHADOW_WRITE_PCS=(0x49fca,0x4a2a6,0x4a426,0x4a43e,0x4a0ca)
FIXED_READS=((0x4a2a0,FIELD_ADDRESS,2),(0x4a418,CALLBACK_SLOT,4))
PORT_FF8,PORT_FF9=0x2ffff0,0x2ffff2
SHADOWS=(0x0000,0x0001,0x0002,0x0006,0x0007,0x0008,0x000e,0x000f,0x0014,0x0015,0xffff)
CHAINS=('none','high','low','high_to_low')
DEFAULT_DEVICE=dict(ff8=0x00a0,ff9=0x1000,bank_base=0x200000)
VARIANT_DEVICE=dict(ff8=0xabcd,ff9=0xffff,bank_base=0x12345678)
CAP=20000

def word(value):return value&65535

# ---------------------------------------------------------------- pinned PVC device formula (model, not CPU)
def pvc_apply(device,address,size,value):
    """One write through neogeo.cpp:1231 write_bankprot_pvc: protection_w COMBINE_DATA (full WORD mask),
    then, for offset>=ff8, prot_pvc.cpp:71 get_bank_base (bank from stored ff8/ff9, then ff8/ff9 masking)."""
    assert size==2 and address in (PORT_FF8,PORT_FF9),(hex(address),size)
    offset=(address-0x2fe000)//2
    ff8,ff9=device['ff8'],device['ff9']
    if offset==0xff8:ff8=value&0xffff
    else:ff9=value&0xffff
    stored=dict(ff8=ff8,ff9=ff9)
    bank=(((ff8>>8)|(ff9<<8))+0x100000)&0xffffffff
    after=dict(ff8=(ff8&0xfe00)|0x00a0,ff9=ff9&0x7fff,bank_base=bank)
    return after,dict(offset=offset,stored_before_get_bank_base=stored,bank_base=bank,ff8_after=after['ff8'],ff9_after=after['ff9'])

def pair_formula(value):return 0x100000+((value&0x7fff)<<8)

def bank_chain(device_in,before,writes,phase):
    """Replay the actual ordered writes: RAM (to observe the shadow, never to select the bank) and PVC ports
    (through pvc_apply). Returns per-port-write records, PVC pairs and the outgoing device state."""
    ram=bytearray(before);device=dict(device_in);records=[]
    for index,x in enumerate(writes):
        if x['kind']=='ram':ram[x['address']-BASE:x['address']-BASE+x['size']]=x['value'].to_bytes(x['size'],'big')
        if x['kind']!='ports':continue
        device,record=pvc_apply(device,x['address'],x['size'],x['value'])
        record.update(phase=phase,ordered_write_index=index,pc=x['pc'],port=x['address'],raw_value=x['value'],
            shadow_ram_at_write=int.from_bytes(ram[SHADOW-BASE:SHADOW-BASE+2],'big'))
        records.append(record)
    return records,device

def group_pairs(records):
    """Each animation PVC call issues ff9<-value then ff8<-0 (consecutive port writes)."""
    assert len(records)%2==0,records
    pairs=[]
    for first,second in zip(records[0::2],records[1::2]):
        assert first['port']==PORT_FF9 and second['port']==PORT_FF8 and second['raw_value']==0,(first,second)
        site=next(k for k,v in PVC_PCS.items() if v==(first['pc'],second['pc']))
        assert second['bank_base']==pair_formula(first['raw_value'])
        pairs.append(dict(site=site,phase=first['phase'],pcs=[first['pc'],second['pc']],raw_value=first['raw_value'],
            first_write_bank=first['bank_base'],pair_bank=second['bank_base'],formula_100000_plus_value_and_7fff_shl8=pair_formula(first['raw_value']),
            first_differs_from_pair=first['bank_base']!=second['bank_base'],shadow_ram_at_first=first['shadow_ram_at_write'],
            shadow_ram_at_second=second['shadow_ram_at_write']))
    return pairs

# ---------------------------------------------------------------- cases and fixtures
def cases():
    rows=[]
    def add(family,shadow,chain,device=DEFAULT_DEVICE,**kw):
        case=dict(family=family,shadow=shadow,chain=chain,with_callback=family!='omit-14-shadow-only',device_in=dict(device),
            head=0x40,tail=0,read=0,write=6,entries=[0x0455,0x0566,0x0677,0x0788])
        case.update(kw);rows.append(case)
    for family in ('14-restore-bank','omit-14-shadow-only'):
        for shadow in SHADOWS:
            for chain in CHAINS:add(family,shadow,chain)
    for shadow in (0x0007,0x000e):
        for chain in ('none','high_to_low'):add('14-restore-incoming-device-variant',shadow,chain,device=VARIANT_DEVICE)
    return rows

def chain_head(case):
    tail=word(case['tail']);first=(tail+1)&0x7f
    return {'none':case['head'],'high':first,'high_to_low':first,'low':(tail+2)&0x7f}[case['chain']]

def fixture(case,index,program=None):
    if program is None:program,_=load_verified_program(Path(__file__).resolve().parents[1])
    assert int.from_bytes(program[FIELD_ADDRESS:FIELD_ADDRESS+2],'big')==0
    assert int.from_bytes(program[CALLBACK_SLOT:CALLBACK_SLOT+4],'big')==TARGET and program[TARGET:TARGET+2]==b'\x4e\x75'
    ram=bytearray(hashlib.shake_256(b'animation-bank-state-'+str(index).encode()).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=A5,a6=A6)
    setup=[(A6+0x26,4,SCRIPT),(A6+0x2a,2,0),(A6+0x2c,2,256),(A6+0x17,1,0),(SHADOW,2,0xbeef),
        (SPECIAL,1,0),(HEAD,2,chain_head(case)),(TAIL,2,case['tail']),(READ,2,case['read']),(WRITE,2,case['write'])]
    setup+=[(WORDQ+2*i,2,e) for i,e in enumerate(case['entries'])]
    setup+=[(a,s,1 if n=='g10fd8d' else 0) for n,(a,s) in GATES.items()]
    commands=[];cursor=SCRIPT
    def cmd(kind,raw,**extra):
        nonlocal cursor
        for i,b in enumerate(raw):setup.append((cursor+i,1,b))
        commands.append(dict(kind=kind,opcode_address=cursor,size=len(raw),cursor_after=cursor+len(raw),raw=bytes(raw).hex(),**extra));cursor+=len(raw)
    cmd('1c-field-WORD',[0x1c,FIELD_SELECTOR,case['shadow']>>8,case['shadow']&255],word_address=cursor+2,field_address=FIELD_ADDRESS,store_address=A6+0)
    if case['with_callback']:
        cmd('14-callback',[0x14,CALLBACK_SELECTOR]+list(CALLBACK_OPERAND.to_bytes(4,'big')),slot=CALLBACK_SLOT,target=TARGET,operand_address=cursor+2)
    cmd('30-direct-sound',[0x30,0x5a,SOUND_WORD>>8,SOUND_WORD&255],padding_address=cursor+1,word_address=cursor+2)
    terminal=cursor;setup+=[(terminal,1,0x28),(terminal+1,1,0xc3)]
    for address,size,value in setup:put(ram,address,size,value)
    details=dict(commands=commands,terminal=terminal,outer_a0=OBJECT_A0,shadow_address=SHADOW,
        setup_writes=[dict(address=a,size=s,value=v) for a,s,v in setup],
        intended_aliases=[dict(name='1c field A6+WORD[4a76e]=A6+0 is RAM bank shadow -7ff0(A5)',address=SHADOW)],
        adjacency=[dict(name='gate g100012 is A6+2, adjacent to shadow WORD A6+0..1 (no byte overlap)',address=0x100012)])
    spans=[(SHADOW,SHADOW+2),(A6+0x17,A6+0x18),(A6+0x26,A6+0x2e),(SCRIPT,terminal+2),(HEAD,HEAD+4),(SPECIAL,SPECIAL+1),
        (WORDQ,WRITE+2),(CLEARED_BYTE,CLEARED_BYTE+1)]+[(a,a+s) for a,s in GATES.values()]
    for i,(a,b) in enumerate(spans):
        for c,d in spans[i+1:]:assert b<=c or d<=a,('fixture overlap',hex(a),hex(c))
    details['checked_spans']=[[a,b] for a,b in spans]
    return bytes(ram),regs,details

# ---------------------------------------------------------------- original CPU observer
class Observer:
    def __init__(self,program,branches):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x2ff000,4096);self.cpu.mem_map(0xd00000,4096)
        self.baseline=self.cpu.context_save();self.branch_pcs=branches
        self.pcs=[];self.reads=[];self.writes=[];self.boundaries=[];self.error=None;self.visits=0;self.stop_state=None
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc in BOUNDARIES or not any(a<=pc<b for a,b in RANGES):
                sp=c.reg_read(m.UC_M68K_REG_A7)
                state=dict(pc=pc,a7=sp,registers=self.regs(),stack=bytes(c.mem_read(sp,max(0,STACK+4-sp))).hex())
                self.boundaries.append(state)
                if not any(a<=pc<b for a,b in RANGES):
                    self.stop_state=state;self.error=dict(kind='unsupported-code',pc=pc);c.emu_stop();return
            opcode=int.from_bytes(c.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:self.error=dict(kind='trap',pc=pc);c.emu_stop();return
            if pc==WAIT:
                if int.from_bytes(c.mem_read(HEAD,2),'big')==(c.reg_read(m.UC_M68K_REG_D1)&65535):
                    self.visits+=1
                    if self.visits==2:c.emu_stop()
                else:self.visits=0
        def write(c,access,address,size,value,user):
            kind='ports' if address in (PORT_FF8,PORT_FF9) and size==2 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1),kind=kind);self.writes.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);c.emu_stop()
        def read(c,access,address,size,value,user):
            pc=c.reg_read(m.UC_M68K_REG_PC)
            kind=('ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4
                else 'external' if address==EXTERNAL and size==1 else 'fixed' if (pc,address,size) in FIXED_READS else None)
            event=dict(pc=pc,address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind);self.reads.append(event)
            if kind is None:self.error=dict(kind='unexpected-read',event=event);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(c,number,user):self.error=dict(kind='exception',number=number,pc=c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):
            self.cpu.hook_add(hook,callback)
    def regs(self):return {key:self.cpu.reg_read(reg)&0xffffffff for key,reg in zip(KEYS,REGS)}
    def long(self,address):return int.from_bytes(self.cpu.mem_read(address,4),'big')
    def raw_ports(self):return bytes(self.cpu.mem_read(PORT_FF8,4)).hex()
    def prepare(self,ram,regs,external=0):
        c=self.cpu;c.context_restore(self.baseline);c.mem_write(BASE,ram);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'))
        c.mem_write(EXTERNAL,bytes([external]));c.mem_write(PORT_FF8,b'\0'*4)
        c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):c.reg_write(reg,regs[key])
        c.reg_write(m.UC_M68K_REG_PC,ENTRY);self.low=STACK
    def mutate(self,changes):
        """Host RAM/external writes only; the PVC port page is never touched."""
        ports=self.raw_ports()
        for x in changes:
            if x['address']==EXTERNAL:assert x['size']==1;self.cpu.mem_write(EXTERNAL,bytes([x['value']]))
            else:
                assert BASE<=x['address'] and x['address']+x['size']<=BASE+65536
                self.cpu.mem_write(x['address'],x['value'].to_bytes(x['size'],'big'))
        assert self.raw_ports()==ports
    def run(self,allow_stop=False):
        c=self.cpu;before=bytes(c.mem_read(BASE,65536));incoming=self.regs();start=c.reg_read(m.UC_M68K_REG_PC);ports_before=self.raw_ports()
        self.pcs.clear();self.reads.clear();self.writes.clear();self.boundaries.clear();self.error=None;self.visits=0;self.stop_state=None
        try:c.emu_start(start,0xffffff,count=CAP)
        except UcError as error:
            if self.error is None:self.error=dict(kind='unicorn-error',message=str(error))
        pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        if self.error is None and pc not in (RETURN,WAIT):self.error=dict(kind='instruction-cap-or-stop',pc=pc,instructions=len(self.pcs))
        if allow_stop and self.error is not None:return dict(self.error)
        assert self.error is None,(self.error,hex(pc))
        result=self.regs();pending=None;carry=None
        if pc==WAIT:
            assert self.visits==2
            top=self.long(sp)
            if top==0x3c00:
                assert sp==STACK-18 and self.long(STACK-12)==0x4a2ec
                pending=dict(sound_phase=1,saved_low=c.mem_read(STACK-14,1)[0],saved_low_address=STACK-14,unused_pad_byte=c.mem_read(STACK-13,1)[0])
            else:
                assert top==0x4a2ec and sp==STACK-12,(hex(top),hex(sp))
                pending=dict(sound_phase=2,saved_low=result['d0']&255,saved_low_address=None,unused_pad_byte=None)
            pending.update(animation_phase=4,a7=sp,top_return=top,return_4a2ec_at=STACK-12,outer_a0=self.long(STACK-8),outer_a1=self.long(STACK-4),
                wait_d1=result['d1']&65535,head=int.from_bytes(c.mem_read(HEAD,2),'big'),stack_raw=bytes(c.mem_read(sp,STACK+4-sp)).hex())
        else:
            assert sp==STACK+4;carry=bool(c.reg_read(m.UC_M68K_REG_SR)&1)
        assert bytes(c.mem_read(0,BASE))==self.program[:BASE] and bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        self.low=min([self.low]+[x['address'] for x in self.writes if x['kind']=='stack'])
        assert bytes(c.mem_read(STACK_START,self.low-STACK_START))==b'\x5a'*(self.low-STACK_START)
        replay=bytearray(before);ports=[];raw=bytearray.fromhex(ports_before)
        for x in self.writes:
            if x['kind']=='ram':replay[x['address']-BASE:x['address']-BASE+x['size']]=x['value'].to_bytes(x['size'],'big')
            if x['kind']=='ports':
                ports.append(struct.pack('>BII',x['size'],x['address'],x['value']));raw[x['address']-PORT_FF8:x['address']-PORT_FF8+2]=x['value'].to_bytes(2,'big')
        output=bytes(c.mem_read(BASE,65536));assert output==bytes(replay)
        assert self.raw_ports()==raw.hex()
        trace=dict(pcs=self.pcs.copy(),reads=self.reads.copy(),ordered_writes=self.writes.copy(),boundaries=self.boundaries.copy(),
            branches=[dict(pc=a,next_pc=b) for a,b in zip(self.pcs,self.pcs[1:]) if a in self.branch_pcs],
            final_stack=dict(a7=sp,from_address=min(sp,self.low),bytes=bytes(c.mem_read(min(sp,self.low),STACK+4-min(sp,self.low))).hex()))
        info=dict(incoming=incoming,result=result,waiting=pc==WAIT,carry=carry,pending=pending,final_pc=pc,final_a7=sp,
            lowest_stack_write=self.low,instructions=len(self.pcs)-(1 if pc==RETURN else 0),
            external_reads=sum(1 for r in self.reads if r['kind']=='external'),raw_port_memory_before=ports_before,raw_port_memory_after=self.raw_ports())
        return info,before,output,b''.join(ports),trace

# ---------------------------------------------------------------- checks
def check_phase(case,details,info,trace,first):
    for x in trace['ordered_writes']:
        if x['kind']=='ports':assert any(x['pc'] in v for v in PVC_PCS.values()),x
        if x['kind']=='ram' and x['address']<=SHADOW+1 and SHADOW<x['address']+x['size']:assert x['pc'] in SHADOW_WRITE_PCS,x
        if x['kind']=='ram':assert not (x['address']<=0x2ffff0<x['address']+x['size'])
    for r in trace['reads']:
        if r['kind']=='external':assert r['pc']==0x3b54 and r['size']==1
        if r['kind']=='fixed':assert (r['pc'],r['address'],r['size']) in FIXED_READS
        assert not (0x200000<=r['address']<0x300000),('banked ROM read',r)
        if r['address']<=0x100012<r['address']+r['size'] and r['kind']=='ram':assert 0x3ac8<=r['pc']<0x3c08,('object A6+2 read outside sound',r)
        for c in details['commands']:
            if 'padding_address' in c:assert not r['address']<=c['padding_address']<r['address']+r['size'],('padding read',r)
    assert sum(1 for b in trace['boundaries'] if b['pc']==ENTRY)==(1 if first else 0)
    fixed=[(r['pc'],r['address'],r['size'],r['value']) for r in trace['reads'] if r['kind']=='fixed']
    if first:
        expected=[(0x4a2a0,FIELD_ADDRESS,2,0)]+([(0x4a418,CALLBACK_SLOT,4,TARGET)] if case['with_callback'] else [])
        assert fixed==expected,(fixed,expected)
    else:assert fixed==[]
    bs=trace['boundaries']
    for i,b in enumerate(bs):
        regs=b['registers'];stack=bytes.fromhex(b['stack'])
        if b['pc']==0x4a2a6:
            assert regs['d0']==0 and regs['d1']&0xffff==case['shadow'] and regs['a6']==A6
        if b['pc']==TARGET:
            # Static 14 stack: S-14 return 4a43e, S-10 pushed shadow WORD, S-8 post-operand A1, S-4 outer A0.
            cb=next(c for c in details['commands'] if c['kind']=='14-callback')
            assert b['a7']==STACK-14 and int.from_bytes(stack[:4],'big')==0x4a43e
            assert int.from_bytes(stack[4:6],'big')==case['shadow'],('pushed shadow',stack[4:6].hex())
            assert int.from_bytes(stack[6:10],'big')==cb['cursor_after'] and int.from_bytes(stack[10:14],'big')==details['outer_a0']
            assert regs['a0']==CALLBACK_OPERAND and regs['a1']==TARGET and regs['d7']==TARGET and regs['d0']&0xffff==CALLBACK_SELECTOR*4
            assert trace['pcs'].count(TARGET)==1
        if b['pc']==0x4a43e:assert b['a7']==STACK-10
        if b['pc']==0x3af8:
            snd=next(c for c in details['commands'] if c['kind']=='30-direct-sound')
            assert b['a7']==STACK-12 and int.from_bytes(stack[:4],'big')==0x4a2ec
            assert int.from_bytes(stack[4:8],'big')==details['outer_a0'] and int.from_bytes(stack[8:12],'big')==snd['cursor_after']
            assert regs['d0']==SOUND_WORD
        if b['pc']==0x4a2ec:assert b['a7']==STACK-8
        if b['pc']==0x4a0e4:assert regs['a1']==details['terminal']+1 and regs['a0']==details['outer_a0']

def poison(case,details,salt,full):
    """Pending-only host writes: consumed 1c/14/30 bytes, object pointer/fields, the RAM bank shadow, and
    (full) sound gates/rings/external. A6+2a (28 timer WORD) and the unfetched 28 terminal are untouched."""
    changes=[]
    def add(address,size,value):changes.append(dict(address=address,size=size,value=value&((1<<(8*size))-1)))
    for c in details['commands']:
        add(c['opcode_address'],1,0x44)
        for a in range(c['opcode_address']+1,c['cursor_after']):add(a,1,(0x3c^salt^(a&0xff))&0xff)
    shadow=0x0006 if case['shadow']!=0x0006 else 0x000e
    add(A6+0x26,4,0x10fff0^(salt*2));add(A6+0x17,1,0x7f);add(A6+0x2c,2,0x7777^salt);add(SHADOW,2,shadow)
    if full:
        add(0x100012,1,1);add(0x10fd82,1,1);add(0x10fe80,1,0);add(0x10fd8d,1,0);add(0x104d7e,1,1);add(0x10f001,1,0x20)
        add(READ,2,0x7ff0^salt*2);add(WRITE,2,0x7ff0^salt*2)
        for i in range(4):add(WORDQ+2*i,2,(0x1f00|0x40+i)^salt)
        add(SPECIAL,1,0x5a^salt)
        changes.append(dict(address=EXTERNAL,size=1,value=0x81^salt))
    return changes

# ---------------------------------------------------------------- one case (all phases)
def run_case(observer,program,case,index):
    ram,regs,details=fixture(case,index,program);observer.prepare(ram,regs,0)
    phases=[];traces=[];payloads={};device=dict(case['device_in']);timeline=[]
    def observe(label,changes=()):
        nonlocal device
        device_in=dict(device)
        info,before,output,ports,trace=observer.run();check_phase(case,details,info,trace,not phases)
        records,device=bank_chain(device_in,before,trace['ordered_writes'],label);timeline.extend(records)
        prefix='case_%04d_%s'%(index,label)
        files={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace)+'\n').encode()}
        payloads.update(files)
        info.update(phase=label,host_changes=list(changes),device_in=device_in,device_out=dict(device),port_count=len(ports)//9,
            shadow_ram_in=int.from_bytes(before[SHADOW-BASE:SHADOW-BASE+2],'big'),shadow_ram_out=int.from_bytes(output[SHADOW-BASE:SHADOW-BASE+2],'big'),
            files={n:sha(v) for n,v in files.items()},input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',
            ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json')
        phases.append(info);traces.append(trace);return info,trace
    snd=next(c for c in details['commands'] if c['kind']=='30-direct-sound')
    begin,trace=observe('begin')
    chain=case['chain']
    if chain=='none':assert not begin['waiting']
    else:
        assert begin['waiting'];first=begin['pending']
        assert first['sound_phase']==(2 if chain=='low' else 1) and first['outer_a0']==details['outer_a0'] and first['outer_a1']==snd['cursor_after']
        captured=first['saved_low']
        def hold(label,salt):
            changes=poison(case,details,salt,True);observer.mutate(changes);info,trace=observe(label,changes)
            previous=phases[-2]
            assert info['waiting'] and info['pending']==previous['pending'] and info['result']==previous['result']
            assert not trace['ordered_writes'] and not trace['boundaries'] and info['external_reads']==0 and info['port_count']==0
            assert all(r['address']==HEAD and r['pc']==WAIT and r['size']==2 for r in trace['reads'])
            assert info['device_out']==info['device_in'] and info['raw_port_memory_after']==info['raw_port_memory_before']
            assert info['shadow_ram_in']!=case['shadow'] and info['shadow_ram_out']==info['shadow_ram_in']
        def release(label,head):
            changes=[dict(address=HEAD,size=2,value=head)];observer.mutate(changes);info,trace=observe(label,changes)
            assert info['external_reads']==0
            assert not any(c['opcode_address']<=r['address']<c['cursor_after'] for c in details['commands'] for r in trace['reads']),'prefix reread'
            assert not any(r['kind']=='fixed' or r['address']==SHADOW for r in trace['reads'])
            assert not any(b['pc'] in (ENTRY,0x4a294,0x4a408,TARGET,0x4a2da,0x3af8) for b in trace['boundaries'])
            assert trace['pcs'][0]==WAIT
            return info,trace
        hold('hold',0x11)
        if chain=='high_to_low':
            mid,trace=release('mid',(first['wait_d1']+1)&0x7f)
            assert mid['waiting'] and mid['pending']['sound_phase']==2 and mid['pending']['saved_low']==captured
            assert any(r['pc']==0x3c00 and r['address']==STACK-14 and r['value']==captured for r in trace['reads'])
            assert mid['port_count']==0
            hold('low_hold',0x22)
        ready,trace=release('ready',(phases[-1]['pending']['wait_d1']+0x40)&0x7f)
        assert not ready['waiting']
        # Actual phase4 resume: 3aea -> ... -> RTS to 4a2ec with the static outer A0/A1, then 4a276 publish, 28.
        back=[b for b in trace['boundaries'] if b['pc']==0x4a2ec];assert len(back)==1
        stack=bytes.fromhex(back[0]['stack'])
        assert int.from_bytes(stack[:4],'big')==details['outer_a0'] and int.from_bytes(stack[4:8],'big')==snd['cursor_after']
        pub=[w for w in trace['ordered_writes'] if w['pc']==0x4a278]
        assert [(w['address'],w['value']) for w in pub]==[(details['outer_a0'],snd['cursor_after'])]
        ready['phase4_resume']=dict(first_pcs=trace['pcs'][:8],at_4a2ec=back[0],publication=pub[0],
            reads_of_command_bytes=0,fixed_reads=0,shadow_reads=0)
    final=phases[-1];assert final['final_pc']==RETURN and final['final_a7']==STACK+4 and final['carry'] is True
    assert all(p['carry'] is None for p in phases[:-1])
    pairs=group_pairs(timeline)
    expect=['entry']+(['callback_zero','callback_restore'] if case['with_callback'] else [])+['terminal']
    assert [p['site'] for p in pairs]==expect,(pairs,expect)
    assert all(p['phase']=='begin' for p in pairs[:-1]) and pairs[-1]['phase']==final['phase']
    writes=[w for t in traces for w in t['ordered_writes']]
    shadow_writes=[dict(pc=w['pc'],value=w['value']) for w in writes if w['kind']=='ram' and w['address']==SHADOW]
    entry_first=((case['device_in']['ff8']>>8)|(0x1000<<8))+0x100000
    assert pairs[0]['raw_value']==0x1000 and pairs[0]['first_write_bank']==entry_first and pairs[0]['pair_bank']==0x200000
    assert pairs[-1]['raw_value']==0x1000 and pairs[-1]['pair_bank']==0x200000
    if case['with_callback']:
        restore=[w for w in shadow_writes if w['pc']==0x4a43e]
        assert [w['pc'] for w in shadow_writes]==[0x49fca,0x4a2a6,0x4a426,0x4a43e,0x4a0ca]
        assert shadow_writes[1]['value']==case['shadow'] and restore[0]['value']==case['shadow'] and shadow_writes[-1]['value']==0
        value=pairs[2]['raw_value']
        assert pairs[1]['raw_value']==0x1000 and pairs[1]['pair_bank']==0x200000
        # Observed relation between the actual restored WORD and the actual PVC WORD (not a shadow inference).
        assert value==word((restore[0]['value']+1)<<12)
        assert pairs[2]['first_write_bank']==(value<<8)+0x100000 and pairs[2]['pair_bank']==pair_formula(value)
        selected=pairs[2]['pair_bank']
    else:
        assert [w['pc'] for w in shadow_writes]==[0x49fca,0x4a2a6,0x4a0ca] and shadow_writes[1]['value']==case['shadow']
        selected=0x200000
    # The derived bank persists through every pending/hold/release phase until the terminal pair.
    for p in phases[:-1]:assert p['device_out']['bank_base']==selected,(p['phase'],hex(p['device_out']['bank_base']))
    at=next(i for i,r in enumerate(timeline) if r['pc']==0x4a0d0)
    assert at==len(timeline)-2 and timeline[at-1]['bank_base']==selected
    assert final['device_out']['bank_base']==0x200000 and final['shadow_ram_out']==0
    shadow_pending=[p['shadow_ram_out'] for p in phases[:-1]]
    if case['chain']!='none':assert shadow_pending[0]==case['shadow']
    summary=dict(selected_bank_before_terminal=selected,final_bank=final['device_out']['bank_base'],
        shadow_at_first_pending=shadow_pending[0] if shadow_pending else None,
        # Demonstration only (never used to select the bank): what a shadow-based guess would have produced.
        naive_shadow_guess_bank=pair_formula(word((case['shadow']+1)<<12)),
        naive_shadow_guess_matches=selected==pair_formula(word((case['shadow']+1)<<12)),
        callback_pvc_raw=pairs[2]['raw_value'] if case['with_callback'] else None,
        callback_first_write_bank=pairs[2]['first_write_bank'] if case['with_callback'] else None)
    return dict(details=details,phases=phases,pairs=pairs,pvc_timeline=timeline,shadow_writes=shadow_writes,summary=summary),payloads,traces

def guard_controls(observer,program):
    controls=[]
    def attempt(name,case,mutate,kind,pc):
        ram,regs,details=fixture(case,200000+len(controls),program);ram=bytearray(ram)
        for a,s,v in mutate(details):put(ram,a,s,v)
        observer.prepare(bytes(ram),regs,0);stopped=observer.run(allow_stop=True)
        assert isinstance(stopped,dict) and stopped['kind']==kind and (pc is None or stopped.get('pc',stopped.get('event',{}).get('pc'))==pc),(name,stopped)
        controls.append(dict(name=name,stopped=stopped,artifacts_written=False))
    base=dict(cases()[0])
    # Another slot read (4a500 -> 22656) is rejected by the exact (pc,address,size) allowlist before any JSR.
    attempt('14-selector00-other-slot-read-rejected',base,lambda d:[(d['commands'][1]['opcode_address']+1,1,0)],'unexpected-read',0x4a418)
    attempt('1c-selector00-field-read-not-allowlisted',base,lambda d:[(d['commands'][0]['opcode_address']+1,1,0)],'unexpected-read',0x4a2a0)
    attempt('terminal-opcode44-trap',base,lambda d:[(d['terminal'],1,0x44)],'trap',0x4a00a)
    return controls

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/animation_bank_state_native';folder.mkdir(parents=True,exist_ok=True)
    for old in folder.glob('case_*'):old.unlink()
    report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for a,b in RANGES:instructions.extend(disassemble_range(program,a,b-a,a))
    for r in instructions:assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    ref=root/'artifacts/reference'
    neogeo=(ref/'neogeo.cpp').read_text().splitlines();pvc=(ref/'prot_pvc.cpp').read_text().splitlines()
    assert neogeo[1230].startswith('void neogeo_base_state::write_bankprot_pvc(offs_t offset, uint16_t data, uint16_t mem_mask)')
    assert pvc[70]=='uint32_t pvc_prot_device::get_bank_base()'
    assert [x.strip() for x in pvc[72:76]]==['uint32_t bankaddress = ((m_cart_ram[0xff8] >> 8)|(m_cart_ram[0xff9] << 8));',
        'm_cart_ram[0xff8] = (m_cart_ram[0xff8] & 0xfe00) | 0x00a0;','m_cart_ram[0xff9] &= 0x7fff;','return bankaddress + 0x100000;']
    assert 'install_write_handler(0x2fe000, 0x2fffff, write16s_delegate(*this, FUNC(neogeo_base_state::write_bankprot_pvc)))' in neogeo[1483]
    pinned=dict(neogeo_cpp=dict(path='artifacts/reference/neogeo.cpp',line=1231,install_line=1484,excerpt=neogeo[1230:1242],excerpt_sha256=sha('\n'.join(neogeo[1230:1242]).encode())),
        prot_pvc_cpp=dict(path='artifacts/reference/prot_pvc.cpp',line=71,excerpt=pvc[70:77],excerpt_sha256=sha('\n'.join(pvc[70:77]).encode())),
        revision=(ref/'revision.txt').read_text().strip())
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=RANGES,boundaries=BOUNDARIES,instructions=instructions,
        fixed_reads=[dict(pc=p,cpu_address=a,rom_offset=a,size=s,raw=program[a:a+s].hex()) for p,a,s in FIXED_READS],
        actual_rts=dict(cpu_address=TARGET,rom_offset=TARGET,raw=program[TARGET:TARGET+2].hex()),pinned_pvc_reference=pinned,
        note='CPU address equals ROM file offset for these ranges in the canonical big-endian program.'),indent=2)+'\n')
    names=('tools/observe_animation_bank_state.py','tools/observe_object_sound_lookup.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py',
        'artifacts/reference/neogeo.cpp','artifacts/reference/prot_pvc.cpp','artifacts/reference/revision.txt','artifacts/animation_bank_state_native/source.json')
    inputs={n:sha((root/n).read_bytes()) for n in names};oracle=oracle_provenance()
    observer=Observer(program,branches);rows=[];outcomes=collections.defaultdict(collections.Counter);artifacts={}
    for index,case in enumerate(cases()):
        row,payloads,traces=run_case(observer,program,case,index)
        # Independent reset and full re-execution must reproduce every phase, trace and payload.
        again,payloads2,_=run_case(observer,program,case,index)
        assert again==row and payloads2==payloads
        for n,data in payloads.items():(folder/n).write_bytes(data);artifacts[n]=sha(data)
        for t in traces:
            for b in t['branches']:outcomes[b['pc']][b['next_pc']]+=1
        row.update(case_index=index,fixture=case,total_external_reads=sum(p['external_reads'] for p in row['phases']))
        rows.append(row)
    controls=guard_controls(observer,program)
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/n).read_bytes())==h for n,h in inputs.items())
    for n,h in artifacts.items():assert sha((folder/n).read_bytes())==h
    selected=collections.defaultdict(set);first_vs_pair=[]
    for r in rows:
        selected['%s/shadow%04x'%(r['fixture']['family'],r['fixture']['shadow'])].add(hex(r['summary']['selected_bank_before_terminal']))
        for p in r['pairs']:
            if p['first_differs_from_pair']:first_vs_pair.append(dict(case_index=r['case_index'],site=p['site'],raw_value=p['raw_value'],
                first_write_bank=p['first_write_bank'],pair_bank=p['pair_bank'],shadow_ram_at_second=p['shadow_ram_at_second']))
    pending_rows=[r for r in rows if r['fixture']['chain']!='none']
    report=dict(source=source,oracle=oracle,inputs=inputs,pinned_pvc_reference=pinned,entry_pc=ENTRY,
        static_contract=dict(script=['1c 01 WORD(shadow)','14 03 LONG(operand)','30 pad WORD(04a0)','28'],a5=A5,a6=A6,shadow=SHADOW,
            field_word_4a76e=0,callback_slot_4a50c=TARGET,callback_raw='4e75',
            callback_stack=dict(a7='S-14',return_4a43e='S-14',pushed_shadow_word='S-10',outer_a1='S-8',outer_a0='S-4'),
            sound_high_wait=dict(a7='S-18',top=0x3c00,saved_low='S-14',return_4a2ec='S-12',outer_a0='S-8',outer_a1='S-4'),
            sound_low_wait=dict(a7='S-12',top=0x4a2ec,outer_a0='S-8',outer_a1='S-4'),S=STACK,verified_by_native_memory=True),
        bank_model=dict(kind='derived-from-actual-PVC-writes-plus-pinned-device-formula',
            not_claimed=['original CPU register','full PVC device behaviour','bank inferred from RAM shadow','banked ROM data read','opcode40'],
            default_incoming_device=DEFAULT_DEVICE,variant_incoming_device=VARIANT_DEVICE,
            per_write='protection_w full WORD store then get_bank_base: bank=((ff8>>8)|(ff9<<8))+100000; ff8=(ff8&fe00)|a0; ff9&=7fff',
            pair_final='100000+((value&7fff)<<8)'),
        cases=len(rows),phases=sum(len(r['phases']) for r in rows),pending_chains=len(pending_rows),
        cases_by_family=dict(collections.Counter(r['fixture']['family'] for r in rows)),
        chains_by_kind=dict(collections.Counter(r['fixture']['chain'] for r in rows)),
        selected_bank_before_terminal={k:sorted(v) for k,v in sorted(selected.items())},
        first_write_bank_differs_from_pair_bank=dict(count=len(first_vs_pair),examples=first_vs_pair[:40]),
        total_native_ports=sum(p['port_count'] for r in rows for p in r['phases']),
        total_external_reads=sum(r['total_external_reads'] for r in rows),banked_rom_data_reads=0,
        returned_carry_counts=dict(collections.Counter(str(r['phases'][-1]['carry']) for r in rows)),
        observed_branch_successors={hex(a):{hex(b):n for b,n in sorted(c.items())} for a,c in sorted(outcomes.items())},
        guard_controls=controls,reproduced_twice=True,instruction_cap_per_run=CAP,original_program_modified=False,
        in_call_SR_read=False,register_injection_after_begin=False,fake_callback=False,device_mutated_by_host=False,
        Cpp_comparison_performed=False,opcode40_claim=False,failure=None,
        artifact_files=len(artifacts),artifact_manifest_sha256=sha(json.dumps(sorted(artifacts.items())).encode()),artifacts=dict(sorted(artifacts.items())),
        results=rows,
        limitations=['Synthetic live-RAM fixtures; A5=108000, A6=100010 (object overlaps bank shadow by design), script at even 106000.',
            'Bank values are derived from actual ordered PVC port writes plus the pinned MAME formula and a declared incoming device state; '
            'no physical PVC/cartridge device or CPU register is observed. The cart wrapper get_bank_base(data) and m_cart_ram declaration are not in the pinned excerpt.',
            'Only the complete animation pair ff9<-value, ff8<-0 is exercised; arbitrary PVC write sequences are not claimed.',
            'No banked ROM data read occurs; the observer maps only the PVC port page at 2ff000 inside the bank window and rejects all data reads there. Opcode40 and MS5D routing are not claimed.',
            'Shadow list includes both decimal-intended e/f and hex 14/15 interpretations of the requested "14,15".',
            'Only callback selector03 -> actual RTS 3679e; other callbacks are not stubbed. The selector00 guard rejects the non-allowlisted dispatch read before any JSR.',
            'Byte-queue head release and poisoning are host writes between phases, recorded in host_changes; no natural IRQ/Z80 consumer, cycle timing or full CCR claim.'],
        scope='Unpatched original whole49fc6: 1c01 writes RAM shadow100010 via ROM WORD[4a76e]=0; 14/03 -> ROM LONG[4a50c] -> actual RTS3679e; '
            '4a43e restores the pushed shadow WORD and writes PVC; 30 -> 3af8 same-CPU high/low/high->low waits with shadow poison; 28 -> 4a0ca zero bank. '
            'Counterexample family omits 14. Full64KiB RAM/15 registers/RTS carry/ordered PVC/read-write-PC-stack traces per phase.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=report['pending_chains'],ports=report['total_native_ports'],
        external_reads=report['total_external_reads'],first_vs_pair_differences=len(first_vs_pair),guards=len(controls),
        artifacts=len(artifacts),carry=report['returned_carry_counts'],sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
