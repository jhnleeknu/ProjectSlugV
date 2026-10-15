"""V1 spec of unit F6c (IRQ sprite writer families A f226..11792 / B 13b46..16092; contract docs/analysis/animation-machine-irq-f6c-contract.md).

Declared native steps: those of the F6a spec (tools/unit_fixture_specs/f6a.py is imported: RTE emulation, Z80 / system / palette pages,
P1 prep, exception frame, BIOS c0044a resume); this module adds none.  Role PCs come from tools/check_animation_irq_f6c_template.py
(the template proof, run against the ROM at import).

Fixtures:
  natural  seeds (natural_cases) x frames: P1 prep, the head advanced natively to the ef2 wait, then the frame's IRQs (two per frame).
           Every writer-table JSR (A3,D7.W) of 16d80 / 16e3c inside an IRQ gives one compared fixture: the native state at the table
           target to the JSR return PC (16d84 / 16e40); everything else in the IRQ (F6a, the F6b 72fa call) runs native-only between
           fixtures.  Natural states only reach family B (BYTE 108d3c bit 7 is 0 in every seed frame and only an IRQ flips it); the
           'flip' variant applies the declared host write 108d3c |= 80 at the IRQ entry (same natural sprite queue, family A).
  typed    from a natural call state of each family (A2 / A4 / A5 / A6 = 3c0000 / A7 with the natural return PC): declared work-RAM
           frames (A3 -> 10b000) entered at the routine's swap7 block with the head's register effects declared (D7.W = word0 - 100,
           D6.W = 4(A4) (A) / 6(A4) (B)), for every routine x height byte 0..31 (every cell-table entry, cell and Duff entry), the clip /
           scale / test / scb3 branches, MULS / MULU edge values (5(A2) = 0 / 2 / 7f / 80 / fe / ff, 4(A2) = 0 / ff, height byte 1 / 55 /
           80 / ff, y = 8000 / 7fff; the MULU rounding boundary product & ff = 01), A6 not the video port, every table slot with natural
           sprite entries (head with the real ROM frames, PVC bank select), the head BCS.W finish (LONG 8(A2) = 8a20ea: a ROM frame whose
           first WORD is below 100, found by a native scan of frame ids), live table landings (index 8 = routine 0 head, index 9 =
           interior), live cell-table / Duff targets (D7.B = 40 / 41), direct entries at every role block.
  errors   interior PCs of both families (table slots, role blocks, cells, Duff), odd PCs, out-of-range computed targets.
  coverage (PYTHONPATH=tools python tools/unit_fixture_specs/f6c.py --coverage; not used by the verifier): every block start and Duff
           entry is executed natively by a 'match' fixture and every conditional block (head, outer, step, test, scale, clip, scb3,
           cell / Duff tail, next) is seen with both successors; natural (unflipped and flipped) fixtures reach A 52/624, B 48/616, Duff 0.
"""
import importlib.util
from pathlib import Path
import struct
import sys

import verify_animation_machine_unit_fixtures as U

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A6S = _load('unit_fixture_spec_f6a', HERE / 'f6a.py')                       # F6a declared native steps (patches PvcMachine once)
T = _load('check_animation_irq_f6c_template', HERE.parent / 'check_animation_irq_f6c_template.py')
ERR = 'unsupported animation irq f6c PC'
SENT = A6S.SENT
FAMILY = {'A': dict(table=0xf226, end=0x11792, ret=0x16d84, fwd=True), 'B': dict(table=0x13b46, end=0x16092, ret=0x16e40, fwd=False)}
for _f, _d in FAMILY.items():
    _rs = T.routines(_d['table']) + [_d['end']]
    _d['roles'] = [T.roles(_rs[k], _rs[k + 1], _d['fwd']) for k in range(8)]
F6C_RANGES = ((0xf226, 0x11792), (0x13b46, 0x16092))
FRAME = 0x10b000          # declared frame data (work RAM)
EMPTY_FRAME = 0x8a20ea    # LONG 8(A2) whose ROM frame starts with a WORD below 100 (head BCS.W finish)
TRACE = [None]            # coverage helper: set of executed F6c PCs
EDGES = set()             # coverage helper: (block start, next block start) pairs
EDGE_STARTS = set()


def in_f6c(pc):
    return any(lo <= pc < hi for lo, hi in F6C_RANGES)


# Coverage hook (only when TRACE is set; never active in the verifier run).
_BASE = A6S.F6aMachine


class F6cTraceMachine(_BASE):
    def install_basic_hooks(self, *a, **k):
        _BASE.install_basic_hooks(self, *a, **k)
        if TRACE[0] is not None:
            import unicorn
            tr = TRACE[0]

            last = [None]

            def code(uc, pc, size, user):
                tr.add(pc)
                if pc in EDGE_STARTS:
                    if last[0] is not None:
                        EDGES.add((last[0], pc))
                    last[0] = pc
            for lo, hi in F6C_RANGES:
                self.cpu.hook_add(unicorn.UC_HOOK_CODE, code, begin=lo, end=hi - 1)


A6S.PB.PvcMachine = F6cTraceMachine
OUT = []


def fx(name, state, queue=(), stop=SENT, expect='match', **kw):
    OUT.append(U.Fixture(name, state, list(queue), stop, expect, **kw))
    return OUT[-1]


def rd(state, address, n):
    return A6S.rd(state, address, n)


# ----------------------------------------------------------------------------------
# Natural IRQs
# ----------------------------------------------------------------------------------
def natural_irq(name, state, z80, video, meta, flip=False):
    """One IRQ at a natural wait state; one fixture per F6c writer call.  -> (native state after the RTE, call states [(family, state, queue)])."""
    wait_pc = state['pc']
    writes = [(0x108d3c, 1, rd(state, 0x108d3c, 1) | 0x80)] if flip else []
    entry = A6S.irq_entry(state, 0x20c, writes=writes)
    q = [(0x320000, 1, z80)]
    A6S.F6aMachine.CALLS = []
    try:
        probe = U.native().run(entry, q, A6S.BIOS_IO)
        calls = list(A6S.F6aMachine.CALLS)
    finally:
        A6S.F6aMachine.CALLS = None
    U.require(probe['ok'], ('natural IRQ probe', name, probe.get('error'), probe.get('detail')))
    cur, found = entry, []
    for i, (target, ret) in enumerate(calls):
        st, q, _ = U.advance_native(cur, q, target)
        if in_f6c(target):
            fam = 'A' if target < 0x11792 else 'B'
            fx('%s-c%d-%x' % (name, i, target), st, q, ret, meta=dict(meta, wait_pc=wait_pc, target=target, family=fam, flip=flip))
            found.append((fam, st, q))
        cur, q, _ = U.advance_native(st, q, ret)
    mid, rest, _ = U.advance_native(cur, q, A6S.BIOS_IO)
    U.require(not rest, ('IRQ queue not consumed', name, rest))
    b = A6S.resume_bios(mid)
    end, rest, _ = U.advance_native(b, [(0x3c0006, 2, video)], wait_pc)
    U.require(not rest, ('IRQ B queue not consumed', name, rest))
    return end, found


def natural_fixtures(cases, frames):
    z80s = (0, 1, 3, 0x7f, 0xff, 0)
    k = 0
    calls = {'A': [], 'B': []}
    for case in cases:
        for fr in U.seed_frames(case, max(frames) + 1):
            h = fr.get('h')
            if fr['frame'] not in frames or h is None or h['reason']['reason'] != 'controller':
                continue
            base = U.seed_state(fr['start'])
            meta = dict(case=case, frame=fr['frame'])
            for flip in (False, True):
                st = U.with_host_writes(base, A6S.p1_writes(base))
                st, _, _ = U.advance_native(st, h['ext'], 0xef2, external_status=fr['start']['status'])
                for i in range(2):
                    U.require(rd(st, 0x100016, 1) < rd(st, 0x100017, 1), ('ef2 not waiting', case, fr['frame'], i))
                    st, found = natural_irq('nat-%s-seed%d-f%d-irq%d' % ('flip' if flip else 'p1', case, fr['frame'], i), st, z80s[k % len(z80s)],
                                            (k & 1) * 8, dict(meta, irq=i), flip=flip and i == 0)
                    k += 1
                    for fam, s, q in found:
                        calls[fam].append((s, q))
    return calls


# ----------------------------------------------------------------------------------
# Typed frames
# ----------------------------------------------------------------------------------
def tiles(n, salt):
    out, x = [], (0x9e37 * (salt + 1)) & 0xffff
    for _ in range(n):
        x = (x * 0x6255 + 0x3619) & 0xffff
        out.append(x)
    return out


def frame_words(strips, salt=0):
    """strips: [(x, y, cols, height_byte)] -> frame words (word0 = strips << 8 | 5a); every column has h = ((height_byte - 1) & 1f) + 1 cells."""
    words = [(len(strips) << 8) | 0x5a]
    for i, (x, y, cols, hb) in enumerate(strips):
        words += [x & 0xffff, y & 0xffff, ((cols & 0xff) << 8) | (hb & 0xff)]
        h = ((hb - 1) & 0x1f) + 1
        words += tiles(2 * h * cols, salt * 64 + i)
    return words


def typed_state(base, fam, k, strips, salt=0, a2=None, box=None, regs=None, extra=()):
    """Call state of family fam -> routine k entered at swap7 with A3 at the declared frame (the head's effects declared)."""
    f = FAMILY[fam]
    R = f['roles'][k]
    words = frame_words(strips, salt)
    ws = [(FRAME + 2 * i, 2, w) for i, w in enumerate(words)]
    a2a = base['regs']['a2']
    for off, size, v in (a2 or ()):
        ws.append(((a2a + off) & 0xffffff, size, v))
    a4 = base['regs']['a4']
    for i, v in enumerate(box or ()):
        if v is not None:
            ws.append(((a4 + 2 * i) & 0xffffff, 2, v & 0xffff))
    ws += list(extra)
    st = U.with_host_writes(base, ws)
    d6 = rd(st, a4 + (4 if f['fwd'] else 6), 2)
    r = dict(a3=FRAME + 2, d7=(base['regs']['d7'] & 0xffff0000) | ((words[0] - 0x100) & 0xffff), d6=(base['regs']['d6'] & 0xffff0000) | d6)
    r.update(regs or {})
    return U.with_host_writes(st, regs=r, pc=R['swap7'])


def box_all(fam):
    """A4 box that draws every column: A start 4(A4) = 1, limit 2(A4) = 17f, draw from 6(A4) = 0; B start 6(A4) = 17f, limit (A4) = 0,
    draw below 4(A4) = 180."""
    return (0, 0x17f, 1, 0) if fam == 'A' else (0, 0, 0x180, 0x17f)


def typed_fixtures(calls):
    for fam in ('A', 'B'):
        base, q = calls[fam][0]
        ret = FAMILY[fam]['ret']
        a2n = [(2, 2, 0x0040), (4, 1, 0x3f), (5, 1, 0x7f), (8, 2, 0x1234)]
        for k in range(8):
            tag = '%s%d' % (fam, k)
            # every height byte 0..31 (cell-table entry, cells, Duff entry (h - 1) & 1f), two columns
            # (H routines negate x: x = ffe0 keeps the first columns inside the clip window)
            hx = 0xffe0 if k & 1 else 0x10
            for hb in range(32):
                a2h = a2n[:2] + [(5, 1, (0x7f + 37 * hb) & 0xff), a2n[3]]
                fx('typed-%s-height%02d' % (tag, hb), typed_state(base, fam, k, [(hx, 0x20, 2, hb)], salt=hb, a2=a2h, box=box_all(fam)), q, ret)
            # multi strip, mixed heights, 3 columns each
            fx('typed-%s-strips' % tag, typed_state(base, fam, k, [(0x08, 0x30, 3, 5), (0x30, 0x10, 3, 0x21), (0x50, 0x7f, 1, 0x1f), (0x3f0, 0x00, 4, 0)],
                                                     salt=99, a2=a2n, box=box_all(fam)), q, ret)
            # clip: x wrap (fc00), crossing 4e00, far right
            for x in (0x3f0, 0x130, 0x13c, 0x200, 0x3e0):
                fx('typed-%s-clip-x%x' % (tag, x), typed_state(base, fam, k, [(x, 0x10, 6, 3)], a2=[(2, 2, 0), (4, 1, 0xff), (5, 1, 0x3f)], box=box_all(fam)), q, ret)
            # scale BMI (S): small 4(A2) gives a negative D4 + D3 for some columns
            for s4 in (0, 1, 0x10, 0x7f, 0xff):
                fx('typed-%s-scale4-%02x' % (tag, s4), typed_state(base, fam, k, [(0x20, 0x18, 7, 2)], a2=[(2, 2, 0x100), (4, 1, s4), (5, 1, 0x40)], box=box_all(fam)), q, ret)
            # MULS / MULU edges: 5(A2), y, height byte
            for s5, y, hb in ((0, 0x10, 3), (0xff, 0x10, 0xff), (0x7f, 0x8000, 0x80), (0xff, 0x7fff, 0xff), (0xff, 0x8000, 0), (0, 0xffff, 0x9f), (0x80, 0x0001, 0x41),
                              (0, 0x10, 1), (0xfe, 0x20, 0xff), (0x02, 0x20, 0x55)):
                fx('typed-%s-mul-%02x-%04x-%02x' % (tag, s5, y, hb), typed_state(base, fam, k, [(0x18, y, 2, hb)], a2=[(2, 2, 0x20), (4, 1, 0x40), (5, 1, s5), (8, 2, 0xabcd)],
                                                                                box=box_all(fam)), q, ret)
            # test / scb3 limits
            if fam == 'A':
                boxes = ((0, 3, 1, 0), (0, 0x17f, 1, 3), (0, 2, 5, 0), (0, 0x8001, 0x7fff, 0), (0, 0x7fff, 0x8000, 0), (0, 0x10, 0x9000, 0), (0, 0x8000, 0, 0x7000))
            else:
                boxes = ((0x7c, 0, 0x180, 0x7f), (0, 0, 0x7d, 0x7f), (5, 0, 0x180, 2), (0x8001, 0, 0x180, 0x7fff), (0x7fff, 0, 0x180, 0x8000), (0, 0, 0x9000, 0x10),
                         (0x8000, 0, 0x7000, 0))
            for i, bx in enumerate(boxes):
                fx('typed-%s-box%d' % (tag, i), typed_state(base, fam, k, [(0x10, 0x20, 5, 4), (0x30, 0x40, 3, 0x1e)], a2=a2n, box=bx), q, ret)
            # A6 not the video port (MOVE.L Dn,(A6) are RAM writes)
            fx('typed-%s-a6-ram' % tag, typed_state(base, fam, k, [(0x10, 0x20, 2, 6)], a2=a2n, box=box_all(fam), regs={'a6': 0x10a100}), q, ret)
            # cols 0 in the first strip / in a later strip (outer BCS finish)
            fx('typed-%s-cols0' % tag, typed_state(base, fam, k, [(0x10, 0x20, 2, 6), (0x10, 0x20, 0, 6)], a2=a2n, box=box_all(fam)), q, ret)
            # live computed targets: column entered with D7.B = 40 (cell 0 start; S: Duff target past the run = interior) / 41 (interior)
            R = FAMILY[fam]['roles'][k]
            st = typed_state(base, fam, k, [(0x10, 0x20, 1, 1)], a2=a2n, box=box_all(fam))
            col = U.with_host_writes(st, regs={'d7': 0x00000040, 'd5': 0x100, 'a3': FRAME + 8}, pc=R['column'])
            if R['duff']:
                fx('error-%s-duff-past-run' % tag, col, q, ret, ('error', ERR))
            else:
                fx('typed-%s-column-d7-40' % tag, col, q, ret)
            fx('error-%s-column-d7-41' % tag, U.with_host_writes(col, regs={'d7': 0x00000041}), q, ret, ('error', ERR))
            # direct entries at the role blocks a natural or typed path reaches only mid-routine (split points)
            for role in ('outer', 'height', 'step', 'advance', 'test', 'scale', 'clip', 'scb3', 'column', 'next', 'finish', 'skip'):
                if R[role]:
                    fx('typed-%s-at-%s' % (tag, role), U.with_host_writes(st, regs={'d7': 0x00000306, 'd5': 0x100}, pc=R[role]), q, ret)
        # every table slot with the natural sprite entries (head: real ROM frames, PVC bank select)
        for i, (s, q2) in enumerate(calls[fam][:6]):
            for k in range(8):
                fx('table-%s-call%d-slot%d' % (fam, i, k), U.with_host_writes(s, pc=FAMILY[fam]['table'] + 4 * k), q2, FAMILY[fam]['ret'])
        # head BCS finish: LONG 8(A2) = 8a20ea selects a ROM frame whose first WORD is below 100 (found by a native scan of frame ids)
        for k in range(8):
            fx('table-%s-empty-slot%d' % (fam, k), U.with_host_writes(base, [((base['regs']['a2'] + 8) & 0xffffff, 4, EMPTY_FRAME)], pc=FAMILY[fam]['table'] + 4 * k),
               q, FAMILY[fam]['ret'])
        # live table landings: index 8 = routine 0 head (runs), index 9 = interior (error)
        fx('land-%s-index8' % fam, U.with_host_writes(base, pc=FAMILY[fam]['table'] + 32), q, ret)
        fx('error-land-%s-index9' % fam, U.with_host_writes(base, pc=FAMILY[fam]['table'] + 36), q, ret, ('error', ERR))


def error_fixtures(calls):
    for fam in ('A', 'B'):
        base, q = calls[fam][0]
        f = FAMILY[fam]
        pcs = [f['table'] + 2, f['table'] + 30]
        for R in f['roles']:
            pcs += [R['head'] + 2, R['outer'] + 2, R['column'] + 2, R['table'] + 2, R['cells'] + 2, R['cells'] + 18 * 31 + 16, R['finish'] + 2]
            if R['duff']:
                pcs += [R['duff'] + 2, R['duff'] + 8 * 31 + 2]
            if not f['fwd']:
                pcs.append(R['step'] - 2)
        for pc in pcs:
            fx('error-interior-%x' % pc, U.with_host_writes(base, pc=pc), q, f['ret'], ('error', ERR))
        fx('error-odd-%x' % (f['table'] + 1), U.with_host_writes(base, pc=f['table'] + 1), q, f['ret'], ('error', 'unaligned animation machine PC'))


def build():
    del OUT[:]
    cases = U.natural_cases(4)
    calls = natural_fixtures(cases, (1, 2, 3))
    U.require(calls['A'] and calls['B'], 'natural writer calls of both families')
    typed_fixtures(calls)
    error_fixtures(calls)
    return list(OUT)


# ----------------------------------------------------------------------------------
# Coverage helper (not used by the verifier): python tools/unit_fixture_specs/f6c.py --coverage
# ----------------------------------------------------------------------------------
def coverage(fixtures):
    import json
    starts = {}
    for fam, f in FAMILY.items():
        s, d = T.starts_of(f['table'], f['roles'])
        starts[fam] = (set(s), set(d))
    TRACE[0] = set()
    for fam, (s, d) in starts.items():
        EDGE_STARTS.update(s | d)
    nat = U.native()
    natural = set()
    for fx_ in fixtures:
        if fx_.expect != 'match':
            continue
        before = set(TRACE[0])
        r = nat.run(fx_.state, fx_.queue, fx_.stop, fx_.releases, fx_.wait_limit, fx_.external_status, fx_.card_answer, fx_.max_insn)
        if not r['ok']:
            print('native failed', fx_.name, r.get('error'), r.get('detail'))
        if fx_.name.startswith('nat-'):
            natural |= TRACE[0] - before
    pcs = TRACE[0]
    out = {}
    for fam, (s, d) in starts.items():
        out[fam] = dict(starts=len(s), reached=len(s & pcs), natural=len(s & natural), duff=len(d), duff_reached=len(d & pcs), duff_natural=len(d & natural),
                        missed=sorted(hex(x) for x in (s | d) - pcs))
    # both outcomes of every conditional block (successor block starts observed in native runs)
    one_sided = []
    for fam, f in FAMILY.items():
        for k, R in enumerate(f['roles']):
            reentry = R['test'] if k & 1 else R['advance']
            tail = (R['duff'] + 8 * 31) if R['duff'] else (R['cells'] + 18 * 31)
            want = {'head': (R['finish'], R['swap7']), 'outer': (R['finish'], R['height']), 'step': (R['next'], reentry),
                    'test': (R['finish'], R['scale'] or R['clip']), 'clip': (R['step'], R['scb3']), 'next': (R['finish'], R['outer']),
                    'scb3': ((R['skip'] if f['fwd'] else R['step']), R['column']), 'tail': (R['next'], reentry)}
            if R['scale']:
                want['scale'] = (R['step'], R['clip'])
            for role, outs in want.items():
                pc = tail if role == 'tail' else R[role]
                seen = set(b for a, b in EDGES if a == pc)
                for o in outs:
                    if o not in seen:
                        one_sided.append('%s%d %s %x -> %x' % (fam, k, role, pc, o))
    out['missing_outcomes'] = one_sided
    print(json.dumps(out, indent=1))


if __name__ == '__main__' and '--coverage' in sys.argv:
    coverage(build())
