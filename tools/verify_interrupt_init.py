"""Compare nativec42/3dce and connect actual default3dcc to IRQ/service entry."""
import hashlib
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

BASE, RETURN, STACK_BASE, STACK_SP = 0x100000, 0xff000, 0x110000, 0x110100
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    initializer, envelope, service = [root / 'build' / name for name in
        ('initialize_interrupt', 'step_irq_envelope', 'step_interrupt')]
    folder = root / 'artifacts/interrupt_init'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, stack_in, stack_out, regs_in, regs_out, ports_out, banks_in, banks_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'stack.bin', 'cpp.stack.bin', 'registers.bin', 'cpp.registers.bin', 'cpp.ports.bin', 'banks.bin', 'cpp.banks.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address, length in ((0x2f0000, 0x10000), (0x300000, 0x1000), (0x320000, 0x1000), (0x3a0000, 0x1000), (0x3c0000, 0x1000), (0xfff000, 0x1000)):
        cpu.mem_map(address, length)
    ports, stack_writes, rows, integrations, callbacks, negatives = [], [], [], [], [], []
    state = {'stack_base': 0x1fe000, 'stack_size': 4096, 'reads': 0,
        'default_callbacks': 0, 'service_entry': None, 'stop_pc': None}

    def write(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        if state['stack_base'] <= address and address + size <= state['stack_base'] + state['stack_size']:
            stack_writes.append((size, address, value))
        elif BASE <= address and address + size <= BASE + 65536:
            pass
        elif address in (0x3c000c, 0x300001, 0x320000, 0x3a0001, 0x2ffff0, 0x2ffff2):
            ports.append((size, address, value))
        else:
            raise ValueError('Unexpected native write: ' + repr((hex(address), size, value)))

    def read(cpu, access, address, size, value, user):
        assert address == 0x320000 and size == 1
        state['reads'] += 1
        cpu.mem_write(address, b'\0')

    def code(cpu, address, size, user):
        if address == state['stop_pc']:
            cpu.emu_stop()
            return
        if address == 0x3dcc:
            state['default_callbacks'] += 1
        elif address == 0xc8c:
            state['service_entry'] = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]

    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_MEM_READ, read, begin=0x320000, end=0x320000)
    cpu.hook_add(UC_HOOK_CODE, code)

    def fixture():
        seed = b'ms5-interrupt-init-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[13], registers[15] = 0x108000, 0x1feffc
        return ram, registers

    def set_cpu(ram, registers, stack_base=0x1fe000, stack_size=4096):
        cpu.mem_write(BASE, bytes(ram))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        state.update(stack_base=stack_base, stack_size=stack_size, reads=0, service_entry=None, stop_pc=None)
        ports.clear()
        stack_writes.clear()

    def run_init(ram, registers, mode, profile):
        set_cpu(ram, registers)
        cpu.mem_write(registers[15], RETURN.to_bytes(4, 'big'))
        cpu.emu_start(0xc42 if mode == 'state' else 0x3dce, RETURN, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        after = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        expected_registers = list(registers)
        expected_registers[15] += 4
        if mode == 'callbacks':
            expected_registers[8] = 0x3dcc
        assert after == expected_registers and not ports and not stack_writes and state['reads'] == 0
        if mode == 'state':
            assert expected[0x18] == ram[0x18]
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        actual = subprocess.run([str(initializer), mode, str(inp), str(out), hex(registers[8])], capture_output=True, text=True)
        assert not actual.returncode and out.exists() and out.read_bytes() == expected and json.loads(actual.stdout) == {'a0': after[8]}, (profile, mode, actual.stdout, actual.stderr)
        rows.append({'profile': profile, 'mode': mode, 'initial_flag4d91': ram[0x4d91],
            'latched18': ram[0x18], 'initial_a0': registers[8], 'result_a0': after[8],
            'other_registers_preserved_except_rts_a7': True, 'mmio_writes': 0,
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected), after

    for flag in range(256):
        ram, registers = fixture()
        ram[0x4d91] = flag
        ram[0x16], ram[0x17], ram[0x19], ram[0x1a], ram[0x1b], ram[0x18] = [flag] * 6
        run_init(ram, registers, 'state', 'all256-state-sentinel-values')
        run_init(ram, registers, 'callbacks', 'all256-callback-flag-values')
    for index in range(16):
        ram, registers = fixture()
        state_ram, state_regs = run_init(ram, registers, 'state', 'idempotence-and-commuting-initializers')
        repeated, ignored = run_init(state_ram, state_regs, 'state', 'state-idempotence')
        assert repeated == state_ram
        first_order, first_regs = run_init(state_ram, state_regs, 'callbacks', 'state-then-callbacks')
        callback_ram, callback_regs = run_init(ram, registers, 'callbacks', 'idempotence-and-commuting-initializers')
        repeated, ignored = run_init(callback_ram, callback_regs, 'callbacks', 'callbacks-idempotence')
        assert repeated == callback_ram
        second_order, second_regs = run_init(callback_ram, callback_regs, 'state', 'callbacks-then-state')
        assert first_order == second_order and first_regs == second_regs
    initializer_isolated = len(rows)

    def run_envelope(ram, stack, registers, mode, stack_base=STACK_BASE, target=0x3dcc):
        set_cpu(ram, registers, stack_base, len(stack))
        cpu.mem_write(stack_base, bytes(stack))
        before_callbacks = state['default_callbacks']
        state['stop_pc'] = target
        try:
            cpu.emu_start(0x20c if mode == 'begin' else 0x3dcc, target, count=1000)
        except unicorn.UcError as error:
            raise ValueError(repr((mode, hex(target), hex(cpu.reg_read(m68k_const.UC_M68K_REG_PC)), ram[0xfd80], ram[6:10].hex(), [hex(cpu.reg_read(reg)) for reg in REGS], str(error)))) from error
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == target
        expected_ram = bytes(cpu.mem_read(BASE, 65536))
        expected_stack = bytes(cpu.mem_read(stack_base, len(stack)))
        after = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        result = {'next_pc': target, 'bios_handoff': False, 'stack_writes': [list(entry) for entry in stack_writes]}
        if mode == 'callback':
            assert state['default_callbacks'] == before_callbacks + 1 and not ports and not stack_writes
            assert expected_ram == ram and expected_stack == stack
        inp.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, stack_out, regs_out, ports_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(envelope), mode, str(inp), str(stack_in), str(regs_in), str(out), str(stack_out), str(regs_out), str(ports_out), hex(stack_base)], capture_output=True, text=True)
        assert not actual.returncode and out.read_bytes() == expected_ram and stack_out.read_bytes() == expected_stack and regs_out.read_bytes() == struct.pack('>16I', *after) and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (mode, actual.stdout, actual.stderr)
        callbacks.append({'mode': mode, 'target': target, 'stack_base': stack_base,
            'input_sp': registers[15], 'actual_default_rts_executed': mode == 'callback',
            'ram_sha256': hashlib.sha256(expected_ram).hexdigest(), 'stack_sha256': hashlib.sha256(expected_stack).hexdigest(),
            'registers_sha256': hashlib.sha256(struct.pack('>16I', *after)).hexdigest()})
        return bytearray(expected_ram), bytearray(expected_stack), after

    for index in range(16):
        ram, registers = fixture()
        # Safe unrelated sound inputs remain explicit; initializers do not set them.
        ram[0xfd80], ram[0x14], ram[0xfd82], ram[0xf001] = 128, 0, 0, (16 if index & 1 else 0)
        ram[0x4d7b], ram[0xf003] = 0, 0
        struct.pack_into('>HH', ram, 0x4d74, 0, 0)
        struct.pack_into('>H', ram, 0xd68c, 0)
        ram, registers = run_init(ram, registers, 'state', 'initializer-to-actual-default-callback-service')
        ram, registers = run_init(ram, registers, 'callbacks', 'initializer-to-actual-default-callback-service')
        registers[15] = STACK_SP
        stack = bytearray(hashlib.shake_256(b'init-integration-stack:' + bytes([index])).digest(512))
        ram, stack, registers = run_envelope(ram, stack, registers, 'begin')
        assert registers[15] == STACK_SP - 68
        ram, stack, registers = run_envelope(ram, stack, registers, 'callback', target=0x23c)
        assert registers[15] == STACK_SP - 64
        # Continue original23c JSRc8c and stop at242 before its BIOS call.
        initial_service_ram = bytes(ram)
        ports.clear()
        stack_writes.clear()
        state.update(reads=0, service_entry=None, stop_pc=0x242)
        cpu.emu_start(0x23c, 0x242, count=100000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == 0x242 and state['reads'] == 1
        expected_ram = bytes(cpu.mem_read(BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        service_registers = state['service_entry']
        assert service_registers is not None and service_registers[15] == STACK_SP - 68
        assert expected_ram[0x16] == 1 and expected_ram[0x17] == 2 and expected_ram[0x19] == 0
        assert expected_ram[0x18] == initial_service_ram[0x18]
        banks = hashlib.shake_256(b'init-integration-banks:' + bytes([index])).digest(16384)
        inp.write_bytes(initial_service_ram)
        banks_in.write_bytes(banks)
        regs_in.write_bytes(struct.pack('>16I', *service_registers))
        for path in (out, banks_out, ports_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(service), 'begin', str(inp), str(banks_in), str(regs_in), str(out), str(banks_out), str(ports_out), '0', '0'], capture_output=True, text=True)
        result = {'service_phase': 0, 'display_bank': 0, 'sound_reads': 1, 'task_registers': [0] * 16,
            'task': {'next_pc': 0, 'restored': False, 'stack_address': [0, 0], 'stack_value': [0, 0]},
            'pending': dict.fromkeys(('kind', 'phase', 'low', 'cursor', 'command', 'tail', 'next'), 0)}
        assert not actual.returncode and out.read_bytes() == expected_ram and banks_out.read_bytes() == banks and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (index, actual.stdout, actual.stderr)
        integrations.append({'index': index, 'actual_default_callback_executed': True,
            'native23c_jsr_c8c_until242_before_bios': True, 'counter': 1, 'gate': 2,
            'latched18_preserved': expected_ram[0x18] == initial_service_ram[0x18],
            'ram_sha256': hashlib.sha256(expected_ram).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for stack_base, offset, target in ((0x110000, 0, 0xff000), (0x110000, 2, 0xff002),
            (0xfff000, 0xffa, 0xfffffc)):
        ram, registers = fixture()
        stack = bytearray(4096)
        registers[15] = stack_base + offset
        struct.pack_into('>I', stack, offset, target)
        run_envelope(ram, stack, registers, 'callback', stack_base, target)

    sentinel = b'previous-interrupt-init-output\0\xff'
    for mode in ('state', 'callbacks'):
        for size in (0, 65535, 65537):
            inp.write_bytes(bytes(size))
            out.write_bytes(sentinel)
            actual = subprocess.run([str(initializer), mode, str(inp), str(out), '0'], capture_output=True, text=True)
            assert actual.returncode and out.read_bytes() == sentinel
            negatives.append({'failure': 'invalid-ram-size', 'mode': mode, 'outputs_preserved': True, 'original_executed': False})
    ram, registers = fixture()
    inp.write_bytes(ram)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(initializer), 'state', str(inp), str(alias), '0'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    stack = bytes(128)
    stack_in.write_bytes(stack)
    for sp in (0x10fffe, 0x110001, 0x11007e, 0xfffffc):
        registers[15] = sp
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, stack_out, regs_out, ports_out):
            path.write_bytes(sentinel)
        actual = subprocess.run([str(envelope), 'callback', str(inp), str(stack_in), str(regs_in), str(out), str(stack_out), str(regs_out), str(ports_out), '0x110000'], capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, stack_out, regs_out, ports_out))
        negatives.append({'failure': 'invalid-default-callback-stack', 'outputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_addresses': [0xc42, 0x3dce],
        'entry_rom_offsets': [0xc42, 0x3dce], 'initializer_cases': len(rows), 'isolated_initializer_cases': initializer_isolated,
        'envelope_callback_cases': len(callbacks), 'service_integration_cases': len(integrations),
        'negative_cases': len(negatives), 'whole_ram_a0_and_unchanged_other_registers_equal': True,
        'initializers_zero_mmio': True, 'idempotence_and_commuting_orders_checked': True,
        'latched18_preserved_by_state_initializer': True, 'actual_default_callback_rts_executed': True,
        'callback_results': callbacks, 'service_integrations': integrations, 'negative_results': negatives,
        'results': rows,
        'scope': 'Originalc42 state and3dce callback initializer throughRTS, with fullRAM '
            'and A0 verified and other registers unchanged except RTS stack consumption. '
            'All256 callbackflags and state sentinels, idempotence/commuting order checked. '
            'Native20c enters actual3dcc RTS then original23c JSRc8c completes at242 before '
            'BIOS call; envelope/callback/service CLIs compared separately with same state. '
            'Unrelated sound fields explicitly constrained. No BIOS or RTE execution, '
            'exception frame, natural scheduling or physical device timing claimed.'}, indent=2) + '\n')
    print(json.dumps({'initializer_cases': len(rows), 'envelope_callback_cases': len(callbacks),
        'service_integration_cases': len(integrations), 'negative_cases': len(negatives),
        'report': str(report), 'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
