"""Stage-startup direct callees: bounded instruction and reuse-address inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import capstone
from disassemble_program import load_verified_program
from inventory_game_initialization import asm,coverage_references
from inventory_object_removal import listing,controls,fields
PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ENTRIES=(0x1a5a4,0xca48,0x1c5b0,0x4e24e,0x9056)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/stage_startup');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==PROGRAM_SHA256 and hashlib.sha256(program).hexdigest()==PROGRAM_SHA256
    blocks=[]
    for address in ENTRIES:
        limit=0x200 if address==0x1a5a4 else 0x80
        rows=listing(program,address,limit)
        assert all(row['rom_offset']+row['size']<=address+limit for row in rows)
        blocks.append(dict(cpu_address=address,rom_offset=address,max_bytes=limit,instructions=rows,
            decoded_end_exclusive=rows[-1]['rom_offset']+rows[-1]['size'],
            first_linear_rts_seen=rows[-1]['mnemonic']=='rts',control_targets=controls(rows),memory_operands=fields(rows),
            existing_references=coverage_references(root,address),
            basis='Explicit assigned original entry; contiguous bounded decode, stopping at firstRTS or undecoded word. '
                  '1a5a4 limit enlarged to512bytes because128bytes truncates an absolute CLR instruction before later calls.'))
    targets=sorted({entry['target_cpu_address'] for block in blocks for entry in block['control_targets']
        if entry['mnemonic'].split('.')[0] in ('jsr','bsr') and entry['target_cpu_address']<0x100000})
    helpers=[]
    for address in targets:
        rows=listing(program,address,0x80)
        helpers.append(dict(cpu_address=address,rom_offset=address,max_bytes=0x80,instructions=rows,
            decoded_end_exclusive=rows[-1]['rom_offset']+rows[-1]['size'],
            first_linear_rts_seen=rows[-1]['mnemonic']=='rts',controls=controls(rows),memory_operands=fields(rows),
            existing_references=coverage_references(root,address),
            classification='Direct-target bounded helper candidate only; no recursive reachability/behavior claim.'))
    families={
        'column':['column_control.h'],
        'sprite':['sprite_pool.h','sprite_queue.h','sprite_producer.h','sprite_prepare_queue.h','sprite_refresh_queue.h'],
        'video':['video_control.h','video_port.h','position_state.h'],
        'control_palette':['palette_control.h','palette_allocator.h','palette_prepare.h','main_startup.h','game_startup.h']}
    candidates=[]
    for family,names in families.items():
        for name in names:
            path=root/'engine/include/ms5'/name
            lines=path.read_text().splitlines();references=[]
            for index,line in enumerate(lines):
                if re.search(r'bool\s+\w+\s*\(|Native|native|CPU|0x[0-9a-f]+',line):
                    references.append(dict(line=index+1,text=line.strip()))
            candidates.append(dict(family=family,path=str(path.relative_to(root)),references=references,
                classification='API/header reference candidate; family grouping is organizational, not semantic or address-equivalence proof.'))
    folder=Path(args.output);folder=folder if folder.is_absolute() else root/folder;folder.mkdir(parents=True,exist_ok=True)
    report=dict(source=source,decoder='Capstone '+capstone.__version__,cpu_model='M68000',program_code_modified=False,
        mapping='Fixed first MiB: CPU address equals canonical decrypted ROM offset. Banked calls/data need separate mapping analysis.',
        explicit_entries=blocks,primary_instruction_count=sum(len(block['instructions']) for block in blocks),
        primary_direct_calls=[entry for block in blocks for entry in block['control_targets'] if entry['mnemonic'].split('.')[0] in ('jsr','bsr')],
        helper_candidate_count=len(helpers),helper_candidates=helpers,reuse_api_candidates=candidates,
        limitations='No original execution was observed; automatic decoding is not completed analysis. '
            'First linear RTS is a bounded endpoint, not proof every branch/callee returns or that all effects '
            'are represented. Internal branches and their raw target addresses are preserved but not followed. '
            'Helper128byte windows may truncate a longer routine or encounter data; undecoded words are explicit. '
            'disassemble_range handles incomplete instructions and every accepted row is range checked. '
            'Exact address textual references are distinguished from family API candidates; no reuse is '
            'declared behaviorally equivalent. Memory operand fields and port constants are exact syntactic '
            'evidence, without inferred background/scene meaning, register outputs or hardware timing.')
    path=folder/'report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    text=['; Original program SHA256 '+PROGRAM_SHA256,'; Candidate bounded listings only; no whole-path/behavior claim.']
    for label,entries in (('Explicit assigned entry',blocks),('Direct-target helper candidate',helpers)):
        for block in entries:text.extend(['','; '+label+' %06x..%06x, max%x bytes'%(block['rom_offset'],block['decoded_end_exclusive'],block['max_bytes']),asm(block['instructions'])])
    asm_path=folder/'inventory.asm';asm_path.write_text('\n'.join(text)+'\n')
    print(json.dumps(dict(instructions=report['primary_instruction_count'],direct_calls=len(report['primary_direct_calls']),
        unique_helper_targets=len(helpers),primary_endpoints=[hex(block['decoded_end_exclusive']) for block in blocks],
        report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),asm_sha256=hashlib.sha256(asm_path.read_bytes()).hexdigest())))


if __name__=='__main__':main()
