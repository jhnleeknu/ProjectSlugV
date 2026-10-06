"""Compare reconstructed ASCII/font61 text writes with original warning routine."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_D0, UC_M68K_REG_D1
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    # 0xcb80 contains embedded zero operands, so determine its end by original
    # execution rather than a naive search for a zero byte.
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x300000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    call(cpu, 0x3ef2)
    events = []
    def on_write(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video port write')
            events.append((value >> 16, value & 0xffff))
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    call(cpu, 0xcb64)
    end = cpu.reg_read(UC_M68K_REG_A0)
    if not 0xcb80 < end < 0xcd00 or program[end-1] != 0:
        raise ValueError('Unexpected warning stream boundary')
    directory = root/'artifacts/fixed_text'
    directory.mkdir(parents=True, exist_ok=True)
    script_path, actual_path = directory/'warning.script.bin', directory/'cpp.writes.bin'
    script_path.write_bytes(program[0xcb80:end])
    subprocess.run([str(root/'build/trace_fixed_text'), str(script_path), str(actual_path)], check=True)
    expected = b''.join(struct.pack('>HH', address, value) for address, value in events)
    (directory/'m68k.writes.bin').write_bytes(expected)
    if actual_path.read_bytes() != expected:
        raise ValueError('C++ text write sequence differs from original')
    if len(events) != 560:
        raise ValueError('Original write count changed')
    warning_events = list(events)
    warning_hash = hashlib.sha256(expected).hexdigest()
    synthetic_count = 0
    for glyph in range(1, 128):
        encoded = bytes([glyph]) if glyph != 0x5c else b'\\\\'
        script = b'\\ca\\p\x0f\\l\x03\x05' + encoded + b'\\nA\\rB\x00'
        events.clear()
        cpu.mem_write(0x100100, script)
        cpu.reg_write(UC_M68K_REG_A0, 0x100100)
        cpu.reg_write(UC_M68K_REG_D0, 0)
        cpu.reg_write(UC_M68K_REG_D1, 0)
        call(cpu, 0xe89da)
        script_path.write_bytes(script)
        subprocess.run([str(root/'build/trace_fixed_text'), str(script_path), str(actual_path)], check=True)
        reference = b''.join(struct.pack('>HH', address, value) for address, value in events)
        if actual_path.read_bytes() != reference:
            raise ValueError('Synthetic ASCII mismatch at glyph %d' % glyph)
        synthetic_count += 1
    script_path.write_bytes(program[0xcb80:end])
    subprocess.run([str(root/'build/trace_fixed_text'), str(script_path), str(actual_path)], check=True)
    events = warning_events
    report = {'source_program_sha256': source['sha256'], 'original_entry': 0xcb64,
              'stream_rom_offset': 0xcb80, 'stream_end_exclusive': end,
              'stream_sha256': hashlib.sha256(program[0xcb80:end]).hexdigest(),
              'video_port': 0x3c0000, 'ordered_writes': len(events), 'all_writes_equal': True,
              'writes_sha256': warning_hash, 'synthetic_ascii_cases': synthetic_count,
              'tile_ids': sorted(set(value & 0xfff for _, value in events)),
              'palette_slots': sorted(set(value >> 12 for _, value in events)),
              'scope': 'One original warning string ASCII/font61 path; ordered port writes, not screen or full text engine.'}
    (directory/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
