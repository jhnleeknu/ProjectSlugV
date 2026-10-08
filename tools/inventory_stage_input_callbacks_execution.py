"""Exact bounded original callback instruction evidence; no runtime closure proof."""
import collections
import hashlib
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import CONTROL, target
from pack_scene_scripts import SOURCE_SHA256

WINDOWS = ((0x49d88,0x49f8c), (0x1bec0,0x1bee4), (0x1d5ac,0x1d5c4),
    (0x1d5e2,0x1d5fc), (0x1d61a,0x1d63a), (0x1d664,0x1d698),
    (0x1d6c2,0x1d6fa), (0x1d8cc,0x1d8ce), (0xe73f2,0xe73f8),
    (0x4836e,0x48384))
ENTRIES = (0x49d88,0x49de6,0x49e34,0x49e38,0x49e9c,0x49eba,0x49ef0,
    0x49f2c,0x49f66,0x1bec0,0x1d5ac,0x1d5e2,0x1d61a,0x1d628,
    0x1d664,0x1d6c2,0x1d8cc,0xe73f2)
LITERALS = (
    (0x49ebc,'cmpa.l','$100cb8.l, a0'),
    (0x49ef2,'cmpa.l','$100cb8.l, a0'),
    (0x49f68,'cmpa.l','#$100cb8, a0'),
    (0x49f76,'cmpa.l','#$100da8, a0'),
    (0x49eda,'movem.l','d0, -(a7)'),
    (0x49ede,'move.w','d7, d0'),
    (0x49ee0,'ori.w','#$20, d0'),
    (0x49ee4,'movem.l','(a7)+, d0'),
    (0x49f10,'movem.l','d0, -(a7)'),
    (0x49f14,'bsr.w','$49de6'),
    (0x49f18,'movem.l','(a7)+, d1'),
    (0x1d628,'move.w','$78(a0), d0'),
    (0x1d62c,'jsr','$49c32.l'),
    (0x1d632,'jsr','$49f66.l'),
    (0x1d638,'rts',''))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    program,source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported pinned original source')
    windows,indexed,controls = [],{},[]
    for start,end in WINDOWS:
        rows = disassemble_range(program,start,end-start,start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == row['rom_offset'] == cursor and
                row['size'] > 0 and cursor+row['size'] <= end,
                'Window gap, overlap or out-of-bounds row')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Candidate row/source bytes mismatch')
            require(cursor not in indexed, 'Overlapping assigned windows')
            indexed[cursor] = row
            cursor += row['size']
        require(cursor == end, 'Incomplete exact bounded coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        local = []
        for row in rows:
            if row['classification'] == 'candidate_instruction' and row['mnemonic'].split('.')[0] in CONTROL:
                destination = target(row)
                control = dict(instruction=row,target_cpu_address=destination,
                    target_rom_offset=destination if destination is not None and destination < 0x100000 else None,
                    target_in_assigned_windows=destination is not None and any(a <= destination < b for a,b in WINDOWS),
                    classification='Literal direct control operand candidate; no execution or callee ownership claim')
                local.append(control)
                controls.append(control)
        windows.append(dict(start_cpu_address=start,start_rom_offset=start,
            end_cpu_address_exclusive=end,end_rom_offset_exclusive=end,
            byte_count=end-start,raw_sha256=sha(program[start:end]),row_count=len(rows),
            instruction_row_count=len(rows)-len(undecoded),undecoded_row_count=len(undecoded),
            undecoded_rows=undecoded,gaps=[],gap_count=0,instructions=rows,
            control_operands=local))
    for entry in ENTRIES:
        require(entry in indexed and indexed[entry]['classification'] == 'candidate_instruction',
                'Supported entry is not a decoded bounded row boundary')
    evidence = []
    for address,mnemonic,operand in LITERALS:
        row = indexed[address]
        require(row['mnemonic'] == mnemonic and row['op_str'] == operand,
                'Requested literal instruction evidence changed')
        evidence.append(row)
    sequences = []
    for name,addresses in (
        ('49eba literal D0 push, MOVE.W, ORI.W, D0 pop', (0x49eda,0x49ede,0x49ee0,0x49ee4)),
        ('49ef0 literal D0 push, call, D1 pop', (0x49f10,0x49f14,0x49f18)),
        ('1d628 literal WORD load, setter call, mapper-wrapper call, RTS', (0x1d628,0x1d62c,0x1d632,0x1d638))):
        rows = [indexed[a] for a in addresses]
        require(all(a['cpu_address']+a['size'] == b['cpu_address'] for a,b in zip(rows,rows[1:])),
                'Requested literal sequence is not contiguous')
        sequences.append(dict(description=name,instructions=rows,
            scope='Contiguous encoded instructions only; callee state effects are not inferred here'))
    fresh,fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Original source changed during inventory')
    counts = collections.Counter(c['target_cpu_address'] for c in controls if c['target_cpu_address'] is not None)
    calls = [c for c in controls if c['instruction']['mnemonic'].split('.')[0] in ('jsr','bsr')]
    return dict(schema_version=1,source=source,program_code_modified=False,
        decoder='Capstone '+capstone.__version__,mapping='Fixed first1MiB CPU addresses equal ROM file offsets; encoded operands retained literally.',
        window_count=len(windows),byte_count=sum(w['byte_count'] for w in windows),
        row_count=sum(w['row_count'] for w in windows),
        instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),gap_count=0,
        supported_entries=list(ENTRIES),supported_entry_count=len(ENTRIES),windows=windows,
        control_operand_count=len(controls),direct_call_operand_count=len(calls),
        target_counts=[dict(target_cpu_address=at,target_rom_offset=at,count=count)
                       for at,count in sorted(counts.items())],
        literal_comparison_evidence=evidence[:4],literal_key_instruction_evidence=evidence,
        literal_contiguous_sequences=sequences,
        scope='Explicit assigned bounded source instruction candidates, including bytes after first RTS. '
              'Exact coverage and undecoded rows are recorded; decoded rows do not establish automatic analysis completion or a code/data ownership map. '
              'Absolute-memory CMPA operands and immediate CMPA operands, D0 versus D1 MOVEM operands, and contiguous call sequences remain literal evidence. '
              'No new semantic inference, runtime execution, whole callback closure, callee implementation, natural reachability or cycle-equivalence proof.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/stage_input_callbacks_execution.json'
    listing = root/'artifacts/stage_input_callbacks_execution.asm'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    lines = ['; Original SHA256 '+SOURCE_SHA256,
             '; Fixed CPU=ROM bounded source candidates; no runtime/closure proof.']
    for window in report['windows']:
        lines.append('; [%06x,%06x) SHA256 %s; first RTS does not truncate.' % (
            window['start_cpu_address'],window['end_cpu_address_exclusive'],window['raw_sha256']))
        lines.append(asm(window['instructions']))
    listing.write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(windows=report['window_count'],rows=report['row_count'],
        instructions=report['instruction_row_count'],undecoded=report['undecoded_row_count'],gaps=0,
        supported_entries=report['supported_entry_count'],control_operands=report['control_operand_count'],
        direct_call_operands=report['direct_call_operand_count'],
        report_sha256=sha(path.read_bytes()),asm_sha256=sha(listing.read_bytes()))))


if __name__ == '__main__':
    main()
