"""Generates the native-oracle tables of engine/tests/animation_machine_objects_fr15_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000; work RAM is not executable) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test
declares (not ROM data; data areas only, never over code of the unit, every one differs from the original): the WORD table 4fe8a (4fea4 / 4feb6), the
LONG tables ea3ac (e9bae: RAM WORD pairs) and ea3c4 (e9bae: RAM records), the WORD table ea37c (ea182), the signed-index probes e237c / e23ac / e23c4 (8000 below ea37c / ea3ac / ea3c4; hand rules only) and the bank-window LONG 2000b0 (40896 / 40a5a;
bank 200000: physical offset = CPU address).  A native run that reads any other fixed-ROM or banked byte is dropped, as is a run that lands inside the
unit on a PC that is not a block start (the bundled BEQ c1540 reached by a BEQ excepted), a JMP e9c72(PC,D0.W) to a table entry other than e9c7e (the
C++ checked jump-target error), a run that writes a device port other than the video port LONG 3c0000, or that reads a device.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00, LONG 76(A6) := the script record 10ea40
(or the BYTE indices 76.. for the e9b8a child), LONG 7e(A6) := the RAM record 10e700, WORD 88(A6) 0..2, BYTE 8f(A6) small, BYTE 90(A6) = 3 mostly),
A0 / A3 / A4 the record 10ea00 or the child 10e400, A1 / A2 the parent / child node, A5 = 108000 (the player nodes 100cb8 / 100da8 of 3ff5c / 3ff64),
seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 (small D2 for the circle plotter) and the hint worlds of the V1 spec
(tools/unit_fixture_specs/fr15.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'rec' / 'regrec' / 'a6rec' address
the record 10ea00 (rec + 20 = A0 / A1 / A4 / LONG 76 / LONG c), 'a5off' an A5 field, 'writes' a work RAM offset).
Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit, a
            later-unit stop; through the bundled BEQ c1540 to c0944).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, the RTS sentinel) or a consumer.
  single 2  a consumer entered through its real producer: kept when both outcomes occur; a run that passes 290e after 2986 is not a chain world.
  single 3  a consumer entered directly with a declared known C (1 clear / 2 set): stop = its successor (native branch on the SR C bit).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
Every success row records the ordered video port LONGs 3c0000 (count and FNV-1a digest) of the circle plotter 4fe74.
Known C is never read from the Unicorn SR after a run: consumer rows check the native branch outcome against the declared C.  The modelled C of the
unit: the 8 consumers and the pass RTS 40b7a keep the incoming C, 40b72 / 40acc (ORI) leave Set, ea2ca (CMP.W) leaves the C of its compare (computed
from the run's own operands: unsigned D0.W < WORD (A0 + D1.W)), every other block leaves Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_fr15_test_table.py  (rewrites the generated section in place)
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
import fr15 as B                                    # noqa: E402  (block lists, ranges, consumers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_fr15_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
CONSUMERS = list(B.CONSUMERS)
CONS_SET = set(CONSUMERS)
RANGES = list(B.RANGES)
THREAD = dict(B.THREAD)                             # the bundled BEQ c1540 -> c0944
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC, PARENT, LTAB = 0x10ea00, 0x10eb00, 0x10e700
PLAYERS = (0x100cb8, 0x100da8)
KEEP_C = CONS_SET | {0x40b7a}                       # the consumers and the pass RTS keep the incoming C
SET_C = {0x40b72, 0x40acc}                          # ORI.B #1,CCR
JUMP_ALLOWED = {0xe9c6e: {0xe9c7e}}                 # JMP e9c72(PC,D0.W): the transcribed entry 3 only
PORT_CAP = 400


def longs(vals):
    return b''.join(struct.pack('>I', v) for v in vals)


def words(vals):
    return b''.join(struct.pack('>H', v & 0xffff) for v in vals)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only."""
    return [(0x4fe8a, words([0x0100 + 0x11 * k for k in range(13)])),                          # 4feb6: the cell codes of the 13 circles
            (0xea37c, words([0x8000 if k == 7 else (0x35 * k + 3) ^ (0x4000 if k & 1 else 0) for k in range(20)])),   # ea182: WORD (ea37c + 2 x D6.W)
            (0xea3ac, longs((LTAB + 0x80, LTAB + 0x84, LTAB + 0x88))),                          # e9bae: LONG (ea3ac + 4 x WORD 88): RAM WORD pairs
            (0xea3c4, longs((LTAB, LTAB + 0x40))),                                               # e9bae: LONG (ea3c4 + 4 x D0.W of ea2c6 = 0): the record
            (0xe237c, words((0x5a5a,))),                                                         # ea182: ea37c + sext(2 x 4000) (the signed index; rule only)
            (0xe23ac, longs((LTAB + 0x90,))),                                                    # e9bae: ea3ac + sext(4 x 2000) (the signed index; rule only)
            (0xe23c4, longs((0x10e123 & ~1,))),                                                  # e9bae: ea3c4 + sext(4 x 2000) (the signed index; rule only)
            (0x2000b0, longs((0x00fedcba,)))]                                                    # 40896 / 40a5a (bank window)


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
SUCC = {0x3ff78: (0x3ff9c, 0x3ff7c), 0x4084c: (0x40856, 0x40850), 0x408c6: (0x4095e, 0x408ca), 0x40ac8: (0x40af6, 0x40acc),
        0x40b06: (0x40890, 0x40b0a), 0x40b6e: (0x40b7a, 0x40b72), 0xc13ee: (0xc1d06, 0xc13f2), 0xea150: (0xea154, 0xea2c0)}
assert set(SUCC) == CONS_SET
CHAIN_CANDIDATES = tuple(B.CHAINS)


def cons_value(cons, o):
    """The C a consumer read (1 clear / 2 set): from its successor in the trace."""
    tr = o['trace'] + [o['stop']]
    i = tr.index(cons)
    succ = SUCC[cons]
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

    def byte(self, a):
        return self.b[a & 0xffff]

    def word(self, a):
        return (self.b[a & 0xffff] << 8) | self.b[(a + 1) & 0xffff]


def base_ram():
    r = Ram()
    r.put(SP, 4, STOP)
    r.base = 1
    return r


def canonical_ports(ports):
    """Native port events -> C++ form: one (3c0000, 4, LONG) per MOVE.L D3,3c0000 (a WORD pair 3c0000 / 3c0002 is joined)."""
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


def bundled_ok(p, prev):
    """The bundled BEQ c1540 entered by a BEQ (c1532 / c153c) or by the straight-line fall-through of c153c."""
    if p not in THREAD:
        return False
    ins = B.decode(prev)
    return B.target(ins.op_str) == p or p == prev + ins.size


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
        if trace and trace[-1] in JUMP_ALLOWED and p not in JUMP_ALLOWED[trace[-1]]:
            out['bad'] = True                       # a computed jump outside the transcribed table entry: the C++ checked jump-target error
            uc.emu_stop()
            return
        if n[0] > 1 and stopfn(p, trace):
            out['stop'] = p
            uc.emu_stop()
            return
        if len(trace) > 60000 or len(m.ports) > PORT_CAP:
            out['bad'] = True                       # a long loop: not a table row
            uc.emu_stop()
            return
        if trace and (p & 1 or (inr(p) and p not in STARTS_SET and p != trace[-1] + B.decode(trace[-1]).size and not bundled_ok(p, trace[-1]))):
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
        c.emu_start(pc, 0xffffff, count=800000)
    except unicorn.UcError:
        return None
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.dev_reads or m.bank != 0x200000:
        return None
    if (m.ff8, m.ff9) != (0xa0, 0x1000):
        return None
    ports = canonical_ports([(a, sz, v) for kind, a, sz, v in m.ports])
    if any(a != 0x3c0000 or sz != 4 for a, sz, v in ports):
        return None                                 # FR15 writes only the video port LONG 3c0000
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


def cmp_c(o):
    """The C of ea2ca from the run's own operands (D0.W, D1.W, A0 after the block; ea2ca writes no memory): unsigned D0.W < WORD (A0 + sext D1.W)."""
    regs = o['regs']
    ram = o['ram']
    d1 = regs['d1'] & 0xffff
    a = (regs['a0'] + (d1 - 0x10000 if d1 & 0x8000 else d1)) & 0xffff
    w = (ram[a] << 8) | ram[(a + 1) & 0xffff]
    return 2 if (regs['d0'] & 0xffff) < w else 1


def carry_after(p, c, o=None):
    """C after the block p entered with c (0 unknown / 1 clear / 2 set)."""
    if p in KEEP_C:
        return c
    if p in SET_C:
        return 2
    if p == 0xea2ca:
        return cmp_c(o)
    return 0


def model(executed, carry, o):
    """C after a path (ea2ca can only be the last block of a path: its RTS lands on the consumer ea150 or the sentinel)."""
    c = carry
    for p in executed:
        c = carry_after(p, c, o)
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
BOUNDED = (0x88, 0x8f, 0x90, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81)


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
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((REC, CHILD, REC + 0x40)),
                a1=rng.choice((PARENT, CHILD, LTAB)), a2=rng.choice((PARENT, CHILD)), a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x13, 0x25, 0x26, 0x40, 0x80, 0x2000, 0x4000, 0xffff, 0x12345678, 0x10000, 0x8000, 0xfff0))
    if rng.random() < 0.6:
        regs['d1'] = rng.choice((0, 1, 2, 3, 4, 7, 0xe, 0x1d, 0x1e, 0xffff, 0xfffd, 0xfffc, 0x10001, 0x8000, 0x12340000))
    if 0x4fdfc <= s < 0x4ff96 or rng.random() < 0.3:
        regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 5, 8, 0xd, 0xe, 0x10, 0x14))
        for k in ('d4', 'd5', 'd6'):
            if rng.random() < 0.7:
                regs[k] = (regs[k] & 0xffff0000) | rng.choice((0, 1, 2, 3, 5, 8, 0xfffe, 0xffff))
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
    r.put(NODE + 0xc, 4, rng.choice((PARENT, PARENT, CHILD)))
    r.put(NODE + 0x88, 2, rng.choice((0, 1, 2)))
    r.put(NODE + 0x8f, 1, rng.choice((0, 1, 2, 3, 4)))
    r.put(NODE + 0x90, 1, rng.choice((3, 3, 3, 0, 4)))
    if 0xe9b8a <= s < 0xea34a:
        r.put(NODE + 0x7e, 4, LTAB)
        for k in range(8):
            r.put(NODE + 0x76 + k, 1, rng.choice((0, 1, 2, 3, 5, 8, 0xa)))
    else:
        r.put(NODE + 0x76, 4, rng.choice((REC + 0x40, REC + 0x40, 0)))
        r.put(NODE + 0x7a, 2, rng.choice((0, 0x100, 0x1ff, 0x200, 0x201, 0xd00, 0x8000, 0xffff)))
    for i in range(0, 0x20, 2):
        r.put(REC + 0x40 + i, 2, rng.choice((0, 2, 4, 0x10, 0x7fff, 0xffff, 0xfffe, 0xfffd, 0xfffc, 0x8000, 6)))
    for i in range(0, 0xc0, 2):
        if rng.random() < 0.6:
            r.put(LTAB + i, 2, rng.choice((0, 0, 1, 2, 0x10, 0x8000, 0xffff, 0x1234)))       # the e9b8a record (LONG 7e) and the ea3ac WORD pairs
    for p in PLAYERS:
        r.put(p + 0x2e, 2, rng.choice((0, 1, 0x7fff, 0x8000, 0xffff, 0x100)))
    for k in range(3):
        r.put(A5 + 0x5e4a + 2 * k, 2, rng.choice((0, 3, 4, 5, 6, 0xffff)))
    if hint:
        regs.update(dict((k, v) for k, v in hint.get('regs', {}).items() if v is not None))
        for k, v in hint.get('regrec', {}).items():
            regs[k] = REC - 0x20 + v                      # the V1 spec's record: rec + 20 is A0 / A1 / A4 (REC here)
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a6rec', []):
            r.put(NODE + off, n, REC - 0x20 + v)
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
        if 0x7e in [off for off, n, v in hint.get('a6off', []) if n == 4]:
            r.put(NODE + 0x7e, 4, LTAB)                 # the V1 hint's ROM record ea3cc is the synthetic RAM record here
    return r, regs


# the stops a success row may end at outside the unit: the routed exits, the later-unit stops and the RTS sentinel
ROUTED_EXITS = {0x288c, 0x28ae, 0x2a00, 0x8d34, 0x8ebe, 0xce02, 0x16ea4, 0x1aa3a, 0x43e34, 0x491c4, 0x49290, 0x496c2, 0x49a58, 0x49f8c, 0x49fc6,
                0x4b54e, 0x4bce0, 0x4bfb4, 0x4c2d0, 0x4d418, 0x4d508, 0x4d766, 0x4d81c, 0xb3ea2, 0xb402a, 0xb4030, 0xb4304, 0xb4334, 0xb4958, 0xb4ab0,
                0xc0944, 0xc1cf2, 0xc1d06, 0xc1d2e, 0xc6a96}
UNIT_EXITS = set(B.UNIT_EXITS)
ALLOWED_STOPS = ROUTED_EXITS | {STOP} | UNIT_EXITS
EXITS = sorted(ROUTED_EXITS) + sorted(UNIT_EXITS)


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p) or p in CONS_SET


def hints(s):
    """The V1 spec hint worlds (fr15.hint_worlds) of the block; converted to absolute addresses by world()."""
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
            if nxt in CONS_SET or (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
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
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, carry_after(s, 0, o), 1, o)


PATH_ENTRIES = tuple(s for s in STARTS if s not in CONS_SET)


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
            if any(p in CONS_SET for p in ex) or not allowed(o['stop']) or o['stop'] == s:
                continue
            if 0xea2ca in ex[:-1]:
                continue                                 # ea2ca leaves its compare C only as the last block (model)
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
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, model(ex, carry, o), 0, o)


PLAIN = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x33330002, d3=0x44440003, d4=0x55550004, d5=0x66660005, d6=0x77770006, d7=0x88880007, a0=REC,
             a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)


def chain_world(rng, entry, k):
    """A world for a real producer chain (RAM producers only)."""
    r, regs = world(rng, [], entry)
    h = B.chain_hint(entry, k, rng)
    if h:
        for off, n, v in h.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in h.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in h.get('writes', []):
            r.put(0x100000 + off, n, v)
        regs.update(h.get('regs', {}))
    if entry in (0x40ab8, 0x40af6):                              # 28ae: the free-node list LONG 104c9c (a RAM node with a RAM next LONG)
        r.put(0x104c9c, 4, rng.choice((0x10e800, 0x10e800, 0)))
        r.put(0x10e808, 4, 0)
        r.put(NODE + 0x8, 4, PARENT)
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
    # real producers: entry -> consumer; the native branch on the real flags decides, the C++ consumer reads the modelled known C
    for entry, cons in CHAIN_CANDIDATES:
        succ = set(SUCC[cons])
        seen = {}
        rows = []
        for k in range(1500):
            r, regs = chain_world(rng, entry, k)
            o = native(r.b, regs, entry, 0, lambda q, tr: (cons in tr and q in succ) or q in B.EXIT_STOPS)
            if o is None or cons not in o['trace'] or o['stop'] not in succ or (0x290e in o['trace'] and 0x2986 in o['trace']):
                continue
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
            row('chain-%x-%x-%d' % (entry, cons, k), r, regs, entry, o['stop'], 0, carry_after(cons, c), 2, o)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=REC, a1=PARENT, a2=PARENT, a3=REC, a4=REC, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    rom = 'missing or ambiguous physical program bus ROM byte'
    jump = 'unsupported animation objects fr15 jump target'
    device = 'unsupported animation machine write device'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 0, 4, None, message, fail_pc)
    for cp in CONSUMERS:
        err('unknown-c-%x' % cp, cp, 'objects fr15 caller requires known carry', cp, stop=SUCC[cp][0])
    # the JMP e9c72(PC,D0.W) of e9c64 (contract decision 2): BYTE 90 other than 3
    for v in (0, 1, 2, 4, 5, 0x80, 0xff):
        err('jump-e9c64-%x' % v, 0xe9c64, jump, 0xe9c64, puts=((NODE + 0x90, 1, v),))
    # fixed ROM / bank outside the declared synthetic bytes: the WORD table 4fe8a beyond its 13 WORDs (A0 = 4fea4), the ea3ac LONG of WORD 88 = 3, the
    # ea3c4 LONG of D0 = 2 (entered at e9bae), the ea37c WORD of D6.W = 14 (entered at ea182), the record LONG 7e in ROM (e9bfa), the script LONG 76 in
    # ROM (409e6)
    err('rom-4feb6-a0', 0x4feb6, rom, 0x4feb6, a0=0x4fea4)
    err('rom-e9bae-88-3', 0xe9bae, rom, 0xe9bae, puts=((NODE + 0x88, 2, 3),))
    err('rom-e9bae-d0-2', 0xe9bae, rom, 0xe9bae, d0=2)
    err('rom-ea182-d6-14', 0xea182, rom, 0xea182, d6=0x14, a0=REC)
    err('rom-e9bfa-a1', 0xe9bfa, rom, 0xe9bfa, a1=0xea3cc, a0=NODE + 0x76)
    err('rom-409e6-76', 0x409e6, rom, 0x409e6, puts=((NODE + 0x76, 4, 0x40000),))
    # odd node / stack / pointer: the entry block fails (the row's stop is the PC right after the failing block)
    err('odd-node-40896', 0x40896, wodd, 0x40896, stop=0x49290, a6=NODE + 1)
    err('odd-node-3ff24', 0x3ff24, wodd, 0x3ff24, stop=0x496c2, a6=NODE + 1)
    err('odd-node-4fec6', 0x4fec6, odd, 0x4fec6, stop=0x4feea, a6=NODE + 1)
    err('odd-node-ea13c', 0xea13c, odd, 0xea13c, stop=0xea14c, a6=NODE + 1)
    err('odd-node-c13f8', 0xc13f8, wodd, 0xc13f8, stop=0xc1cf2, a6=NODE + 1)
    err('odd-node-e9b9a', 0xe9b9a, wodd, 0xe9b9a, stop=0xea2c6, a6=NODE + 1)
    err('odd-list-409e6', 0x409e6, odd, 0x409e6, stop=0x40a0e, puts=((NODE + 0x76, 4, REC + 0x41),))
    err('odd-a0-40bc8', 0x40bc8, odd, 0x40bc8, a0=REC + 1)
    err('odd-a0-6f282', 0x6f282, odd, 0x6f282, a0=REC + 1)
    err('odd-a0-40a0a', 0x40a0a, odd, 0x40a0a, stop=0x40a0e, a0=REC + 1)
    err('odd-stack-4088e', 0x4088e, odd, 0x4088e, a7=SP + 1)
    err('odd-stack-40b7a', 0x40b7a, odd, 0x40b7a, a7=SP + 1)
    err('odd-stack-ea2c6', 0xea2c6, odd, 0xea2c6, a7=SP + 1)
    err('odd-stack-4fe86', 0x4fe86, odd, 0x4fe86, a7=SP + 1)
    err('odd-stack-ea1bc', 0xea1bc, odd, 0xea1bc, stop=0xea1d0, a7=SP + 1)
    err('odd-stack-ea166', 0xea166, odd, 0xea166, stop=0xea172, a7=SP + 1)
    err('odd-stack-4febc', 0x4febc, odd, 0x4febc, stop=0x4fec4, a7=SP + 1)
    # fixed ROM writes: the node / parent in fixed ROM
    err('rom-write-4ff64', 0x4ff64, device, 0x4ff64, stop=0x2a00, puts=((NODE + 0xc, 4, 0x1b000),))
    err('rom-write-c141e', 0xc141e, device, 0xc141e, stop=0xc142a, a6=0x1b000)
    err('rom-write-40acc', 0x40acc, device, 0x40acc, stop=0x40af6, a0=0x1b000)
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('3ff54-then-3ff68', 0x3ff54, odd, 0x3ff68, a5=A5 + 1)
    err('4fe48-then-4fe4e', 0x4fe48, odd, 0x4fe4e, a7=SP + 1, d4=5, d5=5, d6=0)
    err('ea1c2-then-ea2be', 0xea1c2, odd, 0xea2be, a7=SP + 1, puts=((NODE + 0x93, 1, 1),))
    err('4ff74-then-4feae', 0x4ff74, odd, 0x4feae, a7=SP + 1, puts=((NODE + 0x7a, 2, 0x100),))
    err('e9b8a-then-e9b9a', 0xe9b8a, wodd, 0xe9b9a, a6=NODE + 1)
    err('c1536-then-c1544', 0xc1536, odd, 0xc1544, a7=SP + 1, puts=((NODE + 0xb6, 1, 2),))
    err('ea1d0-then-ea2be', 0xea1d0, odd, 0xea2be, a7=SP + 1)


def main():
    rng = random.Random(0xF15C)
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
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",NULL,0x0,{%s},%d,%d,%dULL,%d,%dULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs,
                                                                                         d['puts'], outr, d['c'], d['single'], d['digest'], d['pn'], d['pd']))
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
    singles = [d for d in ROWS if d['single'] == 1]
    print('rows', len(ROWS), 'single', len(singles), 'path', sum(1 for d in ROWS if d['single'] == 0), 'chain', sum(1 for d in ROWS if d['single'] == 2),
          'cons', sum(1 for d in ROWS if d['single'] == 3), 'error', sum(1 for d in ROWS if d['single'] == 4),
          'port rows', sum(1 for d in ROWS if d.get('pn')), 'ports', sum(d.get('pn', 0) for d in ROWS))
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
    jstops = set(d['stop'] for d in singles if d['entry'] == 0xe9c64)
    print('table entries reached by the computed-jump rows', sorted(hex(x) for x in jstops))


if __name__ == '__main__':
    main()
