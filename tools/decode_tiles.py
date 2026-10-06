"""Decode verified Metal Slug 5 C/S graphics to indexed tile pixels.

Sprite bitplane ordering and fixed layer nibble ordering follow pinned MAME
src/mame/snk/neogeo_spr.cpp. Copyright Bryan McPhail, Ernesto Corvi,
Andrew Prime, Zsolt Vasvari; BSD-3-Clause, see licenses/mame-sprites.txt.
Indices preserve the graphics data only: palette assignment remains unresolved.
"""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SPRITE_SOURCE_SIZE = 0x4000000
FIXED_SOURCE_SIZE = 0x20000

# Pack eight pixels into eight separate bytes. ORing four entries combines the
# four planes without per-pixel loops during the complete 64 MiB conversion.
PLANE_PACKED = tuple(tuple(sum(((value >> x) & 1) << (8 * x + plane)
                              for x in range(8))
                           for value in range(256))
                     for plane in range(4))


def decode_sprite_tile(tile):
    """Convert one 128-byte planar tile to 16x16 row-major index bytes."""
    if len(tile) != 128:
        raise ValueError('Sprite tile must contain exactly 128 bytes')
    pixels = bytearray(256)
    plane0, plane1, plane2, plane3 = PLANE_PACKED
    for y in range(16):
        for half in range(2):
            # The upper 64 source bytes describe the left eight pixels.
            source = y * 4 + (64 if half == 0 else 0)
            packed = (plane0[tile[source]] | plane1[tile[source + 2]] |
                      plane2[tile[source + 1]] | plane3[tile[source + 3]])
            offset = y * 16 + half * 8
            pixels[offset:offset + 8] = packed.to_bytes(8, 'little')
    return bytes(pixels)


def decode_fixed_tile(tile):
    """Convert one 32-byte fixed tile to 8x8 row-major index bytes."""
    if len(tile) != 32:
        raise ValueError('Fixed tile must contain exactly 32 bytes')
    pixels = bytearray(64)
    for y in range(8):
        for pair, column in enumerate((0x10, 0x18, 0x00, 0x08)):
            value = tile[column + y]
            pixels[y * 8 + pair * 2] = value & 15
            pixels[y * 8 + pair * 2 + 1] = value >> 4
    return bytes(pixels)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def extracted_path(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to((ROOT / 'extracted').resolve()) or not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError('Tile inputs and outputs must remain inside project extracted/')
    return resolved


def verified_sources(media_directory):
    """Read both source regions and check complete sizes and manifest hashes."""
    media_directory = extracted_path(media_directory)
    manifest = json.loads((media_directory / 'manifest.json').read_text())
    if manifest.get('schema_version') != 1 or manifest.get('set') != 'mslug5':
        raise ValueError('Unsupported media manifest')
    outputs = manifest.get('outputs', [])
    sources = []
    for filename, expected_size in (('sprites.decrypted.bin', SPRITE_SOURCE_SIZE),
                                    ('fixed.decrypted.bin', FIXED_SOURCE_SIZE)):
        entries = [entry for entry in outputs if entry.get('file') == filename]
        if len(entries) != 1:
            raise ValueError('Missing or duplicate media entry: ' + filename)
        entry = entries[0]
        source_path = extracted_path(media_directory / filename)
        data = source_path.read_bytes()
        digest = sha256(data)
        if entry.get('size') != expected_size or len(data) != expected_size:
            raise ValueError('Incorrect media size: ' + filename)
        if entry.get('sha256') != digest:
            raise ValueError('Media hash mismatch: ' + filename)
        sources.append((source_path, data, digest))
    return sources


def write_tiles(destination, source, decoder, bytes_per_tile):
    """Stream a complete region to an atomic output and return its hash."""
    digest = hashlib.sha256()
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=destination.name + '.',
                                         suffix='.tmp', delete=False) as output:
            temporary_path = Path(output.name)
            for start in range(0, len(source), bytes_per_tile * 1024):
                end = min(start + bytes_per_tile * 1024, len(source))
                block = b''.join(decoder(source[offset:offset + bytes_per_tile])
                                 for offset in range(start, end, bytes_per_tile))
                output.write(block)
                digest.update(block)
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return digest.hexdigest()


def decode_tiles(media_directory=None, output_directory=None):
    """Verify complete sources, decode every tile, and save resource manifest."""
    media_directory = media_directory or ROOT / 'extracted/media'
    output_directory = extracted_path(output_directory or ROOT / 'extracted/tiles')
    sources = verified_sources(media_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    resources = []
    specifications = (('mslug5.sprite_tiles', 'sprites.idx8', 16, 128, decode_sprite_tile),
                      ('mslug5.fixed_tiles', 'fixed.idx8', 8, 32, decode_fixed_tile))
    for specification, source in zip(specifications, sources):
        identifier, filename, width, bytes_per_tile, decoder = specification
        source_path, data, source_hash = source
        digest = write_tiles(output_directory / filename, data, decoder, bytes_per_tile)
        resources.append({'id': identifier, 'file': filename, 'width': width, 'height': width,
                          'count': len(data) // bytes_per_tile, 'pixel_format': 'indexed8',
                          'layout': 'tile-row-column', 'transparent_index': 0,
                          'palette_status': 'unresolved', 'sha256': digest,
                          'source': {'file': source_path.relative_to(ROOT.resolve()).as_posix(),
                                     'sha256': source_hash, 'bytes_per_tile': bytes_per_tile,
                                     'address_space': 'decrypted-region-offset'}})
    manifest = {'schema_version': 1, 'format': 'mslug5-indexed-tiles', 'resources': resources}
    with tempfile.NamedTemporaryFile(mode='w', dir=output_directory, prefix='manifest.',
                                     suffix='.tmp', delete=False) as output:
        manifest_path = Path(output.name)
        output.write(json.dumps(manifest, indent=2) + '\n')
    try:
        manifest_path.replace(output_directory / 'manifest.json')
    finally:
        manifest_path.unlink(missing_ok=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media', type=Path, default=ROOT / 'extracted/media')
    parser.add_argument('--output', type=Path, default=ROOT / 'extracted/tiles')
    arguments = parser.parse_args()
    manifest = decode_tiles(arguments.media, arguments.output)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
