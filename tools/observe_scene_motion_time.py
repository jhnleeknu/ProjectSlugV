"""Original19802 observations; canonical strict and separately relocated RAM paths."""
import hashlib
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_scene_command import REGS, KEYS
from verify_stage_catalog import SOURCE_SHA256, checked_resource
BASE, STACK, RETURN, ENTRY = 0x100000, 0x1feffc, 0xff000, 0x19802
SCRATCH, FIXED = 0x106000, 0x60000
HIGHS = ((0,)*12, (0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xfeedbeef))
def sha(data): return hashlib.sha256(data).hexdigest()
def build_cases(program, root):
    manifest=json.loads((root/'extracted/runtime/scene_scripts/manifest.json').read_text()); cases=[]; paths=[]
    for item in manifest['dependencies']:
        if not item['file'].startswith('motion_'): continue
        path=root/'extracted/runtime/scene_scripts'/item['file']; data=checked_resource(path,program,item['source_cpu_address'],item['end_exclusive'])
        data=path.read_bytes()[32:]; paths.append((path,item['source_cpu_address'],data))
    assert len(paths)==37
    for path,address,data in paths:
        count=(len(data)-4)//10
        for index in range(count):
            time,kind,duration,x,y=struct.unpack_from('>5H',data,index*10)
            nexttime=struct.unpack_from('>H',data,(index+1)*10)[0]
            for target in sorted({(time-1)&65535,time,(time+1)&65535,(nexttime-1)&65535,nexttime,(nexttime+1)&65535}):
                for profile in range(2):
                    cases.append(dict(family='canonical-cursor-boundary',path_file=str(path.relative_to(root)),cpu=address,cursor=address+index*10,profile=profile,target=target,fraction=(0,0x8000)[profile],base=(0,0xffff)[profile],relocated=False))
        for direction in (1,-1):
            times=[struct.unpack_from('>H',data,i*10)[0] for i in range(count+1)]
            if direction<0: times.reverse()
            for position,target in enumerate(times):
                cases.append(dict(family='canonical-cli-carry',sequence=path.name+str(direction),sequence_position=position,path_file=str(path.relative_to(root)),cpu=address,cursor=address+(0 if direction>0 else count-1)*10,profile=1,target=target,fraction=0xffff,base=0x8000,relocated=False))
    for profile in range(2):cases.append(dict(family='null',path_file=str(paths[0][0].relative_to(root)),cpu=paths[0][1],cursor=0,profile=profile,target=0,fraction=0,base=0,relocated=False))
    for kind in range(0,0x90,4):
        raw=b''.join(struct.pack('>5H',t,k,10,x,y) for t,k,x,y in ((0,0x14,0xffff,0x8000),(10,kind,0x7fff,0xffff),(20,0x14,0x8000,1)))+struct.pack('>2H',30,0xffff)
        for cursor in (0,10,20):
            for target in (0,9,10,11,19,20,29,30,0x8000,0xffff):
                cases.append(dict(family='relocated-RAM-all36-types',path_file='synthetic.ms5d',cpu=FIXED,cursor=FIXED+cursor,profile=1,target=target,fraction=0xffff,base=0x7fff,relocated=True,payload_hex=raw.hex()))
    return cases

def fixture(case):
    ram=bytearray(hashlib.shake_256(b'motion-time'+bytes([case['profile']])).digest(65536))
    struct.pack_into('>IHH',ram,0xd3b4,case['cursor'],case['base'],case['base'])
    if case['relocated']:
        raw=bytes.fromhex(case['payload_hex']);ram[SCRATCH-BASE:SCRATCH-BASE+len(raw)]=raw
    return ram

def incoming(case, ram, previous=None):
    values=list(HIGHS[case['profile']] if previous is None else previous)
    cursor=int.from_bytes(ram[0xd3b4:0xd3b8],'big')
    raw=bytes.fromhex(case['payload_hex']) if case['relocated'] else incoming.program
    offset=cursor-FIXED if case['relocated'] else cursor
    if cursor:
        time,kind=struct.unpack_from('>HH',raw,offset)
        difference=(case['target']-time)&65535
        xbase,ybase=struct.unpack_from('>HH',ram,0xd3b8)
        coord=((((xbase if kind<0x58 else ybase)+(difference if kind<0x2c or 0x58<=kind<0x74 else -difference))&65535)<<16)|case['fraction']
        if kind<0x58:values[0]=coord
        else:values[1]=coord
    return values

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    incoming.program=program;cases=build_cases(program,root);folder=root/'artifacts/scene_motion_time';folder.mkdir(parents=True,exist_ok=True)
    cpu=make_cpu(program);baseline=cpu.context_save();rows=[];calls={};writes=[]
    def code(cpu,address,size,user):
        if address==RETURN:cpu.emu_stop()
        if address in (0x19812,0x196de,0x196ac,0x18efa,0x1972a,0x1982a):calls[address]=calls.get(address,0)+1
    def write(cpu,access,address,size,value,user):
        assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(address,size,value)
        writes.append((size,address,value))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);previous={}
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(case) if prior is None else bytearray(prior[0]);values=incoming(case,ram,None if prior is None else prior[1]);native=bytearray(ram)
        if case['relocated']:struct.pack_into('>I',native,0xd3b4,SCRATCH+case['cursor']-FIXED)
        cpu.context_restore(baseline);cpu.mem_write(BASE,bytes(native));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        calls.clear();writes.clear();error=None
        try:cpu.emu_start(ENTRY,0xffffff,count=200000)
        except unicorn.UcError as failure:error=str(failure)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));output=bytearray(cpu.mem_read(BASE,65536))
        assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
        if pc!=RETURN:
            failure=dict(source=source,case_index=index,fixture=case,incoming=values,pc=pc,error=error,calls=calls,instruction_cap=200000,native_returned=False)
            (folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise RuntimeError(failure)
        assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        if case['relocated']:
            struct.pack_into('>I',output,0xd3b4,int.from_bytes(output[0xd3b4:0xd3b8],'big')-SCRATCH+FIXED);result['a1']=result['a1']-SCRATCH+FIXED
        assert result['d0']==values[0] and result['d1']==values[1]
        path=folder/('ram_%05d.bin'%index);path.write_bytes(output)
        rows.append(dict(case_index=index,fixture=case,input_ram_sha256=sha(ram),incoming=values,result=result,ram_file=path.name,ram_sha256=sha(output),calls={hex(k):v for k,v in calls.items()},final_pc=pc,final_a7=STACK+4,mmio_writes=0))
        if 'sequence'in case:previous[case['sequence']]=(output,tuple(result[k] for k in KEYS))
    assert any(r['calls'].get('0x19812',0)>1 for r in rows)
    assert any(r['calls'].get('0x196de',0) for r in rows)
    report=dict(source=source,cases=len(rows),completed_cases=len(rows),results=rows,smoke=False,fixed_rom_immutable=True,mmio_writes=0,scope='Uninterrupted original19802 toRTS. Canonical strict; synthetic paths in RAM106000 normalize only A1 and RAMd3b4 tofixed60000. Standalone context reset only. XY updates are explicit controlled fixtures; not natural motion scheduling. Native observations, not C++ equivalence.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
