"""Native c52a/c560 game initialization and actual IRQ-released palette fill wait."""
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

BASE,ENTRY,NEXT,RETURN,STACK=0x100000,0xc52a,0xc584,0xff000,0x1feffc
REGS=(mc.UC_M68K_REG_D0,mc.UC_M68K_REG_D1,mc.UC_M68K_REG_D3)

def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    executable=root/'build/step_game_startup';resource=root/'extracted/runtime/main_startup.ms5d'
    resource_hash=checked_resource(resource,program,TABLE_BASE,TABLE_END)
    table=validate_payload(program[TABLE_BASE:TABLE_END]);fixed_slots={record['slot'] for record in table}
    folder=root/'artifacts/game_startup';folder.mkdir(parents=True,exist_ok=True)
    inp,out,ports_out,bank_in,bank_out,regs_in,report=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin','banks.bin','cpp.banks.bin','regs.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_map(0x400000,8192);cpu.mem_map(0xd00000,4096);cpu.mem_write(0x200000,program[0x200000:0x300000])
    ports,rows,sequences,negatives,irq_rows=[],[],[],[],[]
    physical={'display':0,'banks':[bytearray(8192),bytearray(8192)]}
    reads=[]
    state={'stop':RETURN,'bank':0x200000,'video':0,'video_reads':0}
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3c0000,0x3c0004,0x2ffff0,0x2ffff2,0x320000,0x3a000f,0x3a001f,0x3a0001,0x3a0011) or 0x400000<=address<0x402000:
            ports.append((size,address,value&((1<<(size*8))-1)))
            if address==0x2ffff2:
                state['bank']=((value>>12)+1)*0x100000
                cpu.mem_write(0x200000,program[state['bank']:state['bank']+0xffff0])
            elif address in (0x3a000f,0x3a001f):
                physical['display']=int(address==0x3a001f);cpu.mem_write(0x400000,bytes(physical['banks'][physical['display']]))
            elif 0x400000<=address<0x402000:
                at=address-0x400000;physical['banks'][physical['display']][at:at+size]=(value&((1<<(size*8))-1)).to_bytes(size,'big')
        elif not (BASE<=address and address+size<=BASE+65536) and not (0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write '+repr((hex(address),size,value)))
    def read(cpu,access,address,size,value,user):
        assert size==1 and address in (0x320000,0xd00046)
        cpu.mem_write(address,b'\0');reads.append((size,address,0))
    def code(cpu,address,size,user):
        if address in (state['stop'],RETURN): cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x320000,end=0x320000);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
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
    fill=root/'extracted/runtime/palette_fill.ms5p'
    from pack_palette_fill import extract as extract_fill
    fill_records,fill_base,fill_lookup=extract_fill(program)
    fill_payload=b''.join(struct.pack('<I',identifier)+fill_records[identifier][0]+fill_records[identifier][1] for identifier in sorted(fill_records))
    assert fill.read_bytes()==struct.pack('<4s7I',b'MS5P',1,len(fill_records),68,len(fill_payload),zlib.crc32(fill_payload)&0xffffffff,0,0)+fill_payload
    def arguments(obj,registers,pc=ENTRY,selected=resource,selected_fill=fill):
        return [str(executable),str(pc),str(obj)]+[str(value) for value in registers]+[str(inp),str(out),str(ports_out),str(selected_fill),str(selected)]
    def compare(ram,obj,registers,profile,pc=ENTRY):
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A6,BASE+obj),(mc.UC_M68K_REG_A7,STACK)):
            cpu.reg_write(reg,value)
        for reg,value in zip(REGS,registers): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));ports.clear();state.update(stop=NEXT,video_reads=0)
        cpu.emu_start(pc,RETURN,count=100000)
        native_pc=cpu.reg_read(mc.UC_M68K_REG_PC)
        assert native_pc in (NEXT,RETURN),hex(native_pc)
        assert tuple(cpu.reg_read(reg) for reg in (mc.UC_M68K_REG_A5,mc.UC_M68K_REG_A6,mc.UC_M68K_REG_A7))==(0x108000,BASE+obj,STACK+(4 if native_pc==RETURN else 0))
        expected=bytes(cpu.mem_read(BASE,65536));values=[cpu.reg_read(reg)&0xffffffff for reg in REGS]
        if native_pc==RETURN: assert values[1:]==list(registers[1:])
        assert ports==[(2,0x2ffff2,0x1000),(2,0x2ffff0,0),(2,0x2ffff2,0x1000),(2,0x2ffff0,0)] if pc==ENTRY else (len(ports)==2 and all(event[:2]==(1,0x300001) for event in ports) if native_pc==NEXT else not ports)
        result=dict(zip(('d0','d1','d3'),values));result.update(next_pc=0xc560 if native_pc==RETURN else NEXT,writes=len(ports))
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        inp.write_bytes(ram);actual=subprocess.run(arguments(obj,registers,pc),capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();actual_ports=ports_out.read_bytes()
        if actual_ram!=expected or actual_ports!=expected_ports or parsed!=result:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,obj,diff[:16],result,parsed,ports,actual_ports.hex())))
        preserved_normal=[]
        for slot in range(256):
            at=0x4d92+slot*16
            if native_pc==NEXT and slot not in fixed_slots and 0<struct.unpack_from('>H',ram,at+8)[0]<65535:
                assert actual_ram[at+8:at+16]==ram[at+8:at+16]
                preserved_normal.append(slot)
        rows.append(dict(profile=profile,input_pc=pc,fill_counter_before=struct.unpack_from('>H',ram,0x7dea)[0],fill_counter_after=struct.unpack_from('>H',actual_ram,0x7dea)[0],object_offset=obj,incoming_registers=list(registers),result=parsed,normal_non_target_slots_preserved=preserved_normal,ports=ports.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),input_sha256=hashlib.sha256(ram).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest(),a5_a6_preserved_stack_return_accounted=True))
        return bytearray(actual_ram),tuple(parsed[key] for key in ('d0','d1','d3')),cpu.context_save()
    incoming=((0,0,0),(0xabcdabff,0xdead1234,0xbeefffff),(0xffffffff,0xffffffff,0xffffffff),(0x12345678,0x98768000,0x76547000))
    for prior_fixed,normal_count,obj,registers in itertools.product((False,True),(0,20),(0x820,0x8e4,0xff7c),incoming):
        ram=initialized(0)
        if prior_fixed: ram=preset(ram)
        if normal_count: ram=acquire(ram,normal_count)
        compare(ram,obj,registers,'initial-fill-full-highword-shift')
    for high in (0x0001,0x07ff,0x0800):
        compare(initialized(0),0x8e4,(high<<16|0x1234,0xabcdabff,0x9876fedc),'full-d0-lsl32-upper-boundaries')
    for counter,registers in itertools.product((0,1,0x2000,0x8000,0xffff),incoming):
        ram=acquire(preset(initialized(1)),20);struct.pack_into('>H',ram,0x7dea,counter)
        compare(ram,0x8e4,registers,'poll-counter-boundaries-ready-fixed-and-normal',pc=0xc560)
    regs=[getattr(mc,'UC_M68K_REG_'+kind+str(index)) for kind in ('D','A') for index in range(8)]
    def interrupt(ram,banks,context,render,profile):
        cpu.context_restore(context);saved_registers=[cpu.reg_read(reg)&0xffffffff for reg in regs]
        cpu.mem_write(BASE,bytes(ram));physical['banks']=[bytearray(banks[:8192]),bytearray(banks[8192:])]
        assert physical['display']==0
        cpu.mem_write(0x400000,banks[:8192])
        irq_registers=list(struct.unpack('>16I',hashlib.shake_256(b'game-startup-irq:'+len(irq_rows).to_bytes(4,'big')).digest(64)))
        irq_registers[0],irq_registers[13],irq_registers[15]=0x12345678,0x108000,0x1fcffc
        for reg,value in zip(regs,irq_registers): cpu.reg_write(reg,value)
        cpu.reg_write(mc.UC_M68K_REG_SR,0x2000);cpu.mem_write(0x1fcffc,RETURN.to_bytes(4,'big'))
        state['stop']=RETURN;ports.clear();reads.clear();cpu.emu_start(0xc8c,RETURN,count=1000000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN and reads==[(1,0x320000,0)]
        expected=bytes(cpu.mem_read(BASE,65536));expected_banks=b''.join(physical['banks'])
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        result=dict(service_phase=0,display_bank=physical['display'],sound_reads=1,task_registers=[0]*16,task=dict(next_pc=0,restored=False,stack_address=[0,0],stack_value=[0,0]),pending=dict.fromkeys(('kind','phase','low','cursor','command','tail','next'),0))
        inp.write_bytes(ram);bank_in.write_bytes(banks);regs_in.write_bytes(struct.pack('>16I',*irq_registers))
        command=[str(root/'build/step_interrupt'),'begin',str(inp),str(bank_in),str(regs_in),str(out),str(bank_out),str(ports_out),'0','0']
        actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout)
        assert out.read_bytes()==expected and bank_out.read_bytes()==expected_banks and ports_out.read_bytes()==expected_ports and parsed==result,(result,parsed)
        assert struct.unpack_from('>H',expected,0x7dea)[0]==(0 if render else 0x2000)
        irq_rows.append(dict(profile=profile,render=render,result=parsed,ports=len(ports),fill_counter_before=struct.unpack_from('>H',ram,0x7dea)[0],fill_counter_after=struct.unpack_from('>H',expected,0x7dea)[0],palette_changed=expected_banks!=banks,ram_sha256=hashlib.sha256(expected).hexdigest(),banks_sha256=hashlib.sha256(expected_banks).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest()))
        cpu.context_restore(context);assert [cpu.reg_read(reg)&0xffffffff for reg in regs]==saved_registers
        return bytearray(out.read_bytes()),bank_out.read_bytes(),context
    for prior_fixed,registers in itertools.product((False,True),incoming):
        ram=initialized(2)
        if prior_fixed: ram=preset(ram)
        ram=acquire(ram,20)
        # Initial valid unrelated IRQ state. The host never writes fill counter after this point.
        ram[0x1b],ram[0x19],ram[0x7dec],ram[0xf001],ram[0x8d3d]=0,0,0,0,0
        for at in (0x4d74,0x4d76,0x4d8a,0x4d8c,0xd68c,0x8d34,0x8d36): struct.pack_into('>H',ram,at,0)
        struct.pack_into('>I',ram,0x81c,0x10081c)
        ram[0x4d7b],ram[0xf003],ram[0x14]=0,0,0
        for obj in (0x109156,0x10b1d6,0x10d256,0x10d2d6): ram[obj-BASE+0x7a]=0
        physical['display']=0;banks=hashlib.shake_256(b'game-startup-physical-banks').digest(16384)
        first=len(rows);ram,registers,context=compare(ram,0x8e4,registers,'actual-irq-released-fill-start')
        ram,registers,context=compare(ram,0x8e4,registers,'unchanged-fill-wait',pc=0xc560)
        ram,banks,context=interrupt(ram,banks,context,False,'render-disabled-retains-fill-wait')
        ram,registers,context=compare(ram,0x8e4,registers,'disabled-irq-still-waiting',pc=0xc560)
        ram[0x1b]|=128 # Explicit host render gate release; not a counter mutation.
        ram,banks,context=interrupt(ram,banks,context,True,'actual-irq-palette-fill-completes')
        ram,registers,context=compare(ram,0x8e4,registers,'irq-released-ready-seed-boundary',pc=0xc560)
        assert rows[-1]['result']['next_pc']==NEXT
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_full_d0_d1_d3_palette_banks_carried=True,no_host_fill_counter_write=True,render_gate_host_enabled=True))
    sentinel=b'previous-game-startup-output\0\xff'
    def reject(ram,obj=0x8e4,registers=incoming[1],pc=ENTRY,selected=resource,selected_fill=fill,label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);ports_out.write_bytes(sentinel)
        actual=subprocess.run(arguments(obj,registers,pc,selected,selected_fill),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports_out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,original_executed=False))
    for size in (0,65535,65537): reject(bytes(size),label='invalid-ram-size')
    for obj in (1,0xff7d,0xff7e,0xffffffff): reject(initialized(0),obj=obj,label='invalid-object-span-or-alignment')
    for pc in (0,0xc52b,0xc56e,0xc584): reject(initialized(0),pc=pc,label='unsupported-entry')
    for index,invalid in itertools.product(range(3),('-1','4294967296','0x','1x','')):
        registers=list(incoming[1]);registers[index]=invalid;reject(initialized(0),registers=registers,label='invalid-register-uint32')
    malformed=folder/'bad.ms5d';malformed.write_bytes(b'bad')
    reject(initialized(0),selected_fill=malformed,label='invalid-fill-resource')
    ready=initialized(0);struct.pack_into('>H',ready,0x7dea,0)
    reject(ready,pc=0xc560,selected=malformed,label='invalid-ready-binding-resource')
    bad=bytearray(ready);struct.pack_into('>H',bad,0x4d92+255*16+2,0x1012)
    reject(bad,pc=0xc560,label='late-invalid-binding-node')
    for alias_kind in ('same','hardlink','symlink'):
        good=initialized(0);inp.write_bytes(good);ports_out.write_bytes(sentinel)
        alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=arguments(0x8e4,incoming[1]);command[command.index(str(out))]=str(alias)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good and ports_out.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+alias_kind+'-alias',outputs_preserved=True,original_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert bytes(cpu.mem_read(0x200000,0xffff0))==program[state['bank']:state['bank']+0xffff0]
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_addresses=[ENTRY,0xc560],stop_before_cpu_address=NEXT,binding_resource_sha256=resource_hash,fill_resource_sha256=hashlib.sha256(fill.read_bytes()).hexdigest(),cases=len(rows),startup_ports=sum(len(row['ports']) for row in rows),irq_calls=len(irq_rows),irq_ports=sum(row['ports'] for row in irq_rows),negative_cases=len(negatives),negative_results=negatives,carry_sequences=sequences,results=rows,irq_results=irq_rows,scope='Native c52a fill setup and c560 polling stop at caller return while counter nonzero or c584 before47570. Full RAM/D0/D1/D3 and ordered writes are compared. Native initialized palette rings/fixed bindings/normal references are controlled fixtures. Actual native c8c and equivalent CLI release fill counter, with full RAM/physical banks/display/MMIO compared and saved main registers restored by host; no host counter writes after initialization. The host explicitly enables render1b.bit7 after one disabled service. Callback invocation stack is explicitly reset between c560 polls; no47570 execution, boot scheduler, BIOS/SR/RTE, natural IRQ timing or general CPU-register claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),startup_ports=sum(len(row['ports']) for row in rows),irq_calls=len(irq_rows),irq_ports=sum(row['ports'] for row in irq_rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__': main()
