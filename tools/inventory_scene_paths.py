"""Fixed-ROM scene path syntax candidates; no interpreter execution claim."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program, disassemble_range
from pack_scene_scripts import SOURCE_SHA256, command_span

PAYLOAD={0:4,4:12,8:12,12:12,16:12,20:12,24:6,28:4}
BRANCH={8,12,16,20}


def walk(program,root):
    rows={}; edges=[]; errors=[]; occupied={}; colors={}; cycles=[]
    stack=[('enter',root,0,None)]
    while stack:
        action,address,depth,edge=stack.pop()
        if action=='exit':colors[address]=2;continue
        if colors.get(address)==1:
            if edge is not None:cycles.append(edge)
            continue
        if address in rows:continue
        if depth>4096 or sum(row['size']for row in rows.values())>=65536:
            errors.append(dict(address=address,error='bounded_graph_limit'));continue
        if address&1 or not 0<=address<0x100000-1:
            errors.append(dict(address=address,error='unaligned_or_outside_fixed_ROM'));continue
        if address+2>len(program):
            errors.append(dict(address=address,error='truncated_opcode'));continue
        if address in occupied and occupied[address]!=address:
            errors.append(dict(address=address,error='overlapping_instruction',conflicts=[occupied[address]]));continue
        opcode=struct.unpack_from('>H',program,address)[0]
        terminal=bool(opcode&0x8000)
        if not terminal and opcode not in PAYLOAD:
            errors.append(dict(address=address,opcode=opcode,raw_hex=program[address:address+16].hex(),error='unknown_opcode'));continue
        size=2 if terminal else 2+PAYLOAD[opcode]
        if address+size>min(0x100000,len(program)):
            errors.append(dict(address=address,error='truncated_command'));continue
        conflicts=sorted({occupied[b]for b in range(address,address+size)if b in occupied and occupied[b]!=address})
        if conflicts:
            errors.append(dict(address=address,error='overlapping_instruction',conflicts=conflicts));continue
        for b in range(address,address+size):occupied[b]=address
        row=dict(cpu_address=address,rom_offset=address,opcode_word=opcode,terminal=terminal,size=size,
            raw_hex=program[address:address+size].hex(),operand_raw_hex=program[address+2:address+size].hex())
        rows[address]=row;colors[address]=1
        stack.append(('exit',address,depth,None))
        if terminal:colors[address]=2;continue
        targets=[('sequential',address+size)]
        if opcode==4:
            fields=struct.unpack_from('>4HI',program,address+2)
            row.update(descriptor_raw_hex=program[address+2:address+14].hex(),descriptor_cpu_address=address+2,
                map_selector_word=fields[0],secondary_selector_word=fields[1],word_at_2=fields[1],width_word=fields[2],height_word=fields[3],column_pointer_long=fields[4])
        if opcode in BRANCH:
            fields=struct.unpack_from('>4HI',program,address+2)
            row.update(condition_offset_word=fields[0],flags_word=fields[1],word_at_operand_4=fields[2],word_at_operand_6=fields[3],branch_pointer_long=fields[4])
            targets.append(('branch',fields[4]))
        for kind,target in targets:
            edges.append(dict(from_cpu_address=address,to_cpu_address=target,kind=kind))
        for kind,target in reversed(targets):
            edge=dict(from_cpu_address=address,to_cpu_address=target,kind=kind)
            stack.append(('enter',target,depth+1,edge))
    return dict(root_cpu_address=root,root_rom_offset=root,rows=[rows[a]for a in sorted(rows)],
        edges=edges,cycle_edges=cycles,errors=errors,status='syntax_candidates'if not errors else'unsupported_candidates',
        reachable_row_count=len(rows),descriptor_addresses=[a+2 for a in sorted(rows)if rows[a]['opcode_word']==4])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/scene_paths');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=SOURCE_SHA256:raise ValueError('Unsupported source SHA')
    manifest_path=root/'extracted/runtime/scene_scripts/manifest.json';manifest=json.loads(manifest_path.read_text());refs=[]
    for script in manifest['scripts']:
        address=script['source_cpu_address'];end,commands,terminal=command_span(program,address)
        if end!=script['end_exclusive']or hashlib.sha256(program[address:end]).hexdigest()!=script['payload_sha256']:raise ValueError('Script manifest/source mismatch')
        for command in commands:
            if command['opcode']!=0x24:continue
            raw=bytes.fromhex(command['operand_hex']);selector,pointer=struct.unpack('>HI',raw)
            refs.append(dict(script_cpu_address=address,command_cpu_address=command['source_cpu_address'],selector_word=selector,pointer_long=pointer,operand_raw_hex=raw.hex()))
    paths=[walk(program,p)for p in sorted({r['pointer_long']for r in refs if r['pointer_long']})]
    for path in paths:path['references']=[r for r in refs if r['pointer_long']==path['root_cpu_address']]
    unique={row['cpu_address']:row for path in paths for row in path['rows']}
    descriptors=[row for row in unique.values()if row['opcode_word']==4]
    scope='Main-confirmed syntax CFG candidates only: both conditional successors followed, visited cycles bounded. No interpreter execution, branch feasibility, descriptor behavior, frame scheduling or resource extraction claim.'
    report=dict(source=source,program_code_modified=False,mapping='Fixed first1MiB CPU addresses equal ROM offsets.',
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),references=refs,paths=paths,
        reference_count=len(refs),nonzero_reference_count=sum(bool(r['pointer_long'])for r in refs),unique_root_count=len(paths),
        unique_row_count=len(unique),unique_descriptor_count=len(descriptors),descriptor_distribution=[dict(map_selector_word=k[0],word_at_2=k[1],width_word=k[2],height_word=k[3],column_pointer_long=k[4],count=v)for k,v in sorted(Counter((r['map_selector_word'],r['word_at_2'],r['width_word'],r['height_word'],r['column_pointer_long'])for r in descriptors).items())],opcode_counts=dict(sorted(Counter(row['opcode_word']for row in unique.values()).items())),
        error_count=sum(len(p['errors'])for p in paths),cycle_edge_count=sum(len(p['cycle_edges'])for p in paths),scope=scope)
    windows=[]
    for start,end in ((0x19e64,0x1a07a),(0x16ff8,0x17012),(0x1861a,0x1879c),(0x16f0e,0x16f9a),(0x183c6,0x185fa)):
        instructions=disassemble_range(program,start,end-start,start)
        assert sum(row['size']for row in instructions)==end-start
        windows.append(dict(start_cpu_address=start,start_rom_offset=start,end_exclusive=end,raw_sha256=hashlib.sha256(program[start:end]).hexdigest(),instructions=instructions))
    listing=dict(source=source,scope='Explicit bounded raw instruction candidates, not full routine analysis; window endpoints are supplied bounds, not inferred completion.',windows=windows)
    output=Path(args.output);output=output if output.is_absolute()else root/output;output.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name,data in(('inventory.json',report),('disassembly.json',listing)):
        path=output/name;path.write_text(json.dumps(data,indent=2)+'\n');hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(dict(references=len(refs),roots=len(paths),rows=len(unique),errors=report['error_count'],cycles=report['cycle_edge_count'],sha256=hashes)))

if __name__=='__main__':main()
