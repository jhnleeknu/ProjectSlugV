"""Differential debug callback and full menu against unmodified 68000 code."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
                               UC_M68K_REG_D3, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_menu_event import SOURCE_SHA256


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    folder = root / 'artifacts/menu_debug'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports = [folder / name for name in ('input.bin', 'output.bin', 'writes.bin')]
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    font = root / 'extracted/runtime/menu_font_6b.ms5d'
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    writes, rows = [], []

    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)

    def ram_for(index, flags, older, selected, height):
        ram = bytearray(hashlib.shake_256(('debug-' + str(len(rows))).encode()).digest(65536))
        current = 0x107efe
        head = 0x107eee if older else current
        struct.pack_into('>II', ram, 0x7f0e, head, current)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        struct.pack_into('>H', ram, 0xf000, flags)
        for at in range(head - 0x100000, 0x7f0e, 16):
            struct.pack_into('>I', ram, at, 0x99ee)
            ram[at + 4] = height
            ram[at + 6:at + 13] = bytes((15, selected, index, 4, 8, 24, 17))
            ram[at + 15] = 0
        if older:
            ram[head - 0x100000 + 4] = 8
            ram[head - 0x100000 + 9:head - 0x100000 + 12] = bytes((10, 8, 8))
        return ram

    def compare(ram, event=None, clip=False):
        line = 0x7000
        cpu.mem_write(0x100000, bytes(ram))
        for reg, value in ((UC_M68K_REG_A1, 0xa008 if clip else 0x3650),
                           (UC_M68K_REG_A2, 0x107efe), (UC_M68K_REG_D0, event or 0),
                           (UC_M68K_REG_D1, 0), (UC_M68K_REG_D3, line),
                           (UC_M68K_REG_A7, 0x1feffc)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(0x9b3e if event is not None else 0x9e1a, 0xff000, count=2000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original did not return')
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        executable = 'dispatch_menu_event' if event is not None else 'draw_menu_text'
        args = [str(root / 'build' / executable), str(inp), str(native), str(out), str(ports),
                str(event if event is not None else int(clip)), str(line), str(font)]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + result.stderr)
        actual = out.read_bytes()
        expected_result = {'a2': cpu.reg_read(UC_M68K_REG_A2), 'external_jump': 0}
        parsed = json.loads(result.stdout) if event is not None else None
        if actual != expected or ports.read_bytes() != expected_ports or (parsed is not None and parsed != expected_result):
            differences = [(hex(i), expected[i], actual[i]) for i in range(min(len(actual), 65536)) if expected[i] != actual[i]]
            actual_ports = ports.read_bytes()
            mismatch = next((i for i in range(min(len(actual_ports), len(expected_ports))) if actual_ports[i] != expected_ports[i]), None)
            raise ValueError('Debug mismatch: ' + repr((event, clip, ram[0x7f06], ram[0xf000:0xf002].hex(), differences[:12], len(expected_ports)//9, len(actual_ports)//9, mismatch, expected_result, parsed)))
        rows.append({'event': event, 'clip': clip, 'index': ram[0x7f06], 'selected': ram[0x7f05],
                     'height': ram[0x7f02], 'flags': int.from_bytes(ram[0xf000:0xf002], 'big'),
                     'nested': ram[0x7f0e:0x7f12] != ram[0x7f12:0x7f16],
                     'ports': len(writes), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for index, event, flags, older, same in itertools.product(range(15), range(8),
            (0, 65535, 0xaaaa, 0x5555), (False, True), (False, True)):
        compare(ram_for(index, flags, older, index if same else (index + 1) % 15, 0), event)
    callbacks = len(rows)
    for height, selected, older, clip in itertools.product((0, 2, 8, 17), (0, 7, 14), (False, True), (False, True)):
        compare(ram_for(0, 0xaaaa, older, selected, height), clip=clip)
    full_menus = len(rows) - callbacks

    def compare_integration(ram, mode, requested=0):
        cpu.mem_write(0x100000, bytes(ram))
        for reg, value in ((UC_M68K_REG_A0, 0x93e0), (UC_M68K_REG_A1, 0x3650),
                           (UC_M68K_REG_D0, requested if mode != 'push' else 4),
                           (UC_M68K_REG_D1, 8), (UC_M68K_REG_D3, 0x7000),
                           (UC_M68K_REG_A7, 0x1feffc)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        entry = {'step': 0xa216, 'select': 0xa280, 'push': 0xa0a0}[mode]
        cpu.emu_start(entry, 0xff000, count=3000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original integration did not return: ' + mode)
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        executable = 'push_menu' if mode == 'push' else 'navigate_menu'
        tail = ['0x93e0', '4', '8', '28672'] if mode == 'push' else [mode, str(requested)]
        args = [str(root / 'build' / executable), str(inp), str(native), str(out), str(ports)] + tail + [str(font)]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ integration rejected: ' + result.stderr)
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        if actual != expected or actual_ports != expected_ports:
            differences = [(hex(i), expected[i], actual[i]) for i in range(min(len(actual), 65536)) if expected[i] != actual[i]]
            raise ValueError('Debug integration mismatch: ' + repr((mode, requested, ram[0x7f05], ram[0x7f02], differences[:12], len(expected_ports)//9, len(actual_ports)//9)))
        rows.append({'mode': mode, 'requested': requested, 'selected': ram[0x7f05],
                     'height': ram[0x7f02], 'direction': ram[0x7f0d], 'ports': len(writes),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for selected, direction, height, older in itertools.product((0, 7, 14), (0, 2), (2, 17), (False, True)):
        for mode, requested in [('step', 0)] + [('select', i) for i in (0, 7, 14, 255)]:
            ram = ram_for(selected, 0xaaaa, older, selected, height)
            ram[0x7f0d] = direction
            compare_integration(ram, mode, requested)
    navigation = len(rows) - callbacks - full_menus
    for height, selected, older in itertools.product((2, 17), (0, 7, 14), (False, True)):
        ram = ram_for(0, 0xaaaa, older, selected, height)
        # Parent redraw uses head; populate head as the native debug descriptor.
        compare_integration(ram, 'push')
    pushes = len(rows) - callbacks - full_menus - navigation
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn', 'callback_entry_cpu_address': 0x9b3e,
        'full_menu_entry_cpu_address': 0x9e1a, 'cases': len(rows), 'callback_cases': callbacks,
        'full_menu_cases': full_menus, 'navigation_cases': navigation, 'push_cases': pushes, 'whole_ram_and_ordered_ports_equal': True,
        'callback_a2_and_external_jump_equal': True, 'results': rows,
        'scope': 'Unmodified 9b3e dispatch to 9aa8 and full 9e1a debug menu. All 15 mapped bits, '
                 'events 0..7, flags 0000/ffff/aaaa/5555, head/current and selected/unselected. '
                 'Direct callbacks run even with height zero. Full draw covers height 0/2/8/17, '
                 'selection 0/7/14, nesting and ordinary glyph clipping; callback ON/OFF text stays '
                 'unclipped. Native a216/a280 navigation and a0a0 parent redraw during child push included. Whole RAM and ordered video port writes checked; hardware timing, '
                 'pixels, remaining CPU registers/flags and full boot are outside scope.'
    }, indent=2) + '\n')
    print('Debug menu original/C++ match:', callbacks, 'callbacks;', full_menus, 'full menus;', navigation, 'navigation;', pushes, 'pushes')


if __name__ == '__main__':
    main()
