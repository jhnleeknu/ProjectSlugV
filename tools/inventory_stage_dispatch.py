"""Full bounded stage-dispatch instruction/reference candidates, not a trace."""
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
START, END = 0x478c4, 0x47b00
ENTRIES = (0x478c4, 0x478f0, 0x4791c, 0x47934, 0x4794c, 0x47964)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/stage_dispatch')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical ROM')
    rows = disassemble_range(program, START, END-START, START)
    assert sum(row['size'] for row in rows) == END-START
    assert all(row['rom_offset']+row['size'] <= END for row in rows)
    for row in rows:
        row['explicit_dispatch_entry'] = row['cpu_address'] in ENTRIES
    code_rows = [row for row in rows if row['classification'] == 'candidate_instruction']
    targets = controls(code_rows)
    fixed = fixed_references(code_rows)
    callback_stores = []
    for row in code_rows:
        if row['mnemonic'] == 'move.l' and re.search(r',\s*\(a6\)$', row['op_str']):
            match = re.fullmatch(r'#\$([0-9a-f]+),\s*\(a6\)', row['op_str'])
            callback_stores.append(dict(instruction_cpu_address=row['cpu_address'], instruction_rom_offset=row['rom_offset'],
                raw=row['raw'], mnemonic=row['mnemonic'], operands=row['op_str'], destination='(A6)',
                immediate_value=int(match[1],16) if match else None,
                classification='Long store to A6 base; callback-slot candidate from supplied caller context. Execution not observed.'))
    entry_rows = []
    for address in ENTRIES:
        aligned = [row for row in rows if row['cpu_address'] == address]
        entry_rows.append(dict(cpu_address=address, rom_offset=address, instruction=aligned[0] if aligned else None,
            instruction_boundary_in_linear_window=bool(aligned), existing_references=coverage_references(root,address)))
    direct_calls = [target for target in targets if target['mnemonic'].split('.')[0] in ('jsr','bsr')]
    unique_calls = sorted({target['target_cpu_address'] for target in direct_calls})
    report = dict(source=source, decoder='Capstone '+capstone.__version__, cpu_model='M68000', program_code_modified=False,
        mapping='Fixed first1MiB CPU address equals canonical ROM offset; RAM/MMIO and banked addresses remain separate.',
        start_cpu_address=START, start_rom_offset=START, end_exclusive=END,
        window_raw_sha256=hashlib.sha256(program[START:END]).hexdigest(), instructions=rows,
        row_count=len(rows), candidate_instruction_count=len(code_rows), explicit_entries=entry_rows,
        control_target_candidates=targets, direct_call_count=len(direct_calls), unique_direct_call_count=len(unique_calls),
        direct_callee_text_references=[dict(cpu_address=address, existing_references=coverage_references(root,address)) for address in unique_calls],
        encoded_memory_operand_candidates=fields(code_rows), fixed_rom_operand_candidates=fixed,
        callback_store_candidates=callback_stores,
        rts_addresses=[row['cpu_address'] for row in code_rows if row['mnemonic']=='rts'],
        undecoded_words=[row for row in rows if row['classification']!='candidate_instruction'],
        limitations='Explicit full window only; no stop at firstRTS. All branch successors inside the window retained syntactically '
            'but reachability/code-data boundaries are unproven. No callee body or complete callback/dispatch behavior analysis. '
            'Assigned47b00 end is not proven routine boundary. Truncated/invalid final words retained asdc.w by padded bounded decoder. '
            'Fixed operands include immediates/PC references; address-value encoding does not prove ROM data type or dereference. '
            'Other stores/references remain raw encoded candidates; callback store interpretation requires main review.')
    output = Path(args.output)
    if not output.is_absolute():
        output = root/output
    output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    lines = ['; Explicit bounded478c4..47b00; no whole-body/code-data completion claim.']
    for row in rows:
        if row['explicit_dispatch_entry']:
            lines.append('; supplied dispatch entry %06x' % row['cpu_address'])
        lines.append(asm([row]))
    (output/'inventory.asm').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(rows=len(rows), direct_calls=len(direct_calls), unique_direct_calls=len(unique_calls),
        controls=len(targets), fixed_operands=len(fixed), callback_store_candidates=len(callback_stores),
        undecoded_words=len(report['undecoded_words']), final_row=rows[-1],
        report_sha256=hashlib.sha256((output/'report.json').read_bytes()).hexdigest(),
        asm_sha256=hashlib.sha256((output/'inventory.asm').read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
