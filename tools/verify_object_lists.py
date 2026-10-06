"""Differential-check C++ object list bootstrap against original CPU routine."""
import hashlib
import json
from pathlib import Path
import subprocess
import unicorn
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    cases=[bytes([v])*0x10000 for v in (0,0xff,0xa5,0x5a)]
    cases.append(bytes(range(256))*256)
    for i in range(16):
        cases.append(hashlib.shake_256(b'ms5-object-list-v1'+bytes([i])).digest(0x10000))
    directory=root/'artifacts/object_lists'
    directory.mkdir(parents=True,exist_ok=True)
    input_path=directory/'input.bin'
    output_path=directory/'cpp.bin'
    input_path.write_bytes(b''.join(cases))
    subprocess.run([str(root/'build/init_objects'),str(root/'extracted/runtime/object_boot.ms5i'),
                    str(input_path),str(output_path)],check=True)
    cpu=make_cpu(program)
    expected=[]
    for data in cases:
        cpu.mem_write(0x100000,data)
        # Scratch stack outside the compared RAM; isolates the routine's
        # persistent RAM writes from temporary JSR/RTS stack words.
        cpu.reg_write(UC_M68K_REG_A7,0x1feffc)
        cpu.mem_write(0x1feffc,(0xff000).to_bytes(4,'big'))
        cpu.emu_start(0x2790,0xff000,count=50000)
        if cpu.reg_read(UC_M68K_REG_PC)!=0xff000:
            raise ValueError('Original initialization did not return within limit')
        expected.append(bytes(cpu.mem_read(0x100000,0x10000)))
    expected=b''.join(expected)
    actual=output_path.read_bytes()
    (directory/'m68k.bin').write_bytes(expected)
    if len(actual) != len(expected):
        raise ValueError('C++ RAM output size mismatch')
    if actual!=expected:
        offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
        raise ValueError('RAM mismatch case %d CPU address %06x'%(offset//0x10000,0x100000+offset%0x10000))
    report={'source_program_sha256':source['sha256'],'entry_cpu_address':0x2790,
            'emulator':'Unicorn '+unicorn.__version__,'cpu_model':'M68000',
            'cases':len(cases),'bytes_compared_per_case':0x10000,'all_bytes_equal':True,
            'output_sha256':hashlib.sha256(actual).hexdigest(),
            'scope':'Persistent 64 KiB game RAM only; harness stack outside compared RAM. Not game boot or register/flag equivalence.'}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
