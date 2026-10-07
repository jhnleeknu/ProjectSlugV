"""Compare unmodified1bcfe/1bd12 object reset selectors and RAM pointer writes."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import m68k_const as mc
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE,RETURN,STACK=0x100000,0xff000,0x1feffc
OBJECTS=(0xcb8,0xda8)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    executable=root/'build/reset_game_objects';folder=root/'artifacts/game_objects';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
    cpu=make_cpu(program);rows,negatives,sequences,parity=[],[],[],[]
    def write(cpu,access,address,size,value,user):
        assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def code(cpu,address,size,user):
        if address==RETURN: cpu.emu_stop()
        elif address==0x1bd8c:
            obj=cpu.reg_read(mc.UC_M68K_REG_A0)-BASE
            parity.append(dict(object_offset=obj,raw_selector=int.from_bytes(cpu.mem_read(BASE+obj+0x78,2),'big'),parity_reset_pointer=cpu.reg_read(mc.UC_M68K_REG_A4),stored_pointer=int.from_bytes(cpu.mem_read(BASE+obj+0x8c,4),'big')))
    cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_CODE,code)
    def fixture(active,selectors,pointers=(0x10d450,0x10d460)):
        ram=bytearray(hashlib.shake_256(b'game-objects-fixture:'+len(rows).to_bytes(4,'big')).digest(65536))
        for index,obj in enumerate(OBJECTS):
            struct.pack_into('>I',ram,obj,0 if active&(1<<index) else 0x270e)
            struct.pack_into('>H',ram,obj+0x78,selectors[index]);struct.pack_into('>I',ram,obj+0x8c,pointers[index])
        return ram
    def compare(ram,entry,d0,profile):
        cpu.mem_write(BASE,bytes(ram))
        d1,d3=0xabcd1234,0x9876fedc
        for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A7,STACK),(mc.UC_M68K_REG_D0,d0),(mc.UC_M68K_REG_D1,d1),(mc.UC_M68K_REG_D3,d3)):
            cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));parity.clear();cpu.emu_start(entry,RETURN,count=20000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN and cpu.reg_read(mc.UC_M68K_REG_A7)==STACK+4
        assert cpu.reg_read(mc.UC_M68K_REG_D1)==d1 and cpu.reg_read(mc.UC_M68K_REG_D3)==d3
        expected=bytes(cpu.mem_read(BASE,65536));expected_d0=cpu.reg_read(mc.UC_M68K_REG_D0)&0xffffffff
        inp.write_bytes(ram);actual=subprocess.run([str(executable),str(entry),str(d0),str(inp),str(out)],capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
        if actual_ram!=expected or parsed!={'d0':expected_d0}:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,entry,diff[:16],expected_d0,parsed)))
        rows.append(dict(profile=profile,entry=entry,incoming_d0=d0,result=parsed,original_d1_d3_preserved=[d1,d3],parity_pointer_observations=parity.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),input_sha256=hashlib.sha256(ram).hexdigest()))
        return bytearray(actual_ram),parsed['d0']
    selector_pairs=((0,0),(1,1),(2,2),(65535,65535),(0,1),(1,0),(2,65535),(65535,2))
    for entry,active,selectors,d0 in itertools.product((0x1bcfe,0x1bd12),range(4),selector_pairs,(0x12345678,0xffffabcd)):
        compare(fixture(active,selectors),entry,d0,'both-pair-activity-and-zero-nonzero-parity-selectors')
    for active,selectors in itertools.product(range(4),((2,65535),(65535,2))):
        ram=fixture(active,selectors);d0=0xabcd1234;first=len(rows)
        ram,d0=compare(ram,0x1bcfe,d0,'actual-cli-outer-reset-carry')
        ram,d0=compare(ram,0x1bd12,d0,'actual-cli-direct-reset-carry')
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_d0_carried=True))
    for pointer in (0x100000,0x108800,0x10fff4):
        compare(fixture(3,(2,65535),(pointer,pointer)),0x1bd12,0x98761234,'valid-direct-stored-pointer-boundaries')
    compare(fixture(3,(2,65535),(0xdeadbeef,0xffffffff)),0x1bcfe,0x98761234,'initializer-overwrites-unused-invalid-old-pointers')
    compare(fixture(0,(2,65535),(0xdeadbeef,0xffffffff)),0x1bd12,0x98761234,'inactive-bypasses-unused-invalid-pointers')
    sentinel=b'previous-game-object-output\0\xff'
    def reject(ram,entry='0x1bd12',d0='0x12345678',label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        actual=subprocess.run([str(executable),entry,d0,str(inp),str(out)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,original_executed=False))
    for pointer in (0,0x100001,0x10fff6,0x110000,0xffffffff): reject(fixture(3,(0,1),(0x10d450,pointer)),label='late-invalid-second-active-pointer')
    for size in (0,65535,65537): reject(bytes(size),label='invalid-ram-size')
    for entry in ('0','0x1bd2e','-1','4294967296','0x','1x',''): reject(fixture(0,(0,1)),entry=entry,label='unsupported-or-malformed-entry')
    for invalid in ('-1','4294967296','0x100000000','0x','1x',''): reject(fixture(0,(0,1)),d0=invalid,label='invalid-d0-parser')
    for alias_kind in ('same','hardlink','symlink'):
        good=fixture(0,(0,1));inp.write_bytes(good)
        alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        actual=subprocess.run([str(executable),'0x1bcfe','0',str(inp),str(alias)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good
        negatives.append(dict(failure='input-output-'+alias_kind+'-alias',output_preserved=True,original_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    observations=[value for row in rows for value in row['parity_pointer_observations']]
    assert any(value['raw_selector']==2 and value['stored_pointer']==0x10d460 and value['parity_reset_pointer']==0x10d450 for value in observations)
    assert any(value['raw_selector']==65535 and value['parity_reset_pointer']==0x10d460 for value in observations)
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_addresses=[0x1bcfe,0x1bd12],cases=len(rows),full_ram_d0_equal=True,original_only_d1_d3_preservation_observed=True,mmio_writes=0,negative_cases=len(negatives),negative_results=negatives,carry_sequences=sequences,results=rows,scope='Native paired objects100cb8/100da8 use callback270e as inactive sentinel; callback0 is active. Complete RAM and full D0 match C++ reset API. D1/D3 native preservation is observed independently because the API exposes only D0. Zero/nonzero initialization and parity byte0/word8 reset pointers are separately observed, including selector2 disagreement. CLI RAM/D0 output is carried from1bcfe to1bd12 at explicit call boundaries. Other registers/flags, object scheduler, rendering and timing are excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
