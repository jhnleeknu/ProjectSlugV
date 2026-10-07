"""Compare immutable original 9b3e callbacks, full D1/D3, RAM and ports."""
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
                               UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import checked_resource, verify_resources

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
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    stages = root / 'extracted/runtime/stages'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    verify_resources(stages, program, source)
    folder = root / 'artifacts/menu_event_registers'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'verification.json').unlink(missing_ok=True)
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
        elif not (0x100000 <= address and address + size <= 0x110000) and not (0x1f7000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))

    def bios_hook(cpu, address, size, user):
        cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, bios_hook, begin=0xc00444, end=0xc00444)
    cpu.hook_add(UC_HOOK_CODE, bios_hook, begin=0xff000, end=0xff000)

    counts = {0x93e0: 6, 0x958a: 10, 0x978a: 10, 0x99ee: 15}
    def ram_for(index, sentinel, height, older=False, x=4, y=8, descriptor=0x93e0, renderer=0x3650):
        ram = bytearray(hashlib.shake_256(('menu-event-' + str(len(rows))).encode()).digest(65536))
        # Valid initialized allocator lists, independently random unrelated memory.
        ram[0x4d92:0x5da2] = palette_ram[0x4d92:0x5da2]
        head = 0x107ede if older else 0x107eee
        current = 0x107efe if older else head
        struct.pack_into('>II', ram, 0x7f0e, head, current)
        struct.pack_into('>I', ram, 0x7f16, renderer)
        ram[0x7dfe] = 0
        ram[0x7dff:0x7e07] = bytes(8)
        struct.pack_into('>H', ram, 0x7dfa, sentinel)
        for address in range(head, 0x107f0e, 16):
            at = address - 0x100000
            struct.pack_into('>I', ram, at, descriptor)
            ram[at + 4] = height
            ram[at + 6:at + 13] = bytes((counts[descriptor], index, index, x, y, 24, 12))
            ram[at + 15] = 0
        struct.pack_into('>H', ram, OBJECT + 0x10, 0)
        ram[OBJECT + 0x1d] = 0
        ram[OBJECT + 0x6c] = 255
        return ram

    def invoke(ram, path, event, d1, d3):
        inp.write_bytes(ram)
        return subprocess.run([str(executable), '--registers', str(d1), str(d3), str(inp), str(path), str(out), str(ports), str(event), str(d3 & 65535), str(font), str(stages), str(0x1feffc)], capture_output=True, text=True)

    def compare(ram, event, line=0x7000, label='native-parent-callback', path=native, register_inputs=None):
        d1, d3 = register_inputs if register_inputs is not None else (((len(rows)*0x1234567)^0xabcdab68)&0xffffffff, (((len(rows)*0x7341)^0xcafe)&65535)<<16|line)
        cpu.mem_write(0x100000, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_D0, event),
                           (UC_M68K_REG_D1, d1), (UC_M68K_REG_D3, d3), (UC_M68K_REG_A7, 0x1feffc)):
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
                           'external_jump': 0xc00444 if pc == 0xc00444 else 0,
                           'line': cpu.reg_read(UC_M68K_REG_D3) & 65535,
                           'd1': cpu.reg_read(UC_M68K_REG_D1) & 0xffffffff,
                           'd3': cpu.reg_read(UC_M68K_REG_D3) & 0xffffffff}
        result = invoke(ram, path, event, d1, d3)
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
                     'height': ram[current - 0x100000 + 4], 'initial_line': d3 & 65535,
                     'descriptor': struct.unpack_from('>I',ram,current-0x100000)[0], 'renderer': struct.unpack_from('>I',ram,0x7f16)[0], 'incoming_d1': d1, 'incoming_d3': d3,
                     'result': parsed, 'port_events': len(writes),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(actual), (parsed['d1'], parsed['d3'])

    for descriptor, count in counts.items():
        for index, event, sentinel, height, older, renderer in itertools.product(range(count), range(8), (0, 1), (0, 12), (False, True), (0x3650, 0x9332)):
            compare(ram_for(index, sentinel, height, older, descriptor=descriptor, renderer=renderer), event)
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

    sequences = []
    for descriptor, renderer in itertools.product(counts, (0x3650, 0x9332)):
        index = 0 if descriptor in (0x93e0, 0x99ee) else 2
        ram = ram_for(index, 0, 12, descriptor=descriptor, renderer=renderer)
        registers = (0xabcdab68, 0xdead7000)
        for event in (0, 1, 2, 5, 6, 7):
            ram, registers = compare(ram, event, label='cpp-output-carry', register_inputs=registers)
        sequences.append({'descriptor': descriptor, 'renderer': renderer, 'frames': 6, 'cpp_ram_and_register_outputs_carried': True})

    sentinel = b'prior-menu-event-output\0\xff'
    def reject(label, ram, event=3, custom_args=None):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        command = custom_args or [str(executable), '--registers', '0xabcdab68', '0xdead7000', str(inp), str(native), str(out), str(ports), str(event), '0x7000', str(font), str(stages), str(0x1feffc)]
        actual = subprocess.run(command, capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        rejections.append({'profile': label, 'outputs_preserved': True, 'original_executed': False})
    for register in (2, 3):
        for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
            command = [str(executable), '--registers', '0xabcdab68', '0xdead7000', str(inp), str(native), str(out), str(ports), '3', '0x7000', str(font), str(stages), str(0x1feffc)]
            command[register] = invalid
            reject('invalid-register', ram_for(0,0,0), custom_args=command)
    for size in (0, 65535, 65537):
        reject('invalid-ram-size', bytes(size))
    for invalid in ('-1', '65536', '0x10000', '0x', '1x', ''):
        command = [str(executable), '--registers', '0xabcdab68', '0xdead7000', str(inp), str(native), str(out), str(ports), invalid, '0x7000', str(font), str(stages), str(0x1feffc)]
        reject('invalid-event', ram_for(0, 0, 0), custom_args=command)
    command = [str(executable), '--registers', '0xabcdab68', '0xdead7000', str(inp), str(native), str(out), str(ports), '5', '0x7001', str(font), str(stages), str(0x1feffc)]
    reject('inconsistent-line-lowword', ram_for(0, 0, 0), custom_args=command)
    ram = ram_for(4, 0, 0)
    struct.pack_into('>H', ram, OBJECT + 0x10, 1)
    reject('restart-invalid-object-type', ram)
    ram = ram_for(4, 0, 0)
    ram[OBJECT + 0x6c] = 8
    reject('restart-invalid-cleanup-slot', ram)
    ram = ram_for(1, 0, 0)
    struct.pack_into('>I', ram, 0x7f0e, 0x107e0e)
    reject('full-stack-child-push', ram)
    for kind in ('same', 'hardlink', 'symlink'):
        ram = ram_for(0,0,0)
        inp.write_bytes(ram)
        ports.write_bytes(sentinel)
        alias = inp if kind == 'same' else folder / (kind + '.bin')
        if kind != 'same':
            alias.unlink(missing_ok=True)
            if kind == 'hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command = [str(executable), '--registers', '0xabcdab68', '0xdead7000', str(inp), str(native), str(alias), str(ports), '5', '0x7000', str(font), str(stages), str(0x1feffc)]
        actual = subprocess.run(command, capture_output=True, text=True)
        assert actual.returncode and inp.read_bytes() == ram and ports.read_bytes() == sentinel
        rejections.append({'profile': 'input-output-' + kind + '-alias', 'outputs_preserved': True, 'original_executed': False})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report = folder / 'verification.json'
    report.write_text(json.dumps({'source': source, 'entry_cpu_address': 0x9b3e, 'bios_boundary_cpu_address': 0xc00444, 'program_code_modified': False, 'menu_sha256': native_hash, 'font_sha256': font_hash, 'cases': len(rows), 'ordered_port_events': sum(row['port_events'] for row in rows), 'whole_ram_full_d1_d3_a2_line_external_jump_ordered_ports_equal': True, 'results': rows, 'negative_cases': len(rejections), 'rejections': rejections, 'carry_sequences': sequences, 'scope': 'Actual 9b3e dispatch over all main/debug/area/group descriptor rows and events0..7, both renderers, catalog context at native callback-entry stack. Original restart helpers include coordinate slots0..7, active parents and palette acquisition/release. BIOS boundary stops before c00444. Eight sequences carry actual CLI RAM/full-register outputs. Other CPU registers, external stack, pixels, natural reachability, hardware timing and boot are not claimed.'}, indent=2)+'\n')
    print('Menu event full-register match:', len(rows), 'cases;', len(rejections), 'negatives')

if __name__ == '__main__':
    main()
