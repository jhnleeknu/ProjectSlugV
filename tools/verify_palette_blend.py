"""Compare C++ MS5P blend preparation with original full preparation."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f': raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000,0x200000)
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    cpu.reg_write(UC_M68K_REG_A5,0x108000)
    folder = root/'artifacts/palette_blend_cpp'
    folder.mkdir(parents=True,exist_ok=True)
    inp,out=folder/'input.bin',folder/'output.bin'
    ids=(0x3d3,0x39d,0x203,0x87d,0x87a)
    rows=[]
    for first in ids:
        for second in ids:
            if first==second: continue
            for weight in list(range(32))+[255]:
                state=bytearray(65536)
                slot=(first+second+weight)&255
                node=0x4d92+slot*16
                struct.pack_into('>HH',state,node+10,first,second)
                state[node+14]=weight
                state[node+15]=0x82 if weight&1 else 0x80
                state[0x7dc2]=weight&1
                state[0x5da2:0x7da2]=bytes([0x5a])*8192
                cpu.mem_write(0x100000,bytes(state))
                call(cpu,0x7196)
                expected=bytes(cpu.mem_read(0x100000,65536))
                inp.write_bytes(state)
                subprocess.run([str(root/'build/prepare_palette'),str(inp),str(root/'extracted/runtime/palettes.ms5p'),str(out)],check=True)
                if out.read_bytes()!=expected:raise ValueError('Blend preparation mismatch '+repr((first,second,weight)))
                rows.append({'first':first,'second':second,'weight':weight,'slot':slot,'ram_sha256':hashlib.sha256(expected).hexdigest()})
    (folder/'verification.json').write_text(json.dumps({'source':source,'cases':len(rows),'all_ram_equal':True,
        'scope':'All ordered unequal pairs of five actual initializer palette IDs, weights0..31 and255, normal/effect-bypass branches. No active effects or natural gameplay claim.', 'results':rows},indent=2)+'\n')
    print('C++ palette blend matches original RAM:',len(rows),'cases')


if __name__=='__main__':main()
