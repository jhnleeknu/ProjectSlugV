"""Read-only C++ placement decoding against pinned source and packed metadata."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
from disassemble_program import load_verified_program
from pack_scene_placements import build, decode_payload, sha, validate_container, SOURCE_SHA256


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256
    directory = root/'extracted/runtime/scene_placements'
    inventory_bytes = (root/'artifacts/scene_placements/inventory.json').read_bytes()
    scripts_bytes = (root/'extracted/runtime/scene_scripts/manifest.json').read_bytes()
    manifest_bytes = (directory/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    expected_files, expected_metadata = build(program, source, json.loads(inventory_bytes), scripts_bytes)
    assert manifest['source'] == source and manifest['resources'] == expected_metadata
    assert manifest['inventory_sha256'] == sha(inventory_bytes)
    assert manifest['scene_scripts_manifest_sha256'] == sha(scripts_bytes)
    assert (manifest['schema_version'], manifest['id'], manifest['format'], manifest['version']) == (1, 'scene-placements', 'MS5D', 1)
    assert {p.name for p in directory.glob('*.ms5d')} == set(expected_files)
    exe = root/'build/inspect_scene_placement'
    binary_sha = sha(exe.read_bytes())
    rows = []
    for item in expected_metadata:
        path = directory/item['file']
        packed = path.read_bytes()
        assert packed == expected_files[path.name]
        cpu = item['source_cpu_address']
        payload = validate_container(packed, cpu)
        assert payload == program[cpu:cpu+len(payload)]
        decoded = decode_payload(payload, cpu)
        expected_records = [dict(source_cpu_address=r['cpu_address'], source_rom_offset=r['rom_offset'],
            next_cpu_address=r['next_cpu_address'], next_rom_offset=r['end_rom_offset_exclusive'],
            gate=r['gate_word'], inline_byte_count=r['inline_byte_count_word'], x=r['word_at_4'],
            y=r['word_at_6'], bounds_pointer=r['bounds_pointer_long'], callback=r['callback_pointer_long'],
            inline_hex=r['inline_raw_hex']) for r in decoded[:-1]]
        expected = dict(source_cpu_address=cpu, source_rom_offset=cpu, payload_size=len(payload),
            records=expected_records, terminal_cpu_address=decoded[-1]['cpu_address'],
            terminal_rom_offset=decoded[-1]['rom_offset'], terminal_gate=0xffff)
        result = subprocess.run([str(exe), str(path)], capture_output=True, text=True)
        assert result.returncode == 0, (path.name, result.stderr)
        parsed = json.loads(result.stdout)
        assert parsed == expected, (path.name, parsed, expected)
        reconstructed = b''.join(struct.pack('>4H2I', r['gate'], r['inline_byte_count'], r['x'], r['y'],
            r['bounds_pointer'], r['callback'])+bytes.fromhex(r['inline_hex']) for r in parsed['records'])+struct.pack('>H', parsed['terminal_gate'])
        assert reconstructed == payload
        rows.append(dict(file=path.name, container_sha256=sha(packed), payload_sha256=sha(payload),
            decoded=parsed, all_bytes_equal=True))
    assert len(rows) == 18 and sum(len(r['decoded']['records']) for r in rows) == 24
    negatives = []
    raw_positive = []
    folder = root/'artifacts/scene_placements'
    report_path = folder/'resource_verification.json'
    report_path.unlink(missing_ok=True)
    good = next(iter(expected_files.values()))
    def changed(payload=None, **fields):
        header = list(struct.unpack('<4s7I', good[:32]))
        body = good[32:] if payload is None else payload
        for key, value in fields.items():
            header[dict(magic=0, version=1, kind=2, cpu=3, rom=4, size=5, crc=6, reserved=7)[key]] = value
        if payload is not None:
            header[5], header[6] = len(body), zlib.crc32(body)
        return struct.pack('<4s7I', *header)+body
    with tempfile.TemporaryDirectory(dir=folder) as scratch:
        temp = Path(scratch)/'test.ms5d'
        def reject(data, label):
            temp.write_bytes(data)
            result = subprocess.run([str(exe), str(temp)], capture_output=True, text=True)
            assert result.returncode != 0 and not result.stdout and temp.read_bytes() == data, (label, result.stdout, result.stderr)
            negatives.append(dict(failure=label, read_only_input_preserved=True, stderr=result.stderr.strip()))
        for length in (0, 1, 31):
            reject(good[:length], 'truncated-header-%d' % length)
        for field, value in [('magic', b'BAD!'), ('version', 2), ('kind', 2), ('cpu', 1), ('rom', 0),
                             ('size', len(good)), ('crc', 0), ('reserved', 1)]:
            reject(changed(**{field:value}), 'header-'+field)
        reject(changed(cpu=0x100000, rom=0x100000), 'outside-fixed-ROM')
        reject(good[:-1], 'truncated-payload')
        reject(good+b'\0', 'unadvertised-trailing-byte')
        bad = bytearray(good); bad[-1] ^= 1
        reject(bytes(bad), 'payload-CRC')
        for body, label in [(b'', 'empty'), (b'\x80\0', 'negative-gate-is-not-terminal'),
                            (b'\xff\xff\0\0', 'bytes-after-exact-terminal'),
                            (b'\xff\xff\0', 'odd-payload'), (good[32:-2], 'missing-terminal')]:
            reject(changed(payload=body), label)
        header = struct.pack('>4H2I', 0, 0, 0, 0, 0, 0)
        for count in (1, 3, 0x8000, 0xfffe):
            body = bytearray(header); struct.pack_into('>H', body, 2, count)
            reject(changed(payload=bytes(body)+b'\xff\xff'), 'invalid-inline-count-%04x' % count)
        reject(changed(payload=header[:14]), 'truncated-record-header')
        body = bytearray(header); struct.pack_into('>H', body, 2, 4)
        reject(changed(payload=bytes(body)+b'\x12\x34'), 'truncated-inline')
        # Decoder stores bounds and callback raw; packer alone restricts canonical bounds0.
        body = struct.pack('>4H2I', 0x8000, 2, 0xffff, 0x8000, 0xffffffff, 1)+b'\x12\x34'+struct.pack('>4H2I', 0xfffe, 0, 1, 2, 3, 0xfffffffe)+b'\xff\xff'
        data = changed(payload=body)
        temp.write_bytes(data)
        result = subprocess.run([str(exe), str(temp)], capture_output=True, text=True)
        assert result.returncode == 0 and temp.read_bytes() == data, result.stderr
        parsed = json.loads(result.stdout)
        assert [(r['gate'], r['bounds_pointer'], r['callback']) for r in parsed['records']] == [(0x8000, 0xffffffff, 1), (0xfffe, 3, 0xfffffffe)]
        assert parsed['records'][0]['inline_hex'] == '1234' and parsed['terminal_gate'] == 0xffff
        raw_positive.append(dict(fixture='synthetic-raw-negative-gates-and-opaque-pointers', payload_sha256=sha(body), decoded=parsed))
    assert sha(exe.read_bytes()) == binary_sha
    assert sha(program) == SOURCE_SHA256
    assert (directory/'manifest.json').read_bytes() == manifest_bytes
    assert all((directory/name).read_bytes() == data for name, data in expected_files.items())
    assert (root/'artifacts/scene_placements/inventory.json').read_bytes() == inventory_bytes
    report = dict(source=source, binary_sha256=binary_sha, manifest_sha256=sha(manifest_bytes),
        inventory_sha256=sha(inventory_bytes), script_manifest_sha256=sha(scripts_bytes),
        resources=len(rows), records=24, terminals=18, payload_bytes=sum(r['decoded']['payload_size'] for r in rows),
        negative_cases=len(negatives), synthetic_raw_positive_cases=len(raw_positive),
        source_unchanged=True, resource_inputs_unchanged=True, results=rows,
        negatives=negatives, synthetic_raw_positive=raw_positive,
        scope='Typed read-only resource decoding and byte reconstruction, not native placement handler execution or C++ gameplay equivalence. Canonical18 spans have null bounds. Callback and bounds pointers are opaque stored values, never dereferenced. Synthetic negative gates8000/fffe and opaque pointers are separate decoder fixtures. CLI failures preserve input bytes; API output preservation is covered separately by C++ units.')
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(resources=18, records=24, terminals=18, negative_cases=len(negatives),
        report_sha256=sha(report_path.read_bytes()), binary_sha256=binary_sha)))


if __name__ == '__main__':
    main()
