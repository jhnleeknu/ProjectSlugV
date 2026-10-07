"""Preserve the reviewed four-slot stage palette table as existing MS5D v1."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, END = 0xe7bda, 0xe7bf4
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '55d47a0a681ab9b06490608b3fdb599297c26507093f8c6aa1e072774454e7bc'
EXPECTED = ((0xb,0x25f,2,0),(0xc,0x65,2,0),(0xd,0x67,2,0),(0xe,0x6a,2,0))


def validate_payload(data):
    if len(data) != END-BASE:
        raise ValueError('Stage palettes require the complete26-byte window')
    records = [struct.unpack_from('>HHBB',data,index*6) for index in range(4)]
    if records != list(EXPECTED):
        raise ValueError('Stage palette reviewed fields or sixth byte changed')
    if data[-2:] != b'\xff\xff':
        raise ValueError('Stage palette terminator changed')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Stage palette pinned bytes changed')
    return [dict(record_cpu_address=BASE+index*6, record_rom_offset=BASE+index*6,
        slot=slot, source_id=source, flags=flags, sixth_byte=sixth,
        raw_bytes_hex=bytes(data[index*6:index*6+6]).hex())
        for index,(slot,source,flags,sixth) in enumerate(records)]


def extract(program):
    if len(program) < END:
        raise ValueError('Truncated stage palette program window')
    data = bytes(program[BASE:END])
    validate_payload(data)
    return data


def verify_program(program):
    if len(program) != 8*1024*1024 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program size or SHA256')
    return extract(program)


def pack_payload(data):
    validate_payload(data)
    return struct.pack('<4s7I',b'MS5D',1,1,BASE,BASE,len(data),zlib.crc32(data),0)+data


def validate_container(raw):
    if len(raw) < 32:
        raise ValueError('Truncated stage palette container')
    magic,version,kind,cpu,offset,length,crc,reserved = struct.unpack_from('<4s7I',raw)
    if (magic,version,kind,cpu,offset,length,reserved) != (b'MS5D',1,1,BASE,BASE,END-BASE,0):
        raise ValueError('Stage palette MS5D header schema mismatch')
    if len(raw) != 32+length:
        raise ValueError('Stage palette container length mismatch')
    payload = raw[32:]
    if zlib.crc32(payload) != crc:
        raise ValueError('Stage palette container CRC mismatch')
    validate_payload(payload)
    return payload


def main():
    root = Path(__file__).resolve().parents[1]
    program,source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported program manifest hash')
    data = verify_program(program)
    records = validate_payload(data)
    packed = pack_payload(data)
    assert validate_container(packed) == data
    folder = root/'extracted/runtime'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'stage_palettes.ms5d').write_bytes(packed)
    (folder/'stage_palettes.manifest.json').write_text(json.dumps(dict(
        schema_version=1,id='stage-palettes:000e7bda',format='MS5D',version=1,kind=1,
        file='stage_palettes.ms5d',source=source,source_cpu_address=BASE,source_rom_offset=BASE,
        end_cpu_address_exclusive=END,payload_size=len(data),size=len(packed),
        payload_sha256=hashlib.sha256(data).hexdigest(),sha256=hashlib.sha256(packed).hexdigest(),
        record_count=len(records),record_size=6,records=records,
        terminator_cpu_address=END-2,terminator_rom_offset=END-2,
        mapping='Fixed ROM; CPU address equals canonical decrypted ROM offset.',
        scope='Four reviewed fixed-slot palette bindings and finalffff word. Allsixth bytes preserved. '
            'Existing MS5D v1 kind1 rawwindow; no newformat, no naturalexecution/whole stagepreparation claim.'),indent=2)+'\n')
    print('Stage palettes:',len(records),'records;',len(packed),'bytes;',hashlib.sha256(packed).hexdigest())


if __name__ == '__main__':
    main()
