"""Unpatched47672/ca70/3af8, full native state and same-CPU waits."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program, disassemble_range
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from observe_screen_reset_full import BASE, STACK, STACK_START, RETURN, KEYS, REGS
from verify_stage_catalog import SOURCE_SHA256

ENTRY, WAIT, EXTERNAL=0x47672,0x3aea,0xd00046
RANGES=((ENTRY,0x476bc),(0xca70,0xca76),(0x3ac8,0x3c08))
RAW_START,RAW_END=0x4411e,0x4421e
RAW_SHA='eea1eddb352dfc10643395459d1afbd26ad22d1c5d3aa5c0fdf312052e458649'

def sha(data):return hashlib.sha256(data).hexdigest()
def put(ram,address,size,value):
    assert BASE<=address and address+size<=BASE+65536,(address,size)
    ram[address-BASE:address-BASE+size]=value.to_bytes(size,'big')
def cases():
    rows=[]
    def add(family,**kw):
        case=dict(family=family,a5=0x108000,source_word=0x5a01,a6=0x102000,
            sound=False,wait=0,mode=0,external=0,queue_alias=False)
        case.update(kw);rows.append(case)
    for value in range(256):
        add('all-low-BYTE-no-sound',source_word=0x5a00|value,
            a5=(0x108000,0x108002,0x1076a4,0x1176a2)[value%4])
    for mode,external in ((0,0),(1,0),(2,0),(3,0),(3,1),(3,255),(4,0),(5,0)):
        add('sound-immediate-gates-external',sound=True,mode=mode,external=external)
    for alias in ('source-high','source-low'):
        for sound in (False,True):
            add('live-object-destination-'+alias,sound=sound,a6=0x10095c+(alias=='source-low')-0x7e,
                source_word=0x5a01 if sound else 0x5a5a)
    for alias in ('source-high','source-low'):
        add('shifted-A5-no-sound-'+alias,a5=0x108002,a6=0x10095e+(alias=='source-low')-0x7e,source_word=0x5a5a)
    for alias in (False,True):
        for wait in (1,2,3):
            add('same-CPU-sound-wait-chain',sound=True,wait=wait,
                a6=0x1008df if alias else 0x102000,source_word=0x5a01)
    add('sound-signed-queue-write-aliases-live-source',sound=True,queue_alias=True)
    assert len(rows)==277
    return rows

def fixture(case,index):
    ram=bytearray(hashlib.shake_256(b'object-sound-lookup-'+bytes([index%4])).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=case['a5'],a6=case['a6'])
    source=case['a5']-0x76a4
    for at,size,value in ((0x100012,1,0),(0x104d7e,1,0),(0x10f001,1,0),
        (0x104d8a,2,0),(0x104d8c,2,0),(0x104d74,2,0),(0x104d76,2,0),
        (0x10fd82,1,0),(0x10fe80,1,0),(0x10fd8d,1,1)):
        put(ram,at,size,value)
    mode=case['mode']
    if mode==1:put(ram,0x104d7e,1,1)
    if mode==2:put(ram,0x100012,1,1);put(ram,0x10fd8d,1,0)
    if mode==3:put(ram,0x100012,1,1);put(ram,0x10fd82,1,1)
    if mode==4:put(ram,0x10f001,1,32)
    if mode==5:put(ram,0x104d8a,2,0);put(ram,0x104d8c,2,2);put(ram,0x104d82,2,0x1ac0)
    if case['wait']:
        for at,value in ((0x104d8a,0),(0x104d8c,6),(0x104d74,2 if case['wait']==2 else 1),
            (0x104d76,0),(0x104d82,0x0455),(0x104d84,0x0566),(0x104d86,0x0677),(0x104d88,0x0788)):
            put(ram,at,2,value)
    if case['queue_alias']:put(ram,0x104d8a,2,0xbbda);put(ram,0x104d8c,2,0xbbda)
    put(ram,source,2,case['source_word'])
    # Keep source-low alias different for sound, equal for no-sound. A
    # source-high alias can never trigger sound because both operands alias.
    if case['a6']+0x7e not in (source,source+1):
        put(ram,case['a6']+0x7e,1,(case['source_word']>>8)^(1 if case['sound'] else 0))
    return bytes(ram),regs

class Observer:
    """Same CPU continuation pattern used by verify_stage_hud_counter.Native."""
    def __init__(self,program,branch_pcs):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x300000,0x100000);self.cpu.mem_map(0xd00000,4096)
        self.baseline=self.cpu.context_save();self.branch_pcs=branch_pcs
        self.pcs=[];self.events=[];self.reads=[];self.boundaries=[];self.visits=0;self.error=None
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc in (ENTRY,0xca70,0x3af8,0x3ac8,0x4768e,0x47690):
                self.boundaries.append(dict(pc=pc,a7=c.reg_read(m.UC_M68K_REG_A7),registers=self.regs()))
            if pc==WAIT:
                head=int.from_bytes(c.mem_read(c.reg_read(m.UC_M68K_REG_A5)-0x328c,2),'big')
                if head==(c.reg_read(m.UC_M68K_REG_D1)&65535):
                    self.visits+=1
                    if self.visits==2:c.emu_stop()
                else:self.visits=0
            opcode=int.from_bytes(c.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:self.error=dict(kind='trap',pc=pc);c.emu_stop()
            if not any(start<=pc<end for start,end in RANGES):self.error=dict(kind='unexpected-code',pc=pc);c.emu_stop()
        def write(c,access,address,size,value,user):
            kind='ports' if address==0x3c0000 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1),kind=kind)
            self.events.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);c.emu_stop()
        def read(c,access,address,size,value,user):
            kind='raw-lookup' if RAW_START<=address and address+size<=RAW_END else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else 'external' if address==EXTERNAL else 'program' if address+size<=BASE else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind)
            if kind!='program':self.reads.append(event)
            if kind is None:self.error=dict(kind='unexpected-read',event=event);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(c,number,user):self.error=dict(kind='exception',number=number,pc=c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):
            self.cpu.hook_add(hook,callback)
    def regs(self):return {key:self.cpu.reg_read(reg)&0xffffffff for key,reg in zip(KEYS,REGS)}
    def prepare(self,ram,regs,external):
        c=self.cpu;c.context_restore(self.baseline);c.mem_write(BASE,ram);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'))
        c.mem_write(EXTERNAL,bytes([external]));c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):c.reg_write(reg,regs[key])
        c.reg_write(m.UC_M68K_REG_PC,ENTRY);self.stack_low=STACK
    def mutate(self,changes,external=255):
        for change in changes:self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
        self.cpu.mem_write(EXTERNAL,bytes([external]))
    def run(self):
        c=self.cpu;before=bytes(c.mem_read(BASE,65536));incoming=self.regs();start=c.reg_read(m.UC_M68K_REG_PC)
        self.pcs.clear();self.events.clear();self.reads.clear();self.boundaries.clear();self.visits=0;self.error=None
        c.emu_start(start,0xffffff,count=100000)
        pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc in (WAIT,RETURN),(self.error,hex(pc))
        result=self.regs();stack={};sound_phase=0;saved_low=0;saved_a0=0
        if pc==WAIT:
            assert self.visits==2
            top=int.from_bytes(c.mem_read(sp,4),'big');sound_phase={0x3c00:1,0x4768e:2}[top]
            assert sp==(STACK-14 if sound_phase==1 else STACK-8)
            assert int.from_bytes(c.mem_read(STACK-8,4),'big')==0x4768e
            saved_a0=int.from_bytes(c.mem_read(STACK-4,4),'big')
            saved_low=c.mem_read(sp+4,1)[0] if sound_phase==1 else result['d0']&255
            stack=dict(a7=sp,top_return=top,outer_return=0x4768e,saved_a0=saved_a0,
                raw=bytes(c.mem_read(STACK-18,22)).hex(),two_wait_visits=self.visits)
        else:assert sp==STACK+4
        assert bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        assert bytes(c.mem_read(0,BASE))==self.program[:BASE]
        self.stack_low=min([self.stack_low]+[e['address'] for e in self.events if e['kind']=='stack'])
        assert bytes(c.mem_read(STACK_START,self.stack_low-STACK_START))==b'\x5a'*(self.stack_low-STACK_START)
        replay=bytearray(before);ports=[]
        for e in self.events:
            if e['kind']=='ram':replay[e['address']-BASE:e['address']-BASE+e['size']]=e['value'].to_bytes(e['size'],'big')
            if e['kind']=='ports':ports.append(struct.pack('>BII',e['size'],e['address'],e['value']))
        output=bytes(c.mem_read(BASE,65536));assert output==bytes(replay)
        transitions=[dict(pc=a,next_pc=b) for a,b in zip(self.pcs,self.pcs[1:]+[pc]) if a in self.branch_pcs]
        return dict(incoming=incoming,result=result,waiting=pc==WAIT,sound_phase=sound_phase,saved_low=saved_low,saved_a0=saved_a0,
            final_pc=pc,final_a7=sp,pcs=self.pcs.copy(),ordered_writes=self.events.copy(),reads=self.reads.copy(),
            boundaries=self.boundaries.copy(),stack=stack,lowest_stack_write=self.stack_low,branches=transitions),before,output,b''.join(ports)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256 and sha(program[RAW_START:RAW_END])==RAW_SHA
    folder=root/'artifacts/object_sound_lookup';folder.mkdir(parents=True,exist_ok=True);report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for start,end in RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    for row in instructions:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    branches={row['cpu_address'] for row in instructions if row['mnemonic'].startswith('b') and row['mnemonic'] not in ('btst.b','bsr.w','bra.b','bra.w')}
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,
        raw_lookup=dict(cpu_address=RAW_START,rom_offset=RAW_START,size=256,sha256=RAW_SHA,raw=program[RAW_START:RAW_END].hex())),indent=2)+'\n')
    names=('tools/observe_object_sound_lookup.py','tools/verify_stage_hud_counter.py','tools/disassemble_program.py',
        'tools/verify_object_reset.py','tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    inputs['artifacts/object_sound_lookup/source.json']=sha((folder/'source.json').read_bytes())
    oracle=oracle_provenance()
    observer=Observer(program,branches);rows=[]
    for index,case in enumerate(cases()):
        ram,regs=fixture(case,index);observer.prepare(ram,regs,case['external']);phases=[]
        def observe(label,changes=()):
            info,before,output,ports=observer.run();prefix='case_%03d_%s'%(index,label)
            payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports}
            for name,data in payloads.items():(folder/name).write_bytes(data)
            info.update(phase=label,host_changes=list(changes),files={name:sha(data) for name,data in payloads.items()},
                input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',port_count=len(ports)//9)
            phases.append(info);return info,output
        begin,output=observe('begin');source_address=case['a5']-0x76a4
        actual_sound=any(b['pc']==0x3af8 for b in begin['boundaries'])
        assert actual_sound==bool(ram[source_address-BASE]!=ram[case['a6']+0x7e-BASE])
        if case['wait']:
            assert begin['waiting'] and begin['sound_phase']==(2 if case['wait']==2 else 1)
            assert begin['saved_a0']==source_address
            changes=[dict(address=source_address,size=2,value=0x1234),
                dict(address=case['a6']+0x7e,size=1,value=0x12),dict(address=0x100012,size=1,value=1),
                dict(address=0x10fd82,size=1,value=1),dict(address=0x10fd8d,size=1,value=0),dict(address=0x104d7e,size=1,value=1)]
            observer.mutate(changes);hold,held=observe('hold',changes)
            assert hold['waiting'] and hold['sound_phase']==begin['sound_phase'] and hold['result']==begin['result']
            assert not hold['ordered_writes'] and not hold['boundaries'] and all(r['kind']!='external' for r in hold['reads'])
            changes=[dict(address=0x104d74,size=2,value=2 if case['wait']==3 else 0xffff)]
            observer.mutate(changes);ready,output=observe('high_to_low' if case['wait']==3 else 'ready',changes)
            if case['wait']==3:
                assert ready['waiting'] and ready['sound_phase']==2 and ready['saved_a0']==source_address
                changes=[dict(address=0x104d74,size=2,value=0xffff)];observer.mutate(changes);ready,output=observe('ready',changes)
            assert not ready['waiting'] and not any(b['pc'] in (ENTRY,0xca70,0x3af8) for b in ready['boundaries'])
            assert not any(r['pc'] in (0x47678,0x4767a) or r['kind']=='external' for r in ready['reads'])
            assert any(r['pc']==0x47690 and r['address']==source_address and r['value']==0x12 for r in ready['reads'])
            assert any(r['pc']==0x47694 and r['address']==source_address and r['value']==(0x1212 if case['a6']+0x7e==source_address+1 else 0x1234) for r in ready['reads'])
        else:assert not begin['waiting']
        for phase in phases:
            assert phase['result']['a5']==regs['a5'] and phase['result']['a6']==regs['a6']
            for boundary in phase['boundaries']:
                if boundary['pc']==0x47690:assert boundary['registers']['a0']==source_address
        final=phases[-1]
        final_lookup=[r for r in final['reads'] if r['kind']=='raw-lookup']
        assert len(final_lookup)==1
        raw_word=final_lookup[0]['value']
        assert final['result']['a0']==RAW_START
        assert final['result']['d1']==(0 if raw_word==0 else (regs['d1']&0xffff0000)|((raw_word-1)&65535))
        if case['queue_alias']:
            assert any(w['pc']==0x3bcc and w['address']==source_address and w['value']==0x1ac0 for w in begin['ordered_writes'])
            assert any(r['pc']==0x47690 and r['address']==source_address and r['value']==0x1a for r in begin['reads'])
            assert any(r['pc']==0x47694 and r['address']==source_address and r['value']==0x1ac0 for r in begin['reads'])
        rows.append(dict(case_index=index,fixture=case,phases=phases))
    lookup=[r for row in rows for phase in row['phases'] for r in phase['reads'] if r['kind']=='raw-lookup']
    addresses=sorted({r['address'] for r in lookup});assert addresses==list(range(RAW_START,RAW_END,2))
    assert all(r['size']==2 and r['value']==int.from_bytes(program[r['address']:r['address']+2],'big') for r in lookup)
    outcomes=collections.defaultdict(collections.Counter)
    for row in rows:
        for phase in row['phases']:
            for branch in phase['branches']:outcomes[branch['pc']][branch['next_pc']]+=1
    assert all(digest==sha((root/name).read_bytes()) for name,digest in inputs.items())
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,cases=len(rows),phases=sum(len(r['phases']) for r in rows),
        pending_chains=6,total_native_ports=sum(p['port_count'] for r in rows for p in r['phases']),
        raw_lookup=dict(cpu_address=RAW_START,rom_offset=RAW_START,size=256,sha256=RAW_SHA,observed_addresses=addresses,read_count=len(lookup)),
        observed_branch_successors={hex(pc):{hex(target):n for target,n in sorted(counts.items())} for pc,counts in sorted(outcomes.items())},
        results=rows,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,
        scope='Unpatched original47672/ca70/full3af8 throughRTS or actual3aea wait. Full64KiB RAM/15registers, ordered RAM/stack/port writes, actual RAM/stack/raw/external reads. '
        'Six same-CPU chains retain native stack/CCR; high/low sound phase and saved A0 derived from native stack. Explicit source/object/gate poisoning and consumer release occur outside hooks; no prefix replay. '
        'ArbitraryA5 only in no-sound cases; sound cases canonicalA5. Includes source-low object alias and signed sound queue append overwriting live source. '
        'Observed branch outcomes only, not complete sound gate coverage. No C++/IRQ/natural scheduler/cycle/physicalmirror/fullCCR claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=6,ports=report['total_native_ports'],lookup_addresses=len(addresses),sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
