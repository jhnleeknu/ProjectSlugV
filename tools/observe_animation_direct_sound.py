"""Immutable original whole49fc6 opcode30->3af8 direct sound with same-CPU waits; no C++ oracle.

Each case runs the unpatched canonical program from 49fc6 with a synthetic live-RAM script
(opcode30 commands followed by the 00,00 timer exit). A run stops only at the caller RETURN,
or at the actual 3aea byte-queue wait after two consecutive equal head visits. Pending runs
resume on the same Unicorn context; between phases the host only writes recorded RAM/external
changes (poison and explicit byte-queue head release). Nothing patches code or registers.
"""
import collections
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from observe_object_sound_lookup import (put,sha,oracle_provenance,make_cpu,load_verified_program,disassemble_range,
    BASE,STACK,STACK_START,RETURN,KEYS,REGS,SOURCE_SHA256)
import hashlib

ENTRY,WAIT,EXTERNAL=0x49fc6,0x3aea,0xd00046
A5,A6,SCRIPT=0x108000,0x102000,0x106000
HEAD,TAIL,BYTEQ,SPECIAL=0x104d74,0x104d76,0x104cf4,0x104d7b
WORDQ,READ,WRITE=0x104d82,0x104d8a,0x104d8c
GATES=dict(g100012=(0x100012,1),g10fd82=(0x10fd82,1),g10fe80=(0x10fe80,1),g10fd8d=(0x10fd8d,1),g104d7e=(0x104d7e,1),g10f001=(0x10f001,1))
RANGES=((ENTRY,0x4a0e4),(0x4a276,0x4a27e),(0x4a2da,0x4a2f2),(0x3ac8,0x3c08))
BOUNDARIES=(ENTRY,0x49ffe,0x4a2da,0x4a2e2,0x4a2e6,0x3af8,0x3b98,0x3bcc,0x3be4,0x3bf8,0x3ac8,0x3c00,0x4a2ec,0x4a2f0,0x4a276,0x4a0ca)
PVC_PCS=(0x49fd0,0x49fd8,0x4a0d0,0x4a0d8);BANK_PCS=(0x49fca,0x4a0ca)
CAP=20000

def word(value):return value&65535
def signed(value):return value-0x10000 if value&0x8000 else value

def cases():
    rows=[]
    def add(family,commands,**kw):
        case=dict(family=family,commands=list(commands),gates={},external=0,head=0x40,tail=0,read=0,write=0,
            entries=[0x0455,0x0566,0x0677,0x0788],chain='none',alias='none')
        case.update(kw);rows.append(case)
    words=sorted({h<<8|l for h in list(range(0x21))+[0x7f,0x80,0xff] for l in (0x1f,0x20,0xff)}|{0,0x80,0x1000,0x2000,0x7fff,0x8000,0xffff})
    for w in words:add('category-open-gates-append',[w])
    for value in (1,0x80):
        for w in (0x0020,0x0fff,0x1000,0x1020,0x1fff):add('gate-104d7e',[w],gates=dict(g104d7e=value))
    for value in (0x20,0xdf,0xff):
        for w in (0x0020,0x00ff,0x0120,0x0420):add('gate-10f001-bit5',[w],gates=dict(g10f001=value))
    for w in (0x0020,0x00ff,0x0420):add('gate-100012-high-zero',[w],gates=dict(g100012=1))
    for value in (0,2,0xff):add('gate-100012-not-one',[0x0420],gates=dict(g100012=value,g10fd82=1,g10fd8d=0))
    for fd82,fe80,fd8d in ((0,0,1),(0,0,0),(1,1,1),(1,1,0),(0,1,0)):
        add('gate-fd82-fe80-fd8d',[0x0420],gates=dict(g100012=1,g10fd82=fd82,g10fe80=fe80,g10fd8d=fd8d))
    for external in (0,1,0x80,0xff):
        for fd8d in (0,1):
            add('external-gate',[0x0420],gates=dict(g100012=1,g10fd82=1,g10fe80=0,g10fd8d=fd8d),external=external)
    add('external-gate-then-104d7e',[0x1020],gates=dict(g100012=1,g10fd82=1,g10fe80=0,g10fd8d=1,g104d7e=1),external=0)
    for external in (0,1):
        add('external-two-commands-one-invocation',[0x0420,0x0520],gates=dict(g100012=1,g10fd82=1,g10fe80=0,g10fd8d=1),external=external)
    # Four-entry WORD ring: full sends the oldest entry, duplicate move/no-op, popped special/zero entries.
    for read,write in ((0,6),(2,0),(4,2),(6,4)):add('word-ring-full-send',[0x0420],read=read,write=write)
    for read,write in ((0,0),(2,2),(0,2),(0,4),(6,2)):add('word-ring-append-no-send',[0x0420],read=read,write=write)
    for popped in (0x0000,0x0080,0x0300,0x0003,0x0303,0x0488,0x1f20,0xff88,0x8001):
        add('word-ring-popped-entry',[0x0420],read=0,write=6,entries=[popped,0x0566,0x0677,0x0788])
    for at in (0,1,2):
        entries=[0x0455,0x0566,0x0677,0x0788];entries[at]=0x0420
        add('word-ring-duplicate',[0x0420],read=0,write=6,entries=entries)
    add('word-ring-duplicate-wrap',[0x0420],read=4,write=2,entries=[0x0420,0x0566,0x0677,0x0788])
    for tail in (0x7f,0x7e,0x1234,0xff00):add('byte-queue-tail-index',[0x0420],read=0,write=6,tail=tail,head=(word(tail)+0x40)&0x7f)
    add('byte-queue-special-03',[0x0420],read=0,write=6,entries=[0x0303,0x0566,0x0677,0x0788],head=1,tail=0)
    # Signed WORD-ring index aliases (both indices equal, so the append store uses the raw signed index).
    # next-terminal stores 0020 over the 00,00 exit, so the live fetch executes timer opcode00 with BYTE20.
    for name,target,w in (('object-pointer',A6+0x26,0x0420),('own-consumed-word',SCRIPT+2,0x0420),('next-terminal',SCRIPT+4,0x0020),
            ('read-index',READ,0x0420),('write-index',WRITE,0x0420)):
        index=word(target-WORDQ)
        add('word-ring-signed-alias',[w],read=index,write=index,alias=name)
    # Same-CPU waits.
    for chain in ('high','low','high_to_low'):
        for popped in (0x0455,0x0488):
            for tail in (0,0x7f):
                add('same-CPU-wait',[0x04a0],read=0,write=6,entries=[popped,0x0566,0x0677,0x0788],tail=tail,chain=chain)
    for chain in ('high','low'):
        add('same-CPU-wait-after-external',[0x04a0],read=0,write=6,chain=chain,gates=dict(g100012=1,g10fd82=1,g10fe80=0,g10fd8d=1),external=0)
        add('same-CPU-wait-tail-alias',[0x04a0],read=0,write=6,chain=chain,tail=0xff00)
    add('same-CPU-wait-sequential',[0x04a0,0x0520],read=0,write=6,chain='sequential')
    add('same-CPU-wait-sequential-external',[0x04a0,0x0520],read=0,write=6,chain='sequential',gates=dict(g100012=1,g10fd82=1,g10fe80=0,g10fd8d=1),external=0)
    return rows

def chain_head(case):
    tail=word(case['tail']);first=(tail+1)&0x7f
    return {'none':case['head'],'high':first,'high_to_low':first,'sequential':first,'low':(tail+2)&0x7f}[case['chain']]

def fixture(case,index):
    ram=bytearray(hashlib.shake_256(b'animation-direct-sound-'+str(index).encode()).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=A5,a6=A6)
    for address,size,value in ((A6+0x26,4,SCRIPT),(A6+0x2a,2,0),(A6+0x2c,2,256),(A6+0x17,1,0),(0x100010,2,0xbeef),
            (SPECIAL,1,0),(HEAD,2,chain_head(case)),(TAIL,2,case['tail']),(READ,2,case['read']),(WRITE,2,case['write'])):
        put(ram,address,size,value)
    for i,entry in enumerate(case['entries']):put(ram,WORDQ+2*i,2,entry)
    for name,(address,size) in GATES.items():put(ram,address,size,case['gates'].get(name,1 if name=='g10fd8d' else 0))
    cursor=SCRIPT;commands=[]
    for i,value in enumerate(case['commands']):
        put(ram,cursor,4,0x30000000|(0xa5^i)<<16|value)
        commands.append(dict(opcode_address=cursor,padding_address=cursor+1,word_address=cursor+2,word=value,cursor_after=cursor+4));cursor+=4
    put(ram,cursor,2,0)
    details=dict(commands=commands,terminal=cursor,outer_a0=A6+0x26)
    if case['alias']!='none':details['alias_store_address']=WORDQ+signed(case['read'])
    # Controlled setup must not overlap; signed aliases are the intended exception and are listed above.
    spans=[(A6+0x17,A6+0x2e),(SCRIPT,cursor+2),(HEAD,HEAD+4),(SPECIAL,SPECIAL+1),(WORDQ,WRITE+2)]+[(a,a+s) for a,s in GATES.values()]
    for i,(a,b) in enumerate(spans):
        for c,d in spans[i+1:]:assert b<=c or d<=a,('fixture overlap',hex(a),hex(c))
    return bytes(ram),regs,details

class Observer:
    def __init__(self,program,branches):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x2ff000,4096);self.cpu.mem_map(0xd00000,4096)
        self.baseline=self.cpu.context_save();self.branch_pcs=branches
        self.pcs=[];self.reads=[];self.writes=[];self.boundaries=[];self.error=None;self.visits=0
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc in BOUNDARIES:
                sp=c.reg_read(m.UC_M68K_REG_A7)
                self.boundaries.append(dict(pc=pc,a7=sp,registers=self.regs(),stack=bytes(c.mem_read(sp,max(0,STACK+4-sp))).hex()))
            if not any(a<=pc<b for a,b in RANGES):self.error=dict(kind='unsupported-code',pc=pc);c.emu_stop();return
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
            kind='ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else 'external' if address==EXTERNAL and size==1 else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind);self.reads.append(event)
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
            if x['address']==EXTERNAL:self.cpu.mem_write(EXTERNAL,bytes([x['value']]))
            else:put_live(self.cpu,x)
    def run(self):
        c=self.cpu;before=bytes(c.mem_read(BASE,65536));incoming=self.regs();start=c.reg_read(m.UC_M68K_REG_PC)
        self.pcs.clear();self.reads.clear();self.writes.clear();self.boundaries.clear();self.error=None;self.visits=0
        c.emu_start(start,0xffffff,count=CAP);pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        if self.error is None and pc not in (RETURN,WAIT):self.error=dict(kind='instruction-cap-or-stop',pc=pc,instructions=len(self.pcs))
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
            pending.update(a7=sp,top_return=top,return_4a2ec_at=STACK-12,outer_a0=self.long(STACK-8),outer_a1=self.long(STACK-4),
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
            branches=[dict(pc=a,next_pc=b) for a,b in zip(self.pcs,self.pcs[1:]) if a in self.branch_pcs])
        info=dict(incoming=incoming,result=result,waiting=pc==WAIT,carry=carry,pending=pending,final_pc=pc,final_a7=sp,
            lowest_stack_write=self.low,instructions=len(self.pcs)-(1 if pc==RETURN else 0),
            external_reads=sum(1 for r in self.reads if r['kind']=='external'))
        return info,before,output,b''.join(ports),trace

def put_live(cpu,change):
    assert BASE<=change['address'] and change['address']+change['size']<=BASE+65536
    cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))

def summarize_calls(trace):
    """Callee exits: the RTS executed immediately before each 4a2ec."""
    pcs=trace['pcs'];return [pcs[i-1] for i in range(1,len(pcs)) if pcs[i]==0x4a2ec]

def check_phase(case,details,info,trace,first):
    """Structural invariants valid for every phase of every case."""
    for x in trace['ordered_writes']:
        if x['kind']=='ports':assert x['pc'] in PVC_PCS,x
        if x['kind']=='ram' and x['address']<=0x100010<x['address']+x['size']:
            assert x['pc'] in BANK_PCS,x
    for r in trace['reads']:
        if r['kind']=='external':assert r['pc']==0x3b54 and r['size']==1
        for cmd in details['commands']:
            assert not r['address']<=cmd['padding_address']<r['address']+r['size'],('padding read',r)
    entries=[b for b in trace['boundaries'] if b['pc']==ENTRY]
    assert len(entries)==(1 if first else 0)
    for b in trace['boundaries']:
        stack=bytes.fromhex(b['stack'])
        if b['pc']==0x3af8:
            # Static stack from the contract: S-12 return 4a2ec, S-8 outer A0, S-4 outer A1 (after the WORD).
            assert b['a7']==STACK-12 and stack[:4]==(0x4a2ec).to_bytes(4,'big')
            a0,a1=int.from_bytes(stack[4:8],'big'),int.from_bytes(stack[8:12],'big')
            assert a0==details['outer_a0'] and a0==b['registers']['a0'] and a1==b['registers']['a1']
            assert any(a1==cmd['cursor_after'] for cmd in details['commands'])
            assert b['registers']['d7']==0x30 and b['registers']['d0']>>16==0
        if b['pc']==0x4a2ec:
            assert b['a7']==STACK-8 and b['registers']['d7']==0x30
        if b['pc']==0x4a2f0:
            assert b['a7']==STACK and b['registers']['a0']==details['outer_a0']
            assert any(b['registers']['a1']==cmd['cursor_after'] for cmd in details['commands'])

def restoration(trace):
    """D0/D7 at 4a2ec versus a hypothetical WORD sign-extension restore (as in the 14 callback path)."""
    rows=[];bs=trace['boundaries']
    for i,b in enumerate(bs):
        if b['pc']!=0x4a2ec:continue
        after=next(x for x in bs[i+1:] if x['pc']==0x4a2f0)
        d0=b['registers']['d0'];d7=b['registers']['d7']
        assert after['registers']['d0']==d0 and after['registers']['d7']==d7
        low=d0&65535;sign=low|0xffff0000 if low&0x8000 else low
        rows.append(dict(d0_after_call=d0,d7_after_call=d7,d0_after_movem=after['registers']['d0'],d7_after_movem=after['registers']['d7'],
            d0_upper_word_zero=d0>>16==0,d0_low_byte_ge_80=bool(d0&0x80),
            byte_sign_extension_would_differ=(d0&0xff|(0xffffff00 if d0&0x80 else 0))!=d0,word_sign_extension_would_differ=sign!=d0))
    return rows

def poison(details,consumed,salt,full):
    """Pending-only host writes. Consumed command bytes/object/bank always; gates/rings/external unless a later
    command of the same invocation still has to evaluate them."""
    changes=[]
    def add(address,size,value):changes.append(dict(address=address,size=size,value=value&((1<<(8*size))-1)))
    for cmd in details['commands'][:consumed]:
        add(cmd['opcode_address'],1,0x44);add(cmd['padding_address'],1,0x3c^salt);add(cmd['word_address'],2,0x0303^salt)
    add(A6+0x26,4,0x10fff0^(salt*2));add(A6+0x17,1,0x7f);add(A6+0x2c,2,0x7777^salt);add(0x100010,2,0x1234^salt)
    if not full:return changes
    add(0x100012,1,1);add(0x10fd82,1,1);add(0x10fe80,1,0);add(0x10fd8d,1,0);add(0x104d7e,1,1);add(0x10f001,1,0x20)
    add(READ,2,0x7ff0^salt*2);add(WRITE,2,0x7ff0^salt*2)
    for i in range(4):add(WORDQ+2*i,2,(0x1f00|0x40+i)^salt)
    add(SPECIAL,1,0x5a^salt)
    changes.append(dict(address=EXTERNAL,size=1,value=0x81^salt))
    return changes

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/animation_direct_sound_native';folder.mkdir(parents=True,exist_ok=True)
    for old in folder.glob('case_*'):old.unlink()
    report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for a,b in RANGES:instructions.extend(disassemble_range(program,a,b-a,a))
    for r in instructions:assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=RANGES,boundaries=BOUNDARIES,instructions=instructions,
        note='CPU address equals ROM file offset for these ranges in the canonical big-endian program.'),indent=2)+'\n')
    names=('tools/observe_animation_direct_sound.py','tools/observe_object_sound_lookup.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py','artifacts/animation_direct_sound_native/source.json')
    inputs={n:sha((root/n).read_bytes()) for n in names};oracle=oracle_provenance()
    observer=Observer(program,branches);rows=[];outcomes=collections.defaultdict(collections.Counter);exits=collections.Counter()
    for index,case in enumerate(cases()):
        ram,regs,details=fixture(case,index);observer.prepare(ram,regs,case['external']);phases=[];calls=[]
        def observe(label,changes=()):
            info,before,output,ports,trace=observer.run();check_phase(case,details,info,trace,not phases)
            prefix='case_%04d_%s'%(index,label)
            payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace)+'\n').encode()}
            for n,data in payloads.items():(folder/n).write_bytes(data)
            callee_exits=summarize_calls(trace);calls.extend(callee_exits)
            for b in trace['branches']:outcomes[b['pc']][b['next_pc']]+=1
            info.update(phase=label,host_changes=list(changes),callee_exits=callee_exits,after_call=restoration(trace),
                callee_entries=sum(1 for b in trace['boundaries'] if b['pc']==0x3af8),
                files={n:sha(v) for n,v in payloads.items()},input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',
                ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json',port_count=len(ports)//9)
            phases.append(info);return info,trace
        begin,trace=observe('begin')
        chain=case['chain']
        if chain=='none':
            assert not begin['waiting'] and len(calls)==len(case['commands'])
        else:
            assert begin['waiting']
            first=begin['pending'];expected_phase=2 if chain=='low' else 1
            assert first['sound_phase']==expected_phase and first['outer_a0']==details['outer_a0'] and first['outer_a1']==details['commands'][0]['cursor_after']
            captured=first['saved_low']
            low_write_value=None
            def hold(label,salt,consumed=1,full=True):
                changes=poison(details,consumed,salt,full);observer.mutate(changes);info,trace=observe(label,changes)
                previous=phases[-2]
                assert info['waiting'] and info['pending']==previous['pending'] and info['result']==previous['result']
                assert not trace['ordered_writes'] and not trace['boundaries'] and info['external_reads']==0 and info['port_count']==0
                assert all(r['address']==HEAD and r['pc']==WAIT for r in trace['reads'])
            def release(label,head):
                changes=[dict(address=HEAD,size=2,value=head)];observer.mutate(changes);info,trace=observe(label,changes)
                assert info['external_reads']==0 or chain=='sequential'
                assert not any(r['address'] in (c['opcode_address'],c['word_address']) for c in details['commands'][:1] for r in trace['reads'])
                return info,trace
            def check_low(trace,expected,resumed_phase):
                # Resuming a high wait stores high then low; resuming a low wait stores only low.
                stores=[w for w in trace['ordered_writes'] if w['pc']==0x3af0]
                at=1 if resumed_phase==1 else 0
                assert len(stores)>at and stores[at]['value']==expected,(stores,expected)
            hold('hold',0x11,1,chain!='sequential')
            if chain=='high_to_low':
                mid,trace=release('mid',(first['wait_d1']+1)&0x7f)
                assert mid['waiting'] and mid['pending']['sound_phase']==2 and mid['pending']['saved_low']==captured
                assert mid['pending']['outer_a1']==details['commands'][0]['cursor_after']
                assert any(r['pc']==0x3c00 and r['address']==STACK-14 and r['value']==captured for r in trace['reads'])
                assert sum(1 for w in trace['ordered_writes'] if w['pc']==0x3af0)==1
                hold('low_hold',0x22)
            if chain=='sequential':
                # First high/low use slots wait_d1-1/wait_d1; second high computes wait_d1+2.
                mid,trace=release('first_ready_second_waits',(first['wait_d1']+2)&0x7f)
                check_low(trace,captured,1)
                assert mid['waiting'] and mid['pending']['sound_phase']==1 and mid['pending']['outer_a1']==details['commands'][1]['cursor_after']
                assert sum(1 for b in trace['boundaries'] if b['pc']==0x3af8)==1
                hold('second_hold',0x33,2,True);captured=mid['pending']['saved_low']
            resumed=phases[-1]['pending']['sound_phase']
            ready,trace=release('ready',(phases[-1]['pending']['wait_d1']+0x40)&0x7f)
            assert not ready['waiting'] and ready['carry'] is not None
            if chain in ('high','sequential'):
                assert any(r['pc']==0x3c00 and r['address']==STACK-14 and r['value']==captured for r in trace['reads'])
            check_low(trace,captured,resumed)
            assert not any(b['pc'] in (ENTRY,0x4a2da,0x3af8) for b in trace['boundaries'])
        final=phases[-1];assert final['final_pc']==RETURN and final['final_a7']==STACK+4
        assert len(calls)==len(case['commands']),(calls,case['commands'])
        for x in calls:exits[x]+=1
        a0_publications=[w for p in phases for w in json.loads((folder/p['trace_file']).read_text())['ordered_writes'] if w['pc']==0x4a278]
        assert [w['value'] for w in a0_publications]==[c['cursor_after'] for c in details['commands']]
        assert all(w['address']==details['outer_a0'] and w['size']==4 for w in a0_publications)
        rows.append(dict(case_index=index,fixture=case,details=details,callee_exits=calls,
            total_external_reads=sum(p['external_reads'] for p in phases),phases=phases))
    # Negative guard controls: the observer must stop (not stub) when execution leaves the supported ranges.
    controls=[]
    for name,tail,kind,pc in (('next-opcode04-outside-ranges',0x0400,'unsupported-code',0x4a104),('next-opcode44-trap',0x4400,'trap',0x4a00a)):
        case=dict(cases()[0]);case['commands']=[0x0420];ram,regs,details=fixture(case,len(controls)+100000)
        ram=bytearray(ram);put(ram,details['terminal'],2,tail);observer.prepare(bytes(ram),regs,0)
        try:observer.run();stopped=None
        except AssertionError:stopped=dict(observer.error)
        assert stopped is not None and stopped['kind']==kind and stopped['pc']==pc,(name,stopped)
        controls.append(dict(name=name,terminal_word=tail,stopped=stopped,artifacts_written=False))
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/n).read_bytes())==h for n,h in inputs.items())
    pending_rows=[r for r in rows if r['fixture']['chain']!='none']
    report=dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,cases=len(rows),phases=sum(len(r['phases']) for r in rows),
        pending_chains=len(pending_rows),chains_by_kind=dict(collections.Counter(r['fixture']['chain'] for r in pending_rows)),
        cases_by_family=dict(collections.Counter(r['fixture']['family'] for r in rows)),
        callee_exit_counts={hex(pc):n for pc,n in sorted(exits.items())},
        total_external_reads=sum(r['total_external_reads'] for r in rows),
        total_native_ports=sum(p['port_count'] for r in rows for p in r['phases']),
        returned_carry_counts=dict(collections.Counter(str(r['phases'][-1]['carry']) for r in rows)),
        observed_branch_successors={hex(a):{hex(b):n for b,n in sorted(c.items())} for a,c in sorted(outcomes.items())},
        static_stack=dict(high_wait=dict(a7='S-18',top=0x3c00,saved_low='S-14',return_4a2ec='S-12',outer_a0='S-8',outer_a1='S-4'),
            low_wait=dict(a7='S-12',top=0x4a2ec,outer_a0='S-8',outer_a1='S-4'),S=STACK,verified_by_native_memory=True),
        guard_controls=controls,instruction_cap_per_run=CAP,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,results=rows,
        limitations=['Synthetic live-RAM fixtures; canonical A5=108000 and A6=102000 only; script at even 106000.',
            'Odd WORD-ring indices/aliases are not exercised: Unicorn M68000 address-error fidelity is not relied upon.',
            'No natural IRQ/Z80 consumer, cycle timing, physical mirror or full CCR claim; only RETURN carry recorded.',
            'Byte-queue head release and poisoning are host writes between phases, recorded in host_changes.',
            'Callee exit categories are observed outcomes for the listed fixtures, not a proof of complete gate coverage.'],
        scope='Unpatched original whole49fc6 executing opcode30 (4a2da) -> JSR 3af8 on synthetic live-RAM scripts, terminated by 00,00. '
            'Full64KiB RAM/15 registers/RTS carry/ordered PVC+bank/external read count/PC,read,write,stack traces; same-CPU high, low, '
            'high->low and sequential waits with poisoning; no ROM patch/stubs/register injection/C++ comparison.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=report['pending_chains'],
        external_reads=report['total_external_reads'],ports=report['total_native_ports'],exits=report['callee_exit_counts'],
        sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
