"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr2b_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data; only data areas, never
code bytes): the LONG state table 70d72..70d92 (70d22), the WORD-pair list 76a1c..76aa0 (768b6), the box 702fa..70302 (the A1 of 494c0 / 4941e in the
70302 chain), the bank-window LONGs 2000d0 / 2000d4 / 200140 / 20017c (-> 2a1000 / 2a2000 / 2a3000 / 2a4000) with the LONGs behind them.  A native run
that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as is a run that lands inside the unit on a PC that is not a
block start.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent 10eb00, LONG 8(A6) = the sibling 10ec00, LONG
3e(A6) = 10e400, LONG 7e(A6) = a position in 76a1c..76aa0), A0 = 10e400, A1 = 10ea00, A5 = 108000 (BYTEs -7453 / -e6 / 568e / 5681, the WORD table
5b88 of 4bc04), the player records 100cb8 / 100da8 (WORDs 42 / 46), the BYTEs 100014 / 10fd92, seeded BYTE / WORD / LONG field edits (sign
boundaries included), seeded D0-D7, the declared stack values (BYTE / WORD / LONG) the entered block pops.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA / BEQ exits, the RTS sentinel).
  single 2  a consumer entered through its real producer (494c0 -> 7031e; 497a6 -> 7686e; 288c -> 76938; 7054c -> 70cf8; 705ca (4bc04) -> 70d06;
            70606 -> 70d4c): stop = the consumer's successor; the native branch on the real flags decides it.  49fc6 (ROM scripts), 7028e (4ae4a
            terrain) and 46d72 (terrain) read ROM data: those consumers (769a0 bc930 70d14 4c2e8) have declared-C rows only (V1 runs the real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).  The passing
            RTS 4c2ec returns to the consumer 7686e (return LONG 7686e): its native branch confirms the passed C.
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C.  The modelled C
of the producers: 7061e 4c2ee Set, 70624 Clear.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr2b_test_table.py  (rewrites the generated section in place)
"""
import ctypes
import hashlib
import random
import re
import struct
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'unit_fixture_specs'))
import fr2b as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr2b_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
SET_SET, CLEAR_SET, DATA_SET, PASS_SET = set(B.SET_SET), set(B.CLEAR_SET), set(B.DATA_SET), set(B.PASS_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC1, PARENT, SIBLING = 0x10ea00, 0x10eb00, 0x10ec00
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
LIST, LIST_END = B.LIST, B.LIST_END
WINDOWS = {0x2000d0: (0x2a1000, (0x180, 0x20, 0x28, 0xc)), 0x2000d4: (0x2a2000, (0x1cc, 0x20, 0x28, 0xc)), 0x200140: (0x2a3000, (0x1c, 0x8c)),
           0x20017c: (0x2a4000, (0xc,))}


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    srng = random.Random(0xF42C)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    states = b''.join(l(v) for v in (0, 0x10fe10, 0x10fe14, 0, 0x10fe18, 0x10fe1c, 0x10fe1c, 0x10fe20))           # 70d72..70d92 (0 = no install)
    pairs = b''.join(w(srng.choice((0, 1, 0x7fff, 0x8000, 0xffff, srng.getrandbits(16)))) for _ in range(2 * 33))       # 76a1c..76aa0
    box = b''.join(w(v) for v in (srng.getrandbits(16), srng.getrandbits(16), 0x8000, 0x8000))                     # 702fa: WORD x, y, w, h (4941e)
    out = [(0x70d72, states), (LIST, pairs), (0x702fa, box)]
    for win in sorted(WINDOWS):
        dest, disps = WINDOWS[win]
        out.append((win, l(dest)))
        for d in disps:
            out.append((dest + d, l(srng.getrandbits(19) << 1)))
    return out


SYN = synthetic()


def load_program():
    program = bytearray(ob.load_rom())
    assert hashlib.sha256(program).hexdigest() == '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    for a, b in SYN:
        assert not any(lo < a + len(b) and a < hi for lo, hi in RANGES), hex(a)     # never over code of the unit
        program[a:a + len(b)] = b
    return bytes(program)


PROGRAM = load_program()
FIXED = (ctypes.c_ubyte * 0x100000).from_buffer_copy(PROGRAM[:0x100000])


def syn_ok(address, size):
    return any(a <= address and address + size <= a + len(b) for a, b in SYN)


# consumer -> (C clear successor, C set successor)
SUCC = {0x7031e: (0x703f0, 0x70322), 0x7686e: (0x76884, 0x76872), 0x76938: (0x7693c, 0x76942), 0x769a0: (0x769aa, 0x769a4), 0xbc930: (0xbc93a, 0xbc934),
        0x70cf8: (0x70d02, 0x70cfc), 0x70d06: (0x70d10, 0x70d0a), 0x70d14: (0x70d1e, 0x70d18), 0x70d4c: (0x70d60, 0x70d50), 0x4c2e8: (0x4c2ec, 0x4c2ee)}
assert set(SUCC) == CONS_SET
# consumers with a real producer chain in this test (RAM-only producers) and the chain entry
CHAINS = ((0x7031c, 0x7031e), (0x76862, 0x7686e), (0x76932, 0x76938), (0x70cf4, 0x70cf8), (0x70d02, 0x70d06), (0x70d48, 0x70d4c))


class Ram(object):
    def __init__(self):
        self.b = bytearray(65536)
        self.puts = []

    def put(self, a, n, v):
        assert 0x100000 <= a and a + n <= 0x110000, hex(a)
        data = (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'big')
        for i, x in enumerate(data):
            self.b[(a + i) & 0xffff] = x
        self.puts.append((a, data))


def base_ram():
    r = Ram()
    r.put(SP, 4, STOP)
    r.base = 1
    return r


def word_of(ram, a):
    if 0x100000 <= a < 0x110000:
        return (ram[a & 0xffff] << 8) | ram[(a + 1) & 0xffff]
    return (PROGRAM[a] << 8) | PROGRAM[a + 1]


def native(ram, regs, pc, carry, stopfn):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    sr = 0x2000 | (1 if carry == 2 else 0)
    if pc in B.C_RECOMPUTE:
        sr = (sr & ~1) | (1 if (regs['d1'] & 0xffff) < (regs['d0'] & 0xffff) else 0)     # b47f4: C of b47de (decision 4)
    if pc in B.Z_RECOMPUTE and word_of(ram, regs['a1'] & 0xffffff) == 0:
        sr |= 4                                     # b48ba: Z of TST.W (A1) (decision 4)
    c.reg_write(UC_REG['sr'], sr)
    out = dict(stop=None, bad=False)
    trace = []
    stray = []
    n = [0]

    def at(uc, p, size, user):
        if out['stop'] is not None:
            return
        n[0] += 1
        if n[0] > 1 and stopfn(p, trace):
            out['stop'] = p
            uc.emu_stop()
            return
        if trace and (p & 1 or (inr(p) and p not in STARTS_SET and p != trace[-1] + B.decode(trace[-1]).size)):
            out['bad'] = True                       # an odd PC or a computed landing inside a block of the unit: the C++ rejects it (error rows)
            uc.emu_stop()
            return
        trace.append(p)

    def rd(uc, access, address, size, value, user):
        if address < 0x100000 or 0x200000 <= address < 0x300000:
            if not syn_ok(address, size):
                stray.append((hex(address), size))
    c.hook_add(UC_HOOK_CODE, at, begin=0, end=0xffffff)
    c.hook_add(UC_HOOK_MEM_READ, rd, begin=0, end=0x2fffff)
    try:
        c.emu_start(pc, 0xffffff, count=2000000)
    except unicorn.UcError:
        return None
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.bank != 0x200000:
        return None
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or m.ports:
        return None                                 # FR2a writes no PVC port
    return dict(stop=out['stop'], trace=trace, regs=m.regs(), ram=m.ram(), ports=[])


def fnv_add(h, data):
    for x in data:
        h ^= x
        h = (h * 1099511628211) & 0xffffffffffffffff
    return h


def digest(ram, regs, pc):
    tail = b''.join(struct.pack('>I', regs[k]) for k in KEYS) + struct.pack('>III', pc, 0x200000, 0) + bytes([0])
    return fnv_add(fnv_add(1469598103934665603, ram), tail)


def puts_text(r):
    return ','.join('%x:%s' % (a & 0xffffff, d.hex()) for a, d in r.puts[r.base:])


def carry_after(p, c):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set)."""
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in SET_SET:
        return 2
    if p in CLEAR_SET:
        return 1
    return 0


def model(executed, carry):
    c = carry
    for p in executed:
        c = carry_after(p, c)
    return c


ROWS = []
NAMES = set()


def row(name, r, regs, entry, stop, carry, c, single, o=None, error=None, fail_pc=0):
    assert name not in NAMES, name
    NAMES.add(name)
    d = dict(name=name, entry=entry, stop=stop, carry=carry, regs=[regs[k] & 0xffffffff for k in KEYS], puts=puts_text(r), error=error, single=single, c=c,
             fail=fail_pc)
    if o is not None:
        d.update(out=[o['regs'][k] for k in KEYS], digest=digest(o['ram'], o['regs'], o['stop']))
    ROWS.append(d)


# ---------------------------------------------------------------------------------------------------------------------
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xe2, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x17, 0x18, 0x2f, 0x30, 0x47, 0x48, 0x7f, 0x80, 0xe0, 0xff, 0x100, 0x127, 0x128, 0x1e0, 0x7fff, 0x8000, 0x8001,
      0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 0x10, 0x7fff, 0x10000, 0x30000, 0x60000, 0x8a9ffff, 0x8aa0000, 0x148fffff, 0x14a00000, 0x7fffffff, 0x80000000, 0xfff00000, 0xfffa0000,
      0xfffe0000, 0xffff0000, 0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x3e, 0x7e}
STACK = dict(B.STACK)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq'):
            sz = 1
        for m in HX.finditer(op):
            disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
            out.append((int(m.group(3)), disp, sz))
    return out


def rand_val(rng, size):
    if size == 1:
        return rng.choice(VB) if rng.random() < 0.8 else rng.getrandbits(8)
    if size == 2:
        return rng.choice(VW) if rng.random() < 0.7 else rng.getrandbits(16)
    return rng.choice(VL) if rng.random() < 0.6 else rng.getrandbits(32)


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, REC1, PLAYER1)),
                a1=rng.choice((REC1, CHILD)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=CHILD, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x30, 0x48, 0x80, 0xff, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340003))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 2, 0x80, 0xff, 0x8000, 0xffff, 0x123456a5))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG and the node links are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x3e, 4, CHILD)
    r.put(NODE + 0x7e, 4, rng.choice((LIST, LIST + 4, LIST_END - 8, LIST_END - 4, LIST + 4 * rng.randrange(33))))
    for off in (0x62, 0x89, 0x15):
        r.put(PARENT + off, 1, rand_val(rng, 1))
    r.put(PARENT, 4, rng.choice((0x270e, 0x270f, 0)))
    for a in (PLAYER1, PLAYER2, CHILD, REC1):
        r.put(a + 0x1e, 2, rand_val(rng, 2))
        r.put(a + 0x42, 2, rand_val(rng, 2))
        r.put(a + 0x46, 2, rand_val(rng, 2))
        r.put(a + 0x15, 1, rand_val(rng, 1))
    for a in (0x100bad, 0x107f1a, 0x100014, 0x10fd92, 0x10d68e):
        r.put(a, 1, rand_val(rng, 1))
    for k in range(0, 0x100, 2):
        if rng.random() < 0.1:
            r.put(0x10db88 + k, 2, rand_val(rng, 2))
    pops = []
    for size, kind in STACK.get(s, ()):
        if size == 'B':
            pops.append((2, (rand_val(rng, 1) << 8) | rng.getrandbits(8)))
        else:
            n = 4 if size == 'L' else 2
            v = {'node': rng.choice((CHILD, REC1, PLAYER1)), 'a6': NODE, 'small': rng.choice((0, 1, 2, 3)), 'any': rand_val(rng, n)}[kind]
            pops.append((n, v))
    depth = sum(n for n, v in pops)
    at = SP - depth
    for n, v in pops:
        r.put(at, n, v)
        at += n
    regs['a7'] = SP - depth
    if hint:
        for a, n, v in hint.get('puts', []):
            r.put(a, n, v)
        regs.update(hint.get('regs', {}))
    return r, regs


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x288c, 0x28ae, 0x2a00, 0x8ebe, 0x8ff4, 0xa70a, 0xa73e, 0x43e34, 0x43ea4, 0x46d72, 0x491b6, 0x491c4, 0x49214, 0x49274, 0x49290, 0x494c0,
                 0x497a6, 0x49a84, 0x49f8c, 0x49fc6, 0x4bc44, 0x4be2c, 0x4be34, 0x4bfa4, 0x70036, 0x7028e, 0x70418, 0x7054c, 0x705ca, 0x71c90, 0x72dd2,
                 0xc6a96, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer (70d22 / 70d38 -> 70606 -> 70d4c: the modelled C of 70606)


def hints(s):
    h = []
    N = lambda o, n, vals: [dict(puts=[(NODE + o, n, v)]) for v in vals]
    R = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if s == 0x48256:
        h += [dict(regs=dict(d0=0x12345600), puts=[(0x100bad, 1, v)]) for v in (0, 0x7f, 0xfe, 0xff)]
    if s == 0x9ef2:
        h += [dict(regs=dict(d0=0x12345678), puts=[(0x107f1a, 1, v)]) for v in (0, 0x80, 0xff)]
    if s == 0xbb6:
        h += [dict(regs=dict(d0=d), puts=[(0x100014, 1, v)]) for d, v in ((0x12345680, 0x01), (0, 0x5a), (0xff, 0))]
    if s in (0xa8d4, 0xa8dc, 0xa8e4, 0xa930):
        h += R('d0', (0, 1, 3, 4, 0x10003, 0xffff0004, 0x12340001))
    if s == 0x4c2d0:
        h += R('d0', (0x8000, 0xffff, 0x12345678))
    if s == 0x4c2ee:
        h += R('d6', (0x80000000, 0x00010000, 0xffff0000, 0x12345678))
    if s == 0x702cc:
        h += [dict(puts=[(NODE + 0x64, 4, a), (NODE + 0x36, 4, b), (NODE + 0x3a, 4, c)]) for a, b, c in
              ((0, 0, 0), (0x80000000, 0x7fffffff, 0xfff00000), (0x7fffffff, 0x80000000, 0), (0x1f, 0, 0xffefffff), (0, 0x20, 0x7fffffff))]
    if s == 0x70302:
        h += N(0x78, 2, (0, 1, 0x8000))
    if s == 0x7030a:
        h += N(0x82, 1, (0, 8, 0xf7, 0xff))
    if s in (0x70314, 0x70616):
        h += N(0x86, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0x70322:
        h += [dict(puts=[(NODE + 0x87, 1, b), (NODE + 0x15, 1, f)]) for b in (0, 0xff, 2, 0xfd) for f in (0, 0x80)]
    if s == 0x70330:
        h += R('d1', (0xff, 0x12345602, 0xfffffffd))
    if s in (0x70334, 0x70346):
        h += N(0x82, 1, (0, 2, 0x40, 0x42, 0xff))
    if s == 0x7033e:
        h += R('d1', (0, 2, 0xfd, 0x12345602, 0xfffffffd))
    if s == 0x70364:
        h += R('d1', (0, 0x100, 1, 0xffffff00))
    if s == 0x7036a:
        h += R('d1', (0xff, 0x80, 1, 0x123456a5, 0))
    if s == 0x70394:
        h += [dict(puts=[(NODE + 0x87, 1, b)], regs=dict(d0=d)) for b in (0, 1, 0x80, 0xff, 0x55) for d in (0, 1, 7, 8, 0x12340003)]
    if s in (0x703a8, 0x703b2, 0x703bc, 0x703c6, 0x703d0, 0x703da, 0x703e4):
        h += [dict(regs=dict(d1=a, d2=b, d3=c)) for a, b, c in ((0, 0x80, 0), (1, 0x80, 0), (0, 0x7f, 0), (0x8000, 0xff, 1), (0, 0, 0xffff), (5, 0x80, 0xffff), (0, 0x80, 0x12340000), (1, 0x80, 0x12340001), (0, 0, 0xffff0000))]
    if s in (0x703ee, 0x703f0):
        h += R('d0', (0, 0x12340000))
    if s == 0x70606:
        h += N(0x42, 2, (0x17, 0x18, 0x127, 0x128, 0x8000, 0xffff))
    if s in (0x70674, 0x70764, 0x707e2):
        h += N(0x70, 2, (0, 1, 0x8000))
    if s == 0x7068c:
        h += N(0x6a, 1, (0, 1, 0x80)) + N(0x6a, 2, (0x00ff, 0x0001, 0x0100))
    if s == 0x70c76:
        h += N(0x15, 1, (0, 0x40, 0x80, 0xc0, 0x3f, 0x7f))
    if s == 0x76974:
        h += [dict(puts=[(NODE + 0x36, 4, a), (NODE + 0x3a, 4, b)]) for a, b in ((0x12345678, 0), (0, 0x9abcdef0), (0xffffffff, 0xffffffff))]
    if s == 0x769ec:
        h += [dict(regs=dict(a0=CHILD), puts=[(CHILD + 0x15, 1, v)]) for v in (0, 1, 0xfe, 0xff)]
    if s in (0x70698, 0x706fe, 0x7077c, 0x70c0c):
        h += N(0x9c, 2, (0, 1, 0x8000))
    if s == 0x70832:
        h += N(0x15, 1, (0, 1, 0xfe, 0xff))
    if s == 0x70c8c:
        h += N(0x6e, 1, (2, 3, 4, 0x83))
    if s == 0x70c96:
        h += [dict(puts=[(NODE + 0x8e, 2, a), (NODE + 0x42, 2, b), (NODE + 0x15, 1, f)]) for a, b in
              ((0x10, 0), (0, 0x10), (0x8000, 0), (0x7fff, 0xffff), (0, 0), (0x30, 0)) for f in (0, 1)]
    if s == 0x70cb0:
        h += R('d0', (0x8000, 0xffff, 0x12340001))
    if s in (0x70cb2, 0x70cc6, 0x70cd8, 0x70ce6):
        h += R('d0', (0xf, 0x10, 0x2f, 0x30, 0x47, 0x48, 0x8000, 0x12340010))
    if s == 0x70cc0:
        h += R('d1', (0, 0x7fff, 0x8000, 0x12348000))
    if s == 0x70d22:
        h += R('d0', (0, 1, 2, 3, 4, 5, 6, 7, 0x12340003))
    if s == 0x70d38:
        h += N(0x82, 1, (0, 1))
    if s in (0x70d50, 0x768cc, 0xbc8b6, 0x718d2):
        h += N(0x15, 1, (0, 1, 8, 0x80, 0x88))
    if s == 0x70d60:
        h += N(0x7c, 2, (0, 1, 0x8000))
    if s == 0x768b6:
        h += N(0x7e, 4, (LIST, LIST + 4, LIST_END - 8, LIST_END - 4))
    if s == 0x768da:
        h += R('d0', (0, 1, 0x8000, 0xffff, 0x12348000))
    if s == 0x768dc:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0))]
    if s == 0x7690a:
        h += [dict(puts=[(PARENT + 0x89, 1, v)]) for v in (0, 1, 0x80)]
    if s == 0x76984:
        h += N(0x3a, 4, (0, 0xfffe0000, 0x80000000, 0x7fffffff, 0xffffffff, 0x10))
    if s == 0x769c8:
        h += [dict(puts=[(SP - 6, 4, CHILD), (CHILD, 2, a), (CHILD + 2, 2, b), (NODE + 0x15, 1, f)]) for a, b in ((0x8000, 0x7fff), (0, 0xffff))
              for f in (0, 1)]
    if s == 0x769d8:
        h += R('d0', (0, 0x8000, 0x12340001))
    if s == 0x769b4:
        h += R('d0', (0, 1, 0x12345601))
    if s == 0x769e6:
        h += [dict(puts=[(SP - 2, 2, v)]) for v in (0x0000, 0x00ff, 0x0100, 0x8000)]
    if s == 0xb33c8:
        h += N(0x86, 2, (0, 1, 0x8000, 0xffff))
    if s == 0xbc8d0:
        h += [dict(puts=[(PARENT + 0x62, 1, v)]) for v in (0, 1, 0x80)]
    if s == 0xbc8dc:
        h += N(0x76, 2, (0, 1, 0x8000))
    if s == 0xdd5a6:
        h += N(0x76, 4, (0x8a9ffff, 0x8aa0000, 0x8a9fffe, 0xfffa0000, 0xfff9ffff, 0xffffffff, 0, 0x80000000, 0x7fffffff))
    if s == 0xdd5f8:
        h += N(0x76, 4, (0x1489ffff, 0x148a0000, 0xfffa0000, 0))
    if s == 0xdd64a:
        h += N(0x76, 4, (0x1589ffff, 0x158a0000, 0xfffa0000, 0))
    if s == 0xdd69c:
        h += N(0x76, 4, (0, 0xfffa0000, 0xffffffff))
    if s in (0x76852, 0x76944, 0xb336a, 0xbc844, 0x70c0c, 0xdd574, 0x48256, 0x4c2cc):
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d7=0x55667788))]
    return h


def gen_singles(rng):
    for s in STARTS:
        if s in CONS_SET:
            continue
        fl = fields(s)
        kept = {}
        hs = hints(s)
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs = world(rng, fl, s, hint)
            o = native(r.b, regs, s, 0, single_stop)
            if o is None:
                continue
            nxt = o['stop']
            if nxt in CONS_SET or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
                continue
            key = (nxt, 'h%d' % t) if hint else nxt
            if key in kept:
                continue
            if not hint and sum(1 for k in kept if (k[0] if isinstance(k, tuple) else k) == nxt) >= 2:
                continue
            kept[key] = (r, regs, o)
            if t >= len(hs) and len(kept) >= 6:
                break
            if t >= len(hs) and t > 120 and len(kept) >= 2:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 1, o)


PATH_ENTRIES = (0x48256, 0xa92a, 0xa8d0, 0xa8d4, 0xa930, 0x9ef2, 0xbb6, 0x4c2d0, 0x702cc, 0x70302, 0x70322, 0x70334, 0x70364, 0x7036a, 0x70394, 0x70606,
                0x70674, 0x7068c, 0x706fe, 0x70764, 0x7077c, 0x707e2, 0x70832, 0x70c0c, 0x70c76, 0x70c8c, 0x70c96, 0x70cb2, 0x70cc0, 0x70d22, 0x70d38,
                0x70d50, 0x70d60, 0x718c8, 0x718d2, 0x76852, 0x76892, 0x768b6, 0x768cc, 0x7690a, 0x76944, 0x76974, 0x76984, 0x769ac, 0x769b2, 0x769c8,
                0x769e6, 0x769f4, 0xb336a, 0xb33b0, 0xb33c8, 0xbc844, 0xbc884, 0xbc8b6, 0xbc8d0, 0xbc8f2, 0xdd574, 0xdd5a6, 0xdd5c6, 0xdd5f8, 0xdd618,
                0xdd64a, 0xdd66a, 0xdd69c)


def gen_paths(rng):
    fl = []
    for b in STARTS:
        fl += fields(b)
    fl = sorted(set(fl))
    for s in PATH_ENTRIES:
        kept = {}
        hs = hints(s)
        for t in range(240):
            carry = rng.choice((0, 1, 2))
            r, regs = world(rng, fl, s, hs[t % len(hs)] if hs and t % 3 == 1 else None)
            o = native(r.b, regs, s, carry, path_stop)
            if o is None:
                continue
            ex = [p for p in o['trace'] if p in STARTS_SET]
            if any(p in CONS_SET for p in ex) or not allowed(o['stop']):
                continue
            key = (o['stop'], tuple(ex[:60]))
            if key in kept:
                continue
            kept[key] = (r, regs, o, carry, ex)
            if len(kept) >= 4:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o, carry, ex)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=REC1, a2=PLAYER1, a3=PLAYER2, a4=0xa4a4a4a4, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry):
    """A world for a real producer chain (494c0 / 497a6 / 288c / 7054c / 705ca / 70606)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d7=rng.getrandbits(32)))
    if entry == 0x7031c:                                         # 49370: BYTE 568e(A5) bits 0 / 1 choose the players tested by 4941e (box 702fa)
        r.put(0x10d68e, 1, rng.choice((0, 1, 2, 3)))
        for p in (PLAYER1, PLAYER2):
            r.put(p + 0x42, 2, rng.choice((0, 0x10, 0x100, rng.getrandbits(16))))
            r.put(p + 0x46, 2, rng.choice((0, 0x10, 0x100, rng.getrandbits(16))))
        r.put(NODE + 0x42, 2, rng.choice((0, 0x10, 0x100, rng.getrandbits(16))))
        r.put(NODE + 0x46, 2, rng.choice((0, 0x10, 0x100, rng.getrandbits(16))))
        r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0x76862:                                         # 497a6: TST.B 10fd92 (0 -> ORI Set)
        regs['a0'] = CHILD
        r.put(0x10fd92, 1, rng.choice((0, 1, 0x80)))
    if entry == 0x76932:                                         # 288c: LONG c(A6) = 0 (Set) / LONG (parent) 270e (Clear)
        v = rng.choice((0, PARENT, PARENT))
        r.put(NODE + 0xc, 4, v)
        r.put(PARENT, 4, rng.choice((0x270e, 0x270f)))
    if entry == 0x70cf4:                                         # 7054c: BYTE 61 bit 5, 82 bits 2 / 4 / 5 / 6, 6f = 40
        r.put(NODE + 0x61, 1, rng.choice((0, 0x20)))
        r.put(NODE + 0x82, 1, rng.choice((0, 4, 0x10, 0x20, 0x40, 0x14)))
        r.put(NODE + 0x6f, 1, rng.choice((0x40, 0)))
    if entry == 0x70d02:                                         # 705ca: BYTE 82 bit 1, 6f = 40, 4bc04 reads WORD 5b88(A5) + offset
        r.put(NODE + 0x82, 1, rng.choice((2, 2, 0)))
        r.put(NODE + 0x6f, 1, rng.choice((0x40, 0x40, 0)))
        r.put(NODE + 0x42, 2, 0x100)
        r.put(NODE + 0x46, 2, 0x120)
        r.put(0x10dbfc, 2, rng.choice((0x10, 0x3f, 0x40, 0x80, 0x100)))
    if entry == 0x70d48:                                         # 70606: WORD 42, BYTE 86
        r.put(NODE + 0x42, 2, rng.choice((0x17, 0x18, 0x100, 0x128, 0x200)))
        r.put(NODE + 0x86, 1, rng.choice((0x80, 0, 0xff)))
    return r, regs


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # the passing RTS 4c2ec entered with a declared C returns to the consumer 7686e (return LONG 7686e): its native branch confirms the C
    for pp in sorted(PASS_SET):
        for carry in (1, 2):
            r = base_ram()
            r.put(SP, 4, 0x7686e)
            regs = dict(PLAIN)
            o = native(r.b, regs, pp, carry, lambda p, tr: p in (0x76884, 0x76872))
            assert o is not None and o['stop'] == (0x76884 if carry == 1 else 0x76872), (hex(pp), carry)
            row('pass-%x-c%d' % (pp, carry), r, regs, pp, o['stop'], carry, carry, 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAINS:
        clr, st = SUCC[cons]
        seen = {}
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st))
            if o is None or cons not in o['trace'] or (o['stop'] in seen and seen[o['stop']] >= 3):
                continue
            seen[o['stop']] = seen.get(o['stop'], 0) + 1
            c = 1 if o['stop'] == clr else 2
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, c, 2, o)
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        assert set(seen) == {clr, st}, (hex(entry), seen)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=0, a3=0, a4=CHILD, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr2b caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node / list / stack: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-70302', 0x70302, odd, 0x70302, stop=0x7030a, a6=NODE + 1)
    err('odd-node-70c68', 0x70c68, wodd, 0x70c68, stop=0x70c76, a6=NODE + 1)
    err('odd-node-dd5a6', 0xdd5a6, odd, 0xdd5a6, stop=0xdd5ba, a6=NODE + 1)
    err('odd-list-768b6', 0x768b6, odd, 0x768b6, stop=0x768cc, puts=[(NODE + 0x7e, 4, LIST + 1)])
    err('odd-stack-70362', 0x70362, odd, 0x70362, stop=0x70364, a7=SP + 1)
    err('odd-stack-769c8', 0x769c8, odd, 0x769c8, stop=0x769da, a7=SP + 1)
    err('odd-pair-769c8', 0x769c8, odd, 0x769c8, stop=0x769da, a7=SP - 6, puts=[(SP - 6, 4, CHILD + 1)])
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('70d22-table-rom', 0x70d22, missing, 0x70d22, stop=0x70d36, d0=0x40)
    err('768b6-list-rom', 0x768b6, missing, 0x768b6, stop=0x768cc, puts=[(NODE + 0x7e, 4, LIST_END)])
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   70302 (WORD 78 != 0) -> 703f0 MOVEQ; RTS at an odd A7
    err('70302-then-703f0', 0x70302, odd, 0x703f0, puts=[(NODE + 0x78, 2, 1)], a7=SP + 1)
    #   70606 (WORD 42 - 18 >= 110) -> 70624 ANDI; RTS at an odd A7
    err('70606-then-70624', 0x70606, odd, 0x70624, puts=[(NODE + 0x42, 2, 0x200)], a7=SP + 1)
    #   b33c8 (WORD 86 = 5) -> b33d6 RTS at an odd A7
    err('b33c8-then-b33d6', 0xb33c8, odd, 0xb33d6, puts=[(NODE + 0x86, 2, 5)], a7=SP + 1)
    #   a8d4 (D0.W = 0) -> a8dc -> a8e4 -> a8ec RTS at an odd A7
    err('a8d4-then-a8ec', 0xa8d4, odd, 0xa8ec, a7=SP + 1)
    #   dd5a6 (LONG 76 + 60000 < 8b00000) -> dd5c0 MOVE.L D0,76(A6); RTS at an odd A7
    err('dd5a6-then-dd5c0', 0xdd5a6, odd, 0xdd5c0, a7=SP + 1)
    #   70c96 (D0.W >= 0) -> 70cb2 (>= 10) -> 70cba MOVE.L #70e2a,(A6) at an odd ... (A6 even): 70cc0 ... -> 70cf4 BSR at an odd A7
    err('70c96-then-70cf4', 0x70c96, odd, 0x70cf4, stop=0x7054c, puts=[(NODE + 0x8e, 2, 0x20)], a7=SP + 1)


def main():
    rng = random.Random(0xF42B)
    B.load_routing()
    gen_singles(rng)
    gen_paths(rng)
    gen_consumers(rng)
    gen_errors()
    out = []
    for d in ROWS:
        regs = ','.join('0x%x' % v for v in d['regs'])
        if d['error'] is None:
            outr = ','.join('0x%x' % v for v in d['out'])
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",NULL,0x0,{%s},%d,%d,%dULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'], outr,
                                                                                   d['c'], d['single'], d['digest']))
        else:
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s","%s",0x%x,{0},0,%d,0ULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'],
                                                                                d['error'], d['fail'], d['single']))
    tables = [BEGIN]
    tables.append('const std::uint32_t STARTS[]={%s};' % ','.join('0x%x' % x for x in STARTS))
    tables.append('const std::uint32_t CONSUMERS[][3]={%s};' % ','.join('{0x%x,0x%x,0x%x}' % (c, SUCC[c][0], SUCC[c][1]) for c in CONSUMERS))
    tables.append('const unsigned int EVEN_COUNT=%d;' % sum((hi - lo) // 2 for lo, hi in RANGES))
    tables.append('const Fixture FIXTURES[]={')
    tables += out
    tables.append('};')
    tables.append('const Synthetic SYNTHETIC[]={')
    tables += [' {0x%x,"%s"},' % (a, b.hex()) for a, b in SYN]
    tables.append('};')
    tables.append(END)
    text = TEST.read_text()
    i = text.index(BEGIN)
    j = text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(tables) + text[j:])
    singles = [d for d in ROWS if d['single'] == 1]
    print('rows', len(ROWS), 'single', len(singles), 'path', sum(1 for d in ROWS if d['single'] == 0), 'chain', sum(1 for d in ROWS if d['single'] == 2),
          'cons', sum(1 for d in ROWS if d['single'] == 3), 'error', sum(1 for d in ROWS if d['single'] == 4))
    entered = set(d['entry'] for d in singles)
    print('starts without single', [hex(s) for s in STARTS if s not in entered and s not in CONS_SET])
    succ = {}
    for d in singles:
        succ.setdefault(d['entry'], set()).add(d['stop'])
    one = []
    for s in STARTS:
        if s in CONS_SET or s not in succ:
            continue
        nxt = B.static_next(s)
        if nxt is not None and len(nxt) > 1 and not nxt <= succ[s]:
            one.append((hex(s), sorted(hex(x) for x in nxt - succ[s])))
    print('branch blocks with a missing successor', one)
    print('chain rows', sorted(set((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2)))
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
