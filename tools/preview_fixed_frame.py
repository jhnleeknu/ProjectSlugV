"""Diagnostic PNG only: convert verified hardware-word frame with MAME lookup."""
from pathlib import Path
import struct
import subprocess
import zlib


def chunk(name, payload):
    return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload))


def main():
    root = Path(__file__).resolve().parents[1]
    words_path = root/'artifacts/fixed_renderer/warning.words.be.bin'
    if words_path.stat().st_size != 320*256*2:
        raise ValueError('Frame length mismatch')
    rgb_path = root/'artifacts/fixed_renderer/warning.rgb'
    subprocess.run([str(root/'build/convert_color_words'), str(words_path), str(rgb_path), 'normal'], check=True)
    rgb = rgb_path.read_bytes()
    if len(rgb) != 320*256*3:
        raise ValueError('RGB frame length mismatch')
    rows = b''.join(b'\0'+rgb[y*960:(y+1)*960] for y in range(256))
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,256,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
    path = root/'artifacts/previews/warning-fixed.png'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(png)
    print(path)


if __name__ == '__main__':
    main()
