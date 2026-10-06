"""Verify full original control-menu text layout, callbacks and clipping model."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
                               UC_M68K_REG_D3, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from pack_control_menu import extract
from verify_object_reset import make_cpu


def stream(program, pointer, style):
    # The catalog currently contains only ordinary glyphs and c/p commands.
    # Refuse other commands so adding a catalog cannot silently change coverage.
    result = []
    while True:
        glyph = program[pointer]
        pointer += 1
        if glyph == 92:
            command = program[pointer]
            pointer += 1
            if command not in (ord('c'), ord('p')):
                raise ValueError('New text command requires model review')
            operand = program[pointer]
            pointer += 1
            style = ((style & 0xff00) | operand) if command == ord('c') else ((style & 255) | ((operand & 15) << 8))
            continue
        if glyph == 0:
            return result
        result.append(((style & 0xf00) << 4) | ((style & 15) << 8) | glyph)


def covered(ram, address):
    head, current = struct.unpack_from('>II', ram, 0x7f0e)
    delta = (address - 0x7000) & 65535
    x, y = (delta >> 5) & 255, delta & 31
    for pointer in range(current - 16, head - 1, -16):
        at = pointer - 0x100000
        if not ram[at + 15] & 1 and ((x - ram[at + 9]) & 255) < ram[at + 11] and ((y - ram[at + 10]) & 255) < ram[at + 4]:
            return True
    return False


def model(program, descriptor, ram, clip):
    expected = bytearray(ram)
    height, selected = ram[0x7f02], ram[0x7f05]
    x, y, width = ram[0x7f07:0x7f0a]
    head, current = struct.unpack_from('>II', ram, 0x7f0e)
    events, callbacks = [], []
    if not height:
        return expected, events, callbacks
    def glyphs(address, words):
        for word in words:
            if clip and covered(ram, address):
                continue  # a008 skips the renderer and its cursor increment.
            events.extend(((4, 0x3c0000, (address << 16) | word), (2, 0x3c0000, 0x8200)))
            address = (address + 32) & 65535
    length = len(stream(program, descriptor['title_address'], 0))
    center = (width - length) & 255
    center = center if center < 128 else center - 256
    column = (x + (center // 2)) & 255
    start = 0x7000 + ((column << 5) & 0xff00) + (((column << 5) + y) & 255)
    glyphs(start, stream(program, descriptor['title_address'], 0x103 if current == head else 0x603))
    for index, item in enumerate(descriptor['items']):
        expected[0x7f06] = index
        if index + 1 >= height:
            continue
        base = (0x7000 + ((x << 5) & 0xff00) + (((x << 5) + y) & 255) + 32) & 65535
        address = (base & 0xff00) | ((base + index + 1) & 255)
        value = 0x313 if selected == index else 0xff
        for half in range(2):
            if not covered(ram, address):  # Arrow checks a018 even with direct A1.
                tile = value + (half if selected == index else 0)
                events.append((4, 0x3c0000, (address << 16) | tile))
            address = (address + 32) & 65535
        style = 0x603 if current != head and selected != index else 3
        glyphs(address, stream(program, item['title_address'], style))
        callbacks.append((item['callback'], 5, item['argument']))
    return expected, events, callbacks


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    descriptor, _ = extract(program)
    if descriptor['flags'] != 0 or len(descriptor['items']) != 6:
        raise ValueError('Menu layout profile changed')
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    events, callbacks = [], []
    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            events.append((size, address, value & ((1 << (size * 8)) - 1)))
    def call_hook(cpu, address, size, user):
        if address == 0x9b54:
            callbacks.append((cpu.reg_read(UC_M68K_REG_A0), cpu.reg_read(UC_M68K_REG_D0) & 65535,
                              cpu.reg_read(UC_M68K_REG_D1) & 65535))
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, call_hook, begin=0x9b54, end=0x9b54)
    rows = []
    for height, selected, width, clip, nested in itertools.product(
            (0, 1, 2, 4, 8, 255), (0, 3, 5, 255), (0, 16, 255), (False, True), (False, True)):
        ram = bytearray(hashlib.shake_256(str(len(rows)).encode()).digest(65536))
        struct.pack_into('>II', ram, 0x7f0e, 0x107eee if nested else 0x107efe, 0x107efe)
        struct.pack_into('>I', ram, 0x7efe, 0x93e0)
        ram[0x7f02] = height
        ram[0x7f04] = 6
        ram[0x7f05] = selected
        ram[0x7f07:0x7f0a] = bytes((4, 8, width))
        ram[0x7ef2] = 4
        ram[0x7ef7:0x7efa] = bytes((7, 8, 4))
        ram[0x7efd] = 0
        expected, expected_events, expected_callbacks = model(program, descriptor, ram, clip)
        cpu.mem_write(0x100000, bytes(ram))
        cpu.reg_write(UC_M68K_REG_A1, 0xa008 if clip else 0x3650)
        cpu.reg_write(UC_M68K_REG_D1, 0)
        cpu.reg_write(UC_M68K_REG_D3, 0x7000)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        # a008 dispatches to the RAM-configured renderer.
        cpu.mem_write(0x107f16, (0x3650).to_bytes(4, 'big'))
        expected[0x7f16:0x7f1a] = (0x3650).to_bytes(4, 'big')
        events.clear(); callbacks.clear()
        cpu.emu_start(0x9e1a, 0xff000, count=1000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original layout did not return')
        if events != expected_events or callbacks != expected_callbacks or bytes(cpu.mem_read(0x100000, 65536)) != expected:
            raise ValueError('Layout mismatch: ' + repr((height, selected, width, clip, nested, len(events), len(expected_events))))
        rows.append({'height': height, 'selected': selected, 'width': width, 'clip': clip, 'nested': nested,
                     'port_events': len(events), 'callback_calls': len(callbacks)})
    folder = root / 'artifacts/menu_text'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'analysis.json').write_text(json.dumps({'source': source, 'cases': len(rows),
        'whole_ram_ports_callbacks_equal': True, 'results': rows,
        'scope': 'Original full9e1a/9d3a and real six callbacks against independent model for menu93e0. '
                 'No C++ full-layout implementation yet; other menus/flags/callbacks not covered.'}, indent=2) + '\n')
    print('Original menu text model matches:', len(rows), 'cases')


if __name__ == '__main__':
    main()
