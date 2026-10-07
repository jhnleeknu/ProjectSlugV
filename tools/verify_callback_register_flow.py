"""Carry actual C++ D1/D3 through native callback, palette, IRQ and input."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources
from verify_frame_gate import zlib_crc

BASE, GATE, PREFIX, CALLBACK, CONTROL, RETURN, LOOP, TRAP, BIOS = (
    0x100000, 0xf4c, 0xf12, 0xf3c, 0xf54, 0xff000, 0xec4, 0xfee, 0xc00444)
INPUT_PORTS = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    irq_cli, main_cli = root / 'build/step_interrupt', root / 'build/step_input_control'
    streams, status, menu, pause, palettes, font, stages = [root / 'extracted/runtime' / name for name in
        ('input_streams.ms5d', 'input_status.ms5d', 'control_menu_tree.ms5d', 'control_pause.ms5d',
         'palettes.ms5p', 'menu_fonts.ms5d', 'stages')]
    debug = root / 'extracted/runtime/main_debug.ms5d'
    hashes = {'debug': checked_resource(debug, program, 0xd56, 0xe40), 'streams': checked_resource(streams, program, 0xf01fe, 0xf1a0e),
        'status': checked_resource(status, program, 0xb58, 0xc58),
        'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
        'pause': checked_resource(pause, program, 0x9068, 0x9086),
        'font': checked_resource(font, program, 0xe80c8, 0xe84c8),
        'null_name': checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)}
    groups = verify_resources(stages, program, source)
    records, ignored = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] + records[identifier][1] for identifier in sorted(records))
    packed = palettes.read_bytes()
    assert packed == struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload), zlib_crc(payload), 0, 0) + payload
    hashes['palettes'] = hashlib.sha256(packed).hexdigest()
    folder = root / 'artifacts/callback_register_flow'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, regs_in, banks_in, banks_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'registers.bin', 'banks.bin', 'cpp.banks.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 0x1000)
    state = {'mode': 'setup', 'visits': 0, 'video': 0, 'video_reads': 0, 'sound_reads': 0, 'stop_pc': None, 'palette_calls': 0, 'paths': [], 'stack_writes': []}
    ports, reads, trace, rows, sequences = [], [], [], [], []
    samples = []

    def read(cpu, access, address, size, value, user):
        if address == 0x320000:
            assert state['mode'] == 'irq' and size == 1
            state['sound_reads'] += 1
            cpu.mem_write(address, b'\0')
        elif address == 0x3c0006:
            assert state['mode'] == 'main' and size == 2
            state['video_reads'] += 1
            cpu.mem_write(address, state['video'].to_bytes(2, 'big'))
        elif address in INPUT_PORTS:
            ordinal = len(reads)
            assert state['mode'] == 'main' and ordinal < len(samples) and address == INPUT_PORTS[ordinal] and size == 1
            cpu.mem_write(address, bytes([samples[ordinal]]))
            reads.append((address, samples[ordinal]))

    def write(cpu, access, address, size, value, user):
        if state['mode'] == 'envelope' and 0x1fe000 <= address and address + size <= 0x1ff000:
            state['stack_writes'].append((size, address, value & ((1 << (size * 8)) - 1)))
        if address in (0x300001, 0x320000, 0x2ffff0, 0x2ffff2, 0x3a0001) or 0x3c0000 <= address < 0x3c0010:
            ports.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fb000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((hex(address), size, value)))

    def code(cpu, address, size, user):
        if address == state['stop_pc']:
            cpu.emu_stop()
            return
        if address == 0x5728:
            state['palette_calls'] += 1
        if address in (0x4718, 0x479e, 0x4c40, 0x504c):
            state['paths'].append(address)
        if state['mode'] == 'main':
            if address == GATE:
                state['visits'] += 1
                if state['visits'] == 2:
                    cpu.emu_stop()
            elif address in (PREFIX, CALLBACK, CONTROL):
                trace.append({'pc': address, 'd1': cpu.reg_read(m68k_const.UC_M68K_REG_D1),
                    'a6': cpu.reg_read(m68k_const.UC_M68K_REG_A6), 'a7': cpu.reg_read(m68k_const.UC_M68K_REG_A7)})
            if address in (CALLBACK, LOOP, TRAP, BIOS, RETURN):
                cpu.emu_stop()
        elif state['mode'] == 'irq' and address == RETURN:
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_READ, read, begin=0x300000, end=0x3c0007)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.mem_write(BASE, bytes(65536))
    cpu.reg_write(m68k_const.UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(m68k_const.UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN
    allocated = bytes(cpu.mem_read(BASE, 65536))

    def fixture(threshold, signal=0, callback=0, guard=0, pointer=0x100001):
        ram = bytearray(allocated)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14], ram[node + 15] = slot & 31, 0x80 | (slot & 3)
        ram[0x7df0], ram[0xfdaf], ram[0xf000], ram[0xf002] = 0, 2, 2, 1
        ram[0xfdb6:0xfdba] = b'\1\1\1\1'
        ram[0x4cd2], ram[0x4cd3] = 15, 4
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        struct.pack_into('>H', ram, 0xe, 0xffff)
        struct.pack_into('>H', ram, 0xf5c + 0x7e, 0xffff)
        ram[0xf5c + 0x84] = 1
        struct.pack_into('>II', ram, 0xf5c + 0x76, callback, 0xdeadbeef)
        ram[0x16], ram[0x17], ram[0x18], ram[0x19], ram[0x1b] = signal, threshold, 0xa5, guard, 0x7f
        struct.pack_into('>I', ram, 0x81c, pointer)
        struct.pack_into('>H', ram, 0xd68c, 0)
        struct.pack_into('>HH', ram, 0x4d74, 0, 0)
        ram[0x4d7b], ram[0xf003], ram[0x14] = 0, 0, 0
        return ram

    def new_main_context(ram, style=0xff6b, object_address=0x100f5c):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((m68k_const.UC_M68K_REG_SR, 0x2000), (m68k_const.UC_M68K_REG_A5, 0x108000),
                (m68k_const.UC_M68K_REG_A6, object_address), (m68k_const.UC_M68K_REG_A7, 0x1feffc),
                (m68k_const.UC_M68K_REG_D0, 0x12345678), (m68k_const.UC_M68K_REG_D1, 0xbeef0000 | style),
                (m68k_const.UC_M68K_REG_D3, 0xcafe7000), (m68k_const.UC_M68K_REG_A1, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        return cpu.context_save()

    def poll(ram, context, video, current_samples, profile):
        cpu.mem_write(BASE, bytes(ram))
        cpu.context_restore(context)
        incoming = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        state.update(mode='main', visits=0, video=video, video_reads=0, sound_reads=0, stop_pc=None, palette_calls=0)
        samples[:] = current_samples[:5 if ram[0x4cd4] == 0 else 3]
        ports.clear()
        reads.clear()
        trace.clear()
        cpu.emu_start(GATE, RETURN, count=12000000)
        ready = ram[0x16] != 0
        pc = cpu.reg_read(m68k_const.UC_M68K_REG_PC)
        expected = bytes(cpu.mem_read(BASE, 65536))
        assert expected[0x18] == ram[0x18]
        if not ready or pc == CALLBACK:
            assert state['palette_calls'] == 0
        assert state['visits'] == (1 if ready else 2) and state['video_reads'] == 0 and state['sound_reads'] == 0
        prefix = [entry for entry in trace if entry['pc'] in (CALLBACK, CONTROL)]
        if ready:
            assert len(prefix) == 1 and prefix[0]['a6'] == incoming[14] and prefix[0]['a7'] == incoming[15]
            assert expected[0x1a] == ram[0x16] and expected[0x16] == 0
            callback = struct.unpack_from('>I', expected, 0xf5c + 0x76)[0] if pc == CALLBACK else 0
            callback_context = struct.unpack_from('>I', expected, 0xf5c + 0x7a)[0] if callback else 0
            style = prefix[0]['d1'] & 65535
        else:
            assert pc == GATE and expected == ram and not ports and not reads and not trace
            assert cpu.reg_read(m68k_const.UC_M68K_REG_D1) == incoming[1] and cpu.reg_read(m68k_const.UC_M68K_REG_A6) == incoming[14]
            callback, callback_context, style = 0, 0, incoming[1] & 65535
        result = {'next_pc': 0 if pc == RETURN else pc, 'callback': callback,
            'callback_context': callback_context, 'style': style, 'read_count': len(reads),
            'd1': cpu.reg_read(REGS[1]) & 0xffffffff, 'd3': cpu.reg_read(REGS[3]) & 0xffffffff}
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        inp.write_bytes(ram)
        for path in (out, ports_out):
            path.unlink(missing_ok=True)
        resume_mode = profile.startswith('default-callback-cycle-') or profile.startswith('full-default-callback-cycle-')
        gate_options = ['--main', hex(GATE), str(debug), str(video)] if resume_mode else ['--callback-poll']
        args = [str(main_cli), '--registers', str(incoming[1]), str(incoming[3]), *gate_options, str(inp), str(streams), str(status), str(menu), str(pause), str(palettes),
            str(out), str(ports_out), str(incoming[14]), str(incoming[1] & 65535), str(incoming[3] & 65535), str(incoming[15])] + [str(value) for value in current_samples] + [str(font), str(stages)]
        actual = subprocess.run(args, capture_output=True, text=True)
        if actual.returncode or out.read_bytes() != expected or ports_out.read_bytes() != expected_ports or json.loads(actual.stdout) != result:
            raise ValueError(repr((len(rows), profile, 'main', result, actual.stdout, actual.stderr)))
        parsed = json.loads(actual.stdout)
        cpu.reg_write(REGS[1], parsed['d1'])
        cpu.reg_write(REGS[3], parsed['d3'])
        rows.append({'kind': 'main', 'profile': profile, 'initial_signal': ram[0x16], 'threshold': ram[0x17],
            'ready': ready, 'main_resume_api': resume_mode, 'video': video, 'video_reads': state['video_reads'], 'input_reads': reads[:],
            'ports': len(ports), 'result': result, 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(out.read_bytes()), cpu.context_save(), ready

    def interrupt(ram, main_context, profile):
        cpu.mem_write(BASE, bytes(ram))
        cpu.context_restore(main_context)
        main_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        registers = list(struct.unpack('>16I', hashlib.shake_256(b'frame-flow-irq-regs:' + len(rows).to_bytes(4, 'big')).digest(64)))
        registers[0], registers[13], registers[15] = 0xabcd0000 | (len(rows) & 255), 0x108000, 0x1fcffc
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        cpu.mem_write(registers[15], RETURN.to_bytes(4, 'big'))
        state.update(mode='irq', video_reads=0, sound_reads=0, stop_pc=None, palette_calls=0)
        ports.clear()
        reads.clear()
        trace.clear()
        cpu.emu_start(0xc8c, RETURN, count=100000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN and not reads and not state['video_reads']
        expected = bytes(cpu.mem_read(BASE, 65536))
        reentrant = bool(ram[0x19] & 128)
        assert state['sound_reads'] == int(not reentrant)
        assert expected[0x16] == (ram[0x16] if reentrant else min(255, ram[0x16] + 1))
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        result = {'service_phase': 1 if reentrant else 0, 'display_bank': 0, 'sound_reads': state['sound_reads'],
            'task_registers': [0] * 16, 'task': {'next_pc': 0, 'restored': False, 'stack_address': [0, 0], 'stack_value': [0, 0]},
            'pending': dict.fromkeys(('kind', 'phase', 'low', 'cursor', 'command', 'tail', 'next'), 0)}
        banks = hashlib.shake_256(b'frame-flow-unused-banks').digest(16384)
        inp.write_bytes(ram)
        banks_in.write_bytes(banks)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, banks_out, ports_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(irq_cli), 'begin', str(inp), str(banks_in), str(regs_in), str(out), str(banks_out), str(ports_out), '0', '0'], capture_output=True, text=True)
        assert not actual.returncode and out.read_bytes() == expected and banks_out.read_bytes() == banks and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (profile, actual.stdout, actual.stderr)
        cpu.context_restore(main_context)
        restored_main_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        assert restored_main_registers == main_registers
        rows.append({'kind': 'irq', 'profile': profile, 'initial_signal': ram[0x16], 'result_signal': expected[0x16],
            'reentrant': reentrant, 'sound_reads': state['sound_reads'], 'ports': len(ports),
            'main_d1_preserved': main_registers[1], 'main_a6_preserved': main_registers[14],
            'all_main_registers_restored_by_host_context': True, 'result': result,
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(out.read_bytes()), cpu.context_save()

    def prepare(ram, context, profile):
        cpu.context_restore(context)
        incoming = cpu.reg_read(m68k_const.UC_M68K_REG_D1)
        incoming_d3 = cpu.reg_read(REGS[3])
        saved_context = [cpu.reg_read(REGS[index]) for index in (13, 14, 15)]
        cpu.mem_write(BASE, bytes(ram))
        state.update(mode='palette', stop_pc=GATE, palette_calls=0, paths=[])
        ports.clear()
        cpu.emu_start(0xf46, RETURN, count=1000000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == GATE and state['palette_calls'] == 1
        assert [cpu.reg_read(REGS[index]) for index in (13, 14, 15)] == saved_context
        expected = bytes(cpu.mem_read(BASE, 65536))
        final = cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 0xffffffff
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        inp.write_bytes(ram)
        actual = subprocess.run([str(root / 'build/step_palette_frame'), '--registers', hex(incoming), hex(incoming_d3), str(inp), str(palettes), str(out), str(ports_out)], capture_output=True, text=True)
        assert not actual.returncode and out.read_bytes() == expected and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == {'d1': final, 'd3': cpu.reg_read(REGS[3]) & 0xffffffff}, (profile, actual.stdout, actual.stderr)
        parsed = json.loads(actual.stdout)
        cpu.reg_write(REGS[1], parsed['d1'])
        cpu.reg_write(REGS[3], parsed['d3'])
        rows.append({'kind': 'palette', 'profile': profile, 'paths': state['paths'][:], 'incoming_d1': incoming,
            'final_d1': final, 'incoming_d3': incoming_d3, 'final_d3': parsed['d3'], 'ports': len(ports), 'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(out.read_bytes()), cpu.context_save(), parsed['d1']

    def envelope(ram, context, mode, entry, target):
        cpu.context_restore(context)
        registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        stack = bytes(cpu.mem_read(0x1fe000, 4096))
        cpu.mem_write(BASE, bytes(ram))
        state.update(mode='envelope', stop_pc=target, stack_writes=[])
        ports.clear()
        cpu.emu_start(entry, RETURN, count=10000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == target and not ports
        expected = bytes(cpu.mem_read(BASE, 65536))
        after_stack = bytes(cpu.mem_read(0x1fe000, 4096))
        after = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        stack_in, stack_out, regs_out = [folder / name for name in ('stack.bin', 'cpp.stack.bin', 'cpp.regs.bin')]
        inp.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        actual = subprocess.run([str(root / 'build/step_irq_envelope'), mode, str(inp), str(stack_in), str(regs_in), str(out), str(stack_out), str(regs_out), str(ports_out), '0x1fe000'], capture_output=True, text=True)
        result = {'next_pc': target, 'bios_handoff': False, 'stack_writes': [list(event) for event in state['stack_writes']]}
        assert not actual.returncode and out.read_bytes() == expected and stack_out.read_bytes() == after_stack and regs_out.read_bytes() == struct.pack('>16I', *after) and not ports_out.read_bytes() and json.loads(actual.stdout) == result, (mode, actual.stdout, actual.stderr, result)
        cpp_registers = struct.unpack('>16I', regs_out.read_bytes())
        for reg, value in zip(REGS, cpp_registers):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1fe000, stack_out.read_bytes())
        rows.append({'kind': 'envelope', 'mode': mode, 'ports': 0, 'result': result, 'all_ram_stack_registers_equal': True})
        return bytearray(out.read_bytes()), cpu.context_save()

    def palette_fixture(kind):
        ram = fixture(255, callback=0x3dcc)
        for slot in range(256):
            at = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, at + 10, 0x203, 0x203)
            ram[at + 14], ram[at + 15] = 0, 2
        at = 0x4d92 + 255 * 16
        ram[at + 15] = 128 | (2 if kind == 'direct' else 0)
        if kind in ('blend', 'effect-blend'):
            struct.pack_into('>H', ram, at + 12, 0x87a)
            ram[at + 14] = 15
        if kind in ('effect', 'effect-blend'):
            struct.pack_into('>HHH', ram, 0x7dc2, 0xff00, 0x0700, 0x1f00)
        return ram

    for kind, path in (('direct', 0x4718), ('effect', 0x479e), ('blend', 0x4c40), ('effect-blend', 0x504c)):
        begin = len(rows)
        ram = palette_fixture(kind)
        ram, context, d1 = prepare(ram, new_main_context(ram, 0xa5aa), kind)
        assert path in rows[-1]['paths']
        ram, context, ready = poll(ram, context, 0xffff, [255] * 5, kind + '-wait')
        assert not ready
        ram, context = interrupt(ram, context, kind + '-irq-produces-signal')
        ram, context, ready = poll(ram, context, 0xffff, [255, 254, 253, 252, 251], kind + '-ready')
        assert ready and rows[-1]['result']['style'] & 0xff00 == d1 & 0xff00
        sequences.append({'profile': kind, 'cases': len(rows) - begin, 'signal_generated_by_native_irq': True,
            'palette_runs': 1, 'wait_does_not_repeat_palette': True, 'palette_d1_high_byte_reaches_input_style': True})

    begin = len(rows)
    ram = palette_fixture('blend')
    ram[0x16] = 1  # Initial fixture only; subsequent readiness is produced by c8c.
    ram, context, ready = poll(ram, new_main_context(ram), 0, [255] * 5, 'full-default-callback-cycle-input')
    assert ready
    for cycle in range(3):
        label = 'default-callback-cycle-' + str(cycle)
        ram, context = envelope(ram, context, 'main-call', 0xf3c, 0x3dcc)
        ram, context = envelope(ram, context, 'callback', 0x3dcc, 0xf44)
        ram, context = envelope(ram, context, 'main-return', 0xf44, 0xf46)
        ram, context, d1 = prepare(ram, context, label + '-palette')
        ram, context, ready = poll(ram, context, 0, [255] * 5, label + '-wait')
        assert not ready
        ram, context = interrupt(ram, context, label + '-native-irq')
        ram, context, ready = poll(ram, context, 0, [255] * 5, label + '-ready')
        assert ready and rows[-1]['result']['style'] & 0xff00 == d1 & 0xff00
    sequences.append({'profile': 'actual-main-call-default-rts-main-return-palette-irq-input', 'cycles': 3,
        'cases': len(rows) - begin, 'actual_default_callback_executed': True,
        'signal_generated_by_native_irq': True, 'palette_runs': 3})

    negatives = []
    sentinel = b'previous-callback-gate-output\0\xff'
    def reject(ram, label, selected_streams=streams):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports_out.write_bytes(sentinel)
        args = [str(main_cli), '--callback-poll', str(inp), str(selected_streams), str(status), str(menu), str(pause), str(palettes), str(out), str(ports_out), '0x100f5c', '0xff6b', '0x7000', '0x1feffc'] + ['253', '255', '255', '255', '255'] + [str(font), str(stages)]
        actual = subprocess.run(args, capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports_out.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})
    for size in (0, 65535, 65537):
        reject(bytes(size), 'invalid-ram-size-' + str(size))
    bad_resource = folder / 'invalid.ms5d'
    bad_resource.write_bytes(b'bad-resource')
    reject(fixture(0), 'cli-loads-resource-even-while-waiting', bad_resource)
    late = fixture(255, 1)
    struct.pack_into('>HH', late, 0x4d92 + 10, 0xfffe, 0xfffe)
    reject(late, 'late-palette-lookup-after-input-controller-mutation')
    for label, options in (
            ('duplicate-registers', ['--registers', '3', '0', '--registers', '3', '0']),
            ('registers-then-d1', ['--registers', '3', '0', '--d1', '3']),
            ('d1-then-registers', ['--d1', '3', '--registers', '3', '0']),
            ('missing-registers-values', ['--registers']),
            ('missing-registers-d3', ['--registers', '3']),
            ('overflow-d1', ['--registers', '4294967296', '0']),
            ('negative-d3', ['--registers', '3', '-1'])):
        inp.write_bytes(palette_fixture('blend'))
        out.write_bytes(sentinel); ports_out.write_bytes(sentinel)
        actual = subprocess.run([str(root/'build/step_palette_frame'), *options,
            str(inp), str(palettes), str(out), str(ports_out)], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports_out.read_bytes() == sentinel
        negatives.append({'failure': 'palette-' + label, 'outputs_preserved': True})
    # Existing --d1 and silent CLI modes remain compatible with register mode.
    legacy_ram = palette_fixture('blend')
    inp.write_bytes(legacy_ram)
    outputs = []
    for options in ([], ['--d1', '0x1234ab68'], ['--registers', '0x1234ab68', '0x56787088']):
        actual = subprocess.run([str(root/'build/step_palette_frame'), *options,
            str(inp), str(palettes), str(out), str(ports_out)], capture_output=True, text=True)
        assert not actual.returncode
        outputs.append((out.read_bytes(), ports_out.read_bytes(), actual.stdout))
    assert outputs[0][:2] == outputs[1][:2] == outputs[2][:2] and not outputs[0][2]
    assert json.loads(outputs[1][2]) == {'d1': json.loads(outputs[2][2])['d1']}
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert bytes(cpu.mem_read(0x200000, 0xffff0)) == program[0x200000:0x2ffff0]
    assert any(row['kind'] == 'main' and row['result']['next_pc'] == CALLBACK for row in rows)
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'cases': len(rows),
        'irq_cases': sum(row['kind'] == 'irq' for row in rows), 'main_poll_cases': sum(row['kind'] == 'main' for row in rows),
        'whole_ram_and_ordered_ports_equal': True, 'video_input_sound_read_counts_equal': True,
        'cpp_full_d1_d3_equal_and_carried': True,
        'main_f4c_resume_api_cases': sum(row.get('main_resume_api', False) for row in rows),
        'remaining_main_palette_cpu_registers_are_native_context_fixtures': True,
        'irq_main_context_restored_explicitly_by_host': True,
        'envelope_register_file_is_actual_cpp_output': True,
        'palette_legacy_modes_compatible': True,
        'carried_sequence_readiness_produced_by_actual_irq_without_host_signal_writes': True,
        'initial_sequence_signals_are_explicit_fixtures': True,
        'palette_cases': sum(row['kind'] == 'palette' for row in rows),
        'envelope_cases': sum(row['kind'] == 'envelope' for row in rows),
        'negative_cases': len(negatives), 'negative_results': negatives,
        'runtime_hashes': hashes, 'stage_groups_verified': len(groups), 'output_carry_sequences': sequences,
        'results': rows,
        'scope': 'Actual C++ RAM/D1/D3 outputs carry across input callback polling and palette APIs. '
            'Envelope boundaries carry actual C++ RAM, stack and all 16 register outputs. '
            'Other main/input/palette registers and CPU flags remain native context fixtures; '
            'they are not claimed as C++ outputs. IRQ c8c readiness updates shared RAM while '
            'host explicitly saves/restores main CPU context; no SR/RTE or natural timing claimed. '
            'Four palette paths and three complete main-call/default RTS/main-return/palette/wait/IRQ/input '
            'cycles use unchanged ROM. Arbitrary callbacks, BIOS and physical timing excluded.'
    }, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'irq_cases': sum(row['kind'] == 'irq' for row in rows),
        'main_poll_cases': sum(row['kind'] == 'main' for row in rows), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
