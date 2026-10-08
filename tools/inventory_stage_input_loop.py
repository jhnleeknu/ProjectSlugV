"""Bounded original stage-input-loop/caller candidates and immutable resource audit."""
import collections
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_object_removal import CONTROL, target
from inventory_stage_input_callbacks import bounded, require, sha
import pack_game_records as records
import pack_player_record_lookup as lookup
import pack_stage_input as masks

WINDOWS = ((0x49b0c,0x49bca),(0x47642,0x47672),(0x289e,0x28ae),
           (0x1da60,0x1daba),(0x4d7a6,0x4d81c))
LITERALS = (
    (0x49b10,'movea.l','$5734(a5), a1'),
    (0x49b2c,'jsr','(a1)'),
    (0x49b2e,'lea.l','$5726(a5), a1'),
    (0x49b5a,'lea.l','$5726(a5), a1'),
    (0x49b66,'movea.l','$5738(a5), a1'),
    (0x49b82,'jsr','(a1)'),
    (0x49b84,'lea.l','$572c(a5), a1'),
    (0x49bb0,'lea.l','$572c(a5), a1'),
    (0x49bb4,'move.w','$4(a1), d0'),
    (0x49bb8,'move.w','#$ffff, $4(a1)'),
    (0x49bc2,'move.w','d7, $2(a1)'),
    (0x49bc6,'move.w','d6, (a1)'),
    (0x1da98,'move.w','$78(a0), d0'),
    (0x1da9c,'jsr','$4d7a6.l'),
    (0x1daa8,'move.w','$78(a0), d0'),
    (0x1daac,'jsr','$49c32.l'),
    (0x1dab2,'jsr','$49f66.l'),
    (0x4d7f0,'trap','#$f'),
    (0x4d810,'lea.l','$4cf64(pc), a4'),
    (0x4d816,'move.w','$a(a4), d4'))


def resource_audit(root,program,source):
    lookup.verify_program(program)
    body = lookup.extract(program)
    packed = (root/'extracted/runtime/player_record_lookup.ms5d').read_bytes()
    require(lookup.validate_container(packed) == body and packed == lookup.pack_payload(body),
            'Player lookup container differs from canonical source/header/CRC')
    prefix = records.extract(program)
    prefix_packed = (root/'extracted/runtime/game_records.ms5d').read_bytes()
    require(prefix_packed == records.pack_payload(prefix) and body[:lookup.PREFIX_SIZE] == prefix,
            'Lookup first320 bytes or existing game-records container changed')
    lp = root/'extracted/runtime/player_record_lookup.manifest.json'
    manifest = json.loads(lp.read_text())
    expected = dict(schema_version=1,id='player-record-lookup:0004cf64',format='MS5D',version=1,kind=1,
        file='player_record_lookup.ms5d',source=source,source_cpu_address=lookup.BASE,
        source_rom_offset=lookup.BASE,end_cpu_address_exclusive=lookup.END,
        payload_size=len(body),size=len(packed),payload_sha256=sha(body),sha256=sha(packed),
        lookup_expression='BE16 at4cf64 + unsignedbyteindex*16 +0a',
        native_active_index_range=[1,255],
        native_index_zero='TRAP path outside normal lookup; rawindex0 bytes stillpreserved',
        last_read=dict(index=255,cpu_address=lookup.END-2,rom_offset=lookup.END-2,end_exclusive=lookup.END),
        existing_twenty_record_prefix=dict(file='game_records.ms5d',size=lookup.PREFIX_SIZE,
            sha256=lookup.RECORD_PREFIX_SHA256,cpu_address=lookup.BASE,
            end_exclusive=lookup.BASE+lookup.PREFIX_SIZE,actual_resource_prefix_equal=True),
        instruction_evidence=disassemble_range(program,lookup.EVIDENCE_ADDRESS,len(lookup.EVIDENCE),lookup.EVIDENCE_ADDRESS))
    require(all(manifest.get(k) == v for k,v in expected.items()), 'Player lookup manifest/source/prefix/evidence mismatch')
    gp = root/'extracted/runtime/game_records.manifest.json'
    gm = json.loads(gp.read_text())
    ge = dict(schema_version=1,id='game-records:0004cf64',format='MS5D',version=1,kind=1,
        file='game_records.ms5d',source=source,source_cpu_address=records.BASE,
        source_rom_offset=records.BASE,end_cpu_address_exclusive=records.END,
        record_count=records.RECORD_COUNT,record_size=records.RECORD_SIZE,payload_size=len(prefix),
        size=len(prefix_packed),payload_sha256=sha(prefix),sha256=sha(prefix_packed),
        records=records.validate_payload(prefix))
    require(all(gm.get(k) == v for k,v in ge.items()), 'Game-records prefix manifest/source mismatch')
    files,mask_manifest = masks.build(root)
    for name,data in files.items():
        require((root/'extracted/runtime/stage_input'/name).read_bytes() == data,
                'Existing default-mask resource/manifest differs from current packer/source')
    references = [dict(index=i,cpu_address=at,rom_offset=at,raw_be16=value)
                  for i in range(256) for at,value in [lookup.lookup_word(body,i)]]
    paths = ('extracted/runtime/player_record_lookup.ms5d',
        'extracted/runtime/player_record_lookup.manifest.json',
        'extracted/runtime/game_records.ms5d','extracted/runtime/game_records.manifest.json',
        'extracted/runtime/stage_input/default_masks.ms5d','extracted/runtime/stage_input/manifest.json')
    return dict(resource_count=3,manifest_count=3,
        files=[dict(file=p,sha256=sha((root/p).read_bytes())) for p in paths],
        lookup=dict(source_cpu_address=lookup.BASE,source_rom_offset=lookup.BASE,
            end_cpu_address_exclusive=lookup.END,payload_size=len(body),payload_sha256=sha(body),
            container_sha256=sha(packed),prefix_size=len(prefix),prefix_sha256=sha(prefix),
            prefix_equals_existing_game_records=True,all256_raw_lookup_words=references,
            manifest=manifest),
        prefix_manifest=gm,default_masks_manifest=mask_manifest,
        regenerated_resource_files=False,
        scope='Read-only comparison against pinned original bytes, existing extraction validators/container builders, and source/CRC/bounds/hash/prefix metadata. '
              'All256 byte-indexed raw WORDs are preserved as data evidence; index0 runtime/TRAP behavior and natural index reachability are separate. '
              '4092-byte lookup is a raw addressable window, not a claim of enlarged logical record-table extent.')


def inventory(root):
    program,source = load_verified_program(root)
    require(source['sha256'] == masks.SOURCE_SHA256 and sha(program) == masks.SOURCE_SHA256,
            'Unsupported pinned original source')
    paths = ('tools/pack_game_records.py','tools/pack_player_record_lookup.py',
        'tools/pack_stage_input.py','tools/inventory_stage_input_callbacks.py',
        'tools/disassemble_program.py','tools/inventory_stage_input_loop.py')
    provenance = [dict(file=p,sha256=sha((root/p).read_bytes())) for p in paths]
    windows = [bounded(program,start,end) for start,end in WINDOWS]
    indexed = {r['cpu_address']:r for w in windows for r in w['instructions']}
    controls,indirect = [],[]
    for window in windows:
        direct = []
        for row in window['instructions']:
            if row['classification'] != 'candidate_instruction' or row['mnemonic'].split('.')[0] not in CONTROL:
                continue
            destination = target(row)
            item = dict(instruction=row,literal_target_cpu_address=destination,
                        literal_target_rom_offset=destination if destination is not None and destination < 0x100000 else None)
            if destination is None:
                indirect.append(item)
            else:
                direct.append(item);controls.append(item)
        window['direct_control_operands'] = direct
    require([(r['instruction']['cpu_address'],r['instruction']['mnemonic'],r['instruction']['op_str']) for r in indirect]
        == [(0x49b2c,'jsr','(a1)'),(0x49b82,'jsr','(a1)')], 'Indirect call evidence mismatch')
    literals = []
    for at,mnemonic,operand in LITERALS:
        row = indexed[at]
        require(row['mnemonic'] == mnemonic and row['op_str'] == operand,'Literal instruction changed')
        literals.append(row)
    audit = resource_audit(root,program,source)
    for item in audit['files']+provenance:
        require(sha((root/item['file']).read_bytes()) == item['sha256'], 'Input changed during audit')
    fresh,fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source,'Original source changed')
    return dict(schema_version=1,source=source,program_code_modified=False,
        decoder='Capstone '+capstone.__version__,mapping='Fixed first1MiB CPU addresses equal ROM offsets; relative A5/A1 operands retained without invented field ownership.',
        window_count=len(windows),row_count=sum(w['row_count'] for w in windows),
        instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),gap_count=0,
        windows=windows,direct_control_operand_count=len(controls),indirect_call_operand_count=len(indirect),
        indirect_call_operands=indirect,
        direct_target_counts=[dict(cpu_address=at,rom_offset=at,count=n)
            for at,n in sorted(collections.Counter(c['literal_target_cpu_address'] for c in controls).items())],
        literal_slot_and_helper_operand_evidence=literals,resource_audit=audit,provenance=provenance,
        scope='Exact assigned bounded instruction candidates and immutable resource evidence, including bytes after first RTS. '
              'JSR(A1) has no static direct target and is separated from literal direct control targets. '
              'No runtime execution, whole unknown callback closure, callee semantics, scheduling or natural reachability proof.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/stage_input_loop_inventory.json'
    listing = root/'artifacts/stage_input_loop_inventory.asm'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    lines = ['; Original SHA256 '+masks.SOURCE_SHA256,
             '; Fixed CPU=ROM bounded instruction/resource evidence; not full callback closure.']
    for window in report['windows']:
        lines.append('; [%06x,%06x) SHA256 %s; first RTS does not truncate.' % (
            window['start_cpu_address'],window['end_cpu_address_exclusive'],window['raw_sha256']))
        lines.append(asm(window['instructions']))
    listing.write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(windows=report['window_count'],rows=report['row_count'],
        instructions=report['instruction_row_count'],undecoded=report['undecoded_row_count'],gaps=0,
        direct_controls=report['direct_control_operand_count'],indirect_calls=report['indirect_call_operand_count'],
        resources=report['resource_audit']['resource_count'],report_sha256=sha(path.read_bytes()),asm_sha256=sha(listing.read_bytes()))))


if __name__ == '__main__':
    main()
