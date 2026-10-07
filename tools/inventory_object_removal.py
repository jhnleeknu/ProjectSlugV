"""Bounded object-removal entry/callee candidates and textual reuse references."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import capstone
from disassemble_program import disassemble_range,load_verified_program
from inventory_game_initialization import asm,coverage_references
PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ENTRIES=(0x299c,0x2782,0x2a0a,0x2a84,0xc4cc)
CONTROL={'jsr','bsr','jmp','bra','beq','bne','bcc','bcs','bhi','bls','bge','bgt','ble','blt','bmi','bpl','bvc','bvs','dbra','dbf'}


def target(row):
    if row['mnemonic'].split('.')[0] not in CONTROL:return None
    match=re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\.w|\(pc\))?',row['op_str'])
    return int(match.group(1),16) if match else None


def listing(program,start,limit):
    rows=[]
    for row in disassemble_range(program,start,limit,start):
        assert row['rom_offset']+row['size']<=start+limit
        rows.append(row)
        if row['classification']!='candidate_instruction' or row['mnemonic']=='rts':break
    return rows


def fields(rows):
    result=[]
    for row in rows:
        refs=[]
        for match in re.finditer(r'(-?)\$([0-9a-f]+)\((a[0-7])\)',row['op_str']):
            refs.append(dict(base_register=match[3],displacement=(-1 if match[1] else 1)*int(match[2],16),operand=match[0]))
        for match in re.finditer(r'(?<![0-9a-f)])\((a[0-7])\)',row['op_str']):
            refs.append(dict(base_register=match[1],displacement=0,operand=match[0]))
        absolute=re.findall(r'(?<![#0-9a-f])\$[0-9a-f]+\.[lw]',row['op_str'])
        if refs or absolute:
            result.append(dict(instruction_cpu_address=row['cpu_address'],instruction_rom_offset=row['rom_offset'],
                raw=row['raw'],mnemonic=row['mnemonic'],operands=row['op_str'],register_relative_operands=refs,
                absolute_operand_text=absolute,
                classification='Encoded operand references only; no object layout, access role or inherited register context inferred.'))
    return result


def controls(rows):
    result=[]
    for row in rows:
        destination=target(row)
        if destination is not None:
            result.append(dict(instruction_cpu_address=row['cpu_address'],instruction_rom_offset=row['rom_offset'],
                raw=row['raw'],mnemonic=row['mnemonic'],operands=row['op_str'],target_cpu_address=destination,
                target_rom_offset=destination if destination<0x100000 else None,
                classification='Direct encoded control target candidate; execution not observed.'))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/object_removal');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==PROGRAM_SHA256 and hashlib.sha256(program).hexdigest()==PROGRAM_SHA256
    entries=[]
    for start in ENTRIES:
        rows=listing(program,start,0x100)
        entries.append(dict(cpu_address=start,rom_offset=start,max_bytes=0x100,instructions=rows,
            end_rom_offset_exclusive=rows[-1]['rom_offset']+rows[-1]['size'],
            first_linear_rts_seen=rows[-1]['mnemonic']=='rts',control_targets=controls(rows),memory_fields=fields(rows),
            existing_references=coverage_references(root,start),
            basis='Explicit supplied entry, contiguous bounded instruction candidates. Branch paths are not followed.'))
    helpers=[]
    helper_targets=sorted({entry['target_cpu_address'] for block in entries for entry in block['control_targets']
        if entry['mnemonic'].split('.')[0] in ('jsr','bsr','bra') and entry['target_cpu_address'] not in ENTRIES and entry['target_cpu_address']<0x100000
        and not any(block['rom_offset']<=entry['target_cpu_address']<block['end_rom_offset_exclusive'] for block in entries)})
    for start in helper_targets:
        rows=listing(program,start,0x80)
        helpers.append(dict(cpu_address=start,rom_offset=start,max_bytes=0x80,instructions=rows,
            end_rom_offset_exclusive=rows[-1]['rom_offset']+rows[-1]['size'],
            first_linear_rts_seen=rows[-1]['mnemonic']=='rts',control_targets=controls(rows),memory_fields=fields(rows),
            existing_references=coverage_references(root,start),
            basis='Bounded candidate listing at directly encoded call/tail-branch target; no recursive CFG or behavior analysis.'))
    reuse=[]
    for name in ('object_restart','object_lists','object_state','palette_allocator','position_state','main_startup'):
        paths=[root/'engine/include/ms5'/(name+'.h'),root/'engine/src'/(name+'.cpp')]
        refs=[]
        for path in paths:
            if not path.exists():continue
            for number,line in enumerate(path.read_text().splitlines(),1):
                if re.search(r'bool\s+\w+\s*\(|0x00299c|0x002790|0x008ff4|unlink|reset_object_fields',line):
                    refs.append(dict(path=str(path.relative_to(root)),line=number,text=line.strip()))
        reuse.append(dict(name=name,references=refs,classification='Textual implementation/API candidate only; equivalence and suitability require main-agent review.'))
    folder=Path(args.output);folder=folder if folder.is_absolute() else root/folder;folder.mkdir(parents=True,exist_ok=True)
    report=dict(source=source,decoder='Capstone '+capstone.__version__,cpu_model='M68000',program_code_modified=False,
        mapping='Fixed first MiB: CPU addresses equal canonical decrypted ROM offsets.',entries=entries,helper_candidates=helpers,
        primary_instruction_count=sum(len(entry['instructions']) for entry in entries),
        primary_control_target_count=sum(len(entry['control_targets']) for entry in entries),
        helper_target_count=len(helpers),reuse_candidates=reuse,
        limitations='No execution, reachability, complete control flow or semantic completion claimed. First linear RTS '
            'is a listing endpoint rather than proof all paths terminate. Branch targets outside windows may be '
            'shared tails or other routines; no ownership is inferred. Bounded helper windows may end before RTS or '
            'contain data; undecoded words stop the listing. disassemble_range rejects truncated instructions and '
            'each accepted row is checked to fit its requested range. Register displacements are exact encoded '
            'operands; object-field meanings and inherited register values are left to the main agent. '
            'Existing engine/docs matches and API candidates are textual crossreferences only.')
    path=folder/'report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    text=['; Original program SHA256 '+PROGRAM_SHA256,'; Candidate instruction inventory only; no execution/semantic equivalence claim.']
    for group,blocks in (('Explicit entry',entries),('Direct target helper candidate',helpers)):
        for block in blocks:text.extend(['','; '+group+' %06x, max%x bytes'%(block['rom_offset'],block['max_bytes']),asm(block['instructions'])])
    asm_path=folder/'inventory.asm';asm_path.write_text('\n'.join(text)+'\n')
    print(json.dumps(dict(primary_instructions=report['primary_instruction_count'],control_targets=report['primary_control_target_count'],
        helper_targets=helper_targets,report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),asm_sha256=hashlib.sha256(asm_path.read_bytes()).hexdigest())))


if __name__=='__main__':main()
