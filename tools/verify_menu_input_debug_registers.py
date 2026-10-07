"""Native a472 decisions,9430 header and direct9aa8 debug full-register outputs."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import m68k_const as r
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

BASE, RETURN, STACK = 0x100000, 0xff000, 0x1feffc
EXITS = {0xa566: (1, 0), 0xa574: (2, 0), 0xa596: (3, 1),
         0xa5a0: (3, 2), 0xa58c: (3, 4), 0xa582: (3, 3), 0xa5ce: (0, 0)}


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    menu, font = [root / 'extracted/runtime' / name for name in ('control_menu_tree.ms5d', 'menu_font_6b.ms5d')]
    hashes = {'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
        'font': checked_resource(font, program, 0xe80c8, 0xe82c8)}
    folder = root / 'artifacts/menu_input_debug_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, action_out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'cpp.action.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 4096)
    state = {'mode': ''}
    ports, rows, negatives, sequences = [], [], [], []

    def code(cpu, address, size, user):
        if address == RETURN or (state['mode'] == 'input' and address in EXITS):
            cpu.emu_stop()

    def write(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            ports.append((size, address, value & ((1 << (8 * size)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)

    def fixture():
        ram = bytearray(hashlib.shake_256(b'menu-input-debug-registers:' + len(rows).to_bytes(4, 'big')).digest(65536))
        struct.pack_into('>II', ram, 0x7f0e, 0x107efe, 0x107efe)
        return ram

    def debug_fixture(index, flags, older, selected):
        ram = fixture()
        head = 0x107eee if older else 0x107efe
        struct.pack_into('>II', ram, 0x7f0e, head, 0x107efe)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        struct.pack_into('>H', ram, 0xf000, flags)
        for at in range(head - BASE, 0x7f0e, 16):
            struct.pack_into('>I', ram, at, 0x99ee)
            ram[at + 4] = 0
            ram[at + 6:at + 13] = bytes((15, selected, index, 4, 8, 24, 17))
            ram[at + 15] = 0
        if older:
            ram[head - BASE + 4] = 8
            ram[head - BASE + 9:head - BASE + 12] = bytes((10, 8, 8))
        return ram

    def compare(ram, mode, event=0, register_inputs=None):
        d1, d3 = register_inputs if register_inputs is not None else (
            (0xabcdab68 ^ (len(rows) * 0x1234567)) & 0xffffffff,
            (0xdead7000 ^ (len(rows) * 0x3210765)) & 0xffffffff)
        a2 = (0, 0x107efe, 0xdeadbeef, 0xffffffff)[len(rows) % 4] if mode == 'header' else struct.unpack_from('>I', ram, 0x7f12)[0]
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((r.UC_M68K_REG_SR, 0x2000), (r.UC_M68K_REG_A5, 0x108000),
                (r.UC_M68K_REG_A2, a2), (r.UC_M68K_REG_A1, 0x3650), (r.UC_M68K_REG_A7, STACK),
                (r.UC_M68K_REG_D0, event), (r.UC_M68K_REG_D1, d1), (r.UC_M68K_REG_D3, d3)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        ports.clear()
        state['mode'] = mode
        cpu.emu_start({'input': 0xa472, 'header': 0x9430, 'debug': 0x9aa8}[mode], RETURN, count=2000000)
        pc = cpu.reg_read(r.UC_M68K_REG_PC)
        assert pc in EXITS if mode == 'input' else pc == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        final_d1, final_d3 = cpu.reg_read(r.UC_M68K_REG_D1) & 0xffffffff, cpu.reg_read(r.UC_M68K_REG_D3) & 0xffffffff
        inp.write_bytes(ram)
        if mode == 'input':
            assert not ports and final_d3 == d3 and final_d1 >> 8 == 0
            kind, action = EXITS[pc]
            expected_action = bytes((kind, action, expected[0x7f1a]))
            result = {'d1': final_d1}
            args = [str(root / 'build/select_menu_input'), '--d1', str(d1), str(inp), str(out), str(action_out)]
        elif mode == 'header':
            assert not ports and final_d3 == d3
            result = {'a2': cpu.reg_read(r.UC_M68K_REG_A2) & 0xffffffff, 'd1': final_d1}
            args = [str(root / 'build/update_menu_header'), '--d1', str(d1), str(inp), str(out), str(a2)]
        else:
            if event in (1, 2, 3, 5):
                assert final_d1 >> 16 == 0
            else:
                assert final_d1 == d1 and final_d3 == d3
            result = {'a2': cpu.reg_read(r.UC_M68K_REG_A2) & 0xffffffff, 'line': final_d3 & 65535,
                'd1': final_d1, 'd3': final_d3}
            args = [str(root / 'build/dispatch_debug_menu'), str(inp), str(menu), str(font), str(out), str(ports_out), str(event), str(d1), str(d3)]
        actual = subprocess.run(args, capture_output=True, text=True)
        expected_ports = b''.join(struct.pack('>BII', *item) for item in ports)
        parsed = json.loads(actual.stdout) if not actual.returncode else None
        assert not actual.returncode and out.read_bytes() == expected and parsed == result, (len(rows), mode, event, actual.stdout, actual.stderr, result)
        if mode == 'input':
            assert action_out.read_bytes() == expected_action
        if mode == 'debug':
            assert ports_out.read_bytes() == expected_ports
        rows.append({'mode': mode, 'event': event, 'incoming_d1': d1, 'incoming_d3': d3, 'result': result,
            'final_native_d3': final_d3, 'native_pc': pc, 'ports': len(ports), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(out.read_bytes()), (parsed['d1'], parsed['d3'] if mode == 'debug' else d3)

    for enabled, first in itertools.product((0, 1, 2, 3, 255), range(256)):
        ram = fixture()
        ram[0x7f0b], ram[0x4cba], ram[0x4cc0] = enabled, first, (first * 73 + 19) & 255
        compare(ram, 'input')
    for first, second in itertools.product((0, 1, 2, 3, 4, 8, 16, 32, 63, 255), repeat=2):
        ram = fixture()
        ram[0x7f0b], ram[0x4cba], ram[0x4cc0] = 3, first, second
        compare(ram, 'input')
    for request, enabled in itertools.product(range(16), range(4)):
        ram = fixture()
        ram[0x12], ram[0xfd82], ram[0xfdb6], ram[0xfdb7] = 2, 0, 1, 1
        ram[0x4cb5], ram[0x7df0] = request | 0xf0, enabled | 0xf0
        compare(ram, 'header')
    for mode, replay, live, buttons, mask, status in itertools.product((0, 2, 255), (0, 1, 255), (0, 255),
            ((0, 0), (128, 127), (127, 128), (255, 255)), (0, 2, 8, 255), ((0, 3), (255, 1))):
        ram = fixture()
        ram[0x12], ram[0xfd82], ram[0xf002] = mode, replay, live
        ram[0x4cb9], ram[0x4cbf], ram[0x4cb4] = buttons[0], buttons[1], mask
        ram[0xfdb6], ram[0xfdb7] = status
        ram[0x7df0] = (0, 1, 2, 3, 0xfc, 0xfd, 0xfe, 255)[len(rows) % 8]
        compare(ram, 'header')
    for row, event, flags, older, same in itertools.product(range(15), range(8), (0, 65535, 0xaaaa, 0x5555), (False, True), (False, True)):
        compare(debug_fixture(row, flags, older, row if same else (row + 1) % 15), 'debug', event)
    for row, older in itertools.product((0, 7, 14), (False, True)):
        ram = debug_fixture(row, 0xaaaa, older, row)
        regs, begin = (0xabcdab68, 0xdead7000), len(rows)
        for event in (1, 2, 3, 5, 0, 6, 7, 4):
            ram, regs = compare(ram, 'debug', event, regs)
        sequences.append({'row': row, 'older': older, 'frames': len(rows) - begin, 'full_ram_d1_d3_cpp_outputs_carried': True})

    sentinel = b'prior-menu-input-debug-output\0\xff'
    def reject(mode, ram, d1, d3='0', selected_font=font, label='invalid-argument', selected_event='1'):
        inp.write_bytes(ram)
        for path in (out, ports_out, action_out):
            path.write_bytes(sentinel)
        if mode == 'input':
            args = [str(root / 'build/select_menu_input'), '--d1', d1, str(inp), str(out), str(action_out)]
        elif mode == 'header':
            args = [str(root / 'build/update_menu_header'), '--d1', d1, str(inp), str(out), '0x107efe']
        else:
            args = [str(root / 'build/dispatch_debug_menu'), str(inp), str(menu), str(selected_font), str(out), str(ports_out), selected_event, d1, d3]
        actual = subprocess.run(args, capture_output=True, text=True)
        assert actual.returncode and all(path.read_bytes() == sentinel for path in (out, ports_out, action_out)), (mode, label, actual.stdout, actual.stderr)
        negatives.append({'mode': mode, 'failure': label, 'outputs_preserved': True, 'original_executed': False})
    for mode in ('input', 'header', 'debug'):
        for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
            reject(mode, debug_fixture(0, 0, False, 0), invalid, label='invalid-d1')
            if mode == 'debug':
                reject(mode, debug_fixture(0, 0, False, 0), '0', invalid, label='invalid-d3')
        for size in (0, 65535, 65537):
            reject(mode, bytes(size), '0', label='invalid-ram-size')
    reject('debug', debug_fixture(15, 0, False, 0), '0', label='unsupported-debug-row')
    short_font = folder / 'short-font.ms5d'
    short_font.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0xe80c8, 0xe80c8, 1, zlib.crc32(b'X'), 0) + b'X')
    reject('debug', debug_fixture(0, 0, False, 0), '0', selected_font=short_font, label='late-font-lookup-after-toggle-candidate')
    for invalid in ('-1', '65536', '0x10000', '0x', '1x', ''):
        reject('debug', debug_fixture(0, 0, False, 0), '0', label='invalid-event', selected_event=invalid)
    for kind in ('same', 'hardlink', 'symlink'):
        ram = debug_fixture(0, 0, False, 0)
        inp.write_bytes(ram)
        ports_out.write_bytes(sentinel)
        alias = inp if kind == 'same' else folder / (kind + '.bin')
        if kind != 'same':
            alias.unlink(missing_ok=True)
            if kind == 'hardlink':
                alias.hardlink_to(inp)
            else:
                alias.symlink_to(inp)
        actual = subprocess.run([str(root / 'build/dispatch_debug_menu'), str(inp), str(menu), str(font), str(alias), str(ports_out), '1', '0', '0'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram and ports_out.read_bytes() == sentinel
        negatives.append({'mode': 'debug', 'failure': 'input-output-' + kind + '-alias', 'outputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    counts = {mode: sum(row['mode'] == mode for row in rows) for mode in ('input', 'header', 'debug')}
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__, 'original_rom_unmodified': True,
        'runtime_hashes': hashes, 'cases': len(rows), 'counts': counts, 'negative_cases': len(negatives),
        'ordered_port_events': sum(row['ports'] for row in rows), 'all_full_ram_register_outputs_and_ordered_ports_equal': True,
        'native_d3_preserved_for_input_and_header': True, 'output_carry_sequences': sequences, 'results': rows,
        'negative_results': negatives, 'scope': 'Native a472 stops at first decision target without executing actions; '
            '9430 runs real9086 and compares A2/D1 while preserving fullD3; direct9aa8 begins with A2=current '
            'as established by9b3e context. Debug1/2/3/5 text paths and no-op/close paths, all15 rows, '
            'flags/head/selection and six C++ RAM/register carry sequences. Debug entry9b3e itself, '
            'other CPU scratch registers, callbacks, pixels and hardware timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'counts': counts, 'negative_cases': len(negatives), 'ports': sum(row['ports'] for row in rows),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
