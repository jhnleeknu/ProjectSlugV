"""Immutable4847c native readiness observation; no C++ comparison."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program, disassemble_range
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from observe_screen_reset_full import BASE, STACK, STACK_START, RETURN, KEYS, REGS
from verify_stage_catalog import SOURCE_SHA256
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance as musashi_provenance

ENTRY=0x4847c
RANGES=((ENTRY,0x484b4),(0x1bdde,0x1be3a),(0x289e,0x28ae),(0x4dee2,0x4df1a),(0x4e166,0x4e186))
CALLEES=(ENTRY,0x1bdde,0x289e,0x4dee2,0x4e166)
PROFILES=(
    dict(name='inactive',marker=0x270e,a8=0,flag61=0,word=0,type=0,status=0),
    dict(name='a8-priority',marker=0x123456,a8=16,flag61=128,word=0,type=0,status=0),
    dict(name='flag61-block',marker=0x123456,a8=0,flag61=128,word=0,type=0,status=0),
    dict(name='record-negative',marker=0x123456,a8=0,flag61=0,word=0x8000,type=1,status=3),
    dict(name='record-type0',marker=0x123456,a8=0,flag61=0,word=0,type=0,status=3),
    dict(name='record-type3',marker=0x123456,a8=0,flag61=0,word=0x7fff,type=3,status=4),
    dict(name='type1-status2',marker=0x123456,a8=0,flag61=0,word=0,type=1,status=2),
    dict(name='type1-status3',marker=0x123456,a8=0,flag61=0,word=0,type=1,status=3),
    dict(name='type2-status4',marker=0x123456,a8=0,flag61=0,word=0,type=2,status=4),
    dict(name='type1-status5',marker=0x123456,a8=0,flag61=0,word=0,type=1,status=5),
    dict(name='type2-status6',marker=0x123456,a8=0,flag61=0,word=0,type=2,status=6),
    dict(name='type2-status255',marker=0x123456,a8=0,flag61=0,word=0,type=2,status=255),
    dict(name='type1-status0',marker=0x123456,a8=0,flag61=0,word=0,type=1,status=0),
    dict(name='record-wordffff',marker=0x123456,a8=0,flag61=0,word=0xffff,type=2,status=5))

def sha(data):return hashlib.sha256(data).hexdigest()

def build_cases():
    cases=[]
    for first,second in itertools.product(range(len(PROFILES)),repeat=2):
        cases.append(dict(first=first,second=second,a5=0x108000,flag=0,mask=len(cases)%4))
    for flag,mask in itertools.product((1,255),range(4)):
        cases.append(dict(first=6,second=10,a5=0x108000,flag=flag,mask=mask))
    for a5,first,second in itertools.product((0x107ffe,0x108002),(0,7),(0,8)):
        cases.append(dict(first=first,second=second,a5=a5,flag=1,mask=0))
    cases.append(dict(first=0,second=0,a5=0x10a2ee,flag=0,mask=3,
        skipped_bad_ram='both record addresses at/above110000, inactive objects skip reads'))
    cases.append(dict(first=2,second=None,a5=0x117258,flag=None,mask=None,
        skipped_bad_ram='second object starts110000; first player fails before second/flag/records'))
    return cases

def fixture(case,index):
    ram=bytearray(hashlib.shake_256(b'stage-readiness-'+bytes([index%4])).digest(65536));writes=[]
    def put(address,size,value):
        assert BASE<=address and address+size<=BASE+65536,(hex(address),size)
        at=address-BASE;ram[at:at+size]=value.to_bytes(size,'big')
        writes.append(dict(address=address,size=size,value=value))
    a5=case['a5']
    for player,key in enumerate(('first','second')):
        if case[key] is None:continue
        profile=PROFILES[case[key]];a0=a5-(0x7258 if player else 0x7348);a4=a5+(0x5d18 if player else 0x5d12)
        put(a0,4,profile['marker']);put(a0+0xa8,1,profile['a8']);put(a0+0x61,1,profile['flag61'])
        if BASE<=a4 and a4+6<=BASE+65536:
            put(a4,1,profile['type']);put(a4+2,1,profile['status']);put(a4+4,2,profile['word'])
    if case['flag'] is not None:
        put(a5+0x5684,1,case['flag'])
        put(a5-0x75bc,1,2 if case['mask']&1 else 0)
        put(a5-0x74f8,1,2 if case['mask']&2 else 255)
    regs={key:((0xabcd1234 if index%2 else 0xffff0000)+i*0x10203)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=a5,a6=(0,0xffffffff,0x102000,0x87654321)[index%4])
    case.update(incoming=regs,host_writes=writes)
    return bytes(ram)

class Observer:
    def __init__(self,program,branches):
        self.program=program;self.cpu=make_cpu(program);self.baseline=self.cpu.context_save();self.branch_pcs=branches
        self.pcs=[];self.writes=[];self.reads=[];self.boundaries=[];self.branches=[];self.pending=None;self.error=None
        def code(cpu,pc,size,user):
            self.pcs.append(pc)
            if self.pending is not None:self.branches.append(dict(pc=self.pending,next_pc=pc));self.pending=None
            if pc in self.branch_pcs:self.pending=pc
            if pc==RETURN:cpu.emu_stop();return
            if not any(start<=pc<end for start,end in RANGES):self.error=dict(kind='unexpected-code',pc=pc);cpu.emu_stop();return
            if pc in CALLEES:self.boundaries.append(dict(pc=pc,a7=cpu.reg_read(m.UC_M68K_REG_A7),
                registers=dict(zip(KEYS,(cpu.reg_read(r)&0xffffffff for r in REGS)))))
        def write(cpu,access,address,size,value,user):
            event=dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(size*8))-1))
            self.writes.append(event)
            if not STACK_START<=address or address+size>STACK+4:self.error=dict(kind='nonstack-write',event=event);cpu.emu_stop()
        def read(cpu,access,address,size,value,user):
            if BASE<=address and address+size<=BASE+65536:
                self.reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(cpu.mem_read(address,size),'big')))
            elif not(address+size<=BASE or STACK_START<=address and address+size<=STACK+4):
                self.error=dict(kind='read-outside-ROM-RAM-stack',pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size);cpu.emu_stop()
        def invalid(cpu,access,address,size,value,user):
            self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(cpu,number,user):self.error=dict(kind='cpu-exception',number=number);cpu.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):self.cpu.hook_add(hook,callback)
    def run(self,case,ram):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,ram)
        cpu.mem_write(STACK_START,b'\x5a'*4100);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):cpu.reg_write(reg,case['incoming'][key])
        self.pcs.clear();self.writes.clear();self.reads.clear();self.boundaries.clear();self.branches.clear();self.pending=None;self.error=None
        try:cpu.emu_start(ENTRY,0xffffff,count=1000)
        except unicorn.UcError as exc:
            if self.error is None:self.error=dict(kind='emulator-error',error=str(exc))
        assert self.error is None,self.error
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
        # SR is sampled only after original RTS, never from an instruction hook.
        sr=cpu.reg_read(m.UC_M68K_REG_SR);carry=bool(sr&1)
        assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        assert bytes(cpu.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        lowest=min([e['address'] for e in self.writes]+[STACK]);assert bytes(cpu.mem_read(STACK_START,lowest-STACK_START))==b'\x5a'*(lowest-STACK_START)
        assert bytes(cpu.mem_read(0,BASE))==self.program[:BASE]
        output=bytes(cpu.mem_read(BASE,65536));assert output==ram
        result=dict(zip(KEYS,(cpu.reg_read(r)&0xffffffff for r in REGS)))
        info=dict(final_pc=RETURN,final_a7=STACK+4,carry=carry,returned_sr=sr,instructions=len(self.pcs)-1,
            calls=dict(collections.Counter(hex(b['pc']) for b in self.boundaries)),branches=self.branches.copy(),
            boundaries=self.boundaries.copy(),RAM_reads=self.reads.copy(),stack_writes=self.writes.copy(),lowest_stack_write=lowest)
        return output,result,dict(pcs=self.pcs.copy(),reads=self.reads.copy(),writes=self.writes.copy()),info

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256==source['sha256']
    folder=root/'artifacts/stage_readiness';folder.mkdir(parents=True,exist_ok=True)
    instructions=[]
    for start,end in RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    branch_pcs={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and r['mnemonic'] not in ('btst.b','bra.w')}
    static=folder/'source.json';static.write_text(json.dumps(dict(source=source,instructions=instructions),indent=2)+'\n')
    for row in instructions:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    names=('tools/observe_stage_readiness.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py',
        'tools/musashi_oracle.py','tools/observe_scene_motion_pair.py')
    inputs={name:sha((root/name).read_bytes()) for name in names};inputs['artifacts/stage_readiness/source.json']=sha(static.read_bytes())
    oracle=oracle_provenance();cross_oracle=musashi_provenance(root);report=folder/'observation.json';report.unlink(missing_ok=True)
    observer=Observer(program,branch_pcs);musashi=MusashiOracle();musashi.load(0,program[:BASE]);rows=[];coverage=collections.Counter();cross=[]
    cases=build_cases();cross_indices={0,1,2,3,7,14,196,200,len(cases)-2,len(cases)-1}
    for index,case in enumerate(cases):
        ram=fixture(case,index);output,result,trace,info=observer.run(case,ram)
        if index in cross_indices:
            musashi.reset();musashi.load(BASE,ram);musashi.load(STACK_START,b'\x5a'*4100);musashi.load(STACK,RETURN.to_bytes(4,'big'))
            musashi.set_reg('sr',0x2000);musashi.set_reg('a7',STACK)
            for key,value in case['incoming'].items():musashi.set_reg(key,value)
            musashi.set_reg('pc',ENTRY);status=musashi.run(1000,RETURN)
            assert status['status']=='sentinel',status
            other={key:musashi.get_reg(key) for key in KEYS};other_carry=bool(musashi.get_reg('sr')&1)
            assert other==result and other_carry==info['carry'] and musashi.read(BASE,65536)==output,(index,result,other,info['carry'],other_carry)
            cross.append(dict(case_index=index,status=status,carry=other_carry,full_RAM_15regs_carry_equal=True))
        files=dict(input_ram_file='input_%03d.bin'%index,ram_file='native_%03d.bin'%index,trace_file='native_%03d.trace.json'%index)
        payloads=dict(input_ram_file=ram,ram_file=output,trace_file=(json.dumps(trace,indent=2)+'\n').encode())
        for key,data in payloads.items():(folder/files[key]).write_bytes(data)
        for b in info['branches']:coverage[(b['pc'],b['next_pc'])]+=1
        rows.append(dict(case_index=index,fixture=case,result=result,input_ram_sha256=sha(ram),ram_sha256=sha(output),
            trace_sha256=sha(payloads['trace_file']),port_count=0,**files,**info))
    missing=[pc for pc in branch_pcs if len({dest for branch,dest in coverage if branch==pc})!=2]
    assert not missing,[hex(pc) for pc in missing]
    assert oracle==oracle_provenance() and cross_oracle==musashi_provenance(root)
    for name in names:assert inputs[name]==sha((root/name).read_bytes())
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report.write_text(json.dumps(dict(source=source,oracle=oracle,cross_oracle=cross_oracle,inputs=inputs,
        entry_pc=ENTRY,cases=len(rows),completed_cases=len(rows),profiles=PROFILES,
        branch_coverage=[dict(pc=pc,next_pc=dest,count=count) for (pc,dest),count in sorted(coverage.items())],
        conditional_branch_count=len(branch_pcs),every_conditional_branch_both_outcomes=True,
        total_native_ports=0,full_RAM_15_registers_returned_carry_observed=True,
        carry_read_after_RTS_outside_hook=True,in_call_SR_read=False,original_program_modified=False,
        musashi_crosschecks=cross,Cpp_comparison_performed=False,results=rows,
        scope='Immutable original4847c throughRTS with actual1bdde/289e/4dee2/4e166, fullRAM15regs/carry and complete stack writes/RAM operand reads. Controlled host fixtures, SRbeforeA7, isolated guarded stack; no helperstubs/carryoverrides. No physicalhardware/CCRotherbits/cycle/IRQ/scheduler/fullstageclaim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),conditional_branches=len(branch_pcs),both_outcomes=True,
        carry_true=sum(r['carry'] for r in rows),musashi_crosschecks=len(cross),sha256=sha(report.read_bytes()))))

if __name__=='__main__':main()
