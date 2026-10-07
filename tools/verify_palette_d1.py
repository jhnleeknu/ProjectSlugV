"""Compare original5728 fullRAM, finalD1 and MMIO with real palette resources."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK = 0x100000, 0xff000, 0x1feffc
PATHS = (0x4718, 0x479e, 0x4c40, 0x504c)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable, resource = root / 'build/step_palette_frame', root / 'extracted/runtime/palettes.ms5p'
    records, ignored = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] + records[identifier][1] for identifier in sorted(records))
    packed = resource.read_bytes()
    assert packed == struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload), zlib.crc32(payload) & 0xffffffff, 0, 0) + payload
    folder = root / 'artifacts/palette_d1'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    hardware, paths, rows, negatives = [], [], [], []

    def write(cpu, access, address, size, value, user):
        if address in (0x300001, 0x2ffff0, 0x2ffff2):
            hardware.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((hex(address), size, value)))

    def code(cpu, address, size, user):
        if address == RETURN:
            cpu.emu_stop()
        elif address in PATHS:
            paths.append(address)

    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.mem_write(BASE, bytes(65536))
    cpu.reg_write(m68k_const.UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(m68k_const.UC_M68K_REG_A7, STACK)
    cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN
    initial = bytes(cpu.mem_read(BASE, 65536))

    def fixture(timer=0, pending=0, current=0, step=0, target=0):
        ram = bytearray(initial)
        ram[0x7dd4], ram[0x7ded] = timer, pending
        for channel in range(3):
            for at, value in ((0x7dc2, current), (0x7dc8, target)):
                struct.pack_into('>H', ram, at + 2 * channel, (value + channel * 0x101) & 65535)
            struct.pack_into('>H', ram, 0x7dce + 2 * channel, step)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x203)
            ram[node + 14], ram[node + 15] = 0, 2  # No implicit timer dirtiness.
        return ram

    def node(ram, slot, first, second, weight, exempt=False):
        at = 0x4d92 + slot * 16
        struct.pack_into('>HH', ram, at + 10, first, second)
        ram[at + 14], ram[at + 15] = weight, 128 | (2 if exempt else 0)

    def compare(ram, d1, profile):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((m68k_const.UC_M68K_REG_SR, 0x2000), (m68k_const.UC_M68K_REG_A5, 0x108000),
                (m68k_const.UC_M68K_REG_A7, STACK), (m68k_const.UC_M68K_REG_D1, d1)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        hardware.clear()
        paths.clear()
        cpu.emu_start(0x5728, RETURN, count=500000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_d1 = cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 0xffffffff
        expected_ports = b''.join(struct.pack('>BII', *event) for event in hardware)
        inp.write_bytes(ram)
        for path in (out, ports_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), '--d1', hex(d1), str(inp), str(resource), str(out), str(ports_out)], capture_output=True, text=True)
        if actual.returncode or not out.exists() or out.read_bytes() != expected or not ports_out.exists() or ports_out.read_bytes() != expected_ports or json.loads(actual.stdout) != {'d1': expected_d1}:
            actual_ram = out.read_bytes() if out.exists() else b''
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, hex(d1), hex(expected_d1), paths[-5:], actual.stdout, actual.stderr, diff[:20])))
        rows.append({'profile': profile, 'timer': ram[0x7dd4], 'pending': ram[0x7ded],
            'input_d1': d1, 'result_d1': expected_d1, 'native_paths': sorted(set(paths)),
            'last_native_path': paths[-1] if paths else None, 'ports': len(hardware),
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), expected_d1

    incoming = (0, 0xabcdabff, 0xffffffff, 0x12348000)
    effects = ((0, 0, 0), (0x00ff, 1, 0x1000), (0x7fff, 1, 0x8000), (0xffff, 1, 0),
        (0x8000, 0xffff, 0x7fff), (0x1000, 0x80, 0xf000), (0x1234, 0, 0x12ff))
    for timer, effect, pending, d1 in itertools.product((0, 1, 2, 255), effects, (0, 128), incoming):
        ram = fixture(timer, pending, *effect)
        compare(ram, d1, 'timer-byte-difference-no-dirty-pending-gates')
    for weight, exempt, effect, pair, d1 in itertools.product((0, 1, 15, 30, 31, 255), (False, True),
            (False, True), ((0x203, 0x203), (0x203, 0x87a), (0x87a, 0x203)), incoming):
        ram = fixture()
        if effect:
            struct.pack_into('>3H', ram, 0x7dc2, 0xff00, 0x0700, 0x1f00)
        else:
            struct.pack_into('>3H', ram, 0x7dc2, 0x007f, 0x007f, 0x007f)
        node(ram, 253, pair[0], pair[1], weight, exempt)
        compare(ram, d1, 'last-color-direct-effect-blend-effect-exempt-weight-boundaries')
    for weight, pending, d1 in itertools.product((0, 1, 15, 30, 31, 255), (0, 128), incoming):
        ram = fixture(2, pending, 0x1000, 0xff00, 0x7fff)
        for slot, first, second, selected_weight, exempt in ((0, 0x203, 0x203, 0, False),
                (7, 0x203, 0x87a, 15, True), (127, 0x87a, 0x203, 31, False),
                (255, 0x203, 0x87a, weight, bool(weight & 1))):
            node(ram, slot, first, second, selected_weight, exempt)
        compare(ram, d1, 'multiple-dirty-final-transform-after-timer-update')
    isolated = len(rows)
    ram = fixture(4, 0, 0x1000, 0xff00, 0xff00)
    node(ram, 255, 0x203, 0x87a, 15)
    d1 = 0xabcddcba
    for frame in range(6):
        ram, d1 = compare(ram, d1, 'six-carried-effect-frames-d1-high-bits-and-pending')

    sentinel = b'previous-palette-d1-output\0\xff'
    def reject(ram, selected_resource, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports_out.write_bytes(sentinel)
        actual = subprocess.run([str(executable), '--d1', '0xabcdabff', str(inp), str(selected_resource), str(out), str(ports_out)], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports_out.read_bytes() == sentinel
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    ram = fixture(2, 0, 0x1000, 0x100, 0)
    node(ram, 0, 0x203, 0x87a, 15)
    node(ram, 255, 0xfffe, 0xfffe, 0)
    reject(ram, resource, 'late-palette-id-after-timer-and-first-transform')
    bad_resource = folder / 'bad.ms5p'
    bad_resource.write_bytes(b'bad-palette-resource')
    reject(fixture(), bad_resource, 'invalid-resource')
    for size in (0, 65535, 65537):
        reject(bytes(size), resource, 'invalid-ram-size')
    ram = fixture()
    inp.write_bytes(ram)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), '--d1', '0', str(inp), str(resource), str(alias), str(ports_out)], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    inp.write_bytes(fixture())
    for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
        out.write_bytes(sentinel)
        ports_out.write_bytes(sentinel)
        actual = subprocess.run([str(executable), '--d1', invalid, str(inp), str(resource), str(out), str(ports_out)], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports_out.read_bytes() == sentinel
        negatives.append({'failure': 'invalid-d1-parser-value', 'value': invalid,
            'outputs_preserved': True, 'original_executed': False})
    seen_paths = {path for row in rows for path in row['native_paths']}
    assert seen_paths == set(PATHS)
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert bytes(cpu.mem_read(0x200000, 0xffff0)) == program[0x200000:0x2ffff0]
    # Actual source pairs used in both directions contain decreasing channels.
    first = struct.unpack('>16H', records[0x203][1])
    second = struct.unpack('>16H', records[0x87a][1])
    assert any(((second[color] >> shift) & 31) < ((first[color] >> shift) & 31) for color in range(1, 16) for shift in (0, 5, 10))
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': 0x5728,
        'entry_rom_offset': 0x5728, 'cases': len(rows), 'isolated_cases': isolated, 'negative_cases': len(negatives),
        'whole_ram_final_uint32_d1_and_ordered_mmio_equal': True, 'all_native_transform_paths_reached': sorted(seen_paths),
        'real_source_pairs_include_negative_channel_interpolation': True,
        'resource_sha256': hashlib.sha256(packed).hexdigest(), 'negative_results': negatives, 'results': rows,
        'scope': 'Original5728 effect tick and conditional7196 palette preparation. NativeD1 '
            'is the oracle for timer-byte and last-color transform effects; noPython D1 formula. '
            'Direct/effect-only/blend/effect-blend, exempt flags, all weight boundaries, dirty '
            'ordering and pending gates compared using verifiedMS5P source. Six complete outputs '
            'carried includingD1. FullRAM/fullD1/ordered watchdog/PVC writes verified; fixedROM '
            'and mapped source bank through2fffef unchanged. Physical palette devices, other '
            'registers/flags, natural frame scheduling and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
