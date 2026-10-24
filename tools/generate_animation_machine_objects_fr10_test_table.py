"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr10_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit, every one differs from the original): the LONG tables 70d72 (70fec, 8 LONGs),
b7f6c (b6bb8 / b6bf4, 16 LONGs), ea732 (eaa00, 4 LONGs) and eaa5c (eaada, 4 LONGs), and the bank-window LONGs 2000d0 / 2000d4 / 2001a8 / 2001ac /
200094 (bank 200000: physical offset = CPU address) with the LONGs behind them (2a1000 + 8 / 18 / 11c, 2a2000 + 8 / 18 / 194, the tables 2a3000 /
2a4000 of 32 LONGs, 2a5000 + 3c).  A native run that reads any other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a
PC that is not a block start, a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, WORD 76(A6) 0..3, WORD 8c(A6) 0..5,
WORD 8e(A6) 0..15), the records 10e900 / 10e940 / 10e980 / 10e9c0 (A0 of b7b30 / cca44), A0 = 70d72 with D0.W 0..7 (x 4) at 70fe8 / 70fea / 70fec,
A1 / A2 / A3 = the A5 counters 5ddc / 5de0 / 5de3 or 5de4 / 5de8 / 5deb at b7aa8 .. b7ac8, A3 a RAM WORD at cd80a, A5 = 108000, seeded BYTE / WORD /
LONG field edits (sign boundaries included), seeded D0-D7 and the hint worlds of the V1 spec (tools/unit_fixture_specs/fr10.py hint_worlds, converted
to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' address the record 10ea00 (rec + 20 = A0), 'rega5' an A5 field).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, the RTS sentinel).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, exits, the RTS sentinel), a consumer or a flag reader.
  single 2  a consumer (or a flag reader) entered through its real producer: kept when both outcomes occur and the producer reads RAM / declared bytes.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit); b7b40
            (EORI.B #1,CCR; RTS) returns to the U19 consumer b7b6a (return LONG b7b6a): its inverted C decides b7b6e / b7b70.
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  a flag reader entered directly: 70ff4 with the native SR Z = (A0 = 0), cd80a with the native SR N = bit 15 of the WORD (A3); the C++
            recomputes them (contract decision 3).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 13 consumers and the pass blocks ccae6 / ccaf6 / 70f3e keep the incoming C, b7b40 inverts it, 705c4 / b7b46 / ccade / eaa26 / 70f2c leave
Clear, 705be / cddae Set, every other block Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr10_test_table.py  (rewrites the generated section in place)
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
import fr10 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr10_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREAD, NREAD = 0x70ff4, 0xcd80a                     # the Z reader (CMPA.W #0,A0 of 70ff0) and the N reader (49a58 SUB.W D0,(A3))
READERS = (ZREAD, NREAD)
assert tuple(B.Z_READERS) == READERS
INVERT = 0xb7b40                                    # EORI.B #1,CCR; RTS
PASS_SET = set(B.PASS_SET)
CLEAR_SET = set(B.CLEAR_SET)
SET_SET = set(B.SET_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT = 0x10ea00, 0x10eb00
MRECS = (0x10e900, 0x10e940, 0x10e980, 0x10e9c0)
RING = 0x10e600                                     # a RAM WORD area for the A3 of cd80a
WINDOWS = {0x2000d0: (0x2a1000, (0x8, 0x18, 0x11c)), 0x2000d4: (0x2a2000, (0x8, 0x18, 0x194)), 0x200094: (0x2a5000, (0x3c,))}
TABLE_WINDOWS = {0x2001a8: 0x2a3000, 0x2001ac: 0x2a4000}


def longs(vals):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    srng = random.Random(0xF10F)
    out = [(0x70d72, longs((0x10e800, 0, 0x71622, 0, 0x10e900, 0x12, 0, 0x716ca))),                  # 70fec: 8 LONGs (0 / not 0)
           (0xb7f5c, longs((0x10, 2, 0x12340001, 6) + (3, 0, 7, 1, 0x1f, 0x00038002, 5, 4, 6, 0x10, 0x11, 0x1e, 8, 9, 0xa, 0x1b))),
           # b6bb8 / b6bf4: the table b7f6c (16 LONGs, index 5 with upper bits and a WORD that overflows when doubled) and 4 LONGs before it (negative
           # D0.W index)
           (0xea732, longs((0x10e100, 0x10e120, 0x10e140, 0x10e160))),                                 # eaa00: 4 anim LONGs
           (0xeaa5c, longs((0x10e180, 0x10e1a0, 0x10e1c0, 0x10e1e0)))]                                 # eaada: 4 anim LONGs
    for win in sorted(WINDOWS):
        dest, disps = WINDOWS[win]
        out.append((win, longs((dest,))))
        for d in disps:
            out.append((dest + d, longs((srng.getrandbits(19) << 1,))))
    for win in sorted(TABLE_WINDOWS):
        dest = TABLE_WINDOWS[win]
        out.append((win, longs((dest,))))
        out.append((dest, longs(srng.getrandbits(19) << 1 for _ in range(32))))
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


# consumer -> (C clear successor, C set successor); b7b40 returns to the U19 consumer b7b6a: clear -> inverted Set -> b7b6e, set -> Clear -> b7b70
SUCC = {0x70f8a: (0x70f94, 0x70f8e), 0x7145a: (0x71464, 0x7145e), 0x714ea: (0x714fe, 0x714ee), 0xeab36: (0xeab40, 0xeab3a), 0x70fd6: (0x70fe0, 0x70fda),
        0x70ffe: (0x71008, 0x71002), 0x71016: (0x71020, 0x7101a), 0xb7a68: (0xb7a6e, 0xb7a6c), 0xb7a78: (0xb7aca, 0xb7a80), 0xcd940: (0xcd94a, 0xcd944),
        0xcdd9c: (0xcddb2, 0xcdda0), 0xeaa3a: (0xeaa44, 0xeaa3e), 0xeaac6: (0xeaaca, 0xeaad0), INVERT: (0xb7b6e, 0xb7b70)}
assert set(SUCC) == CONS_SET
U19_CONSUMER = 0xb7b6a
# the flag readers -> (flag clear successor, flag set successor): 70ff4 Z (A0 not 0 -> 70ff8, A0 = 0 -> 70ffa), cd80a N (clear -> cd814, set -> cd80e)
RSUCC = {ZREAD: (0x70ff8, 0x70ffa), NREAD: (0xcd814, 0xcd80e)}
CHAIN_CANDIDATES = tuple(B.CHAINS)


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set; for a flag reader: 1 flag clear / 2 flag set): from its successor in the trace."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    succ = RSUCC[cons] if cons in RSUCC else SUCC[cons]
    if cons == INVERT:
        return 2 if tr[-1] == SUCC[INVERT][1] else 1        # the chain runs b7b40 to the sentinel: the C is read from the native SR (below)
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
    if p == INVERT:
        return 3 - c if c else 0
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
BOUNDED = (0x76, 0x77, 0x8c, 0x8d, 0x8e, 0x8f)
COUNTERS = (0x5ddc, 0x5de4)


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
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x1c, 0xff, 0x100, 0x3fff, 0x4000, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340001,
                                 0xffffffff, 0x80000000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0xffff0000, 0x12345600))
    if rng.random() < 0.5:
        regs['d7'] = rng.choice((0x2800, 0x27ff, 0x57ff, 0x5800, 0, 0xffff, 0x12342800, 0x12345800))
    if s in (0x70fe8, 0x70fea):
        regs['a0'] = 0x70d72
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(8)
    if s == 0x70fec:
        regs['a0'] = 0x70d72
        regs['d0'] = (regs['d0'] & 0xffff0000) | (4 * rng.randrange(8))
    if s == 0xb6bb8:
        regs['d0'] = regs['d0'] & 0xffff0000
    if s == 0xb6bf4:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(1, 16)
    if s in (0xb7aa8, 0xb7ab2, 0xb7ab6, 0xb7ac0, 0xb7ac2, 0xb7ac8, 0xb7aca):
        k = rng.choice(COUNTERS)
        regs['a1'], regs['a2'], regs['a3'] = A5 + k, A5 + k + 4, A5 + k + 7
    if s == NREAD:
        regs['a3'] = RING + 2 * rng.randrange(16)
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
    # the node link, the bounded indices; the records (BYTE 61 for b7b30, WORD 0 for cca44); the A5 counters; the RAM WORDs of cd80a
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x76, 2, rng.randrange(4))
    r.put(NODE + 0x8c, 2, rng.choice((0, 1, 2, 3, 4, 5, 5, 0xffff)))
    r.put(NODE + 0x8e, 2, rng.randrange(16))
    for m in MRECS + (REC,):
        r.put(m + 0x61, 1, rand_val(rng, 1))
        r.put(m, 2, rand_val(rng, 2))
    for k in COUNTERS:
        r.put(A5 + k, 2, rng.choice((0, 0x62, 0x63, 0x64, 0xffff, rng.getrandbits(16))))
        r.put(A5 + k + 4, 1, rand_val(rng, 1))
        r.put(A5 + k + 7, 1, rand_val(rng, 1))
    for i in range(16):
        r.put(RING + 2 * i, 2, rand_val(rng, 2))
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


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts and the RTS sentinel
ROUTED_EXITS = {0x28ae, 0x2a00, 0x8ebe, 0x1abda, 0x43e34, 0x484e2, 0x492d0, 0x49392, 0x4941e, 0x4970a, 0x49a58, 0x49a84, 0x49f8c, 0x49fc6, 0x4b54e,
                0x4bfa4, 0x7028e, 0x70302, 0x705ca, 0x71c48, 0x71c90, 0x72dd2, 0xb76d2, 0xb7cfa, 0xcc778, 0xcdd2e}   # (cde96: the return PC of cde6e only)
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x70e42, 0x70fac, 0xcd7e2, 0xcd92e, 0xcd96c, 0x70f8e, 0xb6c58, 0x70f60, 0x70fcc, 0x70ff8, 0x71028}
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | set(SUCC[INVERT])
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(SUCC[INVERT])


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p in READERS


def hints(s):
    """The V1 spec hint worlds (fr10.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def reader_hints(s):
    """The flag readers: 70ff4 with A0 0 / not 0, cd80a with the WORD (A3) 0 / 7fff / 8000 / ffff (the native SR Z / N set from them)."""
    if s == ZREAD:
        return [dict(regs=dict(a0=v)) for v in (0, 0x71502, 0x10000, 0x80000000, 1)] + [dict(regs=dict(a0=0), mirror=True)]
    return [dict(regs=dict(a3=RING + 2 * k), writes=[((RING + 2 * k) & 0xffff, 2, v)]) for k, v in enumerate((0, 0x7fff, 0x8000, 0xffff, 0x1234))]


def reader_flags(s, r, regs):
    if s == ZREAD:
        return 4 if regs['a0'] & 0xffffffff == 0 else 0
    return 8 if r.word(regs['a3']) & 0x8000 else 0


def gen_singles(rng):
    for s in STARTS:
        if s in CONS_SET:
            continue
        fl = fields(s)
        kept = {}
        hs = reader_hints(s) if s in READERS else hints(s)
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs = world(rng, fl, s, hint)
            flags = 0
            if s in READERS:
                if hint is None:
                    continue
                flags = reader_flags(s, r, regs)
            o = native(r.b, regs, s, 0, single_stop, flags)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue                                 # a stop at the entry is a zero-step run
            if (nxt in CONS_SET and s not in CLEAR_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
    if entry in (0x70f84, 0x71454, 0x714e4, 0xeab30, 0xeaa34):     # 49fc6: LONG 26(A6) = 0 -> Set (else the interpreter reads ROM: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry == 0x71012:                                         # 70594: WORD 80 bit 0, BYTE 82 bit 5, WORD 64, BYTE 15 bit 0
        r.put(NODE + 0x80, 2, rng.choice((0, 1, 1, 1)))
        r.put(NODE + 0x82, 1, rng.choice((0, 0x20, 0x20)))
        r.put(NODE + 0x64, 2, rng.choice((0, 0x8000)))
        r.put(NODE + 0x15, 1, rng.choice((0, 1)))
    if entry == 0x70fd2:                                         # 7028e: BYTE 15 bit 3, WORD 42
        r.put(NODE + 0x15, 1, rng.choice((0, 8)))
        r.put(NODE + 0x42, 2, rng.choice((0x110, 0x200, 0x40, 0x30)))
    if entry == 0xcd93c:                                         # ccade: BYTE 7b, BYTE 61 bit 3
        r.put(NODE + 0x7b, 1, rng.choice((0, 1)))
        r.put(NODE + 0x61, 1, rng.choice((0, 8)))
    if entry == 0xeaa26:                                         # BCLR.B #7,5e50(A5); 49fc6
        r.put(A5 + 0x5e50, 1, rng.choice((0, 0x80)))
        r.put(NODE + 0x26, 4, 0)
    if entry == 0xeaac0:                                         # 1abda: WORD 5430(A5)
        r.put(A5 + 0x5430, 2, rng.choice((0xffff, 0, 0x1234)))
    if entry == 0x70ff0:                                         # the Z chain: A0
        regs['a0'] = rng.choice((0, 0x71502))
    if entry == 0xb7a62:                                         # 484e2: BYTE 5683(A5) bit 0 -> Set
        r.put(A5 + 0x5683, 1, rng.choice((0, 1, 0xfe, 0xff)))
    if entry == 0xb7a6e:                                         # 49392: BYTE 568e(A5) bit (D0 & 1) -> Set
        r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3)))
        regs['d0'] = rng.choice((0, 1, 0x12340001, 0xfffe))
    if entry == 0xcdd86:                                         # 28ae: D0 = 1e >= WORD 104ca0 -> 290e (Clear), else a free node (Set)
        r.put(0x104ca0, 2, rng.choice((0, 5, 0x40, 0x40)))
        r.put(0x104c9c, 4, rng.choice((0, 0x10e700)))
        r.put(0x10e708, 4, 0)
    if entry == 0xcd804:                                         # 49a58: the ring pointer 10d722 := 10d6b4, D0 = WORD 10d6b4 = 0, WORD 10d6e4 decides N
        r.put(0x10d722, 4, 0x10d6b4)
        r.put(0x10d6b4, 2, 0)
        r.put(0x10d6e4, 2, rng.choice((0x1234, 0x8000, 0, 0xffff)))
    return r, regs


CHAINS = []


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            if cp == INVERT:
                r.put(SP, 4, U19_CONSUMER)                  # the RTS of b7b40 returns to the U19 consumer b7b6a (BCC.W b7b70)
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st) and len(tr) > 0)
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)   # b7b40: the inverted C, kept by b7b6a
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(RSUCC[cons] if cons in RSUCC else SUCC[cons])
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            if cons == INVERT:
                stopf = lambda q, tr: q == STOP or q in B.EXIT_STOPS
            else:
                stopf = lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS
            o = native(r.b, regs, entry, 0, stopf)
            if o is None or cons not in o['trace']:
                continue
            if cons == INVERT:
                if o['stop'] != STOP:
                    continue
                c = 2 if o['sr'] & 1 else 1                  # the C that b7b40 returned (the native SR at the sentinel)
            else:
                if o['stop'] not in succ:
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
            cc = c if cons == INVERT else (carry_after(cons, c) if cons not in RSUCC else 0)
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, cc, 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    flag = 'unsupported animation objects fr10 flag source'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr10 caller requires known carry', cp, stop=SUCC[cp][0])
    # the N source of cd80a (contract decision 3): the WORD (A3) outside work RAM / fixed ROM (24 bit)
    for v in (0x200000, 0x3c0000, 0x2ffff0, 0x300000, 0xff200000):
        err('n-a3-%x' % v, NREAD, flag, NREAD, a3=v)
    # fixed ROM outside the declared synthetic bytes: the table index of 70fec / b6bf4 / eaa00 / eaada, the bank table of b6bb8, the record of cca44
    err('rom-70fec-index-20', 0x70fec, rom, 0x70fec, stop=0x70ff0, a0=0x70d72, d0=0x20)
    err('rom-b6bf4-index-10', 0xb6bf4, rom, 0xb6bf4, d0=0x10)
    err('rom-eaa00-76-4', 0xeaa00, rom, 0xeaa00, puts=((NODE + 0x76, 2, 4),))
    err('rom-eaada-76-ffff', 0xeaada, rom, 0xeaada, puts=((NODE + 0x76, 2, 0xffff),))
    err('rom-cca44-a0', 0xcca44, rom, 0xcca44, a0=0x1000)
    # odd node / stack / A0 / A1 / A3: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-70ea2', 0x70ea2, odd, 0x70ea2, a6=NODE + 1)
    err('odd-node-b6c66', 0xb6c66, wodd, 0xb6c66, stop=0xb6c72, a6=NODE + 1)
    err('odd-node-eaafe', 0xeaafe, wodd, 0xeaafe, stop=0xeab2a, a6=NODE + 1)
    err('odd-node-70f2c', 0x70f2c, wodd, 0x70f2c, stop=0x70f3e, a6=NODE + 1)
    err('odd-node-71434', 0x71434, wodd, 0x71434, stop=0x7143a, a6=NODE + 1)
    err('odd-node-7143a', 0x7143a, odd, 0x7143a, a6=NODE + 1)
    err('odd-node-cd916', 0xcd916, wodd, 0xcd916, a6=NODE + 1)
    err('odd-a0-cca44', 0xcca44, odd, 0xcca44, a0=REC + 1)
    err('odd-a0-70fec', 0x70fec, odd, 0x70fec, stop=0x70ff0, a0=0x70d73, d0=0)
    err('odd-a1-b7aa8', 0xb7aa8, odd, 0xb7aa8, a1=A5 + 0x5ddd)
    err('odd-a1-b7ab2', 0xb7ab2, wodd, 0xb7ab2, stop=0xb7ab6, a1=A5 + 0x5ddd)
    err('odd-a3-cd80a', NREAD, odd, NREAD, a3=RING + 1)
    err('odd-stack-eab40', 0xeab40, odd, 0xeab40, a7=SP + 1)
    err('odd-stack-6f1ca', 0x6f1ca, odd, 0x6f1ca, a7=SP + 1)
    err('odd-stack-b7a6e', 0xb7a6e, odd, 0xb7a6e, stop=0x49392, a7=SP + 1)
    err('odd-stack-b7a78', 0xb7a78, odd, 0xb7a78, carry=1, a7=SP + 1)
    err('odd-stack-705be', 0x705be, odd, 0x705be, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-cca52', 0xcca52, device, 0xcca52, a6=0x70d72 - 0x15)        # BYTE 15(A6) = the synthetic 70d72: BSET writes fixed ROM
    err('rom-write-70fda', 0x70fda, device, 0x70fda, stop=0x70fe0, a6=0x1000)
    # failures after executed blocks (rollback; the failing PC differs from the entry): the later-unit stops of FR11 / FR12 / FR13
    # objects FR11 routes 70e42 / 70fac / cd7e2 / cd92e / cd96c since FR11: the rows that failed there (unrouted) now fail on the FR11 path (FR11 contract,
    # was: 70e2a-then-70e42 / cd7cc-then-cd7e2 / cd8ee-then-cd92e / cd95a-then-cd96c / 70f94-then-70fac with 'unsupported animation machine PC')
    err('70e2a-then-70e4a', 0x70e2a, rom, 0x70e4a, puts=((NODE + 0x8e, 2, 0), (NODE + 0x42, 2, 1), (NODE + 0x15, 1, 1)))   # FR11 70e4a reads the undeclared 2a1110
    err('70f4e-then-70f60', 0x70f4e, unrouted, 0x70f60, d7=0x6000)
    err('70fc2-then-70fcc', 0x70fc2, unrouted, 0x70fcc, puts=((NODE + 0x82, 1, 0x80),))
    err('71020-then-71028', 0x71020, unrouted, 0x71028)
    err('b6c2c-then-b6c58', 0xb6c2c, unrouted, 0xb6c58)
    err('cd7cc-then-cd7e4', 0xcd7cc, wodd, 0xcd7e4, a6=NODE + 1, puts=((NODE + 1 + 0x5f, 1, 0x80),))   # FR11 cd7e2 NEG.L -> FR10 cd7e4 writes LONG 7e(A6)
    err('cd8ee-then-cd92e', 0xcd8ee, wodd, 0xcd92e, a6=NODE + 1, puts=((NODE + 1 + 0x15, 1, 0x80),))   # FR11 cd92e writes LONG 7e(A6) of the odd node
    err('cd95a-then-cd96c', 0xcd95a, odd, 0xcd96c, a6=NODE + 1, puts=((NODE + 1 + 0x5f, 1, 0x80),))   # FR11 cd96c reads WORD 8c(A6) of the odd node
    err('70ff0-then-70ff8', 0x70ff0, unrouted, 0x70ff8, a0=0x71502)
    err('70fe4-then-70ff8', 0x70fe4, unrouted, 0x70ff8, d0=0)                       # the synthetic LONG 70d72 + 0 = 10e800 (not 0)
    err('70f94-then-70fcc', 0x70f94, unrouted, 0x70fcc, puts=((NODE + 0x8e, 2, 0), (NODE + 0x42, 2, 1), (NODE + 0x15, 1, 1), (NODE + 0x82, 1, 0x80)))   # FR11 70fac -> FR10 70fc2
    err('70f8a-then-70f8e', 0x70f8a, unrouted, 0x70f8e, carry=2)
    err('eaa44-then-eaa52-odd-stack', 0xeaa44, odd, 0xeaa52, a7=SP + 1)
    err('ccade-then-ccaf6-odd-stack', 0xccade, odd, 0xccaf6, a7=SP + 1)
    err('b7a86-then-b7aca-odd-stack', 0xb7a86, odd, 0xb7aca, a7=SP + 1, a5=A5, puts=((A5 + 0x5ddc, 2, 0x10),))


def main():
    rng = random.Random(0xF10F10)
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
