"""Direct immutable native a0a0 versus push_menu full-register outputs."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_menu_stack import SOURCE_SHA256
from verify_stage_catalog import checked_resource, verify_resources


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    menu = root / 'extracted/runtime/control_menu_tree.ms5d'
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    stages = root / 'extracted/runtime/stages'
    menu_hash = checked_resource(menu, program, 0x937e, 0x9aa8)
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    verify_resources(stages, program, source)
    executable = root / 'build/push_menu'
    folder = root / 'artifacts/menu_stack_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows, negatives = [], [], []
    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
        elif not (0x100000 <= address and address + size <= 0x110000) and not (0x1f7000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    def stop(cpu, address, size, user):
        if address == 0xff000:
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, stop)
    descriptors = (0x93e0, 0x958a, 0x978a, 0x99ee)
    counts = {}
    for descriptor in descriptors:
        cursor = descriptor + 16
        while struct.unpack_from('>I', program, cursor)[0] != 0xffffffff:
            cursor += 10
        counts[descriptor] = (cursor - descriptor - 16) // 10
    def make_ram(parent, height, selected, renderer, empty=False):
        ram = bytearray(hashlib.shake_256(('menu-stack-registers:' + str(len(rows))).encode()).digest(65536))
        head = 0x107f0e if empty else 0x107efe
        struct.pack_into('>II', ram, 0x7f0e, head, head)
        struct.pack_into('>I', ram, 0x7f16, renderer)
        ram[0x7dfe] = 0
        ram[0x7dff:0x7e07] = bytes(8)
        if not empty:
            at = head - 0x100000
            struct.pack_into('>I', ram, at, parent)
            ram[at + 4] = height
            ram[at + 6:at + 13] = bytes((counts[parent], selected, 0, 4, 8, 24, height))
            ram[at + 15] = 0
        return ram
    def args(child, x, d1, d3):
        return [str(executable), '--registers', str(d1), str(d3), str(inp), str(menu), str(out), str(ports), str(child), str(x & 65535), str(d1 & 65535), str(d3 & 65535), str(font), str(stages), str(0x1fefd4)]
    def compare(ram, child, x, d1, d3, profile):
        cpu.mem_write(0x100000, bytes(ram))
        for register, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A0, child), (UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_A7, 0x1feffc), (UC_M68K_REG_D0, x), (UC_M68K_REG_D1, d1), (UC_M68K_REG_D3, d3)):
            cpu.reg_write(register, value)
        cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
        writes.clear()
        cpu.emu_start(0xa0a0, 0xff000, count=3000000)
        assert cpu.reg_read(UC_M68K_REG_PC) == 0xff000
        expected = bytes(cpu.mem_read(0x100000, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_d1 = cpu.reg_read(UC_M68K_REG_D1) & 0xffffffff
        expected_d3 = cpu.reg_read(UC_M68K_REG_D3) & 0xffffffff
        inp.write_bytes(ram)
        actual = subprocess.run(args(child, x, d1, d3), capture_output=True, text=True)
        assert actual.returncode == 0, (profile, child, actual.stderr)
        parsed = json.loads(actual.stdout)
        actual_ram, actual_ports = out.read_bytes(), ports.read_bytes()
        differences = [(hex(at), expected[at], actual_ram[at]) for at in range(min(len(actual_ram), 65536)) if expected[at] != actual_ram[at]]
        assert actual_ram == expected and actual_ports == expected_ports and parsed['d1'] == expected_d1 and parsed['d3'] == expected_d3, (profile, hex(child), differences[:16], len(writes), len(actual_ports)//9, hex(expected_d1), hex(expected_d3), parsed)
        if 'line' in parsed:
            assert parsed['line'] == expected_d3 & 65535
        rows.append({'profile': profile, 'child': child, 'parent': struct.unpack_from('>I', ram, struct.unpack_from('>I', ram, 0x7f0e)[0]-0x100000)[0] if struct.unpack_from('>I',ram,0x7f0e)[0] < 0x107f0e else None, 'incoming_d1': d1, 'incoming_d3': d3, 'result': parsed, 'port_events': len(writes), 'ram_sha256': hashlib.sha256(expected).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(actual_ram), parsed['d1'], parsed['d3']
    for parent, child, height, selected, renderer, position in itertools.product(descriptors, descriptors, (0, 1, 2, 12), (0, 1), (0x3650, 0x9332), ((4, 8), (255, 255))):
        ram = make_ram(parent, height, selected, renderer)
        d1 = (((len(rows)*0x7341)^0xabcd)&65535)<<16 | position[1]
        d3 = (((len(rows)*0x4321)^0xdead)&65535)<<16 | (0xffff if len(rows)&1 else 0x7000)
        compare(ram, child, position[0], d1, d3, 'native-parent-child')
    for child, renderer, high in itertools.product(descriptors, (0x3650, 0x9332), (0, 0x8000, 0xffff)):
        compare(make_ram(0x93e0, 0, 0, renderer, True), child, 255, high<<16|255, 0xdeadffff, 'empty-head')
    sequences = []
    for renderer in (0x3650, 0x9332):
        ram = make_ram(0x93e0, 0, 0, renderer, True)
        d1, d3 = 0xabcd0008, 0xdead7000
        for child in descriptors:
            ram, d1, d3 = compare(ram, child, 4, d1, d3, 'cpp-ram-register-carry')
        sequences.append({'renderer': renderer, 'frames': len(descriptors), 'cpp_outputs_carried': True, 'parents_hidden_as_configured_by_native_push': True})
    sentinel = b'prior-menu-stack-output\0\xff'
    def reject(label, ram, supplied_args=None):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        result = subprocess.run(supplied_args or args(0x93e0, 4, 0xabcd0008, 0xdead7000), capture_output=True, text=True)
        assert result.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel, (label, result.stdout, result.stderr)
        negatives.append({'profile': label, 'outputs_preserved': True, 'original_executed': False})
    for register_index in (2, 3):
        for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
            supplied = args(0x93e0, 4, 0xabcd0008, 0xdead7000)
            supplied[register_index] = invalid
            reject('invalid-register', make_ram(0x93e0, 0, 0, 0x3650, True), supplied)
    for head in (0x107e0e, 0, 0x107e0d, 0x107e0f, 0x107f0f, 0xffffffff):
        ram = make_ram(0x93e0, 0, 0, 0x3650, True)
        struct.pack_into('>I', ram, 0x7f0e, head)
        reject('invalid-head', ram)
    for size in (0, 65535, 65537):
        reject('invalid-ram-size', bytes(size))
    for at in (10, 11):
        supplied = args(0x93e0, 4, 0xabcd0008, 0xdead7000)
        supplied[at] = '1'
        reject('inconsistent-lowword', make_ram(0x93e0, 0, 0, 0x3650, True), supplied)
    supplied = args(0x1234, 4, 0xabcd0008, 0xdead7000)
    reject('unsupported-child-descriptor', make_ram(0x93e0, 12, 0, 0x3650), supplied)
    for kind in ('same', 'hardlink', 'symlink'):
        ram = make_ram(0x93e0, 0, 0, 0x3650, True)
        inp.write_bytes(ram)
        ports.write_bytes(sentinel)
        alias = inp if kind == 'same' else folder / (kind + '.bin')
        if kind != 'same':
            alias.unlink(missing_ok=True)
            if kind == 'hardlink':
                alias.hardlink_to(inp)
            else:
                alias.symlink_to(inp)
        supplied = args(0x93e0, 4, 0xabcd0008, 0xdead7000)
        supplied[6] = str(alias)
        result = subprocess.run(supplied, capture_output=True, text=True)
        assert result.returncode and inp.read_bytes() == ram and ports.read_bytes() == sentinel
        negatives.append({'profile': 'input-output-' + kind + '-alias', 'outputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'entry_cpu_address': 0xa0a0, 'program_code_modified': False, 'menu_sha256': menu_hash, 'font_sha256': font_hash, 'cases': len(rows), 'ordered_port_events': sum(row['port_events'] for row in rows), 'whole_ram_full_d1_d3_ordered_ports_equal': True, 'results': rows, 'negative_cases': len(negatives), 'negative_results': negatives, 'carry_sequences': sequences, 'scope': 'Direct a0a0, original main/debug/area/group parents and children, real catalog context at S-40, both native renderers. No other register, external stack, pixel, natural timing or boot equivalence claim.'}, indent=2)+'\n')
    print('Menu stack full-register match:', len(rows), 'cases;', len(negatives), 'negatives')

if __name__ == '__main__':
    main()
