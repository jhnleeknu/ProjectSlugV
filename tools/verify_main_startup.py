"""Native immutable e4a startup, fixed-slot head insertion and CLI state carry."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import m68k_const as mc
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from pack_main_startup import BASE as TABLE_BASE,END as TABLE_END,validate_payload
from pack_palettes import extract

BASE,ENTRY,NEXT,RETURN,STACK=0x100000,0xe4a,0xe74,0xff000,0x1feffc
REGS=(mc.UC_M68K_REG_D0,mc.UC_M68K_REG_D1,mc.UC_M68K_REG_D3)

def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    executable=root/'build/start_main';resource=root/'extracted/runtime/main_startup.ms5d'
    resource_hash=checked_resource(resource,program,TABLE_BASE,TABLE_END)
    table=validate_payload(program[TABLE_BASE:TABLE_END]);fixed_slots={record['slot'] for record in table}
    folder=root/'artifacts/main_startup';folder.mkdir(parents=True,exist_ok=True)
    inp,out,ports_out,report=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_write(0x200000,program[0x200000:0x300000])
    ports,rows,sequences,negatives,integrations=[],[],[],[],[]
    state={'stop':RETURN,'bank':0x200000,'video':0,'video_reads':0}
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3c0000,0x3c0004,0x2ffff0,0x2ffff2):
            ports.append((size,address,value&((1<<(size*8))-1)))
            if address==0x2ffff2:
                state['bank']=((value>>12)+1)*0x100000
                cpu.mem_write(0x200000,program[state['bank']:state['bank']+0xffff0])
        elif not (BASE<=address and address+size<=BASE+65536) and not (0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write '+repr((hex(address),size,value)))
    def read(cpu,access,address,size,value,user):
        assert address==0x3c0006 and size==2
        state['video_reads']+=1;cpu.mem_write(address,state['video'].to_bytes(2,'big'))
    def code(cpu,address,size,user):
        if address==state['stop']: cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x3c0006,end=0x3c0006)
    def native_call(entry):
        state['stop']=RETURN;cpu.reg_write(mc.UC_M68K_REG_A5,0x108000);cpu.reg_write(mc.UC_M68K_REG_A7,STACK)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.emu_start(entry,RETURN,count=100000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN
    def initialized(seed):
        cpu.mem_write(BASE,hashlib.shake_256(b'main-startup-initial:'+bytes([seed])).digest(65536))
        native_call(0x3ef2)
        return bytearray(cpu.mem_read(BASE,65536))
    def acquire(ram,count,flags=1):
        cpu.mem_write(BASE,bytes(ram))
        for index in range(count):
            obj=0x102000+(index//4)*0x40
            if index%4==0: cpu.mem_write(obj+0x1d,b'\0')
            cpu.reg_write(mc.UC_M68K_REG_A6,obj)
            cpu.reg_write(mc.UC_M68K_REG_D0,(0x62,0x162,0x203,0x87a,1,0x101)[index%6]);cpu.reg_write(mc.UC_M68K_REG_D1,flags)
            native_call(0x8ebe)
        return bytearray(cpu.mem_read(BASE,65536))
    def preset(ram):
        cpu.mem_write(BASE,bytes(ram));native_call(0xe7bf4)
        return bytearray(cpu.mem_read(BASE,65536))
    def arguments(obj,registers,selected=resource):
        return [str(executable)]+[str(value) for value in registers]+[str(obj),str(inp),str(out),str(ports_out),str(selected)]
    def compare(ram,obj,registers,profile):
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A6,BASE+obj),(mc.UC_M68K_REG_A7,STACK)):
            cpu.reg_write(reg,value)
        for reg,value in zip(REGS,registers): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));ports.clear();state.update(stop=NEXT,video_reads=0)
        cpu.emu_start(ENTRY,RETURN,count=100000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==NEXT
        assert tuple(cpu.reg_read(reg) for reg in (mc.UC_M68K_REG_A5,mc.UC_M68K_REG_A6,mc.UC_M68K_REG_A7))==(0x108000,BASE+obj,STACK)
        expected=bytes(cpu.mem_read(BASE,65536));values=[cpu.reg_read(reg)&0xffffffff for reg in REGS]
        assert len(ports)==2 and all(event[:2]==(1,0x300001) for event in ports) and not state['video_reads']
        result=dict(zip(('d0','d1','d3'),values));result.update(next_pc=NEXT,writes=len(ports))
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        inp.write_bytes(ram);actual=subprocess.run(arguments(obj,registers),capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();actual_ports=ports_out.read_bytes()
        if actual_ram!=expected or actual_ports!=expected_ports or parsed!=result:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,obj,diff[:16],result,parsed,ports,actual_ports.hex())))
        preserved_normal=[]
        for slot in range(256):
            at=0x4d92+slot*16
            if slot not in fixed_slots and 0<struct.unpack_from('>H',ram,at+8)[0]<65535:
                assert actual_ram[at+8:at+16]==ram[at+8:at+16]
                preserved_normal.append(slot)
        rows.append(dict(profile=profile,object_offset=obj,incoming_registers=list(registers),result=parsed,normal_non_target_slots_preserved=preserved_normal,ports=ports.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),input_sha256=hashlib.sha256(ram).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest(),a5_a6_a7_preserved=True))
        return bytearray(actual_ram),tuple(parsed[key] for key in ('d0','d1','d3')),cpu.context_save()
    incoming=((0,0,0),(0xabcdabff,0xdead1234,0xbeefffff),(0xffffffff,0xffffffff,0xffffffff),(0x12345678,0x98768000,0x76547000))
    for seed,prior_fixed,normal_count,obj,registers in itertools.product((0,1),(False,True),(0,8,25),(0,0x820,0xf5c,0xff7a),incoming):
        ram=initialized(seed)
        if prior_fixed: ram=preset(ram)
        if normal_count: ram=acquire(ram,normal_count)
        compare(ram,obj,registers,'initialized-lists-fixed-and-normal-reference-mixtures')
    for flags in (0,1,2,0x80,0xff):
        ram=acquire(preset(initialized(2)),20,flags)
        first=len(rows);registers=(0x123456ab,0xabcdabff,0x9876fedc)
        for frame in range(3): ram,registers,context=compare(ram,0x820,registers,'three-actual-cli-startup-register-ram-carry')
        sequences.append(dict(calls=len(rows)-first,flags=flags,actual_cli_ram_full_d0_d1_d3_carried=True,native_context_reset_at_explicit_startup_boundary=True))
    # Connect the actual startup outputs and original native continuation to preparation.
    palette=root/'extracted/runtime/palettes.ms5p'
    records,_=extract(program);payload=b''.join(struct.pack('<I',identifier)+records[identifier][0]+records[identifier][1] for identifier in sorted(records))
    assert palette.read_bytes()==struct.pack('<4s7I',b'MS5P',1,len(records),68,len(payload),zlib.crc32(payload)&0xffffffff,0,0)+payload
    for prior_fixed in (False,True):
        ram=initialized(3)
        if prior_fixed: ram=preset(ram)
        # Controlled valid unrelated producer/pool state; startup itself leaves these fields alone.
        for at in (0x4d8a,0x4d8c,0x4d74,0x4d76,0x8d34,0x8d36,0x8d38,0x8d3a,0x914e,0x7dea): struct.pack_into('>H',ram,at,0)
        ram[0x8d3c]=0xa1;ram[0x8d3d]=0;ram[0x7dd4]=0;ram[0x7ded]=0
        for pool,lower,upper in ((0x8d3e,0,190),(0x8d46,190,380)): struct.pack_into('>4H',ram,pool,lower,upper,lower,upper)
        for obj in (0x109156,0x10b1d6,0x10d256,0x10d2d6):
            at=obj-BASE;ram[at+0x25]=0
            for field in (0x14,0x18,0x7c,0x7e): struct.pack_into('>H',ram,at+field,0)
        ram,registers,context=compare(ram,0x820,incoming[1],'startup-before-preparation')
        cpu.context_restore(context);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(REGS[1],registers[1]);cpu.reg_write(REGS[2],registers[2])
        ports.clear();state.update(stop=0xec4,video=0xffff,video_reads=0)
        cpu.emu_start(NEXT,RETURN,count=1000000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==0xec4 and state['video_reads']==1
        expected=bytes(cpu.mem_read(BASE,65536));expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        result=dict(next_pc=0xec4,d1=cpu.reg_read(REGS[1])&0xffffffff,d3=cpu.reg_read(REGS[2])&0xffffffff,writes=len(ports),sound=dict(kind=0,phase=0,low=0,cursor=0,waiting=False,command=0,tail=0,next=0),sprite=dict(waiting=False,cursor=0))
        inp.write_bytes(ram)
        command=[str(root/'build/prepare_main_frame'),'--state',str(NEXT),str(registers[1]),str(registers[2]),'65535',str(inp),str(out),str(ports_out),str(palette)]
        actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout)
        assert out.read_bytes()==expected and ports_out.read_bytes()==expected_ports and parsed==result,(result,parsed)
        integrations.append(dict(prior_fixed=prior_fixed,result=parsed,actual_startup_cli_ram_d1_d3_carried=True,native_continued_at_e74_without_context_reset=True,video_reads=state['video_reads'],ram_sha256=hashlib.sha256(expected).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest()))
    sentinel=b'prior-main-startup-output\0\xff'
    def reject(ram,obj=0x820,registers=incoming[1],selected=resource,label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);ports_out.write_bytes(sentinel)
        actual=subprocess.run(arguments(obj,registers,selected),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports_out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,original_executed=False))
    for size in (0,65535,65537): reject(bytes(size),label='invalid-ram-size')
    for obj in (1,0xff7b,0xff7c,0xffffffff): reject(initialized(0),obj=obj,label='invalid-object-span-or-alignment')
    for index,invalid in itertools.product(range(3),('-1','4294967296','0x100000000','0x','1x','')):
        registers=list(incoming[1]);registers[index]=invalid;reject(initialized(0),registers=registers,label='invalid-register-uint32')
    malformed=folder/'bad.ms5d'
    malformed.write_bytes(b'bad');reject(initialized(0),selected=malformed,label='malformed-resource')
    for byte_offset,newword in ((17*6,0),(16*6,256)):
        payload=bytearray(program[TABLE_BASE:TABLE_END]);struct.pack_into('>H',payload,byte_offset,newword)
        malformed.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,TABLE_BASE,TABLE_BASE,len(payload),zlib.crc32(payload)&0xffffffff,0)+payload)
        reject(initialized(0),selected=malformed,label='late-invalid-table-slot-or-terminator')
    bad=initialized(0);struct.pack_into('>H',bad,0x4d92+255*16+2,0x1012)
    reject(bad,label='corrupt-late-node-backlink')
    for alias_kind in ('same','hardlink','symlink'):
        good=initialized(0);inp.write_bytes(good);ports_out.write_bytes(sentinel)
        alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=arguments(0x820,incoming[1]);command[command.index(str(out))]=str(alias)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good and ports_out.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+alias_kind+'-alias',outputs_preserved=True,original_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert bytes(cpu.mem_read(0x200000,0xffff0))==program[state['bank']:state['bank']+0xffff0]
    assert any(row['normal_non_target_slots_preserved'] for row in rows)
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_address=ENTRY,stop_cpu_address=NEXT,binding_resource_sha256=resource_hash,binding_table_cpu_address=TABLE_BASE,binding_table_rom_offset=TABLE_BASE,cases=len(rows),watchdog_ports=sum(len(row['ports']) for row in rows),full_ram_d0_d1_d3_ordered_ports_equal=True,carry_sequences=sequences,preparation_integrations=integrations,negative_cases=len(negatives),negative_results=negatives,results=rows,scope='Initialized palette rings are native3ef2 fixtures; existing fixed bindings use actuale7bf4 and normal references use actual8ebe. e4a startup executes unmodified original code and stops beforee74. Head-prepend bucket links, target conversion and non-target normal references are compared over whole RAM. Repeated startup carries actual CLI RAM/full D0/D1/D3 with explicit entry context resets; preparation integrations continue the same native context and carry CLI RAM/D1/D3. Only D0/D1/D3 plus preserved A5/A6/A7 boundary evidence and ordered hardware writes are claimed, excluding boot scheduling, arbitrary callback execution, BIOS/RTE, CPU flags and timing.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),ports=sum(len(row['ports']) for row in rows),preparation_integrations=len(integrations),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__': main()
