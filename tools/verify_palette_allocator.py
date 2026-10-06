"""Compare dynamic palette ownership and list mutation with original routines."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_D0, UC_M68K_REG_D1
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.mem_write(0x100000, bytes(65536))
    call(cpu, 0x3ef2)
    initialized = bytes(cpu.mem_read(0x100000, 65536))
    folder = root/'artifacts/palette_allocator'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out = folder/'input.bin', folder/'output.bin'
    rows = []
    def run(state, operation, obj, identifier=0, flags=0):
        cpu.mem_write(0x100000, bytes(state))
        cpu.reg_write(UC_M68K_REG_A5, 0x108000)
        cpu.reg_write(UC_M68K_REG_A6, 0x100000+obj)
        cpu.reg_write(UC_M68K_REG_D0, identifier)
        cpu.reg_write(UC_M68K_REG_D1, flags)
        call(cpu, 0x8ebe if operation == 'acquire' else 0x8ff4)
        expected = bytes(cpu.mem_read(0x100000, 65536))
        inp.write_bytes(state)
        command = [str(root/'build/palette_allocator'), operation, str(inp), str(out), str(obj)]
        if operation == 'acquire': command += [str(identifier), str(flags)]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if out.read_bytes() != expected:
            raise ValueError('Palette RAM mismatch '+repr((operation, obj, identifier, flags)))
        allocated = expected[obj+0x1d] != state[obj+0x1d]
        if operation == 'acquire' and result.stdout.strip() != str(int(allocated)):
            raise ValueError('Palette allocation status mismatch')
        rows.append({'operation': operation, 'object': obj, 'id': identifier, 'flags': flags,
                     'allocated': allocated if operation == 'acquire' else None,
                     'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected)
    # Same low-byte bucket collisions, sharing and MRU relinking.
    for flags in (0, 1, 2, 0x7e, 0x80, 0xff):
        state = bytearray(initialized)
        for identifier in (7, 263, 7, 519):
            state = run(state, 'acquire', 0x2000, identifier, flags)
        for identifier in (263, 7, 519, 7):
            state = run(state, 'acquire', 0x2100, identifier, 0)
        state = run(state, 'release', 0x2000)
        state = run(state, 'release', 0x2100)
        state = run(state, 'release', 0x2100)
    # Reference saturation sentinel and zero-reference release.
    for count in (0, 1, 0xfffe, 0xffff):
        state = run(bytearray(initialized), 'acquire', 0x2000, 0x87a, 0)
        slot = state[0x2019]
        struct.pack_into('>H', state, 0x4d92+slot*16+8, count)
        state = run(state, 'acquire', 0x2100, 0x87a, 0)
        state = run(state, 'release', 0x2100)
        state = run(state, 'release', 0x2000)
    # Fill all 256 slots, test exhaustion, free them, then observe FIFO reuse.
    state = bytearray(initialized)
    for index in range(256):
        state = run(state, 'acquire', 0x2000+(index//4)*0x40, index*257, 1)
    for identifier in (0, 255, 0x3d3, 0xffff):
        state = run(state, 'acquire', 0x3100, identifier, 1)
    for index in range(64):
        state = run(state, 'release', 0x2000+index*0x40)
    for identifier in (0x3d3, 0x39d, 0x203):
        state = run(state, 'acquire', 0x2000, identifier, 1)
    (folder/'verification.json').write_text(json.dumps({'source': source, 'operations': len(rows),
        'all_ram_equal': True, 'scope': 'Controlled initialized lists: hash collisions, sharing, forced allocation, flag variants, saturation sentinel, exhaustion without debug UI, reverse release and FIFO reuse. No palette upload or full object lifecycle claim.',
        'results': rows}, indent=2)+'\n')
    print('Palette allocator original/C++ whole-RAM match:', len(rows), 'operations')


if __name__ == '__main__': main()
