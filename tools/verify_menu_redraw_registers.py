"""Compare unmodified native stack redraw RAM, ports and full D1/D3."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A2, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import (COUNTS, SOURCE_SHA256, checked_resource,
                                  verify_resources)

RAM_BASE = 0x100000
OLDEST = 0x107efe
EMPTY = 0x107f0e
ENTRY = 0xa6da
MENUS = (0x93e0, 0x958a, 0x978a, 0x99ee)
ITEM_COUNTS = (6, 10, 10, 15)
CALLBACKS = (0x9602, 0x9802)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    stages = root / 'extracted/runtime/stages'
    groups = verify_resources(stages, program, source)
    null_hash = checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    for menu, count in zip(MENUS, ITEM_COUNTS):
        if (struct.unpack_from('>H', program, menu + 14)[0] != 0 or
                struct.unpack_from('>I', program, menu + 16 + count * 10)[0] != 0xffffffff):
            raise ValueError('Native descriptor flags/count changed: ' + hex(menu))
    executable = root / 'build/redraw_menu_stack'
    if not executable.exists():
        raise ValueError('Build build/redraw_menu_stack before verification')
    folder = root / 'artifacts/menu_redraw_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
                             ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, calls, draw_order, rows, negatives = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        if address in CALLBACKS:
            calls.append((address, cpu.reg_read(UC_M68K_REG_A7)))
        elif address in (0x9b58, 0x9e1a):
            current = int.from_bytes(cpu.mem_read(0x107f12, 4), 'big')
            draw_order.append((address, current))

    def return_hook(cpu, address, size, user):
        cpu.emu_stop()

    cpu.hook_add(UC_HOOK_CODE, return_hook, begin=0xff000, end=0xff000)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in CALLBACKS + (0x9b58, 0x9e1a):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def compare(menus, height, selected_mode, width, cutoff, geometry=0,
                boundary=0, line=0x7000, stack=0x1feffc, slot_flags=0, profile='native-matrix',
                d1=None, d3=None, renderer=None, input_ram=None):
        if d1 is None:
            d1 = (0x1234ab68, 0xffff0f03, 0xdeadbeef)[len(rows) % 3]
        if d3 is None:
            d3 = (0x56780000, 0xffff0000, 0)[len(rows) % 3] | line
        if renderer is None:
            renderer = (0x3650, 0x9332)[len(rows) % 2]
        assert d3 & 65535 == line
        depth = len(menus)
        heights = (height,) * depth if isinstance(height, int) else height
        if len(heights) != depth:
            raise ValueError('One visible height required per slot')
        head = OLDEST - 16 * (depth - 1)
        last_slot = EMPTY if cutoff == -1 else OLDEST - 16 * cutoff
        ram = bytearray(hashlib.shake_256(
            b'ms5-stack-redraw-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        saved_current = (0, head, OLDEST, 0xdeadbeef)[len(rows) % 4]
        struct.pack_into('>III', ram, 0x7f0e, head, saved_current, renderer)
        ram[0x7dfe] = len(rows) % 8
        for group in range(8):
            ram[0x7dff + group] = (0, COUNTS[group] - 1, 255)[boundary]
        struct.pack_into('>H', ram, 0xf000, (0, 0xaaaa, 0xffff)[geometry % 3])
        expected_calls = []
        expected_order = []
        for index, menu in enumerate(menus):
            slot = OLDEST - 16 * index
            offset = slot - RAM_BASE
            count = ITEM_COUNTS[MENUS.index(menu)]
            selected = (0, count // 2, count - 1)[selected_mode]
            xy = ((4, 8), (4 + index * 2, 8 + index), (253, 250), (255, 255))[geometry]
            struct.pack_into('>I', ram, offset, menu)
            ram[offset + 4] = heights[index]
            ram[offset + 6:offset + 13] = bytes((count, selected, 0, *xy, width, 17))
            ram[offset + 15] = slot_flags if index > 0 else 0
            if cutoff != -1 and index <= cutoff:
                expected_order.extend(((0x9b58, slot), (0x9e1a, slot)))
                first = 2 if menu == 0x958a else 0
                if menu in (0x958a, 0x978a):
                    callback = CALLBACKS[(0x958a, 0x978a).index(menu)]
                    expected_calls.extend((callback, stack - 28)
                                          for row in range(first, count) if row + 1 < heights[index])
        if input_ram is not None:
            ram = bytearray(input_ram)
            saved_current = struct.unpack_from('>I', ram, 0x7f12)[0]
            assert struct.unpack_from('>I', ram, 0x7f16)[0] == renderer
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_A2, last_slot), (UC_M68K_REG_D1, d1),
                           (UC_M68K_REG_D3, d3),
                           (UC_M68K_REG_A7, stack)):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        calls.clear()
        draw_order.clear()
        try:
            cpu.emu_start(ENTRY, 0xffffff, count=8000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((profile, menus, height, width,
                             hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if (cpu.reg_read(UC_M68K_REG_PC) != 0xff000 or
                cpu.reg_read(UC_M68K_REG_A2) != last_slot):
            raise ValueError('Original redraw did not return with preserved A2')
        if draw_order != expected_order or calls != expected_calls:
            raise ValueError('Original actual draw/callback coverage changed: ' +
                             repr((menus, height, cutoff, expected_order, draw_order,
                                   expected_calls, calls)))
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_current = saved_current if cutoff == -1 else last_slot
        if int.from_bytes(expected[0x7f12:0x7f16], 'big') != expected_current:
            raise ValueError('Original final current slot changed')
        if cutoff == -1 and (expected != ram or writes):
            raise ValueError('Original empty redraw changed RAM/video ports')
        if profile == 'native-matrix' and height > 0 and not writes:
            raise ValueError('Nonempty redraw produced no actual video writes')
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_result = {'line': cpu.reg_read(UC_M68K_REG_D3) & 65535,
                           'd1': cpu.reg_read(UC_M68K_REG_D1) & 0xffffffff,
                           'd3': cpu.reg_read(UC_M68K_REG_D3) & 0xffffffff}
        if cutoff == -1:
            assert expected_result['d1'] == d1 and expected_result['d3'] == d3
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), '--registers', str(d1), str(d3), str(inp), str(native), str(out), str(ports),
                                 str(last_slot), str(line), str(font), str(stages),
                                 str(stack - 28)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((profile, menus, height, width,
                                                    cutoff, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        parsed = json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at])
                           for at in range(min(len(actual), 65536)) if actual[at] != expected[at]]
            port_difference = next((at for at in range(min(len(actual_ports), len(expected_ports)))
                                    if actual_ports[at] != expected_ports[at]), None)
            raise ValueError('Redraw mismatch: ' + repr((profile, menus, height, selected_mode,
                width, cutoff, geometry, boundary, line, stack, differences[:16],
                len(expected_ports) // 9, len(actual_ports) // 9, port_difference,
                expected_result, parsed)))
        rows.append({'profile': profile, 'menus_oldest_to_newest': list(menus),
                     'depth': depth, 'head': head, 'last_slot': last_slot,
                     'visible_heights_oldest_to_newest': list(heights), 'target_height': 17,
                     'newer_slot_flags': slot_flags,
                     'selected_mode': selected_mode, 'width': width, 'geometry': geometry,
                     'area_boundary_mode': boundary, 'initial_current': saved_current,
                     'final_current': expected_current, 'initial_line': line, 'initial_d1': d1, 'initial_d3': d3,
                     'renderer_cpu_address': renderer, 'entry_stack': stack,
                     'callback_entry_stack': stack - 28, 'callback_calls': len(calls),
                     'callback_cpu_addresses': [address for address, _ in calls],
                     'draw_order': draw_order.copy(), 'result': parsed, 'port_events': len(writes),
                     'input_sha256': hashlib.sha256(ram).hexdigest(),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return actual, parsed

    for depth, rotation, height, selected, width in itertools.product(
            (2, 3, 4), range(4), (0, 2, 5, 12), range(3), (2, 3, 24)):
        menus = tuple(MENUS[(rotation + index) % 4] for index in range(depth))
        compare(menus, height, selected, width, depth - 1,
                geometry=(rotation + selected) % 2)
    native_cases = len(rows)
    for menus in itertools.product(MENUS, repeat=2):
        for cutoff, geometry, boundary in itertools.product((0, 1), (2, 3), (1, 2)):
            compare(menus, 12, 2, 24, cutoff, geometry, boundary,
                    (0, 0x74ff, 0xffff)[len(rows) % 3],
                    (0x1feffc, 0x1f8000)[len(rows) % 2], profile='partial-coordinate-style-area')
    for rotation, depth, cutoff in itertools.product(range(4), (3, 4), (0, 1, 2)):
        menus = tuple(MENUS[(rotation + index) % 4] for index in range(depth))
        compare(menus, 5, 1, 2, cutoff, 1, 2, profile='partial-newer-head-clipping')
    for depth, rotation in itertools.product((2, 3, 4), range(4)):
        menus = tuple(MENUS[(rotation + index) % 4] for index in range(depth))
        compare(menus, 12, 2, 24, -1, line=0xffff, profile='empty-loop')
    for rotation, heights, cutoff, flags in itertools.product(
            range(4), ((12, 0, 5), (0, 12, 0), (5, 12, 2), (2, 0, 12)),
            (0, 1, 2), (0, 1)):
        menus = tuple(MENUS[(rotation + index) % 4] for index in range(3))
        compare(menus, heights, 2, 2, cutoff, 1, 2, 0x74ff,
                slot_flags=flags, profile='mixed-heights-and-occlusion-flags')
    # Each later redraw consumes the previous actual CLI RAM and JSON registers.
    for renderer in (0x3650, 0x9332):
        carried_ram = None
        carried_d1, carried_d3 = 0x1234ab68, 0x56787088
        for frame in range(3):
            carried_ram, carried = compare((0x93e0, 0x958a, 0x978a), (8, 12, 5),
                1, 24, 2, 1, 0, carried_d3 & 65535,
                profile='cli-ram-json-carry', d1=carried_d1, d3=carried_d3,
                renderer=renderer, input_ram=carried_ram)
            carried_d1, carried_d3 = carried['d1'], carried['d3']

    sentinel = b'preserved-redraw-register-output'
    baseline = bytearray(65536)
    struct.pack_into('>III', baseline, 0x7f0e, OLDEST, OLDEST, 0x3650)
    struct.pack_into('>I', baseline, OLDEST - RAM_BASE, 0x93e0)
    baseline[0x7f02] = 8
    baseline[0x7f04:0x7f0b] = bytes((6, 0, 0, 4, 8, 24, 17))
    def reject(label, options, line=0x7088, bad_count=False):
        ram = bytearray(baseline)
        if bad_count:
            # Descriptor is valid for border preparation; item count fails later.
            ram[0x7f04] = 5
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        result = subprocess.run([str(executable), *options, str(inp), str(native),
            str(out), str(ports), str(OLDEST), str(line), str(font), str(stages),
            str(0x1feffc - 28)], capture_output=True, text=True)
        assert result.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel and inp.read_bytes() == ram, (label, result.stdout, result.stderr)
        negatives.append({'failure': label, 'outputs_preserved': True})
    for label, options in (
            ('duplicate-registers', ['--registers', '3', '0x7088', '--registers', '3', '0x7088']),
            ('missing-d3', ['--registers', '3']), ('missing-values', ['--registers']),
            ('overflow-d1', ['--registers', '4294967296', '0x7088']),
            ('negative-d3', ['--registers', '3', '-1'])):
        reject(label, options)
    reject('line-register-mismatch', ['--registers', '3', '0x7088'], line=0x7000)
    reject('late-item-count-error', ['--registers', '3', '0x7088'], bad_count=True)
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    if not any(row['callback_calls'] > 0 for row in rows) or not any(
            row['port_events'] > 0 for row in rows):
        raise ValueError('Actual callback/video coverage absent')
    report.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
        'program_code_modified': False,
        'address_mapping': 'CPU address equals verified decrypted ROM offset below 0x100000.',
        'entry_cpu_address': ENTRY, 'native_descriptor_cpu_addresses': list(MENUS),
        'native_callback_cpu_addresses': list(CALLBACKS),
        'native_menu_resource_sha256': native_hash, 'font_resource_sha256': font_hash,
        'null_name_resource_sha256': null_hash,
        'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'native_matrix_cases': native_cases,
        'whole_65536_byte_ram_equal': True, 'ordered_video_ports_equal': True,
        'full_d1_d3_equal': True, 'both_menu_renderers_verified': True,
        'cli_ram_json_carry_frames': 6, 'negative_cases': len(negatives),
        'negative_results': negatives, 'original_a2_restored': True,
        'actual_draw_order_and_callback_counts_asserted': True,
        'actual_stage_callback_entry_a7_equals_entry_minus_28': True,
        'results': rows,
        'scope': 'Unmodified a6da redraws oldest107efe through inclusive A2 last slot, '
                 'border9b58 and full9e1a with real9602/9802 and debug9aa8 callbacks. '
                 'All four native descriptors with flags0, depths2..4, partial redraw with '
                 'newer head occlusion, visible heights0/2/5/12 vs target17, selected rows, '
                 'widths2/3/24, coordinates, debug style and area0/last/255. '
                 'Mixed slot heights and newer slotflag bit0 occlusion bypass also checked. '
                 'Empty-loop A2=107f0e leaves RAM/ports/current unchanged. Whole RAM, '
                 'ordered ports and full D1/D3 compared; original A2 preservation and observed '
                 'stage callback entryA7=S-28 asserted. External stacks exceed110000. '
                 'Other registers/flags, external stack memory, natural reachability, pixels, '
                 'hardware timing and full boot excluded.'
    }, indent=2) + '\n')
    print('Menu stack redraw original/C++ match:', len(rows), 'cases;',
          native_cases, 'native matrix;', sum(row['callback_calls'] for row in rows),
          'actual stage callbacks;', sum(row['port_events'] for row in rows), 'ordered port events;',
          len(negatives), 'transactional rejections;', hashlib.sha256(report.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
