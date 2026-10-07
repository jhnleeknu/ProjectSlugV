"""Pinned instruction inventory after47570; evidence only, no execution claim."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import capstone
from disassemble_program import disassemble_range,load_verified_program
from inventory_game_initialization import asm,coverage_references
PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
SEGMENTS=((0xc58a,0xc6ce),(0xc6da,0xc724),(0xc724,0xc74c))
CONTROL={'jsr','jmp','bsr','bra','beq','bne','bcc','bcs','bge','bgt','ble','blt','bhi','bls','bmi','bpl','bvc','bvs','dbra','dbf'}


def target(row):
    if row['mnemonic'].split('.')[0] not in CONTROL:return None
    match=re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\.w|\(pc\))?',row['op_str'])
    return int(match.group(1),16) if match else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='artifacts/game_continuation');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==PROGRAM_SHA256 and hashlib.sha256(program).hexdigest()==PROGRAM_SHA256
    segments=[];rows=[]
    for start,end in SEGMENTS:
        decoded=disassemble_range(program,start,end-start,start)
        assert all(row['classification']=='candidate_instruction' for row in decoded)
        assert decoded[-1]['rom_offset']+decoded[-1]['size']==end
        segments.append(dict(start_cpu_address=start,start_rom_offset=start,end_exclusive=end,instructions=decoded,
            evidence='Explicit47570 return boundary c58a; later block boundaries are encoded branch targets. '
                     'Contiguous candidate decode; multiple control paths, no execution observed.'))
        rows.extend(decoded)
    references=[];calls=[];branches=[]
    for row in rows:
        base=row['mnemonic'].split('.')[0];destination=target(row)
        if destination is not None:
            entry=dict(instruction_cpu_address=row['cpu_address'],instruction_rom_offset=row['rom_offset'],
                raw=row['raw'],mnemonic=row['mnemonic'],operands=row['op_str'],target_cpu_address=destination,
                target_rom_offset=destination if destination<0x100000 else None,execution_observed=False,
                target_classification='external_BIOS_address_candidate' if 0xc00000<=destination<0xc20000 else
                    'fixed_ROM_target_candidate' if destination<0x100000 else 'external_or_unmapped_target_candidate')
            (calls if base in ('jsr','bsr') else branches).append(entry)
        registers=sorted(set(re.findall(r'\b[ad][0-7]\b',row['op_str'])))
        memory=re.findall(r'(?:-?\$[0-9a-f]+)?\([^)]*\)|(?<![#0-9a-f])\$[0-9a-f]+\.[lw]',row['op_str'])
        immediates=[int(value,16) for value in re.findall(r'#\$([0-9a-f]+)',row['op_str'])]
        if registers or memory:
            references.append(dict(instruction_cpu_address=row['cpu_address'],instruction_rom_offset=row['rom_offset'],
                raw=row['raw'],mnemonic=row['mnemonic'],operands=row['op_str'],register_tokens=registers,
                memory_operand_text=memory,immediate_values=immediates,
                classification='Syntactic operand references only; register context and immediate pointer meaning not inferred.'))
    callees=[]
    for destination in sorted({call['target_cpu_address'] for call in calls if call['target_cpu_address']<0x100000}):
        callees.append(dict(cpu_address=destination,rom_offset=destination,
            existing_references=coverage_references(root,destination),
            classification='Directly encoded candidate callee; body not analyzed or executed by this inventory.'))
    marker=next(row for row in rows if row['cpu_address']<=0xc700<row['cpu_address']+row['size'])
    gap=dict(start_cpu_address=0xc6ce,start_rom_offset=0xc6ce,end_exclusive=0xc6da,
        size=12,sha256=hashlib.sha256(program[0xc6ce:0xc6da]).hexdigest(),
        classification='Data reference candidate, excluded from code decode.',
        evidence='c6c8 JMP leaves the contiguous code window; c6f8 LEA references c6ce. c5b0 BEQ targets c6da, used as explicit restart.')
    nearby=disassemble_range(program,0xc78e,6,0xc78e)
    assert int.from_bytes(program[0x180:0x182],'big')==0
    folder=Path(args.output);folder=folder if folder.is_absolute() else root/folder;folder.mkdir(parents=True,exist_ok=True)
    report=dict(source=source,decoder='Capstone '+capstone.__version__,cpu_model='M68000',program_code_modified=False,
        mapping='Fixed first MiB: CPU address equals canonical decrypted file offset.',
        requested_initial_start=0xc58a,initial_neighborhood_marker=0xc700,
        marker_falls_inside_instruction=marker['cpu_address']!=0xc700,marker_instruction=marker,
        analyzed_segments=segments,excluded_gap=gap,instruction_count=len(rows),
        direct_call_count=len(calls),direct_non_call_control_count=len(branches),
        direct_calls=calls,direct_branches_or_jumps=branches,register_memory_references=references,
        candidate_callee_references=callees,canonical_rom180_word=0,
        explicitly_checked_nearby_c78e=nearby,
        limitations='Inventory only, not gameplay interpretation or completed reverse engineering. '
            'No CPU execution, natural reachability, complete CFG, callee behavior or ABI context is proved. '
            'All straight decode boundaries and data/code distinctions retain their explicit evidence. '
            'The c700 marker bisects c6fc JSR, so that complete instruction is preserved; the requested '
            'neighborhood is expanded through c74c exclusive to include c724/c73e branch blocks. '
            'Branches leaving these segments are recorded, not followed. External BIOS addresses have no '
            'ROMoffset in this program. Textual docs/engine references are not implementation-equivalence evidence.')
    path=folder/'report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    listing=['; Original program SHA256 '+PROGRAM_SHA256,'; No execution or semantic completion claim.']
    for segment in segments:
        listing.extend(['','; Candidate code %06x..%06x'%(segment['start_rom_offset'],segment['end_exclusive']),asm(segment['instructions'])])
    listing.extend(['','; c6ce..c6da excluded: referenced data candidate, no instruction listing.',
        '; Explicit separate c78e instruction check (outside primary segments).',asm(nearby)])
    listing_path=folder/'inventory.asm';listing_path.write_text('\n'.join(listing)+'\n')
    print(json.dumps(dict(instructions=len(rows),calls=len(calls),branches=len(branches),
        external_targets=sorted({entry['target_cpu_address'] for entry in branches+calls if entry['target_rom_offset'] is None}),
        report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),asm_sha256=hashlib.sha256(listing_path.read_bytes()).hexdigest())))


if __name__=='__main__':main()
