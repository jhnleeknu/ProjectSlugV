"""Compare continuous unmodifiedc8c interrupt service and explicit continuations."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK, WAIT, PALETTE = 0x100000, 0xff000, 0x1feffc, 0x3aea, 0x400000
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]
PENDING = ('kind', 'phase', 'low', 'cursor', 'command', 'tail', 'next')
OBJECTS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/step_interrupt'
    resources = [root / 'extracted/runtime' / ('composition_%06x.ms5c' % identifier) for identifier in (0x2152, 0x2952)]
    folder = root / 'artifacts/interrupt_service'
    folder.mkdir(parents=True, exist_ok=True)
    inp, bank_in, regs_in, out, bank_out, ports, report = [folder / name for name in
        ('input.bin', 'banks.bin', 'registers.bin', 'cpp.bin', 'cpp.banks.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x400000:0x500000])
    cpu.mem_map(PALETTE, 8192)
    cpu.mem_map(0xd00000, 0x1000)
    state = {'bank': 0, 'banks': None, 'wait': 0, 'target': None,
        'external': 0, 'external_reads': 0, 'status': 0, 'reads': 0, 'sp': STACK}
    hardware, task_stack, rows, negatives, sequences = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        pc = cpu.reg_read(m68k_const.UC_M68K_REG_PC)
        if pc in (0xd18, 0xd1e):
            assert size == 4
            task_stack.append((address, value))
        if address in (0x300001, 0x2ffff0, 0x2ffff2, 0x3a000f, 0x3a001f,
                0x3a0011, 0x3a0001, 0x3c0000, 0x320000) or PALETTE <= address < PALETTE + 8192:
            hardware.append((size, address, value))
            if address in (0x3a000f, 0x3a001f):
                assert size == 1
                state['bank'] = int(address == 0x3a001f)
                cpu.mem_write(PALETTE, bytes(state['banks'][state['bank']]))
            elif PALETTE <= address < PALETTE + 8192:
                assert size in (2, 4)
                at = address - PALETTE
                state['banks'][state['bank']][at:at + size] = value.to_bytes(size, 'big')
        elif not (BASE <= address and address + size <= BASE + 65536) and not (STACK - 4096 <= address and address + size <= STACK + 8):
            raise ValueError('Unexpected native write outside RAM/stack/MMIO: ' + repr((hex(pc), hex(address), size, value)))

    def read_hook(cpu, access, address, size, value, user):
        assert size == 1
        if address == 0xd00046:
            state['external_reads'] += 1
            cpu.mem_write(address, bytes([state['external']]))
        else:
            state['reads'] += 1
            cpu.mem_write(address, bytes([state['status']]))

    def code_hook(cpu, address, size, user):
        if address == state['target']:
            cpu.emu_stop()
        if address == WAIT:
            head = int.from_bytes(cpu.mem_read(BASE + 0x4d74, 2), 'big')
            if head == cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 65535:
                state['wait'] += 1
                if state['wait'] == 2:
                    cpu.emu_stop()
            else:
                state['wait'] = 0

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x320000, end=0x320000)
    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0xd00046, end=0xd00046)
    cpu.hook_add(UC_HOOK_CODE, code_hook)

    def word(ram, at, value):
        struct.pack_into('>H', ram, at, value)

    def fixture(render=False):
        seed = b'ms5-interrupt-service-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(65536)
        banks = hashlib.shake_256(seed + b'banks').digest(16384)
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[0], registers[13], registers[15] = 0xabcdab35, 0x108000, STACK
        ram[4], ram[5], ram[0xfdaf], ram[0xf004], ram[0xf007] = 0x99, 0x99, 2, 3, 3
        ram[0x1b] = 128 if render else 0
        struct.pack_into('>I', ram, 0x81c, 0x10081c)
        ram[0x5da2:0x7dc2] = hashlib.shake_256(seed + b'palette-and-pattern').digest(8224)
        for block in range(256):
            ram[0x5da2 + 32 * block] &= 127
        for pool, lower, upper in ((0x8d3e, 0, 190), (0x8d46, 190, 380)):
            ram[pool:pool + 8] = struct.pack('>4H', lower, upper, lower + 95, lower + 95)
        return ram, banks, registers

    def sprite_state(ram, count=0, ready=True, forward=True, disabled=False, flip=0):
        ram[0x8d3c], ram[0x8d3d] = 0x21 | (128 if forward else 0), 0x35 | (128 if ready else 0)
        word(ram, 0x8d34, 0x1fc)
        word(ram, 0x8d36, (0x1fc + count * 2) & 0x1fe)
        if disabled:
            ram[0x8d46:0x8d4e] = bytes([255]) * 8
        for index in range(count):
            offset = 12 * (index + 1)
            word(ram, 0x8b34 + ((0x1fc + index * 2) & 0x1fe), offset)
            identifier = 0x2152 if index % 2 == 0 else 0x2952
            ram[0x7f34 + offset:0x7f34 + offset + 12] = struct.pack('>III', 160 << 6,
                0xffff1500 | (4 if index % 2 else 0) | flip, (384 << 23) | identifier)

    def columns(ram, mask):
        for index, address in enumerate(OBJECTS):
            at = address - BASE
            ram[at + 0x7a] = 0x81 if mask & (1 << index) else 1
            word(ram, at + 0x26, 0x7bfe + index if index < 2 else index * 31)
            word(ram, at + 0x7c, 0x0137 + index)
            word(ram, at + 0x7e, 0x01ff - index)
            ram[at + 0x3a:at + 0x7a] = hashlib.shake_256(b'columns:' + bytes([index])).digest(64)

    def tasks(ram, count):
        pointer = 0x10081c - 64 * count
        for index in range(count):
            frame = list(struct.unpack('>16I', hashlib.shake_256(b'interrupt-frame:' + index.to_bytes(4, 'big')).digest(64)))
            frame[0], frame[13], frame[15] = 0x12340000 | index, 0x108000, 0xff100 + index * 4
            struct.pack_into('>16I', ram, pointer - BASE + index * 64, *frame)
        struct.pack_into('>I', ram, 0x81c, pointer)
        return 0xff100 if count else None

    def expected_result(mode, ram, incoming):
        pc = cpu.reg_read(m68k_const.UC_M68K_REG_PC)
        pending = dict.fromkeys(PENDING, 0)
        task = {'next_pc': 0, 'restored': False, 'stack_address': [0, 0], 'stack_value': [0, 0]}
        task_registers = [0] * 16
        if pc == WAIT:
            phase = 3
            sp = cpu.reg_read(m68k_const.UC_M68K_REG_A7)
            ret = int.from_bytes(cpu.mem_read(sp, 4), 'big')
            assert ret in (0x3c00, 0x4817e)
            byte_phase = 1 if ret == 0x3c00 else 2
            low = cpu.mem_read(sp + 4, 1)[0] if byte_phase == 1 else cpu.reg_read(m68k_const.UC_M68K_REG_D0) & 255
            tail = cpu.reg_read(m68k_const.UC_M68K_REG_A0) - BASE - 0x4cf4
            pending.update(kind=1, phase=byte_phase, low=low, cursor=0,
                command=cpu.reg_read(m68k_const.UC_M68K_REG_D0) & 255, tail=tail,
                next=cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 65535)
            assert state['wait'] == 2 and state['reads'] == 0
        elif pc == state['target'] and state['target'] is not None:
            phase = 2
            task_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
            assert task_stack == [(incoming[15] - 4, 0xd2a), (incoming[15] - 8, pc)]
            for address, value in task_stack:
                assert bytes(cpu.mem_read(address, 4)) == value.to_bytes(4, 'big')
            task = {'next_pc': pc, 'restored': True, 'stack_address': [event[0] for event in task_stack],
                'stack_value': [event[1] for event in task_stack]}
            assert state['reads'] == 0
        else:
            assert pc == RETURN, hex(pc)
            phase = 1 if mode == 'begin' and ram[0x19] & 128 else 0
            assert state['reads'] == (0 if phase == 1 else 1)
        return {'service_phase': phase, 'display_bank': state['bank'] if mode == 'begin' else None,
            'sound_reads': state['reads'], 'task_registers': task_registers, 'task': task, 'pending': pending}

    def compare(ram, banks, registers, mode='begin', external=0, status=0, previous=None,
            target=None, profile='matrix', selected_resources=None, context=None):
        cpu.mem_write(BASE, bytes(ram))
        state['banks'] = [bytearray(banks[:8192]), bytearray(banks[8192:])]
        if mode == 'begin':
            state['bank'] = 0
        cpu.mem_write(PALETTE, bytes(state['banks'][state['bank']]))
        state.update(wait=0, target=target, external=external, external_reads=0, status=status, reads=0, sp=registers[15])
        hardware.clear()
        task_stack.clear()
        if context is None:
            cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
            for reg, value in zip(REGS, registers):
                cpu.reg_write(reg, value)
            cpu.mem_write(registers[15], RETURN.to_bytes(4, 'big'))
        else:
            cpu.context_restore(context)
        cpu.emu_start({'begin': 0xc8c, 'task': 0xd2a, 'sound': WAIT}[mode], RETURN, count=1000000)
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_banks = b''.join(state['banks'])
        result = expected_result(mode, ram, registers)
        expected_ports = b''.join(struct.pack('>BII', *event) for event in hardware)
        assert bytes(cpu.mem_read(PALETTE, 8192)) == state['banks'][state['bank']]
        if result['service_phase'] == 0:
            assert expected[0x19] == 0
        elif result['service_phase'] in (2, 3):
            assert expected[0x19] & 128
        inp.write_bytes(ram)
        bank_in.write_bytes(banks)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, bank_out, ports):
            path.unlink(missing_ok=True)
        args = [str(executable), mode, str(inp), str(bank_in), str(regs_in), str(out), str(bank_out), str(ports), str(external), str(status)]
        if mode == 'sound':
            args += [str(previous['pending'][key]) for key in PENDING]
        if mode != 'sound':
            args += [str(path) for path in (resources if selected_resources is None else selected_resources)]
        actual = subprocess.run(args, capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or not bank_out.exists() or bank_out.read_bytes() != expected_banks or not ports.exists() or ports.read_bytes() != expected_ports or json.loads(actual.stdout) != result:
            differences = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            expected_events = hardware[:8]
            raise ValueError(repr((len(rows), profile, mode, result, actual.stdout, actual.stderr, differences[:20], expected_events)))
        rows.append({'profile': profile, 'mode': mode, 'initial_counter': ram[0x16], 'initial_guard': ram[0x19],
            'native_external_reads': state['external_reads'], 'ports': len(hardware), 'result': result,
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'banks_sha256': hashlib.sha256(expected_banks).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), expected_banks, result, [cpu.reg_read(reg) & 0xffffffff for reg in REGS], cpu.context_save()

    for counter in range(256):
        ram, banks, registers = fixture()
        ram[0x16], ram[0x19] = counter, counter & 127
        ram[0xfd82] = counter & 1
        compare(ram, banks, registers, status=counter, profile='all256-counter-saturation-values')
    for guard in range(256):
        ram, banks, registers = fixture(render=True)
        ram[0x19], ram[0x16] = guard, 255
        ram[0x1b] = 0 if guard < 128 else 128
        compare(ram, banks, registers, status=guard, profile='all256-busy-guard-bytes')
    for credit, mode, request in itertools.product((0, 1, 9, 0x10, 0x99, 0xa0, 0xfa, 255), (0, 1, 2, 255), (0, 3)):
        ram, banks, registers = fixture()
        ram[4], ram[5], ram[0xfdaf], ram[0x14] = credit, 255 - credit, mode, request
        compare(ram, banks, registers, status=2, profile='credit-valid-invalid-bcd-composed-prefix')
    for index in range(32):
        ram, banks, registers = fixture(render=True)
        ram[0x7ded], ram[0x7dec], ram[0xf001] = (128 if index & 1 else 0), (255 if index & 2 else 0), (16 if index & 4 else 0)
        dirty = ((), (index,), tuple(range(256)), tuple(range(0, 256, 2)))[index % 4]
        for block in dirty:
            ram[0x5da2 + block * 32] |= 128
        columns(ram, index & 15)
        sprite_state(ram, count=(0, 1, 4, 20)[index % 4], ready=bool(index & 8),
            forward=bool(index & 16), disabled=bool(index & 2), flip=index & 3)
        ram[0xfd82] = index & 1
        compare(ram, banks, registers, status=index, profile='composed-normal-palette-columns-real-sprites')
    for pattern, display in itertools.product((bytes(32), bytes([255]) * 32, bytes(range(32)),
            hashlib.shake_256(b'interrupt-special-pattern').digest(32)), (0, 255)):
        ram, banks, registers = fixture(render=True)
        word(ram, 0x7dea, 0x2000)
        ram[0x7da2:0x7dc2], ram[0x7dec], ram[0xf001] = pattern, display, 16
        columns(ram, 15)
        sprite_state(ram, 4)
        compare(ram, banks, registers, status=1, profile='special-palette-fill-full-columns-sprites')
    ram, banks, registers = fixture(render=True)
    ram[0x7ded], ram[0x7dec], ram[0xf001] = 128, 255, 16
    ram[4], ram[5], ram[0x14] = 0xa0, 0x10, 3
    for block in range(256):
        ram[0x5da2 + block * 32] |= 128
    columns(ram, 15)
    sprite_state(ram, 4)
    compare(ram, banks, registers, status=2, profile='all256-dirty-normal-upload-credit-columns-sprites')
    for pointer in (0x100001, 0x1007dc, 0xffffffff):
        ram, banks, registers = fixture(render=False)
        struct.pack_into('>I', ram, 0x81c, pointer)
        compare(ram, banks, registers, status=1, profile='render-disabled-bypasses-nonempty-invalid-task-pointer')
    isolated = len(rows)

    for count in (1, 4, 32):
        ram, banks, registers = fixture(render=True)
        target = tasks(ram, count)
        ram[0x7ded], ram[0x7dec], ram[0xf001] = 128, 255, 16
        ram[0x5da2] |= 128
        columns(ram, 5)
        sprite_state(ram, 4)
        begin = len(rows)
        ram, banks, result, registers, context = compare(ram, banks, registers, target=target, profile='render-then-carried-task-chain')
        for index in range(count):
            assert result['service_phase'] == 2 and registers[0] == 0x12340000 | index
            callback_registers = list(registers)
            callback_registers[0], callback_registers[13] = 0xabcdef00 | index, (0, 0xffffffff, 0x12345678)[index % 3]
            callback_registers[15] += 4  # Explicit host model of callback RTS consumption.
            ram, banks, result, registers, context = compare(ram, banks, callback_registers, mode='task',
                target=0xff100 + (index + 1) * 4 if index + 1 < count else None,
                status=index & 255, profile='carried-task-callback-register-mutations')
        assert result['service_phase'] == 0
        sequences.append({'profile': 'task-chain%d' % count, 'cases': len(rows) - begin,
            'callback_execution_not_claimed': True, 'input_stack_explicitly_advanced4': True})

    ram, banks, registers = fixture(render=True)
    ram[0x19], ram[0xf001] = 0x35, 16
    target = tasks(ram, 1)
    begin = len(rows)
    ram, banks, result, registers, context = compare(ram, banks, registers, target=target,
        profile='task-to-sound-wait-composed-chain')
    assert result['service_phase'] == 2
    callback_registers = list(registers)
    callback_registers[0], callback_registers[13] = 0xabcdef77, 0xffffffff
    callback_registers[15] += 4
    word(ram, 0xd68c, 1)
    struct.pack_into('>4H', ram, 0x4d82, 0x0455, 0x0566, 0x0677, 0x0788)
    struct.pack_into('>HH', ram, 0x4d8a, 0, 6)
    struct.pack_into('>HH', ram, 0x4d74, 1, 0)
    ram, banks, result, registers, context = compare(ram, banks, callback_registers,
        mode='task', status=1, profile='callback-return-then-sound-high-wait')
    assert result['service_phase'] == 3 and result['pending']['phase'] == 1
    for head, status in ((2, 255), (4, 2)):
        changed = bytearray(ram)
        word(changed, 0x4d74, head)
        word(changed, 0xd68c, 0x4567)
        ram, banks, result, registers, context = compare(changed, banks, registers,
            mode='sound', status=status, previous=result, context=context,
            profile='task-origin-sound-context-resume')
        assert result['pending']['phase'] == (2 if head == 2 else 0)
        assert ram[0xd68c:0xd68e] == b'\x45\x67' and state['external_reads'] == 0
    sequences.append({'profile': 'task-to-sound-wait-high-low-complete', 'cases': len(rows) - begin,
        'actual_sound_context_preserved': True, 'callback_execution_not_claimed': True})

    for render, tail in itertools.product((False, True), (0, 127)):
        ram, banks, registers = fixture(render=render)
        ram[0x19], ram[0xf001] = 0x35, 16
        word(ram, 0xd68c, 1)
        struct.pack_into('>4H', ram, 0x4d82, 0x0455, 0x0566, 0x0677, 0x0788)
        struct.pack_into('>HH', ram, 0x4d8a, 0, 6)
        struct.pack_into('>HH', ram, 0x4d74, (tail + 1) & 127, tail)
        if render:
            ram[0x7ded], ram[0x7dec] = 128, 255
            columns(ram, 3)
            sprite_state(ram, 4)
        begin = len(rows)
        ram, banks, result, registers, context = compare(ram, banks, registers, status=1, profile='prefix-then-sound-high-wait')
        assert result['service_phase'] == 3 and result['pending']['phase'] == 1
        for step, status in ((2, 255), (4, 1)):
            changed = bytearray(ram)
            word(changed, 0x4d74, (tail + step) & 127)
            word(changed, 0xd68c, 0x4567)
            ram, banks, result, registers, context = compare(changed, banks, registers, mode='sound', status=status,
                previous=result, context=context, profile='actual-native-sound-context-high-low-complete')
            assert ram[0xd68c:0xd68e] == b'\x45\x67' and state['external_reads'] == 0
            assert result['pending']['phase'] == (2 if step == 2 else 0)
        sequences.append({'profile': 'sound-chain-render%d-tail%d' % (render, tail), 'cases': len(rows) - begin,
            'actual_native_cpu_context_and_stack_preserved': True, 'prefix_and_display_enable_not_repeated': True})

    sentinel = b'previous-interrupt-service-output\0\xff'
    def reject(ram, banks, registers, label, selected_resources=None, mode='begin', pending=None, raw_regs=None):
        inp.write_bytes(ram)
        bank_in.write_bytes(banks)
        regs_in.write_bytes(struct.pack('>16I', *registers) if raw_regs is None else raw_regs)
        for path in (out, bank_out, ports):
            path.write_bytes(sentinel)
        args = [str(executable), mode, str(inp), str(bank_in), str(regs_in), str(out), str(bank_out), str(ports), '0', '0']
        if mode == 'sound':
            args += [str(pending[key]) for key in PENDING]
        if mode != 'sound':
            args += [str(path) for path in (resources if selected_resources is None else selected_resources)]
        actual = subprocess.run(args, capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, bank_out, ports)), (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    ram, banks, registers = fixture(render=True)
    word(ram, 0x7dea, 1)
    reject(ram, banks, registers, 'late-palette-counter-after-prefix')
    ram, banks, registers = fixture(render=True)
    sprite_state(ram, 4)
    reject(ram, banks, registers, 'missing-second-composition-after-rendering', resources[:1])
    ram, banks, registers = fixture(render=True)
    columns(ram, 15)
    sprite_state(ram, 4)
    struct.pack_into('>I', ram, 0x81c, 0x100001)
    reject(ram, banks, registers, 'late-invalid-task-after-all-renderers')
    ram, banks, registers = fixture(render=True)
    word(ram, 0x4d74, 128)
    word(ram, 0xd68c, 1)
    reject(ram, banks, registers, 'late-consumer-index-after-prefix-render-timer-production')
    ram, banks, registers = fixture()
    registers[13] = 0
    reject(ram, banks, registers, 'invalid-begin-a5')
    ram, banks, registers = fixture()
    for size in (0, 65535, 65537):
        reject(bytes(size), banks, registers, 'invalid-ram-size')
    for size in (0, 16383, 16385):
        reject(ram, bytes(size), registers, 'invalid-bank-size')
    for size in (0, 63, 65):
        reject(ram, banks, registers, 'invalid-register-size', raw_regs=bytes(size))
    reject(ram, banks, registers, 'invalid-sound-pending', mode='sound', pending=dict.fromkeys(PENDING, 0))
    inp.write_bytes(ram)
    bank_in.write_bytes(banks)
    regs_in.write_bytes(struct.pack('>16I', *registers))
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), 'begin', str(inp), str(bank_in), str(regs_in), str(alias), str(bank_out), str(ports), '0', '0'] + [str(path) for path in resources], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert bytes(cpu.mem_read(0x200000, 0xffff0)) == program[0x400000:0x4ffff0]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_addresses': [0xc8c, 0xd2a, WAIT],
        'entry_rom_offsets': [0xc8c, 0xd2a, WAIT], 'cases': len(rows), 'isolated_cases': isolated,
        'negative_cases': len(negatives), 'whole_ram_and_both_palette_banks_equal': True,
        'all_ordered_mmio_equal': True, 'unexpected_non_ram_non_stack_writes_rejected': True, 'task_boundary_all16_registers_and_stack_writes_equal': True,
        'sound_pending_and_status_read_counts_equal': True, 'output_carry_sequences': sequences,
        'resource_hashes': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in resources},
        'negative_results': negatives, 'results': rows,
        'scope': 'Continuous originalc8c through reentrant/return/task/sound-wait boundaries. '
            'NoROM patches. Includes counter saturation, credit BCD, normal/special palette, '
            'columns, realMS5C sprites, deferred tasks and sound producer/consumer. Native '
            'logical palette banks tracked while MMIO remains ordered. Begin display-bank '
            'state starts0; task/sound JSONnull means unchanged, physical selection remains '
            'carried. Task continuations use explicit host callback register changes and '
            'A7+4, without executing callbacks. Sound retains actual CPU context/stack; '
            'prefix/rendering/display-enable do not repeat. Final scratch registers, exception '
            'frames, natural interrupt scheduling, graphics/Z80 execution and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
