"""Preserve twenty fixed16-byte records consumed by4d81c and481de as MS5D v1."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

BASE, END, RECORD_SIZE, RECORD_COUNT = 0x4cf64, 0x4d0a4, 16, 20
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = '9b1c4db78844053dff88ac7c863b15852c1ad1b9e500a831ed5a01fa9eff923c'
# Exact instruction evidence: unsigned D1.word bound, base/stride and field reads;
# caller destination writes. These are code evidence, not embedded record data.
EVIDENCE = {
    0x4d81c: bytes.fromhex('0c410014650000044e4f3001024100ffc2fc001041faf732d0c13228000c142800013628000a38033a28000e1c2800024e75'),
    0x481de: bytes.fromhex('41ed5694024000016700000641ed569c2f084eb90004d81c205f108011410003114200023143000431450006114600014e75')}


def validate_payload(data):
    if len(data) != RECORD_COUNT*RECORD_SIZE:
        raise ValueError('Game records require the complete320-byte window')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Game record native bytes changed')
    return [{'id': index, 'record_cpu_address': BASE+index*RECORD_SIZE,
        'record_rom_offset': BASE+index*RECORD_SIZE,
        'raw_bytes_hex': data[index*RECORD_SIZE:(index+1)*RECORD_SIZE].hex(),
        'sha256': hashlib.sha256(data[index*RECORD_SIZE:(index+1)*RECORD_SIZE]).hexdigest(),
        'raw_fields': {'byte_01': data[index*RECORD_SIZE+1],
                       'byte_02': data[index*RECORD_SIZE+2],
                       'word_0a': struct.unpack_from('>H',data,index*RECORD_SIZE+10)[0],
                       'word_0c': struct.unpack_from('>H',data,index*RECORD_SIZE+12)[0],
                       'word_0e': struct.unpack_from('>H',data,index*RECORD_SIZE+14)[0]}}
        for index in range(RECORD_COUNT)]


def extract(program):
    if len(program) < max(END,*(address+len(code) for address,code in EVIDENCE.items())):
        raise ValueError('Truncated game records or instruction evidence')
    for address,code in EVIDENCE.items():
        if bytes(program[address:address+len(code)]) != code:
            raise ValueError('Game record instruction evidence changed at '+hex(address))
    data=bytes(program[BASE:END]);validate_payload(data)
    return data


def pack_payload(data):
    validate_payload(data)
    return struct.pack('<4s7I',b'MS5D',1,1,BASE,BASE,len(data),zlib.crc32(data),0)+data


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program')
    data=extract(program);records=validate_payload(data);packed=pack_payload(data)
    assert packed[32:]==data and zlib.crc32(packed[32:])==struct.unpack_from('<I',packed,24)[0]
    folder=root/'extracted/runtime';folder.mkdir(parents=True,exist_ok=True)
    (folder/'game_records.ms5d').write_bytes(packed)
    (folder/'game_records.manifest.json').write_text(json.dumps({
        'schema_version':1,'id':'game-records:0004cf64','format':'MS5D','version':1,'kind':1,
        'file':'game_records.ms5d','source':source,'source_cpu_address':BASE,
        'source_rom_offset':BASE,'end_cpu_address_exclusive':END,
        'record_count':RECORD_COUNT,'record_size':RECORD_SIZE,'payload_size':len(data),'size':len(packed),
        'payload_sha256':hashlib.sha256(data).hexdigest(),'sha256':hashlib.sha256(packed).hexdigest(),
        'records':records,'instruction_evidence':[{'cpu_address':address,'rom_offset':address,
            'end_cpu_address_exclusive':address+len(code),'sha256':hashlib.sha256(code).hexdigest()}
            for address,code in EVIDENCE.items()],
        'lookup':'D1.word unsigned<20; base4cf64 + (D1 & ff)*16; otherwise TRAP #15',
        'consumed_record_byte_ranges':[[1,2],[2,3],[10,12],[12,14],[14,16]],
        'mapping':'Fixed ROM; CPU addresses equal canonical decrypted file offsets.',
        'scope':'Twenty complete16-byte records; all unconsumed bytes preserved. Raw field offsets '
            'are named without gameplay interpretation. Extraction does not establish natural callsite '
            'reachability, whole startup behavior or native trap handling.'},indent=2)+'\n')
    print('Game records:',len(records),'records;',len(packed),'bytes;',hashlib.sha256(packed).hexdigest())


if __name__=='__main__':main()
