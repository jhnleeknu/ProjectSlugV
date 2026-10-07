"""Compare continuous unmodified nativebbe/a74/a2c/a4e credit requests."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
    UC_M68K_REG_D6, UC_M68K_REG_D7, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, ENTRY, RETURN, STACK = 0x100000, 0xbbe, 0xff000, 0x1feffc


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/process_credit_request'
    folder = root / 'artifacts/credit_request'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    rows, negatives, reached = [], [], set()

    def hook(cpu, address, size, user):
        reached.add(address)

    for address in (0xa74, 0xa2c, 0xa4e, 0xa68):
        cpu.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)

    def fixture(request=3, credits=(0x99, 0x99), mode=2, blocked=0, masks=(3, 0, 3), previous=0):
        ram = bytearray(hashlib.shake_256(b'ms5-credit-request-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        ram[4], ram[5] = credits
        ram[0x14], ram[0xfdaf], ram[0xfd82], ram[0xfdb4] = request, mode, blocked, previous
        ram[0xf004], ram[0xf006], ram[0xf007] = masks
        return ram

    def native(ram, d0):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, STACK), (UC_M68K_REG_D0, d0),
                (UC_M68K_REG_D6, 0x12345678), (UC_M68K_REG_D7, 0xcafef00d)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        cpu.emu_start(ENTRY, RETURN, count=1000)
        assert cpu.reg_read(UC_M68K_REG_PC) == RETURN
        return bytes(cpu.mem_read(BASE, 65536)), cpu.reg_read(UC_M68K_REG_D0) & 0xffffffff

    def compare(ram, d0, profile):
        expected, expected_d0 = native(ram, d0)
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), str(inp), str(out), hex(d0)], capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or json.loads(actual.stdout) != {'d0': expected_d0}:
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, hex(d0), hex(expected_d0), actual.stdout, actual.stderr, diff[:20])))
        if ram[0xfd82]:
            assert expected == ram and expected_d0 == d0
        rows.append({'profile': profile, 'request': ram[0x14], 'credits': list(ram[4:6]),
            'mode': ram[0xfdaf], 'blocked': ram[0xfd82], 'masks': list(ram[0xf004:0xf008]),
            'input_d0': d0, 'result_d0': expected_d0,
            'input_sha256': hashlib.sha256(ram).hexdigest(), 'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return expected, expected_d0

    for credit, request in itertools.product(range(256), (1, 2, 3)):
        compare(fixture(request, (credit, 255 - credit)), 0xabcdabff, 'all-credit-bytes-valid-and-invalid-bcd')
    for request in range(256):
        compare(fixture(request, (0x10, 0x01), previous=(request * 73) & 255,
            masks=((request * 17) & 255, (request * 31) & 255, (request * 47) & 255)),
            0x12345678, 'all-request-bytes-and-masks')
    for mode, request, blocked, masks, d0 in itertools.product((0, 1, 2, 3, 255), (0, 3, 255),
            (0, 1, 255), ((0, 0, 0), (3, 255, 3), (255, 0x55, 255)), (0, 0xffffffff)):
        compare(fixture(request, mode=mode, blocked=blocked, masks=masks, previous=0xa5), d0,
            'mode-request-mask-immediate-return-matrix')
    isolated = len(rows)
    ram = fixture(0)
    d0 = 0xabcdabff
    for frame in range(32):
        changed = bytearray(ram)
        changed[0x14] |= (1, 2, 3, 0)[frame % 4]
        ram, d0 = compare(changed, d0, '32-carried-host-credit-requests')

    sentinel = b'previous-credit-request-output\0\xff'
    for size in (0, 1, 65535, 65537):
        inp.write_bytes(bytes(size))
        out.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(out), '0'], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel
        negatives.append({'failure': 'invalid-ram-size', 'size': size, 'output_preserved': True, 'original_executed': False})
    good = fixture()
    inp.write_bytes(good)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), str(inp), str(alias), '0'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == good
        negatives.append({'failure': 'input-output-alias', 'alias': alias.name,
            'input_preserved': True, 'original_executed': False})
    assert reached == {0xa74, 0xa2c, 0xa4e, 0xa68}
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'helper_cpu_addresses_reached': sorted(reached),
        'cases': len(rows), 'isolated_cases': isolated, 'carried_frames': 32,
        'negative_cases': len(negatives), 'whole_65536_byte_ram_equal': True, 'full_uint32_d0_equal': True,
        'all_256_credit_and_request_bytes_checked': True, 'nonzero_fd82_preserves_ram_and_d0': True,
        'negative_results': negatives, 'results': rows,
        'scope': 'Continuous nativebbe througha74/a2c/a4e and return, including actual SBCD '
            'execution for all256 credit byte encodings. FullRAM and fulluint32 D0 compared; '
            'upper word retained and low word shifts observed directly from original CPU. '
            'Carried requests use explicit host input writes. Other register outputs, flags, '
            'BIOS scheduling, coin hardware and natural interrupt timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
