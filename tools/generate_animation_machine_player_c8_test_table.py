"""Generates the native-oracle tables of engine/tests/animation_machine_player_c8_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the WORD table 1b716 that C2 1cb08 reads for the producer chain of 1fa70 and
the (handler LONG, key WORD) list 21b3c that C3 215e6 reads for the producer chain of 21e72 (the same handlers, other keys).  A native run that reads
any other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a PC that is not a block start, a JMP (A1) 21d9e / 21e76 to a
PC outside its ROM list (the C++ checked jump-target error), a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 22(A6) := the LONG table 10e700,
LONG 84(A6) := a routed slot-84 value, WORD 78 mostly 0 / 1, BYTE 9e 0..3, BYTE 9f / 9c small), the motion records 10e900 / 10e940 / 10e980 / 10e9c0
(A0 of a direct 1cfee / 1cffa / 1d018 entry: LONGs 10 / 14 / 18), the record 10ea00 (A4 of 4d0cc .. 4d0f6 / 4d1c0 / 4d1c6, or the A5 records 5cba /
5ce6: WORDs 0 / 2 / 4 / 18, BYTEs 22 / 28, LONGs c / 10 / 14), the WORD 10000e (-7ff2(A5)), the BYTE 5683(A5), A1 a handler of the ROM list of the
JMP (A1) 21d9e / 21e76, A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 (the input bits of D0, the ASR.L
count D2) and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc8.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at
1fe000, 'rec' / 'regrec' address the record 10ea00 (rec + 20 = A0 / A4), 'stack' writes at A7).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a JMP (A1) list handler).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, list handlers, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer: kept when both C values occur.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 4d0ea Set; every other block leaves Unknown (no pass block, no data C).
Usage:  .venv/bin/python tools/generate_animation_machine_player_c8_test_table.py  (rewrites the generated section in place)
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
import pc8 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c8_test.cpp'
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
REC, PARENT, LTAB = 0x10ea00, 0x10eb00, 0x10e700
MRECS = (0x10e900, 0x10e940, 0x10e980, 0x10e9c0)
PLAYERS = (0x100cb8, 0x100da8)
LIST_21B3C_KEYS = (0, 3, 2)                         # synthetic keys of the list 21b3c (ROM: 0 1 2); the handlers are the ROM handlers
LIST_JUMPS = dict((k, set(v)) for k, v in B.LIST_JUMPS.items())


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)




def table_1b716():
    """32 WORDs at 1b716: C2 1cb08 reads WORD (A0 + 2 x BYTE 9f) (A0 = 1b716 for 1fa68); not 0 -> C5 1cb1a reads WORD (A0 + W) and tests LONG 22(A6)
    + 4 x that WORD."""
    w = [0] * 32
    w[0:5] = [0x10, 0, 0x12, 0, 0x14]            # 1b716 + 2 x 9f (9f 0..4)
    w[8:11] = [1, 2, 3]                          # 1b716 + 10 / 12 / 14
    return words(w)


def list_21b3c():
    out = b''
    for h, k in zip(B.LIST_21B3C, LIST_21B3C_KEYS):
        out += struct.pack('>IH', h, k)
    return out + struct.pack('>I', 0)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1b716, table_1b716()),                                            # C2 1cb08 / C5 1cb1a from 1fa68
            (0x21b3c, list_21b3c())]                                             # C3 215e6 from 21e6a


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
SUCC = {0x1f47c: (0x1f486, 0x1f480), 0x1fa70: (0x1fa74, 0x1fa90), 0x1fd34: (0x1fd3c, 0x1fd38), 0x21e72: (0x21e78, 0x21e76),
        0x4d0e6: (0x4d0f6, 0x4d0ea)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both C values occur
CHAIN_CANDIDATES = tuple(B.CHAINS)
JUMP_ALLOWED = LIST_JUMPS


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
        return None                                 # C8 writes no device port
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
BOUNDED = (0x9e, 0x9f, 0x9c, 0x76, 0x78)


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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice(MRECS + (REC, CHILD)),
                a1=rng.choice((PARENT, CHILD)), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=rng.choice((REC, A5 + 0x5cba, A5 + 0x5ce6)), a5=A5,
                a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x22, 0x30, 0x40, 0x50, 0x80, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000))
    if rng.random() < 0.5:
        regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0, 1, 2, 5, 0x1f, 0x20, 0x21, 0x3f, 0x40, 0x45))
    if s in LIST_JUMPS:
        regs['a1'] = rng.choice(sorted(LIST_JUMPS[s]))
    if s in (0x1cfee, 0x1cffa, 0x1d018):
        regs['a0'] = rng.choice(MRECS + (REC,))
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
    # the node links and pointers, the slot LONG 84, the bounded indices; the player nodes; the motion records (LONGs 10 / 14 / 18), the A4 records
    # (REC and 5cba / 5ce6(A5)), the WORD -7ff2(A5) and the BYTE 5683(A5)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0x9e, 1, rng.randrange(4))
    r.put(NODE + 0x9f, 1, rng.randrange(5))
    r.put(NODE + 0x9c, 1, rng.randrange(6))
    r.put(NODE + 0x76, 2, rng.choice((0, 0, 1, 1, 0x4000, 0xffff)))
    r.put(NODE + 0x78, 2, rng.choice((0, 0, 1, 1, 0x100, 0x8000)))
    for p in PLAYERS:
        r.put(p, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c)))
        r.put(p + 0x9e, 1, rng.randrange(4))
        r.put(p + 0x78, 2, rng.choice((0, 1)))
    for m in MRECS + (REC,):
        for off in (0x10, 0x14, 0x18):
            r.put(m + off, 4, rand_val(rng, 4))
    for a4 in (REC, A5 + 0x5cba, A5 + 0x5ce6):
        r.put(a4, 2, rng.choice((0, 0, 1, 0x100, 0x8000)))
        r.put(a4 + 2, 2, rand_val(rng, 2))
        r.put(a4 + 4, 2, rand_val(rng, 2))
        r.put(a4 + 0xc, 4, rng.choice((0, PARENT, 0x12345678)))
        r.put(a4 + 0x10, 4, rand_val(rng, 4))
        r.put(a4 + 0x14, 4, rand_val(rng, 4))
        r.put(a4 + 0x18, 2, rng.choice((0, 1, 0x12, 0x1234, 0x8000)))
        r.put(a4 + 0x22, 1, rng.choice((0, 1, 2, 0x80, 0xff)))
        r.put(a4 + 0x28, 1, rng.choice((0, 0x01, 0x80, 0x81, 0x7e, 0xff)))
    r.put(A5 - 0x7ff2, 2, rng.choice((0, 1, 0x12, 0x1234, 0x8000)))
    r.put(A5 + 0x5683, 1, rng.choice((0, 8, 0xf7, 0xff)))
    for i in range(0, 0x80, 4):
        if rng.random() < 0.5:
            r.put(LTAB + i, 4, rng.choice((0, 0, 1, 0x80000000, 0x12345678)))         # C5 1cb1a: LONG 22(A6) + sext(4 x WORD)
    if s == 0x1d070:
        regs['a7'] = SP - 4                               # the LONG that 1d066 pushed (above it the return LONG)
        r.put(SP - 4, 4, rand_val(rng, 4))
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


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts (deferred leaders), the JMP (A1) list handlers and the
# RTS sentinel
ROUTED_EXITS = {0xce02, 0x1cab6, 0x1cabe, 0x1cb08, 0x1cd98, 0x1cea8, 0x1cfbe, 0x1ebbe, 0x1f5d2, 0x1f5f2, 0x1f76a, 0x1f76e, 0x1f7a4, 0x1fa3c, 0x1fa90,
                0x1fad2, 0x201a2, 0x201da, 0x2156a, 0x215e6, 0x21ffc, 0x43e34, 0x484b4, 0x49fc6, 0x4be82, 0x4bfc0, 0x4d100, 0x4de7a}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x1f48a, 0x1fb28, 0x1fd3c, 0x21ea0, 0x21d0e, 0x2210c, 0x223a0, 0x223d6}
JUMP_TARGETS = set(t for v in LIST_JUMPS.values() for t in v if t not in STARTS_SET)
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_TARGETS - ROUTED_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET


def hints(s):
    """The V1 spec hint worlds (pc8.hint_worlds) of the block; converted to absolute addresses by world()."""
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0), 1, o)


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
    if entry == 0x1f476:                                         # 49fc6: LONG 26(A6) = 0 -> Set (else the interpreter reads ROM: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry == 0x1fa68:                                         # C2 1cb08 on the synthetic WORD table 1b716 with BYTE 9f 0..4
        r.put(NODE + 0x9f, 1, rng.randrange(5))
    if entry in (0x1fd2e, 0x4d0e0):                              # 484b4: BTST.B #3,5683(A5)
        r.put(A5 + 0x5683, 1, rng.choice((0, 8, 0xf7, 0xff)))
        regs['a4'] = REC
    if entry == 0x21e6a:                                         # 215e6 on the synthetic list 21b3c (keys 0 3 2): BYTE 9c
        r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 4, 0xff)))
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
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=0x21602, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c8 jump target'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c8 caller requires known carry', cp, stop=SUCC[cp][0])
    # the JMP (A1) (contract decision 2): A1 outside the list; the unrouted handler 21e48 fails at the next dispatch
    for v in (0x21d60, 0x21e3b, 0, 0x121602, 0x21e52, 0x1021e3a, 0x21c20):
        err('jump-21d9e-%x' % v, 0x21d9e, jump, 0x21d9e, a1=v)
    for v in (0x21e3a, 0x21e48, 0, 0x21d61, 0x1021602, 0x21c24):
        err('jump-21e76-%x' % v, 0x21e76, jump, 0x21e76, a1=v)
    err('entry-21d9e-21e48', 0x21d9e, unrouted, 0x21e48, a1=0x21e48)
    # the motion record A0 in fixed ROM outside the declared synthetic bytes (the ROM records 1cf1e / 1cf3e of the C4 table 1cfce)
    err('rom-1cfee-1cf1e', 0x1cfee, rom, 0x1cfee, a0=0x1cf1e)
    err('rom-1cffa-1cf3e', 0x1cffa, rom, 0x1cffa, a0=0x1cf3e)
    err('rom-1d018-1cf1e', 0x1d018, rom, 0x1d018, a0=0x1cf1e)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1f3f0', 0x1f3f0, wodd, 0x1f3f0, stop=0x1f418, a6=NODE + 1)
    err('odd-node-1fcce', 0x1fcce, wodd, 0x1fcce, stop=0x1fcd4, a6=NODE + 1)
    err('odd-node-1fcd4', 0x1fcd4, wodd, 0x1fcd4, stop=0x1fd12, a6=NODE + 1)
    err('odd-node-4d1c6', 0x4d1c6, wodd, 0x4d1c6, stop=0x43e34, a6=NODE + 1)
    err('odd-node-1d066', 0x1d066, odd, 0x1d066, stop=0x4be82, a6=NODE + 1)
    err('odd-node-1cffa', 0x1cffa, odd, 0x1cffa, stop=0x1d018, a6=NODE + 1)
    err('odd-a0-1cfee', 0x1cfee, odd, 0x1cfee, a0=REC + 1)
    err('odd-a4-4d0d4', 0x4d0d4, odd, 0x4d0d4, stop=0x4d0e0, a4=REC + 1)
    err('odd-a4-4d0f6', 0x4d0f6, wodd, 0x4d0f6, stop=0x4d100, a4=REC + 1)
    err('odd-a4-4d1c0', 0x4d1c0, odd, 0x4d1c0, stop=0x4d1c6, a4=REC + 1)
    err('odd-stack-1d066', 0x1d066, odd, 0x1d066, stop=0x4be82, a7=SP + 1)
    err('odd-stack-1d070', 0x1d070, odd, 0x1d070, stop=0x1d076, a7=SP + 1)
    err('odd-stack-ea626', 0xea626, odd, 0xea626, a7=SP + 1)
    err('odd-stack-4d0ea', 0x4d0ea, odd, 0x4d0ea, a7=SP + 1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1f45c-then-1f48a', 0x1f45c, unrouted, 0x1f48a, d0=4)
    err('1fb1e-then-1fb28', 0x1fb1e, unrouted, 0x1fb28, puts=((NODE + 0x15, 1, 0x80),))
    err('21e52-then-21ea0', 0x21e52, unrouted, 0x21ea0, puts=((NODE + 0x9d, 1, 1),))
    err('21e52-then-21d0e', 0x21e52, unrouted, 0x21d0e, puts=((NODE + 0x9d, 1, 0x80),))
    err('21e7c-then-223a0', 0x21e7c, unrouted, 0x223a0, d0=1)
    err('21e84-then-223d6', 0x21e84, unrouted, 0x223d6, d0=2)
    err('21e8c-then-2210c', 0x21e8c, unrouted, 0x2210c, d0=0x10)
    err('1fd34-then-1fd3c', 0x1fd34, unrouted, 0x1fd3c, carry=1)
    err('1d04e-then-1d064', 0x1d04e, odd, 0x1d064, a7=SP + 1)
    err('1d076-then-1d084', 0x1d076, odd, 0x1d084, a7=SP + 1, puts=((NODE + 0x61, 1, 2),))
    err('4d1c0-then-4d206', 0x4d1c0, odd, 0x4d206, a7=SP + 1)
    err('1cfde-then-1cfec', 0x1cfde, odd, 0x1cfec, a7=SP + 1, puts=((NODE + 0x6e, 1, 8),))
    err('4d0cc-then-4d100', 0x4d0cc, odd, 0x4d100, a7=SP + 1)


def main():
    rng = random.Random(0xC8C8)
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
    jstops = set(d['stop'] for d in singles if d['entry'] in LIST_JUMPS)
    print('list handlers reached by 21d9e / 21e76 rows', sorted(hex(x) for x in jstops))


if __name__ == '__main__':
    main()
