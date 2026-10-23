"""Generates the native-oracle tables of engine/tests/animation_machine_player_c7_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the WORD table 1b310 that C2 1cb08 reads for the producer chains of 1f644 /
1f776, the LONG table 1f65e (1f648: 1f65e + 4 x BYTE 4(A4)), the LONG sub-tables 22502 / 2254e and the LONG table 225e6 (226ca: 225e6 + 4 x BYTE 9e,
then + 4 x BYTE 4(A4)), the LONG table 225f6 (2267a: 225f6 + 4 x BYTE 4(A4)), the BYTE table 22642 (22656: 22642 + BYTE 4(A4)), the LONG lists 227fc
.. 2283c and the LONG table 2284c (22894: 2284c + 4 x BYTE 9e, 228cc: list + 4 x BYTE 6(A4)), the LONG tables 25082 / 250c2 (25122: + 4 x (BYTE 77 & f))
and the bank-window LONGs 2000b8 / 200094 (24fb0 / 251c2, bank 200000).  A native run that reads any other fixed-ROM or banked byte is dropped (a table
index beyond the declared bytes), as is a run that lands inside the unit on a PC that is not a block start, a computed jump 25298 outside the table
2529c..252bc (the C++ checked jump-target error), a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 8c(A6) := the record 10ea00 (A4: BYTE 2 / 3 / 4 / 6 / 7, WORD a / c), LONG 84(A6) := a routed slot-84 value, WORD 76 / 78 mostly 0 / 1, BYTE 9e
0..3, BYTE 9f 0..4), the player nodes 100cb8 / 100da8, the BYTE records 5450 / 5460(A5), the BYTE 10f001, A0 = 10e600 (a script LONG: LONG (10e600)
= 10e610, three WORDs at 10e610) or the record, A1 = 10e610, A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded
D0-D7 (D0.W 0..8 for 25294, the input bits of D0, the key D1.B of 1c9ec) and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc7.py
hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' address the record 10ea00, 'stack' writes at A7).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a table entry of 25298).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, table entries, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer: kept when both C values occur.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit; the SCS.B
            25140 stores ff / 00 into BYTE 83(A6)).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 1ca04 1ca28 Clear, 1ca46 1ca56 1ca6a Set, 1ca5c the borrow of CMP.B 3(A4),D2 (data); 1ca12 / 1ca68 keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c7_test_table.py  (rewrites the generated section in place)
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
import pc7 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c7_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
CLEAR_SET, SET_SET, PASS_SET, DATA_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET), set(B.DATA_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, REC2, LIST, RTAB, LTAB = 0x10ea00, 0x10eb00, 0x10ec00, 0x10e600, 0x10e800, 0x10e700
PLAYERS = (0x100cb8, 0x100da8)
TABLE_1F65E = tuple(0x31000 + 0x40 * k for k in range(19))
TABLE_22502 = tuple(0 if k % 3 == 0 else 0x32000 + 0x10 * k for k in range(38))          # the two sub-tables 22502 / 2254e (19 LONGs each)
TABLE_225E6 = (0x22502, 0x2254e, 0x2254e, 0x22502)
TABLE_225F6 = tuple(0 if k % 4 == 1 else 0x33000 + 0x10 * k for k in range(19))
TABLE_22642 = tuple(1 if k in (2, 5, 0x10) else 0 for k in range(0x14))
TABLE_227FC = tuple(0x34000 + 0x10 * k for k in range(16))                               # the four lists 227fc / 2280c / 2281c / 2282c (4 LONGs each)
TABLE_2284C = (0x2280c, 0x227fc, 0x2282c, 0x2281c)
TABLE_25082 = tuple(0x35000 + 0x20 * k for k in range(32))                               # 25082 (16 LONGs) and 250c2 (16 LONGs)
WINDOW_B8, WINDOW_94 = 0x0012abcd, 0x00345678
TABLE_2529C = tuple(B.TABLE_2529C)


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def table_1b310():
    """32 WORDs at 1b310: C2 1cb08 reads WORD (A0 + 2 x BYTE 9f) (A0 = 1b310 for 1f76e and the chain of 1f640); not 0 -> C5 1cb1a reads WORD (A0 + W)
    and tests LONG 22(A6) + 4 x that WORD."""
    w = [0] * 32
    w[0:5] = [0x10, 0, 0x12, 0, 0x14]            # 1b310 + 2 x 9f (9f 0..4)
    w[8:11] = [1, 2, 3]                          # 1b310 + 10 / 12 / 14
    return words(w)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1b310, table_1b310()),                                            # C2 1cb08 / C5 1cb1a from 1f640 / 1f76e
            (0x1f65e, longs(TABLE_1F65E)),                                       # 1f648: the LONG table 1f65e + 4 x BYTE 4(A4) (0..12)
            (0x22502, longs(TABLE_22502)),                                       # 226ca: the sub-tables 22502 / 2254e + 4 x BYTE 4(A4)
            (0x225e6, longs(TABLE_225E6)),                                       # 226ca: the LONG table 225e6 + 4 x BYTE 9e (0..3)
            (0x225f6, longs(TABLE_225F6)),                                       # 2267a: the LONG table 225f6 + 4 x BYTE 4(A4)
            (0x22642, bytes(TABLE_22642)),                                       # 22656: the BYTE table 22642 + BYTE 4(A4) (0..13)
            (0x227fc, longs(TABLE_227FC)),                                       # 228cc: the lists + 4 x BYTE 6(A4) (0..3)
            (0x2284c, longs(TABLE_2284C)),                                       # 22894: the LONG table 2284c + 4 x BYTE 9e (0..3)
            (0x25082, longs(TABLE_25082)),                                       # 25122: the LONG tables 25082 / 250c2 + 4 x (BYTE 77 & f)
            (0x2000b8, struct.pack('>I', WINDOW_B8)),                            # 24fb0: the bank-window LONG 2000b8 (bank 200000)
            (0x200094, struct.pack('>I', WINDOW_94))]                            # 251c2: the bank-window LONG 200094


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


# consumer -> (C clear successor, C set successor); the SCS.B 83(A6) of 25140 continues to 25144 with BYTE 83 = 00 / ff
SUCC = {0x1ca0e: (0x1ca12, 0x1ca14), 0x1f330: (0x1f33a, 0x1f334), 0x1f5c4: (0x1f5ce, 0x1f5c8), 0x1f644: (0x1f648, 0x1f6aa), 0x1f752: (0x1f76a, 0x1f756),
        0x1f776: (0x1f77a, 0x1f77e), 0x22674: (0x22678, 0x2267a), 0x22704: (0x22786, 0x2270a), 0x25140: (0x25144, 0x25144), 0x25454: (0x2545e, 0x25458)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both C values occur
CHAIN_CANDIDATES = tuple(B.CHAINS)
JUMP_ALLOWED = {0x25298: set(TABLE_2529C)}


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (the first PC after the consumer that is one of its two successors); 25140 from the
    BYTE 83(A6) it stored."""
    if cons == 0x25140:
        return 2 if o['ram'][(NODE + 0x83) & 0xffff] == 0xff else 1
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
        if trace and trace[-1] in JUMP_ALLOWED and p not in JUMP_ALLOWED[trace[-1]]:
            out['bad'] = True                       # a computed jump outside the table: the C++ checked jump-target error (error rows)
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
        return None                                 # C7 writes no device port
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


def data_carry(p, o):
    """The C of the data producer 1ca5c: MOVE.B 2(A4),D2; CMP.B 3(A4),D2 (D2.B and A4 unchanged after it): the borrow, unsigned D2.B < BYTE 3(A4)."""
    assert p == 0x1ca5c, hex(p)
    return 2 if (o['regs']['d2'] & 0xff) < o['ram'][(o['regs']['a4'] + 3) & 0xffff] else 1


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


def path_data(ex, o):
    """The C of the last data producer of a path when only pass blocks follow it (D2 / A4 / the record are unchanged by them)."""
    idx = [i for i, p in enumerate(ex) if p in DATA_SET]
    if not idx or any(p not in PASS_SET for p in ex[idx[-1] + 1:]):
        return 0
    return data_carry(ex[idx[-1]], o)


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


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((LIST, LIST, REC, CHILD) + PLAYERS),
                a1=LIST + 0x10, a2=rng.choice((PARENT, CHILD)), a3=rng.choice((REC, REC2)), a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x22, 0x30, 0x40, 0x50, 0x80, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000))
    if rng.random() < 0.7:
        regs['d1'] = (regs['d1'] & 0xffffff00) | rng.choice((0, 1, 2, 3, 5, 0xa, 0x11, 0x13, 0xff))
    if s == 0x25294:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 4, 5, 6, 7, 8, 0x4002, 0x8001, 0xc008))
    if s in (0x2528c,) and rng.random() < 0.7:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(12)
    if s == 0x25122:
        regs['a0'] = rng.choice((0x25082, 0x250c2))
        regs['d0'] = (regs['d0'] & 0xffff0000) | (4 * rng.randrange(16))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or disp in BOUNDED):
            continue                                    # (A6) callback LONG, the node links, the pointer fields and the bounded indices are declared below
        if reg == 4 and disp in (4, 6):
            continue
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links and pointers, the record, the slot LONG 84, the bounded indices; the player nodes; the A5 records and the BYTE 10f001; the script
    # LONG at LIST (-> LIST + 10: three WORDs and the WORD 2 / 8 test value)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0x9e, 1, rng.randrange(4))
    r.put(NODE + 0x9f, 1, rng.randrange(5))
    r.put(NODE + 0x76, 2, rng.choice((0, 0, 1, 1, 0x4000, 0xffff)))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 0x100)))
    r.put(NODE + 0x77, 1, rng.randrange(0x40))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x8c, 4, rng.choice((REC, REC2)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    r.put(REC + 2, 1, rng.choice((0, 1, 2, 3, 0x80, 0xfe)))
    r.put(REC + 3, 1, rng.choice((0, 1, 2, 3, 0x80, 0xff, 0xff)))
    r.put(REC + 4, 1, rng.randrange(0x13))
    r.put(REC + 6, 1, rng.choice((0, 1, 2, 3, 3, 4, 0xff)))
    r.put(REC + 7, 1, rng.choice((0, 0, 1, 2, 0x80)))
    r.put(REC + 0xa, 2, rng.choice((0, 0, 1, 2, 0x8000)))
    r.put(REC + 0xc, 2, rng.choice((0, 1, 2, 0xffff, 0x8000)))
    for k in (0x5450, 0x5460):
        r.put(A5 + k + 4, 1, rng.choice((0, 1, 2, 3, 5, 0xa, 0xff)))
        r.put(A5 + k + 2, 1, rng.choice((0, 1, 2, 3, 0x80)))
        r.put(A5 + k + 3, 1, rng.choice((0, 1, 2, 3, 0xff)))
        r.put(A5 + k + 0xc, 2, rng.choice((0, 1, 2, 0xffff, 0x8000)))
    r.put(0x10f001, 1, rng.getrandbits(8))
    r.put(LIST, 4, LIST + 0x10)
    for k in range(3):
        r.put(LIST + 0x10 + 2 * k, 2, rng.choice((0, 2, 8, 0x10, 0x80, 0xfff0, 0x7f80, 0x8000)))
    for i in range(0, 0x40, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # C5 1cb1a: LONG 22(A6) + sext(4 x WORD)
    if s in (0x2269e, 0x22704, 0x2288e, 0x228e6, 0x226c8):
        regs['a7'] = SP - 4                               # the stacked A0 that the block reads or pops (above it the return LONG)
        r.put(SP - 4, 4, LIST + 0x10)
    if s == 0x224a6:
        regs['a7'] = SP - 8                               # the stacked A0, WORD 46 and WORD 42 that 224a6 pops
        r.put(SP - 8, 4, LIST + 0x10)
        r.put(SP - 4, 2, rng.choice((0, 0x100, 0x8000)))
        r.put(SP - 2, 2, rng.choice((0, 0x140, 0xffff)))
    if hint:
        regs.update(hint.get('regs', {}))
        for k, v in hint.get('regrec', {}).items():
            regs[k] = REC - 0x20 + v if k == 'a4' or v >= 0x20 else (LIST + v)
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('rec', []):
            # the V1 spec's record: rec + 20 is A4 (BYTEs 2 / 3 / 4 / 6 / 7, WORDs a / c), rec + 10 the three WORDs, rec + 76 a child BYTE
            if off >= 0x20 and off < 0x40:
                r.put(REC + off - 0x20, n, v)
            else:
                r.put(LIST + off, n, v)
        for off, n, v in hint.get('stack', []):
            r.put(SP + off, n, LIST + 0x10 if v == B.SCR + 0x10 else v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
    for k in ('a0', 'a1'):
        if regs[k] < 0x100000 or regs[k] >= 0x110000:
            if not syn_ok(regs[k], 1) and k == 'a1':
                regs[k] = LIST + 0x10                   # a hint pointer outside work RAM and the declared bytes
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the unrouted table entries and the RTS sentinel
ROUTED_EXITS = {0x2986, 0x2a00, 0x3af8, 0x8ebe, 0xce02, 0x16ed2, 0x1cab6, 0x1cb08, 0x1cd98, 0x1cec2, 0x1f7a4, 0x1fa3c, 0x1faa0, 0x1fad2, 0x1fae8,
                0x201a2, 0x2291a, 0x43e34, 0x443d2, 0x491b6, 0x49214, 0x49a58, 0x49f8c, 0x49fc6, 0x4ae4a, 0x4bb52, 0x4be34, 0x4bfc0, 0xea69c}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x1eb98, 0x1f756, 0x1fa68}
JUMP_TARGETS = set(t for t in TABLE_2529C if t not in STARTS_SET)
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_TARGETS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET


def hints(s):
    """The V1 spec hint worlds (pc7.hint_worlds) of the block; converted to absolute addresses by world()."""
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
                continue                                 # a stop at the entry is a zero-step run
            if (nxt in CONS_SET and s not in CLEAR_SET | PASS_SET | SET_SET | DATA_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
            data = data_carry(s, o) if s in DATA_SET else 0
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, data), 1, o)


PATH_ENTRIES = tuple(s for s in STARTS if s not in CONS_SET)


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
            if any(p in CONS_SET for p in ex) or not allowed(o['stop']) or o['stop'] == s:
                continue
            key = (o['stop'], tuple(ex[:60]))
            if key in kept:
                continue
            kept[key] = (r, regs, o, carry, ex, path_data(ex, o))
            if len(kept) >= 3:
                break
        if not kept:
            print('no path row', hex(s))
            continue
        for i, (k, (r, regs, o, carry, ex, data)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, data), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=LIST,
             a1=LIST + 0x10, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    if entry == 0x1ca0a:                                         # 1ca4c on the record A4: BYTE 3 = ff -> Set; BYTE 2 < BYTE 3 -> Set; else Clear
        b2, b3 = rng.choice(((0, 0xff), (2, 3), (3, 3), (4, 3), (0x80, 0x7f), (0x7f, 0x80)))
        r.put(REC + 2, 1, b2)
        r.put(REC + 3, 1, b3)
    if entry in (0x1f32a, 0x1f5be, 0x1f74c, 0x2544e):            # 49fc6: LONG 26(A6) = 0 -> Set (else the interpreter reads ROM: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry in (0x1f640, 0x1f76e):                              # C2 1cb08 on the synthetic WORD table 1b310 with BYTE 9f 0..4
        regs['a0'] = 0x1b310
        r.put(NODE + 0x9f, 1, rng.randrange(5))
    if entry == 0x22670:                                         # 1c9ec: D0.W & 1 picks the record 5450 / 5460(A5); the key D1.B
        d0 = rng.choice((0, 1))
        key = rng.choice((3, 5))
        regs['d0'] = (regs['d0'] & 0xffff0000) | d0
        regs['d1'] = (regs['d1'] & 0xffffff00) | key
        rec = A5 + 0x5450 + 0x10 * d0
        r.put(rec + 4, 1, rng.choice((key, key, 0)))
        r.put(rec + 2, 1, rng.choice((0, 3, 4)))
        r.put(rec + 3, 1, rng.choice((3, 0xff, 3)))
        r.put(rec + 0xc, 2, rng.choice((0, 1, 0xffff)))
        r.put(0x10f001, 1, rng.choice((0, 8)))
    if entry == 0x226f0:                                         # 2986 / 28ae: D0.W a below the WORD 104ca0 -> a node from the free list LONG 104c9c,
        regs['d7'] = 0x24fb0                                     # Set; else Clear (the child: the C7 state 24fb0)
        regs['a7'] = SP
        r.put(0x104ca0, 2, rng.choice((0x100, 0x15, 0x40, 0, 0xa)))
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
            if cp == 0x22704:
                r.put(SP - 4, 4, LIST + 0x10)
                regs['a7'] = SP - 4                     # MOVEA.L (A7)+,A1 pops the stacked A0 before the BCC
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st) and len(tr) > 0)
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            if cp == 0x25140:
                assert o['ram'][(NODE + 0x83) & 0xffff] == (0xff if carry == 2 else 0), 'SCS.B 83(A6)'
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(SUCC[cons])
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            o = native(r.b, regs, entry, 0, lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS)
            if o is None or cons not in o['trace'] or o['stop'] not in succ:
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


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=LIST, a1=LIST + 0x10, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c7 jump target'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c7 caller requires known carry', cp, stop=SUCC[cp][0], **({'a7': SP - 4} if cp == 0x22704 else {}))
    # the computed jump (contract decision 2): displacements beyond the table; the unrouted entries fail at the next dispatch
    for v in (9, 0xa, 0x3fff, 0xffff, 0x8009, 0x12340009, 0x4009):
        err('jump-25294-%x' % v, 0x25294, jump, 0x25294, d0=v)
    for v in (0, 1, 3, 8, 0x4000):
        err('entry-25294-%x' % v, 0x25294, unrouted, 0x2529c + 4 * (v & 0x3fff), d0=v)
    # the ROM tables outside the declared synthetic bytes
    err('table-22642-14', 0x22656, rom, 0x22656, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0x14)))
    err('table-225f6-18', 0x2267a, rom, 0x2267a, d1=0x18)
    err('table-225f6-neg', 0x2267a, rom, 0x2267a, d1=0x2000)
    err('table-1f65e-13', 0x1f648, rom, 0x1f648, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0x13)))
    err('table-225e6-40', 0x226ca, rom, 0x226ca, puts=((NODE + 0x9e, 1, 0x40),))
    err('table-2284c-4', 0x22894, rom, 0x22894, puts=((NODE + 0x9e, 1, 4),))
    err('table-25082-80', 0x25122, rom, 0x25122, a0=0x25082, d0=0x80)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1f2ac', 0x1f2ac, wodd, 0x1f2ac, stop=0x1f2d4, a6=NODE + 1)
    err('odd-node-25172', 0x25172, odd, 0x25172, stop=0x25184, a6=NODE + 1)
    err('odd-node-22480', 0x22480, odd, 0x22480, stop=0x4ae4a, a6=NODE + 1)
    err('odd-stack-22480', 0x22480, odd, 0x22480, stop=0x4ae4a, a7=SP + 1)
    err('odd-stack-224a6', 0x224a6, odd, 0x224a6, stop=0x224b8, a7=SP + 1)
    err('odd-stack-22704', 0x22704, odd, 0x22704, stop=0x22786, a7=SP + 1, carry=2)
    err('odd-a4-1ca20', 0x1ca20, odd, 0x1ca20, stop=0x1ca28, a4=REC + 1)
    err('odd-a0-224c2', 0x224c2, odd, 0x224c2, stop=0x224d6, a0=REC + 1)
    err('odd-a1-2270a', 0x2270a, odd, 0x2270a, stop=0x22726, a1=REC + 1)
    err('odd-a0-22726', 0x22726, wodd, 0x22726, stop=0x2291a, a0=REC + 1)
    err('odd-a0-253de', 0x253de, wodd, 0x253de, stop=0x49214, a0=REC + 1)
    err('odd-a0-25122', 0x25122, odd, 0x25122, stop=0x4ae4a, a0=0x25083)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1f2fc-then-1fa68', 0x1f2fc, unrouted, 0x1fa68, d0=4)
    err('1f596-then-1eb98', 0x1f596, unrouted, 0x1eb98)
    err('1f71a-then-1eb98', 0x1f71a, unrouted, 0x1eb98)
    err('1f752-then-1f756', 0x1f752, unrouted, 0x1f756, carry=2)
    err('1ca4c-then-1ca68', 0x1ca4c, odd, 0x1ca68, a7=SP + 1, puts=((REC + 2, 1, 4), (REC + 3, 1, 3)))
    err('1c9fc-then-1ca04', 0x1c9fc, odd, 0x1ca04, a7=SP + 1, d1=4, puts=((REC + 4, 1, 3),))
    err('224b8-then-224c0', 0x224b8, odd, 0x224c0, a7=SP + 1)
    err('2274e-then-22758', 0x2274e, odd, 0x22758, a7=SP + 1)
    err('251ac-then-251c0', 0x251ac, odd, 0x251c0, a7=SP + 1, puts=((NODE + 0x89, 1, 7),))
    err('25470-then-25486', 0x25470, odd, 0x25486, a7=SP + 1, puts=((NODE + 0x46, 2, 0x180),))
    err('2528c-then-2529c', 0x2528c, unrouted, 0x2529c, d0=0)
    err('22766-then-22786', 0x22766, odd, 0x22786, a7=SP + 1, a0=REC, puts=((REC + 0x76, 1, 1),))


def main():
    rng = random.Random(0xC7C7)
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
    stops = set(d['stop'] for d in ROWS if d['error'] is None)
    print('exits never a stop', [hex(e) for e in EXITS if e not in stops])
    jstops = set(d['stop'] for d in singles if d['entry'] == 0x25294)
    print('table entries reached by 25294 rows', sorted(hex(x) for x in jstops))


if __name__ == '__main__':
    main()
