"""Build MS5T v1 C++ runtime resources from verified indexed tile catalogs."""
import hashlib
import json
from pathlib import Path
import struct
import zlib


def pack_payload(data, kind, width, height, count):
    expected = {1: (16, 16, 524288), 2: (8, 8, 4096)}
    if kind not in expected or (width, height, count) != expected[kind]:
        raise ValueError('Invalid MS5T v1 catalog geometry')
    if len(data) != width * height * count or any(value > 15 for value in data):
        raise ValueError('Invalid indexed tile payload')
    header = struct.pack('<4s7I', b'MS5T', 1, kind, width, height, count,
                         len(data), zlib.crc32(data))
    return header + data


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'extracted/tiles'
    manifest = json.loads((source / 'manifest.json').read_text())
    if manifest.get('schema_version') != 1 or manifest.get('format') != 'mslug5-indexed-tiles':
        raise ValueError('Unsupported intermediate tile manifest')
    identifiers = [item['id'] for item in manifest['resources']]
    if sorted(identifiers) != ['mslug5.fixed_tiles', 'mslug5.sprite_tiles']:
        raise ValueError('Expected both tile catalogs exactly once')
    destination = root / 'extracted/runtime'
    destination.mkdir(parents=True, exist_ok=True)
    output = {'schema_version': 1, 'format': 'mslug5-runtime-resources', 'resources': []}
    for item in manifest['resources']:
        kind = {'mslug5.sprite_tiles': 1, 'mslug5.fixed_tiles': 2}[item['id']]
        raw = (source / item['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Decoded tile hash mismatch')
        if (item['pixel_format'] != 'indexed8' or item['layout'] != 'tile-row-column'
                or item['transparent_index'] != 0):
            raise ValueError('Unsupported intermediate pixel layout')
        packed = pack_payload(raw, kind, item['width'], item['height'], item['count'])
        name = 'sprites.ms5t' if kind == 1 else 'fixed.ms5t'
        (destination / name).write_bytes(packed)
        output['resources'].append({'id': item['id'], 'file': name,
            'format': 'MS5T', 'version': 1, 'size': len(packed),
            'sha256': hashlib.sha256(packed).hexdigest(), 'palette_status': 'unresolved',
            'source': {'file': 'extracted/tiles/' + item['file'], 'sha256': item['sha256']}})
        print('Runtime resource:', name, len(packed), 'bytes')
    (destination / 'manifest.json').write_text(json.dumps(output, indent=2)+'\n')


if __name__ == '__main__':
    main()
