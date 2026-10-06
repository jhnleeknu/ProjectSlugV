"""Record grounded palette addresses and test the original lookup-copy helper."""
import hashlib
import json
from pathlib import Path
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    palette_base = int.from_bytes(program[0x200004:0x200008], 'big')
    lookup_base = int.from_bytes(program[0x200008:0x20000c], 'big')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x100000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    results = []
    # These IDs are probes only: no claim of actual in-game selection or table length.
    for palette_id in range(16):
        address = palette_base + palette_id * 32
        raw = program[address:address + 32]
        expected = bytearray([0xa5] * 32)
        lookups = []
        for index in range(1, 16):
            word = int.from_bytes(raw[index * 2:index * 2 + 2], 'big')
            displacement = (word * 2) & 0xffff
            if displacement & 0x8000:
                displacement -= 0x10000
            lookup_address = lookup_base + displacement
            expected[index * 2:index * 2 + 2] = program[lookup_address:lookup_address + 2]
            lookups.append(lookup_address)
        cpu.mem_write(0x105da0, bytes([0x3c]) * 2 + bytes([0xa5]) * 32 + bytes([0x5a]) * 2)
        cpu.reg_write(UC_M68K_REG_A0, address)
        cpu.reg_write(UC_M68K_REG_A3, lookup_base)
        cpu.reg_write(UC_M68K_REG_A4, 0x105da2)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        cpu.emu_start(0x4718, 0xff000, count=128)
        actual = bytes(cpu.mem_read(0x105da2, 32))
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000 or actual != expected or cpu.reg_read(UC_M68K_REG_A4) != 0x105da2:
            raise ValueError('Original lookup helper mismatch')
        if bytes(cpu.mem_read(0x105da0, 2)) != bytes([0x3c])*2 or bytes(cpu.mem_read(0x105dc2, 2)) != bytes([0x5a])*2:
            raise ValueError('Lookup helper boundary mismatch')
        results.append({'probe_id': palette_id, 'rom_offset': address, 'source_words_be_hex': raw.hex(),
                        'lookup_rom_offsets': lookups, 'output_be_hex': actual.hex()})
    directory = root/'artifacts/palette_flow'
    directory.mkdir(parents=True, exist_ok=True)
    report = {'source_program_sha256': source['sha256'], 'bank_base': 0x200000,
              'palette_table_pointer': palette_base, 'lookup_table_pointer': lookup_base,
              'helper_entry': 0x4718, 'probe_results': results, 'all_bytes_equal': True,
              'scope': '16 probe IDs; table bounds, in-game use, color conversion and other helper branches unresolved.'}
    (directory/'analysis.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Palette base=0x%x lookup base=0x%x; %d original helper probes matched' % (palette_base, lookup_base, len(results)))


if __name__ == '__main__':
    main()
