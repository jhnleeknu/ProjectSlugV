"""Inventory literal placement references and preceding linear opcode00 context.

This does not execute scripts, follow branches, or establish native reachability.
Opcode00's operand LONG at +4 is the d3b4 write documented in scene_command.cpp.
An earlier decoded row is only a linear syntax reference, never runtime state.
"""
import hashlib
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program
from inventory_scene_scripts import decode_script
from pack_scene_scripts import SOURCE_SHA256, command_span, wrap
from pack_scene_placements import build


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical program')
    paths = dict(
        scene_scripts_manifest='extracted/runtime/scene_scripts/manifest.json',
        scene_scripts_inventory='artifacts/scene_scripts/report.json',
        scene_placements_manifest='extracted/runtime/scene_placements/manifest.json',
        scene_placements_inventory='artifacts/scene_placements/inventory.json')
    inputs = {}
    hashes = {}
    raw_inputs = {}
    for key, relative in paths.items():
        raw_inputs[key] = (root / relative).read_bytes()
        inputs[key] = json.loads(raw_inputs[key])
        hashes[key] = sha(raw_inputs[key])
        require(inputs[key]['source'] == source, key + ' source mismatch')
    scripts_manifest = inputs['scene_scripts_manifest']
    scripts_inventory = inputs['scene_scripts_inventory']
    placement_manifest = inputs['scene_placements_manifest']
    placement_inventory = inputs['scene_placements_inventory']
    require(not scripts_inventory['program_code_modified'], 'Modified script source')
    require(placement_manifest['inventory_sha256'] == hashes['scene_placements_inventory']
            and placement_manifest['scene_scripts_manifest_sha256'] == hashes['scene_scripts_manifest'],
            'Placement manifest input hashes mismatch')
    files, metadata = build(program, source, placement_inventory,
                            raw_inputs['scene_scripts_manifest'])
    require(metadata == placement_manifest['resources'], 'Placement manifest metadata mismatch')
    for name, data in files.items():
        require((root / 'extracted/runtime/scene_placements' / name).read_bytes() == data,
                'Placement resource/source mismatch: ' + name)

    decoded = {}
    for entry in scripts_inventory['scripts']:
        address = entry['cpu_address']
        require(address not in decoded, 'Duplicate inventory script')
        require(entry == decode_script(program, address), 'Script inventory/source mismatch')
        decoded[address] = entry
    manifest_addresses = [s['source_cpu_address'] for s in scripts_manifest['scripts']]
    require(len(manifest_addresses) == len(set(manifest_addresses)), 'Duplicate manifest script')
    require(set(manifest_addresses) == set(decoded) - {0}, 'Script inventory/manifest closure mismatch')
    motions = {d['source_cpu_address']: d for d in scripts_manifest['dependencies']
               if d['id'].startswith('scene-motion:')}
    references = []
    command_count = 0
    for script in scripts_manifest['scripts']:
        address = script['source_cpu_address']
        end, commands, terminal = command_span(program, address)
        payload = bytes(program[address:end])
        packed = wrap(payload, address)
        require(script['source_rom_offset'] == address and script['end_exclusive'] == end
                and script['terminator_cpu_address'] == terminal
                and script['command_count'] == len(commands)
                and script['payload_size'] == len(payload) and script['size'] == len(packed)
                and script['payload_sha256'] == sha(payload) and script['sha256'] == sha(packed),
                'Script manifest/source mismatch')
        require((root / 'extracted/runtime/scene_scripts' / script['file']).read_bytes() == packed,
                'Script resource/source mismatch')
        command_count += len(commands)
        preceding = None
        for command in commands:
            operands = bytes.fromhex(command['operand_hex'])
            cpu = command['source_cpu_address']
            if command['opcode'] == 0:
                pointer = struct.unpack_from('>I', operands, 4)[0]
                motion = motions.get(pointer)
                require(pointer == 0 or motion is not None, 'Missing literal motion dependency')
                if motion is not None:
                    motion_payload = bytes(program[pointer:motion['end_exclusive']])
                    require(motion['source_rom_offset'] == pointer
                            and sha(motion_payload) == motion['payload_sha256'],
                            'Motion dependency/source mismatch')
                preceding = dict(command_cpu_address=cpu, command_rom_offset=cpu, opcode=0,
                                 operand_raw_hex=operands.hex(), motion_pointer_long=pointer,
                                 motion_resource_id=motion['id'] if motion else None,
                                 status='literal_null_pointer' if pointer == 0 else 'literal_resource_reference')
            if command['opcode'] == 0x0c:
                pointer = struct.unpack('>I', operands)[0]
                references.append(dict(script_cpu_address=address, script_rom_offset=address,
                    command_cpu_address=cpu, command_rom_offset=cpu, opcode=0x0c,
                    operand_raw_hex=operands.hex(), placement_root_cpu_address=pointer,
                    placement_root_rom_offset=pointer if pointer else None,
                    placement_resource_id='scene-placement:%08x' % pointer if pointer else None,
                    preceding_linear_motion=dict(preceding) if preceding else None,
                    context_status='preceding_linear_opcode00_only' if preceding else 'unknown',
                    placement_record_cpu_addresses=[]))
    expected_refs = [dict(script_cpu_address=r['script_cpu_address'],
        command_cpu_address=r['command_cpu_address'], command_rom_offset=r['command_rom_offset'],
        operand_raw_hex=r['operand_raw_hex'], root_pointer_long=r['placement_root_cpu_address'])
        for r in references]
    require(expected_refs == placement_inventory['references'], 'Placement reference closure mismatch')
    records = {}
    for resource in metadata:
        root_address = resource['source_cpu_address']
        for row in resource['records']:
            cpu = row['cpu_address']
            item = dict(cpu_address=cpu, rom_offset=row['rom_offset'], root_cpu_addresses=[],
                        gate_word=row['gate_word'], word_at_4=row['word_at_4'], word_at_6=row['word_at_6'],
                        bounds_pointer_long=row['bounds_pointer_long'],
                        callback_pointer_long=row['callback_pointer_long'],
                        inline_byte_count_word=row['inline_byte_count_word'],
                        inline_raw_hex=row['inline_raw_hex'], raw_sha256=row['raw_sha256'])
            if cpu in records:
                previous = dict(records[cpu])
                previous['root_cpu_addresses'] = []
                require(previous == item, 'Shared record data mismatch')
            else:
                records[cpu] = item
            records[cpu]['root_cpu_addresses'].append(root_address)
        for reference in references:
            if reference['placement_root_cpu_address'] == root_address:
                reference['placement_record_cpu_addresses'] = [r['cpu_address'] for r in resource['records']]
    counts = dict(scene_scripts=len(manifest_addresses), decoded_script_rows=sum(len(s['rows']) for s in decoded.values()),
                  decoded_commands=command_count, placement_references=len(references),
                  placement_resources=len(metadata), unique_placement_records=len(records),
                  placement_terminals=len({r['terminal_cpu_address'] for r in metadata}),
                  preceding_linear_motion_contexts=sum(r['preceding_linear_motion'] is not None for r in references),
                  unknown_motion_contexts=sum(r['preceding_linear_motion'] is None for r in references))
    require((counts['scene_scripts'], counts['decoded_script_rows'], counts['decoded_commands'],
             counts['placement_references'], counts['placement_resources'],
             counts['unique_placement_records'], counts['placement_terminals']) == (41, 855, 814, 18, 18, 24, 18),
            'Canonical context counts changed')
    require(sha(program) == SOURCE_SHA256, 'Source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        mapping='Fixed first1MiB CPU addresses equal ROM offsets; callback LONGs remain raw values.',
        input_paths=paths, input_sha256=hashes, counts=counts,
        motion_write_basis=dict(opcode=0, operand_long_byte_offset=4, ram_cpu_address=0x10d3b4,
            evidence='engine/src/scene_command.cpp opcode00 branch: next.a2=longword(operands,4); put_long(candidate,0xd3b4,next.a2).'),
        references=references, records=[records[cpu] for cpu in sorted(records)],
        scope='Mechanical verified source/manifest/syntax inventory only. preceding_linear_motion is the latest earlier decoded opcode00 in the same script, including literal null. Absence is unknown; no initial motion state assumed. Linear precedence does not establish execution, control flow, current RAMd3b4, placement use time, or natural reachability. No engine execution, callback semantics or XY interpretation.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root / 'artifacts/scene_placement_execution/contexts.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(counts=report['counts'], input_sha256=report['input_sha256'],
                          report_sha256=sha(path.read_bytes()))))


if __name__ == '__main__':
    main()
