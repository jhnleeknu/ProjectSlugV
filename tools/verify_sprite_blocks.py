"""Ground all four rectangular transform branches and slot directions."""
import argparse
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
from verify_sprite_flips import model

ENTRIES = {(False,False):(0xce82,0xd250,0xd620,0xd9f2),
           (True,False):(0x117b2,0x11b7e,0x11f4c,0x1231c),
           (False,True):(0xf246,0xf636,0xfa28,0xfe26),
           (True,True):(0x13b66,0x13f52,0x14340,0x1473a)}


def resolve_blocks(program, identifier):
    bank = ((identifier & 7)+2)*0x100000
    group, item = (identifier>>3)&255, (identifier>>11)&4095
    def pointer(at):
        address = int.from_bytes(program[at:at+4], 'big')
        if not 0x200000 <= address < 0x2fe000:
            raise ValueError('Pointer outside bank ROM')
        return bank+address-0x200000
    table = pointer(bank+4+group*4)
    offset = pointer(table+item*4)
    header = int.from_bytes(program[offset:offset+2], 'big')
    if not 1 <= header>>8 <= 255:
        raise ValueError('Unsupported block header')
    cursor, blocks = offset+2, []
    for index in range(header>>8):
        width, height = program[cursor+4:cursor+6]
        if not width or not 1 <= height <= 32:
            raise ValueError('Unsupported block dimensions')
        end = cursor+6+width*height*4
        if end > bank+0xfe000:
            raise ValueError('Block crosses bank ROM')
        blocks.append(b'\x01\x00'+program[cursor:end])
        cursor = end
    return bank, offset, program[offset:cursor], blocks


def model_blocks(blocks, u, v, style, first, limit, cached, reverse, refresh):
    writes = bytearray()
    for block in blocks:
        result = model(block,u,v,style,first,limit,cached,reverse,refresh)
        first = int.from_bytes(result[:4],'big')
        writes.extend(result[4:])
    return struct.pack('>I',first)+writes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpp',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory = root/'artifacts/sprite_blocks'
    directory.mkdir(parents=True,exist_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000,0x200000)
    events = []
    def hook(cpu,access,address,size,value,user):
        if 0x3c0000<=address<0x3c0010:
            if address!=0x3c0000 or size!=4:
                raise ValueError('Unexpected video access')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE,hook)
    results = []
    for identifier in (0x2382a,0x2402a,0x2482a,0x122,0x29802,0x70002):
        bank,offset,data,blocks = resolve_blocks(program,identifier)
        path=directory/('%06x.raw.bin'%identifier)
        path.write_bytes(data)
        cpu.mem_write(0x200000,program[bank:bank+0x100000])
        for (reverse,refresh),entries in ENTRIES.items():
            for flip,entry in enumerate(entries):
                for u in (0,160,0xffff):
                    for v in ((0,384,65535) if refresh else (0,)):
                        for capacity in (0,1,380):
                            for cached in ((0,190,380) if refresh else (0,)):
                                first,limit = (capacity,0) if reverse else (0,capacity)
                                style=0x1500|flip
                                cpu.mem_write(0x100000,bytes(65536))
                                cpu.mem_write(0x107f40,struct.pack('>III',(u<<6)&65535,style,((v<<23)&0xffffffff)|identifier))
                                if reverse:
                                    controls=(limit,380,cached if refresh else limit,first)
                                else:
                                    controls=(0,limit,first,cached if refresh else limit)
                                cpu.mem_write(0x105000,struct.pack('>4H',*controls))
                                for reg,value in ((UC_M68K_REG_A2,0x107f40),(UC_M68K_REG_A4,0x105000),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A6,0x3c0000),(UC_M68K_REG_D1,style)):
                                    cpu.reg_write(reg,value)
                                events.clear();call(cpu,entry)
                                next_slot=int.from_bytes(cpu.mem_read(0x105006 if reverse else 0x105004,2),'big')
                                actual=struct.pack('>I',next_slot)+b''.join(struct.pack('>I',w) for w in events)
                                expected=model_blocks(blocks,u,v,style,first,limit,cached,reverse,refresh)
                                if actual!=expected:
                                    raise ValueError('Flip model mismatch '+repr((identifier,entry,u,v,first,limit,cached)))
                                if args.cpp:
                                    out=directory/'cpp.bin'
                                    subprocess.run([str(root/'build/emit_composition_blocks'),str(path),str(out),str(u),str(v),str(style),str(first),str(limit),str(cached),'reverse' if reverse else 'forward','refresh' if refresh else 'normal'],check=True)
                                    if out.read_bytes()!=actual:
                                        raise ValueError('C++ flip mismatch')
                                results.append({'id':identifier,'entry':entry,'flip':flip,'reverse':reverse,'refresh':refresh,'u':u,'v':v,'first':first,'limit':limit,'cached':cached,'writes':len(events),'sha256':hashlib.sha256(actual).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({'source_program_sha256':source['sha256'],'cases':len(results),'cpp_verified':args.cpp,'all_ordered_writes_equal':True,'scope':'Six real counted-rectangle resources including nonzero low header bytes, transforms, allocation directions and prepare/refresh. No pixel or caller reachability claim.','results':results},indent=2)+'\n')
    print('All multi-block writes match:',len(results),'cases')


if __name__=='__main__':
    main()
