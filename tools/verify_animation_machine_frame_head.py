"""Strict F5 original execution acceptance; immutable archived inputs, explicit boundaries.

Natural/variant H runs stop at controller c52a. Declared BYTE 108d3c bit7
segments stop at 31d6. Neither boundary executes the controller/new D1 unit.
"""
import argparse
import collections
import ctypes
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import unicorn
import observe_animation_machine_scheduler as S
import observe_animation_machine_pvc_banks as PB
import verify_animation_machine as common

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'artifacts/animation_machine_frame_head_native'
OUT = ROOT / 'artifacts/animation_machine_frame_head_execution'
BUILD = ROOT / 'build/frame_head_acceptance'
OBS_SHA = '4fe4f796879af90df1c1fd4c753485a9bf0a04d2667b14b8c00dbab23879b16b'
EXT = {0x3c0006: (2, 0), 0x300000: (1, 255), 0x340000: (1, 255), 0x380000: (1, 255)}


def require(ok, detail):
    if not ok:
        raise RuntimeError(str(detail))


def local_output(path, directory=True):
    path = Path(path).absolute()
    require(path.is_relative_to(ROOT), ('output outside local checkout', path))
    current = ROOT
    for part in path.relative_to(ROOT).parts:
        current = current / part
        require(not current.is_symlink(), ('symlink output forbidden', current))
    if directory:
        path.mkdir(parents=True, exist_ok=True)
    return path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def page(bank):
    p = bytearray(8192)
    p[0x1ff0:0x1ff4] = struct.pack('>HH', bank[1], bank[2])
    return bytes(p)


def wait_release(m, pc):
    r = m.regs()
    a5 = r['a5']
    if pc == 0xef2 and m.byte(a5 - 0x7fea) < m.byte(a5 - 0x7fe9):
        address, size, value = a5 - 0x7fea, 1, m.byte(a5 - 0x7fe9)
    elif pc == 0x16bd0 and m.word(a5 + 0xd34) != (r['d0'] & 65535):
        address, size, value = a5 + 0xd34, 2, r['d0'] & 65535
    elif pc == 0x3aea and m.word(a5 - 0x328c) == (r['d1'] & 65535):
        address, size, value = 0x104d74, 2, 65535
    elif pc == 0xcda4 and m.word(a5 + 0xd34) != (r['d4'] & 65535):
        address, size, value = a5 + 0xd34, 2, r['d4'] & 65535
    else:
        return None
    before = int.from_bytes(m.cpu.mem_read(address, size), 'big')
    return pc, address, size, before, value


def native(program, fixed, state, queue, stop, defaults=False):
    m = PB.PvcMachine(program, fixed, state)
    m.install_basic_hooks()
    c = m.cpu
    for base in (0x340000, 0x380000):
        c.mem_map(base, 4096, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    consumed, waits, bad = [], [], []
    rest = list(queue)
    result = {'stop': False, 'wait': None}

    def read(uc, access, address, size, value, user):
        if address not in EXT:
            return
        if defaults:
            n, v = EXT[address]
            if n != size:
                bad.append(('external size', address, size))
                uc.emu_stop()
                return
        else:
            if not rest or rest[0][:2] != (address, size):
                bad.append(('external order', address, size, rest[:1]))
                uc.emu_stop()
                return
            _, n, v = rest.pop(0)
        uc.mem_write(address, v.to_bytes(n, 'big'))
        consumed.append((address, size, v))

    def code(uc, pc, size, user):
        if pc == stop:
            result['stop'] = True
            uc.emu_stop()
            return
        release = wait_release(m, pc) if pc in (0xef2, 0x16bd0, 0x3aea, 0xcda4) else None
        if release is not None:
            result['wait'] = release
            uc.emu_stop()

    c.hook_add(unicorn.UC_HOOK_MEM_READ, read, begin=0x300000, end=0x3fffff)
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    cur = state['pc']
    while True:
        c.emu_start(cur, 0xffffff, count=6000000)
        require(not bad and m.odd is None and m.invalid is None and m.intr is None,
                ('native error', bad, m.odd, m.invalid, m.intr))
        if result['wait'] is None:
            break
        release = result['wait']
        result['wait'] = None
        waits.append(release)
        require(len(waits) <= 64, 'native wait limit')
        _, address, size, _, value = release
        m.put(address, size, value)
        cur = release[0]
        c.reg_write(S.UC_REG['pc'], cur)
    require(result['stop'], ('native did not reach declared boundary', hex(stop)))
    # The historical observer tracks ff8/ff9 side effects separately; its mapped
    # page retains the raw last CPU write. Normalize only these four bytes.
    pvc = bytearray(c.mem_read(0x2fe000, 8192))
    pvc[0x1ff0:0x1ff4] = struct.pack('>HH', m.ff8, m.ff9)
    return dict(ram=m.ram(), regs=m.regs(), pc=stop, bank=(m.bank, m.ff8, m.ff9),
                pvc=bytes(pvc), ports=[(a, n, v) for _, a, n, v in m.ports],
                consumed=consumed, remaining=rest, waits=waits, status=0)


def request(state, queue, stop):
    values = [state['regs'][k] for k in S.KEYS] + [state['pc'], 0, state['bank'][0], stop, len(queue), 0]
    return struct.pack('>22I', *values) + state['ram'] + page(state['bank']) + b''.join(struct.pack('>III', *e) for e in queue)


def exact(stream, n):
    data = stream.read(n)
    require(len(data) == n, ('truncated harness response', len(data), n))
    return data


def invoke(proc, payload):
    proc.stdin.write(struct.pack('>I', len(payload)) + payload)
    proc.stdin.flush()
    size = struct.unpack('>I', exact(proc.stdout, 4))[0]
    require(4 <= size <= 1048576, 'invalid harness packet size')
    return exact(proc.stdout, size)


def parse(payload):
    require(len(payload) >= 100, ('harness error', payload[:200]))
    v = struct.unpack_from('>25I', payload)
    ok, status, pc, carry, bank, consumed, np, nq, nw = v[:9]
    require(ok == 1 and status == 0 and carry in (0, 1, 2), 'invalid harness result')
    require(len(payload) == 100 + 65536 + 8192 + 12 * (np + nq) + 20 * nw, 'invalid result length')
    at = 100
    ram = payload[at:at + 65536]
    at += 65536
    pvc = payload[at:at + 8192]
    at += 8192
    ports = [struct.unpack_from('>III', payload, at + i * 12) for i in range(np)]
    at += np * 12
    remaining = [struct.unpack_from('>III', payload, at + i * 12) for i in range(nq)]
    at += nq * 12
    waits = [struct.unpack_from('>5I', payload, at + i * 20) for i in range(nw)]
    return dict(ram=ram, pvc=pvc, regs=dict(zip(S.KEYS, v[9:])), pc=pc,
                bank=bank, consumed=consumed, ports=ports, remaining=remaining, waits=waits, status=status, carry=carry)


def compare(actual, expected, queue):
    for key in ('ram', 'pvc', 'regs', 'pc', 'ports', 'remaining', 'waits', 'status'):
        require(actual[key] == expected[key], ('C++ mismatch', key))
    require(actual['bank'] == expected['bank'][0], 'C++ bank mismatch')
    require(actual['consumed'] == len(expected['consumed']), 'C++ consumed count mismatch')
    require(queue[:actual['consumed']] == expected['consumed'], 'C++ consumed contents mismatch')
    require(queue[actual['consumed']:] == actual['remaining'], 'C++ remaining contents mismatch')


def negatives(proc, state, queue, stop, expected):
    payload = invoke(proc, request(state, queue, stop))
    got = parse(payload)
    compare(got, expected, queue)
    tests = []
    for name, mutate in (
            ('RAM', lambda b: b.__setitem__(100, b[100] ^ 1)),
            ('PVC', lambda b: b.__setitem__(100 + 65536, b[100 + 65536] ^ 1)),
            ('PC', lambda b: b.__setitem__(11, b[11] ^ 2)),
            ('register', lambda b: b.__setitem__(39, b[39] ^ 1)),
            ('bank', lambda b: b.__setitem__(19, b[19] ^ 1)),
            ('ordered-port', lambda b: b.__setitem__(100 + 65536 + 8192 + 11, b[100 + 65536 + 8192 + 11] ^ 1)),
            ('read-count', lambda b: b.__setitem__(23, b[23] ^ 1)),
            ('status', lambda b: b.__setitem__(7, 1)),
            ('truncated', lambda b: b.pop())):
        bad = bytearray(payload)
        mutate(bad)
        try:
            compare(parse(bytes(bad)), expected, queue)
        except RuntimeError:
            tests.append(name)
        else:
            raise RuntimeError('negative accepted: ' + name)
    sentinel = (0x300000, 1, 0x5a)
    extra_queue = queue + [sentinel]
    extra_expected = dict(expected, remaining=[sentinel])
    extra_payload = invoke(proc, request(state, extra_queue, stop))
    compare(parse(extra_payload), extra_expected, extra_queue)
    bad = bytearray(extra_payload)
    # Remaining queue follows the ordered port list, and must be compared by value.
    at = 100 + 65536 + 8192 + 12 * len(expected['ports']) + 11
    bad[at] ^= 1
    try:
        compare(parse(bytes(bad)), extra_expected, extra_queue)
    except RuntimeError:
        tests.append('remaining-queue-content')
    else:
        raise RuntimeError('remaining queue mutation accepted')
    tests.append('remaining-queue-preserved')
    # Harness semantic rejection is a failed record, never a success packet.
    bad = invoke(proc, b'bad request')
    require(bad[:4] == b'\0\0\0\0', 'malformed request accepted')
    try:
        parse(bad)
    except RuntimeError:
        tests.append('harness-error')
    else:
        raise RuntimeError('harness error accepted')
    # A standalone consumer must also fail with a nonzero process exit.
    path = OUT / 'negative-result.bin'
    path.write_bytes(payload[:-1])
    child = subprocess.run([sys.executable, '-c',
        'import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); '
        'import verify_animation_machine_frame_head as v; v.parse(Path(sys.argv[2]).read_bytes())',
        str(ROOT / 'tools'), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(child.returncode != 0, 'bad result process exit was zero')
    tests.append('bad-result-nonzero-exit')
    broken = subprocess.run(proc.args, input=b'\0\0\0\x10short', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(broken.returncode != 0, 'truncated request transport exit was zero')
    tests.append('bad-request-nonzero-exit')
    return tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-seeds', type=int, help='sample per family; never full acceptance')
    parser.add_argument('--mode', choices=('all', 'natural', 'variants', 'derived'), default='all')
    args = parser.parse_args()
    require(not sys.flags.optimize, 'optimized Python disables dependency audit assertions')
    require(args.max_seeds is None or args.max_seeds > 0, 'positive sample required')
    local_output(OUT)
    local_output(BUILD)
    for target in (OUT / 'verification.json', OUT / 'build.stderr', OUT / 'harness.stderr',
                   OUT / 'negative-result.bin', BUILD / 'frame_head_acceptance'):
        local_output(target, directory=False)
    report_path = OUT / 'verification.json'
    if report_path.exists():
        report_path.unlink()
    started = time.time()
    require(digest(OBS / 'observation.json') == OBS_SHA, 'native observation hash')
    obs = json.loads((OBS / 'observation.json').read_text())
    # Archived tool/import inputs must match their original recorded identity.
    for name, sha in obs['inputs'].items():
        if isinstance(sha, str):
            require(digest(ROOT / name) == sha, ('archived input changed', name))
    require(unicorn.__version__ == obs['oracle']['version'], 'oracle version')
    libraries = list(Path(unicorn.__file__).parent.rglob('libunicorn*.dylib')) + list(Path(unicorn.__file__).parent.rglob('libunicorn*.so*'))
    require(any(digest(p) == obs['oracle']['library_sha256'] for p in libraries), 'oracle binary identity')
    program = S.load_rom()
    resources, _ = common.resource_audit(ROOT, program)
    fixed = (ctypes.c_ubyte * 0x100000).from_buffer_copy(program[:0x100000])
    compiler = Path(shutil.which('clang++')).resolve()
    inputs = set(ROOT.glob('engine/src/*.cpp')) | set((ROOT / 'engine/src').rglob('*.h')) | set((ROOT / 'engine/include').rglob('*.h'))
    inputs |= {ROOT / obs['tool']} | set(OBS.rglob('*'))
    inputs |= {ROOT / name for name, sha in obs['inputs'].items() if isinstance(sha, str)}
    inputs = {p for p in inputs if p.is_file()}
    inputs |= set(resources) | {ROOT / 'extracted/program/maincpu.decrypted.be.bin', ROOT / 'extracted/program/manifest.json', compiler, Path(sys.executable).resolve()}
    # Pin the loaded oracle binary and Python modules too.
    for module in tuple(sys.modules.values()):
        p = getattr(module, '__file__', None)
        if p and Path(p).is_file():
            inputs.add(Path(p).resolve())
    inputs |= set(Path(unicorn.__file__).parent.rglob('*.dylib')) | set(Path(unicorn.__file__).parent.rglob('*.so'))
    before = {str(p): digest(p) for p in sorted(inputs)}
    exe = BUILD / 'frame_head_acceptance'
    command = [str(compiler), '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(ROOT / 'engine/include')]
    command += [str(ROOT / 'engine/src' / name) for name in common.SOURCES]
    command += [str(ROOT / 'engine/tools/frame_head_acceptance.cpp'), '-o', str(exe)]
    harness = ROOT / 'engine/tools/frame_head_acceptance.cpp'
    before[str(harness)] = digest(harness)
    with (OUT / 'build.stderr').open('wb') as build_log:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=build_log)
    before[str(exe)] = digest(exe)
    count, starts, stops, waits, families = (collections.Counter() for _ in range(5))
    rows = []
    negative_tests = None
    wait_negative = False
    error_log = (OUT / 'harness.stderr').open('wb')
    proc = subprocess.Popen([str(exe)] + list(map(str, resources)), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_log)
    try:
        jobs = []
        if args.mode in ('all', 'natural', 'derived'):
            files = sorted((OBS / 'seeds').glob('seed_*.json.gz'))
            if args.max_seeds:
                files = files[:args.max_seeds]
            jobs += [('natural', p) for p in files]
        if args.mode in ('all', 'variants'):
            for family in sorted((OBS / 'variants').iterdir()):
                files = sorted(family.glob('seed_*.json.gz'))
                if args.max_seeds:
                    files = files[:args.max_seeds]
                jobs += [(family.name, p) for p in files]
        if args.mode in ('all', 'derived'):
            jobs.append(('fixture-forward', OBS / 'fixtures/path-sprite-forward/seed_0000.json.gz'))
        for family, path in jobs:
            d = json.load(gzip.open(path))
            if d['kind'] != 'natural':
                count['non-natural-seed-excluded'] += 1
                continue
            frames = {f['frame']: f for f in d['frames']}
            for dump in d['dumps']:
                if dump['kind'] != 'pass-end':
                    continue
                frame = dump['frame'] + 1
                if frame not in frames or frames[frame].get('h') is None:
                    count['no-next-H'] += 1
                    continue
                if family == 'fixture-forward' and frame not in (6, 7):
                    continue
                h = frames[frame]['h']
                ram = (OBS / 'blobs' / (dump['ram'] + '.bin')).read_bytes()
                require(len(ram) == 65536 and hashlib.sha256(ram).hexdigest() == dump['ram'], 'RAM blob identity')
                require(S.state_blob_digest(ram, dump['regs'], dump['pc'], tuple(dump['bank'])) == h['start'], ('start digest', family, d['case'], frame))
                require(dump['pc'] in (0xe4a, 0xe74) and dump['regs']['a6'] == 0x100820 and dump['regs']['a7'] == 0x1feffc, 'D1 H entry')
                require(int.from_bytes(ram[0xeffc:0xf000], 'big') == 0x2ac2, 'original dispatcher stack')
                changed = bytearray(ram)
                for a, n, old, value, mode in h['host_writes']:
                    at = a & 65535
                    require(int.from_bytes(changed[at:at+n], 'big') == old, 'host before value')
                    changed[at:at+n] = value.to_bytes(n, 'big')
                state = dict(ram=bytes(changed), regs=dump['regs'], pc=dump['pc'], bank=tuple(dump['bank']))
                queue = [tuple(e) for e in h['ext']]
                # Reproduce immutable historical whole H; derived natural state is
                # separately declared and does not assert a historical end digest.
                expected = native(program, fixed, state, queue, h['ctrl_cb'])
                require(S.state_blob_digest(expected['ram'], expected['regs'], expected['pc'], expected['bank']) == h['end'], 'archived H end')
                encoded_ports = [(1 if 0x2fe000 <= a < 0x300000 else 2, a, n, v) for a, n, v in expected['ports']]
                require(S.ports_digest(encoded_ports) == h['ports_sha'], 'archived ordered ports')
                require([w[0] for w in expected['waits']] == [w['pc'] for w in h['waits']] and not expected['remaining'], 'archived waits/queue')
                require([[w[1], w[2], w[4]] for w in expected['waits']] ==
                        [w['released'][0] for w in h['waits']], 'archived wait releases')
                count['archived-H-reproduced'] += 1
                scenarios = []
                if family != 'fixture-forward' and args.mode != 'derived':
                    require(h['ctrl_cb'] == 0xc52a, 'unexpected natural boundary')
                    scenarios.append((family, state, queue, 0xc52a, expected))
                if args.mode in ('all', 'derived') and family in ('natural', 'fixture-forward'):
                    altered = bytearray(state['ram'])
                    altered[0x8d3c] |= 128
                    derived = dict(state, ram=bytes(altered))
                    result = native(program, fixed, derived, [], 0x31d6, defaults=True)
                    scenarios.append(('derived-' + family, derived, result['consumed'], 0x31d6, result))
                for label, incoming, reads, stop, result in scenarios:
                    try:
                        compare(parse(invoke(proc, request(incoming, reads, stop))), result, reads)
                    except RuntimeError as e:
                        raise RuntimeError((label, d['case'], frame, str(e))) from e
                    if negative_tests is None:
                        negative_tests = negatives(proc, incoming, reads, stop, result)
                    if result['waits'] and not wait_negative:
                        bad_wait = bytearray(invoke(proc, request(incoming, reads, stop)))
                        bad_wait[-1] ^= 1
                        try:
                            compare(parse(bytes(bad_wait)), result, reads)
                        except RuntimeError:
                            negative_tests.append('wait-release-content')
                            wait_negative = True
                        else:
                            raise RuntimeError('wait release mutation accepted')
                    count['compared'] += 1
                    families[label] += 1
                    starts[hex(incoming['pc'])] += 1
                    stops[hex(stop)] += 1
                    waits.update(hex(w[0]) for w in result['waits'])
                    rows.append(dict(family=label, case=d['case'], frame=frame, start_pc=incoming['pc'], stop_pc=stop, waits=len(result['waits']), reads=len(result['consumed']), ports=len(result['ports'])))
            print(json.dumps(dict(family=family, case=d['case'], compared=count['compared'])), file=sys.stderr, flush=True)
        proc.stdin.close()
        require(proc.wait(timeout=30) == 0, 'harness nonzero exit')
        require(count['compared'] > 0 and negative_tests is not None and wait_negative, 'empty acceptance')
        if args.max_seeds is None and args.mode == 'all':
            require(families['natural'] == 4975, ('natural sample cardinality', families))
            require(sum(v for k, v in families.items() if k not in ('natural', 'derived-natural', 'derived-fixture-forward')) == 976, 'variant sample cardinality')
            require(families['derived-natural'] == 4975 and families['derived-fixture-forward'] == 2, 'derived cardinality')
        for path, sha in before.items():
            require(digest(path) == sha, ('input changed during run', path))
        report = dict(ok=True, full_acceptance=args.max_seeds is None and args.mode == 'all', sample_limit=args.max_seeds,
                      mode=args.mode, native_observation_sha256=OBS_SHA, ROM_sha256=hashlib.sha256(program).hexdigest(),
                      counts=dict(count), families=dict(families), starts=dict(starts), stops=dict(stops), waits=dict(waits),
                      negative_tests=negative_tests, inputs_before_after_equal=before, build_command=command,
                      elapsed_seconds=time.time()-started, rows=rows,
                      limits=['54264 archived H executions do not all have dumps; only retained paired starts are replayed.',
                              'PVC initial page zero except declared ff8/ff9; final observer pair normalized to modeled hardware side effects.',
                              'Carry has no SR oracle; checked valid tag only. Video remains ordered ports, not rendered pixels.',
                              'Controller c52a and derived boundary 31d6 are not executed.'])
        (OUT / 'verification.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
        print(json.dumps({k:report[k] for k in ('ok', 'full_acceptance', 'counts', 'families', 'starts', 'stops', 'waits', 'negative_tests', 'elapsed_seconds')}, sort_keys=True))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        error_log.close()


if __name__ == '__main__':
    main()
