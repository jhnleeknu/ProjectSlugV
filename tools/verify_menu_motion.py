"""Verify menu opening/closing RAM and ordered port writes against a348/a2be."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A2, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
                               UC_M68K_REG_D3, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    writes = []
    def hook(cpu, access, address, size, value, user):
        if address == 0x3c0000:
            if size != 4:
                raise ValueError('Unexpected video write width')
            writes.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    folder = root / 'artifacts/menu_motion'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, video, resource = [folder / n for n in ('input.bin', 'output.bin', 'writes.bin', 'fixture.ms5d')]
    rows = []

    def original(entry):
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        cpu.emu_start(entry, 0xff000, count=8000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original routine did not return')

    def compare(ram, path, mode, label):
        cpu.mem_write(0x100000, bytes(ram))
        cpu.reg_write(UC_M68K_REG_A2, 0x107efe)
        writes.clear()
        original(0xa348 if mode == 'open' else 0xa2be)
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_video = b''.join(struct.pack('>I', value) for value in writes)
        inp.write_bytes(ram)
        subprocess.run([str(root / 'build/step_menu_motion'), mode, str(inp), str(path),
                        str(out), str(video)], check=True)
        if out.read_bytes() != expected or video.read_bytes() != expected_video:
            raise ValueError('Menu motion mismatch: ' + repr((mode, label)))
        rows.append({'mode': mode, 'label': label, 'height_before': int.from_bytes(ram[0x7f02:0x7f04], 'big'),
                     'height_after': int.from_bytes(expected[0x7f02:0x7f04], 'big'), 'writes': len(writes),
                     'writes_sha256': hashlib.sha256(expected_video).hexdigest()})
        return bytearray(expected)

    for mode, old, pair, blocked, flags in itertools.product(
            ('open', 'close'), (0, 1, 63, 64, 255, 256, 257, 0x7fff, 0xff00, 0xffff),
            ((0, 0), (1, 1), (2, 1), (8, 6), (31, 255), (255, 0), (255, 255)), (False, True), (0, 1)):
        data = struct.pack('>IBBIIHI', 0, 0, 0, 0, 0, flags, 0xffffffff)
        cpu.mem_write(0x60000, data)
        resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0x60000, 0x60000,
                                         len(data), zlib.crc32(data), 0) + data)
        ram = bytearray(hashlib.shake_256(str(len(rows)).encode()).digest(65536))
        struct.pack_into('>II', ram, 0x7f0e, 0x107eee if blocked else 0x107efe, 0x107efe)
        struct.pack_into('>I', ram, 0x7efe, 0x60000)
        struct.pack_into('>H', ram, 0x7f02, old)
        ram[0x7f04] = pair[1]
        ram[0x7f0a] = pair[0]
        ram[0x7f07:0x7f0a] = bytes((4, 255 if old & 1 else 8, 16))
        ram[0x7ef2] = 8
        ram[0x7ef7:0x7efa] = bytes((4, 0, 8))
        ram[0x7efd] = 0
        compare(ram, resource, mode, 'boundary')
    # Resource-driven initialization followed by an uninterrupted open/close cycle.
    ram = bytearray(65536)
    cpu.mem_write(0x100000, bytes(ram))
    for reg, value in ((UC_M68K_REG_A0, 0x93e0), (UC_M68K_REG_D0, 4),
                       (UC_M68K_REG_D1, 8), (UC_M68K_REG_D3, 0x7000)):
        cpu.reg_write(reg, value)
    original(0xa29c)
    expected = bytes(cpu.mem_read(0x100000, 65536))
    path = root / 'extracted/runtime/control_menu.ms5d'
    inp.write_bytes(ram)
    subprocess.run([str(root / 'build/init_menu'), str(inp), str(path), str(out),
                    str(0x93e0), '4', '8', str(0x7000)], check=True)
    if out.read_bytes() != expected:
        raise ValueError('Initial menu state mismatch')
    ram = bytearray(expected)
    struct.pack_into('>I', ram, 0x7f12, 0x107efe)
    for mode in ['open'] * 8 + ['close'] * 8:
        ram = compare(ram, path, mode, 'initialized-sequence')
    if ram[0x7f02:0x7f04] != bytes(2):
        raise ValueError('Sequence did not close fully')
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'cases': len(rows), 'all_ram_and_ordered_writes_equal': True,
        'results': rows, 'scope': 'a348/a2be helper steps plus actual-resource initialization sequence. '
                 'Does not include a370 state transitions, menu text, callbacks or pixel/timing comparison.'
    }, indent=2) + '\n')
    print('Menu motion original/C++ match:', len(rows), 'steps')


if __name__ == '__main__':
    main()
