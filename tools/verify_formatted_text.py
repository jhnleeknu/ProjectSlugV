"""Compare formatter3a70 full RAM and ordered ports with original M68000 execution."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2,
                               UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_PC, UC_M68K_REG_SR)
from disassemble_program import load_verified_program
from verify_menu_event import SOURCE_SHA256
from verify_object_reset import make_cpu

RAM_BASE = 0x100000
RAM_SIZE = 0x10000
MEMORY_BASE = 0x60000
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
    folder = root / 'artifacts/formatted_text'
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

    def compare(format_data, arguments=(), cursor=0x7088, style=3,
                label='format', source_format_address=None, arguments_in_ram=False):
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
        initial_ram = bytes(ram)
        input_path.write_bytes(initial_ram)
        resource_path.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1,
                                             MEMORY_BASE, MEMORY_BASE, len(memory),
                                             zlib.crc32(memory), 0) + memory)
        cpu.mem_write(MEMORY_BASE, bytes(memory))
        cpu.mem_write(RAM_BASE, initial_ram)
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        for register, value in ((UC_M68K_REG_A0, MEMORY_BASE),
                                (UC_M68K_REG_A1, 0xe84c8),
                                (UC_M68K_REG_A2, ARGUMENT_TABLE),
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
        result = subprocess.run([str(root / 'build/format_text'), str(input_path),
                                 str(output_path), str(resource_path), str(font),
                                 str(MEMORY_BASE), str(ARGUMENT_TABLE), str(cursor),
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
        if not arguments:
            start = FORMAT_STATE - RAM_BASE + 18
            if expected_ram[start:start+4] != initial_ram[start:start+4]:
                raise ValueError('No-argument call altered reserved prior pointer: ' + label)
        row = {'label': label, 'initial_cursor': cursor, 'initial_style': style,
               'argument_count': len(arguments), 'format_hex': format_data.hex(),
               'argument_storage': 'RAM' if arguments_in_ram else 'MS5D',
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

    stage_name_count = 0
    for group, address in enumerate(struct.unpack_from('>19I', program, 0x474f4)):
        position, record_index = address + 2, 0
        while True:
            length = struct.unpack_from('>h', program, position)[0]
            position += 2
            if length == 0:
                break
            if length < 20 or length & 1 or position + length > 0x100000:
                raise ValueError('Original stage record violates catalog constraints')
            name_address = position + 18
            data = program[name_address:position+length]
            if 0 not in data:
                raise ValueError('Stage name lacks terminator')
            compare(b'\\c0%1x:%2x %s\0', (bytes([group]), bytes([record_index]), data),
                    label='stage-name-%02d-%02d' % (group, record_index),
                    source_format_address=0x955e)
            rows[-1].update(source_name_cpu_address=name_address,
                            source_name_rom_offset=name_address)
            position += length
            record_index += 1
            stage_name_count += 1
    if stage_name_count != 59:
        raise ValueError('Expected 59 actual stage record names')
    report_path.write_text(json.dumps({
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'entry_cpu_address': 0x3a70,
        'renderer_cpu_address': 0xe84c8, 'ram_cpu_base': RAM_BASE,
        'ram_size': RAM_SIZE, 'fixture_cpu_base': MEMORY_BASE,
        'argument_table_cpu_address': ARGUMENT_TABLE,
        'font_resource_sha256': hashlib.sha256(packed_font).hexdigest(),
        'font_resource_matches_original_slice': True,
        'cases': len(rows), 'stage_name_count': stage_name_count,
        'all_full_ram_and_ordered_ports_equal': True, 'results': rows,
        'scope': 'Unmodified original3a70/3950/396e/386e/37e2/e84c8/3650 execution; '
                 'all64KiB RAM bytes and video-port write address, size, value and order. '
                 'Literal percent, default/fixed-width strings, raw numeric operands at '
                 'odd/even widths1..8, zero padding, style/control changes, cursor wrapping, '
                 'empty strings, zero-prefixed string widths, long-string counter byte '
                 'wrapping at256/512, width65537 word wrapping, RAM/resource operands, '
                 'native955e/9781 formats and59 actual stage names. Random initial RAM checks '
                 'preservation, including prior pointer at state+18..21 on no-argument calls. '
                 'Null string pointers, malformed formats, other fonts, CPU flags/register '
                 'equivalence, final pixels and hardware timing remain outside scope.'
    }, indent=2) + '\n')
    print('Formatted text original/C++ match:', len(rows), 'full-RAM/port cases;',
          stage_name_count, 'actual stage names')


if __name__ == '__main__':
    main()
