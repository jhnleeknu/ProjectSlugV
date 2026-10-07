"""Explicit128-byte stage-body callee inventories and textual API candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import capstone
from disassemble_program import disassemble_range, load_verified_program
from inventory_game_initialization import asm, coverage_references
from inventory_game_ready import fixed_references
from inventory_object_removal import controls, fields

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ENTRIES = (0xe7c36,0x477c2,0x476dc,0x48180,0x4e666,0xd760a,0x49c32,0xe8a1c,0x48398,0xe905c)
BODY_START, BODY_END = 0x479b0, 0x47af0
WINDOW_SIZE = 128


def api_candidates(root):
    result = []
    for path in sorted((root/'engine/include/ms5').glob('*.h')):
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            match = re.search(r'\bbool\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(', line)
            if match:
                result.append(dict(path=str(path.relative_to(root)), line=index+1, api_name=match[1],
                    preceding_comment_text='\n'.join(lines[max(0,index-7):index]), declaration_line=line.strip()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/stage_body')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical ROM')
    body = disassemble_range(program, BODY_START, BODY_END-BODY_START, BODY_START)
    body_calls = [entry for entry in controls(body) if entry['mnemonic'].split('.')[0] in ('jsr','bsr')]
    candidates = api_candidates(root)
    windows = []
    addresses = list(ENTRIES) + sorted({entry['target_cpu_address'] for entry in body_calls} - set(ENTRIES))
    for start in addresses:
        rows = disassemble_range(program,start,WINDOW_SIZE,start)
        assert sum(row['size'] for row in rows) == WINDOW_SIZE
        assert all(row['rom_offset']+row['size'] <= start+WINDOW_SIZE for row in rows)
        known = [row for row in rows if row['classification']=='candidate_instruction']
        # Map exact nearby address text, or matching source/header filename stems.
        # This organizational text mapping does not assert equivalent behavior/register contracts.
        pattern = re.compile(r'(?<![0-9a-f])(?:0x)?0*'+format(start,'x')+r'(?![0-9a-f])',re.I)
        references = coverage_references(root,start)
        stems = {Path(ref['path']).stem for ref in references['engine']['shown_matches']}
        mappings = []
        for entry in candidates:
            exact = bool(pattern.search(entry['preceding_comment_text']+'\n'+entry['declaration_line']))
            same_stem = Path(entry['path']).stem in stems
            if exact or same_stem:
                mapping = dict(entry)
                mapping['basis'] = 'Exact address near declaration' if exact else 'Header/source filename stem matches an engine text-address reference; organizational association only'
                mappings.append(mapping)
        windows.append(dict(cpu_address=start,rom_offset=start,end_exclusive=start+WINDOW_SIZE,
            raw_sha256=hashlib.sha256(program[start:start+WINDOW_SIZE]).hexdigest(),instructions=rows,
            explicitly_requested_callee=start in ENTRIES,
            callsites_in_supplied_body=[entry for entry in body_calls if entry['target_cpu_address']==start],
            control_target_candidates=controls(known),fixed_rom_operand_candidates=fixed_references(known),
            encoded_memory_operand_candidates=fields(known),rts_addresses=[row['cpu_address'] for row in known if row['mnemonic']=='rts'],
            undecoded_words=[row for row in rows if row['classification']!='candidate_instruction'],
            existing_address_text_references=references, existing_api_name_text_candidates=mappings,
            boundary_caveat='Explicit entry and128-byte limit only. Decode continues after firstRTS. '
                'Branch successors/callee effects not analyzed; code/data ownership and routine end unproven. '
                'Undecoded words include invalid/truncated operands and remain rawdc.w candidates.'))
    report = dict(source=source,decoder='Capstone '+capstone.__version__,cpu_model='M68000',program_code_modified=False,
        mapping='Fixed first1MiB CPU address equals canonical ROM offset; all supplied callees are within this mapping.',
        body_callsite_window=dict(start_cpu_address=BODY_START,end_exclusive=BODY_END,
            raw_sha256=hashlib.sha256(program[BODY_START:BODY_END]).hexdigest(),instructions=body,direct_call_candidates=body_calls),
        explicit_callee_windows=windows,window_count=len(windows),row_count=sum(len(w['instructions']) for w in windows),
        direct_call_count=sum(sum(ref['mnemonic'].split('.')[0] in ('jsr','bsr') for ref in w['control_target_candidates']) for w in windows),
        undecoded_word_count=sum(len(w['undecoded_words']) for w in windows),
        limitations='Read-only inventory, not native execution or complete semantic analysis. Exact address text references and '
            'API names are reuse candidates only, not proof of equivalent effects. Every explicit128-byte window is retained '
            'withoutfirstRTS termination; overlaps are intentional. All direct encoded call targets in the supplied body window receive a listing, without claiming all runtime callees. '
            'Padded bounded decoding rejects instructions extending past each assigned end; raw finalwords are retained.')
    output = Path(args.output)
    if not output.is_absolute():
        output = root/output
    output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    listing = ['; stage body479b0..47af0 callsite evidence; no whole-body completeness claim.',asm(body)]
    for window in windows:
        listing.extend(['; explicit callee %06x..%06x exclusive (128bytes)' % (window['cpu_address'],window['end_exclusive']),asm(window['instructions'])])
    (output/'inventory.asm').write_text('\n'.join(listing)+'\n')
    print(json.dumps(dict(windows=len(windows),callee_rows=report['row_count'],body_direct_calls=len(body_calls),
        callee_direct_calls=report['direct_call_count'],undecoded_words=report['undecoded_word_count'],
        report_sha256=hashlib.sha256((output/'report.json').read_bytes()).hexdigest(),
        asm_sha256=hashlib.sha256((output/'inventory.asm').read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
