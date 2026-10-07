"""Opcode08 raw descriptor stride/type inventory, not handler execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program
from pack_scene_scripts import command_span, SOURCE_SHA256
from pack_stage_catalog import decode_group, INDEX, COUNT


def descriptor_inventory(program, address):
    rows = []; visited = set(); cursor = address; phase = 'prefix'
    limit = min(len(program), 0x100000, address + 65536)
    status = 'bounded_limit'; error = None
    while True:
        if cursor in visited:
            status = 'visited_loop'; error = 'Descriptor address repeated'; break
        if cursor & 1 or cursor < address or cursor + 4 > limit:
            status = 'unsupported_address_or_bound'; error = 'Aligned fixed-ROM64KiB descriptor window exceeded'; break
        visited.add(cursor)
        stride, kind = struct.unpack_from('>hH', program, cursor)
        size = 6 if kind == 1 else 8 if kind == 2 else 4
        row = dict(cpu_address=cursor, rom_offset=cursor, phase=phase, stride_signed=stride,
                   stride_raw=program[cursor:cursor+2].hex(), type_word=kind)
        if kind not in (0, 1, 2, 3):
            row['raw_hex'] = program[cursor:cursor+4].hex(); rows.append(row)
            status = 'unknown_type'; error = 'Unsupported descriptor type'; break
        if cursor + size > limit:
            row['available_raw_hex'] = program[cursor:limit].hex(); rows.append(row)
            status = 'truncated_record'; error = 'Required raw fields exceed window'; break
        row['minimum_field_size'] = size; row['raw_hex'] = program[cursor:cursor+size].hex()
        if kind == 1: row['request_slots_word'] = struct.unpack_from('>H',program,cursor+4)[0]
        if kind == 2: row['node_ram_pointer'] = struct.unpack_from('>I',program,cursor+4)[0]
        if kind == 3:
            rows.append(row); status = 'type3_terminal'; break
        if kind == 0 and phase == 'suffix':
            rows.append(row); status = 'unsupported_type0_in_suffix'; error = 'Only prefix type0 transition specified'; break
        next_address = cursor + stride; row['next_cpu_address'] = next_address
        rows.append(row)
        if stride < 0:
            status = 'unsupported_negative_stride'; error = 'Negative stride requires main review'; break
        if kind == 0: phase = 'suffix'
        cursor = next_address
    return dict(cpu_address=address, rom_offset=address, window_end_exclusive=limit,
                status=status, error=error, records=rows,
                classification='Raw stride/type candidates following main-confirmed prefix/suffix grammar; not native execution or allocation semantics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/scene_setup'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]; program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256 or hashlib.sha256(program).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported canonical source')
    script_addresses = set(); refs = []
    for group, address in enumerate(struct.unpack_from('>%dI' % COUNT, program, INDEX)):
        for record in decode_group(program,address)['records']:
            pointer = struct.unpack_from('>I',program,record['source_cpu_address']+2)[0]
            if pointer: script_addresses.add(pointer)
    for script in sorted(script_addresses):
        end, commands, terminal = command_span(program,script)
        for command in commands:
            if command['opcode'] != 8: continue
            operands = bytes.fromhex(command['operand_hex']); pointer = struct.unpack('>I',operands)[0]
            refs.append(dict(script_cpu_address=script, command_cpu_address=command['source_cpu_address'],
                operand_raw_hex=operands.hex(), descriptor_cpu_address=pointer,
                descriptor_rom_offset=pointer if pointer < 0x100000 else None))
    descriptors = [descriptor_inventory(program,a) for a in sorted({r['descriptor_cpu_address'] for r in refs})]
    assert len(script_addresses) == 41 and len(refs) == 41
    rows = [row for descriptor in descriptors for row in descriptor['records']]
    type_counts = Counter(row['type_word'] for row in rows)
    stride_counts = Counter(row['stride_signed'] for row in rows)
    request_counts = Counter(row['request_slots_word'] for row in rows if 'request_slots_word' in row)
    report = dict(source=source, program_code_modified=False,
        mapping='Descriptor CPU addresses fixed first1MiB equal ROM offsets; node RAM pointers remain separate.',
        script_count=len(script_addresses), reference_count=len(refs), unique_descriptor_count=len(descriptors),
        references=refs, descriptors=descriptors,
        unique_descriptor_record_count=len(rows),
        type_counts=[dict(type_word=value,count=count) for value,count in sorted(type_counts.items())],
        stride_counts=[dict(stride_signed=value,count=count) for value,count in sorted(stride_counts.items())],
        request_counts=[dict(request_slots_word=value,count=count) for value,count in sorted(request_counts.items())],
        node_ram_pointers=sorted({row['node_ram_pointer'] for row in rows if 'node_ram_pointer' in row}),
        status_counts={s:sum(d['status']==s for d in descriptors) for s in sorted({d['status'] for d in descriptors})},
        limitations='Minimum required fields only, not logical record lengths. Stride is signed firstword; type is secondword. '
            'Prefix0 advances once then switches to suffix,3 terminates. Negative stride/unknown type/loop/bounds preserved as unsupported. '
            'No request allocation/node layout/helper behavior or natural reachability interpretation.')
    output = Path(args.output); output = output if output.is_absolute() else root/output; output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    lines = ['; Raw opcode08 descriptor fields, not code disassembly/native execution.']
    for d in descriptors:
        lines.append('; descriptor %06x %s' % (d['cpu_address'],d['status']))
        for row in d['records']:
            lines.append('%06x %-6s stride=%d type=%d raw=%s request=%s node=%s' % (row['cpu_address'],row['phase'],row['stride_signed'],row['type_word'],row.get('raw_hex',row.get('available_raw_hex','')),row.get('request_slots_word','-'),hex(row['node_ram_pointer']) if 'node_ram_pointer' in row else '-'))
    (output/'inventory.asm').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(references=len(refs), unique_descriptors=len(descriptors),
        records=sum(len(d['records']) for d in descriptors), status_counts=report['status_counts'],
        report_sha256=hashlib.sha256((output/'report.json').read_bytes()).hexdigest(),
        listing_sha256=hashlib.sha256((output/'inventory.asm').read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
