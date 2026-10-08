"""Immutable original whole49fc6 opcode3c (4a30c) -> known callbacks 2b3e8/2b3fa/47672; no C++ oracle.

Each case runs the unpatched canonical program from 49fc6 with a synthetic live-RAM script
(one or two 3c commands followed by a 00,00 timer exit or a 28 finish). A run stops only at the
caller RETURN, at the actual 3aea byte-queue wait after two consecutive equal head visits, or,
for explicitly unsupported callbacks, when the first PC outside the supported ranges is reached
(before it executes). Pending runs resume on the same Unicorn context; between phases the host
only writes recorded RAM changes (poison and byte-queue head release). Nothing patches code or
registers; SR is written before A7 at preparation and read only after RTS to RETURN (carry).
The actual target LONG read from the dispatch table decides the callee, not the selector value.
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
PREFIX,CALL,BACK=0x4a30c,0x4a352,0x4a354
A5,A6,SCRIPT,OPERANDS=0x108000,0x102000,0x106000,0x107000
BANK,SOURCE=0x100010,0x10095c
HEAD,TAIL,BYTEQ=0x104d74,0x104d76,0x104cf4
WORDQ,READ,WRITE=0x104d82,0x104d8a,0x104d8c
DISPATCH,FIELD,RAW=0x4a500,0x4a76c,0x4411e
KNOWN={0x2b3e8:'2b3e8-index7c',0x2b3fa:'2b3fa-index7d',0x47672:'47672-sound-lookup'}
RANGES=((ENTRY,0x4a104),(0x4a276,0x4a27e),(PREFIX,0x4a382),(0x2b3e8,0x2b40c),(0x47672,0x476bc),(0xca70,0xca76),(0x3ac8,0x3c08))
BOUNDARIES=(ENTRY,0x49ffe,PREFIX,0x4a322,0x4a330,CALL,0x2b3e8,0x2b3fa,0x47672,0x3af8,0x4768e,0x47690,
    BACK,0x4a376,0x4a37a,0x4a37e,0x4a276,0x4a0ca)
PVC_PCS=(0x49fd0,0x49fd8,0x4a342,0x4a34a,0x4a368,0x4a36e,0x4a0d0,0x4a0d8)
BANK_PCS=(0x49fca,0x4a33c,BACK,0x4a0ca)
FIXED_READ_PCS=(0x4a31e,0x4a32c,0x2b3f2,0x2b404,0x476aa)
GATES=(0x100012,0x104d7e,0x10f001,0x10fd82,0x10fe80,0x10fd8d)
CAP=20000

def word(value):return value&65535
def signed(value):return value-0x10000 if value&0x8000 else value
def sext(value):return value|0xffff0000 if value&0x8000 else value&65535
def rom_long(program,address):return int.from_bytes(program[address:address+4],'big')
def rom_word(program,address):return int.from_bytes(program[address:address+2],'big')
def slot_of(sel1):return DISPATCH+signed(word(sel1*4))
def field_of(sel2):return FIELD+signed(word(sel2*2))

D1_HIGHS=(0x1234abcd,0xfedc5678,0x0000ffff,0xffff0000,0x80007fff)

def cases():
    rows=[]
    def add(family,commands,**kw):
        case=dict(family=family,commands=commands,terminal='00',a6=A6,d0_in=0x89abcdef,d1_in=D1_HIGHS[len(rows)%5],
            index=5,sound=False,mode=0,external=0,wait=0,queue_alias=False,source_word=0x5a01,poison='none',
            operand_table=True,overwrite_value=None)
        case.update(kw);rows.append(case)
    def cmd(sel1,sel2=0x0010,operand=OPERANDS):return dict(sel1=sel1,sel2=sel2,operand=operand)
    # First WORD: all four 16-bit modular aliases of each known slot (the full-table scan finds no other slot).
    for sel in (0x1d,0x1e,0x1f):
        for alias in (0,0x4000,0x8000,0xc000):
            add('first-selector-modular-alias',[cmd(sel+alias,operand=OPERANDS if sel!=0x1f else 0x8123fedc)],terminal='28')
    # Second WORD: wrap boundaries and values whose looked-up field WORD is negative (positive/negative displacement).
    for sel in (0x1d,0x1e,0x1f):
        for sel2 in (0,1,0x3fff,0x4000,0x7fff,0x8000,0xbfff,0xc000,0xffff,0x0096,0x00ff,0xff01,0xff3d):
            add('second-selector-boundary',[cmd(sel,sel2,OPERANDS if sel!=0x1f else 0x00fffffe)],terminal='28')
    # 1d/1e operand LONG profiles and live index BYTE; terminal alternates so both RTS carries are observed.
    profiles=(('RAM-operand-table',lambda i:OPERANDS),('fixed-6431a',lambda i:0x6431a),('fixed-000000-vectors',lambda i:0),
        ('fixed-ffc00-last-ROM-LONG',lambda i:0xffc00),('RAM-source-is-own-3c-command',lambda i:SCRIPT-i*4))
    for sel in (0x1d,0x1e):
        for name,operand in profiles:
            for index in (0,1,0x80,0xff):
                add('operand-index-'+name,[cmd(sel,0x7fff,operand(index))],index=index,terminal='28' if index in (0,0x80) else '00',
                    operand_table=name=='RAM-operand-table')
    # Callee $78(a6) store overwrites the not-yet-fetched terminal: next opcode must be fetched live.
    add('callee-store-overwrites-next-opcode',[cmd(0x1d,0xffff)],a6=SCRIPT+10-0x78,terminal='00',overwrite_value=0x28a5c3e1)
    add('callee-store-overwrites-next-opcode',[cmd(0xc01e,0x8000)],a6=SCRIPT+10-0x78,terminal='28',overwrite_value=0x00005a5a)
    # Two 3c commands in one invocation (4a276 continuation into another 3c prefix).
    add('two-3c-commands',[cmd(0x1d,0x0096),cmd(0x401f,0xff01,0xffffffff)],terminal='28')
    add('two-3c-commands',[cmd(0x801e,0x3fff),cmd(0xc01d,0x0001,0x6431a)],terminal='00')
    # 1f immediate: sound gates/external, full D0 operand LONG values.
    operands=(0,0xffffffff,0x80000000,0x7fffffff,SOURCE,0x00fffffe,0x12345678,0xfedcba98)
    for sound in (False,True):
        for i,(mode,external) in enumerate(((0,0),(1,0),(2,0),(3,0),(3,1),(3,255),(4,0),(5,0))):
            add('1f-immediate-gates',[cmd(0x1f,0x7fff,operands[i])],sound=sound,mode=mode,external=external,terminal='28' if i%2 else '00')
    for sound in (False,True):add('1f-bank-shadow-alias-a6+12',[cmd(0x1f,0x0010,0x8123fedc)],a6=0xffffe,sound=sound,terminal='28')
    # Callee source low BYTE: ADD.B overflow (->80) and index 0, via the 3c prefix.
    for source_word in (0x5a40,0x5a00):add('1f-source-low-byte-lookup',[cmd(0x801f,0x0001,0x00ff00ff)],source_word=source_word,terminal='28')
    add('1f-signed-queue-write-aliases-live-source',[cmd(0x1f,0x0010,0x8123fedc)],sound=True,queue_alias=True,terminal='28')
    # Same-CPU waits: high, low, high->low; prefix-only poison vs prefix+live-terminal swap.
    for wait in (1,2,3):
        add('1f-same-CPU-wait',[cmd(0x1f,0x7fff,0x80123456)],sound=True,wait=wait,poison='prefix',terminal='00')
        add('1f-same-CPU-wait',[cmd(0xc01f,0x8000,0x7fedcba9)],sound=True,wait=wait,poison='prefix+live-terminal',terminal='00')
    return rows

def unsupported_cases():
    # Actual raw dispatch LONGs that are not the three known callees; executed only up to the target PC.
    return [dict(family='unsupported-target-stop',commands=[dict(sel1=s,sel2=0x0010,operand=OPERANDS)],terminal='28',a6=A6,
        d0_in=0x89abcdef,d1_in=0x1234abcd,index=5,sound=False,mode=0,external=0,wait=0,queue_alias=False,source_word=0x5a01,
        poison='none',operand_table=True,overwrite_value=None) for s in (0x0000,0x001c,0x0020,0x2000,0x1fff)]

def sound_setup(ram,case):
    for at,size,value in ((0x100012,1,0),(0x104d7e,1,0),(0x10f001,1,0),(READ,2,0),(WRITE,2,0),(HEAD,2,0),(TAIL,2,0),
            (0x10fd82,1,0),(0x10fe80,1,0),(0x10fd8d,1,1)):
        put(ram,at,size,value)
    mode=case['mode']
    if mode==1:put(ram,0x104d7e,1,1)
    if mode==2:put(ram,0x100012,1,1);put(ram,0x10fd8d,1,0)
    if mode==3:put(ram,0x100012,1,1);put(ram,0x10fd82,1,1)
    if mode==4:put(ram,0x10f001,1,32)
    if mode==5:put(ram,READ,2,0);put(ram,WRITE,2,2);put(ram,WORDQ,2,0x1ac0)
    if case['wait']:
        for at,value in ((READ,0),(WRITE,6),(HEAD,2 if case['wait']==2 else 1),(TAIL,0),
                (WORDQ,0x0455),(WORDQ+2,0x0566),(WORDQ+4,0x0677),(WORDQ+6,0x0788)):
            put(ram,at,2,value)
    if case['queue_alias']:put(ram,READ,2,word(SOURCE-WORDQ));put(ram,WRITE,2,word(SOURCE-WORDQ))
    put(ram,SOURCE,2,case['source_word'])
    put(ram,case['a6']+0x7e,1,(case['source_word']>>8)^(1 if case['sound'] else 0))

def fixture(case,index,program):
    ram=bytearray(hashlib.shake_256(b'animation-word-callback-'+str(index).encode()).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    a6=case['a6'];regs.update(a5=A5,a6=a6,d0=case['d0_in'],d1=case['d1_in'])
    sound_setup(ram,case)
    for address,size,value in ((a6+0x26,4,SCRIPT),(a6+0x2a,2,0),(a6+0x2c,2,256),(a6+0x17,1,0),(BANK,2,0xbeef),
            (a6+0x7c,1,case['index']),(a6+0x7d,1,case['index'])):
        put(ram,address,size,value)
    cursor=SCRIPT;commands=[]
    for i,c in enumerate(case['commands']):
        pad=0xa5^(i*0x11)
        put(ram,cursor,1,0x3c);put(ram,cursor+1,1,pad);put(ram,cursor+2,2,c['sel1']);put(ram,cursor+4,2,c['sel2']);put(ram,cursor+6,4,c['operand'])
        slot=slot_of(c['sel1']);field=field_of(c['sel2']);target=rom_long(program,slot)
        commands.append(dict(opcode_address=cursor,padding_address=cursor+1,padding=pad,sel1_address=cursor+2,sel2_address=cursor+4,
            operand_address=cursor+6,cursor_after=cursor+10,sel1=c['sel1'],sel2=c['sel2'],operand=c['operand'],
            slot=slot,slot_rom_offset=slot,target=target,callee=KNOWN.get(target,'unsupported'),
            field=field,field_rom_offset=field,field_word=rom_word(program,field)))
        cursor+=10
    put(ram,cursor,2,0x0000 if case['terminal']=='00' else 0x28c3)
    if case['operand_table']:
        for i in range(256):put(ram,OPERANDS+4*i,4,(0x81000000|i<<16|0xa500|i)^(index<<8))
    if case['overwrite_value'] is not None:
        # The callee copies LONG operand[index] to a6+78 == the terminal address.
        assert a6+0x78==cursor;put(ram,OPERANDS+4*case['index'],4,case['overwrite_value'])
    details=dict(commands=commands,terminal=cursor,outer_a0=a6+0x26)
    spans=[(a6+0x17,a6+0x18),(a6+0x26,a6+0x2e),(a6+0x7c,a6+0x7f),(SCRIPT,cursor+2),(BANK,BANK+2),(SOURCE,SOURCE+2),
        (HEAD,HEAD+4),(WORDQ,WRITE+2)]+[(g,g+1) for g in GATES]
    if case['operand_table']:spans.append((OPERANDS,OPERANDS+1024))
    if case['a6']!=0xffffe:spans.append((a6+0x12,a6+0x13))  # 0xffffe: a6+12 == bank shadow, the intended alias.
    if case['overwrite_value'] is None:spans.append((a6+0x78,a6+0x7c))  # Intended alias: a6+78 == terminal.
    for i,(a,b) in enumerate(spans):
        for c,d in spans[i+1:]:assert b<=c or d<=a,('fixture overlap',case['family'],hex(a),hex(c))
    return bytes(ram),regs,details

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
            kind='ports' if address in (0x2ffff0,0x2ffff2) and size==2 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1),kind=kind);self.writes.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);c.emu_stop()
        def read(c,access,address,size,value,user):
            pc=c.reg_read(m.UC_M68K_REG_PC)
            kind=('ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4
                else 'external' if address==EXTERNAL and size==1 else 'fixed' if address+size<=BASE and pc in FIXED_READ_PCS else None)
            event=dict(pc=pc,address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind);self.reads.append(event)
            if kind is None:self.error=dict(kind='unexpected-read',event=event);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(c,number,user):self.error=dict(kind='exception',number=number,pc=c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):
            self.cpu.hook_add(hook,callback)
    def regs(self):return {key:self.cpu.reg_read(reg)&0xffffffff for key,reg in zip(KEYS,REGS)}
    def long(self,address):return int.from_bytes(self.cpu.mem_read(address,4),'big')
    def prepare(self,ram,regs,external):
        c=self.cpu;c.context_restore(self.baseline);c.mem_write(BASE,ram);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'))
        c.mem_write(EXTERNAL,bytes([external]))
        c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):c.reg_write(reg,regs[key])
        c.reg_write(m.UC_M68K_REG_PC,ENTRY);self.low=STACK
    def mutate(self,changes):
        for x in changes:
            assert BASE<=x['address'] and x['address']+x['size']<=BASE+65536
            self.cpu.mem_write(x['address'],x['value'].to_bytes(x['size'],'big'))
    def run(self,allow_unsupported=False):
        c=self.cpu;before=bytes(c.mem_read(BASE,65536));incoming=self.regs();start=c.reg_read(m.UC_M68K_REG_PC)
        self.pcs.clear();self.reads.clear();self.writes.clear();self.boundaries.clear();self.error=None;self.visits=0;self.stop_state=None
        try:c.emu_start(start,0xffffff,count=CAP)
        except UcError as error:
            if self.error is None:self.error=dict(kind='unicorn-error',message=str(error))
        pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        if self.error is None and pc not in (RETURN,WAIT):self.error=dict(kind='instruction-cap-or-stop',pc=pc,instructions=len(self.pcs))
        stopped=None
        if allow_unsupported and self.error is not None and self.error['kind']=='unsupported-code':stopped=dict(self.error)
        else:assert self.error is None,(self.error,hex(pc))
        result=self.regs();pending=None;carry=None
        if stopped:
            assert pc==stopped['pc']
        elif pc==WAIT:
            assert self.visits==2
            top=self.long(sp)
            if top==0x3c00:
                assert sp==STACK-28 and self.long(STACK-22)==0x4768e
                pending=dict(sound_phase=1,saved_low=c.mem_read(STACK-24,1)[0],saved_low_address=STACK-24,unused_pad_byte=c.mem_read(STACK-23,1)[0])
            else:
                assert top==0x4768e and sp==STACK-22,(hex(top),hex(sp))
                pending=dict(sound_phase=2,saved_low=result['d0']&255,saved_low_address=None,unused_pad_byte=None)
            assert self.long(STACK-14)==BACK
            pending.update(a7=sp,top_return=top,inner_a0=self.long(STACK-18),return_4a354_at=STACK-14,
                bank=int.from_bytes(c.mem_read(STACK-10,2),'big'),outer_a1=self.long(STACK-8),outer_a0=self.long(STACK-4),
                wait_d1=result['d1']&65535,head=int.from_bytes(c.mem_read(HEAD,2),'big'),stack_raw=bytes(c.mem_read(sp,STACK+4-sp)).hex())
        else:
            assert sp==STACK+4;carry=bool(c.reg_read(m.UC_M68K_REG_SR)&1)
        assert bytes(c.mem_read(0,BASE))==self.program[:BASE] and bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        self.low=min([self.low]+[x['address'] for x in self.writes if x['kind']=='stack'])
        assert bytes(c.mem_read(STACK_START,self.low-STACK_START))==b'\x5a'*(self.low-STACK_START)
        replay=bytearray(before);ports=[]
        for x in self.writes:
            if x['kind']=='ram':replay[x['address']-BASE:x['address']-BASE+x['size']]=x['value'].to_bytes(x['size'],'big')
            if x['kind']=='ports':ports.append(struct.pack('>BII',x['size'],x['address'],x['value']))
        output=bytes(c.mem_read(BASE,65536));assert output==bytes(replay)
        trace=dict(pcs=self.pcs.copy(),reads=self.reads.copy(),ordered_writes=self.writes.copy(),boundaries=self.boundaries.copy(),
            branches=[dict(pc=a,next_pc=b) for a,b in zip(self.pcs,self.pcs[1:]) if a in self.branch_pcs],
            final_stack=dict(a7=sp,bytes=bytes(c.mem_read(min(sp,self.low),STACK+4-min(sp,self.low))).hex(),from_address=min(sp,self.low)))
        info=dict(incoming=incoming,result=result,waiting=pc==WAIT,stopped_unsupported=stopped,stop_state=self.stop_state,carry=carry,
            pending=pending,final_pc=pc,final_a7=sp,lowest_stack_write=self.low,instructions=len(self.pcs)-(1 if pc==RETURN or stopped else 0),
            external_reads=sum(1 for r in self.reads if r['kind']=='external'))
        return info,before,output,b''.join(ports),trace

def expected_prefix_reads(cmd,bank):
    return [(0x4a312,cmd['sel1_address'],2,cmd['sel1']),(0x4a31e,cmd['slot'],4,cmd['target']),(0x4a322,cmd['sel2_address'],2,cmd['sel2']),
        (0x4a32c,cmd['field'],2,cmd['field_word']),(0x4a330,cmd['operand_address'],4,cmd['operand']),(0x4a338,BANK,2,bank)]

def check_phase(case,details,info,trace,first):
    """Structural invariants valid for every phase of every case (incl. unsupported stops)."""
    commands=details['commands'];cursors=[c['cursor_after'] for c in commands]
    for x in trace['ordered_writes']:
        if x['kind']=='ports':assert x['pc'] in PVC_PCS,x
        if x['kind']=='ram' and x['address']<=BANK+1 and BANK<x['address']+x['size']:
            assert x['pc'] in BANK_PCS or (case['a6']==0xffffe and x['pc']==0x476b6),x
        if x['pc']==0x4a278:assert x['address']==details['outer_a0'] and x['size']==4 and x['value'] in cursors,x
    for r in trace['reads']:
        if r['kind']=='external':assert r['pc']==0x3b54 and r['size']==1
        # Only the 1d/1e operand-source read may cover the padding (own-command source profile); 3c skips it.
        if r['pc'] not in (0x2b3f2,0x2b404):
            for c in commands:assert not r['address']<=c['padding_address']<r['address']+r['size'],('padding read',r)
    assert sum(1 for b in trace['boundaries'] if b['pc']==ENTRY)==(1 if first else 0)
    # Exact prefix reads per 3c execution, in order: no extra/duplicate read.
    prefix=[(r['pc'],r['address'],r['size'],r['value']) for r in trace['reads'] if PREFIX<=r['pc']<BACK]
    starts=[b for b in trace['boundaries'] if b['pc']==PREFIX]
    expected=[]
    for b in starts:
        cmd=next(c for c in commands if c['opcode_address']+1==b['registers']['a1'])
        expected.extend(expected_prefix_reads(cmd,0))
    assert prefix==expected,(prefix,expected)
    bs=trace['boundaries'];at_prefix=None
    for i,b in enumerate(bs):
        regs=b['registers'];stack=bytes.fromhex(b['stack'])
        if b['pc']==PREFIX:
            assert b['a7']==STACK and regs['a0']==details['outer_a0'];at_prefix=regs
        if b['pc']==0x4a322:
            # First WORD replaces only D0.low; D0.high is the value at 3c entry.
            cmd=next(c for c in commands if c['sel1_address']+2==regs['a1'])
            assert regs['d0']==(at_prefix['d0']&0xffff0000)|word(cmd['sel1']*4) and regs['d7']==cmd['target'] and regs['a0']==DISPATCH
            assert b['a7']==STACK-4 and int.from_bytes(stack[:4],'big')==details['outer_a0']
        if b['pc']==0x4a330:
            # Second WORD: D0.low=2*WORD, D1.low=field WORD, both high halves from 3c entry.
            cmd=next(c for c in commands if c['sel2_address']+2==regs['a1'])
            assert regs['d0']==(at_prefix['d0']&0xffff0000)|word(cmd['sel2']*2) and regs['a0']==FIELD
            assert regs['d1']==(at_prefix['d1']&0xffff0000)|cmd['field_word']
        if b['pc']==CALL or b['pc'] in KNOWN or (info['stop_state'] is not None and b is bs[-1] and b['pc']==info['stop_state']['pc']):
            # Static outer stack from the contract: S-14 return 4a354, S-10 bank WORD, S-8 post-operand A1, S-4 outer A0.
            depth=10 if b['pc']==CALL else 14
            assert b['a7']==STACK-depth,(hex(b['pc']),hex(b['a7']))
            if depth==14:assert int.from_bytes(stack[:4],'big')==BACK
            s=stack[depth-10:]
            bank,a1,a0=int.from_bytes(s[:2],'big'),int.from_bytes(s[2:6],'big'),int.from_bytes(s[6:10],'big')
            cmd=next(c for c in commands if c['cursor_after']==a1)
            assert a0==details['outer_a0'] and bank==0
            assert regs['d0']==cmd['operand'] and regs['a0']==cmd['operand'] and regs['d7']==cmd['target'] and regs['a1']==cmd['target']
            assert regs['d1']==(at_prefix['d1']&0xffff0000)|cmd['field_word']
            if b['pc']!=CALL:assert b['pc']==cmd['target']
        if b['pc']==BACK:assert b['a7']==STACK-10
        if b['pc']==0x4a376:
            after=next(x for x in bs[i+1:] if x['pc']==0x4a37a)
            for key,at in (('d0',0),('d7',2)):assert after['registers'][key]==sext(int.from_bytes(stack[at:at+2],'big'))
        if b['pc']==0x4a37e:
            assert b['a7']==STACK and regs['a0']==details['outer_a0'] and regs['a1'] in cursors
    # PVC after the call is computed from the restored bank WORD.
    ports=[x for x in trace['ordered_writes'] if x['kind']=='ports']
    for x in ports:
        if x['pc']==0x4a368:
            restored=next(w for w in trace['ordered_writes'] if w['pc']==BACK and w['address']==BANK)
            assert x['address']==0x2ffff2 and x['value']==word((restored['value']+1)<<12)
        if x['pc'] in (0x49fd0,0x4a342,0x4a0d0):assert x['address']==0x2ffff2 and x['value']==0x1000
        if x['pc'] in (0x49fd8,0x4a34a,0x4a36e,0x4a0d8):assert x['address']==0x2ffff0 and x['value']==0

def callee_records(trace,details,before):
    """Per callback: entry/return registers and callee-specific static expectations checked against native."""
    rows=[];bs=trace['boundaries']
    for i,b in enumerate(bs):
        if b['pc'] not in KNOWN:continue
        stack=bytes.fromhex(b['stack']);cmd=next(c for c in details['commands'] if c['cursor_after']==int.from_bytes(stack[6:10],'big'))
        back=next((x for x in bs[i+1:] if x['pc']==BACK),None)
        entry={k:b['registers'][k] for k in ('d0','d1','d7','a0','a1')}
        rows.append(dict(target=b['pc'],callee=KNOWN[b['pc']],command_address=cmd['opcode_address'],entry=entry,
            entry_stack=dict(a7=b['a7'],return_pc=int.from_bytes(stack[:4],'big'),bank=int.from_bytes(stack[4:6],'big'),
                outer_a1=int.from_bytes(stack[6:10],'big'),outer_a0=int.from_bytes(stack[10:14],'big')),
            returned_in_this_phase=back is not None,at_4a354=None if back is None else {k:back['registers'][k] for k in ('d0','d1','d7','a0','a1')}))
    return rows

def check_known_callee(case,details,row,trace,input_ram,program):
    """Callee effects for 2b3e8/2b3fa from the contract-restored semantics (independent Python model)."""
    a6=case['a6'];t=row['target'];cmd=next(c for c in details['commands'] if c['opcode_address']==row['command_address'])
    if t in (0x2b3e8,0x2b3fa):
        idx_at=a6+(0x7c if t==0x2b3e8 else 0x7d);idx=input_ram[idx_at-BASE];source=(cmd['operand']+idx*4)&0xffffff
        value=rom_long(program,source) if source<BASE else int.from_bytes(input_ram[source-BASE:source-BASE+4],'big')
        pc=0x2b3f2 if t==0x2b3e8 else 0x2b404
        rd=[r for r in trace['reads'] if r['pc']==pc];wr=[w for w in trace['ordered_writes'] if w['pc']==pc]
        assert [(r['address'],r['size'],r['value']) for r in rd]==[(source,4,value)]
        assert [(w['address'],w['size'],w['value']) for w in wr]==[(a6+0x78,4,value)]
        assert row['at_4a354']['d0']==idx*4 and row['at_4a354']['d1']==row['entry']['d1'] and row['at_4a354']['d7']==t
        assert row['at_4a354']['a0']==cmd['operand']
        return dict(index_address=idx_at,index=idx,source_address=source,source_kind='fixed' if source<BASE else 'ram',source_value=value,store_address=a6+0x78)
    return None

def check_sound_final(case,phases,traces,program):
    """47672 effects whose live operands are read after any wait (source word, $7e(a6))."""
    a6=case['a6'];reads=[r for tr in traces for r in tr['reads']];writes=[w for tr in traces for w in tr['ordered_writes']]
    hi=next(r for r in reads if r['pc']==0x47690);full=next(r for r in reads if r['pc']==0x47694);raw=next(r for r in reads if r['pc']==0x476aa)
    assert hi['address']==SOURCE and full['address']==SOURCE
    v=full['value'];low=v&255;doubled=(low*2)&255
    overflow=((low^doubled)&0x80)!=0
    index=(0x80 if overflow else doubled)&0xfe
    assert raw['address']==RAW+index and raw['value']==rom_word(program,RAW+index)
    assert any(w['pc']==0x47690 and w['address']==a6+0x7e and w['value']==hi['value'] for w in writes)
    back=[b for tr in traces for b in tr['boundaries'] if b['pc']==BACK][-1]
    entry_d1=[b for tr in traces for b in tr['boundaries'] if b['pc']==0x47672][-1]['registers']['d1']
    d1=0 if raw['value']==0 else (entry_d1&0xffff0000)|word(raw['value']-1)
    assert back['registers']['d1']==d1 and back['registers']['a0']==RAW and back['registers']['d7']==0x47672
    assert any(w['pc']==0x476b6 and w['address']==a6+0x12 and w['value']==d1&255 for w in writes)
    sound=any(b['pc']==0x3af8 for tr in traces for b in tr['boundaries'])
    return dict(source_word_live=v,raw_lookup_address=raw['address'],raw_lookup_word=raw['value'],callee_d1=d1,sound_called=sound)

def check_final(details,info,trace,output,incoming0,last_callee_d1):
    """RETURN state: terminal fetched live, outer A0 restored, untouched registers preserved."""
    r=info['result'];term=details['terminal']
    op=output[term-BASE]
    fetched=[x for x in trace['reads'] if x['pc']==0x4a000 and x['address']==term]
    assert len(fetched)==1 and fetched[0]['value']==op
    assert op in (0,0x28),hex(op)
    if op==0x28:assert info['carry'] is True and r['a1']==term+1 and r['d7']==0xffffffff and r['d1']==last_callee_d1
    else:
        assert output[term+1-BASE]==0 and info['carry'] is False and r['a1']==term+2 and r['d7']==0
        assert r['d1']==(last_callee_d1&0xffffff00)
    assert r['a0']==details['outer_a0']
    for k in ('d2','d3','d4','d5','a2','a3','a4','a5','a6'):assert r[k]==incoming0[k],k
    return 'finish-28-carry1' if op==0x28 else 'timer-00,00-carry0'

def poison(case,details,salt,live_terminal):
    """Pending-only host writes: consumed 3c bytes, outer object/script pointer, bank shadow, gates, WORD ring,
    callee live operands (source WORD, $7e(a6)) and optionally the not-yet-fetched terminal."""
    changes=[];a6=case['a6']
    def add(address,size,value):changes.append(dict(address=address,size=size,value=value&((1<<(8*size))-1)))
    c=details['commands'][0]
    add(c['opcode_address'],1,0x14);add(c['padding_address'],1,0x3c^salt);add(c['sel1_address'],2,0x001d^salt<<8)
    add(c['sel2_address'],2,0x0000^salt);add(c['operand_address'],4,0xdeadbeef^salt)
    add(a6+0x26,4,0x10fff0^(salt*2));add(a6+0x17,1,0x7f);add(a6+0x2c,2,0x7777^salt);add(BANK,2,0xbeef^salt)
    add(0x100012,1,1);add(0x10fd82,1,1);add(0x10fe80,1,0);add(0x10fd8d,1,0);add(0x104d7e,1,1);add(0x10f001,1,0x20)
    add(READ,2,0x7ff0^salt*2);add(WRITE,2,0x7ff0^salt*2)
    for i in range(4):add(WORDQ+2*i,2,(0x1f00|0x40+i)^salt)
    add(SOURCE,2,0x1234^salt);add(a6+0x7e,1,0x99^salt)
    if live_terminal:add(details['terminal'],2,0x28e7)
    return changes

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/animation_word_callback_native';folder.mkdir(parents=True,exist_ok=True)
    for old in folder.glob('case_*'):old.unlink()
    report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for a,b in RANGES:instructions.extend(disassemble_range(program,a,b-a,a))
    for r in instructions:assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
    jsr=[r for r in instructions if r['cpu_address']==CALL];assert jsr and jsr[0]['raw']=='4e91' and jsr[0]['size']==2
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    # Full raw first-WORD table scan: every one of the 16384 LONG slots in [42500,52500).
    scan=collections.defaultdict(list)
    for k in range(16384):
        slot=slot_of(k);value=rom_long(program,slot)
        if value in KNOWN:scan[value].append(dict(slot=slot,selectors=[k|a for a in (0,0x4000,0x8000,0xc000)]))
    assert {t:[s['slot'] for s in v] for t,v in scan.items()}=={0x2b3e8:[0x4a574],0x2b3fa:[0x4a578],0x47672:[0x4a57c]}
    data_ranges=[dict(name=n,cpu_address=a,rom_offset=a,size=s,sha256=sha(program[a:a+s])) for n,a,s in
        (('first-WORD dispatch LONG slots',0x42500,0x10000),('second-WORD field WORDs',0x4276c,0x10000),('47672 raw WORD lookup',RAW,256),
         ('fixed operand 6431a span',0x6431a,1024),('fixed operand vectors',0,1024),('fixed operand last ROM KiB',0xffc00,1024))]
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=RANGES,boundaries=BOUNDARIES,instructions=instructions,data_ranges=data_ranges,
        note='CPU address equals ROM file offset for these ranges in the canonical big-endian program.'),indent=2)+'\n')
    names=('tools/observe_animation_word_callback.py','tools/observe_object_sound_lookup.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py','artifacts/animation_word_callback_native/source.json')
    inputs={n:sha((root/n).read_bytes()) for n in names};oracle=oracle_provenance()
    observer=Observer(program,branches);rows=[];outcomes=collections.defaultdict(collections.Counter);artifacts={}
    def save(prefix,before,output,ports,trace):
        payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace)+'\n').encode()}
        for n,data in payloads.items():(folder/n).write_bytes(data);artifacts[n]=sha(data)
        return {n:sha(v) for n,v in payloads.items()}
    for index,case in enumerate(cases()):
        ram,regs,details=fixture(case,index,program);observer.prepare(ram,regs,case['external']);phases=[];traces=[];inputs_ram=[]
        assert all(c['callee']!='unsupported' for c in details['commands'])
        def observe(label,changes=()):
            info,before,output,ports,trace=observer.run();check_phase(case,details,info,trace,not phases)
            files=save('case_%04d_%s'%(index,label),before,output,ports,trace)
            for b in trace['branches']:outcomes[b['pc']][b['next_pc']]+=1
            info.update(phase=label,host_changes=list(changes),callbacks=callee_records(trace,details,before),files=files,
                input_ram_file='case_%04d_%s_input.bin'%(index,label),ram_file='case_%04d_%s_native.bin'%(index,label),
                ports_file='case_%04d_%s_ports.bin'%(index,label),trace_file='case_%04d_%s_trace.json'%(index,label),port_count=len(ports)//9)
            phases.append(info);traces.append(trace);inputs_ram.append(before);return info,trace,output
        begin,trace,output=observe('begin')
        if case['wait']==0:
            assert not begin['waiting']
        else:
            assert begin['waiting']
            first=begin['pending'];assert first['sound_phase']==(2 if case['wait']==2 else 1)
            assert first['outer_a0']==details['outer_a0'] and first['outer_a1']==details['commands'][0]['cursor_after'] and first['bank']==0
            assert first['inner_a0']==SOURCE
            def hold(label,salt):
                changes=poison(case,details,salt,case['poison']=='prefix+live-terminal');observer.mutate(changes);info,trace,_=observe(label,changes)
                previous=phases[-2]
                assert info['waiting'] and info['pending']==previous['pending'] and info['result']==previous['result']
                assert not trace['ordered_writes'] and not trace['boundaries'] and info['external_reads']==0 and info['port_count']==0
                assert all(r['address']==HEAD and r['pc']==WAIT and r['size']==2 for r in trace['reads'])
            def release(label,head):
                changes=[dict(address=HEAD,size=2,value=head)];observer.mutate(changes);info,trace,output=observe(label,changes)
                c=details['commands'][0]
                assert not any(PREFIX<=r['pc']<BACK or c['opcode_address']<=r['address']<c['cursor_after'] or r['kind'] in ('external',) for r in trace['reads'])
                assert not any(r['pc'] in (0x47678,0x4767a,0x4a31e,0x4a32c) for r in trace['reads'])
                assert not any(b['pc'] in (ENTRY,PREFIX,CALL,0x47672,0x3af8) for b in trace['boundaries'])
                return info,trace,output
            hold('hold',0x11)
            if case['wait']==3:
                mid,trace,_=release('high_to_low',(first['wait_d1']+1)&0x7f)
                assert mid['waiting'] and mid['pending']['sound_phase']==2 and mid['pending']['saved_low']==first['saved_low']
                assert any(r['pc']==0x3c00 and r['address']==STACK-24 and r['value']==first['saved_low'] for r in trace['reads'])
                hold('low_hold',0x22)
            ready,trace,output=release('ready',0xffff)
            assert not ready['waiting'] and ready['carry'] is not None
            # Bank WORD comes from the stack, not the poisoned shadow.
            assert any(w['pc']==BACK and w['address']==BANK and w['value']==0 for w in trace['ordered_writes'])
            assert any(r['pc']==0x47690 and r['address']==SOURCE and r['value']==(0x1234^0x22 if case['wait']==3 else 0x1234^0x11)>>8 for r in trace['reads'])
        final=phases[-1];assert final['final_pc']==RETURN and final['final_a7']==STACK+4
        callbacks=[cb for p in phases for cb in p['callbacks']]
        assert [cb['target'] for cb in callbacks]==[c['target'] for c in details['commands']]
        effects=[]
        for cb in callbacks:
            effects.append(check_known_callee(case,details,cb,traces[0],inputs_ram[0],program))
        sound=None
        if any(c['target']==0x47672 for c in details['commands']):
            sound=check_sound_final(case,phases,traces,program)
            src_hi=inputs_ram[0][SOURCE-BASE];obj=inputs_ram[0][case['a6']+0x7e-BASE]
            if not case['queue_alias']:assert sound['sound_called']==(src_hi!=obj)==case['sound']
            if not sound['sound_called']:
                cb=next(cb for cb in callbacks if cb['target']==0x47672)
                assert cb['at_4a354']['d0']==(cb['entry']['d0']&0xffffff00)|src_hi
        last=[b for tr in traces for b in tr['boundaries'] if b['pc']==BACK][-1]
        finals=[b for tr in traces for b in tr['boundaries'] if b['pc']==0x4a37a][-1]
        terminal=check_final(details,final,traces[-1],output,phases[0]['incoming'],last['registers']['d1'])
        assert final['result']['d0']==finals['registers']['d0']
        if case['overwrite_value'] is not None:
            assert terminal==('finish-28-carry1' if case['overwrite_value']>>24==0x28 else 'timer-00,00-carry0')
        if case['poison']=='prefix+live-terminal':assert terminal=='finish-28-carry1'
        if case['a6']==0xffffe:
            writes=[w for tr in traces for w in tr['ordered_writes']]
            alias=[j for j,w in enumerate(writes) if w['pc']==0x476b6 and w['address']==BANK and w['size']==1]
            restore=[j for j,w in enumerate(writes) if w['pc']==BACK and w['address']==BANK and w['size']==2]
            assert len(alias)==1 and len(restore)==1 and alias[0]<restore[0] and writes[restore[0]]['value']==0
        if case['queue_alias']:
            w=[w for tr in traces for w in tr['ordered_writes'] if w['pc']==0x3bcc]
            assert any(x['address']==SOURCE and x['value']==0x1ac0 for x in w) and sound['source_word_live']==0x1ac0
        rows.append(dict(case_index=index,fixture=case,details=details,callbacks=callbacks,callee_effects=effects,sound=sound,
            terminal_outcome=terminal,final_carry=final['carry'],total_external_reads=sum(p['external_reads'] for p in phases),phases=phases))
    # Unsupported actual targets: execute the unpatched prefix, stop at the first PC outside the supported ranges.
    unsupported=[]
    for j,case in enumerate(unsupported_cases()):
        index=10000+j;ram,regs,details=fixture(case,index,program);cmd=details['commands'][0]
        assert cmd['callee']=='unsupported';observer.prepare(ram,regs,0)
        info,before,output,ports,trace=observer.run(allow_unsupported=True);check_phase(case,details,info,trace,True)
        assert info['stopped_unsupported']['pc']==cmd['target'] and not any(x['pc']==cmd['target'] for x in trace['reads']+trace['ordered_writes'])
        files=save('case_%04d_unsupported_stop'%index,before,output,ports,trace)
        unsupported.append(dict(case_index=index,fixture=case,details=details,stop=info['stopped_unsupported'],stop_state=info['stop_state'],
            incoming=info['incoming'],result=info['result'],port_count=len(ports)//9,files=files,native_callee_executed=False,success=False,
            classification='unsupported callback: actual dispatch LONG is not 2b3e8/2b3fa/47672; prefix observed, callee not executed'))
    excluded=[]
    for sel in (0x3fff,):
        slot=slot_of(sel);target=rom_long(program,slot)
        assert target&1
        excluded.append(dict(sel1=sel,slot=slot,target=target,native_executed=False,success=False,
            classification='excluded: odd target (68000 address error); Unicorn address-error fidelity not relied upon'))
    # Negative guard controls: the observer stops (never stubs) when execution leaves the supported ranges.
    controls=[]
    for name,tail,kind,pc in (('next-opcode04-outside-ranges',0x0400,'unsupported-code',0x4a104),('next-opcode44-trap',0x4400,'trap',0x4a00a)):
        case=dict(cases()[0]);ram,regs,details=fixture(case,20000+len(controls),program)
        ram=bytearray(ram);put(ram,details['terminal'],2,tail);observer.prepare(bytes(ram),regs,0)
        try:observer.run();stopped=None
        except AssertionError:stopped=dict(observer.error)
        assert stopped is not None and stopped['kind']==kind and stopped['pc']==pc,(name,stopped)
        controls.append(dict(name=name,terminal_word=tail,stopped=stopped,artifacts_written=False))
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/n).read_bytes())==h for n,h in inputs.items())
    for n,h in artifacts.items():assert sha((folder/n).read_bytes())==h
    observed=collections.defaultdict(set)
    for r in rows:
        for c,cb in zip(r['details']['commands'],r['callbacks']):observed[hex(cb['target'])].add(hex(c['sel1']))
    second=sorted({hex(c['sel2']) for r in rows for c in r['details']['commands']})
    pending_rows=[r for r in rows if r['fixture']['wait']]
    report=dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,
        static_contract=dict(prefix=[hex(PREFIX),'0x4a382'],jsr=hex(CALL),return_pc=hex(BACK),opcode14_return_pc='0x4a43e',
            outer_stack=dict(S=STACK,return_4a354='S-14',bank_word='S-10',outer_a1_post_operand='S-8',outer_a0='S-4'),
            sound_high_wait=dict(a7='S-28',top=0x3c00,saved_low='S-24',return_4768e='S-22',inner_a0='S-18'),
            sound_low_wait=dict(a7='S-22',top=0x4768e,inner_a0='S-18'),verified_by_native_memory=True),
        raw_first_word_scan=dict(slots_scanned=16384,range=['0x42500','0x52500'],known_target_slots={hex(t):[dict(slot=hex(s['slot']),selectors=[hex(x) for x in s['selectors']]) for s in v] for t,v in sorted(scan.items())},
            other_raw_aliases_for_known_targets=[]),
        cases=len(rows),phases=sum(len(r['phases']) for r in rows),pending_chains=len(pending_rows),
        chains=dict(collections.Counter('wait%d/%s'%(r['fixture']['wait'],r['fixture']['poison']) for r in pending_rows)),
        cases_by_family=dict(collections.Counter(r['fixture']['family'] for r in rows)),
        observed_first_selectors_by_target={k:sorted(v) for k,v in sorted(observed.items())},observed_second_selectors=second,
        terminal_outcomes=dict(collections.Counter(r['terminal_outcome'] for r in rows)),
        total_external_reads=sum(r['total_external_reads'] for r in rows),total_native_ports=sum(p['port_count'] for r in rows for p in r['phases']),
        observed_branch_successors={hex(a):{hex(b):n for b,n in sorted(c.items())} for a,c in sorted(outcomes.items())},
        unsupported_stops=unsupported,excluded=excluded,guard_controls=controls,
        lookup_poisoning='not applicable: dispatch [42500,52500) and field [4276c,5276c) tables are fixed ROM (<100000); writing them would be a ROM patch',
        artifact_files=len(artifacts),artifact_manifest_sha256=sha(json.dumps(sorted(artifacts.items())).encode()),artifacts=dict(sorted(artifacts.items())),
        instruction_cap_per_run=CAP,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,results=rows,
        limitations=['Synthetic live-RAM fixtures; A5=108000; A6=102000 except bank-alias ffffe and next-opcode-overwrite 105f92; script at even 106000.',
            'Saved bank WORD is always 0 here: 49fca clears the shadow on every whole-49fc6 entry and no fixture reaches a nonzero save.',
            'No raw-table aliases other than 1d/1e/1f modular aliases exist for the three targets (full 16384-slot scan).',
            'Unsupported targets are executed only through the prefix; the first instruction of the target is not executed.',
            'No natural IRQ/Z80 consumer, cycle timing, physical mirror or full CCR claim; only RETURN carry recorded.',
            'Byte-queue head release and poisoning are host writes between phases, recorded in host_changes.',
            'No natural gameplay reachability claim; no other callback, opcode40, or full Goal completion claim.'],
        scope='Unpatched original whole49fc6 executing opcode3c (4a30c..4a382) -> JSR (A1) to actual dispatch target 2b3e8/2b3fa/47672, '
            'return 4a354, then 4a276 continuation to 00,00 or 28. Full64KiB RAM/15 registers/RTS carry/ordered PVC+bank/external reads/'
            'PC,read,write,boundary,stack traces per phase; same-CPU high, low, high->low sound waits with prefix poison and live terminal; '
            'no ROM patch/stubs/register injection/C++ comparison.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=report['pending_chains'],unsupported=len(unsupported),
        excluded=len(excluded),external_reads=report['total_external_reads'],ports=report['total_native_ports'],terminals=report['terminal_outcomes'],
        artifacts=len(artifacts),sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
