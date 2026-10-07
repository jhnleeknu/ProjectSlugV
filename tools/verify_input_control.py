"""Compare continuous native f12 input/controller/caller execution and MMIO."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A1, UC_M68K_REG_A5, UC_M68K_REG_A6,
    UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources

RAM_BASE, RETURN, ENTRY, CALLBACK, CONTROL, LOOP, TRAP, BIOS = (
    0x100000, 0xff000, 0xf12, 0xf3c, 0xf54, 0xec4, 0xfee, 0xc00444)
OLDEST, EMPTY = 0x107efe, 0x107f0e
PORT_ADDRESSES = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)
HOOKS = (CALLBACK, CONTROL, 0xf5a, 0x919a, 0x91c2, 0x92ce, 0x92fc, 0x9302,
         0x928e, 0x9602, 0x9802, 0x950c, 0x9532, 0x5728, 0x7196, 0x43dbc, LOOP, TRAP, BIOS)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256 or program[0x180:0x182] != b'\0\0':
        raise ValueError('Unsupported ROM or playback selector')
    streams, status_table, menu, pause, palettes, font, stages = [root / 'extracted/runtime' / name for name in
        ('input_streams.ms5d', 'input_status.ms5d', 'control_menu_tree.ms5d', 'control_pause.ms5d',
         'palettes.ms5p', 'menu_fonts.ms5d', 'stages')]
    hashes = {'streams': checked_resource(streams, program, 0xf01fe, 0xf1a0e),
        'status': checked_resource(status_table, program, 0xb58, 0xc58),
        'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
        'pause': checked_resource(pause, program, 0x9068, 0x9086),
        'font': checked_resource(font, program, 0xe80c8, 0xe84c8),
        'null_name': checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)}
    groups = verify_resources(stages, program, source)
    records, _ = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] +
                       records[identifier][1] for identifier in sorted(records))
    packed = palettes.read_bytes()
    if packed != struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload),
                              zlib.crc32(payload), 0, 0) + payload:
        raise ValueError('Palette resource differs from verified native source')
    hashes['palettes'] = hashlib.sha256(packed).hexdigest()
    executable = root / 'build/step_input_control'
    if not executable.exists():
        raise ValueError('Build build/step_input_control first')
    folder = root / 'artifacts/input_control'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, port_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    # This bank mapping already covers all input/video MMIO addresses.
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(RAM_BASE, bytes(65536))
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
        raise ValueError('Native allocator initialization failed')
    initial = bytes(cpu.mem_read(RAM_BASE, 65536))
    samples, reads, writes, trace = [], [], [], []
    rows, sequences, negatives = [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address not in PORT_ADDRESSES:
            return
        ordinal = len(reads)
        if ordinal >= len(samples) or address != PORT_ADDRESSES[ordinal] or size != 1:
            raise ValueError('Native MMIO read order/width differs')
        cpu.mem_write(address, bytes((samples[ordinal],)))
        reads.append((address, samples[ordinal]))

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010 or address in (0x2ffff0, 0x2ffff2):
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        trace.append({'address': address, 'a1': cpu.reg_read(UC_M68K_REG_A1),
            'a6': cpu.reg_read(UC_M68K_REG_A6), 'a7': cpu.reg_read(UC_M68K_REG_A7),
            'd0': cpu.reg_read(UC_M68K_REG_D0), 'd3': cpu.reg_read(UC_M68K_REG_D3), 'd1_word': cpu.reg_read(UC_M68K_REG_D1) & 65535})
        if address in (CALLBACK, LOOP, TRAP, BIOS):
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x300000, end=0x380000)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in HOOKS:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(active=0, pending=0, mode=0, palette_pending=0, callback=0):
        ram = bytearray(initial)
        ram[0x5da2:0x7da2] = hashlib.shake_256(b'ms5-input-control-v1:' +
            len(rows).to_bytes(4, 'big')).digest(8192)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14] = slot & 31
            ram[node + 15] = (slot & 3) | (0x80 if slot % 7 == 0 else 0)
        ram[0x7df0], ram[0x7df1], ram[0x4cd4], ram[0x7ded] = active, pending, mode, palette_pending
        ram[0xfdaf], ram[0xf000], ram[0xf002] = 2, 2, 1
        ram[0xfdb6:0xfdba] = b'\1\1\1\1'
        ram[0xfd94], ram[0xfd9a] = 0xa5, 0x5a
        ram[0x4cd2], ram[0x4cd3] = 15, 4
        struct.pack_into('>I', ram, 0x4cc4, 0xf01fe)
        struct.pack_into('>H', ram, 0x4cc2, 0x1234)
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        struct.pack_into('>H', ram, 0x000e, 0xffff)
        struct.pack_into('>H', ram, 0x0f5c + 0x7e, 0xffff)
        ram[0x0f5c + 0x84] = 1
        struct.pack_into('>II', ram, 0x0f5c + 0x76, callback, 0xdeadbeef)
        return ram

    def menu_fixture(mode=0, height=12, selected=0, exit_word=0):
        ram = fixture(active=3)
        ram[0x7dee] = 255
        struct.pack_into('>III', ram, 0x7f0e, OLDEST, OLDEST, 0x9332)
        struct.pack_into('>H', ram, 0x7dfa, exit_word)
        struct.pack_into('>I', ram, 0x7efe, 0x93e0)
        ram[0x7f02:0x7f0e] = bytes((height, 0, 6, selected, selected, 4, 8, 24, 12, 3, 255, 0))
        ram[0x7f1b] = mode
        return ram

    def arguments(style, line, stack, current_samples, table_input=status_table):
        return ([str(executable), str(inp), str(streams), str(table_input), str(menu), str(pause),
            str(palettes), str(out), str(port_out), str(0x100f5c), str(style), str(line), str(stack)] +
            [str(value) for value in current_samples] + [str(font), str(stages)])

    def compare(ram, current_samples, profile, style=0xff6b, line=0xffff, stack=0x1feffc, sequence=None):
        samples[:] = current_samples[:5 if ram[0x4cd4] == 0 else 3]
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, 0x100f5c), (UC_M68K_REG_A7, stack),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, 0xbeef0000 | style),
                (UC_M68K_REG_D3, 0xcafe0000 | line), (UC_M68K_REG_A1, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        reads.clear()
        writes.clear()
        trace.clear()
        try:
            cpu.emu_start(ENTRY, RETURN, count=12000000)
        except unicorn.UcError as error:
            raise ValueError('Native continuous chain exception: ' + repr((len(rows), profile,
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (RETURN, CALLBACK, LOOP, TRAP, BIOS) or len(reads) != len(samples):
            raise ValueError('Native chain failed boundary/read-count assertion')
        prefix = [item for item in trace if item['address'] in (CONTROL, CALLBACK)]
        if len(prefix) != 1 or prefix[0]['a1'] != 0xb58 or prefix[0]['a6'] != 0x100f5c or prefix[0]['a7'] != stack:
            raise ValueError('Native prefix context at controller/callback boundary differs: ' + repr(prefix))
        if prefix[0]['d3'] != 0xcafe0000 | line:
            raise ValueError('Native input prefix changed incoming fullD3')
        consumed = [item for item in trace if item['address'] == 0xf5a]
        if any(item['a6'] != 0x100f5c or item['a7'] != stack for item in consumed):
            raise ValueError('Native controller failed caller A6/stack preservation')
        if pc in (CALLBACK, BIOS) and consumed:
            raise ValueError('Callback/BIOS bypass unexpectedly ran caller consumer')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        callback = struct.unpack_from('>I', expected, 0x0f5c + 0x76)[0] if pc == CALLBACK else 0
        context = struct.unpack_from('>I', expected, 0x0f5c + 0x7a)[0] if callback else 0
        expected_result = {'next_pc': 0 if pc == RETURN else pc, 'callback': callback,
            'callback_context': context, 'style': prefix[0]['d1_word'], 'read_count': len(samples)}
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(ram)
        for path in (out, port_out):
            path.unlink(missing_ok=True)
        result = subprocess.run(arguments(style, line, stack, current_samples), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ chain rejected: ' + repr((len(rows), profile, result.stderr)))
        actual, actual_ports, parsed = out.read_bytes(), port_out.read_bytes(), json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            port_difference = next(((at//9, expected_ports[at:at+9].hex(), actual_ports[at:at+9].hex())
                for at in range(0, max(len(expected_ports), len(actual_ports)), 9)
                if expected_ports[at:at+9] != actual_ports[at:at+9]), None)
            raise ValueError('Continuous input/controller mismatch: ' + repr((len(rows), profile,
                sequence, differences[:20], port_difference, expected_result, parsed, trace)))
        rows.append({'profile': profile, 'sequence': sequence, 'initial_mode': ram[0x4cd4],
            'initial_active': ram[0x7df0], 'initial_menu_active': ram[0x7dee],
            'initial_style': style, 'initial_line': line, 'entry_stack': stack,
            'samples': current_samples, 'actual_reads': reads.copy(), 'actual_trace': trace.copy(),
            'result': parsed, 'port_events': len(writes),
            'input_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), parsed['style']

    for pending, system, input_mode, palette_pending in itertools.product((0, 1, 3),
            (255, 253, 247, 245), (0, 1, 2), (0, 128)):
        ram = fixture(pending=pending, mode=input_mode, palette_pending=palette_pending)
        compare(ram, [system, 255, 255, 0x55, 0xaa], 'inactive-sampled-activation-idle')
    for active, buttons, repeat in itertools.product((1, 2, 3), (0, 1, 2, 4, 8), (0, 1, 15)):
        ram = fixture(active=active, palette_pending=(len(rows) % 2) * 128)
        ram[0x7df2] = repeat
        compare(ram, [buttons ^ 255, 255, 255, 255, 255], 'sampled-wait-repeat-step-menu-start')
    for mode, height, exit_word, style in itertools.product((0, 1, 2), (0, 12), (0, 1), (0, 0x0603, 0xff6b)):
        ram = menu_fixture(mode, height, exit_word=exit_word)
        compare(ram, [255] * 5, 'sampled-active-menu-open-close', style=style)
    for input_mode, callback, style in itertools.product((0, 1, 2, 255), (0, 1, 0xdeadbeef), (0, 0x0603, 0xff6b)):
        ram = fixture(mode=input_mode, callback=callback)
        compare(ram, [0xf0, 0x55, 0xaa, 0x81, 0x42], 'prefix-callback-bypass-style')
    for selected in (4, 5):
        ram = menu_fixture(selected=selected)
        ram[0x7f0c] = 3
        struct.pack_into('>H', ram, 0x8e4 + 0x10, 0)
        ram[0x8e4 + 0x1d], ram[0x8e4 + 0x6c] = 0, 255
        compare(ram, [255] * 5, 'static-restart-or-bios')
    ram = fixture(active=1)
    ram[0x000f] ^= 1
    compare(ram, [254, 255, 255, 255, 255], 'sampled-step-counter-trap')
    isolated = len(rows)

    for child, palette_pending, stack in ((2, 0, 0x1feffc), (3, 128, 0x1f8000)):
        ram, style = fixture(palette_pending=palette_pending), 0xff6b
        label, begin = 'sampled-carried-child-%d-pending-%d' % (child, palette_pending), len(rows)

        def tick(system_buttons=0, player_buttons=0):
            nonlocal ram, style
            current_samples = [system_buttons ^ 255, player_buttons ^ 255, 255,
                               player_buttons ^ 255, 255]
            ram, style = compare(ram, current_samples, 'continuous-whole-ram-and-prefix-style-carry',
                                 style, 0xffff, stack, label)

        def press(system_buttons=0, player_buttons=0):
            tick(system_buttons, player_buttons)
            tick()

        def open_menu():
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big') - RAM_BASE
                if ram[0x7f1b] == 0 and ram[head + 4] >= ram[head + 12]:
                    return
            raise ValueError('Sampled carried menu failed to open')

        press(system_buttons=2)
        if not ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Sampled native activation failed')
        for _ in range(20):
            tick(system_buttons=1)
        tick()
        press(system_buttons=2)
        open_menu()
        for _ in range(child):
            press(player_buttons=2)
        press(player_buttons=16)
        head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
        descriptor = int.from_bytes(ram[head - RAM_BASE:head - RAM_BASE + 4], 'big')
        if head != OLDEST - 16 or descriptor != (0x958a, 0x978a)[child - 2]:
            raise ValueError('Sampled raw button selection failed stage child push')
        open_menu()
        for buttons in (2, 4, 8, 16):
            press(player_buttons=buttons)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]:
                break
        else:
            raise ValueError('Sampled stage choice failed full close')
        tick()
        press(system_buttons=2)
        if not ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Sampled whole-chain reactivation failed')
        press(system_buttons=2)
        open_menu()
        press(system_buttons=2)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]:
                break
        else:
            raise ValueError('Sampled reactivation failed second full close')
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'full_exit_resume_reactivation_asserted': True})

    ram = fixture()
    struct.pack_into('>HH', ram, 0x4d92 + 10, 0xfffe, 0xfffe)
    ram[0x4d92 + 15] = 0x80
    inp.write_bytes(ram)
    for existing in (False, True):
        sentinels = (b'previous-integrated-ram', b'previous-integrated-ports')
        for path, sentinel in zip((out, port_out), sentinels):
            if existing:
                path.write_bytes(sentinel)
            else:
                path.unlink(missing_ok=True)
        result = subprocess.run(arguments(0xff6b, 0xffff, 0x1feffc, [253, 255, 255, 255, 255]),
                                capture_output=True, text=True)
        if result.returncode == 0:
            raise ValueError('Late integrated palette lookup accepted missing ID')
        for path, sentinel in zip((out, port_out), sentinels):
            if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                    not existing and path.exists()):
                raise ValueError('Late input/controller failure published outputs')
        negatives.append({'failure': 'late-palette-after-input-and-activation', 'existing_outputs': existing,
            'outputs_preserved': True, 'stderr': result.stderr.strip(), 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original fixed ROM changed')
    if bytes(cpu.mem_read(0x200000, 0xffff0)) != program[0x200000:0x2ffff0]:
        raise ValueError('Original palette ROM bank changed outside PVC tail')
    hook_counts = {hex(address): sum(item['address'] == address for row in rows
                   for item in row['actual_trace']) for address in HOOKS}
    if not all(hook_counts.values()):
        raise ValueError('Integrated native helper/boundary coverage missing: ' + repr(hook_counts))
    stage_stack_deltas = {row['entry_stack'] - item['a7'] for row in rows
        for item in row['actual_trace'] if item['address'] in (0x9602, 0x9802)}
    if stage_stack_deltas != {12, 16, 32}:
        raise ValueError('Stage callback stack lost real outer controller return: ' + repr(stage_stack_deltas))
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'address_mapping': 'Fixed CPU addresses equal decrypted '
            'ROM offsets; palette bank CPU200000..2ffff0 maps same source offsets.',
        'native_resource_sha256': hashes, 'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'isolated_cases': isolated, 'actual_hook_counts': hook_counts,
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_pvc_ports_equal': True,
        'prefix_style_callback_context_read_count_and_next_pc_equal': True,
        'continuous_native_execution_no_register_reset_at_f54': True,
        'native_a1_b58_at_f54_and_f3c_asserted': True,
        'native_full_d3_preserved_by_input_prefix_asserted': True,
        'actual_stage_callback_stack_deltas': sorted(stage_stack_deltas),
        'actual_stage_outer_return_depth_asserted': True,
        'native_caller_a6_and_stack_preservation_asserted': True,
        'actual_mmio_read_order_asserted': True, 'callback_and_bios_skip_consumer_asserted': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'late_palette_failure_outputs_preserved': True,
        'ordered_port_events': sum(row['port_events'] for row in rows), 'results': rows,
        'scope': 'Continuous unmodifiedf12 input prefix, native31d6/b68, native9136 controller '
            'and f5a caller helpers without register reset atf54. Stop atf3c external callback '
            'before execution, ec4 loop, fee TRAP15 before execution, BIOS transfer or normal '
            'RTS. Original A1=b58 fromstatus table reaches controller unchanged; reported '
            'style is exact prefixD1, not final controllerD1. Supplied active-low raw buttons '
            'with press/release drive activation/wait/repeat/menu/stage choices/fullclose '
            'and reactivation with wholeRAM/style carry. Physical input timing, external '
            'callbacks, ec4 loop acquisition, trap handler and full boot excluded.'}, indent=2) + '\n')
    print('Continuous sampled input/control original/C++ match:', len(rows), 'cases;',
          len(sequences), 'sampled carried lifecycles;', len(negatives), 'late failures;', hook_counts)


if __name__ == '__main__':
    main()
