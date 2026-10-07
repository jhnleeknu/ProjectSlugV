"""Continuous original2a28 full15register/static restart and live cleanup aliases."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE, STACK, RETURN, ENTRY=0x100000,0x1feffc,0xff000,0x2a28
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(7))
REGS=tuple(getattr(m,'UC_M68K_REG_'+name.upper()) for name in KEYS)
HIGHS=((0,)*15,(0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xe1e23456,0xfeedbeef,0x13579bdf,0xffffffff))
CALLS=(0x2a28,0x299c,0x2782,0x8ff4,0x8e4a,0xc3fa,0x46ef4,0x43e38,0x271c,0x29c0,0x29c8,0x29fe)
PALETTE=None

def sha(data):return hashlib.sha256(data).hexdigest()
def build_cases():
    cases=[]
    def add(family,**changes):
        case=dict(family=family,object=0x100820,count=0,reference=0,coord=255,parent=0,stamp=0,profile=1,callback=0xf12);case.update(changes);cases.append(case)
    for count,reference,profile,callback in itertools.product(range(5),(0,1,2,0xffff),range(2),(0,1,0x101000,0xffffffff)):
        add('raw-count0-4-reference-boundaries-callback-LONG',count=count,reference=reference,profile=profile,callback=callback)
    for count,reference,duplicate in itertools.product((1,2,4),(1,2,0xffff),(False,True)):
        add('duplicates-freed-head-tail',count=count,reference=reference,duplicate=duplicate)
    for count in (5,8,32,128,255):
        for reference in (0,1,2,0xffff):add('raw-large-count-descending-live-slots',count=count,reference=reference)
    for coord,parent_kind,stamp,profile in itertools.product((0,1,2,3,4,5,6,7,0x80,0xff),('null','ordinary','self','overlap','object','global-stamp'),(0,0x55,255),range(2)):
        parent=0 if parent_kind=='null' else 0x100200 if parent_kind=='ordinary' else BASE+0xd4e6+coord*0x2c if parent_kind=='self' and coord<8 else BASE+0xd4ea+coord*0x2c if parent_kind=='overlap' and coord<8 else 0x10084e if parent_kind=='object' else 0x10d480
        add('coordinate-index-parent-self-overlap-stamp',coord=coord,parent=parent,stamp=stamp,profile=profile,parent_kind=parent_kind,count=2,reference=1)
    for object in (0x100000,0x100b30,0x100bf4,0x104d82,0x104d92,0x104da2,0x105d90,0x10ff3c):
        for profile in range(2):add('object-span-edges-palette-state-overlap',object=object,profile=profile)
    for previous,next,tail in ((0xc000,0x10,0xff0),(0x1000,0x127e,0xc000),(0xb26e,0x10,0xb26e)):
        add('palette-signed16-raw-live-links',count=1,reference=1,links=[previous,next,tail])
    for next_type,profile in itertools.product((0,0x1001),range(2)):
        add('cleanup-alias-type-changes-linked-fallback',object=0x106000,count=1,reference=1,alias_type=True,next_type=next_type,profile=profile)
    for previous_depth,profile in itertools.product((0,1),range(2)):
        add('cleanup-alias-linked-cascade-or-static-previous',object=0x106000,count=1,reference=1,alias_type=True,next_type=0,previous_depth=previous_depth,profile=profile)
    for sequence,different in enumerate((False,True)):
        for profile in range(2):
            for step in range(3):add('actual-cli-carry-same-and-different-object',sequence=str(sequence)+'-'+str(profile),sequence_position=step,object=0x100820 if not different or step==0 else 0x101200,profile=profile,count=2,reference=2,callback=(0,1,0xffffffff)[step])
    assert len(cases)==597
    return cases

def fixture(program,case):
    global PALETTE
    if PALETTE is None:
        cpu=make_cpu(program);cpu.mem_write(BASE,bytes(65536));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.emu_start(0x3ef2,RETURN,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN;PALETTE=bytes(cpu.mem_read(BASE,65536))
    ram=bytearray(hashlib.shake_256(b'object-restart-full'+bytes([case['profile']])).digest(65536));ram[0x4d92:0x5da2]=PALETTE[0x4d92:0x5da2]
    # Controlled raw slots preserve their descending/live nature, including count byte at slot4.
    for slot in range(256):struct.pack_into('>H',ram,0x4d92+slot*16+8,case['reference'])
    for obj in (case['object'],0x101200):
        at=obj-BASE;struct.pack_into('>H',ram,at+0x10,0);ram[at+0x6c]=255;ram[at+0x1d]=0
    at=case['object']-BASE
    for index in range(case['count']):ram[at+0x19+index]=7 if case.get('duplicate') else index&255
    ram[at+0x1d]=case['count'];ram[at+0x6c]=case['coord'];ram[0xd494]=0x55
    if case['coord']<8:
        offset=0xd4e6+case['coord']*0x2c;struct.pack_into('>5I',ram,offset,0xffff0001,0x7fffffff,1,0x80000001,case['parent']);struct.pack_into('>II',ram,offset+0x14,0x13579bdf,0x80000000);ram[offset+0x24:offset+0x26]=bytes((case['stamp'],0xa0))
        if case['parent']:
            parent=case['parent']-BASE;struct.pack_into('>II',ram,parent+0x14,0xffff8001,0x7fffffff);ram[parent+0x25]=0xc3
    if case.get('links'):
        previous,next,tail=case['links'];struct.pack_into('>HH',ram,0x4d92,previous,next);struct.pack_into('>H',ram,0x5d92,tail)
    if case.get('alias_type'):
        struct.pack_into('>4I',ram,at,0x1234,0x106200,0x106100,0);struct.pack_into('>H',ram,at+0x10,0);ram[at+0x19]=0;ram[at+0x1d]=1;ram[at+0x6c]=255
        struct.pack_into('>HHH',ram,0x4d92,0x1000,0x127e,0);struct.pack_into('>H',ram,0x4d9a,1);struct.pack_into('>H',ram,0x5d92,0x1000)
        struct.pack_into('>H',ram,0x6110,case['next_type']);struct.pack_into('>I',ram,0x6200,0x270e if 'previous_depth' in case else 0x1234);struct.pack_into('>H',ram,0x6210,case.get('previous_depth',0))
        struct.pack_into('>II',ram,0x6204,0x106300,0x106140);struct.pack_into('>I',ram,0x6300,0x1234);struct.pack_into('>H',ram,0x6310,0);struct.pack_into('>IH',ram,0x4c9c,0x106300,4)
    return ram

def values(case,prior=None):
    result=list(HIGHS[case['profile']] if prior is None else prior);result[8]=case['object'];result[9]=case['callback'];return result

class Observer:
    def __init__(self,program):
        self.cpu=make_cpu(program);self.cpu.mem_map(0x300000,4096);self.baseline=self.cpu.context_save();self.program=program;self.calls=collections.Counter();self.ports=[];self.error=None;self.instructions=0;self.reads=[]
        def code(cpu,address,size,user):
            self.instructions+=1
            if address==RETURN:cpu.emu_stop();return
            if address in CALLS:self.calls[address]+=1
            word=int.from_bytes(cpu.mem_read(address,2),'big')
            if word==0x4afc or 0x4e40<=word<=0x4e4f:self.error=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            if address==0x300001:
                assert size==1;self.ports.append((size,address,value&255));return
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
        def read(cpu,access,address,size,value,user):self.reads.append((size,address))
        def intr(cpu,number,user):self.error=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x300000,end=0x300fff);self.cpu.hook_add(UC_HOOK_INTR,intr)
    def run(self,ram,regs):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(REGS,regs):cpu.reg_write(register,value)
        self.calls.clear();self.ports.clear();self.error=None;self.instructions=0;self.reads.clear()
        try:cpu.emu_start(ENTRY,0xffffff,count=200000)
        except unicorn.UcError as e:self.error=dict(kind='emulator-error',error=str(e),pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc=cpu.reg_read(m.UC_M68K_REG_PC)
        if pc!=RETURN and self.error is None:self.error=dict(kind='instruction-cap',pc=pc)
        assert not self.reads and bytes(cpu.mem_read(0,0x100000))==self.program[:0x100000]
        if pc==RETURN:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        result=dict(zip(KEYS,(cpu.reg_read(register)&0xffffffff for register in REGS)));output=bytes(cpu.mem_read(BASE,65536));ports=b''.join(struct.pack('>BII',*event) for event in self.ports)
        info=dict(returned=pc==RETURN,final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),calls={hex(k):v for k,v in self.calls.items()},instructions=self.instructions,error=self.error,mmio_reads=0)
        return output,result,ports,info

def assert_evidence(case,ram,output,result,ports,info,regs):
    if not info['returned']:return
    assert ports==struct.pack('>BII',1,0x300001,regs[0]&255)
    assert result['a0']==case['object'] and result['a6']==regs[14] and result['a5']==0x108000
    assert output[case['object']-BASE:case['object']-BASE+4]==case['callback'].to_bytes(4,'big')
    if case.get('alias_type'):
        assert info['calls'].get('0x29c0',0)>0
        if case['next_type']:assert '0x271c' not in info['calls']
        else:
            expected=2 if case.get('previous_depth') else 1
            assert info['calls'].get('0x29c0',0)==expected and info['calls'].get('0x29c8',0)==expected and int.from_bytes(output[0x4ca0:0x4ca2],'big')==4+expected
            if expected==2:assert int.from_bytes(output[0x4c9c:0x4ca0],'big')==0x106200
    if case['reference']==1 and case['count']>0 and case.get('sequence_position',0)==0:assert info['calls'].get('0x8e4a',0)>0
    if case['count']>4:
        assert info['calls'].get('0x8ff4')==1 and output[case['object']-BASE+0x1d]==0
    if case['coord']<8 and case.get('sequence_position',0)==0:assert info['calls'].get('0x43e38',0)>0

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/object_restart_full';folder.mkdir(parents=True,exist_ok=True);cases=build_cases();observer=Observer(program);rows=[];previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(program,case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1]);output,result,ports,info=observer.run(ram,regs);assert_evidence(case,ram,output,result,ports,info,regs)
        rf='native_%04d.bin'%index;pf='native_%04d.ports.bin'%index;(folder/rf).write_bytes(output);(folder/pf).write_bytes(ports)
        rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),result=result,input_ram_sha256=sha(ram),ram_file=rf,ram_sha256=sha(output),ports_file=pf,ports_sha256=sha(ports),port_count=len(ports)//9,**info))
        if 'sequence'in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
        if info['error']:break
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,cases=len(cases),completed_cases=sum(r['returned'] for r in rows),results=rows,failure=observer.error,program_code_modified=False,scope='Continuous original2a28/299c/8ff4/46ef4 andcleanup fallback toRTS, no patches/calleecontextresets. Original3ef2 seeds palette beforeentry; raw count/ref/link/coordinate/objectaliases are controlledfixtures. All15regs includingA5/A6 andorderedwatchdog recorded; native-only no CCR/callback execution/natural scheduling claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],failure=observer.error,sha256=sha(path.read_bytes()))))
    if observer.error:raise SystemExit(1)
if __name__=='__main__':main()
