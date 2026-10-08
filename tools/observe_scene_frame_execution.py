"""Original uninterrupted full-frame observations with actual native initializer seeds."""
import collections
import json
from pathlib import Path
import struct
import unicorn
from unicorn.unicorn_py3 import unicorn as native_unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from observe_scene_general_initialization import BASE,STACK,RETURN,KEYS,REGS,PORTS,sha,resources,build_cases as initialization_cases
from verify_stage_catalog import SOURCE_SHA256
from inventory_scene_frame_execution import inventory
ENTRY=0x1a73c
CAP=2000000
BOUNDARIES=(0x1a73c,0x1a752,0x1a756,0x1a75a,0x1a75e,0x1a762,0x1a766,0x1a76a,0x1a772,0x1a776,0x1a77c,0x1a780,0x1a784,0x1a788,0x1a78c,0x1a790,0x1a7a6)
CALLEES=(0x1a2b4,0x1a29e,0x1a26a,0x1a526,0x19b96,0x19cd6,0x19ce6,0x19c28,0x19d08,0x19802,0x1a3d6,0x1a7a8,0x1a442,0x1a470,0x28ae,0x2912,0x43e08,0x19e64,0x183c6,0x185f2,0x1861a,0x1afda,0x1b0e0)


def oracle_provenance():
    assert unicorn.__version__=='2.1.4'
    library=Path(native_unicorn.uclib._name);wrapper=Path(native_unicorn.__file__)
    return dict(engine='Unicorn M68000',version=unicorn.__version__,library_file=str(library),library_sha256=sha(library.read_bytes()),wrapper_file=str(wrapper),wrapper_sha256=sha(wrapper.read_bytes()),in_call_SR_read=False)


def seeds(root,program):
    folder=root/'artifacts/scene_general_initialization';path=folder/'observation.json';data=path.read_bytes();native=json.loads(data);verification_path=folder/'verification.json';verification=json.loads(verification_path.read_text());cases=initialization_cases(root,program)
    assert native['source']['sha256']==SOURCE_SHA256 and native['failure'] is None and native['cases']==native['completed_cases']==len(native['results'])==len(cases)==221
    assert verification['native_observation_sha256']==sha(data) and verification['cases']==221 and verification['full_RAM_14_registers_ordered_ports_equal']
    rs,manifests=resources(root,program);assert len(rs)==458 and native['resources']==rs and native['manifests']==manifests
    for index,(row,case) in enumerate(zip(native['results'],cases)):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4
        assert sha((folder/row['ram_file']).read_bytes())==row['ram_sha256'] and sha((folder/row['ports_file']).read_bytes())==row['ports_sha256']
    audit_path=root/'artifacts/scene_frame_execution_disassembly.json';audit=json.loads(audit_path.read_text());assert audit==json.loads(json.dumps(inventory(root)))
    metadata=dict(frame_inventory_file=str(audit_path.relative_to(root)),frame_inventory_sha256=sha(audit_path.read_bytes()),initialization_observation_file=str(path.relative_to(root)),initialization_observation_sha256=sha(data),initialization_verification_file=str(verification_path.relative_to(root)),initialization_verification_sha256=sha(verification_path.read_bytes()))
    return native,rs,manifests,metadata


def build_cases(root,program):
    native,rs,manifests,metadata=seeds(root,program);cases=[]
    for index,row in enumerate(native['results']):cases.append(dict(family='canonical-post-initialization-frame',seed_index=index,initializer=row['fixture'],host_writes=[]))
    def write(address,size,value):return dict(address=address,hex=value.to_bytes(size,'big').hex())
    for seed,count,force,label in ((4,32,0x100,'canonical-script-wait16-settings'),(22,132,0x100,'canonical-placement-gate128'),(25,56,0x1000,'canonical-two-eligible-placements'),(34,72,0x1000,'canonical-script-multiple-waits-placement'),(4,12,0xff00,'canonical-forced-time-clipping'),(150,56,0x1000,'canonical-empty-allocation-placement')):
        for step in range(count):cases.append(dict(family='actual-cli-carried-frames',seed_index=seed,sequence=label,sequence_position=step,host_writes=[write(0x10d44c,2,force)] if step==0 else [],controlled_initial_force=force))
    for amplitude in (0x00080000,0xfff80000,0x7fffffff,0x80000000):cases.append(dict(family='shake-propagation-before-coordinate-update',seed_index=0,host_writes=[write(0x10d408,4,amplitude)]))
    cases.append(dict(family='canonical-condition-true-duration-before-script',seed_index=41,host_writes=[write(0x10d68e,1,3),write(0x100cb8,4,0x270e),write(0x100da8,4,0x270e)]))
    for accepted in (False,True):
        writes=[write(0x10d422,4,0x106000),write(0x106000,4,0x00001234),write(0x10d41e,2,0 if accepted else 1)]
        if not accepted:writes+=[write(0x10d412,4,0xffffffff),write(0x10d416,2,0)]
        cases.append(dict(family='RAM-selector0-condition-'+('true' if accepted else 'false-bypasses-invalid-script'),seed_index=0,host_writes=writes))
    for seed in (0,4,25,34):
        script=native['results'][seed]['fixture']['script'];writes=[write(0x10d412,4,script),write(0x10d416,2,0),write(0x10d422,4,0),write(0x10d3b4,4,0)]
        writes+=[write(BASE+at,4,0) for at in (0xd356,0xd364,0xd372,0xd380)]
        cases.append(dict(family='controlled-canonical-setup-replay-before-motion-path-selection',seed_index=seed,host_writes=writes))
    for debug in (8,16):cases.append(dict(family='explicit-debug8-16-on-retained-native-cache',seed_index=129,debug=debug,host_writes=[write(0x10f000,1,debug)]))
    assert len(cases)==594
    return cases,rs,manifests,metadata


def fixture(root,case):
    path=root/'artifacts/scene_general_initialization/observation.json';row=json.loads(path.read_text())['results'][case['seed_index']];ram=bytearray((path.parent/row['ram_file']).read_bytes());assert sha(ram)==row['ram_sha256'];regs=[row['result'][key] for key in KEYS]
    return ram,regs


def prepare(case,ram):
    for write in case['host_writes']:
        raw=bytes.fromhex(write['hex']);at=write['address']-BASE;assert 0<=at and at+len(raw)<=65536;ram[at:at+len(raw)]=raw


def snapshot(cpu):
    ram=bytes(cpu.mem_read(BASE,65536))
    return dict(phase=int.from_bytes(ram[0xd418:0xd41a],'big'),condition=int.from_bytes(ram[0xd422:0xd426],'big'),script=int.from_bytes(ram[0xd412:0xd416],'big'),script_wait=int.from_bytes(ram[0xd416:0xd418],'big'),force=int.from_bytes(ram[0xd3fa:0xd3fc],'big'),fixed_delta=[int.from_bytes(ram[a:a+4],'big') for a in (0xd3fc,0xd400)],camera_flags=ram[0xd3cc],motion=int.from_bytes(ram[0xd3b4:0xd3b8],'big'),placement=int.from_bytes(ram[0xd40e:0xd412],'big'),camera=[int.from_bytes(ram[at:at+4],'big') for at in (0xd3bc,0xd3c0)],paths=[int.from_bytes(ram[at:at+4],'big') for at in (0xd356,0xd364,0xd372,0xd380)],shake=int.from_bytes(ram[0xd404:0xd406],'big'),shake_amplitude=int.from_bytes(ram[0xd408:0xd40c],'big'),d7=cpu.reg_read(m.UC_M68K_REG_D7)&0xffffffff)


class Observer:
    """Unicorn PC/register-only hooks; never read SR during execution."""
    def __init__(self,program):
        self.cpu=make_cpu(program);self.cpu.mem_map(0x200000,0x300000);self.baseline=self.cpu.context_save();self.program=program;self.ports=[];self.calls=collections.Counter();self.boundaries=[];self.commands=[];self.error=None;self.instructions=0;self.bank=0x200000;self.reads=[];self.bank_reads=collections.Counter();self.ram_writes=[];self.ram_write_count=0;self.branch_pending=None;self.branches=[];self.shake_additions=[];self.shake_pending=None;self.fallback_writes=[]
        def code(cpu,address,size,user):
            self.instructions+=1
            if address==RETURN:cpu.emu_stop();return
            if self.shake_pending is not None:
                pending=self.shake_pending;pending['after']=int.from_bytes(cpu.mem_read(pending['address'],2),'big');self.shake_additions.append(pending);self.shake_pending=None
            if address in (0x1a7d6,0x1a812,0x1a84e,0x1a88a,0x1a8c6):
                target=cpu.reg_read(m.UC_M68K_REG_A0)+0x18;self.shake_pending=dict(pc=address,address=target,before=int.from_bytes(cpu.mem_read(target,2),'big'),delta=cpu.reg_read(m.UC_M68K_REG_D0)&65535)
            if self.branch_pending is not None:self.branches.append(dict(pc=self.branch_pending,next_pc=address));self.branch_pending=None
            if address in (0x1a756,0x1a77c):self.branch_pending=address
            if address in CALLEES:self.calls[address]+=1
            if address in BOUNDARIES:self.boundaries.append(dict(pc=address,**snapshot(cpu)))
            if address==0x1a0b6:self.commands.append(cpu.reg_read(m.UC_M68K_REG_A1)&0xffffffff)
            word=int.from_bytes(cpu.mem_read(address,2),'big')
            if word==0x4afc or 0x4e40<=word<=0x4e4f:self.error=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            if BASE<=address and address+size<=BASE+65536:
                self.ram_write_count+=1
                if 0x100ec6<=address<0x100eec:self.fallback_writes.append(dict(address=address,size=size,value=value&((1<<(size*8))-1)))
                if 0x10d3b4<=address<0x10d450 or address==0x100010:self.ram_writes.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(size*8))-1)))
                return
            if STACK-4096<=address and address+size<=STACK+4:return
            if address not in PORTS:self.error=dict(kind='unexpected-write',address=address,size=size,value=value);cpu.emu_stop();return
            self.ports.append((size,address,value&((1<<(size*8))-1)))
            if address==0x2ffff2:
                if size!=2 or value not in (0x1000,0x2000):self.error=dict(kind='unsupported-bank',value=value);cpu.emu_stop();return
                self.bank=0x200000 if value==0x1000 else 0x300000;cpu.mem_write(0x200000,program[self.bank:self.bank+0xffff0])
        def read(cpu,access,address,size,value,user):
            if 0x200000<=address<0x2ffff0:self.bank_reads[self.bank]+=1
            if address<0x500000 and address+size>0x2ffff0:self.reads.append((size,address))
        def invalid(cpu,access,address,size,value,user):self.error=dict(kind='invalid-memory',access=access,address=address,size=size);return False
        def intr(cpu,number,user):self.error=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read);self.cpu.hook_add(UC_HOOK_MEM_INVALID,invalid);self.cpu.hook_add(UC_HOOK_INTR,intr)
    def run(self,ram,regs):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,self.program[0x200000:0x2ffff0]);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        self.ports.clear();self.fallback_writes.clear();self.calls.clear();self.boundaries.clear();self.commands.clear();self.reads.clear();self.bank_reads.clear();self.ram_writes.clear();self.branches.clear();self.shake_additions.clear();self.shake_pending=None;self.branch_pending=None;self.ram_write_count=0;self.error=None;self.instructions=0;self.bank=0x200000
        try:cpu.emu_start(ENTRY,0xffffff,count=CAP)
        except unicorn.UcError as error:
            if self.error is None:self.error=dict(kind='emulator-error',error=str(error),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=RETURN and self.error is None:self.error=dict(kind='instruction-cap',cap=CAP,pc=pc)
        assert bytes(cpu.mem_read(0,BASE))==self.program[:BASE] and bytes(cpu.mem_read(0x200000,0xffff0))==self.program[self.bank:self.bank+0xffff0]
        assert not self.reads,self.reads[:10]
        if pc==RETURN:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        output=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(r)&0xffffffff for r in REGS)));ports=b''.join(struct.pack('>BII',*p) for p in self.ports)
        return output,result,ports,dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),calls={hex(k):v for k,v in self.calls.items()},boundaries=self.boundaries.copy(),branch_successors=self.branches.copy(),command_addresses=self.commands.copy(),instructions=self.instructions,error=self.error,final_bank=self.bank,physical_bank_reads={hex(k):v for k,v in self.bank_reads.items()},mmio_reads=0,fallback_position_writes=self.fallback_writes.copy(),shake_additions=self.shake_additions.copy(),control_RAM_writes=self.ram_writes.copy(),RAM_write_count=self.ram_write_count)


def assert_evidence(case,ram,output,ports,info):
    if not info['returned']:return
    events=[struct.unpack_from('>BII',ports,at) for at in range(0,len(ports),9)];assert events[:2]==[(2,0x2ffff2,0x2000),(2,0x2ffff0,0)] and events[-2:]==[(2,0x2ffff2,0x1000),(2,0x2ffff0,0)] and output[0x10:0x12]==bytes(2)
    for key in ('0x1a2b4','0x1a526','0x19b96','0x19d08','0x1a3d6','0x1a7a8','0x1a442'):assert info['calls'].get(key)==1,(key,info['calls'])
    assert info['calls'].get('0x1a470',0)<=1
    pcs=[b['pc'] for b in info['boundaries']];expected=[p for p in BOUNDARIES if p not in (0x1a75a,0x1a780)];assert [p for p in pcs if p not in (0x1a75a,0x1a780)]==expected
    branch={b['pc']:b['next_pc'] for b in info['branch_successors']};assert bool(info['calls'].get('0x1a26a'))==(branch[0x1a756]==0x1a75a)
    snapshots={b['pc']:b for b in info['boundaries']};before=snapshots[0x1a77c];after=snapshots[0x1a784];assert after['phase']==(before['d7']&65535 if branch[0x1a77c]==0x1a780 else before['phase'])
    assert snapshots[0x1a788]['shake']==snapshots[0x1a78c]['shake']
    assert len(info['shake_additions'])==5
    for addition in info['shake_additions']:assert addition['delta']==snapshots[0x1a788]['shake'] and addition['after']==(addition['before']+addition['delta'])&65535
    if case['family']=='RAM-selector0-condition-false-bypasses-invalid-script':assert not info['calls'].get('0x1a26a') and not info['command_addresses']
    if case['family']=='canonical-condition-true-duration-before-script' or case['family']=='RAM-selector0-condition-true':assert info['calls'].get('0x1a29e')==1 and info['calls'].get('0x1a26a')==1
    if case['family']=='controlled-canonical-setup-replay-before-motion-path-selection':assert info['command_addresses'] and snapshots[0x1a752]['motion']==0 and snapshots[0x1a762]['motion']!=0 and any(snapshots[0x1a788]['paths'])


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,rs,manifests,metadata=build_cases(root,program);oracle=oracle_provenance();folder=root/'artifacts/scene_frame_execution';folder.mkdir(parents=True,exist_ok=True);observer=Observer(program);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram,regs=fixture(root,case) if prior is None else (bytearray(prior[0]),prior[1].copy());prepare(case,ram);output,result,ports,info=observer.run(ram,regs);assert_evidence(case,ram,output,ports,info)
        if 'sequence'in case:previous[case['sequence']]=(output,[result[key] for key in KEYS])
        name='native_%04d.bin'%index;pname='native_%04d.ports.bin'%index;(folder/name).write_bytes(output);(folder/pname).write_bytes(ports);rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),input_ram_sha256=sha(ram),result=result,ram_file=name,ram_sha256=sha(output),ports_file=pname,ports_sha256=sha(ports),port_count=len(ports)//9,**info))
        if info['error']:break
    for item in rs+manifests:assert sha((root/item['file']).read_bytes())==item['sha256']
    for label in ('initialization_observation','initialization_verification','frame_inventory'):assert sha((root/metadata[label+'_file']).read_bytes())==metadata[label+'_sha256']
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==oracle
    report=dict(source=source,oracle=oracle,cases=len(cases),completed_cases=sum(row['returned'] for row in rows),failure=observer.error,results=rows,resources=rs,manifests=manifests,metadata=metadata,program_code_modified=False,physical_bank_payload_modified=False,in_call_SR_read=False,scope='Original uninterrupted 1a73c and all original callees to RTS; all 64 KiB RAM, 14 exposed registers, exact ordered 9-byte ports. Unicorn hooks inspect PC/registers but never SR during execution. Fixed ROM and original physical bank 2/3 payloads immutable; exact PVC1000/2000 bank mapping. Inputs are actual stored source-verified continuous native general-initializer outputs. Controlled initial force fixtures feed six actual-output frame chains without subsequent host rewrites. Initial setup replay explicitly repositions the canonical script cursor, clears motion and path cursors, and lets original canonical commands publish them. Other host writes are listed per case. No IRQ/scheduler/callback execution, natural-player or carry/cycle-equivalence claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],ports=sum(row['port_count'] for row in rows),failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
