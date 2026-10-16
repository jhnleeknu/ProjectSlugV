"""Native fixture spec of unit C3b (controller post-wait boot c56e..c64c, demo intro c5ce..c608, title c6da..c720 and the demo child allocation 4fb1a..4fb42:
38 block starts of animation_controller_c3_block, beside the 9 C3a starts) for tools/verify_animation_machine_unit_fixtures.py.

Every fixture starts from a NATURAL controller entry state: the D1 native reference (seed_frames) of a natural seed ends its H segment at the controller callback
c52a (A6 = 1008e4, A5 = 108000, return LONG 2ac2 at A7 = 1feffc).  C3b is fixture-only (decision D10): the boot wait WORD 107dea reaches 0 only through the IRQ c8c, so the
declared state is a host write on that natural state, plus PC := the block (or LONG 1008e4 := c560 and 107dea := 0 for the boot chain), BYTE 10fdae (BIOS request),
BYTE 62(A6), WORD 76(A6), WORD 10f02a, BYTE 10fd82 / 100001 (demo child), BYTE 10fdda (title BCD) and the registers.  The C++ run and the native Unicorn run of the original ROM
start from the same declared state and must agree on RAM, D0-D7 / A0-A7, PC, bank, PVC page, ports and external-read bookkeeping at the stop PC.  Stop PCs are native-determined
(`trace()` runs the original code, never the C++); the ROM WORD 000180 is canonical 0, so the c5b4 BNE c610 side is covered by the C++ unit test only.

Groups:
  edge-<pc>-s<case>-<k>   every one of the 38 C3b block starts entered directly in seeded worlds; one fixture per distinct native successor (both sides of every branch a
                          world can reach); the stop is the next unit block start or the first PC outside the unit (callee entry, C1 wait tail c724 / c73e, RTS target 2ac2, BIOS c00444).
  chain-<kind>-<pc>-...   multi-block runs through the real routed callees (e7bf4, ca7e, ca76, 28ae child allocation, caf0, 3902 H2, 36ba / c724 / c73e C1, ...) to the first boundary:
                          the boot after the wait (LONG 1008e4 := c560, 107dea := 0, 10fdae 0/1/2/3/4/ff), the demo intro, the restart, the title, the demo child allocation.
  carry-4fb3c-<kind>      the SCC.B consumer 4fb3c with a real C: 28ae entered with 4fb3c as the pushed return (success C Set -> 62(A6) := 00, failure with WORD 104ca0 := 0 C Clear -> ff).
  error-*                 checked errors with preservation: Unknown C at 4fb3c, every even non-start PC of the four unit ranges, odd PCs, unrouted neighbours.
  negative-*              the C++ input differs by one bit; the comparison must report it.
Boundary stops: 2ac2 c00444 c00450 and every PC without an executor (the C2 callees 49a1a 47570 4823a 3162 c4cc while C2 is not routed).
"""
import importlib.util
import os
import random

import verify_animation_machine_unit_fixtures as U


def load_c1():
    spec = importlib.util.spec_from_file_location('unit_fixture_spec_c1', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c1.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C1 = load_c1()
STARTS = tuple(int(x, 16) for x in (
    'c56e c574 c57c c58a c598 c59e c5a6 c5ac c5b4 c5be c5c2 c5c8 c5ce c5d6 c5da c5ea c5f4 c5fc c608 c610 c61e c622 c626 c62c c642 c64c '
    'c6da c6de c6ee c6f4 c702 c718 c720 4fb1a 4fb22 4fb2c 4fb3c 4fb42').split())
C3A_STARTS = (0xc52a, 0xc530, 0xc55a, 0xc560, 0xc566, 0xc56c, 0x8b64, 0x8b98, 0x8bb6)
assert len(STARTS) == 38 and len(set(STARTS)) == 38
STARTSET = frozenset(STARTS + C3A_STARTS)
RANGES = ((0x8b64, 0x8bbc), (0xc52a, 0xc654), (0xc6da, 0xc724), (0x4fb1a, 0x4fb4a))
BOUNDARY = frozenset([0x2ac2, 0xc00444, 0xc00450])
NODE = 0x1008e4
CASES = (0, 94)
MAX_VARIANTS = 48
hx = C1.hx
trace = C1.trace
routed = C1.routed

BYTE_POOL = {
    0x10fdae: (0, 1, 2, 3, 4, 0x80, 0xff), NODE + 0x62: (0, 1, 0x80, 0xff), 0x10fd82: (0, 1, 2, 0xff), 0x100001: (0, 1, 2, 0xff),
    0x10fdda: (0, 1, 0x12, 0x80, 0xff), 0x10f004: (0, 3, 0xff)}
WORD_POOL = {NODE + 0x76: (0, 1, 2, 0x96, 0x100, 0x8000, 0xffff), 0x10f02a: (0, 1, 2, 3, 0x8001, 0xffff, 0x1234), 0x104ca0: (0, 1, 0x20, 0x100)}
FRAMES = {}


def in_ranges(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def edge_rule(pc):
    return pc in STARTSET or not in_ranges(pc)


def chain_rule(pc):
    return pc in BOUNDARY or not routed(pc)


def seq_chain_rule(pc):
    return pc in BOUNDARY


def entry_state(case, frame):
    """Natural controller entry (PC c52a, A6 1008e4, A5 108000, A7 1feffc with the return LONG 2ac2) of seed `case`, frame `frame`."""
    if case not in FRAMES:
        FRAMES[case] = U.seed_frames(case, 4)
    fr = [f for f in FRAMES[case] if f['frame'] == frame and f.get('h')]
    U.require(fr, ('no controller entry', case, frame))
    return U.seed_state(fr[0]['h']['end'])


def world(rng, state, kinds=None):
    regs = dict(state['regs'])
    for k in range(8):
        regs['d%d' % k] = rng.choice(C1.REG_VALUES) if rng.random() < 0.6 else rng.getrandbits(32)
    regs['d2'] = rng.choice(C1.D2_POOL) if rng.random() < 0.8 else rng.getrandbits(32)
    regs['a0'] = rng.choice(C1.A0_POOL)
    regs['a1'] = rng.choice(C1.A1_POOL)
    writes = []
    for addr, vals in BYTE_POOL.items():
        if rng.random() < 0.7:
            writes.append((addr, 1, rng.choice(vals) if rng.random() < 0.9 else rng.getrandbits(8)))
    for addr, vals in WORD_POOL.items():
        if rng.random() < 0.7:
            writes.append((addr, 2, rng.choice(vals) if rng.random() < 0.9 else rng.getrandbits(16)))
    return writes, regs


def edge_fixtures(rng, pc, case):
    base = entry_state(case, 2)
    out, seen = [], set()
    for v in range(MAX_VARIANTS):
        writes, regs = world(rng, base)
        st = dict(U.with_host_writes(base, writes, regs=regs, pc=pc), carry=0)
        if pc == 0x4fb3c:
            continue                                           # needs a real C: carry-4fb3c fixtures
        r = trace(st, pc, edge_rule)
        if r is None or r['pc'] in seen:
            continue
        seen.add(r['pc'])
        out.append(U.Fixture('edge-%x-s%d-%d' % (pc, case, len(out)), st, [], r['pc'], meta=dict(block=hx(pc), successor=hx(r['pc']), case=case, variant=v)))
    return out


CHAIN_ENTRIES = (('boot', 0xc56e), ('boot', 0xc574), ('boot', 0xc57c), ('boot', 0xc58a), ('demo', 0xc5be), ('demo', 0xc5c2), ('demo', 0xc5c8), ('demo', 0xc5ce),
                 ('demo', 0xc5d6), ('demo', 0xc5ea), ('demo', 0xc5f4), ('demo', 0xc5fc), ('demo', 0xc608), ('restart', 0xc610), ('restart', 0xc62c), ('restart', 0xc64c),
                 ('title', 0xc6da), ('title', 0xc6de), ('title', 0xc6f4), ('title', 0xc702), ('title', 0xc718), ('child', 0x4fb1a), ('child', 0x4fb22), ('child', 0x4fb2c),
                 ('child', 0x4fb42))


def chain_fixtures(rng, case):
    out = []
    base = entry_state(case, 3)
    for kind, entry in CHAIN_ENTRIES:
        seen = set()
        for v in range(40):
            writes, regs = world(rng, base)
            if kind == 'child' or entry in (0xc5be, 0xc5c2):
                writes += [(0x10fd82, 1, rng.choice((0, 1, 1, 1))), (0x100001, 1, rng.choice((0, 1, 1, 2)))]
            if entry in (0xc5be, 0xc5c2, 0xc5c8, 0xc5da, 0xc6de, 0x4fb2c) and rng.random() < 0.3:
                writes.append((0x104ca0, 2, 0))              # 28ae fails (D0.W >= WORD 104ca0): C Clear
            if kind == 'title':
                writes.append((0x10fdda, 1, rng.choice((0, 0, 1, 0x12, 0x99))))
            st = dict(U.with_host_writes(base, writes, regs=regs, pc=entry), carry=0)
            r = trace(st, entry, chain_rule, limit=60000, seq_rule=seq_chain_rule)
            if r is None:
                continue
            key = (r['pc'], tuple(r['visited']))
            if key in seen:
                continue
            seen.add(key)
            out.append(U.Fixture('chain-%s-%x-s%d-%d' % (kind, entry, case, len(seen)), st, [], r['pc'],
                                 meta=dict(kind=kind, entry=hx(entry), stop=hx(r['pc']), blocks=len(r['visited']), case=case, variant=v)))
            if len(seen) >= 6:
                break
    return out


def boot_fixtures(case):
    """The natural boot head state with the wait released (LONG 1008e4 := c560, WORD 107dea := 0) and the BIOS request 10fdae: run to the first boundary.  With request 0 / 1 the
    original continues (through the C2 helpers) to JMP c00444; the stop is native-determined by the routed C++ units."""
    out = []
    for frame in (1, 2):
        base = entry_state(case, frame)
        for req in (0, 1, 2, 3, 4, 0xff):
            st = dict(U.with_host_writes(base, [(NODE, 4, 0xc560), (0x107dea, 2, 0), (0x10fdae, 1, req)], pc=0xc560), carry=0)
            r = trace(st, 0xc560, chain_rule, limit=200000, seq_rule=seq_chain_rule)
            if r is None:
                continue
            out.append(U.Fixture('chain-boot-wait0-req%02x-s%d-f%d' % (req, case, frame), st, [], r['pc'], meta=dict(request=req, stop=hx(r['pc']), case=case, frame=frame)))
    return out


def carry_fixtures(case):
    """4fb3c consumes the C returned by 28ae: 28ae entered with A0 = 4fb64, D0.W = 0 and 4fb3c pushed as the return (the natural 2ac2 below it): success -> C Set, 62(A6) := 00;
    WORD 104ca0 := 0 -> the failure exit 290e, C Clear, 62(A6) := ff.  Both run through SCC.B and the RTS to 2ac2."""
    out = []
    base = entry_state(case, 2)
    a7 = base['regs']['a7'] - 4
    for kind, extra in (('set', []), ('clear', [(0x104ca0, 2, 0)])):
        for k, seed in enumerate((0xa5, 0x00, 0xff)):
            regs = dict(base['regs'])
            regs['a0'] = 0x4fb64
            regs['d0'] = regs['d0'] & 0xffff0000
            regs['a7'] = a7
            st = dict(U.with_host_writes(base, [(a7, 4, 0x4fb3c), (NODE + 0x62, 1, seed)] + extra, regs=regs, pc=0x28ae), carry=0)
            r = trace(st, 0x28ae, chain_rule, after=0x4fb3c, seq_rule=seq_chain_rule)
            if r is None:
                continue
            out.append(U.Fixture('carry-4fb3c-%s-s%d-%d' % (kind, case, k), st, [], r['pc'], meta=dict(kind=kind, stop=hx(r['pc']))))
    return out


def error_fixtures(case):
    out = []
    probe = entry_state(case, 2)
    out.append(U.Fixture('error-unknown-carry-4fb3c', dict(U.with_host_writes(probe, [], pc=0x4fb3c), carry=0), [], 0xffffe,
                         ('error', 'controller c3 caller requires known carry')))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in STARTSET:
                out.append(U.Fixture('error-interior-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation controller c3 PC')))
        for pc in (lo + 1, hi - 1):
            out.append(U.Fixture('error-odd-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unaligned animation machine PC')))
    # PCs without an executor: even work-RAM PCs 10fe10..10fe16 (review 0264 M-3; were the ROM range ends c6ce c6d8 4fb4a 4fb18, code of later units) and the BIOS entry c00444
    for pc in (0x10fe10, 0x10fe12, 0x10fe14, 0x10fe16, 0xc00444):
        U.require(not routed(pc), ('probe is routed', hex(pc)))
        out.append(U.Fixture('error-outside-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation machine PC')))
    # c598 / c5a6 end in JMP c00444: running past the BIOS fetch is the checked unsupported-PC error (no executor) at the BIOS entry c00444 (failing PC asserted), state preserved.
    for pc in (0xc598, 0xc5a6):
        out.append(U.Fixture('error-bios-return-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation machine PC'), fail_pc=0xc00444))
    return out


def negative_fixtures(fixtures):
    out = []
    pool = [f for f in fixtures if f.name.startswith('edge-') and f.expect == 'match']
    for f in pool[:3]:
        st = f.state
        out.append(U.Fixture('negative-ram-' + f.name, st, [], f.stop, 'mismatch', cpp_state=U.flip_ram(st, 0x10fff0)))
        out.append(U.Fixture('negative-reg-' + f.name, st, [], f.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs={'d5': st['regs']['d5'] ^ 1})))
    f = pool[0]
    out.append(U.Fixture('negative-stop-' + f.name, f.state, [], f.stop, 'mismatch', cpp_stop=0x2ac2 if f.stop != 0x2ac2 else 0xc00444))
    f = [x for x in fixtures if x.name.startswith('carry-4fb3c-set')][0]
    out.append(U.Fixture('negative-carry-write-' + f.name, f.state, [], f.stop, 'mismatch', cpp_state=U.flip_ram(f.state, NODE + 0x63)))
    return out


def coverage(fixtures):
    got = {}
    for f in fixtures:
        if f.name.startswith('edge-') and f.expect == 'match':
            got[int(f.meta['block'], 16)] = got.get(int(f.meta['block'], 16), 0) + 1
    missing = [pc for pc in STARTS if pc != 0x4fb3c and got.get(pc, 0) == 0]
    U.require(not missing, ('block starts without an edge fixture', [hx(p) for p in missing]))


def build():
    rng = random.Random(0xc3b)
    out = []
    for case in CASES:
        for pc in STARTS:
            out += edge_fixtures(rng, pc, case)
    coverage(out)
    for case in CASES:
        out += chain_fixtures(rng, case)
        out += boot_fixtures(case)
        out += carry_fixtures(case)
    out += error_fixtures(CASES[0])
    out += negative_fixtures(out)
    return out
