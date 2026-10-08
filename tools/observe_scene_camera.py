"""Pinned Musashi observations for original19a40/19ac8/full19b96 camera calls."""
import collections
import itertools
import json
from pathlib import Path
import random
import struct
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance,payload
from observe_scene_motion_bounds import resource_items,sha
from observe_scene_motion_time import BASE,STACK,RETURN,SCRATCH,FIXED,HIGHS
from verify_scene_command import KEYS
from verify_stage_catalog import SOURCE_SHA256
ENTRIES=(0x19a40,0x19ac8,0x19b96)
WORD_CONFIGS=((0,0,0,0),(0x7fff,0x7fff,0,0),(0x8000,0x8000,0,0),(0xffff,1,0,0),(0,0x7fff,0x8000,0xffff),(0x8000,0x7fff,0xffff,1),(0x100,0x300,0xa0,0x10),(0x7fff,0x8000,1,0x8000))
LIMITS=(0,1,0x7fffffff,0x80000000,0x80000001,0xffffffff,0x60000,0x7f000000)


def build_cases(root,program):
    resources,metadata=resource_items(root,program);cases=[]
    def add(family,**changes):
        case=dict(family=family,entry=0x19b96,profile=1,cursor=0,relocated=False,base_x=0,base_y=0,time=0,fraction=0,bounds=[0x7fff,0x7fff,0x8000,0x8000],center=[0xa0,0x80],margin=[0,0],speed=[0x60000,0x60000],old_velocity=[0,0],fixed_delta=[0xa0000,0],camera=[0,0],flags=0,force=0,forward_limit=0xffff,backward_limit=0,current_override=None,relative_bounds=False);case.update(changes);cases.append(case)
    for entry,config,limit,old in itertools.product(ENTRIES[:2],WORD_CONFIGS,LIMITS,(0,1,0x7fffffff,0x80000000,0xffffffff)):
        lo,hi,center,margin=config;axis=0 if entry==0x19a40 else 1;bounds=[0,0,0,0];bounds[axis]=lo;bounds[axis+2]=hi;centers=[0,0];centers[axis]=center;margins=[0,0];margins[axis]=margin
        add('axis-WORD-config-LONG-limit-old-velocity',entry=entry,bounds=bounds,center=centers,margin=margins,speed=[limit,limit],old_velocity=[old,old])
    rng=random.Random(0x19b96)
    for entry,index in itertools.product(ENTRIES[:2],range(256)):
        add('axis-deterministic-random-WORD-LONG',entry=entry,profile=index%2,bounds=[rng.randrange(65536) for _ in range(4)],center=[rng.randrange(65536) for _ in range(2)],margin=[rng.randrange(65536) for _ in range(2)],speed=[rng.randrange(1<<32) for _ in range(2)],old_velocity=[rng.randrange(1<<32) for _ in range(2)])
    records=0
    for item in resources:
        for offset in range(0,item['end']-item['cpu']-4,10):
            records+=1;cursor=item['cpu']+offset;time=struct.unpack_from('>H',program,cursor)[0]
            for flags,profile in itertools.product(range(4),range(2)):
                add('canonical-all108-camera-flags',cursor=cursor,path_file=item['file'],time=(time+1)&65535,fraction=profile*0xffff,flags=flags,profile=profile,base_x=0xffff if profile else 0,base_y=0x8000 if profile else 0,bounds=[0x100,0x80,0x200,0x100],old_velocity=[0x10001,0xffff0001],fixed_delta=[0xa1234,0xffff1234])
            for force in (1,0xffff):add('canonical-all108-forced-unsigned-WORD',cursor=cursor,path_file=item['file'],time=time,force=force,flags=3)
    assert records==108
    for kind,flags,profile in itertools.product(range(0,0x90,4),range(4),range(3)):
        add('synthetic-all36-full-camera',cursor=FIXED+10,relocated=True,kind=kind,payload_hex=payload(kind,10).hex(),time=(15,5,35)[profile],fraction=(0,0xffff,0x8000)[profile],flags=flags,bounds=([0x100,0x80,0x200,0x100],[0x2b,0x17,0x114,0xb8],[0x8000,0x7fff,0xffff,1])[profile],speed=[LIMITS[profile+2],LIMITS[profile+2]],fixed_delta=([0xa1234,0],[0xfff51234,0xffff],[0x140000,0xa0000])[profile],base_x=(0,0x7fff,0x8000)[profile],base_y=(0,0x8000,0x7fff)[profile])
    for kind,direction,cap in itertools.product((0x14,0x64),('forward','backward'),(10,20)):
        axis=0 if kind<0x58 else 1;delta=[0,0];delta[axis]=0xa0000 if direction=='forward' else 0xfff60000
        add('synthetic-unsigned-limit-oldtime-fallback',cursor=FIXED+10,relocated=True,kind=kind,payload_hex=payload(kind,10).hex(),time=15,flags=0,fixed_delta=delta,forward_limit=cap if direction=='forward' else 0xffff,backward_limit=cap if direction=='backward' else 0,limit_direction=direction,limit_cap=cap,expected_limited_time=(cap if (direction=='forward' and cap==20) or (direction=='backward' and cap==10) else 15)<<16)
    raw=struct.pack('>5H5H2H',0,0x14,10,0,0,0xff00,0x14,10,0,0,0xffff,0xffff)
    add('synthetic-forced-unsigned-LONG-wrap-still-forward',cursor=FIXED+10,relocated=True,kind=0x14,payload_hex=raw.hex(),time=0xfffe,force=0xffff,forward_limit=0xffff)
    for flags,force,profile in itertools.product(range(4),(0,1,0x7fff,0x8000,0xffff),range(3)):
        add('null-flags-force-and-unsigned-limits',flags=flags,force=force,profile=profile%2,current_override=([0x12340001,0x56780001],[0x1234ffff,0x5678ffff],[0x80000000,0x7fffffff])[profile],forward_limit=(0,0x8000,0xffff)[profile],backward_limit=(0xffff,0x7fff,0)[profile])
    # Null19978 publishes integer-base proposal; fractional current WORD isolates rejection checks.
    for axis,direction,accepted,profile in itertools.product(range(2),('forward','backward'),(False,True),range(2)):
        bounds=[0x100,0x100,0x100,0x100];bounds[axis if direction=='forward' else axis+2]=((0x2c if axis==0 else 0x18)+(0 if accepted else -1)) if direction=='forward' else ((0x114 if axis==0 else 0xb8)+(0 if accepted else 1)) if axis==0 else ((0xb7 if accepted else 0xb8))
        low=0xffff if direction=='forward' else 1;current=[0,0];current[axis]=(low<<16)|0x1234
        add('null-targeted-axis-accept-reject',flags=1<<axis,bounds=bounds,current_override=current,relative_bounds=True,axis=axis,direction=direction,expected_accept=accepted,profile=profile)
    for kind,direction in itertools.product((0x14,0x24,0x64,0x78),(1,-1)):
        for step in range(3):add('actual-cli-camera-carry',sequence=hex(kind)+'-'+str(direction),sequence_position=step,cursor=FIXED+10,relocated=True,kind=kind,payload_hex=payload(kind,10).hex(),time=15,flags=(0,3,1)[step],fixed_delta=[(0xa1234 if direction>0 else 0xfff51234),0x1234],bounds=[0x100,0x100,0x200,0x200],relative_bounds=True)
    assert len(cases)==2773,len(cases)
    return cases,resources,metadata


def fixture(case,program):
    ram=bytearray(__import__('hashlib').shake_256(b'scene-camera'+bytes([case['profile']])).digest(65536));struct.pack_into('>IHH',ram,0xd3b4,case['cursor'],case['base_x'],case['base_y'])
    if case['relocated']:
        raw=bytes.fromhex(case['payload_hex']);ram[SCRATCH-BASE:SCRATCH-BASE+len(raw)]=raw
    coords=case['current_override']
    if coords is None:
        coords=[0,0]
        if case['cursor']:
            raw=bytes.fromhex(case['payload_hex']) if case['relocated'] else program;offset=case['cursor']-FIXED if case['relocated'] else case['cursor'];time,kind=struct.unpack_from('>HH',raw,offset);sign=1 if kind<0x2c or 0x58<=kind<0x74 else -1;axis=0 if kind<0x58 else 1;base=case['base_x'] if axis==0 else case['base_y'];coords[axis]=(((base+sign*((case['time']-time)&65535))&65535)<<16)|case['fraction']
    struct.pack_into('>4I',ram,0xd3bc,*coords,0x12345678,0x87654321)
    prepare(case,ram)
    return ram


def prepare(case,ram):
    bounds=case['bounds'].copy()
    if case['entry']==0x19b96 and case['relative_bounds']:
        x,y=struct.unpack_from('>4I',ram,0xd3bc)[:2]
        for axis,value in enumerate((x,y)):
            delta=((value>>16)+case['camera'][axis])&65535;bounds[axis]=(bounds[axis]+delta)&65535;bounds[axis+2]=(bounds[axis+2]+delta)&65535
    struct.pack_into('>4H',ram,0xd3ce,*bounds);struct.pack_into('>4H',ram,0xd3d6,*case['center'],*case['margin']);struct.pack_into('>4I',ram,0xd3de,*case['old_velocity'],*case['speed']);struct.pack_into('>HH',ram,0xd3ee,case['forward_limit'],case['backward_limit']);struct.pack_into('>H',ram,0xd3fa,case['force']);struct.pack_into('>II',ram,0xd3fc,*case['fixed_delta']);ram[0xd3cc]=case['flags'];struct.pack_into('>H',ram,0xd3a2,case['camera'][0]);struct.pack_into('>H',ram,0xd3a6,case['camera'][1])


class Observer:
    def __init__(self,program):
        self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE]);self.program=program;self.calls=collections.Counter();self.adds=[];self.types=[];self.pending_add=None;self.pending_branch=None;self.y=[];self.predecision=None;self.force=None;self.limit_branches=[];self.pending_limit=None;self.limited=None;self.error=None
        def hook(pc):
            cpu=self.cpu
            if pc in (0x18efa,0x18fd2,0x192c4):self.types.append(int.from_bytes(cpu.read(cpu.get_reg('a1')+2,2),'big'))
            if self.pending_limit is not None:self.limit_branches.append(dict(self.pending_limit,next_pc=pc));self.pending_limit=None
            if pc in (0x19c24,0x19c32,0x19c38,0x19c4e,0x19c54):self.pending_limit=dict(pc=pc,left=cpu.get_reg('d6' if pc in (0x19c38,0x19c54) else 'd7'),right=cpu.get_reg('d6' if pc==0x19c24 else 'd5'))
            if pc==0x19c5c:self.limited=dict(d6=cpu.get_reg('d6'),d7=cpu.get_reg('d7'))
            if self.pending_branch is not None:self.adds.append(dict(self.pending_branch,next_pc=pc));self.pending_branch=None
            if pc in (0x19a40,0x19ac8,0x19b96,0x19802,0x19832,0x19978,0x196ac,0x196de,0x19cd6,0x19ce6,0x19c28,0x19c44,0x19c3e,0x19c5a,0x19c82,0x19c92,0x19cba,0x19cca):self.calls[pc]+=1
            if pc in (0x19aa8,0x19b30):self.pending_add=dict(pc=pc,left=cpu.get_reg('d0'),right=cpu.get_reg('d7'))
            if pc in (0x19aaa,0x19b32):self.pending_branch=dict(self.pending_add,branch_pc=pc,result=cpu.get_reg('d0'));self.pending_add=None
            if pc in (0x19b3c,0x19b40):self.y.append(dict(pc=pc,d7=cpu.get_reg('d7'),RAM_d3e2=int.from_bytes(cpu.read(BASE+0xd3e2,4),'big')))
            if pc==0x19bd6:self.force=dict(d6=cpu.get_reg('d6'),d7=cpu.get_reg('d7'))
            if pc==0x19c60:self.predecision=dict(current=cpu.read(BASE+0xd3bc,8).hex(),proposal=cpu.read(BASE+0xd3c4,8).hex(),cursor=int.from_bytes(cpu.read(BASE+0xd3b4,4),'big'))
        def write(pc,address,size,value):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(pc),hex(address),size,value)
        self.cpu.set_instruction_hook(hook);self.cpu.set_write_hook(write)
    def run(self,case,ram,regs):
        cpu=self.cpu;native=bytearray(ram)
        if case['relocated']:struct.pack_into('>I',native,0xd3b4,SCRATCH+int.from_bytes(native[0xd3b4:0xd3b8],'big')-FIXED)
        cpu.reset();cpu.load(BASE,bytes(native));cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in zip(KEYS,regs):cpu.set_reg(key,value)
        self.calls.clear();self.adds.clear();self.types.clear();self.y.clear();self.pending_add=None;self.pending_branch=None;self.predecision=None;self.force=None;self.limit_branches=[];self.pending_limit=None;self.limited=None;self.error=None;cpu.set_reg('pc',case['entry']);status=cpu.run(200000,RETURN)
        if status['status']!='sentinel':self.error=status
        assert cpu.read(0,BASE)==self.program[:BASE]
        output=bytearray(cpu.read(BASE,65536));result={key:cpu.get_reg(key) for key in KEYS}
        predecision=None if self.predecision is None else self.predecision.copy()
        if case['relocated'] and status['status']=='sentinel':
            result['a1']=result['a1']-SCRATCH+FIXED;struct.pack_into('>I',output,0xd3b4,int.from_bytes(output[0xd3b4:0xd3b8],'big')-SCRATCH+FIXED)
            if predecision is not None:predecision['cursor']=predecision['cursor']-SCRATCH+FIXED
        if status['status']=='sentinel':assert cpu.get_reg('a7')==STACK+4
        return bytes(output),result,dict(returned=status['status']=='sentinel',final_pc=cpu.get_reg('pc'),final_a7=cpu.get_reg('a7'),instructions=status['instructions'],calls={hex(k):v for k,v in self.calls.items()},signed_ADD_branches=self.adds.copy(),observed_motion_types=self.types.copy(),Y_write_before_read=self.y.copy(),predecision=predecision,force_projection=self.force,unsigned_limit_branches=self.limit_branches.copy(),limited_times=self.limited,input_cursor=int.from_bytes(ram[0xd3b4:0xd3b8],'big'),error=self.error,mmio_writes=0)


def assert_evidence(case,output,result,info):
    if not info['returned']:return
    for add in info['signed_ADD_branches']:
        expected=(add['left']+add['right'])&0xffffffff;assert add['result']==expected;overflow=bool((~(add['left']^add['right'])&(add['left']^expected))&0x80000000);negative=bool(expected&0x80000000);taken=not(negative^overflow);assert add['next_pc']==((0x19ab0 if taken else 0x19aae) if add['branch_pc']==0x19aaa else (0x19b38 if taken else 0x19b36))
    for branch in info['unsigned_limit_branches']:
        pc=branch['pc'];below=branch['left']<branch['right'];targets={0x19c24:(0x19c44,0x19c28),0x19c32:(0x19c40,0x19c36),0x19c38:(0x19c3e,0x19c3c),0x19c4e:(0x19c52,0x19c5c),0x19c54:(0x19c58,0x19c5a)};assert branch['next_pc']==targets[pc][0 if below else 1]
    if case['family']=='synthetic-unsigned-limit-oldtime-fallback':assert info['limited_times']==dict(d6=15<<16,d7=case['expected_limited_time'])
    if case['family']=='synthetic-forced-unsigned-LONG-wrap-still-forward':assert info['force_projection']==dict(d6=0xfffe0000,d7=0x00fdff00) and info['calls'].get('0x19c28')==1 and not info['calls'].get('0x19c44')
    if info['Y_write_before_read']:
        assert len(info['Y_write_before_read'])==2;before,after=info['Y_write_before_read'];assert before['d7']==before['RAM_d3e2']==after['RAM_d3e2'] and after['d7']==0
    if case['entry']==0x19b96:
        assert info['calls'].get('0x19978')==1 and struct.unpack_from('>4H',output,0xd3ce)==(0x7fff,0x7fff,0x8000,0x8000)
        if case['force']:
            assert info['calls'].get('0x19802')==1 and not info['calls'].get('0x19832');assert info['force_projection']['d7']==(info['force_projection']['d6']+(case['force']<<8))&0xffffffff
        else:assert info['calls'].get('0x19832')==1
        state=info['predecision'];assert state is not None
        if info['calls'].get('0x19ce6'):
            assert output[0xd3bc:0xd3c4].hex()==state['current'] and output[0xd3c4:0xd3cc].hex()==state['proposal'] and int.from_bytes(output[0xd3b4:0xd3b8],'big')==state['cursor'] and output[0xd3de:0xd3e6]==bytes(8)
        else:assert output[0xd3bc:0xd3c4].hex()==state['proposal']
        if case['family']=='null-targeted-axis-accept-reject':assert bool(info['calls'].get('0x19cd6'))==case['expected_accept']


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);oracle=oracle_provenance(root);observer=Observer(program);folder=root/'artifacts/scene_camera';folder.mkdir(parents=True,exist_ok=True);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case,program) if prior is None else bytearray(prior[0]);prepare(case,ram);regs=list(HIGHS[case['profile']] if prior is None else prior[1]);output,result,info=observer.run(case,ram,regs);assert_evidence(case,output,result,info);name='native_%04d.bin'%index;(folder/name).write_bytes(output);rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),input_ram_sha256=sha(ram),result=result,ram_file=name,ram_sha256=sha(output),**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[key] for key in KEYS])
        if info['error']:break
    assert oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources+[metadata]:assert sha((root/item['file']).read_bytes())==item['sha256']
    report=dict(source=source,oracle=oracle,cases=len(cases),completed_cases=sum(row['returned'] for row in rows),failure=observer.error,results=rows,resources=resources,metadata=metadata,program_code_modified=False,scope='Unpatched original19a40/19ac8/19b96 in pinnedMusashi continuously toRTS, full64KiBRAM/12regs, A7+4, zeroMMIO, CPUwrite guard. Canonicalfixedaddresses strict; syntheticmotion nativeRAM106000 versusC++exactMS5D60000 normalizesonlyA1/RAMd3b4. Controlled axes/fullcamera paths, unsignedforcedWORD andlimits, signedADDoverflow, Ystore-before-read, retainedproposal/cursor onrejection. ActualCLI carry usespriorRAM/12regs with explicit host updates to bounds, centers, margins, speed limits, old velocities, phase limits, force, fixed deltas, flags and camera WORDs eachcall. RemainingRAM/12regs carry; no naturalframe or velocitycarry claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
