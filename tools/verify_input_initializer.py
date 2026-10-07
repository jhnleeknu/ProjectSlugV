"""Compare native3162 input initialization and carried31d6 sampling."""
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

RAM_BASE, RETURN, INITIALIZE, SAMPLE = 0x100000, 0xff000, 0x3162, 0x31d6
PORT_ADDRESSES = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256 or program[0x180:0x182] != b'\0\0':
        raise ValueError('Unsupported ROM or native playback selector')
    resource = root / 'extracted/runtime/input_streams.ms5d'
    resource_hash = checked_resource(resource, program, 0xf01fe, 0xf1a0e)
    unused_resource = root / 'extracted/runtime/control_pause.ms5d'
    unused_hash = checked_resource(unused_resource, program, 0x9068, 0x9086)
    executable, sampler = root / 'build/initialize_input', root / 'build/sample_input'
    if not executable.exists() or not sampler.exists():
        raise ValueError('Build initialize_input and sample_input first')
    folder = root / 'artifacts/input_initializer'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x340000, 0x380000):
        cpu.mem_map(address, 0x1000)
    reads, samples, hardware_writes = [], [], []
    rows, sample_rows, sequences, negatives = [], [], [], []

    def read_hook(cpu, access, address, size, value, user):
        if address not in PORT_ADDRESSES:
            return
        ordinal = len(reads)
        if ordinal >= len(samples) or address != PORT_ADDRESSES[ordinal] or size != 1:
            raise ValueError('Native MMIO read ordering/width changed')
        cpu.mem_write(address, bytes((samples[ordinal],)))
        reads.append((address, samples[ordinal]))

    def write_hook(cpu, access, address, size, value, user):
        if address in PORT_ADDRESSES or address == 0x300001:
            hardware_writes.append((address, size, value))

    cpu.hook_add(UC_HOOK_MEM_READ, read_hook, begin=0x300000, end=0x380000)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)

    def fixture(index):
        if index < 3:
            return bytearray(bytes((0, 255, 0xa5)[index: index + 1]) * 65536)
        return bytearray(hashlib.shake_256(b'ms5-input-initializer-v1:' +
            index.to_bytes(4, 'big')).digest(65536))

    def original(ram, selector=None, current_samples=None):
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, 0x1feffc),
                (UC_M68K_REG_D0, 0xa5a50000 | selector if selector is not None else 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        reads.clear()
        hardware_writes.clear()
        samples[:] = [] if current_samples is None else current_samples[:5 if ram[0x4cd4] == 0 else 3]
        cpu.emu_start(INITIALIZE if selector is not None else SAMPLE, RETURN, count=100000)
        if cpu.reg_read(UC_M68K_REG_PC) != RETURN or hardware_writes:
            raise ValueError('Original initialization/sampler failed return or wrote hardware')
        if selector is not None and reads:
            raise ValueError('Initializer read hardware ports')
        return bytes(cpu.mem_read(RAM_BASE, 65536))

    def compare(ram, selector, profile, input_resource=resource):
        expected = original(ram, selector)
        if expected[0x4ca8:0x4cb4] != bytes(12) or expected[0x4cb4] != ram[0x4cb4]:
            raise ValueError('Native clear span crossed into system held input')
        if selector >= 2 and expected[0x4cc2:0x4cd4] != ram[0x4cc2:0x4cd4]:
            raise ValueError('Native disabled replay did not preserve replay state')
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(input_resource), str(out), str(selector)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ initializer rejected: ' + repr((len(rows), selector, result.stderr)))
        actual = out.read_bytes()
        if actual != expected or json.loads(result.stdout) != {'mode': expected[0x4cd4]}:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if expected[at] != actual[at]]
            raise ValueError('Initializer mismatch: ' + repr((len(rows), selector, differences[:20], result.stdout)))
        rows.append({'profile': profile, 'selector_word': selector, 'mode': expected[0x4cd4],
            'resource': input_resource.name,
            'loaded_pointers': list(struct.unpack_from('>II', expected, 0x4cc4)),
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected)

    selectors = [0, 1, 2, 3, 0x7fff, 0x8000, 0xffff]
    selectors += list(struct.unpack('>96H', hashlib.shake_256(b'ms5-initializer-selectors-v1').digest(192)))
    for index, selector in enumerate(selectors):
        compare(fixture(index + 3), selector, 'word-boundaries-and-random-selectors')
    for selector in (0, 1, 2, 0xffff):
        for index in range(3):
            compare(fixture(index), selector, 'uniform-prior-memory')
    for selector in (2, 0x8000, 0xffff):
        compare(fixture(len(rows) + 3), selector, 'unused-valid-resource-without-tables', unused_resource)
    isolated = len(rows)
    for selector in (0, 1, 2):
        label, begin = 'initialized-selector-%d' % selector, len(sample_rows)
        ram = compare(fixture(200 + selector), selector, 'initialize-to-sampler-carry')
        for frame in range(40):
            current_samples = [(frame * 17 + 3) & 255, frame ^ 0x55,
                               frame ^ 0xaa, (frame * 29 + 11) & 255, (frame * 37 + 7) & 255]
            expected = original(ram, current_samples=current_samples)
            expected_reads = 5 if ram[0x4cd4] == 0 else 3
            if len(reads) != expected_reads:
                raise ValueError('Carried initialized sampler read count differs')
            inp.write_bytes(ram)
            out.unlink(missing_ok=True)
            result = subprocess.run([str(sampler), str(inp), str(resource), str(out)] +
                [str(value) for value in current_samples], capture_output=True, text=True)
            if result.returncode or out.read_bytes() != expected or json.loads(result.stdout) != {
                    'read_count': expected_reads}:
                raise ValueError('Initialized sampler wholeRAM mismatch: ' + repr((selector, frame, result.stderr)))
            sample_rows.append({'sequence': label, 'frame': frame, 'initial_mode': ram[0x4cd4],
                'actual_reads': reads.copy(), 'read_count': expected_reads,
                'input_sha256': hashlib.sha256(ram).hexdigest(),
                'ram_sha256': hashlib.sha256(expected).hexdigest()})
            ram = bytearray(expected)
        sequences.append({'label': label, 'frames': len(sample_rows) - begin,
            'final_mode': ram[0x4cd4], 'final_cursor': struct.unpack_from('>H', ram, 0x4cce)[0],
            'whole_ram_carried_each_frame': True})

    good = fixture(300)
    inp.write_bytes(good)
    sentinel = b'previous-initializer-output\0\xff'

    def reject(command, failure, details=None):
        out.write_bytes(sentinel)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 or out.read_bytes() != sentinel:
            raise ValueError('Initializer failure changed output: ' + failure)
        negatives.append({'failure': failure, 'details': details, 'outputs_preserved': True,
                          'stderr': result.stderr.strip(), 'original_executed': False})

    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        reject([str(executable), str(inp), str(resource), str(out), '0'], 'invalid-ram-size', size)
    inp.write_bytes(good)
    for selector in ('-1', '65536', '0x10000', '0xffffffff', 'bad'):
        reject([str(executable), str(inp), str(resource), str(out), selector], 'invalid-selector', selector)
    for selector in (0, 1):
        reject([str(executable), str(inp), str(unused_resource), str(out), str(selector)],
               'missing-native-pointer-tables', selector)
    malformed = folder / 'invalid-resource.bin'
    malformed.write_bytes(b'not-MS5D')
    reject([str(executable), str(inp), str(malformed), str(out), '2'], 'invalid-resource-header')
    reject([str(executable), str(inp), str(folder / 'missing.ms5d'), str(out), '0'], 'missing-resource-file')
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        result = subprocess.run([str(executable), str(inp), str(resource), str(alias), '0'],
                                capture_output=True, text=True)
        if result.returncode == 0 or inp.read_bytes() != good:
            raise ValueError('Initializer output alias changed RAM input')
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name,
                          'input_preserved': True, 'original_executed': False})
    packed_before = resource.read_bytes()
    result = subprocess.run([str(executable), str(inp), str(resource), str(resource), '0'],
                            capture_output=True, text=True)
    if result.returncode == 0 or resource.read_bytes() != packed_before:
        raise ValueError('Initializer output alias modified runtime resource')
    negatives.append({'failure': 'resource-output-alias', 'input_preserved': True, 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped program was modified')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': INITIALIZE,
        'entry_rom_offset': INITIALIZE, 'integration_sampler_cpu_address': SAMPLE,
        'address_mapping': 'Fixed CPU addresses equal decrypted ROM offsets.',
        'input_resource_sha256': resource_hash, 'unused_valid_resource_sha256': unused_hash,
        'native_rom180_selector_word': 0, 'initializer_cases': len(rows),
        'isolated_initializer_cases': isolated, 'sampler_integration_frames': len(sample_rows),
        'whole_65536_byte_ram_equal': True, 'clear_12_bytes_preserves_system_held_byte': True,
        'unsigned_selector_ge2_preserves_replay_state': True,
        'unused_resource_accepted_for_selector_ge2': True,
        'hardware_read_counts_and_order_asserted': True, 'no_hardware_writes': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'cli_failures_and_aliases_preserve_inputs_outputs': True,
        'results': rows, 'sampler_results': sample_rows,
        'scope': 'Unmodified3162 initializes12 game-state bytes and mode; unsigned selector '
            '0/1 loads both native pointer tables and resets playback words/byte, while '
            'selector>=2 preserves replay state. Random RAM and selectors, word boundaries, '
            'uniform prior states and unused resources compared. Whole initializer output '
            'carried into40 actual31d6 frames for selectors0/1/2 with distinct MMIO samples. '
            'ROM180=0 excludes recording-buffer writes. CPU register outputs, physical '
            'port timing, natural initializer call-site reachability and full boot excluded.'}, indent=2) + '\n')
    print('Input initializer original/C++ match:', len(rows), 'initializers;', len(sample_rows),
          'whole-RAM integration frames;', len(negatives), 'preservation failures')


if __name__ == '__main__':
    main()
