"""Original192c4 strip and19832 paired-point motion observations, including CCR.C."""
import collections
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from observe_scene_motion_bounds import resource_items,sha
from observe_scene_motion_time import HIGHS,BASE,STACK,RETURN,SCRATCH,FIXED
from verify_scene_command import REGS,KEYS
from verify_stage_catalog import SOURCE_SHA256
ENTRIES=(0x192c4,0x19832)
BUG_PCS={0x18:0x1941a,0x1c:0x19432,0x20:0x1944a,0x24:0x1945e,0x28:0x19476,0x44:0x19502,0x48:0x1951a,0x4c:0x19532,0x50:0x19546,0x54:0x1955e}
POINTS=((-100,-100),(100,100),(-100,100),(0,0),(0x8000,0x7fff))
TIME_PAIRS=((15,16),(15,25),(15,35),(15,5),(15,0xffff),(0x8000,0))

def payload(kind,extent):
    return b''.join(struct.pack('>5H',time,k,ext,0,0) for time,k,ext in ((0,0x14,10),(10,kind,extent),(20,0x14,10),(30,0x6c,10)))+struct.pack('>2H',40,0xffff)

def build_cases(root,program):
    resources,metadata=resource_items(root,program);cases=[]
    def add(family,**changes):
        case=dict(family=family,entry=0x192c4,profile=1,cursor=0,input_a1=0,base_x=0,base_y=0,coords=[0x10001,0,0x900ff,0],current_time=0,proposed_time=0,fraction=0,orthogonal=0,relocated=False);case.update(changes);cases.append(case)
    records=0
    for item in resources:
        for offset in range(0,item['end']-item['cpu']-4,10):
            records+=1;cursor=item['cpu']+offset;time=struct.unpack_from('>H',program,cursor)[0];end=struct.unpack_from('>H',program,cursor+10)[0]
            for (left,right),profile in itertools.product(POINTS,range(2)):
                add('canonical-all108-record-strips',cursor=0,input_a1=cursor,path_file=item['file'],profile=profile,coords=[0x10001,(left&65535)<<16,0x900ff,((right&65535)<<16)|profile])
            for (current,target),profile in itertools.product(((time,time),(time,(time+1)&65535),(time,(end-1)&65535),(time,end),(time,(time-1)&65535),(end,time)),range(2)):
                add('canonical-all108-record-pair-directions',entry=0x19832,cursor=cursor,path_file=item['file'],profile=profile,current_time=current,proposed_time=target,fraction=profile*0xffff,orthogonal=(0,100)[profile])
    assert records==108
    for kind,extent,(left,right) in itertools.product(range(0,0x90,4),(0,1,0x7fff,0x8000,0xffff),POINTS):
        add('synthetic-all36-strip-width-points',cursor=0,input_a1=FIXED+10,relocated=True,kind=kind,extent=extent,payload_hex=payload(kind,extent).hex(),coords=[0x10001,(left&65535)<<16,0x900ff,((right&65535)<<16)|0xffff])
    for kind,base,extent,(left,right) in itertools.product((0x14,0x64),(0,1,0x7fff,0x8000,0xffff),(0,1,0x7fff,0x8000,0xffff),POINTS):
        add('synthetic-flat-signed-band-and-expanded-WORD-wrap',cursor=0,input_a1=FIXED+10,relocated=True,kind=kind,extent=extent,payload_hex=payload(kind,extent).hex(),base_x=base,base_y=base,coords=[(left&65535)<<16,(left&65535)<<16,((right&65535)<<16)|0xffff,((right&65535)<<16)|0xffff])
    for kind,(current,target),orthogonal in itertools.product(range(0,0x90,4),TIME_PAIRS,(0,100,0xffff)):
        add('synthetic-all36-pair-transition-bands',entry=0x19832,cursor=FIXED+10,relocated=True,kind=kind,extent=10,payload_hex=payload(kind,10).hex(),current_time=current,proposed_time=target,fraction=0x8000,orthogonal=orthogonal)
    for kind,(current,target),fraction in itertools.product((0x14,0x64),((0x7fff,0x8000),(0x8000,0x7fff),(0,0x8000),(0x8000,0),(0,0x7fff)),(0,0xffff)):
        add('synthetic-N-only-LONG-WORD-overflow-direction',entry=0x19832,cursor=FIXED,relocated=True,kind=kind,extent=10,payload_hex=(struct.pack('>5H',0,kind,10,0,0)+struct.pack('>2H',0xffff,0xffff)).hex(),current_time=current,proposed_time=target,fraction=fraction)
    for kind,fraction in itertools.product((0x14,0x64),(0,0xffff)):
        raw=struct.pack('>5H5H2H',0,kind,10,0,0,0xffff,kind,10,0,0,0x10,0xffff)
        add('synthetic-N-only-WORD-backward-overflow',entry=0x19832,cursor=FIXED+10,relocated=True,kind=kind,extent=10,payload_hex=raw.hex(),current_time=0x8000,proposed_time=0x7fff,fraction=fraction)
    for profile,word in itertools.product(range(2),(0,1,0x7fff,0x8000,0xffff)):
        add('null-pair-clears-D6-D7',entry=0x19832,profile=profile,current_time=word,proposed_time=word)
    for kind,direction in itertools.product((0x14,0x24,0x6c,0x78),(1,-1)):
        targets=(5,15,35) if direction==1 else (35,15,5);sequence=hex(kind)+'-'+str(direction)
        for position,target in enumerate(targets):
            add('actual-cli-carry-three-pair-calls',entry=0x19832,cursor=FIXED if direction==1 else FIXED+30,relocated=True,kind=kind,extent=10,payload_hex=payload(kind,10).hex(),current_time=(0 if direction==1 else 39) if position==0 else targets[position-1],proposed_time=target,sequence=sequence,sequence_position=position)
    assert len(cases)==4232,len(cases)
    return cases,resources,metadata

def fixture(case):
    ram=bytearray(__import__('hashlib').shake_256(b'motion-pair'+bytes([case['profile']])).digest(65536));struct.pack_into('>IHH',ram,0xd3b4,case['cursor'],case['base_x'],case['base_y'])
    if case['relocated']:
        raw=bytes.fromhex(case['payload_hex']);ram[SCRATCH-BASE:SCRATCH-BASE+len(raw)]=raw
    return ram

def incoming(case,program,ram,prior=None):
    values=list(HIGHS[case['profile']] if prior is None else prior)
    if case['entry']==0x192c4:values[:4]=case['coords'];values[9]=case['input_a1'];return values
    cursor=int.from_bytes(ram[0xd3b4:0xd3b8],'big');points=[]
    if cursor:
        raw=bytes.fromhex(case['payload_hex']) if case['relocated'] else program;offset=cursor-FIXED if case['relocated'] else cursor;time,kind=struct.unpack_from('>HH',raw,offset);bx,by=struct.unpack_from('>HH',ram,0xd3b8);sign=1 if kind<0x2c or 0x58<=kind<0x74 else -1
        for target in (case['current_time'],case['proposed_time']):
            primary=(((bx if kind<0x58 else by)+sign*((target-time)&65535))&65535)<<16|case['fraction'];other=(case['orthogonal']&65535)<<16
            points.extend((primary,other) if kind<0x58 else (other,primary))
    else:points=[0x12345678,0x87654321,0x7fffffff,0x80000000]
    struct.pack_into('>4I',ram,0xd3bc,*points)
    return values

class UnicornObserver:
    def __init__(self,program,record_trace=False):
        self.record_trace=record_trace;self.trace=[];self.cpu=make_cpu(program);self.baseline=self.cpu.context_save();self.program=program;self.calls=collections.Counter();self.snapshots=[];self.bugs=[];self.pending=None;self.types=[];self.transitions=[];self.branches=[];self.pending_branch=None;self.pending_transition=None;self.error=None
        def code(cpu,address,size,user):
            if self.pending_transition is not None:self.transitions.append(dict(self.pending_transition,carry=address==0x1985e,next_pc=address));self.pending_transition=None
            if self.record_trace and address!=RETURN:self.trace.append(address)
            if self.pending_branch is not None:self.branches.append(dict(pc=self.pending_branch,next_pc=address));self.pending_branch=None
            if address in (0x19864,0x1986c,0x198b0):self.pending_branch=address
            if address==RETURN:cpu.emu_stop();return
            if address in (0x192c4,0x19832,0x18efa,0x196ac,0x196de,0x19710,0x1971c,0x1985e,0x1989a,0x198de,0x1989e,0x198e2,0x19370,0x19578):self.calls[address]+=1
            if address==0x192c4:self.types.append(int.from_bytes(cpu.mem_read(cpu.reg_read(m.UC_M68K_REG_A1)+2,2),'big'))
            if address in (0x19864,0x1986c,0x198b0):self.snapshots.append(dict(pc=address,d5=cpu.reg_read(REGS[5])&0xffffffff,d6=cpu.reg_read(REGS[6])&0xffffffff,d7=cpu.reg_read(REGS[7])&0xffffffff,a1=cpu.reg_read(REGS[9])&0xffffffff,start=int.from_bytes(cpu.mem_read(cpu.reg_read(REGS[9]),2),'big'),end=int.from_bytes(cpu.mem_read(cpu.reg_read(REGS[9])+10,2),'big')))
            if address in (0x19898,0x198dc):self.pending_transition=dict(pc=address,d6=cpu.reg_read(REGS[6])&0xffffffff,d7=cpu.reg_read(REGS[7])&0xffffffff)
            if address in BUG_PCS.values():self.pending=dict(pc=address,d0=cpu.reg_read(REGS[0])&0xffffffff,d2=cpu.reg_read(REGS[2])&0xffffffff,before_d3=cpu.reg_read(REGS[3])&0xffffffff)
            if self.pending is not None and address==self.pending['pc']+2:self.bugs.append(dict(self.pending,after_d3=cpu.reg_read(REGS[3])&0xffffffff));self.pending=None
        def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,case,ram,regs):
        cpu=self.cpu;native=bytearray(ram);native_regs=regs.copy()
        if case['relocated']:
            if case['entry']==0x19832:struct.pack_into('>I',native,0xd3b4,SCRATCH+int.from_bytes(native[0xd3b4:0xd3b8],'big')-FIXED)
            else:native_regs[9]=SCRATCH+native_regs[9]-FIXED
        cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(native));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(REGS,native_regs):cpu.reg_write(register,value)
        self.trace.clear();self.calls.clear();self.snapshots.clear();self.bugs.clear();self.types.clear();self.transitions.clear();self.branches.clear();self.pending_branch=None;self.pending_transition=None;self.pending=None;self.error=None
        try:cpu.emu_start(case['entry'],0xffffff,count=200000)
        except unicorn.UcError as error:self.error=dict(kind='emulator-error',error=str(error),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=RETURN and self.error is None:self.error=dict(kind='instruction-cap',pc=pc)
        assert bytes(cpu.mem_read(0,0x100000))==self.program[:0x100000]
        output=bytearray(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(register)&0xffffffff for register in REGS)));result['carry']=bool(cpu.reg_read(m.UC_M68K_REG_SR)&1)
        if case['relocated'] and pc==RETURN:
            result['a1']=result['a1']-SCRATCH+FIXED
            if case['entry']==0x19832:struct.pack_into('>I',output,0xd3b4,int.from_bytes(output[0xd3b4:0xd3b8],'big')-SCRATCH+FIXED)
        if pc==RETURN:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        return bytes(output),result,dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),final_sr=cpu.reg_read(m.UC_M68K_REG_SR),calls={hex(k):v for k,v in self.calls.items()},observed_types=self.types.copy(),comparison_snapshots=self.snapshots.copy(),duplicate_D0_ADD_snapshots=self.bugs.copy(),transition_returns=self.transitions.copy(),branch_successors=self.branches.copy(),instruction_trace=self.trace.copy(),error=self.error,mmio_writes=0)

def oracle_provenance(root):
    from build_musashi_oracle import REVISION,ARCHIVE_SHA256
    folder=root/'artifacts/dependencies/musashi_oracle_build';metadata_path=folder/'metadata.json';metadata=json.loads(metadata_path.read_text())
    assert metadata['revision']==REVISION and metadata['archive_sha256']==ARCHIVE_SHA256
    archive=root/'artifacts/dependencies'/('musashi-'+REVISION+'.tar.gz');assert sha(archive.read_bytes())==ARCHIVE_SHA256
    source=root/'artifacts/dependencies'/('Musashi-'+REVISION)
    for name,digest in metadata['source_file_sha256'].items():assert sha((source/name).read_bytes())==digest
    for name,digest in metadata['generated_file_sha256'].items():assert sha((folder/name).read_bytes())==digest
    paths=[metadata_path,Path(metadata['library_path']),root/'tools/native/musashi_oracle.c',root/'tools/musashi_oracle.py',root/'tools/build_musashi_oracle.py',archive]
    files={str(path.relative_to(root)):sha(path.read_bytes()) for path in paths}
    assert files[str(Path(metadata['library_path']).relative_to(root))]==metadata['library_sha256'] and files['tools/native/musashi_oracle.c']==metadata['bridge_sha256']
    return dict(engine='Musashi M68000',metadata=metadata,files_sha256=files)

class Observer:
    def __init__(self,program,record_trace=False):
        from musashi_oracle import MusashiOracle
        self.record_trace=record_trace;self.trace=[];self.cpu=MusashiOracle();self.cpu.load(0,program[:0x100000]);self.program=program;self.calls=collections.Counter();self.snapshots=[];self.bugs=[];self.pending=None;self.types=[];self.transitions=[];self.branches=[];self.pending_branch=None;self.error=None
        def code(address):
            if self.record_trace and address!=RETURN:self.trace.append(address)
            if self.pending_branch is not None:self.branches.append(dict(pc=self.pending_branch,next_pc=address));self.pending_branch=None
            if address in (0x19864,0x1986c,0x198b0):self.pending_branch=address
            cpu=self.cpu
            if address in (0x192c4,0x19832,0x18efa,0x196ac,0x196de,0x19710,0x1971c,0x1985e,0x1989a,0x198de,0x1989e,0x198e2,0x19370,0x19578):self.calls[address]+=1
            if address==0x192c4:self.types.append(int.from_bytes(cpu.read(cpu.get_reg('a1')+2,2),'big'))
            if address in (0x19864,0x1986c,0x198b0):self.snapshots.append(dict(pc=address,d5=cpu.get_reg('d5'),d6=cpu.get_reg('d6'),d7=cpu.get_reg('d7'),a1=cpu.get_reg('a1'),start=int.from_bytes(cpu.read(cpu.get_reg('a1'),2),'big'),end=int.from_bytes(cpu.read(cpu.get_reg('a1')+10,2),'big')))
            if address in (0x19898,0x198dc):self.transitions.append(dict(pc=address,carry=bool(cpu.get_reg('sr')&1),d6=cpu.get_reg('d6'),d7=cpu.get_reg('d7')))
            if address in BUG_PCS.values():self.pending=dict(pc=address,d0=cpu.get_reg('d0'),d2=cpu.get_reg('d2'),before_d3=cpu.get_reg('d3'))
            if self.pending is not None and address==self.pending['pc']+2:self.bugs.append(dict(self.pending,after_d3=cpu.get_reg('d3')));self.pending=None
        self.cpu.set_instruction_hook(code)
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(pc),hex(address),size,value)
        self.cpu.set_write_hook(write)
    def run(self,case,ram,regs):
        cpu=self.cpu;native=bytearray(ram);native_regs=regs.copy()
        if case['relocated']:
            if case['entry']==0x19832:struct.pack_into('>I',native,0xd3b4,SCRATCH+int.from_bytes(native[0xd3b4:0xd3b8],'big')-FIXED)
            else:native_regs[9]=SCRATCH+native_regs[9]-FIXED
        cpu.reset();cpu.load(BASE,bytes(native));cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(KEYS,native_regs):cpu.set_reg(register,value)
        cpu.set_reg('pc',case['entry']);self.trace.clear();self.calls.clear();self.snapshots.clear();self.bugs.clear();self.types.clear();self.transitions.clear();self.branches.clear();self.pending_branch=None;self.pending=None;self.error=None
        guards=[(0,BASE),(BASE+65536,STACK-4096-BASE-65536),(STACK+4,0x200000-STACK-4)];before=[cpu.read(address,size) for address,size in guards]
        status=cpu.run(instruction_budget=200000,sentinel=RETURN);pc=cpu.get_reg('pc')
        if status['status']!='sentinel':self.error=status
        assert [cpu.read(address,size) for address,size in guards]==before and cpu.read(0,BASE)==self.program[:BASE]
        output=bytearray(cpu.read(BASE,65536));result={register:cpu.get_reg(register) for register in KEYS};result['carry']=bool(cpu.get_reg('sr')&1)
        if case['relocated'] and pc==RETURN:
            result['a1']=result['a1']-SCRATCH+FIXED
            if case['entry']==0x19832:struct.pack_into('>I',output,0xd3b4,int.from_bytes(output[0xd3b4:0xd3b8],'big')-SCRATCH+FIXED)
        if pc==RETURN:assert cpu.get_reg('a7')==STACK+4
        return bytes(output),result,dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.get_reg('a7'),final_sr=cpu.get_reg('sr'),instructions=status['instructions'],calls={hex(k):v for k,v in self.calls.items()},observed_types=self.types.copy(),comparison_snapshots=self.snapshots.copy(),duplicate_D0_ADD_snapshots=self.bugs.copy(),transition_returns=self.transitions.copy(),branch_successors=self.branches.copy(),instruction_trace=self.trace.copy(),error=self.error,mmio_writes=0)

def assert_evidence(case,output,result,info,check_carry=True):
    if not info['returned']:return
    if case['entry']==0x192c4:
        if check_carry:assert result['carry']==((result['d7']&65535)==0)
        assert result['d6']>>16==HIGHS[case['profile']][6]>>16 and result['d7']>>16==HIGHS[case['profile']][7]>>16
        if case['family']=='synthetic-flat-signed-band-and-expanded-WORD-wrap':
            base=case['base_x'] if case['kind']>=0x58 else case['base_y'];end=(base+case['extent'])&65535;signed=lambda value:value if value<0x8000 else value-65536;lo,hi=sorted((signed(base),signed(end)))
            assert result['d4']==((lo-1)&65535)<<16 and result['d5']==((hi+1)&65535)<<16
            if base==case['extent']==0:
                axis=0 if case['kind']>=0x58 else 1;points=(case['coords'][axis],case['coords'][axis+2]);masks=[0xff00 if v&0x80000000 else 0xff if v>0x10000 else 0 for v in points]
                assert result['d6']&65535==masks[0] and result['d7']&65535==masks[0]&masks[1]
    else:
        if check_carry:assert not result['carry']
        if case['cursor']:assert info['calls'].get('0x18efa')==2 # No reprojection in transition loop.
        else:assert result['d6']==result['d7']==0
    assert len(info['comparison_snapshots'])==len(info['branch_successors'])
    for sample,branch in zip(info['comparison_snapshots'],info['branch_successors']):
        assert sample['pc']==branch['pc'];pc=sample['pc']
        lhs,rhs,sign=(sample['d7'],sample['d6'],0x80000000) if pc==0x19864 else (sample['d5']&65535,sample['end' if pc==0x1986c else 'start'],0x8000)
        negative=bool((lhs-rhs)&sign);expected=(0x198ae if negative else 0x19868) if pc==0x19864 else (0x198a8 if negative else 0x19870) if pc==0x1986c else (0x198b4 if negative else 0x198e8)
        assert branch['next_pc']==expected
    for sample in info['duplicate_D0_ADD_snapshots']:
        assert sample['after_d3']==(sample['before_d3']+sample['d0'])&0xffffffff
    if case['family']=='synthetic-all36-strip-width-points' and case['kind'] in BUG_PCS:
        assert any(v['d0']!=v['d2'] for v in info['duplicate_D0_ADD_snapshots'])

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);folder=root/'artifacts/scene_motion_pair';folder.mkdir(parents=True,exist_ok=True);secondary='--unicorn' in __import__('sys').argv;oracle=None if secondary else oracle_provenance(root);observer=UnicornObserver(program) if secondary else Observer(program);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case) if prior is None else bytearray(prior[0]);regs=incoming(case,program,ram,None if prior is None else prior[1]);output,result,info=observer.run(case,ram,regs);assert_evidence(case,output,result,info,check_carry=not secondary);file=('unicorn_%04d.bin' if secondary else 'native_%04d.bin')%index;(folder/file).write_bytes(output);rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),input_ram_sha256=sha(ram),result=result,ram_file=file,ram_sha256=sha(output),**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
        if info['error']:break
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources+[metadata]:assert sha((root/item['file']).read_bytes())==item['sha256']
    if not secondary:assert oracle_provenance(root)==oracle
    report=dict(oracle=oracle,carry_is_authoritative=not secondary,source=source,cases=len(cases),completed_cases=sum(r['returned'] for r in rows),results=rows,failure=observer.error,resources=resources,metadata=metadata,program_code_modified=False,scope='Original 192c4/19832 uninterrupted in pinned Musashi through original callees to RTS; full RAM,12 registers and actual CCR.C. Canonical addresses strict. Synthetic native RAM106000 versus C++ MS5D60000 normalizes only outgoing A1 and RAMd3b4. InputA1 authoritative for192c4, RAMcursor authoritative for19832. No ROM patch or callee resets, no MMIO. Controlled point pairs and call carry, not natural movement.')
    if secondary:report['scope']='Uninterrupted original192c4/19832 Unicorn fullRAM/12regs diagnostic; raw returnedSR.C retained as read/stop-resume serialization inconsistency evidence only. No carry correction/ROMpatch/callee reset; independent Musashi is the returnedcarry oracle.'
    path=folder/('unicorn_observation.json' if secondary else 'observation.json');path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
