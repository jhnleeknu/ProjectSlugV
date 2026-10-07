"""Bounded ready/callback candidates, exact references and textual reuse evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import capstone
from disassemble_program import disassemble_range,load_verified_program
from inventory_game_initialization import asm,coverage_references
from inventory_object_removal import listing,controls,fields
PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
RANGES=((0xc654,0xc6ce),(0x289e,0x28ae),(0x314c,0x3162),
        (0x477e4,0x478ac),(0x478ac,0x478c4),(0x478c4,0x479b0))


def fixed_references(rows):
    refs=[]
    for row in rows:
        # Syntactic constants and PC references only: no automatic data typing.
        for match in re.finditer(r'#\$([0-9a-f]+)|\$([0-9a-f]+)(?:\.l|\(pc(?:,[^)]*)?\))',row['op_str']):
            value=int(match[1] or match[2],16)
            if 0x100<=value<0x100000:
                refs.append(dict(instruction_cpu_address=row['cpu_address'],instruction_rom_offset=row['rom_offset'],
                    raw=row['raw'],mnemonic=row['mnemonic'],operands=row['op_str'],
                    referenced_cpu_address=value,referenced_rom_offset=value,
                    classification='Fixed-address operand candidate; code/data/pointer semantics not inferred.'))
    return refs


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/game_ready');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==PROGRAM_SHA256 and hashlib.sha256(program).hexdigest()==PROGRAM_SHA256
    blocks=[]
    for start,end in RANGES:
        rows=disassemble_range(program,start,end-start,start)
        assert all(row['classification']=='candidate_instruction' and row['rom_offset']+row['size']<=end for row in rows)
        assert rows[-1]['rom_offset']+rows[-1]['size']==end
        blocks.append(dict(cpu_address=start,rom_offset=start,end_exclusive=end,instructions=rows,
            control_targets=controls(rows),memory_operand_references=fields(rows),fixed_address_references=fixed_references(rows),
            classification='Encoded BRA dispatch entries, not a data table.' if start==0x478ac else
                'Explicit-start contiguous candidate instructions; not an execution trace.'))
    primary=[row for block in blocks for row in block['instructions']]
    callback=[row for block in blocks if 0x477e4<=block['cpu_address']<0x479b0 for row in block['instructions']]
    target_addresses=sorted({entry['target_cpu_address'] for entry in controls(primary)
        if entry['mnemonic'].split('.')[0] in ('jsr','bsr') and entry['target_cpu_address']<0x100000})
    helpers=[]
    for address in target_addresses:
        if address in (0x289e,0x314c):continue
        # Include both47540 return branches; other helpers retain bounded firstRTS endpoint.
        rows=disassemble_range(program,address,0x1e,address) if address==0x47540 else listing(program,address,0x40)
        helpers.append(dict(cpu_address=address,rom_offset=address,max_bytes=0x1e if address==0x47540 else 0x40,
            instructions=rows,end_exclusive=rows[-1]['rom_offset']+rows[-1]['size'],
            controls=controls(rows),fixed_address_references=fixed_references(rows),
            existing_references=coverage_references(root,address),
            classification='Bounded callee candidate; direct target encoding only, not whole body/path analysis.'))
    reuse=[]
    for relative in ('engine/include/ms5/object_restart.h','engine/src/object_restart.cpp',
            'engine/include/ms5/input_sampler.h','engine/src/input_sampler.cpp',
            'engine/include/ms5/stage_catalog.h','engine/src/stage_catalog.cpp'):
        path=root/relative;matches=[]
        for number,line in enumerate(path.read_text().splitlines(),1):
            if re.search(r'bool\s+\w+\s*\(|2a28|314c|289e|474e2|47540|4cd4|object \+0x10|0x10U',line):
                matches.append(dict(line=number,text=line.strip()))
        reuse.append(dict(path=relative,matches=matches,
            classification='Textual API/source candidate only; behavior, carry flags and register equivalence require main review.'))
    folder=Path(args.output);folder=folder if folder.is_absolute() else root/folder;folder.mkdir(parents=True,exist_ok=True)
    report=dict(source=source,decoder='Capstone '+capstone.__version__,cpu_model='M68000',program_code_modified=False,
        mapping='Fixed first MiB: CPU address equals canonical decrypted ROM offset.',blocks=blocks,
        primary_instruction_count=len(primary),callback_instructions=len(callback),
        callback_direct_calls=[entry for entry in controls(callback) if entry['mnemonic'].split('.')[0] in ('jsr','bsr')],
        callback_fixed_reference_candidates=fixed_references(callback),helper_candidates=helpers,reuse_candidates=reuse,
        explicit_stage_index_reference=dict(instruction_cpu_address=0x474ee,table_cpu_address=0x474f4,table_rom_offset=0x474f4,
            basis='MOVEA.L $474f4(PC,D0.word),A0 in bounded474e2 helper; table bytes are not decoded as instructions.'),
        excluded_gap=dict(start=0xc6ce,end_exclusive=0xc6da,classification='Previously reviewed referenced-data gap; outside ready code listing.'),
        limitations='Listing/reference inventory only; no execution or completed behavior analysis.314c includes both '
            'RTS branches explicitly, preventing a firstRTS listing from dropping315c.477e4 is bounded through479b0 '
            'exclusive and is not a complete callback body. Its indexed JMP478a8 and six BRA entries478ac..478c4 '
            'are recorded without resolving runtime selector or following all paths. Branches outside windows '
            'and later callback continuations are not analyzed. No standalone289e/314c API was found by exact '
            'address-reference search; existing input code mode4cd4 and static restart are reuse candidates only. '
            'Fixed address constants include code, script and unknown data; none is automatically declared a table. '
            'Truncated instructions are rejected by disassemble_range; all primary ends are checked exact. '
            'No CCR semantics, final registers, natural scheduling or BIOS behavior is inferred.')
    path=folder/'report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    text=['; Original program SHA256 '+PROGRAM_SHA256,'; No execution or completed semantics claim.']
    for group,candidates in (('Explicit bounded block',blocks),('Callee candidate',helpers)):
        for block in candidates:text.extend(['','; '+group+' %06x..%06x'%(block['rom_offset'],block['end_exclusive']),asm(block['instructions'])])
    asm_path=folder/'inventory.asm';asm_path.write_text('\n'.join(text)+'\n')
    print(json.dumps(dict(instructions=len(primary),callback_instructions=len(callback),
        callback_calls=len(report['callback_direct_calls']),callee_candidates=len(helpers),
        report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),asm_sha256=hashlib.sha256(asm_path.read_bytes()).hexdigest())))


if __name__=='__main__':main()
