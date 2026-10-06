"""Compare complete original 9b3e parent callbacks, RAM and ordered ports."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A2, UC_M68K_REG_A5, UC_M68K_REG_A6,
                               UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
                               UC_M68K_REG_D3, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_menu_navigation import fixture, pack, FIXTURE_BASE, FIXTURE_MENU

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
OBJECT = 0x8e4


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    executable = root / 'build/dispatch_menu_event'
    if not executable.exists():
        raise ValueError('Build build/dispatch_menu_event before verification')
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    folder = root / 'artifacts/menu_event'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, resource = [folder / name for name in
                               ('input.bin', 'output.bin', 'writes.bin', 'fixture.ms5d')]
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.mem_map(0x300000, 0x1000)
    cpu.mem_map(0xc00000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.mem_write(0x100000, bytes(65536))
    call(cpu, 0x3ef2)
    palette_ram = bytes(cpu.mem_read(0x100000, 65536))
    writes, rows, rejections = [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010 or address == 0x300001:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def bios_hook(cpu, address, size, user):
        cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, bios_hook, begin=0xc00444, end=0xc00444)

    def ram_for(index, sentinel, height, older=False, x=4, y=8):
        ram = bytearray(hashlib.shake_256(('menu-event-' + str(len(rows))).encode()).digest(65536))
        # Valid initialized allocator lists, independently random unrelated memory.
        ram[0x4d92:0x5da2] = palette_ram[0x4d92:0x5da2]
        head = 0x107ede if older else 0x107eee
        current = 0x107efe if older else head
        struct.pack_into('>II', ram, 0x7f0e, head, current)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        struct.pack_into('>H', ram, 0x7dfa, sentinel)
        for address in range(head, 0x107f0e, 16):
            at = address - 0x100000
            struct.pack_into('>I', ram, at, 0x93e0)
            ram[at + 4] = height
            ram[at + 6:at + 13] = bytes((6, index, index, x, y, 16, 8))
            ram[at + 15] = 0
        struct.pack_into('>H', ram, OBJECT + 0x10, 0)
        ram[OBJECT + 0x1d] = 0
        ram[OBJECT + 0x6c] = 255
        return ram

    def invoke(ram, path, event, line):
        inp.write_bytes(ram)
        for target in (out, ports):
            target.unlink(missing_ok=True)
        return subprocess.run([str(executable), str(inp), str(path), str(out), str(ports),
                               str(event), str(line)], capture_output=True, text=True)

    def compare(ram, event, line=0x7000, label='native-parent-callback', path=native):
        cpu.mem_write(0x100000, bytes(ram))
        for reg, value in ((UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_D0, event),
                           (UC_M68K_REG_D3, line), (UC_M68K_REG_A7, 0x1feffc)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        try:
            cpu.emu_start(0x9b3e, 0xff000, count=3000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((label, event,
                             hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (0xff000, 0xc00444):
            raise ValueError('Original event did not return or reach BIOS boundary: ' + hex(pc))
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_result = {'a2': cpu.reg_read(UC_M68K_REG_A2),
                           'external_jump': 0xc00444 if pc == 0xc00444 else 0}
        result = invoke(ram, path, event, line)
        if result.returncode:
            raise ValueError('C++ rejected original-returning case: ' + repr(
                (label, event, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        parsed = json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at])
                           for at in range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('C++ event mismatch: ' + repr((label, event,
                ram[0x7dfa:0x7dfc].hex(), differences[:16],
                len(expected_ports) // 9, len(actual_ports) // 9, expected_result, parsed,
                writes[:4])))
        current = struct.unpack_from('>I', ram, 0x7f12)[0]
        rows.append({'profile': label, 'index': ram[current - 0x100000 + 8], 'event': event,
                     'sentinel': struct.unpack_from('>H', ram, 0x7dfa)[0],
                     'head': struct.unpack_from('>I', ram, 0x7f0e)[0], 'current': current,
                     'height': ram[current - 0x100000 + 4], 'initial_line': line,
                     'result': parsed, 'port_events': len(writes),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for index, event, sentinel, height, older in itertools.product(
            range(6), tuple(range(9)) + (65535,), (0, 1, 65535), (0, 8), (False, True)):
        compare(ram_for(index, sentinel, height, older), event)
    for index, x, y, line, older in itertools.product(
            (1, 2, 3), (0, 253, 255), (0, 250, 255), (0x7000, 0x74ff), (False, True)):
        compare(ram_for(index, 0, 8, older, x, y), 3, line, 'child-push-byte-wrap')

    # Execute every helper beneath original 2a28; only input data is controlled.
    for slot, parent, current_stamp, stamp in itertools.product(
            range(8), (0, 0x100200), (0, 1, 255), (0, 1, 255)):
        ram = ram_for(4, 0, 0)
        ram[OBJECT + 0x6c] = slot
        at = 0xd4e6 + slot * 0x2c
        struct.pack_into('>5I', ram, at, 0xffff0001, 0x7fffffff, 1, 0x80000001, parent)
        ram[at + 0x24] = stamp
        ram[at + 0x25] = 0xa0
        ram[0xd494] = current_stamp
        if parent:
            struct.pack_into('>II', ram, 0x214, 0x00010001, 0x80000001)
            ram[0x225] = 0x40
        compare(ram, 3, label='restart-coordinate-cleanup')

    for identifiers in ((7,), (7, 263), (7, 263, 519, 7)):
        ram = ram_for(4, 0, 0)
        # Start from all allocator bytes produced by original initialization.
        cpu.mem_write(0x100000, palette_ram)
        cpu.reg_write(UC_M68K_REG_A6, 0x100000 + OBJECT)
        for identifier in identifiers:
            cpu.reg_write(UC_M68K_REG_D0, identifier)
            cpu.reg_write(UC_M68K_REG_D1, 0)
            call(cpu, 0x8ebe)
        acquired = bytes(cpu.mem_read(0x100000, 65536))
        for start, end in ((0x4d92, 0x5da2), (OBJECT + 0x19, OBJECT + 0x1e)):
            ram[start:end] = acquired[start:end]
        compare(ram, 3, label='restart-palette-release-' + str(len(identifiers)))

    def reject(label, ram, event=3, data=None):
        path = native
        if data is not None:
            resource.write_bytes(pack(data))
            path = resource
        result = invoke(ram, path, event, 0x7000)
        if result.returncode == 0 or out.exists() or ports.exists():
            raise ValueError('Invalid event created outputs: ' + label)
        rejections.append({'profile': label, 'exit_code': result.returncode,
                           'error': result.stderr.strip()})

    ram = ram_for(4, 0, 0)
    struct.pack_into('>H', ram, OBJECT + 0x10, 1)
    reject('restart-invalid-object-type', ram)
    ram = ram_for(4, 0, 0)
    ram[OBJECT + 0x6c] = 8
    reject('restart-invalid-cleanup-slot', ram)
    ram = ram_for(0, 0, 0)
    current = struct.unpack_from('>I', ram, 0x7f12)[0]
    struct.pack_into('>I', ram, current - 0x100000, FIXTURE_MENU)
    ram[current - 0x100000 + 6] = 1
    reject('unsupported-callback', ram, data=fixture([(FIXTURE_BASE + 8, 0x12345678, 0)]))
    ram = ram_for(1, 0, 0)
    struct.pack_into('>I', ram, 0x7f0e, 0x107e0e)
    reject('full-stack-child-push', ram)
    reject('short-ram', bytes(65535))
    reject('long-ram', bytes(65537))
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'entry_cpu_address': 0x9b3e, 'bios_boundary_cpu_address': 0xc00444,
        'cases': len(rows), 'whole_ram_and_ordered_ports_equal': True,
        'result_a2_and_external_jump_equal': True, 'invalid_requests_create_no_outputs': True,
        'results': rows, 'rejections': rejections,
        'scope': 'All six native parent callbacks execute unmodified through 9b3e, '
                 'including original object restart 2a28 and its helper routines. '
                 'Six item indices, events 0..8/ffff, sentinel 0/1/ffff, hidden/visible rows, '
                 'current at head/older slot, child coordinate byte wrapping, coordinate '
                 'cleanup slots 0..7 and palette release covered. BIOS jump stops before '
                 'executing c00444. Whole RAM, ordered video/watchdog ports, A2 and external '
                 'jump compared; other register/flag effects, BIOS behavior, full boot '
                 'and hardware timing remain outside scope. Rejections are transactional '
                 'API policy checks, not equivalence claims for original traps.'
    }, indent=2) + '\n')
    print('Menu event original/C++ match:', len(rows), 'cases;', len(rejections), 'rejections')


if __name__ == '__main__':
    main()
