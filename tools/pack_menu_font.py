"""Preserve original 6b/68 glyph lookup words for C++ menu rendering."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    data=program[0xe80c8:0xe82c8]
    packed=struct.pack('<4s7I',b'MS5D',1,1,0xe80c8,0xe80c8,len(data),zlib.crc32(data),0)+data
    folder=root/'extracted/runtime'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'menu_font_6b.ms5d').write_bytes(packed)
    (folder/'menu_font_6b.manifest.json').write_text(json.dumps({
        'schema_version':1,'id':'font:6b','format':'MS5D','version':1,
        'file':'menu_font_6b.ms5d','source':source,'source_cpu_address':0xe80c8,
        'source_rom_offset':0xe80c8,'size':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),
        'entries':256,'entry_encoding':'BE16 fixed tile word; palette bits ORed by renderer',
        'reference_cpu_address':0xe869c,'scope':'One lookup font table. Glyph pixels remain in MS5T fixed tiles.'
    },indent=2)+'\n')
    print('Packed font6b:256 entries;',len(packed),'bytes')
    data=program[0xe80c8:0xe84c8]
    if len(data)!=1024:
        raise ValueError('Menu font tables are truncated')
    packed=struct.pack('<4s7I',b'MS5D',1,1,0xe80c8,0xe80c8,len(data),zlib.crc32(data),0)+data
    (folder/'menu_fonts.ms5d').write_bytes(packed)
    (folder/'menu_fonts.manifest.json').write_text(json.dumps({
        'schema_version':1,'id':'menu-fonts:000e80c8','format':'MS5D','version':1,
        'file':'menu_fonts.ms5d','source':source,'source_cpu_address':0xe80c8,
        'source_rom_offset':0xe80c8,'size':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),
        'entry_encoding':'BE16 fixed tile word; palette bits ORed by renderer',
        'tables':[
            {'id':'font:6b','source_cpu_address':0xe80c8,'source_rom_offset':0xe80c8,
             'payload_offset':0,'entries':256,'reference_cpu_address':0xe869c},
            {'id':'font:68','source_cpu_address':0xe82c8,'source_rom_offset':0xe82c8,
             'payload_offset':512,'entries':256,'reference_cpu_address':0xe868c}
        ],
        'scope':'Two lookup font tables. Glyph pixels remain in MS5T fixed tiles.'
    },indent=2)+'\n')
    print('Packed menu fonts:2 tables,512 entries;',len(packed),'bytes')


if __name__=='__main__':
    main()
