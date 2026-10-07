"""Preserve the addressable byte-indexed scene debug lookup window as MS5D."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE,END=0x1af12,0x1b112
PROGRAM_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256='44aae050bb5e0eb32e593dee5e8d81ea41b3c18dd0c6913c763d7ef446bb7583'
EVIDENCE={0x1b094:bytes.fromhex('43fafe7c45faff38'),
    0x1b102:bytes.fromhex('3e300000060700587c001c07dc46383160000c4403206700000c0247c000e75f887270004e75')}


def verify_program(program):
    if hashlib.sha256(program).hexdigest()!=PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program SHA256')


def validate_payload(data):
    if len(data)!=END-BASE:
        raise ValueError('Scene debug requires complete512-byte window')
    if hashlib.sha256(data).hexdigest()!=PAYLOAD_SHA256:
        raise ValueError('Scene debug native payload changed')


def extract(program):
    if len(program)<max(END,*(address+len(code) for address,code in EVIDENCE.items())):
        raise ValueError('Truncated scene debug window or instruction evidence')
    for address,code in EVIDENCE.items():
        if bytes(program[address:address+len(code)])!=code:
            raise ValueError('Scene debug instruction evidence changed at '+hex(address))
    data=bytes(program[BASE:END]);validate_payload(data);return data


def validate_container(packed):
    if len(packed)<32:raise ValueError('Truncated MS5D header')
    magic,version,kind,cpu,rom,size,crc,reserved=struct.unpack('<4s7I',packed[:32])
    if (magic,version,kind,cpu,rom,size,reserved)!=(b'MS5D',1,1,BASE,BASE,END-BASE,0):
        raise ValueError('Invalid scene debug MS5D header')
    if len(packed)!=32+size:raise ValueError('Incorrect MS5D file length')
    data=bytes(packed[32:])
    if zlib.crc32(data)!=crc:raise ValueError('MS5D CRC mismatch')
    validate_payload(data);return data


def pack_payload(data):
    validate_payload(data)
    packed=struct.pack('<4s7I',b'MS5D',1,1,BASE,BASE,len(data),zlib.crc32(data),0)+data
    assert validate_container(packed)==data
    return packed


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    verify_program(program)
    if source['sha256']!=PROGRAM_SHA256:raise ValueError('Unsupported source metadata')
    data=extract(program);packed=pack_payload(data)
    folder=root/'extracted/runtime';folder.mkdir(parents=True,exist_ok=True)
    (folder/'scene_debug.ms5d').write_bytes(packed)
    (folder/'scene_debug.manifest.json').write_text(json.dumps(dict(
        schema_version=1,id='scene-debug:0001af12',format='MS5D',version=1,kind=1,file='scene_debug.ms5d',
        source=source,source_cpu_address=BASE,source_rom_offset=BASE,end_cpu_address_exclusive=END,
        payload_size=len(data),size=len(packed),payload_sha256=hashlib.sha256(data).hexdigest(),
        sha256=hashlib.sha256(packed).hexdigest(),
        lookup_base_cpu_address=BASE,lookup_base_rom_offset=BASE,
        lookup_offset_expression='unsigned byte index *2; complete256-word addressable window',
        flag_lookup=dict(cpu_address=0x1afd2,rom_offset=0x1afd2,byte_size=8,
            interpretation='Referenced by1b098; OR.W indexed flag operands, preserved within full window.'),
        instruction_evidence=[dict(cpu_address=address,rom_offset=address,end_exclusive=address+len(code),
            raw=code.hex(),sha256=hashlib.sha256(code).hexdigest()) for address,code in EVIDENCE.items()],
        mapping='Fixed ROM: CPU addresses equal canonical decrypted file offsets.',
        scope='512-byte addressable lookup window, not a proven logical table extent. Includes flag8bytes at1afd2 '
            'and overlapping code. All native bytes are preserved without semantic entry names or deleting unused '
            'ranges. Natural index reachability, complete stage initialization and runtime behavior remain separate.'),indent=2)+'\n')
    print('Scene debug:',len(packed),'bytes;',hashlib.sha256(packed).hexdigest())


if __name__=='__main__':main()
