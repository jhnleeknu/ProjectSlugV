"""Original49fc6 representative full paths with coherent shared work-RAM stack.

Fixture generators are imported read-only. No ROM patch/stub, register injection
or SR reads. This is native observation, not C++ comparison or natural gameplay.
"""
import copy
import collections
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
import observe_animation_shared_stack as shared
import observe_activation_animation_scripts as direct
import observe_animation_indexed_execution as indexed
import observe_animation_control_commands as control
import observe_animation_sound_callback as sound
import observe_animation_word_callback as word
import observe_animation_field_execution as field
import observe_animation_direct_sound as direct_sound
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/animation_machine_extended_native'
ENTRY,RETURN,S,RAM,SIZE,PVC=shared.ENTRY,shared.RETURN,shared.S,shared.RAM,shared.SIZE,shared.PVC
RANGES=((ENTRY,0x4a00c),(0x4a01e,0x4a25a),(0x4a268,0x4a46c),
        (0xcd50,0xce02),(0x3ac8,0x3c08),(0x47672,0x476bc),(0xca70,0xca76),
        (0x2b3e8,0x2b40c),(0x3679e,0x367a0))
BOUNDARIES=(ENTRY,0x49ffe,0x4a0ca,0x4a104,0x4a10c,0x4a1dc,0xcd58,0xcd5e,0xcda4,
            0xcdaa,0xcdb6,0xcdd0,0xcde4,0xce00,0x4a200,0x4a222,0x4a226,0x4a22a,
            0x4a22c,0x4a23e,0x4a270,0x4a276,0x4a2da,0x4a2ec,0x4a30c,0x4a354,
            0x4a376,0x4a37a,0x4a408,0x4a43e,0x4a460,0x4a464,0x3679e,
            0x2b3e8,0x2b3fa,0x47672,0x4768e,0x3af8,0x3ac8,0x3c00)
REGS=shared.REG_IDS
CAP=500000
EXTERNAL=0xd00046
sha=shared.sha


def put(ram,address,size,value):shared.put(ram,address,size,value)


def matrix(program):
    rows=[]
    def add(source,index,case,chain='none',**extra):
        rows.append(dict(source=source,source_case_index=index,case=copy.deepcopy(case),chain=chain,**extra))
    dc=direct.cases()
    for i,c in enumerate(dc):
        if c['family'].startswith('queue-') and c['queue'] in ('normal','deferred','clip-x','clip-y','full'):add('direct',i,c)
        elif c['family']=='actual-flash-draw-skip' and c['flash_flag']==8 and c['flash_phase']==1:add('direct',i,c)
        elif c['family']=='same-CPU-current-draw-wait':add('direct',i,c,'sprite')
    ic=indexed.cases()
    for i,c in enumerate(ic):
        if c['family'].startswith('draw-') and c['index']==4:add('indexed',i,c)
        elif c['family']=='same-CPU-indexed-draw-wait' and c['index']==0:add('indexed',i,c,'indexed-sprite')
    cc=control.cases()
    for i,c in enumerate(cc):
        if c['opcode']==0x0c and c['selector'] in (0,0xffff) and c['desired'] in (0,1) and c['requested_live'] in (0,0xff):add('control',i,c)
        elif c['opcode']==0x14 and ((c['profile']=='RAM' and c['requested_index']==1) or (c['profile']=='fixed6431a' and c['requested_index']==255) or (c['profile']=='overlap+7a' and c['requested_index']==0)):add('control',i,c)
    # A real standalone RTS callback from the original dispatch table.
    base=next((i,c) for i,c in enumerate(cc) if c['opcode']==0x14 and c['profile']=='RAM' and c['requested_index']==1)
    c=copy.deepcopy(base[1]);c['selector']=3;c['family']='14-03-actual-RTS';add('control',base[0],c)
    sc=sound.cases()
    for i,c in enumerate(sc):
        if c['a6']==0x102000 and not c['queue_alias'] and ((c['wait']>0) or c['wait']==0 and c['mode'] in (0,3) and c['external'] in (0,1)):
            add('sound',i,c,'sound' if c['wait'] else 'none')
    wc=word.cases()
    for sel in (0x1d,0x1e):
        i,c=next((i,c) for i,c in enumerate(wc) if c['family']=='first-selector-modular-alias' and c['commands'][0]['sel1']==sel+0x4000)
        add('word',i,c)
    i,c=next((i,c) for i,c in enumerate(wc) if c['family']=='first-selector-modular-alias' and c['commands'][0]['sel1']==0x1d)
    c=copy.deepcopy(c);c['commands'][0]['sel1']=3;c['commands'][0]['operand']=0x8123fedc;c['operand_table']=False;c['family']='3c-03-actual-RTS';add('word',i,c)
    for i,c in enumerate(wc):
        if c['family']=='1f-immediate-gates' and c['mode']==0:add('word',i,c)
        elif c['family']=='1f-same-CPU-wait' and c['poison']=='prefix':add('word',i,c,'sound')
    fc=field.cases(program)
    for op in (0x18,0x1c,0x20,0x24,0x34,0x38,0x2c):
        options=[(i,c) for i,c in enumerate(fc) if c['opcode']==op and c['alias']=='none']
        if op==0x18:chosen=[(i,c) for i,c in options if c['selector'] in (0,0x8000,0xffff) and c['value']==0x80]
        elif op in (0x1c,0x20,0x24):chosen=[(i,c) for i,c in options if c['selector'] in (0,0x90,0x96) and c['family'] in ('BYTE-selector-domain','24-all-BYTE-selectors-zero-wrap')]
        elif op in (0x34,0x38):chosen=[(i,c) for i,c in options if c['value'] in (0,0x8000,0xffff)]
        else:chosen=[(i,c) for i,c in options if c['selector']==0x1e and ((c['family']=='2c-length-and-unsigned-compare' and (c['length'],c['field']) in ((0,255),(8,0))) or c['family']=='2c-two-signed-additions' and c['relative']==0xfffe)]
        for i,c in chosen:add('field',i,c)
    ds=direct_sound.cases()
    for i,c in enumerate(ds):
        if c['family']=='same-CPU-wait' and c['entries'][0]==0x0455 and c['tail']==0:add('direct_sound',i,c,'sound')
        elif c['family']=='category-open-gates-append' and c['commands'] in ([0x2000],[0x0420]):add('direct_sound',i,c)
        elif c['family']=='external-two-commands-one-invocation' and c['external']==0:add('direct_sound',i,c)
    # Explicit control08 into a terminal28, derived from a direct fixture.
    add('direct',0,dict(dc[0],script=0x106000,timer=0),'none',control_script='080000106008000028')
    return rows


def fixture(program,row):
    c=row['case'];i=row['source_case_index'];source=row['source']
    if source=='direct':ram,regs=direct.fixture(c,i);details={}
    elif source=='indexed':ram,regs,details=indexed.fixture(program,c,i)
    elif source=='control':ram,regs=control.fixture(c,i,program);details={}
    elif source=='sound':ram,regs=sound.fixture(c,i);details={}
    elif source=='word':ram,regs,details=word.fixture(c,i,program)
    elif source=='field':ram,regs,details=field.fixture(program,c,i)
    else:ram,regs,details=direct_sound.fixture(c,i)
    ram=bytearray(ram)
    # The old isolated stack fixture is now explicit incoming shared RAM;
    # its full final differences are retained and never masked.
    stack_start=S-4096
    for address in range(stack_start,S+4):ram[address&65535]=0x5a
    put(ram,S,4,RETURN)
    if 'control_script' in row:
        script=bytes.fromhex(row['control_script']);ram[0x6000:0x6000+len(script)]=script
    pvc=bytearray(8192);pvc[0x1ff0:0x1ff4]=bytes.fromhex('00a01000')
    return dict(ram=bytes(ram),regs=regs,pvc=bytes(pvc),external=c.get('external',0),details=details,
        bank_base=0x200000,initial_a7=S,stop_pc=RETURN,entry_pc=ENTRY,
        initial_shared_stack=dict(start=stack_start,end_exclusive=S+4,fill=0x5a,return_address=S,return_value=RETURN),
        synthetic_control_script=row.get('control_script'))


class Observer:
    def __init__(self,program):self.program=program;self.cpu=None;self.backing=None
    def regs(self):return {key:self.cpu.reg_read(REGS[key]) for key in shared.isolated.REG_NAMES+('a7','pc')}
    def prepare(self,fx):
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
            if pc==RETURN:cpu.emu_stop();return
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
        c.reg_write(REGS['sr'],0x2000);c.reg_write(REGS['a7'],S)
        for key in shared.isolated.REG_NAMES:c.reg_write(REGS[key],fx['regs'][key])
        c.reg_write(REGS['pc'],ENTRY)
        return self
    def run(self):
        self.pcs=[];self.events=[];self.boundaries=[];self.guard=None;self.pc=None;self.visits=0
        before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192));incoming=self.regs()
        bank_before=self.bank;ff8_before=self.ff8;ff9_before=self.ff9
        self.cpu.emu_start(incoming['pc'],0xffffff,count=CAP)
        outgoing=self.regs()
        assert self.guard is None,self.guard
        assert outgoing['pc']==RETURN or outgoing['pc'] in (0xcda4,0x3aea) and self.visits==2,('timeout_or_stop',outgoing)
        if outgoing['pc']==RETURN:assert outgoing['a7']==S+4
        result=dict(incoming=incoming,outgoing=outgoing,ram_before=before,ram_after=bytes(self.backing),
            pvc_before=pvc_before,pvc_after=bytes(self.cpu.mem_read(PVC,8192)),pcs=self.pcs,events=self.events,
            boundaries=self.boundaries,waiting=outgoing['pc']!=RETURN,modeled_bank=self.bank,
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


def replay(program,result):
    ram=bytearray(result['ram_before']);pvc=bytearray(result['pvc_before'])
    for e in result['events']:
        assert e['pc']==e['hook_pc'];a,n=e['address'],e['size'];data=bytes.fromhex(e['bytes'])
        if e['region']=='ram':
            before=bytes(ram[(a+i)&65535] for i in range(n));assert e['before']==before.hex()
            if e['access']=='read':assert before==data
            else:
                for i,b in enumerate(data):ram[(a+i)&65535]=b
        elif e['region']=='pvc':
            assert bytes(pvc[a-PVC:a-PVC+n]).hex()==e['before'];pvc[a-PVC:a-PVC+n]=data
        elif e['region'] in ('fixed','bank'):assert e['access']=='read' and data==program[a:a+n]
        else:assert e['access']=='read'
    assert bytes(ram)==result['ram_after'] and bytes(pvc)==result['pvc_after']


def run_case(program,row):
    row=copy.deepcopy(row);fx=fixture(program,row);obs=Observer(program)
    try:
        obs.prepare(fx);phases=[]
        def take(label,changes=()):
            obs.mutate(changes);phase=obs.run();phase['label']=label;phase['host_changes']=list(changes);phases.append(phase);return phase
        first=take('begin')
        if row['chain']=='none':assert not first['waiting'],row
        elif row['chain'] in ('sprite','indexed-sprite'):
            assert first['waiting'] and first['outgoing']['pc']==0xcda4
            changes=[dict(address=obs.cpu.reg_read(REGS['a6'])+0x42,size=2,value=0x8000),
                     dict(address=obs.cpu.reg_read(REGS['a6'])+0x46,size=2,value=0)]
            if row['chain']=='indexed-sprite':
                changes += [dict(address=shared.canonical(S-4),size=4,value=0x106800),dict(address=0x106800,size=2,value=0),
                            dict(address=0x105802,size=2,value=0xffff),dict(address=0x105800,size=1,value=0xff)]
            held=take('hold-poisoned-current-prefix',changes)
            assert held['waiting'] and held['outgoing']==first['outgoing'] and held['ram_after']==held['ram_before']
            consumer=(held['outgoing']['a5']+0xd34)&0xffffffff
            last=take('release',[dict(address=consumer,size=2,value=held['outgoing']['d4']&65535)])
            assert not last['waiting']
            if row['chain']=='indexed-sprite':
                pop=[e for e in last['events'] if e['pc']==0x4a270 and e['access']=='read']
                assert len(pop)==1 and pop[0]['bytes']=='00106800'
            assert 0x4a10c not in last['pcs'] or row['chain']=='sprite' # later direct draws legitimately reread object
        else:
            assert first['waiting'] and first['outgoing']['pc']==0x3aea
            script_pointer=int.from_bytes(fx['ram'][(fx['regs']['a6']+0x26)&65535:((fx['regs']['a6']+0x26)&65535)+4],'big')
            changes=[dict(address=script_pointer,size=1,value=0xff)]
            if row['source'] in ('sound','word'):changes.append(dict(address=0x10095c,size=2,value=0x1234))
            held=take('hold-poisoned-consumed-prefix',changes);assert held['waiting'] and held['outgoing']==first['outgoing'] and held['ram_after']==held['ram_before']
            high_to_low=row['case'].get('wait')==3 or row['case'].get('chain')=='high_to_low'
            if high_to_low:
                next_head=((held['outgoing']['d1']&65535)+1)&0x7f
                mid=take('high-to-low',[dict(address=0x104d74,size=2,value=next_head)])
                assert mid['waiting'] and mid['outgoing']['pc']==0x3aea
                low_hold=take('low-hold');assert low_hold['waiting'] and low_hold['outgoing']==mid['outgoing'] and low_hold['ram_after']==low_hold['ram_before']
            last=take('release',[dict(address=0x104d74,size=2,value=0xffff)])
            assert not last['waiting']
        return row,fx,phases
    finally:obs.close()


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    OUT.mkdir(parents=True,exist_ok=True)
    initial_sources={Path(__file__).resolve():sha(Path(__file__).read_bytes())}
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.suffix=='.py' and ROOT/'tools' in path.parents:initial_sources[path]=sha(path.read_bytes())
    rows=matrix(program);results=[];artifacts={};coverage=set();phase_count=0;edges=collections.Counter();commands=collections.Counter()
    for i,row in enumerate(rows):
        actual,fx,phases=run_case(program,row);again=run_case(program,row)
        assert (actual,fx,phases)==again,('nonreproducible',row)
        phase_rows=[]
        for j,phase in enumerate(phases):
            coverage.update(phase['pcs']);edges.update(zip(phase['pcs'],phase['pcs'][1:]))
            commands.update(int(e['bytes'],16) for e in phase['events'] if e['pc']==0x4a000 and e['access']=='read')
            stem='case_%03d_phase_%02d'%(i,j)
            ports=[e for e in phase['events'] if e['region']=='pvc']
            trace={k:phase[k] for k in ('pcs','events','boundaries')}
            payloads={stem+'_ram_before.bin':phase['ram_before'],stem+'_ram_after.bin':phase['ram_after'],
                stem+'_pvc_before.bin':phase['pvc_before'],stem+'_pvc_after.bin':phase['pvc_after'],
                stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
                stem+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
            for name,data in payloads.items():(OUT/name).write_bytes(data);artifacts[name]=sha(data)
            phase_rows.append(dict(label=phase['label'],incoming=phase['incoming'],outgoing=phase['outgoing'],waiting=phase['waiting'],
                host_changes=phase['host_changes'],modeled_bank=phase['modeled_bank'],external_reads=sum(e['region']=='external' for e in phase['events']),
                artifacts={name:sha(data) for name,data in payloads.items()}))
        phase_count+=len(phases);results.append(dict(index=i,selection=actual,fixture={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')},phases=phase_rows,reproduced_twice=True))
        print('%d/%d %s %s %dphases'%(i+1,len(rows),row['source'],row['case'].get('family','sound'),len(phases)),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    source_path=OUT/'source.json';source_path.write_text(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions),indent=2)+'\n');artifacts[source_path.name]=sha(source_path.read_bytes())
    inputs={}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            p=Path(name).resolve()
            if p.suffix=='.py' and (ROOT/'tools' in p.parents or 'unicorn' in str(p)):inputs[str(p)]=sha(p.read_bytes())
    inputs[str(Path(__file__).resolve())]=sha(Path(__file__).read_bytes())
    for path,value in initial_sources.items():assert sha(path.read_bytes())==value,path
    for p in (rom,ROOT/'extracted/program/manifest.json',Path(uclib._name)):
        inputs[str(p.resolve())]=sha(p.read_bytes())
    pin=shared.isolated.pinned_reference(ROOT)
    for name in pin['files']:
        p=ROOT/'artifacts/reference'/name;inputs[str(p)]=sha(p.read_bytes())
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    required=(0xcde4,0xcdd0,0xcd9c,0xcd66,0xcd78,0xcda4,0x4a270,0x3679e,0x2b3e8,0x2b3fa,0x47672,0x3c00,0x4a27e,0x4a294,0x4a2ac,0x4a2c4,0x4a2f2,0x4a300,0x4a3de,0x4a3ac,0x4a3b8,0x4a0e4)
    assert set(required)<=coverage,set(required)-coverage
    conditional={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    report=dict(schema_version=1,source=source,cases=len(rows),phases=phase_count,fresh_CPU_runs=len(rows)*2,phase_executions=phase_count*2,
        inputs=inputs,artifacts=artifacts,results=results,covered_PCs=sorted(coverage),
        actual_opcode_fetch_counts={hex(k):v for k,v in sorted(commands.items())},
        conditional_branch_edges=[dict(pc=a,next_pc=b,count=n) for (a,b),n in sorted(edges.items()) if a in conditional],
        required_PC_coverage=list(required),
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        shared_stack=True,stack_difference_mask=False,failure=None,
        limitations=['Controlled imported fixtures; natural caller/script reachability unknown. No CCR/timing/IRQ/hardware equivalence claim.',
            'Canonical fixedROM RX plusbank2; actual PVC writes fold into metadata. No PVC reads; bankROM reads permitted only when actual folded bank2.',
            'All16RAM mirrors share CPU-retained64KiB backing. Original stack scratch initialfill is explicit sharedRAMfixture, not isolated memory.',
            'Known originalcode ranges/callbacks only. Timeout/TRAP/unsupporteddevices fail; no silently skipped native cases.'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),phases=phase_count,sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()
