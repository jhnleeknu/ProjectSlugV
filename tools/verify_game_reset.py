"""Verify nine selected reset callees; this does not execute the whole47570 caller."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

ENTRIES=(0xb7a20,0x4d126,0x49a8e,0x4aa30,0xb4a24,0x2ef90,0x46f2e,0x4d13c,0x4ddb6)
BASE,RETURN=0x100000,0xff000


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/game_reset';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')]
    report.unlink(missing_ok=True)
    executable=root/'build/reset_game_subsystem'
    cpu=make_cpu(program)
    rows,negatives=[],[]
    def stop(cpu,address,size,user):cpu.emu_stop()
    def write(cpu,access,address,size,value,user):
        if not (BASE<=address and address+size<=BASE+65536 or
                0x1fe000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native reset write: '+hex(address))
    cpu.hook_add(UC_HOOK_CODE,stop,begin=RETURN,end=RETURN)
    cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    registers=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3)
    def compare(ram,entry,values,label):
        cpu.mem_write(BASE,bytes(ram))
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000)
        # All non-API CPU register values are independent native fixtures.
        for reg in (m.UC_M68K_REG_A0,m.UC_M68K_REG_A1,m.UC_M68K_REG_A2,
                    m.UC_M68K_REG_A3,m.UC_M68K_REG_A4,m.UC_M68K_REG_A6):cpu.reg_write(reg,0x108000)
        for reg in (m.UC_M68K_REG_D2,m.UC_M68K_REG_D4,m.UC_M68K_REG_D5,
                    m.UC_M68K_REG_D6,m.UC_M68K_REG_D7):cpu.reg_write(reg,0x13579bdf)
        cpu.reg_write(m.UC_M68K_REG_A5,0x108000)
        cpu.reg_write(m.UC_M68K_REG_A7,0x1feffc)
        for reg,value in zip(registers,values):cpu.reg_write(reg,value)
        cpu.mem_write(0x1feffc,RETURN.to_bytes(4,'big'))
        cpu.emu_start(entry,0xffffff,count=10000)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN,(hex(entry),hex(cpu.reg_read(m.UC_M68K_REG_PC)))
        expected=bytes(cpu.mem_read(BASE,65536))
        expected_regs=dict(zip(('d0','d1','d3'),(cpu.reg_read(reg)&0xffffffff for reg in registers)))
        inp.write_bytes(ram);out.unlink(missing_ok=True)
        result=subprocess.run([str(executable),hex(entry),*(str(value) for value in values),str(inp),str(out)],capture_output=True,text=True)
        parsed=json.loads(result.stdout) if not result.returncode else None
        actual=out.read_bytes() if out.exists() else None
        if result.returncode or actual!=expected or parsed!=expected_regs:
            mismatch=next((hex(BASE+i) for i,(a,b) in enumerate(zip(actual or b'',expected)) if a!=b),None)
            raise ValueError('Reset mismatch: '+repr((hex(entry),label,values,expected_regs,parsed,mismatch,result.stderr)))
        rows.append({'entry_cpu_address':entry,'profile':label,'initial_registers':dict(zip(('d0','d1','d3'),values)),
                     'result':parsed,'ram_sha256':hashlib.sha256(expected).hexdigest()})
        return actual,tuple(parsed[name] for name in ('d0','d1','d3'))
    patterns={'zero':bytes(65536),'ff':bytes([255])*65536,
              'incrementing':bytes(range(256))*256,
              'deterministic-random':hashlib.shake_256(b'game-reset-native-fixture').digest(65536)}
    triples=((0,0,0),(0xffffffff,0xffffffff,0xffffffff),
             (0x12345678,0xabcdef12,0x87654321),(0xffff0000,0x0000ffff,0x80008000))
    for entry,(name,ram),values in itertools.product(ENTRIES,patterns.items(),triples):
        compare(ram,entry,values,'isolated-'+name)
    for (name,ram),values in itertools.product(patterns.items(),triples):
        for index,entry in enumerate(ENTRIES):
            ram,values=compare(ram,entry,values,'carried-selected-callee-sequence-'+name+'-'+str(index))
    sentinel=b'previous-game-reset-output'
    def reject(ram,entry,values,label):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        result=subprocess.run([str(executable),str(entry),*(str(value) for value in values),str(inp),str(out)],capture_output=True,text=True)
        assert result.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram,(label,result.stderr)
        negatives.append({'failure':label,'input_output_preserved':True})
    for entry in (0,0x47570,0x4d17c,0xffffffff):
        reject(patterns['ff'],entry,triples[2],'unsupported-entry-'+hex(entry))
    for size in (0,65535,65537):reject(bytes(size),ENTRIES[0],triples[2],'invalid-ram-size-'+str(size))
    for index,value in itertools.product(range(3),(-1,4294967296)):
        values=list(triples[2]);values[index]=value
        reject(patterns['ff'],ENTRIES[0],values,'invalid-register-'+str(index)+'-'+str(value))
    reject(patterns['ff'],4294967296,triples[2],'overflow-entry')
    for kind in ('same','hardlink','symlink'):
        ram=patterns['ff'];inp.write_bytes(ram)
        alias=inp if kind=='same' else folder/(kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        result=subprocess.run([str(executable),hex(ENTRIES[0]),'1','2','3',str(inp),str(alias)],capture_output=True,text=True)
        assert result.returncode and inp.read_bytes()==ram
        negatives.append({'failure':'input-output-'+kind+'-alias','input_output_preserved':True})
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    report.write_text(json.dumps({'source':source,'emulator':'Unicorn '+unicorn.__version__,
        'program_code_modified':False,'entry_cpu_addresses':list(ENTRIES),'native_cpp_cases':len(rows),
        'isolated_cases':144,'carried_sequence_count':16,'carried_calls':144,
        'whole_ram_full_d0_d1_d3_equal':True,'no_native_mmio_writes':True,
        'negative_cases':len(negatives),'results':rows,'negative_results':negatives,
        'scope':'Nine original fixed-ROM reset callees and their nested calls, separately entered with A5=108000. '
                'Sixteen sequences carry actual CLI RAM/D0/D1/D3 through these nine callees in their47570 order. '
                'Other47570 calls are omitted; these sequences do not establish whole47570 behavior. '
                'Other CPU registers, CCR, stack and natural callsite preconditions are outside the C++ comparison. '
                'Invalid entry/size/register and aliases are host rejections, not native fault emulation.'},indent=2)+'\n')
    print('Game reset:',len(rows),'native/C++ cases;',len(negatives),'transactional rejections;',hashlib.sha256(report.read_bytes()).hexdigest())


if __name__=='__main__':main()
