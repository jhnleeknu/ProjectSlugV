"""Compare continuous native3cac timer, word producer and sound consumer."""
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

BASE, RETURN, STACK, WAIT, PORT, EXTERNAL = 0x100000, 0xff000, 0x1feffc, 0x3aea, 0x320000, 0xd00046
KEYS = ('kind', 'phase', 'low', 'cursor', 'command', 'tail', 'next')


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/step_sound'
    folder = root / 'artifacts/sound_service'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(PORT, 0x1000)
    cpu.mem_map(0xd00000, 0x1000)
    state = {'wait': 0, 'external': 0, 'external_reads': 0, 'status': 0, 'reads': 0}
    writes, rows, negatives, sequences = [], [], [], []

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
        if address == EXTERNAL:
            state['external_reads'] += 1
            cpu.mem_write(EXTERNAL, bytes([state['external']]))
        else:
            state['reads'] += 1
            cpu.mem_write(PORT, bytes([state['status']]))

    def write(cpu, access, address, size, value, user):
        writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    cpu.hook_add(UC_HOOK_CODE, hook, begin=WAIT, end=WAIT)
    cpu.hook_add(UC_HOOK_MEM_READ, read, begin=PORT, end=PORT)
    cpu.hook_add(UC_HOOK_MEM_READ, read, begin=EXTERNAL, end=EXTERNAL)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write, begin=PORT, end=PORT)

    def word(ram, offset, value):
        struct.pack_into('>H', ram, offset, value)

    def fixture(timer=0, head=0, tail=0, bytehead=0, bytetail=0):
        ram = bytearray(hashlib.shake_256(b'ms5-sound-service-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        for offset in (0x12, 0xfd82, 0xfe80, 0xfd8d, 0x4d7e, 0xf001, 0x4d7b, 0xf003):
            ram[offset] = 0
        struct.pack_into('>4H', ram, 0x4d82, 0x0455, 0x0566, 0x0677, 0x0788)
        struct.pack_into('>HH', ram, 0x4d8a, head, tail)
        struct.pack_into('>HH', ram, 0x4d74, bytehead, bytetail)
        word(ram, 0xd68c, timer)
        return ram

    def result():
        pc = cpu.reg_read(UC_M68K_REG_PC)
        assert pc in (RETURN, WAIT), hex(pc)
        pending = dict.fromkeys(KEYS, 0)
        if pc == WAIT:
            sp = cpu.reg_read(UC_M68K_REG_A7)
            ret = int.from_bytes(cpu.mem_read(sp, 4), 'big')
            assert ret in (0x3c00, 0x4817e), hex(ret)
            phase = 1 if ret == 0x3c00 else 2
            low = cpu.mem_read(sp + 4, 1)[0] if phase == 1 else cpu.reg_read(UC_M68K_REG_D0) & 255
            tail = cpu.reg_read(UC_M68K_REG_A0) - BASE - 0x4cf4
            pending.update(kind=1, phase=phase, low=low, cursor=0,
                command=cpu.reg_read(UC_M68K_REG_D0) & 255, tail=tail,
                next=cpu.reg_read(UC_M68K_REG_D1) & 65535)
            assert state['wait'] == 2 and state['reads'] == 0 and not writes
            assert 0 <= tail < 128 and pending['next'] == (tail + 1) & 127
        else:
            assert state['reads'] == 1
        pending.update(read_count=state['reads'], writes=len(writes))
        return bytes(cpu.mem_read(BASE, 65536)), b''.join(struct.pack('>BII', *event) for event in writes), pending

    def start(ram, external=0, status=0):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, STACK), (UC_M68K_REG_D0, 0xbeefffff), (UC_M68K_REG_D1, 0xcafeffff)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        state.update(wait=0, external=external, external_reads=0, status=status, reads=0)
        writes.clear()
        cpu.emu_start(0x3cac, RETURN, count=10000)
        return result()

    def compare(ram, expected, expected_ports, pending, external=0, status=0, previous=None, profile='matrix'):
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        args = [str(executable), 'resume' if previous else 'step', str(inp), str(out), str(ports)]
        args += [str(status)] + [str(previous[key]) for key in KEYS] if previous else [str(external), str(status)]
        actual = subprocess.run(args, capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or not ports.exists() or ports.read_bytes() != expected_ports or json.loads(actual.stdout) != pending:
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, previous, pending, actual.stdout, actual.stderr, diff[:20])))
        rows.append({'profile': profile, 'resume': bool(previous), 'external': external, 'status': status,
            'native_external_reads': state['external_reads'], 'result': pending,
            'input_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    timers = (0, 1, 15, 16, 0x7fff, 0x8000, 0xffff, 0xf65f, 0xf660, 0xf760, 0xe63f, 0xe640, 0xe65f, 0xe660,
        0xe740, 0xe760, 0xe840, 0xe860, 0xe940, 0xe960)
    for timer, status, flags in itertools.product(timers, (0, 1, 2, 128, 255), (0, 1, 2, 3)):
        ram = fixture(timer, head=2, tail=0, bytehead=125, bytetail=3)
        ram[0x4d7b], ram[0xf003] = (255 if flags & 1 else 0), (255 if flags & 2 else 0)
        expected, event_bytes, pending = start(ram, status=status)
        compare(ram, expected, event_bytes, pending, status=status, profile='signed-timer-boundaries-consumer-priorities')
    for status in range(256):
        ram = fixture(timers[status % len(timers)], bytehead=127, bytetail=2)
        ram[0x4cf4 + 127], ram[0x4cf4], ram[0x4cf4 + 1] = 0x44, 0x44, 0x45
        expected, event_bytes, pending = start(ram, status=status)
        compare(ram, expected, event_bytes, pending, status=status, profile='all-status-bytes-wrap-dedup')
    for fd82, fe80, fd8d, external in itertools.product((0, 255), repeat=4):
        ram = fixture(1)
        ram[0x12], ram[0xfd82], ram[0xfe80], ram[0xfd8d] = 1, fd82, fe80, fd8d
        expected, event_bytes, pending = start(ram, external, 0)
        assert state['external_reads'] == int(fd82 != 0 and fe80 == 0)
        compare(ram, expected, event_bytes, pending, external, profile='conditional-external-native-read')
    isolated = len(rows)

    ram = fixture(1)
    begin = len(rows)
    for frame in range(40):
        expected, event_bytes, pending = start(ram, status=frame % 3)
        assert pending['kind'] == 0
        compare(ram, expected, event_bytes, pending, status=frame % 3, profile='40-continuous-carried-service-ticks')
        ram = expected
    sequences.append({'profile': '40-continuous-carried-service-ticks', 'cases': len(rows) - begin})

    for tail in (0, 127):
        ram = fixture(1, tail=6, bytehead=(tail + 1) & 127, bytetail=tail)
        begin = len(rows)
        expected, event_bytes, pending = start(ram, external=255, status=1)
        compare(ram, expected, event_bytes, pending, external=255, status=1, profile='producer-high-wait')
        assert pending['phase'] == 1
        for headstep, status in ((2, 255), (4, 0)):
            saved = cpu.context_save()
            changed = bytearray(expected)
            word(changed, 0x4d74, (tail + headstep) & 127)
            word(changed, 0xd68c, 0x4567)
            word(changed, 0x4d76, 53)  # Explicit host change, captured position stays valid.
            cpu.mem_write(BASE, bytes(changed))
            cpu.context_restore(saved)
            state.update(wait=0, external_reads=0, status=status, reads=0)
            writes.clear()
            cpu.emu_start(WAIT, RETURN, count=10000)
            final, event_bytes, resumed = result()
            assert state['external_reads'] == 0 and final[0xd68c:0xd68e] == b'\x45\x67'
            assert resumed['phase'] == (2 if headstep == 2 else 0)
            compare(changed, final, event_bytes, resumed, status=status, previous=pending, profile='same-native-context-high-low-complete')
            expected, pending = final, resumed
        sequences.append({'profile': 'same-native-context-tail%d' % tail, 'cases': len(rows) - begin,
            'native_context_and_stack_preserved': True, 'resume_timer_and_external_not_resampled': True})

    sentinel = b'previous-service-output\0\xff'
    def reject(ram, action, fields, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        actual = subprocess.run([str(executable), action, str(inp), str(out), str(ports)] + [str(v) for v in fields], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False, 'stderr': actual.stderr.strip()})

    for timer in (0, 1, 16):
        ram = fixture(timer, bytehead=128, bytetail=0)
        reject(ram, 'step', (0, 0), 'late-consumer-invalid-index-rolls-back-timer-word-production')
    for offset in (0x4d8a, 0x4d8c, 0x4d74, 0x4d76):
        ram = fixture(1, tail=6)
        word(ram, offset, 65535)
        reject(ram, 'step', (0, 0), 'producer-invalid-used-index')
    for fields in ((0, 1, 55, 0, 4, 0, 1), (2, 1, 55, 0, 4, 0, 1), (1, 2, 55, 0, 4, 0, 1)):
        reject(fixture(), 'resume', (0,) + fields, 'invalid-pending')
    for size in (0, 65535, 65537):
        reject(bytes(size), 'step', (0, 0), 'invalid-ram-size')
    good = fixture()
    inp.write_bytes(good)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), 'step', str(inp), str(alias), str(ports), '0', '0'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == good
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': 0x3cac,
        'entry_rom_offset': 0x3cac, 'wait_resume_cpu_address': WAIT,
        'cases': len(rows), 'isolated_cases': isolated, 'negative_cases': len(negatives),
        'whole_65536_byte_ram_equal': True, 'ordered_hardware_ports_equal': True,
        'pending_read_count_writes_equal': True, 'waiting_consumer_reads_zero_done_one': True,
        'resume_timer_and_external_not_resampled': True, 'output_carry_sequences': sequences,
        'negative_results': negatives, 'results': rows,
        'scope': 'Continuous original3cac including48156 timer,3af8 word producer, suspended '
            '3aea byte producer and3cb2 consumer. Native CPU context and original stack retained '
            'for resume. Explicit host changes to queue fields and timer exercise suspension '
            'without claiming natural scheduling. FullRAM, pending and ordered320000 writes '
            'compared. CPU flags/register outputs, natural interrupt restoration, Z80 execution, '
            'physical audio and hardware timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
