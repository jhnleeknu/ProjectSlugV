"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr3_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
only data areas, never code bytes): the LONG tables ea712..ea732 (ea880 / ea8ae), the boxes 772be..772ce (the A0 of 1ab80 / 1ab02 in the producer
chains), the bank-window LONGs 2000d0 / 2000d4 / 200090 / 20003c / 200080 / 200140 (-> 2a1000 / 2a2000 / 2a3000 / 2a4000 / 2a5000 / 2a6000) with
the LONGs behind them.  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as is a run that lands
inside the unit on a PC that is not a block start, or that takes an exception (DIVU zero divisor: error rows only).
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) = the parent 10eb00, LONG 8(A6) = the sibling 10ec00),
A0 = 10e400, A1 = 10ea00, A5 = 108000 (BYTEs 5e51 / 5e50, WORDs 542e / 5430 of 1abda), the player records 100cb8 / 100da8, seeded BYTE / WORD /
LONG field edits (sign boundaries included), seeded D0-D7, the declared stack values (WORD / LONG) the entered block pops.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a consumer only
            after a block that sets the C itself: ea8e8 -> ea8fc).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP / BRA / BEQ exits, the RTS sentinel) or a consumer
            (ea8e8 -> ea8fc: the modelled Clear of the ANDI).
  single 2  a consumer entered through its real producer (only producers that read RAM / the synthetic bytes; the generator keeps a chain when it
            produced both C values): stop = the consumer's successor; the native branch on the real flags decides it.  The others (49fc6 ROM scripts,
            4c2cc / ea65a terrain, ...) have declared-C rows only (V1 and the real-ROM differential run the real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit; 77170 SCS:
            the BYTE 8a it writes).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C.  The modelled C
of the producers: ea6fc 771d8 Set, ea70a ea8e8 Clear.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr3_test_table.py  (rewrites the generated section in place)
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
import fr3 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr3_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
SET_SET, CLEAR_SET = set(B.SET_SET), set(B.CLEAR_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC1, PARENT, SIBLING = 0x10ea00, 0x10eb00, 0x10ec00
PLAYER1, PLAYER2 = 0x100cb8, 0x100da8
WINDOWS = {0x2000d0: (0x2a1000, (0x18,)), 0x2000d4: (0x2a2000, (0x18,)), 0x200090: (0x2a3000, (0x1c,)), 0x20003c: (0x2a4000, (0x14,)),
           0x200080: (0x2a5000, (0x38, 0x140)), 0x200140: (0x2a6000, (0x4, 0x8))}


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    srng = random.Random(0xF43C)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    tables = b''.join(l(v) for v in (0x10fe10, 0x10fe14, 0x10fe18, 0x10fe1c, 0x10fe20, 0x10fe24, 0x10fe28, 0x10fe2c))   # ea712..ea732
    boxes = b''.join(w(v) for v in (0xfff0, 0xffe0, 0x20, 0x40, 0xfff8, 0xfff0, 0x10, 0x20))                          # 772be / 772c6: WORD x, y, w, h
    out = [(0xea712, tables), (0x772be, boxes)]
    for win in sorted(WINDOWS):
        dest, disps = WINDOWS[win]
        out.append((win, l(dest)))
        for d in disps:
            out.append((dest + d, l(srng.getrandbits(19) << 1)))
    return out


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


# consumer -> (C clear successor, C set successor); 77170 (SCS.B 8a(A6)) has one successor, its C shows in BYTE 8a
SUCC = {0x70e12: (0x70e26, 0x70e16), 0x7704a: (0x77054, 0x7704e), 0x77264: (0x7726e, 0x77268), 0xbc470: (0xbc47a, 0xbc474), 0xbca1a: (0xbca2a, 0xbca1e),
        0xea8fc: (0xea906, 0xea900), 0x7705e: (0x77068, 0x77062), 0x77158: (0x77162, 0x7715c), 0x77278: (0x77282, 0x7727c), 0x770bc: (0x770c2, 0x770c0),
        0x77170: (0x77174, 0x77174), 0x771ca: (0x771dc, 0x771ce), 0xc5412: (0xc5430, 0xc5416), 0xc5682: (0xc5694, 0xc5686), 0xea6b8: (0xea70a, 0xea6bc),
        0xea6cc: (0xea70a, 0xea6d0), 0xea86e: (0xea89e, 0xea872)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / synthetic bytes and both C values occur
CHAIN_CANDIDATES = ((0x77054, 0x7705e), (0x7714e, 0x77158), (0x7726e, 0x77278), (0x770b6, 0x770bc), (0x7716a, 0x77170), (0x771ba, 0x771ca),
                    (0xc540c, 0xc5412), (0xc567c, 0xc5682), (0xea6b0, 0xea6b8), (0xea6bc, 0xea6cc), (0xea860, 0xea86e), (0x70e0c, 0x70e12))


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
            out['bad'] = True                       # an odd PC or a computed landing inside a block of the unit: the C++ rejects it (error rows)
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
        return None                                 # FR3 writes no PVC port
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
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x20, 0x37, 0x38, 0x39, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x3f, 0x40, 0x41, 0x7f, 0x80, 0xff, 0x100, 0x2000, 0x7fff, 0x8000, 0x8001, 0xe000, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x10, 0x7fff, 0x8000, 0xffff, 0x10000, 0x10001, 0x30000, 0x7fffffff, 0x80000000, 0xfff00000, 0xffff0000, 0xffffac60, 0xffffffff,
      0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22, 0x76}
STACK = dict(B.STACK)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'scs'):
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, REC1, PLAYER1)),
                a1=rng.choice((REC1, CHILD)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=CHILD, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 0x3f, 0x40, 0x41, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340040, 0x80000000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x8000, 0xffff, 0x123456a5))
    if rng.random() < 0.4:
        regs['d3'] = rng.choice((0, 1, 2, 3, 0x7fff, 0x8000, 0xffff, 0x12340002))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG, the node links and the table index WORD 76 are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x76, 2, rng.choice((0, 1, 2, 3, 3, 0, 0x8000, 0xffff)) if s not in (0xea880, 0xea8ae) else rng.choice((0, 1, 2, 3)))
    for off in (0x62, 0x63, 0x15):
        r.put(PARENT + off, 1, rand_val(rng, 1))
    r.put(PARENT + 0x42, 2, rand_val(rng, 2))
    for a in (PLAYER1, PLAYER2, CHILD, REC1):
        r.put(a + 0x42, 2, rand_val(rng, 2))
        r.put(a + 0x46, 2, rand_val(rng, 2))
        r.put(a + 0x15, 1, rand_val(rng, 1))
        r.put(a + 0x62, 1, rand_val(rng, 1))
        r.put(a + 0x63, 1, rand_val(rng, 1))
    for a in (0x10de51, 0x10de50):
        r.put(a, 1, rand_val(rng, 1))
    pops = []
    for size, kind in STACK.get(s, ()):
        n = 4 if size == 'L' else 2
        v = {'node': rng.choice((CHILD, REC1, PLAYER1)), 'a6': NODE, 'small': rng.choice((0, 1, 2, 3)), 'any': rand_val(rng, n)}[kind]
        pops.append((n, v))
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
        if hint.get('stack'):
            at = regs['a7']
            for n, v in hint['stack']:
                r.put(at, n, v)
                at += n
    return r, regs


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x28ae, 0x2986, 0x2a00, 0x8ebe, 0x8ff4, 0x1ab02, 0x1ab80, 0x1abda, 0x43e08, 0x43e34, 0x43ea4, 0x443d2, 0x44602, 0x490ba, 0x491c4,
                 0x49290, 0x492d0, 0x496c2, 0x4970a, 0x49f8c, 0x49fc6, 0x4ae4a, 0x4b54e, 0x4be06, 0x4be2c, 0x4be34, 0x4bfa4, 0x4c0ac, 0x4c2cc, 0x71c90,
                 0x72dd2, 0x76f98, 0xc6a96, 0xd1d08, 0xea65a, 0xea762, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer (ea8e8 -> ea8fc: the modelled Clear of ea8e8)


def hints(s):
    h = []
    N = lambda o, n, vals: [dict(puts=[(NODE + o, n, v)]) for v in vals]
    R = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if s in (0x70d92,):
        h += N(0x9c, 2, (0, 1, 0x8000))
    if s in (0x70dfc, 0xc53ec, 0xc564e):
        h += N(0x15, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0x770c2:
        h += [dict(regs=dict(a0=CHILD, d0=0x12345678), puts=[(CHILD + 0x42, 2, a), (NODE + 0x42, 2, b), (NODE + 0x15, 1, f)]) for a, b in
              ((0x10, 0), (0, 0x10), (0x8000, 0), (0x7fff, 0xffff)) for f in (0, 1)]
    if s in (0x770d4, 0x770f6):
        h += R('d0', (0, 1, 0x8000, 0x12340040))
    if s == 0x770d6:
        h += [dict(regs=dict(d0=d, d2=0xabcd0000), stack=[(2, v)]) for d, v in ((0x12340040, 0x40), (0x12340041, 0x40), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0))]
    if s == 0x770de:
        h += [dict(regs=dict(d0=0x12345678, d2=0xabcd8001))]
    if s == 0x770e0:
        h += R('d0', (0x3f, 0x40, 0x41, 0x8000, 0x7fff, 0xffff, 0x1234003f))
    if s == 0x770e8:
        h += R('d0', (0x12345678,))
    if s == 0x770ec:
        h += N(0x15, 1, (0, 1, 0xfe))
    if s == 0x770f8:
        h += [dict(regs=dict(a0=CHILD, d1=0x12345678, d3=0x9abc0000), puts=[(CHILD + 0x46, 2, a), (NODE + 0x46, 2, b), (NODE + 0x7a, 2, t)]) for a, b, t in
              ((0, 0x10, 5), (0xfff0, 0, 0x8000), (0x7ff8, 0x8000, 1))]
    if s == 0x77114:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, d2=0xffffac60), puts=[(NODE + 0x15, 1, f), (NODE + 0x89, 1, 0xff)]) for f in (0, 1, 0xff)]
    if s == 0x77138:
        h += [dict(puts=[(NODE + 0x7e, 4, a), (NODE + 0x36, 4, b), (NODE + 0x82, 4, c), (NODE + 0x3a, 4, d)]) for a, b, c, d in
              ((0, 0x7fffffff, 0xffffac60, 0x80000000), (1, 0xffffffff, 0x10000, 0xffff0000))]
    if s in (0x77162, 0x7717e):
        h += N(0x8a, 1, (0, 1, 0xff))
    if s == 0x77174:
        h += N(0x15, 1, (0, 0x20, 0xdf, 0xff))
    if s == 0x7719e:
        h += R('d0', (0, 1, 0x10000, 0xffff0000, 0x12340000))
    if s == 0x771b0:
        h += N(0x89, 1, (0, 0x37, 0x38, 0x39, 0xff))
    if s == 0x771ce:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0))]
    if s == 0x77284:
        h += [dict(puts=[(NODE + 0x36, 4, a), (NODE + 0x3a, 4, b)]) for a, b in ((0x80000000, 0x7fffffff), (0xfff00000, 0x000fffff), (0x1000, 0xffffefff))]
    if s == 0x77298:
        h += R('d0', (0x123456ff, 0x80, 0x7, 0xfffffff8))
    if s in (0x7709e, 0xbca1e):
        h += N(0x15, 1, (0, 1, 8, 0xf7, 0xfe, 0xff))
    if s in (0xbc404, 0xbc93c, 0x76ff2, 0x7706a, 0x77206, 0xc5370, 0xea69c, 0xea85a, 0xd0fec):
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d7=0x55667788))]
    if s == 0xbc97e:
        h += [dict(puts=[(PARENT + 0x42, 2, a), (NODE + 0x42, 2, b)]) for a, b in ((0x10, 0x10), (0x0f, 0x10), (0x8000, 0x7fff), (0x7fff, 0x8000))]
    if s in (0xbc98e, 0xbc9a2):
        h += N(0x15, 1, (0, 1, 0xfe, 0xff))
    if s in (0xbc9b2, 0xbc9c8):
        h += [dict(regs=dict(a0=PARENT), puts=[(PARENT + 0x63, 1, v), (PARENT + 0x62, 1, w)]) for v in (0, 1, 0x80) for w in (0, 1)]
    if s in (0xbc9ba, 0xbc9d0, 0xc538e):
        h += N(0x76, 2, (0, 1, 0x8000, 0xffff))
    if s == 0xc53a2:
        h += [dict(regs=dict(d0=d), puts=[(NODE + 0x2e, 2, a), (NODE + 0x7a, 2, b)]) for d in (0x12340001, 0x8000, 0x7fff, 0xffff) for a, b in ((0x10, 0x10), (0x11, 0x10), (0x8000, 0x7fff))]
    if s == 0xc53b6:
        h += N(0x86, 4, (0, 1, 0x80000000, 0xffffff00))
    if s == 0xc5416:
        h += N(0x61, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0xc5686:
        h += [dict(puts=[(NODE + 0x5e, 1, 0xff), (NODE + 0x5f, 1, 0xff)])]    # CLR.B 5e(A6) clears 5e only, not the neighbour 5f
    if s == 0xc566e:
        h += N(0x82, 2, (0, 1, 0x8000))
    if s == 0xc561a:
        h += N(0x7e, 2, (0, 0x8000, 0xffff))
    if s == 0xd0fec:
        h += R('d2', (0, 1, 0x7fffffff, 0x80000000, 0xffffac60, 0xffffffff))
    if s == 0xd0ff2:
        h += R('d2', (0x80000000, 0xffffffff, 1))
    if s == 0xd0ff4:
        h += R('d3', (0, 1, 2, 3, 0x7fff, 0x8000, 0xffff, 0x12340001, 0x12340002))
    if s == 0xd0ffc:
        h += R('d3', (0x12345678,))
    if s == 0xd1000:
        h += [dict(regs=dict(d0=a, d1=b, d2=c, d3=d)) for a, b, c, d in ((0x12348000, 0xabcd7fff, 0x5555ac60, 0x77770002), (0x7fff, 0xffff, 0xffff0001, 0x7fff),
                                                                       (0xffff, 0x8000, 0x00010001, 3), (0x1234, 0x5678, 0x89abcdef, 0x8000),
                                                                       (0x00010000, 0xffff0000, 0x0000ffff, 0x0001ffff), (5, 7, 0x00030004, 0xffff0001))]
        h += [dict(regs=dict(d3=d, d0=0x7fff, d1=0x8001), stack=[(4, v)]) for d, v in ((2, 0x80000000), (5, 0x7fffffff))]
    if s in (0xd1022, 0xd1024):
        h += [dict(regs=dict(d1=a, d3=b)) for a, b in ((0, 1), (0x80000000, 0x7fffffff), (0x12345678, 0x80000000))]
    if s == 0xd1028:
        h += [dict(regs=dict(d0=a, d1=b, d3=c)) for a, b, c in ((0x12348000, 0xabcd7fff, 0x55555580), (0, 0xffffffff, 0x7f), (0x7fff, 0x8000, 0xff))]
    if s == 0xd1036:
        h += [dict(regs=dict(d0=a, d1=b), stack=[(2, x), (2, y)]) for a, b, x, y in ((0x80000000, 0x7fffffff, 0x8000, 0x7fff), (0x12345678, 0xffffff00, 0, 0xffff),
                                                                                   (0x100, 0xffffff7f, 1, 0x8000))]
    if s == 0xd1048:
        h += R('d0', (0x12340000,))
    if s == 0xd104c:
        h += [dict(regs=dict(d2=a, d3=b, d0=c, d1=d)) for a, b, c, d in ((0x12348000, 0xabcd7fff, 0x10000, 0x7fff), (0xffff, 0x1, 0xffffffff, 0x8000), (0x7fff, 0x8000, 1, 0))]
    if s in (0xd105e, 0xd106e):
        h += [dict(regs=dict(d7=a, d1=b, d2=c, d3=d, d0=e)) for a, b, c, d, e in ((0x80000001, 0x8000, 0x7fff, 0x12345678, 0x10000), (0x7fffffff, 0xffff, 0x8000, 0xffffffff, 3),
                                                                               (1, 0x12347fff, 0xabcd8000, 0x80000000, 0xffff))]
    if s == 0xd107c:
        h += [dict(regs=dict(d4=0x12345678, d7=0x9abcdef0), stack=[(4, a), (4, b)]) for a, b in ((0x00ffffff, 0xff000001), (0x80000000, 0x7fffffff))]
    if s == 0xd108a:
        h += [dict(regs=dict(d0=a, d7=b, d1=c)) for a, b, c in ((0x80000000, 0x7fffffff, 0x12345600), (0x00010000, 0x00050000, 0x123456ff), (0x10003, 0x80000000, 0),
                                                              (0xffff0002, 0xfffffffe, 0x80), (3, 0x100, 0xff))]
    if s in (0xd1096, 0xd1098, 0xd109e):
        h += [dict(regs=dict(d0=a, d7=b, d1=c)) for a, b, c in ((0x80000000, 0x80000000, 0x123456ff), (1, 0x7fffffff, 0x12345600), (0xffffffff, 0xffffffff, 0x80))]
    if s in (0xd10a6, 0xd10ac):
        h += [dict(regs=dict(d1=c, d7=b)) for b, c in ((5, 0xffffff00), (5, 0x12345601), (0x80000000, 0xff))]
    if s in (0xd10b4, 0xd10bc):
        h += [dict(regs=dict(d0=a, d7=b, d6=0x12345678)) for a, b in ((1, 0xffffffff), (3, 0x12345678), (0xffff, 0xfffeffff), (0x10003, 0x00030005),
                                                                    (0x7fff, 0x80000000), (0x12340002, 0x55555555))]
    if s == 0xea6b0:
        h += R('d2', (0x12340001, 0xffff, 0x8000))
    if s == 0xea6bc:
        h += [dict(regs=dict(a0=0x12345678, d7=0xffffffff), puts=[(NODE + 0x42, 4, a), (NODE + 0x46, 4, b)]) for a, b in ((0x80000000, 0x7fffffff), (0x100000, 0x2000000))]
    if s == 0xea6d0:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, a0=CHILD))]
    if s == 0xea6ea:
        h += [dict(regs=dict(a0=CHILD, a1=REC1), stack=[(4, 0x11112222), (4, 0x33334444), (4, PARENT), (2, 0x8001)])]
    if s == 0xea6fc:
        h += [dict(regs=dict(a0=CHILD + 0x2e), stack=[(2, v)]) for v in (0x8001, 0x7fff)]
        h += [dict(regs=dict(a0=0x1fff2e), stack=[(2, 0x1234)])]             # LEA -2e(A0) in the upper RAM mirror (a zero-extended ffd2 leaves RAM)
    if s == 0xea70a:
        h += [dict(stack=[(2, 0x1234)])]
    if s == 0xea860:
        h += N(0x32, 2, (0, 0x7fff, 0xffff))
    if s in (0xea880, 0xea8ae):
        h += N(0x76, 2, (0, 1, 2, 3))
    if s == 0xea8a4:
        h += R('d1', (0x12348001, 0xffffffff, 0))
    if s == 0xea878:
        h += R('d1', (0x12345678,))
    if s == 0xea8c8:
        h += N(0x32, 2, (0, 0x8000, 1))
    if s in (0xea8d2, 0xea8e8):
        h += [dict(puts=[(0x10de51, 1, v), (0x10de50, 1, w)]) for v, w in ((0, 0x80), (0x80, 0), (0x7f, 0xff), (0xff, 0x7f))]
        h += [dict(regs=dict(a5=0x1f8000), puts=[(0x10de51, 1, v), (0x10de50, 1, v)]) for v in (0x80, 0x01)]   # A5 in the upper RAM mirror
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


PATH_ENTRIES = (0x70d92, 0x70dfc, 0x76ff2, 0x7703e, 0x7706a, 0x7709e, 0x770c2, 0x770d6, 0x770e0, 0x77138, 0x77162, 0x77174, 0x7718c, 0x7719e, 0x771b0,
                0x77206, 0x77258, 0x77284, 0xbc404, 0xbc93c, 0xbc972, 0xbc97e, 0xbc9b2, 0xbc9e0, 0xc5370, 0xc538e, 0xc53a2, 0xc53ec, 0xc561a, 0xc564e,
                0xc566e, 0xc5686, 0xd0fec, 0xd0ff4, 0xd1028, 0xd1036, 0xd108a, 0xd10b4, 0xea69c, 0xea6bc, 0xea6d0, 0xea6ea, 0xea85a, 0xea880, 0xea8ae,
                0xea8c8, 0xea8d2, 0xea8e8)


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
            if any(p in CONS_SET for p in ex) or not allowed(o['stop']):
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
    """A world for a real producer chain (RAM / synthetic producers only)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d7=rng.getrandbits(32)))
    for off in (0x42, 0x46, 0x4e, 0x2e, 0x32):
        r.put(NODE + off, 2, rng.choice((0, 0x10, 0x100, 0x180, 0x200, 0x7fff, 0x8000, rng.getrandbits(16))))
    r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry in (0xea6b0, 0x7716a):                              # 1abda: WORD 5430(A5) = ffff -> ANDI Clear, otherwise CMPI borrow Set
        r.put(A5 + 0x542e, 2, rng.getrandbits(16))
        r.put(A5 + 0x5430, 2, rng.choice((0xffff, 0xffff, 0, 0x100, rng.getrandbits(16))))
    if entry == 0x771ba:                                         # 28ae: the free-node list (RAM)
        pass
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
            if cp == 0x77170:
                assert o['ram'][(NODE + 0x8a) & 0xffff] == (0xff if carry == 2 else 0), carry
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        clr, st = SUCC[cons]
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st) and len(tr) > 0 and cons in tr)
            if o is None or cons not in o['trace']:
                continue
            if cons == 0x77170:
                c = 2 if o['ram'][(NODE + 0x8a) & 0xffff] == 0xff else 1
            else:
                c = 1 if o['stop'] == clr else 2
            if seen.get(c, 0) >= 3:
                continue
            seen[c] = seen.get(c, 0) + 1
            rows.append((k, r, regs, o, c))
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        print('chain %x -> %x: %s' % (entry, cons, dict(seen)))
        if set(seen) != {1, 2}:
            continue                                             # the producer reads ROM data or one C value never occurred: declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, c, 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=0, a3=0, a4=CHILD, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    zero = 'objects fr3 DIVU zero divisor'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr3 caller requires known carry', cp, stop=SUCC[cp][0] if SUCC[cp][0] != cp else STOP)
    # odd node / stack / pointer: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-70d92', 0x70d92, odd, 0x70d92, stop=0x70d9a, a6=NODE + 1)
    err('odd-node-70dee', 0x70dee, wodd, 0x70dee, stop=0x70dfc, a6=NODE + 1)
    err('odd-stack-770d6', 0x770d6, odd, 0x770d6, stop=0x770de, a7=SP + 1)
    err('odd-stack-d1036', 0xd1036, odd, 0xd1036, stop=0xd104c, a7=SP + 1)
    err('odd-stack-ea6ea', 0xea6ea, odd, 0xea6ea, stop=0x43e08, a7=SP + 1)
    err('odd-a0-770c2', 0x770c2, odd, 0x770c2, stop=0x770d4, a0=CHILD + 1)
    err('odd-a0-ea6fc', 0xea6fc, wodd, 0xea6fc, a0=CHILD + 0x2f, a7=SP - 2)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('ea880-table-rom', 0xea880, missing, 0xea880, stop=0x49f8c, puts=[(NODE + 0x76, 2, 0x10)])
    # DIVU zero divisors (C++ only: the original takes the vector 5 exception)
    err('divu-zero-d1000', 0xd1000, zero, 0xd1000, stop=0xd1022, d3=0x12340000, a7=SP - 4, puts=[(SP - 4, 4, 0x12345678)])
    err('divu-zero-d10bc', 0xd10bc, zero, 0xd10bc, d0=0x10000, d7=0x12345678)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   d10b4 (D0 = 10000 != 0) -> d10bc DIVU with D0.W = 0
    err('d10b4-then-d10bc', 0xd10b4, zero, 0xd10bc, d0=0x10000)
    #   d0ff4 (D3.W = 0 < 2) -> d0ffc -> d1000 MOVE.L (A7)+,D2 at an odd A7
    err('d0ff4-then-d1000', 0xd0ff4, odd, 0xd1000, stop=0xd1022, a7=SP + 1)
    #   bc9b2 (BYTE 63(A0) = 0) -> bc9c8 (BYTE 62(A0) != 0) -> bc9de RTS at an odd A7
    err('bc9b2-then-bc9de', 0xbc9b2, odd, 0xbc9de, puts=[(PARENT + 0x62, 1, 1)], a0=PARENT, a7=SP + 1)
    #   7719e (D0.W != 0) -> 771e6 JSR 8ff4 at an odd A7
    err('7719e-then-771e6', 0x7719e, odd, 0x771e6, stop=0x8ff4, d0=1, a7=SP + 1)
    #   770e0 (D0.W = 40) -> 770ec (BYTE 15 bit 0 set) -> 770f8 MOVE.W 46(A0),D1 at an odd A0
    err('770e0-then-770f8', 0x770e0, odd, 0x770f8, stop=0xd0fec, puts=[(NODE + 0x15, 1, 1)], d0=0x40, a0=CHILD + 1)
    #   ea8c8 (WORD 32 -= 1, install ea8d2) -> ea8d2 (5e51 bit 7 set) -> ea8e2 JSR 43e34 at an odd A7
    err('ea8c8-then-ea8e2', 0xea8c8, odd, 0xea8e2, stop=0x43e34, puts=[(0x10de51, 1, 0x80)], a7=SP + 1)


def main():
    rng = random.Random(0xF43B)
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
    tables.append('const std::uint32_t CHAINED[]={%s};' % ','.join('0x%x' % c for e, c in CHAINS))
    tables.append('const std::uint32_t CHAIN_FROM[]={%s};' % ','.join('0x%x' % e for e, c in CHAINS))
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
    print('chains kept', [('%x' % e, '%x' % c) for e, c in CHAINS])
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
