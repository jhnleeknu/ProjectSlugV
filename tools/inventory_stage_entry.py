"""Bounded stage-entry instructions and exact existing stage-catalog fields."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

import capstone
from disassemble_program import disassemble_range, load_verified_program
from inventory_game_initialization import asm
from inventory_object_removal import controls, fields
from pack_stage_catalog import decode_group, INDEX, COUNT

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS = ((0x477ee, 0x478c8), (0x474e2, 0x47558), (0x3d58, 0x3d7c))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_resource(path, address, expected, expected_hash):
    raw = path.read_bytes()
    if len(raw) < 32:
        raise ValueError('Truncated MS5D: ' + str(path))
    header = struct.unpack_from('<4s7I', raw)
    if header != (b'MS5D', 1, 1, address, address, len(expected), zlib.crc32(expected), 0):
        raise ValueError('MS5D schema/source/length/CRC mismatch: ' + str(path))
    if raw[32:] != expected or digest(raw) != expected_hash:
        raise ValueError('MS5D payload or manifest hash mismatch: ' + str(path))
    return dict(file=path.name, container_sha256=digest(raw), payload_sha256=digest(expected),
                source_cpu_address=address, source_rom_offset=address, payload_size=len(expected))


def distribution(values):
    return [dict(value=value, value_hex='0x%x' % value, count=count)
            for value, count in sorted(Counter(values).items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/stage_entry')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or digest(program) != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical ROM')
    blocks = []
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        assert sum(row['size'] for row in rows) == end-start
        assert all(row['rom_offset'] + row['size'] <= end for row in rows)
        for row in rows:
            if INDEX <= row['cpu_address'] < INDEX+COUNT*4:
                row['classification'] = 'known_pointer_index_data_decoded_as_instruction_candidate'
        code_rows = [row for row in rows if row['classification'] == 'candidate_instruction']
        blocks.append(dict(cpu_address=start, rom_offset=start, end_exclusive=end,
            raw_sha256=digest(program[start:end]), instructions=rows,
            control_target_candidates=controls(code_rows), encoded_memory_operand_candidates=fields(code_rows),
            rts_addresses=[row['cpu_address'] for row in code_rows if row['mnemonic']=='rts'],
            boundary_caveat='Explicit bounded window, not complete reachable function. All rows after first RTS retained; '
                'branches/callees not executed or recursively analyzed. End is assigned, not proven function boundary. '
                '474f4..47540 is the known nineteen-pointer data index; its synthetic instruction decodes are excluded from references.'))
    folder = root/'extracted/runtime/stages'
    manifest_raw = (folder/'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if (manifest['schema_version'] != 1 or manifest['id'] != 'stage-catalog:000474f4'
            or manifest['source'] != source or len(manifest['groups']) != COUNT):
        raise ValueError('Stage catalog manifest/source mismatch')
    index_resource = read_resource(folder/manifest['index_file'], INDEX,
        program[INDEX:INDEX+COUNT*4], manifest['index_sha256'])
    groups = []
    records = []
    query_count = 0
    for number, address in enumerate(struct.unpack_from('>19I', program, INDEX)):
        decoded = decode_group(program, address)
        original = manifest['groups'][number]
        for key in ('source_cpu_address', 'header', 'end_cpu_address', 'records'):
            if original[key] != decoded[key]:
                raise ValueError('Manifest record mismatch in group%d' % number)
        if original['size'] != 32+decoded['end_cpu_address']-address:
            raise ValueError('Manifest container size mismatch')
        if original['index'] != number:
            raise ValueError('Manifest group ordering mismatch')
        resource = read_resource(folder/original['file'], address,
            program[address:decoded['end_cpu_address']], original['sha256'])
        group_rows = []
        for area, record in enumerate(decoded['records']):
            cpu = record['source_cpu_address']
            payload = program[cpu:cpu+record['size']]
            row = dict(stage_group=number, area_index=area, id=record['id'],
                length_word_cpu_address=cpu-2, length_word_rom_offset=cpu-2,
                payload_cpu_address=cpu, payload_rom_offset=cpu, payload_length=record['size'],
                payload_sha256=digest(payload), byte_00=payload[0],
                word_10_be=int.from_bytes(payload[0x10:0x12], 'big'),
                selector_test_lt_0x18_and_multiple_4=(payload[0]<0x18 and payload[0]%4==0))
            group_rows.append(row)
            records.append(row)
        # Existing C++ query CLI independently consumes actual containers. No rebuild or RAM mutation.
        for area in range(max(1, len(group_rows))):
            query = json.loads(subprocess.check_output([str(root/'build/query_stage'), str(folder), str(number), str(area)], text=True))
            expected = dict(count=len(group_rows), record=group_rows[area]['payload_cpu_address'] if group_rows else 0,
                name=group_rows[area]['payload_cpu_address']+18 if group_rows else 0)
            if query != expected:
                raise ValueError('Existing query_stage CLI mismatch')
            query_count += 1
        groups.append(dict(stage_group=number, header_word=decoded['header'], resource=resource,
            end_cpu_address_exclusive=decoded['end_cpu_address'], record_count=len(group_rows), records=group_rows))
    invalid = [row for row in records if not row['selector_test_lt_0x18_and_multiple_4']]
    report = dict(source=source, decoder='Capstone '+capstone.__version__, program_code_modified=False,
        mapping='First1MiB fixed CPU address equals canonical ROM offset; RAM/MMIO and banked pointers are separate.',
        windows=blocks, bounded_row_count=sum(len(block['instructions']) for block in blocks),
        catalog_manifest_sha256=digest(manifest_raw), index_resource=index_resource,
        groups=groups, group_count=len(groups), record_count=len(records),
        byte_00_distribution=distribution(row['byte_00'] for row in records),
        word_10_be_distribution=distribution(row['word_10_be'] for row in records),
        length_distribution=distribution(row['payload_length'] for row in records),
        selector_criterion='Host-requested byte00<0x18 and divisible by4; criterion is not inferred dispatch semantics.',
        invalid_selector_count=len(invalid), invalid_selector_records=invalid,
        existing_query_stage_cli_checked=True, query_cli_calls=query_count,
        limitations='Inventory only. No native execution/callee behavior/function completeness proven. '
            'byte00 and word10 are raw field names; music/selector interpretation belongs to main analysis. '
            'All19 existing groups and raw record bytes match pinned source; no resources regenerated or modified.')
    output = Path(args.output)
    if not output.is_absolute():
        output = root/output
    output.mkdir(parents=True, exist_ok=True)
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    with (output/'inventory.asm').open('w') as stream:
        for block in blocks:
            stream.write('; explicit window %06x..%06x exclusive\n' % (block['cpu_address'], block['end_exclusive']))
            stream.write(asm(block['instructions'])+'\n')
    print(json.dumps(dict(groups=len(groups), records=len(records), rows=report['bounded_row_count'],
        invalid_selector_count=len(invalid), query_cli_calls=query_count,
        byte_00_distribution=report['byte_00_distribution'], word_10_be_distribution=report['word_10_be_distribution'],
        report_sha256=digest((output/'report.json').read_bytes()), asm_sha256=digest((output/'inventory.asm').read_bytes()))))


if __name__ == '__main__':
    main()
