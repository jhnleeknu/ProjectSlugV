"""G3 N03..N16a acceptance through the public C++ machine API.

The pinned G2 comparison engine is reused as a library, without modifying it.
G3 supplies its own contracts, fixtures, complete matrix, strict guard probes,
provenance, failure injection and report. Declared reentries are not execution
chains. Native observers are read-only; outputs must be local nonsymlink paths.
"""
import argparse
import collections
import copy
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import sys
import shutil
import subprocess
import capstone
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_animation_machine_objects_g2 as V
import observe_animation_machine_objects_g3 as N

OBS_SHA = '5bab5b216f7e3af4870544bf5f4467ec0507e836fe7def10bda1c957c816849f'
FX_SHA = '37a7762b9ac9d6554851be6d9327c1bb73f6827e0dec371e8f250dbb45c6c437'
NATIVE = ROOT / 'artifacts/animation_machine_objects_g3_native'
OUT = ROOT / 'artifacts/animation_machine_objects_g3_execution'
SCRATCH = ROOT / 'build/g3_acceptance'
ORIGINAL_EXPLAIN = V.explain_error
ORIGINAL_PROBE = V.probe_task
ORIGINAL_FIXTURE = V.fixture_task
ORIGINAL_FLOW = V.run_cpp_flow
ORIGINAL_SEGMENT = V.cpp_segment
ORIGINAL_GROUPS = V.phase_groups
ORIGINAL_BLOCK = V.native_block
EXTERNAL_PROOFS = [None]
LOADED_FILES = set()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_output(path, directory=True):
    path = Path(path)
    assert '..' not in path.parts, ('parent traversal output forbidden', path)
    path = path.absolute()
    assert path.is_relative_to(ROOT), ('output outside local checkout', path)
    relative = path.relative_to(ROOT)
    current = ROOT
    for part in relative.parts:
        current = current / part
        assert not current.is_symlink(), ('symlink output forbidden', current)
    if directory:
        path.mkdir(parents=True, exist_ok=True)
    else:
        assert not path.is_dir(), ('file output is directory', path)
    return path


def negative_output_paths():
    outside = ROOT.parent / ('g3-output-negative-%d' % os.getpid())
    assert not outside.exists(), outside
    results = {}
    for kind, path in (('parent_traversal', ROOT / '..' / outside.name),
                       ('absolute_outside', outside)):
        rejected = False
        try:
            local_output(path)
        except AssertionError:
            rejected = True
        results['reject_' + kind] = rejected and not outside.exists()
    parent = local_output(SCRATCH / 'path-validation')
    for name, target, child, directory in (
            ('file-link', ROOT / 'Makefile', None, False),
            ('dir-link', ROOT, outside.name, True)):
        link = parent / name
        assert not link.exists() and not link.is_symlink(), link
        link.symlink_to(target)
        rejected = False
        try:
            try:
                local_output(link / child if child else link, directory)
            except AssertionError:
                rejected = True
            results['reject_' + name] = rejected
        finally:
            link.unlink()
    assert not outside.exists()
    assert not (ROOT / outside.name).exists()
    return results


def native_setup():
    program = N.G2.setup_sched()
    env = N.Env3()
    N.analyze_units3(env)
    for c in env.contracts.values():
        c['lists'] = dict(flow=c['flow'], producers=c['producers'])
    N.GLOBAL.update(env=env, program=program, out=NATIVE, fix_limit=20000,
                    plan={}, twice=False, records=N.G2.load_records())
    V.ENV[0] = env
    return env


def explain_error(nat, a, b, begin, target, seg, gk, units):
    result = ORIGINAL_EXPLAIN(nat, a, b, begin, target, seg, gk, units)
    if result['cls'] == 'checked-callee':
        reviewed = {'unsupported animation command or dispatch alignment': 0x49ffe,
                    'unsupported sprite callback target': 0xcd58}
        result['ok'] = result['ok'] and seg['error'] in V.BLACKBOX_ALLOWED
        if seg['error'] in reviewed:
            result['ok'] = result['ok'] and result['ev']['diag_pc'] == reviewed[seg['error']]
        if seg['error'] == 'objects n19 caller requires known carry':
            dpc = result['ev']['diag_pc']
            result['ok'] = result['ok'] and dpc == 0xb1fdc and units == [0]
            if result['ok']:
                # Stop immediately before the reviewed external consumer and
                # compare its full actually executed prefix; never compare its
                # native known C to the C++ Unknown as an equivalence claim.
                ns = nat.states[nat.pieces[a]['start']]
                prefix = V.native_flow(ns, (dpc,), V.O.GLOBAL['fix_limit'])
                cpp = V.cpp_segment(V.server(), begin, dpc)
                diffs = ['prefix-not-reached']
                if prefix.final['kind']=='stop' and cpp['kind']=='ok':
                    ports, ext = V.native_phase_expect(prefix, 0, len(prefix.pieces)-1)
                    diffs = V.compare_ok_segment(cpp, begin, prefix.states[-1], ports, ext)
                    if cpp['cur']['carry'] != 0: diffs.append('expected-unknown-boundary')
                result['ev'].update(reviewed_external_consumer='N19 b1fdc BCS', prefix_diffs=diffs, phase_input_carry=begin['carry'], consumer_input_carry=cpp['cur']['carry'], native_predecessor_pcs=[hex(pc) for piece in nat.pieces[:a] for pc in piece['pcs']][-8:])
                result['ok'] = not diffs
                if EXTERNAL_PROOFS[0] is not None: EXTERNAL_PROOFS[0].append(copy.deepcopy(result))
    if result['cls'] == 'native-unmasked-address':
        # Address masking diverges after the native fault. Require the actual
        # checked error and diagnostic rollback, but do not claim reach after
        # that fault; the G2 guard_prefix separately compares the bounded prefix.
        result['ok'] = bool(result['ev']['preserved'] and result['ev']['diag_error_same'])
        result['ev']['excluded_after_native_address_mask_divergence'] = True
    if gk == 'cpu-exception' and seg['error'] == 'objects n13 DIVU zero divisor':
        detail = nat.final['detail'].get('detail', {})
        result['cls'] = 'table'
        result['ok'] = bool(detail.get('number') == 5 and result['ev']['preserved']
                            and result['ev']['diag_error_same'] and result['ev']['native_reached_diag_pc'])
    return result


def phase_groups(nat):
    groups = ORIGINAL_GROUPS(nat)
    merged = []
    i = 0
    while i < len(groups):
        a, b = groups[i]
        while (i + 1 < len(groups)
               and nat.states[nat.pieces[b]['end']]['pc'] == 0x71c98
               and 0x71c86 in V.reached_pcs(nat, a, b)):
            i += 1
            b = groups[i][1]
        merged.append((a, b))
        i += 1
    return merged


def native_block(st, start, unit, limit=400):
    if start != 0x71c86:
        return ORIGINAL_BLOCK(st, start, unit, limit)
    env = V.ENV[0]
    stops = tuple(sorted((set(env.starts) | set(env.boundary) | set(env.traps)) - {start}))
    flow = V.native_flow(st, stops, limit)
    if flow.final['kind'] != 'stop':
        return dict(kind=flow.final['kind'], guard=flow.final['detail'].get('kind'), n=sum(len(p['pcs']) for p in flow.pieces))
    ports, ext = V.native_phase_expect(flow, 0, len(flow.pieces)-1)
    return dict(kind='stop', pc=flow.states[-1]['pc'], state=flow.states[-1],
                ports=ports, ext=ext, n=sum(len(p['pcs']) for p in flow.pieces))


def run_cpp_flow(srv, nat, st, carry0, tag, declared_carry=True, with_whole=False):
    # G2 has a native-unmasked-address fast path that deliberately skips
    # explain_error. Capture the real production phase input, then require the
    # checked rollback and diagnostic error; only the prefix is comparable.
    calls = []
    def capture(server, begin, target):
        segment = ORIGINAL_SEGMENT(server, begin, target)
        if server is srv:
            calls.append((begin, target, segment))
        return segment
    V.cpp_segment = capture
    try:
        result = ORIGINAL_FLOW(srv, nat, st, carry0, tag, declared_carry, with_whole)
    finally:
        V.cpp_segment = ORIGINAL_SEGMENT
    res = result[0]
    boundary = res.get('boundary')
    if boundary and boundary['cls'] == 'native-unmasked-address':
        a, b = V.phase_groups(nat)[boundary['phase']]
        pc = nat.states[nat.pieces[a]['start']]['pc']
        matching = [(begin, seg) for begin, target, seg in calls
                    if begin['pc'] == pc and target == V.IMPOSSIBLE_STOP]
        proof = dict(cls='native-unmasked-address', ok=False,
                     ev=dict(reason='production phase input missing'))
        if matching:
            begin, seg = matching[0]
            if seg['kind'] == 'error':
                proof = explain_error(nat, a, b, begin, V.IMPOSSIBLE_STOP,
                                      seg, 'read-unmapped', V.phase_unit_set(nat, a, b))
            else:
                proof['ev'] = dict(reason='production completed native guard', result=seg['kind'])
        boundary.update(ok=proof['ok'], ev=proof['ev'])
        if not proof['ok']:
            res['errors'].append(('unmasked-guard-evidence', proof))
    return result


def fixture_task(arg):
    index, fixture = arg
    EXTERNAL_PROOFS[0] = []
    try:
        row = ORIGINAL_FIXTURE(arg)
        row['external_carry_boundaries'] = EXTERNAL_PROOFS[0]
    finally:
        EXTERNAL_PROOFS[0] = None
    if index in (1278, 1281):
        state = V.O.load_state(fixture['start'])
        pc = state['pc']
        expected_n = not bool(state['regs']['d1'] & 0x8000) if pc == 0x5b326 else bool(state['regs']['d2'] & 0x8000)
        actual_n = bool(state['ccr'] & 8)
        assert pc == (0x5b326 if index == 1278 else 0xbddb4) and actual_n != expected_n
        row['raw_comparison'] = dict(cls=row['cls'], errors=row['errors'])
        row['cls'] = 'excluded:contradictory-caller-N'
        row['errors'] = []
        row['no_execution_equivalence'] = True
        row['precondition'] = dict(expected_n=expected_n, actual_n=actual_n, formula='not bit15 D1.W' if pc == 0x5b326 else 'bit15 D2.W', counterpart=1279 if index == 1278 else 1280)
    if fixture['kind'] == 'carry-consumer' and fixture['start']['pc'] == 0xc637c:
        st = V.O.load_state(fixture['start'])
        nat = V.native_flow(st, (0xc6380,), 400)
        begin = V.start_state(st, 0)
        seg = V.cpp_segment(V.server(), begin, 0xc6380)
        ports, ext = V.native_phase_expect(nat, 0, len(nat.pieces)-1)
        row['consumer_passthrough'] = (nat.final['kind'] == 'stop' and seg['kind']=='ok' and not V.compare_ok_segment(seg, begin, nat.states[-1], ports, ext) and seg['cur']['carry']==0)
        row['consumer_semantics'] = 'observer model names consumer; ROM branch target equals fallthrough; contract pass-through'
    # Never silently accept a skipped requested fixture.
    if row['cls'] == 'recorded-state-not-reached':
        row['cls'] = 'DIFF:requested-state-not-reached'
    return row


def probe_task(start):
    result = ORIGINAL_PROBE(start)
    env = V.ENV[0]
    state, origin = V.probe_start_state(start)
    if state is None:
        return result
    for cin, row in result['runs'].items():
        if row.get('cpp') != 'native-guard':
            continue
        st = dict(state, ccr=((state['ccr'] or 0) & ~1) | cin)
        stops = tuple(sorted((set(env.starts) | set(env.boundary) | set(env.traps)) - {start}))
        native = V.native_flow(st, stops, 400)
        if native.final['kind'] != 'guard' or not native.pieces:
            row['guard_ok'] = False
            row['guard_evidence'] = dict(reason='native single-block guard not regenerated')
            continue
        begin = V.start_state(st, 1 + cin)
        seg = V.cpp_segment(V.server(), begin, V.IMPOSSIBLE_STOP)
        kind = native.final['detail']['kind']
        if seg['kind'] != 'error':
            row['guard_ok'] = False
            row['guard_evidence'] = dict(reason='production completed native guard', result=seg['kind'])
            continue
        units = V.phase_unit_set(native, 0, len(native.pieces) - 1)
        proof = explain_error(native, 0, len(native.pieces) - 1, begin, V.IMPOSSIBLE_STOP, seg, kind, units)
        # Checked boundary and exact native guard are reported separately.
        row['guard_evidence'] = proof
        row['guard'] = [kind, seg['error']]
        row['guard_ok'] = proof['ok'] and proof['cls'] in ('table', 'interior-landing', 'unknown-carry-boundary', 'caller-x-2986', 'checked-callee')
    if start in (0x792ac, 0x7961e):
        # EORI CCR consumes C even though RAM/registers/destination are equal.
        result['dep'] = True
        result['dependency_kind'] = 'output-carry inversion'
        begin = V.start_state(state, 0)
        seg = V.cpp_segment(V.server(), begin, V.IMPOSSIBLE_STOP)
        diagnostic = V.cpp_segment(V.dserver(), begin, V.IMPOSSIBLE_STOP)
        exact = (seg['kind']=='error' and seg['error']==V.UNKNOWN_CARRY[env.starts[start]] and seg['preserved'] and diagnostic.get('diag_pc')==start and diagnostic.get('error')==seg['error'])
        result['unknown_in'] = 'error-exact' if exact else 'DIFF:carry-inversion-consumer'
    bad = [row for row in result['runs'].values()
           if row.get('cpp') not in ('match', 'self-loop-skipped', 'native-guard')
           or row.get('cout_ok') is False or row.get('guard_ok') is False]
    result['class'] = 'DIFF' if bad or str(result.get('unknown_in')).startswith('DIFF') else 'ok'
    return result


def configure(args):
    V.ROOT = ROOT
    V.NATIVE_DIR = NATIVE
    V.OUT = OUT
    V.SCRATCH = SCRATCH
    V.WORKERS = args.workers
    V.LIMIT_ONLY_CASES = args.cases
    V.UIDS = N.UIDS
    V.UNAME = N.NAMES
    V.ULABEL = {u: N.UNITS[u]['file'] for u in N.UIDS}
    V.UNSUPPORTED_UNIT = {u: 'unsupported animation objects %s PC' % label for u, label in V.ULABEL.items()}
    V.UNKNOWN_CARRY = {u: 'objects %s caller requires known carry' % label for u, label in V.ULABEL.items()
                       if 'caller requires known carry' in (ROOT / ('engine/src/animation_machine_objects_%s.cpp' % label)).read_text()}
    V.GUARD_TABLE = dict(V.GUARD_TABLE)
    V.GUARD_TABLE['cpu-exception'] = (V.UNSUPPORTED_MACHINE, 'objects n13 DIVU zero divisor')
    V.GUARD_TABLE['unicorn-error'] = (V.UNSUPPORTED_MACHINE, V.UNALIGNED_PC) + tuple(V.UNSUPPORTED_UNIT.values())
    V.BLACKBOX_ALLOWED = V.BLACKBOX_ALLOWED + ('unsupported animation command or dispatch alignment', 'unsupported sprite callback target', 'objects n19 caller requires known carry') + tuple('unsupported animation objects n%02d PC' % i for i in range(1, 36))
    V.native_setup = native_setup
    V.explain_error = explain_error
    V.probe_task = probe_task
    V.fixture_task = fixture_task
    V.run_cpp_flow = run_cpp_flow
    V.phase_groups = phase_groups
    V.native_block = native_block


def provenance():
    paths = [ROOT / 'Makefile', Path(__file__)]
    paths += sorted((ROOT / 'engine/src').glob('*.cpp'))
    paths += sorted((ROOT / 'engine/src').glob('*.h'))
    paths += sorted((ROOT / 'engine/include').rglob('*.h'))
    paths += [ROOT / 'tools' / name for name in ('verify_animation_machine_objects_g2.py',) + tuple(N.IMPORTS)] if hasattr(N, 'IMPORTS') else []
    paths += [ROOT / 'tools' / name for name in json.loads((NATIVE / 'observation.json').read_text())['inputs']['tools']]
    paths += [ROOT / 'tools/verify_animation_machine_objects_g2.py']
    paths += [N.contract_path(u) for u in N.UIDS]
    paths += [ROOT / 'docs/analysis/animation-machine-objects-n19-contract.md']
    paths += sorted((ROOT / 'extracted/runtime/program_rom').glob('*.ms5d'))
    paths += [ROOT / 'tools/disassemble_program.py', ROOT / 'extracted/program/manifest.json', N.S.ROM_PATH, N.S.F3_CONTRACT, N.S.SEED_OBS, N.G2.SCHED_DIR / 'observation.json', N.G2.RNG_DIR / 'observation.json']
    seeds = json.loads(N.S.SEED_OBS.read_text())
    paths += [N.S.SEED_DIR / phase['ram_file'] for result in seeds['results'] for phase in result['phases'] if phase['final_pc']==0xff000 and phase['name'] in ('begin', 'release-poisoned-prefix')]
    paths += list(LOADED_FILES)
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): digest(p) for p in sorted(set(paths))}


def pinned_inputs():
    obs = json.loads((NATIVE / 'observation.json').read_text())
    assert digest(NATIVE / 'observation.json') == OBS_SHA
    assert digest(NATIVE / 'fixtures.json.gz') == FX_SHA
    for directory, mapping in (('docs/analysis', obs['inputs']['contracts']), ('tools', obs['inputs']['tools'])):
        for name, expected in mapping.items():
            assert digest(ROOT / directory / name) == expected, name
    # Hash all compressed cases and every deduplicated native state blob, without
    # copying them. This binds captures used by load_state and natural replay.
    native_manifest = {str(p.relative_to(NATIVE)): digest(p) for p in sorted(NATIVE.rglob('*')) if p.is_file()}
    return obs, native_manifest


def negative_bad_results():
    base = dict(ram=bytes(65536), pvc=bytes(8192), regs={k: 0 for k in V.KEYS},
                pc=0x100, carry=1, bank=0x200000)
    expected = dict(ram=base['ram'], regs=base['regs'], pc=base['pc'], bank=(base['bank'], 0, 0), ccr=0)
    results = {}
    for field in ('ram', 'regs', 'pc', 'pvc', 'bank'):
        mutated = copy.deepcopy(base)
        if field == 'ram': mutated[field] = bytes([1]) + base[field][1:]
        elif field == 'pvc': mutated[field] = bytes([1]) + base[field][1:]
        elif field == 'regs': mutated[field]['d0'] = 1
        else: mutated[field] += 2
        results['reject_' + field] = bool(V.diff_state(mutated, expected, base['pvc']))
    for field in ('ports', 'reads'):
        seg = dict(kind='ok', cur=base, ports=[], reads=0, waits=[])
        seg[field] = [(1, 1, 1)] if field == 'ports' else 1
        results['reject_' + field] = bool(V.compare_ok_segment(seg, base, expected, [], 0))
    res = dict(carry_checked=0, carry_bad=0, carry_unknown=0, errors=[])
    V.carry_check(res, dict(base, carry=2), expected)
    results['reject_carry'] = res['carry_bad'] == 1
    results['reject_waits'] = not V.waits_equal([dict(pc=0x3aea, kind='sound', live=1, compared=0, released=True)], [])
    return results


def negatives_stage(workers, base_row):
    env = V.ENV[0]
    tasks = []
    for unit in N.UIDS:
        contract = env.contracts[unit]
        starts = set(contract['starts'])
        even = [pc for lo, hi in contract['ranges'] for pc in range(lo, hi, 2)]
        odd = [pc for lo, hi in contract['ranges'] for pc in range(lo + 1, hi, 2)]
        for kind, pcs in (('interior', [pc for pc in even if pc not in starts]), ('odd', odd), ('zero', sorted(starts))):
            for i in range(0, len(pcs), 200):
                tasks.append((kind, dict(unit=unit, pcs=pcs[i:i+200], base=base_row)))
    tasks.append(('unrouted', dict(base=base_row)))
    with multiprocessing.get_context('fork').Pool(workers, initializer=V.pool_init) as pool:
        return list(pool.imap(V.negatives_task, tasks, chunksize=1))


def summarize_natural(rows):
    totals = collections.Counter()
    classes = collections.Counter()
    for row in rows:
        totals.update(row['counters'])
        classes.update(row['classes'])
    totals['nodes'] = sum(row['nodes'] for row in rows)
    return dict(totals=dict(totals), classes=dict(classes), cases=rows,
                definition='match: actual C++ output chain; match-partial: declared native reentry after a checked external callee; guard/boundary: checked rejection, not execution equivalence')


def summarize_fixtures(rows):
    return dict(count=len(rows), classes=dict(collections.Counter(row['cls'] for row in rows)), rows=rows,
                declared_entries=sum(row['kind'] in ('entry-self', 'entry-declared') for row in rows))


def probe_checks(rows, env):
    by_start = {int(row['start'], 16): row for row in rows}
    # Invert/Computed producers are evaluated against exact native Cout per
    # fixture, not mistaken for fixed Set/Clear.
    prod_bad = []
    for unit in N.UIDS:
        for pc, wanted in env.contracts[unit]['producers'].items():
            row = by_start.get(pc)
            if row is None or row['class'] != 'ok':
                prod_bad.append([hex(pc), wanted, 'missing or failed'])
            elif wanted in ('Clear', 'Set') and row['cls'] != wanted.lower():
                prod_bad.append([hex(pc), wanted, row['cls']])
    return dict(probes_all_starts=len(rows) == len(env.starts), probes_no_diff=all(row['class'] == 'ok' for row in rows),
                known_producers_no_diff=not prod_bad), prod_bad


def main(argv=None):
    global OUT, SCRATCH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--cases', type=lambda text: [int(x) for x in text.split(',')], default=[])
    parser.add_argument('--fixture-limit', type=int, default=0)
    parser.add_argument('--stages', default='natural,fixtures,probes,negatives')
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--scratch', type=Path, default=SCRATCH)
    parser.add_argument('--reuse-build', action='store_true')
    args = parser.parse_args(argv)
    if sys.flags.optimize: raise RuntimeError('optimized Python disables acceptance assertions')
    assert 1 <= args.workers <= 3
    OUT = local_output(args.out)
    SCRATCH = local_output(args.scratch)
    local_output(OUT / 'verification.json', directory=False)
    assert not (OUT / 'verification.json').exists(), 'choose a new output directory'
    configure(args)
    t0 = time.time()
    obs, native_hashes = pinned_inputs()
    LOADED_FILES.update(Path(module.__file__).resolve() for module in tuple(sys.modules.values()) if getattr(module, '__file__', None) and Path(module.__file__).is_file())
    LOADED_FILES.add(Path(sys.executable).resolve())
    LOADED_FILES.add(Path(N.S.uclib._name).resolve())
    LOADED_FILES.add(Path(capstone._cs._name).resolve())
    decoder_before = dict(version=capstone.__version__, library=str(Path(capstone._cs._name).resolve()), sha256=digest(capstone._cs._name))
    oracle_before = dict(version=N.unicorn.__version__, library=str(Path(N.S.uclib._name).resolve()), sha256=digest(N.S.uclib._name))
    assert oracle_before['version'] == obs['oracle']['version']
    before = provenance()
    compiler = Path(shutil.which('clang++')).resolve()
    compiler_before = dict(path=str(compiler), sha256=digest(compiler), version=subprocess.check_output([str(compiler), '--version'], text=True))
    rom_before = V.rom_stat()
    assert rom_before[0] == N.ROM_SHA
    V.RUN_ROOT[0] = local_output(SCRATCH / 'run')
    build = local_output(SCRATCH / 'build')
    for name in ('harness_batch.cpp', 'harness_batch_diag.cpp', 'animation_machine_diag.cpp',
                 'objects_g2_batch_harness', 'objects_g2_batch_harness_diag',
                 'compile.log', 'compile_diag.log', 'source-freeze.json'):
        local_output(build / name, directory=False)
    path_checks = negative_output_paths()
    build_manifest = build / 'source-freeze.json'
    if args.reuse_build:
        prior = json.loads(build_manifest.read_text())
        assert prior['inputs'] == before, 'compiled inputs changed: rebuild harness'
        for name, expected in prior['binaries'].items(): assert digest(build / name) == expected
        exe, diagnostic = build / 'objects_g2_batch_harness', build / 'objects_g2_batch_harness_diag'
        commands = prior['commands']
    else:
        exe, diagnostic, cmd, dcmd = V.build_harness(build)
        commands = [cmd, dcmd]
        prior = dict(inputs=before, binaries={exe.name: digest(exe), diagnostic.name: digest(diagnostic)}, commands=commands)
        build_manifest.write_text(json.dumps(prior, indent=1, sort_keys=True) + '\n')
    generated = {p.name: digest(p) for p in build.glob('*.cpp')}
    assert before == provenance(), 'inputs changed during build'
    V.EXE[:] = [exe, diagnostic, sorted(str(p) for p in (ROOT / 'extracted/runtime/program_rom').glob('*.ms5d'))]
    assert len(V.EXE[2]) == 8
    env = native_setup()
    stages = args.stages.split(',')
    assert set(stages) <= {'natural', 'fixtures', 'probes', 'negatives'}
    report = dict(schema_version=1, tool='tools/verify_animation_machine_objects_g3.py',
                  observation_sha256=OBS_SHA, fixtures_sha256=FX_SHA, inputs=before, native_input_sha256=native_hashes,
                  binaries=prior['binaries'], generated_sources=generated, compiler=compiler_before, native_oracle=oracle_before, native_decoder=decoder_before, commands=commands, contract_discrepancies=obs['discrepancies'],
                  discrepancy_evidence={'710c6': 'ROM 2d400064 MOVE.L D0,64(A6); 710ca 4a80 TST.L D0; 710cc 6a000004 BPL 710d2. Contract grouped wording parser associated 710a0 TST.W/BEQ with 710c6.', '494b4': 'ROM LEA 100cb8,A0; 494ba ORI #1,CCR; RTS. External 77604 BCC 7760e consumes carry; N08 contract explicitly excludes external consumers.'},
                  discrepancy_policy='Preserved pending original-evidence review; successful executable differential does not automatically resolve contract wording.',
                  complete_requested_matrix=not args.cases and not args.fixture_limit and set(stages)=={'natural','fixtures','probes','negatives'})
    checks = negative_bad_results()
    checks.update(path_checks)
    report['bad_result_tests'] = negative_bad_results()
    report['output_path_tests'] = path_checks
    if 'natural' in stages:
        rows = V.natural_stage(args.workers)
        report['natural'] = summarize_natural(rows)
        totals = report['natural']['totals']
        checks.update(natural_cases=len(rows)==(len(args.cases) if args.cases else 290),
                      natural_nodes=bool(args.cases) or totals['nodes']==30632,
                      natural_record_regeneration=all(row['seed_ok'] for row in rows),
                      natural_no_diff=all(not any(cls.startswith('DIFF') for cls in row['classes']) and not row['bad'] for row in rows),
                      natural_unit_pieces=totals['unit_pieces']==totals['unit_pieces_ok'], natural_carry=totals['carry_bad']==0)
        print('natural done', json.dumps(totals), flush=True)
    if 'fixtures' in stages:
        fx = json.load(gzip.open(NATIVE / 'fixtures.json.gz'))['fixtures']
        jobs = list(enumerate(fx[:args.fixture_limit] if args.fixture_limit else fx))
        with multiprocessing.get_context('fork').Pool(args.workers, initializer=V.pool_init) as pool:
            rows = list(pool.imap_unordered(fixture_task, jobs, chunksize=1))
        rows.sort(key=lambda row: row['index'])
        report['fixtures'] = summarize_fixtures(rows)
        checks.update(fixtures_count=len(rows)==(args.fixture_limit or 2459),
                      fixtures_regeneration=all(row['regen_ok'] for row in rows),
                      fixtures_no_diff=all(not row['cls'].startswith('DIFF') and not row['errors'] for row in rows),
                      fixtures_carry=all(row['carry_bad']==0 for row in rows),
                      fixtures_through=all(not row.get('through') or (row['through']['regen_ok'] and not row['through']['cls'].startswith('DIFF') and not row['through']['errors']) for row in rows),
                      fixture_consumers_exact=all(row.get('consumer_passthrough') is True if row.get('consumer_semantics') else row.get('consumer_unknown') is True for row in rows if row['kind']=='carry-consumer'),
                      valid_N_counterparts=all(row['cls']=='match' and not row['errors'] for row in rows if row['index'] in (1279,1280)),
                      fixtures_unknown=all(not str(row['unknown_carry']).startswith('DIFF') for row in rows))
        print('fixtures done', json.dumps(report['fixtures']['classes']), flush=True)
    if 'probes' in stages:
        rows = V.probe_stage(args.workers)
        new_checks, prod_bad = probe_checks(rows, env)
        checks.update(new_checks)
        report['probes'] = dict(count=len(rows), rows=rows, producer_failures=prod_bad)
        print('probes done', json.dumps(new_checks), flush=True)
    if 'negatives' in stages:
        captures = V.probe_state_sources(env)[0]
        rows = negatives_stage(args.workers, captures[sorted(captures)[0]][2])
        counts = collections.Counter()
        for row in rows: counts.update(row['counts'])
        failures = [failure for row in rows for failure in row['fails']]
        checks['negatives_exact_error_full_rollback'] = not failures and not any('DIFF' in key for key in counts)
        report['negatives'] = dict(counts=dict(counts), failures=failures)
        print('negatives done', json.dumps(dict(counts)), flush=True)
    checks['decoder_unchanged'] = decoder_before == dict(version=capstone.__version__, library=str(Path(capstone._cs._name).resolve()), sha256=digest(capstone._cs._name))
    checks['oracle_unchanged'] = oracle_before == dict(version=N.unicorn.__version__, library=str(Path(N.S.uclib._name).resolve()), sha256=digest(N.S.uclib._name))
    checks['compiler_unchanged'] = compiler_before == dict(path=str(compiler), sha256=digest(compiler), version=subprocess.check_output([str(compiler), '--version'], text=True))
    checks['generated_sources_unchanged'] = generated == {p.name: digest(p) for p in build.glob('*.cpp')}
    checks['inputs_unchanged'] = before == provenance()
    checks['rom_unchanged'] = rom_before == V.rom_stat()
    checks['native_unchanged'] = all(digest(NATIVE / name)==expected for name,expected in native_hashes.items())
    checks['binaries_unchanged'] = all(digest(build / name)==expected for name,expected in prior['binaries'].items())
    report.update(checks=checks, accepted=all(checks.values()) and report['complete_requested_matrix'], seconds=round(time.time()-t0, 2))
    path = local_output(OUT / 'verification.json', directory=False)
    path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps(dict(checks=checks, accepted=report['accepted'], report_sha256=digest(path)), sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
