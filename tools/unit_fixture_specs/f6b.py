"""V1 spec of unit F6b (IRQ palette transfer 72fa..8b64; contract docs/analysis/animation-machine-irq-f6b-contract.md, scope decision E6 as decided).

Native machine (this module; extends the F6a spec's machine, which is loaded unchanged from tools/unit_fixture_specs/f6a.py):
  * F6a declared steps are kept: RTE emulation at 29a / 2cc / 2d6, the Z80 page 320000 and the system page 3a0000, SR 2000 (see f6a.py).
  * Palette RAM (E6): the F6a plain 8 KiB at 400000 is replaced by one 8 KiB active buffer mapped 512 times over 400000..7fffff (mirror,
    reads and writes), plus two stored banks.  A BYTE write to 3a000f / 3a001f (still an ordered port of the system page) swaps the active
    buffer to bank 0 / bank 1 (the address selects).  palette_load / palette_dump give the verifier the (bank0, bank1, selected) state; the
    verifier then runs run_animation_machine_with_palette and compares both banks and the selection (tools/verify_animation_machine_unit_fixtures.py).
    Palette writes are not ports on either side.

Fixtures:
  natural  seeds (natural_cases) x frames: P1 prep (the F6a declaration) advanced natively to the ef2 wait, then each natural IRQ: the
           exception frame at 20c, native to the cbe JSR 72fa (F6a CALLS probe), a fixture 72fa -> cc4 (the F6b routine alone, real staging /
           pending / counter / display state of the seed) with a deterministic palette; and, when the IRQ has no F6c writer-table call, the
           whole IRQ 20c -> c0044a with the palette (F6a + F6b chain).  The IRQ is completed natively (BIOS resume, RTE) and the next IRQ of the
           frame follows (P1: two per frame).  P2 prep: one IRQ at the first ef2 arrival.
  typed    a natural P1 state (seed 0 frame 1 at ef2) with declared host writes, entered at a block start with the return sentinel c00500
           pushed: every cell test block (k = 1..255) and every cell copy block (k = 0..255) entered directly; 72fa with dirty patterns (all,
           alternate, none, random, single), pending 0 / 80, display 0 / 1, initial bank 0 / 1; special fill counters 2000 / 4000 / 6000 (8b5c
           with and without), direct entries of the head / tail / fill blocks; palette mirror reads and writes through A5 in 400000..7fffff;
           run_animation_machine (no palette) on a clean transfer.
  errors   fill counters leaving the mirror (1000, ffe0, 8000, 0020), odd counter 2001, palette write without a palette device, interior PCs.
  negative C++ palette input corrupted (one byte, selection): the comparison must report it.
"""
import ctypes
import importlib.util
from pathlib import Path
import random
import sys
import zlib

import verify_animation_machine_unit_fixtures as U
import observe_animation_machine_pvc_banks as PB

# Restore the original machine class if this module is loaded again in the same process, then load the F6a spec (it patches PB.PvcMachine).
PB.PvcMachine = [k for k in PB.PvcMachine.__mro__ if k.__name__ == 'PvcMachine' and k.__module__ == PB.__name__][0]
_spec = importlib.util.spec_from_file_location('unit_fixture_spec_f6a_base', str(Path(__file__).resolve().parent / 'f6a.py'))
F6A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F6A)

SENT = F6A.SENT
BIOS_IO = F6A.BIOS_IO
STAGING, FILL, COUNTER, DISPLAY, PENDING = 0x105da2, 0x107da2, 0x107dea, 0x107dec, 0x107ded
PAL_LO, PAL_SIZE, PAL_MIRRORS = 0x400000, 0x2000, 512
F6B_LO, F6B_HI = 0x72fa, 0x8b64
TRACE = [None]            # set to a set() to record executed F6b PCs (coverage helper)


def cell_test(k):
    return 0x732e + 0x14 * (k - 1)


def cell_copy(k):
    return 0x7326 if k == 0 else cell_test(k) + 8


STARTS = sorted([0x72fa, 0x7302, 0x730c, 0x871a, 0x8720, 0x8728, 0x8732, 0x8738, 0x873a, 0x8b5c, 0x8b60] +
                [cell_copy(k) for k in range(256)] + [cell_test(k) for k in range(1, 256)])
assert len(STARTS) == 522


class F6bMachine(F6A.F6aMachine):
    F6B_PATCHED = True

    def __init__(self, *a, **k):
        F6A.F6aMachine.__init__(self, *a, **k)
        import unicorn
        c = self.cpu
        c.mem_unmap(PAL_LO, PAL_SIZE)                       # the F6a plain 8 KiB (no mirror)
        self.pal_active = (ctypes.c_ubyte * PAL_SIZE)()
        c._keep.append(self.pal_active)
        for i in range(PAL_MIRRORS):
            c.mem_map_ptr(PAL_LO + PAL_SIZE * i, PAL_SIZE, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE, ctypes.addressof(self.pal_active))
        self.pal_banks = [bytearray(PAL_SIZE), bytearray(PAL_SIZE)]
        self.pal_sel = 0

    def palette_load(self, palette):
        self.pal_banks = [bytearray(palette[0]), bytearray(palette[1])]
        self.pal_sel = palette[2]
        ctypes.memmove(self.pal_active, bytes(self.pal_banks[self.pal_sel]), PAL_SIZE)

    def palette_select(self, sel):
        self.pal_banks[self.pal_sel][:] = bytes(self.pal_active)
        self.pal_sel = sel
        ctypes.memmove(self.pal_active, bytes(self.pal_banks[sel]), PAL_SIZE)

    def palette_dump(self):
        self.pal_banks[self.pal_sel][:] = bytes(self.pal_active)
        return (bytes(self.pal_banks[0]), bytes(self.pal_banks[1]), self.pal_sel)

    def install_basic_hooks(self, *a, **k):
        import unicorn
        F6A.F6aMachine.install_basic_hooks(self, *a, **k)
        mach = self

        def select(uc, access, address, size, value, user):
            if size == 1 and address in (0x3a000f, 0x3a001f):
                mach.palette_select(1 if address == 0x3a001f else 0)
        self.cpu.hook_add(unicorn.UC_HOOK_MEM_WRITE, select, begin=0x3a000f, end=0x3a001f)
        if TRACE[0] is not None:
            tr = TRACE[0]

            def code(uc, pc, size, user):
                tr.add(pc)
            self.cpu.hook_add(unicorn.UC_HOOK_CODE, code, begin=F6B_LO, end=F6B_HI - 1)


PB.PvcMachine = F6bMachine


# ----------------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------------
rd = F6A.rd


def seed_of(*parts):
    """Deterministic seed (str hash() is randomized per process)."""
    return zlib.crc32(repr(parts).encode())


def make_palette(seed, sel=0):
    r = random.Random(seed)
    return (bytes(r.getrandbits(8) for _ in range(PAL_SIZE)), bytes(r.getrandbits(8) for _ in range(PAL_SIZE)), sel)


def with_palette(state, palette):
    return dict(state, palette=palette)


def staging_writes(seed, dirty, pattern=True):
    """Staging blocks with bit 7 of the first BYTE = (k in dirty), random contents; the fill pattern."""
    r = random.Random(seed)
    ws = []
    for k in range(256):
        for i in range(0, 32, 4):
            v = r.getrandbits(32)
            if i == 0:
                v = (v & 0x7fffffff) | (0x80000000 if k in dirty else 0)
            ws.append((STAGING + 32 * k + i, 4, v))
    if pattern:
        ws += [(FILL + i, 4, r.getrandbits(32)) for i in range(0, 32, 4)]
    return ws


OUT = []


def fx(name, state, queue=(), stop=SENT, expect='match', **kw):
    OUT.append(U.Fixture(name, state, list(queue), stop, expect, **kw))
    return OUT[-1]


# ----------------------------------------------------------------------------------
# Natural IRQs
# ----------------------------------------------------------------------------------
def natural_irq(name, state, z80, video, meta, pal_seed):
    """One natural IRQ at a wait-point state (with palette): fixture 72fa -> cc4 when the IRQ reaches the F6b call, plus the whole IRQ
    20c -> c0044a when it has no F6c call; the IRQ is then completed natively.  -> state after the RTE."""
    wait_pc = state['pc']
    entry = F6A.irq_entry(state, 0x20c)
    qa = [(0x320000, 1, z80)]
    F6A.F6aMachine.CALLS = []
    try:
        probe = U.native().run(entry, qa, BIOS_IO)
        calls = list(F6A.F6aMachine.CALLS)
    finally:
        F6A.F6aMachine.CALLS = None
    U.require(probe['ok'], ('natural IRQ probe', name, probe.get('error'), probe.get('detail')))
    if (0x72fa, 0xcc4) in calls:
        at, q, _ = U.advance_native(entry, qa, 0x72fa)
        fx(name + '-72fa', at, q, 0xcc4, meta=dict(meta, wait_pc=wait_pc, part='72fa-cc4', pending=rd(at, PENDING, 1), counter=rd(at, COUNTER, 2),
                                                   dirty=sum(1 for k in range(256) if rd(at, STAGING + 32 * k, 1) & 0x80)))
        if len(calls) == 1:
            fx(name + '-irq', entry, qa, BIOS_IO, meta=dict(meta, wait_pc=wait_pc, part='20c-c0044a'))
    mid, rest, _ = U.advance_native(entry, qa, BIOS_IO)
    U.require(not rest, ('IRQ A queue not consumed', name, rest))
    b = F6A.resume_bios(mid)
    end, rest, _ = U.advance_native(b, [(0x3c0006, 2, video)], wait_pc)
    U.require(not rest, ('IRQ B queue not consumed', name, rest))
    U.require(end['regs'] == state['regs'], ('E3 register restore', name))
    return end


def natural_fixtures(cases, frames):
    z80s = (0, 1, 3, 0x7f, 0xff, 0)
    n = 0
    for case in cases:
        for fr in U.seed_frames(case, max(frames) + 1):
            h = fr.get('h')
            if fr['frame'] not in frames or h is None or h['reason']['reason'] != 'controller':
                continue
            base = U.seed_state(fr['start'])
            meta = dict(case=case, frame=fr['frame'])
            pal = make_palette(case * 1000 + fr['frame'], sel=fr['frame'] & 1)
            st = with_palette(U.with_host_writes(base, F6A.p1_writes(base)), pal)
            st, _, _ = U.advance_native(st, h['ext'], 0xef2, external_status=fr['start']['status'])
            for i in range(2):
                U.require(rd(st, 0x100016, 1) < rd(st, 0x100017, 1), ('ef2 not waiting', case, fr['frame'], i))
                st = natural_irq('nat-p1-seed%d-f%d-irq%d' % (case, fr['frame'], i), st, z80s[n % 6], (n & 1) * 8, dict(meta, prep='P1', irq=i), n)
                n += 1
            st = with_palette(U.with_host_writes(base, F6A.p2_writes(base)), pal)
            st, _, _ = U.advance_native(st, h['ext'], 0xef2, external_status=fr['start']['status'])
            natural_irq('nat-p2-seed%d-f%d' % (case, fr['frame']), st, z80s[n % 6], 8, dict(meta, prep='P2'), n)
            n += 1


# ----------------------------------------------------------------------------------
# Typed fixtures
# ----------------------------------------------------------------------------------
def build():
    del OUT[:]
    cases = U.natural_cases(3)
    natural_fixtures(cases, (1, 2, 3, 21, 25, 30))
    fr = [f for f in U.seed_frames(cases[0], 2) if f['frame'] == 1][0]
    base0 = U.seed_state(fr['start'])
    base, _, _ = U.advance_native(U.with_host_writes(base0, F6A.p1_writes(base0)), fr['h']['ext'], 0xef2, external_status=fr['start']['status'])
    base = with_palette(base, make_palette(7))
    regs_cell = {'a0': STAGING, 'a1': PAL_LO}

    def typed(name, pc, writes=(), regs=None, pal=None, stop=SENT, expect='match', **kw):
        st = F6A.typed_entry(base, pc, list(writes), regs)
        if pal is not None:
            st = with_palette(st, pal)
        return fx(name, st, [], stop, expect, **kw)

    # ---- every cell entry: test block k (k = 1..255, staging k dirty plus a few later blocks) and copy block k (k = 0..255) --------
    r = random.Random(0xf6b)
    for k in range(1, 256):
        dirty = {k} | set(j for j in range(k + 1, 256) if r.random() < 0.05)
        typed('cell-test-%d' % k, cell_test(k), staging_writes(k, dirty) + [(DISPLAY, 1, k & 1)], regs_cell, make_palette(100 + k, k & 1))
    for k in range(256):
        typed('cell-copy-%d' % k, cell_copy(k), staging_writes(500 + k, set()) + [(DISPLAY, 1, (k >> 1) & 1)], regs_cell, make_palette(600 + k, (k + 1) & 1))
    # ---- 72fa full transfers ---------------------------------------------------------------------------------------------------------
    patterns = dict(all=set(range(256)), alternate=set(range(1, 256, 2)), none=set(), first=set([0]), last=set([255]),
                    random=set(k for k in range(256) if r.random() < 0.3))
    for pname, dirty in sorted(patterns.items()):
        for pend in (0x80, 0x00, 0xff):
            for disp in (0, 1):
                for sel in (0, 1):
                    typed('xfer-%s-p%02x-d%d-b%d' % (pname, pend, disp, sel), 0x72fa,
                          staging_writes(seed_of(pname, pend, disp, sel), dirty) + [(COUNTER, 2, 0), (PENDING, 1, pend), (DISPLAY, 1, disp * 0x41)],
                          {'d0': 0x12345600 | (pend ^ disp)}, make_palette(seed_of(pname, sel), sel))
    # ---- special fill 873a / 8b5c / 8b60 ----------------------------------------------------------------------------------------------
    for counter in (0x2000, 0x4000, 0x6000):
        for disp in (0, 1):
            for sel in (0, 1):
                typed('fill-%04x-d%d-b%d' % (counter, disp, sel), 0x72fa, staging_writes(counter + disp, set(range(0, 256, 3))) +
                      [(COUNTER, 2, counter), (PENDING, 1, 0x80), (DISPLAY, 1, disp)], None, make_palette(counter + sel, sel))
    typed('fill-direct-873a', 0x873a, staging_writes(1, set()) + [(COUNTER, 2, 0x2000)], None, make_palette(11, 0), stop=0x8b5c)
    typed('fill-direct-8b5c', 0x8b5c, regs={'a0': 0x401ffe - 0x1e}, pal=make_palette(12, 1), stop=0x8b60)
    typed('fill-direct-8b5c-mirror', 0x8b5c, regs={'a0': 0x7fe000}, pal=make_palette(13, 0), stop=0x8720)
    typed('fill-direct-8b60', 0x8b60, [(DISPLAY, 1, 1)], pal=make_palette(14, 0))
    # ---- direct entries of the head / tail blocks ---------------------------------------------------------------------------------------
    typed('head-7302-pending', 0x7302, [(PENDING, 1, 0x81)], pal=make_palette(20, 1), stop=0x730c)
    typed('head-7302-clear', 0x7302, [(PENDING, 1, 0x7f)], pal=make_palette(21, 1))
    typed('head-730c', 0x730c, staging_writes(22, set([0, 9, 200])), pal=make_palette(22, 1))
    typed('head-730c-clean0', 0x730c, staging_writes(23, set([1])), pal=make_palette(23, 1))
    for pc, stop in ((0x871a, SENT), (0x8720, SENT), (0x8728, SENT), (0x8732, SENT), (0x8738, SENT)):
        for disp in (0, 1):
            typed('tail-%x-d%d' % (pc, disp), pc, [(DISPLAY, 1, disp)], {'d0': 0xabcdef00 | pc & 0xff}, make_palette(pc + disp, disp ^ 1), stop=stop)
    # ---- palette mirror reads / writes through A5 -----------------------------------------------------------------------------------
    # A5 = 7fe216: counter 7fe000 (= 0), pending 7fe003 (bit 7 set), display 7fe002, staging 7fbfb8.. = palette offsets 1fb8 + 20k (mod 2000).
    # A5 = 400300: counter 4000ea (= 2000 in both banks), fill source 4000a2 (bank 1 after the 3a001f select), display 4000ec.
    for sel in (0, 1):
        banks = [bytearray(b) for b in make_palette(30 + sel)[:2]]
        banks[sel][0:2] = b'\x00\x00'
        banks[sel][3] |= 0x80
        typed('mirror-xfer-b%d' % sel, 0x72fa, regs={'a5': 0x7fe216, 'd0': 0x77}, pal=(bytes(banks[0]), bytes(banks[1]), sel))
        banks = [bytearray(b) for b in make_palette(40 + sel)[:2]]
        for b in banks:
            b[0xea:0xec] = b'\x20\x00'
        typed('mirror-fill-b%d' % sel, 0x72fa, regs={'a5': 0x400300, 'd0': 0x78}, pal=(bytes(banks[0]), bytes(banks[1]), sel))
    # ---- run_animation_machine (no palette device) ----------------------------------------------------------------------------------
    plain = F6A.typed_entry(dict((k, v) for k, v in base.items() if k != 'palette'), 0x72fa, staging_writes(40, set()) + [(PENDING, 1, 0x80), (DISPLAY, 1, 1)])
    fx('plain-72fa-clean', plain)
    fx('error-plain-72fa-dirty', F6A.typed_entry(plain, 0x72fa, [(STAGING + 32 * 5, 1, 0x80)]), [], SENT, ('error', 'unsupported animation machine write device'))
    fx('error-plain-873a', F6A.typed_entry(plain, 0x72fa, [(COUNTER, 2, 0x2000)]), [], SENT, ('error', 'unsupported animation machine write device'))
    # ---- checked errors ------------------------------------------------------------------------------------------------------------------
    for counter in (0x1000, 0xffe0, 0x8000, 0x0020):
        typed('error-fill-%04x' % counter, 0x72fa, staging_writes(counter, set()) + [(COUNTER, 2, counter)], pal=make_palette(50),
              expect=('error', 'unsupported animation machine write device'))
    typed('error-fill-odd-2001', 0x72fa, [(COUNTER, 2, 0x2001)], pal=make_palette(51), expect=('error', 'invalid animation machine write size/alignment'))
    for pc in (0x72fc, 0x7304, 0x7320, 0x7324, 0x7328, 0x732a, 0x732c, 0x7330, 0x7336 + 2, 0x8710, 0x8718, 0x871c, 0x8722, 0x872e, 0x8734,
               0x873c, 0x8746, 0x874e, 0x8752, 0x8a00, 0x8b4e, 0x8b52, 0x8b58, 0x8b62):
        typed('error-interior-%x' % pc, pc, pal=make_palette(52), expect=('error', 'unsupported animation irq f6b PC'))
    typed('error-odd-pc', 0x7327, pal=make_palette(53), expect=('error', 'unaligned animation machine PC'))
    typed('error-neighbour-8b64', 0x8b64, pal=make_palette(54), expect=('error', 'unsupported animation machine PC'))
    # ---- negative checks: corrupted C++ palette input ------------------------------------------------------------------------------
    good = F6A.typed_entry(base, 0x72fa, staging_writes(60, set([3, 4])) + [(PENDING, 1, 0x80)])
    p0, p1, sel = good['palette']
    flipped = bytearray(p1)
    flipped[0x1234] ^= 1
    fx('negative-palette-byte', good, [], SENT, 'mismatch', cpp_state=with_palette(good, (p0, bytes(flipped), sel)))
    # the initial selection matters on a path without the 730c select: cell copy 3 entered directly writes the selected bank
    copy3 = F6A.typed_entry(base, cell_copy(3), staging_writes(61, set()), regs_cell)
    q0, q1, qsel = copy3['palette']
    fx('negative-palette-selected', copy3, [], SENT, 'mismatch', cpp_state=with_palette(copy3, (q0, q1, qsel ^ 1)))
    fx('negative-palette-missing', good, [], SENT, 'mismatch', cpp_state=dict((k, v) for k, v in good.items() if k != 'palette'))
    return list(OUT)


# ----------------------------------------------------------------------------------
# Coverage helper (not used by the verifier): python tools/unit_fixture_specs/f6b.py --coverage
# ----------------------------------------------------------------------------------
def coverage(fixtures):
    import json
    nat = U.native()
    seen = {'natural': set(), 'all': set()}
    for f in fixtures:
        if f.expect != 'match':
            continue
        TRACE[0] = set()
        r = nat.run(f.state, f.queue, f.stop, f.releases, f.wait_limit, f.external_status, f.card_answer, f.max_insn)
        if not r['ok']:
            print('native failed', f.name, r.get('error'), r.get('detail'))
        seen['all'] |= TRACE[0]
        if f.name.startswith('nat-'):
            seen['natural'] |= TRACE[0]
    TRACE[0] = None
    print(json.dumps(dict(starts=len(STARTS), reached_all=sum(1 for s in STARTS if s in seen['all']),
                          reached_natural=sum(1 for s in STARTS if s in seen['natural']),
                          missed=[hex(s) for s in STARTS if s not in seen['all']],
                          natural_fixtures=sum(1 for f in fixtures if f.name.startswith('nat-'))), indent=0))


if __name__ == '__main__' and '--coverage' in sys.argv:
    coverage(build())
