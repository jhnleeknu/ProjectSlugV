"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr11_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code, every one differs from the original): the ROM tables b7f14..b8004 (the WORD table b7f14 of
b774a and the LONG tables b7f5c / b7f64 / b7f7c / b7fc4 of the table anims), 4411e..4439e (the sine WORD tables 4411e / 4419e of b4156 / bfcb2),
bfdd0..bfebe (the WORD table bfdd0 of bfdbe and the records bfdee + 8k of bfc2a / bfc70 / bfc80), and the bank-window LONGs 2000d0 / 2000d4 / 200080 /
200094 / 2001a8 / 2001ac / 2001c0 (bank 200000: physical offset = CPU address) with the LONGs behind them (2a1000 + 110, 2a2000 + 188, 2a7000 + 144,
2a5000 + 20, the tables 2a3000 / 2a4000 / 2a6000 of 32 LONGs).  A native run that reads any other fixed-ROM or banked byte is dropped, as is a run that
lands inside the unit on a PC that is not a block start, a run whose computed jump leaves the decision-2 targets, a run that writes a device port, or
that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 76 / 7a a handler of decision 2,
BYTE 97 0 / 4 / c, WORD 8e 0..7, WORD 8c 0..5, LONG 9e a record bfdee + 8k), the records 10e900 / 10e940 / 10e980 / 10e9c0 / 10ea00 (A0 of the bounds
blocks and of b6cb0 / b68a0 / b7d94), A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 and the hint worlds of
the V1 spec (tools/unit_fixture_specs/fr11.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' address
the record 10ea00 (rec + 20 = A0), 'rega5' an A5 field).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a computed-jump target, the TRAP b3e58, the RTS sentinel).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer: kept when both outcomes occur and the producer reads RAM / declared bytes.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 11 consumers keep the incoming C, b689c / b7dae (ORI.B #1,CCR) Set, every other block Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr11_test_table.py  (rewrites the generated section in place)
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
import fr11 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr11_test.cpp'
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
WINDOWS = {0x2000d0: (0x2a1000, (0x110,)), 0x2000d4: (0x2a2000, (0x188,)), 0x200080: (0x2a7000, (0x144,)), 0x200094: (0x2a5000, (0x20,))}
TABLE_WINDOWS = {0x2001a8: 0x2a3000, 0x2001ac: 0x2a4000, 0x2001c0: 0x2a6000}
JUMP_TARGETS = dict(B.JUMP_TARGETS)
HANDLERS = tuple(B.HANDLERS)


def longs(vals):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (the region ends are the next code: b8004 data continues, 4439e and bfec6
    are code)."""
    srng = random.Random(0xF11F)
    words = lambda vals: b''.join(struct.pack('>H', v & 0xffff) for v in vals)
    # b7f14: 4 WORDs (b774a, WORD 8e 0..3), then 58 LONGs b7f1c..b8004 (b7f5c / b7f64 / b7f7c / b7fc4 + 4 x WORD 8e: small bank-table indices, one
    # with upper bits and a WORD that overflows when doubled, one negative-looking WORD)
    tl = [srng.randrange(32) for _ in range(58)]
    tl[16] = 0x00038002                             # b7f5c + 0 ... index 0 of b7f5c (b7f1c + 4 x 16)
    tl[19] = 0x1234000a                             # b7f64 + 4 (upper bits kept by MOVE.L, only the WORD x 4 indexes)
    tl[24] = 0xfffe                                 # b7f7c + 0: a WORD that is negative after the doubling (sign-extended index)
    sine = [0 if k in (0, 0x3f) else (srng.getrandbits(16) | (0x8000 if k % 5 == 0 else 0)) for k in range(0x140)]
    sine[0x10] = 0x1200                             # a WORD with a zero low BYTE (the WORD BEQ of bfcb2)
    table = [srng.getrandbits(16) for _ in range(15)]
    table[4] = 0x0005                               # bfdd8: the low WORD of the LONG at bfdd6 (bfc2a with D0.W 1ffd: index -18) is a small bank-table index
    out = [(0xb7f14, words((0x1d89, 0x8001, 0x0000, 0x7fff)) + longs(tl)),
           # 4411e..4439e: 320 sine-like WORDs (signed, zero at the indices 0 / 3f for the BEQ of bfcb2, 1200 at 10)
           (0x4411e, words(sine)),
           # bfdd0: 15 WORDs (bfdbe, 49a84 D0 0..f; the 16th is the first WORD of bfdee), bfdee: 26 records of 8 bytes (LONG = a small bank-table index,
           # WORD 4 / 6 = sound numbers)
           (0xbfdd0, words(table) +
            b''.join(longs((srng.randrange(32) | (0x12340000 if k == 3 else 0),)) + words((srng.getrandbits(16), srng.getrandbits(16))) for k in range(0x1a)))]
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
SUCC = {0xb687a: (0xb68b6, 0xb687e), 0xb6d74: (0xb6d7e, 0xb6d78), 0xb6e5a: (0xb6e8c, 0xb6e5e), 0xb7800: (0xb780a, 0xb7804), 0xc547c: (0xc5486, 0xc5480),
        0xc560e: (0xc5618, 0xc5612), 0xb688e: (0xb68a0, 0xb6892), 0xb6cac: (0xb6ccc, 0xb6cb0), 0xb6d8c: (0xb6dac, 0xb6d90), 0xc5492: (0xc551e, 0xc5496),
        0xb7d8c: (0xb7db2, 0xb7d94)}
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
        if trace and (p & 1 or (inr(p) and p not in STARTS_SET and p != trace[-1] + B.decode(trace[-1]).size)):
            out['bad'] = True                       # an odd PC or a landing inside a block of the unit: the C++ rejects it (error rows)
            uc.emu_stop()
            return
        if trace and trace[-1] in JUMP_TARGETS and p not in JUMP_TARGETS[trace[-1]]:
            out['bad'] = True                       # a computed jump outside the decision-2 targets: the C++ checked jump-target error (error rows)
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
BOUNDED = (0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x8c, 0x8d, 0x8e, 0x8f, 0x97, 0x9e, 0x9f, 0xa0, 0xa1)


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
    if s in (0xb67c4, 0xb6cd8, 0xb6db8, 0xb777a, 0xb6800, 0xb6d14, 0xb6df4, 0xb77b6):
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(8)        # WORD 8e 0..7: inside the synthetic LONG tables
    if s == 0xbfc2a:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(0x1a)
    if s == 0xbfdbe:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(0x10)
    if s == 0xb42b0 and rng.random() < 0.8:
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.choice((0, 4, 0xc))
    if s == 0xc54a6 and rng.random() < 0.8:
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x1b)
    if s == 0xb4156:
        regs['d7'] = (regs['d7'] & 0xffff0000) | rng.randrange(0x81)
    if s == 0xb4154:
        regs['d7'] = (regs['d7'] & 0xffffff00) | rng.randrange(0x80, 0x100)
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
    # the node link, the handler LONGs, the bounded indices, the record pointer; the records (bounds WORDs, WORD 42 for b6cb0)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x76, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e, 0xb41be, 0xb403e)))
    r.put(NODE + 0x7a, 4, rng.choice(HANDLERS + (0, 0xb41be, 0xb403e)))
    r.put(NODE + 0x97, 1, rng.choice((0, 4, 0xc, 0)))
    r.put(NODE + 0x8c, 2, rng.choice((0, 1, 2, 3, 4, 5, 5, 0xffff)))
    r.put(NODE + 0x8e, 2, rng.randrange(8))
    r.put(NODE + 0x9e, 4, 0xbfdee + 8 * rng.randrange(0x1a))
    if rng.random() < 0.5:
        r.put(NODE + 0x7c, 2, rand_val(rng, 2))                            # WORD 7c (b7d52) apart from the handler LONG 7a
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


# the stops a success row may end at outside the unit: the routed exits (FR10 70efe / 70fc2 / cd7c6 / cd7e4 / cd93c included), the later-unit starts,
# the computed-jump targets that are not FR11 blocks, the TRAP b3e58 and the RTS sentinel
ROUTED_EXITS = {0x28ae, 0x2986, 0x8ebe, 0x8ff4, 0x1aa3a, 0x43e34, 0x43ea4, 0x491c4, 0x49214, 0x49290, 0x49392, 0x496c2, 0x4970a, 0x49a58, 0x49a84,
                0x49f8c, 0x49fc6, 0x4b54e, 0x4be06, 0x4be2c, 0x4be34, 0x4c2fa, 0xb3ea2, 0xb4334, 0xb4958, 0xb4ab0, 0xb4aca, 0xb76d2, 0xb7cfa, 0xb7e06,
                0xc6a96, 0xcdc1c, 0x70efe, 0x70fc2, 0xcd7c6, 0xcd7e4, 0xcd93c}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0xb41f2, 0xb6e5e, 0xc5612, 0xb6d90, 0xbfcfa}
JUMP_STOPS = set(t for ts in JUMP_TARGETS.values() for t in ts) - STARTS_SET
TRAP_STOPS = {0xb3e58}
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_STOPS | TRAP_STOPS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_STOPS) + sorted(TRAP_STOPS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET


def hints(s):
    """The V1 spec hint worlds (fr11.hint_worlds) of the block, converted to absolute addresses by world(); the computed jumps get every allowed
    target (the handlers of b4030, the displacements 0 / 4 / c of b42b0, the indices 0..1a of c54a6)."""
    h = B.hint_worlds(s)
    if s == 0xb4030:
        h = h + [dict(a6off=[(0x76, 4, v)]) for v in HANDLERS]
    if s == 0xb42b0:
        h = h + [dict(regs=dict(d0=0x12345600 | v)) for v in (0, 4, 0xc)]
    if s == 0xc54a6:
        h = h + [dict(regs=dict(d0=0x12345600 | v)) for v in range(0x1b)]
    return h


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
    if entry in (0xb6874, 0xb6d6e, 0xb6e54, 0xb77fa, 0xc5476, 0xc5608):    # 49fc6: LONG 26(A6) = 0 -> Set (it writes the bank device: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry in (0xb6ca2, 0xb6d82):                              # 49392: BYTE 568e(A5) bit (BYTE 9d(A6) & 1)
        r.put(NODE + 0x9d, 1, rng.choice((0, 1, 2, 0x81)))
        r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3)))
    if entry in (0xb687e, 0xb7d5a):                              # 28ae (via 2986): D0 = 14 >= WORD 104ca0 -> 290e (Clear), else a free node (Set)
        r.put(0x104ca0, 2, rng.choice((0, 0x15, 0x40, 0x40)))
        r.put(0x104c9c, 4, rng.choice((0, 0x10e700)))
        r.put(0x10e708, 4, 0)
        r.put(NODE + 8, 4, PARENT)                                # the list link 8(A6) of 28ae (a RAM node)
        r.put(0x100bfc, 4, PARENT)                                # the list head 100bf4 of 2986: its link 8
        if entry == 0xb7d5a:
            r.put(NODE + 0x7c, 2, rng.choice((1, 0x10, 0x7fff)))
    if entry == 0xc5486:                                         # 4b54e: LONG 56(A6) = 0 -> 4b6be
        r.put(NODE + 0x56, 4, rng.choice((0, 0, 0x10e900)))
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
    jump = 'unsupported animation objects fr11 jump target'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr11 caller requires known carry', cp, stop=SUCC[cp][0])
    # the computed jumps (contract decision 2): a JMP (A0) target outside the ROM-writer handlers (LONG compare), a b42b8 displacement other than 0 / 4 / c,
    # a c54b2 index above 1a
    for v in (0, 0xb41c2, 0xb4030, 0x10b41be, 0xc0926, 0xff0b403e):
        err('b4030-target-%x' % v, 0xb4030, jump, 0xb4030, puts=((NODE + 0x76, 4, v),))
    for v in (8, 2, 0x10, 0xff, 0x80):
        err('b42b0-d0-%x' % v, 0xb42b0, jump, 0xb42b0, d0=0x12345600 | v)
    for v in (0x1b, 0x40, 0xff, 0x80):
        err('c54a6-d0-%x' % v, 0xc54a6, jump, 0xc54a6, d0=0x12345600 | v)
    # fixed ROM outside the declared synthetic bytes: the table index of b774a / b67c4, the record of bfc2a / bfc70, the sine index of b4156
    err('rom-b774a-8e-100', 0xb774a, rom, 0xb774a, stop=0xb776e, puts=((NODE + 0x8e, 2, 0x100),))
    err('rom-b67c4-index-40', 0xb67c4, rom, 0xb67c4, d0=0x40)
    err('rom-bfc2a-index-40', 0xbfc2a, rom, 0xbfc2a, d0=0x40)
    err('rom-bfc70-record', 0xbfc70, rom, 0xbfc70, puts=((NODE + 0x9e, 4, 0x1000),))
    err('rom-b4156-d7-200', 0xb4156, rom, 0xb4156, d7=0x200)
    err('rom-b408c-a0', 0xb408c, rom, 0xb408c, a0=0x1000)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-70e42', 0x70e42, odd, 0x70e42, a6=NODE + 1)
    err('odd-node-b4030', 0xb4030, odd, 0xb4030, a6=NODE + 1)
    err('odd-node-b6d4c', 0xb6d4c, wodd, 0xb6d4c, stop=0xb6d6a, a6=NODE + 1)
    err('odd-node-b6e2c', 0xb6e2c, wodd, 0xb6e2c, stop=0xb6e50, a6=NODE + 1)
    err('odd-node-cd92e', 0xcd92e, wodd, 0xcd92e, stop=0xcd93c, a6=NODE + 1)
    err('odd-node-b4104', 0xb4104, odd, 0xb4104, a6=NODE + 1)
    err('odd-node-b4064', 0xb4064, odd, 0xb4064, a6=NODE + 1)
    err('odd-node-c5540', 0xc5540, odd, 0xc5540, a6=NODE + 1)
    err('odd-a0-b408c', 0xb408c, odd, 0xb408c, a0=REC + 1)
    err('odd-a0-b40dc', 0xb40dc, odd, 0xb40dc, a0=REC + 1)
    err('odd-a0-b6cb0', 0xb6cb0, odd, 0xb6cb0, a0=REC + 1)
    err('odd-a0-b7d94', 0xb7d94, wodd, 0xb7d94, a0=REC + 1)
    err('odd-a0-b68a0', 0xb68a0, wodd, 0xb68a0, stop=0xb68b6, a0=REC + 1)
    err('odd-stack-b42c8', 0xb42c8, odd, 0xb42c8, a7=SP + 1)
    err('odd-stack-b3e1c', 0xb3e1c, odd, 0xb3e1c, stop=0x8ff4, a7=SP + 1)
    err('odd-stack-b3e46', 0xb3e46, odd, 0xb3e46, a7=SP + 1)
    err('odd-stack-b7d5a', 0xb7d5a, odd, 0xb7d5a, stop=0x2986, a7=SP + 1)
    err('odd-stack-b7d8c', 0xb7d8c, odd, 0xb7d8c, carry=1, a7=SP + 1)
    err('odd-stack-cda2c', 0xcda2c, odd, 0xcda2c, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM / the bank window
    err('rom-write-b4ac2', 0xb4ac2, device, 0xb4ac2, a6=0xb7f14 - 0x95)   # BYTE 95(A6) = the synthetic b7f14: BSET writes fixed ROM
    err('rom-write-cd92e', 0xcd92e, device, 0xcd92e, stop=0xcd93c, a6=0x1000)
    # failures after executed blocks (rollback; the failing PC differs from the entry): the later-unit stops of FR12 / FR13, the TRAP boundary b3e58 and
    # the unrouted computed-jump targets
    err('b3e46-then-b3e58', 0xb3e46, unrouted, 0xb3e58, puts=((SP, 4, 0),))
    # objects FR12 routes b41f2 / b6e5e / c5612 / c0924 / b42c4 since FR12 (FR12 contract; was: b41d8-then-b41f2 / b6e5a-then-b6e5e / c560e-then-c5612 /
    # b4030-then-c0924 / b42b0-then-b42c4 with 'unsupported animation machine PC' at the FR12 PC): the rows fail on the FR12 path or keep the failing PC
    # with an odd node
    err('b41d8-then-b4292-odd-stack', 0xb41d8, odd, 0xb4292, a7=SP + 1, puts=((NODE + 0x8e, 2, 1),))   # FR12 b41f2 .. b427a -> FR11 b427e -> RTS b4292
    # objects FR13 routes b6d90 / bfcfa / c54ba / c54d6 since FR13 (FR13 contract; was: b6d8c-then-b6d90 / bfcea-then-bfcfa / c5496-then-c54ba with
    # 'unsupported animation machine PC' at the FR13 PC): b6d90 reads WORD 42 of the odd A0, bfcfa pushes the JSR 2986 return on the odd A7, c54ba
    # runs on to FR13 c5520 that writes LONG (A6) of the odd node
    err('b6d8c-then-b6d90', 0xb6d8c, odd, 0xb6d90, carry=2, a0=REC + 1)
    err('b6e5a-then-b6e5e', 0xb6e5a, wodd, 0xb6e5e, carry=2, a6=NODE + 1)       # FR12 b6e5e MOVE.L #b6ed8,(A6) of the odd node
    err('c560e-then-2a00-odd-stack', 0xc560e, odd, 0x2a00, stop=0x299c, carry=2, a7=SP + 1)   # FR12 c5612 JMP 2a00: the BSR 299c push on the odd A7
    err('bfcea-then-bfcfa', 0xbfcea, odd, 0xbfcfa, stop=0x2986, d0=4, a7=SP + 1)
    err('b4030-then-b4036', 0xb4030, unrouted, 0xb4036, puts=((NODE + 0x76, 4, 0xb4036),))
    err('b4030-then-b412c-odd-stack', 0xb4030, odd, 0xb412c, a7=SP + 1, puts=((NODE + 0x76, 4, 0xc0924),))   # FR12 c0924 -> b4294 -> b429e -> FR11 b411c
    err('b42b0-then-b42bc', 0xb42b0, unrouted, 0xb42bc, d0=4)
    err('b42b0-then-b42ea-odd-stack', 0xb42b0, odd, 0xb42ea, stop=0x49a58, d0=0xc, a7=SP + 1)   # FR12 b42c4 BRA.W b42ea: the JSR 49a58 push
    err('c54a6-then-c54b2', 0xc54a6, unrouted, 0xc54b2, d0=0)
    err('c54a6-then-c551a', 0xc54a6, unrouted, 0xc551a, d0=0x1a)
    err('c5496-then-c5520', 0xc5496, wodd, 0xc5520, a6=NODE + 1, puts=((NODE + 1 + 0x5e, 1, 2),))
    err('b6e8c-then-b6e9c-odd-stack', 0xb6e8c, odd, 0xb6e9c, stop=0xb7e06, a7=SP + 1, puts=((NODE + 0x9c, 1, 1),))
    err('b403e-then-b40f0-odd-stack', 0xb403e, odd, 0xb40f0, stop=0x43ea4, a7=SP + 1, puts=((NODE + 0x8c, 2, 0),))


def main():
    rng = random.Random(0xF11F11)
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
