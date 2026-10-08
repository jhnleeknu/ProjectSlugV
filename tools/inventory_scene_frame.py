"""Explicit frame instruction windows and literal motion WORD+4 inventory.

No field semantics, frame execution or natural reachability are inferred.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_scene_general_initialization import context_inventory
from inventory_scene_motion import inspect_resource
from pack_scene_scripts import SOURCE_SHA256, command_span, wrap

WINDOWS = ((0x1a73c, 0x1a7a8), (0x1a2b4, 0x1a3a6), (0x1a3d6, 0x1a40e),
           (0x1a442, 0x1a470), (0x1a526, 0x1a5a4), (0x19b96, 0x19d08),
           (0x19d08, 0x19dee), (0x19832, 0x199d4), (0x19a40, 0x19b50),
           (0x289e, 0x28ae))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instruction_windows(program):
    windows = []
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Window gap, overlap or out-of-range instruction')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Instruction raw bytes/source mismatch')
            cursor += row['size']
        require(cursor == end, 'Incomplete exact window coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            instructions=rows, undecoded_rows=undecoded))
    return windows


def motion_inventory(root, program, source):
    catalog = context_inventory(root, program, source)
    folder = root/'extracted/runtime/scene_scripts'
    manifest_bytes = (folder/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest['source'] == source, 'Scene scripts manifest/source mismatch')
    expected_catalog_references = [dict(group=r['group'], area=r['area'],
        record_cpu_address=r['record_cpu_address'], script_cpu_address=r['script_pointer_long'],
        resource_id='scene-script:%08x' % r['script_pointer_long'] if r['script_pointer_long'] else None)
        for r in catalog['records']]
    require(manifest['references'] == expected_catalog_references,
            'Scene script catalog reference closure mismatch')
    scripts = manifest['scripts']
    addresses = [s['source_cpu_address'] for s in scripts]
    require(len(addresses) == len(set(addresses)) == 41
            and set(addresses) == {r['script_pointer_long'] for r in catalog['records']}-{0},
            'Scene script pointer closure mismatch')
    motion_references = {}
    for script in scripts:
        cpu = script['source_cpu_address']
        require(script['id'] == 'scene-script:%08x' % cpu
                and script['file'] == 'scene_%06x.ms5d' % cpu,
                'Scene script canonical identity mismatch')
        end, commands, terminal = command_span(program, cpu)
        payload = bytes(program[cpu:end])
        packed = wrap(payload, cpu)
        require(script['source_rom_offset'] == cpu and script['end_exclusive'] == end
                and script['terminator_cpu_address'] == terminal
                and script['command_count'] == len(commands)
                and script['payload_size'] == len(payload) and script['size'] == len(packed)
                and script['payload_sha256'] == sha(payload) and script['sha256'] == sha(packed)
                and (folder/script['file']).read_bytes() == packed,
                'Scene script manifest/container/source mismatch')
        for command in commands:
            if command['opcode'] != 0:
                continue
            pointer = struct.unpack_from('>I', bytes.fromhex(command['operand_hex']), 4)[0]
            if pointer:
                motion_references.setdefault(pointer, []).append(dict(script_cpu_address=cpu,
                    command_cpu_address=command['source_cpu_address'], opcode=0, operand_pointer=pointer))
    metadata = [m for m in manifest['dependencies'] if m['id'].startswith('scene-motion:')]
    roots = [m['source_cpu_address'] for m in metadata]
    require(len(roots) == len(set(roots)) == 37 and set(roots) == set(motion_references),
            'Motion source reference closure mismatch')
    paths = []
    records = []
    for item in metadata:
        cpu = item['source_cpu_address']
        require((item['format'], item['version'], item['kind']) == ('MS5D', 1, 1)
                and item['id'] == 'scene-motion:%08x' % cpu
                and item['file'] == 'motion_%06x.ms5d' % cpu,
                'Motion canonical format/identity mismatch')
        require(item['references'] == motion_references[cpu], 'Motion reference metadata mismatch')
        path = inspect_resource(folder/item['file'], item, program)
        require(item['ordinary_record_count'] == path['ordinary_record_count']
                and item['first_type_word'] == path['first_type_word']
                and item['terminator_cpu_address'] == path['terminal']['cpu_address']
                and item['end_exclusive'] == cpu+path['payload_size']
                and item['size'] == path['payload_size']+32,
                'Motion record count/terminal metadata mismatch')
        entries = []
        for row in path['records']:
            value = row['word_at_4']
            signed = value-0x10000 if value & 0x8000 else value
            record = dict(resource_id=item['id'], root_cpu_address=cpu, root_rom_offset=cpu,
                cpu_address=row['cpu_address'], rom_offset=row['rom_offset'],
                resource_offset=row['resource_offset'], time_word=row['time_word'],
                type_word=row['type_word'], word_at_4_unsigned=value, word_at_4_signed=signed,
                field_offset=4, field_cpu_address=row['cpu_address']+4,
                field_rom_offset=row['rom_offset']+4, field_raw_hex='%04x' % value,
                raw_hex=row['raw_hex'], raw_sha256=sha(bytes.fromhex(row['raw_hex'])))
            entries.append(record)
            records.append(record)
        paths.append(dict(resource_id=item['id'], file=item['file'], root_cpu_address=cpu,
            root_rom_offset=cpu, end_cpu_address_exclusive=item['end_exclusive'],
            end_rom_offset_exclusive=item['end_exclusive'], container_sha256=item['sha256'],
            payload_sha256=item['payload_sha256'], references=item['references'],
            ordinary_record_count=len(entries), records=entries, terminal=path['terminal']))
    values = Counter(r['word_at_4_signed'] for r in records)
    kinds = Counter(r['type_word'] for r in records)
    by_type = []
    for kind in sorted(kinds):
        counts = Counter(r['word_at_4_signed'] for r in records if r['type_word'] == kind)
        by_type.append(dict(type_word=kind, record_count=kinds[kind],
            signed_word_at_4_counts=[dict(value=value, count=count) for value, count in sorted(counts.items())]))
    return dict(scene_scripts_manifest_sha256=sha(manifest_bytes),
        stage_catalog_manifest_sha256=catalog['stage_catalog_manifest_sha256'],
        resource_count=len(paths), ordinary_record_count=len(records), terminal_record_count=len(paths),
        script_command_reference_count=sum(len(p['references']) for p in paths),
        distinct_type_word_count=len(kinds), distinct_signed_word_at_4_count=len(values),
        signed_word_at_4_counts=[dict(value=value, count=count) for value, count in sorted(values.items())],
        type_word_counts=[dict(type_word=kind, count=count) for kind, count in sorted(kinds.items())],
        signed_word_at_4_counts_by_type=by_type, paths=paths,
        scope='Each of37 distinct existing motion raw resources counted once, not weighted by references. '
              'WORD at ordinary record+4 is only converted from raw BE16 to signed16 for literal value counts; '
              'no extent interval, duration, frame progression, field use, type semantics or natural reachability inferred. '
              'Terminal retains exact four raw bytes; no nonexistent terminal+4 WORD is read.')


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    windows = instruction_windows(program)
    motion = motion_inventory(root, program, source)
    require(sha(program) == SOURCE_SHA256, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        provenance='Immutable canonical decrypted original source verified by load_verified_program and pinned hash before/after. '
                   'Existing stage/catalog/script/motion manifests and containers checked against exact original bytes.',
        decoder='Capstone '+capstone.__version__,
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets; RAM/MMIO distinct.',
        window_count=len(windows), instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows),
        windows=windows, motion_word_at_4_inventory=motion,
        scope='Ten main-confirmed explicit bounded frame windows using padded decoder. Every requested byte retained including undecoded rows and bytes after any RTS. '
              'Candidate-only decode; no routine completion, callee effects, field inference, native/C++ execution equivalence or natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/scene_frame_disassembly.json'
    listing_path = root/'artifacts/scene_frame_disassembly.asm'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    listing = ['; Source SHA256 '+SOURCE_SHA256,
               '; Explicit bounded instruction candidates, fixed CPU=ROM. No frame execution/reachability proof.']
    for window in report['windows']:
        listing.append('; [%06x,%06x) SHA256 %s; full assigned bounds, not firstRTS.' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        listing.append(asm(window['instructions']))
    listing_path.write_text('\n'.join(listing)+'\n')
    motion = report['motion_word_at_4_inventory']
    print(json.dumps(dict(windows=report['window_count'], rows=report['instruction_row_count'],
        undecoded=report['undecoded_row_count'], per_window=[dict(start_cpu_address=w['start_cpu_address'],
            rows=w['instruction_row_count'], undecoded=w['undecoded_row_count'], raw_sha256=w['raw_sha256'])
            for w in report['windows']], motion_resources=motion['resource_count'],
        motion_records=motion['ordinary_record_count'], motion_script_references=motion['script_command_reference_count'],
        motion_types=motion['distinct_type_word_count'], signed_word_at_4_counts=motion['signed_word_at_4_counts'],
        report_sha256=sha(path.read_bytes()), asm_sha256=sha(listing_path.read_bytes()))))


if __name__ == '__main__':
    main()
