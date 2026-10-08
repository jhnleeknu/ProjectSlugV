"""Literal opcode2c inline condition candidates from canonical scene scripts.

Known selector lengths are comparison labels, not semantic validity checks.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program
from inventory_scene_general_initialization import context_inventory
from pack_scene_scripts import SOURCE_SHA256, command_span, wrap

SELECTOR_LENGTHS = {0:4, 4:10, 8:18}
EMPTY_INLINE_EVIDENCE_BYTES = 18


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    catalog = context_inventory(root, program, source)
    folder = root/'extracted/runtime/scene_scripts'
    manifest_bytes = (folder/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest['source'] == source, 'Scene script source metadata mismatch')
    expected_refs = [dict(group=r['group'], area=r['area'], record_cpu_address=r['record_cpu_address'],
        script_cpu_address=r['script_pointer_long'],
        resource_id='scene-script:%08x' % r['script_pointer_long'] if r['script_pointer_long'] else None)
        for r in catalog['records']]
    require(manifest['references'] == expected_refs, 'Scene script catalog reference closure mismatch')
    addresses = [s['source_cpu_address'] for s in manifest['scripts']]
    require(len(addresses) == len(set(addresses)) == 41
            and set(addresses) == {r['script_pointer_long'] for r in catalog['records']}-{0},
            'Scene script pointer closure mismatch')
    scripts = []
    conditions = []
    total_commands = 0
    for script in manifest['scripts']:
        cpu = script['source_cpu_address']
        require(script['id'] == 'scene-script:%08x' % cpu
                and script['file'] == 'scene_%06x.ms5d' % cpu,
                'Canonical scene script identity mismatch')
        end, commands, terminal = command_span(program, cpu)
        payload = bytes(program[cpu:end])
        packed = wrap(payload, cpu)
        require(script['source_rom_offset'] == cpu and script['end_exclusive'] == end
                and script['terminator_cpu_address'] == terminal
                and script['command_count'] == len(commands)
                and script['inline_block_count'] == sum(bool(c['inline_hex']) for c in commands)
                and script['payload_size'] == len(payload) and script['size'] == len(packed)
                and script['sha256'] == sha(packed) and script['payload_sha256'] == sha(payload)
                and (folder/script['file']).read_bytes() == packed,
                'Scene script container/manifest/source mismatch')
        total_commands += len(commands)
        user_refs = [dict(group=r['group'], area=r['area'],
            record_cpu_address=r['record_cpu_address'], record_rom_offset=r['record_cpu_address'])
            for r in manifest['references'] if r['script_cpu_address'] == cpu]
        script_conditions = []
        for command in commands:
            if command['opcode'] != 0x2c:
                continue
            address = command['source_cpu_address']
            operands = bytes.fromhex(command['operand_hex'])
            inline = bytes.fromhex(command['inline_hex'])
            pointer = address+8
            count = struct.unpack_from('>H', operands, 4)[0]
            require(len(operands) == 6 and count == len(inline)
                    and command['next_cpu_address'] == pointer+count
                    and program[pointer:pointer+count] == inline,
                    'Opcode2c inline address/count/source mismatch')
            selector = struct.unpack_from('>H', inline)[0] if len(inline) >= 2 else None
            expected = SELECTOR_LENGTHS.get(selector)
            if selector is None:
                relation = 'selector_not_available_in_owned_inline'
            elif expected is None:
                relation = 'unknown_selector'
            elif len(inline) == expected:
                relation = 'exact'
            elif len(inline) > expected:
                relation = 'larger'
            else:
                relation = 'truncated'
            evidence = None
            if count == 0:
                following_end = min(pointer+EMPTY_INLINE_EVIDENCE_BYTES, 0x100000, len(program))
                raw = bytes(program[pointer:following_end])
                evidence = dict(start_cpu_address=pointer, start_rom_offset=pointer,
                    end_cpu_address_exclusive=following_end, end_rom_offset_exclusive=following_end,
                    byte_count=len(raw), raw_hex=raw.hex(), raw_sha256=sha(raw),
                    literal_first_word=struct.unpack_from('>H', raw)[0] if len(raw) >= 2 else None,
                    bytes_within_script_span=max(0, min(following_end, end)-pointer),
                    classification='Separate bounded following source bytes, NOT opcode2c owned inline data; may include subsequent commands/terminator or bytes outside script span. No condition record ownership inferred.')
            item = dict(script_id=script['id'], script_cpu_address=cpu, script_rom_offset=cpu,
                command_cpu_address=address, command_rom_offset=address, opcode=0x2c,
                operand_raw_hex=operands.hex(), first_operand_word=struct.unpack_from('>H', operands, 0)[0],
                second_operand_word=struct.unpack_from('>H', operands, 2)[0],
                inline_byte_count_word=count, inline_cpu_address=pointer, inline_rom_offset=pointer,
                end_inline_cpu_address_exclusive=pointer+count, end_inline_rom_offset_exclusive=pointer+count,
                next_command_cpu_address=command['next_cpu_address'],
                inline_raw_hex=inline.hex(), inline_raw_sha256=sha(inline),
                selector_word=selector, selector_raw_hex=inline[:2].hex() if selector is not None else None,
                remaining_raw_hex=inline[2:].hex() if selector is not None else inline.hex(),
                remaining_byte_count=len(inline)-2 if selector is not None else len(inline),
                main_defined_total_inline_bytes=expected, defined_size_comparison=relation,
                stage_catalog_references=user_refs, zero_inline_following_source_evidence=evidence)
            conditions.append(item)
            script_conditions.append(address)
        scripts.append(dict(id=script['id'], file=script['file'], source_cpu_address=cpu,
            source_rom_offset=cpu, end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            command_count=len(commands), opcode2c_count=len(script_conditions),
            opcode2c_command_cpu_addresses=script_conditions, container_sha256=sha(packed),
            payload_sha256=sha(payload), stage_catalog_references=user_refs))
    statuses = Counter(c['defined_size_comparison'] for c in conditions)
    selectors = Counter(c['selector_word'] for c in conditions if c['selector_word'] is not None)
    counts = dict(scripts=len(scripts), decoded_commands=total_commands, opcode2c_commands=len(conditions),
        scripts_with_opcode2c=sum(s['opcode2c_count'] > 0 for s in scripts),
        inline_payload_bytes=sum(c['inline_byte_count_word'] for c in conditions),
        zero_inline_commands=sum(c['inline_byte_count_word'] == 0 for c in conditions),
        missing_owned_inline_selector=sum(c['selector_word'] is None for c in conditions))
    require(total_commands == 814, 'Canonical script command count changed')
    require(sha(program) == SOURCE_SHA256, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        scene_scripts_manifest_sha256=sha(manifest_bytes),
        stage_catalog_manifest_sha256=catalog['stage_catalog_manifest_sha256'],
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets; RAM10d422 is distinct.',
        pointer_basis='Main-confirmed scene opcode2c sets RAMd422 to command CPU+8, the existing scene-script inline_data address; setup dependencies are not the condition source.',
        main_defined_selector_total_inline_bytes=[dict(selector_word=selector, bytes=count)
            for selector, count in sorted(SELECTOR_LENGTHS.items())],
        counts=counts, scripts=scripts, conditions=conditions,
        selector_counts=[dict(selector_word=selector, count=count) for selector, count in sorted(selectors.items())],
        defined_size_comparison_counts=[dict(comparison=relation, count=count) for relation, count in sorted(statuses.items())],
        scope='Mechanical inventory of every literal opcode2c in41 source-verified canonical scene scripts. Owned inline spans follow existing pack_scene_scripts positive-even skip grammar. '
              'Raw selector and remaining bytes retained without rectangle/condition semantics or selector validity assumptions. Main-defined selector0/4/8 total lengths4/10/18 are comparison labels only; larger/truncated/unknown records are reported rather than semantically rejected. '
              'Zero inline following bytes, if any, remain separate unowned evidence. No new packed resources, engine execution, field inference, resource ownership extension or natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/scene_condition_inventory.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(counts=report['counts'], selector_counts=report['selector_counts'],
        defined_size_comparison_counts=report['defined_size_comparison_counts'],
        scene_scripts_manifest_sha256=report['scene_scripts_manifest_sha256'],
        report_sha256=sha(path.read_bytes()))))


if __name__ == '__main__':
    main()
