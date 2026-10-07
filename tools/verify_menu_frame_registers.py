"""Compare native a370 RAM, ports and full D1/D3 against C++ frames."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5, UC_M68K_REG_A7,
                               UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call as call_palette_helper
from verify_stage_catalog import COUNTS, SOURCE_SHA256, checked_resource, verify_resources

MENUS = (0x93e0, 0x958a, 0x978a, 0x99ee)
COUNTS_MENU = (6, 10, 10, 15)
CALLBACKS = (0x9488, 0x94d6, 0x949a, 0x94b8, 0x950c, 0x9532,
             0x9602, 0x9802, 0x9aa8)
RAM_BASE, OLDEST, EMPTY, RETURN = 0x100000, 0x107efe, 0x107f0e, 0xff000
BIOS = 0xc00444


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    stages = root / 'extracted/runtime/stages'
    groups = verify_resources(stages, program, source)
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    null_hash = checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)
    executable = root / 'build/step_menu_frame'
    if not executable.exists():
        raise ValueError('Build build/step_menu_frame before verification')
    folder = root / 'artifacts/menu_frame_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    cpu.mem_write(RAM_BASE, bytes(65536))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    call_palette_helper(cpu, 0x3ef2)
    palette_ram = bytes(cpu.mem_read(RAM_BASE, 65536))
    writes, calls, trace, rows = [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (RAM_BASE <= address and address + size <= 0x110000) and not (0x1f7000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))

    def code_hook(cpu, address, size, user):
        if address in (BIOS, RETURN):
            cpu.emu_stop()
        elif address in CALLBACKS:
            calls.append({'address': address, 'event': cpu.reg_read(UC_M68K_REG_D0) & 65535,
                          'a7': cpu.reg_read(UC_M68K_REG_A7)})
        else:
            trace.append({'address': address, 'a7': cpu.reg_read(UC_M68K_REG_A7),
                          'current': int.from_bytes(cpu.mem_read(0x107f12, 4), 'big')})

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in CALLBACKS + (BIOS, RETURN, 0x9430, 0xa6da, 0x9b58, 0x9e1a):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def original(ram, entry, line, stack, init=False, registers=None):
        d1, d3 = registers if registers is not None else (8 if init else 0xbeefaaaa, line)
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_D0, 4 if init else 0x12345678),
                           (UC_M68K_REG_D1, d1),
                           (UC_M68K_REG_D3, d3), (UC_M68K_REG_A7, stack),
                           (UC_M68K_REG_A0, 0x93e0),
                           (UC_M68K_REG_A1, int.from_bytes(ram[0x7f16:0x7f1a], 'big'))):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        writes.clear()
        calls.clear()
        trace.clear()
        try:
            cpu.emu_start(entry, RETURN, count=8000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), hex(entry),
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (RETURN, BIOS):
            raise ValueError('Original did not reach return or BIOS boundary: ' + hex(pc))
        result = {'status': 0 if pc == BIOS else
                  struct.unpack('>i', struct.pack('>I', cpu.reg_read(UC_M68K_REG_D0)))[0],
                  'external_jump': BIOS if pc == BIOS else 0,
                  'line': cpu.reg_read(UC_M68K_REG_D3) & 65535,
                  'd1': cpu.reg_read(UC_M68K_REG_D1) & 0xffffffff,
                  'd3': cpu.reg_read(UC_M68K_REG_D3) & 0xffffffff}
        return bytes(cpu.mem_read(RAM_BASE, 65536)), b''.join(
            struct.pack('>BII', *write) for write in writes), result

    def fixture(menu, depth=1, mode=0, height=None, selected=None, pending=255,
                flags=0, inputs=(0, 0), enable=3, sentinel=0):
        ram = bytearray(hashlib.shake_256(b'ms5-menu-frame-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        head = OLDEST - 16 * (depth - 1)
        if height is None:
            height = 17 if menu == 0x99ee else 12
        struct.pack_into('>III', ram, 0x7f0e, head, head, 0x3650)
        struct.pack_into('>H', ram, 0x7dfa, sentinel)
        ram[0x7df0] = 0
        ram[0x7dfe] = len(rows) % 8
        for group in range(8):
            ram[0x7dff + group] = COUNTS[group] - 1
        ram[0x7f1b] = mode
        ram[0x4cba], ram[0x4cc0] = inputs
        struct.pack_into('>H', ram, 0xf000, 0xaaaa)
        # Header request selector inputs are deterministic, with no exit request.
        ram[0x12] = 2
        ram[0xfd82] = 0
        ram[0xfdb6] = ram[0xfdb7] = 1
        ram[0x4cb5] = 0
        for index in range(depth):
            slot = OLDEST - 16 * index
            at = slot - RAM_BASE
            descriptor = menu if index == depth - 1 else (0x93e0, 0x958a)[index % 2]
            count = COUNTS_MENU[MENUS.index(descriptor)]
            choice = 2 if descriptor == 0x958a else 0
            if index == depth - 1 and selected is not None:
                choice = selected
            struct.pack_into('>I', ram, at, descriptor)
            ram[at + 4] = height if index == depth - 1 else 12
            ram[at + 5] = 0
            ram[at + 6:at + 16] = bytes((count, choice, choice, 4 + index * 3,
                8 + index, 24, 17 if descriptor == 0x99ee else 12,
                enable, pending if index == depth - 1 else 255,
                flags if index == depth - 1 else 0))
        return ram

    def compare(ram, profile, line=0x7000, stack=0x1feffc, sequence=None, register_inputs=None):
        registers = register_inputs if register_inputs is not None else (((len(rows)*0x1234567)^0xabcdab68)&0xffffffff, (((len(rows)*0x7341)^0xdead)&65535)<<16|line)
        line = registers[1] & 65535
        expected, expected_ports, expected_result = original(ram, 0xa370, line, stack, registers=registers)
        observed_calls, observed_trace = calls.copy(), trace.copy()
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), '--registers', str(registers[0]), str(registers[1]), str(inp), str(native), str(out), str(ports),
            str(line), str(stack), str(font), str(stages)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        parsed = json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at])
                for at in range(min(len(actual), 65536)) if actual[at] != expected[at]]
            port_difference = next((at for at in range(min(len(actual_ports), len(expected_ports)))
                if actual_ports[at] != expected_ports[at]), None)
            raise ValueError('Frame mismatch: ' + repr((len(rows), profile, sequence,
                differences[:20], len(expected_ports)//9, len(actual_ports)//9,
                port_difference, expected_result, parsed, observed_calls)))
        head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
        slot = head - RAM_BASE
        rows.append({'profile': profile, 'sequence': sequence, 'head': head,
            'menu': int.from_bytes(ram[slot:slot+4], 'big') if head < EMPTY else None,
            'renderer': int.from_bytes(ram[0x7f16:0x7f1a], 'big'),
            'watchdog_events': sum(write[1] == 0x300001 for write in writes),
            'mode': ram[0x7f1b], 'height': ram[slot+4] if head < EMPTY else None,
            'pending': ram[slot+14] if head < EMPTY else None,
            'inputs': [ram[0x4cba], ram[0x4cc0]], 'initial_line': line, 'incoming_d1': registers[0], 'incoming_d3': registers[1],
            'entry_stack': stack, 'result': parsed, 'port_events': len(expected_ports)//9,
            'actual_callbacks': observed_calls, 'actual_draw_header_redraw_trace': observed_trace,
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(actual), (parsed['d1'], parsed['d3'])

    for menu, depth in itertools.product(MENUS, (1, 2, 3)):
        target = 17 if menu == 0x99ee else 12
        for mode, height in itertools.product((0, 1), (0, 2, target - 1, target)):
            compare(fixture(menu, depth, mode, height), 'open-and-complete')
        for event in range(8):
            compare(fixture(menu, depth, pending=event), 'active-pending')
        for enable, first, second in ((0, 255, 255), (1, 1, 2), (2, 1, 2), (3, 1, 2),
            (3, 2, 1), (3, 4, 8), (3, 8, 4), (3, 16, 32), (3, 32, 16),
            (1, 0, 255), (2, 255, 0), (255, 128, 64)):
            compare(fixture(menu, depth, inputs=(first, second), enable=enable),
                    'active-input-enable-priority')
        for height, sentinel in itertools.product((0, 1, 2, target), (0, 1)):
            compare(fixture(menu, depth, 2, height, sentinel=sentinel), 'close-pop-return')
        compare(fixture(menu, depth, flags=1), 'active-flag-redraw')
        for mode in (3, 255):
            compare(fixture(menu, depth, mode), 'invalid-mode-status')
    isolated = len(rows)
    for depth, height in itertools.product((2, 3), (0, 1, 2)):
        ram = fixture(0x958a, depth)
        ram[0x7f0d] = 1
        ram[0x7f02] = height
        compare(ram, 'background-slot-close-helper', stack=0x1f8000, line=0x74ff)
    for height in (1, 2):
        ram = fixture(0x958a, 3)
        # Closing a middle slot redraws older visible stage rows while the
        # newest slot remains active. Separate X coordinates avoid occlusion.
        struct.pack_into('>I', ram, 0x7efe, 0x958a)
        ram[0x7f04:0x7f07] = bytes((10, 2, 2))
        struct.pack_into('>I', ram, 0x7eee, 0x99ee)
        ram[0x7ef2] = height
        ram[0x7ef3] = 0xff
        ram[0x7ef4:0x7ef7] = bytes((15, 0, 0))
        ram[0x7efd] = 1
        ram[0x7ee7] = 100
        compare(ram, 'background-middle-close-stage-redraw')
    for mode in (0, 1, 2, 3, 255):
        ram = fixture(0x93e0)
        struct.pack_into('>I', ram, 0x7f0e, EMPTY)
        ram[0x7f1b] = mode
        compare(ram, 'empty-stack')
    for menu, mode, height, flags in itertools.product(MENUS, (0, 1), (2, 17), (0, 1)):
        ram = fixture(menu, 2, mode, height, flags=flags)
        struct.pack_into('>I', ram, 0x7f16, 0x9332)
        compare(ram, 'renderer9332-frame-paths')
    for menu, line, stack in itertools.product((0x958a, 0x978a),
            (0, 0x74ff, 0xffff), (0x1feffc, 0x1f8000)):
        ram = fixture(menu, 3, flags=1, selected=9, sentinel=0xffff)
        head = int.from_bytes(ram[0x7f0e:0x7f12], 'big') - RAM_BASE
        ram[head + 9:head + 12] = bytes((255, 255, 2))
        ram[0x7dfe] = 7
        ram[0x7dff:0x7e07] = bytes([255] * 8)
        compare(ram, 'stage-coordinate-line-stack-area-boundaries', line, stack)
    for selected in (1, 2, 3, 5):
        compare(fixture(0x93e0, selected=selected, pending=3), 'root-confirm-child-or-bios')
    for pending in (255, 3, 4):
        ram = fixture(0x93e0, pending=pending)
        ram[0x7df0] = 1
        ram[0x4cb5] = 2
        compare(ram, 'header-exit-still-processes-pending')
    ram = fixture(0x93e0, inputs=(2, 0))
    ram[0x7df0] = 1
    ram[0x4cb5] = 2
    compare(ram, 'header-exit-still-processes-input')
    for depth, pending, renderer in ((1, 3, 0x3650), (2, 255, 0x3650), (1, 3, 0x9332)):
        ram = fixture(0x93e0, depth, selected=4, pending=pending,
                      inputs=(16, 0) if pending == 255 else (0, 0))
        # Reuse the validated static-object restart preconditions from
        # verify_menu_event: original allocator3ef2, no palette owner or
        # coordinate link, and object+10 word0 for the static path.
        ram[0x4d92:0x5da2] = palette_ram[0x4d92:0x5da2]
        struct.pack_into('>H', ram, 0x8e4 + 0x10, 0)
        ram[0x8e4 + 0x1d] = 0
        ram[0x8e4 + 0x6c] = 255
        struct.pack_into('>I', ram, 0x7f16, renderer)
        compare(ram, 'initialized-static-object-restart')

    # Each sequence starts from original a29c and C++ init_menu, then carries
    # CLI RAM/full D1/D3 outputs into every subsequent frame comparison.
    initialized_sequences = []
    for (child, confirm), renderer in itertools.product(
            ((1, False), (2, False), (3, False), (2, True), (3, True)), (0x3650, 0x9332)):
        ram = bytearray(65536)
        expected, _, _ = original(ram, 0xa29c, 0x7000, 0x1feffc, init=True)
        inp.write_bytes(ram)
        subprocess.run([str(root / 'build/init_menu'), str(inp), str(native), str(out),
            str(0x93e0), '4', '8', str(0x7000)], check=True, capture_output=True)
        if out.read_bytes() != expected:
            raise ValueError('Sequence initialization differs')
        ram, registers = bytearray(out.read_bytes()), (0xabcdab68, 0xdead7000)
        struct.pack_into('>I', ram, 0x7f16, renderer)
        label = ('initialized-root-child-' + str(child) +
                 ('-confirm' if confirm else '-cancel') + '-renderer-' + hex(renderer))
        start = len(rows)

        def tick(first=0, second=0):
            nonlocal ram, registers
            ram[0x4cba], ram[0x4cc0] = first, second
            ram, registers = compare(ram, 'initialized-multiframe', sequence=label, register_inputs=registers)

        def open_menu():
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big') - RAM_BASE
                if ram[0x7f1b] == 0 and ram[head+4] >= ram[head+12]:
                    return
            raise ValueError('Initialized menu did not open')

        open_menu()
        for _ in range(child):
            tick(2)
        tick(16)
        new_head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
        child_menu = (0x99ee, 0x958a, 0x978a)[child - 1]
        if new_head != OLDEST - 16 or int.from_bytes(
                ram[new_head - RAM_BASE:new_head - RAM_BASE + 4], 'big') != child_menu:
            raise ValueError('Initialized confirmation did not push expected native child')
        open_menu()
        tick(2)
        tick(4)
        tick(8)
        # Confirm stage children exercises sentinel1 and parent event7 close
        # propagation; cancellation returns to the parent for a separate close.
        tick(16 if confirm else 32)
        if confirm and ram[0x7dfa:0x7dfc] != b'\x00\x01':
            raise ValueError('Stage confirmation did not set sentinel1')
        def close_to(target):
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
                if head == target and (target == EMPTY or ram[0x7f1b] == 0):
                    return
            raise ValueError('Initialized menu did not close to expected stack')

        close_to(EMPTY if confirm else OLDEST)
        if not confirm:
            tick(32)
            close_to(EMPTY)
        if int.from_bytes(ram[0x7f0e:0x7f12], 'big') != EMPTY:
            raise ValueError('Initialized sequence did not empty menu stack')
        initialized_sequences.append({'label': label, 'frames': len(rows) - start,
                                      'final_head': EMPTY, 'cpp_ram_full_d1_d3_outputs_carried': True, 'initial_registers_are_explicit_frame_boundary_fixtures': True})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    actual_stage_calls = [call for row in rows for call in row['actual_callbacks']
                          if call['address'] in (0x9602, 0x9802)]
    if not actual_stage_calls:
        raise ValueError('Actual stage callback coverage missing')
    expected_paths = {
        'open-and-complete': {0: {4}, 5: {24}, 6: {4}},
        'active-flag-redraw': {5: {28}},
        'active-input-enable-priority': {0: {8}, 1: {8}, 4: {8}, 5: {24}},
        'active-pending': {event: ({8, 28} if event == 5 else {8}) for event in range(8)},
        'close-pop-return': {0: {4}, 5: {32}, 7: {8}},
        'background-middle-close-stage-redraw': {5: {36}},
    }
    for profile, events in expected_paths.items():
        for event, deltas in events.items():
            observed = {row['entry_stack'] - call['a7'] for row in rows
                        if row['profile'] == profile for call in row['actual_callbacks']
                        if call['address'] in (0x9602, 0x9802) and call['event'] == event}
            if observed != deltas:
                raise ValueError('Original stage callback stack path coverage changed: ' +
                                 repr((profile, event, deltas, observed)))
    if sum(row['watchdog_events'] for row in rows) != 3:
        raise ValueError('Original static restart watchdog coverage changed')
    negatives = []
    sentinel = b'prior-menu-frame-output\0\xff'
    def arguments(d1='0xabcdab68', d3='0xdead7000', line='0x7000'):
        return [str(executable), '--registers', d1, d3, str(inp), str(native), str(out), str(ports), line, str(0x1feffc), str(font), str(stages)]
    def reject(label, ram, command=None):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        actual = subprocess.run(command or arguments(), capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'profile': label, 'outputs_preserved': True, 'original_executed': False})
    for register in (2, 3):
        for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
            command = arguments()
            command[register] = invalid
            reject('invalid-register', fixture(0x93e0), command)
    for invalid in ('-1', '65536', '0x10000', '0x', '1x', ''):
        reject('invalid-line', fixture(0x93e0), arguments(line=invalid))
    reject('inconsistent-line', fixture(0x93e0), arguments(line='0x7001'))
    for size in (0, 65535, 65537):
        reject('invalid-ram-size', bytes(size))
    ram = fixture(0x93e0, selected=4, pending=3)
    ram[0x4d92:0x5da2] = palette_ram[0x4d92:0x5da2]
    struct.pack_into('>H', ram, 0x8f4, 1)
    ram[0x901] = 0
    ram[0x950] = 255
    reject('late-invalid-restart-type', ram)
    for bad_stack in ('0x110002', '0x1feffd', '0xffffffff'):
        command = arguments()
        command[9] = bad_stack
        reject('invalid-entry-stack', fixture(0x93e0), command)
    for kind in ('same', 'hardlink', 'symlink'):
        ram = fixture(0x93e0)
        inp.write_bytes(ram)
        ports.write_bytes(sentinel)
        alias = inp if kind == 'same' else folder / (kind + '.bin')
        if kind != 'same':
            alias.unlink(missing_ok=True)
            if kind == 'hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command = arguments()
        command[6] = str(alias)
        actual = subprocess.run(command, capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram and ports.read_bytes() == sentinel
        negatives.append({'profile': 'input-output-' + kind + '-alias', 'outputs_preserved': True, 'original_executed': False})
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_address': 0xa370, 'entry_rom_offset': 0xa370,
        'address_mapping': 'CPU address equals decrypted ROM offset below 0x100000.',
        'native_menu_resource_sha256': native_hash, 'font_resource_sha256': font_hash,
        'null_name_resource_sha256': null_hash,
        'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'native_isolated_cases': isolated,
        'initialized_sequences': initialized_sequences,
        'palette_allocator_fixture_entry_cpu_address': 0x3ef2,
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_ports_equal': True,
        'signed_d0_status_full_d1_full_d3_line_equal': True, 'negative_cases': len(negatives), 'negative_results': negatives, 'ordered_port_events': sum(row['port_events'] for row in rows), 'external_jump_equal': True,
        'initial_a1_contract': 'A1 equals global renderer107f16 on frame entry.',
        'actual_stage_callback_stack_path_coverage_asserted': True,
        'actual_stage_callback_calls': len(actual_stage_calls),
        'actual_watchdog_port_events': sum(row['watchdog_events'] for row in rows),
        'observed_stage_callback_stack_deltas_by_profile_event': {
            profile: {str(event): sorted({row['entry_stack'] - call['a7']
                for row in rows if row['profile'] == profile
                for call in row['actual_callbacks']
                if call['address'] in (0x9602, 0x9802) and call['event'] == event})
                for event in range(8)}
            for profile in sorted({row['profile'] for row in rows})},
        'results': rows,
        'scope': 'Unmodified a370 and actual nested helpers/callbacks for native root93e0, '
            'area958a, group978a, debug99ee. Open/complete, active pending0..7, input enable '
            'and priority, header exit continuation, close/pop/event7/event0/redraw, background '
            'slot close, global renderer3650/9332, empty/invalid mode and initialized multiframe root/child/return cycles. '
            'Every original stage callback event and A7 recorded. BIOS c00444 stops before '
            'execution; host transition status0 is diagnostic, not BIOS behavior. Static restart '
            'row4/event3 uses original allocator initialization and no coordinate/palette owner. Linked-object restart, remaining descriptors/flags, CPU registers other than D1/D3, flags, external CPU-stack '
            'memory, natural input collection, pixels, hardware timing and full boot excluded. Initialized sequence RAM is verified from init_menu, whose CLI does not expose full register outputs: initial D1/D3 are explicit a370 boundary fixtures. Subsequent frames carry exclusively CLI RAM/full-register outputs.'
        }, indent=2) + '\n')
    print('Menu frame original/C++ match:', len(rows), 'frames;', len(actual_stage_calls),
          'actual stage callbacks;', sum(row['port_events'] for row in rows), 'ordered port events')


if __name__ == '__main__':
    main()
