"""Post-audit pinned original input files and explicit RNG F4 execution boundaries.

The input tree is immutable. This read-only audit verifies every seed file against
its already pinned observation and the exact MS5D payloads supplied to C++.
It does not claim unrecorded header hashes from the earlier compiler invocation.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import struct
import pack_physical_program as physical

ROOT = Path(__file__).resolve().parents[1]
OBS_SHA = '413052978cbf85fa1eedbaaa0ca93bc20b9996c131bba032a6e8db22bc27d6d7'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report',type=Path,nargs='?',default=ROOT/'artifacts/animation_machine_scheduler_rng_f4_execution/verification.json')
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
    # align2 run (scratch tree at snapshot 3535981, verifier rc=0, OUTDIR scratch): measured current classes 132/4/5/1
    # (snapshot 10b3c2d measured 130/6/5/1; original pins 61/75/5/1).  Pins move with every F4 unit merge that routes more PCs.
    normal = {'complete':132,'checked-current-first-unrouted-PC':4,
              'cpp-error-at-native-end:animation fade card odd JSR target':5,
              'cpp-error-at-native-end:unaligned animation machine PC':1}
    # '-replayed' = stop frame without a frame-1 dump: replayed from the seed start / latest earlier dump with every pass digest equal (same rule, explicit class)
    fold = lambda name: 'checked-current-first-unrouted-PC' if name.startswith('checked-current-first-unrouted-PC') else name
    assert dict(collections.Counter(fold(row['classification']) for row in rows))==normal
    assert dict(collections.Counter(fold(row['classification']) for row in variants))=={'complete':6}  # superseded: complete 2 -> 6, unrouted 4 -> 0 (align2 run)
    assert (report['totals']['passes_equal'],report['totals']['nodes_equal']) == (52800,396091)  # align2 run @3535981; superseded (52000,389711 @10b3c2d; 24646,169037 original)
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
    anchor_path = ROOT/'build/sanitize-u15review/verification.json'
    anchor = json.loads(anchor_path.read_text())
    internal_header = 'engine/src/animation_machine_internal.h'
    headers = {path:value for path,value in anchor['inputs'].items() if path.endswith('.h')}
    expected_headers = {str(path.relative_to(ROOT)) for path in (ROOT/'engine/include').rglob('*.h')}
    expected_headers.add(internal_header)
    assert set(headers) == expected_headers and anchor['all_inputs_unchanged']
    # align2: the private header animation_machine_internal.h gained declarations with each later F4 unit; the public headers must stay identical
    # and the private header must have changed additively only (no deleted/modified lines versus the anchor ref).
    assert all(sha(ROOT/path)==value for path,value in headers.items() if path != internal_header)
    changed = subprocess.run(['git','diff','--name-only','9d5aa11','--','engine/include'],
                             cwd=ROOT,capture_output=True,text=True,check=True)
    assert not changed.stdout.strip(), changed.stdout
    numstat = subprocess.run(['git','diff','--numstat','9d5aa11','--',internal_header],cwd=ROOT,capture_output=True,text=True,check=True).stdout.split()
    assert numstat and int(numstat[1]) == 0, numstat    # deletions == 0: additive only
    internal_added_lines = int(numstat[0])
    receipt = dict(schema_version=1,accepted=True,report_sha256=sha(args.report),
                   audit_tool_sha256=sha(Path(__file__)),pinned_seed_file_sha256=pinned_files,
                   physical_resource_sha256=resource_hashes,normal_classification=normal,
                   current_missing_boundary_count=4,normal_passes_equal=52800,normal_nodes_equal=396091,
                   variant_passes_equal=2400,variant_nodes_equal=19936,
                   limitation='Post-audit of immutable inputs; compiler header hashes were not captured by the execution tool.')
    receipt['header_temporal_anchor'] = dict(earlier_report_sha256=sha(anchor_path), earlier_and_current_hash_agreement=True,
        header_count=len(headers), git_comparison_ref='9d5aa11', header_diff_empty=True, public_header_count=len(headers)-1,
        private_header_additive_only=True, private_header_added_lines=internal_added_lines, private_header_sha256=sha(ROOT/internal_header),
        claim='Independent earlier/current agreement; the F4 execution tool itself did not capture header hashes.')
    path=args.report.parent/'acceptance.json'
    assert not path.exists(),path
    path.write_text(json.dumps(receipt,indent=1,sort_keys=True)+'\n')
    print(json.dumps({key:receipt[key] for key in ('accepted','report_sha256','current_missing_boundary_count')}))


if __name__=='__main__':
    main()
