"""Compare the unmodified f54 controller/caller chain and carried lifecycles."""
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
    UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
    UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources

RAM_BASE, RETURN, ENTRY, LOOP, TRAP, BIOS = 0x100000, 0xff000, 0xf54, 0xec4, 0xfee, 0xc00444
OLDEST, EMPTY = 0x107efe, 0x107f0e
HOOKS = (0xf5a, 0x919a, 0x91c2, 0x92ce, 0x92fc, 0x9302, 0x928e,
         0x9602, 0x9802, 0x950c, 0x9532, 0x5728, 0x7196, 0x43dbc, LOOP, TRAP, BIOS)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    menu, pause, font, stages, palettes = [root / 'extracted/runtime' / name for name in
        ('control_menu_tree.ms5d', 'control_pause.ms5d', 'menu_fonts.ms5d', 'stages', 'palettes.ms5p')]
    hashes = {'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
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
    executable = root / 'build/step_control_caller'
    if not executable.exists():
        raise ValueError('Build build/step_control_caller first')
    folder = root / 'artifacts/control_caller_step'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 0x1000)
    cpu.mem_write(RAM_BASE, bytes(65536))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
        raise ValueError('Native allocator initialization failed')
    initial = bytes(cpu.mem_read(RAM_BASE, 65536))
    writes, trace, rows, sequences, negatives = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if (address == 0x300001 or 0x3c0000 <= address < 0x3c0010 or
                address in (0x2ffff0, 0x2ffff2)):
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        trace.append({'address': address, 'a6': cpu.reg_read(UC_M68K_REG_A6),
                      'a7': cpu.reg_read(UC_M68K_REG_A7), 'd0': cpu.reg_read(UC_M68K_REG_D0)})
        if address in (LOOP, TRAP, BIOS):
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in HOOKS:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(address=0x100f5c, active=0, pending=0, request=0, palette_pending=0):
        ram = bytearray(initial)
        ram[0x5da2:0x7da2] = hashlib.shake_256(b'ms5-caller-step-v1:' +
            len(rows).to_bytes(4, 'big')).digest(8192)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14] = slot & 31
            ram[node + 15] = (slot & 3) | (0x80 if slot % 7 == 0 else 0)
        ram[0x7df0], ram[0x7df1], ram[0x7dee] = active, pending, 0
        ram[0x12], ram[0xfd82], ram[0xf000], ram[0xf002] = 2, 0, 2, 1
        ram[0xfdb6] = ram[0xfdb7] = 1
        ram[0x4cb5], ram[0x7ded] = request, palette_pending
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        struct.pack_into('>H', ram, address - RAM_BASE + 0x7e, 0xffff)
        struct.pack_into('>H', ram, 0x000e, 0xffff)
        ram[address - RAM_BASE + 0x84] = 1
        return ram

    def menu_fixture(address=0x100f5c, mode=0, height=12, selected=0, exit_word=0):
        ram = fixture(address, active=3)
        ram[0x7dee] = 255
        struct.pack_into('>III', ram, 0x7f0e, OLDEST, OLDEST, 0x9332)
        struct.pack_into('>H', ram, 0x7dfa, exit_word)
        struct.pack_into('>I', ram, 0x7efe, 0x93e0)
        ram[0x7f02:0x7f0e] = bytes((height, 0, 6, selected, selected, 4, 8, 24, 12, 3, 255, 0))
        ram[0x7f1b] = mode
        return ram

    def arguments(address, style, line, stack):
        return [str(executable), str(inp), str(menu), str(pause), str(palettes), str(out), str(ports),
                str(address), str(style), str(line), str(stack), str(font), str(stages)]

    def compare(ram, address, profile, style=0x0603, line=0x7000, stack=0x1feffc, sequence=None):
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, address), (UC_M68K_REG_A7, stack),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, 0xbeef0000 | style),
                (UC_M68K_REG_D3, 0xcafe0000 | line), (UC_M68K_REG_A0, 0x87654321),
                (UC_M68K_REG_A1, int.from_bytes(ram[0x7f16:0x7f1a], 'big'))):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        writes.clear()
        trace.clear()
        try:
            cpu.emu_start(ENTRY, RETURN, count=12000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), profile,
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (RETURN, LOOP, TRAP, BIOS):
            raise ValueError('Original failed to stop at expected boundary')
        caller_entries = [item for item in trace if item['address'] == 0xf5a]
        if pc == BIOS:
            if caller_entries:
                raise ValueError('BIOS transfer ran caller consumer')
        elif len(caller_entries) != 1 or caller_entries[0]['a6'] != address:
            raise ValueError('Native controller did not preserve caller A6: ' + repr(
                (len(rows), profile, address, caller_entries, trace)))
        if caller_entries and caller_entries[0]['a7'] != stack:
            raise ValueError('Original controller return did not restore caller stack')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        next_pc = 0 if pc == RETURN else pc
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run(arguments(address, style, line, stack), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports, parsed = out.read_bytes(), ports.read_bytes(), json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != {'next_pc': next_pc}:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if expected[at] != actual[at]]
            port_difference = next(((at//9, expected_ports[at:at+9].hex(), actual_ports[at:at+9].hex())
                for at in range(0, max(len(expected_ports), len(actual_ports)), 9)
                if expected_ports[at:at+9] != actual_ports[at:at+9]), None)
            raise ValueError('Caller-step mismatch: ' + repr((len(rows), profile, sequence,
                differences[:20], port_difference, next_pc, parsed, trace)))
        rows.append({'profile': profile, 'sequence': sequence, 'object_cpu_address': address,
            'initial_line': line, 'initial_style': style, 'entry_stack': stack,
            'active': ram[0x7df0], 'menu_active': ram[0x7dee], 'next_pc': next_pc,
            'actual_trace': trace.copy(), 'port_events': len(writes),
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected)

    for pending, request, gate, inhibited, palette_pending in itertools.product(
            (0, 1, 2, 3, 255), (0, 2, 8), (0, 2), (0, 255), (0, 128)):
        ram = fixture(pending=pending, request=request, palette_pending=palette_pending)
        ram[0xf000], ram[0x7def] = gate, inhibited
        compare(ram, 0x100f5c, 'inactive-idle-or-activation')
    for active, request, held, repeat in itertools.product((1, 2, 3), (0, 1, 2, 4, 8),
                                                         (0, 1, 4), (0, 1, 15)):
        ram = fixture(active=active, request=request, palette_pending=len(rows) % 2 * 128)
        ram[0x4cb4], ram[0x7df2], ram[0x7df3] = held, repeat, (0, 49, 255)[repeat % 3]
        compare(ram, 0x100f5c, 'active-wait-step-repeat-startup', style=0xff6b, line=0xffff)
    for mode, height, exit_word, matched in itertools.product((0, 1, 2), (0, 12), (0, 1), (False, True)):
        ram = menu_fixture(mode=mode, height=height, exit_word=exit_word)
        if not matched:
            ram[0x000f] ^= 1
        compare(ram, 0x100f5c, 'menu-opening-closing-counter-trap')
    for selected in (4, 5):
        ram = menu_fixture(selected=selected)
        ram[0x7f0c] = 3
        # Native static restart preconditions: no animation/palette owner or
        # coordinate link and object+10 zero, with original3ef2 allocator state.
        struct.pack_into('>H', ram, 0x8e4 + 0x10, 0)
        ram[0x8e4 + 0x1d], ram[0x8e4 + 0x6c] = 0, 255
        compare(ram, 0x100f5c, 'static-restart-caller-a6' if selected == 4 else
                'bios-transfer-skips-caller')
    isolated = len(rows)

    for child, palette_pending, stack in ((2, 0, 0x1feffc), (3, 128, 0x1f8000)):
        address, ram = 0x100f5c, fixture(pending=3, palette_pending=palette_pending)
        label, begin = 'carried-native-child-%d-pending-%d' % (child, palette_pending), len(rows)

        def tick(request=0, first=0, held=0):
            nonlocal ram
            ram[0x4cb5], ram[0x4cba], ram[0x4cc0], ram[0x4cb4] = request, first, 0, held
            ram = compare(ram, address, 'whole-native-chain-carry', 0xff6b, 0xffff, stack, label)

        def open_menu():
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big') - RAM_BASE
                if ram[0x7f1b] == 0 and ram[head + 4] >= ram[head + 12]:
                    return
            raise ValueError('Carried native menu failed to open')

        tick()
        for _ in range(20):
            tick(held=1)
        tick(2)
        open_menu()
        for _ in range(child):
            tick(first=2)
        tick(first=16)
        head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
        descriptor = int.from_bytes(ram[head - RAM_BASE:head - RAM_BASE + 4], 'big')
        if head != OLDEST - 16 or descriptor != (0x958a, 0x978a)[child - 2]:
            raise ValueError('Native chain failed to push selected stage child')
        open_menu()
        for first in (2, 4, 8, 16):
            tick(first=first)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]:
                break
        else:
            raise ValueError('Native chain stage choice failed full close')
        tick()  # Inactive idle: resumed caller counter path.
        tick(2)  # Reactivate from the complete caller output.
        if not ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Native chain failed reactivation')
        tick(2)
        open_menu()
        tick(2)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]:
                break
        else:
            raise ValueError('Reactivated native chain failed second full close')
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'resume_reactivation_and_second_exit_asserted': True})

    # A startup already mutates menu/video RAM before caller palette preparation
    # discovers the absent ID. Publishing must remain atomic across the chain.
    ram = fixture(active=1, request=2, palette_pending=0)
    ram[0x100f5c - RAM_BASE + 0x84] = 1
    struct.pack_into('>HH', ram, 0x4d92 + 10, 0xfffe, 0xfffe)
    ram[0x4d92 + 15] = 0x80
    inp.write_bytes(ram)
    for existing in (False, True):
        sentinels = (b'previous-chain-ram', b'previous-chain-ports')
        for path, sentinel in zip((out, ports), sentinels):
            if existing:
                path.write_bytes(sentinel)
            else:
                path.unlink(missing_ok=True)
        result = subprocess.run(arguments(0x100f5c, 0xff6b, 0xffff, 0x1feffc),
                                capture_output=True, text=True)
        if result.returncode == 0:
            raise ValueError('Late missing palette ID accepted')
        for path, sentinel in zip((out, ports), sentinels):
            if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                    not existing and path.exists()):
                raise ValueError('Late caller-chain failure modified outputs')
        negatives.append({'failure': 'late-palette-id-after-menu-startup', 'existing_outputs': existing,
            'outputs_preserved': True, 'stderr': result.stderr.strip(), 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original fixed ROM changed')
    if bytes(cpu.mem_read(0x200000, 0xffff0)) != program[0x200000:0x2ffff0]:
        raise ValueError('Original palette ROM bank changed outside PVC tail')
    hook_counts = {hex(address): sum(item['address'] == address for row in rows
                   for item in row['actual_trace']) for address in HOOKS}
    if not all(hook_counts.values()):
        raise ValueError('Native caller-chain hook coverage missing: ' + repr(hook_counts))
    stage_calls = [item for row in rows for item in row['actual_trace']
                   if item['address'] in (0x9602, 0x9802)]
    stage_stack_deltas = {row['entry_stack'] - item['a7'] for row in rows
        for item in row['actual_trace'] if item['address'] in (0x9602, 0x9802)}
    if stage_stack_deltas != {12, 16, 32}:
        raise ValueError('Stage callback stack depths lost real f54 outer return: ' +
                         repr(stage_stack_deltas))
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'address_mapping': 'Fixed ROM addresses equal decrypted '
            'offsets; observed palette bank CPU200000..2ffff0 maps same decrypted offsets.',
        'native_resource_sha256': hashes, 'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'isolated_cases': isolated, 'actual_hook_counts': hook_counts,
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_pvc_ports_equal': True,
        'next_pc_equal': True, 'caller_a6_preserved_asserted_at_f5a': True,
        'caller_stack_restored_at_f5a': True, 'controller_outer_return_stack_bytes': 4,
        'actual_stage_callback_stack_deltas': sorted(stage_stack_deltas),
        'stage_callback_outer_return_depth_asserted': True,
        'actual_stage_callback_calls': len(stage_calls), 'bios_skips_caller_asserted': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'late_failure_outputs_preserved': True,
        'ordered_port_events': sum(row['port_events'] for row in rows), 'results': rows,
        'scope': 'Unmodified f54 JSR9136 through f5a caller helpers, stopping before ec4 '
            'loop or fee TRAP15 execution, normal RTS, or BIOS c00444 transfer. Controller '
            'uses the real outer return stack and preserves caller A6. WholeRAM and all '
            'ordered video/watchdog/PVC writes compared; carried activation/wait/held '
            'steps/stage children/full close/resume/reactivation cycles. Host supplies '
            'input bytes and incoming line/style each call. ec4 loop implementation, '
            'natural input collection, physical device timing, trap handler, other CPU '
            'registers/flags, external stack memory and full boot excluded.'}, indent=2) + '\n')
    print('Native control caller chain original/C++ match:', len(rows), 'cases;',
          len(sequences), 'carried lifecycles;', len(negatives), 'late failures;', hook_counts)


if __name__ == '__main__':
    main()
