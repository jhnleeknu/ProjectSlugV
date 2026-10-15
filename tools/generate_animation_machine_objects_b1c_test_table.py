"""Generates the native-oracle tables of engine/tests/animation_machine_objects_b1c_test.cpp (between the 'generated tables' markers).

Synthetic world (no ROM data in the repository): zero work RAM, return LONG 000ff000 at A7 = 10f000, node A6 = 10e000, A5 = 108000, A0 = 10c800, A1 = 10c400,
seeded BYTE / WORD / LONG field edits of the node and seeded D0-D7.  The only fixed-ROM data the 224 blocks read is the WORD table 4411e (blocks 33434): a synthetic table
T[i] = (i * 0123 + 4567) & ffff overlays 4411e - 400 .. 4411e + 800 on both sides (native Unicorn fixed ROM copy, C++ physical resource).  For every block start and every
world the ORIGINAL code runs natively (Unicorn M68000, never the C++) from the block start to the first PC that is another block start or outside the three routed ranges;
one row per distinct successor (consumers: per incoming C, native SR C = 0 / 1) records the successor and the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, reads, status.
Non-consumer blocks are also checked here to be independent of the incoming C (the table has one row; the test runs all three C tags).
Usage:  .venv/bin/python tools/generate_animation_machine_objects_b1c_test_table.py  (rewrites the generated section in place)
"""
import ctypes
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'unit_fixture_specs'))
import b1c as B                                   # noqa: E402  (block lists, ranges, consumers)
import verify_animation_machine_unit_fixtures as U  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_b1c_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
STOP, SP, NODE, A5, OBJ0, OBJ1 = 0xff000, 0x10f000, 0x10e000, 0x108000, 0x10c800, 0x10c400
FIXED = dict(a0=OBJ0, a1=OBJ1, a2=0x10c300, a3=0x10c200, a4=0x10c100, a5=A5, a6=NODE, a7=SP)
TABLE_BASE, TABLE_LO, TABLE_HI = 0x4411e, 0x4411e - 0x400, 0x4411e + 0x800
WORLDS = 72
BYTES = dict(B.OFFSET_BYTES)
WORDS = dict(B.OFFSET_WORDS)
WORDS[0x86] = (0, 1, 2, 3, 0x7f, 0xff, 0x1ff, 0xffff, 0xfffe, 0xfe01)     # 2 * WORD stays inside the synthetic table overlay
LONGS = dict(B.OFFSET_LONGS)
M64 = (1 << 64) - 1


def table_bytes():
    out = bytearray()
    for i in range((TABLE_HI - TABLE_LO) // 2):
        index = (TABLE_LO - TABLE_BASE) // 2 + i
        out += (((index * 0x123 + 0x4567) & 0xffff)).to_bytes(2, 'big')
    return bytes(out)


def make_world(rng):
    regs = {}
    for k in range(8):
        regs['d%d' % k] = rng.choice(B.REG_VALUES) if rng.random() < 0.6 else rng.getrandbits(32)
    puts = []
    for off, vals in BYTES.items():
        if rng.random() < 0.55:
            puts.append((NODE + off, 1, rng.choice(vals) if rng.random() < 0.85 else rng.getrandbits(8)))
    for off, vals in WORDS.items():
        if rng.random() < 0.5:
            puts.append((NODE + off, 2, rng.choice(vals) if (rng.random() < 0.85 or off == 0x86) else rng.getrandbits(16)))
    for off, vals in LONGS.items():
        if rng.random() < 0.5:
            puts.append((NODE + off, 4, rng.choice(vals) if rng.random() < 0.85 else rng.getrandbits(32)))
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
    return dict(ram=bytes(ram), regs=regs, bank=(0x200000, 0xa0, 0x1000), pvc=bytes(page))


NATIVE_FIXED = []


def fixed_buffer():
    if not NATIVE_FIXED:
        nat = U.native()
        data = bytearray(bytes(nat.fixed))
        data[TABLE_LO:TABLE_HI] = table_bytes()
        NATIVE_FIXED.append((ctypes.c_ubyte * 0x100000).from_buffer_copy(bytes(data)))
    return NATIVE_FIXED[0]


def run_native(state, pc, carry):
    """-> (next_pc, ram, regs) of the original code from the block start `pc` (SR.C = 1 when carry == 2) to the first other block start / PC outside the routed ranges."""
    import unicorn
    nat = U.native()
    snap = dict(ram=state['ram'], regs=state['regs'], pc=pc, bank=state['bank'])
    m = nat.PB.PvcMachine(nat.program, fixed_buffer(), snap)
    m.install_basic_hooks()
    c = m.cpu
    c.mem_write(U.PVC_LO, state['pvc'])
    if carry == 2:
        c.reg_write(nat.S.UC_REG['sr'], 0x2001)
    seen = dict(stop=None, steps=0)

    def code(uc, at, size, user):
        if seen['steps'] > 0 and B.edge_rule(at):
            seen['stop'] = at
            uc.emu_stop()
            return
        seen['steps'] += 1
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    try:
        c.emu_start(pc, 0xffffff, count=4000)
    except unicorn.UcError:
        return None
    if seen['stop'] is None or m.odd is not None or m.invalid is not None or m.intr is not None or m.ports or m.dev_reads:
        return None
    return seen['stop'], m.ram(), m.regs()


def sext16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def table_target(pc, regs0):
    """For the computed JMP blocks 30b78 / 335f6: the target when it is a PC inside a B1c range that is not a block start (None otherwise)."""
    d0 = regs0['d0']
    target = 0x30b84 + sext16((d0 & 0xff) * 4) if pc == 0x30b78 else 0x335fe + sext16(d0 * 4)
    return target if B.in_ranges(target) and target not in B.STARTSET else None


def digest(ram, regs, pc):
    h = 1469598103934665603
    for b in ram:
        h = ((h ^ b) * 1099511628211) & M64
    tail = bytearray()
    for k in range(8):
        tail += (regs['d%d' % k] & 0xffffffff).to_bytes(4, 'big')
    for k in range(8):
        tail += (regs['a%d' % k] & 0xffffffff).to_bytes(4, 'big')
    tail += pc.to_bytes(4, 'big') + (0x200000).to_bytes(4, 'big') + (0).to_bytes(4, 'big') + bytes([0])
    for b in tail:
        h = ((h ^ b) * 1099511628211) & M64
    return h


def hexput(world):
    out = []
    for addr, size, value in world['puts']:
        out.append('%x:%s' % (addr, value.to_bytes(size, 'big').hex()))
    return ','.join(out)


def flow_blocks():
    """The FLOW_ONLY starts (C kept by the dispatcher): every instruction of the block is JSR / JMP / BRA / LEA / MOVEA / BTST / BEQ / BNE / BCC / BCS (classified from the ROM)."""
    import capstone
    nat = U.native()
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    ok = set(['jsr', 'jmp', 'bra', 'rts', 'lea', 'movea', 'btst', 'bcc', 'bcs', 'beq', 'bne'])
    flow = []
    for lo, hi in B.RANGES:
        starts = [s for s in B.STARTS if lo <= s < hi]
        starts.sort()
        for k, s in enumerate(starts):
            end = starts[k + 1] if k + 1 < len(starts) else hi
            pc, names = s, []
            while pc < end:
                ins = list(md.disasm(nat.program[pc:pc + 10], pc, 1))[0]
                names.append(ins.mnemonic.split('.')[0])
                pc += ins.size
            if all(n in ok for n in names):
                flow.append(s)
    return flow


def main():
    rng = random.Random(0x1b1ca)
    worlds = [make_world(rng) for _ in range(WORLDS)]
    for d0 in (4, 0x104):                                       # CMPI.B #4,D0 (33a20) needs the exact BYTE
        w = make_world(rng)
        w['regs']['d0'] = d0
        worlds.append(w)
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
                if pc in B.TABLE_ENTRIES and table_target(pc, regs0=st['regs']) is not None:
                    continue                                    # the computed PC lands inside a block: a checked error in the C++, tested separately
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
    for pc, fields, regs in B.BOUNDARY_CASES:                    # boundary values of every compare: one forced row each (successor repeats are kept)
        r0 = dict(('d%d' % k, 0) for k in range(8))
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
        lines.append(' {"%s",{%s}},' % (hexput(worlds[w]), ','.join('0x%x' % d['d%d' % k] for k in range(8))))
    lines.append('};')
    lines.append('const Row ROWS[]={')
    for r in rows:
        lines.append(' {0x%x,%d,%d,0x%x,0x%xULL},' % (r['pc'], remap[r['world']], r['c'], r['next'], r['digest']))
    lines.append('};')
    lines.append('const Synthetic SYNTHETIC[]={')
    lines.append(' {0x%x,"%s"},' % (TABLE_LO, table_bytes().hex()))
    lines.append('};')
    flow = flow_blocks()
    lines.append('const std::uint32_t FLOW[]={' + ','.join('0x%x' % x for x in flow) + '};')
    lines.append('const std::uint32_t STARTS[]={' + ','.join('0x%x' % x for x in B.STARTS) + '};')
    lines.append(END)
    text = TEST.read_text()
    i, j = text.index(BEGIN), text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(lines) + text[j:])
    print('worlds', len(used), 'rows', len(rows), 'flow', len(flow))


if __name__ == '__main__':
    main()
