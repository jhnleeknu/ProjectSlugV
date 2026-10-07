"""Probe native c8c prefixes, bounded dependencies, and quiet full returns."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ENTRY, RETURN, RAM_BASE, STACK = 0xc8c, 0xff000, 0x100000, 0x1feffc
BOUNDARIES = (0xcb0, 0xa2c, 0x72fa, 0x3af8, 0x3cb2)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    writes, calls = [], []
    stop = None
    reached = None

    def write_hook(cpu, access, address, size, value, user):
        if not (RAM_BASE <= address < RAM_BASE + 65536 or STACK - 256 <= address <= STACK):
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        nonlocal reached
        calls.append(address)
        if address == stop:
            reached = address
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in BOUNDARIES + (0xbbe, 0x3cac, 0x48156, 0xd4e):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def execute(ram, incoming_d0=0x12345681, sound_status=0, boundary=None):
        nonlocal stop, reached
        stop, reached = boundary, None
        cpu.mem_write(RAM_BASE, bytes(ram))
        cpu.mem_write(0x320000, bytes((sound_status,)))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_A7, STACK), (UC_M68K_REG_D0, incoming_d0)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        calls.clear()
        cpu.emu_start(ENTRY, RETURN, count=500000)
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc != RETURN and pc != boundary:
            raise ValueError('Unexpected interrupt probe boundary: ' + hex(pc))
        return bytes(cpu.mem_read(RAM_BASE, 65536)), writes.copy(), calls.copy(), pc

    prefix_digest = hashlib.sha256()
    prefix_count, immediate_returns, prefix_watchdogs = 0, 0, 0

    def prefix(signal, flag, low):
        nonlocal prefix_count, immediate_returns, prefix_watchdogs
        ram = bytearray(65536)
        ram[0x16], ram[0x19] = signal, flag
        expected = bytearray(ram)
        expected[0x19] |= 128
        reentrant = bool(flag & 128)
        expected_ports = []
        if not reentrant:
            expected[0x16] = min(signal + 1, 255)
            if signal < 255:
                expected_ports = [(1, 0x300001, low)]
        result, ports, trace, pc = execute(ram, 0x12345600 | low, boundary=0xcb0)
        if result != expected or ports != expected_ports or pc != (RETURN if reentrant else 0xcb0):
            raise ValueError('Prefix mismatch: ' + repr((signal, flag, low, pc, ports)))
        if trace != ([] if reentrant else [0xcb0]):
            raise ValueError('Prefix passed an unrequested dependency')
        prefix_count += 1
        immediate_returns += reentrant
        prefix_watchdogs += len(ports)
        prefix_digest.update(bytes((signal, flag, low)))
        prefix_digest.update(result)
        prefix_digest.update(b''.join(struct.pack('>BII', *write) for write in ports))

    for signal, flag, low in itertools.product(range(256), (0, 1, 0x7f, 0x80, 0xff),
                                               (0, 1, 0x81, 0xff)):
        prefix(signal, flag, low)
    primary_prefix_count = prefix_count
    for flag, signal in itertools.product(range(256), (0, 255)):
        prefix(signal, flag, 0xaa)

    quiet_digest = hashlib.sha256()
    quiet_count, quiet_ports = 0, 0
    examples = []
    for signal, flag, fd82, status, display, request, low in itertools.product(
            (0, 254, 255), (0, 1, 0x7f), (0, 1), (0, 1, 2, 255), (0, 16),
            ('none', 'command3', 'command7f'), (0, 0x81)):
        ram = bytearray(65536)
        ram[0x16], ram[0x19], ram[0xfd82], ram[0xf001] = signal, flag, fd82, display
        ram[0x4d7c], ram[0x4d7a] = 0xa5, 0x42
        if request == 'command3':
            ram[0x4d7b] = 0x80
        elif request == 'command7f':
            ram[0xf003] = 0x80
        expected = bytearray(ram)
        expected[0x16], expected[0x19], expected[0x4d7c] = min(signal + 1, 255), 0, status
        expected_ports = [(1, 0x300001, low)] if signal < 255 else []
        if display:
            expected_ports.append((1, 0x3a0001, low if fd82 else 0))
        if request == 'command3':
            expected[0x4d7b] = 0
            expected[0x4d7a] = 255
            expected_ports.append((1, 0x320000, 3))
        elif request == 'command7f' and status != 1:
            expected[0xf003] = 0
            expected[0x4d7a] = 255
            expected_ports.append((1, 0x320000, 127))
        result, ports, trace, pc = execute(ram, 0x12345600 | low, status)
        if result != expected or ports != expected_ports or pc != RETURN:
            differences = [hex(at) for at in range(65536) if result[at] != expected[at]]
            raise ValueError('Quiet full-return mismatch: ' + repr((signal, flag, fd82, status,
                display, request, low, differences[:12], ports, expected_ports)))
        if trace != [0xcb0, 0xbbe, 0x3cac, 0x48156, 0x3cb2, 0xd4e]:
            raise ValueError('Quiet original dependency trace changed: ' + repr(trace))
        quiet_count += 1
        quiet_ports += len(ports)
        quiet_digest.update(bytes((signal, flag, fd82, status, display, low)))
        quiet_digest.update(request.encode())
        quiet_digest.update(result)
        quiet_digest.update(b''.join(struct.pack('>BII', *write) for write in ports))
        if signal == 255 and flag == 0 and fd82 == 1 and low == 0x81:
            examples.append({'signal': signal, 'sound_status': status, 'display': display,
                             'request': request, 'ordered_writes': ports, 'trace': trace})

    dependency_rows = []
    for name, boundary in (('credit-helper', 0xa2c), ('palette-upload', 0x72fa),
                           ('sound-producer', 0x3af8), ('sound-consumer-read', 0x3cb2)):
        ram = bytearray(65536)
        ram[0xfd82] = 1
        if name == 'credit-helper':
            ram[0xfd82], ram[0xfdaf], ram[0x14] = 0, 2, 1
        elif name == 'palette-upload':
            ram[0x1b] = 128
        elif name == 'sound-producer':
            ram[0xd68d] = 1
        result, ports, trace, pc = execute(ram, boundary=boundary)
        if pc != boundary or result[0x16] != 1 or result[0x19] != 128:
            raise ValueError('Dependency boundary not reached: ' + name)
        dependency_rows.append({'profile': name, 'stop_cpu_address': pc,
            'execution_stopped_before_instruction': True, 'signal': result[0x16],
            'guard_byte': result[0x19], 'ordered_writes': ports, 'actual_trace': trace,
            'actual_boundary_d0': cpu.reg_read(UC_M68K_REG_D0),
            'actual_boundary_stack': cpu.reg_read(UC_M68K_REG_A7),
            'request100014': result[0x14], 'credit_request10fdb4': result[0xfdb4],
            'producer_word10d68c': int.from_bytes(result[0xd68c:0xd68e], 'big'),
            'ram_sha256': hashlib.sha256(result).hexdigest()})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Mapped original program changed')
    folder = root / 'artifacts/interrupt_flow'
    folder.mkdir(parents=True, exist_ok=True)
    report = {'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'program_code_modified': False,
        'address_mapping': 'CPU address equals canonical fixed ROM offset below 100000.',
        'prefix': {'cases': prefix_count, 'primary_cases': primary_prefix_count,
            'signal_values': 'Every byte 0..255', 'primary_flags': [0, 1, 127, 128, 255],
            'primary_incoming_d0_low_bytes': [0, 1, 129, 255],
            'additional_all_guard_bytes': 'Every byte 0..255 at signals 0/255 with D0.low=aa',
            'stop_cpu_address': 0xcb0, 'whole_64k_ram_asserted': True,
            'immediate_reentrancy_returns': immediate_returns,
            'ordered_watchdog_byte_writes': prefix_watchdogs,
            'combined_sha256': prefix_digest.hexdigest()},
        'quiet_full_return': {'cases': quiet_count, 'signal_values': [0, 254, 255],
            'guard_values': [0, 1, 127], 'fd82_values': [0, 1],
            'request100014': 0, 'byte10001b': 0, 'word10d68c': 0,
            'sound_queue_words104d74_104d76': [0, 0],
            'sound_status_values': [0, 1, 2, 255], 'display_bit4_values': [0, 16],
            'command_profiles': ['none', 'command3', 'command7f'],
            'incoming_d0_low_bytes': [0, 129], 'whole_64k_ram_asserted': True,
            'guard_clear_signal_saturation_and_sound_status_asserted': True,
            'ordered_hardware_writes_asserted': True, 'port_events': quiet_ports,
            'combined_sha256': quiet_digest.hexdigest(), 'examples': examples},
        'dependency_boundary_cases': dependency_rows,
        'scope': 'Unmodified c8c prefix and quiet full c8c returns through native bbe, '
            '3cac and 48156. Other cases stop before actual a2c/72fa/3af8/3cb2 entry '
            'instructions. These boundaries do not establish completed dependency behavior. '
            'No vector 20c or BIOS execution, palette upload, active sound production, queued '
            'sound consumption, natural IRQ timing, reentrance during execution, or full IRQ '
            'handler equivalence is claimed.'}
    (folder / 'analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Interrupt flow:', prefix_count, 'prefix cases;', quiet_count,
          'quiet full returns;', len(dependency_rows), 'actual dependency boundaries')


if __name__ == '__main__':
    main()
