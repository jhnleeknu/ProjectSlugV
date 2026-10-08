"""Pack immutable ROM units actually read by the frozen isolated40 observation.

Existing MS5D v1 kind1/2 only. Synthetic handler fixtures and declared incoming
bank/vector state are provenance, not natural script/table or C++ consumption.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
OBSERVER = 'tools/observe_animation_banked_handler.py'
OBSERVER_SHA256 = '66a156cd73be2a10cfb91413396a8fa9379f6ee09cea48c17f3d561d3e9daed3'
REPORT = 'artifacts/animation_banked_handler_native/observation.json'
REPORT_SHA256 = 'a6b075d468e015c8fde64129abf6003964bd1f1669ef8c6538545cc0aa3d39a5'
BANK_END = 0x2fe000  # stricter than the existing loader's 2ffff0 upper bound


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, name):
    require(type(value) is int and value >= 0, 'Invalid ' + name)
    return value


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated MS5D header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    require((magic, version, reserved) == (b'MS5D', 1, 0) and kind in (1, 2), 'Invalid MS5D header')
    require(0 < size <= 0x100000 and len(packed) == 32 + size, 'Invalid MS5D size')
    if kind == 1:
        require(cpu == rom and cpu < 0x100000 and size <= 0x100000-cpu, 'Invalid fixed mapping')
    else:
        require(0x200000 <= cpu < BANK_END and size <= BANK_END-cpu, 'Bank window enters PVC')
        bank = rom-(cpu-0x200000)
        require(0x100000 <= bank and bank % 0x100000 == 0, 'Invalid aligned bank mapping')
        require(rom < 0x800000 and size <= 0x800000-rom, 'Bank source outside ROM')
    payload = packed[32:]
    require(zlib.crc32(payload) == crc, 'MS5D payload CRC mismatch')
    return payload


def wrap(program, kind, cpu, rom, size):
    require(0 <= rom < len(program) and 0 < size <= len(program)-rom, 'Source span outside ROM')
    payload = bytes(program[rom:rom+size])
    packed = struct.pack('<4s7I', b'MS5D', 1, kind, cpu, rom, size, zlib.crc32(payload), 0)+payload
    require(validate_container(packed) == payload, 'MS5D source bytes differ')
    return packed


def unit_identity(address, bank, size):
    """Independent byte-region classification; do not trust report kind/offsets."""
    require(0 <= address < 0x1000000 and size in (1, 2), 'Unsupported reached address or unit')
    require(size == 1 or address % 2 == 0, 'Odd WORD unit')
    if address < 0x100000:
        require(address+size <= 0x100000, 'Fixed unit crosses region')
        return dict(kind='fixed_vector_cart_view_assumed' if address < 0x80 else 'fixed_rom',
                    logical=address, physical_rom=address)
    if address < 0x200000:
        require(address+size <= 0x200000, 'RAM unit crosses region')
        return dict(kind='ram', logical=address, canonical_ram=0x100000 | (address & 0xffff), mirror=(address >> 16) & 15)
    if address < BANK_END:
        require(address+size <= BANK_END, 'ROM unit enters PVC')
        return dict(kind='bank_rom', logical=address, bank_base=bank, physical_rom=bank+address-0x200000)
    require(address+size <= 0x300000, 'Unsupported reached device region')
    return dict(kind='pvc_cart_ram', logical=address, pvc_word=(address-0x2fe000) >> 1)


def collect(program, report):
    """Validate complete read units against immutable source, then retain ROM only."""
    spans = []
    skipped = dict(ram=0, pvc_cart_ram=0)
    for index, row in enumerate(report['results']):
        require(row['case_index'] == index and row['label'] == row['case']['label'], 'Case identity differs')
        bank = integer(row['bank_base'], 'bank')
        require(bank >= 0x100000 and bank % 0x100000 == 0, 'Unaligned original bank')
        for access in row['ordered_accesses']:
            if access['access'] != 'read':
                continue
            address = integer(access['address'], 'read address')
            size = integer(access['size'], 'read size')
            require(size in (1, 2, 4) and (size == 1 or address % 2 == 0), 'Invalid reached read')
            raw = bytes.fromhex(access['value'])
            require(len(raw) == size and access['before'] == access['value'], 'Read byte count/before differs')
            step = 1 if size == 1 else 2
            require(len(access['units']) == size//step, 'Missing LONG/WORD units')
            for offset, declared in zip(range(0, size, step), access['units']):
                cpu = address+offset
                actual = unit_identity(cpu, bank, step)
                require(actual == declared, 'Read classification/mapping differs')
                if actual['kind'] in skipped:
                    skipped[actual['kind']] += 1
                    continue
                rom = actual['physical_rom']
                require(0 <= rom and rom+step <= len(program), 'Read physical span outside ROM')
                require(raw[offset:offset+step] == program[rom:rom+step], 'Read bytes differ from immutable ROM')
                kind = 2 if actual['kind'] == 'bank_rom' else 1
                if kind == 2:
                    require(bank+0xfe000 <= len(program), 'Unbacked original bank')
                evidence = dict(case_index=index, case_label=row['label'], outcome=row['outcome'],
                    read_pc=access['pc'], logical_read_address=address, logical_read_size=size,
                    unit_cpu_address=cpu, unit_rom_offset=rom, unit_size=step,
                    unit_sha256=sha(program[rom:rom+step]), cart_vectors_assumed=cpu < 0x80)
                spans.append(dict(kind=kind, bank=bank if kind == 2 else None,
                                  cpu=cpu, rom=rom, end=cpu+step, evidence=[evidence]))
    return spans, skipped


def merge(spans):
    result = []
    for item in sorted(spans, key=lambda x: (x['kind'], x['bank'] or 0, x['cpu'], x['end'])):
        item = copy.deepcopy(item)
        if result:
            previous = result[-1]
            if (previous['kind'], previous['bank']) == (item['kind'], item['bank']) and item['cpu'] <= previous['end']:
                require(item['rom']-item['cpu'] == previous['rom']-previous['cpu'], 'Merge mapping differs')
                previous['end'] = max(previous['end'], item['end'])
                previous['evidence'].extend(item['evidence'])
                continue
        result.append(item)
    for item in result:
        unique = {json.dumps(x, sort_keys=True): x for x in item['evidence']}
        item['evidence'] = [unique[k] for k in sorted(unique)]
    return result


def audit_report(root, program, source):
    require(sha((root/REPORT).read_bytes()) == REPORT_SHA256, 'Frozen native report SHA differs')
    require(sha((root/OBSERVER).read_bytes()) == OBSERVER_SHA256, 'Frozen observer SHA differs')
    report = json.loads((root/REPORT).read_text())
    require(report['source'] == source and report['failure'] is None and report['cases'] == len(report['results']) == 95,
            'Native source/cases/status differs')
    require(not report['original_program_modified'] and not report['register_injection_after_begin'], 'Invalid native provenance')
    inputs = {REPORT: REPORT_SHA256, OBSERVER: OBSERVER_SHA256}
    for name, digest in report['inputs'].items():
        require(sha((root/name).read_bytes()) == digest, 'Native input SHA differs: '+name)
        inputs[name] = digest
    for name, digest in report['pinned_reference']['files'].items():
        path = 'artifacts/reference/'+name
        require(sha((root/path).read_bytes()) == digest, 'Pinned reference SHA differs: '+name)
        inputs[path] = digest
    folder = (root/REPORT).parent
    for name, digest in report['artifacts'].items():
        require(Path(name).name == name, 'Invalid native artifact filename')
        require(sha((folder/name).read_bytes()) == digest, 'Native artifact SHA differs: '+name)
        inputs[str((folder/name).relative_to(root))] = digest
    require(len(report['artifacts']) == report['artifact_files'] == 380, 'Native artifact count differs')
    require(sha(json.dumps(sorted(report['artifacts'].items())).encode()) == report['artifact_manifest_sha256'], 'Native manifest SHA differs')
    for index, row in enumerate(report['results']):
        trace = json.loads((folder/('case_%04d_trace.json' % index)).read_text())
        actual = [dict(pc=x['pc'], access=x['access'], address=x['address'], size=x['size'], value=x['bytes']) for x in trace['reads']]
        declared = [{k: x[k] for k in ('pc', 'access', 'address', 'size', 'value')} for x in row['ordered_accesses'] if x['access'] == 'read']
        require(actual == declared, 'Actual native trace/read metadata differs')
    require(sha(program) == SOURCE_SHA256, 'Canonical program SHA differs')
    return report, inputs


def build(root):
    root = Path(root)
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256, 'Unsupported canonical program')
    report, inputs = audit_report(root, program, source)
    names = ('tools/pack_animation_banked_reads.py', 'tools/disassemble_program.py',
             'engine/src/fixed_data_resource.cpp', 'engine/include/ms5/fixed_data_resource.h')
    for name in names:
        inputs[name] = sha((root/name).read_bytes())
    spans, skipped = collect(program, report)
    files, resources = {}, []
    for item in merge(spans):
        kind, cpu, rom, size = item['kind'], item['cpu'], item['rom'], item['end']-item['cpu']
        stable = 'animation-banked-read-kind%d-cpu%06x-rom%06x' % (kind, cpu, rom)
        name = 'read_k%d_%06x_%06x.ms5d' % (kind, cpu, rom)
        packed = wrap(program, kind, cpu, rom, size)
        files[name] = packed
        resources.append(dict(id=stable, file=name, format='MS5D', version=1, kind=kind,
            source_cpu_address=cpu, source_rom_offset=rom, bank_base=item['bank'],
            end_cpu_address_exclusive=cpu+size, end_rom_offset_exclusive=rom+size,
            payload_size=size, size=len(packed), payload_crc32=zlib.crc32(packed[32:]),
            payload_sha256=sha(packed[32:]), sha256=sha(packed),
            read_pcs=sorted({x['read_pc'] for x in item['evidence']}),
            case_labels=sorted({x['case_label'] for x in item['evidence']}),
            cart_vectors_assumed=any(x['cart_vectors_assumed'] for x in item['evidence']),
            observed_read_units=item['evidence']))
    manifest = dict(schema_version=1, id='animation-banked-handler-reached-rom', source=source,
        provenance=dict(observer_sha256=OBSERVER_SHA256, report_sha256=REPORT_SHA256, inputs=dict(sorted(inputs.items()))),
        counts=dict(cases=95, resources=len(resources), fixed_resources=sum(x['kind'] == 1 for x in resources),
            banked_resources=sum(x['kind'] == 2 for x in resources), reached_rom_units=len(spans),
            skipped_ram_units=skipped['ram'], skipped_pvc_units=skipped['pvc_cart_ram'],
            total_payload_bytes=sum(x['payload_size'] for x in resources), total_container_bytes=sum(x['size'] for x in resources)),
        resources=resources,
        scope='Only immutable ROM units actually read before STOP/guards in95 synthetic isolated40 fixtures. '
              'Overlapping/adjacent units merged per kind and physical bank; RAM/PVC excluded. '
              'Cartridge vector view assumed; no logical-table, natural-script, full40 or C++ consumption claim.',
        loader_limits=dict(format='existing MS5D v1 kind1/2,32-byte little-endian header and CRC32 payload',
            maximum_payload=0x100000, bank_alignment=0x100000, loader_banked_end_exclusive=0x2ffff0,
            packer_rom_end_exclusive=BANK_END, reason='PVC overlay starts2fe000; never pack it as ROM'))
    files['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical program changed during packing')
    require(all(sha((root/n).read_bytes()) == h for n, h in inputs.items()), 'Provenance changed during packing')
    return files, manifest


def self_test():
    """Synthetic tests only; no canonical game bytes embedded in source."""
    count = 0
    def rejects(call):
        nonlocal count
        try:
            call()
        except (ValueError, KeyError):
            count += 1
            return
        raise AssertionError('Invalid input accepted')
    p = bytes((i*37) & 255 for i in range(0x100000))
    packed = wrap(p, 1, 0x100, 0x100, 4)
    require(validate_container(packed) == p[0x100:0x104], 'Synthetic fixed roundtrip');count += 1
    bad = bytearray(packed);bad[-1] ^= 1
    rejects(lambda: validate_container(bad))
    rejects(lambda: wrap(p, 1, 0xffffe, 0xffffe, 4))
    bank = b'\x5a'*0x300000
    require(validate_container(wrap(bank, 2, 0x2fdffe, 0x2fdffe, 2)) == b'\x5a\x5a', 'Last bank WORD');count += 1
    rejects(lambda: wrap(bank, 2, 0x2fdffe, 0x2fdffe, 4))
    rejects(lambda: wrap(bank, 2, 0x200000, 0x200100, 2))
    sample = dict(kind=2, bank=0x200000, cpu=0x200004, rom=0x200004, end=0x200006, evidence=[])
    joined = merge([sample, dict(sample, cpu=0x200006, rom=0x200006, end=0x200008), dict(sample)])
    require(len(joined) == 1 and joined[0]['end'] == 0x200008, 'Adjacent/overlap merge');count += 1
    separate = merge([sample, dict(sample, bank=0x300000, rom=0x300004)])
    require(len(separate) == 2, 'Distinct physical banks');count += 1
    access = dict(access='read', pc=0x4a3a0, address=0x100, size=4,
        value=p[0x100:0x104].hex(), before=p[0x100:0x104].hex(),
        units=[unit_identity(0x100, 0x200000, 2), unit_identity(0x102, 0x200000, 2)])
    report = dict(results=[dict(case_index=0, label='synthetic', case=dict(label='synthetic'),
        bank_base=0x200000, outcome='complete', ordered_accesses=[access])])
    spans, skipped = collect(p, report)
    require(len(spans) == 2 and merge(spans)[0]['end'] == 0x104 and not any(skipped.values()),
            'Both LONG WORD units retained');count += 1
    wrong = copy.deepcopy(report);wrong['results'][0]['ordered_accesses'][0]['units'][1]['physical_rom'] += 2
    rejects(lambda: collect(p, wrong))
    wrong = copy.deepcopy(report);wrong['results'][0]['ordered_accesses'][0]['units'].pop()
    rejects(lambda: collect(p, wrong))
    changed = bytearray(p);changed[0x100] ^= 1
    rejects(lambda: collect(changed, report))
    nonrom = copy.deepcopy(report)
    nonrom['results'][0]['ordered_accesses'] = [dict(access='read', pc=0x4a3a0,
        address=address, size=2, value='a5a5', before='a5a5', units=[unit_identity(address, 0x200000, 2)])
        for address in (0x1f8004, 0x2fe000)]
    require(collect(p, nonrom) == ([], dict(ram=1, pvc_cart_ram=1)), 'RAM/PVC never packed');count += 1
    require(unit_identity(0x7e, 0x200000, 2)['kind'] == 'fixed_vector_cart_view_assumed',
            'Vector assumption retained');count += 1
    with tempfile.TemporaryDirectory(prefix='ms5-banked-packer-test-') as directory:
        fake_root = Path(directory)
        fake_report = fake_root/REPORT
        fake_report.parent.mkdir(parents=True)
        fake_report.write_bytes(b'{}')
        rejects(lambda: audit_report(fake_root, p, {}))
    return count


def main():
    root = Path(__file__).resolve().parents[1]
    if sys.argv[1:] == ['--self-test']:
        print(json.dumps(dict(synthetic_tests=self_test(), passed=True)))
        return
    require(not sys.argv[1:], 'Usage: pack_animation_banked_reads.py [--self-test]')
    files, manifest = build(root)
    again, manifest_again = build(root)
    require(files == again and manifest == manifest_again, 'Two regenerations differ')
    output = root/'extracted/runtime/animation_banked_reads'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name, data in files.items():
            (staging/name).write_bytes(data)
            if name.endswith('.ms5d'):
                validate_container((staging/name).read_bytes())
        require(json.loads((staging/'manifest.json').read_text()) == manifest, 'Staged metadata differs')
        for name in files:
            (staging/name).replace(output/name)
    require(all((output/name).read_bytes() == data for name, data in files.items()), 'Published files differ')
    print(json.dumps(dict(counts=manifest['counts'], manifest_sha256=sha(files['manifest.json']), reproducible_twice=True)))


if __name__ == '__main__':
    main()
