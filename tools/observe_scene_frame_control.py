"""Pinned original condition/rectangle/duration/settings/shake observations."""
import collections
import itertools
import json
from pathlib import Path
import random
import struct
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from observe_scene_motion_bounds import sha,resource_items
from observe_scene_motion_time import BASE,STACK,RETURN,HIGHS
from verify_scene_command import KEYS
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from inventory_scene_conditions import inventory
ENTRIES=(0x1a2b4,0x1a34c,0x1a29e,0x1a526,0x1a3d6)
COND,RECT,DURATION=0x106000,0x106100,0x106200
OBJECTS=(0x100cb8,0x100da8)
WORDS=(0,1,0x7fff,0x8000,0xffff)
BRANCHES=(0x1a352,0x1a362,0x1a380,0x1a386,0x1a390,0x1a396,0x1a3f2,0x1a3fc,0x1a534,0x1a540,0x1a55a,0x1a57a,0x1a596)


def inputs(root,program):
    path=root/'artifacts/scene_condition_inventory.json';raw=path.read_bytes();data=json.loads(raw);assert data==inventory(root) and data['source']['sha256']==SOURCE_SHA256 and len(data['conditions'])==9
    manifest_path=root/'extracted/runtime/scene_scripts/manifest.json';manifest=json.loads(manifest_path.read_text());resources=[]
    for item in manifest['scripts']:
        file=manifest_path.parent/item['file'];digest=checked_resource(file,program,item['source_cpu_address'],item['end_exclusive']);assert digest==item['sha256'];resources.append(dict(file=str(file.relative_to(root)),cpu=item['source_cpu_address'],end=item['end_exclusive'],sha256=digest))
    motions,metadata=resource_items(root,program);resources+=motions;assert len(resources)==78
    return data,resources,dict(condition_inventory_file=str(path.relative_to(root)),condition_inventory_sha256=sha(raw),script_manifest=metadata)


def build_cases(root,program):
    catalog,resources,metadata=inputs(root,program);cases=[]
    def add(family,**changes):
        case=dict(family=family,entry=0x1a2b4,profile=1,condition=COND,condition_hex=struct.pack('>HH',0,0x1234).hex(),rectangle=RECT,rectangle_hex=struct.pack('>II',0,0xa000a).hex(),motion=0,motion_hex=None,motion_data_address=DURATION,players=[dict(callback=0x1234,flag=0x80,x=1,y=1),dict(callback=0x1234,flag=0x80,x=1,y=1)],camera=[0,0],enabled=1,phase=0,threshold=1,duration_end=0x1234,force=0x4321,settings=None,shake=0,old_shake=0xabcd,files=[]);case.update(changes);cases.append(case)
    for item in catalog['conditions']:
        payload=bytes.fromhex(item['inline_raw_hex']);start,size=struct.unpack_from('>II',payload,2);end=(start+size)&0xffffffff;x,y=start>>16,start&65535;outside=end&65535;script=next(r for r in resources if r['cpu']==item['script_cpu_address'])
        for mode,profile in itertools.product(('inside','first-outside','second-outside','both-inactive','first-flag-off','disabled'),range(2)):
            players=[dict(callback=0x1234,flag=0x80,x=x,y=y),dict(callback=0x1234,flag=0x80,x=x,y=y)]
            if mode=='first-outside':players[0]['y']=outside
            if mode=='second-outside':players[1]['y']=outside
            if mode=='both-inactive':
                for player in players:player['callback']=0x270e
            if mode=='first-flag-off':players[0]['flag']=0
            add('canonical-nine-inline-conditions',condition=item['inline_cpu_address'],condition_hex=None,players=players,enabled=0 if mode=='disabled' else 1,profile=profile,files=[script['file']],canonical_inline=item['inline_cpu_address'],mode=mode)
    for phase,threshold,force,profile in itertools.product(WORDS,WORDS,WORDS,range(2)):
        add('synthetic-selector0-unsigned-phase-force',phase=phase,threshold=threshold,condition_hex=struct.pack('>HH',0,force).hex(),force=force,profile=profile)
    for profile,phase in itertools.product(range(2),WORDS):add('null-condition-no-duration-reset',condition=0,condition_hex=None,motion=0xffffffff,phase=phase,profile=profile)
    rect=struct.pack('>4I',0,0xa000a,0x50000,0xa000a)
    for p1,p2 in itertools.product(((1,1),(6,1),(12,1),(40,40)),repeat=2):
        add('synthetic-selector8-overlap-shortcircuits',condition_hex=(struct.pack('>H',8)+rect).hex(),players=[dict(callback=0x1234,flag=0x80,x=p1[0],y=p1[1]),dict(callback=0x1234,flag=0x80,x=p2[0],y=p2[1])])
    for selector,enabled,mode in itertools.product((4,8),(0,1),('both-inactive','first-flag-off','second-flag-off')):
        players=[dict(callback=0x270e if mode=='both-inactive' else 0x1234,flag=0x80,x=1,y=1) for _ in range(2)]
        if mode=='first-flag-off':players[0]['flag']=0
        if mode=='second-flag-off':players[1]['flag']=0
        add('synthetic-condition-enabled-inactive-flag-shortcircuits',condition_hex=(struct.pack('>H',selector)+rect[:8 if selector==4 else 16]).hex(),enabled=enabled,players=players)
    configs=((0,0xa000a),(0x0001ffff,0x00020002),(0xffff7fff,0x00010001),(0x80008000,0x7fff7fff),(0x7fff0000,0x00010010),(0xfffffff0,0x00010020),(0x8000ffff,0x80000001),(0x7fffffff,0x7fff0001))
    for (start,size),point,camera,mode,profile in itertools.product(configs,range(6),((0,0),(0xffff,0xffff),(0x8000,0x7fff)),('active','inactive','flag-off'),range(2)):
        end=(start+size)&0xffffffff;x,y=start>>16,start&65535;ex,ey=end>>16,end&65535;positions=((x,y),((ex-1)&65535,(ey-1)&65535),(ex,y),(x,ey),((x-1)&65535,y),(x,(y-1)&65535));px,py=positions[point];players=[dict(callback=0x270e if mode=='inactive' else 0x1234,flag=0 if mode=='flag-off' else 0x80,x=(px+camera[0])&65535,y=(py+camera[1])&65535),dict(callback=0x1234,flag=0x80,x=1,y=1)]
        add('synthetic-rectangle-packed-signed-edges-camera',entry=0x1a34c,players=players,camera=list(camera),rectangle_hex=struct.pack('>II',start,size).hex(),profile=profile,rectangle_config=[start,size],point_index=point,mode=mode)
    for callback,flag in ((0x270e,0x80),(0x1234,0)):
        add('rectangle-bypasses-invalid-address',entry=0x1a34c,rectangle=0xffffffff,rectangle_hex=None,players=[dict(callback=callback,flag=flag,x=1,y=1),dict(callback=0x1234,flag=0x80,x=1,y=1)])
    add('packed-low-Y-carry-increments-X',entry=0x1a34c,rectangle_hex=struct.pack('>II',0x0001ffff,0x00020002).hex(),players=[dict(callback=0x1234,flag=0x80,x=3,y=0),dict(callback=0x1234,flag=0x80,x=1,y=1)])
    motions=[r for r in resources if '/motion_'in r['file']]
    for item in motions:
        for offset,profile in itertools.product(range(0,item['end']-item['cpu']-4,10),range(2)):
            add('canonical-duration-all108-cursors',entry=0x1a29e,motion=item['cpu']+offset,profile=profile,files=[item['file']])
    for profile in range(2):add('null-duration',entry=0x1a29e,profile=profile)
    for time,profile in itertools.product(WORDS,range(2)):
        add('RAM-raw-terminal-duration',entry=0x1a29e,motion=DURATION,motion_hex=struct.pack('>HH',time,0xffff).hex(),profile=profile,duration_end=time)
    for address,profile in itertools.product((0x10d41e,0x10d420,0x10d422,0x10d424),range(2)):
        raw=struct.pack('>5H2H',0xaaaa,0xffff,0x1234,0x4321,0,0x1234,0xffff)
        add('RAM-duration-live-d422-clear-alias',entry=0x1a29e,motion=address,motion_data_address=address,motion_hex=raw.hex(),profile=profile)
    for profile in range(2):add('RAM-duration-untyped-raw-record',entry=0x1a29e,motion=DURATION,motion_hex=struct.pack('>5H2H',0xffff,0x8001,1,2,3,0x8000,0xffff).hex(),profile=profile,duration_end=0x8000)
    for a,b,fallback,profile in itertools.product(WORDS,WORDS,range(4),range(2)):
        fields={'d41e':a,'d420':b,'d440':b,'d442':a,'d444':0x8000 if fallback&1 else 1,'d446':0x8000 if fallback&2 else 0xffff,'d448':0x8000,'d44a':0x8000,'d426':0x7fff,'d428':0xffff,'d42a':1,'d42c':0x8000,'d43e':a,'d44c':b}
        add('settings-unsigned-min-max-and-D0-only-fallback',entry=0x1a526,settings=fields,profile=profile)
    amplitudes={0,1,15,16,0x7fffffff,0x80000000,0xffffffff}
    amplitudes.update(((word<<16)+fraction)&0xffffffff for word in range(-9,10) for fraction in (0,1,0x7fff,0x8000,0xffff));rng=random.Random(0x1a3d6);amplitudes.update(rng.randrange(1<<32) for _ in range(128))
    for amplitude,profile in itertools.product(sorted(amplitudes),range(2)):add('shake-signed-ASR-neg-wrap-and-clamp',entry=0x1a3d6,shake=amplitude,profile=profile)
    for profile in range(2):
        for step,entry in enumerate((0x1a2b4,0x1a526,0x1a3d6,0x1a29e,0x1a2b4)):
            add('actual-cli-five-helper-output-carry',entry=entry,sequence=str(profile),sequence_position=step,profile=profile,shake=0x80000000)
    for profile in range(2):
        for step in range(16):add('actual-cli-sixteen-shake-output-carry',entry=0x1a3d6,sequence='shake'+str(profile),sequence_position=step,profile=profile,shake=0x7fffffff if profile==0 else 0x80000000)
    for selector,profile in itertools.product((0,4,8),range(2)):
        condition=struct.pack('>HH',0,0x1234) if selector==0 else struct.pack('>H',selector)+rect[:8 if selector==4 else 16]
        for item in motions[:3]:add('condition-true-canonical-nonnull-duration',condition_hex=condition.hex(),phase=1,threshold=1,motion=item['cpu'],profile=profile,files=[item['file']])
        for raw in (struct.pack('>HH',0x8000,0xffff),struct.pack('>5H2H',0xffff,0x8001,1,2,3,0x8000,0xffff)):
            add('condition-true-RAM-nonnull-duration',condition_hex=condition.hex(),phase=1,threshold=1,motion=DURATION,motion_hex=raw.hex(),profile=profile)
        add('condition-false-bypasses-invalid-duration',condition_hex=condition.hex(),phase=0,threshold=1,motion=0xffffffff,enabled=0,profile=profile)
    for profile in range(2):add('rectangle-Y-reject-preserves-unswapped-packed-registers',entry=0x1a34c,rectangle_hex=struct.pack('>II',0x000afffe,0x00010004).hex(),players=[dict(callback=0x1234,flag=0x80,x=11,y=2),dict(callback=0x1234,flag=0x80,x=1,y=1)],profile=profile)
    assert len(cases)==2235,len(cases)
    return cases,resources,metadata


def fixture(case):
    ram=bytearray(__import__('hashlib').shake_256(b'frame-control'+bytes([case['profile']])).digest(65536));struct.pack_into('>I',ram,0xd422,case['condition']);struct.pack_into('>I',ram,0xd3b4,case['motion']);struct.pack_into('>HHH',ram,0xd418,case['phase'],0x4321,0x8765);struct.pack_into('>HH',ram,0xd41e,case['threshold'],0x9876);struct.pack_into('>H',ram,0xd43e,case['force']);ram[0xd68e]=case['enabled'];struct.pack_into('>HH',ram,0xd3a2,case['camera'][0],0);struct.pack_into('>H',ram,0xd3a6,case['camera'][1]);struct.pack_into('>I',ram,0xd408,case['shake']);struct.pack_into('>HH',ram,0xd404,case['old_shake'],0x5678)
    for address,player in zip(OBJECTS,case['players']):
        offset=address-BASE;struct.pack_into('>I',ram,offset,player['callback']);ram[offset+0x15]=player['flag'];struct.pack_into('>H',ram,offset+0x42,player['x']);struct.pack_into('>H',ram,offset+0x46,player['y'])
    if case['condition_hex'] is not None and case['condition']>=BASE:ram[case['condition']-BASE:case['condition']-BASE+len(bytes.fromhex(case['condition_hex']))]=bytes.fromhex(case['condition_hex'])
    if case['rectangle_hex'] is not None:ram[RECT-BASE:RECT-BASE+8]=bytes.fromhex(case['rectangle_hex'])
    if case['settings'] is not None:
        for key,value in case['settings'].items():struct.pack_into('>H',ram,int(key,16),value)
    if case['motion_hex'] is not None:
        raw=bytes.fromhex(case['motion_hex']);offset=case['motion_data_address']-BASE;ram[offset:offset+len(raw)]=raw
    return ram


def incoming(case,prior=None):
    values=list(HIGHS[case['profile']] if prior is None else prior)
    if case['entry']==0x1a34c:values[8]=OBJECTS[0];values[9]=case['rectangle']
    return values


class Observer:
    def __init__(self,program):
        self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE]);self.program=program;self.calls=collections.Counter();self.rectangles=[];self.rect_pending=None;self.writes=[];self.branches=[];self.branch_pending=None;self.error=None
        def hook(pc):
            cpu=self.cpu
            if self.branch_pending is not None:self.branches.append(dict(pc=self.branch_pending,next_pc=pc));self.branch_pending=None
            if pc in BRANCHES:self.branch_pending=pc
            if pc in ENTRIES+(0x197da,0x197ec,0x197fc,0x1a2e0,0x1a334,0x1a2f2,0x1a314,0x1a3a0,0x1a38a,0x1a356,0x1a39a,0x1a55e,0x1a57e,0x1a3f6,0x1a400):self.calls[pc]+=1
            if pc==0x1a34c:self.rectangles.append(dict(object=cpu.get_reg('a0'),rectangle=cpu.get_reg('a1')))
            if pc==0x1a36c:self.rect_pending=dict(start=cpu.get_reg('d4'),size=cpu.get_reg('d5'))
            if pc==0x1a36e:self.rectangles[-1].update(self.rect_pending,end=cpu.get_reg('d5'));self.rect_pending=None
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(pc),hex(address),size,value)
            if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(hook);self.cpu.set_write_hook(write)
    def run(self,case,ram,values):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,bytes(ram));cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(KEYS,values):cpu.set_reg(register,value)
        self.calls.clear();self.rectangles.clear();self.writes.clear();self.rect_pending=None;self.branches.clear();self.branch_pending=None;self.error=None;cpu.set_reg('pc',case['entry']);status=cpu.run(200000,RETURN)
        if status['status']!='sentinel':self.error=status
        assert cpu.read(0,BASE)==self.program[:BASE];output=cpu.read(BASE,65536);result={key:cpu.get_reg(key) for key in KEYS};result['carry']=bool(cpu.get_reg('sr')&1)
        if status['status']=='sentinel':assert cpu.get_reg('a7')==STACK+4
        return output,result,dict(returned=status['status']=='sentinel',final_pc=cpu.get_reg('pc'),final_a7=cpu.get_reg('a7'),instructions=status['instructions'],calls={hex(k):v for k,v in self.calls.items()},branch_successors=self.branches.copy(),rectangle_calls=self.rectangles.copy(),RAM_writes=self.writes.copy(),error=self.error,mmio_writes=0)


def assert_evidence(case,ram,output,result,info,values):
    if case['settings'] is not None:
        for key,value in case['settings'].items():assert int.from_bytes(ram[int(key,16):int(key,16)+2],'big')==value
    if not info['returned']:return
    write_addresses=[w['address'] for w in info['RAM_writes']]
    if case['entry']==0x1a29e or case['family'].startswith('condition-true-'):
        assert write_addresses[-4:]==[0x10d422,0x10d41e,0x10d420,0x10d43e],write_addresses
    if case['entry']==0x1a3d6:assert write_addresses==[0x10d408,0x10d406,0x10d404]
    if case['entry']==0x1a526:assert write_addresses==[0x10d3ee,0x10d3f0,0x10d3d6,0x10d3da,0x10d3d8,0x10d3dc,0x10d3fa]
    if case['entry']==0x1a34c:assert not write_addresses
    if case['entry'] in (0x1a29e,0x1a526,0x1a3d6):assert not result['carry']
    if case['entry']==0x1a2b4 and not int.from_bytes(ram[0xd422:0xd426],'big'):assert result['carry'] and not info['calls'].get('0x1a29e') and output[0xd41e:0xd440]==ram[0xd41e:0xd440]
    if case['family']=='synthetic-selector0-unsigned-phase-force':
        accepted=case['phase']>=case['threshold'];assert result['carry']==accepted and bool(info['calls'].get('0x1a29e'))==accepted;assert int.from_bytes(output[0xd43e:0xd440],'big')==(0 if accepted else case['force'])
    if case['family']=='synthetic-selector8-overlap-shortcircuits':
        trace=info['rectangle_calls'];assert trace[0]['object']==OBJECTS[0] and trace[0]['rectangle']==COND+2
        fallback=False
        for call in trace:
            assert call['object'] in OBJECTS and call['rectangle'] in (COND+2,COND+10)
            if call['rectangle']==COND+10:fallback=True
            else:assert not fallback
        assert bool(info['calls'].get('0x1a314'))==fallback
    for rectangle in info['rectangle_calls']:
        if 'end'in rectangle:assert rectangle['end']==(rectangle['start']+rectangle['size'])&0xffffffff
    if case['family']=='packed-low-Y-carry-increments-X':assert result['carry'] and info['rectangle_calls'][0]['end']==0x00040001
    if case['family']=='rectangle-bypasses-invalid-address':assert not any('end'in r for r in info['rectangle_calls']) and result['carry']==(case['players'][0]['callback']==0x270e)
    if case['family'].startswith('condition-true-'):assert result['carry'] and info['calls'].get('0x1a29e')==1 and info['calls'].get('0x197da')==1
    if case['family']=='condition-false-bypasses-invalid-duration':assert not result['carry'] and not info['calls'].get('0x197da')
    if case['family']=='rectangle-Y-reject-preserves-unswapped-packed-registers':assert not result['carry'] and not info['calls'].get('0x1a38a') and result['d4']==0x000afffe and result['d5']==0x000c0002
    if case['entry']==0x1a29e:
        assert output[0xd422:0xd426]==bytes(4) and output[0xd43e:0xd440]==bytes(2) and output[0xd41e:0xd420]==output[0xd420:0xd422];assert result['d7']>>16==values[7]>>16
        if case['family']=='RAM-duration-live-d422-clear-alias' and case['motion'] in (0x10d420,0x10d422):assert result['d7']&65535==0x1233 and info['calls'].get('0x197ec')==2
    if case['entry']==0x1a526:
        get=lambda at:int.from_bytes(ram[at:at+2],'big');out=lambda at:int.from_bytes(output[at:at+2],'big');assert out(0xd3ee)==min(get(0xd41e),get(0xd440)) and out(0xd3f0)==min(get(0xd420),get(0xd442)) and out(0xd3fa)==max(get(0xd43e),get(0xd44c));assert result['d2']&65535==get(0xd442)
        for index in range(3):assert result['d'+str(index)]>>16==values[index]>>16
        for axis in range(2):
            fallback=get(0xd444+axis*2)==0x8000;assert out(0xd3d6+axis*2)==get(0xd426+axis*2 if fallback else 0xd444+axis*2) and out(0xd3da+axis*2)==get(0xd42a+axis*2 if fallback else 0xd448+axis*2)
    if case['entry']==0x1a3d6:
        amplitude=int.from_bytes(ram[0xd408:0xd40c],'big');signed=amplitude if amplitude<0x80000000 else amplitude-(1<<32);expected=(-amplitude+(signed>>4))&0xffffffff;assert int.from_bytes(output[0xd408:0xd40c],'big')==expected and output[0xd406:0xd408]==ram[0xd404:0xd406];rounded=((expected+0x8000)&0xffffffff)>>16;rounded=rounded if rounded<0x8000 else rounded-65536;assert int.from_bytes(output[0xd404:0xd406],'big')==max(-8,min(8,rounded))&65535


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);oracle=oracle_provenance(root);observer=Observer(program);folder=root/'artifacts/scene_frame_control';folder.mkdir(parents=True,exist_ok=True);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case) if prior is None else bytearray(prior[0]);values=incoming(case,None if prior is None else prior[1]);output,result,info=observer.run(case,ram,values);assert_evidence(case,ram,output,result,info,values);name='native_%04d.bin'%index;(folder/name).write_bytes(output);rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,values)),input_ram_sha256=sha(ram),result=result,ram_file=name,ram_sha256=sha(output),**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[key] for key in KEYS])
        if info['error']:break
    assert oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources:assert sha((root/item['file']).read_bytes())==item['sha256']
    assert sha((root/metadata['condition_inventory_file']).read_bytes())==metadata['condition_inventory_sha256'] and sha((root/metadata['script_manifest']['file']).read_bytes())==metadata['script_manifest']['sha256']
    report=dict(source=source,oracle=oracle,cases=len(cases),completed_cases=sum(row['returned'] for row in rows),failure=observer.error,results=rows,resources=resources,metadata=metadata,program_code_modified=False,scope='Original 1a2b4/1a34c/1a29e/1a526/1a3d6 continuously to RTS in pinned Musashi; full RAM, 12 registers, CCR.C, A7+4, zero MMIO and write guard. All 9 canonical condition inline resources regenerated from source and original script MS5D ownership verified. Synthetic condition/rectangle/duration bytes use live RAM at identical CPU addresses in both engines; no normalization, ROM patch or callee reset. Actual CLI carry feeds entire prior RAM and 12 registers into two five-helper chains and two sixteen-shake chains without host RAM or register rewrites; only next entry and call-boundary stack/SR selected. No natural-frame claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
