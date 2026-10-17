"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b4_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data): the bank-window LONGs
20006c..200098, the sin / cos WORDs 4411e..4439e, the WORD table 22d82..22d94, the LONG lists 22a02..22a0e and 235b6..235c2 and the 1ab80 rectangle
235c2..235ca.  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there).
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000, child record A0 = 10e400, A4 record 10e800, A1 / A2 records 10ea00 /
10e900, A5 = 108000 (player records 10d450 / 10d460, grid 10db88), the RAM list 10ec80 (two LONGs and the 0 end), the 28ae free node 10ed00 and the
node link LONG 8(A6) = 10ec00, seeded BYTE / WORD / LONG field edits, seeded D0-D7.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the first instruction that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP 2a00, the RTS sentinel).
  single 2  a consumer entered through its real producer (28ae -> 23190 23284 231de 232be, 287e -> 23336, 1ab80 -> 236be): stop = the consumer's
            successor; the native branch on the real flags decides it.  49fc6 runs ROM scripts: its two consumers have declared-C rows here (real chains in V1).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C; the ORI.B #1,CCR
blocks are the only producers (C Set, contract decision 5).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b4_test_table.py  (rewrites the generated section in place)
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
import b4 as B                                      # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b4_test.cpp'
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
REC4, REC2, REC1, RAMLIST, FREE, LINK = 0x10e800, 0x10e900, 0x10ea00, 0x10ec80, 0x10ed00, 0x10ec00
ROM_BANK, ROM_SIN, ROM_SOUND, ROM_LIST1, ROM_LIST2 = 0x20006c, 0x4411e, 0x22d82, 0x22a02, 0x235b6
LISTS = (0x22a02, 0x22a06, 0x22a0a, 0x235b6, 0x235ba, 0x235be, RAMLIST, RAMLIST + 4, RAMLIST + 8)
LIST_BLOCKS = dict(B.LIST_BLOCKS)


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xB45)
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    bank = b''.join(l(srng.choice((0x00290000 | srng.getrandbits(15) << 1, srng.getrandbits(32)))) for _ in range(11))           # 20006c..200098
    sin = b''.join(w(srng.choice((0, 1, 0x100, 0xff00, 0x7fff, 0x8000, 0xffff, srng.getrandbits(16), srng.getrandbits(9) - 256))) for _ in range(320))
    sound = b''.join(w(srng.getrandbits(16)) for _ in range(9))                                                                       # 22d82: 9 WORDs
    list1 = l(0x229c6) + l(srng.getrandbits(19) << 1) + l(0)                                                                         # 22a02..22a0e
    list2 = l(srng.getrandbits(19) << 1) + l(0x23598) + l(0) + w(0xfff0) + w(0xffd0) + w(0x20) + w(0x40)                               # 235b6..235ca
    assert len(bank) == 0x2c and len(sin) == 0x280 and len(sound) == 0x12 and len(list1) == 0xc and len(list2) == 0x14
    return [(ROM_BANK, bank), (ROM_SIN, sin), (ROM_SOUND, sound), (ROM_LIST1, list1), (ROM_LIST2, list2)]


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
SUCC = {0x22d2c: (0x22d36, 0x22d30), 0x23768: (0x23772, 0x2376c), 0x23190: (0x231a2, 0x23194), 0x231de: (0x231f0, 0x231e2), 0x23284: (0x23296, 0x23288),
        0x232be: (0x232d0, 0x232c2), 0x23336: (0x23348, 0x2333a), 0x236be: (0x236c2, 0x22c82)}
assert set(SUCC) == CONS_SET


class Ram(object):
    def __init__(self):
        self.b = bytearray(65536)
        self.puts = []

    def put(self, a, n, v):
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
VB = (0, 1, 2, 3, 4, 7, 8, 0x10, 0x18, 0x20, 0x7f, 0x80, 0x81, 0xc0, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 0x10, 0x80, 0xff, 0x100, 0x13f, 0x140, 0x15f, 0x160, 0x17f, 0x180, 0x1ff, 0x200, 0x23f, 0x240, 0x7fff, 0x8000, 0x8001, 0xffe0,
      0xfff0, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fffffff, 0x80000000, 0xfff00000, 0xfff05398, 0xffffffff, 0x123456, 0xc0000, 0x1400000)
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


def world(rng, fl, s, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=CHILD, a1=rng.choice((0, REC1, REC1)),
                a2=rng.choice((REC2, 0xa2a2a2a2)), a3=0xa3a3a3a3, a4=REC4, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x7f, 0x80, 0xff, 0x100, 0x10000, 0xffff, 0x8000, 0x10101))
    if rng.random() < 0.7:
        regs['d4'] = (regs['d4'] & 0xffff0000) | rng.randrange(0x100)                       # 22a10: sin / cos index 2 * D4.W
    if 0x4bb66 <= s < 0x4bc04:
        regs['a7'] = SP - 12                                                                # inside 4bb52: the three MOVEM.L LONGs are on the stack
        for k in range(3):
            r.put(SP - 12 + 4 * k, 4, rng.getrandbits(32))
    if s in (0x4bb7c,):
        regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 2, 4, 6, 8, 0xa, 0xc, 0xe))
        regs['d1'] = (regs['d1'] & 0xffff0000) | rng.randrange(0x200)
    base_of = {6: NODE, 0: regs['a0'], 4: regs['a4'], 5: A5, 2: REC2, 1: REC1}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG and the node links are declared below
        r.put((base_of[reg] + disp) & 0xffffffff, size, rand_val(rng, size))
    r.put(NODE + 0x8, 4, LINK)
    r.put(LINK + 0x10, 2, rand_val(rng, 2))
    r.put(NODE + 0x10, 2, rand_val(rng, 2))
    for k in range(3):
        r.put(RAMLIST + 4 * k, 4, (rng.getrandbits(19) << 1) if k < 2 else 0)
    for p in (0x10d451, 0x10d461):
        r.put(p, 1, rand_val(rng, 1))
    if s in LIST_BLOCKS:
        lst = rng.choice(LISTS)
        r.put(NODE + LIST_BLOCKS[s], 4, lst)
        regs['a4'] = lst
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
    if s in (0x1c9b8, 0x1c9ce):
        h += R('d0', (0, 1, 0xfffe, 0xffff, 0x10001))
    if s in (0x1c9de, 0x1c9e6, 0x1c9c8):
        h += [dict(puts=[(REC4 + 1, 1, v)]) for v in (0, 1, 0x7f, 0xff)]
    if s == 0x22a4c:
        h += N(0x76, 2, (0, 0x7fff, 0x8000, 0xffff))
    if s == 0x22a5a:
        h += N(0x76, 2, (0, 0x7fff, 0x8000))
    if s in (0x22a62, 0x2368c):
        h += [dict(puts=[(NODE + 0x36, 4, v), (NODE + 0x3a, 4, w)]) for v, w in ((0, 0), (1, 0xfff05398), (0x80000000, 0x7fffffff), (0xffffffff, 0x80000000),
                                                                             (0x7fffffff, 0xfff00000), (0xfffffff1, 0xfff00001), (0xfffffff9, 0x1))]
    if s in (0x22a7c, 0x236a6):
        h += R('d0', (0, 0x7ffffff1, 0xfffffff1, 0x7ffffffc))
    if s in (0x22a82, 0x236a8):
        h += R('d0', (0, 0xf, 0x10, 0x80000000, 0xffffffff, 0x7fffffff, 0xfffffff0))
    if s == 0x22a10:
        h += [dict(regs=dict(d0=a, d1=b, d4=k)) for a, b, k in ((0, 0, 0), (0x7fffffff, 0x80000000, 0x40), (0x12345678, 0xfedcba98, 0x80),
                                                               (0xffffff00, 0x100, 0xff), (0x00ff0000, 0xff000000, 0xc0), (0x80000000, 0x7fffffff, 0x12340001))]
    if s in (0x22b40, 0x22b58, 0x22e02, 0x22e32, 0x230d0, 0x235e2):
        h += N(0x15, 1, (0, 1, 0xee, 0xff))
    if s == 0x22b56:
        h += R('d2', (0x280, 0, 0x8000, 0x12340001))
    if s in (0x22ba0, 0x22e5c, 0x2366e, 0x23104, 0x2310c):
        h += R('d0', (0, 1, 2, 3, 0x100, 0xff, 0x102, 0x201))
    if s in (0x22bb8, 0x22eca, 0x23124, 0x2367a):
        h += N(0x15, 1, (0, 0x7f, 0x80, 0xff))
    if s == 0x22bde:
        h += [dict(puts=[(NODE + 0x7c, 2, w), (NODE + 0x82, 1, b), (NODE + 0x80, 2, v)], regs=dict(d2=x, d3=y)) for w, b, v, x, y in (
            (0, 0, 0x280, 0x12345678, 0x9abcdef0), (1, 0x40, 0xfd80, 0x7fffffff, 0x80000000), (0xffff, 0x80, 0x8000, 0, 0), (2, 0xff, 0x7fff, 0xffffffff, 1),
            (0, 0x10, 0x1fff, 0x80000000, 0x7fffffff))]
    if s == 0x22c46:
        h += [dict(puts=[(NODE + 0x80, 2, v), (NODE + 0x7e, 2, w)]) for v, w in ((0, 0), (0x8000, 0x1fff), (0x7fff, 0xe001), (0xffe0, 0x10), (0x280, 0x1f00))]
    if s in (0x22c64, 0x22f5c, 0x23134, 0x232fc):
        h += N(0x42, 2, (0, 0x13f, 0x140, 0xffff))
    if s in (0x22c70, 0x22f68, 0x23146, 0x2330e, 0x22d4c):
        h += N(0x46, 2, (0, 0xff, 0x100, 0x23f, 0x240))
    if s == 0x22d36:
        h += N(0x42, 2, (0xffdf, 0xffe0, 0x15f, 0x160))
    if s in LIST_BLOCKS:
        h += [dict(puts=[(NODE + LIST_BLOCKS[s], 4, v)], regs=dict(a4=v)) for v in LISTS]
    if s in (0x22e48, 0x22f3a):
        h += N(0x61, 1, (0, 8, 0xf7, 0xff))
    if s == 0x22e62:
        h += R('d0', (0, 1, 4, 8, 0xff00, 0x12340003))
    if s == 0x22e76:
        h += N(0x3a, 4, (0, 0x7fffffff, 0x80000000, 0xffffffff))
    if s == 0x22e82:
        h += R('d0', (0x80000000, 0xffffffff, 0x80000001))
    if s == 0x22efa:
        h += R('d1', (0x20000, 0x30000, 0x2ffff, 0xffff0000, 0x80000000, 0x7fff0000))
    if s in (0x22f44, 0x22f32):
        h += N(0x80 if s == 0x22f44 else 0x7c, 2, (0, 1, 0xffff))
    if s == 0x23684:
        h += N(0x7e, 2, (0, 1, 0xffff))
    if s in (0x2315e, 0x23256, 0x231f0):
        h += N(0x84, 1, (0, 1, 2, 0xff))
    if s == 0x23248:
        h += N(0x80, 2, (0, 1, 2, 0x8000, 0x8001, 0x7fff))
    if s == 0x232d0:
        h += N(0x82, 1, (3, 4, 0x7f, 0x80, 0xff))
        h += N(0x64, 4, (0, 0x80000000, 1))
    if s in (0x23328, 0x2333a):
        h += N(0x83, 1, (0, 1, 0x7f, 0x80, 0xff))
    if s == 0x23342:
        h += N(0x83, 1, (0, 1, 0x80))
    if s in (0x23270, 0x231bc):
        h += N(0x82, 1, (0xff, 0x7f))
        h += N(0x32, 2, (0xfffe, 0xffff))
    if s == 0x2360a:
        h += [dict(puts=[(NODE + 0x2e + 4 * i, 4, v) for i, v in enumerate(vs)]) for vs in ((1, 2, 3, 4, 5), (0xffffffff, 0x80000000, 0x7fffffff, 0, 0x10e800))]
    if s == 0x2374e:
        h += N(0x7c, 2, (0, 0x13f, 0x140, 0xffff))
    if s == 0x2373c:
        h += [dict(puts=[(NODE + 0x14, 1, a), (NODE + 0x7c, 1, b)]) for a, b in ((0, 0xff), (0x80, 0x20))]
    if s == 0x4bb52:
        h += N(0x46, 2, (0xff, 0x100, 0x1ff, 0x200, 0))
    if s == 0x4bb66:
        h += [dict(puts=[(NODE + 0x42, 2, v)], regs=dict(d0=d)) for v, d in ((0x1f, 0), (0x20, 0xff), (0x21f, 0xe0), (0x220, 0x10), (0x120, 0xfff0))]
    if s in (0x4bb96, 0x4bbaa, 0x4bbb8, 0x4bbc6, 0x4bbdc, 0x4bbf0):
        h += R('d1', (0, 0xf, 0x10, 0xef, 0xf0, 0xffff))
    if s in (0x4bb7c, 0x4bbd4):
        h += [dict(regs=dict(d0=d, d1=e)) for d, e in ((0, 0), (1, 0x1f), (2, 0x20), (0xc, 0x1e0), (0xd, 0x1ff), (0xe, 0x100))]
    if s in (0x4bba4, 0x4bbb2, 0x4bbc0, 0x4bbce, 0x4bbea, 0x4bbf8, 0x4bb96, 0x4bbdc):
        h += [dict(puts=[(CHILD + d, 2, 0xff80)]) for d in (-0x12, -0x10, -0xe, -2, 2, 0xe, 0x10, 0x12)][:2]
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


PATH_ENTRIES = (0x1c9b8, 0x1c9ce, 0x22a4c, 0x22a62, 0x22a10, 0x22ad4, 0x22b04, 0x22b40, 0x22b96, 0x22ba0, 0x22bb8, 0x22bde, 0x22c46, 0x22c64, 0x22c98,
                0x22cb0, 0x22cf8, 0x22d06, 0x22d36, 0x22d94, 0x22dbc, 0x22e32, 0x22e48, 0x22e5c, 0x22e62, 0x22e76, 0x22eca, 0x22efa, 0x22f32, 0x22f3a,
                0x22f5c, 0x23058, 0x2308e, 0x23104, 0x23124, 0x2315e, 0x2319e, 0x231bc, 0x231f0, 0x23248, 0x23256, 0x232d0, 0x23328, 0x2333a, 0x235ca,
                0x2360a, 0x23650, 0x2366e, 0x2367a, 0x23684, 0x2368c, 0x236c8, 0x23710, 0x23726, 0x2374e, 0x4bb52, 0x4bb7c)


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
    for entry, cons in ((0x23180, 0x23190), (0x231ce, 0x231de), (0x23270, 0x23284), (0x23296, 0x232be)):
        clr, st = SUCC[cons]
        for k, (limit, free) in enumerate(((0, FREE), (0x100, FREE), (0x14, FREE), (0x15, FREE), (0x100, 0))):
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
    # 287e: MOVEA.L 8(A6),A0; MOVE.W 10(A6),D0; CMP.W 10(A0),D0 (C = D0.W < WORD 10(A0), unsigned).  Entry 23330.
    for k, (a, b) in enumerate(((0, 0), (0, 1), (1, 0), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0xffff))):
        r = base_ram()
        r.put(NODE + 0x8, 4, LINK)
        r.put(NODE + 0x10, 2, a)
        r.put(LINK + 0x10, 2, b)
        regs = dict(PLAIN)
        o = native(r.b, regs, 0x23330, 0, lambda q, tr: q in (0x23348, 0x2333a))
        assert o is not None, k
        c = 1 if o['stop'] == 0x23348 else 2
        assert c == (2 if a < b else 1), (k, hex(o['stop']))
        row('chain-23330-287e-%d' % k, r, regs, 0x23330, o['stop'], 0, c, 2, o)
    # 1ab80: the rectangle 235c2 (synthetic fff0 ffd0 0020 0040) against WORD 46 / 42 and BYTE 15 bits 0 / 1.  Entry 236b4.
    for k, (y, x, f) in enumerate(((0x180, 0xa0, 0), (0x100, 0xa0, 0), (0x210, 0xa0, 2), (0x180, 0, 1), (0x180, 0x150, 3), (0xc0, 0x20, 0), (0x1e0, 0x130, 1),
                                   (0x150, 0x10, 2))):
        r = base_ram()
        r.put(NODE + 0x46, 2, y)
        r.put(NODE + 0x42, 2, x)
        r.put(NODE + 0x15, 1, f)
        regs = dict(PLAIN)
        o = native(r.b, regs, 0x236b4, 0, lambda q, tr: q in (0x236c2, 0x22c82))
        if o is None:
            continue
        c = 1 if o['stop'] == 0x236c2 else 2
        row('chain-236b4-1ab80-%d' % k, r, regs, 0x236b4, o['stop'], 0, c, 2, o)
    # 49fc6 (the interpreter on ROM scripts): no synthetic world; the consumers 22d2c 23768 have the declared-C rows above and the real-producer
    # chains of the V1 spec / real-ROM differential.


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x10c000, a2=0, a3=0, a4=REC4, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    missing = 'missing or ambiguous physical program bus ROM byte'

    def err(name, entry, message, fail_pc, carry=0, puts=(), **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects b4 caller requires known carry', cp)
    # odd node / child / list / stack / A5: the entry block fails
    err('odd-node-22ad4', 0x22ad4, wodd, 0x22ad4, a6=NODE + 1)
    err('odd-node-22a4c', 0x22a4c, odd, 0x22a4c, a6=NODE + 1)
    err('odd-child-231a2', 0x231a2, wodd, 0x231a2, a0=CHILD + 1)
    err('odd-child-2360a', 0x2360a, wodd, 0x2360a, a0=CHILD + 1)
    err('odd-list-22d06', 0x22d06, odd, 0x22d06, puts=[(NODE + 0x8c, 4, RAMLIST + 1)])
    err('odd-cursor-23730', 0x23730, odd, 0x23730, a4=RAMLIST + 1)
    err('odd-stack-4bb52', 0x4bb52, odd, 0x4bb52, a7=SP + 1)
    err('odd-a5-4bb7c', 0x4bb7c, odd, 0x4bb7c, a5=A5 + 1)
    # fixed ROM data read outside the declared synthetic bytes (the entry block fails)
    err('22a10-index-100', 0x22a10, missing, 0x22a10, d4=0x100)
    err('22a10-index-4000', 0x22a10, missing, 0x22a10, d4=0x4000)
    err('22e62-index-9', 0x22e62, missing, 0x22e62, d0=9)
    err('22d06-list-22a0e', 0x22d06, missing, 0x22d06, puts=[(NODE + 0x8c, 4, 0x22a0e)])
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    #   22ba0 (D0.B = 0) -> 22ba6 reads LONG 36 of an odd node
    err('22ba0-then-22ba6', 0x22ba0, odd, 0x22ba6, a6=NODE + 1)
    #   22b56 NEG.W D2 -> 22b58 writes WORD 80 of an odd node
    err('22b56-then-22b58', 0x22b56, wodd, 0x22b58, a6=NODE + 1)
    #   22e82 stores LONG 3a, then 22e88 pushes the 2986 return LONG at an odd A7
    err('22e82-then-22e88', 0x22e82, odd, 0x22e88, a7=SP + 1, d0=0x80000000)
    #   23342 stores BYTE 83, then the RTS of 23346 pops at an odd A7
    err('23342-then-23346', 0x23342, odd, 0x23346, a7=SP + 1, puts=[(NODE + 0x83, 1, 5)])
    #   23260 stores WORD 80, 23270 the BYTE 82, then its JSR 28ae push fails at an odd A7
    err('23260-then-23270', 0x23260, odd, 0x23270, a7=SP + 1)
    #   4bb7c adds to the grid, 4bb96 (D0.W >= 2) then reads WORD -2(A0) ... with an odd A0 never: the grid stays even; instead 4bbd4 -> 4bbdc -> 4bbea
    #   with an odd A0 (direct entry, A0 declared): 4bbdc's ADDI.W #c0,2(A0) fails at once (failing PC = entry 4bbd4's successor)
    err('4bbd4-then-4bbdc', 0x4bbd4, odd, 0x4bbdc, a0=CHILD + 1, d0=0, d1=0x20)


def main():
    rng = random.Random(0xB4)
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
    print('chain rows', sorted((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2))
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
