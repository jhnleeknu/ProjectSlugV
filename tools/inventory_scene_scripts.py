"""Fixed-ROM scene script syntax candidates; no native execution/meaning claims."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program,disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import controls
from pack_stage_catalog import decode_group,INDEX,COUNT

PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
OPERAND_BYTES={0x00:8,0x04:2,0x08:4,0x0c:4,0x10:4,0x14:6,0x18:6,0x1c:4,0x20:2,0x24:6,
    0x28:2,0x2c:6,0x30:8,0x34:2,0x38:8,0x3c:2,0x40:2,0x44:4,0x48:2,0x4c:4}
MAX_BYTES=65536
MAX_ROWS=32768


def decode_script(program,address):
    if address==0:return dict(cpu_address=0,rom_offset=0,status='null_pointer_not_decoded',rows=[])
    rows=[];cursor=address;end=min(0x100000,address+MAX_BYTES);status='bounded_limit_without_terminator';error=None
    if address&1 or not 0<=address<0x100000:
        return dict(cpu_address=address,rom_offset=None,status='unsupported_pointer',rows=[],error='Pointer is not even fixed ROM')
    for _ in range(MAX_ROWS):
        if cursor+2>end:break
        start=cursor;opcode=struct.unpack_from('>H',program,cursor)[0];cursor+=2
        row=dict(cpu_address=start,rom_offset=start,opcode_word=opcode,opcode_raw=program[start:cursor].hex())
        if opcode&0x8000:
            row['classification']='negative_word_terminator_candidate';rows.append(row);status='negative_word_terminator';break
        if opcode not in OPERAND_BYTES:
            row['classification']='unknown_opcode';rows.append(row);status='unknown_opcode';error='Unknown opcode preserved at0x%x'%start;break
        size=OPERAND_BYTES[opcode]
        if cursor+size>end:
            row['classification']='truncated_operands';row['available_raw']=program[cursor:end].hex();rows.append(row)
            status='truncated_operands';error='Operands exceed fixed/bounded window';break
        operands=program[cursor:cursor+size];cursor+=size
        row.update(classification='syntax_candidate',operand_size=size,operand_raw=operands.hex(),end_after_operands=cursor)
        if opcode==0x2c:
            skip=struct.unpack_from('>h',operands,4)[0];row['third_operand_signed_skip']=skip
            if skip<0:
                rows.append(row);status='unsupported_negative_skip';error='Negative inline skip requires control-flow interpretation';break
            if cursor+skip>end:
                rows.append(row);status='truncated_inline_block';error='Inline skip exceeds fixed/bounded window';break
            row['opaque_inline_block']=dict(cpu_address=cursor,rom_offset=cursor,size=skip,raw_hex=program[cursor:cursor+skip].hex(),
                sha256=hashlib.sha256(program[cursor:cursor+skip]).hexdigest(),classification='Opaque skipped bytes, not recursively decoded')
            cursor+=skip
            if skip&1:
                row['next_cpu_address']=cursor;row['classification']='unsupported_odd_skip';rows.append(row)
                status='unsupported_odd_skip';error='Odd inline skip would leave next opcodeword unaligned; native address-error unsupported';break
        row['next_cpu_address']=cursor;rows.append(row)
    return dict(cpu_address=address,rom_offset=address,end_exclusive=cursor,status=status,error=error,rows=rows,
        raw_consumed_sha256=hashlib.sha256(program[address:cursor]).hexdigest(),window_limit=end,
        classification='Bounded script syntax candidate only; opcode effects/reachability not executed')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/scene_scripts');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=PROGRAM_SHA256:raise ValueError('Unsupported canonical program')
    references=[]
    for group,address in enumerate(struct.unpack_from('>19I',program,INDEX)):
        for area,record in enumerate(decode_group(program,address)['records']):
            cpu=record['source_cpu_address'];pointer=struct.unpack_from('>I',program,cpu+2)[0]
            references.append(dict(stage_group=group,area_index=area,record_cpu_address=cpu,record_rom_offset=cpu,
                pointer_field_cpu_address=cpu+2,pointer_field_raw=program[cpu+2:cpu+6].hex(),script_cpu_address=pointer,
                script_rom_offset=pointer if pointer<0x100000 else None))
    addresses=sorted({r['script_cpu_address'] for r in references});scripts=[decode_script(program,a) for a in addresses]
    code=disassemble_range(program,0x1a0bc,0x1a26a-0x1a0bc,0x1a0bc)
    dispatcher=disassemble_range(program,0x1a0b6,6,0x1a0b6)
    termination_gate=disassemble_range(program,0x1a26a,0x1a29c-0x1a26a,0x1a26a)
    dispatch_entries=[]
    for opcode,size in OPERAND_BYTES.items():
        entry_address=0x1a0bc+opcode
        entry_rows=disassemble_range(program,entry_address,4,entry_address)
        targets=controls(entry_rows)
        if len(entry_rows)!=1 or len(targets)!=1 or entry_rows[0]['mnemonic']!='bra.w':
            raise ValueError('Expected4-byte BRA opcode dispatch entry changed')
        dispatch_entries.append(dict(opcode=opcode,operand_bytes=size,dispatch_cpu_address=entry_address,
            branch_instruction=entry_rows[0],target_cpu_address=targets[0]['target_cpu_address'],
            length_basis='Main-confirmed handleroperand map; fullhandlercandidatebytes preserved for manual instruction comparison, not automaticbehavior proof'))
    assert all(0<a<0x100000 and a%2==0 for a in addresses if a)
    assert len(references)==59 and len(addresses)==42 and addresses[0]==0 and len([r for r in references if r['script_cpu_address']==0])==4
    report=dict(source=source,program_code_modified=False,mapping='Fixed first1MiB CPU addresses equal ROM offsets.',
        record_references=references,record_count=len(references),unique_pointer_count=len(addresses),nonzero_pointer_count=len(addresses)-1,
        null_record_count=sum(r['script_cpu_address']==0 for r in references),scripts=scripts,
        opcode_operand_bytes=[dict(opcode=op,operand_bytes=size,basis='Main-confirmed operand lengths; syntax inventory, not behavior analysis') for op,size in OPERAND_BYTES.items()],
        dispatcher_entry_instructions=dispatcher,termination_phasegate_candidate_window=termination_gate,opcode_dispatch_entries=dispatch_entries,full_dispatcher_candidate_window=code,
        limits=dict(max_bytes_per_script=MAX_BYTES,max_rows_per_script=MAX_ROWS),
        status_counts={status:sum(s['status']==status for s in scripts) for status in sorted({s['status'] for s in scripts})},
        limitations='No native script execution. LeadingBE16 opcode branches via1a0bc+signedword as main confirmed; '
            'negativeword termination is syntax only. Opcode2c reads3words and skips signedthird operand; positive '
            'inlinebytes remainopaque, negative/odd skip explicitlyunsupported. Unknown/truncated records preserve error evidence. '
            'All41 nonzero pointers fixed<1MiB, but logical ownership/natural reachability and opcode sideeffects unproven.')
    output=Path(args.output);output=output if output.is_absolute() else root/output;output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    listing=['; decoder1a0b6 and full assigned1a0bc..1a26a window, not complete ownership.',asm(dispatcher),asm(code),'; termination/phasegate1a26a..1a29c fullcandidatewindow',asm(termination_gate)]
    for script in scripts:
        listing.append('; script %06x: %s'%(script['cpu_address'],script['status']))
        for row in script['rows']:
            listing.append('%06x opcode=%04x operands=%s %s'%(row['cpu_address'],row['opcode_word'],row.get('operand_raw',''),row['classification']))
            if 'opaque_inline_block' in row:listing.append('; opaque inlineblock %s'%row['opaque_inline_block'])
    (output/'inventory.asm').write_text('\n'.join(listing)+'\n')
    print(json.dumps(dict(records=len(references),unique_pointers=len(addresses),status_counts=report['status_counts'],
        script_rows=sum(len(s['rows']) for s in scripts),report_sha256=hashlib.sha256((output/'report.json').read_bytes()).hexdigest(),
        asm_sha256=hashlib.sha256((output/'inventory.asm').read_bytes()).hexdigest())))


if __name__=='__main__':main()
