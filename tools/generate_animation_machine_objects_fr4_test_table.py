"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr4_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
only data areas, never code bytes): the sound LONG table cdf3e..cdf56 (cc610 / cc654; its LONGs point to RAM records 10fe40.. so the sound WORDs are
world RAM), the boxes 72d5e..72d66 / 87a8c..87a94 (the A0 of 1ab80 / 1ab02 in the producer chains), the bank-window LONGs 2000d0 / 2000d4 / 200080 /
200140 (-> 2a1000 / 2a2000 / 2a5000 / 2a6000) with the LONGs behind them.  A native run that reads any other fixed-ROM or banked byte is dropped (the
C++ has no bytes there), as is a run that lands inside the unit on a PC that is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent 10eb00, LONG 8(A6) = the sibling 10ec00),
A0 = 10e400, A1 = 10ea00, A5 = 108000 (WORD 53a2), the BYTE 10fd92 of 497a6, the player records 100cb8 / 100da8, seeded BYTE / WORD / LONG field
edits (sign boundaries included), seeded D0-D7, the declared stack WORDs 7310c pops, and the hint worlds of the V1 spec (tools/unit_fixture_specs/
fr4.py hint_worlds, converted to absolute addresses).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit or a
            computed table target cc7ac.. / cc82e..).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA / BEQ exits, a computed table target, the RTS
            sentinel) or a consumer.
  single 2  a consumer entered through its real producer (only producers that read RAM / the synthetic bytes; the generator keeps a chain when it
            produced both C values): stop = the consumer's successor; the native branch on the real flags decides it.  The others have declared-C rows
            only (V1 and the real-ROM differential run the real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  No FR4 block produces a
known C (no ORI / ANDI CCR).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr4_test_table.py  (rewrites the generated section in place)
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
import fr4 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr4_test.cpp'
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
WINDOWS = {0x2000d0: (0x2a1000, (0x4, 0xc, 0x28)), 0x2000d4: (0x2a2000, (0x4, 0xc, 0x28)), 0x200080: (0x2a5000, (0x4c, 0x50, 0x54, 0x58, 0x5c)),
           0x200140: (0x2a6000, (0x90, 0xdc))}
SOUND_RECORDS = 0x10fe40                            # the 6 synthetic sound LONGs point to RAM records 10fe40 + 8 k (WORD +0, WORD +2)
# the computed table targets (contract decision 2): stop-only, routed by a later unit
TARGETS = [0xcc7ac + 4 * k for k in range(27)] + [0xcc82e + 4 * k for k in range(27)]


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    srng = random.Random(0xF44C)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    sound = b''.join(l(SOUND_RECORDS + 8 * k) for k in range(6))                                                      # cdf3e..cdf56
    box1 = b''.join(w(v) for v in (0xfff8, 0xfff0, 0x10, 0x50))                                                       # 72d5e: WORD x, y, w, h
    box2 = b''.join(w(v) for v in (0xfff0, 0xfff8, 0x20, 0x10))                                                       # 87a8c
    out = [(0xcdf3e, sound), (0x72d5e, box1), (0x87a8c, box2)]
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
SUCC = {0x73124: (0x7312e, 0x73128), 0x73468: (0x7347a, 0x7346c), 0x878ec: (0x8790a, 0x878f0), 0x87a9e: (0x87aa8, 0x87aa2), 0xcc60c: (0xcc610, 0xcc654),
        0xcc638: (0xcc63c, 0xcc642), 0xcc67c: (0xcc680, 0xcc686)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / synthetic bytes and both C values occur
CHAIN_CANDIDATES = tuple(B.CHAINS)


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
        return None                                 # FR4 writes no PVC port
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
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x72, 0x8c}
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


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, REC1, PLAYER1)),
                a1=rng.choice((REC1, CHILD)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=CHILD, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 0x3f, 0x40, 0x41, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340040, 0x80000000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x8000, 0xffff, 0x123456a5))
    if rng.random() < 0.4:
        regs['d3'] = rng.choice((0, 1, 2, 3, 0x7fff, 0x8000, 0xffff, 0x12340002))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG, the node links and the table index WORD 76 are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x8c, 2, rng.choice((0, 1, 2, 3, 4, 5, 5, 0)))
    r.put(NODE + 0x72, 4, rng.choice((0, 0, REC1)))
    for off in (0x62, 0x63, 0x15):
        r.put(PARENT + off, 1, rand_val(rng, 1))
    for a in (PLAYER1, PLAYER2, CHILD, REC1):
        r.put(a + 0x42, 2, rand_val(rng, 2))
        r.put(a + 0x46, 2, rand_val(rng, 2))
        r.put(a + 0x62, 1, rand_val(rng, 1))
        r.put(a + 0x63, 1, rand_val(rng, 1))
    for k in range(6):
        r.put(SOUND_RECORDS + 8 * k, 2, rng.choice((0, 0x0c49, 0x8000, 0xffff, rand_val(rng, 2))))
        r.put(SOUND_RECORDS + 8 * k + 2, 2, rng.choice((0, 0x0c4d, 0x8001, 0x7fff, rand_val(rng, 2))))
    r.put(0x10fd92, 1, rng.choice((0, 0, 1, 0x80)))
    r.put(A5 + 0x53a2, 2, rand_val(rng, 2))
    pops = []
    for size, kind in STACK.get(s, ()):
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
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((regs['a5'] + off) & 0xffffff, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('parent', []):
            r.put(PARENT + off, n, v)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
        if hint.get('stack'):
            at = regs['a7']
            for n, v in hint['stack']:
                r.put(at, n, v)
                at += n
    return r, regs


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x28ae, 0x2a00, 0x8ebe, 0x8ff4, 0x1ab02, 0x1ab80, 0x43e34, 0x48502, 0x491c4, 0x49290, 0x4970a, 0x497a6, 0x49a58, 0x49f8c, 0x49fc6,
                 0x4ae4a, 0x4b54e, 0x4bc04, 0x4be34, 0x4bfa4, 0x70036, 0x70054, 0x7054c, 0x71a80, 0xc6a96, 0xe9112, STOP} | set(TARGETS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer (ea8e8 -> ea8fc: the modelled Clear of ea8e8)


def hints(s):
    """The V1 spec hint worlds (fr4.hint_worlds) of the block; converted to absolute addresses by world()."""
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


PATH_ENTRIES = (0x72f8a, 0x72f90, 0x7306a, 0x730a6, 0x730ba, 0x730ea, 0x73218, 0x73296, 0x732ac, 0x732c2, 0x732d2, 0x73304, 0x73392, 0x7347a, 0x734ac,
                0x734b4, 0x734be, 0x734d0, 0x734da, 0x73506, 0x73520, 0x73542, 0x878dc, 0x878f0, 0x8790c, 0x87912, 0x87982, 0x879b6, 0x879e4, 0x87a02,
                0x87a28, 0x87a3e, 0x87a50, 0x87a6c, 0x87a94, 0xbc7d6, 0xbca2c, 0xbca62, 0xbca6e, 0xcc600, 0xcc610, 0xcc654, 0xcc778, 0xcc784, 0xcca76,
                0xcca80)


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
    for off in (0x42, 0x46, 0x4a, 0x4e):                       # 1ab80 / 1ab02: WORD positions (and the LONG 42 / 46 vs 4a / 4e of 1ab02)
        r.put(NODE + off, 2, rng.choice((0, 0x10, 0x80, 0x100, 0x180, 0x200, 0x7fff, 0x8000, rng.getrandbits(16))))
    r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0x73120:                                         # 7054c: BYTE 61 bit 5, BYTE 82 bits 2 / 4 / 5 / 6, BYTE 6f
        r.put(NODE + 0x61, 1, rng.choice((0, 0x20, 0xff)))
        r.put(NODE + 0x82, 1, rng.choice((0, 0x04, 0x10, 0x14, 0x20, 0x40, 0xff)))
        r.put(NODE + 0x6f, 1, rng.choice((0, 0x40)))
    if entry in (0xcc606, 0xcc632, 0xcc676):                     # 497a6: BYTE 10fd92 = 0 -> ORI Set, otherwise Clear
        r.put(0x10fd92, 1, rng.choice((0, 1)))
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
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        clr, st = SUCC[cons]
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st) and len(tr) > 0 and cons in tr)
            if o is None or cons not in o['trace']:
                continue
            c = 1 if o['stop'] == clr else 2
            if seen.get(c, 0) >= 3:
                continue
            seen[c] = seen.get(c, 0) + 1
            rows.append((k, r, regs, o, c))
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        print('chain %x -> %x: %s' % (entry, cons, dict(seen)))
        if set(seen) != {1, 2}:
            continue                                             # the producer reads ROM data or one C value never occurred: declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, c, 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=0, a3=0, a4=CHILD, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    inside = 'unsupported animation objects fr4 PC'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr4 caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node / stack / pointer: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-72fa8', 0x72fa8, odd, 0x72fa8, stop=0x72fb0, a6=NODE + 1)
    err('odd-node-7330e', 0x7330e, wodd, 0x7330e, stop=0x73316, a6=NODE + 1)
    err('odd-stack-7310c', 0x7310c, odd, 0x7310c, stop=0x70036, a7=SP + 1)
    err('odd-a0-cc63c', 0xcc63c, odd, 0xcc63c, stop=0xcc646, a0=CHILD + 1)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('cc610-table-rom', 0xcc610, missing, 0xcc610, stop=0xcc632, puts=[(NODE + 0x8c, 2, 0x10)])
    # computed landings inside the unit on a PC that is not a block start (F1 decision 3)
    err('cc7a0-lands-cc81c', 0xcc7a0, inside, 0xcc81c, d0=0x1c)
    err('cc822-lands-cca7a', 0xcc822, inside, 0xcca7a, d0=0x93)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   730ea (BYTE 15 bit 0 set) -> 730fa MOVEM.W D0-D1,-(A7) at an odd A7
    err('730ea-then-730fa', 0x730ea, odd, 0x730fa, stop=0x4bc04, puts=[(NODE + 0x15, 1, 1)], a7=SP + 1)
    #   87a6c (WORD 3a negative) -> 87a78 -> 87a84 -> 87a88 -> 87a8a RTS at an odd A7
    err('87a6c-then-87a8a', 0x87a6c, odd, 0x87a8a, puts=[(NODE + 0x3a, 2, 0x8000)], a7=SP + 1)
    #   cc778 (BYTE 5e != 0) -> cc780 JSR cca76 at an odd A7
    err('cc778-then-cc780', 0xcc778, odd, 0xcc780, stop=0xcca76, puts=[(NODE + 0x5e, 1, 3)], a7=SP + 1)
    #   cc798 (D0.B = 1b) -> cdc1c MOVE.L #cdc24,(A6) at an odd A6
    err('cc798-then-cdc1c', 0xcc798, wodd, 0xcdc1c, d0=0x1b, a6=NODE + 1)
    #   7351e (NEG.L D0) -> 73520 MOVE.L 92(A6) at an odd A6
    err('7351e-then-73520', 0x7351e, odd, 0x73520, stop=0x7353c, a6=NODE + 1)


def main():
    rng = random.Random(0xF44B)
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
    tables.append('const std::uint32_t TARGETS[]={%s};' % ','.join('0x%x' % x for x in TARGETS))
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
