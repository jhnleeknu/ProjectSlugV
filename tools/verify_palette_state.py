"""Check palette initialization and trace original palette allocation/release."""
import hashlib
import json
from pathlib import Path
import subprocess
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def call(cpu, entry):
    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
    cpu.emu_start(entry, 0xff000, count=20000)
    if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
        raise ValueError('Original routine did not return')


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM revision')
    directory = root/'artifacts/palette_state'
    directory.mkdir(parents=True, exist_ok=True)
    cases = [bytes([v])*65536 for v in (0, 0xff, 0xa5, 0x5a)]
    cases += [hashlib.shake_256(b'palette-state-v1'+bytes([i])).digest(65536) for i in range(16)]
    input_path, output_path = directory/'input.bin', directory/'cpp.bin'
    input_path.write_bytes(b''.join(cases))
    subprocess.run([str(root/'build/init_palette'), str(input_path), str(output_path)], check=True)
    cpu = make_cpu(program)
    expected = []
    for data in cases:
        cpu.mem_write(0x100000, data)
        call(cpu, 0x3ef2)
        expected.append(bytes(cpu.mem_read(0x100000, 65536)))
    expected = b''.join(expected)
    (directory/'m68k.bin').write_bytes(expected)
    actual = output_path.read_bytes()
    if actual != expected:
        raise ValueError('C++ palette initialization differs from original')
    # Controlled original-only observation: same ID shares a slot; flag bit0 forces allocation.
    cpu.mem_write(0x100000, bytes(65536))
    call(cpu, 0x3ef2)
    cpu.reg_write(UC_M68K_REG_A6, 0x100820)
    trace = []
    for palette_id, flags in ((7, 0), (7, 0), (7, 1), (263, 0)):
        cpu.reg_write(UC_M68K_REG_D0, palette_id)
        cpu.reg_write(UC_M68K_REG_D1, flags)
        call(cpu, 0x8ebe)
        obj = bytes(cpu.mem_read(0x100820, 0xc4))
        slot = obj[0x14]
        node = bytes(cpu.mem_read(0x104d92 + slot*16, 16))
        trace.append({'requested_id': palette_id, 'flags': flags, 'slot': slot,
                      'object_slot_count': obj[0x1d], 'reference_count': int.from_bytes(node[8:10], 'big'),
                      'node_hex': node.hex()})
    if [t['slot'] for t in trace] != [0, 0, 1, 2] or [t['reference_count'] for t in trace] != [1, 2, 1, 1]:
        raise ValueError('Allocation observation changed')
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    call(cpu, 0x8ff4)
    released = bytes(cpu.mem_read(0x104d92, 48))
    if bytes(cpu.mem_read(0x10083d, 1)) != b'\x00':
        raise ValueError('Release did not clear object palette count')
    for offset in (0, 16, 32):
        if released[offset+8:offset+14] != bytes.fromhex('0000ffffffff') or released[offset+15] != 2:
            raise ValueError('Release did not free acquired palette node')
    report = {'source_program_sha256': source['sha256'], 'init_entry': 0x3ef2,
              'cases': len(cases), 'bytes_per_case': 65536, 'all_bytes_equal': True,
              'output_sha256': hashlib.sha256(actual).hexdigest(), 'allocation_trace': trace,
              'release_entry': 0x8ff4, 'release_cleared_references': True,
              'scope': 'C++ initialization persistent RAM only. Allocation/release observations are original-only, not reconstructed equivalence.'}
    (directory/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
