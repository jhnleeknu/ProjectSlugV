"""Generates the native-oracle tables of engine/tests/animation_machine_objects_u06b_test.cpp (between the 'generated tables' markers) and
prints the three U06 re-targeted rows (native digests) for engine/tests/animation_machine_objects_u06_test.cpp.

Synthetic world (no ROM data in the repository): zero work RAM, return LONG 000ff000 at A7 = 10f000, node A6 = 10e000, A5 = 108000, seeded D0-D7 / A0-A7 and
"address:bytes" items.  The code of the three U06b block starts (e7562 e756c 48250) and of the BSR call sites e7462 e7478 e7486 (U06) is the ORIGINAL code: it runs
natively (Unicorn M68000, never the C++; shared PvcMachine of tools/observe_animation_machine_pvc_banks.py, write-protected ROM, stack in work RAM) from the entry to the
stop PC.  U06b reads no ROM data: any native ROM / banked data read, port write, odd access, undeclared fetch or interrupt drops the row (this script raises).  The U06
re-targeted rows overlay the same synthetic typed bytes as the U06 test (SYN_* strings parsed from that file) and every data read has to stay inside them.
Each row records the stop state (16 registers, FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, PVC words ff8/ff9, ordered port writes) and the contract carry tag:
the incoming C when no executed block is e7562 / 48250 (the only non FLOW_ONLY starts of U06b; e756c, e7462 e7478 e7486 are FLOW_ONLY), else Unknown.
Usage:  .venv/bin/python tools/generate_animation_machine_objects_u06b_test_table.py  (rewrites the generated section in place and prints the U06 rows)
"""
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import verify_animation_machine_unit_fixtures as U  # noqa: E402

TEST = ROOT / 'engine/tests/animation_machine_objects_u06b_test.cpp'
U06_TEST = ROOT / 'engine/tests/animation_machine_objects_u06_test.cpp'
BEGIN, END = '// ---- generated tables (begin)', '// ---- generated tables (end)'
STOP, SP, NODE, A5 = 0xff000, 0x10f000, 0x10e000, 0x108000
M64 = (1 << 64) - 1
KEYS = U.KEYS
STARTS = (0xe7562, 0xe756c, 0x48250)
NON_FLOW = (0xe7562, 0x48250)            # contract: e756c (MOVEA.L (A7)+,A0; RTS) is the only carry-preserving start
SITES = (0xe7462, 0xe7478, 0xe7486)      # U06 BSR e7562 call sites (FLOW_ONLY in U06)
TRACKED = set(STARTS) | set(SITES)
BASE_REGS = [0x11110000, 0x22220001, 0x33330002, 0x44440003, 0x55550004, 0x66660005, 0x77770006, 0x88880007,
             0x10e400, 0x10e600, 0xa2a2a2a2, 0xa3a3a3a3, 0xa4a4a4a4, A5, NODE, SP]
GENERIC_PUTS = '10d681:5a,10f004:000ff004'
GENERIC_REGS = [0x11110000, 0x22220001, 0x33330002, 0x44440003, 0x55550004, 0x66660005, 0x77770006, 0x88880007,
                0x10e400, 0x10e600, 0xa2a2a2a2, 0xa3a3a3a3, 0xa4a4a4a4, A5, NODE, SP]


def regs_of(**kw):
    r = list(BASE_REGS)
    for k, v in kw.items():
        r[KEYS.index(k)] = v & 0xffffffff
    return r


def parse_puts(text):
    out = []
    for item in text.split(',') if text else []:
        a, b = item.split(':')
        out.append((int(a, 16), bytes.fromhex(b)))
    return out


def build_ram(puts):
    ram = bytearray(65536)
    ram[SP & 0xffff:(SP & 0xffff) + 4] = STOP.to_bytes(4, 'big')
    for a, b in parse_puts(puts):
        for i, v in enumerate(b):
            ram[(a + i) & 0xffff] = v
    return ram


def native_run(entry, stop, carry, regs, puts, windows=(), overlay=()):
    """-> dict(regs, ram, pc, tags) of the original code from entry to the first fetch of stop.  windows: allowed (lo, hi) ROM data reads."""
    import unicorn
    nat = U.native()
    PB, S = nat.PB, nat.S
    program = bytearray(nat.program)
    fixed = bytearray(bytes(nat.fixed))
    for a, b in overlay:
        if a < 0x100000:
            fixed[a:a + len(b)] = b
        program[a:a + len(b)] = b
    import ctypes
    fixed_buf = (ctypes.c_ubyte * 0x100000).from_buffer_copy(bytes(fixed))
    snap = dict(ram=bytes(build_ram(puts)), regs={k: regs[i] & 0xffffffff for i, k in enumerate(KEYS)}, pc=entry, bank=(0x200000, 0xa0, 0x1000))
    m = PB.PvcMachine(bytes(program), fixed_buf, snap)
    m.install_basic_hooks()
    c = m.cpu
    if carry == 2:
        c.reg_write(S.UC_REG['sr'], 0x2001)
    seen = dict(stop=False, bad=None, executed=[])

    def code(uc, at, size, user):
        if at == stop:
            seen['stop'] = True
            uc.emu_stop()
            return
        if at in TRACKED:
            seen['executed'].append(at)

    def read(uc, access, address, size, value, user):
        if address < 0x100000:
            if not any(lo <= address and address + size <= hi for lo, hi in windows):
                seen['bad'] = ('ROM data read outside the synthetic bytes', hex(address))
                uc.emu_stop()
        elif address >= 0x200000:
            seen['bad'] = ('banked / device read', hex(address))
            uc.emu_stop()
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    c.hook_add(unicorn.UC_HOOK_MEM_READ, read, begin=0, end=0x3fffff)
    try:
        c.emu_start(entry, 0xffffff, count=2000000)
    except unicorn.UcError as e:
        raise RuntimeError('native error %s at %x' % (e, entry))
    if not seen['stop'] or seen['bad'] or m.odd or m.invalid or m.intr or m.ports or m.dev_reads or m.fetch_unmapped is not None:
        raise RuntimeError('native row rejected: %r %r %r %r %r' % (seen, m.odd, m.invalid, m.intr, m.ports))
    r = m.regs()
    return dict(regs=[r[k] & 0xffffffff for k in KEYS], ram=m.ram(), pc=stop, executed=seen['executed'])


def digest(ram, regs, pc):
    h = 1469598103934665603
    for b in ram:
        h = ((h ^ b) * 1099511628211) & M64
    tail = bytearray(b''.join(v.to_bytes(4, 'big') for v in regs))       # D0-D7 then A0-A7
    tail += pc.to_bytes(4, 'big') + (0x200000).to_bytes(4, 'big') + (0xa0).to_bytes(2, 'big') + (0x1000).to_bytes(2, 'big')
    for b in tail:
        h = ((h ^ b) * 1099511628211) & M64
    return h


def tag_of(executed, carry):
    return 0 if any(p in NON_FLOW for p in executed) else carry


def hx(v):
    return '0x%x' % v


def row(name, entry, stop, carry, regs, puts, tail='', **kw):
    n = native_run(entry, stop, carry, regs, puts, **kw)
    out = n['regs']
    return ('{"%s",%s,%s,%d,{%s},"%s",NULL,{%s},%d,0x%016xULL%s},' % (
        name, hx(entry), hx(stop), carry, ','.join(hx(v) for v in regs), puts, ','.join(hx(v) for v in out), tag_of(n['executed'], carry),
        digest(n['ram'], out, stop), tail), n)


def fixtures_rows():
    rows = []
    # (a) e7562 chains: full chain to the return LONG STOP, and partial stops at 48250 and e756c; every scenario with the three incoming C tags.
    scen = [
        ('s1', dict(d0=0x12345678, a0=0x10e400), '10d681:5a'),
        ('s2', dict(d0=0xffffffff, a0=0), '10d681:ff'),
        ('s3', dict(d0=0, a0=0xffffffff), '10d681:00'),
        ('s4', dict(d0=0x80, a0=SP), '10d681:01'),
        ('s5', dict(d0=0xabcdef01, a0=0x10d681, a5=0x10a000), '10f681:77'),
        ('s6', dict(d0=0x000000fe, a0=0x12345679, a5=0x10ffff), '115680:9c'),
        ('s7', dict(d0=0x7fffff7f, a0=0xfffffffe, a5=0x108001), '10d682:3c'),
        ('s8', dict(d0=0x55aa55aa, a0=0x8000, a7=0x10effc), '10effc:000ff000'),
    ]
    for name, kw, puts in scen:
        regs = regs_of(**kw)
        for c in (0, 1, 2):
            rows.append(row('e7562-%s-c%d' % (name, c), 0xe7562, STOP, c, regs, puts)[0])
        if name in ('s1', 's2', 's5'):
            for stop, label in ((0x48250, 'to48250'), (0xe756c, 'toe756c')):
                for c in (0, 2):
                    rows.append(row('e7562-%s-%s-c%d' % (name, label, c), 0xe7562, stop, c, regs, puts)[0])
    # (b) 48250: BYTE 5681(A5) := D0.B for D0.B boundary values with a dirty upper part; other A5 (mirror, odd) and all C tags.
    for label, d0 in (('00', 0x12345600), ('01', 0xffffff01), ('7f', 0x0000007f), ('80', 0x80000080), ('ff', 0x1234ffff)):
        regs = regs_of(d0=d0)
        for c in (0, 1, 2):
            rows.append(row('48250-d0-%s-c%d' % (label, c), 0x48250, STOP, c, regs, '10d681:5a')[0])
    for label, a5, puts in (('a5-10a000', 0x10a000, '10f681:11'), ('a5-10ffff', 0x10ffff, '115680:22'), ('a5-odd', 0x108001, '10d682:33'), ('a5-low', 0x100000, '105681:44'),
                            ('a5-mirror', 0x10fff0, '115671:55')):
        regs = regs_of(d0=0x000000a5, a5=a5)
        for c in (0, 2):
            rows.append(row('48250-%s-c%d' % (label, c), 0x48250, STOP, c, regs, puts)[0])
    # (c) e756c: MOVEA.L (A7)+,A0; RTS with the popped LONG and the return LONG in the stack.
    for label, a0new in (('0', 0), ('ffffffff', 0xffffffff), ('10e400', 0x10e400), ('odd', 0x12345679)):
        for c in (0, 1, 2):
            rows.append(row('e756c-a0-%s-c%d' % (label, c), 0xe756c, STOP, c, regs_of(d0=0xdeadbeef, a0=0x5a5a5a5a, a7=0x10e800),
                            '10e800:%08x,10e804:000ff000' % a0new)[0])
    # (d) the BSR call sites of the U06 callback e73f8/e7426 into U06b and back (stop at the return PC): e7462 -> e7466, e7478 -> e747c, e7486 -> e748a.
    for entry, back in ((0xe7462, 0xe7466), (0xe7478, 0xe747c), (0xe7486, 0xe748a)):
        for label, kw, puts in (('a', dict(a0=0x10e400), '10d681:5a'), ('b', dict(a0=0, d0=0xffffffff, a7=0x10e800), '10d681:ff,10e800:000ff000')):
            for c in (0, 1, 2):
                rows.append(row('%x-%s-c%d' % (entry, label, c), entry, back, c, regs_of(**kw), puts)[0])
    return rows


def block_rows():
    rows = []
    for pc, nxt in ((0xe7562, 0x48250), (0xe756c, 0xff004), (0x48250, STOP)):
        digs = []
        for c in (0, 2):
            n = native_run(pc, nxt, c, GENERIC_REGS, GENERIC_PUTS)
            digs.append((digest(n['ram'], n['regs'], nxt), n))
        rows.append('{%s,%s,0x%016xULL,%s,0x%016xULL},' % (hx(pc), hx(nxt), digs[0][0], hx(nxt), digs[1][0]))
    return rows


def u06_rows():
    """The three U06 rows (stop e7562, boundaries) re-run through e7562 -> 48250 -> e756c to the return STOP."""
    text = U06_TEST.read_text()
    syn = {}
    for name in ('TEXT', 'SCRIPT', 'SLOT', 'BLIST'):
        syn[name] = bytes.fromhex(re.search(r'SYN_%s="([0-9a-f]*)"' % name, text).group(1))
    overlay = [(0xe7392, syn['TEXT']), (0xe7570, syn['SCRIPT']), (0xe7752, syn['SLOT']), (0xeba9e, syn['BLIST'])]
    windows = [(a, a + len(b)) for a, b in overlay]
    out = []
    for name, extra in (('e742c-clear-key1', ''), ('e7462', ',10e07a:0005'), ('script-end', '')):
        m = re.search(r'\{"%s",(0x[0-9a-f]+),0xe7562,(\d),\{([^}]*)\},"([^"]*)",NULL' % re.escape(name), text)
        entry, carry, regs, puts = int(m.group(1), 16), int(m.group(2)), [int(x, 16) for x in m.group(3).split(',')], m.group(4)
        puts = puts + extra if puts else extra[1:]
        line, n = row(name + '-to-stop', entry, STOP, carry, regs, puts, tail=',0,0x200000', windows=windows, overlay=overlay)
        out.append(line)
        print('U06 %s: executed starts %s, 10d681 = %02x' % (name, [hex(p) for p in n['executed']], n['ram'][0xd681]), file=sys.stderr)
    return out


def main():
    rows = fixtures_rows()
    blocks = block_rows()
    section = ['// ---- generated tables (begin)', 'const Fixture FIXTURES[]={']
    section += [' ' + r for r in rows]
    section += ['};', 'const Block BLOCKS[]={'] + [' ' + r for r in blocks] + ['};']
    section += ['const char* const GENERIC_PUTS="%s";' % GENERIC_PUTS]
    section += ['const std::uint32_t GENERIC_REGS[16]={%s};' % ','.join(hx(v) for v in GENERIC_REGS)]
    section += ['// ---- generated tables (end)']
    text = TEST.read_text()
    i, j = text.index(BEGIN), text.index(END) + len(END)
    TEST.write_text(text[:i] + '\n'.join(section) + text[j:])
    print('fixtures %d, blocks %d' % (len(rows), len(blocks)), file=sys.stderr)
    print('---- U06 rows')
    for r in u06_rows():
        print(' ' + r)


if __name__ == '__main__':
    main()
