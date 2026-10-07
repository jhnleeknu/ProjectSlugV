"""Immutable explicit scene initialization windows and raw stage contexts.

Instruction candidates and catalog values do not prove runtime reachability.
"""
import hashlib
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program, disassemble_range
from pack_stage_catalog import INDEX, COUNT, decode_group, wrap

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS = ((0x1a5a4, 0x1a73c), (0x19768, 0x19802), (0x199d4, 0x19a00),
           (0x1a29e, 0x1a2b4), (0x19b50, 0x19b96), (0x19cee, 0x19d08),
           (0x19dee, 0x19e60), (0x1a07a, 0x1a086), (0x1a3c8, 0x1a3d6),
           (0x47a94, 0x47aa6))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instruction_inventory(program, source):
    windows = []
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Instruction window has gap, overlap or out-of-range row')
            cursor += row['size']
        require(cursor == end, 'Instruction window lacks exact coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            instructions=rows, undecoded_rows=undecoded))
    return dict(schema_version=1, source=source, program_code_modified=False,
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets; RAM/MMIO addresses are distinct.',
        window_count=len(windows), instruction_row_count=sum(len(w['instructions']) for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows), windows=windows,
        scope='Ten main-confirmed explicit windows including stage caller47a94..47aa6, immutable padded decoder output. Exact coverage including undecoded rows; first RTS does not end a window. No routine completion, control-flow, callee effects, execution equivalence or natural reachability claim.')


def context_inventory(root, program, source):
    folder = root / 'extracted/runtime/stages'
    manifest_bytes = (folder / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest['source'] == source and manifest['index_cpu_address'] == INDEX,
            'Stage catalog source/index mismatch')
    index_raw = bytes(program[INDEX:INDEX+COUNT*4])
    index_packed = wrap(index_raw, INDEX)
    require(manifest['index_sha256'] == sha(index_packed)
            and (folder / manifest['index_file']).read_bytes() == index_packed,
            'Stage catalog index/source mismatch')
    addresses = struct.unpack('>%dI' % COUNT, index_raw)
    require(len(manifest['groups']) == COUNT, 'Stage group count mismatch')
    records = []
    groups = []
    target_counts = {}
    for number, address in enumerate(addresses):
        actual = decode_group(program, address)
        expected = manifest['groups'][number]
        for key in ('source_cpu_address', 'header', 'end_cpu_address', 'records'):
            require(actual[key] == expected[key], 'Stage group metadata/source mismatch')
        require(expected['index'] == number, 'Stage group index mismatch')
        packed = wrap(program[address:actual['end_cpu_address']], address)
        require(expected['size'] == len(packed) and expected['sha256'] == sha(packed)
                and (folder / expected['file']).read_bytes() == packed,
                'Stage group resource/source mismatch')
        groups.append(dict(group=number, source_cpu_address=address, source_rom_offset=address,
                           record_count=len(actual['records'])))
        for area, record in enumerate(actual['records']):
            cpu = record['source_cpu_address']
            raw = bytes(program[cpu:cpu+record['size']])
            pointer = struct.unpack_from('>I', raw, 2)[0]
            target = struct.unpack_from('>H', raw, 0x0e)[0]
            target_counts[target] = target_counts.get(target, 0)+1
            records.append(dict(group=number, area=area, record_cpu_address=cpu,
                record_rom_offset=cpu, record_length=record['size'], record_raw_sha256=sha(raw),
                script_pointer_field_offset=2, script_pointer_field_cpu_address=cpu+2,
                script_pointer_field_rom_offset=cpu+2, script_pointer_raw_hex=raw[2:6].hex(),
                script_pointer_long=pointer, target_field_offset=0x0e,
                target_field_cpu_address=cpu+0x0e, target_field_rom_offset=cpu+0x0e,
                target_raw_hex=raw[0x0e:0x10].hex(), target_word=target))
    pointers = {r['script_pointer_long'] for r in records}
    counts = dict(groups=len(groups), records=len(records), distinct_script_pointers=len(pointers),
                  nonzero_script_pointers=len(pointers-{0}),
                  null_script_records=sum(r['script_pointer_long'] == 0 for r in records),
                  distinct_target_words=len(target_counts))
    require((counts['groups'], counts['records'], counts['distinct_script_pointers'],
             counts['nonzero_script_pointers'], counts['null_script_records']) == (19, 59, 42, 41, 4),
            'Canonical stage/script counts changed')
    return dict(schema_version=1, source=source, program_code_modified=False,
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets.',
        stage_catalog_manifest_sha256=sha(manifest_bytes), stage_index_cpu_address=INDEX,
        stage_index_rom_offset=INDEX, stage_index_raw_sha256=sha(index_raw),
        counts=counts, groups=groups, records=records,
        target_word_counts=[dict(value=value, count=count) for value, count in sorted(target_counts.items())],
        caller_basis=dict(start_cpu_address=0x47a94, end_cpu_address_exclusive=0x47aa6,
            callsite_cpu_address=0x47aa0, scene_initialization_cpu_address=0x1a5a4,
            script_pointer_record_offset=2, target_word_record_offset=0x0e,
            evidence='Main-confirmed raw47a94..47aa6: A4=LONG(A6+76), A0=LONG(A4+2), D0.low=WORD(A4+0e), JSR1a5a4.'),
        scope='Mechanical raw fields from all59 records in19 source-verified existing stage catalog groups. Script pointer/target pairs are literal caller input fields, not natural reachability, ownership, execution frequency, script execution or initializer completion evidence. No engine execution or field semantics beyond main-confirmed caller operand offsets.')


def write_report(path, report):
    path.write_text(json.dumps(report, indent=2) + '\n')
    return sha(path.read_bytes())


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical program')
    instructions = instruction_inventory(program, source)
    contexts = context_inventory(root, program, source)
    require(sha(program) == SOURCE_SHA256, 'Source changed during inventory')
    folder = root / 'artifacts/scene_general_initialization'
    folder.mkdir(parents=True, exist_ok=True)
    hashes = dict(disassembly=write_report(folder/'disassembly.json', instructions),
                  contexts=write_report(folder/'contexts.json', contexts))
    print(json.dumps(dict(windows=instructions['window_count'], rows=instructions['instruction_row_count'],
        undecoded=instructions['undecoded_row_count'], per_window=[dict(
            start_cpu_address=w['start_cpu_address'], rows=w['instruction_row_count'],
            undecoded=w['undecoded_row_count'], raw_sha256=w['raw_sha256']) for w in instructions['windows']],
        counts=contexts['counts'], target_word_counts=contexts['target_word_counts'],
        stage_catalog_manifest_sha256=contexts['stage_catalog_manifest_sha256'], hashes=hashes)))


if __name__ == '__main__':
    main()
