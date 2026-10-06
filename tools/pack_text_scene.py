"""Package the original warning stream and proven palette binding for C++."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from pack_palettes import extract


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    start, end = 0xcb80, 0xccd5
    script = program[start:end]
    if hashlib.sha256(script).hexdigest() != 'c63119be00c1f26c13bcfc7c1c1def3eadcee76f62f86e0810d1a4496e2f18c4':
        raise ValueError('Warning text stream changed')
    _, bindings = extract(program)
    bindings = [b for b in bindings if b['table_rom_offset'] == 0xcb78]
    if len(bindings) != 1 or bindings[0]['slot'] != 0 or bindings[0]['source_id'] != 0x897:
        raise ValueError('Warning palette binding changed')
    payload = b''.join(struct.pack('<II', b['slot'], b['source_id']) for b in bindings)+script
    data = struct.pack('<4s7I', b'MS5X', 1, 1, start, len(bindings), len(payload), zlib.crc32(payload), 0)+payload
    directory = root/'extracted/runtime'
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'warning.ms5x').write_bytes(data)
    manifest = {'schema_version':1,'id':'mslug5.fixed_text.00cb80','format':'MS5X','version':1,
                'file':'warning.ms5x','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                'source':source,'source_rom_offset':start,'source_end_exclusive':end,
                'original_entry':0xcb64,'bindings':bindings,
                'kind':'original_fixed_text_stream','supported_execution':'ASCII/font61',
                'initial_state':'demo uses zero VRAM/background, normal screen, cartridge fixed tiles; not measured boot state'}
    (directory/'warning.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Packed original text resource:',len(data),'bytes')


if __name__ == '__main__':
    main()
