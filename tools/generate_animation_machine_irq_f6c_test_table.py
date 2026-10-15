"""Generates the native-oracle tables of engine/tests/animation_machine_irq_f6c_test.cpp (between the 'generated tables' markers).

Synthetic world (no ROM data in the repository; the C++ test builds the same world from the row parameters):
  zero work RAM; LONG STOP = 000ff000 at 10f000 + 4i (i = 0..7); A2 = 10c000 (WORD 2 = a2x, BYTE 4 = s4, BYTE 5 = s5,
  LONG 8 = w8 << 16 | bank | i1sel << 3 | i2sel << 11 with i1sel = 3k + 1, i2sel = k + 2, w8 & 7f = 0); A4 = 10c100 (box WORDs 0..6);
  LONG 10c200 + 4 * i2sel = 10b000; frame WORDs at 10b000 (word0 = strips << 8 | 5a, then per strip x, y, cols << 8 | height byte and
  2 * h * cols tile WORDs, h = ((height byte - 1) & 1f) + 1, tiles from a 16-bit LCG salted per strip); registers D0-D7 = 11110000 * (i+1) + i
  with D3 / D5 / D6 / D7 / A3 per row, A0 = a0a0a0a0, A1 = a1a1a1a1, A2 = 10c000, A4 = 10c100, A5 = 108000, A6 = 3c0000 or a RAM
  address, A7 = 10f000; PVC page ff8 = a0, ff9 = 1000, bank base 200000.
  Synthetic typed physical bytes (not ROM data): the first-level LONG 10c200 at the physical bank window offset (PVC bank of
  (bank + 1) << 12) + 4 + 4 * i1sel for every (bank, k) used.
For every row the ORIGINAL code runs natively (Unicorn M68000, observer PvcMachine with the synthetic bytes overlaid on a copy of the
program ROM) and records the end PC, the number of port events and the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank base, PVC ff8 / ff9
and the ordered ports (size BYTE, address and value BE LONGs; a native WORD pair 3c0000 / 3c0002 is one LONG event).
  BLOCKS     every block start (1,240) and Duff entry (256) from a generic world to the first other block start / PC outside F6c.
  SCENARIOS  whole writer calls from a table slot (head, PVC bank select, synthetic frame) to the return LONG STOP: every routine x
             height byte 0..31, clip / scale / MULS / MULU / box / A6 / cols 0 / empty frame / landing index 8, plus the expected checked
             errors (computed targets that land inside the unit, landing index 9); three split PCs per success row from the native trace.
Usage:  .venv/bin/python tools/generate_animation_machine_irq_f6c_test_table.py  (rewrites the generated section in place)
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import verify_animation_machine_unit_fixtures as U          # noqa: E402
import check_animation_irq_f6c_template as T                # noqa: E402
from address_map import pvc_bank_update                     # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_irq_f6c_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
STOP, SP, A2, A4, A5, FRAME, TABLE2 = 0xff000, 0x10f000, 0x10c000, 0x10c100, 0x108000, 0x10b000, 0x10c200
ERR = 'unsupported animation irq f6c PC'
M64 = (1 << 64) - 1
FAMILY = (('A', 0xf226, 0x11792, True), ('B', 0x13b46, 0x16092, False))
ROLES = {}
for _n, _t, _e, _f in FAMILY:
    _r = T.routines(_t) + [_e]
    ROLES[_n] = [T.roles(_r[k], _r[k + 1], _f) for k in range(8)]
STARTS, DUFF = set(), set()
for _n, _t, _e, _f in FAMILY:
    _s, _d = T.starts_of(_t, ROLES[_n])
    STARTS |= set(_s)
    DUFF |= set(_d)
EDGE = STARTS | DUFF


def in_f6c(pc):
    return 0xf226 <= pc < 0x11792 or 0x13b46 <= pc < 0x16092


def tiles(n, salt):
    out, x = [], (0x9e37 * (salt + 1)) & 0xffff
    for _ in range(n):
        x = (x * 0x6255 + 0x3619) & 0xffff
        out.append(x)
    return out


def frame_words(strips, salt):
    words = [(len(strips) << 8) | 0x5a]
    for i, (x, y, cols, hb) in enumerate(strips):
        words += [x & 0xffff, y & 0xffff, ((cols & 0xff) << 8) | (hb & 0xff)]
        words += tiles(2 * (((hb - 1) & 0x1f) + 1) * cols, salt * 64 + i)
    return words


def bank_base_after(bank):
    _, ff8, ff9 = pvc_bank_update(0xa0, (bank + 1) << 12)
    base, _, _ = pvc_bank_update(0, ff9)
    return base


def row(name, fam, k, pc, bank=0, a2x=0x40, s4=0x3f, s5=0x7f, w8=0x1280, box=None, a6=0x3c0000, strips=((0x10, 0x20, 2, 6),), salt=0,
        d3=None, d5=None, d6=None, d7=None, a3=0xa3a3a3a3, error=None):
    fwd = fam == 'A'
    if box is None:
        box = (0, 0x17f, 1, 0) if fwd else (0, 0, 0x180, 0x17f)
    base = [(0x11110000 * (i + 1) + i) & 0xffffffff for i in range(8)]
    return dict(name=name, fam=fam, k=k, pc=pc, bank=bank, a2x=a2x, s4=s4, s5=s5, w8=w8, box=tuple(box), a6=a6, strips=list(strips), salt=salt,
                d3=base[3] if d3 is None else d3, d5=base[5] if d5 is None else d5, d6=base[6] if d6 is None else d6,
                d7=base[7] if d7 is None else d7, a3=a3, error=error)


def i_sel(k):
    return (3 * k + 1) & 0x7f, (k + 2) & 0x1f


def world(r):
    ram = bytearray(65536)
    for i in range(8):
        ram[(SP & 0xffff) + 4 * i:(SP & 0xffff) + 4 * i + 4] = STOP.to_bytes(4, 'big')

    def put(a, n, v):
        ram[a & 0xffff:(a & 0xffff) + n] = (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'big')
    i1, i2 = i_sel(r['k'])
    assert r['w8'] & 0x7f == 0 and r['bank'] < 6
    put(A2 + 2, 2, r['a2x'])
    put(A2 + 4, 1, r['s4'])
    put(A2 + 5, 1, r['s5'])
    put(A2 + 8, 4, (r['w8'] << 16) | r['bank'] | (i1 << 3) | (i2 << 11))
    for i, v in enumerate(r['box']):
        put(A4 + 2 * i, 2, v)
    put(TABLE2 + 4 * i2, 4, FRAME)
    for i, w in enumerate(frame_words(r['strips'], r['salt'])):
        put(FRAME + 2 * i, 2, w)
    regs = dict(('d%d' % i, (0x11110000 * (i + 1) + i) & 0xffffffff) for i in range(8))
    regs.update(d3=r['d3'], d5=r['d5'], d6=r['d6'], d7=r['d7'], a0=0xa0a0a0a0, a1=0xa1a1a1a1, a2=A2, a3=r['a3'], a4=A4, a5=A5, a6=r['a6'], a7=SP)
    return bytes(ram), regs


PROGRAMS = {}


def program_for(rows):
    """Program ROM copy with every synthetic first-level LONG the rows can read (one copy for the whole table)."""
    key = 'all'
    if key not in PROGRAMS:
        nat = U.native()
        data = bytearray(nat.program)
        syn = {}
        for r in rows:
            i1, _ = i_sel(r['k'])
            phys = bank_base_after(r['bank']) + 4 + 4 * i1
            syn[phys] = TABLE2.to_bytes(4, 'big')
        for phys, b in syn.items():
            data[phys:phys + 4] = b
        PROGRAMS[key] = (bytes(data), sorted(syn.items()))
    return PROGRAMS[key]


def native_ports(m):
    out, ports = [], [(a, n, v) for _, a, n, v in m.ports]
    i = 0
    while i < len(ports):
        a, n, v = ports[i]
        if a == 0x3c0000 and n == 2 and i + 1 < len(ports) and ports[i + 1][:2] == (0x3c0002, 2):
            out.append((0x3c0000, 4, (v << 16) | ports[i + 1][2]))
            i += 2
            continue
        out.append((a, n, v))
        i += 1
    return out


def run_native(r, program, stop=None):
    """-> dict(pc, digest, ports, trace) of the original code from r['pc'] to stop (None: the first other block start / PC outside F6c)."""
    import unicorn
    nat = U.native()
    ram, regs = world(r)
    snap = dict(ram=ram, regs=regs, pc=r['pc'], bank=(0x200000, 0xa0, 0x1000))
    m = nat.PB.PvcMachine(program, nat.fixed, snap)
    m.install_basic_hooks()
    c = m.cpu
    page = bytearray(8192)
    page[0x1ff0:0x1ff4] = (0xa0).to_bytes(2, 'big') + (0x1000).to_bytes(2, 'big')
    c.mem_write(U.PVC_LO, bytes(page))
    seen = dict(stop=None, steps=0, trace=[])

    def code(uc, at, size, user):
        if stop is not None:
            if at == stop:
                seen['stop'] = at
                uc.emu_stop()
                return
            if at in EDGE:
                seen['trace'].append(at)
        elif seen['steps'] > 0 and (at in EDGE or not in_f6c(at)):
            seen['stop'] = at
            uc.emu_stop()
            return
        seen['steps'] += 1
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    try:
        c.emu_start(r['pc'], 0xffffff, count=400000)
    except unicorn.UcError as e:
        raise AssertionError((r['name'], str(e)))
    assert seen['stop'] is not None and m.odd is None and m.invalid is None and m.intr is None and not m.dev_reads, (r['name'], m.odd, m.invalid, m.intr)
    regs = m.regs()
    ports = native_ports(m)
    h = 1469598103934665603
    for b in m.ram():
        h = ((h ^ b) * 1099511628211) & M64
    tail = bytearray()
    for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7'):
        tail += (regs[k] & 0xffffffff).to_bytes(4, 'big')
    tail += seen['stop'].to_bytes(4, 'big') + m.bank.to_bytes(4, 'big') + (m.ff8 & 0xffff).to_bytes(2, 'big') + (m.ff9 & 0xffff).to_bytes(2, 'big')
    for a, n, v in ports:
        tail += bytes([n]) + a.to_bytes(4, 'big') + v.to_bytes(4, 'big')
    for b in tail:
        h = ((h ^ b) * 1099511628211) & M64
    return dict(pc=seen['stop'], digest=h, ports=len(ports), trace=seen['trace'])


def scenarios():
    out = []
    for fam, table, end, fwd in FAMILY:
        for k in range(8):
            R = ROLES[fam][k]
            tag = '%s%d' % (fam, k)
            slot = table + 4 * k
            bank = k % 6
            hx = 0xffe0 if k & 1 else 0x10
            for hb in range(32):
                out.append(row('%s-height%02d' % (tag, hb), fam, k, slot, bank, s5=(0x7f + 37 * hb) & 0xff, strips=[(hx, 0x20, 2, hb)], salt=hb))
            out.append(row('%s-strips' % tag, fam, k, slot, bank, strips=[(0x08, 0x30, 3, 5), (0x30, 0x10, 3, 0x21), (0x50, 0x7f, 1, 0x1f), (0x3f0, 0, 4, 0)], salt=99))
            for x in (0x3f0, 0x130, 0x200, 0x3e0):
                out.append(row('%s-clip-x%x' % (tag, x), fam, k, slot, bank, a2x=0, s4=0xff, s5=0x3f, strips=[(x, 0x10, 6, 3)]))
            for s4 in (0, 0x10, 0xff):
                out.append(row('%s-scale4-%02x' % (tag, s4), fam, k, slot, bank, a2x=0x100, s4=s4, s5=0x40, strips=[(0x20, 0x18, 7, 2)]))
            for s5, y, hb in ((0, 0x10, 3), (0xff, 0x7fff, 0xff), (0x7f, 0x8000, 0x80), (0xff, 0x8000, 0), (0x80, 1, 0x41), (0, 0x10, 1), (0xfe, 0x20, 0xff),
                              (0x02, 0x20, 0x55)):
                out.append(row('%s-mul-%02x-%04x-%02x' % (tag, s5, y, hb), fam, k, slot, bank, a2x=0x20, s4=0x40, s5=s5, w8=0xab80, strips=[(0x18, y, 2, hb)]))
            boxes = ((0, 3, 1, 0), (0, 0x17f, 1, 3), (0, 0x8001, 0x7fff, 0), (0, 0x7fff, 0x8000, 0)) if fwd else \
                ((0x7c, 0, 0x180, 0x7f), (0, 0, 0x7d, 0x7f), (0x8001, 0, 0x180, 0x7fff), (0x7fff, 0, 0x180, 0x8000))
            for i, bx in enumerate(boxes):
                out.append(row('%s-box%d' % (tag, i), fam, k, slot, bank, box=bx, strips=[(0x10, 0x20, 5, 4), (0x30, 0x40, 3, 0x1e)]))
            out.append(row('%s-a6-ram' % tag, fam, k, slot, bank, a6=0x10a100, strips=[(0x10, 0x20, 2, 6)]))
            out.append(row('%s-cols0' % tag, fam, k, slot, bank, strips=[(0x10, 0x20, 2, 6), (0x10, 0x20, 0, 6)]))
            out.append(row('%s-empty' % tag, fam, k, slot, bank, strips=[]))
            # computed targets entered at the column block: D7.B = 40 (cell 0; S: the Duff target is past the run) / 41 (interior)
            col = dict(d5=0x100, d6=0x10, a3=FRAME + 8)
            if R['duff']:
                out.append(row('%s-column-d7-40' % tag, fam, k, R['column'], bank, d7=0x40, error=ERR, **col))
            else:
                out.append(row('%s-column-d7-40' % tag, fam, k, R['column'], bank, d7=0x40, **col))
            out.append(row('%s-column-d7-41' % tag, fam, k, R['column'], bank, d7=0x41, error=ERR, **col))
        out.append(row('%s-land-index8' % fam, fam, 0, table + 32, 0))
        out.append(row('%s-land-index9' % fam, fam, 0, table + 36, 0, error=ERR))
    return out


def blocks():
    out = []
    for fam, table, end, fwd in FAMILY:
        for pc in sorted(p for p in EDGE if table <= p < end):
            k = 0
            for i, R in enumerate(ROLES[fam]):
                if R['head'] <= pc < R['end']:
                    k = i
            out.append(row('block-%x' % pc, fam, k, pc, k % 6, strips=[(0x10, 0x20, 3, 6), (0x30, 0x40, 2, 0x1f)], d3=0x00120300, d5=0x100,
                           d6=0x00450005, d7=0x01020306, a3=FRAME + 8))
    return out


def splits(trace):
    firsts, seen = [], set()
    for i, pc in enumerate(trace):
        if pc not in seen:
            seen.add(pc)
            firsts.append((i, pc))
    if len(firsts) < 4:
        return (0, 0, 0)
    n = len(firsts)
    return tuple(firsts[n * q // 4][1] for q in (1, 2, 3))


def main():
    sc = scenarios()
    bl = blocks()
    program, syn = program_for(sc + bl)
    lines = [BEGIN]
    lines.append('const Synthetic SYNTHETIC[]={')
    for phys, b in syn:
        lines.append(' {0x%x,0x%s},' % (phys, b.hex()))
    lines.append('};')
    lines.append('const std::uint32_t ROLES[2][8][18]={')
    for fam, _, _, _ in FAMILY:
        lines.append(' {')
        for R in ROLES[fam]:
            lines.append('  {%s},' % ','.join('0x%x' % R[n] for n in T.ROLE_NAMES))
        lines.append(' },')
    lines.append('};')
    lines.append('const Row BLOCKS[]={')
    for r in bl:
        res = run_native(r, program)
        lines.append(' {0x%x,0x%x,%d,0x%xULL},' % (r['pc'], res['pc'], res['ports'], res['digest']))
    lines.append('};')
    lines.append('const Scenario SCENARIOS[]={')
    count = dict(ok=0, error=0)
    for r in sc:
        if r['error']:
            res = dict(pc=0, ports=0, digest=0, trace=[])
            count['error'] += 1
        else:
            res = run_native(r, program, STOP)
            count['ok'] += 1
        sp = splits(res['trace'])
        st = r['strips'] + [(0, 0, 0, 0)] * (4 - len(r['strips']))
        lines.append(' {"%s",%d,%d,0x%x,%d,0x%x,0x%x,0x%x,0x%x,{0x%x,0x%x,0x%x,0x%x},0x%x,%d,{%s},%d,0x%x,0x%x,0x%x,0x%x,0x%x,%s,0x%x,%d,0x%xULL,{0x%x,0x%x,0x%x}},'
                     % (r['name'], 0 if r['fam'] == 'A' else 1, r['k'], r['pc'], r['bank'], r['a2x'], r['s4'], r['s5'], r['w8'], r['box'][0], r['box'][1],
                        r['box'][2], r['box'][3], r['a6'], len(r['strips']), ','.join('{0x%x,0x%x,0x%x,0x%x}' % s for s in st), r['salt'], r['d3'], r['d5'],
                        r['d6'], r['d7'], r['a3'], ('"%s"' % r['error']) if r['error'] else 'NULL', res['pc'], res['ports'], res['digest'], sp[0], sp[1], sp[2]))
    lines.append('};')
    lines.append(END)
    text = TEST.read_text()
    i, j = text.index(BEGIN), text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(lines) + text[j:])
    print('synthetic', len(syn), 'blocks', len(bl), 'scenarios', count)


if __name__ == '__main__':
    main()
