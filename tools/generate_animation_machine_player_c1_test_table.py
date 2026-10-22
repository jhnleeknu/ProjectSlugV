"""Generates the native-oracle tables of engine/tests/animation_machine_player_c1_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
data areas only, never over code of the unit): the 8-BYTE slot table 4e4d2..4e4d9 (read by 4e58a / 4e5a6 / 4e5c2 / 4e5de / 4f3be as 4e4d2 + index and
4e4d6 + index) and the bank-window LONG 2001e4 (4f2e0, bank 200000).  A native run that reads any other fixed-ROM or banked byte is dropped (that is a
callee run or a table index beyond the 8 declared BYTEs), as is a run that lands inside the unit on a PC that is not a block start, or that takes an
exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 78(A6) := the player record
100cb8 for the slot blocks), A0 = 10e400 / 10ea00 (child), A1 / A2 = 10ea00 / 100cb8, A5 = 108000, seeded BYTE / WORD / LONG field edits (sign
boundaries included), seeded D0-D7 and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc1.py hint_worlds, converted to absolute addresses;
'mirror' puts the node at 1fe000, 'parent' / 'parent_mirror' the parent 10eb00 / 1feb00).  The Z readers 4e7da 4e7f2 4e842 are entered with the SR Z
equal to (BYTE -7699(A5) = 0) (contract decision 3).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, the TRAP 4e69a).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer (RAM-only producers): ca32 -> 4e808 (4e802), 289e -> 4e958 (4e94e) are kept when both C values
            occur; 48346 -> 1d21c (1d216) has only the routed Clear side (48368; the Set side runs into the C3 start 48350): its rows are kept as
            Clear-only chain rows (not in CHAINED).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 48368 (ANDI.B #fe,CCR; RTS) Clear.  4e808 leaves C Unknown (the CMP.B after its SCS.B).
Usage:  .venv/bin/python tools/generate_animation_machine_player_c1_test_table.py  (rewrites the generated section in place)
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
import pc1 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c1_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
SET_SET, CLEAR_SET, UNKNOWN_AFTER = set(B.SET_SET), set(B.CLEAR_SET), set(B.UNKNOWN_AFTER)
Z_SET = set(B.Z_RECOMPUTE)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC1, PARENT, SIBLING = 0x10ea00, 0x10eb00, 0x10ec00
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
TABLE = 0x4e4d2
TABLE_BYTES = bytes((0x01, 0x03, 0x00, 0x02, 0x03, 0x00, 0x0a, 0x01))   # synthetic: 4e4d2 + 0..7 (4e4d6 + 0..3 = 03 00 0a 01)
WINDOW = 0x2001e4                                   # the bank-window LONG of 4f2e0 (stored into 22(A6), never followed)
WINDOW_LONG = 0x0012abcd
ZADDR = (A5 + B.Z_ADDR) & 0xffffff                  # 100967: BYTE -7699(A5), the Z source of the readers


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(TABLE, TABLE_BYTES), (WINDOW, struct.pack('>I', WINDOW_LONG))]


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


# consumer -> (C clear successor, C set successor) in the plain world (BYTE 9a(A6) = 0: 4e808 SCS.B D0 then CMP.B 9a(A6),D0; BEQ.W 4e82a)
SUCC = {0x1d21c: (0x1d220, 0x1d222), 0x4e808: (0x4e82a, 0x4e812), 0x4e958: (0x4e8e6, 0x4e95a)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM and both C values occur
CHAIN_CANDIDATES = ((0x4e802, 0x4e808), (0x4e94e, 0x4e958))
CLEAR_ONLY_CHAINS = ((0x1d216, 0x1d21c),)


def scc_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (4e808 with BYTE 9a = 0)."""
    return 1 if o['stop'] == SUCC[cons][0] else 2


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
    z = 4 if pc in Z_SET and ram[(regs['a5'] + B.Z_ADDR) & 0xffff] == 0 else 0          # the Z of the ca50 TST.B (decision 3)
    c.reg_write(UC_REG['sr'], 0x2000 | z | (1 if carry == 2 else 0))
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
        c.emu_start(pc, 0xffffff, count=2000000)
    except unicorn.UcError:
        return None
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.bank != 0x200000:
        return None
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or m.ports:
        return None                                 # C1 writes no PVC port (a producer that does is dropped here)
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
    if p in UNKNOWN_AFTER:
        return 0
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


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'scc', 'abcd'):
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
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xb, 0xff, 0x100, 0x12340001, 0xffff, 0x8000, 0x10000, 0x10003))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((1, 0xffffffff, 0x101, 0x1ff, 0x12345601, 0x80, 0xff))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or (disp == 0x78 and s in B.SLOT_FAMILY)):
            continue                                    # (A6) callback LONG, the node links and the pointer fields are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links, the parent (LONG c(A6): 4f32e / 4f396 / 4f34a / 4f3b2) and the player record (LONG 78(A6) of the slot node)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(PARENT + 0x9c, 1, rng.choice((1, 1, 0, 2)))
    r.put(PARENT + 0xa1, 1, rand_val(rng, 1))
    r.put(PARENT + 0x98, 1, rng.choice((0, 1, 2, 3, 4, 5, 6, 7)))
    if s in B.SLOT_FAMILY:
        r.put(NODE + 0x78, 4, rng.choice((PLAYER1, PLAYER2)))
        r.put(PLAYER1, 4, rng.choice((0x270e, 0x270e, 0, 0x2b99c)))       # 289e: LONG (A0) = 270e -> C Clear
        r.put(PLAYER2, 4, rng.choice((0x270e, 0x1d1f4)))
    if rng.random() < 0.6:
        r.put(ZADDR, 1, rng.choice((0, 0, 1, 0x80, 0xff)))                # the Z source of 4e7da / 4e7f2 / 4e842
    if rng.random() < 0.6:
        r.put(A5 + 0x5d1e, 1, rng.choice((0, 1, 2, 4, 8, 3, 7, 0xb, 0xd, 0xe, 0xf0)))   # the slot bits (never all four: the 4e5d2 loop would not end)
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
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the TRAP site and the RTS sentinel
ALLOWED_STOPS = {0x289e, 0x28ae, 0x2a00, 0x2a0a, 0x2a28, 0x3670, 0x8d34, 0x8ebe, 0x8ff4, 0xca32, 0xca42, 0x16ed2, 0x1bd2e, 0x48398, 0x49be0, 0x49f8c,
                 0x49fc6, 0xb7a2e, 0xb7a48, 0xe62ec, STOP} | set(B.EXIT_STOPS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer


def hints(s):
    """The V1 spec hint worlds (pc1.hint_worlds) of the block; converted to absolute addresses by world()."""
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
                continue                                 # a loop back to its own block (4e596 / 4e5d2): a stop at the entry is a zero-step run
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


PATH_ENTRIES = (0x4e68e, 0x4e69c, 0x4e6a2, 0x4e6cc, 0x4e702, 0x4e732, 0x4e744, 0x4e7a4, 0x4e7ac, 0x4e7d4, 0x4e7e2, 0x4e7ec, 0x4e7fa, 0x4e812, 0x4e82c,
                0x4e83c, 0x4e84e, 0x4e854, 0x4e868, 0x4e874, 0x4e87e, 0x4e888, 0x4e894, 0x4e89e, 0x4e8b8, 0x4e8d6, 0x4e8f0, 0x4e8fc, 0x4e904, 0x4e90e,
                0x4e928, 0x4e940, 0x4e95a, 0x4e97e, 0x4f304, 0x4f32e, 0x4f342, 0x4f396, 0x4f3aa, 0x4f3be, 0x4f3d4, 0x4f406, 0x4f438, 0x4f46a, 0x4f4a2,
                0x1d204, 0x1d20c, 0x48346, 0x49bca, 0x4e0f6, 0x4e4da, 0x4e58a, 0x4e596, 0x4e5c2, 0x4e5d2, 0xca3a, 0xca50, 0xb7a28, 0x4e7da, 0x4e842)


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
    if entry == 0x4e802:                                         # ca32: CMPI.B #aa,-769c(A5): C = BYTE < aa (unsigned); BYTE 9a(A6) = 0
        r.put(A5 - 0x769c, 1, rng.choice((0, 0x7f, 0xa9, 0xaa, 0xab, 0xff)))
        r.put(NODE + 0x9a, 1, 0)
    if entry == 0x4e94e:                                         # 289e: CMPI.L #270e,(A0) with A0 = LONG 78(A6): equal -> C Clear, else ORI -> Set
        rec = rng.choice((PLAYER1, PLAYER2))
        r.put(NODE + 0x78, 4, rec)
        r.put(rec, 4, rng.choice((0x270e, 0x270f, 0, 0x8000270e)))
    if entry == 0x1d216:                                         # 48346: BYTE 5683 bit 1 clear -> 48368 (C Clear); set -> 48350 (C3, a stop)
        r.put(A5 + 0x5683, 1, rng.choice((0, 0xfd, 2, 0xff)))
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
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES + CLEAR_ONLY_CHAINS:
        clr, st = SUCC[cons]
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: (q in (clr, st) and len(tr) > 0 and cons in tr) or q in B.EXIT_STOPS)
            if o is None or cons not in o['trace']:
                continue
            c = scc_value(cons, o)
            if seen.get(c, 0) >= 3:
                continue
            seen[c] = seen.get(c, 0) + 1
            rows.append((k, r, regs, o, c))
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
            if (entry, cons) in CLEAR_ONLY_CHAINS and seen.get(1, 0) >= 3:
                break
        print('chain %x -> %x: %s' % (entry, cons, dict(seen)))
        if (entry, cons) in CLEAR_ONLY_CHAINS:
            for k, r, regs, o, c in rows:
                assert c == 1
                row('chain1-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)
            continue
        if set(seen) != {1, 2}:
            continue                                             # one C value never occurred: declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=PLAYER1, a3=0, a4=0, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    flag = 'unsupported animation player c1 flag source'
    unrouted = 'unsupported animation machine PC'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c1 caller requires known carry', cp, stop=SUCC[cp][0])
    # the Z source outside work RAM (decision 3): A5 = 8000 (BYTE 967 of the fixed ROM) / 400000 (3f8967)
    for zp in sorted(Z_SET):
        err('zsource-rom-%x' % zp, zp, flag, zp, a5=0x8000)
        err('zsource-io-%x' % zp, zp, flag, zp, a5=0x400000)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-4e68e', 0x4e68e, odd, 0x4e68e, stop=0x4e69c, a6=NODE + 1)
    err('odd-node-4e6a2', 0x4e6a2, wodd, 0x4e6a2, stop=0x4e6f2, a6=NODE + 1)
    err('odd-node-4f32e', 0x4f32e, odd, 0x4f32e, stop=0x4f342, a6=NODE + 1)
    err('odd-stack-1d1f4', 0x1d1f4, odd, 0x1d1f4, stop=0x2a0a, a7=SP + 1)
    err('odd-stack-ca3a', 0xca3a, odd, 0xca3a, a7=SP + 1)
    err('odd-a0-1d204', 0x1d204, wodd, 0x1d204, stop=0x1d20c, a0=NODE + 1)
    err('odd-a0-4e84e', 0x4e84e, odd, 0x4e84e, stop=0x4e854, a0=NODE + 1)
    err('odd-a0-4e0f6', 0x4e0f6, wodd, 0x4e0f6, a5=A5 + 1)
    # the TRAP #15 4e69a (WORD 76 >= 2): the next dispatch fails at the TRAP site
    err('trap-4e68e-2', 0x4e68e, unrouted, 0x4e69a, puts=((NODE + 0x76, 2, 2),))
    err('trap-4e68e-ffff', 0x4e68e, unrouted, 0x4e69a, puts=((NODE + 0x76, 2, 0xffff),))
    # the slot table outside the 8 declared synthetic BYTEs: index 8 (4e4da, a code BYTE of the unit) is no declared physical byte here
    err('table-4e58a-8', 0x4e58a, 'missing or ambiguous physical program bus ROM byte', 0x4e58a, d0=8)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('4e69c-then-4e6f2', 0x4e69c, odd, 0x4e6f2, stop=0xe62ec, a7=SP + 1)
    err('4e58a-then-4e5a6', 0x4e58a, odd, 0x4e5a6, a7=SP + 1)
    err('4e7e6-then-4e7ec', 0x4e7e6, odd, 0x4e7ec, stop=0xca50, a7=SP + 1)
    err('48346-then-48368', 0x48346, odd, 0x48368, a7=SP + 1)
    err('4f3e2-then-4f400', 0x4f3e2, odd, 0x4f400, stop=0x8d34, a7=SP + 1)
    err('4e7d4-then-4e7da', 0x4e7d4, flag, 0x4e7da, a5=0x4e4d2 + 0x7699)   # ca50 tests the synthetic ROM BYTE 4e4d2, then 4e7da rejects that source
    err('odd-stack-4e7a4', 0x4e7a4, odd, 0x4e7a4, stop=0x4e58a, a7=SP + 1)


def main():
    rng = random.Random(0xC1C1)
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
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
