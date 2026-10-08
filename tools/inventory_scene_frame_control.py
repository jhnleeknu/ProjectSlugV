"""Explicit frame-control candidates and literal instruction evidence.

Whole assigned windows are retained; this does not execute or infer semantics.
"""
import hashlib
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import CONTROL, target
from pack_scene_scripts import SOURCE_SHA256

WINDOWS = ((0x1a29e, 0x1a3d6), (0x1a3d6, 0x1a414), (0x1a526, 0x1a5a4),
           (0x289e, 0x28ae), (0x197da, 0x19802))
DISPATCH_ENTRIES = ((0x1a2d4, 0x1a2e0), (0x1a2d8, 0x1a334), (0x1a2dc, 0x1a2f2))
LITERAL_EXPECTATIONS = ((0x1a36c, 'add.l', 'd4, d5'),
                        (0x1a38a, 'swap', 'd4'), (0x1a38c, 'swap', 'd5'),
                        (0x1a3dc, 'asr.l', '#$4, d1'), (0x1a3de, 'neg.l', 'd0'),
                        (0x1a3e0, 'add.l', 'd1, d0'),
                        (0x1a3e6, 'addi.l', '#$8000, d0'), (0x1a3ec, 'swap', 'd0'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def literal_category(row):
    base = row['mnemonic'].split('.')[0]
    if row['cpu_address'] == 0x1a36c:
        return 'main_requested_packed_add_long_literal'
    if row['mnemonic'] in ('add.l', 'addi.l'):
        return 'long_add_literal'
    if row['mnemonic'].endswith('.w') and base in ('cmp', 'cmpi', 'cmpa'):
        return 'word_compare_literal'
    if base == 'swap':
        return 'swap_literal'
    if base == 'asr':
        return 'arithmetic_shift_right_literal'
    if base in ('ori', 'eori', 'andi') and row['op_str'].endswith('ccr'):
        return 'ccr_mask_literal'
    if base in ('sub', 'subi', 'subq', 'neg'):
        return 'subtract_or_negate_literal'
    return None


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    windows = []
    indexed = {}
    controls = []
    literals = []
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Window gap, overlap or out-of-range row')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Instruction raw bytes/source mismatch')
            require(cursor not in indexed, 'Overlapping requested instruction windows')
            indexed[cursor] = row
            cursor += row['size']
            base = row['mnemonic'].split('.')[0]
            if base in CONTROL:
                destination = target(row)
                controls.append(dict(instruction_cpu_address=row['cpu_address'],
                    instruction_rom_offset=row['rom_offset'], instruction=dict(row),
                    control_kind='call' if base in ('jsr', 'bsr') else 'branch_or_jump',
                    target_cpu_address=destination,
                    target_rom_offset=destination if destination is not None and destination < 0x100000 else None,
                    classification='Literal direct encoded target' if destination is not None else
                        'Encoded indexed/indirect control operand; final target not inferred'))
            category = literal_category(row)
            if category:
                literals.append(dict(cpu_address=row['cpu_address'], rom_offset=row['rom_offset'],
                    category=category, instruction=dict(row), raw_sha256=sha(bytes.fromhex(row['raw']))))
        require(cursor == end, 'Incomplete exact instruction coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            gap_count=0, gaps=[], instructions=rows, undecoded_rows=undecoded,
            classification='Explicit bounded instruction candidates; no code/data ownership completion'))
    for address, mnemonic, operand in LITERAL_EXPECTATIONS:
        require(address in indexed and indexed[address]['mnemonic'] == mnemonic
                and indexed[address]['op_str'] == operand, 'Main-requested literal instruction changed')
    entries = []
    for address, destination in DISPATCH_ENTRIES:
        row = indexed[address]
        require(row['mnemonic'] == 'bra.w' and row['size'] == 4 and target(row) == destination,
                'Three-entry encoded BRA.W dispatch table changed')
        entries.append(dict(cpu_address=address, rom_offset=address, instruction=dict(row),
                            target_cpu_address=destination, target_rom_offset=destination))
    require(indexed[0x1a2c2]['mnemonic'] == 'jsr'
            and indexed[0x1a2c2]['op_str'] == '$1a2d4(pc, d0.w)',
            'Literal indexed condition dispatch instruction changed')
    dispatch = dict(start_cpu_address=0x1a2d4, start_rom_offset=0x1a2d4,
        end_cpu_address_exclusive=0x1a2e0, end_rom_offset_exclusive=0x1a2e0,
        raw_sha256=sha(program[0x1a2d4:0x1a2e0]), entries=entries,
        indexed_call_instruction=dict(indexed[0x1a2c2]),
        classification='Three real encoded BRA.W instruction candidates used by main-confirmed indexed JSR; not treated as raw pointer data. No selector bounds or execution reachability inferred.')
    ordered = sorted(WINDOWS)
    unassigned = []
    for (_, previous_end), (following_start, _) in zip(ordered, ordered[1:]):
        if previous_end < following_start:
            unassigned.append(dict(start_cpu_address=previous_end, start_rom_offset=previous_end,
                end_cpu_address_exclusive=following_start, end_rom_offset_exclusive=following_start,
                classification='Unassigned interval between requested windows; not decoded, no code/data claim'))
    require(sha(program) == SOURCE_SHA256, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        decoder='Capstone '+capstone.__version__,
        mapping='Fixed first1MiB CPU addresses equal ROM offsets; encoded RAM operands remain distinct.',
        main_contract_document='docs/analysis/scene-frame-control.md',
        window_count=len(windows), instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows), gap_count=0,
        windows=windows, dispatch_instruction_table=dispatch,
        raw_data_sections=[], unassigned_inter_window_intervals=unassigned,
        branch_call_operand_count=len(controls), branch_call_operands=controls,
        literal_instruction_count=len(literals), literal_instructions=literals,
        scope='Five main-confirmed explicit windows, including full289e..28ae and197da..19802 helper ranges. '
              'Every assigned byte retained using padded decoder, including undecoded rows and bytes after RTS. '
              'Dispatch BRA instruction table is distinguished from raw data; no raw data section is invented. '
              'Branch/call operand addresses and packed ADD.L, WORD compares, SWAP, ASR and other requested literal opcode evidence only. '
              'No new condition/rectangle/shake/settings semantics, code/data ownership completion, native/C++ execution equivalence or natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/scene_frame_control_disassembly.json'
    listing_path = root/'artifacts/scene_frame_control_disassembly.asm'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    listing = ['; Original source SHA256 '+SOURCE_SHA256,
               '; Whole bounded instruction candidates; firstRTS does not truncate. No semantic/execution proof.']
    for window in report['windows']:
        listing.append('; [%06x,%06x) SHA256 %s' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        listing.append(asm(window['instructions']))
    listing.append('; Dispatch table1a2d4..1a2e0: real BRA.W instruction candidates, not raw pointer data.')
    for entry in report['dispatch_instruction_table']['entries']:
        listing.append(asm([entry['instruction']]))
    listing_path.write_text('\n'.join(listing)+'\n')
    print(json.dumps(dict(windows=report['window_count'], rows=report['instruction_row_count'],
        undecoded=report['undecoded_row_count'], gaps=report['gap_count'],
        per_window=[dict(start_cpu_address=w['start_cpu_address'], rows=w['instruction_row_count'],
            raw_sha256=w['raw_sha256']) for w in report['windows']],
        branch_call_operands=report['branch_call_operand_count'], literal_instructions=report['literal_instruction_count'],
        report_sha256=sha(path.read_bytes()), asm_sha256=sha(listing_path.read_bytes()))))


if __name__ == '__main__':
    main()
