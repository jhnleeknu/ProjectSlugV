"""Compare native 92ce control-menu startup with unmodified M68000 execution."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
                               UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

RAM_BASE, RETURN, ENTRY = 0x100000, 0xff000, 0x92ce
START_HELPERS = (0xca9e, 0xa29c, 0xa2b8, 0xa370, 0x92a8)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    executable = root / 'build/start_control_menu'
    frame_executable = root / 'build/step_menu_frame'
    if not executable.exists() or not frame_executable.exists():
        raise ValueError('Build build/start_control_menu and build/step_menu_frame first')
    folder = root / 'artifacts/control_menu_start'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    writes, trace, rows = [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        trace.append({'address': address, 'a7': cpu.reg_read(UC_M68K_REG_A7),
                      'renderer': int.from_bytes(cpu.mem_read(0x107f16, 4), 'big')})

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in START_HELPERS + (0x9332,):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def original(ram, entry, line, stack):
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, 0xbeefaaaa),
                           (UC_M68K_REG_D3, line), (UC_M68K_REG_A7, stack),
                           (UC_M68K_REG_A0, 0x87654321),
                           (UC_M68K_REG_A1, int.from_bytes(ram[0x7f16:0x7f1a], 'big'))):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        writes.clear()
        trace.clear()
        try:
            cpu.emu_start(entry, RETURN, count=8000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), hex(entry),
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
            raise ValueError('Original did not reach return')
        result = {'status': struct.unpack('>i', struct.pack('>I',
            cpu.reg_read(UC_M68K_REG_D0)))[0], 'external_jump': 0,
            'line': cpu.reg_read(UC_M68K_REG_D3) & 65535}
        return bytes(cpu.mem_read(RAM_BASE, 65536)), b''.join(
            struct.pack('>BII', *write) for write in writes), result

    expected_start_writes = [(4, 0x3c0000, address << 16)
                             for address in range(0x7500, 0x7800)]
    expected_start_writes += [(4, 0x3c0000, (address << 16) | 0x0200)
                              for address in (0x7500, 0x7520, 0x7540, 0x7560)]
    expected_start_writes.append((4, 0x3c0000, 0x7580ff02))

    def compare(ram, profile, line, stack, entry=ENTRY, sequence=None):
        expected, expected_ports, expected_result = original(ram, entry, line, stack)
        observed_trace = trace.copy()
        if entry == ENTRY:
            if writes != expected_start_writes:
                raise ValueError('Original ca9e clear/control port sequence changed')
            if [item['address'] for item in trace] != list(START_HELPERS):
                raise ValueError('Original startup helper order changed: ' + repr(trace))
            if [item['a7'] for item in trace] != [stack - 4] * 4 + [stack]:
                raise ValueError('Original startup helper stack entries changed')
            if expected_result != {'status': 0, 'external_jump': 0, 'line': line}:
                raise ValueError('Original initial-frame result changed')
            if expected[0x7f03] != ram[0x7f03]:
                raise ValueError('Original slot fraction preservation changed')
            if expected[0x7df3] != (ram[0x7df3] - 1) & 255:
                raise ValueError('Original countdown decrement changed')
            for held, saved, pending in ((0x4caa, 0x7dfc, 0x4cab),
                                         (0x4cb0, 0x7dfd, 0x4cb1)):
                if expected[pending] != (ram[pending] | ((ram[held] ^ ram[saved]) & ram[held])):
                    raise ValueError('Original tail input accumulation changed')
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        args = [str(executable if entry == ENTRY else frame_executable), str(inp),
                str(native), str(out), str(ports), str(line), str(stack)]
        if entry != ENTRY:
            args += [str(root / 'extracted/runtime/menu_fonts.ms5d'),
                     str(root / 'extracted/runtime/stages')]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        parsed = json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Startup/frame mismatch: ' + repr((len(rows), profile,
                differences[:20], len(expected_ports)//9, len(actual_ports)//9,
                expected_result, parsed, observed_trace)))
        rows.append({'profile': profile, 'sequence': sequence, 'entry_cpu_address': entry,
            'entry_stack': stack, 'initial_line': line,
            'initial_fraction': ram[0x7f03], 'initial_countdown': ram[0x7df3],
            'inputs_held_saved_pending': [list(ram[at] for at in indices) for indices in
                ((0x4caa, 0x7dfc, 0x4cab), (0x4cb0, 0x7dfd, 0x4cb1))],
            'result': parsed, 'port_events': len(expected_ports)//9,
            'actual_helper_trace': observed_trace,
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), parsed['line']

    input_profiles = ((0, 0, 0), (255, 0, 0), (255, 255, 0), (0, 255, 255),
                      (0x55, 0xaa, 0x80), (0xaa, 0x55, 1), (0x81, 1, 0x40),
                      (1, 0x81, 0x20))
    for counter, line, stack, inputs, prior in itertools.product(
            (0, 1, 255), (0, 0x7000, 0xffff), (0x1feffc, 0x1f8000),
            input_profiles, range(3)):
        ram = bytearray(hashlib.shake_256(b'ms5-control-menu-start-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        old_head, old_current, old_renderer = (
            (0x107f0e, 0x107efe, 0x3650), (0x107ede, 0x107eee, 0x9332),
            (0xffffffff, 0x12345678, 0xdeadbeef))[prior]
        struct.pack_into('>III', ram, 0x7f0e, old_head, old_current, old_renderer)
        ram[0x7f1a], ram[0x7f1b] = (0, 0, 255)[prior], (0, 2, 255)[prior]
        ram[0x7df3] = counter
        ram[0x7f03] = (0, 1, 127, 255)[len(rows) % 4]
        for indices, values in (((0x4caa, 0x7dfc, 0x4cab), inputs),
                               ((0x4cb0, 0x7dfd, 0x4cb1), inputs[::-1])):
            for at, value in zip(indices, values):
                ram[at] = value
        compare(ram, 'native-start-prior-state-input-boundaries', line, stack)
    isolated = len(rows)

    # Carry the entire startup output into actual a370 frame execution. Three
    # fraction/line/stack variants cover opening through the real renderer9332.
    sequences = []
    for fraction, line, stack in ((0, 0, 0x1feffc), (127, 0x7000, 0x1f8000),
                                  (255, 0xffff, 0x1feffc)):
        ram = bytearray(65536)
        ram[0x7f03] = fraction
        label = 'start-open-fraction-' + str(fraction)
        begin = len(rows)
        ram, line = compare(ram, 'start-opening-sequence', line, stack, sequence=label)
        for _ in range(16):
            ram, line = compare(ram, 'continue-opening-sequence', line, stack,
                                entry=0xa370, sequence=label)
            if ram[0x7f1b] == 0 and ram[0x7f02] >= ram[0x7f0a]:
                break
        else:
            raise ValueError('Startup root did not finish opening')
        if int.from_bytes(ram[0x7f16:0x7f1a], 'big') != 0x9332:
            raise ValueError('Startup renderer9332 was not retained')
        if not any(item['address'] == 0x9332 for row in rows[begin:]
                   for item in row['actual_helper_trace']):
            raise ValueError('Actual renderer9332 opening call missing')
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'final_height': ram[0x7f02], 'final_mode': ram[0x7f1b]})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'address_mapping': 'CPU address equals decrypted ROM offset below 0x100000.',
        'native_menu_resource_sha256': native_hash, 'cases': len(rows),
        'isolated_start_cases': isolated, 'opening_sequences': sequences,
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_ports_equal': True,
        'signed_d0_status_and_d3_word_equal': True, 'external_jump_equal': True,
        'startup_helper_order_and_stack_entries_asserted': True,
        'startup_video_port_events_per_case': 773,
        'startup_countdown_and_new_input_accumulation_asserted': True,
        'slot_fraction_preserved': True, 'actual_renderer9332_opening_asserted': True,
        'results': rows,
        'scope': 'Unmodified 92ce startup through actual ca9e/a29c/a2b8/a370/92a8. '
            'Native root93e0 initialization x4/y8, renderer9332, first frame and common '
            'tail compared across prior globals, countdown0/1/255, input held/saved/pending '
            'bit patterns, slot fractions and line/stack boundaries. Whole startup output '
            'carried into root opening frames that actually call9332. CPU flags/registers '
            'except D0/D3, external CPU-stack memory, natural input collection, later '
            'interaction/child callbacks, pixels, hardware timing and full boot excluded.'
        }, indent=2) + '\n')
    print('Control menu startup original/C++ match:', isolated, 'starts;',
          len(rows) - isolated, 'sequence frames;', sum(row['port_events'] for row in rows),
          'ordered port events')


if __name__ == '__main__':
    main()
