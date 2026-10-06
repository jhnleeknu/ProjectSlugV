"""Check opaque low header byte against every rectangular consumer branch."""
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A2, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_D1
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_sprite_flips import ENTRIES
from verify_sprite_blocks import resolve_blocks, model_blocks


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000,0x200000)
    events = []
    def hook(cpu,access,address,size,value,user):
        if 0x3c0000 <= address < 0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video write')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE,hook)
    cases = 0
    for identifier in (0x2152,0x2402a):
        bank,offset,data,blocks = resolve_blocks(program,identifier)
        cpu.mem_write(0x200000,program[bank:bank+0x100000])
        for (reverse,refresh),entries in ENTRIES.items():
            for flip,entry in enumerate(entries):
                first,limit,cached = (380,0,380) if reverse else (0,380,0)
                expected = model_blocks(blocks,160,384,0x1500|flip,first,limit,cached,reverse,refresh)
                for low_byte in range(256):
                    # Controlled RAM/ROM fixture: only low header byte is replaced.
                    cpu.mem_write(0x200000+offset-bank+1,bytes([low_byte]))
                    cpu.mem_write(0x100000,bytes(65536))
                    cpu.mem_write(0x107f40,struct.pack('>III',160<<6,0x1500|flip,(384<<23)|identifier))
                    controls = (0,380,cached,first) if reverse else (0,380,first,cached)
                    if not refresh:
                        controls = (0,380,0,380) if reverse else (0,380,0,380)
                    cpu.mem_write(0x105000,struct.pack('>4H',*controls))
                    for reg,value in ((UC_M68K_REG_A2,0x107f40),(UC_M68K_REG_A4,0x105000),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A6,0x3c0000),(UC_M68K_REG_D1,0x1500|flip)):
                        cpu.reg_write(reg,value)
                    events.clear();call(cpu,entry)
                    next_slot=int.from_bytes(cpu.mem_read(0x105006 if reverse else 0x105004,2),'big')
                    actual=struct.pack('>I',next_slot)+b''.join(struct.pack('>I',w) for w in events)
                    if actual != expected:
                        raise ValueError('Opaque byte changed emission '+repr((identifier,entry,low_byte)))
                    cases += 1
    destination=root/'artifacts/sprite_header'
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'cases':cases,
        'all_outputs_equal':True,'scope':'Synthetic low-byte sweep on one single and one three-block payload. Does not establish meaning to other consumers.'},indent=2)+'\n')
    print('Opaque low header byte leaves emission unchanged:',cases,'cases')


if __name__ == '__main__':
    main()
