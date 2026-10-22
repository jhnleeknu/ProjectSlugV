"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr8_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
only data areas, never code bytes of the unit): the bank-window LONGs 200038 / 200094 / 200138 and the LONG table behind 200138 (2a5fc0..2a6044:
aeaca, indices -10..11 LONGs), the LONG table 4376c..437ac (42e6e), the LONG table 38f0c..38f14 (38eec, BYTE 99 = 0 / 1), the LONG table
cdf3a..cdf56 (cdce4, indices -1..5; the records it points to are declared RAM records 10fc00 + 10 k) and the rectangle ae6a8 (1ab02 of aea18).  A
native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there), as is a run that lands inside the unit on a PC that
is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG 96(A6) := the emitter record GREC 10fb00, LONG 82(A6) := 10e400,
LONG c(A6) := the parent 10eb00), A0 = 10e400 / 10ea00, A1 = GREC / 10ea00, A2 = 100cb8 / 10e400, A5 = 108000 (WORD 5418), the 28ae free list
(WORD 104ca0, LONG 104c9c, links +8), seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7, the declared stack values the
entered block pops, and the hint worlds of the V1 spec (tools/unit_fixture_specs/fr8.py hint_worlds, converted to absolute addresses; 'mirror' puts the
node at 1fe000, 'grec_mirror' the record at 1ffb00, 'a5_mirror' A5 at 1f8000).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer (only producers that read RAM / the synthetic bytes and write no PVC port; the generator
            keeps a chain when it produced both C values): stop = the consumer's successor.  The others have declared-C rows only (V1 and the
            real-ROM differential run the real chains).
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: d3822 / d3a5a (ORI.B #1,CCR) Set.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr8_test_table.py  (rewrites the generated section in place)
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
import fr8 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr8_test.cpp'
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
GREC, GTAB = B.GREC, B.GTAB
CREC = 0x10fc00                                     # RAM records behind the synthetic cdf3a table (cdce4)
BANK_TABLE = 0x2a6000                               # the synthetic destination of the bank-window LONG 200138 (CPU address with bank base 200000)
FREE = [0x10c000 + 0x100 * i for i in range(8)]     # the 28ae free list


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (never code bytes of the unit)."""
    w = lambda v: struct.pack('>H', v & 0xffff)
    l = lambda v: struct.pack('>I', v & 0xffffffff)
    out = []
    out.append((0x200038, l(0x2a2000)))                                                                              # 42da4 (stored only)
    out.append((0x200094, l(0x2a3000)))                                                                              # 42f62 (stored only)
    out.append((0x200138, l(BANK_TABLE)))                                                                            # aeaca
    out.append((BANK_TABLE - 0x40, b''.join(l(0x2a7000 + 0x40 * k) for k in range(34))))                             # 2a5fc0..2a6048 (index -10..17 LONGs)
    out.append((0x4376c, b''.join(l(0x2a8000 + 0x40 * k) for k in range(16))))                                      # 42e6e (index 0..f)
    out.append((0x38f0c, l(0x2a9000) + l(0x2a9100)))                                                                # 38eec (BYTE 99 = 0 / 1)
    out.append((0xcdf3a, b''.join(l(CREC + 0x10 * k) for k in range(7))))                                           # cdce4 (index -1..5)
    out.append((0xae6a8, w(0xffd0) + w(0xffe0) + w(0x60) + w(0x90)))                                               # 1ab02 (aea18)
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


# consumer -> (C clear successor, C set successor)
SUCC = {0x38fb4: (0x38fbc, 0x39076), 0xae936: (0xae93e, 0xae93a), 0xaea22: (0xaea36, 0xaea26), 0xcdd0c: (0xcdd10, 0xcdd16),
        0xd3814: (0xd3826, 0xd3818), 0xd3a4c: (0xd3a5e, 0xd3a50)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM / synthetic bytes and both C values occur
CHAIN_CANDIDATES = tuple(B.CHAINS)


def scc_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (this unit has no SCC / SCS consumer)."""
    return 1 if o['stop'] == SUCC[cons][0] else 2


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
        return None                                 # FR8 writes no PVC port (a producer that does is dropped here)
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
VB = tuple(B.VB)
VW = tuple(B.VW)
VL = tuple(B.VL)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
POINTERS = set(B.POINTERS)
STACK = dict(B.STACK)


def fields(s):
    out = []
    for a, mn, op, size, full in B.block_instrs(s):
        if mn in ('lea', 'jsr', 'jmp', 'pea', 'movem', 'bsr', 'bra'):
            continue
        sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'scs', 'scc', 'abcd'):
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, REC1)),
                a1=rng.choice((GREC, REC1)), a2=rng.choice((PLAYER1, CHILD)), a3=REC1, a4=REC1, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 5, 8, 9, 0x12340001, 0xffff, 0x8000, 0x10000, 0x100, 0x12340002))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0x8000, 0xffff, 0x123456a5))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG, the node links and the pointer fields are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the declared emitter record GREC (LONG 96(A6)) with its child-value table GTAB, the cdce4 records CREC + 10 k, the node links, the free list
    r.put(GREC, 1, rng.choice((0, 0, 1, 0xff)))
    r.put(GREC + 1, 1, rng.choice((0, 1, 2, 8, 0xff)))
    r.put(GREC + 2, 2, rng.choice((0, 1, 2, 3, 8, 0x8000, 0xffff)))
    for off in (4, 6, 8, 0xa):
        r.put(GREC + off, 2, rng.choice((0, 1, 0x10, 0x20, 0x70, 0xffc8, 0x7fff, 0x8000, 0xffff, rand_val(rng, 2))))
    r.put(GREC + 0xc, 1, 0)
    r.put(GREC + 0xd, 1, rng.choice((0, 0, 1, 0x80)))
    r.put(GREC + 0xe, 4, rng.choice(B.CHILD_VALUES + (GTAB, GTAB)))
    for k in range(16):
        r.put(GTAB + 4 * k, 4, rng.choice(B.CHILD_VALUES))
    for k in range(7):
        for off in (0, 2, 6):
            r.put(CREC + 0x10 * k + off, 2, rng.choice((0, 1, 0x7fff, 0x8000, 0xffff, 0x0c59, rand_val(rng, 2))))
    r.put(NODE + 0x96, 4, rng.choice((GREC, GREC, REC1)))
    r.put(NODE + 0x82, 4, rng.choice(B.N32_ACTIONS))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    for a in (PARENT, CHILD, REC1):
        for off in (0x12, 0x13):
            r.put(a + off, 1, rand_val(rng, 1))
    r.put(A5 + 0x5418, 2, rand_val(rng, 2))
    n = rng.choice((0, 5, 0x40))
    r.put(0x104ca0, 2, n)
    r.put(0x104c9c, 4, FREE[0] if n else 0)
    for i in range(8):
        r.put(FREE[i] + 8, 4, FREE[i + 1] if i + 1 < 8 else 0)
    pops = []
    for size, kind in STACK.get(s, ()):
        n = 4 if size == 'L' else 2
        v = {'node': rng.choice((CHILD, REC1, PLAYER1)), 'grec': GREC, 'count': rng.choice((0, 1, 2, 3, 0x8000, 0x8001, 0xffff)),
             'any': rand_val(rng, n)}[kind]
        pops.append((n, v))
    depth = sum(n for n, v in pops)
    at = SP - depth
    for n, v in pops:
        r.put(at, n, v)
        at += n
    regs['a7'] = SP - depth
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        if hint.get('grec') is not None:
            r.put(NODE + 0x96, 4, GREC)
            for off, n, v in hint['grec']:
                r.put(GREC + off, n, v)
        for off, n, v in hint.get('a2off', []):
            a = (regs['a2'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        if hint.get('grec_mirror'):
            r.put(NODE + 0x96, 4, GREC | 0xf0000)       # the emitter record through the upper RAM mirror
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
        if hint.get('a5_mirror'):
            regs['a5'] = A5 | 0xf0000                   # A5 in the upper RAM mirror (1f8000 = 108000)
        if hint.get('stack'):
            at = regs['a7']
            for n, v in hint['stack']:
                r.put(at, n, v)
                at += n
    if regs['a1'] not in (GREC, REC1) and not (0x100000 <= regs['a1'] < 0x200000):
        pass
    return r, regs


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x28ae, 0x2986, 0x2a00, 0x3af8, 0x8ebe, 0x1ab02, 0x3a4da, 0x3a5be, 0x3b288, 0x3b302, 0x3b334, 0x3b424, 0x4356e, 0x43e34, 0x443d2, 0x4706c,
                 0x49214, 0x49290, 0x4970a, 0x497a6, 0x49a58, 0x49a84, 0x49f8c, 0x49fc6, 0x4a496, 0x4ae4a, 0x4b54e, 0x4be06, 0x4be2c, 0x4be34, 0x4c0ac,
                 0xc6a96, 0x38ff4, 0x39076, 0x39156, 0x395dc, 0x395f8, 0x3976a, 0x398be, 0x39b72, 0x39db4, 0x3a350, 0xcdc1c, 0xcdd2e, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET             # a path ends at a consumer


def hints(s):
    """The V1 spec hint worlds (fr8.hint_worlds) of the block; converted to absolute addresses by world()."""
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
                continue                                 # a computed jump back to its own block: a stop at the entry is a zero-step run
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


PATH_ENTRIES = (0x38e92, 0x38eb4, 0x38ee2, 0x38f14, 0x38f22, 0x38f2a, 0x38f3c, 0x38f44, 0x38f56, 0x38f6e, 0x38f78, 0x38f98, 0x38fc4, 0x42e0c, 0x42e24,
                0x42e3c, 0x42e88, 0x42e8e, 0x42e9e, 0x42eb0, 0x42ec8, 0x42ed8, 0x42f08, 0x42f38, 0x42f92, 0x42f9a, 0x42fd4, 0x42ffa, 0x43030, 0x43048,
                0xae93e, 0xae948, 0xae9b4, 0xaea54, 0xaea78, 0xaea92, 0xaeab0, 0xaeb08, 0xaeb38, 0xcdc24, 0xcdc46, 0xcdce4, 0xd3500, 0xd3528, 0xd3532,
                0xd355a, 0xd3570, 0xd3826, 0xd384a, 0xd386c, 0xd3880, 0xd38ac, 0xd3a2e, 0xd3a5e, 0xd39f6, 0xcc7b4, 0x42fa2, 0x42faa, 0x42fae)


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
            if any(p in CONS_SET for p in ex) or not allowed(o['stop']) or o['stop'] == s:
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
    if entry == 0x38fa2:                                         # 3a4da: BYTE b2(A6) != 0 -> 3a5b8 (Clear); 0 -> the 4d6b4 path (BYTE 10f001 bit 2)
        r.put(NODE + 0xb2, 1, rng.choice((0, 0, 1, 0x18, 0xff)))
        r.put(0x10f001, 1, rng.choice((0, 4, 0xff)))
    if entry == 0xae930:                                         # 4b54e: LONG 56(A6) = 0 -> 4b6be; a hit record otherwise
        r.put(NODE + 0x56, 4, rng.choice((0, 0, REC1)))
        r.put(A5 + 0x5744, 1, rng.choice((0, 0x80)))
        r.put(A5 + 0x5b84, 1, rng.choice((0, 1)))
        r.put(NODE + 0x5e, 1, rng.choice((0, 1, 0x19)))
    if entry == 0xaea18:                                         # 1ab02: LONG positions on / off the screen
        for off in (0x42, 0x46, 0x4a, 0x4e):
            r.put(NODE + off, 4, rng.choice((0, 0x00100000, 0x00a00000, 0x01500000, 0x7fff0000, 0x80000000, 0xfff00000, rng.getrandbits(32))))
        r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0xcdd06:                                         # 497a6: BYTE 10fd92 = 0 -> ORI Set
        r.put(0x10fd92, 1, rng.choice((0, 1, 0x80)))
    if entry in (0xd3802, 0xd3a38):                              # 28ae: the free-list count decides success / failure
        n = rng.choice((0, 5, 0x40))
        r.put(0x104ca0, 2, n)
        r.put(0x104c9c, 4, FREE[0] if n else 0)
        if entry == 0xd3a38:
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((1, 2))
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
            assert scc_value(cp, o) == carry, (hex(cp), carry)
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags (or the written BYTE) decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        clr, st = SUCC[cons]
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry)
            o = native(r.b, regs, entry, 0, lambda q, tr: q in (clr, st) and len(tr) > 0 and cons in tr)
            if o is None or cons not in o['trace']:
                continue
            c = scc_value(cons, o)
            if seen.get(c, 0) >= 3:
                continue
            seen[c] = seen.get(c, 0) + 1
            rows.append((k, r, regs, o, c))
            if len(seen) == 2 and min(seen.values()) >= 3:
                break
        print('chain %x -> %x: %s' % (entry, cons, dict(seen)))
        if set(seen) != {1, 2}:
            continue                                             # the producer reads ROM data / writes ports or one C value never occurred: declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=GREC, a2=PLAYER1, a3=0, a4=0, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr8 caller requires known carry', cp, stop=SUCC[cp][0])
    # odd node (MOVE.W 8c(A6),D0 read; MOVE.L #6f364,7c(A6) write), odd stack (MOVEM.L (A7)+,D0 of 38f8e, MOVE.L (A7)+,D1 of d3a5e, MOVE.L
    # A1,-(A7) of d3802), odd record (MOVE.W 2(A0),9e(A6) of d3500): the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-cdc24', 0xcdc24, odd, 0xcdc24, stop=0xcdc2c, a6=NODE + 1)
    err('odd-node-42da4', 0x42da4, wodd, 0x42da4, stop=0x42dd2, a6=NODE + 1)
    err('odd-stack-38f8e', 0x38f8e, odd, 0x38f8e, stop=0x38f98, a7=SP + 1)
    err('odd-stack-d3a5e', 0xd3a5e, odd, 0xd3a5e, stop=0xd3a6e, a7=SP + 1)
    err('odd-stack-d3802', 0xd3802, odd, 0xd3802, stop=0xd3814, a7=SP + 1)
    err('odd-record-d3500', 0xd3500, odd, 0xd3500, stop=0xd3518, puts=((NODE + 0x96, 4, GREC + 1),))
    # the computed jump lands inside its own block: D0.W = ffff -> 42f9e
    err('42f9a-to-42f9e', 0x42f9a, 'unsupported animation objects fr8 PC', 0x42f9e, d0=0xffff)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('cc7b4-then-cdc1c', 0xcc7b4, wodd, 0xcdc1c, a6=NODE + 1)
    err('42f9a-then-42ff0', 0x42f9a, odd, 0x42ff0, stop=0x3af8, d0=1, a7=SP + 1)
    err('42fec-then-430ba', 0x42fec, odd, 0x430ba, stop=0x2986, a7=SP + 1)
    err('d39f6-then-d3a38', 0xd39f6, odd, 0xd3a38, stop=0x28ae, d0=1, a7=SP + 1)
    err('aeb44-then-aeb4a', 0xaeb44, odd, 0xaeb4a, a7=SP + 1)


def main():
    rng = random.Random(0xF84B)
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
