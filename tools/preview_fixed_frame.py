"""Diagnostic PNG only: convert verified hardware-word frame with MAME lookup."""
import hashlib
from pathlib import Path
import struct
import zlib


def chunk(name, payload):
    return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload))


def main():
    root = Path(__file__).resolve().parents[1]
    lookup = (root/'artifacts/color_reference/channel_lookup.bin').read_bytes()
    if hashlib.sha256(lookup).hexdigest() != '1a35fd99068aba9ed9e05a97335f63ded453d32c8ddbb567c64a0d45da630ed4':
        raise ValueError('Unverified channel lookup')
    words = (root/'artifacts/fixed_renderer/warning.words.be.bin').read_bytes()
    if len(words) != 320*256*2:
        raise ValueError('Frame length mismatch')
    rgb = bytearray()
    for (word,) in struct.iter_unpack('>H', words):
        dark = word >> 15
        red = ((word >> 14)&1)|((word>>7)&30)
        green = ((word>>13)&1)|((word>>3)&30)
        blue = ((word>>12)&1)|((word<<1)&30)
        rgb.extend((lookup[red*4+dark],lookup[green*4+dark],lookup[blue*4+dark]))
    rows = b''.join(b'\0'+rgb[y*960:(y+1)*960] for y in range(256))
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,256,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
    path = root/'artifacts/previews/warning-fixed.png'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(png)
    print(path)


if __name__ == '__main__':
    main()
