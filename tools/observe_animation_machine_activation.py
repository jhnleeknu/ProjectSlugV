"""Unpatched activation output chain and standalone object helpers.

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
import observe_object_sprite_wrapper as wrapper
import pack_physical_program as physical
import observe_animation_machine_extended as extended
import observe_animation_shared_stack as shared
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_activation_native'
RAM,SIZE,PVC,S,RETURN=extended.RAM,extended.SIZE,extended.PVC,extended.S,extended.RETURN
REGS,EXTERNAL,CAP=extended.REGS,extended.EXTERNAL,extended.CAP
RANGES=callers.RANGES+((0x16ea4,0x16ef0),(0x47cae,0x47cec))
BOUNDARIES=callers.BOUNDARIES+(0x16ea4,0x16eac,0x16ed2,0x16ede,0x16ee8,0x16eee,0x47cae,0x47cc0,0x47cc6,0x47cca,0x47cd2,0x47ce0,0x47ce6,0x47cec)
sha,put,replay=extended.sha,extended.put,extended.replay


def matrix(program):
    rows=[]
    def add(group,label,**extra):rows.append(dict(group=group,label=label,**extra))
    for flag in (0,1,2,3,0x7c,0x81,0xfe,0xff):
        for profile in (0,1):add('sprite','flag-%02x-wrap-%d'%(flag,profile),flag=flag,profile=profile)
    for queue in ('normal','deferred','clip','full'):add('sprite','queue-'+queue,flag=3,profile=2,queue=queue)
    for deferred in (False,True):add('sprite','wait-poison-'+str(deferred),flag=3,profile=2,queue='deferred' if deferred else 'normal',sprite_wait=True)
    for a6 in (0x1f2000,0x1fffac):add('sprite','mirror-%x'%a6,flag=0x81,profile=2,a6=a6)
    add('sprite','wait-live-RTS',flag=0,profile=2,sprite_wait=True,live_return=True)
    for left,right in ((0x8000,0x7fff),(0x7fff,0x8000),(0,0),(0,1),(0xffff,0),(0,0xffff)):
        add('signed','signed-%04x-%04x'%(left,right),left=left,right=right)
    add('signed','mirrored-operands',left=0x8000,right=1,a5=0x1f8000,a6=0x1f2001)
    for which in ('left-high','right-low'):add('signed','flag-alias-'+which,left=0x8000,right=0x7fff,alias=which)
    for less in (False,True):add('signed','live-return-'+str(less),left=0 if less else 1,right=1 if less else 0,live_return=True)
    for i,source in enumerate((0x0000,0x0101,0x0203,0x0340,0x7fbf,0x80ff,0xfe01,0xff00)):
        add('chain','raw-source-%04x'%source,source_word=source,queue='normal',signed_less=bool(i&1))
    for queue in ('normal','deferred','full','flash'):add('chain','queue-'+queue,source_word=0x0101,queue=queue,signed_less=True)
    for wait in (1,2,3):add('chain','sound-wait-%d'%wait,source_word=0x0101,queue='normal',signed_less=True,sound_wait=wait)
    add('chain','sound-sprite-animation-waits',source_word=0x0101,queue='normal',signed_less=True,sound_wait=3,sprite_wait=True,mixed_wait=True)
    assert len(rows)==52
    return rows


def cases(program):return matrix(program)


def fixture(program,row):
    # Fixture only: import original prior input constructor, never its expected-prefix function.
    queue=row.get('queue','normal');profile=row.get('profile',2)
    case=dict(wrapper.cases()[0],a5=0xffffffff,a6=(row.get('a6',0x102000)&65535)|RAM,flag=row.get('flag',0),
        x=0xffff if profile==0 else 0x7fff if profile==1 else 0,y=0xffff if profile==0 else 0x8000 if profile==1 else 0x40,
        x_offset=1 if profile==0 else 0x8000 if profile==1 else 0,y_offset=0xffff if profile==0 else 1 if profile==1 else 0,
        consumer=2 if queue=='full' or row.get('sprite_wait') else 0x100,prepared=2 if queue=='full' else 4 if row.get('mixed_wait') else 0x80,
        producer=0,normal=0,count=0,offset=12,deferred=queue=='deferred')
    if profile==2 and row.get('flag')==3:case['x']=1;case['y']=0x41
    if queue=='clip':case['x']=0x2a1
    case['pending']=bool(row.get('sprite_wait'))
    ram,regs=wrapper.fixture(case,profile);ram=bytearray(ram)
    regs['a6']=row.get('a6',0x102000)
    group=row['group'];stop=RETURN;entry=0x16ea4;expected_sp=S+4
    writes=[]
    def setup(address,size,value):put(ram,address,size,value);writes.append(dict(address=address,size=size,value=value))
    if group=='signed':
        entry=0x16ed2;regs['a5']=row.get('a5',0x108000);regs['a6']=row.get('a6',0x102001)
        if row.get('alias'):regs['a6']=regs['a5']+(0xd3e if row['alias']=='left-high' else 0xd47)-0x15
        if row.get('live_return'):regs['a6']=S+3-0x15;stop=RETURN+4 if row['left']<row['right'] else RETURN
        setup(regs['a5']+0xd3e,2,row['left']);setup(regs['a5']+0xd46,2,row['right'])
        if not row.get('alias') and not row.get('live_return'):setup(regs['a6']+0x15,1,0xa5)
    elif group=='chain':
        entry=0x47cae;stop=0x47d20;expected_sp=S;regs['a5']=0x108000;regs['d0']=0x8123ffff
        # All sound queue gates are explicit incoming setup; actual callees remain unpatched.
        for address,size,value in ((0x100012,1,0),(0x104d7e,1,0),(0x10f001,1,0),(0x104d8a,2,0),(0x104d8c,2,0),
            (0x104d74,2,0),(0x104d76,2,0),(0x10fd82,1,0),(0x10fe80,1,0),(0x10fd8d,1,1),
            (0x108d3e,2,0x8000 if row['signed_less'] else 0x7fff),(0x108d46,2,0x7fff if row['signed_less'] else 0x8000),
            (regs['a6']+0x15,1,0x40 if queue=='deferred' else 0),(regs['a6']+0x53,1,3),(regs['a6']+0x61,1,8 if queue=='flash' else 0),
            (0x10000f,1,1 if queue=='flash' else 0)):
            setup(address,size,value)
        setup(0x10095c,2,row['source_word']);setup(regs['a6']+0x7e,1,(row['source_word']>>8)^(1 if row.get('sound_wait') else 0))
        if row.get('sound_wait'):
            for address,value in ((0x104d8a,0),(0x104d8c,6),(0x104d74,2 if row['sound_wait']==2 else 1),(0x104d76,0),
                                  (0x104d82,0x0455),(0x104d84,0x0566),(0x104d86,0x0677),(0x104d88,0x0788)):setup(address,2,value)
    if row.get('live_return') and group=='sprite':stop=RETURN+4
    # Previous isolated scratch pattern becomes explicit shared-RAM input, before actual execution.
    for address in range(S-4096,S+4):ram[address&65535]=0x5a
    initial_return=RETURN+4 if group=='signed' and row.get('live_return') and row['left']>=row['right'] else RETURN
    setup(S,4,initial_return)
    pvc=bytearray(8192);pvc[0x1ff0:0x1ff4]=bytes.fromhex('00a01000')
    return dict(ram=bytes(ram),pvc=bytes(pvc),regs=regs,initial_a7=S,entry_pc=entry,stop_pc=stop,expected_final_a7=expected_sp,
        bank_base=0x200000,external=0,group=group,initial_host_writes=writes,source_fixture=case,
        initial_shared_stack=dict(start=S-4096,end_exclusive=S+4,fill=0x5a,return_address=S,return_value=initial_return),
        actual_compare_left=int.from_bytes(bytes(ram[(regs['a5']+0xd3e+i)&65535] for i in range(2)),'big') if group=='signed' else None,
        actual_compare_right=int.from_bytes(bytes(ram[(regs['a5']+0xd46+i)&65535] for i in range(2)),'big') if group=='signed' else None)


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
        obs.prepare(fx);phases=[];sound_released=False;seen_animation=False;sprite_waits=0
        def take(label,changes=()):
            obs.mutate(changes);phase=obs.run();phase['label']=label;phase['host_changes']=list(changes);phases.append(phase);return phase
        phase=take('begin')
        if row['group']=='sprite' and row.get('sprite_wait'):assert phase['waiting']
        while phase['waiting']:
            assert len(phases)<12,('unexpected repeated wait',row)
            if phase['outgoing']['pc']==0x3aea:
                assert row.get('sound_wait') and not sound_released
                sp=phase['outgoing']['a7'];high=int.from_bytes(obs.cpu.mem_read(sp,4),'big')==0x3c00
                a6=fx['regs']['a6']
                changes=[dict(address=0x10095c,size=2,value=0x0201),dict(address=a6+0x7e,size=1,value=0xaa),
                         dict(address=a6+0x42,size=2,value=0x110),dict(address=a6+0x46,size=2,value=0x190)]
                if high:changes.append(dict(address=shared.canonical(sp+4),size=1,value=0x77))
                hold=take('sound-hold-live-source-and-prefix-poison',changes)
                assert hold['waiting'] and hold['outgoing']==phase['outgoing'] and hold['ram_before']==hold['ram_after']
                if row['sound_wait']==3:
                    phase=take('sound-high-to-low',[dict(address=0x104d74,size=2,value=((hold['outgoing']['d1']&65535)+1)&0x7f)])
                    assert phase['waiting'] and phase['outgoing']['pc']==0x3aea
                    hold=take('sound-low-hold');assert hold['waiting'] and hold['outgoing']==phase['outgoing'] and hold['ram_before']==hold['ram_after']
                phase=take('sound-release',[dict(address=0x104d74,size=2,value=0xffff)]);sound_released=True
                assert not any(pc in phase['pcs'] for pc in (0x47cae,0x16ed2,0x47672))
                if high:assert any(e['pc']==0x3c00 and e['access']=='read' and e['bytes']=='77' for p in phases[2:] for e in p['events'])
                continue
            assert phase['outgoing']['pc']==0xcda4 and row.get('sprite_wait')
            sprite_waits+=1;seen_animation=any(0x49fc6 in p['pcs'] for p in phases)
            kind='animation-sprite' if seen_animation else 'wrapper-sprite'
            a6=phase['outgoing']['a6'];changes=[dict(address=a6+0x42,size=2,value=0x8000),dict(address=a6+0x46,size=2,value=0),
                dict(address=a6+0x53,size=1,value=0xff),dict(address=a6+0x12,size=4,value=0x12345640),dict(address=a6+0x1e,size=2,value=0x8001)]
            if row.get('live_return'):changes.append(dict(address=shared.canonical(S),size=4,value=fx['stop_pc']))
            if row.get('mixed_wait') and not seen_animation:changes.append(dict(address=0x108d36,size=2,value=8))
            hold=take(kind+'-hold-object-poison',changes)
            assert hold['waiting'] and hold['outgoing']==phase['outgoing'] and hold['ram_before']==hold['ram_after']
            release_pc=phase['outgoing']['pc'];captured=dict(phase['outgoing'])
            phase=take(kind+'-release',[dict(address=0x108d34,size=2,value=hold['outgoing']['d4']&65535)])
            # The immediate queue-accept boundary uses captured transformed registers;
            # later wrappers/draws may legitimately reread the changed object.
            accepted=next(b for b in phase['boundaries'] if b['pc']==0xcdaa)
            assert accepted['registers']==dict(captured,pc=0xcdaa)
            if row['group']=='sprite':assert 0x16ea4 not in phase['pcs'] and 0xcd58 not in phase['pcs']
        if row['group']=='signed':assert phase['pcs'][-2]==0x16eee
        elif row['group']=='sprite':assert phase['pcs'][-2] in (0xcd70,0xcd82,0xcd9c,0xce00)
        else:
            assert phase['pcs'][-2] in (0x4a0e2,0x49fea)
            all_pcs=[pc for p in phases for pc in p['pcs']]
            assert all(pc in all_pcs for pc in (0x16ed2,0x47672,0x16ea4,0x49f8c,0x49fc6))
            if row.get('mixed_wait'):assert sprite_waits==2 and sound_released
        return row,fx,phases
    finally:obs.close()

def physical_inputs(program,source):
    folder=ROOT/'extracted/runtime/program_rom';path=folder/'manifest.json';manifest=json.loads(path.read_text())
    assert manifest['source']==source and manifest['format']['kind']==3
    paths={path};joined=bytearray();cursor=0
    for row in manifest['resources']:
        resource=folder/row['file'];data=resource.read_bytes();paths.add(resource)
        assert sha(data)==row['sha256'];payload=physical.validate_container(data)
        header=struct.unpack_from('<4s7I',data)
        assert header[4]==row['source_rom_offset']==cursor and row['payload_size']==len(payload)
        assert payload==program[cursor:cursor+len(payload)]
        joined.extend(payload);cursor+=len(payload)
    assert cursor==len(program)==0x800000 and bytes(joined)==program
    return paths


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name)}
    # Native physical mapping is the exact eight real kind3 payloads; device
    # overlay/RAM mirrors still win over ROM in the declared CPU map.
    input_paths.update(physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];coverage=set();phase_count=0;ports_count=0;reads_count=0;edges=collections.Counter()
    selections=matrix(program)
    for i,row in enumerate(selections):
        actual,fx,phases=run_case(program,row);assert (actual,fx,phases)==run_case(program,row)
        phase_rows=[]
        for j,phase in enumerate(phases):
            coverage.update(phase['pcs']);edges.update(zip(phase['pcs'],phase['pcs'][1:]));stem='case_%03d_phase_%02d'%(i,j)
            ports=[e for e in phase['events'] if e['region']=='pvc'];ports_count+=len(ports)
            external_reads=sum(e['region']=='external' for e in phase['events']);reads_count+=external_reads
            payloads={stem+'_ram_before.bin':phase['ram_before'],stem+'_ram_after.bin':phase['ram_after'],
                stem+'_pvc_before.bin':phase['pvc_before'],stem+'_pvc_after.bin':phase['pvc_after'],
                stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
                stem+'_trace.json':(json.dumps({k:phase[k] for k in ('pcs','events','boundaries','guard')},indent=2)+'\n').encode()}
            for name,data in payloads.items():(OUT/name).write_bytes(data);artifacts[name]=sha(data)
            phase_rows.append(dict(label=phase['label'],incoming=phase['incoming'],outgoing=phase['outgoing'],waiting=phase['waiting'],
                host_changes=phase['host_changes'],modeled_bank=phase['modeled_bank'],external_reads=external_reads,guard=phase['guard'],
                raw_sprite_lookup_reads=[dict(address=e['address'],size=e['size'],bytes=e['bytes']) for e in phase['events'] if e['pc']==0x47ce0 and e['access']=='read'],
                artifacts={name:sha(data) for name,data in payloads.items()}))
        phase_count+=len(phases)
        results.append(dict(index=i,selection=actual,fixture={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')},phases=phase_rows,reproduced_twice=True))
        print('%d/%d %s %s %dphases'%(i+1,len(selections),row['group'],row['label'],len(phases)),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions),indent=2)+'\n').encode();(OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    required=(0x47cae,0x47cc0,0x47cc6,0x47cca,0x47ce0,0x47ce6,0x16ede,0x16ee8,0x16eee,0x16ea4,0xcda4,0xcdaa,0xcdd0,0xcdb6,0x49f8c,0x49fc6,0x3aea,0x3c00)
    assert set(required)<=coverage,set(required)-coverage
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,cases=len(results),phases=phase_count,
        fresh_CPU_runs=len(results)*2,phase_executions=phase_count*2,previous_same_CPU_resumes=phase_count-len(results),ports=ports_count,external_reads=reads_count,
        case_groups=dict(sprite=25,signed=11,chain=16),covered_PCs=sorted(coverage),required_PC_coverage=list(required),
        actual_branch_edges=[dict(pc=a,next_pc=b,count=n) for (a,b),n in sorted(edges.items())],
        raw_sprite_window=dict(start=0x48a12,end_exclusive=0x48e12,size=1024,sha256=sha(program[0x48a12:0x48e12]),interpretation='raw LONG lookup window, not claimed logical256-entry table'),
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,failure=None,
        limits=['Controlled incoming fixtures at actual47cae/16ea4/16ed2; natural scheduler/gameplay reachability not claimed.',
            'Actual chain47cae through16ed2/47672/16ea4 and initializer49f8c/49fc6 stops before47d20. Standalone helpers use caller-supplied live returnLONG; no artificial per-phase stack.',
            'FullRAM/16R/PC/events/ports without stackdiffmask. SameCPU sound/sprite/animation holds and releases apply only declared hostRAMchanges; laterdraws may legitimately reread object.',
            'Originalprogram physicalbytes equal all8actualkind3 payloads. CPU overlay maps16coherentRAMmirrors/PVC before ROM; declaredbank2 only, otherbankROMread/PVCread/unsupportedcallback/MMIO/TRAP/timeout guarded.',
            'NoSRreads or nativeCCR/carry oracle/generalhardware/timing/IRQ proof. Existing original observers and extracted runtime resources imported/read-only.',
            'Eight chosen sourcehighBYTE query representatives do not exhaust256rawindices; rawLONGpayload values do not establish logical/natural validity.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(results),phases=phase_count,resumes=phase_count-len(results),sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
