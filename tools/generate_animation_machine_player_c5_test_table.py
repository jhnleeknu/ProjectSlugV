"""Generates the native-oracle tables of engine/tests/animation_machine_player_c5_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the 10-byte records 1c298..1c356 (1c378 / 1c3e6: 1c298 + sext(MULU product
WORD)) and one record at 14498 (the product WORD 8200 of D1.W = d00: a negative index), the LONG table 1c52c (1c51c / the Z reader 1c3e2), the BYTE
table 1cbb2, the LONG table 1cc04 and the BYTE table 1cc10 (one block 1cbb2..1cc1a; 1cc1a / 1cc38 / 1cc6a / 1cc7c), the WORD pairs 1cce8 (1ccd0), the
WORD tables 20710 (206ec) and 1b128 (212d4 / 213e4) with the WORDs 18710 / 13128 that their negative indices (WORD 76 = 4000) reach, the 16-byte records
4cf64 (4d640), the record WORDs 1bc4a..1bc54 / 1bc82 (1cb44 from 21310 / 2140e / 20e18) and the (handler LONG, key WORD) list 21b26 (C3 215e6 from
21f70).  A native run that reads any other fixed-ROM or banked byte is dropped (a table index beyond the declared bytes), as is a run that lands inside
the unit on a PC that is not a block start, that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 84(A6) := a routed slot-84 value, LONG b2(A6) := 0 / the child 10e400, the bounded BYTE indices a0 0..8, a9 0..5, 9e 0..3, 9f 0..8, 7c 0..5 and
5e mostly 0..1a, WORD 76 / 78 mostly 0 / 1), the player nodes 100cb8 / 100da8 that 1c356 reads (A5 - 7348 / - 7258: callback LONG 270e (289e Clear) or
not, LONG 8c := the record 10ea00 / 10ec00, BYTE 9e 0..3, WORD 78), A0 = 10e400 / 10e800 / 10e600 / the player nodes, A1 = a handler of the list 21b26
for 21f7c (contract decision 2), A3 = a ROM record of 1c298 or 10ea00, A4 = 10ea00, A5 = 108000, seeded BYTE / WORD / LONG field edits (sign
boundaries included), seeded D0-D7 (D1.B mostly a record type below 13, D0.B 0..1a for 20946 / 209ce) and the hint worlds of the V1 spec
(tools/unit_fixture_specs/pc5.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'stack' writes at A7).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a computed-jump target).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, computed-jump targets, the RTS sentinel) or a consumer / the Z
            reader 1c3e2.
  single 2  a consumer entered through its real producer: kept when both C values occur; the Z chain 1c3dc -> 1c51c -> 1c3e2 runs as plain fixtures.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the Z reader 1c3e2 entered directly: the native SR Z is the Z of the BTST.L D1,D7 it recomputes (D7 = the synthetic LONG 1c52c + 4 x BYTE
            9e(A0)).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 1cb1a (TST.L) 1c4aa 4d6a8 Clear, 1cb32 1c494 4d69c cde10 Set; 1cb30 keeps the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c5_test_table.py  (rewrites the generated section in place)
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
import pc5 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c5_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREAD = 0x1c3e2
CLEAR_SET, SET_SET, PASS_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, REC2, LIST, RTAB, LTAB = 0x10ea00, 0x10eb00, 0x10ec00, 0x10e600, 0x10e800, 0x10e700
PLAYERS = (0x100cb8, 0x100da8)
LIST_21B26 = tuple(B.LIST_21B26)
TABLE_1C52C = (0x00012345, 0x80000001, 0xffffffff, 0x0000a5a5)


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def entries(pairs):
    """(handler LONG, key WORD) pairs and the LONG 0 terminator."""
    return b''.join(struct.pack('>IH', h, k) for h, k in pairs) + struct.pack('>I', 0)


def record(k):
    """The synthetic 10-byte record k of 1c298: type BYTE (A3) (a bit number of 1c51c), BYTE 1 (D2 of 4d628 / the compare of 1c3e6), BYTE 2, WORD 4
    (D1 of 4d628 / c(A4)), WORD 6 (the ADD.W of 1c41e), WORD 8 (the child WORD 76)."""
    return bytes((k, (3 * k + 1) & 0xff, (5 * k + 2) & 0xff, 0)) + words(((0x37 * k) & 0xffff, (0x3e0 + k) if k % 3 == 0 else (k * 0x101) & 0xffff,
                                                                         0x8000 | k))


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    tab = bytearray(0x1cc1a - 0x1cbb2)
    for i in range(0x1cc04 - 0x1cbb2):
        tab[i] = (i * 7) % 5                                                     # 1cc1a: the BYTE table 1cbb2 + 9 x BYTE a0 + BYTE 9f (0..4)
    tab[0x1cc04 - 0x1cbb2:0x1cc10 - 0x1cbb2] = longs((0x10e7c0, 0x10e700, 0x10e740))   # 1cc38: LONG 1cc04 + 4 x BYTE (0 .. 2; 3 is 1cc10)
    tab[0x1cc10 - 0x1cbb2:] = bytes((0, 0, 0, 1, 1, 0, 1, 0, 0, 1))                  # 1cc6a / 1cc7c: BYTE 1cc10 + BYTE 9f / a0; also the LONG 3 of 1cc04
    return [(0x13128, words((0x5a5a,))),                                         # 212d4: 1b128 + sext(2 x WORD 76) for WORD 76 = 4000 (negative index)
            (0x14498, record(0x0c)),                                             # 1c378: 1c298 + sext(a x d00 = 8200) (negative index)
            (0x18710, words((0x6a6a,))),                                         # 206ec: 20710 + sext(2 x WORD 76) for WORD 76 = 4000 (negative index)
            (0x1b128, words((0x1234, 0x8001, 0xfffe, 0x0300))),                  # 212d4 / 213e4: WORD 1b128 + 2 x WORD 76
            (0x1bc4a, words((1, 2, 0, 3, 0x4000))),                              # 1cb44 from 2140a / 2130c / 213fc / 212fc: WORD (A0)
            (0x1bc82, words((2,))),                                              # 1cb44 from 20e18
            (0x1c298, b''.join(record(k) for k in range(0x13))),                 # 1c378 / 1c3e6: the 10-byte records (1c298 .. 1c356)
            (0x1c52c, longs(TABLE_1C52C)),                                       # 1c51c / 1c3e2: LONG 1c52c + 4 x BYTE 9e(A0) (9e 0..3)
            (0x1cbb2, bytes(tab)),                                               # 1cc1a .. 1cc7c: the tables 1cbb2 / 1cc04 / 1cc10 (one block)
            (0x1cce8, words((1, 2, 3, 0x8000, 0xfff0, 0x10, 0x7fff, 0, 5, 6, 0x1234, 0xfedc))),   # 1ccd0: the WORD pairs 1cce8 + 4 x BYTE 7c (7c 0..5)
            (0x20710, words((0x1111, 0x2222, 0x3333, 0x4444, 0x8000, 0xffff, 0x7fff, 0))),       # 206ec: WORD 20710 + 2 x WORD 76
            (0x21b26, entries(((0x21e3a, 1), (0x21602, 3), (0x21e48, 0x104)))),  # C3 215e6 from 21f70 (the list 21b26)
            (0x4cf64, longs((0, 0x00000001, 0, 0, 0, 0x80000000, 0, 0, 0, 0x0000ffff, 0, 0, 0, 0xaaaaaaaa, 0, 0)))]   # 4d640: LONG 4cf64 + 16 x BYTE 27 + 4


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


def syn_long(address):
    for a, b in SYN:
        if a <= address and address + 4 <= a + len(b):
            return struct.unpack('>I', b[address - a:address - a + 4])[0]
    return None


# consumer -> (C clear successor, C set successor)
SUCC = {0x1c374: (0x1c4aa, 0x1c378), 0x1c3ca: (0x1c3dc, 0x1c3d2), 0x20288: (0x2028c, 0x20290), 0x20e56: (0x20e60, 0x20e5a), 0x214b2: (0x214bc, 0x214b6),
        0x21f78: (0x21f7e, 0x21f7c), 0xcddfe: (0xcde14, 0xcde02)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both C values occur
CHAIN_CANDIDATES = ((0x1c36e, 0x1c374), (0x1c3c0, 0x1c3ca), (0x2027e, 0x20288), (0x21f70, 0x21f78), (0xcddee, 0xcddfe), (0x20e50, 0x20e56),
                    (0x214ac, 0x214b2))


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (the first PC after the consumer that is one of its two successors; the consumer
    block 1c3ca has three instructions, so the next traced PC is not the successor)."""
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


# the computed jumps of the unit and their allowed landings (contract decision 2)
JUMP_ALLOWED = {0x20792: set(B.TABLE_20796), 0x2094e: set(B.TABLE_20952), 0x209d6: set(B.TABLE_209DA), 0x21f7c: set(LIST_21B26)}


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
        if trace and trace[-1] in JUMP_ALLOWED and p not in JUMP_ALLOWED[trace[-1]]:
            out['bad'] = True                       # a computed jump outside the ROM-bounded targets: the C++ checked jump-target error (error rows)
            uc.emu_stop()
            return
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
        return None                                 # C5 writes no device port
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


def carry_after(p, c):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set)."""
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
BOUNDED = (0xa0, 0xa9, 0x9e, 0x9f, 0x7c, 0x5e, 0x76, 0x78)


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


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, RTAB, LIST) + PLAYERS),
                a1=rng.choice(LIST_21B26) if s == 0x21f7c else CHILD, a2=rng.choice((PARENT, CHILD)),
                a3=rng.choice((REC, REC2, 0x1c298 + 10 * rng.randrange(0x13))), a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x18, 0x50, 0x400, 0xffff, 0x12345678, 0x10000, 0x100, 0xff))
    if rng.random() < 0.7:
        regs['d1'] = (regs['d1'] & 0xffffff00) | rng.choice((0, 0, 1, 2, 5, 0xc, 0x12, 0x13, 0x80))
    if s in (0x20946, 0x209ce):
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x1b)
    for k in ('d2', 'd5', 'd6', 'd7'):
        if rng.random() < 0.6:
            regs[k] = (regs[k] & 0xffff0000) | rng.choice((0, 1, 2, 4, 6, 0xc, 0x1f, 0x20, 0x3e7, 0x8000, 0xfffe, 0xffff))
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
    # the node links and pointers, the slot LONG 84, the bounded indices; the player nodes of 1c356; the records; the RAM tables 10e700 / 10e800
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0xb2, 4, rng.choice((0, CHILD)))
    r.put(NODE + 0xa0, 1, rng.randrange(9))
    r.put(NODE + 0xa9, 1, rng.randrange(6))
    r.put(NODE + 0x9e, 1, rng.randrange(4) if rng.random() < 0.9 else rng.choice((4, 0x80, 0xff)))
    r.put(NODE + 0x9f, 1, rng.randrange(9))
    r.put(NODE + 0x7c, 1, rng.randrange(6))
    r.put(NODE + 0x5e, 1, rng.choice((0, 1, 2, 2, 7, 0x11, 0x1a, 0x1b, 0x7f, 0x80)))
    r.put(NODE + 0x76, 2, rng.choice((0, 0, 1, 1, 2, 3, 0x4000)))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 0x100)))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x8c, 4, rng.choice((REC, REC2)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for rec in (REC, REC2):
        r.put(rec + 4, 1, rng.randrange(0x13))
        r.put(rec + 0xc, 2, rng.choice((0, 0x3e6, 0x3e7, 0x3e8, 5)))
    for off in (0x5cba, 0x5ce6):
        r.put(A5 + off, 2, rng.choice((0, 1, 0x100)))
        r.put(A5 + off + 0x27, 1, rng.randrange(4))
    for i in range(0, 0x40, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # 1cb1a / 1cb44: LONG 22(A6) + sext(4 x WORD)
    for i in range(0, 0x20, 2):
        if rng.random() < 0.5:
            r.put(RTAB + i, 2, rng.choice((0, 1, 2, 3, 4, 6, 8, 0x4000, 0xfffe)))      # 1cb1a / 1cb44: WORD (A0) with A0 = 10e800
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('a4off', []):
            a = (regs['a4'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
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
    if s == 0x21f7c and regs['a1'] not in LIST_21B26:
        regs['a1'] = LIST_21B26[0]
    for k in ('a0', 'a4'):
        if regs[k] < 0x100000 or regs[k] >= 0x110000:
            regs[k] = REC                               # a hint pointer outside work RAM (the V1 worlds' nodes are absolute): kept in RAM
    if regs['a3'] >= 0x110000 or (regs['a3'] < 0x100000 and not syn_ok(regs['a3'], 10)):
        regs['a3'] = REC
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the computed-jump targets and the RTS sentinel
ROUTED_EXITS = {0x289e, 0x28ae, 0x2986, 0x3af8, 0x8ebe, 0x8ff4, 0xce02, 0x1aa3a, 0x1c1f4, 0x491b6, 0x49214, 0x4970a, 0x49c38, 0x49f96, 0x49fc6, 0x4be82,
                0x4bfc0, 0x4d7a6, 0x1c1e2, 0x1cabe, 0x1cb08, 0x1cd98, 0x1d15a, 0x20264, 0x20290, 0x202a0, 0x20626, 0x2156a, 0x21f58, 0x21ffc, 0x21602}
# (C3 202b6 / 21c1a are the return PCs of 202ac JSR 1c356 / 21c12 BSR 1cb08: reached through the callee's RTS, not a stop of a C5 row)
JUMP_TARGETS = set(t for t in B.TABLE_20796 + B.TABLE_20952 + B.TABLE_209DA + (0x21e48, 0x21e3a) if t not in STARTS_SET)
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x21564, 0x208fa, 0x2210c}
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_TARGETS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p == ZREAD


def hints(s):
    """The V1 spec hint worlds (pc5.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def zread_hints():
    """The Z reader 1c3e2: A0 = a player node with BYTE 9e 0..3, D7 = the synthetic LONG 1c52c + 4 x BYTE 9e, D1 a bit number (modulo 32)."""
    hs = []
    for i, d1 in enumerate((0, 1, 5, 9, 0x10, 0x1f, 0x20, 0x21, 0x12345600, 0x2f)):
        b = i % 4
        hs.append(dict(regs=dict(a0=PLAYERS[i % 2], d1=d1, d7=TABLE_1C52C[b]), writes=[((PLAYERS[i % 2] + 0x9e) & 0xffff, 1, b)]))
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
                b = r.byte(regs['a0'] + 0x9e)
                z = ((TABLE_1C52C[b] >> (regs['d1'] & 31)) & 1) == 0
            o = native(r.b, regs, s, 0, single_stop, z)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue                                 # a stop at the entry is a zero-step run
            if ((nxt in CONS_SET or nxt == ZREAD) and s not in CLEAR_SET | PASS_SET | SET_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 5 if s == ZREAD else 1, o)


def gen_tables():
    """Contract decision 2: one row per entry of the BRA.W tables (20778: BYTE 9e 0..3; 20946 / 209ce: D0.B 0..1a), the entry being the stop (the
    executed entries 20796 / 2095a are blocks of the unit, the others unrouted table entries)."""
    for entry, table, n in ((0x20778, 0x20796, 4), (0x20946, 0x20952, 0x1b), (0x209ce, 0x209da, 0x1b)):
        for k in range(n):
            r = base_ram()
            regs = dict(PLAIN)
            if entry == 0x20778:
                r.put(NODE + 0x9e, 1, k)
            else:
                regs['d0'] = 0x12345600 | k
            o = native(r.b, regs, entry, 0, lambda p, tr: p == table + 4 * k)
            assert o is not None and o['stop'] == table + 4 * k, (hex(entry), k)
            row('table-%x-%d' % (entry, k), r, regs, entry, o['stop'], 0, 0, 0, o)


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
            kept[key] = (r, regs, o, carry, ex)
            if len(kept) >= 3:
                break
        if not kept:
            print('no path row', hex(s))
            continue
        for i, (k, (r, regs, o, carry, ex)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    if entry == 0x1c36e:                                         # 289e: CMPI.L #270e,(A0): equal -> Clear
        regs['a0'] = PLAYERS[k % 2]
        r.put(regs['a0'], 4, rng.choice((0x270e, 0x1ef0e, 0x270e, 0)))
    if entry == 0x1c3c0:                                         # 4d628: WORD (A5 + 5cba / 5ce6) 0 -> Clear; else the synthetic record 4cf64 + 16 x
        regs['d0'] = rng.choice((0, 1, 0x100))                   # BYTE 27, BTST.L D2
        regs['d2'] = rng.choice((0, 1, 0x1f, 0x20, 5))
        a4 = A5 + (0x5ce6 if regs['d0'] & 0xff else 0x5cba)
        r.put(a4, 2, rng.choice((0, 1, 0x8000)))
        r.put(a4 + 0x27, 1, rng.choice((0, 1, 2, 3)))
        regs['a3'] = 0x1c298 + 10 * rng.randrange(0x13)
    if entry == 0x2027e:                                         # 49c38: TST.L 5734(A5) + 4 x (D0.W & 1)
        w = rng.choice((0, 1))
        r.put(NODE + 0x78, 2, w)
        r.put(A5 + 0x5734 + 4 * w, 4, rng.choice((0, CHILD)))
    if entry == 0x21f70:                                         # C3 215e6 on the synthetic list 21b26
        r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 4)))
    if entry == 0xcddee:                                         # 28ae: D0.W 1e below the WORD 104ca0 -> a node from the free list LONG 104c9c,
        r.put(0x104ca0, 2, rng.choice((0x100, 0x15, 0x40, 0x1f, 0x1e)))   # Set; else Clear
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
    # the Z chain: 1c3dc (MOVE.B (A3),D1; BSR 1c51c) -> 1c51c (BYTE 9e(A0): the synthetic LONG 1c52c; BTST.L D1,D7) -> 1c3e2 (BEQ) -> 1c4aa / 1c3e6
    n = {}
    for k in range(600):
        r, regs = world(rng, [], 0x1c3dc)
        regs['a0'] = PLAYERS[k % 2]
        regs['a3'] = 0x1c298 + 10 * rng.randrange(0x13) if k % 3 else REC
        if k % 3 == 0:
            r.put(REC, 1, rng.randrange(0x40))
        r.put(regs['a0'] + 0x9e, 1, rng.randrange(4))
        o = native(r.b, regs, 0x1c3dc, 0, lambda q, tr: q in (0x1c4aa, 0x1c3e6) or q in B.EXIT_STOPS)
        if o is None or ZREAD not in o['trace']:
            continue
        if n.get(o['stop'], 0) >= 3:
            continue
        n[o['stop']] = n.get(o['stop'], 0) + 1
        row('zchain-1c3dc-%d' % k, r, regs, 0x1c3dc, o['stop'], 0, 0, 2, o)
        if len(n) == 2 and min(n.values()) >= 3:
            break
    print('Z chain', dict((hex(a), b) for a, b in n.items()))
    assert len(n) == 2, 'Z chain: both outcomes'


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c5 jump target'
    flag = 'unsupported animation player c5 flag source'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c5 caller requires known carry', cp, stop=SUCC[cp][0])
    # the computed jumps (contract decision 2)
    for v in (4, 0x40, 0xff):
        err('20778-9e-%x' % v, 0x20778, jump, 0x20778, puts=((NODE + 0x9e, 1, v),))
    for v in (1, 2, 3):
        err('20778-9e-%x-entry' % v, 0x20778, unrouted, 0x20796 + 4 * v, puts=((NODE + 0x9e, 1, v),))
    for v in (0x1b, 0x1c, 0xff, 0x12345640):
        err('20946-d0-%x' % v, 0x20946, jump, 0x20946, d0=v)
        err('209ce-d0-%x' % v, 0x209ce, jump, 0x209ce, d0=v)
    for v in (0, 1, 0x1a, 0x12345603):
        err('20946-d0-%x-entry' % v, 0x20946, unrouted, 0x20952 + 4 * (v & 0xff), d0=v)
        err('209ce-d0-%x-entry' % v, 0x209ce, unrouted, 0x209da + 4 * (v & 0xff), d0=v)
    for v in (0x21622, 0x21b26, 0, 0x1021602, 0x21603, 0x21c66):
        err('21f7c-%x' % v, 0x21f7c, jump, 0x21f7c, a1=v)
    for v in (0x21e48, 0x21e3a):
        err('21f7c-listed-%x' % v, 0x21f7c, unrouted, v, a1=v)
    # the Z source of 1c3e2 (contract decision 3)
    for v in (0x200000 - 0x9e, 0x3c0000, 0x2ffff0):
        err('z-a0-%x' % v, ZREAD, flag, ZREAD, a0=v, d7=TABLE_1C52C[0])
    for v in (TABLE_1C52C[0] ^ 1, 0, TABLE_1C52C[1]):
        err('z-d7-%x' % v, ZREAD, flag, ZREAD, a0=PLAYERS[0], d7=v)
    err('z-table-missing', ZREAD, rom, ZREAD, a0=PLAYERS[0], puts=((PLAYERS[0] + 0x9e, 1, 4),))
    # the ROM tables outside the declared synthetic bytes
    err('table-1c52c-4', 0x1c51c, rom, 0x1c51c, a0=PLAYERS[0], puts=((PLAYERS[0] + 0x9e, 1, 4),))
    err('table-1cc10-a0', 0x1cc7c, rom, 0x1cc7c, a1=0x1cc10, d0=0x100, puts=((NODE + 0xa0, 1, 0),))   # D0.W 0100: 1cd10 (code of the unit)
    err('table-1cce8-6', 0x1ccd0, rom, 0x1ccd0, puts=((NODE + 0x7c, 1, 6),))
    err('table-20710-8', 0x206ec, rom, 0x206ec, puts=((NODE + 0x76, 2, 8),))
    err('table-4cf64-4', 0x4d640, rom, 0x4d640, a4=REC, puts=((REC + 0x27, 1, 4),))
    # odd node / stack / A0 / A3 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-2027e', 0x2027e, odd, 0x2027e, stop=0x49c38, a6=NODE + 1)
    err('odd-node-20778', 0x20778, wodd, 0x20778, stop=0x20796, a6=NODE + 1)
    err('odd-node-20554', 0x20554, wodd, 0x20554, stop=0x20626, a6=NODE + 1)
    err('odd-node-21494', 0x21494, odd, 0x21494, stop=0xce02, a6=NODE + 1)
    err('odd-stack-1c390', 0x1c390, odd, 0x1c390, stop=0x4d7a6, a7=SP + 1)
    err('odd-stack-1c39a', 0x1c39a, odd, 0x1c39a, stop=0x1c3dc, a7=SP + 1)
    err('odd-stack-1c3ca', 0x1c3ca, odd, 0x1c3ca, carry=1, stop=0x1c3dc, a7=SP + 1)
    err('odd-stack-1c462', 0x1c462, odd, 0x1c462, stop=0x1c480, a7=SP + 1)
    err('odd-stack-1c494', 0x1c494, odd, 0x1c494, a7=SP + 1)
    err('odd-stack-1c45c', 0x1c45c, odd, 0x1c45c, stop=0x1c462, a0=PLAYERS[0], a7=SP + 1)
    err('odd-a0-1cb44', 0x1cb44, odd, 0x1cb44, stop=0x1cb56, a0=NODE + 1)
    err('odd-a0-1cb1a', 0x1cb1a, odd, 0x1cb1a, stop=0x1cb30, a0=NODE + 1, d7=2)
    err('odd-a4-1c412', 0x1c412, odd, 0x1c412, stop=0x1c41e, a4=NODE + 1)
    err('odd-a4-4d63a', 0x4d63a, odd, 0x4d63a, stop=0x4d640, a4=NODE + 1)
    err('odd-a3-1c408', 0x1c408, odd, 0x1c408, stop=0x1c432, a3=NODE + 1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('20f04-then-20f20', 0x20f04, odd, 0x20f20, a7=SP + 1)
    err('21524-then-21540', 0x21524, odd, 0x21540, a7=SP + 1, puts=((NODE + 0x46, 2, 0x100),))
    err('4d628-then-4d6a8', 0x4d628, odd, 0x4d6a8, a7=SP + 1)
    err('214d6-then-21564', 0x214d6, unrouted, 0x21564)
    err('208f2-then-208fa', 0x208f2, unrouted, 0x208fa, puts=((NODE + 0x5e, 1, 0x80),))
    err('21f8a-then-2210c', 0x21f8a, unrouted, 0x2210c, d0=0x10)
    err('2093a-then-20952', 0x2093a, unrouted, 0x20952)
    err('1c356-then-1c4aa', 0x1c356, odd, 0x1c4aa, d1=0x13, a7=SP + 1)


def main():
    rng = random.Random(0xC5C5)
    B.load_routing()
    gen_singles(rng)
    gen_paths(rng)
    gen_tables()
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
