"""Unmodified native object removal and nested cleanup differential verifier."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import m68k_const as mc
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256
BASE, RETURN, STACK = 0x100000,0xff000,0x1feffc
REGS=(mc.UC_M68K_REG_D0,mc.UC_M68K_REG_D1,mc.UC_M68K_REG_D3,mc.UC_M68K_REG_A6)
KEYS=('d0','d1','d3','a6')

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/object_removal';folder.mkdir(parents=True,exist_ok=True)
    inp,out,ports,report=[folder/name for name in ('input.bin','cpp.bin','ports.bin','verification.json')]
    report.unlink(missing_ok=True);executable=root/'build/remove_object'
    cpu=make_cpu(program);cpu.mem_map(0x300000,0x1000)
    rows,negatives,sequences,trace,paths=[],[],[],[],[]
    def code(cpu,address,size,user):
        if address==RETURN:cpu.emu_stop()
        elif address in (0x299c,0x2782,0x8ff4,0x46ef4,0x43e38,0x271c,0x287e,0x2a0a,0x2a84,0x3dce):paths.append(address)
    def write(cpu,access,address,size,value,user):
        if address==0x300001:
            assert size==1;trace.append((size,address,value&255))
        else:assert BASE<=address and address+size<=BASE+65536 or STACK-256<=address and address+size<=STACK+4,(hex(address),size,value)
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    cpu.mem_write(BASE,bytes(65536));call(cpu,0x3ef2)
    palette=bytes(cpu.mem_read(BASE,65536))
    def fixture(nodes=((0x820,0,1),(0x1200,1,1),(0x1400,0,1))):
        ram=bytearray(hashlib.shake_256(b'object-removal'+len(rows).to_bytes(4,'big')).digest(65536))
        ram[0x4d92:0x5da2]=palette[0x4d92:0x5da2]
        struct.pack_into('>I',ram,0x4c9c,0x101800);struct.pack_into('>H',ram,0x4ca0,4)
        for index,(offset,depth,active) in enumerate(nodes):
            struct.pack_into('>4I',ram,offset,0x1234 if active else 0x270e,BASE+nodes[index-1][0],BASE+nodes[(index+1)%len(nodes)][0],BASE+0x820)
            struct.pack_into('>H',ram,offset+0x10,depth);ram[offset+0x1d]=0;ram[offset+0x6c]=255
        return ram
    def compare(ram,entry,values,label,target=0x101200):
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(mc.UC_M68K_REG_A5,0x108000)
        cpu.reg_write(mc.UC_M68K_REG_A0,target);cpu.reg_write(mc.UC_M68K_REG_A7,STACK)
        cpu.reg_write(mc.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        trace.clear();paths.clear();cpu.emu_start(entry,0xffffff,count=100000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN and cpu.reg_read(mc.UC_M68K_REG_A7)==STACK+4,(label,hex(cpu.reg_read(mc.UC_M68K_REG_PC)))
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result['writes']=len(trace)
        inp.write_bytes(ram)
        actual=subprocess.run([str(executable),str(entry),str(target)]+[str(value) for value in values]+[str(inp),str(out),str(ports)],capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();data=ports.read_bytes()
        actual_ports=[struct.unpack('>BII',data[at:at+9]) for at in range(0,len(data),9)]
        if expected!=actual_ram or parsed!=result or actual_ports!=trace:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,entry,diff[:16],result,parsed,trace,actual_ports)))
        rows.append(dict(profile=label,entry=entry,target=target,incoming=dict(zip(KEYS,values)),result=parsed,ports=trace.copy(),native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),parsed
    highregs=((0,0,0),(0xabcd1234,0x87654321,0xfedcba98),(0xffffffff,0xffffffff,0xffffffff))
    profiles=(('static',((0x820,0,1),(0x1200,0,1),(0x1400,0,1)),0x101200),
              ('linked-leaf',((0x820,0,1),(0x1200,1,1),(0x1400,0,1)),0x101200),
              ('unsigned-depth-high',((0x820,0,1),(0x1200,0xffff,1),(0x1400,0x8000,1)),0x101200),
              ('parent-holds-children',((0x820,0,1),(0x1200,1,1),(0x1400,2,1),(0x1600,0,1)),0x101200),
              ('last-child-cascade',((0x820,0,1),(0x1200,1,0),(0x1400,2,0),(0x1600,3,1),(0x1800,0,1)),0x101600),
              ('active-previous-stops',((0x820,0,1),(0x1200,1,1),(0x1400,2,1),(0x1600,0,1)),0x101400))
    for label,nodes,obj in profiles:
        for values in highregs:compare(fixture(nodes),0x299c,values+(obj,),label)
    tree=((0x820,0,1),(0x1200,1,1),(0x1400,2,1),(0x1600,1,1),(0x1800,0,1))
    for depth in (0,1,0x7fff,0x8000):
        nodes=tuple((off,dep+depth if dep else 0,active) for off,dep,active in tree)
        for values in highregs:compare(fixture(nodes),0x2a0a,values+(0x100820,),'nested-subtree-live-traversal')
    static_tree=((0x820,0,1),(0x1200,0,1),(0x1400,1,1),(0x1600,2,1),(0x1800,0,1))
    for values in highregs:
        compare(fixture(static_tree),0x2a84,values+(0x100820,),'static-wrapper-preserves-incoming-a6',0x101200)
        compare(fixture(static_tree),0xc4cc,values+(0x100820,),'sentinel-list-cleanup')
    # Hold parent, then actual CLI child deletion returns parent to the free pool.
    for values in highregs:
        ram=fixture(((0x820,0,1),(0x1200,1,1),(0x1400,2,1),(0x1600,0,1)));first=len(rows)
        ram,state=compare(ram,0x299c,values+(0x101200,),'parent-request-held-actual-cli-carry')
        assert int.from_bytes(ram[0x1200:0x1204],'big')==0x270e and int.from_bytes(ram[0x4ca0:0x4ca2],'big')==4
        state['a6']=0x101400 # Explicit host selects the final child.
        ram,state=compare(ram,0x299c,tuple(state[key] for key in KEYS),'child-deletion-cascades-actual-cli-carry')
        assert int.from_bytes(ram[0x4ca0:0x4ca2],'big')==6
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_carried=True,host_input='second target A6'))
    def cleanup_fixture(deferred):
        return fixture(((0x820,0,1),(0x1200,1,1),(0x1400,2,1),(0x1600,0,1))) if deferred else fixture()
    for slot,parent,stamp,current,deferred in itertools.product(range(8),(0,0x100200),(0,1,255),(0,1,255),(False,True)):
        ram=cleanup_fixture(deferred);ram[0x126c]=slot;at=0xd4e6+slot*0x2c
        struct.pack_into('>5I',ram,at,0xffff0001,0x7fffffff,1,0x80000001,parent)
        struct.pack_into('>II',ram,at+0x14,0x11112222,0x87654321)
        ram[at+0x24]=stamp;ram[at+0x25]=0xa0;ram[0xd494]=current
        if parent:struct.pack_into('>II',ram,0x214,0x00010001,0x80000001);ram[0x225]=0x40
        before=len(rows)
        compare(ram,0x299c,(0xabcd1234,0xfedcba98,0x87654321,0x101200),'coordinate-cleanup-deferred-full-register-return' if deferred else 'coordinate-cleanup-all-slots-stamps-parent')
        if deferred:assert 0x271c not in rows[before]['native_calls'] and rows[before]['result']['a6']==0x101200
    for identifiers,shared,deferred in itertools.product(((7,),(7,263),(7,263,519,7)),(False,True),(False,True)):
        ram=cleanup_fixture(deferred);cpu.mem_write(BASE,bytes(ram))
        if shared:
            cpu.reg_write(mc.UC_M68K_REG_A6,0x101400)
            for identifier in identifiers:
                cpu.reg_write(mc.UC_M68K_REG_D0,identifier);cpu.reg_write(mc.UC_M68K_REG_D1,0);call(cpu,0x8ebe)
        cpu.reg_write(mc.UC_M68K_REG_A6,0x101200)
        for identifier in identifiers:
            cpu.reg_write(mc.UC_M68K_REG_D0,identifier);cpu.reg_write(mc.UC_M68K_REG_D1,0);call(cpu,0x8ebe)
        ram=bytearray(cpu.mem_read(BASE,65536))
        before=len(rows)
        compare(ram,0x299c,(0x12345678,0xabcd1234,0x98765432,0x101200),'palette-release-deferred-full-register-return' if deferred else 'palette-release-free-or-shared-actual-native-acquisition')
        if deferred:assert 0x271c not in rows[before]['native_calls'] and rows[before]['result']['a6']==0x101200
    # Actual28ae allocation followed by299c, with runtime palette/coordinate disabled.
    ram=fixture(((0x820,0,1),(0x1400,0,1)));struct.pack_into('>I',ram,0x4c9c,0x101200);struct.pack_into('>I',ram,0x1208,0x101800)
    ram[0x121d]=0;ram[0x126c]=255
    cpu.mem_write(BASE,bytes(ram));cpu.reg_write(mc.UC_M68K_REG_A0,0x1234);cpu.reg_write(mc.UC_M68K_REG_A6,0x100820);cpu.reg_write(mc.UC_M68K_REG_D0,0xabcd0000)
    call(cpu,0x28ae);expected_alloc=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram)
    allocated=subprocess.run([str(root/'build/allocate_object'),'0xabcd0000','0x1234','0','0x100820',str(inp),str(out)],capture_output=True,text=True)
    assert not allocated.returncode and out.read_bytes()==expected_alloc,allocated.stderr
    allocation=json.loads(allocated.stdout);first=len(rows)
    ram,state=compare(bytearray(out.read_bytes()),0x299c,(allocation['d0'],0x87654321,0xfedcba98,allocation['a0']),'actual-allocator-cli-to-removal')
    assert int.from_bytes(ram[0x4ca0:0x4ca2],'big')==4
    sequences.append(dict(calls=len(rows)-first,allocator_entry=0x28ae,actual_cli_ram_d0_target_carried=True,other_registers_explicit_fixture=True))
    sentinel=b'old-removal-output\0\xff'
    def reject(ram,entry='0x299c',target='0x101200',values=('0','0','0','0x101200'),label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);ports.write_bytes(sentinel)
        actual=subprocess.run([str(executable),entry,target]+list(values)+[str(inp),str(out),str(ports)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for pointer in (0,0x100001,0x10ff3e,0x110000,0xffffffff):reject(fixture(),values=('0','0','0',str(pointer)),label='invalid-object-pointer')
    for field in (4,8):
        ram=fixture();struct.pack_into('>I',ram,0x1200+field,0xffffffff);reject(ram,label='late-invalid-linked-pointer')
    for index in (8,127):ram=fixture();ram[0x126c]=index;reject(ram,label='coordinate-trap')
    ram=fixture();ram[0x121d]=5;reject(ram,label='palette-count-overflow')
    ram=fixture();ram[0x126c]=0;struct.pack_into('>I',ram,0xd4f6,0xffffffff);reject(ram,label='late-coordinate-parent-pointer')
    for offset in (0x820,0x1200):
        ram=fixture();struct.pack_into('>H',ram,offset+0x10,1);reject(ram,entry='0x2a84',values=('0','0','0','0x100820'),label='static-wrapper-depth-trap')
    ram=fixture(((0x820,0,1),(0x1200,0,1)));struct.pack_into('>I',ram,0x1208,0x101200);reject(ram,entry='0xc4cc',values=('0','0','0','0x100820'),label='sentinel-traversal-cycle-rejected-without-running-native')
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for field,bad in itertools.product(range(6),('-1','4294967296','0x','1x','')):
        args=['0x299c','0x101200','0','0','0','0x101200'];args[field]=bad
        reject(fixture(),entry=args[0],target=args[1],values=args[2:],label='invalid-uint32-parser')
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        ports.write_bytes(sentinel)
        actual=subprocess.run([str(executable),'0x299c','0','0','0','0','0x101200',str(inp),str(alias),str(ports)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and ports.read_bytes()==sentinel
        negatives.append(dict(failure='ram-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    observed=set(address for row in rows for address in row['native_calls'])
    assert {0x2782,0x8ff4,0x46ef4,0x43e38,0x271c,0x287e,0x2a0a,0x2a84,0x3dce}<=observed
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entries_cpu_and_rom_offsets=[0x299c,0x2a0a,0x2a84,0xc4cc],cases=len(rows),negative_cases=len(negatives),ordered_watchdog_writes=sum(row['result']['writes'] for row in rows),full_ram_d0_d1_d3_a6_ports_equal=True,carry_sequences=sequences,results=rows,negative_results=negatives,scope='All nested original callees execute; watchdog writes compared in order. Synthetic valid lists cover hold/cascade/live traversal; native palette initialization/acquisition establishes cleanup resources. Actual CLI RAM/register outputs carried with explicit second-call target selection. Actual allocator CLI RAM/D0/allocated target connects28ae to299c. No callback bodies/scheduler/other registers/CCR/stack equivalence claimed. Malformed or cyclic input original execution intentionally excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),ports=sum(row['result']['writes'] for row in rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
