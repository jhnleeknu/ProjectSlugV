"""Native481de wrapper with actual4d81c lookup across20 immutable16-byte records."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import m68k_const as mc
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256,checked_resource

BASE,ENTRY,LOOKUP,RETURN,STACK=0x100000,0x481de,0x4d81c,0xff000,0x1feffc
REGS=(mc.UC_M68K_REG_D0,mc.UC_M68K_REG_D1,mc.UC_M68K_REG_D3)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    executable=root/'build/configure_game_record';resource=root/'extracted/runtime/game_records.ms5d'
    resource_hash=checked_resource(resource,program,0x4cf64,0x4d0a4)
    folder=root/'artifacts/game_records';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
    cpu=make_cpu(program);rows,negatives,sequences,lookups=[],[],[],[]
    def write(cpu,access,address,size,value,user):
        assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def code(cpu,address,size,user):
        if address==RETURN: cpu.emu_stop()
        elif address==LOOKUP: lookups.append(cpu.reg_read(mc.UC_M68K_REG_D1)&0xffffffff)
        elif address==0x4d824: raise ValueError('Unsupported record index reached native TRAP')
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def fixture(): return bytearray(hashlib.shake_256(b'game-records-fixture:'+len(rows).to_bytes(4,'big')).digest(65536))
    def compare(ram,registers,profile):
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A7,STACK)):
            cpu.reg_write(reg,value)
        for reg,value in zip(REGS,registers): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));lookups.clear();cpu.emu_start(ENTRY,RETURN,count=10000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN and lookups==[registers[1]]
        expected=bytes(cpu.mem_read(BASE,65536));result={key:cpu.reg_read(reg)&0xffffffff for key,reg in zip(('d0','d1','d3'),REGS)}
        assert result['d0']>>16==registers[0]>>16 and result['d1']>>16==0 and result['d3']>>16==registers[2]>>16
        inp.write_bytes(ram)
        actual=subprocess.run([str(executable)]+[str(value) for value in registers]+[str(inp),str(out),str(resource)],capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
        if actual_ram!=expected or parsed!=result:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,registers,diff[:16],result,parsed)))
        destination=0xd69c if registers[0]&1 else 0xd694
        rows.append(dict(profile=profile,incoming_registers=list(registers),result=parsed,index=registers[1]&65535,selector=registers[0]&65535,destination=BASE+destination,destination_bytes=expected[destination:destination+8].hex(),native_lookup_entered=True,ram_sha256=hashlib.sha256(expected).hexdigest(),input_sha256=hashlib.sha256(ram).hexdigest()))
        return bytearray(actual_ram),tuple(parsed[key] for key in ('d0','d1','d3'))
    for index,selector,high in itertools.product(range(20),(0,1,2,65535),(0,0xabcd)):
        compare(fixture(),(high<<16|selector,0xbeef0000|index,0x9876fedc),'all20-records-selector-parity-register-highwords')
    for high in (0,0xffff):
        ram=fixture();registers=(high<<16,0xbeef0000,high<<16|0xabcd);first=len(rows)
        for index,selector in ((0,0),(19,1),(7,2),(13,65535)):
            # Host issues the next index and destination selector; all other bits/RAM are actual outputs.
            registers=((registers[0]&0xffff0000)|selector,(registers[1]&0xffff0000)|index,registers[2])
            ram,registers=compare(ram,registers,'cli-output-carry-with-explicit-next-index-and-selector')
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_d0_high_d1_high_full_d3_carried=True,next_index_and_selector_host_supplied=True))
    sentinel=b'previous-game-record-output\0\xff'
    def reject(ram,registers=(0,0,0),selected=resource,label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        actual=subprocess.run([str(executable)]+[str(value) for value in registers]+[str(inp),str(out),str(selected)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,original_executed=False))
    for index in (20,21,255,0x8000,65535): reject(fixture(),(0,0xabcd0000|index,0x9876fedc),label='unsupported-index-before-original-trap')
    for size in (0,65535,65537): reject(bytes(size),label='invalid-ram-size')
    for index,invalid in itertools.product(range(3),('-1','4294967296','0x100000000','0x','1x','')):
        registers=[0,0,0];registers[index]=invalid;reject(fixture(),registers,label='invalid-register-parser')
    malformed=folder/'bad.ms5d';malformed.write_bytes(b'bad');reject(fixture(),selected=malformed,label='invalid-resource')
    payload=program[0x4cf64:0x4d0a4]
    for address,size in ((0x4cf65,320),(0x4cf64,319)):
        data=payload[:size];malformed.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,address,address,len(data),zlib.crc32(data)&0xffffffff,0)+data)
        reject(fixture(),selected=malformed,label='wrong-exact-window-metadata')
    for alias_kind in ('same','hardlink','symlink'):
        good=fixture();inp.write_bytes(good)
        alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        actual=subprocess.run([str(executable),'0','0','0',str(inp),str(alias),str(resource)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good
        negatives.append(dict(failure='input-output-'+alias_kind+'-alias',output_preserved=True,original_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert {row['index'] for row in rows}==set(range(20))
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_address=ENTRY,lookup_cpu_address=LOOKUP,resource_cpu_address=0x4cf64,resource_rom_offset=0x4cf64,resource_sha256=resource_hash,cases=len(rows),full_ram_d0_d1_d3_equal=True,mmio_writes=0,negative_cases=len(negatives),negative_results=negatives,carry_sequences=sequences,results=rows,scope='Native481de wrapper calls actual4d81c lookup against20 original16-byte records. Full RAM/D0/D1/D3 and both fixed destinations are compared; D1 highword MULU clearing and D0/D3 highword preservation are observed. No direct4d81c standalone API is claimed. Short CLI carry sequences explicitly supply each next selector/index while preserving actual output RAM and remaining register bits. Unsupported indices are CLI-only negatives; original TRAP is not executed. Other registers/CCR, suffix integration and timing are excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
