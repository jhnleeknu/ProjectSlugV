"""Compare isolated original40 handler evidence with actual13-register CLI.

Native high32-bit guards are deliberately pending, not error-equivalence cases:
the new program bus masks24 bits whereas that bounded observer does not.
"""
import collections
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zlib

import observe_animation_banked_handler as original
import pack_animation_banked_reads as packer

NATIVE_SHA = 'a6b075d468e015c8fde64129abf6003964bd1f1669ef8c6538545cc0aa3d39a5'
OBSERVER_SHA = '66a156cd73be2a10cfb91413396a8fa9379f6ee09cea48c17f3d561d3e9daed3'
MANIFEST_SHA = '366b8f89dc46705fc765ca2b331c69b206b9633fc80f0b7c8fb9fdb3a484cb82'
KEYS = tuple('d%d' % n for n in range(8))+tuple('a%d' % n for n in range(5))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse(text):
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key: '+key)
            value[key] = item
        return value
    value = json.loads(text, object_pairs_hook=unique_object)
    assert type(value) is dict and set(value) == set(KEYS), value
    assert all(type(value[k]) is int and 0 <= value[k] <= 0xffffffff for k in KEYS), value
    return value


def invoke(exe, fx, inp, out, vectors, pvc, resources, numeric=None):
    numbers = [fx['bank_base'], fx['regs']['a6']]+[fx['regs'][k] for k in KEYS]
    if numeric:
        for index, value in numeric.items():
            numbers[index] = value
    return subprocess.run([str(exe)]+[str(x) for x in numbers]+[str(inp), str(out), str(vectors), str(pvc)]+
        [str(p) for p in resources], text=True, capture_output=True, timeout=5)


def native_audit(root, program, source):
    folder = root/'artifacts/animation_banked_handler_native'
    rp = folder/'observation.json'
    assert digest(rp) == NATIVE_SHA and digest(root/'tools/observe_animation_banked_handler.py') == OBSERVER_SHA
    native = json.loads(rp.read_text())
    assert native['source'] == source and native['failure'] is None and native['reproduced_twice']
    hashes = {str(rp.relative_to(root)): NATIVE_SHA}
    for name, value in native['inputs'].items():
        assert digest(root/name) == value, name
        hashes[name] = value
    assert original.pinned_reference(root) == native['pinned_reference']
    for name, value in native['pinned_reference']['files'].items():
        path = 'artifacts/reference/'+name
        assert digest(root/path) == value
        hashes[path] = value
    oracle = native['oracle']
    assert original.unicorn.__version__ == oracle['version']
    assert digest(oracle['library']) == oracle['library_sha256']
    assert digest(inspect.getfile(original.unicorn.Uc)) == oracle['wrapper_sha256']
    hashes[oracle['library']] = oracle['library_sha256']
    hashes[str(Path(inspect.getfile(original.unicorn.Uc)).resolve())] = oracle['wrapper_sha256']
    probe = native['bus_alias_probe']
    if probe:
        assert digest(root/probe['file']) == probe['sha256']
        assert digest(root/'tools/probe_m68k_bus_alias.py') == probe['tool_sha256']
        hashes[probe['file']] = probe['sha256']
        hashes['tools/probe_m68k_bus_alias.py'] = probe['tool_sha256']
    static = json.loads((folder/'source.json').read_text())
    for row in static['instructions']:
        at = row['rom_offset']
        assert bytes.fromhex(row['raw']) == program[at:at+row['size']]
    fixtures, rows, files = [], [], {}
    for index, case in enumerate(original.cases()):
        fx, expected, actual = original.run_case(program, case, index)
        row = original.summarize(fx, expected, actual, case)
        row.update(case_index=index, case=case, reproduced_twice=True,
            ram_before_sha256=original.sha(fx['ram']), ram_after_sha256=original.sha(actual['ram_after']),
            pvc_incoming_sha256=original.sha(fx['pvc']))
        assert row == native['results'][index], (index, 'full native replay')
        assert all(actual['outgoing'][k] == fx['regs'][k] for k in ('a5', 'a6'))
        payloads = {'case_%04d_ram_before.bin' % index: fx['ram'],
            'case_%04d_ram_after.bin' % index: actual['ram_after'],
            'case_%04d_pvc_incoming.bin' % index: fx['pvc'],
            'case_%04d_trace.json' % index: (json.dumps({k: actual[k] for k in
                ('pcs', 'reads', 'writes', 'invalid', 'interrupts', 'guard', 'error')})+'\n').encode()}
        for name, data in payloads.items():
            assert (folder/name).read_bytes() == data, name
            files[name] = original.sha(data)
            hashes[str((folder/name).relative_to(root))] = files[name]
        fixtures.append(fx);rows.append(row)
    assert files == native['artifacts'] and len(files) == native['artifact_files'] == 380
    assert original.sha(json.dumps(sorted(files.items())).encode()) == native['artifact_manifest_sha256']
    assert len(rows) == native['cases'] == 95
    assert original.guard_controls(program, rows) == native['guard_controls']
    assert original.sr_backend_probe() == native['sr_backend_probe']
    return native, fixtures, hashes


def resources_audit(root, program):
    folder = root/'extracted/runtime/animation_banked_reads'
    mp = folder/'manifest.json'
    assert digest(mp) == MANIFEST_SHA
    files, manifest = packer.build(root)
    assert manifest == json.loads(mp.read_text())
    resources, hashes = [], {str(mp.relative_to(root)): MANIFEST_SHA}
    for name, data in files.items():
        assert (folder/name).read_bytes() == data
        hashes[str((folder/name).relative_to(root))] = original.sha(data)
        if name.endswith('.ms5d'):
            payload = packer.validate_container(data)
            fields = struct.unpack_from('<4s7I', data)
            rom = fields[4]
            assert payload == program[rom:rom+len(payload)]
            resources.append(folder/name)
    assert len(resources) == 37
    return resources, manifest, hashes


def extra_negatives(root, exe, fx, vectors, resources):
    rows = []
    field = next(p for p in resources if struct.unpack_from('<I', p.read_bytes(), 12)[0] <= 0x4a76c <
        struct.unpack_from('<I', p.read_bytes(), 12)[0]+len(p.read_bytes())-32)
    with tempfile.TemporaryDirectory(prefix='ms5-banked-lookup-negative-') as directory:
        work = Path(directory)
        def reject(label, ram=None, vector=None, pvc=None, windows=None, numeric=None,
                   output_alias=None, fifo=None):
            inp, out, vp, pp = (work/n for n in ('input.bin', 'output.bin', 'vectors.bin', 'pvc.bin'))
            for path in (inp, out, vp, pp):
                if path.exists():path.unlink()
            inp.write_bytes(fx['ram'] if ram is None else ram);out.write_bytes(b'previous output')
            vp.write_bytes(vectors if vector is None else vector);pp.write_bytes(fx['pvc'] if pvc is None else pvc)
            windows = list(resources if windows is None else windows)
            if fifo:
                path = dict(input=inp, output=out, vector=vp, pvc=pp).get(fifo, work/'fifo.ms5d')
                if path.exists():path.unlink()
                os.mkfifo(path)
                if fifo == 'resource':windows.append(path)
            target = {'input': inp, 'vector': vp, 'pvc': pp}.get(output_alias, out)
            if output_alias == 'hardlink-input':
                target = work/'input-hardlink.bin'
                if target.exists():target.unlink()
                os.link(inp, target)
            if output_alias == 'resource':target = windows[-1]
            protected = {p: p.read_bytes() for p in [inp, out, vp, pp]+windows if p.is_file()}
            run = invoke(exe, fx, inp, target, vp, pp, windows, numeric)
            assert run.returncode != 0 and not run.stdout and run.stderr.strip(), (label, run.stdout, run.stderr)
            assert all(p.read_bytes() == data for p, data in protected.items()), label
            rows.append(dict(label=label, error=run.stderr.strip(), files_preserved=True))
            if fifo:
                path.unlink()
        reject('truncated-RAM', ram=fx['ram'][:-1])
        reject('truncated-vector-view', vector=vectors[:-1])
        reject('truncated-PVC-view', pvc=fx['pvc'][:-1])
        reject('negative-bank-number', numeric={0: -1})
        reject('overflow-bank-number', numeric={0: 0x100000000})
        reject('invalid-register-number', numeric={2: '1junk'})
        reject('input-output-alias', output_alias='input')
        reject('input-output-hardlink-alias', output_alias='hardlink-input')
        reject('vector-output-alias', output_alias='vector')
        reject('PVC-output-alias', output_alias='pvc')
        reject('missing-reached-field-window', windows=[p for p in resources if p != field])
        duplicate = work/'duplicate.ms5d';duplicate.write_bytes(field.read_bytes())
        reject('distinct-inode-duplicate-physical-window', windows=resources+[duplicate])
        reject('resource-output-alias-copy', windows=resources+[duplicate], output_alias='resource')
        raw = field.read_bytes()
        bad = work/'bad.ms5d'
        data = bytearray(raw);struct.pack_into('<I', data, 8, 99);bad.write_bytes(data)
        reject('malformed-resource-kind', windows=[bad])
        data = bytearray(raw);data[-1] ^= 1;bad.write_bytes(data)
        reject('resource-CRC', windows=[bad])
        bad.write_bytes(raw[:-1]);reject('truncated-resource', windows=[bad])
        cpu = 0x4a76c;payload = raw[32+cpu-struct.unpack_from('<I', raw, 12)[0]:][:1]
        bad.write_bytes(struct.pack('<4s7I', b'MS5D', 1, 1, cpu, cpu, 1, zlib.crc32(payload), 0)+payload)
        reject('partial-reached-WORD-unit', windows=[p for p in resources if p != field]+[bad])
        for surface in ('input', 'output', 'vector', 'pvc', 'resource'):
            reject('FIFO-'+surface, fifo=surface)
    return rows


def cpp_dependencies(root, initial):
    """Pin every repository header reached from the target's translation units."""
    names = set(initial);todo = list(initial)
    while todo:
        name = todo.pop()
        if not name.endswith(('.h', '.cpp')):continue
        for header in re.findall(r'#include\s+"([^"]+)"', (root/name).read_text()):
            dependency = 'engine/include/'+header
            assert (root/dependency).is_file(), dependency
            if dependency not in names:names.add(dependency);todo.append(dependency)
    return names


def main():
    root = Path(__file__).resolve().parents[1]
    exe = root/'build/execute_animation_banked_lookup'
    if sys.argv[1:]:
        assert len(sys.argv) == 3 and sys.argv[1] == '--exe'
        exe = Path(sys.argv[2]).resolve()
    folder = root/'artifacts/animation_banked_lookup_execution';folder.mkdir(parents=True, exist_ok=True)
    report_path = folder/'verification.json';report_path.unlink(missing_ok=True)
    for old in folder.glob('case_*'):old.unlink()
    program, source = original.load_verified_program(root)
    rom = root/source['path'];rom_before = digest(rom), rom.stat().st_mtime_ns
    native, fixtures, artifacts = native_audit(root, program, source)
    resources, manifest, resource_hashes = resources_audit(root, program);artifacts.update(resource_hashes)
    names = cpp_dependencies(root, {'engine/tools/execute_animation_banked_lookup.cpp',
        'engine/src/animation_banked_lookup.cpp', 'engine/src/program_bus.cpp',
        'engine/src/physical_rom_resource.cpp', 'engine/src/fixed_data_resource.cpp'})
    names.add('Makefile')
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.suffix == '.py' and root/'tools' in path.parents:names.add(str(path.relative_to(root)))
    inputs = {name: digest(root/name) for name in sorted(names)}
    inputs[source['path']] = rom_before[0]
    inputs[str(exe)] = digest(exe)
    assert exe.stat().st_mtime_ns >= max((root/n).stat().st_mtime_ns for n in names if n.endswith(('.cpp', '.h'))), 'Stale CLI'
    vectors = program[:128];vp = folder/'vectors128.bin';vp.write_bytes(vectors);artifacts[str(vp.relative_to(root))] = digest(vp)
    successes, failures, pending = [], [], []
    for index, (row, fx) in enumerate(zip(native['results'], fixtures)):
        outcome = row['outcome']
        if outcome == 'unsupported_high_32bit_effective_address':
            pending.append(dict(case_index=index, label=row['label'], status='not-compared',
                reason='Native observer guarded high32-bit address; C++24-bit bus masking has different scope. No original equivalence or expected-error claim.'))
            continue
        inp, out, pvc = (folder/('case_%04d_' % index+suffix) for suffix in ('input.bin', 'cpp.bin', 'pvc.bin'))
        inp.write_bytes(fx['ram']);pvc.write_bytes(fx['pvc']);out.write_bytes(b'previous output')
        protected = {p: p.read_bytes() for p in [inp, vp, pvc]+resources}
        run = invoke(exe, fx, inp, out, vp, pvc, resources)
        if outcome == 'complete':
            assert run.returncode == 0, (index, row['label'], run.stderr)
            actual = parse(run.stdout);want = {k: row['outgoing']['registers15'][k] for k in KEYS}
            assert actual == want, (index, actual, want)
            assert out.read_bytes() == (root/'artifacts/animation_banked_handler_native'/('case_%04d_ram_after.bin' % index)).read_bytes()
            state = folder/('case_%04d_state.json' % index);state.write_text(run.stdout)
            artifacts[str(state.relative_to(root))] = digest(state)
            successes.append(dict(case_index=index, label=row['label'], result=actual, full_RAM_equal=True))
        else:
            assert run.returncode != 0 and not run.stdout and run.stderr.strip(), (index, outcome, run.stdout, run.stderr)
            assert out.read_bytes() == b'previous output', row['label']
            failures.append(dict(case_index=index, label=row['label'], original_guard=outcome, error=run.stderr.strip(), output_preserved=True))
        assert all(p.read_bytes() == data for p, data in protected.items()), row['label']
        for path in (inp, out, pvc):artifacts[str(path.relative_to(root))] = digest(path)
    assert (len(successes), len(failures), len(pending)) == (73, 19, 3)
    extra = extra_negatives(root, exe, fixtures[0], vectors, resources)
    for name, value in {**inputs, **artifacts}.items():
        path = Path(name) if name.startswith('/') else root/name
        assert digest(path) == value, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_before
    report = dict(source=source, oracle=native['oracle'], inputs=inputs, native_resource_and_CPP_artifacts=artifacts,
        native_observation_sha256=NATIVE_SHA, resource_manifest_sha256=MANIFEST_SHA,
        original_cases_reexecuted=95, original_complete_CPP_matches=len(successes),
        original_guard_CPP_errors=len(failures), native_high32_pending=len(pending),
        extra_negative_count=len(extra), resources_loaded_together=37, resource_counts=manifest['counts'],
        successes=successes, native_guard_errors=failures, high32_pending=pending, extra_negatives=extra,
        ROM_unchanged=True, full40_claim=False,
        limits='Isolated13-register handler only, stops before4a276. A5/A6 unchanged in original replay; CLI A6 is by-value input, A5 is outside13-register ABI. '
            'Vectors are explicit canonical-cart128BYTE view; PVC is declared8192BYTE fixture. High32bit guards pending, not compared to24bit-masked C++. '
            'No full49fc6/bank-selection/natural-script/carry/fullCCR/timing claim. MS5D kind2loader cannot represent final16bytes of each1MiB bank; reached spans end beforePVC2fe000. '
            'Tested validation/execution failures preserve files; ftruncate/write OS I/O failures can mutate output and are not atomic. API transaction rollback is separate unit evidence.')
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(native_replayed=95, complete_CPP_matches=73, guard_CPP_errors=19, high32_pending=3,
        extra_negatives=len(extra), sha256=digest(report_path))))


if __name__ == '__main__':
    main()
