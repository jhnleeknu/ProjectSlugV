"""Compare active control waiting with unmodified M68000 entry execution."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5,
    UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_control_request import model as request_model
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

RAM_BASE, RETURN = 0x100000, 0xff000
BRANCHES = {0x9256: 'idle', 0x925e: 'step', 0x926c: 'held', 0x92ce: 'menu'}


def expected_branch(ram):
    request = request_model(ram)
    for enabled, request_bit, action_bit in ((1, 2, 1), (2, 8, 4)):
        if not ram[0x7df0] & enabled:
            continue
        if request & request_bit:
            return 'menu'
        if ram[0xf002]:
            if ram[0x4cb5] & action_bit:
                return 'step'
            if ram[0x4cb4] & action_bit:
                return 'held'
    return 'idle'


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    menu = root / 'extracted/runtime/control_menu_tree.ms5d'
    pause = root / 'extracted/runtime/control_pause.ms5d'
    resource_hashes = {'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
                      'pause': checked_resource(pause, program, 0x9068, 0x9086)}
    executable = root / 'build/step_control_wait'
    if not executable.exists():
        raise ValueError('Build build/step_control_wait first')
    folder = root / 'artifacts/control_wait_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    writes, scripts, branches, rows = [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (RAM_BASE <= address and address + size <= RAM_BASE + 65536) and not (0x1f7000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))

    def code_hook(cpu, address, size, user):
        if address == 0x3902:
            scripts.append(cpu.reg_read(UC_M68K_REG_A0))
        else:
            branches.append(BRANCHES[address])

    def stop(cpu, address, size, user):
        if address == RETURN:
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, stop)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in tuple(BRANCHES) + (0x3902,):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def compare(ram, profile, style, line, entry, stack, sequence=None, register_inputs=None):
        branch = 'menu' if entry == 0x92ce else expected_branch(ram)
        d1, d3 = register_inputs if register_inputs is not None else (
            ((((len(rows) * 0x1237) ^ 0xbeef) & 65535) << 16) | style,
            ((((len(rows) * 0x7341) ^ 0xcafe) & 65535) << 16) | line)
        assert d1 & 65535 == style and d3 & 65535 == line
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, d1),
                (UC_M68K_REG_D3, d3), (UC_M68K_REG_A7, stack),
                (UC_M68K_REG_A0, 0x87654321),
                (UC_M68K_REG_A1, int.from_bytes(ram[0x7f16:0x7f1a], 'big'))):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        writes.clear()
        scripts.clear()
        branches.clear()
        try:
            cpu.emu_start(entry, RETURN, count=8000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), profile,
                hex(entry), hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
            raise ValueError('Original did not reach return')
        if branches != [branch]:
            raise ValueError('Original priority/branch model mismatch: ' + repr(
                (profile, branch, branches)))
        expected_scripts = []
        if branch == 'idle' and not ram[0xf001] & 64:
            expected_scripts = [0x9068 if ((ram[0x7df3] - 1) & 0x30) else 0x9079]
        if scripts != expected_scripts:
            raise ValueError('Actual 3902 script trace differs: ' + repr(scripts))
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_result = {'status': struct.unpack('>i', struct.pack('>I',
            cpu.reg_read(UC_M68K_REG_D0)))[0], 'external_jump': 0,
            'line': cpu.reg_read(UC_M68K_REG_D3) & 65535,
            'd1': cpu.reg_read(UC_M68K_REG_D1) & 0xffffffff,
            'd3': cpu.reg_read(UC_M68K_REG_D3) & 0xffffffff}
        if branch == 'step' and (expected[0x7df2] != 15 or expected_result['status'] != 2):
            raise ValueError('Original step repeat/status assertion failed')
        if branch == 'held':
            repeat = (ram[0x7df2] - 1) & 255 if ram[0x7df2] else 1
            if expected[0x7df2] != repeat or expected_result['status'] != (0 if ram[0x7df2] else 2):
                raise ValueError('Original held byte borrow assertion failed')
        countdown_decrements = 2 if expected_scripts else 1
        if expected[0x7df3] != (ram[0x7df3] - countdown_decrements) & 255:
            raise ValueError('Original countdown assertion failed')
        for held, saved, pending in ((0x4caa, 0x7dfc, 0x4cab), (0x4cb0, 0x7dfd, 0x4cb1)):
            if expected[pending] != ram[pending] | ((ram[held] ^ ram[saved]) & ram[held]):
                raise ValueError('Original input accumulation assertion failed')
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        args = [str(root / 'build/start_control_menu' if entry == 0x92ce else executable),
            '--registers', str(d1), str(d3), str(inp), str(menu)]
        if entry != 0x92ce:
            args += [str(pause)]
        args += [str(out), str(ports)]
        if entry != 0x92ce:
            args += [str(style)]
        args += [str(line), str(stack)]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports, parsed = out.read_bytes(), ports.read_bytes(), json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Wait mismatch: ' + repr((len(rows), profile, differences[:20],
                len(expected_ports)//9, len(actual_ports)//9, expected_result, parsed,
                'style-line-entry-stack', style, line, entry, stack,
                'first-port-difference', next(((at//9, expected_ports[at:at+9].hex(),
                    actual_ports[at:at+9].hex()) for at in range(0, max(len(expected_ports),
                    len(actual_ports)), 9) if expected_ports[at:at+9] != actual_ports[at:at+9]), None))))
        rows.append({'profile': profile, 'sequence': sequence, 'entry_cpu_address': entry,
            'entry_stack': stack, 'incoming_d1': d1, 'incoming_d3': d3, 'incoming_style': style, 'incoming_line': line,
            'active': ram[0x7df0], 'repeat': ram[0x7df2], 'countdown': ram[0x7df3],
            'selector_state': [ram[at] for at in (0x12, 0xfd82, 0xf002, 0xfdb6, 0xfdb7)],
            'inputs': [ram[at] for at in (0x4cb4, 0x4cb5, 0x4cb9, 0x4cbf)],
            'actual_branch': branch, 'actual_3902_scripts': scripts.copy(),
            'result': parsed, 'port_events': len(expected_ports)//9,
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), parsed

    def fixture(active=3, pending=0, held=0, counter=0, blink=0, selector=0):
        ram = bytearray(hashlib.shake_256(b'ms5-control-wait-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0x7df0], ram[0x7dee] = active, 0
        ram[0x7df2], ram[0x7df3], ram[0xf001] = counter, blink, 0
        ram[0x4cb5], ram[0x4cb4] = pending, held
        ram[0x4cb9], ram[0x4cbf] = 128, 128
        mode, special, gate, p1, p2 = ((2, 0, 1, 1, 1), (2, 255, 1, 1, 1),
            (1, 0, 1, 1, 1), (2, 0, 0, 1, 1), (2, 255, 1, 3, 0),
            (2, 255, 0, 1, 1))[selector]
        for at, value in ((0x12, mode), (0xfd82, special), (0xf002, gate),
                          (0xfdb6, p1), (0xfdb7, p2)):
            ram[at] = value
        return ram

    scenarios = ((3, 9, 0), (3, 8, 1), (3, 6, 0), (3, 2, 4), (3, 4, 0),
        (3, 0, 4), (1, 8, 0), (2, 3, 0), (2, 0, 5), (3, 15, 15),
        (0x80, 15, 15), (0x83, 0, 0))
    for scenario, selector, counter, style in itertools.product(
            scenarios, range(6), (0, 1, 2, 15, 255), (0, 0x0603, 0xff6b)):
        ram = fixture(*scenario, counter=counter, blink=len(rows) % 256, selector=selector)
        compare(ram, 'player-priority-selector-repeat', style,
                (0, 0x7000, 0xffff)[len(rows) % 3],
                (0x9136, 0x91c2)[len(rows) % 2],
                (0x1feffc, 0x1f8000)[len(rows) % 2])
    for active, blink, suppress, style in itertools.product(
            (1, 2, 3, 0x80), (0, 1, 16, 17, 32, 33, 48, 49, 255),
            (0, 64), (0, 0x0603, 0xff6b)):
        ram = fixture(active=active, blink=blink)
        ram[0xf001] = suppress
        compare(ram, 'idle-blink-suppression-boundaries', style, 0xffff,
                (0x9136, 0x91c2)[len(rows) % 2], 0x1feffc)
    for blink, style, line, stack in itertools.product((0, 1, 255), (0, 0x0603, 0xff6b),
            (0, 0x7000, 0xffff), (0x1feffc, 0x1f8000)):
        compare(fixture(blink=blink), 'direct-menu-start-full-registers', style, line, 0x92ce, stack)
    isolated = len(rows)
    sequences = []
    for active, held in ((1, 1), (2, 4)):
        ram = fixture(active=active, held=held, counter=15, blink=0)
        register_inputs = (0xbeef0603, 0xcafe7000)
        label, begin = 'held-player-' + str(active), len(rows)
        for frame in range(20):
            ram, parsed = compare(ram, 'held-output-carry', register_inputs[0] & 65535, register_inputs[1] & 65535,
                0x9136, 0x1feffc, sequence=label, register_inputs=register_inputs)
            register_inputs = parsed['d1'], parsed['d3']
        statuses = [row['result']['status'] for row in rows[begin:]]
        if statuses != [0] * 15 + [2, 0, 2, 0, 2]:
            raise ValueError('Held sequence did not retain repeat countdown behavior')
        sequences.append({'label': label, 'frames': len(rows) - begin, 'statuses': statuses, 'full_d1_d3_cli_outputs_carried': True})
    for suppress in (0, 64):
        ram = fixture(blink=49)
        ram[0xf001] = suppress
        register_inputs = (0xbeefff6b, 0xcafeffff)
        label, begin = 'blink-suppression-' + str(suppress), len(rows)
        for frame in range(40):
            ram, parsed = compare(ram, 'blink-output-carry', register_inputs[0] & 65535, register_inputs[1] & 65535,
                0x9136, 0x1f8000, sequence=label, register_inputs=register_inputs)
            register_inputs = parsed['d1'], parsed['d3']
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'final_countdown': ram[0x7df3], 'full_d1_d3_cli_outputs_carried': True})
    negatives = []
    sentinel = b'prior-wait-register-output\0\xff'
    def reject(ram, mode, label, d1='0xbeef0603', d3='0xcafeffff', selected_pause=pause):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        args = [str(root / 'build/start_control_menu' if mode == 'start' else executable),
            '--registers', d1, d3, str(inp), str(menu)]
        if mode == 'wait':
            args += [str(selected_pause)]
        args += [str(out), str(ports)]
        if mode == 'wait':
            args += ['0x0603']
        args += ['0xffff', '0x1feffc']
        actual = subprocess.run(args, capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'mode': mode, 'failure': label, 'outputs_preserved': True, 'original_executed': False})
    for mode in ('start', 'wait'):
        for register in ('d1', 'd3'):
            for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
                values = {'d1': '0xbeef0603', 'd3': '0xcafeffff'}
                values[register] = invalid
                reject(fixture(), mode, 'invalid-' + register + '-' + invalid, **values)
        for size in (0, 65535, 65537):
            reject(bytes(size), mode, 'invalid-ram-size')
        reject(fixture(), mode, 'register-line-inconsistency', d3='0xcafefffe')
    reject(fixture(), 'wait', 'register-style-inconsistency', d1='0xbeef0602')
    reject(fixture(active=0), 'wait', 'inactive-state')
    already_open = fixture()
    already_open[0x7dee] = 1
    reject(already_open, 'wait', 'already-open-state')
    bad_pause = folder / 'invalid-location.ms5d'
    payload = bytearray(program[0x9068:0x9086])
    for at in (0x906a, 0x907b):
        payload[at - 0x9068:at - 0x9068 + 2] = b'\xff\xff'
    bad_pause.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0x9068, 0x9068, len(payload), zlib.crc32(payload), 0) + payload)
    reject(fixture(blink=1), 'wait', 'late-invalid-pause-location', selected_pause=bad_pause)
    counts = {branch: sum(row['actual_branch'] == branch for row in rows)
              for branch in BRANCHES.values()}
    script_counts = {hex(address): sum(address in row['actual_3902_scripts'] for row in rows)
                     for address in (0x9068, 0x9079)}
    if not all(counts.values()) or not all(script_counts.values()):
        raise ValueError('Missing actual original branch/script coverage')
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_addresses_and_rom_offsets': [0x9136, 0x91c2, 0x92ce],
        'address_mapping': 'CPU address equals decrypted ROM offset below 0x100000.',
        'native_resource_sha256': resource_hashes, 'cases': len(rows),
        'isolated_cases': isolated, 'branch_counts': counts, 'actual_3902_script_counts': script_counts,
        'output_carry_sequences': sequences, 'whole_65536_byte_ram_equal': True,
        'ordered_port_events': sum(row['port_events'] for row in rows),
        'ordered_video_watchdog_ports_equal': True, 'signed_d0_full_d1_and_full_d3_equal': True,
        'player_priority_repeat_borrow_countdown_and_input_accumulation_asserted': True,
        'results': rows, 'negative_cases': len(negatives), 'negative_results': negatives,
        'scope': 'Active 7df0!=0 / 7dee=0 control waiting through original selector9086, '
            'idle renderer3902 and native menu startup92ce without stubs. All selector paths, '
            'player priority, repeat byte borrow, blink boundaries/suppression, incoming styles, '
            'lines and external stack addresses compared. Entire output RAM carried across '
            'repeat and blink frames together with full D1/D3 CLI outputs. Native92ce start '
            'also compares full registers after ca9e/title measurements/height0 frame. '
            'Other CPU registers/flags, external stack contents, '
            'natural input acquisition, physical hardware timing, pixels and full boot excluded.'
        }, indent=2) + '\n')
    print('Control wait original/C++ match:', len(rows), 'cases;', counts, '; scripts', script_counts)


if __name__ == '__main__':
    main()
