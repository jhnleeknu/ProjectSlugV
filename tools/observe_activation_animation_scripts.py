"""Full unpatched49fc6 on actual fixed scripts; no C++ comparison."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program,disassemble_range
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from observe_screen_reset_full import BASE,STACK,STACK_START,RETURN,KEYS,REGS
from verify_stage_catalog import SOURCE_SHA256

ENTRY,WAIT,CAP=0x49fc6,0xcda4,500000
BOUNDARIES=(ENTRY,0x4a10c,0xcd58,0x4a200,0x4a222,0x4a226,0x4a22a)
CODE_RANGES=((ENTRY,0x4a22c),(0x4a276,0x4a27e),(0x4a3ac,0x4a3b8),(0xcd50,0xce02))
SCRIPTS=((0x48980,65),(0x489c2,80))
def sha(data):return hashlib.sha256(data).hexdigest()
def put(ram,at,size,value):
    assert at>=0 and at+size<=len(ram)
    ram[at:at+size]=value.to_bytes(size,'big')
def cases():
    rows=[]
    def add(family,**values):
        row=dict(family=family,script=0x48980,timer=0,speed=256,flags=0,counter=0,
            flash_flag=0,flash_phase=0,x=160,y=384,queue='normal',pending=False,initial_bank=3)
        row.update(values);rows.append(row)
    for script,timer,flags in itertools.product((0x48980,0x489c2),(0,1,0x7f,0x100,0x7fff,0x8000,0xffff),(0,1,2,0x43)):
        add('actual-script-timer-flags',script=script,timer=timer,flags=flags)
    for script,counter in itertools.product((0x48980,0x489c2),(0,1,0x7f,0x80,0xff)):
        add('signed-positive-object-counter',script=script,counter=counter)
    for script,flash in itertools.product((0x48980,0x489c2),((0,1),(8,0),(8,1))):
        add('actual-flash-draw-skip',script=script,flash_flag=flash[0],flash_phase=flash[1])
    for script,kind in itertools.product((0x48980,0x489c2),('normal','deferred','clip-x','clip-y','full','wide-bank')):
        add('queue-'+kind,script=script,queue=kind,flags=0x40 if kind=='deferred' else 0,
            x=0x8000 if kind=='clip-x' else 160,y=0 if kind=='clip-y' else 384,
            initial_bank=0xffff if kind=='wide-bank' else 3)
    for script,deferred in itertools.product((0x48980,0x489c2),(False,True)):
        add('same-CPU-current-draw-wait',script=script,pending=True,flags=0x40 if deferred else 0,
            queue='deferred' if deferred else 'normal')
    for bank in (0,0xffff):add('null-pointer-early-return',script=0,initial_bank=bank)
    assert len(rows)==90;return rows
def fixture(case,index):
    ram=bytearray(hashlib.shake_256(b'activation-animation-'+bytes([index%4])).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=0x108000,a6=0x102000)
    for at,size,value in ((0x10,2,case['initial_bank']),(0xf,1,case['flash_phase']),
        (0x2012,4,0xffff1500|case['flags']),(0x2016,1,1),(0x2017,1,case['counter']),
        (0x2019,1,21),(0x201a,1,22),(0x201b,1,23),(0x201c,1,24),
        (0x201e,2,13),(0x2020,2,0xea if case['script']!=0x489c2 else 0xf2),
        (0x2026,4,case['script']),(0x202a,2,case['timer']),(0x202c,2,case['speed']),
        (0x2042,2,case['x']),(0x2046,2,case['y']),(0x2053,1,3),(0x2061,1,case['flash_flag']),
        (0x9152,4,0xcd50),(0x8d34,2,2 if case['pending'] or case['queue']=='full' else 0x100),
        (0x8d36,2,4 if case['pending'] else 2),(0x8d38,2,0),(0x8d3a,2,0),(0x914e,2,0)):
        put(ram,at,size,value)
    for i in range(256):put(ram,0x8b34+i*2,2,i*12)
    return bytes(ram),regs

class Observer:
    def __init__(self,program,branch_pcs):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x2ff000,4096)
        self.baseline=self.cpu.context_save();self.branch_pcs=branch_pcs
        self.pcs=[];self.events=[];self.reads=[];self.boundaries=[];self.opcodes=[];self.error=None;self.visits=0
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc in BOUNDARIES:
                sp=c.reg_read(m.UC_M68K_REG_A7)
                self.boundaries.append(dict(pc=pc,a7=sp,registers=self.regs(),
                    stack_at_sp=bytes(c.mem_read(sp,min(26,STACK+4-sp))).hex()))
            if pc==0x4a000:
                address=c.reg_read(m.UC_M68K_REG_A1)
                self.opcodes.append(dict(address=address,value=c.mem_read(address,1)[0]))
            if pc==0xcd5c:
                if c.reg_read(m.UC_M68K_REG_A0)!=0xcd50:self.error=dict(kind='unsupported-callback',pc=pc);c.emu_stop()
            if pc==WAIT:
                consumer=int.from_bytes(c.mem_read(0x108d34,2),'big')
                if consumer!=(c.reg_read(m.UC_M68K_REG_D4)&65535):
                    self.visits+=1
                    if self.visits==2:c.emu_stop()
                else:self.visits=0
            if not any(start<=pc<end for start,end in CODE_RANGES):self.error=dict(kind='unexpected-code',pc=pc);c.emu_stop()
            opcode=int.from_bytes(c.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:self.error=dict(kind='trap',pc=pc);c.emu_stop()
        def write(c,access,address,size,value,user):
            kind='ports' if address in (0x2ffff0,0x2ffff2) and size==2 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1),kind=kind);self.events.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);c.emu_stop()
        def read(c,access,address,size,value,user):
            kind='ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else 'fixed' if address+size<=BASE else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind)
            self.reads.append(event)
            if kind is None:self.error=dict(kind='unexpected-read',event=event);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(c,number,user):self.error=dict(kind='exception',number=number,pc=c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):
            self.cpu.hook_add(hook,callback)
    def regs(self):return {key:self.cpu.reg_read(reg)&0xffffffff for key,reg in zip(KEYS,REGS)}
    def prepare(self,ram,regs):
        c=self.cpu;c.context_restore(self.baseline);c.mem_write(BASE,ram);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'))
        c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):c.reg_write(reg,regs[key])
        c.reg_write(m.UC_M68K_REG_PC,ENTRY);self.stack_low=STACK
    def mutate(self,changes):
        for change in changes:self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
    def run(self):
        c=self.cpu;before=bytes(c.mem_read(BASE,65536));incoming=self.regs();start=c.reg_read(m.UC_M68K_REG_PC)
        self.pcs.clear();self.events.clear();self.reads.clear();self.boundaries.clear();self.opcodes.clear();self.error=None;self.visits=0
        c.emu_start(start,0xffffff,count=CAP);pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc in (WAIT,RETURN),(self.error,hex(pc),'bounded cap',CAP)
        result=self.regs();pending={};carry=None
        if pc==WAIT:
            assert self.visits==2 and sp==STACK-18
            assert int.from_bytes(c.mem_read(sp,4),'big')==0x4a200
            assert int.from_bytes(c.mem_read(STACK-4,4),'big')==0x4a108
            pending=dict(return_pc=0x4a200,saved_bank=int.from_bytes(c.mem_read(sp+4,2),'big'),
                saved_a0=int.from_bytes(c.mem_read(sp+6,4),'big'),saved_a1=int.from_bytes(c.mem_read(sp+10,4),'big'),
                draw_return=0x4a108,raw=bytes(c.mem_read(STACK-22,26)).hex())
        else:
            assert sp==STACK+4;carry=bool(c.reg_read(m.UC_M68K_REG_SR)&1)
        assert bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big') and bytes(c.mem_read(0,BASE))==self.program[:BASE]
        self.stack_low=min([self.stack_low]+[e['address'] for e in self.events if e['kind']=='stack'])
        assert bytes(c.mem_read(STACK_START,self.stack_low-STACK_START))==b'\x5a'*(self.stack_low-STACK_START)
        replay=bytearray(before);ports=[]
        for e in self.events:
            if e['kind']=='ram':replay[e['address']-BASE:e['address']-BASE+e['size']]=e['value'].to_bytes(e['size'],'big')
            if e['kind']=='ports':ports.append(struct.pack('>BII',e['size'],e['address'],e['value']))
        output=bytes(c.mem_read(BASE,65536));assert output==bytes(replay)
        trace=dict(pcs=self.pcs.copy(),ordered_writes=self.events.copy(),reads=self.reads.copy(),opcodes=self.opcodes.copy(),
            boundaries=self.boundaries.copy(),branches=[dict(pc=a,next_pc=b) for a,b in zip(self.pcs,self.pcs[1:]+[pc]) if a in self.branch_pcs])
        info=dict(incoming=incoming,result=result,waiting=pc==WAIT,carry=carry,final_pc=pc,final_a7=sp,pending=pending,
            lowest_stack_write=self.stack_low,instructions=len(self.pcs)-(1 if pc==RETURN else 0),
            boundary_counts=dict(collections.Counter(hex(b['pc']) for b in self.boundaries)),
            observed_opcodes=sorted({row['value'] for row in self.opcodes}),port_count=len(ports),trace=trace)
        return info,before,output,b''.join(ports)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/activation_animation_scripts';folder.mkdir(parents=True,exist_ok=True);report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for start,end in CODE_RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    for row in instructions:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=CODE_RANGES,instructions=instructions,
        scripts=[dict(cpu_address=at,rom_offset=at,size=size,sha256=sha(program[at:at+size]),raw=program[at:at+size].hex()) for at,size in SCRIPTS],
        padding_489c1=program[0x489c1]),indent=2)+'\n')
    names=('tools/observe_activation_animation_scripts.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','artifacts/activation_animation_scripts/source.json')
    inputs={name:sha((root/name).read_bytes()) for name in names};oracle=oracle_provenance();observer=Observer(program,branches);rows=[]
    outcomes=collections.defaultdict(collections.Counter);all_opcodes=collections.Counter();all_boundaries=collections.Counter()
    for index,case in enumerate(cases()):
        ram,regs=fixture(case,index);observer.prepare(ram,regs);phases=[]
        def observe(label,changes=()):
            info,before,output,ports=observer.run();trace=info.pop('trace');prefix='case_%03d_%s'%(index,label)
            pending_words=None;pending_addresses=None
            for boundary in trace['boundaries']:
                if boundary['pc']==0x4a222:
                    raw=bytes.fromhex(boundary['stack_at_sp']);pending_words=[int.from_bytes(raw[i:i+2],'big') for i in (0,2)]
                elif boundary['pc']==0x4a226:
                    assert pending_words is not None
                    expected=[value if value<0x8000 else value|0xffff0000 for value in pending_words]
                    assert boundary['registers']['d0']==expected[0] and boundary['registers']['d7']==expected[1]
                    pending_words=None;raw=bytes.fromhex(boundary['stack_at_sp'])
                    pending_addresses=[int.from_bytes(raw[i:i+4],'big') for i in (0,4)]
                elif boundary['pc']==0x4a22a:
                    assert pending_addresses is not None
                    assert [boundary['registers']['a0'],boundary['registers']['a1']]==pending_addresses
                    pending_addresses=None
            assert pending_words is None and pending_addresses is None
            assert all(any(at<=row['address']<at+size for at,size in SCRIPTS) and program[row['address']]==row['value'] for row in trace['opcodes'])
            payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,
                prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
            for name,data in payloads.items():(folder/name).write_bytes(data)
            info.update(phase=label,host_changes=list(changes),files={name:sha(data) for name,data in payloads.items()},
                input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json')
            for branch in trace['branches']:outcomes[branch['pc']][branch['next_pc']]+=1
            all_opcodes.update(row['value'] for row in trace['opcodes']);all_boundaries.update(info['boundary_counts']);phases.append(info)
            return info,output,trace
        begin,output,trace=observe('begin')
        if case['pending']:
            assert begin['waiting'] and begin['pending']['saved_a0']==0x102026 and begin['pending']['saved_bank']==0
            assert begin['pending']['saved_a1']==case['script']+8
            captured=begin['result'];changes=[dict(address=0x100010,size=2,value=0xbeef),
                dict(address=0x102042,size=2,value=0x8000),dict(address=0x102046,size=2,value=0),
                dict(address=0x102053,size=1,value=0xfc),dict(address=0x102020,size=2,value=0x1234)]
            observer.mutate(changes);hold,held,holdtrace=observe('hold',changes)
            assert hold['waiting'] and hold['pending']==begin['pending'] and hold['result']==captured and not holdtrace['ordered_writes']
            assert holdtrace['pcs']==[WAIT,0xcda8,WAIT]
            changes=[dict(address=0x108d34,size=2,value=captured['d4']&65535)]
            observer.mutate(changes);done,output,readytrace=observe('ready',changes)
            assert not done['waiting']
            boundary=readytrace['pcs'].index(0x4a200)
            assert not any(pc in (ENTRY,0x4a10c,0xcd58,0xcd5c) for pc in readytrace['pcs'][:boundary])
            current=next(b['registers'] for b in readytrace['boundaries'] if b['pc']==0x4a200)
            expected_d0=((captured['d5']&65535)<<16)|(((captured['d0']>>16)<<6)&65535)
            expected_d7=(captured['d7']&65535)|((((captured['d7']>>16)|((captured['d0']&65535)<<7))&65535)<<16)
            expected_d1=(captured['d1']&0xffffff00)|(captured['d1']&7)
            assert [current['d0'],current['d1'],current['d7']]==[expected_d0,expected_d1,expected_d7]
            current_writes=[e for e in readytrace['ordered_writes'] if e['pc']==0xcdfc][:3]
            assert [e['value'] for e in current_writes]==[expected_d0,expected_d1,expected_d7]
            # Later script draws may legitimately re-read object/callback fields.
            later=next(b for b in readytrace['boundaries'] if b['pc']==0x4a10c)
            later_sprite=next(b for b in readytrace['boundaries'] if b['pc']==0xcd58)
            assert later['a7']==STACK-4 and later_sprite['registers']['d2']&255==0x3f
            for pc,address,size,value in ((0x4a126,0x102020,2,0x1234),(0x4a16e,0x102042,2,0x8000),
                    (0x4a172,0x102046,2,0),(0x4a178,0x102053,1,0xfc)):
                read=next(e for e in readytrace['reads'] if e['pc']==pc)
                assert (read['address'],read['size'],read['value'])==(address,size,value)
            assert readytrace['pcs'].index(0x4a10c)>boundary
            assert len([e for e in readytrace['ordered_writes'] if e['pc']==0xcdfc])==3
            assert all(readytrace['pcs'][i+1]==0xce00 for i,pc in enumerate(readytrace['pcs']) if pc==0xcd66)
            restore=next(e for e in readytrace['ordered_writes'] if e['pc']==0x4a200)
            assert restore['address']==0x100010 and restore['value']==0
        else:assert not begin['waiting']
        if case['script']==0:
            assert begin['carry'] is True and begin['result']['d7']==0
            assert begin['port_count']==2 and begin['boundary_counts']=={'0x49fc6':1}
            assert [(e['address'],e['value']) for e in trace['ordered_writes'] if e['kind']=='ports']==[(0x2ffff2,0x1000),(0x2ffff0,0)]
        rows.append(dict(case_index=index,fixture=case,phases=phases))
    assert set(all_opcodes)=={0,4,8,0x28},dict(all_opcodes)
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/name).read_bytes())==digest for name,digest in inputs.items())
    report=dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,cases=len(rows),phases=sum(len(r['phases']) for r in rows),
        pending_chains=4,total_native_ports=sum(p['port_count'] for r in rows for p in r['phases']),
        opcode_execution_counts={hex(k):n for k,n in sorted(all_opcodes.items())},boundary_counts=dict(all_boundaries),
        observed_branch_successors={hex(pc):{hex(target):n for target,n in sorted(counts.items())} for pc,counts in sorted(outcomes.items())},
        max_phase_instructions=max(p['instructions'] for r in rows for p in r['phases']),instruction_cap=CAP,
        results=rows,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,
        scope='Actual fixed48980(65bytes,padding separate)/489c2(80bytes), unpatched49fc6/defaultcd50 throughRTS or actualspritecda4 wait. '
        'Full64KiB RAM/15registers, carry only afterRTS, orderedRAM/stack/PVC writes, all reached reads and interpreter boundaries. '
        'Four same-CPU waits retain savedA0/A1/bank and originalstack; explicit bank-shadow/objectX/Y/flag/group poison and consumer release occur outsidehooks. '
        'Current draw prefix is skipped on resume; subsequent script draws may legitimately execute again. SR set beforeA7 and never read/changed in hooks. '
        'Fixture groups ea/f2 explicit, not naturalgroup proof; only actually reached00/04/08/28 opcode paths, not all17. NoC++/IRQ/scheduler/cycle/physicalmirror/fullCCR claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=4,ports=report['total_native_ports'],opcodes=report['opcode_execution_counts'],max_instructions=report['max_phase_instructions'],sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
