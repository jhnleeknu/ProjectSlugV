"""Compare native29c/2b6 raster IRQ envelopes with explicit external stack."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, CALLBACK, INACTIVE, FINISH, AFTER_CALLBACK = 0x100000, 0x3dcc, 0x2d6, 0x2cc, 0x2b6
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index))
        for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/step_irq_envelope'
    folder = root / 'artifacts/raster_irq'
    folder.mkdir(parents=True, exist_ok=True)
    paths = [folder / name for name in ('input.bin', 'stack.bin', 'registers.bin', 'cpp.bin',
             'cpp.stack.bin', 'cpp.registers.bin', 'cpp.ports.bin')]
    ram_in, stack_in, regs_in, ram_out, stack_out, regs_out, ports_out = paths
    outputs = paths[3:]
    report = folder / 'verification.json'
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.mem_map(0xfff000, 0x1000)
    state = {'base': 0, 'size': 0, 'boundary': 0}
    stack_writes, ports, rows, negatives, sequences = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        if state['base'] <= address and address + size <= state['base'] + state['size']:
            stack_writes.append((size, address, value))
        elif address in (0x3c000c, 0x3c0000):
            assert size == 2
            ports.append((size, address, value))
        elif not (BASE <= address and address + size <= BASE + 65536):
            raise ValueError('Unexpected native raster write: ' + repr((hex(address), size, value)))

    def code_hook(cpu, address, size, user):
        if address == state['boundary']:
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in (CALLBACK, INACTIVE, FINISH, AFTER_CALLBACK):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(stack_base=0x110000, stack_size=512, sp_offset=256):
        seed = b'ms5-raster-irq-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        stack = bytearray(hashlib.shake_256(seed + b'stack').digest(stack_size))
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[15] = stack_base + sp_offset
        struct.pack_into('>I', ram, 10, CALLBACK)
        return ram, stack, registers

    def finish_frame(stack, registers, stack_base, vram, saved_a5):
        struct.pack_into('>HI', stack, registers[15] - stack_base, vram, saved_a5)

    def arguments(mode, stack_base):
        return [str(executable), mode, *(str(path) for path in paths), hex(stack_base)]

    def compare(ram, stack, registers, mode='raster-begin', stack_base=0x110000, profile='matrix'):
        if mode == 'raster-begin':
            entry, boundary = 0x29c, CALLBACK if ram[0xfd80] & 128 else INACTIVE
        elif mode == 'raster-finish':
            entry, boundary = 0x2b6, FINISH
        else:
            entry, boundary = CALLBACK, AFTER_CALLBACK
        cpu.mem_write(BASE, bytes(ram))
        if stack:
            cpu.mem_write(stack_base, bytes(stack))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        state.update(base=stack_base, size=len(stack), boundary=boundary)
        stack_writes.clear()
        ports.clear()
        # Explicit code hooks stop before RTE/callback even when a cached
        # Unicorn translation block crosses the emu_start until address.
        cpu.emu_start(entry, 0xffffff, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == boundary
        expected_ram = bytes(cpu.mem_read(BASE, 65536))
        expected_stack = bytes(cpu.mem_read(stack_base, len(stack))) if stack else b''
        expected_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        if mode == 'raster-begin':
            assert expected_ram == ram
            if boundary == INACTIVE:
                assert expected_stack == stack and expected_registers == registers and not stack_writes
                assert ports == [(2, 0x3c000c, 2)]
            else:
                vram = int.from_bytes(ram[0x4d8e:0x4d90], 'big')
                assert stack_writes == [(4, registers[15] - 4, registers[13]),
                    (2, registers[15] - 6, vram), (4, registers[15] - 10, AFTER_CALLBACK)]
                assert expected_registers == registers[:13] + [CALLBACK, registers[14], registers[15] - 10]
                assert not ports
        elif mode == 'raster-finish':
            at = registers[15] - stack_base
            vram, saved_a5 = struct.unpack_from('>HI', stack, at)
            model_ram = bytearray(ram)
            struct.pack_into('>H', model_ram, 0x4d8e, vram)
            assert expected_ram == model_ram and expected_stack == stack and not stack_writes
            assert expected_registers == registers[:13] + [saved_a5, registers[14], registers[15] + 6]
            assert ports == [(2, 0x3c000c, 2), (2, 0x3c0000, vram)]
        else:
            assert expected_ram == ram and expected_stack == stack and not stack_writes and not ports
            assert expected_registers == registers[:15] + [registers[15] + 4]
        result = {'next_pc': boundary, 'bios_handoff': False,
                  'stack_writes': [list(event) for event in stack_writes]}
        ram_in.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in outputs:
            path.unlink(missing_ok=True)
        actual = subprocess.run(arguments(mode, stack_base), capture_output=True, text=True)
        expected_files = (expected_ram, expected_stack, struct.pack('>16I', *expected_registers),
                          b''.join(struct.pack('>BII', *event) for event in ports))
        if actual.returncode or any(not path.exists() or path.read_bytes() != data
                for path, data in zip(outputs, expected_files)) or json.loads(actual.stdout) != result:
            raise ValueError(repr((len(rows), profile, mode, hex(stack_base), hex(registers[15]),
                                  result, actual.stdout, actual.stderr)))
        rows.append({'profile': profile, 'mode': mode, 'stack_base': stack_base,
            'stack_size': len(stack), 'input_sp': registers[15], 'fd80': ram[0xfd80],
            'ports': len(ports), 'result': result,
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected_ram).hexdigest(),
            'stack_sha256': hashlib.sha256(expected_stack).hexdigest(),
            'registers_sha256': hashlib.sha256(expected_files[2]).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_files[3]).hexdigest()})
        return bytearray(expected_ram), bytearray(expected_stack), expected_registers

    for flag in range(256):
        ram, stack, registers = fixture()
        ram[0xfd80] = flag
        compare(ram, stack, registers, profile='all256-fd80-flags')
    for vram, saved_a5, stack_base in itertools.product(
            (0, 1, 0x7fff, 0x8000, 0xff00, 0xffff),
            (0, 0x108000, 0x12345678, 0xffffffff), (0x110000, 0x1fe000, 0xfff000)):
        ram, stack, registers = fixture(stack_base, 128, 0)
        finish_frame(stack, registers, stack_base, vram, saved_a5)
        compare(ram, stack, registers, 'raster-finish', stack_base, 'saved-vram-a5-boundaries')
    for stack_base, size, offset in ((0x110000, 10, 10), (0xfff000, 4096, 4094), (0xfffff4, 10, 10)):
        ram, stack, registers = fixture(stack_base, size, offset)
        ram[0xfd80] = 128
        compare(ram, stack, registers, stack_base=stack_base, profile='begin-minimum-maximum-sp')
    for stack_base, size, offset in ((0x110000, 6, 0), (0xfff000, 4096, 4088), (0xfffff8, 6, 0)):
        ram, stack, registers = fixture(stack_base, size, offset)
        finish_frame(stack, registers, stack_base, 0xffff, 0xffffffff)
        compare(ram, stack, registers, 'raster-finish', stack_base, 'finish-minimum-maximum-sp')
    for sp in (0, 1, 0xffffffff):
        ram, stack, registers = fixture(stack_size=0, sp_offset=0)
        ram[0xfd80], registers[15] = 0, sp
        compare(ram, stack, registers, profile='inactive-unused-stack-arbitrary-sp')
    ram, stack, registers = fixture(0xfffffe, 2, 0)
    ram[0xfd80], registers[15] = 0, 0xffffffff
    compare(ram, stack, registers, stack_base=0xfffffe,
            profile='inactive-highest-valid-stack-base')
    isolated = len(rows)
    for index in range(16):
        ram, stack, registers = fixture(sp_offset=384)
        ram[0xfd80] = 0x80 | index
        original_a5 = registers[13]
        original_vram = 0xabcd ^ index
        struct.pack_into('>H', ram, 0x4d8e, original_vram)
        start = len(rows)
        ram, stack, registers = compare(ram, stack, registers, profile='carried-default-rts-host-register-mutations')
        ram, stack, registers = compare(ram, stack, registers, 'callback', profile='carried-default-rts-host-register-mutations')
        assert registers[15] == 0x110000 + 384 - 6
        host_registers = [value ^ (0xdead0000 | index) for value in registers]
        host_registers[15] = registers[15]
        ram[0x4d8e:0x4d90] = b'\0\0'
        ram, stack, final_registers = compare(ram, stack, host_registers, 'raster-finish',
                                             profile='carried-default-rts-host-register-mutations')
        assert final_registers[:13] == host_registers[:13] and final_registers[14] == host_registers[14]
        assert final_registers[13] == original_a5 and final_registers[15] == 0x110000 + 384
        assert int.from_bytes(ram[0x4d8e:0x4d90], 'big') == original_vram
        sequences.append({'cases': len(rows) - start, 'actual_default3dcc_rts_executed': True,
            'other_register_host_mutations_preserved': True, 'saved_a5_and_vram_restored': True})

    sentinel = b'previous-raster-output\0\xff'
    def reject(ram, stack, registers, mode, stack_base, label, raw_regs=None):
        ram_in.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers) if raw_regs is None else raw_regs)
        for path in outputs:
            path.write_bytes(sentinel)
        actual = subprocess.run(arguments(mode, stack_base), capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in outputs), (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    ram, stack, registers = fixture()
    ram[0xfd80] = 128
    for mode, values in (('raster-begin', (0x110000, 0x110008, 0x110101, 0x110202, 0xffffffff)),
                         ('raster-finish', (0x10fffe, 0x110001, 0x1101fc, 0x110202, 0xfffffa))):
        for sp in values:
            changed = list(registers)
            changed[15] = sp
            reject(ram, stack, changed, mode, 0x110000, 'invalid-sp-range-alignment-or-span')
    for stack_base in (0x100000, 0x110001, 0xfffffe):
        reject(ram, stack, registers, 'raster-begin', stack_base, 'invalid-stack-base-or-end')
    for size in (0, 65535, 65537):
        reject(bytes(size), stack, registers, 'raster-begin', 0x110000, 'invalid-ram-size')
    for size in (0, 63, 65):
        reject(ram, stack, registers, 'raster-begin', 0x110000, 'invalid-register-size', bytes(size))
    reject(ram, stack[:-1], registers, 'raster-begin', 0x110000, 'odd-stack-length')
    ram_in.write_bytes(ram)
    stack_in.write_bytes(stack)
    regs_in.write_bytes(struct.pack('>16I', *registers))
    aliases = (ram_in, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(ram_in)
    aliases[2].symlink_to(ram_in.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), 'raster-begin', str(ram_in), str(stack_in),
            str(regs_in), str(alias), str(stack_out), str(regs_out), str(ports_out), '0x110000'],
            capture_output=True, text=True)
        assert actual.returncode and ram_in.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_addresses': [0x29c, 0x2b6, CALLBACK], 'entry_rom_offsets': [0x29c, 0x2b6, CALLBACK],
        'cases': len(rows), 'isolated_cases': isolated, 'negative_cases': len(negatives),
        'whole_ram_stack_and_all16_registers_equal': True,
        'ordered_mmio_and_actual_stack_writes_equal': True,
        'all256_fd80_flags_and_stack_bounds_checked': True,
        'explicit_code_hooks_stop_before_callback_or_rte': True,
        'output_carry_sequences': sequences, 'negative_results': negatives, 'results': rows,
        'scope': 'Unmodified raster 29c entry stops before the callback or inactive RTE 2d6. '
            'Native 2b6 finish stops before RTE 2cc. Explicit external stack, full RAM, all 16 '
            'registers, ordered MMIO and chronological stack writes compared. Carry sequences '
            'execute actual default 3dcc RTS and preserve explicit host mutations of other '
            'registers through finish while restoring saved A5 and VRAM. No arbitrary '
            'callback, BIOS, RTE, exception frame semantics, physical devices or natural '
            'interrupt timing claimed.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
                     'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
