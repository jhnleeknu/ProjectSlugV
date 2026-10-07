"""Bounded fixed-ROM initialization call inventory; no behavioral inference."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import capstone
from disassemble_program import disassemble_range, load_verified_program

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
START, LIMIT, CALLEE_BYTES = 0x47570, 0x400, 0x40
EXPECTED_TARGETS = (0x100e,0x4755e,0x4823a,0xe8a1c,0x3af8,0x3d3a,0xb7a20,
    0x4d126,0x1bcfe,0x481de,0x481de,0x1bd12,0xe89fa,0x3d42,0x3dce,
    0x49a8e,0x4aa30,0xb4a24,0x2ef90,0x6f1c2,0x46f2e,0x4d13c,0x4ddb6)


def direct_target(row):
    if row['mnemonic'].split('.')[0] not in ('jsr','bsr'):
        return None
    match = re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\.w|\(pc\))?',row['op_str'])
    return int(match.group(1),16)&0xffffff if match else None


def bounded_rows(program,start,size):
    result=[]
    for row in disassemble_range(program,start,size,start):
        result.append(row)
        if row['classification'] != 'candidate_instruction' or row['mnemonic']=='rts':
            break
    return result


def coverage_references(root,target):
    # Text references only. They do not prove matching implementation effects,
    # routine reachability, complete coverage or a verified native callsite.
    pattern=re.compile(r'(?<![0-9a-f])(?:0x)?0*'+format(target,'x')+r'(?![0-9a-f])',re.I)
    groups={}
    for category in ('docs','engine'):
        matches=[]
        paths=sorted(path for path in (root/category).rglob('*') if path.suffix in ('.md','.cpp','.h'))
        for path in paths:
            for line_number,line in enumerate(path.read_text(errors='replace').splitlines(),1):
                if pattern.search(line):
                    matches.append({'path':str(path.relative_to(root)),'line':line_number,
                        'text':line.strip()[:320],'classification':'textual_address_reference_only'})
        groups[category]={'total_matches':len(matches),'shown_matches':matches[:12],
            'truncated':len(matches)>12}
    return groups


def asm(rows):
    return '\n'.join('%06x  %-24s %-9s %s'%(row['rom_offset'],row['raw'],row['mnemonic'],row['op_str']) for row in rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='artifacts/game_initialization')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!=PROGRAM_SHA256:
        raise ValueError('Unsupported original program')
    primary=bounded_rows(program,START,LIMIT)
    reached_rts=primary[-1]['mnemonic']=='rts'
    branch_rows=[row for row in primary if row['mnemonic'].split('.')[0] in
        ('bra','jmp','dbra','dbf','beq','bne','bcc','bcs','bge','bgt','ble','blt','bhi','bls','bmi','bpl','bvc','bvs')]
    calls=[]
    for row in primary:
        target=direct_target(row)
        if target is not None:
            calls.append({'instruction_cpu_address':row['cpu_address'],
                'instruction_rom_offset':row['rom_offset'],'raw':row['raw'],
                'mnemonic':row['mnemonic'],'operands':row['op_str'],
                'target_cpu_address':target,'target_rom_offset':target,
                'basis':'Contiguous decode from explicitly supplied original start47570.',
                'execution_observed':False})
    if tuple(call['target_cpu_address'] for call in calls)!=EXPECTED_TARGETS:
        raise ValueError('Reviewed primary direct-call sequence changed')
    callees=[]
    for target in sorted(set(call['target_cpu_address'] for call in calls)):
        rows=bounded_rows(program,target,min(CALLEE_BYTES,0x100000-target))
        callees.append({'cpu_address':target,'rom_offset':target,'max_bytes':CALLEE_BYTES,
            'decoded_end_rom_offset_exclusive':rows[-1]['rom_offset']+rows[-1]['size'],
            'rts_seen_in_candidate_window':rows[-1]['mnemonic']=='rts',
            'classification':'Candidate callee decode at directly encoded target; internal branch paths not followed.',
            'instructions':rows,'existing_references':coverage_references(root,target)})
    folder=Path(args.output)
    if not folder.is_absolute():folder=root/folder
    folder.mkdir(parents=True,exist_ok=True)
    report={'source':source,'decoder':'Capstone '+capstone.__version__,'cpu_model':'M68000',
        'program_code_modified':False,'mapping':'Fixed first MiB: CPU address equals canonical decrypted ROM offset.',
        'primary_start_cpu_address':START,'primary_start_rom_offset':START,
        'primary_max_bytes':LIMIT,'primary_decoded_bytes':sum(row['size'] for row in primary),
        'primary_end_rom_offset_exclusive':primary[-1]['rom_offset']+primary[-1]['size'],
        'linear_window_reaches_rts':reached_rts,'primary_non_call_branch_count':len(branch_rows),
        'primary_non_call_branches':branch_rows,'direct_call_count':len(calls),
        'unique_direct_target_count':len(callees),'primary_instructions':primary,
        'direct_calls':calls,'callee_candidate_windows':callees,
        'limitations':'Primary instruction boundaries are supported by contiguous decoding from the explicitly supplied start and pinned bytes. '
            'No original execution was observed. First linear RTS is a bounded endpoint, not proof that every callee returns or that whole-function behavior is understood. '
            'Callee windows may include data after branches or omit paths; their decoding is not analysis completion. '
            'Documentation/engine address matches are textual crossreferences, not proof of implementation equivalence or complete coverage. '
            'No raw byte scan is presented as a confirmed code reference, and no gameplay meaning is inferred.'}
    report_path=folder/'report.json'
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    listing=['; Fixed ROM; original program SHA256 '+PROGRAM_SHA256,
        '; Primary explicit-start bounded contiguous decode; no execution/behavior claim.',asm(primary)]
    for callee in callees:
        listing.extend(['','; Candidate callee %06x, at most %x bytes; branch paths not followed.'%(callee['rom_offset'],CALLEE_BYTES),asm(callee['instructions'])])
    asm_path=folder/'inventory.asm'
    asm_path.write_text('\n'.join(listing)+'\n')
    assert hashlib.sha256(program).hexdigest()==PROGRAM_SHA256
    print(json.dumps({'calls':len(calls),'unique_targets':len(callees),
        'primary_bytes':report['primary_decoded_bytes'],'rts':reached_rts,
        'non_call_branches':len(branch_rows),'report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'asm_sha256':hashlib.sha256(asm_path.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
