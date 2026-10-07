"""Preserve byte-indexed player-record word lookup window without resizing records."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
try:
    from .disassemble_program import load_verified_program, disassemble_range
    from .pack_game_records import PAYLOAD_SHA256 as RECORD_PREFIX_SHA256
except ImportError:
    from disassemble_program import load_verified_program, disassemble_range
    from pack_game_records import PAYLOAD_SHA256 as RECORD_PREFIX_SHA256
BASE, END = 0x4cf64, 0x4df60
PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
PAYLOAD_SHA256 = 'a6ff769be292399534dc547ca3c43af55f33f5c047758ab44487d23cf0f6f899'
EVIDENCE_ADDRESS = 0x4d806
EVIDENCE = bytes.fromhex('3800024400ffc8fc001049faf752d8c4382c000a')
PREFIX_SIZE = 320


def verify_program(program):
    if len(program) != 8*1024*1024 or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Unsupported canonical program size or SHA256')


def validate_payload(data):
    if len(data) != END-BASE: raise ValueError('Player lookup requires complete4092-byte addressable window')
    if hashlib.sha256(data[:PREFIX_SIZE]).hexdigest() != RECORD_PREFIX_SHA256:
        raise ValueError('Existing twenty-record prefix changed')
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256: raise ValueError('Player lookup pinned payload changed')


def extract(program):
    if len(program) < END: raise ValueError('Truncated player record lookup window')
    if bytes(program[EVIDENCE_ADDRESS:EVIDENCE_ADDRESS+len(EVIDENCE)]) != EVIDENCE:
        raise ValueError('Player record lookup instruction evidence changed')
    data = bytes(program[BASE:END]); validate_payload(data); return data


def lookup_word(data,index):
    validate_payload(data)
    if not isinstance(index,int) or isinstance(index,bool) or not 0 <= index <= 255:
        raise ValueError('Lookup index must be unsigned byte')
    offset = index*16+10
    return BASE+offset,struct.unpack_from('>H',data,offset)[0]


def validate_container(raw):
    if len(raw) < 32: raise ValueError('Truncated MS5D header')
    magic,version,kind,cpu,rom,size,crc,reserved = struct.unpack_from('<4s7I',raw)
    if (magic,version,kind,cpu,rom,size,reserved) != (b'MS5D',1,1,BASE,BASE,END-BASE,0):
        raise ValueError('Invalid player lookup MS5D header')
    if len(raw) != 32+size: raise ValueError('Incorrect MS5D file length')
    payload = bytes(raw[32:])
    if zlib.crc32(payload) != crc: raise ValueError('MS5D CRC mismatch')
    validate_payload(payload); return payload


def pack_payload(data):
    validate_payload(data)
    raw = struct.pack('<4s7I',b'MS5D',1,1,BASE,BASE,len(data),zlib.crc32(data),0)+data
    assert validate_container(raw) == data
    return raw


def main():
    root = Path(__file__).resolve().parents[1]; program,source = load_verified_program(root)
    verify_program(program)
    if source['sha256'] != PROGRAM_SHA256: raise ValueError('Unsupported program manifest')
    data = extract(program); raw = pack_payload(data)
    rows = disassemble_range(program,EVIDENCE_ADDRESS,len(EVIDENCE),EVIDENCE_ADDRESS)
    assert all(row['classification']=='candidate_instruction' for row in rows)
    prefix_resource = root/'extracted/runtime/game_records.ms5d'
    prefix_raw = prefix_resource.read_bytes()
    if len(prefix_raw) != 352 or prefix_raw[32:] != data[:PREFIX_SIZE]:
        raise ValueError('Existing game_records resource prefix mismatch')
    folder = root/'extracted/runtime'; folder.mkdir(parents=True,exist_ok=True)
    (folder/'player_record_lookup.ms5d').write_bytes(raw)
    (folder/'player_record_lookup.manifest.json').write_text(json.dumps(dict(
        schema_version=1,id='player-record-lookup:0004cf64',format='MS5D',version=1,kind=1,
        file='player_record_lookup.ms5d',source=source,source_cpu_address=BASE,source_rom_offset=BASE,
        end_cpu_address_exclusive=END,payload_size=len(data),size=len(raw),payload_sha256=hashlib.sha256(data).hexdigest(),
        sha256=hashlib.sha256(raw).hexdigest(),lookup_expression='BE16 at4cf64 + unsignedbyteindex*16 +0a',
        native_active_index_range=[1,255],native_index_zero='TRAP path outside normal lookup; rawindex0 bytes stillpreserved',
        last_read=dict(index=255,cpu_address=END-2,rom_offset=END-2,end_exclusive=END),
        existing_twenty_record_prefix=dict(file='game_records.ms5d',size=PREFIX_SIZE,sha256=RECORD_PREFIX_SHA256,
            cpu_address=BASE,end_exclusive=BASE+PREFIX_SIZE,actual_resource_prefix_equal=True),
        instruction_evidence=rows,
        mapping='Fixed first1MiB CPU addresses equal canonical decrypted ROM offsets.',
        scope='4092-byte raw addressable lookupwindow, not enlarged logicalrecordtable. Existing20x16 records unchanged. '
            'Laterbytes include possible code/unclassifieddata; preserveallbytes. Nativecallback/trapbehavior, naturalindexes '
            'and wholeplayercapture/gameplay remain separate.'),indent=2)+'\n')
    print('Player record lookup:',len(data),'payloadbytes;',len(raw),'containerbytes;',hashlib.sha256(raw).hexdigest())


if __name__ == '__main__': main()
