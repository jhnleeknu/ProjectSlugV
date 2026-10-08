"""Uninterrupted original M68000 calls for the eighteen confirmed input callbacks."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from pack_stage_input import build as pack_build,SOURCE_SHA256

BASE,STACK,RETURN=0x100000,0x1feffc,0xff000
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
ENTRIES=(0x49d88,0x49de6,0x49e34,0x49e38,0x49e9c,0x49eba,0x49ef0,0x49f2c,0x49f66,0x1bec0,0x1d5ac,0x1d5e2,0x1d61a,0x1d628,0x1d664,0x1d6c2,0x1d8cc,0xe73f2)
PAIRS=((-1,-1),(1,1),(0,0),(1,-1),(-1,1),(-32768,32767),(32767,-32768),(-32768,-32768),(32767,32767),(0,1),(0,-1),(1,0),(-1,0))
WORDS=(0,1,0x7fff,0x8000,0xffff)
CAMERAS=(0,1,0xffff0001,0x7fffffff,0x80000000)
BRANCHES=(0x49da0,0x49dba,0x49dd0,0x49dd4,0x49dec,0x49e16,0x49e1e,0x49e24,0x49e4e,0x49e64,0x49e6c,0x49e76,0x49e86,0x49e8a,0x49eaa,0x49ec2,0x49ece,0x49ef8,0x49f04,0x49f22,0x49f3a,0x49f4e,0x49f54,0x49f6e,0x49f7c,0x1bec6,0x1bed0,0x1d5b2,0x1d5e8,0x1d5f2,0x1d620,0x1d672,0x1d676,0x1d694,0x1d6d0,0x1d6d6,0x1d6f4,0x48374)
CALLEES=(0x49c20,0x49c32,0x49c66,0x49ab4,0x4836e)


def sha(data):return hashlib.sha256(data).hexdigest()

def provenance(root):
    files,_=pack_build(root);items=[]
    for name,data in sorted(files.items()):
        path=root/'extracted/runtime/stage_input'/name;assert path.read_bytes()==data;items.append(dict(file=str(path.relative_to(root)),sha256=sha(data)))
    for name in ('build/step_stage_input_callback','engine/src/stage_input_callback.cpp','engine/include/ms5/stage_input_callback.h','engine/tools/step_stage_input_callback.cpp','engine/src/stage_input.cpp','engine/include/ms5/stage_input.h','engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','tools/observe_stage_input_callback.py','tools/verify_stage_input_callback.py','tools/pack_stage_input.py'):
        items.append(dict(file=name,sha256=sha((root/name).read_bytes())))
    return items


def build_cases():
    cases=[]
    def add(family,entry,**changes):
        index=len(cases);case=dict(family=family,entry=entry,profile=1,object=0x100cb8,parent=0x106800,slot=0,flag=0x80,flag_a7=0,current=1,previous=1,target=WORDS[index%5],camera=CAMERAS[index%5],old_camera=CAMERAS[(index+2)%5],camera_y=CAMERAS[(index+1)%5],fraction=(0,1,0x8000,0xffff)[index%4],absolute_memory=0x270e,latch=0,state740=0,state741=0,parent_word=0,inhibit=0,held=0xff,edge=0xff,global_word=0xabcd,register_overrides={});case.update(changes);cases.append(case)
    for entry,pair,slot,profile in itertools.product((0x49d88,0x49de6,0x49e9c,0x49eba,0x49ef0),PAIRS,(0,1,2,0xffff),range(2)):
        add('LONG-projection-signed-XOR-cross-target-and-slot',entry,current=pair[0],previous=pair[1],slot=slot,profile=profile)
    for entry,obj,absolute,latch,current,profile in itertools.product((0x49eba,0x49ef0),(0x100cb8,0x100da8,0x106000),('object','first-address','marker','allones'),(0,1,2,3,0xff),(0,1,-1),range(2)):
        value=obj if absolute=='object' else 0x100cb8 if absolute=='first-address' else 0x270e if absolute=='marker' else 0xffffffff
        add('absolute-memory-CMPA-latch-save-restore',entry,object=obj,absolute_memory=value,latch=latch,current=current,previous=current,profile=profile,absolute_mode=absolute)
    for pair,slot,flag,profile in itertools.product(PAIRS,(0,1,2,0xffff),(0,1,0x80,0x81),range(2)):
        add('WORD-projection-cross-arrival-flag-tail-setter',0x49e38,current=pair[0],previous=pair[1],slot=slot,flag=flag,profile=profile)
    for entry,pair,slot,profile in itertools.product((0x1d664,0x1d6c2),PAIRS,(0,1,2,0xffff),range(2)):
        add('WORD-same-camera-previous-XOR-axis-stop',entry,current=pair[0],previous=pair[1],slot=slot,profile=profile)
    for slot,obj,edge,profile in itertools.product((0,1,2,0xffff),(0x100cb8,0x100da8,0x106000),(0,1,0x30,0x80,0xff),range(2)):
        add('setter-clears-A0-before-default-mapping',0x1d628,slot=slot,object=obj,edge=edge,profile=profile)
    for flag,states,slot,profile in itertools.product((0,1,0x80,0x81),((0,0),(1,0),(0,0xff),(0xff,0xff)),(0,1,2,0xffff),range(2)):
        add('flag-bit0-state-byte-SNE-XOR',0x49f2c,flag=flag,state740=states[0],state741=states[1],slot=slot,profile=profile)
    for held,edge,obj,profile in itertools.product((0,1,0xf,0x10,0x30,0x80,0xff),(0,1,0x30,0x80,0xff),(0x100cb8,0x100da8,0x106000),range(2)):
        add('immediate-address-player-mapping-and-upper-bytes',0x49f66,held=held,edge=edge,object=obj,profile=profile)
    for flag,flag_a7,held,obj,profile in itertools.product((0,1,0x80,0x81),(0,0x7f,0x80,0xff),(0,0xff),(0x100cb8,0x100da8,0x106000),range(2)):
        add('object15-a7-bit7-shortcircuit-low-nibble',0x1bec0,flag=flag,flag_a7=flag_a7,held=held,object=obj,profile=profile)
    for inhibit,slot,profile,obj in itertools.product((0,1,4,0xff),(0,1,2,0xffff),range(2),(0x100cb8,0x100da8,0x106000)):
        add('global-bit2-carry-setter-side-effect',0x1d5ac,inhibit=inhibit,slot=slot,profile=profile,object=obj)
    for flag,parent_word,slot,profile in itertools.product((0,1,0x80,0x81),(0,1,0x7fff,0x8000,0x8001,0xfffe,0xffff),(0,1,2,0xffff),range(2)):
        add('A6-plus3a-signed-WORD-and-flag-gating',0x1d5e2,flag=flag,parent_word=parent_word,slot=slot,profile=profile)
    for flag,slot,profile in itertools.product((0,1,0x80,0x81),(0,1,2,0xffff),range(2)):
        add('flag7-clear-or-setter-mapper',0x1d61a,flag=flag,slot=slot,profile=profile)
    for entry,profile,pointer in itertools.product((0x49e34,0x1d8cc),range(3),(0,1,0xdeadbeef,0xffffffff)):
        add('noop-or-clear-unused-invalid-addresses',entry,profile=profile,register_overrides={'a0':pointer,'a6':pointer})
    for value,profile in itertools.product((0,1,0x7fff,0x8000,0x8001,0xfffe,0xffff),range(3)):
        add('global-WORD-D7-high-preserved',0xe73f2,global_word=value,profile=profile)
    for obj,profile in itertools.product((0x100cb8,0x100da8),range(2)):
        for step,entry in enumerate((0x49eba,0x49ef0,0x49e9c,0x1d628,0x49f66,0x49e34,0xe73f2,0x1d8cc)):
            add('actual-CLI-output-callback-sequence',entry,object=obj,profile=profile,sequence=hex(obj)+'-'+str(profile),sequence_position=step,current=1,previous=1)
    assert len(cases)==2943,len(cases)
    assert {c['entry'] for c in cases}==set(ENTRIES)
    return cases


def fixture(case):
    ram=bytearray(hashlib.shake_256(b'stage-input-callback'+bytes([case['profile']])).digest(65536));profile=case['profile'];regs=[0]*14 if profile==0 else [0xffffffff]*14 if profile==2 else [(0x89abcdef+i*0x1020304)&0xffffffff for i in range(14)]
    regs[1]=(regs[1]&0xffffff00)|case['edge'];regs[8]=case['object'];regs[13]=case['parent'];obj=case['object']-BASE;slot=case['slot'];target=case['target'] if slot==0 else case['target']^0x55aa;camera=case['camera'];old=case['old_camera'];camy=case['camera_y'];fraction=case['fraction']
    struct.pack_into('>IIII',ram,0xd3a2,camera,camy,old,old^0xffffffff)
    if case['entry'] in (0x49e38,0x1d664,0x1d6c2):
        if case['entry'] in (0x1d664,0x1d6c2):target=case['target'];old=camera
        current=(((camera>>16)+target+case['current'])&65535)<<16|fraction;previous=(((old>>16)+target+case['previous'])&65535)<<16|(fraction^0xffff)
    else:current=(camera+(((target+case['current'])&65535)<<16)+fraction)&0xffffffff;previous=(old+(((target+case['previous'])&65535)<<16)+(fraction^0xffff))&0xffffffff
    ycurrent=(((camy>>16)+case['target']+case['current'])&65535)<<16|fraction;yprevious=(((camy>>16)+case['target']+case['previous'])&65535)<<16|(fraction^0xffff)
    struct.pack_into('>IIII',ram,obj+0x42,current,ycurrent,previous,yprevious);struct.pack_into('>H',ram,obj+0x78,slot);struct.pack_into('>H',ram,obj+0xae,case['target']);ram[obj+0x15]=case['flag'];ram[obj+0xa7]=case['flag_a7'];struct.pack_into('>H',ram,case['parent']-BASE+0x3a,case['parent_word']);struct.pack_into('>HH',ram,0xd73c,case['target'],case['target']^0x55aa);ram[0xd732]=case['latch'];ram[0xd740]=case['state740'];ram[0xd741]=case['state741'];ram[0xd683]=case['inhibit'];ram[0x4caa]=case['held'];ram[0x4cb0]=case['held']^0xa5;struct.pack_into('>H',ram,0xde24,case['global_word']);struct.pack_into('>I',ram,0xcb8,case['absolute_memory'])
    for key,value in case['register_overrides'].items():regs[KEYS.index(key)]=value
    return ram,regs


class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE]);self.calls=collections.Counter();self.branches=[];self.pending=None;self.writes=[];self.mapping_inputs=[]
        def instruction(pc):
            cpu=self.cpu
            if self.pending is not None:self.branches.append(dict(pc=self.pending,next_pc=pc));self.pending=None
            if pc in BRANCHES:self.pending=pc
            if pc in ENTRIES+CALLEES:self.calls[pc]+=1
            if pc==0x49f66:self.mapping_inputs.append(dict(a0=cpu.get_reg('a0'),d0=cpu.get_reg('d0'),d1=cpu.get_reg('d1')))
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(pc),hex(address),size,value)
            if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(instruction);self.cpu.set_write_hook(write)
    def run(self,entry,ram,regs):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,bytes(ram));cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in zip(KEYS,regs):cpu.set_reg(key,value)
        self.calls.clear();self.branches.clear();self.pending=None;self.writes.clear();self.mapping_inputs.clear();cpu.set_reg('pc',entry);status=cpu.run(2000,RETURN);assert status['status']=='sentinel' and cpu.get_reg('a7')==STACK+4,status;assert cpu.read(0,BASE)==self.program[:BASE];output=cpu.read(BASE,65536);result={key:cpu.get_reg(key) for key in KEYS}
        return output,result,dict(returned=True,final_pc=RETURN,final_a7=STACK+4,instructions=status['instructions'],calls={hex(pc):count for pc,count in self.calls.items()},branch_successors=self.branches.copy(),RAM_writes=self.writes.copy(),mapping_inputs=self.mapping_inputs.copy(),mmio_writes=0)


def assert_evidence(case,ram,output,result,info,regs):
    entry=case['entry'];assert result['a6']==regs[13]
    assert all(w['address'] in (0x10d732,0x10d734,0x10d738) for w in info['RAM_writes'])
    if entry==0x1d8cc:assert output==ram and result==dict(zip(KEYS,regs))
    if entry==0x49e34:assert output==ram and result==dict(dict(zip(KEYS,regs)),d7=0)
    if entry==0xe73f2:assert result==dict(dict(zip(KEYS,regs)),d7=(regs[7]&0xffff0000)|int.from_bytes(ram[0xde24:0xde26],'big')) and output==ram
    if info['calls'].get('0x1d628'):
        assert info['mapping_inputs'] and all(m['a0']==0 for m in info['mapping_inputs']) and result['a0']==0
    if entry==0x49eba:assert not result['d7']&0x20
    if entry==0x49ef0 and not (ram[0xd732]&(1<<(0 if int.from_bytes(ram[0xcb8:0xcbc],'big')==regs[8] else 1))):
        index=0 if int.from_bytes(ram[0xcb8:0xcbc],'big')==regs[8] else 1;assert result['d1']==(regs[0]&0xffffff00)|index
    if entry==0x1d5e2 and not ram[regs[8]-BASE+0x15]&0x80:assert result['d7']==(0 if int.from_bytes(ram[regs[13]-BASE+0x3a:regs[13]-BASE+0x3c],'big')&0x8000 else 8)


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases=build_cases();inputs=provenance(root);oracle=oracle_provenance(root);observer=Observer(program);folder=root/'artifacts/stage_input_callback';folder.mkdir(parents=True,exist_ok=True);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram,regs=fixture(case) if prior is None else (bytearray(prior[0]),prior[1].copy());output,result,info=observer.run(case['entry'],ram,regs);assert_evidence(case,ram,output,result,info,regs);name='native_%04d.bin'%index;(folder/name).write_bytes(output);rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),input_ram_sha256=sha(ram),result=result,ram_file=name,ram_sha256=sha(output),**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[key] for key in KEYS])
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(cases),completed_cases=len(rows),results=rows,failure=None,program_code_modified=False,counts_by_entry=dict(sorted(collections.Counter(c['entry'] for c in cases).items())),scope='Eighteen confirmed callback entries run continuously to native RTS in pinned Musashi M68000, original fixed ROM unchanged, no patches/stubs/in-call reset. Full64KiB RAM and14 exposed registers including A6; RAM/stack write guard and zero MMIO. Original four-byte default mask source/container/manifest checked by regeneration. Explicit object/camera/target/flag/latch/player fixtures; absolute-memory CMPA is distinct from immediate-address comparison. Four actual-output eight-call sequences carry allRAM/14registers without host writes. No full49b0c/dynamic-callback dispatcher/scheduler/CCR claim; 1da60/4d7a6 excluded.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
