"""Pack the reviewed32byte raw HUD lookup span as existingMS5Dv1kind1."""
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

CPU, END = 0x4e272, 0x4e292
SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '095633d24bf3730eff7bc16f1f39975b01599421b749480b2ad6b8e30859bdda'
CONTAINER_SHA256 = '97e2e029a44238156c22f96c85ea53c66cfebe8f7d3289ed5e8669ba585a8bb6'
CRC32 = 0x07354387
CONTRACT = 'docs/analysis/stage-hud-counter-contract.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_payload(payload):
    require(len(payload) == END-CPU, 'HUD lookup requires exactly 32 payload bytes')
    require(sha(payload) == PAYLOAD_SHA256, 'HUD lookup pinned payload differs')


def wrap(payload):
    validate_payload(payload)
    packed = struct.pack('<4s7I', b'MS5D', 1, 1, CPU, CPU, len(payload),
                         zlib.crc32(payload), 0)+payload
    require(sha(packed) == CONTAINER_SHA256, 'HUD lookup canonical container differs')
    return packed


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated MS5D header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    require((magic, version, kind, cpu, rom, size, reserved) ==
            (b'MS5D', 1, 1, CPU, CPU, END-CPU, 0), 'Invalid block table MS5D header')
    require(len(packed) == 32+size, 'HUD lookup container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc, 'HUD lookup CRC mismatch')
    validate_payload(payload)
    require(crc == CRC32 and sha(packed) == CONTAINER_SHA256,
            'HUD lookup canonical container differs')
    return payload


def build(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    payload = bytes(program[CPU:END]); packed = wrap(payload)
    require(validate_container(packed) == payload, 'Packed table differs from original source')
    reads = []
    for index in range(16):
        reads.append(dict(id='stage-hud-counter-lookup-word:%02d'%index, index=index,
            source_cpu_address=CPU+index*2, source_rom_offset=CPU+index*2,
            payload_offset=index*2, value=struct.unpack_from('>H', payload, index*2)[0],
            nominal_digit_entry=index<10))
    resource = dict(id='stage-hud-counter-raw-lookup', file='lookup.ms5d',
        role='hud_counter_raw_word_reads', format='MS5D', version=1, kind=1,
        source_cpu_address=CPU, source_rom_offset=CPU,
        end_cpu_address_exclusive=END, end_rom_offset_exclusive=END,
        size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
        sha256=sha(packed), payload_sha256=sha(payload), word_reads=reads,
        read_layout=dict(byte_order='big', stride=2, size=2, count=16),
        nominal_digit_entries=10, code_bytes_begin_cpu=0x4e286,
        provenance=dict(confirmed_contract=CONTRACT,
            source_mapping='Fixed first1MiB CPU address equals original program ROM offset'),
        scope='Exact32byte rawlookup read span, including code bytes for indices10..15; not16logical digit entries or a logical table extent claim.')
    manifest = dict(schema_version=1, id='stage-hud-counter', format='MS5D', version=1,
        source=source, counts=dict(resources=1, word_reads=16, total_payload_bytes=len(payload),
            total_container_bytes=len(packed)), resources=[resource])
    files = {'lookup.ms5d': packed, 'manifest.json': (json.dumps(manifest, indent=2)+'\n').encode()}
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/stage_hud_counter'; output.mkdir(parents=True, exist_ok=True)
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
