"""Exhaustively compare ef2 gate and continuous ready/wait input-control paths."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A1, UC_M68K_REG_A5, UC_M68K_REG_A6,
    UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources

RAM_BASE, ENTRY, PREFIX, CALLBACK, CONTROL, RETURN, LOOP, TRAP, BIOS = (
    0x100000, 0xef2, 0xf12, 0xf3c, 0xf54, 0xff000, 0xec4, 0xfee, 0xc00444)
INPUT_PORTS = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    executable = root / 'build/poll_frame_gate'
    chain = root / 'build/step_input_control'
    if not executable.exists() or not chain.exists():
        raise ValueError('Build poll_frame_gate and step_input_control first')
    streams, status, menu, pause, palettes, font, stages = [root / 'extracted/runtime' / name for name in
        ('input_streams.ms5d', 'input_status.ms5d', 'control_menu_tree.ms5d', 'control_pause.ms5d',
         'palettes.ms5p', 'menu_fonts.ms5d', 'stages')]
    hashes = {'streams': checked_resource(streams, program, 0xf01fe, 0xf1a0e),
        'status': checked_resource(status, program, 0xb58, 0xc58),
        'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
        'pause': checked_resource(pause, program, 0x9068, 0x9086),
        'font': checked_resource(font, program, 0xe80c8, 0xe84c8),
        'null_name': checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)}
    groups = verify_resources(stages, program, source)
    records, _ = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] + records[identifier][1]
                       for identifier in sorted(records))
    packed = palettes.read_bytes()
    if packed != struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload), zlib_crc(payload), 0, 0) + payload:
        raise ValueError('Palette resource differs from native source')
    hashes['palettes'] = hashlib.sha256(packed).hexdigest()
    folder = root / 'artifacts/frame_gate'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, port_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 0x1000)
    state = {'integrated': False, 'video': 0, 'gate_visits': 0, 'video_reads': 0}
    samples, reads, writes, trace = [], [], [], []
    cli_rows, integrated_rows, sequences, negatives = [], [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address == 0x3c0006:
            if size != 2:
                raise ValueError('Native gate video read width differs')
            state['video_reads'] += 1
            cpu.mem_write(address, state['video'].to_bytes(2, 'big'))
        elif address in INPUT_PORTS:
            ordinal = len(reads)
            if ordinal >= len(samples) or address != INPUT_PORTS[ordinal] or size != 1:
                raise ValueError('Native input MMIO read order/width differs')
            cpu.mem_write(address, bytes((samples[ordinal],)))
            reads.append((address, samples[ordinal]))

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010 or address in (0x2ffff0, 0x2ffff2):
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        if address == ENTRY:
            state['gate_visits'] += 1
            if state['gate_visits'] == 2:
                cpu.emu_stop()
        else:
            trace.append({'address': address, 'a1': cpu.reg_read(UC_M68K_REG_A1),
                'a6': cpu.reg_read(UC_M68K_REG_A6), 'a7': cpu.reg_read(UC_M68K_REG_A7),
                'd1_word': cpu.reg_read(UC_M68K_REG_D1) & 65535})
            if address in (CALLBACK, LOOP, TRAP, BIOS) or (address == PREFIX and not state['integrated']):
                cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x300000, end=0x3c0006)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in (ENTRY, PREFIX, CALLBACK, CONTROL, 0xf5a, LOOP, TRAP, BIOS):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def run(ram, video, integrated=False, current_samples=None, style=0xff6b):
        state.update(integrated=integrated, video=video, gate_visits=0, video_reads=0)
        samples[:] = [] if current_samples is None else current_samples[:5 if ram[0x4cd4] == 0 else 3]
        reads.clear()
        writes.clear()
        trace.clear()
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, 0x100f5c), (UC_M68K_REG_A7, 0x1feffc),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, 0xbeef0000 | style),
                (UC_M68K_REG_D3, 0xcafe7000), (UC_M68K_REG_A1, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        cpu.emu_start(ENTRY, RETURN, count=12000000 if integrated else 100)
        ready = ram[0x16] >= ram[0x17]
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if state['gate_visits'] != (1 if ready else 2) or state['video_reads'] != int(ready):
            raise ValueError('Native gate wait/read-count differs')
        if not ready and (pc != ENTRY or trace or reads or writes):
            raise ValueError('Waiting gate executed input prefix or hardware access')
        if not integrated and ready and pc != PREFIX:
            raise ValueError('Ready gate did not reach f12')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        if not integrated:
            if writes or reads:
                raise ValueError('Isolated gate wrote hardware or read inputs')
            model = bytearray(ram)
            if ready:
                model[0x18] = max((video >> 7) - 0x100, 0)
            if expected != model:
                raise ValueError('Native gate wholeRAM/arithmetic model differs')
        return expected, ready, pc

    baseline = hashlib.shake_256(b'ms5-frame-gate-v1').digest(65536)
    # Single C++ batch covers every unsigned signal/threshold pair and then
    # every video word while ready. Original wholeRAM checked per record.
    cases = [(value >> 8, value & 255, (value * 73) & 255, (value * 40503 + 17) & 65535)
             for value in range(65536)]
    cases += [(0, 0, (video * 17) & 255, video) for video in range(65536)]
    batch_input, expected_batch = bytearray(), bytearray()
    ready_count = 0
    for signal, threshold, old_byte, video in cases:
        ram = bytearray(baseline)
        ram[0x16:0x19] = bytes((signal, threshold, old_byte))
        expected, ready, _ = run(ram, video)
        ready_count += ready
        batch_input.extend(struct.pack('>BBBH', signal, threshold, old_byte, video))
        expected_batch.extend(bytes((int(ready), expected[0x18])))
    result = subprocess.run([str(executable), '--batch'], input=bytes(batch_input), capture_output=True)
    if result.returncode or result.stdout != expected_batch:
        first = next((at for at in range(min(len(result.stdout), len(expected_batch)))
                      if result.stdout[at] != expected_batch[at]), None)
        raise ValueError('Gate batch mismatch: ' + repr((first, result.returncode, result.stderr[:200])))
    print('Gate exhaustive matrix matched:', len(cases), 'records', flush=True)
    for signal, threshold in ((0, 0), (0, 1), (1, 0), (255, 255), (128, 129), (255, 0)):
        for video in (0, 0x7f, 0x80, 0x7fff, 0x8000, 0x807f, 0x8080, 0xffff):
            ram = bytearray(hashlib.shake_256(b'ms5-gate-cli-v1:' + len(cli_rows).to_bytes(4, 'big')).digest(65536))
            ram[0x16], ram[0x17] = signal, threshold
            expected, ready, _ = run(ram, video)
            inp.write_bytes(ram)
            out.unlink(missing_ok=True)
            result = subprocess.run([str(executable), str(inp), str(out), str(video)], capture_output=True, text=True)
            if result.returncode or out.read_bytes() != expected or json.loads(result.stdout) != {'ready': ready}:
                raise ValueError('Gate wholeRAM CLI mismatch: ' + repr((signal, threshold, video, result.stderr)))
            cli_rows.append({'signal': signal, 'threshold': threshold, 'video': video, 'ready': ready,
                'video_reads': state['video_reads'], 'ram_sha256': hashlib.sha256(expected).hexdigest()})

    cpu.mem_write(RAM_BASE, bytes(65536))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
        raise ValueError('Native allocator fixture initialization failed')
    initial = bytes(cpu.mem_read(RAM_BASE, 65536))

    def fixture(active=0, callback=0):
        ram = bytearray(initial)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14], ram[node + 15] = slot & 31, 0x80 | (slot & 3)
        ram[0x7df0], ram[0xfdaf], ram[0xf000], ram[0xf002] = active, 2, 2, 1
        ram[0xfdb6:0xfdba] = b'\1\1\1\1'
        ram[0x4cd2], ram[0x4cd3] = 15, 4
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        struct.pack_into('>H', ram, 0x000e, 0xffff)
        struct.pack_into('>H', ram, 0x0f5c + 0x7e, 0xffff)
        ram[0x0f5c + 0x84] = 1
        struct.pack_into('>II', ram, 0x0f5c + 0x76, callback, 0xdeadbeef)
        return ram

    def chain_arguments(video, current_samples):
        return [str(chain), '--poll', str(video), str(inp), str(streams), str(status), str(menu), str(pause),
            str(palettes), str(out), str(port_out), str(0x100f5c), str(0xff6b), str(0x7000), str(0x1feffc)] + [
            str(value) for value in current_samples] + [str(font), str(stages)]

    def integrated_compare(ram, video, current_samples, profile):
        expected, ready, pc = run(ram, video, True, current_samples)
        prefix = [item for item in trace if item['address'] in (CONTROL, CALLBACK)]
        if ready and len(prefix) != 1:
            raise ValueError('Ready gate failed continuous prefix boundary')
        if ready and (prefix[0]['a1'] != 0xb58 or prefix[0]['a6'] != 0x100f5c or prefix[0]['a7'] != 0x1feffc):
            raise ValueError('Ready prefix failed A1/caller context preservation')
        callback = struct.unpack_from('>I', expected, 0x0f5c + 0x76)[0] if pc == CALLBACK else 0
        context = struct.unpack_from('>I', expected, 0x0f5c + 0x7a)[0] if callback else 0
        expected_result = {'next_pc': 0 if pc == RETURN else pc, 'callback': callback,
            'callback_context': context, 'style': prefix[0]['d1_word'] if ready else 0xff6b,
            'read_count': len(reads)}
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(ram)
        for path in (out, port_out):
            path.unlink(missing_ok=True)
        result = subprocess.run(chain_arguments(video, current_samples), capture_output=True, text=True)
        if result.returncode or out.read_bytes() != expected or port_out.read_bytes() != expected_ports or json.loads(result.stdout) != expected_result:
            raise ValueError('Poll/input/control mismatch: ' + repr((profile, ready, expected_result, result.stdout, result.stderr, trace)))
        integrated_rows.append({'profile': profile, 'signal': ram[0x16], 'threshold': ram[0x17],
            'video': video, 'ready': ready, 'video_reads': state['video_reads'], 'actual_reads': reads.copy(),
            'actual_trace': trace.copy(), 'result': expected_result, 'port_events': len(writes),
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected)

    for active, signal, threshold, callback in ((0, 0, 1, 0), (0, 1, 1, 0), (1, 1, 1, 0),
            (0, 1, 1, 0xdeadbeef), (1, 0, 255, 0xdeadbeef)):
        ram = fixture(active, callback)
        ram[0x16], ram[0x17], ram[0x18] = signal, threshold, 0xa5
        integrated_compare(ram, 0xffff, [253, 255, 255, 255, 255], 'poll-ready-wait-callback-activation')
    ram = fixture(active=1)
    ram[0x16], ram[0x17] = 1, 1
    ram[0x000f] ^= 1
    integrated_compare(ram, 0x8080, [254, 255, 255, 255, 255], 'ready-step-counter-trap')
    # Only the host signal changes between polls; waiting preserves all RAM and
    # never runs f12. Ready calls carry complete native/C++ outputs onward.
    ram = fixture()
    ram[0x17] = 1
    begin = len(integrated_rows)
    for signal, system in ((0, 253), (0, 253), (1, 253), (0, 255), (1, 254),
                           (0, 255), (1, 255), (0, 255)):
        ram[0x16] = signal
        ram = integrated_compare(ram, 0xffff, [system, 255, 255, 255, 255], 'host-signal-whole-output-carry')
    sequences.append({'frames': len(integrated_rows) - begin, 'host_changes_only_signal_between_polls': True})
    ram = fixture()
    ram[0x16], ram[0x17], ram[0x18] = 1, 1, 0xa5
    struct.pack_into('>HH', ram, 0x4d92 + 10, 0xfffe, 0xfffe)
    inp.write_bytes(ram)
    for existing in (False, True):
        sentinels = (b'prior-poll-ram', b'prior-poll-ports')
        for path, sentinel in zip((out, port_out), sentinels):
            if existing:
                path.write_bytes(sentinel)
            else:
                path.unlink(missing_ok=True)
        result = subprocess.run(chain_arguments(0xffff, [253, 255, 255, 255, 255]), capture_output=True, text=True)
        if result.returncode == 0:
            raise ValueError('Late palette failure accepted after gate write18')
        for path, sentinel in zip((out, port_out), sentinels):
            if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (not existing and path.exists()):
                raise ValueError('Late gate/input failure changed outputs')
        negatives.append({'failure': 'palette-lookup-after-gate18-input-activation', 'existing_outputs': existing,
                          'outputs_preserved': True, 'stderr': result.stderr.strip(), 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000] or bytes(cpu.mem_read(0x200000, 0xffff0)) != program[0x200000:0x2ffff0]:
        raise ValueError('Original ROM or palette bank changed outside PVC tail')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'native_resource_sha256': hashes,
        'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'address_mapping': 'Fixed CPU addresses equal decrypted offsets; observed palette bank maps same offsets.',
        'all65536_signal_threshold_pairs': True, 'all65536_video_words': True,
        'batch_cases': len(cases), 'ready_cases': ready_count, 'waiting_cases': len(cases) - ready_count,
        'batch_input_sha256': hashlib.sha256(batch_input).hexdigest(),
        'batch_output_sha256': hashlib.sha256(expected_batch).hexdigest(),
        'native_whole_65536_byte_ram_equal': True, 'cli_whole_ram_cases': len(cli_rows), 'cli_results': cli_rows,
        'video_word_reads_exactly0_wait1_ready_asserted': True,
        'integrated_cases': len(integrated_rows), 'integrated_results': integrated_rows,
        'integrated_ram_ordered_ports_and_result_equal': True,
        'waiting_never_executes_f12_or_reads_input_ports': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives), 'negative_results': negatives,
        'late_failure_preserves_outputs_including_gate_write18': True,
        'scope': 'Nativeef2 gate: unsigned signal>=threshold, conditional video word read, '
            'word shift/subtract with underflow-to-zero, byte18 store. Allbyte pairs and '
            'allvideo words compared; isolated native entireRAM checked and C++ batch '
            'ready/new18 compared, representative C++ wholeRAM CLI cases checked. Continuous '
            'ready gate throughf12/input/controller/caller and waiting second-entry boundary '
            'compared. Host signal transitions explicit; no interrupt/device timing, wait '
            'duration, external callback, trap handler or full boot fidelity claim.'}, indent=2) + '\n')
    print('Frame gate original/C++ match:', len(cases), 'batch records;', len(cli_rows),
          'wholeRAM CLI cases;', len(integrated_rows), 'continuous chain cases;', len(negatives), 'late failures')


def zlib_crc(data):
    import zlib
    return zlib.crc32(data)


if __name__ == '__main__':
    main()
