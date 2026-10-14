"""Actual activation callers/helpers vs the public animation-machine API.

Native ROM and observations are immutable. This is controlled fixture evidence,
not natural scheduler reachability or a production command-line interface.
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
OUT = ROOT / 'artifacts/animation_machine_activation_execution'
# Set only after the native owner explicitly freezes both files.
NATIVE_SHA = '9244bfafbf4fe921ccbb8d293e5b713fa16f4fdc35b38246d851c7726fac8e61'
NATIVE_TOOL_SHA = 'a188f9d8823c6fd19fa6b5cdea4ca0c55016f38d644b25b6fe9b8778954b828c'


def digest(path):
    return helpers.digest(path)


def audit_native(program, source):
    import observe_animation_machine_activation as native
    folder = ROOT / 'artifacts/animation_machine_activation_native'
    path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA, 'native owner freeze required'
    assert digest(path) == NATIVE_SHA
    assert digest(ROOT / 'tools/observe_animation_machine_activation.py') == NATIVE_TOOL_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    refs = helpers.audit_references(ROOT, folder, report)
    refs[str(path.resolve())] = NATIVE_SHA
    oracle = report['oracle']
    assert native.unicorn.__version__ == oracle['version']
    assert digest(oracle['library']) == oracle['library_sha256']
    static = json.loads((folder / 'source.json').read_text())
    assert static['source'] == source
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes.fromhex(instruction['raw']) == program[at:at + size]
    selections = native.matrix(program)
    assert len(selections) == len(report['results'])
    records = []
    for i, selection in enumerate(selections):
        normalized, fx, phases = native.run_case(program, selection)
        saved = report['results'][i]
        assert saved['index'] == i and saved['selection'] == normalized
        assert saved['reproduced_twice'] is True
        assert saved['fixture'] == {k: v for k, v in fx.items() if k not in ('ram', 'pvc', 'regs')}
        assert len(phases) == len(saved['phases'])
        for j, (phase, row) in enumerate(zip(phases, saved['phases'])):
            for key in ('label', 'incoming', 'outgoing', 'waiting',
                        'host_changes', 'modeled_bank', 'guard'):
                assert phase[key] == row[key], (i, j, key)
            assert phase['guard'] is None
            assert row['raw_sprite_lookup_reads'] == [
                dict(address=e['address'], size=e['size'], bytes=e['bytes'])
                for e in phase['events'] if e['pc'] == 0x47ce0 and e['access'] == 'read']
            assert row['external_reads'] == sum(e['region'] == 'external' for e in phase['events'])
            stem = 'case_%03d_phase_%02d' % (i, j)
            ports = [e for e in phase['events'] if e['region'] == 'pvc']
            payloads = {stem + '_ram_before.bin': phase['ram_before'],
                        stem + '_ram_after.bin': phase['ram_after'],
                        stem + '_pvc_before.bin': phase['pvc_before'],
                        stem + '_pvc_after.bin': phase['pvc_after'],
                        stem + '_ports.bin': b''.join(struct.pack('>BII', e['size'], e['address'],
                                                                   int(e['bytes'], 16)) for e in ports),
                        stem + '_trace.json': (json.dumps({k: phase[k] for k in
                            ('pcs', 'events', 'boundaries', 'guard')}, indent=2) + '\n').encode()}
            assert set(row['artifacts']) == set(payloads)
            for filename, data in payloads.items():
                assert (folder / filename).read_bytes() == data, (i, j, filename)
                assert hashlib.sha256(data).hexdigest() == row['artifacts'][filename]
        records.append((normalized, fx, phases))
    assert len(records) == report['cases']
    assert sum(len(x[2]) for x in records) == report['phases']
    assert report['fresh_CPU_runs'] == 2 * len(records)
    assert report['raw_sprite_window']['sha256'] == hashlib.sha256(program[0x48a12:0x48e12]).hexdigest()
    assert report['previous_same_CPU_resumes'] == sum(len(x[2]) - 1 for x in records)
    return records, refs


def put(ram, address, size, value):
    data = value.to_bytes(size, 'big')
    for i, byte in enumerate(data):
        ram[(address + i) & 65535] = byte


def checked_failures(exe, records, resources, program):
    rows = []
    marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
    def fixture(entry, predicate=None):
        return next(fx for selection, fx, phases in records
                    if fx['entry_pc'] == entry and len(phases) == 1
                    and (predicate is None or predicate(fx, phases)))
    def reject(label, fx, cause, changes=None, memory=None, stop=None, selected=None):
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=2)
        state.update(changes or {})
        ram = bytearray(fx['ram'])
        for address, size, value in memory or []:
            put(ram, address, size, value)
        actual = common.invoke(exe, OUT, label, bytes(ram), state, fx['pvc'],
                               fx['bank_base'], resources if selected is None else selected,
                               stop=fx['stop_pc'] if stop is None else stop, external=fx['external'])
        result, out_ram, pvc, ports, error = actual
        assert not result['ok'] and cause in error, (label, error)
        assert {key: result[key] for key in common.STATE_KEYS} == state, label
        assert out_ram == ram and pvc == fx['pvc'] and ports == marker, label
        assert result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=label, entry=state['pc'], error=error,
                         all_API_outputs_preserved=True,
                         native_exception_rollback_equivalence_claimed=False))
    sprite = fixture(0x16ea4)
    signed = fixture(0x16ed2)
    chain = fixture(0x47cae)
    reject('odd_object_WORD_after_wrapper_prefix', sprite, 'even WORD/LONG',
           changes={'a6': 0x102001})
    reject('second_signed_read_device_after_first_read', signed,
           'unsupported program bus device address', changes={'a5': 0x2ff2ba})
    reject('late_flag_write_into_banked_ROM', signed,
           'unsupported animation machine write device', changes={'a6': 0x1fffeb})
    reject('late_MOVEM_third_LONG_split_write', sprite,
           'unsupported animation machine write device',
           changes={'pc': 0xcde4, 'a5': 0x2000c2, 'd3': 0})
    reject('unsupported_live_sprite_callback_after_prefix', sprite,
           'unsupported sprite callback target', memory=[(0x109152, 4, 0xdeac)])
    for entry in (0x16ea4, 0x16ed2):
        fx = fixture(entry, lambda fx, phases: entry != 0x16ea4 or 0xcde4 in phases[0]['pcs'])
        reject('late_live_RTS_unsupported_%06x' % entry, fx,
               'unsupported animation frame head h8 PC', memory=[(fx['initial_a7'], 4, 0xdeac)])
    # superseded expectation (was 'unsupported animation machine PC'): past the supported caller the 480bc frame helpers are executable now (U1..U7),
    # so the run ends in a state-dependent bus error; the label is kept and the former error is noted here.
    reject('whole_activation_past_supported_caller_boundary', chain,
           'program bus requires even WORD/LONG address', stop=0xff000)
    # Preserve real earlier fixed code/data while removing only the reached raw
    # index window. These negative-only kind3 files contain immutable ROM bytes.
    import pack_physical_program as physical
    selected = [path for path in resources if struct.unpack_from('<I', Path(path).read_bytes(), 16)[0] != 0]
    for start, end in ((0, 0x48a12), (0x48e12, 0x100000)):
        path = OUT / ('negative_fixed_%06x_%06x.ms5d' % (start, end))
        path.write_bytes(physical.wrap(program[start:end], start))
        physical.validate_container(path.read_bytes())
        selected.append(path)
    reached_chain = fixture(0x47cae, lambda fx, phases: any(
        e['access'] == 'read' and 0x48a12 <= e['address'] < 0x48e12
        for e in phases[0]['events']))
    reject('actual_raw_source_lookup_missing_only_reached_span', reached_chain,
           'missing or ambiguous physical program bus ROM byte', selected=selected)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    import observe_animation_machine_activation as native
    import pack_physical_program as physical
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_activation.py',
                 'docs/analysis/animation-machine-activation-contract.md',
                 'engine/tests/animation_machine_activation_test.cpp'):
        inputs[name] = digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    records, native_refs = audit_native(program, source)
    refs.update(native_refs)
    exe, command = helpers.compile_harness(ROOT, OUT)
    matches = common.compare_extended(exe, OUT, records, resources)
    negative = checked_failures(exe, records, resources, program)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert digest(ROOT / name) == expected, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update({str(p.resolve()): digest(p) for p in OUT.iterdir()
                 if p.is_file() and p != report_path})
    canonical = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in canonical or canonical[key] == expected
        canonical[key] = expected
    report = dict(schema_version=1, harness_JSON_keys=22, source=source,
                  inputs=inputs, artifacts=refs, native_observation_sha256=NATIVE_SHA,
                  native_tool_sha256=NATIVE_TOOL_SHA,
                  native_cases_replayed=len(records), native_phases_replayed=sum(len(x[2]) for x in records),
                  carry_native_observed=False, actual_CPP=matches,
                  checked_API_failures=negative, negative_count=len(negative),
                  compile_command=command, normalized_reference_paths=len(canonical),
                  failure=None, ROM_unchanged=True,
                  limits=['Synthetic controlled standalone helpers and actual upper activation caller chain; no natural scheduler/gameplay reachability claim.',
                          'Exact16registers/PC/fullRAM/status/orderedPVC/externalreads comparison; native has no carry observation. Actual C++ carry forwards on resume; waits require APIUnknown. No general CCR or timing claim.',
                          'Device PVC/bank is independently folded from original ordered writes; raw native PVC does not model device side effects.',
                          'Resumes use preceding actual C++ RAM/registers/carry/PVC/bank plus only recorded host RAM changes.',
                          'Checked invalid-access/callback/return failures preserve all API outputs; this is not original exception rollback equivalence or atomic filesystem I/O.',
                          'Negative missing-window fixtures package real immutable ROM slices as existing kind3; no original program data or pointers are patched.',
                          'Stops at helper return or47d20; prior47c6c condition and subsequent readiness/frame behavior remain outside this unit.'])
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=matches['cases'], phases=matches['phases'],
                         resumes=matches['previous_actual_CPP_resumes'],
                         negatives=len(negative), sha256=digest(report_path))))


if __name__ == '__main__':
    main()
