"""Fail closed on the explicitly reviewed F4 original differential matrix boundaries.

This post-audit does not execute game code or turn incomplete native rows into passes.
It checks the frozen full verifier output against the reviewed input/boundary manifest.
"""
import argparse
import hashlib
import json
import os
import gzip
import observe_animation_machine_objects_g1 as native
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# F5 external-read queue: the only permitted public header change since 9d5aa11 (additive: AnimationMachineExternalRead and
# AnimationMachineDevice::reads). Pinned hash; the diff versus 9d5aa11 must contain zero deleted lines.
PUBLIC_HEADER = 'engine/include/ms5/animation_machine.h'
PUBLIC_HEADER_SHA256 = '0e9ed25b4ae745d9fab7bd8c01795d00096a526404c222abf1bf59ed77b738e2'
STEP_LIMITS = {
    'u06-eb7f2', 'u06-eba3e-bank2', 'u06-eba3e-bank3',
    'u06-eba3e-ram-list', 'u06-eba3e-bank3-short',
    'u06-eba3e-hi', 'u06-eba3e-bank4',
    'pvc-bank eba3e LONG80(A6)=2',
}
DENOMINATORS = {'01':105,'02':133,'03':83,'04':69,'05':71,'06':135,'07':85,
                '08':181,'08b':165,'09':150,'10':223,'11':215,'12':162,
                '13':76,'14':78,'15':175,'15b':144,'15c':196,'16':39}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    # The report path may also come from the environment (OBJECTS_F4_REPORT) so the audit can run against a scratch regeneration.
    parser.add_argument('report', type=Path, nargs='?', default=Path(os.environ.get('OBJECTS_F4_REPORT') or ROOT/'artifacts/animation_machine_objects_integration_execution/execution.json'))
    # Sanitizer anchor report (earlier header hashes); MS5_HEADER_ANCHOR overrides the default build/ location (e.g. a scratch tree).
    parser.add_argument('--anchor', type=Path, default=Path(os.environ.get('MS5_HEADER_ANCHOR') or ROOT/'build/sanitize-u15review/verification.json'))
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    rows = report['results']
    assert report['complete_requested_matrix'] and report['rows'] == len(rows) == 4743
    assert report['total_available_inputs'] == 4743 and not report['mismatches']
    assert report['executed_tool_sha256'] == sha(ROOT/'tools/verify_animation_machine_objects_g1.py')
    assert all(sha(ROOT/path) == value for path,value in report['inputs'].items())
    # align2 run (scratch tree at 10b3c2d, objects_g1 verifier, 4743 rows): measured 4679/55/8/1.
    # Superseded pins (later F4 units route more PCs): execution-equal 4657 -> 4679, checked-boundary 77 -> 55.
    expected = {'execution-equal':4679,'checked-boundary':55,'native-step-limit':8,
                'invalid-declared-flag-precondition':1}
    assert report['verdicts'] == expected, report['verdicts']
    assert {row['name'] for row in rows if row['verdict']=='native-step-limit'} == STEP_LIMITS
    g1_folder = ROOT/'artifacts/animation_machine_objects_g1_native'
    assert sha(g1_folder/'observation.json') == '04b4a91dd1b81708305f605d19fda986c88d3cb3b1c0c1e1478f88d4530bd94a'
    g1_obs = json.loads((g1_folder/'observation.json').read_text())
    fixture_file = g1_folder/g1_obs['fixtures_file']['file']
    assert sha(fixture_file) == g1_obs['fixtures_file']['sha256']
    fixtures = json.load(gzip.open(fixture_file,'rt'))['fixtures']
    for fixture in fixtures:
        start = fixture['start']
        ram = (g1_folder/'blobs'/(start['ram']+'.bin')).read_bytes()
        assert hashlib.sha256(ram).hexdigest() == start['ram']
        assert native.g1_digest(dict(start,ram=ram)) == start['state']
    assert {row['name'] for row in rows if row['unit']=='g1'} == {fixture['name'] for fixture in fixtures if fixture['final']=='stop'}
    for row in rows:
        assert not row.get('differences'), row['name']
        if 'test' in row['provenance']:
            assert sha(ROOT/row['provenance']['test']) == row['provenance']['test_sha256']
        if row['verdict'] == 'checked-boundary':
            assert row['rollback_verified'], row['name']
            evidence = row['checked_error_evidence']
            if row['cpp_error']=='unsupported animation machine PC':
                assert evidence['native_reaches_actual_missing_PC'] and evidence['current_dispatch_missing']
                assert evidence['diagnostic_public_outputs_equal']
                assert evidence['actual_CPP_missing_PC'] != 0x500000
        if row['verdict'] == 'invalid-declared-flag-precondition':
            assert row['name']=='carry-consumer d73ca ccr=04'
            assert (row['input_D0_WORD'],row['input_RAM_WORD'],row['input_CCR']) == (1,2,4)
            assert row['original_G1_input_preserved']
            assert not row['execution_equality_claimed'] and not row['checked_CPP_boundary_claimed']
    # align2: the G1 verifier now globs every objects-u*-contract.md; units added after this matrix (17..20b) are outside the native G1 matrix and
    # must show zero native-observed starts here (their coverage lives in their own unit verifiers).
    assert set(DENOMINATORS) <= set(report['contract_coverage'])
    later_units = sorted(set(report['contract_coverage']) - set(DENOMINATORS))
    assert later_units == ['17','18','19','20','20b'], later_units
    for unit in later_units:
        assert report['contract_coverage'][unit]['native_observed_starts'] == 0, unit
    for unit,denominator in DENOMINATORS.items():
        coverage = report['contract_coverage'][unit]
        assert coverage['block_denominator'] == denominator
        assert sha(ROOT/('docs/analysis/animation-machine-objects-u%s-contract.md'%unit)) == coverage['contract_sha256']
        missing = [0xeb7f2] if unit=='06' else ([0x46928] if unit=='08b' else [])
        assert coverage['missing_native_starts'] == missing, (unit,coverage)
        assert coverage['native_observed_starts'] == denominator-len(missing)
    assert all(0x500000 not in pcs for pcs in report['instruction_PC_coverage'].values())
    anchor_path = args.anchor
    anchor = json.loads(anchor_path.read_text())
    headers = {path:value for path,value in anchor['inputs'].items() if path.endswith('.h')}
    expected_headers = {str(path.relative_to(ROOT)) for path in (ROOT/'engine/include').rglob('*.h')}
    internal_header = 'engine/src/animation_machine_internal.h'
    expected_headers.add(internal_header)
    assert set(headers) == expected_headers and anchor['all_inputs_unchanged']
    # align2: the private header gains declarations with each later F4 unit; public headers stay identical except the pinned additive external-read queue change in animation_machine.h, the private one additive only.
    assert PUBLIC_HEADER in headers
    assert all(sha(ROOT/path)==value for path,value in headers.items() if path not in (internal_header,PUBLIC_HEADER))
    assert sha(ROOT/PUBLIC_HEADER)==PUBLIC_HEADER_SHA256 and headers[PUBLIC_HEADER]!=PUBLIC_HEADER_SHA256
    changed = subprocess.run(['git','diff','--name-only','9d5aa11','--','engine/include'],
                             cwd=ROOT,capture_output=True,text=True,check=True)
    assert changed.stdout.split()==[PUBLIC_HEADER], changed.stdout    # exactly the pinned additive change, no other public header
    public_numstat = subprocess.run(['git','diff','--numstat','9d5aa11','--',PUBLIC_HEADER],cwd=ROOT,capture_output=True,text=True,check=True).stdout.split()
    assert public_numstat and int(public_numstat[0]) > 0 and int(public_numstat[1]) == 0, public_numstat    # deletions == 0: additive only
    numstat = subprocess.run(['git','diff','--numstat','9d5aa11','--',internal_header],cwd=ROOT,capture_output=True,text=True,check=True).stdout.split()
    assert numstat and int(numstat[1]) == 0, numstat    # no deleted/modified lines
    receipt = dict(schema_version=1, accepted=True, report_sha256=sha(args.report),
                   audit_tool_sha256=sha(Path(__file__)), verdicts=expected,
                   original_execution_equal_rows=4657, excluded_native_step_limit_rows=sorted(STEP_LIMITS),
                   excluded_invalid_declared_flag_rows=['carry-consumer d73ca ccr=04'],
                   native_coverage_gaps={'06':[0xeb7f2],'08b':[0x46928]},
                   claim='Reviewed bounded matrix; excluded rows and checked boundaries are not execution equality.')
    receipt['header_temporal_anchor'] = dict(earlier_report_sha256=sha(anchor_path), earlier_and_current_hash_agreement=True,
        header_count=len(headers), git_comparison_ref='9d5aa11', header_diff_empty=False, public_header_diff_files=[PUBLIC_HEADER], public_header_additive_only=True,
        public_header_added_lines=int(public_numstat[0]), public_header_sha256=PUBLIC_HEADER_SHA256,
        public_header_identical_count=len(headers)-2, public_header_count=len(headers)-1,
        private_header_additive_only=True, private_header_added_lines=int(numstat[0]), private_header_sha256=sha(ROOT/internal_header),
        claim='Independent earlier/current agreement; the F4 execution tool itself did not capture header hashes.')
    path = args.report.parent/'acceptance.json'
    assert not path.exists(), path
    path.write_text(json.dumps(receipt,indent=1,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))


if __name__ == '__main__':
    main()
