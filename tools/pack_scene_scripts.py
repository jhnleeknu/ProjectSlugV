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


def wrap(payload, address):
    return struct.pack('<4s7I', b'MS5D', 1, 1, address, address, len(payload),
                       zlib.crc32(payload), 0) + payload


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
    for address in sorted({r['script_cpu_address'] for r in references} - {0}):
        end, commands, terminator = command_span(program, address)
        payload = bytes(program[address:end])
        data = wrap(payload, address)
        name = 'scene_%06x.ms5d' % address
        prepared.append((name, data, dict(id='scene-script:%08x' % address, file=name,
            source_cpu_address=address, source_rom_offset=address, end_exclusive=end,
            payload_size=len(payload), size=len(data), sha256=hashlib.sha256(data).hexdigest(),
            payload_sha256=hashlib.sha256(payload).hexdigest(), command_count=len(commands),
            inline_block_count=sum(bool(c['inline_hex']) for c in commands),
            terminator_cpu_address=terminator)))
    # Validate all source spans before publishing any resource.
    folder.mkdir(parents=True, exist_ok=True)
    for name, data, metadata in prepared:
        (folder / name).write_bytes(data)
    manifest = dict(schema_version=1, id='scene-scripts:stage-catalog', format='MS5D', version=1,
        source=source, references=references, scripts=[p[2] for p in prepared],
        scope='Exact contiguous syntax spans through negative-word terminator, including opaque inline bytes. '
              'Null pointers have no resource. Referenced maps, paths and other external targets are not bundled. '
              'No script execution, logical ownership or natural reachability claim.')
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    result = pack(program, source, root / 'extracted/runtime/scene_scripts')
    print(json.dumps(dict(scripts=len(result['scripts']), references=len(result['references']),
                          payload_bytes=sum(s['payload_size'] for s in result['scripts']))))


if __name__ == '__main__':
    main()
