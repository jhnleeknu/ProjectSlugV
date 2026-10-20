"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b2c_test.cpp (between the 'generated tables' markers).

Synthetic world (no ROM data in the repository): zero work RAM, return LONG 000ff000 at A7 = 10f000, node A6 = 10e000, A5 = 108000, parent c(A6) = 10d000, seeded BYTE /
WORD / LONG field edits of the node, the parent, the player objects 100cb8 / 100da8 and a LONG table at 10c000, seeded D0-D7 and A0 (live JMP (A0) targets of the unit, the
slot-table bases of the input dispatcher and pointers).  The fixed-ROM / banked data the 218 blocks read are replaced by SYNTHETIC typed bytes on both sides (native Unicorn
fixed-area copy and program image copy, C++ physical resources): the LONG state table / WORD masks 3ab80..3aba4, the BYTE slot table 3abde..3abee, the WORD tables
3af6c..3af86, the BYTE pairs 3b4bc..3b4e0, the LONG rows 1d1b0..1d1d0 and the banked bytes 200000..200100 (bank base 200000).  A native run that reads any other fixed-ROM
or banked byte is dropped (the C++ has no bytes there).  For every block start and every world the ORIGINAL code runs natively (Unicorn M68000, never the C++) from the
block start to the first PC that is another block start or outside the eight routed ranges; one row per distinct successor (the three consumers: per incoming C, native
SR C = 0 / 1) records the successor and the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, reads, status.  Non-consumer blocks are also checked here to be independent of
the incoming C (the table has one row; the test runs all three C tags).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b2c_test_table.py  (rewrites the generated section in place)
"""
import ctypes
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'unit_fixture_specs'))
import b2c as B                                   # noqa: E402  (block lists, ranges, consumers)
import verify_animation_machine_unit_fixtures as U  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b2c_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
STOP, SP, NODE, A5, PARENT, LTAB = 0xff000, 0x10f000, 0x10e000, 0x108000, 0x10d000, 0x10c000
FIXED = dict(a1=0x10c400, a2=0x10c300, a3=0x10c200, a4=0x10c100, a5=A5, a6=NODE, a7=SP)
BANK = 0x200000
WORLDS = 64
M64 = (1 << 64) - 1
BYTES = {0x13: (0, 1, 0x7f, 0x80, 0xfe, 0xff), 0x14: (0, 3), 0x15: (0, 1, 0x80, 0x81), 0x1b: (0, 7), 0x5e: (0, 5), 0x61: (0, 0x80, 0xff), 0x8e: (0, 1, 0x7f, 0x80, 0xff),
         0x8f: (0, 2, 0x7f, 0x80, 0xfe), 0x94: (0, 1, 0x10, 0x11, 0xff), 0x95: (0, 1, 2, 3, 4, 5, 0xff, 0xff), 0x96: (0, 1, 2, 3, 4, 5, 0xff, 0xff),
         0x97: (0, 2, 0x7f, 0x80, 0xff), 0x99: (0, 1, 3), 0x9a: (0, 1, 2, 3), 0x9d: (0, 0x10, 0x40, 0x50, 0xff), 0x9e: (0, 0x10, 0x50, 0xff),
         0x9f: (0, 3, 0x10, 0x11, 0x12, 0xff), 0xa3: (0, 1, 6, 0xff), 0xa6: (0, 5), 0xa8: (0, 2), 0xa9: (0, 9), 0xaa: (0, 9), 0xab: (0, 1), 0xb2: (0, 0x18)}
WORDS = {0x1e: (0, 0x8811), 0x20: (0, 0xf2), 0x2e: (0, 0x10, 0xfff0, 0x8000), 0x32: (0, 0x20, 0xffe0), 0x36: (0, 1, 0x7fff, 0x8000, 0xffff),
         0x3a: (0, 1, 0x7fff, 0x8000, 0xffff), 0x42: (0, 0x100, 0xff00), 0x46: (0, 0x80, 0xff80), 0x68: (0, 0x8811), 0x86: (0, 1, 0x100, 0xff), 0x8a: (0, 1)}
LONGS = {0x22: (LTAB, BANK + 0x40, LTAB + 0x20), 0x56: (0, 0x3b882), 0x64: (0, 0x10000), 0x7e: (0, 1), 0x82: (0x3a60a, 0x3a622, 0)}
PARENT_FIELDS = {0x88: (2, (0, 1, 2, 3)), 0x9f: (1, (0, 8, 0x10, 0x11, 0x12, 0xff)), 0x62: (1, (0, 0x5a))}
D_VALUES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x10, 0x11, 0x7f, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12345678, 0xffffff00, 0xffffffff)
A0_VALUES = B.CONTINUATIONS + B.SLOT_TABLES + B.STATE_ENTRIES + (0x10fe00, LTAB, PARENT)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    out = []
    t = bytearray()
    for v in (0x3a774, 0x3a8ba, 0x3a8f8, 0x3aae8, 0x3ab0c, 0x3a62e):          # LONG state table (a permutation of the unit's state entries)
        t += v.to_bytes(4, 'big')
    for v in (0x0003, 0x0005, 0x0009, 0x0011, 0x0021, 0x00ff):                 # WORD request masks
        t += v.to_bytes(2, 'big')
    out.append((0x3ab80, bytes(t)))
    out.append((0x3abde, bytes(((i * 3 + 1) % 7) for i in range(16))))         # BYTE slot numbers 0..6
    out.append((0x3af6c, b''.join(((0x1200 + 0x111 * i) & 0xffff).to_bytes(2, 'big') for i in range(13))))
    out.append((0x3b4bc, bytes(((i * 37 + 0x85) & 0xff) for i in range(36))))  # signed BYTE pairs
    rows = bytearray()
    for i in range(4):
        rows += (BANK + 0x40 + 8 * i).to_bytes(4, 'big') + (0x10000 * i + 0x1234 + i).to_bytes(4, 'big')
    out.append((0x1d1b0, bytes(rows)))
    out.append((BANK, bytes(((i * 37 + 11) & 0xff) for i in range(0x100))))
    return out


SYN = synthetic()
FIXED_RANGES = [(a, a + len(b)) for a, b in SYN if a < 0x100000]
BANK_RANGES = [(a, a + len(b)) for a, b in SYN if a >= 0x200000]


def make_world(rng):
    regs = {}
    for k in range(8):
        regs['d%d' % k] = rng.choice(D_VALUES) if rng.random() < 0.7 else rng.getrandbits(32)
    regs['a0'] = rng.choice(A0_VALUES)
    puts = []
    for off, vals in BYTES.items():
        if rng.random() < 0.6:
            puts.append((NODE + off, 1, rng.choice(vals)))
    for off, vals in WORDS.items():
        if rng.random() < 0.5:
            puts.append((NODE + off, 2, rng.choice(vals)))
    for off, vals in LONGS.items():
        if rng.random() < 0.5:
            puts.append((NODE + off, 4, rng.choice(vals)))
    if rng.random() < 0.8:
        puts.append((NODE + 0xc, 4, PARENT))
        for off, (size, vals) in PARENT_FIELDS.items():
            puts.append((PARENT + off, size, rng.choice(vals)))
    for obj in (0x100cb8, 0x100da8):
        if rng.random() < 0.7:
            puts.append((obj + 0x9f, 1, rng.choice((0, 1, 3, 8))))
    if rng.random() < 0.6:
        for i in range(16):
            puts.append((LTAB + 4 * i, 4, rng.choice((0x200040, 0x200044, LTAB + 0x80, 0x12345678))))
    if rng.random() < 0.35:
        puts.append((SP, 4, rng.choice(B.SLOT_TABLES)))       # the LONG popped by 3abc0 (MOVEA.L (A7)+,A0)
    return dict(puts=puts, regs=regs)


def base_state(world):
    ram = bytearray(65536)
    ram[SP & 0xffff:(SP & 0xffff) + 4] = STOP.to_bytes(4, 'big')
    for addr, size, value in world['puts']:
        ram[addr & 0xffff:(addr & 0xffff) + size] = value.to_bytes(size, 'big')
    regs = dict(FIXED)
    regs.update(world['regs'])
    page = bytearray(8192)
    page[0x1ff0:0x1ff4] = (0xa0).to_bytes(2, 'big') + (0x1000).to_bytes(2, 'big')
    return dict(ram=bytes(ram), regs=regs, bank=(BANK, 0xa0, 0x1000), pvc=bytes(page))


NATIVE = []


def native_buffers():
    if not NATIVE:
        nat = U.native()
        fixed = bytearray(bytes(nat.fixed))
        program = bytearray(nat.program)
        for a, b in SYN:
            if a < 0x100000:
                fixed[a:a + len(b)] = b
            program[a:a + len(b)] = b                       # a fixed address is also its physical offset; a banked one with bank base 200000
        NATIVE.append(((ctypes.c_ubyte * 0x100000).from_buffer_copy(bytes(fixed)), bytes(program)))
    return NATIVE[0]


def edge(pc):
    return pc in B.STARTS_SET or not B.mine(pc)


def run_native(state, pc, carry):
    """-> (next_pc, ram, regs) of the original code from the block start `pc` (SR.C = 1 when carry == 2) to the first other block start / PC outside the routed ranges."""
    import unicorn
    nat = U.native()
    fixed, program = native_buffers()
    snap = dict(ram=state['ram'], regs=state['regs'], pc=pc, bank=state['bank'])
    m = nat.PB.PvcMachine(program, fixed, snap)
    m.install_basic_hooks()
    c = m.cpu
    c.mem_write(U.PVC_LO, state['pvc'])
    if carry == 2:
        c.reg_write(nat.S.UC_REG['sr'], 0x2001)
    seen = dict(stop=None, steps=0, bad=None)

    def code(uc, at, size, user):
        if seen['steps'] > 0 and edge(at):
            seen['stop'] = at
            uc.emu_stop()
            return
        seen['steps'] += 1

    def read(uc, access, address, size, value, user):
        if address < 0x100000:
            if not any(lo <= address and address + size <= hi for lo, hi in FIXED_RANGES):
                seen['bad'] = ('fixed read outside the synthetic bytes', address)
                uc.emu_stop()
        elif 0x200000 <= address < 0x2fe000:
            if not any(lo <= address and address + size <= hi for lo, hi in BANK_RANGES):
                seen['bad'] = ('banked read outside the synthetic bytes', address)
                uc.emu_stop()
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    c.hook_add(unicorn.UC_HOOK_MEM_READ, read, begin=0, end=0x2fffff)
    try:
        c.emu_start(pc, 0xffffff, count=4000)
    except unicorn.UcError:
        return None
    if seen['stop'] is None or seen['bad'] is not None or m.odd is not None or m.invalid is not None or m.intr is not None or m.ports or m.dev_reads:
        return None
    if seen['stop'] & 1:
        return None                                         # an odd computed target: a checked error in the C++, tested separately
    return seen['stop'], m.ram(), m.regs()


def digest(ram, regs, pc):
    h = 1469598103934665603
    for b in ram:
        h = ((h ^ b) * 1099511628211) & M64
    tail = bytearray()
    for k in range(8):
        tail += (regs['d%d' % k] & 0xffffffff).to_bytes(4, 'big')
    for k in range(8):
        tail += (regs['a%d' % k] & 0xffffffff).to_bytes(4, 'big')
    tail += pc.to_bytes(4, 'big') + BANK.to_bytes(4, 'big') + (0).to_bytes(4, 'big') + bytes([0])
    for b in tail:
        h = ((h ^ b) * 1099511628211) & M64
    return h


def hexput(world):
    return ','.join('%x:%s' % (addr, value.to_bytes(size, 'big').hex()) for addr, size, value in world['puts'])


# Boundary values of every compare / test / table index: one forced row each (successor repeats are kept).  (pc, node BYTE/WORD/LONG edits, register edits)
BOUNDARY_CASES = (
    [(0x3ab3e, {0x95: (1, v)}, {}) for v in (0, 5, 0xfe, 0xff)] +
    [(0x3ab4c, {0x96: (1, v)}, {}) for v in (0, 5, 0xff)] +
    [(0x3ab5a, {}, dict(d0=d, d1=v, d2=0xffff0000)) for v in (0, 5) for d in (0, 1, 16, 31)] +
    [(0x3ab6c, {}, dict(d0=v)) for v in (0x7f, 0x80)] +
    [(0x3ab72, {}, dict(d0=v)) for v in (0, 5, 0x12340003)] +
    [(0x3abaa, {}, dict(d0=v)) for v in (0, 1, 2, 3)] +
    [(0x3a97c, {0x9f: (1, v)}, {}) for v in (0x10, 0x11)] +
    [(0x3b48c, {0x9f: (1, v)}, {}) for v in (0x11, 0x12)] +
    [(0x3aa8e, {0x97: (1, v)}, {}) for v in (0x7f, 0x80)] +
    [(0x3aaa4, {0x95: (1, v), 0x96: (1, 2)}, {}) for v in (0xfe, 0xff)] +
    [(0x3aeca, {0x13: (1, v)}, {}) for v in (0xfe, 0xff)] +
    [(0x3aed6, {0x3a: (2, w)}, dict(d0=d)) for d in (0x80, 0x8000) for w in (0x7fff, 0x8000)] +
    [(0x3af1c, {0x13: (1, v)}, {}) for v in (0, 0xff)] +
    [(0x1bf80, {}, dict(d0=v)) for v in (0, 0x100, 1)] +
    [(0x1d198, {}, dict(d0=v)) for v in (0, 3)])


def main():
    rng = random.Random(0xb2c7)
    worlds = [make_world(rng) for _ in range(WORLDS)]
    states = [base_state(w) for w in worlds]
    rows, used = [], set()
    unreached = []
    for pc in B.STARTS:
        consumer = pc in B.CONSUMERS
        incoming = (1, 2) if consumer else (0,)
        got = 0
        for c in incoming:
            seen = {}
            for wi, st in enumerate(states):
                r = run_native(st, pc, c)
                if r is None:
                    continue
                nxt, ram, regs = r
                if not consumer and wi < 8:
                    for other in (1, 2):                    # the incoming C never matters for a non-consumer block
                        r2 = run_native(st, pc, other)
                        assert r2 is not None and r2[0] == nxt and r2[1] == ram and r2[2] == regs, (hex(pc), wi, other)
                if nxt in seen:
                    continue
                seen[nxt] = True
                regs['pc'] = nxt
                rows.append(dict(pc=pc, world=wi, c=c, next=nxt, digest=digest(ram, regs, nxt)))
                used.add(wi)
                got += 1
        if got == 0:
            unreached.append(pc)
    assert not unreached, [hex(p) for p in unreached]
    for pc, fields, regs in BOUNDARY_CASES:
        r0 = dict(('d%d' % k, 0) for k in range(8))
        r0['a0'] = B.CONTINUATIONS[0]
        r0.update(regs)
        worlds.append(dict(puts=[(NODE + off, size, value) for off, (size, value) in sorted(fields.items())], regs=r0))
        st = base_state(worlds[-1])
        r = run_native(st, pc, 0)
        assert r is not None, hex(pc)
        nxt, ram, rg = r
        rg['pc'] = nxt
        rows.append(dict(pc=pc, world=len(worlds) - 1, c=0, next=nxt, digest=digest(ram, rg, nxt)))
        used.add(len(worlds) - 1)
    remap = {w: i for i, w in enumerate(sorted(used))}
    lines = [BEGIN, 'const World WORLDS[]={']
    for w in sorted(used):
        d = worlds[w]['regs']
        lines.append(' {"%s",{%s},0x%x},' % (hexput(worlds[w]), ','.join('0x%x' % d['d%d' % k] for k in range(8)), d['a0']))
    lines.append('};')
    lines.append('const Row ROWS[]={')
    for r in rows:
        lines.append(' {0x%x,%d,%d,0x%x,0x%xULL},' % (r['pc'], remap[r['world']], r['c'], r['next'], r['digest']))
    lines.append('};')
    lines.append('const Synthetic SYNTHETIC[]={')
    for a, b in SYN:
        lines.append(' {0x%x,"%s"},' % (a, b.hex()))
    lines.append('};')
    lines.append('const std::uint32_t STARTS[]={' + ','.join('0x%x' % x for x in B.STARTS) + '};')
    lines.append(END)
    text = TEST.read_text()
    i, j = text.index(BEGIN), text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(lines) + text[j:])
    print('worlds', len(used), 'rows', len(rows))


if __name__ == '__main__':
    main()
