"""Inventory raw3c WORD selector slots; target equality is not callback support."""
import collections
import json
from pathlib import Path
import tempfile

try:
    from .disassemble_program import load_verified_program, disassemble_range
    from . import pack_animation_control as control
except ImportError:
    from disassemble_program import load_verified_program, disassemble_range
    import pack_animation_control as control

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
DISPATCH_START, DISPATCH_END = 0x42500, 0x52500
FIELD_START, FIELD_END = 0x4276c, 0x5276c
DISPATCH_SHA256 = '275e74e5e3e14cd1d5ff48e672fa89d36afc2d0dc5d0aa536874dae0bc4ca7c6'
FIELD_SHA256 = '00fd4b3f850678709eb4da84d61addd145491b9a6f0afc5637b8bd273ad32bd4'
PREFIX_SHA256 = 'd418ddaba698d044f4b0d570a5da75db9869ea074d357650105520295e4477e6'
KNOWN_TARGETS = {0x2b3e8:'existing14-selector1d',0x2b3fa:'existing14-selector1e',
                 0x47672:'existing14-selector1f',0x3679e:'original-RTS-bytes'}
RTS_ADDRESS, RTS_RAW = 0x3679e, '4e75'
EVIDENCE = {0x4a312:'3019',0x4a314:'d040',0x4a316:'d040',
    0x4a318:'41f90004a500',0x4a31e:'2e300000',0x4a322:'3019',
    0x4a324:'d040',0x4a326:'41f90004a76c',0x4a32c:'32300000'}


def signed_word(value):
    return value-65536 if value&0x8000 else value


def encode(value):
    return (json.dumps(value,indent=2)+'\n').encode()


def build(root):
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256 == control.sha(program)
    assert len(program) == source['size'] == 8388608 and source['byte_order'] == 'big'
    for address, raw in EVIDENCE.items():
        assert program[address:address+len(raw)//2] == bytes.fromhex(raw)
    assert program[RTS_ADDRESS:RTS_ADDRESS+2] == bytes.fromhex(RTS_RAW)
    assert program[0x4a50c:0x4a510] == bytes.fromhex('0003679e')
    assert control.sha(program[DISPATCH_START:DISPATCH_END]) == DISPATCH_SHA256
    assert control.sha(program[FIELD_START:FIELD_END]) == FIELD_SHA256
    assert control.sha(program[DISPATCH_START:FIELD_START]) == PREFIX_SHA256
    inputs = {name:control.sha((root/name).read_bytes()) for name in (
        'tools/inventory_animation_word_callbacks.py','tools/disassemble_program.py',
        'tools/pack_animation_control.py')}
    dispatch_aliases = collections.defaultdict(list)
    field_aliases = collections.defaultdict(list)
    for selector in range(65536):
        # Two separate ADD.W operations; check against the contract formula.
        once = (selector+selector)&65535
        twice = (once+once)&65535
        assert twice == (selector*4)&65535
        callback_address = 0x4a500+signed_word(twice)
        field_address = 0x4a76c+signed_word(once)
        assert DISPATCH_START <= callback_address and callback_address+4 <= DISPATCH_END
        assert FIELD_START <= field_address and field_address+2 <= FIELD_END
        dispatch_aliases[callback_address].append(selector)
        field_aliases[field_address].append(selector)
    assert sorted(dispatch_aliases) == list(range(DISPATCH_START,DISPATCH_END,4))
    assert sorted(field_aliases) == list(range(FIELD_START,FIELD_END,2))
    assert len(dispatch_aliases) == 16384 and len(field_aliases) == 32768
    assert sorted(s for group in dispatch_aliases.values() for s in group) == list(range(65536))
    assert sorted(s for group in field_aliases.values() for s in group) == list(range(65536))
    callback_rows, field_rows, known = [], [], []
    targets = collections.Counter()
    for address, aliases in sorted(dispatch_aliases.items()):
        assert len(aliases) == 4 and aliases == [aliases[0]+i*0x4000 for i in range(4)]
        raw = program[address:address+4]
        target = int.from_bytes(raw,'big')
        targets[target] += 1
        row = dict(slot_id='animation3c-dispatch:%05x'%address,
            source_cpu_address=address,source_rom_offset=address,size=4,
            raw=raw.hex(),raw_target=target,selector_aliases=aliases,
            known_target_equality=KNOWN_TARGETS.get(target),
            resource_part='proposed-prefix' if address<FIELD_START else 'existing-control-window')
        callback_rows.append(row)
        if target in KNOWN_TARGETS:
            known.append(dict(row,scope='Raw equality to a separately identified target; no3c support or natural selector use claim'))
    for address, aliases in sorted(field_aliases.items()):
        assert len(aliases) == 2 and aliases[1] == aliases[0]+0x8000
        raw = program[address:address+2]
        field_rows.append(dict(slot_id='animation3c-field-selector:%05x'%address,
            source_cpu_address=address,source_rom_offset=address,size=2,
            raw=raw.hex(),raw_word=int.from_bytes(raw,'big'),selector_aliases=aliases))
    # The split lies on both LONG and WORD slot boundaries. No actual read
    # needs to be assembled from two adjacent resource windows.
    assert FIELD_START%4 == 0 and DISPATCH_START%4 == 0
    assert all(address+4<=FIELD_START or address>=FIELD_START for address in dispatch_aliases)
    prefix_size = FIELD_START-DISPATCH_START
    prefix_slots = prefix_size//4
    assert prefix_size == 620 and prefix_slots == 155
    assert sum(row['resource_part']=='proposed-prefix' for row in callback_rows) == prefix_slots
    spec = next(spec for spec in control.SPECS if spec['cpu'] == FIELD_START)
    assert spec['end'] == FIELD_END and spec['payload_sha256'] == FIELD_SHA256
    runtime_path = root/'extracted/runtime/animation_control'/spec['file']
    if runtime_path.exists():
        packed = runtime_path.read_bytes()
        assert control.validate_container(packed) == program[FIELD_START:FIELD_END]
        inputs[str(runtime_path.relative_to(root))] = control.sha(packed)
    decoded = disassemble_range(program,0x4a30c,0x76,0x4a30c)
    source_info = dict(source=source,mapping='Fixed CPU address equals canonical BE ROM file offset',
        handler=dict(source_cpu_address=0x4a30c,source_rom_offset=0x4a30c,
                     end_exclusive=0x4a382,instructions=decoded),
        evidence=[dict(cpu_address=address,rom_offset=address,raw=raw) for address,raw in sorted(EVIDENCE.items())],
        target_byte_evidence=[dict(source_cpu_address=RTS_ADDRESS,source_rom_offset=RTS_ADDRESS,
            size=2,raw=RTS_RAW,instruction='RTS',sha256=control.sha(bytes.fromhex(RTS_RAW)),
            anchor_slot=dict(source_cpu_address=0x4a50c,source_rom_offset=0x4a50c,raw='0003679e'),
            scope='Original two-byte RTS encoding verified separately from raw table target equality; no execution, callback support, or natural reachability claim')],
        raw_windows=[dict(role=role,source_cpu_address=start,source_rom_offset=start,
            end_exclusive=end,size=end-start,sha256=digest) for role,start,end,digest in (
                ('WORD-callback-selector-LONG-reads',DISPATCH_START,DISPATCH_END,DISPATCH_SHA256),
                ('second-WORD-selector-WORD-reads',FIELD_START,FIELD_END,FIELD_SHA256),
                ('missing-prefix-candidate',DISPATCH_START,FIELD_START,PREFIX_SHA256))],
        caveat='Decoded handler is address/raw evidence only. Table bytes include unrelated data/code; targets are not certified functions or supported callbacks.')
    summary = dict(source=source,inputs=inputs,
        selector_domains=dict(callback_word_inputs=65536,callback_unique_slots=16384,
            callback_aliases_per_slot=4,field_word_inputs=65536,field_unique_slots=32768,field_aliases_per_slot=2,
            callback_formula='4a500 + sign16((s*4)&ffff)',field_formula='4a76c + sign16((s*2)&ffff)',
            callback_alias_rule='s,s+4000,s+8000,s+c000 modulo65536',field_alias_rule='s,s+8000 modulo65536'),
        callback_raw_target_counts=dict(distinct_values=len(targets),zero_slots=targets[0],
            odd_raw_values=sum(count for value,count in targets.items() if value&1),
            scope='Raw value statistics only; even/24bit/code-range values are not validated callbacks'),
        known_target_matches=known,
        known_target_slot_counts={('%06x'%target):targets[target] for target in sorted(KNOWN_TARGETS)},
        resource_extension_candidate=dict(existing_file='animation_control/'+spec['file'],
            existing_start=FIELD_START,existing_end_exclusive=FIELD_END,
            missing_start=DISPATCH_START,missing_end_exclusive=FIELD_START,missing_payload_bytes=prefix_size,
            missing_LONG_slots=prefix_slots,missing_payload_sha256=PREFIX_SHA256,
            hypothetical_MS5D_header_bytes=32,hypothetical_container_bytes=32+prefix_size,
            existing_callback_LONG_slots=len(callback_rows)-prefix_slots,union_start=DISPATCH_START,union_end_exclusive=FIELD_END,
            union_payload_bytes=FIELD_END-DISPATCH_START,overlap_bytes=0,split_crossing_reads=0,
            proposed_only=True,scope='Nonoverlapping620-byte prefix plus existing control window can satisfy both raw read domains. No packer/container/C++ consumption implemented here.'),
        validations=dict(all_65536_selectors_classified=True,all_alias_groups_complete=True,
            pinned_raw_window_hashes=True,existing_runtime_container_checked=runtime_path.exists()),
        scope='Static original3c raw selector inventory; no ROM mutation, execution, callback support, natural reachability, or logical table extent claim.')
    files = {'source.json':encode(source_info),'callback_slots.json':encode(callback_rows),
             'field_slots.json':encode(field_rows)}
    summary['files'] = {name:dict(size=len(data),sha256=control.sha(data)) for name,data in files.items()}
    fresh, fresh_source = load_verified_program(root)
    assert fresh == program and fresh_source == source
    assert all(control.sha((root/name).read_bytes()) == digest for name,digest in inputs.items())
    files['inventory.json'] = encode(summary)
    return files, summary


def main():
    root = Path(__file__).resolve().parents[1]
    files, summary = build(root)
    folder = root/'artifacts/animation_word_callbacks'
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent) as staging:
        staging = Path(staging)
        for name,data in files.items():
            (staging/name).write_bytes(data)
            assert (staging/name).read_bytes() == data
        for name in files:
            (staging/name).replace(folder/name)
    assert all((folder/name).read_bytes() == data for name,data in files.items())
    print(json.dumps(dict(domains=summary['selector_domains'],known_target_matches=summary['known_target_matches'],
        missing_payload_bytes=summary['resource_extension_candidate']['missing_payload_bytes'],
        files={name:dict(size=len(data),sha256=control.sha(data)) for name,data in files.items()})))


if __name__ == '__main__':
    main()
