"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b2e_test.cpp (between the 'generated tables' markers).

Synthetic world (no ROM data in the repository): zero work RAM, return LONG 000ff000 at A7 = 10f000, node A6 = 10e000, A5 = 108000, parent c(A6) = 10d000, a second
node 10c400 (A0 of the stores into a new child), seeded BYTE / WORD / LONG field edits of the node and the parent, the callback argument WORDs at 10c000, the ranking
records 10f02e..10f086, optional stacked values above the return LONG, seeded D0-D7, A0 and A1.  The fixed-ROM / banked data the 109 blocks read are replaced by
SYNTHETIC typed bytes on both sides (native Unicorn fixed-area copy and program image copy, C++ physical resources): the angle bytes 44380..44602 (every 44602 read
lies in 44383..44601), the rank-label LONG pointers e637a..e63a6 with their text e63a6..e63d2, the two LONG script pointers e63e4..e63ec and the banked bytes
200000..200100 (bank base 200000).  A native run that reads any other fixed-ROM or banked byte is dropped (the C++ has no bytes there).  For every block start
(except e6890, whose odd WORD write is a checked C++ error tested separately) and every world the ORIGINAL code runs natively (Unicorn M68000, never the C++) from
the block start to the first PC that is another block start or outside the ten routed ranges; one row per distinct successor (the five consumers: per incoming C,
native SR C = 0 / 1) records the successor and the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, reads, status.  Non-consumer blocks are also checked here to be
independent of the incoming C (the table has one row; the test runs all three C tags).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b2e_test_table.py  (rewrites the generated section in place)
"""
import ctypes
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'unit_fixture_specs'))
import b2e as B                                   # noqa: E402  (block lists, ranges, consumers)
import verify_animation_machine_unit_fixtures as U  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b2e_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
STOP, SP, NODE, A5, PARENT, CHILD, ARGS, RECORDS = 0xff000, 0x10f000, 0x10e000, 0x108000, 0x10d000, 0x10c400, 0x10c000, 0x10f02e
FIXED = dict(a2=0x10c300, a3=0x10c200, a4=0x10c100, a5=A5, a6=NODE, a7=SP)
BANK = 0x200000
WORLDS = 64
M64 = (1 << 64) - 1
BYTES = {0x12: (0, 0xef, 0xf0, 0xff), 0x15: (0, 1, 0x80, 0x81), 0x60: (0, 3), 0x80: (0, 1, 0xff), 0x98: (0, 9), 0x9d: (0, 0x10, 0xef, 0xff), 0x9e: (0, 0x10, 0xff),
         0xa1: (0, 0x40, 0x80, 0xff), 0xa2: (0, 5), 0xa3: (0, 6), 0xa6: (0, 1, 2, 5, 0xff), 0xa8: (0, 1, 2, 3, 4, 0x80, 0xff)}
WORDS = {0x1e: (0, 0x1001), 0x20: (0, 0xea), 0x68: (0, 0xfff1), 0x76: (0, 1, 2, 0x5a, 0xffff), 0x78: (0, 1, 8, 9, 10), 0x7a: (0, 1, 2, 0xffff),
         0x7c: (0, 1, 0xffff), 0x7e: (0, 5)}
LONGS = {0x22: (0, BANK + 0x40), 0x36: (0, 0x80000000, 0x7fffffff, 0xffff0000, 0x12345678), 0x3a: (0, 0xfffe0000, 0x00020000, 0x7fff0000),
         0x64: (0, 0x10000), 0x7a: (0, 0x288c, 0x10fe00)}
PARENT_FIELDS = {0x62: (1, (0, 0x5a)), 0x80: (1, (0, 0xff))}
D_VALUES = (0, 1, 2, 3, 4, 5, 9, 10, 11, 0x10, 0x3f, 0x40, 0x7f, 0x80, 0xff, 0x100, 0x1ff, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12345678, 0xffffff00, 0xffffffff)
A0_VALUES = (ARGS, ARGS + 2, CHILD, PARENT)


def synthetic():
    """(address, bytes) list.  Deterministic, not ROM data."""
    out = []
    out.append((0x44380, bytes(((i * 53 + 0x1d) & 0xff) for i in range(0x44602 - 0x44380))))   # angle bytes (44602.. is code: never read)
    ptr = bytearray()
    for k in range(11):
        ptr += (0xe63a6 + 4 * k).to_bytes(4, 'big')                                          # rank-label pointers into the synthetic text below
    out.append((0xe637a, bytes(ptr)))
    out.append((0xe63a6, bytes(((0x30 + k) & 0xff) for k in range(44))))
    out.append((0xe63e4, (0x3c000).to_bytes(4, 'big') + (0x3c100).to_bytes(4, 'big')))         # the two script pointers (values only)
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
    regs['a1'] = rng.choice((ARGS, RECORDS, ARGS + 4))
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
    for k in range(6):
        puts.append((ARGS + 2 * k, 2, rng.choice((0, 0x10, 0x40, 0x80, 0xfff0, 0xffff, 0x1234))))
    if rng.random() < 0.7:
        for k in range(11):
            puts.append((RECORDS + 8 * k, 4, rng.choice((0, 5, 0x1000, 0x80000000, 0x00107400 - 0x1000 * k))))
            puts.append((RECORDS + 8 * k + 4, 4, 0x41424300 + k))
    if rng.random() < 0.3:
        stack = rng.choice(((2, 5), (8, 0x12348765)))
        if stack[0] == 2:                                   # a stacked row WORD above the return LONG (e682a / e678c)
            puts += [(SP, 2, stack[1]), (SP + 2, 4, STOP)]
        else:                                               # D0.W, D1.W and LONG 0 above the return LONG (4db34)
            puts += [(SP, 4, stack[1]), (SP + 4, 4, 0), (SP + 8, 4, STOP)]
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
    [(0x3abee, {0xa6: (1, v)}, {}) for v in (0, 1)] +
    [(0x3abf6, {0x9d: (1, v)}, {}) for v in (0xef, 0x10)] +
    [(0x3ac1c, {0xa6: (1, 1), 0xa8: (1, v)}, {}) for v in (3, 4)] +
    [(0x3ac98, {}, dict(d7=v, d2=0x8000)) for v in (0, 0x80)] +
    [(0x3aca0, {}, dict(d7=v, a0=CHILD)) for v in (0x3f, 0x40)] +
    [(0x3acb2, {0xa8: (1, v)}, dict(d7=2, a0=CHILD)) for v in (0, 1, 2, 0xff)] +
    [(0x3b458, {0x36: (4, x), 0x3a: (4, y)}, {}) for x, y in ((0x80000000, 0x7fff0000), (0x7fffffff, 0xfffe0000))] +
    [(0x3b46c, {0xa1: (1, a)}, dict(d0=d)) for d, a in ((0x7f, 0), (0, 0x80), (0xff, 0xff))] +
    [(0x44602, {}, dict(d0=a, d1=b)) for a, b in ((0, 0), (0x8000, 1), (0xffff, 0xfffe), (0x100, 0x200), (2, 0x1ff))] +
    [(0x4462a, {}, dict(d0=a, d1=b)) for a, b in ((0, 0xff), (0xff, 0), (0x40, 0x40))] +
    [(0x4463c, {}, dict(d0=0x40, d2=b, d3=c)) for b in (0, 0xff) for c in (0, 0xff)] +
    [(0x4dc38, {0x7a: (4, v)}, {}) for v in (0, 0x288c)] +
    [(0x4dc58, {}, dict(d0=v)) for v in (0x7f, 0x80)] +
    [(0xe66fa, {0x7c: (2, v)}, {}) for v in (0, 1)] +
    [(0xe6702, {0x7a: (2, v)}, {}) for v in (0, 1, 0xffff)] +
    [(0xe673e, {0x76: (2, v)}, {}) for v in (1, 2, 0)] +
    [(0xe6916, {0x12: (1, v)}, {}) for v in (0xef, 0xf0)] +
    [(0xe682e, {}, dict(d7=v)) for v in (9, 10, 0xffff)] +
    [(0xe6884, {}, dict(d1=v, a1=RECORDS)) for v in (9, 0xffff)] +
    [(0xe678c, {}, dict(d0=v)) for v in (1, 11)] +
    [(0xe6826, {}, dict(d7=v)) for v in (0, 1)] +
    [(0xe68cc, {}, dict(d0=v)) for v in (0, 1)])


def main():
    rng = random.Random(0xb2e7)
    worlds = [make_world(rng) for _ in range(WORLDS)]
    states = [base_state(w) for w in worlds]
    rows, used = [], set()
    unreached = []
    for pc in B.STARTS:
        if pc in B.ERROR_ONLY:
            continue
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
        r0['a0'] = ARGS
        r0['a1'] = ARGS
        r0.update(regs)
        worlds.append(dict(puts=[(NODE + off, size, value) for off, (size, value) in sorted(fields.items())] + [(NODE + 0xc, 4, PARENT)], regs=r0))
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
        lines.append(' {"%s",{%s},0x%x,0x%x},' % (hexput(worlds[w]), ','.join('0x%x' % d['d%d' % k] for k in range(8)), d['a0'], d['a1']))
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
