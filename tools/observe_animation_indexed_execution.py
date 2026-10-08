"""Full unpatched49fc6 opcode10 indexed draw on synthetic live RAM lists."""
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
BOUNDARIES=(ENTRY,0x4a22c,0x4a23e,0x4a242,0x4a246,0x4a248,0x4a24a,0x4a268,0x4a10c,0xcd58,0x4a200,0x4a222,0x4a226,0x4a22a,0x4a270,0x49ffe)
CODE_RANGES=((ENTRY,0x4a258),(0x4a268,0x4a276),(0x4a276,0x4a27e),(0x4a3ac,0x4a3b8),(0xcd50,0xce02))
TABLE=(0x4a76c,512)
def sha(data):return hashlib.sha256(data).hexdigest()
def put(ram,at,size,value):
    assert at>=0 and at+size<=len(ram)
    ram[at:at+size]=value.to_bytes(size,'big')
def cases():
    rows=[]
    def add(family,**values):
        row=dict(family=family,selector=0x1e,index=0,timer=0,length=40,a6=0x102000,
            queue='normal',pending=False,flags=0,x=160,y=384,flash_flag=0,flash_phase=0,sentinel=False)
        row.update(values);rows.append(row)
    for index,timer in itertools.product(range(256),(0,0x1234,0xffff)):
        add('all-BYTE-indices-three-timers',index=index,timer=timer)
    for index,kind in itertools.product((0,4),('normal','deferred','full','clip-x','clip-y','sentinel','flash')):
        add('draw-'+kind,index=index,queue=kind,flags=0x40 if kind=='deferred' else 0,
            x=0x8000 if kind=='clip-x' else 160,y=0 if kind=='clip-y' else 384,
            flash_flag=8 if kind=='flash' else 0,flash_phase=1 if kind=='flash' else 0,sentinel=kind=='sentinel')
    for index,deferred in itertools.product((0,4),(False,True)):
        add('same-CPU-indexed-draw-wait',index=index,pending=True,queue='deferred' if deferred else 'normal',flags=0x40 if deferred else 0)
    for selector,index in itertools.product((0x91,0x92,0x96,0x97,0xa7,0xac),(0,1,4,5,0x80,0xff)):
        add('actual-selector-retained-high-BYTE',selector=selector,index=index,a6=0x108000)
    for length,index in itertools.product((0,7,8,39,40,0xfff8,0xfff0),(0,4,5,255)):
        if length in (0xfff8,0xfff0) and index>=5:continue # Selected record would exceed this synthetic five-record fixture.
        add('unsigned-length-boundaries',length=length,index=index)
    return rows

def fixture(program,case,index):
    ram=bytearray(hashlib.shake_256(b'animation-indexed-'+str(index).encode()).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=0x108000,a6=case['a6']);obj=case['a6']-BASE
    for at,size,value in ((0x10,2,3),(0xf,1,case['flash_phase']),
        (obj+0x12,4,0xffff1500|case['flags']),(obj+0x16,1,1),(obj+0x17,1,0),
        (obj+0x19,1,21),(obj+0x1a,1,22),(obj+0x1b,1,23),(obj+0x1c,1,24),
        (obj+0x1e,2,13),(obj+0x20,2,0xea),(obj+0x26,4,0x105800),
        (obj+0x2a,2,case['timer']),(obj+0x2c,2,256),(obj+0x42,2,case['x']),
        (obj+0x46,2,case['y']),(obj+0x53,1,3),(obj+0x61,1,case['flash_flag']),
        (0x9152,4,0xcd50),(0x8d34,2,2 if case['pending'] or case['queue']=='full' else 0x100),
        (0x8d36,2,4 if case['pending'] else 2),(0x8d38,2,0),(0x8d3a,2,0),(0x914e,2,0)):
        put(ram,at,size,value)
    for i in range(256):put(ram,0x8b34+i*2,2,i*12)
    ram[0x5800:0x5804]=bytes((0x10,case['selector']))+case['length'].to_bytes(2,'big')
    for i in range(5):
        at=0x5804+i*8;ram[at:at+4]=bytes((4,0x40+i,i,i))
        put(ram,at+4,4,0x7ff800 if case['sentinel'] else 0x2152+i*0x800)
    offset=int.from_bytes(program[0x4a76c+case['selector']*2:0x4a76e+case['selector']*2],'big')
    signed=offset if offset<0x8000 else offset-65536
    put(ram,obj+signed,1,case['index'])
    length=case['length'];end=0x5804+(length if length<0x8000 else length-65536)
    ram[end:end+2]=b'\0\0'
    return bytes(ram),regs,dict(field_offset=offset,field_address=BASE+obj+signed,
        live_field_byte=ram[obj+signed],list_base=0x105804,list_end=BASE+end)

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
            assert self.visits==2 and sp==STACK-22
            assert int.from_bytes(c.mem_read(sp,4),'big')==0x4a200
            assert int.from_bytes(c.mem_read(STACK-8,4),'big')==0x4a270
            pending=dict(return_pc=0x4a200,saved_bank=int.from_bytes(c.mem_read(sp+4,2),'big'),
                saved_a0=int.from_bytes(c.mem_read(sp+6,4),'big'),saved_a1=int.from_bytes(c.mem_read(sp+10,4),'big'),
                draw_return=0x4a270,list_end=int.from_bytes(c.mem_read(STACK-4,4),'big'),raw=bytes(c.mem_read(STACK-22,26)).hex())
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

def validate_restore(trace):
    words=None;addresses=None
    for boundary in trace['boundaries']:
        pc=boundary['pc'];raw=bytes.fromhex(boundary['stack_at_sp'])
        if pc==0x4a222:words=[int.from_bytes(raw[i:i+2],'big') for i in (0,2)]
        elif pc==0x4a226:
            assert words is not None
            assert [boundary['registers'][k] for k in ('d0','d7')]==[v if v<0x8000 else v|0xffff0000 for v in words]
            words=None;addresses=[int.from_bytes(raw[i:i+4],'big') for i in (0,4)]
        elif pc==0x4a22a:
            assert addresses is not None and [boundary['registers'][k] for k in ('a0','a1')]==addresses
            addresses=None
    assert words is None and addresses is None

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/animation_indexed_execution_native';folder.mkdir(parents=True,exist_ok=True)
    report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for start,end in CODE_RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    for row in instructions:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    at,size=TABLE
    source_info=dict(source=source,ranges=CODE_RANGES,instructions=instructions,
        raw_fixed_table=dict(cpu_address=at,rom_offset=at,size=size,sha256=sha(program[at:at+size]),raw=program[at:at+size].hex()),
        caveat='512 bytes are the reached selector BYTE raw span, not proof of a logical256-entry table.')
    (folder/'source.json').write_text(json.dumps(source_info,indent=2)+'\n')
    names=('tools/observe_animation_indexed_execution.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','artifacts/animation_indexed_execution_native/source.json')
    inputs={name:sha((root/name).read_bytes()) for name in names};oracle=oracle_provenance();observer=Observer(program,branches)
    rows=[];outcomes=collections.defaultdict(collections.Counter);families=collections.Counter()
    for index,case in enumerate(cases()):
        ram,regs,details=fixture(program,case,index);observer.prepare(ram,regs);phases=[]
        def observe(label,changes=()):
            info,before,output,ports=observer.run();trace=info.pop('trace');validate_restore(trace)
            prefix='case_%03d_%s'%(index,label)
            payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,
                prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
            for name,data in payloads.items():(folder/name).write_bytes(data)
            info.update(phase=label,host_changes=list(changes),files={name:sha(data) for name,data in payloads.items()},
                input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json')
            for branch in trace['branches']:outcomes[branch['pc']][branch['next_pc']]+=1
            phases.append(info);return info,output,trace
        begin,output,trace=observe('begin')
        # These checks are assertions against captured native boundaries, never
        # injected register values or a host-generated expected CPU result.
        shaped=((details['field_offset']&0xff00)|details['live_field_byte'])<<3&65535
        choose=shaped<case['length'];details.update(shaped_offset=shaped,unsigned_in_range=choose)
        field_reads=[e for e in trace['reads'] if e['pc']==0x4a242]
        assert field_reads and all((e['address'],e['size'],e['value'])==(details['field_address'],1,details['live_field_byte']) for e in field_reads)
        compare=[b for b in trace['boundaries'] if b['pc']==0x4a248]
        assert compare and all((b['registers']['d0']&65535)==shaped and (b['registers']['d1']&65535)==case['length'] for b in compare)
        selected=[b for b in trace['boundaries'] if b['pc']==0x4a10c]
        expected_operand=details['list_base']+(shaped if shaped<0x8000 else shaped-65536)+1
        assert all(b['registers']['a1']==expected_operand for b in selected)
        assert bool(selected)==choose
        if case['pending']:
            assert begin['waiting'] and begin['pending']['list_end']==details['list_end']
            assert begin['pending']['saved_a0']==case['a6']+0x26 and begin['pending']['saved_a1']==expected_operand+7
            assert begin['pending']['saved_bank']==0 and begin['pending']['draw_return']==0x4a270
            captured=begin['result'];obj=case['a6']
            changes=[dict(address=0x100010,size=2,value=0xbeef),dict(address=obj+0x42,size=2,value=0x8000),
                dict(address=obj+0x46,size=2,value=0),dict(address=obj+0x53,size=1,value=0xfc),
                dict(address=obj+0x20,size=2,value=0x1234),dict(address=details['field_address'],size=1,value=255),
                dict(address=0x105800,size=1,value=0x7f),dict(address=0x105802,size=2,value=0xfff8),
                dict(address=expected_operand-1,size=1,value=0x7f)]
            observer.mutate(changes);hold,held,holdtrace=observe('hold',changes)
            assert hold['waiting'] and hold['pending']==begin['pending'] and hold['result']==captured and not holdtrace['ordered_writes']
            assert holdtrace['pcs']==[WAIT,0xcda8,WAIT]
            changes=[dict(address=0x108d34,size=2,value=captured['d4']&65535)]
            observer.mutate(changes);done,output,readytrace=observe('ready',changes);assert not done['waiting']
            boundary=readytrace['pcs'].index(0x4a200)
            assert not any(pc in (ENTRY,0x4a22c,0x4a10c,0xcd58) for pc in readytrace['pcs'][:boundary])
            cursor=next(b for b in readytrace['boundaries'] if b['pc']==0x49ffe)
            assert cursor['registers']['a1']==details['list_end']
            current=next(b['registers'] for b in readytrace['boundaries'] if b['pc']==0x4a200)
            expected_d0=((captured['d5']&65535)<<16)|(((captured['d0']>>16)<<6)&65535)
            expected_d7=(captured['d7']&65535)|((((captured['d7']>>16)|((captured['d0']&65535)<<7))&65535)<<16)
            expected_d1=(captured['d1']&0xffffff00)|(captured['d1']&7)
            assert [current['d0'],current['d1'],current['d7']]==[expected_d0,expected_d1,expected_d7]
            assert sum(e['size']==4 and e['kind']=='ram' for e in readytrace['ordered_writes'])==3
        else:assert not begin['waiting']
        families[case['family']]+=1;rows.append(dict(case_index=index,fixture=case,details=details,phases=phases))
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/name).read_bytes())==digest for name,digest in inputs.items())
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(rows),phases=sum(len(r['phases']) for r in rows),
        pending_chains=4,families=dict(families),excluded_fixture_combinations=[dict(length=length,index=i,reason='Unsigned compare selects beyond five synthetic04 records; not a normal completion fixture.') for length in (0xfff8,0xfff0) for i in (5,255)],total_native_ports=sum(p['port_count'] for r in rows for p in r['phases']),
        observed_branch_successors={hex(pc):{hex(target):n for target,n in sorted(counts.items())} for pc,counts in sorted(outcomes.items())},
        max_phase_instructions=max(p['instructions'] for r in rows for p in r['phases']),instruction_cap=CAP,
        results=rows,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,
        scope='Original49fc6 opcode10 on syntheticliveRAM5recordlists, actualfixed4a76c rawselector span anddefaultcd50. '
        'FullRAM15R/carry/PVC/read-write-stack traces; all256BYTEindices at3timers, representativeunsignedlength/retainedhighBYTE selectors, '
        'drawskip/queuecases and4sameCPU indexedwaitchains. ROM immutable, noSRhooks, noC++/naturalgameplay/IRQ/fullCCR/allselector-length-combinations claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=report['phases'],pending_chains=4,ports=report['total_native_ports'],
        max_instructions=report['max_phase_instructions'],sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
