"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr1c_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data): the two rectangles
d13a4..d13b4 (1ab80 of d155a, 4941e through d1432 / 494c0), the bank-window LONGs 200140 (-> 2a0400) / 200090 (-> 2a0500) / 20008c (-> 2a0600) with
the LONGs behind them (2a0404..2a0494, 2a0514, 2a0614).  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes
there), as is a run that lands inside the unit on a PC that is not a block start.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent record 10eb00, LONG 8(A6) = the sibling
10ec00), record A0 = 10e400, the RAM
rectangle A1 = 10ea00 (or the synthetic d13ac), A2 / A3 = the player records 100cb8 / 100da8, A4 = 10e800, A5 = 108000 (BYTE 568e(A5) for 49370,
BYTE 5b86(A5) for 4b6f4), WORD 10000e, the 28ae free list (WORD 104ca0, LONG 104c9c -> 10c000), seeded BYTE / WORD / LONG field edits (sign
boundaries included), seeded D0-D7, the declared stack LONG (the pushed rectangle pointer) for 494ca / 49508.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA exits, the RTS sentinel).
  single 2  a consumer entered through its real producer (28ae -> bc79e; 49370 -> 494c6; 4941e -> 494e6 494fc; 494c0 (49370, 4941e, N08 49462) ->
            d143c; 4b6f4 -> d153a; 1ab80 -> d156a): stop = the consumer's successor; the native branch on the real flags decides it.  49fc6 runs ROM
            scripts: its consumers bc1f6 bc338 bc394 bc6a2 bc6de bc74e bc78a have declared-C rows here (real chains in V1).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).  49458
            (EORI.B #1,CCR; RTS) returns to the consumer 494e6 (return LONG 494e6): the stop is 494ea (C Set after the inversion) or 494ee (Clear).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C.  The modelled C
of the producers: 49432 (CMP.W borrow: successor 49458 -> Clear, 4943e -> Set), 49452 (CMP.W 4(A1),D7 borrow, computed here from the native D7.W and
the WORD 4(A1): an independent Python model), 49458 (the inverted incoming C), bc7b0 (ORI) Set.  bc3aa recomputes the Z of bc398 from WORD 76(A6): its
native direct entry sets SR Z = (WORD 76 = 0) (contract decision 4).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr1c_test_table.py  (rewrites the generated section in place)
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
import fr1c as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr1c_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
SET_SET, DATA_SET, INVERT_SET = set(B.SET_SET), set(B.DATA_SET), set(B.INVERT_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC4, REC1, PARENT, SIBLING = 0x10e800, 0x10ea00, 0x10eb00, 0x10ec00
FREE = 0x10c000
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
RECT = 0xd13ac


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xF41C)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    rects = w(0xffe0) + w(0xff80) + w(0x0040) + w(0x00a0) + w(0xff00) + w(0xfe00) + w(0x0200) + w(0x0400)    # d13a4..d13b4 (two rectangles)
    anim = b''.join(l(srng.getrandbits(19) << 1) for _ in range(0x26))                                        # 2a0400..2a0498 (LONGs 0..94)
    return [(0xd13a4, rects), (0x200140, l(0x2a0400)), (0x200090, l(0x2a0500)), (0x20008c, l(0x2a0600)), (0x2a0400, anim),
            (0x2a0514, l(srng.getrandbits(19) << 1)), (0x2a0614, l(srng.getrandbits(19) << 1))]


SYN = synthetic()


def load_program():
    program = bytearray(ob.load_rom())
    assert hashlib.sha256(program).hexdigest() == '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    for a, b in SYN:
        program[a:a + len(b)] = b
    return bytes(program)


PROGRAM = load_program()
FIXED = (ctypes.c_ubyte * 0x100000).from_buffer_copy(PROGRAM[:0x100000])


def syn_ok(address, size):
    return any(a <= address and address + size <= a + len(b) for a, b in SYN)


# consumer -> (C clear successor, C set successor); 49458 runs its RTS to the consumer 494e6 (return LONG 494e6): clear -> inverted Set -> 494ea
SUCC = {0xbc1f6: (0xbc200, 0xbc1fa), 0xbc338: (0xbc342, 0xbc33c), 0xbc394: (0xbc402, 0xbc398), 0xbc6a2: (0xbc6ac, 0xbc6a6), 0xbc6de: (0xbc6e8, 0xbc6e2),
        0xbc74e: (0xbc758, 0xbc752), 0xbc78a: (0xbc7c0, 0xbc78e), 0xbc79e: (0xbc7b4, 0xbc7a2), 0x494c6: (0x494ca, 0x49508), 0x494e6: (0x494ee, 0x494ea),
        0x494fc: (0x49504, 0x49500), 0x49458: (0x494ea, 0x494ee), 0xd143c: (0xd144c, 0xd1440), 0xd153a: (0xd1544, 0xd153e), 0xd156a: (0xd1574, 0xd156e)}
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
    if pc in B.Z_RECOMPUTE and word_of(ram, NODE + B.Z_RECOMPUTE[pc]) == 0 and regs['a6'] == NODE:
        sr |= 4                                     # bc3aa: Z of bc398 = (WORD 76(A6) = 0), the recomputation the C++ does (decision 4)
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
        return None                                 # FR1c writes no PVC port
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


def box_carry(o):
    """49452 (independent model of SUB.W (A1),D7; CMP.W 4(A1),D7): C = the unsigned borrow of the final D7.W against WORD 4(A1)."""
    return 2 if (o['regs']['d7'] & 0xffff) < word_of(o['ram'], (o['regs']['a1'] + 4) & 0xffffff) else 1


def carry_after(p, c, nxt=None, o=None):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set); nxt = the next PC, o = the native run (for 49452)."""
    if p in INVERT_SET:
        return 3 - c if c else 0
    if p in CONS_SET:
        return c
    if p in SET_SET:
        return 2
    if p == 0x49432:
        return 1 if nxt == 0x49458 else 2
    if p == 0x49452:
        assert o is not None
        return box_carry(o)
    return 0


def model(executed, carry, stop):
    c = carry
    for i, p in enumerate(executed):
        nxt = executed[i + 1] if i + 1 < len(executed) else stop
        assert p != 0x49452, 'paths through 49452 end in the consumer 49458 (excluded)'
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
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x20, 0x21, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 0x10, 0x1f, 0x20, 0x40, 0x50, 0x60, 0x61, 0x70, 0x78, 0x79, 0x7f, 0x80, 0x9c, 0x9d, 0xff, 0x100, 0x140, 0x1a0, 0x1a1, 0x200,
      0x7fff, 0x8000, 0x8001, 0xfec0, 0xff00, 0xffbf, 0xffc0, 0xffe0, 0xffff)
VL = (0, 1, 0x1f, 0x20, 0x7fff, 0x10000, 0x18000, 0x30000, 0x7fffffff, 0x80000000, 0xc0000000, 0xfff00000, 0xfff40000, 0xfffd8000, 0xffffffe0, 0xffffffff,
      0x123456)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22}
STACK_LONG = set(B.STACK_LONG)
RECT_BLOCKS = set(B.RECT_BLOCKS)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st'):
            sz = 1
        for m in HX.finditer(op):
            disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
            out.append((int(m.group(3)), disp, sz))
    if s in RECT_BLOCKS:
        out += [(1, 0, 2), (1, 2, 2), (1, 4, 2), (1, 6, 2)]
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, PLAYER1, PLAYER2)),
                a1=rng.choice((REC1, REC1, RECT)), a2=PLAYER1, a3=PLAYER2, a4=REC4, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 5, 0x20, 0x60, 0x61, 0x80, 0xff, 0x8000, 0xffc0, 0xffbf, 0xffff, 0x10000, 0x12340004))
    if rng.random() < 0.3:
        regs['d1'] = rng.choice((0x40, 0x50, 0x70, 0, 0x8000, 0xffff, 0x12340050))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 1, 2, 5, 0x10001, 0xffff, 0x1ffff))
    if s == 0xd155a and rng.random() < 0.8:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(3)
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG and the node links are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(PARENT + 0x62, 1, rand_val(rng, 1))
    for a in (PLAYER1, PLAYER2, CHILD):
        r.put(a + 0x42, 2, rand_val(rng, 2))
        r.put(a + 0x46, 2, rand_val(rng, 2))
    r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3, 0xff)))
    r.put(A5 + 0x5b86, 1, rng.choice((0, 0, 1, 0x80)))
    r.put(0x10000e, 2, rand_val(rng, 2))
    if rng.random() < 0.5:
        r.put(NODE + 0x76, 2, rng.choice((0, 1, 2, 4, 5, 0x8000)))
    pops = []
    if s in STACK_LONG:
        pops = [(4, rng.choice((RECT, REC1)))]
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


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p)


def hints(s):
    h = []
    N = lambda o, n, vals: [dict(puts=[(NODE + o, n, v)]) for v in vals]
    R = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if s in (0xbc0b2, 0xbc398, 0xbc4bc, 0xbc510, 0xbc630, 0xbc706, 0xbc17a, 0xbc14c, 0xd1418, 0xbc3aa):
        h += N(0x76, 2, (0, 1, 2, 4, 5, 0x8000, 0xffff))
    if s == 0xbc154:
        h += R('d0', (4, 5, 3, 0x10004, 0xffff0004))
    if s == 0xd1420:
        h += R('d0', (1, 2, 0x10001, 0xffff0001, 0))
    if s == 0xbc1a0:
        h += N(0x42, 2, (0, 0x78, 0x79, 0x7fff, 0x8000, 0xffff))
    if s == 0xbc56c:
        h += N(0x42, 2, (0x7f, 0x80, 0x7fff, 0x8000))
    if s == 0xbc5d0:
        h += N(0x42, 2, (0x9c, 0x9d, 0x7fff, 0x8000))
    if s in (0xbc132, 0xbc27e, 0xbc2ec, 0xd1504, 0x4941e, 0x4943e, 0xd13de, 0xd1428, 0xbc0c2):
        h += N(0x15, 1, (0, 1, 2, 3, 0x20, 0x7f, 0x80, 0xff))
    if s == 0xbc26a:
        h += N(0x3a, 4, (0, 0x7fffffff, 0x80000000, 0xffffffff))
    if s in (0xbc246, 0xbc2be):
        h += [dict(puts=[(NODE + 0x64, 4, a), (NODE + 0x36, 4, b), (NODE + 0x3a, 4, c)]) for a, b, c in
              ((0, 0, 0), (0x80000000, 0x7fffffff, 0x7fffffff), (0x7fffffff, 0x80000000, 0x80000000), (0x1f, 0, 0xfff00000), (0xffffffe0, 0, 0xffefffe1),
               (0x30000, 0xfffd8000, 0x8a000), (0x20, 0, 0xffeffff0))]
    if s == 0xd14de:
        h += [dict(puts=[(NODE + 0x3a, 4, a), (NODE + 0x36, 4, b)]) for a, b in ((0, 0), (0x80000000, 0x80000000), (0x7fffffff, 0x7fffffff),
                                                                                 (0xfff40000, 0xffffffe0), (0xfff4001f, 0x1f), (0xfff40020, 0x20))]
    if s == 0xd144c:
        h += [dict(regs=dict(a0=CHILD), puts=[(CHILD + 0x46, 2, a), (NODE + 0x46, 2, b)]) for a, b in
              ((0x1a0, 0x1a0), (0x1a1, 0x1a1), (0x1000, 0x8000), (0, 0x7fff), (0x7fff, 0x1a0), (0x8000, 0x7fff))]
    if s == 0xd1466:
        h += R('d0', (0x60, 0x61, 0x7fff, 0x8000, 0x12340060))
    if s == 0xd147a:
        h += R('d0', (0xffc0, 0xffbf, 0x8000, 0x7fff, 0x1234ffc0))
    if s == 0xd1486:
        h += [dict(regs=dict(d0=a, a0=CHILD, d7=0x55550000), puts=[(CHILD + 0x42, 2, b), (NODE + 0x42, 2, c)]) for a, b, c in
              ((0, 0, 0), (0x8000, 0x8000, 0), (1, 0, 1), (0xffff, 0x7fff, 0x8000), (0x12348001, 5, 3), (0xfffe, 0, 0x8000))]
    if s == 0xd1498:
        h += [dict(regs=dict(d0=a, d7=b, d1=c)) for a, b, c in ((0, 0, 0), (0x10, 0x10000, 0x40), (0xffff, 0x1fffe, 0x70), (0x8000, 0x8000, 0x50),
                                                                (0x70, 0, 0x70), (0x5f, 0x12340001, 0x40), (0x60, 0xffff0000, 0x40), (0x6f, 0x10000, 0x48),
                                                                (0x60, 0x80000000, 0x40))]
    if s == 0xd14a8:
        h += R('d0', (0, 0x1f, 0x20, 0xffe0, 0xffdf, 0x12348000, 0xffff))
    if s == 0xd14b8:
        h += [dict(regs=dict(d0=a, d1=b, d7=0x12345678), puts=[(NODE + 0x15, 1, c)]) for a, b, c in
              ((0x8000, 0xffff, 0), (0x7fff, 0x8000, 1), (0xffff, 0x50, 0), (0x40, 0, 1), (0xffe0, 0x70, 0xfe), (0x12340020, 0x12340040, 0xff))]
    if s == 0xd14d2:
        h += R('d0', (0, 0x80000000, 1, 0xffffffff))
    if s == 0xd1528:
        h += R('d0', (0, 0x10000, 1, 0xffff0000))
    if s == 0xd1544:
        h += [dict(puts=[(0x10000e, 2, v)], regs=dict(d0=0x12345678)) for v in (0, 1, 2, 3, 0xfffc, 0xffff)]
    if s == 0xd155a:
        h += [dict(regs=dict(d0=v), puts=[(NODE + 0x19 + (v & 0xffff), 1, 0x5a)]) for v in (0, 1, 2, 0x12340002, 0x1000)]
        h += [dict(regs=dict(d0=v), puts=[(NODE + 0x19 - 0x10000 + (v & 0xffff), 1, 0xa5)]) for v in (0xffff, 0xfff0, 0x8000)]
    if s in (0x494ca, 0x494ee):
        h += R('d0', (0, 1, 2, 3, 0xfffffffc, 0x12345601))
    if s in (0x494ea, 0x49500):
        h += R('d0', (0, 0xff, 0x12345601, 0xfffffffe))
    if s in (0x49432, 0x49452):
        lo, sz = (2, 6) if s == 0x49432 else (0, 4)
        h += [dict(regs=dict(d7=d, a1=REC1), puts=[(REC1 + lo, 2, a), (REC1 + sz, 2, b)]) for d, a, b in
              ((0x5, 0, 5), (0x5, 0, 6), (0x5, 0, 4), (0x8000, 0x8000, 1), (0x12340000, 1, 0xffff), (0xff00, 0xff00, 0), (0x7fff, 0xffff, 0x8000))]
        h += [dict(regs=dict(d7=d, a1=RECT)) for d in (0, 0x100, 0xff00, 0xfe00)]
    if s in (0x4941e, 0x4943e):
        off = 0x46 if s == 0x4941e else 0x42
        h += [dict(regs=dict(a0=CHILD, d7=0x12340000), puts=[(CHILD + off, 2, a), (NODE + off, 2, b), (NODE + 0x15, 1, f)]) for a, b, f in
              ((5, 3, 0), (3, 5, 3), (0x8000, 0, 0), (0, 0x8000, 0xff), (0x7fff, 0xffff, 2))]
    if s in (0x49430, 0x49450, 0xd1496):
        h += R('d7', (0, 0x8000, 0x12340001, 0xffff))
    if s == 0xbc674:
        h += [dict(puts=[(NODE + 0x19, 1, v)]) for v in (0, 0x80, 0xff)]
    if s == 0xbc6ae:
        h += [dict(puts=[(NODE + 0xc, 4, v)]) for v in (PLAYER1, PLAYER2)]
    if s == 0xbc7b4:
        h += R('a0', (CHILD, PLAYER1))
    if s in (0xbc08c, 0xbc0c2, 0xbc16c, 0xbc192, 0xbc64a, 0xbc7a2, 0xd13b4, 0xd1440, 0xd222e, 0xd14a6):
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
            if (nxt in CONS_SET and s not in DATA_SET) or (inr(nxt) and nxt not in STARTS_SET):
                continue
            key = (nxt, 'h%d' % t) if hint else nxt
            if key in kept:
                continue
            if nxt == s:
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, o['stop'], o), 1, o)


PATH_ENTRIES = (0xbc08c, 0xbc09a, 0xbc0b2, 0xbc0c2, 0xbc102, 0xbc132, 0xbc14c, 0xbc154, 0xbc16c, 0xbc17a, 0xbc1a0, 0xbc1e0, 0xbc22a, 0xbc26a, 0xbc27e,
                0xbc2b8, 0xbc2ec, 0xbc37c, 0xbc398, 0xbc3aa, 0xbc4a4, 0xbc4bc, 0xbc4f4, 0xbc510, 0xbc548, 0xbc56c, 0xbc5ac, 0xbc5d0, 0xbc618, 0xbc630,
                0xbc674, 0xbc690, 0xbc6ea, 0xbc706, 0xbc7a2, 0xbc7b0, 0xbc7b4, 0xbc7c2, 0xd13de, 0xd1418, 0xd1440, 0xd144c, 0xd1466, 0xd147a, 0xd1486,
                0xd1498, 0xd14a8, 0xd14b8, 0xd14d4, 0xd1504, 0xd1514, 0xd1528, 0xd1544, 0xd1576, 0xd1586, 0xd2240, 0x494ca, 0x494ee, 0x49508)


def gen_paths(rng):
    fl = []
    for b in STARTS:
        fl += fields(b)
    fl = sorted(set(fl))
    for s in PATH_ENTRIES:
        kept = {}
        for t in range(200):
            carry = rng.choice((0, 1, 2))
            r, regs = world(rng, fl, s)
            o = native(r.b, regs, s, carry, path_stop)
            if o is None:
                continue
            ex = [p for p in o['trace'] if p in STARTS_SET]
            if any(p in CONS_SET for p in ex):
                continue
            key = (o['stop'], tuple(ex))
            if key in kept:
                continue
            kept[key] = (r, regs, o, carry, ex)
            if len(kept) >= 4:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o, carry, ex)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, o['stop']), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=REC1, a2=PLAYER1, a3=PLAYER2, a4=0xa4a4a4a4, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry):
    """A world for a real producer chain (28ae / 49370 / 4941e / 494c0 / 4b6f4 / 1ab80)."""
    r = base_ram()
    regs = dict(PLAIN)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    for d in (0x42, 0x46):
        r.put(NODE + d, 2, rng.choice((0, 0x10, 0x80, 0x100, 0x140, 0x1a0, 0x7fff, 0xfff0, rng.getrandbits(16))))
    for a in (PLAYER1, PLAYER2, CHILD):
        for d in (0x42, 0x46):
            r.put(a + d, 2, rng.choice((0, 0x10, 0x80, 0x100, 0x140, 0x1a0, 0x7fff, 0xfff0, rng.getrandbits(16))))
    r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3)))
    r.put(A5 + 0x5b86, 1, rng.choice((0, 1)))
    r.put(0x104ca0, 2, rng.choice((0, 1, 0xa, 0xb, 0x40)))
    r.put(0x104c9c, 4, FREE)
    r.put(FREE + 8, 4, 0)
    if entry in (0x494e0, 0x494f6):
        regs['a1'] = rng.choice((REC1, RECT))
        if regs['a1'] == REC1:
            big = rng.random() < 0.5
            for off, v in ((0, 0x8000), (2, 0x8000), (4, 0xffff), (6, 0xffff)):
                r.put(REC1 + off, 2, v if big else rng.choice((0, 0x10, 0x100, 0xff00)))
    if entry == 0xd155a:
        regs['d0'] = rng.randrange(3)
        for d in (0x42, 0x46):
            r.put(NODE + d, 2, rng.choice((0, 0x40, 0x80, 0x100, 0x140, 0x200, 0x7fff, 0xffc0)))
    return r, regs


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            if cp == 0x49458:
                r.put(SP, 4, 0x494e6)                       # the RTS of 49458 returns to the consumer 494e6
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in ((0xbc78e, 0xbc79e), (0x494c0, 0x494c6), (0x494e0, 0x494e6), (0x494f6, 0x494fc), (0xd1432, 0xd143c), (0xd1534, 0xd153a),
                        (0xd155a, 0xd156a)):
        clr, st = SUCC[cons]
        seen = {}
        for k in range(800):
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
    # 49fc6 (ROM scripts): no synthetic world; the consumers bc1f6 bc338 bc394 bc6a2 bc6de bc74e bc78a have the declared-C rows above and the real
    # producer chains of the V1 spec / real-ROM differential.


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=0, a3=0, a4=REC4, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    unrouted = 'unsupported animation machine PC'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr1c caller requires known carry', cp)
    # odd node / record / rectangle / stack: the entry block fails
    err('odd-node-bc09a', 0xbc09a, wodd, 0xbc09a, a6=NODE + 1)
    err('odd-node-bc14c', 0xbc14c, odd, 0xbc14c, a6=NODE + 1)
    err('odd-node-bc2e2', 0xbc2e2, odd, 0xbc2e2, stop=0x49fc6, a6=NODE + 1)    # TST.L 3a(A6): the read is observable only through its odd address; stop 49fc6 so that a skipped read would reach the stop
    err('odd-record-4941e', 0x4941e, odd, 0x4941e, a0=CHILD + 1)
    err('odd-record-d144c', 0xd144c, odd, 0xd144c, a0=CHILD + 1)
    err('odd-rect-49432', 0x49432, odd, 0x49432, a1=REC1 + 1)
    err('odd-stack-494c0', 0x494c0, odd, 0x494c0, a7=SP + 1)
    err('odd-stack-494ca', 0x494ca, odd, 0x494ca, a7=SP + 1)
    # fixed ROM / bank data read outside the declared synthetic bytes (the entry block fails)
    err('49432-rect-rom', 0x49432, missing, 0x49432, a1=0x1000)
    err('d155a-index-rom', 0xd155a, missing, 0xd155a, a6=0x100000, d0=0x8000)
    # TRAP #15 boundary of 49370 (A5 != 108000 -> 4937c, unrouted)
    err('494c0-49370-trap', 0x494c0, unrouted, 0x4937c, a5=0x108100)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   bc0b2 (WORD 76 = 0: borrow) -> bc0ba (MOVE.L #bc0c2,(A6)) -> bc0c0 RTS at an odd A7
    err('bc0b2-then-bc0c0', 0xbc0b2, odd, 0xbc0c0, a7=SP + 1, puts=[(NODE + 0x76, 2, 0)])
    #   49432 (zero sizes: no borrow, C Clear) -> 49458 (C Set) RTS at an odd A7
    err('49432-then-49458', 0x49432, odd, 0x49458, a7=SP + 1, puts=[(REC1 + 2, 2, 0), (REC1 + 6, 2, 0)])
    #   d1514 -> d1520 JSR 4ae4a at an odd A7
    err('d1514-then-d1520', 0xd1514, odd, 0xd1520, a7=SP + 1)
    #   d1598 (JMP d2206) -> d2206 bank animation -> JSR 49f8c at an odd A7
    err('d1598-then-d2206', 0xd1598, odd, 0xd2206, a7=SP + 1)
    #   4941e (bit 1 of BYTE 15 set) -> 49430 (NEG.W D7) -> 49432 reads an odd rectangle
    err('4941e-then-49432', 0x4941e, odd, 0x49432, a1=REC1 + 1, puts=[(NODE + 0x15, 1, 2)])


def main():
    rng = random.Random(0xF41C)
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
        if nxt is not None:
            last = B.block_instrs(s)[-1]
            nxt = set(t for t in nxt if (last[0], t) not in B.STATIC_IMPOSSIBLE)
        if nxt is not None and len(nxt) > 1 and not nxt <= succ[s]:
            one.append((hex(s), sorted(hex(x) for x in nxt - succ[s])))
    print('branch blocks with a missing successor', one)
    print('chain rows', sorted(set((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2)))
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))
    print('data-C rows', sorted(set((hex(d['entry']), hex(d['stop']), d['c']) for d in singles if d['entry'] in DATA_SET)))


if __name__ == '__main__':
    main()
