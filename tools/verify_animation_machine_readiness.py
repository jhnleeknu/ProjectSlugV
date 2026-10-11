"""Original readiness stack/caller execution vs the animation-machine API.

No SR reads or expected-state injection. Legacy native evidence stays immutable.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as callers
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_readiness_execution'
NATIVE_SHA = 'a93d54a8b9001073a469795b70e00541ab5c9f09dcee9af9c2aa7b7393157ada'
NATIVE_TOOL_SHA = '2055e9c1a3c89a7b9378f8ebcfe259a176815d42ede2f03543e5118026b9fb3e'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(exe, folder, records, resources):
    rows = []
    resumes = ports_count = reads = returns = branches = waits = 0
    for i, (selection, fx, phases) in enumerate(records):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
        ram, pvc, bank = fx['ram'], fx['pvc'], fx['bank_base']
        expected_pvc, expected_bank = pvc, bank
        phase_rows = []
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
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming']
            assert ram == phase['ram_before']
            expected_pvc, expected_bank, portbytes = common.fold_device(expected_pvc, expected_bank, phase['events'])
            assert expected_bank == phase['modeled_bank']
            # Return-boundary is compared separately from execution of the real
            # caller BCC/BCS. Stop uses the original observed successor for that
            # branch phase; a wrong C++ decision cannot silently pass this stop.
            stop = fx['return_pc'] if phase['waiting'] or phase['label'] != 'branch-result' else phase['outgoing']['pc']
            actual = common.invoke(exe, folder, 'case_%03d_phase_%02d' % (i, j),
                                   ram, state, pvc, bank, resources, stop=stop, external=fx['external'])
            common.check_result(actual, phase, expected_pvc, expected_bank, portbytes)
            result, ram, pvc, _, _ = actual
            expected_carry = 0 if phase['waiting'] else phase['carry']
            assert expected_carry in (0, 1, 2) and result['carry'] == expected_carry
            state = {k: result[k] for k in common.STATE_KEYS}
            bank = result['bank_base']
            waits += phase['waiting']
            returns += phase['label'] == 'return-boundary'
            branches += phase['label'] == 'branch-result'
            reads += result['external_reads']
            ports_count += len(portbytes) // 9
            phase_rows.append(dict(label=phase['label'], carry=result['carry'],
                                   actual_previous_outputs_used=bool(j),
                                   carry_oracle='APIwaitUnknown' if phase['waiting'] else 'actual original branch direction',
                                   full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
        rows.append(dict(index=i, selection=selection, phases=phase_rows))
    return dict(cases=len(rows), phases=sum(len(x['phases']) for x in rows),
                previous_actual_CPP_resumes=resumes, waits=waits, return_boundaries=returns,
                branch_results=branches, external_reads=reads, ports=ports_count, matches=rows)


# Superseded expectations (final state): the successor 480bc / its callees are executable now (U1..U7), so these runs go on and end in a state-dependent
# bus error instead of an unsupported-PC rollback. Labels are kept; former and observed errors are recorded in the report (superseded_negatives).
SUPERSEDED_CAUSES = {'known_branch_late_unsupported_successor_1': 'program bus requires even WORD/LONG address',
                     'whole_activation_readiness_late_unsupported_successor': 'program bus requires even WORD/LONG address'}
SUPERSEDED_NEGATIVES = []


def negatives(exe, folder, records, resources):
    rows = []
    base = records[0][1]
    marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
    def reject(label, fx, changes, cause, memory=(), selected=None, stop=0xff000):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        state.update(changes)
        ram = bytearray(fx['ram'])
        for address, size, value in memory:
            common.native.put(ram, address, size, value)
        actual = common.invoke(exe, folder, 'negative_' + label, bytes(ram), state,
                               fx['pvc'], fx['bank_base'], resources if selected is None else selected,
                               stop=stop, external=fx['external'])
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
    for pc in (0x47d42, 0x48484, 0x48490, 0x1bdf4, 0x1be12):
        reject('Unknown-branch-%06x' % pc, base, {'pc': pc, 'carry': 0},
               'readiness caller requires known carry')
    reject('odd_player_marker_after_nested_JSR', base,
           {'pc': 0x4847c, 'a5': 0x108001}, 'even WORD/LONG')
    reject('late_JSR_return_LONG_crosses_RAM_bank', base,
           {'pc': 0x47d3e, 'a7': 0x200002}, 'program bus write requires RAM mirror units')
    reject('odd_record_WORD_after_pointer_and_D0_changes', base,
           {'pc': 0x4dee2, 'a5': 0x108001}, 'even WORD/LONG')
    reject('second_mask_BYTE_device_after_first_PVC_read', base,
           {'pc': 0x4e166, 'a5': 0x3075bb}, 'unsupported program bus device address')
    reject('late_live_RTS_after_marker_read', base,
           {'pc': 0x289e, 'a0': 0x104900}, 'unsupported animation machine PC',
           memory=((0x104900, 4, 0x270e), (base['initial_a7'], 4, 0xdeac)))
    # Real kind3 resources remain unmodified. Removing physical bank2 leaves
    # the first player marker in mirrored RAM, then rejects the reached second
    # player's original ROM data at CPU200010 after the first live stack calls.
    selected = [path for path in resources
                if struct.unpack_from('<I', Path(path).read_bytes(), 16)[0] != 0x200000]
    reject('late_second_player_missing_physical_bank2', base,
           {'pc': 0x4847c, 'a5': 0x207268},
           'missing or ambiguous physical program bus ROM byte',
           memory=((0x1fff20, 4, 0x270e),), selected=selected)
    for carry in (1, 2):
        reject('known_branch_late_unsupported_successor_%d' % carry, base,
               {'pc': 0x47d42, 'carry': carry}, 'unsupported animation machine PC')
    chain = next(fx for selection, fx, phases in records
                 if selection['label'] == 'activation-single-wrapper-wait')
    released = bytearray(chain['ram'])
    common.native.put(released, 0x108d34, 2, 0x100)
    chain = dict(chain, ram=bytes(released))
    # Explicit checked-fixture host setup only: first demonstrate the complete
    # whole activation/readiness prefix runs without waiting before asking for
    # an unsupported successor. This extra control is not a native comparison.
    state = dict(chain['regs'], a7=chain['initial_a7'], pc=chain['entry_pc'], carry=2)
    actual = common.invoke(exe, folder, 'negative_whole_chain_control', chain['ram'], state,
                           chain['pvc'], chain['bank_base'], resources,
                           stop=chain['return_pc'], external=chain['external'])
    result, ram, pvc, ports, error = actual
    assert result['ok'] and not error and result['status'] == 0
    assert result['pc'] == 0x47d42 and result['carry'] in (1, 2)
    assert ram != chain['ram'] and ports and ports != marker
    reject('whole_activation_readiness_late_unsupported_successor', chain, {},
           'unsupported animation machine PC')
    rows[-1].update(control_succeeded_to=0x47d42, control_ports=len(ports) // 9,
                    explicit_host_fixture_change=dict(address=0x108d34, size=2, value=0x100),
                    native_comparison_claimed=False)
    return rows


def zero_step(exe, folder, fx, resources):
    rows = []
    for carry in (0, 1, 2):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=0xff000, carry=carry)
        result, ram, pvc, ports, error = common.invoke(exe, folder, 'zero_step_%d' % carry,
            fx['ram'], state, fx['pvc'], fx['bank_base'], resources, stop=state['pc'])
        assert result['ok'] and not error and result['status'] == 0
        assert {k: result[k] for k in common.STATE_KEYS} == state
        assert ram == fx['ram'] and pvc == fx['pvc'] and result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0 and not ports
        rows.append(dict(carry=carry, complete_input_state_preserved=True))
    return rows


def audit_native(root, program, source):
    import observe_animation_machine_readiness as native
    folder = root / 'artifacts/animation_machine_readiness_native'
    report_path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA
    assert digest(report_path) == NATIVE_SHA
    assert digest(root / 'tools/observe_animation_machine_readiness.py') == NATIVE_TOOL_SHA
    report = json.loads(report_path.read_text())
    assert report['source'] == source and report['failure'] is None
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False
    refs = callers.audit_references(root, folder, report)
    refs[str(report_path.resolve())] = NATIVE_SHA
    assert native.unicorn.__version__ == report['oracle']['version']
    assert digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((folder / 'source.json').read_text())
    assert static['source'] == source
    for ins in static['instructions']:
        at, size = ins['rom_offset'], ins['size']
        assert bytes.fromhex(ins['raw']) == program[at:at + size]
    records = []
    split_count = control_count = 0
    def check_payload(i, phases, saved, prefix):
        assert len(phases) == len(saved)
        for j, (phase, row) in enumerate(zip(phases, saved)):
            for key in ('label', 'incoming', 'outgoing', 'waiting', 'carry', 'host_changes', 'modeled_bank'):
                assert phase[key] == row[key], (prefix, i, j, key)
            assert row['branch_taken'] == phase.get('branch_taken')
            assert row['external_reads'] == sum(e['region'] == 'external' for e in phase['events'])
            assert phase['guard'] is None
            stem = '%s_%03d_phase_%02d' % (prefix, i, j)
            ports = [e for e in phase['events'] if e['region'] == 'pvc']
            payloads = {stem + '_ram_before.bin': phase['ram_before'], stem + '_ram_after.bin': phase['ram_after'],
                        stem + '_pvc_before.bin': phase['pvc_before'], stem + '_pvc_after.bin': phase['pvc_after'],
                        stem + '_ports.bin': b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports),
                        stem + '_trace.json': (json.dumps({k: phase[k] for k in ('pcs', 'events', 'boundaries', 'guard')}, indent=2) + '\n').encode()}
            snapshot = phase['return_snapshot']
            assert row['return_snapshot_registers'] == (snapshot['registers'] if snapshot else None)
            if snapshot:
                payloads[stem + '_return_ram.bin'] = snapshot['ram']
                payloads[stem + '_return_pvc.bin'] = snapshot['pvc']
            assert set(row['artifacts']) == set(payloads)
            for name, data in payloads.items():
                assert (folder / name).read_bytes() == data
                assert hashlib.sha256(data).hexdigest() == row['artifacts'][name]
    selections = native.matrix(program)
    assert len(selections) == report['cases'] == len(report['results'])
    for i, selection in enumerate(selections):
        normalized, fx, split = native.run_case(program, selection)
        other, other_fx, control = native.run_case(program, selection, continuous=True)
        saved = report['results'][i]
        at = fx['return_pc']
        expected_opcode = 0x64 if fx['branch_opcode'] == 'BCC' else 0x65
        assert program[at] == expected_opcode and program[at + 1] == 0
        assert at + 2 + int.from_bytes(program[at + 2:at + 4], 'big', signed=True) == fx['branch_target']
        assert at + 4 == fx['branch_fallthrough']
        assert fx['return_pc'] == 0x47d42
        assert fx['branch_target'] == 0x47d72 and fx['branch_fallthrough'] == 0x47d46
        assert fx['branch_opcode'] == 'BCC'
        assert normalized == other and fx == other_fx
        assert saved['index'] == i and saved['selection'] == normalized
        assert saved['reproduced_twice'] and saved['continuous_split_equivalent']
        assert saved['fixture'] == {k: v for k, v in fx.items() if k not in ('ram', 'pvc', 'regs')}
        check_payload(i, split, saved['phases'], 'case')
        check_payload(i, control, saved['continuous_control'], 'control')
        # Derive C independently from executed original branch successor, not
        # observer's carry tag or C++ output. BCC taken iff C clear; BCS iff set.
        boundary, branch, uninterrupted = split[-2], split[-1], control[-1]
        assert branch['outgoing']['pc'] in (fx['branch_target'], fx['branch_fallthrough'])
        taken = branch['outgoing']['pc'] == fx['branch_target']
        carry = (1 if taken else 2) if fx['branch_opcode'] == 'BCC' else (2 if taken else 1)
        assert branch['pcs'] == [fx['return_pc'], branch['outgoing']['pc']] and not branch['events']
        assert boundary['outgoing'] == branch['incoming'] == uninterrupted['return_snapshot']['registers']
        assert boundary['ram_after'] == branch['ram_before'] == uninterrupted['return_snapshot']['ram']
        assert boundary['pvc_after'] == branch['pvc_before'] == uninterrupted['return_snapshot']['pvc']
        assert branch['outgoing'] == uninterrupted['outgoing']
        assert branch['ram_after'] == uninterrupted['ram_after'] == branch['ram_before']
        assert branch['pvc_after'] == uninterrupted['pvc_after'] == branch['pvc_before']
        assert uninterrupted['pcs'] == boundary['pcs'][:-1] + branch['pcs']
        assert uninterrupted['events'] == boundary['events']
        for phase in split + control:
            assert phase['carry'] == (None if phase['waiting'] else carry)
        for a, b in zip(split[:-2], control[:-1]):
            assert a == b
        split_count += len(split)
        control_count += len(control)
        records.append((normalized, fx, split))
    assert split_count == report['phases'] and control_count == report['continuous_control_phases']
    assert report['fresh_CPU_runs'] == 4 * len(records)
    assert report['phase_executions'] == 2 * (split_count + control_count)
    return records, refs, control_count


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    import observe_animation_machine_readiness as native
    inputs = callers.dependencies(ROOT)
    inputs['tools/verify_animation_machine_readiness.py'] = digest(Path(__file__))
    inputs['docs/analysis/animation-machine-readiness-contract.md'] = digest(ROOT / 'docs/analysis/animation-machine-readiness-contract.md')
    for tool in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(tool)] = digest(tool)
    for name in ('animation_machine_device_test.cpp', 'animation_machine_readiness_test.cpp'):
        path = ROOT / 'engine/tests' / name
        assert path.is_file()
        inputs[str(path.relative_to(ROOT))] = digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path'];rom_guard = digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    records, native_refs, control_phases = audit_native(ROOT, program, source)
    refs.update(native_refs)
    exe, command = callers.compile_harness(ROOT, OUT)
    matches = compare(exe, OUT, records, resources)
    negative_rows = negatives(exe, OUT, records, resources)
    zero_rows = zero_step(exe, OUT, records[0][1], resources)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert digest(ROOT / name) == expected, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update({str(p.resolve()): digest(p) for p in OUT.iterdir() if p.is_file() and p != report_path})
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve());assert key not in unique or unique[key] == expected;unique[key] = expected
    report = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  native_split_phases_replayed=matches['phases'], native_continuous_control_phases_replayed=control_phases,
                  actual_CPP=matches, superseded_negatives=SUPERSEDED_NEGATIVES, negatives=negative_rows, negative_count=len(negative_rows),
                  zero_step=zero_rows, harness_JSON_keys=22, normalized_reference_paths=len(unique),
                  compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled originalreadiness helper/caller/sharedstack fixtures; natural gameplay not proved.',
                          'Carry is proved by actual originalbranch successor. Return-boundary tags use the subsequent actualbranch; pendingUnknown is an API contract, not observed nativeC.',
                          'No hostSR reads or originalcodepatches; fresh continuous controls check that stop/resume did not change nativebranch outcomes.',
                          'FullRAM/16R/PC/status/orderedports/reads match original; devicePVC/bank independently folds raw nativewrites.',
                          'No otherCCR/timing/IRQ/hardware or post-branch caller behavior claim.',
                          'Negative results establish checkedAPI transaction semantics, not nativefaultrollback or productionfileatomicity.'])
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=matches['cases'], phases=matches['phases'],
                          resumes=matches['previous_actual_CPP_resumes'], negatives=len(negative_rows),
                          sha256=digest(report_path))))


if __name__ == '__main__':
    main()
