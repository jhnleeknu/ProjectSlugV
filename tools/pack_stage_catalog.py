"""Preserve the 19 fixed-ROM stage lists and their pointer index as MS5D."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program

INDEX = 0x474f4
COUNT = 19


def decode_group(program, address):
    if address & 1 or not 0 <= address <= 0x100000-4:
        raise ValueError('Stage list must begin at an even fixed-ROM address')
    cursor=address+2
    records=[]
    while cursor+2 <= 0x100000:
        length=struct.unpack_from('>h',program,cursor)[0]
        cursor+=2
        if length==0:
            return {'source_cpu_address':address,'header':struct.unpack_from('>H',program,address)[0],
                    'end_cpu_address':cursor,'records':records}
        if length<20 or length & 1 or cursor+length>0x100000:
            raise ValueError('Unexpected stage record length')
        payload=program[cursor:cursor+length]
        if 0 not in payload[18:]:
            raise ValueError('Stage name has no terminator within its record')
        records.append({'id':'stage-record:%08x'%cursor,'source_cpu_address':cursor,
                        'source_rom_offset':cursor,'size':length,'opaque_header_hex':payload[:18].hex(),
                        'name_cpu_address':cursor+18,'name_and_padding_hex':payload[18:].hex()})
        if len(records)>65535:
            raise ValueError('Stage count exceeds word range')
        cursor+=length
    raise ValueError('Stage list lacks a terminator')


def wrap(data,address):
    return struct.pack('<4s7I',b'MS5D',1,1,address,address,len(data),zlib.crc32(data),0)+data


def pack_null_name_prefix(program, source, folder):
    # The null name pointer reaches the original reset-vector bytes. Keep the
    # initial zero as well as the bytes read before the following terminator.
    raw = program[0:4]
    if raw != bytes.fromhex('0010f300'):
        raise ValueError('Original fixed-ROM vector prefix changed')
    packed = wrap(raw, 0)
    name = 'stage_null_name.ms5d'
    (folder / name).write_bytes(packed)
    (folder / 'stage_null_name.manifest.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'stage-null-name:00000000',
        'format': 'MS5D', 'version': 1, 'file': name, 'source': source,
        'source_cpu_address': 0, 'source_rom_offset': 0, 'source_length': 4,
        'size': len(packed), 'sha256': hashlib.sha256(packed).hexdigest(),
        'references': {'name_lookup_cpu_address': 0x4827e,
                       'stage_callback_cpu_address': 0x9802},
        'scope': 'Raw vector prefix consumed through a null name pointer for '
                 'empty stage groups 9 through 15. The formatter consumes the '
                 'initial byte 00 and bytes 10 f3 before the following 00 '
                 'terminator. This is not an actual intended stage name; '
                 'the original bytes are preserved without substitution.'
    }, indent=2) + '\n')


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    folder=root/'extracted/runtime/stages'
    folder.mkdir(parents=True,exist_ok=True)
    index=wrap(program[INDEX:INDEX+COUNT*4],INDEX)
    (folder/'stage_index.ms5d').write_bytes(index)
    groups=[]
    for number,address in enumerate(struct.unpack_from('>19I',program,INDEX)):
        group=decode_group(program,address)
        data=wrap(program[address:group['end_cpu_address']],address)
        name='stage_group_%02d.ms5d'%number
        (folder/name).write_bytes(data)
        group.update({'id':'stage-group:%02d'%number,'index':number,'file':name,
                      'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        groups.append(group)
    (folder/'manifest.json').write_text(json.dumps({
        'schema_version':1,'id':'stage-catalog:000474f4','format':'MS5D','version':1,
        'source':source,'index_file':'stage_index.ms5d','index_cpu_address':INDEX,
        'index_sha256':hashlib.sha256(index).hexdigest(),'groups':groups,
        'scope':'All19 lists referenced by474e2, including empty groups and test-labelled records. '
                'Opaque18-byte headers and name/control/padding bytes are preserved. '
                'Referenced gameplay scripts/maps and natural reachability are not yet decoded.'
    },indent=2)+'\n')
    pack_null_name_prefix(program, source, folder)
    print('Packed stage catalog:',len(groups),'groups;',sum(len(g['records']) for g in groups),'records')


if __name__=='__main__':
    main()
