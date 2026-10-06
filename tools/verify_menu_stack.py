"""Compare unmodified original a0a0 push with whole RAM and ordered video ports."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
                               UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
FIXTURE_BASE = 0x80000
PARENT = FIXTURE_BASE + 0x40
CHILD = FIXTURE_BASE + 0x100


def pack(data):
    return struct.pack('<4s7I', b'MS5D', 1, 1, FIXTURE_BASE, FIXTURE_BASE,
                       len(data), zlib.crc32(data), 0) + data


def fixture(last=b'B\0', title=b'A\0', callback=0x9488, count=6, flags=0):
    """Native data only: callbacks and the original program remain untouched."""
    data = bytearray(0x200)
    struct.pack_into('>IBBIIH', data, 0x40, FIXTURE_BASE + 0x200, 16, 8, 0, 0, 0)
    for index in range(count):
        struct.pack_into('>IIH', data, 0x50 + 10 * index,
                         FIXTURE_BASE + 0x202, callback if index % 2 else 0, index)
    struct.pack_into('>I', data, 0x50 + 10 * count, 0xffffffff)
    struct.pack_into('>IBBIIHI', data, 0x100, FIXTURE_BASE + 0x202 + len(last),
                     0, 0, 0, 0, flags, 0xffffffff)
    data.extend(b'A\0' + last + title)
    return bytes(data)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    executable = root / 'build/push_menu'
    if not executable.exists():
        raise ValueError('Build build/push_menu before verification')
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    if not native.exists():
        raise ValueError('Generate control_menu_tree.ms5d before verification')
    folder = root / 'artifacts/menu_stack'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, resource = [folder / name for name in
                               ('input.bin', 'output.bin', 'writes.bin', 'fixture.ms5d')]
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    writes, rows, rejections = [], [], []

    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)

    def make_ram(head, current, height, selected, parent=0x93e0, count=6):
        ram = bytearray(hashlib.shake_256(('menu-stack-' + str(len(rows))).encode()).digest(65536))
        struct.pack_into('>II', ram, 0x7f0e, head, current)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        if head < 0x107f0e:
            slot = head - 0x100000
            struct.pack_into('>I', ram, slot, parent)
            ram[slot + 4] = height
            ram[slot + 6] = count
            ram[slot + 7] = selected
            ram[slot + 9:slot + 13] = bytes((4, 8, 16, 8))
            ram[slot + 15] = 0
        return ram

    def invoke(ram, path, address, x, y, line):
        inp.write_bytes(ram)
        for target in (out, ports):
            target.unlink(missing_ok=True)
        return subprocess.run([str(executable), str(inp), str(path), str(out), str(ports),
                               str(address), str(x & 65535), str(y & 65535), str(line & 65535)],
                              capture_output=True, text=True)

    def compare(ram, path, address, x, y, line, label):
        cpu.mem_write(0x100000, bytes(ram))
        for reg, value in ((UC_M68K_REG_A0, address), (UC_M68K_REG_D0, x),
                           (UC_M68K_REG_D1, y), (UC_M68K_REG_D3, line)):
            cpu.reg_write(reg, value)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        try:
            cpu.emu_start(0xa0a0, 0xff000, count=3000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((label, hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original push did not return: ' + label)
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_ports = b''.join(struct.pack('>BII', *event) for event in writes)
        result = invoke(ram, path, address, x, y, line)
        if result.returncode:
            raise ValueError('C++ rejected original-returning case: ' + repr((label, result.stderr)))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        if actual != expected or actual_ports != expected_ports:
            differences = [(hex(i), expected[i], actual[i]) for i in range(min(len(actual), 65536))
                           if actual[i] != expected[i]]
            first_port = next((i // 9 for i, (a, b) in enumerate(zip(actual_ports, expected_ports))
                               if a != b), None)
            raise ValueError('C++ push mismatch: ' + repr((label, differences[:16],
                             len(expected_ports) // 9, len(actual_ports) // 9, first_port)))
        head = struct.unpack_from('>I', ram, 0x7f0e)[0]
        slot = head - 16 - 0x100000
        if (expected[slot + 5] != ram[slot + 5] or
                expected[0x7f12:0x7f1b] != ram[0x7f12:0x7f1b]):
            raise ValueError('Preserved fraction/current/renderer/input source changed: ' + label)
        if head < 0x107f0e and ram[head - 0x100000 + 4]:
            if expected[head - 0x100000 + 8] != ram[head - 0x100000 + 6] - 1:
                raise ValueError('Parent draw final row assumption changed')
        rows.append({'profile': label, 'descriptor_cpu_address': address,
                     'head': head, 'saved_current': struct.unpack_from('>I', ram, 0x7f12)[0],
                     'x': x, 'y': y, 'initial_line': line,
                     'port_events': len(writes), 'new_slot': expected[slot:slot + 16].hex(),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    xy = ((0, 0), (4, 8), (255, 255), (0x12340004, 0x56780008))
    for head, height, selected, child, position in itertools.product(
            (0x107efe, 0x107e1e), (0, 1, 2, 8), (0, 5),
            (0x93e0, 0x958a, 0x978a, 0x99ee), xy):
        currents = (0, head, 0x107efe, 0xdeadbeef)
        current = currents[len(rows) % len(currents)]
        compare(make_ram(head, current, height, selected), native, child,
                *position, 0x7000, 'native-parent-and-child')
    for child, position, current in itertools.product(
            (0x93e0, 0x958a, 0x978a, 0x99ee), xy, (0, 0x107efe, 0xdeadbeef)):
        compare(make_ram(0x107f0e, current, 0, 0), native, child,
                *position, 0x74ff, 'empty-head')

    for last, title, callback, height in itertools.product(
            (b'B\0', b'\\l\x04\x08B\0', b'\\r\x05B\0'),
            (b'A\0', b'\\nA\0', b'\\l\x20\xffA\0', b'\\r\x09A\0'),
            (0, 0x9488), (0, 2, 8)):
        data = fixture(last, title, callback)
        cpu.mem_write(FIXTURE_BASE, data)
        resource.write_bytes(pack(data))
        ram = make_ram(0x107efe, 0xdeadbeef, height, 0, PARENT)
        compare(ram, resource, CHILD, 4, 8, 0x74fe, 'synthetic-line-carry-' + last.hex() + '-' + title.hex())
    data = fixture(title=b'A\0', callback=0x12345678)
    cpu.mem_write(FIXTURE_BASE, data)
    resource.write_bytes(pack(data))
    compare(make_ram(0x107f0e, 0xdeadbeef, 0, 0), resource, PARENT,
            4, 8, 0x7000, 'empty-head-unknown-callback')

    def reject(label, ram, data=None, address=CHILD, line=0x7000):
        path = native
        if data is not None:
            resource.write_bytes(pack(data))
            path = resource
        result = invoke(ram, path, address, 4, 8, line)
        if result.returncode == 0 or out.exists() or ports.exists():
            raise ValueError('Invalid push created outputs: ' + label)
        rejections.append({'profile': label, 'exit_code': result.returncode,
                           'error': result.stderr.strip()})

    for head in (0x107e0e, 0, 0x107e0d, 0x107e0f, 0x107f0f, 0xffffffff):
        ram = make_ram(0x107f0e, 0, 0, 0)
        struct.pack_into('>I', ram, 0x7f0e, head)
        reject('full-or-invalid-head-' + hex(head), ram, address=0x93e0)
    reject('short-ram', bytes(65535), address=0x93e0)
    reject('long-ram', bytes(65537), address=0x93e0)
    reject('visible-unsupported-parent-callback', make_ram(0x107efe, 0, 8, 0, PARENT),
           fixture(callback=0x12345678))
    reject('parent-zero-count', make_ram(0x107efe, 0, 8, 0, PARENT, 0), fixture())
    reject('parent-count-mismatch', make_ram(0x107efe, 0, 8, 0, PARENT, 5), fixture())
    reject('visible-parent-flags', make_ram(0x107efe, 0, 8, 0, CHILD, 0), fixture(flags=2))
    reject('outside-new-descriptor', make_ram(0x107f0e, 0, 0, 0), address=0x80000)
    # Measurement \\n at 0x7500 enters the original trap path. The safe API rejects it;
    # this is an error policy test, not an equivalence claim for CPU exception behavior.
    reject('newline-original-trap-boundary', make_ram(0x107f0e, 0, 0, 0),
           fixture(title=b'\\nA\0'), line=0x7500)
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'entry_cpu_address': 0xa0a0, 'native_resource': 'control_menu_tree.ms5d',
        'native_resource_cpu_range': [0x937e, 0x9aa8],
        'cases': len(rows), 'whole_ram_and_ordered_video_ports_equal': True,
        'invalid_requests_create_no_outputs': True, 'results': rows, 'rejections': rejections,
        'scope': 'Unmodified original a0a0 including previous head border and inactive text. '
                 'Parent and four native child descriptors, empty/deep stack, current-pointer preservation, '
                 'slot fractional byte, renderer/input source, high-word register inputs and text line carry. '
                 'Synthetic native data replaces no program instructions. Full-stack original broken early RTS, '
                 'unsupported parent callbacks/flags, register/flag equivalence, full boot and hardware timing '
                 'remain outside scope. Original measurement trap boundary is tested as C++ rejection only.'
    }, indent=2) + '\n')
    print('Menu stack original/C++ match:', len(rows), 'cases;', len(rejections), 'rejections')


if __name__ == '__main__':
    main()
