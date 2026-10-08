"""Actual opcode30 direct-sound C++ CLI versus the immutable full original native observer.

Independent of the old sound-callback verifier except for shared helpers (state/argument layout, JSON parser).
Every original case and phase is replayed with the Unicorn observer (including recorded host changes) and compared
with the saved native artifacts; the C++ CLI is then run on the same cases feeding only its OWN previous output
RAM/state plus the recorded host changes. Usage: verify_animation_direct_sound.py [--exe CLI] [--general-exe CLI].
"""
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import observe_animation_direct_sound as direct
import verify_animation_execution as general
import verify_animation_sound_execution as sound

NATIVE_SHA = '4ef6c7dd0ea871f98dacf1145e1a57fabdffb3ef587cfe3ec8cf55c7871c9386'
EXPECTED = dict(cases=207, phases=255, pending_chains=18, ports=828, external_reads=17)
LABELS = {'none': ['begin'], 'high': ['begin', 'hold', 'ready'], 'low': ['begin', 'hold', 'ready'],
    'high_to_low': ['begin', 'hold', 'mid', 'low_hold', 'ready'],
    'sequential': ['begin', 'hold', 'first_ready_second_waits', 'second_hold', 'ready']}
HOLDS = ('hold', 'low_hold', 'second_hold')
REPORT = Path('/tmp/ms5-direct-verifier-report.txt')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_state(info, trace):
    """Native phase -> expected CLI JSON (phase 4 contract; saved_bank/list_end/callback_saved_a0 are 0)."""
    result = sound.initial(info['result'])
    if info['waiting']:
        pending = info['pending']
        result.update(phase=4, saved_a0=pending['outer_a0'], saved_a1=pending['outer_a1'], saved_bank=0, saved_list_end=0,
            waiting=False, callback_saved_a0=0, callback_sound_phase=pending['sound_phase'],
            callback_saved_low=pending['saved_low'], callback_waiting=True)
        result['carry'] = None
    else:
        assert info['pending'] is None
        result['carry'] = info['carry']
    reads = sum(read['kind'] == 'external' for read in trace['reads'])
    assert reads == info['external_reads']
    result['external_reads'] = reads
    return result


def parse(text):
    result = sound.parse(text)
    if result['phase'] == 4:
        assert result['saved_bank'] == 0 and result['saved_list_end'] == 0 and result['callback_saved_a0'] == 0
        assert not result['waiting'] and result['callback_waiting'] and result['callback_sound_phase'] in (1, 2)
    return result


def apply_changes(ram, changes, external):
    """Recorded host writes: RAM bytes, or the one external status byte at 0xd00046."""
    data = bytearray(ram)
    for change in changes:
        if change['address'] == direct.EXTERNAL:
            assert change['size'] == 1
            external = change['value']
            continue
        at = change['address'] - direct.BASE
        assert 0 <= at and at + change['size'] <= 65536
        data[at:at + change['size']] = change['value'].to_bytes(change['size'], 'big')
    return bytes(data), external


def audit(root, program, source):
    folder = root / 'artifacts/animation_direct_sound_native'
    path = folder / 'observation.json'
    assert digest(path) == NATIVE_SHA, ('native observation.json changed', digest(path))
    native = json.loads(path.read_text())
    assert native['source'] == source and native['oracle'] == direct.oracle_provenance()
    assert native['original_program_modified'] is False and native['in_call_SR_read'] is False
    assert native['Cpp_comparison_performed'] is False and native['failure'] is None and native['entry_pc'] == direct.ENTRY
    hashes = {str(path.relative_to(root)): digest(path)}
    for name, value in native['inputs'].items():
        assert digest(root / name) == value, name
        hashes[name] = value
    static = json.loads((folder / 'source.json').read_text())
    assert static['source'] == source
    branches = set()
    for start, end in static['ranges']:
        cursor = start
        for row in static['instructions']:
            if start <= row['cpu_address'] < end:
                assert row['cpu_address'] == row['rom_offset'] == cursor
                assert bytes.fromhex(row['raw']) == program[cursor:cursor + row['size']]
                cursor += row['size']
                if row['mnemonic'].startswith('b') and not row['mnemonic'].startswith(('bra', 'bsr', 'btst', 'bclr')):
                    branches.add(row['cpu_address'])
        assert cursor == end
    cases = direct.cases()
    assert len(cases) == len(native['results']) == native['cases'] == EXPECTED['cases']
    observer = direct.Observer(program, branches)
    referenced = set()
    counts = collections.Counter()
    for index, (case, row) in enumerate(zip(cases, native['results'])):
        assert row['case_index'] == index and row['fixture'] == case
        ram, regs, details = direct.fixture(case, index)
        assert json.loads(json.dumps(details)) == row['details']
        observer.prepare(ram, regs, case['external'])
        assert [phase['phase'] for phase in row['phases']] == LABELS[case['chain']], (index, case['chain'])
        for position, phase in enumerate(row['phases']):
            if position:
                observer.mutate(phase['host_changes'])
                counts['resumes'] += 1
            else:
                assert not phase['host_changes']
            info, before, output, ports, trace = observer.run()
            direct.check_phase(case, details, info, trace, not position)
            assert all(phase[key] == value for key, value in info.items()), (index, phase['phase'])
            assert phase['callee_exits'] == direct.summarize_calls(trace)
            assert phase['after_call'] == direct.restoration(trace)
            assert phase['callee_entries'] == sum(b['pc'] == 0x3af8 for b in trace['boundaries'])
            assert before == (folder / phase['input_ram_file']).read_bytes()
            assert output == (folder / phase['ram_file']).read_bytes()
            assert ports == (folder / phase['ports_file']).read_bytes()
            assert trace == json.loads((folder / phase['trace_file']).read_text())
            assert phase['port_count'] == len(ports) // 9
            assert set(phase['files']) == {phase[k] for k in ('input_ram_file', 'ram_file', 'ports_file', 'trace_file')}
            for name, value in phase['files'].items():
                assert digest(folder / name) == value, name
                hashes[str((folder / name).relative_to(root))] = value
                referenced.add(name)
            if phase['waiting']:
                assert phase['final_pc'] == direct.WAIT and phase['carry'] is None and phase['pending'] is not None
            else:
                assert phase['final_pc'] == direct.RETURN and phase['final_a7'] == direct.STACK + 4 and phase['pending'] is None
            counts['phases'] += 1
            counts['ports'] += len(ports) // 9
            counts['external_reads'] += info['external_reads']
    actual_files = {p.name for p in folder.glob('case_*')}
    assert actual_files == referenced, sorted(actual_files ^ referenced)[:5]
    assert counts['phases'] == native['phases'] == EXPECTED['phases']
    assert counts['ports'] == native['total_native_ports'] == EXPECTED['ports']
    assert counts['external_reads'] == native['total_external_reads'] == EXPECTED['external_reads']
    assert native['pending_chains'] == EXPECTED['pending_chains'] and counts['resumes'] > 0
    return native, hashes, counts


def invoke(exe, state, external, inp, out, ports, resources):
    return sound.invoke(exe, state, external, inp, out, ports, resources)


def negatives(root, folder, exe, general_exe, native, native_folder, program):
    """Checked rejections. CLI file preservation is observable behaviour only; source-level rollback is covered
    by the C++ unit tests, not by these cases."""
    chain = next(row for row in native['results'] if row['fixture']['chain'] == 'high')
    begin, hold, ready = chain['phases']
    details = chain['details']
    fixture_ram, regs, _ = direct.fixture(chain['fixture'], chain['case_index'])
    begin_state = sound.initial(regs)
    begin_ram = (native_folder / begin['input_ram_file']).read_bytes()
    pending = expected_state(begin, json.loads((native_folder / begin['trace_file']).read_text()))
    pending.pop('carry')
    pending.pop('external_reads')
    pending_ram = (native_folder / begin['ram_file']).read_bytes()
    ready_ram = (native_folder / ready['input_ram_file']).read_bytes()
    ready_trace = json.loads((native_folder / ready['trace_file']).read_text())
    ready_external = chain['fixture']['external']
    for change in hold['host_changes']:
        if change['address'] == direct.EXTERNAL:
            ready_external = change['value']
    # Late failures are only meaningful if the successful twin really performed sound writes before the restore.
    assert any(w['pc'] == 0x3af0 for w in ready_trace['ordered_writes'])
    assert any(w['pc'] == 0x4a278 for w in ready_trace['ordered_writes'])
    cursor_after = details['commands'][0]['cursor_after']
    assert pending['saved_a0'] == details['outer_a0'] and pending['saved_a1'] == cursor_after
    rows = []
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work = Path(temporary)
        inp, out, ports = (work / name for name in ('input', 'output', 'ports'))
        sentinel = b'preserved-output'

        def reject(label, error, st=begin_state, payload=begin_ram, external=0, source=None, destinations=None,
                   resources=(), command=None, new_outputs=()):
            inp.write_bytes(payload)
            out.write_bytes(sentinel)
            ports.write_bytes(sentinel)
            source = inp if source is None else source
            destinations = (out, ports) if destinations is None else destinations
            watched = {path: path.read_bytes() for path in [inp, out, ports, source] + list(destinations) + list(resources)
                       if path.exists() and path.is_file()}
            if command is None:
                result = invoke(exe, st, external, source, destinations[0], destinations[1], list(resources))
            else:
                result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            assert result.returncode != 0 and not result.stdout, (label, result.returncode, result.stdout, result.stderr)
            assert error in result.stderr, (label, error, result.stderr)
            assert all(path.read_bytes() == data for path, data in watched.items()), label
            for path in new_outputs:
                assert not path.exists(), (label, path)
            rows.append(dict(label=label, expected_error=error, error=result.stderr.strip(), files_preserved=True))

        def general_reject(label, error, st, payload):
            inp.write_bytes(payload)
            out.write_bytes(sentinel)
            ports.write_bytes(sentinel)
            result = general.invoke(general_exe, st, inp, out, ports, [])
            assert result.returncode != 0 and not result.stdout and error in result.stderr, (label, result.stderr)
            assert out.read_bytes() == sentinel and ports.read_bytes() == sentinel and inp.read_bytes() == payload
            rows.append(dict(label=label, expected_error=error, error=result.stderr.strip(), files_preserved=True,
                general_cli=True))

        # Invalid phase4 / direct-sound metadata (library validity check).
        invalid = 'invalid animation RAM or continuation'
        for label, change in (('sprite-waiting', dict(waiting=True)), ('saved-bank', dict(saved_bank=1)),
                ('saved-list-end', dict(saved_list_end=1)), ('callback-saved-a0', dict(callback_saved_a0=2)),
                ('callback-waiting-false', dict(callback_waiting=False)), ('sound-phase-0', dict(callback_sound_phase=0))):
            reject('phase4-metadata-' + label, invalid, st=dict(pending, **change), payload=pending_ram)
        reject('phase4-metadata-sound-phase-3', 'invalid continuation at argument', st=dict(pending, callback_sound_phase=3),
            payload=pending_ram)
        reject('phase5', 'invalid continuation at argument', st=dict(pending, phase=5), payload=pending_ram)
        reject('phase0-with-active-direct-sound-metadata', invalid, st=dict(pending, phase=0), payload=pending_ram)
        # Current-model A5 restriction (not an original early-filter claim).
        a5 = 'canonical A5=108000'
        reject('A5-pending-resume', a5, st=dict(pending, a5=0x108002), payload=pending_ram)
        reject('A5-fresh-call', a5, st=dict(begin_state, a5=0x108002), payload=begin_ram)
        # Old general CLI cannot execute opcode30 or accept phase4.
        general_reject('old-CLI-opcode30', 'direct animation sound requires external-input overload',
            general.initial(regs), begin_ram)
        general_reject('old-CLI-phase4', 'invalid continuation', dict(general.initial(regs), phase=4), pending_ram)
        # Late failures after the callee ran: restore through saved A0 / next fetch through saved A1.
        late_a0 = 'aligned complete reached RAM span'
        for label, value in (('odd', details['outer_a0'] | 1), ('below-RAM', 0xffc), ('end-of-RAM', 0x110000),
                ('last-LONG-straddle', 0x10fffe), ('high-wrap', 0xfffffffe)):
            reject('late-restore-saved-A0-' + label, late_a0, st=dict(pending, saved_a0=value), payload=ready_ram,
                external=ready_external)
        reject('late-saved-A1-110000-after-sound-writes', 'partial fixed animation script read',
            st=dict(pending, saved_a1=0x110000), payload=ready_ram, external=ready_external)
        # Missing / odd command WORD for a fresh opcode30.
        outer_pointer = details['outer_a0'] - 0x100000
        for label, address, error in (('odd-word', 0x106001, 'unaligned or overflowing animation script read'),
                ('word-beyond-RAM', 0x10fffe, 'partial fixed animation script read')):
            data = bytearray(begin_ram)
            data[outer_pointer:outer_pointer + 4] = address.to_bytes(4, 'big')
            data[address - 0x100000] = 0x30
            reject('command-' + label, error, payload=bytes(data))
        data = bytearray(begin_ram)
        data[outer_pointer:outer_pointer + 4] = (0xffffffff).to_bytes(4, 'big')
        reject('command-pointer-outside-RAM', 'script read', payload=bytes(data))
        # Input RAM size and file-system hazards.
        for size in (0, 65535, 65537):
            reject('RAM-size-%d' % size, 'RAM must contain exactly 65536 bytes', payload=bytes(size))
        reject('missing-input', 'input RAM must be a regular file', source=work / 'missing')
        reject('input-directory', 'input RAM must be a regular file', source=work)
        reject('output-directory', 'cannot reserve output files', destinations=(work, ports))
        reject('ports-directory', 'cannot reserve output files', destinations=(out, work))
        distinct = 'all input and output files must be distinct'
        reject('input-output-alias', distinct, destinations=(inp, ports))
        reject('input-ports-alias', distinct, destinations=(out, inp))
        reject('same-outputs', distinct, destinations=(out, out))
        for kind in ('hardlink', 'symlink'):
            alias = work / kind
            if kind == 'hardlink':
                os.link(inp, alias)
            else:
                alias.symlink_to(inp)
            reject('input-output-' + kind, distinct, destinations=(alias, ports))
        fifo = work / 'fifo'
        os.mkfifo(fifo)
        reject('FIFO-input', 'input RAM must be a regular file', source=fifo)
        reject('FIFO-output', 'cannot reserve output files', destinations=(fifo, ports))
        reject('FIFO-ports', 'cannot reserve output files', destinations=(out, fifo))
        fresh = work / 'fresh'
        reject('second-reservation-failure-removes-new-first', 'cannot reserve output files', destinations=(fresh, fifo),
            new_outputs=(fresh,))
        # Unneeded resources are still protected from output aliasing; use disposable copies, never real resources.
        copy = work / 'resource-copy.ms5d'
        shutil.copyfile(root / 'extracted/runtime/animation_control/control_04276c.ms5d', copy)
        reject('resource-output-alias', 'resources must be distinct from RAM and outputs', destinations=(copy, ports),
            resources=[copy])
        reject('resource-ports-alias', 'resources must be distinct from RAM and outputs', destinations=(out, copy),
            resources=[copy])
        insensitive = (work / 'INPUT').exists() and os.path.samefile(inp, work / 'INPUT')
        if insensitive:
            reject('casefold-input-output', distinct, destinations=(work / 'INPUT', ports))
    return rows, insensitive


def main():
    root = Path(__file__).resolve().parents[1]
    args = sys.argv[1:]
    exe = root / 'build/step_animation_sound_execution'
    general_exe = root / 'build/step_animation_execution'
    while args:
        flag = args.pop(0)
        if flag == '--exe':
            exe = Path(args.pop(0))
        elif flag == '--general-exe':
            general_exe = Path(args.pop(0))
        else:
            raise SystemExit('usage: verify_animation_direct_sound.py [--exe CLI] [--general-exe CLI]')
    folder = root / 'artifacts/animation_direct_sound_execution'
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob('case_*'):
        old.unlink()
    report_path = folder / 'verification.json'
    report_path.unlink(missing_ok=True)
    native_folder = root / 'artifacts/animation_direct_sound_native'
    program, source = direct.load_verified_program(root)
    rom_path = root / source['path']
    rom_before = (digest(rom_path), rom_path.stat().st_mtime_ns)
    assert direct.sha(program) == direct.SOURCE_SHA256 == source['sha256']
    native, artifacts, native_counts = audit(root, program, source)
    names = ['tools/verify_animation_direct_sound.py', 'tools/verify_animation_sound_execution.py',
        'tools/verify_animation_execution.py', 'tools/observe_animation_direct_sound.py', 'tools/observe_object_sound_lookup.py',
        'tools/observe_animation_sound_callback.py', 'engine/tools/step_animation_sound_execution.cpp',
        'engine/tools/step_animation_execution.cpp', 'engine/src/animation_execution.cpp',
        'engine/include/ms5/animation_execution.h', 'engine/src/object_sound_lookup.cpp',
        'engine/include/ms5/object_sound_lookup.h', 'engine/src/sound_word_execution.cpp',
        'engine/include/ms5/sound_word_execution.h', 'engine/src/sound_byte_execution.cpp',
        'engine/include/ms5/sound_byte_execution.h', 'engine/src/sprite_submit_execution.cpp',
        'engine/include/ms5/sprite_submit_execution.h', 'engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h', 'engine/include/ms5/video_port.h',
        'engine/src/fixed_data_resource.cpp', 'engine/include/ms5/fixed_data_resource.h',
        'engine/src/animation_resource.cpp', 'engine/include/ms5/animation_resource.h', 'Makefile',
        'extracted/runtime/animation_control/control_04276c.ms5d']
    inputs = {name: digest(root / name) for name in names}
    inputs[source['path']] = rom_before[0]
    for label, path in (('sound CLI', exe), ('general CLI', general_exe)):
        assert path.is_file(), label
        inputs[str(path.relative_to(root)) if root in path.parents else str(path)] = digest(path)
    newest_source = max((root / name).stat().st_mtime_ns for name in names if name.startswith('engine/') or name == 'Makefile')
    stale = exe.stat().st_mtime_ns < newest_source or general_exe.stat().st_mtime_ns < newest_source
    assert not stale, 'CLI executable older than engine sources; rebuild first (not done by this verifier)'
    resources = []  # live-RAM scripts and holds need no resources; the unused fixed resource is never passed to successes
    rows = []
    tallies = collections.Counter()
    by_sound_phase = collections.Counter()
    for row in native['results']:
        index = row['case_index']
        case = row['fixture']
        ram, regs, _ = direct.fixture(case, index)
        state = sound.initial(regs)
        external = case['external']
        for position, phase in enumerate(row['phases']):
            if position:
                ram, external = apply_changes(ram, phase['host_changes'], external)
                tallies['resumes_from_previous_actual_CPP_output'] += 1
            assert ram == (native_folder / phase['input_ram_file']).read_bytes(), (index, phase['phase'])
            prefix = 'case_%04d_%s' % (index, phase['phase'])
            inp, out, ports, state_file = (folder / (prefix + suffix) for suffix in
                ('_input.bin', '_cpp.bin', '_ports.bin', '_state.json'))
            inp.write_bytes(ram)
            out.write_bytes(b'old')
            ports.write_bytes(b'old')
            result = invoke(exe, state, external, inp, out, ports, resources)
            assert result.returncode == 0, (index, phase['phase'], result.stderr)
            actual = parse(result.stdout)
            trace = json.loads((native_folder / phase['trace_file']).read_text())
            want = expected_state(phase, trace)
            assert actual == want, (index, phase['phase'], actual, want)
            output = out.read_bytes()
            assert len(output) == 65536
            assert output == (native_folder / phase['ram_file']).read_bytes(), (index, phase['phase'], 'RAM')
            assert ports.read_bytes() == (native_folder / phase['ports_file']).read_bytes(), (index, phase['phase'], 'ports')
            assert inp.read_bytes() == ram
            if phase['phase'] in HOLDS:
                assert output == ram and actual['external_reads'] == 0 and not ports.read_bytes()
            state_file.write_text(result.stdout)
            files = {str(p.relative_to(root)): digest(p) for p in (inp, out, ports, state_file)}
            artifacts.update(files)
            rows.append(dict(case_index=index, phase=phase['phase'], result=actual, files=files,
                host_changes=phase['host_changes'], external_status_passed=external,
                previous_actual_CPP_output_carried=bool(position), port_count=len(ports.read_bytes()) // 9))
            tallies['phases'] += 1
            tallies['ports'] += len(ports.read_bytes()) // 9
            tallies['external_reads'] += actual['external_reads']
            tallies['phase4_outputs'] += actual['phase'] == 4
            if actual['phase'] == 4:
                by_sound_phase[actual['callback_sound_phase']] += 1
            state = dict(actual)
            state.pop('carry')
            state.pop('external_reads')
            ram = output
    assert tallies['phases'] == native['phases'] == EXPECTED['phases']
    assert tallies['ports'] == EXPECTED['ports'] and tallies['external_reads'] == EXPECTED['external_reads']
    assert tallies['resumes_from_previous_actual_CPP_output'] == native_counts['resumes']
    rejected, insensitive = negatives(root, folder, exe, general_exe, native, native_folder, program)
    for name, value in {**inputs, **artifacts}.items():
        path = Path(name) if name.startswith('/') else root / name
        assert digest(path) == value, name
    rom_after = (digest(rom_path), rom_path.stat().st_mtime_ns)
    assert rom_after == rom_before and direct.oracle_provenance() == native['oracle']
    result = dict(source=source, oracle=native['oracle'], native_observation_sha256=NATIVE_SHA, inputs=inputs,
        resources_passed_to_successful_runs=[], native_and_CPP_artifacts=artifacts, cases=native['cases'],
        phases=tallies['phases'], original_phases_reexecuted=native_counts['phases'],
        previous_actual_CPP_output_resumes=tallies['resumes_from_previous_actual_CPP_output'],
        ports=tallies['ports'], external_reads=tallies['external_reads'], phase4_outputs=tallies['phase4_outputs'],
        phase4_outputs_by_sound_phase={str(k): v for k, v in sorted(by_sound_phase.items())},
        chains_by_kind=native['chains_by_kind'], results=rows, negative_cases=rejected,
        case_insensitive_filesystem=insensitive, ROM_unchanged=True,
        scope='Whole unpatched 49fc6 opcode30 (4a2da->3af8) live-RAM scripts and same-CPU high/low/high->low/sequential waits; '
            'all native phases replayed; C++ runs feed only the previous actual C++ RAM/state plus recorded host changes '
            '(including the recorded external status byte). Full 64KiB RAM, 15 registers, 27 output fields incl. phase4 '
            'saved outer A0/A1, callback metadata, carry, ordered PVC ports and external_reads compared.',
        limits='Input A5 restriction is current model support, not an original early-filter claim. Synthetic live-RAM '
            'fixtures only: no MS5A scripts, no resources. CLI file preservation after rejection does not prove source-level '
            'rollback (covered by C++ unit tests). No natural IRQ/Z80, cycle timing, other callbacks or whole-game claim.')
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    summary = dict(cases=result['cases'], phases=result['phases'], resumes=result['previous_actual_CPP_output_resumes'],
        ports=result['ports'], external_reads=result['external_reads'], phase4_outputs=result['phase4_outputs'],
        negative_cases=len(rejected), sha256=digest(report_path))
    lines = ['PASS animation direct sound verifier', json.dumps(summary), 'report: ' + str(report_path.relative_to(root)),
        'native observation sha256: ' + NATIVE_SHA, 'limits: ' + result['limits'], 'hashes:']
    lines += ['  %s  %s' % (value, name) for name, value in sorted(inputs.items())]
    REPORT.write_text('\n'.join(lines) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    started = time.time()
    try:
        main()
    except BaseException:
        REPORT.write_text('FAIL animation direct sound verifier\n' + traceback.format_exc())
        raise
