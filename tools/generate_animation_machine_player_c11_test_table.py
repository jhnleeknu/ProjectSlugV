"""Generates the native-oracle tables of engine/tests/animation_machine_player_c11_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit, every one differs from the original): the BYTE table 1c1c4 (1cb76), the WORD
record 1bcde (21950 -> 1cb76), the WORD tables 4409e..4421e (the MULS of 1e5ba from 4411e / 4419e), 1e776 / 1e77c (1e744), 49c00 (49bf2) and 4e396 (4ecec), the LONG table
219f6 (21a42; RAM record pointers), the BYTE table e8c22 (e8c40), the bank-window LONG 200088 (1e67a; bank 200000: physical offset = CPU address), the
(handler LONG, key WORD) lists 21930 / 216c8 (C3 215e6 for the producer chains of 21968 / 21a7e: the ROM handlers with other keys) and the LONG tables
1d468 / 1d4b8 (C6 1d510 / 1d514 for the producer chains of 1d8fa / 1db9c).  A native run that reads any other fixed-ROM or banked byte is dropped, as
is a run that lands inside the unit on a PC that is not a block start, a JMP (A1) 21a82 to a PC outside its ROM list (the C++ checked jump-target
error), a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 8c(A6) := the record 10ea00 (BYTEs 3 / 4 bounded), LONG 84(A6) := a routed slot-84 value, WORDs 76 / 78 small, BYTE 9c small), A0 / A3 / A4 the
record 10ea00 or the child 10e400, A1 a handler of the ROM list of the JMP (A1), A2 the parent / child node, A5 = 108000 (BYTE 7d82(A5) mostly 0),
seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 (D7 the appearance types of 1d3e0, D1 small) and the hint worlds of the V1
spec (tools/unit_fixture_specs/pc11.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' / 'a6rec'
address the record 10ea00 (rec + 20 = A0 / A1 / A4 / LONG 8c / LONG c), 'a5off' an A5 field, 'writes' a work RAM offset).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, the JMP
            (A1) list handler, a later-unit stop).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, list handler, the RTS sentinel), a consumer or the Z reader.
  single 2  a consumer entered through its real producer (and the Z reader 4eb84 through 4eb7a / 4a974): kept when both outcomes occur; a run that
            passes 290e (the 28ae failure inside 2986: the C++ 2986 executor's caller-X checked error, C7 decision 6) is not a chain world.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the Z reader 4eb84 entered directly: the native SR Z = the recomputed Z (BYTE (A0) = 0, A0 one of 100004 100005 10fdb0 10fdb1); the C++
            re-reads it (contract decision 3).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: every block leaves Unknown (no producer, no pass block); the 9 consumers keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c11_test_table.py  (rewrites the generated section in place)
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
import pc11 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c11_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREADS = (0x4eb84,)                                 # the Z reader (BNE on the TST.B (A0) that ends 4a974)
assert tuple(B.Z_READERS) == ZREADS
ZSET = set(ZREADS)
Z_A0 = (0x100004, 0x100005, 0x10fdb0, 0x10fdb1)     # the BYTEs 4a974 tests
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, LTAB = 0x10ea00, 0x10eb00, 0x10e700
PLAYERS = (0x100cb8, 0x100da8)
LIST_21930_KEYS = (3, 5)                            # synthetic keys of the list 21930 (ROM: 0 a); the handlers are the ROM handlers 21602 2197e
LIST_216C8_KEYS = (2,)                              # synthetic key of the list 216c8 (ROM: 0)
LIST_JUMPS = dict((k, set(v)) for k, v in B.LIST_JUMPS.items())
RECS = (REC, CHILD, PARENT, REC + 0x40)             # RAM records of the synthetic LONG table 219f6


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def plist(handlers, keys):
    out = b''
    for h, k in zip(handlers, keys):
        out += struct.pack('>IH', h, k)
    return out + struct.pack('>I', 0)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1bcde, words([0x10 * k + 3 for k in range(16)])),                              # 21950: the WORD record of 1cb76 (A0 = 1bcde)
            (0x1c1c4, bytes(((k * 5 + 1) & 7) if k != 31 else 0x90 for k in range(32))),      # 1cb76: BYTE (1c1c4 + BYTE 4 of the record); 31: 90
            (0x1d468, longs([0, 0x10e480, 0, 0x10e4c0] * 5)),                                 # C6 1d510 -> 1d54c: LONG (1d468 + 4 x D1.W)
            (0x1d4b8, longs([0x10e4c0, 0, 0, 0x10e480, 0] * 4)),                              # 1d508 -> C6 1d54c: LONG (1d4b8 + 4 x D1.W)
            (0x1e776, words((0x0102, 0xfe03, 0x8004) + tuple((0x111 * k) ^ 0x8000 for k in range(13)))),   # 1e744: WORDs 1e776 / 1e77c
            (0x216c8, plist(B.LIST_216C8, LIST_216C8_KEYS)),                                  # C3 215e6 from 21a76
            (0x21930, plist((0x21602, 0x2197e), LIST_21930_KEYS)),                            # C3 215e6 from 21960
            (0x219f6, longs([RECS[k % 4] for k in range(19)])),                               # 21a42: LONG (219f6 + 4 x BYTE 4 of the record)
            (0x4409e, words([0x8000 if k in (6, 70) else ((0x123 * k) & 0xffff) ^ (0x8000 if k & 1 else 0) for k in range(-64, 128)])),   # 1e5ba: MULS WORDs
            # (4411e / 4419e + 2 x D1.W, k = (address - 4411e) / 2 from -40 on so that a negative D1.W reads both tables; k 6 / 70: 8000)
            (0x49c00, words((0x0003, 0x8000, 0x7fff, 0xffff, 0, 1, 0x40, 0x41, 0x8001, 0xfff0, 0x10, 0x20, 0x3f, 0xc000, 0x2a, 0x7)),),
            (0x4e396, words([0x4b00 + 7 * k for k in range(16)])),                            # 4ecec: WORD (4e396 + 2 x BYTE (A0))
            (0xe8c22, bytes((0x80 + 3 * k) & 0xff for k in range(24))),                       # e8c40: BYTE (e8c22 + BYTE 3(A0))
            (0x200088, longs((0x00fedcba,)))]                                                 # 1e67a (bank window)


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


# consumer -> (C clear successor, C set successor); the Z reader -> (Z clear successor, Z set successor)
SUCC = {0x1d5ce: (0x1d5d2, 0x1d5e0), 0x1d606: (0x1d60a, 0x1d618), 0x1d770: (0x1d776, 0x1d774), 0x1d8fa: (0x1d902, 0x1d8fe), 0x1db9c: (0x1dba0, 0x1dbc6),
        0x1e5ec: (0x1e604, 0x1e5f0), 0x21968: (0x2196e, 0x2196c), 0x21a7e: (0x21a84, 0x21a82), 0xe8c7c: (0xe8ca2, 0xe8c84)}
assert set(SUCC) == CONS_SET
ZSUCC = {0x4eb84: (0x4eba8, 0x4eb88)}
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both outcomes occur
CHAIN_CANDIDATES = tuple(B.CHAINS)
JUMP_ALLOWED = dict(LIST_JUMPS)


def cons_value(cons, o):
    """The flag a consumer read (1 clear / 2 set; for the Z reader: 1 Z clear / 2 Z set): from its successor in the trace."""
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
    """C after the block p entered with c (0 unknown / 1 clear / 2 set): the consumers keep it, every other C11 block leaves Unknown."""
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

VB = tuple(B.VB)
VW = tuple(B.VW)
VL = tuple(B.VL)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = set(B.POINTERS)
BOUNDED = (0x9c, 0x76, 0x78, 0x9e, 0x9f, 0xa0, 0xa9)


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
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x40, 0x80, 0x800, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000, 0xfff0))
    if rng.random() < 0.6:
        regs['d1'] = rng.choice((0, 1, 2, 7, 9, 0x109, 0x3f, 0x10001, 0xffff0001, 0x8000, 0x12340000, 0x14, 0x13))
    if rng.random() < 0.5:
        regs['d7'] = rng.choice((0xf, 0x10, 0xc, 0xd, 0x11, 0x19, 0x1a, 0x1b, 0x18, 0x14, 0x16, 0x15, 0x10016, 0, 0x17, 0xffff, 1, 0x100))
    if s in LIST_JUMPS:
        regs['a1'] = rng.choice(sorted(LIST_JUMPS[s]))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or disp in BOUNDED):
            continue                                    # (A6) callback LONG, the node links, the pointer fields and the bounded indices are declared below
        if reg in (0, 4) and disp in (3, 4):
            continue                                    # the bounded record BYTEs 3 / 4
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links and pointers, the slot LONG 84, the bounded indices; the player nodes; the record LONG 8c(A6) with its BYTEs 3 / 4; the parent
    r.put(NODE + 0xc, 4, rng.choice((PARENT, PARENT, CHILD)))
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 5, 0xa)))
    r.put(NODE + 0x76, 2, rng.choice((0, 0, 1, 1, 2, 3)))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 0x100)))
    r.put(REC + 3, 1, rng.randrange(24))
    r.put(REC + 4, 1, rng.randrange(19))
    for p in (PARENT, CHILD):
        r.put(p + 0x7c, 1, rng.randrange(3))
        r.put(p + 0x76, 2, rng.randrange(4))
        r.put(p + 0x9e, 1, rng.choice((3, 3, 0, 1)))
        r.put(p + 0xa7, 1, rng.choice((0, 0, 0x40, 0x80, 0x3f)))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for i in range(0, 0x80, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # 1cb76: LONG 22(A6) + sext(4 x WORD)
    if rng.random() < 0.8:
        r.put(A5 + 0x7d82, 1, 0)                                                        # home mode (4a90e / 4eb72)
    if rng.random() < 0.9:
        r.put(0x10fd82, 1, 0)                                                           # 4a974 without the BIOS call
    if hint:
        regs.update(hint.get('regs', {}))
        for k, v in hint.get('regrec', {}).items():
            regs[k] = REC - 0x20 + v                      # the V1 spec's record: rec + 20 is A0 / A1 / A4 (REC here)
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


# the stops a success row may end at outside the unit: the routed exits, the JMP (A1) list handler, the later-unit stops and the RTS sentinel
ROUTED_EXITS = {0xb0c, 0x28ae, 0x2986, 0x2a00, 0x35f0, 0x8ebe, 0xca70, 0xce02, 0x1cb38, 0x1cd98, 0x1d1d0, 0x1d510, 0x1d514, 0x1d582, 0x1d698, 0x1d90a,
                0x1dbc6, 0x1ddc8, 0x1ddfc, 0x1e60a, 0x1e65c, 0x1fae8, 0x201a2, 0x2156a, 0x215e6, 0x43e08, 0x43e34, 0x481b2, 0x481de, 0x48210, 0x48296,
                0x4836e, 0x49214, 0x49260, 0x49290, 0x49bca, 0x49be0, 0x49c20, 0x49c38, 0x49f8c, 0x49f96, 0x49fc6, 0x4a974, 0x4a9ca, 0x4be82, 0x4c0ac,
                0x4d17c, 0x4e4da, 0x4e564, 0x4ed3c, 0xe8ad0, 0xe8b6e, 0xea626}
UNIT_EXITS = set(B.UNIT_EXITS)
JUMP_TARGETS = set(t for v in LIST_JUMPS.values() for t in v if t not in STARTS_SET)
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_TARGETS - ROUTED_EXITS)

def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p in ZSET

def hints(s):
    """The V1 spec hint worlds (pc11.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def zread_hints(s):
    """The Z reader 4eb84: A0 one of the four BYTEs 4a974 tests, the BYTE 0 / not 0 (the native SR Z = BYTE (A0) = 0)."""
    out = []
    for a0 in Z_A0:
        for v in (0, 1, 0x80, 0xff):
            out.append(dict(regs=dict(a0=a0), writes=[(a0 - 0x100000, 1, v), ((a0 - 0x100000) ^ 1, 1, 0x55)]))
    return out


def zflag(s, r, regs):
    """The Z flag the predecessor leaves for the Z reader (the SR bit 2 of the native entry): BYTE (A0) = 0."""
    return r.byte(regs['a0']) == 0

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
    if entry in (0x1d5c4, 0x1d5fc):                              # 49c38: TST.L 5734(A5) + 4 x (WORD 78(A6) & 1)
        pl = rng.choice((0, 1))
        r.put(NODE + 0x78, 2, pl)
        r.put(A5 + 0x5734 + 4 * pl, 4, rng.choice((0, 0, 0x10e400, 0x80000000, 1)))
    if entry == 0x1d76a:                                         # 4836e: BTST.B #2,5683(A5)
        r.put(A5 + 0x5683, 1, rng.choice((0, 4, 0xfb, 0xff)))
    if entry in (0x1d8f6, 0x1db98):                              # 1d514: CMPI.W #14,D1 (>= 14 Clear; else 481b2 / 1aa3a / the synthetic LONG tables)
        regs['d1'] = rng.choice((0x14, 0x15, 0xffff, 0, 1, 3, 9, 0x13, 0x10014, 2))
    if entry in (0x21960, 0x21a76):                              # 215e6 on the synthetic lists 21930 / 216c8: BYTE 9c
        r.put(NODE + 0x9c, 1, rng.choice((0, 2, 3, 5, 0xa, 0xff)))
    if entry == 0xe8c40:                                         # 2986 from e8c40 (A0 = the record, BYTE 3 the synthetic e8c22 index)
        regs['a0'] = REC
        r.put(REC + 3, 1, rng.randrange(24))
    if entry == 0x4eb7a:                                         # 4a974: BYTE 10fd82 = 0, BYTEs 100003 / 100004 / 100005 (player = WORD 76(A6))
        r.put(0x10fd82, 1, 0)
        r.put(NODE + 0x76, 2, rng.choice((0, 1)))
        r.put(0x100003, 1, rng.choice((0, 0xff)))
        r.put(0x100004, 1, rng.choice((0, 1, 0x80)))
        r.put(0x100005, 1, rng.choice((0, 2)))
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
            if o is None or cons not in o['trace'] or o['stop'] not in succ or 0x290e in o['trace']:
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
    jump = 'unsupported animation player c11 jump target'
    flag = 'unsupported animation player c11 flag source'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c11 caller requires known carry', cp, stop=SUCC[cp][0])
    # the JMP (A1) 21a82 (contract decision 2): A1 outside the list 216c8 (compared as a LONG)
    for v in (0x21d60, 0x21e48, 0, 0x21603, 0x1021602, 0x2197e, 0x21600):
        err('jump-21a82-%x' % v, 0x21a82, jump, 0x21a82, a1=v)
    # the Z source of 4eb84 (contract decision 3): A0 outside the four BYTEs of 4a974
    for v in (0x100003, 0x100006, 0x10fdaf, 0x10fdb2, 0x10e000, 0x200004, 0x1100004, 0):
        err('z-4eb84-a0-%x' % v, 0x4eb84, flag, 0x4eb84, a0=v)
    # fixed ROM / bank outside the declared synthetic bytes: the BYTE table 1c1c4 (record BYTE 4 = 20 / ff), the LONG table 219f6 (BYTE 4 = 13 / 80), the
    # BYTE table e8c22 (BYTE 3 = 18), the WORD table 4e396 (BYTE (A0) = 10), the MULS tables (D1.W = 40 / c0 / ff00: 4419e + 80 / 180 / -200), the WORD tables 1e776 / 1e77c
    # (BYTE 7c = 10), the d00034 credit BYTE (MVS: BYTE 7d82(A5) set, 7e80(A5) clear: a device address
    # of the program bus)
    err('rom-1cb76-b4-20', 0x1cb76, rom, 0x1cb76, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0x20),))
    err('rom-1cb76-b4-ff', 0x1cb76, rom, 0x1cb76, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0xff),))
    err('rom-21a42-b4-13', 0x21a42, rom, 0x21a42, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0x13),))
    err('rom-21a42-b4-80', 0x21a42, rom, 0x21a42, puts=((NODE + 0x8c, 4, REC), (REC + 4, 1, 0x80),))
    err('rom-e8c40-b3-18', 0xe8c40, rom, 0xe8c40, puts=((REC + 3, 1, 0x18),))
    err('rom-4ecec-10', 0x4ecec, rom, 0x4ecec, puts=((REC, 1, 0x10),))
    err('rom-1e5ba-d1-40', 0x1e5ba, rom, 0x1e5ba, d1=0x40)
    err('rom-1e5ba-d1-ff00', 0x1e5ba, rom, 0x1e5ba, d1=0xff00)
    err('rom-1e5ba-d1-c0', 0x1e5ba, rom, 0x1e5ba, d1=0xc0)
    err('rom-1e744-7c-10', 0x1e744, rom, 0x1e744, puts=((REC + 0x7c, 1, 0x10),))
    err('mvs-4a90e-then-4a93e', 0x4a90e, 'unsupported program bus device address', 0x4a93e, puts=((A5 + 0x7d82, 1, 1),))
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-a5-ca64', 0xca64, wodd, 0xca64, a5=A5 + 1)
    err('odd-node-1d9b8', 0x1d9b8, odd, 0x1d9b8, stop=0x1d9cc, a6=NODE + 1)
    err('odd-node-1e67a', 0x1e67a, wodd, 0x1e67a, stop=0x49290, a6=NODE + 1)
    err('odd-node-1e8f4', 0x1e8f4, wodd, 0x1e8f4, stop=0x1e918, a6=NODE + 1)
    err('odd-node-1e5d8', 0x1e5d8, wodd, 0x1e5d8, stop=0x4c2c4, a6=NODE + 1)
    err('odd-node-4ebe2', 0x4ebe2, odd, 0x4ebe2, stop=0x4ebf4, a6=NODE + 1)
    err('odd-node-21a5e', 0x21a5e, wodd, 0x21a5e, stop=0x21a76, a6=NODE + 1)
    err('odd-a0-1da04', 0x1da04, wodd, 0x1da04, stop=0x49260, a0=CHILD + 1)
    err('odd-a0-e8c84', 0xe8c84, wodd, 0xe8c84, stop=0x49214, a0=CHILD + 1)
    err('odd-a0-4ec6a', 0x4ec6a, odd, 0x4ec6a, stop=0x4ec80, a0=REC + 1)
    err('odd-stack-1e606', 0x1e606, odd, 0x1e606, a7=SP + 1)
    err('odd-stack-4ed34', 0x4ed34, odd, 0x4ed34, a7=SP + 1)
    err('odd-stack-e8cbc', 0xe8cbc, odd, 0xe8cbc, a7=SP + 1)
    err('odd-stack-e8c7c', 0xe8c7c, odd, 0xe8c7c, stop=0xe8ca2, carry=1, a7=SP + 1)
    err('odd-stack-e8c3a', 0xe8c3a, odd, 0xe8c3a, stop=0xe8ad0, a7=SP + 1)
    err('odd-stack-3fee2', 0x3fee2, odd, 0x3fee2, stop=0x40a5a, a7=SP + 1)
    err('odd-stack-1a952', 0x1a952, odd, 0x1a952, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-1e8f4', 0x1e8f4, device, 0x1e8f4, stop=0x1e918, a6=0x1b000)
    err('rom-write-4ed34', 0x4ed34, device, 0x4ed34, a6=0x1b000)
    err('rom-write-ca6a', 0xca6a, device, 0xca6a, a5=0x80000)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1d3e0-then-1d746', 0x1d3e0, odd, 0x1d746, a7=SP + 1, d7=0x16)
    err('1d3e0-then-1d722', 0x1d3e0, odd, 0x1d722, a5=A5 + 1, d7=0x14)
    err('4ebf4-then-4ec32', 0x4ebf4, odd, 0x4ec32, a7=SP + 1, d0=2)
    err('1db7c-then-1db84', 0x1db7c, odd, 0x1db84, a7=SP + 1, puts=((NODE + 0x88, 2, 5),))
    err('1e600-then-1e606', 0x1e600, odd, 0x1e606, a7=SP + 1)
    err('21a88-then-21a98', 0x21a88, odd, 0x21a98, a7=SP + 1)
    err('4a90e-then-4a93e', 0x4a90e, odd, 0x4a93e, a7=SP + 1)
    err('1e8f4-then-1e918', 0x1e8f4, odd, 0x1e918, a7=SP + 1)
    err('1e6b6-then-1e6c0', 0x1e6b6, odd, 0x1e6c0, puts=((NODE + 0xc, 4, CHILD + 1),))

def main():
    rng = random.Random(0xC11C)
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
    print('list handlers reached by the computed-jump rows', sorted(hex(x) for x in jstops))


if __name__ == '__main__':
    main()
