"""Unpatched actual animation callers observing C through original BCC/BCS.

Controlled incoming fixtures; coherent16work-RAM mirrors and live shared stack.
No SR reads, ROM patches, stubs or register injection after execution begins.
"""
import collections
import copy
import ctypes
import hashlib
import inspect
import json
from pathlib import Path
import struct
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_callers as callers
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_carry_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=callers.RANGES+((0x1dc84,0x1dc8e),(0x210ae,0x210b8))
BOUNDARIES=callers.BOUNDARIES+(0x49fe6,0x49fea,0x4a0e0,0x4a0e2,0x1dc84,0x1dc8a,0x210ae,0x210b4)
sha,put,replay=extended.sha,extended.put,extended.replay
CALLERS=((0x1dc84,0x1dc8a,0x1dccc,0x1dc8e,'BCC'),(0x210ae,0x210b4,0x21564,0x210b8,'BCS'))


def matrix(program):
    existing=callers.matrix(program);selected=[24,25,26,28,31,35,37,39]+list(range(41,59))
    base=[copy.deepcopy(existing[i]) for i in selected]
    for label,script in (('00-duration0','0000'),('00-duration1-next28','000128'),('28-terminal','28')):
        row=copy.deepcopy(existing[24]);row['label']=label;row['selection']['chain']='none';row['synthetic_script']=script;base.append(row)
    rows=[]
    for caller,ret,target,fall,op in CALLERS:
        for b in base:
            row=dict(copy.deepcopy(b),entry_pc=caller,return_pc=ret,branch_target=target,branch_fallthrough=fall,branch_opcode=op,initializer_only=False)
            row['label']=op+'-'+row['label'];rows.append(row)
        row=copy.deepcopy(existing[0]);row.update(entry_pc=0x49f8c,return_pc=ret,branch_target=target,branch_fallthrough=fall,branch_opcode=op,initializer_only=True,pointer=0xffffffff)
        row['label']=op+'-controlled-initializer-return';rows.append(row)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    seed=dict(row,entry_pc=0x49f8c if row['initializer_only'] else 0x47f04,stop_pc=row['return_pc'])
    fx=callers.fixture(program,seed);ram=bytearray(fx['ram'])
    if row['initializer_only']:put(ram,S,4,row['return_pc'])
    if 'synthetic_script' in row:
        data=bytes.fromhex(row['synthetic_script']);ram[0x6000:0x6000+len(data)]=data
        put(ram,fx['regs']['a6']+0x26,4,0x106000);put(ram,fx['regs']['a6']+0x2a,2,0);put(ram,fx['regs']['a6']+0x2c,2,0x100)
    return dict(fx,ram=bytes(ram),entry_pc=row['entry_pc'],return_pc=row['return_pc'],branch_target=row['branch_target'],branch_fallthrough=row['branch_fallthrough'],branch_opcode=row['branch_opcode'],
                initial_return=int.from_bytes(ram[S&65535:(S&65535)+4],'big'),synthetic_script=row.get('synthetic_script'),
                initial_shared_stack=dict(fx['initial_shared_stack'],return_value=int.from_bytes(ram[S&65535:(S&65535)+4],'big')))


class Observer:
    def __init__(self,program,continuous=False):self.program=program;self.cpu=None;self.backing=None;self.continuous=continuous;self.branch_only=False
    def regs(self):return {key:self.cpu.reg_read(REGS[key]) for key in shared.isolated.REG_NAMES+('a7','pc')}
    def prepare(self,fx):
        self.stop_pc=fx['return_pc'];self.successors=(fx['branch_target'],fx['branch_fallthrough']);self.expected_a7=fx['expected_final_a7']
        self.backing=(ctypes.c_ubyte*SIZE).from_buffer_copy(fx['ram'])
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._ram_backing=self.backing
        c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        c.mem_map(0,RAM,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(0,self.program[:RAM])
        for i in range(16):c.mem_map_ptr(RAM+i*SIZE,SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        c.mem_map(0x200000,0xfe000,unicorn.UC_PROT_READ);c.mem_write(0x200000,self.program[0x200000:0x2fe000])
        c.mem_map(PVC,8192,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(PVC,fx['pvc'])
        c.mem_map(0xd00000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(EXTERNAL,bytes([fx['external']]))
        self.cpu=c;self.bank=0x200000;self.ff8=0xa0;self.ff9=0x1000
        self.boundary_set=set(BOUNDARIES)
        allowed=set()
        for lo,hi in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(self.program,lo,hi-lo,lo))
        def stop(problem,**fields):self.guard=dict(problem=problem,pc=self.pc,**fields);c.emu_stop()
        def code(cpu,pc,size,user):
            self.pc=pc;self.pcs.append(pc)
            if pc==self.stop_pc:
                self.return_snapshot=dict(registers=self.regs(),ram=bytes(self.backing),pvc=bytes(c.mem_read(PVC,8192)))
                if not self.continuous and not self.branch_only:cpu.emu_stop();return
            if pc in self.successors:cpu.emu_stop();return
            if pc not in allowed:stop('unsupported_code_target',target=pc);return
            opcode=int.from_bytes(cpu.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:stop('unsupported_TRAP',opcode=opcode);return
            if pc==0xcd5c and cpu.reg_read(REGS['a0'])!=0xcd50:stop('unsupported_sprite_callback');return
            if pc in (0x4a43c,0x4a352) and cpu.reg_read(REGS['a1']) not in (0x3679e,0x2b3e8,0x2b3fa,0x47672):stop('unsupported_animation_callback');return
            if pc in self.boundary_set:
                self.boundaries.append(dict(pc=pc,registers=self.regs(),stack_address=S-40,stack=bytes(cpu.mem_read(S-40,44)).hex()))
            if pc in (0xcda4,0x3aea):
                if pc==0xcda4:
                    waiting=int.from_bytes(cpu.mem_read((cpu.reg_read(REGS['a5'])+0xd34)&0xffffffff,2),'big')!=(cpu.reg_read(REGS['d4'])&65535)
                else:waiting=int.from_bytes(cpu.mem_read((cpu.reg_read(REGS['a5'])-0x328c)&0xffffffff,2),'big')==(cpu.reg_read(REGS['d1'])&65535)
                if waiting:
                    self.visits+=1
                    if self.visits==2:cpu.emu_stop();return
                else:self.visits=0
        def event(kind,address,size,value=None):
            if RAM<=address and address+size<=0x200000:region='ram'
            elif address<RAM and address+size<=RAM:region='fixed'
            elif 0x200000<=address and address+size<=PVC:region='bank'
            elif PVC<=address and address+size<=0x300000:region='pvc'
            elif address==EXTERNAL and size==1:region='external'
            else:stop('unsupported_data_device',address=address,size=size);return
            if kind=='write' and region not in ('ram','pvc'):stop('unsupported_write',address=address,size=size);return
            if region=='pvc' and (kind!='write' or size!=2 or address not in (0x2ffff0,0x2ffff2)):
                stop('unsupported_PVC_read_or_write',address=address,size=size);return
            if region=='bank' and self.bank!=0x200000:stop('bank_mapping_requires_different_bank',bank=self.bank);return
            if size>1 and address&1:stop('unsupported_odd_data_access',address=address,size=size);return
            before=bytes(c.mem_read(address,size));data=before if kind=='read' else (value&((1<<(size*8))-1)).to_bytes(size,'big')
            item=dict(pc=self.pc,hook_pc=c.reg_read(REGS['pc']),access=kind,address=address,size=size,bytes=data.hex(),before=before.hex(),region=region)
            if region=='pvc':
                v=int.from_bytes(data,'big')
                if address==0x2ffff0:self.ff8=v
                else:self.ff9=v
                self.bank,self.ff8,self.ff9=pvc_bank_update(self.ff8,self.ff9)
                item.update(bank_after=self.bank,ff8_after=self.ff8,ff9_after=self.ff9)
            self.events.append(item)
        def read(cpu,access,address,size,value,user):event('read',address,size)
        def write(cpu,access,address,size,value,user):event('write',address,size,value)
        def bad(cpu,access,address,size,value,user):stop('unmapped_or_protected',address=address,size=size);return False
        def interrupt(cpu,number,user):stop('CPU_exception',number=number)
        for hook,callback in ((unicorn.UC_HOOK_CODE,code),(unicorn.UC_HOOK_MEM_READ,read),(unicorn.UC_HOOK_MEM_WRITE,write),(unicorn.UC_HOOK_MEM_INVALID,bad),(unicorn.UC_HOOK_INTR,interrupt)):c.hook_add(hook,callback)
        c.reg_write(REGS['sr'],0x2000);c.reg_write(REGS['a7'],fx['initial_a7'])
        for key in shared.isolated.REG_NAMES:c.reg_write(REGS[key],fx['regs'][key])
        c.reg_write(REGS['pc'],fx['entry_pc'])
        return self
    def run(self,allow_guard=False):
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0;self.return_snapshot=None
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
        outgoing=self.regs()
        if not allow_guard:assert self.guard is None,self.guard
        if self.guard is None:assert outgoing['pc'] in (self.stop_pc,)+self.successors or outgoing['pc'] in (0xcda4,0x3aea) and self.visits==2,('timeout_or_stop',outgoing)
        if outgoing['pc'] in (self.stop_pc,)+self.successors:assert outgoing['a7']==self.expected_a7
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=self.guard is None and outgoing['pc'] in (0xcda4,0x3aea),return_snapshot=self.return_snapshot,guard=self.guard,modeled_bank=self.bank,
            bank_before=bank_before,ff8_before=ff8_before,ff9_before=ff9_before)
        assert bytes(self.cpu.mem_read(0,RAM))==self.program[:RAM]
        assert bytes(self.cpu.mem_read(0x200000,0xfe000))==self.program[0x200000:0x2fe000]
        assert all(bytes(self.cpu.mem_read(RAM+i*SIZE,SIZE))==bytes(self.backing) for i in range(16))
        replay(self.program,result)
        return result
    def mutate(self,changes):
        before=self.regs()
        for change in changes:self.cpu.mem_write(change['address'],change['value'].to_bytes(change['size'],'big'))
        assert self.regs()==before
    def close(self):self.cpu=None;self.backing=None



def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program,continuous)
    try:
        obs.prepare(fx);phases=[]
        def take(label,changes=()):
            obs.mutate(changes);phase=obs.run(row.get('expected_guard',False));phase['label']=label;phase['host_changes']=list(changes);phases.append(phase);return phase
        def finish():
            final=phases[-1];idx=final['pcs'].index(row['return_pc'])
            assert final['pcs'][idx-1] in ((0x49fc4,) if row['initializer_only'] else (0x49fea,0x4a0e2))
            assert final['return_snapshot']['registers']['a7']==fx['expected_final_a7']
            if not continuous:
                final['label']='return-boundary'
                obs.branch_only=True;branch=take('branch-result')
            else:branch=final;final['label']='continuous-branch-result'
            pc=branch['outgoing']['pc'];assert pc in (row['branch_target'],row['branch_fallthrough'])
            taken=pc==row['branch_target'];carry=1 if (taken if row['branch_opcode']=='BCC' else not taken) else 2
            for phase in phases:phase['carry']=None if phase['waiting'] else carry
            branch['branch_taken']=taken
            return row,fx,phases
        begin=take('begin')
        if row.get('expected_guard'):
            assert begin['guard']['problem']=='unsupported_TRAP' and begin['outgoing']['pc']==0x49fb6
            assert 0x49fac in begin['pcs'] and 0x49fb8 not in begin['pcs']
            return row,fx,phases
        if row['initializer_only']:
            assert not begin['waiting'];return finish()
        chain=row['selection']['chain']
        if chain=='none':assert not begin['waiting'],row
        elif chain in ('sprite','indexed-sprite'):
            assert begin['waiting'] and begin['outgoing']['pc']==0xcda4
            a6=begin['outgoing']['a6'];changes=[dict(address=a6+0x42,size=2,value=0x8000),dict(address=a6+0x46,size=2,value=0)]
            if chain=='indexed-sprite':
                pea=next(b for b in begin['boundaries'] if b['pc']==0x4a23e)
                slot=(pea['registers']['a7']-4)&0xffffffff
                assert int.from_bytes(obs.cpu.mem_read(slot,4),'big')==fx['details']['list_end']
                changes += [dict(address=shared.canonical(slot),size=4,value=0x106800),dict(address=0x106800,size=2,value=0),
                            dict(address=0x105802,size=2,value=0xffff),dict(address=0x105800,size=1,value=0xff)]
            hold=take('hold-poisoned-current-draw',changes)
            assert hold['waiting'] and hold['outgoing']==begin['outgoing'] and hold['ram_after']==hold['ram_before']
            release=take('release',[dict(address=hold['outgoing']['a5']+0xd34,size=2,value=hold['outgoing']['d4']&65535)])
            assert not release['waiting']
            if chain=='indexed-sprite':assert any(e['pc']==0x4a270 and e['access']=='read' and e['bytes']=='00106800' for e in release['events'])
        else:
            assert begin['waiting'] and begin['outgoing']['pc']==0x3aea
            a6=fx['regs']['a6'];at=(a6+0x26)&65535;script=int.from_bytes(fx['ram'][at:at+4],'big')
            changes=[dict(address=script,size=1,value=0xff)]
            if row['selection']['source'] in ('sound','word'):changes.append(dict(address=0x10095c,size=2,value=0x1234))
            # The saved low BYTE is located by the actual pending return LONG.
            sp=begin['outgoing']['a7'];high=int.from_bytes(obs.cpu.mem_read(sp,4),'big')==0x3c00
            if high:changes.append(dict(address=shared.canonical(sp+4),size=1,value=0x77))
            live_outer=row['selection']['source']=='direct_sound' and row['selection']['case'].get('chain')=='high_to_low'
            if live_outer:
                saved=next(b for b in begin['boundaries'] if b['pc']==0x4a2e2)
                outer_slot=(saved['registers']['a7']-8)&0xffffffff
                assert int.from_bytes(obs.cpu.mem_read(outer_slot,4),'big')==a6+0x26
                changes += [dict(address=shared.canonical(outer_slot),size=4,value=0x104900),
                            dict(address=0x104904,size=2,value=0),dict(address=0x104906,size=2,value=0x100)]
            hold=take('hold-live-low-and-prefix-poison',changes)
            assert hold['waiting'] and hold['outgoing']==begin['outgoing'] and hold['ram_after']==hold['ram_before']
            c=row['selection']['case'];two=c.get('wait')==3 or c.get('chain')=='high_to_low'
            if two:
                mid=take('high-to-low',[dict(address=0x104d74,size=2,value=((hold['outgoing']['d1']&65535)+1)&0x7f)])
                assert mid['waiting']
                low_hold=take('low-hold');assert low_hold['waiting'] and low_hold['outgoing']==mid['outgoing'] and low_hold['ram_before']==low_hold['ram_after']
            release=take('release',[dict(address=0x104d74,size=2,value=0xffff)]);assert not release['waiting']
            if live_outer:
                assert release['outgoing']['a0']==0x104900
                assert any(e['pc']==0x4a2ec and e['access']=='read' and e['address']==outer_slot and e['bytes']=='00104900' for e in release['events'])
                assert any(e['pc']==0x4a278 and e['access']=='write' and e['address']==0x104900 for e in release['events'])
            if high:assert any(e['pc']==0x3c00 and e['access']=='read' and e['bytes']=='77' for phase in phases[2:] for e in phase['events'])
        return finish()
    finally:obs.close()


def compare_control(row,split,control):
    assert len(split)==len(control)+1
    for actual,other in zip(split[:-2],control[:-1]):assert actual==other
    boundary,branch,continuous=split[-2],split[-1],control[-1]
    assert boundary['outgoing']==continuous['return_snapshot']['registers']==branch['incoming']
    assert boundary['ram_after']==continuous['return_snapshot']['ram']==branch['ram_before']
    assert boundary['pvc_after']==continuous['return_snapshot']['pvc']==branch['pvc_before']
    assert branch['outgoing']==continuous['outgoing']
    assert branch['ram_after']==continuous['ram_after']==branch['ram_before']
    assert branch['pvc_after']==continuous['pvc_after']==branch['pvc_before']
    assert not branch['events'] and branch['pcs']==[row['return_pc'],branch['outgoing']['pc']]
    assert continuous['pcs']==boundary['pcs'][:-1]+branch['pcs']
    assert continuous['events']==boundary['events']
    assert boundary['carry']==branch['carry']==continuous['carry']
    assert branch['modeled_bank']==boundary['modeled_bank']==continuous['modeled_bank']


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name)}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];coverage=set();phase_count=0;control_phase_count=0
    def store_phases(index,phases,group):
        rows=[]
        for j,phase in enumerate(phases):
            coverage.update(phase['pcs']);stem='%s_%03d_phase_%02d'%(group,index,j)
            ports=[e for e in phase['events'] if e['region']=='pvc']
            trace={k:phase[k] for k in ('pcs','events','boundaries','guard')}
            payloads={stem+'_ram_before.bin':phase['ram_before'],stem+'_ram_after.bin':phase['ram_after'],
                stem+'_pvc_before.bin':phase['pvc_before'],stem+'_pvc_after.bin':phase['pvc_after'],
                stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
                stem+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
            snapshot=phase['return_snapshot']
            if snapshot:
                payloads[stem+'_return_ram.bin']=snapshot['ram'];payloads[stem+'_return_pvc.bin']=snapshot['pvc']
            for name,data in payloads.items():(OUT/name).write_bytes(data);artifacts[name]=sha(data)
            rows.append(dict(label=phase['label'],incoming=phase['incoming'],outgoing=phase['outgoing'],waiting=phase['waiting'],carry=phase['carry'],
                carry_evidence='subsequent_actual_caller_branch' if phase['label']=='return-boundary' else 'actual_caller_branch' if not phase['waiting'] else None,
                branch_taken=phase.get('branch_taken'),host_changes=phase['host_changes'],modeled_bank=phase['modeled_bank'],
                external_reads=sum(e['region']=='external' for e in phase['events']),return_snapshot_registers=snapshot['registers'] if snapshot else None,
                artifacts={name:sha(data) for name,data in payloads.items()}))
        return rows
    for i,row in enumerate(matrix(program)):
        actual,fx,phases=run_case(program,row);assert (actual,fx,phases)==run_case(program,row)
        other,other_fx,control=run_case(program,row,True);assert (other,other_fx,control)==run_case(program,row,True)
        assert actual==other and fx==other_fx;compare_control(actual,phases,control)
        results.append(dict(index=i,selection=actual,fixture={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')},
            phases=store_phases(i,phases,'case'),continuous_control=store_phases(i,control,'control'),reproduced_twice=True,continuous_split_equivalent=True))
        phase_count+=len(phases);control_phase_count+=len(control)
        print('%d/%d %s %d phases C%d'%(i+1,60,row['label'],len(phases),phases[-1]['carry']),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    assert {phase['carry'] for result in results for phase in result['phases']}=={None,1,2}
    for op in ('BCC','BCS'):
        assert {r['phases'][-1]['carry'] for r in results if r['selection']['branch_opcode']==op}=={1,2}
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,cases=len(results),phases=phase_count,
        continuous_control_phases=control_phase_count,fresh_CPU_runs=len(results)*4,phase_executions=(phase_count+control_phase_count)*2,
        carry_enum=dict(Unobserved=None,Clear=1,Set=2),covered_PCs=sorted(coverage),original_program_modified=False,SR_read_at_any_phase=False,
        register_injection_after_begin=False,Cpp_comparison_performed=False,failure=None,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming state at actual original caller JSR; natural gameplay reachability notclaimed. Initializer group has explicitly declared originalcallerbranch return, notnaturalinitializer caller.',
            'C is observed only from actual BCC/BCS successor. Return-boundary C is tagged retrospectively using subsequent originalbranch; pending phasecarry remainsnull.',
            'Continuous freshCPUcontrol compared against stop/resume sameCPU path including fullRAM/PVC/16R/PC/events. NoSR/context read or registerwrite afterinitialprepare.',
            'Fixedbank2 mapping; guard otherbankROMreads/PVCreads/unsupportedcallee/MMIO/TRAP/timeouts. Nohardware/timing/IRQ/generalCCR proof.',
            'Stops before caller branch successors execute; caller behavior afterbranch is outside scope. Existing tools/resources were imported read-only.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),phases=phase_count,control_phases=control_phase_count,sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
