"""Compare originalf3c/f44 main callback stack boundaries and actual default RTS."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE = 0x100000
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/step_irq_envelope'
    folder = root / 'artifacts/main_callback_stack'
    folder.mkdir(parents=True, exist_ok=True)
    inp, stack_in, regs_in, out, stack_out, regs_out, ports_out, report = [folder / name for name in
        ('input.bin', 'stack.bin', 'registers.bin', 'cpp.bin', 'cpp.stack.bin', 'cpp.registers.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0xfff000, 0x1000)
    state = {'base': 0, 'size': 0, 'target': 0, 'default_calls': 0}
    writes, rows, sequences, negatives = [], [], [], []

    def write(cpu, access, address, size, value, user):
        if state['base'] <= address and address + size <= state['base'] + state['size']:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        else:
            raise ValueError('Unexpected native RAM/MMIO write: ' + repr((hex(address), size, value)))

    def code(cpu, address, size, user):
        if address == state['target']:
            cpu.emu_stop()
        elif address == 0x3dcc:
            state['default_calls'] += 1

    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_CODE, code)

    def fixture(stack_base=0x110000, size=256, offset=128, object_address=0x100100, target=0xff000):
        seed = b'ms5-main-callback-stack-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        stack = bytearray(hashlib.shake_256(seed + b'stack').digest(size))
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[8], registers[14], registers[15] = target, object_address, stack_base + offset
        # Deliberately disagree with incomingA0, which nativef3c actually uses.
        struct.pack_into('>II', ram, object_address - BASE + 0x76, 0xdeadbeef, 0xf1234567 ^ len(rows))
        return ram, stack, registers

    def compare(ram, stack, registers, mode, stack_base=0x110000, profile='matrix'):
        target = registers[8] if mode == 'main-call' else 0xf46 if mode == 'main-return' else int.from_bytes(stack[registers[15] - stack_base:registers[15] - stack_base + 4], 'big')
        entry = {'main-call': 0xf3c, 'main-return': 0xf44, 'callback': 0x3dcc}[mode]
        cpu.mem_write(BASE, bytes(ram))
        cpu.mem_write(stack_base, bytes(stack))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        state.update(base=stack_base, size=len(stack), target=target)
        writes.clear()
        before_default = state['default_calls']
        cpu.emu_start(entry, target, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == target
        expected_ram = bytes(cpu.mem_read(BASE, 65536))
        expected_stack = bytes(cpu.mem_read(stack_base, len(stack)))
        after = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        assert expected_ram == ram
        if mode == 'main-call':
            assert writes == [(4, registers[15] - 4, registers[14]), (4, registers[15] - 8, 0xf44)]
            expected_registers = list(registers)
            expected_registers[14] = int.from_bytes(ram[registers[14] - BASE + 0x7a:registers[14] - BASE + 0x7e], 'big')
            expected_registers[15] -= 8
            assert after == expected_registers
        else:
            assert not writes and expected_stack == stack
            expected_registers = list(registers)
            if mode == 'main-return':
                offset = registers[15] - stack_base
                expected_registers[14] = int.from_bytes(stack[offset:offset + 4], 'big')
            else:
                assert state['default_calls'] == before_default + 1
            expected_registers[15] += 4
            assert after == expected_registers
        result = {'next_pc': target, 'bios_handoff': False, 'stack_writes': [list(event) for event in writes]}
        inp.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, stack_out, regs_out, ports_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), mode, str(inp), str(stack_in), str(regs_in), str(out), str(stack_out), str(regs_out), str(ports_out), hex(stack_base)], capture_output=True, text=True)
        if actual.returncode or out.read_bytes() != expected_ram or stack_out.read_bytes() != expected_stack or regs_out.read_bytes() != struct.pack('>16I', *after) or ports_out.read_bytes() or json.loads(actual.stdout) != result:
            raise ValueError(repr((len(rows), profile, mode, result, actual.stdout, actual.stderr)))
        rows.append({'profile': profile, 'mode': mode, 'stack_base': stack_base, 'input_sp': registers[15],
            'input_a0': registers[8], 'input_a6': registers[14], 'result_a6': after[14], 'result': result,
            'ram_sha256': hashlib.sha256(expected_ram).hexdigest(), 'stack_sha256': hashlib.sha256(expected_stack).hexdigest(),
            'registers_sha256': hashlib.sha256(struct.pack('>16I', *after)).hexdigest(), 'mmio_writes': 0})
        return bytearray(expected_ram), bytearray(expected_stack), after

    boundaries = ((0x110000, 128, 8), (0x110000, 128, 10), (0x1fe000, 128, 64), (0xfff000, 4096, 4094))
    for object_address, boundary, target in itertools.product((0x100000, 0x100002, 0x100100, 0x10ff82),
            boundaries, (0xff000, 0x3dcc, 0x100200)):
        stack_base, size, offset = boundary
        ram, stack, registers = fixture(stack_base, size, offset, object_address, target)
        compare(ram, stack, registers, 'main-call', stack_base, 'object-and-stack-boundaries-input-a0-source')
    for value in range(256):
        stack_base, size, offset = ((0x110000, 128, 0), (0x110000, 128, 2), (0xfff000, 4096, 0xffa))[value % 3]
        ram, stack, registers = fixture(stack_base, size, offset)
        saved_a6 = 0xffffffff if value == 255 else (0x80000000 | ((value * 0x01010101) & 0x7fffffff))
        struct.pack_into('>I', stack, offset, saved_a6)
        registers[14] = 0xdeadbeef
        compare(ram, stack, registers, 'main-return', stack_base, 'all-saved-a6-byte-patterns-word-aligned-pop')
    isolated = len(rows)
    for index in range(16):
        ram, stack, registers = fixture(target=0x3dcc)
        original_object = registers[14]
        begin = len(rows)
        ram, stack, registers = compare(ram, stack, registers, 'main-call', profile='carried-main-call-default-rts-main-return')
        host_registers = [value ^ (0xdead0000 | index) for value in registers]
        host_registers[15] = registers[15]
        ram, stack, registers = compare(ram, stack, host_registers, 'callback', profile='actual-default-rts-after-host-register-mutations')
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == 0xf44
        ram, stack, registers = compare(ram, stack, registers, 'main-return', profile='carried-main-call-default-rts-main-return')
        assert registers[14] == original_object
        sequences.append({'cases': len(rows) - begin, 'saved_object_a6_restored': True,
            'actual_default_rts_executed': True, 'host_callback_register_mutations_explicit': True})

    sentinel = b'previous-main-callback-output\0\xff'
    def reject(ram, stack, registers, mode, stack_base, label):
        inp.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, stack_out, regs_out, ports_out):
            path.write_bytes(sentinel)
        actual = subprocess.run([str(executable), mode, str(inp), str(stack_in), str(regs_in), str(out), str(stack_out), str(regs_out), str(ports_out), hex(stack_base)], capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, stack_out, regs_out, ports_out)), (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    ram, stack, registers = fixture()
    for object_address in (0xffffe, 0x100001, 0x10ff84, 0xffffffff):
        bad = list(registers)
        bad[14] = object_address
        reject(ram, stack, bad, 'main-call', 0x110000, 'invalid-object-address')
    for sp in (0x110006, 0x110009, 0x110102, 0xffffffff):
        bad = list(registers)
        bad[15] = sp
        reject(ram, stack, bad, 'main-call', 0x110000, 'invalid-main-call-sp')
    for sp in (0x10fffe, 0x110001, 0x1100fe, 0xfffffc):
        bad = list(registers)
        bad[15] = sp
        reject(ram, stack, bad, 'main-return', 0x110000, 'invalid-main-return-sp')
    for size in (0, 65535, 65537):
        reject(bytes(size), stack, registers, 'main-call', 0x110000, 'invalid-ram-size')
    for stack_base in (0x100000, 0x110001, 0xfffffe):
        reject(ram, stack, registers, 'main-call', stack_base, 'invalid-stack-span')
    inp.write_bytes(ram)
    stack_in.write_bytes(stack)
    regs_in.write_bytes(struct.pack('>16I', *registers))
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), 'main-call', str(inp), str(stack_in), str(regs_in), str(alias), str(stack_out), str(regs_out), str(ports_out), '0x110000'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert state['default_calls'] == 16
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_addresses': [0xf3c, 0xf44],
        'entry_rom_offsets': [0xf3c, 0xf44], 'cases': len(rows), 'isolated_cases': isolated,
        'negative_cases': len(negatives), 'whole_ram_stack_and_all16_registers_equal': True,
        'chronological_stack_writes_equal': True, 'mmio_writes_zero': True,
        'incoming_a0_used_instead_of_object_callback_pointer': True,
        'output_carry_sequences': sequences, 'negative_results': negatives, 'results': rows,
        'scope': 'Originalf3c saves callerA6, loads object+7a context and enters incomingA0; '
            'object+76 deliberately differs. Originalf44 restores savedA6 and stops before '
            'palette helperf46. FullRAM/fullstack/all16 registers and exact stack writes '
            'compared, with zeroMMIO. Carried cases execute actual default3dcc RTS after '
            'explicit host register mutations, then restore callerA6. Other callback bodies, '
            'palette helper execution, CPU flags/RTE and physical timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
