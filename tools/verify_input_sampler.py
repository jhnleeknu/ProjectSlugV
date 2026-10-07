"""Compare native31d6 input sampling and long playback with unmodified M68000."""
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
from verify_stage_catalog import SOURCE_SHA256, checked_resource

RAM_BASE, RETURN, ENTRY, STREAM_BASE, STREAM_END = 0x100000, 0xff000, 0x31d6, 0xf01fe, 0xf1a0e
STREAMS = (0xf01fe, 0xf07fe)
WINDOW_BEGIN, WINDOW_END = 0x4ca8, 0x4cd6
PORT_ADDRESSES = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256 or program[0x180:0x182] != b'\0\0':
        raise ValueError('Unsupported ROM or native playback selector')
    resource = root / 'extracted/runtime/input_streams.ms5d'
    resource_hash = checked_resource(resource, program, STREAM_BASE, STREAM_END)
    executable = root / 'build/sample_input'
    if not executable.exists():
        raise ValueError('Build build/sample_input first')
    folder = root / 'artifacts/input_sampler'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, trace_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.trace.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x340000, 0x380000):
        cpu.mem_map(address, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    samples, reads, write_violations, helper_hits, replay_reads = [], [], [], [], []
    rows, sequences, negatives = [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address not in PORT_ADDRESSES:
            return
        ordinal = len(reads)
        if ordinal >= len(samples) or address != PORT_ADDRESSES[ordinal] or size != 1:
            raise ValueError('Native MMIO read ordering/width differs: ' + repr((reads, address, size)))
        cpu.mem_write(address, bytes((samples[ordinal],)))
        reads.append((address, samples[ordinal]))

    def write_hook(cpu, access, address, size, value, user):
        if RAM_BASE <= address < RAM_BASE + 65536 and not (
                RAM_BASE + WINDOW_BEGIN <= address and address + size <= RAM_BASE + WINDOW_END):
            write_violations.append((address, size, value))
        if address in PORT_ADDRESSES or address == 0x300001:
            write_violations.append((address, size, value))

    def replay_read_hook(cpu, access, address, size, value, user):
        replay_reads.append((address, size))

    def code_hook(cpu, address, size, user):
        helper_hits.append(address)

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x300000, end=0x380000)
    cpu.hook_add(UC_HOOK_MEM_READ, replay_read_hook, begin=0xf0000, end=0xf1b00)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, code_hook, begin=0x352a, end=0x352a)
    cpu.hook_add(UC_HOOK_CODE, code_hook, begin=0x349c, end=0x349c)

    def fixture(mode=0, timer=0, pointer=STREAMS[0], index=0, previous=0, duration=0):
        ram = bytearray(hashlib.shake_256(b'ms5-input-sampler-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0x4cd4] = mode
        struct.pack_into('>I', ram, 0x4cc4, pointer)
        struct.pack_into('>HH', ram, 0x4ccc, previous, index)
        ram[0x4cd0] = duration
        for at in (0x4cbb, 0x4cc1, 0x4cad, 0x4cb3):
            ram[at] = timer
        ram[0x4cd2], ram[0x4cd3] = (0, 1, 2, 255)[timer % 4], (255, 2, 1, 0)[timer % 4]
        ram[0xfd94], ram[0xfd9a] = 0xa5, 0x5a
        return ram

    def original_frame(current_samples, expected_reads):
        samples[:] = current_samples[:expected_reads]
        reads.clear()
        helper_hits.clear()
        replay_reads.clear()
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        cpu.emu_start(ENTRY, RETURN, count=100000)
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN or len(reads) != expected_reads:
            raise ValueError('Native sampler failed return/read-count assertion')
        if write_violations:
            raise ValueError('Native sampler wrote outside input state: ' + repr(write_violations[:10]))

    def compare(ram, current_samples, profile):
        mode = ram[0x4cd4]
        expected_reads = 5 if mode == 0 else 3
        cpu.mem_write(RAM_BASE, bytes(ram))
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(UC_M68K_REG_D0, 0xdeadbeef)
        write_violations.clear()
        original_frame(current_samples, expected_reads)
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        if helper_hits != ([0x352a] if mode == 1 else []):
            raise ValueError('Native selector did not choose exact playback helper')
        inp.write_bytes(ram)
        outside_reads = [(address, size) for address, size in replay_reads if
                         address < STREAM_BASE or address + size > STREAM_END]
        if outside_reads:
            sentinel = b'prior-output-for-native-read-outside-resource'
            out.write_bytes(sentinel)
            result = subprocess.run([str(executable), str(inp), str(resource), str(out)] +
                [str(value) for value in current_samples], capture_output=True, text=True)
            if result.returncode == 0 or out.read_bytes() != sentinel:
                raise ValueError('Native read outside retained window was accepted/published')
            negatives.append({'failure': 'native-replay-read-outside-retained-window',
                'original_executed': True, 'profile': profile,
                'actual_replay_reads': replay_reads.copy(), 'outside_reads': outside_reads,
                'pointer': struct.unpack_from('>I', ram, 0x4cc4)[0],
                'cursor': struct.unpack_from('>H', ram, 0x4cce)[0],
                'previous_cursor': struct.unpack_from('>H', ram, 0x4ccc)[0],
                'duration': ram[0x4cd0], 'outputs_preserved': True,
                'stderr': result.stderr.strip()})
            return bytearray(expected)
        out.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(resource), str(out)] +
            [str(value) for value in current_samples], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr)))
        actual = out.read_bytes()
        if actual != expected or json.loads(result.stdout) != {'read_count': expected_reads}:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Sampler mismatch: ' + repr((len(rows), profile, mode,
                current_samples, differences[:20], result.stdout)))
        if expected[0xfd94] != ram[0xfd94] or expected[0xfd9a] != ram[0xfd9a]:
            raise ValueError('Sampler changed metadata sources')
        if mode != 0 and (expected[0x4ca8] != ram[0x4ca8] or expected[0x4cae] != ram[0x4cae]):
            raise ValueError('Non-hardware game mode overwrote metadata copies')
        rows.append({'profile': profile, 'mode': mode, 'samples': current_samples,
            'read_count': expected_reads, 'actual_mmio_reads': reads.copy(),
            'actual_helpers': helper_hits.copy(), 'actual_replay_reads': replay_reads.copy(), 'replay_pointer': struct.unpack_from('>I', ram, 0x4cc4)[0],
            'cursor': struct.unpack_from('>H', ram, 0x4cce)[0], 'duration': ram[0x4cd0],
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected)

    for value, mode, timer in itertools.product(range(256), (0, 1, 2, 255), (0, 1, 2, 255)):
        ram = fixture(mode, timer, pointer=STREAMS[len(rows) % 2])
        current_samples = [value, value ^ 0x55, value ^ 0xaa, (value * 17 + 3) & 255,
                           (value * 29 + 11) & 255]
        old = (0, 255, 0x55, 0xaa)[value % 4]
        for at in (0x4cb4, 0x4cb8, 0x4cbe, 0x4caa, 0x4cb0):
            ram[at] = old
        compare(ram, current_samples, 'all-input-bytes-modes-repeat-edges')
    for pointer, cursor, previous, duration in itertools.product(STREAMS,
            (0, 1, 0x5fe, 0x5ff, 0x600, 0xffff), (0, 1, 0x5ff, 0xffff), (0, 15, 255)):
        compare(fixture(1, 1, pointer, cursor, previous, duration),
                [0, 0x12, 0x34, 0x56, 0x78], 'replay-cursor-duration-terminal-boundaries')
    # Signed d0.w previous cursor -1 can read the byte before the second
    # native buffer because that byte is still within the retained resource.
    compare(fixture(1, 1, STREAMS[1], 0, 0xffff, program[STREAMS[1]]),
            [255] * 5, 'signed-previous-minus-one-within-resource')
    for pointer, cursor in itertools.product((0, 0xffffffff), (0x600, 0xffff)):
        compare(fixture(1, 1, pointer, cursor), [255] * 5,
                'exhausted-cursor-bypasses-resource-pointer')
    for pointer in STREAMS:
        compare(fixture(1, 1, pointer, 0x5ff, 0, 255), [255] * 5,
                'native-adjacent-byte-peek-at-offset600')
    threshold_cases = []
    for pointer in STREAMS:
        for threshold, same_previous in ((255, False), (15, True)):
            candidates = [at for at in range(0x600) if (
                program[pointer + at] & (15 if same_previous else 255)) == threshold]
            # Observe native ff/0f continuation including following-zero skips.
            chosen = candidates[:3] + [at for at in candidates if program[pointer + at + 1] == 0][:3]
            for cursor in sorted(set(chosen)):
                compare(fixture(1, 255, pointer, cursor, cursor if same_previous else cursor ^ 1, threshold),
                        [255, 255, 255, 0, 0], 'native-ff-0f-continuation-threshold')
                threshold_cases.append({'pointer': pointer, 'cursor': cursor, 'threshold': threshold,
                                        'following_byte': program[pointer + cursor + 1]})
    isolated = len(rows)
    print('Input sampler matrix matched:', isolated, 'cases', flush=True)
    # A shorter mode0 sequence carries all RAM and distinct second port samples.
    ram = fixture(0, 1)
    begin = len(rows)
    for frame in range(40):
        ram = compare(ram, [255, 255 ^ (frame & 255), 0xaa, frame & 255, 0x55], 'mode0-whole-output-carry')
    sequences.append({'mode': 0, 'frames': len(rows) - begin, 'whole_ram_each_frame': True})

    for pointer in STREAMS:
        ram = fixture(1, 0, pointer)
        # Native replay starts with a zero input word and cursors/duration zero.
        ram[0x4cc2:0x4cc4] = b'\0\0'
        cpu.mem_write(RAM_BASE, bytes(ram))
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        write_violations.clear()
        native_trace = bytearray()
        frames = 0
        for frame in range(2000000):
            original_frame([255] * 5, 3)
            native_trace.extend(cpu.mem_read(RAM_BASE + WINDOW_BEGIN, WINDOW_END - WINDOW_BEGIN))
            native_trace.append(3)
            frames += 1
            if cpu.mem_read(RAM_BASE + 0x4cd4, 1)[0] == 2:
                break
        else:
            raise ValueError('Native replay did not finish within2million frame bound')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        trace_out.unlink(missing_ok=True)
        result = subprocess.run([str(executable), '--playback', str(inp), str(resource), str(out),
            str(trace_out)] + ['255'] * 5 + ['2000000'], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('Playback CLI rejected: ' + result.stderr)
        parsed = json.loads(result.stdout)
        expected_result = {'frames': frames, 'terminated': True, 'read_count': 3}
        actual_trace = trace_out.read_bytes()
        if out.read_bytes() != expected or actual_trace != native_trace or parsed != expected_result:
            first = next((at for at in range(min(len(actual_trace), len(native_trace)))
                          if actual_trace[at] != native_trace[at]), None)
            raise ValueError('Playback trace/finalRAM mismatch: ' + repr(
                (pointer, frames, first, None if first is None else first // 47, parsed)))
        print('Native/C++ playback matched:', hex(pointer), frames, 'frames', flush=True)
        sequences.append({'mode': 1, 'pointer': pointer, 'frames': frames,
            'final_cursor': struct.unpack_from('>H', expected, 0x4cce)[0],
            'final_mode': expected[0x4cd4], 'per_frame_46_byte_state_and_read_count_equal': True,
            'original_writes_outside_input_window_absent': True, 'final_whole_ram_equal': True,
            'trace_sha256': hashlib.sha256(native_trace).hexdigest(),
            'final_ram_sha256': hashlib.sha256(expected).hexdigest()})
    for pointer in (0, STREAM_BASE - 1, STREAM_END, 0xffffffff):
        inp.write_bytes(fixture(1, pointer=pointer))
        sentinel = b'previous-input-sampler-output'
        out.write_bytes(sentinel)
        result = subprocess.run([str(executable), str(inp), str(resource), str(out)] + ['255'] * 5,
                                capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Invalid replay pointer changed output')
        negatives.append({'failure': 'replay-pointer-outside-resource', 'pointer': pointer,
            'outputs_preserved': True, 'stderr': result.stderr.strip(), 'original_executed': False})
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        out.write_bytes(sentinel)
        result = subprocess.run([str(executable), str(inp), str(resource), str(out)] + ['255'] * 5,
                                capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Invalid RAM size changed output')
        negatives.append({'failure': 'invalid-ram-size', 'size': size,
                          'outputs_preserved': True, 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped ROM was modified')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'address_mapping': 'Fixed CPU addresses equal decrypted ROM offsets.',
        'input_resource_sha256': resource_hash, 'native_playback_selector_word': 0,
        'cases': len(rows), 'isolated_cases': isolated, 'whole_65536_byte_ram_equal': True,
        'actual_mmio_read_order_and_active_low_samples_asserted': True,
        'mode0_distinct_second_player_reads_asserted': True,
        'actual_playback352a_without_record349c_asserted': True,
        'metadata_source_and_nonzero_mode_copies_preserved': True,
        'threshold_cases': threshold_cases, 'output_carry_sequences': sequences,
        'negative_cases': len(negatives), 'negative_results': negatives, 'results': rows,
        'scope': 'Unmodified31d6 sampler with supplied active-low MMIO values. Modes0/1/2/255, '
            'all256 values for each port, system nibble/edge and player repeat boundaries, '
            'native playback ff/0f continuation and cursor/terminal boundaries. Native reads '
            'outside the retained window are classified as unsupported resource cases and '
            'must fail without publishing. FullRAM compared per isolated/mode0 carried frame. '
            'Both streams run untilmode2: every46-byte state/read-count trace frame and finalRAM '
            'compared; native writes outside input window absent. Durations are decoder '
            'observations. Recording349c is unreachable withROM180=0. Physical timing, call-site '
            'reachability, other CPU registers/flags and full boot excluded.'}, indent=2) + '\n')
    print('Input sampler original/C++ match:', len(rows), 'whole-RAM cases;',
          sum(sequence['frames'] for sequence in sequences if sequence['mode'] == 1),
          'native playback trace frames;', len(negatives), 'preserved-output failures')


if __name__ == '__main__':
    main()
