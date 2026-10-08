"""Pack the reviewed256byte raw object sound lookup span as existingMS5Dv1kind1."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

CPU, END = 0x4411e, 0x4421e
WORD_COUNT = 128
SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = 'eea1eddb352dfc10643395459d1afbd26ad22d1c5d3aa5c0fdf312052e458649'
CONTAINER_SHA256 = 'b8fb48ea03880f2285abf550e43cae731889b3545e1241b48074dcc05a3e6b7e'
CRC32 = 0x7344c719
CONTRACT = 'docs/analysis/stage-object-output-wrappers-contract.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_payload(payload):
    require(len(payload) == END-CPU, 'Object sound lookup requires exactly 256 payload bytes')
    require(sha(payload) == PAYLOAD_SHA256, 'Object sound lookup pinned payload differs')


def wrap(payload):
    payload = bytes(payload)
    validate_payload(payload)
    require(zlib.crc32(payload) == CRC32, 'Object sound lookup pinned CRC differs')
    packed = struct.pack('<4s7I', b'MS5D', 1, 1, CPU, CPU, len(payload),
                         zlib.crc32(payload), 0)+payload
    require(sha(packed) == CONTAINER_SHA256, 'Object sound lookup canonical container differs')
    return packed


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated MS5D header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    require((magic, version, kind, cpu, rom, size, reserved) ==
            (b'MS5D', 1, 1, CPU, CPU, END-CPU, 0), 'Invalid object sound lookup MS5D header')
    require(len(packed) == 32+size, 'Object sound lookup container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc, 'Object sound lookup CRC mismatch')
    validate_payload(payload)
    require(crc == CRC32 and sha(packed) == CONTAINER_SHA256,
            'Object sound lookup canonical container differs')
    return payload


def build(root):
    program, source = load_verified_program(root)
    require(source.get('sha256') == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    require(source.get('size') == len(program) and source.get('byte_order') == 'big',
            'Canonical source metadata size or byte order differs')
    payload = bytes(program[CPU:END]); packed = wrap(payload)
    require(validate_container(packed) == payload, 'Packed table differs from original source')
    reads = []
    for index in range(WORD_COUNT):
        reads.append(dict(id='object-sound-lookup-raw-word:%03d'%index, index=index,
            source_cpu_address=CPU+index*2, source_rom_offset=CPU+index*2,
            payload_offset=index*2, raw_index=index*2, value=struct.unpack_from('>H', payload, index*2)[0]))
    resource = dict(id='object-sound-lookup-raw-window', file='lookup.ms5d',
        role='object_sound_lookup_raw_word_reads', format='MS5D', version=1, kind=1,
        source_cpu_address=CPU, source_rom_offset=CPU,
        end_cpu_address_exclusive=END, end_rom_offset_exclusive=END,
        size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
        sha256=sha(packed), payload_sha256=sha(payload), word_reads=reads,
        read_layout=dict(byte_order='big', stride=2, size=2, count=WORD_COUNT),
        provenance=dict(confirmed_contract=CONTRACT, source_helper_cpu_address=0x47672,
            source_mapping='Fixed first1MiB CPU address equals original program ROM offset'),
        scope='Exact256byte raw read window addressed by every even raw index00..fe from original47672; 128rawWORDpositions, not128logical table entries or a logical table extent claim.')
    manifest = dict(schema_version=1, id='object-sound-lookup', format='MS5D', version=1,
        source=source, counts=dict(resources=1, word_reads=WORD_COUNT, total_payload_bytes=len(payload),
            total_container_bytes=len(packed)), resources=[resource])
    files = {'lookup.ms5d': packed, 'manifest.json': (json.dumps(manifest, indent=2)+'\n').encode()}
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/object_sound_lookup'; output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items(): (staging/name).write_bytes(data)
        validate_container((staging/'lookup.ms5d').read_bytes())
        (staging/'lookup.ms5d').replace(output/'lookup.ms5d')
        (staging/'manifest.json').replace(output/'manifest.json')
    for name, data in files.items():
        require((output/name).read_bytes() == data, 'Published bytes differ from staged resource')
    require(json.loads((output/'manifest.json').read_text()) == manifest,
            'Published metadata differs from regenerated metadata')
    print(json.dumps(dict(counts=manifest['counts'], manifest_sha256=sha(files['manifest.json']),
        resource_sha256=sha(files['lookup.ms5d']), payload_sha256=PAYLOAD_SHA256,
        payload_crc32=CRC32)))


if __name__ == '__main__': main()
