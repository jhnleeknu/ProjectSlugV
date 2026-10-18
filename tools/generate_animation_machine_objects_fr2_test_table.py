"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr2_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data; only data areas, never
code bytes): the BYTE tables 1c1c0..1c1f4 and 1c238..1c278 (1c1f4), the item records b3894..b3dbc (b4680 b46a2 b442e b4440 e62ce; handler LONG 4 =
b445e / b4374 / b43d8 (unit blocks with a known C) or the RAM probe 10fe40), the LONG table b433c..b4354 (b4354 / b437a / 10fe40), the box pointer
table b4ad4..b4aec (-> RAM boxes 10e600..10e630), the WORD table b46f6..b4706 (b46c0) and the bank-window LONGs 2001c4 (-> 2a0700) / 20017c (-> 2a0800)
with the LONGs behind them.  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as is a run that lands
inside the unit on a PC that is not a block start.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent 10eb00, LONG 8(A6) = the sibling 10ec00), record
A0 = 10e400 (LONG 8c(A0) = 10e800), A1 = 10ea00, the player records 100cb8 / 100da8 (LONG 8c = 10e800), A4 = 10e800, A5 = 108000 (the RAM areas
5d48 5d50 5d5c 5d98 5dd4 538e 5e4a -ee -f2 -7ff2 of A5), the menu record LONG -ee(A5) = 10e900, the score BCDs 10de14..10de24, the rank table
10f02e..10f07e, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7, the declared stack values the entered block pops.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA exits, live JSR targets, the RTS sentinel).
  single 2  a consumer entered through its real producer (288c -> b3454; 289e -> b48e8; b4760 (b4aca, 1aa7e) -> b4a18; the table tests b4354 / b437a
            -> b478e b47b2 b491a; the item handler b445e / b4374 / b43d8 -> b46ac; 1c1f4 -> 1c230 -> the consumer b478e): stop = the consumer's
            successor; the native branch on the real flags decides it.  49fc6 runs ROM scripts: the passing RTS b433a has declared-C rows here.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).  The passing
            RTS b433a / 1c230 return to the consumer b478e (return LONG b478e): its native branch confirms the passed C.
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C.  The modelled C
of the producers: 1c1f4 (CMP.B D0,D1 borrow from the native final D0.B / D1.B; equal -> Clear), 1c232 b4374 b43d2 b4458 Set, b43d8 b445e Clear.
b47f4 recomputes the C of b47de (D1.W < D0.W) and b48ba the Z of TST.W (A1): their native direct entries set SR C / Z to that value (decision 4).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr2_test_table.py  (rewrites the generated section in place)
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
import fr2 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr2_test.cpp'
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
REC4, REC1, PARENT, SIBLING, MENU, BOXES = 0x10e800, 0x10ea00, 0x10eb00, 0x10ec00, 0x10e900, 0x10e600
PROBE = 0x10fe40
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
ITEMS = 0xb3894


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def bcd_long(rng):
    """A LONG of BCD digits (sometimes a non-decimal digit, sometimes the sign bit for TST.L)."""
    v = 0
    for _ in range(8):
        v = (v << 4) | (rng.randrange(10) if rng.random() < 0.85 else rng.randrange(16))
    return v


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    srng = random.Random(0xF42B)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    t1c0 = bytes(srng.randrange(4) for _ in range(4)) + bytes(srng.randrange(4) for _ in range(0x30))           # 1c1c0..1c1f4
    t238 = bytes(srng.getrandbits(8) for _ in range(0x40))                                                          # 1c238..1c278
    items = b''
    for k in range(0x6e):
        handler = (0xb445e, 0xb445e, 0xb445e, 0xb4374, 0xb43d8, PROBE)[k % 6] if k != 0x32 else 0xb445e
        items += bytes([srng.getrandbits(8), srng.getrandbits(8)]) + w(k) + l(handler) + l(bcd_long(srng) if k % 7 else (bcd_long(srng) | 0x80000000))
    table = b''.join(l(v) for v in (0xb4354, 0xb437a, PROBE, 0xb437a, 0xb4354, 0xb437a))                          # b433c..b4354
    boxes = b''.join(l(BOXES + 8 * k) for k in range(6))                                                           # b4ad4..b4aec
    words = b''.join(w(srng.getrandbits(16)) for _ in range(8))                                                    # b46f6..b4706
    return [(0x1c1c0, t1c0), (0x1c238, t238), (ITEMS, items), (0xb433c, table), (0xb46f6, words), (0xb4ad4, boxes),
            (0x2001c4, l(0x2a0700)), (0x2a0714, l(srng.getrandbits(19) << 1)), (0x20017c, l(0x2a0800)), (0x2a0808, l(srng.getrandbits(19) << 1))]


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
SUCC = {0xb3454: (0xb3458, 0xb345e), 0xb46ac: (0xb46b4, 0xb46bc), 0xb478e: (0xb4796, 0xb4792), 0xb47b2: (0xb47ba, 0xb47b6), 0xb48e8: (0xb4942, 0xb48ec),
        0xb491a: (0xb4942, 0xb4922), 0xb4a18: (0xb4a22, 0xb4a1c)}
assert set(SUCC) == CONS_SET


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


def cmp_carry(o):
    """1c1f4 (independent model of CMP.B D0,D1): C = the unsigned borrow of D1.B - D0.B (the native final registers)."""
    return 2 if (o['regs']['d1'] & 0xff) < (o['regs']['d0'] & 0xff) else 1


def carry_after(p, c, nxt=None, o=None):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set); o = the native run (for 1c1f4)."""
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in SET_SET:
        return 2
    if p in CLEAR_SET:
        return 1
    if p in DATA_SET:
        if nxt == 0x1c230:
            return 1
        assert o is not None
        return cmp_carry(o)
    return 0


def model(executed, carry, stop, o=None):
    """C along a path: a 1c1f4 inside the path is followed by 1c230 (its Clear) or 1c232 (ORI, not carry preserving: the borrow is overwritten)."""
    c = carry
    for i, p in enumerate(executed):
        nxt = executed[i + 1] if i + 1 < len(executed) else stop
        if p in DATA_SET and nxt != 0x1c230:
            assert i + 1 < len(executed), 'a path never ends right after 1c1f4 (both successors are unit blocks)'
            c = 0
            continue
        c = carry_after(p, c, nxt)
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
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x20, 0x3f, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xdf, 0xe0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 8, 9, 0xa, 0xb, 0x10, 0x24, 0x6d, 0x6e, 0x7f, 0x80, 0xff, 0x100, 0x58f, 0x590, 0x77f, 0x780, 0x7fff, 0x8000, 0x8001, 0xfff6, 0xfffe,
      0xffff)
VL = (0, 1, 0xf, 0x10, 0x7fff, 0x10000, 0x1ffff, 0x20000, 0x27fff, 0x28000, 0x50000, 0x7fffffff, 0x80000000, 0xc0000000, 0xfffd8000, 0xfffd7fff,
      0xfffffff0, 0xffffffff, 0x123456)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x8c}
# declared stack values the entered block pops (below the return LONG): (size, kind)
STACK = dict(B.STACK)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'scs'):
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


def item(rng):
    return ITEMS + 12 * rng.randrange(0x6e)


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, PLAYER1, PLAYER2, item(rng))),
                a1=rng.choice((REC1, REC1, CHILD)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=REC4, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 9, 0xa, 0xb, 0x20, 0x80, 0xff, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340004))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 7, 9, 0xa, 0xb, 0x32, 0x6d, 0x6e, 0x8000, 0xffff, 0x1234000a))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 1, 2, 3, 4, 7, 0x80, 0xff, 0x10003))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG and the node links are declared below
        if reg == 5 and disp in (-0xee, -0xf2):
            continue
        if reg in (0, 2) and disp == 0x8c:
            continue
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(PARENT + 0x61, 1, rand_val(rng, 1))
    r.put(PARENT + 0x62, 1, rand_val(rng, 1))
    for a in (PLAYER1, PLAYER2, CHILD):
        r.put(a + 0x42, 2, rand_val(rng, 2))
        r.put(a + 0x46, 2, rand_val(rng, 2))
        r.put(a + 0x8c, 4, REC4)
        r.put(a + 0x9e, 2, rng.getrandbits(16) & 0x0303)
    r.put(REC4 + 4, 1, rng.randrange(0x30))
    r.put(REC4 + 8, 2, rand_val(rng, 2))
    r.put(A5 - 0xee, 4, MENU)
    r.put(A5 - 0xf2, 4, rng.choice((MENU, REC1)))
    for off in (4, 9, 0xa, 0xb, 0xc):
        r.put(MENU + off, 1, rand_val(rng, 1) if off != 0xc else rng.choice((1, 2, 3, 0x10, 0x80, 0xff, rng.getrandbits(8) | 1)))
    r.put(0x10000e, 2, rand_val(rng, 2))
    r.put(NODE + 0x90, 2, rng.choice((0, 0, 4, 8, 0xc, 0x10, 0x14)) if rng.random() < 0.9 else rand_val(rng, 2) & 0xfffe)
    for lst in (0x10dd48, 0x10dd50):
        r.put(lst, 2, rng.choice((0x8000, 0x8000, rand_val(rng, 2))))
        r.put(lst + 2, 4, rand_val(rng, 4))
        r.put(lst + 6, 2, rand_val(rng, 2))
    for k in range(6):
        r.put(BOXES + 8 * k, 2, rand_val(rng, 2))
        r.put(BOXES + 8 * k + 2, 4, rand_val(rng, 4))
        r.put(BOXES + 8 * k + 6, 2, rand_val(rng, 2))
    for a in (0x10d3aa, 0x10d3ae, 0x10d3f2, 0x10d3f4, 0x10d3f6, 0x10d3f8):     # 538e(A5) 1c / 20, the 1aa7e screen limits 53f2..53f8(A5)
        r.put(a, 2, rand_val(rng, 2))
    for k in range(4):
        r.put(0x10de14 + 4 * k, 4, bcd_long(rng))
    for k in range(10):
        r.put(0x10f02e + 8 * k, 4, rng.choice((0, 0x1000, 0x5000, 0x10000, 0x99999999, rand_val(rng, 4))))
        r.put(0x10f032 + 8 * k, 4, rand_val(rng, 4))
    # the 10-byte records of 5d5c(A5) / 5d98(A5): WORD node low, LONG box pointer, LONG handler (a unit block with a known C); 0 ends the list
    for lst in (0x10dd5c, 0x10dd98):
        for k in range(rng.choice((0, 1, 2))):
            r.put(lst + 10 * k, 2, rng.choice((CHILD, SIBLING, PARENT)) & 0xffff)
            r.put(lst + 10 * k + 2, 4, rng.choice((REC1, CHILD)))
            r.put(lst + 10 * k + 6, 4, rng.choice((0xb445e, 0xb4374, 0xb43d8)))
    for a in (CHILD, SIBLING, PARENT):
        r.put(a, 4, rng.choice((0x270e, 0x270e, rand_val(rng, 4))))
    r.put(0x10de4a, 2, rand_val(rng, 2))
    if rng.random() < 0.5:
        r.put(NODE + 0x8c, 2, rng.choice((0, 1, 2, 0x24)))
    pops = []
    for size, kind in STACK.get(s, ()):
        n = 4 if size == 'L' else 2
        v = {'node': rng.choice((CHILD, REC1)), 'a6': NODE, 'item': item(rng), 'small': rng.choice((0, 1, 2, 3, 9, 0xa)), 'any': rand_val(rng, n)}[kind]
        pops.append((n, v))
    depth = sum(n for n, v in pops)
    at = SP - depth
    for n, v in pops:
        r.put(at, n, v)
        at += n
    regs['a7'] = SP - depth
    # per-entry constraints: the RAM targets of writes / copies, the DIVU divisor, the loop counters
    if s in (0xe63f2, 0xe63ec):
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1, 2, 8))
        regs['a0'] = rng.choice((0x10f02e, CHILD))
        regs['a1'] = rng.choice((0x10f036, REC1))
    if s in (0xe62ce, 0xe62e0):
        regs['a1'] = rng.choice((0x10de1c, 0x10de24, REC1 + 4))
        regs['a0'] = item(rng) + 8
    if s in (0xe9922, 0xe9930, 0xe993c, 0xe9942, 0xe9952, 0xe9956, 0xe9b72, 0xe694c, 0xe55ae, 0xe55d0, 0xe6516, 0xb4436, 0xb4440, 0xb442e):
        regs['a0'] = rng.choice((CHILD, REC1)) if s not in (0xb4436, 0xb4440, 0xb442e) else item(rng) + 8
        if s in (0xe9942, 0xe9930, 0xe993c, 0xe9952):
            regs['a1'] = CHILD + 0x76
            regs['d7'] = (regs['d7'] & 0xffff0000) | rng.choice((0, 1, 7))
    if s == 0xe9b72:
        regs['a5'] = A5
    if s in (0xb4380,):
        regs['a0'] = BOXES + 8 * rng.randrange(6)
    if s in (0xb4388, 0xb4396, 0xb439a, 0xb43ac, 0xb43ba, 0xb43be):
        regs['a1'] = BOXES + 8 * rng.randrange(6) + (0 if s == 0xb4388 else rng.choice((6, 8)))
        regs['a0'] = rng.choice((0x10dd48, 0x10dd50, 0x10ddd4))
    if s in (0xb4354, 0xb4364):
        regs['a0'] = rng.choice((0x10dd48, 0x10dd50, 0x10ddd4)) + (0 if s == 0xb4354 else 6)
    if s in (0xb48b8, 0xb48ba, 0xb48be, 0xb48ca, 0xb48d2, 0xb48d6, 0xb48dc, 0xb48ec, 0xb4922, 0xb4942):
        regs['a1'] = rng.choice((0x10dd5c, 0x10dd98, 0x10dd66, 0x10dda2))
    if s == 0xb4922:                                    # the list record's handler LONG 6(A1) is the RAM probe (a live target stop)
        r.put(regs['a1'], 2, rng.choice((CHILD, SIBLING, PARENT)) & 0xffff)
        r.put(regs['a1'] + 6, 4, rng.choice((0xb445e, 0xb4374, 0xb43d8)))     # work RAM is not executable natively: unit producers as handlers
    if s == 0xb48d6 and rng.random() < 0.3:
        regs['a2'] = regs['a1']
    if s in (0xb4680,) and rng.random() < 0.8:
        regs['d1'] = (regs['d1'] & 0xffff0000) | rng.randrange(0x6e)
    if s in (0xb46a2, 0xb469e, 0xb4694):
        regs['a0'] = item(rng)
    if s == 0xa7ac and (regs['d2'] & 0xffff) == 0:
        regs['d2'] |= rng.choice((1, 3, 0x10, 0xff))   # DIVU zero divisor: error rows
    if s in (0x1c1f4,):
        regs['a0'] = rng.choice((CHILD, PLAYER1, PLAYER2))
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(3)
    if s in (0x1c8ce, 0x1c8e8):
        regs['a0'] = rng.choice((PLAYER1, PLAYER2))
    if s in (0xe9b72,) and rng.random() < 0.8:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(8)
    if hint:
        for a, n, v in hint.get('puts', []):
            r.put(a, n, v)
        regs.update(hint.get('regs', {}))
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the RTS sentinel, the TRAP boundaries and the RAM live target
ALLOWED_STOPS = {0x1aa3a, 0x1aa7e, 0x288c, 0x289e, 0x28ae, 0x2986, 0x2a00, 0x3af8, 0x43e34, 0x43ea4, 0x49260, 0x49290, 0x49a58, 0x49f8c, 0x49fc6,
                 0xc6a96, 0xcd58, STOP, 0xb466c, 0xe6570, PROBE}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p)


def hints(s):
    h = []
    N = lambda o, n, vals: [dict(puts=[(NODE + o, n, v)]) for v in vals]
    R = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if s == 0xe5580:
        h += N(0x80, 2, (0, 9, 0xa, 0xb, 0x8000, 0xffff))
    if s == 0xe5596:
        h += N(0x7a, 2, (0, 1, 2, 0x8000))
    if s == 0xe55e2:
        h += N(0x62, 1, (0, 1, 0x80, 0xff))
    if s in (0xe55ec, 0xe55ae):
        h += N(0x7c, 2, (0, 1, 0x8000))
    if s in (0xc0b04, 0xb4388, 0xb43ac):
        h += N(0x15, 1, (0, 1, 2, 3, 0xfe, 0xff))
    if s == 0xc0b58:
        h += N(0x3a, 4, (0x1ffff, 0x20000, 0x7fffffff, 0x80000000, 0xffffffff, 0))
    if s == 0xc0b6e:
        h += N(0x36, 4, (0x27fff, 0x28000, 0xfffd8000, 0xfffd7fff, 0x7fffffff, 0xffffffff))
    if s == 0xc0b64:
        h += N(0x3a, 4, (0x80000000, 0xffffffff, 0x7fffffff, 0xf, 0xfffffff0, 0x10))
    if s == 0xc0b82:
        h += N(0x36, 4, (0x80000000, 0xffffffff, 0x7fffffff, 0xf, 0xfffffff0, 0x10))
    if s == 0xc0b0e:
        h += N(0x36, 4, (0, 1, 0x80000000, 0xffffffff))
    if s in (0xc0ad6, 0xc0aec):
        h += R('d0', (0, 0x7fff, 0x8000, 0xffff, 0x1234ffff))
    if s == 0xc0b98:
        h += R('d0', (0, 4, 0xfb, 0x12345604))
    if s in (0xb4958, 0xb49f2):
        h += N(0x95, 1, (0, 8, 0x10, 0x18, 0xff))
    if s in (0xb4962, 0xb496c):
        h += N(0x12, 1, (0, 0x3f, 0x40, 0x7f, 0xc0, 0xdf, 0xe0, 0xfe, 0xff))
    if s in (0xb4980, 0xb498a):
        h += N(0x13, 1, (0, 0x3f, 0x40, 0x7f, 0xc0, 0xdf, 0xe0, 0xfe, 0xff))
    if s == 0xb499e:
        h += N(0x96, 1, (0, 4, 0xfb, 0xff))
    if s in (0xb49a8, 0xb49b0):
        h += N(0x94, 1, (0, 1, 0x80, 0xff))
    if s in (0xb49c2, 0xb49c8):
        h += R('d7', (0, 1, 2, 3, 4, 0x80, 0xffffff00))
    if s == 0xb49e4:
        h += N(0x8c, 2, (0, 1, 2, 0x8000, 0xffff))
    if s == 0xb49ec:
        h += R('d0', (0, 1, 2, 0x10000, 0x10001))
    if s == 0xb49fc:
        h += N(0x61, 1, (0, 8, 0xf7, 0xff))
    if s == 0xb4664:
        h += R('d1', (0, 0x6d, 0x6e, 0x8000, 0xffff, 0x1230006d))
    if s == 0xb4680:
        h += R('d1', (0, 1, 0x32, 0x6d, 0x12340000))
    if s in (0xb46a2,):
        h += [dict(regs=dict(a0=ITEMS + 12 * k)) for k in (0, 3, 4, 5, 0x32)]
    if s in (0xb442e, 0xb4436, 0xb4440):
        h += [dict(regs=dict(a0=ITEMS + 12 * k + 8)) for k in (0, 1, 7, 0x32, 0x6d)]
    if s == 0xb46c0:
        h += R('d1', (0, 7, 8, 0xffff, 0x12340003)) + R('d0', (0, 1, 0x100))
    if s == 0xb476a:
        h += R('d7', (0, 4, 0xfb, 0x12345604))
    if s in (0xb4772, 0xb4796):
        h += [dict(puts=[((0x10dd48 if s == 0xb4772 else 0x10dd50), 2, v)]) for v in (0x8000, 0, 0x7fff, 0x8001)]
    if s == 0xb47ba:
        h += R('d7', (0, 1, 2, 3, 0x103, 0xffffff03))
    if s in (0xb47c2, 0xb47d0):
        h += [dict(puts=[(NODE + 0x42, 2, b), ((0x10dd48 if s == 0xb47c2 else 0x10dd50), 2, a)]) for a, b in
              ((0, 0), (5, 3), (3, 5), (0x8000, 0), (0, 0x8000), (0x7fff, 0xffff))]
    if s in (0xb47ce, 0xb47dc):
        h += R('d0' if s == 0xb47ce else 'd1', (0, 1, 0x8000, 0xffff, 0x12348000))
    if s == 0xb47de:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (5, 5), (3, 5), (5, 3), (0x12340005, 0x56780005), (0x8000, 0x7fff))]
    if s == 0xb47f4:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (3, 5), (5, 3), (0x7fff, 0x8000), (0x8000, 0x7fff), (0x12340001, 0x00000001))]
    if s in (0xb47ea,):
        h += R('d0', (0, 1, 2, 0xff, 0x12345601))
    if s in (0xb489e, 0xb48be):
        h += [dict(puts=[(0x10000e, 2, v)]) for v in (0, 1, 2, 0xffff)]
    if s in (0xb48b8, 0xb48ba, 0xb4942):
        h += [dict(regs=dict(a1=0x10dd5c), puts=[(0x10dd5c + (0xa if s == 0xb4942 else 0), 2, v)]) for v in (0, 1, 0x8000)]
    if s == 0xb48d6:
        h += [dict(regs=dict(a1=a, a2=b)) for a, b in ((0x10dd98, 0x10dd98), (0x10dd98, 0x10ddd4), (0x10dd5c, 0x10dd98))]
    if s == 0xb4936:
        h += R('d0', (0, 1, 0xffff))
    if s in (0xb4354, 0xb4364):
        h += [dict(puts=[(NODE + 0x4a, 2, v)]) for v in (0, 1, 0x8000, 0xffff)]
    if s in (0xb4396, 0xb439a, 0xb43ba, 0xb43be):
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (1, 0), (0, 1), (0x8000, 0x7fff), (0xffff, 0), (0x12340000, 0x5678ffff))]
    if s == 0x1c8ac:
        h += R('d0', (0, 0x20, 0xffdf, 0x12340020))
    if s == 0x1c8ba:
        h += R('d0', (0, 1, 2, 3, 0xfffe))
    if s == 0x1c8ce:
        h += [dict(regs=dict(a0=p), puts=[(REC4 + 8, 2, v)]) for p in (PLAYER1, PLAYER2) for v in (0, 0x58f, 0x590, 0xfe10, 0xffff)]
    if s == 0x1c1f4:
        h += [dict(regs=dict(d0=v, a0=CHILD), puts=[(CHILD + 0x9f, 1, f)]) for v in (0, 1, 2) for f in (0, 1, 0x80, 0xff)]
    if s in (0xe62a8, 0xe62ba):
        h += R('d0', (0, 1, 2, 3, 0xfffffffc))
    if s == 0xe62ce:
        h += [dict(regs=dict(a0=ITEMS + 12 * k + 8, a1=0x10de1c), puts=[(0x10de18, 4, v)]) for k in (0, 0x32) for v in (0, 0x99999999, 0x12345678,
                                                                                                                         0xaaaaaaaa, 0x09090909)]
    if s == 0xe63ec:
        h += R('d0', (0, 1, 2, 0x10000))
    if s == 0xe63f2:
        h += R('d0', (0, 1, 0x10000))
    if s in (0xe6522, 0xe652e):
        h += [dict(regs=dict(d3=a, d4=b)) for a, b in ((0, 0), (1, 0), (0, 1), (0x80000000, 0x7fffffff), (0xffffffff, 0))]
    if s in (0xe6538, 0xe6540, 0xe65b0, 0xe65ba, 0xe6552):
        h += R('d1', (0, 9, 0xa, 0xb, 0x7fff, 0x8000, 0xffff, 0x1234000a))
    if s in (0xe655c, 0xe6568):
        h += R('d0', (0, 9, 0xa, 0xb, 0x7fff, 0x8000, 0xffff, 0x1234000a))
    if s == 0xe658c:
        h += [dict(puts=[(SP - 12, 4, a), (SP - 8, 4, b)]) for a, b in ((0, 0), (1, 1), (3, 2), (0x10003, 3))]
    if s in (0xe659a, 0xe65c2):
        h += R('d0' if s == 0xe659a else 'd1', (0, 1, 2, 9, 0xa, 0x12340005))
    if s == 0xe9930:
        h += R('d3', (0, 0xf0000000, 0x12345678, 0x0fffffff))
    if s == 0xe993c:
        h += R('d6', (0, 1, 2, 0x7f, 0x80, 0x81, 0xff))
    if s == 0xe9942:
        h += R('d5', (0, 1, 9, 0xf, 0x55, 0xff))
    if s == 0xe9952:
        h += R('d4', (0, 1, 0x10000, 0xffff))
    if s == 0xa77a:
        h += R('d7', (0, 1, 0x100, 0xff))
    if s == 0xa796:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x1fff, 0x1fff), (0xffff, 0x40), (0x12345678, 0x9abcdef0))]
    if s == 0xa7ac:
        h += [dict(regs=dict(d1=a, d2=b)) for a, b in ((0xff, 1), (0x80, 0x100), (0xffff, 1), (0xffff, 0xff), (0x7f, 0x101), (0, 5), (0x12340080, 0xabcd0001))]
    if s == 0xa7c0:
        h += R('d1', (0, 0x80, 0x10000))
    if s == 0x9ee6:
        h += [dict(puts=[(A5 - 0xf2, 4, MENU)]), dict(puts=[(A5 - 0xf2, 4, REC1)])]
    if s in (0x9ef8, 0x9f12):
        h += [dict(puts=[(MENU + 4, 1, 0xff), (MENU + 0xb, 1, 0x80), (MENU + 0xc, 1, 0xff), (MENU + 9, 1, 0x7f), (MENU + 0xa, 1, 0x81)])]
    if s in (0xb33d8, 0xb33e2, 0xc0b12, 0xa8ee, 0xa770, 0xe9b5a, 0xe693a, 0xb4436):
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
            if (nxt in CONS_SET and s not in DATA_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
                continue                                # a wild live target (random RAM LONG) is not a declared stop
            key = (nxt, 'h%d' % t) if hint else nxt
            if key in kept:
                continue
            if nxt == s:
                continue                                # e63f2 DBRA back to itself: a zero-step stop; the loop is covered by the path rows
            if not hint and sum(1 for k in kept if (k[0] if isinstance(k, tuple) else k) == nxt) >= 2:
                continue
            kept[key] = (r, regs, o)
            if t >= len(hs) and len(kept) >= 6:
                break
            if t >= len(hs) and t > 120 and len(kept) >= 2:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, o['stop'], o), 1, o)


PATH_ENTRIES = (0xc0ace, 0xc0b04, 0xc0b52, 0xc0b58, 0xc0b6e, 0xc0b8c, 0xc0b98, 0xb4958, 0xb4962, 0xb499e, 0xb49c2, 0xb49e4, 0xb49fc, 0xb4664, 0xb4680,
                0xb442e, 0xb4436, 0xb4440, 0xb476a, 0xb4772, 0xb47ba, 0xb47c2, 0xb489e, 0xb48b8, 0xb48be, 0xb4942, 0xb4354, 0xb437a, 0xb4388, 0xb46c0,
                0xe5580, 0xe5596, 0xe55ae, 0xe55e2, 0xe55ec, 0xe6556, 0xe6516, 0xe6522, 0xe655c, 0xe6582, 0xe6584, 0xe65b0, 0xe63ec, 0xe62a8, 0xe62ce,
                0xe9922, 0xe9930, 0xe991c, 0xb33d8, 0xb343a, 0xa8ee, 0xa770, 0xa77a, 0xa7ac, 0x9ee6, 0x9ef8, 0x1c8a4, 0x1c8ac, 0x1c8ba, 0x1c8ce, 0x1c1f4)


def gen_paths(rng):
    fl = []
    for b in STARTS:
        fl += fields(b)
    fl = sorted(set(fl))
    for s in PATH_ENTRIES:
        kept = {}
        for t in range(240):
            carry = rng.choice((0, 1, 2))
            r, regs = world(rng, fl, s)
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
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, o['stop'], o), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=REC1, a2=PLAYER1, a3=PLAYER2, a4=0xa4a4a4a4, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry):
    """A world for a real producer chain (288c / 289e / 1aa7e / the table tests / the item handler / 1c1f4)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d7=rng.getrandbits(32)))
    if entry == 0xb344e:
        v = rng.choice((0, PARENT, PARENT))
        r.put(NODE + 0xc, 4, v)
        r.put(PARENT, 4, rng.choice((0x270e, 0x270f)))
    if entry == 0xb48dc:
        regs['a1'] = 0x10dd5c
        r.put(0x10dd5c, 2, CHILD & 0xffff)
        r.put(CHILD, 4, rng.choice((0x270e, 0x2b99c)))
    if entry in (0xb4780, 0xb47a4, 0xb48ec):
        r.put(NODE + 0x90, 2, rng.choice((0, 4, 0xc, 0x10, 0x14)))
        r.put(NODE + 0x4a, 2, rng.choice((0, 0x10, 0x100, 0xff00, rng.getrandbits(16))))
        r.put(NODE + 0x4e, 2, rng.choice((0, 0x10, 0x100, 0xff00, rng.getrandbits(16))))
        r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
        for lst in (0x10dd48, 0x10dd50, 0x10ddd4):
            r.put(lst, 2, rng.choice((0, 0x10, 0xfff0, rng.getrandbits(16))))
            r.put(lst + 2, 4, rng.choice((0x00100010, 0x7fff7fff, 0, rng.getrandbits(32))))
            r.put(lst + 6, 2, rng.choice((0, 0x20, 0x7fff, rng.getrandbits(16))))
        if entry == 0xb48ec:
            regs['a1'] = 0x10dd5c
            regs['a0'] = CHILD
            r.put(0x10dd5e, 4, REC1)
    if entry == 0xb46a2:
        regs['a0'] = ITEMS + 12 * rng.choice((0, 3, 4, 0x32))      # handlers b445e (Clear) / b4374 (Set) / b43d8 (Clear)
    if entry == 0xb4a14:
        r.put(NODE + 0x90, 2, rng.choice((0, 4, 8, 0xc)))
        for off in (0x42, 0x46, 0x4a, 0x4e):                     # 1aa7e: the node position against its reference and the screen limits
            r.put(NODE + off, 2, rng.choice((0, 0x10, 0x100, 0x7fff, 0x8000, 0xff00, rng.getrandbits(16))))
        r.put(NODE + 0x15, 1, rng.choice((0, 2)))
        for a in (0x10d3f2, 0x10d3f4, 0x10d3f6, 0x10d3f8):
            r.put(a, 2, rng.choice((0, 0x40, 0x140, 0x7fff, 0x8000, rng.getrandbits(16))))
    if entry in (0x1c1f4,):
        regs['a0'] = CHILD
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(3)
        r.put(SP, 4, 0xb478e)                                     # 1c230 / 1c232 return to the consumer b478e
    return r, regs


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            pops = {0xb46ac: ((4, 0x11112222), (4, ITEMS)), 0xb491a: ((4, 0x10dd5c),)}.get(cp, ())
            depth = sum(n for n, v in pops)
            at = SP - depth
            for n, v in pops:
                r.put(at, n, v)
                at += n
            regs['a7'] = SP - depth
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # the passing RTS b433a / 1c230 entered with a declared C return to the consumer b478e (return LONG b478e): its native branch confirms the C
    for pp in sorted(PASS_SET):
        for carry in (1, 2):
            r = base_ram()
            r.put(SP, 4, 0xb478e)
            regs = dict(PLAIN)
            o = native(r.b, regs, pp, carry, lambda p, tr: p in (0xb4796, 0xb4792))
            assert o is not None and o['stop'] == (0xb4796 if carry == 1 else 0xb4792), (hex(pp), carry)
            row('pass-%x-c%d' % (pp, carry), r, regs, pp, o['stop'], carry, carry, 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in ((0xb344e, 0xb3454), (0xb48dc, 0xb48e8), (0xb4a14, 0xb4a18), (0xb4780, 0xb478e), (0xb47a4, 0xb47b2), (0xb48ec, 0xb491a),
                        (0xb46a2, 0xb46ac), (0x1c1f4, 0xb478e)):
        clr, st = SUCC[cons]
        seen = {}
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st))
            if o is None or cons not in o['trace'] or (o['stop'] in seen and seen[o['stop']] >= 3):
                continue
            if entry == 0x1c1f4 and 0x1c230 not in o['trace'] and 0x1c232 not in o['trace']:
                continue
            seen[o['stop']] = seen.get(o['stop'], 0) + 1
            c = 1 if o['stop'] == clr else 2
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, c, 2, o)
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        assert set(seen) == {clr, st}, (hex(entry), seen)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=0, a3=0, a4=REC4, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    unrouted = 'unsupported animation machine PC'
    unaligned = 'unaligned animation machine PC'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr2 caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node / record / stack: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-e558a', 0xe558a, wodd, 0xe558a, stop=0xe5596, a6=NODE + 1)
    err('odd-node-e5580', 0xe5580, odd, 0xe5580, stop=0xe558a, a6=NODE + 1)
    err('odd-node-c0b58', 0xc0b58, odd, 0xc0b58, stop=0xc0b6e, a6=NODE + 1)
    err('odd-record-b442e', 0xb442e, odd, 0xb442e, stop=0xb4436, a0=ITEMS + 9)
    err('odd-record-b46a2', 0xb46a2, odd, 0xb46a2, stop=0xb46ac, a0=ITEMS + 1)
    err('odd-stack-e6556', 0xe6556, odd, 0xe6556, stop=0xe6516, a7=SP + 1)
    err('odd-stack-b494c', 0xb494c, odd, 0xb494c, a7=SP + 1)
    err('odd-box-b4354', 0xb4354, odd, 0xb4354, stop=0xb4364, a0=0x10dd49)
    err('odd-list-b48ba', 0xb48ba, odd, 0xb48ba, stop=0xb48be, a1=0x10dd5d)
    # DIVU zero divisor (a7ac)
    err('a7ac-divu-zero', 0xa7ac, 'objects fr2 DIVU zero divisor', 0xa7ac, stop=0xa7c2, d1=0xff, d2=0x12340000)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('b4680-items-rom', 0xb4680, missing, 0xb4680, stop=0xb46a2, d1=0x7000)
    err('b4780-table-rom', 0xb4780, missing, 0xb4780, stop=0xb478e, puts=[(NODE + 0x90, 2, 0x18)])
    err('b4aca-boxes-rom', 0xb4aca, missing, 0xb4aca, puts=[(NODE + 0x90, 2, 0x18)])
    # TRAP #15 boundaries b466c (item index >= 6e) / e6570 (rank > a); the live JSR (A1) target in RAM (item handler 10fe40 of record 5)
    err('b4664-trap', 0xb4664, unrouted, 0xb466c, d1=0x6e)
    err('e6568-trap', 0xe6568, unrouted, 0xe6570, d0=0xb)
    err('b46a2-live-ram', 0xb46a2, unrouted, PROBE, a0=ITEMS + 12 * 5)
    err('b4780-live-ram', 0xb4780, unrouted, PROBE, stop=0xb478e, puts=[(NODE + 0x90, 2, 8)])
    err('b4922-live-odd', 0xb4922, unaligned, 0x10e401, stop=0xb4936, a1=0x10dd5c, puts=[(0x10dd5c, 2, 0xe400), (0x10dd62, 4, 0x10e401)])
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   b476a (D7 bit 2 clear) -> b4772 (10dd48 = 8000) -> b4796 (10dd50 = 8000) -> b47ba (D7.B != 3) -> b4804 RTS at an odd A7
    err('b476a-then-b4804', 0xb476a, odd, 0xb4804, puts=[(0x10dd48, 2, 0x8000), (0x10dd50, 2, 0x8000)], a7=SP + 1)
    #   e63ec (D0.W = 0) -> e63f8 RTS at an odd A7
    err('e63ec-then-e63f8', 0xe63ec, odd, 0xe63f8, a7=SP + 1)
    #   c0b98 (D0 bit 2 clear) -> c0ba0 JSR b4334 at an odd A7
    err('c0b98-then-c0ba0', 0xc0b98, odd, 0xc0ba0, stop=0xb4334, a7=SP + 1)
    #   b499e (BYTE 96 bit 2 set) -> b49e4 MOVE.W 8c(A6) at an odd A6
    err('b499e-then-b49e4', 0xb499e, odd, 0xb49e4, stop=0xb49ec, a6=NODE + 1, puts=[(NODE + 0x97, 1, 4)])
    #   1c8ba (D0 bit 0 clear) -> 1c8ce ADDI.W #1f0,8(A4) with LONG 8c(100cb8) odd
    err('1c8ba-then-1c8ce', 0x1c8ba, odd, 0x1c8ce, stop=0x1c8ee, puts=[(PLAYER1 + 0x8c, 4, REC4 + 1)])
    #   a8ee -> a770 -> a772 MOVE.L D7,-(A7) at an odd A7
    err('a8ee-then-a772', 0xa8ee, odd, 0xa772, stop=0x9ee6, a7=SP + 1)
    #   e62a8 (D0 bit 0 set) -> e62b0 BSR e62ce at an odd A7
    err('e62a8-then-e62b0', 0xe62a8, odd, 0xe62b0, stop=0xe62ce, d0=1, a7=SP + 1)


def main():
    rng = random.Random(0xF42A)
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
    print('data-C rows', sorted(set((hex(d['entry']), hex(d['stop']), d['c']) for d in singles if d['entry'] in DATA_SET)))


if __name__ == '__main__':
    main()
