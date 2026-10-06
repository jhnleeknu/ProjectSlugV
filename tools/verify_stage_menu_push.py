"""Compare unmodified a0a0 pushes with native stage parents and real callbacks."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A7,
                               UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
                               UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import (COUNTS, SOURCE_SHA256, checked_resource,
                                  verify_resources)

RAM_BASE = 0x100000
ENTRY = 0xa0a0
MENUS = (0x958a, 0x978a)
CALLBACKS = (0x9602, 0x9802)
CHILDREN = (0x93e0, 0x99ee, 0x958a, 0x978a)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    for menu, callback in zip(MENUS, CALLBACKS):
        items = [struct.unpack_from('>IIH', program, menu + 16 + 10 * index)
                 for index in range(10)]
        expected = ([(0x956c, 0, 0), (0xfffffffe, 0, 0)] +
                    [(0x956c, callback, 0)] * 8) if menu == 0x958a else [
                    (0x976a, callback, 0)] * 10
        if (items != expected or program[menu + 116:menu + 120] != b'\xff' * 4 or
                struct.unpack_from('>H', program, menu + 14)[0] != 0):
            raise ValueError('Native descriptor changed: ' + hex(menu))
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    stages = root / 'extracted/runtime/stages'
    groups = verify_resources(stages, program, source)
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    null_hash = checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)
    if program[:4] != bytes.fromhex('0010f300'):
        raise ValueError('Original address-zero name changed')
    executable = root / 'build/push_menu'
    folder = root / 'artifacts/stage_menu_push'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
                             ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, calls, separator_writes, rows = [], [], [], []
    in_separator = False

    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            event = (size, address, value & ((1 << (size * 8)) - 1))
            writes.append(event)
            if in_separator:
                separator_writes.append(event)

    def code_hook(cpu, address, size, user):
        nonlocal in_separator
        if address in CALLBACKS:
            calls.append((address, cpu.reg_read(UC_M68K_REG_A7)))
        if address == 0x9cd4:
            in_separator = True
        elif address == 0x9d38:
            in_separator = False

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, code_hook, begin=0x9cd4, end=0x9d3a)
    for callback in CALLBACKS:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=callback, end=callback)

    def compare(menu, height, selected, width, child, head, current,
                xy=(4, 8), child_xy=(6, 10), boundary=0,
                line=0x7000, stack=0x1feffc, profile='native-stage-parent'):
        nonlocal in_separator
        ram = bytearray(hashlib.shake_256(
            b'ms5-stage-menu-push-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        struct.pack_into('>II', ram, 0x7f0e, head, current)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        slot = head - RAM_BASE
        struct.pack_into('>I', ram, slot, menu)
        ram[slot + 4] = height
        ram[slot + 6:slot + 13] = bytes((10, selected, 0, *xy, width, 12))
        ram[slot + 15] = 0
        ram[0x7dfe] = selected % 8
        for group in range(8):
            ram[0x7dff + group] = (0, COUNTS[group] - 1, 255)[boundary]
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_A0, child), (UC_M68K_REG_D0, child_xy[0]),
                           (UC_M68K_REG_D1, child_xy[1]), (UC_M68K_REG_D3, line),
                           (UC_M68K_REG_A7, stack)):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        calls.clear()
        separator_writes.clear()
        in_separator = False
        try:
            cpu.emu_start(ENTRY, 0xff000, count=4000000)
        except unicorn.UcError as error:
            raise ValueError('Original push exception: ' + repr((profile, hex(menu), height,
                             width, hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original push did not return')
        first_callback_row = 2 if menu == 0x958a else 0
        expected_calls = sum(index + 1 < height for index in range(first_callback_row, 10))
        callback_stack = stack - 40
        if len(calls) != expected_calls or any(
                address != CALLBACKS[MENUS.index(menu)] or observed != callback_stack
                for address, observed in calls):
            raise ValueError('Push callback address/count/entry stack changed: ' + repr(
                (hex(menu), height, hex(stack), calls, expected_calls, hex(callback_stack))))
        if expected_calls and not writes:
            raise ValueError('Visible callbacks produced no video writes')
        if (menu == 0x958a and height >= 3 and width == 2 and
                len(separator_writes) != 256):
            raise ValueError('Original width2 separator no longer writes256 tiles')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *event) for event in writes)
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(native), str(out), str(ports),
                                 str(child), str(child_xy[0] & 65535),
                                 str(child_xy[1] & 65535), str(line & 65535),
                                 str(font), str(stages), str(callback_stack)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((profile, hex(menu), height,
                             width, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        if actual != expected or actual_ports != expected_ports:
            differences = [(hex(at), expected[at], actual[at])
                           for at in range(min(len(actual), 65536)) if actual[at] != expected[at]]
            first_port = next((at // 9 for at, (a, b) in
                               enumerate(zip(actual_ports, expected_ports)) if a != b), None)
            raise ValueError('Stage push mismatch: ' + repr((profile, hex(menu), height,
                selected, width, hex(child), hex(head), hex(current), xy, child_xy, boundary,
                line, hex(callback_stack), differences[:16], len(expected_ports) // 9,
                len(actual_ports) // 9, first_port)))
        new_slot = slot - 16
        if (struct.unpack_from('>I', expected, 0x7f0e)[0] != head - 16 or
                expected[new_slot + 5] != ram[new_slot + 5] or
                expected[0x7f12:0x7f1b] != ram[0x7f12:0x7f1b]):
            raise ValueError('New slot fraction/current/renderer/input preservation changed')
        rows.append({'profile': profile, 'parent_descriptor_cpu_address': menu,
                     'child_descriptor_cpu_address': child, 'visible_height': height,
                     'target_height': 12, 'selected': selected, 'width': width,
                     'head': head, 'saved_current': current, 'parent_xy': list(xy),
                     'child_xy': list(child_xy), 'initial_line': line,
                     'area_bytes': list(ram[0x7dff:0x7e07]),
                     'entry_stack': stack, 'expected_callback_entry_stack': callback_stack,
                     'observed_callback_entry_stacks': sorted({value for _, value in calls}),
                     'callback_calls': len(calls), 'separator_port_events': len(separator_writes),
                     'port_events': len(writes), 'new_slot': expected[new_slot:new_slot + 16].hex(),
                     'input_sha256': hashlib.sha256(ram).hexdigest(),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for menu, height, selected, width, child, head in itertools.product(
            MENUS, (0, 2, 5, 12), range(10), (0, 1, 2, 3, 4, 24, 255),
            CHILDREN, (0x107efe, 0x107e1e)):
        current = (0, head, 0x107efe, 0xdeadbeef)[len(rows) % 4]
        compare(menu, height, selected, width, child, head, current)
    native_cases = len(rows)
    for menu, child, current, xy, line, stack in itertools.product(
            MENUS, CHILDREN, (0, 0x107efe, 0xdeadbeef),
            ((0, 0), (253, 250), (255, 255)), (0, 0x74ff, 0xffff),
            (0x1feffc, 0x1f8000)):
        compare(menu, 12, 9, 24, child, 0x107e1e, current, xy,
                (0x12340004, 0x56780008), line=line, stack=stack,
                profile='coordinate-line-stack-current')
    geometry_cases = len(rows) - native_cases
    for menu, selected, boundary, height, width, child in itertools.product(
            MENUS, range(10), (1, 2), (0, 2, 5, 12), (2, 24), CHILDREN):
        compare(menu, height, selected, width, child, 0x107efe, 0xdeadbeef,
                boundary=boundary, profile='last-valid-and-address-zero-area')
    report.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
        'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'address_mapping': 'CPU address equals verified decrypted ROM offset below 0x100000.',
        'native_parent_descriptor_cpu_addresses': list(MENUS),
        'native_child_descriptor_cpu_addresses': list(CHILDREN),
        'native_callback_cpu_addresses': list(CALLBACKS),
        'native_menu_resource_sha256': native_hash, 'font_resource_sha256': font_hash,
        'null_name_resource_sha256': null_hash,
        'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'native_parent_cases': native_cases,
        'coordinate_line_stack_current_cases': geometry_cases,
        'last_valid_and_address_zero_area_cases': len(rows) - native_cases - geometry_cases,
        'whole_65536_byte_ram_equal': True, 'ordered_video_ports_equal': True,
        'new_child_slot_equal': True, 'saved_current_and_fraction_preserved': True,
        'callback_entry_stack_equals_push_entry_minus_40': True,
        'visible_callback_cases': sum(bool(row['callback_calls']) for row in rows),
        'results': rows,
        'scope': 'Unmodified original a0a0 push through native958a/978a parents, real9602/9802 '
                 'callbacks, full9e1a drawing and original separator9cd4, followed by child '
                 'initialization. Root/debug/stage child descriptors, visible0/2/5/12 versus '
                 'target12, all selected rows, width0/1/2/3/4/24/255, shallow/deep head, saved '
                 'current including invalid preserved values, coordinates/high-word child inputs, '
                 'initialD3 and external stack variants. Area0/last/255 includes original '
                 'address-zero bytes0010f300. Every real callback entryA7 asserted push entryS-40 '
                 '(savecurrent4 + movem12 + bsr fulltext4 + callbackframe20) and supplied to C++. '
                 'Hidden/no-callback cases checked independently. All65536RAM bytes, new child '
                 'slot and exact ordered video writes compared. Registers/flags, external stack '
                 'memory, natural reachability, pixels, hardware timing and full boot excluded.'
    }, indent=2) + '\n')
    print('Native stage-parent push original/C++ match:', len(rows), 'cases;',
          native_cases, 'native;', geometry_cases, 'geometry/line/stack/current')


if __name__ == '__main__':
    main()
