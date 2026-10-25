"""Generates the native-oracle tables of engine/tests/animation_machine_select_e2_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code, every one differs from the original): the default rank table e6322..e637a (read only
through a negative index), the rank text table e637a..e63d2 (11 LONGs and the 4-byte texts behind them), the character table e6e06..e6e28 (32 characters, the end mark 7f, 00), the default name e6e28, the replacement name
e6e2c, the cursor text e6e30, the bad-name list e6e32..e6e5e (LONGs, 0-terminated) and its 4-byte names e6e5e..e6e86.  A native run that reads any
other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a PC that is not a block start, a run that writes a device
port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 7a(A6) := a name buffer 10de18 /
10de20 / the record 10ea00 with three characters and the score LONG in front, WORD 76 the player 0 / 1 mostly, WORD 80 / 82 the cursor in range
mostly), the records 10e900 / 10e940 / 10e980 / 10e9c0 / 10ea00, A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included),
seeded D0-D7 and the hint worlds of the V1 spec (tools/unit_fixture_specs/se2.py hint_worlds, converted to absolute addresses; 'mirror' puts the node
at 1fe000, 'rec' / 'regrec' address the record 10ea00 (rec + 20 = A0), 'writes' a work RAM offset).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            TRAP #15 boundary, the RTS sentinel).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer: kept when both outcomes occur and the producer reads RAM / declared bytes.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 3 consumers keep the incoming C, the producers e640a / e6c44 / e6c68 leave Set, e6410 / e6c90 Clear, every other block Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_select_e2_test_table.py  (rewrites the generated section in place)
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
import se2 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_select_e2_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
PASS_SET = set(B.PASS_SET)
CLEAR_SET = set(B.CLEAR_SET)
SET_SET = set(B.SET_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT = 0x10ea00, 0x10eb00
MRECS = (0x10e900, 0x10e940, 0x10e980, 0x10e9c0)
NAMEBUFS = (0x10de18, 0x10de20, REC)               # the name buffers (LONG 7a(A6)): the two players' and a record
JUMP_TARGETS = {}
READERS = ()
TRAPS = tuple(B.TRAPS)


def longs(vals):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (the original bytes differ)."""
    # e6322: the 11 records of the default rank table (LONG, 4-byte name; read by E2 only through a negative index: e6a6a with e6496 = -1 reads the
    # LONG e6372, a WORD 82 near f51c reaches e6322 from e6e06) as LONGs that point into the texts and 4 text bytes each; e637a: 11 rank text LONGs
    # (permuted: entry k -> text (3 k) mod 11) and the 4-byte texts e63a6 + 4 j
    table = b''.join(longs((0xe63a6 + 4 * ((5 * k + 1) % 11),)) + bytes((0x44, 0x30 + k, 0x61 + k, 0x7f if k == 3 else 0x2e)) for k in range(11))
    ranks = table + longs(0xe63a6 + 4 * ((3 * k) % 11) for k in range(11)) + b''.join(bytes((0x52, 0x30 + j, 0x80 | j, 0x2e)) for j in range(11))
    # e6e06: the characters (index 0 '-', 1..1a 'Z'..'A', 1b..1e '#$%+', 1f the end mark 7f, 20 the terminator 00), e6e27 00, the default name
    # e6e28 'Q? ', the replacement e6e2c 'XYZ', the cursor text e6e30 (5f 00)
    chars = bytes([0x2d] + list(range(0x5a, 0x40, -1)) + [0x23, 0x24, 0x25, 0x2b, 0x7f, 0x00, 0x00])
    names = b'Q? \x00XYZ\x00\x5f\x00'
    # e6e32: the bad-name list (4 LONGs, 0, then filler never read) and its names e6e5e..e6e86
    bad = longs((0xe6e5e, 0xe6e6a, 0xe6e62, 0xe6e66, 0)) + b'\xee' * 24
    badnames = b'QWE\x00RTY\x00\x7f\x7f\x7f\x00UIO\x00' + b'\xdd' * 24
    return [(0xe6322, ranks), (0xe6e06, chars + names + bad + badnames)]


SYN = synthetic()
assert SYN[1][0] + len(SYN[1][1]) == 0xe6e86 and SYN[0][0] + len(SYN[0][1]) == 0xe63d2 and len(SYN[0][1]) == 0xb0


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
SUCC = {0xe69c6: (0xe69cc, 0xe69ca), 0xe69e8: (0xe69ec, 0xe6b24), 0xe6b64: (0xe6b78, 0xe6b68)}
assert set(SUCC) == CONS_SET
RSUCC = {}
CHAIN_CANDIDATES = tuple(B.CHAINS)


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor in the trace."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    succ = SUCC[cons]
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

    def word(self, a):
        return (self.b[a & 0xffff] << 8) | self.b[(a + 1) & 0xffff]


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
        if trace and trace[-1] in JUMP_TARGETS and p not in JUMP_TARGETS[trace[-1]]:
            out['bad'] = True                       # the computed jump leaves its table: the C++ checked jump-target error (error rows)
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
    sr = None
    try:
        # Unicorn evaluates the M68000 condition codes lazily: MOVE SR,D0 on a scratch page forces the evaluation (the C of a returned producer).
        c.mem_map(0x800000, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE | unicorn.UC_PROT_EXEC)
        c.mem_write(0x800000, b'\x40\xc0\x4e\x71')
        d0 = c.reg_read(UC_REG['d0'])
        c.emu_start(0x800000, 0x800002, count=1)
        sr = c.reg_read(UC_REG['d0']) & 0xffff
        c.reg_write(UC_REG['d0'], d0)
    except unicorn.UcError:
        return None
    return dict(stop=out['stop'], trace=trace, regs=m.regs(), ram=m.ram(), sr=sr)


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
BOUNDED = (0x76, 0x77, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83)


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
                a1=rng.choice((PARENT, CHILD, REC)), a2=rng.choice((PARENT, CHILD)), a3=rng.choice(MRECS + (REC,)), a4=rng.choice((REC, 0xe6e06, 0xe6e32)),
                a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xc, 0x10, 0x20, 0x30, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340001,
                                 0xffffffff, 0xfffe, 0x10001))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 1, 2, 3, 4, 0x24, 0x28, 0x100, 0x7fff, 0x8000, 0xffff, 0x12340003, 0xc000))
    if rng.random() < 0.3:
        regs['d6'] = rng.choice((0, 1, 0x1f, 0x20, 0x10000))
    if rng.random() < 0.3:
        regs['d5'] = rng.choice((0, 1, 2, 3, 0x10002, 0xffff))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or (disp in BOUNDED and rng.random() < 0.9)):
            continue                                    # (A6) callback LONG, the node links, the name buffer, the player and the cursor are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the parent link, the name buffer (three characters of the synthetic table mostly, the score LONG in front), the player, the cursor, the rank
    r.put(NODE + 0xc, 4, PARENT)
    name = rng.choice(NAMEBUFS)
    r.put(NODE + 0x7a, 4, name)
    table = SYN[1][1]
    for k in range(3):
        r.put(name + k, 1, table[rng.randrange(0x21)] if rng.random() < 0.85 else rng.choice((0x41, 0x61, 0x7f, 0, rng.getrandbits(8))))
    r.put(name + 3, 1, 0)
    r.put(name - 4, 4, rng.choice((0, 0x100, 0x99999, 0xffffffff, rng.getrandbits(32))))
    if rng.random() < 0.95:
        r.put(NODE + 0x76, 2, rng.choice((0, 0, 1, 1, 2, 0xffff, 0x8000)))
    if rng.random() < 0.9:
        r.put(NODE + 0x80, 2, rng.choice((0, 1, 2, 3, 3, 4, 0xffff)))
    if rng.random() < 0.9:
        r.put(NODE + 0x82, 2, rng.randrange(0x21) if rng.random() < 0.85 else rng.choice((0xffff, 0x21, 0x7fff)))
    r.put(NODE + 0x7e, 2, rng.randrange(0xb))
    r.put(A5 + 0x5683, 1, rng.choice((0, 4, 0xfb, 0xff)))           # 4836e: BTST #2,5683(A5)
    for off in (0x4ca8, 0x4cab, 0x4cac, 0x4cae, 0x4cb1, 0x4cb2):        # the player records / new-press BYTEs (-3358 .. -334e(A5))
        r.put(0x100000 + off, 1, rng.choice((0, 0x10, 0x20, 0x30, 0x08, 0x04, 0x0c, 0xff)))
    for m in MRECS + (REC,):
        for off in (0, 2, 4, 6):
            r.put(m + off, 2, rand_val(rng, 2))
    if hint:
        regs.update(hint.get('regs', {}))
        for k, v in hint.get('regrec', {}).items():
            regs[k] = REC - 0x20 + v                      # the V1 spec's record: rec + 20 is A0 (REC here)
        for k, v in hint.get('rega5', {}).items():
            regs[k] = A5 + v                              # an A5 field
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


# the stops a success row may end at outside the unit: the routed exits, the TRAP #15 boundaries e6d92 / e6dd0 and the RTS sentinel
ROUTED_EXITS = {0x2a00, 0x35a2, 0x3af8, 0x4836e, 0xe63ec, 0xe6496, 0xe84c8}
UNIT_EXITS = set(TRAPS)
assert UNIT_EXITS == {0xe6d92, 0xe6dd0} and not B.UNIT_EXITS
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p in READERS


def hints(s):
    """The V1 spec hint worlds (se2.hint_worlds) of the block, converted to absolute addresses by world()."""
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
            if ((nxt in CONS_SET or nxt in READERS) and s not in CLEAR_SET and s not in SET_SET and s not in B.DATA_SET) or \
               (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 5 if s in READERS else 1, o)


PATH_ENTRIES = tuple(s for s in STARTS if s not in CONS_SET and s not in READERS)


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
            if any(p in CONS_SET or p in READERS for p in ex) or not allowed(o['stop']) or o['stop'] == s:
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
             a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    table = SYN[1][1]
    if entry == 0xe69c0:                                         # 4836e: BTST #2,5683(A5): set -> Clear, clear -> Set
        r.put(A5 + 0x5683, 1, rng.choice((0, 4, 0xfb, 0xff)))
    if entry == 0xe69e0:                                         # e6c26: the end mark (WORD 82 = 1f) -> e6c44 Set, WORD 80 3 -> e6c68 Set, else e6c90 Clear
        r.put(NODE + 0x82, 2, rng.choice((0x1f, 0x1f, 0, 5, 0x20)))
        r.put(NODE + 0x80, 2, rng.choice((0, 1, 2, 3, 3)))
    if entry == 0xe6b5a:                                         # e63fa: the name against a synthetic bad name (A0) -> equal Set / different Clear
        bad = rng.choice((0xe6e5e, 0xe6e62, 0xe6e66, 0xe6e6a))
        regs['a0'] = bad
        name = rng.choice(NAMEBUFS)
        r.put(NODE + 0x7a, 4, name)
        text = table[bad - 0xe6e06:bad - 0xe6e06 + 3]
        if rng.random() < 0.5:
            text = bytes((text[0], text[1], text[2] ^ rng.choice((1, 0x80))))
        for kk in range(3):
            r.put(name + kk, 1, text[kk])
    return r, regs


CHAINS = []


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st) and len(tr) > 0)
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C (the Z reader
    # recomputes its Z)
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(RSUCC[cons] if cons in RSUCC else SUCC[cons])
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            stopf = lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS
            o = native(r.b, regs, entry, 0, stopf)
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
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    device = 'unsupported animation machine write device'
    name = ((NODE + 0x7a, 4, NAMEBUFS[0]), (NAMEBUFS[0], 4, 0x5a592d00))

    def err(name_, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name_, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'select e2 caller requires known carry', cp, stop=SUCC[cp][0])
    # the TRAP #15 boundaries (D0.W > 1 signed): the selector runs, the dispatcher stops at the unrouted TRAP PC
    err('e6d8a-then-e6d92', 0xe6d8a, unrouted, 0xe6d92, d0=2)
    err('e6d8a-then-e6d92-7fff', 0xe6d8a, unrouted, 0xe6d92, d0=0xffff7fff)
    err('e6dc8-then-e6dd0', 0xe6dc8, unrouted, 0xe6dd0, d0=0x10002)
    err('e6a0a-then-e6d92', 0xe6a0a, unrouted, 0xe6d92, puts=((NODE + 0x76, 2, 2),))
    err('e69cc-then-e6dd0', 0xe69cc, unrouted, 0xe6dd0, puts=((NODE + 0x76, 2, 0x100),))
    # fixed ROM outside the declared synthetic bytes: the rank table read past its 11 LONGs, the character table read below it, the bad-name list
    # entry read past the list, a name buffer in fixed ROM
    err('rom-e6a6a-index', 0xe6a6a, rom, 0xe6a6a, d0=0x16)
    err('rom-e6c26-index', 0xe6c26, rom, 0xe6c26, puts=((NODE + 0x82, 2, 0xffff),))
    err('rom-e6b4c-index', 0xe6b4c, rom, 0xe6b4c, a4=0xe6e32, d7=0x54)
    err('rom-e6d66-name', 0xe6d66, rom, 0xe6d66, puts=((NODE + 0x7a, 4, 0x1000),))
    # odd node / stack / table index: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-e6a2e', 0xe6a2e, odd, 0xe6a2e, a6=NODE + 1)
    err('odd-node-e69aa', 0xe69aa, wodd, 0xe69aa, a6=NODE + 1)
    err('odd-node-e6c26', 0xe6c26, wodd, 0xe6c26, a6=NODE + 1)
    err('odd-node-e6bf2', 0xe6bf2, odd, 0xe6bf2, a6=NODE + 1)
    err('odd-node-e6ba0', 0xe6ba0, odd, 0xe6ba0, a6=NODE + 1)
    err('odd-node-e6d84', 0xe6d84, wodd, 0xe6d84, a6=NODE + 1)
    err('odd-node-e6b9a', 0xe6b9a, wodd, 0xe6b9a, a6=NODE + 1)
    err('odd-stack-e6acc', 0xe6acc, odd, 0xe6acc, stop=0xe84c8, puts=name, a7=SP + 1)
    err('odd-stack-e6adc', 0xe6adc, odd, 0xe6adc, a7=SP + 1)
    err('odd-stack-e640a', 0xe640a, odd, 0xe640a, a7=SP + 1)
    err('odd-stack-e6c90', 0xe6c90, odd, 0xe6c90, a7=SP + 1)
    err('odd-stack-3144', 0x3144, odd, 0x3144, a7=SP + 1)
    err('odd-index-e6b4c', 0xe6b4c, odd, 0xe6b4c, a4=0xe6e32, d7=0x12340001)
    # fixed ROM writes: the node / the name / the parent in fixed ROM
    err('rom-write-e695a', 0xe695a, device, 0xe695a, a6=0x1000)
    err('rom-write-e6422', 0xe6422, device, 0xe6422, a0=0x1000)
    err('rom-write-e6bf2', 0xe6bf2, device, 0xe6bf2, puts=((NODE + 0xc, 4, 0x1000),))
    # failures after executed blocks (rollback; the failing PC differs from the entry)
    err('e695a-then-e695e-odd-node', 0xe695a, odd, 0xe695e, a6=NODE + 1)
    err('e6ae8-then-e6b06-odd-stack', 0xe6ae8, odd, 0xe6b06, puts=((NODE + 0x80, 2, 0),), d7=3, a7=SP + 1)
    err('e6c5a-then-e6c80-rom', 0xe6c5a, rom, 0xe6c80, puts=((NODE + 0x80, 2, 1), (NODE + 0x7a, 4, 0x1000)))


def main():
    rng = random.Random(0xE2E2E2)
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
