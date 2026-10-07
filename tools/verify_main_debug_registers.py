"""Compare unmodified ec4 debug branch to ef2, whole RAM, full D1/D3 and ordered ports."""
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
    folder = root / 'artifacts/main_debug_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 4096)
    ports, rows, negatives = [], [], []
    calls = []

    def write(cpu, access, address, size, value, user):
        if address == 0x300001 or address in (0x2ffff0, 0x2ffff2) or 0x3c0000 <= address < 0x3c0010:
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

    def compare(ram, obj, d1, label, selected_resource=resource, d3=None, with_line=True):
        if d3 is None:
            d3 = (0, 0x12347088, 0x8000ffff, 0xffffffff)[len(rows) % 4]
        cpu.mem_write(BASE, bytes(ram))
        for register, value in ((m68k_const.UC_M68K_REG_SR, 0x2000), (m68k_const.UC_M68K_REG_A5, 0x108000),
                (m68k_const.UC_M68K_REG_A6, obj), (m68k_const.UC_M68K_REG_A7, STACK),
                (m68k_const.UC_M68K_REG_D1, d1), (m68k_const.UC_M68K_REG_D3, d3)):
            cpu.reg_write(register, value)
        ports.clear()
        calls.clear()
        cpu.emu_start(0xec4, STOP, count=1000000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == STOP
        expected = bytes(cpu.mem_read(BASE, 65536))
        final_d1 = cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 0xffffffff
        final_d3 = cpu.reg_read(m68k_const.UC_M68K_REG_D3) & 0xffffffff
        active = bool(ram[0xf000] & 1) and bool(ram[obj - BASE + 0x84])
        assert len(calls) == int(active)
        assert final_d1 >> 16 == d1 >> 16
        if not active:
            assert expected == ram and final_d1 == d1 and final_d3 == d3 and not ports
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        inp.write_bytes(ram)
        args = [str(executable), '--d3', str(d3), str(inp), str(selected_resource), str(out), str(ports_out), hex(obj), hex(d1)]
        if with_line:
            args.append(str(d3 & 65535))
        actual = subprocess.run(args, capture_output=True, text=True)
        result = {'next_pc': STOP, 'd1': final_d1, 'd3': final_d3}
        if with_line:
            result['line'] = final_d3 & 65535
        assert not actual.returncode and out.read_bytes() == expected and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (label, actual.stdout, actual.stderr, result)
        rows.append({'label': label, 'flag': ram[0xf000], 'object': obj, 'active': active, 'incoming_d1': d1, 'incoming_d3': d3, 'line_supplied': with_line,
            'result': result, 'ports': len(ports), 'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(out.read_bytes()), result

    for flag in range(256):
        for status in (0, 1, 255):
            obj = 0xffffffff if not flag & 1 else 0x100f5c
            ram = fixture(flag, status, obj)
            compare(ram, obj, ((flag * 0x1020304) ^ (status * 0x01010101)) & 0xffffffff, 'all-flags-object-status')
    for obj in (0x100000, 0x100001, 0x100002, 0x10ff7a, 0x10ff7b):
        for d1 in (0, 0xffffffff, 0xabcdab68, 0x80000f30):
            compare(fixture(1, 1, obj), obj, d1, 'object-boundary-debug-metrics')

    for active in (False, True):
        for d3 in (0x12345678, 0xffff0000, 0x8000ffff, 0xffffffff):
            compare(fixture(int(active), int(active)), 0x100f5c, 0xabcdab68, 'full-d3-only', d3=d3, with_line=False)

    unused = folder / 'unused.ms5d'
    unused.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0x100, 0x100, 1, zlib.crc32(b'X'), 0) + b'X')
    compare(fixture(0, 0, 0xffffffff), 0xffffffff, 0xabcdef12, 'bit-clear-ignores-resource-window', unused)
    compare(fixture(1, 0), 0x100f5c, 0xabcdef12, 'status-zero-ignores-resource-window', unused)

    # Complementary actual-output carry: debug ec4->ef2, then f12 through
    # input sampling/controller/caller to the next ec4 boundary, repeated.
    runtime = root / 'extracted/runtime'
    from verify_stage_catalog import checked_resource, verify_resources
    for filename, begin, end in (('input_streams.ms5d', 0xf01fe, 0xf1a0e),
            ('input_status.ms5d', 0xb58, 0xc58), ('control_menu_tree.ms5d', 0x937e, 0x9aa8),
            ('control_pause.ms5d', 0x9068, 0x9086), ('menu_fonts.ms5d', 0xe80c8, 0xe84c8)):
        checked_resource(runtime / filename, program, begin, end)
    verify_resources(runtime / 'stages', program, source)
    from pack_palettes import extract
    records, _ = extract(program)
    palette_payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] +
        records[identifier][1] for identifier in sorted(records))
    palette_bytes = (runtime / 'palettes.ms5p').read_bytes()
    assert palette_bytes == struct.pack('<4s7I', b'MS5P', 1, len(records), 68,
        len(palette_payload), zlib.crc32(palette_payload), 0, 0) + palette_payload
    palette_hash = hashlib.sha256(palette_bytes).hexdigest()
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 4096)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    input_running = False
    input_reads, prefixes, carry_rows = [], [], []
    port_addresses = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)

    def carry_code(cpu, address, size, user):
        if input_running and address == 0xf54:
            prefixes.append(cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 65535)
        if (input_running and address == 0xec4) or (not input_running and address == STOP):
            cpu.emu_stop()
        if address == 0x3a70:
            calls.append(address)
        if address == 0xff000:
            cpu.emu_stop()

    def carry_read(cpu, access, address, size, value, user):
        if input_running and address in port_addresses:
            assert len(input_reads) < 5 and address == port_addresses[len(input_reads)] and size == 1
            cpu.mem_write(address, b'\xff')
            input_reads.append(address)

    cpu.hook_add(UC_HOOK_CODE, carry_code)
    cpu.hook_add(UC_HOOK_MEM_READ, carry_read, begin=0x300000, end=0x380000)
    cpu.mem_write(BASE, bytes(65536))
    cpu.reg_write(m68k_const.UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(m68k_const.UC_M68K_REG_A7, STACK)
    cpu.mem_write(STACK, (0xff000).to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, 0xffffff, count=1000000)
    initialized = bytes(cpu.mem_read(BASE, 65536))
    for enabled in (0, 1):
        ram = bytearray(initialized)
        ram[0xf000], ram[0xf002], ram[0xfdaf] = enabled, 1, 2
        ram[0x7df1] = 1
        ram[0xfdb6:0xfdba] = b'\1\1\1\1'
        struct.pack_into('>H', ram, 0xe, 0xffff)
        struct.pack_into('>H', ram, 0xf5c+0x7e, 0xffff)
        ram[0xf5c+0x84] = 1
        ram[0x4cd2], ram[0x4cd3] = 15, 4
        struct.pack_into('>I', ram, 0x4cc4, 0xf01fe)
        struct.pack_into('>H', ram, 0x4cc2, 0x1234)
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        d1, d3 = 0x1234ab68, 0x56787088
        for frame in range(4):
            input_running = False
            ram, debug_result = compare(ram, 0x100f5c, d1, 'actual-debug-input-controller-carry', d3=d3)
            d1, d3 = debug_result['d1'], debug_result['d3']
            before = bytes(ram)
            cpu.mem_write(BASE, before)
            for reg, value in ((m68k_const.UC_M68K_REG_SR, 0x2000),
                    (m68k_const.UC_M68K_REG_A5, 0x108000), (m68k_const.UC_M68K_REG_A6, 0x100f5c),
                    (m68k_const.UC_M68K_REG_A7, STACK), (m68k_const.UC_M68K_REG_D1, d1),
                    (m68k_const.UC_M68K_REG_D3, d3)):
                cpu.reg_write(reg, value)
            ports.clear(); input_reads.clear(); prefixes.clear()
            input_running = True
            cpu.emu_start(0xf12, 0xffffff, count=12000000)
            assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == 0xec4 and len(input_reads) == 5 and len(prefixes) == 1, (enabled, frame, hex(cpu.reg_read(m68k_const.UC_M68K_REG_PC)), input_reads, prefixes)
            expected = bytes(cpu.mem_read(BASE, 65536))
            expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
            expected_result = {'next_pc': 0xec4, 'callback': 0, 'callback_context': 0,
                'style': prefixes[0], 'read_count': 5,
                'd1': cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 0xffffffff,
                'd3': cpu.reg_read(m68k_const.UC_M68K_REG_D3) & 0xffffffff}
            inp.write_bytes(before)
            args = [str(root/'build/step_input_control'), '--registers', str(d1), str(d3), str(inp),
                str(runtime/'input_streams.ms5d'), str(runtime/'input_status.ms5d'),
                str(runtime/'control_menu_tree.ms5d'), str(runtime/'control_pause.ms5d'),
                str(runtime/'palettes.ms5p'), str(out), str(ports_out), '0x100f5c', str(d1 & 65535),
                str(d3 & 65535), str(STACK), *['255']*5, str(runtime/'menu_fonts.ms5d'), str(runtime/'stages')]
            actual = subprocess.run(args, capture_output=True, text=True)
            parsed = json.loads(actual.stdout) if not actual.returncode else None
            assert not actual.returncode and out.read_bytes() == expected and ports_out.read_bytes() == expected_ports and parsed == expected_result, (enabled, frame, actual.stderr, parsed, expected_result)
            ram = bytearray(out.read_bytes())
            d1, d3 = parsed['d1'], parsed['d3']
            carry_rows.append({'debug_enabled': enabled, 'frame': frame, 'debug_result': debug_result,
                'input_controller_result': parsed, 'raw_samples': [255]*5,
                'input_port_events': len(ports), 'input_mmio_reads': len(input_reads),
                'ram_sha256': hashlib.sha256(ram).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
    input_running = False

    sentinel = b'previous-main-debug-output\0\xff'
    def reject(ram, obj, selected_resource, label, options=None, line=0x7088):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports_out.write_bytes(sentinel)
        selected_options = ['--d3', '0x12347088'] if options is None else options
        actual = subprocess.run([str(executable), *selected_options, str(inp), str(selected_resource), str(out), str(ports_out), hex(obj), '0xabcdab68', str(line)], capture_output=True, text=True)
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
    for flag, status in ((0, 0), (1, 0), (1, 1)):
        reject(fixture(flag, status), 0x100f5c, resource, 'line-d3-mismatch', line=0x7000)
    for label, options in (('duplicate-d3', ['--d3', '0x7088', '--d3', '0x7088']),
                           ('missing-d3', ['--d3']), ('negative-d3', ['--d3', '-1']),
                           ('overflow-d3', ['--d3', '4294967296'])):
        reject(fixture(0, 0), 0xffffffff, resource, label, options=options)
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
        'whole_ram_full_d1_d3_and_ordered_ports_equal': True, 'native_font_reads': 0,
        'results': rows, 'negative_results': negatives, 'carry_results': carry_rows,
        'actual_cli_debug_input_controller_carry_frames': len(carry_rows),
        'carry_palette_resource_sha256': palette_hash,
        'carry_initial_pending_activation': 1,
        'carry_scope': 'Initial debug status1 followed by native pending activation and next ec4; subsequent debug may bypass when original controller clears object status. Actual CLI RAM/D1/D3 are carried with no later host RAM injection; raw samples are five ff bytes per frame.',
        'scope': 'Original ec4 through ef2 before gate. All flag bytes and zero/nonzero object status, '
            'native debug metrics/format/pointers, high16 D1 preservation and full D3 render/bypass results. No other CPU register, '
            'gate execution, pixels or physical timing equivalence claimed.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'ports': sum(row['ports'] for row in rows),
        'input_carry_frames': len(carry_rows), 'input_carry_ports': sum(row['input_port_events'] for row in carry_rows),
        'input_carry_reads': sum(row['input_mmio_reads'] for row in carry_rows),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
