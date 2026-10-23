"""Generates the native-oracle tables of engine/tests/animation_machine_player_c3_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the record WORD tables 1b542 1b55e 1b57c 1b598 1b5b6 1b5f2 (1cb08 from 1ed22 /
1ee2a / 1ee4e / 1ee7e and the Z source of 1ee56), the BYTE table 21ba4..21baa (21bb2: 21ba6 + sext(WORD 76)), the LONG table 206d4 (206a4), the
(handler LONG, key WORD) lists 21622 / 21aee / 216c8 / 21b26 (215e6 from 21610 / 21c66 / 221d2 / 21f70) and the bank-window LONG 200098 (361e4, bank 200000).  A
native run that reads any other fixed-ROM or banked byte is dropped (a table index beyond the declared bytes), as is a run that lands inside the unit on
a PC that is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 8c(A6) := the record 10ea00 (A4 of
202b6 / 202f4), LONG 84(A6) := a listed slot-84 value (contract decision 2), BYTE a0(A6) 0..8, BYTE a9(A6) 0..5, LONG 5e26(A5) := the record 10ec00
(A4 of e8b5a)), A0 = 10e400 / 10e800 (RAM lists and tables) / a synthetic record table, A1 = a handler of the JMP (A1) list, A4 = 10ea00, A5 = 108000,
seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc3.py
hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'stack' writes at A7).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a computed-jump target).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, computed-jump targets, the RTS sentinel) or a consumer / the Z
            reader 1ee56.
  single 2  a consumer entered through its real producer (RAM / synthetic-table producers): kept when both C values occur; the Clear-only chains
            (the Set side needs a later unit) and the Z chain 1ee4e -> 1cb08 -> 1cb18 -> 1ee56 -> 1ee5a run as plain fixtures.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the Z reader 1ee56 entered directly: the native SR Z is the Z it recomputes (contract decision 3, widened by player C5): WORD W = (A0 + 2 x
            BYTE 9f) = 0 (1cb08 / 1cb18), or for W not 0 the TST.L of LONG (LONG 22(A6) + sext(4 x WORD (A0 + sext(W)))) (C5 1cb1a / 1cb30 / 1cb32);
            worlds whose sources are neither RAM nor declared bytes are skipped, sources at or above 200000 are C++ error rows.
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 215ec (CMPA) 21bc0 21be0 21bfa 21c1c 48392 4d100 4debc 4ded4 Clear, 215fc 21bda 48362 4deca Set, 1ed30 / 21c06 (CMP.W D1,D0) and 21bb2
(CMP.B a1(A6),D0) the borrow recomputed from the native input / output; 1ee00 1ed32 215f6 21c1a keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c3_test_table.py  (rewrites the generated section in place)
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
import pc3 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c3_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
ZREAD = 0x1ee56
CLEAR_SET, SET_SET, PASS_SET, DATA_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET), set(B.DATA_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, REC2, LIST, RTAB = 0x10ea00, 0x10eb00, 0x10ec00, 0x10e600, 0x10e800
RECORDS = (0x1b542, 0x1b55e, 0x1b57c, 0x1b598, 0x1b5b6, 0x1b5f2)
SLOTS = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x2210c, 0x22452)
LIST_21622 = tuple(B.LIST_21622)
BANK_LONG = 0x0012fedc


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def entries(pairs):
    """(handler LONG, key WORD) pairs and the LONG 0 terminator."""
    return b''.join(struct.pack('>IH', h, k) for h, k in pairs) + struct.pack('>I', 0)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1b542, words((0, 2, 0, 0, 4, 0, 0, 6))),                          # 1cb08 from 1ee2a (WORD 0 -> 1cb18, else 1cb1a (C5))
            (0x1b55e, words((0, 0, 8, 0, 0, 0, 2, 0))),                          # 1cb08 from 1ed22 (1ee1a)
            (0x1b57c, words((4, 0, 0, 0, 0, 2, 0, 0))),                          # 1cb08 from 1ed22 (1ee98)
            (0x1b598, words((0, 4, 0, 0, 0, 0, 0, 2))),                          # 1cb08 from 1ed22 (1eeb6)
            (0x1b5b6, words((0, 0, 0, 2, 0, 4, 0, 0))),                          # 1cb08 from 1ee7e
            (0x1b5f2, words((0, 6, 0, 0, 0, 0, 2, 0))),                          # 1cb08 from 1ee4e and the Z source of 1ee56
            (0x200098, struct.pack('>I', BANK_LONG)),                            # 361e4: the bank-window LONG 200098 (bank 200000)
            (0x206d4, longs((0x10e900, 0, 0x10e940, 0, 0x110000, 0x10e980))),   # 206a4: LONG 206d4 + 4 x BYTE a9 (a9 0..5; 110000: low WORD 0)
            (0x21622, entries(((0x21d60, 1), (0x21c22, 2), (0x219c8, 0x103)))),  # 215e6 from 21610 (JMP (A1) 21620: the list 21622)
            (0x216c8, entries(((0x21602, 2),))),                                 # 215e6 from 221d2 (JMP (A1) 221de: the list 216c8)
            (0x21aee, entries(((0x21e48, 1), (0x21602, 3)))),                    # 215e6 from 21c66
            (0x21b26, entries(((0x21e3a, 1),))),                                 # 215e6 from 21f70
            (0x21ba4, bytes((0x77, 0x33, 0x05, 0x0a, 0x80, 0x01)))]              # 21bb2: BYTE 21ba6 + sext(WORD 76) (fffe / ffff / 0..3)


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


def syn_word(address):
    for a, b in SYN:
        if a <= address and address + 2 <= a + len(b):
            return struct.unpack('>H', b[address - a:address - a + 2])[0]
    return None


# consumer -> (C clear successor, C set successor)
SUCC = {0x1ed26: (0x1ed32, 0x1ed2a), 0x1ee04: (0x1ee08, 0x1f126), 0x1ee16: (0x1ee36, 0x1ee1a), 0x1ee26: (0x1ee2a, 0x1eee0), 0x1ee32: (0x1ee36, 0x1eee0),
        0x1ee3c: (0x1ee5a, 0x1ee40), 0x1ee7a: (0x1ee7e, 0x1ee8a), 0x1ee86: (0x1ee8a, 0x1eee0), 0x1eea4: (0x1eea8, 0x1eee0), 0x1eec2: (0x1eec6, 0x1eee0),
        0x1f1ca: (0x1f1d4, 0x1f1ce), 0x201b8: (0x201d0, 0x201bc), 0x201e4: (0x201fc, 0x201e8), 0x202da: (0x202de, 0x202e6), 0x2161c: (0x21662, 0x21620),
        0x21c3a: (0x21c3e, 0x21f40), 0x21c42: (0x21c46, 0x21f30), 0x21c48: (0x21c4c, 0x21fa6), 0x21c6e: (0x21c74, 0x21c72), 0x21c9c: (0x21ca0, 0x21f4c),
        0x221da: (0x221e0, 0x221de), 0x36282: (0x3628c, 0x36286)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / declared bytes and both C values occur
CHAIN_CANDIDATES = ((0x1ee12, 0x1ee16), (0x1ee36, 0x1ee3c), (0x1ee74, 0x1ee7a), (0x201da, 0x201e4), (0x202d0, 0x202da), (0x21610, 0x2161c),
                    (0x21c34, 0x21c3a), (0x21c3e, 0x21c42), (0x21c66, 0x21c6e), (0x221d2, 0x221da), (0x36278, 0x36282))
# the Set side needs a later unit (C5 1cb1a, C8 4d0cc, C5 21c12) or never occurs (21c1c): Clear-only chains
CLEAR_ONLY_CHAINS = ((0x1edf6, 0x1ee04), (0x1ed22, 0x1ed26), (0x1ee1a, 0x1ee26), (0x1ee2a, 0x1ee32), (0x1ee7e, 0x1ee86), (0x1ee98, 0x1eea4),
                     (0x1eeb6, 0x1eec2), (0x201ae, 0x201b8), (0x21c46, 0x21c48), (0x21c98, 0x21c9c))


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor."""
    tr = o['trace']
    i = tr.index(cons)
    nxt = tr[i + 1] if i + 1 < len(tr) else o['stop']
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

    def word(self, a):
        return (self.b[a & 0xffff] << 8) | self.b[(a + 1) & 0xffff]

    def long(self, a):
        return (self.word(a) << 16) | self.word(a + 2)


def base_ram():
    r = Ram()
    r.put(SP, 4, STOP)
    r.base = 1
    return r


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
        return None                                 # C3 writes no PVC port (a run that does is dropped here)
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


def data_carry(p, regs_in, ram_in, regs_out, a6):
    """The C of the data producers: 1ed30 / 21c06 CMP.W D1,D0 (D0 unchanged; D1 of 21c06 is the output) and 21bb2 CMP.B a1(A6),D0 (the output D0.B)."""
    if p == 0x1ed30:
        return 2 if (regs_out['d0'] & 0xffff) < (regs_out['d1'] & 0xffff) else 1
    if p == 0x21c06:
        return 2 if (regs_out['d0'] & 0xffff) < (regs_out['d1'] & 0xffff) else 1
    if p == 0x21bb2:
        return 2 if (regs_out['d0'] & 0xff) < ram_in[(a6 + 0xa1) & 0xffff] else 1
    raise AssertionError(hex(p))


def carry_after(p, c, data=0):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set); data = the C of a data producer (1 / 2)."""
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in CLEAR_SET:
        return 1
    if p in SET_SET:
        return 2
    if p in DATA_SET:
        assert data in (1, 2)
        return data
    return 0


def model(executed, carry, data):
    """C after a path; data = the C of its last data producer when only pass blocks follow it (else 0: a later block resets or sets the C)."""
    c = carry
    for p in executed:
        c = (data if data else 0) if p in DATA_SET else carry_after(p, c)
    return c


def path_data(ex, regs, ram, out_regs):
    """The C of the last data producer of a path when only pass blocks follow it (the compared registers are unchanged by them)."""
    idx = [i for i, p in enumerate(ex) if p in DATA_SET]
    if not idx or any(p not in PASS_SET for p in ex[idx[-1] + 1:]):
        return 0
    return data_carry(ex[idx[-1]], regs, ram, out_regs, regs['a6'])


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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, RTAB, LIST) + RECORDS),
                a1=0x21602 if s == 0x221de else rng.choice(LIST_21622[:3]), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x48, 0x5e, 0x400, 0xffff, 0x12345678, 0x10000, 0x22, 0x53))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 4, 0x8, 0x40, 0x400, 0xffff, 0x12345678))
    if s == 0x20318:
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1, 2, 5, 8, 0x4000, 0x4003, 0xc008))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9)):
            continue                                    # (A6) callback LONG, the node links, the slot LONG 84 and the bounded indices are declared below
        if reg == 5 and disp in (0x5434, 0x5474, 0x5e26):
            continue
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links, the record LONG 8c(A6), the slot LONG 84(A6), the bounded indices a0 / a9, the record LONG 5e26(A5)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x84, 4, rng.choice(SLOTS))
    r.put(NODE + 0xa0, 1, rng.randrange(9))
    r.put(NODE + 0xa9, 1, rng.randrange(6))
    r.put(A5 + 0x5e26, 4, REC2)
    for i in range(4):
        r.put(REC2 + 2 * i, 2, rand_val(rng, 2))                            # e8b5a: WORD (A4) / 2(A4), BYTE 4(A4)
    r.put(PARENT + 0x78, 2, rng.choice((0, 1, 0x8000)))                     # 361e4: WORD 78 of the parent
    if rng.random() < 0.6:                                                  # a RAM (handler, key) list at 10e600: keys 1 / 2 / 0 / ff, then 0
        keys = (1, 2, 0, 0xff)
        for i, k in enumerate(keys):
            r.put(LIST + 6 * i, 4, rng.choice(LIST_21622 + (0x10000, 1)))
            r.put(LIST + 6 * i + 4, 2, k if rng.random() < 0.8 else rng.choice((0x100, 0x8001)))
        r.put(LIST + 24, 4, 0)
    if rng.random() < 0.6:
        for i in range(0, 0x40, 2):
            if rng.random() < 0.4:
                r.put(RTAB + i, 2, rng.choice((0, 2, 4, 6, 0x7a, 0x8000, 0xffff)))   # RAM WORD tables (1ee56 Z source with A0 = 10e800)
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('a4off', []):
            r.put(REC + off, n, v)
            regs['a4'] = REC
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
    if s == 0x21620 and regs['a1'] not in LIST_21622:
        regs['a1'] = LIST_21622[0]
    if s == 0x221de:
        regs['a1'] = 0x21602
    if regs['a4'] < 0x100000 or regs['a4'] >= 0x110000:
        regs['a4'] = REC                                # a hint A4 in the A5 area (4d0b8 / 4deac) is a RAM address: kept
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the computed-jump targets and the RTS sentinel
ROUTED_EXITS = {0x8ebe, 0xce02, 0x1a988, 0x1aa3a, 0x1c1f4, 0x36292, 0x482aa, 0x484e2, 0x49290, 0x49a58, 0x49c38, 0x49f8c, 0x49fc6, 0x49fca, 0x4ae4a,
                0x4b54e, 0x4bfc0, 0x4c1de, 0xe8b7e, 0xe8b80, 0x1cdfe, 0x1a9e8, 0x1cab6, 0x1cabe, 0x1cb08, 0x1cd98, 0x1cef8, 0x1d0c2, 0x1d15a, 0x1dfe6, 0x1ed34,
                0x1ed78, 0x1eee0, 0x1f7a4, 0x1fa3c, 0x1fae8, 0x48368, 0x49bca}
JUMP_TARGETS = set(B.SLOT84) | set(LIST_21622) | set(range(0x20320, 0x20344, 4))
UNIT_EXITS = set(B.EXIT_STOPS[:23])                 # the C3 later-unit and deferred stops (the rest of EXIT_STOPS are C2 stops)
assert 0x223d6 in UNIT_EXITS and 0x202ac in UNIT_EXITS and 0x1cb1a not in UNIT_EXITS and len(UNIT_EXITS) == 23
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_TARGETS


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p == ZREAD


def hints(s):
    """The V1 spec hint worlds (pc3.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def zword(r, regs):
    """The Z source of 1ee56: WORD (A0 + 2 x BYTE 9f(A6)) from the world (synthetic table or RAM); None when outside both."""
    a = (regs['a0'] + 2 * r.b[(regs['a6'] + 0x9f) & 0xffff]) & 0xffffffff
    if 0x100000 <= a < 0x200000:
        return r.word(a)
    return syn_word(a)


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


def zvalue(r, regs):
    """The Z that 1ee56 recomputes (contract decision 3, widened by player C5): W = zword 0 -> True; else the C5 path 1cb1a: WORD W2 = (A0 + sext(W)),
    Z = LONG (LONG 22(A6) + sext(4 x W2)) = 0.  None when a source is neither RAM nor declared synthetic bytes."""
    w = zword(r, regs)
    if w is None:
        return None
    if w == 0:
        return True
    a = (regs['a0'] + sext16(w)) & 0xffffffff
    w2 = r.word(a) if 0x100000 <= a < 0x200000 else syn_word(a)
    if w2 is None:
        return None
    a = (r.long((regs['a6'] + 0x22) & 0xffffffff) + sext16((w2 << 2) & 0xffff)) & 0xffffffff
    if 0x100000 <= a and a + 4 <= 0x200000:
        return r.long(a) == 0
    hi, lo = syn_word(a), syn_word(a + 2)
    if hi is None or lo is None:
        return None
    return (hi | lo) == 0


def zpath_rows(fl, kept):
    """Player C5 decision 3: the Z reader 1ee56 on the C5 path (W not 0): W = 4 / 8004 at RTAB + 2 x 9f, W2 at RTAB + sext(W), LONG 22(A6) = 10e700
    (or 10e710 / the mirror 1fe700), the LONG at LONG 22(A6) + sext(4 x W2) zero or not.  An own RNG keeps the worlds of every other row unchanged."""
    rng5 = random.Random(0xC5C5)
    for i, (b, w, w2, base, lv) in enumerate(((0, 4, 3, 0x10e700, 0), (0, 4, 3, 0x10e700, 0x12345678), (1, 4, 0, 0x10e700, 0x80000000),
                                              (2, 0x8004, 5, 0x10e700, 0), (2, 0x8004, 5, 0x10e700, 1), (3, 4, 0x3fff, 0x10e700, 0),
                                              (3, 4, 0x3ffe, 0x1fe700, 0xff), (1, 4, 0xfffe, 0x10e710, 0))):
        at_w2 = (RTAB + sext16(w)) & 0xffffffff
        at_l = (base + sext16((w2 << 2) & 0xffff)) & 0xffffffff
        hint = dict(regs=dict(a0=RTAB), a6off=[(0x9f, 1, b), (0x22, 4, base)], writes=[((RTAB + 2 * b) & 0xffff, 2, w), (at_w2 & 0xffff, 2, w2), (at_l & 0xffff, 4, lv)])
        r, regs = world(rng5, fl, ZREAD, hint)
        zv = zvalue(r, regs)
        assert zv is not None and zword(r, regs) != 0, i
        o = native(r.b, regs, ZREAD, 0, single_stop, zv)
        assert o is not None and o['stop'] == (0x1ee5a if zv else 0x1eee0), (i, o and hex(o['stop']))
        kept[('c5path', i)] = (r, regs, o)


def gen_singles(rng):
    for s in STARTS:
        if s in CONS_SET:
            continue
        fl = fields(s)
        kept = {}
        hs = hints(s)
        if s == ZREAD:
            hs = [dict(regs=dict(a0=t), a6off=[(0x9f, 1, b)]) for t in RECORDS for b in range(8)] + [dict(regs=dict(a0=RTAB), a6off=[(0x9f, 1, b)]) for b in (0, 1, 0x80, 0xff)]
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs = world(rng, fl, s, hint)
            z = False
            if s == ZREAD:
                w = zword(r, regs)
                if w != 0:
                    continue                             # a WORD that is not 0: the C5-path rows below (own RNG, the other rows keep their worlds)
                z = True
            o = native(r.b, regs, s, 0, single_stop, z)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue                                 # a stop at the entry is a zero-step run
            if ((nxt in CONS_SET or nxt == ZREAD) and s not in CLEAR_SET | PASS_SET | DATA_SET | SET_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
        if s == ZREAD:
            zpath_rows(fl, kept)
        assert kept, hex(s)
        for i, (k, (r, regs, o)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            data = data_carry(s, regs, r.b, o['regs'], regs['a6']) if s in DATA_SET else 0
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, data), 5 if s == ZREAD else 1, o)


PATH_ENTRIES = (0x1cde0, 0x1cdf0, 0x202a0, 0x1ed22, 0x1ed2a, 0x1ee00, 0x1ee08, 0x1ee12, 0x1ee1a, 0x1ee2a, 0x1ee36, 0x1ee40, 0x1ee46, 0x1ee5a, 0x1ee64, 0x1ee8a, 0x1ee90, 0x1eea8,
                0x1eeae, 0x1eec6, 0x1eecc, 0x1f126, 0x1f12a, 0x1f166, 0x1f16a, 0x1f174, 0x1f17c, 0x1f19c, 0x1f1a4, 0x1f1b4, 0x201a2, 0x201a8, 0x201d0,
                0x201e8, 0x201fc, 0x20206, 0x2021c, 0x2022a, 0x20238, 0x2024a, 0x20254, 0x202b6, 0x202c2, 0x202e6, 0x202ec, 0x20300, 0x2030a, 0x20516,
                0x2051e, 0x2053c, 0x20626, 0x2062e, 0x20640, 0x20654, 0x20670, 0x20674, 0x20686, 0x2068e, 0x206a4, 0x206c6, 0x2156a, 0x21582, 0x2158e,
                0x215c4, 0x215e6, 0x215ec, 0x215f8, 0x21602, 0x21610, 0x21baa, 0x21bb2, 0x21bc6, 0x21bd0, 0x21be6, 0x21c00, 0x21c06, 0x21c22, 0x21c34,
                0x21c4c, 0x21c5a, 0x21c66, 0x21c74, 0x21c78, 0x21c80, 0x21c88, 0x21c90, 0x21f30, 0x21f40, 0x21f58, 0x21ffc, 0x22004, 0x221ca, 0x221e0,
                0x221e4, 0x221ec, 0x221fe, 0x22216, 0x2221a, 0x22228, 0x361e4, 0x3620a, 0x3622c, 0x3624a, 0x3625c, 0x3626a, 0x36278, 0x48350, 0x4835a,
                0x48384, 0x484ca, 0x4d0a4, 0x4d0b8, 0x4de9c, 0x4deac, 0x4deb4, 0x4dec2, 0xe8b5a, 0xe8b6e)


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
            if any(p in CONS_SET or p == ZREAD for p in ex) or not allowed(o['stop']) or o['stop'] == s:
                continue
            key = (o['stop'], tuple(ex[:60]))
            if key in kept:
                continue
            data = path_data(ex, regs, r.b, o['regs'])
            kept[key] = (r, regs, o, carry, ex, data)
            if len(kept) >= 4:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o, carry, ex, data)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, data), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=0x21c22, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM / synthetic-table producers only)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d7=rng.getrandbits(32)))
    if entry == 0x1edf6:                                         # 1edf6: D0 & c = 0 -> 1ee00; 1ed34: D0 bit 4 clear -> 1ed3c (RTS)
        regs['d0'] = rng.choice((0, 3, 0x20, 0x12340001))
    if entry == 0x1ed22:                                         # 1cb08 on a synthetic record table: WORD 0 -> 1cb18 (C Clear)
        regs['a0'] = rng.choice(RECORDS)
    if entry in (0x1ed22, 0x1ee1a, 0x1ee2a, 0x1ee7e, 0x1ee98, 0x1eeb6, 0x1ee4e):
        r.put(NODE + 0x9f, 1, rng.choice((0, 1, 2, 3, 4, 5, 7)))
    if entry == 0x1ee12:                                         # 1dfe6: BYTE a7 bit 5 clear -> 1dff0 (Clear); set -> 1dff6 .. 1e016 (borrow)
        r.put(NODE + 0xa7, 1, rng.choice((0, 0x20)))
        r.put(NODE + 0xa2, 1, rng.choice((0, 0x1d, 0x1e, 0x40, 0xff)))
        r.put(A5 + 0x5722, 4, 0x10d6b4)                          # 49a58: D0.W := the WORD at the ring pointer LONG 5722(A5)
        r.put(0x10d6b4, 2, rng.choice((0x10, 0x8000, 0xe0, 0xe1)))
    if entry == 0x1ee36:                                         # 484e2: bit 0 of BYTE 5683(A5)
        r.put(A5 + 0x5683, 1, rng.choice((0, 1, 0xfe, 0xff)))
    if entry == 0x1ee74:
        regs['d0'] = rng.choice((0x10, 0xfff0, 0x12340010))
    if entry == 0x201ae:                                         # 4d0a4: WORD (A5 + 5cba / 5ce6) = 0 -> 4d0be -> 4d100 (Clear)
        w = rng.choice((0, 1))
        r.put(NODE + 0x78, 2, w)
        r.put(A5 + (0x5ce6 if w else 0x5cba), 2, 0)
    if entry == 0x201da:                                         # 4de9c: BYTE (A4) / WORD 4(A4) of 5d12 / 5d18(A5)
        w = rng.choice((0, 1))
        a4 = A5 + (0x5d18 if w else 0x5d12)
        r.put(NODE + 0x78, 2, w)
        r.put(a4 + 4, 2, rng.choice((0, 0x8000)))
        r.put(a4, 1, rng.choice((0, 1, 2)))
    if entry == 0x202d0:                                         # 49c38: TST.L 5734(A5) + 4 (WORD 78 & 1)
        w = rng.choice((0, 1, 0x8000, 0xffff))
        r.put(NODE + 0x78, 2, w)
        r.put(A5 + 0x5734 + 4 * (w & 1), 4, rng.choice((0, 0x10e400)))
    if entry in (0x21610, 0x21c66, 0x221d2):                     # the synthetic lists 21622 / 21aee / 216c8
        r.put(NODE + 0x9c, 1, rng.choice((0, 1, 2, 3, 4)))
    if entry == 0x21c34:
        r.put(NODE + 0x9e, 1, rng.choice((0, 1, 1)))
        r.put(NODE + 0xa7, 1, rng.choice((0, 0x10, 0xff)))
    if entry == 0x21c3e:
        r.put(NODE + 0x9f, 1, rng.choice((0, 0, 1)))
        r.put(NODE + 0x76, 2, rng.choice((0, 1, 2, 3)))
        r.put(NODE + 0xa1, 1, rng.choice((0, 1, 5, 0xa, 0xb, 0x80)))
    if entry == 0x21c98:
        r.put(NODE + 0xa3, 1, rng.choice((0, 1, 2)))
    if entry == 0x36278:                                         # 482aa: BTST #4,5683(A5): set -> Clear, clear -> Set
        r.put(A5 + 0x5683, 1, rng.choice((0, 0x10, 0xef, 0xff)))
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
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES + CLEAR_ONLY_CHAINS:
        clr, st = SUCC[cons]
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            o = native(r.b, regs, entry, 0, lambda q, tr: (len(tr) > 0 and cons in tr and tr[-1] == cons) or q in B.EXIT_STOPS)
            if o is None or cons not in o['trace']:
                continue
            c = cons_value(cons, o)
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
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)
    # the Z chain: 1ee4e (LEA 1b5f2; BSR 1cb08) -> 1cb08 (WORD 0) -> 1cb18 RTS -> 1ee56 (BNE not taken) -> 1ee5a
    n = 0
    for k in range(400):
        r, regs = chain_world(rng, 0x1ee4e, k)
        o = native(r.b, regs, 0x1ee4e, 0, lambda q, tr: q == 0x1ee5a or q == 0x1eee0 or q in B.EXIT_STOPS)
        if o is None or ZREAD not in o['trace']:
            continue
        assert o['stop'] == 0x1ee5a
        row('zchain-1ee4e-%d' % k, r, regs, 0x1ee4e, o['stop'], 0, 0, 2, o)
        n += 1
        if n >= 3:
            break
    assert n, 'no Z chain row'


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x21c22, a2=PARENT, a3=0, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    inside = 'unsupported animation player c3 PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation player c3 jump target'
    flag = 'unsupported animation player c3 flag source'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c3 caller requires known carry', cp, stop=SUCC[cp][0])
    # the computed jumps (contract decision 2)
    for v in (0, 0x21603, 0x12345678, 0x1021602, 0x1ee00, 0x21622):
        err('slot-%x' % v, 0x201a2, jump, 0x201a2, puts=((NODE + 0x84, 4, v),))
    for v in (0x2210c, 0x22452, 0x21664, 0x2173c):
        err('slot-listed-%x' % v, 0x201a2, unrouted, v, puts=((NODE + 0x84, 4, v),))
    err('slot-odd-node', 0x201a2, odd, 0x201a2, stop=0x201a8, a6=NODE + 1)
    for v in (0x21602, 0x10fe40, 0, 0x21c23, 0x1021c22):
        err('21620-%x' % v, 0x21620, jump, 0x21620, a1=v)
    for v in (0x21e48, 0x219c8, 0x21720):            # player C4 routes 21d60 since (was 0x21d60, 0x219c8, 0x21720)
        err('21620-listed-%x' % v, 0x21620, unrouted, v, a1=v)
    for v in (0x21c22, 0x21603, 0x1021602, 0):
        err('221de-%x' % v, 0x221de, jump, 0x221de, a1=v)
    for v in (9, 0x47, 0xffff, 0x12340010, 0x3fff):
        err('20318-%x' % v, 0x20318, jump, 0x20318, d0=v)
    for v in (0, 3, 8, 0x4000, 0x12348002):
        err('20318-entry-%x' % v, 0x20318, unrouted, 0x20320 + ((4 * v) & 0xffff), d0=v)
    err('2030a-a0-9', 0x2030a, jump, 0x20318, puts=((NODE + 0xa0, 1, 9), (NODE + 0x9f, 1, 0)))
    err('2030a-a0-ff', 0x2030a, jump, 0x20318, puts=((NODE + 0xa0, 1, 0xff), (NODE + 0x9f, 1, 0)))
    # the synthetic list 21622: key 1 -> 21d60 (player C4 since) -> BYTE 9d = 1: BGT.W 21dd0 (C12, unrouted) (was: unrouted at 21d60, puts 9c only)
    err('21610-key-1', 0x21610, unrouted, 0x21dd0, puts=((NODE + 0x9c, 1, 1), (NODE + 0x9d, 1, 1)))
    err('21610-key-3', 0x21610, unrouted, 0x21662, puts=((NODE + 0x9c, 1, 3),))    # the key WORD 0103 does not match BYTE 3: C Clear -> 21662 (C6)
    # the Z source of 1ee56 (contract decision 3, widened by player C5: a WORD that is not 0 is the C5 path 1cb1a; before C5 the rows z-word-1b5f2 /
    # z-word-ram expected the flag-source error for any WORD not 0)
    err('z-path-rom', ZREAD, rom, ZREAD, a0=0x1b5f2, puts=((NODE + 0x9f, 1, 1), (NODE + 0x22, 4, 0x2000)))   # W 6 -> W2 0 -> LONG 2000 (ROM, not declared)
    err('z-path-ram', ZREAD, rom, ZREAD, a0=RTAB, puts=((NODE + 0x9f, 1, 0x80), (RTAB + 0x100, 2, 0x8000), (NODE + 0x22, 4, 0x2000)))  # 106800: W2 0
    err('z-path-w2-bank', ZREAD, flag, ZREAD, a0=0x1f9000, puts=((0x109000, 2, 0x7000),))                  # A0 + sext(7000) = 200000
    err('z-path-long-bank', ZREAD, flag, ZREAD, a0=RTAB, puts=((RTAB, 2, 2), (RTAB + 2, 2, 4), (NODE + 0x22, 4, 0x1ffff0)))   # 1ffff0 + 10
    err('z-path-long-io', ZREAD, flag, ZREAD, a0=RTAB, puts=((RTAB, 2, 2), (RTAB + 2, 2, 1), (NODE + 0x22, 4, 0x3bfffc)))     # 3bfffc + 4
    err('z-bank', ZREAD, flag, ZREAD, a0=0x200000)
    err('z-io', ZREAD, flag, ZREAD, a0=0x3c0004, puts=((NODE + 0x9f, 1, 1),))
    err('z-mirror-top', ZREAD, flag, ZREAD, a0=0x1fff00, puts=((NODE + 0x9f, 1, 0x80),))
    err('z-rom-missing', ZREAD, rom, ZREAD, a0=0x1b5f2, puts=((NODE + 0x9f, 1, 8),))
    err('z-odd', ZREAD, odd, ZREAD, a0=0x1b5f3)
    # the ROM tables outside the declared synthetic bytes: 21bb2 WORD 76 = 4 (21baa, a code BYTE of the unit), 206a4 BYTE a9 = 6 (206ec)
    err('table-21bb2-4', 0x21bb2, rom, 0x21bb2, puts=((NODE + 0x76, 2, 4),))
    err('table-21bb2-fffd', 0x21bb2, rom, 0x21bb2, puts=((NODE + 0x76, 2, 0xfffd),))
    err('table-206a4-6', 0x206a4, rom, 0x206a4, puts=((NODE + 0xa9, 1, 6),))
    # odd node / stack / A0 / A4 / A5: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1f12a', 0x1f12a, wodd, 0x1f12a, stop=0x1f166, a6=NODE + 1)
    err('odd-stack-2158e', 0x2158e, odd, 0x2158e, stop=0x49fca, a7=SP + 1)
    err('odd-stack-215c4', 0x215c4, odd, 0x215c4, a7=SP + 1)
    err('odd-stack-e8b6e', 0xe8b6e, odd, 0xe8b6e, stop=0xe8b80, a7=SP + 1)
    err('odd-a4-4d0b8', 0x4d0b8, odd, 0x4d0b8, stop=0x4d0be, a4=NODE + 1)
    err('odd-a4-202b6', 0x202b6, odd, 0x202b6, stop=0x202e6, puts=((NODE + 0x8c, 4, NODE + 1),))
    err('odd-a0-215ec', 0x215ec, odd, 0x215ec, stop=0x215f6, a0=NODE + 1)
    err('odd-a0-215f8', 0x215f8, odd, 0x215f8, stop=0x215fc, a0=NODE + 1)
    err('odd-a5-e8b5a', 0xe8b5a, odd, 0xe8b5a, stop=0xe8b6e, a5=A5 + 1)
    err('odd-a4-4deac', 0x4deac, odd, 0x4deac, stop=0x4dec2, a4=NODE + 1)
    err('odd-node-361e4', 0x361e4, wodd, 0x361e4, stop=0x3620a, a6=NODE + 1)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('21baa-then-21bc0', 0x21baa, odd, 0x21bc0, a7=SP + 1, puts=((NODE + 0x9f, 1, 1),))
    err('48384-then-48392', 0x48384, odd, 0x48392, a7=SP + 1)
    err('1ee5a-then-1ee74', 0x1ee5a, odd, 0x1ee74, stop=0x4c1de, a7=SP + 1, puts=((NODE + 0x6e, 1, 2),))
    err('21c5a-then-21c66', 0x21c5a, odd, 0x21c66, stop=0x215e6, a7=SP + 1)
    err('215e6-then-215f6', 0x215e6, odd, 0x215f6, a0=LIST, a7=SP + 1)
    err('4de9c-then-4debc', 0x4de9c, odd, 0x4debc, a7=SP + 1, puts=((A5 + 0x5d12 + 4, 2, 0x8000),))
    err('21be6-then-21bfa', 0x21be6, odd, 0x21bfa, a7=SP + 1)


def main():
    rng = random.Random(0xC3C3)
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
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
