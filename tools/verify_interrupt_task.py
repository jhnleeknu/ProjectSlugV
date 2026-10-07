"""Compare originalce2 task restoration through callback or emptyd36 boundary."""
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

BASE, EMPTY, TARGET = 0x100000, 0xd36, 0xff000
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/restore_interrupt_task'
    folder = root / 'artifacts/interrupt_task'
    folder.mkdir(parents=True, exist_ok=True)
    inp, regs_in, out, regs_out, ports, report = [folder / name for name in
        ('input.bin', 'registers.bin', 'cpp.bin', 'cpp.registers.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address, length in ((0x2f0000, 0x10000), (0x300000, 0x1000), (0xfff000, 0x1000)):
        cpu.mem_map(address, length)
    writes, stack_writes, rows, negatives = [], [], [], []
    state = {'sp': 0}

    def hook(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        if address in (0x300001, 0x2ffff2, 0x2ffff0):
            writes.append((size, address, value))
        elif address in (state['sp'] - 4, state['sp'] - 8):
            assert size == 4
            stack_writes.append((address, value))

    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)

    def fixture(pointer, alias='global', sp=0x1feffc, d0=0xabcdab35):
        seed = b'ms5-interrupt-task-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        registers = list(struct.unpack('>16I', hashlib.shake_256(seed + b'regs').digest(64)))
        registers[0], registers[13], registers[15] = d0, 0x108000, sp
        struct.pack_into('>I', ram, 0x81c, pointer)
        target = TARGET
        if pointer < 0x10081c:
            destination = {'global': BASE + 0x81c, 'a6': pointer + 56,
                'pc': pointer + 60, 'flagword': BASE + 0x10}[alias]
            frame = list(struct.unpack('>16I', hashlib.shake_256(seed + b'frame').digest(64)))
            frame[13], frame[15] = destination + 0x77e4, TARGET
            struct.pack_into('>16I', ram, pointer - BASE, *frame)
            # Frame may cover RAM0010 or queue storage; entryqueue is set last.
            struct.pack_into('>I', ram, 0x81c, pointer)
            if alias == 'pc':
                target = pointer + 64
        return ram, registers, target

    def compare(ram, registers, target, profile, alias='global'):
        pointer = int.from_bytes(ram[0x81c:0x820], 'big')
        restored = pointer < 0x10081c
        boundary = target if restored else EMPTY
        cpu.mem_write(BASE, bytes(ram))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        state['sp'] = registers[15]
        writes.clear()
        stack_writes.clear()
        cpu.emu_start(0xce2, boundary, count=1000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == boundary
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_regs = struct.pack('>16I', *[cpu.reg_read(reg) & 0xffffffff for reg in REGS])
        expected_ports = b''.join(struct.pack('>BII', *event) for event in writes)
        if restored:
            assert stack_writes == [(registers[15] - 4, 0xd2a), (registers[15] - 8, boundary)]
            for address, value in stack_writes:
                assert bytes(cpu.mem_read(address, 4)) == value.to_bytes(4, 'big')
            assert writes == [(1, 0x300001, registers[0] & 255), (2, 0x2ffff2, 0x1000), (2, 0x2ffff0, 0)]
        else:
            assert not writes and not stack_writes and expected == ram
        result = {'next_pc': boundary, 'restored': restored,
            'stack_address': [entry[0] for entry in stack_writes] if restored else [0, 0],
            'stack_value': [entry[1] for entry in stack_writes] if restored else [0, 0], 'writes': len(writes)}
        inp.write_bytes(ram)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, regs_out, ports):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), str(inp), str(regs_in), str(out), str(regs_out), str(ports)], capture_output=True, text=True)
        if actual.returncode or not out.exists() or out.read_bytes() != expected or not regs_out.exists() or regs_out.read_bytes() != expected_regs or not ports.exists() or ports.read_bytes() != expected_ports or json.loads(actual.stdout) != result:
            actual_ram = out.read_bytes() if out.exists() else b''
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, hex(pointer), alias, result, actual.stdout, actual.stderr, diff[:20], expected_regs.hex(), regs_out.read_bytes().hex() if regs_out.exists() else '')))
        rows.append({'profile': profile, 'queue_pointer': pointer, 'alias': alias,
            'input_stack': registers[15], 'input_d0': registers[0], 'result': result,
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'registers_sha256': hashlib.sha256(expected_regs).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for slot, alias, variant in itertools.product(range(32), ('global', 'a6', 'pc', 'flagword'), range(2)):
        pointer = 0x10081c - 64 * (slot + 1)
        sp = (0x110008, 0x1feffc, 0xfffffc, 0x11000a)[slot % 4]
        ram, registers, target = fixture(pointer, alias, sp, 0xffffffff if variant else 0xabcdab00 | slot)
        compare(ram, registers, target, 'all32-canonical-slots-pointer-write-alias-order', alias)
    for pointer, sp in itertools.product((0x100000, 0x100002, 0x1007da, 0x1007dc), (0x110008, 0xfffffc)):
        ram, registers, target = fixture(pointer, sp=sp)
        compare(ram, registers, target, 'word-aligned-frame-and-external-stack-boundaries')
    for pointer, sp in itertools.product((0x10081c, 0x10081d, 0x100820, 0x80000000, 0xffffffff), (0, 1, 0xffffffff)):
        ram, registers, target = fixture(pointer, sp=sp)
        compare(ram, registers, target, 'unsigned-empty-pointer-ignores-stack')

    sentinel = b'previous-interrupt-task-output\0\xff'
    def reject(ram, registers, label, raw_regs=None):
        inp.write_bytes(ram)
        regs_in.write_bytes(struct.pack('>16I', *registers) if raw_regs is None else raw_regs)
        for path in (out, regs_out, ports):
            path.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(regs_in), str(out), str(regs_out), str(ports)], capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, regs_out, ports))
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    for pointer in (0, 0xffffe, 0x100001, 0x1007de, 0x10081a):
        ram, registers, target = fixture(0x100100)
        struct.pack_into('>I', ram, 0x81c, pointer)
        reject(ram, registers, 'invalid-used-frame-pointer')
    for sp in (0, 0x110006, 0x110009, 0xfffffe, 0xffffffff):
        ram, registers, target = fixture(0x100100, sp=sp)
        reject(ram, registers, 'invalid-external-stack')
    for restored_a5 in (0, 0x1077e3, 0x1077e5, 0x1177e2, 0xffffffff):
        ram, registers, target = fixture(0x100100)
        struct.pack_into('>I', ram, 0x100 + 52, restored_a5)
        reject(ram, registers, 'invalid-restored-a5-pointer-destination')
    ram, registers, target = fixture(0x100100)
    registers[13] = 0x108002
    reject(ram, registers, 'invalid-entry-a5')
    for size in (0, 65535, 65537):
        reject(bytes(size), registers, 'invalid-ram-size')
    for size in (0, 63, 65):
        reject(ram, registers, 'invalid-register-file-size', bytes(size))
    ram, registers, target = fixture(0x100100)
    inp.write_bytes(ram)
    regs_in.write_bytes(struct.pack('>16I', *registers))
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), str(inp), str(regs_in), str(alias), str(regs_out), str(ports)], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': 0xce2,
        'entry_rom_offset': 0xce2, 'cases': len(rows), 'negative_cases': len(negatives),
        'whole_65536_byte_ram_and_all16_registers_equal': True, 'ordered_hardware_ports_equal': True,
        'external_stack_actual_writes_and_memory_equal': True, 'pointer_write_before_saved_a6_and_pc_reads_checked': True,
        'negative_results': negatives, 'results': rows,
        'scope': 'Originalce2 task dispatch through actuald28 RTS to callback boundary or '
            'emptyd36, stopped before callback/empty-path execution. All16 D/A registers, '
            'wholeRAM, watchdog/PVC order and actual external stack writes compared. SavedA5 '
            'destination aliases savedA6, savedPC and RAM0010 to test read/write ordering. '
            'All32 canonical slots plus word-aligned boundaries and unsigned empty pointers. '
            'Invalid frames/A5/stack are unsupported API inputs. Callback execution, exception '
            'frame/CPU flags, natural interrupt scheduling and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
