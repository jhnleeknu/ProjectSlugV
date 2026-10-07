"""Compare unmodified native3af8/3c08 and suspended3aea word-queue paths."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK, WAIT, EXTERNAL = 0x100000, 0xff000, 0x1feffc, 0x3aea, 0xd00046
KEYS = ('kind', 'phase', 'low', 'cursor', 'command', 'tail', 'next')


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/sound_word'
    folder = root / 'artifacts/sound_word'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0xd00000, 0x1000)
    state = {'wait': 0, 'external': 0, 'reads': 0}
    rows, negatives, sequences = [], [], []

    def hook(cpu, address, size, user):
        head = int.from_bytes(cpu.mem_read(BASE + 0x4d74, 2), 'big')
        if head == cpu.reg_read(UC_M68K_REG_D1) & 65535:
            state['wait'] += 1
            if state['wait'] == 2:
                cpu.emu_stop()
        else:
            state['wait'] = 0

    def read(cpu, access, address, size, value, user):
        assert size == 1
        state['reads'] += 1
        cpu.mem_write(EXTERNAL, bytes([state['external']]))

    cpu.hook_add(UC_HOOK_CODE, hook, begin=WAIT, end=WAIT)
    cpu.hook_add(UC_HOOK_MEM_READ, read, begin=EXTERNAL, end=EXTERNAL)

    def word(ram, offset, value):
        struct.pack_into('>H', ram, offset, value)

    def fixture(head=0, tail=0, bytehead=0, bytetail=0, slots=(0x0455, 0x0566, 0x0677, 0x0788)):
        ram = bytearray(hashlib.shake_256(b'ms5-sound-word-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        for offset in (0x12, 0xfd82, 0xfe80, 0xfd8d, 0x4d7e, 0xf001, 0x4d7b):
            ram[offset] = 0
        struct.pack_into('>4H', ram, 0x4d82, *slots)
        struct.pack_into('>HH', ram, 0x4d8a, head, tail)
        struct.pack_into('>HH', ram, 0x4d74, bytehead, bytetail)
        return ram

    def native_result(kind):
        pc = cpu.reg_read(UC_M68K_REG_PC)
        assert pc in (RETURN, WAIT), hex(pc)
        result = dict.fromkeys(KEYS, 0)
        if pc == WAIT:
            sp = cpu.reg_read(UC_M68K_REG_A7)
            ret = int.from_bytes(cpu.mem_read(sp, 4), 'big')
            phase = 1 if ret in (0x3c00, 0x3c2c) else 2
            assert ret in (0x3c00, 0x3c2c, 0x3c32, RETURN), hex(ret)
            assert (kind == 1 and ret in (0x3c00, RETURN)) or (kind == 2 and ret in (0x3c2c, 0x3c32))
            low = cpu.mem_read(sp + 4, 1)[0] if phase == 1 else cpu.reg_read(UC_M68K_REG_D0) & 255
            cursor = int.from_bytes(cpu.mem_read(sp + (6 if phase == 1 else 4), 2), 'big') if kind == 2 else 0
            tail = cpu.reg_read(UC_M68K_REG_A0) - BASE - 0x4cf4
            result.update(kind=kind, phase=phase, low=low, cursor=cursor,
                command=cpu.reg_read(UC_M68K_REG_D0) & 255, tail=tail,
                next=cpu.reg_read(UC_M68K_REG_D1) & 65535)
            assert state['wait'] == 2
            assert 0 <= tail < 128 and result['next'] == (tail + 1) & 127
        return bytes(cpu.mem_read(BASE, 65536)), result

    def start(ram, action, command=0x0455, external=0):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, STACK), (UC_M68K_REG_D0, 0xbeef0000 | command),
                (UC_M68K_REG_D1, 0xcafeffff)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        state.update(wait=0, external=external, reads=0)
        cpu.emu_start(0x3af8 if action == 'enqueue' else 0x3c08, RETURN, count=10000)
        high = command & 0xff00
        expected_reads = int(action == 'enqueue' and command < 0x2000 and command & 255 >= 0x20 and high not in (0x100, 0x200, 0x300) and ram[0x12] == 1 and high != 0 and ram[0xfd82] != 0 and ram[0xfe80] == 0)
        assert state['reads'] == expected_reads, (action, command, state['reads'], expected_reads)
        return native_result(1 if action == 'enqueue' else 2)

    def compare(ram, expected, result, action, command=0x0455, external=0, pending=None, profile='matrix'):
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        args = [str(executable), action, str(inp), str(out)]
        if action == 'enqueue':
            args += [str(command), str(external)]
        elif action == 'resume':
            args += [str(pending[key]) for key in KEYS]
        actual = subprocess.run(args, capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or json.loads(actual.stdout) != result:
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, action, command, pending, result, actual.stdout, actual.stderr, diff[:20])))
        rows.append({'profile': profile, 'action': action, 'command': command, 'external': external,
            'native_external_reads': state['reads'], 'pending': pending, 'result': result,
            'ram_changed': bytes(ram) != expected, 'input_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest()})

    commands = (0, 0x1f, 0x20, 0xff, 0x100, 0x120, 0x1ff, 0x220, 0x320, 0x420,
        0xfff, 0x1000, 0x1020, 0x1fff, 0x2000, 0xffff)
    for command, mode, fd82, fe80, fd8d, block, bit5, external in itertools.product(
            commands, (0, 1), (0, 1), (0, 1), (0, 1), (0, 1), (0, 32), (0, 1)):
        ram = fixture()
        ram[0x12], ram[0xfd82], ram[0xfe80], ram[0xfd8d], ram[0x4d7e], ram[0xf001] = mode, fd82, fe80, fd8d, block, bit5
        expected, result = start(ram, 'enqueue', command, external)
        compare(ram, expected, result, 'enqueue', command, external, profile='native-filter-branches')
    for head, tail in itertools.product((0, 2, 4, 6), repeat=2):
        for command in (0x0455, 0x0566, 0x0677, 0x0788, 0x0866):
            ram = fixture(head, tail)
            expected, result = start(ram, 'enqueue', command)
            compare(ram, expected, result, 'enqueue', command, profile='duplicate-one-following-slot-append-overflow')
    for head, tail, slots in itertools.product((0, 2, 4, 6), (0, 2, 4, 6),
            ((0, 0, 0, 0), (0x0303, 0x0355, 0x5503, 0x1234), (0x0455, 0x0566, 0x0677, 0x0788))):
        ram = fixture(head, tail, slots=slots)
        expected, result = start(ram, 'drain')
        compare(ram, expected, result, 'drain', profile='drain-zero-special3-ring-positions')
    for head in (0, 2, 4, 6):
        ram = fixture(head, (head + 6) & 6, bytehead=65535, bytetail=65535, slots=(0, 0, 0, 0))
        expected, result = start(ram, 'enqueue', 0x0866)
        compare(ram, expected, result, 'enqueue', 0x0866, profile='overflow-zero-skips-invalid-byte-indices')
    isolated = len(rows)

    # Stop inside the original byte producer, retain its CPU context and stack,
    # then host-edit only explicitly specified queue fields before resuming.
    for action, bytetail, bytehead, first in itertools.product(('enqueue', 'drain'), (0, 127), (1, 2), (0x0455, 0x0303, 0x0355, 0x5503)):
        ram = fixture(0, 6 if action == 'enqueue' else 4, bytehead=(bytetail + bytehead) & 127,
            bytetail=bytetail, slots=(first, 0x0566, 0x0677, 0x0788))
        label, begin = '%s-tail%d-headstep%d-first%x' % (action, bytetail, bytehead, first), len(rows)
        expected, pending = start(ram, action)
        compare(ram, expected, pending, action, profile=label)
        steps = 0
        while pending['kind']:
            saved = cpu.context_save()
            changed = bytearray(expected)
            word(changed, 0x4d74, (pending['next'] + 4) & 127)
            # The captured byte position and low byte survive a changed live tail.
            word(changed, 0x4d76, 53)
            if pending['kind'] == 2:
                word(changed, 0x4d8a, 65535)  # Native drain never rereads head.
                word(changed, 0x4d8c, (pending['cursor'] + 2) & 6)
                word(changed, 0x4d82 + pending['cursor'], 0xaabb)
            cpu.mem_write(BASE, bytes(changed))
            cpu.context_restore(saved)
            state.update(wait=0, reads=0)
            cpu.emu_start(WAIT, RETURN, count=10000)
            final, result = native_result(pending['kind'])
            compare(changed, final, result, 'resume', pending=pending, profile='host-edit-captured-low-cursor-live-tail')
            expected, pending = final, result
            steps += 1
            assert steps <= 8
        sequences.append({'label': label, 'cases': len(rows) - begin, 'resumes': steps,
            'actual_cpu_context_and_stack_preserved': True, 'external_host_mutations_explicit': True})

    assert any(row['action'] == 'enqueue' and row['result']['kind'] == 1 for row in rows)
    assert any(row['profile'] == 'duplicate-one-following-slot-append-overflow' and row['ram_changed'] for row in rows)
    assert any(row['result']['phase'] == 2 for row in rows)
    assert any(row['native_external_reads'] == 1 for row in rows)
    ram = fixture(0, 2, bytehead=1)
    expected, pending = start(ram, 'drain')
    compare(ram, expected, pending, 'drain', profile='high-then-low-wait-carry')
    assert pending['phase'] == 1
    for head in (2, 4):
        saved = cpu.context_save()
        changed = bytearray(expected)
        word(changed, 0x4d74, head)
        cpu.mem_write(BASE, bytes(changed))
        cpu.context_restore(saved)
        state.update(wait=0, reads=0)
        cpu.emu_start(WAIT, RETURN, count=10000)
        final, result = native_result(2)
        compare(changed, final, result, 'resume', pending=pending, profile='high-then-low-wait-carry')
        assert result['phase'] == (2 if head == 2 else 0)
        expected, pending = final, result
    sentinel = b'previous-word-output\0\xff'
    def reject(ram, action, fields, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        result = subprocess.run([str(executable), action, str(inp), str(out)] + [str(value) for value in fields], capture_output=True, text=True)
        assert result.returncode and out.read_bytes() == sentinel, (label, result.stdout, result.stderr)
        negatives.append({'failure': label, 'output_preserved': True, 'original_executed': False, 'stderr': result.stderr.strip()})

    for offset in (0x4d8a, 0x4d8c, 0x4d74, 0x4d76):
        for bad in (1 if offset < 0x4d74 or offset >= 0x4d8a else 128, 65535):
            ram = fixture(0, 6)
            word(ram, offset, bad)
            reject(ram, 'enqueue', (0x0866, 0), 'invalid-used-index-%x' % offset)
    for head, tail in ((1, 0), (0, 8), (65535, 0), (0, 65535)):
        reject(fixture(head, tail), 'drain', (), 'invalid-word-drain-indices')
    for fields in ((0, 1, 55, 0, 42, 0, 1), (1, 3, 55, 0, 42, 0, 1),
            (2, 1, 55, 1, 42, 0, 1), (1, 1, 55, 0, 3, 0, 1),
            (1, 1, 55, 0, 42, 128, 1), (1, 1, 55, 0, 42, 0, 2)):
        reject(fixture(), 'resume', fields, 'invalid-pending-state')
    for size in (0, 65535, 65537):
        reject(bytes(size), 'drain', (), 'invalid-ram-size')
    ram = fixture(0, 2, bytehead=1)
    suspended, pending = start(ram, 'drain')
    late = bytearray(suspended)
    word(late, 0x4d74, 4)
    word(late, 0x4d8c, 65535)
    reject(late, 'resume', [pending[key] for key in KEYS], 'late-invalid-live-tail-after-pair-writes')
    good = fixture()
    inp.write_bytes(good)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), 'drain', str(inp), str(alias)], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == good
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name,
            'input_preserved': True, 'original_executed': False})
    # Filtered words return before accessing even unsupported queue indices.
    for command in (0x1f, 0x120, 0x220, 0x320, 0x2000, 0xffff):
        ram = fixture(65535, 65535, 65535, 65535)
        expected, result = start(ram, 'enqueue', command)
        compare(ram, expected, result, 'enqueue', command, profile='filtered-invalid-indices-bypassed')
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_addresses': [0x3af8, 0x3c08],
        'entry_rom_offsets': [0x3af8, 0x3c08], 'wait_resume_cpu_address': WAIT,
        'cases': len(rows), 'isolated_cases': isolated, 'negative_cases': len(negatives),
        'whole_65536_byte_ram_equal': True, 'pending_all_fields_equal': True, 'conditional_external_read_count_asserted': True,
        'high_wait_then_low_wait_then_completion_carry': True, 'late_invalid_live_tail_preserves_output': True,
        'native_context_and_stack_resume': True, 'output_carry_sequences': sequences,
        'negative_results': negatives, 'results': rows,
        'scope': 'Native word enqueue/drain and original suspended byte producer. '
            'Native filter code, conditional d00046 byte read, one-following-slot duplicate swap, '
            'ring overflow, zero skips and special3 compared. Explicit host queue changes exercise '
            'captured low/cursor/byte-position and live drain tail; these do not establish natural '
            'producer concurrency. Completed pending uses canonical all-zero API representation. '
            'Invalid used indices/pending states are unsupported API inputs. CPU flags, other '
            'register outputs, physical sound, natural caller scheduling and hardware timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
