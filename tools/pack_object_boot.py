"""Pack reviewed ROM initialization records as a C++ MS5I v1 resource."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program


def main():
    root=Path(__file__).resolve().parents[1]
    program, source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    payload=program[0x268a:0x270a]
    if program[0x270a:0x270e]!=bytes(4):
        raise ValueError('Missing boot table sentinel')
    header=struct.pack('<4s7I',b'MS5I',1,8,16,0x268a,len(payload),zlib.crc32(payload),0)
    packed=header+payload
    destination=root/'extracted/runtime'
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'object_boot.ms5i').write_bytes(packed)
    report={'schema_version':1,'id':'mslug5.object_boot','format':'MS5I','version':1,
            'file':'object_boot.ms5i','size':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),
            'source':{'file':source['path'],'sha256':source['sha256'],
                      'rom_offset':0x268a,'size':128,'address_space':'decrypted-fixed-ROM'},
            'callback_ids':'Original CPU addresses; not native host function pointers'}
    (destination/'object_boot.manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Packed object_boot.ms5i:',len(packed),'bytes')


if __name__=='__main__':
    main()
