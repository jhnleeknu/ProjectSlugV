"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr1_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data): the bank-window LONGs
2001c0 (-> 2a0000) and 2001d0 (-> 2a0100) with the LONGs 2a000c / 2a0148 they lead to, the kind and item records b3484..b3dbc (kind records 0 / 1 / 2
hold the handler LONGs b3fa5 (odd), b3fa6 (inside the unit) and 10fe40 (work RAM) for the error rows), the LONG table b3f8c..b3fa4, the WORD list
51620..51626, the menu records eba9e..ebb1e, the 1ab02 rectangle ba3d6..ba3de and the sign-extension targets ab486 (kind record at b3484 - 7ffe),
abf8c (LONG at b3f8c - 8000) and e3a9e (menu record at eba9e - 8000).  A native run that reads any other fixed-ROM or banked byte is dropped (the C++
has no bytes there), as is a run that lands inside the unit on a PC that is not a block start (the C++ rejects it; error rows cover those targets).
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000, record A0 = 10e400, A1 = 10ea00, A2 / A4 = 10e900 / 10e800, the parent
record of LONG c(A6) = 10eb00, the 515e2 WORD list at 10ec80, A5 = 108000, the player records 1009a8 / 100a6c, seeded BYTE / WORD / LONG field edits
(BYTE / WORD sign boundaries included), seeded D0-D7, declared stack words for the blocks that read or pop them (515e2 515e8 515ec 515f8).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the first instruction that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP exits, TRAP b3eac, a live jump target, the RTS sentinel).
  single 2  a consumer entered through its real producer (1ab02 -> b97b4; the 4b6f4 C through the B2a consumer 5f5e6): stop = the consumer's successor;
            the native branch on the real flags decides it.  49fc6 runs ROM scripts: its consumers b401e / b9798 have declared-C rows here (real chains in V1).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C; 4b6f4 (TST.B
clears C) / 4b6fc (ORI.B #1,CCR) are the only producers and 4b700 keeps the incoming C (contract decision 5).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr1_test_table.py  (rewrites the generated section in place)
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
import fr1 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr1_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
CLEAR_SET, SET_SET, PASS_SET = set(B.CLEAR_SET), set(B.SET_SET), set(B.PASS_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC4, REC2, REC1, PARENT, LIST = 0x10e800, 0x10e900, 0x10ea00, 0x10eb00, 0x10ec80
ITEMS, KINDS, ITEM_COUNT, KIND_COUNT = 0xb3894, 0xb3484, 0x6e, 104
ODD_HANDLER, INSIDE_HANDLER, RAM_HANDLER = 0xb3fa5, 0xb3fa6, 0x10fe40
SEXT_ITEM = ITEM_COUNT - 1                          # item record 6d: kind index ccd (x a = 8002 -> sext -> b3484 - 7ffe = ab486)
SEXT_KIND = 103                                     # kind record 103: LONG-table offset 8000 (-> sext -> b3f8c - 8000 = abf8c)


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xF4A1)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    handlers = (0x2a00, 0x43e34, 0xbff02, 0xc0986, 0xd8f78, 0x10fe40, 0xb3fa4, 0xb4012, 0xb3ddc, STOP)
    kinds = []
    for j in range(KIND_COUNT):
        if j == 0:
            h = ODD_HANDLER
        elif j == 1:
            h = INSIDE_HANDLER
        elif j == 2:
            h = RAM_HANDLER
        else:
            h = srng.choice(handlers)
        off = 0x8000 if j == SEXT_KIND else (srng.choice((0, 4, 8, 0xc, 0x10, 0x14)) if srng.random() < 0.95 else 0x18)
        kinds.append(bytes([srng.getrandbits(8), srng.getrandbits(8)]) + w(srng.getrandbits(16)) + w(off) + l(h))
    items = []
    for k in range(ITEM_COUNT):
        idx = 0xccd if k == SEXT_ITEM else (k % 3 if k < 6 else srng.randrange(KIND_COUNT))
        items.append(bytes([srng.getrandbits(8), srng.getrandbits(8)]) + w(idx) + bytes(srng.getrandbits(8) for _ in range(8)))
    records = b''.join(kinds) + b''.join(items)
    assert len(records) == 0xb3dbc - 0xb3484
    table = b''.join(l(srng.choice((0, 0xffffc000, 0xffff8000, srng.getrandbits(32)))) for _ in range(6))         # b3f8c..b3fa4
    menu = b''.join(l(srng.getrandbits(32)) + w(srng.getrandbits(16)) + w(srng.getrandbits(16)) for _ in range(16))  # eba9e..ebb1e
    hud = w(0x0003) + w(0x0105) + w(0xffff)                                                                        # 51620..51626
    rect = w(0xffd0) + w(0xff00) + w(0x0060) + w(0x0200)                                                           # ba3d6..ba3de
    sext_kind = bytes([0x5a, 0x01]) + w(0x1234) + w(0x0004) + l(0x2a00)                                            # ab486
    return [(0x51620, hud), (0xab486, sext_kind), (0xabf8c, l(0x13572468)), (KINDS, records), (0xb3f8c, table), (0xba3d6, rect),
            (0xe3a9e, l(0x24681357) + w(0x0c11) + w(0x0022)), (0xeba9e, menu), (0x2001c0, l(0x2a0000)), (0x2001d0, l(0x2a0100)),
            (0x2a000c, l(srng.getrandbits(19) << 1)), (0x2a0148, l(srng.getrandbits(19) << 1))]


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
SUCC = {0xb401e: (0xb4028, 0xb4022), 0xb9798: (0xb97a8, 0xb979c), 0xb97b4: (0xb97be, 0xb97b8)}
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
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.ports or m.bank != 0x200000:
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
        d.update(out=[o['regs'][k] for k in KEYS], digest=digest(o['ram'], o['regs'], o['stop']))
    ROWS.append(d)


# ---------------------------------------------------------------------------------------------------------------------
VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 9, 0xf, 0x10, 0x1e, 0x6d, 0x6e, 0x80, 0xff, 0x100, 0x3e6, 0x3e7, 0x3e8, 0x19ce, 0x19cf, 0x19d0, 0x7fff, 0x8000, 0x8001,
      0xfff0, 0xffff)
VL = (0, 1, 0x7fff, 0x10000, 0x7fffffff, 0x80000000, 0xfff80000, 0xffffffff, 0x123456)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x0, 0x4, 0x8, 0xc, 0x22}
LIST_BLOCKS = set(B.LIST_BLOCKS)
ITEM_BLOCKS = set(B.ITEM_BLOCKS)
KIND_BLOCKS = set(B.KIND_BLOCKS)


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


# stack words read or popped by the entered block (declared below A7 = 10ef00): 515e2 515e8 515ec a WORD (the pushed D2), 515f8 the LONG list + WORD
def pops_of(rng, s):
    if s in (0x515e2, 0x515e8, 0x515ec):
        return [(2, rng.getrandbits(16))]
    if s == 0x515f8:
        return [(4, LIST), (2, rng.getrandbits(16))]
    return []


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=CHILD, a1=REC1,
                a2=rng.choice((REC2, 0xa2a2a2a2)), a3=0xa3a3a3a3, a4=REC4, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 9, 0xa, 0x80, 0xff, 0x3e7, 0x8000, 0xffff, 0x10000, 0x9ffff, 0xa0000, 0x123480))
    if rng.random() < 0.3:
        regs['d1'] = rng.choice((0, 0x3e7, 0x3e8, 0x8000, 0xffff, 0x1234ff80))
    if rng.random() < 0.5:
        regs['d3'] = rng.choice((0, 1, 2, 0x10000))
    if s in (0xe56d0, 0xe56e6, 0xe56fe) and rng.random() < 0.85:
        regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0xa, 1, 3, 0xffff))
    if s in ITEM_BLOCKS:
        regs['a0'] = ITEMS + 12 * rng.randrange(ITEM_COUNT)
    if s in KIND_BLOCKS:
        regs['a1'] = KINDS + 10 * rng.randrange(3, KIND_COUNT)
    if s in (0x4e158, 0x4e162):
        regs['a0'] = rng.choice((0x1009a8, 0x100a6c, REC1))
    if s in LIST_BLOCKS:
        regs['a0'] = LIST
        words = []
        for _ in range(rng.randrange(3)):
            words += [rng.choice((0, 1, 0x85, 0x7fff)), rng.getrandbits(16)]
        words.append(rng.choice((0xffff, 0x8000)))
        for i, v in enumerate(words):
            r.put(LIST + 2 * i, 2, v)
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
    r.put(NODE + 0xc, 4, PARENT)
    for d in (0x62, 0x82, 0x84):
        r.put(PARENT + d, 1 if d == 0x62 else 2, rand_val(rng, 1 if d == 0x62 else 2))
    for a in (0x1009a8 + 0x9c, 0x100a6c + 0x9c, 0x10fdb6, 0x10fdb7):
        r.put(a, 1, rng.choice((0, 1, 1, 2, 0xff)))
    # item / kind / menu indices inside the transcribed synthetic tables most of the time (the hints test the edges)
    if rng.random() < 0.8:
        r.put(NODE + 0x76, 2, rng.randrange(1, ITEM_COUNT))
        r.put(NODE + 0x8a, 2, rng.randrange(ITEM_COUNT))
        r.put(NODE + 0x7e, 2, rng.randrange(4))
        r.put(NODE + 0x7c, 2, rng.randrange(3))
    if rng.random() < 0.5:
        r.put(NODE + 0x78, 2, rng.randrange(1, 16))
        r.put(NODE + 0x7a, 2, rng.randrange(1, 16))
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
    if s == 0x4b6f4:
        h += [dict(puts=[(A5 + 0x5b86, 1, v)]) for v in (0, 1, 0x7f, 0x80, 0xff)]
    if s == 0x4e158:
        h += [dict(regs=dict(a0=a), puts=[(a + 0x9c, 1, v)]) for a in (0x1009a8, 0x100a6c) for v in (0, 1, 2, 0x81, 0xff)]
    if s == 0x4e162:
        h += R('d0', (0, 0xffff, 0x1234ffff))
    if s == 0x4e0de:
        h += [dict(regs=dict(d0=d), puts=[(A5 + 0x5d22, 4, 0x11112222), (A5 + 0x5d26, 4, 0x8333f444)]) for d in (0, 1, 2, 3, 0xffff, 0x12340001)]
    if s == 0x515e2:
        h += [dict(puts=[(LIST, 2, v), (LIST + 2, 2, 0x1234), (LIST + 4, 2, 0xffff)]) for v in (0, 0x7fff, 0x8000, 0xffff)]
    if s in (0xde686, 0xde754, 0xde84c, 0xde898):
        h += N(0x76, 2, (0, 1, 2, 0x8000, 0xffff))
    if s in (0xe5364, 0xe537e, 0xe539e, 0xe5424, 0xe543e, 0xe545e, 0xe54e4, 0xe5538):
        h += N(0x7a, 2, (0, 1, 2, 8, 9, 0x8000))
    if s in (0xe53a6, 0xe5466):
        h += N(0x7a, 2, (0, 7, 8, 0x10, 0x8000, 0xffff))
    if s == 0xde778:
        h += N(0x62, 1, (0, 3, 4, 5, 0x84, 0xff))
    if s == 0xde832:
        h += R('d0', (0, 1, 0x80, 0xff, 0x100, 0x12345600))
    if s == 0xde880:
        h += N(0x82, 2, (0, 0x19c0, 0x19ce, 0x19cf, 0x19d0, 0x7fff, 0x8000, 0xffff))
    if s == 0xde88a:
        h += N(0x82, 2, (0x7fff, 0xffff, 0x19ce))
    if s in (0xe5292, 0xe52b2, 0xe52d6, 0xe5308, 0xe533c, 0xe53ec, 0xe54ac, 0xe54fc):
        h += N(0x7c, 2, (0, 1, 0x8000, 0xffff))
    if s == 0xe52f6:
        h += [dict(puts=[(A5 - 0x8000, 1, v)]) for v in (0, 2, 3, 4, 0x83)]
    if s == 0xe5324:
        h += [dict(puts=[(NODE + 0x7c, 2, k), (0x10fdb6, 1, a), (0x10fdb7, 1, b)]) for k, a, b in (
            (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 0), (2, 1, 2), (0xffff, 0x81, 1), (0x8000, 1, 0xff))]
    if s in (0xe53da, 0xe549a):
        h += R('d1' if s == 0xe53da else 'd2', (0, 0x3e6, 0x3e7, 0x3e8, 0x7fff, 0x8000, 0xffff, 0x123403e7))
    if s == 0xe5568:
        h += N(0x62, 1, (0, 1, 0x80, 0xff))
    if s == 0xe5572:
        h += [dict(puts=[(PARENT + 0x62, 1, v)]) for v in (0x7f, 0xff)]
    if s == 0xe56c0:
        h += R('d0', (0, 1, 9, 0xa, 0x3e7, 0x999, 0xffff, 0x10000, 0x12340000, 0x1234ffff))
    if s in (0xe56d0, 0xe56e6, 0xe56fe):
        h += [dict(regs=dict(d0=a, d2=b)) for a, b in ((0, 0xa), (9, 0xa), (0xffff, 0xa), (0x9ffff, 0xa), (0xa0000, 0xa), (0xffffffff, 0xa), (5, 1),
                                                       (0x10000, 1), (0xffff, 0x1234000a), (0x7fff8, 0x8))]
    if s == 0xe5720:
        h += R('d3', (0, 0x9999, 0x12345678))
    if s == 0xb3dbc:
        h += N(0x7e, 2, (0, 1, 2, 3, 4, 0x2000, 0x4000, 0x6000))
    if s == 0xb3fc6:
        h += R('d3', (0, 1, 2, 0x4000, 0x2000, 0x12340001))
    if s == 0xb3ea2:
        h += N(0x76, 2, (0, 0x6d, 0x6e, 0x6f, 0x8000, 0xffff))
    if s == 0xb3ec4:
        h += N(0x76, 2, (0, 1, 0x6d))
    if s == 0xb3ede:
        h += N(0x78, 2, (0, 1, 0x8000))
    if s == 0xb3eea:
        h += N(0x95, 1, (0, 4, 0xfb, 0xff))
    if s == 0xb3f02:
        h += [dict(regs=dict(d2=v), puts=[(NODE + 0x15, 1, f)]) for v, f in ((0, 0), (3, 0xff), (0xff, 0x80), (0x1234567c, 1))]
    if s == 0xb3f2c:
        h += [dict(regs=dict(d0=a, d3=b)) for a, b in ((0, 0), (0x8000, 1), (0x7fff, 0x10000), (0xffff, 0xffff))]
    if s == 0xb3f5c:
        h += R('d0', (0, 1, 0x6d, 0xaaa, 0xaab, 0xffff, 0x12340005))
    if s in (0xb3f68, 0xb3fb2):
        h += R('a0', (ITEMS, ITEMS + 12 * 3, ITEMS + 12 * SEXT_ITEM))
        h += [dict(regs=dict(a0=REC1), puts=[(REC1 + 2, 2, SEXT_KIND)])]
    if s == 0xb3f3a:
        h += R('a1', (KINDS + 10 * 3, KINDS + 10 * 50, 0xab486))
    if s == 0xb3f50:
        h += [dict(regs=dict(a0=REC1, d0=0x12345678), puts=[(REC1, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)]
    if s == 0xb3faa:
        h += N(0x8a, 2, (0, 1, 0x6d, 0xaab))
    if s == 0xeb9ba:
        h += [dict(puts=[(NODE + 0x7e, 2, a), (NODE + 0x7a, 2, b)]) for a, b in ((0, 3), (2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 3), (0xffff, 0), (5, 0xffff))]
    if s == 0xeb9ce:
        h += [dict(regs=dict(d1=a), puts=[(NODE + 0x7a, 2, b)]) for a, b in ((2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 0x7fff), (0xffff, 0))]
    if s == 0xeb9e4:
        h += [dict(puts=[(NODE + 0x7c, 2, a), (NODE + 0x78, 2, b)]) for a, b in ((0, 3), (2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 3), (0xffff, 4))]
    if s == 0xeb9fa:
        h += [dict(regs=dict(d1=a), puts=[(NODE + 0x78, 2, b)]) for a, b in ((2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 0x7fff))]
    if s == 0xeb9ec:
        h += N(0x78, 2, (0, 1, 0x1001))
    if s == 0xeb9dc:
        h += R('d3', (0, 1, 0x10000, 0x8000))
    if s == 0xeba08:
        h += N(0x7c, 2, (0, 1, 15, 0x1000))
    # Verification-run additions (mutation survivors): clamp edge WORD == 3e7 (and neighbours / upper half), MOVEQ #0,D3 clears the whole D3,
    # BYTE 62(A6) nonzero before e5552 clears it, WORD 84(A6) != WORD 86(A6) at eba2e.
    if s == 0xe53da:
        h += R('d1', (0x3e6, 0x3e7, 0x3e8, 0x103e7, 0xffff, 0x8000))
    if s == 0xe549a:
        h += R('d2', (0x3e6, 0x3e7, 0x3e8, 0x103e7, 0xffff, 0x8000))
    if s == 0xde81a:
        h += R('d3', (0x12345678, 0xffffffff, 0x80000001))
    if s == 0xe5552:
        h += N(0x62, 1, (0, 1, 0x80, 0xff))
    if s == 0xeba2e:
        h += [dict(puts=[(NODE + 0x84, 2, a), (NODE + 0x86, 2, b)]) for a, b in ((0x1234, 0x5678), (0x5678, 0x1234), (0, 0xffff), (0x8000, 0))]
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


PATH_ENTRIES = (0xde660, 0xde686, 0xde690, 0xde754, 0xde778, 0xde784, 0xde814, 0xde832, 0xde84c, 0xde880, 0xde898, 0x4e146, 0x4e152, 0x4e158,
                0xe5292, 0xe52b2, 0xe52d6, 0xe52f6, 0xe5324, 0xe533c, 0xe5364, 0xe539e, 0xe53a6, 0xe53ca, 0xe53da, 0xe53ec, 0xe545e, 0xe548a, 0xe549a,
                0xe54ac, 0xe54e4, 0xe54fc, 0xe5538, 0xe5568, 0xe56c0, 0xe56d0, 0xe56e6, 0x4e0de, 0xb3dbc, 0xb3dcc, 0xb3dd8, 0xb3ea2, 0xb3ec4, 0xb3ede,
                0xb3eea, 0xb3f02, 0xb3f2c, 0xb3f4c, 0xb3f68, 0xb3fa4, 0xb3fc6, 0xb3fce, 0xb3fd2, 0xb4022, 0xb979c, 0x4b6f4, 0x4b6fc, 0xd131a, 0xd1330,
                0xeb9ba, 0xeb9ce, 0xeb9e4, 0xeb9ec, 0xeb9fa, 0xeba02, 0xeba28, 0x51602, 0x515e0, 0x515e2, 0x515f8, 0xca42, 0xb7742, 0xde8a2, 0xe5542)


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
    # real producer 1ab02 (b97a8: LEA ba3d6.l,A0; JSR 1ab02.l): the node position against the synthetic rectangle decides; inside -> C Clear, outside -> Set
    clr, st = SUCC[0xb97b4]
    seen = {}
    for k in range(400):
        r = base_ram()
        regs = dict(PLAIN)
        r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
        for d in (0x42, 0x46, 0x4a, 0x4e):
            r.put(NODE + d, 4, rng.choice((0, 0x100000, 0x800000, 0x1000000, 0x1400000, 0x2000000, 0x7fff0000, 0xfff00000, rng.getrandbits(32))))
        o = native(r.b, regs, 0xb97a8, 0, lambda q, tr: q in (clr, st))
        if o is None or o['stop'] in seen and seen[o['stop']] >= 3:
            continue
        seen[o['stop']] = seen.get(o['stop'], 0) + 1
        c = 1 if o['stop'] == clr else 2
        row('chain-b97a8-1ab02-%d' % k, r, regs, 0xb97a8, o['stop'], 0, c, 2, o)
        if len(seen) == 2 and min(seen.values()) >= 3:
            break
    assert set(seen) == {clr, st}, seen
    # 4b6f4 -> RTS 4b700 -> the B2a consumer 5f5e6 (BCC.W 5f5f0): BYTE 5b86(A5) = 0 -> C Clear -> 5f5f0, otherwise Set -> 5f5ea.
    for k, v in enumerate((0, 1, 0x7f, 0x80, 0xff)):
        r = base_ram()
        r.put(SP, 4, 0x5f5e6)
        r.put(A5 + 0x5b86, 1, v)
        regs = dict(PLAIN)
        o = native(r.b, regs, 0x4b6f4, k % 3, lambda q, tr: q in (0x5f5f0, 0x5f5ea))
        assert o is not None and o['stop'] == (0x5f5f0 if v == 0 else 0x5f5ea), (v, o and hex(o['stop']))
        row('chain-4b6f4-5f5e6-%d' % k, r, regs, 0x4b6f4, o['stop'], k % 3, 1 if v == 0 else 2, 2, o)
    # 49fc6 (the interpreter on ROM scripts): no synthetic world; the consumers b401e b9798 have the declared-C rows above and the real-producer chains
    # of the V1 spec / real-ROM differential.


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x10c000, a2=0, a3=0, a4=REC4, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'
    inside = 'unsupported animation objects fr1 PC'
    unrouted = 'unsupported animation machine PC'
    unaligned = 'unaligned animation machine PC'
    divu = 'objects fr1 DIVU zero divisor'

    def err(name, entry, message, fail_pc, carry=0, puts=(), **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr1 caller requires known carry', cp)
    # odd node / record / list / stack: the entry block fails
    err('odd-node-de67a', 0xde67a, wodd, 0xde67a, a6=NODE + 1)
    err('odd-node-b3ea2', 0xb3ea2, odd, 0xb3ea2, a6=NODE + 1)
    err('odd-child-de6ba', 0xde6ba, wodd, 0xde6ba, a0=CHILD + 1)
    err('odd-parent-e533c', 0xe533c, odd, 0xe533c, puts=[(NODE + 0xc, 4, PARENT + 1)])
    err('odd-list-515e2', 0x515e2, odd, 0x515e2, a0=LIST + 1)
    err('odd-stack-515ec', 0x515ec, odd, 0x515ec, a0=LIST, a7=SP + 1, puts=[(LIST, 4, 0x12345678)])
    err('odd-stack-e5350', 0xe5350, odd, 0xe5350, a7=SP + 1)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('eba08-menu-rom', 0xeba08, missing, 0xeba08, puts=[(NODE + 0x7c, 2, 0x20)])
    err('b3f50-item-rom', 0xb3f50, missing, 0xb3f50, a0=0x1000)
    err('515e2-list-rom', 0x515e2, missing, 0x515e2, a0=0x1000)
    # DIVU zero divisor (D2.W = 0; e56c0 itself sets D2.W := a)
    err('divu-zero-e56d0', 0xe56d0, divu, 0xe56d0, d0=5, d2=0x12340000)
    err('divu-zero-e56e6', 0xe56e6, divu, 0xe56e6, d0=0xffff, d2=0)
    err('divu-zero-e56fe', 0xe56fe, divu, 0xe56fe, d0=1, d2=0xffff0000)
    # computed targets: the jump tables (index outside the table: inside a block of the unit) and the kind-record handlers (odd, inside, work RAM)
    err('b3dbc-target-b3de0', 0xb3dbc, inside, 0xb3de0, puts=[(NODE + 0x7e, 2, 5)])
    err('b3dbc-target-b3dc8', 0xb3dbc, inside, 0xb3dc8, puts=[(NODE + 0x7e, 2, 0xffff)])
    err('b3fc6-target-b3fda', 0xb3fc6, inside, 0xb3fda, d3=3)
    err('b3fc6-target-b3fca', 0xb3fc6, inside, 0xb3fca, d3=0xffff)
    err('b3f3a-handler-odd', 0xb3f3a, unaligned, ODD_HANDLER, a1=KINDS)
    err('b3f3a-handler-inside', 0xb3f3a, inside, INSIDE_HANDLER, a1=KINDS + 10)
    err('b3f3a-handler-ram', 0xb3f3a, unrouted, RAM_HANDLER, a1=KINDS + 20)
    err('b3fb2-handler-odd', 0xb3fb2, unaligned, ODD_HANDLER, a0=ITEMS)                 # item record 0: kind 0
    err('b3fb2-handler-inside', 0xb3fb2, inside, INSIDE_HANDLER, a0=ITEMS + 12)         # item record 1: kind 1
    # TRAP #15 boundary without a stop (b3ea2 with WORD 76 >= 6e)
    err('b3ea2-trap', 0xb3ea2, unrouted, 0xb3eac, puts=[(NODE + 0x76, 2, 0x6e)])
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   e5364 (WORD 7a = 2 -> 1) -> e536c RTS at an odd A7
    err('e5364-then-e536c', 0xe5364, odd, 0xe536c, a7=SP + 1, puts=[(NODE + 0x7a, 2, 2)])
    #   eb9c4 copies WORD 7a -> 7e, eb9dc (D3 = 0) -> eb9e2 RTS at an odd A7
    err('eb9c4-then-eb9e2', 0xeb9c4, odd, 0xeb9e2, a7=SP + 1)
    #   4e152 -> 4e158 (BYTE 9c(100a6c)) -> 4e164 RTS at an odd A7
    err('4e152-then-4e164', 0x4e152, odd, 0x4e164, a7=SP + 1)
    #   b3dcc -> b3ddc (A0 := b41be) -> b3ea2 reads WORD 76 of an odd node
    err('b3dcc-then-b3ea2', 0xb3dcc, odd, 0xb3ea2, a6=NODE + 1)
    #   51602 -> 515e0 pushes WORD D2 at an odd A7
    err('51602-then-515e0', 0x51602, odd, 0x515e0, a7=SP + 1)
    #   4b6fc (C Set) -> 4b700 RTS at an odd A7
    err('4b6fc-then-4b700', 0x4b6fc, odd, 0x4b700, a7=SP + 1)
    #   e56c0 (D0 = 7) -> e56d0 -> e56e6 ... -> e5720 RTS at an odd A7
    err('e56c0-then-e5720', 0xe56c0, odd, 0xe5720, d0=7, a7=SP + 1)


def main():
    rng = random.Random(0xF41)
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
    print('b3dbc targets', sorted(hex(d['stop']) for d in singles if d['entry'] == 0xb3dbc), 'b3fc6 targets', sorted(hex(d['stop']) for d in singles if d['entry'] == 0xb3fc6))
    print('handler stops', sorted(set(hex(d['stop']) for d in singles if d['entry'] in (0xb3f3a, 0xb3fb2))))
    print('chain rows', sorted((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2))
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
