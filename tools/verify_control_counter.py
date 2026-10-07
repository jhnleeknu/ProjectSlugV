"""Compare native fe2 counter guard and43dbc phase update with unmodified ROM."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

RAM_BASE, RETURN, ENTRY, TRAP, PHASE_HELPER = 0x100000, 0xff000, 0xfe2, 0xfee, 0x43dbc
OBJECTS = (0x100000, 0x100100, 0x100f5c, 0x10ff80, 0x10d416, 0x10d414)
COUNTERS = (0, 1, 0x7fff, 0x8000, 0xffff)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    executable = root / 'build/advance_control_counter'
    if not executable.exists():
        raise ValueError('Build build/advance_control_counter first')
    folder = root / 'artifacts/control_counter'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    trace, ports, rows, negatives = [], [], [], []

    def code_hook(cpu, address, size, user):
        trace.append(address)
        if address == TRAP:
            cpu.emu_stop()

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            ports.append((size, address, value & ((1 << (size * 8)) - 1)))

    for address in (TRAP, PHASE_HELPER):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)

    def fixture(address, counter, phase, matching):
        ram = bytearray(hashlib.shake_256(b'ms5-control-counter-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        struct.pack_into('>H', ram, address - RAM_BASE + 0x7e, counter)
        ram[0xd494] = phase
        # Phase can alias the object's counter high byte. Derive the global
        # comparison word from the final seeded RAM, rather than hiding aliasing.
        object_counter = struct.unpack_from('>H', ram, address - RAM_BASE + 0x7e)[0]
        struct.pack_into('>H', ram, 0x000e, object_counter if matching else object_counter ^ 1)
        return ram

    def compare(ram, address, profile, sequence=None):
        offset = address - RAM_BASE + 0x7e
        local_counter = struct.unpack_from('>H', ram, offset)[0]
        global_counter = struct.unpack_from('>H', ram, 0x000e)[0]
        trapped = local_counter != global_counter
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, address), (UC_M68K_REG_A7, 0x1feffc),
                (UC_M68K_REG_D0, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        trace.clear()
        ports.clear()
        cpu.emu_start(ENTRY, RETURN, count=1000)
        expected_pc = TRAP if trapped else RETURN
        if cpu.reg_read(UC_M68K_REG_PC) != expected_pc:
            raise ValueError('Original did not stop at expected return/trap boundary')
        if trace != ([TRAP] if trapped else [PHASE_HELPER]):
            raise ValueError('Original phase-helper/trap trace differs: ' + repr(trace))
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        model = bytearray(ram)
        if not trapped:
            next_counter = (local_counter + 1) & 65535
            struct.pack_into('>H', model, 0x000e, next_counter)
            struct.pack_into('>H', model, offset, next_counter)
            model[0xd494] = (model[0xd494] & 1) + 1
        if expected != model or ports:
            raise ValueError('Native sequential-word-write/phase model differs: ' + repr(
                (address, local_counter, global_counter, ram[0xd494], trapped)))
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(out), str(address)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr)))
        if out.read_bytes() != expected or json.loads(result.stdout) != {'trap15': trapped}:
            raise ValueError('Counter mismatch: ' + repr((len(rows), profile, address,
                local_counter, global_counter, ram[0xd494], result.stdout)))
        rows.append({'profile': profile, 'sequence': sequence, 'object_cpu_address': address,
            'object_counter_cpu_address': address + 0x7e, 'local_counter': local_counter,
            'global_counter': global_counter, 'initial_phase': ram[0xd494],
            'final_phase': expected[0xd494], 'trap15': trapped, 'actual_trace': trace.copy(),
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected)

    for phase, matching, address in itertools.product(range(256), (False, True),
            (0x100f5c, 0x10d416, 0x10d414)):
        compare(fixture(address, 0xffff, phase, matching), address,
                'all-phase-bytes-match-mismatch-and-alias')
    for counter, matching, address, phase in itertools.product(COUNTERS, (False, True),
            OBJECTS, (0, 1, 255)):
        compare(fixture(address, counter, phase, matching), address,
                'word-wrap-object-boundaries-and-alias')
    isolated = len(rows)
    sequences = []
    for address in (0x100f5c, 0x10d416, 0x10d414):
        ram = fixture(address, 0xfffe, 255, True)
        label, begin = 'carried-object-%06x' % address, len(rows)
        for _ in range(6):
            ram = compare(ram, address, 'whole-output-carry', sequence=label)
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'trap_frames': sum(row['trap15'] for row in rows[begin:])})
    good = fixture(0x100f5c, 0xffff, 255, True)
    inp.write_bytes(good)
    sentinel = b'previous-counter-output\0\xff'
    for invalid in ('-1', '0', '0xfffff', '0x100001', '0x10ff82', '0x110000',
                    '0xffffffff', '0x100000000', 'bad'):
        for existing in (False, True):
            if existing:
                out.write_bytes(sentinel)
            else:
                out.unlink(missing_ok=True)
            result = subprocess.run([str(executable), str(inp), str(out), invalid],
                                    capture_output=True, text=True)
            if result.returncode == 0 or (existing and (
                    not out.exists() or out.read_bytes() != sentinel)) or (not existing and out.exists()):
                raise ValueError('Invalid object address changed outputs: ' + invalid)
            negatives.append({'failure': 'invalid-object-address', 'value': invalid,
                'existing_outputs': existing, 'outputs_preserved': True,
                'stderr': result.stderr.strip(), 'original_executed': False})
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        out.write_bytes(sentinel)
        result = subprocess.run([str(executable), str(inp), str(out), str(0x100f5c)],
                                capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Invalid RAM size changed output')
        negatives.append({'failure': 'invalid-ram-size', 'size': size,
            'outputs_preserved': True, 'original_executed': False})
    inp.write_bytes(good)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        result = subprocess.run([str(executable), str(inp), str(alias), str(0x100f5c)],
                                capture_output=True, text=True)
        if result.returncode == 0 or inp.read_bytes() != good:
            raise ValueError('Input/output alias changed input')
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name,
            'input_preserved': True, 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    trap_count = sum(row['trap15'] for row in rows)
    helper_count = len(rows) - trap_count
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'trap_boundary_cpu_address': TRAP, 'phase_helper_cpu_address': PHASE_HELPER,
        'address_mapping': 'CPU address equals decrypted ROM offset below0x100000.',
        'cases': len(rows), 'isolated_cases': isolated,
        'actual_trap_boundary_cases': trap_count, 'actual_phase_helper_calls': helper_count,
        'whole_65536_byte_ram_equal': True, 'no_video_watchdog_ports_asserted': True,
        'word_wrap_and_sequential_phase_alias_order_asserted': True,
        'all_256_initial_phase_bytes_checked': True, 'output_carry_sequences': sequences,
        'negative_cases': len(negatives), 'negative_results': negatives,
        'cli_failures_and_aliases_preserve_outputs': True, 'results': rows,
        'scope': 'Originalfe2 counter guard through actual43dbc phase update. Mismatch '
            'stops atfee before executing TRAP15 and leaves allRAM unchanged. Matching '
            'counters wrap as16-bit words; global word then object word then phase byte '
            'update order checked including object10d416 whose counter aliases phase d494. '
            'All256 phase bytes, low/high valid object boundaries and word boundaries '
            'compared. Trap handler behavior, object reachability, other registers/flags, '
            'external CPU stack memory, natural frame scheduling and full boot excluded.'}, indent=2) + '\n')
    print('Control counter original/C++ match:', len(rows), 'cases;', trap_count,
          'trap boundaries;', helper_count, 'actual phase helper calls;', len(negatives), 'CLI failures')


if __name__ == '__main__':
    main()
