"""Package CPU-verified counted rectangles as MS5C v1 kind 2 runtime resources."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from verify_sprite_blocks import resolve_blocks


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    destination = root/'extracted/runtime'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for identifier in (0x2382a, 0x2402a, 0x2482a, 0x122, 0x29802, 0x70002):
        bank, offset, data, blocks = resolve_blocks(program, identifier)
        packed = struct.pack('<4s7I', b'MS5C', 1, 2, identifier, offset, len(data), zlib.crc32(data), 0)+data
        filename = 'composition_%06x.ms5c'%identifier
        (destination/filename).write_bytes(packed)
        records.append({'packed_id':identifier, 'file':filename, 'source_rom_offset':offset,
                        'source_cpu_address':offset-bank+0x200000, 'bank_base':bank,
                        'sha256':hashlib.sha256(packed).hexdigest(), 'payload_size':len(data), 'opaque_header_byte':data[1],
                        'blocks':[{'dx_word':int.from_bytes(b[2:4],'big'), 'dy_word':int.from_bytes(b[4:6],'big'),
                                   'width':b[6], 'height':b[7]} for b in blocks],
                        'use_status':'unclassified', 'palette_binding':'caller_context_unknown'})
    manifest = {'schema_version':1, 'format':'MS5C', 'version':1, 'kind':2, 'source':source,
                'catalog_status':'incomplete_sparse',
                'scope':'Six resources verified by direct original consumer calls; natural gameplay reachability and palette bindings are not established.',
                'records':records}
    (destination/'composition_blocks.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Packed',len(records),'counted rectangle runtime resources')


if __name__ == '__main__':
    main()
