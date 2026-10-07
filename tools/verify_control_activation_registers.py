"""Compare native request/activation D1 and preserved D3 with unmodified ROM."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import m68k_const as r
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, STACK, RETURN = 0x100000, 0x1feffc, 0xff000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    folder = root / 'artifacts/control_activation_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    state = {'stop': RETURN}
    ports, rows, negatives, sequences = [], [], [], []

    def code(cpu, address, size, user):
        if address == state['stop']:
            cpu.emu_stop()

    def write(cpu, access, address, size, value, user):
        if address == 0x300001 or address in (0x2ffff0, 0x2ffff2) or 0x3c0000 <= address < 0x3c0010:
            ports.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)

    def fixture(pending=0, configuration=0):
        ram = bytearray(hashlib.shake_256(b'activation-registers:' + len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0x7df0], ram[0x7df1] = 0, pending
        ram[0xf000], ram[0x7def] = (0, 2)[configuration & 1], (0, 255)[(configuration >> 1) & 1]
        ram[0x12], ram[0xfd82], ram[0xf002] = 2, 255, (0, 255)[(configuration >> 2) & 1]
        ram[0x4cb4], ram[0x4cb5] = (0, 2, 8, 10, 255)[configuration % 5], (0, 2, 8, 10)[configuration % 4]
        ram[0x4cb9], ram[0x4cbf] = (128, 0) if configuration & 8 else (128, 128)
        ram[0xfdb6], ram[0xfdb7] = (0, 1, 3, 255)[configuration % 4], (0, 1, 3, 255)[(configuration // 4) % 4]
        return ram

    def compare(ram, mode, d1=None, d3=None, carried=False):
        d1 = ((len(rows) * 0x1020304) ^ 0xabcdab68) & 0xffffffff if d1 is None else d1
        d3 = ((len(rows) * 0x3040102) ^ 0xdead1234) & 0xffffffff if d3 is None else d3
        cpu.mem_write(BASE, bytes(ram))
        entry = 0x9086 if mode == 'request' else 0x9136
        state['stop'] = 0xf5a if carried else RETURN
        sp = STACK - 4 if carried else STACK
        for reg, value in ((r.UC_M68K_REG_SR, 0x2000), (r.UC_M68K_REG_A5, 0x108000),
                (r.UC_M68K_REG_A6, 0x100f5c), (r.UC_M68K_REG_A7, sp), (r.UC_M68K_REG_D0, 0x12345678),
                (r.UC_M68K_REG_D1, d1), (r.UC_M68K_REG_D3, d3)):
            cpu.reg_write(reg, value)
        cpu.mem_write(sp, state['stop'].to_bytes(4, 'big'))
        cpu.mem_write(STACK + (4 if not carried else 0), RETURN.to_bytes(4, 'big'))
        ports.clear()
        cpu.emu_start(entry, state['stop'], count=100000)
        assert cpu.reg_read(r.UC_M68K_REG_PC) == state['stop'] and not ports
        expected = bytes(cpu.mem_read(BASE, 65536))
        status = cpu.reg_read(r.UC_M68K_REG_D0) & 255
        final_d1 = cpu.reg_read(r.UC_M68K_REG_D1) & 0xffffffff
        assert cpu.reg_read(r.UC_M68K_REG_D3) & 0xffffffff == d3
        inp.write_bytes(ram)
        executable = root / 'build' / ('read_control_request' if mode == 'request' else 'activate_control')
        actual = subprocess.run([str(executable), '--d1', hex(d1), str(inp), str(out)], capture_output=True, text=True)
        result = {'d1': final_d1} if mode == 'request' else {'status': status, 'd1': final_d1}
        assert not actual.returncode and out.read_bytes() == (bytes([status]) if mode == 'request' else expected) and json.loads(actual.stdout) == result, (len(rows), mode, actual.stdout, actual.stderr, result)
        if mode == 'request':
            assert expected == ram
        rows.append({'mode': mode, 'pending': ram[0x7df1], 'incoming_d1': d1, 'incoming_d3': d3,
            'final_d1': final_d1, 'd3_preserved': True, 'status': status, 'no_ports': True,
            'ram_sha256': hashlib.sha256(expected).hexdigest()})
        return bytearray(expected), result, d3

    for pending, configuration in itertools.product(range(256), range(8)):
        compare(fixture(pending, configuration), 'activation')
    for value, statuses in itertools.product(range(256), ((0, 0), (1, 1), (3, 3), (255, 255))):
        ram = fixture(configuration=value % 16)
        ram[0x4cb4], ram[0x4cb5] = value, value
        ram[0xfdb6], ram[0xfdb7] = statuses
        ram[0xf002] = 255
        compare(ram, 'request')
    for mode, replay, enabled, buttons in itertools.product((0, 1, 2, 255), (0, 255), (0, 255), ((0, 0), (128, 0), (0, 128), (128, 128))):
        ram = fixture(configuration=5)
        ram[0x12], ram[0xfd82], ram[0xf002] = mode, replay, enabled
        ram[0x4cb9], ram[0x4cbf] = buttons
        compare(ram, 'request')

    # Activation result fields, unchanged D3 and RAM feed the real f5a continuation.
    cpu.mem_write(BASE, bytes(65536))
    cpu.reg_write(r.UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(r.UC_M68K_REG_A7, STACK)
    cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
    state['stop'] = RETURN
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    allocated = bytes(cpu.mem_read(BASE, 65536))
    for pending in (0, 1, 2, 8, 255):
        ram = bytearray(allocated)
        for slot in range(256):
            at = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, at + 10, 0x203, 0x203)
            ram[at + 14], ram[at + 15] = 0, 2
        ram[0x7df1], ram[0xf000], ram[0xf5c + 0x84] = pending, 2, 1
        if pending == 0:
            ram[0x12], ram[0xfd82], ram[0xf002], ram[0x4cb4] = 2, 1, 1, 10
            ram[0xfdb6], ram[0xfdb7], ram[0x4cb9], ram[0x4cbf] = 1, 1, 128, 128
        ram, activation, unchanged_d3 = compare(ram, 'activation', 0xabcdab68, 0xdead7000, True)
        if pending == 0:
            assert activation['d1'] != 0xabcdab68
        assert cpu.reg_read(r.UC_M68K_REG_A6) == 0x100f5c and cpu.reg_read(r.UC_M68K_REG_A7) == STACK
        inp.write_bytes(ram)
        state['stop'] = 0xec4
        ports.clear()
        cpu.emu_start(0xf5a, RETURN, count=1000000)
        pc = cpu.reg_read(r.UC_M68K_REG_PC)
        assert pc in (0xec4, RETURN)
        expected = bytes(cpu.mem_read(BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        actual = subprocess.run([str(root / 'build/consume_control'), '--registers', str(activation['d1']), str(unchanged_d3), str(inp),
            str(root / 'extracted/runtime/palettes.ms5p'), str(out), str(ports_out), '0x100f5c', str(activation['status'])], capture_output=True, text=True)
        caller = {'next_pc': 0 if pc == RETURN else pc, 'd1': cpu.reg_read(r.UC_M68K_REG_D1) & 0xffffffff, 'd3': cpu.reg_read(r.UC_M68K_REG_D3) & 0xffffffff}
        assert not actual.returncode and out.read_bytes() == expected and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == caller, (actual.stdout, actual.stderr, caller)
        sequences.append({'pending': pending, 'activation_status_and_d1_cpp_output_consumed': True,
            'unchanged_input_d3_consumed': True, 'native_context_retained': True,
            'request_d1_mutation_consumed': pending == 0, 'caller': caller, 'ports': len(ports)})

    sentinel = b'prior-activation-register-output\0\xff'
    for mode in ('request', 'activation'):
        executable = root / 'build' / ('read_control_request' if mode == 'request' else 'activate_control')
        for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
            inp.write_bytes(fixture())
            out.write_bytes(sentinel)
            actual = subprocess.run([str(executable), '--d1', invalid, str(inp), str(out)], capture_output=True, text=True)
            assert actual.returncode and out.read_bytes() == sentinel
            negatives.append({'failure': 'invalid-d1', 'mode': mode, 'value': invalid, 'outputs_preserved': True})
        for size in (0, 65535, 65537):
            inp.write_bytes(bytes(size))
            out.write_bytes(sentinel)
            actual = subprocess.run([str(executable), '--d1', '0xabcdab68', str(inp), str(out)], capture_output=True, text=True)
            assert actual.returncode and out.read_bytes() == sentinel
            negatives.append({'failure': 'invalid-ram-size', 'mode': mode, 'outputs_preserved': True})
    for mode in ('request', 'activation'):
        executable = root / 'build' / ('read_control_request' if mode == 'request' else 'activate_control')
        for kind in ('same', 'hardlink', 'symlink'):
            ram = fixture()
            inp.write_bytes(ram)
            alias = inp if kind == 'same' else folder / (mode + '-' + kind + '.bin')
            if kind != 'same':
                alias.unlink(missing_ok=True)
                if kind == 'hardlink':
                    alias.hardlink_to(inp)
                else:
                    alias.symlink_to(inp)
            actual = subprocess.run([str(executable), '--d1', '0xabcdab68', str(inp), str(alias)], capture_output=True, text=True)
            assert actual.returncode and inp.read_bytes() == ram
            negatives.append({'failure': 'input-output-' + kind + '-alias', 'mode': mode, 'outputs_preserved': True})
    bad = fixture()
    bad[0x7df0] = 1
    inp.write_bytes(bad)
    out.write_bytes(sentinel)
    actual = subprocess.run([str(root / 'build/activate_control'), '--d1', '0xabcdab68', str(inp), str(out)], capture_output=True, text=True)
    assert actual.returncode and out.read_bytes() == sentinel
    negatives.append({'failure': 'active-state', 'outputs_preserved': True})
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert bytes(cpu.mem_read(0x200000, 0xffff0)) == program[0x200000:0x2ffff0]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'original_rom_unmodified': True, 'cases': len(rows), 'negative_cases': len(negatives),
        'all_full_ram_d0_byte_d1_and_preserved_d3_equal': True, 'request_activation_ports': 0,
        'results': rows, 'negative_results': negatives, 'activation_caller_sequences': sequences,
        'scope': 'Native9086 and inactive9136; D0 status byte, full D1 and unchanged full D3. '
            'Activation API returns status and D1 only; unchanged incoming D3 is carried explicitly. '
            'Five native activation-to-f5a sequences consume CLI-produced status/D1 and compare '
            'wholeRAM/registers/ordered ports. Active controller, physical timing and other CPU '
            'scratch registers excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'sequences': len(sequences),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
