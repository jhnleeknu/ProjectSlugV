"""Compare palette dirty-block transfer with the original 68000 kernel."""
import hashlib
import json
from pathlib import Path
import subprocess

import unicorn
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM revision')
    cases = []
    # Exercise every block individually, plus none/all/alternating dirty.
    for selected in range(-3, 256):
        data = bytearray(hashlib.shake_256(b'palette-transfer-v1' + selected.to_bytes(2, 'big', signed=True)).digest(16384))
        for block in range(256):
            dirty = selected == -2 or (selected == -3 and block % 2 == 0) or selected == block
            data[block * 32] = (data[block * 32] & 0x7f) | (0x80 if dirty else 0)
        cases.append(bytes(data))
    directory = root / 'artifacts/palette_upload'
    directory.mkdir(parents=True, exist_ok=True)
    input_path, output_path = directory / 'input.bin', directory / 'cpp.bin'
    input_path.write_bytes(b''.join(cases))
    subprocess.run([str(root / 'build/upload_palette'), str(input_path), str(output_path)], check=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x400000, 0x3000)
    expected = []
    for data in cases:
        cpu.mem_write(0x105da2 - 16, bytes([0x5a]) * 16 + data[:8192] + bytes([0xa5]) * 16)
        cpu.mem_write(0x400000, data[8192:] + bytes([0x3c]) * 16)
        cpu.reg_write(UC_M68K_REG_A0, 0x105da2)
        cpu.reg_write(UC_M68K_REG_A1, 0x400000)
        cpu.emu_start(0x7320, 0x871a, count=2048)
        if cpu.reg_read(UC_M68K_REG_PC) != 0x871a:
            raise ValueError('Original kernel did not reach stop address')
        if bytes(cpu.mem_read(0x105da2 - 16, 16)) != bytes([0x5a]) * 16 or bytes(cpu.mem_read(0x107da2, 16)) != bytes([0xa5]) * 16 or bytes(cpu.mem_read(0x402000, 16)) != bytes([0x3c]) * 16:
            raise ValueError('Original kernel changed boundary guards')
        expected.append(bytes(cpu.mem_read(0x105da2, 8192)) + bytes(cpu.mem_read(0x400000, 8192)))
    expected = b''.join(expected)
    actual = output_path.read_bytes()
    (directory / 'm68k.bin').write_bytes(expected)
    if actual != expected:
        raise ValueError('Palette staging or destination differs from original kernel')
    report = {'source_program_sha256': source['sha256'], 'entry_cpu_address': 0x7320,
              'stop_cpu_address': 0x871a, 'cases': len(cases), 'bytes_per_case': 16384,
              'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
              'all_bytes_equal': True, 'output_sha256': hashlib.sha256(actual).hexdigest(),
              'scope': 'Dirty-block kernel staging and destination bytes only; excludes wrapper, bank selection, RGB conversion, device timing and CPU register/flag equivalence.'}
    (directory / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
