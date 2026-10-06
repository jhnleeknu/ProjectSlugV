"""Compare normal rectangular refresh, including Y and cached-slot reuse."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A2, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_D1
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_sprite_composition import resolve


def main():
    root = Path(__file__).resolve().parents[1]
    program,source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported revision')
    directory = root/'artifacts/sprite_refresh'
    directory.mkdir(parents=True,exist_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000,0x200000)
    events = []
    def on_write(cpu,access,address,size,value,user):
        if 0x3c0000<=address<0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video access')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE,on_write)
    results = []
    for identifier in (0x2152,0x2952):
        bank,offset,data = resolve(program,identifier)
        path = directory/('%06x.raw.bin'%identifier)
        path.write_bytes(data)
        cpu.mem_write(0x200000,program[bank:bank+0x100000])
        for u in (0,160,319):
            for v in (0,384,511,65535):
                for cached in (0,10,380):
                    for first,limit in ((0,380),(379,380),(0,0)):
                        style = 0x1500
                        cpu.mem_write(0x100000,bytes(65536))
                        packed = ((((v<<7)&0xffff)<<16)|identifier)
                        cpu.mem_write(0x107f40,struct.pack('>III',(u<<6)&0xffff,style,packed))
                        cpu.mem_write(0x105002,struct.pack('>HHH',limit,first,cached))
                        for register,value in ((UC_M68K_REG_A2,0x107f40),(UC_M68K_REG_A4,0x105000),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A6,0x3c0000),(UC_M68K_REG_D1,style)):
                            cpu.reg_write(register,value)
                        events.clear()
                        call(cpu,0xf246)
                        next_slot = int.from_bytes(cpu.mem_read(0x105004,2),'big')
                        expected = struct.pack('>I',next_slot)+b''.join(struct.pack('>I',x) for x in events)
                        output = directory/'cpp.bin'
                        subprocess.run([str(root/'build/emit_composition_refresh'),str(path),str(output),str(u),str(v),str(style),str(first),str(limit),str(cached)],check=True)
                        if output.read_bytes() != expected:
                            raise ValueError('Refresh mismatch %x U%d V%d first%d limit%d cached%d'%(identifier,u,v,first,limit,cached))
                        results.append({'id':identifier,'u':u,'v':v,'first':first,'limit':limit,'cached_end':cached,
                                        'next_slot':next_slot,'writes':len(events),'sha256':hashlib.sha256(expected).hexdigest()})
    report = {'source_program_sha256':source['sha256'],'entry':0xf246,'cases':len(results),
              'all_ordered_writes_equal':True,'scope':'Single-block normal refresh and slot reuse; no full double-buffer scheduling, flipped paths, or pixel rasterization claim.',
              'results':results}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('All sprite refresh writes match:',len(results),'cases')


if __name__ == '__main__':
    main()
