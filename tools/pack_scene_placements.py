"""Pack source-verified placement spans as fixed MS5D v1 raw data windows."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib
try:
    from .disassemble_program import load_verified_program
    from .pack_scene_scripts import SOURCE_SHA256, command_span
except ImportError:
    from disassemble_program import load_verified_program
    from pack_scene_scripts import SOURCE_SHA256, command_span

CANONICAL_COUNTS = (18, 18, 24, 18)  # references, roots, unique records, terminals


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode_payload(payload, cpu):
    if not payload or len(payload) & 1 or cpu & 1 or cpu < 0 or cpu+len(payload) > 0x100000:
        raise ValueError('Empty, odd, unaligned or nonfixed placement span')
    rows = []
    offset = 0
    while offset+2 <= len(payload):
        address = cpu+offset
        gate = struct.unpack_from('>H', payload, offset)[0]
        if gate == 0xffff:
            if offset+2 != len(payload):
                raise ValueError('Bytes after exactffff placement terminal')
            rows.append(dict(cpu_address=address, rom_offset=address, terminal=True,
                             span_size=2, raw_hex=payload[offset:offset+2].hex()))
            return rows
        if offset+16 > len(payload):
            raise ValueError('Truncated placement header')
        gate, count, x, y, bounds, callback = struct.unpack_from('>4H2I', payload, offset)
        if count & 1 or count >= 0x8000:
            raise ValueError('Placement inline count must be even and below8000')
        if bounds:
            raise ValueError('Canonical pack v1 requires null bounds; no invented dependency')
        end = offset+16+count
        if end > len(payload):
            raise ValueError('Truncated placement inline bytes')
        raw = payload[offset:end]
        rows.append(dict(cpu_address=address, rom_offset=address, terminal=False,
                         gate_word=gate, inline_byte_count_word=count, word_at_4=x,
                         word_at_6=y, bounds_pointer_long=bounds, callback_pointer_long=callback,
                         header_raw_hex=raw[:16].hex(), span_size=16+count,
                         next_cpu_address=cpu+end, end_cpu_address_exclusive=cpu+end,
                         end_rom_offset_exclusive=cpu+end, raw_hex=raw.hex(), raw_sha256=sha(raw),
                         inline_raw_hex=raw[16:].hex(), bounds_status='null'))
        offset = end
    raise ValueError('Missing exactffff placement terminal')


def wrap(payload, cpu):
    decode_payload(payload, cpu)
    return struct.pack('<4s7I', b'MS5D', 1, 1, cpu, cpu, len(payload), zlib.crc32(payload), 0)+payload


def validate_container(packed, cpu):
    if len(packed) < 32:
        raise ValueError('Truncated MS5D header')
    magic, version, kind, c, r, size, crc, reserved = struct.unpack('<4s7I', packed[:32])
    payload = packed[32:]
    if (magic, version, kind, c, r, reserved) != (b'MS5D', 1, 1, cpu, cpu, 0) or size != len(payload):
        raise ValueError('MS5D identity or size mismatch')
    if zlib.crc32(payload) != crc:
        raise ValueError('MS5D CRC mismatch')
    if wrap(payload, cpu) != packed:
        raise ValueError('Noncanonical placement container')
    return payload


def placement_payload(program, path):
    cpu = path['root_cpu_address']
    if cpu <= 0 or cpu >= 0x100000 or cpu & 1 or path['root_rom_offset'] != cpu or path['errors'] or path['status'] != 'raw_candidates':
        raise ValueError('Placement inventory root or status invalid')
    cursor = cpu
    limit = min(len(program), 0x100000, cpu+65536)
    for record in range(4096):
        if cursor+2 > limit:
            raise ValueError('Placement scan lacks bounded terminal')
        if struct.unpack_from('>H', program, cursor)[0] == 0xffff:
            cursor += 2
            break
        if cursor+16 > limit:
            raise ValueError('Truncated source placement header')
        count = struct.unpack_from('>H', program, cursor+2)[0]
        if count & 1 or count >= 0x8000 or cursor+16+count > limit:
            raise ValueError('Unsupported source placement inline span')
        cursor += 16+count
    else:
        raise ValueError('Placement record scan budget exceeded')
    payload = bytes(program[cpu:cursor])
    actual = dict(root_cpu_address=cpu, root_rom_offset=cpu, rows=decode_payload(payload, cpu),
                  errors=[], status='raw_candidates', end_cpu_address_exclusive=cursor)
    expected = dict(path)
    expected.pop('references', None)
    if actual != expected:
        raise ValueError('Placement inventory rows differ from original bytes')
    return payload


def verified_references(program, source, manifest_bytes):
    manifest = json.loads(manifest_bytes)
    if manifest['source'] != source or not manifest['scripts']:
        raise ValueError('Scene script manifest source or empty script set')
    refs = []
    scripts_seen = set()
    for script in manifest['scripts']:
        address = script['source_cpu_address']
        if address in scripts_seen:
            raise ValueError('Duplicate script metadata')
        scripts_seen.add(address)
        end, commands, terminal = command_span(program, address)
        if script['source_rom_offset'] != address or end != script['end_exclusive'] or sha(program[address:end]) != script['payload_sha256']:
            raise ValueError('Scene script metadata/source mismatch')
        for command in commands:
            if command['opcode'] == 0xc:
                address = command['source_cpu_address']
                raw = bytes.fromhex(command['operand_hex'])
                if program[address:address+2] != b'\x00\x0c' or program[address+2:address+6] != raw or len(raw) != 4:
                    raise ValueError('Placement reference opcode or operands mismatch')
                refs.append(dict(script_cpu_address=script['source_cpu_address'], command_cpu_address=address,
                                 command_rom_offset=address, operand_raw_hex=raw.hex(),
                                 root_pointer_long=struct.unpack('>I', raw)[0]))
    return refs


def build(program, source, inventory, manifest_bytes):
    if source['sha256'] != SOURCE_SHA256 or sha(program) != SOURCE_SHA256:
        raise ValueError('Unsupported original program source')
    if inventory['source'] != source or inventory['program_code_modified'] or inventory['error_count']:
        raise ValueError('Inventory source/status invalid')
    refs = verified_references(program, source, manifest_bytes)
    if inventory['references'] != refs or inventory['scene_scripts_manifest_sha256'] != sha(manifest_bytes):
        raise ValueError('Inventory reference closure differs from scene scripts')
    paths = inventory['paths']
    roots = [p['root_cpu_address'] for p in paths]
    if not roots or len(roots) != len(set(roots)) or set(roots) != {r['root_pointer_long'] for r in refs if r['root_pointer_long']}:
        raise ValueError('Empty, duplicate or incomplete placement roots')
    files = {}
    metadata = []
    unique = {}
    for path in paths:
        cpu = path['root_cpu_address']
        expected_refs = [r for r in refs if r['root_pointer_long'] == cpu]
        if path['references'] != expected_refs:
            raise ValueError('Placement root reference metadata differs')
        payload = placement_payload(program, path)
        rows = decode_payload(payload, cpu)
        for row in rows:
            if row['cpu_address'] in unique and unique[row['cpu_address']] != row:
                raise ValueError('Conflicting shared placement record metadata')
            unique[row['cpu_address']] = row
        name = 'placement_%06x.ms5d' % cpu
        packed = wrap(payload, cpu)
        if name in files:
            raise ValueError('Duplicate placement resource filename')
        files[name] = packed
        assert validate_container(packed, cpu) == payload
        metadata.append(dict(file=name, id='scene-placement:%08x' % cpu, format='MS5D', version=1, kind=1,
                             source_cpu_address=cpu, source_rom_offset=cpu,
                             end_cpu_address_exclusive=cpu+len(payload), end_rom_offset_exclusive=cpu+len(payload),
                             size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
                             sha256=sha(packed), payload_sha256=sha(payload), references=expected_refs,
                             records=[r for r in rows if not r['terminal']],
                             terminal_cpu_address=rows[-1]['cpu_address'], terminal_rom_offset=rows[-1]['rom_offset'],
                             terminal_gate=0xffff))
    records = sum(not r['terminal'] for r in unique.values())
    terminals = sum(r['terminal'] for r in unique.values())
    actual_counts = (len(refs), len(paths), records, terminals)
    if actual_counts != CANONICAL_COUNTS or (inventory['reference_count'], inventory['unique_root_count'], inventory['unique_record_count'], inventory['unique_terminal_count']) != actual_counts:
        raise ValueError('Unexpected canonical placement counts')
    if inventory['bounds_pointers']:
        raise ValueError('Nonzero bounds dependencies require a later pack version')
    return files, metadata


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    inventory_bytes = (root/'artifacts/scene_placements/inventory.json').read_bytes()
    scripts_bytes = (root/'extracted/runtime/scene_scripts/manifest.json').read_bytes()
    files, metadata = build(program, source, json.loads(inventory_bytes), scripts_bytes)
    manifest = dict(schema_version=1, id='scene-placements', format='MS5D', version=1, source=source,
                    inventory_sha256=sha(inventory_bytes), scene_scripts_manifest_sha256=sha(scripts_bytes),
                    resources=metadata,
                    scope='Raw fixed first1MiB placement spans, CPU=ROM. Exactlyffff terminal; other gate bits and callback LONGs remain raw stored data. Canonical bounds0 only; no invented bounds bytes, callback execution, placement scheduling or lifecycle equivalence claim.')
    files['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    output = root/'extracted/runtime/scene_placements'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items():
            (staging/name).write_bytes(data)
        for name in sorted(n for n in files if n != 'manifest.json'):
            (staging/name).replace(output/name)
        (staging/'manifest.json').replace(output/'manifest.json')
    print(json.dumps(dict(resources=len(metadata), records=sum(len(r['records']) for r in metadata),
                          payload_bytes=sum(r['payload_size'] for r in metadata), manifest_sha256=sha(files['manifest.json']))))


if __name__ == '__main__':
    main()
