"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b4b_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data): the bank-window LONGs
20003c..2000a0 (20008c -> 2a0000 and 200090 -> 2a0100), the bank LONGs 2a000c and 2a0130 that d207c / e79d0 read through them, the sin / cos WORDs
4411e..4439e and the 128 bytes 0000..0080 (the C++ test's program vectors view: BTST.B #7,61(A0) with A0 = 0).  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no
bytes there).
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (ring cells 10e078 + 8k), child / parent record A0 = 10e400, the parent
record of LONG c(A6) = 10eb00, A1 / A2 / A4 records 10ea00 / 10e900 / 10e800, the rectangle of LONG 56(A0) = 10ec40, the e74f8 script WORD at 10ec80,
A5 = 108000 (LONG 10d3a2 / 10d3a6), the 28ae free node 10ed00 and the node link LONG 8(A6) = 10ec00, seeded BYTE / WORD / LONG field edits (BYTE /
WORD sign boundaries included), seeded D0-D7, declared stack words for the blocks that pop (283cc 2840a 28456 e7500).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the first instruction that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP 2a00, BCC 22c82, BRA 2b8b6 / d239c, the RTS sentinel).
  single 2  a consumer entered through its real producer (28ae -> 2b746 2b788 e7a2c, 288c -> 28268): stop = the consumer's successor; the native branch
            on the real flags decides it.  49fc6 runs ROM scripts: its five consumers have declared-C rows here (real chains in V1).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C; the blocks that end
with ORI.B #1,CCR are the only producers (C Set, contract decision 5).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b4b_test_table.py  (rewrites the generated section in place)
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
import b4b as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b4b_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ORI_SET = set(B.ORI_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC4, REC2, REC1, PARENT, RECT, SCRIPT, FREE, LINK = 0x10e800, 0x10e900, 0x10ea00, 0x10eb00, 0x10ec40, 0x10ec80, 0x10ed00, 0x10ec00
RING_BLOCKS = set(B.RING_BLOCKS)
SCRIPT_WORDS = B.SCRIPT_WORDS


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xB4B5)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    bank = []
    for a in range(0x20003c, 0x2000a0, 4):
        if a == 0x20008c:
            bank.append(l(0x2a0000))
        elif a == 0x200090:
            bank.append(l(0x2a0100))
        else:
            bank.append(l(srng.choice((0x00290000 | srng.getrandbits(15) << 1, srng.getrandbits(32)))))
    bank = b''.join(bank)                                                                                                            # 20003c..2000a0
    sin = b''.join(w(srng.choice((0, 1, 0x100, 0xff00, 0x7fff, 0x8000, 0xffff, srng.getrandbits(16), srng.getrandbits(9) - 256))) for _ in range(320))
    ptr1 = l(srng.getrandbits(19) << 1)                                                                                             # 2a000c
    ptr2 = l(srng.getrandbits(19) << 1)                                                                                             # 2a0130
    low = bytearray(srng.getrandbits(8) for _ in range(0x80))                                                                        # 0000..0080 (vectors view)
    low[0x61] = 0x80                                                                                                                 # BYTE 61: bit 7 = 1
    assert len(bank) == 0x64 and len(sin) == 0x280
    return [(0x0, bytes(low)), (0x20003c, bank), (0x2a000c, ptr1), (0x2a0130, ptr2), (0x4411e, sin)]


SYN = synthetic()


def load_program():
    program = bytearray(ob.load_rom())
    assert hashlib.sha256(program).hexdigest() == '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    for a, b in SYN:
        program[a:a + len(b)] = b
    return bytes(program)


PROGRAM = load_program()
FIXED = (ctypes.c_ubyte * 0x100000).from_buffer_copy(PROGRAM[:0x100000])


def syn_ok(address, size):
    return any(a <= address and address + size <= a + len(b) for a, b in SYN)


# consumer -> (C clear successor, C set successor)
SUCC = {0x22fd4: (0x22fde, 0x22fd8), 0x233ea: (0x233f4, 0x233ee), 0x234c6: (0x234d0, 0x234ca), 0x237be: (0x237c8, 0x237c2), 0x23c4a: (0x23c54, 0x23c4e),
        0x28268: (0x282de, 0x2826c), 0x2b746: (0x2b774, 0x2b74a), 0x2b788: (0x2b7b6, 0x2b78c), 0xe7a2c: (0xe7a3e, 0xe7a30)}
assert set(SUCC) == CONS_SET


class Ram(object):
    def __init__(self):
        self.b = bytearray(65536)
        self.puts = []

    def put(self, a, n, v):
        assert 0x100000 <= a and a + n <= 0x110000, hex(a)
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
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0))
    out = dict(stop=None)
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
    if out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.ports or m.bank != 0x200000:
        return None
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
    if p in CONS_SET:
        return c
    if p in ORI_SET:
        return 2
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
VB = (0, 1, 2, 3, 4, 7, 8, 0x10, 0x11, 0x20, 0x7f, 0x80, 0x81, 0xc0, 0xe0, 0xe1, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0x10, 0x30, 0x38, 0x80, 0xff, 0x100, 0x13f, 0x140, 0x1ff, 0x200, 0x23f, 0x240, 0xfff, 0x1000, 0x7fff, 0x8000, 0x8001, 0xffe0,
      0xfff0, 0xffff)
VL = (0, 1, 0x7fff, 0x10000, 0x170000, 0x178001, 0x180000, 0x7fffffff, 0x80000000, 0xfff80000, 0xffffffff, 0x123456, 0x1400000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc}


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg'):
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


# stack words popped by the entered block (declared below A7 = 10ef00): 283cc A1, 2840a four LONGs, 28456 four LONGs + one WORD, e7500 A0
def pops_of(rng, s):
    if s == 0x283cc:
        return [(4, NODE + 0x78 + 8 * rng.randrange(7))]
    if s == 0x2840a:
        return [(4, rng.getrandbits(32)) for _ in range(4)]
    if s == 0x28456:
        return [(4, rng.getrandbits(32)) for _ in range(4)] + [(2, rng.choice((0, 8, 0x30, 0x8000, 0xfff8)))]
    if s == 0xe7500:
        return [(4, rng.choice((CHILD, REC1, 0x12345678)))]
    return []


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=CHILD, a1=REC1,
                a2=rng.choice((REC2, 0xa2a2a2a2)), a3=0xa3a3a3a3, a4=REC4, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 4, 8, 0x10, 0x30, 0x40, 0x7f, 0x80, 0xff, 0x100, 0x10000, 0xffff, 0x8000, 0x10101, 0x123480))
    if rng.random() < 0.3:
        regs['d1'] = rng.choice((0, 0x7f, 0x80, 0xff, 0xe0, 0xe1, 0x1234ff80))
    if s in RING_BLOCKS:
        regs['a1'] = NODE + 0x78 + 8 * rng.randrange(7)
    if s in (0x28366, 0x2845c, 0x28468, 0x2834e) or rng.random() < 0.2:
        regs['d7'] = (regs['d7'] & 0xffff0000) | (8 * rng.randrange(7))
    if s == 0x4964e and rng.random() < 0.4:
        regs['a0'] = 0
    if s == 0xe74f8:
        regs['a0'] = SCRIPT
        r.put(SCRIPT, 2, rng.choice(SCRIPT_WORDS))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: REC2, 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG and the node links are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0x8, 4, LINK)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(LINK + 0x10, 2, rand_val(rng, 2))
    r.put(NODE + 0x10, 2, rand_val(rng, 2))
    r.put(PARENT, 4, rng.choice((0x270e, 0x2b99c, 0)))
    for d in (0x36, 0x3a):
        r.put(PARENT + d, 4, rand_val(rng, 4))
    r.put(CHILD + 0x56, 4, rng.choice((0, RECT, RECT)))
    for d in range(0, 8, 2):
        r.put(RECT + d, 2, rand_val(rng, 2))
    pops = pops_of(rng, s)
    depth = sum(n for n, v in pops)
    at = SP - depth
    for n, v in pops:
        r.put(at, n, v)
        at += n
    regs['a7'] = SP - depth
    if hint:
        for a, n, v in hint.get('puts', []):
            r.put(a, n, v)
        regs.update(hint.get('regs', {}))
    return r, regs


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p)


def hints(s):
    h = []
    N = lambda o, n, vals: [dict(puts=[(NODE + o, n, v)]) for v in vals]
    R = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if s == 0x22f7a:
        h += N(0x8a, 1, (0, 1, 0x80, 0xff))
    if s == 0x23360:
        h += N(0x84, 1, (0, 1, 2, 0x81, 0xff))
    if s in (0x2339c, 0x2345e):
        h += N(0x82, 1, (0, 1, 0x7f, 0x80, 0xff))
    if s in (0x233be, 0x23480):
        h += N(0x82, 1, (0, 1, 0x80, 0x81))
    if s in (0x233ac, 0x2346e, 0x234d0):
        h += N(0x15, 1, (0, 0x7f, 0x80, 0xff))
    if s in (0x233f4, 0x234e0, 0x23bb6):
        h += N(0x42, 2, (0, 0x13f, 0x140, 0x8000, 0xffff))
    if s in (0x23406, 0x234f2, 0x23bc2):
        h += N(0x46, 2, (0, 0xff, 0x100, 0x1ff, 0x200, 0x23f, 0x240, 0x80ff))
    if s == 0x234a0:
        h += N(0x7c, 4, (0, 0x2303a, 0x80000000, 1))
    if s == 0x234b0:
        h += R('d0', (0, 1, 0x10000, 0x8000, 0xffff0000))
    if s == 0x23508:
        h += N(0x12, 1, (0, 0x7f, 0x80, 0xd6, 0xfe, 0xff))
    if s == 0x23516:
        h += R('d1', (0, 0x1f, 0x7f, 0x80, 0xa0, 0xa1, 0xd5, 0xd6, 0xd7, 0xdf, 0xe0, 0xfe, 0x123456a1, 0xffffff00))
    if s in (0x23aee, 0xe7a0e):
        h += R('d0', (0, 1, 0x80, 0xff, 0x100, 0x8000, 0x10000))
    if s == 0x23af4:
        h += N(0x15, 1, (0, 0x20, 0xdf, 0xff))
    if s == 0x23afe:
        h += N(0x84, 4, (0, 0x170000, 0x178000, 0x178001, 0x180000, 0xffff8001, 0x7fffffff, 0xffff8000))
    if s == 0x23b18:
        h += N(0x82, 2, (0, 1, 0x8000, 0xffff))
    if s == 0x23b26:
        h += R('d0', (0, 1, 0x8000, 0x12340000))
    if s == 0x23b36:
        h += R('d0', (0, 1, 0x80, 0x100))
    if s == 0x23b44:
        h += [dict(regs=dict(d0=d), puts=[(NODE + 0x78, 2, w)]) for d, w in ((0, 0), (0x7f, 0x7f80), (0x80, 0x1234), (0xff, 0xff7f), (0x1234ff, 0x8000),
                                                                           (0x81, 0x0081))]
    if s == 0x23b56:
        h += [dict(regs=dict(d7=d), puts=[(NODE + 0x7e, 4, a), (NODE + 0x84, 4, b), (NODE + 0x64, 4, c)]) for d, a, b, c in (
            (0, 0, 0, 0), (0x80000000, 0x7fffffff, 0x180000, 0), (0xfffffff8, 0x10, 0, 0x180000), (0x12345678, 0x87654321, 0x7fffffff, 0x80000000))]
    if s == 0x23b84:
        h += [dict(regs=dict(d0=a, d1=b), puts=[(NODE + 0x36, 4, c), (NODE + 0x3a, 4, d), (NODE + 0x78, 2, w)]) for a, b, c, d, w in (
            (0, 0, 0, 0, 0), (0x80000000, 0x7fffffff, 0x7fffffff, 0x80000000, 0xffff), (0x10, 0xfffffff0, 0x20, 0x20, 0x7f80), (1, 2, 3, 4, 0x8000))]
    if s == 0x23aa0:
        h += N(0x3a, 4, (0, 1, 0x40, 0x80000000, 0xffffffc0, 0x7fffffff))
    if s == 0x23ad0:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0x7fffffff, 0x80000000), (1, 0xffffffff))]
    if s == 0x2826c:
        h += [dict(puts=[(CHILD + 0x61, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)] + [dict(regs=dict(a0=0))]
    if s == 0x28276:
        h += [dict(puts=[(CHILD + 0x63, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)]
    if s == 0x282a8:
        h += [dict(regs=dict(d0=a, d1=b), puts=[(PARENT + 0x36, 4, x), (PARENT + 0x3a, 4, y)]) for a, b, x, y in (
            (0, 0, 0, 0), (0x7fff, 0x8000, 0x80000000, 0x7fffffff), (0xffff, 1, 0xffffffff, 0x80000001))]
    if s in (0x282bc, 0x282c6):
        h += R('d0' if s == 0x282bc else 'd1', (0x80000000, 0xffffffff, 1, 0))
    if s == 0x282c8:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (1, 0), (0, 1), (0x80000000, 0x7fffffff), (0x7fffffff, 0x80000000), (5, 5))]
    if s == 0x282d0:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x7fffffff, 0x7fffffff), (0xfff00000, 0x10000), (0x12345678, 0x9abcdef0), (0xfff0, 0x8))]
    if s == 0x282de:
        h += N(0x62, 1, (0, 1, 2, 0x80, 0xff))
    if s == 0x282e6:
        h += N(0xb0, 2, (0, 7, 8, 0x30, 0x8000, 0xffff))
    if s == 0x282f4:
        h += R('d0', (0xfff8, 0xffff, 0x12340000))
    if s == 0x282f8:
        h += [dict(regs=dict(d0=d), puts=[(NODE + 0x61, 1, f)]) for d, f in ((0, 0), (0x30, 0x80), (8, 0x7f), (0x18, 0xff))]
    if s in (0x28366, 0x2845c):
        h += R('d7', (0, 8, 0x30, 0x12340030, 0x37, 0x38, 0xffff))
    if s == 0x28366:
        h += [dict(regs=dict(d7=0xabcd0000 | (8 * k)), puts=[(NODE + 0x78 + 8 * k + 6, 1, v)]) for k, v in ((0, 1), (3, 0x80), (6, 0xff))]
    if s == 0x28468:
        h += [dict(regs=dict(d7=d), puts=[(NODE + 0xb0, 2, w)]) for d, w in ((0, 0), (8, 0), (0x10008, 8), (0x30, 0x30), (8, 0x108), (0x30, 0x130))]
    if s == 0x28470:
        h += N(0x63, 1, (0, 1, 0x80, 0xff))
    if s == 0x28478:
        h += N(0x61, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0x28376:
        h += [dict(regs=dict(d0=a, d1=b, d2=cc, d3=d, a1=NODE + 0x78), puts=[(NODE + 0x78, 1, k), (NODE + 0x7c, 2, rr), (NODE + 0x7e, 1, n)]) for a, b, cc, d, k, rr, n in (
            (0, 0, 0, 0, 0, 0, 1), (0x10000, 0, 0, 0, 0x40, 0x100, 2), (0x7fffffff, 0x80000000, 0, 0, 0x80, 0x1000, 0x11),
            (0x12345678, 0x9abcdef0, 0x12340000, 0x9abc0000, 0xff, 0x8000, 0x80), (0x40000, 0x40000, 0x40000, 0x40000, 0x7f, 0x7fff, 0))]
    if s == 0x283cc:
        h += R('d0', (0, 0x7f, 0x80, 0xff, 0x8000))
    if s == 0x283d4:
        h += [dict(regs=dict(d0=d, a1=NODE + 0x78), puts=[(NODE + 0x7f, 1, a), (NODE + 0x7c, 2, ww), (NODE + 0x64, 1, b)]) for d, a, b, ww in (
            (0, 0, 0, 0), (0x8000, 0x80, 0x80, 0xfff), (0x7fff, 0xff, 1, 0xc00), (0xffff, 0x7f, 0x80, 0x1000), (0x1234, 0xf0, 0x10, 0x8000),
            (0x10, 0x7f, 0x81, 0xbff))]
    if s == 0x2840a:
        h += [dict(regs=dict(d4=ww, a1=NODE + 0x78), puts=[(NODE + 0x78, 1, k)]) for ww, k in ((0, 0), (0x1000, 0x40), (0xfff, 0x80), (0x8000, 0xff))]
    if s == 0x28456:
        h += [dict(regs=dict(d7=0x12345678))]
    if s == 0x2b726:
        h += N(0x15, 1, (0, 1, 0xfe, 0xff))
    if s == 0x4439e:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x7fff, 0x40), (0x8000, 0x80), (0xffff, 0xff), (0x12340100, 0xffffff7f), (0x80, 0x7f))]
    if s == 0x4963a:
        h += [dict(regs=dict(d0=a, d1=b), puts=[(NODE + 0x42, 2, c), (NODE + 0x46, 2, d)]) for a, b, c, d in ((0, 0, 1, 0xffff), (0x8000, 0x7fff, 0x7fff, 0x8000))]
    if s == 0x49648:
        h += R('d0', (0x100, 0x1ff, 0x8080, 0x12345678, 0x7f, 0x80))
    if s == 0x4964e:
        h += R('a0', (0, CHILD, 0x80000000, 1 << 24))
    if s == 0x49662:
        h += [dict(puts=[(CHILD + 0x56, 4, v)]) for v in (0, RECT, 0x10000)]
    if s == 0x49676:
        h += [dict(puts=[(CHILD + 0x15, 1, f), (REC1 + 4, 2, ww), (REC1 + 6, 2, ww ^ 0xffff)]) for f, ww in ((0, 0), (1, 0x8000), (2, 0x7fff), (3, 0xffff), (0xfc, 1))]
    if s in (0x49692, 0x4969e):
        h += R('d2' if s == 0x49692 else 'd3', (0, 1, 0x8000, 0xffff, 0x12340001))
    if s == 0x496a0:
        h += [dict(regs=dict(d0=a, d1=b, d2=cc, d3=d)) for a, b, cc, d in ((0x7fff, 0x8000, 1, 0xffff), (0x1234ffff, 0xffff0001, 0xffff0001, 0x0000ffff))]
    if s == 0xe74f8:
        h += [dict(puts=[(SCRIPT, 2, v)]) for v in SCRIPT_WORDS]
    if s == 0xe751c:
        h += R('a0', (CHILD, REC1))
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
            if nxt in CONS_SET or (inr(nxt) and nxt not in STARTS_SET):
                continue
            key = (nxt, 'h%d' % t) if hint else nxt
            if key in kept:
                continue
            if nxt == s:
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


PATH_ENTRIES = (0x22f7a, 0x23360, 0x2339c, 0x233be, 0x233f4, 0x23406, 0x2344a, 0x2345e, 0x23480, 0x234a0, 0x234b0, 0x234d0, 0x234e0, 0x234f2, 0x23508,
                0x23516, 0x23aee, 0x23af4, 0x23afe, 0x23b18, 0x23b36, 0x23b44, 0x23bb6, 0x23c30, 0x2826c, 0x282a8, 0x282c8, 0x282de, 0x282e6, 0x282f8,
                0x2834e, 0x28366, 0x28376, 0x283cc, 0x283d4, 0x28456, 0x2845c, 0x28468, 0x28470, 0x2b726, 0x2b74a, 0x2b78c, 0x2b7b8, 0x4964e, 0x49662,
                0x49676, 0xe74f8, 0xe7500, 0xe7504, 0xe7508, 0xe7a0e, 0xe7a3a, 0x23ad0, 0x23394, 0xe79f8)


def gen_paths(rng):
    fl = []
    for b in STARTS:
        fl += fields(b)
    fl = sorted(set(fl))
    for s in PATH_ENTRIES:
        kept = {}
        for t in range(200):
            carry = rng.choice((0, 1, 2))
            r, regs = world(rng, fl, s)
            o = native(r.b, regs, s, carry, path_stop)
            if o is None:
                continue
            ex = [p for p in o['trace'] if p in STARTS_SET]
            if any(p in CONS_SET for p in ex):
                continue
            key = (o['stop'], tuple(ex))
            if key in kept:
                continue
            kept[key] = (r, regs, o, carry, ex)
            if len(kept) >= 4:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o, carry, ex)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=0x10c000, a2=0xa2a2a2a2, a3=0xa3a3a3a3, a4=0xa4a4a4a4, a5=A5, a6=NODE, a7=SP)


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry, 3, o)
    # real producers.  28ae: CMP.W 104ca0.l,D0 (limit) / A0 = 0 -> failure (C Clear, A0 = 100e98); else the free node LONG 104c9c is linked (C Set).
    for entry, cons in ((0x2b736, 0x2b746), (0x2b778, 0x2b788), (0xe7a1c, 0xe7a2c)):
        clr, st = SUCC[cons]
        for k, (limit, free) in enumerate(((0, FREE), (0x100, FREE), (0xa, FREE), (0x1e, FREE), (0x1f, FREE), (0x100, 0))):
            r = base_ram()
            r.put(0x104ca0, 2, limit)
            r.put(0x104c9c, 4, free)
            r.put(FREE + 8, 4, 0x10ed80)
            r.put(0x104ca2, 2, 5)
            r.put(NODE + 0x8, 4, LINK)
            r.put(NODE + 0x10, 2, 3)
            r.put(NODE + 0x6a, 1, 0x5a)
            regs = dict(PLAIN)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st))
            if o is None:
                continue
            c = 1 if o['stop'] == clr else 2
            row('chain-%x-28ae-%d' % (entry, k), r, regs, entry, o['stop'], 0, c, 2, o)
    # 288c: MOVEA.L c(A6),A0; A0 = 0 -> ORI Set; CMPI.L #270e,(A0); equal -> C Clear, else ORI Set.  Entry 2825c (BSET.B #7,61(A6); JSR 288c).
    for k, (parent, cb) in enumerate(((0, 0), (PARENT, 0x270e), (PARENT, 0x270f), (PARENT, 0x270d), (PARENT, 0), (PARENT, 0x8000270e))):
        r = base_ram()
        r.put(NODE + 0xc, 4, parent)
        r.put(PARENT, 4, cb)
        regs = dict(PLAIN)
        o = native(r.b, regs, 0x2825c, 0, lambda q, tr: q in (0x282de, 0x2826c))
        assert o is not None, k
        c = 1 if o['stop'] == 0x282de else 2
        assert c == (1 if parent and cb == 0x270e else 2), (k, hex(o['stop']))
        row('chain-2825c-288c-%d' % k, r, regs, 0x2825c, o['stop'], 0, c, 2, o)
    # 49fc6 (the interpreter on ROM scripts): no synthetic world; the consumers 22fd4 233ea 234c6 237be 23c4a have the declared-C rows above and the
    # real-producer chains of the V1 spec / real-ROM differential.


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x10c000, a2=0, a3=0, a4=REC4, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    inside = 'unsupported animation objects b4b PC'

    def err(name, entry, message, fail_pc, carry=0, puts=(), **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects b4b caller requires known carry', cp)
    # odd node / child / script / stack / record: the entry block fails
    err('odd-node-22f7a', 0x22f7a, wodd, 0x22f7a, a6=NODE + 1)
    err('odd-node-233f4', 0x233f4, odd, 0x233f4, a6=NODE + 1)
    err('odd-child-23a5c', 0x23a5c, wodd, 0x23a5c, a0=CHILD + 1)
    err('odd-child-e751c', 0xe751c, wodd, 0xe751c, a0=CHILD + 1)
    err('odd-script-e74f8', 0xe74f8, odd, 0xe74f8, a0=SCRIPT + 1)
    err('odd-stack-28376', 0x28376, odd, 0x28376, a7=SP + 1, a1=NODE + 0x78)
    err('odd-stack-e7500', 0xe7500, odd, 0xe7500, a7=SP + 1)
    err('odd-parent-282a8', 0x282a8, odd, 0x282a8, puts=[(NODE + 0xc, 4, PARENT + 1)])
    err('odd-cell-283d4', 0x283d4, odd, 0x283d4, a1=NODE + 0x79)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('e74f8-script-rom', 0xe74f8, missing, 0xe74f8, a0=0x1000)
    err('2826c-a0-rom', 0x2826c, missing, 0x2826c, a0=0x100)
    err('49662-a0-rom', 0x49662, missing, 0x49662, a0=0x1000)
    # computed e74fc targets (the failing PC is the computed target e7504 + sext(D0.W))
    err('e74f8-target-e7506', 0xe74f8, inside, 0xe7506, a0=SCRIPT, puts=[(SCRIPT, 2, 2)])
    err('e74f8-target-e750a', 0xe74f8, inside, 0xe750a, a0=SCRIPT, puts=[(SCRIPT, 2, 6)])
    err('e74f8-target-e7505', 0xe74f8, 'unaligned animation machine PC', 0xe7505, a0=SCRIPT, puts=[(SCRIPT, 2, 1)])
    err('e74f8-target-e7503', 0xe74f8, 'unaligned animation machine PC', 0xe7503, a0=SCRIPT, puts=[(SCRIPT, 2, 0xffff)])
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   233be (BYTE 82 = 1 -> 0) -> 2339c (<= 0) -> 233c4 pushes the 43e34 return LONG at an odd A7
    err('233be-then-233c4', 0x233be, odd, 0x233c4, a7=SP + 1, puts=[(NODE + 0x82, 1, 1)])
    #   2b7b8 sets BYTE 15 bit 0, then the BSR of 2b7be pushes at an odd A7
    err('2b7b8-then-2b7be', 0x2b7b8, odd, 0x2b7be, a7=SP + 1)
    #   23528 sets D1.B, 2352c stores BYTE 12 / 13, then its RTS pops at an odd A7
    err('23528-then-2352c', 0x23528, odd, 0x2352c, a7=SP + 1)
    #   4964e (A0 = 0) -> 49658 sets D0.W / D1.W, then its RTS pops at an odd A7
    err('4964e-then-49658', 0x4964e, odd, 0x49658, a7=SP + 1, a0=0)
    #   4964e (A0 odd, not 0) -> 49662 reads WORD 42(A0) at an odd address
    err('4964e-then-49662', 0x4964e, odd, 0x49662, a0=CHILD + 1)
    #   282f4 adds 38 to D0.W, then 282f8 writes WORD b0 of an odd node
    err('282f4-then-282f8', 0x282f4, wodd, 0x282f8, a6=NODE + 1)
    #   e7504 BRA -> e750c -> its JSR 28ae push fails at an odd A7
    err('e7504-then-e750c', 0xe7504, odd, 0xe750c, a7=SP + 1)


def main():
    rng = random.Random(0xB4B)
    gen_singles(rng)
    gen_paths(rng)
    gen_consumers(rng)
    gen_errors()
    out = []
    for d in ROWS:
        regs = ','.join('0x%x' % v for v in d['regs'])
        if d['error'] is None:
            outr = ','.join('0x%x' % v for v in d['out'])
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",NULL,0x0,{%s},%d,%d,%dULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'], outr, d['c'],
                                                                                    d['single'], d['digest']))
        else:
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s","%s",0x%x,{0},0,%d,0ULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'], d['error'],
                                                                                   d['fail'], d['single']))
    tables = [BEGIN]
    tables.append('const std::uint32_t STARTS[]={%s};' % ','.join('0x%x' % x for x in STARTS))
    tables.append('const std::uint32_t CONSUMERS[][3]={%s};' % ','.join('{0x%x,0x%x,0x%x}' % (c, SUCC[c][0], SUCC[c][1]) for c in CONSUMERS))
    tables.append('const std::uint32_t ORI_SET[]={%s};' % ','.join('0x%x' % x for x in sorted(ORI_SET)))
    tables.append('const unsigned int EVEN_COUNT=%d;' % sum((hi - lo) // 2 for lo, hi in RANGES))
    tables.append('const Fixture FIXTURES[]={')
    tables += out
    tables.append('};')
    tables.append('const Synthetic SYNTHETIC[]={')
    tables += [' {0x%x,"%s"},' % (a, b.hex()) for a, b in SYN]
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
    print('e74f8 targets', sorted(hex(d['stop']) for d in singles if d['entry'] == 0xe74f8))
    print('chain rows', sorted((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2))
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
