"""Compare nativeb68 input-status table updates and31d6 integration."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

RAM_BASE, RETURN, UPDATE, SAMPLE = 0x100000, 0xff000, 0xb68, 0x31d6
PORT_ADDRESSES = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256 or program[0x180:0x182] != b'\0\0':
        raise ValueError('Unsupported ROM or playback selector')
    table = root / 'extracted/runtime/input_status.ms5d'
    streams = root / 'extracted/runtime/input_streams.ms5d'
    table_hash = checked_resource(table, program, 0xb58, 0xc58)
    streams_hash = checked_resource(streams, program, 0xf01fe, 0xf1a0e)
    wrong_resource = root / 'extracted/runtime/control_pause.ms5d'
    executable = root / 'build/update_input_status'
    if not executable.exists():
        raise ValueError('Build build/update_input_status first')
    folder = root / 'artifacts/input_status'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x340000, 0x380000):
        cpu.mem_map(address, 0x1000)
    reads, samples, writes = [], [], []
    rows, sampled_rows, sequences, negatives = [], [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address not in PORT_ADDRESSES:
            return
        ordinal = len(reads)
        if ordinal >= len(samples) or address != PORT_ADDRESSES[ordinal] or size != 1:
            raise ValueError('Native MMIO read ordering/width differs')
        cpu.mem_write(address, bytes((samples[ordinal],)))
        reads.append((address, samples[ordinal]))

    def write_hook(cpu, access, address, size, value, user):
        if address in PORT_ADDRESSES or address == 0x300001:
            writes.append((address, size, value))

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x300000, end=0x380000)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)

    def fixture(index):
        return bytearray(hashlib.shake_256(b'ms5-input-status-v1:' +
            index.to_bytes(4, 'big')).digest(65536))

    def call(entry):
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        cpu.emu_start(entry, RETURN, count=100000)
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
            raise ValueError('Native routine failed to return: ' + hex(entry))

    def original(ram, current_samples=None):
        cpu.mem_write(RAM_BASE, bytes(ram))
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(UC_M68K_REG_A5, 0x108000)
        cpu.reg_write(UC_M68K_REG_D0, 0xdeadbeef)
        reads.clear()
        writes.clear()
        samples[:] = [] if current_samples is None else current_samples[:5 if ram[0x4cd4] == 0 else 3]
        if current_samples is not None:
            call(SAMPLE)
        call(UPDATE)
        if writes or len(reads) != len(samples):
            raise ValueError('Native status updater wrote hardware or sampler read count differs')
        return bytes(cpu.mem_read(RAM_BASE, 65536))

    def compare(ram, profile, current_samples=None, sequence=None):
        expected = original(ram, current_samples)
        if expected[0x0012] != ram[0xfdaf] or expected[0xf006] != ram[0xf006] & 0xf0:
            raise ValueError('Native metadata/low pending-bit behavior differs')
        for bit in range(4):
            expected_slot = 1 if ram[0xf006] & (1 << bit) else ram[0xfdb6 + bit]
            if expected[0xfdb6 + bit] != expected_slot:
                raise ValueError('Native bclr-before-table slot update differs')
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        command = ([str(executable), str(inp), str(table), str(out)] if current_samples is None else
            [str(executable), '--sample', str(inp), str(streams), str(table), str(out)] +
            [str(value) for value in current_samples])
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((profile, len(rows), result.stderr)))
        expected_result = {'status': expected[0xf007]}
        if current_samples is not None:
            expected_result['read_count'] = len(samples)
        actual, parsed = out.read_bytes(), json.loads(result.stdout)
        if actual != expected or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Status mismatch: ' + repr((profile, differences[:20], expected_result, parsed)))
        row = {'profile': profile, 'sequence': sequence, 'metadata_fdaf': ram[0xfdaf],
            'pending': ram[0xf006], 'slots': list(ram[0xfdb6:0xfdba]),
            'status': expected[0xf007], 'read_count': len(samples), 'actual_reads': reads.copy(),
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest()}
        (rows if current_samples is None else sampled_rows).append(row)
        return bytearray(expected)

    for value in range(256):
        ram = fixture(value)
        ram[0xf006], ram[0xfdaf] = 0, value
        ram[0xfdb6:0xfdba] = bytes((value + slot * 73) & 255 for slot in range(4))
        compare(ram, 'all-slot-bytes-and-metadata')
    for pending in range(256):
        ram = fixture(256 + pending)
        ram[0xf006], ram[0xfdaf] = pending, pending ^ 0xa5
        ram[0xfdb6:0xfdba] = bytes((pending, pending ^ 255, (pending * 17) & 255, (pending * 29) & 255))
        compare(ram, 'all-pending-bytes-bit-clear-force-slots')
    for index in range(64):
        compare(fixture(512 + index), 'unrelated-random-state')
    isolated = len(rows)
    for mode, terminal in ((0, False), (1, False), (2, False), (1, True)):
        ram = fixture(1000 + mode + int(terminal) * 10)
        ram[0x4cd4] = mode
        struct.pack_into('>I', ram, 0x4cc4, 0xf07fe if terminal else 0xf01fe)
        struct.pack_into('>HH', ram, 0x4ccc, 0, 0x5ff if terminal else 0)
        ram[0x4cd0] = 255 if terminal else 0
        ram[0x4cc2:0x4cc4] = b'\0\0'
        ram[0xf006] = 255
        label, begin = 'carried-mode%d-terminal%d' % (mode, terminal), len(sampled_rows)
        for frame in range(40):
            current_samples = [(frame * 17 + 3) & 255, frame ^ 0x55, frame ^ 0xaa,
                               (frame * 29 + 11) & 255, (frame * 37 + 7) & 255]
            ram = compare(ram, 'sample-then-native-status-whole-output-carry', current_samples, label)
        if terminal and ram[0x4cd4] != 2:
            raise ValueError('Terminal native playback did not enter mode2')
        sequences.append({'label': label, 'frames': len(sampled_rows) - begin,
            'final_mode': ram[0x4cd4], 'full_ram_each_frame': True})

    good = fixture(2000)
    good[0x4cd4] = 0
    inp.write_bytes(good)
    sentinel = b'previous-input-status-output\0\xff'

    def reject(command, failure):
        out.write_bytes(sentinel)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Rejected status update changed output: ' + failure)
        negatives.append({'failure': failure, 'outputs_preserved': True,
                          'stderr': result.stderr.strip(), 'original_executed': False})

    reject([str(executable), str(inp), str(wrong_resource), str(out)], 'wrong-table-range')
    reject([str(executable), '--sample', str(inp), str(streams), str(wrong_resource), str(out)] +
           ['255', '1', '2', '3', '4'], 'late-wrong-table-after-sampling')
    playback = bytearray(good)
    playback[0x4cd4] = 1
    struct.pack_into('>I', playback, 0x4cc4, 0xf01fe)
    struct.pack_into('>HH', playback, 0x4ccc, 0, 0)
    playback[0x4cd0] = 0
    inp.write_bytes(playback)
    reject([str(executable), '--sample', str(inp), str(wrong_resource), str(table), str(out)] +
           ['255'] * 5, 'wrong-stream-range')
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        reject([str(executable), str(inp), str(table), str(out)], 'invalid-ram-size%d' % size)
    inp.write_bytes(good)
    malformed = folder / 'invalid-resource.bin'
    malformed.write_bytes(b'not-MS5D')
    reject([str(executable), str(inp), str(malformed), str(out)], 'invalid-table-header')
    reject([str(executable), '--sample', str(inp), str(streams), str(table), str(out)] +
           ['256', '0', '0', '0', '0'], 'invalid-port-byte')
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        result = subprocess.run([str(executable), str(inp), str(table), str(alias)],
                                capture_output=True, text=True)
        if result.returncode == 0 or inp.read_bytes() != good:
            raise ValueError('Status update output alias changed input')
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name,
                          'input_preserved': True, 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program bytes changed')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': UPDATE,
        'entry_rom_offset': UPDATE, 'integration_sampler_cpu_address': SAMPLE,
        'table_cpu_address_and_rom_offset': 0xb58, 'table_end_cpu_address': 0xc58,
        'address_mapping': 'Fixed CPU addresses equal decrypted ROM offsets.',
        'table_resource_sha256': table_hash, 'streams_resource_sha256': streams_hash,
        'table_includes_native_code_bytes_preserved_verbatim': True,
        'cases': len(rows), 'isolated_cases': isolated, 'sample_then_status_frames': len(sampled_rows),
        'whole_65536_byte_ram_equal': True, 'all256_slot_bytes_each_slot_checked': True,
        'all256_pending_bytes_and_metadata_values_checked': True,
        'native_bclr_slot_force_and_metadata_copy_asserted': True,
        'actual_sampler_mmio_order_and_read_count_equal': True, 'no_hardware_writes': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'failures_and_aliases_preserve_outputs': True,
        'results': rows, 'sample_results': sampled_rows,
        'scope': 'Unmodifiedb68 status update uses nativeb58..c58 byte window, including '
            'overlapping code bytes, without semantic filtering. Allslot bytes and byte '
            'index wrap, allpending bits including preserved high bits, metadata copy '
            'and forced slots compared in fullRAM. Actual31d6 thenb68 carried across '
            '40 frames per mode0/1/2 and terminal1-to2 transition; distinct second player '
            'MMIO samples used. CPU register outputs, physical port timing, natural '
            'caller scheduling and full boot excluded.'}, indent=2) + '\n')
    print('Input status original/C++ match:', len(rows), 'isolated cases;', len(sampled_rows),
          'whole-RAM sampled frames;', len(negatives), 'preservation failures')


if __name__ == '__main__':
    main()
