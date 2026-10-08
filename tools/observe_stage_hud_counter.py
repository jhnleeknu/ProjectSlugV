"""Observe unpatched4e286 nonwaiting native execution; no C++ comparison."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UC_HOOK_INTR, m68k_const as m
try:
    from .disassemble_program import load_verified_program, disassemble_range
    from .verify_object_reset import make_cpu
    from .observe_scene_frame_execution import oracle_provenance
    from .observe_screen_reset_full import BASE, STACK, STACK_START, RETURN, KEYS, REGS
    from .verify_stage_catalog import SOURCE_SHA256
except ImportError:
    from disassemble_program import load_verified_program, disassemble_range
    from verify_object_reset import make_cpu
    from observe_scene_frame_execution import oracle_provenance
    from observe_screen_reset_full import BASE, STACK, STACK_START, RETURN, KEYS, REGS
    from verify_stage_catalog import SOURCE_SHA256

ENTRY, CAP = 0x4e286, 100000
CALLEES = (ENTRY, 0x8cda, 0x35f0, 0x3af8, 0x3ac8, 0x3aea)

def sha(data): return hashlib.sha256(data).hexdigest()

def build_cases():
    words = (0, 1, 0x09ff, 0x0a00, 0x0b00, 0x0c00, 0x0d00, 0x0e00, 0x0f00,
        0x8a00, 0x8b00, 0x8c00, 0x8d00, 0x8e00, 0x8f00, 0x9000, 0x9100,
        0x9200, 0x9900, 0x99ff, 0x9a00, 0xffff,
        0x2300, 0x3400, 0x4500, 0x5600, 0x6700, 0x7800)
    cases = []
    for flag, values in ((1, words), (0, (0, 0x09ff, 0x99ff, 0xffff))):
        for word in values:
            for variant in range(4):
                regs = {key: (0x81231234 + i*0x01010101 + variant*0x1234567)&0xffffffff
                    for i,key in enumerate(KEYS)}
                regs.update(a5=0x108000,a6=0x102000,d0=((0x8123+variant*0x1234)<<16)|word)
                cases.append(dict(incoming=regs,word=word,flag=flag,profile=variant,
                    counter=(0,1,255,0)[variant],reference=(0,1,1,1)[variant],
                    target=(0x2222,0x2222,0x0a0d,0x0a0d)[variant],
                    current=(0x3333,0x3333,0x0a0d,0x3333)[variant],weight=(0,31,0,31)[variant]))
    assert len(cases)==128
    return cases

def fixture(case):
    ram=bytearray(hashlib.shake_256(b'stage-hud-counter-'+bytes([case['profile']])).digest(65536))
    writes=[(0xdd1f,1,case['flag']),(0xdd20,1,case['counter']),
        (0x12,1,0),(0x4d7e,1,0),(0xf001,1,0),(0x4d8a,2,0),(0x4d8c,2,0),
        (0x4d92+0x120+8,2,case['reference']),(0x4d92+0x120+0xa,2,case['current']),
        (0x4d92+0x120+0xc,2,case['target']),(0x4d92+0x120+0xe,1,case['weight']),
        (0x4d92+0x120+0xf,1,0x25)]
    case['host_writes']=[dict(address=BASE+at,size=size,value=value) for at,size,value in writes]
    for at,size,value in writes:ram[at:at+size]=value.to_bytes(size,'big')
    return bytes(ram)

class Observer:
    def __init__(self, program):
        self.program=program;self.cpu=make_cpu(program)
        self.cpu.mem_map(0x300000,0x100000);self.cpu.mem_map(0xd00000,0x1000)
        self.baseline=self.cpu.context_save()
        self.events=[];self.pcs=[];self.boundaries=[];self.reads=[];self.external=[];self.error=None
        def code(cpu,pc,size,user):
            self.pcs.append(pc)
            if pc in CALLEES:
                self.boundaries.append(dict(pc=pc,a7=cpu.reg_read(m.UC_M68K_REG_A7),
                    registers=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))))
            if pc==RETURN:cpu.emu_stop();return
            opcode=int.from_bytes(cpu.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:
                self.error=dict(kind='trap-or-illegal',pc=pc,opcode=opcode);cpu.emu_stop()
            if pc==0x3aea:
                self.error=dict(kind='unexpected-sound-wait',pc=pc);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            kind='ports' if address==0x3c0000 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else None
            event=dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,
                value=value&((1<<(size*8))-1),kind=kind)
            self.events.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);cpu.emu_stop()
        def read(cpu,access,address,size,value,user):
            event=dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,
                value=int.from_bytes(cpu.mem_read(address,size),'big'))
            if 0x4e272<=address and address+size<=0x4e292:self.reads.append(event)
            if address==0xd00046:self.external.append(event)
            elif not(address+size<=BASE or BASE<=address and address+size<=BASE+65536 or STACK_START<=address and address+size<=STACK+4):
                self.error=dict(kind='unexpected-read',event=event);cpu.emu_stop()
        def invalid(cpu,access,address,size,value,user):
            self.error=dict(kind='invalid-memory',address=address,size=size,pc=cpu.reg_read(m.UC_M68K_REG_PC));return False
        def intr(cpu,number,user):
            self.error=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),
                (UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):self.cpu.hook_add(hook,callback)

    def run(self,case,ram):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,ram);cpu.mem_write(0xd00046,b'\0')
        cpu.mem_write(STACK_START,b'\x5a'*4100);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):cpu.reg_write(reg,case['incoming'][key])
        self.events.clear();self.pcs.clear();self.boundaries.clear();self.reads.clear();self.external.clear();self.error=None
        try:cpu.emu_start(ENTRY,0xffffff,count=CAP)
        except unicorn.UcError as exc:
            if self.error is None:self.error=dict(kind='emulator-error',error=str(exc),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        assert self.error is None,self.error
        assert pc==RETURN,(hex(pc),'instruction cap',CAP)
        assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4 and bytes(cpu.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        assert bytes(cpu.mem_read(0,BASE))==self.program[:BASE]
        stack=[e for e in self.events if e['kind']=='stack'];lowest=min([e['address'] for e in stack]+[STACK])
        assert bytes(cpu.mem_read(STACK_START,lowest-STACK_START))==b'\x5a'*(lowest-STACK_START)
        output=bytes(cpu.mem_read(BASE,65536));replay=bytearray(ram)
        for event in self.events:
            if event['kind']=='ram':
                at=event['address']-BASE;replay[at:at+event['size']]=event['value'].to_bytes(event['size'],'big')
        assert output==bytes(replay)
        result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        ports=b''.join(struct.pack('>BII',e['size'],e['address'],e['value']) for e in self.events if e['kind']=='ports')
        calls=dict(collections.Counter(hex(e['pc']) for e in self.boundaries))
        queue=lambda data:dict(head=int.from_bytes(data[0x4d8a:0x4d8c],'big'),
            tail=int.from_bytes(data[0x4d8c:0x4d8e],'big'),raw_words=data[0x4d82:0x4d8a].hex())
        info=dict(final_pc=pc,final_a7=STACK+4,instructions=len(self.pcs)-1,lowest_stack_write=lowest,
            stack_write_count=len(stack),RAM_writes=[e for e in self.events if e['kind']=='ram'],
            boundaries=self.boundaries.copy(),calls=calls,raw_lookup_reads=self.reads.copy(),
            external_reads=self.external.copy(),queue_before=queue(ram),queue_after=queue(output))
        return output,result,ports,dict(pcs=self.pcs.copy(),writes=self.events.copy(),raw_lookup_reads=self.reads.copy(),external_reads=self.external.copy()),info

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256==source['sha256']
    folder=root/'artifacts/stage_hud_counter';folder.mkdir(parents=True,exist_ok=True)
    instructions=[]
    for start,end in ((0x4e286,0x4e330),(0x8cda,0x8d32),(0x35f0,0x3628),(0x3af8,0x3c08)):
        instructions.extend(disassemble_range(program,start,end-start,start))
    static=folder/'source.json';static.write_text(json.dumps(dict(source=source,instructions=instructions,
        raw_lookup=dict(cpu_address=0x4e272,rom_offset=0x4e272,size=32,raw=program[0x4e272:0x4e292].hex())),indent=2)+'\n')
    for row in instructions:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    names=('tools/observe_stage_hud_counter.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py')
    inputs={name:sha((root/name).read_bytes()) for name in names};inputs['artifacts/stage_hud_counter/source.json']=sha(static.read_bytes())
    oracle=oracle_provenance();report=folder/'observation.json';report.unlink(missing_ok=True)
    observer=Observer(program);rows=[];lookup=[]
    for index,case in enumerate(build_cases()):
        ram=fixture(case);output,result,ports,trace,info=observer.run(case,ram)
        files=dict(input_ram_file='input_%03d.bin'%index,ram_file='native_%03d.bin'%index,
            ports_file='native_%03d.ports.bin'%index,trace_file='native_%03d.trace.json'%index)
        payloads=dict(input_ram_file=ram,ram_file=output,ports_file=ports,trace_file=(json.dumps(trace,indent=2)+'\n').encode())
        for key,data in payloads.items():(folder/files[key]).write_bytes(data)
        lookup.extend(info['raw_lookup_reads'])
        rows.append(dict(case_index=index,fixture=case,result=result,input_ram_sha256=sha(ram),ram_sha256=sha(output),
            ports_sha256=sha(ports),trace_sha256=sha(payloads['trace_file']),port_count=len(ports)//9,**files,**info))
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for name in names:assert inputs[name]==sha((root/name).read_bytes())
    addresses=sorted({e['address'] for e in lookup})
    assert addresses==list(range(0x4e272,0x4e292,2)),addresses
    assert all(e['size']==2 and e['value']==int.from_bytes(program[e['address']:e['address']+2],'big') for e in lookup)
    counts=collections.Counter()
    for row in rows:
        counts.update(row['calls'])
        case=row['fixture'];calls=row['calls']
        sound=bool(case['flag'] and case['word']<0x0a00 and case['counter']==0)
        assert calls.get('0x3af8',0)==int(sound)
        assert calls.get('0x3ac8',0)==0 and calls.get('0x3aea',0)==0
        if sound:
            assert row['queue_before']['head']==row['queue_before']['tail']==0
            assert row['queue_after']['head']==0 and row['queue_after']['tail']==2
            assert row['queue_after']['raw_words'].startswith('1ac3')
        if not case['flag']:
            assert row['result']==case['incoming'] and row['input_ram_sha256']==row['ram_sha256']
            assert row['port_count']==0
    assert inputs['artifacts/stage_hud_counter/source.json']==sha(static.read_bytes())
    report.write_text(json.dumps(dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,
        cases=len(rows),completed_cases=len(rows),total_native_ports=sum(r['port_count'] for r in rows),
        native_call_counts=dict(counts),raw_lookup_read_addresses=addresses,raw_lookup_read_count=len(lookup),
        external_read_count=sum(len(r['external_reads']) for r in rows),original_program_modified=False,in_call_SR_read=False,
        full_RAM_15_registers_ordered_ports_observed=True,Cpp_comparison_performed=False,results=rows,
        scope='Unpatched original4e286 throughRTS with actual8cda/35f0/3af8. Controlled nonwaiting sound queue only; no sound resume/IRQ/scheduler/CCR/cycle/rendered pixel equivalence claim. Complete compared64KiB RAM,15regs, all ordered RAM/stack/video writes and raw lookup reads. SR set before isolated A7; stack replay/guard and immutable fixed program checked.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),ports=sum(r['port_count'] for r in rows),calls=dict(counts),lookup_addresses=addresses,
        external_reads=sum(len(r['external_reads']) for r in rows),sha256=sha(report.read_bytes()))))

if __name__=='__main__':main()
