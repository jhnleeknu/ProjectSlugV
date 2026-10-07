"""Unpatched continuous native1a5a4 initialization, RAM/register/ordered ports."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import zlib
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE, STACK, RETURN, ENTRY = 0x100000, 0x1feffc, 0xff000, 0x1a5a4
KEYS=tuple('d'+str(i) for i in range(8))+('a0','a1','a2','a3','a4','a6')
REGS=tuple(getattr(m,'UC_M68K_REG_'+name.upper()) for name in KEYS)
HIGHS=((0,)*14,(0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xe1e23456,0xfeedbeef,0))
PORTS=(0x2ffff0,0x2ffff2,0x300001,0x3c0000,0x3c0004,0x3c0006)
CAP=2000000

def sha(data):return hashlib.sha256(data).hexdigest()
def resources(root,program):
    result=[];manifests=[];identities={}
    for dirname in ('scene_scripts','scene_maps','scene_secondary','scene_placements'):
        directory=root/'extracted/runtime'/dirname;mp=directory/'manifest.json';manifest=json.loads(mp.read_text());assert manifest['source']['sha256']==SOURCE_SHA256
        manifests.append(dict(file=str(mp.relative_to(root)),sha256=sha(mp.read_bytes())))
        items=manifest.get('resources',[])+manifest.get('scripts',[])+manifest.get('dependencies',[])
        if dirname=='scene_scripts':items.append(manifest['node_pointers'])
        for item in items:
            path=directory/item['file'];data=path.read_bytes();header=struct.unpack('<4s7I',data[:32]);magic,version,kind,cpu,rom,size,crc,reserved=header
            assert magic==b'MS5D' and version==1 and reserved==0 and kind in (1,2) and len(data)==size+32
            assert zlib.crc32(data[32:])==crc
            assert data[32:]==program[rom:rom+size] and cpu==item['source_cpu_address'] and rom==item['source_rom_offset']
            if 'sha256' in item:assert sha(data)==item['sha256']
            identity=(kind,cpu,rom,size)
            if identity in identities:
                assert identities[identity]==data;continue
            identities[identity]=data;result.append(dict(file=str(path.relative_to(root)),sha256=sha(data),kind=kind,cpu=cpu,rom=rom,size=size))
    path=root/'extracted/runtime/scene_debug.ms5d';data=path.read_bytes();assert struct.unpack('<4s7I',data[:32])==(b'MS5D',1,1,0x1af12,0x1af12,512,zlib.crc32(data[32:]),0) and data[32:]==program[0x1af12:0x1b112];result.append(dict(file=str(path.relative_to(root)),sha256=sha(data),kind=1,cpu=0x1af12,rom=0x1af12,size=512))
    for path in (root/'extracted/runtime/stages/manifest.json',root/'artifacts/scene_general_initialization/contexts.json'):
        manifests.append(dict(file=str(path.relative_to(root)),sha256=sha(path.read_bytes())))
    return result,manifests

def build_cases(root,program):
    scripts=json.loads((root/'extracted/runtime/scene_scripts/manifest.json').read_text());stages=json.loads((root/'extracted/runtime/stages/manifest.json').read_text());cases=[]
    for script in scripts['scripts']:cases.append(dict(family='canonical-all41-target0',script=script['source_cpu_address'],target=0,profile=0,debug=0,available=True))
    assert len(cases)==41
    for group,g in enumerate(stages['groups']):
        for area,r in enumerate(g['records']):
            at=r['source_cpu_address'];script=struct.unpack_from('>I',program,at+2)[0];target=struct.unpack_from('>H',program,at+14)[0]
            cases.append(dict(family='actual-stage-catalog-script-target',script=script,target=target,profile=1,debug=0,available=True,group=group,area=area,record=at))
    assert len(cases)==100
    for script in scripts['scripts']:
        for profile,debug,available in ((1,0,False),(1,24,True)):
            cases.append(dict(family='canonical-target0-highs-debug-allocation',script=script['source_cpu_address'],target=0,profile=profile,debug=debug,available=available))
    for target in (0,1,0x7fff,0x8000,0xffff):
        for profile,debug in ((0,0),(1,24)):
            cases.append(dict(family='null-script-target-clamp-boundaries',script=0,target=target,profile=profile,debug=debug,available=True))
    assert len(cases)==192
    for script in (0xd9edc,0xddb18,0xdd9da):
        for target in (0x7fff,0x8000,0xffff):cases.append(dict(family='selected-motion-target-unsigned-boundaries',script=script,target=target,profile=1,debug=0,available=True))
    for script,target in ((0xd9edc,0x130),(0xddb18,0x580),(0xdd9da,0x580)):
        for debug in (8,16):
            for available in (False,True):cases.append(dict(family='multi-iteration-debug8-16-allocation',script=script,target=target,profile=1,debug=debug,available=available))
    for script,target in ((0xd9edc,0x130),(0xddb18,0x580)):
        for debug in (8,16):
            sequence=hex(script)+'-'+str(debug)
            for step,phase in enumerate((0,target)):cases.append(dict(family='actual-cli-carry-reinitialize-host-target-script',script=script,target=phase,profile=1,debug=debug,available=True,sequence=sequence,sequence_position=step))
    assert len(cases)==221
    return cases

def fixture(program,case):
    # Independently seed verified original2790/3ef2 before entering1a5a4.
    cpu=make_cpu(program);cpu.mem_write(BASE,bytes(65536))
    for entry in (0x2790,0x3ef2):
        cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.emu_start(entry,RETURN,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
    ram=bytearray(cpu.mem_read(BASE,65536));ram[0xf000]=case['debug'];ram[0xd494]=0x55
    if not case['available']:struct.pack_into('>H',ram,0x4ca0,0)
    # Retained bounds are explicit full signed acceptance limits.
    struct.pack_into('>4H',ram,0xd3f2,0x8000,0x7fff,0x8000,0x7fff)
    return ram

def values(case,prior=None):
    vals=list(HIGHS[case['profile']] if prior is None else prior);vals[0]=(vals[0]&0xffff0000)|case['target'];vals[8]=case['script'];vals[13]=0x100820;return vals

class Observer:
    def __init__(self,program):
        self.cpu=make_cpu(program);self.cpu.mem_map(0x200000,0x300000);self.baseline=self.cpu.context_save();self.program=program;self.ports=[];self.calls=collections.Counter();self.commands=[];self.error=None;self.instructions=0;self.bank=0x200000;self.reads=[];self.fallback_writes=[]
        def code(cpu,address,size,user):
            self.instructions+=1
            if address==RETURN:cpu.emu_stop();return
            if address in (0x1a5a4,0x1a65a,0x1a26a,0x19938,0x1a7a8,0x1afda,0x1a414,0x1a470,0x28ae,0x2912,0x43e08,0x19e64,0x183c6,0x185f2,0x1861a,0xcaf0,0x3a88,0x1b0e0):self.calls[address]+=1
            if address==0x1a0b6:self.commands.append(cpu.reg_read(m.UC_M68K_REG_A1))
            word=int.from_bytes(cpu.mem_read(address,2),'big')
            if word==0x4afc or 0x4e40<=word<=0x4e4f:self.error=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            if 0x100ec6<=address<0x100eec:self.fallback_writes.append((size,address,value&((1<<(size*8))-1)))
            if BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=STACK+4:return
            if address not in PORTS:self.error=dict(kind='unexpected-write',address=address,size=size,value=value);cpu.emu_stop();return
            self.ports.append((size,address,value&((1<<(size*8))-1)))
            if address==0x2ffff2:
                if size!=2 or value not in (0x1000,0x2000):self.error=dict(kind='unsupported-bank',value=value);cpu.emu_stop();return
                self.bank=0x200000 if value==0x1000 else 0x300000;cpu.mem_write(0x200000,program[self.bank:self.bank+0xffff0])
        def read(cpu,access,address,size,value,user):
            if 0x2ffff0<=address<0x500000:self.reads.append((size,address))
        def intr(cpu,number,user):self.error=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read);self.cpu.hook_add(UC_HOOK_INTR,intr)
    def run(self,ram,regs):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,self.program[0x200000:0x2ffff0]);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        self.ports.clear();self.calls.clear();self.commands.clear();self.reads.clear();self.fallback_writes.clear();self.error=None;self.instructions=0;self.bank=0x200000
        try:cpu.emu_start(ENTRY,0xffffff,count=CAP)
        except unicorn.UcError as e:
            if self.error is None:self.error=dict(kind='emulator-error',error=str(e),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=RETURN and self.error is None:self.error=dict(kind='instruction-cap',cap=CAP,pc=pc)
        assert bytes(cpu.mem_read(0,0x100000))==self.program[:0x100000]
        assert bytes(cpu.mem_read(0x200000,0xffff0))==self.program[self.bank:self.bank+0xffff0]
        assert not self.reads,(self.reads[:10])
        if pc==RETURN:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        output=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(r)&0xffffffff for r in REGS)));ports=b''.join(struct.pack('>BII',*p) for p in self.ports)
        info=dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),calls={hex(k):v for k,v in self.calls.items()},command_addresses=self.commands.copy(),instructions=self.instructions,error=self.error,final_bank=self.bank,mmio_reads=0,fallback_position_writes=self.fallback_writes.copy())
        return output,result,ports,info

def assert_evidence(case,ram,output,ports,info):
    if not info['returned']:return
    events=[struct.unpack_from('>BII',ports,at) for at in range(0,len(ports),9)]
    assert events[:2]==[(2,0x2ffff2,0x2000),(2,0x2ffff0,0)] and events[-2:]==[(2,0x2ffff2,0x1000),(2,0x2ffff0,0)]
    assert output[0x10:0x12]==b'\0\0'
    if not case['available'] and info['calls'].get('0x1a470',0):
        assert info['calls'].get('0x2912',0)>0 and any(w[1]==0x100ec6 for w in info['fallback_position_writes'])

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    rs,manifests=resources(root,program);cases=build_cases(root,program);folder=root/'artifacts/scene_general_initialization';folder.mkdir(parents=True,exist_ok=True);observer=Observer(program);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(program,case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1]);output,result,ports,info=observer.run(ram,regs)
        assert_evidence(case,ram,output,ports,info)
        if 'sequence' in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
        (folder/('native_%04d.bin'%index)).write_bytes(output);(folder/('native_%04d.ports.bin'%index)).write_bytes(ports)
        rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),result=result,input_ram_sha256=sha(ram),ram_file='native_%04d.bin'%index,ram_sha256=sha(output),ports_file='native_%04d.ports.bin'%index,ports_sha256=sha(ports),port_count=len(ports)//9,**info))
        if info['error']:break
    for item in rs+manifests:assert sha((root/item['file']).read_bytes())==item['sha256']
    report=dict(source=source,cases=len(cases),completed_cases=sum(r['returned'] for r in rows),results=rows,resources=rs,manifests=manifests,failure=observer.error,program_code_modified=False,scope='Original1a5a4 continuous toactualRTS with everycallee, no patches/substitution/calleecontextreset. Original2790/3ef2 seed controlled input before entry; explicit bounds,debugflag,allocationcount fixtures. Initial physicalbank2, originalPVC1000/2000 switching tobank2/3, exactordered9byteporttrace. Native-only, no natural scheduler/IRQ/callback reachability claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
