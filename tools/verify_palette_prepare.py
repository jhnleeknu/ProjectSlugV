"""Compare resource-backed palette preparation and hardware upload bytes."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x300000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    folder = root/'artifacts/palette_prepare'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out = folder/'input.bin', folder/'output.bin'
    resource = root/'extracted/runtime/palettes.ms5p'
    rows = []
    ids = (0x3d3, 0x39d, 0x203, 0x87d, 0x87a)
    for slot in range(256):
        state = bytearray(65536)
        state[0x5da2:0x7da2] = hashlib.shake_256(bytes((slot,))).digest(8192)
        cpu.mem_write(0x100000, bytes(state))
        call(cpu, 0x3ef2)
        state = bytearray(cpu.mem_read(0x100000, 65536))
        node = 0x4d92+slot*16
        identifier = ids[slot%5]
        struct.pack_into('>HH', state, node+10, identifier, identifier)
        state[node+15] = 0x80 | (slot&2)
        # High effect bytes activate the alternate path; bit1 bypasses effects.
        if slot&2: state[(0x7dc2, 0x7dc4, 0x7dc6)[slot%3]] = 1
        else: state[0x7dc3] = 127  # low byte alone must not activate effects
        state[0x10:0x12] = bytes.fromhex('beef')
        for phase in ('dirty', 'clean'):
            cpu.mem_write(0x100000, bytes(state))
            call(cpu, 0x7196)
            expected = bytes(cpu.mem_read(0x100000, 65536))
            inp.write_bytes(state)
            subprocess.run([str(root/'build/prepare_palette'), str(inp), str(resource), str(out)], check=True)
            state = bytearray(out.read_bytes())
            if state != expected: raise ValueError('Prepare RAM mismatch '+repr((slot, phase)))
            initial_palette = bytes([0x5a])*8192
            cpu.mem_write(0x400000, initial_palette)
            call(cpu, 0x72fa)
            expected_stage = bytes(cpu.mem_read(0x105da2, 8192))
            expected_palette = bytes(cpu.mem_read(0x400000, 8192))
            inp.write_bytes(state[0x5da2:0x7da2]+initial_palette)
            subprocess.run([str(root/'build/upload_palette'), str(inp), str(out)], check=True)
            if out.read_bytes() != expected_stage+expected_palette:
                raise ValueError('Upload bytes mismatch')
            state[0x5da2:0x7da2] = expected_stage
            rows.append({'slot': slot, 'source_id': identifier, 'phase': phase,
                         'ram_sha256': hashlib.sha256(expected).hexdigest(),
                         'palette_sha256': hashlib.sha256(expected_palette).hexdigest()})
    (folder/'verification.json').write_text(json.dumps({'source': source, 'cases': len(rows),
        'all_prepare_ram_upload_bytes_equal': True,
        'scope': 'Every destination slot, five initializer-backed IDs, dirty/clean phases, normal lookup and effect-bypass flags. Preparation RAM and upload staging/palette bytes are compared; interpolation and active effects without bypass remain unsupported.',
        'results': rows}, indent=2)+'\n')
    print('Palette prepare RAM and upload bytes match:', len(rows), 'cases')


if __name__ == '__main__': main()
