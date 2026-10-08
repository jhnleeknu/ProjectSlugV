"""Actual original BCC/BCS direction vs animation-machine carry enum.

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
OUT = ROOT / 'artifacts/animation_machine_carry_execution'
NATIVE_SHA = '759ea9af0fd9e9fa58ba44b87be2b48a8b7b6b257aba6b164438f7c3df586d70'
NATIVE_TOOL_SHA = '1f133fb8a6d8645f7cf837c18d78c56e9294550a67722e50bac5eb5d3ce06633'


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


def negatives(exe, folder, records, resources):
    fx = records[0][1]
    rows = []
    initial = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
    def reject(label, state, stop, cause):
        actual = common.invoke(exe, folder, 'negative_' + label, fx['ram'], state,
                               fx['pvc'], fx['bank_base'], resources, stop=stop, external=fx['external'])
        result, ram, pvc, ports, error = actual
        assert not result['ok'] and cause in error, (label, error)
        assert {k: result[k] for k in common.STATE_KEYS} == state
        assert ram == fx['ram'] and pvc == fx['pvc'] and result['bank_base'] == fx['bank_base']
        assert ports == struct.pack('>BII', 1, 0xdeadbeef, 0x87)
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=label, error=error, incoming_carry=state['carry'], all_API_outputs_preserved=True))
    for pc in (0x1dc8a, 0x210b4):
        reject('Unknown-branch-%06x' % pc, dict(initial, pc=pc, carry=0), 0xff000, 'requires known carry')
    for value in (3, 0xffffffff):
        reject('invalid-enum-%x' % value, dict(initial, pc=0xff000, carry=value), 0xff000, 'carry')
    for pc, carry in ((0x1dc8a, 1), (0x1dc8a, 2), (0x210b4, 1), (0x210b4, 2)):
        reject('late-branch-%06x-%d' % (pc, carry), dict(initial, pc=pc, carry=carry), 0xff000,
               'unsupported animation machine PC')
    for entry in (0x1dc84, 0x210ae):
        selection, fx, phases = next(record for record in records
                                     if record[1]['entry_pc'] == entry and len(record[2]) == 2)
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=entry, carry=2)
        assert any(e['access'] == 'write' for e in phases[0]['events'])
        reject('whole-caller-late-branch-%06x' % entry, state, 0xff000,
               'unsupported animation machine PC')
        rows[-1]['prior_original_prefix_writes'] = sum(e['access'] == 'write' for e in phases[0]['events'])
        rows[-1]['prior_original_prefix_ports'] = sum(e['region'] == 'pvc' for e in phases[0]['events'])
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
    import observe_animation_machine_carry as native
    folder = root / 'artifacts/animation_machine_carry_native'
    report_path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA
    assert digest(report_path) == NATIVE_SHA
    assert digest(root / 'tools/observe_animation_machine_carry.py') == NATIVE_TOOL_SHA
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
        if not normalized['initializer_only']:
            assert program[fx['entry_pc']:fx['entry_pc'] + 6] == bytes.fromhex('4eb900049fc6')
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
    import observe_animation_machine_carry as native
    inputs = callers.dependencies(ROOT)
    inputs['tools/verify_animation_machine_carry.py'] = digest(Path(__file__))
    for tool in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(tool)] = digest(tool)
    for name in ('animation_machine_device_test.cpp', 'animation_machine_carry_test.cpp'):
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
                  actual_CPP=matches, negatives=negative_rows, negative_count=len(negative_rows),
                  zero_step=zero_rows, harness_JSON_keys=22, normalized_reference_paths=len(unique),
                  compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled originalcallerJSR/BCC/BCS fixtures; natural gameplay not proved.',
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
