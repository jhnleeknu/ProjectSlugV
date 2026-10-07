"""Nativec654/c66a/c686/c6c0 to documented ready or BIOS entry boundaries."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256
from verify_game_prelude import empty_word,empty_byte
BASE,STACK=0x100000,0x1feffc
BOUNDARIES=(0xc724,0xc73e,0xc00444)
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3,m.UC_M68K_REG_A6)
KEYS=('d0','d1','d3','a6')
CALLS=(0x2a28,0x299c,0x2782,0x8ff4,0x46ef4,0x43e38,0x289e,0x314c,0xc4cc,0xcaf0,0xca76,0x28ae)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256 and program[0x180:0x182]==bytes(2)
    folder=root/'artifacts/game_ready';folder.mkdir(parents=True,exist_ok=True)
    inp,out,portfile,report=[folder/name for name in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_map(0xc00000,0x1000)
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    rows,negatives,sequences,ports,paths=[],[],[],[],[]
    def code(cpu,address,size,user):
        if address in BOUNDARIES:cpu.emu_stop()
        elif address in CALLS:paths.append(address)
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3c0000,0x3c0004):ports.append((size,address,value&((1<<(size*8))-1)))
        else:assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790)
    native_boot=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(bytes(65536));boot=root/'extracted/runtime/object_boot.ms5i'
    actual=subprocess.run([str(root/'build/init_objects'),str(boot),str(inp),str(out)],capture_output=True,text=True)
    assert not actual.returncode and out.read_bytes()==native_boot,actual.stderr
    call(cpu,0x3ef2);base_fixture=bytes(cpu.mem_read(BASE,65536))
    def fixture(mode=1,callback=0x477e4,freecount=80):
        ram=bytearray(base_fixture);ram[0x4cd4]=mode
        struct.pack_into('>I',ram,0xb30,callback);struct.pack_into('>H',ram,0x4ca0,freecount)
        return ram
    def compare(ram,entry,values,label):
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000)
        cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,(0xff000).to_bytes(4,'big'));cpu.reg_write(m.UC_M68K_REG_SR,0x2000)
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        ports.clear();paths.clear();cpu.emu_start(entry,0xffffff,count=100000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in BOUNDARIES,(label,hex(pc))
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        result.update(next_pc=pc,writes=len(ports));inp.write_bytes(ram)
        actual=subprocess.run([str(root/'build/step_game_ready'),str(entry)]+[str(value) for value in values]+[str(inp),str(out),str(portfile)],capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();data=portfile.read_bytes()
        actual_ports=[struct.unpack('>BII',data[at:at+9]) for at in range(0,len(data),9)]
        if actual_ram!=expected or actual_ports!=ports or parsed!=result:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,entry,diff[:16],result,parsed,len(ports),len(actual_ports))))
        assert result['a6']==values[3]
        if entry==0xc654:assert 0x2a28 in paths
        if entry in (0xc654,0xc66a):assert 0x289e in paths
        if pc==0xc73e and entry!=0xc6c0:
            assert {0xc4cc,0xcaf0,0xca76,0x28ae}<=set(paths)
            assert int.from_bytes(expected[values[3]-BASE:values[3]-BASE+4],'big')==0xc6c0
        rows.append(dict(profile=label,entry=entry,incoming=dict(zip(KEYS,values)),result=parsed,native_calls=paths.copy(),ports=ports.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),parsed
    highs=((0,0,0),(0xabcd1234,0xfedcba98,0x87654321))
    for entry,a6,mode,callback,values in itertools.product((0xc654,0xc66a,0xc686),(0x100820,0x1008e4),(0,1,2,255),(0,0x270e,0x1234),highs):
        ram=fixture(mode,callback)
        compare(ram,entry,values+(a6,),'runtime-predicate-active-inactive-mode')
    for a6,flag,values in itertools.product((0x100820,0x1008e4),(0,1,127,128,255),highs):
        ram=fixture();ram[a6-BASE+0x62]=flag
        compare(ram,0xc6c0,values+(a6,),'reentry-zero-or-bios-boundary')
    for entry,a6 in itertools.product((0xc654,0xc66a,0xc686),(0x100820,0x1008e4)):
        ram=fixture(0,0x270e,0);struct.pack_into('>I',ram,0x4c9c,0xdeadbeef)
        compare(ram,entry,(0xabcd1234,0x87654321,0xfedcba98,a6),'cleanup-allocation-normal-failure-invalid-unused-head')
    # Coordinate and real palette cleanup on fixed100b30 at c654.
    for slot,parent,stamp,current in itertools.product(range(8),(0,0x100200),(0,255),(0,255)):
        ram=fixture(1);ram[0xb9c]=slot;at=0xd4e6+slot*0x2c
        struct.pack_into('>5I',ram,at,0xffff0001,0x7fffffff,1,0x80000001,parent)
        struct.pack_into('>II',ram,at+0x14,0x11112222,0x87654321)
        ram[at+0x24]=stamp;ram[at+0x25]=0xa0;ram[0xd494]=current
        if parent:struct.pack_into('>II',ram,0x214,0x00010001,0x80000001);ram[0x225]=0x40
        compare(ram,0xc654,(0xabcd1234,0x87654321,0xfedcba98,0x1008e4),'fixed-object-coordinate-cleanup')
    for identifiers,shared in itertools.product(((7,),(7,263),(7,263,519,7)),(False,True)):
        ram=fixture(1);cpu.mem_write(BASE,bytes(ram))
        for obj in ((0xb30,0xda8) if shared else (0xb30,)):
            cpu.reg_write(m.UC_M68K_REG_A6,BASE+obj)
            for identifier in identifiers:
                cpu.reg_write(REGS[0],identifier);cpu.reg_write(REGS[1],0);call(cpu,0x8ebe)
        compare(bytearray(cpu.mem_read(BASE,65536)),0xc654,(0xabcd1234,0x87654321,0xfedcba98,0x1008e4),'fixed-object-palette-free-shared-cleanup')
    for a6 in (0x100820,0x1008e4):
        first=len(rows);ram,state=compare(fixture(0),0xc686,(0xabcd1234,0xfedcba98,0x87654321,a6),'actual-cli-cleanup-to-reentry')
        ram[a6-BASE+0x62]=255 # Explicit host fixture, callback e66aa is not executed.
        ram,state=compare(ram,0xc6c0,tuple(state[key] for key in KEYS),'actual-cli-reentry-bios-after-host-flag')
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_carried=True,host_input='controller+62byte ff',stored_callback_e66aa_not_executed=True))
    # Actual restart CLI state is the next c654 callback entry fixture.
    for a6 in (0x100820,0x1008e4):
        ram=fixture();inp.write_bytes(ram)
        records=root/'extracted/runtime/game_records.ms5d';streams=root/'extracted/runtime/input_streams.ms5d'
        args=[str(root/'build/restart_game'),'--phase','0','--a6',str(a6),'--state','0x47570','0xabcd1234','0x87654321','0xfedcba98','0','0',str(inp),str(out),str(portfile),str(records),str(streams)]
        restarted=subprocess.run(args,capture_output=True,text=True);assert not restarted.returncode,restarted.stderr
        parsed=json.loads(restarted.stdout);assert parsed['outer_phase']==2
        # Native c610 on the identical fixture validates the actual predecessor.
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A6,a6)
        for reg,value in zip(REGS,(0xabcd1234,0x87654321,0xfedcba98)):cpu.reg_write(reg,value)
        call(cpu,0xc610)
        assert bytes(cpu.mem_read(BASE,65536))==out.read_bytes()
        assert tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS)==tuple(parsed[key] for key in KEYS)
        first=len(rows);compare(bytearray(out.read_bytes()),0xc654,tuple(parsed[key] for key in KEYS),'actual-restart-cli-to-c654-callback-entry')
        sequences.append(dict(calls=len(rows)-first,predecessor_entry=0xc610,predecessor_ram_registers_native_equal=True,actual_cli_ram_registers_carried=True,invocation='explicit callback entry; no scheduler claim'))
    sentinel=b'old-game-ready-output\0\xff'
    def reject(ram,entry='0xc654',values=('0','0','0','0x1008e4'),label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel)
        actual=subprocess.run([str(root/'build/step_game_ready'),entry]+list(values)+[str(inp),str(out),str(portfile)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for bad in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(),values=('0','0','0',str(bad)),label='invalid-controller-pointer')
    ram=fixture();struct.pack_into('>H',ram,0xb40,1);reject(ram,label='fixed-object-depth-trap')
    ram=fixture();ram[0xb9c]=8;reject(ram,label='fixed-object-coordinate-trap')
    ram=fixture();struct.pack_into('>I',ram,0x4c9c,0xdeadbeef);reject(ram,entry='0xc686',label='late-allocation-invalid-freehead')
    ram=fixture();struct.pack_into('>I',ram,0x8ec,0xffffffff);reject(ram,entry='0xc686',label='late-invalid-controller-list-next')
    for field,bad in itertools.product(range(5),('-1','4294967296','0x','1x','')):
        args=['0xc654','0','0','0','0x1008e4'];args[field]=bad
        reject(fixture(),entry=args[0],values=args[1:],label='invalid-uint32-parser')
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        portfile.write_bytes(sentinel)
        actual=subprocess.run([str(root/'build/step_game_ready'),'0xc654','0','0','0','0x1008e4',str(inp),str(alias),str(portfile)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert set(BOUNDARIES)=={row['result']['next_pc'] for row in rows}
    assert set(CALLS)<={address for row in rows for address in row['native_calls']}
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entries_cpu_and_rom_offsets=[0xc654,0xc66a,0xc686,0xc6c0],stop_boundaries=list(BOUNDARIES),cases=len(rows),negative_cases=len(negatives),ports=sum(len(row['ports']) for row in rows),full_ram_d0_d1_d3_a6_ordered_ports_equal=True,carry_sequences=sequences,results=rows,negative_results=negatives,scope='Actual nested original calls execute to c724/c73e or BIOSc00444 before instruction execution. ROM180 remains canonical0; callbacks477e4/e66aa installed only, not executed. Runtime lists from original2790 checked against actual MS5I CLI; original3ef2/8ebe initialize cleanup resources. CLI state carries into explicit reentry and actual restart CLI carries into c654 callback entry; host sets+62 in reentry fixtures. No BIOS/scheduler/callback-body/other-register/CCR/stack equivalence claim. Malformed pointer and TRAP cases original execution excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),ports=sum(len(row['ports']) for row in rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
