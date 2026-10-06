"""Compare original slot-pool configuration, including sentinels, to C++."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory = root/'artifacts/sprite_pool'
    directory.mkdir(parents=True, exist_ok=True)
    cpu = make_cpu(program)
    original = hashlib.shake_256(b'slot-pool').digest(65536)
    input_path, output_path = directory/'input.bin', directory/'cpp.bin'
    input_path.write_bytes(original)
    results = []
    for selector in (0, 1, 65535):
        for lower in (0, 1, 379, 380, 381, 32767, 32768, 65535):
            for upper in (0, 1, 379, 380, 381, 32767, 32768, 65535):
                cpu.mem_write(0x100000, original)
                for reg, value in ((UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_D0, selector), (UC_M68K_REG_D1, lower), (UC_M68K_REG_D2, upper)):
                    cpu.reg_write(reg, value)
                call(cpu, 0xcd1c)
                actual = bytes(cpu.mem_read(0x100000, 65536))
                lo = lower if lower < 380 else 65535
                hi = upper if lo < upper else 65535
                expected = bytearray(original)
                at = 0x8d3e if selector == 0 else 0x8d46
                expected[at:at+8] = struct.pack('>4H', lo, hi, lo, hi)
                if actual != expected:
                    raise ValueError('Slot model differs from original')
                subprocess.run([str(root/'build/configure_sprite_pool'), str(input_path), str(output_path), str(selector), str(lower), str(upper)], check=True)
                if output_path.read_bytes() != actual:
                    raise ValueError('C++ slot configuration differs from original')
                results.append({'selector': selector, 'lower': lower, 'upper': upper, 'pool_words': [lo,hi,lo,hi], 'ram_sha256': hashlib.sha256(actual).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({'source_program_sha256': source['sha256'], 'entry': 0xcd1c,
        'cases': len(results), 'all_ram_equal': True,
        'scope': 'Exact setter RAM effect, including malformed/mixed sentinel bounds. Dispatchers support valid 0..380 pools and fully disabled FFFF pools only.', 'results': results}, indent=2)+'\n')
    print('Slot configuration full RAM matches:', len(results), 'cases')


if __name__ == '__main__':
    main()
