"""Pack catalog-referenced scene command spans as existing MS5D resources."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

try:
    from .disassemble_program import load_verified_program
    from .pack_stage_catalog import decode_group, INDEX, COUNT
except ImportError:
    from disassemble_program import load_verified_program
    from pack_stage_catalog import decode_group, INDEX, COUNT

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
OPERANDS = (8, 2, 4, 4, 4, 6, 6, 4, 2, 6, 2, 6, 8, 2, 8, 2, 2, 4, 2, 4)
NODE_POINTERS = 0x1a08e
PATH_NODES = 0x1a0a6
PALETTE_ROOT = 0x20000c
PALETTE_BANK_START, PALETTE_BANK_END = 0x200000, 0x2ffff0


def command_span(program, address):
    """Positive-even inline skips only; return through first negative opcode."""
    if address <= 0 or address & 1 or address >= min(len(program), 0x100000):
        raise ValueError('Scene script requires nonzero aligned fixed-ROM address')
    cursor = address
    limit = min(len(program), 0x100000, address + 65536)
    commands = []
    while cursor + 2 <= limit:
        start = cursor
        opcode = struct.unpack_from('>H', program, cursor)[0]
        cursor += 2
        if opcode & 0x8000:
            return cursor, commands, start
        if opcode & 3 or opcode // 4 >= len(OPERANDS):
            raise ValueError('Unsupported scene opcode at %06x' % start)
        count = OPERANDS[opcode // 4]
        if cursor + count > limit:
            raise ValueError('Truncated scene operands')
        operands = bytes(program[cursor:cursor + count])
        cursor += count
        skip = struct.unpack_from('>h', operands, 4)[0] if opcode == 0x2c else 0
        if skip < 0 or skip & 1:
            raise ValueError('Unsupported negative or odd scene inline skip')
        if cursor + skip > limit:
            raise ValueError('Truncated scene inline block')
        inline = bytes(program[cursor:cursor + skip])
        cursor += skip
        commands.append(dict(source_cpu_address=start, opcode=opcode,
                             operand_hex=operands.hex(), inline_hex=inline.hex(),
                             next_cpu_address=cursor))
    raise ValueError('Scene script lacks bounded terminator')


def wrap(payload, address, kind=1):
    return struct.pack('<4s7I', b'MS5D', 1, kind, address, address, len(payload),
                       zlib.crc32(payload), 0) + payload



def motion_span(program, address):
    """Preserve 10-byte records through a four-byte ffff terminal prefix."""
    if address <= 0 or address & 1 or address >= min(len(program), 0x100000):
        raise ValueError('Motion path requires nonzero aligned fixed-ROM address')
    cursor = address
    limit = min(len(program), 0x100000, address + 65536)
    records = 0
    first_type = None
    while cursor + 4 <= limit:
        time_word, marker = struct.unpack_from('>HH', program, cursor)
        if marker == 0xffff:
            if records == 0:
                raise ValueError('Motion path first record must be nonterminal')
            return cursor + 4, records, first_type, cursor
        if cursor + 10 > limit:
            raise ValueError('Truncated ordinary motion record')
        if records == 0:
            if marker > 0x8c or marker & 3:
                raise ValueError('Motion first type outside confirmed18c06 dispatch')
            first_type = marker
        records += 1
        cursor += 10
    raise ValueError('Motion path lacks bounded terminal prefix')



def palette_lookup_address(root, selector):
    shifted = (selector << 2) & 0xffff
    signed_offset = shifted - 65536 if shifted & 0x8000 else shifted
    address = root + signed_offset
    if address & 1 or not PALETTE_BANK_START <= address <= PALETTE_BANK_END - 4:
        raise ValueError('Palette lookup outside bank2MiB data window')
    return address, shifted, signed_offset


def palette_binding_span(program, address):
    if address & 1 or not PALETTE_BANK_START <= address < min(len(program), PALETTE_BANK_END):
        raise ValueError('Palette binding requires aligned bank2MiB address')
    cursor = address
    limit = min(len(program), PALETTE_BANK_END, address + 65536)
    records = []
    while cursor + 2 <= limit:
        slot = struct.unpack_from('>H', program, cursor)[0]
        if slot == 0xffff:
            return cursor + 2, records, cursor
        if slot > 255:
            raise ValueError('Palette binding slot exceeds byte range')
        if cursor + 6 > limit:
            raise ValueError('Truncated palette binding record')
        records.append(dict(cpu_address=cursor, rom_offset=cursor, slot_word=slot,
            source_word=struct.unpack_from('>H', program, cursor + 2)[0],
            flags_byte=program[cursor + 4], sixth_byte=program[cursor + 5],
            raw_hex=program[cursor:cursor + 6].hex()))
        cursor += 6
    raise ValueError('Palette binding lacks bounded ffff terminal')

def dependency(program, address, end, name, stable_id, references, kind=1, **extra):
    payload = bytes(program[address:end])
    data = wrap(payload, address, kind)
    metadata = dict(format='MS5D', version=1, kind=kind, id=stable_id, file=name, source_cpu_address=address,
        source_rom_offset=address, end_exclusive=end, size=len(data), payload_size=len(payload),
        sha256=hashlib.sha256(data).hexdigest(), payload_sha256=hashlib.sha256(payload).hexdigest(),
        references=references)
    metadata.update(extra)
    return name, data, metadata

def pack(program, source, folder):
    if len(program) != 8 * 1024 * 1024 or hashlib.sha256(program).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported canonical program')
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Program metadata hash mismatch')
    references = []
    for group, address in enumerate(struct.unpack_from('>%dI' % COUNT, program, INDEX)):
        for area, record in enumerate(decode_group(program, address)['records']):
            record_address = record['source_cpu_address']
            pointer = struct.unpack_from('>I', program, record_address + 2)[0]
            references.append(dict(group=group, area=area, record_cpu_address=record_address,
                                   script_cpu_address=pointer,
                                   resource_id='scene-script:%08x' % pointer if pointer else None))
    prepared = []
    motion_references = {}
    indirect_references = {}
    palette_references = {}
    for address in sorted({r['script_cpu_address'] for r in references} - {0}):
        end, commands, terminator = command_span(program, address)
        for command in commands:
            operands = bytes.fromhex(command['operand_hex'])
            if command['opcode'] == 4:
                selector = struct.unpack_from('>H', operands, 0)[0]
                palette_references.setdefault(selector, []).append(dict(script_cpu_address=address,
                    command_cpu_address=command['source_cpu_address'], opcode=4, selector_word=selector))
            if command['opcode'] not in (0, 0x10):
                continue
            pointer = struct.unpack_from('>I', operands, 4 if command['opcode'] == 0 else 0)[0]
            ref = dict(script_cpu_address=address, command_cpu_address=command['source_cpu_address'],
                       opcode=command['opcode'], operand_pointer=pointer)
            targets = motion_references if command['opcode'] == 0 else indirect_references
            if pointer:
                targets.setdefault(pointer, []).append(ref)
        payload = bytes(program[address:end])
        data = wrap(payload, address)
        name = 'scene_%06x.ms5d' % address
        prepared.append((name, data, dict(id='scene-script:%08x' % address, file=name,
            source_cpu_address=address, source_rom_offset=address, end_exclusive=end,
            payload_size=len(payload), size=len(data), sha256=hashlib.sha256(data).hexdigest(),
            payload_sha256=hashlib.sha256(payload).hexdigest(), command_count=len(commands),
            inline_block_count=sum(bool(c['inline_hex']) for c in commands),
            terminator_cpu_address=terminator)))
    dependencies = [dependency(program, PATH_NODES, PATH_NODES + 16, 'path_nodes.ms5d',
        'scene-path-nodes:0001a0a6', [], scope='Four raw BE32 RAM pointers; known selector table only.')]
    for address, refs in sorted(motion_references.items()):
        end, records, first_type, terminator = motion_span(program, address)
        dependencies.append(dependency(program, address, end, 'motion_%06x.ms5d' % address,
            'scene-motion:%08x' % address, refs, ordinary_record_count=records,
            first_type_word=first_type, terminator_cpu_address=terminator,
            scope='Raw10-byte records plus four-byte terminal prefix. Only first type dispatch validated; subsequent motion effects/types uninterpreted.'))
    for address, refs in sorted(indirect_references.items()):
        if address & 1 or not 0 < address <= min(len(program), 0x100000) - 4:
            raise ValueError('Indirect lookup requires aligned fixed-ROM four-byte span')
        dependencies.append(dependency(program, address, address + 4, 'indirect_%06x.ms5d' % address,
            'scene-indirect:%08x' % address, refs, raw_be32=struct.unpack_from('>I',program,address)[0],
            scope='Single raw indirect BE32 read; pointed target not extracted or interpreted.'))
    root_address = struct.unpack_from('>I', program, PALETTE_ROOT)[0]
    root_refs = [ref for refs in palette_references.values() for ref in refs]
    dependencies.append(dependency(program, PALETTE_ROOT, PALETTE_ROOT + 4, 'palette_root.ms5d',
        'scene-palette-root:%08x' % PALETTE_ROOT, root_refs, kind=2, bank_source_rom_offset=PALETTE_BANK_START,
        bank_cpu_start=PALETTE_BANK_START, raw_be32=root_address,
        scope='Raw root pointer after bank2MiB mapping; no palette color transfer.'))
    binding_references = {}
    lookup_references = {}
    for selector, refs in sorted(palette_references.items()):
        address, shifted, signed_offset = palette_lookup_address(root_address, selector)
        binding = struct.unpack_from('>I', program, address)[0]
        expanded = [dict(ref, shifted_word=shifted, signed_offset=signed_offset,
                         lookup_cpu_address=address, binding_cpu_address=binding) for ref in refs]
        lookup_references.setdefault(address, []).extend(expanded)
        binding_references.setdefault(binding, []).extend(expanded)
    for address, refs in sorted(lookup_references.items()):
        dependencies.append(dependency(program, address, address + 4, 'palette_lookup_%06x.ms5d' % address,
            'scene-palette-lookup:%08x' % address, refs, kind=2, bank_source_rom_offset=PALETTE_BANK_START,
            bank_cpu_start=PALETTE_BANK_START, raw_be32=struct.unpack_from('>I',program,address)[0],
            scope='Root plus signed((selector<<2)&ffff) raw four-byte lookup.'))
    for address, refs in sorted(binding_references.items()):
        end, records, terminator = palette_binding_span(program, address)
        dependencies.append(dependency(program, address, end, 'palette_bindings_%06x.ms5d' % address,
            'scene-palette-bindings:%08x' % address, refs, kind=2, bank_source_rom_offset=PALETTE_BANK_START,
            bank_cpu_start=PALETTE_BANK_START, binding_record_count=len(records), records=records,
            terminator_cpu_address=terminator,
            scope='Raw six-byte binding records plus two-byte ffff firstword terminal; color transfer not executed.'))
    # Validate all source spans before publishing any resource.
    folder.mkdir(parents=True, exist_ok=True)
    for name, data, metadata in prepared:
        (folder / name).write_bytes(data)
    for name, data, metadata in dependencies:
        (folder / name).write_bytes(data)
    node_payload = program[NODE_POINTERS:NODE_POINTERS + 16]
    node_data = wrap(node_payload, NODE_POINTERS)
    (folder / 'node_pointers.ms5d').write_bytes(node_data)
    manifest = dict(schema_version=1, id='scene-scripts:stage-catalog', format='MS5D', version=1,
        source=source, references=references, scripts=[p[2] for p in prepared],
        dependencies=[p[2] for p in dependencies],
        node_pointers=dict(id='scene-node-pointers:0001a08e', file='node_pointers.ms5d',
            source_cpu_address=NODE_POINTERS, source_rom_offset=NODE_POINTERS, payload_size=16,
            sha256=hashlib.sha256(node_data).hexdigest(),
            scope='Four known long pointers used with selectors0/4/8/12. General signed-index lookup unsupported.'),
        scope='Exact contiguous syntax spans through negative-word terminator, including opaque inline bytes. '
              'Null pointers have no resource. Referenced motion raw spans and indirect reads are preserved separately; maps and other external targets are not bundled. '
              'No script execution, logical ownership or natural reachability claim.')
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    result = pack(program, source, root / 'extracted/runtime/scene_scripts')
    print(json.dumps(dict(scripts=len(result['scripts']), references=len(result['references']),
                          payload_bytes=sum(s['payload_size'] for s in result['scripts']),
                          dependency_files=len(result['dependencies']),
                          dependency_payload_bytes=sum(s['payload_size'] for s in result['dependencies']),
                          motion_files=sum(s['file'].startswith('motion_') for s in result['dependencies']),
                          palette_lookup_files=sum(s['file'].startswith('palette_lookup_') for s in result['dependencies']),
                          palette_binding_files=sum(s['file'].startswith('palette_bindings_') for s in result['dependencies']))))


if __name__ == '__main__':
    main()
