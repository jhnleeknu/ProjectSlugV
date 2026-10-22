"""Generates the native-oracle tables of engine/tests/animation_machine_player_c6_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the BYTE table b58 (b2a / b40: b58 + 4 x D1.B + BYTE 10fdb6 + D0.W), the LONG
table 1d468 (1d54c: 1d468 + sext(4 x D1.W)), the BYTE table 1d8ce (1d91a: 1d8ce + sext(D1.W)), the BYTE table 4e4d2 (4e5b0: 4e4d2 + D0.W & ff) and the
WORD tables 1b1b0 / 1b1ca that C2 1cb08 reads for the producer chains of 1dc62 / 1ebba.  A native run that reads any other fixed-ROM or banked byte is
dropped (a table index beyond the declared bytes), as is a run that lands inside the unit on a PC that is not a block start, that writes a device
port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 84(A6) := a routed slot-84 value, WORD 76 / 78 mostly 0 / 1, BYTE 9e 0..3, BYTE 9f 0..4), the player nodes 100cb8 / 100da8, the BYTE slots 10fdb6 /
10fdb7 0..3, the bit BYTEs 10f006 / 10f007, the LONG table 10f02e (10 LONGs, stride 8) and the LONGs 10de14 / 10de1c of e6496, A0 = 10e400 / 10e800 /
10e600 / a player node (10de14 / 10de1c for e6496, 1d468 for 1d54c, 10fdb6 for b2a / b3c / b40), A1 = 10e400 (b58 for b2a / b40, a 10f02e entry for
e64a2 ..), A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 (D0.W 0 / 1 and D1.B 0..3 for b0c, D7.W a type of
1d398, D1.W mostly below 14 for 1d510 .. 1d54c) and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc6.py hint_worlds, converted to absolute
addresses; 'mirror' puts the node at 1fe000, 'stack' writes at A7).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, the RTS sentinel) or a consumer / the Z reader 4ee30.
  single 2  a consumer entered through its real producer: kept when both C values occur; the Z chain 4ee26 -> 4a974 -> 4ee30 runs as plain fixtures.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the Z reader 4ee30 entered directly: the native SR Z is the Z of the TST.B (A0) it recomputes (A0 one of the four 4a974 BYTEs).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 1d546 1d54c Clear, 1d574 4838c Set, 1d514 the borrow of CMPI.W #14,D1 (data); 1d51c / 1d580 keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c6_test_table.py  (rewrites the generated section in place)
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
import pc6 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c6_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREAD = 0x4ee30
CLEAR_SET, SET_SET, PASS_SET, DATA_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET), set(B.DATA_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, REC2, LIST, RTAB, LTAB = 0x10ea00, 0x10eb00, 0x10ec00, 0x10e600, 0x10e800, 0x10e700
PLAYERS = (0x100cb8, 0x100da8)
A4974 = tuple(B.A4974)
TABLE_B58 = (0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0)
TABLE_1D468 = tuple(0 if k % 4 == 0 else 0x30000 + 0x1234 * k for k in range(0x14))
TABLE_1D8CE = tuple(1 if (k * 3) % 4 == 1 else 0 for k in range(0x14))
TABLE_4E4D2 = (3, 1, 2, 0, 7, 5, 6, 4)


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def table_1b1b0():
    """32 WORDs at 1b1b0: C2 1cb08 reads WORD (A0 + 2 x BYTE 9f) (A0 = 1b1b0 for 1dc42, 1b1ca = WORD 13 for 1ebb2); not 0 -> C5 1cb1a reads WORD
    (A0 + W) and tests LONG 22(A6) + 4 x that WORD."""
    w = [0] * 32
    w[0:5] = [0x10, 0, 0x12, 0, 0x14]            # 1b1b0 + 2 x 9f (9f 0..4)
    w[8:11] = [1, 2, 3]                          # 1b1b0 + 10 / 12 / 14
    w[13:18] = [0xc, 0xe, 0, 0x10, 0]            # 1b1ca + 2 x 9f
    w[19:22] = [4, 5, 6]                         # 1b1ca + c / e / 10
    return words(w)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0xb58, bytes(TABLE_B58)),                                           # b2a / b40: the BYTE table b58 (index 0..f)
            (0x1b1b0, table_1b1b0()),                                            # C2 1cb08 / C5 1cb1a from 1dc42 / 1ebb2
            (0x1d468, longs(TABLE_1D468)),                                       # 1d54c: the LONG table 1d468 + 4 x D1.W (D1.W 0..13)
            (0x1d8ce, bytes(TABLE_1D8CE)),                                       # 1d91a: the BYTE table 1d8ce + D1.W (D1.W 0..13)
            (0x4e4d2, bytes(TABLE_4E4D2))]                                       # 4e5b0: the BYTE table 4e4d2 + (D0.W & ff) (0..7)


SYN = synthetic()


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def load_program():
    program = bytearray(ob.load_rom())
    assert hashlib.sha256(program).hexdigest() == '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    for a, b in SYN:
        assert not any(lo < a + len(b) and a < hi for lo, hi in RANGES), hex(a)     # never over code of the unit
        assert program[a:a + len(b)] != b, hex(a)                                   # not the original bytes
        program[a:a + len(b)] = b
    for i, (a, b) in enumerate(SYN):
        for c, d in SYN[i + 1:]:
            assert a + len(b) <= c or c + len(d) <= a, (hex(a), hex(c))
    return bytes(program)


PROGRAM = load_program()
FIXED = (ctypes.c_ubyte * 0x100000).from_buffer_copy(PROGRAM[:0x100000])


def syn_ok(address, size):
    return any(a <= address and address + size <= a + len(b) for a, b in SYN)


# consumer -> (C clear successor, C set successor)
SUCC = {0x1d644: (0x1d648, 0x1d662), 0x1d6a2: (0x1d6a6, 0x1d6c0), 0x1d934: (0x1d93c, 0x1d938), 0x1dc36: (0x1dc3c, 0x1dc3a), 0x1dc62: (0x1dcd0, 0x1dc66),
        0x1ebba: (0x1ed78, 0x1ebbe), 0x1ec66: (0x1ec70, 0x1ec6a), 0x4ed8c: (0x4edd4, 0x4ed90)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both C values occur
CHAIN_CANDIDATES = ((0x1d63a, 0x1d644), (0x1d698, 0x1d6a2), (0x1d92e, 0x1d934), (0x1dc30, 0x1dc36), (0x1dc42, 0x1dc62), (0x1ebb2, 0x1ebba),
                    (0x1ec60, 0x1ec66), (0x4ed70, 0x4ed8c))


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (the first PC after the consumer that is one of its two successors)."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    nxt = next(p for p in tr[i + 1:] if p in SUCC[cons])
    return 1 if nxt == SUCC[cons][0] else 2


class Ram(object):
    def __init__(self):
        self.b = bytearray(65536)
        self.puts = []

    def put(self, a, n, v):
        assert 0x100000 <= a and a + n <= 0x200000, hex(a)     # work RAM and its mirror
        data = (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'big')
        for i, x in enumerate(data):
            self.b[(a + i) & 0xffff] = x
        self.puts.append((a, data))

    def byte(self, a):
        return self.b[a & 0xffff]

    def word(self, a):
        return (self.b[a & 0xffff] << 8) | self.b[(a + 1) & 0xffff]

    def long(self, a):
        return (self.word(a) << 16) | self.word(a + 2)


def base_ram():
    r = Ram()
    r.put(SP, 4, STOP)
    r.base = 1
    return r


def native(ram, regs, pc, carry, stopfn, z=False):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0) | (4 if z else 0))
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
        if len(trace) > 20000:
            out['bad'] = True                       # a long loop: not a table row
            uc.emu_stop()
            return
        if trace and (p & 1 or (inr(p) and p not in STARTS_SET and p != trace[-1] + B.decode(trace[-1]).size)):
            out['bad'] = True                       # an odd PC or a landing inside a block of the unit: the C++ rejects it (error rows)
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
        c.emu_start(pc, 0xffffff, count=400000)
    except unicorn.UcError:
        return None
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.bank != 0x200000:
        return None
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or m.ports:
        return None                                 # C6 writes no device port
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


def data_carry(p, regs_out):
    """The C of the data producer 1d514: CMPI.W #14,D1 (D1 unchanged): the borrow, unsigned D1.W < 14."""
    assert p == 0x1d514, hex(p)
    return 2 if (regs_out['d1'] & 0xffff) < 0x14 else 1


def carry_after(p, c, data=0):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set); data = the C of the data producer (1 / 2)."""
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in CLEAR_SET:
        return 1
    if p in SET_SET:
        return 2
    if p in DATA_SET:
        assert data in (1, 2)
        return data
    return 0


def model(executed, carry, data):
    """C after a path; data = the C of its last data producer when only pass blocks follow it (else 0: a later block resets or sets the C)."""
    c = carry
    for p in executed:
        c = (data if data else 0) if p in DATA_SET else carry_after(p, c)
    return c


def path_data(ex, out_regs):
    """The C of the last data producer of a path when only pass blocks follow it (D1 is unchanged by them)."""
    idx = [i for i, p in enumerate(ex) if p in DATA_SET]
    if not idx or any(p not in PASS_SET for p in ex[idx[-1] + 1:]):
        return 0
    return data_carry(ex[idx[-1]], out_regs)


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
BOUNDED = (0x9e, 0x9f, 0x76, 0x78)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'scc', 'smi', 'abcd'):
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


E6496 = (0xe6496, 0xe64d2, 0xe64de, 0xe64e6, 0xe64f0, 0xe64f4, 0xe64fe, 0xe6506)
E64A2 = (0xe64a2, 0xe64aa, 0xe64ae, 0xe64b8, 0xe64c0)


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, RTAB, LIST) + PLAYERS),
                a1=CHILD, a2=rng.choice((PARENT, CHILD)), a3=rng.choice((REC, REC2)), a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 8, 0x20, 0x22, 0x40, 0x80, 0xc, 0x50, 0x10, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000, 4, 7))
    if rng.random() < 0.7:
        regs['d1'] = (regs['d1'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 4, 9, 0xa, 0x11, 0x13, 0x14, 0xff, 0x8000))
    if rng.random() < 0.7:
        regs['d7'] = (regs['d7'] & 0xffff0000) | rng.choice((3, 5, 6, 7, 8, 9, 0xa, 0xb, 0xe, 0, 4, 0x8005))
    if s in (0xb0c, 0xb2a, 0xb3c, 0xb40, 0xb50):
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1))
        regs['d1'] = (regs['d1'] & 0xffffff00) | rng.randrange(4)
    if s in (0xb2a, 0xb3c, 0xb40):
        regs['a0'] = 0x10fdb6
        regs['a1'] = 0xb58
    if s in (0x1d54c, 0x1d532):
        regs['a0'] = 0x1d468
    if s == 0x4e5b0 and rng.random() < 0.8:
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(8)
    if s in E6496:
        regs['a0'] = rng.choice((0x10de14, 0x10de1c, CHILD))
    if s in E64A2:
        regs['a1'] = 0x10f02e + 8 * rng.randrange(10)
        regs['d1'] = (regs['d1'] & 0xffff0000) | rng.randrange(1, 11)
    if s == 0x481c2:
        regs['a0'] = A5 + rng.choice((0x5694, 0x569c))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or disp in BOUNDED):
            continue                                    # (A6) callback LONG, the node links, the pointer fields and the bounded indices are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links and pointers, the slot LONG 84, the bounded indices; the player nodes; the BYTE slots, bit BYTEs and LONG tables of b0c / e6496
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0x9e, 1, rng.randrange(4))
    r.put(NODE + 0x9f, 1, rng.randrange(5))
    r.put(NODE + 0x76, 2, rng.choice((0, 0, 1, 1, 0x4000, 0xffff)))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 0x100)))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x8c, 4, rng.choice((REC, REC2)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for k in (0, 1):
        r.put(0x10fdb6 + k, 1, rng.randrange(4))
    r.put(0x10f006, 1, rng.getrandbits(8))
    r.put(0x10f007, 1, rng.getrandbits(8))
    long_pool = (0, 1, 0x100, 0x5000, 0x12345, 0x80000000, 0xffffffff)
    for k in range(10):
        r.put(0x10f02e + 8 * k, 4, rng.choice(long_pool))
    for a in (0x10de14, 0x10de1c, A5 + 0x5e14, A5 + 0x5e1c):
        r.put(a, 4, rng.choice(long_pool))
    for i in range(0, 0x40, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # C5 1cb1a: LONG 22(A6) + sext(4 x WORD)
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('stack', []):
            r.put(SP + off, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
    for k in ('a0', 'a1'):
        if regs[k] < 0x100000 or regs[k] >= 0x110000:
            if not syn_ok(regs[k], 1):
                regs[k] = REC                           # a hint pointer outside work RAM and the declared bytes (the V1 worlds' nodes are absolute)
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts and the RTS sentinel
ROUTED_EXITS = {0x28ae, 0x2986, 0x2a00, 0x2a0a, 0xce02, 0x1aa3a, 0x1cab6, 0x1cb08, 0x1cb38, 0x1cd98, 0x1d182, 0x1d1d0, 0x1dbd8, 0x1ddd0, 0x1ddfc,
                0x1de06, 0x1ed78, 0x1eeea, 0x1f1d8, 0x1f7a4, 0x1fa3c, 0x1fae8, 0x201a2, 0x206d2, 0x43e08, 0x43e34, 0x43ea4, 0x48210, 0x4836e, 0x49214,
                0x49bca, 0x49c20, 0x49c38, 0x49fc6, 0x4a974, 0x4bfc0, 0x4c0ea, 0x4d50e, 0x4e4da, 0x4e564, 0x4e57e, 0x4e6f2, 0x4f22c, 0xe6556}
# (1dc84 / 4e8fc are the return PCs of 1dc7a JSR ce02 / 4e8f8 JSR 4f22c: reached through the callee's RTS, not a stop of a C6 row)
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x1d3e0, 0x4eb6a, 0x1f2a4, 0x1fa68, 0xea626}
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p == ZREAD


def hints(s):
    """The V1 spec hint worlds (pc6.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def zread_hints():
    """The Z reader 4ee30: A0 one of the four 4a974 BYTEs with a BYTE value (zero or not)."""
    hs = []
    for i, v in enumerate((0, 1, 0x80, 0xff, 0, 2, 0, 0x40)):
        a0 = A4974[i % 4]
        hs.append(dict(regs=dict(a0=a0), writes=[(a0 & 0xffff, 1, v)]))
    return hs


def gen_singles(rng):
    for s in STARTS:
        if s in CONS_SET:
            continue
        fl = fields(s)
        kept = {}
        hs = zread_hints() if s == ZREAD else hints(s)
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs = world(rng, fl, s, hint)
            z = False
            if s == ZREAD:
                if hint is None:
                    continue
                z = r.byte(regs['a0']) == 0
            o = native(r.b, regs, s, 0, single_stop, z)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue                                 # a stop at the entry is a zero-step run
            if ((nxt in CONS_SET or nxt == ZREAD) and s not in CLEAR_SET | PASS_SET | SET_SET | DATA_SET) or (inr(nxt) and nxt not in STARTS_SET) or \
                    not allowed(nxt):
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
            data = data_carry(s, o['regs']) if s in DATA_SET else 0
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, data), 5 if s == ZREAD else 1, o)


PATH_ENTRIES = tuple(s for s in STARTS if s not in CONS_SET and s != ZREAD)


def gen_paths(rng):
    fl = []
    for b in STARTS:
        fl += fields(b)
    fl = sorted(set(fl))
    for s in PATH_ENTRIES:
        kept = {}
        hs = hints(s)
        for t in range(120):
            carry = rng.choice((0, 1, 2))
            r, regs = world(rng, fl, s, hs[t % len(hs)] if hs and t % 3 == 1 else None)
            o = native(r.b, regs, s, carry, path_stop)
            if o is None:
                continue
            ex = [p for p in o['trace'] if p in STARTS_SET]
            if any(p in CONS_SET or p == ZREAD for p in ex) or not allowed(o['stop']) or o['stop'] == s:
                continue
            key = (o['stop'], tuple(ex[:60]))
            if key in kept:
                continue
            kept[key] = (r, regs, o, carry, ex, path_data(ex, o['regs']))
            if len(kept) >= 3:
                break
        if not kept:
            print('no path row', hex(s))
            continue
        for i, (k, (r, regs, o, carry, ex, data)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, data), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=CHILD, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    if entry in (0x1d63a, 0x1d698):                              # 49c38: TST.L 5734(A5) + 4 x (D0.W & 1), D0.W = WORD 78
        w = rng.choice((0, 1))
        r.put(NODE + 0x78, 2, w)
        r.put(A5 + 0x5734 + 4 * w, 4, rng.choice((0, CHILD)))
    if entry == 0x1d92e:                                         # 1d510 with the stacked WORD D1: >= 14 -> Clear (1d51c), else the routed 481b2 path
        regs['a7'] = SP - 2                                      # (2986 / 28ae of 1d558 get a free node: the 2986 failure path is the checked
        r.put(SP - 2, 2, rng.choice((0x14, 0x15, 0xffff, 0, 1, 5)))   # caller-X error of buffer_cue decision 1, contract decision 7)
        r.put(0x104ca0, 2, 0x100)
        r.put(0x104c9c, 4, 0x10e500)
        r.put(0x10e508, 4, 0)
        r.put(NODE + 8, 4, PARENT)
    if entry == 0x1dc30:                                         # 4836e: BTST #2,5683(A5): set -> Set
        r.put(A5 + 0x5683, 1, rng.choice((0, 4, 0xfb, 0xff)))
    if entry in (0x1dc42, 0x1ebb2):                              # C2 1cb08 on the synthetic WORD tables 1b1b0 / 1b1ca with BYTE 9f 0..4
        r.put(NODE + 0x9f, 1, rng.randrange(5))
    if entry == 0x1ec60:                                         # 49fc6: LONG 26(A6) = 0 -> Set (else the interpreter reads ROM: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry == 0x4ed70:                                         # 28ae: D0.W 0 below the WORD 104ca0 -> a node from the free list LONG 104c9c,
        r.put(0x104ca0, 2, rng.choice((0x100, 0x15, 0x40, 0, 0x1e)))   # Set; else Clear
        r.put(0x104c9c, 4, 0x10e500)
        r.put(0x10e508, 4, 0)
        r.put(NODE + 8, 4, PARENT)
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
        succ = B.static_next(cons)
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            o = native(r.b, regs, entry, 0, lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS)
            if o is None or cons not in o['trace']:
                continue
            c = cons_value(cons, o)
            if seen.get(c, 0) >= 3:
                continue
            seen[c] = seen.get(c, 0) + 1
            rows.append((k, r, regs, o, c))
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        print('chain %x -> %x: %s' % (entry, cons, dict(seen)))
        if set(seen) != {1, 2}:
            continue                                             # one C value never occurred (or the producer reads undeclared ROM): declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)
    # the Z chain: 4ee26 (MOVE.W 76(A6),D0; JSR 4a974) -> 4a974 (BYTE 10fd82 = 0: A0 = 100004 + (D0.W & 1) when BYTE 100003 is not 0, else 100004;
    # TST.B (A0)) -> 4ee30 (BEQ) -> 4ee5c / 4ee34
    n = {}
    for k in range(600):
        r, regs = world(rng, [], 0x4ee26)
        r.put(0x10fd82, 1, 0)
        r.put(NODE + 0x76, 2, k % 2)
        r.put(0x100003, 1, rng.choice((0, 1)))
        r.put(0x100004, 1, rng.choice((0, 1, 0x80)))
        r.put(0x100005, 1, rng.choice((0, 1, 0x80)))
        o = native(r.b, regs, 0x4ee26, 0, lambda q, tr: q in (0x4ee5c, 0x4ee34) or q in B.EXIT_STOPS)
        if o is None or ZREAD not in o['trace']:
            continue
        if n.get(o['stop'], 0) >= 3:
            continue
        n[o['stop']] = n.get(o['stop'], 0) + 1
        row('zchain-4ee26-%d' % k, r, regs, 0x4ee26, o['stop'], 0, 0, 2, o)
        if len(n) == 2 and min(n.values()) >= 3:
            break
    print('Z chain', dict((hex(a), b) for a, b in n.items()))
    assert len(n) == 2, 'Z chain: both outcomes'


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=CHILD, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    flag = 'unsupported animation player c6 flag source'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c6 caller requires known carry', cp, stop=SUCC[cp][0])
    # the Z source of 4ee30 (contract decision 3)
    for v in (0x10fdb2, 0x100003, 0x100006, 0x11fdb0, 0x3c0000, 0x10fdaf, 0x1100004):
        err('z-a0-%x' % v, ZREAD, flag, ZREAD, a0=v)
    # the ROM tables outside the declared synthetic bytes
    err('table-b58-10', 0xb2a, rom, 0xb2a, a0=0x10fdb6, a1=0xb58, d1=4)
    err('table-1d468-14', 0x1d54c, rom, 0x1d54c, a0=0x1d468, d1=0x14)
    err('table-1d468-neg', 0x1d54c, rom, 0x1d54c, a0=0x1d468, d1=0x2000)
    err('table-1d8ce-14', 0x1d91a, rom, 0x1d91a, d1=0x14)
    err('table-4e4d2-8', 0x4e5b0, rom, 0x4e5b0, d0=8)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1d63a', 0x1d63a, odd, 0x1d63a, stop=0x49c38, a6=NODE + 1)
    err('odd-node-1e83e', 0x1e83e, wodd, 0x1e83e, stop=0x43e08, a6=NODE + 1)
    err('odd-node-1dac2', 0x1dac2, wodd, 0x1dac2, stop=0x1dace, a6=NODE + 1)
    err('odd-node-4ee04', 0x4ee04, odd, 0x4ee04, stop=0x4ee16, a6=NODE + 1)
    err('odd-stack-1d51e', 0x1d51e, odd, 0x1d51e, stop=0x481b2, a7=SP + 1)
    err('odd-stack-1d532', 0x1d532, odd, 0x1d532, stop=0x1d54c, a7=SP + 1)
    err('odd-stack-1d92e', 0x1d92e, odd, 0x1d92e, stop=0x1d510, a7=SP + 1)
    err('odd-stack-1d91a', 0x1d91a, odd, 0x1d91a, stop=0x1d92e, a7=SP + 1)
    err('odd-a0-e6496', 0xe6496, odd, 0xe6496, stop=0xe64a2, a0=0x10de15)
    err('odd-a1-e64a2', 0xe64a2, odd, 0xe64a2, stop=0xe64ae, a1=0x10f02f)
    err('odd-a0-4ed90', 0x4ed90, wodd, 0x4ed90, stop=0x4ed9a, a0=NODE + 1)
    err('odd-a0-481c2', 0x481c2, odd, 0x481c2, stop=0x4d50e, a0=NODE + 1)
    err('odd-a0-4edaa', 0x4edaa, wodd, 0x4edaa, stop=0x4edc0, a0=NODE + 1)
    err('odd-a0-1d574', 0x1d574, wodd, 0x1d574, a0=NODE + 1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1d398-then-1d3e0', 0x1d398, unrouted, 0x1d3e0, d7=0)
    err('4eb58-then-4eb6a', 0x4eb58, unrouted, 0x4eb6a, puts=((0x10fd8a, 1, 1),))
    # 1f2a4 is a player C7 start since C7 (previous row: 'unsupported animation machine PC' at 1f2a4); the BSR.W 1cab6 of 1f2a4 at an odd A7 keeps
    # the failing PC 1f2a4
    err('1ec2c-then-1f2a4', 0x1ec2c, odd, 0x1f2a4, d0=2, a7=SP + 1)
    # 1fa68 / ea626 are player C8 starts since C8 (previous rows: 'unsupported animation machine PC' at 1fa68 / ea626); the BSR.W 1cb08 of 1fa68 at an
    # odd A7 and the MOVE.B #ff,5e50(A5) of ea626 with A5 = 0 (fixed ROM) keep the failing PCs 1fa68 / ea626
    err('1ec1e-then-1fa68', 0x1ec1e, odd, 0x1fa68, d0=0xc, a7=SP + 1)
    err('1dad8-then-ea626', 0x1dad8, 'unsupported animation machine write device', 0xea626, a5=0)
    err('b0c-then-b56', 0xb0c, odd, 0xb56, a7=SP + 1)
    err('1e60a-then-1e630', 0x1e60a, odd, 0x1e630, a7=SP + 1, d0=1)
    err('1d514-then-1d51c', 0x1d514, odd, 0x1d51c, a7=SP + 1, d1=0x14)
    err('1d54c-then-1d580', 0x1d54c, odd, 0x1d580, a7=SP + 1, a0=0x1d468, d1=0)
    err('e6496-then-e64cc', 0xe6496, odd, 0xe64cc, a7=SP + 1, a0=0x10de14)
    err('4ee5c-then-4ee78', 0x4ee5c, odd, 0x4ee78, a7=SP + 1)
    err('1e65c-then-1e674', 0x1e65c, odd, 0x1e674, a7=SP + 1)


def main():
    rng = random.Random(0xC6C6)
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
    tables.append('const std::uint32_t RANGES[][2]={%s};' % ','.join('{0x%x,0x%x}' % r for r in RANGES))
    tables.append('const std::uint32_t EXITS[]={%s};' % ','.join(['0x%x' % e for e in EXITS] + ['STOP']))
    tables.append('const unsigned int EVEN_COUNT=%d;' % sum((hi - lo) // 2 for lo, hi in RANGES))
    tables.append('struct Synthetic {std::uint32_t address;const char* bytes;};')
    tables.append('const Synthetic SYNTHETIC[]={%s};' % ','.join('{0x%x,"%s"}' % (a, b.hex()) for a, b in SYN))
    tables.append('const Fixture FIXTURES[]={')
    tables += out
    tables.append('};')
    tables.append(END)
    text = TEST.read_text()
    i = text.index(BEGIN)
    j = text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(tables) + text[j:])
    singles = [d for d in ROWS if d['single'] in (1, 5)]
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
    stops = set(d['stop'] for d in ROWS if d['error'] is None)
    print('exits never a stop', [hex(e) for e in EXITS if e not in stops])


if __name__ == '__main__':
    main()
