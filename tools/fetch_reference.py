"""Fetch hash-pinned MAME reference sources; never fetch game ROMs."""
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'config/mame_sources.json').read_text())
    destination = root / 'artifacts/reference'
    destination.mkdir(parents=True, exist_ok=True)
    for item in manifest['files']:
        target = destination / Path(item['path']).name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']:
            print('Verified cached:', item['path'])
            continue
        url = 'https://raw.githubusercontent.com/mamedev/mame/' + manifest['revision'] + '/' + item['path']
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Reference source hash mismatch: ' + item['path'])
        temporary = target.with_suffix(target.suffix + '.tmp')
        temporary.write_bytes(data)
        temporary.replace(target)
        print('Fetched:', item['path'])


if __name__ == '__main__':
    main()
