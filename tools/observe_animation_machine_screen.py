"""Unpatched screen reset and exit continuation on coherent shared RAM stack.

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
import observe_animation_machine_exit as exit_native
import observe_animation_machine_transition as transition
import observe_animation_machine_callers as callers
import observe_animation_machine_activation as activation
import observe_stage_readiness as readiness
import observe_stage_hud_counter as hud
import observe_animation_machine_hud as hud_machine
import observe_animation_machine_readiness as readiness_machine
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_screen_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=exit_native.RANGES+((0xca9e,0xcb64),(0x47fca,0x47fe8))
BOUNDARIES=exit_native.BOUNDARIES+(0xca9e,0xcabc,0xcaee,0xcaf0,0xcaf2,0xcb08,0xcb0e,0xcb1c,0xcb22,0xcb30,0xcb36,0xcb44,0xcb4a,0xcb58,0xcb5e,0xcb62,0x47fca,0x47fd0,0x47fdc,0x47fe4)
sha,put=extended.sha,extended.put
BRANCHES=exit_native.BRANCHES

class Observer:
    def __init__(self,program,continuous=False):self.program=program;self.cpu=None;self.backing=None;self.continuous=continuous;self.seen=set()
    def regs(self):return {key:self.cpu.reg_read(REGS[key]) for key in shared.isolated.REG_NAMES+('a7','pc')}
    def prepare(self,fx):
        self.stop_pc=fx['stop_pc'];self.checkpoints=tuple(fx['checkpoints']);self.expected_a7=fx['expected_final_a7']
        self.backing=(ctypes.c_ubyte*SIZE).from_buffer_copy(fx['ram'])
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c._ram_backing=self.backing
        c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        c.mem_map(0,RAM,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(0,self.program[:RAM])
        for i in range(16):c.mem_map_ptr(RAM+i*SIZE,SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        c.mem_map(0x200000,0xfe000,unicorn.UC_PROT_READ);c.mem_write(0x200000,self.program[0x200000:0x2fe000])
        c.mem_map(PVC,8192,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(PVC,fx['pvc'])
        c.mem_map(0x300000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0x3c0000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        c.mem_map(0xd00000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(EXTERNAL,bytes([fx['external']]))
        self.cpu=c;self.bank=0x200000;self.ff8=0xa0;self.ff9=0x1000
        self.boundary_set=set(BOUNDARIES)
        allowed=set()
        for lo,hi in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(self.program,lo,hi-lo,lo))
        def stop(problem,**fields):self.guard=dict(problem=problem,pc=self.pc,**fields);c.emu_stop()
        def code(cpu,pc,size,user):
            self.pc=pc;self.pcs.append(pc)
            if pc==self.stop_pc:cpu.emu_stop();return
            if pc in self.checkpoints and pc not in self.seen:
                self.seen.add(pc)
                self.snapshots.append(dict(registers=self.regs(),ram=bytes(self.backing),pvc=bytes(c.mem_read(PVC,8192))))
                if not self.continuous:cpu.emu_stop();return
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
            elif (address==0x3c0000 and size in (2,4) or address==0x3c0004 and size==2) and kind=='write':region='video'
            elif address==0x300001 and size==1 and kind=='write':region='watchdog'
            else:stop('unsupported_data_device',address=address,size=size);return
            if kind=='write' and region not in ('ram','pvc','video','watchdog'):stop('unsupported_write',address=address,size=size);return
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
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0;self.snapshots=[]
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        try:self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
        except unicorn.UcError:
            if not allow_guard or self.guard is None:raise
        outgoing=self.regs()
        if not allow_guard:assert self.guard is None,self.guard
        if self.guard is None:assert outgoing['pc']==self.stop_pc or outgoing['pc'] in self.checkpoints or outgoing['pc'] in (0xcda4,0x3aea) and self.visits==2,('timeout_or_stop',outgoing)
        if outgoing['pc']==self.stop_pc:assert outgoing['a7']==self.expected_a7,(outgoing,self.expected_a7)
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=self.guard is None and outgoing['pc'] in (0xcda4,0x3aea),snapshots=self.snapshots,guard=self.guard,modeled_bank=self.bank,
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



def matrix(program):
    rows=[]
    def add(group,label,entry,**extra):rows.append(dict(group=group,label=label,entry_pc=entry,**extra))
    for a5 in (0x108000,0x1f8000,0,0xffffffff):add('reset','ca9e-A5-%08x'%a5,0xca9e,a5=a5,profile=len(rows))
    for a5 in (0x108000,0x1f8000,0x108001,0x10769a,0x207699):add('screen','caf0-A5-%08x'%a5,0xcaf0,a5=a5,profile=len(rows))
    for d7 in (0,1,0xffff):add('loop','cab0-D7-%04x-video'%d7,0xcab0,d7=d7,a4=0x3c0000,profile=len(rows))
    for d7 in (0,1):add('loop','cab0-D7-%04x-RAM'%d7,0xcab0,d7=d7,a4=0x104900,profile=len(rows))
    add('loop','cab0-D7-0001-shared-stack',0xcab0,d7=1,a4=S-4,profile=14)
    for a6 in (0x102000,0x1f2000):add('caller','caller47fca-%x'%a6,0x47fca,a6=a6)
    for timer in (0,1,2,0xffff):add('timer','timer47fdc-%04x'%timer,0x47fdc,timer=timer)
    for a6 in (0x102000,0x1f2000):add('late','fresh47fa8-screen-%x'%a6,0x47fa8,timer=1,a6=a6)
    for wait in (0,3,4):add('pipeline','pipeline-separate-wait%d'%wait,0x47f4a,sound_wait=wait,**({'saved_long':0x87658001} if wait==4 else {}))
    add('screen','caf0-nested-return-stack-mirror',0xcaf0,a5=0x108000,initial_a7=0x10effc,profile=25)
    add('reset','ca9e-live-return-untouched',0xca9e,a5=0x12345678,initial_a7=0x104900,profile=26)
    add('screen','caf0-clear-alias-outer-return',0xcaf0,a5=S+1+0x769a,initial_return=0xff000,stop=0xf000,profile=27)
    add('screen','caf0-clear-bank-guard',0xcaf0,a5=0x20769a,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0xcb5e,guard_address=0x200000)
    add('loop','cab0-live-return-overwritten-guard',0xcab0,d7=1,a4=S,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0xcaee,guard_address=0x7580ff02)
    add('caller','caller47fd0-timer-before-fixed-write-guard',0x47fd0,a6=0x0ffffe,guarded=True,guard_problem='unmapped_or_protected',guard_pc=0x47fd6,guard_address=0x0ffffe)
    for d7 in (0,1):add('loop','cab8-D7-%04x-directDBRA'%d7,0xcab8,d7=d7,a4=0x3c0000,profile=28+d7)
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    if row['group']=='pipeline':return exit_native.fixture(program,row)
    base=exit_native.fixture(program,dict(group='players',label='screen-base',entry_pc=0x1c63c,first=0x270e,second=0x270e))
    ram=bytearray(base['ram']);regs=dict(base['regs']);writes=list(base['initial_host_writes']);sp=row.get('initial_a7',S)
    def setup(at,size,value):
        assert RAM<=at and at+size<=0x200000,('fixture_nonRAM',hex(at),size)
        value&=(1<<(size*8))-1;put(ram,at,size,value);writes.append(dict(address=at,size=size,value=value))
    for key in shared.isolated.REG_NAMES:
        if key not in ('a5','a6'):regs[key]=(regs[key]+row.get('profile',0)*0x01020304)&0xffffffff
    regs['a5']=row.get('a5',0x108000);regs['a6']=row.get('a6',0x102000)
    entry=row['entry_pc'];group=row['group'];stop=row.get('stop',RETURN);checkpoints=[];direct=group in ('reset','screen','loop')
    if group=='screen':checkpoints=[0xcaf2,0xcb0e,0xcb22,0xcb36,0xcb4a,0xcb5e]
    elif group=='loop':regs.update(a4=row['a4'],d7=0xabcd0000|row['d7']);checkpoints=[0xcabc]
    elif group=='caller':stop=0x480bc;checkpoints=[0x47fd0,0x47fdc]
    elif group=='timer':
        setup(regs['a6']+0x7a,2,row['timer']);stop=0x47fe4 if row['timer']==1 else 0x480bc
    elif group=='late':
        setup(regs['a6']+0x7a,2,1);stop=0x480bc;checkpoints=[0x47fbe,0x47fc4,0x47fca,0x47fd0,0x47fdc]
    if entry==0x47fd0:checkpoints=[]
    ret=row.get('initial_return',RETURN);setup(sp,4,ret)
    return dict(base,ram=bytes(ram),regs=regs,initial_a7=sp,entry_pc=entry,stop_pc=stop,expected_final_a7=sp+4 if direct else sp,checkpoints=checkpoints,initial_host_writes=writes,group=group,return_pc=ret,initial_shared_stack=dict(base['initial_shared_stack'],return_address=sp,return_value=ret))

replay=transition.replay
flattened=transition.flattened
def compare_control(row,split,control):
    assert flattened(split)==flattened(control)
    for key in ('outgoing','ram_after','pvc_after','guard','branch_evidence'):assert split[-1][key]==control[-1][key]
    checkpoints={p['outgoing']['pc']:(p['outgoing'],p['ram_after'],p['pvc_after']) for p in split[:-1] if not p['waiting'] and p['guard'] is None}
    seen=set()
    for phase in control:
        for snapshot in phase['snapshots']:
            regs=snapshot['registers'];assert checkpoints[regs['pc']]==(regs,snapshot['ram'],snapshot['pvc']);seen.add(regs['pc'])
    assert seen==set(checkpoints)


def run_case(program,row,continuous=False):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program,continuous);phases=[]
    try:
        obs.prepare(fx)
        def take(label,changes=()):
            obs.mutate(changes);remaining=[pc for pc in fx['checkpoints'] if pc not in obs.seen]
            target=fx['stop_pc'] if continuous or not remaining else remaining[0]
            p=obs.run(allow_guard=row.get('guarded',False))
            if p['guard'] is None and not p['waiting']:assert p['outgoing']['pc']==target,(row,p['outgoing'],hex(target))
            p.update(label=label,host_changes=list(changes),stop_pc=target,carry=None);phases.append(p);return p
        p=take('begin');sound_waits=sprite_waits=0
        while p['guard'] is None and p['outgoing']['pc']!=fx['stop_pc']:
            if p['waiting']:
                before=p;changes=[]
                if p['outgoing']['pc']==0xcda4:
                    sprite_waits+=1;assert sprite_waits<=1
                    a6=fx['regs']['a6'];changes=[dict(address=a6+0x53,size=1,value=0x77),dict(address=a6+0x42,size=2,value=0x8000),dict(address=a6+0x46,size=2,value=0)]
                    p=take('sprite-hold-current-prefix-poison',changes)
                    assert p['waiting'] and p['outgoing']==before['outgoing'] and p['ram_before']==p['ram_after']
                    p=take('sprite-ready',[dict(address=0x108d34,size=2,value=p['outgoing']['d4']&65535)])
                else:
                    sound_waits+=1;assert sound_waits<=6,(row,sound_waits)
                    high=int.from_bytes(obs.cpu.mem_read(p['outgoing']['a7'],4),'big')==0x3c00
                    if high:changes.append(dict(address=p['outgoing']['a7']+4,size=1,value=0x77))
                    if row.get('saved_long') is not None and sound_waits==1:
                        assert any(0x47f74 in q['pcs'] for q in phases)
                        changes.append(dict(address=fx['initial_a7']-4,size=4,value=row['saved_long']))
                    p=take('sound-hold%d-live-stack'%sound_waits,changes)
                    assert p['waiting'] and p['outgoing']==before['outgoing'] and p['ram_before']==p['ram_after']
                    head=((p['outgoing']['d1']&65535)+1)&0x7f if row.get('sound_wait')==3 and sound_waits==1 else 0xffff
                    p=take('sound-ready%d'%sound_waits,[dict(address=0x104d74,size=2,value=head)])
            else:p=take('after-checkpoint-%x'%p['outgoing']['pc'])
        pcs,events,_=flattened(phases);known={}
        for pc,nxt in zip(pcs,pcs[1:]):
            if pc in BRANCHES:
                assert nxt in BRANCHES[pc];assert pc not in known
                known[pc]=dict(successor=nxt,carry=1 if nxt==BRANCHES[pc][0] else 2)
        for q in phases:
            if q['outgoing']['pc'] in known:q['carry']=known[q['outgoing']['pc']]['carry']
            q['branch_evidence']=known
        if row.get('guarded'):
            assert p['guard']['problem']==row['guard_problem'] and p['guard']['pc']==row['guard_pc'],(row,p['guard'])
            if 'guard_address' in row:assert p['guard']['address']==row['guard_address']
        if row.get('saved_long') is not None:
            assert sound_waits>=1
            assert any(e['pc']==0x47f82 and e['access']=='read' and e['address']==fx['initial_a7']-4 and e['bytes']=='%08x'%row['saved_long'] for e in events)
            restored=next(b['registers']['d0'] for q in phases for b in q['boundaries'] if b['pc']==0x47f86)
            assert restored==row['saved_long']
        if row.get('marker_alias'):
            assert any(e['pc']==0x1c642 and e['access']=='write' and e['address']==0x100cb8 and e['bytes']=='0001c648' for e in events)
            assert known[0x1c648]['carry']==2
        if row['group']=='reset':assert sum(e['region']=='video' for e in events)==773
        if row['group']=='screen' and not row.get('guarded'):
            assert all(pc in pcs for pc in (0xcb08,0xcb1c,0xcb30,0xcb44,0xcb58))
            assert sum(e['region'] in ('video','watchdog') for e in events)==2072
            assert sum(e['region']=='watchdog' for e in events)==5
        if row['group']=='loop':assert sum(pc==0xcab0 for pc in pcs)==row['d7']+(1 if row['entry_pc']==0xcab0 else 0)
        if row.get('sound_wait'):assert sound_waits>0
        return row,fx,phases
    finally:obs.close()

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
    artifacts={};results=[];guards=[];coverage=set();split_count=control_count=0
    def store(index,phases,group):
        rows=[]
        for j,p in enumerate(phases):
            coverage.update(p['pcs']);stem='%s_%03d_phase_%02d'%(group,index,j)
            events=p['events'];ports=[e for e in events if e['region'] in ('pvc','video','watchdog')]
            payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
                stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
                stem+'_trace.json':(json.dumps({k:p[k] for k in ('pcs','events','boundaries','guard')},indent=2)+'\n').encode()}
            snapshots=[]
            for k,snapshot in enumerate(p['snapshots']):
                names={}
                for field in ('ram','pvc'):
                    name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
                snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
            for name,data in payloads.items():(OUT/name).write_bytes(data);artifacts[name]=sha(data)
            rows.append(dict(label=p['label'],stop_pc=p['stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],waiting=p['waiting'],carry=p['carry'],branch_evidence=p['branch_evidence'],host_changes=p['host_changes'],modeled_bank=p['modeled_bank'],guard=p['guard'],snapshots=snapshots,
                external_reads=sum(e['region']=='external' for e in events),artifacts={name:sha(data) for name,data in payloads.items()}))
        return rows
    selections=matrix(program)
    for i,row in enumerate(selections):
        actual,fx,split=run_case(program,row);assert (actual,fx,split)==run_case(program,row)
        other,other_fx,control=run_case(program,row,True);assert (other,other_fx,control)==run_case(program,row,True)
        assert actual==other and fx==other_fx;compare_control(actual,split,control)
        result=dict(index=i,selection=actual,fixture={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')},phases=store(i,split,'case'),continuous_control=store(i,control,'control'),reproduced_twice=True,continuous_split_equivalent=True)
        (guards if row.get('guarded') else results).append(result)
        split_count+=len(split);control_count+=len(control)
        print('%d/%d %s %d phases%s'%(i+1,len(selections),row['label'],len(split),' guarded' if row.get('guarded') else ''),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,raw_lookup_30ec=dict(cpu_start=0x30ec,end_exclusive=0x30f4,sha256=sha(program[0x30ec:0x30f4]),raw=program[0x30ec:0x30f4].hex())),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),phases=sum(len(r['phases']) for r in results),continuous_control_phases=sum(len(r['continuous_control']) for r in results),
        total_split_phases=split_count,total_control_phases=control_count,fresh_CPU_runs=len(selections)*4,phase_executions=(split_count+control_count)*2,covered_PCs=sorted(coverage),failure=None,
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled original screen/exit continuation fixtures, not natural scheduler reachability or whole game completion.',
            'No SR/context reads after init. Known C only from executed original1c648/1c664 BCC successors; other endpoints unobserved.',
            'Coherent16RAMmirrors, CPU-owned backing, actual callerA7/JSR/BSR/RTS and LONG/WORD/BYTE live stack without stack masking.',
            'Freshcontinuous controls execute identical immutableprogram through checkpoints; waits resume sameCPU with declared RAM hostchanges only.',
            'Actualkind3bytes equalcanonicalROM; nativebankmappingbank2only; unsupported devices/PVCreads/targets/TRAP guarded.',
            'Fresh47fa8 latecallback inputs are separate from47f4a pipeline output; no host PC reset or natural frame/scheduler claim.',
            '47fca actualJSRcaf0 executes. 47fe4 BSR477c2 and480bc bodies stop BEFORE execution.',
            'No generic CCR, IRQ/timing, complete watchdog/video/VRAM model or original CPU fault rollback equivalence.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),phases=report['phases'],control=report['continuous_control_phases'],sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
