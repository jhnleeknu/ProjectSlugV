"""Compare complete native 958a/978a drawing against unmodified M68000 9e1a."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A1, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D1,
                               UC_M68K_REG_D3, UC_M68K_REG_PC,
                               UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import (COUNTS, SOURCE_SHA256, checked_resource,
                                  verify_resources)

RAM_BASE = 0x100000
CURRENT = 0x107efe
ENTRY = 0x9e1a
MENUS = (0x958a, 0x978a)
CALLBACKS = (0x9602, 0x9802)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    for menu, callback in zip(MENUS, CALLBACKS):
        items = [struct.unpack_from('>IIH', program, menu + 16 + index * 10)
                 for index in range(10)]
        expected = ([(0x956c, 0, 0), (0xfffffffe, 0, 0)] +
                    [(0x956c, callback, 0)] * 8) if menu == 0x958a else [
                    (0x976a, callback, 0)] * 10
        if (items != expected or program[menu + 116:menu + 120] != b'\xff' * 4 or
                struct.unpack_from('>H', program, menu + 14)[0] != 0):
            raise ValueError('Native descriptor changed: ' + hex(menu))
    stages = root / 'extracted/runtime/stages'
    groups = verify_resources(stages, program, source)
    null_hash = checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)
    if program[:4] != bytes.fromhex('0010f300'):
        raise ValueError('Native address-zero name changed')
    native = root / 'extracted/runtime/control_menu_tree.ms5d'
    native_hash = checked_resource(native, program, 0x937e, 0x9aa8)
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    executable = root / 'build/draw_menu_text'
    folder = root / 'artifacts/stage_menu_draw'
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
            write = (size, address, value & ((1 << (size * 8)) - 1))
            writes.append(write)
            if in_separator:
                separator_writes.append(write)

    def code_hook(cpu, address, size, user):
        nonlocal in_separator
        if address in CALLBACKS:
            calls.append((address, cpu.reg_read(UC_M68K_REG_A7)))
        # Count the real separator subroutine's writes without changing code.
        if address == 0x9cd4:
            in_separator = True
        elif address == 0x9d38:
            in_separator = False

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, code_hook, begin=0x9cd4, end=0x9d3a)
    for callback in CALLBACKS:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=callback, end=callback)

    def ram_for(menu, height, selected, width, head_mode, xy=(4, 8), boundary=0):
        ram = bytearray(hashlib.shake_256(
            b'ms5-full-stage-menu-v1:' + len(rows).to_bytes(4, 'big')).digest(65536))
        head = CURRENT if head_mode == 0 else CURRENT - 16
        struct.pack_into('>II', ram, 0x7f0e, head, CURRENT)
        struct.pack_into('>I', ram, 0x7f16, 0x3650)
        slot = CURRENT - RAM_BASE
        struct.pack_into('>I', ram, slot, menu)
        ram[slot + 4] = height  # Current visible height; +12 is merely target.
        ram[slot + 6:slot + 13] = bytes((10, selected, 0, *xy, width, 12))
        ram[slot + 15] = 0
        if head_mode:
            blocker = head - RAM_BASE
            struct.pack_into('>I', ram, blocker, menu)
            ram[blocker + 4] = 5
            ram[blocker + 9:blocker + 12] = bytes((xy[0], xy[1], 7))
            ram[blocker + 15] = 1 if head_mode == 2 else 0
        ram[0x7dfe] = selected % 8
        for group in range(8):
            ram[0x7dff + group] = (0, COUNTS[group] - 1, 255)[boundary]
        return ram

    def compare(menu, height, selected, width, clip, head_mode, xy=(4, 8),
                boundary=0, line=0x7000, stack=0x1feffc, profile='native-full'):
        nonlocal in_separator
        ram = ram_for(menu, height, selected, width, head_mode, xy, boundary)
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                           (UC_M68K_REG_A1, 0xa008 if clip else 0x3650),
                           (UC_M68K_REG_D1, 0), (UC_M68K_REG_D3, line),
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
            raise ValueError('Original exception: ' + repr((profile, hex(menu), height,
                             width, hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original full draw did not return')
        callback_stacks = {value for _, value in calls}
        if len(callback_stacks) > 1:
            raise ValueError('Full invocation has differing callback entry stacks')
        first_callback_row = 2 if menu == 0x958a else 0
        expected_calls = sum(index + 1 < height for index in range(first_callback_row, 10))
        if len(calls) != expected_calls or any(
                address != CALLBACKS[MENUS.index(menu)] for address, _ in calls):
            raise ValueError('Native visible callback coverage changed')
        if (menu == 0x958a and height >= 3 and width == 2 and head_mode == 0 and
                len(separator_writes) != 256):
            raise ValueError('Original width2 separator no longer writes256 tiles')
        callback_stack = next(iter(callback_stacks)) if calls else stack
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_result = {'line': cpu.reg_read(UC_M68K_REG_D3) & 65535}
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(native), str(out), str(ports),
                                 str(int(clip)), str(line), str(font), str(stages),
                                 str(callback_stack)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((profile, hex(menu), height,
                             width, result.stderr.strip())))
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        parsed = json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at])
                           for at in range(min(len(actual), 65536)) if actual[at] != expected[at]]
            port_difference = next((at for at in range(min(len(actual_ports), len(expected_ports)))
                                    if actual_ports[at] != expected_ports[at]), None)
            raise ValueError('Full draw mismatch: ' + repr((profile, hex(menu), height,
                selected, width, clip, head_mode, xy, boundary, line, callback_stack,
                differences[:16], len(expected_ports) // 9, len(actual_ports) // 9,
                port_difference, expected_result, parsed)))
        rows.append({'profile': profile, 'menu_cpu_address': menu, 'visible_height': height,
                     'target_height': 12, 'selected': selected, 'width': width,
                     'clip': clip, 'head_mode': head_mode, 'x': xy[0], 'y': xy[1],
                     'area_bytes': list(ram[0x7dff:0x7e07]), 'initial_line': line,
                     'entry_stack': stack, 'callback_entry_stack': callback_stack,
                     'callback_calls': len(calls), 'separator_port_events': len(separator_writes),
                     'result': parsed, 'port_events': len(writes),
                     'input_sha256': hashlib.sha256(ram).hexdigest(),
                     'ram_sha256': hashlib.sha256(expected).hexdigest(),
                     'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    for case in itertools.product(MENUS, (0, 2, 5, 12), range(10),
                                  (0, 1, 2, 3, 4, 24, 255), (False, True), (0, 1)):
        compare(*case)
    native_cases = len(rows)
    for menu, selected, clip, head_mode, xy, line, stack in itertools.product(
            MENUS, range(10), (False, True), (0, 1, 2),
            ((0, 0), (253, 250), (255, 255)), (0, 0x74ff, 0xffff),
            (0x1feffc, 0x1f8000)):
        compare(menu, 12, selected, 24, clip, head_mode, xy, 0, line, stack,
                'coordinate-line-stack-occlusion')
    geometry_cases = len(rows) - native_cases
    for selected, boundary, clip, head_mode, height, width in itertools.product(
            range(10), (1, 2), (False, True), (0, 1), (0, 2, 5, 12), (2, 24)):
        compare(0x958a, height, selected, width, clip, head_mode,
                boundary=boundary, profile='last-valid-and-address-zero-area')
    report.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__, 'cpu_model': 'M68000',
        'program_code_modified': False,
        'address_mapping': 'CPU address equals verified decrypted ROM offset below 0x100000.',
        'entry_cpu_address': ENTRY, 'native_descriptor_cpu_addresses': list(MENUS),
        'native_callback_cpu_addresses': list(CALLBACKS),
        'native_menu_resource_sha256': native_hash, 'font_resource_sha256': font_hash,
        'null_name_resource_sha256': null_hash,
        'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'native_full_cases': native_cases,
        'coordinate_line_stack_occlusion_cases': geometry_cases,
        'last_valid_and_address_zero_area_cases': len(rows) - native_cases - geometry_cases,
        'whole_65536_byte_ram_equal': True, 'ordered_video_ports_equal': True,
        'final_d3_word_equal': True, 'callback_entry_stack_constant_per_invocation': True,
        'results': rows,
        'scope': 'Unmodified full9e1a through native958a/978a, all ten rows, real9602/9802 '
                 'callbacks, original9cd4 separator, formatter3a70 and rendering helpers. '
                 'Visible slot+4 height0/2/5/12 differs from target+12 fixed12. Width0/1/2/3/4/'
                 '24/255, selected0..9, head=current/nested, clipping3650/a008, disabled blocker, '
                 'coordinates, initialD3 and external callback stack checked. Area0/last/255 '
                 'includes original address-zero bytes0010f300. Original callback entryA7 is '
                 'observed and supplied unchanged to every C++ callback within each call; '
                 'no-callback calls use valid external entry stack. Whole RAM, ordered video '
                 'writes and finalD3 word compared. Other registers/flags, external stack '
                 'memory, natural reachability, pixels, hardware timing and full boot excluded.'
    }, indent=2) + '\n')
    print('Full native stage menu original/C++ match:', len(rows), 'cases;',
          native_cases, 'native full;', geometry_cases, 'geometry/line/stack/occlusion')


if __name__ == '__main__':
    main()
