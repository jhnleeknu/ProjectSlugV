"""Inventory immutable bank3 tilemap candidates; no extraction or execution."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

from disassemble_program import load_verified_program

CPU_BASE = 0x200000
ROM_BASE = 0x300000
BANK_END = 0x2FFFF0
ROOT_SLOT = 0x200004


def rom_offset(address, size=1):
    if address < CPU_BASE or address + size > BANK_END:
        raise ValueError('tilemap address crosses bank3/PVC boundary')
    return ROM_BASE + address - CPU_BASE


def digest(data):
    return {'sha256': hashlib.sha256(data).hexdigest(),
            'crc32': '%08x' % (zlib.crc32(data) & 0xFFFFFFFF)}


def inventory(program, source, path_inventory, path_inventory_bytes):
    if source['sha256'] != path_inventory['source']['sha256']:
        raise ValueError('scene path inventory and verified program hashes differ')
    root = struct.unpack_from('>I', program, rom_offset(ROOT_SLOT, 4))[0]
    first = struct.unpack_from('>I', program, rom_offset(root, 4))[0]
    if root != 0x200008 or first != 0x20013C or (first - root) % 4:
        raise ValueError('unexpected main-confirmed root/first-map boundary')
    count = (first - root) // 4
    pointers = [struct.unpack_from('>I', program, rom_offset(root + i*4, 4))[0]
                for i in range(count)]
    ordered = all(a < b for a, b in zip(pointers, pointers[1:]))
    descriptors = {}
    for path in path_inventory['paths']:
        for row in path['rows']:
            if row.get('opcode_word') != 4 or row.get('terminal'):
                continue
            address = row['descriptor_cpu_address']
            raw = bytes.fromhex(row['descriptor_raw_hex'])
            if program[address:address + len(raw)] != raw:
                raise ValueError('descriptor inventory bytes differ from immutable source')
            selector, secondary, width, height, column_pointer = struct.unpack('>4HI', raw)
            if (selector, secondary, width, height, column_pointer) != (
                    row['map_selector_word'], row['word_at_2'], row['width_word'],
                    row['height_word'], row['column_pointer_long']):
                raise ValueError('descriptor metadata differs from raw operand fields')
            descriptor = descriptors.setdefault(address, {
                'descriptor_cpu_address': address, 'descriptor_rom_offset': address,
                'opcode_cpu_address': row['cpu_address'],
                'map_selector_word': selector,
                'width': width, 'height': height,
                'raw_hex': raw.hex(), 'path_roots': [], 'script_references': []})
            if path['root_cpu_address'] not in descriptor['path_roots']:
                descriptor['path_roots'].append(path['root_cpu_address'])
            for reference in path['references']:
                if reference not in descriptor['script_references']:
                    descriptor['script_references'].append(reference)
    entries = []
    for selector, pointer in enumerate(pointers):
        offset = rom_offset(pointer, 4)
        width, height = struct.unpack_from('>HH', program, offset)
        if width == 0 or height == 0:
            raise ValueError('nonpositive tilemap header dimensions')
        size = 4 + width*height*4
        end = pointer + size
        rom_offset(pointer, size)
        next_pointer = pointers[selector + 1] if selector + 1 < count else None
        raw = program[offset:offset + size]
        references = [item for item in descriptors.values()
                      if item['map_selector_word'] == selector]
        entries.append({
            'selector_word': selector, 'lookup_cpu_address': root + selector*4,
            'lookup_rom_offset': rom_offset(root + selector*4, 4),
            'source_cpu_address': pointer, 'source_rom_offset': offset,
            'width': width, 'height': height, 'cell_count': width*height,
            'header_raw_hex': raw[:4].hex(), 'header_size': 4, 'cell_stride': 4,
            'cell_order': 'column-major: cell(column,row) offset=4+4*(column*height+row)',
            'raw_span_size': size, 'end_cpu_address': end,
            'end_rom_offset': offset + size, **digest(raw),
            'next_pointer_cpu_address': next_pointer,
            'gap_to_next_pointer': next_pointer - end if next_pointer is not None else None,
            'overlaps_next_pointer': next_pointer is not None and end > next_pointer,
            'descriptor_reference_count': len(references), 'references': references})
    mismatches = []
    out_of_candidate = []
    for descriptor in descriptors.values():
        selector = descriptor['map_selector_word']
        displacement = (selector << 2) & 0xFFFF
        displacement = displacement if displacement < 0x8000 else displacement - 0x10000
        lookup = root + displacement
        descriptor['lookup_cpu_address'] = lookup
        if selector >= count:
            out_of_candidate.append(descriptor)
            continue
        entry = entries[selector]
        descriptor['header_dimensions_match'] = (descriptor['width'], descriptor['height']) == (entry['width'], entry['height'])
        if not descriptor['header_dimensions_match']:
            mismatches.append(descriptor)
    table = program[rom_offset(root, first - root):rom_offset(first)]
    return {
        'source': source, 'program_code_modified': False,
        'mapping': {'cpu_bank_base': CPU_BASE, 'source_rom_bank_base': ROM_BASE,
                    'pvc_overlay_start': BANK_END, 'root_slot_cpu_address': ROOT_SLOT,
                    'lookup_root_cpu_address': root},
        'scene_paths_inventory_sha256': hashlib.sha256(path_inventory_bytes).hexdigest(),
        'candidate_table': {'start_cpu_address': root, 'end_cpu_address': first,
                            'entry_count': count, 'size': len(table), **digest(table),
                            'extent_basis': 'root to first lookup target; structural candidate, not exhaustive-use proof'},
        'entry_count': count, 'pointers_strictly_ordered': ordered,
        'unique_descriptor_count': len(descriptors),
        'unique_referenced_selector_count': len({item['map_selector_word'] for item in descriptors.values()}),
        'dimension_mismatch_count': len(mismatches), 'dimension_mismatches': mismatches,
        'out_of_candidate_references': out_of_candidate,
        'overlap_count': sum(item['overlaps_next_pointer'] for item in entries),
        'internal_gap_count': sum(item['gap_to_next_pointer'] not in (None, 0) for item in entries),
        'map_raw_bytes_total': sum(item['raw_span_size'] for item in entries),
        'last_map_end_cpu_address': entries[-1]['end_cpu_address'],
        'remaining_bank_bytes_after_last_map': BANK_END - entries[-1]['end_cpu_address'],
        'selectors_without_known_descriptor_references': [item['selector_word'] for item in entries if not item['references']],
        'entries': entries,
        'structural_status': 'anomalies' if (not ordered or mismatches or out_of_candidate or any(item['overlaps_next_pointer'] for item in entries)) else 'consistent_candidates',
        'scope': 'Main-confirmed bank3 mapping/cell layout plus immutable structural inventory. References are scene-path CFG syntax candidates; no interpreter execution, natural reachability, unused-data claim, resource extraction or format change.'}


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    before = hashlib.sha256(program).hexdigest()
    input_bytes = (root / 'artifacts/scene_paths/inventory.json').read_bytes()
    report = inventory(program, source, json.loads(input_bytes), input_bytes)
    if hashlib.sha256(program).hexdigest() != before:
        raise AssertionError('verified program was modified')
    directory = root / 'artifacts/scene_tilemaps'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / 'inventory.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in (
        'entry_count', 'unique_descriptor_count', 'unique_referenced_selector_count',
        'dimension_mismatch_count', 'overlap_count', 'internal_gap_count',
        'map_raw_bytes_total', 'selectors_without_known_descriptor_references')}))
    print('report_sha256=' + hashlib.sha256(output.read_bytes()).hexdigest())
    if report['structural_status'] != 'consistent_candidates':
        raise SystemExit('tilemap structural anomalies recorded; investigation required')


if __name__ == '__main__':
    main()
