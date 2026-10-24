"""Generates the native-oracle tables of engine/tests/animation_machine_player_c10_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit, every one differs from the original): the LONG table 20444 (2042e, index BYTE
a9 0..5), the bank-window LONG 200038 (24ecc; bank 200000: physical offset = CPU address), the WORD tables 1b7fc / 1b81e (C2 1cb08 / C5 1cb1a for the
producer chain of 22164), the BYTE table 21ba6 (C3 21baa for the producer chain of 21de2), the (handler LONG, key WORD) lists 21b0a / 216c8 (C3 215e6
for the producer chains of 21e0c / 22296 / 22374: the ROM handlers with other keys) and the LONG table 1c52c (C5 1c51c for the Z chain of 20508).  A
native run that reads any other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a PC that is not a block start, a JMP
(A1) 21e10 / 2229a / 22378 to a PC outside its ROM list or a JMP 203b0(PC,D0.W) beyond the table (the C++ checked jump-target error), a run that writes
a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 8c(A6) := the record 10ea00 (BYTE 4 0..18), LONG 84(A6) := a routed slot-84 value, WORDs 76 / 78 small, BYTEs 9c / 9d / 9e / 9f / a9 small or
signed boundaries), A0 / A3 / A4 the record 10ea00, A1 a handler of the ROM list of the JMP (A1), A2 the parent / child node, A5 = 108000, seeded BYTE /
WORD / LONG field edits (sign boundaries included), seeded D0-D7 (the input bits of D0, D1 of 1cec2, D7 of 2156a) and the hint worlds of the V1 spec
(tools/unit_fixture_specs/pc10.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' / 'a6rec' address
the record 10ea00 (rec + 20 = A0 / A2 / A4 / LONG 8c), 'a5off' an A5 field).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a JMP
            (A1) list handler, an unrouted entry of the table 203b0).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, list handlers, the RTS sentinel), a consumer or a Z reader.
  single 2  a consumer entered through its real producer (and the Z readers 1efee / 1eff6 / 20508 through 1efe8 / 1eff2 / 204fa): kept when both outcomes
            occur.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  a Z reader entered directly: the native SR Z = the recomputed Z (1efee: BYTE 15(A6) bit 7 clear, 1eff6: D0 bit 5 clear, 20508: D7 bit (D1 mod
            32) clear); the C++ recomputes it (contract decision 3).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: every block leaves Unknown (no producer, no pass block); the 7 consumers keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c10_test_table.py  (rewrites the generated section in place)
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
import pc10 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c10_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREADS = (0x1efee, 0x1eff6, 0x20508)                # the Z readers (BEQ on BTST.B #7,15(A6) / BEQ on BTST #5,D0 / BNE on the 1c51c BTST.L D1,D7)
assert tuple(B.Z_READERS) == ZREADS
ZSET = set(ZREADS)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, LTAB = 0x10ea00, 0x10eb00, 0x10e700
PLAYERS = (0x100cb8, 0x100da8)
LIST_21B0A_KEYS = (2, 5, 0, 3)                      # synthetic keys of the list 21b0a (ROM: 0 1 3 4); the handlers are the ROM handlers
LIST_216C8_KEYS = (3,)                              # synthetic key of the list 216c8 (ROM: 0)
LIST_JUMPS = dict((k, set(v)) for k, v in B.LIST_JUMPS.items())
TABLE_203B0 = tuple(B.TABLE_203B0)


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def table_20444():
    """6 LONGs at 20444 (2042e: MOVE.L (20444 + 4 x BYTE a9),D7; 0 -> BEQ 20516, else MOVE.L D7,(A6))."""
    return longs((0x10000, 0, 0x12345678, 0x1ed78, 0, 0x80000000))


def table_1b7fc():
    """50 WORDs at 1b7fc..1b860: C2 1cb08 reads WORD (A0 + 2 x BYTE 9f) (A0 = 1b7fc / 1b81e for 22148 / 2215c, BYTE 9f 0..8); not 0 -> C5 1cb1a reads
    WORD (A0 + W) and tests LONG 22(A6) + 4 x that WORD."""
    w = [0] * 50
    w[0:9] = [0x40, 0, 0x42, 0, 0x44, 0, 0, 0, 0]                  # 1b7fc + 2k: W = 40 / 42 / 44 -> 1b83c / 1b83e / 1b840
    w[17:26] = [0x30, 0, 0, 0x32, 0, 0, 0, 0, 0x34]               # 1b81e + 2k: W = 30 / 32 / 34 -> 1b84e / 1b850 / 1b852
    w[32:35] = [1, 2, 3]                                          # 1b83c / 1b83e / 1b840
    w[41:44] = [4, 5, 6]                                          # 1b84e / 1b850 / 1b852
    return words(w)


def table_21ba6():
    """4 BYTEs at 21ba6: C3 21baa compares BYTE (21ba6 + WORD 76) with BYTE a1(A6) (WORD 76 0..3)."""
    return bytes((0x02, 0x05, 0x00, 0xff))


def table_1c52c():
    """4 LONGs at 1c52c: C5 1c51c: D7 := LONG (1c52c + 4 x BYTE 9e(A0)); BTST.L D1,D7 (BYTE 9e 0..3)."""
    return longs((0x0000ffff, 0x80000001, 0x00f0f0f0, 0x7ffffffe))


def plist(handlers, keys):
    out = b''
    for h, k in zip(handlers, keys):
        out += struct.pack('>IH', h, k)
    return out + struct.pack('>I', 0)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1b7fc, table_1b7fc()),                                            # C2 1cb08 / C5 1cb1a from 22160
            (0x1c52c, table_1c52c()),                                            # C5 1c51c from 204fa
            (0x20444, table_20444()),                                            # 2042e
            (0x216c8, plist(B.LIST_216C8, LIST_216C8_KEYS)),                     # C3 215e6 from 2228e / 2236c
            (0x21b0a, plist(B.LIST_21B0A, LIST_21B0A_KEYS)),                     # C3 215e6 from 21e04
            (0x21ba6, table_21ba6()),                                            # C3 21baa from 21dde
            (0x200038, longs((0x00abcdef,)))]                                    # 24ecc (bank window)


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


# consumer -> (C clear successor, C set successor); the Z readers -> (Z clear successor, Z set successor)
SUCC = {0x21dda: (0x21dde, 0x223b2), 0x21de2: (0x21de6, 0x223b2), 0x21dea: (0x21dee, 0x223b2), 0x21e0c: (0x21e12, 0x21e10), 0x22164: (0x22174, 0x22168),
        0x22296: (0x2229c, 0x2229a), 0x22374: (0x2237a, 0x22378)}
assert set(SUCC) == CONS_SET
ZSUCC = {0x1efee: (0x1eff2, 0x1fae8), 0x1eff6: (0x1effa, 0x1f01a), 0x20508: (0x20516, 0x2050c)}
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both outcomes occur
CHAIN_CANDIDATES = tuple(B.CHAINS)
JUMP_ALLOWED = dict(LIST_JUMPS)
JUMP_ALLOWED[0x203ac] = set(TABLE_203B0)


def cons_value(cons, o):
    """The flag a consumer read (1 clear / 2 set; for a Z reader: 1 Z clear / 2 Z set): from its successor in the trace."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    succ = ZSUCC[cons] if cons in ZSET else SUCC[cons]
    nxt = next(p for p in tr[i + 1:] if p in succ)
    return 1 if nxt == succ[0] else 2


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


def native(ram, regs, pc, carry, stopfn, flags=0):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0) | flags)
    out = dict(stop=None, bad=False)
    trace = []
    stray = []
    n = [0]

    def at(uc, p, size, user):
        if out['stop'] is not None:
            return
        n[0] += 1
        if trace and trace[-1] in JUMP_ALLOWED and p not in JUMP_ALLOWED[trace[-1]]:
            out['bad'] = True                       # a computed jump outside the list / the table: the C++ checked jump-target error (error rows)
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
        return None                                 # the kept runs write no device port
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
    """C after the block p entered with c (0 unknown / 1 clear / 2 set): the consumers keep it, every other C10 block leaves Unknown."""
    if p in CONS_SET:
        return c
    return 0


def model(executed, carry):
    """C after a path."""
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
BOUNDED = (0x9e, 0x9f, 0x9c, 0x76, 0x78, 0xa9)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'scc', 'smi', 'spl', 'abcd'):
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((REC, CHILD)),
                a1=rng.choice((PARENT, CHILD)), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x22, 0x30, 0x40, 0x48, 0x50, 0x80, 0xffff, 0x12345678, 0x10000, 0x10001,
                                 0x8000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 2, 0x101, 0x102, 0x10001, 0xffff0001, 0x12, 0x13, 0x12340000, 0x80000000))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 0x10000, 1, 0xffff, 0x12340000))
    if s in LIST_JUMPS:
        regs['a1'] = rng.choice(sorted(LIST_JUMPS[s]))
    if s == 0x1c50e:
        regs['d0'] = rng.choice((PARENT, CHILD))         # 1c500: D0 = LONG c(A6) (not 0): MOVEA.L D0,A0; CLR.L b2(A0)
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
    # the node links and pointers, the slot LONG 84, the bounded indices; the player nodes; the record LONG 8c(A6) with its BYTE 4 0..18
    r.put(NODE + 0xc, 4, rng.choice((PARENT, PARENT, 0)))
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0x9e, 1, rng.randrange(4))
    r.put(NODE + 0x9f, 1, rng.randrange(9))
    r.put(NODE + 0x9c, 1, rng.randrange(6))
    r.put(NODE + 0xa9, 1, rng.randrange(6))
    r.put(NODE + 0x76, 2, rng.randrange(4))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 2, 0x100, 0x8000)))
    r.put(REC + 4, 1, rng.randrange(19))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for i in range(0, 0x80, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # C5 1cb1a: LONG 22(A6) + sext(4 x WORD)
    if hint:
        regs.update(hint.get('regs', {}))
        for k, v in hint.get('regrec', {}).items():
            regs[k] = REC - 0x20 + v                      # the V1 spec's record: rec + 20 is A0 / A2 / A4 (REC here)
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a6rec', []):
            r.put(NODE + off, n, REC - 0x20 + v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('rec', []):
            r.put(REC - 0x20 + off, n, v)
        for off, n, v in hint.get('stack', []):
            r.put(SP + off, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the JMP (A1) list handlers, the unrouted table entries and the RTS sentinel
ROUTED_EXITS = {0x2a00, 0x3af8, 0x8ebe, 0xce02, 0x1aa3a, 0x1c1e2, 0x1c356, 0x1c51c, 0x1cab6, 0x1cabe, 0x1cb08, 0x1cc1a, 0x1cd98, 0x1cec2, 0x1d09e,
                0x1d1d0, 0x1ed78, 0x1eeea, 0x1f070, 0x1f086, 0x1f1d8, 0x1f2a4, 0x1f3ec, 0x1f7a4, 0x1fa3c, 0x1fa68, 0x1fae8, 0x201a2, 0x20516, 0x20c00,
                0x2156a, 0x215e6, 0x21baa, 0x21bc6, 0x21c1c, 0x21ffc, 0x2210c, 0x22128, 0x22174, 0x221ca, 0x223b2, 0x223c4, 0x24ffa, 0x253c8,
                0x492c8, 0x49f8c, 0x49fc6, 0x4bfc0}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == set()
JUMP_TARGETS = set(t for v in LIST_JUMPS.values() for t in v if t not in STARTS_SET) | set(t for t in TABLE_203B0 if t not in STARTS_SET)
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(JUMP_TARGETS - ROUTED_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p in ZSET


def hints(s):
    """The V1 spec hint worlds (pc10.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def zread_hints(s):
    """The Z readers: 1efee BYTE 15(A6) (the native SR Z = bit 7 clear), 1eff6 D0 (Z = bit 5 clear), 20508 D7 / D1 (Z = D7 bit (D1 mod 32) clear)."""
    if s == 0x1efee:
        return [dict(a6off=[(0x15, 1, v)]) for v in (0, 0x80, 0x7f, 0xff, 1, 0x81)] + [dict(a6off=[(0x15, 1, 0x80)], mirror=True)]
    if s == 0x1eff6:
        return [dict(regs=dict(d0=v)) for v in (0, 0x20, 0xffffffdf, 0xffffffff, 0x12340020, 0x10)]
    return [dict(regs=dict(d7=d7, d1=d1)) for d7, d1 in ((0x0007ffff, 0), (0x0007ffff, 18), (0x0007ffff, 19), (0x0007ffff, 0x13), (0x80000000, 31),
                                                         (0x80000000, 0xffffff1f), (1, 32), (1, 0x20), (0xfffffffe, 0x100), (0, 5))]


def zflag(s, r, regs):
    """The Z flag the predecessor leaves for the Z reader s (the SR bit 2 of the native entry)."""
    if s == 0x1efee:
        return (r.byte(regs['a6'] + 0x15) & 0x80) == 0
    if s == 0x1eff6:
        return (regs['d0'] & 0x20) == 0
    return (regs['d7'] & (1 << (regs['d1'] & 31))) == 0


def gen_singles(rng):
    for s in STARTS:
        if s in CONS_SET:
            continue
        fl = fields(s)
        kept = {}
        hs = zread_hints(s) if s in ZSET else hints(s)
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs = world(rng, fl, s, hint)
            flags = 0
            if s in ZSET:
                if hint is None:
                    continue
                flags = 4 if zflag(s, r, regs) else 0
            o = native(r.b, regs, s, 0, single_stop, flags)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue                                 # a stop at the entry is a zero-step run
            if nxt in CONS_SET or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 5 if s in ZSET else 1, o)


PATH_ENTRIES = tuple(s for s in STARTS if s not in CONS_SET and s not in ZSET)


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
            if any(p in CONS_SET or p in ZSET for p in ex) or not allowed(o['stop']) or o['stop'] == s:
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


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=REC,
             a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    if entry == 0x21dd0:                                         # 21bc6: CMPI.B #1,9e(A6); BCLR.B #4,a7(A6)
        r.put(NODE + 0x9e, 1, rng.choice((0, 1, 1, 2)))
        r.put(NODE + 0xa7, 1, rng.choice((0, 0x10, 0x30, 0xff)))
    if entry == 0x21dde:                                         # 21baa: TST.B 9f(A6); synthetic BYTE (21ba6 + WORD 76) against BYTE a1(A6)
        r.put(NODE + 0x9f, 1, rng.choice((0, 0, 1)))
        r.put(NODE + 0xa1, 1, rng.choice((0, 1, 2, 5, 6, 0xff)))
    if entry in (0x21e04, 0x2228e, 0x2236c):                     # 215e6 on the synthetic lists 21b0a / 216c8: BYTE 9c
        r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 4, 5, 0xff)))
    if entry == 0x22148:                                         # 1cb08 on the synthetic WORD tables 1b7fc / 1b81e (BYTE a7 bit 1 picks one)
        r.put(NODE + 0x9f, 1, rng.randrange(9))
        r.put(NODE + 0xa7, 1, rng.choice((0, 2, 0xff, 0xfd)))
    if entry == 0x1efe8:                                         # the Z source BYTE 15(A6) bit 7
        r.put(NODE + 0x15, 1, rng.choice((0, 0x80, 0x7f, 0xff)))
    if entry == 0x1eff2:                                         # the Z source D0 bit 5
        regs['d0'] = rng.choice((0, 0x20, 0xffffffdf, 0xffffffff))
    if entry == 0x204fa:                                         # 1c51c on the synthetic LONG table 1c52c (BYTE 9e) with D1.B = BYTE 4 of the record
        r.put(NODE + 0x9e, 1, rng.randrange(4))
        r.put(REC + 4, 1, rng.choice((0, 1, 7, 15, 16, 31, 32, 0x81)))
    return r, regs


CHAINS = []


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            if SUCC[cp][1] in LIST_JUMPS:
                regs['a1'] = sorted(LIST_JUMPS[SUCC[cp][1]])[0]
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st) and len(tr) > 0)
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C (the Z readers recompute)
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(ZSUCC[cons] if cons in ZSET else SUCC[cons])
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
            continue                                             # one outcome never occurred (or the producer reads undeclared ROM): declared rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c) if cons not in ZSET else 0, 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c10 jump target'
    flag = 'unsupported animation player c10 flag source'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c10 caller requires known carry', cp, stop=SUCC[cp][0])
    # the JMP (A1) (contract decision 2): A1 outside the list (compared as a LONG)
    for v in (0x21d60, 0x21e49, 0, 0x121602, 0x21e52, 0x1021e48, 0x21c23):
        err('jump-21e10-%x' % v, 0x21e10, jump, 0x21e10, a1=v)
    for jp in (0x2229a, 0x22378):
        for v in (0x21d60, 0x21e48, 0, 0x21603, 0x1021602):
            err('jump-%x-%x' % (jp, v), jp, jump, jp, a1=v)
    # the table jump 203ac (contract decision 2): BYTE 9f 9 .. ff beyond the table (checked); 1 .. 8 an unrouted table entry (the next dispatch)
    for v in (9, 0x10, 0x80, 0xff):
        err('jump-203a0-9f-%x' % v, 0x203a0, jump, 0x203a0, puts=((NODE + 0x9f, 1, v),))
    for v in range(1, 9):
        err('entry-203a0-9f-%x' % v, 0x203a0, unrouted, 0x203b0 + 4 * v, puts=((NODE + 0x9f, 1, v),))
    # the Z source of 1efee (contract decision 3): BYTE 15(A6) outside work RAM / fixed ROM
    for v in (0x200000 - 0x15, 0x3c0000, 0x2ffff0, 0x300000 - 0x15):
        err('z-a6-%x' % v, 0x1efee, flag, 0x1efee, a6=v)
    # fixed ROM / bank outside the declared synthetic bytes: the LONG table 20444 (BYTE a9 6 / 7f / ff), the BYTE 61(A2) of 252ce in fixed ROM
    for v in (6, 0x7f, 0xff):
        err('rom-2042e-a9-%x' % v, 0x2042e, rom, 0x2042e, puts=((NODE + 0xa9, 1, v),))
    err('rom-252ce-a2', 0x252ce, rom, 0x252ce, a2=0x1d000)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1c4c2', 0x1c4c2, wodd, 0x1c4c2, stop=0x1c4d2, a6=NODE + 1)
    err('odd-node-1c4e0', 0x1c4e0, odd, 0x1c4e0, stop=0x1c4e8, a6=NODE + 1)
    err('odd-node-1c500', 0x1c500, odd, 0x1c500, stop=0x1c50e, a6=NODE + 1)
    err('odd-node-1dc92', 0x1dc92, wodd, 0x1dc92, stop=0x1aa3a, a6=NODE + 1)
    err('odd-node-204e4', 0x204e4, wodd, 0x204e4, stop=0x492c8, a6=NODE + 1)
    err('odd-node-204fa', 0x204fa, odd, 0x204fa, stop=0x1c51c, a6=NODE + 1)
    err('odd-node-2050c', 0x2050c, odd, 0x2050c, stop=0x1c356, a6=NODE + 1)
    err('odd-node-22286', 0x22286, wodd, 0x22286, stop=0x2228e, a6=NODE + 1)
    err('odd-node-24ecc', 0x24ecc, wodd, 0x24ecc, stop=0x24b78, a6=NODE + 1)
    err('odd-node-24ee2', 0x24ee2, wodd, 0x24ee2, stop=0x49f8c, a6=NODE + 1)
    err('odd-a5-24b78', 0x24b78, odd, 0x24b78, stop=0x24b8a, a5=A5 + 1)
    err('odd-a0-1c50e', 0x1c50e, wodd, 0x1c50e, stop=0x1c514, d0=PARENT + 1)
    err('odd-stack-1c4e8', 0x1c4e8, odd, 0x1c4e8, a7=SP + 1)
    err('odd-stack-1c4f8', 0x1c4f8, odd, 0x1c4f8, a7=SP + 1)
    err('odd-stack-22312', 0x22312, odd, 0x22312, a7=SP + 1)
    err('odd-stack-2239e', 0x2239e, odd, 0x2239e, a7=SP + 1)
    err('odd-stack-24b94', 0x24b94, odd, 0x24b94, a7=SP + 1)
    err('odd-stack-1dc8e', 0x1dc8e, odd, 0x1dc8e, stop=0x1d1d0, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-20414', 0x20414, device, 0x20414, stop=0x2041a, a6=0)
    err('rom-write-223fa', 0x223fa, device, 0x223fa, stop=0x1cabe, a6=0)
    err('rom-write-2234c', 0x2234c, device, 0x2234c, stop=0x22360, a6=0x203a0)          # a5(A6) = 20445: the synthetic table 20444 (read), then the write
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1c4d2-then-1c4e8', 0x1c4d2, odd, 0x1c4e8, a7=SP + 1, puts=((NODE + 0x7a, 1, 0), (NODE + 0x78, 2, 2)))
    err('1c4b0-then-1c50e', 0x1c4b0, wodd, 0x1c50e, puts=((NODE + 0xc, 4, PARENT + 1),))                      # WORD 76 = 0 -> 1c500 -> odd parent
    err('22304-then-22312', 0x22304, odd, 0x22312, a7=SP + 1, d7=0x10000)
    err('2237e-then-2239e', 0x2237e, odd, 0x2239e, a7=SP + 1)
    err('20324-then-203bc', 0x20324, unrouted, 0x203bc, puts=((NODE + 0x9f, 1, 3),))
    err('252b4-then-252d8', 0x252b4, odd, 0x252d8, a7=SP + 1, a2=PARENT)


def main():
    rng = random.Random(0xC10C)
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
    jstops = set(d['stop'] for d in singles if d['entry'] in LIST_JUMPS or d['entry'] == 0x203a0)
    print('list handlers / table entries reached by the computed-jump rows', sorted(hex(x) for x in jstops))


if __name__ == '__main__':
    main()
