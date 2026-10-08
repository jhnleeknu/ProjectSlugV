"""Immutable bounded motion-pair instruction candidates and ADD operands.

No handler semantics, execution equivalence or reachability are inferred.
"""
import hashlib
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS = ((0x192c4, 0x196ac), (0x196ac, 0x1972a),
           (0x19832, 0x198ee), (0x18efa, 0x18fd2))
ADD_ADDRESSES = (0x1941a, 0x19432, 0x1944a, 0x1945e, 0x19476,
                 0x19502, 0x1951a, 0x19532, 0x19546, 0x1955e)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    windows = []
    indexed = {}
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Window gap, overlap or out-of-range row')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Instruction raw bytes/source mismatch')
            require(cursor not in indexed, 'Overlapping explicit windows')
            indexed[cursor] = row
            cursor += row['size']
        require(cursor == end, 'Incomplete exact window coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            instructions=rows, undecoded_rows=undecoded))
    operands = []
    for address in ADD_ADDRESSES:
        require(address in indexed, 'Requested ADD address is not a decoded row boundary')
        row = indexed[address]
        require(row['classification'] == 'candidate_instruction'
                and row['mnemonic'] == 'add.l' and row['op_str'] == 'd0, d3',
                'Requested literal ADD.L D0,D3 instruction changed')
        operands.append(dict(cpu_address=address, rom_offset=address,
            source_register='d0', destination_register='d3', operation_size_bits=32,
            instruction=dict(row), raw_sha256=sha(bytes.fromhex(row['raw'])),
            classification='Literal encoded ADD.L D0,D3 operands; no semantic correction'))
    require(sha(program) == SOURCE_SHA256, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        decoder='Capstone '+capstone.__version__,
        provenance='Canonical original decrypted program loaded with verified metadata and pinned SHA256 before/after read-only inventory.',
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets; RAM/MMIO distinct.',
        window_count=len(windows), instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),
        windows=windows, literal_add_operand_count=len(operands), literal_add_operands=operands,
        scope='Four main-confirmed explicit motion-pair windows using padded decoder. Every assigned byte preserved including undecoded rows and bytes after RTS; endpoints are evidence bounds, not routine completion. '
              'Ten requested ADD operand instructions retain exact original bytes and registers without semantic correction. '
              'Candidate-only decode; no branch-handler semantics, zero-axis behavior, callee effects, native/C++ execution equivalence or natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/scene_motion_pair_disassembly.json'
    listing_path = root/'artifacts/scene_motion_pair_disassembly.asm'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    listing = ['; Source SHA256 '+SOURCE_SHA256,
               '; Fixed CPU=ROM. Explicit bounded instruction candidates; no execution/reachability proof.']
    for window in report['windows']:
        listing.append('; [%06x,%06x) SHA256 %s; full assigned bounds, not firstRTS.' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        listing.append(asm(window['instructions']))
    listing.append('; Main-requested literal ADD.L D0,D3 operand evidence; no semantic correction.')
    for row in report['literal_add_operands']:
        listing.append(asm([row['instruction']]))
    listing_path.write_text('\n'.join(listing)+'\n')
    print(json.dumps(dict(windows=report['window_count'], rows=report['instruction_row_count'],
        undecoded=report['undecoded_row_count'], per_window=[dict(start_cpu_address=w['start_cpu_address'],
            rows=w['instruction_row_count'], undecoded=w['undecoded_row_count'], raw_sha256=w['raw_sha256'])
            for w in report['windows']], literal_add_operand_count=report['literal_add_operand_count'],
        report_sha256=sha(path.read_bytes()), asm_sha256=sha(listing_path.read_bytes()))))


if __name__ == '__main__':
    main()
