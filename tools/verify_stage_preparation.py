"""Immutable native stage palette initialization and object cleanup boundaries."""
import hashlib,itertools,json,struct,subprocess,zlib
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from pack_main_startup import BASE as MAIN_BASE,END as MAIN_END
from pack_stage_palettes import BASE as STAGE_BASE,END as STAGE_END
from pack_palettes import extract
BASE,STACK,RETURN=0x100000,0x1feffc,0xff000
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3,m.UC_M68K_REG_A6)
KEYS=('d0','d1','d3','a6')
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/stage_preparation';folder.mkdir(parents=True,exist_ok=True)
    inp,out,portfile,report=[folder/n for n in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
    executable=root/'build/step_stage_preparation';binary_sha=hashlib.sha256(executable.read_bytes()).hexdigest()
    main_resource=root/'extracted/runtime/main_startup.ms5d';stage_resource=root/'extracted/runtime/stage_palettes.ms5d'
    hashes=[checked_resource(main_resource,program,MAIN_BASE,MAIN_END),checked_resource(stage_resource,program,STAGE_BASE,STAGE_END)]
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);cpu.mem_write(0x200000,program[0x200000:0x300000])
    trace,paths,rows,negatives,sequences=[],[],[],[],[];state={'stop':RETURN,'reads':0,'resource_conversion':False}
    def code(cpu,address,size,user):
        if address==state['stop']:cpu.emu_stop()
        elif address in (0xe7bf4,0x8da2,0x2a0a,0x2a84,0x299c,0x8ff4,0x43e38,0x3dce):paths.append(address)
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3a000f,0x3a001f) or 0x400000<=address<0x402000:trace.append((size,address,value&((1<<(8*size))-1)))
        elif address in (0x2ffff0,0x2ffff2):
            assert state['resource_conversion'] and size==2 and value in (0,0x1000),(hex(address),size,value)
            trace.append((size,address,value))
        else:assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
    def read(cpu,access,address,size,value,user):state['reads']+=1
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x300000,end=0x3fffff)
    cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);boot=bytes(cpu.mem_read(BASE,65536))
    def fixture(children=0,prior=False,references=0,coordinate=None):
        cpu.mem_write(BASE,boot);state['stop']=RETURN
        if prior:call(cpu,0xe7c36)
        for parent in (0x100b30,0x100bf4):
            for index in range(children):
                cpu.reg_write(m.UC_M68K_REG_A6,parent);cpu.reg_write(m.UC_M68K_REG_A0,0x1234);cpu.reg_write(m.UC_M68K_REG_D0,0);call(cpu,0x28ae)
                child=cpu.reg_read(m.UC_M68K_REG_A0);cpu.mem_write(child+0x1d,b'\0');cpu.mem_write(child+0x6c,b'\xff')
        for obj in (0x100bf4,0x102000):
            cpu.mem_write(obj+0x1d,b'\0')
            for index in range(references):
                cpu.reg_write(m.UC_M68K_REG_A6,obj);cpu.reg_write(m.UC_M68K_REG_D0,(7,263,519)[index%3]);cpu.reg_write(m.UC_M68K_REG_D1,0);call(cpu,0x8ebe)
        ram=bytearray(cpu.mem_read(BASE,65536));ram[0x7dec]=255;ram[0x4d91]=0xff
        if coordinate is not None:
            ram[0xbf4+0x6c]=coordinate;at=0xd4e6+coordinate*0x2c
            struct.pack_into('>5I',ram,at,0xffff0001,0x7fffffff,1,0x80000001,0)
            struct.pack_into('>II',ram,at+0x14,0x11112222,0x87654321);ram[at+0x24]=255;ram[0xd494]=0
        return ram
    def args(entry,values,mainfile=main_resource,stagefile=stage_resource):return [str(executable),str(entry)]+list(map(str,values))+list(map(str,(inp,out,portfile,mainfile,stagefile)))
    def compare(ram,entry,values,label):
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        trace.clear();paths.clear();state.update(stop=0x479ba if entry==0x479b0 else RETURN,reads=0)
        cpu.emu_start(entry,0xffffff,count=200000);assert cpu.reg_read(m.UC_M68K_REG_PC)==state['stop'],(label,hex(cpu.reg_read(m.UC_M68K_REG_PC)))
        assert cpu.reg_read(m.UC_M68K_REG_A7)==(STACK if entry==0x479b0 else STACK+4),(label,hex(cpu.reg_read(m.UC_M68K_REG_A7)))
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result['writes']=len(trace)
        inp.write_bytes(ram);actual=subprocess.run(args(entry,values),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();ports=b''.join(struct.pack('>BII',*event) for event in trace)
        if actual_ram!=expected or parsed!=result or portfile.read_bytes()!=ports:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,hex(entry),diff[:20],result,parsed,trace)))
        assert not state['reads']
        if entry in (0xe7c36,0x479b0):assert paths.count(0x8da2)==2 and 0xe7bf4 in paths
        if entry in (0x477c2,0x479b0):assert {0x2a0a,0x2a84,0x3dce}<=set(paths)
        rows.append(dict(profile=label,entry=entry,incoming=dict(zip(KEYS,values)),result=parsed,ports=trace.copy(),native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),tuple(parsed[key] for key in KEYS)
    high=((0,0,0),(0xabcd1234,0xfedcba98,0x87654321),(0xffffffff,0xffffffff,0xffffffff))
    for entry,children,prior,refs,registers in itertools.product((0xe7c36,0x477c2,0x479b0),(0,2),(False,True),(0,3),high):
        compare(fixture(children,prior,refs),entry,registers+(0x100b30,),'runtime-palette-and-nested-removal')
    for slot,entry in itertools.product(range(8),(0x477c2,0x479b0)):compare(fixture(2,True,3,slot),entry,high[1]+(0x100b30,),'fixed-object-coordinate-cleanup')
    for a6 in (0,1,0xffffffff):compare(fixture(),0xe7c36,high[1]+(a6,),'unused-arbitrary-a6-palette-entry')
    for children in (0,2):
        ram=fixture(children,True,3);values=high[1]+(0x100b30,);start=len(rows)
        combined,combined_regs=compare(ram,0x479b0,values,'combined-composition')
        ram,values=compare(ram,0xe7c36,values,'palette-cli-carry-to-cleanup');ram,values=compare(ram,0x477c2,values,'cleanup-cli-carried-registers')
        assert ram==combined and values==combined_regs
        for iteration in range(2):ram,values=compare(ram,0x479b0,values,'repeated-actual-cli-stage-preparation-carry')
        sequences.append(dict(calls=len(rows)-start,actual_cli_ram_full_d0_d1_d3_a6_carried=True,entry_context_reset_explicit=True))
    # Separate native resource evidence: actual e7c36 registers four new fixed slots.
    cpu.mem_write(BASE,boot);trace.clear();state.update(stop=RETURN,resource_conversion=True);call(cpu,0xe7c36);call(cpu,0x7196);call(cpu,0x72fa)
    records,_=extract(program);packed=(root/'extracted/runtime/palettes.ms5p').read_bytes();payload=b''.join(struct.pack('<I',identifier)+records[identifier][0]+records[identifier][1] for identifier in sorted(records))
    assert packed==struct.pack('<4s7I',b'MS5P',1,len(records),68,len(payload),zlib.crc32(payload)&0xffffffff,0,0)+payload
    resource_pvc_writes=[event for event in trace if event[1] in (0x2ffff0,0x2ffff2)]
    assert resource_pvc_writes==[(2,0x2ffff2,0x1000),(2,0x2ffff0,0)]*2,resource_pvc_writes
    resource_evidence=[]
    for slot,identifier in ((11,0x25f),(12,0x65),(13,0x67),(14,0x6a)):
        converted=bytes(cpu.mem_read(0x400000+slot*32,32));assert converted==records[identifier][1]
        resource_evidence.append(dict(slot=slot,source_id=identifier,native_color_sha256=hashlib.sha256(converted).hexdigest()))
    state['resource_conversion']=False
    sentinel=b'prior-output\0\xff'
    def reject(ram,entry=0x479b0,values=high[1]+(0x100b30,),mainfile=main_resource,stagefile=stage_resource,label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel);actual=subprocess.run(args(entry,values,mainfile,stagefile),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for entry in (0,0x479ba):reject(fixture(),entry=entry,label='unsupported-entry')
    for a6 in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(),values=high[1]+(a6,),label='invalid-removal-object')
    for index,value in itertools.product(range(4),('-1','4294967296','0x','1x','')):
        values=list(high[1]+(0x100b30,));values[index]=value;reject(fixture(),values=values,label='invalid-uint32')
    badfile=folder/'bad.ms5d'
    badfile.write_bytes(b'bad');reject(fixture(),stagefile=badfile,label='malformed-resource')
    raw=bytearray(stage_resource.read_bytes());raw[-1]^=1;badfile.write_bytes(raw);reject(fixture(),stagefile=badfile,label='resource-crc-error')
    raw=bytearray(stage_resource.read_bytes());struct.pack_into('>H',raw,32,256);struct.pack_into('<I',raw,24,zlib.crc32(raw[32:])&0xffffffff);badfile.write_bytes(raw)
    reject(fixture(),stagefile=badfile,label='late-stage-binding-slot-after-main-palette-work')
    ram=fixture();struct.pack_into('>H',ram,0x4d92+255*16+2,0x1012);reject(ram,label='corrupt-palette-backlink')
    ram=fixture();struct.pack_into('>I',ram,0xb38,0xdeadbeef);reject(ram,label='invalid-live-child-pointer')
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);portfile.write_bytes(sentinel);alias=inp if kind=='same' else folder/('alias-'+kind)
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        command=args(0x479b0,high[1]+(0x100b30,));command[7]=str(alias);actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and bytes(cpu.mem_read(0x200000,0xffff0))==program[0x200000:0x2ffff0]
    assert hashlib.sha256(executable.read_bytes()).hexdigest()==binary_sha
    report.write_text(json.dumps(dict(source=source,binary_sha256=binary_sha,resource_sha256=hashes,palette_resource_sha256=hashlib.sha256(packed).hexdigest(),cases=len(rows),ports=sum(row['result']['writes'] for row in rows),negative_cases=len(negatives),full_ram_d0_d1_d3_a6_ordered_ports_equal=True,program_code_modified=False,mmio_reads=0,carry_sequences=sequences,resource_conversion_evidence=resource_evidence,resource_conversion_pvc_writes=resource_pvc_writes,physical_bank_data_unchanged_range=[0x200000,0x2ffff0],physical_bank_source_rom_range=[0x200000,0x2ffff0],external_stack_endpoint_equal=True,resource_conversion_entries=[0x3ef2,0xe7c36,0x7196,0x72fa],results=rows,negative_results=negatives,scope='Native2790 and3ef2 establish fixtures; actual28ae adds controlled children and8ebe acquires normal shared references. Entry contexts are explicit standalone boundaries, not natural scheduling. All callees run original code; combined479b0 stops479ba before later stage body. CLI RAM/full returned registers carry over repeated preparation. Separate resource evidence compares four e7c36 registered slots with MS5P conversion; mapped physical palette window and fixed2MiB bank, no hardware timing/bank-device model. No other CPU register/CCR/BIOS/whole-stage claims.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),ports=sum(row['result']['writes'] for row in rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()
