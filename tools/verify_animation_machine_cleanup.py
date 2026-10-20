"""Original cleanup/helper shared-stack execution vs the public machine API.

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
OUT = ROOT / 'artifacts/animation_machine_cleanup_execution'
NATIVE_SHA = '12b825b02281f215bc554605dffc30c8d1e28d9921ac3a49cc40081df0e7553a'
NATIVE_TOOL_SHA = 'd1e5051a482423c0078b53e958b59ac403cdd294b1d7494befd18de2abd032be'


def digest(path):
    return helpers.digest(path)


def fold_outputs(pvc, bank, events):
    """Independent PVC effects plus native video/watchdog writes in total order."""
    ports = []
    for event in events:
        if event['access'] != 'write':
            continue
        address, size = event['address'], event['size']
        if 0x2fe000 <= address < 0x300000:
            pvc, bank, encoded = common.fold_device(pvc, bank, [event])
            assert len(encoded) == 9
            ports.append(encoded)
        elif event['region'] in ('video', 'watchdog'):
            assert ((address == 0x3c0000 and size in (2, 4)) or
                    (address == 0x3c0004 and size == 2) or
                    (address == 0x300001 and size == 1))
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
            assert actual[0]['ok'] and not actual[4], (selection, phase['label'], actual[4])
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
    import observe_animation_machine_cleanup as native
    folder = ROOT / 'artifacts/animation_machine_cleanup_native'
    path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA, 'native freeze required'
    assert digest(path) == NATIVE_SHA
    assert digest(ROOT / 'tools/observe_animation_machine_cleanup.py') == NATIVE_TOOL_SHA
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
            assert phase['branch_evidence'] == row['branch_evidence']
            assert row['external_reads'] == sum(e['region'] == 'external' for e in phase['events'])
            stem = '%s_%03d_phase_%02d' % (prefix, index, j)
            ports = [e for e in phase['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
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
                       for p in split[:-1] if not p['waiting'] and p['guard'] is None}
        seen = set()
        for phase in control:
            for snapshot in phase['snapshots']:
                pc = snapshot['registers']['pc']
                assert pc not in seen and checkpoints[pc] == (snapshot['registers'], snapshot['ram'], snapshot['pvc'])
                seen.add(pc)
        assert seen == set(checkpoints)
        audit_carry(program, selection, fx, split, control)
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


BRANCHES = {
    0x29c4: (0x29c8, 0x29fe, bytes.fromhex('65000038')),
    0x2a16: (0x2a1e, 0x2a1a, bytes.fromhex('64000006')),
}


def audit_carry(program, selection, fx, split, control):
    # The original executed successor is the oracle, including repeated PCs.
    # A checkpoint stops BEFORE its branch; its later actual decision labels C.
    pcs = []
    for phase in split:
        pcs.extend(phase['pcs'][:-1])
    pcs.extend(split[-1]['pcs'][-1:])
    decisions, at_position = [], {}
    for i, pc in enumerate(pcs[:-1]):
        if pc not in BRANCHES:
            continue
        clear_pc, set_pc, raw = BRANCHES[pc]
        assert program[pc:pc + len(raw)] == raw
        successor = pcs[i + 1]
        assert successor in (clear_pc, set_pc), (hex(pc), hex(successor))
        carry = 1 if successor == clear_pc else 2
        decisions.append(dict(index=i, pc=pc, successor=successor, carry=carry))
        at_position[i] = carry
    for phases in (split, control):
        position = 0
        for phase in phases:
            position += len(phase['pcs']) - 1
            expected = at_position.get(position)
            if fx['entry_pc'] == 0x287e and position and pcs[position - 1] in BRANCHES:
                expected = at_position[position - 1]
            if phase['waiting']:
                expected = None
            assert phase['branch_evidence'] == decisions
            assert phase['carry'] == expected, (selection, phase['label'], expected, phase['carry'])


def compare_guards(exe, guards, resources):
    rows = []
    for i, (selection, fx, phases) in enumerate(guards):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        result, ram, pvc, ports, error = common.invoke(exe, OUT, 'native_guard_%03d' % i,
            fx['ram'], state, fx['pvc'], fx['bank_base'], resources,
            stop=fx['stop_pc'], external=fx['external'])
        guard = phases[-1]['guard']
        cause = {0x46f06: 'animation cleanup original TRAP15: coordinate index',
                 0x2a52: 'animation cleanup original TRAP15: nonzero object type',
                 0x278e: 'unsupported animation machine PC'}[guard['pc']]
        assert guard['problem'] == ('unmapped_or_protected' if guard['pc'] == 0x278e else 'unsupported_TRAP')
        assert not result['ok'] and cause in error, (selection, guard, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state
        assert ram == fx['ram'] and pvc == fx['pvc'] and result['bank_base'] == fx['bank_base']
        assert ports == struct.pack('>BII', 1, 0xdeadbeef, 0x87)
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(selection=selection, native_guard=guard,
                         checked_API_error=error, all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    return rows


def negatives(exe, records, resources, program):
    rows = []
    base = records[0][1]
    marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
    def reject(label, changes, cause, memory=(), fx=None):
        fx = base if fx is None else fx
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        state.update(changes)
        ram = bytearray(fx['ram'])
        for address, size, value in memory:
            common.native.put(ram, address, size, value)
        result, outgoing, pvc, ports, error = common.invoke(exe, OUT, 'negative_' + label,
            bytes(ram), state, fx['pvc'], fx['bank_base'], resources, stop=0xff000,
            external=fx['external'])
        assert not result['ok'] and cause in error, (label, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state
        assert outgoing == ram and pvc == fx['pvc'] and ports == marker
        assert result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=label, error=error, all_API_outputs_preserved=True,
                         native_exception_rollback_equivalence_claimed=False))
    for pc in (0x29c4, 0x2a16):
        reject('Unknown_branch_%06x' % pc, {'pc': pc, 'carry': 0},
               'cleanup caller requires known carry')
    for pc in (0x2a28, 0x2a48):
        reject('nonzero_object_type_%06x' % pc, {'pc': pc, 'a0': 0x102000},
               'animation cleanup original TRAP15: nonzero object type',
               memory=((0x102010, 2, 1),))
    for pc in (0x2a60, 0x2a84):
        reject('nonzero_parent_type_%06x' % pc, {'pc': pc, 'a6': 0x102000},
               'animation cleanup original TRAP15: nonzero parent type',
               memory=((0x102010, 2, 1),))
    reject('coordinate_index_TRAP', {'pc': 0x46ef4, 'a6': 0x102000},
           'animation cleanup original TRAP15: coordinate index', memory=((0x10206c, 1, 8),))
    reject('nine_LONG_clears_before_unwritable_final_WORD', {'pc': 0x43dda, 'a0': 0x1fffdc},
           'unsupported animation machine write device')
    reject('object_BYTE_WORD_clears_before_unwritable_LONG_array', {'pc': 0x272e, 'a0': 0x1fff90},
           'unsupported animation machine write device')
    reject('two_stack_LONG_pushes_before_fixed_bank_push', {'pc': 0x2a34, 'a7': 0x100008},
           'program bus write requires RAM mirror units')
    reject('coordinate_LONG_clears_before_bad_live_RTS', {'pc': 0x43dda, 'a0': 0x102000},
           'unsupported animation frame head h8 PC', memory=((base['initial_a7'], 4, 0xdeac),))
    # Former expectation 'unsupported animation machine PC': 3dce publishes A0=3dcc over the live return, RTS then enters 3dcc. 3dcc is routed by the
    # F6a IRQ shell (animation_machine_irq_f6a.cpp case 0x3dcc) [I: the new error is attributed to that execution, not separately traced]; the run ends with the checked odd-PC error. Work-RAM PCs are the unrouted controls.
    reject('sound_callback_publication_overwrites_live_return', {'pc': 0x3dce, 'a5': 0x108000, 'a7': 0x100006},
           'unaligned animation machine PC')
    for pc in (0x10fe00, 0x10fefe):
        reject('unrouted_work_ram_control_%06x' % pc, {'pc': pc}, 'unsupported animation machine PC')
    reject('post_map_sequence_unsupported', {'pc': 0xc00468}, 'unsupported animation machine PC')
    whole = next(fx for _, fx, _ in records if fx['entry_pc'] == 0x47fe4)
    # Legacy synthetic cleanup lists are not initialized binding bucket lists.
    # Preserve the fixture and check the actual later write guard.
    reject('legacy_cleanup_scene_palette_alignment_guard', {}, 'invalid animation machine write size/alignment', fx=whole)
    return rows


def zero_step(exe, resources, fx):
    rows = []
    for pc in (0x299c, 0x29c4, 0x2a0a, 0x2a16, 0x2a28, 0x2a48, 0x2a60, 0x2a84,
               0x477c2, 0x47fe4, 0x47fe8):
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
    import observe_animation_machine_cleanup as native
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_cleanup.py',
                 'docs/analysis/animation-machine-hud-contract.md',
                 'docs/analysis/animation-machine-cleanup-contract.md',
                 'engine/tests/animation_machine_cleanup_test.cpp'):
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
                  negatives=negative, negative_count=len(negative) + len(guarded), zero_step=zero,
                  harness_JSON_keys=22, normalized_reference_paths=len(unique),
                  compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled original cleanup/helper fixtures; no natural gameplay or scheduler reachability claim.',
                          'Native has no SR reads; known carry only from actual original branch direction. No general CCR/timing/IRQ or hardware proof.',
                          'Video/watchdog are ordered register-port output; no rendered VRAM/pixel behavior claim. PVC device effects independently fold original ordered writes.',
                          'Resumes forward previous actual C++ outputs plus declared host RAM changes; native incoming is only an assertion.',
                          'Checked failures preserve API outputs, not original CPU fault rollback or filesystem atomic I/O.'])
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=matches['cases'], phases=matches['phases'],
                         resumes=matches['previous_actual_CPP_resumes'], negatives=len(negative) + len(guarded),
                         sha256=digest(report_path))))


if __name__ == '__main__':
    main()
