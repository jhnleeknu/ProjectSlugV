"""Package reviewed immutable ROM windows for animation table operations."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    directory=root/'extracted/runtime';directory.mkdir(parents=True,exist_ok=True)
    records=[]
    for address,size,role,scope in ((0x4a76c,290,'field_selectors','Candidate table extent before separately referenced code; natural usage of all entries unproven.'),
                                   (0x6431a,1024,'callback_1e_window','Complete byte-index read window; not a claim that all bytes form one logical table.')):
        data=program[address:address+size]
        packed=struct.pack('<4s7I',b'MS5D',1,1,address,address,len(data),zlib.crc32(data),0)+data
        name='data_%06x.ms5d'%address;(directory/name).write_bytes(packed)
        records.append({'file':name,'source_cpu_address':address,'source_rom_offset':address,'size':size,'role':role,'scope':scope,
                        'sha256':hashlib.sha256(packed).hexdigest()})
    (directory/'animation_data.manifest.json').write_text(json.dumps({'schema_version':1,'format':'MS5D','source':source,'records':records},indent=2)+'\n')
    print('Packed',len(records),'fixed-ROM data windows')


if __name__=='__main__':main()
