"""Immutable bounded original-ROM candidates for full object restart analysis.

Explicit windows are preserved through their assigned exclusive endpoints.
Decoder success is syntax evidence only, not execution or routine completion.
"""
import hashlib
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS = ((0x2a28, 0x2a48), (0x299c, 0x2a00), (0x2782, 0x2790),
           (0x8ff4, 0x9038), (0x8e4a, 0x8e82), (0x46ef4, 0x46f2e),
           (0xc3fa, 0xc402), (0x271c, 0x2782), (0x8eb6, 0x8ebe),
           (0x43dcc, 0x43e04), (0xc3dc, 0xc3fa), (0x4aa06, 0x4aa30),
           (0xe90ca, 0xe90d8), (0x46eec, 0x46ef4), (0x287e, 0x288c))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(program, source):
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source')
    windows = []
    for start, end in WINDOWS:
        require(start % 2 == 0 and end % 2 == 0 and 0 <= start < end <= 0x100000,
                'Window is not even fixed ROM')
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Window gap, overlap or out-of-range instruction')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Decoder raw bytes differ from source')
            cursor += row['size']
        require(cursor == end, 'Window coverage is incomplete')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            instructions=rows, undecoded_rows=undecoded))
    data_start = 0x30ec
    data_end = data_start+8
    data = dict(start_cpu_address=data_start, start_rom_offset=data_start,
                end_cpu_address_exclusive=data_end, end_rom_offset_exclusive=data_end,
                byte_count=data_end-data_start, raw_hex=program[data_start:data_end].hex(),
                raw_sha256=sha(program[data_start:data_end]),
                classification='Main-requested eight raw fixed-ROM lookup bytes; not decoded as code or interpreted as logical table extent.')
    require(sha(program) == SOURCE_SHA256, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, decoder='Capstone '+capstone.__version__,
        provenance='Canonical decrypted original program loaded by load_verified_program; pinned SHA256 checked before and after read-only inventory. No original ROM modification or native execution.',
        program_code_modified=False,
        mapping='Fixed first1MiB CPU addresses equal canonical ROM file offsets; RAM/MMIO addresses are distinct.',
        window_count=len(windows), instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),
        windows=windows, data_sections=[data],
        scope='Main-confirmed explicit fixed-ROM windows using the existing padded disassemble_range decoder. Candidate-only decode, including preserved undecoded rows and bytes after any RTS. Exclusive endpoints are requested evidence bounds, not routine-completion claims. No ownership, control-flow interpretation, callee semantics, C++ equivalence, native execution or natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    report = inventory(program, source)
    folder = root/'artifacts'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder/'object_restart_full_disassembly.json'
    listing_path = folder/'object_restart_full_disassembly.asm'
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    listing = ['; Canonical original source SHA256 '+SOURCE_SHA256,
               '; Fixed first1MiB CPU=ROM. Explicit bounded instruction candidates only; no native execution.']
    for window in report['windows']:
        listing.append('; Window [%06x,%06x), raw SHA256 %s; full assigned bounds, not routine completion.' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        listing.append(asm(window['instructions']))
    for data in report['data_sections']:
        listing.append('; Raw data [%06x,%06x), SHA256 %s; no field interpretation.' % (
            data['start_cpu_address'], data['end_cpu_address_exclusive'], data['raw_sha256']))
        listing.append('%06x raw=%s' % (data['start_cpu_address'], data['raw_hex']))
    listing_path.write_text('\n'.join(listing)+'\n')
    print(json.dumps(dict(windows=report['window_count'], rows=report['instruction_row_count'],
        undecoded=report['undecoded_row_count'], per_window=[dict(
            start_cpu_address=w['start_cpu_address'], end_cpu_address_exclusive=w['end_cpu_address_exclusive'],
            rows=w['instruction_row_count'], undecoded=w['undecoded_row_count'],
            raw_sha256=w['raw_sha256'], last_instruction=w['instructions'][-1]) for w in report['windows']],
        data_sections=report['data_sections'],
        report_sha256=sha(report_path.read_bytes()), asm_sha256=sha(listing_path.read_bytes()))))


if __name__ == '__main__':
    main()
