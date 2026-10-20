"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr6_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
only data areas, never code bytes of the unit): the bank-window LONGs 2000d0 / 2000d4 and the LONGs 6c / 58 behind them (72980 / 729ac), the WORDs
52486 / 52790 (50e06 / 50ef6), the WORD table 4411e..4431f (515a2), the LONG table d75ca..d760a (d75ce indices -1..14 of d7714 / d7766 / d7780) and the
BCD BYTEs e625c / e625d (ABCD -(A2) of e6284).  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as
is a run that lands inside the unit on a PC that is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent 10eb00 with its WORD 78, LONG 8(A6) = the
sibling 10ec00, LONG 80(A6) = the RAM sound script 10fd00, LONG 72(A6) = 0 or 10ea00), A0 = 10e400, A1 = 10ea00, A5 = 108000 (BYTEs 568e / 5683,
WORD 5df8, LONGs 5734 / 5738 and the fields of the entered block), the player records 100cb8 / 100da8, the absolute RAM LONG 100bf4 (289e), WORDs
10ddec..10ddf6 (d7714) and BCD BYTEs 10de14..10de1f (e6284), seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7, the
declared stack values the entered block pops, and the hint worlds of the V1 spec (tools/unit_fixture_specs/fr6.py hint_worlds, converted to absolute
addresses; 'mirror' puts the node at 1fe000, 'parent_mirror' the parent at 1feb00, 'a5_mirror' A5 at 1f8000).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer (only producers that read RAM / the synthetic bytes and write no PVC port; the generator
            keeps a chain when it produced both C values; the single-successor SCC / SCS consumers 50f62 d77da d7802 show the C in the BYTE they
            write): stop = the consumer's successor.  The others have declared-C rows only (V1 and the real-ROM differential run the real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome (or the written BYTE) against the declared C.  The
modelled C of the producers: 1aa72 485a2 49c4a (ANDI; RTS) and 51044 (AND.B) Clear, 1aa78 4859c 49c50 (ORI; RTS) and 51050 (ORI) Set, 50f62 Clear
after its MOVE.W.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr6_test_table.py  (rewrites the generated section in place)
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
import fr6 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr6_test.cpp'
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
# bank windows: the bank-window LONG -> a synthetic destination in the bank (CPU 2a1000 / 2a2000 with bank base 200000) and the LONG field that 72980 /
# 729ac read there (6c / 58; its value is only passed in A1 to 49f8c)
WINDOWS = {0x2000d0: (0x2a1000, 0x6c), 0x2000d4: (0x2a2000, 0x58)}
SCRIPT = B.SCRIPT                                   # the declared RAM sound script (LONG 80(A6))
FREE = 0x10f400                                     # the declared free node of the 28ae chain (LONG 104c9c)
TABLE_4411E = 0x4411e                               # WORD table of 515a2 (index 2 * BYTE: 4411e..4431f)
TABLE_D75CE = 0xd75ce                               # LONG table of d7714 / d7766 / d7780 (synthetic indices -1..14: d75ca..d760a)


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (never code bytes of the unit)."""
    srng = random.Random(0xF64C)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    out = []
    for win in sorted(WINDOWS):
        dest, field = WINDOWS[win]
        out.append((win, l(dest)))
        out.append((dest + field, l(0x2a7000 + (srng.getrandbits(10) << 1))))
    out.append((0x52486, w(0xff40)))                                                                                # 50e06: WORD 8e of the rise
    out.append((0x52790, w(0xff60)))                                                                                # 50ef6
    out.append((TABLE_4411E, b''.join(w(srng.getrandbits(16)) for k in range(256))))                                 # 515a2 (any sign)
    out.append((TABLE_D75CE - 4, b''.join(l(0x2a3000 + 0x40 * (k + 1)) for k in range(16))))                          # d75ca..d760a (index -1..14)
    out.append((0xe625c, bytes([0x01, 0x23])))                                                                      # e6284: ABCD -(A2) BYTEs
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


# consumer -> (C clear successor, C set successor); 50f62 (SCC.B 62(A6)), d77da (SCS.B -(A7)) and d7802 (SCS.B D0) have one successor, their C shows
# in the BYTE they write
SUCC = {0x362cc: (0x362d2, 0x362d0), 0x4858e: (0x485a2, 0x48592), 0x48598: (0x4859c, 0x485a2), 0x50d0e: (0x50d12, 0x50d24), 0x50f62: (0x49214, 0x49214),
        0x51054: (0x51058, 0x51064), 0x729ee: (0x729f8, 0x729f2), 0xd77da: (0xd77e4, 0xd77e4), 0xd7802: (0xd780c, 0xd780c), 0xd7698: (0xd769c, 0xd76a6),
        0xd76b8: (0xd76f4, 0xd76bc), 0xd770e: (0xd7712, 0xd7714)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / synthetic bytes and both C values occur
CHAIN_CANDIDATES = tuple(B.CHAINS)


def scc_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor, or for the single-successor SCC / SCS consumers from the BYTE it wrote."""
    if cons == 0x50f62:
        return 1 if o['ram'][(NODE + 0x62) & 0xffff] == 0xff else 2
    if cons == 0xd77da:
        return 2 if o['ram'][o['regs']['a7'] & 0xffff] == 0xff else 1
    if cons == 0xd7802:
        return 2 if o['regs']['d0'] & 0xff == 0xff else 1
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
        return None                                 # FR5 writes no PVC port (the 49fc6 chain is dropped here)
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
    if p in B.CLEAR_AFTER:
        return 1 if c else 0                        # 50f62: SCC.B then MOVE.W #0,D0 (C := 0)
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
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x72, 0x80}
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
    r.put(PARENT + 0x78, 2, rand_val(rng, 2))                                               # 36292: WORD 78 of the parent
    r.put(NODE + 0x80, 4, rng.choice((SCRIPT, SCRIPT, SCRIPT + 4)))                        # 50de0: the RAM sound script
    for k in range(4):
        r.put(SCRIPT + 2 * k, 2, rng.choice((0xffff, 0xffff, 0x1886, 0x7fff, 0xfffe, 0x20, rand_val(rng, 2))))
    r.put(NODE + 0x72, 4, rng.choice((0, 0, REC1)))                                         # 703f6: 0 or the A0 of 4ae4a
    for a in (PLAYER1, PLAYER2, CHILD, REC1):
        r.put(a + 0x42, 2, rand_val(rng, 2))
        r.put(a + 0x46, 2, rand_val(rng, 2))
        r.put(a + 0x62, 1, rand_val(rng, 1))
        r.put(a + 0x63, 1, rand_val(rng, 1))
    r.put(A5 + 0x568e, 1, rng.choice((0, 0, 1, 2, 3)))                                      # 4855c / 4945e
    r.put(A5 + 0x5683, 1, rng.choice((0, 6, 7, 0x16, 0x10, 0xff, rng.getrandbits(8))))      # 4855c bits 0..2, 482aa bit 4
    r.put(A5 + 0x5df8, 2, rng.choice((0, 1, 2, 0x96, 0xffff)))                              # d764a
    for off in (0x5734, 0x5738):
        r.put(A5 + off, 4, rng.choice((0, 0, 1, 0x80000000, REC1)))                        # 49c38
    r.put(0x100bf4, 4, rng.choice((0x270e, 0x270e, 0, 0x2710, 0x270e0000)))                 # 289e: LONG (100bf4) = 270e -> Clear
    for k in range(6):                                                                      # d7714 (the d75ce indices -1..14 are synthetic)
        r.put(0x10ddec + 2 * k, 2, rng.choice((0, 1, 2, 5, 14, 0xffff)) if k in (0, 3) else rand_val(rng, 2))
    for k in range(12):                                                                     # e6284: the BCD BYTEs
        r.put(0x10de14 + k, 1, rng.choice((0, 0x01, 0x09, 0x10, 0x50, 0x99, rng.getrandbits(8))))
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
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        if hint.get('parent_mirror'):
            r.put(NODE + 0xc, 4, PARENT | 0xf0000)      # LONG c(A6) := the parent in the upper RAM mirror (1feb00 = 10eb00)
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
ALLOWED_STOPS = {0x289e, 0x28ae, 0x2a00, 0x3af8, 0x8ebe, 0xce02, 0x16ed2, 0x1bfb4, 0x43e04, 0x43e08, 0x43e34, 0x43ea4, 0x482aa, 0x490ba, 0x491b6, 0x49214,
                 0x4945e, 0x496c2, 0x49a58, 0x49a84, 0x49f8c, 0x49f96, 0x49fc6, 0x49fca, 0x4ae4a, 0x4b54e, 0x4bfa4, 0x4fce0, 0x515e0, 0x72dd2, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer


def hints(s):
    """The V1 spec hint worlds (fr6.hint_worlds) of the block; converted to absolute addresses by world()."""
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


PATH_ENTRIES = (0x19a00, 0x19a06, 0x19a12, 0x19a1e, 0x19a26, 0x19a32, 0x1aa66, 0x362b2, 0x362ba, 0x48210, 0x4855c, 0x48564, 0x49c38, 0x4fcb8, 0x50d12,
                0x50dd2, 0x50de0, 0x50e34, 0x50e60, 0x50ed0, 0x50f86, 0x50f90, 0x50fa2, 0x50ff0, 0x50ffe, 0x51014, 0x51024, 0x51032, 0x51044, 0x5107e,
                0x51086, 0x510b6, 0x510c8, 0x5157a, 0x515da, 0x703f6, 0x70406, 0x72978, 0x729d4, 0x729fc, 0xd767a, 0xd769c, 0xd76a6, 0xd76bc, 0xd76c4,
                0xd76e6, 0xd76f4, 0xd779e, 0xd77c0, 0xd77e4, 0xd780c, 0xd7812, 0xe625e, 0xe6270, 0xe6284, 0xe629c, 0x1a988, 0xe9148)


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
    if entry == 0x362c6:                                         # 482aa: BTST #4,5683(A5): 1 -> Clear, 0 -> Set
        r.put(A5 + 0x5683, 1, rng.choice((0x10, 0, 0xff, 0xef)))
    if entry == 0x48582:                                         # 289e: LONG (100bf4) = 270e -> Clear, otherwise Set
        r.put(0x100bf4, 4, rng.choice((0x270e, 0x270f, 0, 0x270e0000)))
    if entry == 0x48592:                                         # 1aa66: WORD 5418 >= 53ee (unsigned) -> Set
        a, b = rng.choice(((5, 5), (5, 6), (6, 5), (0x8000, 0x7fff), (0x7fff, 0x8000)))
        r.put(A5 + 0x5418, 2, a)
        r.put(A5 + 0x53ee, 2, b)
    if entry == 0x50d08:                                         # 4945e -> 49370: BYTE 568e(A5) = 0 -> ORI Set; the player WORDs 42
        r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3)))
        for a in (PLAYER1, PLAYER2):
            r.put(a + 0x42, 2, rng.getrandbits(16))
    if entry == 0x50f52:                                         # 28ae: free node list (LONG 104c9c -> FREE), WORD 104ca0 <= D0 (a) -> 290e Clear
        r.put(0x104c9c, 4, FREE)
        r.put(FREE + 8, 4, 0)
        r.put(0x104ca0, 2, rng.choice((0, 0xa, 0xb, 0x40)))
        r.put(NODE + 0x10, 2, rng.choice((0, 1, 0x7fff)))
    if entry == 0x51044:                                         # AND.B D3,D2 = 0 -> 51054 directly (Clear), otherwise 51050 ORI (Set)
        regs['d2'], regs['d3'] = rng.choice(((0xff, 0xff), (0xff, 0), (0, 0xff), (0x80, 0x80), (0x12345601, 0x9abcde02)))
    if entry in (0x729e8, 0xd77c8):                              # 49fc6: LONG 26(A6) = 0 -> ORI Set (it writes the PVC bank ports: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, REC1)))
    if entry == 0xd77ec:                                         # 49fca (A0 = A6 + 84): LONG 84(A6) = 0 -> Set (PVC bank ports: dropped)
        r.put(NODE + 0x84, 4, rng.choice((0, REC1)))
    if entry in (0xd7692, 0xd76b2, 0xd7708):                     # 4855c: every condition -> Set (289e and 1aa66 run as real producers)
        r.put(A5 + 0x568e, 1, rng.choice((0, 1, 1, 1)))
        r.put(A5 + 0x5683, 1, rng.choice((6, 6, 7, 2, 0x16)))
        r.put(0x100bf4, 4, rng.choice((0x2710, 0x2710, 0x270e)))
        r.put(A5 + 0x5418, 2, rng.choice((1, 1, 2, 3)))
        r.put(A5 + 0x53ee, 2, 2)
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
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=0, a3=0, a4=CHILD, a5=A5, a6=NODE, a7=SP)
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
        err('unknown-c-%x' % cp, cp, 'objects fr6 caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node (TST.W 8c(A6) read, MOVE.W #ffe2,7a(A6) write), odd stack (MOVE.L (A7)+ of 515da), odd script pointer (MOVE.W (A0)+ of 50de0), odd A1
    # (MOVE.W #9999,(A1) of e629c): the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-50dd2', 0x50dd2, odd, 0x50dd2, stop=0x50de0, a6=NODE + 1)
    err('odd-node-4fcb8', 0x4fcb8, wodd, 0x4fcb8, stop=0x4fcc4, a6=NODE + 1)
    err('odd-stack-515da', 0x515da, odd, 0x515da, a7=SP + 1)
    err('odd-script-50de0', 0x50de0, odd, 0x50de0, stop=0x50dee, puts=[(NODE + 0x80, 4, SCRIPT + 1)])
    err('odd-a1-e629c', 0xe629c, wodd, 0xe629c, stop=0xe62a6, a1=0x10de15)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   19a00 (D7 = 0) -> 19a1e -> 19a3e RTS at an odd A7
    err('19a00-then-19a3e', 0x19a00, odd, 0x19a3e, a7=SP + 1)
    #   4855c (BYTE 568e(A5) = 0) -> 485a2 ANDI; RTS at an odd A7
    err('4855c-then-485a2', 0x4855c, odd, 0x485a2, a7=SP + 1)
    #   d76f4 (5df8 := 1, enters d7700) -> d7700 -> d7708 JSR 4855c at an odd A7
    err('d76f4-then-d7708', 0xd76f4, odd, 0xd7708, stop=0x4855c, a7=SP + 1)
    #   50e34 (enters 50e42) -> 50e42 BSR 51608 at an odd A7
    err('50e34-then-50e42', 0x50e34, odd, 0x50e42, stop=0x51608, a7=SP + 1)
    #   e625e (D0 bit 0) -> e6266 BSR e6284 at an odd A7
    err('e625e-then-e6266', 0xe625e, odd, 0xe6266, stop=0xe6284, d0=1, a7=SP + 1)


def main():
    rng = random.Random(0xF64B)
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
