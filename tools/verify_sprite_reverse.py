"""Compare reverse-slot normal/refresh emission to original 68000 routines."""
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
from verify_sprite_composition import resolve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-resources", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    directory = root/('artifacts/sprite_reverse_resource' if args.runtime_resources else 'artifacts/sprite_reverse')
    directory.mkdir(parents=True, exist_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    events = []
    def on_write(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video access')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    results = []
    for identifier in (0x2152, 0x2952):
        bank, offset, data = resolve(program, identifier)
        path = directory/('%06x.raw.bin' % identifier)
        path.write_bytes(data)
        cpu.mem_write(0x200000, program[bank:bank+0x100000])
        for mode, entry in (('normal', 0x117b2), ('refresh', 0x13b66)):
            for u in (0xff60, 0, 160, 319, 640):
                for v in ((0, 384, 511) if mode == 'refresh' else (384,)):
                    for first, lower in ((380, 0), (1, 0), (10, 10), (20, 10)):
                        for cached in ((0, 10, 380) if mode == 'refresh' else (0,)):
                            style = 0x1500 if identifier == 0x2152 else 0x1600
                            cpu.mem_write(0x100000, bytes(65536))
                            packed = ((((v<<7)&65535)<<16)|identifier)
                            cpu.mem_write(0x107f40, struct.pack('>III', (u<<6)&65535, style, packed))
                            cpu.mem_write(0x105000, struct.pack('>4H', lower, 380, cached if mode == 'refresh' else lower, first))
                            for reg, value in ((UC_M68K_REG_A2, 0x107f40), (UC_M68K_REG_A4, 0x105000),
                                               (UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_A6, 0x3c0000), (UC_M68K_REG_D1, style)):
                                cpu.reg_write(reg, value)
                            events.clear()
                            call(cpu, entry)
                            next_slot = int.from_bytes(cpu.mem_read(0x105006, 2), 'big')
                            expected = struct.pack('>I', next_slot)+b''.join(struct.pack('>I', x) for x in events)
                            output = directory/'cpp.bin'
                            subprocess.run([str(root/'build/emit_composition_reverse'), str(path), str(output),
                                            str(u), str(v), str(style), str(first), str(lower), str(cached), mode], check=True)
                            if output.read_bytes() != expected:
                                raise ValueError('Raw reverse CLI differs from original')
                            if args.runtime_resources and mode == 'refresh':
                                resource = root/'extracted/runtime'/('composition_%06x.ms5c' % identifier)
                                subprocess.run([str(root/'build/emit_sprite_resource'), str(resource), str(output),
                                                str(u), str(v), str(style), str(first), str(lower), str(cached), 'reverse'], check=True)
                            if output.read_bytes() != expected:
                                raise ValueError('Reverse mismatch %x %s u%d v%d first%d lower%d cache%d' % (identifier, mode, u, v, first, lower, cached))
                            results.append({'id': identifier, 'mode': mode, 'entry': entry, 'u': u, 'v': v,
                                            'first': first, 'lower': lower, 'cached_begin': cached, 'next_slot': next_slot,
                                            'writes': len(events), 'sha256': hashlib.sha256(expected).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({'source_program_sha256': source['sha256'],
        'cases': len(results), 'refresh_uses_ms5c': args.runtime_resources, 'all_ordered_writes_equal': True,
        'scope': 'Normal single rectangles, reverse slot allocation and cached reuse; no flip/multi-block/scheduler/pixel claim.',
        'results': results}, indent=2)+'\n')
    print('Reverse-slot normal/refresh writes match:', len(results), 'cases')


if __name__ == '__main__':
    main()
