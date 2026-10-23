"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr13_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code, every one differs from the original): the record d13a4..d13ac (the two LONGs that 1ab80
reads for d1698) and the bank-window LONGs 2000d0 / 2000d4 / 2001c0 / 200080 / 200090 (bank 200000: physical offset = CPU address) with the LONGs
behind them (2a1000 + 64 / 68 / 88 / 104 / 180 / 188, 2a2000 + 4 / 10 / a4 / 1cc / 1d4, 2a3000 + c, 2a4000 + 148, 2a5000 + 4 / 8 / c).  A native run
that reads any other fixed-ROM or banked byte is dropped, as is a run that lands inside the unit on a PC that is not a block start, a run whose
computed jump cc8da leaves the 27-entry table cc8de, a run that writes a device port, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 76 a handler of the FR11 decision
2, BYTE 97 0 / 4 / c), the records 10e900 / 10e940 / 10e980 / 10e9c0 / 10ea00 (A0 of b6d90 / cca5a), A5 = 108000, seeded BYTE / WORD / LONG field
edits (sign boundaries included), seeded D0-D7 and the hint worlds of the V1 spec (tools/unit_fixture_specs/fr13.py hint_worlds, converted to absolute
addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' address the record 10ea00 (rec + 20 = A0), 'writes' a work RAM offset).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit start, an unrouted entry of the table cc8de, the RTS sentinel).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, exits, the RTS sentinel), a consumer or the Z reader 71fe4.
  single 2  a consumer (or the Z reader) entered through its real producer: kept when both outcomes occur and the producer reads RAM / declared bytes.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
  single 5  the Z reader 71fe4 entered directly with the native SR Z = (D0.B = 0) (the Z of the TST.B D0 of 71fe2); the C++ recomputes it (contract
            decision 4).
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 10 consumers and the RTS b450c keep the incoming C, every other block Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr13_test_table.py  (rewrites the generated section in place)
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
import fr13 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr13_test.cpp'
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
WINDOWS = {0x2000d0: (0x2a1000, (0x64, 0x68, 0x88, 0x104, 0x180, 0x188)), 0x2000d4: (0x2a2000, (0x4, 0x10, 0xa4, 0x1cc, 0x1d4)),
           0x2001c0: (0x2a3000, (0xc,)), 0x200080: (0x2a4000, (0x148,)), 0x200090: (0x2a5000, (0x4, 0x8, 0xc))}
HANDLERS = tuple(B.HANDLERS)
JUMP_TARGETS = dict(B.JUMP_TARGETS)
ZREAD = 0x71fe4                                     # the Z reader (the TST.B D0 of 71fe2)
READERS = (ZREAD,)
assert tuple(B.Z_READERS) == READERS




def longs(vals):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (d13a4..d13ac is the record before the FR1c code d13b4; the bank windows
    and the LONGs behind them are banked data)."""
    srng = random.Random(0xF13F)
    # d13a4: two LONGs (1ab80: MOVE.L (A0)+,D0; MOVE.L (A0)+,D1 -> the x / y offsets (high WORDs) and sizes (low WORDs) of the screen test)
    out = [(0xd13a4, longs((0xffe8ff80, 0x00300040)))]
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
SUCC = {0x716bc: (0x716c6, 0x716c0), 0x71a6e: (0x71a78, 0x71a72), 0x71f30: (0x71f42, 0x71f34), 0x72102: (0x7210c, 0x72106), 0x722cc: (0x722d6, 0x722d0),
        0xbfd94: (0xbfd9e, 0xbfd98), 0xc5586: (0xc5590, 0xc558a), 0xd16a2: (0xd16ac, 0xd16a6), 0xd172a: (0xd173c, 0xd172e), 0xd177a: (0xd1670, 0xd177e)}
assert set(SUCC) == CONS_SET
# the Z reader -> (Z clear successor, Z set successor): 71fe4 BEQ.W 72000
RSUCC = {ZREAD: (0x71fe8, 0x72000)}
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
BOUNDED = (0x76, 0x77, 0x78, 0x79, 0x90, 0x91, 0x97)


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
                a1=rng.choice((PARENT, CHILD)), a2=rng.choice((PARENT, CHILD)), a3=rng.choice(MRECS), a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 6, 7, 8, 0xf, 0x10, 0x1a, 0x1b, 0x80, 0xff, 0x100, 0x106, 0x7fff, 0x8000, 0xfff0, 0xffff, 0x10000,
                                 0x12340001, 0xffffffff, 0xfffe8000, 0x18000))
    if rng.random() < 0.4:
        regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffff0000, 0x12345600))
    if rng.random() < 0.4:
        regs['d7'] = rng.choice((0x1800, 0x17ff, 0x9800, 0x97ff, 0, 0xffff, 0x8000, 0x12341800))
    if s == 0xcc8d2 and rng.random() < 0.85:
        regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x1b)     # the table index 0..1a (a larger one is the checked jump-target error)
    if s in (0xb6d90, 0xcca5a) and rng.random() < 0.7:
        regs['a0'] = REC
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
    # the node link, the handler LONG (bfd34 -> b4030), the bounded index BYTE 97; the records (WORD 0 / 42)
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x76, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924)))
    r.put(NODE + 0x97, 1, rng.choice((0, 4, 0xc, 0xc)))
    r.put(NODE + 0x90, 2, rng.choice((0, 4, 8, 0xc, 0x10, 0x14)))
    for m in MRECS + (REC,):
        for off in (0, 2, 4, 6, 0x42):
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


# the stops a success row may end at outside the unit: the routed exits (FR10 70f84 / 70fd2 / 70ffa / 7102e, FR11 b4030 / b6dac, FR12 717c8 / 722da,
# FR4 cdc1c / cca76 included), the later-unit starts (FR14 71874 / d1632 / d177e), the unrouted entries of the table cc8de and the RTS sentinel
ROUTED_EXITS = {0x2986, 0x2a00, 0x8ebe, 0x1ab80, 0x1c356, 0x43e34, 0x491b6, 0x49214, 0x4970a, 0x49a58, 0x49f8c, 0x49fc6, 0x4ae4a, 0x4be06, 0x4be2c,
                0x4be34, 0x4bfa4, 0x702cc, 0x70302, 0x703f6, 0x705ca, 0x72d66, 0x72dd2, 0xb4334, 0xc6a96, 0xcca76, 0xcdc1c, 0x70f84, 0x70fd2, 0x70ffa,
                0x7102e, 0x717c8, 0x722da, 0xb4030, 0xb6dac}
UNIT_EXITS = set(B.UNIT_EXITS)
assert UNIT_EXITS == {0x71874, 0xd1632, 0xd177e}
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
    """The V1 spec hint worlds (fr13.hint_worlds) of the block, converted to absolute addresses by world()."""
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
    if entry in (0x716b6, 0x71a68, 0x720fc, 0x722c6, 0xbfd8e, 0xc5580, 0xd1724, 0xd1774):   # 49fc6: LONG 26(A6) = 0 -> Set (it writes the bank device: dropped)
        r.put(NODE + 0x26, 4, rng.choice((0, 0, CHILD)))
    if entry == 0x71f2c:                                         # 705ca: BYTE 82 bit 1 / BYTE 6f = 40 / 4bc04 (the map WORD 5b88(A5) + 72) -> Clear / Set
        r.put(NODE + 0x82, 1, rng.choice((0, 2, 2)))
        r.put(NODE + 0x6f, 1, rng.choice((0x40, 0x40, 0x41)))
        r.put(NODE + 0x42, 2, rng.choice((0x100, 0x100, 0x80, 0x200)))
        r.put(NODE + 0x46, 2, rng.choice((0x100, 0x100, 0x80, 0x200)))
        r.put(A5 + 0x5b88 + 0x72, 2, rng.choice((0x80, 0x10, 0x200, 0x3f, 0x40)))
    if entry == 0xd1698:                                         # 1ab80: the synthetic record d13a4 against WORD 42 / 46 and BYTE 15 bits 0 / 1 -> Clear / Set
        r.put(NODE + 0x42, 2, rng.choice((0, 0x40, 0xa0, 0x120, 0x200, 0xffc0)))
        r.put(NODE + 0x46, 2, rng.choice((0, 0xc0, 0x100, 0x180, 0x1f0, 0x300)))
        r.put(NODE + 0x15, 1, rng.choice((0, 1, 2, 3)))
    if entry == 0x71fe2:                                         # TST.B D0 -> the Z of 71fe4
        regs['d0'] = rng.choice((0, 1, 2, 0x100, 0xff, 0x12345600))
    if entry == 0x71fde:                                         # 70302 (FR2b) -> D0.B (WORD 78 = 0, BYTE 82 bit 3, BYTE 86 >= 0, 494c0, BYTE 87, 49a84)
        r.put(NODE + 0x78, 2, rng.choice((0, 0, 1)))
        r.put(NODE + 0x82, 1, rng.choice((0x08, 0x48, 0)))
        r.put(NODE + 0x86, 1, 0)
        r.put(NODE + 0x87, 1, rng.choice((0xff, 0x0f, 0x81)))
        r.put(NODE + 0x15, 1, rng.choice((0x80, 0)))
        r.put(NODE + 0x42, 2, rng.choice((0xa0, 0x100, 0x60, 0x140)))
        r.put(NODE + 0x46, 2, rng.choice((0x100, 0x180, 0xc0, 0x1c0)))
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
    unrouted = 'unsupported animation machine PC'
    rom = 'missing or ambiguous physical program bus ROM byte'
    device = 'unsupported animation machine write device'
    jump = 'unsupported animation objects fr13 jump target'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr13 caller requires known carry', cp, stop=SUCC[cp][0])
    # the computed jump cc8da past the cc8c0 guard: an index above 1a (decision 2)
    err('jump-cc8d2-1b', 0xcc8d2, jump, 0xcc8d2, d0=0x1b)
    err('jump-cc8d2-ff', 0xcc8d2, jump, 0xcc8d2, d0=0x123456ff)
    err('jump-cc8d2-80', 0xcc8d2, jump, 0xcc8d2, d0=0x80)
    # fixed ROM outside the declared synthetic bytes: a bank-window displacement nobody declares (none: the windows are declared), WORD 42 / WORD 0 of
    # a ROM record at b6d90 / cca5a
    err('rom-b6d90-a0', 0xb6d90, rom, 0xb6d90, a0=0x1000)
    err('rom-cca5a-a0', 0xcca5a, rom, 0xcca5a, a0=0x1000)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-71622', 0x71622, odd, 0x71622, a6=NODE + 1)
    err('odd-node-71682', 0x71682, odd, 0x71682, stop=0x71696, a6=NODE + 1)
    err('odd-node-70fcc', 0x70fcc, wodd, 0x70fcc, stop=0x70fd2, a6=NODE + 1)
    err('odd-node-70ff8', 0x70ff8, wodd, 0x70ff8, stop=0x70ffa, a6=NODE + 1)
    err('odd-node-7209c', 0x7209c, odd, 0x7209c, a6=NODE + 1)
    err('odd-node-720c6', 0x720c6, wodd, 0x720c6, stop=0x720d6, a6=NODE + 1)
    err('odd-node-72000', 0x72000, odd, 0x72000, a6=NODE + 1)
    err('odd-node-c5520', 0xc5520, wodd, 0xc5520, a6=NODE + 1)
    err('odd-node-cc8c0', 0xcc8c0, wodd, 0xcc8c0, a6=NODE + 1)
    err('odd-node-ccbc0', 0xccbc0, odd, 0xccbc0, a6=NODE + 1)
    err('odd-node-d1654', 0xd1654, odd, 0xd1654, a6=NODE + 1)
    err('odd-node-d16d6', 0xd16d6, wodd, 0xd16d6, stop=0xd16fa, a6=NODE + 1)
    err('odd-node-bfd48', 0xbfd48, wodd, 0xbfd48, a6=NODE + 1)
    err('odd-a0-cca5a', 0xcca5a, odd, 0xcca5a, a0=REC + 1)
    err('odd-a0-b6d90', 0xb6d90, odd, 0xb6d90, a0=REC + 1)
    err('odd-a5-d1670', 0xd1670, odd, 0xd1670, a5=A5 + 1)
    err('odd-stack-b450c', 0xb450c, odd, 0xb450c, carry=2, a7=SP + 1)
    err('odd-stack-cc8bc', 0xcc8bc, odd, 0xcc8bc, stop=0xcca76, a7=SP + 1)
    err('odd-stack-bfcfa', 0xbfcfa, odd, 0xbfcfa, stop=0x2986, a7=SP + 1)
    err('odd-stack-cca6c', 0xcca6c, odd, 0xcca6c, a7=SP + 1)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-70fcc', 0x70fcc, device, 0x70fcc, stop=0x70fd2, a6=0x1000)
    err('rom-write-c553a', 0xc553a, device, 0xc553a, a6=0x1000)
    # failures after executed blocks (rollback; the failing PC differs from the entry): the later-unit stops of FR14, the unrouted entries of the table
    # cc8de, the item handler path into the declared stop after a consumer
    err('71860-then-71874', 0x71860, unrouted, 0x71874)
    err('d161a-then-d1632', 0xd161a, unrouted, 0xd1632)
    err('d177a-then-d177e', 0xd177a, unrouted, 0xd177e, carry=2)
    err('cc8d2-then-cc8de', 0xcc8d2, unrouted, 0xcc8de, d0=0x12345600)
    err('cc8c0-then-cc8e2', 0xcc8c0, unrouted, 0xcc8e2, puts=((NODE + 0x5e, 1, 1),))
    err('cc8c0-then-cc946', 0xcc8c0, unrouted, 0xcc946, puts=((NODE + 0x5e, 1, 0x1a),))


def main():
    rng = random.Random(0xF13F13)
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
    tables.append('const std::uint32_t TABLE[]={%s};' % ','.join('0x%x' % t for t in JUMP_TARGETS[0xcc8da]))
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
    print('table entries a stop', sorted(hex(t) for t in JUMP_STOPS & stops))


if __name__ == '__main__':
    main()
