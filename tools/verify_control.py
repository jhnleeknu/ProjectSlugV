"""Compare unified native9136 dispatch and carried controller transitions."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5,
    UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources

RAM_BASE, RETURN, ENTRY, EMPTY, OLDEST, BIOS = 0x100000, 0xff000, 0x9136, 0x107f0e, 0x107efe, 0xc00444
HOOKS = (0x919a, 0x91c2, 0x92ce, 0x92fc, 0x9302, 0x928e, 0x9602, 0x9802, BIOS)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    menu, pause, font, stages = [root / 'extracted/runtime' / name for name in
        ('control_menu_tree.ms5d', 'control_pause.ms5d', 'menu_fonts.ms5d', 'stages')]
    hashes = {'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
              'pause': checked_resource(pause, program, 0x9068, 0x9086),
              'font': checked_resource(font, program, 0xe80c8, 0xe84c8)}
    groups = verify_resources(stages, program, source)
    hashes['null_name'] = checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)
    executable = root / 'build/step_control'
    if not executable.exists():
        raise ValueError('Build build/step_control first')
    folder = root / 'artifacts/control'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    for address in (0x300000, 0x3c0000, 0xc00000):
        cpu.mem_map(address, 0x1000)
    writes, trace, rows, sequences, negatives = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        trace.append({'address': address, 'd0': cpu.reg_read(UC_M68K_REG_D0),
                      'a7': cpu.reg_read(UC_M68K_REG_A7)})
        if address == BIOS:
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in HOOKS:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def arguments(style, line, stack):
        return [str(executable), str(inp), str(menu), str(pause), str(out), str(ports),
                str(style), str(line), str(stack), str(font), str(stages)]

    def fixture(active=0, pending=0, request=0):
        ram = bytearray(hashlib.shake_256(b'ms5-unified-control-v1:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0x7df0], ram[0x7df1], ram[0x7dee] = active, pending, 0
        ram[0x12], ram[0xfd82] = 2, 0
        ram[0xfdb6] = ram[0xfdb7] = 1
        ram[0x4cb5], ram[0x4cb4], ram[0xf001], ram[0xf002] = request, 0, 0, 1
        ram[0x4cba] = ram[0x4cc0] = 0
        struct.pack_into('>IH', ram, 0x7df6, 0, 0)
        return ram

    def compare(ram, profile, style=0x0603, line=0x7000, stack=0x1feffc, sequence=None):
        branch = 'inactive' if not ram[0x7df0] else 'menu' if ram[0x7dee] else 'wait'
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, 0xbeef0000 | style),
                (UC_M68K_REG_D3, 0xcafe0000 | line), (UC_M68K_REG_A7, stack),
                (UC_M68K_REG_A0, 0x87654321),
                (UC_M68K_REG_A1, int.from_bytes(ram[0x7f16:0x7f1a], 'big'))):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        writes.clear()
        trace.clear()
        try:
            cpu.emu_start(ENTRY, RETURN, count=8000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), profile,
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (RETURN, BIOS):
            raise ValueError('Original did not reach return or BIOS boundary')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_result = {'status': 0 if pc == BIOS else struct.unpack('>i', struct.pack('>I',
            cpu.reg_read(UC_M68K_REG_D0)))[0], 'external_jump': BIOS if pc == BIOS else 0,
            'line': cpu.reg_read(UC_M68K_REG_D3) & 65535}
        if branch == 'inactive' and expected_result['line'] != line:
            raise ValueError('Inactive path changed incoming D3')
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run(arguments(style, line, stack), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports, parsed = out.read_bytes(), ports.read_bytes(), json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if actual[at] != expected[at]]
            raise ValueError('Unified mismatch: ' + repr((len(rows), profile, sequence,
                differences[:20], len(expected_ports)//9, len(actual_ports)//9,
                expected_result, parsed, trace)))
        rows.append({'profile': profile, 'sequence': sequence, 'incoming_branch': branch,
            'active': ram[0x7df0], 'menu_active': ram[0x7dee], 'style': style, 'line': line,
            'entry_stack': stack, 'actual_trace': trace.copy(), 'result': parsed,
            'port_events': len(writes), 'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), parsed['line']

    for pending, request, gate, inhibited in itertools.product((0, 1, 2, 3, 0x80, 255),
            (0, 2, 8, 10), (0, 2), (0, 255)):
        ram = fixture(pending=pending, request=request)
        ram[0xf000], ram[0x7def] = gate, inhibited
        compare(ram, 'inactive-pending-request-gates', style=(0, 0xff6b)[len(rows) % 2],
                line=(0, 0xffff)[len(rows) % 2])
    for active, request, held, repeat, blink in itertools.product((1, 2, 3, 0x80),
            (0, 1, 4, 2, 8), (0, 1, 4), (0, 1, 15, 255), (0, 49)):
        ram = fixture(active=active, request=request)
        ram[0x4cb4], ram[0x7df2], ram[0x7df3] = held, repeat, blink
        compare(ram, 'active-wait-step-repeat-menu-start', style=0xff6b, line=0xffff)
    isolated = len(rows)

    # Start with inactive state, then carry every output byte through the whole
    # dispatcher lifecycle. Only the input bytes supplied by the host are changed.
    for child, confirm, activation_pending, style, stack in (
            (2, True, 0, 0x0603, 0x1feffc), (3, True, 3, 0xff6b, 0x1f8000),
            (1, False, 1, 0, 0x1feffc), (2, False, 2, 0xff6b, 0x1f8000)):
        ram = bytearray(65536)
        ram[0x12], ram[0xf000], ram[0xf002] = 2, 2, 1
        ram[0xfdb6] = ram[0xfdb7] = 1
        ram[0x7df1] = activation_pending
        label = 'activation-child-%d-%s-pending-%d' % (child, 'confirm' if confirm else 'cancel', activation_pending)
        begin, line = len(rows), 0xffff

        def tick(request=0, first=0, held=0):
            nonlocal ram, line
            ram[0x4cb5], ram[0x4cba], ram[0x4cc0], ram[0x4cb4] = request, first, 0, held
            ram, line = compare(ram, 'carried-lifecycle', style, line, stack, label)

        activation_request = 8 if activation_pending == 2 else 2
        tick(activation_request if not activation_pending else 0)
        if not ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Sequence failed inactive-to-wait activation')
        for frame in range(20):
            tick(held=4 if ram[0x7df0] == 2 else 1)
        tick(8 if ram[0x7df0] == 2 else 2)
        if not ram[0x7dee]:
            raise ValueError('Sequence failed wait-to-menu startup')

        def open_menu():
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big') - RAM_BASE
                if ram[0x7f1b] == 0 and ram[head + 4] >= ram[head + 12]:
                    return
            raise ValueError('Carried menu did not open')

        open_menu()
        for _ in range(child):
            tick(first=2)
        tick(first=16)
        head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
        descriptor = int.from_bytes(ram[head - RAM_BASE:head - RAM_BASE + 4], 'big')
        if head != OLDEST - 16 or descriptor != (0x99ee, 0x958a, 0x978a)[child - 1]:
            raise ValueError('Carried root did not push expected child')
        open_menu()
        for first in (2, 4, 8):
            tick(first=first)
        tick(first=16 if confirm else 32)

        def close_to(target):
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
                if head == target and (target == EMPTY or ram[0x7f1b] == 0):
                    return
            raise ValueError('Carried menu failed to close to target')

        close_to(EMPTY if confirm else OLDEST)
        if not confirm:
            # Request exit while parent is still active; header sets exitword1.
            tick(request=8 if ram[0x7df0] == 2 else 2)
            close_to(EMPTY)
        if ram[0x7dee] or ram[0x7df0] or ram[0x7dfa:0x7dfc] != b'\0\1':
            raise ValueError('Full controller exit did not clear both activity bytes')
        # Reactivation, waiting, a second root startup, and exit use carried RAM.
        tick(2)
        if not ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Full exit failed reactivation')
        tick()
        tick(2)
        open_menu()
        tick(2)
        close_to(EMPTY)
        if ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Reactivated controller failed second full exit')
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'final_head': EMPTY, 'full_exit_and_reactivation_asserted': True})

    # Carry actual startup output into an unsupported completion callback.
    ram = fixture(active=1, request=2)
    ram, _ = compare(ram, 'late-callback-fixture-start')
    ram[0x7f1b], ram[0x7f02] = 2, 0
    struct.pack_into('>I', ram, 0x7df6, 0xdeadbeef)
    struct.pack_into('>H', ram, 0x7dfa, 1)
    inp.write_bytes(ram)
    for existing in (False, True):
        sentinels = (b'previous-ram-output', b'previous-port-output')
        for path, sentinel in zip((out, ports), sentinels):
            if existing:
                path.write_bytes(sentinel)
            else:
                path.unlink(missing_ok=True)
        result = subprocess.run(arguments(0xff6b, 0xffff, 0x1feffc), capture_output=True, text=True)
        if result.returncode == 0:
            raise ValueError('Unknown completion callback accepted')
        for path, sentinel in zip((out, ports), sentinels):
            if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                    not existing and path.exists()):
                raise ValueError('Late rejection changed output files')
        negatives.append({'failure': 'unsupported-late-callback', 'existing_outputs': existing,
            'stderr': result.stderr.strip(), 'outputs_preserved': True, 'original_executed': False})
    hook_counts = {hex(address): sum(item['address'] == address for row in rows
        for item in row['actual_trace']) for address in HOOKS}
    if not all(hook_counts[hex(address)] for address in HOOKS[:-1]):
        raise ValueError('Unified branch/stage-callback transition coverage missing')
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original mapped ROM bytes changed')
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'address_mapping': 'CPU address equals decrypted ROM offset below0x100000.',
        'native_resource_sha256': hashes,
        'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'isolated_cases': isolated, 'actual_hook_counts': hook_counts,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_ports_equal': True,
        'signed_d0_and_d3_word_equal': True, 'inactive_d3_preservation_asserted': True,
        'late_callback_failure_outputs_preserved': True, 'negative_results': negatives,
        'ordered_port_events': sum(row['port_events'] for row in rows), 'results': rows,
        'scope': 'Unified unmodified9136 inactive/wait/menu dispatch. Inactive pending/request '
            'and gate matrix, active wait/step/repeat/blink/startup matrix, and wholeRAM '
            'activation-to-wait-to-menu-to-child-to-full-exit-to-reactivation lifecycles. '
            'Both stage children confirm, debug/area cancellation with later header exit, '
            'second full exit, styles and external stack variants compared. Host supplies '
            'input bytes between frames; natural input acquisition, pixels, hardware timing, '
            'other CPU registers/flags, arbitrary callbacks, external stack contents and '
            'full boot excluded.'}, indent=2) + '\n')
    print('Unified control original/C++ match:', len(rows), 'cases;', len(sequences),
          'carried lifecycles;', len(negatives), 'late callback rejections;', hook_counts)


if __name__ == '__main__':
    main()
