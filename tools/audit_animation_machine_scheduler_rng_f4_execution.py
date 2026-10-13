"""Post-audit pinned original input files and explicit RNG F4 execution boundaries.

The input tree is immutable. This read-only audit verifies every seed file against
its already pinned observation and the exact MS5D payloads supplied to C++.
It does not claim unrecorded header hashes from the earlier compiler invocation.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import pack_physical_program as physical

ROOT = Path(__file__).resolve().parents[1]
# F5 external-read queue: the only permitted public header change since 9d5aa11 (additive: AnimationMachineExternalRead and
# AnimationMachineDevice::reads). Pinned hash; the diff versus 9d5aa11 must contain zero deleted lines.
PUBLIC_HEADER = 'engine/include/ms5/animation_machine.h'
PUBLIC_HEADER_SHA256 = '0e9ed25b4ae745d9fab7bd8c01795d00096a526404c222abf1bf59ed77b738e2'
OBS_SHA = '413052978cbf85fa1eedbaaa0ca93bc20b9996c131bba032a6e8db22bc27d6d7'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    # The report path may also come from the environment (RNG_F4_REPORT) so the audit can run against a scratch regeneration.
    parser.add_argument('report',type=Path,nargs='?',default=Path(os.environ.get('RNG_F4_REPORT') or ROOT/'artifacts/animation_machine_scheduler_rng_f4_execution/verification.json'))
    # Sanitizer anchor report (earlier header hashes); MS5_HEADER_ANCHOR overrides the default build/ location (e.g. a scratch tree).
    parser.add_argument('--anchor',type=Path,default=Path(os.environ.get('MS5_HEADER_ANCHOR') or ROOT/'build/sanitize-u15review/verification.json'))
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    native = ROOT/'artifacts/animation_machine_scheduler_rng_native'
    observation = native/'observation.json'
    assert sha(observation) == OBS_SHA == report['native']['observation_sha256']
    obs = json.loads(observation.read_text())
    manifests = obs['seeds'] + obs['variants_answer00']
    assert len(obs['seeds']) == 142 and len(obs['variants_answer00']) == 6
    pinned_files = {}
    for item in manifests:
        path = native/item['file']
        assert path.stat().st_size == item['file_size'] and sha(path) == item['file_sha256']
        pinned_files[item['file']] = item['file_sha256']
    resources = sorted((ROOT/'extracted/runtime/program_rom').glob('*.ms5d'))
    assert len(resources) == 8
    combined = bytearray()
    resource_hashes = {}
    for index,path in enumerate(resources):
        data = path.read_bytes()
        assert struct.unpack_from('<I',data,16)[0] == index*0x100000
        payload = physical.validate_container(data)
        assert len(payload)==0x100000
        combined.extend(payload)
        resource_hashes[str(path.relative_to(ROOT))] = sha(path)
    assert hashlib.sha256(combined).hexdigest() == physical.SOURCE_SHA256 == report['rom']['sha256']
    assert report['executed_tool_sha256'] == sha(ROOT/'tools/verify_animation_machine_scheduler_rng_f4.py')
    assert all(sha(ROOT/path)==value for path,value in report['engine_source_sha256'].items())
    rows,variants = report['seeds'],report['variants_answer00']['seeds']
    assert {row['case'] for row in rows} == {item['case'] for item in obs['seeds']} and len(rows)==142
    assert {row['case'] for row in variants} == {item['case'] for item in obs['variants_answer00']} and len(variants)==6
    # b70a71a run (scratch OUTDIR, verifier rc=0): measured 134 complete / 2 unrouted / 5 / 1; passes_equal 53600, nodes_equal 403677
    # (previous pins: 132/4/5/1 and 52800/396091 at 3535981).
    # align2 run (scratch tree at snapshot 3535981, verifier rc=0, OUTDIR scratch): measured current classes 132/4/5/1
    # (snapshot 10b3c2d measured 130/6/5/1; original pins 61/75/5/1).  Pins move with every F4 unit merge that routes more PCs.
    normal = {'complete':134,'checked-current-first-unrouted-PC':2,
              'cpp-error-at-native-end:animation fade card odd JSR target':5,
              'cpp-error-at-native-end:unaligned animation machine PC':1}
    # '-replayed' = stop frame without a frame-1 dump: replayed from the seed start / latest earlier dump with every pass digest equal (same rule, explicit class)
    fold = lambda name: 'checked-current-first-unrouted-PC' if name.startswith('checked-current-first-unrouted-PC') else name
    assert dict(collections.Counter(fold(row['classification']) for row in rows))==normal
    assert dict(collections.Counter(fold(row['classification']) for row in variants))=={'complete':6}  # superseded: complete 2 -> 6, unrouted 4 -> 0 (align2 run)
    assert (report['totals']['passes_equal'],report['totals']['nodes_equal']) == (53600,403677)  # b70a71a run; superseded (52800,396091 @3535981; 52000,389711 @10b3c2d; 24646,169037 original)
    assert (report['variants_answer00']['totals']['passes_equal'],report['variants_answer00']['totals']['nodes_equal']) == (2400,19936)  # align2 run; superseded (844,6116)
    for row in rows+variants:
        assert not row['mismatches'] and row['chain_unequal']==0
        assert row['node_compared']==row['node_equal']
        if row['cpp_stop']:
            assert row['cpp_stop']['preserved'] is True
        if row['classification'].startswith('checked-current-first-unrouted-PC'):
            evidence=row['current_boundary_evidence']
            assert evidence['approved'] and evidence['node_entry_matches_frozen_native']
            assert evidence['completed_native_node_prefix_equal']
            assert evidence['current_first_missing_PC'] == evidence['native_reason']['pc']
            assert evidence['callback'] == row['cpp_stop']['node_cb']
            assert evidence['frame'] == row['cpp_stop']['frame'] == row['pass_equal']
            assert evidence['replayed_equal_passes'] == (evidence['frame']-evidence['first_replayed_frame'] if evidence['replay_from'].startswith('pass-end-dump') or evidence['replay_from']=='seed-start' else 0)
    anchor_path = args.anchor
    anchor = json.loads(anchor_path.read_text())
    internal_header = 'engine/src/animation_machine_internal.h'
    headers = {path:value for path,value in anchor['inputs'].items() if path.endswith('.h')}
    expected_headers = {str(path.relative_to(ROOT)) for path in (ROOT/'engine/include').rglob('*.h')}
    expected_headers.add(internal_header)
    assert set(headers) == expected_headers and anchor['all_inputs_unchanged']
    # align2: the private header animation_machine_internal.h gained declarations with each later F4 unit; the public headers must stay identical (except the pinned additive external-read queue change in animation_machine.h)
    # and the private header must have changed additively only (no deleted/modified lines versus the anchor ref).
    assert PUBLIC_HEADER in headers
    assert all(sha(ROOT/path)==value for path,value in headers.items() if path not in (internal_header,PUBLIC_HEADER))
    assert sha(ROOT/PUBLIC_HEADER)==PUBLIC_HEADER_SHA256 and headers[PUBLIC_HEADER]!=PUBLIC_HEADER_SHA256
    changed = subprocess.run(['git','diff','--name-only','9d5aa11','--','engine/include'],
                             cwd=ROOT,capture_output=True,text=True,check=True)
    assert changed.stdout.split()==[PUBLIC_HEADER], changed.stdout    # exactly the pinned additive change, no other public header
    public_numstat = subprocess.run(['git','diff','--numstat','9d5aa11','--',PUBLIC_HEADER],cwd=ROOT,capture_output=True,text=True,check=True).stdout.split()
    assert public_numstat and int(public_numstat[0]) > 0 and int(public_numstat[1]) == 0, public_numstat    # deletions == 0: additive only
    numstat = subprocess.run(['git','diff','--numstat','9d5aa11','--',internal_header],cwd=ROOT,capture_output=True,text=True,check=True).stdout.split()
    assert numstat and int(numstat[1]) == 0, numstat    # deletions == 0: additive only
    internal_added_lines = int(numstat[0])
    receipt = dict(schema_version=1,accepted=True,report_sha256=sha(args.report),
                   audit_tool_sha256=sha(Path(__file__)),pinned_seed_file_sha256=pinned_files,
                   physical_resource_sha256=resource_hashes,normal_classification=normal,
                   current_missing_boundary_count=2,normal_passes_equal=53600,normal_nodes_equal=403677,
                   variant_passes_equal=2400,variant_nodes_equal=19936,
                   limitation='Post-audit of immutable inputs; compiler header hashes were not captured by the execution tool.')
    receipt['header_temporal_anchor'] = dict(earlier_report_sha256=sha(anchor_path), earlier_and_current_hash_agreement=True,
        header_count=len(headers), git_comparison_ref='9d5aa11', header_diff_empty=False, public_header_diff_files=[PUBLIC_HEADER], public_header_additive_only=True,
        public_header_added_lines=int(public_numstat[0]), public_header_sha256=PUBLIC_HEADER_SHA256,
        public_header_identical_count=len(headers)-2, public_header_count=len(headers)-1,
        private_header_additive_only=True, private_header_added_lines=internal_added_lines, private_header_sha256=sha(ROOT/internal_header),
        claim='Independent earlier/current agreement; the F4 execution tool itself did not capture header hashes.')
    path=args.report.parent/'acceptance.json'
    assert not path.exists(),path
    path.write_text(json.dumps(receipt,indent=1,sort_keys=True)+'\n')
    print(json.dumps({key:receipt[key] for key in ('accepted','report_sha256','current_missing_boundary_count')}))


if __name__=='__main__':
    main()
