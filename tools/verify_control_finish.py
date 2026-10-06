"""Compare the native 9302 post-a370 tail with unmodified M68000 execution."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5,
    UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

RAM_BASE, RETURN, ENTRY, STACK = 0x100000, 0xff000, 0x9302, 0x1feffc
FRAME_RESULTS = (0, 0x100, 0x12345600, 0xffff0000, 1, 0x12345680, 0xffffffff)
INPUT_PROFILES = ((0, 0, 0), (255, 0, 0), (255, 255, 0),
                  (0, 255, 255), (0x55, 0xaa, 0x80), (0xaa, 0x55, 1),
                  (0x81, 1, 0x40), (1, 0x81, 0x20))


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    pause = root / 'extracted/runtime/control_pause.ms5d'
    pause_hash = checked_resource(pause, program, 0x9068, 0x9086)
    executable = root / 'build/finish_control_menu'
    if not executable.exists():
        raise ValueError('Build build/finish_control_menu first')
    folder = root / 'artifacts/control_finish'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    writes, scripts, rows, negative_rows = [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        scripts.append({'script': cpu.reg_read(UC_M68K_REG_A0),
                        'renderer': cpu.reg_read(UC_M68K_REG_A1)})

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, code_hook, begin=0x3918, end=0x3918)

    def arguments(d0, style, line):
        return [str(executable), str(inp), str(pause), str(out), str(ports),
                str(d0), str(style), str(line)]

    def fixture(exit_word=0, blink=0, inputs=None, callback=0):
        ram = bytearray(hashlib.shake_256(b'ms5-control-finish-v1:' +
            (len(rows) + len(negative_rows)).to_bytes(4, 'big')).digest(65536))
        struct.pack_into('>IH', ram, 0x7df6, callback, exit_word)
        ram[0x7df3] = blink
        # These sentinels make clearing/preservation observable for both branches.
        ram[0x7dee], ram[0x7df0] = 0xa5, 0x83
        if inputs is not None:
            for indices, values in (((0x4caa, 0x7dfc, 0x4cab), inputs),
                                   ((0x4cb0, 0x7dfd, 0x4cb1), inputs[::-1])):
                for at, value in zip(indices, values):
                    ram[at] = value
        return ram

    def compare(ram, profile, d0, style, line, sequence=None):
        callback = struct.unpack_from('>I', ram, 0x7df6)[0]
        if d0 & 255 and callback:
            raise ValueError('Refuse original execution of an unanalysed callback')
        exit_word = struct.unpack_from('>H', ram, 0x7dfa)[0]
        exiting = bool(d0 & 255) and exit_word == 1
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_D0, d0), (UC_M68K_REG_D1, 0xbeef0000 | style),
                (UC_M68K_REG_D3, 0xcafe0000 | line), (UC_M68K_REG_A7, STACK),
                (UC_M68K_REG_A0, 0x87654321), (UC_M68K_REG_A1, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        scripts.clear()
        try:
            cpu.emu_start(ENTRY, RETURN, count=1000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), profile,
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
            raise ValueError('Original did not reach return')
        expected_scripts = [{'script': 0x9079, 'renderer': 0xe84c8}] if exiting else []
        if scripts != expected_scripts:
            raise ValueError('Actual 3918 script/renderer trace changed: ' + repr(scripts))
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        result_d0 = cpu.reg_read(UC_M68K_REG_D0)
        model_d0 = 1 if exiting else d0 if d0 & 255 else d0 & 0xffff0000
        if result_d0 != model_d0:
            raise ValueError('Original TST.B/MOVE.W/MOVEQ D0 model differs')
        expected_result = {'status': struct.unpack('>i', struct.pack('>I', result_d0))[0],
                           'external_jump': 0, 'line': cpu.reg_read(UC_M68K_REG_D3) & 65535}
        if expected[0x7df3] != (ram[0x7df3] - 1) & 255:
            raise ValueError('Original tail countdown byte wrap changed')
        if expected[0x7dee] != (0 if d0 & 255 else ram[0x7dee]):
            raise ValueError('Original active-menu byte clear/preservation changed')
        if expected[0x7df0] != (0 if exiting else ram[0x7df0]):
            raise ValueError('Original control-active byte clear/preservation changed')
        for held, saved, pending in ((0x4caa, 0x7dfc, 0x4cab), (0x4cb0, 0x7dfd, 0x4cb1)):
            if expected[pending] != ram[pending] | ((ram[held] ^ ram[saved]) & ram[held]):
                raise ValueError('Original new-input accumulation changed')
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run(arguments(d0, style, line), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports, parsed = out.read_bytes(), ports.read_bytes(), json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            port_difference = next(((at // 9, expected_ports[at:at+9].hex(),
                actual_ports[at:at+9].hex()) for at in range(0,
                max(len(expected_ports), len(actual_ports)), 9)
                if expected_ports[at:at+9] != actual_ports[at:at+9]), None)
            raise ValueError('Finish mismatch: ' + repr((len(rows), profile, differences[:20],
                len(actual), expected_result, parsed, port_difference, d0, style, line)))
        rows.append({'profile': profile, 'sequence': sequence,
            'frame_result_d0': d0, 'incoming_style': style, 'incoming_line': line,
            'exit_word': exit_word, 'callback_cpu_address': callback,
            'initial_countdown': ram[0x7df3], 'exiting': exiting,
            'actual_3918_scripts': scripts.copy(), 'result': parsed,
            'port_events': len(writes), 'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), parsed['line']

    for d0, exit_word, style, line in itertools.product(FRAME_RESULTS,
            (0, 1, 0x0100, 0xffff), (0, 0x0603, 0xff6b), (0, 0x7000, 0xffff)):
        compare(fixture(exit_word, len(rows) % 256), 'result-exit-style-line', d0, style, line)
    for d0, exit_word, blink in itertools.product(FRAME_RESULTS,
            (0, 1, 0x0100, 0xffff), (0, 1, 16, 17, 32, 33, 48, 49, 255)):
        compare(fixture(exit_word, blink), 'blink-byte-boundaries', d0, 0xff6b, 0xffff)
    for d0, exit_word, inputs in itertools.product(FRAME_RESULTS,
            (0, 1, 0x0100, 0xffff), INPUT_PROFILES):
        compare(fixture(exit_word, 0, inputs), 'held-saved-pending-edges', d0, 0x0603, 0x7000)
    for d0, callback, exit_word in itertools.product(FRAME_RESULTS[:4],
            (1, 0x9302, 0xdeadbeef, 0xffffffff), (0, 1)):
        compare(fixture(exit_word, 1, callback=callback), 'unused-callback-zero-low-byte',
                d0, 0xff6b, 0xffff)
    isolated = len(rows)
    sequences = []
    for d0, exit_word in ((0x12345600, 1), (0x12345680, 0), (0xffffffff, 1)):
        ram = fixture(exit_word, 1, INPUT_PROFILES[0])
        line, label, begin = 0xffff, 'tail-%08x-exit-%04x' % (d0, exit_word), len(rows)
        for frame in range(40):
            for held, pending in ((0x4caa, 0x4cab), (0x4cb0, 0x4cb1)):
                ram[held] = (0, 0x81, 0xff, 1, 0)[frame % 5]
                if frame % 7 == 0:
                    ram[pending] = 0
            ram, line = compare(ram, 'whole-output-carry', d0, 0xff6b, line, sequence=label)
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'final_countdown': ram[0x7df3]})
    # Unsupported callbacks must fail before publishing either output file.
    for d0, callback, exit_word in itertools.product(FRAME_RESULTS[4:],
            (1, 0x9302, 0xdeadbeef, 0xffffffff), (0, 1)):
        inp.write_bytes(fixture(exit_word, callback=callback))
        for existing in (False, True):
            sentinels = (b'prior-ram-output\0\xff', b'prior-port-output\xff\0')
            for path, sentinel in zip((out, ports), sentinels):
                if existing:
                    path.write_bytes(sentinel)
                else:
                    path.unlink(missing_ok=True)
            result = subprocess.run(arguments(d0, 0xff6b, 0xffff), capture_output=True, text=True)
            if result.returncode == 0:
                raise ValueError('Unsupported callback was accepted')
            for path, sentinel in zip((out, ports), sentinels):
                if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                        not existing and path.exists()):
                    raise ValueError('Rejected callback published/modified output: ' + str(path))
            negative_rows.append({'frame_result_d0': d0, 'callback_cpu_address': callback,
                'exit_word': exit_word, 'existing_outputs': existing,
                'returncode': result.returncode, 'stderr': result.stderr.strip(),
                'outputs_preserved': True, 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    exit_count = sum(row['exiting'] for row in rows)
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'address_mapping': 'CPU address equals decrypted ROM offset below 0x100000.',
        'native_pause_resource_sha256': pause_hash, 'cases': len(rows),
        'isolated_cases': isolated, 'exit_cases': exit_count,
        'actual_3918_script_counts': {'0x9079': exit_count},
        'ordered_port_events': sum(row['port_events'] for row in rows),
        'output_carry_sequences': sequences, 'negative_cases': len(negative_rows),
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_ports_equal': True,
        'signed_d0_and_d3_word_equal': True, 'd0_byte_test_and_word_clear_asserted': True,
        'countdown_wrap_and_input_accumulation_asserted': True,
        'unsupported_callback_failures_preserve_outputs': True,
        'results': rows, 'negative_results': negative_rows,
        'scope': 'Post-a370 tail9302 with callback7df6 zero whenever low D0 is nonzero. '
            'Actual exit928e uses native script9079 and renderer e84c8 through3918. '
            'Full D0 byte-test/word-clear, exact exit-word1, styles, line boundaries, '
            'blink byte wrap and both input-edge accumulators compared. Whole RAM carried '
            'across40-frame tails. Nonzero callbacks accepted only when low D0 is zero '
            'and therefore unused; other callbacks rejected by C++ without executing '
            'unknown original targets or changing outputs. a370 frame dispatcher, arbitrary '
            'callbacks, other CPU registers/flags, external stack memory, natural input '
            'acquisition, hardware timing, pixels and full boot excluded.'}, indent=2) + '\n')
    print('Control finish original/C++ match:', len(rows), 'cases;', exit_count,
          'native3918 exits;', len(negative_rows), 'output-preserving callback rejections')


if __name__ == '__main__':
    main()
