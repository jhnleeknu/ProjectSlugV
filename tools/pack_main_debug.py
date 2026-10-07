"""Preserve the exact native main-loop debug format and 20-pointer table."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, TABLE, END = 0xd56, 0xdf0, 0xe40
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '69457695579f02202848b37b9fe517df1ea77d9ceedf282600d06f6bcf887fbb'
POINTERS = (0x100016, 0x104ca1, 0x104ca3,
            0x10de30, 0x10de31, 0x10de32, 0x10de33, 0x10de34, 0x10de35,
            0x10de36, 0x10de37, 0x10de38, 0x10de39, 0x10de3a, 0x10de3b,
            0x100cfa, 0x100cfe, 0x10d3bc, 0x10d3c0, 0x10d418)


def validate_payload(data):
    if len(data) != END - BASE:
        raise ValueError('Main debug payload must contain the exact native window')
    if struct.unpack_from('>20I', data, TABLE - BASE) != POINTERS:
        raise ValueError('Main debug argument pointer table changed')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Main debug native bytes changed')


def extract(program):
    if len(program) < END:
        raise ValueError('Truncated main debug program window')
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
    (folder / 'main_debug.ms5d').write_bytes(packed)
    manifest = {
        'schema_version': 1, 'id': 'main-debug:00000d56', 'format': 'MS5D',
        'version': 1, 'file': 'main_debug.ms5d', 'source': source,
        'source_cpu_address': BASE, 'source_rom_offset': BASE,
        'end_cpu_address': END, 'payload_size': len(data), 'size': len(packed),
        'payload_sha256': hashlib.sha256(data).hexdigest(),
        'sha256': hashlib.sha256(packed).hexdigest(),
        'mapping': 'Fixed ROM; CPU address equals canonical decrypted program offset',
        'format_stream': {'source_cpu_address': BASE, 'source_rom_offset': BASE,
            'end_cpu_address': TABLE, 'size': TABLE - BASE,
            'terminator_cpu_address': TABLE - 1,
            'embedded_nul_control_operand_cpu_addresses': [0xd58],
            'encoding': 'Original byte/control format stream, preserved without string normalization'},
        'argument_pointer_table': {'source_cpu_address': TABLE, 'source_rom_offset': TABLE,
            'encoding': 'BE32', 'entries': len(POINTERS), 'size': 4 * len(POINTERS),
            'pointers': [{'index': index, 'source_cpu_address': TABLE + 4 * index,
                          'source_rom_offset': TABLE + 4 * index, 'target_cpu_address': target}
                         for index, target in enumerate(POINTERS)]},
        'scope': 'Exact d56..e40 window: native format bytes including embedded NUL control '
                 'operands and final terminator, followed by 20 native BE32 RAM pointers. '
                 'The code beginning at e40 is excluded. No debug-state execution, natural '
                 'display reachability, pointer field semantics or pixels are claimed.'
    }
    metadata = json.dumps(manifest, indent=2) + '\n'
    (folder / 'main_debug.manifest.json').write_text(metadata)
    print('Packed main debug:', len(packed), 'bytes;', hashlib.sha256(packed).hexdigest())
    print('Main debug metadata SHA256:', hashlib.sha256(metadata.encode()).hexdigest())


if __name__ == '__main__':
    main()
