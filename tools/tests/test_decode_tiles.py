"""Synthetic tile/address patterns; no game data is needed."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import decode_tiles


class DecodeTileTests(unittest.TestCase):
    def test_sprite_each_pixel_and_plane(self):
        # Byte offsets are derived explicitly from the source plane order,
        # independent of the decoder's packed lookup optimization.
        for y in range(16):
            for x in range(16):
                for plane, plane_byte in enumerate((0, 2, 1, 3)):
                    with self.subTest(x=x, y=y, plane=plane):
                        tile = bytearray(128)
                        tile[y * 4 + (64 if x < 8 else 0) + plane_byte] = 1 << (x % 8)
                        expected = bytearray(256)
                        expected[y * 16 + x] = 1 << plane
                        self.assertEqual(decode_tiles.decode_sprite_tile(tile), bytes(expected))

    def test_sprite_planes_combine_without_reversing_pixels(self):
        tile = bytearray(128)
        tile[64:68] = bytes((0x55, 0x0f, 0x33, 0xff))
        self.assertEqual(decode_tiles.decode_sprite_tile(tile)[:16],
                         bytes((15, 14, 13, 12, 11, 10, 9, 8)) + bytes(8))
        self.assertEqual(decode_tiles.decode_sprite_tile(bytes([255]) * 128), bytes([15]) * 256)

    def test_fixed_every_row_pair_and_nibble(self):
        for y in range(8):
            for pair, column in enumerate((16, 24, 0, 8)):
                for value in range(256):
                    with self.subTest(y=y, pair=pair, value=value):
                        tile = bytearray(32)
                        tile[column + y] = value
                        expected = bytearray(64)
                        expected[y * 8 + pair * 2] = value & 15
                        expected[y * 8 + pair * 2 + 1] = value >> 4
                        self.assertEqual(decode_tiles.decode_fixed_tile(tile), bytes(expected))

    def test_invalid_tile_lengths(self):
        for function, size in ((decode_tiles.decode_sprite_tile, 128),
                               (decode_tiles.decode_fixed_tile, 32)):
            for length in (0, size - 1, size + 1, size * 2):
                with self.subTest(size=size, length=length), self.assertRaises(ValueError):
                    function(bytes(length))

    def test_stream_preserves_tile_order_across_chunk_boundary(self):
        source = bytes(128 * 1024) + bytes([255]) * 128
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'sprites.idx8'
            digest = decode_tiles.write_tiles(destination, source, decode_tiles.decode_sprite_tile, 128)
            expected = bytes(256 * 1024) + bytes([15]) * 256
            self.assertEqual(destination.read_bytes(), expected)
            self.assertEqual(digest, hashlib.sha256(expected).hexdigest())
            self.assertEqual(list(Path(temporary).iterdir()), [destination])

    def test_manifest_and_source_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'extracted/media'
            media.mkdir(parents=True)
            records = []
            for filename, data in (('sprites.decrypted.bin', bytes([255]) * 128),
                                   ('fixed.decrypted.bin', bytes([0x21]) * 32)):
                (media / filename).write_bytes(data)
                records.append({'file': filename, 'size': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()})
            (media / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'set': 'mslug5',
                                                          'outputs': records}))
            with mock.patch.object(decode_tiles, 'ROOT', root), \
                    mock.patch.object(decode_tiles, 'SPRITE_SOURCE_SIZE', 128), \
                    mock.patch.object(decode_tiles, 'FIXED_SOURCE_SIZE', 32):
                manifest = decode_tiles.decode_tiles()
                self.assertEqual(manifest['format'], 'mslug5-indexed-tiles')
                self.assertEqual(manifest['resources'][0]['count'], 1)
                self.assertEqual(manifest['resources'][1]['source']['file'],
                                 'extracted/media/fixed.decrypted.bin')
                self.assertEqual((root / 'extracted/tiles/fixed.idx8').read_bytes(), bytes((1, 2)) * 32)
                # Validation of either source precedes all output creation.
                (media / 'fixed.decrypted.bin').write_bytes(bytes(32))
                output = root / 'extracted/rejected'
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    decode_tiles.decode_tiles(output_directory=output)
                self.assertFalse(output.exists())
                (media / 'fixed.decrypted.bin').write_bytes(bytes(31))
                with self.assertRaisesRegex(ValueError, 'size'):
                    decode_tiles.decode_tiles(output_directory=output)

    def test_output_cannot_escape_extracted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'project'
            root.mkdir()
            outside = Path(temporary) / 'outside'
            outside.mkdir()
            with mock.patch.object(decode_tiles, 'ROOT', root):
                with self.assertRaises(ValueError):
                    decode_tiles.decode_tiles(output_directory=outside)
                (root / 'extracted').symlink_to(outside, target_is_directory=True)
                with self.assertRaises(ValueError):
                    decode_tiles.decode_tiles(output_directory=root / 'extracted/tiles')


if __name__ == '__main__':
    unittest.main()
