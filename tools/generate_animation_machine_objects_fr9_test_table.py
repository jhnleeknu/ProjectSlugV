"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr9_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000).  FR9 reads no fixed-ROM or banked data byte (its callees only receive addresses), so no synthetic
physical byte is overlaid and the C++ test runs with an empty physical ROM: a native run that reads any fixed-ROM or banked byte is dropped (that is a
callee run), as is a run that lands inside the unit on a PC that is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00), A0 = 10e400 / 10ea00 (child), A1 / A2
= 10ea00 / 100cb8, A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7, the declared stack WORDs the entered
block pops, and the hint worlds of the V1 spec (tools/unit_fixture_specs/fr9.py hint_worlds, converted to absolute addresses; 'mirror' puts the node
at 1fe000, 'parent' / 'parent_mirror' the parent 10eb00 / 1feb00).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, or the
            routing-outside PC afb3c of a computed landing).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer (only producers that read RAM only and write no PVC port; the generator keeps a chain when
            it produced both C values): none of the 5 FR9 producers qualifies (49fc6 writes the bank ports, the b0468 Set side reads the ROM table
            b067e, the 2986 failure side is the caller-X error), so the consumers have declared-C rows only (V1 and the real-ROM differential run the
            real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: b0578 (ORI.B #1,CCR) Set.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr9_test_table.py  (rewrites the generated section in place)
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
import fr9 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr9_test.cpp'
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


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def load_program():
    program = bytes(ob.load_rom())
    assert hashlib.sha256(program).hexdigest() == '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    return program


PROGRAM = load_program()
FIXED = (ctypes.c_ubyte * 0x100000).from_buffer_copy(PROGRAM[:0x100000])


# consumer -> (C clear successor, C set successor)
SUCC = {0xafd90: (0xafda2, 0xafd94), 0xaff3c: (0xaff4e, 0xaff40), 0xb0048: (0xb005a, 0xb004c), 0xafe6a: (0xafe84, 0xafe6e), 0xb0556: (0xb057c, 0xb055e)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM and both C values occur
CHAIN_CANDIDATES = ((0xafe66, 0xafe6a),)


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
            stray.append((hex(address), size))     # FR9 reads no fixed-ROM / banked byte: a run that does is a callee run
    c.hook_add(UC_HOOK_CODE, at, begin=0, end=0xffffff)
    c.hook_add(UC_HOOK_MEM_READ, rd, begin=0, end=0x2fffff)
    try:
        c.emu_start(pc, 0xffffff, count=2000000)
    except unicorn.UcError:
        return None
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.bank != 0x200000:
        return None
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or m.ports:
        return None                                 # FR9 writes no PVC port (a producer that does is dropped here)
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, REC1)),
                a1=rng.choice((REC1, PLAYER1)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=REC1, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 7, 0xa, 0xb, 0x1a, 0x1b, 0x12340001, 0xffff, 0x8000, 0x10000, 0x100, 0x12340002))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0x8000, 0xffff, 0x123456a5))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG, the node links and the pointer fields are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links and the parent (LONG c(A6): afd94 / aff40 / b004c SUBQ.B #1,62(A0))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(PARENT + 0x62, 1, rand_val(rng, 1))
    pops = []
    for size, kind in STACK.get(s, ()):
        n = 4 if size == 'L' else 2
        pops.append((n, rand_val(rng, n)))
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
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('parent', []):
            r.put(NODE + 0xc, 4, PARENT | (0xf0000 if hint.get('parent_mirror') else 0))
            r.put(PARENT + off, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
        if hint.get('stack'):
            at = regs['a7']
            for n, v in hint['stack']:
                r.put(at, n, v)
                at += n
    return r, regs


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x2986, 0x2a00, 0x3af8, 0x8ff4, 0x43e34, 0x43ea4, 0x443d2, 0x490ba, 0x49214, 0x49274, 0x49a58, 0x49f8c, 0x49fc6, 0x4be06, 0x4be34,
                 0xe9112, 0xb0468, 0xaf92c, 0xaf96a, 0xafc16, 0xb005e, 0xafb3c, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer


def hints(s):
    """The V1 spec hint worlds (fr9.hint_worlds) of the block; converted to absolute addresses by world()."""
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
            if nxt == s:
                continue                                 # a computed jump back to its own block: a stop at the entry is a zero-step run
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


PATH_ENTRIES = (0xaf8d8, 0xaf8de, 0xaf8fe, 0xaf906, 0xaf99c, 0xaf9a6, 0xaf9b0, 0xaf9bc, 0xafa34, 0xafa40, 0xafab8, 0xafac4, 0xafb44, 0xafb5e, 0xafb78,
                0xafbaa, 0xafbbe, 0xafbfe, 0xafd1c, 0xafd2a, 0xafd38, 0xafdc2, 0xafdd2, 0xafdfe, 0xafe20, 0xafe30, 0xafe54, 0xafe74, 0xafe7a, 0xafe80,
                0xafe84, 0xafebc, 0xafec4, 0xafece, 0xafed4, 0xaff5c, 0xaff6a, 0xaff78, 0xaff82, 0xaff90, 0xaffc0, 0xb0014, 0xb001a, 0xb0024, 0xb0032,
                0xb051a, 0xb0578, 0xaf9e4, 0xafb88, 0xafa74, 0xafafc, 0xafbba)


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
            if any(p in CONS_SET for p in ex) or not allowed(o['stop']) or o['stop'] == s:
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
    """A world for a real producer chain (RAM producers only)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d7=rng.getrandbits(32)))
    if entry == 0xafe66:                                         # b0468: WORD 3a >= 0 -> RTS with C clear; < 0 -> the 4ae4a search (ROM table b067e)
        r.put(NODE + 0x3a, 2, rng.choice((0, 1, 0x7fff, 0x8000, 0xffff)))
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
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=PLAYER1, a3=0, a4=0, a5=A5, a6=NODE, a7=SP)
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
        err('unknown-c-%x' % cp, cp, 'objects fr9 caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node (MOVE.W 92(A6) read of b051a, MOVE.W D0,96(A6) write of af8de, MOVEA.L c(A6),A0 of afd94), odd stack (MOVE.W #0,-(A7) of b0524, the
    # JSR of af8cc, the MOVEM.W pop of b0556 with a declared C): the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-b051a', 0xb051a, odd, 0xb051a, stop=0xb0524, a6=NODE + 1)
    err('odd-node-af8de', 0xaf8de, wodd, 0xaf8de, stop=0xaf8f2, a6=NODE + 1)
    err('odd-node-afd94', 0xafd94, odd, 0xafd94, stop=0x2a00, a6=NODE + 1)
    err('odd-stack-b0524', 0xb0524, odd, 0xb0524, stop=0x2986, a7=SP + 1)
    err('odd-stack-af8cc', 0xaf8cc, odd, 0xaf8cc, stop=0x490ba, a7=SP + 1)
    err('odd-stack-b0556', 0xb0556, odd, 0xb0556, carry=2, stop=0xb055e, a7=SP + 1)
    # computed landings: af9bc / afa40 D0.B = 1c -> afa38 / afabc (inside a block), afac4 D0.B = 1c -> afb40 (inside afb3e), 1b -> afb3c (unrouted)
    err('af9bc-to-afa38', 0xaf9bc, 'unsupported animation objects fr9 PC', 0xafa38, d0=0x1234ff1c)
    err('afa40-to-afabc', 0xafa40, 'unsupported animation objects fr9 PC', 0xafabc, d0=0x1c)
    err('afac4-to-afb40', 0xafac4, 'unsupported animation objects fr9 PC', 0xafb40, d0=0x1c)
    err('afac4-to-afb3c', 0xafac4, 'unsupported animation machine PC', 0xafb3c, d0=0x1b)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('af9bc-then-afb58', 0xaf9bc, odd, 0xafb58, stop=0x49a58, d0=2, a7=SP + 1)
    err('afb78-then-afcf2', 0xafb78, odd, 0xafcf2, stop=0x3af8, d0=3, a7=SP + 1)
    err('afe80-then-afe8e', 0xafe80, wodd, 0xafe8e, stop=0xafe94, puts=((NODE + 0x16, 1, 0x80),), a6=NODE + 1)
    err('b0578-then-b057c', 0xb0578, odd, 0xb057c, a7=SP + 1)
    err('afed4-then-aff24', 0xafed4, odd, 0xaff24, stop=0x49274, a7=SP + 1)


def main():
    rng = random.Random(0xF94B)
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
    tables.append('const std::uint32_t CHAINED[]={%s};' % ','.join(['0x%x' % c for e, c in CHAINS] + ['0x0']))     # 0-terminated (may be empty)
    tables.append('const std::uint32_t CHAIN_FROM[]={%s};' % ','.join(['0x%x' % e for e, c in CHAINS] + ['0x0']))
    tables.append('const unsigned int EVEN_COUNT=%d;' % sum((hi - lo) // 2 for lo, hi in RANGES))
    tables.append('const Fixture FIXTURES[]={')
    tables += out
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
    print('table entries never the stop of a single row of their jump block',
          [(hex(j), [hex(e) for e in ents if e not in succ.get(j, set())]) for j, ents in sorted(B.TABLE_JUMPS.items()) if not set(ents) <= succ.get(j, set())])
    print('chains kept', [('%x' % e, '%x' % c) for e, c in CHAINS])
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
