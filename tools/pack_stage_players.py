"""Preserve the full byte-area addressable stage-player window as MS5D v1."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, END = 0x476bc, 0x47acc
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '25428ef0315eda68ca0e772c8bdba8beaed38c831b835bf866a866e1724b3391'
PAIRS = ((0,0xffff),(3,0xffff),(1,0xffff),(2,1),(4,0xffff))
POINTERS = (0x476bc,0x476c4,0x476cc)
EVIDENCE = {0x476dc: bytes.fromhex('7000102e007c5d400c400003650000047000d040d04041faffdc207000007000102e007dd040d04043f000003219'),
            0x47724: bytes.fromhex('3219')}


def verify_program(program):
    if len(program) != 8*1024*1024 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program size or SHA256')


def validate_payload(data):
    if len(data) != END-BASE:
        raise ValueError('Stage players require complete1040-byte addressable window')
    if tuple(struct.unpack_from('>HH',data,i*4) for i in range(5)) != PAIRS:
        raise ValueError('Stage player five leading pairs changed')
    if struct.unpack_from('>3I',data,20) != POINTERS:
        raise ValueError('Stage player pointer table changed')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Stage player pinned payload changed')


def extract(program):
    if len(program) < END:
        raise ValueError('Truncated stage player addressable window')
    for address,code in EVIDENCE.items():
        if bytes(program[address:address+len(code)]) != code:
            raise ValueError('Stage player instruction evidence changed')
    data = bytes(program[BASE:END]); validate_payload(data); return data


def address_pair(data, stage_byte, area_byte):
    validate_payload(data)
    if not 0 <= stage_byte <= 255 or not 0 <= area_byte <= 255:
        raise ValueError('Stage and area must be unsigned bytes')
    pointer_index = stage_byte-6 if 6 <= stage_byte <= 8 else 0
    address = POINTERS[pointer_index]+area_byte*4
    offset = address-BASE
    if offset < 0 or offset+4 > len(data):
        raise ValueError('Stage player pair outside preserved window')
    return address,struct.unpack_from('>HH',data,offset)


def validate_container(raw):
    if len(raw) < 32: raise ValueError('Truncated MS5D header')
    magic,version,kind,cpu,rom,size,crc,reserved = struct.unpack_from('<4s7I',raw)
    if (magic,version,kind,cpu,rom,size,reserved) != (b'MS5D',1,1,BASE,BASE,END-BASE,0):
        raise ValueError('Invalid stage player MS5D header')
    if len(raw) != 32+size: raise ValueError('Incorrect MS5D file length')
    payload = bytes(raw[32:])
    if zlib.crc32(payload) != crc: raise ValueError('MS5D CRC mismatch')
    validate_payload(payload); return payload


def pack_payload(data):
    validate_payload(data)
    packed = struct.pack('<4s7I',b'MS5D',1,1,BASE,BASE,len(data),zlib.crc32(data),0)+data
    assert validate_container(packed) == data
    return packed


def main():
    root = Path(__file__).resolve().parents[1]; program,source = load_verified_program(root)
    verify_program(program)
    if source['sha256'] != PROGRAM_SHA256: raise ValueError('Unsupported program manifest')
    data = extract(program); packed = pack_payload(data)
    folder = root/'extracted/runtime'; folder.mkdir(parents=True,exist_ok=True)
    (folder/'stage_players.ms5d').write_bytes(packed)
    (folder/'stage_players.manifest.json').write_text(json.dumps(dict(
        schema_version=1,id='stage-players:000476bc',format='MS5D',version=1,kind=1,file='stage_players.ms5d',
        source=source,source_cpu_address=BASE,source_rom_offset=BASE,end_cpu_address_exclusive=END,
        payload_size=len(data),size=len(packed),payload_sha256=hashlib.sha256(data).hexdigest(),sha256=hashlib.sha256(packed).hexdigest(),
        leading_pairs=[dict(cpu_address=BASE+i*4,rom_offset=BASE+i*4,word_00=pair[0],word_02=pair[1]) for i,pair in enumerate(PAIRS)],
        pointer_table=dict(cpu_address=0x476d0,rom_offset=0x476d0,size=12,pointers=list(POINTERS)),
        address_calculation='stagebyte6..8 selects pointerindexstagebyte-6; otherbytes selectfirstpointer. ReadtwoBE16wordsatpointer+areabyte*4.',
        max_read=dict(pointer=0x476cc,area_byte=255,start_cpu_address=END-4,end_cpu_address_exclusive=END),
        instruction_evidence=[dict(cpu_address=a,rom_offset=a,end_exclusive=a+len(code),raw=code.hex(),sha256=hashlib.sha256(code).hexdigest()) for a,code in EVIDENCE.items()],
        mapping='Fixed first1MiB; CPU addresses equal canonical decrypted ROM offsets.',
        scope='1040-byte raw addressable window, not logical table extent. First20bytes are five reviewedpairs, '
            'next12bytes threepointers; subsequentbytes include originalcode. Preserveallbytes, even overlap/unused. '
            'Natural area use, callbackexecution and completeplayers/gameplay remain unverified.'),indent=2)+'\n')
    print('Stage players:',len(data),'payloadbytes;',len(packed),'containerbytes;',hashlib.sha256(packed).hexdigest())


if __name__ == '__main__': main()
