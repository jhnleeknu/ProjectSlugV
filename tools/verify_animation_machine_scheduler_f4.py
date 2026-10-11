"""Supplemental differential diagnostics for existing declared scheduler records.

This inherited normal-seed tool reports matches but is not an independent strict
acceptance gate. Use the audited RNG F4 suite and the typed matrix acceptance gate
for integration acceptance; preserved unknown errors alone are insufficient.
"""
import collections, concurrent.futures, gzip, hashlib, json, os, struct, subprocess, sys
from pathlib import Path
MAIN = Path(__file__).resolve().parents[1]
NAT = MAIN / 'artifacts/animation_machine_scheduler_native'
PVC = MAIN / 'artifacts/animation_machine_pvc_banks_native'
PVC_SHA = '613bd4648d7ed3035620ad1949e1be4c94e4e866635a788a423df6c9650a65fe'
PVC_CASES = (58, 59)
OBS_SHA = 'c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff'
S = MAIN / 'artifacts/animation_machine_scheduler_f4_execution'
EXE = S / 'sched_diff'
WORK = S / 'work'
RES = sorted(str(p) for p in (MAIN / 'extracted/runtime/program_rom').glob('*.ms5d'))
KEYS = ('d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5','a6','a7')


def sha(b): return hashlib.sha256(b).hexdigest()


def state_digest(ram, regs, pc, bank):
    h = hashlib.sha256(); h.update(b'MS5-SCHED-STATE-1'); h.update(ram); h.update(struct.pack('>16I', *[regs[k] for k in KEYS]))
    h.update(struct.pack('>IIIHH', pc, bank[0], 0, bank[1] & 0xffff, bank[2] & 0xffff)); return h.hexdigest()


def one(case):
    NAT = PVC if case in PVC_CASES else globals()['NAT']
    doc = json.load(gzip.open(NAT / 'seeds' / ('seed_%04d.json.gz' % case)))
    start = [d for d in doc['dumps'] if d['kind'] == 'seed-start']; assert len(start) == 1
    st = start[0]; ram = (NAT / 'blobs' / (st['ram'] + '.bin')).read_bytes(); assert sha(ram) == st['ram']
    assert state_digest(ram, st['regs'], st['pc'], st['bank']) == st['state']
    assert int.from_bytes(ram[0x4ca4:0x4ca8], 'big') == 0x1ff000
    base, ff8, ff9 = st['bank']; pvc = bytearray(8192); pvc[0x1ff0:0x1ff2] = ff8.to_bytes(2, 'big'); pvc[0x1ff2:0x1ff4] = ff9.to_bytes(2, 'big')
    passes = doc['passes']; frames = len(passes)
    blob = ram + bytes(pvc) + struct.pack('>16I', *[st['regs'][k] for k in KEYS]) + struct.pack('>III', st['pc'], base, frames)
    inp = WORK / ('in_%04d.bin' % case); out = WORK / ('out_%04d.jsonl' % case); inp.write_bytes(blob)
    r = subprocess.run([str(EXE), str(inp), str(out)] + RES, capture_output=True, text=True, close_fds=False, timeout=7200)
    assert r.returncode == 0, (case, r.returncode, r.stderr)
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    inp.unlink()
    res = dict(case=case, kind=doc.get('kind'), native_frames=frames, native_stop=doc['stop'], covered=doc.get('covered'), cpp_passes=len(rows),
               pass_equal=0, node_equal=0, node_compared=0, mismatches=[], cpp_stop=None, chain_unequal=0)
    for i, row in enumerate(rows):
        p = passes[i]
        if row['start'] != p['start']: res['mismatches'].append(dict(frame=i, what='start')); break
        nn = p['nodes']; cn = row.get('nodes', [])
        for j, c in enumerate(cn):
            if j >= len(nn): res['mismatches'].append(dict(frame=i, what='extra-node', node=c)); break
            n = nn[j]
            if 'error' in c:
                if c['entry'] != n['entry'] or c['a6'] != n['a6'] or c['cb'] != n['cb']:
                    res['mismatches'].append(dict(frame=i, what='node-entry-at-error', j=j))
                break
            res['node_compared'] += 1
            if (c['a6'], c['cb'], c['entry'], c['exit'], c['ports_sha']) == (n['a6'], n['cb'], n['entry'], n['exit'], n['ports_sha']):
                res['node_equal'] += 1
            else:
                res['mismatches'].append(dict(frame=i, what='node', j=j, cpp=c, native={k: n[k] for k in ('a6', 'cb', 'entry', 'exit', 'ports', 'ports_sha', 'partial')}))
                break
        if 'error' in row or 'host_reject' in row:
            fail = next((c for c in cn if 'error' in c), None)
            res['cpp_stop'] = dict(frame=i, error=row.get('error'), preserved=row.get('preserved'), host_reject=row.get('host_reject'), chain_error=row.get('chain_error'),
                                   node_cb=fail['cb'] if fail else None, node_a6=fail['a6'] if fail else None, native_pass_stop=p['stop'], native_covA=p.get('covA'))
            break
        if not row['chain_equal']: res['chain_unequal'] += 1
        if p['stop'] != 'frame-head': res['mismatches'].append(dict(frame=i, what='cpp-completed-native-stopped', native=p['stop'])); break
        if row['end'] == p['end'] and len(cn) == len(nn): res['pass_equal'] += 1
        else: res['mismatches'].append(dict(frame=i, what='end', cpp=row['end'], native=p['end'])); break
        assert row['a7'] == 0x1ff000 - 4 and row['stack'] == 0x2ac2 and row['a6'] == 0x100820 and row['a5'] == 0x108000 and row['a0'] == row['pc'] and row['pc'] in (0xe4a, 0xe74)
    out.unlink()
    return res


def main():
    assert sha((NAT / 'observation.json').read_bytes()) == OBS_SHA and sha((PVC / 'observation.json').read_bytes()) == PVC_SHA
    S.mkdir(parents=True, exist_ok=False)
    WORK.mkdir()
    import verify_animation_machine as common
    harness = MAIN / 'tools/animation_machine_scheduler_f4_harness.cpp'
    sources = [MAIN / 'engine/src' / name for name in common.SOURCES]
    source = MAIN / 'engine/src/physical_rom_resource.cpp'
    if source not in sources: sources.append(source)
    command = ['clang++','-std=c++11','-O2','-Wno-deprecated-declarations','-I'+str(MAIN/'engine/include')] + list(map(str,sources)) + [str(harness),'-o',str(EXE)]
    subprocess.run(command,check=True,capture_output=True)
    assert len(RES) == 8
    provenance = {'native_observation_sha256': OBS_SHA, 'PVC_observation_sha256': PVC_SHA,
                  'sources': {str(p.relative_to(MAIN)): sha(p.read_bytes()) for p in sources + [harness,Path(__file__)]},
                  'build_command': command, 'scope': 'Declared scheduler frame model; original ROM data; no IRQ/boot claim'}
    (S/'provenance.json').write_text(json.dumps(provenance,indent=1,sort_keys=True))
    cases = sorted(int(p.name[5:9]) for p in (NAT / 'seeds').glob('seed_*.json.gz'))
    if len(sys.argv) > 1: cases = [int(x) for x in sys.argv[1].split(',')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('W', '3'))) as ex:
        results = list(ex.map(one, cases))
    (S / os.environ.get('OUTJSON', 'diff_results.json')).write_text(json.dumps(results, indent=1, sort_keys=True))
    tot = collections.Counter(); errs = collections.Counter(); cbs = collections.Counter()
    for r in results:
        tot['seeds'] += 1; tot['passes_equal'] += r['pass_equal']; tot['nodes_equal'] += r['node_equal']; tot['nodes_compared'] += r['node_compared']
        tot['mismatch_seeds'] += bool(r['mismatches']); tot['chain_unequal'] += r['chain_unequal']
        if r['cpp_stop']:
            errs[(r['cpp_stop']['error'], r['cpp_stop']['frame'] == 0, r['cpp_stop']['preserved'])] += 1
            cbs['%x' % r['cpp_stop']['node_cb'] if r['cpp_stop']['node_cb'] is not None else 'none'] += 1
        if r['covered'] or r['native_frames'] >= 200:
            print('seed', r['case'], 'native frames', r['native_frames'], 'pass_equal', r['pass_equal'], 'stop', r['native_stop'].get('reason'), 'cpp', r['cpp_stop'] and r['cpp_stop']['error'])
    print(dict(tot)); print(errs); print(cbs.most_common())
    for r in results:
        if r['mismatches']: print('MISMATCH', r['case'], json.dumps(r['mismatches'][:2])[:800])
    assert tot['mismatch_seeds'] == 0 and tot['chain_unequal'] == 0, dict(tot)
    assert all(not r['cpp_stop'] or r['cpp_stop'].get('preserved') is not False for r in results)


if __name__ == '__main__':
    main()
