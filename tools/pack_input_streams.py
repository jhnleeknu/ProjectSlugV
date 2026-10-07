"""Retain the four fixed native input playback buffers and pointer tables."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, END = 0xf01fe, 0xf1a0e
BUFFER_SIZE = 0x600
BUFFER_ADDRESSES = (0xf01fe, 0xf07fe, 0xf0e06, 0xf1406)
TABLES = ((0xf0dfe, BUFFER_ADDRESSES[:2]), (0xf1a06, BUFFER_ADDRESSES[2:]))
SELECTOR = 0x180
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = 'e1dc1a531699c43bf6ad556832ec749ba859268e203f8e316436bfe48e016615'


def validate_payload(data):
    if len(data) != END - BASE:
        raise ValueError('Input streams payload must contain the complete native window')
    for address, targets in TABLES:
        actual = struct.unpack_from('>II', data, address - BASE)
        if actual != targets:
            raise ValueError('Input stream pointer table changed at %06x' % address)
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Input stream native bytes changed')


def extract(program):
    if len(program) < END:
        raise ValueError('Truncated input stream program window')
    if program[SELECTOR:SELECTOR + 2] != b'\0\0':
        raise ValueError('Native playback selector word at 000180 changed')
    data = bytes(program[BASE:END])
    validate_payload(data)
    return data


def pack_payload(data):
    validate_payload(data)
    return struct.pack('<4s7I', b'MS5D', 1, 1, BASE, BASE, len(data),
                       zlib.crc32(data), 0) + data


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported ROM')
    data = extract(program)
    packed = pack_payload(data)
    folder = root / 'extracted/runtime'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'input_streams.ms5d').write_bytes(packed)
    (folder / 'input_streams.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'input-streams:000f01fe', 'format': 'MS5D',
        'version': 1, 'file': 'input_streams.ms5d', 'source': source,
        'source_cpu_address': BASE, 'source_rom_offset': BASE,
        'end_cpu_address': END, 'payload_size': len(data), 'size': len(packed),
        'payload_sha256': hashlib.sha256(data).hexdigest(),
        'sha256': hashlib.sha256(packed).hexdigest(),
        'mapping': 'Fixed ROM; CPU address equals canonical decrypted program offset',
        'buffers': [{'source_cpu_address': address, 'source_rom_offset': address,
                     'size': BUFFER_SIZE} for address in BUFFER_ADDRESSES],
        'pointer_tables': [{'source_cpu_address': address, 'source_rom_offset': address,
                            'size': 8, 'pointer_encoding': 'BE32',
                            'target_cpu_addresses': list(targets)}
                           for address, targets in TABLES],
        'playback_selector': {'source_cpu_address': SELECTOR, 'source_rom_offset': SELECTOR,
                              'encoding': 'BE16', 'verified_word': 0,
                              'included_in_resource': False},
        'scope': 'Complete native byte window containing four 1536-byte buffers and two '
                 'pointer tables. All record targets and unused bytes are preserved; '
                 'no claim of natural playback reachability or stream semantics.'
    }, indent=2) + '\n')
    print('Packed input streams:', len(packed), 'bytes;', hashlib.sha256(packed).hexdigest())


if __name__ == '__main__':
    main()
