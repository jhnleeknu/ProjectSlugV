"""Preserve the caller-backed pause text streams in the existing MS5D format."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program


BASE = 0x9068
CLEAR = 0x9079
END = 0x9086
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
EXPECTED_DATA = bytes.fromhex('5c6c121a5c70005c6303504155534500005c6c121a5c6303202020202000')
CALLERS = ((0x9238, bytes.fromhex('41fafe3f'), CLEAR),
           (0x924c, bytes.fromhex('41fafe1a'), BASE))


def extract(program):
    """Check known native references and retain both streams, including padding."""
    if len(program) < END:
        raise ValueError('Truncated pause text window')
    for address, expected, target in CALLERS:
        if len(program) < address + len(expected):
            raise ValueError('Truncated pause text caller')
        instruction = program[address:address + len(expected)]
        if instruction != expected:
            raise ValueError('Pause text caller changed at %06x' % address)
        displacement = int.from_bytes(instruction[2:4], 'big', signed=True)
        if address + 2 + displacement != target:
            raise ValueError('Pause text caller target changed')
    data = bytes(program[BASE:END])
    if data != EXPECTED_DATA:
        raise ValueError('Pause text streams changed')
    return data


def pack_payload(data):
    if data != EXPECTED_DATA:
        raise ValueError('Pause text payload must match the verified native window')
    return struct.pack('<4s7I', b'MS5D', 1, 1, BASE, BASE, len(data),
                       zlib.crc32(data), 0) + data


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported ROM')
    packed = pack_payload(extract(program))
    folder = root / 'extracted/runtime'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'control_pause.ms5d').write_bytes(packed)
    (folder / 'control_pause.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'control-pause:00009068', 'format': 'MS5D',
        'version': 1, 'file': 'control_pause.ms5d', 'source': source,
        'source_cpu_address': BASE, 'source_rom_offset': BASE,
        'end_cpu_address': END, 'payload_size': END - BASE, 'size': len(packed),
        'sha256': hashlib.sha256(packed).hexdigest(),
        'mapping': 'Fixed ROM; CPU address equals canonical decrypted program offset',
        'text_addresses': [BASE, CLEAR],
        'streams': [
            {'source_cpu_address': BASE, 'source_rom_offset': BASE,
             'size': 16, 'text': 'PAUSE', 'terminator_cpu_address': 0x9077},
            {'source_cpu_address': CLEAR, 'source_rom_offset': CLEAR,
             'size': 13, 'text': '     ', 'terminator_cpu_address': 0x9085}],
        'padding': [{'source_cpu_address': 0x9078, 'source_rom_offset': 0x9078,
                     'size': 1, 'value': 0}],
        'caller_references': [
            {'source_cpu_address': address, 'source_rom_offset': address,
             'raw': instruction.hex(), 'target_cpu_address': target}
            for address, instruction, target in CALLERS],
        'text_encoding': 'Original 386e byte/control stream, retained without Unicode conversion',
        'scope': 'Two caller-backed pause text streams and original inter-stream padding; '
                 'does not claim a complete pause state machine.'
    }, indent=2) + '\n')
    print('Packed pause text 9068/9079:', len(packed), 'bytes')


if __name__ == '__main__':
    main()
