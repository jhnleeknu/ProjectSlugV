"""Unit IO (IO-2): C++ frame comparison and frontier report against the native input / stage-progress observation (tools/observe_animation_machine_io.py).

Inputs (read-only, pinned): the observation directory (default artifacts/animation_machine_io_native; observation.json file SHA256 and compared_sha256 are pinned,
every run record and state pack is checked against the SHA256 in observation.json).
Known observations (player C9, docs/analysis/animation-machine-player-c9-contract.md): the table KNOWN_OBSERVATIONS replaces the former single pin.
  historic  artifacts/animation_machine_io_native (the default; behaviour and verification.json / frontier.json unchanged, negative checks on P1 case 0).
  io-ext    artifacts/animation_machine_io_ext (tools/observe_animation_machine_io_ext.py, extended input).  It has no P1 case 0 run: the negative checks
            run on its P1 case 94 control run (required, like P1 case 0 for historic); verification.json records inputs.observation.pin / .negatives.
  io-ext2   the third observation (tools/observe_animation_machine_io_ext2.py: other stage groups, two players, continue); negatives on P1 case 94 as io-ext.
Nothing is executed natively here: the native side is the recorded observation
(frame-start states of every frame, the native external-read consumption log `q`, the declared host writes, per-segment digests / port digests / IRQ records / waits).

For every run (configuration x seed) and every frame:
  frame-wise   C++ from the NATIVE frame-start state (declared host writes already applied) with the native consumption log as the declared external-read queue:
               frame 0 run_animation_machine_pass, frame k step_animation_machine_frame (controller Execute + irq_execution + palette RAM, one packet,
               engine/tools/frame_io_acceptance.cpp).  Compared with the recorded native frame: the end-state digest (RAM 64 KiB, D0-D7/A0-A7, PC, bank base, ff8/ff9,
               PVC page, both palette banks and the selection, status byte), the ordered head / controller / node ports (count and SHA256), the ordered IRQ records and IRQ
               ports (count, SHA256 per IRQ), the card waits, the external-read counts (the queue must be consumed completely), head / controller / pass-stop PCs,
               carry Unknown.  A mismatch reports the first differing field and, when the next recorded state allows it, the first differing byte.
  chain        pure C++ chain: frame k starts from the C++ OUTPUT of frame k-1 plus the declared host writes of frame k (never from a native state); the queue is the native
               consumption log.  The start digest of every chained frame is compared with the native start digest; equal -> the frame-wise result is the chained result
               (verified by real chain calls on the chain-verified set), different -> a real chain call and a recorded divergence.  The chain runs to the first C++
               failure; a failure on a frame where native stopped (guard) must be the declared checked error with preserved state.
  frontier     the first C++ failure on a natively completed frame ('unsupported animation machine PC'): candidate PCs from the native record (first unrouted TB PC, then the
               unrouted PCs first seen in that frame); a candidate P is confirmed like check_fail_pc (review 0264 L-1): P is not routed by the dispatch chain
               (verify_animation_machine_unit_fixtures.pc_routed), is even, and the same frame run segment by segment with stop = P succeeds and ends exactly at P.
frontier.json groups the confirmed frontier PCs and all native unrouted PCs of the frontier runs by static function root, area (C player / D enemy-boss-stage /
E boot-title-demo, address rule of the scope document 6.3) and candidate unit, with static closure sizes (an5 rules of the IO-1 probe).
Everything in verification.json / frontier.json is deterministic (no times, no paths of the machine); timing and platform data go to run_info.json.
"""
import argparse
import bisect
import collections
import gzip
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
import observe_animation_machine_io as O  # noqa: E402  (imported for read_pack / state_digest / canon only, never edited; file SHA256 pinned through observation.json)

NATIVE_DIR_DEFAULT = ROOT / 'artifacts/animation_machine_io_native'
OUT_DEFAULT = ROOT / 'build/animation_machine_io_execution'        # never the shared artifacts/ tree
EXE = ROOT / 'build/frame_io_acceptance'
HARNESS = ROOT / 'engine/tools/frame_io_acceptance.cpp'
ROM_PATH = ROOT / 'extracted/program/maincpu.decrypted.be.bin'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
# Known-observation pin table (player C9 contract, area-C plan 10.6 / main decision 10.x): --observation must match one entry exactly (observation.json file
# SHA256 prefix and the stored compared_sha256).  'negatives' names the (config, case) run whose frame 5 carries the negative checks; None skips them and the
# acceptance key negatives_ok stays None.  The historic entry is the former single pin (OBS_FILE_SHA_PREFIX / OBS_COMPARED_SHA); its behaviour and its
# verification.json / frontier.json are unchanged apart from the recorded SHA256 of this file.
KNOWN_OBSERVATIONS = collections.OrderedDict([
    ('historic', dict(file_sha_prefix='66d30130d8a11a86', compared_sha256='4bb6b9336274742a492182b8a745f48a574ba456aa94856c535395f89f969b62',
                      negatives=('P1', 0))),
    ('io-ext', dict(file_sha_prefix='9da40ac6dcbea3eb', compared_sha256='b5d15d4fcd53555bce3f4773c8ee6113c6b79ee5aac113f6c1e59a87ddc57161',
                    negatives=('P1', 94))),          # no P1 case 0 run; P1 case 94 passes every check (case 68 misses palette-not-attached)
    ('io-ext2', dict(file_sha_prefix='bac35488287f2a5a', compared_sha256='d30e68d6b8c7f69181be12b00f017c4eafccb705416af7e8beea02b6d9595673',
                     negatives=('P1', 94))),         # third observation (tools/observe_animation_machine_io_ext2.py, area-C plan section 11)
])
OBS_FILE_SHA_PREFIX = KNOWN_OBSERVATIONS['historic']['file_sha_prefix']
OBS_COMPARED_SHA = KNOWN_OBSERVATIONS['historic']['compared_sha256']
HISTORIC_SEED_SHA = '1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207'
KEYS = O.KEYS
PVC_LO, PVC_HI = 0x2fe000, 0x300000
MODE_PASS, MODE_STEP, MODE_SEG = 0, 1, 4
SEG_H, SEG_N, SEG_C = 0, 1, 2
SEG_CODE = {'H': SEG_H, 'N': SEG_N, 'C': SEG_C}
OPT_CARD, OPT_EXEC, OPT_IRQ, OPT_PAL = 0x100, 0x200, 0x800, 0x1000
CARD_BIOS, CARD_BYTE, CARD_ANSWER = 0xc00468, 0x10fdc6, 0x80
UNSUPPORTED = 'unsupported animation machine PC'
# Native guard kind -> the exact checked C++ error (the native frame did not complete; C++ must fail with this text and preserve everything).
# Sources: D1 / controller / IRQ verifiers (NATIVE_END_ERROR) and engine/src (animation_machine.cpp am_read / am_write, animation_machine_frame.cpp).
NATIVE_END_ERROR = collections.OrderedDict([
    ('system-return', 'animation frame controller system return'),                  # C fetch of BIOS c00444 (JMP, always the end of the controller)
    ('external-read-queue-empty', 'animation machine external read queue empty'),    # H reads more than the declared queue
    ('undeclared-device-read', 'animation machine external read queue empty'),       # direct input / raster port read in N or C: the queue is already consumed by H
    ('rom-write', 'unsupported animation machine write device'),                    # am_write outside RAM / PVC / palette (scope decision 2: checked stop in v1)
    ('bios-boundary', UNSUPPORTED),                                                  # fetch in the BIOS window outside the declared c00444 / c00468
    ('odd-pc', 'unaligned animation machine PC'),
    ('fetch-unmapped', 'animation fade card odd JSR target'),
    ('wait-not-released', 'animation irq wait not released'),
    ('irq:bios-int1', 'animation irq bios int1 boundary'),
    ('irq:internal-wait', 'animation irq internal wait'),
    ('irq:regs-differ', 'animation irq register restore mismatch'),
    ('irq:undeclared-read', 'animation irq external read overrun'),
])
# Native guard kinds the observation can produce that have no declared C++ error (reported, never silently passed).
CHAIN_VERIFIED_CONFIGS = ('boot-demo-0', 'boot-title-start', 'boot-title-idle', 'fx-start-c79a')
CTX = {}
HINT = {}


# ----------------------------------------------------------------------------------
# Pure helpers (ROM-free)
# ----------------------------------------------------------------------------------
def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def ports_digest(events):
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-PORTS-1')
    for e in events:
        h.update(struct.pack('>BIBI', e[0], e[1], e[2], e[3]))
    return h.hexdigest()


def native_form(ports, split_long=False):
    """C++ (address, size, value) -> native tuples (kind, address, size, value): PVC page writes are kind 1 (WORD value & ffff), the rest kind 2.  split_long: every
    MOVE.L 3c0000 event becomes the WORD pair 3c0000 / 3c0002 (the native form of the 4fcce / 4fcda callbacks)."""
    out = []
    for a, n, v in ports:
        if PVC_LO <= a < PVC_HI:
            out.append((1, a, n, v & 0xffff) if n == 2 else (1, a, n, v))
        elif split_long and a == 0x3c0000 and n == 4:
            out.append((2, 0x3c0000, 2, v >> 16))
            out.append((2, 0x3c0002, 2, v & 0xffff))
        else:
            out.append((2, a, n, v))
    return out


def _pk(e):
    return struct.pack('>BIBI', e[0], e[1], e[2], e[3])


def _digest_of(chunks):
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-PORTS-1')
    h.update(b''.join(chunks))
    return h.hexdigest()


def match_ports(ports, count, digest, hint=None):
    """-> (ok, variant, cpp_count, window).  The C++ ports equal the native [count, sha] in the plain form, with every MOVE.L 3c0000 as a WORD pair ('long-pair'), or with one run
    of consecutive MOVE.L 3c0000 events as WORD pairs ('long-window': the native form of the 4fcce / 4fcda callbacks; the run is found by search, `hint` = the previous (start, k))."""
    plain_ev = native_form(ports, False)
    plain = [_pk(e) for e in plain_ev]
    if len(plain) == count and _digest_of(plain) == digest:
        return True, 'plain', len(plain), None
    longs = [i for i, (a, n, v) in enumerate(ports) if a == 0x3c0000 and n == 4]
    k = count - len(plain)
    if k <= 0 or k > len(longs):
        return False, None, len(plain), None
    pair = dict((i, _pk((2, 0x3c0000, 2, ports[i][2] >> 16)) + _pk((2, 0x3c0002, 2, ports[i][2] & 0xffff))) for i in longs)
    if k == len(longs):
        chunks = [pair.get(i, plain[i]) for i in range(len(ports))]
        if _digest_of(chunks) == digest:
            return True, 'long-pair', len(plain) + k, None
    starts = list(range(0, len(longs) - k + 1))
    if hint is not None and hint[1] == k and hint[0] in starts:
        starts.remove(hint[0])
        starts.insert(0, hint[0])
    for s in starts:
        win = set(longs[s:s + k])
        chunks = [pair[i] if i in win else plain[i] for i in range(len(ports))]
        if _digest_of(chunks) == digest:
            return True, 'long-window', len(plain) + k, (s, k)
    return False, None, len(plain), None


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b)) if len(a) != len(b) else None


def be(ram, address, size):
    o = address & 0xffff
    return int.from_bytes(bytes(ram[o:o + size]), 'big')


def got_state(got, status):
    """C++ result -> state dict of the observer (bank = base, ff8, ff9 from the modelled PVC page 1ff0..1ff3)."""
    pvc = got['pvc']
    return dict(regs=got['regs'], pc=got['pc'], bank=(got['bank_base'], int.from_bytes(pvc[0x1ff0:0x1ff2], 'big'), int.from_bytes(pvc[0x1ff2:0x1ff4], 'big')),
                status=status, ram=got['ram'], pvc=pvc, palette=got['palette'])


def encode_request(mode, st, queue, segment=0, stop=0, irq=True, palette=True, z80=0, video=0, card_resume=True, exec_ctrl=True):
    ram, pvc = st['ram'], st['pvc']
    b0, b1, sel = st['palette']
    assert len(ram) == 65536 and len(pvc) == 8192 and len(b0) == 8192 and len(b1) == 8192
    options = (OPT_CARD if card_resume else 0) | CARD_ANSWER | (OPT_EXEC if exec_ctrl else 0) | (OPT_IRQ if irq else 0) | (OPT_PAL if palette else 0)
    values = [mode] + [st['regs'][k] & 0xffffffff for k in KEYS] + [st['pc'], st.get('carry', 0), st['bank'][0], st['status'], options, 0x01010000, z80 & 0xff, video & 0xffff,
                                                                     sel, len(queue), segment, stop]
    return struct.pack('>29I', *values) + bytes(ram) + bytes(pvc) + bytes(b0) + bytes(b1) + b''.join(struct.pack('>III', *e) for e in queue)


def parse_response(payload):
    if len(payload) < 8:
        raise ValueError('short harness packet')
    ok = struct.unpack_from('>I', payload)[0]
    if ok == 0:
        return dict(ok=False, preserved=struct.unpack_from('>I', payload, 4)[0] == 1, error=payload[8:].decode('latin-1'))
    n0 = 35
    if ok != 1 or len(payload) < 4 * n0 + 65536 + 8192 + 16384:
        raise ValueError('invalid harness packet')
    v = struct.unpack_from('>%dI' % n0, payload)
    pc, carry, bank, head_pc, ctrl_pc, stop_pc, exit_pc, hreads, nreads, creads, nh, nn, nc, nw, nr, ni, np_, sel = v[1:19]
    regs = dict(zip(KEYS, v[19:35]))
    at = 4 * n0
    if len(payload) != at + 65536 + 8192 + 16384 + 12 * (nh + nn + nc + np_ + nr) + 24 * nw + 32 * ni:
        raise ValueError('invalid harness packet length')
    ram = payload[at:at + 65536]
    at += 65536
    pvc = payload[at:at + 8192]
    at += 8192
    pal = (payload[at:at + 8192], payload[at + 8192:at + 16384], sel)
    at += 16384

    def triples(n):
        nonlocal at
        out = [struct.unpack_from('>III', payload, at + 12 * i) for i in range(n)]
        at += 12 * n
        return out
    head_ports, node_ports, ctrl_ports = triples(nh), triples(nn), triples(nc)
    waits = [struct.unpack_from('>6I', payload, at + 24 * i) for i in range(nw)]
    at += 24 * nw
    irqs = [struct.unpack_from('>8I', payload, at + 32 * i) for i in range(ni)]
    at += 32 * ni
    irq_ports = triples(np_)
    remaining = triples(nr)
    return dict(ok=True, pc=pc, carry=carry, bank_base=bank, head_pc=head_pc, controller_pc=ctrl_pc, pass_stop_pc=stop_pc, controller_exit_pc=exit_pc,
                head_reads=hreads, node_reads=nreads, controller_reads=creads, regs=regs, ram=ram, pvc=pvc, palette=pal, head_ports=head_ports,
                node_ports=node_ports, controller_ports=ctrl_ports, waits=waits, irqs=irqs, irq_ports=irq_ports, remaining=remaining)


class Harness(object):
    def __init__(self, exe, resources, stderr_path):
        self.err = open(stderr_path, 'ab')
        self.proc = subprocess.Popen([str(exe)] + [str(p) for p in resources], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, close_fds=False)
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


def effective_start(st, rec):
    """Frame-start state with the declared host writes of the frame applied.  The observer captures the start of a frame whose H stops (guard in H) BEFORE the writes, every other
    frame after them: a recorded write whose address already holds `new` is applied, one that still holds `old` is applied here.  -> (state, number of writes applied here)."""
    ram = bytearray(st['ram'])
    n = 0
    final = collections.OrderedDict()
    for a, s_, old, new, mode in rec['hw']:
        k = (a, s_)
        final[k] = (final[k][0], new) if k in final else (old, new)           # several writes to one address: first old, last new
    for (a, s_), (old, new) in final.items():
        o = a & 0xffff
        cur = int.from_bytes(ram[o:o + s_], 'big')
        if cur != new:
            assert cur == old, 'recorded host write neither pending nor applied'
            ram[o:o + s_] = new.to_bytes(s_, 'big')
            n += 1
    if not n:
        return st, 0
    out = dict(st)
    out['ram'] = bytes(ram)
    return out, n


def apply_host_writes(st, frame, writes):
    """Declared host writes of `frame` (observation host_writes rows: frames [lo, hi], address, size, value, mode) on a copy of the state."""
    ram = bytearray(st['ram'])
    rows = []
    for w in writes:
        lo, hi = w['frames']
        if not lo <= frame <= hi:
            continue
        o = w['address'] & 0xffff
        old = int.from_bytes(ram[o:o + w['size']], 'big')
        new = w['value'] if w['mode'] == 'set' else (old | w['value'])
        ram[o:o + w['size']] = new.to_bytes(w['size'], 'big')
        rows.append([w['address'], w['size'], old, new, w['mode']])
    out = dict(st)
    out['ram'] = bytes(ram)
    return out, rows


# ----------------------------------------------------------------------------------
# Frame comparison
# ----------------------------------------------------------------------------------
def expected_waits(rec):
    out = []
    for key, code in (('H', SEG_H), ('C', SEG_C), ('N', SEG_N)):
        seg = rec.get(key)
        if not seg:
            continue
        for w in seg['waits']:
            out.append((code, w[0], CARD_BYTE if w[0] == CARD_BIOS else None))
    return out


def native_end_state(rec_next, st_next, rec):
    """Native N.end state reconstructed from the next recorded start state with the declared host writes of the next frame undone (None without a next frame)."""
    if rec_next is None or st_next is None:
        return None
    ram = bytearray(st_next['ram'])
    for a, s, old, new, mode in rec_next['hw']:
        o = a & 0xffff
        ram[o:o + s] = old.to_bytes(s, 'big')
    out = dict(st_next)
    out['ram'] = bytes(ram)
    return out


def state_detail(g, n):
    """First differing field of two state dicts (observer form)."""
    for k in KEYS:
        if g['regs'][k] != n['regs'][k]:
            return dict(field='reg-' + k, cpp=g['regs'][k], native=n['regs'][k])
    if g['pc'] != n['pc']:
        return dict(field='pc', cpp=g['pc'], native=n['pc'])
    if g['bank'] != n['bank']:
        return dict(field='bank', cpp=list(g['bank']), native=list(n['bank']))
    if g['ram'] != n['ram']:
        i = first_diff(g['ram'], n['ram'])
        return dict(field='ram', address=0x100000 + i, cpp=g['ram'][i], native=n['ram'][i], count=sum(1 for x, y in zip(g['ram'], n['ram']) if x != y))
    if g['pvc'] != n['pvc']:
        return dict(field='pvc', first=PVC_LO + first_diff(g['pvc'], n['pvc']))
    for b in (0, 1):
        if g['palette'][b] != n['palette'][b]:
            return dict(field='palette-bank%d' % b, first=first_diff(g['palette'][b], n['palette'][b]))
    if g['palette'][2] != n['palette'][2]:
        return dict(field='palette-selected', cpp=g['palette'][2], native=n['palette'][2])
    return dict(field='state-digest-only')


def compare_frame(rec, status, got, native_end=None, tally=None):
    """Mismatch list of one C++ frame result against the recorded native frame (empty = equal).  `got` is a successful harness response."""
    bad = []
    n_rec = rec['N']
    gs = got_state(got, status)
    if O.state_digest(gs) != n_rec['end']:
        d = state_detail(gs, native_end) if native_end is not None else dict(field='state-digest-only')
        bad.append(dict(d, field='end-state:' + d['field']))
    if got['carry'] != 0:
        bad.append(dict(field='carry', cpp=got['carry'], native='Unknown(0)'))
    H, C, N = rec.get('H'), rec.get('C'), n_rec
    for key, ports, seg in (('H', got['head_ports'], H), ('C', got['controller_ports'], C), ('N', got['node_ports'], N)):
        if seg is None:
            if ports:
                bad.append(dict(field='ports-' + key, why='C++ produced ports for a segment the native frame does not have', cpp_len=len(ports)))
            continue
        ok, variant, ncpp, win = match_ports(ports, seg['ports'][0], seg['ports'][1], HINT.get(key))
        if ok and win is not None:
            HINT[key] = win
        if ok and tally is not None and variant != 'plain':
            tally[key + ':' + variant] += 1
        if not ok:
            bad.append(dict(field='ports-' + key, cpp_len=ncpp, native_len=seg['ports'][0]))
    # IRQ records and ports
    exp = rec['irq']
    irqs = got['irqs']
    if len(irqs) != len(exp):
        bad.append(dict(field='irqs', cpp_len=len(irqs), native_len=len(exp)))
    else:
        for i, (q, e) in enumerate(zip(irqs, exp)):
            seg, wait_pc, seq, pb, pe, reads, bios, rte = q
            ok_ports, _, ncpp, _w = match_ports(got['irq_ports'][pb:pe], e['ports'][0], e['ports'][1])
            cpp_t = (seg, wait_pc, seq, reads, bios, rte, ok_ports)
            nat_t = (SEG_CODE[e['seg']], e['pc'], i, e['reads'], e['bios'], e['sr'], True)
            if cpp_t != nat_t or e['res'] != 'ok':
                bad.append(dict(field='irq', index=i, cpp=list(cpp_t), native=list(nat_t), cpp_ports=ncpp, native_ports=e['ports'][0]))
                break
    if len(got['irq_ports']) != sum(q[4] - q[3] for q in irqs):
        bad.append(dict(field='irq-ports-total', cpp=len(got['irq_ports']), native=sum(q[4] - q[3] for q in irqs)))
    # card waits
    ew = expected_waits(rec)
    cw = [(w[0], w[1], w[2] if w[1] == CARD_BIOS else None) for w in got['waits']]
    if cw != ew or any(w[1] == CARD_BIOS and w[5] != CARD_ANSWER for w in got['waits']):
        bad.append(dict(field='waits', cpp=[list(w) for w in cw], native=[list(w) for w in ew]))
    # external reads: every queue entry consumed, plus the status byte reads recorded natively
    status_reads = sum((s['status'] if s else 0) for s in (H, C, N))
    total = got['head_reads'] + got['controller_reads'] + got['node_reads']
    if got['remaining']:
        bad.append(dict(field='queue-not-consumed', left=len(got['remaining'])))
    if total != len(rec['q']) + status_reads:
        bad.append(dict(field='external-reads', cpp=total, native=len(rec['q']) + status_reads))
    if H is not None:
        if (got['head_pc'], got['controller_pc']) != (H['head_cb'], H['ctrl_cb']):
            bad.append(dict(field='head-controller-pc', cpp=[got['head_pc'], got['controller_pc']], native=[H['head_cb'], H['ctrl_cb']]))
    elif got['head_pc'] or got['controller_pc'] or got['head_ports'] or got['head_reads']:
        bad.append(dict(field='head-output-in-pass'))
    if C is not None:
        if got['controller_exit_pc'] != C['exit']:
            bad.append(dict(field='controller-exit', cpp=got['controller_exit_pc'], native=C['exit']))
    elif got['controller_exit_pc'] or got['controller_reads']:
        bad.append(dict(field='controller-output-in-pass'))
    if got['pass_stop_pc'] != be(got['ram'], 0x100820, 4) or got['pass_stop_pc'] not in (0xe4a, 0xe74):
        bad.append(dict(field='pass-stop-pc', cpp=got['pass_stop_pc']))
    return bad


def check_expected_failure(got, native_kind):
    expected = NATIVE_END_ERROR.get(native_kind)
    if got['ok']:
        return dict(ok=False, native_kind=native_kind, why='C++ completed where native did not complete the frame')
    ok = bool(got['preserved']) and expected is not None and got['error'] == expected
    r = dict(ok=ok, native_kind=native_kind, expected_error=expected, error=got['error'], preserved=got['preserved'])
    if not ok:
        r['why'] = 'native stop kind without a declared C++ error' if expected is None else ('C++ error differs' if got['error'] != expected else 'state not preserved')
    return r


# ----------------------------------------------------------------------------------
# Frontier confirmation (check_fail_pc approach)
# ----------------------------------------------------------------------------------
def pc_routed(pc):
    return CTX['U'].pc_routed(pc)


def segment_request(st, queue, seg, stop):
    return encode_request(MODE_SEG, st, queue, segment=seg, stop=stop)


def confirm_frontier(h, frame, st, queue, phase, pc):
    """Run the frame segment by segment (H, C, N) from the native start state with stop = pc in `phase`.  -> dict(ok, ...)."""
    if pc & 1:
        return dict(ok=False, why='odd candidate')
    if pc_routed(pc):
        return dict(ok=False, why='candidate is routed by the dispatch chain')
    order = [('N', SEG_N)] if frame == 0 else [('H', SEG_H), ('C', SEG_C), ('N', SEG_N)]
    cur, q = dict(st), list(queue)
    for name, code in order:
        if name == phase:
            stop = pc
        elif name == 'H':
            stop = be(cur['ram'], 0x1008e4, 4)
        elif name == 'C':
            stop = 0x2ac2
        else:
            stop = be(cur['ram'], 0x100820, 4)
        got = h.call(segment_request(cur, q, code, stop))
        if not got['ok']:
            return dict(ok=False, why='segment %s failed before the candidate' % name if name != phase else 'stop not reached', error=got['error'])
        if name == phase:
            if got['pc'] != pc:
                return dict(ok=False, why='segment ended at a different PC', end_pc=got['pc'])
            a7 = got['regs']['a7']
            a6 = got['regs']['a6']
            return dict(ok=True, pc=pc, phase=phase, a7=a7, a7_long=be(got['ram'], a7, 4), a6=a6, a6_long=be(got['ram'], a6, 4),
                        a0=got['regs']['a0'], stop_state_sha=sha(got['ram'])[:16])
        cur = got_state(got, st['status'])
        cur['carry'] = got['carry']
        q = got['remaining']
    return dict(ok=False, why='phase %s not in the frame' % phase)


def locate_frontier(h, rec, f, st, queue):
    """Candidates: native first unrouted TB PC, then the unrouted PCs first seen in the frame (listed order).  -> dict."""
    cands = []
    if rec.get('unr_first'):
        cands.append((rec['unr_first'][0], rec['unr_first'][1]))
    for pc, cnt, ph in rec.get('unr_new', []):
        if (ph, pc) not in cands:
            cands.append((ph, pc))
    for ph, addr, size, cnt in rec.get('tbs', []):                        # key frames carry the executed TB list (guard frames too)
        if addr < 0x100000 and not addr & 1 and (ph, addr) not in cands:
            cands.append((ph, addr))
    tried = []
    for ph, pc in cands[:400]:
        r = confirm_frontier(h, f, st, queue, ph, pc)
        tried.append(dict(phase=ph, pc=pc, ok=r['ok'], why=r.get('why')))
        if r['ok']:
            return dict(confirmed=True, frame=f, candidates_tried=len(tried), **r)
    return dict(confirmed=False, frame=f, candidates=len(cands), tried=tried[:8])


# ----------------------------------------------------------------------------------
# One run
# ----------------------------------------------------------------------------------
def load_run(entry):
    nat = CTX['native']
    raw = gzip.decompress((nat / entry['records']['path']).read_bytes())
    assert sha(raw) == entry['records']['sha256'], 'run record SHA mismatch ' + entry['records']['path']
    body = json.loads(raw)
    sp = gzip.decompress((nat / entry['states']['path']).read_bytes())
    assert sha(sp) == entry['states']['sha256'], 'state pack SHA mismatch ' + entry['states']['path']
    pack = O.read_pack(sp)
    states = {}
    for fr, st, dig in pack:
        states[fr] = (st, dig)
    return body, states


def harness_for_worker():
    h = CTX.get('harness')
    if h is None:
        h = Harness(CTX['exe'], CTX['resources'], CTX['stderr_dir'] / ('harness.%d.stderr' % os.getpid()))
        CTX['harness'] = h
    return h


def request_frame(f, st, queue, **kw):
    return encode_request(MODE_PASS if f == 0 else MODE_STEP, st, queue, **kw)


def run_one(task):
    entry = task['entry']
    max_frames = task.get('max_frames')
    h = harness_for_worker()
    body, states = load_run(entry)
    frames = body['frames']
    if max_frames is not None:
        frames = frames[:max_frames]
    nf = len(frames)
    cfg, case = entry['config'], entry['case']
    writes = entry['host_writes']
    real_chain = cfg in CHAIN_VERIFIED_CONFIGS or task.get('real_chain', False)
    t0 = time.time()
    row = dict(config=cfg, case=case, native_frames=len(body['frames']), native_stop=entry['summary']['stop'].get('reason'), native_guard=None,
               compared=0, matched=0, mismatched=0, unrouted=0, cpp_errors=0, beyond_matched=0, beyond_unrouted=0, beyond_mismatched=0, guard_check=None, first_failure=None,
               mismatches=[], error_counts={}, port_variants={}, hw_checks=0, hw_check_fail=0)
    errs = collections.Counter()
    pvar = collections.Counter()
    HINT.clear()
    chain = dict(alive=True, state=None, status=None, matched=0, calls=0, divergences=[], end=None, real_calls=0, reused=0)
    frontier = None
    first_fail = None
    guard_rec = None
    for f, rec in enumerate(frames):
        st, dig = states[f]
        assert dig == rec['start'], 'state pack digest differs from the record start (frame %d)' % f
        st, pending_hw = effective_start(st, rec)
        eff_start = rec['start'] if not pending_hw else O.state_digest(st)
        if pending_hw:
            row['pending_host_write_frames'] = row.get('pending_host_write_frames', 0) + 1
        queue = [tuple(e) for e in rec['q']]
        guard = rec['guard']
        got = h.call(request_frame(f, st, queue))
        status = st['status']
        beyond = first_fail is not None
        kind = None
        if guard is not None:
            guard_rec = dict(frame=f, **guard)
            row['native_guard'] = dict(frame=f, kind=guard['kind'], seg=guard['seg'])
            chk = check_expected_failure(got, guard['kind'])
            if not chk['ok'] and not got['ok'] and got['error'] == UNSUPPORTED:
                chk['behind_frontier'] = True
            row['guard_check'] = dict(chk, frame=f, kind=guard['kind'], native_start_state=True)
            kind = 'guard-ok' if chk['ok'] else ('guard-behind-frontier' if got.get('error') == UNSUPPORTED else 'guard-bad')
            if first_fail is None:
                first_fail = dict(frame=f, kind=kind, error=None if got['ok'] else got['error'])
                if kind == 'guard-behind-frontier':           # an unrouted PC is reached before the native guard: locate it like any frontier
                    frontier = locate_frontier(h, rec, f, st, queue)
                    frontier['error'] = got['error']
                    frontier['preserved'] = got['preserved']
            # chain reaches the guard frame only while alive
            if chain['alive']:
                cs = chain_start(chain, f, eff_start, writes, st)
                chain['end'] = dict(frame=f, why='native-guard', check_from_chain=(chk if cs['same'] else None), chain_state_equal=cs['same'])
            break
        row['compared'] += 1
        if got['ok']:
            nrec = frames[f + 1] if f + 1 < len(frames) else None
            nend = native_end_state(nrec, states[f + 1][0] if f + 1 < len(frames) else None, rec)
            bad = compare_frame(rec, status, got, nend, pvar)
            if bad:
                row['mismatched' if not beyond else 'beyond_mismatched'] += 1
                if len(row['mismatches']) < 3:
                    row['mismatches'].append(dict(frame=f, fields=bad[:4]))
                kind = 'mismatch'
                if first_fail is None:
                    first_fail = dict(frame=f, kind='mismatch', error=None)
            else:
                row['matched' if not beyond else 'beyond_matched'] += 1
                kind = 'match'
        else:
            errs[got['error']] += 1
            if got['error'] == UNSUPPORTED:
                row['unrouted' if not beyond else 'beyond_unrouted'] += 1
                kind = 'unrouted'
            else:
                row['cpp_errors'] += 1
                kind = 'cpp-error'
            if first_fail is None:
                first_fail = dict(frame=f, kind=kind, error=got['error'], preserved=got['preserved'])
                if kind == 'unrouted':
                    frontier = locate_frontier(h, rec, f, st, queue)
                    frontier['error'] = got['error']
                    frontier['preserved'] = got['preserved']
        # ---- pure C++ chain
        if chain['alive']:
            cs = chain_start(chain, f, eff_start, writes, st)
            if cs['same'] and not real_chain:
                cgot = got
                chain['reused'] += 1
            else:
                cgot = h.call(request_frame(f, cs['state'], queue))
                chain['real_calls'] += 1
                if cs['same'] and (cgot['ok'] != got['ok'] or (got['ok'] and O.state_digest(got_state(cgot, status)) != O.state_digest(got_state(got, status)))):
                    chain['divergences'].append(dict(frame=f, why='real chain call differs from the frame-wise call on an equal start state'))
                if not cs['same'] and len(chain['divergences']) < 3:
                    chain['divergences'].append(dict(frame=f, why='chain start digest differs from the native start'))
            if not cgot['ok']:
                chain['alive'] = False
                chain['end'] = dict(frame=f, why='cpp-failure', error=cgot['error'])
            else:
                bad_c = compare_frame(rec, status, cgot, None) if not cs['same'] else []
                chain['matched'] += int(cs['same'] and kind == 'match')
                chain['state'] = got_state(cgot, status)
                chain['state']['carry'] = 0
                chain['status'] = status
                if cs['same'] and kind != 'match':
                    chain['alive'] = False
                    chain['end'] = dict(frame=f, why='mismatch')
    else:
        if chain['alive']:
            chain['end'] = dict(frame=nf - 1, why='all-frames')
    if chain['alive'] and chain['end'] is None:
        chain['end'] = dict(frame=nf - 1, why='all-frames')
    chain.pop('state')
    chain.pop('status')
    row['error_counts'] = dict(sorted(errs.items()))
    row['port_variants'] = dict(pvar)
    row['first_failure'] = first_fail
    row['frontier'] = frontier
    row['chain'] = dict(matched_frames=chain['matched'], end=chain['end'], reused=chain['reused'], real_calls=chain['real_calls'], divergences=chain['divergences'][:3],
                        divergence_count=len(chain['divergences']))
    row['native_unr_frames'] = entry['summary'].get('unr_frames')
    nat_first_unr = None
    for r in body['frames']:
        if r.get('unr_first'):
            nat_first_unr = r['f']
            break
    row['native_first_unrouted_frame'] = nat_first_unr
    row['native_new_unrouted'] = {k: v for k, v in body['unr_pcs'].items()}
    row['seconds'] = round(time.time() - t0, 1)
    return row


def chain_start(chain, f, start_digest, writes, nat_st):
    """Start state of the chained frame: frame 0 = native start; frame k = previous C++ output + declared host writes.  -> dict(state, same)."""
    if f == 0 or chain['state'] is None:
        return dict(state=nat_st, same=True)
    st = chain['state']
    st2, rows = apply_host_writes(st, f, writes)
    same = O.state_digest(st2) == start_digest
    return dict(state=st2, same=same, rows=rows)


# ----------------------------------------------------------------------------------
# Negative checks
# ----------------------------------------------------------------------------------
def negatives(entry_gen):
    """Detection of: RAM byte, queue value / order / count, missing host write, IRQ option, forged results, malformed packets.  Runs on the first frames of P1 case 0."""
    h = harness_for_worker()
    entry = entry_gen
    body, states = load_run(entry)
    frames = body['frames']
    f = 5
    rec = frames[f]
    st = states[f][0]
    status = st['status']
    queue = [tuple(e) for e in rec['q']]
    nend = native_end_state(frames[f + 1], states[f + 1][0], rec)
    base = h.call(request_frame(f, st, queue))
    tests = {}
    tests['baseline-equal'] = dict(detected=bool(base['ok'] and not compare_frame(rec, status, base, nend)))

    def detected(label, bad_expected=True, **kw):
        s = kw.pop('st', st)
        q = kw.pop('q', queue)
        got = h.call(request_frame(f, s, q, **kw))
        bad = [dict(field='cpp-error', error=got['error'])] if not got['ok'] else compare_frame(rec, status, got, None)
        tests[label] = dict(detected=bool(bad), first=bad[0]['field'] if bad else None, error=None if got['ok'] else got['error'])
        return got
    ram = bytearray(st['ram'])
    ram[0x4000] ^= 1
    s2 = dict(st, ram=bytes(ram))
    detected('ram-byte-changed', st=s2)
    pal = (bytes([st['palette'][0][0] ^ 1]) + st['palette'][0][1:], st['palette'][1], st['palette'][2])
    detected('palette-byte-changed', st=dict(st, palette=pal))
    detected('queue-value-changed', q=[(a, s, (v ^ 1) & (0xffff if s == 2 else 0xff)) if a == 0x300000 else (a, s, v) for a, s, v in queue])
    swapped = list(queue)
    swapped[2], swapped[3] = swapped[3], swapped[2]
    detected('queue-order-swapped', q=swapped)
    detected('queue-short', q=queue[:-1])
    detected('queue-extra-entry', q=queue + [(0x300000, 1, 0x5a)])
    detected('irq-execution-off', irq=False)
    detected('z80-reply-changed', z80=0x5a)
    detected('video-status-changed', video=8)
    detected('palette-not-attached', palette=False)
    detected('controller-skip', exec_ctrl=False)
    # host write missing: the chain start of frame 1 without the declared player-start write must differ from the native start
    st1 = states[1][0]
    st0 = states[0][0]
    cut = [w for w in entry['host_writes'] if not (w['frames'][0] == 1 and w['address'] == 0x10f006)]
    full_chain_state = h.call(request_frame(0, st0, []))
    cstate = got_state(full_chain_state, st0['status']) if full_chain_state['ok'] else None
    start_ok, _ = apply_host_writes(cstate, 1, entry['host_writes'])
    start_cut, _ = apply_host_writes(cstate, 1, cut)
    tests['host-write-matches-native'] = dict(detected=O.state_digest(start_ok) == frames[1]['start'])
    tests['host-write-missing'] = dict(detected=O.state_digest(start_cut) != frames[1]['start'])
    # forged C++ results must be rejected by the comparison
    g0 = dict(base, irqs=list(base['irqs']), irq_ports=list(base['irq_ports']), waits=list(base['waits']), node_ports=list(base['node_ports']),
              head_ports=list(base['head_ports']), controller_ports=list(base['controller_ports']))
    forged = collections.OrderedDict()
    forged['result-ram'] = lambda g: g.update(ram=bytes([g['ram'][0] ^ 1]) + g['ram'][1:])
    forged['result-reg'] = lambda g: g.update(regs=dict(g['regs'], d3=g['regs']['d3'] ^ 1))
    forged['result-pc'] = lambda g: g.update(pc=g['pc'] ^ 2)
    forged['result-pvc'] = lambda g: g.update(pvc=bytes([g['pvc'][0] ^ 1]) + g['pvc'][1:])
    forged['result-palette-byte'] = lambda g: g.update(palette=(bytes([g['palette'][0][0] ^ 1]) + g['palette'][0][1:], g['palette'][1], g['palette'][2]))
    forged['result-palette-selected'] = lambda g: g.update(palette=(g['palette'][0], g['palette'][1], g['palette'][2] ^ 1))
    forged['result-irq-dropped'] = lambda g: g['irqs'].pop()
    forged['result-irq-sr'] = lambda g: g['irqs'].__setitem__(0, tuple(g['irqs'][0][:7]) + (0x2001,))
    forged['result-irq-port-value'] = lambda g: g['irq_ports'].__setitem__(0, (g['irq_ports'][0][0], g['irq_ports'][0][1], g['irq_ports'][0][2] ^ 1))
    forged['result-node-port-value'] = lambda g: g['node_ports'].__setitem__(0, (g['node_ports'][0][0], g['node_ports'][0][1], g['node_ports'][0][2] ^ 1))
    forged['result-head-port-dropped'] = lambda g: g['head_ports'].pop() if g['head_ports'] else g['head_ports'].append((0x300001, 1, 0))
    forged['result-controller-port-dropped'] = lambda g: g['controller_ports'].pop() if g['controller_ports'] else g['controller_ports'].append((0x300001, 1, 0))
    forged['result-wait-dropped'] = lambda g: g['waits'].pop() if g['waits'] else g.update(waits=[(0, 0xef2, 0, 1, 0, 0)])
    forged['result-queue-left'] = lambda g: g.update(remaining=[(0x300000, 1, 0)])
    forged['result-controller-exit'] = lambda g: g.update(controller_exit_pc=g['controller_exit_pc'] ^ 2)
    forged['result-carry'] = lambda g: g.update(carry=1)
    for label, mutate in forged.items():
        g = dict(g0, irqs=list(g0['irqs']), irq_ports=list(g0['irq_ports']), waits=list(g0['waits']), node_ports=list(g0['node_ports']), head_ports=list(g0['head_ports']),
                 controller_ports=list(g0['controller_ports']))
        mutate(g)
        tests[label] = dict(detected=bool(compare_frame(rec, status, g, None)))
    # C++ side evidence of the native-guard -> checked-error table (typed C++ fixtures on the same completed frame: a declared RAM LONG makes the routed code hit the guard)
    evidence = collections.OrderedDict()

    def evidence_case(label, kind, address, value, expect=None, ram_edit=None):
        ram2 = bytearray(st['ram'])
        if ram_edit is not None:
            ram2[ram_edit[0]] &= ram_edit[1]
        else:
            ram2[address & 0xffff:(address & 0xffff) + 4] = value.to_bytes(4, 'big')
        got = h.call(request_frame(f, dict(st, ram=bytes(ram2)), queue))
        want = expect or NATIVE_END_ERROR[kind]
        evidence[label] = dict(kind=kind, edit=('LONG %x := %x' % (address, value)) if ram_edit is None else 'BYTE %x &= %x' % (0x100000 + ram_edit[0], ram_edit[1]),
                               expected_error=want, error=None if got['ok'] else got['error'], preserved=got.get('preserved'), ok=(not got['ok']) and got['error'] == want and bool(got['preserved']))
    evidence_case('rom-write', 'rom-write', 0x10081c, 0x100)
    evidence_case('undeclared-device-read-N', 'undeclared-device-read', 0x100bf4, 0x31d6)
    evidence_case('undeclared-device-read-C', 'undeclared-device-read', 0x1008e4, 0x349c)
    evidence_case('irq:bios-int1', 'irq:bios-int1', 0, 0, ram_edit=(0xfd80, 0x7f))
    tests['guard-evidence-all-ok'] = dict(detected=all(v['ok'] for v in evidence.values()))
    broken = subprocess.run([str(CTX['exe'])] + [str(p) for p in CTX['resources']], input=struct.pack('>I', 11) + b'bad request', stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, close_fds=False)
    tests['malformed-request-nonzero-exit'] = dict(detected=broken.returncode != 0, returncode=broken.returncode)
    try:
        parse_response(b'\0\0\0\x01' + b'\0' * 20)
        tests['malformed-response-rejected'] = dict(detected=False)
    except ValueError:
        tests['malformed-response-rejected'] = dict(detected=True)
    # the native record itself: a state pack whose digest differs from the record must be rejected by the loader assertion
    tests['record-digest-mismatch-rejected'] = dict(detected=O.state_digest(dict(st, ram=bytes(ram))) != rec['start'])
    ok = tests['baseline-equal']['detected'] and all(v['detected'] for k, v in tests.items() if k != 'baseline-equal')
    return dict(case=entry['case'], config=entry['config'], frame=f, ok=ok, tests=tests, guard_evidence=evidence)


def run_task(task):
    if task.get('negatives'):
        return dict(negatives=negatives(task['entry']))
    try:
        return dict(row=run_one(task))
    except Exception as e:                                       # a verifier fault is a failed row, never a match
        import traceback
        return dict(row=dict(config=task['entry']['config'], case=task['entry']['case'], verifier_error=repr(e), trace=traceback.format_exc()[-1500:]))


def worker_init(exe, resources, native, stderr_dir):
    CTX.update(exe=exe, resources=resources, native=native, stderr_dir=stderr_dir)
    import verify_animation_machine_unit_fixtures as U
    CTX['U'] = U


# ----------------------------------------------------------------------------------
# Static closure and grouping (an5 rules of the IO-1 probe)
# ----------------------------------------------------------------------------------
def static_setup(program):
    import measure_code_coverage as MC
    text = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    atoms, _ = MC.parse_routed_atoms(text)
    routed = bytearray(0x100000)
    for a in atoms:
        for p in range(a['start'], min(a['end'], 0x100000)):
            routed[p] = 1
    disc, _ = MC.run_discovery(bytes(program), atoms, do_sweep=False)
    roots = set()
    for a, (size, layer, ri) in disc.instrs.items():
        fl = disc.classify(a, size)
        for t, kind in fl.targets:
            if kind == 'call':
                roots.add(t)
        for t, k in fl.pointers:
            if t is not None and t in disc.instrs:
                roots.add(t)
    return dict(MC=MC, atoms=atoms, routed=routed, disc=disc, roots=sorted(roots), routing_sha=file_sha(ROOT / 'engine/src/animation_machine.cpp'))


def root_of(S, pc):
    roots = S['roots']
    i = bisect.bisect_right(roots, pc) - 1
    return roots[i] if i >= 0 and pc - roots[i] < 0x1000 else pc


def area_of(r):
    if 0x1b000 <= r < 0x24000 or 0x4e4c0 <= r < 0x4f400:
        return 'C'
    if 0xde000 <= r < 0xdf400 or 0xe6400 <= r < 0xe7000 or 0xc000 <= r < 0xcc00 or r < 0x1400:
        return 'E'
    return 'D'


def static_closure(S, root, limit=20000, follow_pointers=False):
    """Branches + calls (JSR / BSR) + fall-through from root, stopping at routed PCs (the routing atoms of the checked-out engine/src/animation_machine.cpp)."""
    disc, routed = S['disc'], S['routed']
    seen, todo, leaders, ptrs, unres = set(), [root], {root}, set(), 0
    while todo and len(seen) < limit:
        pc = todo.pop()
        if pc in seen or not 0 <= pc < 0x100000:
            continue
        if routed[pc] and pc != root:
            continue
        d = disc.decode(pc)
        if d is None:
            continue
        seen.add(pc)
        fl = disc.classify(pc, d[0])
        for t, kind in fl.targets:
            if 0 <= t < 0x100000 and not routed[t]:
                leaders.add(t)
                todo.append(t)
        for t, k in fl.pointers:
            if t is not None and 0x100 <= t < 0x100000:
                ptrs.add(t)
                if follow_pointers and t % 2 == 0 and disc.check_target(t) and not routed[t]:
                    leaders.add(t)
                    todo.append(t)
        if fl.unresolved:
            unres += 1
        if fl.fall:
            nxt = pc + d[0]
            if fl.targets:
                leaders.add(nxt)
            todo.append(nxt)
    nbytes = sum(disc.decode(p)[0] for p in seen)
    return dict(instructions=len(seen), leaders=len(leaders & seen), bytes=nbytes, pointers=len(ptrs), unresolved=unres, seen=seen, leader_set=leaders & seen)


def frontier_report(S, rows, base_pcs, entries_by_key):
    """frontier.json content from the run rows."""
    runs = []
    for r in rows:
        fr = r.get('frontier')
        runs.append(dict(config=r['config'], case=r['case'], first_failure=r.get('first_failure'), frontier=fr, native_first_unrouted_frame=r.get('native_first_unrouted_frame'),
                         chain_end=r['chain']['end'] if r.get('chain') else None))
    for x, r in zip(runs, rows):
        x['fixture'] = r['config'].startswith('fx-')
    confirmed = [x for x in runs if x['frontier'] and x['frontier'].get('confirmed') and not x['fixture']]
    unconfirmed = [x for x in runs if x['frontier'] and not x['frontier'].get('confirmed')]
    by_pc = collections.OrderedDict()
    for x in sorted(confirmed, key=lambda x: (x['frontier']['pc'], x['config'], x['case'])):
        pc = x['frontier']['pc']
        e = by_pc.setdefault(pc, dict(pc=pc, runs=0, configs=collections.Counter(), root=root_of(S, pc), area=area_of(root_of(S, pc)), phases=collections.Counter(),
                                      first_frames=[], a7_long=collections.Counter(), a6_long=collections.Counter()))
        e['runs'] += 1
        e['configs'][x['config']] += 1
        e['phases'][x['frontier']['phase']] += 1
        e['first_frames'].append(x['frontier']['frame'])
        e['a7_long'][x['frontier']['a7_long']] += 1
        e['a6_long'][x['frontier']['a6_long']] += 1
    pcs = []
    for pc, e in by_pc.items():
        pcs.append(dict(pc=pc, pc_hex='%x' % pc, runs=e['runs'], configs=dict(sorted(e['configs'].items())), root=e['root'], root_hex='%x' % e['root'], area=e['area'],
                        phases=dict(sorted(e['phases'].items())), frames=dict(min=min(e['first_frames']), max=max(e['first_frames'])),
                        caller_return=dict(('%x' % k, v) for k, v in sorted(e['a7_long'].items(), key=lambda kv: (-kv[1], kv[0]))[:4]),
                        node_callback=dict(('%x' % k, v) for k, v in sorted(e['a6_long'].items(), key=lambda kv: (-kv[1], kv[0]))[:4])))
    # all native unrouted PCs (minus the P0 baseline) of the runs that have a confirmed frontier, by root
    groups = {}
    for r in rows:
        if not (r.get('frontier') and r['frontier'].get('confirmed')) or r['config'].startswith('fx-'):
            continue
        for p, n in r['native_new_unrouted'].items():
            pc = int(p, 16)
            if pc in base_pcs:
                continue
            root = root_of(S, pc)
            g = groups.setdefault(root, dict(execs=0, pcs=set(), runs=set(), frontier_runs=0))
            g['execs'] += n
            g['pcs'].add(pc)
            g['runs'].add((r['config'], r['case']))
    for pcrow in pcs:
        g = groups.setdefault(pcrow['root'], dict(execs=0, pcs=set(), runs=set(), frontier_runs=0))
        g['frontier_runs'] += pcrow['runs']
    roots_rows = []
    closures = {}
    for root, g in groups.items():
        cl = static_closure(S, root)
        closures[root] = cl
        roots_rows.append(dict(root=root, root_hex='%x' % root, area=area_of(root), frontier_runs=g['frontier_runs'], execs=g['execs'], unrouted_pcs=len(g['pcs']),
                               runs=len(g['runs']), closure=dict((k, cl[k]) for k in ('leaders', 'instructions', 'bytes', 'pointers', 'unresolved'))))
    roots_rows.sort(key=lambda x: (-x['frontier_runs'], -x['execs'], x['root']))
    # candidate units: roots of one area connected by calls / branches inside the direct closure of one of them
    parent = dict((r, r) for r in groups)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a in groups:
        for b in groups:
            if a != b and area_of(a) == area_of(b) and b in closures[a]['leader_set']:
                parent[find(a)] = find(b)
    comp = collections.defaultdict(list)
    for r in groups:
        comp[find(r)].append(r)
    units = []
    for k, members in comp.items():
        seen = set()
        leaders = set()
        for m in members:
            seen |= closures[m]['seen']
            leaders |= closures[m]['leader_set']
        nbytes = sum(S['disc'].decode(p)[0] for p in seen)
        fr = sum(groups[m]['frontier_runs'] for m in members)
        urun = set()
        for m in members:
            urun |= groups[m]['runs']
        units.append(dict(area=area_of(members[0]), leader_root=max(members, key=lambda m: (groups[m]['frontier_runs'], groups[m]['execs'], -m)),
                          roots=sorted(members), frontier_runs=fr, execs=sum(groups[m]['execs'] for m in members), unrouted_pcs=sum(len(groups[m]['pcs']) for m in members),
                          runs=len(urun), closure=dict(leaders=len(leaders), instructions=len(seen), bytes=nbytes)))
    units.sort(key=lambda u: (-u['frontier_runs'], -u['execs'], u['leader_root']))
    for i, u in enumerate(units):
        u['rank'] = i + 1
        u['leader_root_hex'] = '%x' % u['leader_root']
        u['roots_hex'] = ['%x' % r for r in u['roots']]
    fam = {}
    for r in rows:
        if not (r.get('frontier') and r['frontier'].get('confirmed')) or r['config'].startswith('fx-'):
            continue
        fname = 'B' if r['config'].startswith('boot-') else 'S'
        for p, n in r['native_new_unrouted'].items():
            pc = int(p, 16)
            if pc in base_pcs:
                continue
            root = root_of(S, pc)
            e = fam.setdefault((fname, area_of(root)), dict(roots=set(), pcs=set(), execs=0))
            e['roots'].add(root)
            e['pcs'].add(pc)
            e['execs'] += n
    families = dict(('%s:%s' % k, dict(roots=len(v['roots']), unrouted_pcs=len(v['pcs']), execs=v['execs'])) for k, v in sorted(fam.items()))
    by_area = collections.OrderedDict()
    for a in ('C', 'D', 'E'):
        rr = [x for x in roots_rows if x['area'] == a]
        by_area[a] = dict(roots=len(rr), frontier_runs=sum(x['frontier_runs'] for x in rr), execs=sum(x['execs'] for x in rr), unrouted_pcs=sum(x['unrouted_pcs'] for x in rr),
                          units=sum(1 for u in units if u['area'] == a))
    return dict(format='ms5-io-frontier', version=1, runs=runs, confirmed_runs=len(confirmed), unconfirmed_runs=[dict(config=x['config'], case=x['case'], frontier=x['frontier']) for x in unconfirmed],
                frontier_pcs=pcs, roots=roots_rows, areas=by_area, families=families, units=units,
                method=dict(root='nearest call / pointer target at or below the PC within 0x1000 (an5 rule) [I]', area='C = 1b000..23fff, 4e4c0..4f3ff; E = de000..df3ff, e6400..e6fff, c000..cbff, <1400; rest D [I]',
                            closure='branches + JSR/BSR + fall-through, stopping at routed PCs of the checked-out engine/src/animation_machine.cpp (direct closure, pointers not followed)',
                            unit='roots of one area connected by a call / branch inside the direct closure of one of them; ranked by frontier runs, then executions',
                            baseline='native unrouted PCs of the P0 control runs are excluded from the root statistics'),
                routing_file_sha256=S['routing_sha'])


# ----------------------------------------------------------------------------------
# Build and main
# ----------------------------------------------------------------------------------
def build_harness(jobs):
    r = subprocess.run(['make', '-C', str(ROOT), '-j%d' % jobs, 'build/frame_io_acceptance'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=False)
    if r.returncode != 0:
        sys.stderr.write(r.stdout.decode('latin-1')[-3000:])
        raise SystemExit('harness build failed')


def seed_info(args, obs):
    chosen = args.seed_dir or os.environ.get('MS5_SEED_DIR')
    pin = obs['pins']['seed']
    if not chosen:
        return dict(seed_dir=None, seed_sha256=pin['observation_sha256'], seed_kind=pin['kind'], note='taken from the observation pins (no seed directory given; the seed is not read)')
    path = Path(chosen)
    path = path if path.is_absolute() else ROOT / path
    f = path / 'observation.json'
    if not f.is_file():
        raise SystemExit('seed observation missing: %s' % f)
    got = file_sha(f)
    if got != pin['observation_sha256']:
        raise SystemExit('seed observation SHA256 %s differs from the observation pin %s' % (got, pin['observation_sha256']))
    return dict(seed_dir=str(path), seed_sha256=got, seed_kind=pin['kind'], note='verified against the observation pin; the seed is not otherwise read (frame-start states come from the observation)')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--observation', default=str(NATIVE_DIR_DEFAULT / 'observation.json'))
    ap.add_argument('--out', default=str(OUT_DEFAULT), help='output directory (default build/animation_machine_io_execution; never the shared artifacts/)')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--configs', default=None, help='comma list of configurations (default all)')
    ap.add_argument('--cases', default=None, help='comma list of seed cases (default all)')
    ap.add_argument('--max-frames', type=int, default=None, help='compare only the first N frames of every run (partial run, never accepted as the full result)')
    ap.add_argument('--reuse-chain', action='store_true', help='speed-up: when the chained start digest equals the native start digest reuse the frame-wise call instead of a real chain call (default: every chained frame is a real call)')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--no-negatives', action='store_true')
    ap.add_argument('--seed-dir', default=None, help='stage_entry_body seed directory (checked against the observation pin); env MS5_SEED_DIR')
    args = ap.parse_args(argv)
    assert not sys.flags.optimize
    t0 = time.time()
    obs_path = Path(args.observation).absolute()
    native = obs_path.parent
    obs_sha = file_sha(obs_path)
    pin_name = next((n for n, p in KNOWN_OBSERVATIONS.items() if obs_sha.startswith(p['file_sha_prefix'])), None)
    if pin_name is None:
        raise SystemExit('observation.json SHA256 %s is not a pinned observation (%s)' % (
            obs_sha, ', '.join('%s %s...' % (n, p['file_sha_prefix']) for n, p in KNOWN_OBSERVATIONS.items())))
    pin = KNOWN_OBSERVATIONS[pin_name]
    obs = json.loads(obs_path.read_text())
    claimed = obs['compared_sha256']
    if claimed != pin['compared_sha256']:
        raise SystemExit('observation compared_sha256 is not the pinned %s (%s)' % (pin['compared_sha256'], pin_name))
    if O.recompute_compared_sha(obs) != claimed:
        raise SystemExit('observation compared_sha256 cannot be recomputed from observation.json')
    if file_sha(TOOLS / 'observe_animation_machine_io.py') != obs['pins']['observer']['sha256']:
        raise SystemExit('tools/observe_animation_machine_io.py differs from the observer that wrote the observation')
    rom_stat = ROM_PATH.stat()
    rom_bytes = ROM_PATH.read_bytes()
    assert sha(rom_bytes) == ROM_SHA
    seed = seed_info(args, obs)
    out = Path(args.out).absolute()
    if out.is_symlink() or any(p.is_symlink() for p in out.parents if p != Path('/')) and False:
        raise SystemExit('output path must not be a symlink')
    if ROOT / 'artifacts' in out.parents or out == ROOT / 'artifacts':
        raise SystemExit('refusing to write into the shared artifacts/ tree (use build/ or a scratch directory)')
    out.mkdir(parents=True, exist_ok=True)
    stderr_dir = out / 'harness_stderr'
    stderr_dir.mkdir(exist_ok=True)
    if not args.no_build:
        build_harness(args.workers)
    if not EXE.exists():
        raise SystemExit('missing %s (build it with make build/frame_io_acceptance)' % EXE)
    import verify_animation_machine as common
    resources, resource_refs = common.resource_audit(ROOT, rom_bytes)
    worker_init(EXE, resources, native, stderr_dir)
    entries = obs['runs']
    configs = args.configs.split(',') if args.configs else None
    cases = [int(x) for x in args.cases.split(',')] if args.cases else None
    entries = [e for e in entries if (configs is None or e['config'] in configs) and (cases is None or e['case'] in cases or e['case'] < 0)]
    for e in entries:
        assert e['mode'] == 'continuous' and e.get('states', {}).get('all_frames'), 'run %s/%s has no all-frame state pack' % (e['config'], e['case'])
    entries.sort(key=lambda e: (e['config'], e['case']))
    tasks = []
    for e in entries:
        tasks.append(dict(entry=e, max_frames=args.max_frames, real_chain=not args.reuse_chain))
    tasks.sort(key=lambda t: (-t['entry']['frames'], t['entry']['config'], t['entry']['case']))
    neg_entry = None
    if pin['negatives'] is not None:   # required for this observation: the named run must exist (historic: P1 case 0, the former fixed choice)
        neg_entry = next((e for e in obs['runs'] if (e['config'], e['case']) == pin['negatives']), None)
        if neg_entry is None:
            raise SystemExit('observation %s has no %s case %d run for the negative checks' % (pin_name, pin['negatives'][0], pin['negatives'][1]))
    ctx = multiprocessing.get_context('fork')
    rows, neg = [], None
    with ctx.Pool(args.workers, initializer=worker_init, initargs=(EXE, resources, native, stderr_dir)) as pool:
        neg_async = None
        if neg_entry is not None and not args.no_negatives:
            neg_async = pool.apply_async(run_task, (dict(negatives=True, entry=neg_entry),))
        for res in pool.imap_unordered(run_task, tasks, chunksize=1):
            r = res['row']
            rows.append(r)
            print('[%6.0fs] %-16s case %4d native %s/%s compared %4d matched %4d unrouted %4d mism %d first %s' % (
                time.time() - t0, r['config'], r['case'], r.get('native_stop'), (r.get('native_guard') or {}).get('kind'), r.get('compared', 0), r.get('matched', 0),
                r.get('unrouted', 0), r.get('mismatched', 0), (r.get('first_failure') or {}).get('frame')) if 'verifier_error' not in r else
                  'VERIFIER ERROR %s %s %s' % (r['config'], r['case'], r['verifier_error']), file=sys.stderr, flush=True)
        if neg_async is not None:
            neg = neg_async.get()['negatives']
    rows.sort(key=lambda r: (r['config'], r['case']))
    rom_stat2 = ROM_PATH.stat()
    assert file_sha(ROM_PATH) == ROM_SHA and rom_stat2.st_mtime_ns == rom_stat.st_mtime_ns and rom_stat2.st_size == rom_stat.st_size, 'ROM changed'
    full = args.configs is None and args.cases is None and args.max_frames is None
    # frontier report
    program = rom_bytes
    S = static_setup(program)
    base_pcs = set(int(x, 16) for x in obs['aggregates']['stage']['baseline_p0_unrouted_pcs'])
    CTX['U'] = __import__('verify_animation_machine_unit_fixtures')
    fr = frontier_report(S, [r for r in rows if 'verifier_error' not in r], base_pcs, None)
    summary = summarize(rows)
    inputs = dict(
        rom=dict(path='extracted/program/maincpu.decrypted.be.bin', sha256=ROM_SHA, size=rom_stat.st_size),
        observation=dict(file_sha256=obs_sha, compared_sha256=pin['compared_sha256'], runs=len(obs['runs']), observer_sha256=obs['pins']['observer']['sha256'],
                         input_scripts_sha256=obs['pins']['input_scripts']['sha256'], scope_doc_sha256=obs['pins']['scope_doc']['sha256'],
                         **({} if pin_name == 'historic' else dict(pin=pin_name, negatives='skipped' if pin['negatives'] is None else '%s/%d' % pin['negatives']))),
        seed=seed, program_rom_resources=resource_refs,
        engine_sources=dict((str(p.relative_to(ROOT)), file_sha(p)) for p in machine_sources()),
        engine_headers=dict((str(p.relative_to(ROOT)), file_sha(p)) for p in sorted(set((ROOT / 'engine/include').rglob('*.h')) | set((ROOT / 'engine/src').rglob('*.h')))),
        harness={str(HARNESS.relative_to(ROOT)): file_sha(HARNESS)}, harness_binary_sha256=file_sha(EXE),
        tools=dict((n, file_sha(TOOLS / n)) for n in ('verify_animation_machine_io.py', 'observe_animation_machine_io.py', 'verify_animation_machine_unit_fixtures.py',
                                                       'verify_animation_machine.py', 'measure_code_coverage.py')),
        routing=dict(file='engine/src/animation_machine.cpp', sha256=S['routing_sha'], atoms=len(S['atoms'])))
    accept = acceptance(rows, neg, summary, full)
    report = dict(format='ms5-io-verification', version=1, tool='tools/verify_animation_machine_io.py', full_run=full, max_frames=args.max_frames, inputs=inputs,
                  native_end_error=NATIVE_END_ERROR, cpp_options=dict(card_resume=True, card_answer=CARD_ANSWER, controller_mode='Execute', irq_execution=True, irq_z80_reply=0,
                                                                      irq_video_status=0, palette_ram=True, credit_resume=False),
                  summary=summary, negative_checks=neg, acceptance=accept, runs=[slim(r) for r in rows],
                  limits=['The native side is the recorded observation (IO-1); nothing is executed natively here.',
                          'Native IRQ pre/post digests are not compared: the C++ driver exposes the IRQ records and ports, not the intermediate states.',
                          'Per-segment native digests (H.end, C.start/end, N.start) are not compared: the C++ packet returns the frame result; the end-state digest, ports, waits and reads cover the frame.',
                          'External-read consumption is compared as a total (queue entries + native status reads) and by complete consumption of the ordered queue; the per-segment split is not recorded natively.',
                          'MOVE.L 3c0000 events are accepted in the plain or in the pair form (all events of a segment); a mixed segment would be reported as a port mismatch.'])
    (out / 'verification.json').write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n')
    (out / 'frontier.json').write_text(json.dumps(fr, indent=1, sort_keys=True, default=str) + '\n')
    import platform as _p
    (out / 'run_info.json').write_text(json.dumps(dict(elapsed_seconds=round(time.time() - t0, 1), python=sys.version.split()[0], os=_p.platform(), workers=args.workers,
                                                       observation_pin=pin_name,
                                                       harness_calls_note='per-process counters are not kept', argv=sys.argv[1:]), indent=1, sort_keys=True) + '\n')
    print(json.dumps(dict(observation_pin=pin_name, summary=summary['totals'], acceptance=accept, report_sha256=file_sha(out / 'verification.json'), frontier_sha256=file_sha(out / 'frontier.json')),
                     indent=1, sort_keys=True, default=str))
    return 0 if all(v is True for k, v in accept.items() if isinstance(v, bool)) else 1


def machine_sources():
    line = [l for l in (ROOT / 'Makefile').read_text().splitlines() if l.startswith('ANIMATION_MACHINE_SOURCES =')][0]
    return [ROOT / s for s in line.split('=', 1)[1].split()] + [ROOT / 'engine/src/physical_rom_resource.cpp']


def slim(r):
    r = dict(r)
    r.pop('native_new_unrouted', None)
    r.pop('seconds', None)
    return r


def summarize(rows):
    per = collections.OrderedDict()
    tot = collections.Counter()
    for r in rows:
        if 'verifier_error' in r:
            tot['verifier_errors'] += 1
            continue
        c = per.setdefault(r['config'], collections.Counter())
        c['runs'] += 1
        for k in ('compared', 'matched', 'mismatched', 'unrouted', 'cpp_errors', 'beyond_matched', 'beyond_unrouted', 'beyond_mismatched'):
            c[k] += r[k]
        c['native_frames'] += r['native_frames']
        ff = r.get('first_failure')
        if ff is None:
            c['complete_runs'] += 1
        else:
            c['first_failure_' + ff['kind']] += 1
        if r.get('frontier') and r['frontier'].get('confirmed'):
            c['frontier_confirmed'] += 1
        elif r.get('frontier'):
            c['frontier_unconfirmed'] += 1
        gc = r.get('guard_check')
        if gc:
            c['guard_ok' if gc['ok'] else 'guard_not_ok'] += 1
        c['chain_matched_frames'] += r['chain']['matched_frames']
        c['chain_divergences'] += r['chain']['divergence_count']
        c['chain_real_calls'] += r['chain']['real_calls']
        nf = r.get('native_first_unrouted_frame')
        fr = r.get('frontier')
        if fr and nf is not None and fr['frame'] != nf:
            c['frontier_frame_differs_from_native_first_unrouted'] += 1
    for k, v in per.items():
        tot.update({kk: vv for kk, vv in v.items() if kk in ('runs', 'compared', 'matched', 'mismatched', 'unrouted', 'cpp_errors', 'beyond_matched', 'beyond_unrouted',
                                                              'beyond_mismatched', 'chain_matched_frames', 'chain_divergences')})
    return dict(totals=dict(tot), per_config=dict((k, dict(v)) for k, v in per.items()))


def acceptance(rows, neg, summary, full):
    good = [r for r in rows if 'verifier_error' not in r]
    t = summary['totals']
    unconf = [r for r in good if r.get('frontier') and not r['frontier'].get('confirmed')]
    bad_first = [r for r in good if r.get('first_failure') and r['first_failure']['kind'] not in ('unrouted', 'guard-ok', 'guard-behind-frontier')]
    guard_bad = [r for r in good if r.get('guard_check') and not r['guard_check']['ok'] and not (r['guard_check'].get('behind_frontier') and r.get('frontier') and r['frontier'].get('confirmed'))]
    return dict(no_verifier_errors=len(good) == len(rows), zero_mismatches=t.get('mismatched', 0) == 0 and t.get('beyond_mismatched', 0) == 0,
                no_unexpected_cpp_errors=t.get('cpp_errors', 0) == 0, frontiers_confirmed=not unconf, no_other_first_failures=not bad_first,
                guards_match_or_behind_frontier=not guard_bad, chain_no_divergence=t.get('chain_divergences', 0) == 0,
                negatives_ok=bool(neg and neg['ok']) if neg is not None else None, full_run=full)


if __name__ == '__main__':
    sys.exit(main())
