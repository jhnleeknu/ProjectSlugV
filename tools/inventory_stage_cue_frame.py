"""Pinned bounded cue-frame instruction/data and catalog pointer evidence only."""
import collections
import json
from pathlib import Path
import struct

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import CONTROL, target
from inventory_scene_general_initialization import context_inventory, SOURCE_SHA256
from inventory_stage_input_callbacks import bounded, require, sha

WINDOWS = ((0xe89fa,0xe8a0c),(0xe8a1c,0xe8a3a),(0xe8a48,0xe8b5a),
           (0x2986,0x299c),(0xcd50,0xce02))
DATA = ((0xe89e4,0xe89ec,'default cue DATA','0000000003000000'),
        (0xe89ec,0xe89fa,'default stream DATA','00000000006001000308000bffff'),
        (0xe8a0c,0xe8a1c,'literal DATA','00000002000000010001000100020001'))
LITERALS = (
    (0xe8a06,'move.l','a0, $5e2a(a5)'),
    (0xe8a28,'move.l','a0, $5e26(a5)'),
    (0xe8a2c,'move.b','#$ff, $5e2e(a5)'),
    (0xe8a32,'move.b','#$0, $5e2f(a5)'),
    (0xe8a84,'jsr','$2986.l'),
    (0xe8a96,'jsr','$43e08.l'),
    (0xe8aa2,'lea.l','$e8a0c(pc), a1'),
    (0xe8aaa,'move.w','(a1)+, (a0)+'),
    (0xe8aac,'move.w','(a1)+, (a0)+'),
    (0xe8ad0,'movea.l','$5e2a(a5), a0'),
    (0xe8ae0,'cmp.w','$c(a0), d0'),
    (0xe8ae8,'adda.w','#$c, a0'),
    (0xe8b52,'jsr','$cd58.l'),
    (0x2986,'move.l','a6, -(a7)'),
    (0x2988,'movea.l','a1, a6'),
    (0x298e,'movea.l','(a7)+, a6'),
    (0x2990,'move.w','sr, -(a7)'),
    (0x2992,'move.b','$6a(a6), $6a(a0)'),
    (0x2998,'move.w','(a7)+, sr'),
    (0xcd52,'move.l','a0, $1152(a5)'),
    (0xcd58,'movea.l','$1152(a5), a0'),
    (0xcd5c,'jsr','(a0)'))


def cd52_references(program):
    result = []
    end = 0x100000
    for at in range(0,end-1,2):
        word = int.from_bytes(program[at:at+2],'big')
        destination,size,form = None,None,None
        if word in (0x4eb9,0x4ef9) and at+6 <= end:
            destination = int.from_bytes(program[at+2:at+6],'big')
            size,form = 6,'absolute-long JSR/JMP'
        elif word == 0x4eba and at+4 <= end:
            destination = at+2+int.from_bytes(program[at+2:at+4],'big',signed=True)
            size,form = 4,'PC-relative signed-WORD JSR'
        elif word>>8 in (0x60,0x61):
            delta = word&255
            if delta == 0:
                if at+4 > end:continue
                delta = int.from_bytes(program[at+2:at+4],'big',signed=True)
                size,form = 4,'signed-WORD BRA/BSR'
            else:
                delta = delta if delta < 128 else delta-256
                size,form = 2,'signed-BYTE BRA/BSR M68000'
            destination = at+2+delta
        if destination != 0xcd52:continue
        row = disassemble_range(program,at,min(16,end-at),at)[0]
        valid = (row['classification']=='candidate_instruction' and row['size']==size and target(row)==destination)
        context = bounded(program,max(0,at-16),min(end,at+size+24))
        result.append(dict(cpu_address=at,rom_offset=at,raw_hex=program[at:at+size].hex(),
            encoding_form=form,target_cpu_address=destination,target_rom_offset=destination,
            instruction=row,padded_decoder_matches_encoding=valid,context=context,
            scope='Even-offset raw encoding candidate decoded in isolation; not a verified instruction boundary or natural callsite. '
                  'Before16/after24 context starts at an arbitrary even offset and may contain data or extension words.'))
    return result


def catalog_inventory(root,program,source):
    catalog = context_inventory(root,program,source)
    rows = []
    roots = collections.defaultdict(list)
    for record in catalog['records']:
        at = record['record_cpu_address']
        require(record['record_length'] >= 10,'Catalog record lacks complete LONG+6')
        raw = bytes(program[at+6:at+10])
        pointer = struct.unpack('>I',raw)[0]
        row = dict(group=record['group'],area=record['area'],record_cpu_address=at,
            record_rom_offset=at,record_length=record['record_length'],
            record_raw_sha256=record['record_raw_sha256'],cue_pointer_field_offset=6,
            cue_pointer_field_cpu_address=at+6,cue_pointer_field_rom_offset=at+6,
            cue_pointer_raw_hex=raw.hex(),cue_pointer_long=pointer,null_pointer=pointer==0)
        if pointer:
            require(pointer%2==0 and pointer+8 <= 0x100000,'Cue prefix outside fixed source span')
            prefix = bytes(program[pointer:pointer+8])
            require(len(prefix)==8,'Truncated cue prefix')
            row['root_prefix'] = dict(cpu_address=pointer,rom_offset=pointer,
                end_cpu_address_exclusive=pointer+8,end_rom_offset_exclusive=pointer+8,
                byte_count=8,raw_hex=prefix.hex(),raw_sha256=sha(prefix))
            roots[pointer].append(dict(group=record['group'],area=record['area'],record_cpu_address=at))
        else:row['root_prefix']=None
        rows.append(row)
    return dict(stage_catalog_manifest_sha256=catalog['stage_catalog_manifest_sha256'],
        stage_index_cpu_address=catalog['stage_index_cpu_address'],
        stage_index_rom_offset=catalog['stage_index_rom_offset'],
        stage_index_raw_sha256=catalog['stage_index_raw_sha256'],
        group_count=len(catalog['groups']),record_count=len(rows),
        null_pointer_records=sum(r['null_pointer'] for r in rows),
        nonnull_pointer_records=sum(not r['null_pointer'] for r in rows),
        distinct_nonnull_roots=len(roots),records=rows,
        roots=[dict(cpu_address=at,rom_offset=at,byte_count=8,
            end_cpu_address_exclusive=at+8,end_rom_offset_exclusive=at+8,
            raw_hex=program[at:at+8].hex(),raw_sha256=sha(program[at:at+8]),
            references=refs) for at,refs in sorted(roots.items())],
        scope='All existing source-verified catalog records, main-confirmed following field LONG+6. '
              'Only the first8 bytes of each nonnull root are retained; this is an evidence bound, not a logical resource length, grammar, ownership or runtime use claim.')


def inventory(root):
    program,source = load_verified_program(root)
    require(source['sha256']==SOURCE_SHA256 and sha(program)==SOURCE_SHA256,'Unsupported pinned original source')
    paths = ('tools/inventory_stage_cue_frame.py','tools/disassemble_program.py',
        'tools/inventory_scene_general_initialization.py','tools/pack_stage_catalog.py',
        'tools/inventory_stage_input_callbacks.py')
    provenance = [dict(file=p,sha256=sha((root/p).read_bytes())) for p in paths]
    windows = [bounded(program,start,end) for start,end in WINDOWS]
    indexed = {r['cpu_address']:r for w in windows for r in w['instructions']}
    controls,indirect = [],[]
    for window in windows:
        local = []
        for row in window['instructions']:
            if row['classification']!='candidate_instruction' or row['mnemonic'].split('.')[0] not in CONTROL:continue
            destination = target(row)
            item = dict(instruction=row,literal_target_cpu_address=destination,
                literal_target_rom_offset=destination if destination is not None and destination < 0x100000 else None)
            if destination is None:indirect.append(item)
            else:controls.append(item);local.append(item)
        window['direct_control_operands']=local
    literals=[]
    for at,mnemonic,operand in LITERALS:
        row=indexed[at]
        require(row['mnemonic']==mnemonic and row['op_str']==operand,'Literal instruction evidence changed')
        literals.append(row)
    data=[]
    for start,end,role,rawhex in DATA:
        raw=bytes(program[start:end])
        require(raw.hex()==rawhex,'Explicit source DATA bytes changed')
        require(not any(a<end and start<b for a,b in WINDOWS),'Assigned DATA/code windows overlap')
        data.append(dict(start_cpu_address=start,start_rom_offset=start,
            end_cpu_address_exclusive=end,end_rom_offset_exclusive=end,role=role,
            classification='Main-confirmed DATA, not decoded as code',byte_count=len(raw),
            raw_hex=raw.hex(),raw_sha256=sha(raw)))
    catalog=catalog_inventory(root,program,source)
    candidates=cd52_references(program)
    for item in provenance:require(sha((root/item['file']).read_bytes())==item['sha256'],'Input tool changed')
    fresh,fresh_source=load_verified_program(root)
    require(fresh==program and fresh_source==source,'Original source changed')
    return dict(schema_version=1,source=source,program_code_modified=False,
        decoder='Capstone '+capstone.__version__,mapping='Fixed first1MiB CPU addresses equal source ROM offsets; RAM operands remain separately encoded.',
        window_count=len(windows),row_count=sum(w['row_count'] for w in windows),
        instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),gap_count=0,
        windows=windows,data_regions=data,literal_instruction_evidence=literals,
        direct_control_operand_count=len(controls),indirect_control_operand_count=len(indirect),
        indirect_control_operands=indirect,
        direct_target_counts=[dict(cpu_address=at,rom_offset=at,count=n)
            for at,n in sorted(collections.Counter(c['literal_target_cpu_address'] for c in controls).items())],
        catalog_cue_pointer_inventory=catalog,
        cd52_encoding_scan=dict(start_rom_offset=0,end_rom_offset_exclusive=0x100000,stride_bytes=2,
            target_cpu_address=0xcd52,target_rom_offset=0xcd52,
            forms='Absolute-long JSR/JMP and PC-relative signed-WORD JSR, signed-BYTE/WORD BSR/BRA; M68000 ff byte displacement means -1.',
            candidate_count=len(candidates),decoder_match_count=sum(c['padded_decoder_matches_encoding'] for c in candidates),candidates=candidates),
        provenance=provenance,
        scope='Assigned exact bounded source instruction candidates and separate raw DATA, including code bytes after first RTS. '
              'Catalog source containers/manifests are verified by existing context_inventory; only LONG+6 and first8 root bytes are listed. '
              'cd52 raw matches/context do not establish actual instruction boundaries, A0 reaching definitions, callback targets, or reachability. '
              'No runtime/callee/pending behavior or resource-length inference, complete closure, engine implementation or execution-equivalence claim.')


def main():
    root=Path(__file__).resolve().parents[1]
    report=inventory(root)
    path=root/'artifacts/stage_cue_frame_inventory.json';listing=root/'artifacts/stage_cue_frame_inventory.asm'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    lines=['; Original SHA256 '+SOURCE_SHA256,'; Fixed CPU=ROM bounded instruction/data evidence only.']
    for region in report['data_regions']:
        lines.append('; DATA[%06x,%06x) %s; not decoded as code.' % (region['start_cpu_address'],region['end_cpu_address_exclusive'],region['raw_hex']))
    for window in report['windows']:
        lines.append('; [%06x,%06x) SHA256 %s; first RTS does not truncate.' % (window['start_cpu_address'],window['end_cpu_address_exclusive'],window['raw_sha256']))
        lines.append(asm(window['instructions']))
    for candidate in report['cd52_encoding_scan']['candidates']:
        lines.append('; Raw cd52 candidate%06x; arbitrary-even context, boundaries unconfirmed.' % candidate['cpu_address'])
        lines.append(asm(candidate['context']['instructions']))
    listing.write_text('\n'.join(lines)+'\n')
    catalog=report['catalog_cue_pointer_inventory'];scan=report['cd52_encoding_scan']
    print(json.dumps(dict(windows=report['window_count'],instructions=report['instruction_row_count'],
        undecoded=report['undecoded_row_count'],gaps=0,data_regions=len(report['data_regions']),
        direct_controls=report['direct_control_operand_count'],indirect_controls=report['indirect_control_operand_count'],
        catalog_records=catalog['record_count'],null_records=catalog['null_pointer_records'],
        nonnull_records=catalog['nonnull_pointer_records'],distinct_nonnull_roots=catalog['distinct_nonnull_roots'],
        cd52_raw_candidates=scan['candidate_count'],cd52_decoder_matches=scan['decoder_match_count'],
        report_sha256=sha(path.read_bytes()),asm_sha256=sha(listing.read_bytes()))))


if __name__=='__main__':main()
