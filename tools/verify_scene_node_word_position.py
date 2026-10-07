"""Original43e08 integer-word positioning, exact RAM/full-register differential."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_scene_command import REGS, KEYS
from verify_stage_catalog import SOURCE_SHA256
BASE, STACK, RETURN, ENTRY = 0x100000, 0x1feffc, 0xff000, 0x43e08
WORDS=(0,1,0x7fff,0x8000,0xffff)
HIGHS=(tuple(0x12340000+i*0x10000 for i in range(12)),
       (0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xfeedbeef))
def sha(data):return hashlib.sha256(data).hexdigest()
def build_cases():
    cases=[]
    for node in (0,0x1000,0xb30+0x2e,0xe98+0x2e,0x9156,0xd470,0xd480,0xffda):
        parents=(0,0x102000,BASE+node,BASE+node+4 if node<0xffda else 0x10ffd6,0x10d480)
        for parent,x,y,profile in itertools.product(parents,WORDS,WORDS,range(2)):
            cases.append(dict(family='word-boundaries-parent-self-overlap-stamp-alias',node=node,parent=parent,x=x,y=y,profile=profile))
    for parent in (0,0x102000,0x101000,0x101004):
        for frame in range(5):cases.append(dict(family='actual-cli-carry',node=0x1000,parent=parent,x=WORDS[frame],y=WORDS[4-frame],profile=1,sequence=str(parent),sequence_position=frame))
    assert len(cases)==2020
    return cases

def fixture(case):
    ram=bytearray(hashlib.shake_256(b'word-position'+bytes([case['profile']])).digest(65536));node=case['node'];parent=case['parent']
    struct.pack_into('>4I',ram,node+0x14,0x7fffffff,0x80000001,0xffff00ff,0x8000ffff)
    struct.pack_into('>H',ram,node+0x24,0xa5ff)
    if parent:
        at=parent-BASE;struct.pack_into('>II',ram,at+0x14,0xffff8001,0x7fffffff);ram[at+0x25]=0xc3
    ram[0xd494]=(0,255)[case['profile']]
    return ram

def values(case, previous=None):
    result=list(HIGHS[case['profile']] if previous is None else previous)
    result[0]=(0xabcd0000|case['x']);result[1]=(0x98760000|case['y']);result[8]=BASE+case['node'];result[9]=case['parent']
    return result

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256 and source['sha256']==SOURCE_SHA256
    exe=root/'build/step_scene_node_registers';binary=sha(exe.read_bytes());folder=root/'artifacts/scene_node_word_position';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report_path=(folder/name for name in ('input.bin','cpp.bin','verification.json'));report_path.unlink(missing_ok=True)
    cases=build_cases();cpu=make_cpu(program);baseline=cpu.context_save();rows=[];negatives=[];previous={};visits=[]
    def code(cpu,address,size,user):
        if address==RETURN:cpu.emu_stop()
        if address in (ENTRY,0x43e38,0x43e56,0x43e86):visits.append(address)
    def write(cpu,access,address,size,value,user):
        assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1])
        cpu.context_restore(baseline);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        visits.clear();cpu.emu_start(ENTRY,0xffffff,count=100000)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        assert cpu.reg_read(m.UC_M68K_REG_A5)==0x108000 and cpu.reg_read(m.UC_M68K_REG_A6)==0
        inp.write_bytes(ram);actual=subprocess.run([str(exe),str(ENTRY)]+list(map(str,regs))+list(map(str,(inp,out))),capture_output=True,text=True)
        assert actual.returncode==0 and inp.read_bytes()==ram,(index,actual.stderr)
        parsed=json.loads(actual.stdout);cpp=out.read_bytes()
        assert parsed==result and cpp==expected,(index,case,result,parsed,[(hex(i),a,b) for i,(a,b) in enumerate(zip(cpp,expected)) if a!=b][:20])
        assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
        rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),result=parsed,input_ram_sha256=sha(ram),ram_sha256=sha(cpp),native_calls=visits.copy(),final_pc=RETURN,final_a7=STACK+4,mmio_writes=0))
        if 'sequence'in case:previous[case['sequence']]=(cpp,tuple(parsed[key] for key in KEYS))
    assert len(rows)==len(cases)==2020 and all(r['case_index']==i and r['fixture']==cases[i] for i,r in enumerate(rows))
    sentinel=b'word-position-output-preserved\0\xff';case=cases[0];ram=fixture(case);regs=values(case)
    def reject(data,inputs,label):
        inp.write_bytes(data);out.write_bytes(sentinel);actual=subprocess.run([str(exe),str(ENTRY)]+list(map(str,inputs))+list(map(str,(inp,out))),capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==data and out.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,input_output_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),regs,'invalid-RAM-size')
    for pointer in (1,0x100001,0x10ffdc,0xffffffff):
        data=list(regs);data[8]=pointer;reject(ram,data,'invalid-node-span')
    for pointer in (1,0x100001,0x10ffdc,0xffffffff):
        data=list(regs);data[8]=0x101000;data[9]=pointer;reject(fixture(dict(case,node=0x1000)),data,'late-parent-after-local-writes-rollback')
    for register,text in itertools.product(range(12),('-1','4294967296','0x','1x','')):
        data=list(regs);data[register]=text;reject(ram,data,'invalid-register-parser')
    inp.write_bytes(ram);actual=subprocess.run([str(exe),str(ENTRY)]+list(map(str,regs))+list(map(str,(inp,inp))),capture_output=True,text=True)
    assert actual.returncode and inp.read_bytes()==ram;negatives.append(dict(failure='input-output-alias',input_output_preserved=True,native_executed=False))
    assert sha(exe.read_bytes())==binary and sha(program)==SOURCE_SHA256
    report=dict(source=source,binary_sha256=binary,cases=len(rows),negative_cases=len(negatives),full_ram_12_registers_equal=True,all_RTS_A7_valid=True,mmio_writes=0,original_rom_immutable=True,positive_input_RAM_preserved=True,cli_carry_sequences=len(previous),cli_carry_calls=20,cli_calls_consuming_previous_outputs=16,results=rows,negative_results=negatives,
        scope='Actual43e08 continuous through43e38 toRTS. Word XY inputs have unrelated nonzero highwords. Complete64KiBRAM/full12 exposed registers andA7+4 compare; MMIO forbidden. Null/ordinary/self/overlap/globalstamp aliases and validlower/upper spans are controlledfixtures. Placement object100b30+2e and allocator rejection sentinel100e98+2e are explicit addressfixtures, not actual placement allocation. CLI outputRAM/registers carry in4sequences; hostXY/parent updates and standalone stack/SR context resets are explicit. No natural scheduling or otherregister/CCR equivalence claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
