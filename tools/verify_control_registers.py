"""Compare immutable 92fc/9136/f54 control paths and full D1/D3 outputs."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5,
    UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1,
    UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources

RAM_BASE, RETURN, ENTRY, LOOP, TRAP, BIOS = 0x100000, 0xff000, 0xf54, 0xec4, 0xfee, 0xc00444
OLDEST, EMPTY = 0x107efe, 0x107f0e
HOOKS = (0xf5a, 0x919a, 0x91c2, 0x92ce, 0x92fc, 0x9302, 0x928e,
         0x9602, 0x9802, 0x4718, 0x479e, 0x4c40, 0x504c, 0x950c, 0x9532, 0x5728, 0x7196, 0x43dbc, LOOP, TRAP, BIOS)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    menu, pause, font, stages, palettes = [root / 'extracted/runtime' / name for name in
        ('control_menu_tree.ms5d', 'control_pause.ms5d', 'menu_fonts.ms5d', 'stages', 'palettes.ms5p')]
    hashes = {'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
              'pause': checked_resource(pause, program, 0x9068, 0x9086),
              'font': checked_resource(font, program, 0xe80c8, 0xe84c8),
              'null_name': checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)}
    groups = verify_resources(stages, program, source)
    records, _ = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] +
                       records[identifier][1] for identifier in sorted(records))
    packed = palettes.read_bytes()
    if packed != struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload),
                              zlib.crc32(payload), 0, 0) + payload:
        raise ValueError('Palette resource differs from verified native source')
    hashes['palettes'] = hashlib.sha256(packed).hexdigest()
    executable = root / 'build/step_control_caller'
    if not executable.exists():
        raise ValueError('Build build/step_control_caller first')
    folder = root / 'artifacts/control_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 0x1000)
    cpu.mem_write(RAM_BASE, bytes(65536))
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    if cpu.reg_read(UC_M68K_REG_PC) != RETURN:
        raise ValueError('Native allocator initialization failed')
    initial = bytes(cpu.mem_read(RAM_BASE, 65536))
    writes, trace, rows, sequences, negatives = [], [], [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if (address == 0x300001 or 0x3c0000 <= address < 0x3c0010 or
                address in (0x2ffff0, 0x2ffff2)):
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (RAM_BASE <= address and address + size <= 0x110000) and not (0x1f7000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((address, size, value)))

    def code_hook(cpu, address, size, user):
        trace.append({'address': address, 'a6': cpu.reg_read(UC_M68K_REG_A6),
                      'a7': cpu.reg_read(UC_M68K_REG_A7), 'd0': cpu.reg_read(UC_M68K_REG_D0)})
        if address in (LOOP, TRAP, BIOS, RETURN):
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in HOOKS + (RETURN,):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)

    def fixture(address=0x100f5c, active=0, pending=0, request=0, palette_pending=0):
        ram = bytearray(initial)
        ram[0x5da2:0x7da2] = hashlib.shake_256(b'ms5-caller-step-v1:' +
            len(rows).to_bytes(4, 'big')).digest(8192)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14] = slot & 31
            ram[node + 15] = (slot & 3) | (0x80 if slot % 7 == 0 else 0)
        ram[0x7df0], ram[0x7df1], ram[0x7dee] = active, pending, 0
        ram[0x12], ram[0xfd82], ram[0xf000], ram[0xf002] = 2, 0, 2, 1
        ram[0xfdb6] = ram[0xfdb7] = 1
        ram[0x4cb5], ram[0x7ded] = request, palette_pending
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        struct.pack_into('>H', ram, address - RAM_BASE + 0x7e, 0xffff)
        struct.pack_into('>H', ram, 0x000e, 0xffff)
        ram[address - RAM_BASE + 0x84] = 1
        return ram

    def menu_fixture(address=0x100f5c, mode=0, height=12, selected=0, exit_word=0):
        ram = fixture(address, active=3)
        ram[0x7dee] = 255
        struct.pack_into('>III', ram, 0x7f0e, OLDEST, OLDEST, 0x9332)
        struct.pack_into('>H', ram, 0x7dfa, exit_word)
        struct.pack_into('>I', ram, 0x7efe, 0x93e0)
        ram[0x7f02:0x7f0e] = bytes((height, 0, 6, selected, selected, 4, 8, 24, 12, 3, 255, 0))
        ram[0x7f1b] = mode
        return ram

    def arguments(address, style, line, stack, registers=(0xabcd0603, 0xdead7000), kind='caller'):
        binary = root / 'build' / {'caller': 'step_control_caller', 'control': 'step_control', 'menu': 'step_control_menu'}[kind]
        common = [str(binary), '--registers', str(registers[0]), str(registers[1]), str(inp), str(menu), str(pause)]
        if kind == 'caller':
            return common + [str(palettes), str(out), str(ports), str(address), str(style), str(line), str(stack), str(font), str(stages)]
        return common + [str(out), str(ports), str(style), str(line), str(stack), str(font), str(stages)]

    def compare(ram, address, profile, style=0x0603, line=0x7000, stack=0x1feffc, sequence=None, register_inputs=None, kind='caller'):
        registers = register_inputs if register_inputs is not None else ((((len(rows)*0x7341)^0xabcd)&65535)<<16|style, (((len(rows)*0x1234)^0xdead)&65535)<<16|line)
        style, line = registers[0]&65535, registers[1]&65535
        entry = {'caller': 0xf54, 'control': 0x9136, 'menu': 0x92fc}[kind]
        cpu.mem_write(RAM_BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, address), (UC_M68K_REG_A7, stack),
                (UC_M68K_REG_D0, 0x12345678), (UC_M68K_REG_D1, registers[0]),
                (UC_M68K_REG_D3, registers[1]), (UC_M68K_REG_A0, 0x87654321),
                (UC_M68K_REG_A1, int.from_bytes(ram[0x7f16:0x7f1a], 'big'))):
            cpu.reg_write(reg, value)
        cpu.mem_write(stack, RETURN.to_bytes(4, 'big'))
        writes.clear()
        trace.clear()
        try:
            cpu.emu_start(entry, RETURN, count=12000000)
        except unicorn.UcError as error:
            raise ValueError('Original exception: ' + repr((len(rows), profile,
                hex(cpu.reg_read(UC_M68K_REG_PC)), str(error)))) from error
        pc = cpu.reg_read(UC_M68K_REG_PC)
        if pc not in (RETURN, LOOP, TRAP, BIOS):
            raise ValueError('Original failed to stop at expected boundary')
        caller_entries = [item for item in trace if item['address'] == 0xf5a]
        if pc == BIOS:
            if caller_entries:
                raise ValueError('BIOS transfer ran caller consumer')
        elif kind == 'caller' and (len(caller_entries) != 1 or caller_entries[0]['a6'] != address):
            raise ValueError('Native controller did not preserve caller A6: ' + repr(
                (len(rows), profile, address, caller_entries, trace)))
        if caller_entries and caller_entries[0]['a7'] != stack:
            raise ValueError('Original controller return did not restore caller stack')
        expected = bytes(cpu.mem_read(RAM_BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        next_pc = 0 if pc == RETURN else pc
        expected_result = {'d1': cpu.reg_read(UC_M68K_REG_D1)&0xffffffff, 'd3': cpu.reg_read(UC_M68K_REG_D3)&0xffffffff}
        if kind == 'caller':
            expected_result['next_pc'] = next_pc
        else:
            expected_result.update({'status': 0 if pc == BIOS else struct.unpack('>i',struct.pack('>I',cpu.reg_read(UC_M68K_REG_D0)))[0], 'external_jump': BIOS if pc == BIOS else 0, 'line': expected_result['d3']&65535})
        inp.write_bytes(ram)
        for path in (out, ports):
            path.unlink(missing_ok=True)
        result = subprocess.run(arguments(address, style, line, stack, registers, kind), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected: ' + repr((len(rows), profile, result.stderr.strip())))
        actual, actual_ports, parsed = out.read_bytes(), ports.read_bytes(), json.loads(result.stdout)
        if actual != expected or actual_ports != expected_ports or parsed != expected_result:
            differences = [(hex(at), expected[at], actual[at]) for at in
                range(min(len(actual), 65536)) if expected[at] != actual[at]]
            port_difference = next(((at//9, expected_ports[at:at+9].hex(), actual_ports[at:at+9].hex())
                for at in range(0, max(len(expected_ports), len(actual_ports)), 9)
                if expected_ports[at:at+9] != actual_ports[at:at+9]), None)
            raise ValueError('Caller-step mismatch: ' + repr((len(rows), profile, sequence,
                differences[:20], port_difference, next_pc, parsed, trace)))
        rows.append({'profile': profile, 'kind': kind, 'entry_cpu_address': entry, 'sequence': sequence, 'object_cpu_address': address, 'incoming_d1': registers[0], 'incoming_d3': registers[1], 'result': parsed,
            'initial_line': line, 'initial_style': style, 'entry_stack': stack,
            'active': ram[0x7df0], 'menu_active': ram[0x7dee], 'next_pc': next_pc,
            'actual_trace': trace.copy(), 'port_events': len(writes),
            'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(actual), (parsed['d1'], parsed['d3'])

    for pending, request, gate, inhibited, palette_pending in itertools.product(
            (0, 1, 2, 3, 255), (0, 2, 8), (0, 2), (0, 255), (0, 128)):
        ram = fixture(pending=pending, request=request, palette_pending=palette_pending)
        ram[0xf000], ram[0x7def] = gate, inhibited
        compare(ram, 0x100f5c, 'inactive-idle-or-activation')
    for active, request, held, repeat in itertools.product((1, 2, 3), (0, 1, 2, 4, 8),
                                                         (0, 1, 4), (0, 1, 15)):
        ram = fixture(active=active, request=request, palette_pending=len(rows) % 2 * 128)
        ram[0x4cb4], ram[0x7df2], ram[0x7df3] = held, repeat, (0, 49, 255)[repeat % 3]
        compare(ram, 0x100f5c, 'active-wait-step-repeat-startup', style=0xff6b, line=0xffff)
    for mode, height, exit_word, matched in itertools.product((0, 1, 2), (0, 12), (0, 1), (False, True)):
        ram = menu_fixture(mode=mode, height=height, exit_word=exit_word)
        if not matched:
            ram[0x000f] ^= 1
        compare(ram, 0x100f5c, 'menu-opening-closing-counter-trap')
    for selected in (4, 5):
        ram = menu_fixture(selected=selected)
        ram[0x7f0c] = 3
        # Native static restart preconditions: no animation/palette owner or
        # coordinate link and object+10 zero, with original3ef2 allocator state.
        struct.pack_into('>H', ram, 0x8e4 + 0x10, 0)
        ram[0x8e4 + 0x1d], ram[0x8e4 + 0x6c] = 0, 255
        compare(ram, 0x100f5c, 'static-restart-caller-a6' if selected == 4 else
                'bios-transfer-skips-caller')
    for timer, pending, previous, restore in itertools.product((0, 1, 2, 255), (0, 128), (0, 1), (0, 1)):
        ram = fixture(palette_pending=pending)
        for channel in range(3):
            struct.pack_into('>H', ram, 0x7dc2 + channel*2, (0x00ff + channel*0x101)&65535)
            struct.pack_into('>H', ram, 0x7dc8 + channel*2, (0x1000 + channel*0x101)&65535)
            struct.pack_into('>H', ram, 0x7dce + channel*2, 1)
        ram[0x7dd4] = timer
        ram[0x7dd6:0x7dea] = ram[0x7dc2:0x7dd6]
        ram[0xfdaf] = 3
        ram[0xfd82] = 1
        ram[0xf002] = 0
        ram[0xfd9a] = 0
        ram[0xfdc] = restore
        ram[0xfe0] = previous
        compare(ram, 0x100f5c, 'caller-palette-full-register-paths')

    def native_menu(menu_address=0x93e0, mode=0, height=None, pending=255, renderer=0x3650, depth=1, selected=None, exit_word=0):
        ram = fixture(active=3)
        ram[0x7dee] = 255
        ram[0x4cb5] = ram[0x4cb4] = 0
        ram[0x4cba] = ram[0x4cc0] = 0
        ram[0x7f1b] = mode
        ram[0x7dfe] = 0
        ram[0x7dff:0x7e07] = bytes(8)
        struct.pack_into('>I', ram, 0x7df6, 0)
        struct.pack_into('>H', ram, 0x7dfa, exit_word)
        head = OLDEST-16*(depth-1)
        struct.pack_into('>III', ram, 0x7f0e, head, head, renderer)
        for index in range(depth):
            address = OLDEST-16*index
            descriptor = menu_address if index == depth-1 else 0x93e0
            count = {0x93e0:6,0x958a:10,0x978a:10,0x99ee:15}[descriptor]
            choice = selected if index == depth-1 and selected is not None else 2 if descriptor in (0x958a,0x978a) else 0
            target = 17 if descriptor == 0x99ee else 12
            at = address-RAM_BASE
            struct.pack_into('>I',ram,at,descriptor)
            ram[at+4] = (target if height is None else height) if index == depth-1 else 12
            ram[at+5] = 0
            ram[at+6:at+16] = bytes((count,choice,choice,4+index*3,8+index,24,target,3,pending if index == depth-1 else 255,0))
        return ram

    for kind, descriptor, depth, renderer in itertools.product(('menu','control'), (0x93e0,0x958a,0x978a,0x99ee), (1,2), (0x3650,0x9332)):
        target = 17 if descriptor == 0x99ee else 12
        for mode, height, pending in ((1,0,255),(1,target-1,255),(0,target,0),(0,target,3),(0,target,5),(0,target,255),(2,0,255),(2,target,255)):
            compare(native_menu(descriptor,mode,height,pending,renderer,depth),0x100f5c,'direct-dispatch-open-actions-close',kind=kind)
    for pending, request, gate in itertools.product((0,1,2,3,128,255),(0,2,8,10),(0,2)):
        ram = fixture(pending=pending,request=request)
        ram[0xf000] = gate
        ram[0x7def] = 255 if pending&1 else 0
        compare(ram,0x100f5c,'unified-inactive-pending-gates',kind='control')
    for active, request, held, repeat in itertools.product((1,2,3),(0,1,2,4,8),(0,1,4),(0,1,15)):
        ram = fixture(active=active,request=request)
        ram[0x4cb4],ram[0x7df2],ram[0x7df3] = held,repeat,(0,49,255)[repeat%3]
        compare(ram,0x100f5c,'unified-wait-step-repeat-start',kind='control')
    for request in (0,2,8,128):
        ram = fixture(request=request)
        ram[0xfd82] = ram[0xf002] = 1
        ram[0x4cb4] = 16
        compare(ram,0x100f5c,'selector-full-d1-byte-mutation',kind='control')
    for kind, selected in itertools.product(('menu','control','caller'),(4,5)):
        ram = native_menu(selected=selected,pending=3)
        struct.pack_into('>H',ram,0x8f4,0)
        ram[0x901],ram[0x950] = 0,255
        compare(ram,0x100f5c,'restart-or-bios-boundary',kind=kind)
    isolated = len(rows)

    for child, palette_pending, stack in ((2, 0, 0x1feffc), (3, 128, 0x1f8000)):
        address, ram = 0x100f5c, fixture(pending=3, palette_pending=palette_pending)
        label, begin = 'carried-native-child-%d-pending-%d' % (child, palette_pending), len(rows)
        registers = (0xabcdff6b, 0xdeadffff)

        def tick(request=0, first=0, held=0):
            nonlocal ram, registers
            ram[0x4cb5], ram[0x4cba], ram[0x4cc0], ram[0x4cb4] = request, first, 0, held
            ram, registers = compare(ram, address, 'whole-native-chain-carry', stack=stack, sequence=label, register_inputs=registers)

        def open_menu():
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12], 'big') - RAM_BASE
                if ram[0x7f1b] == 0 and ram[head + 4] >= ram[head + 12]:
                    return
            raise ValueError('Carried native menu failed to open')

        tick()
        for _ in range(20):
            tick(held=1)
        tick(2)
        open_menu()
        for _ in range(child):
            tick(first=2)
        tick(first=16)
        head = int.from_bytes(ram[0x7f0e:0x7f12], 'big')
        descriptor = int.from_bytes(ram[head - RAM_BASE:head - RAM_BASE + 4], 'big')
        if head != OLDEST - 16 or descriptor != (0x958a, 0x978a)[child - 2]:
            raise ValueError('Native chain failed to push selected stage child')
        open_menu()
        for first in (2, 4, 8, 16):
            tick(first=first)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]:
                break
        else:
            raise ValueError('Native chain stage choice failed full close')
        tick()  # Inactive idle: resumed caller counter path.
        tick(2)  # Reactivate from the complete caller output.
        if not ram[0x7df0] or ram[0x7dee]:
            raise ValueError('Native chain failed reactivation')
        tick(2)
        open_menu()
        tick(2)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]:
                break
        else:
            raise ValueError('Reactivated native chain failed second full close')
        sequences.append({'label': label, 'frames': len(rows) - begin,
                          'resume_reactivation_and_second_exit_asserted': True, 'cpp_ram_full_d1_d3_outputs_carried': True, 'kind': 'caller'})

    for kind, child, renderer in itertools.product(('menu','control'),(2,3),(0x3650,0x9332)):
        ram = native_menu(mode=1,height=0,renderer=renderer) if kind == 'menu' else fixture(pending=3)
        registers = (0xabcdff6b,0xdeadffff)
        label = kind+'-cpp-register-child-'+str(child)+'-renderer-'+hex(renderer)
        begin = len(rows)
        def tick(request=0,first=0,held=0):
            nonlocal ram,registers
            ram[0x4cb5],ram[0x4cba],ram[0x4cc0],ram[0x4cb4] = request,first,0,held
            ram,registers = compare(ram,0x100f5c,'cpp-register-ram-lifecycle',sequence=label,register_inputs=registers,kind=kind)
        if kind == 'control':
            tick()
            for _ in range(16): tick(held=1)
            tick(2)
            struct.pack_into('>I',ram,0x7f16,renderer)
        def open_menu():
            for _ in range(64):
                tick()
                head = int.from_bytes(ram[0x7f0e:0x7f12],'big')-RAM_BASE
                if ram[0x7f1b] == 0 and ram[head+4] >= ram[head+12]: return
            raise ValueError('Carried menu failed to open: '+label)
        open_menu()
        for _ in range(child): tick(first=2)
        tick(first=16)
        open_menu()
        for first in (2,4,8,16): tick(first=first)
        for _ in range(64):
            tick()
            if not ram[0x7df0] and not ram[0x7dee]: break
        else: raise ValueError('Carried full controller exit failed: '+label)
        sequences.append({'label':label,'kind':kind,'frames':len(rows)-begin,'cpp_ram_full_d1_d3_outputs_carried':True,'full_exit_asserted':True})

    # A startup already mutates menu/video RAM before caller palette preparation
    # discovers the absent ID. Publishing must remain atomic across the chain.
    ram = fixture(active=1, request=2, palette_pending=0)
    ram[0x100f5c - RAM_BASE + 0x84] = 1
    struct.pack_into('>HH', ram, 0x4d92 + 10, 0xfffe, 0xfffe)
    ram[0x4d92 + 15] = 0x80
    inp.write_bytes(ram)
    for existing in (False, True):
        sentinels = (b'previous-chain-ram', b'previous-chain-ports')
        for path, sentinel in zip((out, ports), sentinels):
            if existing:
                path.write_bytes(sentinel)
            else:
                path.unlink(missing_ok=True)
        result = subprocess.run(arguments(0x100f5c, 0xff6b, 0xffff, 0x1feffc, (0xabcdff6b, 0xdeadffff)),
                                capture_output=True, text=True)
        if result.returncode == 0:
            raise ValueError('Late missing palette ID accepted')
        for path, sentinel in zip((out, ports), sentinels):
            if (existing and (not path.exists() or path.read_bytes() != sentinel)) or (
                    not existing and path.exists()):
                raise ValueError('Late caller-chain failure modified outputs')
        negatives.append({'failure': 'late-palette-id-after-menu-startup', 'existing_outputs': existing,
            'outputs_preserved': True, 'stderr': result.stderr.strip(), 'original_executed': False})
    sentinel = b'prior-control-register-output\0\xff'
    def reject(kind,label,ram,command=None):
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports.write_bytes(sentinel)
        actual = subprocess.run(command or arguments(0x100f5c,0x603,0x7000,0x1feffc,kind=kind),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes() == sentinel and ports.read_bytes() == sentinel,(kind,label,actual.stdout,actual.stderr)
        negatives.append({'kind':kind,'failure':label,'outputs_preserved':True,'original_executed':False})
    for kind in ('menu','control','caller'):
        for register in (2,3):
            for invalid in ('-1','4294967296','0x100000000','0x','1x',''):
                command = arguments(0x100f5c,0x603,0x7000,0x1feffc,kind=kind)
                command[register] = invalid
                reject(kind,'invalid-register',native_menu(),command)
        for index in ((11,12) if kind == 'caller' else (9,10)):
            command = arguments(0x100f5c,0x603,0x7000,0x1feffc,kind=kind)
            command[index] = '1'
            reject(kind,'inconsistent-lowword',native_menu(),command)
        for size in (0,65535,65537): reject(kind,'invalid-ram-size',bytes(size))
        ram = native_menu(mode=2,height=0,exit_word=1)
        struct.pack_into('>I',ram,0x7df6,0xdeadbeef)
        reject(kind,'unsupported-late-callback',ram)
        for alias_kind in ('same','hardlink','symlink'):
            ram = native_menu()
            inp.write_bytes(ram)
            ports.write_bytes(sentinel)
            alias = inp if alias_kind == 'same' else folder/(kind+'-'+alias_kind+'.bin')
            if alias_kind != 'same':
                alias.unlink(missing_ok=True)
                if alias_kind == 'hardlink': alias.hardlink_to(inp)
                else: alias.symlink_to(inp)
            command = arguments(0x100f5c,0x603,0x7000,0x1feffc,kind=kind)
            command[8 if kind == 'caller' else 7] = str(alias)
            actual = subprocess.run(command,capture_output=True,text=True)
            assert actual.returncode and inp.read_bytes() == ram and ports.read_bytes() == sentinel
            negatives.append({'kind':kind,'failure':'input-output-'+alias_kind+'-alias','outputs_preserved':True,'original_executed':False})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Original fixed ROM changed')
    if bytes(cpu.mem_read(0x200000, 0xffff0)) != program[0x200000:0x2ffff0]:
        raise ValueError('Original palette ROM bank changed outside PVC tail')
    hook_counts = {hex(address): sum(item['address'] == address for row in rows
                   for item in row['actual_trace']) for address in HOOKS}
    if not all(hook_counts[hex(address)] for address in HOOKS if address not in (0x4718,0x479e,0x4c40,0x504c)):
        raise ValueError('Native caller-chain hook coverage missing: ' + repr(hook_counts))
    stage_calls = [item for row in rows for item in row['actual_trace']
                   if item['address'] in (0x9602, 0x9802)]
    stage_stack_deltas = {row['entry_stack'] - item['a7'] for row in rows
        for item in row['actual_trace'] if row['kind'] == 'caller' and item['address'] in (0x9602, 0x9802)}
    if stage_stack_deltas != {12, 16, 32}:
        raise ValueError('Stage callback stack depths lost real f54 outer return: ' +
                         repr(stage_stack_deltas))
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False, 'entry_cpu_address': ENTRY,
        'entry_rom_offset': ENTRY, 'address_mapping': 'Fixed ROM addresses equal decrypted '
            'offsets; observed palette bank CPU200000..2ffff0 maps same decrypted offsets.',
        'native_resource_sha256': hashes, 'stage_group_resource_sha256': [group['sha256'] for group in groups],
        'cases': len(rows), 'isolated_cases': isolated, 'actual_hook_counts': hook_counts,
        'whole_65536_byte_ram_equal': True, 'ordered_video_watchdog_pvc_ports_equal': True,
        'boundary_signed_status_line_full_d1_full_d3_equal': True, 'entry_cpu_addresses': [0x92fc, 0x9136, 0xf54], 'cases_by_kind': {kind: sum(row['kind']==kind for row in rows) for kind in ('menu','control','caller')}, 'caller_a6_preserved_asserted_at_f5a': True,
        'caller_stack_restored_at_f5a': True, 'controller_outer_return_stack_bytes': 4,
        'actual_stage_callback_stack_deltas': sorted(stage_stack_deltas),
        'stage_callback_outer_return_depth_asserted': True,
        'actual_stage_callback_calls': len(stage_calls), 'bios_skips_caller_asserted': True,
        'output_carry_sequences': sequences, 'negative_cases': len(negatives),
        'negative_results': negatives, 'late_failure_outputs_preserved': True,
        'ordered_port_events': sum(row['port_events'] for row in rows), 'results': rows,
        'scope': 'Unmodified f54 JSR9136 through f5a caller helpers, stopping before ec4 '
            'loop or fee TRAP15 execution, normal RTS, or BIOS c00444 transfer. Controller '
            'uses the real outer return stack and preserves caller A6. WholeRAM and all '
            'ordered video/watchdog/PVC writes compared; carried activation/wait/held '
            'steps/stage children/full close/resume/reactivation cycles. Host supplies '
            'input bytes between calls; carried full D1/D3 are actual CLI outputs. Native 92fc and unified9136 paths also compared. ec4 loop implementation, '
            'natural input collection, physical device timing, trap handler, other CPU '
            'registers except D1/D3, flags, external stack memory and full boot excluded. Initial RAM menu slots are explicit host fixtures, not validated startup outputs. Unified-control carried sequences change RAM7f16 once after native startup to select the tested renderer; that renderer change is an explicit host fixture action.'}, indent=2) + '\n')
    print('Native control caller chain original/C++ match:', len(rows), 'cases;',
          len(sequences), 'carried lifecycles;', len(negatives), 'late failures;', hook_counts)


if __name__ == '__main__':
    main()
