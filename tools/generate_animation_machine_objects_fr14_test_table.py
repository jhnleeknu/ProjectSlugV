"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr14_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code, every one differs from the original): the anim LONG tables 363ae / 36522 and the sound WORD
table 363be (by WORD 76), the records 363a6 (1ab80), b6270 (1aa7e) and b6278 (4941e) that the producer chains read, the LONG table b6280 (by BYTE 8a)
and the bank-window LONGs 200034 / 2001a8 / 2001c4 / 20008c (bank 200000: physical offset = CPU address) with the LONGs behind them (2a1000 + 94,
2a2000 + 44, 2a3000 + 10).  A native run that reads any other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a PC that
is not a block start, a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, WORD 76 0..3 mostly), the records
10e900 / 10e940 / 10e980 / 10e9c0 / 10ea00 (A0 / A1 / A2), A5 = 108000, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7
and the hint worlds of the V1 spec (tools/unit_fixture_specs/fr14.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000,
'rec' / 'regrec' address the record 10ea00 (rec + 20 = A0), 'rega5' / 'a5off' an A5 field, 'writes' a work RAM offset).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, the
            RTS sentinel).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, exits, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer: kept when both outcomes occur and the producer reads RAM / declared bytes.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 12 consumers keep the incoming C, b6128 Clear, b6146 Set, every other block Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr14_test_table.py  (rewrites the generated section in place)
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
import fr14 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr14_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
PASS_SET = set(B.PASS_SET)
CLEAR_SET = set(B.CLEAR_SET)
SET_SET = set(B.SET_SET)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT = 0x10ea00, 0x10eb00
MRECS = (0x10e900, 0x10e940, 0x10e980, 0x10e9c0)
WINDOWS = {0x2001a8: (0x2a1000, (0x94,)), 0x2001c4: (0x2a2000, (0x44,)), 0x20008c: (0x2a3000, (0x10,))}
JUMP_TARGETS = dict(B.JUMP_TARGETS)
READERS = ()
assert tuple(B.Z_READERS) == READERS




def longs(vals):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (363a6..363c6 is the data between the code 363a4 and 363c6, 36522..36532
    between 36520 and 36532, b6270..b62c0 the records and the first 16 LONGs of the table behind b6146; the bank windows and the LONGs behind them
    are banked data)."""
    srng = random.Random(0xF14F)
    # 363a6: the 1ab80 record (two LONGs: the x / y offsets (high WORDs) and sizes (low WORDs) of the screen test); 363ae: the anim LONG table (4
    # entries by 4 x WORD 76); 363be: the sound WORD table (4 entries by 2 x WORD 76)
    out = [(0x363a6, longs((0xffe8ff80, 0x00300040))), (0x363ae, longs((0x2b1000, 0x2b1040, 0x2b1080, 0x2b10c0))),
           (0x363be, struct.pack('>HHHH', 0x0111, 0x0222, 0x0333, 0x0444))]
    # 36522: the anim LONG table of the 36532 branch
    out.append((0x36522, longs((0x2b2000, 0x2b2040, 0x2b2080, 0x2b20c0))))
    # b6270: the 1aa7e record; b6278: the 4941e record (WORD (A1) / 2 / 4 / 6: the box against the player record); b6280: the LONG table by BYTE 8a
    out.append((0xb6270, longs((0xffd0ffd8, 0x00500048))))
    out.append((0xb6278, struct.pack('>HHHH', 0xffe8, 0xfff4, 0x0030, 0x0018)))
    out.append((0xb6280, longs(tuple((srng.getrandbits(18) << 1) ^ (0x80000000 if k % 3 == 0 else 0) for k in range(16)))))
    # the bank-window LONG 200034 (3643e only stores it)
    out.append((0x200034, longs((0x2a4000,))))
    for win in sorted(WINDOWS):
        dest, disps = WINDOWS[win]
        out.append((win, longs((dest,))))
        for d in disps:
            out.append((dest + d, longs((srng.getrandbits(19) << 1,))))
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


# consumer -> (C clear successor, C set successor)
SUCC = {0x36516: (0x36520, 0x3651a), 0x365f0: (0x365fa, 0x365f4), 0xb5d30: (0xb5d3a, 0xb5d34), 0xb5d3e: (0xb5d48, 0xb5d42), 0xb6042: (0xb604c, 0xb6046),
        0xb60ec: (0xb6104, 0xb60f0), 0xb60fa: (0xb60fe, 0xb6104), 0xb610e: (0xb6128, 0xb6112), 0xb611c: (0xb6120, 0xb6128), 0xb7b02: (0xb7b2e, 0xb7b0a),
        0xc0dfc: (0xc0e28, 0xc0e00), 0xd17ec: (0xd17f6, 0xd17f0)}
assert set(SUCC) == CONS_SET
RSUCC = {}
CHAIN_CANDIDATES = tuple(B.CHAINS)


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set; for the Z reader: 1 Z clear / 2 Z set): from its successor in the trace."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    succ = RSUCC[cons] if cons in RSUCC else SUCC[cons]
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
        if trace and trace[-1] in JUMP_TARGETS and p not in JUMP_TARGETS[trace[-1]]:
            out['bad'] = True                       # the computed jump leaves its table: the C++ checked jump-target error (error rows)
            uc.emu_stop()
            return
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
        # Unicorn evaluates the M68000 condition codes lazily: MOVE SR,D0 on a scratch page forces the evaluation (the C of a returned producer).
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
BOUNDED = (0x76, 0x77, 0x90, 0x91)


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
                a1=rng.choice(MRECS + (PARENT, CHILD)), a2=rng.choice(MRECS + (PARENT, CHILD)), a3=rng.choice(MRECS), a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 6, 7, 8, 0xf, 0x10, 0x1a, 0x1b, 0x80, 0xff, 0x100, 0x106, 0x7fff, 0x8000, 0xfff0, 0xffff, 0x10000,
                                 0x12340001, 0xffffffff, 0xfffe8000, 0x18000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffff0000, 0x12345600))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0x1800, 0x17ff, 0x9800, 0x97ff, 0, 0xffff, 0x8000, 0x12341800))
    if s in (0xb7b1e, 0xb7b28, 0xb7b2c) and rng.random() < 0.6:
        regs['a1'] = A5 + 0x5ddc
        regs['a2'] = A5 + 0x5dde
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
    # the node link, the player index WORD 76 (the tables 363ae / 36522 / 363be), the FR2 b4aca index WORD 90, the 49fc6 LONG 26, the records
    r.put(NODE + 0xc, 4, PARENT)
    if rng.random() < 0.85:
        r.put(NODE + 0x76, 2, rng.choice((0, 1, 0, 1, 2, 3)))
    r.put(NODE + 0x90, 2, rng.choice((0, 4, 8, 0xc, 0x10, 0x14)))
    if rng.random() < 0.7:
        r.put(NODE + 0x26, 4, 0)
    for m in MRECS + (REC,):
        for off in (0, 2, 4, 6, 0x42, 0x46):
            r.put(m + off, 2, rand_val(rng, 2))
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


# the stops a success row may end at outside the unit: the routed exits (FR12 7177c / 71788, FR13 71876 / d1636 included) and the RTS sentinel
ROUTED_EXITS = {0x2a00, 0x8ebe, 0x8ff4, 0x1aa3a, 0x1aa7e, 0x1ab80, 0x43e34, 0x490ba, 0x49392, 0x4941e, 0x49f8c, 0x49fc6, 0x4ae4a, 0x4b54e, 0x4be2c,
                0x4be34, 0x4bfa4, 0x4c0ac, 0xb4334, 0xb4958, 0xb4ab0, 0xc1d2e, 0xc6a96, 0x7177c, 0x71788, 0x71876, 0xd1636}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == set()
JUMP_STOPS = set(t for ts in JUMP_TARGETS.values() for t in ts) - STARTS_SET
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS | JUMP_STOPS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET or p in READERS


def hints(s):
    """The V1 spec hint worlds (fr14.hint_worlds) of the block, converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def reader_hints(s):
    """The Z reader 71fe4 with D0.B 0 / not 0 (the native SR Z set from it)."""
    return [dict(regs=dict(d0=v)) for v in (0, 1, 0x100, 0xff, 0x12345600, 0x80)] + [dict(regs=dict(d0=0), mirror=True)]


def reader_flags(s, r, regs):
    return 4 if regs['d0'] & 0xff == 0 else 0


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
            if ((nxt in CONS_SET or nxt in READERS) and s not in CLEAR_SET and s not in SET_SET and s not in B.DATA_SET) or \
               (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
    if entry in (0xc0df6, 0xd17e6):                              # 49fc6: LONG 26(A6) = 0 -> Set (it writes the bank device: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry in (0x3650c, 0x365e6, 0xb6038):                     # 1ab80 / 1aa7e: the synthetic records against WORD 42 / 46 and BYTE 15 bits 0 / 1
        r.put(NODE + 0x42, 2, rng.choice((0, 0x40, 0xa0, 0x120, 0x200, 0xffc0)))
        r.put(NODE + 0x46, 2, rng.choice((0, 0xc0, 0x100, 0x180, 0x1f0, 0x300)))
        r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0xb5d2a:                                         # 4b54e: LONG 56 = 0 -> BYTE 5e 0 (Clear) / not 0 (Set)
        r.put(NODE + 0x56, 4, 0)
        r.put(NODE + 0x5e, 1, rng.choice((0, 1, 0x80)))
    if entry in (0xb5d3a, 0xb60e4, 0xb6104, 0xb7af8):            # b60da / 49392: BYTE 61 bit 0, BYTE 568e(A5) bit D0
        r.put(NODE + 0x61, 1, rng.choice((0, 0, 1)))
        r.put(A5 + 0x568e, 1, rng.choice((0, 1, 2, 3)))
        r.put(NODE + 0x8b, 1, rng.choice((0, 1)))
        regs['d0'] = rng.choice((0, 1, 0x10000, 0x10001))
    if entry in (0xb60f0, 0xb6112, 0xb5d3a):                     # 4941e: the box b6278 of A0 (the player record) against the node
        regs['a0'] = rng.choice((0x100cb8, 0x100da8))
        for p in (0x100cb8, 0x100da8):
            r.put(p + 0x42, 2, 0x100)
            r.put(p + 0x46, 2, 0x100)
        r.put(NODE + 0x42, 2, rng.choice((0x100, 0x110, 0x140, 0x80, 0xe0)))
        r.put(NODE + 0x46, 2, rng.choice((0x100, 0x108, 0x130, 0xc0, 0xf0)))
        r.put(NODE + 0x15, 1, rng.choice((0, 3)))
    return r, regs


CHAINS = []


def gen_consumers(rng):
    for cp in CONSUMERS:
        clr, st = SUCC[cp]
        for carry in (1, 2):
            r = base_ram()
            regs = dict(PLAIN)
            o = native(r.b, regs, cp, carry, lambda p, tr: p in (clr, st) and len(tr) > 0)
            assert o is not None, hex(cp)
            assert o['stop'] == (clr if carry == 1 else st), (hex(cp), carry, hex(o['stop']))
            row('cons-%x-c%d' % (cp, carry), r, regs, cp, o['stop'], carry, carry_after(cp, carry), 3, o)
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C (the Z reader
    # recomputes its Z)
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(RSUCC[cons] if cons in RSUCC else SUCC[cons])
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            stopf = lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS
            o = native(r.b, regs, entry, 0, stopf)
            if o is None or cons not in o['trace'] or o['stop'] not in succ:
                continue
            if 0x290e in o['trace'] and 0x2986 in o['trace']:
                continue                                         # the 28ae failure inside 2986: the C++ caller-X checked error (C7 decision 6)
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
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c) if cons not in RSUCC else 0, 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    rom = 'missing or ambiguous physical program bus ROM byte'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr14 caller requires known carry', cp, stop=SUCC[cp][0])
    # fixed ROM outside the declared synthetic bytes: the table indices past the declared tables (WORD 76 = 4: 363ae + 10 = 363be is declared as WORDs
    # only, so 4 LONG-reads 363be..363c2: declared; WORD 76 = 5 reads 363c2..363c6 (declared) and 6 reads 363c6.. (code, undeclared))
    err('rom-3645a-index', 0x3645a, rom, 0x3645a, puts=((NODE + 0x76, 2, 6),))
    err('rom-36532-index', 0x36532, rom, 0x36532, puts=((NODE + 0x76, 2, 0x3fff),))
    err('rom-36474-index', 0x36474, rom, 0x36474, stop=0x8ebe, puts=((NODE + 0x76, 2, 4),))
    # odd node / stack / A1: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-3643e', 0x3643e, wodd, 0x3643e, stop=0x1aa3a, a6=NODE + 1)
    err('odd-node-364aa', 0x364aa, odd, 0x364aa, a6=NODE + 1)
    err('odd-node-364a0', 0x364a0, odd, 0x364a0, stop=0x364aa, a6=NODE + 1)
    err('odd-node-3657c', 0x3657c, wodd, 0x3657c, stop=0x36588, a6=NODE + 1)
    err('odd-node-365b2', 0x365b2, odd, 0x365b2, a6=NODE + 1)
    err('odd-node-b5c60', 0xb5c60, odd, 0xb5c60, a6=NODE + 1)
    err('odd-node-b5c84', 0xb5c84, wodd, 0xb5c84, a6=NODE + 1)
    err('odd-node-b5d02', 0xb5d02, wodd, 0xb5d02, stop=0xb6084, a6=NODE + 1)
    err('odd-node-b60a4', 0xb60a4, odd, 0xb60a4, a6=NODE + 1)
    err('odd-node-c0d68', 0xc0d68, wodd, 0xc0d68, a6=NODE + 1)
    err('odd-node-cd110', 0xcd110, odd, 0xcd110, a6=NODE + 1)
    err('odd-node-cd360', 0xcd360, wodd, 0xcd360, a6=NODE + 1)
    err('odd-node-d1798', 0xd1798, wodd, 0xd1798, a6=NODE + 1)
    err('odd-a1-b7b1e', 0xb7b1e, odd, 0xb7b1e, a1=A5 + 0x5ddd)
    err('odd-stack-364d4', 0x364d4, odd, 0x364d4, stop=0x4be34, a7=SP + 1)
    err('odd-stack-364e4', 0x364e4, odd, 0x364e4, a7=SP + 1)
    err('odd-stack-b7af8', 0xb7af8, odd, 0xb7af8, stop=0x49392, a7=SP + 1)
    err('odd-stack-b7b02', 0xb7b02, odd, 0xb7b02, carry=1, a7=SP + 1)
    err('odd-stack-b6128', 0xb6128, odd, 0xb6128, a7=SP + 1)
    err('odd-stack-b6146', 0xb6146, odd, 0xb6146, a7=SP + 1)
    err('odd-stack-cd360', 0xcd360, odd, 0xcd360, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-3657c', 0x3657c, device, 0x3657c, stop=0x36588, a6=0x1000)
    err('rom-write-b60b4', 0xb60b4, device, 0xb60b4, a6=0x1000)
    err('rom-write-b7b2c', 0xb7b2c, device, 0xb7b2c, a2=0x363a6)               # ADDQ.B reads the declared BYTE first, the write fails
    # failures after executed blocks (rollback; the failing PC differs from the entry)
    err('cc7b8-then-cd110', 0xcc7b8, odd, 0xcd110, a6=NODE + 1)
    err('b7ae4-then-b7af8', 0xb7ae4, odd, 0xb7af8, stop=0x49392, a7=SP + 1)
    err('36576-then-36578', 0x36576, device, 0x36578, a6=0x363a6 - 0x36)       # ADD.W D0,36(A6) reads the declared WORD 363a6 first
    err('b6120-then-b612e', 0xb6120, odd, 0xb6136, stop=0xb7af0, a7=SP + 1)


def main():
    rng = random.Random(0xF14F14)
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
