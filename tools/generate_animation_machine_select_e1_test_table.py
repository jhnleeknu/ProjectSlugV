"""Generates the native-oracle tables of engine/tests/animation_machine_select_e1_test.cpp (between the 'generated tables' markers).

Unicorn M68000 on the canonical BE ROM (observer Machine of observe_animation_machine_scheduler: write-protected fixed ROM, 64 KiB work RAM mirrored
100000..1fffff, stack in work RAM, bank 200000) with SYNTHETIC typed physical bytes overlaid at the same offsets the C++ test declares (not ROM data;
data areas only, never over code of the unit): the select tables de580..de660 (light ids de580, WORD pairs de588 / de640 / de650, digit-triple pointers
de598, script LONGs de5c0 / de5d0 / de5e0, window indices de5f0, list pointers de600, sound ids de628, WORD pairs de630), the portrait script LONGs
dfbb0..dfbe0, the digit triples / index lists dfc00..dfcc0 (targets of de598 / de600), the bank-window LONG 2000c0 (:= 200100) and the window table
200100..2001e0 (bank 200000).  A native run that reads any other fixed-ROM or banked byte is dropped (a table index beyond the declared bytes), as is a
run that lands inside the unit on a PC that is not a block start, that takes an exception or that reads a device other than the declared queue BYTE
300000 of 2634.
World: zero work RAM, return LONG 000ff000 at A7 = 10ef00, node A6 = 10e000 (LONG c(A6) := the parent 10eb00), A0 = 10e400 / 10ea00, A1 / A2 = 10ea00 /
10e800, A5 = 108000, WORD 7a(A6) = 0..3 mostly, seeded BYTE / WORD / LONG field edits (sign boundaries included), seeded D0-D7 and the hint worlds of the
V1 spec (tools/unit_fixture_specs/se1.py hint_worlds, converted to absolute addresses; 'mirror' puts the node at 1fe000, 'parent' / 'parent_mirror' the
parent 10eb00 / 1feb00, 'stack' the WORD at A7, 'queue' the BYTE of 2634).  The Z readers de8f4 / de938 are entered with the SR Z equal to (the Z
source BYTE = 0) (contract decision 3; de938 with A0 one of the four credit BYTEs).  Rows:
  single 1  one block: entry = block start, stop = the first PC after the block that is a block start of the unit or outside it (a routed exit).
  single 0  a path inside the unit: stop = the first PC outside the unit (callee entry, the fall-through 183c6, the RTS sentinel).
  single 4  C++ only: entry state, the exact checked error, the failing PC (review 0264 L-1) and the row's run stop (right after the failing block).
E1 has no C consumer: every row ends with C Unknown whatever the incoming C (the block table runs every single row with C Unknown / Clear / Set).
Usage:  .venv/bin/python tools/generate_animation_machine_select_e1_test_table.py  (rewrites the generated section in place)
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
import se1 as B                                     # noqa: E402  (block lists, ranges, Z readers, static decode)
import observe_animation_machine_scheduler as ob    # noqa: E402
import unicorn                                      # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_select_e1_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
KEYS = ob.KEYS
UC_REG = ob.UC_REG
STARTS = list(B.STARTS)
STARTS_SET = set(STARTS)
B.STARTS_SET = STARTS_SET                           # block_instrs stops at the next block start
Z_SET = set(B.Z_RECOMPUTE)
RANGES = list(B.RANGES)
STOP, SP, NODE, A5, CHILD = 0xff000, 0x10ef00, 0x10e000, 0x108000, 0x10e400
REC1, PARENT, OTHER = 0x10ea00, 0x10eb00, 0x10e800
CREDIT = B.CREDIT_BYTES
PORT = 0x300000


def be16(*ws):
    return b''.join(struct.pack('>H', w & 0xffff) for w in ws)


def be32(*ls):
    return b''.join(struct.pack('>I', v & 0xffffffff) for v in ls)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data, data areas only (the original bytes differ)."""
    t = bytearray(b'\xee' * 0xe0)                  # de580..de660
    def put(addr, data):
        o = addr - 0xde580
        t[o:o + len(data)] = data
    put(0xde580, be16(0x0a11, 0x0b22, 0x8c33, 0x7d44))                                   # light id WORD per 7a (dee48)
    put(0xde588, be16(0x0011, 0x0101, 0x0022, 0x0202, 0x8033, 0x0303, 0x0044, 0xf404))   # WORD pairs (D0, D1) per 7a (deba4 / defee)
    put(0xde598, be32(0xdfc00, 0xdfc06, 0xdfc0c, 0xdfc12))                               # digit-triple pointers per 7a (df272)
    put(0xde5c0, be32(0xe10010, 0xe10020, 0x80e10030, 0xe10041))                         # script LONGs per 7a (df0d2 / df202)
    put(0xde5d0, be32(0xe20010, 0xe20020, 0xe20030, 0xe20040))                           # (df230)
    put(0xde5e0, be32(0xe30010, 0xe30020, 0xe30030, 0xe30040))                           # (df038 / df1de)
    put(0xde5f0, be32(0x2, 0x5, 0xffff0001, 0x7))                                        # window indices per 7a (deb5e; the 3rd keeps an upper WORD)
    put(0xde600, be32(0xdfc40, 0xdfc60, 0xdfc80, 0xdfca0))                               # index-list pointers per 7a (deaba)
    put(0xde628, be16(0x18aa, 0x18bb, 0x8001, 0x0000))                                   # sound id WORD per 7a (decda)
    put(0xde630, be16(0x0040, 0x01c1, 0x00c2, 0x81b3, 0x0084, 0x01b5, 0x0106, 0x01c7))   # WORD pairs by D2.W (deb02: (32, 2e))
    put(0xde640, be16(0x0048, 0x0159, 0x00ca, 0x015b, 0x808c, 0x015d, 0x010e, 0x815f))   # WORD pairs (D0, D1) per 7a (deb3a)
    put(0xde650, be16(0x0041, 0x0182, 0x00c3, 0x0184, 0x0085, 0x8186, 0x0107, 0x0188))   # WORD pairs (D0, D1) per 7a (dedd6)
    tables = bytes(t)
    scripts = be32(0xe40010, 0xe40020, 0xe40030, 0x80e40040,                             # dfbb0 (defa0)
                   0xe50010, 0xe50020, 0xe50030, 0xe50040,                               # dfbc0 (dee70 .. deed6)
                   0xe60010, 0xe60020, 0xe60030, 0xe60040)                               # dfbd0 (def58)
    c = bytearray(b'\xee' * 0xc0)                  # dfc00..dfcc0
    c[0:0x18] = be16(0x0d01, 0x0d02, 0x0d03, 0x0d11, 0x8d12, 0x0d13, 0x0d21, 0x0d22, 0xfd23, 0x0d31, 0x0d32, 0x0d33)   # digit triples
    for k in range(4):                             # index lists: 8 LONGs each (window indices; the upper WORD of the 2nd list kept by MOVE.W D2,D1)
        c[0x40 + 0x20 * k:0x60 + 0x20 * k] = be32(*[((0x1230000 if k == 1 else 0) | (k * 8 + i) % 0x38) for i in range(8)])
    window = be32(*[0xc00000 | (i << 4) for i in range(0x38)])                          # 200100..2001e0: LONG i = c00000 + 10 i
    return [(0xde580, tables), (0xdfbb0, scripts), (0xdfc00, bytes(c)), (0x2000c0, be32(0x200100)), (0x200100, window)]


SYN = synthetic()


def inr(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


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


def zsource(ram, regs, pc):
    if B.Z_RECOMPUTE[pc] == 'ca50':
        return ram[(regs['a5'] + B.Z_ADDR) & 0xffff]
    return ram[regs['a0'] & 0xffff] if regs['a0'] in CREDIT else None


def native(ram, regs, pc, carry, stopfn, queue=None):
    snap = dict(ram=bytes(ram), regs=regs, pc=pc, bank=(0x200000, 0xa0, 0x1000))
    m = ob.Machine(PROGRAM, FIXED, snap)
    m.install_basic_hooks()
    c = m.cpu
    z = 0
    if pc in Z_SET:
        zs = zsource(ram, regs, pc)
        if zs is None:
            return None                             # a Z source the C++ rejects (error rows only)
        z = 4 if zs == 0 else 0                     # the Z of the TST.B that ended ca50 / 4a974 (decision 3)
    c.reg_write(UC_REG['sr'], 0x2000 | z | (1 if carry == 2 else 0))
    if queue is not None:
        c.mem_write(PORT, bytes([queue]))
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
    if out['bad'] or out['stop'] is None or stray or m.odd or m.invalid or m.intr or m.fetch_unmapped is not None or m.bank != 0x200000:
        return None
    if m.dev_reads != ([(PORT, 1)] if queue is not None and m.dev_reads else []):
        return None                                 # a device read other than the one declared queue BYTE 300000
    if (m.ff8, m.ff9) != (0xa0, 0x1000) or m.ports:
        return None                                 # E1 writes no PVC port (a run that does is dropped here)
    return dict(stop=out['stop'], trace=trace, regs=m.regs(), ram=m.ram(), ports=[], reads=len(m.dev_reads))


def fnv_add(h, data):
    for x in data:
        h ^= x
        h = (h * 1099511628211) & 0xffffffffffffffff
    return h


def digest(ram, regs, pc, reads):
    tail = b''.join(struct.pack('>I', regs[k]) for k in KEYS) + struct.pack('>III', pc, 0x200000, reads) + bytes([0])
    return fnv_add(fnv_add(1469598103934665603, ram), tail)


def puts_text(r):
    return ','.join('%x:%s' % (a & 0xffffff, d.hex()) for a, d in r.puts[r.base:])


ROWS = []
NAMES = set()


def row(name, r, regs, entry, stop, carry, single, o=None, error=None, fail_pc=0, queue=None, qaddr=None):
    assert name not in NAMES, name
    NAMES.add(name)
    q = -1 if queue is None else queue
    d = dict(name=name, entry=entry, stop=stop, carry=carry, regs=[regs[k] & 0xffffffff for k in KEYS], puts=puts_text(r), error=error, single=single,
             fail=fail_pc, qaddr=(PORT if queue is not None else 0) if qaddr is None else qaddr, qval=max(q, 0))
    if o is not None:
        d.update(out=[o['regs'][k] for k in KEYS], digest=digest(o['ram'], o['regs'], o['stop'], o['reads']), reads=o['reads'])
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
        if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'scc', 'abcd'):
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
    """-> (ram, regs, queue BYTE or None)."""
    r = base_ram()
    regs = dict(d0=rng.getrandbits(32), d1=rng.getrandbits(32), d2=rng.getrandbits(32), d3=rng.getrandbits(32), d4=rng.getrandbits(32),
                d5=rng.getrandbits(32), d6=rng.getrandbits(32), d7=rng.getrandbits(32), a0=rng.choice((CHILD, CHILD, REC1)),
                a1=rng.choice((REC1, OTHER)), a2=rng.choice((OTHER, CHILD)), a3=REC1, a4=REC1, a5=A5, a6=NODE, a7=SP)
    if rng.random() < 0.5:
        regs['d0'] = rng.choice((0, 1, 2, 3, 4, 0xff, 0x100, 0x12340001, 0xffff, 0x8000, 0x10000, 0x10003))
    if rng.random() < 0.5:
        regs['d1'] = rng.choice((0xffff, 0xffffffff, 1, 0x10001, 0, 2, 0x1ffff))
    if rng.random() < 0.5:
        regs['d2'] = rng.choice((0, 1, 2, 3, 0x10000, 0x10001, 0xffff0003, 7))
    base_of = {6: NODE, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: A5}
    for reg, disp, size in fl:
        if reg not in base_of or rng.random() < 0.15:
            continue
        if reg == 6 and (disp in POINTERS or disp == 0x7a):
            continue                                    # (A6) callback LONG, the node links and the pointer fields / index are declared below
        addr = (base_of[reg] + disp) & 0xffffffff
        if not (0x100000 <= addr and addr + size <= 0x110000) or (SP - 0x40 <= addr < SP + 4) or (size > 1 and addr & 1):
            continue
        r.put(addr, size, rand_val(rng, size))
    r.put(NODE + 0xc, 4, PARENT)
    r.put(NODE + 0x7a, 2, rng.choice((0, 1, 2, 3, 0, 1, 2, 3, 4, 0x8000)))
    for off, n in ((0x62, 1), (0x63, 1), (0x2e, 2)):
        if rng.random() < 0.7:
            r.put(PARENT + off, n, rand_val(rng, n))
    if rng.random() < 0.6:
        r.put(A5 + B.Z_ADDR, 1, rng.choice((0, 0, 1, 0x80, 0xff)))         # the Z source of de8f4
    for a in CREDIT:
        if rng.random() < 0.5:
            r.put(a, 1, rng.choice((0, 0, 1, 0x80)))                     # the Z sources of de938
    if s == 0xde938:
        regs['a0'] = rng.choice(CREDIT)
    if rng.random() < 0.3:
        r.put(SP - 2, 2, rng.choice((0, 1, 2, 3, 7)))                     # a WORD below the return LONG (never read: pushes land here)
    queue = rng.choice((0, 0x10, 0x20, 0x40, 0x70, 0x8f, 0xff, rng.getrandbits(8))) if s == 0x2634 else None
    if hint:
        regs.update(hint.get('regs', {}))
        for off, n, v in hint.get('a6off', []):
            r.put(NODE + off, n, v)
        for off, n, v in hint.get('a5off', []):
            r.put((A5 + off) & 0xffffff, n, v)
        for off, n, v in hint.get('parent', []):
            r.put(NODE + 0xc, 4, PARENT | (0xf0000 if hint.get('parent_mirror') else 0))
            r.put(PARENT + off, n, v)
        for off, n, v in hint.get('a0off', []):
            a = (regs['a0'] + off) & 0xffffff
            if 0x100000 <= a and a + n <= 0x110000:
                r.put(a, n, v)
        if hint.get('mirror'):
            regs['a6'] = NODE | 0xf0000                 # the node in the upper RAM mirror (1fe000 = 10e000)
        for off, n, v in hint.get('writes', []):
            r.put(0x100000 + off, n, v)
        at = SP
        for n, v in hint.get('stack', []):
            r.put(at, n, v)
            at += n
        if 'queue' in hint:
            queue = hint['queue']
    if s == 0xde938 and regs['a0'] not in CREDIT:
        regs['a0'] = CREDIT[0]
    return r, regs, queue


# the stops a success row may end at outside the unit: the routed exits and the RTS sentinel
ALLOWED_STOPS = {0x28ae, 0x3918, 0x3af8, 0x3c44, 0x3d7e, 0x8cda, 0x8ebe, 0x8ff4, 0x183c6, 0x185f4, 0x43e04, 0x43e34, 0x43ea4, 0x49a84, 0x49f8c,
                 0x49fc6, 0x4a974, 0x4e186, 0xca50, STOP}


def allowed(stop):
    return stop in STARTS_SET or stop in ALLOWED_STOPS


def single_stop(p, tr):
    return p in STARTS_SET or not inr(p)


def path_stop(p, tr):
    return not inr(p)


def hints(s):
    """The V1 spec hint worlds (se1.hint_worlds) of the block; converted to absolute addresses by world()."""
    return B.hint_worlds(s)


def gen_singles(rng):
    for s in STARTS:
        fl = fields(s)
        kept = {}
        hs = hints(s)
        for t in range(400 + len(hs)):
            hint = hs[t] if t < len(hs) else None
            r, regs, q = world(rng, fl, s, hint)
            o = native(r.b, regs, s, 0, single_stop, q)
            if o is None:
                continue
            nxt = o['stop']
            if nxt == s:
                continue
            if (inr(nxt) and nxt not in STARTS_SET) or not allowed(nxt):
                continue
            key = (nxt, 'h%d' % t) if hint else nxt
            if key in kept:
                continue
            if not hint and sum(1 for k in kept if (k[0] if isinstance(k, tuple) else k) == nxt) >= 2:
                continue
            kept[key] = (r, regs, o, q)
            if t >= len(hs) and len(kept) >= 6:
                break
            if t >= len(hs) and t > 120 and len(kept) >= 2:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o, q)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('%x-%d' % (s, i), r, regs, s, o['stop'], 0, 1, o, queue=q)


PATH_ENTRIES = (0x2634, 0x18364, 0x1837c, 0x18392, 0xde8bc, 0xde8ca, 0xde8ee, 0xde8f4, 0xde938, 0xde97e, 0xde9e8, 0xdea50, 0xdea86, 0xdeaba, 0xdeb02,
                0xdeb1a, 0xdeba4, 0xdec10, 0xdec16, 0xdec6e, 0xdec8c, 0xdecd2, 0xded00, 0xded06, 0xded50, 0xded9e, 0xdedb6, 0xdee28, 0xdee36, 0xdee5e,
                0xdef32, 0xdef40, 0xdef58, 0xdef8c, 0xdef98, 0xdefc0, 0xdefdc, 0xdf038, 0xdf06c, 0xdf076, 0xdf0b0, 0xdf0f2, 0xdf128, 0xdf15e, 0xdf16e,
                0xdf192, 0xdf1c0, 0xdf21a, 0xdf230, 0xdf254, 0xdf272, 0xdf2c0)


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
            r, regs, q = world(rng, fl, s, hs[t % len(hs)] if hs and t % 3 == 1 else None)
            o = native(r.b, regs, s, carry, path_stop, q)
            if o is None:
                continue
            ex = [p for p in o['trace'] if p in STARTS_SET]
            if not allowed(o['stop']) or o['stop'] == s:
                continue
            key = (o['stop'], tuple(ex[:60]))
            if key in kept:
                continue
            kept[key] = (r, regs, o, carry, q)
            if len(kept) >= 4:
                break
        assert kept, hex(s)
        for i, (k, (r, regs, o, carry, q)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            row('path-%x-%d' % (s, i), r, regs, s, o['stop'], carry, 0, o, queue=q)


def gen_errors():
    plain = dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=CHILD, a1=REC1, a2=OTHER, a3=0, a4=0, a5=A5, a6=NODE, a7=SP)
    odd = 'program bus requires even WORD/LONG address'
    wodd = 'invalid animation machine write size/alignment'
    flag = 'unsupported animation select e1 flag source'
    missing = 'missing or ambiguous physical program bus ROM byte'

    def err(name, entry, message, fail_pc, carry=0, puts=(), stop=None, queue=None, qaddr=None, **kw):
        r = base_ram()
        for a, n, v in puts:
            r.put(a, n, v)
        regs = dict(plain)
        regs.update(kw)
        row('error-' + name, r, regs, entry, STOP if stop is None else stop, carry, 4, None, message, fail_pc, queue=queue, qaddr=qaddr)
    # the Z sources (decision 3): ca50 rule outside work RAM; 4a974 rule outside the four credit BYTEs (mirror and neighbours included)
    err('zsource-rom-de8f4', 0xde8f4, flag, 0xde8f4, a5=0x8000)
    err('zsource-io-de8f4', 0xde8f4, flag, 0xde8f4, a5=0x400000)
    for a0 in (0x10fdb2, 0x100003, 0x100006, 0x1ffdb0, 0x10fdaf, NODE, 0xff10fdb0):
        err('zsource-de938-%x' % a0, 0xde938, flag, 0xde938, a0=a0)
    # de8ee (JSR ca50) -> ca50 tests the synthetic ROM BYTE de580 (A5 = de580 + 7699) -> RTS -> de8f4 rejects that source
    err('de8ee-then-de8f4', 0xde8ee, flag, 0xde8f4, stop=0xde8f8, a5=0xde580 + 0x7699)
    # the input port of 2634: no queue entry / another device first
    err('2634-queue-empty', 0x2634, 'animation machine external read queue empty', 0x2634)
    err('2634-queue-mismatch', 0x2634, 'animation machine external read queue mismatch', 0x2634, queue=0, qaddr=0x340000)
    # odd node / stack / A0 / parent; tables beyond the declared synthetic bytes
    err('odd-node-de8ca', 0xde8ca, odd, 0xde8ca, stop=0xde8d2, a6=NODE + 1)
    err('odd-node-de8de', 0xde8de, wodd, 0xde8de, stop=0xde8ee, a6=NODE + 1)
    err('odd-stack-dea8e', 0xdea8e, odd, 0xdea8e, stop=0xdea98, a7=SP + 1)
    err('odd-stack-de97e', 0xde97e, odd, 0xde97e, stop=0x8ff4, a7=SP + 1)
    err('odd-a0-18364', 0x18364, odd, 0x18364, a0=NODE + 1)
    err('odd-parent-deef0', 0xdeef0, odd, 0xdeef0, stop=0x3c44, puts=((NODE + 0xc, 4, PARENT + 1),))
    err('table-dee48-7a-8', 0xdee48, missing, 0xdee48, stop=0x8ebe, puts=((NODE + 0x7a, 2, 0x80),))
    err('table-deaba-7a-20', 0xdeaba, missing, 0xdeaba, stop=0x49f8c, puts=((NODE + 0x7a, 2, 0x20),))
    # failures after executed blocks (rollback; the failing PC differs from the entry):
    err('de8d2-then-de8ee', 0xde8d2, odd, 0xde8ee, stop=0xca50, a7=SP + 1)
    err('dec66-then-dec6c', 0xdec66, odd, 0xdec6c, a7=SP + 1)
    err('df0fc-then-df122', 0xdf0fc, odd, 0xdf122, stop=0xde8bc, a7=SP + 1, puts=((NODE + 0xc, 4, PARENT),))
    err('18384-then-18392', 0x18384, odd, 0x18392, a0=NODE + 1, d7=0, d2=1)
    err('df264-then-df272', 0xdf264, missing, 0xdf272, stop=0x8cda, puts=((NODE + 0x7a, 2, 0x40),))
    err('odd-stack-de92e', 0xde92e, odd, 0xde92e, stop=0x4a974, a7=SP + 1)


def main():
    rng = random.Random(0xE1E1)
    B.load_routing()
    gen_singles(rng)
    gen_paths(rng)
    gen_errors()
    out = []
    for d in ROWS:
        regs = ','.join('0x%x' % v for v in d['regs'])
        if d['error'] is None:
            outr = ','.join('0x%x' % v for v in d['out'])
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",0x%x,0x%x,NULL,0x0,{%s},%d,%dULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'],
                                                                                   d['qaddr'], d['qval'], outr, d['single'], d['digest']))
        else:
            out.append(' {"%s",0x%x,0x%x,%d,{%s},"%s",0x%x,0x%x,"%s",0x%x,{0},%d,0ULL},' % (d['name'], d['entry'], d['stop'], d['carry'], regs, d['puts'],
                                                                                d['qaddr'], d['qval'], d['error'], d['fail'], d['single']))
    tables = [BEGIN]
    tables.append('const std::uint32_t STARTS[]={%s};' % ','.join('0x%x' % x for x in STARTS))
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
    print('rows', len(ROWS), 'single', len(singles), 'path', sum(1 for d in ROWS if d['single'] == 0), 'error', sum(1 for d in ROWS if d['single'] == 4))
    entered = set(d['entry'] for d in singles)
    print('starts without single', [hex(s) for s in STARTS if s not in entered])
    succ = {}
    for d in singles:
        succ.setdefault(d['entry'], set()).add(d['stop'])
    one = []
    for s in STARTS:
        if s not in succ:
            continue
        nxt = B.static_next(s)
        if nxt is not None and len(nxt) > 1 and not nxt <= succ[s]:
            one.append((hex(s), sorted(hex(x) for x in nxt - succ[s])))
    print('branch blocks with a missing successor', one)
    print('stops', sorted(set(hex(d['stop']) for d in ROWS if d['error'] is None and not inr(d['stop']))))


if __name__ == '__main__':
    main()
