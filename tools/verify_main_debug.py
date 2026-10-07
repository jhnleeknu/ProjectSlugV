"""Compare unmodified ec4 debug branch to ef2, whole RAM, D1 and ordered ports."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ
from unicorn import m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, STOP, STACK = 0x100000, 0xef2, 0x1feffc


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    resource = root / 'extracted/runtime/main_debug.ms5d'
    executable = root / 'build/step_main_debug'
    packed = resource.read_bytes()
    payload = program[0xd56:0xe40]
    assert packed == struct.pack('<4s7I', b'MS5D', 1, 1, 0xd56, 0xd56, len(payload), zlib.crc32(payload), 0) + payload
    folder = root / 'artifacts/main_debug'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 4096)
    ports, rows, negatives = [], [], []
    calls = []

    def write(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            ports.append((size, address, value & ((1 << (8 * size)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((hex(address), size, value)))

    def code(cpu, address, size, user):
        if address == STOP:
            cpu.emu_stop()
        elif address == 0x3a70:
            calls.append(address)

    def forbid_font(cpu, access, address, size, value, user):
        raise ValueError('Debug direct renderer read font: ' + hex(address))

    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.hook_add(UC_HOOK_MEM_READ, forbid_font, begin=0xe80c8, end=0xe84c7)

    def fixture(flag, status, obj=0x100f5c):
        ram = bytearray(hashlib.shake_256(b'native-main-debug:' + len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0xf000] = flag
        if BASE <= obj and obj + 0x84 < BASE + 65536:
            ram[obj - BASE + 0x84] = status
        return ram

    def compare(ram, obj, d1, label, selected_resource=resource):
        cpu.mem_write(BASE, bytes(ram))
        for register, value in ((m68k_const.UC_M68K_REG_SR, 0x2000), (m68k_const.UC_M68K_REG_A5, 0x108000),
                (m68k_const.UC_M68K_REG_A6, obj), (m68k_const.UC_M68K_REG_A7, STACK),
                (m68k_const.UC_M68K_REG_D1, d1)):
            cpu.reg_write(register, value)
        ports.clear()
        calls.clear()
        cpu.emu_start(0xec4, STOP, count=1000000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == STOP
        expected = bytes(cpu.mem_read(BASE, 65536))
        final_d1 = cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 0xffffffff
        active = bool(ram[0xf000] & 1) and bool(ram[obj - BASE + 0x84])
        assert len(calls) == int(active)
        assert final_d1 >> 16 == d1 >> 16
        if not active:
            assert expected == ram and final_d1 == d1 and not ports
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        inp.write_bytes(ram)
        actual = subprocess.run([str(executable), str(inp), str(selected_resource), str(out), str(ports_out), hex(obj), hex(d1)], capture_output=True, text=True)
        result = {'next_pc': STOP, 'd1': final_d1}
        assert not actual.returncode and out.read_bytes() == expected and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (label, actual.stdout, actual.stderr, result)
        rows.append({'label': label, 'flag': ram[0xf000], 'object': obj, 'active': active, 'incoming_d1': d1,
            'result': result, 'ports': len(ports), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for flag in range(256):
        for status in (0, 1, 255):
            obj = 0xffffffff if not flag & 1 else 0x100f5c
            ram = fixture(flag, status, obj)
            compare(ram, obj, ((flag * 0x1020304) ^ (status * 0x01010101)) & 0xffffffff, 'all-flags-object-status')
    for obj in (0x100000, 0x100001, 0x100002, 0x10ff7a, 0x10ff7b):
        for d1 in (0, 0xffffffff, 0xabcdab68, 0x80000f30):
            compare(fixture(1, 1, obj), obj, d1, 'object-boundary-debug-metrics')

    unused = folder / 'unused.ms5d'
    unused.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0x100, 0x100, 1, zlib.crc32(b'X'), 0) + b'X')
    compare(fixture(0, 0, 0xffffffff), 0xffffffff, 0xabcdef12, 'bit-clear-ignores-resource-window', unused)
    compare(fixture(1, 0), 0x100f5c, 0xabcdef12, 'status-zero-ignores-resource-window', unused)

    sentinel = b'previous-main-debug-output\0\xff'
    def reject(ram, obj, selected_resource, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports_out.write_bytes(sentinel)
        actual = subprocess.run([str(executable), str(inp), str(selected_resource), str(out), str(ports_out), hex(obj), '0xabcdab68'], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports_out.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})
    for obj in (0xffffe, 0x10ff7c, 0xffffffff):
        reject(fixture(1, 1), obj, resource, 'invalid-used-object')
    for size in (0, 65535, 65537):
        reject(bytes(size), 0x100f5c, resource, 'invalid-ram-size')
    invalid = folder / 'invalid.ms5d'
    invalid.write_bytes(b'invalid')
    reject(fixture(1, 1), 0x100f5c, invalid, 'invalid-active-resource')
    reject(fixture(1, 1), 0x100f5c, unused, 'incorrect-active-resource-window')
    for alias_kind in ('same', 'hardlink', 'symlink'):
        ram = fixture(1, 1)
        inp.write_bytes(ram)
        ports_out.write_bytes(sentinel)
        alias = inp if alias_kind == 'same' else folder / (alias_kind + '.bin')
        if alias_kind != 'same':
            alias.unlink(missing_ok=True)
            if alias_kind == 'hardlink':
                alias.hardlink_to(inp)
            else:
                alias.symlink_to(inp)
        actual = subprocess.run([str(executable), str(inp), str(resource), str(alias), str(ports_out), '0x100f5c', '0xabcdab68'], capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram and ports_out.read_bytes() == sentinel
        negatives.append({'failure': 'input-output-' + alias_kind + '-alias', 'outputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'entry': 0xec4, 'stop': STOP, 'program_code_modified': False, 'resource_window': [0xd56, 0xe40],
        'resource_sha256': hashlib.sha256(packed).hexdigest(), 'cases': len(rows), 'negative_cases': len(negatives),
        'whole_ram_final_d1_and_ordered_ports_equal': True, 'native_font_reads': 0,
        'results': rows, 'negative_results': negatives,
        'scope': 'Original ec4 through ef2 before gate. All flag bytes and zero/nonzero object status, '
            'native debug metrics/format/pointers, high16 D1 preservation. No full CPU register, '
            'gate execution, pixels or physical timing equivalence claimed.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'ports': sum(row['ports'] for row in rows),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
