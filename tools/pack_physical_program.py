"""Preserve the complete canonical program as MS5D v1 kind3 physical windows.

Kind3 has no CPU/bank binding: header CPU field is the ffffffff sentinel.
Code, data, unused and unknown bytes are all retained without classification.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ROM_SIZE = 0x800000
MAX_PAYLOAD = 0x100000
CPU_SENTINEL = 0xffffffff
KIND = 3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_span(rom_offset, size):
    require(type(rom_offset) is int and 0 <= rom_offset < ROM_SIZE, 'Invalid physical ROM offset')
    require(type(size) is int and 0 < size <= MAX_PAYLOAD, 'Invalid physical payload size')
    require(size <= ROM_SIZE-rom_offset, 'Physical span exceeds8MiB ROM')


def wrap(payload, rom_offset):
    payload = bytes(payload)
    validate_span(rom_offset, len(payload))
    return struct.pack('<4s7I', b'MS5D', 1, KIND, CPU_SENTINEL,
                       rom_offset, len(payload), zlib.crc32(payload), 0)+payload


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated physical program header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    require((magic, version, kind, cpu, reserved) == (b'MS5D', 1, KIND, CPU_SENTINEL, 0),
            'Invalid physical program header')
    validate_span(rom, size)
    require(len(packed) == 32+size, 'Physical program length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc, 'Physical program CRC32 differs')
    return payload


def coverage(resources):
    cursor = 0
    for item in resources:
        require(item['source_rom_offset'] == cursor, 'Physical coverage has gap/overlap/order error')
        size = item['payload_size']
        validate_span(cursor, size)
        cursor += size
        require(item['end_rom_offset_exclusive'] == cursor, 'Physical coverage end differs')
    require(cursor == ROM_SIZE, 'Physical coverage is incomplete')


def source_snapshot(root, source):
    path = root/source['path']
    return path.stat(), sha(path.read_bytes())


def build(root):
    root = Path(root)
    program, source = load_verified_program(root)
    require(source.get('sha256') == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source hash')
    require(source.get('size') == len(program) == ROM_SIZE and source.get('byte_order') == 'big',
            'Canonical source size/byte order differs')
    snapshot = source_snapshot(root, source)
    require(snapshot[1] == SOURCE_SHA256, 'Canonical source file hash differs')
    names = ('tools/pack_physical_program.py', 'tools/disassemble_program.py')
    inputs = {name: sha((root/name).read_bytes()) for name in names}
    files, resources = {}, []
    for rom in range(0, ROM_SIZE, MAX_PAYLOAD):
        payload = bytes(program[rom:rom+MAX_PAYLOAD])
        packed = wrap(payload, rom)
        require(validate_container(packed) == payload, 'Packed source bytes differ')
        name = 'program_rom_%06x.ms5d' % rom
        files[name] = packed
        resources.append(dict(id='physical-program:%08x' % rom, file=name,
            format='MS5D', version=1, kind=KIND, header_cpu_field=CPU_SENTINEL,
            cpu_binding=None, source_rom_offset=rom, end_rom_offset_exclusive=rom+len(payload),
            payload_size=len(payload), size=len(packed), payload_crc32=zlib.crc32(payload),
            payload_sha256=sha(payload), sha256=sha(packed),
            classification='unclassified physical ROM bytes; code/data/unused/unknown preserved'))
    coverage(resources)
    require(b''.join(validate_container(files[r['file']]) for r in resources) == program,
            'Concatenated physical payload differs from canonical source')
    tails = [dict(source_rom_offset=(bank+1)*MAX_PAYLOAD-16,
                  end_rom_offset_exclusive=(bank+1)*MAX_PAYLOAD, size=16,
                  sha256=sha(program[(bank+1)*MAX_PAYLOAD-16:(bank+1)*MAX_PAYLOAD])) for bank in range(1, 8)]
    manifest = dict(schema_version=1, id='canonical-physical-program', source=source,
        format=dict(magic='MS5D', version=1, kind=KIND, header_size=32,
            header_byte_order='little', header_cpu_field=CPU_SENTINEL,
            cpu_binding=None, payload_byte_order='unchanged canonical big-endian source bytes',
            maximum_payload=MAX_PAYLOAD, physical_rom_size=ROM_SIZE),
        provenance=dict(inputs=inputs, source_program_sha256=SOURCE_SHA256,
            mapping='Physical ROM offset only; CPU address, active bank and vector/device selection are caller state'),
        counts=dict(resources=len(resources), total_payload_bytes=ROM_SIZE,
            total_container_bytes=sum(r['size'] for r in resources)),
        exact_coverage=dict(start=0, end_exclusive=ROM_SIZE, adjacent=True, overlap=False, all_source_bytes_preserved=True),
        legacy_kind2_tail_coverage=dict(bytes=112, ranges=tails,
            reason='Legacy kind2 CPU upper bound2ffff0 omits final16bytes of each1MiB bank1..7; physical kind3 retains these raw source bytes without mapping them as ROM at PVC addresses'),
        resources=resources,
        scope='Complete canonical8MiB raw program preservation, including unclassified and unused bytes. '
              'Physical windows do not establish CPU binding, logical resource semantics, natural reachability or C++ consumption.')
    files['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    require(source_snapshot(root, source) == snapshot, 'Canonical source hash/stat changed during packing')
    require(all(sha((root/name).read_bytes()) == digest for name, digest in inputs.items()),
            'Packer provenance changed during packing')
    return files, manifest


def main():
    require(not sys.argv[1:], 'Usage: pack_physical_program.py')
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    again, again_manifest = build(root)
    require(files == again and manifest == again_manifest, 'Two regenerations differ')
    output = root/'extracted/runtime/program_rom'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items():
            (staging/name).write_bytes(data)
            if name.endswith('.ms5d'):
                validate_container((staging/name).read_bytes())
        require(json.loads((staging/'manifest.json').read_text()) == manifest, 'Staged manifest differs')
        for name in files:
            (staging/name).replace(output/name)
    require(all((output/name).read_bytes() == data for name, data in files.items()), 'Published files differ')
    print(json.dumps(dict(counts=manifest['counts'], manifest_sha256=sha(files['manifest.json']),
        source_sha256=SOURCE_SHA256, reproducible_twice=True)))


if __name__ == '__main__':
    main()
