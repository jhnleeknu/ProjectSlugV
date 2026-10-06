"""Execute the original f5a controller-result consumer up to its loop/return/trap boundary."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A5, UC_M68K_REG_A6,
    UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3,
    UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, OBJECT, STACK, RETURN = 0x100000, 0x100100, 0x1feffc, 0xff000
HELPERS = (0x3db2, 0x3d7e, 0x8bbc, 0x8bc8, 0x8c16, 0x5728, 0x8be0, 0x43dbc)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    folder = root / 'artifacts/control_caller'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'analysis.json'
    path.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x300000, 0x1000)
    cpu.mem_map(0x3c0000, 0x1000)
    calls, writes, rows = [], [], []

    def code_hook(cpu, address, size, user):
        if address in (0xec4, 0xfee):
            cpu.emu_stop()
        else:
            calls.append(address)

    def write_hook(cpu, access, address, size, value, user):
        if address == 0x300001 or 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (size * 8)) - 1)))

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    for address in HELPERS + (0xec4, 0xfee):
        cpu.hook_add(UC_HOOK_CODE, code_hook, begin=address, end=address)
    for status, previous, flag, disabled, count, mismatch, saved_timer in itertools.product(
            (0, 1, 2, 255), (0, 1, 2, 255), (0, 255), (False, True),
            (0, 65535), (False, True), (0, 4)):
        ram = bytearray(hashlib.shake_256(b'ms5-caller-f5a:' +
            len(rows).to_bytes(4, 'big')).digest(65536))
        ram[0x184], ram[0x180] = previous, flag
        struct.pack_into('>H', ram, 0x182, (0, 1, 256, 65535)[len(rows) % 4])
        struct.pack_into('>H', ram, 0x17e, count)
        struct.pack_into('>H', ram, 0x0e, count ^ int(mismatch))
        ram[0x4d90] = (0, 1, 127, 255)[len(rows) % 4]
        ram[0x4d91] = 0x95 | (8 if disabled else 0)
        struct.pack_into('>HHHHHHHHH', ram, 0x7dc2,
            0x1234, 0xff80, 0x0304, 0x0200, 0xfe00, 0x0010, 0x0040, 0xffc0, 0x0001)
        ram[0x7dd4] = 0
        ram[0x7de8] = saved_timer
        ram[0x7ded] = 128  # Exercise real5728; stop preparation at its original gate.
        ram[0xd494] = len(rows) & 255
        incoming = 0xa5b6c700 | status
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((UC_M68K_REG_SR, 0x2000), (UC_M68K_REG_A5, 0x108000),
                (UC_M68K_REG_A6, OBJECT), (UC_M68K_REG_A7, STACK),
                (UC_M68K_REG_D0, incoming), (UC_M68K_REG_D1, 0x11223344),
                (UC_M68K_REG_D3, 0x55667788)):
            cpu.reg_write(reg, value)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        calls.clear()
        writes.clear()
        cpu.emu_start(0xf5a, RETURN, count=200000)
        pc = cpu.reg_read(UC_M68K_REG_PC)
        expected_pc = 0xec4 if status == 0 else 0xfee if mismatch else RETURN
        if pc != expected_pc:
            raise ValueError('Unexpected consumer boundary: ' + hex(pc))
        result = bytes(cpu.mem_read(BASE, 65536))
        expected_calls = []
        if status == 0:
            if previous != 0:
                expected_calls += [0x3db2, 0x3d7e]
            if previous == 1:
                expected_calls += [0x8bbc, 0x8bc8, 0x8c16]
            expected_calls += [0x5728]
        else:
            if previous == 0:
                expected_calls += [0x3d7e]
                if flag:
                    expected_calls += [0x8be0]
            if not mismatch:
                expected_calls += [0x43dbc]
        if calls != expected_calls or result[0x184] != status:
            raise ValueError('Low-byte transition or actual helper order differs')
        should_advance = status != 0 and not mismatch
        counter = (count + int(should_advance)) & 65535
        global_counter = counter if should_advance else count ^ int(mismatch)
        if struct.unpack_from('>H', result, 0x17e)[0] != counter or \
                struct.unpack_from('>H', result, 0x0e)[0] != global_counter:
            raise ValueError('Counter equality gate/wrap differs')
        phase = (ram[0xd494] & 1) + 1 if should_advance else ram[0xd494]
        if result[0xd494] != phase:
            raise ValueError('Position update phase differs')
        video_writes = [w for w in writes if w[1] == 0x3c0006]
        expected_video = []
        if status == 0 and previous != 0:
            query = 0 if disabled else ram[0x4d90] + 1
            if struct.unpack_from('>H', result, 0x182)[0] != query:
                raise ValueError('Saved video-control query differs')
            expected_video = [(2, 0x3c0006, ram[0x4d91] | 8)]
        elif status != 0 and previous == 0:
            value = struct.unpack_from('>H', ram, 0x182)[0]
            word = (ram[0x4d91] | 8) if value == 0 else \
                (((value - 1) & 255) << 8) | (ram[0x4d91] & 247)
            expected_video = [(2, 0x3c0006, word)]
        if video_writes != expected_video:
            raise ValueError('Video control port differs')
        if expected_video and struct.unpack_from('>H', result, 0x4d90)[0] != expected_video[0][2]:
            raise ValueError('Video control shadow word differs')
        if status == 0 and previous == 1:
            if result[0x7dd6:0x7dea] != ram[0x7dc2:0x7dd6] or result[0x180] != 255 or result[0x7dec] != 0:
                raise ValueError('Palette save/flag transition differs')
            if result[0x7dc8:0x7dce] != b'\xfc\x00' * 3 or result[0x7dd4] != 3:
                raise ValueError('Palette target or immediate first tick differs')
        elif status != 0 and previous == 0 and flag:
            restored = bytearray(ram[0x7dd6:0x7dea])
            if saved_timer == 0:
                restored[18] = 1
                for index in (0, 2, 4):
                    restored[index] = ram[0x7dc2 + index]
            if result[0x7dc2:0x7dd6] != restored or result[0x180] != 0:
                raise ValueError('Palette restoration transition differs')
        rows.append({'incoming_d0': incoming, 'previous_status': previous,
            'restore_flag': flag, 'video_disabled': disabled, 'counter': count,
            'counter_mismatch': mismatch, 'saved_timer': saved_timer,
            'boundary_cpu_address': pc, 'actual_helpers': calls.copy(),
            'ordered_ports': writes.copy(), 'input_sha256': hashlib.sha256(ram).hexdigest(),
            'output_ram_sha256': hashlib.sha256(result).hexdigest()})
    if bytes(cpu.mem_read(0, 0x100000)) != program[:0x100000]:
        raise ValueError('Mapped original program changed')
    report = {'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'entry_cpu_address': 0xf5a, 'entry_rom_offset': 0xf5a, 'cases': len(rows),
        'program_code_modified': False,
        'boundary_counts': {hex(pc): sum(r['boundary_cpu_address'] == pc for r in rows)
                            for pc in (0xec4, 0xfee, RETURN)},
        'scope': 'Original consumer after9136 return. Actual helpers execute without patches. '
            'Assertions cover low-byte routing, helper order, video shadow/port, palette save/restore, '
            'effect target/first tick, equality trap boundary, counter wrap and phase. '
            'Palette preparation is deferred with7ded bit7; full RAM hashes are observations, '
            'not an independent full-RAM model comparison. ec4 loop and trap handler stop before '
            'execution. Whole caller C++, natural entry, full game scheduling and timing remain unverified.',
        'results': rows}
    path.write_text(json.dumps(report, indent=2) + '\n')
    print('Original controller caller:', len(rows), 'cases;', report['boundary_counts'])


if __name__ == '__main__':
    main()
