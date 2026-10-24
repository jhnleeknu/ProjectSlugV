"""Generates the native-oracle tables of engine/tests/animation_machine_player_c9_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit, every one differs from the original): the WORD tables 1b170 / 1b178 (one block:
20aa4 / 21376 / 2138e, index WORD 76 0..3), the LONG tables 22028 / 22074 / 220c0 (2218c, index BYTE 4 of the record LONG 8c(A6), 0..18), the WORD table
1b764 (C2 1cb08 / C5 1cb1a for the producer chain of 1eca0), the BYTE table 21ba6 (C3 21baa for the producer chain of 21cb6) and the (handler LONG,
key WORD) lists 21aee / 216c8 (C3 215e6 for the producer chains of 21ce0 / 21d32 / 22248 / 22424: the ROM handlers with other keys).  A native run that
reads any other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a PC that is not a block start, a JMP (A1) 21ce4 / 21d36 /
2224c / 22428 to a PC outside its ROM list (the C++ checked jump-target error), a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 8c(A6) := the record 10ea00 (BYTE 4 0..18), LONG 84(A6) := a routed slot-84 value, WORDs 76 / 78 / 88 small, BYTEs 9c / 9d / 9e / 9f small or
signed boundaries), the records 10e900 / 10e940 / 10e980 / 10e9c0 (A0 of a direct 1d08a / 1d096 / 20a54 / 20bd6 / 20cf6 / 20d62 entry: LONGs 4 / 8
/ 18, WORD 18, WORD 76), A1 a handler of the ROM list of the JMP (A1), A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included),
seeded D0-D7 (the input bits of D0, D1 of 1cec2 / ea680, D7 of 2156a) and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc9.py hint_worlds,
converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' address the record 10ea00 (rec + 20 = A0 / A4), 'stack' writes
at A7).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a JMP (A1) list handler).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, list handlers, the RTS sentinel), a consumer or the N reader.
  single 2  a consumer entered through its real producer (and the N reader 22180 through 22174): kept when both outcomes occur.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the N reader 22180 entered directly: the native SR carries N = bit 7 of BYTE 9d(A6) (V = 0), the C++ recomputes it from that BYTE.
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: every block leaves Unknown (no producer, no pass block); the 14 consumers keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c9_test_table.py  (rewrites the generated section in place)
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
import pc9 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c9_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREAD = 0x22180                                     # BLT on the N of the TST.B 9d(A6) of 22174 (recomputed from that BYTE)
assert tuple(B.Z_READERS) == (ZREAD,)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, LTAB = 0x10ea00, 0x10eb00, 0x10e700
MRECS = (0x10e900, 0x10e940, 0x10e980, 0x10e9c0)
PLAYERS = (0x100cb8, 0x100da8)
LIST_21AEE_KEYS = (3, 0, 5, 1)                      # synthetic keys of the list 21aee (ROM: 0 2 3 4); the handlers are the ROM handlers
LIST_216C8_KEYS = (2,)                              # synthetic key of the list 216c8 (ROM: 0)
LIST_JUMPS = dict((k, set(v)) for k, v in B.LIST_JUMPS.items())


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def table_1b170():
    """8 WORDs at 1b170 (the tables 1b170 / 1b178 of 21376 / 2138e / 20aa4 overlap: 1b178 = 1b170 + 8; index 2 x WORD 76(A6), WORD 76 0..3)."""
    return words((0x0101, 0x8202, 0x0303, 0xfff4, 0x0410, 0x7f11, 0x8612, 0x0013))


def tables_22028():
    """3 x 19 LONGs at 22028 / 22074 / 220c0 (2218c: MOVEA.L (A0 + 4 x BYTE 4(A4)),A0 for 1cabe); record-like LONGs, all different."""
    out = []
    for t in range(3):
        for i in range(19):
            out.append(0x10e800 + 0x40 * t + 2 * i if i % 3 else 0x1b000 + 0x100 * t + 4 * i)
    return longs(out)


def table_1b764():
    """32 WORDs at 1b764: C2 1cb08 reads WORD (A0 + 2 x BYTE 9f) (A0 = 1b764 for 1ec98); not 0 -> C5 1cb1a reads WORD (A0 + W) and tests LONG 22(A6)
    + 4 x that WORD."""
    w = [0] * 32
    w[0:5] = [0x10, 0, 0x12, 0, 0x14]            # 1b764 + 2 x 9f (9f 0..4)
    w[8:11] = [1, 2, 3]                          # 1b764 + 10 / 12 / 14
    return words(w)


def table_21ba6():
    """4 BYTEs at 21ba6: C3 21baa compares BYTE (21ba6 + WORD 76) with BYTE a1(A6) (WORD 76 0..3)."""
    return bytes((0x02, 0x05, 0x00, 0xff))


def plist(handlers, keys):
    out = b''
    for h, k in zip(handlers, keys):
        out += struct.pack('>IH', h, k)
    return out + struct.pack('>I', 0)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1b170, table_1b170()),                                            # 20aa4 / 21376 / 2138e
            (0x1b764, table_1b764()),                                            # C2 1cb08 / C5 1cb1a from 1ec98
            (0x216c8, plist(B.LIST_216C8, LIST_216C8_KEYS)),                     # C3 215e6 from 21d2a / 22240 / 2241c
            (0x21aee, plist(B.LIST_21AEE, LIST_21AEE_KEYS)),                     # C3 215e6 from 21cd8
            (0x21ba6, table_21ba6()),                                            # C3 21baa from 21cb2
            (0x22028, tables_22028())]                                           # 2218c


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


# consumer -> (C clear successor, C set successor); the N reader 22180 -> (N clear 22188, N set 2218c)
SUCC = {0x1eca0: (0x1eba0, 0x1eca4), 0x1ed14: (0x1ed1e, 0x1ed18), 0x1f118: (0x1f122, 0x1f11c), 0x1f52a: (0x1f534, 0x1f52e),
        0x20900: (0x2091e, 0x20904), 0x20a50: (0x20a6e, 0x20a54), 0x20bd2: (0x20bee, 0x20bd6), 0x21cae: (0x21cb2, 0x223b2),
        0x21cb6: (0x21cba, 0x223b2), 0x21cbe: (0x21cc2, 0x223b2), 0x21ce0: (0x21ce6, 0x21ce4), 0x21d32: (0x21d38, 0x21d36),
        0x22248: (0x2224e, 0x2224c), 0x22424: (0x2242a, 0x22428)}
assert set(SUCC) == CONS_SET
ZSUCC = (0x22188, 0x2218c)
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both outcomes occur
CHAIN_CANDIDATES = tuple(B.CHAINS)
JUMP_ALLOWED = LIST_JUMPS


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set; for the N reader: 1 N clear / 2 N set): from its successor in the trace."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    succ = ZSUCC if cons == ZREAD else SUCC[cons]
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


def native(ram, regs, pc, carry, stopfn, n_flag=False):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0) | (8 if n_flag else 0))
    out = dict(stop=None, bad=False)
    trace = []
    stray = []
    n = [0]

    def at(uc, p, size, user):
        if out['stop'] is not None:
            return
        n[0] += 1
        if trace and trace[-1] in JUMP_ALLOWED and p not in JUMP_ALLOWED[trace[-1]]:
            out['bad'] = True                       # a computed jump outside the list: the C++ checked jump-target error (error rows)
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
    """C after the block p entered with c (0 unknown / 1 clear / 2 set): the consumers keep it, every other C9 block leaves Unknown."""
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
BOUNDED = (0x9e, 0x9f, 0x9c, 0x76, 0x78, 0x88)


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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice(MRECS + (REC, CHILD)),
                a1=rng.choice((PARENT, CHILD)), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x22, 0x30, 0x40, 0x50, 0x80, 0x200, 0x800, 0xa02, 0xffff, 0x12345678,
                                 0x10000, 0x10001, 0x8000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 2, 0x10001, 0xffff0001, 0x28, 0x27, 0x12340000, 0x80000000))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 0x10000, 1, 0xffff, 0x12340000))
    if s in LIST_JUMPS:
        regs['a1'] = rng.choice(sorted(LIST_JUMPS[s]))
    if s in (0x1d08a, 0x1d096, 0x20a54, 0x20bd6, 0x20cf6, 0x20d62):
        regs['a0'] = rng.choice(MRECS)
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
    # the node links and pointers, the slot LONG 84, the bounded indices; the player nodes; the records (LONGs 4 / 8 / 18, WORDs 18 / 76), the record
    # LONG 8c(A6) with its BYTE 4 0..18
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0x9e, 1, rng.randrange(4))
    r.put(NODE + 0x9f, 1, rng.randrange(5))
    r.put(NODE + 0x9c, 1, rng.randrange(6))
    r.put(NODE + 0x76, 2, rng.randrange(4))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 0x100, 0x8000)))
    r.put(NODE + 0x88, 2, rng.choice((0, 0, 1, 2, 0x14, 0x8000, 0xffff)))
    r.put(REC + 4, 1, rng.randrange(19))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for m in MRECS + (REC,):
        for off in (0x4, 0x8, 0x18):
            r.put(m + off, 4, rand_val(rng, 4))
        r.put(m + 0x76, 2, rand_val(rng, 2))
    for i in range(0, 0x80, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # C5 1cb1a: LONG 22(A6) + sext(4 x WORD)
    if hint:
        regs.update(hint.get('regs', {}))
        for k, v in hint.get('regrec', {}).items():
            regs[k] = REC - 0x20 + v                      # the V1 spec's record: rec + 20 is A0 / A4 (REC here)
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
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


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the JMP (A1) list handlers and the RTS sentinel
ROUTED_EXITS = {0x28ae, 0x8ebe, 0x8ff4, 0xce02, 0x1aa3a, 0x1cab6, 0x1cabe, 0x1cb08, 0x1cb38, 0x1cd98, 0x1cec2, 0x1cfbe, 0x1d0a4, 0x1eb98, 0x1eba0, 0x1eeea,
                0x1f1d8, 0x1f2a4, 0x1f3ec, 0x1f538, 0x1f5d2, 0x1f5f2, 0x1f76e, 0x1f7a4, 0x1fa3c, 0x1fa68, 0x1fad2, 0x1fae8, 0x1fb2e, 0x201a2, 0x20738, 0x2092c,
                0x20efc, 0x21430, 0x21520, 0x2156a, 0x215e6, 0x21602, 0x21baa, 0x21bc6, 0x21c1c, 0x21e52, 0x21ffc, 0x221ca, 0x43ea4, 0x49214, 0x49274,
                0x4970a, 0x49fc6, 0x4bfc0, 0xea680}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x1f082, 0x20bfe, 0x22148, 0x22286, 0x223fa}
JUMP_TARGETS = set(t for v in LIST_JUMPS.values() for t in v if t not in STARTS_SET)
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_TARGETS - ROUTED_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p == ZREAD


def hints(s):
    """The V1 spec hint worlds (pc9.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def zread_hints():
    """The N reader 22180: BYTE 9d(A6) 0 / 1 / 7f / 80 / ff (the native SR N is set from its bit 7; Z / V are not read by the BLT)."""
    return [dict(a6off=[(0x9d, 1, v)]) for v in (0, 1, 0x7f, 0x80, 0xff, 0x81)] + [dict(a6off=[(0x9d, 1, 0x80)], mirror=True)]


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
            nflag = False
            if s == ZREAD:
                if hint is None:
                    continue
                nflag = (r.byte(regs['a6'] + 0x9d) & 0x80) != 0
            o = native(r.b, regs, s, 0, single_stop, nflag)
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 5 if s == ZREAD else 1, o)


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


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=REC,
             a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    if entry in (0x1ed0e, 0x1f112, 0x1f524):                     # 49fc6: LONG 26(A6) = 0 -> Set (else the interpreter reads ROM: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry == 0x1ec98:                                         # C2 1cb08 on the synthetic WORD table 1b764 with BYTE 9f 0..4
        r.put(NODE + 0x9f, 1, rng.randrange(5))
    if entry == 0x21ca4:                                         # 21bc6: CMPI.B #1,9e(A6); BCLR.B #4,a7(A6)
        r.put(NODE + 0x9e, 1, rng.choice((0, 1, 1, 2)))
        r.put(NODE + 0xa7, 1, rng.choice((0, 0x10, 0x30, 0xff)))
    if entry == 0x21cb2:                                         # 21baa: TST.B 9f(A6); synthetic BYTE (21ba6 + WORD 76) against BYTE a1(A6)
        r.put(NODE + 0x9f, 1, rng.choice((0, 0, 1)))
        r.put(NODE + 0xa1, 1, rng.choice((0, 1, 2, 5, 6, 0xff)))
    if entry in (0x21cd8, 0x21d2a, 0x22240, 0x2241c):            # 215e6 on the synthetic lists 21aee / 216c8: BYTE 9c
        r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 4, 5, 0xff)))
    if entry == 0x22174:                                         # the N chain 22174 -> 22180: BYTE 9d signed
        r.put(NODE + 0x9d, 1, rng.choice((0, 0x80, 0xff, 0x81)))
    return r, regs


CHAINS = []


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            if cp in LIST_JUMPS or SUCC[cp][1] in LIST_JUMPS:
                regs['a1'] = sorted(LIST_JUMPS[SUCC[cp][1]])[0] if SUCC[cp][1] in LIST_JUMPS else regs['a1']
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st) and len(tr) > 0)
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(ZSUCC if cons == ZREAD else SUCC[cons])
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
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c) if cons != ZREAD else 0, 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c9 jump target'
    flag = 'unsupported animation player c9 flag source'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c9 caller requires known carry', cp, stop=SUCC[cp][0])
    # the JMP (A1) (contract decision 2): A1 outside the list (compared as a LONG)
    for v in (0x21c22, 0x21e49, 0, 0x121602, 0x21e52, 0x1021e48, 0x21d62):
        err('jump-21ce4-%x' % v, 0x21ce4, jump, 0x21ce4, a1=v)
    for jp in (0x21d36, 0x2224c, 0x22428):
        for v in (0x21d60, 0x21e48, 0, 0x21603, 0x1021602):
            err('jump-%x-%x' % (jp, v), jp, jump, jp, a1=v)
    # the N source of 22180 (contract decision 3): BYTE 9d(A6) outside work RAM / fixed ROM
    for v in (0x200000 - 0x9d, 0x3c0000, 0x2ffff0, 0x300000 - 0x9d):
        err('n-a6-%x' % v, ZREAD, flag, ZREAD, a6=v)
    # fixed ROM outside the declared synthetic bytes: the record A0 of 1d08a / 1d096 / 20a54 / 20bd6, the table index of 20aa4 / 2218c
    err('rom-1d08a-1cf1e', 0x1d08a, rom, 0x1d08a, a0=0x1cf1e)
    err('rom-1d096-1cf3e', 0x1d096, rom, 0x1d096, a0=0x1cf3e)
    err('rom-20a54-a0', 0x20a54, rom, 0x20a54, a0=0x1d000)
    err('rom-20bd6-a0', 0x20bd6, rom, 0x20bd6, a0=0x1d000)
    err('rom-20aa4-76-8', 0x20aa4, rom, 0x20aa4, puts=((NODE + 0x76, 2, 8),))
    err('rom-21376-76-ffff', 0x21376, rom, 0x21376, puts=((NODE + 0x76, 2, 0xffff),))
    err('rom-2218c-index-13', 0x2218c, rom, 0x2218c, a0=0x220c0, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0x13)))   # 220c0 + 4c = 2210c (code)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1eca8', 0x1eca8, wodd, 0x1eca8, stop=0x1ecb8, a6=NODE + 1)
    err('odd-node-1f08a', 0x1f08a, wodd, 0x1f08a, stop=0x1f0ae, a6=NODE + 1)
    err('odd-node-1f492', 0x1f492, wodd, 0x1f492, stop=0x1f4b6, a6=NODE + 1)
    err('odd-node-20ac4', 0x20ac4, wodd, 0x20ac4, stop=0x20aec, a6=NODE + 1)
    err('odd-node-20b6e', 0x20b6e, wodd, 0x20b6e, stop=0x20b96, a6=NODE + 1)
    err('odd-node-20d0a', 0x20d0a, wodd, 0x20d0a, stop=0x20d36, a6=NODE + 1)
    err('odd-node-20a6e', 0x20a6e, odd, 0x20a6e, stop=0x20a80, a6=NODE + 1)
    err('odd-node-20aec', 0x20aec, odd, 0x20aec, stop=0x20b00, a6=NODE + 1)
    err('rom-write-22128', 0x22128, device, 0x22128, stop=0x22174, a6=0)          # 22128 has BYTE accesses only: the node in fixed ROM
    err('odd-node-2218c', 0x2218c, odd, 0x2218c, stop=0x1cabe, a6=NODE + 1)
    err('odd-a0-1d08a', 0x1d08a, odd, 0x1d08a, a0=MRECS[0] + 1)
    err('odd-a0-20a54', 0x20a54, odd, 0x20a54, a0=MRECS[0] + 1)
    err('odd-a0-20cf6', 0x20cf6, wodd, 0x20cf6, stop=0x49274, a0=CHILD + 1)
    err('odd-a0-20d62', 0x20d62, wodd, 0x20d62, stop=0x20d6e, a0=CHILD + 1)
    err('odd-stack-20a90', 0x20a90, odd, 0x20a90, a7=SP + 1)
    err('odd-stack-22284', 0x22284, odd, 0x22284, a7=SP + 1)
    err('odd-stack-22450', 0x22450, odd, 0x22450, a7=SP + 1)
    err('odd-stack-1d086', 0x1d086, odd, 0x1d086, stop=0x1cfbe, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM (A6 = 0 / 1b000)
    err('rom-write-20720', 0x20720, device, 0x20720, stop=0x20738, a6=0x1b170 - 0x42)   # WORD 42(A6) = the synthetic 1b170, SPL.B 5f(A6) writes ROM
    err('rom-write-1fb28', 0x1fb28, device, 0x1fb28, stop=0x1fb2e, a6=0x1b000)
    err('rom-write-21e48', 0x21e48, device, 0x21e48, stop=0x21e52, a6=0)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1f070-then-1f082', 0x1f070, unrouted, 0x1f082, puts=((NODE + 0x9d, 1, 1),))
    err('20bee-then-20bfe', 0x20bee, unrouted, 0x20bfe, puts=((NODE + 0x36, 4, 0xffffff00),))   # D2 = 0 - ffffff00 = 100: BPL
    err('22128-then-22148', 0x22128, unrouted, 0x22148, puts=((NODE + 0xa7, 1, 1),))
    err('221a2-then-22286', 0x221a2, unrouted, 0x22286, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 5)))
    err('21d3c-then-223fa', 0x21d3c, unrouted, 0x223fa, d0=1)
    err('20bc4-then-20bfe', 0x20bc4, unrouted, 0x20bfe, d0=0)                     # D0 bit 4 clear -> 20bee; LONG 36 = 0: D2 = 0, BPL
    err('20a6e-then-20a90', 0x20a6e, odd, 0x20a90, a7=SP + 1)
    err('20b00-then-20b28', 0x20b00, odd, 0x20b28, a7=SP + 1)
    err('22276-then-22284', 0x22276, odd, 0x22284, a7=SP + 1)
    err('22442-then-22450', 0x22442, odd, 0x22450, a7=SP + 1, d7=0x10000)
    err('2225a-then-2226c', 0x2225a, odd, 0x22272, a7=SP + 1, puts=((NODE + 0x7e, 1, 1),))


def main():
    rng = random.Random(0xC9C9)
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
    jstops = set(d['stop'] for d in singles if d['entry'] in LIST_JUMPS)
    print('list handlers reached by the JMP (A1) rows', sorted(hex(x) for x in jstops))


if __name__ == '__main__':
    main()
