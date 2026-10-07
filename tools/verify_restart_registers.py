"""Compare direct native static-object restart with transactional C++ D1/D3."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, OBJECT, RETURN = 0x100000, 0x820, 0xff000
HARNESS = r'''
#include "ms5/object_restart.h"
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
int main(int argc, char** argv) {
    if (argc != 10) return 2;
    std::vector<std::uint8_t> ram(65536);
    std::ifstream input(argv[1], std::ios::binary);
    if (!input.read(reinterpret_cast<char*>(&ram[0]), 65536)) return 2;
    const std::vector<std::uint8_t> before = ram;
    std::uint32_t d1 = static_cast<std::uint32_t>(std::strtoul(argv[8], NULL, 0));
    std::uint32_t d3 = static_cast<std::uint32_t>(std::strtoul(argv[9], NULL, 0));
    const std::uint32_t old_d1 = d1, old_d3 = d3;
    std::vector<ms5::VideoPortWrite> writes(1);
    writes[0].address = 0xabcdefU; writes[0].value = 0x12345678U; writes[0].size = 4;
    std::string error;
    if (!ms5::restart_static_object(ram, static_cast<std::uint32_t>(std::strtoul(argv[5], NULL, 0)),
        static_cast<std::uint32_t>(std::strtoul(argv[6], NULL, 0)),
        static_cast<std::uint8_t>(std::strtoul(argv[7], NULL, 0)), writes, error, &d1, &d3)) {
        if (ram != before || d1 != old_d1 || d3 != old_d3 || writes.size() != 1 ||
            writes[0].address != 0xabcdefU || writes[0].value != 0x12345678U || writes[0].size != 4) return 3;
        std::cout << "{\"failure\":true,\"d1\":" << d1 << ",\"d3\":" << d3 << "}\n";
        std::cerr << error << '\n'; return 1;
    }
    std::ofstream output(argv[2], std::ios::binary | std::ios::trunc);
    std::ofstream ports(argv[3], std::ios::binary | std::ios::trunc);
    if (!output || !ports) return 2;
    output.write(reinterpret_cast<const char*>(&ram[0]), 65536);
    for (std::size_t index = 0; index < writes.size(); ++index) {
        const ms5::VideoPortWrite& write = writes[index];
        char bytes[9]; bytes[0] = static_cast<char>(write.size);
        for (unsigned int i = 0; i < 4; ++i) {
            bytes[1+i] = static_cast<char>(write.address >> (24U-i*8U));
            bytes[5+i] = static_cast<char>(write.value >> (24U-i*8U));
        }
        ports.write(bytes, 9);
    }
    output.close(); ports.close();
    if (!output || !ports) return 2;
    std::cout << "{\"d1\":" << d1 << ",\"d3\":" << d3 << "}\n";
    return 0;
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    folder = root / 'artifacts/restart_registers'
    folder.mkdir(parents=True, exist_ok=True)
    harness, executable, inp, out, ports, report = [folder / name for name in
        ('restart_harness.cpp', 'restart_harness', 'input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    harness.write_text(HARNESS)
    sources = ['object_restart', 'object_state', 'palette_allocator', 'position_state']
    command = ['c++', '-std=c++11', '-Wall', '-Wextra', '-pedantic', '-I', str(root / 'engine/include'),
        str(harness), *[str(root / 'engine/src' / (name + '.cpp')) for name in sources], '-o', str(executable)]
    subprocess.run(command, check=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x300000, 0x1000)
    writes, rows, negatives = [], [], []

    def on_return(cpu, address, size, user):
        cpu.emu_stop()

    def on_write(cpu, access, address, size, value, user):
        if address == 0x300001:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536 or
                  0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native restart write: ' + hex(address))

    cpu.hook_add(UC_HOOK_CODE, on_return, begin=RETURN, end=RETURN)
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)

    def call(entry):
        cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(m.UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        cpu.emu_start(entry, 0xffffff, count=1000000)
        assert cpu.reg_read(m.UC_M68K_REG_PC) == RETURN

    cpu.mem_write(BASE, bytes(65536))
    cpu.reg_write(m.UC_M68K_REG_A5, 0x108000)
    call(0x3ef2)
    palette_ram = bytes(cpu.mem_read(BASE, 65536))

    def fixture(ids=(), shared=False, reference=None):
        ram = bytearray(hashlib.shake_256(('restart-registers-' + str(len(rows))).encode()).digest(65536))
        ram[0x4d92:0x5da2] = palette_ram[0x4d92:0x5da2]
        struct.pack_into('>H', ram, OBJECT + 0x10, 0)
        ram[OBJECT + 0x1d] = 0
        ram[OBJECT + 0x6c] = 0xff
        cpu.mem_write(BASE, bytes(ram))
        for identifier in ids:
            cpu.reg_write(m.UC_M68K_REG_A6, BASE + OBJECT)
            cpu.reg_write(m.UC_M68K_REG_D0, identifier)
            cpu.reg_write(m.UC_M68K_REG_D1, 0)
            call(0x8ebe)
        if shared:
            cpu.mem_write(BASE + 0x41d, b'\0')
            cpu.reg_write(m.UC_M68K_REG_A6, BASE + 0x400)
            cpu.reg_write(m.UC_M68K_REG_D0, ids[0])
            cpu.reg_write(m.UC_M68K_REG_D1, 0)
            call(0x8ebe)
        ram = bytearray(cpu.mem_read(BASE, 65536))
        if reference is not None:
            slot = ram[OBJECT + 0x19]
            struct.pack_into('>H', ram, 0x4d92 + slot * 16 + 8, reference)
        return ram

    def invoke(ram, d1, d3, watchdog, callback, object_address=BASE+OBJECT):
        inp.write_bytes(ram)
        return subprocess.run([str(executable), str(inp), str(out), str(ports), 'unused',
            str(object_address), str(callback), str(watchdog), str(d1), str(d3)],
            capture_output=True, text=True)

    def compare(ram, label, d1, d3, watchdog=0x78, callback=0xf12):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((m.UC_M68K_REG_A0, BASE + OBJECT), (m.UC_M68K_REG_A1, callback),
                (m.UC_M68K_REG_A5, 0x108000), (m.UC_M68K_REG_A6, 0x100400),
                (m.UC_M68K_REG_D0, 0x12345600 | watchdog),
                (m.UC_M68K_REG_D1, d1), (m.UC_M68K_REG_D3, d3)):
            cpu.reg_write(reg, value)
        writes.clear()
        call(0x2a28)
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        registers = {'d1': cpu.reg_read(m.UC_M68K_REG_D1) & 0xffffffff,
                     'd3': cpu.reg_read(m.UC_M68K_REG_D3) & 0xffffffff}
        assert registers['d1'] == 0xffffffff
        assert writes == [(1, 0x300001, watchdog)]
        result = invoke(ram, d1, d3, watchdog, callback)
        parsed = json.loads(result.stdout) if result.returncode == 0 else None
        if result.returncode or out.read_bytes() != expected or ports.read_bytes() != expected_ports or parsed != registers:
            actual = out.read_bytes() if out.exists() else b''
            differences = [(hex(i), expected[i], actual[i]) for i in range(min(len(actual), 65536)) if actual[i] != expected[i]]
            raise ValueError('Restart mismatch: ' + repr((label, hex(d1), hex(d3), differences[:8], registers, parsed, result.returncode, result.stderr)))
        rows.append({'profile': label, 'initial_d1': d1, 'initial_d3': d3,
            'palette_count': ram[OBJECT+0x1d], 'coordinate_index': ram[OBJECT+0x6c],
            'watchdog': watchdog, 'callback': callback, 'native_final_registers': registers,
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for index, d1, d3, watchdog, callback in itertools.product((0x80, 0xff),
            (0, 0x1234ab68, 0xffffffff), (0, 0x12347088, 0xffffffff), (0, 0x78, 0xff), (0, 0xf12)):
        ram = fixture()
        ram[OBJECT+0x6c] = index
        compare(ram, 'no-cleanup', d1, d3, watchdog, callback)
    for ids, shared, reference in (((), False, None), ((7,), False, None),
            ((7,263), False, None), ((7,263,519,7), False, None),
            ((7,), True, None), ((7,), False, 0), ((7,), False, 0xffff)):
        for d3 in (0x12347088, 0xffffffff):
            compare(fixture(ids, shared, reference), 'palette-release-' + repr((ids, shared, reference)), 0x5678abcd, d3)
    for index, parent, stamp, old_y, palettes in itertools.product(range(8), (0, 0x100200),
            (0, 1, 255), (0, 0x7fffffff, 0x80000000, 0xffffffff), ((), (7,263))):
        ram = fixture(palettes)
        ram[OBJECT+0x6c] = index
        at = 0xd4e6 + index*0x2c
        struct.pack_into('>5I', ram, at, 0xffff0001, 0x7fffffff, 1, 0x80000001, parent)
        struct.pack_into('>II', ram, at+0x14, 0x13579bdf, old_y)
        ram[at+0x24:at+0x26] = bytes((stamp, 0xa0))
        ram[0xd494] = (0, 1, 255)[len(rows) % 3]
        if parent:
            struct.pack_into('>II', ram, 0x214, 0x00010001, 0x80000001)
            ram[0x225] = 0x40
        compare(ram, 'attached-coordinate', 0x1234ab68, 0x56787088)
        assert rows[-1]['native_final_registers']['d3'] == old_y

    sentinel = b'preserved-restart-output'
    for label in ('nonzero-object-type', 'invalid-coordinate-index', 'invalid-parent-after-palette-release',
                  'odd-object-address', 'odd-callback'):
        ram = fixture((7,))
        address, callback = BASE+OBJECT, 0xf12
        if label == 'nonzero-object-type': struct.pack_into('>H', ram, OBJECT+0x10, 1)
        elif label == 'invalid-coordinate-index': ram[OBJECT+0x6c] = 8
        elif label == 'invalid-parent-after-palette-release':
            ram[OBJECT+0x6c] = 0
            struct.pack_into('>I', ram, 0xd4e6+0x10, 0x100201)
        elif label == 'odd-object-address': address += 1
        else: callback += 1
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        result = invoke(ram, 0x1234ab68, 0x56787088, 0x78, callback, address)
        assert result.returncode == 1 and out.read_bytes() == sentinel and ports.read_bytes() == sentinel and inp.read_bytes() == ram
        assert json.loads(result.stdout) == {'failure': True, 'd1': 0x1234ab68, 'd3': 0x56787088}
        negatives.append({'failure': label, 'ram_ports_registers_preserved': True})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'native_entry_cpu_address': 0x2a28, 'program_code_modified': False,
        'harness_source_sha256': hashlib.sha256(HARNESS.encode()).hexdigest(),
        'compile_command': command, 'cases': len(rows), 'negative_cases': len(negatives),
        'whole_ram_full_d1_d3_ordered_watchdog_equal': True,
        'native_allocator_initializer': 0x3ef2, 'native_allocator_acquire': 0x8ebe,
        'results': rows, 'negative_results': negatives,
        'scope': 'Direct returned static-object 0x2a28 with original code and helper routines. '
            'Palette fixtures use original initializer/acquire routines; coordinate and other '
            'RAM bytes are controlled inputs. Full D1/D3, whole RAM and ordered watchdog '
            'writes compared. Errors verify C++ transactional RAM/register/port preservation. '
            'No linked objects, trap/fault behavior, other registers, stack memory or hardware timing claimed.'}, indent=2)+'\n')
    print('Restart registers:', len(rows), 'native/C++ cases;', len(negatives),
          'transactional rejections;', hashlib.sha256(report.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
