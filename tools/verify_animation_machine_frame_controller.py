"""D9 frame driver acceptance, controller Execute mode: C++ step_animation_machine_frame with AnimationFrameOptions.controller_mode = Execute versus native Unicorn
execution of the original ROM in which the controller LONG (1008e4) is EXECUTED (no declared skip, no declared controller state: D9 configuration (iii)).

Native reference: the D1 verifier's FH HeadRun subclass (tools/verify_animation_machine_frame_driver.py make_verify_class, imported, not edited; same declared
platform rebase of the stage_entry_body seeds, same routing text, base configuration, card answer) extended by a controller phase C: after the H stop at the
controller entry, the controller runs natively from PC = LONG (1008e4) until the dispatcher return 2ac2 is fetched with A7 = SPd.  Inside C the same declared
releases as the C++ driver apply (vblank ef2, sprite flush 16bd0, sound 3aea, sprite queue cda4, gate); the BIOS card fetch c00468 with return c37c / c316 is
the declared card resume (answer R.DEFAULT_ANSWER); a fetch of c00444 is the controller system return (native C stop 'system-return'); any other BIOS fetch is a
native stop.  After C, the observer's own controller skip (PC := 2ac2, A7 += 4) is fed A7 = SPd - 4 so that N starts from the executed controller state.

Per seed and frame:
  frame 0  native N0                          vs C++ run_animation_machine_pass (mode 0);
  frame k  native H_k + C_k + N_k             vs C++ step_animation_machine_frame Execute (mode 1) from the native H start, plus localisation:
           mode 3 (controller segment alone, AnimationFrameController, stop 2ac2) from the native H end vs the native C end, and mode 0 from the native N start.
Compared: RAM 64 KiB, D0-D7/A0-A7, PC, bank base, PVC page, ordered ports per segment (head / controller / node), ordered waits (segment, pc, address, size,
before, released), external reads per segment, head / controller / controller exit / pass stop PCs, carry tag (Unknown).  The C++ external-read queue is
exactly what native consumed (H, then C device reads, then N) and must be fully consumed.
Native non-completions must make C++ fail with a checked error and preserved state (N stops as in D1; C 'system-return' -> 'animation frame controller system
return').  Full pure-C++ chain for every seed (Execute mode, C++ outputs only); determinism: two chain runs for the first natural seeds.
Fixtures: controller c00444 (system return), controller c364 (card request inside C), the c560 wait opened by WORD 107dea := 0 (C3b boundary), all with a native run
using the observer's declared host writes.  Negatives: RAM byte, controller-path RAM byte (107dea), wrong controller PC, Skip mode, queue, result mutations.
"""
import argparse
import collections
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
import verify_animation_machine_frame_driver as D  # noqa: E402  (imported, never edited)

OUT = ROOT / 'artifacts/animation_machine_frame_controller'
BUILD = ROOT / 'build/frame_controller_acceptance'
HARNESS = ROOT / 'engine/tools/frame_controller_acceptance.cpp'
KEYS = D.KEYS
MODE_PASS, MODE_STEP, MODE_CTRL = 0, 1, 3
SEG_C = 2
OPT_EXECUTE, OPT_CREDIT = 0x200, 0x400
CARD_BIOS, CARD_RETS, CARD_BYTE, SYSTEM_RETURN = 0xc00468, (0xc37c, 0xc316), 0x10fdc6, 0xc00444
DISPATCH = 0x2ac2
C_LIMIT = 2000000
C3A_LEADERS = (0xc52a, 0xc530, 0xc55a, 0xc560, 0xc566, 0xc56c, 0x8b64, 0x8b98, 0x8bb6)
CHAIN_SEEDS = 4
NATIVE_END_ERROR = dict(D.NATIVE_END_ERROR)
NATIVE_END_ERROR['C:system-return'] = 'animation frame controller system return'
CTX = {}


# ----------------------------------------------------------------------------------
# Packets (ROM-free)
# ----------------------------------------------------------------------------------
def encode_request(mode, ram, regs, pc, bank_base, pvc, queue, external_status=0, carry=0, card_resume=True, card_answer=0x80, execute=True,
                   credit_resume=False, credit_answer=0x01010000):
    assert len(ram) == 65536 and len(pvc) == 8192
    options = (0x100 if card_resume else 0) | (card_answer & 0xff) | (OPT_EXECUTE if execute else 0) | (OPT_CREDIT if credit_resume else 0)
    values = [mode] + [regs[k] & 0xffffffff for k in KEYS] + [pc, carry, bank_base, external_status, options, credit_answer & 0xffffffff, len(queue)]
    return struct.pack('>24I', *values) + bytes(ram) + bytes(pvc) + b''.join(struct.pack('>III', *e) for e in queue)


def parse_response(payload):
    if len(payload) < 8:
        raise ValueError('short harness packet')
    ok = struct.unpack_from('>I', payload)[0]
    if ok == 0:
        return dict(ok=False, preserved=struct.unpack_from('>I', payload, 4)[0] == 1, error=payload[8:].decode('latin-1'))
    n0 = 32
    if ok != 1 or len(payload) < 4 * n0 + 65536 + 8192:
        raise ValueError('invalid harness packet')
    v = struct.unpack_from('>%dI' % n0, payload)
    pc, carry, bank, head_pc, ctrl_pc, stop_pc, exit_pc, hreads, nreads, creads, nh, nn, nc, nw, nr = v[1:16]
    regs = dict(zip(KEYS, v[16:32]))
    at = 4 * n0
    if len(payload) != at + 65536 + 8192 + 12 * (nh + nn + nc + nr) + 24 * nw:
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
    head_ports, node_ports, ctrl_ports = triples(nh), triples(nn), triples(nc)
    waits = [struct.unpack_from('>6I', payload, at + 24 * i) for i in range(nw)]
    at += 24 * nw
    remaining = triples(nr)
    return dict(ok=True, pc=pc, carry=carry, bank_base=bank, head_pc=head_pc, controller_pc=ctrl_pc, pass_stop_pc=stop_pc, controller_exit_pc=exit_pc,
                head_reads=hreads, node_reads=nreads, controller_reads=creads, regs=regs, ram=ram, pvc=pvc, head_ports=head_ports, node_ports=node_ports,
                controller_ports=ctrl_ports, waits=waits, remaining=remaining)


def compare(got, exp):
    """D1 comparison plus the controller fields (exit PC, reads, ordered controller ports)."""
    bad = D.compare(got, exp)
    if not got['ok']:
        return bad
    for k in ('controller_exit_pc', 'controller_reads'):
        if got[k] != exp.get(k, 0):
            bad.append(dict(field=k, cpp=got[k], native=exp.get(k, 0)))
    conv, _ = D.cpp_ports_native_form(got['controller_ports'], exp.get('controller_ports', []))
    if conv != exp.get('controller_ports', []):
        e = exp.get('controller_ports', [])
        i = D.first_diff(conv, e)
        bad.append(dict(field='controller_ports', index=i, cpp_len=len(conv), native_len=len(e)))
    return bad


def check_expected_failure(got, label, native_kind):
    if got['ok']:
        return dict(check=label, ok=False, native_kind=native_kind, why='C++ completed where native did not complete the frame')
    expected = NATIVE_END_ERROR.get(native_kind)
    ok = bool(got['preserved']) and expected is not None and got['error'] == expected
    r = dict(check=label, ok=ok, native_kind=native_kind, expected_error=expected, error=got['error'], preserved=got['preserved'])
    if not ok:
        r['why'] = 'native stop kind without a declared C++ error' if expected is None else 'C++ error or preservation differs'
    return r


class Harness(D.Harness):
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


def request_for(mode, st, queue, **kw):
    kw.setdefault('card_answer', CTX.get('answer', 0x80))
    return encode_request(mode, st['ram'], st['regs'], st['pc'], st['bank'][0], st['pvc'], queue, st['status'], **kw)


# ----------------------------------------------------------------------------------
# Native: D1 VerifyRun + executed controller phase C
# ----------------------------------------------------------------------------------
def make_controller_class():
    FH, S = D.FH, D.S
    UC_REG = S.UC_REG
    Verify = D.make_verify_class()

    class ControllerRun(Verify):
        def build(self, snap):
            mach = Verify.build(self, snap)
            mach.cpu.hook_add(FH.UC_HOOK_CODE, self.c_ret, begin=DISPATCH, end=DISPATCH)
            for pc in C3A_LEADERS:
                mach.cpu.hook_add(FH.UC_HOOK_CODE, self.c_lead, begin=pc, end=pc)
            self.start_override = None
            return mach

        # the D1 head-only waits also apply inside the controller (the C++ driver releases them in every segment)
        def h_vbl(self, uc, pc, size, user):
            if self.phase == 'C':
                self.phase = 'H'
                try:
                    return FH.HeadRun.h_vbl(self, uc, pc, size, user)
                finally:
                    self.phase = 'C'
            return FH.HeadRun.h_vbl(self, uc, pc, size, user)

        def h_sprflush(self, uc, pc, size, user):
            if self.phase == 'C':
                self.phase = 'H'
                try:
                    return FH.HeadRun.h_sprflush(self, uc, pc, size, user)
                finally:
                    self.phase = 'C'
            return FH.HeadRun.h_sprflush(self, uc, pc, size, user)

        def c_ret(self, uc, pc, size, user):
            if self.phase == 'C' and uc.reg_read(UC_REG['a7']) == S.SPD:
                self.c_done = True
                uc.emu_stop()

        def c_lead(self, uc, pc, size, user):
            if self.phase == 'C':
                self.c_path.append(pc)

        def apply_host_writes(self, frame):
            out = FH.HeadRun.apply_host_writes(self, frame)
            if out:
                self.start_override = self.capture()     # the C++ request starts from the state with the declared host writes applied
            return out

        def run_head(self, frame):
            self.start_override = None
            out = Verify.run_head(self, frame)
            if self.start_override is not None and getattr(self, 'fr', None) is not None and self.fr.get('frame') == frame:
                self.fr['start'] = self.start_override
            reason = out[0]
            if reason['reason'] != 'controller':
                return out
            res, crec = self.run_controller()
            self.fr['c'] = crec
            if res['reason'] != 'returned':
                self.fr['n'] = None
                self.on_frame(self.fr)
                return (dict(reason='C:' + res['reason'], **{k: v for k, v in res.items() if k != 'reason'}),) + tuple(out[1:])
            self.m.cpu.reg_write(UC_REG['a7'], S.SPD - 4)     # the observer's skip (PC := 2ac2, A7 += 4) then hands the executed state to N
            return out

        def run_controller(self):
            mach = self.m
            c = mach.cpu
            self.phase = 'C'
            self.c_done = False
            self.c_path = []
            self.devlog = []
            start = self.capture()
            ports0 = len(mach.ports)
            waits = []
            res = None
            while True:
                mach.fetch_unmapped = None
                mach.odd = None
                mach.invalid = None
                mach.intr = None
                self.waiting = None
                self.stop = None
                err = None
                try:
                    c.emu_start(mach.pc(), 0xffffff, count=C_LIMIT)
                except FH.unicorn.UcError as e:
                    err = str(e)
                if self.waiting is not None and self.stop is None:
                    w = self.waiting
                    self.waiting = None
                    before = None
                    changes = self.release_wait(w)
                    if changes:
                        a, n, v = changes[0]
                        waits.append((SEG_C, w['pc'], a & 0xffffff, n, w['live'], v))
                    if len(waits) > S.WAIT_LIMIT or not changes:
                        res = dict(reason='wait-not-released', pc=w['pc'])
                        break
                    continue
                if mach.fetch_unmapped is not None:
                    a = mach.fetch_unmapped
                    a7 = mach.regs()['a7']
                    ret = mach.long(a7)
                    if a == CARD_BIOS and ret in CARD_RETS and mach.pc() == CARD_BIOS:
                        before = mach.byte(CARD_BYTE)
                        c.reg_write(UC_REG['pc'], ret)
                        c.reg_write(UC_REG['a7'], (a7 + 4) & 0xffffffff)
                        mach.put(CARD_BYTE, 1, self.answer)
                        waits.append((SEG_C, CARD_BIOS, CARD_BYTE, 1, before, self.answer))
                        if len(waits) > S.WAIT_LIMIT:
                            res = dict(reason='wait-not-released', pc=a)
                            break
                        continue
                    res = dict(reason='system-return' if a == SYSTEM_RETURN else 'bios-boundary', address=a, ret=ret)
                    break
                if self.c_done:
                    res = dict(reason='returned')
                    break
                if self.stop is not None:
                    res = dict(reason='stop', detail=self.stop)
                    self.stop = None
                    break
                if mach.odd:
                    res = dict(reason='odd', **mach.odd)
                    break
                if mach.invalid:
                    res = dict(reason='invalid', **mach.invalid)
                    break
                res = dict(reason='other', err=err, pc=mach.pc())
                break
            self.phase = 'H'
            end = self.capture()
            crec = dict(reason=res, start=start, end=end, ports=list(mach.ports[ports0:]), waits=waits, dev=[d for d in self.devlog if d[0] == 'C'],
                        path=list(self.c_path), exit_cb=mach.long(S.CONTROLLER), entry=start['pc'])
            self.devlog = []
            return res, crec
    return ControllerRun


# ----------------------------------------------------------------------------------
# Expectations
# ----------------------------------------------------------------------------------
def c_expectation(crec):
    q, status, other = D.n_queue(crec['dev'])
    end = crec['end']
    exp = dict(ram=end['ram'], regs=end['regs'], pc=end['pc'], bank_base=end['bank'][0], pvc=end['pvc'], head_pc=0, controller_pc=0, pass_stop_pc=0,
               controller_exit_pc=crec['exit_cb'], head_reads=0, node_reads=0, controller_reads=len(q) + status, head_ports=[], node_ports=[],
               controller_ports=[tuple(p) for p in crec['ports']], waits=list(crec['waits']))
    return exp, q, other


def frame_expectation(fr):
    """-> (category, expectations).  D1 H/N expectations plus the controller segment."""
    if fr['frame'] > 0 and fr['h']['reason']['reason'] != 'controller':
        return 'native-H-stop:' + fr['h']['reason']['reason'], None
    if fr['frame'] > 0:
        crec = fr['c']
        exp_c, cq, cother = c_expectation(crec)
        if crec['reason']['reason'] != 'returned':
            return 'native-C-stop:' + crec['reason']['reason'], dict(exp_c=exp_c, cq=cq, h_queue=list(fr['h']['ext']))
    cat, ex = D.frame_expectation(fr)
    if fr['frame'] == 0:
        return cat, ex
    if cother and cat == 'complete':
        cat = 'native-undeclared-C-device-read'
    ex['exp_c'] = exp_c
    ex['cq'] = cq
    hwaits = D.native_wait_tuples(fr['h']['rec']['waits'], 0)
    nwaits = D.native_wait_tuples(fr['n']['waits'], 1)
    e = ex['exp_step']
    e['controller_exit_pc'] = exp_c['controller_exit_pc']
    e['controller_reads'] = exp_c['controller_reads']
    e['controller_ports'] = exp_c['controller_ports']
    e['waits'] = hwaits + exp_c['waits'] + nwaits
    return cat, ex


def native_kind(cat, fr):
    if cat.startswith('native-C-stop:'):
        return 'C:' + fr['c']['reason']['reason']
    if cat.startswith('native-N-stop:'):
        return fr['n']['reason']['reason']
    return cat


def compare_frame(harness, fr):
    cat, ex = frame_expectation(fr)
    frame = fr['frame']
    row = dict(frame=frame, category=cat, checks={})
    if fr.get('c') is not None:
        row['c_entry'] = fr['c']['entry']
        row['c_exit'] = fr['c']['exit_cb']
        row['c_path'] = fr['c']['path'][:16]
        row['c_ports'] = len(fr['c']['ports'])
        row['c_waits'] = len(fr['c']['waits'])
    if ex is None:                                             # native H stop
        got = harness.call(request_for(MODE_STEP, fr['start'], list(fr['h']['ext'])))
        kind = 'H:' + fr['h']['reason']['reason']
        row['checks']['step'] = check_expected_failure(got, 'step', kind)
        row['match'] = False
        return row, dict(fail=True, kind=kind, queue=list(fr['h']['ext']))
    if cat.startswith('native-C-stop:'):
        kind = native_kind(cat, fr)
        queue = ex['h_queue'] + ex['cq']
        got = harness.call(request_for(MODE_STEP, fr['start'], queue))
        cgot = harness.call(request_for(MODE_CTRL, fr['c']['start'], ex['cq']))
        row['checks']['step'] = check_expected_failure(got, 'step', kind)
        row['checks']['controller'] = check_expected_failure(cgot, 'controller', kind)
        row['native_stop'] = fr['c']['reason']
        row['match'] = False
        return row, dict(fail=True, kind=kind, queue=queue)
    info = ex['info']
    if frame == 0:
        got = harness.call(request_for(MODE_PASS, fr['start'], info['n_queue']))
        if cat == 'complete':
            bad = compare(got, ex['exp_n'])
            row['checks']['pass'] = dict(ok=not bad, mismatch=bad[:4])
            row['match'] = not bad
            e = ex['exp_n']
            return row, dict(queue=info['n_queue'], exp=e, digest=D.state_digest(e['ram'], e['regs'], e['pc'], e['bank_base'], e['pvc']))
        kind = native_kind(cat, fr)
        row['checks']['pass'] = check_expected_failure(got, 'pass', kind)
        row['match'] = False
        return row, dict(fail=True, kind=kind, queue=info['n_queue'])
    queue = info['h_queue'] + ex['cq'] + info['n_queue']
    got = harness.call(request_for(MODE_STEP, fr['start'], queue))
    cgot = harness.call(request_for(MODE_CTRL, fr['c']['start'], ex['cq']))
    ngot = harness.call(request_for(MODE_PASS, fr['n']['start'], info['n_queue']))
    cbad = compare(cgot, ex['exp_c'])
    row['checks']['controller'] = dict(ok=not cbad, mismatch=cbad[:4])
    if cat == 'complete':
        bad = compare(got, ex['exp_step'])
        nbad = compare(ngot, ex['exp_n'])
        row['checks']['step'] = dict(ok=not bad, mismatch=bad[:4])
        row['checks']['pass'] = dict(ok=not nbad, mismatch=nbad[:4])
        row['match'] = not bad and not nbad and not cbad
        e = ex['exp_step']
        return row, dict(queue=queue, exp=e, digest=D.state_digest(e['ram'], e['regs'], e['pc'], e['bank_base'], e['pvc']))
    kind = native_kind(cat, fr)
    row['checks']['step'] = check_expected_failure(got, 'step', kind)
    row['checks']['pass'] = check_expected_failure(ngot, 'pass', kind)
    row['match'] = False
    return row, dict(fail=True, kind=kind, queue=queue)


# ----------------------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------------------
def harness_for_worker():
    h = CTX.get('harness')
    if h is None:
        h = Harness(CTX['exe'], CTX['resources'], OUT / ('harness.%d.stderr' % os.getpid()))
        CTX['harness'] = h
    return h


def chain_step(harness, fr, c, fc):
    if not fc['alive']:
        return
    st = fr['start'] if fr['frame'] == 0 else fc['state']
    if st is None:
        fc['alive'] = False
        return
    fc['frames'] += 1
    got = harness.call(request_for(MODE_PASS if fr['frame'] == 0 else MODE_STEP, st, c['queue']))
    if c.get('fail'):
        r = check_expected_failure(got, 'chain', c['kind'])
        if r['ok']:
            fc['expected_failures'] += 1
        else:
            fc['first_divergence'] = dict(frame=fr['frame'], detail=r)
        fc['alive'] = False
        return
    bad = compare(got, c['exp'])
    if bad:
        fc['first_divergence'] = dict(frame=fr['frame'], mismatch=bad[:4])
        fc['alive'] = False
        return
    fc['matched'] += 1
    fc['state'] = dict(ram=got['ram'], regs=got['regs'], pc=got['pc'], bank=(got['bank_base'],), pvc=got['pvc'], status=st['status'])


def run_chain(harness, seed_start, chain_rows):
    st = dict(seed_start)
    digests = []
    for i, c in enumerate(chain_rows):
        if c is None or c.get('fail'):
            break
        got = harness.call(request_for(MODE_PASS if i == 0 else MODE_STEP, st, c['queue']))
        if not got['ok'] or got['remaining']:
            digests.append('error:' + (got.get('error') or 'queue'))
            break
        digests.append(D.state_digest(got['ram'], got['regs'], got['pc'], got['bank_base'], got['pvc']))
        st = dict(ram=got['ram'], regs=got['regs'], pc=got['pc'], bank=(got['bank_base'],), pvc=got['pvc'], status=st['status'])
    return digests


def make_run(case, frames, on_frame, writes=()):
    FH, R = D.FH, D.R
    sd, snap, meta, rec, carried = FH.prepared(case)
    cfg = dict(FH.BASE_CFG)
    cfg['writes'] = list(writes)
    run = CTX['cls'](R.G['program'], R.G['fixed'], R.G['levels'], {k: v for k, v in carried.items() if k != 'prep_entry_state'}, 'continuous', frames,
                     heavy=False, plan=None, sink=None, extend=False, answer=R.DEFAULT_ANSWER, full_dump=False, prep_dump=None, cfg=cfg, case=case, tbset=None,
                     keep_all=False, do_model=False)
    run.on_frame = on_frame
    return sd, run


def work(arg):
    case, frames, chain = arg
    t0 = time.time()
    harness = harness_for_worker()
    calls0 = harness.calls
    rows, chain_rows, state0 = [], [], {}
    fchain = dict(state=None, alive=True, matched=0, expected_failures=0, first_divergence=None, frames=0)
    paths = collections.Counter()
    leaders = collections.Counter()
    cports = collections.Counter()
    cwaits = collections.Counter()

    def on_frame(fr):
        if fr['frame'] == 0:
            state0.update(fr['start'])
        c = fr.get('c')
        if c is not None:
            paths['%x>%x' % (c['entry'], c['exit_cb'])] += 1
            leaders.update('%x' % p for p in set(c['path']))
            cports.update('%x/%d' % (p[1], p[2]) for p in c['ports'])
            cwaits.update('%x' % w[1] for w in c['waits'])
        try:
            row, ch = compare_frame(harness, fr)
        except Exception as e:                                  # a verifier failure is recorded, never a match
            row, ch = dict(frame=fr['frame'], category='verifier-error', error=repr(e), match=False, checks={}), None
        rows.append(row)
        if ch is not None:
            chain_step(harness, fr, ch, fchain)
            ch.pop('exp', None)
        chain_rows.append(ch)
    sd, run = make_run(case, frames, on_frame)
    run.run()
    out = dict(case=case, kind=sd['kind'], stop=run.stop, frames_done=run.frames_done, rows=rows, controller_paths=dict(paths), controller_leaders=dict(leaders),
               controller_ports=dict(cports), controller_waits=dict(cwaits), skip_bad=run.skip_bad)
    if chain:
        d1 = run_chain(harness, state0, chain_rows)
        d2 = run_chain(harness, state0, chain_rows)
        native = [c['digest'] for c in chain_rows if c is not None and not c.get('fail')]
        k = 0
        for x, y in zip(d1, [c.get('digest') if c else None for c in chain_rows]):
            if x != y:
                break
            k += 1
        out['chain'] = dict(frames=len(d1), deterministic=d1 == d2, digest=D.sha(json.dumps(d1).encode()), equal_native_prefix=k, native_complete_frames=len(native))
    fchain.pop('state', None)
    out['full_chain'] = fchain
    out['harness_calls'] = harness.calls - calls0
    out['seconds'] = time.time() - t0
    return out


# ----------------------------------------------------------------------------------
# Fixtures and negatives (one natural seed)
# ----------------------------------------------------------------------------------
def capture_frames(case, frames, keep, writes=()):
    got = {}

    def on_frame(fr):
        if fr['frame'] in keep:
            got[fr['frame']] = fr
    sd, run = make_run(case, frames, on_frame, writes)
    run.run()
    return got, run


def fixtures(case):
    harness = harness_for_worker()
    tests = {}
    base, _ = capture_frames(case, 3, (1, 2))
    f1, f2 = base[1], base[2]
    # 1. controller LONG := c00444 (frame 1): native C fetches c00444 (system return); C++ fails, checked and preserving.
    w = [(1, 1, 0x1008e4, 4, SYSTEM_RETURN, 'set')]
    nat, run = capture_frames(case, 2, (1,), w)
    fr = nat.get(1)
    cat, ex = frame_expectation(fr) if fr else ('missing', None)
    got = harness.call(request_for(MODE_STEP, fr['start'], list(fr['h']['ext'])))
    r = check_expected_failure(got, 'step', 'C:system-return')
    # Native: the transferring JSR (A0) at 2ac0 itself fetches c00444 (the FH H classifies it as a BIOS boundary at c00444) or C fetches it.
    hreason = fr['h']['reason']
    native_ok = cat == 'native-C-stop:system-return' or (cat == 'native-H-stop:bios-boundary' and hreason.get('address') == SYSTEM_RETURN)
    tests['controller-c00444-system-return'] = dict(ok=native_ok and r['ok'] and fr['start']['ram'][0x08e4:0x08e8] == bytes.fromhex('00c00444'),
                                                     native_category=cat, native_reason=hreason, cpp=r)
    # 2. controller LONG := c364 (frame 1): the BIOS card request inside C (declared card resume, answer 80), then RTS to 2ac2.
    w = [(1, 1, 0x1008e4, 4, 0xc364, 'set')]
    nat, run = capture_frames(case, 2, (1,), w)
    fr = nat.get(1)
    cat, ex = frame_expectation(fr)
    ok = cat == 'complete'
    detail = dict(native_category=cat)
    if ok:
        queue = ex['info']['h_queue'] + ex['cq'] + ex['info']['n_queue']
        got = harness.call(request_for(MODE_STEP, fr['start'], queue))
        bad = compare(got, ex['exp_step'])
        cw = [list(x) for x in ex['exp_c']['waits']]
        off = harness.call(request_for(MODE_STEP, fr['start'], queue, card_resume=False))
        detail.update(match=not bad, mismatch=bad[:3], controller_waits=cw, controller_exit=ex['exp_c']['controller_exit_pc'],
                      card_resume_off=dict(error=off.get('error'), preserved=off.get('preserved')))
        ok = not bad and len(cw) == 1 and cw[0][:4] == [SEG_C, CARD_BIOS, CARD_BYTE, 1] and not off['ok'] and off['preserved'] and \
            off['error'] == 'unsupported animation machine PC'
    tests['controller-c364-card'] = dict(ok=ok, **detail)
    # 3. the c560 wait opened (frame 2, WORD 107dea := 0): native C continues into C3b (c56e ..); C++ stops at the unrouted c56e (checked, preserved).
    w = [(2, 2, 0x107dea, 2, 0, 'set')]
    nat, run = capture_frames(case, 3, (2,), w)
    fr = nat.get(2)
    cat, ex = frame_expectation(fr) if fr else ('missing', None)
    queue = list(fr['h']['ext']) + (ex['cq'] if ex else []) + (ex['info']['n_queue'] if ex and 'info' in ex else [])
    got = harness.call(request_for(MODE_STEP, fr['start'], queue))
    tests['controller-c560-open-c3b-boundary'] = dict(ok=(not got['ok']) and got['preserved'] and got['error'] == 'unsupported animation machine PC' and
                                                      fr['c']['entry'] == 0xc560 and 0xc56e not in C3A_LEADERS,
                                                      native_category=cat, native_c=fr['c']['reason'], native_path=['%x' % p for p in fr['c']['path']],
                                                      cpp_error=got.get('error'), preserved=got.get('preserved'))
    # natural frames 1 (c52a) and 2 (c560): controller path and ports
    c1, e1 = frame_expectation(f1)
    c2, e2 = frame_expectation(f2)
    tests['natural-frame1-c52a'] = dict(ok=c1 == 'complete' and f1['c']['entry'] == 0xc52a and f1['c']['exit_cb'] == 0xc560 and len(f1['c']['ports']) == 4 and
                                        sorted(set(f1['c']['path'])) == sorted(C3A_LEADERS), path=['%x' % p for p in f1['c']['path']], ports=len(f1['c']['ports']))
    tests['natural-frame2-c560'] = dict(ok=c2 == 'complete' and f2['c']['entry'] == 0xc560 and f2['c']['exit_cb'] == 0xc560 and not f2['c']['ports'],
                                        path=['%x' % p for p in f2['c']['path']])
    return dict(case=case, ok=all(t['ok'] for t in tests.values()), tests=tests), (f1, e1, f2, e2)


def negatives(case):
    harness = harness_for_worker()
    res, (f1, e1, f2, e2) = fixtures(case)
    tests = {}
    q2 = e2['info']['h_queue'] + e2['cq'] + e2['info']['n_queue']
    exp = e2['exp_step']
    base = harness.call(request_for(MODE_STEP, f2['start'], q2))
    tests['baseline-equal'] = dict(detected=not compare(base, exp))

    def detected(st, q, label, **kw):
        got = harness.call(request_for(MODE_STEP, st, q, **kw))
        bad = compare(got, exp)
        tests[label] = dict(detected=bool(bad), first=bad[0] if bad else None)

    def flip(st, address, mask=1):
        ram = bytearray(st['ram'])
        ram[address & 0xffff] ^= mask
        return dict(st, ram=bytes(ram))
    detected(flip(f2['start'], 0x100100), q2, 'ram-byte-flipped')
    detected(flip(f2['start'], 0x107deb), q2, 'controller-path-ram-byte-107dea')     # WORD 107dea 2000 -> 2001: D0 of c560
    wrong = bytearray(f2['start']['ram'])
    wrong[0x08e4:0x08e8] = bytes.fromhex('0000c52a')                                  # controller LONG c560 -> c52a (boot fill runs again)
    detected(dict(f2['start'], ram=bytes(wrong)), q2, 'wrong-controller-pc-c52a')
    detected(f2['start'], q2, 'skip-mode', execute=False)
    detected(f2['start'], q2[:-1], 'queue-short')
    q1 = e1['info']['h_queue'] + e1['cq'] + e1['info']['n_queue']
    b1 = harness.call(request_for(MODE_STEP, f1['start'], q1))
    tests['frame1-baseline-equal'] = dict(detected=not compare(b1, e1['exp_step']))
    for label, mutate in (('result-controller-port-dropped', lambda g: g['controller_ports'].pop()),
                          ('result-controller-port-value', lambda g: g['controller_ports'].__setitem__(0, (g['controller_ports'][0][0], 2, g['controller_ports'][0][2] ^ 1))),
                          ('result-controller-exit-pc', lambda g: g.update(controller_exit_pc=g['controller_exit_pc'] ^ 2)),
                          ('result-controller-reads', lambda g: g.update(controller_reads=g['controller_reads'] + 1)),
                          ('result-ram', lambda g: g.update(ram=bytes([g['ram'][0] ^ 1]) + g['ram'][1:])),
                          ('result-reg', lambda g: g['regs'].update(d0=g['regs']['d0'] ^ 1))):
        g = dict(b1, regs=dict(b1['regs']), controller_ports=list(b1['controller_ports']))
        mutate(g)
        tests[label] = dict(detected=bool(compare(g, e1['exp_step'])))
    broken = subprocess.run([str(CTX['exe'])] + [str(p) for p in CTX['resources']], input=struct.pack('>I', 11) + b'bad request', stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    tests['malformed-request-nonzero-exit'] = dict(detected=broken.returncode != 0)
    ok = tests['baseline-equal']['detected'] and tests['frame1-baseline-equal']['detected'] and \
        all(v['detected'] for k, v in tests.items() if not k.endswith('baseline-equal'))
    return dict(case=case, ok=ok, tests=tests, fixtures=res)


# ----------------------------------------------------------------------------------
# Build and main
# ----------------------------------------------------------------------------------
def build(jobs):
    compiler = Path(shutil.which('clang++'))
    flags = ['-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(ROOT / 'engine/include')]
    objdir = BUILD / 'obj'
    if objdir.exists():
        shutil.rmtree(objdir)
    objdir.mkdir(parents=True)
    srcs = D.machine_sources()
    log = open(OUT / 'build.stderr', 'wb')
    procs, objs = [], []
    for s in srcs:
        o = objdir / (s.stem + '.o')
        objs.append(o)
        while len([p for p in procs if p.poll() is None]) >= jobs:
            time.sleep(0.05)
        procs.append(subprocess.Popen([str(compiler)] + flags + ['-c', str(s), '-o', str(o)], stdout=subprocess.DEVNULL, stderr=log))
    for p in procs:
        assert p.wait() == 0, 'compile failed (see build.stderr)'
    exe = BUILD / 'frame_controller_acceptance'
    subprocess.run([str(compiler)] + flags + [str(o) for o in objs] + [str(HARNESS), '-o', str(exe)], check=True, stdout=subprocess.DEVNULL, stderr=log)
    log.close()
    return exe, compiler, srcs


def aggregate(results):
    tot = collections.Counter()
    cats = collections.Counter()
    errs = collections.Counter()
    paths, leaders, cports, cwaits = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    per_seed = []
    for r in results:
        rows = r['rows']
        comp = [x for x in rows if x['category'] == 'complete']
        nonc = [x for x in rows if x['category'] != 'complete']
        bad_fail = [x for x in nonc if not all(c.get('ok') for c in x['checks'].values())]
        for x in rows:
            cats[x['category']] += 1
            for c in x['checks'].values():
                if c.get('error'):
                    errs['%s|%s|%s' % (x['category'], c['check'], c['error'])] += 1
        first = next((x for x in comp if not x['match']), None)
        fc = r['full_chain']
        seed = dict(case=r['case'], kind=r['kind'], native_stop=r['stop'], frames=len(rows), complete=len(comp), matches=sum(1 for x in comp if x['match']),
                    non_completions=[dict(frame=x['frame'], category=x['category'], checks=x['checks']) for x in nonc][:3], expected_failure_bad=len(bad_fail),
                    first_mismatch=first, full_chain=fc, chain=r.get('chain'), seconds=round(r['seconds'], 1))
        per_seed.append(seed)
        key = 'natural_' if r['kind'] == 'natural' else ''
        for k in ({'natural_', ''} if key else {''}):
            tot[k + 'frames'] += len(rows)
            tot[k + 'complete_frames'] += len(comp)
            tot[k + 'matches'] += seed['matches']
            tot[k + 'mismatches'] += len(comp) - seed['matches']
            tot[k + 'non_completions'] += len(nonc)
            tot[k + 'expected_failure_not_ok'] += len(bad_fail)
        if r['kind'] == 'natural':
            tot['natural_seeds'] += 1
            tot['natural_complete_400'] += int(r['stop']['reason'] == 'frame-limit' and r['frames_done'] == 400)
            tot['natural_chain_frames_matched'] += fc['matched']
            tot['natural_chain_expected_failures'] += fc['expected_failures']
            tot['natural_chain_divergent_seeds'] += int(fc['first_divergence'] is not None)
            whole = fc['first_divergence'] is None and fc['matched'] + fc['expected_failures'] == len(rows)
            tot['natural_chain_seeds_to_frame_limit'] += int(whole and fc['expected_failures'] == 0 and r['stop']['reason'] == 'frame-limit')
            tot['natural_chain_seeds_to_native_stop'] += int(whole and fc['expected_failures'] == 1 and r['stop']['reason'] != 'frame-limit')
            tot['natural_skip_bad'] += r['skip_bad']
            paths.update(r['controller_paths'])
            leaders.update(r['controller_leaders'])
            cports.update(r['controller_ports'])
            cwaits.update(r['controller_waits'])
        tot['controller_segment_checks_ok'] += sum(1 for x in comp if x['checks'].get('controller', {}).get('ok'))
    return dict(totals=dict(tot), categories=dict(cats), cpp_errors_on_non_completions=dict(errs), natural_controller_paths=dict(paths),
                natural_controller_leader_frames=dict(leaders), natural_controller_port_kinds=dict(cports), natural_controller_waits=dict(cwaits),
                stop_categories=dict(collections.Counter(r['stop']['reason'] for r in results)), per_seed=per_seed)


def main(argv=None):
    global OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', help='comma list (default: all seeds)')
    ap.add_argument('--frames', type=int, default=400)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args(argv)
    assert not sys.flags.optimize
    OUT = Path(args.out).absolute()
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob('harness.*.stderr'):
        p.unlink()
    report_path = OUT / 'verification.json'
    if report_path.exists():
        report_path.unlink()
    rebase, routing_info, pins = D.setup_native()
    import verify_animation_machine as common
    program = D.R.G['program']
    rom_sha = D.sha(program)
    assert rom_sha == D.S.ROM_SHA
    resources, resource_refs = common.resource_audit(ROOT, program)
    exe = BUILD / 'frame_controller_acceptance'
    if args.no_build and exe.exists():
        compiler, srcs = Path(shutil.which('clang++')), D.machine_sources()
    else:
        exe, compiler, srcs = build(args.workers)
    CTX.update(exe=exe, resources=resources, cls=make_controller_class(), answer=D.R.DEFAULT_ANSWER)
    import unicorn
    tool_files = [TOOLS / n for n in ('verify_animation_machine_frame_controller.py', 'verify_animation_machine_frame_driver.py', 'observe_animation_machine_frame_head.py',
                                      'observe_animation_machine_scheduler_rng.py', 'observe_animation_machine_scheduler.py', 'observe_animation_machine_pvc_banks.py')]
    headers = sorted(set((ROOT / 'engine/include').rglob('*.h')) | set((ROOT / 'engine/src').rglob('*.h')))
    inputs = dict(rom=dict(sha256=rom_sha), seed_observation=dict(path=str(D.S.SEED_OBS.relative_to(ROOT)), sha256=D.file_sha(D.S.SEED_OBS)),
                  program_rom_resources=resource_refs, engine_sources={str(p.relative_to(ROOT)): D.file_sha(p) for p in srcs},
                  engine_headers={str(p.relative_to(ROOT)): D.file_sha(p) for p in headers}, harness={str(HARNESS.relative_to(ROOT)): D.file_sha(HARNESS)},
                  harness_binary_sha256=D.file_sha(exe), tools={str(p.relative_to(ROOT)): D.file_sha(p) for p in tool_files},
                  unicorn=unicorn.__version__, compiler=subprocess.run([str(compiler), '--version'], stdout=subprocess.PIPE, text=True).stdout.splitlines()[0],
                  python=sys.version.split()[0], routing=routing_info)
    cases = sorted(D.S.SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    naturals = [c for c in cases if D.S.SEEDS[c]['kind'] == 'natural']
    chain_cases = set(naturals[:CHAIN_SEEDS])
    ctx = multiprocessing.get_context('fork')
    results = []
    with ctx.Pool(args.workers) as pool:
        neg_async = pool.apply_async(negatives, (naturals[0],)) if naturals and args.frames >= 3 else None
        for r in pool.imap_unordered(work, [(c, args.frames, c in chain_cases) for c in cases], chunksize=1):
            results.append(r)
            nonmatch = sum(1 for x in r['rows'] if x['category'] == 'complete' and not x['match'])
            print('[%6.0fs] case %3d %-13s frames %3d complete-mismatch %d stop %s paths %s' % (time.time() - t0, r['case'], r['kind'], len(r['rows']), nonmatch,
                  r['stop']['reason'], r['controller_paths']), file=sys.stderr, flush=True)
        neg = neg_async.get() if neg_async else None
    results.sort(key=lambda r: r['case'])
    agg = aggregate(results)
    chains = [r['chain'] for r in results if r.get('chain')]
    determinism = dict(seeds=sorted(chain_cases), all_deterministic=all(c['deterministic'] for c in chains), chains=chains)
    report = dict(tool='tools/verify_animation_machine_frame_controller.py', full_run=args.cases is None and args.frames == 400, cases=len(cases),
                  frames_limit=args.frames, declared_platform_rebase=rebase, observer_pins=pins, inputs=inputs, build='clang++ -std=c++11 -O2 -Wall -Wextra -pedantic',
                  negative_checks=neg, determinism=determinism, elapsed_seconds=round(time.time() - t0, 1), protocol=__doc__.strip().splitlines(), **agg,
                  limits=['Native reference: D1 FH HeadRun + executed controller (configuration (iii), no declared controller state); IRQ c8c is not executed, so the '
                          'c560 boot wait never opens naturally.', 'Carry has no SR oracle (Unknown tag only).  Video is ordered ports, not pixels.'])
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n')
    print(json.dumps({k: report[k] for k in ('full_run', 'totals', 'categories', 'natural_controller_paths', 'natural_controller_port_kinds', 'stop_categories',
                                             'elapsed_seconds')}, indent=1, sort_keys=True, default=str))
    print(json.dumps(dict(negative_ok=neg['ok'] if neg else None, fixtures_ok=neg['fixtures']['ok'] if neg else None, deterministic=determinism['all_deterministic'],
                          report_sha256=D.file_sha(report_path)), sort_keys=True))


if __name__ == '__main__':
    main()
