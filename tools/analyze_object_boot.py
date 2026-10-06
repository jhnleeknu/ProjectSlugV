"""Extract the reviewed fixed-ROM object initialization table and evidence.

Names are analyst labels. No unknown fields are assigned gameplay meanings.
This report is analysis metadata, not the runtime object resource format.
"""
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program, write_disassembly


def main():
    root = Path(__file__).resolve().parents[1]
    data, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('This analysis only applies to the reviewed mslug5 program revision')
    records = []
    for offset in range(0x268a, 0x270a, 16):
        address, callback, a, b, c, d = struct.unpack_from('>II4H', data, offset)
        records.append({'table_rom_offset': offset, 'ram_address': address,
                        'callback_cpu_address': callback,
                        'words_by_object_offset': {'0x76': a, '0x78': b, '0x7a': c, '0x7c': d}})
    if data[0x270a:0x270e] != bytes(4):
        raise ValueError('Expected zero address sentinel')
    ranges = [('header_callbacks',0x122,0x18), ('entry_dispatch',0x852,0x1da),
              ('object_reset',0x270e,0x82), ('object_init',0x2790,0xee),
              ('object_dispatch',0x2aac,0x1c), ('first_callback',0xe4a,0xce),
              ('second_callback',0xc52a,0x44), ('ram_code_decode',0x1022,0x74)]
    for name, start, length in ranges:
        write_disassembly(start, length, start, 'artifacts/disassembly/'+name+'.json')
    report = {'schema_version':1, 'program_sha256':source['sha256'],
              'method':'Manual instruction interpretation, fixed ROM CPU mapping; runtime unverified',
              'initial_table':records, 'sentinel_rom_offset':0x270a,
              'dynamic_slots':{'base':0x100f5c,'stride':0xc4,'count':80,
                               'end_exclusive':0x104c9c,'default_callback':0x270e,
                               'evidence_rom_range':[0x2800,0x2848]},
              'dispatch':{'rom_start':0x2aac,'first_node':0x100820,
                          'callback_pointer_offset':0,'next_pointer_offset':8,
                          'a5_base':0x108000,'saved_a7_address':0x104ca4,
                          'next_pointer_read':'after callback returns'},
              'unresolved':['Full reset helper behavior','Meaning of offset 0x10 and 0x76..0x7c',
                            'Runtime list mutations and callback nonlocal returns',
                            'Mapping of nodes to player/enemy/background',
                            'Palette and animation resource links']}
    out=root/'artifacts/analysis/object_boot.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print('Recorded',len(records),'initial nodes and 80-slot pool; execution remains unverified.')


if __name__ == '__main__':
    main()
