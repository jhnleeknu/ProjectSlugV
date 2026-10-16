"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b3b_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM, stack in
work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data): the record 2b3d0..2b3f0
(LONG 9e(A6) = 2b3d0), the path list 2c7a6..2c7fe (LONG 98(A6) = 2c7a6, installed by 2c974) and the two LONGs 2b6de..2b6e6 that 1ab02 reads (2ca48).
A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there).  World: zero work RAM, return LONG 000ff000 at
A7 = 10f000, node A6 = 10e000, A5 = 108000, input WORD A0 = 10e400, records 10e800 (LONG 9e) / 10e900 (LONG 78), path list 10ea00 (LONG 98), seeded
BYTE / WORD / LONG node field edits, seeded D0-D7.  Rows:
  single 1  one block: entry = block start, stop = the first PC after the first instruction that is a block start of the unit or outside it.
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, B3a / N28 exit).
  single 2  a consumer entered through its real producer (2b532 -> 2bb66 2bd06 2bea2 2bf9c, 1ab02 -> 2ca52; 2b418 reads ROM tables): stop = the
            consumer's successor; the native branch on the real flags decides it.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error and the failing PC (review 0264 L-1).
2bd58 (BMI, two predecessors 2bd48 / 2bd56) is folded into both; the native block runs through it to 2bd5c / 2bd76.  Known C is never read from the
Unicorn SR after a run: consumer rows check the native branch outcome against the declared / modelled C.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b3b_test_table.py  (rewrites the generated section in place)
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
import b3b as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b3b_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, PARENT, REC9E, REC78, PATH = 0xff000, 0x10f000, 0x10e000, 0x108000, 0x10e400, 0x10e800, 0x10e900, 0x10ea00
ROM_RECORD, ROM_PATH, ROM_BOX = 0x2b3d0, 0x2c7a6, 0x2b6de


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    srng = random.Random(0xB3B5)
    record = bytes.fromhex('00018000' '0000' '0003' '00024000' '0001' '0005' 'fff40000' '00030000') + bytes(srng.getrandbits(8) for _ in range(8))
    path = bytearray(srng.getrandbits(8) & 0xfe for _ in range(0x58))
    path[0x10:0x14] = bytes.fromhex('fffffff0')           # 2c7b6: WORD ffff, rewind fff0 -> 2c7a8
    path[0x54:0x58] = bytes.fromhex('fffffff4')           # 2c7fa: WORD ffff, rewind fff4 -> 2c7f0 (the original list shape)
    box = bytes.fromhex('00100020' '00300040')
    return [(ROM_RECORD, record), (ROM_PATH, bytes(path)), (ROM_BOX, box)]


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
SUCC = {0x2bb66: (0x2bb6a, 0x2bef6), 0x2bd06: (0x2bd0a, 0x2bef6), 0x2bea2: (0x2bea6, 0x2bef6), 0x2bf9c: (0x2bfa0, 0x2bef6),
        0x2bee8: (0x2bef2, 0x2beec), 0x2bfa8: (0x2bfb2, 0x2bfac), 0x2c074: (0x2c084, 0x2c078), 0x2ca52: (0x2ca64, 0x2ca56)}
assert set(SUCC) == CONS_SET
PRODUCER = {0x2bb66: 0x2bb62, 0x2bd06: 0x2bd02, 0x2bea2: 0x2be9e, 0x2bf9c: 0x2bf98, 0x2bee8: 0x2bee4, 0x2bfa8: 0x2bfa4, 0x2c074: 0x2c070, 0x2ca52: 0x2ca48}


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


def native(ram, regs, pc, carry, stopfn, n_flag=False):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2000 | (1 if carry == 2 else 0) | (8 if n_flag else 0))
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


def model(executed, carry):
    c = carry
    for p in executed:
        if p not in CONS_SET:
            c = 0
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
VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x10, 0x18, 0x30, 0x4f, 0x50, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x0c, 0x82, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fffffff, 0x80000000, 0xfff00000, 0xffffffff, 0x123456, 0xc0000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = {0x78, 0x9e, 0x98, 0x94, 0x56}


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'smi', 'sne') and '(a' in op:
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


def world(rng, fl, hint=None):
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=0x44440003, d4=rng.getrandbits(32), d5=rng.getrandbits(32),
                d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=PARENT, a1=rng.choice((0x10c000, 0x6795e)), a2=rng.choice((0x10c100, 0x6a210)),
                a3=0xa3a3a3a3, a4=rng.choice((REC78, REC9E)), a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 5, 8, 9, 0xa, 0x10, 0x20, 0x40, 0x80, 0xff, 0x7f, 0x8000, 0x10101, 0xffff, 0x4000, 0xc0000))
    base_of = {6: NODE, 0: PARENT, 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp == 0 or disp in POINTERS):
            continue                                    # (A6) callback LONG and the pointers are declared below
        r.put((base_of[reg] + disp) & 0xffffffff, size, rand_val(rng, size))
    r.put(NODE + 0x78, 4, REC78)
    r.put(NODE + 0x9e, 4, REC9E if rng.random() < 0.7 else ROM_RECORD)
    r.put(NODE + 0x98, 4, rng.choice((0, 0, PATH, PATH + 4, ROM_PATH, ROM_PATH + 0x54)))
    r.put(NODE + 0x94, 4, rng.getrandbits(32))
    r.put(NODE + 0x56, 4, rng.getrandbits(32))
    r.put(REC9E + 0, 4, rand_val(rng, 4))
    r.put(PARENT, 2, rand_val(rng, 2))
    r.put(PATH, 2, rng.choice((0x1234, 0xffff)))
    r.put(PATH + 2, 2, rng.choice((0xfffc, 0x4, 0x5678, 0)))
    r.put(PATH + 4, 2, rng.choice((0xffff, 0x9abc)))
    r.put(PATH + 6, 2, rng.choice((0xfff8, 0xfffa, 0x2)))
    r.put(PATH + 8, 2, rng.getrandbits(16))
    r.put(PATH - 4, 4, rng.getrandbits(32))
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
    bits = (0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x0c, 0x82, 0x42, 0xff, 0x100)
    if s in (0x2bb30, 0x2bc7a, 0x2be4a, 0x2c026, 0x2c0b2, 0x2bf32):
        h += [dict(puts=[(PARENT, 2, v)]) for v in bits]
    if s == 0x2bf32:
        h += [dict(puts=[(PARENT, 2, v), (NODE + 0x81, 1, f)]) for v in (0, 2, 8) for f in (0, 0xff)]
    if s in (0x2baf4, 0x2bbf6, 0x2bc10, 0x2bc2a, 0x2bc44, 0x2bd5c, 0x2bd76, 0x2bde0):
        h += N(0x7f, 1, (0, 6, 7, 8, 0xff))
    if s in (0x2bcd8, 0x2be74):
        h += N(0x7f, 1, (4, 5, 6, 0xff))
    if s in (0x2bb1c, 0x2be36, 0x2bf1e, 0x2c012, 0x2c09e, 0x2bd9a, 0x2bb7e, 0x2bba0, 0x2bbb6, 0x2bbdc, 0x2bd48, 0x2c9d6):
        h += N(0x15, 1, (0, 0x80, 1, 0x81, 0x7f))
    if s in (0x2bcb4, 0x2bcc8, 0x2bde0, 0x2bd48):
        h += N(0x64, 4, (0, 1, 0x7fffffff, 0x80000000, 0xffffffff))
    if s in (0x2bb7e, 0x2bba0, 0x2bbb6, 0x2bbdc, 0x2bf3c, 0x2c026):
        h += [dict(puts=[(NODE + 0x9e, 4, REC9E), (REC9E, 4, v)]) for v in (0, 1, 0x80000000, 0xffffffff, 0x18000)]
        h += [dict(puts=[(NODE + 0x9e, 4, ROM_RECORD)])]
    if s in (0x2bd36, 0x2bece):
        h += [dict(puts=[(NODE + 0x7e, 1, a), (NODE + 0x82, 1, b)]) for a, b in ((0, 0), (0x80, 0), (0x80, 0x80), (1, 0x81), (0x7f, 0xff))]
    if s == 0x2bdaa:
        h += N(0x9d, 1, (0, 1, 3, 5, 0xff))
    if s == 0x2bdb4:
        h += [dict(regs=dict(d0=d), puts=[(NODE + 0x9c, 1, v)]) for d, v in ((5, 0x50), (5, 0x4f), (3, 0x30), (0x10f, 0xf0), (0, 0), (0xfffffff1, 0x0f))]
    if s == 0x2bdbe:
        h += N(0x9d, 1, (0, 1, 5))
    if s == 0x2bdd6:
        h += N(0x7e, 1, (0, 1, 0x80))
    if s == 0x2be0a:
        h += [dict(puts=[(NODE + 0x15, 1, b), (NODE + 0x85, 1, v)]) for b in (0, 1) for v in (0, 0xff, 1)]
    if s in (0x2be54, 0x2be68):
        h += N(0x85, 1, (0, 0x7f, 0x80, 0xff))
    if s in (0x2bfb2, 0x2bfba):
        h += [dict(puts=[(NODE + 0x82, 1, a), (NODE + 0x7e, 1, b)]) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
    if s == 0x2bff2:
        h += [dict(puts=[(NODE + 0x7e, 1, a), (NODE + 0x82, 1, b)]) for a, b in ((1, 1), (1, 2), (0xff, 0x7f))]
    if s == 0x2c9a8:
        h += N(0x98, 4, (0, 1, 0x80000000, PATH, ROM_PATH, ROM_PATH + 0x54))
    if s == 0x2c9b4:
        h += [dict(regs=dict(a0=v)) for v in (ROM_PATH + 0x54, ROM_PATH, ROM_PATH + 0x10, PATH, PATH + 4)]
    if s == 0x2c9c4:
        h += [dict(regs=dict(a0=v)) for v in (ROM_PATH + 0x56, ROM_PATH + 0x12, PATH + 2, PATH + 6)]
    if s == 0x2c9fa:
        h += N(0x61, 1, (0, 1, 0xfe, 0xff))
    if s == 0x2c9e8:
        h += [dict(regs=dict(d0=d), puts=[(NODE + 0x64, 4, v)]) for d, v in ((0xc0000, 0), (0xfff40000, 0x7fffffff), (0, 0x80000000), (0x1f, 0), (0x20, 0x40))]
    if s == 0x2ca14:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3, 8, 9, 0x10, 0xffff, 0x10001, 0x8000)]
    if s == 0x2ca1c:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0x4000, 0x14001)]   # 9 -> 2ca48; 4000*4 wraps to 2ca24 (fffe -> 2ca1c = entry: no row)
    if s == 0x2bd48:
        h += [dict(puts=[(NODE + 0x64, 4, v)]) for v in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff)]
    if s == 0x2bd56:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff)]
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
            r, regs = world(rng, fl, hint)
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
                continue                                # a stop equal to the entry is a zero-step run (2ca1c with D0.W = fffe loops to itself)
            if not hint and sum(1 for k in kept if (k[0] if isinstance(k, tuple) else k) == nxt) >= 2:
                continue
            kept[key] = (r, regs, o)
            if t >= len(hs) and len(kept) >= 6:
                break
            if t >= len(hs) and t > 120 and len(kept) >= 2:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, 0, 1, o)


PATH_ENTRIES = (0x2baf4, 0x2bb1c, 0x2bb30, 0x2bb7e, 0x2bb9a, 0x2bbb6, 0x2bbd6, 0x2bc7a, 0x2bcac, 0x2bcd8, 0x2bd0e, 0x2bd36, 0x2bd48, 0x2bd9a, 0x2bdaa,
                0x2bdd6, 0x2bde0, 0x2be0a, 0x2be36, 0x2be4a, 0x2be74, 0x2beaa, 0x2bece, 0x2bef6, 0x2bf1e, 0x2bf32, 0x2bf60, 0x2bfb2, 0x2bff2, 0x2c012,
                0x2c026, 0x2c09e, 0x2c0b2, 0x2c96a, 0x2c9a8, 0x2c9d6, 0x2c9fa, 0x2ca14, 0x2ca1c)


def gen_paths(rng):
    fl = []
    for b in STARTS:
        fl += fields(b)
    fl = sorted(set(fl))
    for s in PATH_ENTRIES:
        kept = {}
        for t in range(200):
            carry = rng.choice((0, 1, 2))
            r, regs = world(rng, fl)
            if s == 0x2ca1c:
                regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(9)
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


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=PARENT,
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
    # real producers.  2b532 (B3a): WORD 92 != 0 -> 2b602 ANDI Clear; WORD 92 = 0 and 4d6b4 (B2b) Clear (BYTE 10f001 bit 2 clear, BYTE 25 of the
    # player slot 0) -> 2b602 Clear; 4d6b4 Set -> 2b548 (28ae child 2d7be ... 4c2fa) -> 2b5fc ORI Set (kept when the native run completes).
    for cp in (0x2bb66, 0x2bd06, 0x2bea2, 0x2bf9c):
        entry = PRODUCER[cp]
        clr, st = SUCC[cp]
        seen = set()
        for k in range(60):
            rng2 = random.Random(0x2B532 + 97 * k + cp)
            r = base_ram()
            mode = k % 3
            r.put(NODE + 0x92, 2, rng2.choice((1, 0x18, 0x8000)) if mode == 0 else 0)
            d0 = rng2.choice((0, 1))
            r.put(NODE + 0x88, 2, d0)
            r.put(0x10f001, 1, 4 if mode == 2 and k % 2 else 0)
            r.put(A5 + (0x5cba if d0 == 0 else 0x5ce6) + 0x25, 1, (rng2.choice((1, 3)) if mode == 2 and not k % 2 else 0))
            r.put(NODE + 0x78, 4, REC78)
            for o_ in range(2, 6):
                r.put(REC78 + o_, 1, rng2.getrandbits(8))
            r.put(NODE + 0x15, 1, rng2.choice((0, 1, 0x80, 0x81)))
            r.put(NODE + 0x84, 1, rng2.choice((4, 5)))
            for o_ in (0x60, 0x1e, 0x8c):
                r.put(NODE + o_, 2 if o_ != 0x60 else 1, rng2.getrandbits(16))
            regs = dict(PLAIN)
            o = native(r.b, regs, entry, 0, lambda p, tr: p in (clr, st))
            if o is None:
                continue
            c = 1 if o['stop'] == clr else 2
            if (c, mode) in seen:
                continue
            seen.add((c, mode))
            row('chain-%x-2b532-%x-m%d' % (entry, cp, mode), r, regs, entry, o['stop'], 0, c, 2, o)
        assert any(c == 1 for c, m in seen), hex(cp)
    # 2b418 (N28) reads its fixed ROM tables 2b2ec / 2b330 / 2b374 (BYTE 7c) and runs the interpreter 49fc6 on ROM scripts: no synthetic world here.
    # Its consumers 2bee8 2bfa8 2c074 are covered by the declared C rows here and by the real-producer chains of the V1 spec / real-ROM differential.
    # 1ab02 (U05): the LONG pair at 2b6de (synthetic) against the node position fields 42 / 46 / 4a / 4e and BYTE 15 -> 1aafc Set / 1ab7a Clear.
    counts = {}
    for k in range(80):
        rng2 = random.Random(0x1AB02 + k)
        r = base_ram()
        for o_ in (0x42, 0x46, 0x4a, 0x4e):
            r.put(NODE + o_, 4, rng2.choice((0, 0x10000, 0x800000, 0x1000000, 0xff000000, rng2.getrandbits(32))))
        r.put(NODE + 0x15, 1, rng2.choice((0, 1, 2, 3)))
        regs = dict(PLAIN)
        o = native(r.b, regs, 0x2ca48, 0, lambda p, tr: p in (0x2ca64, 0x2ca56))
        if o is None:
            continue
        c = 1 if o['stop'] == 0x2ca64 else 2
        if counts.get(c, 0) >= 3:
            continue
        counts[c] = counts.get(c, 0) + 1
        row('chain-2ca48-1ab02-%d' % k, r, regs, 0x2ca48, o['stop'], 0, c, 2, o)
    assert set(counts) == {1, 2}, counts


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=PARENT, a1=0x10c000, a2=0, a3=0, a4=0, a5=A5, a6=NODE, a7=SP)

    def err(name, entry, message, fail_pc, carry=0, puts=(), **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects b3b caller requires known carry', cp)
    # fixed ROM data read outside the declared synthetic bytes: record LONG at 2b3f0 / path WORD at 2c7fe -> checked error in the entry block
    err('2bb7e-outside-record', 0x2bb7e, 'missing or ambiguous physical program bus ROM byte', 0x2bb7e, puts=[(NODE + 0x9e, 4, ROM_RECORD + 0x20)])
    err('2c9b4-outside-path', 0x2c9b4, 'missing or ambiguous physical program bus ROM byte', 0x2c9b4, a0=ROM_PATH + 0x58)
    # odd node / odd pointers: WORD / LONG accesses at an odd address
    err('odd-node-2baf4', 0x2baf4, 'invalid animation machine write size/alignment', 0x2baf4, a6=NODE + 1)
    err('odd-node-2bcb4', 0x2bcb4, 'program bus requires even WORD/LONG address', 0x2bcb4, a6=NODE + 1)
    err('odd-input-2bb30', 0x2bb30, 'program bus requires even WORD/LONG address', 0x2bb30, a0=PARENT + 1)
    err('odd-record-2bb7e', 0x2bb7e, 'program bus requires even WORD/LONG address', 0x2bb7e, puts=[(NODE + 0x9e, 4, REC9E + 1)])
    # failure after executed blocks: 2c9a8 loads A0 = LONG 98 (odd) and passes; 2c9b4 stores BYTE 14 and then fails on MOVE.W (A0)+,D1
    err('odd-path-2c9a8', 0x2c9a8, 'program bus requires even WORD/LONG address', 0x2c9b4, puts=[(NODE + 0x98, 4, PATH + 1), (NODE + 0x1a, 1, 0x5a)])
    # the table jump without the 2ca14 limit lands inside a block: 2ca4c (2ca48 block), 2ca20 (2ca1c block), 2c9e4 (the middle of the BEQ.W of 2c9d6)
    err('table-2ca1c-a', 0x2ca1c, 'unsupported animation objects b3b PC', 0x2ca4c, d0=0xa)
    err('table-2ca1c-ffff', 0x2ca1c, 'unsupported animation objects b3b PC', 0x2ca20, d0=0xffff)
    err('table-2ca1c-3ff0', 0x2ca1c, 'unsupported animation objects b3b PC', 0x2c9e4, d0=0x3ff0)
    # a store before the failure: 2bdb4 stores BYTE 9c, 2bdbe stores BYTE 9d, then 28ae with an odd A6 fails (fail PC 2bdbe: SUBQ.B passes, the
    # WORD stack write of the JSR is fine; the run with an odd node fails in 28ae) -- kept out: the failing PC would be inside another executor.


def main():
    rng = random.Random(0xB3B)
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
    print('chain rows', sorted((hex(d['entry']), hex(d['stop']), d['c']) for d in ROWS if d['single'] == 2))


if __name__ == '__main__':
    main()
