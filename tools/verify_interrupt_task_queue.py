"""Compare nativec64 deferred task queue and continuous nativece2 LIFO restore."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, IMMEDIATE = 0x100000, 0xff000
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable, restore_cli = root / 'build/queue_interrupt_task', root / 'build/restore_interrupt_task'
    folder = root / 'artifacts/interrupt_task_queue'
    folder.mkdir(parents=True, exist_ok=True)
    inp, regs_in, out, regs_out, ports, report = [folder / name for name in
        ('input.bin', 'registers.bin', 'cpp.bin', 'cpp.registers.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address, length in ((0x2f0000, 0x10000), (0x300000, 0x1000), (0xfff000, 0x1000)):
        cpu.mem_map(address, length)
    stack_writes, hardware, rows, negatives, restore_rows = [], [], [], [], []
    state = {'stack_addresses': ()}

    def hook(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        if address in state['stack_addresses']:
            assert size == 4
            stack_writes.append((address, value))
        elif address in (0x300001, 0x2ffff2, 0x2ffff0):
            hardware.append((size, address, value))

    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)

    def fixture(pointer, sp=0x1feffc):
        seed = b'ms5-interrupt-task-queue-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[15] = sp
        struct.pack_into('>I', ram, 0x81c, pointer)
        return ram, registers

    def set_cpu(ram, registers):
        cpu.mem_write(BASE, bytes(ram))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        stack_writes.clear()
        hardware.clear()

    def compare(ram, registers, deferred=0xff100, profile='matrix'):
        pointer = int.from_bytes(ram[0x81c:0x820], 'big')
        queued = pointer > 0x10001c
        sp = registers[15]
        set_cpu(ram, registers)
        cpu.mem_write(sp, struct.pack('>II', IMMEDIATE, deferred))
        state['stack_addresses'] = (sp - 4, sp + 4)
        cpu.emu_start(0xc64, IMMEDIATE, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == IMMEDIATE
        expected = bytes(cpu.mem_read(BASE, 65536))
        native_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        expected_regs = struct.pack('>16I', *native_registers)
        assert native_registers[:15] == registers[:15] and native_registers[15] == sp + 8
        assert stack_writes == [(sp - 4, registers[14]), (sp + 4, IMMEDIATE)] and not hardware
        for address, value in stack_writes:
            assert bytes(cpu.mem_read(address, 4)) == value.to_bytes(4, 'big')
        if not queued:
            assert expected == ram
        result = {'next_pc': IMMEDIATE, 'queued': queued,
            'stack_address': [event[0] for event in stack_writes], 'stack_value': [event[1] for event in stack_writes]}
        inp.write_bytes(ram)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, regs_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), str(inp), str(regs_in), str(out), str(regs_out), hex(IMMEDIATE), hex(deferred)], capture_output=True, text=True)
        if actual.returncode or not out.exists() or out.read_bytes() != expected or not regs_out.exists() or regs_out.read_bytes() != expected_regs or json.loads(actual.stdout) != result:
            raise ValueError(repr((len(rows), profile, hex(pointer), result, actual.stdout, actual.stderr)))
        rows.append({'profile': profile, 'queue_pointer': pointer, 'input_stack': sp,
            'deferred_pc': deferred, 'result': result, 'input_ram_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'registers_sha256': hashlib.sha256(expected_regs).hexdigest()})
        return expected, native_registers

    for slot, variant in itertools.product(range(32), range(4)):
        pointer = 0x10081c - 64 * slot
        ram, registers = fixture(pointer, (0x110004, 0x110006, 0x1feffc, 0xfffff4)[variant])
        compare(ram, registers, deferred=0xff100 + slot * 4, profile='all32-canonical-queue-slots-all-stack-boundaries')
    for pointer in (0x100040, 0x100042, 0x10081a):
        ram, registers = fixture(pointer)
        compare(ram, registers, profile='word-aligned-noncanonical-full-frame')
    for pointer, sp in itertools.product((0, 1, 0xfffff, 0x100000, 0x10001b, 0x10001c), (0x110004, 0xfffff4)):
        ram, registers = fixture(pointer, sp)
        compare(ram, registers, profile='unsigned-full-queue-skips-frame-validation')
    isolated = len(rows)

    # Fill exactly32 slots, retaining wholeRAM across calls; then use actualce2
    # on that same RAM and compare the separate restore CLI at every LIFO step.
    ram, registers = fixture(0x10081c)
    saved = []
    for index in range(32):
        registers = list(struct.unpack('>16I', hashlib.shake_256(b'lifo-registers:' + index.to_bytes(4, 'big')).digest(64)))
        registers[0], registers[13], registers[15] = 0xabc00000 | index, 0x108000, 0x1feffc
        deferred = 0xff100 + index * 4
        saved.append((registers[:], deferred))
        ram, ignored = compare(ram, registers, deferred, '32-carried-queue-pushes')
    assert int.from_bytes(ram[0x81c:0x820], 'big') == 0x10001c
    compare(ram, registers, 0xff200, 'full-queue-after32-pushes-preserves-ram')
    for index in reversed(range(32)):
        incoming = [0xaabbccdd] * 16
        incoming[13], incoming[15] = 0x108000, 0x1fcffc
        expected_saved, deferred = saved[index]
        set_cpu(ram, incoming)
        sp = incoming[15]
        state['stack_addresses'] = (sp - 4, sp - 8)
        cpu.emu_start(0xce2, deferred, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == deferred
        expected = bytes(cpu.mem_read(BASE, 65536))
        native_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        expected_regs = struct.pack('>16I', *native_registers)
        expected_ports = b''.join(struct.pack('>BII', *event) for event in hardware)
        assert native_registers[:15] == expected_saved[:15] and native_registers[15] == sp - 4
        assert stack_writes == [(sp - 4, 0xd2a), (sp - 8, deferred)]
        for address, value in stack_writes:
            assert bytes(cpu.mem_read(address, 4)) == value.to_bytes(4, 'big')
        result = {'next_pc': deferred, 'restored': True, 'stack_address': [sp - 4, sp - 8],
            'stack_value': [0xd2a, deferred], 'writes': len(hardware)}
        inp.write_bytes(ram)
        regs_in.write_bytes(struct.pack('>16I', *incoming))
        for path in (out, regs_out, ports):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(restore_cli), str(inp), str(regs_in), str(out), str(regs_out), str(ports)], capture_output=True, text=True)
        assert not actual.returncode and out.read_bytes() == expected and regs_out.read_bytes() == expected_regs and ports.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (index, actual.stdout, actual.stderr)
        restore_rows.append({'lifo_index': index, 'deferred_pc': deferred, 'all_registers_restored': True,
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'registers_sha256': hashlib.sha256(expected_regs).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        ram = expected
    assert int.from_bytes(ram[0x81c:0x820], 'big') == 0x10081c

    sentinel = b'previous-task-queue-output\0\xff'
    def reject(ram, registers, label, raw_regs=None):
        inp.write_bytes(ram)
        regs_in.write_bytes(struct.pack('>16I', *registers) if raw_regs is None else raw_regs)
        for path in (out, regs_out):
            path.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(regs_in), str(out), str(regs_out), hex(IMMEDIATE), '0xff100'], capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, regs_out))
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    for pointer in (0x10001d, 0x10001e, 0x10003e, 0x100041, 0x10081e, 0xffffffff):
        ram, registers = fixture(pointer)
        reject(ram, registers, 'invalid-used-frame-pointer')
    for sp in (0x110002, 0x110005, 0xfffff6, 0xffffffff):
        ram, registers = fixture(0x10081c, sp)
        reject(ram, registers, 'invalid-external-stack')
    ram, registers = fixture(0x10081c)
    for size in (0, 65535, 65537):
        reject(bytes(size), registers, 'invalid-ram-size')
    for size in (0, 63, 65):
        reject(ram, registers, 'invalid-register-file-size', bytes(size))
    inp.write_bytes(ram)
    regs_in.write_bytes(struct.pack('>16I', *registers))
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), str(inp), str(regs_in), str(alias), str(regs_out), hex(IMMEDIATE), '0xff100'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': 0xc64,
        'entry_rom_offset': 0xc64, 'cases': len(rows), 'isolated_cases': isolated, 'restore_cases': len(restore_rows),
        'negative_cases': len(negatives), 'whole_65536_byte_ram_and_all16_registers_equal': True,
        'actual_external_stack_writes_and_memory_equal': True, 'queue_producer_hardware_writes_zero': True,
        'carried32_pushes_and32_lifo_restores': True, 'negative_results': negatives,
        'restore_results': restore_rows, 'results': rows,
        'scope': 'Originalc64 task enqueue throughc8a immediate return, stopped before '
            'callback execution. WholeRAM, all16 registers and actual external stack writes '
            'compared; noA5 constraint on enqueue. All32 slots, word-aligned frame boundaries '
            'and unsigned full-queue skips checked. SameRAM filled with32 distinct tasks then '
            'nativece2 and separate restore CLI compared in exact LIFO order. Invalid frames '
            'and stacks are unsupported API inputs. Callback execution, exception flags, '
            'natural interrupt scheduling and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'restore_cases': len(restore_rows), 'negative_cases': len(negatives),
        'report': str(report), 'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
