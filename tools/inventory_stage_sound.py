"""Bounded stage sound instruction and catalog field inventory; not native execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import capstone
from disassemble_program import disassemble_range, load_verified_program
from inventory_game_initialization import asm
from inventory_object_removal import controls, fields, target
from pack_stage_catalog import decode_group, INDEX, COUNT

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS = ((0x47a1c, 0x47a94), (0x3af8, 0x3c08), (0x3c84, 0x3c8a), (0x3d44, 0x3d54))


def local_successors(rows):
    """Encoded caller edges only; direct calls treated as eventual fallthrough."""
    edges = {}
    for row in rows:
        pc = row['cpu_address']; following = pc + row['size']
        mnemonic = row['mnemonic'].split('.')[0]; destination = target(row)
        if row['classification'] != 'candidate_instruction':
            raise ValueError('Caller window contains undecoded words')
        if mnemonic in ('rts', 'rte', 'jmp'):
            successors = [destination] if destination is not None else []
        elif mnemonic == 'bra':
            successors = [destination]
        elif mnemonic.startswith('b') and mnemonic not in ('bsr', 'btst', 'bclr', 'bset', 'bchg'):
            successors = [following, destination]
        else:
            successors = [following]
        edges[pc] = [value for value in successors if value is not None]
    visited = set(); pending = [0x47a1c]
    while pending:
        pc = pending.pop()
        if pc in visited or pc not in edges: continue
        visited.add(pc); pending.extend(edges[pc])
    return dict(edges=[dict(cpu_address=pc, successors=successors) for pc, successors in edges.items()],
                reachable_instruction_candidates=sorted(visited),
                unreachable_instruction_candidates=sorted(set(edges)-visited),
                classification='Intraprocedural encoded branch graph; calls assumed to return to following instruction. No indirect callee transfer/reentry analysis or execution.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/stage_sound')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program')
    windows = []
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        assert sum(row['size'] for row in rows) == end-start
        assert all(row['rom_offset'] + row['size'] <= end for row in rows)
        windows.append(dict(start_cpu_address=start, start_rom_offset=start, end_exclusive=end,
            raw_sha256=hashlib.sha256(program[start:end]).hexdigest(), instructions=rows,
            control_target_candidates=controls(rows), encoded_memory_operands=fields(rows),
            undecoded_words=[row for row in rows if row['classification'] != 'candidate_instruction']))
    records = []; groups = []
    for number, address in enumerate(struct.unpack_from('>19I', program, INDEX)):
        group = decode_group(program, address); counts = Counter()
        for area, record in enumerate(group['records']):
            cpu = record['source_cpu_address']; raw = program[cpu:cpu+record['size']]
            value = struct.unpack_from('>H', raw, 0x10)[0]; counts[value] += 1
            records.append(dict(group=number, area=area, record_cpu_address=cpu, record_rom_offset=cpu,
                record_length=record['size'], record_raw_sha256=hashlib.sha256(raw).hexdigest(),
                field_offset=0x10, field_cpu_address=cpu+0x10, field_raw=raw[0x10:0x12].hex(), word10=value))
        groups.append(dict(group=number, source_cpu_address=address, source_rom_offset=address,
            record_count=len(group['records']), word10_counts=[dict(value=value,count=count) for value,count in sorted(counts.items())]))
    assert COUNT == 19 and len(records) == 59
    cfg = local_successors(windows[0]['instructions'])
    assert 0x47a54 in cfg['unreachable_instruction_candidates']
    counts = Counter(row['word10'] for row in records)
    report = dict(source=source, decoder='Capstone '+capstone.__version__, program_code_modified=False,
        mapping='CPU addresses in fixed first1MiB equal canonical ROM offsets; RAM/MMIO distinct.',
        windows=windows, caller_encoded_cfg=cfg, records=records, groups=groups, record_count=len(records),
        unique_word10_count=len(counts), word10_counts=[dict(value=value,count=count) for value,count in sorted(counts.items())],
        resource='Existing MS5D stage catalog; no new binary resource or logical table extension.',
        limitations='Full assigned windows preserved, not firstRTS routine completion. Instruction candidates and raw catalog fields are not execution evidence. '
            '47a54 block has no encoded intraprocedural predecessor reachable from47a1c, assuming calls return normally; arbitrary external entry not excluded. '
            'General sound primitive register/continuation contracts and natural scheduling require independent implementation/native verification.')
    output = Path(args.output); output = output if output.is_absolute() else root/output
    output.mkdir(parents=True, exist_ok=True)
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    listing=[]
    for window in windows:
        listing.append('; Explicit bounded %06x..%06x; candidate instructions, not whole routine claim.' % (window['start_cpu_address'], window['end_exclusive']))
        listing.append(asm(window['instructions']))
    (output/'inventory.asm').write_text('\n'.join(listing)+'\n')
    table=['# Stage record word10 raw field distribution', '', '| Group (decimal) | Records | word10 (hex): count |', '| --- | ---: | --- |']
    for group in groups:
        table.append('| %d | %d | %s |' % (group['group'], group['record_count'], ', '.join('%04x: %d' % (item['value'],item['count']) for item in group['word10_counts']) or 'empty'))
    table += ['', 'Raw field counts only; no music identity or natural reachability claim.']
    (output/'distribution.md').write_text('\n'.join(table)+'\n')
    print(json.dumps(dict(records=len(records), groups=len(groups), word10_counts=report['word10_counts'],
        rows=sum(len(window['instructions']) for window in windows), unreachable=cfg['unreachable_instruction_candidates'],
        hashes={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ('report.json','inventory.asm','distribution.md')})))


if __name__ == '__main__':
    main()
