"""Compare original20c/248 explicit external-stack IRQ entry/finish envelopes."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, CALLBACK, BIOS, FINISH = 0x100000, 0xff000, 0xc00438, 0x29a
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/step_irq_envelope'
    folder = root / 'artifacts/irq_envelope'
    folder.mkdir(parents=True, exist_ok=True)
    ram_in, stack_in, regs_in, ram_out, stack_out, regs_out, ports_out, report = [folder / name for name in
        ('input.bin', 'stack.bin', 'registers.bin', 'cpp.bin', 'cpp.stack.bin', 'cpp.registers.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address, length in ((0x2f0000, 0x10000), (0x3c0000, 0x1000), (0xc00000, 0x1000), (0xfff000, 0x1000)):
        cpu.mem_map(address, length)
    state = {'stack_base': 0, 'stack_size': 0, 'video': 0, 'reads': 0}
    stack_writes, ports, rows, negatives, sequences = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        if state['stack_base'] <= address and address + size <= state['stack_base'] + state['stack_size']:
            stack_writes.append((size, address, value))
        elif address in (0x3c000c, 0x3c0004, 0x3c0000, 0x2ffff2, 0x2ffff0):
            assert size == 2
            ports.append((size, address, value))
        elif not (BASE <= address and address + size <= BASE + 65536):
            raise ValueError('Unexpected native write: ' + repr((hex(address), size, value)))

    def read_hook(cpu, access, address, size, value, user):
        assert address == 0x3c0006 and size == 2
        state['reads'] += 1
        cpu.mem_write(address, state['video'].to_bytes(2, 'big'))

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x3c0006, end=0x3c0007)

    def fixture(stack_base=0x110000, stack_size=512, sp_offset=256):
        seed = b'ms5-irq-envelope-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        stack = bytearray(hashlib.shake_256(seed + b'stack').digest(stack_size))
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[15] = stack_base + sp_offset
        struct.pack_into('>I', ram, 6, CALLBACK)
        return ram, stack, registers

    def finish_frame(stack, registers, stack_base, bank=0, vram=0xabcd):
        at = registers[15] - stack_base
        saved = list(struct.unpack('>15I', hashlib.shake_256(b'irq-saved-frame:' + len(rows).to_bytes(4, 'big')).digest(60)))
        struct.pack_into('>HH15I', stack, at, bank, vram, *saved)
        return saved

    def compare(ram, stack, registers, mode='begin', stack_base=0x110000, video=0, profile='matrix'):
        boundary = FINISH if mode == 'finish' else CALLBACK if ram[0xfd80] & 128 else BIOS
        cpu.mem_write(BASE, bytes(ram))
        if stack:
            cpu.mem_write(stack_base, bytes(stack))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        state.update(stack_base=stack_base, stack_size=len(stack), video=video, reads=0)
        stack_writes.clear()
        ports.clear()
        cpu.emu_start(0x20c if mode == 'begin' else 0x248, boundary, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == boundary
        expected_ram = bytes(cpu.mem_read(BASE, 65536))
        expected_stack = bytes(cpu.mem_read(stack_base, len(stack))) if stack else b''
        expected_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        expected_regs = struct.pack('>16I', *expected_registers)
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        assert state['reads'] == int(mode == 'finish')
        if mode == 'begin':
            assert ports == [(2, 0x3c000c, 6)]
            if boundary == BIOS:
                assert expected_ram == ram and expected_stack == stack and expected_registers == registers and not stack_writes
            else:
                assert len(stack_writes) == 18 and [entry[0] for entry in stack_writes] == [4] * 15 + [2, 2, 4]
                assert stack_writes[-1] == (4, registers[15] - 68, 0x23c)
                assert expected_registers[15] == registers[15] - 68
        else:
            assert stack_writes == [(2, registers[15], registers[7] & 65535), (2, registers[15] - 2, registers[0] & 65535)]
            assert expected_registers[15] == registers[15] + 64
        result = {'next_pc': boundary, 'bios_handoff': boundary == BIOS,
            'stack_writes': [list(entry) for entry in stack_writes]}
        ram_in.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (ram_out, stack_out, regs_out, ports_out):
            path.unlink(missing_ok=True)
        args = [str(executable), mode, str(ram_in), str(stack_in), str(regs_in), str(ram_out), str(stack_out), str(regs_out), str(ports_out), hex(stack_base)]
        if mode == 'finish':
            args.append(str(video))
        actual = subprocess.run(args, capture_output=True, text=True)
        if actual.returncode or not ram_out.exists() or ram_out.read_bytes() != expected_ram or not stack_out.exists() or stack_out.read_bytes() != expected_stack or not regs_out.exists() or regs_out.read_bytes() != expected_regs or not ports_out.exists() or ports_out.read_bytes() != expected_ports or json.loads(actual.stdout) != result:
            raise ValueError(repr((len(rows), profile, mode, hex(stack_base), hex(registers[15]), result, actual.stdout, actual.stderr)))
        rows.append({'profile': profile, 'mode': mode, 'stack_base': stack_base, 'stack_size': len(stack),
            'input_sp': registers[15], 'fd80': ram[0xfd80], 'video_status': video,
            'native_video_reads': state['reads'], 'ports': len(ports), 'result': result,
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected_ram).hexdigest(),
            'stack_sha256': hashlib.sha256(expected_stack).hexdigest(), 'registers_sha256': hashlib.sha256(expected_regs).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected_ram), bytearray(expected_stack), expected_registers

    for flag in range(256):
        ram, stack, registers = fixture()
        ram[0xfd80] = flag
        compare(ram, stack, registers, profile='all256-fd80-flags')
    for high, low in itertools.product((0, 1, 128, 255), range(256)):
        ram, stack, registers = fixture(sp_offset=128)
        finish_frame(stack, registers, 0x110000, bank=(high << 8) | low, vram=(low << 8) | high)
        compare(ram, stack, registers, mode='finish', video=(high << 8) | low,
            profile='all256-video-lowbytes-selected-highbytes-bank-words')
    for bank, stack_base in itertools.product((0, 1, 7, 15, 16, 0x7fff, 0x8000, 0xffff), (0x110000, 0x1fe000, 0xfff000)):
        ram, stack, registers = fixture(stack_base, stack_size=128, sp_offset=2)
        registers[0], registers[7] = 0xabcd8000, 0x1234ffff
        finish_frame(stack, registers, stack_base, bank, vram=bank ^ 0xffff)
        compare(ram, stack, registers, mode='finish', stack_base=stack_base, video=8,
            profile='bank-increment-shift-word-wrap-and-stack-boundaries')
    for stack_base, size, offset in ((0x110000, 68, 68), (0xfff000, 4096, 4094)):
        ram, stack, registers = fixture(stack_base, size, offset)
        ram[0xfd80] = 128
        compare(ram, stack, registers, stack_base=stack_base, profile='active-entry-minimum-and-maximum-sp')
    ram, stack, registers = fixture(0xfff000, 4096, 0xfbe)
    finish_frame(stack, registers, 0xfff000, 0xffff, 0xffff)
    compare(ram, stack, registers, mode='finish', stack_base=0xfff000, video=0xffff,
        profile='finish-maximum-spffffbe')
    for sp in (0, 1, 0xffffffff):
        ram, stack, registers = fixture(stack_size=0, sp_offset=0)
        ram[0xfd80], registers[15] = 0, sp
        compare(ram, stack, registers, profile='bios-unused-empty-stack-arbitrary-sp')
    isolated = len(rows)

    for index in range(16):
        ram, stack, registers = fixture(sp_offset=384)
        ram[0xfd80] = 0x80 | index
        struct.pack_into('>HH', ram, 0x10, index * 0x1111, 0x1234)
        struct.pack_into('>H', ram, 0x4d8e, 0xabcd ^ index)
        begin = len(rows)
        ram, stack, after_begin = compare(ram, stack, registers, profile='carried-entry-through-host-callback-to-finish')
        host_registers = [value ^ (0xdead0000 | index) for value in after_begin]
        host_registers[15] = after_begin[15] + 4  # Explicit host callback RTS consumption.
        # Host/BIOS scratch changes occur before248; saved registers remain on stack.
        ram[0x10:0x12] = b'\xff\xff'
        ram[0x4d8e:0x4d90] = b'\0\0'
        final_ram, final_stack, final_registers = compare(ram, stack, host_registers,
            mode='finish', video=index * 0x1111, profile='carried-entry-through-host-callback-to-finish')
        assert final_registers == registers
        sequences.append({'cases': len(rows) - begin, 'original_registers_restored': True,
            'explicit_host_callback_and_bios_mutations': True, 'callback_bios_rte_execution_not_claimed': True})

    sentinel = b'previous-irq-envelope-output\0\xff'
    def reject(ram, stack, registers, mode, stack_base, label, raw_regs=None):
        ram_in.write_bytes(ram)
        stack_in.write_bytes(stack)
        regs_in.write_bytes(struct.pack('>16I', *registers) if raw_regs is None else raw_regs)
        for path in (ram_out, stack_out, regs_out, ports_out):
            path.write_bytes(sentinel)
        args = [str(executable), mode, str(ram_in), str(stack_in), str(regs_in), str(ram_out), str(stack_out), str(regs_out), str(ports_out), hex(stack_base)]
        if mode == 'finish':
            args.append('0')
        actual = subprocess.run(args, capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (ram_out, stack_out, regs_out, ports_out)), (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    ram, stack, registers = fixture()
    ram[0xfd80] = 128
    for sp in (0x110000, 0x110042, 0x110101, 0x110202):
        bad = list(registers)
        bad[15] = sp
        reject(ram, stack, bad, 'begin', 0x110000, 'invalid-begin-stack-range-or-alignment')
    for sp in (0x110000, 0x110001, 0x1101c2, 0x110202):
        bad = list(registers)
        bad[15] = sp
        reject(ram, stack, bad, 'finish', 0x110000, 'invalid-finish-stack-range-or-alignment')
    for stack_base in (0x100000, 0x110001, 0xfffffe):
        reject(ram, stack, registers, 'begin', stack_base, 'invalid-stack-base-or-overflow')
    for size in (0, 65535, 65537):
        reject(bytes(size), stack, registers, 'begin', 0x110000, 'invalid-ram-size')
    for size in (0, 63, 65):
        reject(ram, stack, registers, 'begin', 0x110000, 'invalid-register-file-size', bytes(size))
    ram_in.write_bytes(ram)
    stack_in.write_bytes(stack)
    regs_in.write_bytes(struct.pack('>16I', *registers))
    aliases = (ram_in, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(ram_in)
    aliases[2].symlink_to(ram_in.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), 'begin', str(ram_in), str(stack_in), str(regs_in), str(alias), str(stack_out), str(regs_out), str(ports_out), '0x110000'], capture_output=True, text=True)
        assert actual.returncode and ram_in.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_addresses': [0x20c, 0x248],
        'entry_rom_offsets': [0x20c, 0x248], 'cases': len(rows), 'isolated_cases': isolated,
        'negative_cases': len(negatives), 'whole_ram_stack_and_all16_registers_equal': True,
        'ordered_mmio_and_stack_writes_equal': True, 'native_video_read_count_exact': True,
        'all256_flags_video_lowbytes_and_selected_highbytes_checked': True,
        'output_carry_sequences': sequences, 'negative_results': negatives, 'results': rows,
        'scope': 'Original20c entry stopped before callback or BIOSc00438. Original248 '
            'finish stopped at29a beforeRTE. Explicit external stack fully compared, including '
            'descending MOVEM save and temporary MOVEM.W overwrite order. WholeRAM, all16 '
            'registers, MMIO and video reads verified. Carried entry/finish pairs include '
            'explicit host callback/BIOS scratch mutations and A7+4 consumed callback return. '
            'No callback, BIOS or RTE execution, exception frame semantics, physical devices '
            'or natural interrupt timing claimed.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
