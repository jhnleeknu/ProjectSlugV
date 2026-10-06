"""Differential-check fixed-width coordinate update/advance against original 68000."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def put32(ram, offset, value):
    ram[offset:offset+4] = (value & 0xffffffff).to_bytes(4,'big')


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    coordinate = 0x10084e  # original object0x100820 +0x2e
    offset = coordinate-0x100000
    cases = []
    for parent in (0,0x10102e,coordinate):
        for current in (0,1,2,255):
            for stamp in (0,current,(current+1)&255):
                for carry in range(4):
                    for advance in (0,1):
                        ram = bytearray(hashlib.shake_256(struct.pack('>6I',parent,current,stamp,carry,advance,len(cases))).digest(65536))
                        # Boundary words combine signed-looking values with low-word carries.
                        x = 0xffff0000 | (0xffff if carry&1 else 0)
                        y = 0x7fff0000 | (0xffff if carry&2 else 0)
                        put32(ram,offset,x)
                        put32(ram,offset+4,y)
                        put32(ram,offset+8,0x00010001)
                        put32(ram,offset+12,0xffff0001)
                        put32(ram,offset+16,parent)
                        if parent:
                            p = parent-0x100000
                            put32(ram,p+0x14,0x00010001)
                            put32(ram,p+0x18,0x80000001)
                            ram[p+0x25] = 0xa0
                        ram[offset+0x24] = stamp
                        ram[0xd494] = current
                        cases.append((coordinate,advance,bytes(ram)))
    directory = root/'artifacts/position_state'
    directory.mkdir(parents=True,exist_ok=True)
    input_path, output_path = directory/'input.bin',directory/'cpp.bin'
    input_path.write_bytes(b''.join(struct.pack('>II',address,advance)+ram for address,advance,ram in cases))
    subprocess.run([str(root/'build/update_position'),str(input_path),str(output_path)],check=True)
    cpu = make_cpu(program)
    expected = bytearray()
    for address,advance,ram in cases:
        cpu.mem_write(0x100000,ram)
        cpu.reg_write(UC_M68K_REG_A0,address)
        call(cpu,0x43ea8 if advance else 0x43e38)
        expected.extend(struct.pack('>II',address,advance))
        expected.extend(cpu.mem_read(0x100000,65536))
    actual = output_path.read_bytes()
    (directory/'m68k.bin').write_bytes(expected)
    if actual != expected:
        if len(actual) != len(expected):
            raise ValueError('C++ output length mismatch')
        where = next(i for i in range(len(actual)) if actual[i] != expected[i])
        raise ValueError('Coordinate mismatch case %d record byte 0x%x' % (where//65544,where%65544))
    report = {'source_program_sha256':source['sha256'],'entries':[0x43e38,0x43ea8],
              'cases':len(cases),'ram_bytes_per_case':65536,'all_bytes_equal':True,
              'output_sha256':hashlib.sha256(actual).hexdigest(),
              'coverage':['null/other/self parent','low-word carry combinations','32-bit wrap','stamp zero/same/changed','current stamp 0/1/2/255','advance off/on'],
              'scope':'Persistent RAM only, valid RAM-resident structures; no CPU register/flag or real frame cadence equivalence.'}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
