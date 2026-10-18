"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr1b_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000, the PVC bank ports 2ffff0 / 2ffff2 recorded in order) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++
test declares (not ROM data): the state LONG table 5a5ba..5a5ca, the bank-window LONGs 20017c (-> 2a0200) / 2001d0 (-> 2a0100) / 20000c (-> 2a0300)
with the LONGs behind them (2a0200..2a0214, 2a0150, 2a03ec) and the sign-extension target 298200 (2a0200 - 8000), the logo LONG table de34e..de376 and
its sign-extension target d634e (de34e - 8000), the sprite WORD / LONG list de3e6..de3fa and the 1ab02 rectangles b30aa..b30ba / ba3d6..ba3de.  A
native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as is a run that lands inside the unit on a PC that is
not a block start.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent record 10eb00, LONG 8(A6) = the sibling 10ec00),
record A0 = 10e400, A1 = 10ea00, A2 / A4 = 10e900 / 10e800, the WORD / LONG list at 10ec80, A5 = 108000 (the 5e30(A5) counters, -7fff(A5)), the
player records 100cb8 / 100da8, the 28ae free list (WORD 104ca0, LONG 104c9c -> 10c000), seeded BYTE / WORD / LONG field edits (BYTE / WORD / LONG sign
boundaries included), seeded D0-D7, the declared stack LONG for de318 / de3e0.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the first instruction that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA exits, the RTS sentinel).
  single 2  a consumer entered through its real producer (1ab02 -> b30ea b335e b9816; 493bc -> b3470; b3460 -> b31f4 through 493bc and b3474 / b347e;
            28ae -> b32d8 b330a b333c): stop = the consumer's successor; the native branch on the real flags decides it.  49fc6 / 5ab5a / 4945e run ROM
            scripts or tables: their consumers b97fa / 5a3f8 / 5a58e have declared-C rows here (real chains in V1).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C; b3474 (ORI;
RTS) / b32ea b331c b334e (ORI) leave C Set, b347e (ANDI; RTS) leaves C Clear (contract decision 5).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr1b_test_table.py  (rewrites the generated section in place)
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
import fr1b as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr1b_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
CLEAR_SET, SET_SET, PASS_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC4, REC2, REC1, PARENT, SIBLING, LIST = 0x10e800, 0x10e900, 0x10ea00, 0x10eb00, 0x10ec00, 0x10ec80
FREE = 0x10c000
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
TABLE, LOGO, SPRITES = 0x5a5ba, 0xde34e, 0xde3e6


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xF41B)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    table = l(0x5a0ae) + l(0x5a1c4) + l(0x5a376) + l(0x10fe40)                                                   # 5a5ba..5a5ca
    logo = b''.join(l(v) for v in (0x12952, 0x80000000, 0x7fffffff, 0x17152, 0, 0xffffffff, 0x1b952, 0xfffe0000, 0x1e952, 0xffffffff))   # de34e..de376
    sprites = w(0x1400) + l(0x1952) + w(0x7fff) + l(0x80000152) + w(0x0000) + l(0x00000001) + w(0xffff)              # de3e6..de3fa
    rect = w(0xffc0) + w(0xffd0) + w(0x0080) + w(0x0060)
    rect2 = w(0xffd0) + w(0xff00) + w(0x0060) + w(0x0200)
    anim = b''.join(l(srng.getrandbits(19) << 1) for _ in range(6))                                               # 2a0200..2a0218
    return [(TABLE, table), (0xb30aa, rect + rect), (0xba3d6, rect2), (0xd634e, l(0x2468ace0)), (LOGO, logo), (SPRITES, sprites),
            (0x20000c, l(0x2a0300)), (0x20017c, l(0x2a0200)), (0x2001d0, l(0x2a0100)), (0x2a0150, l(srng.getrandbits(19) << 1)), (0x2a0200, anim),
            (0x2a03ec, l(srng.getrandbits(19) << 1)), (0x298200, l(0x13572468))]


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


# consumer -> (C clear successor, C set successor)
SUCC = {0x5a3f8: (0x5a402, 0x5a3fc), 0x5a58e: (0x5a592, 0x5a9c2), 0xb30ea: (0xb30f4, 0xb30ee), 0xb31f4: (0xb3218, 0xb31f8), 0xb3470: (0xb347e, 0xb3474),
        0xb32d8: (0xb32ee, 0xb32dc), 0xb330a: (0xb3320, 0xb330e), 0xb333c: (0xb3352, 0xb3340), 0xb335e: (0xb3368, 0xb3362), 0xb97fa: (0xb980a, 0xb97fe),
        0xb9816: (0xb9820, 0xb981a)}
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


def native(ram, regs, pc, carry, stopfn):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0))
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
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or any(e[0] != 1 for e in m.ports):
        return None                                 # only the bank register writes of am_zero_bank (de05e) are expected; the PVC words end as at the start
    return dict(stop=out['stop'], trace=trace, regs=m.regs(), ram=m.ram(), ports=[(e[1], e[2], e[3]) for e in m.ports])


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


def ports_text(ports):
    return ','.join('%x:%x:%x' % p for p in ports)


def carry_after(p, c):
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in CLEAR_SET:
        return 1
    if p in SET_SET:
        return 2
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
             fail=fail_pc, ports='')
    if o is not None:
        d.update(out=[o['regs'][k] for k in KEYS], digest=digest(o['ram'], o['regs'], o['stop']), ports=ports_text(o['ports']))
    ROWS.append(d)


# ---------------------------------------------------------------------------------------------------------------------
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0xb, 0xc, 0xd, 0x10, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0xf, 0x10, 0x14, 0x15, 0x1e, 0x7f, 0x80, 0xff, 0x100, 0x1000, 0x2000, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffc,
      0xffff)
VL = (0, 1, 3, 0x4000, 0x7fff, 0x10000, 0x7fffffff, 0x80000000, 0xc0000000, 0xfff80000, 0xfffffffd, 0xffffffff, 0x123456)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x88}
LIST_BLOCKS = set(B.LIST_BLOCKS)
COUNTER_BLOCKS = set(B.COUNTER_BLOCKS)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'sne'):
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


def list_words(rng):
    words = []
    for _ in range(rng.randrange(3)):
        words.append(rng.choice((0, 1, 0x1400, 0x7fff)))
        v = rng.getrandbits(32)
        words += [v >> 16, v & 0xffff]
    words.append(rng.choice((0xffff, 0x8000)))
    return words


# stack LONG popped by the entered block (declared below A7 = 10ef00): de318 / de3e0 the list pointer
def pops_of(rng, s):
    if s in (0xde318, 0xde3e0):
        return [(4, rng.choice((LIST, SPRITES)))]
    return []


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=CHILD, a1=REC1,
                a2=rng.choice((REC2, 0xa2a2a2a2)), a3=0xa3a3a3a3, a4=REC4, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 5, 0xa, 0xb, 0xc, 0x14, 0x15, 0x80, 0xff, 0x2000, 0x8000, 0xffff, 0x10000, 0x12340004))
    if rng.random() < 0.3:
        regs['d1'] = rng.choice((0, 1, 0xb, 0xc, 0x8000, 0xffff, 0x80000000, 0x1234ff80))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 1, 2, 5, 0x10001, 0xffff))
    if s in COUNTER_BLOCKS:
        regs['a1'] = A5 + 0x5e30
        regs['d1'] = rng.randrange(0xc) | (rng.choice((0, 0x12345600)) if s == 0xe9132 else 0)
        if s == 0xe9132 and rng.random() < 0.85:
            regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0xc)
    if s in LIST_BLOCKS:
        regs['a0'] = rng.choice((LIST, LIST, SPRITES))
    if s in (0xde318, 0xde3e0) or s in LIST_BLOCKS:
        for i, v in enumerate(list_words(rng)):
            r.put(LIST + 2 * i, 2, v)
    if s in (0xb3468, 0xb322c):
        regs['d0'] = rng.choice((PLAYER1, PLAYER2, REC1, 0x10e000))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: REC2, 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG and the node links are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (LIST <= addr < LIST + 0x20 and s in LIST_BLOCKS):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x88, 4, rng.choice((PLAYER1, PLAYER2, REC1, 0x80000000, 0xffffffff, 0x7fffffff)))
    r.put(PARENT + 0x62, 1, rand_val(rng, 1))
    for a in (PLAYER1, PLAYER2, REC1, CHILD):
        r.put(a + 0x46, 2, rand_val(rng, 2))
    r.put(A5 + 0x568e, 1, rng.getrandbits(8))
    r.put(A5 - 0x7fff, 1, rng.choice((0, 0, 1, 0x80, 0xff)))
    for k in range(0xc):
        r.put(A5 + 0x5e30 + k, 1, rng.choice((0, 1, 0x7f, 0x80, 0xff)))
    if rng.random() < 0.8:
        r.put(NODE + 0x6b, 1, rng.choice((rng.randrange(0xc), 0xc, 0xff)))
        r.put(NODE + 0x78, 2, rng.randrange(10))
    if rng.random() < 0.5:
        r.put(NODE + 0x76, 2, rng.choice((0, 1, 2, 0x8000)))
    pops = pops_of(rng, s)
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
    if s == 0x5a376:
        h += N(0x80, 1, (0, 1, 2, 3, 0x80, 0xfd, 0xff))
    if s in (0x5a3e4, 0x5a43a, 0x5a574):
        h += N(0x80, 1, (0, 1, 0xfe, 0xff))
    if s == 0x5a3d6:
        h += N(0x8c, 1, (0, 1, 0x80, 0xff))
    if s in (0x5a394, 0x5a3a8):
        h += R('d0', (0, 0x80, 0x123456ff))
    if s == 0x5a402:
        h += [dict(puts=[(NODE + 0x8c, 1, a), (NODE + 0x9c, 1, b)]) for a, b in ((0, 0), (1, 0), (0, 1), (0x80, 0xff), (1, 1))]
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0), puts=[(NODE + 0x8c, 1, a), (NODE + 0x9c, 1, b)]) for a, b in ((1, 1), (0, 0))]
    if s == 0x5a44e:
        h += N(0x84, 2, (0, 1, 2, 0x8000, 0xffff))
    if s == 0x5a59c:
        h += [dict(regs=dict(d0=a, d7=b)) for a, b in ((0, 1), (1, 2), (2, 0), (3, 0x10001), (0xffff, 0xffff), (0x12345677, 2), (0x7ffe, 1))]
    if s == 0x5a5ae:
        h += [dict(regs=dict(a0=a), puts=[(NODE + 0x98, 4, b)]) for a, b in ((0x5a376, 0x5a376), (0x5a376, 0x5a377), (0x5a0ae, 0x15a0ae), (0, 0))]
    if s == 0x5a592:
        h += R('d7', (0, 0x12340000, 0xffffffff))
    if s == 0xb30f6:
        h += [dict(puts=[(NODE + 0x7c, 2, a), (NODE + 0x78, 2, b)]) for a, b in ((0, 0), (1, 1), (0x7fff, 0), (0x8000, 0x8000), (0xffff, 1), (0x80, 0))]
    if s == 0xb3118:
        h += N(0x7a, 2, (0, 1, 0x8000))
    if s == 0xb3120:
        h += [dict(puts=[(NODE + 0x36, 4, a), (NODE + 0x15, 1, b)]) for a, b in ((0, 0), (1, 0xfe), (0x80000000, 0xff), (0xffffffff, 1))]
    if s in (0xb314e, 0xb3284, 0xb30d0, 0xb32a2, 0xb31dc):
        h += N(0x76, 2, (0, 1, 0x8000, 0xffff))
    if s == 0xb31e4:
        h += N(0x80, 2, (0, 1, 0x8000))
    if s == 0xb31ec:
        h += N(0x80, 2, (0, 1, 0x8000))
    if s == 0xb316e:
        h += R('d0', (1, 4, 0, 0x2000, 0x1fff, 0x12340004, 0x5))
    if s == 0xb31f8:
        h += [dict(regs=dict(a0=CHILD), puts=[(CHILD + 0x46, 2, a), (NODE + 0x46, 2, b)]) for a, b in ((5, 3), (3, 5), (0, 0), (0x8000, 0), (0, 0x8000),
                                                                                               (0x7fff, 0xffff), (0x8000, 1))]
    if s == 0xb3208:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x8000, 0x80000000), (1, 1), (0x12340005, 0xfffffffb))]
    if s == 0xb320c:
        h += [dict(regs=dict(d0=a), puts=[(NODE + 0x7e, 2, b)]) for a, b in ((5, 5), (6, 5), (4, 5), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0),
                                                                             (0x12340000, 0xffff))]
    if s == 0xb3224:
        h += N(0x72, 4, (0, 0x10000, 1, 0x80000000))
    if s == 0xb3234:
        h += R('d0', (0, 0x10000, 1, 0xffff))
    if s == 0xb30c0:
        h += N(0x61, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0xb3266:
        h += N(0x15, 1, (0x7f, 0x80))
    if s == 0xb3270:
        h += [dict(puts=[(NODE + 0x36, 4, a), (NODE + 0x82, 4, b)]) for a, b in ((0, 0), (3, 0x80000000), (0x80000000, 1), (0xfffffffd, 0xffffffff),
                                                                                 (0x7fffffff, 0), (0xc0000001, 5))]
    if s == 0xb324c:
        h += [dict(puts=[(NODE + 0x36, 4, a), (NODE + 0x61, 1, b)]) for a, b in ((0, 0), (0x3fff, 0xf7), (0x80003fff, 8))]
    if s == 0xb32b6:
        h += N(0x86, 2, (0, 1, 0x15, 0xb, 6, 0x8000))
    if s == 0xb32be:
        h += R('d0', (0x15, 0xb, 6, 0, 0x10015, 0x14))
    if s == 0xb32f2:
        h += R('d0', (0xa, 0xb, 0x1000a))
    if s == 0xb3324:
        h += R('d0', (5, 6, 0x10005))
    if s == 0xb3460:
        h += N(0x88, 4, (0x80000000, 0x7fffffff, PLAYER1, PLAYER2, 0xffffffff))
    if s == 0xe9114:
        h += [dict(puts=[(NODE + 0x6b, 1, a)], regs=dict(d0=b)) for a, b in ((0, 0), (0xb, 0xb), (0xc, 0xc), (0x80, 0x80), (0xff, 0xff), (5, 0x1234560b))]
    if s == 0xe912a:
        h += [dict(regs=dict(d0=v, a1=A5 + 0x5e30)) for v in (0, 0xb, 0xc, 0x80, 0xff, 0x1234560b)]
    if s == 0xe9126:
        h += [dict(regs=dict(d1=v, a1=A5 + 0x5e30), puts=[(A5 + 0x5e30 + v, 1, b)]) for v, b in ((0, 0), (0xb, 0x80), (3, 0xff))]
    if s == 0xe9132:
        h += [dict(regs=dict(d0=v, a1=A5 + 0x5e30), puts=[(A5 + 0x5e30 + (v & 0xff), 1, b)]) for v, b in ((0, 0xff), (0xb, 0x7f), (0x12340005, 0))]
    if s == 0xe9140:
        h += R('d0', (0xffffffff, 0x12345605))
    if s in (0xde054, 0xde0d8, 0xde0ee, 0xde112):
        h += N(0x76, 2, (0, 1, 2, 0x8000, 0xffff))
    if s in (0xde194, 0xde1ec, 0xde248):
        h += [dict(puts=[(NODE + 0x76, 2, a), (NODE + 0x7a, 2, b), (NODE + 0x7c, 2, b ^ 0x1111)]) for a, b in ((1, 0xfff8), (2, 0x7fff), (0, 0xfffc),
                                                                                                                (0x8001, 2))]
    if s in (0xde176, 0xde1ce, 0xde22a):
        h += [dict(regs=dict(d0=0x55556666), puts=[(NODE + 0x7a, 2, a), (NODE + 0x7c, 2, b)]) for a, b in ((0x8000, 0x1234), (0, 0xffff))]
    if s == 0xde2cc:
        h += N(0x78, 2, (0, 1, 2, 4, 5, 7, 8, 9, 0x2000))
    if s in (0xde2fe, 0xde3c6):
        h += [dict(regs=dict(a0=LIST, d1=0x12345678), puts=[(LIST, 2, v), (LIST + 2, 4, 0x89abcdef), (LIST + 6, 2, 0xffff)]) for v in (0, 0x7fff, 0x8000,
                                                                                                                                  0xffff)]
    if s in (0xde306, 0xde3ce):
        h += [dict(regs=dict(a0=LIST, d7=0x12345678, d5=0x87654321), puts=[(LIST, 4, v)]) for v in (0, 0x80000000, 0xffffffff)]
    if s == 0xddfdc:
        h += [dict(puts=[(A5 - 0x7fff, 1, v)]) for v in (0, 1, 0x80, 0xff)]
    if s == 0xde05e:
        h += R('d0', (0, 0x12345678, 0xffff))
    if s == 0xde2e6:
        h += R('d5', (0, 0x12345678))
    if s in (0xb3130, 0xb31ae, 0xb32dc, 0xb330e, 0xb3340, 0xddff4, 0xde376):
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788))]
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
            if nxt in CONS_SET or (inr(nxt) and nxt not in STARTS_SET):
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 1, o)


PATH_ENTRIES = (0x515fc, 0x5a376, 0x5a388, 0x5a39c, 0x5a3c6, 0x5a3d6, 0x5a3e4, 0x5a3fc, 0x5a402, 0x5a41e, 0x5a42e, 0x5a43a, 0x5a44e, 0x5a54e, 0x5a56e,
                0x5a574, 0x5a592, 0x5a59c, 0x5a5ae, 0xb30f6, 0xb3118, 0xb3130, 0xb314e, 0xb316e, 0xb31d6, 0xb31dc, 0xb31e4, 0xb31f8, 0xb320c, 0xb3224,
                0xb3234, 0xb3242, 0xb30c0, 0xb30d0, 0xb3246, 0xb324c, 0xb3266, 0xb3284, 0xb32a2, 0xb32b6, 0xb32be, 0xb32f2, 0xb3324, 0xb32ea, 0xb331c,
                0xb334e, 0xb3460, 0xb3474, 0xb97c0, 0xb97e8, 0xb97fe, 0xddfdc, 0xde024, 0xde048, 0xde054, 0xde05e, 0xde0cc, 0xde0d8, 0xde0ee, 0xde112,
                0xde144, 0xde194, 0xde1ec, 0xde248, 0xde1a8, 0xde204, 0xde2c0, 0xde2cc, 0xde2f6, 0xde2fe, 0xde318, 0xde3b2, 0xde3c2, 0xde3c6, 0xde3e0,
                0xe9112, 0xe9114, 0xe912a)


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
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=0x10c000, a2=0xa2a2a2a2, a3=0xa3a3a3a3, a4=0xa4a4a4a4, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry):
    """A world for a real producer chain (1ab02 / 493bc / b3460 / 28ae)."""
    r = base_ram()
    regs = dict(PLAIN)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x10, 2, rng.getrandbits(8))
    r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    for d in (0x42, 0x46, 0x4a, 0x4e):
        r.put(NODE + d, 4, rng.choice((0, 0x100000, 0x800000, 0x1000000, 0x1400000, 0x2000000, 0x7fff0000, 0xfff00000, rng.getrandbits(32))))
    r.put(NODE + 0x88, 4, rng.choice((PLAYER1, PLAYER2, REC1, 0x80000000)))
    r.put(NODE + 0x80, 2, rng.choice((1, 2, 5)))
    r.put(A5 + 0x568e, 1, rng.getrandbits(8))
    for a in (PLAYER1, PLAYER2, REC1):
        r.put(a + 0x46, 2, rng.getrandbits(16))
    r.put(0x104ca0, 2, rng.choice((0, 1, 0x1e, 0x1f, 0x40)))
    r.put(0x104c9c, 4, FREE)
    r.put(FREE + 8, 4, 0)
    if entry in (0xb3358,):
        regs['a0'] = rng.choice((0xb30aa, 0xb30b2))
    if entry == 0xb3468:
        regs['d0'] = rng.choice((PLAYER1, PLAYER2, REC1))
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
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in ((0xb30e4, 0xb30ea), (0xb3358, 0xb335e), (0xb980a, 0xb9816), (0xb3468, 0xb3470), (0xb31ec, 0xb31f4), (0xb32c8, 0xb32d8),
                        (0xb32fa, 0xb330a), (0xb332c, 0xb333c)):
        clr, st = SUCC[cons]
        seen = {}
        for k in range(600):
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
    # 49fc6 / 5ab5a / 4945e (ROM scripts and tables): no synthetic world; the consumers b97fa 5a3f8 5a58e have the declared-C rows above and the real
    # producer chains of the V1 spec / real-ROM differential.


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x10c000, a2=0, a3=0, a4=REC4, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    unrouted = 'unsupported animation machine PC'

    def err(name, entry, message, fail_pc, carry=0, puts=(), **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr1b caller requires known carry', cp)
    # odd node / record / list / stack / A5: the entry block fails
    err('odd-node-5a42e', 0x5a42e, wodd, 0x5a42e, a6=NODE + 1)
    err('odd-node-b30f6', 0xb30f6, odd, 0xb30f6, a6=NODE + 1)
    err('odd-node-de3b2', 0xde3b2, odd, 0xde3b2, a6=NODE + 1)
    err('odd-record-b31f8', 0xb31f8, odd, 0xb31f8, a0=CHILD + 1)
    err('odd-list-de2fe', 0xde2fe, odd, 0xde2fe, a0=LIST + 1)
    err('odd-stack-de306', 0xde306, odd, 0xde306, a0=LIST, a7=SP + 1, puts=[(LIST, 4, 0x12345678)])
    err('odd-stack-de318', 0xde318, odd, 0xde318, a7=SP + 1)
    err('odd-a5-de05e', 0xde05e, wodd, 0xde05e, a5=A5 + 1)
    err('odd-pointer-b3474', 0xb3474, odd, 0xb3474, puts=[(NODE + 0x88, 4, 0)], a7=SP + 1)
    # fixed ROM / bank data read outside the declared synthetic bytes (the entry block fails)
    err('de2cc-logo-rom', 0xde2cc, missing, 0xde2cc, puts=[(NODE + 0x78, 2, 0x100)])
    err('de2fe-list-rom', 0xde2fe, missing, 0xde2fe, a0=0x1000)
    err('b316e-bank-rom', 0xb316e, missing, 0xb316e, d0=0x100)
    # TRAP #15 boundary of 493bc (A5 != 108000 -> 493c6, unrouted)
    err('b3468-493bc-trap', 0xb3468, unrouted, 0x493c6, a5=0x108100, d0=PLAYER1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   de054 (WORD 76 = 2 -> 1) -> de05c RTS at an odd A7
    err('de054-then-de05c', 0xde054, odd, 0xde05c, a7=SP + 1, puts=[(NODE + 0x76, 2, 2)])
    #   b3460 (LONG 88 negative) -> b347e (C Clear) RTS at an odd A7
    err('b3460-then-b347e', 0xb3460, odd, 0xb347e, a7=SP + 1, puts=[(NODE + 0x88, 4, 0x80000000)])
    #   de3c2 (A0 := de3e6) -> de3c6 reads the synthetic WORD 1400 (positive) -> de3ce reads the LONG and pushes A0 at an odd A7
    err('de3c2-then-de3ce', 0xde3c2, odd, 0xde3ce, a7=SP + 1)
    #   515fc -> 515e0 (FR1a) pushes WORD D2 at an odd A7
    err('515fc-then-515e0', 0x515fc, odd, 0x515e0, a7=SP + 1)
    #   b97fe (MOVE.W #0,76(A6); MOVE.L #b970e,(A6)) -> b980a JSR 1ab02 pushes at an odd A7
    err('b97fe-then-b980a', 0xb97fe, odd, 0xb980a, a7=SP + 1)


def main():
    rng = random.Random(0xF41B)
    gen_singles(rng)
    gen_paths(rng)
    gen_consumers(rng)
    gen_errors()
    out = []
    for d in ROWS:
        regs = ','.join('0x%x' % v for v in d['regs'])
        if d['error'] is None:
            outr = ','.join('0x%x' % v for v in d['out'])
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",NULL,0x0,{%s},%d,%d,%dULL,"%s"},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'], outr,
                                                                                         d['c'], d['single'], d['digest'], d['ports']))
        else:
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s","%s",0x%x,{0},0,%d,0ULL,""},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'],
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
          'cons', sum(1 for d in ROWS if d['single'] == 3), 'error', sum(1 for d in ROWS if d['single'] == 4),
          'with ports', sum(1 for d in ROWS if d['ports']))
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
