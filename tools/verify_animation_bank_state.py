"""Whole-original bank chains versus actual sound CLI; never infer bank from RAM shadow.

The native bank is a pinned PVC model driven by actual original port writes, not
physical hardware measurement. C++ resumptions consume only their preceding C++
RAM/state and recorded host changes. No build or native artifact mutation occurs.
"""
import collections
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

import observe_animation_bank_state as original
import verify_animation_sound_execution as sound
from address_map import pvc_bank_update
from pack_animation_control import validate_container

NATIVE_SHA = '28060b3d2ea2edcd9048929b34855e8698c13504314c81421bde9764aa7fe777'
OBSERVER_SHA = '4fc007dca23ba6aebb2886c072329c777a65cbbaf4dd9d981a457af378bb4359'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_device(device, ports):
    """Apply each actual port write through the separately maintained address-map model."""
    result = dict(device)
    records = []
    assert len(ports) % 9 == 0
    for size, address, value in struct.iter_unpack('>BII', ports):
        assert size == 2 and address in (0x2ffff0, 0x2ffff2)
        assert 0 <= value <= 65535
        if address == 0x2ffff0:
            result['ff8'] = value
        else:
            result['ff9'] = value
        bank, ff8, ff9 = pvc_bank_update(result['ff8'], result['ff9'])
        result = dict(ff8=ff8, ff9=ff9, bank_base=bank)
        records.append(dict(port=address, raw_value=value, bank_base=bank, ff8_after=ff8, ff9_after=ff9))
    return result, records


def apply_changes(ram, changes, external):
    data = bytearray(ram)
    for change in changes:
        address, size, value = (change[k] for k in ('address', 'size', 'value'))
        if address == original.EXTERNAL:
            assert size == 1 and 0 <= value <= 255
            external = value
        else:
            at = address - original.BASE
            assert 0 <= at and at + size <= 65536 and 0 <= value < 1 << (8 * size)
            data[at:at + size] = value.to_bytes(size, 'big')
    return bytes(data), external


def expected(phase, trace, bank):
    result = sound.initial(phase['result'], bank)
    if phase['waiting']:
        pending = phase['pending']
        assert pending['animation_phase'] == 4 and pending['sound_phase'] in (1, 2)
        result.update(phase=4, saved_a0=pending['outer_a0'], saved_a1=pending['outer_a1'],
            callback_sound_phase=pending['sound_phase'], callback_saved_low=pending['saved_low'], callback_waiting=True)
    else:
        assert phase['pending'] is None and phase['final_pc'] == original.RETURN
        assert phase['final_a7'] == original.STACK + 4
    result.update(carry=phase['carry'], external_reads=sum(r['kind'] == 'external' for r in trace['reads']))
    assert result['external_reads'] == phase['external_reads']
    return result


def audit(root, program, source):
    folder = root / 'artifacts/animation_bank_state_native'
    report_path = folder / 'observation.json'
    assert NATIVE_SHA is not None, 'Native report has not been frozen for acceptance'
    assert digest(report_path) == NATIVE_SHA
    assert digest(root / 'tools/observe_animation_bank_state.py') == OBSERVER_SHA
    native = json.loads(report_path.read_text())
    assert native['source'] == source and native['oracle'] == original.oracle_provenance()
    assert native['failure'] is None and native['reproduced_twice'] is True
    assert (native['cases'], native['phases'], native['pending_chains'], native['total_native_ports'], native['total_external_reads']) == (92, 276, 68, 560, 0)
    assert len(native['guard_controls']) == 3
    for key in ('original_program_modified', 'in_call_SR_read', 'register_injection_after_begin',
            'fake_callback', 'device_mutated_by_host', 'Cpp_comparison_performed', 'opcode40_claim'):
        assert native[key] is False, key
    hashes = {str(report_path.relative_to(root)): digest(report_path)}
    for name, value in native['inputs'].items():
        assert digest(root / name) == value, name
        hashes[name] = value
    static = json.loads((folder / 'source.json').read_text())
    assert static['source'] == source
    branches = set()
    for start, end in static['ranges']:
        cursor = start
        for instruction in static['instructions']:
            if start <= instruction['cpu_address'] < end:
                assert instruction['cpu_address'] == instruction['rom_offset'] == cursor
                assert bytes.fromhex(instruction['raw']) == program[cursor:cursor + instruction['size']]
                cursor += instruction['size']
                if instruction['mnemonic'].startswith('b') and not instruction['mnemonic'].startswith(('bra', 'bsr', 'btst', 'bclr')):
                    branches.add(instruction['cpu_address'])
        assert cursor == end
    assert static['actual_rts']['raw'] == '4e75' and program[original.TARGET:original.TARGET + 2] == b'\x4e\x75'
    assert static['ranges'] == [list(x) for x in original.RANGES]
    cases = original.cases()
    assert len(cases) == len(native['results']) == native['cases']
    observer = original.Observer(program, branches)
    counts = collections.Counter()
    all_files = {}
    outcomes = collections.defaultdict(collections.Counter)
    for index, (case, row) in enumerate(zip(cases, native['results'])):
        assert row['case_index'] == index and row['fixture'] == case
        replay, payloads, traces = original.run_case(observer, program, case, index)
        replay.update(case_index=index, fixture=case,
            total_external_reads=sum(p['external_reads'] for p in replay['phases']))
        assert replay == row, (index, 'native complete phase/stack/device metadata replay')
        for name, data in payloads.items():
            assert (folder / name).read_bytes() == data, (index, name)
            all_files[name] = hashlib.sha256(data).hexdigest()
            assert native['artifacts'][name] == all_files[name]
            hashes[str((folder / name).relative_to(root))] = all_files[name]
        device = dict(case['device_in'])
        timeline = []
        for phase, trace in zip(row['phases'], traces):
            assert phase['device_in'] == device
            ports = payloads[phase['ports_file']]
            device, records = independent_device(device, ports)
            assert phase['device_out'] == device
            timeline.extend(records)
            for branch in trace['branches']:
                outcomes[branch['pc']][branch['next_pc']] += 1
            counts['phases'] += 1
            counts['ports'] += len(ports) // 9
            counts['external_reads'] += phase['external_reads']
        assert len(timeline) == len(row['pvc_timeline'])
        for independently_derived, recorded in zip(timeline, row['pvc_timeline']):
            assert all(recorded[k] == v for k, v in independently_derived.items())
        counts['resumes'] += len(row['phases']) - 1
    assert all_files == native['artifacts'] and len(all_files) == native['artifact_files']
    assert hashlib.sha256(json.dumps(sorted(all_files.items())).encode()).hexdigest() == native['artifact_manifest_sha256']
    assert original.guard_controls(observer, program) == native['guard_controls']
    observed = {hex(a): {hex(b): n for b, n in sorted(values.items())} for a, values in sorted(outcomes.items())}
    assert observed == native['observed_branch_successors']
    assert counts['phases'] == native['phases'] and counts['ports'] == native['total_native_ports']
    assert counts['external_reads'] == native['total_external_reads']
    return native, hashes, counts


def negatives(root, exe, native):
    row = next(r for r in native['results'] if r['fixture']['chain'] == 'high')
    phase = row['phases'][1]
    native_folder = root / 'artifacts/animation_bank_state_native'
    trace = json.loads((native_folder / phase['trace_file']).read_text())
    state = expected(phase, trace, phase['device_out']['bank_base'])
    ram = (native_folder / phase['input_ram_file']).read_bytes()
    external = 0
    rows = []
    with tempfile.TemporaryDirectory(prefix='ms5-animation-bank-neg-') as directory:
        work = Path(directory)
        inp, out, ports = (work / n for n in ('input.bin', 'output.bin', 'ports.bin'))
        def reject(label, change=None, resources=(), output=None, payload=None, error=''):
            st = dict(state, **(change or {}))
            data = ram if payload is None else payload
            inp.write_bytes(data); out.write_bytes(b'old RAM'); ports.write_bytes(b'old ports')
            destinations = (out if output is None else output, ports)
            protected = {p: p.read_bytes() for p in (inp, out, ports) + tuple(resources) if p.is_file()}
            run = sound.invoke(exe, st, external, inp, *destinations, resources)
            assert run.returncode != 0 and not run.stdout and error in run.stderr, (label, run.stderr)
            assert all(p.read_bytes() == before for p, before in protected.items()), label
            rows.append(dict(label=label, error=run.stderr.strip(), files_preserved=True))
        reject('bank-parser-negative', dict(current_bank_base=-1), error='invalid continuation at argument 22')
        reject('bank-parser-overflow', dict(current_bank_base=0x100000000), error='invalid continuation at argument 22')
        ready = row['phases'][-1]
        ready_ram = (native_folder / ready['input_ram_file']).read_bytes()
        reject('late-next-fetch-after-sound-release', dict(saved_a1=0x110000), payload=ready_ram,
            error='partial fixed animation script read')
        copy = work / 'resource.ms5d'
        copy.write_bytes((root / 'extracted/runtime/animation_control/control_04276c.ms5d').read_bytes())
        reject('resource-output-alias', resources=(copy,), output=copy, error='resources must be distinct')
        packed = bytearray(copy.read_bytes()); packed[-1] ^= 1; copy.write_bytes(packed)
        reject('corrupt-supplied-unused-resource', resources=(copy,), error='CRC')
    return rows


def main():
    root = Path(__file__).resolve().parents[1]
    exe = root / 'build/step_animation_sound_execution'
    if len(sys.argv) > 1:
        assert len(sys.argv) == 3 and sys.argv[1] == '--exe'
        exe = Path(sys.argv[2]).resolve()
    folder = root / 'artifacts/animation_bank_state_execution'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder / 'verification.json'
    report_path.unlink(missing_ok=True)
    for old in folder.glob('case_*'):
        old.unlink()
    program, source = original.load_verified_program(root)
    rom = root / source['path']
    rom_before = (digest(rom), rom.stat().st_mtime_ns)
    assert original.sha(program) == original.SOURCE_SHA256 == source['sha256']
    native, artifacts, replay_counts = audit(root, program, source)
    names = ['tools/verify_animation_bank_state.py', 'tools/observe_animation_bank_state.py',
        'tools/verify_animation_sound_execution.py', 'tools/verify_animation_execution.py', 'tools/address_map.py',
        'tools/pack_animation_control.py', 'docs/analysis/animation-bank-state-contract.md', 'Makefile',
        'engine/src/animation_execution.cpp', 'engine/include/ms5/animation_execution.h',
        'engine/tools/step_animation_sound_execution.cpp', 'engine/src/animation_resource.cpp',
        'engine/include/ms5/animation_resource.h', 'engine/src/fixed_data_resource.cpp',
        'engine/include/ms5/fixed_data_resource.h', 'engine/src/object_sound_lookup.cpp',
        'engine/include/ms5/object_sound_lookup.h', 'engine/src/sound_word_execution.cpp',
        'engine/include/ms5/sound_word_execution.h', 'engine/src/sound_byte_execution.cpp',
        'engine/include/ms5/sound_byte_execution.h', 'engine/src/sprite_submit_execution.cpp',
        'engine/include/ms5/sprite_submit_execution.h', 'engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h', 'engine/include/ms5/video_port.h',
        'extracted/runtime/animation_control/control_04276c.ms5d']
    resource = root / names[-1]
    assert validate_container(resource.read_bytes()) == program[0x4276c:0x5276c]
    # Include indirectly imported repository helpers (including FIELDS/strict-parser providers).
    imported_helpers = []
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        if path.suffix == '.py' and root / 'tools' in path.parents:
            imported_helpers.append(str(path.relative_to(root)))
    names = sorted(set(names + imported_helpers))
    inputs = {name: digest(root / name) for name in names}
    inputs[source['path']] = rom_before[0]
    executable_name = str(exe.relative_to(root)) if root in exe.parents else str(exe)
    inputs[executable_name] = digest(exe)
    assert exe.stat().st_mtime_ns >= max((root / n).stat().st_mtime_ns for n in names if n.startswith('engine/') or n == 'Makefile'), 'Stale CLI; rebuild outside verifier'
    counts = collections.Counter()
    rows = []
    native_folder = root / 'artifacts/animation_bank_state_native'
    for row in native['results']:
        case, index = row['fixture'], row['case_index']
        ram, registers, details = original.fixture(case, index, program)
        state = sound.initial(registers, case['device_in']['bank_base'])
        external = 0
        device = dict(case['device_in'])
        for position, phase in enumerate(row['phases']):
            if position:
                ram, external = apply_changes(ram, phase['host_changes'], external)
                counts['resumes_from_previous_actual_CPP_output'] += 1
            assert ram == (native_folder / phase['input_ram_file']).read_bytes()
            prefix = 'case_%04d_%s' % (index, phase['phase'])
            inp, out, ports, state_path = (folder / (prefix + suffix) for suffix in ('_input.bin', '_cpp.bin', '_ports.bin', '_state.json'))
            inp.write_bytes(ram)
            resources = [resource] if position == 0 else []
            run = sound.invoke(exe, state, external, inp, out, ports, resources)
            assert run.returncode == 0, (index, phase['phase'], run.stderr)
            actual = sound.parse(run.stdout)
            trace = json.loads((native_folder / phase['trace_file']).read_text())
            native_ports = (native_folder / phase['ports_file']).read_bytes()
            device, _ = independent_device(device, native_ports)
            want = expected(phase, trace, device['bank_base'])
            assert actual == want, (index, phase['phase'], actual, want)
            output = out.read_bytes()
            assert output == (native_folder / phase['ram_file']).read_bytes() and len(output) == 65536
            assert ports.read_bytes() == native_ports and inp.read_bytes() == ram
            if phase['phase'] in ('hold', 'low_hold'):
                assert output == ram and not native_ports and actual['external_reads'] == 0
                assert actual['current_bank_base'] == state['current_bank_base']
            state_path.write_text(run.stdout)
            files = {str(p.relative_to(root)): digest(p) for p in (inp, out, ports, state_path)}
            artifacts.update(files)
            rows.append(dict(case_index=index, phase=phase['phase'], result=actual, files=files,
                previous_actual_CPP_output_carried=bool(position), host_changes=phase['host_changes'],
                external_status_passed=external, resources_passed=[str(p.relative_to(root)) for p in resources]))
            counts['phases'] += 1; counts['ports'] += len(native_ports) // 9
            counts['external_reads'] += actual['external_reads']; counts['phase4_outputs'] += actual['phase'] == 4
            state = {k: v for k, v in actual.items() if k not in ('carry', 'external_reads')}
            ram = output
    assert counts['phases'] == native['phases'] and counts['ports'] == native['total_native_ports']
    assert counts['resumes_from_previous_actual_CPP_output'] == replay_counts['resumes']
    assert counts['external_reads'] == native['total_external_reads']
    rejected = negatives(root, exe, native)
    for name, value in {**inputs, **artifacts}.items():
        path = Path(name) if name.startswith('/') else root / name
        assert digest(path) == value, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_before
    assert original.oracle_provenance() == native['oracle']
    report = dict(source=source, oracle=native['oracle'], inputs=inputs, native_and_CPP_artifacts=artifacts,
        native_observation_sha256=NATIVE_SHA, cases=native['cases'], phases=counts['phases'],
        original_phases_reexecuted=replay_counts['phases'], previous_actual_CPP_output_resumes=replay_counts['resumes'],
        ports=counts['ports'], external_reads=counts['external_reads'], phase4_outputs=counts['phase4_outputs'],
        native_guard_controls_replayed=native['guard_controls'], negative_cases=rejected, results=rows,
        bank_expectation='Independent address_map.pvc_bank_update per actual original WORD port write, full ff8/ff9 side effects; not RAM shadow or physical device measurement.',
        ROM_unchanged=True, opcode40_claim=False,
        limits='Synthetic live-RAM scripts, canonical A5 and A6=100010 shadow alias; only1c/01,14/03 actual RTS3679e,30 sound and28 terminal. No banked ROM read, natural IRQ/Z80, timing, fullCCR or arbitrary PVC sequence claim. File preservation after failure does not prove internal API rollback; separate C++ units cover it.')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=report['cases'], phases=report['phases'], resumes=report['previous_actual_CPP_output_resumes'],
        ports=report['ports'], negatives=len(rejected), sha256=digest(report_path))))


if __name__ == '__main__':
    main()
