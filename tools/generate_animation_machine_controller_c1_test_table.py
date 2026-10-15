"""Generates the native-oracle tables of engine/tests/animation_machine_controller_c1_test.cpp (between the 'generated tables' markers).

Synthetic world (no ROM data in the repository): zero work RAM, return LONG 000ff000 at A7 = 10f000, controller node A6 = 1008e4, A5 = 108000, seeded BYTE / WORD / LONG
edits of the node and the BIOS / credit bytes, seeded D0-D7 and A0 / A1.  The only fixed-ROM data the 116 blocks read are the digit glyph table 370c.. (BYTE (A0,D2.W)) and the
credit text pointer table c48c.. (LONG (PC,D7.W)): synthetic tables overlay 370c..3760 and c48c..c49c on both sides (native Unicorn fixed ROM copy, C++ physical resource); a
world whose original run reads any other fixed-ROM byte is dropped.  For every block start and every world the ORIGINAL code runs natively (Unicorn M68000, never the C++)
from the block start to the first PC that is another block start or outside the 12 ranges; one row per distinct successor (consumers: per incoming C, native SR C = 0 / 1)
records the successor, the native C at the stop and the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, reads, status.  Non-consumer blocks are also checked here to be
independent of the incoming C.  The Z consumers 4a9d0 / 4a9da use worlds whose flag byte is non-zero (native SR.Z = 0 at entry); the zero side is a key fact of the test.
Also emits the 512 SBCD results of ca06 (BYTE 7a(A6) x X) and the FLOW / producer classification.
Usage:  .venv/bin/python tools/generate_animation_machine_controller_c1_test_table.py  (rewrites the generated section in place)
"""
import ctypes
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'unit_fixture_specs'))
import c1 as B                                    # noqa: E402  (block lists, ranges, consumers, pools)
import verify_animation_machine_unit_fixtures as U  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_controller_c1_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
STOP, SP, NODE, A5 = 0xff000, 0x10f000, 0x1008e4, 0x108000
GLYPH_LO, GLYPH_HI = 0x370c, 0x3760
TEXT_LO, TEXT_HI = 0xc48c, 0xc49c
OVERLAYS = ((GLYPH_LO, GLYPH_HI), (TEXT_LO, TEXT_HI))
WORLDS = 90
M64 = (1 << 64) - 1
RAM_A0 = (0x100100, 0x100101, 0x10c800, 0x10fe00, 0x10fdb0, 0x100004, 0x108000, 0x1008e4)
RAM_A1 = (0x3650, 0x3650, 0x3650, 0x100004, 0x10fe00, 0x10fdb0, 0x10c400, 0x100100, 0x100005)
D2_SMALL = (0, 1, 2, 9, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x11111100, 0x11110010, 0x11110011)
D7_SMALL = (0, 1, 2, 3, 0x4000, 0x4001, 0x10002, 0xffff0003, 0x20000)
SBCD_LOW = (7, 8)


def glyph_bytes():
    return bytes(((i * 0x23 + 0x45) & 0xff) for i in range(GLYPH_HI - GLYPH_LO))


def text_bytes():
    out = bytearray()
    for i in range((TEXT_HI - TEXT_LO) // 4):
        out += (0x100100 + 0x10 * i).to_bytes(4, 'big')
    return bytes(out)


def make_world(rng):
    regs = {}
    for k in range(8):
        regs['d%d' % k] = rng.choice(B.REG_VALUES) if rng.random() < 0.6 else rng.getrandbits(32)
    regs['d2'] = rng.choice(D2_SMALL)
    regs['d3'] = rng.choice(B.D3_POOL)
    regs['d4'] = rng.choice(B.D4_POOL)
    regs['d7'] = rng.choice(D7_SMALL)
    regs['a0'] = rng.choice(RAM_A0)
    regs['a1'] = rng.choice(RAM_A1)
    puts = []
    for addr, vals in B.BYTE_POOL.items():
        if rng.random() < 0.6:
            puts.append((addr, 1, rng.choice(vals) if rng.random() < 0.9 else rng.getrandbits(8)))
    for addr, vals in B.WORD_POOL.items():
        if rng.random() < 0.6:
            puts.append((addr, 2, rng.choice(vals) if rng.random() < 0.9 else rng.getrandbits(16)))
    for addr, vals in B.LONG_POOL.items():
        if rng.random() < 0.7:
            puts.append((addr, 4, rng.choice(vals)))
    if rng.random() < 0.06:
        puts.append((0x10fd82, 1, 1))
        puts.append((0x10fe80, 1, 1))
    return dict(puts=puts, regs=regs)


def base_state(world):
    ram = bytearray(65536)
    ram[SP & 0xffff:(SP & 0xffff) + 4] = STOP.to_bytes(4, 'big')
    for addr, size, value in world['puts']:
        ram[addr & 0xffff:(addr & 0xffff) + size] = value.to_bytes(size, 'big')
    regs = dict(a2=0x10c300, a3=0x10c200, a4=0x10c100, a5=A5, a6=NODE, a7=SP)
    regs.update(world['regs'])
    page = bytearray(8192)
    page[0x1ff0:0x1ff4] = (0xa0).to_bytes(2, 'big') + (0x1000).to_bytes(2, 'big')
    return dict(ram=bytes(ram), regs=regs, bank=(0x200000, 0xa0, 0x1000), pvc=bytes(page))


NATIVE_FIXED = []


def fixed_buffer():
    if not NATIVE_FIXED:
        data = bytearray(bytes(U.native().fixed))
        data[GLYPH_LO:GLYPH_HI] = glyph_bytes()
        data[TEXT_LO:TEXT_HI] = text_bytes()
        NATIVE_FIXED.append((ctypes.c_ubyte * 0x100000).from_buffer_copy(bytes(data)))
    return NATIVE_FIXED[0]


def pointer_world(pc, world, rng):
    """Declared stack content of the blocks that pop their own pushes, and the non-zero flag byte of the Z consumers (a copy of the world)."""
    w = dict(puts=list(world['puts']), regs=dict(world['regs']))
    if pc in (0x36b2, 0x36fc, 0x4a8e6):
        w['puts'].append((SP, 4, rng.choice((0x100100, 0x100101, 0x10c800))))
    elif pc == 0x4a8c2:
        w['puts'] += [(SP, 4, rng.choice((0x100004, 0x10fe00, 0x100100))), (SP + 4, 2, rng.choice((0, 1, 0x1234)))]
    elif pc == 0x4a992:
        w['puts'].append((SP, 2, rng.choice((0, 1, 0x1234))))
    elif pc == 0xc526:
        w['puts'].append((SP - 2, 1, rng.choice((0, 1, 0xff))))
        w['regs']['a7'] = SP - 2
    elif pc in B.Z_CONSUMERS:
        a0 = rng.choice(B.Z_BYTES)
        w['regs']['a0'] = a0
        w['puts'].append((a0, 1, rng.choice((1, 2, 0x99, 0xff))))
    return w


def run_native(state, pc, carry):
    """-> (next_pc, ram, regs, c) of the original code from the block start `pc` (SR.C = 1 when carry == 2) to the first other block start / PC outside the 12 ranges."""
    import unicorn
    nat = U.native()
    snap = dict(ram=state['ram'], regs=state['regs'], pc=pc, bank=state['bank'])
    m = nat.PB.PvcMachine(nat.program, fixed_buffer(), snap)
    m.install_basic_hooks()
    c = m.cpu
    c.mem_write(U.PVC_LO, state['pvc'])
    if carry == 2:
        c.reg_write(nat.S.UC_REG['sr'], 0x2001)
    seen = dict(stop=None, steps=0, bad=False)

    def code(uc, at, size, user):
        if seen['steps'] > 0 and B.edge_rule(at):
            seen['stop'] = at
            uc.emu_stop()
            return
        seen['steps'] += 1

    def rom_read(uc, access, address, size, value, user):
        if not any(lo <= address and address + size <= hi for lo, hi in OVERLAYS):
            seen['bad'] = True
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    c.hook_add(unicorn.UC_HOOK_MEM_READ, rom_read, begin=0, end=0xfffff)
    m.fetch_unmapped = None
    try:
        c.emu_start(pc, 0xffffff, count=4000)
    except unicorn.UcError:
        pass
    if seen['stop'] is None and m.fetch_unmapped is not None and B.edge_rule(m.fetch_unmapped):
        seen['stop'] = m.fetch_unmapped
    if seen['stop'] is None or seen['bad'] or m.odd is not None or m.invalid is not None or m.intr is not None or m.ports or m.dev_reads:
        return None
    sr = c.reg_read(nat.S.UC_REG['sr'])
    return seen['stop'], m.ram(), m.regs(), sr & 1


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
    return ','.join('%x:%s' % (addr, value.to_bytes(size, 'big').hex()) for addr, size, value in world['puts'])


def sbcd_table():
    """(result byte, C) of SBCD.B D2,D1 with D2 = 0 for BYTE 7a(A6) x X, from the native 68000 (ca0c..ca10: SUBQ.B #8,D0; SBCD.B D2,D1; BCC.W)."""
    import unicorn
    nat = U.native()
    out = []
    base = dict(ram=bytes(65536), regs=dict(d0=0, d1=0, d2=0, d3=0, d4=0, d5=0, d6=0, d7=0, a0=0, a1=0, a2=0, a3=0, a4=0, a5=A5, a6=NODE, a7=SP), bank=(0x200000, 0xa0, 0x1000))
    for low in SBCD_LOW:
        for value in range(256):
            regs = dict(base['regs'])
            regs['d0'] = low
            regs['d1'] = value
            snap = dict(ram=base['ram'], regs=regs, pc=0xca0c, bank=base['bank'])
            m = nat.PB.PvcMachine(nat.program, nat.fixed, snap)
            m.install_basic_hooks()
            c = m.cpu

            def code(uc, at, size, user):
                if at == 0xca10:
                    uc.emu_stop()
            c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
            c.emu_start(0xca0c, 0xffffff, count=10)
            sr = c.reg_read(nat.S.UC_REG['sr'])
            out.append((m.regs()['d1'] & 255, sr & 1))
    return out


def flow_blocks():
    """The FLOW starts (C kept by the dispatcher): every instruction of the block is JSR / JMP / BSR / BRA / RTS / LEA / MOVEA / ADDQ.W #n,An / ADDA / BTST / BSET / Bcc (from the ROM)."""
    import capstone
    nat = U.native()
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    md.detail = True
    ok = set(['jsr', 'jmp', 'bsr', 'bra', 'rts', 'lea', 'movea', 'btst', 'bset', 'bcc', 'bcs', 'beq', 'bne', 'adda'])
    flow = []
    for lo, hi in B.RANGES:
        starts = sorted(s for s in B.STARTS if lo <= s < hi)
        for k, s in enumerate(starts):
            end = starts[k + 1] if k + 1 < len(starts) else hi
            pc, names = s, []
            while pc < end:
                ins = list(md.disasm(nat.program[pc:pc + 10], pc, 1))[0]
                name = ins.mnemonic.split('.')[0]
                if name == 'addq' and ins.op_str.split(',')[-1].strip().startswith('a'):
                    name = 'adda'                                   # ADDQ to an address register leaves the CCR alone
                names.append(name)
                pc += ins.size
            if all(n in ok for n in names):
                flow.append(s)
    return flow


def main():
    rng = random.Random(0xc1c1a)
    worlds = [make_world(rng) for _ in range(WORLDS)]
    FLOW = frozenset(flow_blocks())
    rows, used = [], set()
    unreached = []
    extra_worlds = []
    for pc in B.STARTS:
        consumer = pc in B.CONSUMERS
        incoming = (1, 2) if consumer else (0,)
        got = 0
        for c in incoming:
            seen = {}
            for wi, w0 in enumerate(worlds):
                w = pointer_world(pc, w0, rng) if pc in (0x36b2, 0x36fc, 0x4a8e6, 0x4a8c2, 0x4a992, 0xc526) + B.Z_CONSUMERS else w0
                st = base_state(w)
                r = run_native(st, pc, c)
                if r is None:
                    continue
                nxt, ram, regs, cout = r
                if consumer and pc in FLOW:
                    assert cout == (1 if c == 2 else 0), (hex(pc), wi, c, cout)
                if not consumer and wi < 8:
                    for other in (1, 2):                         # the incoming C never matters for a non-consumer block
                        r2 = run_native(st, pc, other)
                        assert r2 is not None and r2[0] == nxt and r2[1] == ram and r2[2] == regs, (hex(pc), wi, other)
                        if pc in FLOW:                           # a FLOW block keeps the native C (SR.C = 0 stays 0, SR.C = 1 stays 1)
                            assert cout == 0 and r2[3] == (1 if other == 2 else 0), (hex(pc), wi, other, cout, r2[3])
                if nxt in seen:
                    continue
                seen[nxt] = True
                regs['pc'] = nxt
                if w is not w0:
                    extra_worlds.append(w)
                    wid = len(worlds) + len(extra_worlds) - 1
                else:
                    wid = wi
                rows.append(dict(pc=pc, world=wid, c=c, next=nxt, cout=cout, digest=digest(ram, regs, nxt)))
                used.add(wid)
                got += 1
        if got == 0:
            unreached.append(pc)
    assert not unreached, [hex(p) for p in unreached]
    allworlds = worlds + extra_worlds
    remap = {w: i for i, w in enumerate(sorted(used))}
    lines = [BEGIN, 'const World WORLDS[]={']
    for w in sorted(used):
        d = base_state(allworlds[w])['regs']
        lines.append(' {"%s",{%s},{%s}},' % (hexput(allworlds[w]), ','.join('0x%x' % d['d%d' % k] for k in range(8)),
                                              ','.join('0x%x' % d['a%d' % k] for k in range(8))))
    lines.append('};')
    lines.append('const Row ROWS[]={')
    for r in rows:
        lines.append(' {0x%x,%d,%d,0x%x,%d,0x%xULL},' % (r['pc'], remap[r['world']], r['c'], r['next'], r['cout'], r['digest']))
    lines.append('};')
    lines.append('const Synthetic SYNTHETIC[]={')
    lines.append(' {0x%x,"%s"},' % (GLYPH_LO, glyph_bytes().hex()))
    lines.append(' {0x%x,"%s"},' % (TEXT_LO, text_bytes().hex()))
    lines.append('};')
    flow = flow_blocks()
    lines.append('const std::uint32_t FLOW[]={' + ','.join('0x%x' % x for x in flow) + '};')
    lines.append('const std::uint32_t STARTS[]={' + ','.join('0x%x' % x for x in B.STARTS) + '};')
    table = sbcd_table()
    lines.append('// SBCD.B D2,D1 (D2 = 0) after SUBQ.B #8,D0: [X][BYTE] -> result << 1 | C, X = 1 (D0.B = 7) then X = 0 (D0.B = 8).')
    lines.append('const unsigned short SBCD[512]={' + ','.join('0x%x' % ((v << 1) | cflag) for v, cflag in table) + '};')
    lines.append(END)
    text = TEST.read_text()
    i, j = text.index(BEGIN), text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(lines) + text[j:])
    print('worlds', len(used), 'rows', len(rows), 'flow', len(flow))


if __name__ == '__main__':
    main()
