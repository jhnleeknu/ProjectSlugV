"""Complementary carried CLI/native frame sequences: restart, BIOS and empty."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources

BASE, OBJECT, OLDEST, EMPTY, RETURN, BIOS = 0x100000, 0x8e4, 0x107efe, 0x107f0e, 0xff000, 0xc00444


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    stages = root / 'extracted/runtime/stages'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    verify_resources(stages, program, source)
    folder = root / 'artifacts/menu_frame_register_sequences'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    writes, rows, sequences = [], [], []

    def on_boundary(cpu, address, size, user):
        cpu.emu_stop()

    def on_write(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (BASE <= address and address + size <= BASE+65536 or
                  0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected original write: '+hex(address))

    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    for boundary in (RETURN, BIOS):
        cpu.hook_add(UC_HOOK_CODE, on_boundary, begin=boundary, end=boundary)

    def call(entry):
        cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(m.UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(entry, 0xffffff, count=8000000)
        assert cpu.reg_read(m.UC_M68K_REG_PC) in (RETURN, BIOS)

    for profile, renderer in itertools.product(('restart-palette', 'restart-palette-coordinate', 'bios', 'close-empty'), (0x3650, 0x9332)):
        cpu.mem_write(BASE, bytes(65536))
        cpu.reg_write(m.UC_M68K_REG_A5, 0x108000)
        call(0x3ef2)
        ram = bytearray(cpu.mem_read(BASE, 65536))
        ram[OBJECT+0x6c] = 0xff
        if profile.startswith('restart'):
            cpu.mem_write(BASE, bytes(ram))
            for identifier in (7, 263):
                cpu.reg_write(m.UC_M68K_REG_A6, BASE+OBJECT)
                cpu.reg_write(m.UC_M68K_REG_D0, identifier)
                cpu.reg_write(m.UC_M68K_REG_D1, 0)
                call(0x8ebe)
            ram = bytearray(cpu.mem_read(BASE, 65536))
            if profile.endswith('coordinate'):
                ram[OBJECT+0x6c] = 3
                at = 0xd4e6+3*0x2c
                struct.pack_into('>7I', ram, at, 0xffff0001, 0x7fffffff, 1, 0x80000001,
                                 0, 0x13579bdf, 0x24687088)
                ram[at+0x24] = 0
                ram[0xd494] = 1
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((m.UC_M68K_REG_A0, 0x93e0), (m.UC_M68K_REG_A1, 0x3650),
                           (m.UC_M68K_REG_D0, 4), (m.UC_M68K_REG_D1, 8),
                           (m.UC_M68K_REG_D3, 0x7000)):
            cpu.reg_write(reg, value)
        call(0xa29c)
        expected_init = bytes(cpu.mem_read(BASE, 65536))
        inp.write_bytes(ram)
        subprocess.run([str(root/'build/init_menu'), str(inp), str(native), str(out),
            str(0x93e0), '4', '8', str(0x7000)], capture_output=True, check=True)
        assert out.read_bytes() == expected_init
        ram = bytearray(out.read_bytes())
        # One documented start fixture change selects the original renderer.
        struct.pack_into('>I', ram, 0x7f16, renderer)
        d1, d3 = 0x1234ab68, 0x56787000
        start = len(rows)
        label = profile+'-'+hex(renderer)

        def tick(first=0, second=0):
            nonlocal ram, d1, d3
            # After initialization, these are the only host RAM injections.
            ram[0x4cba], ram[0x4cc0] = first, second
            before = bytes(ram)
            initial_d1, initial_d3 = d1, d3
            cpu.mem_write(BASE, before)
            for reg, value in ((m.UC_M68K_REG_A5, 0x108000), (m.UC_M68K_REG_A1, renderer),
                    (m.UC_M68K_REG_D0, 0x12345678), (m.UC_M68K_REG_D1, d1),
                    (m.UC_M68K_REG_D3, d3)):
                cpu.reg_write(reg, value)
            call(0xa370)
            pc = cpu.reg_read(m.UC_M68K_REG_PC)
            expected = bytes(cpu.mem_read(BASE, 65536))
            expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
            final_d0 = cpu.reg_read(m.UC_M68K_REG_D0)&0xffffffff
            expected_json = {'status': 0 if pc == BIOS else struct.unpack('>i', struct.pack('>I', final_d0))[0],
                'external_jump': BIOS if pc == BIOS else 0,
                'line': cpu.reg_read(m.UC_M68K_REG_D3)&65535,
                'd1': cpu.reg_read(m.UC_M68K_REG_D1)&0xffffffff,
                'd3': cpu.reg_read(m.UC_M68K_REG_D3)&0xffffffff}
            inp.write_bytes(before)
            out.unlink(missing_ok=True)
            ports.unlink(missing_ok=True)
            result = subprocess.run([str(root/'build/step_menu_frame'), '--registers', str(d1), str(d3),
                str(inp), str(native), str(out), str(ports), str(d3&65535), str(0x1feffc),
                str(font), str(stages)], capture_output=True, text=True)
            parsed = json.loads(result.stdout) if result.returncode == 0 else None
            if result.returncode or not out.exists() or out.read_bytes()!=expected or not ports.exists() or ports.read_bytes()!=expected_ports or parsed!=expected_json:
                raise ValueError('Carried frame mismatch: '+repr((label, len(rows)-start, first, second, expected_json, parsed, result.returncode, result.stderr)))
            ram = bytearray(out.read_bytes())
            d1, d3 = parsed['d1'], parsed['d3']
            rows.append({'sequence': label, 'frame': len(rows)-start, 'controller_injection': [first, second],
                'initial_d1': initial_d1, 'initial_d3': initial_d3, 'result': parsed,
                'head': struct.unpack_from('>I', ram, 0x7f0e)[0], 'mode': ram[0x7f1b],
                'watchdog_events': sum(write[1]==0x300001 for write in writes),
                'port_events': len(writes), 'input_sha256': hashlib.sha256(before).hexdigest(),
                'ram_sha256': hashlib.sha256(ram).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
            return parsed

        for _ in range(64):
            tick()
            head = struct.unpack_from('>I', ram, 0x7f0e)[0]-BASE
            if ram[0x7f1b]==0 and ram[head+4]>=ram[head+12]:
                break
        else: raise ValueError('Root did not finish opening')
        if profile == 'bios':
            for _ in range(5): tick(2)
            assert tick(16)['external_jump']==BIOS
        else:
            if profile.startswith('restart'):
                for _ in range(4): tick(2)
                tick(16)
                assert rows[-1]['watchdog_events']==1
            else: tick(32)
            for _ in range(64):
                if struct.unpack_from('>I', ram, 0x7f0e)[0]==EMPTY: break
                tick()
            else: raise ValueError('Root did not finish closing')
            before_empty = bytes(ram)
            empty_d1, empty_d3 = d1, d3
            result = tick()
            assert result['status']==-1 and bytes(ram)==before_empty and d1==empty_d1 and d3==empty_d3
            assert rows[-1]['port_events']==0
        sequences.append({'sequence': label, 'frames': len(rows)-start,
            'final_result': rows[-1]['result'], 'final_head': rows[-1]['head']})
    assert bytes(cpu.mem_read(0, 0x100000))==program[:0x100000]
    assert sum(row['watchdog_events'] for row in rows)==4
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn '+unicorn.__version__,
        'program_code_modified': False, 'native_entry': 0xa370, 'native_initializer': 0xa29c,
        'resource_sha256': native_hash, 'font_sha256': font_hash, 'frames': len(rows),
        'sequence_count': len(sequences), 'whole_ram_full_d1_d3_ordered_ports_equal': True,
        'actual_cli_outputs_carried': True, 'initial_d1': 0x1234ab68, 'initial_d3': 0x56787000,
        'start_fixture': 'Original palette initialization/acquisition and coordinate inputs before native/init_menu a29c. Renderer set once after initialization; initial a370 full registers are explicit fixtures.',
        'later_ram_injections': ['1004cba controller byte', '1004cc0 controller byte'],
        'sequences': sequences, 'results': rows,
        'scope': 'Complementary initialized root restart/palette/coordinate, BIOS boundary and close-to-empty lifecycles. '
            'Each next original and C++ frame receives prior actual CLI RAM/D1/D3; D1 is never reseeded after start. '
            'BIOS stops before firmware execution; status 0 is host diagnostic. No normal child-cycle matrix, '
            'other registers, stack memory, pixels, hardware timing, full controller or game-loop behavior claimed.'}, indent=2)+'\n')
    print('Menu frame register sequences:', len(rows), 'frames;', len(sequences),
        'sequences;', hashlib.sha256(report.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
