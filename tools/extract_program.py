"""Produce a canonical big-endian 68000 image from verified assembled ROMs."""
import hashlib
import json
from pathlib import Path

from assemble_regions import swap_words
from decrypt_pvc import decrypt_program


def main():
    root = Path(__file__).resolve().parents[1]
    region = root / 'extracted/regions/maincpu.encrypted.le.bin'
    source = region.read_bytes()
    assembly = json.loads((region.parent / 'manifest.json').read_text())
    expected = next(x for x in assembly['regions'] if x['name'] == 'maincpu')
    if (expected['file'] != region.name or expected['byte_order'] != 'little-endian-16'
            or len(source) != expected['size']
            or hashlib.sha256(source).hexdigest() != expected['sha256']):
        raise ValueError('Program region does not match its verified assembly manifest')
    decrypted = swap_words(decrypt_program(source))
    directory = root / 'extracted/program'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / 'maincpu.decrypted.be.bin'
    output.write_bytes(decrypted)
    report = {
        'schema_version': 1,
        'input': {'path': str(region.relative_to(root)),
                  'sha256': hashlib.sha256(source).hexdigest(), 'byte_order': 'little'},
        'output': {'path': str(output.relative_to(root)), 'size': len(decrypted),
                   'sha256': hashlib.sha256(decrypted).hexdigest(), 'byte_order': 'big'},
        'algorithm': 'MAME mslug5_decrypt_68k; pinned config/mame_sources.json',
        'source_revision': assembly['reference']['source']['revision'],
        'address_space': 'Decrypted ROM region offsets; not a flat 8 MiB CPU mapping.',
        'first_8_longs_hex': ['%08x' % int.from_bytes(decrypted[i:i+4], 'big')
                             for i in range(0, 32, 4)],
        'scope': 'Decryption only. Code/data classification and runtime behavior unverified.'
    }
    (directory / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
