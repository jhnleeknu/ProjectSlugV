"""Exact bounded screen-reset instruction inventory and reuse reference candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import capstone
from disassemble_program import disassemble_range,load_verified_program
from inventory_game_initialization import asm,coverage_references
from inventory_object_removal import controls,fields
PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
RANGES=((0xca9e,0xcaf0),(0xcaf0,0xcb64),(0x35a2,0x35f0))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/game_screen_reset');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==PROGRAM_SHA256 and hashlib.sha256(program).hexdigest()==PROGRAM_SHA256
    blocks=[]
    for start,end in RANGES:
        rows=disassemble_range(program,start,end-start,start)
        assert all(row['classification']=='candidate_instruction' and row['rom_offset']+row['size']<=end for row in rows)
        assert rows[-1]['rom_offset']+rows[-1]['size']==end and rows[-1]['mnemonic']=='rts'
        blocks.append(dict(cpu_address=start,rom_offset=start,end_exclusive=end,instructions=rows,
            controls=controls(rows),memory_operands=fields(rows),existing_references=coverage_references(root,start),
            data_register_operand_rows=[row for row in rows if any('d'+str(reg) in row['op_str'] for reg in (0,1,3))],
            basis='Explicit original entry and complete bounded instructions through final linear RTS; no execution claim.'))
    reuse=[]
    for relative,first,last,reason in (
        ('engine/src/control_menu_start.cpp',6,12,'Shared VideoPortWrite long-write constructor candidate.'),
        ('engine/src/control_menu_start.cpp',26,32,'Existing ca9e ordered-write construction, embedded in menu-start API.'),
        ('engine/include/ms5/control_menu_start.h',10,19,'Current menu-start optional D1/D3 contract; whole menu behavior, not caf0 API.'),
        ('engine/include/ms5/video_port.h',7,16,'Common ordered address/value/byte-size port record.'),
        ('tools/verify_control_menu_start.py',76,90,'Current native-port serialization and ca9e regression expectations.'),
        ('engine/include/ms5/fixed_text.h',65,81,'Existing direct fixed-text renderer API candidate, requiring behavior review.')):
        path=root/relative;lines=path.read_text().splitlines()
        reuse.append(dict(path=relative,first_line=first,last_line=last,text='\n'.join(lines[first-1:last]),
            reason=reason,classification='Source/reference candidate only; no35a2 behavior equivalence asserted.'))
    absolute_writes=[]
    for block in blocks:
        for row in block['instructions']:
            if row['cpu_address'] in (0x35a2,0x35e0):absolute_writes.append(row)
    folder=Path(args.output);folder=folder if folder.is_absolute() else root/folder;folder.mkdir(parents=True,exist_ok=True)
    report=dict(source=source,decoder='Capstone '+capstone.__version__,cpu_model='M68000',program_code_modified=False,
        mapping='Fixed first MiB: CPU addresses equal canonical decrypted ROM offsets.',
        requested_primary_range=[0xca9e,0xcb64],explicit_callee_range=[0x35a2,0x35f0],
        blocks=blocks,instruction_count=sum(len(block['instructions']) for block in blocks),
        direct_call_count=sum(entry['mnemonic'].split('.')[0] in ('jsr','bsr') for block in blocks for entry in block['controls']),
        explicit_absolute_write_instructions=absolute_writes,
        indirect_port_address_load_instructions=[row for block in blocks for row in block['instructions'] if row['cpu_address'] in (0xca9e,0xcaf2,0x35a8)],
        reuse_candidates=reuse,
        limitations='Exact instruction operands/control targets are evidence, not completed semantic analysis. '
            'No execution, port count, final register computation, trap behavior or natural caller equivalence '
            'is claimed. ca9e/caf0 have aligned complete ends; cb64 begins outside the requested range. '
            '35a2 loop/TRAP paths need main-agent interpretation. Existing ca9e constructor and port format '
            'are reuse candidates; no standalone35a2 implementation was found by address-reference search. '
            'All accepted instructions fit the real supplied range; disassemble_range handles truncated '
            'instructions separately, and no undecoded words appear in these explicit ranges.')
    path=folder/'report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    text=['; Original program SHA256 '+PROGRAM_SHA256,'; Candidate code only, no native execution or semantic completion claim.']
    for block in blocks:text.extend(['','; Explicit range %06x..%06x'%(block['rom_offset'],block['end_exclusive']),asm(block['instructions'])])
    asm_path=folder/'inventory.asm';asm_path.write_text('\n'.join(text)+'\n')
    print(json.dumps(dict(instructions=report['instruction_count'],calls=report['direct_call_count'],
        report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),asm_sha256=hashlib.sha256(asm_path.read_bytes()).hexdigest())))


if __name__=='__main__':main()
