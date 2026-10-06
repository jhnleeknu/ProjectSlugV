"""Compare packed palette words to original registration/preparation/upload chain."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib
from unicorn.m68k_const import UC_M68K_REG_A0
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from pack_palettes import BINDING_TABLES, extract


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source["sha256"] != "29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f":
        raise ValueError("Unsupported program revision")
    records, bindings = extract(program)
    packed = (root/'extracted/runtime/palettes.ms5p').read_bytes()
    expected_payload = b''.join(struct.pack('<I', i)+records[i][0]+records[i][1] for i in sorted(records))
    if packed != struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(expected_payload), zlib.crc32(expected_payload), 0, 0)+expected_payload:
        raise ValueError('Packed resource differs from current verified source')
    subprocess.run([str(root/'build/check_palettes'), str(root/'extracted/runtime/palettes.ms5p')], check=True)
    cpu = make_cpu(program)
    # ROM bank is fixed for this observed path. Device writes are plain mapped
    # memory: no claim about Neo Geo device side effects or timing.
    cpu.mem_map(0x200000, 0x300000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_write(0x100000, bytes(65536))
    call(cpu, 0x3ef2)
    for table in BINDING_TABLES:
        cpu.reg_write(UC_M68K_REG_A0, table)
        call(cpu, 0x8da2)
    call(cpu, 0x7196)
    call(cpu, 0x72fa)
    for binding in bindings:
        actual = bytes(cpu.mem_read(0x400000+binding['slot']*32, 32))
        if actual != records[binding['source_id']][1]:
            raise ValueError('Packed palette differs from original full preparation chain')
    report = {'source_program_sha256': source['sha256'], 'packed_sha256': hashlib.sha256(packed).hexdigest(),
              'entries': [0x3ef2, 0x8da2, 0x7196, 0x72fa], 'bindings': bindings,
              'all_palette_bytes_equal': True, 'scope': 'Three grounded palettes, zero initial RAM, normal lookup branch. Device writes stored only; no RGB/bank device/timing fidelity claim.'}
    directory = root/'artifacts/palette_resources'
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Original registration/preparation/upload chain agrees with all packed palette words')


if __name__ == '__main__':
    main()
