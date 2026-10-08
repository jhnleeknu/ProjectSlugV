"""Unpatched49fc6 opcode14/1f with actual nested sound continuations."""
import collections
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from observe_object_sound_lookup import fixture as sound_fixture,put,sha,oracle_provenance,make_cpu,load_verified_program,disassemble_range,BASE,STACK,STACK_START,RETURN,KEYS,REGS,SOURCE_SHA256
ENTRY,WAIT,EXTERNAL=0x49fc6,0x3aea,0xd00046
RANGES=((ENTRY,0x4a104),(0x4a276,0x4a27e),(0x4a408,0x4a46c),(0x47672,0x476bc),(0xca70,0xca76),(0x3ac8,0x3c08))
BOUNDARIES=(ENTRY,0x4a408,0x47672,0x3af8,0x4768e,0x47690,0x4a43e,0x4a460,0x4a464,0x4a468,0x4a276)
def cases():
    rows=[]
    for sound in (False,True):
        for mode,external in ((0,0),(1,0),(2,0),(3,0),(3,1),(3,255),(4,0),(5,0)):
            rows.append(dict(a5=0x108000,a6=0x102000,source_word=0x5a01,sound=sound,wait=0,mode=mode,external=external,queue_alias=False))
    for wait in (1,2,3):rows.append(dict(a5=0x108000,a6=0x102000,source_word=0x5a01,sound=True,wait=wait,mode=0,external=0,queue_alias=False))
    return rows
def fixture(case,index):
    ram,regs=sound_fixture(case,index);ram=bytearray(ram)
    for address,size,value in ((0x102026,4,0x106000),(0x10202a,2,0),(0x10202c,2,256),(0x102017,1,0),(0x100010,2,0xbeef)):
        put(ram,address,size,value)
    ram[0x6000:0x6008]=bytes.fromhex('141f123456780000')
    return bytes(ram),regs
class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=make_cpu(program)
        self.cpu.mem_map(0x2ff000,4096);self.cpu.mem_map(0x300000,0x100000);self.cpu.mem_map(0xd00000,4096)
        self.baseline=self.cpu.context_save();self.pcs=[];self.reads=[];self.writes=[];self.boundaries=[];self.error=None;self.visits=0
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc in BOUNDARIES:
                sp=c.reg_read(m.UC_M68K_REG_A7)
                self.boundaries.append(dict(pc=pc,a7=sp,registers=self.regs(),stack=bytes(c.mem_read(sp,STACK+4-sp)).hex()))
            if not any(a<=pc<b for a,b in RANGES):self.error=('unexpected-code',pc);c.emu_stop()
            opcode=int.from_bytes(c.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:self.error=('trap',pc);c.emu_stop()
            if pc==WAIT:
                head=int.from_bytes(c.mem_read(0x104d74,2),'big')
                if head==(c.reg_read(m.UC_M68K_REG_D1)&65535):
                    self.visits+=1
                    if self.visits==2:c.emu_stop()
                else:self.visits=0
        def write(c,access,address,size,value,user):
            kind='ports' if address in (0x2ffff0,0x2ffff2) and size==2 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(size*8))-1),kind=kind);self.writes.append(event)
            if kind is None:self.error=('unexpected-write',event);c.emu_stop()
        def read(c,access,address,size,value,user):
            kind='ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else 'external' if address==EXTERNAL and size==1 else 'fixed' if address+size<=BASE else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind);self.reads.append(event)
            if kind is None:self.error=('unexpected-read',event);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=('invalid',address,size);return False
        def intr(c,number,user):self.error=('exception',number,c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):self.cpu.hook_add(hook,callback)
    def regs(self):return {k:self.cpu.reg_read(r)&0xffffffff for k,r in zip(KEYS,REGS)}
    def prepare(self,ram,regs,external):
        c=self.cpu;c.context_restore(self.baseline);c.mem_write(BASE,ram);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'));c.mem_write(EXTERNAL,bytes([external]))
        c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
        for k,r in zip(KEYS,REGS):c.reg_write(r,regs[k])
        c.reg_write(m.UC_M68K_REG_PC,ENTRY);self.low=STACK
    def mutate(self,changes):
        for x in changes:self.cpu.mem_write(x['address'],x['value'].to_bytes(x['size'],'big'))
    def run(self):
        c=self.cpu;before=bytes(c.mem_read(BASE,65536));incoming=self.regs();start=c.reg_read(m.UC_M68K_REG_PC)
        self.pcs.clear();self.reads.clear();self.writes.clear();self.boundaries.clear();self.error=None;self.visits=0
        c.emu_start(start,0xffffff,count=100000);pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc in (RETURN,WAIT),(self.error,hex(pc))
        pending={};carry=None;result=self.regs()
        if pc==WAIT:
            assert self.visits==2
            top=int.from_bytes(c.mem_read(sp,4),'big');phase={0x3c00:1,0x4768e:2}[top]
            assert sp==STACK-(28 if phase==1 else 22)
            assert int.from_bytes(c.mem_read(STACK-14,4),'big')==0x4a43e
            assert int.from_bytes(c.mem_read(STACK-22,4),'big')==0x4768e
            pending=dict(sound_phase=phase,saved_low=c.mem_read(sp+4,1)[0] if phase==1 else result['d0']&255,
                inner_a0=int.from_bytes(c.mem_read(STACK-18,4),'big'),outer_a0=int.from_bytes(c.mem_read(STACK-4,4),'big'),
                outer_a1=int.from_bytes(c.mem_read(STACK-8,4),'big'),bank=int.from_bytes(c.mem_read(STACK-10,2),'big'),raw=bytes(c.mem_read(sp,STACK+4-sp)).hex())
            assert (pending['inner_a0'],pending['outer_a0'],pending['outer_a1'],pending['bank'])==(0x10095c,0x102026,0x106006,0)
        else:assert sp==STACK+4;carry=bool(c.reg_read(m.UC_M68K_REG_SR)&1)
        assert bytes(c.mem_read(0,BASE))==self.program[:BASE] and bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
        self.low=min([self.low]+[x['address'] for x in self.writes if x['kind']=='stack']);assert bytes(c.mem_read(STACK_START,self.low-STACK_START))==b'\x5a'*(self.low-STACK_START)
        replay=bytearray(before);ports=[]
        for x in self.writes:
            if x['kind']=='ram':replay[x['address']-BASE:x['address']-BASE+x['size']]=x['value'].to_bytes(x['size'],'big')
            if x['kind']=='ports':ports.append(struct.pack('>BII',x['size'],x['address'],x['value']))
        output=bytes(c.mem_read(BASE,65536));assert bytes(replay)==output
        trace=dict(pcs=self.pcs.copy(),reads=self.reads.copy(),ordered_writes=self.writes.copy(),boundaries=self.boundaries.copy())
        for b in self.boundaries:
            if b['pc']==0x4a460:
                raw=bytes.fromhex(b['stack']);after=next(x for x in self.boundaries if x['pc']==0x4a464)
                for key,offset in (('d0',0),('d7',2)):
                    v=int.from_bytes(raw[offset:offset+2],'big');assert after['registers'][key]==(v if v<0x8000 else v|0xffff0000)
            if b['pc']==0x4a468:assert b['registers']['a0']==0x102026 and b['registers']['a1']==0x106006
        return dict(incoming=incoming,result=result,waiting=pc==WAIT,carry=carry,pending=pending,final_pc=pc,final_a7=sp,trace=trace),before,output,b''.join(ports)
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/animation_sound_callback';folder.mkdir(parents=True,exist_ok=True);report=folder/'observation.json';report.unlink(missing_ok=True)
    oracle=oracle_provenance();names=('tools/observe_animation_sound_callback.py','tools/observe_object_sound_lookup.py','tools/disassemble_program.py','tools/verify_object_reset.py','tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py')
    inputs={n:sha((root/n).read_bytes()) for n in names};observer=Observer(program);rows=[]
    for i,case in enumerate(cases()):
        ram,regs=fixture(case,i);observer.prepare(ram,regs,case['external']);phases=[]
        def observe(label,changes=()):
            info,before,output,ports=observer.run();trace=info.pop('trace');prefix='case_%03d_%s'%(i,label)
            payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
            for n,data in payloads.items():(folder/n).write_bytes(data)
            info.update(phase=label,host_changes=list(changes),files={n:sha(v) for n,v in payloads.items()},input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json',port_count=len(ports)//9)
            phases.append(info);return info,trace
        begin,trace=observe('begin')
        if case['wait']:
            assert begin['waiting'] and begin['pending']['sound_phase']==(2 if case['wait']==2 else 1)
            changes=[dict(address=0x10095c,size=2,value=0x1234),dict(address=0x10207e,size=1,value=0x12),dict(address=0x104d7e,size=1,value=1),dict(address=0x100010,size=2,value=0xbeef),dict(address=0x106002,size=4,value=0xdeadbeef)]
            observer.mutate(changes);hold,trace=observe('hold',changes);assert hold['waiting'] and hold['result']==begin['result'] and not trace['ordered_writes'] and not trace['boundaries']
            changes=[dict(address=0x104d74,size=2,value=2 if case['wait']==3 else 0xffff)]
            observer.mutate(changes);ready,trace=observe('high_to_low' if case['wait']==3 else 'ready',changes)
            if case['wait']==3:
                assert ready['waiting'] and ready['pending']['sound_phase']==2
                again,trace=observe('low_hold');assert again['waiting'] and not trace['ordered_writes']
                changes=[dict(address=0x104d74,size=2,value=0xffff)];observer.mutate(changes);ready,trace=observe('ready',changes)
            assert not ready['waiting'] and not any(b['pc'] in (ENTRY,0x4a408,0x47672,0x3af8) for b in trace['boundaries'])
        else:assert not begin['waiting']
        rows.append(dict(case_index=i,fixture=case,phases=phases))
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/n).read_bytes())==h for n,h in inputs.items())
    result=dict(source=source,oracle=oracle,inputs=inputs,cases=len(rows),phases=sum(len(r['phases']) for r in rows),results=rows,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,
        scope='Original49fc6 syntheticRAM14/1f scripts; canonicalA5/A6, gate and sameCPU high/low waits. WholeRAM15R/carry/PVC and nestedstack observed; no naturalgameplay/allcallbacks/physicalIRQ claim.')
    report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(cases=result['cases'],phases=result['phases'],sha256=sha(report.read_bytes()))))
if __name__=='__main__':main()
