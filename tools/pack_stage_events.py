"""Pack source-verified raw event windows, indirection cells and lookup bytes.

The ff byte bounds a confirmed gate-skip read window, not a complete script.
"""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

from disassemble_program import load_verified_program
from inventory_stage_event_contexts import inventory, walk_gates, fixed_span
from inventory_scene_general_initialization import SOURCE_SHA256

CANONICAL_COUNTS = (47, 47, 95, 48685)
LOOKUP_CPU = 0x30ec
LOOKUP_RAW = bytes.fromhex('6070809090909090')
SCOPE = ('Raw fixed-ROM windows for the confirmed e905c gate-skip reads and future analysis. '
         'All bytes root..terminal_ff+1 are preserved, including opaque intermediate commands. '
         'The one-byte ff stop is a known read boundary, not proof of full script grammar, '
         'logical resource extent, full callback execution, ownership or natural reachability.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wrap(payload, cpu):
    require(payload and cpu > 0 and cpu % 2 == 0 and cpu+len(payload) <= 0x100000,
            'Resource must have nonempty even-addressed fixed-ROM span; odd payload size is allowed')
    return struct.pack('<4s7I', b'MS5D', 1, 1, cpu, cpu, len(payload), zlib.crc32(payload), 0)+payload


def validate_container(packed, cpu):
    require(len(packed) >= 32, 'Truncated MS5D header')
    magic, version, kind, source_cpu, source_rom, size, crc, reserved = struct.unpack('<4s7I', packed[:32])
    payload = packed[32:]
    require((magic, version, kind, source_cpu, source_rom, reserved) == (b'MS5D', 1, 1, cpu, cpu, 0)
            and size == len(payload), 'MS5D identity, mapping, reserved or size mismatch')
    require(crc == zlib.crc32(payload), 'MS5D payload CRC mismatch')
    require(wrap(payload, cpu) == packed, 'Noncanonical MS5D container')
    return payload


def stream_payload(program, cpu):
    require(cpu > 0, 'Null stream cannot be a resource')
    chain = walk_gates(program, cpu)
    require(chain['status'] == 'terminal_ff' and chain['header'] is not None,
            'Unsupported event gate-skip chain')
    require(chain['header']['signed_jump'] >= 0, 'Stream header jump must be nonnegative')
    for gate in chain['gates']:
        require(gate['next_offset_signed'] > 0, 'Gate chain must advance with positive signed WORD offsets')
    terminal = chain['terminal']['cpu_address']
    require(terminal >= cpu and fixed_span(program, cpu, terminal+1-cpu)
            and program[terminal] == 0xff, 'Invalid exact one-byte ff read boundary')
    payload = bytes(program[cpu:terminal+1])
    require(len(payload) == terminal+1-cpu, 'Truncated event raw window')
    return payload, chain


def overlaps(resources):
    result = []
    for i, first in enumerate(resources):
        a, b = first['source_cpu_address'], first['end_cpu_address_exclusive']
        for second in resources[i+1:]:
            c, d = second['source_cpu_address'], second['end_cpu_address_exclusive']
            if a < d and c < b:
                result.append(dict(first_id=first['id'], second_id=second['id'],
                    first_cpu_address=a, second_cpu_address=c,
                    overlap_start_cpu_address=max(a, c), overlap_end_cpu_address_exclusive=min(b, d),
                    classification='exact_duplicate_span' if (a, b) == (c, d) else 'partial_overlap'))
    return result


def build(root):
    # Regenerate the inventory directly; never trust a cached report file.
    report = inventory(root)
    program, source = load_verified_program(root)
    require(source == report['source'] and source['sha256'] == SOURCE_SHA256
            and sha(program) == SOURCE_SHA256, 'Canonical inventory/source mismatch')
    files = {}
    resources = []

    def add(cpu, payload, role, name, stable_id, references, **extra):
        require(name not in files and stable_id not in {r['id'] for r in resources},
                'Duplicate event resource identity')
        require(bytes(program[cpu:cpu+len(payload)]) == payload, 'Resource payload/source mismatch')
        packed = wrap(payload, cpu)
        require(validate_container(packed, cpu) == payload, 'Packed payload/source mismatch')
        files[name] = packed
        metadata = dict(file=name, id=stable_id, role=role, format='MS5D', version=1, kind=1,
            source_cpu_address=cpu, source_rom_offset=cpu,
            end_cpu_address_exclusive=cpu+len(payload), end_rom_offset_exclusive=cpu+len(payload),
            size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
            sha256=sha(packed), payload_sha256=sha(payload), references=references)
        metadata.update(extra)
        resources.append(metadata)

    def references(rows):
        return [dict(group=r['group'], area=r['area'], record_cpu_address=r['record_cpu_address'],
            record_rom_offset=r['record_rom_offset'], indirect_pointer_long=r['indirect_pointer_long'],
            stream_pointer_long=r['stream_pointer_long'], target_word=r['target_word'],
            selected_cursor_cpu_address=r['target_selection']['selected_cursor_cpu_address'],
            selected_cursor_rom_offset=r['target_selection']['selected_cursor_rom_offset'],
            selection_status=r['target_selection']['status']) for r in rows]

    stream_bytes = 0
    for stream in report['streams']:
        cpu = stream['stream_cpu_address']
        payload, chain = stream_payload(program, cpu)
        expected = dict(stream)
        expected.pop('record_references')
        require(chain == expected, 'Regenerated event gate chain/source mismatch')
        refs = [r for r in report['records'] if r['stream_pointer_long'] == cpu]
        require(refs, 'Unreferenced event stream')
        stream_bytes += len(payload)
        add(cpu, payload, 'event_stream', 'event_%06x.ms5d' % cpu, 'stage-event-stream:%08x' % cpu,
            references(refs), header=chain['header'], gate_count=len(chain['gates']),
            gate_cpu_addresses=[g['cpu_address'] for g in chain['gates']],
            terminal_ff_cpu_address=chain['terminal']['cpu_address'],
            terminal_ff_rom_offset=chain['terminal']['rom_offset'], terminal_ff_raw_hex='ff',
            scope=SCOPE)
    pointers = sorted({r['indirect_pointer_long'] for r in report['records']} - {0})
    for cpu in pointers:
        refs = [r for r in report['records'] if r['indirect_pointer_long'] == cpu]
        require(fixed_span(program, cpu, 4, True), 'Invalid indirect pointer read boundary')
        payload = bytes(program[cpu:cpu+4])
        stream = struct.unpack('>I', payload)[0]
        require(all(r['dereference']['raw_hex'] == payload.hex() and r['stream_pointer_long'] == stream
                    for r in refs), 'Event indirection/source mismatch')
        add(cpu, payload, 'event_indirect_pointer', 'pointer_%06x.ms5d' % cpu,
            'stage-event-indirect:%08x' % cpu, references(refs), raw_be32=stream,
            scope='Exact four-byte fixed-ROM indirection read at record+0a pointer; no surrounding table extent claim.')
    require(program[LOOKUP_CPU:LOOKUP_CPU+8] == LOOKUP_RAW, 'Canonical lookup bytes changed')
    add(LOOKUP_CPU, LOOKUP_RAW, 'stage_event_lookup', 'lookup_0030ec.ms5d',
        'stage-event-lookup:000030ec', [],
        scope='Exact eight raw lookup bytes requested for future48398 analysis; field semantics and callback execution are unproven.')
    require((len(report['streams']), len(pointers), len(resources), stream_bytes) == CANONICAL_COUNTS,
            'Unexpected canonical event resource counts or stream bytes')
    for resource in resources:
        payload = validate_container(files[resource['file']], resource['source_cpu_address'])
        require(payload == program[resource['source_rom_offset']:resource['end_rom_offset_exclusive']],
                'Container bytes do not equal exact source window')
    collisions = overlaps(resources)
    counts = dict(resources=len(resources), streams=len(report['streams']), indirect_pointers=len(pointers),
        lookups=1, catalog_records=len(report['records']), stream_payload_bytes=stream_bytes,
        total_payload_bytes=sum(r['payload_size'] for r in resources),
        total_container_bytes=sum(r['size'] for r in resources), overlaps=len(collisions))
    manifest = dict(schema_version=1, id='stage-events', format='MS5D', version=1, source=source,
        stage_catalog_manifest_sha256=report['stage_catalog_manifest_sha256'],
        regenerated_context_sha256=sha((json.dumps(report, indent=2)+'\n').encode()),
        counts=counts, resources=resources, overlaps=collisions,
        null_record_references=references([r for r in report['records'] if not r['stream_pointer_long']]),
        scope=SCOPE)
    require(sha(program) == SOURCE_SHA256, 'Original program changed during packing')
    files['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/stage_events'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items():
            (staging/name).write_bytes(data)
        for name in sorted(n for n in files if n != 'manifest.json'):
            (staging/name).replace(output/name)
        (staging/'manifest.json').replace(output/'manifest.json')
    for name, data in files.items():
        require((output/name).read_bytes() == data, 'Published resource differs from staged bytes')
    print(json.dumps(dict(counts=manifest['counts'], manifest_sha256=sha(files['manifest.json']),
                          regenerated_context_sha256=manifest['regenerated_context_sha256'])))


if __name__ == '__main__':
    main()
