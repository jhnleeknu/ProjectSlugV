"""Preserve reviewed selector-byte address window as existing MS5D v1 kind1."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program, disassemble_range
except ImportError:
    from disassemble_program import load_verified_program, disassemble_range
BASE,END = 0x4e4d2,0x4e552
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = 'aab36d4692c572b94b43fb395e58d13c8b39e8ed0448a91b8a06e52a919cbf86'
EVIDENCE_ADDRESS = 0x4e666
EVIDENCE = bytes.fromhex('41ed5d2a6100000641ed5d2b103c000010106b00001243fafe541031000001ad5d1e10bc00ff4e75')


def verify_program(program):
    if len(program)!=8*1024*1024 or hashlib.sha256(program).hexdigest()!=PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program size or SHA256')


def validate_payload(data):
    if len(data)!=END-BASE:raise ValueError('Selector lookup requires complete128-byte raw window')
    if hashlib.sha256(data).hexdigest()!=PAYLOAD_SHA256:raise ValueError('Selector lookup pinned payload changed')


def extract(program):
    if len(program)<max(END,EVIDENCE_ADDRESS+len(EVIDENCE)):raise ValueError('Truncated selector lookup or evidence')
    if bytes(program[EVIDENCE_ADDRESS:EVIDENCE_ADDRESS+len(EVIDENCE)])!=EVIDENCE:
        raise ValueError('Selector lookup instruction evidence changed')
    data=bytes(program[BASE:END]);validate_payload(data);return data


def validate_container(raw):
    if len(raw)<32:raise ValueError('Truncated MS5D header')
    magic,version,kind,cpu,rom,size,crc,reserved=struct.unpack_from('<4s7I',raw)
    if (magic,version,kind,cpu,rom,size,reserved)!=(b'MS5D',1,1,BASE,BASE,END-BASE,0):
        raise ValueError('Invalid selector lookup MS5D header')
    if len(raw)!=32+size:raise ValueError('Incorrect MS5D file length')
    data=bytes(raw[32:])
    if zlib.crc32(data)!=crc:raise ValueError('MS5D CRC mismatch')
    validate_payload(data);return data


def pack_payload(data):
    validate_payload(data)
    raw=struct.pack('<4s7I',b'MS5D',1,1,BASE,BASE,len(data),zlib.crc32(data),0)+data
    assert validate_container(raw)==data
    return raw


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    verify_program(program)
    if source['sha256']!=PROGRAM_SHA256:raise ValueError('Unsupported program manifest')
    data=extract(program);raw=pack_payload(data)
    rows=disassemble_range(program,EVIDENCE_ADDRESS,len(EVIDENCE),EVIDENCE_ADDRESS)
    assert all(row['classification']=='candidate_instruction' for row in rows)
    folder=root/'extracted/runtime';folder.mkdir(parents=True,exist_ok=True)
    (folder/'stage_selector_lookup.ms5d').write_bytes(raw)
    (folder/'stage_selector_lookup.manifest.json').write_text(json.dumps(dict(
        schema_version=1,id='stage-selector-lookup:0004e4d2',format='MS5D',version=1,kind=1,
        file='stage_selector_lookup.ms5d',source=source,source_cpu_address=BASE,source_rom_offset=BASE,
        end_cpu_address_exclusive=END,payload_size=len(data),size=len(raw),
        payload_sha256=hashlib.sha256(data).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),
        instruction_evidence=rows,
        lookup='4e680 uses base4e4d2 + signedD0.word, preserving bits8..15 across byteoperations. '
            'This128-byte window supports nonnegative0..127 byte offsets only; nonzero bits8..15 require a wider signed-index address window.',
        mapping='Fixed first1MiB CPU address equals canonical decrypted ROM offset.',
        scope='Raw128-byte addressable evidence window, not a logical128-entry table. Preserveallbytes without '
            'semanticentrynames. Natural selector use, general register-index paths and full stage gameplay unverified.'),indent=2)+'\n')
    print('Stage selector lookup:',len(data),'payloadbytes;',len(raw),'containerbytes;',hashlib.sha256(raw).hexdigest())


if __name__=='__main__':main()
