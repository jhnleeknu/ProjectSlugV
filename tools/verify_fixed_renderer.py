"""Compare C++ fixed layer words with pinned MAME raw tile addressing."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from extract_media import reference_source
from pack_palettes import extract
from disassemble_program import load_verified_program


def main():
    root = Path(__file__).resolve().parents[1]
    reference_source('neogeo_spr.cpp')  # verify pinned source before using its mapping
    program, source = load_verified_program(root)
    palettes, bindings = extract(program)
    raw = (root/'extracted/media/fixed.decrypted.bin').read_bytes()
    if hashlib.sha256(raw).hexdigest() != '8cbbe34735a51a71fdce50566323a23c4afd41be5a11c94afdfcb23c2f6a7981':
        raise ValueError('Unverified raw fixed tile image')
    writes_path = root/'artifacts/fixed_text/cpp.writes.bin'
    reference_writes = root/'artifacts/fixed_text/m68k.writes.bin'
    writes = writes_path.read_bytes()
    if writes != reference_writes.read_bytes() or hashlib.sha256(writes).hexdigest() != '5b7226162bf069a169c70096001c3dca4c3fffa621752366e2862afa373aa9a1':
        raise ValueError('Unverified warning writes; run verify_fixed_text.py')
    directory = root/'artifacts/fixed_renderer'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory/'warning.words.be.bin'
    subprocess.run([str(root/'build/render_fixed_words'), str(root/'extracted/runtime/fixed.ms5t'),
                    str(writes_path), str(root/'extracted/runtime/palettes.ms5p'), str(output)], check=True)
    vram = [0]*1280
    for address, value in struct.iter_unpack('>HH', writes):
        if not 0x7000 <= address < 0x7500 or value >> 12 != 0:
            raise ValueError('Unexpected warning address or palette')
        vram[address-0x7000] = value
    colors = struct.unpack('>16H', palettes[0x897][1])
    expected = bytearray(320*256*2)
    # Independently walk the raw ROM layout by MAME's pairs, not decoded tiles.
    for y in range(256):
        for column in range(40):
            code = vram[column*32+y//8] & 0xfff
            for pair, offset in enumerate((16, 24, 0, 8)):
                data = raw[code*32+(y&7)+offset]
                for half, pixel in enumerate((data&15, data>>4)):
                    if pixel:
                        at = (y*320+column*8+pair*2+half)*2
                        expected[at:at+2] = struct.pack('>H', colors[pixel])
    actual = output.read_bytes()
    if actual != expected:
        raise ValueError('C++ fixed frame differs from raw-tile reference')
    report = {'source_program_sha256': source['sha256'], 'frame_size': [320,256],
              'format': 'BE hardware palette words', 'all_pixels_equal': True,
              'sha256': hashlib.sha256(actual).hexdigest(), 'source_palette_id': 0x897,
              'scope': 'Unbanked cartridge fixed tiles, zero VRAM/background, word-valued framebuffer; not original complete screen or RGB display.'}
    (directory/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
