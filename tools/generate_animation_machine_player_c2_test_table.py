"""Generates the native-oracle tables of engine/tests/animation_machine_player_c2_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit): the BYTE tables 1c1d8 (1c1e2), 22642 (1ce08), 1cd94 (1ce6e), the LONG tables
1d112 / 1d136 (1d170) and 1ed70 / 1ed74 (1ed6a) whose LONGs point into work RAM, and the record WORD tables 1b230 1b716 (1cb08 from 1ed78 / 1fa3c) and
1b34a 1b6c4 1b72e (1cab6 from 1f7a4 / 1ed8e / 1fa50 / 1fae8).  A native run that reads any other fixed-ROM or banked byte is dropped (a table index beyond
the declared bytes), as is a run that lands inside the unit on a PC that is not a block start, or that takes an exception.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 8c(A6) := the record 10ea00 (A4 of
1cd98 / 1d2de / 1d32e / 1f1e8), LONG 22(A6) := the LONG table 10e600 (1cad4), LONG 3e(A6) := a map buffer or not, LONG 5434(A5) := the JMP (A1) target
0 / 1c1e2 / 1ee00 / 1ce0e (ROM only), LONG 5474(A5) := 0 / the box 10e700), A0 = 10e400 / 10e800, A1 = a ROM JMP target, A4 = 10ea00, A5 = 108000,
seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 and the hint worlds of the V1 spec (tools/unit_fixture_specs/pc2.py
hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'stack' writes at A7).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, a JMP (A1) target).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, JMP exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer (RAM-only producers): 4836e -> 1d58e (1d588), 49c38 -> 1d59c (1d592) are kept when both C values
            occur; 1cb08 -> 1cb18 -> 1ed80 (1ed78) / 1fa44 (1fa3c) have only the Clear side (the Set side 1cb1a is C5): Clear-only chain rows.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
producers: 1cb08 1edf6 (MOVE.W / AND.W) and 1dff0 1ed54 (ANDI.B #fe,CCR; RTS) Clear, 1e016 (SUB.W D1,D0; RTS) the borrow, recomputed from the native
output registers (D0.W + D1.W >= 10000); 1cb18 1ed34 1ed3c 1ed3e 1ed48 keep the incoming C.
Usage:  .venv/bin/python tools/generate_animation_machine_player_c2_test_table.py  (rewrites the generated section in place)
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
import pc2 as B                                     # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_player_c2_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
CLEAR_SET, PASS_SET, DATA_SET = set(B.CLEAR_SET), set(B.PASS_SET), set(B.DATA_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, SIBLING, LTAB, BOX, RTAB = 0x10ea00, 0x10eb00, 0x10ec00, 0x10e600, 0x10e700, 0x10e800
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)
JUMPS = (0x1c1e2, 0x1ee00, 0x201a2)                 # ROM JMP (A1) targets: a C2 start, the C3 starts 1ee00 / 201a2


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x1b230, words((0, 4, 0, 6))),                                     # 1cb08 from 1ed78: 0 -> 1cb18, else 1cb1a (C5)
            (0x1b34a, words((8, 0xa, 0, 0, 1, 3, 0, 0))),                       # 1cab6 from 1f7a4
            (0x1b6c4, words((8, 0, 0xa, 0xc, 1, 2, 0, 3))),                     # 1cab6 from 1ed8e
            (0x1b716, words((0, 8, 0, 0))),                                     # 1cb08 from 1fa3c
            (0x1b72e, words((8, 8, 0, 0, 2, 0, 0, 0))),                         # 1cab6 from 1fa50 / 1fae8
            (0x1c1d8, bytes((5, 1, 3, 7, 2, 6, 4, 0, 9, 8))),                   # 1c1e2: BYTE 9e := 1c1d8[BYTE a0]
            (0x1cd94, bytes((0x7f, 0xbd, 0x0f, 0xf0))),                         # 1ce6e: AND.B 1cd94[BYTE 9e],D0
            (0x1d112, longs([RTAB + 0x20 * i for i in range(9)] + [RTAB + 0x100 + 0x20 * i for i in range(9)])),   # 1d170: LONG tables 1d112 / 1d136
            (0x1ed70, longs((RTAB + 0x40, RTAB + 0x60))),                       # 1ed6a: LONG 1ed70 / 1ed74
            (0x22642, bytes((0, 1, 0, 1, 1, 0, 0, 0, 0xff, 0, 0x80, 0, 0, 1, 0, 0)))]   # 1ce08: TST.B 22642[BYTE 4(A4)]


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
SUCC = {0x1d1d6: (0x1d1da, 0x1d1f2), 0x1d58e: (0x1d5aa, 0x1d592), 0x1d59c: (0x1d5a0, 0x1d5aa), 0x1ed80: (0x1ed8e, 0x1ed84),
        0x1f296: (0x1f2a0, 0x1f29a), 0x1f802: (0x1f80c, 0x1f806), 0x1fa44: (0x1fa48, 0x1fa90), 0x1fac0: (0x1face, 0x1fac4)}
assert set(SUCC) == CONS_SET
# candidate producer chains (entry -> consumer); kept when the native producer reads only RAM and both C values occur
CHAIN_CANDIDATES = ((0x1d588, 0x1d58e), (0x1d592, 0x1d59c))
CLEAR_ONLY_CHAINS = ((0x1ed78, 0x1ed80), (0x1fa3c, 0x1fa44))


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor (1d58e / 1d59c: the shared successor 1d5aa is told apart by the trace)."""
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
        return None                                 # C2 writes no PVC port (a run that does is dropped here)
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


def borrow(regs):
    """The C of 1e016 (SUB.W D1,D0) from the output registers: the borrow is D0.W(after) + D1.W >= 10000."""
    return 2 if (regs['d0'] & 0xffff) + (regs['d1'] & 0xffff) >= 0x10000 else 1


def carry_after(p, c, regs=None):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set); regs = the output registers when p is the last block (1e016)."""
    if p in CONS_SET or p in PASS_SET:
        return c
    if p in CLEAR_SET:
        return 1
    if p in DATA_SET:
        assert regs is not None
        return borrow(regs)
    return 0


def model(executed, carry, regs):
    c = carry
    for i, p in enumerate(executed):
        c = carry_after(p, c, regs if i == len(executed) - 1 else None)
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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, RTAB)),
                a1=rng.choice(JUMPS), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x1c, 0xc8, 0x400, 0xffff, 0x12345678, 0x10000, 0x22, 0x82))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 4, 0x8, 0x40, 0x400, 0x1e, 0xffff, 0x12345678))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and disp in POINTERS:
            continue                                    # (A6) callback LONG, the node links and the pointer fields are declared below
        if reg == 5 and disp in (0x5434, 0x5474):
            continue
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    # the node links, the record LONG 8c(A6), the LONG table 22(A6), the map LONG 3e(A6), the JMP target 5434(A5) and the box 5474(A5)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x8, 4, SIBLING)
    r.put(NODE + 0x8c, 4, REC)
    r.put(NODE + 0x22, 4, LTAB)
    r.put(NODE + 0x3e, 4, rng.choice(MAPS + (CHILD,)))
    r.put(A5 + 0x5434, 4, rng.choice((0, 0, 0x1c1e2, 0x1ee00, 0x1ce0e)))
    r.put(A5 + 0x5474, 4, rng.choice((0, BOX)))
    for i in range(8):
        r.put(LTAB + 4 * i, 4, rng.choice((0, 0x1d000 + 0x10 * i)))       # the script LONGs of 1cad4 (0 -> the default 1cafe)
    for i in range(4):
        r.put(BOX + 2 * i, 2, rand_val(rng, 2))                             # the box WORDs of 1cd2a / 1cd50
    if rng.random() < 0.6:
        for i in range(0, 0x140, 2):
            if rng.random() < 0.3:
                r.put(RTAB + i, 2, rng.choice((0, 2, 4, 6, 0x7a, 0x8000, 0xffff)))   # the WORD tables of 1d0ca / 1cb08 / 1cac2 (RAM)
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
    if regs['a1'] not in JUMPS + (0x1ce0e,):
        regs['a1'] = JUMPS[0]                           # a hint A1 that is a RAM address would not run natively
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit starts, the JMP (A1) targets and the RTS sentinel
ALLOWED_STOPS = {0x28ae, 0x2986, 0x8cda, 0x8ebe, 0x8ff4, 0xce02, 0x1aa3a, 0x1c1f4, 0x1d198, 0x43e08, 0x43e34, 0x4836e, 0x49a58, 0x49be0, 0x49c20, 0x49c38,
                 0x49f96, 0x49fc6, 0x4be82, 0x4bfc0, 0x4c0ea, 0xea5f0, STOP} | set(B.EXIT_STOPS) | set(JUMPS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p) or (tr and tr[-1] == 0x1aa38)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or (tr and tr[-1] == 0x1aa38)      # a path ends at a consumer and at the JMP (A1) target


def hints(s):
    """The V1 spec hint worlds (pc2.hint_worlds) of the block; converted to absolute addresses by world()."""
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
                continue                                 # a stop at the entry is a zero-step run
            if (nxt in CONS_SET and s not in CLEAR_SET | PASS_SET | DATA_SET) or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, o['regs']), 1, o)


PATH_ENTRIES = (0x1a9e8, 0x1a9f2, 0x1a9fe, 0x1cab6, 0x1cabe, 0x1cac2, 0x1cad4, 0x1cb08, 0x1cd12, 0x1cd2a, 0x1cd58, 0x1cd98, 0x1cdba, 0x1cdfe, 0x1ce08,
                0x1ce2a, 0x1ce34, 0x1ce50, 0x1ce62, 0x1ce6e, 0x1ce80, 0x1d0c2, 0x1d0f6, 0x1d15a, 0x1d160, 0x1d170, 0x1d1da, 0x1d2d4, 0x1d2e6, 0x1d31e,
                0x1d32e, 0x1d380, 0x1d45a, 0x1d592, 0x1dbde, 0x1ddd4, 0x1de00, 0x1de28, 0x1dfe6, 0x1dff6, 0x1e006, 0x1ed34, 0x1ed3e, 0x1ed4a, 0x1ed5a,
                0x1ed78, 0x1ed84, 0x1ed8e, 0x1ed96, 0x1edb4, 0x1edbe, 0x1edc6, 0x1ede6, 0x1eee0, 0x1f1d8, 0x1f1fc, 0x1f228, 0x1f23a, 0x1f244, 0x1f25a,
                0x1f278, 0x1f29a, 0x1f7a4, 0x1f7ac, 0x1f7e2, 0x1f806, 0x1fa3c, 0x1fa48, 0x1fa50, 0x1fa90, 0x1fa94, 0x1fac4, 0x1fad2, 0x1fae0, 0x1fae8)


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
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, o['regs']), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=CHILD,
             a1=0x1c1e2, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry):
    """A world for a real producer chain (RAM producers only)."""
    r, regs = world(rng, [], entry)
    regs.update(dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d7=rng.getrandbits(32)))
    if entry == 0x1d588:                                         # 4836e: BTST #2,5683(A5): set -> 48378 (C Clear), clear -> 4837e (C Set)
        r.put(A5 + 0x5683, 1, rng.choice((0, 4, 0xfb, 0xff)))
    if entry == 0x1d592:                                         # 49c38: TST.L 5734(A5) + 4 (WORD 78 & 1)
        w = rng.choice((0, 1, 0x8000, 0xffff))
        r.put(NODE + 0x78, 2, w)
        r.put(A5 + 0x5734 + 4 * (w & 1), 4, rng.choice((0, 0x10e400)))
    if entry in (0x1ed78, 0x1fa3c):                              # 1cb08 on the synthetic tables 1b230 / 1b716: BYTE 9f = 0 -> 1cb18 (C Clear)
        r.put(NODE + 0x9f, 1, rng.choice((0, 0, 2)))
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
            r, regs = chain_world(rng, entry)
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
            for k, r, regs, o, c in rows:
                assert c == 1
                row('chain1-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)
            continue
        if set(seen) != {1, 2}:
            continue                                             # one C value never occurred: declared-C rows only
        CHAINS.append((entry, cons))
        for k, r, regs, o, c in rows:
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=0x1c1e2, a2=PARENT, a3=0, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    inside = 'unsupported animation player c2 PC'
    rom = 'missing or ambiguous physical program bus ROM byte'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'player c2 caller requires known carry', cp, stop=SUCC[cp][0])
    # the live JMP (A1) 1aa38 (contract decision 2): a RAM target / a C3 start / the interior PC 1ce0e / an odd target
    err('jmp-ram', 0x1aa2c, unrouted, 0x10fe40, a1=0x10fe40)
    err('jmp-1ed70', 0x1aa2c, unrouted, 0x1ed70, a1=0x1ed70)          # player C3 refresh: was jmp-1ee00 (1ee00 is a C3 start now); 1ed70 is ROM data
    err('jmp-interior', 0x1aa2c, inside, 0x1ce0e, a1=0x1ce0e)
    err('jmp-odd', 0x1aa2c, 'unaligned animation machine PC', 0x1c1e3, a1=0x1c1e3)
    err('jmp-chain', 0x1a9e8, unrouted, 0x10fe40, puts=((NODE + 0x6e, 1, 6), (A5 + 0x5434, 4, 0x10fe40), (NODE + 0x3e, 4, 0x10d2d6)))
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-1aa2c', 0x1aa2c, odd, 0x1aa2c, a6=NODE + 1)
    err('odd-node-1cd98', 0x1cd98, odd, 0x1cd98, stop=0x1cdb0, a6=NODE + 1)
    err('odd-node-1d22a', 0x1d22a, wodd, 0x1d22a, stop=0x1aa3a, a6=NODE + 1)
    err('odd-stack-1d0c2', 0x1d0c2, odd, 0x1d0c2, stop=0x8ff4, a7=SP + 1)
    err('odd-stack-1d326', 0x1d326, odd, 0x1d326, stop=0xea5f0, a7=SP + 1)
    err('odd-a4-1cd12', 0x1cd12, odd, 0x1cd12, stop=0x1cd1c, a4=NODE + 1)
    err('odd-a0-1cdba', 0x1cdba, odd, 0x1cdba, stop=0x1cdc8, a0=NODE + 1)
    err('odd-a0-1ed6a', 0x1ed6a, odd, 0x1ed6a, stop=0x1cb08, a0=NODE + 1)
    err('odd-a0-1cd50', 0x1cd50, odd, 0x1cd50, stop=0x1cd58, a0=NODE + 1)
    # the ROM tables outside the declared synthetic bytes: index 0xa of 1c1d8 (1c1e2, a code BYTE of the unit), BYTE 4(A4) = 10 of 22642
    err('table-1c1e2-a', 0x1c1e2, rom, 0x1c1e2, puts=((NODE + 0xa0, 1, 0xa),))
    err('table-1ce08-10', 0x1ce08, rom, 0x1ce08, puts=((REC + 4, 1, 0x10),))
    err('table-1d170-9f', 0x1d170, rom, 0x1d170, a0=0x1d136, puts=((NODE + 0x9f, 1, 9),))
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('1dfe6-then-1dff0', 0x1dfe6, odd, 0x1dff0, a7=SP + 1)
    err('1ed34-then-1ed3c', 0x1ed34, odd, 0x1ed3c, a7=SP + 1)
    err('1ed96-then-1edb0', 0x1ed96, odd, 0x1edb0, stop=0x1cd98, a7=SP + 1)
    err('1d2e6-then-1d306', 0x1d2e6, odd, 0x1d306, stop=0x1c1f4, a7=SP + 1)
    err('1ed4a-then-1ed54', 0x1ed4a, odd, 0x1ed54, a7=SP + 1)
    err('1e006-then-1e016', 0x1e006, odd, 0x1e016, a7=SP + 1)


def main():
    rng = random.Random(0xC2C2)
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
