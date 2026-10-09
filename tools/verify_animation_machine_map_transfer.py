"""Original map transfer/node helper shared-stack execution vs the public machine API.

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
OUT = ROOT / 'artifacts/animation_machine_map_transfer_execution'
NATIVE_SHA = '3cbf2b1b6b49c675f116c8298f09d36feb817ae76173fcab4d03a71b1428abf8'
NATIVE_TOOL_SHA = '5c3e49d5f3b74f275e2efc7d5c670b462be3f2e6a1b9e4c651a9d4816dbaf5e8'


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
    import observe_animation_machine_map_transfer as native
    folder = ROOT / 'artifacts/animation_machine_map_transfer_native'
    path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA, 'native freeze required'
    assert digest(path) == NATIVE_SHA
    assert digest(ROOT / 'tools/observe_animation_machine_map_transfer.py') == NATIVE_TOOL_SHA
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
        assert audit_program_reads(program, fx, split) == audit_program_reads(program, fx, control)
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


def audit_program_reads(program, fx, phases):
    """Reconstruct each live bank from ordered writes, independently of tags."""
    bank = fx['bank_base']
    ff8 = int.from_bytes(fx['pvc'][0x1ff0:0x1ff2], 'big')
    ff9 = int.from_bytes(fx['pvc'][0x1ff2:0x1ff4], 'big')
    counts = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for phase in phases:
        assert (phase['bank_before'], phase['ff8_before'], phase['ff9_before']) == (bank, ff8, ff9)
        for event in phase['events']:
            address, size = event['address'], event['size']
            raw = bytes.fromhex(event['bytes'])
            assert len(raw) == size
            if event['region'] == 'pvc':
                assert event['access'] == 'write' and size == 2
                if address == 0x2ffff0:
                    ff8 = int.from_bytes(raw, 'big')
                else:
                    assert address == 0x2ffff2
                    ff9 = int.from_bytes(raw, 'big')
                bank, ff8, ff9 = common.pvc_bank_update(ff8, ff9)
                assert (event['bank_after'], event['ff8_after'], event['ff9_after']) == (bank, ff8, ff9)
                counts['PVC_writes'] += 1
            elif event['region'] in ('fixed', 'bank'):
                assert event['access'] == 'read'
                if event['region'] == 'fixed':
                    assert 0 <= address <= 0x100000 - size
                    physical = address
                    counts['fixed_reads'] += 1
                else:
                    assert 0x200000 <= address <= 0x2fe000 - size
                    physical = bank + address - 0x200000
                    assert (event['bank_at_read'], event['physical_rom_offset']) == (bank, physical)
                    counts['bank_reads'] += 1
                assert 0 <= physical <= len(program) - size
                assert raw == program[physical:physical + size]
        assert phase['modeled_bank'] == bank
    return counts


def audit_carry(program, selection, fx, split, control):
    # Native map transfer scope does not claim observed C; no SR oracle is introduced.
    for phase in split + control:
        assert phase['carry'] is None and not phase['branch_evidence']


def compare_guards(exe, guards, resources):
    rows = []
    for i, (selection, fx, phases) in enumerate(guards):
        guard = phases[-1]['guard']
        assert guard is not None
        if guard['problem'] == 'CPU_exception' and guard['pc'] in (0x1871a, 0x18738):
            cause = 'animation map DIVU zero divisor'
        elif guard['problem'] == 'unsupported_odd_data_access' and guard['pc'] == 0x16f4e:
            cause = 'program bus requires even WORD/LONG address'
        elif guard['problem'] == 'unmapped_or_protected' and guard['pc'] == 0x185e8:
            assert guard['address'] == 0x200000
            cause = 'unsupported animation machine write device'
        else:
            assert guard['problem'] == 'unmapped_or_protected' and guard['pc'] == 0x16f98
            assert guard['address'] == 0x218742
            cause = 'unsupported animation machine PC'
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        result, ram, pvc, ports, error = common.invoke(exe, OUT, 'guard_%03d' % i,
            fx['ram'], state, fx['pvc'], fx['bank_base'], resources,
            stop=fx['stop_pc'], external=fx['external'])
        assert not result['ok'] and cause in error, (selection, guard, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state
        assert ram == fx['ram'] and pvc == fx['pvc'] and result['bank_base'] == fx['bank_base']
        assert ports == struct.pack('>BII', 1, 0xdeadbeef, 0x87)
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(selection=selection, native_guard=guard, checked_API_error=error,
                         all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    return rows


def negatives(exe, records, resources, program):
    rows = []
    base = records[0][1]
    marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
    def reject(label, changes, cause, memory=(), fx=None, selected_resources=None):
        fx = base if fx is None else fx
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        state.update(changes)
        ram = bytearray(fx['ram'])
        for address, size, value in memory:
            common.native.put(ram, address, size, value)
        result, outgoing, pvc, ports, error = common.invoke(exe, OUT, 'negative_' + label,
            bytes(ram), state, fx['pvc'], fx['bank_base'],
            resources if selected_resources is None else selected_resources,
            stop=0xff000, external=fx['external'])
        assert not result['ok'] and cause in error, (label, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state
        assert outgoing == ram and pvc == fx['pvc'] and ports == marker
        assert result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=label, error=error, all_API_outputs_preserved=True,
                         native_exception_rollback_equivalence_claimed=False))
    for pc in (0x16f50, 0x16f64, 0x1871a, 0x18738):
        reject('flag_or_DIVU_only_%06x' % pc, {'pc': pc}, 'unsupported animation map transfer PC')
    reject('post_map_body_unsupported', {'pc': 0xc00468}, 'unsupported animation machine PC')
    reject('live_MOVEM_pushes_before_fixed_stack_write', {'pc': 0x18424, 'a7': 0x100008},
           'program bus write requires RAM mirror units')
    reject('live_MOVEM_pops_before_bank_stack_read', {'pc': 0x18530, 'a7': 0x1ffff8},
           'missing or ambiguous physical program bus ROM byte', selected_resources=[])
    reject('first_secondary_RAM_LONG_before_second_bank_write', {'pc': 0x1858a,
           'a4': 0x103000, 'a3': 0x1ffffc, 'd0': 0, 'd6': 2},
           'unsupported animation machine write device')
    reject('column_record_BYTE_write_before_live_node_BYTE_failure', {'pc': 0x16f76,
           'a3': 0x102000, 'a0': 0x2fffcb, 'a2': 0x103000},
           'unsupported program bus device address')
    reject('flag_write_before_bad_live_RTS', {'pc': 0x17012, 'a0': 0x102000},
           'unsupported animation machine PC', memory=((base['initial_a7'], 4, 0xdeac),))
    reject('finite_budget_after_repeated_secondary_clear_writes', {'pc': 0x185a6,
           'a0': 0x106000, 'd2': 0, 'd3': 0, 'd4': 0, 'd5': 0},
           'animation machine block budget exceeded')
    whole = next(fx for _, fx, _ in records if fx['entry_pc'] == 0x48042)
    # Whole run now proceeds past 4804e (fade_card core); first checked failure moved to a write guard.
    reject('whole_map_before_fade_body_write_guard', {}, 'unsupported animation machine write device', fx=whole)
    reject('PVC_bank3_before_missing_primary_ROM_chunk', {},
           'missing or ambiguous physical program bus ROM byte', fx=whole,
           selected_resources=[p for p in resources if 'program_rom_300000' not in str(p)])
    return rows


def source_carry_writers(exe, resources, fx, program):
    # Opcode evidence is distinct from observing native CCR/SR.
    rows = []
    for pc, stop, raw, expected in ((0x185ee, 0x185f2, '003c00014e75', 2),
                                    (0x185f4, 0x185f8, '023c00fe4e75', 1)):
        assert program[pc:pc + 6].hex() == raw
        for incoming in (0, 1, 2):
            state = dict(fx['regs'], a7=fx['initial_a7'], pc=pc, carry=incoming)
            result, ram, pvc, ports, error = common.invoke(exe, OUT,
                'source_carry_%06x_%d' % (pc, incoming), fx['ram'], state,
                fx['pvc'], fx['bank_base'], resources, stop=stop, external=fx['external'])
            assert result['ok'] and not error and result['status'] == 0 and result['carry'] == expected
            assert {k: result[k] for k in common.STATE_KEYS} == dict(state, pc=stop, carry=expected)
            assert ram == fx['ram'] and pvc == fx['pvc'] and not ports
            assert result['bank_base'] == fx['bank_base'] and result['external_reads'] == 0
            rows.append(dict(pc=pc, stop=stop, original_raw=raw, incoming_carry=incoming,
                             source_classified_carry=expected, native_CCR_observation=False))
    return rows


def zero_step(exe, resources, fx):
    rows = []
    for pc in (0x48042, 0x48048, 0x4804e, 0x16f0e, 0x16f98,
               0x183c6, 0x18424, 0x185ee, 0x185f4, 0x1861a, 0x18702):
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
    import observe_animation_machine_map_transfer as native
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_map_transfer.py',
                 'docs/analysis/animation-machine-hud-contract.md',
                 'docs/analysis/animation-machine-map-transfer-contract.md',
                 'engine/tests/animation_machine_map_transfer_test.cpp'):
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
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for _, fx, phases in records:
        for key, value in audit_program_reads(program, fx, phases).items():
            program_reads[key] += value
    matches = compare(exe, records, resources)
    guarded = compare_guards(exe, guards, resources)
    negative = negatives(exe, records, resources, program)
    zero = zero_step(exe, resources, records[0][1])
    classified_carry = source_carry_writers(exe, resources, records[0][1], program)
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
                  actual_CPP=matches, original_program_read_audit=program_reads,
                  native_guards_checked_API=guarded,
                  native_continuous_control_phases_replayed=control_count,
                  negatives=negative, negative_count=len(negative) + len(guarded), zero_step=zero,
                  source_classified_carry_writers=classified_carry,
                  harness_JSON_keys=22, normalized_reference_paths=len(unique),
                  compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled original map transfer/node fixtures; no natural gameplay or scheduler reachability claim.',
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
