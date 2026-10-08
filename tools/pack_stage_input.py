"""Pack the confirmed four-byte default input mask as MS5D v1 kind1 data."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
    from .pack_scene_scripts import SOURCE_SHA256
except ImportError:
    from disassemble_program import load_verified_program
    from pack_scene_scripts import SOURCE_SHA256

CPU = 0x49ab0
RAW = bytes.fromhex('10204080')
CONTRACT = 'docs/analysis/stage-frame-followup.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wrap(payload):
    require(payload == RAW, 'Default input mask must be the exact confirmed four bytes')
    return struct.pack('<4s7I', b'MS5D', 1, 1, CPU, CPU, len(payload),
                       zlib.crc32(payload), 0)+payload


def validate_container(packed):
    require(len(packed) == 32+len(RAW), 'Default mask container length mismatch')
    header = struct.unpack('<4s7I', packed[:32])
    require(header == (b'MS5D', 1, 1, CPU, CPU, len(RAW), zlib.crc32(RAW), 0),
            'Default mask MS5D header, mapping, size, reserved or CRC mismatch')
    payload = packed[32:]
    require(payload == RAW and wrap(payload) == packed,
            'Default mask payload or canonical container mismatch')
    return payload


def build(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    payload = bytes(program[CPU:CPU+len(RAW)])
    require(payload == RAW, 'Original default mask bytes differ from confirmed source')
    packed = wrap(payload)
    require(validate_container(packed) == program[CPU:CPU+len(RAW)],
            'Packed default mask differs from original source')
    resource = dict(id='stage-input-default-masks', file='default_masks.ms5d',
        role='default_input_masks', format='MS5D', version=1, kind=1,
        source_cpu_address=CPU, source_rom_offset=CPU,
        end_cpu_address_exclusive=CPU+len(RAW), end_rom_offset_exclusive=CPU+len(RAW),
        size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
        sha256=sha(packed), payload_sha256=sha(payload), raw_hex=payload.hex(),
        provenance=dict(confirmed_contract=CONTRACT,
            source_mapping='Fixed first1MiB CPU address equals original program ROM offset'),
        scope='Exact four-byte default mask DATA; no surrounding code/data extent or callback execution claim.')
    manifest = dict(schema_version=1, id='stage-input', format='MS5D', version=1,
        source=source, counts=dict(resources=1, total_payload_bytes=len(payload),
            total_container_bytes=len(packed)), resources=[resource],
        scope='Only the confirmed default four-byte mask is included; this directory may hold separately specified input resources later.')
    files = {'default_masks.ms5d': packed,
             'manifest.json': (json.dumps(manifest, indent=2)+'\n').encode()}
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/stage_input'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items():
            (staging/name).write_bytes(data)
        validate_container((staging/'default_masks.ms5d').read_bytes())
        (staging/'default_masks.ms5d').replace(output/'default_masks.ms5d')
        (staging/'manifest.json').replace(output/'manifest.json')
    for name, data in files.items():
        require((output/name).read_bytes() == data, 'Published bytes differ from staged resource')
    require(json.loads((output/'manifest.json').read_text()) == manifest,
            'Published manifest metadata differs from regenerated metadata')
    print(json.dumps(dict(counts=manifest['counts'],
        manifest_sha256=sha(files['manifest.json']), resource_sha256=sha(files['default_masks.ms5d']),
        payload_sha256=manifest['resources'][0]['payload_sha256'],
        payload_crc32=manifest['resources'][0]['payload_crc32'])))


if __name__ == '__main__':
    main()
