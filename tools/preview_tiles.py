"""Diagnostic tile contact sheet; grayscale is NOT the original palette."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['sprites', 'fixed'], default='sprites')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int, default=256)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = root / 'extracted/tiles'
    manifest = json.loads((directory / 'manifest.json').read_text())
    filename = args.kind + '.idx8'
    item = next(x for x in manifest['resources'] if x['file'] == filename)
    data = (directory / filename).read_bytes()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Tile artifact hash mismatch')
    if args.start < 0 or not 1 <= args.count <= 4096 or args.start+args.count > item['count']:
        raise ValueError('Invalid tile range')
    width, height = item['width'], item['height']
    columns, scale, gap = 16, 2, 2
    image_width = columns*(width*scale+gap)+gap
    image_height = ((args.count+columns-1)//columns)*(height*scale+gap)+gap
    rows = [bytearray(bytes((32,32,32))*image_width) for _ in range(image_height)]
    for index in range(args.count):
        tile_id = args.start+index
        left = gap + (index % columns)*(width*scale+gap)
        top = gap + (index // columns)*(height*scale+gap)
        for y in range(height):
            for x in range(width):
                pen = data[tile_id*width*height+y*width+x]
                color = bytes((96,0,96)) if pen == 0 else bytes((pen*17,)*3)
                for dy in range(scale):
                    for dx in range(scale):
                        position = (left+x*scale+dx)*3
                        rows[top+y*scale+dy][position:position+3] = color
    payload = b''.join(b'\0'+row for row in rows)
    png = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', struct.pack('>IIBBBBB',image_width,image_height,8,2,0,0,0))
    png += png_chunk(b'tEXt',b'Description\0Diagnostic grayscale; index zero purple; original palette unresolved')
    png += png_chunk(b'IDAT',zlib.compress(payload)) + png_chunk(b'IEND',b'')
    output = root / 'artifacts/previews'
    output.mkdir(parents=True,exist_ok=True)
    path = output / ('%s-%06x.png' % (args.kind,args.start))
    path.write_bytes(png)
    path.with_suffix('.json').write_text(json.dumps({'resource_id':item['id'],
        'start_tile':args.start,'count':args.count,'columns':columns,'scale':scale,
        'palette':'diagnostic grayscale, zero purple; not original colors'},indent=2)+'\n')
    print(path)


if __name__ == '__main__':
    main()
