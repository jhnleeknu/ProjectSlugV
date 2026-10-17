"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b3c_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data): the bank-window LONGs
200094..2000a0, the WORD tables 2d8b8..2d916 (pairs 2d8b8, sounds 2d8fc, animation indices 2d904), the WORD table 2d9dc..2da64 and the LONG tables
227fc..2285c (child tables and the 2284c selector).  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there).
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00 (not 10f000: the BYTE 10f001 that 1c12e tests would overlap it), node A6 = 10e000 (LONG c(A6) = parent 10e400), A5 = 108000 (player records 100cb8 /
100da8, LONG 8c -> record 10e800), LONG 3e(A6) record 10e900, A1 record 10ea00, LONG 22(A6) table 10eb00, the 538e(A5) record 10d38e, a RAM child
table 10ec80 (the fourth 2284c entry), seeded BYTE / WORD / LONG field edits, seeded D0-D7.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the first instruction that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP 2a00 / 491b6, the RTS sentinel).
  single 2  a consumer entered through its real producer (289e -> 1c128 from 1c122, 288c -> 2dbb2 from 2dbac): stop = the consumer's successor; the
            native branch on the real flags decides it.  49fc6 runs ROM scripts: its four consumers have declared-C rows here (real chains in V1).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b3c_test_table.py  (rewrites the generated section in place)
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
import b3c as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b3c_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, PARENT = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC8C, REC3E, RECA1, TAB22, REC538E, TABRAM = 0x10e800, 0x10e900, 0x10ea00, 0x10eb00, 0x10d38e, 0x10ec80
PLAYERS = (0x100cb8, 0x100da8)
ROM_BANK, ROM_PAIRS, ROM_QUADS, ROM_CHILD = 0x200094, 0x2d8b8, 0x2d9dc, 0x227fc


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xB3C5)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    bank = l(0x0029e000 | srng.getrandbits(8) << 1) + l(srng.getrandbits(32)) + l(0x0029f000 | srng.getrandbits(8) << 1)
    pairs = b''.join(w(srng.choice((0, 1, 0x15, 0x7fff, 0x8000, 0xffeb, srng.getrandbits(16)))) for _ in range(34))   # 2d8b8: 17 WORD pairs
    pairs += b''.join(w(srng.getrandbits(16)) for _ in range(4))                                                        # 2d8fc: 4 sound WORDs
    pairs += b''.join(w(v) for v in (0, 1, 2, 0x3f, 0x10, 0x20, 0x3e, 3, 0x30))                                        # 2d904: 9 indices (< 40)
    quads = b''.join(w(srng.choice((0, 1, 0xfff0, 0x10, 0x8000, 0x7fff, srng.getrandbits(16)))) for _ in range(68))    # 2d9dc: 17 x 4 WORDs
    child = b''
    for t in range(5):                                                                                                  # 227fc..2284c: 5 tables
        child += l(0) + b''.join(l(srng.choice((0, 0x23830, 0x2b99c, srng.getrandbits(19) << 1))) for _ in range(3))
    child += l(0x227fc) + l(0x2280c) + l(TABRAM) + l(0x2282c)                                                          # 2284c: the selector
    assert len(pairs) == 0x5e and len(quads) == 0x88 and len(child) == 0x60
    return [(ROM_BANK, bank), (ROM_PAIRS, pairs), (ROM_QUADS, quads), (ROM_CHILD, child)]


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
SUCC = {0x1c128: (0x1c12c, 0x1c12e), 0x2d85e: (0x2d868, 0x2d862), 0x2d8ac: (0x2d8b6, 0x2d8b0), 0x2d9c6: (0x2d9da, 0x2d9ca),
        0x2dbb2: (0x2dbb6, 0x2dbbc), 0x2dbce: (0x2dbd8, 0x2dbd2)}
assert set(SUCC) == CONS_SET


class Ram(object):
    def __init__(self):
        self.b = bytearray(65536)
        self.puts = []

    def put(self, a, n, v):
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
    out = dict(stop=None)
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
    if out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.ports or m.bank != 0x200000:
        return None
    return dict(stop=out['stop'], trace=trace, regs=m.regs(), ram=m.ram())


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


def model(executed, carry):
    c = carry
    for p in executed:
        if p not in CONS_SET:
            c = 0
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
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x16, 0x17, 0x20, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 0x10, 0x80, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fffffff, 0x80000000, 0xfff00000, 0xffffffff, 0x123456, 0xc0000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x3e}


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg'):
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


def in_callee(s):
    return any(lo <= s < hi for lo, hi in B.CALLEE_RANGES)


def world(rng, fl, s, hint=None):
    r = base_ram()
    player = rng.choice(PLAYERS)
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=player if in_callee(s) else PARENT,
                a1=rng.choice((0, RECA1, RECA1)), a2=rng.choice((REC3E, 0xa2a2a2a2)), a3=0xa3a3a3a3, a4=REC8C, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x7f, 0x80, 0xff, 0x100, 0x10000, 0xffff, 0x8000, 0x10101))
    base_of = {6: NODE, 0: regs['a0'], 4: REC8C, 5: A5, 2: REC3E, 1: RECA1}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG, node links and the pointers are declared below
        if reg == 0 and in_callee(s) and disp == 0x8c:
            continue
        r.put((base_of[reg] + disp) & 0xffffffff, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x3e, 4, rng.choice((0, REC3E)))
    r.put(NODE + 0x22, 4, TAB22)
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x2b99c, 0)))
        r.put(p + 0x8c, 4, REC8C)
        r.put(p + 0x9e, 1, rng.choice((0, 1, 2, 3, 3)))
    r.put(REC8C + 6, 1, rng.choice((0, 1, 2, 3, 3, 4, 0xff)))
    r.put(REC8C + 7, 1, rng.choice((0, 1, 0x80)))
    r.put(PARENT + 0x7c, 1, rng.randrange(17))
    r.put(PARENT + 0x8a, 2, rng.randrange(4))
    r.put(NODE + 0x7c, 1, rng.randrange(17))
    r.put(0x10f001, 1, rng.choice((0, 4, 0xfb, 0xff)))
    for k in range(4):
        r.put(TABRAM + 4 * k, 4, rng.choice((0, 0x23830, rng.getrandbits(19) << 1)))
    for k in range(0, 0x100, 4):
        if rng.random() < 0.3:
            r.put(TAB22 + k, 4, rng.getrandbits(32))
    for base in (REC3E, RECA1):
        for o_ in (0x14, 0x18, 0x1c, 0x20):
            r.put(base + o_, 4, rand_val(rng, 4))
    r.put(REC538E + 0x14, 2, rand_val(rng, 2))
    r.put(REC538E + 0x18, 2, rand_val(rng, 2))
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
    P = lambda o, n, vals: [dict(puts=[(PARENT + o, n, v)]) for v in vals]
    if s == 0x1c114:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x10000, 0xffff, 0x8000)]
    if s == 0x1c12e:
        h += [dict(puts=[(0x10f001, 1, v)]) for v in (0, 4, 0xfb, 0xff)]
    if s in (0x1c13e, 0x1c148):
        h += [dict(puts=[(REC8C + 7, 1, v)]) for v in (0, 1, 0x80, 0xff)]
    if s == 0x1c14c:
        h += [dict(puts=[(REC8C + 6, 1, v), (p + 0x9e, 1, b)], regs=dict(a0=p, d0=0x8001, d2=0x7fff, d3=0xffff0123))
              for v, b, p in ((0, 0, PLAYERS[0]), (1, 1, PLAYERS[1]), (3, 2, PLAYERS[0]), (4, 3, PLAYERS[1]), (0xff, 2, PLAYERS[0]), (2, 3, PLAYERS[0]))]
    if s == 0x1c172:
        h += [dict(regs=dict(d0=v, a1=a)) for v in (0, 1, 2, 3) for a in (0x227fc, TABRAM)]
    if s == 0x1c18a:
        h += [dict(puts=[(SP, 2, a), (SP + 2, 2, b), (SP + 4, 2, c), (NODE + 0x15, 1, f)], regs=dict(a0=REC3E))
              for a, b, c, f in ((0x8000, 0x7fff, 0xffff, 0), (1, 0x8001, 0, 1), (0xffff, 0, 0x8000, 0xff))]
    if s == 0x1c1a6:
        h += [dict(regs=dict(d0=v, d2=w)) for v, w in ((0x20, 0x0001), (0x80, 0x8000), (0, 0), (0xffffff7f, 0xffff))]
    if s == 0x22920:
        h += N(0x3e, 4, (0, REC3E))
    if s == 0x22944:
        h += [dict(regs=dict(a1=0)), dict(regs=dict(a1=RECA1)), dict(regs=dict(a1=0x10000))]
    if s == 0x2d7da:
        h += P(0x15, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0x2d816:
        h += N(0x13, 1, (0, 1, 0x7f, 0xfe, 0xff))
    if s == 0x2d822:
        h += [dict(regs=dict(d0=d), puts=[(NODE + 0x3a, 2, v)]) for d, v in ((1, 0x7fff), (0xff, 0x8000), (0x80, 0xffff), (0x8000, 0x8000), (0xffff, 1),
                                                                             (0x7fff, 0x7fff), (0x12340100, 0x100))]
    if s in (0x1c18a, 0x2d830, 0x2d98e, 0x2db6a):
        h += N(0x15, 1, (0, 1, 0x80, 0xff))
    if s == 0x2d830:
        h += [dict(puts=[(NODE + 0x8e, 1, a), (NODE + 0x8f, 1, b)]) for a, b in ((0x80, 0x7f), (0xff, 1), (0, 0x80))]
    if s == 0x2d868:
        h += N(0x13, 1, (0, 1, 0x7f, 0x80, 0xfe, 0xff))
    if s == 0x2d932:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 3, 8, 0xff00, 0x12340005)]
    if s == 0x2d95c:
        h += P(0x8a, 2, (0, 1, 2, 3))
    if s in (0x2d98e, 0x2db32):
        h += P(0x7c, 1, (0, 8, 16))
    if s == 0x2db32:
        h += P(0x36, 4, (0, 0x7fffffff, 0x80000000, 0xffffffff))
        h += P(0x9c, 1, (0, 0xff))
    if s == 0x2db58:
        h += N(0x7d, 1, (0, 1, 4, 5, 0x84, 0xff))
    if s == 0x2db6a:
        h += N(0x7c, 1, (0, 1, 8, 16))
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, 0, 1, o)


PATH_ENTRIES = (0x1c114, 0x1c12e, 0x1c13e, 0x1c148, 0x1c14c, 0x1c18a, 0x22920, 0x22944, 0x2d7be, 0x2d7da, 0x2d816, 0x2d822, 0x2d830, 0x2d868,
                0x2d87a, 0x2d916, 0x2d932, 0x2d95c, 0x2d98e, 0x2db06, 0x2db32, 0x2db58, 0x2db6a, 0x2db88, 0x2d80a, 0x2d89a, 0x2d988, 0x2dba6)


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


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=PARENT,
             a1=0x10c000, a2=0xa2a2a2a2, a3=0xa3a3a3a3, a4=0xa4a4a4a4, a5=A5, a6=NODE, a7=SP)


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry, 3, o)
    # real producers.  289e (readiness): CMPI.L #270e,(A0); BEQ -> RTS with C Clear, else 28a8 ORI Set.  Entry 1c122 with A0 = a player record.
    for k, (p, v) in enumerate(((PLAYERS[0], 0x270e), (PLAYERS[0], 0x2b99c), (PLAYERS[1], 0x270e), (PLAYERS[1], 0), (PLAYERS[0], 0x270f))):
        r = base_ram()
        r.put(p, 4, v)
        regs = dict(PLAIN)
        regs['a0'] = p
        o = native(r.b, regs, 0x1c122, 0, lambda q, tr: q in (0x1c12c, 0x1c12e))
        assert o is not None, k
        c = 1 if o['stop'] == 0x1c12c else 2
        assert c == (1 if v == 0x270e else 2), (k, hex(o['stop']))
        row('chain-1c122-289e-%d' % k, r, regs, 0x1c122, o['stop'], 0, c, 2, o)
    # 288c: MOVEA.L c(A6),A0; CMPA.W #0,A0; BNE 289e (LONG (A0) = 270e -> Clear) / ORI Set.  Entry 2dbac.
    for k, (parent, v) in enumerate(((0, 0), (PARENT, 0x270e), (PARENT, 0x2db06), (PARENT + 0x100, 0x270e))):
        r = base_ram()
        r.put(NODE + 0xc, 4, parent)
        if parent:
            r.put(parent, 4, v)
        regs = dict(PLAIN)
        o = native(r.b, regs, 0x2dbac, 0, lambda q, tr: q in (0x2dbb6, 0x2dbbc))
        assert o is not None, k
        c = 1 if o['stop'] == 0x2dbb6 else 2
        assert c == (1 if parent and v == 0x270e else 2), (k, hex(o['stop']))
        row('chain-2dbac-288c-%d' % k, r, regs, 0x2dbac, o['stop'], 0, c, 2, o)
    # 49fc6 (the interpreter on ROM scripts): no synthetic world; the consumers 2d85e 2d8ac 2d9c6 2dbce have the declared-C rows above and the
    # real-producer chains of the V1 spec / real-ROM differential.


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=PARENT, a1=0x10c000, a2=0, a3=0, a4=REC8C, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    missing = 'missing or ambiguous physical program bus ROM byte'

    def err(name, entry, message, fail_pc, carry=0, puts=(), **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects b3c caller requires known carry', cp)
    # odd node / parent / player / stack: the entry block fails
    err('odd-node-2db06', 0x2db06, 'invalid animation machine write size/alignment', 0x2db06, a6=NODE + 1)
    err('odd-node-22920', 0x22920, odd, 0x22920, a6=NODE + 1)
    err('odd-parent-2d916', 0x2d916, odd, 0x2d916, puts=[(NODE + 0xc, 4, PARENT + 1)])
    err('odd-player-1c12e', 0x1c12e, odd, 0x1c12e, a0=PLAYERS[0] + 1)
    err('odd-stack-1c14c', 0x1c14c, odd, 0x1c14c, a7=SP + 1, a0=PLAYERS[0])
    err('odd-child-1c18a', 0x1c18a, 'invalid animation machine write size/alignment', 0x1c18a, a0=REC3E + 1)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('2d932-index-9', 0x2d932, missing, 0x2d932, d0=9)
    err('2d98e-index-23', 0x2d98e, missing, 0x2d98e, puts=[(NODE + 0xc, 4, PARENT), (PARENT + 0x7c, 1, 23)])
    err('2d95c-index-ff', 0x2d95c, missing, 0x2d95c, puts=[(NODE + 0xc, 4, PARENT), (PARENT + 0x8a, 2, 0xff)])
    err('2db6a-index-17', 0x2db6a, missing, 0x2db6a, puts=[(NODE + 0x7c, 1, 17)])
    # failures after executed stores (rollback; the failing PC differs from the entry):
    #   1c148 decrements BYTE 7(A4); 1c14c pushes D3 D2 D0, then BYTE 9e = 4 reads LONG 2285c (outside the synthetic tables)
    err('1c148-then-1c14c', 0x1c148, missing, 0x1c14c, puts=[(REC8C + 7, 1, 5), (PLAYERS[0] + 0x9e, 1, 4)], a0=PLAYERS[0])
    #   2db58 sets BYTE 15 bit 0 and stores BYTE 7d; 2db6a then reads 2da64 (BYTE 7c = 17)
    err('2db58-then-2db6a', 0x2db58, missing, 0x2db6a, puts=[(NODE + 0x7c, 1, 17), (NODE + 0x7d, 1, 3)])
    #   2db32 stores WORD 2c / BYTE 7d 7c; 2db88 reads WORD 14(A1) with A1 = an odd A5 + 538e
    err('2db32-then-2db88', 0x2db32, odd, 0x2db88, puts=[(NODE + 0xc, 4, PARENT), (PARENT + 0x7c, 1, 3), (PARENT + 0x36, 4, 0x80000000)], a5=A5 + 1)
    #   2d816 (BYTE 13 != ff) -> 2d822 reads WORD 3a of an odd node
    err('2d816-then-2d822', 0x2d816, odd, 0x2d822, puts=[(NODE + 1 + 0x13, 1, 0x10)], a6=NODE + 1)
    #   2d80a installs 2d810 (LONG (A6)), 2d810 pushes the return LONG, then the JSR target 43e34 runs with an odd A6 (kept out: the failing PC would be
    #   inside another executor).


def main():
    rng = random.Random(0xB3C)
    gen_singles(rng)
    gen_paths(rng)
    gen_consumers(rng)
    gen_errors()
    out = []
    for d in ROWS:
        regs = ','.join('0x%x' % v for v in d['regs'])
        if d['error'] is None:
            outr = ','.join('0x%x' % v for v in d['out'])
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",NULL,0x0,{%s},%d,%d,%dULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'], outr, d['c'],
                                                                                    d['single'], d['digest']))
        else:
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s","%s",0x%x,{0},0,%d,0ULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'], d['error'],
                                                                                   d['fail'], d['single']))
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
    print('chain rows', sorted((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2))
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
