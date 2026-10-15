"""V1 fixture spec of the animation-machine unit B1a (engine/src/animation_machine_objects_b1a.cpp, 215 block starts).

Blocks: the N16b part of the 7839a object (107 starts: 783ea..7865c, the tail 78cc4..78d3a, the helpers 7919a 79222 7962a), the U19b part (86 starts, b7100..b769e: the two ground
states b7100 / b749c and their installed states) and the 22 leaf helper starts 7930a 796e6 7970e 79722 b7d2e b7d3c (none of them is routed by another unit; checked below).

Fixture families (native Unicorn on the original ROM versus the C++ run; V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start (the 19 carry consumers excepted) is entered directly.  The world is a natural N-pass node state of the D1 seeds 76 77 98 105 (the 7839a object: node 12 / 13
            of frame 0, the 77596 state of frame 1) or 8 9 80 81 (the U19 object: b6300 / b6406 / b6362 / b6ac8 nodes) with a declared host edit of D0-D7, A0-A4, the node fields and the
            absolute fields the reachable blocks of the unit read (values drawn from a seeded generator) and PC := the block start.  The stop is the first PC outside the unit (a callee,
            a routed neighbour, the sentinel return LONG, a JMP target).  Worlds are kept per entry while they add a new successor of the entry block (both sides of every branch).
  hint      declared boundary worlds the random generator does not reach by chance (the signed compares of 7851a 7852c 79640 79722 7970e b7256 b745c ..., the sign/zero tests of 796e6,
            the stack word of b75f8, the 28ae failure of 78d0a, the ground index of the 8e(A6) selectors).
  coverage  worlds that reach a conditional branch outcome of any block that the block fixtures did not take.
  chain     every carry consumer (78408 78454 784a0 784ae 7853e 7854c 785dc 78636 78644 78652 78cfe 78d1a 79630 79638 b71a0 b726a b7392 b7538 b75ee) is entered from its calling block with
            the REAL routed producer (791fa 49fc6 79222 7962a 7930a 1ab02 28ae 4945e 79722) running natively through every routed PC: native branches on the real flags, the C++ on the
            known C.  Both outcomes of each consumer are searched.
  oracle    the known C tag of the C++ run at the stop PC (Clear / Set) must equal the C flag of the original CPU (Unicorn SR) for every match fixture.
  error     every even non-start PC of the unit ranges, the unrouted neighbours, the boundaries reached without a stop PC, odd PCs, Unknown C at the 19 consumers: checked error, state kept.
  negative  C++ input differs from the native input in one RAM bit / one register / the stop PC: the comparison must report it.
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
N16_BASES = ((76, 0, 12), (77, 1, 12), (98, 0, 13), (105, 1, 13))       # (seed, frame, node index): the 7839a callback / its 77596 state
U19_BASES = ((8, 0, 6), (9, 1, 5), (80, 0, 5), (81, 1, 5))              # the U19 object nodes b6300 / b6406 / b6362 / b6ac8
MAX_TRIES = 260
KEEP_EXTRA = 3                          # extra worlds kept per entry beyond the first world of each successor
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x783ea, 0x78660), (0x78cc4, 0x78d5a), (0x7919a, 0x791c0), (0x79222, 0x79256), (0x7930a, 0x79320), (0x7962a, 0x79654), (0x796e6, 0x79746),
          (0xb7100, 0xb76a4), (0xb7d2e, 0xb7d4a)]
STARTS = [int(x, 16) for x in (
    '783ea 783f2 783fe 78404 78408 7840c 7843e 78444 7844a 78450 78454 78458 7845e 78462 78468 78490 78496 7849a 784a0 784a4 784aa 784ae 784b2 784b8 784bc '
    '784c0 784cc 784f4 784fa 784fe 78504 78510 7851a 78522 78528 7852c 78534 7853a 7853e 78542 78548 7854c 78550 78556 7855a 78564 7856e 785ae 785b4 785ba '
    '785c4 785d0 785d6 785dc 785e0 785e8 785ee 785f2 78622 78628 7862c 78632 78636 7863a 78640 78644 78648 7864e 78652 78656 7865c 78cc4 78cc8 78cd0 78cd6 '
    '78cdc 78ce6 78cf0 78cf4 78cfe 78d02 78d08 78d0a 78d1a 78d1e 78d2a 78d2e 78d3a 7919a 791a0 791aa 791b0 791b8 791be 79222 7922c 79240 7924c 79250 7930a '
    '79314 79318 7931a 7962a 79630 79634 79638 7963c 79640 79648 7964e 796e6 796f4 796fa 796fc 79700 79706 79708 7970e 7971e 79720 79722 79732 7973a 79740 '
    'b7100 b7106 b7112 b714a b714e b7186 b718c b719a b71a0 b71a4 b71aa b71ae b71ba b71f2 b71f6 b722e b723c b7246 b724c b7256 b725e b7264 b726a b726e b727a '
    'b72b2 b72b6 b72ee b72f2 b72f8 b7304 b733c b7340 b7378 b7380 b7386 b738c b7392 b7396 b739c b73a0 b73b2 b73ea b73ee b7426 b7444 b744c b745c b746a b7474 '
    'b7482 b7488 b7492 b7498 b749c b74a2 b74ae b74e6 b74ea b7522 b7528 b7532 b7538 b753c b7544 b754a b754e b755a b7592 b7596 b75ce b75dc b75e6 b75ee b75f2 '
    'b75f8 b75fe b7604 b760e b7614 b7618 b761e b762a b7662 b7666 b769e b7d2e b7d3a b7d3c b7d48').split()]
CONSUMERS = (0x78408, 0x78454, 0x784a0, 0x784ae, 0x7853e, 0x7854c, 0x785dc, 0x78636, 0x78644, 0x78652, 0x78cfe, 0x78d1a, 0x79630, 0x79638,
             0xb71a0, 0xb726a, 0xb7392, 0xb7538, 0xb75ee)
# neighbours / boundaries that no unit routes: the state chains 78660 78716 78776, the tail cc8b4 and the end of every range
UNROUTED_NEIGHBOURS = (0x78660, 0x78716, 0x78776, 0x78d5a, 0x79320, 0x79654, 0x79746, 0xb7d4a, 0xcc8b4, 0x79400, 0x7942e, 0x79454, 0x7949c, 0x794e2)
STARTS_SET = set()
# producer extra fields: node bytes the routed producer reads (the unit's own blocks do not touch them)
CHAIN_FIELDS = {0x78404: [(6, 0x15, 1), (6, 0x97, 1)], 0x78450: [(6, 0x15, 1), (6, 0x97, 1)], 0x784aa: [(6, 0x15, 1), (6, 0x97, 1)],
                0x78548: [(6, 0x15, 1), (6, 0x97, 1)], 0x7864e: [(6, 0x15, 1), (6, 0x97, 1)]}
NO_EDIT = (0x20, 0x22)                   # the animation record pointers of the node: the interpreter (49f8c / 49fc6) reads them, keep them natural

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x0e, 0x0f, 0x10, 0x1e, 0x20, 0x40, 0x60, 0x7f, 0x80, 0x81, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0x10, 0x23, 0x24, 0x25, 0x30, 0x31, 0x100, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffef, 0xfffe, 0xffff)
VL = (0, 1, 0x10000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff20000, 0xffffffff, 0x2800, 0x270e, 0xf, 0x10, 0xfffffff0)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
ABS = re.compile(r'\$([0-9a-f]{5,6})\.l')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')

# ---------------------------------------------------------------------------------------------------------------------
# Routing (parsed from the C++ dispatch chain) and static decode
# ---------------------------------------------------------------------------------------------------------------------
_ROUTE = []


def load_routing():
    text = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    i = text.index('if ((next.pc>=0x3ac8')
    j = text.index('else return am_error(c,"unsupported animation machine PC")')
    for m in re.finditer(r'(?:else )?if \((.*?)\)ok=(\w+)\(c\);', text[i:j], re.S):
        e = m.group(1).replace('next.pc', 'p').replace('&&', ' and ').replace('||', ' or ')
        e = re.sub(r'!stage_event_ops_trap\(p\)', 'not trap(p)', e)
        e = e.replace('!=', '<>').replace('!', ' not ').replace('<>', '!=')
        _ROUTE.append((m.group(2), compile('(' + e.replace('\n', ' ') + ')', 'route', 'eval')))
    require(len(_ROUTE) >= 100, ('routing rules', len(_ROUTE)))


_UNIT = {}


def unit_of(pc):
    if pc not in _UNIT:
        _UNIT[pc] = _unit_of(pc)
    return _UNIT[pc]


def _unit_of(pc):
    env = {'p': pc, 'trap': lambda x: x in (0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788)}
    for unit, code in _ROUTE:
        if eval(code, env):
            return unit
    return None


def require(ok, detail):
    if not ok:
        raise RuntimeError(str(detail))


_MINE = {}


def mine(pc):
    if pc not in _MINE:
        _MINE[pc] = any(lo <= pc < hi for lo, hi in RANGES)
    return _MINE[pc]


_CS = []


def decode(addr):
    if not _CS:
        import capstone
        _CS.append(capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000))
        _CS.append(U.native().program)
    for ins in _CS[0].disasm(_CS[1][addr:addr + 12], addr):
        return ins
    return None


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full) of the block at `start`: up to a branch / call / return or the next block start."""
    out = []
    a = start
    starts = STARTS_SET
    while True:
        ins = decode(a)
        require(ins is not None, ('undecodable', hex(a)))
        mn = ins.mnemonic.split('.')[0]
        out.append((a, mn, ins.op_str, ins.size, ins.mnemonic))
        a += ins.size
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr') or BCC.match(mn) or a in starts or (start in starts and not mine(a)) or len(out) > 40:
            return out


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op)
    return int(m.group(1), 16) if m else None


def static_next(start):
    """Static successors of the entry block (None = computed: RTS)."""
    last = block_instrs(start)[-1]
    a, mn, op, size, _ = last
    if BCC.match(mn):
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr'):
        return {target(op)}
    if mn == 'rts':
        return None
    return {a + size}


def reachable_blocks(start):
    seen, work = set(), [start]
    while work:
        s = work.pop()
        if s in seen or s not in STARTS_SET:
            continue
        seen.add(s)
        nxt = static_next(s)
        if nxt:
            work += list(nxt)
        last = block_instrs(s)[-1]
        if last[1] in ('jsr', 'bsr'):
            work.append(last[0] + last[3])
    return seen


def fields_of(start):
    """Memory fields (kind, reg, displacement, size) read or written by the blocks reachable from `start`."""
    out = set()
    for s in reachable_blocks(start):
        for a, mn, op, size, full in block_instrs(s):
            if mn in ('lea', 'movem', 'jsr', 'jmp', 'bsr', 'bra', 'rts') or BCC.match(mn):
                continue
            sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
            for m in HX.finditer(op):
                disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
                if int(m.group(3)) == 6 and disp in NO_EDIT:
                    continue
                out.add(('reg', int(m.group(3)), disp, sz))
            for m in ABS.finditer(op):
                ad = int(m.group(1), 16)
                if 0x100000 <= ad < 0x200000:
                    out.add(('abs', 0, ad, sz))
    return sorted(out)


# ---------------------------------------------------------------------------------------------------------------------
# Native tracer (selection of worlds only: every kept world is re-run by the V1 verifier, native versus C++)
# ---------------------------------------------------------------------------------------------------------------------
def trace(state, outside, cap=CAP_INSN):
    """Run the original from state.pc natively until `outside(pc)` is true (checked from the second instruction on).  -> dict(pcs, stop, regs, sr) or None."""
    N = U.native()
    unicorn, S, PB = N.unicorn, N.S, N.PB
    snap = dict(ram=state['ram'], regs=state['regs'], pc=state['pc'], bank=state['bank'])
    m = PB.PvcMachine(N.program, N.fixed, snap)
    m.install_basic_hooks()
    c = m.cpu
    for base in (0x340000, 0x380000):
        c.mem_map(base, 4096, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    c.mem_write(U.PVC_LO, state['pvc'])
    c.mem_write(U.STATUS_ADDR, b'\x00')
    pcs = []
    box = {}

    def code(uc, pc, size, user):
        if box.get('stop') == -1:
            return
        if pcs and outside(pc):
            box['stop'] = pc
            uc.emu_stop()
            return
        pcs.append(pc)
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    try:
        c.emu_start(state['pc'], 0xffffff, count=cap)
    except unicorn.UcError:
        return None
    stop = box.get('stop')
    if stop is None or m.odd is not None or m.invalid is not None or m.intr is not None or m.fetch_unmapped is not None or m.dev_reads:
        return None
    # Unicorn evaluates the M68000 condition codes lazily: reg_read(SR) returns stale flags.  MOVE SR,D0 on a scratch page forces the evaluation.
    c.mem_map(SCRATCH, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE | unicorn.UC_PROT_EXEC)
    c.mem_write(SCRATCH, b'\x40\xc0\x4e\x71')
    box['stop'] = -1
    c.emu_start(SCRATCH, SCRATCH + 2, count=1)
    return dict(pcs=pcs, stop=stop, ports=len(m.ports), sr=c.reg_read(S.UC_REG['d0']) & 0xffff)


# ---------------------------------------------------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------------------------------------------------
class World(object):
    def __init__(self, groups, rng):
        self.groups, self.rng = groups, rng

    def pointer(self, a6):
        rng = self.rng
        pool = [a6, a6 + 0xc4, a6 - 0xc4, a6 + 0x188, a6 - 0x188, 0x1009a8, 0x1009a8 + 0xc4 * 5, 0x1009a8 + 0xc4 * 9]
        return rng.choice(pool) & 0xffffff

    def value(self, size, a6):
        rng = self.rng
        if size == 1:
            return rng.choice(VB)
        if size == 2:
            return rng.choice(VW + tuple(rng.randrange(65536) for _ in range(2)))
        k = rng.random()
        if k < 0.25:
            return self.pointer(a6)
        if k < 0.8:
            return rng.choice(VL)
        return rng.randrange(1 << 32)

    def make(self, entry, ret, flds, hint=None):
        rng = self.rng
        base = rng.choice(self.groups[1 if entry >= 0xb0000 else 0])
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4)), a6) if rng.random() < 0.9 else rng.randrange(1 << 32)
        regs['a0'] = self.pointer(a6)
        for k in ('a1', 'a2', 'a3', 'a4'):
            regs[k] = self.pointer(a6) if rng.random() < 0.9 else regs[k]
        writes = []
        for kind, reg, disp, size in flds:
            if rng.random() < 0.5:
                continue
            base_addr = disp if kind == 'abs' else (regs['a%d' % reg] + disp) & 0xffffffff
            if not (0x100000 <= base_addr < 0x200000) or (size > 1 and base_addr & 1):
                continue
            if 0xee00 <= (base_addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((base_addr & 0xffff, size, self.value(size, a6) & ((1 << (8 * size)) - 1)))
        sp = regs['a7']
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            writes += [((regs['a6'] + off) & 0xffff, size, val) for off, size, val in hint.get('a6off', [])]
            writes += [((regs['a0'] + off) & 0xffff, size, val) for off, size, val in hint.get('a0off', [])]
            for w in hint.get('writes', []):
                if w[0] == 'sp':                                  # ('sp', offset, size, value): a value at A7 + offset
                    writes.append(((sp + w[1]) & 0xffff, w[2], w[3]))
                else:
                    writes.append(w)
            if 'near' in hint:                                    # (dx, dy): the node next to player 0 (100cb8, active byte 568e(A5)): the 4945e / 79722 / 7970e distances
                dx, dy = hint['near']
                px = int.from_bytes(st['ram'][0xcb8 + 0x42:0xcb8 + 0x44], 'big')
                py = int.from_bytes(st['ram'][0xcb8 + 0x46:0xcb8 + 0x48], 'big')
                writes += [((regs['a6'] + 0x42) & 0xffff, 2, (px - dx) & 0xffff), ((regs['a6'] + 0x46) & 0xffff, 2, (py - dy) & 0xffff), (regs['a5'] + 0x568e - 0x100000, 1, 1)]
            regs.update(hint.get('regs', {}))
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    require(len(STARTS) == 215 and len(STARTS_SET) == 215, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for pc in UNROUTED_NEIGHBOURS:
        require(unit_of(pc) is None, ('neighbour is routed', hex(pc), unit_of(pc)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b1a_block', ('start is not routed to b1a', hex(s), unit_of(s)))
        require(any(lo <= s < hi for lo, hi in RANGES), ('start outside the ranges', hex(s)))
    rng = random.Random(0xB1A)
    groups = ([], [])
    for gi, bl in enumerate((N16_BASES, U19_BASES)):
        for case, frame, node in bl:
            fx = U.seed_node_fixture(case, frame, node=node, name='base')
            require(fx is not None, ('missing node', case, frame, node))
            groups[gi].append(fx)
    world = World(groups, rng)
    out = []
    names = set()
    covered = set()
    visited = set()
    cond_points = {}        # branch address -> {successor}

    def add(fx):
        require(fx.name not in names, ('duplicate', fx.name))
        names.add(fx.name)
        out.append(fx)

    def outside_unit(allowed=()):
        al = set(allowed)
        return lambda pc: not mine(pc) and pc not in al

    def record(entry_pcs):
        visited.update(entry_pcs)
        for i in range(len(entry_pcs) - 1):
            pc = entry_pcs[i]
            if pc in cond_points:
                covered.add((pc, entry_pcs[i + 1]))

    for s in STARTS:
        a, mn, op, size, _ = block_instrs(s)[-1]
        if BCC.match(mn):
            cond_points[a] = {target(op), a + size}
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        blk = block_instrs(entry)
        n = len(blk)
        needed = static_next(entry)
        flds = fields_of(entry)
        kept = {}
        extra = 0
        hints = hint_worlds(entry)
        for t in range(MAX_TRIES + len(hints)):
            stats['tries'] += 1
            st = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
            tr = trace(st, outside_unit())
            if tr is None or len(tr['pcs']) < n:
                stats['rejected'] += 1
                continue
            record(tr['pcs'] + [tr['stop']])
            nxt = tr['pcs'][n] if len(tr['pcs']) > n else tr['stop']
            if nxt in CONSUMERS or (mine(nxt) and nxt not in STARTS_SET):
                continue                                        # the native flags at a consumer entered by a computed jump are not a known C
            if t < len(hints):
                kept[('h', t)] = (st, tr)                       # declared boundary worlds are always kept
                if nxt not in kept:
                    kept[nxt] = (st, tr)
            elif nxt not in kept:
                kept[nxt] = (st, tr)
            elif extra < KEEP_EXTRA:
                extra += 1
                kept[(nxt, extra)] = (st, tr)
            if needed is not None and len(needed) > 1 and set(k for k in kept if isinstance(k, int)) >= needed and extra >= KEEP_EXTRA and t >= len(hints):
                break
            if (needed is None or len(needed) <= 1) and extra >= KEEP_EXTRA and t >= len(hints):
                break
        require(kept, ('no world for the block', hex(entry)))
        seen_worlds = set()
        for i, key in enumerate(sorted(kept, key=lambda k: (0, k) if isinstance(k, int) else (1, k[1]))):
            st, tr = kept[key]
            if id(st) in seen_worlds:
                continue
            seen_worlds.add(id(st))
            nxt1 = tr['pcs'][n] if len(tr['pcs']) > n else tr['stop']
            add(U.Fixture('block-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='block', entry=entry, successor=nxt1)))
            if nxt1 != tr['stop']:                              # the exit of the entered block alone: later blocks of the long run cannot hide a defect of this one
                add(U.Fixture('single-%05x-%d' % (entry, i), st, [], nxt1, meta=dict(family='single', entry=entry, successor=nxt1)))
        if needed and len(needed) > 1:
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)))
            if missing:
                out_missing.append((entry, missing))
    chain_fixtures(world, add, record)
    # ---- coverage fixtures: outcomes of any conditional branch not taken so far
    todo = [(a, t) for a, ts in sorted(cond_points.items()) for t in sorted(ts) if (a, t) not in covered]
    entries_for = {}
    for s in STARTS:
        for r in reachable_blocks(s):
            entries_for.setdefault(r, []).append(s)
    for a, t in todo:
        blk = [s for s in STARTS if any(x[0] == a for x in block_instrs(s))][0]
        done = False
        for entry in [e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS][:8]:
            flds = fields_of(entry)
            for _ in range(MAX_TRIES):
                st = world.make(entry, SENTINEL, flds)
                tr = trace(st, outside_unit())
                if tr is None:
                    continue
                record(tr['pcs'] + [tr['stop']])
                if (a, t) in covered:
                    add(U.Fixture('cover-%05x-%05x' % (a, t), st, [], tr['stop'], meta=dict(family='coverage', entry=entry, branch=a, outcome=t)))
                    done = True
                    break
            if done:
                break
        if not done:
            unreachable.append((a, t))
    never = sorted(set(STARTS) - visited)
    require(not never, ('block starts never executed by a fixture', [hex(x) for x in never]))
    error_fixtures(groups, add)
    negative_fixtures(out, add)
    META['carry_oracle'] = carry_oracle(out)
    META['visited_starts'] = len(set(STARTS) & visited)
    META['chain_only'] = [hex(x) for x in CONSUMERS]
    META['out_missing'] = [(hex(a), [hex(x) for x in m]) for a, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    for k in ('out_missing', 'unreachable'):
        if META[k]:
            sys.stderr.write('b1a: %s %s\n' % (k, META[k]))
    return out


out_missing = []
unreachable = []
META = {}


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC."""
    import os
    U.build_harness(2)
    exe = U.BUILD / 'unit_fixture_acceptance'
    harness = U.Harness(exe, U.program_resources(), os.devnull)
    counts = {0: 0, 1: 0, 2: 0}
    try:
        for fx in fixtures:
            if fx.expect != 'match':
                continue
            got = U.cpp_call(harness, fx)
            if not got['ok']:
                continue                                        # the verifier reports a C++ failure itself
            counts[got['carry']] += 1
            if got['carry'] == 0:
                continue
            tr = trace(fx.state, lambda pc, stop=fx.stop: pc == stop)
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('b1a: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: boundary values of the compares / tests of the unit.  Every hint world is kept as a fixture."""
    h = []
    a6b = lambda off, size, vals: [dict(a6off=[(off, size, v)]) for v in vals]
    if entry == 0x783ea:
        h += a6b(0x8a, 1, (0, 1, 0xff))
    if entry == 0x7840c:
        h += a6b(0x36, 4, (0x80000000, 0xffffffff, 1, 0x7fffffff, 0xfffffffe, 0))
    if entry == 0x783f2:
        h += a6b(0x8a, 1, (0, 0x7f, 0xff))
    if entry in (0x7851a, 0x7852c):
        h += [dict(regs=dict(d0=0x12340000 | a), a6off=[(0x42, 2, b)]) for a, b in ((5, 5), (4, 5), (6, 5), (0x7fff, 0x8000), (0x8000, 0x7fff), (0xffff, 0), (0, 0xffff))]
    if entry == 0x78cc8:
        h += a6b(0x84, 2, (0, 1, 2, 0x8000, 0xffff))
    if entry == 0x785e0:
        h += a6b(0x36, 2, (0, 1, 0x8000))
    if entry == 0x7930a:
        h += a6b(0x84, 2, (0, 1, 0x7fff, 0x8000, 0xffff))
    if entry == 0x79640:
        h += [dict(regs=dict(d0=v)) for v in (0x2f, 0x30, 0x31, 0x7fff, 0x8000, 0xffff, 0x12340030, 0x12340031)]
    if entry == 0x7922c:
        h += a6b(0x98, 1, (0x0d, 0x0e, 0x0f, 0x10, 0x7e, 0x7f, 0x80, 0xff))
    if entry == 0x7970e:
        h += [dict(a6off=[(0x42, 2, a)], a0off=[(0x42, 2, b)]) for a, b in ((5, 5), (5, 6), (6, 5), (0, 0x8000), (0x8000, 0), (0x7fff, 0xffff), (0xffff, 0x7fff))]
    if entry == 0x79722:
        h += [dict(a6off=[(0x46, 2, a)], a0off=[(0x46, 2, (a + d) & 0xffff)]) for a in (0, 0x1000) for d in (0x2f, 0x30, 0x31, 0, -0x0f, -0x10, -0x11, 0x7fff, 0x8000)]
    if entry in (0x79634, 0x7963c):
        h += [dict(a6off=[(0x46, 2, 0), (0x42, 2, 0)], a0off=[(0x46, 2, d), (0x42, 2, e)]) for d, e in ((0x30, 0), (0x31, 0), (0xfff0, 0x30), (0xffef, 0), (0, 0x30), (0, 0x31), (0, 0xffd0))]
    if entry == 0x796e6:
        h += [dict(a6off=[(0x64, 4, v), (0x9b, 1, b)]) for v in (0, 1, 0xffffffff, 0x80000000, 0x7fffffff) for b in (0, 1)]
    if entry in (0x796f4, 0x79700):
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0xffffffff, 0x80000000, 0x7fffffff)]
    if entry == 0x7971e:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x8000, 0xffff, 0x12348000)]
    if entry in (0x79732,):
        h += [dict(regs=dict(d0=v)) for v in (0xfff0, 0xffef, 0xfff1, 0x8000, 0x7fff)]
    if entry == 0x78cdc:
        h += a6b(0x61, 1, (0x7f, 0x80))
    if entry in (0x7855a,):
        h += a6b(0x9b, 1, (0, 0x20, 0x04, 0x24))
    if entry == 0x78564:
        h += a6b(0x9b, 1, (0, 0x04))
    if entry == 0x78d0a:
        h += [dict(writes=[(0x104ca0, 2, v)]) for v in (0x10, 0x13, 0x14, 0x15, 0x100, 0)]            # 28ae: D0.W = 14 against the pool size WORD
    if entry == 0xb7246:
        h += [dict(regs=dict(d0=v)) for v in (0x8000, 0x7fff, 0, 0x23, 0x24, 0x25, 0xffff, 0x12348024)]
    if entry == 0xb7256:
        h += [dict(regs=dict(d0=v)) for v in (0, 0x23, 0x24, 0x25, 0x7fff, 0xffff, 0x12340023, 0x12340024)]
    if entry == 0xb7444:
        h += a6b(0x36, 4, (0, 1, 0xf, 0x10, 0x1f, 0x20, 0xffffffff, 0xfffffff0, 0xffffffef, 0x80000000, 0x7fffffff))
    if entry == 0xb744c:
        h += [dict(regs=dict(d0=v)) for v in (1, 0xf, 0x10, 0xffffffff, 0xfffffff0, 0x80000000, 0x7fffffff)]
    if entry == 0xb745c:
        h += a6b(0x9c, 1, (0, 1, 2, 0x7f, 0x80, 0xff))
    if entry == 0xb75f8:
        h += [dict(writes=[('sp', 0, 2, v)]) for v in (0x7fff, 0x8000, 0xffff, 0)]
    if entry in (0xb7106, 0xb71ae, 0xb726e, 0xb72f8, 0xb73a0, 0xb74a2, 0xb754e, 0xb761e):
        h += a6b(0x8e, 2, (0, 1, 2, 3, 0x8000))
    if entry in (0xb7488, 0xb7604, 0x785ba, 0x791a0):
        h += a6b(0x15, 1, (0, 0x80, 0x7f, 0xff))
    if entry == 0x78632:
        h += [dict(near=(dx, dy)) for dx, dy in ((0, 0), (5, 5), (0x30, 0x30), (0x31, 0), (0, 0x31), (0, -0x10), (0, -0x11), (-0x30, 0), (-0x31, 0))] + [dict(writes=[(0x10d68e, 1, 0)])]
    if entry == 0x78640:
        h += [dict(a6off=[(0x84, 2, w), (0x42, 2, x)], writes=[(0x10d68e, 1, 1)]) for w, x in ((0, 0x20), (1, 0x20), (0, 0x17), (0, 0x18), (0, 0x128), (0, 0x129), (0x8000, 0x20))]
        h += [dict(a6off=[(0x84, 2, 0), (0x42, 2, 0x20)], writes=[(0x10d68e, 1, 0)])]
    if entry == 0x7962a:
        h += [dict(writes=[(0x10d68e, 1, v)]) for v in (0, 1, 2, 3)] + [dict(near=(dx, dy)) for dx, dy in ((0, 0), (0x31, 0), (0, 0x31))]
    if entry == 0x78cf4:                                    # 1ab02 (record 798ca): off-screen above / below / left / right gives C set, equal limits stay on-screen
        h += [dict(a6off=[(0x15, 1, 0), (0x46, 4, 0x02100000), (0x4e, 4, 0)]), dict(a6off=[(0x15, 1, 0), (0x46, 4, 0), (0x4e, 4, 0x02100000)]),
              dict(a6off=[(0x15, 1, 0), (0x46, 4, 0x00800000), (0x4e, 4, 0x00800000), (0x42, 4, 0x01800000), (0x4a, 4, 0)]),
              dict(a6off=[(0x15, 1, 0), (0x46, 4, 0x00800000), (0x4e, 4, 0x00800000), (0x42, 4, 0, ), (0x4a, 4, 0x01800000)]),
              dict(a6off=[(0x15, 1, 0), (0x46, 4, 0x00800000), (0x4e, 4, 0x00800000), (0x42, 4, 0x00800000), (0x4a, 4, 0x00800000)])]
    if entry == 0x796cc:
        h += a6b(0x15, 1, (0, 1))
    if entry == 0x791b0:
        h += a6b(0x36, 4, (0, 1, 0x10000, 0x80000000))
    return h


def chain_fixtures(world, add, record):
    """Every carry consumer with its REAL routed producer: the calling block runs natively through every routed PC (stop: first unrouted PC, the sentinel or JMP 2a00)."""
    pred = {}
    for s in STARTS:
        a, mn, op, size, _ = block_instrs(s)[-1]
        if mn == 'jsr' and a + size in CONSUMERS:
            pred[a + size] = s
    require(set(pred) == set(CONSUMERS), ('consumers without a calling block', [hex(x) for x in set(CONSUMERS) - set(pred)]))
    stop_at = lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL
    for cons in CONSUMERS:
        entry = pred[cons]
        flds = fields_of(entry) + [('reg',) + x for x in CHAIN_FIELDS.get(entry, [])]
        flds = [f if len(f) == 4 else (f[0], f[1], f[2], f[3]) for f in flds]
        kept = {}
        for t in range(MAX_TRIES * 2):
            hints = hint_worlds(entry)
            hint = hints[t] if t < len(hints) else None
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, stop_at, cap=6000)
            if tr is None or cons not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            i = tr['pcs'].index(cons)
            succ = tr['pcs'][i + 1] if i + 1 < len(tr['pcs']) else tr['stop']
            key = (succ, tr['stop'])
            if key not in kept:
                kept[key] = (st, tr)
            if len(set(k[0] for k in kept)) >= 2 and len(kept) >= 2 and t >= 40:
                break
        if not kept:
            unreachable.append((cons, 0))
            continue
        if len(set(k[0] for k in kept)) < 2:
            unreachable.append((cons, 1))                       # only one outcome of the consumer was reached
        for i, (key, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-%d' % (cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=key[0])))
            if key[0] != tr['stop']:                            # the run up to the consumer's own exit
                add(U.Fixture('chainexit-%05x-%d' % (cons, i), st, [], key[0], meta=dict(family='chainexit', entry=entry, consumer=cons, successor=key[0])))


def error_fixtures(groups, add):
    base = groups[0][0]
    ubase = groups[1][0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    ust = U.with_host_writes(ubase.state, [(ubase.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)
    # every even PC of the unit ranges that is not a block start
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b1a PC')))
    for pc in UNROUTED_NEIGHBOURS:
        add(U.Fixture('error-unrouted-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    for lo, hi in RANGES:
        for pc in (lo + 1, hi - 1):
            add(U.Fixture('error-odd-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    # Unknown C at the 19 consumers (carry tag 0)
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(ust if pc >= 0xb0000 else st, pc=pc), [], SENTINEL, ('error', 'objects b1a caller requires known carry')))
    # boundaries reached without a stop PC: the state-chain installs 78660 / 78716 (after 78648 / 7863a) and the branch 78776 (78564), the tail jump cc8b4 (78d3a)
    nat = st['regs']['a6']
    add(U.Fixture('error-boundary-78d3a-cc8b4', U.with_host_writes(st, pc=0x78d3a), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-boundary-78564-78776', U.with_host_writes(st, [((nat + 0x9b) & 0xffff, 1, 0)], pc=0x78564), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    # odd LONG write: the install MOVE.L #x,(A6) with an odd A6
    add(U.Fixture('error-odd-install', U.with_host_writes(st, regs=dict(a6=nat + 1), pc=0x7843e), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    # a0-relative store with a read-only target (78d2e: MOVE.B 5f(A6),5f(A0), A0 in ROM)
    add(U.Fixture('error-rom-store-78d2e', U.with_host_writes(st, regs=dict(a0=0x1000), pc=0x78d2e), [], SENTINEL, ('error', 'unsupported animation machine write device')))


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.name in ('block-7840c-0', 'block-b7444-0', 'block-79722-0', 'block-b7112-0', 'block-796e6-0', 'block-78cc8-0')]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, st['regs']['a6'] + 0x36)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
