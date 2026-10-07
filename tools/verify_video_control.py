"""Exhaustively compare video-control words with native unmodified M68000."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

RAM_BASE, RETURN, STACK = 0x100000, 0xff000, 0x1feffc
SETTER, QUERY = 0x3d7e, 0x3db2
BOUNDARIES = (0, 1, 2, 0x7f, 0x80, 0xff, 0x100, 0x101, 0x7fff, 0x8000, 0xffff)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    executable = root / 'build/video_control'
    if not executable.exists():
        raise ValueError('Build build/video_control first')
    folder = root / 'artifacts/video_control'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, cli_rows = [], []

    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    fixture = hashlib.shake_256(b'ms5-video-control-whole-ram-v1').digest(65536)
    cpu.mem_write(RAM_BASE, fixture)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)

    def call(entry, d0=0xdeadbeef):
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(UC_M68K_REG_D0, d0)
        cpu.reg_write(UC_M68K_REG_A7, STACK)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(entry, RETURN, count=100)
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
            raise ValueError('Native routine failed to return: ' + hex(entry))
        return cpu.reg_read(UC_M68K_REG_D0)

    # Independent query sweep: every possible shadow with unrelated seeded RAM.
    query_values = []
    query_digest = hashlib.sha256()
    for shadow in range(65536):
        expected_ram = bytearray(fixture)
        struct.pack_into('>H', expected_ram, 0x4d90, shadow)
        cpu.mem_write(RAM_BASE + 0x4d90, shadow.to_bytes(2, 'big'))
        value = call(QUERY)
        if value != (0 if shadow & 8 else (shadow >> 8) + 1):
            raise ValueError('Native query word model differs: ' + hex(shadow))
        if bytes(cpu.mem_read(RAM_BASE, 65536)) != expected_ram or writes:
            raise ValueError('Native query changed RAM or ports: ' + hex(shadow))
        query_values.append(value)
        query_digest.update(struct.pack('>HH', shadow, value))

    def original_record(shadow, value):
        # Restore only two bytes: exhaustive checks prove every other RAM byte
        # remains identical to the immutable seeded fixture after each call.
        cpu.mem_write(RAM_BASE + 0x4d90, shadow.to_bytes(2, 'big'))
        call(SETTER, 0xbeef0000 | value)
        expected_shadow = (shadow & 0xf7) | 8 if value == 0 else (
            (((value - 1) & 255) << 8) | (shadow & 0xf7))
        expected_ram = bytearray(fixture)
        struct.pack_into('>H', expected_ram, 0x4d90, expected_shadow)
        expected_port = [(2, 0x3c0006, expected_shadow)]
        if bytes(cpu.mem_read(RAM_BASE, 65536)) != expected_ram or writes != expected_port:
            raise ValueError('Native setter RAM/port model differs: ' + repr((shadow, value, writes)))
        native_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        after = call(QUERY)
        if after != query_values[expected_shadow] or writes:
            raise ValueError('Native post-set query differs')
        if bytes(cpu.mem_read(RAM_BASE, 65536)) != expected_ram:
            raise ValueError('Native post-set query changed RAM')
        return struct.pack('>HHH', query_values[shadow], after, expected_shadow) + native_ports

    # Every input word; odd-multiplier shadow generation also spans all bits.
    records = [((value * 40503 + 17) & 65535, value) for value in range(65536)]
    # Independent complete shadow sweep with rotating setter boundary values.
    records += [(shadow, BOUNDARIES[shadow % len(BOUNDARIES)]) for shadow in range(65536)]
    batch_input = b''.join(struct.pack('>HH', *record) for record in records)
    expected_batch = bytearray()
    for shadow, value in records:
        expected_batch.extend(original_record(shadow, value))
    result = subprocess.run([str(executable), '--batch'], input=batch_input, capture_output=True)
    if result.returncode:
        raise ValueError('C++ batch rejected: ' + result.stderr.decode(errors='replace'))
    if result.stdout != expected_batch:
        first = next((at for at in range(min(len(result.stdout), len(expected_batch)))
                      if result.stdout[at] != expected_batch[at]), None)
        raise ValueError('Batch mismatch: ' + repr((first, None if first is None else first // 15,
            len(expected_batch), len(result.stdout))))

    # Actual CLI consumes all64KiB, so its returned RAM independently checks the
    # C++ implementation preserves unrelated bytes (batch uses zeroed RAM).
    cli_cases = [(shadow, value) for shadow in (0, 8, 0xff00, 0xffff, 0x5508, 0xaa07)
                 for value in BOUNDARIES]
    cli_cases += [((index * 257 + 13) & 65535, (index * 40503 + 17) & 65535)
                  for index in range(128)]
    for index, (shadow, value) in enumerate(cli_cases):
        ram = bytearray(hashlib.shake_256(b'ms5-video-control-cli-v1:' +
            index.to_bytes(4, 'big')).digest(65536))
        struct.pack_into('>H', ram, 0x4d90, shadow)
        cpu.mem_write(RAM_BASE, bytes(ram))
        call(SETTER, 0xbeef0000 | value)
        expected_ram = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_value = call(QUERY)
        if bytes(cpu.mem_read(RAM_BASE, 65536)) != expected_ram or writes:
            raise ValueError('Native CLI query changed RAM/ports')
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(out), str(ports), str(value)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ CLI rejected: ' + result.stderr)
        if (out.read_bytes() != expected_ram or ports.read_bytes() != expected_ports or
                json.loads(result.stdout) != {'value': expected_value}):
            raise ValueError('Whole-RAM CLI mismatch: ' + repr((index, shadow, value, result.stdout)))
        cli_rows.append({'initial_shadow': shadow, 'input_value': value,
            'query_after': expected_value, 'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected_ram).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entries_cpu_address_and_rom_offset': {'set': SETTER, 'query': QUERY},
        'address_mapping': 'CPU address equals decrypted ROM offset below 0x100000.',
        'query_shadow_cases': 65536, 'setter_input_word_cases': 65536,
        'setter_shadow_boundary_cases': 65536, 'batch_records': len(records),
        'batch_record_size': 15, 'batch_input_sha256': hashlib.sha256(batch_input).hexdigest(),
        'batch_output_sha256': hashlib.sha256(expected_batch).hexdigest(),
        'query_sweep_sha256': query_digest.hexdigest(),
        'native_whole_65536_byte_ram_equal': True, 'query_ram_and_ports_unchanged': True,
        'batch_queries_shadows_and_ordered_ports_equal': True,
        'cli_whole_65536_byte_ram_equal': True, 'cli_cases': len(cli_rows),
        'cli_results': cli_rows,
        'scope': 'Unmodified3d7e setter and3db2 query. Every 16-bit setter input, '
            'all shadow words with representative setter boundaries, and independent '
            'all-shadow query sweep. Original wholeRAM preservation checked on all '
            'cases with unrelated seeded bytes. Single-process C++ batch compares '
            'before/after queries, final shadow and size2/address3c0006 port write; '
            'separate CLI cases compare entire C++ outputRAM and ordered ports. '
            'D0 upper-word input is seeded for native setter; setter final D0/flags '
            'are not the public API. Natural call reachability, physical hardware '
            'video timing, rendered scanlines and full boot excluded.'}, indent=2) + '\n')
    print('Video control original/C++ match:', len(records), 'batch records;',
          65536, 'independent native queries;', len(cli_rows), 'whole-RAM CLI cases')


if __name__ == '__main__':
    main()
