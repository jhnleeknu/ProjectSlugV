"""Compare reconstructed object memory reset with original 68000 execution."""
import hashlib
import json
from pathlib import Path
import subprocess

import unicorn
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_M68K_REG_A0,
    UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program


def make_cpu(program):
    cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    # Unicorn defaults to another M68K family model; that fails on ADDA.W.
    cpu.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    cpu.mem_map(0, 0x200000)
    cpu.mem_write(0, program[:0x100000])
    cpu.reg_write(UC_M68K_REG_SR, 0x2000)
    return cpu


def run_original(cpu, payload):
    base = 0x100820
    cpu.mem_write(base-16, bytes([0x5a])*16 + payload + bytes([0xa5])*16)
    cpu.reg_write(UC_M68K_REG_A0, base)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A7, 0x10effc)
    cpu.mem_write(0x10effc, (0xff000).to_bytes(4, 'big'))
    cpu.emu_start(0x271c, 0xff000, count=1000)
    if cpu.reg_read(UC_M68K_REG_PC) != 0xff000 or cpu.reg_read(UC_M68K_REG_A0) != base:
        raise ValueError('Original reset failed to return with preserved A0')
    if bytes(cpu.mem_read(base-16,16)) != bytes([0x5a])*16 or bytes(cpu.mem_read(base+0xc4,16)) != bytes([0xa5])*16:
        raise ValueError('Original routine changed boundary guards')
    return bytes(cpu.mem_read(base, 0xc4))


def main():
    root = Path(__file__).resolve().parents[1]
    program, manifest = load_verified_program(root)
    if manifest['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    directory = root/'artifacts/object_reset'
    directory.mkdir(parents=True,exist_ok=True)
    cases = [bytes([value])*0xc4 for value in (0,0xff,0xa5,0x5a)]
    cases.append(bytes(range(0xc4)))
    for index in range(256):
        cases.append(hashlib.shake_256(b'ms5-object-reset-v1'+index.to_bytes(4,'big')).digest(0xc4))
    fixture = b''.join(cases)
    input_path = directory/'input.bin'
    output_path = directory/'cpp.bin'
    input_path.write_bytes(fixture)
    subprocess.run([str(root/'build/reset_object'),str(input_path),str(output_path)],check=True)
    actual = output_path.read_bytes()
    cpu = make_cpu(program)
    expected = b''.join(run_original(cpu, data) for data in cases)
    (directory/'m68k.bin').write_bytes(expected)
    if actual != expected:
        raise ValueError('Object reset C++ memory effect differs from original 68000')
    report = {'source_program_sha256':manifest['sha256'], 'entry_cpu_address':0x271c,
              'emulator':'Unicorn '+unicorn.__version__, 'cpu_model':'M68000',
              'cases':len(cases),'bytes_per_case':0xc4,'all_bytes_equal':True,
              'output_sha256':hashlib.sha256(actual).hexdigest(),
              'scope':'Object memory effect including untouched fields and original boundary guards; not CPU flags/register equivalence or full Neo Geo boot.'}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
