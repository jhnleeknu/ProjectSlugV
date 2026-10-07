"""Compare immutable native1879c and continuous1ae56 coordinate preparation."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK = 0x100000, 0xff000, 0x1feffc
OBJECTS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)
REGS = (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/refresh_column_controls'
    folder = root / 'artifacts/column_prepare'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in ('input.bin','cpp.bin','cpp.ports.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x2f0000, 0x10000)
    cpu.mem_map(0x3c0000,0x1000)
    writes, objects, rows, negatives, sequences = [], [], [], [], []
    def write(cpu, access, address, size, value, user):
        if address in (0x2ffff0,0x2ffff2):
            assert size == 2
            writes.append((size,address,value & 65535))
        elif address==0x3c0000:
            assert size==4
            writes.append((size,address,value & 0xffffffff))
        elif not (BASE <= address and address+size <= BASE+65536) and not (0x1fe000 <= address and address+size <= 0x1ff000):
            raise ValueError('Unexpected native write: '+repr((address,size,value)))
    def code(cpu,address,size,user):
        if address==RETURN: cpu.emu_stop()
        elif address==0x1879c: objects.append(cpu.reg_read(UC_M68K_REG_A0)&0xffffffff)
    cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    cpu.hook_add(UC_HOOK_CODE,code,begin=RETURN,end=RETURN)
    cpu.hook_add(UC_HOOK_CODE,code,begin=0x1879c,end=0x1879c)
    def fixture():
        return bytearray(hashlib.shake_256(b'ms5-column-prepare-v1:'+len(rows).to_bytes(4,'big')).digest(65536))
    def object_state(ram,address,selector=0,flags=0,x=0,y=0,changes=0):
        at=address-BASE
        for offset,value in ((0x14,x),(0x18,y),(0x7c,((x-(selector&1))&65535) ^ (1 if changes&1 else 0)),(0x7e,((y-((selector>>1)&1))&65535) ^ (1 if changes&2 else 0))):
            struct.pack_into('>H',ram,at+offset,value)
        ram[at+0x25],ram[at+0x7a]=selector,flags
    def arguments(address,registers,scene=False):
        return [str(executable),'--prepare',str(registers[1]),str(registers[2])]+(['--scene'] if scene else [])+[str(inp),str(out),str(ports)]+([] if scene else [str(address)])+[str(registers[0])]
    def compare(ram,address=0x100100,registers=None,scene=False,profile='matrix'):
        registers=registers if registers is not None else (((len(rows)*0x1234567)^0xabcd1234)&0xffffffff,((len(rows)*0x7341123)^0xdeadffff)&0xffffffff,((len(rows)*0x3141592)^0xbeefabcd)&0xffffffff)
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((UC_M68K_REG_SR,0x2000),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A7,STACK),(UC_M68K_REG_A0,address)):
            cpu.reg_write(reg,value)
        for reg,value in zip(REGS,registers): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        writes.clear();objects.clear()
        cpu.emu_start(0x1ae56 if scene else 0x1879c,RETURN,count=10000)
        assert cpu.reg_read(UC_M68K_REG_PC)==RETURN
        assert objects==list(OBJECTS) if scene else objects==[address]
        expected=bytes(cpu.mem_read(BASE,65536))
        expected_registers=[cpu.reg_read(reg)&0xffffffff for reg in REGS]
        expected_ports=b''.join(struct.pack('>BII',*write) for write in writes)
        expected_result=dict(zip(('d0','d1','d3'),expected_registers))
        expected_result['writes']=len(writes)
        assert expected_registers[2]==0
        if scene:
            assert writes==[(2,0x2ffff2,0x2000),(2,0x2ffff0,0),(2,0x2ffff2,0x1000),(2,0x2ffff0,0)]
            assert expected[0x10:0x12]==b'\0\0'
        else: assert not writes
        inp.write_bytes(ram)
        actual=subprocess.run(arguments(address,registers,scene),capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout)
        actual_ram,actual_ports=out.read_bytes(),ports.read_bytes()
        if actual_ram!=expected or actual_ports!=expected_ports or parsed!=expected_result:
            differences=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((profile,scene,address,differences[:16],expected_result,parsed)))
        states=[]
        for obj in OBJECTS if scene else (address,):
            at=obj-BASE
            states.append({'object':obj,'selector':ram[at+0x25],'flags_before':ram[at+0x7a],'flags_after':expected[at+0x7a],'x_changed':expected[at+0x7c:at+0x7e]!=ram[at+0x7c:at+0x7e],'y_changed':expected[at+0x7e:at+0x80]!=ram[at+0x7e:at+0x80]})
        rows.append({'profile':profile,'scene':scene,'objects':states,'incoming_registers':list(registers),'result':parsed,'port_events':len(writes),'input_sha256':hashlib.sha256(ram).hexdigest(),'ram_sha256':hashlib.sha256(expected).hexdigest(),'ports_sha256':hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(actual_ram),tuple(parsed[key] for key in ('d0','d1','d3'))
    for selector,changes in itertools.product(range(256),range(4)):
        ram=fixture()
        object_state(ram,0x100100,selector,selector^0xa5,0,0xffff,changes)
        compare(ram,profile='all256-selector-and-flag-bytes-all-cache-combinations')
    for axis,value,selector,changes in itertools.product(('x','y'),(0,1,0x7fff,0x8000,0xfffe,0xffff),range(4),range(4)):
        ram=fixture()
        object_state(ram,0x100100,selector,0x55,value if axis=='x' else 0x1234,value if axis=='y' else 0x9876,changes)
        compare(ram,profile='coordinate-sign-word-wrap-'+axis)
    for address,value in itertools.product((0x100000,0x100002,0x10ff80),(0,0xffff)):
        ram=fixture();object_state(ram,address,3,0x7f,value,value,3)
        compare(ram,address,profile='object-boundaries')
    isolated=len(rows)
    for combination,selector in itertools.product(range(16),range(4)):
        ram=fixture()
        for index,address in enumerate(OBJECTS):
            object_state(ram,address,selector,index*73,0x7fff+index,0xffff-index,3 if combination&(1<<index) else 0)
        ram,registers=compare(ram,scene=True,profile='scene-all16-changed-object-combinations')
        compare(ram,registers=registers,scene=True,profile='scene-unchanged-following-cli-output-carry')
    for scene in (False,True):
        for seed in (0,0xffff):
            ram=fixture();registers=(0xabcd1234,0xdeadffff,0xbeefabcd)
            begin=len(rows)
            addresses=OBJECTS if scene else (0x100100,)
            for address in addresses: object_state(ram,address,0,0x11,seed,seed,0)
            for frame in range(16):
                for index,address in enumerate(addresses):
                    at=address-BASE
                    # Explicit host coordinate updates; caches remain prior CLI output.
                    struct.pack_into('>H',ram,at+0x14,(seed+frame*0x1234+index)&65535)
                    struct.pack_into('>H',ram,at+0x18,(seed-frame*0x4321-index)&65535)
                    ram[at+0x25]=frame&3
                ram,registers=compare(ram,registers=registers,scene=scene,profile='cpp-ram-full-register-coordinate-carry')
                ram,registers=compare(ram,registers=registers,scene=scene,profile='cpp-unchanged-coordinate-following-call')
            sequences.append({'scene':scene,'seed':seed,'calls':len(rows)-begin,'cpp_ram_full_d0_d1_d3_outputs_carried':True,'host_updates_only_coordinates_and_selector':True})
    refresh_results=[]
    for combination in (1,2,5,15):
        ram=fixture()
        for index,address in enumerate(OBJECTS):
            object_state(ram,address,3,1,0xffff-index,0x7fff+index,3 if combination&(1<<index) else 0)
            struct.pack_into('>H',ram,address-BASE+0x26,index)
        ram,registers=compare(ram,scene=True,profile='prepare-to-refresh-dirty-flag-production')
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((UC_M68K_REG_SR,0x2000),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A7,STACK)):
            cpu.reg_write(reg,value)
        for reg,value in zip(REGS,registers): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        writes.clear();objects.clear()
        cpu.emu_start(0x1adf8,RETURN,count=10000)
        assert cpu.reg_read(UC_M68K_REG_PC)==RETURN
        expected=bytes(cpu.mem_read(BASE,65536))
        expected_ports=b''.join(struct.pack('>BII',*write) for write in writes)
        expected_d0=cpu.reg_read(UC_M68K_REG_D0)&0xffffffff
        inp.write_bytes(ram)
        actual=subprocess.run([str(executable),'--scene',str(inp),str(out),str(ports),str(registers[0])],capture_output=True,text=True)
        assert not actual.returncode and out.read_bytes()==expected and ports.read_bytes()==expected_ports and json.loads(actual.stdout)=={'d0':expected_d0,'writes':len(writes)},(combination,actual.stdout,actual.stderr)
        changed_count=sum(bool(combination&(1<<index)) for index in range(4))
        assert len(writes)==4+64*changed_count
        assert all(not expected[address-BASE+0x7a]&128 for address in OBJECTS)
        refresh_results.append({'combination':combination,'active_objects':changed_count,'port_events':len(writes),'result_d0':expected_d0,'whole_ram_d0_and_ordered_ports_equal':True,'ram_sha256':hashlib.sha256(expected).hexdigest(),'ports_sha256':hashlib.sha256(expected_ports).hexdigest(),'scope':'Ends at legacy refresh return; final D1/D3 are not exposed by that API and are not claimed.'})
    sentinel=b'prior-column-prepare-output\0\xff'
    def reject(label,ram,address=0x100100,custom_args=None):
        inp.write_bytes(ram);out.write_bytes(sentinel);ports.write_bytes(sentinel)
        actual=subprocess.run(custom_args or arguments(address,(0,0,0)),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append({'failure':label,'outputs_preserved':True,'original_executed':False})
    for address in (0xffffe,0x100001,0x10ff82,0x110000,0xffffffff): reject('invalid-object',fixture(),address)
    for size in (0,65535,65537): reject('invalid-ram-size',bytes(size))
    for index in (2,3,8):
        for invalid in ('-1','4294967296','0x100000000','0x','1x',''):
            command=arguments(0x100100,(0,0,0));command[index]=invalid
            reject('invalid-register',fixture(),custom_args=command)
    for alias_kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);ports.write_bytes(sentinel)
        alias=inp if alias_kind=='same' else folder/(alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=arguments(0x100100,(0,0,0));command[5]=str(alias)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and ports.read_bytes()==sentinel
        negatives.append({'failure':'input-output-'+alias_kind+'-alias','outputs_preserved':True,'original_executed':False})
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    observed_cache_changes={(item['x_changed'],item['y_changed']) for row in rows for item in row['objects']}
    assert observed_cache_changes==set(itertools.product((False,True),repeat=2))
    report.write_text(json.dumps({'source':source,'emulator':'Unicorn '+unicorn.__version__,'program_code_modified':False,'entry_cpu_addresses':[0x1879c,0x1ae56],'entry_rom_offsets':[0x1879c,0x1ae56],'cases':len(rows),'isolated_cases':isolated,'ordered_port_events':sum(row['port_events'] for row in rows)+sum(row['port_events'] for row in refresh_results),'prepare_refresh_integration_cases':len(refresh_results),'prepare_refresh_results':refresh_results,'negative_cases':len(negatives),'preparation_whole_ram_full_d0_d1_d3_ordered_ports_equal':True,'native_four_scene_object_order_asserted':True,'actual_cache_change_combinations':sorted(observed_cache_changes),'output_carry_sequences':sequences,'negative_results':negatives,'results':rows,'scope':'Unmodified coordinate preparation1879c and four-object wrapper1ae56. All256 selector bytes and dirty flag bytes, cached X/Y equality/change combinations, signed/unsigned word wrap and aligned work-RAM boundaries. WholeRAM, fullD0/D1/D3 and ordered PVC words compared. Four sequences carry actual CLI RAM/full-register outputs; host supplies new coordinates and selector bytes only. Four prepare→refresh1adf8 cases prove dirty-bit production and consumption, comparing final RAM/D0/ports only and ending there because the legacy refresh API does not expose D1/D3. Other CPU registers/flags, natural scheduling and device timing are excluded.'},indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'prepare_refresh_integration_cases':len(refresh_results),'negative_cases':len(negatives),'ordered_port_events':sum(row['port_events'] for row in rows)+sum(row['port_events'] for row in refresh_results),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest()}))

if __name__=='__main__': main()
