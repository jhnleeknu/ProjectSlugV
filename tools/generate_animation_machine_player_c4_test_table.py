"""Generates the native-oracle tables of engine/tests/animation_machine_player_c4_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the character BYTE table 370c..371e and the two BYTEs 370a / 370b before it
(3766 / 37ca with a negative D2.W; also the WORDs that the sign-extended DIVU index 377a + sext(ff92) reaches), the DIVU WORD table 377a..3786 (373a / 37a2), the record LONG table 1cfce (1cfbe), the LONG tables
4e49e..4e4b2 (4ea24: 4e4a2 + sext(4 x D2.W)) and 4e43e..4e452 (4eafc) with the LONGs 464a2 / 4643e that their negative indices (D.W = 2000 -> 8000)
reach, the (handler LONG, key WORD) list 21b0a (C3 215e6 from 21d92) and the BYTE table 21ba4..21baa (C3 21baa from 21d70).  A native run that reads
any other fixed-ROM or banked byte is dropped (a table index beyond the declared bytes), as is a run that lands inside the unit on a PC that is not a
block start, that takes an exception (DIVU by zero: the C++ error rows) or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 78(A6) := the player node 10eb00
(1bf94 A0), LONG 8c(A6) := the record 10ea00, BYTE 9e(A6) 0..3 in most worlds), A0 = 10e400 / 10e800 / 10e600 / the records 10e900.., A1 = 3650 for
the number loops 371e / 3786 and a handler of the list 21aee for 21c72 (contract decision 2), A4 = 10ea00, A5 = 108000, seeded BYTE / WORD / LONG field
edits (sign boundaries included), seeded D0-D7 (small loop counters in most worlds) and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc4.py
hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'stack' writes at A7).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a computed-jump target).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, computed-jump targets, the RTS sentinel) or a consumer / the Z
            reader 4e77a.
  single 2  a consumer entered through its real producer: kept when both C values occur; the Clear-only chains (the Set side needs a later unit) and
            the Z chain 4e770 -> 4a974 -> 4e77a run as plain fixtures.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch / SCS on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the Z reader 4e77a entered directly: the native SR Z is the Z of the TST.B (A0) it recomputes (A0 one of the four 4a974 bytes).
Every success row records the native video port writes (3c0000 LONGs) as a count and an FNV-1a digest.  Known C is never read from the Unicorn SR
after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the producers: 1ef9a (AND.W) 1be64 4da1c 4f126
Clear, 1be5e 4da20 4f130 Set; 1efb0 keeps the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c4_test_table.py  (rewrites the generated section in place)
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
import pc4 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c4_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREAD = 0x4e77a
CLEAR_SET, SET_SET, PASS_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, LIST, RTAB = 0x10ea00, 0x10eb00, 0x10e600, 0x10e800
RECORDS = (0x10e900, 0x10e940, 0x10e980, 0x10e9c0)  # the records the synthetic LONG table 1cfce points at
LIST_21AEE = tuple(B.LIST_21AEE)
Z_SOURCES = (0x10fdb0, 0x10fdb1, 0x100004, 0x100005)


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def entries(pairs):
    """(handler LONG, key WORD) pairs and the LONG 0 terminator."""
    return b''.join(struct.pack('>IH', h, k) for h, k in pairs) + struct.pack('>I', 0)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x370a, bytes((0x5a, 0xa5))),                                     # 3766: 370c + sext(D2.W) for D2.W = fffe / ffff (negative index)
            (0x370c, bytes((0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x2e, 0x7e))),  # 3766: 370c + D2.W
            (0x377a, words((0, 1, 7, 0x31, 0x300, 0x2000))),                     # 373a: DIVU.W 377a + sext(2 x D5.W) (index 0 = 0: the zero-divide rows)
            (0x1cfce, longs(RECORDS)),                                           # 1cfbe: LONG 1cfce + 4 x BYTE 9e (9e 0..3)
            (0x21b0a, entries(((0x21e3a, 1), (0x21602, 2), (0x21c22, 0x104)))),  # C3 215e6 from 21d92 (21d9e JMP (A1) is C8)
            (0x21ba4, bytes((0x77, 0x33, 0x05, 0x0a, 0x80, 0x01))),              # C3 21bb2: BYTE 21ba6 + sext(WORD 76) (from 21d70)
            (0x4643e, longs((0x10e700,))),                                       # 4eafc: 4e43e + sext(4 x 2000) (negative index)
            (0x464a2, longs((0x10e740,))),                                       # 4ea24: 4e4a2 + sext(4 x 2000) (negative index)
            (0x4e43e, longs((0x10e780, 0x10e784, 0x10e788, 0x10e78c, 0x10e790))),  # 4eafc: 4e43e + 4 x D1.W (0..4)
            (0x4e49e, longs((0x10e7a0, 0x10e7a4, 0x10e7a8, 0x10e7ac, 0x10e7b0)))]  # 4ea24: 4e4a2 + 4 x D2.W (ffff, 0..3)


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


# consumer -> (C clear successor, C set successor); the SCS consumers 4e75e / 4e96c with BYTE 9a / a1 = 0 (zero RAM): clear -> the BEQ target
SUCC = {0x1be50: (0x1be64, 0x1be54), 0x1bf9a: (0x1bf9e, 0x1bfa8), 0x1c058: (0x1c05e, 0x1c05c), 0x1efb4: (0x1efb8, 0x1f126), 0x21d6c: (0x21d70, 0x21f40),
        0x21d74: (0x21d78, 0x21f30), 0x21d9a: (0x21da0, 0x21d9e), 0x21dc8: (0x21dcc, 0x21f4c), 0x4f144: (0x4f148, 0x4f152), 0x4e75e: (0x4e7a2, 0x4e768),
        0x4e96c: (0x4e97a, 0x4e976)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both C values occur
CHAIN_CANDIDATES = ((0x1be4a, 0x1be50), (0x1bf94, 0x1bf9a), (0x1c052, 0x1c058), (0x21d68, 0x21d6c), (0x21d70, 0x21d74), (0x21d92, 0x21d9a),
                    (0x4f13c, 0x4f144), (0x4e758, 0x4e75e), (0x4e962, 0x4e96c))
# the Set side needs a later unit (C5 1cb1a for 1ed34, C5 21c12 for 21be6): Clear-only chains
CLEAR_ONLY_CHAINS = ((0x1ef9a, 0x1efb4), (0x21dc4, 0x21dc8))


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (the SCS consumers: from the BYTE D0 after the SCS, 00 / ff)."""
    tr = o['trace']
    i = tr.index(cons)
    nxt = tr[i + 1] if i + 1 < len(tr) else o['stop']
    if cons in (0x4e75e, 0x4e96c):
        return None                                  # decided by the producer model (chain_c)
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

    def word(self, a):
        return (self.b[a & 0xffff] << 8) | self.b[(a + 1) & 0xffff]

    def long(self, a):
        return (self.word(a) << 16) | self.word(a + 2)


def base_ram():
    r = Ram()
    r.put(SP, 4, STOP)
    r.base = 1
    return r


def canonical_ports(ports):
    """Native port events -> C++ form: one (3c0000, 4, LONG) per MOVE.L D0,3c0000 (a WORD pair 3c0000 / 3c0002 is joined)."""
    out = []
    i = 0
    while i < len(ports):
        a, n, v = ports[i]
        if n == 2 and a == 0x3c0000 and i + 1 < len(ports) and ports[i + 1][0] == 0x3c0002 and ports[i + 1][1] == 2:
            out.append((0x3c0000, 4, (v << 16) | ports[i + 1][2]))
            i += 2
            continue
        out.append((a, n, v))
        i += 1
    return out


PORT_CAP = 48


def native(ram, regs, pc, carry, stopfn, z=False):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0) | (4 if z else 0))
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
        if len(m.ports) > PORT_CAP or len(trace) > 20000:
            out['bad'] = True                       # a WORD loop counter near ffff: too many ports / steps for a table row
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
    if (m.ff8, m.ff9) != (0xa0, 0x1000):
        return None
    ports = canonical_ports([(a, sz, v) for kind, a, sz, v in m.ports])
    if any(a != 0x3c0000 or sz != 4 for a, sz, v in ports) or len(ports) > PORT_CAP:
        return None                                 # C4 writes only the video port LONG 3c0000 (a WORD loop counter near ffff: too many rows' ports)
    return dict(stop=out['stop'], trace=trace, regs=m.regs(), ram=m.ram(), ports=ports)


def fnv_add(h, data):
    for x in data:
        h ^= x
        h = (h * 1099511628211) & 0xffffffffffffffff
    return h


def digest(ram, regs, pc):
    tail = b''.join(struct.pack('>I', regs[k]) for k in KEYS) + struct.pack('>III', pc, 0x200000, 0) + bytes([0])
    return fnv_add(fnv_add(1469598103934665603, ram), tail)


def ports_digest(ports):
    return fnv_add(1469598103934665603, b''.join(struct.pack('>IBI', a, n, v) for a, n, v in ports))


def puts_text(r):
    return ','.join('%x:%s' % (a & 0xffffff, d.hex()) for a, d in r.puts[r.base:])


SCS_SET = {0x4e75e, 0x4e96c}                        # SCS consumers: their CMP.B sets C again, left Unknown (contract decision 5)


def carry_after(p, c):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set)."""
    if p in SCS_SET:
        return 0
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in CLEAR_SET:
        return 1
    if p in SET_SET:
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
        d.update(out=[o['regs'][k] for k in KEYS], digest=digest(o['ram'], o['regs'], o['stop']), pn=len(o['ports']), pd=ports_digest(o['ports']))
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


NUMBER_LOOP = set(range(0x371e, 0x37e2, 2))


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, RTAB, LIST) + RECORDS),
                a1=0x3650 if s in NUMBER_LOOP else (rng.choice(LIST_21AEE) if s == 0x21c72 else CHILD), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=REC,
                a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x22, 0xa2, 0x400, 0xffff, 0x12345678, 0x10000, 0x100, 0xff))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 2, 3, 4, 0x8, 0x40, 0x400, 0xffff, 0x12345678))
    if rng.random() < 0.85:
        regs['d4'] = (regs['d4'] & 0xffff0000) | rng.choice((1, 1, 2, 2, 3, 4, 5, 6, 7))
    if rng.random() < 0.7:
        regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 5, 9, 0xa, 0x10, 0x100, 0x2710))
    if s in (0x3766, 0x37ca) and rng.random() < 0.8:
        regs['d2'] = (regs['d2'] & 0xffff0000) | rng.randrange(0x11)
    if s in (0x373a, 0x37a2) and rng.random() < 0.8:
        regs['d5'] = (regs['d5'] & 0xffff0000) | rng.randrange(1, 6)
        if rng.random() < 0.6:
            regs['d2'] &= 0xffff
    for k in ('d6', 'd7'):
        if rng.random() < 0.6:
            regs[k] = (regs[k] & 0xffff0000) | rng.choice((0, 1, 2, 3, 7, 0xd, 0xe, 0xf, 0x10, 0x28, 0x2800, 0xffff))
    if s in (0x4f1e0, 0x4f210, 0x4f1f4, 0x4f1d8) and rng.random() < 0.8:
        regs['d2'] = (regs['d2'] & 0xffff0000) | rng.randrange(1, 6)
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e)):
            continue                                    # (A6) callback LONG, the node links, the slot LONG 84 and the bounded indices are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links, the player node LONG 78(A6), the record LONG 8c(A6), BYTE 9e 0..3 (the LONG table 1cfce), the C3 slot LONG 84 / indices a0 a9
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x78, 4, rng.choice((PARENT, CHILD)))
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(B.SLOT84_C3))
    r.put(NODE + 0xa0, 1, rng.randrange(9) if rng.random() < 0.7 else rng.choice((0xd, 0xe, 0xf)))
    r.put(NODE + 0xa9, 1, rng.randrange(6))
    r.put(NODE + 0x9e, 1, rng.randrange(4) if rng.random() < 0.9 else rng.choice((4, 0x80, 0xff)))
    for rec in RECORDS:                                                     # the records of the LONG table 1cfce (1d0a2 LONG, 1ef20 / 1ef30 WORDs)
        for i in (0, 0x1c, 0x1e):
            r.put(rec + i, 2 if i else 4, rand_val(rng, 2 if i else 4))
    if rng.random() < 0.6:
        for i in range(0, 0x40, 2):
            if rng.random() < 0.4:
                r.put(RTAB + i, 2, rng.choice((0, 2, 4, 0xd, 0xe, 0xf, 0x8000, 0xffff)))   # RAM WORDs (4f240 with A0 = 10e800)
    r.put(0x10dddc, 2, rng.choice((0, 3, 0xd, 0xe, 0xf, 0x8000)))           # 4f22c: the WORDs 10dddc / 10dde4
    r.put(0x10dde4, 2, rng.choice((0, 5, 0xe, 0x10, 0xffff)))
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('a4off', []):
            a = (regs['a4'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('stack', []):
            r.put(SP + off, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
    if s in NUMBER_LOOP and hint is None:
        regs['a1'] = 0x3650
    if s == 0x21c72 and regs['a1'] not in LIST_21AEE:
        regs['a1'] = LIST_21AEE[0]
    for k in ('a0', 'a4'):
        if regs[k] < 0x100000 or regs[k] >= 0x110000:
            regs[k] = REC                               # a hint pointer outside work RAM (the V1 worlds' nodes are absolute): kept in RAM
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the computed-jump targets and the RTS sentinel
ROUTED_EXITS = {0x289e, 0x35a2, 0x362a, 0x36ba, 0x3902, 0x3918, 0x8da2, 0xca32, 0xce02, 0x49fc6, 0x4a974, 0x4bfc0, 0x4d7a6, 0x4f08a, 0xb7a28, 0x3650,
                0x1cab6, 0x1cabe, 0x1cd98, 0x1cec0, 0x1ed34, 0x1f126, 0x1f1d8, 0x1fae8, 0x201a2, 0x2156a, 0x215e6, 0x21baa, 0x21bc6, 0x21be6, 0x21f30,
                0x21f40, 0x21ffc, 0x4e4da, 0x4e7a2, 0x4e97e, 0x4eb50, 0x21602}
JUMP_TARGETS = {0x21e48, 0x21e3a}                   # the unrouted handlers of the list 21aee (3650 / 21602 above, 21d60 a start)
UNIT_EXITS = set(B.UNIT_EXITS)
assert 0x4e572 in UNIT_EXITS and 0x4ef08 in UNIT_EXITS and 0x1cb1a not in UNIT_EXITS and len(UNIT_EXITS) == 13
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS) + sorted(JUMP_TARGETS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p == ZREAD


def hints(s):
    """The V1 spec hint worlds (pc4.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def gen_singles(rng):
    for s in STARTS:
        if s in CONS_SET:
            continue
        fl = fields(s)
        kept = {}
        hs = hints(s)
        if s == ZREAD:
            hs = [dict(regs=dict(a0=a), writes=[(a & 0xffff, 1, v)]) for a in Z_SOURCES for v in (0, 1, 0x80)]
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs = world(rng, fl, s, hint)
            z = False
            if s == ZREAD:
                if hint is None:
                    continue
                z = r.byte(regs['a0']) == 0
            o = native(r.b, regs, s, 0, single_stop, z)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue                                 # a stop at the entry is a zero-step run
            if ((nxt in CONS_SET or nxt == ZREAD) and s not in CLEAR_SET | PASS_SET | SET_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=0x21c22, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d7=rng.getrandbits(32)))
    if entry in (0x1be4a, 0x1bf94):                              # 289e: CMPI.L #270e,(A0): equal -> Clear
        regs['a0'] = CHILD
        r.put(CHILD, 4, rng.choice((0x270e, 0x1ef0e, 0x270e, 0)))
        r.put(CHILD + 0xa8, 1, rng.choice((0, 0x10, 0xff)))
    if entry == 0x4e962:                                         # 1be3a: A0 = A5 - 7348 / - 7258 (100cb8 / 100da8) by D0.W & 1 (WORD 76)
        w = rng.choice((0, 1))
        r.put(NODE + 0x76, 2, w)
        a0 = 0x100cb8 if w == 0 else 0x100da8
        r.put(a0, 4, rng.choice((0x270e, 0x1ef0e)))
        r.put(a0 + 0xa8, 1, rng.choice((0, 0x10)))
        r.put(NODE + 0xa1, 1, rng.choice((0, 0xff)))
    if entry == 0x1c052:                                         # 4da08: WORD (A5 + 5cba / 5ce6) 0 -> Clear
        regs['d0'] = rng.choice((0, 1, 0x100))
        r.put(A5 + (0x5ce6 if regs['d0'] & 0xff else 0x5cba), 2, rng.choice((0, 1, 0x8000)))
    if entry == 0x1ef9a:                                         # 1ed34: D0 bit 4 clear -> 1ed3c RTS (Clear passes) / BYTE a7 bit 0 / 6e
        regs['d0'] = rng.choice((4, 8, 0xc, 0x14, 0x1c))
        r.put(NODE + 0xa7, 1, rng.choice((0, 1)))
        r.put(NODE + 0x6e, 1, rng.choice((4, 6)))
    if entry == 0x21d68:                                         # C3 21bc6: BYTE 9e = 1 and BYTE a7 bit 4 -> Set
        r.put(NODE + 0x9e, 1, rng.choice((0, 1, 1)))
        r.put(NODE + 0xa7, 1, rng.choice((0, 0x10, 0xff)))
    if entry == 0x21d70:                                         # C3 21baa: BYTE 9f = 0 -> the synthetic BYTE table 21ba6 + WORD 76 against a1
        r.put(NODE + 0x9f, 1, rng.choice((0, 0, 1)))
        r.put(NODE + 0x76, 2, rng.choice((0, 1, 2, 3)))
        r.put(NODE + 0xa1, 1, rng.choice((0, 1, 5, 0xa, 0xb, 0x80)))
    if entry == 0x21d92:                                         # C3 215e6 on the synthetic list 21b0a
        r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 4)))
    if entry == 0x21dc4:
        r.put(NODE + 0xa3, 1, rng.choice((0, 1, 2)))
    if entry == 0x4f13c:                                         # 4f118: WORD 94 = 0 -> Clear; else DIVU 92 -> Set
        r.put(NODE + 0x94, 2, rng.choice((0, 0x40, 0x2800, 1)))
        r.put(NODE + 0x92, 2, rng.choice((1, 0x10, 0x100, 3)))
    if entry == 0x4e758:                                         # ca32: CMPI.B #aa,-769c(A5): borrow when the BYTE is below aa
        r.put(A5 - 0x769c, 1, rng.choice((0, 0xa9, 0xaa, 0xab, 0xff)))
        r.put(NODE + 0x9a, 1, rng.choice((0, 0xff)))
    if entry == 0x4e770:                                         # 4a974: BYTE 10fd82 = 0 -> A0 = 100004 + (BYTE 100003 ? D0.W & 1 : 0)
        r.put(0x10fd82, 1, 0)
        r.put(0x100003, 1, rng.choice((0, 1)))
        r.put(0x100004, 1, rng.choice((0, 1, 0x80)))
        r.put(0x100005, 1, rng.choice((0, 1, 0x80)))
        r.put(NODE + 0x76, 2, rng.choice((0, 1)))
    return r, regs


CHAINS = []


def chain_c(entry, cons, r, regs, o):
    """The C the consumer read in a chain run: the branch successor, or for the SCS consumers the BYTE D0 after the SCS (from the trace and the
    output: 4e75e then 4e768 means D0.B != BYTE 9a; recomputed from the producer's input)."""
    if cons == 0x4e75e:
        return 2 if r.byte(A5 - 0x769c) < 0xaa else 1
    if cons == 0x4e96c:
        a0 = 0x100cb8 if (r.word(NODE + 0x76) & 1) == 0 else 0x100da8
        if r.long(a0) == 0x270e:
            return 1
        return 2 if r.byte(a0 + 0xa8) & 0x10 else 1
    return cons_value(cons, o)


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st))
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES + CLEAR_ONLY_CHAINS:
        succ = B.static_next(cons)
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            o = native(r.b, regs, entry, 0, lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS)
            if o is None or cons not in o['trace']:
                continue
            c = chain_c(entry, cons, r, regs, o)
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
            assert rows, ('no Clear-only chain row', hex(entry))
            for k, r, regs, o, c in rows:
                assert c == 1
                row('chain1-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)
            continue
        if set(seen) != {1, 2}:
            continue                                             # one C value never occurred: declared-C rows only
        if cons not in SCS_SET:
            CHAINS.append((entry, cons))                         # the SCS consumers' read C is checked through D0.B (registers / digest), not a successor
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)
    # the Z chain: 4e770 (MOVE.W 76(A6),D0; JSR 4a974) -> 4a974 (BYTE 10fd82 = 0: 4a9b4 .. TST.B (A0); RTS) -> 4e77a (BEQ) -> 4e786 / 4e77e
    n = {}
    for k in range(600):
        r, regs = chain_world(rng, 0x4e770, k)
        o = native(r.b, regs, 0x4e770, 0, lambda q, tr: q in (0x4e786, 0x4e77e) or q in B.EXIT_STOPS)
        if o is None or ZREAD not in o['trace']:
            continue
        if n.get(o['stop'], 0) >= 3:
            continue
        n[o['stop']] = n.get(o['stop'], 0) + 1
        row('zchain-4e770-%d' % k, r, regs, 0x4e770, o['stop'], 0, 0, 2, o)
        if len(n) == 2 and min(n.values()) >= 3:
            break
    print('Z chain', dict((hex(a), b) for a, b in n.items()))
    assert len(n) == 2, 'Z chain: both outcomes'


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x3650, a2=PARENT, a3=0, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c4 jump target'
    flag = 'unsupported animation player c4 flag source'
    div = 'unsupported animation player c4 divide by zero'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c4 caller requires known carry', cp, stop=SUCC[cp][0])
    # the computed jumps (contract decision 2)
    for v in (0x3670, 0x3651, 0, 0x1003650, 0x36ba):
        err('3766-a1-%x' % v, 0x3766, jump, 0x3766, a1=v, d2=1)
        err('37ca-a1-%x' % v, 0x37ca, jump, 0x37ca, a1=v, d2=1)
    for v in (0x21622, 0x21c22, 0x1021602, 0, 0x21d61, 0x21610):
        err('21c72-%x' % v, 0x21c72, jump, 0x21c72, a1=v)
    err('21c72-listed-21e48', 0x21c72, unrouted, 0x21e48, a1=0x21e48)
    # 21e3a is a player C8 start since C8 (previous row: 'unsupported animation machine PC' at 21e3a); the MOVE.B #1,aa(A6) of 21e3a with A6 = 0
    # writes fixed ROM and keeps the failing PC 21e3a
    err('21c72-listed-21e3a', 0x21c72, 'unsupported animation machine write device', 0x21e3a, a1=0x21e3a, a6=0)
    # the Z source of 4e77a (contract decision 3)
    for v in (0x10fdb2, 0x100006, 0x1ffdb0, 0, 0x100003, 0x3c0000):
        err('z-%x' % v, ZREAD, flag, ZREAD, a0=v)
    # DIVU by zero (contract decision 4): the synthetic table WORD 377a + 0 is 0 as in ROM
    err('div-4f16e', 0x4f16e, div, 0x4f16e, d6=0x10000, d7=5)
    err('div-4f130', 0x4f130, div, 0x4f130, d0=5)
    err('div-4f13c', 0x4f13c, div, 0x4f130, puts=((NODE + 0x94, 2, 5),))
    err('div-373a', 0x373a, div, 0x373a, d5=0, d7=5)
    err('div-37a2', 0x37a2, div, 0x37a2, d5=0x8000, d7=5)                 # 2 x 8000 = 0 in the WORD
    err('div-371e-d4-0', 0x371e, div, 0x373a, d4=0x10000)
    err('div-3786-d4-0', 0x3786, div, 0x37a2, d4=0)
    # the ROM tables outside the declared synthetic bytes
    err('table-377a-6', 0x373a, rom, 0x373a, d5=6, d7=5)                    # 377a + c: the code 3786 of the unit (not declared)
    err('table-370c-11', 0x3766, rom, 0x3766, d2=0x12)
    err('table-1cfce-4', 0x1cfbe, rom, 0x1cfbe, puts=((NODE + 0x9e, 1, 4),))
    err('table-4e4a2-4', 0x4ea24, rom, 0x4ea24, d2=4)
    err('table-4e43e-5', 0x4eafc, rom, 0x4eafc, d1=5)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1ef0e', 0x1ef0e, odd, 0x1ef0e, stop=0x1ef20, a6=NODE + 1)
    err('odd-node-1ef08', 0x1ef08, wodd, 0x1ef08, stop=0x1ef0e, a6=NODE + 1)
    err('odd-node-4ee7a', 0x4ee7a, wodd, 0x4ee7a, stop=0x4f08a, a6=NODE + 1)
    err('odd-stack-1c086', 0x1c086, odd, 0x1c086, stop=0x4d7a6, a7=SP + 1)
    err('odd-stack-4eae6', 0x4eae6, odd, 0x4eae6, stop=0x4eafc, a7=SP + 1)
    err('odd-stack-37ca', 0x37ca, odd, 0x37ca, stop=0x3650, a7=SP + 1)
    err('odd-stack-37da', 0x37da, odd, 0x37da, stop=0x37dc, a7=SP + 1)
    err('odd-stack-1c092', 0x1c092, odd, 0x1c092, stop=0x1c09c, a7=SP + 1)
    err('odd-a0-1d0a2', 0x1d0a2, odd, 0x1d0a2, stop=0x1d0a4, a0=NODE + 1)
    err('odd-a4-4da16', 0x4da16, odd, 0x4da16, stop=0x4da1c, a4=NODE + 1)
    err('odd-a0-4f240', 0x4f240, odd, 0x4f240, stop=0x4f24c, a0=NODE + 1)
    err('odd-a0-1bfa8', 0x1bfa8, odd, 0x1bfa8, a0=NODE + 1)
    err('odd-a0-1ef20', 0x1ef20, odd, 0x1ef20, stop=0x1ef36, a0=NODE + 1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1cec2-then-1cef4', 0x1cec2, odd, 0x1cef4, a7=SP + 1)
    err('1c05e-then-1c066', 0x1c05e, odd, 0x1c066, a7=SP + 1, d0=2)
    err('4f22c-then-4f25c', 0x4f22c, odd, 0x4f25c, a7=SP + 1, puts=((0x10dddc, 2, 5), (NODE + 0xa0, 1, 5), (NODE + 0x9a, 1, 1)))
    err('21d60-then-21dd0', 0x21d60, unrouted, 0x21dd0, puts=((NODE + 0x9d, 1, 1),))
    # 4e564 (WORD 76 = 0) -> 4e572 (player C6 since; was: unrouted at 4e572) -> 4e57e -> JMP 3918 -> its RTS to the RAM return LONG 10fe40 (unrouted)
    err('4e564-then-10fe40', 0x4e564, unrouted, 0x10fe40, puts=((SP, 4, 0x10fe40),))
    err('3774-then-3778', 0x3774, odd, 0x3778, a7=SP + 1, d4=1)
    err('4f1e0-then-4f220', 0x4f1e0, odd, 0x4f220, a7=SP + 1, d2=1)


def main():
    rng = random.Random(0xC4C4)
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
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",NULL,0x0,{%s},%d,%d,%dULL,%d,%dULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'],
                                                                                         outr, d['c'], d['single'], d['digest'], d['pn'], d['pd']))
        else:
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s","%s",0x%x,{0},0,%d,0ULL,0,0ULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'],
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
          'cons', sum(1 for d in ROWS if d['single'] == 3), 'error', sum(1 for d in ROWS if d['single'] == 4),
          'ports', sum(d.get('pn', 0) for d in ROWS))
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
