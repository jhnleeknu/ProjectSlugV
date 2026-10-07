"""Differential native28ae object allocation; no ROM or callable substitution."""
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
from verify_stage_catalog import SOURCE_SHA256

BASE, ENTRY, RETURN, STACK = 0x100000, 0x28ae, 0xff000, 0x1feffc
REGS = (mc.UC_M68K_REG_D0, mc.UC_M68K_REG_A0, mc.UC_M68K_REG_A1, mc.UC_M68K_REG_A6)
KEYS = ('d0', 'a0', 'a1', 'a6')

def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    folder = root/'artifacts/object_allocation'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder/name for name in ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    executable = root/'build/allocate_object'
    cpu = make_cpu(program)
    rows, negatives, sequences, paths = [], [], [], []
    def code(cpu, address, size, user):
        if address == RETURN: cpu.emu_stop()
        elif address in (0x2908, 0x2912): paths.append(address)
    def write(cpu, access, address, size, value, user):
        assert BASE <= address and address+size <= BASE+65536 or STACK-16 <= address and address+size <= STACK+4, (hex(address), size, value)
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    def fixture(count=4, depth=0, inherited=0, positions=(0x200,0x400,0x800)):
        ram = bytearray(hashlib.shake_256(b'object-allocation'+len(rows).to_bytes(4,'big')).digest(65536))
        parent, node, successor = positions
        struct.pack_into('>I', ram, 0x4c9c, BASE+node)
        struct.pack_into('>H', ram, 0x4ca0, count)
        struct.pack_into('>I', ram, parent+8, BASE+successor)
        struct.pack_into('>H', ram, parent+0x10, depth)
        ram[parent+0x6a] = inherited
        for index in range(3):
            current = node+index*0x100
            struct.pack_into('>I', ram, current+8, BASE+current+0x100)
        struct.pack_into('>I', ram, successor+4, BASE+parent)
        return ram
    def compare(ram, values, label, request_mode=False):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in zip(REGS, values): cpu.reg_write(reg, value)
        cpu.reg_write(mc.UC_M68K_REG_A5, 0x108000 if request_mode else 0xdeadbeef)
        cpu.reg_write(mc.UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(mc.UC_M68K_REG_A7, STACK)
        cpu.mem_write(STACK, RETURN.to_bytes(4,'big'))
        paths.clear()
        cpu.emu_start(0x4fb1a if request_mode else ENTRY, 0xffffff, count=1000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC) == RETURN
        assert cpu.reg_read(mc.UC_M68K_REG_A7) == STACK+4
        assert cpu.reg_read(mc.UC_M68K_REG_A5) == 0x108000
        assert len(paths) == 1 or request_mode and not paths
        carry = bool(cpu.reg_read(mc.UC_M68K_REG_SR)&1)
        assert carry == bool(paths and paths[0] == 0x2908), (paths, cpu.reg_read(mc.UC_M68K_REG_SR))
        expected = bytes(cpu.mem_read(BASE,65536))
        result = dict(zip(KEYS, (cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        result['carry'] = carry
        inp.write_bytes(ram)
        actual = subprocess.run([str(executable)]+(['--request'] if request_mode else [])+[str(value) for value in values]+[str(inp),str(out)],capture_output=True,text=True)
        assert not actual.returncode, (label,actual.stderr)
        parsed = json.loads(actual.stdout)
        actual_ram = out.read_bytes()
        if actual_ram != expected or parsed != result:
            diff = [(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,values,diff[:16],result,parsed)))
        rows.append(dict(profile=label,incoming=dict(zip(KEYS,values)),result=parsed,request_mode=request_mode,carry_instruction=paths[0] if paths else None,ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram), parsed
    for count, request, high, callback in itertools.product((0,1,2,0x7fff,0x8000,0xffff),(0,1,2,0x7fff,0x8000,0xffff),(0,0xabcd0000),(0,0x1234,0x10000,0xffff0000)):
        compare(fixture(count,0xffff,0xa5),(high|request,callback,0xfedcba98,BASE+0x200),'unsigned-threshold-and-full-callback')
    for depth, inherited, positions in itertools.product((0,1,0x7fff,0x8000,0xffff),(0,1,0x80,0xff),((0x200,0x400,0x800),(0x100,0x1000,0xf000),(0xf000,0x100,0x800))):
        compare(fixture(4,depth,inherited,positions),(0xabcd0000,0x80000000,0x87654321,BASE+positions[0]),'depth-wrap-inheritance-node-gaps')
    for count,request,callback in ((0,0,1),(1,1,1),(0xffff,0xffff,1),(4,0,0)):
        ram=fixture(count);struct.pack_into('>I',ram,0x4c9c,0xdeadbeef)
        compare(ram,(0xabcd0000|request,callback,0xffffffff,0xffffffff),'normal-failure-bypasses-invalid-head-parent')
    for depth in (0,0xffff):
        ram=fixture(3,depth,0xab);first=len(rows)
        state=dict(d0=0xabcd0000,a0=0x12345678,a1=0xffffffff,a6=BASE+0x200)
        for index in range(3):
            # Request/callback are explicit host inputs; all other state is actual CLI output.
            state['d0']=(state['d0']&0xffff0000)|0
            state['a0']=0x12345678+index
            ram,state=compare(ram,tuple(state[key] for key in KEYS),'three-allocations-actual-cli-carry')
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_carried=True,host_inputs='callback and request lowword'))
    for positions in ((0x200,0x200,0x800),(0x200,0x800,0x800),(0x200,0x400,0x200),(0x200,0x4c90,0x800)):
        compare(fixture(4,0xffff,0x80,positions),(0xabcd0000,0x1234,0xffffffff,BASE+positions[0]),'controlled-pointer-alias-native-write-order')
    for enabled, selector, count, high in itertools.product((0,1,255),(0,1,2,255),(0,1,4),(0,0xabcd0000)):
        ram=fixture(count,0xffff,0x80);ram[0xfd82]=enabled;ram[1]=selector
        compare(ram,(high|0x7654,0xdeadbeef,0xffffffff,BASE+0x200),'conditional-request-wrapper',True)
    for enabled, selector in ((0,1),(1,0),(1,2)):
        ram=fixture();ram[0xfd82]=enabled;ram[1]=selector
        struct.pack_into('>I',ram,0x4c9c,0xdeadbeef)
        compare(ram,(0xabcdffff,0,0xffffffff,BASE+0x200),'wrapper-bypasses-unused-invalid-free-head',True)
    # Native2790 establishes actual runtime freepool, compared before allocation.
    boot=root/'extracted/runtime/object_boot.ms5i';ram=bytearray(65536)
    cpu.mem_write(BASE,bytes(ram));cpu.reg_write(mc.UC_M68K_REG_A7,STACK)
    cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.emu_start(0x2790,0xffffff,count=50000)
    assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN
    expected_boot=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram)
    initialized=subprocess.run([str(root/'build/init_objects'),str(boot),str(inp),str(out)],capture_output=True,text=True)
    assert not initialized.returncode and out.read_bytes()==expected_boot,initialized.stderr
    ram=bytearray(out.read_bytes());assert int.from_bytes(ram[0x4ca0:0x4ca2],'big')==80
    first=len(rows);state=dict(d0=0xabcd0000,a0=0x1234,a1=0xffffffff,a6=0x100820)
    for expected_count in (79,78):
        state['d0'] &= 0xffff0000;state['a0']=0x1234
        ram,state=compare(ram,tuple(state[key] for key in KEYS),'native2790-runtime-pool-actual-cli-carry')
        assert int.from_bytes(ram[0x4ca0:0x4ca2],'big')==expected_count
    sequences.append(dict(calls=len(rows)-first,initializer_entry=0x2790,initializer_ram_equal=True,free_counts=[80,79,78],actual_cli_ram_registers_carried=True,host_inputs='callback and request lowword; initial allocator registers explicit'))
    sentinel=b'old-object-allocation-output\0\xff'
    def reject(ram, values=('0','1','0','0x100200'),label='invalid',request_mode=False):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        actual=subprocess.run([str(executable)]+(['--request'] if request_mode else [])+list(values)+[str(inp),str(out)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,native_executed=False))
    for pointer in (0,0x100001,0x10ff96,0x110000,0xffffffff):
        ram=fixture();struct.pack_into('>I',ram,0x4c9c,pointer);reject(ram,label='invalid-used-free-head')
    for pointer in (0,0x100001,0x10ff96,0x110000,0xffffffff):
        reject(fixture(),('0','1','0',str(pointer)),label='invalid-used-parent')
    for pointer in (0,0x100001,0x10fffa,0x110000,0xffffffff):
        ram=fixture();struct.pack_into('>I',ram,0x208,pointer);reject(ram,label='late-invalid-successor')
    for pointer in (0,0x100001,0x10ff9e,0x110000,0xffffffff):
        ram=fixture(0);ram[0xfd82]=1;ram[1]=1
        reject(ram,('0','1','0',str(pointer)),label='wrapper-late-invalid-parent-after-normal-allocation-failure',request_mode=True)
    for size in (0,65535,65537): reject(bytes(size),label='invalid-ram-size')
    for field,invalid in itertools.product(range(4),('-1','4294967296','0x100000000','0x','1x','')):
        values=['0','1','0','0x100200'];values[field]=invalid;reject(fixture(),values,label='invalid-register-parser')
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        actual=subprocess.run([str(executable),'0','1','0','0x100200',str(inp),str(alias)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram
        negatives.append(dict(failure='input-output-'+kind+'-alias',output_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert any(row['result']['carry'] for row in rows) and any(not row['result']['carry'] for row in rows)
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,entry_cpu_addresses=[ENTRY,0x4fb1a,0x2790],entry_rom_offsets=[ENTRY,0x4fb1a,0x2790],program_code_modified=False,cases=len(rows),negative_cases=len(negatives),full_ram_d0_a0_a1_a6_carry_equal=True,mmio_writes=0,carry_sequences=sequences,results=rows,negative_results=negatives,scope='Unmodified native28ae and4fb1a run to actual RTS. Direct/active wrapper carry checked against native2908/2912 and final SR bit0; inactive wrapper final SR carryfalse independently observed. Complete RAM and exposed full registers match. Independent call-boundary native contexts; actual CLI RAM/register output carried across repeated allocations with callback/request supplied explicitly by host. One native2790 initializer is compared with actual MS5I CLI RAM before allocations consume runtime pool80 to79 to78; initializer register outputs are not claimed. Controlled pointer aliases test native read/write order, not natural allocator use. Malformed pointers rejected without executing original. Other CPU registers/flags, callback execution and scheduling excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),sequences=len(sequences),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
