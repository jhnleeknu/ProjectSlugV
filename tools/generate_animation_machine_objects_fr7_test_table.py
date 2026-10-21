"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr7_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
only data areas, never code bytes of the unit): the bank-window LONGs 200094 / 2000b4 and the LONG table behind 200094 (2a2ffc..2a30a0: 3ad48 /
cde42 / d2f9a), the LONG table 3cd22..3cd36 (3ad60, indices -1..3), the WORD tables 4411e..443a0 (3ae18 sine / cosine), the screen rectangle 3b73e
(1ab80 of 3ae6e), the score BCD table 48a38..48a48 and the BCD BYTEs e625c / e625d (e625e / e6284 via 4ad4a), the records d2652..d2672 (d2776..).
A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as is a run that lands inside the unit on a PC that
is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG 3e(A6) / 92(A6) declared), A0 = the attack record ATK 10fb00 (or
10e400), A1 = the hit record HIT 10fc00 / MULT 10fc80 / 10ea00, A2 = the target object 100cb8 / 10e400 (LONG 56(A2) = HIT), A4 = the pad record PAD
10fd80, A5 = 108000 (LONG 5e26 = PAD, BYTE 5744, WORDs 5af2 5b7c 5b82 5492 and the frame counter WORD 10000e), the BCD BYTEs 10de14..10de1f, seeded
BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7, the declared stack values the entered block pops, and the hint worlds of the
V1 spec (tools/unit_fixture_specs/fr7.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'a2_mirror' the target in the
upper mirror, 'a5_mirror' A5 at 1f8000).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer (only producers that read RAM / the synthetic bytes and write no PVC port; the generator
            keeps a chain when it produced both C values): stop = the consumer's successor.  The others have declared-C rows only (V1 and the
            real-ROM differential run the real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 4c1b6 (ANDI; RTS) Clear, 4c1d6 (ORI; RTS) Set.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr7_test_table.py  (rewrites the generated section in place)
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
import fr7 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr7_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
SET_SET, CLEAR_SET = set(B.SET_SET), set(B.CLEAR_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC1, PARENT, SIBLING = 0x10ea00, 0x10eb00, 0x10ec00
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
ATK, HIT, MULT, PAD, DREC = B.ATK, B.HIT, B.MULT, B.PAD, B.DREC
BANK_TABLE = 0x2a3000                               # the synthetic destination of the bank-window LONG 200094 (CPU address with bank base 200000)


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (never code bytes of the unit)."""
    srng = random.Random(0xF74C)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    out = []
    out.append((0x200094, l(BANK_TABLE)))                                                                            # cde42 / d2f9a
    out.append((0x2000b4, l(0x2a5000)))                                                                              # 3ad48 (stored only)
    out.append((BANK_TABLE - 4, b''.join(l(0x2a7000 + 0x40 * k) for k in range(42))))                                # 2a2ffc..2a30a4 (index -1..40)
    out.append((0x3cd22, b''.join(l(0x2a8000 + 0x40 * k) for k in range(5))))                                       # 3ad60 (index -1..3)
    out.append((0x3b73e, w(0xfff8) + w(0) + w(0x10) + w(0x10)))                                                     # 1ab80 (3ae6e)
    out.append((0x4411e, b''.join(w(srng.getrandbits(16)) for k in range(321))))                                    # 3ae18 (any sign)
    out.append((0x48a38, bytes([0x00, 0x05, 0x01, 0x00, 0x99, 0x99, 0x00, 0x50, 0x12, 0x34, 0x00, 0x01, 0x98, 0x76, 0x00, 0x00])))  # e6284 via 4ad4a
    out.append((0xe625c, bytes([0x01, 0x23])))                                                                      # e6284: ABCD -(A2) BYTEs
    out.append((0xd2652, b''.join(l(v) for v in (REC1, 0x22, CHILD, 0x23, REC1, 0x24, 0x10e600, 0x25))))             # d2776..d279a records
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
SUCC = {0x3ae78: (0x3ae82, 0x3ae7c), 0xd308e: (0xd3092, 0xd3094), 0x4c128: (0x4c14a, 0x4c12c), 0x4c182: (0x4c1a4, 0x4c186), 0xcdd3c: (0xcdd46, 0xcdd40),
        0xcdede: (0xcdee8, 0xcdee2), 0xd3080: (0xd3084, 0xd3094), 0xcde9c: (0xcdea0, 0xcdeb2)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / synthetic bytes and both C values occur
CHAIN_CANDIDATES = tuple(B.CHAINS)


def scc_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (this unit has no SCC / SCS consumer)."""
    return 1 if o['stop'] == SUCC[cons][0] else 2


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
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or m.ports:
        return None                                 # FR7 writes no PVC port (the 49fc6 chain is dropped here)
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
    if p in CONS_SET:
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
VB = tuple(B.VB)
VW = tuple(B.VW)
VL = tuple(B.VL)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = set(B.POINTERS)
STACK = dict(B.STACK)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'scs', 'scc', 'abcd'):
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((ATK, ATK, CHILD)),
                a1=rng.choice((HIT, MULT, REC1)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=rng.choice((PAD, CHILD)), a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 0x12340001, 0xffff, 0x8000, 0x4000, 0x12340002))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0x8000, 0xffff, 0x123456a5))
    if rng.random() < 0.4:
        regs['d3'] = rng.choice((0, 1, 2, 3, 7, 0x7fff, 0x8000, 0xffff, 0x12340002))
    if rng.random() < 0.4:
        regs['d2'] = rng.choice((0, 1, 0x10000, 0x8000, 0xffff, 0x12340010))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if (reg == 6 and disp in POINTERS) or (reg == 2 and disp == 0x56) or (reg == 5 and disp == 0x5e26):
            continue                                    # (A6) callback LONG, the node links and the pointer fields are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    close = rng.random() < 0.7
    # the declared records (the same layout as the V1 spec): ATK (A0), HIT (LONG 56(A2)) with MULT, PAD (LONG 5e26(A5)), DREC (d2f9a)
    r.put(ATK, 2, rng.choice((0, 1, 2, 3, 0xffff, 0x8000)))
    r.put(ATK + 2, 1, rand_val(rng, 1))
    r.put(ATK + 3, 1, rand_val(rng, 1))
    for off in (4, 6, 8):
        r.put(ATK + off, 2, rng.choice((0, 1, 0x10, 0x100, 0x7fff, 0xffff, rand_val(rng, 2))))
    for k, v in enumerate(B.rects(rng, rng.choice((1, 1, 2, 3)), close)):
        r.put(ATK + 0x12 + 4 * k, 4, v)
    r.put(HIT + 8, 2, rand_val(rng, 2))
    r.put(HIT + 0xa, 2, rng.choice((0, 1, 2, 4, 7, 0x8001, rand_val(rng, 2))))
    r.put(HIT + 0x10, 1, rng.choice((0, 0, 1, 0x80, 0xff)))
    r.put(HIT + 0x11, 1, rng.choice((0, 1, 1, 2)))
    r.put(HIT + 0xc, 4, rng.choice((MULT, MULT, 0)))
    for k, v in enumerate(B.rects(rng, rng.choice((1, 1, 2, 3)), close)):
        r.put(HIT + 0x12 + 4 * k, 4, v)
    for k in range(-2, 8):
        r.put(MULT + 2 * k, 2, rng.choice((0, 1, 0x80, 0x100, 0xffff, rand_val(rng, 2))))
    for off in (4, 5, 6, 7):
        r.put(PAD + off, 1, rng.choice((0, 1, 0x7f, 0x80, 0xff, 0xb, 0xb) if off == 7 else (0, 1, 0x7f, 0x80, 0xff)))
    r.put(DREC, 4, rng.choice((REC1, CHILD)))
    r.put(DREC + 4, 4, rng.choice((0x22, 0x25, 0, 0xffff, 0x4001, 0x8000)))
    r.put(regs['a2'] + 0x56, 4, rng.choice((HIT, HIT, HIT, 0, REC1)))
    r.put(A5 + 0x5e26, 4, rng.choice((PAD, PAD, CHILD)))
    r.put(NODE + 0x3e, 4, rng.choice((ATK, REC1)))
    r.put(NODE + 0x92, 4, rng.choice((0x3b73e, REC1)))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    for a in (PLAYER1, PLAYER2, CHILD, REC1):
        for off in (0x42, 0x46, 0x4a, 0x4e):
            r.put(a + off, 2, rand_val(rng, 2))
    r.put(A5 + 0x5744, 1, rng.choice((0, 0x7f, 0x80, 0xff)))
    for off in (0x5af2, 0x5b7c, 0x5b82, 0x5492):
        r.put(A5 + off, 2, rand_val(rng, 2))
    r.put(A5 - 0x7ff2, 2, rand_val(rng, 2))                                                 # 4356e: the frame counter WORD 10000e
    for k in range(12):                                                                     # e6284: the BCD BYTEs
        r.put(0x10de14 + k, 1, rng.choice((0, 0x01, 0x09, 0x10, 0x50, 0x99, rng.getrandbits(8))))
    pops = []
    for size, kind in STACK.get(s, ()):
        n = 4 if size == 'L' else 2
        v = {'node': rng.choice((CHILD, REC1, PLAYER1, HIT)), 'small': rng.choice((0, 1, 2, 3)), 'atk': ATK, 'drec': rng.choice((DREC, DREC, 0xd2652, 0xd266a)),
             'any': rand_val(rng, n)}[kind]
        pops.append((n, v))
    depth = sum(n for n, v in pops)
    at = SP - depth
    for n, v in pops:
        r.put(at, n, v)
        at += n
    regs['a7'] = SP - depth
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((regs['a5'] + off) & 0xffffff, n, v)
        if hint.get('atk') is not None:
            regs['a0'] = ATK
            for off, n, v in hint['atk']:
                r.put(ATK + off, n, v)
        if hint.get('hit') is not None:
            r.put(regs['a2'] + 0x56, 4, HIT)
            for off, n, v in hint['hit']:
                r.put(HIT + off, n, v)
        if hint.get('pad') is not None:
            r.put(A5 + 0x5e26, 4, PAD)
            for off, n, v in hint['pad']:
                r.put(PAD + off, n, v)
        for off, n, v in hint.get('a2off', []):
            a = (regs['a2'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        if hint.get('a2_mirror'):
            regs['a2'] = regs['a2'] | 0xf0000           # the target object in the upper RAM mirror
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
        if hint.get('a5_mirror'):
            regs['a5'] = A5 | 0xf0000                   # A5 in the upper RAM mirror (1f8000 = 108000)
        if hint.get('stack'):
            at = regs['a7']
            for n, v in hint['stack']:
                r.put(at, n, v)
                at += n
    return r, regs


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x28ae, 0x2a00, 0x3af8, 0x8ebe, 0x1a988, 0x1aa3a, 0x1ab80, 0x43e08, 0x43e34, 0x43e38, 0x43ea4, 0x43eb8, 0x443d2, 0x44602, 0x46d72, 0x497a6,
                 0x49a58, 0x49a84, 0x49f8c, 0x49fc6, 0x4bb52, 0x4bce0, 0x4be2c, 0x4be34, 0x4be50, 0x4bfa4, 0x4c0b0, 0xd3c2a, 0xe625e, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer


def hints(s):
    """The V1 spec hint worlds (fr7.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


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
            if (nxt in CONS_SET and s not in SET_SET | CLEAR_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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


PATH_ENTRIES = (0x3611e, 0x3adae, 0x3adec, 0x3ae04, 0x4356e, 0x4abc0, 0x4abca, 0x4abe6, 0x4ac0a, 0x4ac1e, 0x4ac3a, 0x4ac4a, 0x4acda, 0x4acee, 0x4ad12,
                0x4ad18, 0x4ad38, 0x4ad6c, 0x4ad7c, 0x4ad82, 0x4ad8e, 0x4ad94, 0x4adc4, 0x4ae0e, 0x4ae32, 0x4c108, 0x4c12c, 0x4c132, 0x4c162, 0x4c186,
                0x4c18c, 0xcc5e8, 0xcc958, 0xcc976, 0xcc996, 0xcc9bc, 0xcc9e8, 0xcca0a, 0xcca38, 0xcdd46, 0xcdd50, 0xcdd70, 0xd2ff4, 0xd3014, 0xd3032,
                0xd3068, 0xe8b7e, 0xe8b80, 0xe8ba0, 0xe8bd6, 0xe8bf0, 0xe8c04, 0xd2776, 0xcdec0, 0x3adc6)


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
    """A world for a real producer chain (RAM / synthetic producers only)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d7=rng.getrandbits(32)))
    for off in (0x42, 0x46, 0x4a, 0x4e):                       # 1ab80: WORD positions
        r.put(NODE + off, 2, rng.choice((0, 0x10, 0x80, 0x100, 0x180, 0x200, 0x7fff, 0x8000, rng.getrandbits(16))))
    r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0xd3084:                                         # 1ab80 with A0 := LONG 92(A6): the synthetic screen rectangle or a RAM record
        r.put(NODE + 0x92, 4, rng.choice((0x3b73e, REC1)))
    if entry in (0xcdd36, 0xcded8, 0xd3072):                     # 49fc6: LONG 26(A6) = 0 -> ORI Set (it writes the PVC bank ports: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, REC1)))
    if entry == 0xcde96:                                         # 497a6: BYTE 10fd92 = 0 -> ORI Set
        r.put(0x10fd92, 1, rng.choice((0, 1, 0x80)))
    return r, regs


CHAINS = []


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            assert scc_value(cp, o) == carry, (hex(cp), carry)
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags (or the written BYTE) decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        clr, st = SUCC[cons]
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st) and len(tr) > 0 and cons in tr)
            if o is None or cons not in o['trace']:
                continue
            c = scc_value(cons, o)
            if seen.get(c, 0) >= 3:
                continue
            seen[c] = seen.get(c, 0) + 1
            rows.append((k, r, regs, o, c))
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        print('chain %x -> %x: %s' % (entry, cons, dict(seen)))
        if set(seen) != {1, 2}:
            continue                                             # the producer reads ROM data / writes ports or one C value never occurred: declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=ATK, a1=HIT, a2=PLAYER1, a3=0, a4=PAD, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr7 caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node (MOVE.W 42(A6),D0 read; MOVE.W #122,20(A6) write), odd stack (MOVEM.L (A7)+ of 3ae04), odd record (MOVE.W (A0),D0 of 4abca; MOVE.L
    # (A3)+ of 4ad8e), odd frame (MOVE.W #4,4(A7) of 4c0f0): the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-cc5e8', 0xcc5e8, odd, 0xcc5e8, stop=0xcc5f6, a6=NODE + 1)
    err('odd-node-3ad48', 0x3ad48, wodd, 0x3ad48, stop=0x3ad60, a6=NODE + 1)
    err('odd-stack-3ae04', 0x3ae04, odd, 0x3ae04, stop=0x3ae12, a7=SP + 1)
    err('odd-a0-4abca', 0x4abca, odd, 0x4abca, stop=0x4abde, a0=ATK + 1)
    err('odd-a0-4ad8e', 0x4ad8e, odd, 0x4ad8e, stop=0x4ad94, a0=ATK + 1)
    err('odd-frame-4c0f0', 0x4c0f0, wodd, 0x4c0f0, stop=0x4c102, a7=SP + 1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   4abc0 (A0 = 0) -> 4ad6a RTS at an odd A7
    err('4abc0-then-4ad6a', 0x4abc0, odd, 0x4ad6a, a0=0, a7=SP + 1)
    #   cdd6c (BRA) -> cdd84 RTS at an odd A7
    err('cdd6c-then-cdd84', 0xcdd6c, odd, 0xcdd84, a7=SP + 1)
    #   d2776 (D0 := 167, A0 := d2652) -> d2f90 MOVE.L A0,-(A7) at an odd A7
    err('d2776-then-d2f90', 0xd2776, odd, 0xd2f90, stop=0xd2f9a, a7=SP + 1)
    #   3adc6 ((A6) := 3add4, enters it) -> 3add4 MOVE.L 3a(A6),-(A7) at an odd A7
    err('3adc6-then-3add4', 0x3adc6, odd, 0x3add4, stop=0x3adec, a7=SP + 1)
    #   e8bbe (NEG.L) -> e8bc2 (LONGs 36 / 3a written) -> JSR 4be34 at an odd A7
    err('e8bbe-then-e8bc2', 0xe8bbe, odd, 0xe8bc2, stop=0x4be34, a7=SP + 1)


def main():
    rng = random.Random(0xF74B)
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
    tables.append('const std::uint32_t CHAINED[]={%s};' % ','.join('0x%x' % c for e, c in CHAINS))
    tables.append('const std::uint32_t CHAIN_FROM[]={%s};' % ','.join('0x%x' % e for e, c in CHAINS))
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
    print('chains kept', [('%x' % e, '%x' % c) for e, c in CHAINS])
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
