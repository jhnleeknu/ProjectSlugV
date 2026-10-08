"""Pack two exact reviewed animation streams and a raw lookup, without MS5C binding."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

if __package__:
    from .disassemble_program import load_verified_program
    # The existing inspector uses script-style sibling imports. Keep its
    # directory available only during import, including package-mode callers.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from . import inspect_activation_animation_scripts as inspector
    finally:
        sys.path.pop(0)
else:
    from disassemble_program import load_verified_program
    import inspect_activation_animation_scripts as inspector

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
CONTRACT = 'docs/analysis/activation-animation-resource-spans.md'
SPECS = (
    dict(cpu=0x48980, end=0x489c1, magic=b'MS5A', file='animation_048980.ms5a',
         id='activation-animation-048980', crc32=0x03ea76cf,
         payload_sha256='e935bc35b1819d4556467ae99e173abc9d9c45f0dd2b3ef2d5cf1f6f37eafbbd',
         container_sha256='585e124a195c69867d877362b0b7928940fa556cd8ece500e8cdabe997e46821'),
    dict(cpu=0x489c2, end=0x48a12, magic=b'MS5A', file='animation_0489c2.ms5a',
         id='activation-animation-0489c2', crc32=0x4e5cb252,
         payload_sha256='31cad4b876026185b466e17791a7ca6069bc87cf9631d662310c3286eeae89b0',
         container_sha256='7dfd0875267b16598e8bac6600f144e0f4e34096cf540e8504b219fdeee90b1d'),
    dict(cpu=0x48a12, end=0x48e12, magic=b'MS5D', file='lookup_048a12.ms5d',
         id='activation-animation-raw-long-window', crc32=0x3a5f6f4e,
         payload_sha256='13009fd91d93f9463ce4e71875b0131fb89a1d292bb7551258611a0c91bdd5ad',
         container_sha256='f5f305c606593a19b7bf4d5eebe684cf683357c289e48486f7439a3360d9acbd'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def spec_for(cpu):
    for spec in SPECS:
        if spec['cpu'] == cpu:
            return spec
    raise ValueError('Unknown activation animation resource CPU address')


def validate_payload(payload, spec):
    require(len(payload) == spec['end']-spec['cpu'], 'Pinned payload extent differs')
    require(sha(payload) == spec['payload_sha256'], 'Pinned payload SHA256 differs')


def wrap(payload, cpu):
    spec = spec_for(cpu)
    payload = bytes(payload)
    validate_payload(payload, spec)
    require(zlib.crc32(payload) == spec['crc32'], 'Pinned CRC differs')
    packed = struct.pack('<4s7I', spec['magic'], 1, 1, cpu, cpu, len(payload),
                         zlib.crc32(payload), 0)+payload
    require(sha(packed) == spec['container_sha256'], 'Pinned container SHA256 differs')
    return packed


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated activation resource header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    spec = spec_for(cpu)
    require((magic, version, kind, cpu, rom, size, reserved) ==
            (spec['magic'], 1, 1, spec['cpu'], spec['cpu'], spec['end']-spec['cpu'], 0),
            'Invalid activation resource header')
    require(len(packed) == 32+size, 'Activation resource container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc, 'Activation resource CRC mismatch')
    validate_payload(payload, spec)
    require(crc == spec['crc32'] and sha(packed) == spec['container_sha256'],
            'Pinned container CRC or SHA256 differs')
    return payload


def build(root):
    program, source = load_verified_program(root)
    require(source.get('sha256') == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source')
    require(source.get('size') == len(program) and source.get('byte_order') == 'big',
            'Canonical source metadata size or byte order differs')
    inventory = inspector.inspect(program, source)
    inputs = dict(inventory['inputs'])
    inputs['tools/pack_activation_animation.py'] = sha(Path(__file__).read_bytes())
    resources = []
    files = {}
    for index, spec in enumerate(SPECS):
        payload = bytes(program[spec['cpu']:spec['end']])
        packed = wrap(payload, spec['cpu'])
        require(validate_container(packed) == payload, 'Packed payload differs from source')
        files[spec['file']] = packed
        resource = dict(id=spec['id'], file=spec['file'], format=spec['magic'].decode(),
            version=1, kind=1, source_cpu_address=spec['cpu'], source_rom_offset=spec['cpu'],
            end_cpu_address_exclusive=spec['end'], end_rom_offset_exclusive=spec['end'],
            size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
            payload_sha256=sha(payload), sha256=sha(packed))
        if index < 2:
            script = inventory['scripts'][index]
            require(script['source_cpu_address'] == spec['cpu'] and script['size'] == len(payload),
                    'Inspector script mapping differs')
            resource.update(role='animation_command_stream', commands=script['commands'],
                excluded_padding=script['padding'],
                identifier_binding=dict(operation='BE32 operand OR live WORD(object+20)',
                    status='local-caller-EA-conditional' if index == 0 else 'unresolved',
                    local_group_word=0xea if index == 0 else None,
                    condition='47ed0 writes object+20=00ea; applies only while unchanged' if index == 0 else
                        '47d0a setup does not establish object+20; no group selected'),
                caller_cpu_address=0x47ed0 if index == 0 else 0x47d0a)
        else:
            resource.update(role='raw_long_read_window', caller_cpu_address=0x47cd0,
                read_layout=dict(byte_order='big', stride=4, size=4, count=256,
                    index_domain='raw object+7e BYTE0..255, zero extended then multiplied by4'),
                reads=[dict(id='activation-animation-raw-long:%03d'%i, index=i,
                    source_cpu_address=spec['cpu']+4*i, source_rom_offset=spec['cpu']+4*i,
                    payload_offset=4*i, value=struct.unpack_from('>I', payload, 4*i)[0]) for i in range(256)],
                scope='Full BYTE-domain raw read window; not a claim of one logical table extent, natural usage or current C++ consumption')
        resources.append(resource)
    manifest = dict(schema_version=1, id='activation-animation', source=source,
        provenance=dict(contract=CONTRACT,
            mapping='Fixed first1MiB CPU address equals program ROM file offset',
            checked_callers=[dict(cpu_address=cpu, rom_offset=cpu, raw=raw,
                sha256=sha(bytes.fromhex(raw))) for cpu, raw in sorted(inspector.CALLERS.items())],
            inputs=inputs),
        counts=dict(resources=3, scripts=2, draw_commands=17, raw_long_positions=256,
            total_payload_bytes=sum(r['payload_size'] for r in resources),
            total_container_bytes=sum(r['size'] for r in resources)), resources=resources,
        scope='Exact two consumed script spans and raw lookup only; separate489c1 padding excluded. '
            'No MS5C extraction/binding, natural gameplay, palette binding or full animation/C++ execution claim.')
    files['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    require(all(sha((root/name).read_bytes()) == digest for name, digest in inputs.items()),
            'Tool provenance changed during packing')
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/activation_animation'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items():
            (staging/name).write_bytes(data)
        for spec in SPECS:
            validate_container((staging/spec['file']).read_bytes())
        require(json.loads((staging/'manifest.json').read_text()) == manifest, 'Staged metadata differs')
        for name in files:
            (staging/name).replace(output/name)
    require(all((output/name).read_bytes() == data for name, data in files.items()), 'Published files differ')
    print(json.dumps(dict(counts=manifest['counts'], manifest_sha256=sha(files['manifest.json']),
        resources=[dict(file=s['file'], sha256=sha(files[s['file']]),
            payload_sha256=s['payload_sha256'], crc32=s['crc32']) for s in SPECS])))


if __name__ == '__main__':
    main()
