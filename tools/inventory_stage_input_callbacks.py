"""Bounded original input/callback instruction candidates and raw call encodings.

Raw-match candidate scans are not a code map or callback/reachability analysis.
"""
import collections
import hashlib
import json
import re
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import target
from pack_scene_scripts import SOURCE_SHA256

WINDOWS = ((0x49ab4, 0x49bca), (0x49c20, 0x49c66))
TARGETS = (0x49c20, 0x49c32, 0x49c66)
FIXED_END = 0x100000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounded(program, start, end):
    rows = disassemble_range(program, start, end-start, start)
    cursor = start
    for row in rows:
        require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                and row['size'] > 0 and cursor+row['size'] <= end,
                'Bounded row gap/overlap/out-of-range')
        require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                'Candidate instruction bytes/source mismatch')
        cursor += row['size']
    require(cursor == end, 'Incomplete exact bounded coverage')
    undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
    return dict(start_cpu_address=start, start_rom_offset=start,
        end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
        raw_sha256=sha(program[start:end]), byte_count=end-start,
        instruction_row_count=len(rows)-len(undecoded), row_count=len(rows),
        undecoded_row_count=len(undecoded), undecoded_rows=undecoded,
        gap_count=0, gaps=[], instructions=rows)


def encoded_references(program):
    matches = []
    for at in range(0, FIXED_END-1, 2):
        word = int.from_bytes(program[at:at+2], 'big')
        dest = None
        size = None
        form = None
        if word in (0x4eb9, 0x4ef9) and at+6 <= FIXED_END:
            dest = int.from_bytes(program[at+2:at+6], 'big')
            if dest != 0x49c20:
                continue
            size, form = 6, 'absolute-long JSR/JMP to49c20'
        elif word == 0x4eba and at+4 <= FIXED_END:
            dest = at+2+int.from_bytes(program[at+2:at+4], 'big', signed=True)
            size, form = 4, 'PC-relative signed-word JSR'
        elif word >> 8 in (0x60, 0x61):
            displacement = word & 255
            if displacement == 0:
                if at+4 > FIXED_END:
                    continue
                displacement = int.from_bytes(program[at+2:at+4], 'big', signed=True)
                size, form = 4, 'signed-word BRA/BSR'
            else:
                displacement = displacement if displacement < 128 else displacement-256
                size, form = 2, 'signed-byte BRA/BSR (M68000)'
            dest = at+2+displacement
        if dest not in TARGETS:
            continue
        # Decode starts exactly at the raw candidate; preceding context is never
        # used to establish instruction boundaries or actual execution.
        row = disassemble_range(program, at, min(16, FIXED_END-at), at)[0]
        valid = (row['classification'] == 'candidate_instruction'
                 and row['size'] == size and target(row) == dest)
        context = bounded(program, max(0, at-16), min(FIXED_END, at+size+24))
        matches.append(dict(cpu_address=at, rom_offset=at,
            encoding_form=form, raw_hex=program[at:at+size].hex(),
            target_cpu_address=dest, target_rom_offset=dest,
            padded_decoder_matches_encoding=valid, instruction=row,
            context=context,
            context_a0_operand_candidates=[r for r in context['instructions']
                if r['classification'] == 'candidate_instruction' and re.search(r'\ba0\b', r['op_str'])],
            scope='Raw encoding at an even offset validated in isolation; code/data and genuine instruction-boundary status remain unconfirmed. '
                  'Context starts at an arbitrary even offset and may decode extension/data words; A0 operand candidates do not establish a reaching definition.'))
    return matches


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported pinned original source')
    windows = [bounded(program, start, end) for start, end in WINDOWS]
    mask = program[0x49ab0:0x49ab4]
    require(mask.hex() == '10204080', 'Default mask source mismatch')
    candidates = encoded_references(program)
    # Exact assigned windows are instruction candidates. Explicit data is kept
    # separate and never fed to the decoder as an assigned code window.
    data = dict(start_cpu_address=0x49ab0, start_rom_offset=0x49ab0,
        end_cpu_address_exclusive=0x49ab4, end_rom_offset_exclusive=0x49ab4,
        byte_count=4, raw_hex=mask.hex(), raw_sha256=sha(mask),
        classification='main-confirmed default-mask data; not code')
    slots = [r for w in windows for r in w['instructions']
             if '$5734(a5)' in r['op_str'] or '$5738(a5)' in r['op_str']]
    indirect = [r for w in windows for r in w['instructions']
                if r['mnemonic'] == 'jsr' and r['op_str'] == '(a1)']
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        decoder='Capstone '+capstone.__version__,
        mapping='Fixed first1MiB CPU addresses equal source ROM offsets; A5 displacements remain encoded operands.',
        window_count=len(windows), row_count=sum(w['row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),
        gap_count=0, windows=windows, data_regions=[data],
        assigned_window_slot_operand_candidates=slots,
        assigned_window_indirect_call_candidates=indirect,
        raw_encoding_scan=dict(start_rom_offset=0, end_rom_offset_exclusive=FIXED_END,
            stride_bytes=2, targets=list(TARGETS),
            forms='Absolute-long JSR/JMP only to49c20; PC-relative signed-word JSR and signed-byte/word BRA/BSR to49c20/49c32/49c66; M68000 byte displacement ff means -1.',
            candidate_count=len(candidates),
            decoder_match_count=sum(c['padded_decoder_matches_encoding'] for c in candidates),
            counts_by_target={address: sum(c['target_cpu_address'] == address for c in candidates) for address in TARGETS},
            candidates=candidates),
        scope='Assigned complete bounded windows, including bytes after RTS; gaps/undecoded rows preserved. '
              'Raw encoding candidates over fixed first1MiB are validated with padded decoding in isolation and retain arbitrary-even-aligned short contexts. '
              'No linear all-code assertion, callback semantics, reaching A0 definition, engine execution or natural reachability proof. '
              '49c66 is a requested scan target, outside the assigned second code window exclusive endpoint.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/stage_input_callbacks.json'
    listing = root/'artifacts/stage_input_callbacks.asm'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    lines = ['; Original source SHA256 '+SOURCE_SHA256,
             '; CPU=ROM; bounded candidates, raw matches are not proven callsites.',
             '; DATA49ab0..49ab4 = 10204080 (not decoded as code).']
    for window in report['windows']:
        lines.append('; Assigned [%06x,%06x) SHA256 %s' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        lines.append(asm(window['instructions']))
    for candidate in report['raw_encoding_scan']['candidates']:
        lines.append('; Raw candidate at%06x target%06x; arbitrary-even-aligned context, boundaries unconfirmed.' % (
            candidate['cpu_address'], candidate['target_cpu_address']))
        lines.append(asm(candidate['context']['instructions']))
    listing.write_text('\n'.join(lines)+'\n')
    scan = report['raw_encoding_scan']
    print(json.dumps(dict(windows=report['window_count'], rows=report['row_count'],
        undecoded=report['undecoded_row_count'], gaps=0,
        candidates=scan['candidate_count'], decoder_matches=scan['decoder_match_count'],
        counts_by_target=scan['counts_by_target'],
        report_sha256=sha(path.read_bytes()), asm_sha256=sha(listing.read_bytes()))))


if __name__ == '__main__':
    main()
