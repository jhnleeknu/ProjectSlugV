"""Bounded stage-area body/callees and raw selector lookup evidence."""
import argparse
import hashlib
import json
from pathlib import Path

import capstone
from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm, coverage_references
from inventory_game_ready import fixed_references
from inventory_object_removal import controls, fields

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
START, END = 0x479d0, 0x47af0
EXPLICIT = ((0x4e666,0x4e68e),(0xd760a,0xd768a),(0x49c20,0x49ca0),(0x49c32,0x49cb2))
TABLE, TABLE_SIZE = 0x4e4d2,128


def block(program,root,start,end,basis):
    rows = disassemble_range(program,start,end-start,start)
    assert sum(row['size'] for row in rows)==end-start
    assert all(row['rom_offset']+row['size']<=end for row in rows)
    known = [row for row in rows if row['classification']=='candidate_instruction']
    return dict(cpu_address=start,rom_offset=start,end_exclusive=end,
        raw_sha256=hashlib.sha256(program[start:end]).hexdigest(),instructions=rows,basis=basis,
        control_target_candidates=controls(known),fixed_rom_operand_candidates=fixed_references(known),
        encoded_memory_operand_candidates=fields(known),existing_address_text_references=coverage_references(root,start),
        rts_addresses=[row['cpu_address'] for row in known if row['mnemonic']=='rts'],
        undecoded_words=[row for row in rows if row['classification']!='candidate_instruction'],
        boundary_caveat='Full assigned window retained after firstRTS; end/code-data/routine ownership unproven. '
            'Branch/callee behavior not analyzed; truncated/invalid finalwords preserved asdc.w.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/stage_area_body');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=PROGRAM_SHA256 or hashlib.sha256(program).hexdigest()!=PROGRAM_SHA256:
        raise ValueError('Unsupported canonical ROM')
    caller=block(program,root,START,END,'Supplied caller window, not a completed whole stage body.')
    direct=[ref for ref in caller['control_target_candidates'] if ref['mnemonic'].split('.')[0] in ('jsr','bsr')]
    windows=[block(program,root,start,end,'Explicit requested callee window.') for start,end in EXPLICIT]
    covered={start for start,end in EXPLICIT}
    for address in sorted({ref['target_cpu_address'] for ref in direct}-covered):
        windows.append(block(program,root,address,address+128,'Direct calltarget candidate; explicitly bounded128-byte listing.'))
    for window in windows:
        window['caller_callsites']=[ref for ref in direct if ref['target_cpu_address']==window['cpu_address']]
    raw=program[TABLE:TABLE+TABLE_SIZE]
    report=dict(source=source,decoder='Capstone '+capstone.__version__,program_code_modified=False,
        mapping='Fixed first1MiB CPU address equals canonical ROM offset; RAM/MMIO/banked addresses remain separate.',
        caller=caller,callee_windows=windows,direct_calls=len(direct),unique_direct_targets=len({ref['target_cpu_address'] for ref in direct}),
        total_rows=sum(len(window['instructions']) for window in [caller]+windows),
        raw_selector_lookup=dict(cpu_address=TABLE,rom_offset=TABLE,end_exclusive=TABLE+TABLE_SIZE,size=TABLE_SIZE,
            raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest(),
            classification='Assigned128-byte raw evidence window only; no logical table extent or128-entry semantic claim.'),
        limitations='Read-only inventory. No native execution/completed callee or stage analysis. '
            'All windows retain syntactic rows beyondfirstRTS, including possibledata. Overlapsintentional. '
            'Fixed references and engine textual references are candidates, not effect/API equivalence. '
            'Caller endsbefore47af0 callback and doesnotclaim complete479d0 continuation.')
    output=Path(args.output);output=output if output.is_absolute() else root/output;output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=[]
    for window in [caller]+windows:
        lines.extend(['; explicit %06x..%06x exclusive'% (window['cpu_address'],window['end_exclusive']),asm(window['instructions'])])
    lines.append('; raw selector lookup4e4d2..4e552, not logicaltableextent')
    for offset in range(0,TABLE_SIZE,16):lines.append('%06x  %s'%(TABLE+offset,raw[offset:offset+16].hex()))
    (output/'inventory.asm').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(rows=report['total_rows'],calls=report['direct_calls'],unique_targets=report['unique_direct_targets'],windows=len(windows),
        table_sha256=report['raw_selector_lookup']['sha256'],report_sha256=hashlib.sha256((output/'report.json').read_bytes()).hexdigest(),
        asm_sha256=hashlib.sha256((output/'inventory.asm').read_bytes()).hexdigest())))


if __name__=='__main__':main()
