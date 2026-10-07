"""Compare post-9136 f5a caller transitions, helpers, and all ordered ports."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7,
    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

RAM_BASE, RETURN, ENTRY, LOOP, TRAP = 0x100000, 0xff000, 0xf5a, 0xec4, 0xfee
HOOKS = (0x3db2, 0x3d7e, 0x8bbc, 0x8bc8, 0x8c16, 0x8be0,
         0x5728, 0x7196, 0x43dbc, LOOP, TRAP)
OBJECTS = (0x100000, 0x100100, 0x100f5c, 0x10ff7a, 0x10d416, 0x10d414)
EFFECTS = ((0, 0, 0), (0x00ff, 1, 0x1000), (0x7fff, 1, 0x8000),
           (0xffff, 1, 0), (0x8000, 0xffff, 0x7fff),
           (0x1000, 0x0080, 0xf000), (0x1234, 0, 0x12ff))


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    resource = root / 'extracted/runtime/palettes.ms5p'
    packed = resource.read_bytes()
    records, _ = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] +
                       records[identifier][1] for identifier in sorted(records))
    if packed != struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload),
                              zlib.crc32(payload), 0, 0) + payload:
        raise ValueError('Palette resource does not match verified native source')
    executable = root / 'build/consume_control'
    palette_executable = root / 'build/step_palette_frame'
    if not executable.exists() or not palette_executable.exists():
        raise ValueError('Build consume_control and step_palette_frame first')
    folder = root / 'artifacts/control_caller'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_write(RAM_BASE, bytes(65536))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
        raise ValueError('Native allocator initialization failed')
    initial = bytes(cpu.mem_read(RAM_BASE, 65536))
    writes, trace, rows, palette_rows, sequences, negatives = [], [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if (address == 0x300001 or 0x3c0000 <= address < 0x3c0010 or
                address in (0x2ffff0, 0x2ffff2)):
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    def code_hook(cpu, address, size, user):
        trace.append(address)
        if address in (LOOP, TRAP):
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in HOOKS:
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(address, previous, restore, counter, phase, matching,
                timer=2, current=0x00ff, step=1, target=0x1000, pending=128):
        ram = bytearray(hashlib.shake_256(b'ms5-control-caller-v1:' +
            (len(rows) + len(palette_rows)).to_bytes(4, 'big')).digest(65536))
        ram[0x4d92:0x5da2] = initial[0x4d92:0x5da2]
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14] = slot & 31
            ram[node + 15] = (slot & 3) | (0x80 if slot % 7 == 0 else 0)
        for channel in range(3):
            struct.pack_into('>H', ram, 0x7dc2 + channel * 2, (current + channel * 0x101) & 65535)
            struct.pack_into('>H', ram, 0x7dc8 + channel * 2, (target + channel * 0x101) & 65535)
            struct.pack_into('>H', ram, 0x7dce + channel * 2, step)
        ram[0x7dd4], ram[0x7ded] = timer, pending
        ram[0x7dd6:0x7dea] = ram[0x7dc2:0x7dd6]
        struct.pack_into('>H', ram, 0x4d90, (0, 8, 0xff00, 0xffff)[len(rows) % 4])
        at = address - RAM_BASE
        struct.pack_into('>H', ram, at + 0x7e, counter)
        ram[at + 0x80], ram[at + 0x84] = restore, previous
        struct.pack_into('>H', ram, at + 0x82, (0, 1, 0x100, 0xffff)[len(rows) % 4])
        ram[0xd494] = phase
        local_counter = struct.unpack_from('>H', ram, at + 0x7e)[0]
        struct.pack_into('>H', ram, 0x000e, local_counter if matching else local_counter ^ 1)
        ram[0x10:0x12] = bytes.fromhex('beef')
        return ram

    def original(ram, d0, address, entry=ENTRY):
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, address), (UC_M68K_REG_A7, 0x1feffc),
                (UC_M68K_REG_D0, d0), (UC_M68K_REG_D1, 0xbeefaaaa)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        writes.clear()
        trace.clear()
        try:
            cpu.emu_start(entry, RETURN, count=8000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), hex(entry),
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (RETURN, LOOP, TRAP):
            raise ValueError('Original did not reach return/loop/trap boundary')
        return bytes(cpu.mem_read(RAM_BASE, 65536)), b''.join(
            struct.pack('>BII', *write) for write in writes), 0 if pc == RETURN else pc

    def compare(ram, d0, address, profile, sequence=None):
        expected, expected_ports, next_pc = original(ram, d0, address)
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(resource), str(out), str(ports),
            str(address), str(d0)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        parsed = json.loads(result.stdout)
        actual, actual_ports = out.read_bytes(), ports.read_bytes()
        if actual != expected or actual_ports != expected_ports or parsed != {'next_pc': next_pc}:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if expected[at] != actual[at]]
            port_difference = next(((at // 9, expected_ports[at:at+9].hex(),
                actual_ports[at:at+9].hex()) for at in range(0,
                max(len(expected_ports), len(actual_ports)), 9)
                if expected_ports[at:at+9] != actual_ports[at:at+9]), None)
            raise ValueError('Caller mismatch: ' + repr((len(rows), profile, d0, address,
                differences[:20], len(expected_ports)//9, len(actual_ports)//9,
                port_difference, next_pc, parsed, trace)))
        rows.append({'profile': profile, 'sequence': sequence, 'object_cpu_address': address,
            'control_d0': d0, 'previous_status': ram[address - RAM_BASE + 0x84],
            'restore_flag': ram[address - RAM_BASE + 0x80], 'next_pc': next_pc,
            'actual_trace': trace.copy(), 'port_events': len(writes),
            'port_counts': {hex(port): sum(write[1] == port for write in writes)
                            for port in (0x300001, 0x3c0006, 0x2ffff0, 0x2ffff2)},
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(expected), next_pc

    for status, previous, restore, effect, matching in itertools.product(
            (0, 1, 2, 255), (0, 1, 2, 255), (0, 255), range(4), (False, True)):
        address = OBJECTS[len(rows) % len(OBJECTS)]
        current, step, target = EFFECTS[effect]
        ram = fixture(address, previous, restore, (0, 1, 0x7fff, 0x8000, 0xffff)[len(rows) % 5],
            (0, 1, 255)[len(rows) % 3], matching, timer=(0, 1, 2, 255)[effect],
            current=current, step=step, target=target, pending=(0, 128)[effect % 2])
        compare(ram, 0x12345600 | status, address, 'status-transition-palette-video-counter')
    isolated = len(rows)
    for address in (0x100f5c, 0x10d416):
        ram = fixture(address, 1, 0, 0xffff, 255, True)
        label, begin = 'carried-caller-%06x' % address, len(rows)
        for status in (0, 0, 0, 2, 2, 0, 1, 1, 0, 255):
            ram, _ = compare(ram, status, address, 'whole-output-carry', sequence=label)
        sequences.append({'label': label, 'frames': len(rows) - begin})

    # Extend all140 original palette-frame fixtures to ordered watchdog/PVC ports
    # using the optional OUTPUT_PORTS CLI. Palette RAM equivalence remains full.
    for timer, effect, pending in itertools.product((0, 1, 2, 128, 255), EFFECTS, (0, 127, 128, 255)):
        current, step, target = effect
        ram = fixture(0x100f5c, 0, 0, 0, 0, True, timer, current, step, target, pending)
        expected, expected_ports, next_pc = original(ram, 0, 0x100f5c, entry=0x5728)
        if next_pc:
            raise ValueError('Independent palette-frame failed to return')
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run([str(palette_executable), str(inp), str(resource), str(out), str(ports)],
                                capture_output=True, text=True)
        if result.returncode or out.read_bytes() != expected or ports.read_bytes() != expected_ports:
            raise ValueError('Independent palette RAM/ports mismatch: ' + repr(
                (timer, effect, pending, result.stderr)))
        palette_rows.append({'timer': timer, 'current': current, 'step': step, 'target': target,
            'pending': pending, 'port_events': len(writes), 'actual_trace': trace.copy(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    # Video/backup mutations precede resource lookup; reject absent palette IDs
    # before either file is published. Never execute unknown native palette IDs.
    ram = fixture(0x100f5c, 1, 0, 0, 0, True, pending=0)
    struct.pack_into('>HH', ram, 0x4d92 + 10, 0xfffe, 0xfffe)
    ram[0x4d92 + 15] = 0x80
    inp.write_bytes(ram)
    for existing in (False, True):
        sentinels = (b'previous-ram-output', b'previous-port-output')
        for path, sentinel in zip((out, ports), sentinels):
            if existing:
                path.write_bytes(sentinel)
            else:
                path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), str(inp), str(resource), str(out), str(ports),
            str(0x100f5c), '0'], capture_output=True, text=True)
        if result.returncode == 0:
            raise ValueError('Missing palette ID accepted')
        for path, sentinel in zip((out, ports), sentinels):
            if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                    not existing and path.exists()):
                raise ValueError('Late palette failure changed outputs')
        negatives.append({'failure': 'late-missing-palette-id', 'existing_outputs': existing,
            'outputs_preserved': True, 'stderr': result.stderr.strip(), 'original_executed': False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original fixed program bytes changed')
    if bytes(cpu.mem_read(0x200000, 0xffff0)) != program[0x200000:0x2ffff0]:
        raise ValueError('Original fixed palette bank bytes changed outside PVC registers')
    hook_counts = {hex(address): sum(item == address for row in rows for item in row['actual_trace'])
                   for address in HOOKS}
    if not all(hook_counts.values()):
        raise ValueError('Caller transition/helper coverage missing: ' + repr(hook_counts))
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'entry_cpu_address': ENTRY, 'entry_rom_offset': ENTRY,
        'address_mapping': 'CPU address equals decrypted ROM offset in fixed region; '
            'observed palette bank maps decrypted ROM200000..2ffff0 to same CPU addresses.',
        'bank_rom_unchanged_except_pvc_register_tail': True,
        'palette_resource_sha256': hashlib.sha256(packed).hexdigest(),
        'cases': len(rows), 'isolated_cases': isolated, 'actual_hook_counts': hook_counts,
        'whole_65536_byte_ram_equal': True, 'all_ordered_video_watchdog_pvc_ports_equal': True,
        'next_pc_boundary_equal': True, 'output_carry_sequences': sequences,
        'independent_palette_frame_port_cases': len(palette_rows),
        'independent_palette_frame_ram_and_ports_equal': True,
        'palette_frame_results': palette_rows, 'negative_cases': len(negatives),
        'late_palette_failure_outputs_preserved': True, 'negative_results': negatives,
        'ordered_port_events': sum(row['port_events'] for row in rows), 'results': rows,
        'scope': 'Post-controller f5a caller consumer. Low-byte status0/1/2/ff and '
            'previous status0/1/2/ff, video query/set, palette backup/darken/restore/frame '
            'preparation, frame counter match/trap and phase alias compared with actual '
            'native helpers. Stop at ec4 loop boundary and fee before TRAP15 execution. '
            'WholeRAM carried across caller status transitions. Independent140 original '
            'palette-frame cases additionally compare watchdog/PVC writes. Physical '
            'bank device/timing, trap handler, ec4 loop input/frame acquisition, full '
            'controller-to-caller execution and full boot excluded.'}, indent=2) + '\n')
    print('Control caller original/C++ match:', len(rows), 'cases;', len(palette_rows),
          'independent palette-port cases;', len(negatives), 'late failures;', hook_counts)


if __name__ == '__main__':
    main()
