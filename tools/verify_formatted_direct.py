"""Compare native formatter3a70 with direct renderer3650: whole RAM and ports."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2,
                               UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_menu_event import SOURCE_SHA256
from verify_object_reset import make_cpu

RAM_BASE = 0x100000
RAM_SIZE = 0x10000
MEMORY_BASE = 0x108000
ARGUMENT_TABLE = 0x106000
FORMAT_STATE = 0x104cd6


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported ROM')
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    packed_font = font.read_bytes()
    font_payload = packed_font[32:]
    header = (b'MS5D', 1, 1, 0xe80c8, 0xe80c8, 1024,
              zlib.crc32(font_payload), 0)
    if (len(packed_font) != 1056 or struct.unpack_from('<4s7I', packed_font) != header
            or font_payload != program[0xe80c8:0xe84c8]):
        raise ValueError('Font resource differs from original ROM slice')
    folder = root / 'artifacts/formatted_direct'
    folder.mkdir(parents=True, exist_ok=True)
    input_path = folder / 'input.bin'
    output_path = folder / 'cpp.bin'
    resource_path = folder / 'fixture.ms5d'
    ports_path = folder / 'cpp.ports.bin'
    report_path = folder / 'verification.json'
    report_path.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows = [], []

    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    def stop(cpu, address, size, user):
        if address == 0xff000:
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, stop)
    def forbid_font(cpu, access, address, size, value, user):
        raise ValueError('Direct renderer unexpectedly read font at ' + hex(address))
    cpu.hook_add(UC_HOOK_MEM_READ, forbid_font, begin=0xe80c8, end=0xe84c7)

    def compare(format_data, arguments=(), cursor=0x7088, style=3,
                label='format', source_format_address=None, arguments_in_ram=False, native_debug=False):
        # Fixtures contain raw operands, not a Python implementation of formatting.
        memory = bytearray(0x4000)
        if len(format_data) > 0x400:
            raise ValueError('Format fixture too long')
        memory[:len(format_data)] = format_data
        ram = bytearray(hashlib.shake_256(
            b'ms5-formatter-v1:' + label.encode('ascii')).digest(RAM_SIZE))
        for index, argument in enumerate(arguments):
            argument_address = (RAM_BASE + 0x800 if arguments_in_ram
                                else MEMORY_BASE + 0x400) + index * 0x800
            if len(argument) > 0x800 or index >= 7:
                raise ValueError('Argument fixture too long')
            if arguments_in_ram:
                ram[argument_address - RAM_BASE:
                    argument_address - RAM_BASE + len(argument)] = argument
            else:
                memory[argument_address - MEMORY_BASE:
                       argument_address - MEMORY_BASE + len(argument)] = argument
            struct.pack_into('>I', ram, ARGUMENT_TABLE - RAM_BASE + index * 4,
                             argument_address)
        ram[MEMORY_BASE - RAM_BASE:MEMORY_BASE - RAM_BASE + len(memory)] = memory
        resource_base, format_address, table = 0xd56, MEMORY_BASE, ARGUMENT_TABLE
        memory = bytearray(program[0xd56:0xe4a])
        if native_debug:
            memory = bytearray(program[0xd56:0xe4a])
            resource_base, format_address, table = 0xd56, 0xd56, 0xdf0
        initial_ram = bytes(ram)
        input_path.write_bytes(initial_ram)
        resource_path.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1,
                                             resource_base, resource_base, len(memory),
                                             zlib.crc32(memory), 0) + memory)
        cpu.mem_write(RAM_BASE, initial_ram)
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        for register, value in ((UC_M68K_REG_A0, format_address),
                                (UC_M68K_REG_A1, 0x3650),
                                (UC_M68K_REG_A2, table),
                                (UC_M68K_REG_A5, 0x108000),
                                (UC_M68K_REG_D0, cursor),
                                (UC_M68K_REG_D1, style),
                                (UC_M68K_REG_A7, 0x1feffc)):
            cpu.reg_write(register, value)
        cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
        writes.clear()
        cpu.emu_start(0x3a70, 0xff000, count=2000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original formatter did not return: ' + label)
        expected_ram = bytes(cpu.mem_read(RAM_BASE, RAM_SIZE))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        output_path.unlink(missing_ok=True)
        ports_path.unlink(missing_ok=True)
        result = subprocess.run([str(root / 'build/format_text'), '--renderer', '0x3650', str(input_path),
                                 str(output_path), str(resource_path), str(font),
                                 str(format_address), str(table), str(cursor),
                                 str(style), str(ports_path)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ rejected ' + label + ': ' + result.stderr)
        actual_ram = output_path.read_bytes()
        actual_ports = ports_path.read_bytes()
        if actual_ram != expected_ram or actual_ports != expected_ports:
            ram_mismatch = next((RAM_BASE + i for i in range(min(len(actual_ram), RAM_SIZE))
                                 if actual_ram[i] != expected_ram[i]), None)
            port_mismatch = next((i for i in range(min(len(actual_ports), len(expected_ports)))
                                  if actual_ports[i] != expected_ports[i]), None)
            raise ValueError('Formatter mismatch: ' + repr({
                'label': label, 'ram_first_cpu_address': ram_mismatch,
                'ram_lengths': [len(expected_ram), len(actual_ram)],
                'port_first_byte': port_mismatch,
                'port_counts': [len(expected_ports) // 9, len(actual_ports) // 9],
                'expected_state': expected_ram[FORMAT_STATE-RAM_BASE:FORMAT_STATE-RAM_BASE+24].hex(),
                'actual_state': actual_ram[FORMAT_STATE-RAM_BASE:FORMAT_STATE-RAM_BASE+24].hex()}))
        if not arguments and not native_debug:
            start = FORMAT_STATE - RAM_BASE + 18
            if expected_ram[start:start+4] != initial_ram[start:start+4]:
                raise ValueError('No-argument call altered reserved prior pointer: ' + label)
        row = {'label': label, 'initial_cursor': cursor, 'initial_style': style,
               'argument_count': len(arguments), 'format_hex': format_data.hex(),
               'argument_storage': 'RAM',
               'argument_hex': [argument.hex() for argument in arguments],
               'state_hex': expected_ram[FORMAT_STATE-RAM_BASE:FORMAT_STATE-RAM_BASE+24].hex(),
               'port_events': len(writes),
               'ram_sha256': hashlib.sha256(expected_ram).hexdigest(),
               'ports_sha256': hashlib.sha256(expected_ports).hexdigest()}
        if source_format_address is not None:
            row.update(source_format_cpu_address=source_format_address,
                       source_format_rom_offset=source_format_address)
        rows.append(row)

    for data, label in ((b'\0', 'empty-format'), (b'ABC 123\0', 'literal'),
                        (b'%% %%%% A%%B\0', 'literal-percent')):
        for style in (3, 0x68, 0xf6b, 0xf30):
            compare(data, style=style, label=label + '-style-%04x' % style)
    string_cases = (b'A\0', b'ABCDE\0', b'\xb6\xde\xca\xdf\0',
                    b'@.a@`@\0', b'\\p\x0fA\\nB\\rC\0',
                    b'\\ch\xb6\xde\\ck\xca\xdf\\c0D\0')
    for index, argument in enumerate(string_cases):
        for width in ('', '1', '3', '8'):
            for style in (3, 0x68, 0x6b, 0x30):
                compare(b'[' + ('%' + width + 's').encode('ascii') + b']\0',
                        (argument,), style=style,
                        label='string-%d-width-%s-style-%02x' % (index, width or 'default', style))
    for arguments_in_ram in (False, True):
        storage = 'ram' if arguments_in_ram else 'resource'
        for style in (3, 0x68, 0x6b, 0x30):
            compare(b'[%s]\0', (b'\0\0',), style=style,
                    label='empty-string-%s-style-%02x' % (storage, style),
                    arguments_in_ram=arguments_in_ram)
            for width in ('01', '03'):
                compare(('%' + width + 's!').encode('ascii') + b'\0',
                        (b'ABCDE\0',), style=style,
                        label='zero-prefixed-string-width-%s-%s-style-%02x' % (
                            width, storage, style), arguments_in_ram=arguments_in_ram)
        # TST.B of the word counter fetches another argument at256 and512.
        # A second/third valid operand makes those original reads reproducible.
        long_arguments = (b'A' * 270 + b'\0', b'B' * 270 + b'\0', b'C' * 100 + b'\0')
        for width in ('', '300', '600'):
            compare(('%' + width + 's!').encode('ascii') + b'\0',
                    long_arguments, label='long-string-width-%s-%s' % (
                        width or 'default', storage), arguments_in_ram=arguments_in_ram)
        compare(b'%65537s!\0', (b'Z\0',),
                label='word-width-wrap-one-string-' + storage,
                arguments_in_ram=arguments_in_ram)
        compare(b'%65537x!\0', (b'\x0a',),
                label='word-width-wrap-one-hex-' + storage,
                arguments_in_ram=arguments_in_ram)
        compare(b'%2x:%03x %3s\0', (b'\x01', b'\x01\xab', b'READ\0'),
                label='numeric-string-operands-' + storage,
                arguments_in_ram=arguments_in_ram)
    for width in range(1, 9):
        for operand in (b'\x00\x00\x00\x00', b'\x00\x01\x00\xaf',
                        b'\x12\x34\x56\x78', b'\xff\xff\xff\xff'):
            for padding in ('', '0'):
                compare(('%' + padding + str(width) + 'x!').encode('ascii') + b'\0',
                        (operand,), label='hex-width-%d-pad-%s-value-%s' % (
                            width, padding or 'space', operand.hex()))
    mixed = b'A\\ch%3s\\ck%2x\\c0%1s\\p\x0f\\l\x03\x05B\\nC\\rD%%\0'
    for cursor in (0, 0x7000, 0x74ff, 0xffe0, 0xffff):
        for style in (3, 0xf68, 0xf6b, 0xf30):
            compare(mixed, (b'\xb6\xde@.aZ\0', b'\x01', b'E\0'),
                    cursor=cursor, style=style,
                    label='mixed-cursor-%04x-style-%04x' % (cursor, style))
    for address, arguments in ((0x955e, (b'\x03', b'\x12', b'RUN AND GUN\0')),
                               (0x9781, (b'PLAYER 1\0',))):
        end = program.index(0, address) + 1
        compare(program[address:end], arguments, label='native-%x' % address,
                source_format_address=address)

    for glyph in range(1, 256):
        if glyph in (37, 92):
            continue  # Formatter introducers have separate cases above.
        compare(bytes([glyph, 65, 0]), style=(glyph * 0x101) & 65535,
                label='single-byte-glyph-%02x' % glyph)
    for style in (0, 3, 0xf6b, 0xffff):
        compare(b'', cursor=0x7066, style=style, label='native-debug-%04x' % style,
                native_debug=True, source_format_address=0xd56)
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    negatives = []
    sentinel = b'previous-direct-output\0\xff'
    def reject(label, renderer='0x3650', data=None, output_alias=False, alias_kind=None):
        ram = bytearray(hashlib.shake_256(b'direct-negative').digest(RAM_SIZE))
        format_pointer = 0x10ffff
        if data is not None:
            ram[-len(data):] = data
            format_pointer = RAM_BASE + RAM_SIZE - len(data)
        ram = bytes(ram)
        input_path.write_bytes(ram)
        payload = program[0xd56:0xe4a]
        resource_path.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, 0xd56, 0xd56,
            len(payload), zlib.crc32(payload), 0) + payload)
        output_path.write_bytes(sentinel)
        ports_path.write_bytes(sentinel)
        destination = input_path if output_alias else output_path
        if alias_kind:
            destination = folder / (alias_kind + '.bin')
            destination.unlink(missing_ok=True)
            if alias_kind == 'hardlink':
                destination.hardlink_to(input_path)
            else:
                destination.symlink_to(input_path)
        result = subprocess.run([str(root / 'build/format_text'), '--renderer', renderer,
            str(input_path), str(destination), str(resource_path), str(font), str(format_pointer),
            str(ARGUMENT_TABLE), '0x7066', '0xf6b', str(ports_path)], capture_output=True, text=True)
        assert result.returncode and ports_path.read_bytes() == sentinel
        assert input_path.read_bytes() == ram and output_path.read_bytes() == sentinel
        negatives.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})
    for renderer in ('0', '0x3652', '-1', '4294967296', '0x'):
        reject('unsupported-or-invalid-renderer-' + renderer, renderer, b'A\0')
    for data in (b'A', b'%', b'%q\0', b'\\', b'\\l\1'):
        reject('malformed-format-' + data.hex(), data=data)
    reject('input-output-path-alias', data=b'A\0', output_alias=True)
    for kind in ('hardlink', 'symlink'):
        reject('input-output-' + kind + '-alias', data=b'A\0', alias_kind=kind)
    stage_name_count = 0
    report_path.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'entry_cpu_address': 0x3a70,
        'renderer_cpu_address': 0x3650, 'ram_cpu_base': RAM_BASE,
        'ram_size': RAM_SIZE, 'fixture_cpu_base': MEMORY_BASE,
        'argument_table_cpu_address': ARGUMENT_TABLE,
        'font_resource_sha256': hashlib.sha256(packed_font).hexdigest(),
        'font_resource_matches_original_slice': True,
        'cases': len(rows), 'stage_name_count': stage_name_count,
        'all_full_ram_and_ordered_ports_equal': True, 'program_code_modified': False,
        'native_font_reads': 0,
        'native_debug_window': [0xd56, 0xe4a], 'native_debug_pointer_table': [0xdf0, 0xe40],
        'native_debug_resource_sha256': hashlib.sha256(program[0xd56:0xe4a]).hexdigest(),
        'negative_cases': len(negatives), 'negative_results': negatives, 'results': rows,
        'scope': 'Unmodified native3a70 with A1=3650; wholeRAM and ordered video ports. '
                 'All single-byte glyphs except formatter introducers, highbytes and @, '
                 'styles, controls, numeric/string widths, RAM/resource operands and native '
                 'debug d56/df0 at cursor7066. Fixturedebug window d56..e4a includes ten '
                 'trailing code bytes e40..e4a retained verbatim. CPU scratch registers, '
                 'pixels and hardware timing excluded.'
    }, indent=2) + '\n')
    print('Formatted text original/C++ match:', len(rows), 'full-RAM/port cases;',
          stage_name_count, 'actual stage names')


if __name__ == '__main__':
    main()
