"""D1 frame driver acceptance: C++ run_animation_machine_pass / step_animation_machine_frame versus native Unicorn execution of the original ROM, frame by frame.

Native reference (regenerated in-process, nothing archived is reused): tools/observe_animation_machine_frame_head.py (FH) HeadRun in 'continuous' mode with FH.BASE_CFG and
R.DEFAULT_ANSWER, 400 frames, on the stage_entry_body seeds.  The seed observation is a DECLARED PLATFORM REBASE: S.SEED_DIR / S.SEED_OBS / S.SEED_SHA are replaced in-process
by the Linux-regenerated artifacts/linux_rebase/stage_entry_body/observation.json (no tool file is edited).  Routing text for R.setup = engine/src/animation_machine.cpp at the
FH scope commit (ea30912), checked against FH.ROUTING_SHA.  The historic RNG_OBS baseline assertions of FH.run_main are skipped (artifact not available).

Per seed and frame (FH protocol D1):
  frame 0  native N0 from the prepared seed state         vs C++ run_animation_machine_pass (mode 0);
  frame k  native H_k + declared skip + N_k               vs C++ step_animation_machine_frame (mode 1) from the native H start state, plus two localisation checks:
           mode 2 (harness-only H segment to LONG (1008e4) with the same declared release table) vs the native state at the controller transfer, and
           mode 0 from the native post-skip state vs the native N_k end.
The C++ external-read queue is exactly what native consumed in that frame (H: FH's declared queue log; N: device reads observed natively, page values), and must be fully
consumed.  Compared: RAM 64 KiB, D0-D7/A0-A7, PC, bank base, PVC page (native mapped page with ff8/ff9 normalised as in verify_animation_machine_frame_head.py), ordered
ports per segment (PVC kind 1 raw WORD; C++ MOVE.L 3c0000 events are split into two WORDs only inside native 4fcce/4fcda node port ranges, as the F4 verifier does), ordered
declared waits (segment, pc, address, size, before, released), external reads per segment, stop PCs, carry tag.
Native frames that are not plain D1 completions (a guard / unrouted stop, or a declared bios-card resume, which the D1 driver does not declare) must make the C++ fail with a
checked error and preserved state; they are classified, never counted as matches.
"""
import argparse
import collections
import ctypes
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
OUT = ROOT / 'artifacts/animation_machine_frame_driver'
BUILD = ROOT / 'build/frame_driver_acceptance'
HARNESS = ROOT / 'engine/tools/frame_driver_acceptance.cpp'
SEED_DIR = ROOT / 'artifacts/linux_rebase/stage_entry_body'
SEED_SHA = 'f74048bbeaa83a80e93473038e1867b07b14d0c4693ab5a05d4f73b3beeab04a'
HISTORIC_SEED_SHA = '1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207'
KEYS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')
EXT_SIZE = {0x300000: 1, 0x340000: 1, 0x380000: 1, 0x3c0006: 2}
STATUS_ADDR = 0xd00046
SPLIT_CALLBACKS = (0x4fcce, 0x4fcda)
PVC_LO, PVC_HI = 0x2fe000, 0x300000
MODE_PASS, MODE_STEP, MODE_HEAD = 0, 1, 2
CHAIN_SEEDS = 4
# Historic aggregates, docs/analysis/animation-machine-frame-head-observation.md (natural seeds, base configuration).
HISTORIC = dict(natural_seeds=137, natural_complete_400=136, guard_release_seeds=5, stop_categories={'frame-limit': 136, 'fetch-unmapped': 5, 'odd-pc': 1},
                h_segments=54264, n_passes=54406, h_stop_controller=54264, h_head_cbs={'e4a': 136, 'e74': 54128}, h_ctrl_cbs={'c52a': 54264},
                sprite_flush_waits=8100, sprite_flush_seeds=100, sprite_flush_zero_seeds=36,  # zero: among the 136 seeds completing 400 frames
                sprite_flush_max=85, sprite_flush_85=61, sprite_flush_81=25,
                vblank_waits=0, card_seeds=130, card_per_seed=1,
                ext_pattern={'3c0006/2 3c0006/2 380000/1 300000/1 340000/1 300000/1 340000/1': 54264},
                port_kinds={'300001/1': 3047696, '3c0000/4': 3845876, '3c0004/2': 54264, 'pvc/2ffff0': 218452, 'pvc/2ffff2': 218452},
                leaders_natural=577, case141=dict(frame=0, reason='odd-pc', pc=0x47c05))


# ----------------------------------------------------------------------------------
# Pure helpers (ROM-free, unit tested)
# ----------------------------------------------------------------------------------
def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def normalise_page(page, ff8, ff9):
    """Native mapped PVC page with the raw last CPU writes at 1ff0..1ff3 replaced by the modelled ff8/ff9 (verify_animation_machine_frame_head.py convention)."""
    p = bytearray(page)
    p[0x1ff0:0x1ff4] = struct.pack('>HH', ff8 & 0xffff, ff9 & 0xffff)
    return bytes(p)


def encode_request(mode, ram, regs, pc, bank_base, pvc, queue, external_status=0, carry=0):
    assert len(ram) == 65536 and len(pvc) == 8192
    values = [mode] + [regs[k] & 0xffffffff for k in KEYS] + [pc, carry, bank_base, external_status, len(queue)]
    return struct.pack('>22I', *values) + bytes(ram) + bytes(pvc) + b''.join(struct.pack('>III', *e) for e in queue)


def parse_response(payload):
    """Harness packet -> dict.  ok=False carries preserved and error.  Raises ValueError on a malformed packet."""
    if len(payload) < 8:
        raise ValueError('short harness packet')
    ok = struct.unpack_from('>I', payload)[0]
    if ok == 0:
        return dict(ok=False, preserved=struct.unpack_from('>I', payload, 4)[0] == 1, error=payload[8:].decode('latin-1'))
    if ok != 1 or len(payload) < 4 * 29 + 65536 + 8192:
        raise ValueError('invalid harness packet')
    v = struct.unpack_from('>29I', payload)
    pc, carry, bank, head_pc, ctrl_pc, stop_pc, hreads, nreads, nh, nn, nw, nr = v[1:13]
    regs = dict(zip(KEYS, v[13:29]))
    at = 4 * 29
    if len(payload) != at + 65536 + 8192 + 12 * (nh + nn + nr) + 24 * nw:
        raise ValueError('invalid harness packet length')
    ram = payload[at:at + 65536]
    at += 65536
    pvc = payload[at:at + 8192]
    at += 8192

    def triples(n):
        nonlocal at
        out = [struct.unpack_from('>III', payload, at + 12 * i) for i in range(n)]
        at += 12 * n
        return out
    head_ports = triples(nh)
    node_ports = triples(nn)
    waits = [struct.unpack_from('>6I', payload, at + 24 * i) for i in range(nw)]
    at += 24 * nw
    remaining = triples(nr)
    return dict(ok=True, pc=pc, carry=carry, bank_base=bank, head_pc=head_pc, controller_pc=ctrl_pc, pass_stop_pc=stop_pc, head_reads=hreads, node_reads=nreads,
                regs=regs, ram=ram, pvc=pvc, head_ports=head_ports, node_ports=node_ports, waits=waits, remaining=remaining)


def cpp_ports_native_form(cpp_ports, native_ports, split_ranges=()):
    """C++ (address, size, value) -> Unicorn tuples (kind, address, size, value).  PVC page writes are kind 1 WORD (value & ffff); a C++ MOVE.L 3c0000 event becomes two
    WORD events (3c0000 hi, 3c0002 lo) only when the aligned native position lies inside a 4fcce/4fcda node port range and native shows the WORD pair there."""
    out = []
    splits = 0
    for a, n, v in cpp_ports:
        j = len(out)
        if PVC_LO <= a < PVC_HI:
            out.append((1, a, n, v & 0xffff) if n == 2 else (1, a, n, v))
            continue
        if a == 0x3c0000 and n == 4 and any(lo <= j < hi for lo, hi in split_ranges) and \
                tuple(native_ports[j:j + 2]) == ((2, 0x3c0000, 2, v >> 16), (2, 0x3c0002, 2, v & 0xffff)):
            out.append((2, 0x3c0000, 2, v >> 16))
            out.append((2, 0x3c0002, 2, v & 0xffff))
            splits += 1
            continue
        out.append((2, a, n, v))
    return out, splits


def native_wait_tuples(waits, segment):
    """FH / S wait records -> (segment, pc, address, size, before, released); a bios-card record (no D1 equivalent) -> ('card', ...)."""
    out = []
    for w in waits:
        if w['kind'] == 'bios-card':
            out.append(('card', w['pc'], w.get('a7_at_stop'), w.get('saved_a6')))
            continue
        if not w['released']:
            out.append(('unreleased', w['pc']))
            continue
        a, n, v = w['released'][0]
        out.append((segment, w['pc'], a & 0xffffff, n, w['live'], v))
    return out


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b)) if len(a) != len(b) else None


def compare(got, exp):
    """Ordered list of mismatching fields (empty = equal).  exp: native expectation dict (see Native.expect)."""
    bad = []
    if not got['ok']:
        return [dict(field='cpp-error', error=got['error'], preserved=got['preserved'])]
    for k in ('pc', 'bank_base', 'head_pc', 'controller_pc', 'pass_stop_pc', 'head_reads', 'node_reads'):
        if got[k] != exp[k]:
            bad.append(dict(field=k, cpp=got[k], native=exp[k]))
    if got['carry'] != 0:
        bad.append(dict(field='carry', cpp=got['carry'], native='Unknown(0)'))
    for k in KEYS:
        if got['regs'][k] != exp['regs'][k]:
            bad.append(dict(field='reg-' + k, cpp=got['regs'][k], native=exp['regs'][k]))
    if got['ram'] != exp['ram']:
        i = first_diff(got['ram'], exp['ram'])
        bad.append(dict(field='ram', first=0x100000 + i, cpp=got['ram'][i], native=exp['ram'][i],
                        count=sum(1 for x, y in zip(got['ram'], exp['ram']) if x != y)))
    if got['pvc'] != exp['pvc']:
        i = first_diff(got['pvc'], exp['pvc'])
        bad.append(dict(field='pvc', first=PVC_LO + i))
    for seg in ('head_ports', 'node_ports'):
        conv, _ = cpp_ports_native_form(got[seg], exp[seg], exp.get(seg + '_split', ()))
        if conv != exp[seg]:
            i = first_diff(conv, exp[seg])
            bad.append(dict(field=seg, index=i, cpp=conv[i] if i is not None and i < len(conv) else None,
                            native=exp[seg][i] if i is not None and i < len(exp[seg]) else None, cpp_len=len(conv), native_len=len(exp[seg])))
    waits = [tuple(w) for w in got['waits']]
    if waits != exp['waits']:
        i = first_diff(waits, exp['waits'])
        bad.append(dict(field='waits', index=i, cpp=waits[i] if i is not None and i < len(waits) else None,
                        native=exp['waits'][i] if i is not None and i < len(exp['waits']) else None))
    if got['remaining']:
        bad.append(dict(field='queue-not-consumed', left=len(got['remaining'])))
    return bad


def state_digest(ram, regs, pc, bank_base, pvc):
    h = hashlib.sha256(b'MS5-D1-FRAME-STATE-1')
    h.update(bytes(ram))
    h.update(struct.pack('>16I', *[regs[k] & 0xffffffff for k in KEYS]))
    h.update(struct.pack('>II', pc, bank_base))
    h.update(bytes(pvc))
    return h.hexdigest()


# ----------------------------------------------------------------------------------
# Harness process
# ----------------------------------------------------------------------------------
class Harness(object):
    def __init__(self, exe, resources, stderr_path):
        self.err = open(stderr_path, 'ab')
        self.proc = subprocess.Popen([str(exe)] + [str(p) for p in resources], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err)
        self.calls = 0

    def call(self, payload):
        self.proc.stdin.write(struct.pack('>I', len(payload)) + payload)
        self.proc.stdin.flush()
        head = self.proc.stdout.read(4)
        if len(head) != 4:
            raise RuntimeError('harness died (exit %r)' % self.proc.poll())
        n = struct.unpack('>I', head)[0]
        data = self.proc.stdout.read(n)
        if len(data) != n:
            raise RuntimeError('truncated harness response')
        self.calls += 1
        return parse_response(data)

    def close(self):
        try:
            self.proc.stdin.close()
            rc = self.proc.wait(timeout=60)
        finally:
            self.err.close()
        return rc


# ----------------------------------------------------------------------------------
# Native side (imported observers, in-process; nothing edited)
# ----------------------------------------------------------------------------------
FH = R = S = None
CTX = {}


def import_observers():
    global FH, R, S
    import observe_animation_machine_frame_head as fh
    import observe_animation_machine_scheduler_rng as r
    import observe_animation_machine_scheduler as s
    FH, R, S = fh, r, s


def declared_rebase():
    """Declared platform rebase of the seed observation (recorded in the report)."""
    S.SEED_DIR = SEED_DIR
    S.SEED_OBS = SEED_DIR / 'observation.json'
    actual = file_sha(S.SEED_OBS)
    S.SEED_SHA = actual
    return dict(seed_dir=str(SEED_DIR.relative_to(ROOT)), observation_sha256=actual, expected_sha256=SEED_SHA, matches_expected=actual == SEED_SHA,
                historic_pin=HISTORIC_SEED_SHA, why='Linux-regenerated stage_entry_body observation (tools/observe_stage_entry_body.py at d94a832); the historic pin differs; '
                'S.SEED_DIR/SEED_OBS/SEED_SHA monkeypatched in-process; equality of seed RAM to the historic run is NOT verified byte-wise (artifact absent)')


def setup_native():
    import_observers()
    rebase = declared_rebase()
    text, routing_info = FH.routing_from_git(FH.SCOPE_SHA)
    assert routing_info['sha256'] == FH.ROUTING_SHA, 'routing text at scope commit changed'
    R.setup(text)
    S.load_seeds()
    pins = dict(scheduler_tool_equal=file_sha(TOOLS / 'observe_animation_machine_scheduler.py') == FH.SCHED_TOOL_SHA,
                rng_tool_prefix_equal=file_sha(TOOLS / 'observe_animation_machine_scheduler_rng.py').startswith(FH.RNG_TOOL_SHA),
                pvc_tool_prefix_equal=file_sha(TOOLS / 'observe_animation_machine_pvc_banks.py').startswith(FH.PVC_TOOL_SHA),
                scope_doc_equal=FH.scope_from_git(FH.SCOPE_SHA) == FH.SCOPE_DOC_SHA,
                rng_obs_baseline='skipped: %s not available on this machine' % FH.RNG_OBS.relative_to(ROOT))
    return rebase, routing_info, pins


def make_verify_class():
    class VerifyRun(FH.HeadRun):
        """FH.HeadRun with per-frame capture; every finished frame is handed to on_frame.  Execution itself is FH's (no protocol change)."""
        def build(self, snap):
            mach = FH.HeadRun.build(self, snap)
            mach.cpu.hook_add(FH.UC_HOOK_MEM_READ, self.h_devlog, begin=0x300000, end=0x3fffff)
            mach.cpu.hook_add(FH.UC_HOOK_MEM_READ, self.h_devlog, begin=0xd00000, end=0xd00fff)
            return mach

        def h_devlog(self, uc, access, address, size, value, user):
            if self.phase == 'H' and address != STATUS_ADDR:
                return                                         # H EXT reads are FH's declared queue log (ext_log)
            val = int.from_bytes(bytes(uc.mem_read(address, size)), 'big')
            self.devlog.append((self.phase, address, size, val))

        def capture(self):
            m = self.m
            st = m.state()
            st['pc'] = m.pc()
            st['pvc'] = normalise_page(bytes(m.cpu.mem_read(PVC_LO, 8192)), m.ff8, m.ff9)
            st['status'] = int.from_bytes(bytes(m.cpu.mem_read(STATUS_ADDR, 1)), 'big')
            return st

        def run_head(self, frame):
            self.devlog = []
            start = self.capture()
            out = FH.HeadRun.run_head(self, frame)
            reason, rec, hend, hports, hext, hpre = out
            end = self.capture()
            self.fr = dict(frame=frame, start=start, h=dict(reason=reason, rec=rec, end=end, ports=list(hports), ext=[tuple(e) for e in hext],
                                                           status_reads=[d for d in self.devlog if d[0] == 'H']))
            if reason['reason'] != 'controller':
                self.fr['n'] = None
                self.on_frame(self.fr)
            return out

        def run_pass(self):
            if self.frame == 0:
                self.fr = dict(frame=0, start=self.capture(), h=None)
            nstart = self.capture()
            self.devlog = []
            out = FH.HeadRun.run_pass(self)
            reason, walk, start_digest, waits, ports0 = out
            ports = list(self.m.ports[ports0:])
            split = [(n['ports0'] - ports0, n['ports0'] - ports0 + n['rec']['ports']) for n in self.pass_nodes if 'rec' in n and n['cb'] in SPLIT_CALLBACKS]
            if self.cur is not None and self.cur['cb'] in SPLIT_CALLBACKS:
                split.append((self.cur['ports0'] - ports0, len(ports)))
            self.fr['n'] = dict(reason=reason, start=nstart, end=self.capture(), ports=ports, split=split, waits=waits, dev=[d for d in self.devlog if d[0] == 'N'],
                                cbs=[n['cb'] for n in self.pass_nodes])
            self.on_frame(self.fr)
            return out
    return VerifyRun


# ----------------------------------------------------------------------------------
# Expectations from one native frame
# ----------------------------------------------------------------------------------
def n_queue(dev):
    queue, status_reads, other = [], 0, []
    for _, a, n, v in dev:
        if a in EXT_SIZE and EXT_SIZE[a] == n:
            queue.append((a, n, v))
        elif a == STATUS_ADDR and n == 1:
            status_reads += 1
        else:
            other.append((a, n, v))
    return queue, status_reads, other


def frame_expectation(fr):
    """-> (category, inputs, expectations).  category 'complete' (a D1 completion to compare), or a non-completion class."""
    n = fr['n']
    h = fr['h']
    if h is not None and h['reason']['reason'] != 'controller':
        return 'native-H-stop:' + h['reason']['reason'], None
    nreason = n['reason']['reason']
    hwaits = native_wait_tuples(h['rec']['waits'], 0) if h else []
    nwaits = native_wait_tuples(n['waits'], 1)
    nq, n_status, n_other = n_queue(n['dev'])
    hq = list(h['ext']) if h else []
    h_status = len(h['status_reads']) if h else 0
    end = n['end']
    exp_n = dict(ram=end['ram'], regs=end['regs'], pc=end['pc'], bank_base=end['bank'][0], pvc=end['pvc'], head_pc=0, controller_pc=0,
                 pass_stop_pc=end['pc'] if nreason == 'frame-head' else None, head_reads=0, node_reads=len(nq) + n_status,
                 head_ports=[], node_ports=[tuple(p) for p in n['ports']], node_ports_split=n['split'], waits=nwaits)
    status_values = set(d[3] for d in n['dev'] if d[1] == STATUS_ADDR) | set(d[3] for d in (h['status_reads'] if h else []))
    info = dict(n_queue=nq, h_queue=hq, n_other_reads=n_other, status_values=sorted(status_values))
    cards = [w for w in hwaits + nwaits if w[0] == 'card']
    unreleased = [w for w in hwaits + nwaits if w[0] == 'unreleased']
    if nreason != 'frame-head':
        cat = 'native-N-stop:' + nreason
    elif unreleased:
        cat = 'native-wait-not-released'
    elif cards:
        cat = 'native-bios-card'
    elif n_other:
        cat = 'native-undeclared-N-device-read'
    else:
        cat = 'complete'
    out = dict(exp_n=exp_n, info=info)
    if h is not None:
        hend = h['end']
        out['exp_h'] = dict(ram=hend['ram'], regs=hend['regs'], pc=hend['pc'], bank_base=hend['bank'][0], pvc=hend['pvc'], head_pc=fr['start']['pc'],
                            controller_pc=hend['pc'], pass_stop_pc=0, head_reads=len(hq) + h_status, node_reads=0, head_ports=[tuple(p) for p in h['ports']],
                            node_ports=[], waits=hwaits)
        out['h_has_card'] = any(w[0] == 'card' for w in hwaits)
        out['exp_step'] = dict(exp_n, head_pc=fr['start']['pc'], controller_pc=hend['pc'], head_reads=len(hq) + h_status, head_ports=[tuple(p) for p in h['ports']],
                               waits=hwaits + nwaits)
    return cat, out


def e_counts(ex):
    e = ex.get('exp_step', ex['exp_n'])
    return dict(h_queue=len(ex['info']['h_queue']), n_queue=len(ex['info']['n_queue']), exp=e)


def frame_counts(got, ec):
    """Small per-frame tallies of what was compared (for the totals)."""
    e = ec['exp']
    c = collections.Counter(head_ports=len(e['head_ports']), node_ports=len(e['node_ports']), h_queue=ec['h_queue'], n_queue=ec['n_queue'],
                            head_reads=e['head_reads'], node_reads=e['node_reads'])
    if got['ok']:
        c['moveL_split'] = cpp_ports_native_form(got['node_ports'], e['node_ports'], e.get('node_ports_split', ()))[1]
    for w in e['waits']:
        c['wait_%s_%x' % ('H' if w[0] == 0 else 'N', w[1])] += 1
    return dict(c)


def request_for(mode, st, queue):
    return encode_request(mode, st['ram'], st['regs'], st['pc'], st['bank'][0], st['pvc'], queue, st['status'])


def check_expected_failure(got, label):
    if got['ok']:
        return dict(check=label, ok=False, why='C++ completed where native did not complete a D1 frame')
    return dict(check=label, ok=bool(got['preserved']), error=got['error'], preserved=got['preserved'])


def compare_frame(harness, fr):
    """Run the C++ checks of one native frame; -> row."""
    cat, ex = frame_expectation(fr)
    frame = fr['frame']
    row = dict(frame=frame, category=cat, checks={})
    if ex is None:                                             # native H stopped (guard): step must fail and preserve
        got = harness.call(request_for(MODE_STEP, fr['start'], list(fr['h']['ext'])))
        row['checks']['step'] = check_expected_failure(got, 'step')
        row['native_stop'] = fr['h']['reason']
        row['match'] = False
        return row, None
    info = ex['info']
    if info['status_values'] and any(v != fr['start']['status'] for v in info['status_values']):
        row['status_varies'] = info['status_values']
    if frame == 0:
        got = harness.call(request_for(MODE_PASS, fr['start'], info['n_queue']))
        if cat == 'complete':
            bad = compare(got, ex['exp_n'])
            row['checks']['pass'] = dict(ok=not bad, mismatch=bad[:4])
            row['match'] = not bad
            row['counts'] = frame_counts(got, e_counts(ex))
            chain = dict(queue=info['n_queue'], digest=state_digest(ex['exp_n']['ram'], ex['exp_n']['regs'], ex['exp_n']['pc'], ex['exp_n']['bank_base'], ex['exp_n']['pvc']))
        else:
            row['checks']['pass'] = check_expected_failure(got, 'pass')
            row['native_stop'] = fr['n']['reason']
            row['match'] = False
            chain = None
        return row, chain
    queue = info['h_queue'] + info['n_queue']
    got = harness.call(request_for(MODE_STEP, fr['start'], queue))
    hgot = harness.call(request_for(MODE_HEAD, fr['start'], info['h_queue']))
    ngot = harness.call(request_for(MODE_PASS, fr['n']['start'], info['n_queue']))
    # H segment: always a native completion here (H stopped at the controller)
    if ex['h_has_card']:
        row['checks']['head'] = check_expected_failure(hgot, 'head')
    else:
        bad = compare(hgot, ex['exp_h'])
        row['checks']['head'] = dict(ok=not bad, mismatch=bad[:4])
    if cat == 'complete':
        bad = compare(got, ex['exp_step'])
        row['checks']['step'] = dict(ok=not bad, mismatch=bad[:4])
        nbad = compare(ngot, ex['exp_n'])
        row['checks']['pass'] = dict(ok=not nbad, mismatch=nbad[:4])
        row['match'] = not bad and not nbad and row['checks']['head']['ok']
        row['counts'] = frame_counts(got, e_counts(ex))
        e = ex['exp_step']
        chain = dict(queue=queue, digest=state_digest(e['ram'], e['regs'], e['pc'], e['bank_base'], e['pvc']))
    else:
        row['checks']['step'] = check_expected_failure(got, 'step')
        row['checks']['pass'] = check_expected_failure(ngot, 'pass')
        row['native_stop'] = fr['n']['reason'] if cat.startswith('native-N-stop') else None
        if cat == 'native-bios-card':
            row['cards'] = [dict(kind=w['kind'], node=w.get('node'), node_a6=w.get('node_a6'), a7=w.get('a7_at_stop')) for w in fr['n']['waits'] if w['kind'] == 'bios-card']
        row['match'] = False
        chain = None
    return row, chain


# ----------------------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------------------
def harness_for_worker():
    h = CTX.get('harness')
    if h is None:
        h = Harness(CTX['exe'], CTX['resources'], OUT / ('harness.%d.stderr' % os.getpid()))
        CTX['harness'] = h
    return h


def run_chain(harness, seed_start, chain_rows):
    """C++-only chain: frame 0 pass from the seed start, then step from the C++ output with the native per-frame queue.  -> list of digests (stops at the first failure)."""
    st = dict(seed_start)
    digests = []
    for i, c in enumerate(chain_rows):
        if c is None:
            break
        got = harness.call(request_for(MODE_PASS if i == 0 else MODE_STEP, st, c['queue']))
        if not got['ok'] or got['remaining']:
            digests.append('error:' + (got.get('error') or 'queue'))
            break
        digests.append(state_digest(got['ram'], got['regs'], got['pc'], got['bank_base'], got['pvc']))
        st = dict(ram=got['ram'], regs=got['regs'], pc=got['pc'], bank=(got['bank_base'],), pvc=got['pvc'], status=st['status'])
    return digests


def work(arg):
    case, frames, chain = arg
    t0 = time.time()
    harness = harness_for_worker()
    calls0 = harness.calls
    Verify = CTX['cls']
    sd, snap, meta, rec, carried = FH.prepared(case)
    cfg = dict(FH.BASE_CFG)
    rows = []
    chain_rows = []
    state0 = {}
    tbset = set()

    def on_frame(fr):
        if fr['frame'] == 0:
            state0.update(fr['start'])
        try:
            row, c = compare_frame(harness, fr)
        except Exception as e:                                  # a verifier failure is recorded, never a match
            row, c = dict(frame=fr['frame'], category='verifier-error', error=repr(e), match=False, checks={}), None
        rows.append(row)
        chain_rows.append(c)
    snapc = {k: v for k, v in carried.items() if k != 'prep_entry_state'}
    run = Verify(R.G['program'], R.G['fixed'], R.G['levels'], snapc, 'continuous', frames, heavy=False, plan=None, sink=None, extend=False,
                 answer=R.DEFAULT_ANSWER, full_dump=False, prep_dump=None, cfg=cfg, case=case, tbset=tbset, keep_all=False, do_model=False)
    run.on_frame = on_frame
    run.run()
    summ = FH.summarize(run, cfg)
    out = dict(case=case, kind=sd['kind'], family=sd['family'], stop=run.stop, stop_category=FH.stop_category(run.stop), frames_done=run.frames_done,
               native_digest=run.digest.hexdigest(), summary={k: summ[k] for k in ('h_stops', 'h_head_cbs', 'h_ctrl_cbs', 'h_waits', 'waits', 'port_kinds', 'ext_patterns',
                                                                                  'h_ext_left', 'a7_bad', 'head_bad', 'skip_bad', 'frames_complete', 'card')},
               n_passes=sum(1 for p in run.pass_records if p['n'] is not None), h_segments=len(run.h_records), tbset=sorted(tbset), rows=rows)
    if chain:
        d1 = run_chain(harness, state0, chain_rows)
        d2 = run_chain(harness, state0, chain_rows)
        native = [c['digest'] for c in chain_rows if c is not None]
        k = 0
        for x, y in zip(d1, [c['digest'] if c else None for c in chain_rows]):
            if x != y:
                break
            k += 1
        out['chain'] = dict(frames=len(d1), deterministic=d1 == d2, digest=sha(json.dumps(d1).encode()), equal_native_prefix=k, native_complete_frames=len(native),
                            last=d1[-1] if d1 else None)
    out['harness_calls'] = harness.calls - calls0
    out['seconds'] = time.time() - t0
    return out


def worker_init():
    pass


# ----------------------------------------------------------------------------------
# Negative checks (one seed, few frames)
# ----------------------------------------------------------------------------------
def negatives(case):
    harness = harness_for_worker()
    Verify = CTX['cls']
    sd, snap, meta, rec, carried = FH.prepared(case)
    frs = []
    run = Verify(R.G['program'], R.G['fixed'], R.G['levels'], {k: v for k, v in carried.items() if k != 'prep_entry_state'}, 'continuous', 3, heavy=False, plan=None,
                 sink=None, extend=False, answer=R.DEFAULT_ANSWER, full_dump=False, prep_dump=None, cfg=dict(FH.BASE_CFG), case=case, tbset=None, keep_all=False, do_model=False)
    run.on_frame = frs.append
    run.run()
    fr = [f for f in frs if f['frame'] == 2][0]
    cat, ex = frame_expectation(fr)
    assert cat == 'complete', cat
    queue = ex['info']['h_queue'] + ex['info']['n_queue']
    exp = ex['exp_step']
    tests = {}
    base = harness.call(request_for(MODE_STEP, fr['start'], queue))
    tests['baseline-equal'] = not compare(base, exp)

    def detected(st, q, label):
        got = harness.call(request_for(MODE_STEP, st, q))
        bad = compare(got, exp)
        tests[label] = dict(detected=bool(bad), first=bad[0] if bad else None)
    flipped = dict(fr['start'])
    ram = bytearray(flipped['ram'])
    ram[0x0100] ^= 0x01
    flipped['ram'] = bytes(ram)
    detected(flipped, queue, 'ram-byte-flipped')
    detected(fr['start'], queue[:-1], 'queue-short')
    detected(fr['start'], queue + [(0x300000, 1, 0x5a)], 'queue-extra-entry')
    # Value changes (the first raster read alone does not influence the state natively either; both raster reads are changed)
    detected(fr['start'], [(a, n, 0x9234) if a == 0x3c0006 else (a, n, v) for a, n, v in queue], 'queue-raster-values-changed')
    detected(fr['start'], [(a, n, 0x00) if a == 0x300000 else (a, n, v) for a, n, v in queue], 'queue-input-values-changed')
    q3 = list(queue)
    q3[0], q3[2] = q3[2], q3[0]
    detected(fr['start'], q3, 'queue-order-swapped')
    wrong_pc = dict(fr['start'], pc=0xe4a)
    got = harness.call(request_for(MODE_STEP, wrong_pc, queue))
    tests['wrong-head-pc'] = dict(detected=not got['ok'], error=got.get('error'), preserved=got.get('preserved'))
    # comparator mutations of a correct C++ result
    for label, mutate in (('result-ram', lambda g: g.update(ram=bytes([g['ram'][0] ^ 1]) + g['ram'][1:])),
                          ('result-reg', lambda g: g['regs'].update(d3=g['regs']['d3'] ^ 1)),
                          ('result-pc', lambda g: g.update(pc=g['pc'] ^ 2)),
                          ('result-pvc', lambda g: g.update(pvc=g['pvc'][:0x1ff1] + bytes([g['pvc'][0x1ff1] ^ 1]) + g['pvc'][0x1ff2:])),
                          ('result-head-port-value', lambda g: g['head_ports'].__setitem__(0, (g['head_ports'][0][0], g['head_ports'][0][1], g['head_ports'][0][2] ^ 1))),
                          ('result-node-port-dropped', lambda g: g['node_ports'].pop()),
                          ('result-wait-dropped', lambda g: g['waits'].pop() if g['waits'] else g['waits'].append((0, 0, 0, 0, 0, 0))),
                          ('result-reads', lambda g: g.update(head_reads=g['head_reads'] + 1)),
                          ('result-carry', lambda g: g.update(carry=1))):
        g = dict(base, regs=dict(base['regs']), head_ports=list(base['head_ports']), node_ports=list(base['node_ports']), waits=list(base['waits']))
        mutate(g)
        tests[label] = dict(detected=bool(compare(g, exp)))
    broken = subprocess.run([str(CTX['exe'])] + [str(p) for p in CTX['resources']], input=struct.pack('>I', 11) + b'bad request', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tests['malformed-request-nonzero-exit'] = dict(detected=broken.returncode != 0, returncode=broken.returncode)
    try:
        parse_response(b'\0\0\0\x01' + b'\0' * 20)
        tests['malformed-response-rejected'] = dict(detected=False)
    except ValueError:
        tests['malformed-response-rejected'] = dict(detected=True)
    ok = tests['baseline-equal'] and all(v['detected'] for k, v in tests.items() if k != 'baseline-equal')
    return dict(case=case, frame=2, ok=ok, tests=tests)


# ----------------------------------------------------------------------------------
# Build and main
# ----------------------------------------------------------------------------------
def machine_sources():
    line = [l for l in (ROOT / 'Makefile').read_text().splitlines() if l.startswith('ANIMATION_MACHINE_SOURCES =')][0]
    srcs = [ROOT / s for s in line.split('=', 1)[1].split()] + [ROOT / 'engine/src/physical_rom_resource.cpp']
    assert ROOT / 'engine/src/animation_machine_frame.cpp' in srcs
    return srcs


def build(jobs):
    compiler = Path(shutil.which('clang++'))                    # not resolved: the symlink target 'clang' would not link libstdc++
    flags = ['-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(ROOT / 'engine/include')]
    objdir = BUILD / 'obj'
    if objdir.exists():
        shutil.rmtree(objdir)
    objdir.mkdir(parents=True)
    srcs = machine_sources()
    log = open(OUT / 'build.stderr', 'wb')
    procs = []
    objs = []
    for s in srcs:
        o = objdir / (s.stem + '.o')
        objs.append(o)
        while len([p for p in procs if p.poll() is None]) >= jobs:
            time.sleep(0.05)
        procs.append(subprocess.Popen([str(compiler)] + flags + ['-c', str(s), '-o', str(o)], stdout=subprocess.DEVNULL, stderr=log))
    for p in procs:
        assert p.wait() == 0, 'compile failed (see build.stderr)'
    exe = BUILD / 'frame_driver_acceptance'
    subprocess.run([str(compiler)] + flags + [str(o) for o in objs] + [str(HARNESS), '-o', str(exe)], check=True, stdout=subprocess.DEVNULL, stderr=log)
    log.close()
    return exe, compiler, srcs, ['clang++'] + flags + ['-c <each source>', 'link + ' + str(HARNESS.relative_to(ROOT))]


def aggregate(results, historic):
    nat = [r for r in results if r['kind'] == 'natural']
    tot = collections.Counter()
    cats = collections.Counter()
    errs = collections.Counter()
    per_seed = []
    compared = collections.Counter()
    for r in results:
        rows = r['rows']
        first = next((x for x in rows if x['category'] == 'complete' and not x['match']), None)
        nonc = [x for x in rows if x['category'] != 'complete']
        bad_fail = [x for x in nonc if not all(c.get('ok') for c in x['checks'].values())]
        for x in rows:
            cats[x['category']] += 1
            for c in x['checks'].values():
                if 'error' in c and c.get('error'):
                    errs[(x['category'], c['check'], c['error'])] += 1
        comp = [x for x in rows if x['category'] == 'complete']
        seed = dict(case=r['case'], kind=r['kind'], native_stop=r['stop'], frames=len(rows), complete_frames=len(comp), matches=sum(1 for x in comp if x['match']),
                    mismatches=sum(1 for x in comp if not x['match']), non_completions=[dict(frame=x['frame'], category=x['category'], checks=x['checks']) for x in nonc][:5],
                    expected_failure_bad=len(bad_fail), first_mismatch=first, seconds=round(r['seconds'], 1), chain=r.get('chain'))
        per_seed.append(seed)
        if r['kind'] == 'natural':
            tot['natural_frames'] += len(rows)
            tot['natural_complete_frames'] += len(comp)
            tot['natural_matches'] += seed['matches']
            tot['natural_mismatches'] += seed['mismatches']
            tot['natural_non_completions'] += len(nonc)
            tot['natural_expected_failure_not_preserved'] += len(bad_fail)
        tot['frames'] += len(rows)
        tot['matches'] += seed['matches']
        tot['mismatches'] += seed['mismatches']
        tot['non_completions'] += len(nonc)
        tot['status_varies'] += sum(1 for x in rows if 'status_varies' in x)
        for x in rows:
            if x.get('match') and r['kind'] == 'natural':
                for k, v in x.get('counts', {}).items():
                    compared[k] += v
    # historic aggregates
    def merge(key):
        c = collections.Counter()
        for r in nat:
            c.update(r['summary'][key])
        return dict(c)
    sf = [r['summary']['h_waits'].get('sprite-flush', 0) for r in nat]
    cards = [len(r['summary']['card']) for r in nat]
    leaders = None
    try:
        ld = FH.load_leaders()
        tbs = set()
        for r in nat:
            tbs.update(tuple(x) for x in r['tbset'])
        leaders = len(FH.covered_leaders(tbs, ld['leaders'], ld['duff']))
    except Exception as e:
        leaders = 'error: %r' % e
    c141 = [r for r in results if r['case'] == 141]
    now = dict(natural_seeds=len(nat), natural_complete_400=sum(1 for r in nat if r['stop']['reason'] == 'frame-limit' and r['frames_done'] == 400),
               guard_release_seeds=sum(1 for r in results if r['kind'] == 'guard-release'),
               stop_categories=dict(collections.Counter(r['stop']['reason'] for r in results)),
               h_segments=sum(r['h_segments'] for r in nat), n_passes=sum(r['n_passes'] for r in results),
               h_stop_controller=sum(r['summary']['h_stops'].get('controller', 0) for r in nat), h_head_cbs=merge('h_head_cbs'), h_ctrl_cbs=merge('h_ctrl_cbs'),
               sprite_flush_waits=sum(sf), sprite_flush_seeds=sum(1 for x in sf if x), sprite_flush_zero_seeds=sum(1 for r in nat if r['stop']['reason'] == 'frame-limit' and not r['summary']['h_waits'].get('sprite-flush', 0)), sprite_flush_max=max(sf or [0]),
               sprite_flush_85=sum(1 for x in sf if x == 85), sprite_flush_81=sum(1 for x in sf if x == 81),
               vblank_waits=sum(r['summary']['h_waits'].get('vblank', 0) for r in nat), card_seeds=sum(1 for x in cards if x), card_per_seed=sorted(set(x for x in cards if x)),
               ext_pattern=merge('ext_patterns'), port_kinds={k: v for k, v in merge('port_kinds').items() if k in HISTORIC['port_kinds']}, leaders_natural=leaders,
               case141=dict(frame=c141[0]['stop'].get('frame'), reason=c141[0]['stop']['reason'], pc=c141[0]['stop'].get('pc')) if c141 else None)
    now['card_per_seed'] = now['card_per_seed'][0] if len(now['card_per_seed']) == 1 else now['card_per_seed']
    cmp_rows = {k: dict(historic=historic[k], regenerated=now.get(k), equal=historic[k] == now.get(k)) for k in historic}
    return dict(totals=dict(tot), natural_matched_frame_tallies=dict(compared), categories=dict(cats), cpp_errors_on_non_completions={'%s|%s|%s' % k: v for k, v in errs.items()}, per_seed=per_seed,
                historic_comparison=cmp_rows, historic_all_equal=all(v['equal'] for v in cmp_rows.values()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', help='comma list (default: all 142 seeds)')
    ap.add_argument('--frames', type=int, default=400)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--no-build', action='store_true')
    args = ap.parse_args(argv)
    assert not sys.flags.optimize
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob('harness.*.stderr'):
        p.unlink()
    report_path = OUT / 'verification.json'
    if report_path.exists():
        report_path.unlink()
    rebase, routing_info, pins = setup_native()
    import verify_animation_machine as common
    program = R.G['program']
    rom_sha = sha(program)
    assert rom_sha == S.ROM_SHA
    resources, resource_refs = common.resource_audit(ROOT, program)
    if args.no_build and (BUILD / 'frame_driver_acceptance').exists():
        exe = BUILD / 'frame_driver_acceptance'
        compiler = Path(shutil.which('clang++'))
        srcs = machine_sources()
        build_cmd = 'reused existing build (--no-build)'
    else:
        exe, compiler, srcs, build_cmd = build(args.workers)
    CTX.update(exe=exe, resources=resources, cls=make_verify_class())
    import unicorn
    libs = sorted(set(Path(unicorn.__file__).parent.rglob('libunicorn*.so*')) | set(Path(unicorn.__file__).parent.rglob('libunicorn*.dylib')))
    headers = sorted(set((ROOT / 'engine/include').rglob('*.h')) | set((ROOT / 'engine/src').rglob('*.h')))
    tool_files = [TOOLS / n for n in ('verify_animation_machine_frame_driver.py', 'observe_animation_machine_frame_head.py', 'observe_animation_machine_scheduler_rng.py',
                                      'observe_animation_machine_scheduler.py', 'observe_animation_machine_pvc_banks.py', 'address_map.py', 'disassemble_program.py',
                                      'verify_animation_machine.py')]
    inputs = dict(rom=dict(path='extracted/program/maincpu.decrypted.be.bin', sha256=rom_sha),
                  seed_observation=dict(path=str(S.SEED_OBS.relative_to(ROOT)), sha256=file_sha(S.SEED_OBS)),
                  program_rom_resources=resource_refs,
                  engine_sources={str(p.relative_to(ROOT)): file_sha(p) for p in srcs}, engine_headers={str(p.relative_to(ROOT)): file_sha(p) for p in headers},
                  harness={str(HARNESS.relative_to(ROOT)): file_sha(HARNESS)}, harness_binary_sha256=file_sha(exe),
                  tools={str(p.relative_to(ROOT)): file_sha(p) for p in tool_files if p.exists()},
                  leaders_file={str(FH.LEADERS_FILE.relative_to(ROOT)): file_sha(FH.LEADERS_FILE)},
                  unicorn=dict(version=unicorn.__version__, libraries={str(p): file_sha(p) for p in libs}), compiler=dict(path=str(compiler), resolved=str(compiler.resolve()), sha256=file_sha(compiler.resolve())),
                  compiler_version=subprocess.run([str(compiler), '--version'], stdout=subprocess.PIPE, text=True).stdout.splitlines()[0],
                  python=sys.version.split()[0], routing=routing_info)
    cases = sorted(S.SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    naturals = [c for c in cases if S.SEEDS[c]['kind'] == 'natural']
    chain_cases = set(naturals[:CHAIN_SEEDS])
    ctx = multiprocessing.get_context('fork')
    results = []
    with ctx.Pool(args.workers) as pool:
        neg_async = pool.apply_async(negatives, (naturals[0],)) if naturals and args.frames >= 3 else None
        jobs = [(c, args.frames, c in chain_cases) for c in cases]
        for r in pool.imap_unordered(work, jobs, chunksize=1):
            results.append(r)
            nonmatch = sum(1 for x in r['rows'] if x['category'] == 'complete' and not x['match'])
            print('[%6.0fs] case %3d %-13s frames %3d complete-mismatch %d stop %s' % (time.time() - t0, r['case'], r['kind'], len(r['rows']), nonmatch, r['stop']['reason']),
                  file=sys.stderr, flush=True)
        neg = neg_async.get() if neg_async else None
    results.sort(key=lambda r: r['case'])
    agg = aggregate(results, HISTORIC)
    chains = [r['chain'] for r in results if r.get('chain')]
    determinism = dict(seeds=sorted(chain_cases), all_deterministic=all(c['deterministic'] for c in chains), chains=chains)
    full = args.cases is None and args.frames == 400
    after = dict(rom=file_sha(ROOT / 'extracted/program/maincpu.decrypted.be.bin'), seed_observation=file_sha(S.SEED_OBS), harness=file_sha(HARNESS))
    report = dict(tool='tools/verify_animation_machine_frame_driver.py', full_run=full, cases=len(cases), frames_limit=args.frames, declared_platform_rebase=rebase,
                  observer_pins=pins, inputs=inputs, inputs_unchanged_after=after == dict(rom=rom_sha, seed_observation=inputs['seed_observation']['sha256'],
                                                                                        harness=list(inputs['harness'].values())[0]),
                  build=build_cmd, negative_checks=neg, determinism=determinism, elapsed_seconds=round(time.time() - t0, 1), **agg,
                  protocol=__doc__.strip().splitlines(),
                  limits=['Native reference is FH HeadRun regenerated on Linux (unicorn %s); the historic macOS observation is not byte-compared (artifact absent).' % unicorn.__version__,
                          'Seed observation is the declared Linux rebase; historic seed RAM equality is not verified byte-wise.',
                          'Mode 2 (H only) restates the declared release table in the harness; it localises, it does not test the driver.',
                          'Carry has no SR oracle; only the Unknown tag is checked.  Video is ordered ports, not pixels.',
                          'Controller c52a is not executed (declared skip).'])
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n')
    keys = ('full_run', 'totals', 'categories', 'historic_all_equal', 'elapsed_seconds')
    print(json.dumps({k: report[k] for k in keys}, indent=1, sort_keys=True, default=str))
    print(json.dumps(dict(negative_ok=neg['ok'] if neg else None, deterministic=determinism['all_deterministic'], report_sha256=file_sha(report_path)), sort_keys=True))


if __name__ == '__main__':
    main()
