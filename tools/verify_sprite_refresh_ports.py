"""Compare native16cfa RAM, full D0 and interleaved video/PVC writes."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK = 0x100000, 0xff000, 0x1feffc


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/refresh_sprite_queue'
    resources = [root / 'extracted/runtime' / ('composition_%06x.ms5c' % identifier) for identifier in (0x2152, 0x2952)]
    folder = root / 'artifacts/sprite_refresh_ports'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, trace, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.writes.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x400000:0x500000])
    writes, cleanup, pvc, hardware, rows, negatives = [], [], [], [], [], []

    def video_hook(cpu, access, address, size, value, user):
        assert address == 0x3c0000 and size == 4
        writes.append(value & 0xffffffff)
        hardware.append((size, address, value & 0xffffffff))

    def pvc_hook(cpu, access, address, size, value, user):
        assert address in (0x2ffff0, 0x2ffff2) and size == 2
        pvc.append((size, address, value & 65535))
        hardware.append((size, address, value & 65535))

    def cleanup_hook(cpu, address, size, user):
        cleanup.append(address)

    cpu.hook_add(UC_HOOK_MEM_WRITE, video_hook, begin=0x3c0000, end=0x3c000f)
    cpu.hook_add(UC_HOOK_MEM_WRITE, pvc_hook, begin=0x2ffff0, end=0x2ffff3)
    for address in (0x16092, 0x166a0):
        cpu.hook_add(UC_HOOK_CODE, cleanup_hook, begin=address, end=address)

    def put(ram, offset, value):
        struct.pack_into('>H', ram, offset, value)

    def fixture(forward, ready, count, start, cache, disabled, flip=0):
        ram = bytearray(65536)
        ram[0x8d3c] = 0x21 | (128 if forward else 0)
        ram[0x8d3d] = 0x35 | (128 if ready else 0)
        put(ram, 0x10, 0xbeef)
        put(ram, 0x8d34, start)
        put(ram, 0x8d36, (start + 2 * count) & 0x1fe)
        for pool, lower, upper in ((0x8d3e, 0, 190), (0x8d46, 190, 380)):
            ram[pool:pool + 8] = struct.pack('>4H', lower, upper, lower + cache, lower + cache)
        if disabled & 1:
            ram[0x8d3e:0x8d46] = bytes([255]) * 8
        if disabled & 2:
            ram[0x8d46:0x8d4e] = bytes([255]) * 8
        for index in range(count):
            offset = 12 * (index + 1)
            put(ram, 0x8b34 + ((start + index * 2) & 0x1fe), offset)
            identifier = 0x2152 if index % 2 == 0 else 0x2952
            style = 0xffff1500 | (4 if index % 2 else 0) | flip
            packed = (384 << 23) | identifier
            record = 0x7f34 + offset
            ram[record:record + 12] = struct.pack('>III', 160 << 6, style, packed)
        return ram

    def compare(ram, d0, profile, fields):
        cpu.mem_write(BASE, bytes(ram))
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(UC_M68K_REG_D0, d0)
        cpu.reg_write(UC_M68K_REG_A7, STACK)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        cleanup.clear()
        pvc.clear()
        hardware.clear()
        cpu.emu_start(0x16cfa, RETURN, count=1000000)
        assert cpu.reg_read(UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_d0 = cpu.reg_read(UC_M68K_REG_D0) & 0xffffffff
        processed = bool(ram[0x8d3d] & 128)
        expected_trace = b''.join(struct.pack('>BII', *event) for event in hardware)
        if processed:
            assert cleanup == [0x16092 if ram[0x8d3c] & 128 else 0x166a0] * 2
        else:
            assert not cleanup and expected_d0 == d0
        inp.write_bytes(ram)
        for path in (out, trace):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), '--ports', hex(d0), str(inp), str(out), str(trace)] + [str(path) for path in resources], capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or not trace.exists() or trace.read_bytes() != expected_trace or json.loads(actual.stdout) != {'d0': expected_d0, 'processed': processed, 'writes': len(hardware)}:
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, fields, hex(d0), hex(expected_d0), cleanup, actual.stdout, actual.stderr, diff[:20])))
        rows.append({'profile': profile, 'fixture': fields, 'input_d0': d0, 'result_d0': expected_d0,
            'processed': processed, 'pvc_writes': len(pvc), 'port_writes': len(hardware), 'pvc_examples': pvc[:8],
            'pvc_sha256': hashlib.sha256(b''.join(struct.pack('>BII', *event) for event in pvc)).hexdigest(), 'video_writes': len(writes), 'cleanup_calls': list(cleanup),
            'input_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'hardware_trace_sha256': hashlib.sha256(expected_trace).hexdigest()})
        return expected, expected_d0

    for forward, ready, count, start, cache, disabled, d0 in itertools.product((False, True),
            (False, True), (0, 1, 4, 20), (0, 0x1fc), (0, 95, 190), (0, 2, 3), (0xabcdabff, 0xffffffff)):
        fields = {'forward': forward, 'ready': ready, 'count': count, 'start': start, 'cache': cache, 'disabled': disabled}
        compare(fixture(forward, ready, count, start, cache, disabled), d0, 'queue-direction-gates-ring-cache-disabled-pools', fields)
    for forward, flip, disabled in itertools.product((False, True), range(4), (0, 2, 3)):
        ram = fixture(forward, True, 4, 0x1fc, 95, disabled, flip)
        compare(ram, 0x12345678, 'all-flip-styles-with-disabled-pools',
            {'forward': forward, 'flip': flip, 'disabled': disabled})
    isolated = len(rows)
    for forward in (False, True):
        ram = fixture(forward, True, 4, 0x1fc, 95, 0)
        d0 = 0x12345678
        for frame in range(4):
            changed = bytearray(ram)
            changed[0x8d3d] |= 128
            ram, d0 = compare(changed, d0, 'four-carried-refresh-calls', {'frame': frame, 'initial_forward': forward})

    sentinel = b'previous-sprite-refresh-output\0\xff'
    def reject(ram, selected_resources, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        trace.write_bytes(sentinel)
        actual = subprocess.run([str(executable), '--ports', '0xabcdabff', str(inp), str(out), str(trace)] + [str(path) for path in selected_resources], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and trace.read_bytes() == sentinel
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    ram = fixture(True, True, 4, 0, 95, 0)
    reject(ram, resources[:1], 'missing-second-resource-after-first-record')
    bad = bytearray(ram)
    put(bad, 0x7f34 + 24 + 6, 0x150c)
    reject(bad, resources, 'unsupported-second-record-style-after-first-record')
    for size in (0, 65535, 65537):
        reject(bytes(size), resources, 'invalid-ram-size')
    inp.write_bytes(ram)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), '--ports', '0', str(inp), str(alias), str(trace)] + [str(path) for path in resources], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert bytes(cpu.mem_read(0x200000, 0xffff0)) == program[0x400000:0x4ffff0]
    assert any(row['processed'] and row['video_writes'] == 0 and len(row['cleanup_calls']) == 2 for row in rows)
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': 0x16cfa,
        'entry_rom_offset': 0x16cfa, 'cases': len(rows), 'isolated_cases': isolated,
        'negative_cases': len(negatives), 'whole_65536_byte_ram_equal': True,
        'full_uint32_d0_equal': True, 'ordered_video_and_pvc_writes_equal': True,
        'all_flip_styles_and_disabled_pools_checked': True,
        'cleanup_calls_even_zero_emit_asserted': True,
        'resource_hashes': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in resources},
        'negative_results': negatives, 'results': rows,
        'scope': 'Original16cfa normal rectangular sprite dispatcher through both cleanup '
            'calls, with native fullD0 and interleaved hardware writes as oracle. WholeRAM '
            'and all video/PVC port records compared using real002152/002952 MS5C resources, '
            'including disabled pools, zero rendering and all four flip styles. FixedROM '
            'unchanged; mapped source bank CPU200000..2fffef unchanged (PVC register tail '
            'excluded). Other styles, CPU flags/registers, graphics device rendering, natural '
            'scheduling and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
