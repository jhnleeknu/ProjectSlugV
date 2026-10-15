"""V1 spec of unit F6a (vblank IRQ shell; contract docs/analysis/animation-machine-irq-f6a-contract.md, scope decisions E1-E10).

Declared native steps (this module only; tools/verify_animation_machine_unit_fixtures.py and the observers are not edited):
  * RTE (E3): Unicorn 2.1.4 M68K cannot execute RTE (intr 256 at the RTE PC).  The native machine class used by the verifier
    (observe_animation_machine_pvc_banks.PvcMachine, looked up at call time) is replaced in this process by a subclass whose interrupt
    hook applies the declared RTE at 29a / 2cc / 2d6 only: SR := WORD (A7), PC := LONG (A7+2), A7 += 6, then execution continues.
    Any other interrupt keeps the original behaviour (native error).
  * Devices: the same subclass maps the Z80 page 320000 and the system page 3a0000 (4 KiB each) like 300000 / 3c0000, so the BYTE
    reply read 320000 consumes the declared queue (E7) and the 320000 / 3a0011 / 3a0001 writes are ordered ports.  It also maps
    8 KiB of plain memory at 400000 (palette RAM, no mirror): only the native-only F6b segments (72fa) write it; a compared F6a segment
    that touched it would fail on the C++ side (F6a has no palette access, contract decision 7).  The native SR is 2000 throughout
    (the IRQ mask is not modelled, E2).
  * Boundaries inside a natural IRQ: JSR 72fa (F6b) and the writer-table JSR (A3,D7.W) (F6c) are stops of the compared fixture; the
    native machine then runs the boundary routine alone (native-only, not compared) to its return PC (cc4 / 16d84 / 16e40) and the
    next compared fixture starts there.
  * BIOS (E4): 242 JSR c0044a is a stop (unmapped fetch == stop).  The declared resume (PC := LONG (A7) = 248, A7 += 4) is applied by
    this module between the two fixtures of one IRQ; 21e JMP c00438 is a stop.
  * Seed prep (E5): P1 = BYTE 10fd80 |= 80, LONG 100006 = LONG 10000a = 3dcc, LONG 10081c = 10081c, BYTE 100016 = 0, 100017 = 2,
    100019 = 0, 10001a = 0, 10001b = 0, BYTE 104d91 &= ef (the 3dce / c42 values and the a1e BSET); P2 = the first four writes only.
  * Exception frame (E2): A7 -= 4, LONG (A7) := interrupted PC; A7 -= 2, WORD (A7) := SR 2000; PC := LONG ROM[64] / ROM[68].

Fixtures:
  natural  seeds (natural_cases) x frames 1..3: the H frame-head entry with P1 prep advanced natively to ef2 (the H wait), two IRQs
           per frame (P1 makes the head wait twice): entry 20c -> stop c0044a, declared resume, 248 -> RTE -> stop ef2; the IRQ is
           re-applied on the native result.  P2 prep: one IRQ at the first ef2 arrival.  The native chain is checked for register /
           A7 restore after every IRQ (E3 integrity).
  typed    a natural P1 state (seed 0 frame 1 at ef2) with declared host writes, entered at a block start with the return sentinel
           c00500 (unmapped; stop) pushed, for every branch of the contract fixture plan; raster 29c; the task queue (E9) with
           frames whose PC is 3dcc (-> d2a -> ce6) and a task PC sentinel; sprite flush both directions with clear runs n = 0..380
           and the writer-table boundaries f226 / 13b46 (stop at the table target); every clear-run entry group via 16092 / 166a0;
           direct entries for 16d84 / 16e40 (only reachable after an F6c writer) and a spread of run entries.
  errors   RTE status S = 0 / T = 1, empty queue at 320000 / 3c0006, interior PCs, clear-run target 160aa (n = 381) and 166a2 (D1 = -1).
"""
import struct
import sys

import verify_animation_machine_unit_fixtures as U
import observe_animation_machine_pvc_banks as PB

SENT = 0xc00500           # return sentinel (unmapped): fixtures stop here
SENT2 = 0xc00600          # second sentinel: non-default callbacks / task PCs
BIOS_IO, BIOS_INT1 = 0xc0044a, 0xc00438
RTE_PCS = (0x29a, 0x2cc, 0x2d6)
P2_WRITES = [(0x10000a, 4, 0x3dcc), (0x100006, 4, 0x3dcc), (0x10081c, 4, 0x10081c)]
TRACE = [None]            # set to a dict to record executed F6a PCs (coverage helper)
F6A_RANGES = ((0x20c, 0x2d8), (0x3dcc, 0x3dce), (0xa2c, 0xb0c), (0xbbe, 0xbee), (0xc8c, 0xd56), (0x3cac, 0x3d3a), (0x48156, 0x48180),
              (0x1adf8, 0x1ae56), (0x187d8, 0x18be8), (0x16092, 0x166bc), (0x16cfa, 0x16ea4))


# ----------------------------------------------------------------------------------
# Declared native steps: RTE emulation + Z80 / system pages (see module docstring)
# ----------------------------------------------------------------------------------
_BASE = PB.PvcMachine
if getattr(_BASE, 'F6A_PATCHED', False):
    _BASE = _BASE.__mro__[1]


class F6aMachine(_BASE):
    F6A_PATCHED = True
    CALLS = None          # list -> records the boundary calls (target, return PC) of cbe / 16d80 / 16e3c in execution order

    def __init__(self, *a, **k):
        _BASE.__init__(self, *a, **k)
        import unicorn
        for base, size in ((0x320000, 0x1000), (0x3a0000, 0x1000), (0x400000, 0x2000)):
            self.cpu.mem_map(base, size, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
        self.rte_count = 0

    def install_basic_hooks(self, *a, **k):
        import unicorn
        c, mach = self.cpu, self
        S = PB.S
        orig = c.hook_add

        def wrap(cb):
            def intr(uc, number, user):
                pc = uc.reg_read(S.UC_REG['pc'])
                if number == 256 and pc in RTE_PCS:
                    sp = uc.reg_read(S.UC_REG['a7'])
                    sr = int.from_bytes(bytes(uc.mem_read(sp, 2)), 'big')
                    npc = int.from_bytes(bytes(uc.mem_read(sp + 2, 4)), 'big')
                    uc.reg_write(S.UC_REG['sr'], sr)
                    uc.reg_write(S.UC_REG['a7'], (sp + 6) & 0xffffffff)
                    uc.reg_write(S.UC_REG['pc'], npc)
                    mach.rte_count += 1
                    if TRACE[0] is not None:
                        TRACE[0].setdefault('rte', []).append((pc, sr, npc))
                    return
                cb(uc, number, user)
            return intr

        def hook_add(kind, cb, *x, **y):
            if kind == unicorn.UC_HOOK_INTR:
                cb = wrap(cb)
            return orig(kind, cb, *x, **y)
        c.hook_add = hook_add
        try:
            _BASE.install_basic_hooks(self, *a, **k)
        finally:
            del c.hook_add
        if F6aMachine.CALLS is not None:
            calls = F6aMachine.CALLS

            def call(uc, pc, size, user):
                if pc == 0xcbe:
                    calls.append((0x72fa, 0xcc4))
                else:
                    d7 = uc.reg_read(S.UC_REG['d7']) & 0xffff
                    a3 = uc.reg_read(S.UC_REG['a3'])
                    calls.append(((a3 + (d7 - 0x10000 if d7 & 0x8000 else d7)) & 0xffffffff, pc + 4))
            for pc in (0xcbe, 0x16d80, 0x16e3c):
                c.hook_add(unicorn.UC_HOOK_CODE, call, begin=pc, end=pc)
        if TRACE[0] is not None:
            tr = TRACE[0]

            def code(uc, pc, size, user):
                tr.setdefault('pcs', set()).add(pc)
                if pc in (0x160aa, 0x166b8):
                    d1 = uc.reg_read(S.UC_REG['d1']) & 0xffff
                    tr.setdefault('jumps', set()).add((0x1669e + (d1 - 0x10000 if d1 & 0x8000 else d1)) & 0xffffff)
            for lo, hi in F6A_RANGES:
                c.hook_add(unicorn.UC_HOOK_CODE, code, begin=lo, end=hi - 1)


PB.PvcMachine = F6aMachine


# ----------------------------------------------------------------------------------
# State helpers
# ----------------------------------------------------------------------------------
def rd(state, address, n):
    o = address & 0xffff
    return int.from_bytes(state['ram'][o:o + n], 'big')


def p1_writes(state):
    return P2_WRITES + [(0x100016, 1, 0), (0x100017, 1, 2), (0x100019, 1, 0), (0x10001a, 1, 0), (0x10001b, 1, 0),
                        (0x104d91, 1, rd(state, 0x104d91, 1) & 0xef), (0x10fd80, 1, rd(state, 0x10fd80, 1) | 0x80)]


def p2_writes(state):
    return P2_WRITES + [(0x10fd80, 1, rd(state, 0x10fd80, 1) | 0x80)]


def push(state, values, pc, writes=(), regs=None):
    """Host writes, register overrides, then push LONG/WORD values [(size, value)] in order (first pushed = highest address); PC := pc."""
    st = U.with_host_writes(state, writes, regs)
    a7 = st['regs']['a7']
    ws = []
    for size, v in values:
        a7 = (a7 - size) & 0xffffffff
        ws.append((a7, size, v))
    return U.with_host_writes(st, ws, regs={'a7': a7}, pc=pc)


def irq_entry(state, vector_pc, sr=0x2000, writes=(), regs=None):
    """E2 exception frame (LONG interrupted PC, WORD SR) and PC := vector target."""
    return push(state, [(4, state['pc']), (2, sr)], vector_pc, writes, regs)


def typed_entry(state, pc, writes=(), regs=None, ret=SENT):
    return push(state, [(4, ret)], pc, writes, regs)


def resume_bios(state):
    """E4 declared resume after the c0044a stop: PC := LONG (A7), A7 += 4."""
    a7 = state['regs']['a7']
    ret = rd(state, a7, 4)
    U.require(ret == 0x248, ('BIOS resume return', hex(ret)))
    return U.with_host_writes(state, regs={'a7': a7 + 4}, pc=ret)


# ----------------------------------------------------------------------------------
# Fixture builders
# ----------------------------------------------------------------------------------
OUT = []


def fx(name, state, queue=(), stop=SENT, expect='match', **kw):
    OUT.append(U.Fixture(name, state, list(queue), stop, expect, **kw))
    return OUT[-1]


def natural_irq(name, state, z80, video, meta, check=True):
    """One IRQ at a natural wait-point state: fixtures A0..Ak (20c -> first F6b/F6c boundary, boundary return -> next boundary, ...,
    -> c0044a; every boundary routine runs native-only between two fixtures) and fixture B (248 -> RTE -> interrupted PC).
    -> native state after B."""
    wait_pc = state['pc']
    entry = irq_entry(state, 0x20c)
    qa = [(0x320000, 1, z80)]
    F6aMachine.CALLS = []
    try:
        probe = U.native().run(entry, qa, BIOS_IO)
        calls = list(F6aMachine.CALLS)
    finally:
        F6aMachine.CALLS = None
    U.require(probe['ok'], ('natural IRQ probe', name, probe.get('error'), probe.get('detail')))
    cur, q = entry, qa
    for i, (target, ret) in enumerate(calls):
        fx('%s-a%d' % (name, i), cur, q, target, meta=dict(meta, wait_pc=wait_pc, part='segment', boundary=target))
        cur, q, _ = U.advance_native(cur, q, target)
        cur, q, _ = U.advance_native(cur, q, ret)
    fx('%s-a%d' % (name, len(calls)), cur, q, BIOS_IO, meta=dict(meta, wait_pc=wait_pc, part='segment', boundary=BIOS_IO))
    mid, rest, _ = U.advance_native(cur, q, BIOS_IO)
    U.require(not rest, ('IRQ A queue not consumed', name, rest))
    b = resume_bios(mid)
    qb = [(0x3c0006, 2, video)]
    fx(name + '-b', b, qb, wait_pc, meta=dict(meta, wait_pc=wait_pc, part='248-rte'))
    end, rest, _ = U.advance_native(b, qb, wait_pc)
    U.require(not rest, ('IRQ B queue not consumed', name, rest))
    if check:
        U.require(end['regs'] == state['regs'], ('E3 register restore', name))
    return end


def natural_fixtures(cases, frames):
    z80s = (0, 1, 3, 0x7f, 0xff, 0)
    k = 0
    for case in cases:
        for fr in U.seed_frames(case, max(frames) + 1):
            h = fr.get('h')
            if fr['frame'] not in frames or h is None or h['reason']['reason'] != 'controller':
                continue
            base = U.seed_state(fr['start'])
            meta = dict(case=case, frame=fr['frame'])
            # P1: the head waits at ef2 until 100016 >= 100017 = 2 (two IRQs).
            st = U.with_host_writes(base, p1_writes(base))
            st, _, _ = U.advance_native(st, h['ext'], 0xef2, external_status=fr['start']['status'])
            for i in range(2):
                U.require(rd(st, 0x100016, 1) < rd(st, 0x100017, 1), ('ef2 not waiting', case, fr['frame'], i))
                st = natural_irq('nat-p1-seed%d-f%d-irq%d' % (case, fr['frame'], i), st, z80s[k % len(z80s)], (k & 1) * 8, dict(meta, prep='P1', irq=i))
                k += 1
            U.require(rd(st, 0x100016, 1) == 2, 'P1 two IRQs release ef2')
            # P2: one IRQ at the ef2 arrival (100017 = 0 keeps the seed's no-wait ef2).
            st = U.with_host_writes(base, p2_writes(base))
            st, _, _ = U.advance_native(st, h['ext'], 0xef2, external_status=fr['start']['status'])
            natural_irq('nat-p2-seed%d-f%d' % (case, fr['frame']), st, z80s[k % len(z80s)], 8, dict(meta, prep='P2'))
            k += 1
    return st


def column_object(base, flags, w26, w7c, w7e, words):
    out = [(base + 0x7a, 1, flags), (base + 0x26, 2, w26), (base + 0x7c, 2, w7c), (base + 0x7e, 2, w7e)]
    for i, w in enumerate(words):
        out.append((base + 0x3a + 2 * i, 2, w & 0xffff))
    return out


COLUMNS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)


def sprite_box(d3e, d46):
    """d3e(A5) / d46(A5) quadruples (WORD 0, 2, 4, 6)."""
    out = []
    for base, q in ((0x108d3e, d3e), (0x108d46, d46)):
        for i, v in enumerate(q):
            out.append((base + 2 * i, 2, v & 0xffff))
    return out


def build():
    del OUT[:]
    cases = U.natural_cases(3)
    natural_fixtures(cases, (1, 2, 3))
    # Typed base: seed 0 frame 1 with P1 prep at the ef2 wait (a natural IRQ wait-point state).
    fr = [f for f in U.seed_frames(cases[0], 2) if f['frame'] == 1][0]
    base0 = U.seed_state(fr['start'])
    base, _, _ = U.advance_native(U.with_host_writes(base0, p1_writes(base0)), fr['h']['ext'], 0xef2, external_status=fr['start']['status'])
    Q_IRQ = [(0x320000, 1, 0)]
    NR = [(0x10001b, 1, 0)]          # no render path (the H of the base frame set 10001b bit 7)

    # ---- IRQ shell branches -------------------------------------------------------------------------
    fx('irq-bios-int1-21e', irq_entry(base, 0x20c, writes=[(0x10fd80, 1, 0)]), [], BIOS_INT1)
    fx('irq-callback-live-224', irq_entry(base, 0x20c, writes=[(0x100006, 4, SENT2)]), [], SENT2)
    fx('irq-reentry-c96', irq_entry(base, 0x20c, writes=[(0x100019, 1, 0x80)]), [], BIOS_IO)
    fx('irq-saturate-fe', irq_entry(base, 0x20c, writes=NR + [(0x100016, 1, 0xfe)]), Q_IRQ, BIOS_IO)
    fx('irq-saturate-ff-caa', irq_entry(base, 0x20c, writes=NR + [(0x100016, 1, 0xff)]), Q_IRQ, BIOS_IO)
    fx('irq-render-72fa', irq_entry(base, 0x20c, writes=[(0x10001b, 1, 0x80)]), [], 0x72fa)
    fx('irq-no-render-d36', irq_entry(base, 0x20c, writes=NR), Q_IRQ, BIOS_IO)
    fx('irq-sound-port-d42', irq_entry(base, 0x20c, writes=NR + [(0x10f001, 1, 0x10)]), Q_IRQ, BIOS_IO)
    # 248 resume variants from a captured c0044a stop (popped SR C clear / set, bank / VRAM copies, status bit 3)
    e = irq_entry(base, 0x20c, writes=NR + [(0x100010, 2, 0x0003), (0x104d8e, 2, 0x7123)], regs={'d0': 0x11112222, 'd7': 0x3333fff7})
    mid, _, _ = U.advance_native(e, Q_IRQ, BIOS_IO)
    b = resume_bios(mid)
    a7 = b['regs']['a7']
    sr_at = a7 + 4 + 60          # bank WORD, VRAM WORD, 15 LONG registers, then the SR WORD
    U.require(rd(b, sr_at, 2) == 0x2000 and rd(b, sr_at + 2, 4) == 0xef2, 'exception frame layout')
    fx('rte-248-sr2000-v0', b, [(0x3c0006, 2, 0)], 0xef2)
    fx('rte-248-sr2001-vfff7', U.with_host_writes(b, [(sr_at, 2, 0x2001)]), [(0x3c0006, 2, 0xfff7)], 0xef2)
    fx('rte-248-sr2701', U.with_host_writes(b, [(sr_at, 2, 0x2701)]), [(0x3c0006, 2, 0x0008)], 0xef2)
    fx('error-rte-248-s0', U.with_host_writes(b, [(sr_at, 2, 0x0000)]), [(0x3c0006, 2, 0)], 0xef2, ('error', 'unsupported animation irq RTE status'))
    fx('error-rte-248-t1', U.with_host_writes(b, [(sr_at, 2, 0xa000)]), [(0x3c0006, 2, 0)], 0xef2, ('error', 'unsupported animation irq RTE status'))
    fx('error-queue-3c0006', b, [], 0xef2, ('error', 'external read queue empty'))
    fx('error-queue-320000', irq_entry(base, 0x20c, writes=NR), [], BIOS_IO, ('error', 'external read queue empty'))
    fx('error-queue-mismatch-320000', irq_entry(base, 0x20c, writes=NR), [(0x300000, 1, 0)], BIOS_IO, ('error', 'external read queue mismatch'))
    # raster 29c (vector 68): bit 7 clear -> 2ce RTE; set -> 2a4 -> 3dcc -> 2b6 RTE; callback live
    fx('raster-2ce', irq_entry(base, 0x29c, writes=[(0x10fd80, 1, 0)]), [], 0xef2)
    fx('raster-2a4-3dcc-2b6', irq_entry(base, 0x29c, writes=[(0x104d8e, 2, 0x5a5a)]), [], 0xef2)
    fx('raster-2b6-sr2001', irq_entry(base, 0x29c, sr=0x2001), [], 0xef2)
    fx('raster-callback-live', irq_entry(base, 0x29c, writes=[(0x10000a, 4, SENT2)]), [], SENT2)
    fx('error-rte-2ce-s0', irq_entry(base, 0x29c, sr=0x0000, writes=[(0x10fd80, 1, 0)]), [], 0xef2, ('error', 'unsupported animation irq RTE status'))
    fx('error-rte-2b6-t1', irq_entry(base, 0x29c, sr=0xa000), [], 0xef2, ('error', 'unsupported animation irq RTE status'))

    # ---- service tail cc4.. (stack top = return sentinel; A5 = 108000) --------------------------------
    no_sprite = [(0x108d3d, 1, 0)]
    fx('svc-cc4-bit4-0', typed_entry(base, 0xcc4, no_sprite), Q_IRQ)
    fx('svc-cc4-bit4-1', typed_entry(base, 0xcc4, no_sprite + [(0x10f001, 1, 0x10)], regs={'d0': 0x5a}), Q_IRQ)
    # task queue (E9): frames at 10001c + 40*i; frame = D0-D7/A0-A5 (14 LONG), A6, PC
    def frames(count, pc=0x3dcc, start_index=None):
        first = 0x10081c - 0x40 * count
        ws = [(0x10081c, 4, first)]
        for i in range(count):
            f = first + 0x40 * i
            for r in range(14):
                v = 0x108000 if r == 13 else ((0x1000 * (i + 1) + r * 0x11) & 0xffffffff)
                ws.append((f + 4 * r, 4, v))
            ws.append((f + 56, 4, 0x10a000 + i))
            ws.append((f + 60, 4, pc))
        return ws
    fx('task-one', typed_entry(base, 0xcc4, no_sprite + frames(1)), Q_IRQ)
    fx('task-two', typed_entry(base, 0xcc4, no_sprite + frames(2) + [(0x10f001, 1, 0x10)]), Q_IRQ)
    fx('task-32', typed_entry(base, 0xcc4, no_sprite + frames(32)), Q_IRQ)
    fx('task-pc-live', typed_entry(base, 0xcc4, no_sprite + frames(1, pc=SENT2)), [], SENT2)

    # ---- credit bbe / a74 / a2c / a4e -----------------------------------------------------------------
    fx('credit-bbe-fd82', typed_entry(base, 0xbbe, [(0x10fd82, 1, 1)]))
    fx('credit-bbe-14-zero', typed_entry(base, 0xbbe, [(0x10fd82, 1, 0), (0x100014, 1, 0)]))
    credit = [(0x10fd82, 1, 0), (0x10f004, 1, 0xff), (0x10f006, 1, 0x0c), (0x10f007, 1, 0x0f), (0x100004, 1, 0x10), (0x100005, 1, 0x01)]
    for fdaf in (0, 1, 2, 3):
        fx('credit-bbe-fdaf%d' % fdaf, typed_entry(base, 0xbbe, credit + [(0x100014, 1, 0x03), (0x10fdaf, 1, fdaf), (0x10fdb4, 1, 0)]))
    fx('credit-bbe-fdaf1-zero', typed_entry(base, 0xbbe, credit + [(0x100014, 1, 0x03), (0x10fdaf, 1, 1), (0x10f004, 1, 0x00)]))
    fx('credit-a74-fdaf1-fd82', typed_entry(base, 0xa74, credit + [(0x10fdaf, 1, 1), (0x10fd82, 1, 1), (0x10fdb4, 1, 3)]))
    fx('credit-a74-fdaf2-fd82', typed_entry(base, 0xa74, credit + [(0x10fdaf, 1, 2), (0x10fd82, 1, 1), (0x10fdb4, 1, 3)]))
    fx('credit-a74-fdaf2-mask0', typed_entry(base, 0xa74, credit + [(0x10fdaf, 1, 2), (0x10fdb4, 1, 3), (0x10f007, 1, 0)]))
    for i, (c0, c1, d0) in enumerate(((0x00, 0x05, 3), (0x01, 0x10, 3), (0x99, 0xa0, 3), (0x00, 0x00, 1), (0x42, 0x00, 2), (0x07, 0x00, 0x101))):
        fx('credit-a2c-%d' % i, typed_entry(base, 0xa2c, [(0x100004, 1, c0), (0x100005, 1, c1)], regs={'d0': 0xabcd0000 | d0}))
        fx('credit-a4e-%d' % i, typed_entry(base, 0xa4e, [(0x100004, 1, c0), (0x100005, 1, c1)], regs={'d0': 0xabcd0000 | d0}))
    fx('credit-a62-direct-00', typed_entry(base, 0xa62, [(0x100004, 1, 0)], regs={'a0': 0x100004, 'd1': 0, 'd7': 0x77777700}))
    fx('credit-a62-direct-a0', typed_entry(base, 0xa62, [(0x100004, 1, 0)], regs={'a0': 0x100004, 'd1': 0, 'd7': 0x777777a0}))

    # ---- sound / Z80 3cac and the sound timer 48156 ---------------------------------------------------
    def z80(name, reply, writes=(), timer=0, regs=None):
        fx('z80-' + name, typed_entry(base, 0x3cac, [(0x10d68c, 2, timer)] + list(writes), regs), [(0x320000, 1, reply)])
    z80('pending-3cc6', 0, [(0x104d7b, 1, 0x80)])
    z80('reply1-3cde', 1, [(0x104d7b, 1, 0)])
    z80('silence-3cea', 0, [(0x104d7b, 1, 0), (0x10f003, 1, 0x80)])
    z80('empty-3d06', 3, [(0x104d7b, 1, 0), (0x10f003, 1, 0), (0x104d74, 2, 5), (0x104d76, 2, 5)])
    ring = [(0x104cf4 + i, 1, (0x11 * (i % 4)) if i < 0x70 else 0x33) for i in range(0x80)]
    z80('ring-one', 0x7f, [(0x104d7b, 1, 0), (0x10f003, 1, 0), (0x104d74, 2, 2), (0x104d76, 2, 9)] + ring)
    z80('ring-dup-run', 0xff, [(0x104d7b, 1, 0), (0x10f003, 1, 0), (0x104d74, 2, 0x72), (0x104d76, 2, 0x10)] + ring)
    z80('ring-dup-to-end', 0, [(0x104d7b, 1, 0), (0x10f003, 1, 0), (0x104d74, 2, 0x72), (0x104d76, 2, 0x7a)] + ring)
    z80('ring-wrap-7f', 0, [(0x104d7b, 1, 0), (0x10f003, 1, 0), (0x104d74, 2, 0x7f), (0x104d76, 2, 0x03)] + ring)
    for t in (1, 0xf, 0x10, 0xffff, 0x8000):
        z80('timer-%x' % t, 0, [(0x104d7b, 1, 0x80)], timer=t)

    # ---- column control 1adf8 / 187d8 ----------------------------------------------------------------
    words = [(0x0101 * (i + 1)) ^ 0x8000 for i in range(32)]
    cols = []
    for obj, s7c in zip(COLUMNS, (0x0000, 0x0100, 0x0138, 0x0040)):
        cols += column_object(obj, 0x81, 0x0123 + (obj & 0xff), s7c, 0x0155 + (obj & 0xf), words)
    fx('columns-all-cells', typed_entry(base, 0x1adf8, cols))
    skips = column_object(COLUMNS[0], 0x80, 0, 0, 0, []) + column_object(COLUMNS[1], 0x01, 0, 0, 0, []) + \
        column_object(COLUMNS[2], 0x81, 0x8000, 0, 0, []) + column_object(COLUMNS[3], 0x83, 0x7fff, 0x1ff, 0x1ff, words[::-1])
    fx('columns-skips', typed_entry(base, 0x1adf8, skips))
    fx('column-cell-direct-18852', typed_entry(base, 0x18852, regs={'a4': 0x3c0000, 'a1': 0x10a000, 'd6': 0x12340000, 'd3': 0xa000, 'd4': 0x800, 'd5': 0x10000}),
       stop=0x18be6)
    fx('column-cell-direct-18bd8', typed_entry(base, 0x18bd8, regs={'a4': 0x3c0000, 'd6': 0x12345678, 'd7': 0x9abcdef0, 'd4': 0x800, 'd5': 0x10000}))

    # ---- sprite flush 16cfa: clear runs (queue empty) and writer-table boundaries ---------------------
    def sprite(name, d3c, d3d, d3e, d46, extra=(), stop=SENT, d34=0, d36=0, expect='match', regs=None):
        ws = [(0x108d3c, 1, d3c), (0x108d3d, 1, d3d), (0x108d34, 2, d34), (0x108d36, 2, d36)] + sprite_box(d3e, d46) + list(extra)
        fx('sprite-' + name, typed_entry(base, 0x16cfa, ws, regs=regs), [], stop, expect)
    sprite('skip-16e9e', 0x80, 0x00, (0, 0, 0, 0), (0, 0, 0, 0))
    # forward (d3c bit 7 = 1): n = WORD 2 - max(WORD 0, WORD 6) per box (16d26 copies WORD 0 to WORD 4)
    for n1, n2, t in ((0, 1, 'a'), (2, 40, 'b'), (379, 380, 'c'), (100, 3, 'd')):
        sprite('fwd-%d-%d' % (n1, n2), 0x80, 0x80, (5, 5 + n1, 0, 3), (-7 & 0xffff, n2 - 7, 0, -9 & 0xffff))
        sprite('fwd-max6-%s' % t, 0x80, 0x80, (5, 20 + n1, 0, 20), (-3 & 0xffff, n2 + 7, 0, 7))
    # backward (d3c bit 7 = 0): n = min(WORD 4, WORD 2) - WORD 0 (16dde copies WORD 2 to WORD 6)
    for n1, n2 in ((0, 1), (2, 40), (379, 380), (200, 7)):
        sprite('bwd-%d-%d' % (n1, n2), 0x00, 0x80, (4, 4 + n1 + 5, 4 + n1, 0), (-2 & 0xffff, n2 - 2, n2 + 30, 0))
        sprite('bwd-min2-%d' % n1, 0x00, 0x80, (4, 4 + n1, 4 + n1 + 9, 0), (-2 & 0xffff, n2 - 2, n2 - 2, 0))
    sprite('error-fwd-n381', 0x80, 0x80, (0, 381, 0, 0), (0, 0, 0, 0), expect=('error', 'unsupported animation irq f6a PC'))
    sprite('error-fwd-neg1', 0x80, 0x80, (0, 0, 0, 1), (0, 0, 0, 0), expect=('error', 'unsupported animation irq f6a PC'))
    sprite('error-bwd-n381', 0x00, 0x80, (0, 381, 381, 0), (0, 0, 0, 0), expect=('error', 'unsupported animation irq f6a PC'))
    # queue entries: A2 = 107f34 + sext(WORD (A0)); D7 = ((4(A2) != ffff) * 4 | (6(A2) & fb).B) * 4; stop at the table target
    obj = 0x107f34 + 0x0100
    def writer(word4, word6, d3c, d34, d36, slot_at, table):
        d7 = (((4 if word4 != 0xffff else 0) | (word6 & 0xfb)) & 0xff) * 4
        ws = [(obj + 4, 2, word4), (obj + 6, 2, word6), (slot_at, 2, 0x0100)]
        return ws, table + d7
    for i, (w4, w6) in enumerate(((0x1234, 0x0000), (0xffff, 0x0004), (0x0000, 0x0003), (0xffff, 0x00ff), (0x0001, 0x0007))):
        ws, tgt = writer(w4, w6, 0x80, 0x10, 0x20, 0x108b44, 0xf226)
        sprite('writer-fwd-%d' % i, 0x80, 0x80, (0, 0, 0, 0), (0, 0, 0, 0), ws, stop=tgt, d34=0x10, d36=0x20)
        ws, tgt = writer(w4, w6, 0x00, 0x20, 0x10, 0x108b42, 0x13b46)
        sprite('writer-bwd-%d' % i, 0x00, 0x80, (0, 0, 0, 0), (0, 0, 0, 0), ws, stop=tgt, d34=0x20, d36=0x10)
    # ring wrap: forward A0 at 108d32 (+2 = 108d34 -> 16d52); backward A1 = 108b34 (-> 16e0c, A1 = 108d34 - 2)
    ws, tgt = writer(0x1234, 0x0001, 0x80, 0x1fe, 0x1fe, 0x108d32, 0xf226)
    sprite('writer-fwd-wrap', 0x80, 0x80, (0, 0, 0, 0), (0, 0, 0, 0), ws, stop=tgt, d34=0x1fe, d36=0x0)
    ws, tgt = writer(0x1234, 0x0002, 0x00, 0, 0, 0x108d32, 0x13b46)
    sprite('writer-bwd-wrap', 0x00, 0x80, (0, 0, 0, 0), (0, 0, 0, 0), ws, stop=tgt, d34=0x10, d36=0x0)
    # 16d84 / 16e40 (BRA back after a writer returns) entered directly: A0 == A1 so the loop ends in the clear runs.
    fx('sprite-direct-16d84', push(base, [(4, SENT), (4, 0x12345678)], 0x16d84, [(0x108d3e, 2, 0), (0x108d40, 2, 3), (0x108d42, 2, 0), (0x108d44, 2, 0),
                                                                                    (0x108d46, 2, 0), (0x108d48, 2, 0), (0x108d4a, 2, 0), (0x108d4c, 2, 0)],
                                         regs={'a0': 0x108b40, 'a1': 0x108b40, 'a6': 0x3c0000}))
    fx('sprite-direct-16e40', push(base, [(4, SENT), (4, 0x10abcd00)], 0x16e40, [(0x108d3e, 2, 0), (0x108d40, 2, 5), (0x108d42, 2, 5), (0x108d44, 2, 7),
                                                                                    (0x108d46, 2, 0), (0x108d48, 2, 0), (0x108d4a, 2, 0), (0x108d4c, 2, 0)],
                                         regs={'a0': 0x108c00, 'a1': 0x108c00, 'a6': 0x3c0000}))
    # clear runs entered at 16092 / 166a0 directly (A6 = 3c0000 and an ordinary RAM target) and run entries entered directly
    for d1 in (0, 1, 2, 3, 7, 40, 41, 100, 199, 256, 300, 378, 379, 380):
        fx('run-16092-n%d' % d1, typed_entry(base, 0x16092, regs={'d0': 0x00017e00 + d1, 'd1': 0xffff0000 | d1, 'a6': 0x3c0000}))
        fx('run-166a0-n%d' % d1, typed_entry(base, 0x166a0, regs={'d0': 0x00027e00 + d1, 'd1': (-d1) & 0xffffffff, 'a6': 0x3c0000}))
    fx('run-16092-ram-a6', typed_entry(base, 0x16092, regs={'d0': 0x00017e00, 'd1': 3, 'a6': 0x10a100}))
    for n in (0, 1, 5, 64, 127, 128, 255, 333, 380):
        fx('run-entry-n%d' % n, typed_entry(base, 0x1669e - 4 * n, regs={'d0': 0x7e000000 + n, 'd2': 0x10000, 'a6': 0x3c0000}))
    fx('error-run-entry-interior-160b0', typed_entry(base, 0x160b0), [], SENT, ('error', 'unsupported animation irq f6a PC'))
    for pc in (0x210, 0x226, 0x2a6, 0xa2e, 0xc8e, 0x3cae, 0x48158, 0x187da, 0x18836 + 4, 0x18be4, 0x1adfa, 0x16094, 0x166a2, 0x16cfc, 0x16ea2):
        fx('error-interior-%x' % pc, typed_entry(base, pc), [], SENT, ('error', 'unsupported animation irq f6a PC'))
    return list(OUT)


# ----------------------------------------------------------------------------------
# Coverage helper (not used by the verifier): python tools/unit_fixture_specs/f6a.py --coverage
# ----------------------------------------------------------------------------------
def coverage(fixtures):
    import json
    starts = json.load(open(sys.argv[2]))['F6a'] if len(sys.argv) > 2 else None
    TRACE[0] = {}
    nat = U.native()
    for f in fixtures:
        if f.expect != 'match':
            continue
        r = nat.run(f.state, f.queue, f.stop, f.releases, f.wait_limit, f.external_status, f.card_answer, f.max_insn)
        if not r['ok']:
            print('native failed', f.name, r.get('error'), r.get('detail'))
    tr = TRACE[0]
    pcs = tr.get('pcs', set())
    blocks = sorted(set([int(x, 16) for x in starts] + [0xd2a, 0xce6])) if starts else []
    missed = [hex(b) for b in blocks if b not in pcs]
    runs = [0x1669e - 4 * n for n in range(381)]
    print(json.dumps(dict(blocks=len(blocks), missed=missed, run_entries_executed=sum(1 for e in runs if e in pcs),
                          jump_targets=sorted(hex(t) for t in tr.get('jumps', ())), rte=len(tr.get('rte', ()))), indent=0))


if __name__ == '__main__' and '--coverage' in sys.argv:
    coverage(build())
