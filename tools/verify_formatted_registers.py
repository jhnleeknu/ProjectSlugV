"""Compare native formatter RAM/ports and full D1/D3 without modifying ROM."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

BASE, FORMAT, ARGUMENTS, RETURN = 0x100000, 0x108000, 0x106000, 0xff000


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    font = root / 'extracted/runtime/menu_fonts.ms5d'
    resource = root / 'extracted/runtime/main_debug.ms5d'
    font_hash = checked_resource(font, program, 0xe80c8, 0xe84c8)
    resource_hash = checked_resource(resource, program, 0xd56, 0xe40)
    executable = root / 'build/format_text'
    folder = root / 'artifacts/formatted_registers'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x3c0000, 0x1000)
    writes, rows, negative_rows = [], [], []

    def write_hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            writes.append((size, address, value & ((1 << (8 * size)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536 or
                  0x1fe000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native formatter write: ' + hex(address))

    def return_hook(cpu, address, size, user):
        cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.hook_add(UC_HOOK_CODE, return_hook, begin=RETURN, end=RETURN)

    def fixture(data, arguments, label):
        ram = bytearray(hashlib.shake_256(b'ms5-format-registers:' + label.encode()).digest(65536))
        assert len(data) <= 0x400
        ram[FORMAT - BASE:FORMAT - BASE + len(data)] = data
        for index, argument in enumerate(arguments):
            address = FORMAT + 0x400 + index * 0x800
            assert len(argument) <= 0x800 and index < 7
            ram[address - BASE:address - BASE + len(argument)] = argument
            struct.pack_into('>I', ram, ARGUMENTS - BASE + index * 4, address)
        return ram

    def arguments_for(renderer, cursor, style, d1, d3, reverse=False, registers=True):
        options = ['--renderer', hex(renderer)]
        if registers:
            reg_options = ['--registers', str(d1), str(d3)]
            options = options + reg_options if reverse else reg_options + options
        return [str(executable), *options, str(inp), str(out), str(resource), str(font),
                str(FORMAT), str(ARGUMENTS), str(cursor), str(style), str(ports_out)]

    def compare(data, arguments, label, renderer, d1, d3, cursor, registers=True):
        ram = fixture(data, arguments, label)
        cpu.mem_write(BASE, bytes(ram))
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in ((m68k_const.UC_M68K_REG_A0, FORMAT),
                           (m68k_const.UC_M68K_REG_A1, renderer),
                           (m68k_const.UC_M68K_REG_A2, ARGUMENTS),
                           (m68k_const.UC_M68K_REG_A5, 0x108000),
                           (m68k_const.UC_M68K_REG_A7, 0x1feffc),
                           (m68k_const.UC_M68K_REG_D0, cursor),
                           (m68k_const.UC_M68K_REG_D1, d1),
                           (m68k_const.UC_M68K_REG_D3, d3)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        writes.clear()
        try:
            cpu.emu_start(0x3a70, 0xffffff, count=2000000)
        except unicorn.UcError as error:
            raise ValueError('Native formatter failure: ' + repr((len(rows), label,
                hex(renderer), hex(d1), hex(d3), hex(cursor),
                hex(cpu.reg_read(m68k_const.UC_M68K_REG_PC))))) from error
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN
        expected_ram = bytes(cpu.mem_read(BASE, 65536))
        expected_ports = b''.join(struct.pack('>BII', *write) for write in writes)
        expected_registers = {'d1': cpu.reg_read(m68k_const.UC_M68K_REG_D1) & 0xffffffff,
                              'd3': cpu.reg_read(m68k_const.UC_M68K_REG_D3) & 0xffffffff}
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        ports_out.unlink(missing_ok=True)
        reverse = bool(len(rows) & 1)
        result = subprocess.run(arguments_for(renderer, cursor, d1 & 65535, d1, d3,
                                              reverse, registers), capture_output=True, text=True)
        parsed = json.loads(result.stdout) if registers and result.returncode == 0 else None
        if result.returncode or not out.exists() or out.read_bytes() != expected_ram or not ports_out.exists() or ports_out.read_bytes() != expected_ports or (registers and parsed != expected_registers) or (not registers and result.stdout):
            actual = out.read_bytes() if out.exists() else b''
            differences = [(hex(at), expected_ram[at], actual[at]) for at in
                           range(min(len(actual), 65536)) if actual[at] != expected_ram[at]]
            raise ValueError('Formatted registers mismatch: ' + repr((len(rows), label,
                hex(renderer), hex(d1), hex(d3), hex(cursor), differences[:12],
                expected_registers, parsed, result.returncode, result.stderr)))
        rows.append({'profile': label, 'renderer_cpu_address': renderer,
            'initial_d1': d1, 'initial_d3': d3, 'cursor': cursor,
            'options_renderer_first': reverse, 'register_reporting': registers,
            'actual_native_final_registers': expected_registers, 'argument_count': len(arguments),
            'format_hex': data.hex(), 'argument_hex': [argument.hex() for argument in arguments],
            'port_events': len(writes), 'input_sha256': hashlib.sha256(ram).hexdigest(),
            'ram_sha256': hashlib.sha256(expected_ram).hexdigest(),
            'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})

    profiles = (
        ('empty', b'\0', ()),
        ('literal', b'ABC 123\0', ()),
        ('literal-percent', b'A%%B\0', ()),
        ('terminal-newline', b'ABC\\n\0', ()),
        ('terminal-line', b'ABC\\l\x03\x05\0', ()),
        ('line-zero-operands', b'\\l\0\0A\0', ()),
        ('line-then-newline', b'\\l\x03\x05A\\nB\0', ()),
        ('terminal-color', b'A\\ck\0', ()),
        ('terminal-palette', b'A\\p\x0f\0', ()),
        ('literal-controls', b'\\chA\\nB\\rC\\p\x02D\\l\x01\x02E\0', ()),
        ('string-literal', b'[%s]\0', (b'A\0',)),
        ('string-terminal-line', b'%s\0', (b'A\\l\x02\x07\0\0',)),
        ('string-line-following-literal', b'%sZ\0', (b'A\\l\x02\x07B\0',)),
        ('string-terminal-newline', b'%s\0', (b'A\\n\0\0',)),
        ('string-terminal-color', b'%s\0', (b'A\\ch\0\0',)),
        ('string-percent-not-nested-format', b'%s\0', (b'%s\\l\x01\x02X\0',)),
        ('width-three-string', b'%03s!\0', (b'AB\0',)),
        ('mixed-hex-widths', b'%1x:%02x:%4x:%08x\0',
         (b'\x0a', b'\x01', b'\x12\x34', b'\x12\x34\x56\x78')),
        ('hex-then-line', b'%03x\\l\x04\x06\0', (b'\x01\xab',)),
    )
    for (label, data, operands), renderer, d1, d3, cursor in itertools.product(profiles,
            (0x3650, 0xe84c8), (3, 0x12340068, 0xffff0f6b, 0xdead0f30),
            (0xaaaa, 0x24681234, 0xfffffff0), (0x7088, 0xffff)):
        # Native string parser traps when newline advances a cursor >= 0x7500.
        # Compare returning paths here; other profiles retain wrapped cursors.
        if label == 'string-terminal-newline' and cursor == 0xffff:
            cursor = 0x70a8
        compare(data, operands, label, renderer, d1, d3, cursor)
    for renderer in (0x3650, 0xe84c8):
        compare(b'A\\n\0', (), 'legacy-empty-stdout', renderer, 3, 0, 0x7088, False)

    sentinel = b'previous-formatted-register-output\0\xff'
    def reject(label, data=b'A\0', reg_options=None, style=3, renderer=0x3650,
               operands=(), cursor=0x7088):
        ram = fixture(data, operands, label)
        # Put truncated streams at the actual RAM boundary so random trailing
        # RAM cannot accidentally supply a valid terminator/control operand.
        pointer = FORMAT
        if label.startswith('malformed'):
            ram[-len(data):] = data
            pointer = BASE + 65536 - len(data)
        inp.write_bytes(ram)
        out.write_bytes(sentinel)
        ports_out.write_bytes(sentinel)
        options = ['--registers', '3', '0x12345678'] if reg_options is None else reg_options
        args = [str(executable), *options, '--renderer', str(renderer), str(inp), str(out),
            str(resource), str(font), str(pointer), str(ARGUMENTS), str(cursor), str(style), str(ports_out)]
        result = subprocess.run(args, capture_output=True, text=True)
        assert result.returncode and out.read_bytes() == sentinel and ports_out.read_bytes() == sentinel and inp.read_bytes() == ram, (label, result.stdout, result.stderr)
        negative_rows.append({'failure': label, 'outputs_preserved': True, 'original_executed': False})

    for data in (b'A', b'%', b'%q\0', b'\\', b'\\l\1', b'A\\l\1'):
        reject('malformed-' + data.hex(), data)
    for options in (['--registers', '-1', '0'], ['--registers', '4294967296', '0'],
                    ['--registers', '3', '4294967296'], ['--registers', '3', '-1']):
        reject('invalid-full-register-argument-' + '-'.join(options[1:]), reg_options=options)
    reject('style-inconsistent-with-d1-lowword', style=0x68)
    reject('unsupported-renderer', renderer=0x3652)
    reject('native-trap15-string-newline-unsupported', data=b'%s\0',
           operands=(b'A\\n\0',), cursor=0xffff,
           reg_options=['--registers', '3', '0xaaaa'])
    reject('duplicate-registers-option', reg_options=['--registers', '3', '0', '--registers', '3', '0'])
    reject('duplicate-renderer-option', reg_options=['--registers', '3', '0', '--renderer', '0x3650'])
    for label, options in (('missing-registers-values', ['--registers']),
                           ('missing-registers-d3', ['--registers', '3']),
                           ('missing-renderer-value', ['--renderer'])):
        reject(label, reg_options=options)
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    report.write_text(json.dumps({'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'entry_cpu_address': 0x3a70, 'entry_rom_offset': 0x3a70,
        'program_code_modified': False, 'format_fixture_cpu_address': FORMAT,
        'argument_table_cpu_address': ARGUMENTS, 'format_and_operands_in_work_ram': True,
        'font_resource_sha256': font_hash, 'fixed_resource_sha256': resource_hash,
        'renderer_cpu_addresses': [0x3650, 0xe84c8], 'cases': len(rows),
        'negative_cases': len(negative_rows), 'whole_64k_ram_and_ordered_ports_equal': True,
        'native_full_d1_d3_equal': True, 'legacy_stdout_empty': True,
        'both_register_renderer_option_orders_verified': True,
        'string_terminal_control_padding': 'Two trailing NUL bytes bound native post-renderer pointer lookahead.',
        'native_trap_exclusion': {'profile': 'string-terminal-newline',
            'format_hex': b'%s\0'.hex(), 'argument_hex': b'A\\n\0'.hex(),
            'renderer_cpu_address': 0x3650, 'initial_d1': 3, 'initial_d3': 0xaaaa,
            'cursor': 0xffff, 'trap_cpu_address': 0x38c8,
            'replacement_returning_cursor': 0x70a8},
        'negative_results': negative_rows, 'results': rows,
        'scope': 'Unmodified native 0x3a70 with actual 0x3650/0xe84c8 renderers and verified original '
            'font resource. Synthetic format, pointer tables and operands reside entirely in '
            'work RAM; fixed ROM is never patched. Full D1/D3, whole RAM and ordered ports '
            'compared across literal/terminal controls, strings containing line controls and '
            'literal percent directives, hexadecimal widths and independent cursor/D3 inputs. '
            'No nested format expansion through %s, pixels, natural call-site reachability, '
            'other CPU registers, CCR/SR or hardware timing claimed. Arbitrary trailing '
            'string memory and fault handling are outside the normal-return comparison; '
            'the known native newline TRAP #15 input is separately rejected transactionally.'}, indent=2) + '\n')
    print('Formatted registers:', len(rows), 'native/C++ cases;', len(negative_rows),
          'output-preserving rejections;', hashlib.sha256(report.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
