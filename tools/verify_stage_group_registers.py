"""Compare direct native9802 stage-group callback and full D1/D3 outputs."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.m68k_const import (UC_M68K_REG_A2, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_menu_event import SOURCE_SHA256
from verify_object_reset import make_cpu
from verify_stage_catalog import checked_resource, verify_resources

MENU = 0x978a
CALLBACK = 0x9802
RAM_BASE = 0x100000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    # Assert the original native descriptor, including its ten zero arguments.
    items = [struct.unpack_from('>IIH', program, MENU + 16 + index * 10)
             for index in range(10)]
    if (any(item != (0x976a, CALLBACK, 0) for item in items) or
            program[MENU + 116:MENU + 120] != b'\xff' * 4 or
            struct.unpack_from('>H', program, MENU + 14)[0] != 0):
        raise ValueError('Native 978a descriptor changed')
    stages = root / 'extracted/runtime/stages'
    verify_resources(stages, program, source)
    # Address zero is an actual ROM string source. Its leading NUL renders glyph
    # zero; the following 10/f3 bytes are consumed until the next NUL.
    null_hash = checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)
    if program[:4] != bytes.fromhex('0010f300'):
        raise ValueError('Native address-zero name bytes changed')
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    executable = root / 'build/dispatch_stage_group_menu'
    folder = root / 'artifacts/stage_group_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
                             ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows = [], []

    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (RAM_BASE <= address and address + size <= RAM_BASE + 65536) and not (0x1f7000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    def stop(cpu, address, size, user):
        if address == 0xff000:
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, stop)

    def ram_for(index, older, selected, x=4, y=8, width=24, sentinel=0):
        ram = bytearray(hashlib.shake_256(
            b'ms5-stage-group-menu-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        current = 0x107efe
        head = 0x107eee if older else current
        struct.pack_into('>II', ram, 0x7f0e, head, current)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        struct.pack_into('>H', ram, 0x7dfa, sentinel)
        for address in range(head, 0x107f0e, 16):
            at = address - RAM_BASE
            struct.pack_into('>I', ram, at, MENU)
            ram[at + 4] = 0
            ram[at + 6:at + 13] = bytes((10, selected, index, x, y, width, 12))
            ram[at + 15] = 0
        return ram

    def compare(ram, event, line=0x7000, stack=0x1feffc, profile='native-events', register_inputs=None):
        d1, d3 = register_inputs if register_inputs is not None else (
            (0xabcdab68 ^ (len(rows) * 0x1234567)) & 0xffffffff,
            ((((len(rows) * 0x7341) ^ 0xcafe) & 65535) << 16) | line)
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_D0, event), (UC_M68K_REG_D1, d1),
                           (UC_M68K_REG_D3, d3), (UC_M68K_REG_A2, struct.unpack_from('>I', ram, 0x7f12)[0]), (UC_M68K_REG_A7, stack)):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        # Supplied A7 is the formatter callback's direct native entry A7.
        try:
            cpu.emu_start(CALLBACK, 0xff000, count=2000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((profile, event,
                             hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original did not return: ' + hex(cpu.reg_read(UC_M68K_REG_PC)))
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_result = {'a2': cpu.reg_read(UC_M68K_REG_A2),
            'd1': cpu.reg_read(UC_M68K_REG_D1) & 0xffffffff, 'd3': cpu.reg_read(UC_M68K_REG_D3) & 0xffffffff}
        if event not in (3, 5):
            assert expected_result['d1'] == d1 and expected_result['d3'] == d3
        if event == 3:
            assert expected_result['d1'] >> 8 == 0 and expected_result['d3'] == d3
        if event == 5:
            assert expected_result['d1'] >> 16 == 0
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(native), str(font), str(stages), str(out), str(ports),
                                 str(event), str(d1), str(d3), str(stack)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((profile, event, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        parsed = json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at])
                           for at in range(min(len(actual), 65536)) if actual[at] != expected[at]]
            port_difference = next((at for at in range(min(len(actual_ports), len(expected_ports)))
                                    if actual_ports[at] != expected_ports[at]), None)
            raise ValueError('Group menu mismatch: ' + repr((profile, ram[0x7f06], event,
                differences[:16], len(expected_ports) // 9, len(actual_ports) // 9,
                port_difference, expected_result, parsed)))
        # These assertions additionally document the original action semantics.
        if event == 3 and (expected[0xd680] != 9 + ram[0x7f06] or
                           expected[0xd681] != 0 or expected[0x7dfa:0x7dfc] != b'\x00\x01'):
            raise ValueError('Original stage confirmation semantics changed')
        if event == 4 and expected[0x7dfa:0x7dfc] != ram[0x7dfa:0x7dfc]:
            raise ValueError('Original cancellation changed sentinel')
        if event not in (3, 4, 5) and (expected != ram or writes):
            raise ValueError('Original nominal no-op changed RAM or ports')
        rows.append({'profile': profile, 'row': ram[0x7f06], 'stage_group': 9 + ram[0x7f06],
                     'event': event, 'selected': ram[0x7f05],
                     'head': struct.unpack_from('>I', ram, 0x7f0e)[0],
                     'current': struct.unpack_from('>I', ram, 0x7f12)[0],
                     'sentinel': struct.unpack_from('>H', ram, 0x7dfa)[0],
                     'x': ram[0x7f07], 'y': ram[0x7f08], 'width': ram[0x7f09],
                     'initial_line': d3 & 65535, 'incoming_d1': d1, 'incoming_d3': d3, 'callback_entry_stack': stack,
                     'result': parsed, 'port_events': len(writes),
                     'input_sha256': hashlib.sha256(ram).hexdigest(),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(actual), (parsed['d1'], parsed['d3'])

    for index, event, older, selected in itertools.product(
            range(10), range(8), (False, True), (False, True)):
        compare(ram_for(index, older, index if selected else (index + 1) % 10), event)
    native_cases = len(rows)
    for index, older, selected, geometry, line, stack in itertools.product(
            range(10), (False, True), (False, True),
            ((0, 0, 0), (253, 250, 255), (255, 255, 1)),
            (0, 0x74ff, 0xffff), (0x1feffc, 0x1f8000)):
        compare(ram_for(index, older, index if selected else (index + 1) % 10, *geometry),
                5, line, stack, 'format-style-coordinate-stack')
    formatted_cases = len(rows) - native_cases
    for index, older, event, sentinel in itertools.product(
            range(10), (False, True), (3, 4), (1, 0xffff)):
        compare(ram_for(index, older, index, sentinel=sentinel), event,
                profile='confirm-cancel-sentinel')
    for index, older, geometry in itertools.product(range(10), (False, True), ((0, 250, 1), (253, 255, 255))):
        compare(ram_for(index, older, index, *geometry), 3, profile='confirm-y-plus-row-byte-wrap')
    sequences = []
    for index, older in itertools.product((0, 7, 9), (False, True)):
        ram = ram_for(index, older, index)
        register_inputs = (0xabcdab68, 0xdead7000)
        begin = len(rows)
        for event in (5, 0, 1, 3, 5, 4, 6, 7):
            ram, register_inputs = compare(ram, event, stack=0x1feffc, profile='cpp-register-ram-carry', register_inputs=register_inputs)
        sequences.append({'row': index, 'older': older, 'frames': len(rows) - begin, 'full_ram_d1_d3_cpp_outputs_carried': True})
    negatives = []
    sentinel = b'prior-stage-group-output\0\xff'
    def reject(ram, event='5', d1='0xabcdab68', d3='0xdead7000', stack='0x1feffc', selected_font=font, selected_stages=stages, label='invalid-argument', selected_menu=native):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(selected_menu), str(selected_font), str(selected_stages), str(out), str(ports), event, d1, d3, stack], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})
    for register in ('d1', 'd3'):
        for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
            values = {'d1': '0xabcdab68', 'd3': '0xdead7000'}
            values[register] = invalid
            reject(ram_for(0, False, 0), label='invalid-' + register, **values)
    for invalid in ('-1', '65536', '0x10000', '0x', '1x', ''):
        reject(ram_for(0, False, 0), event=invalid, label='invalid-event')
    for size in (0, 65535, 65537):
        reject(bytes(size), label='invalid-ram-size')
    for bad_stack in ('0x110002', '0x1feffd', '0xffffffff'):
        reject(ram_for(0, False, 0), stack=bad_stack, label='invalid-callback-stack')
    invalid_format = folder / 'invalid-format.ms5d'
    import zlib
    data = bytearray(program[0x937e:0x9aa8])
    data[0x9786 - 0x937e] = ord('q')
    invalid_format.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0x937e, 0x937e, len(data), zlib.crc32(data), 0) + data)
    reject(ram_for(0, False, 0), selected_menu=invalid_format, label='late-unsupported-format-after-candidate-stage-writes')
    invalid_context = folder / 'invalid-context'
    invalid_context.mkdir(exist_ok=True)
    for stage_file in stages.glob('*.ms5d'):
        destination = invalid_context / stage_file.name
        destination.unlink(missing_ok=True)
        if stage_file.name != 'stage_null_name.ms5d':
            destination.symlink_to(stage_file)
    (invalid_context / 'stage_null_name.ms5d').write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0, 0, 1, zlib.crc32(b'X'), 0) + b'X')
    reject(ram_for(0, False, 0), selected_stages=invalid_context, label='invalid-null-name-context')
    for bad_row in (10, 255):
        reject(ram_for(bad_row, False, 0), label='invalid-stage-row')
    for kind in ('same', 'hardlink', 'symlink'):
        ram = ram_for(0, False, 0)
        inp.write_bytes(ram)
        ports.write_bytes(sentinel)
        alias = inp if kind == 'same' else folder / (kind + '.bin')
        if kind != 'same':
            alias.unlink(missing_ok=True)
            if kind == 'hardlink':
                alias.hardlink_to(inp)
            else:
                alias.symlink_to(inp)
        actual = subprocess.run([str(executable), str(inp), str(native), str(font), str(stages), str(alias), str(ports), '5', '0xabcdab68', '0xdead7000', '0x1feffc'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram and ports.read_bytes() == sentinel
        negatives.append({'failure': 'input-output-' + kind + '-alias', 'outputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
        'program_code_modified': False,
        'address_mapping': 'CPU address equals verified decrypted ROM offset below 0x100000.',
        'entry_cpu_address': CALLBACK, 'descriptor_cpu_address': MENU,
        'callback_cpu_address': CALLBACK, 'native_flags': 0,
        'native_menu_resource_sha256': native_hash,
        'null_name_resource_sha256': null_hash, 'font_resource_sha256': font_hash,
        'cases': len(rows), 'native_event_cases': native_cases,
        'formatted_boundary_cases': formatted_cases,
        'whole_65536_byte_ram_equal': True, 'ordered_video_ports_equal': True,
        'result_a2_full_d1_full_d3_equal': True, 'results': rows,
        'negative_cases': len(negatives), 'negative_results': negatives, 'output_carry_sequences': sequences,
        'ordered_port_events': sum(row['port_events'] for row in rows),
        'scope': 'Unmodified direct9802 with incomingA2=current as supplied by9b3e context; '
                 'stage helpers, original formatter3a70, close path and rendering helpers. '
                 'All ten rows/groups9..18, events0..7, head/current, selected/unselected '
                 'styles, coordinates/width/line and callback entry stack variation checked. '
                 'Groups9..15 consume address-zero original ROM bytes0010f300; groups16..18 '
                 'consume real first-record names. Confirmation stores group9+row, clears '
                 'area and sets sentinel1; cancellation preserves sentinel. Whole RAM, '
                 'ordered3c0000 port writes, A2 and fullD1/D3 compared. Six sequences carry actual '
                 'C++ RAM/register outputs. Outer9b3e and other CPU registers/flags, stack memory outside RAM, pixel output, natural '
                 'reachability, hardware timing and full boot remain outside scope.'
    }, indent=2) + '\n')
    print('Stage group menu original/C++ match:', len(rows), 'cases;',
          native_cases, 'native events;', formatted_cases, 'formatted boundaries')


if __name__ == '__main__':
    main()
