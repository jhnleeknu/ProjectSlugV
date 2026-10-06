"""Compare normal rectangular sprite emission with the original consumer."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A2, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_D1, UC_M68K_REG_D6, UC_M68K_REG_A3
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def resolve(program, identifier):
    bank = ((identifier&7)+2)*0x100000
    group, item = (identifier>>3)&255,(identifier>>11)&4095
    at = bank+4+group*4
    table = int.from_bytes(program[at:at+4],'big')
    if not 0x200000 <= table < 0x2fe000:
        raise ValueError('Unexpected table address')
    at = bank+table-0x200000+item*4
    address = int.from_bytes(program[at:at+4],'big')
    offset = bank+address-0x200000
    if not 0x200000 <= address < 0x2fe000 or not 0 <= offset < len(program)-8:
        raise ValueError('Unexpected composition address')
    header, dx, dy, descriptor = struct.unpack('>4H',program[offset:offset+8])
    width,height = descriptor>>8,descriptor&255
    if header != 0x100 or not 1<=height<=32 or not width:
        raise ValueError('Outside confirmed rectangular subset')
    data = program[offset:offset+8+width*height*4]
    if len(data) != 8+width*height*4:
        raise ValueError('Truncated composition')
    return bank,offset,data


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    directory = root/'artifacts/sprite_composition'
    directory.mkdir(parents=True,exist_ok=True)
    rows = []
    cpu = make_cpu(program)
    cpu.mem_map(0x200000,0x200000)
    events = []
    def on_write(cpu,access,address,size,value,user):
        if 0x3c0000<=address<0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video access')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE,on_write)
    for identifier in (0x2152,0x2952):
        bank,offset,data = resolve(program,identifier)
        path = directory/('%06x.raw.bin'%identifier)
        path.write_bytes(data)
        cpu.mem_write(0x200000,program[bank:bank+0x100000])
        for u in (0xff60,0,160,319,640):
            for style in (0x1500,0xff07):
                for first,limit in ((0,0),(0,1),(0,380),(379,380)):
                    cpu.mem_write(0x100000,bytes(65536))
                    cpu.mem_write(0x107f40,struct.pack('>III',(u<<6)&0xffff,style,0xc0000000|identifier))
                    cpu.mem_write(0x105004,struct.pack('>HH',first,limit))
                    for reg,value in ((UC_M68K_REG_A2,0x107f40),(UC_M68K_REG_A4,0x105000),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A6,0x3c0000),(UC_M68K_REG_D1,style)):
                        cpu.reg_write(reg,value)
                    events.clear()
                    call(cpu,0xce82)
                    next_slot = int.from_bytes(cpu.mem_read(0x105004,2),'big')
                    expected = struct.pack('>I',next_slot)+b''.join(struct.pack('>I',value) for value in events)
                    out = directory/'cpp.bin'
                    subprocess.run([str(root/'build/emit_composition'),str(path),str(out),str(u),str(style),str(first),str(limit)],check=True)
                    if out.read_bytes() != expected:
                        raise ValueError('Sprite emission mismatch ID%x U%x style%x first%d limit%d'%(identifier,u,style,first,limit))
                    rows.append({'id':identifier,'rom_offset':offset,'u':u,'style':style,'first_slot':first,'limit':limit,'next_slot':next_slot,'writes':len(events),'original_d6':cpu.reg_read(UC_M68K_REG_D6),'original_a3':cpu.reg_read(UC_M68K_REG_A3),'sha256':hashlib.sha256(expected).hexdigest()})
    report = {'source_program_sha256':source['sha256'],'entry':0xce82,'cases':len(rows),'all_ordered_writes_equal':True,
              'scope':'One-block normal rectangular consumer only. Raw style bits tested at this entry do not establish flip dispatch correctness. No Y control, sprite rasterizer or full-frame claim.',
              'results':rows}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('All ordered sprite writes match:',len(rows),'cases')


if __name__ == '__main__':
    main()
