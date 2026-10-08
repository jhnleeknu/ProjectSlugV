"""Original caller/initializer vs actual public animation-machine API.

Synthetic controlled fixtures, not a production CLI or natural gameplay proof.
Native artifacts are immutable inputs; this verifier never invokes observer main.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import verify_animation_machine as common
from disassemble_program import load_verified_program

# Filled only after the native owner explicitly freezes its source/report.
NATIVE_SHA = 'f735043941529a9e020020715735b45e60890ab8b2b94211aeb0e4fbe22e17d5'
NATIVE_TOOL_SHA = '20e4a8aec91053be7d21637e599c52ac3894aff22e17c11d0294ffe1dd8a52c7'
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_callers_execution'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_ref(root, folder, name):
    path = Path(name)
    if path.is_absolute():
        return path
    candidate = root / path
    return candidate if candidate.is_file() else folder / path


def audit_references(root, folder, report):
    refs = {}
    for group in ('inputs', 'artifacts'):
        for name, expected in report[group].items():
            path = resolve_ref(root, folder, name)
            assert digest(path) == expected, (group, name)
            key = str(path.resolve())
            assert key not in refs or refs[key] == expected
            refs[key] = expected
    return refs


def dependencies(root):
    names = common.dependencies(root)
    names.add('tools/verify_animation_machine_callers.py')
    # Local imports used by native replay/fixture/resource code are provenance,
    # including dependencies loaded indirectly by the observer's fixture imports.
    tools = (root / 'tools').resolve()
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_file() and tools in path.parents:
            names.add(str(path.relative_to(root)))
    return {name: digest(root / name) for name in sorted(names)}


def compile_harness(root, folder):
    path = folder / 'harness.cpp'
    path.write_text(common.HARNESS)
    exe = folder / 'animation_machine_callers_harness'
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic',
               '-I' + str(root / 'engine/include')]
    command += [str(root / 'engine/src' / name) for name in common.SOURCES]
    command += [str(path), '-o', str(exe)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (folder / 'compile.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stdout and not run.stderr, run.stderr
    return exe, command


def compare(exe, folder, records, resources):
    # common.compare_extended forwards actual previous C++ RAM/16R/PC/PVC/bank
    # plus recorded host RAM changes; native incoming is only an assertion.
    return common.compare_extended(exe, folder, records, resources)


def audit_native(root, program, source):
    import observe_animation_machine_callers as native
    folder = root / 'artifacts/animation_machine_callers_native'
    path = folder / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA
    assert digest(path) == NATIVE_SHA
    assert digest(root / 'tools/observe_animation_machine_callers.py') == NATIVE_TOOL_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    refs = audit_references(root, folder, report)
    refs[str(path.resolve())] = NATIVE_SHA
    oracle = report['oracle']
    assert native.unicorn.__version__ == oracle['version']
    assert digest(oracle['library']) == oracle['library_sha256']
    static = json.loads((folder / 'source.json').read_text())
    assert static['source'] == source
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes.fromhex(instruction['raw']) == program[at:at + size]
    groups = []
    for name, selections, prefix in (('results', native.matrix(program), 'case'),
                                     ('guarded_results', native.guard_cases(program), 'guard')):
        assert len(selections) == len(report[name])
        records = []
        for i, selection in enumerate(selections):
            normalized, fx, phases = native.run_case(program, selection)
            saved = report[name][i]
            assert saved['index'] == i and saved['selection'] == normalized
            assert saved['reproduced_twice'] is True
            assert saved['fixture'] == {k: v for k, v in fx.items() if k not in ('ram', 'pvc', 'regs')}
            assert len(phases) == len(saved['phases'])
            for j, (phase, row) in enumerate(zip(phases, saved['phases'])):
                for key in ('label', 'incoming', 'outgoing', 'waiting',
                            'host_changes', 'modeled_bank', 'guard'):
                    assert phase[key] == row[key], (name, i, j, key)
                assert row['external_reads'] == sum(e['region'] == 'external' for e in phase['events'])
                stem = '%s_%03d_phase_%02d' % (prefix, i, j)
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
                    assert (folder / filename).read_bytes() == data
                    assert hashlib.sha256(data).hexdigest() == row['artifacts'][filename]
                if name == 'results':
                    assert phase['guard'] is None
                else:
                    assert phase['guard']['problem'] == 'unsupported_TRAP'
                    assert phase['outgoing']['pc'] == 0x49fb6
            records.append((normalized, fx, phases))
        groups.append(records)
    assert len(groups[0]) == report['cases']
    assert sum(len(x[2]) for x in groups[0]) == report['phases']
    assert len(groups[1]) == report['guard_cases']
    assert report['fresh_CPU_runs'] == 2 * (len(groups[0]) + len(groups[1]))
    return native, groups[0], groups[1], refs


def compare_guards(exe, folder, records, resources):
    rows = []
    marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
    for i, (selection, fx, phases) in enumerate(records):
        assert len(phases) == 1 and phases[0]['guard']['problem'] == 'unsupported_TRAP'
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=fx['entry_pc'])
        actual = common.invoke(exe, folder, 'native_TRAP_checked_API_%03d' % i,
                               fx['ram'], state, fx['pvc'], fx['bank_base'], resources,
                               stop=fx['stop_pc'], external=fx['external'])
        result, ram, pvc, ports, error = actual
        assert not result['ok'] and 'initializer TRAP15' in error
        assert {k: result[k] for k in common.REGS + ('pc',)} == state
        assert ram == fx['ram'] and pvc == fx['pvc'] and ports == marker
        assert result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(selection=selection, native_guard_PC=0x49fb6,
                         native_partial_writes_observed=True,
                         checked_API_error=error, all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    return rows


def caller_boundary_failures(exe, folder, records, resources):
    rows = []
    for entry, expected_return in ((0x47cec, 0x47d20), (0x47f04, 0x47f0a)):
        fx = next(fx for selection, fx, phases in records
                  if fx['entry_pc'] == entry and len(phases) == 1)
        state = dict(fx['regs'], a7=fx['initial_a7'], pc=entry)
        actual = common.invoke(exe, folder, 'negative_past_caller_%06x' % entry,
                               fx['ram'], state, fx['pvc'], fx['bank_base'], resources,
                               stop=expected_return + 2, external=fx['external'])
        result, ram, pvc, ports, error = actual
        assert not result['ok'] and 'unsupported animation machine PC' in error
        assert {k: result[k] for k in common.REGS + ('pc',)} == state
        assert ram == fx['ram'] and pvc == fx['pvc']
        assert ports == struct.pack('>BII', 1, 0xdeadbeef, 0x87)
        assert result['bank_base'] == fx['bank_base']
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(entry=entry, unmodeled_caller_return=expected_return,
                         stop=expected_return + 2, error=error,
                         all_API_outputs_preserved=True))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    # Import before capturing source identities: replay must not precede its
    # provenance snapshot. End checks below reject edits during any phase.
    import observe_animation_machine_callers as native
    inputs = dependencies(ROOT)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = digest(path)
    test_path = ROOT / 'engine/tests/animation_machine_callers_test.cpp'
    assert test_path.is_file()
    inputs[str(test_path.relative_to(ROOT))] = digest(test_path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    native, records, guards, native_refs = audit_native(ROOT, program, source)
    refs.update(native_refs)
    exe, command = compile_harness(ROOT, OUT)
    matches = compare(exe, OUT, records, resources)
    guarded = compare_guards(exe, OUT, guards, resources)
    boundary_errors = caller_boundary_failures(exe, OUT, records, resources)
    for name, expected in inputs.items():
        assert digest(ROOT / name) == expected, name
    for name, expected in refs.items():
        assert digest(ROOT / name) == expected, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_guard
    artifacts = {str(p.resolve()): digest(p) for p in OUT.iterdir()
                 if p.is_file() and p != report_path}
    refs.update(artifacts)
    canonical = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in canonical or canonical[key] == expected
        canonical[key] = expected
    report = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  native_cases_replayed=len(records), native_phases_replayed=sum(len(x[2]) for x in records),
                  native_guards_replayed=len(guards), actual_CPP=matches,
                  checked_initializer_TRAP_failures=guarded,
                  checked_caller_boundary_failures=boundary_errors,
                  negative_count=len(guarded) + len(boundary_errors),
                  compile_command=command, normalized_reference_paths=len(canonical),
                  failure=None, ROM_unchanged=True,
                  limits=['Controlled initializer/actual caller paths, not natural scheduler or gameplay reachability.',
                          'Full16registers/PC/RAM/status/orderedPVC/externalreads match original. No CCR/carry/timing/hardware claim.',
                          'Native initializer TRAP guard stops before the original TRAP instruction after partial writes; API checked failure rolls back all outputs. These are distinct contracts, not native exception equivalence.',
                          'C++ device PVC/bank is independently folded from native writes; raw native PVC lacks side effects and has no PVC reads.',
                          'Resumes use previous actual C++ outputs and only recorded host changes, never injected native expected state.',
                          'Generated harness is test plumbing, not a production CLI or filesystem atomicity claim.',
                          'Execution stops at caller boundaries47d20/47f0a; subsequent BRA/TST and general caller CCR are outside this unit.'])
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=matches['cases'], phases=matches['phases'],
                          resumes=matches['previous_actual_CPP_resumes'],
                          negatives=report['negative_count'], sha256=digest(report_path))))


if __name__ == '__main__':
    main()
