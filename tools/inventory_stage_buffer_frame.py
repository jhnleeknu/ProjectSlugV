"""Bounded buffer-frame source instructions and existing raw8 resource fixtures."""
import collections
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program
from inventory_game_initialization import asm
from inventory_object_removal import CONTROL, target
from inventory_stage_input_callbacks import bounded, require, sha
from observe_scene_general_initialization import resources
from pack_stage_input import SOURCE_SHA256

WINDOWS = ((0x4aa88,0x4abc0),(0x4b784,0x4b82e),(0xcd58,0xce02))
CONTRACT = 'docs/analysis/stage-buffer-frame.md'
LITERALS = (
    (0x4aa96,'lea.l','$10daf8.l, a4'),
    (0x4aa9e,'movea.l','(a4), a6'),
    (0x4aaa0,'movea.l','$4(a4), a0'),
    (0x4aab4,'move.b','$6d(a6), d6'),
    (0x4aab8,'andi.b','#$f, d6'),
    (0x4aaca,'move.l','#$122b, d7'),
    (0x4aad0,'jsr','$4b784(pc)'),
    (0x4aad4,'move.w','(a7)+, d7'),
    (0x4aad8,'move.w','#$0, -$7ff0(a5)'),
    (0x4aade,'move.w','#$1000, $2ffff2.l'),
    (0x4aae6,'move.w','#$0, $2ffff0.l'),
    (0x4aaee,'addq.w','#$1, d7'),
    (0x4aaf0,'lea.l','$8(a4), a4'),
    (0x4aaf4,'cmpa.l','#$10db78, a4'),
    (0x4ab00,'movea.l','$5c88(a5), a0'),
    (0x4ab24,'cmpa.l','#$10dc88, a0'),
    (0x4ab32,'move.l','a0, $5c88(a5)'),
    (0x4ab74,'lea.l','$5746(a5), a4'),
    (0x4ab78,'lea.l','$5918(a5), a3'),
    (0x4ab7c,'bchg.b','#$7, $5744(a5)'),
    (0x4ab86,'exg.l','a3, a4'),
    (0x4ab8a,'clr.w','$1d0(a4)'),
    (0x4ab9e,'lea.l','$d0(a4), a4'),
    (0x4b798,'move.l','(a0)+, d0'),
    (0x4b7d4,'jsr','$cd58.l'),
    (0x4b7e2,'move.w','(a0)+, d2'),
    (0x4b7e4,'move.w','(a0)+, d3'),
    (0x4b7e6,'eori.w','#$3, d1'),
    (0x4b80e,'jsr','$cd58.l'),
    (0x4b816,'move.w','#$0, -$7ff0(a5)'),
    (0x4b81c,'move.w','#$1000, $2ffff2.l'),
    (0x4b824,'move.w','#$0, $2ffff0.l'),
    (0xcd58,'movea.l','$1152(a5), a0'),
    (0xcd5c,'jsr','(a0)'))


def resource_fixtures(root,program):
    items,manifests = resources(root,program)
    kinds = collections.Counter(r['kind'] for r in items)
    require(len(items)==458 and kinds=={1:187,2:271},'Canonical existing resource input set changed')
    selected=[]
    for role in ('fixed','bank2','bank3'):
        candidates=[]
        for item in items:
            if item['size'] < 8:continue
            cpu,rom=item['cpu'],item['rom']
            eligible=(role=='fixed' and item['kind']==1 and cpu==rom and cpu+8<=0x100000
                or role=='bank2' and item['kind']==2 and 0x200000<=cpu and cpu+8<=0x2ffff0 and rom==cpu
                or role=='bank3' and item['kind']==2 and 0x200000<=cpu and cpu+8<=0x2ffff0 and rom==cpu+0x100000)
            if eligible:candidates.append(item)
        require(candidates,'Missing existing source-verified raw8 resource fixture for '+role)
        item=candidates[0]  # Existing helper order, no gameplay-based selection.
        packed=(root/item['file']).read_bytes();cpu,rom=item['cpu'],item['rom']
        raw=packed[32:40]
        require(len(raw)==8 and raw==program[rom:rom+8],'Selected raw8/source mismatch')
        selected.append(dict(role=role,file=item['file'],container_sha256=item['sha256'],kind=item['kind'],
            resource_source_cpu_address=cpu,resource_source_rom_offset=rom,resource_payload_size=item['size'],
            source_cpu_address=cpu,source_rom_offset=rom,end_cpu_address_exclusive=cpu+8,
            end_rom_offset_exclusive=rom+8,byte_count=8,raw_hex=raw.hex(),raw_sha256=sha(raw),
            mapping='CPU=ROM fixed' if role=='fixed' else 'CPU2MiB window maps originalROM2MiB bank' if role=='bank2' else 'CPU2MiB window maps originalROM3MiB bank; ROM=CPU+1MiB',
            scope='First8 literal payload bytes of an existing verified resource, chosen in existing helper order. '
                  'Read-fixture evidence only, not a bounds record, logical table extent, original gameplay use, or natural bank-selection claim.'))
    for item in items+manifests:
        require(sha((root/item['file']).read_bytes())==item['sha256'],'Existing resource/manifest changed during read audit')
    return dict(helper='observe_scene_general_initialization.resources(root, program)',
        resource_count=len(items),counts_by_kind=dict(sorted(kinds.items())),
        resource_set_sha256=sha((json.dumps(items,indent=2)+'\n').encode()),
        manifests=manifests,resource_read_fixtures=selected,regenerated_resource_files=False)


def inventory(root):
    program,source=load_verified_program(root)
    require(source['sha256']==SOURCE_SHA256 and sha(program)==SOURCE_SHA256,'Unsupported pinned original source')
    paths=('tools/inventory_stage_buffer_frame.py','tools/disassemble_program.py',
        'tools/inventory_stage_input_callbacks.py','tools/observe_scene_general_initialization.py')
    provenance=[dict(file=p,sha256=sha((root/p).read_bytes())) for p in paths]
    windows=[bounded(program,a,b) for a,b in WINDOWS]
    indexed={r['cpu_address']:r for w in windows for r in w['instructions']}
    controls,indirect=[],[]
    for window in windows:
        direct=[]
        for row in window['instructions']:
            if row['classification']!='candidate_instruction' or row['mnemonic'].split('.')[0] not in CONTROL:continue
            destination=target(row)
            item=dict(instruction=row,literal_target_cpu_address=destination,
                literal_target_rom_offset=destination if destination is not None and destination<0x100000 else None)
            if destination is None:indirect.append(item)
            else:direct.append(item);controls.append(item)
        window['direct_control_operands']=direct
    require([(r['instruction']['cpu_address'],r['instruction']['mnemonic'],r['instruction']['op_str']) for r in indirect]
        ==[(0xcd5c,'jsr','(a0)')],'Assigned indirect callback instruction changed')
    evidence=[]
    for at,mnemonic,operand in LITERALS:
        row=indexed[at]
        require(row['mnemonic']==mnemonic and row['op_str']==operand,'Literal buffer-frame instruction changed')
        evidence.append(row)
    shifts=[indexed[at] for at in range(0x4ab04,0x4ab24,2)]
    require(len(shifts)==16 and all(r['mnemonic']=='lsr.w' and r['op_str']=='(a0)+' and r['raw']=='e2d8' for r in shifts),
            'Literal16 sequential LSR.W instructions changed')
    movem=[indexed[at] for at in range(0x4aba2,0x4abbe,4)]
    require(len(movem)==7 and all(r['mnemonic']=='movem.l' and r['op_str']=='d0-d7, -(a4)' for r in movem[:6])
        and movem[6]['mnemonic']=='movem.l' and movem[6]['op_str']=='d0-d3, -(a4)',
        'Literal6x8+1x4 LONG MOVEM sequence changed')
    audit=resource_fixtures(root,program)
    for item in provenance:require(sha((root/item['file']).read_bytes())==item['sha256'],'Source tool changed during inventory')
    fresh,fresh_source=load_verified_program(root)
    require(fresh==program and fresh_source==source,'Original source changed during inventory')
    return dict(schema_version=1,source=source,program_code_modified=False,
        decoder='Capstone '+capstone.__version__,confirmed_contract=CONTRACT,
        mapping='Assigned fixed first1MiB instructions CPU=ROM; selected banked fixtures retain distinct CPU/ROM offsets.',
        window_count=len(windows),row_count=sum(w['row_count'] for w in windows),
        instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),gap_count=0,
        windows=windows,direct_control_operand_count=len(controls),indirect_control_operand_count=len(indirect),
        indirect_control_operands=indirect,
        direct_target_counts=[dict(cpu_address=at,rom_offset=at,count=n)
            for at,n in sorted(collections.Counter(c['literal_target_cpu_address'] for c in controls).items())],
        literal_call_MMIO_slot_index_evidence=evidence,
        literal_LSR_sequence=dict(instruction_count=16,instructions=shifts),
        literal_MOVEM_sequence=dict(instruction_count=7,six_register_lists='D0-D7',last_register_list='D0-D3',
            encoded_LONG_transfer_count=6*8+4,encoded_transfer_bytes=(6*8+4)*4,instructions=movem),
        literal_debug_slot_address_operands=dict(first_cpu_address=0x10daf8,end_cpu_address_exclusive=0x10db78,
            stride_bytes=8,address_span_stride_quotient=(0x10db78-0x10daf8)//8,
            scope='Arithmetic from literal start/end/increment operands; no observed execution count or natural slot ownership claim.'),
        resource_audit=audit,provenance=provenance,
        scope='Only three explicit exact bounded instruction windows, including bytes after first RTS. Direct targets and indirectJSR(A0) are separate. '
              'Literal16 LSR.W and7 MOVEM instructions, MMIO operands and slot/index/register operations are retained without new behavior inference. '
              'Existing fixed/bank2/bank3 raw8 read fixtures are source/container-verified and not decoded as code or interpreted as logical bounds records. '
              'No runtime/callee/pending/callback closure, bank switching, natural gameplay use or execution equivalence claim.')


def main():
    root=Path(__file__).resolve().parents[1];report=inventory(root)
    path=root/'artifacts/stage_buffer_frame_inventory.json';listing=root/'artifacts/stage_buffer_frame_inventory.asm'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    lines=['; Original SHA256 '+SOURCE_SHA256,'; Assigned bounded source instructions only; resource raw8 fixtures are DATA, not decoded.']
    for window in report['windows']:
        lines.append('; [%06x,%06x) SHA256 %s; first RTS does not truncate.' % (window['start_cpu_address'],window['end_cpu_address_exclusive'],window['raw_sha256']))
        lines.append(asm(window['instructions']))
    for fixture in report['resource_audit']['resource_read_fixtures']:
        lines.append('; Raw8 %s CPU%06x ROM%06x %s from%s; no gameplay/table claim.' % (
            fixture['role'],fixture['source_cpu_address'],fixture['source_rom_offset'],fixture['raw_hex'],fixture['file']))
    listing.write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(windows=report['window_count'],instructions=report['instruction_row_count'],undecoded=report['undecoded_row_count'],gaps=0,
        direct_controls=report['direct_control_operand_count'],indirect_controls=report['indirect_control_operand_count'],
        LSR_instructions=16,MOVEM_instructions=7,resource_fixtures=3,
        report_sha256=sha(path.read_bytes()),asm_sha256=sha(listing.read_bytes()))))


if __name__=='__main__':main()
