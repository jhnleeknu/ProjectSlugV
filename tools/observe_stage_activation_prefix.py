"""Unpatched47c04 execution stopped before47c6c; not a callback return."""
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

ENTRY, STOP, CAP = 0x47c04, 0x47c6c, 100000
BOUNDARIES = (ENTRY, STOP, 0x47c48, 0x47c4c, 0x9060, 0x4e254, 0x477a2, 0xddf9a, 0x362a, 0x35f0, 0xca76, 0xca56, 0xc3c0)
BRANCHES = (0x47c08, 0x47c24, 0x47c32, 0x47c50, 0xc3c4)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_cases():
    profiles = ((0,)*15, (0xffffffff,)*15,
        tuple((0x81231234+i*0x01010101)&0xffffffff for i in range(15)),
        tuple((0xabcdffff-i*0x01010203)&0xffffffff for i in range(15)))
    flags, parents, signed = (0,1,2,4,5,255), (0,5,6,255), (0,127,128,255)
    cases = []
    def add(flag, parent, previous, profile, alias, helper_alias=False):
        regs = dict(zip(KEYS, profiles[profile])); regs.update(a5=0x108000,
            a6=0x1009c6 if helper_alias else 0x10d608 if alias else 0x102000)
        cases.append(dict(entry=ENTRY, stop_before_pc=STOP, profile=profile, incoming=regs,
            flag=flag, parent_byte=parent, signed_previous_byte=previous,
            parent_flag_alias=alias, host_writes=[
                dict(address=0x10d684,size=1,value=flag),
                dict(address=regs['a6']+0x7c,size=1,value=parent),
                dict(address=0x107f31,size=1,value=previous)]))
        if helper_alias: cases[-1]['parent_helper_alias']=True
    for fi, flag in enumerate(flags):
        for pi, parent in enumerate(parents):
            for variant in range(3):
                add(flag,parent,signed[(fi+pi+variant)%4],(fi+pi+variant)%4,False)
    for fi, flag in enumerate(flags):
        for si, previous in enumerate(signed): add(flag,flag,previous,(fi+si)%4,True)
    for pi, parent in enumerate(parents):
        for si, previous in enumerate((127,128)): add(0,parent,previous,(pi+si)%4,False,True)
    assert len(cases)==104
    return cases


def fixture(case):
    ram = bytearray(hashlib.shake_256(b'stage-activation-prefix-'+bytes([case['profile']])).digest(65536))
    for write in case['host_writes']:
        at=write['address']-BASE; ram[at:at+write['size']]=write['value'].to_bytes(write['size'],'big')
    return bytes(ram)


class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x300000,0x100000)
        self.baseline=self.cpu.context_save();self.events=[];self.pcs=[];self.boundaries=[];self.reads=[];self.branches=[];self.pending=None;self.error=None
        def registers(cpu): return dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        def code(cpu,pc,size,user):
            self.pcs.append(pc)
            if self.pending is not None:
                self.branches.append(dict(pc=self.pending,next_pc=pc));self.pending=None
            if pc in BRANCHES:self.pending=pc
            if pc in BOUNDARIES:self.boundaries.append(dict(pc=pc,a7=cpu.reg_read(m.UC_M68K_REG_A7),registers=registers(cpu)))
            if pc==STOP:cpu.emu_stop();return
            if pc==RETURN:self.error=dict(kind='unexpected-callback-return',pc=pc);cpu.emu_stop();return
            opcode=int.from_bytes(cpu.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:
                self.error=dict(kind='trap-or-illegal',pc=pc,opcode=opcode);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            kind='ports' if address==0x3c0000 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else None
            event=dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(size*8))-1),kind=kind)
            self.events.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);cpu.emu_stop()
        def read(cpu,access,address,size,value,user):
            if not(address+size<=BASE or BASE<=address and address+size<=BASE+65536 or STACK_START<=address and address+size<=STACK+4):
                self.reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size))
        def invalid(cpu,access,address,size,value,user):
            self.error=dict(kind='invalid-memory',address=address,size=size,pc=cpu.reg_read(m.UC_M68K_REG_PC));return False
        def intr(cpu,number,user):
            self.error=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read)
        self.cpu.hook_add(UC_HOOK_MEM_INVALID,invalid);self.cpu.hook_add(UC_HOOK_INTR,intr)

    def run(self,case,ram):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,ram)
        cpu.mem_write(STACK_START,b'\x5a'*4100);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):cpu.reg_write(reg,case['incoming'][key])
        self.events.clear();self.pcs.clear();self.boundaries.clear();self.reads.clear();self.branches.clear();self.pending=None;self.error=None
        try:cpu.emu_start(ENTRY,0xffffff,count=CAP)
        except unicorn.UcError as exc:
            if self.error is None:self.error=dict(kind='emulator-error',error=str(exc),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=STOP and self.error is None:self.error=dict(kind='instruction-cap',pc=pc,cap=CAP)
        assert self.error is None,self.error
        assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK and bytes(cpu.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        assert bytes(cpu.mem_read(0,BASE))==self.program[:BASE] and not self.reads
        stack=[e for e in self.events if e['kind']=='stack'];lowest=min([e['address'] for e in stack]+[STACK])
        assert bytes(cpu.mem_read(STACK_START,lowest-STACK_START))==b'\x5a'*(lowest-STACK_START)
        output=bytes(cpu.mem_read(BASE,65536));replay=bytearray(ram)
        for e in self.events:
            if e['kind']=='ram':replay[e['address']-BASE:e['address']-BASE+e['size']]=e['value'].to_bytes(e['size'],'big')
        assert output==bytes(replay)
        result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        ports=b''.join(struct.pack('>BII',e['size'],e['address'],e['value']) for e in self.events if e['kind']=='ports')
        before=next(row for row in self.boundaries if row['pc']==0x47c48)
        after=next(row for row in self.boundaries if row['pc']==0x47c4c)
        parent_read=dict(pc=0x47c48,address=before['registers']['a6']+0x7c,
            effective_byte=after['registers']['d0']&255)
        if case.get('parent_helper_alias'):
            clears=[e for e in self.events if e['kind']=='ram' and e['pc']==0x4e25e and e['address']==0x100a42]
            assert len(clears)==1 and clears[0]['value']==0
            assert self.pcs.index(0x4e25e)<self.pcs.index(0x47c48)
            parent_read['earlier_helper_clear']=clears[0]
            parent_read['helper_clear_precedes_read']=True
        info=dict(stopped_at_partial_boundary=True,callback_returned=False,final_pc=pc,final_a7=STACK,
            instructions=len(self.pcs)-1,lowest_stack_write=lowest,stack_write_count=len(stack),
            RAM_writes=[e for e in self.events if e['kind']=='ram'],boundaries=self.boundaries.copy(),
            calls=dict(collections.Counter(hex(e['pc']) for e in self.boundaries)),unexpected_reads=self.reads.copy(),branches=self.branches.copy(),parent_read_evidence=parent_read)
        return output,result,ports,dict(pcs=self.pcs.copy(),writes=self.events.copy()),info


def signed_byte(value): return value if value<128 else value-256


def assert_predictions(case,ram,output,result,ports,info):
    flag,parent,previous=case['flag'],case['parent_byte'],case['signed_previous_byte'];calls=info['calls']
    if case.get('parent_helper_alias'):
        assert flag==0 and case['incoming']['a6']+0x7c==0x100a42
        parent=0 # Original4e254 clears this live field before47c48 reads it.
        assert info['parent_read_evidence']['helper_clear_precedes_read']
    assert info['parent_read_evidence']['effective_byte']==parent
    for pc,present in ((0x9060,flag==0),(0x4e254,flag==0),(0x477a2,bool(flag&1)),
            (0xca76,not bool(flag&4)),(0xca56,True),(0xc3c0,parent<6)):
        assert calls.get(hex(pc),0)==int(present),(case,hex(pc),calls)
    assert len(ports)//9==(137 if flag&1 else 0)
    assert result['a5']==case['incoming']['a5'] and result['a6']==case['incoming']['a6']
    assert result['d0']==parent
    assert output[0xd683]==(ram[0xd683]|4|(16 if flag==0 else 0))
    assert output[0x0967]==0
    assert output[0x0965]==(255 if not flag&4 else ram[0x0965])
    assert output[0x107def-BASE]==(0 if flag==0 else ram[0x107def-BASE])
    assert output[0x7f31]==(parent if parent<6 and signed_byte(parent)>signed_byte(previous) else previous)
    a6=case['incoming']['a6']-BASE
    assert output[a6:a6+4]==STOP.to_bytes(4,'big') and output[a6+0x7e]==255
    assert output[a6+0x20:a6+0x22]==b'\x00\xea'
    if flag==0:
        for offset,value in ((0xdd1f,255),(0xdd20,0),(0x0a42,0),(0x0b06,0)):assert output[offset]==value


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256==source['sha256']
    # Regenerate diagnostic source listings rather than requiring an untracked
    # manually-created artifact from an earlier session.
    instructions=[]
    for start,end in ((0x47c04,0x47d20),(0x4e254,0x4e2ce),(0x9060,0x9068),(0xca56,0xca84),(0xc3c0,0xc3da)):
        instructions.extend(disassemble_range(program,start,end-start,start))
    static_path=root/'artifacts/stage_activation_static.json'
    static_path.parent.mkdir(parents=True,exist_ok=True)
    static_path.write_text(json.dumps(dict(source=source,instructions=instructions),indent=2)+'\n')
    names=('tools/observe_stage_activation_prefix.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py',
        'artifacts/stage_activation_static.json')
    inputs={name:sha((root/name).read_bytes()) for name in names};oracle=oracle_provenance()
    static=json.loads((root/'artifacts/stage_activation_static.json').read_bytes());assert static['source']==source
    for row in static['instructions']:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    folder=root/'artifacts/stage_activation_prefix';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'observation.json';report.unlink(missing_ok=True);observer=Observer(program);rows=[];mismatches=[];branches=collections.Counter()
    for index,case in enumerate(build_cases()):
        ram=fixture(case);output,result,ports,trace,info=observer.run(case,ram)
        try:assert_predictions(case,ram,output,result,ports,info)
        except AssertionError as exc:mismatches.append(dict(case_index=index,error=repr(exc)))
        files=dict(input_ram_file='input_%02d.bin'%index,ram_file='native_%02d.bin'%index,
            ports_file='native_%02d.ports.bin'%index,trace_file='native_%02d.trace.json'%index)
        payloads=dict(input_ram_file=ram,ram_file=output,ports_file=ports,trace_file=(json.dumps(trace,indent=2)+'\n').encode())
        for key,data in payloads.items():(folder/files[key]).write_bytes(data)
        for branch in info['branches']:branches[(branch['pc'],branch['next_pc'])]+=1
        rows.append(dict(case_index=index,fixture=case,result=result,input_ram_sha256=sha(ram),ram_sha256=sha(output),
            ports_sha256=sha(ports),trace_sha256=sha(payloads['trace_file']),port_count=len(ports)//9,**files,**info))
    assert inputs=={name:sha((root/name).read_bytes()) for name in names} and oracle==oracle_provenance()
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    branch_coverage=[dict(pc=pc,next_pc=next_pc,count=count) for (pc,next_pc),count in sorted(branches.items())]
    for pc in BRANCHES:
        assert len({next_pc for branch_pc,next_pc in branches if branch_pc==pc})==2,hex(pc)
    report.write_text(json.dumps(dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,stop_before_pc=STOP,
        cases=len(rows),completed_cases=len(rows),prediction_mismatches=mismatches,total_native_ports=sum(r['port_count'] for r in rows),
        branch_coverage=branch_coverage,original_program_modified=False,in_call_SR_read=False,
        full_RAM_15_registers_ordered_ports_observed=True,Cpp_comparison_performed=False,callback_returned=False,
        results=rows,scope='Only unpatched47c04 through just before47c6c. All actual callees run natively; complete RAM/stack/port write order and15regs, explicit pre-entry host writes. Isolated STACK1feffc outside compared64KiBRAM; no full callback return, subsequent frame, IRQ/scheduler, physical mirror, CCR/cycle or rendered pixel equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),mismatches=len(mismatches),ports=sum(r['port_count'] for r in rows),sha256=sha(report.read_bytes()),branches=branch_coverage)))
    if mismatches:raise SystemExit(1)


if __name__=='__main__':main()
