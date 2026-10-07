"""Compare nativef12 pre-controller frame prefix and exact propagated D1 word."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

RAM_BASE, ENTRY, CONTROLLER, CALLBACK = 0x100000, 0xf12, 0xf54, 0xf3c
PORT_ADDRESSES = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256 or program[0x180:0x182] != b'\0\0':
        raise ValueError('Unsupported ROM or playback selector')
    streams, table = [root / 'extracted/runtime' / name for name in
                      ('input_streams.ms5d', 'input_status.ms5d')]
    hashes = {'streams': checked_resource(streams, program, 0xf01fe, 0xf1a0e),
              'table': checked_resource(table, program, 0xb58, 0xc58)}
    executable = root / 'build/begin_input_frame'
    if not executable.exists():
        raise ValueError('Build build/begin_input_frame first')
    folder = root / 'artifacts/input_frame'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x340000, 0x380000):
        cpu.mem_map(address, 0x1000)
    samples, reads, trace, events, writes = [], [], [], [], []
    rows, sequences, negatives = [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address not in PORT_ADDRESSES:
            return
        ordinal = len(reads)
        if ordinal >= len(samples) or address != PORT_ADDRESSES[ordinal] or size != 1:
            raise ValueError('Native MMIO read order/width differs')
        cpu.mem_write(address, bytes((samples[ordinal],)))
        reads.append((address, samples[ordinal]))

    def code_hook(cpu, address, size, user):
        if address == 0x3588:
            events.append({'bit': cpu.reg_read(UC_M68K_REG_D0) & 255,
                           'generated_input_word': cpu.reg_read(UC_M68K_REG_D1) & 65535})
        else:
            trace.append(address)
            cpu.emu_stop()

    def write_hook(cpu, access, address, size, value, user):
        if address in PORT_ADDRESSES or address == 0x300001:
            writes.append((address, size, value))

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x300000, end=0x380000)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in (CONTROLLER, CALLBACK, 0x3588):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(mode=0, callback=0, address=0x100f5c, replay='event'):
        ram = bytearray(hashlib.shake_256(b'ms5-input-frame-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0x4cd4] = mode
        struct.pack_into('>I', ram, 0x4cc4, 0xf07fe if replay == 'terminal' else 0xf01fe)
        struct.pack_into('>HH', ram, 0x4ccc, 0, 0x5ff if replay == 'terminal' else 0)
        struct.pack_into('>H', ram, 0x4cc2, 0x1234)
        ram[0x4cd0] = 255 if replay == 'terminal' else 1 if replay == 'noevent' else 0
        for at in (0x4cbb, 0x4cc1, 0x4cad, 0x4cb3):
            ram[at] = (0, 1, 2, 255)[len(rows) % 4]
        ram[0x4cd2], ram[0x4cd3] = 2, 1
        ram[0xfd94], ram[0xfd9a] = 0xa5, 0x5a
        struct.pack_into('>II', ram, address - RAM_BASE + 0x76, callback, 0xdeadbeef)
        return ram

    def arguments(address, style, current_samples, streams_input=streams, table_input=table):
        return [str(executable), str(inp), str(streams_input), str(table_input), str(out),
                str(address), str(style)] + [str(value) for value in current_samples]

    def compare(ram, address, style, current_samples, profile, sequence=None):
        samples[:] = current_samples[:5 if ram[0x4cd4] == 0 else 3]
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, address), (UC_M68K_REG_A7, 0x1feffc),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, 0xbeef0000 | style),
                (UC_M68K_REG_D3, 0xcafe7000)):
            cpu.reg_write(reg, value)
        reads.clear()
        trace.clear()
        events.clear()
        writes.clear()
        cpu.emu_start(ENTRY, 0xff000, count=100000)
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (CONTROLLER, CALLBACK) or trace != [pc] or writes or len(reads) != len(samples):
            raise ValueError('Native input prefix failed boundary/read-count assertion')
        if cpu.reg_read(UC_M68K_REG_A6) != address or cpu.reg_read(UC_M68K_REG_A7) != 0x1feffc:
            raise ValueError('Native input prefix changed caller A6/entry stack')
        if cpu.reg_read(UC_M68K_REG_D3) != 0xcafe7000:
            raise ValueError('Native input prefix changed D3')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        callback = struct.unpack_from('>I', expected, address - RAM_BASE + 0x76)[0]
        expected_pc = CALLBACK if callback else CONTROLLER
        context = struct.unpack_from('>I', expected, address - RAM_BASE + 0x7a)[0] if callback else 0
        if pc != expected_pc:
            raise ValueError('Native callback branch did not use updated callback field')
        expected_result = {'next_pc': pc, 'callback': callback, 'callback_context': context,
            'style': cpu.reg_read(UC_M68K_REG_D1) & 65535, 'read_count': len(samples)}
        if expected[0x001a] != ram[0x0016] or expected[0x0016] or expected[0x4ca2:0x4ca4] != b'\0\0':
            raise ValueError('Native frame latch/clear fields differ')
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        result = subprocess.run(arguments(address, style, current_samples), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr)))
        actual, parsed = out.read_bytes(), json.loads(result.stdout)
        if actual != expected or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Input prefix mismatch: ' + repr((len(rows), profile, address,
                style, current_samples, differences[:20], expected_result, parsed, events)))
        rows.append({'profile': profile, 'sequence': sequence, 'object_cpu_address': address,
            'initial_mode': ram[0x4cd4], 'incoming_style': style, 'samples': current_samples,
            'actual_reads': reads.copy(), 'actual_replay_events': events.copy(), 'result': parsed,
            'initial_callback': struct.unpack_from('>I', ram, address - RAM_BASE + 0x76)[0],
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected), parsed['style']

    for mode, callback, style, sample_profile in itertools.product((0, 1, 2, 255),
            (0, 1, 0xdeadbeef), (0, 0x0603, 0xff6b), range(6)):
        current_samples = ([255] * 5, [0] * 5, [0x55, 0xaa, 0x81, 0x12, 0x34],
            [0xf0, 0x0f, 0xff, 0xff, 0], [0x80, 0x7f, 0x7f, 0, 255],
            [3, 17, 29, 43, 61])[sample_profile]
        ram = fixture(mode, callback, replay=('event', 'noevent', 'terminal')[sample_profile % 3])
        compare(ram, 0x100f5c, style, current_samples, 'mode-style-edges-callback-replay')
    for address, mode in itertools.product((0x100000, 0x10ff82, 0x104c2c, 0x104c32,
                                           0x104c3e, 0x10ef90, 0x10fd40), (0, 1, 2)):
        ram = fixture(mode, 0xffffffff, address)
        ram[0xf006] = 15
        compare(ram, address, 0xabcd, [3, 17, 29, 43, 61], 'object-boundaries-updated-callback-context-alias')
    isolated = len(rows)
    for mode, replay in ((0, 'noevent'), (1, 'event'), (1, 'noevent'), (1, 'terminal'), (2, 'noevent')):
        address = 0x100f5c
        ram, style = fixture(mode, 0, address, replay), 0xff6b
        label, begin = 'carried-mode%d-%s' % (mode, replay), len(rows)
        for frame in range(40):
            current_samples = [(frame * 17 + 3) & 255, frame ^ 0x55, frame ^ 0xaa,
                               (frame * 29 + 11) & 255, (frame * 37 + 7) & 255]
            ram, style = compare(ram, address, style, current_samples, 'whole-ram-and-style-carry', label)
        sequences.append({'label': label, 'frames': len(rows) - begin, 'final_style': style,
                          'final_mode': ram[0x4cd4]})
    good = fixture(0)
    inp.write_bytes(good)
    wrong_resource = root / 'extracted/runtime/control_pause.ms5d'
    sentinel = b'previous-input-frame-output\0\xff'

    def reject(command, failure):
        out.write_bytes(sentinel)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Rejected input prefix changed output: ' + failure)
        negatives.append({'failure': failure, 'outputs_preserved': True,
                          'stderr': result.stderr.strip(), 'original_executed': False})

    reject(arguments(0x100f5c, 0x0603, [255] * 5, table_input=wrong_resource),
           'late-table-error-after-latch-clears-and-sampler')
    playback = fixture(1)
    inp.write_bytes(playback)
    reject(arguments(0x100f5c, 0x0603, [255] * 5, streams_input=wrong_resource),
           'late-stream-error-after-latch-clears-and-raw-sampler')
    inp.write_bytes(good)
    for invalid in ('0', '0x100001', '0x10ff84', '0x110000', '0xffffffff'):
        reject(arguments(invalid, 0x0603, [255] * 5), 'invalid-object-%s' % invalid)
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        reject(arguments(0x100f5c, 0x0603, [255] * 5), 'invalid-ram-size%d' % size)
    inp.write_bytes(good)
    for bad_style in ('-1', '65536'):
        reject(arguments(0x100f5c, bad_style, [255] * 5), 'invalid-style-%s' % bad_style)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        command = arguments(0x100f5c, 0x0603, [255] * 5)
        command[4] = str(alias)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 or inp.read_bytes() != good:
            raise ValueError('Input prefix output alias changed input')
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name,
                          'input_preserved': True, 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped ROM bytes changed')
    event_rows = sum(bool(row['actual_replay_events']) for row in rows)
    noevent_rows = sum(row['initial_mode'] == 1 and not row['actual_replay_events'] for row in rows)
    if not event_rows or not noevent_rows:
        raise ValueError('Exact replay D1 event/no-event coverage missing')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'stop_boundaries_cpu_address': [CONTROLLER, CALLBACK],
        'address_mapping': 'Fixed CPU addresses equal decrypted ROM offsets.',
        'native_resource_sha256': hashes, 'cases': len(rows), 'isolated_cases': isolated,
        'whole_65536_byte_ram_equal': True, 'boundary_callback_context_style_read_count_equal': True,
        'actual_mmio_read_order_asserted': True, 'no_callback_executed': True,
        'actual_full_d3_preservation_asserted': True,
        'actual_a6_object_and_a7_entry_stack_preservation_asserted': True,
        'frame_latch_clear_fields_asserted': True,
        'updated_callback_context_alias_order_asserted': True,
        'actual_replay_event_cases': event_rows, 'actual_replay_no_event_cases': noevent_rows,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'late_errors_and_aliases_preserve_outputs': True,
        'results': rows,
        'scope': 'Unmodifiedf12 latch/clear, native31d6 sampling, nativeb68 status update '
            'and callback pointer branch. Stop before f3c callback stack/context execution '
            'or f54 controller call. Exact D1 low word compared from native registers '
            'across hardware/forced-zero/replay event/no-event/terminal paths; D3 preserved. '
            'Object pointer/context aliases are read after allRAM updates. WholeRAM and '
            'style carried across40 frames per mode profile. Callback execution, controller '
            'execution, physical timing, natural call-site scheduling, other CPU registers '
            'and full boot excluded.'}, indent=2) + '\n')
    print('Input frame prefix original/C++ match:', len(rows), 'cases;', event_rows,
          'replay event cases;', noevent_rows, 'replay no-event cases;', len(negatives), 'preservation failures')


if __name__ == '__main__':
    main()
