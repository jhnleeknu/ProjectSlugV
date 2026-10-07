"""Compare native3cb2 sound-queue service with unmodified M68000 execution."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

RAM_BASE, RETURN, ENTRY, PORT = 0x100000, 0xff000, 0x3cb2, 0x320000
BRANCHES = {0x3cc6: 'reset3', 0x3cde: 'busy', 0x3cea: 'special7f',
            0x3d06: 'empty', 0x3d2e: 'queue'}


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    executable = root / 'build/service_sound_queue'
    if not executable.exists():
        raise ValueError('Build build/service_sound_queue first')
    folder = root / 'artifacts/sound_queue'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, port_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(PORT, 0x1000)
    port_state = {'status': 0, 'reads': 0}
    writes, branches, rows, sequences, negatives = [], [], [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address != PORT or size != 1:
            raise ValueError('Native sound status read address/width differs')
        port_state['reads'] += 1
        cpu.mem_write(PORT, bytes((port_state['status'],)))

    def write_hook(cpu, access, address, size, value, user):
        writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        branches.append(BRANCHES[address])

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=PORT, end=PORT)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook, begin=PORT, end=PORT)
    for address in BRANCHES:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(head=0, tail=1, flags=0, special=0):
        ram = bytearray(hashlib.shake_256(b'ms5-sound-queue-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        struct.pack_into('>HH', ram, 0x4d74, head, tail)
        ram[0x4d7b], ram[0xf003] = flags, special
        return ram

    def branch(ram, status):
        if ram[0x4d7b] & 128:
            return 'reset3'
        if status == 1:
            return 'busy'
        if ram[0xf003] & 128:
            return 'special7f'
        return 'empty' if ram[0x4d74:0x4d76] == ram[0x4d76:0x4d78] else 'queue'

    def arguments(status):
        return [str(executable), str(inp), str(out), str(port_out), str(status)]

    def compare(ram, status, profile, sequence=None):
        expected_branch = branch(ram, status)
        head, tail = struct.unpack_from('>HH', ram, 0x4d74)
        if expected_branch == 'queue' and (head >= 128 or tail >= 128):
            raise ValueError('Refuse native execution outside declared queue index contract')
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, 0x1feffc), (UC_M68K_REG_D0, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        port_state.update(status=status, reads=0)
        writes.clear()
        branches.clear()
        cpu.emu_start(ENTRY, RETURN, count=10000)
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN or port_state['reads'] != 1 or branches != [expected_branch]:
            raise ValueError('Native sound service read/return/priority path differs: ' + repr(branches))
        if any(size != 1 or address != PORT for size, address, value in writes) or len(writes) > 1:
            raise ValueError('Native sound command writes differ')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        if expected[0x4d7c] != status or expected[0x4d7b] != ram[0x4d7b] & 127:
            raise ValueError('Native status snapshot or reset flag clear differs')
        expected_special = ram[0xf003] if expected_branch in ('reset3', 'busy') else ram[0xf003] & 127
        if expected[0xf003] != expected_special or expected[0x4d76:0x4d78] != ram[0x4d76:0x4d78]:
            raise ValueError('Native busy/priority special flag or tail preservation differs')
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(ram)
        for path in (out, port_out):
            path.unlink(missing_ok=True)
        result = subprocess.run(arguments(status), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr)))
        actual, actual_ports = out.read_bytes(), port_out.read_bytes()
        if actual != expected or actual_ports != expected_ports or json.loads(result.stdout) != {'writes': len(writes)}:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Sound queue mismatch: ' + repr((len(rows), profile, status,
                differences[:20], expected_ports.hex(), actual_ports.hex(), result.stdout)))
        rows.append({'profile': profile, 'sequence': sequence, 'status': status, 'flags': ram[0x4d7b],
            'special_flags': ram[0xf003], 'initial_head': head, 'tail': tail,
            'final_head': struct.unpack_from('>H', expected, 0x4d74)[0],
            'actual_branch': expected_branch, 'actual_status_reads': port_state['reads'],
            'command': writes[0][2] if writes else None,
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected)

    profiles = ((0, 0), (128, 0), (0, 128), (128, 128),
                (127, 255), (255, 127), (255, 255), (127, 127))
    rings = ((0, 1), (127, 1), (17, 20), (64, 63), (0, 0), (127, 127))
    for status, (flags, special) in itertools.product(range(256), profiles):
        head, tail = rings[len(rows) % len(rings)]
        compare(fixture(head, tail, flags, special), status, 'all-status-bytes-priority-flags')
    for value in range(256):
        ram = fixture(17, 18)
        ram[0x4cf4 + 17] = value
        compare(ram, 0, 'all-command-bytes-single-entry')
    for head, length in itertools.product((0, 127), range(1, 128)):
        tail = (head + length) & 127
        ram = fixture(head, tail)
        ram[0x4cf4:0x4d74] = bytes((0xa5,)) * 128
        compare(ram, 0, 'duplicate-run-lengths-ring-wrap')
        if rows[-1]['final_head'] != tail:
            raise ValueError('Native full duplicate run did not stop at tail')
    for head, tail, flags, special, status in (
            (128, 129, 128, 128, 0), (65535, 0, 255, 255, 1),
            (65535, 128, 0, 255, 0), (128, 65535, 0, 0, 1),
            (128, 128, 0, 0, 0), (65535, 65535, 0, 0, 255), (32768, 32768, 0, 0, 0)):
        compare(fixture(head, tail, flags, special), status, 'unused-invalid-indices-priority-busy-empty')
    isolated = len(rows)
    ram = fixture(125, 5, 128, 128)
    for index, value in enumerate((1, 1, 2, 2, 3, 4, 4, 5)):
        ram[0x4cf4 + ((125 + index) & 127)] = value
    label, begin = 'priority-busy-then-ring-drain', len(rows)
    for status in (0, 1, 2, 0, 1, 0, 0, 0, 0, 0):
        ram = compare(ram, status, 'whole-output-carry', label)
    commands = [row['command'] for row in rows[begin:]]
    if commands != [3, None, 127, 1, None, 2, 3, 4, 5, None]:
        raise ValueError('Native carried priority/dedup ring drain differs')
    sequences.append({'label': label, 'frames': len(rows) - begin, 'commands': commands,
                      'final_head_equals_tail': ram[0x4d74:0x4d76] == ram[0x4d76:0x4d78]})
    # Reject used invalid indices only after status/flag mutations are attempted
    # internally; neither output may be published and existing files must survive.
    for head, tail in ((128, 0), (0, 128), (65535, 0), (0, 65535), (128, 129)):
        inp.write_bytes(fixture(head, tail, 127, 127))
        for existing in (False, True):
            sentinels = (b'prior-sound-ram', b'prior-sound-ports')
            for path, sentinel in zip((out, port_out), sentinels):
                if existing:
                    path.write_bytes(sentinel)
                else:
                    path.unlink(missing_ok=True)
            result = subprocess.run(arguments(0), capture_output=True, text=True)
            if result.returncode == 0:
                raise ValueError('Used invalid queue indices accepted')
            for path, sentinel in zip((out, port_out), sentinels):
                if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                        not existing and path.exists()):
                    raise ValueError('Invalid queue indices changed outputs')
            negatives.append({'failure': 'used-invalid-queue-indices', 'head': head, 'tail': tail,
                'existing_outputs': existing, 'outputs_preserved': True,
                'stderr': result.stderr.strip(), 'original_executed': False})
    sentinel_ram, sentinel_ports = b'prior-sound-ram', b'prior-sound-ports'
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        out.write_bytes(sentinel_ram)
        port_out.write_bytes(sentinel_ports)
        result = subprocess.run(arguments(0), capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel_ram or port_out.read_bytes() != sentinel_ports:
            raise ValueError('Invalid RAM size changed sound outputs')
        negatives.append({'failure': 'invalid-ram-size', 'size': size, 'outputs_preserved': True,
                          'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    counts = {name: sum(row['actual_branch'] == name for row in rows) for name in BRANCHES.values()}
    if not all(counts.values()):
        raise ValueError('Missing native sound service branch coverage')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'address_mapping': 'Fixed CPU addresses equal decrypted ROM offsets.',
        'cases': len(rows), 'isolated_cases': isolated, 'actual_branch_counts': counts,
        'whole_65536_byte_ram_equal': True, 'ordered_sound_port_writes_equal': True,
        'status_port_read_exactly_once_asserted': True,
        'all256_status_and_command_bytes_checked': True,
        'priority_busy_special_flag_order_asserted': True,
        'all_duplicate_run_lengths1_to127_and_ring_wrap_checked': True,
        'unused_invalid_indices_accepted_for_priority_busy_empty': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'used_invalid_indices_and_bad_ram_preserve_outputs': True,
        'port_events': sum(row['command'] is not None for row in rows), 'results': rows,
        'scope': 'Unmodified3cb2 queue service reads supplied320000 status once. Reset3 '
            'priority, busy1 early return preserving special pending flag, special7f '
            'priority, empty queue and adjacent duplicate command collapse compared. '
            'Allstatus/command bytes, ring wrap and duplicate lengths1..127, carried '
            'queue drain and ignored invalid indices checked. Used invalid indices '
            'outside0..127 are unsupported API inputs and rejected without publication. '
            'Entry does not execute upstream48156. Z80 execution, command meaning, '
            'hardware sound timing/audio and natural caller reachability excluded.'}, indent=2) + '\n')
    print('Sound queue original/C++ match:', len(rows), 'cases;', counts, ';', len(negatives), 'preservation failures')


if __name__ == '__main__':
    main()
