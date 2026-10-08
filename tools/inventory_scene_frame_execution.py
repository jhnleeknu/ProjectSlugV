"""Pinned bounded frame/caller candidates and verified existing resource windows.

Literal instruction order and resource overlap only; no execution/reachability proof.
"""
import collections
import hashlib
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import target, CONTROL
from observe_scene_general_initialization import resources
from pack_scene_scripts import SOURCE_SHA256

WINDOWS = ((0x1a73c, 0x1a7a8), (0x47642, 0x47672))
EXPECTED_CALLS = (0x1a2b4, 0x1a26a, 0x1a526, 0x19b96, 0x19d08,
                  0x19802, 0x1a3d6, 0x1a7a8, 0x1a442)
LITERALS = (
    (0x1a73c, 'move.w', '#$1, -$7ff0(a5)'),
    (0x1a742, 'move.w', '#$2000, $2ffff2.l'),
    (0x1a74a, 'move.w', '#$0, $2ffff0.l'),
    (0x1a756, 'bcc.w', '$1a75e'),
    (0x1a76a, 'move.l', '$53bc(a5), d0'),
    (0x1a76e, 'move.l', '$53c0(a5), d1'),
    (0x1a776, 'swap', 'd7'),
    (0x1a778, 'cmp.w', '$5418(a5), d7'),
    (0x1a77c, 'bcs.w', '$1a784'),
    (0x1a780, 'move.w', 'd7, $5418(a5)'),
    (0x1a790, 'move.w', '#$0, -$7ff0(a5)'),
    (0x1a796, 'move.w', '#$1000, $2ffff2.l'),
    (0x1a79e, 'move.w', '#$0, $2ffff0.l'),
    (0x1a7a6, 'rts', ''))
WRITE_ADDRESSES = ((0x1a73c, 'encoded A5 displacement', -0x7ff0),
    (0x1a742, 'absolute bank/MMIO address', 0x2ffff2),
    (0x1a74a, 'absolute bank/MMIO address', 0x2ffff0),
    (0x1a780, 'encoded A5 displacement', 0x5418),
    (0x1a790, 'encoded A5 displacement', -0x7ff0),
    (0x1a796, 'absolute bank/MMIO address', 0x2ffff2),
    (0x1a79e, 'absolute bank/MMIO address', 0x2ffff0))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported original source')
    evidence_files = ('tools/disassemble_program.py',
        'tools/observe_scene_general_initialization.py',
        'tools/inventory_scene_frame_execution.py', 'docs/analysis/scene-frame-control.md')
    evidence = [dict(file=f, sha256=sha((root/f).read_bytes())) for f in evidence_files]
    windows = []
    indexed = {}
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                and row['size'] > 0 and cursor+row['size'] <= end,
                'Instruction coverage gap/overlap/out-of-bounds')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Instruction source bytes changed')
            indexed[cursor] = row
            cursor += row['size']
        require(cursor == end, 'Incomplete exact window coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        require(not undecoded, 'Unexpected undecoded canonical window bytes')
        controls = [dict(instruction=r, literal_target_cpu_address=target(r),
            literal_target_rom_offset=target(r),
            target_mapping='Fixed CPU=ROM for literal targets in these windows')
            for r in rows if r['mnemonic'].split('.')[0] in CONTROL]
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            gaps=[], gap_count=0, instructions=rows, control_operands=controls))
    calls = [r for r in windows[0]['instructions']
             if r['mnemonic'].split('.')[0] in ('bsr', 'jsr')]
    require(tuple(target(r) for r in calls) == EXPECTED_CALLS, 'Frame literal call order mismatch')
    literal = []
    for at, mnemonic, operand in LITERALS:
        row = indexed[at]
        require(row['mnemonic'] == mnemonic and row['op_str'] == operand,
                'Confirmed frame literal instruction mismatch')
        literal.append(row)
    writes = [dict(instruction=indexed[at], address_form=form, encoded_address=value)
              for at, form, value in WRITE_ADDRESSES]
    rs, manifests = resources(root, program)
    require(len(rs) == 458, 'Current input resource set changed')
    fixed = sorted((r for r in rs if r['kind'] == 1), key=lambda r: (r['cpu'], r['size'], r['file']))
    require(all(r['cpu'] == r['rom'] for r in fixed), 'Unexpected nonfixed kind1 mapping')
    overlaps = []
    for i, left in enumerate(fixed):
        for right in fixed[i+1:]:
            start = max(left['cpu'], right['cpu'])
            end = min(left['cpu']+left['size'], right['cpu']+right['size'])
            if start >= end:
                continue
            exact = left['cpu'] == right['cpu'] and left['size'] == right['size']
            contained = ((left['cpu'] <= right['cpu'] and left['cpu']+left['size'] >= right['cpu']+right['size'])
                or (right['cpu'] <= left['cpu'] and right['cpu']+right['size'] >= left['cpu']+left['size']))
            overlaps.append(dict(left_file=left['file'], right_file=right['file'],
                left_cpu=left['cpu'], left_end_exclusive=left['cpu']+left['size'],
                right_cpu=right['cpu'], right_end_exclusive=right['cpu']+right['size'],
                start_cpu_address=start, start_rom_offset=start,
                end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
                byte_count=end-start, raw_sha256=sha(program[start:end]),
                relation='exact' if exact else 'contained' if contained else 'partial'))
    counts = collections.Counter(r['kind'] for r in rs)
    directories = collections.Counter(str(Path(r['file']).parent) for r in rs)
    grouped = collections.Counter((str(Path(r['file']).parent), r['kind']) for r in rs)
    for item in rs+manifests+evidence:
        require(sha((root/item['file']).read_bytes()) == item['sha256'], 'Input changed during audit')
    require(sha(program) == SOURCE_SHA256, 'Original bytes changed')
    return dict(schema_version=1, source=source, program_code_modified=False,
        decoder='Capstone '+capstone.__version__, evidence_files=evidence,
        mapping='Assigned instruction windows and kind1 windows: CPU=ROM. Kind2 banked CPU addresses remain separate from ROM offsets.',
        window_count=len(windows), instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=0, gap_count=0, windows=windows,
        sequential_frame_call_candidates=[dict(instruction=r, target_cpu_address=target(r), target_rom_offset=target(r)) for r in calls],
        confirmed_contract_literal_evidence=literal, frame_write_operand_evidence=writes,
        resource_audit=dict(helper='observe_scene_general_initialization.resources(root, program)',
            resource_count=len(rs), counts_by_kind=dict(sorted(counts.items())),
            counts_by_directory=dict(sorted(directories.items())),
            counts_by_directory_and_kind=[dict(directory=d, kind=k, count=n) for (d,k),n in sorted(grouped.items())],
            resources=rs, manifests=manifests, fixed_window_count=len(fixed),
            fixed_overlap_pair_count=len(overlaps), fixed_overlap_relations=dict(sorted(collections.Counter(o['relation'] for o in overlaps).items())),
            fixed_overlaps=overlaps,
            scope='Helper checks all current MS5D v1 headers/kinds/size/reserved/CRC, source payload bytes and metadata; deduplicates exact (kind,CPU,ROM,size) identities after byte equality. '
                  'Overlap pairs concern audited unique kind1 fixed windows only. Banked kind2 CPU intervals are not merged into fixed overlap comparisons. '
                  'Overlaps are resource selection evidence, not bugs or a proof of read ownership.'),
        scope='Padded candidate decoding with exact bounded source-byte coverage, including bytes after first RTS. '
              'Literal frame call order and key write/branch operands match the existing confirmed contract. '
              'The 47642..47672 window is bounded producer instruction evidence only. No new callee semantics, runtime implementation, native execution, scheduler or reachability proof.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/scene_frame_execution_disassembly.json'
    listing = root/'artifacts/scene_frame_execution_disassembly.asm'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    lines = ['; Original SHA256 '+SOURCE_SHA256, '; Fixed CPU=ROM bounded instruction candidates only.']
    for window in report['windows']:
        lines.append('; [%06x,%06x) SHA256 %s; first RTS does not truncate.' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        lines.append(asm(window['instructions']))
    listing.write_text('\n'.join(lines)+'\n')
    audit = report['resource_audit']
    print(json.dumps(dict(windows=report['window_count'], rows=report['instruction_row_count'],
        undecoded=0, gaps=0, sequential_call_targets=[hex(r['target_cpu_address']) for r in report['sequential_frame_call_candidates']],
        resources=audit['resource_count'], kinds=audit['counts_by_kind'],
        fixed_overlap_pairs=audit['fixed_overlap_pair_count'], overlap_relations=audit['fixed_overlap_relations'],
        report_sha256=sha(path.read_bytes()), asm_sha256=sha(listing.read_bytes()))))


if __name__ == '__main__':
    main()
