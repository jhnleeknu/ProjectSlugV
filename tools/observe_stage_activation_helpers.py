"""Unpatched small activation helpers throughRTS; no C++ comparison."""
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

# c34 is bee's RTS instruction, so its exclusive decode end is c36.
RANGES=((0x4e216,0x4e24e),(0xbee,0xc36),(0x16ed2,0x16ef0),(0x49f8c,0x49fc6))
def sha(data):return hashlib.sha256(data).hexdigest()
def cases():
    rows=[];statuses=(0,1,2,5,6,255)
    for a5,first,second in itertools.product((0x108000,0x108001,0x108002),statuses,statuses):
        rows.append(dict(entry=0x4e216,a5=a5,first=first,second=second))
    for request,first,second in itertools.product((0,0x55,255),statuses,statuses):
        rows.append(dict(entry=0xbee,a5=(0,0xffffffff,0x108001)[request%3],request=request,first=first,second=second))
    for a5,left,right,alias in itertools.product((0x108000,0x108002),(-32768,-1,0,1,32767),(-32768,-1,0,1,32767),('none','left-high','right-low')):
        rows.append(dict(entry=0x16ed2,a5=a5,left=left,right=right,alias=alias))
    for a6,a1,d0 in itertools.product((0x100b30,0x100000,0x10ffd2,0xfffea,0xfffe8),(0,1,0xffffffff,0x81234567,0x200000),(0,0xabcd1234,0xffffffff)):
        rows.append(dict(entry=0x49f8c,a5=0x108000,a6=a6,a1=a1,d0=d0))
    return rows

def fixture(case,index):
    ram=bytearray(hashlib.shake_256(b'stage-activation-helpers-'+bytes([index%4])).digest(65536));writes=[]
    def put(address,size,value):
        assert BASE<=address and address+size<=BASE+65536
        at=address-BASE;ram[at:at+size]=value.to_bytes(size,'big');writes.append(dict(address=address,size=size,value=value))
    regs={key:((0xabcd1234 if index%2 else 0xffff0000)+i*0x10203)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=case['a5']);entry=case['entry']
    if entry==0x4e216:
        put(regs['a5']-0x75bc,1,case['first']);put(regs['a5']-0x74f8,1,case['second'])
    elif entry==0xbee:
        put(0x10f004,1,case['request']);put(0x10fdb6,1,case['first']);put(0x10fdb7,1,case['second'])
    elif entry==0x16ed2:
        put(regs['a5']+0xd3e,2,case['left']&65535);put(regs['a5']+0xd46,2,case['right']&65535)
        regs['a6']=0x102001 if case['alias']=='none' else regs['a5']+(0xd3e if case['alias']=='left-high' else 0xd47)-0x15
        if case['alias']=='none':put(regs['a6']+0x15,1,(0xa1,0xa5)[index%2])
    else:regs.update(a6=case['a6'],a1=case['a1'],d0=case['d0'])
    case.update(incoming=regs,host_writes=writes);return bytes(ram)

class Observer:
    def __init__(self,program,branches):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x2ff000,0x1000);self.baseline=self.cpu.context_save();self.branch_pcs=branches
        self.pcs=[];self.events=[];self.reads=[];self.branches=[];self.pending=None;self.error=None
        def code(cpu,pc,size,user):
            self.pcs.append(pc)
            if self.pending is not None:self.branches.append(dict(pc=self.pending,next_pc=pc));self.pending=None
            if pc in self.branch_pcs:self.pending=pc
            if pc==RETURN:cpu.emu_stop();return
            if not self.start<=pc<self.end:self.error=dict(kind='unexpected-code',pc=pc);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            kind='ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else 'ports' if address in (0x2ffff2,0x2ffff0) and size==2 else None
            event=dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(size*8))-1),kind=kind);self.events.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);cpu.emu_stop()
        def read(cpu,access,address,size,value,user):
            if BASE<=address and address+size<=BASE+65536:self.reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(cpu.mem_read(address,size),'big')))
            elif not(address+size<=BASE or STACK_START<=address and address+size<=STACK+4):self.error=dict(kind='unexpected-read',address=address,size=size);cpu.emu_stop()
        def invalid(cpu,access,address,size,value,user):self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(cpu,number,user):self.error=dict(kind='cpu-exception',number=number);cpu.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):self.cpu.hook_add(hook,callback)
    def run(self,case,ram):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,ram);cpu.mem_write(STACK_START,b'\x5a'*4100);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):cpu.reg_write(reg,case['incoming'][key])
        self.start,self.end=next(r for r in RANGES if r[0]==case['entry'])
        self.pcs.clear();self.events.clear();self.reads.clear();self.branches.clear();self.pending=None;self.error=None
        try:cpu.emu_start(case['entry'],0xffffff,count=100)
        except unicorn.UcError as exc:
            if self.error is None:self.error=dict(kind='emulator-error',error=str(exc))
        assert self.error is None,self.error
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        assert bytes(cpu.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        carry=bool(cpu.reg_read(m.UC_M68K_REG_SR)&1) if case['entry'] in (0x4e216,0xbee) else None
        lowest=min([e['address'] for e in self.events if e['kind']=='stack']+[STACK])
        assert bytes(cpu.mem_read(STACK_START,lowest-STACK_START))==b'\x5a'*(lowest-STACK_START)
        assert bytes(cpu.mem_read(0,BASE))==self.program[:BASE]
        output=bytes(cpu.mem_read(BASE,65536));replay=bytearray(ram)
        for e in self.events:
            if e['kind']=='ram':at=e['address']-BASE;replay[at:at+e['size']]=e['value'].to_bytes(e['size'],'big')
        assert output==bytes(replay)
        result=dict(zip(KEYS,(cpu.reg_read(r)&0xffffffff for r in REGS)))
        port_rows=[e for e in self.events if e['kind']=='ports'];ports=b''.join(struct.pack('>BII',e['size'],e['address'],e['value']) for e in port_rows)
        if case['entry']==0x49f8c:
            assert [(e['address'],e['size'],e['value']) for e in port_rows]==[(0x2ffff2,2,0x1000),(0x2ffff0,2,0)]
            assert [(e['pc'],e['size']) for e in self.events]==[(0x49f90,1),(0x49f96,2),(0x49f9c,2),(0x49fa4,2),(0x49fb8,4),(0x49fba,2),(0x49fc0,2)]
            assert result['a0']==case['incoming']['a6']+0x26
            assert {k:v for k,v in result.items() if k!='a0'}=={k:v for k,v in case['incoming'].items() if k!='a0'}
        elif case['entry']==0x16ed2:
            flag_at=case['incoming']['a6']+0x15-BASE
            expected=(ram[flag_at]|4) if case['left']<case['right'] else (ram[flag_at]&0xfb)
            assert output[flag_at]==expected
            left=int.from_bytes(ram[case['a5']+0xd3e-BASE:case['a5']+0xd40-BASE],'big')
            assert result['d0']==(case['incoming']['d0']&0xffff0000)|left
            assert {k:v for k,v in result.items() if k!='d0'}=={k:v for k,v in case['incoming'].items() if k!='d0'}
        elif case['entry']==0x4e216:
            first_pass=case['first'] in (0,5)
            assert carry==(first_pass and case['second'] in (0,5))
            expected=dict(case['incoming']);expected['d0']=(expected['d0']&0xffffff00)|(case['second'] if first_pass else case['first'])
            assert result==expected and output==ram
            assert len(self.reads)==(2 if first_pass else 1)
        else:
            first_pass=case['first'] in (1,2);success=first_pass or case['second'] in (1,2)
            assert carry==success and output[0xf004]==(case['request'] if success else 0)
            expected=dict(case['incoming']);expected['a0']=0x10fdb7 if first_pass else 0x10fdb8
            expected['d0']=(expected['d0']&0xffffff00)|case['request']
            expected['d1']=(expected['d1']&0xffffff00)|(case['first'] if first_pass else case['second'])
            assert result==expected
            assert len([e for e in self.events if e['kind']=='ram'])==(2 if success else 1)
        info=dict(final_pc=RETURN,final_a7=STACK+4,carry=carry,instructions=len(self.pcs)-1,branches=self.branches.copy(),
            RAM_reads=self.reads.copy(),writes=self.events.copy(),lowest_stack_write=lowest)
        return output,result,ports,dict(pcs=self.pcs.copy(),reads=self.reads.copy(),writes=self.events.copy()),info

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256==source['sha256']
    folder=root/'artifacts/stage_activation_helpers';folder.mkdir(parents=True,exist_ok=True);report=folder/'observation.json';report.unlink(missing_ok=True)
    instructions=[]
    for start,end in RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    branch_pcs={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bset','bclr','bra'))}
    static=folder/'source.json';static.write_text(json.dumps(dict(source=source,instructions=instructions),indent=2)+'\n')
    for r in instructions:assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
    names=('tools/observe_stage_activation_helpers.py','tools/disassemble_program.py','tools/verify_object_reset.py','tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py')
    inputs={name:sha((root/name).read_bytes()) for name in names};inputs['artifacts/stage_activation_helpers/source.json']=sha(static.read_bytes());oracle=oracle_provenance()
    observer=Observer(program,branch_pcs);rows=[];coverage=collections.Counter()
    for index,case in enumerate(cases()):
        ram=fixture(case,index);output,result,ports,trace,info=observer.run(case,ram)
        files=dict(input_ram_file='input_%03d.bin'%index,ram_file='native_%03d.bin'%index,ports_file='native_%03d.ports.bin'%index,trace_file='native_%03d.trace.json'%index)
        payloads=dict(input_ram_file=ram,ram_file=output,ports_file=ports,trace_file=(json.dumps(trace,indent=2)+'\n').encode())
        for key,data in payloads.items():(folder/files[key]).write_bytes(data)
        for b in info['branches']:coverage[(b['pc'],b['next_pc'])]+=1
        rows.append(dict(case_index=index,fixture=case,result=result,input_ram_sha256=sha(ram),ram_sha256=sha(output),ports_sha256=sha(ports),trace_sha256=sha(payloads['trace_file']),port_count=len(ports)//9,**files,**info))
    for pc in branch_pcs:
        assert len({dest for branch,dest in coverage if branch==pc})==(1 if pc==0x49fb2 else 2),hex(pc)
    for name in names:assert inputs[name]==sha((root/name).read_bytes())
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    summary=dict(collections.Counter(hex(row['fixture']['entry']) for row in rows))
    report.write_text(json.dumps(dict(source=source,oracle=oracle,inputs=inputs,cases=len(rows),completed_cases=len(rows),entry_counts=summary,
        total_native_ports=sum(r['port_count'] for r in rows),conditional_branch_count=len(branch_pcs),
        branch_coverage=[dict(pc=pc,next_pc=dest,count=count) for (pc,dest),count in sorted(coverage.items())],
        normal_branches_both_outcomes=True,animation_A5_TRAP_guard_success_only=True,
        original_program_modified=False,in_call_SR_read=False,carry_read_after_RTS_outside_hook=True,
        full_RAM_15_registers_ordered_writes_observed=True,Cpp_comparison_performed=False,results=rows,
        scope='Unpatched4e216/bee/16ed2/49f8c throughRTS, allRAM15regs and orderedRAM/stack/PVC writes, carryonlyfirsttwo. SRbeforeA7, isolatedstack/immutableprogram guards. CanonicalA5normal49f8c only; noTRAP-success/physicalhardware/cycle/otherCCR/naturalstageclaim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),entries=summary,branches=len(branch_pcs),ports=sum(r['port_count'] for r in rows),sha256=sha(report.read_bytes()))))

if __name__=='__main__':main()
