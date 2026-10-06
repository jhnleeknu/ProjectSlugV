"""Compare menu border/clear writes with original9b58 and nested occlusion."""
import hashlib
import itertools
import json
from pathlib import Path
import random
import struct
import subprocess
import zlib
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_PC
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
                raise ValueError('Unexpected port width')
            writes.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    folder = root / 'artifacts/menu_border'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, resource = [folder / name for name in ('input.bin', 'writes.bin', 'fixture.ms5d')]
    rows = []

    def verify(width, height, x, y, flags, blockers, actual=False):
        descriptor = 0x93e0 if actual else 0x60000
        if actual:
            path = root / 'extracted/runtime/control_menu.ms5d'
        else:
            data = struct.pack('>IBBIIHI', 0, 0, 0, 0, 0, flags, 0xffffffff)
            cpu.mem_write(descriptor, data)
            resource.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, descriptor, descriptor,
                                             len(data), zlib.crc32(data), 0) + data)
            path = resource
        ram = bytearray(hashlib.shake_256(str(len(rows)).encode()).digest(65536))
        head = 0x107efe - 16 * len(blockers)
        struct.pack_into('>II', ram, 0x7f0e, head, 0x107efe)
        struct.pack_into('>I', ram, 0x7efe, descriptor)
        ram[0x7f02] = height
        ram[0x7f07:0x7f0a] = bytes((x, y, width))
        for index, (bx, by, bw, bh, bf) in enumerate(blockers):
            at = 0x7eee - index * 16
            ram[at + 4] = bh
            ram[at + 9:at + 12] = bytes((bx, by, bw))
            ram[at + 15] = bf
        cpu.mem_write(0x100000, bytes(ram))
        writes.clear()
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        cpu.emu_start(0x9b58, 0xff000, count=8000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original border did not return')
        if bytes(cpu.mem_read(0x100000, 65536)) != ram:
            raise ValueError('Original border changed RAM')
        expected = b''.join(struct.pack('>I', word) for word in writes)
        inp.write_bytes(ram)
        subprocess.run([str(root / 'build/trace_menu_border'), str(inp), str(path), str(out)], check=True)
        if out.read_bytes() != expected:
            raise ValueError('Border writes mismatch: ' + repr((width, height, x, y, flags, blockers)))
        rows.append({'width': width, 'height': height, 'x': x, 'y': y, 'flags': flags,
                     'blockers': blockers, 'actual_resource': actual, 'writes': len(writes),
                     'sha256': hashlib.sha256(expected).hexdigest()})

    verify(16, 8, 4, 8, 0, [], True)
    sizes = ((0, 0), (0, 1), (1, 1), (2, 2), (3, 3), (16, 8), (255, 1), (1, 255), (255, 255))
    for size, xy, flag, blocked in itertools.product(sizes, ((4, 8), (0, 0), (255, 255)), (0, 1), (False, True)):
        blockers = [(xy[0], xy[1], 8, 4, 0)] if blocked else []
        verify(*size, *xy, flag, blockers)
    rng = random.Random(0x9b58)
    for _ in range(128):
        x, y = rng.randrange(256), rng.randrange(256)
        blockers = [(rng.randrange(256), rng.randrange(256), rng.randrange(256),
                     rng.randrange(256), rng.randrange(4)) for n in range(rng.randrange(1, 4))]
        verify(rng.randrange(17), rng.randrange(13), x, y, 0, blockers)
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'cases': len(rows), 'all_ordered_writes_equal': True,
        'all_original_ram_unchanged': True, 'results': rows,
        'scope': '9b58 border/flag1 clear and a018 nested occlusion. Ordered port writes only; '
                 'no menu text, frame animation, pixel framebuffer or hardware timing comparison.'
    }, indent=2) + '\n')
    print('Menu border original/C++ writes match:', len(rows), 'cases')


if __name__ == '__main__':
    main()
