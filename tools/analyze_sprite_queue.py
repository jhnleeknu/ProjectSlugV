"""Probe the original render-queue producer; retain uncertain field semantics."""
import hashlib
import json
from pathlib import Path
import struct
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D5, UC_M68K_REG_D7
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    cpu = make_cpu(program)
    rows = []
    for upper in (0xfe9f,0xfea0,0xffff,0,0x29f,0x2a0):
        for lower in (0x3f,0x40,0x2bf,0x2c0):
            for deferred in (False,True):
                cpu.mem_write(0x100000,bytes(65536))
                cpu.reg_write(UC_M68K_REG_A5,0x108000)
                call(cpu,0xccd6)
                initial = bytes(cpu.mem_read(0x100000,65536))
                d0 = (upper<<16)|lower
                d1 = 0xabcdff87 | (0x40 if deferred else 0)
                d5,d7 = 0x12345678,0x000155aa
                for register,value in ((UC_M68K_REG_D0,d0),(UC_M68K_REG_D1,d1),(UC_M68K_REG_D5,d5),(UC_M68K_REG_D7,d7)):
                    cpu.reg_write(register,value)
                call(cpu,0xcd58)
                actual = bytes(cpu.mem_read(0x100000,65536))
                accepted = ((lower-0x40)&0xffff)<0x280 and ((upper+0x160)&0xffff)<0x400
                expected = bytearray(initial)
                record = b''
                if accepted:
                    expected[0x8d3a:0x8d3c] = b'\x00\x02'
                    if deferred:
                        expected[0x914e:0x9150] = b'\x00\x02'
                        expected[0x8f4e:0x8f50] = b'\x00\x0c'
                    else:
                        expected[0x8b34:0x8b36] = b'\x00\x0c'
                        expected[0x8d38:0x8d3a] = b'\x00\x02'
                    record = struct.pack('>III',((d5&0xffff)<<16)|((upper<<6)&0xffff),
                                         d1&0xffffff07,((((d7>>16)|((lower<<7)&0xffff))&0xffff)<<16)|(d7&0xffff))
                    expected[0x7f40:0x7f4c] = record
                if actual != expected:
                    at = next(i for i in range(65536) if actual[i] != expected[i])
                    raise ValueError('Original producer effect mismatch at CPU0x%x'%(0x100000+at))
                rows.append({'d0_upper':upper,'d0_lower':lower,'deferred':deferred,
                             'accepted':accepted,'record_be_hex':record.hex(),
                             'ram_sha256':hashlib.sha256(actual).hexdigest()})
    directory = root/'artifacts/sprite_queue'
    directory.mkdir(parents=True,exist_ok=True)
    references = []
    for identifier in (0x2152,0x2952):
        bank = ((identifier&7)+2)*0x100000
        group, item = (identifier>>3)&255,(identifier>>11)&4095
        table_pointer_offset = bank+4+group*4
        table_cpu = int.from_bytes(program[table_pointer_offset:table_pointer_offset+4],'big')
        if not 0x200000 <= table_cpu < 0x2fe000:
            raise ValueError('Unexpected group table address')
        item_pointer_offset = bank+table_cpu-0x200000+item*4
        frame_cpu = int.from_bytes(program[item_pointer_offset:item_pointer_offset+4],'big')
        if not 0x200000 <= frame_cpu < 0x2fe000:
            raise ValueError('Unexpected composition address')
        frame_offset = bank+frame_cpu-0x200000
        references.append({'packed_id':identifier,'bank_base':bank,'group':group,'item':item,
                           'group_pointer_rom_offset':table_pointer_offset,'group_table_cpu':table_cpu,
                           'item_pointer_rom_offset':item_pointer_offset,'composition_cpu':frame_cpu,
                           'composition_rom_offset':frame_offset,'first32_bytes_hex':program[frame_offset:frame_offset+32].hex()})
    report = {'source_program_sha256':source['sha256'],'initializer':0xccd6,'producer':0xcd58,
              'cases':len(rows),'ram_bytes_checked_per_case':65536,'all_expected_effects_match':True,
              'scope':'Original execution and instruction-derived memory effects, one record into empty queue. Not C++ reconstruction, full queue concurrency, sprite consumer or frame rendering.',
              'results':rows,'consumer_references':references}
    (directory/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Matched full RAM effects for',len(rows),'original queue probes; accepted',sum(r['accepted'] for r in rows))


if __name__ == '__main__':
    main()
