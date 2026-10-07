"""Verify unmodified a348/a2be with native descriptors and full D1/D3."""
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
from pack_control_menu_tree import catalog
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

BASE, STACK, RETURN = 0x100000, 0x1feffc, 0xff000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    resource = root / 'extracted/runtime/control_menu_tree.ms5d'
    resource_hash = checked_resource(resource, program, 0x937e, 0x9aa8)
    descriptors, ignored_edges = catalog(program)
    assert all(item['flags'] == 0 for item in descriptors)
    executable = root / 'build/step_menu_motion'
    folder = root / 'artifacts/menu_motion_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, video, report = [folder / name for name in ('input.bin', 'cpp.bin', 'cpp.writes.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 4096)
    writes, rows, negatives, sequences = [], [], [], []
    occlusion = {'covered': 0, 'visible': 0}

    def code(cpu, address, size, user):
        if address == RETURN:
            cpu.emu_stop()
        elif address == 0xa076:
            occlusion['covered'] += 1
        elif address == 0xa06c:
            occlusion['visible'] += 1

    def write(cpu, access, address, size, value, user):
        if address == 0x3c0000:
            assert size == 4
            writes.append(value & 0xffffffff)
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)

    def fixture(old, target, decrement, blocked, descriptor=None):
        ram = bytearray(hashlib.shake_256(b'motion-registers:' + len(rows).to_bytes(4, 'big')).digest(65536))
        address = descriptors[len(rows) % len(descriptors)]['source_cpu_address'] if descriptor is None else descriptor
        struct.pack_into('>II', ram, 0x7f0e, 0x107eee if blocked else 0x107efe, 0x107efe)
        struct.pack_into('>I', ram, 0x7efe, address)
        struct.pack_into('>H', ram, 0x7f02, old)
        ram[0x7f04], ram[0x7f0a] = decrement, target
        ram[0x7f07:0x7f0a] = bytes((4, 255 if old & 1 else 8, 16))
        ram[0x7ef2] = 8
        ram[0x7ef7:0x7efa] = bytes((4, 8, 8))
        ram[0x7efd] = 0
        return ram

    def compare(ram, mode, label, register_inputs=None):
        d1, d3 = register_inputs if register_inputs is not None else (
            (0xabcd0000 ^ (len(rows) * 0x1234567)) & 0xffffffff,
            (0xdeadffff ^ (len(rows) * 0x3210765)) & 0xffffffff)
        cpu.mem_write(BASE, bytes(ram))
        for register, value in ((r.UC_M68K_REG_SR, 0x2000), (r.UC_M68K_REG_A5, 0x108000),
                (r.UC_M68K_REG_A2, 0x107efe), (r.UC_M68K_REG_A7, STACK),
                (r.UC_M68K_REG_D1, d1), (r.UC_M68K_REG_D3, d3)):
            cpu.reg_write(register, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        writes.clear()
        occlusion['covered'], occlusion['visible'] = 0, 0
        cpu.emu_start(0xa348 if mode == 'open' else 0xa2be, RETURN, count=8000000)
        assert cpu.reg_read(r.UC_M68K_REG_PC) == RETURN
        expected = bytes(cpu.mem_read(BASE, 65536))
        result = {'d1': cpu.reg_read(r.UC_M68K_REG_D1) & 0xffffffff,
            'd3': cpu.reg_read(r.UC_M68K_REG_D3) & 0xffffffff}
        assert result['d1'] >> 16 == d1 >> 16 and result['d3'] >> 16 == d3 >> 16
        if mode == 'open':
            assert result['d1'] == d1
        expected_video = b''.join(struct.pack('>I', value) for value in writes)
        inp.write_bytes(ram)
        actual = subprocess.run([str(executable), '--registers', hex(d1), hex(d3), mode, str(inp),
            str(resource), str(out), str(video)], capture_output=True, text=True)
        assert not actual.returncode and out.read_bytes() == expected and video.read_bytes() == expected_video and json.loads(actual.stdout) == result, (len(rows), mode, label, actual.stdout, actual.stderr, result)
        rows.append({'mode': mode, 'label': label, 'descriptor': struct.unpack_from('>I', ram, 0x7efe)[0],
            'height_before': struct.unpack_from('>H', ram, 0x7f02)[0],
            'height_after': struct.unpack_from('>H', expected, 0x7f02)[0],
            'incoming_d1': d1, 'incoming_d3': d3, 'result': result, 'writes': len(writes),
            'native_occlusion_returns': dict(occlusion),
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'writes_sha256': hashlib.sha256(expected_video).hexdigest()})
        return bytearray(expected), (result['d1'], result['d3'])

    for mode, old, pair, blocked in itertools.product(('open', 'close'),
            (0, 1, 63, 64, 255, 256, 257, 0x7fff, 0xff00, 0xffff),
            ((0, 0), (1, 1), (2, 1), (8, 6), (31, 255), (255, 0), (255, 255)), (False, True)):
        compare(fixture(old, pair[0], pair[1], blocked), mode, 'native-descriptor-fraction-borrow-wrap-occlusion')
    for descriptor in descriptors:
        for blocked in (False, True):
            ram = fixture(0, 8, 6, blocked, descriptor['source_cpu_address'])
            register_inputs = (0xabcdab68, 0xcafe7000)
            begin = len(rows)
            for mode in ['open'] * 8 + ['close'] * 8:
                ram, register_inputs = compare(ram, mode, 'carried-open-close', register_inputs)
            assert ram[0x7f02:0x7f04] == bytes(2)
            covered = sum(row['native_occlusion_returns']['covered'] for row in rows[begin:])
            if blocked:
                assert covered > 0
            sequences.append({'native_covered_returns': covered, 'descriptor': descriptor['source_cpu_address'], 'blocked': blocked, 'frames': len(rows) - begin,
                'full_ram_d1_d3_cpp_outputs_carried': True, 'final_d1': register_inputs[0], 'final_d3': register_inputs[1]})

    sentinel = b'prior-motion-register-output\0\xff'
    def reject(mode, ram, d1, d3, selected_resource, label):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        video.write_bytes(sentinel)
        actual = subprocess.run([str(executable), '--registers', d1, d3, mode, str(inp), str(selected_resource),
            str(out), str(video)], capture_output=True, text=True)
        assert actual.returncode and out.read_bytes() == sentinel and video.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        negatives.append({'failure': label, 'mode': mode, 'outputs_preserved': True, 'original_executed': False})
    for mode in ('open', 'close'):
        for register in ('d1', 'd3'):
            for invalid in ('-1', '4294967296', '0x100000000', '0x', '1x', ''):
                d1, d3 = (invalid, '0') if register == 'd1' else ('0', invalid)
                reject(mode, fixture(256, 8, 6, False), d1, d3, resource, 'invalid-' + register)
        for size in (0, 65535, 65537):
            reject(mode, bytes(size), '0xabcdab68', '0xcafe7000', resource, 'invalid-ram-size')
        late = fixture(0xffff, 8, 255, False)
        struct.pack_into('>I', late, 0x7efe, 0x9360)
        reject(mode, late, '0xabcdab68', '0xcafe7000', resource, 'missing-descriptor-after-candidate-height-update')
        bad_slot = fixture(256, 8, 6, False)
        struct.pack_into('>I', bad_slot, 0x7f12, 0xffffffff)
        reject(mode, bad_slot, '0xabcdab68', '0xcafe7000', resource, 'invalid-current-slot')
    occlusion_counts = {kind: sum(row['native_occlusion_returns'][kind] for row in rows) for kind in occlusion}
    assert all(occlusion_counts.values())
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__, 'original_rom_unmodified': True,
        'resource_sha256': resource_hash, 'native_descriptors': [item['source_cpu_address'] for item in descriptors],
        'cases': len(rows), 'ordered_long_video_writes': sum(row['writes'] for row in rows), 'negative_cases': len(negatives),
        'all_full_ram_d1_d3_and_ordered_writes_equal': True, 'native_occlusion_return_counts': occlusion_counts, 'output_carry_sequences': sequences,
        'results': rows, 'negative_results': negatives,
        'scope': 'Native a348 opening and a2be closing with four unchanged native flag0 descriptors. '
            'Fraction boundaries, borrow/clamp/wrap, borders and occlusion; eight open-close sequences '
            'carry C++ RAM/full D1/full D3 outputs. All writes are native size4 at3c0000 and compare '
            'to packed BE32 CLI writes. Native flag1 descriptor was not present in the verified catalog '
            'and its path is excluded. Full dispatcher, callbacks, pixels and timing excluded.'}, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'negative_cases': len(negatives), 'writes': sum(row['writes'] for row in rows),
        'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
