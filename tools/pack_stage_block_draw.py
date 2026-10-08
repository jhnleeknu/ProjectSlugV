"""Pack the confirmed nine-record block stream as existing MS5D v1 kind1."""
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

CPU, END = 0xddfa4, 0xddfdc
SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '14bba835b16c565a15364b794befbc8aca3c2575e28443654fbdae61ea36e30c'
CONTAINER_SHA256 = '6148703a4160af0b0f8514084b222444a57479ba842d8cbed617b200affe034b'
CRC32 = 0x69c2c48f
CONTRACT = 'docs/analysis/stage-block-draw-contract.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_payload(payload):
    require(len(payload) == END-CPU, 'Block table requires exactly 56 payload bytes')
    require(sha(payload) == PAYLOAD_SHA256, 'Block table pinned payload differs')
    require(payload[-2:] == b'\xff\xff', 'Block table sentinel differs')


def wrap(payload):
    validate_payload(payload)
    packed = struct.pack('<4s7I', b'MS5D', 1, 1, CPU, CPU, len(payload),
                         zlib.crc32(payload), 0)+payload
    require(sha(packed) == CONTAINER_SHA256, 'Block table canonical container differs')
    return packed


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated MS5D header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    require((magic, version, kind, cpu, rom, size, reserved) ==
            (b'MS5D', 1, 1, CPU, CPU, END-CPU, 0), 'Invalid block table MS5D header')
    require(len(packed) == 32+size, 'Block table container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc, 'Block table CRC mismatch')
    validate_payload(payload)
    require(crc == CRC32 and sha(packed) == CONTAINER_SHA256,
            'Block table canonical container differs')
    return payload


def build(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    payload = bytes(program[CPU:END]); packed = wrap(payload)
    require(validate_container(packed) == payload, 'Packed table differs from original source')
    records = []
    for index in range(9):
        offset, tile, width, height = struct.unpack_from('>HHBB', payload, index*6)
        records.append(dict(id='stage-block-draw-record:%02d'%index, index=index,
            source_cpu_address=CPU+index*6, source_rom_offset=CPU+index*6,
            payload_offset=index*6, offset=offset, tile=tile, width=width, height=height))
    resource = dict(id='stage-block-draw-table', file='block_table.ms5d',
        role='stage_block_draw_commands', format='MS5D', version=1, kind=1,
        source_cpu_address=CPU, source_rom_offset=CPU,
        end_cpu_address_exclusive=END, end_rom_offset_exclusive=END,
        size=len(packed), payload_size=len(payload), payload_crc32=zlib.crc32(payload),
        sha256=sha(packed), payload_sha256=sha(payload), records=records,
        record_layout=dict(byte_order='big', stride=6, fields=[
            dict(name='offset', offset=0, size=2), dict(name='tile', offset=2, size=2),
            dict(name='width', offset=4, size=1), dict(name='height', offset=5, size=1)]),
        sentinel=dict(payload_offset=54, source_cpu_address=END-2,
            source_rom_offset=END-2, size=2, value=65535),
        provenance=dict(confirmed_contract=CONTRACT,
            source_mapping='Fixed first1MiB CPU address equals original program ROM offset'),
        scope='Exact nine six-byte commands and terminating ffff WORD; no rendered pixel or surrounding extent claim.')
    manifest = dict(schema_version=1, id='stage-block-draw', format='MS5D', version=1,
        source=source, counts=dict(resources=1, records=9, total_payload_bytes=len(payload),
            total_container_bytes=len(packed)), resources=[resource])
    files = {'block_table.ms5d': packed, 'manifest.json': (json.dumps(manifest, indent=2)+'\n').encode()}
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/stage_block_draw'; output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items(): (staging/name).write_bytes(data)
        validate_container((staging/'block_table.ms5d').read_bytes())
        (staging/'block_table.ms5d').replace(output/'block_table.ms5d')
        (staging/'manifest.json').replace(output/'manifest.json')
    for name, data in files.items():
        require((output/name).read_bytes() == data, 'Published bytes differ from staged resource')
    require(json.loads((output/'manifest.json').read_text()) == manifest,
            'Published metadata differs from regenerated metadata')
    print(json.dumps(dict(counts=manifest['counts'], manifest_sha256=sha(files['manifest.json']),
        resource_sha256=sha(files['block_table.ms5d']), payload_sha256=PAYLOAD_SHA256,
        payload_crc32=CRC32)))


if __name__ == '__main__': main()
