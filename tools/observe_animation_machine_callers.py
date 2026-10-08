"""Unpatched animation initializer and actual upper-stage caller observations.

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
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_callers_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=extended.RANGES+((0x49f8c,0x49fc6),(0x47cec,0x47d20),(0x47f04,0x47f0a))
BOUNDARIES=extended.BOUNDARIES+(0x49f8c,0x49fac,0x49fb6,0x49fb8,0x49fc4,0x47cec,0x47d14,0x47d1a,0x47f04,0x4a2e2)
sha=extended.sha
put=extended.put
replay=extended.replay


def matrix(program):
    original=extended.matrix(program);base=copy.deepcopy(original[2]);rows=[]
    def add(label,entry,selection,**extra):
        rows.append(dict(label=label,entry_pc=entry,stop_pc=RETURN if entry==0x49f8c else 0x47d20 if entry==0x47cec else 0x47f0a,
                         selection=copy.deepcopy(selection),**extra))
    for pointer in (0,0x48980,0x489c2,0x106000):
        for speed in (0,0x100,0xffff):add('initializer-pointer-%x-speed-%04x'%(pointer,speed),0x49f8c,base,pointer=pointer,speed=speed)
    add('initializer-opaque-A1',0x49f8c,base,pointer=0xffffffff,speed=0x100)
    for a6 in (0x10ffd4,0x1fffd2):add('initializer-RAM-mirror-boundary-%x'%a6,0x49f8c,base,pointer=0x48980,speed=0x100,a6=a6)
    add('initializer-shadow-alias',0x49f8c,base,pointer=0x489c2,speed=0xffff,a6=0x0fffea)
    add('initializer-overwrites-return-with-A1',0x49f8c,base,pointer=RETURN,speed=0x100,a6=S-0x26,initial_return=0x12345678)
    add('initializer-overwrites-return-with-timer-speed',0x49f8c,base,pointer=0xffffffff,speed=0x8000,a6=S-0x2a,initial_return=0xdeadbeef)
    rows[-1]['stop_pc']=0x8000
    for selection in original:
        source,c=selection['source'],selection['case']
        if source=='direct' and c['script']==0x489c2 and (c['family']=='actual-flash-draw-skip' or c['family'].startswith('queue-') and c['queue'] in ('normal','deferred','full') or selection['chain']=='sprite'):
            add('raw47cec-'+c['family']+'-'+c['queue'],0x47cec,selection)
    for selection in original:
        source,c=selection['source'],selection['case'];selected=False
        if source=='direct':selected=(c['family'].startswith('queue-') and (c['script']==0x48980 or c['queue'] in ('normal','deferred'))) or selection['chain']=='sprite'
        elif source=='indexed':selected=c['family'] in ('draw-normal','draw-full') or selection['chain']=='indexed-sprite'
        elif source=='sound':selected=c['wait']>0 or c['sound'] and c['wait']==0 and c['mode']==0
        elif source=='word':selected=c['family'] in ('first-selector-modular-alias','3c-03-actual-RTS') or c['wait']==3
        elif source=='field':
            op=c['opcode'];selected=(c['selector']==0 and c['value'] in (0x80,0x8001,0x81234567) and op in (0x18,0x1c,0x20,0x24)) or op in (0x34,0x38) and c['value']==0 or op==0x2c and c['length']==8 and c['relative']==0
        elif source=='control':selected=c['opcode']==0x0c and c['selector']==0 and c['desired']==0
        elif source=='direct_sound':selected=c['commands']==[0x2000] or c['chain']=='high_to_low'
        if selected:add('47f04-'+source+'-'+c.get('family','sound'),0x47f04,selection)
    add('47f04-null-script',0x47f04,base,null_script=True)
    return rows


def guard_cases(program):
    base=matrix(program)[0]['selection']
    return [dict(label='bad-A5-%x-entry-%x'%(a5,entry),entry_pc=entry,stop_pc=RETURN if entry==0x49f8c else 0x47d20,
                 selection=copy.deepcopy(base),pointer=0x48980,speed=0x100,a5=a5,expected_guard=True)
            for entry in (0x49f8c,0x47cec) for a5 in (0x108002,0x118000)]


def cases(program):return matrix(program)


def fixture(program,row):
    fx=extended.fixture(program,row['selection']);ram=bytearray(fx['ram']);regs=dict(fx['regs']);overrides=[]
    for name in ('a5','a6'):
        if name in row:regs[name]=row[name];overrides.append(dict(register=name,value=row[name]))
    if row['entry_pc']==0x49f8c:
        regs['a1']=row['pointer'];regs['d0']=(regs['d0']&0xffff0000)|row['speed']
        overrides += [dict(register='a1',value=regs['a1']),dict(register='d0',value=regs['d0'])]
        if row['pointer']==0x106000:ram[0x6000:0x6002]=b'\0\0'
    elif row['entry_pc']==0x47cec:
        regs['a1']=0xffffffff;regs['d0']=0x8123ffff
        overrides += [dict(register='a1',value=regs['a1']),dict(register='d0',value=regs['d0'])]
    if row.get('null_script'):put(ram,regs['a6']+0x26,4,0)
    if 'initial_return' in row:put(ram,S,4,row['initial_return'])
    fx['initial_shared_stack']=dict(fx['initial_shared_stack'],return_value=int.from_bytes(bytes(ram[(S+i)&65535] for i in range(4)),'big'))
    return dict(fx,ram=bytes(ram),regs=regs,entry_pc=row['entry_pc'],stop_pc=row['stop_pc'],initial_a7=S,
                expected_final_a7=S+4 if row['entry_pc']==0x49f8c else S,initial_register_overrides=overrides,
                actual_fixed_script_override=0x489c2 if row['entry_pc']==0x47cec else None,
                initial_return=int.from_bytes(bytes(ram[(S+i)&65535] for i in range(4)),'big'),
                initializer_only=row['entry_pc']==0x49f8c)


class Observer:
    def __init__(self,program):self.program=program;self.cpu=None;self.backing=None
    def regs(self):return {key:self.cpu.reg_read(REGS[key]) for key in shared.isolated.REG_NAMES+('a7','pc')}
    def prepare(self,fx):
        self.stop_pc=fx['stop_pc'];self.expected_a7=fx['expected_final_a7']
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
            if pc==self.stop_pc:cpu.emu_stop();return
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
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
        outgoing=self.regs()
        if not allow_guard:assert self.guard is None,self.guard
        if self.guard is None:assert outgoing['pc']==self.stop_pc or outgoing['pc'] in (0xcda4,0x3aea) and self.visits==2,('timeout_or_stop',outgoing)
        if outgoing['pc']==self.stop_pc:assert outgoing['a7']==self.expected_a7
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=self.guard is None and outgoing['pc']!=self.stop_pc,guard=self.guard,modeled_bank=self.bank,
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



def run_case(program,row):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program)
    try:
        obs.prepare(fx);phases=[]
        def take(label,changes=()):
            obs.mutate(changes);phase=obs.run(row.get('expected_guard',False));phase['label']=label;phase['host_changes']=list(changes);phases.append(phase);return phase
        begin=take('begin')
        if row.get('expected_guard'):
            assert begin['guard']['problem']=='unsupported_TRAP' and begin['outgoing']['pc']==0x49fb6
            assert 0x49fac in begin['pcs'] and 0x49fb8 not in begin['pcs']
            return row,fx,phases
        if row['entry_pc']==0x49f8c:
            assert begin['pcs'][-2]==0x49fc4 and not begin['waiting']
            return row,fx,phases
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
        assert phases[-1]['pcs'][-2]==0x4a0e2 or row.get('null_script') and phases[-1]['pcs'][-2]==0x49fea
        return row,fx,phases
    finally:obs.close()


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name)}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            p=Path(name).resolve()
            if p.suffix=='.py' and (ROOT/'tools' in p.parents or 'unicorn' in str(p)):input_paths.add(p)
    pin=shared.isolated.pinned_reference(ROOT)
    input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(p):sha(p.read_bytes()) for p in sorted(input_paths)}
    artifacts={};groups=[];coverage=set();phase_count=0
    for group_name,selections in (('results',matrix(program)),('guarded_results',guard_cases(program))):
        rows=[]
        for i,row in enumerate(selections):
            actual,fx,phases=run_case(program,row);assert (actual,fx,phases)==run_case(program,row)
            phase_rows=[]
            for j,phase in enumerate(phases):
                coverage.update(phase['pcs']);stem=('%s_%03d_phase_%02d'%('case' if group_name=='results' else 'guard',i,j))
                ports=[e for e in phase['events'] if e['region']=='pvc'];trace={k:phase[k] for k in ('pcs','events','boundaries','guard')}
                payloads={stem+'_ram_before.bin':phase['ram_before'],stem+'_ram_after.bin':phase['ram_after'],stem+'_pvc_before.bin':phase['pvc_before'],stem+'_pvc_after.bin':phase['pvc_after'],
                          stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),stem+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
                for name,data in payloads.items():(OUT/name).write_bytes(data);artifacts[name]=sha(data)
                phase_rows.append(dict(label=phase['label'],incoming=phase['incoming'],outgoing=phase['outgoing'],waiting=phase['waiting'],host_changes=phase['host_changes'],modeled_bank=phase['modeled_bank'],
                    external_reads=sum(e['region']=='external' for e in phase['events']),guard=phase['guard'],artifacts={name:sha(data) for name,data in payloads.items()}))
            rows.append(dict(index=i,selection=actual,fixture={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')},phases=phase_rows,reproduced_twice=True))
            if group_name=='results':phase_count+=len(phases)
            print(group_name,i+1,len(selections),row['label'],len(phases),flush=True)
        groups.append(rows)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions),indent=2)+'\n').encode();(OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,cases=len(groups[0]),phases=phase_count,guard_cases=len(groups[1]),fresh_CPU_runs=(len(groups[0])+len(groups[1]))*2,
                results=groups[0],guarded_results=groups[1],covered_PCs=sorted(coverage),oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
                original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,failure=None,
                limitations=['Controlled incoming fixtures, including actualfixed48980/489c2 vs syntheticRAMscripts. Naturalcallerreachability notclaimed.',
                    '47cec originalsetup executes throughactual49f8c and49fc6, stopsbefore47d20BRA;47f04 stopsbefore47f0aTST. InitializerstopsafteractualRTS atdeclaredcallerPC.',
                    '16coherentRAMmirrors/actualA7/sharedRAMreturnslots;wholeRAM/PVC/eventsretained withoutstackmask. Explicitfreshregisterinputs only.',
                    'Fixedbank2 mapping;actualPVCwrites independentlyfolded. NoPVCreads,otherbankROMreads,CCR/hardware/timing/IRQ proof.',
                    'BadA5 conditions stopbeforeoriginalTRAP afterobservedcomparison/partialwrites;notnativeexceptionexecution orC++faultrollbackequivalence.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],phases=phase_count,guards=len(groups[1]),sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
