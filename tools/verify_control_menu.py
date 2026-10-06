"""Compare the resource parser with original item indexing and callback dispatch."""
import json
from pathlib import Path
import subprocess
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A2, UC_M68K_REG_A3,
                               UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_D3, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from pack_control_menu import extract, MENU
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    expected, pointers = extract(program)
    result = subprocess.run([str(root / 'build/check_menu'),
                             str(root / 'extracted/runtime/control_menu.ms5d'), hex(MENU)],
                            check=True, capture_output=True, text=True)
    parsed = json.loads(result.stdout)
    if parsed != expected:
        raise ValueError('C++ descriptor differs from source fields: ' + repr(parsed))
    cpu = make_cpu(program)
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    rows = []
    for index, item in enumerate(parsed['items']):
        ram = bytearray(65536)
        ram[0x7f12:0x7f16] = (0x107efe).to_bytes(4, 'big')
        ram[0x7efe:0x7f02] = MENU.to_bytes(4, 'big')
        ram[0x7f06] = index  # entry +8 is the original selection used by9b26
        cpu.mem_write(0x100000, bytes(ram))
        call(cpu, 0x9b26)
        if cpu.reg_read(UC_M68K_REG_A3) != item['source_cpu_address']:
            raise ValueError('Original item index mismatch')
        for event in (0, 3, 7, 65535):
            cpu.reg_write(UC_M68K_REG_D0, event)
            cpu.reg_write(UC_M68K_REG_D1, 0xbeefaaaa)
            cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
            cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
            # Stop at callback entry: validate dispatch, do not claim its effects.
            cpu.emu_start(0x9b3e, item['callback'], count=1000)
            if (cpu.reg_read(UC_M68K_REG_PC) != item['callback'] or
                    cpu.reg_read(UC_M68K_REG_D0) != event or
                    cpu.reg_read(UC_M68K_REG_D1) != (0xbeef0000 | item['argument']) or
                    cpu.reg_read(UC_M68K_REG_A3) != item['source_cpu_address'] or
                    bytes(cpu.mem_read(0x100000, 65536)) != ram):
                raise ValueError('Original callback dispatch mismatch')
        rows.append({'index': index, 'callback': item['callback'], 'events': 4})
    texts = []
    for pointer in pointers:
        cpu.reg_write(UC_M68K_REG_A0, pointer)
        cpu.reg_write(UC_M68K_REG_D1, 0)
        cpu.reg_write(UC_M68K_REG_D3, 0x7000)
        call(cpu, 0x38e8)
        end = cpu.reg_read(UC_M68K_REG_A0)
        if not pointer < end <= MENU:
            raise ValueError('Original text traversal outside resource')
        texts.append({'source_cpu_address': pointer, 'end_cpu_address': end,
                      'original_glyph_count': cpu.reg_read(UC_M68K_REG_D0) & 65535})
    folder = root / 'artifacts/control_menu'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'verification.json').write_text(json.dumps({
        'source': source, 'descriptor': parsed, 'index_cases': len(rows),
        'dispatch_cases': len(rows) * 4, 'items': rows, 'texts': texts,
        'scope': 'Native MS5D C++ parser plus original item selection/dispatch to callback entry. '
                 'Text extent measured by original 38e8. Callback behavior and menu rendering unverified.'
    }, indent=2) + '\n')
    print('Menu resource matches:', len(rows), 'indices;', len(rows) * 4, 'dispatches;', len(texts), 'text extents')


if __name__ == '__main__':
    main()
