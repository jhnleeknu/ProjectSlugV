"""Exhaust the native signed-word sound timer before its producer call."""
import hashlib
import json
from pathlib import Path
import struct

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ENTRY, PRODUCER, RETURN, STACK = 0x48156, 0x3af8, 0xff000, 0x1feffc
RAM_BASE, TIMER_OFFSET, INCOMING_D0 = 0x100000, 0xd68c, 0x12345678


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported program')
    cpu = make_cpu(program)
    producer_hits = 0
    writes = []

    def boundary_hook(cpu, address, size, user):
        nonlocal producer_hits
        producer_hits += 1
        cpu.emu_stop()

    def write_hook(cpu, access, address, size, value, user):
        writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    cpu.hook_add(UC_HOOK_CODE, boundary_hook, begin=PRODUCER, end=PRODUCER)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    fixture = bytearray(hashlib.shake_256(b'ms5-native-sound-timer-v1').digest(65536))
    digest = hashlib.sha256()
    branches = {'zero-return': 0, 'signed-nonzero-le15': 0, 'positive-gt15-reset': 0}
    ranges = {name: {'min_initial_word': None, 'max_initial_word': None,
                    'min_command_word': None, 'max_command_word': None}
              for name in branches}
    command_counts = {}
    for initial in range(65536):
        ram = bytearray(fixture)
        struct.pack_into('>H', ram, TIMER_OFFSET, initial)
        expected = bytearray(ram)
        signed = initial if initial < 0x8000 else initial - 65536
        if initial == 0:
            branch, timer, d0, target = 'zero-return', 0, 0x12340000, RETURN
        elif signed <= 15:
            branch, timer, d0, target = ('signed-nonzero-le15', (initial + 1) & 65535,
                0x12340000 | ((initial + 0x19c0) & 65535), PRODUCER)
        else:
            branch, timer, d0, target = 'positive-gt15-reset', 0, 0x19c0, PRODUCER
        struct.pack_into('>H', expected, TIMER_OFFSET, timer)
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_A7, STACK), (UC_M68K_REG_D0, INCOMING_D0)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        before_hits = producer_hits
        cpu.emu_start(ENTRY, RETURN, count=100)
        actual_pc, actual_d0 = cpu.reg_read(UC_M68K_REG_PC), cpu.reg_read(UC_M68K_REG_D0)
        actual = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_writes = [] if initial == 0 else [(2, RAM_BASE + TIMER_OFFSET, timer),
                                                   (4, STACK - 4, 0x4817e)]
        if (actual != expected or actual_pc != target or actual_d0 != d0 or
                producer_hits - before_hits != (0 if initial == 0 else 1) or writes != expected_writes):
            differences = [hex(at) for at in range(65536) if actual[at] != expected[at]]
            raise ValueError('Native sound timer mismatch: ' + repr((initial, branch,
                differences[:12], hex(actual_pc), hex(actual_d0), writes, expected_writes)))
        branches[branch] += 1
        distribution = ranges[branch]
        for key, value in (('initial_word', initial), ('command_word', actual_d0 & 65535)):
            low, high = 'min_' + key, 'max_' + key
            distribution[low] = value if distribution[low] is None else min(distribution[low], value)
            distribution[high] = value if distribution[high] is None else max(distribution[high], value)
        if target == PRODUCER:
            command = actual_d0 & 65535
            command_counts[command] = command_counts.get(command, 0) + 1
        digest.update(struct.pack('>HIII', initial, timer, actual_d0, actual_pc))
        digest.update(actual)
        digest.update(b''.join(struct.pack('>BII', *write) for write in writes))
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Mapped original program changed')
    repeated = {str(command): count for command, count in command_counts.items() if count > 1}
    folder = root / 'artifacts/sound_timer'
    folder.mkdir(parents=True, exist_ok=True)
    report = {'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'address_mapping': 'CPU address equals canonical fixed ROM offset below 100000.',
        'program_code_modified': False, 'cases': 65536,
        'initial_timer_word_values': 'Every unsigned word 0..65535, compared as signed 16-bit at 4815e.',
        'incoming_d0': INCOMING_D0, 'entry_a5': 0x108000, 'entry_stack': STACK,
        'timer_cpu_address': RAM_BASE + TIMER_OFFSET,
        'producer_stop_cpu_address': PRODUCER, 'producer_executed': False,
        'actual_producer_boundaries': producer_hits, 'return_boundary': RETURN,
        'whole_65536_byte_ram_equal': True, 'full_d0_and_command_word_asserted': True,
        'ordered_memory_writes_asserted': True, 'no_hardware_writes_observed': True,
        'branch_cases': branches, 'branch_word_ranges': ranges,
        'distinct_producer_command_words': len(command_counts),
        'repeated_command_word_counts': repeated,
        'combined_sha256': digest.hexdigest(),
        'scope': 'Unmodified native 48156 timer helper through return or the first 3af8 '
                 'producer instruction. Whole RAM, signed-word branch boundaries, word wrap, '
                 'MOVE.W upper-word preservation versus MOVEQ clearing, command word and '
                 'actual control-flow boundary checked exhaustively. No producer execution, '
                 'C++ implementation, sound hardware behavior or natural IRQ timing claimed.'}
    (folder / 'analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Native sound timer:', sum(branches.values()), 'cases;', producer_hits,
          'actual producer boundaries;', branches)


if __name__ == '__main__':
    main()
