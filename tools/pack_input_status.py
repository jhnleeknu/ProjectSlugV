"""Preserve the complete fixed-ROM byte lookup window used by native b68."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, END = 0xb58, 0xc58
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '3a9b0abce59ff1b1b9f93b2d729519def993bd1e9ca3a3b0655c1d2fefc9b756'


def validate_payload(data):
    if len(data) != END - BASE:
        raise ValueError('Input status payload must contain the complete native window')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Input status native bytes changed')


def extract(program):
    if len(program) < END:
        raise ValueError('Truncated input status program window')
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
    (folder / 'input_status.ms5d').write_bytes(packed)
    (folder / 'input_status.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'input-status:00000b58', 'format': 'MS5D',
        'version': 1, 'file': 'input_status.ms5d', 'source': source,
        'source_cpu_address': BASE, 'source_rom_offset': BASE,
        'end_cpu_address': END, 'payload_size': len(data), 'size': len(packed),
        'payload_sha256': hashlib.sha256(data).hexdigest(),
        'sha256': hashlib.sha256(packed).hexdigest(),
        'mapping': 'Fixed ROM; CPU address equals canonical decrypted program offset',
        'lookup_entry_cpu_address': 0xb68,
        'lookup_offset_expression': '(4 + slot_byte) & 255',
        'code_overlap': {'source_cpu_address': 0xb68, 'source_rom_offset': 0xb68,
                         'size': END - 0xb68},
        'scope': 'Complete 256-byte native lookup window, including overlapping code '
                 'bytes. Byte-width lookup permits offsets 0..255; this does not establish '
                 '256 semantic entries or their natural reachability.'
    }, indent=2) + '\n')
    print('Packed input status:', len(packed), 'bytes;', hashlib.sha256(packed).hexdigest())


if __name__ == '__main__':
    main()
