"""Original HUD/counter/palette/video stack execution vs the public machine API.

Controlled fixtures; no native SR reads or expected-state injection. Legacy
native observations remain immutable. Video is modeled as ordered port writes.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_hud_execution'
NATIVE_SHA = '41408a8aa9f6f47468632aca987db6f8fb773660ae2e78b4990a0545ff536a72'
NATIVE_TOOL_SHA = '715b9631674bf3a5cafa13b9254d45398448de6ac67f891376fac63d3a1619fe'


def digest(path):
    return helpers.digest(path)


def fold_outputs(pvc, bank, events):
    """Independent PVC effects plus raw native video writes in total order."""
    ports = []
    for event in events:
        if event['access'] != 'write':
            continue
        address, size = event['address'], event['size']
        if 0x2fe000 <= address < 0x300000:
            pvc, bank, encoded = common.fold_device(pvc, bank, [event])
            assert len(encoded) == 9
            ports.append(encoded)
        elif event['region'] == 'video':
            assert address == 0x3c0000 and size in (2, 4)
            raw = bytes.fromhex(event['bytes'])
            assert len(raw) == size
            ports.append(struct.pack('>BII', size, address, int.from_bytes(raw, 'big')))
    return pvc, bank, b''.join(ports)


def compare(exe, records, resources):
    rows = []
    resumes = waits = ports_count = reads = known_carry = 0
    for i, (selection, fx, phases) in enumerate(records):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
        ram, pvc, bank = fx['ram'], fx['pvc'], fx['bank_base']
        expected_pvc, expected_bank = pvc, bank
        results = []
        for j, phase in enumerate(phases):
            if j:
                changed = bytearray(ram)
                for change in phase['host_changes']:
                    at, size = change['address'] & 65535, change['size']
                    assert 0 <= at <= 65536 - size
                    if 'before' in change:
                        assert changed[at:at + size].hex() == change['before']
                    common.native.put(changed, change['address'], size, change['value'])
                ram = bytes(changed)
                resumes += 1
            else:
                assert not phase['host_changes']
            assert {key: state[key] for key in common.REGS + ('pc',)} == phase['incoming']
            assert ram == phase['ram_before']
            expected_pvc, expected_bank, portbytes = fold_outputs(expected_pvc, expected_bank, phase['events'])
            assert expected_bank == phase['modeled_bank']
            stop = phase.get('stop_pc', fx['stop_pc'])
            actual = common.invoke(exe, OUT, 'case_%03d_phase_%02d' % (i, j),
                                   ram, state, pvc, bank, resources, stop=stop, external=fx['external'])
            common.check_result(actual, phase, expected_pvc, expected_bank, portbytes)
            result, ram, pvc, _, _ = actual
            # Non-None native carry tags must first be independently established
            # from executed original BCC successors by audit_native below.
            if phase.get('carry') is not None:
                assert result['carry'] == phase['carry']
                known_carry += 1
            state = {key: result[key] for key in common.STATE_KEYS}
            bank = result['bank_base']
            waits += phase['waiting']
            reads += result['external_reads']
            ports_count += len(portbytes) // 9
            results.append(dict(label=phase['label'], carry=result['carry'],
                                actual_previous_outputs_used=bool(j),
                                full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
        rows.append(dict(index=i, selection=selection, phases=results))
    return dict(cases=len(rows), phases=sum(len(row['phases']) for row in rows),
                previous_actual_CPP_resumes=resumes, waits=waits, ports=ports_count,
                external_reads=reads, known_carry_phase_checks=known_carry, matches=rows)


def audit_native(program, source):
    import observe_animation_machine_hud as native
    folder = ROOT / 'artifacts/animation_machine_hud_native'
    path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA, 'native freeze required'
    assert digest(path) == NATIVE_SHA
    assert digest(ROOT / 'tools/observe_animation_machine_hud.py') == NATIVE_TOOL_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False
    refs = helpers.audit_references(ROOT, folder, report)
    refs[str(path.resolve())] = NATIVE_SHA
    assert native.unicorn.__version__ == report['oracle']['version']
    assert digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((folder / 'source.json').read_text())
    assert static['source'] == source
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes.fromhex(instruction['raw']) == program[at:at + size]
    assert static['raw_HUD_window']['sha256'] == hashlib.sha256(program[0x4e272:0x4e292]).hexdigest()
    saved_rows = {row['index']: row for row in report['results'] + report['guarded_results']}
    selections = native.matrix(program)
    assert len(saved_rows) == len(selections)
    records, guards = [], []
    split_count = control_count = normal_control_count = 0
    def payloads(index, phases, saved, prefix):
        assert len(phases) == len(saved)
        for j, (phase, row) in enumerate(zip(phases, saved)):
            for key in ('label', 'stop_pc', 'incoming', 'outgoing', 'waiting',
                        'carry', 'host_changes', 'modeled_bank', 'guard'):
                assert phase[key] == row[key], (index, j, key)
            assert row['external_reads'] == sum(e['region'] == 'external' for e in phase['events'])
            stem = '%s_%03d_phase_%02d' % (prefix, index, j)
            ports = [e for e in phase['events'] if e['region'] in ('pvc', 'video')]
            data = {stem + '_ram_before.bin': phase['ram_before'], stem + '_ram_after.bin': phase['ram_after'],
                    stem + '_pvc_before.bin': phase['pvc_before'], stem + '_pvc_after.bin': phase['pvc_after'],
                    stem + '_ports.bin': b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports),
                    stem + '_trace.json': (json.dumps({k: phase[k] for k in ('pcs', 'events', 'boundaries', 'guard')}, indent=2) + '\n').encode()}
            assert len(phase['snapshots']) == len(row['snapshots'])
            for k, (snapshot, snapshot_row) in enumerate(zip(phase['snapshots'], row['snapshots'])):
                assert snapshot['registers'] == snapshot_row['registers']
                names = {field: stem + '_snapshot_%02d_%s.bin' % (k, field) for field in ('ram', 'pvc')}
                assert names == snapshot_row['artifacts']
                for field, name in names.items():
                    data[name] = snapshot[field]
            assert set(data) == set(row['artifacts'])
            for name, value in data.items():
                assert (folder / name).read_bytes() == value, name
                assert hashlib.sha256(value).hexdigest() == row['artifacts'][name]
    def flattened(phases):
        pcs, events, changes = [], [], []
        for phase in phases:
            pcs.extend(phase['pcs'][:-1]);events.extend(phase['events']);changes.extend(phase['host_changes'])
        return pcs + phases[-1]['pcs'][-1:], events, changes
    for i, selection in enumerate(selections):
        normalized, fx, split = native.run_case(program, selection)
        other, other_fx, control = native.run_case(program, selection, continuous=True)
        saved = saved_rows[i]
        assert normalized == other == saved['selection'] and fx == other_fx
        assert saved['fixture'] == {k: v for k, v in fx.items() if k not in ('ram', 'pvc', 'regs')}
        assert saved['reproduced_twice'] and saved['continuous_split_equivalent']
        payloads(i, split, saved['phases'], 'case')
        payloads(i, control, saved['continuous_control'], 'control')
        assert flattened(split) == flattened(control)
        for key in ('outgoing', 'ram_after', 'pvc_after', 'guard'):
            assert split[-1][key] == control[-1][key]
        checkpoints = {p['outgoing']['pc']: (p['outgoing'], p['ram_after'], p['pvc_after'])
                       for p in split if not p['waiting'] and p['outgoing']['pc'] != split[-1]['outgoing']['pc']}
        seen = set()
        for phase in control:
            for snapshot in phase['snapshots']:
                pc = snapshot['registers']['pc']
                assert pc not in seen and checkpoints[pc] == (snapshot['registers'], snapshot['ram'], snapshot['pvc'])
                seen.add(pc)
        assert seen == set(checkpoints)
        if selection.get('branch'):
            assert program[0x47d42:0x47d46] == bytes.fromhex('6400002e')
            assert 0x47d42 in flattened(split)[0]
            successor = split[-1]['outgoing']['pc']
            assert successor in (0x47d72, 0x47d46)
            carry = 1 if successor == 0x47d72 else 2
        else:
            carry = None
        for phase in split + control:
            expected = carry if phase['outgoing']['pc'] in (0x47d42, 0x47d72, 0x47d46) else None
            assert phase['carry'] == expected
        if selection.get('guarded'):
            assert split[-1]['guard'] is not None
            guards.append((normalized, fx, split))
        else:
            assert all(phase['guard'] is None for phase in split + control)
            records.append((normalized, fx, split));normal_control_count += len(control)
        split_count += len(split);control_count += len(control)
    assert len(records) == report['cases'] and len(guards) == report['guarded_cases']
    assert split_count == report['total_split_phases'] and control_count == report['total_control_phases']
    assert sum(len(x[2]) for x in records) == report['phases']
    assert normal_control_count == report['continuous_control_phases']
    assert report['fresh_CPU_runs'] == 4 * len(selections)
    assert report['phase_executions'] == 2 * (split_count + control_count)
    return records, guards, refs, control_count


def compare_guards(exe, guards, resources):
    rows = []
    for i, (selection, fx, phases) in enumerate(guards):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        actual = common.invoke(exe, OUT, 'native_guard_%03d' % i, fx['ram'], state,
                               fx['pvc'], fx['bank_base'], resources, stop=fx['stop_pc'], external=fx['external'])
        result, ram, pvc, ports, error = actual
        cause = 'unaligned animation machine PC' if selection.get('palette_stack_alias') else (
            'unsupported original rectangle TRAP15' if selection['group'] == 'rectangle' else 'even WORD/LONG')
        assert not result['ok'] and cause in error, (selection, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state
        assert ram == fx['ram'] and pvc == fx['pvc'] and result['bank_base'] == fx['bank_base']
        assert ports == struct.pack('>BII', 1, 0xdeadbeef, 0x87)
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(selection=selection, native_guard=phases[-1]['guard'],
                         native_outgoing=phases[-1]['outgoing'], checked_API_error=error,
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows


# Superseded expectations (final state): the successor 480bc / its callees are executable now (U1..U7), so these runs go on and end in a state-dependent
# bus error instead of an unsupported-PC rollback. Labels are kept; former and observed errors are recorded in the report (superseded_negatives).
SUPERSEDED_CAUSES = {'whole_upper_ports_before_unsupported_stop': 'program bus requires even WORD/LONG address'}
SUPERSEDED_NEGATIVES = []


def negatives(exe, records, resources, program):
    rows = []
    base = next(fx for selection, fx, phases in records if fx['entry_pc'] == 0x4e286)
    marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
    def reject(label, changes, cause, memory=(), selected=None, fx=None):
        fx = base if fx is None else fx
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        state.update(changes)
        ram = bytearray(fx['ram'])
        for address, size, value in memory:
            common.native.put(ram, address, size, value)
        actual = common.invoke(exe, OUT, 'negative_' + label, bytes(ram), state,
                               fx['pvc'], fx['bank_base'], resources if selected is None else selected,
                               stop=0xff000, external=fx['external'])
        result, outgoing, pvc, ports, error = actual
        if label in SUPERSEDED_CAUSES:
            SUPERSEDED_NEGATIVES.append(dict(label=label, former_expected_API_error=cause, observed_final_state_error=SUPERSEDED_CAUSES[label],
                                             all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
            cause = SUPERSEDED_CAUSES[label]
        assert not result['ok'] and cause in error, (label, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state
        assert outgoing == ram and pvc == fx['pvc'] and ports == marker
        assert result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=label, error=error, all_API_outputs_preserved=True,
                         native_exception_rollback_equivalence_claimed=False))
    # F5 queues nonphysical read addresses; this synthetic gate read has no queued value.
    reject('HUD_gate_device', {'pc': 0x4e286, 'a5': 0x2fa2e1},
           'animation machine external read queue empty')
    reject('HUD_counter_write_before_odd_saved_WORD_push',
           {'pc': 0x4e286, 'a5': 0x108000, 'a7': 0x1feffd, 'd0': 1},
           'even WORD/LONG', memory=((0x10dd1f, 1, 1), (0x10dd20, 1, 0)))
    reject('palette_writes_before_bad_live_RTS',
           {'pc': 0x8cda, 'd0': 12, 'd1': 0x12340a0d, 'd2': 4},
           'unsupported animation frame head h8 PC',
           memory=((0x104e5a, 2, 1), (0x104e5e, 2, 0x2222),
                   (base['initial_a7'], 4, 0xdeac)))
    reject('rectangle_TRAP_after_first_video_port',
           {'pc': 0x35f0, 'd0': 0x74ff, 'd1': 0, 'd2': 1, 'd3': 2},
           'unsupported original rectangle TRAP15')
    reject('rectangle_zero_height_follows_WORD_decrement_until_TRAP',
           {'pc': 0x35f0, 'd0': 0x7243, 'd1': 0, 'd2': 1, 'd3': 0},
           'unsupported original rectangle TRAP15')
    reject('rectangle_ports_before_bad_live_RTS',
           {'pc': 0x35f0, 'd0': 0x7243, 'd1': 0xc904, 'd2': 2, 'd3': 2},
           'unsupported animation frame head h8 PC', memory=((base['initial_a7'], 4, 0xdeac),))
    reject('rectangle_unsupported_live_A4',
           {'pc': 0x35fe, 'a4': 0x3c0002, 'd7': 0x7243c904, 'd6': 1, 'd2': 1},
           'unsupported animation machine write device')
    reject('BCD_two_BYTE_writes_before_bad_live_RTS',
           {'pc': 0x4843c, 'a5': 0x108000}, 'unsupported animation frame head h8 PC',
           memory=((0x10d683, 1, 0x10), (0x10fdb6, 1, 1), (0x10fdb7, 1, 0),
                   (0x10d67e, 2, 0x0100), (base['initial_a7'], 4, 0xdeac)))
    reject('HUD_second_saved_WORD_odd_pop', {'pc': 0x4e312, 'a7': 0x1feffd}, 'even WORD/LONG')
    reject('readiness_Unknown_branch', {'pc': 0x47d42, 'carry': 0}, 'readiness caller requires known carry')
    # Only the second digit's WORD is absent; first lookup and rectangle remain
    # original bytes. These valid kind3 negative resources are immutable slices.
    import pack_physical_program as physical
    selected = [path for path in resources
                if struct.unpack_from('<I', Path(path).read_bytes(), 16)[0] != 0]
    for start, end in ((0, 0x4e276), (0x4e278, 0x100000)):
        path = OUT / ('negative_lookup_%06x_%06x.ms5d' % (start, end))
        path.write_bytes(physical.wrap(program[start:end], start))
        assert physical.validate_container(path.read_bytes()) == program[start:end]
        selected.append(path)
    reject('second_digit_missing_after_palette_and_first_rectangle',
           {'pc': 0x4e286, 'a5': 0x108000, 'd0': 0x1200},
           'missing or ambiguous physical program bus ROM byte',
           memory=((0x10dd1f, 1, 1), (0x104e5a, 2, 1), (0x104e5e, 2, 0x2222)), selected=selected)
    upper = next(fx for selection, fx, phases in records
                 if fx['entry_pc'] == 0x47c6c and not any(phase['waiting'] for phase in phases)
                 and any(event['region'] == 'video' for phase in phases for event in phase['events']))
    reject('whole_upper_ports_before_unsupported_stop', {}, 'unsupported animation machine PC', fx=upper)
    return rows


def zero_step(exe, resources, fx):
    rows = []
    for pc in (0x4e2f0, 0x4e312, 0x47c80):
        for carry in (0, 1, 2):
            state = dict(fx['regs'], a7=fx['initial_a7'], pc=pc, carry=carry)
            result, ram, pvc, ports, error = common.invoke(exe, OUT, 'zero_%06x_%d' % (pc, carry),
                fx['ram'], state, fx['pvc'], fx['bank_base'], resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0
            assert {key: result[key] for key in common.STATE_KEYS} == state
            assert ram == fx['ram'] and pvc == fx['pvc'] and result['bank_base'] == fx['bank_base']
            assert result['external_reads'] == 0 and not ports
            rows.append(dict(pc=pc, carry=carry, all_input_state_preserved=True))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    import observe_animation_machine_hud as native
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_hud.py',
                 'docs/analysis/animation-machine-hud-contract.md',
                 'engine/tests/animation_machine_hud_test.cpp'):
        inputs[name] = digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    records, guards, native_refs, control_count = audit_native(program, source)
    refs.update(native_refs)
    exe, command = helpers.compile_harness(ROOT, OUT)
    matches = compare(exe, records, resources)
    guarded = compare_guards(exe, guards, resources)
    negative = negatives(exe, records, resources, program)
    zero = zero_step(exe, resources, records[0][1])
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert digest(ROOT / name) == expected, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update({str(path.resolve()): digest(path) for path in OUT.iterdir()
                 if path.is_file() and path != report_path})
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in unique or unique[key] == expected
        unique[key] = expected
    report = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  actual_CPP=matches, native_guards_checked_API=guarded,
                  native_continuous_control_phases_replayed=control_count,
                  superseded_negatives=SUPERSEDED_NEGATIVES, negatives=negative, negative_count=len(negative) + len(guarded), zero_step=zero,
                  harness_JSON_keys=22, normalized_reference_paths=len(unique),
                  compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled original HUD/palette/rectangle/counter/upper fixtures; no natural gameplay or scheduler reachability claim.',
                          'Native has no SR reads; known carry only from actual original branch direction. No general CCR/timing/IRQ or hardware proof.',
                          'Video is ordered register-port output; no rendered VRAM/pixel behavior claim. PVC device effects independently fold original ordered writes.',
                          'Resumes forward previous actual C++ outputs plus declared host RAM changes; native incoming is only an assertion.',
                          'Checked failures preserve API outputs, not original CPU fault rollback or filesystem atomic I/O.'])
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=matches['cases'], phases=matches['phases'],
                         resumes=matches['previous_actual_CPP_resumes'], negatives=len(negative) + len(guarded),
                         sha256=digest(report_path))))


if __name__ == '__main__':
    main()
