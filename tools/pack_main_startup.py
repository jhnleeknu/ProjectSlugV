"""Preserve the reviewed e7b58 fixed-slot startup registration table as MS5D."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, END = 0xe7b58, 0xe7bc0
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '97fdbfce46bb8f350568606b4250550f51ef2c148ec01912845f07a730bda3ca'
EXPECTED = ((0,0x62,2),(1,0x69,2),(2,0x6b,2),(3,0x6c,2),(4,0x63,2),
            (5,0x1b8,2),(6,0x62,2),(7,1,0),(8,0xb03,0),(9,0xb04,0),
            (10,0xb05,0),(15,0xb06,0),(11,0xffff,2),(12,0xffff,2),
            (13,0xffff,2),(14,0xffff,2),(255,1,0))


def validate_payload(data):
    if len(data) != END-BASE:
        raise ValueError('Startup table requires the complete 104-byte window')
    records = [struct.unpack_from('>HHBB', data, index*6) for index in range(17)]
    if [(slot, source, flags) for slot, source, flags, sixth in records] != list(EXPECTED):
        raise ValueError('Startup table reviewed records changed')
    if any(sixth != 0 for _, _, _, sixth in records) or data[-2:] != b'\xff\xff':
        raise ValueError('Startup table sixth byte or terminator changed')
    if len({source for _, source, _, _ in records if source != 0xffff}) != 11:
        raise ValueError('Startup table valid palette ID count changed')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Startup table pinned bytes changed')
    return [{'record_rom_offset': BASE+index*6, 'record_cpu_address': BASE+index*6,
        'slot': slot, 'source_id': source, 'flags': flags, 'sixth_byte': sixth,
        'disabled': source == 0xffff} for index, (slot, source, flags, sixth) in enumerate(records)]


def extract(program):
    if len(program) < END:
        raise ValueError('Truncated main startup program window')
    data = bytes(program[BASE:END])
    validate_payload(data)
    return data


def pack_payload(data):
    validate_payload(data)
    return struct.pack('<4s7I', b'MS5D', 1, 1, BASE, BASE, len(data), zlib.crc32(data), 0)+data


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program')
    data = extract(program)
    records = validate_payload(data)
    packed = pack_payload(data)
    folder = root/'extracted/runtime'
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'main_startup.ms5d').write_bytes(packed)
    (folder/'main_startup.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'main-startup:000e7b58', 'format': 'MS5D', 'version': 1,
        'file': 'main_startup.ms5d', 'source': source, 'source_cpu_address': BASE,
        'source_rom_offset': BASE, 'end_cpu_address_exclusive': END,
        'payload_size': len(data), 'size': len(packed), 'payload_sha256': hashlib.sha256(data).hexdigest(),
        'sha256': hashlib.sha256(packed).hexdigest(), 'record_count': len(records),
        'valid_unique_source_ids': sorted({record['source_id'] for record in records if not record['disabled']}),
        'records': records, 'terminator_rom_offset': END-2,
        'mapping': 'Fixed ROM; CPU addresses equal canonical decrypted file offsets.',
        'scope': 'Reviewed e7bf4/8da2 fixed-slot registration data. Source ffff disables a slot; destination ffff terminates the table. Sixth bytes are preserved. No execution or complete startup equivalence claimed.'}, indent=2)+'\n')
    print('Main startup:', len(records), 'records;', len(packed), 'bytes;', hashlib.sha256(packed).hexdigest())


if __name__ == '__main__':
    main()
