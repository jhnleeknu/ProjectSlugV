"""Unpatched readiness helper/caller carry via original47d42 branch.

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
import observe_animation_machine_activation as activation
import observe_stage_readiness as readiness
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_readiness_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=activation.RANGES+((0x47d20,0x47d24),(0x47d3e,0x47d46),(0x4847c,0x484b4),(0x1bdde,0x1be3a),(0x289e,0x28ae),(0x4dee2,0x4df1a),(0x4e166,0x4e186))
BOUNDARIES=activation.BOUNDARIES+(0x47d20,0x47d3e,0x47d42,0x4847c,0x4847e,0x48484,0x4848a,0x48490,0x48494,0x4849c,0x484a8,0x484ae,0x1bdde,0x1bdee,0x289e,0x4dee2,0x4def2,0x4e166)
sha,put,replay=extended.sha,extended.put,extended.replay
RETURN_PC,TARGET,FALL=0x47d42,0x47d72,0x47d46


def matrix(program):
    rows=[]
    def add(label,entry=0x47d3e,first=0,second=0,flag=0,mask=0,**extra):
        rows.append(dict(label=label,entry_pc=entry,first=first,second=second,flag=flag,mask=mask,return_pc=RETURN_PC,branch_target=TARGET,branch_fallthrough=FALL,branch_opcode='BCC',**extra))
    for profile in range(14):add('first-'+readiness.PROFILES[profile]['name'],first=profile)
    for profile in range(1,14):add('second-'+readiness.PROFILES[profile]['name'],second=profile)
    for flag in (1,255):
        for mask in range(4):add('flag-%d-mask-%d'%(flag,mask),flag=flag,mask=mask)
    for mask in (1,2,3):add('flag0-mask-%d'%mask,mask=mask)
    add('BRA47d20-early-first',entry=0x47d20,first=7)
    add('BRA47d20-ready',entry=0x47d20,flag=1)
    for a5 in (0x107ffe,0x108002,0x1f8000):add('mirror-shift-%x'%a5,a5=a5,flag=1)
    add('caller-JSRs-overlap-record',a5=S-8-0x5d12,first=3,flag=0,mask=1,record_stack_alias=True)
    add('direct4847c-early-first',entry=0x4847c,first=7)
    add('direct4847c-ready',entry=0x4847c,flag=1)
    for i,profile in enumerate((0,1,2,7,8,9)):add('direct1bdde-'+readiness.PROFILES[profile]['name'],entry=0x1bdde,first=profile,second=profile,d0=0xabcd0000|(i&1))
    for value in (0,0x270e,0xffffffff):add('direct289e-marker-%x'%value,entry=0x289e,marker=value)
    add('direct289e-caller-return-operand',entry=0x289e,a0=S,marker=0x270e,marker_return_alias=True)
    for i,profile in enumerate((3,4,5,7,8,9,11,12)):add('direct4dee2-'+readiness.PROFILES[profile]['name'],entry=0x4dee2,first=profile,second=profile,d0=0xabcd0000|(i&1))
    add('direct1bdde-JSR-overwrites-marker',entry=0x1bdde,a5=S-4+0x7348,d0=0xabcd0000,first=2,second=None,flag=None,mask=None,marker_stack_alias=True)
    selections=activation.matrix(program)
    for flag in (0,1):add('activation-mixed-waits-ready-%d'%flag,entry=0x47cae,flag=flag,mask=0,activation_selection=copy.deepcopy(selections[51]))
    single=copy.deepcopy(selections[44]);single['sprite_wait']=True
    add('activation-single-wrapper-wait',entry=0x47cae,first=7,activation_selection=single)
    assert len(rows)==68
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    base=row.get('activation_selection',activation.matrix(program)[16]);fx=activation.fixture(program,base)
    ram=bytearray(fx['ram']);regs=dict(fx['regs']);regs['a5']=row.get('a5',0x108000)
    writes=[]
    def setup(address,size,value):
        bus=address&0xffffff
        assert 0x100000<=bus and bus+size<=0x200000,('fixture write outside RAM',hex(address),size)
        put(ram,address,size,value);writes.append(dict(address=address,size=size,value=value))
    a5=regs['a5']
    for player,key in enumerate(('first','second')):
        if row[key] is None:continue
        profile=readiness.PROFILES[row[key]];a0=(a5-(0x7258 if player else 0x7348))&0xffffffff;a4=(a5+(0x5d18 if player else 0x5d12))&0xffffffff
        setup(a0,4,profile['marker']);setup(a0+0xa8,1,profile['a8']);setup(a0+0x61,1,profile['flag61'])
        if 0x100000<=a4&0xffffff and (a4&0xffffff)+6<=0x200000:
            setup(a4,1,profile['type']);setup(a4+2,1,profile['status']);setup(a4+4,2,profile['word'])
    if row.get('marker_stack_alias'):setup(a5-0x7348,4,0x270e)
    if row['flag'] is not None:
        setup(a5+0x5684,1,row['flag']);setup(a5-0x75bc,1,2 if row['mask']&1 else 0);setup(a5-0x74f8,1,2 if row['mask']&2 else 255)
    entry=row['entry_pc'];direct=entry in (0x4847c,0x1bdde,0x289e,0x4dee2)
    if 'd0' in row:regs['d0']=row['d0']
    if entry==0x289e:
        regs['a0']=row.get('a0',0x104900);setup(regs['a0'],4,row['marker'])
    initial_return=RETURN_PC if direct else RETURN
    setup(S,4,initial_return)
    return dict(fx,ram=bytes(ram),regs=regs,entry_pc=entry,stop_pc=RETURN_PC,return_pc=RETURN_PC,branch_target=TARGET,branch_fallthrough=FALL,branch_opcode='BCC',
        expected_final_a7=S+4 if direct else S,initial_return=initial_return,
        initial_shared_stack=dict(fx['initial_shared_stack'],return_value=initial_return),readiness_host_writes=writes,
        group='activation-readiness' if row.get('activation_selection') else 'readiness',direct_controlled_branch_adapter=direct,activation_selection=row.get('activation_selection'),
        actual_initial_marker=int.from_bytes(bytes(ram[((a5-0x7348)+i)&65535] for i in range(4)),'big'))


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
    row=copy.deepcopy(row);fx=fixture(program,row);condition=row.get('activation_selection',{});obs=Observer(program,continuous)
    try:
        obs.prepare(fx);phases=[];sound_released=False;seen_animation=False;sprite_waits=0
        def take(label,changes=()):
            obs.mutate(changes);phase=obs.run();phase['label']=label;phase['host_changes']=list(changes);phases.append(phase);return phase
        phase=take('begin')
        if condition.get('sprite_wait') or condition.get('sound_wait'):assert phase['waiting']
        while phase['waiting']:
            assert len(phases)<12,('unexpected repeated wait',row)
            if phase['outgoing']['pc']==0x3aea:
                assert condition.get('sound_wait') and not sound_released
                sp=phase['outgoing']['a7'];high=int.from_bytes(obs.cpu.mem_read(sp,4),'big')==0x3c00
                a6=fx['regs']['a6']
                changes=[dict(address=0x10095c,size=2,value=0x0201),dict(address=a6+0x7e,size=1,value=0xaa),
                         dict(address=a6+0x42,size=2,value=0x110),dict(address=a6+0x46,size=2,value=0x190)]
                if high:changes.append(dict(address=shared.canonical(sp+4),size=1,value=0x77))
                hold=take('sound-hold-live-source-and-prefix-poison',changes)
                assert hold['waiting'] and hold['outgoing']==phase['outgoing'] and hold['ram_before']==hold['ram_after']
                if condition['sound_wait']==3:
                    phase=take('sound-high-to-low',[dict(address=0x104d74,size=2,value=((hold['outgoing']['d1']&65535)+1)&0x7f)])
                    assert phase['waiting'] and phase['outgoing']['pc']==0x3aea
                    hold=take('sound-low-hold');assert hold['waiting'] and hold['outgoing']==phase['outgoing'] and hold['ram_before']==hold['ram_after']
                phase=take('sound-release',[dict(address=0x104d74,size=2,value=0xffff)]);sound_released=True
                assert not any(pc in phase['pcs'] for pc in (0x47cae,0x16ed2,0x47672))
                if high:assert any(e['pc']==0x3c00 and e['access']=='read' and e['bytes']=='77' for p in phases[2:] for e in p['events'])
                continue
            assert phase['outgoing']['pc']==0xcda4 and condition.get('sprite_wait')
            sprite_waits+=1;seen_animation=any(0x49fc6 in p['pcs'] for p in phases)
            kind='animation-sprite' if seen_animation else 'wrapper-sprite'
            a6=phase['outgoing']['a6'];changes=[dict(address=a6+0x42,size=2,value=0x8000),dict(address=a6+0x46,size=2,value=0),
                dict(address=a6+0x53,size=1,value=0xff),dict(address=a6+0x12,size=4,value=0x12345640),dict(address=a6+0x1e,size=2,value=0x8001)]
            if condition.get('live_return'):changes.append(dict(address=shared.canonical(S),size=4,value=fx['stop_pc']))
            if condition.get('mixed_wait') and not seen_animation:changes.append(dict(address=0x108d36,size=2,value=8))
            hold=take(kind+'-hold-object-poison',changes)
            assert hold['waiting'] and hold['outgoing']==phase['outgoing'] and hold['ram_before']==hold['ram_after']
            release_pc=phase['outgoing']['pc'];captured=dict(phase['outgoing'])
            phase=take(kind+'-release',[dict(address=0x108d34,size=2,value=hold['outgoing']['d4']&65535)])
            # The immediate queue-accept boundary uses captured transformed registers;
            # later wrappers/draws may legitimately reread the changed object.
            accepted=next(b for b in phase['boundaries'] if b['pc']==0xcdaa)
            assert accepted['registers']==dict(captured,pc=0xcdaa)

        if row.get('marker_stack_alias'):
            assert fx['ram'][(S-4)&65535:S&65535]==bytes.fromhex('0000270e')
            assert any(e['pc']==0x1bdee and e['access']=='write' and e['address']==S-4 and e['bytes']=='0001bdf4' for e in phases[0]['events'])
            assert any(e['pc']==0x289e and e['access']=='read' and e['address']==S-4 and e['bytes']=='0001bdf4' for e in phases[0]['events'])
        if row.get('record_stack_alias'):
            assert fx['ram'][(S-4)&65535:(S-2)&65535]==bytes.fromhex('8000')
            assert any(e['pc']==0x4def2 and e['access']=='read' and e['address']==S-4 and e['bytes']=='0004' for e in phases[0]['events'])
        final=phases[-1];idx=final['pcs'].index(RETURN_PC)
        assert final['pcs'][idx-1] in (0x484ac,0x484b2,0x1be32,0x1be38,0x28ac,0x4df0e,0x4df18)
        assert final['return_snapshot']['registers']['a7']==fx['expected_final_a7']
        if condition.get('mixed_wait'):assert sprite_waits==2 and sound_released
        if not continuous:
            final['label']='return-boundary';obs.branch_only=True;branch=take('branch-result')
        else:branch=final;final['label']='continuous-branch-result'
        assert branch['outgoing']['pc'] in (TARGET,FALL)
        carry=1 if branch['outgoing']['pc']==TARGET else 2
        for phase in phases:phase['carry']=None if phase['waiting'] else carry
        branch['branch_taken']=branch['outgoing']['pc']==TARGET
        return row,fx,phases
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
    input_paths.update(activation.physical_inputs(program,source))
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
        print('%d/%d %s %d phases C%d'%(i+1,68,row['label'],len(phases),phases[-1]['carry']),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    assert {phase['carry'] for result in results for phase in result['phases']}=={None,1,2}
    for op in ('BCC',):
        assert {r['phases'][-1]['carry'] for r in results if r['selection']['branch_opcode']==op}=={1,2}
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,cases=len(results),phases=phase_count,
        continuous_control_phases=control_phase_count,fresh_CPU_runs=len(results)*4,phase_executions=(phase_count+control_phase_count)*2,
        carry_enum=dict(Unobserved=None,Clear=1,Set=2),covered_PCs=sorted(coverage),original_program_modified=False,SR_read_at_any_phase=False,
        register_injection_after_begin=False,Cpp_comparison_performed=False,failure=None,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled original47d3e/47d20 callers and selected47cae activation chains; naturalgameplay/scheduler reachability notclaimed.',
            'Standalone4847c/1bdde/289e/4dee2 use freshcallerreturnLONG47d42 as declaredcontrolledadapter; actualbranch direction suppliesC, not hostSR or C++expected.',
            'Split return-boundary followed byactual47d42BCC compared against separatefreshcontinuousCPU. Ctagsatboundary derive retrospectivelyfromactualbranch; waits remainnull.',
            'All16RAMmirrors/coherentCPU-ownedbacking/sharedA7/fullRAMandPVC/events retained withoutstackmask; onlydeclaredRAMhostmutations duringwaits.',
            'Originalmapping equals8actualkind3payloads; RAM/PVCdevice overlayswin; bankROMreads onlydeclaredbank2. Otherbank/PVCread/unsupportedcallee/MMIO/TRAP/timeout guarded.',
            '4e166mask0..3 reachedinside4847c only; rawstandalone4e166carry notclaimed. No otherCCR/hardware/timing/IRQ/postbranch behavior proof.',
            'Priorlegacyreadinessfixture profiles are inputtemplates only; its SRreadingobserver neverexecutes. Actualstackaliases may change declared profilevalues; live reads andwrites are retained.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),phases=phase_count,control_phases=control_phase_count,sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
