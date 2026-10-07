"""Compare native3ac8 producer and captured3aea resume with unmodified M68000."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

RAM_BASE, RETURN, ENTRY, WAIT, CONSUMER, PORT = 0x100000, 0xff000, 0x3ac8, 0x3aea, 0x3cb2, 0x320000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    executable, consumer = root / 'build/enqueue_sound_byte', root / 'build/service_sound_queue'
    if not executable.exists() or not consumer.exists():
        raise ValueError('Build enqueue_sound_byte and service_sound_queue first')
    folder = root / 'artifacts/sound_byte'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, port_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(PORT, 0x1000)
    state = {'wait_entries': 0, 'status_reads': 0}
    writes, rows, sequences, negatives = [], [], [], []

    def code_hook(cpu, address, size, user):
        state['wait_entries'] += 1
        if state['wait_entries'] == 2:
            cpu.emu_stop()

    def read_hook(cpu, access, address, size, value, user):
        if size != 1:
            raise ValueError('Native consumer sound status width differs')
        state['status_reads'] += 1
        cpu.mem_write(PORT, b'\0')

    def write_hook(cpu, access, address, size, value, user):
        writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    cpu.hook_add(UC_HOOK_CODE, code_hook, begin=WAIT, end=WAIT)
    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=PORT, end=PORT)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook, begin=PORT, end=PORT)

    def fixture(tail=0, waiting=False, head=None):
        ram = bytearray(hashlib.shake_256(b'ms5-sound-byte-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        if head is None:
            head = ((tail + 1) & 127) if waiting else tail
        struct.pack_into('>HH', ram, 0x4d74, head, tail)
        ram[0x4d7b], ram[0xf003] = 0, 0
        return ram

    def original_start(ram, command):
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, 0x1feffc), (UC_M68K_REG_D0, 0x12345600 | command),
                (UC_M68K_REG_D1, 0xcafeffff), (UC_M68K_REG_A0, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        state.update(wait_entries=0, status_reads=0)
        writes.clear()
        cpu.emu_start(ENTRY, RETURN, count=1000)
        return original_result(ram, command)

    def original_result(ram, command, captured_tail=None):
        pc = cpu.reg_read(UC_M68K_REG_PC)
        waiting = pc == WAIT
        if pc not in (WAIT, RETURN) or writes or state['status_reads']:
            raise ValueError('Native producer failed wait/return or touched hardware')
        tail = 0 if command == 3 else struct.unpack_from('>H', ram, 0x4d76)[0] if captured_tail is None else captured_tail
        next_index = 0 if command == 3 else (tail + 1) & 127
        if command != 3 and (cpu.reg_read(UC_M68K_REG_A0) != RAM_BASE + 0x4cf4 + tail or
                cpu.reg_read(UC_M68K_REG_D1) & 65535 != next_index or cpu.reg_read(UC_M68K_REG_D0) & 255 != command):
            raise ValueError('Native producer lost captured A0/D1/D0 state')
        if waiting and state['wait_entries'] != 2:
            raise ValueError('Native waiting did not stop at second3aea entry')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        if waiting and expected != ram:
            raise ValueError('Native waiting producer modified RAM')
        result = {'waiting': waiting, 'command': command, 'tail': tail, 'next': next_index}
        return expected, result

    def cpp_compare(ram, expected, result, profile, resume=False, sequence=None):
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        command = ([str(executable), '--resume', str(inp), str(out), str(result['command']),
            str(result['tail']), str(result['next'])] if resume else
            [str(executable), str(inp), str(out), str(result['command'])])
        actual = subprocess.run(command, capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or json.loads(actual.stdout) != result:
            differences = [(hex(at), expected[at], actual_ram[at]) for at in
                range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError('Sound producer mismatch: ' + repr((len(rows), profile, result,
                actual.stdout, actual.stderr, differences[:20])))
        rows.append({'profile': profile, 'sequence': sequence, 'resume': resume,
            'initial_head': struct.unpack_from('>H', ram, 0x4d74)[0],
            'initial_ram_tail': struct.unpack_from('>H', ram, 0x4d76)[0], 'result': result,
            'native_wait_entries': state['wait_entries'],
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest()})

    for command in range(256):
        ram = fixture(command & 127, bool(command & 128))
        expected, result = original_start(ram, command)
        cpp_compare(ram, expected, result, 'all-command-bytes')
    for tail, waiting in itertools.product(range(128), (False, True)):
        ram = fixture(tail, waiting)
        expected, result = original_start(ram, 0x55)
        cpp_compare(ram, expected, result, 'all-tail-positions-ready-wait-ring-wrap')
    for head, tail in ((128, 65535), (65535, 128), (65535, 65535), (0, 32768)):
        ram = fixture(tail, head=head)
        expected, result = original_start(ram, 3)
        cpp_compare(ram, expected, result, 'special3-bypasses-invalid-indices')
    isolated = len(rows)

    # Save actual producer CPU state at3aea. A separate native consumer runs on
    # the same RAM, after which restoring CPU registers resumes captured A0/D1/D0.
    for tail in (0, 127):
        ram = fixture(tail, True)
        for index in range(128):
            ram[0x4cf4 + index] = (index * 17) & 255
        label, begin = 'consumer-frees-captured-tail-%d' % tail, len(rows)
        expected, pending = original_start(ram, 0x42)
        cpp_compare(ram, expected, pending, 'producer-wait-before-consumer', sequence=label)
        producer_context = cpu.context_save()
        state.update(wait_entries=0, status_reads=0)
        writes.clear()
        cpu.reg_write(UC_M68K_REG_A7, 0x1fcffc)
        cpu.mem_write(0x1fcffc, RETURN.to_bytes(4, 'big'))
        cpu.emu_start(CONSUMER, RETURN, count=10000)
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN or state['status_reads'] != 1:
            raise ValueError('Native intervening consumer failed return/read count')
        after_consumer = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(expected)
        for path in (out, port_out):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(consumer), str(inp), str(out), str(port_out), '0'], capture_output=True, text=True)
        if result.returncode or out.read_bytes() != after_consumer or port_out.read_bytes() != expected_ports or json.loads(result.stdout) != {'writes': len(writes)}:
            raise ValueError('Intervening consumer wholeRAM/port mismatch')
        cpu.context_restore(producer_context)
        state.update(wait_entries=0, status_reads=0)
        writes.clear()
        cpu.emu_start(WAIT, RETURN, count=1000)
        final_ram, resumed = original_result(after_consumer, pending['command'], pending['tail'])
        if resumed['waiting']:
            raise ValueError('Native producer did not resume after consumer freed space')
        cpp_compare(after_consumer, final_ram, resumed, 'native-context-resume-after-consumer', True, label)
        sequences.append({'label': label, 'producer_cases': len(rows) - begin,
            'native_context_save_restore_used': True, 'consumer_ram_and_ports_equal': True,
            'consumer_ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
    # Artificial host changes to RAMtail cannot change the captured write target.
    ram = fixture(127, True)
    expected, pending = original_start(ram, 0x7e)
    cpp_compare(ram, expected, pending, 'captured-tail-before-host-mutation')
    producer_context = cpu.context_save()
    for changed_tail, new_head in ((53, 0), (65535, 1)):
        modified = bytearray(expected)
        struct.pack_into('>HH', modified, 0x4d74, new_head, changed_tail)
        cpu.mem_write(RAM_BASE, bytes(modified))
        cpu.context_restore(producer_context)
        state.update(wait_entries=0, status_reads=0)
        writes.clear()
        cpu.emu_start(WAIT, RETURN, count=1000)
        final_ram, resumed = original_result(modified, pending['command'], pending['tail'])
        cpp_compare(modified, final_ram, resumed, 'captured-tail-survives-artificial-ram-tail-change', True)
        if not resumed['waiting'] and (final_ram[0x4cf4 + 127] != 0x7e or final_ram[0x4d76:0x4d78] != b'\0\0'):
            raise ValueError('Native resume recomputed captured tail from current RAM')

    sentinel = b'previous-sound-byte-output\0\xff'

    def reject(command, failure):
        out.write_bytes(sentinel)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Sound producer rejection changed output: ' + failure)
        negatives.append({'failure': failure, 'outputs_preserved': True,
                          'stderr': result.stderr.strip(), 'original_executed': False})

    for head, tail in ((128, 0), (0, 128), (65535, 0), (0, 65535)):
        inp.write_bytes(fixture(tail, head=head))
        reject([str(executable), str(inp), str(out), '2'], 'used-invalid-indices')
    inp.write_bytes(fixture(0))
    for command, tail, next_index in ((3, 0, 1), (2, 128, 1), (2, 0, 2), (2, 127, 128)):
        reject([str(executable), '--resume', str(inp), str(out), str(command), str(tail), str(next_index)],
               'invalid-captured-pending-state')
    inp.write_bytes(fixture(0, head=128))
    reject([str(executable), '--resume', str(inp), str(out), '2', '0', '1'], 'invalid-current-head-on-resume')
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        reject([str(executable), str(inp), str(out), '2'], 'invalid-ram-size%d' % size)
    good = fixture(0)
    inp.write_bytes(good)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        result = subprocess.run([str(executable), str(inp), str(alias), '2'], capture_output=True, text=True)
        if result.returncode == 0 or inp.read_bytes() != good:
            raise ValueError('Sound producer output alias changed input')
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name, 'input_preserved': True,
                          'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program bytes changed')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'wait_resume_cpu_address': WAIT, 'consumer_cpu_address': CONSUMER,
        'address_mapping': 'Fixed CPU addresses equal decrypted ROM offsets.',
        'cases': len(rows), 'isolated_cases': isolated, 'whole_65536_byte_ram_equal': True,
        'waiting_command_tail_next_equal': True, 'all256_commands_and128_tail_positions_checked': True,
        'waiting_second_entry_and_captured_a0_d1_d0_asserted': True,
        'special3_bypasses_invalid_indices': True, 'output_carry_sequences': sequences,
        'actual_producer_context_save_restore_and_native_consumer_compared': True,
        'artificial_ram_tail_change_uses_captured_position': True,
        'negative_cases': len(negatives), 'negative_results': negatives,
        'invalid_used_indices_and_pending_state_preserve_outputs': True, 'results': rows,
        'scope': 'Native3ac8 sound-byte enqueue. Special low-byte3 sets4d7bff without '
            'queue access. Ordinary commands capture tail/A0 and masked next/D1, wait at3aea '
            'while head equals next, then write captured position and publish next tail. '
            'Allbyte commands and tail positions compared with wholeRAM. Actual CPU context '
            'saved at wait, native3cb2 consumes sameRAM, then restored producer resumes. '
            'Artificial host RAMtail mutation is explicit and does not establish natural '
            'producer concurrency. Invalid used indices/pending state are unsupported API '
            'inputs. CPU flags/other registers, Z80 execution, command meaning, physical '
            'audio/timing and natural caller scheduling excluded.'}, indent=2) + '\n')
    print('Sound byte producer original/C++ match:', len(rows), 'cases;', len(sequences),
          'native consumer/resume sequences;', len(negatives), 'preservation failures')


if __name__ == '__main__':
    main()
