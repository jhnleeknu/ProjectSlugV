"""Compare native187d8 long column writes and continuous1adf8 scene wrapper."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK = 0x100000, 0xff000, 0x1feffc
OBJECTS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/refresh_column_controls'
    folder = root / 'artifacts/column_control'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x2f0000, 0x10000)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows, negatives = [], [], []

    def hook(cpu, access, address, size, value, user):
        if address == 0x3c0000:
            assert size == 4
        else:
            assert address in (0x2ffff0, 0x2ffff2) and size == 2
        writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    cpu.hook_add(UC_HOOK_MEM_WRITE, hook, begin=0x2ffff0, end=0x2ffff3)
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook, begin=0x3c0000, end=0x3c0003)

    def fixture():
        return bytearray(hashlib.shake_256(b'ms5-column-control-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))

    def object_state(ram, address, flags=0x81, slot=0, x=0, y=0):
        at = address - BASE
        ram[at + 0x7a] = flags
        for offset, value in ((0x26, slot), (0x7c, x), (0x7e, y)):
            struct.pack_into('>H', ram, at + offset, value)

    def compare(ram, address=0x100100, d0=0xabcd1234, scene=False, profile='matrix'):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, STACK), (UC_M68K_REG_A0, address), (UC_M68K_REG_D0, d0)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(0x1adf8 if scene else 0x187d8, RETURN, count=10000)
        assert cpu.reg_read(UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_d0 = cpu.reg_read(UC_M68K_REG_D0) & 0xffffffff
        expected_ports = b''.join(struct.pack('>BII', *event) for event in writes)
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        args = [str(executable)] + (['--scene'] if scene else []) + [str(inp), str(out), str(ports)]
        args += [hex(d0)] if scene else [hex(address), hex(d0)]
        actual = subprocess.run(args, capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or not ports.exists() or ports.read_bytes() != expected_ports or json.loads(actual.stdout) != {'d0': expected_d0, 'writes': len(writes)}:
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, scene, hex(address), hex(d0), hex(expected_d0), len(writes), actual.stdout, actual.stderr, diff[:20])))
        if not scene:
            at = address - BASE
            active = ram[at + 0x7a] & 0x81 == 0x81 and int.from_bytes(ram[at + 0x26:at + 0x28], 'big') < 0x8000
            assert len(writes) == (64 if active else 0)
            assert expected_d0 == ((d0 & 0xffff0000) | ((int.from_bytes(ram[at + 0x7e:at + 0x80], 'big') << 7) & 65535)) if active else expected_d0 == d0
        else:
            assert writes[0:2] == [(2, 0x2ffff2, 0x2000), (2, 0x2ffff0, 0)]
            assert writes[-2:] == [(2, 0x2ffff2, 0x1000), (2, 0x2ffff0, 0)]
            assert expected[0x10:0x12] == b'\0\0'
        rows.append({'profile': profile, 'scene': scene, 'object': address, 'input_d0': d0,
            'result_d0': expected_d0, 'writes': len(writes),
            'input_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return expected, expected_d0

    for flags in range(256):
        ram = fixture()
        object_state(ram, 0x100100, flags, slot=0x1234, x=0x0138, y=0x01ff)
        compare(ram, profile='all256-flags')
    for axis, value in itertools.product(('x', 'y'), range(512)):
        ram = fixture()
        object_state(ram, 0x100100, slot=0x7fff, x=value if axis == 'x' else 0x0138,
            y=value if axis == 'y' else 0x0190)
        compare(ram, d0=0xbeef00ff, profile='all512-effective-%s-coordinates' % axis)
    for slot, x, y in itertools.product((0, 1, 0x7bfe, 0x7bff, 0x7dfe, 0x7dff, 0x7fff, 0x8000, 0xffff),
            (0x0137, 0x0138, 0x0139, 0x01f7, 0x01f8, 0x01ff, 0xffff), (0, 0xffff)):
        ram = fixture()
        object_state(ram, 0x100100, slot=slot, x=x, y=y)
        compare(ram, profile='slot-sign-high-word-wrap-unsigned-a000-threshold')
    for address in (0x100000, 0x100002, 0x10ff80):
        ram = fixture()
        object_state(ram, address, slot=0x7fff, x=0xff38, y=0xff90)
        compare(ram, address, 0xffffffff, profile='aligned-object-boundaries-upper-coordinate-bits')
    isolated = len(rows)
    for combination in range(16):
        ram = fixture()
        for index, address in enumerate(OBJECTS):
            object_state(ram, address, flags=0x81 if combination & (1 << index) else 1,
                slot=index * 31, x=0x0137 + index, y=0x01ff - index)
        expected, d0 = compare(ram, scene=True, profile='all16-scene-active-combinations')
        compare(expected, d0=d0, scene=True, profile='scene-carry-dirty-cleared-second-call')

    sentinel = b'previous-column-output\0\xff'
    def reject(ram, object_address, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(out), str(ports), hex(object_address), '0'], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    for address in (0xffffe, 0x100001, 0x10ff82, 0x110000, 0xffffffff):
        reject(fixture(), address, 'invalid-object-address')
    for size in (0, 65535, 65537):
        reject(bytes(size), 0x100100, 'invalid-ram-size')
    good = fixture()
    inp.write_bytes(good)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), str(inp), str(alias), str(ports), '0x100100', '0'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == good
        negatives.append({'failure': 'input-output-alias', 'input_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_addresses': [0x187d8, 0x1adf8],
        'entry_rom_offsets': [0x187d8, 0x1adf8], 'cases': len(rows), 'isolated_cases': isolated,
        'negative_cases': len(negatives), 'whole_65536_byte_ram_equal': True, 'full_uint32_d0_equal': True,
        'ordered_hardware_ports_equal': True, 'native_long_column_writes_not_split': True,
        'all256_flags_and512_effective_coordinates_each_axis_checked': True,
        'all16_scene_active_combinations_and_following_carry_checked': True,
        'negative_results': negatives, 'results': rows,
        'scope': 'Original187d8 column-control helper and continuous1adf8 wrapper. '
            'Native64 long writes per active object compared as indivisible port records; '
            'wrapper bank writes and four sequential objects compared with wholeRAM and fullD0. '
            'Offsets are seeded independently in every fullRAM fixture. Signed slot, unsigned '
            'temporary-x threshold, word/long wrap and upper inputD0 preserved. Graphics device '
            'rendering, other CPU registers/flags, natural interrupt scheduling and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
