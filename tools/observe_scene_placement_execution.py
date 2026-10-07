"""Continuous original1a414/1a470 observations with live RAM and immutable ROM."""
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
BASE, STACK, RETURN = 0x100000, 0x1feffc, 0xff000
REGS = REGS + (m.UC_M68K_REG_A6,)
KEYS = KEYS + ('a6',)
HIGHS = ((0,)*13, (0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xfeedbeef,0))
def sha(data): return hashlib.sha256(data).hexdigest()
def resources(root, program):
    paths=[]; manifests=[]; placements=json.loads((root/'extracted/runtime/scene_placements/manifest.json').read_text()); scripts=json.loads((root/'extracted/runtime/scene_scripts/manifest.json').read_text())
    for directory,manifest,items in (('scene_placements',placements,placements['resources']),('scene_scripts',scripts,[i for i in scripts['dependencies'] if i['file'].startswith('motion_')])):
        mp=root/'extracted/runtime'/directory/'manifest.json';manifests.append(dict(file=str(mp.relative_to(root)),sha256=sha(mp.read_bytes())))
        assert manifest['source']['sha256']==SOURCE_SHA256
        for item in items:
            path=root/'extracted/runtime'/directory/item['file'];end=item.get('end_exclusive',item.get('end_cpu_address_exclusive'))
            digest=checked_resource(path,program,item['source_cpu_address'],end)
            if 'sha256' in item:assert digest==item['sha256']
            paths.append(dict(file=str(path.relative_to(root)),sha256=digest,cpu=item['source_cpu_address'],end=end))
    return placements,scripts,paths,manifests

def build_cases(root,program):
    placements,scripts,paths,manifests=resources(root,program);cases=[];motions=[i['source_cpu_address'] for i in scripts['dependencies'] if i['file'].startswith('motion_')]
    assert len(placements['resources'])==18 and len(motions)==37
    contexts_path=root/'artifacts/scene_placement_execution/contexts.json';contexts=json.loads(contexts_path.read_text());context_motions={}
    manifests.append(dict(file=str(contexts_path.relative_to(root)),sha256=sha(contexts_path.read_bytes())))
    for reference in contexts['references']:
        motion=reference['preceding_linear_motion']
        if motion:
            for address in reference['placement_record_cpu_addresses']:context_motions[address]=motion['motion_pointer_long']
    records={r['cpu_address']:r for item in placements['resources'] for r in item['records']};assert len(records)==24
    for cursor,r in sorted(records.items()):
        phases=sorted({(r['gate_word']-1)&65535,r['gate_word'],(r['gate_word']+1)&65535})
        for entry,phase,count,motion,profile in itertools.product((0x1a414,0x1a470),phases,(0,4),(0,context_motions.get(cursor,motions[0])),(0,1)):
            cases.append(dict(family='canonical-record-cursor-gate-allocation-motion',entry=entry,cursor=cursor,phase=phase,count=count,motion=motion,profile=profile))
    for item in placements['resources']:
        for phase in (0,0xffff):cases.append(dict(family='canonical-root',entry=0x1a414,cursor=item['source_cpu_address'],phase=phase,count=8,motion=0,profile=1))
        cases.append(dict(family='canonical-terminal',entry=0x1a414,cursor=item['terminal_cpu_address'],phase=0xffff,count=8,motion=0,profile=1))
        for step,phase in enumerate((0,1,0x7fff,0xfffe,0xffff)):
            cases.append(dict(family='actual-cli-carry-phase-updates',entry=0x1a414,cursor=item['source_cpu_address'],phase=phase,count=8,motion=0,profile=1,sequence=item['file'],sequence_position=step))
    def synthetic(label,**changes):
        c=dict(family=label,entry=0x1a470,cursor=0x106000,phase=1,count=4,motion=0,profile=1,gate=0,x=0,y=0,bounds=0,callback=0x12345678,payload_hex='12345678abcdffff',synthetic=True);c.update(changes);cases.append(c)
    for motion in motions:
        for entry,phase in itertools.product((0x1a414,0x1a470),(0,1,0x7fff,0xffff)):synthetic('all37-canonical-motion-input-fraction',entry=entry,phase=phase,motion=motion)
    for entry,callback,count in itertools.product((0x1a414,0x1a470),(0,1,0xffffffff),(0,4)):
        synthetic('callback-full-long-allocator-fallback',entry=entry,callback=callback,count=count)
    for edge,thresholds,x,y,bounds_values,scroll in (
        ('accept',(-100,100,-100,100),0,0,(0,0),0),
        ('reject-y-upper',(-100,100,-100,-1),0,0,(0,0),0),
        ('reject-y-lower',(-100,100,1,100),0,0,(0,0),0),
        ('reject-x-upper',(-100,-1,-100,100),0,0,(0,0),0),
        ('reject-x-lower',(1,100,-100,100),0,0,(0,0),0),
        ('signed-overflow',(-32768,32767,-32768,32767),0x7fff,0x8000,(0x00010001,0x80008000),0xffff)):
        for bounds in (0,0x106800):synthetic('bounds-'+edge,bounds=bounds,thresholds=thresholds,x=x,y=y,bounds_values=bounds_values,scroll=scroll)
    # Source immediately behind destination forces later WORD reads to observe previous writes.
    for cursor in (0x100464,0x100466,0x100468,0x10d408,0x10d410):
        synthetic('live-RAM-word-copy-overlap-global-alias',cursor=cursor,phase=0,payload_hex='000000010002000300040005',count=4)
    for entry in (0x1a414,0x1a470):synthetic('high-fffe-ordinary-gate',entry=entry,gate=0xfffe,phase=0xffff)
    synthetic('live-phase-update-between-records',entry=0x1a414,phase=0,free_node=0x10d3a2,payload_hex='0001',second_record=True)
    cases.append(dict(family='null-stream',entry=0x1a414,cursor=0,phase=0,count=4,motion=0,profile=1))
    assert len(cases)==1625
    return cases,paths,manifests

def fixture(case):
    ram=bytearray(hashlib.shake_256(b'placement-execution'+bytes([case['profile']])).digest(65536))
    struct.pack_into('>IH',ram,0x4c9c,0x100400,case['count'])
    struct.pack_into('>I',ram,0x208,0x103000);struct.pack_into('>H',ram,0x210,0xffff);ram[0x26a]=0 if case['cursor']==0x100468 else 0xa5
    for i in range(10):struct.pack_into('>I',ram,0x408+i*0x100,BASE+0x500+i*0x100)
    struct.pack_into('>I',ram,0x3004,0x100200)
    struct.pack_into('>IHH',ram,0xd3b4,case['motion'],0,0)
    struct.pack_into('>I',ram,0xd40e,case['cursor']);struct.pack_into('>H',ram,0xd418,case['phase'])
    struct.pack_into('>H',ram,0xd3a6,case.get('scroll',0));struct.pack_into('>4H',ram,0xd3f2,*[v&65535 for v in case.get('thresholds',(-32768,32767,-32768,32767))])
    struct.pack_into('>II',ram,0xd3a2,0,0)
    # Parent used by43e08 is RAM10d38e; zero absolute coordinates and stamp.
    struct.pack_into('>II',ram,0xd3a2,0,0);ram[0xd3b3]=0;ram[0xd494]=0x55
    struct.pack_into('>H',ram,0xd3a6,case.get('scroll',0))
    if case.get('bounds'):struct.pack_into('>II',ram,case['bounds']-BASE,*case['bounds_values'])
    if case.get('synthetic'):
        raw=struct.pack('>4H2I',case['gate'],len(bytes.fromhex(case['payload_hex'])),case['x'],case['y'],case['bounds'],case['callback'])+bytes.fromhex(case['payload_hex'])
        if case.get('second_record'):raw+=struct.pack('>4H2I',1,0,2,3,0,0x12345678)
        raw+=b'\xff\xff'
        offset=case['cursor']-BASE;ram[offset:offset+len(raw)]=raw
    if case.get('free_node'):
        struct.pack_into('>I',ram,0x4c9c,case['free_node']);struct.pack_into('>I',ram,case['free_node']-BASE+8,0x100500)
    return ram

def values(case,prior=None):
    vals=list(HIGHS[case['profile']] if prior is None else prior);vals[8]=case['cursor'];vals[12]=0x100200;return vals

class Observer:
    def __init__(self,program):
        self.cpu=make_cpu(program);self.baseline=self.cpu.context_save();self.program=program;self.calls={};self.edges=[];self.last=None;self.position_writes=[]
        def code(cpu,address,size,user):
            if self.last in (0x1a4b0,0x1a4ba,0x1a4cc,0x1a4d6):self.edges.append((hex(self.last),hex(address)))
            self.last=address
            if address==RETURN:cpu.emu_stop()
            if address in (0x1a414,0x1a470,0x19802,0x28ae,0x2908,0x2912,0x43e08,0x43e38):self.calls[address]=self.calls.get(address,0)+1
        def write(cpu,access,address,size,value,user):
            if 0x100ec6<=address<0x100eec:self.position_writes.append((hex(address),size,value))
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,case,ram,regs):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        self.calls.clear();self.edges.clear();self.position_writes.clear();self.last=None;cpu.emu_start(case['entry'],0xffffff,count=200000)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4,(case,hex(cpu.reg_read(m.UC_M68K_REG_PC)))
        assert bytes(cpu.mem_read(0,0x100000))==self.program[:0x100000]
        self.calls['bounds_edges']=self.edges.copy();self.calls['fallback_position_writes']=self.position_writes.copy()
        return bytes(cpu.mem_read(BASE,65536)),dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS))),{hex(k) if isinstance(k,int) else k:v for k,v in self.calls.items()}

def assert_evidence(case,ram,output,calls):
    if case['family']=='high-fffe-ordinary-gate':assert calls.get('0x1a470',0)>=1
    if case['family'] in ('canonical-terminal','null-stream'):assert '0x1a470' not in calls
    targets={'bounds-reject-y-upper':'0x1a4b0','bounds-reject-y-lower':'0x1a4ba','bounds-reject-x-upper':'0x1a4cc','bounds-reject-x-lower':'0x1a4d6'}
    if case['family'] in targets:
        assert (targets[case['family']],'0x1a51c') in [tuple(e) for e in calls['bounds_edges']] and '0x28ae' not in calls
    if case['family']=='callback-full-long-allocator-fallback' and (not case['count'] or not case['callback']):
        assert calls.get('0x2912')==1 and calls.get('0x43e08')==1 and any(w[0]=='0x100ec6' for w in calls['fallback_position_writes'])
    if case['family']=='live-RAM-word-copy-overlap-global-alias' and case['cursor']==0x100464:
        assert output[0x476:0x482]==b'\0'*12 and ram[0x476:0x482]!=output[0x476:0x482]
    if case['family']=='live-phase-update-between-records':
        assert calls.get('0x1a470')==2 and output[0xd418:0xd41a]==b'\0\1' and int.from_bytes(output[0xd40e:0xd412],'big')==case['cursor']+34

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    cases,paths,manifests=build_cases(root,program);folder=root/'artifacts/scene_placement_execution';folder.mkdir(parents=True,exist_ok=True);observer=Observer(program);previous={};rows=[]
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(case) if prior is None else bytearray(prior[0]);struct.pack_into('>H',ram,0xd418,case['phase']);regs=values(case,None if prior is None else prior[1]);output,result,calls=observer.run(case,ram,regs)
        assert_evidence(case,ram,output,calls)
        path=folder/('native_%05d.bin'%index);path.write_bytes(output)
        rows.append(dict(case_index=index,fixture=case,incoming=regs,result=result,input_ram_sha256=sha(ram),ram_file=path.name,ram_sha256=sha(output),calls=calls,final_pc=RETURN,final_a7=STACK+4,mmio_writes=0))
        if 'sequence' in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
    for item in paths+manifests:assert sha((root/item['file']).read_bytes())==item['sha256']
    report=dict(source=source,cases=len(rows),completed_cases=len(rows),results=rows,resources=paths,manifests=manifests,mmio_writes=0,original_rom_immutable=True,scope='Original1a414/1a470 uninterrupted toRTS including original19802/28ae/43e08. All live RAMaddresses identical; no patch, normalization or callee resets. Controlledfixtures and explicit hostphase changes; no natural scheduling or callback execution claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
