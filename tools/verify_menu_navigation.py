"""Compare complete a216/a280 navigation execution with the C++ resource API."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from pack_control_menu import extract
from verify_object_reset import make_cpu


SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
FIXTURE_BASE = 0x80000
FIXTURE_MENU = FIXTURE_BASE + 0x40
CALLBACKS = (0x9488, 0x94d6, 0x949a, 0x94b8, 0x950c, 0x9532)


def fixture(items, flags=0):
    """Construct native descriptors and strings; leave all original code intact."""
    data = bytearray(b'FIXTURE\0ONE\0TWO\0THREE\0')
    data.extend(bytes(0x40 - len(data)))
    data.extend(struct.pack('>IBBIIH', FIXTURE_BASE, 16, 8, 0, 0, flags))
    for title, callback, argument in items:
        data.extend(struct.pack('>IIH', title, callback, argument))
    data.extend(struct.pack('>I', 0xffffffff))
    return bytes(data)


def pack(data):
    return struct.pack('<4s7I', b'MS5D', 1, 1, FIXTURE_BASE, FIXTURE_BASE,
                       len(data), zlib.crc32(data), 0) + data


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    descriptor, _ = extract(program)
    if descriptor['flags'] != 0 or len(descriptor['items']) != 6:
        raise ValueError('Menu 93e0 profile changed')
    executable = root / 'build/navigate_menu'
    if not executable.exists():
        raise ValueError('Build build/navigate_menu before running verification')
    folder = root / 'artifacts/menu_navigation'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, resource = [folder / name for name in
                               ('input.bin', 'output.bin', 'writes.bin', 'fixture.ms5d')]
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    writes, callbacks, rows, rejections = [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def call_hook(cpu, address, size, user):
        callbacks.append((cpu.reg_read(UC_M68K_REG_A0),
                          cpu.reg_read(UC_M68K_REG_D0) & 65535,
                          cpu.reg_read(UC_M68K_REG_D1) & 65535))

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, call_hook, begin=0x9b54, end=0x9b54)

    def ram_for(menu, count, old, direction, height, nested, seed):
        ram = bytearray(hashlib.shake_256(seed.encode()).digest(65536))
        struct.pack_into('>II', ram, 0x7f0e, 0x107eee if nested else 0x107efe, 0x107efe)
        struct.pack_into('>I', ram, 0x7efe, menu)
        ram[0x7f02] = height
        ram[0x7f04] = count
        ram[0x7f05] = old
        ram[0x7f07:0x7f0a] = bytes((4, 8, 16))
        ram[0x7f0d] = direction
        ram[0x7ef2] = 8
        ram[0x7ef7:0x7efa] = bytes((7, 8, 4))
        ram[0x7efd] = 0
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        return ram

    def compare(ram, path, mode, requested, label):
        cpu.mem_write(0x100000, bytes(ram))
        cpu.reg_write(UC_M68K_REG_D0, requested)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        callbacks.clear()
        entry = 0xa216 if mode == 'step' else 0xa280
        cpu.emu_start(entry, 0xff000, count=1000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original navigation did not return: ' + repr(label))
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        inp.write_bytes(ram)
        result = subprocess.run([str(executable), str(inp), str(path), str(out), str(ports),
                                 mode, str(requested)], capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError('C++ rejected original-returning case: ' + repr(
                (label, mode, requested, ram[0x7f05], ram[0x7f0d], ram[0x7f02],
                 result.stderr.strip())))
        actual = out.read_bytes()
        if actual != expected or ports.read_bytes() != expected_ports:
            differences = [(hex(at), expected[at], actual[at])
                           for at in range(min(len(actual), len(expected))) if actual[at] != expected[at]]
            raise ValueError('C++ navigation mismatch: ' + repr((label, mode, requested,
                             differences[:16], len(writes), len(ports.read_bytes()) // 9)))
        rows.append({'profile': label, 'mode': mode, 'requested': requested,
                     'old': ram[0x7f05], 'direction_flags': ram[0x7f0d],
                     'height': ram[0x7f02], 'nested': ram[0x7f0e:0x7f12] != ram[0x7f12:0x7f16],
                     'width': ram[0x7f09],
                     'selected': expected[0x7f05], 'port_events': len(writes),
                     'separator_cells': sum(size == 4 and address == 0x3c0000 and
                         (value & 65535) in (0x0bf8, 0x0bf9, 0x0bfa)
                         for size, address, value in writes),
                     'callbacks': callbacks.copy(),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    actions = [('step', 0)] + [('select', index) for index in (0, 3, 5, 6, 255)]
    actual_resource = root / 'extracted/runtime/control_menu.ms5d'
    for old, direction, height, nested, action in itertools.product(
            range(6), (0, 2), (0, 2, 8), (False, True), actions):
        ram = ram_for(0x93e0, 6, old, direction, height, nested, 'actual-' + str(len(rows)))
        compare(ram, actual_resource, action[0], action[1], 'actual-93e0')

    profiles = [
        ('disabled-and-separator', [(FIXTURE_BASE + 8, CALLBACKS[0], 0),
          (FIXTURE_BASE + 12, 0, 1), (0xfffffffe, CALLBACKS[1], 65535),
          (FIXTURE_BASE + 16, CALLBACKS[2], 32768), (0, CALLBACKS[3], 42)]),
        ('one-selectable', [(FIXTURE_BASE + 8, 0, 65535),
          (0xfffffffe, CALLBACKS[4], 32768), (0, CALLBACKS[5], 65535),
          (FIXTURE_BASE + 12, 0, 0)]),
        ('callback-arguments', [(FIXTURE_BASE + 8, callback, argument)
          for callback, argument in zip(CALLBACKS, (0, 1, 255, 256, 32768, 65535))])]
    for label, items in profiles:
        for flags in (0,):
            data = fixture(items, flags)
            cpu.mem_write(FIXTURE_BASE, data)
            resource.write_bytes(pack(data))
            # Include old disabled and separator rows when redrawing the previous selection.
            old_indices = range(len(items))
            for old, direction, height, nested, action in itertools.product(
                    old_indices, (0, 2, 255), (0, 2, 8), (False, True), actions):
                ram = ram_for(FIXTURE_MENU, len(items), old, direction, height, nested,
                              'synthetic-' + str(len(rows)))
                compare(ram, resource, action[0], action[1], label + '-flags-' + str(flags))

    separator_items = [(FIXTURE_BASE + 8, CALLBACKS[0], 0),
                       (0xfffffffe, CALLBACKS[1], 65535),
                       (FIXTURE_BASE + 12, CALLBACKS[2], 32768)]
    data = fixture(separator_items)
    cpu.mem_write(FIXTURE_BASE, data)
    resource.write_bytes(pack(data))
    # The old separator is at column 5, row 10. A one-cell parent can cover
    # its first cell or the next cell, exposing 9cd4's stalled cursor branch.
    for width, occlusion, direction, action in itertools.product(
            (0, 1, 2, 3, 4, 255), ('none', 'first-cell', 'second-cell'),
            (0, 2, 255), actions):
        ram = ram_for(FIXTURE_MENU, 3, 1, direction, 8,
                      occlusion != 'none', 'separator-boundary-' + str(len(rows)))
        ram[0x7f09] = width
        if occlusion != 'none':
            ram[0x7ef2] = 1
            ram[0x7ef7:0x7efa] = bytes((5 if occlusion == 'first-cell' else 6, 10, 1))
        compare(ram, resource, action[0], action[1], 'separator-width-' +
                str(width) + '-occlusion-' + occlusion)
        cells = 0 if width < 2 else 256 if width == 2 else width - 2
        if occlusion == 'first-cell':
            cells = 0
        elif occlusion == 'second-cell':
            cells = min(1, cells)
        if rows[-1]['separator_cells'] != cells:
            raise ValueError('Original separator coverage differed: ' + repr(
                (rows[-1]['profile'], rows[-1]['separator_cells'], cells)))

    boundary_items = [(FIXTURE_BASE + 8, CALLBACKS[0] if index in (0, 127, 254) else 0,
                       index) for index in range(255)]
    for count, items, old_indices, heights in (
            (255, boundary_items, (0, 254), (0, 255)),
            (1, [(0, CALLBACKS[5], 65535)], (0,), (0, 2, 255))):
        data = fixture(items)
        cpu.mem_write(FIXTURE_BASE, data)
        resource.write_bytes(pack(data))
        boundary_actions = [('step', 0), ('select', 254), ('select', 255)]
        for old, direction, height, action in itertools.product(
                old_indices, (0, 2), heights, boundary_actions):
            ram = ram_for(FIXTURE_MENU, count, old, direction, height, False,
                          'boundary-' + str(len(rows)))
            compare(ram, resource, action[0], action[1], 'count-' + str(count))

    # Hidden rows return before inspecting descriptor flags in original 9d3a.
    for flags in (2, 14, 65535):
        data = fixture([(FIXTURE_BASE + 8, CALLBACKS[0], 0)], flags)
        cpu.mem_write(FIXTURE_BASE, data)
        resource.write_bytes(pack(data))
        for direction, nested, action in itertools.product((0, 2, 255), (False, True), actions):
            ram = ram_for(FIXTURE_MENU, 1, 0, direction, 0, nested,
                          'hidden-flags-' + str(len(rows)))
            compare(ram, resource, action[0], action[1], 'hidden-flags-' + str(flags))

    def reject(label, data, count, old=0):
        resource.write_bytes(pack(data))
        ram = ram_for(FIXTURE_MENU, count, old, 0, 8, False, label)
        inp.write_bytes(ram)
        for mode in ('step', 'select'):
            for target in (out, ports):
                target.unlink(missing_ok=True)
            result = subprocess.run([str(executable), str(inp), str(resource), str(out), str(ports),
                                     mode, '255'], capture_output=True, text=True)
            if result.returncode == 0 or out.exists() or ports.exists():
                raise ValueError('Invalid navigation created outputs: ' + label + '-' + mode)
            rejections.append({'profile': label, 'mode': mode, 'exit_code': result.returncode,
                               'error': result.stderr.strip()})

    valid = fixture([(FIXTURE_BASE + 8, CALLBACKS[0], 0)])
    reject('visible-nonzero-flags', fixture([(FIXTURE_BASE + 8, CALLBACKS[0], 0)], 2), 1)
    reject('zero-count', valid, 0)
    reject('count-mismatch', valid, 2)
    reject('old-out-of-range', valid, 1, 1)
    reject('zero-items', fixture([]), 0)
    reject('no-selectable-cycle', fixture([(FIXTURE_BASE + 8, 0, 0),
                                         (0xfffffffe, CALLBACKS[0], 0)]), 2)
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'entry_cpu_addresses': {'step': 0xa216, 'select': 0xa280},
        'synthetic_resource_cpu_address': FIXTURE_BASE,
        'synthetic_descriptor_cpu_address': FIXTURE_MENU,
        'cases': len(rows), 'actual_resource_cases': sum(row['profile'] == 'actual-93e0' for row in rows),
        'whole_ram_and_ordered_video_ports_equal': True,
        'invalid_requests_create_no_outputs': True,
        'results': rows, 'rejections': rejections,
        'scope': 'Full original routines and event-5 callbacks execute unmodified. '
                 'Only synthetic descriptor/string data are installed at CPU 0x80000. '
                 'Descriptor flags zero, zero titles, disabled callbacks, separators skipped during navigation '
                 'and visible old separator redraws are covered. Separator widths 0/1/2/3/4/255 '
                 'are compared with no parent cover and parent cover at the first or second cell. '
                 'Byte index clamping/wrap, clipping and callback arguments are covered. '
                 'Hidden rows bypass nonzero descriptor flags; visible nonzero flags are rejected. '
                 'Unsupported callbacks, CPU register/flag equivalence, '
                 'hardware timing and full boot are outside scope.'
    }, indent=2) + '\n')
    print('Menu navigation original/C++ match:', len(rows), 'cases;', len(rejections), 'rejections')


if __name__ == '__main__':
    main()
