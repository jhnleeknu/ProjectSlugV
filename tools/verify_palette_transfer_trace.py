"""Compare native72fa RAM, both logical palette banks and exact MMIO trace."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN, STACK, PALETTE = 0x100000, 0xff000, 0x1feffc, 0x400000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    executable = root / 'build/trace_palette_transfer'
    folder = root / 'artifacts/palette_transfer_trace'
    folder.mkdir(parents=True, exist_ok=True)
    inp, banks_in, out, banks_out, ports, report = [folder / name for name in
        ('input.bin', 'banks.bin', 'cpp.bin', 'cpp.banks.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address, length in ((0x300000, 0x1000), (0x3a0000, 0x1000), (PALETTE, 8192)):
        cpu.mem_map(address, length)
    state = {'bank': 0, 'banks': None}
    writes, rows, negatives = [], [], []

    def hook(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        writes.append((size, address, value))
        if address in (0x3a000f, 0x3a001f):
            assert size == 1
            state['bank'] = int(address == 0x3a001f)
            cpu.mem_write(PALETTE, bytes(state['banks'][state['bank']]))
        elif address == 0x300001:
            assert size == 1
        else:
            assert PALETTE <= address < PALETTE + 8192 and size in (2, 4)
            at = address - PALETTE
            state['banks'][state['bank']][at:at + size] = value.to_bytes(size, 'big')

    for start, end in ((0x300001, 0x300001), (0x3a000f, 0x3a001f), (PALETTE, PALETTE + 8191)):
        cpu.hook_add(UC_HOOK_MEM_WRITE, hook, begin=start, end=end)

    def fixture(dirty=(), pending=128, display=0, counter=0):
        seed = b'ms5-palette-trace-v1:' + len(rows).to_bytes(4, 'big')
        ram = bytearray(hashlib.shake_256(seed + b'ram').digest(65536))
        banks = hashlib.shake_256(seed + b'banks').digest(16384)
        struct.pack_into('>H', ram, 0x7dea, counter)
        ram[0x7ded], ram[0x7dec] = pending, display
        for block in range(256):
            ram[0x5da2 + block * 32] &= 127
        for block in dirty:
            ram[0x5da2 + block * 32] |= 128
        return ram, banks

    def compare(ram, banks, d0=0xabcdef35, profile='matrix'):
        cpu.mem_write(BASE, bytes(ram))
        state['banks'] = [bytearray(banks[:8192]), bytearray(banks[8192:])]
        state['bank'] = 0
        cpu.mem_write(PALETTE, banks[:8192])
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A7, STACK), (UC_M68K_REG_D0, d0)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(0x72fa, RETURN, count=10000)
        assert cpu.reg_read(UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_banks = b''.join(state['banks'])
        expected_d0 = cpu.reg_read(UC_M68K_REG_D0) & 0xffffffff
        expected_ports = b''.join(struct.pack('>BII', *event) for event in writes)
        expected_result = {'display_bank': state['bank'], 'd0': expected_d0, 'writes': len(writes)}
        assert bytes(cpu.mem_read(PALETTE, 8192)) == state['banks'][state['bank']]
        counter = int.from_bytes(ram[0x7dea:0x7dec], 'big')
        palette_events = [event for event in writes if PALETTE <= event[1] < PALETTE + 8192]
        if counter == 0x2000:
            assert len(palette_events) == 2049 and all(event[0] == 4 for event in palette_events[:-1])
            assert [event[1] for event in palette_events[:-1]] == list(range(PALETTE + 8188, PALETTE - 1, -4))
            assert palette_events[-1] == (2, PALETTE, 0)
            assert not any(event[1] == 0x300001 for event in writes)
        else:
            assert sum(event[1] == 0x300001 for event in writes) == 1
            assert all(event[0] == 4 for event in palette_events)
            assert [event[1] for event in palette_events] == sorted(event[1] for event in palette_events)
        assert state['bank'] == int(ram[0x7dec] != 0)
        inp.write_bytes(ram)
        banks_in.write_bytes(banks)
        for path in (out, banks_out, ports):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(executable), str(inp), str(banks_in), str(out), str(banks_out), str(ports), hex(d0)], capture_output=True, text=True)
        actual_ram = out.read_bytes() if out.exists() else b''
        if actual.returncode or actual_ram != expected or not banks_out.exists() or banks_out.read_bytes() != expected_banks or not ports.exists() or ports.read_bytes() != expected_ports or json.loads(actual.stdout) != expected_result:
            diff = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(expected), len(actual_ram))) if expected[at] != actual_ram[at]]
            raise ValueError(repr((len(rows), profile, expected_result, actual.stdout, actual.stderr, diff[:20])))
        rows.append({'profile': profile, 'counter': counter, 'pending': ram[0x7ded], 'display': ram[0x7dec],
            'input_d0': d0, 'result': expected_result, 'palette_writes': len(palette_events),
            'input_ram_sha256': hashlib.sha256(ram).hexdigest(), 'input_banks_sha256': hashlib.sha256(banks).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'banks_sha256': hashlib.sha256(expected_banks).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return expected, expected_banks, expected_d0

    for block, display in itertools.product(range(256), (0, 255)):
        ram, banks = fixture((block,), display=display)
        compare(ram, banks, d0=0xabcd0000 | block, profile='all256-single-dirty-blocks-both-display-banks')
    for dirty, pending, display, d0 in itertools.product(((), tuple(range(256)), tuple(range(0, 256, 2)), (0, 1, 127, 255)),
            (0, 1, 128, 255), (0, 1, 255), (0, 0xffffffff)):
        ram, banks = fixture(dirty, pending, display)
        compare(ram, banks, d0, profile='none-all-mixed-dirty-pending-display-d0')
    for pattern, display, d0 in itertools.product((bytes(32), bytes([255]) * 32,
            bytes(range(32)), hashlib.shake_256(b'independent-special-fill-pattern').digest(32)), (0, 1, 255), (0, 0x12345678, 0xffffffff)):
        ram, banks = fixture(range(256), pending=255, display=display, counter=0x2000)
        ram[0x7da2:0x7dc2] = pattern
        expected, carried_banks, next_d0 = compare(ram, banks, d0, profile='special2000-descending-fill-no-watchdog')
        compare(expected, carried_banks, next_d0, profile='special-fill-then-normal-carried-transfer')

    sentinel = b'previous-palette-trace-output\0\xff'
    def reject(ram, banks, label):
        inp.write_bytes(ram)
        banks_in.write_bytes(banks)
        for path in (out, banks_out, ports):
            path.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(banks_in), str(out), str(banks_out), str(ports), '0'], capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, banks_out, ports))
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    for counter in (1, 0x1fff, 0x2001, 0xffff):
        ram, banks = fixture(counter=counter)
        reject(ram, banks, 'unsupported-special-counter')
    ram, banks = fixture()
    for size in (0, 65535, 65537):
        reject(bytes(size), banks, 'invalid-ram-size')
    for size in (0, 8192, 16383, 16385):
        reject(ram, bytes(size), 'invalid-bank-size')
    inp.write_bytes(ram)
    banks_in.write_bytes(banks)
    aliases = (inp, folder / 'hardlink.bin', folder / 'symlink.bin')
    for alias in aliases[1:]:
        alias.unlink(missing_ok=True)
    aliases[1].hardlink_to(inp)
    aliases[2].symlink_to(inp.name)
    for alias in aliases:
        actual = subprocess.run([str(executable), str(inp), str(banks_in), str(alias), str(banks_out), str(ports), '0'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram and banks_in.read_bytes() == banks
        negatives.append({'failure': 'input-output-alias', 'inputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': 0x72fa,
        'entry_rom_offset': 0x72fa, 'cases': len(rows), 'negative_cases': len(negatives),
        'whole_65536_byte_ram_equal': True, 'both_8192_byte_palette_banks_equal': True,
        'full_uint32_d0_and_display_bank_equal': True, 'ordered_hardware_ports_equal': True,
        'normal_ascending_and_special_descending_native_long_writes_asserted': True,
        'negative_results': negatives, 'results': rows,
        'scope': 'Native72fa normal upload and exact2000 special fill. Bank-selector hooks '
            'switch the physical palette window and retain both logical banks without altering '
            'ROM. All256 single dirty blocks, pending gates, mixed/all/none markers and independent '
            'special patterns compared. WholeRAM, both banks, fullD0 and ordered bank/palette/watchdog '
            'writes verified. Other special counters are unsupported API inputs. Device timing, '
            'physical display effects, other CPU registers and natural scheduling excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'report': str(report),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
