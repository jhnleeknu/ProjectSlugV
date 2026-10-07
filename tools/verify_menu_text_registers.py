"""Compare returned native menu text/navigation boundaries and full D1/D3."""
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
from verify_stage_catalog import SOURCE_SHA256, checked_resource

BASE, RETURN = 0x100000, 0xff000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    resource = root / 'extracted/runtime/control_menu_tree.ms5d'
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    resource_hash = checked_resource(resource, program, 0x937e, 0x9aa8)
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    folder = root / 'artifacts/menu_text_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
                             ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows, negatives = [], [], []

    def on_write(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536 or
                  0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + hex(address))

    def on_return(cpu, address, size, user):
        cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    cpu.hook_add(UC_HOOK_CODE, on_return, begin=RETURN, end=RETURN)

    def fixture(menu, count, height, row, selected, nested, renderer):
        ram = bytearray(hashlib.shake_256(('menu-registers-' + str(len(rows))).encode()).digest(65536))
        head = 0x107eee if nested else 0x107efe
        struct.pack_into('>II', ram, 0x7f0e, head, 0x107efe)
        struct.pack_into('>I', ram, 0x7f16, renderer)
        for at in range(head - BASE, 0x7f0e, 16):
            struct.pack_into('>I', ram, at, menu)
            ram[at + 4] = height
            ram[at + 6:at + 13] = bytes((count, selected, row, 4, 8, 24, 17))
            ram[at + 14:at + 16] = bytes((0xff, 0))
        if nested:
            ram[0x7ef2] = 8
            ram[0x7ef7:0x7efa] = bytes((10, 8, 8))
        return ram

    def cli(mode, clip, d1, d3, requested=0, registers=True):
        options = ['--registers', str(d1), str(d3)] if registers else []
        if mode == 'item':
            options = options + ['--item'] if len(rows) & 1 else ['--item'] + options
        if mode in ('step', 'select'):
            return [str(root / 'build/navigate_menu'), *options, str(inp), str(resource),
                    str(out), str(ports), mode, str(requested), str(font)]
        return [str(root / 'build/draw_menu_text'), *options, str(inp), str(resource),
                str(out), str(ports), str(int(clip)), str(d3 & 65535), str(font)]

    def compare(ram, mode, clip, d1, d3, requested=0, registers=True):
        cpu.mem_write(BASE, bytes(ram))
        renderer = struct.unpack_from('>I', ram, 0x7f16)[0]
        for reg, value in ((m.UC_M68K_REG_SR, 0x2000), (m.UC_M68K_REG_A5, 0x108000),
                           (m.UC_M68K_REG_A1, 0xa008 if clip else 0x3650),
                           (m.UC_M68K_REG_A2, 0x107efe), (m.UC_M68K_REG_A7, 0x1feffc),
                           (m.UC_M68K_REG_D0, requested), (m.UC_M68K_REG_D1, d1),
                           (m.UC_M68K_REG_D3, d3)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        writes.clear()
        entry = {'text': 0x9e1a, 'item': 0x9d3a, 'step': 0xa216, 'select': 0xa280}[mode]
        try:
            cpu.emu_start(entry, 0xffffff, count=3000000)
        except unicorn.UcError as error:
            raise ValueError('Native menu exception: ' + repr((len(rows), mode,
                ram[0x7f06], hex(cpu.reg_read(m.UC_M68K_REG_PC))))) from error
        assert cpu.reg_read(m.UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        native_d1 = cpu.reg_read(m.UC_M68K_REG_D1) & 0xffffffff
        native_d3 = cpu.reg_read(m.UC_M68K_REG_D3) & 0xffffffff
        expected_regs = {'line': native_d3 & 65535, 'd1': native_d1, 'd3': native_d3}
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        ports.unlink(missing_ok=True)
        result = subprocess.run(cli(mode, clip, d1, d3, requested, registers),
                                capture_output=True, text=True)
        parsed = json.loads(result.stdout) if registers and result.returncode == 0 else None
        if result.returncode or not out.exists() or out.read_bytes() != expected or not ports.exists() or ports.read_bytes() != expected_ports or (registers and parsed != expected_regs) or (not registers and result.stdout):
            actual = out.read_bytes() if out.exists() else b''
            differences = [(hex(i), expected[i], actual[i]) for i in range(min(len(actual), 65536)) if actual[i] != expected[i]]
            raise ValueError('Menu register mismatch: ' + repr((len(rows), mode, clip,
                renderer, ram[0x7f02], ram[0x7f06], hex(d1), hex(d3), differences[:8],
                expected_regs, parsed, result.returncode, result.stderr)))
        rows.append({'mode': mode, 'entry_cpu_address': entry, 'clip': clip,
            'menu_cpu_address': struct.unpack_from('>I', ram, 0x7efe)[0],
            'renderer_cpu_address': renderer, 'height': ram[0x7f02],
            'row': ram[0x7f06], 'selected': ram[0x7f05], 'requested': requested,
            'nested': ram[0x7f0e:0x7f12] != ram[0x7f12:0x7f16],
            'initial_d1': d1, 'initial_d3': d3, 'native_final_registers': expected_regs,
            'register_reporting': registers, 'port_events': len(writes),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    registers = ((0x1234ab68, 0x56787088), (0xffff0f03, 0xdeadffff), (3, 0x7000))
    for mode, height, row, selected, nested, clip, renderer, regs in itertools.product(
            ('text', 'item'), (0, 1, 8), range(6), (0, 5), (False, True),
            (False, True), (0x3650, 0x9332), registers):
        # Full-menu drawing does not consume an input row; avoid duplicate fixtures.
        if mode == 'text' and row != 0:
            continue
        compare(fixture(0x93e0, 6, height, row, selected, nested, renderer), mode, clip, *regs)
    # Native area menu rows 0/1 provide null callbacks and separator evidence,
    # without invoking stage data callbacks on rows 2..9.
    for row, height, clip, nested, regs in itertools.product((0, 1), (0, 1, 8),
            (False, True), (False, True), registers):
        compare(fixture(0x958a, 10, height, row, 0, nested, 0x3650), 'item', clip, *regs)
    for mode, old, height, nested, renderer, direction, regs in itertools.product(
            ('step', 'select'), range(6), (0, 1, 8), (False, True),
            (0x3650, 0x9332), (0, 2), registers):
        ram = fixture(0x93e0, 6, height, old, old, nested, renderer)
        ram[0x7f0d] = direction
        compare(ram, mode, True, *regs, requested=5)
    for mode in ('text', 'step'):
        compare(fixture(0x93e0, 6, 8, 0, 0, False, 0x3650), mode, False, 0, 0,
                registers=False)

    sentinel = b'preserved-menu-register-output'
    def reject(mode, options, label, line=0x7088):
        ram = fixture(0x93e0, 6, 8, 0, 0, False, 0x3650)
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        args = [str(root / 'build' / ('navigate_menu' if mode == 'step' else 'draw_menu_text')),
                *options, str(inp), str(resource), str(out), str(ports),
                'step' if mode == 'step' else '0', '0' if mode == 'step' else str(line), str(font)]
        result = subprocess.run(args, capture_output=True, text=True)
        assert result.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel and inp.read_bytes() == ram, (label, result.stdout, result.stderr)
        negatives.append({'mode': mode, 'failure': label, 'outputs_preserved': True})

    for mode in ('text', 'step'):
        for label, options in (
                ('duplicate-registers', ['--registers', '3', '0x7088', '--registers', '3', '0x7088']),
                ('missing-d3', ['--registers', '3']),
                ('missing-values', ['--registers']),
                ('overflow-d1', ['--registers', '4294967296', '0']),
                ('negative-d3', ['--registers', '3', '-1'])):
            reject(mode, options, label)
    reject('text', ['--registers', '3', '0x7088'], 'line-register-mismatch', line=0x7000)
    reject('text', ['--item', '--item'], 'duplicate-item')
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'program_code_modified': False, 'resource_sha256': resource_hash,
        'font_sha256': font_hash, 'cases': len(rows), 'negative_cases': len(negatives),
        'whole_ram_ordered_ports_full_d1_d3_equal': True, 'legacy_stdout_empty': True,
        'results': rows, 'negative_results': negatives,
        'scope': 'Returned native static full menu, direct item and navigation boundaries. '
            'Original fixed ROM and resources are unmodified. Includes hidden/visible rows, '
            'native null callback and separator rows, clipping, nested occlusion, both native '
            'menu renderers and register carry between navigation redraws. Does not establish '
            'other CPU registers, CCR, trap/fault behavior, pixels or hardware timing.'}, indent=2) + '\n')
    print('Menu text registers:', len(rows), 'native/C++ cases;', len(negatives),
          'transactional rejections;', hashlib.sha256(report.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
