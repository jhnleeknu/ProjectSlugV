"""Original motion extent/clamp/envelope helpers, strict and relocated RAM data."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_scene_command import REGS, KEYS
from verify_stage_catalog import SOURCE_SHA256, checked_resource
from observe_scene_motion_time import HIGHS
BASE,STACK,RETURN,SCRATCH,FIXED=0x100000,0x1feffc,0xff000,0x106000,0x60000
ENTRIES=(0x198ee,0x19978,0x19d98,0x19d08)
WORDS=(0,1,0x7fff,0x8000,0xffff)

def sha(data):return hashlib.sha256(data).hexdigest()
def resource_items(root,program):
    manifest_path=root/'extracted/runtime/scene_scripts/manifest.json';manifest=json.loads(manifest_path.read_text());assert manifest['source']['sha256']==SOURCE_SHA256;items=[]
    for item in manifest['dependencies']:
        if not item['file'].startswith('motion_'):continue
        path=manifest_path.parent/item['file'];digest=checked_resource(path,program,item['source_cpu_address'],item['end_exclusive']);assert digest==item['sha256'];items.append(dict(file=str(path.relative_to(root)),cpu=item['source_cpu_address'],end=item['end_exclusive'],sha256=digest))
    assert len(items)==37
    return items,dict(file=str(manifest_path.relative_to(root)),sha256=sha(manifest_path.read_bytes()))

def synthetic_payload(kind,extent):
    return b''.join(struct.pack('>5H',time,k,ext,x,y) for time,k,ext,x,y in ((0,0x14,10,0xffff,0x8000),(10,kind,extent,0x7fff,0xffff),(20,0x14,10,0x8000,1)))+struct.pack('>2H',30,0xffff)

def build_cases(root,program):
    items,metadata=resource_items(root,program);cases=[]
    def add(family,**changes):
        c=dict(family=family,entry=0x198ee,profile=1,cursor=0,target=0,fraction=0,base_x=0,base_y=0,point_x=0,point_y=0,camera_x=0,camera_y=0,phase=0,lower_time=0,upper_time=0xffff,clip_x=0,clip_y=0,bounds=[0x7fff,0x8000,0x7fff,0x8000],relocated=False);c.update(changes);cases.append(c)
    for item in items:
        terminal=struct.unpack_from('>H',program,item['end']-4)[0]
        for entry,target,profile in itertools.product(ENTRIES,sorted({0,1,(terminal-1)&65535}),range(2)):
            add('canonical37-all-four-entries-time-boundaries',entry=entry,target=target,phase=target,fraction=(0,0xffff)[profile],profile=profile,cursor=item['cpu'],path_file=item['file'],base_x=(0,0x7fff)[profile],base_y=(0,0x8000)[profile],clip_x=(0,0x7fffffff)[profile],clip_y=(0,0x80000000)[profile])
    canonical_count=len(cases)
    for entry,x,y,profile in itertools.product(ENTRIES,WORDS,WORDS,range(2)):
        add('null-base-signed-WORD-boundaries',entry=entry,base_x=x,base_y=y,camera_x=x,camera_y=y,profile=profile,target=0x8000,phase=0xffff)
    for kind,extent,entry,fraction in itertools.product(range(0,0x90,4),WORDS,ENTRIES,(0,0x8000,0xffff)):
        add('synthetic-all36-types-five-extents-fractions',entry=entry,target=15,phase=15,fraction=fraction,cursor=FIXED+10,relocated=True,kind=kind,extent=extent,payload_hex=synthetic_payload(kind,extent).hex(),base_x=0x7fff,base_y=0x8000,clip_x=0x7fffffff,clip_y=0x80000001)
    for kind,entry,target in itertools.product(range(0,0x90,4),ENTRIES,(9,21)):
        add('synthetic-all36-forward-backward-selection',entry=entry,target=target,phase=target,fraction=1,cursor=FIXED+10,relocated=True,kind=kind,extent=0xffff,payload_hex=synthetic_payload(kind,0xffff).hex(),base_x=0xffff,base_y=0x8000)
    for axis,polarity,entry,current in itertools.product(('x','y'),('positive','negative'),(0x19978,0x19d98),(0,0x7fffffff,0x80000000,0xffffffff,0xffff0000)):
        base=0x7fff if polarity=='positive' else 0x8000;extent=1 if polarity=='positive' else 0xffff;kind=0x6c if axis=='x' else 0x14
        add('N-only-LONG-vs-signed-WORD-overflow',entry=entry,target=10,phase=10,cursor=FIXED+10,relocated=True,kind=kind,extent=extent,payload_hex=synthetic_payload(kind,extent).hex(),base_x=base if axis=='x' else 0,base_y=base if axis=='y' else 0,clip_x=current,clip_y=current,axis=axis,polarity=polarity,bounds=[0x8000,0x7fff,0x8000,0x7fff])
    for axis,polarity in itertools.product(('x','y'),('positive','negative','prior-add-only')):
        delta=0x140 if axis=='x' else 0x100;base=1 if polarity=='positive' else 0xffff if polarity=='negative' else 0x7fff;camera=(0x7fff-delta)&65535 if polarity=='positive' else (0x8000-delta)&65535 if polarity=='negative' else 0x7fff
        add('19d08-only-last-ADD-overflow-saturation',entry=0x19d08,axis=axis,polarity=polarity,base_x=base if axis=='x' else 0,base_y=base if axis=='y' else 0,camera_x=camera if axis=='x' else 0,camera_y=camera if axis=='y' else 0,phase=1)
    for kind,(target,phase,lower,upper) in itertools.product((0x14,0x40,0x6c,0x84),((5,10,12,3),(20,5,3,25),(0x8000,0xffff,0x8000,0x7fff),(0xffff,0x8000,0xffff,1))):
        add('19d08-distinct-unsigned-clamps-and-stack-restore',entry=0x19d08,target=target,phase=phase,lower_time=lower,upper_time=upper,fraction=0x8000,cursor=FIXED+10,relocated=True,kind=kind,extent=0xffff,payload_hex=synthetic_payload(kind,0xffff).hex(),base_x=0x7fff,base_y=0x8000)
    for item in (items[0],items[3]):
        for profile in range(2):
            sequence=item['file']+'-'+str(profile)
            for step,entry in enumerate(ENTRIES):add('actual-cli-carry-four-helper-chain',entry=entry,cursor=item['cpu'],path_file=item['file'],target=(0,1,1,0)[step],phase=1,profile=profile,sequence=sequence,sequence_position=step)
    assert canonical_count==len([c for c in cases if c['family']=='canonical37-all-four-entries-time-boundaries'])
    assert len(cases)==3606, len(cases)
    return cases,items,metadata

def fixture(case):
    ram=bytearray(hashlib.shake_256(b'motion-bounds'+bytes([case['profile']])).digest(65536));struct.pack_into('>IHH',ram,0xd3b4,case['cursor'],case['base_x'],case['base_y']);struct.pack_into('>II',ram,0xd3c4,case['clip_x'],case['clip_y']);struct.pack_into('>4H',ram,0xd3f2,*case['bounds']);struct.pack_into('>HH',ram,0xd3ee,case['lower_time'],case['upper_time']);struct.pack_into('>H',ram,0xd418,case['phase']);struct.pack_into('>H',ram,0xd3a2,case['camera_x']);struct.pack_into('>H',ram,0xd3a6,case['camera_y'])
    if case['relocated']:
        raw=bytes.fromhex(case['payload_hex']);ram[SCRATCH-BASE:SCRATCH-BASE+len(raw)]=raw
    return ram

def values(case,program,ram,prior=None):
    vals=list(HIGHS[case['profile']] if prior is None else prior)
    vals[7]=((case['target']<<16)|case['fraction']) if case['entry'] in (0x198ee,0x19978) else ((vals[7]&0xffff0000)|case['target'])
    if case['entry']==0x19d08:
        cursor=int.from_bytes(ram[0xd3b4:0xd3b8],'big');x,y=0,0
        if cursor:
            raw=bytes.fromhex(case['payload_hex']) if case['relocated'] else program;offset=cursor-FIXED if case['relocated'] else cursor;time,kind=struct.unpack_from('>HH',raw,offset);difference=(case['target']-time)&65535;base_x,base_y=struct.unpack_from('>HH',ram,0xd3b8)
            sign=1 if kind<0x2c or 0x58<=kind<0x74 else -1;coord=((((base_x if kind<0x58 else base_y)+sign*difference)&65535)<<16)|case['fraction']
            if kind<0x58:x=coord
            else:y=coord
        struct.pack_into('>II',ram,0xd3bc,x,y)
    return vals

class Observer:
    def __init__(self,program):
        self.cpu=make_cpu(program);self.baseline=self.cpu.context_save();self.program=program;self.calls=collections.Counter();self.types=[];self.snapshots=[];self.times=[];self.saved_time=None;self.error=None
        def code(cpu,address,size,user):
            if address==RETURN:cpu.emu_stop();return
            if address in (0x198ee,0x19978,0x19d98,0x19d08,0x19802,0x1972a,0x196ac,0x196de,0x18fd2,0x18c06,0x19996,0x199b8,0x19db2,0x19dba,0x19d72,0x19d8e,0x19dc0,0x19dc4,0x19dcc,0x19dd0,0x19dd8,0x19ddc,0x19de4,0x19de8):self.calls[address]+=1
            if address==0x19d30:self.saved_time=cpu.reg_read(REGS[7])&65535
            if address==0x19d98:self.times.append(cpu.reg_read(REGS[7])&65535)
            if address==0x18fd2:self.types.append(int.from_bytes(cpu.mem_read(cpu.reg_read(m.UC_M68K_REG_A1)+2,2),'big'))
            if address in (0x19992,0x199b4,0x19dae,0x19db6):self.snapshots.append(dict(pc=address,d0=cpu.reg_read(REGS[0])&0xffffffff,d1=cpu.reg_read(REGS[1])&0xffffffff,d2=cpu.reg_read(REGS[2])&0xffffffff,d3=cpu.reg_read(REGS[3])&0xffffffff))
        def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,case,ram,regs):
        native=bytearray(ram)
        if case['relocated']:
            cursor=int.from_bytes(native[0xd3b4:0xd3b8],'big');struct.pack_into('>I',native,0xd3b4,SCRATCH+cursor-FIXED)
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(native));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(REGS,regs):cpu.reg_write(register,value)
        self.calls.clear();self.types.clear();self.snapshots.clear();self.times.clear();self.saved_time=None;self.error=None
        try:cpu.emu_start(case['entry'],0xffffff,count=200000)
        except unicorn.UcError as e:self.error=dict(kind='emulator-error',error=str(e),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=RETURN and self.error is None:self.error=dict(kind='instruction-cap',pc=pc)
        assert bytes(cpu.mem_read(0,0x100000))==self.program[:0x100000]
        output=bytearray(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(register)&0xffffffff for register in REGS)))
        if case['relocated'] and pc==RETURN:
            struct.pack_into('>I',output,0xd3b4,int.from_bytes(output[0xd3b4:0xd3b8],'big')-SCRATCH+FIXED);result['a1']=result['a1']-SCRATCH+FIXED
        if pc==RETURN:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        info=dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),calls={hex(k):v for k,v in self.calls.items()},observed_types=self.types.copy(),compare_snapshots=self.snapshots.copy(),envelope_times=self.times.copy(),saved_time=self.saved_time,error=self.error,mmio_writes=0)
        return bytes(output),result,info

def assert_evidence(case,output,result,info):
    if not info['returned']:return
    if case['family']=='synthetic-all36-types-five-extents-fractions' and case['entry']==0x198ee:
        assert case['kind'] in info['observed_types'];axis='d3' if case['kind']<0x58 else 'd2';other='d2' if axis=='d3' else 'd3';assert result[axis]==case['extent']<<16 and result[other]==0
    if case['entry']==0x19d08:
        assert info['calls'].get('0x198ee')==2 and info['calls'].get('0x19802')==1
        saved=info['saved_time'];assert info['envelope_times']==[max(saved,min(case['phase'],case['lower_time'])),min(saved,case['upper_time'])]
        if case['family']=='19d08-distinct-unsigned-clamps-and-stack-restore' and case['target']==5:assert info['envelope_times']==[10,3]
    if case['family']=='N-only-LONG-vs-signed-WORD-overflow':
        axis=case['axis'];positive=case['polarity']=='positive'
        bits=32 if case['entry']==0x19978 else 16;mask=(1<<bits)-1;sign=1<<(bits-1)
        pc=(0x199b4 if axis=='x' else 0x19992) if bits==32 else (0x19dae if axis=='x' else 0x19db6)
        snapshot=next(v for v in info['compare_snapshots'] if v['pc']==pc);lhs=snapshot['d2' if axis=='x' else 'd3']&mask;rhs=snapshot['d0' if axis=='x' else 'd1']&mask;difference=(lhs-rhs)&mask
        assert ((lhs^rhs)&(lhs^difference)&sign)!=0, (case,snapshot) # CMP signed overflow is actually present.
        assert bool(difference&sign)==(not positive)
        if case['entry']==0x19978:
            assert (info['calls'].get('0x199b8' if axis=='x' else '0x19996',0)>0)==(not positive)
        else:assert (info['calls'].get('0x19db2' if axis=='x' else '0x19dba',0)>0)==positive
    if case['family']=='19d08-only-last-ADD-overflow-saturation':
        pc='0x19d72' if case['axis']=='x' else '0x19d8e';assert (info['calls'].get(pc,0)>0)==(case['polarity']!='prior-add-only')
        if case['polarity']!='prior-add-only':assert int.from_bytes(output[0xd3f4 if case['axis']=='x' else 0xd3f8:0xd3f6 if case['axis']=='x' else 0xd3fa],'big')==0x7fff

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/scene_motion_bounds';folder.mkdir(parents=True,exist_ok=True);cases,resources,metadata=build_cases(root,program);observer=Observer(program);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case) if prior is None else bytearray(prior[0]);struct.pack_into('>H',ram,0xd418,case['phase']);regs=values(case,program,ram,None if prior is None else prior[1]);output,result,info=observer.run(case,ram,regs);assert_evidence(case,output,result,info)
        rf='native_%04d.bin'%index;(folder/rf).write_bytes(output);rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),result=result,input_ram_sha256=sha(ram),ram_file=rf,ram_sha256=sha(output),**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
        if info['error']:break
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources+[metadata]:assert sha((root/item['file']).read_bytes())==item['sha256']
    report=dict(source=source,cases=len(cases),completed_cases=sum(r['returned'] for r in rows),results=rows,failure=observer.error,resources=resources,metadata=metadata,program_code_modified=False,scope='Original198ee/19978/19d98/19d08 uninterrupted throughoriginal motion/time callees toRTS. Canonical strictaddresses. Syntheticdata nativeRAM106000/CPPMS5D60000 withsame scratchbytes; normalizeonlyoutgoingA1 andRAMd3b4. NoROMpatch/contextresetinsidecallee/MMIO. CompleteRAM12regs; controlled time/base/camera/extent/bounds inputs, notnatural frames orCCR claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
