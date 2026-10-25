"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr12_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code, every one differs from the original): the ROM records 4cf64..4d0a4 (20 records of 16 bytes,
WORD a: the C of 4d84e), the ROM tables b7f14..b8004 (the LONG tables b7fbc / b7fcc of the table anims), 4411e..4439e (the sine WORD tables 4411e /
4419e of b4212), and the bank-window LONGs 2000d0 / 2000d4 / 2001a8 / 2001ac (bank 200000: physical offset = CPU address) with the LONGs behind them
(2a1000 + 4 / 20 / 24 / 70, 2a2000 + 4 / 20 / 24 / a4, the tables 2a3000 / 2a4000 of 36 LONGs).  A native run that reads any other fixed-ROM or banked
byte is dropped, as is a run that lands inside the unit on a PC that is not a block start (the bundled BEQ c113a / c11ec reached by a taken BEQ
excepted), a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 76 a handler of the FR11 decision
2, BYTE 97 0 / 4 / c, WORD 8e 0..7), the records 10e900 / 10e940 / 10e980 / 10e9c0 / 10ea00 (A0 of 717ae and of the child blocks c1246 .. c13aa),
A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 and the hint worlds of the V1 spec
(tools/unit_fixture_specs/fr12.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' address the record
10ea00 (rec + 20 = A0), 'rega5' an A5 field).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, the RTS sentinel).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, exits, the RTS sentinel) or a consumer / the C pass 4d86c.
  single 2  a consumer entered through its real producer: kept when both outcomes occur and the producer reads RAM / declared bytes.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 8 consumers and the RTS 4d86c keep the incoming C, 4d84e / b4322 Clear, 4d868 / b431c / c1260 / c12ee / c137e Set, every other block Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr12_test_table.py  (rewrites the generated section in place)
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
import fr12 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr12_test.cpp'
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
WINDOWS = {0x2000d0: (0x2a1000, (0x4, 0x20, 0x24, 0x70)), 0x2000d4: (0x2a2000, (0x4, 0x20, 0x24, 0xa4))}
TABLE_WINDOWS = {0x2001a8: 0x2a3000, 0x2001ac: 0x2a4000}
HANDLERS = tuple(B.HANDLERS)
THREAD = dict(B.THREAD)


def longs(vals):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (the region ends are the next code: 4d0a4 and 4439e are code, b8004 data
    continues)."""
    srng = random.Random(0xF12F)
    words = lambda vals: b''.join(struct.pack('>H', v & 0xffff) for v in vals)
    # 4cf64: 20 records of 16 bytes (4d84e reads WORD a of record D0.B): zero WORD a at the records 0 / 3 / 7 / 12, the others non-zero (8000 at 5,
    # 0001 at 4)
    recs = b''
    for k in range(0x14):
        wa = 0 if k in (0, 3, 7, 0x12) else (0x8000 if k == 5 else (srng.getrandbits(16) | 1))
        if k == 4:
            wa = 0x0001                             # a WORD with a zero high BYTE (the WORD TST of 4d84e; the random WORD is still drawn)
        recs += words([srng.getrandbits(16) for _ in range(5)]) + words((wa,)) + words([srng.getrandbits(16) for _ in range(2)])
    # b7f14: 4 WORDs, then 58 LONGs b7f1c..b8004 (b7fbc / b7fcc + 4 x WORD 8e: small bank-table indices, one with upper bits, one negative-looking WORD)
    tl = [srng.randrange(32) for _ in range(58)]
    tl[40] = 0x00038002                             # b7fbc + 0 (b7f1c + 4 x 40): the WORD 8002 x 4 overflows the WORD (index 0008)
    tl[41] = 0x1234000a                             # b7fbc + 4 (upper bits kept by MOVE.L, only the WORD x 4 indexes)
    tl[44] = 0xfffe                                 # b7fcc + 0: a WORD that is negative after the doubling (sign-extended index)
    sine = [srng.getrandbits(16) | (0x8000 if k % 5 == 0 else 0) for k in range(0x140)]
    sine[0] = 0x7fff                                # 4411e + 0: the largest positive WORD
    sine[0x41] = 0x8000                             # 4419e + 2: the most negative WORD (MULS.W 8000 x 8000 = 40000000)
    sine[0x40] = 0x8000                             # 4419e + 0
    sine[0x7f] = 0                                  # 4411e + fe
    out = [(0x4cf64, recs),
           (0xb7f14, words((0x1d89, 0x8001, 0x0000, 0x7fff)) + longs(tl)),
           # 4411e..4439e: 320 sine-like WORDs (signed; 7fff / 8000 / 0 at the edge indices)
           (0x4411e, words(sine))]
    for win in sorted(WINDOWS):
        dest, disps = WINDOWS[win]
        out.append((win, longs((dest,))))
        for d in disps:
            out.append((dest + d, longs((srng.getrandbits(19) << 1,))))
    for win in sorted(TABLE_WINDOWS):
        dest = TABLE_WINDOWS[win]
        out.append((win, longs((dest,))))
        out.append((dest - 0x10, longs(srng.getrandbits(19) << 1 for _ in range(36))))
    return out


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
SUCC = {0x716fa: (0x71502, 0x716fe), 0x717aa: (0x717ae, 0x713d8), 0x71f1e: (0x71f28, 0x71f22), 0xb6e7c: (0xb6e8c, 0xb6e80), 0xc1064: (0xc1d06, 0xc1068),
        0xc123e: (0xc1264, 0xc1246), 0xc12cc: (0xc12f2, 0xc12d4), 0xc135c: (0xc1382, 0xc1364)}
assert set(SUCC) == CONS_SET
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
        if n[0] > 1 and stopfn(p, trace):
            out['stop'] = p
            uc.emu_stop()
            return
        if len(trace) > 20000:
            out['bad'] = True                       # a long loop: not a table row
            uc.emu_stop()
            return
        if trace and (p & 1 or (inr(p) and p not in STARTS_SET and p != trace[-1] + B.decode(trace[-1]).size and
                                 not (p in THREAD and B.target(B.decode(trace[-1]).op_str) == p))):
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
        # Unicorn evaluates the M68000 condition codes lazily: MOVE SR,D0 on a scratch page forces the evaluation (the C of an inverted return).
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
BOUNDED = (0x76, 0x77, 0x78, 0x79, 0x8e, 0x8f, 0x97)


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
                a1=rng.choice((PARENT, CHILD)), a2=rng.choice((PARENT, CHILD)), a3=rng.choice(MRECS), a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xc, 0xf, 0x10, 0x1a, 0x1b, 0x2f, 0x30, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffd0, 0xffff, 0x10000,
                                 0x12340001, 0xffffffff, 0x80000000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0xffff0000, 0x12345600))
    if rng.random() < 0.4:
        regs['d4'] = rng.choice((0x40, 0xc0, 0x12345640, 0x99aa00c0, 0, 0x80, 0xff, 0x3f, 0x41, 0xbf, 0xc1, 0x7f))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0, 1, 0x100, 0x7fff, 0x8000, 0xffff, 0x1234ff00, 0xc000))
    if s in (0xb6eee, 0xb6f2a, 0xb7000, 0xb703c):
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(8)        # WORD 8e 0..7: inside the synthetic LONG tables
    if s == 0x4d84e:
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x14)     # the record index: inside the synthetic records 4cf64..4d0a4
    if s in (0x717ae, 0xc1246, 0xc12d4, 0xc1364, 0xc127c, 0xc128a, 0xc130c, 0xc131a, 0xc139c, 0xc13aa) and rng.random() < 0.7:
        regs['a0'] = REC
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
    # the node link, the handler LONG, the bounded indices; the records (WORD 42 for 717ae)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x76, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924)))
    r.put(NODE + 0x97, 1, rng.choice((0, 4, 0xc, 0xc)))
    r.put(NODE + 0x8e, 2, rng.randrange(8))
    for m in MRECS + (REC,):
        for off in (0, 2, 4, 6, 0x42):
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


# the stops a success row may end at outside the unit: the routed exits (FR10 70f94 / 713d8 / b6c66 / cd7c6, FR11 b4030 / b411c / b427e / b6e8c
# included), the later-unit starts (FR13 71682 / 717c2, FR14 7177a / 71786) and the RTS sentinel
ROUTED_EXITS = {0x2986, 0x2a00, 0x49214, 0x492c8, 0x49392, 0x4945e, 0x49a58, 0x49f8c, 0x49fc6, 0x4be06, 0x4be34, 0x4bfa4, 0x4d7a6, 0x71c90, 0x72d66,
                0x72dd2, 0xb4334, 0xb4958, 0xb4ab0, 0xb76d2, 0xb7cfa, 0xc1d2e, 0xc6a96, 0x70f94, 0x713d8, 0xb6c66, 0xcd7c6, 0xb4030, 0xb411c, 0xb427e,
                0xb6e8c}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x71682, 0x717c2, 0x7177a, 0x71786}
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET


def hints(s):
    """The V1 spec hint worlds (fr12.hint_worlds) of the block, converted to absolute addresses by world()."""
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
            if (nxt in CONS_SET and s not in CLEAR_SET and s not in SET_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
             a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    if entry == 0x716f4:                                         # 4d84e: WORD a of the synthetic record D0.B (zero at 0 / 3 / 7 / 12 -> Set)
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.choice((0, 3, 7, 0x12, 1, 2, 4, 5))
    if entry == 0x716ea:                                         # 4d7a6 (D0 = BYTE 86) -> 4d84e
        r.put(NODE + 0x86, 1, rng.choice((0, 1, 2, 3, 4, 5, 6, 7)))
    if entry == 0x717a4:                                         # 4945e: BYTE 568e(A5) != 0 -> Clear
        r.put(A5 + 0x568e, 1, rng.choice((0, 1)))
    if entry == 0x71f18:                                         # 49fc6: LONG 26(A6) = 0 -> Set (it writes the bank device: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry == 0xb6e6e:                                         # 49392: BYTE 568e(A5) bit (BYTE 9d(A6) & 1)
        r.put(NODE + 0x9d, 1, rng.choice((0, 1, 2, 0x81)))
        r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0xc105e:                                         # b4304: LONG 76 = b4036 / b403e -> Clear
        r.put(NODE + 0x76, 4, rng.choice((0xb4036, 0xb403e, 0xb41be, 0xc0924)))
    if entry in (0xc120c, 0xc128a, 0xc131a):                     # 28ae (via 2986): D0 = 14 >= WORD 104ca0 -> 290e (Clear), else a free node (Set)
        r.put(0x104ca0, 2, rng.choice((0, 0x15, 0x40, 0x40)))
        r.put(0x104c9c, 4, rng.choice((0, 0x10e700)))
        r.put(0x10e708, 4, 0)
        r.put(NODE + 8, 4, PARENT)                                # the list link 8(A6) of 28ae (a RAM node)
        r.put(0x100bfc, 4, PARENT)                                # the list head 100bf4 of 2986: its link 8
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
            stopf = lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS
            o = native(r.b, regs, entry, 0, stopf)
            if o is None or cons not in o['trace'] or o['stop'] not in succ:
                continue
            if 0x290e in o['trace'] and 0x2986 in o['trace']:
                continue                                         # the 28ae failure inside 2986: the C++ caller-X checked error (C7 decision 6)
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

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr12 caller requires known carry', cp, stop=SUCC[cp][0])
    # fixed ROM outside the declared synthetic bytes: the record index of 4d84e, the table index of b6eee, the sine index of b4212, the bank LONG of
    # 7150a behind an undeclared window displacement (none: the windows are declared), WORD 42 of a ROM record at 717ae
    err('rom-4d84e-index-14', 0x4d84e, rom, 0x4d84e, d0=0x14)
    err('rom-b6eee-index-40', 0xb6eee, rom, 0xb6eee, d0=0x40)
    err('rom-b7000-index-40', 0xb7000, rom, 0xb7000, d0=0x40)
    err('rom-717ae-a0', 0x717ae, rom, 0x717ae, a0=0x1000)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-71502', 0x71502, odd, 0x71502, a6=NODE + 1)
    err('odd-node-c0924', 0xc0924, odd, 0xc0924, a6=NODE + 1)
    err('odd-node-b4304', 0xb4304, odd, 0xb4304, a6=NODE + 1)
    err('odd-node-c10b0', 0xc10b0, odd, 0xc10b0, a6=NODE + 1)
    err('odd-node-b6e5e', 0xb6e5e, wodd, 0xb6e5e, a6=NODE + 1)
    err('odd-node-b4250', 0xb4250, wodd, 0xb4250, a6=NODE + 1)
    err('odd-node-c1094', 0xc1094, wodd, 0xc1094, stop=0xc10a0, a6=NODE + 1)
    err('odd-node-b6c58', 0xb6c58, wodd, 0xb6c58, stop=0xb6c66, a6=NODE + 1)
    err('odd-node-72336', 0x72336, odd, 0x72336, stop=0x72352, a6=NODE + 1)
    err('odd-node-b402a', 0xb402a, wodd, 0xb402a, a6=NODE + 1)
    err('odd-a0-717ae', 0x717ae, odd, 0x717ae, a0=REC + 1)
    err('odd-a0-c1246', 0xc1246, wodd, 0xc1246, stop=0x49214, a0=REC + 1)
    err('odd-a0-c127c', 0xc127c, wodd, 0xc127c, stop=0x49a58, a0=REC + 1)
    err('odd-a0-c13aa', 0xc13aa, wodd, 0xc13aa, stop=0x2a00, a0=REC + 1)
    err('odd-stack-b402a', 0xb402a, odd, 0xb402a, a7=SP + 1)
    err('odd-stack-b42f6', 0xb42f6, odd, 0xb42f6, a7=SP + 1)
    err('odd-stack-b4322', 0xb4322, odd, 0xb4322, a7=SP + 1)
    err('odd-stack-c120c', 0xc120c, odd, 0xc120c, stop=0x2986, a7=SP + 1)
    err('odd-stack-c123e', 0xc123e, odd, 0xc123e, carry=1, a7=SP + 1)
    err('odd-stack-716f4', 0x716f4, odd, 0x716f4, stop=0x4d84e, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-c1094', 0xc1094, device, 0xc1094, stop=0xc10a0, a6=0x1000)
    err('rom-write-b402a', 0xb402a, device, 0xb402a, a6=0x1000)
    # failures after executed blocks (rollback; the failing PC differs from the entry): the later-unit stops of FR13 / FR14, the unrouted FR11 handler
    # b4036 reached through c1d06 -> b4030
    # objects FR14 routes 7177a / 71786 since FR14 (FR14 contract; was: 7176a-then-7177a / 7177c-then-71786 with 'unsupported animation machine PC'
    # at the FR14 PC): 7177a (NEG.L D0) runs on to FR12 7177c (MOVE.L D0,64 on the odd node); 71786 runs on through FR12 71788 / 7179a to the JSR
    # 4945e push of 717a4 on the odd A7
    err('7176a-then-7177c-odd-node', 0x7176a, wodd, 0x7177c, a6=NODE + 1)
    err('7177c-then-717a4-odd-stack', 0x7177c, odd, 0x717a4, stop=0x4945e, d0=0x80000000, a7=SP + 1, puts=((NODE + 0x15, 1, 0x80),))
    # objects FR13 routes 71682 / 717c2 since FR13 (FR13 contract; was: 71532-then-71682 / 717ae-then-717c2 with 'unsupported animation machine PC' at
    # the FR13 PC): 71682 reads WORD 7a of the odd node; 717c2 runs on to FR12 717c8 (the JSR 4bfa4 push on the odd A7)
    err('71532-then-71682', 0x71532, odd, 0x71682, a6=NODE + 1)
    err('717ae-then-717c8-odd-stack', 0x717ae, odd, 0x717c8, stop=0x4bfa4, a0=REC, a7=SP + 1)
    err('c1d06-then-b4036', 0xc1d06, unrouted, 0xb4036, puts=((NODE + 0x76, 4, 0xb4036),))
    err('b4294-then-b41b2-odd-stack', 0xb4294, odd, 0xb41b2, stop=0x4bfa4, a7=SP + 1, puts=((NODE + 0x15, 1, 0x80),))


def main():
    rng = random.Random(0xF12F12)
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


if __name__ == '__main__':
    main()
