"""V1 fixture spec of the animation-machine unit B2d (engine/src/animation_machine_objects_b2d.cpp, 220 block starts).

Blocks: the orphan state chain 39366 (391e8..395dc, 115 starts; installed by B2b 38dc2 and N32a 391de), its 28ae child 3b044 (3b044..3b118, 18) and the 28ae children
2d3ae / 2d57a of B2b 3a4da with their shared tail and the child 2d6e6 (2d3ae..2d7be, 87; the 9-slot BRA.W tables 2d490 / 2d644).  Contract:
docs/analysis/animation-machine-deferred-b2d-contract.md.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the nine consumers is entered directly.  The world is a natural N-pass node state of the D1 seeds 116/117 (frame 2: N31 38c36, N33
            3b166, N28 2b99c, N30a 331d8 / 34650, N29 30de4, N22 3d32c; node A6, A5, bank and RAM natural) with a declared host edit of D0-D7, A0-A4, the node fields the
            reachable blocks read (values from a seeded generator), the node pointers c(A6) / 4(A6) := another natural node, and PC := the block start.  Stop: the first PC
            outside the unit (a callee, the sentinel return LONG, an exit).  Worlds are kept per entry while they add a successor of the entry block.
  coverage  worlds that reach a conditional branch outcome (both sides of every Bcc, the 18 table slots) that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 3a4da (B2b) -> 3923c 39330 394a8, 3b334 (N33) -> 39358 395ce, 288c -> 3b0ec, 49fc6 -> 3b10c 2d56e 2d7b2.
            Native branches on the real flags, the C++ branches on the known C.  Stop: the consumer's successor (or the first unrouted PC of the run).
  node      the installed callbacks and child entries as node callbacks ((A6) := entry, PC := entry) run through every routed callee up to the dispatcher return or the
            first unrouted PC (LONG 82(A6) := 3a5d2 (N33, routed) for the JSR (A0) of 3a5be, or a natural value).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the nine consumers, 3a5be -> 3a60a (unrouted, B2c) without a stop PC, odd node stores: checked
            error, state preserved.
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b spec does).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x38c36, 0x3b166, 0x2b99c, 0x331d8, 0x34650, 0x30de4, 0x3d32c)
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x2d3ae, 0x2d7be), (0x391e8, 0x395dc), (0x3b044, 0x3b118)]
STARTS = [int(x, 16) for x in (
    '2d3ae 2d3c6 2d3e8 2d3f6 2d406 2d420 2d440 2d442 2d462 2d46c 2d476 2d480 2d488 2d490 2d494 2d498 2d49c 2d4a0 2d4a4 2d4a8 2d4ac 2d4b0 2d4b4 2d4be 2d4c4 2d4ca 2d4d0 '
    '2d4d8 2d4e6 2d504 2d50e 2d510 2d51a 2d524 2d540 2d55c 2d562 2d568 2d56e 2d572 2d578 2d57a 2d592 2d5b4 2d5c2 2d5d2 2d600 2d616 2d620 2d62a 2d634 2d63c 2d644 2d648 '
    '2d64c 2d650 2d654 2d658 2d65c 2d660 2d664 2d668 2d672 2d678 2d67e 2d684 2d69c 2d6ac 2d6be 2d6ca 2d6da 2d6e4 2d6e6 2d702 2d71e 2d746 2d758 2d75e 2d764 2d76a 2d770 '
    '2d776 2d77e 2d7ac 2d7b2 2d7b6 2d7bc '
    '391e8 391f2 391f6 391fe 39206 3920e 39218 39220 3922a 3923c 39244 3924c 39254 39262 3926e 39276 3927a 3927e 39282 3928c 39292 39296 392a6 392aa 392b0 392ba '
    '392be 392c6 392d6 392d8 392e0 392e2 392ea 392f2 392fa 39302 3930c 39314 3931e 39330 39338 39340 39348 39350 39354 39358 3935c 39362 39366 39370 39380 39384 '
    '3939c 393b0 393c6 393d0 393d4 393de 393e2 393e8 39400 39406 3941a 39430 3943a 3943e 39448 39454 3945e 39462 3946a 39472 3947a 39484 3948c 39496 394a8 394b0 '
    '394b8 394c2 394c6 394ce 394d8 394dc 394e2 394ea 394ee 394f2 394fc 39506 3951a 3951e 39534 3953e 39542 3954c 3955a 39564 39568 39570 39578 39580 3958a 39592 '
    '3959a 395a4 395a8 395b0 395ba 395be 395c6 395ca 395ce 395d2 395d8 '
    '3b044 3b062 3b070 3b08a 3b090 3b0a8 3b0ac 3b0c0 3b0c2 3b0e0 3b0e6 3b0ec 3b0f0 3b0f6 3b106 3b10c 3b110 3b116').split()]
CONSUMERS = (0x3923c, 0x39330, 0x394a8, 0x39358, 0x395ce, 0x3b0ec, 0x3b10c, 0x2d56e, 0x2d7b2)
TABLES = {0x2d488: 0x2d490, 0x2d63c: 0x2d644}
# entries whose block pops stack data before it ends: offset of the return LONG from A7 at the entry
RET_AT = {}
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x3922a, 0x3923c), (0x3931e, 0x39330), (0x39496, 0x394a8), (0x39354, 0x39358), (0x395ca, 0x395ce), (0x3b0e6, 0x3b0ec), (0x3b106, 0x3b10c),
          (0x2d568, 0x2d56e), (0x2d7ac, 0x2d7b2))
# installed callbacks and child entries (node callbacks)
NODE_ENTRIES = (0x39366, 0x39380, 0x39292, 0x392b0, 0x39454, 0x3951e, 0x3955a, 0x3b044, 0x3b0e6, 0x2d3ae, 0x2d57a, 0x2d420, 0x2d510, 0x2d562, 0x2d600, 0x2d6e6,
                0x2d77e)

VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x11, 0x18, 0x20, 0x40, 0x60, 0x7f, 0x80, 0x81, 0xbf, 0xc0, 0xc1, 0xfe, 0xff)
VW = (0, 1, 2, 0x10, 0x100, 0x14f, 0x150, 0x151, 0x160, 0x1e, 0x7fff, 0x8000, 0x8001, 0xc000, 0xe000, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff20000, 0xffe40000, 0xffffffff, 0x160000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
ABS = re.compile(r'\$([0-9a-f]{5,6})\.l')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')

# ---------------------------------------------------------------------------------------------------------------------
# Routing (parsed from the C++ dispatch chain) and static decode
# ---------------------------------------------------------------------------------------------------------------------
_ROUTE = []


def load_routing():
    del _ROUTE[:]
    text = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    i = text.index('if ((next.pc>=0x3ac8')
    j = text.index('else return am_error(c,"unsupported animation machine PC")')
    for m in re.finditer(r'(?:else )?if \((.*?)\)ok=(\w+)\(c\);', text[i:j], re.S):
        e = m.group(1).replace('next.pc', 'p').replace('&&', ' and ').replace('||', ' or ')
        e = re.sub(r'!stage_event_ops_trap\(p\)', 'not trap(p)', e)
        e = e.replace('!=', '<>').replace('!', ' not ').replace('<>', '!=')
        _ROUTE.append((m.group(2), compile('(' + e.replace('\n', ' ') + ')', 'route', 'eval')))
    require(len(_ROUTE) >= 110, ('routing rules', len(_ROUTE)))


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


_BLK = {}


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return or the next block start."""
    if start in _BLK:
        return _BLK[start]
    out = []
    a = start
    while True:
        ins = decode(a)
        require(ins is not None, ('undecodable', hex(a)))
        mn = ins.mnemonic.split('.')[0]
        out.append((a, mn, ins.op_str, ins.size, ins.mnemonic))
        a += ins.size
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr') or BCC.match(mn) or a in STARTS_SET or len(out) > 40:
            break
    _BLK[start] = out
    return out


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op)
    return int(m.group(1), 16) if m else None


def static_next(start):
    """Static successors of the entry block (None = computed: RTS)."""
    a, mn, op, size, _ = block_instrs(start)[-1]
    if BCC.match(mn):
        return {target(op), a + size}
    if mn == 'jmp' and 'pc,' in op:
        base = TABLES[start]
        return {base + 4 * k for k in range(9)}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None:
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
    """Memory fields (reg, displacement, size) read or written by the blocks reachable from `start` (A6 / A0 / A5 relative)."""
    out = set()
    for s in reachable_blocks(start):
        for a, mn, op, size, full in block_instrs(s):
            if mn in ('lea', 'movem', 'jsr', 'jmp', 'bsr', 'bra', 'rts', 'pea') or BCC.match(mn):
                continue
            sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
            if mn in ('btst', 'bset', 'bclr', 'bchg'):
                sz = 1
            for m in HX.finditer(op):
                disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
                out.add((int(m.group(3)), disp, sz))
    return sorted(out)


# ---------------------------------------------------------------------------------------------------------------------
# Native tracer (selection of worlds only: every kept world is re-run by the V1 verifier, native versus C++)
# ---------------------------------------------------------------------------------------------------------------------
def trace(state, outside, cap=CAP_INSN, carry=0):
    """Run the original from state.pc natively until `outside(pc, prev)` is true (checked from the second instruction on).  -> dict(pcs, stop, sr) or None."""
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
        if pcs and outside(pc, pcs[-1], box.get('size', 0)):
            box['stop'] = pc
            uc.emu_stop()
            return
        pcs.append(pc)
        box['size'] = size
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


def outside_unit(allowed=()):
    al = set(allowed)
    return lambda pc, prev, size: not mine(pc) and pc not in al


def first_unrouted(extra=()):
    """Stop at the sentinel, at 2a00 (object removal), at an extra PC, or at the first unrouted PC that is not the straight-line successor of the previous
    instruction (a PC inside a block of another executor is not a block entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00}
    return lambda pc, prev, size: pc in ex or (unit_of(pc) is None and pc != prev + size)


# ---------------------------------------------------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------------------------------------------------
class World(object):
    def __init__(self, bases, rng):
        self.bases, self.rng = bases, rng
        self.nodes = sorted(set(b.state['regs']['a6'] for b in bases))

    def pointer(self):
        return self.rng.choice(self.nodes)

    def value(self, size):
        rng = self.rng
        if size == 1:
            return rng.choice(VB) if rng.random() < 0.85 else rng.getrandbits(8)
        if size == 2:
            return rng.choice(VW) if rng.random() < 0.7 else rng.getrandbits(16)
        return rng.choice(VL) if rng.random() < 0.6 else rng.getrandbits(32)

    def make(self, entry, ret, flds, hint=None):
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        parent = self.pointer()
        other = self.pointer()
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        regs['a0'] = parent
        regs['a1'] = self.pointer()
        writes = [((a6 + 0xc) & 0xffff, 4, parent), ((a6 + 0x4) & 0xffff, 4, other)]
        base_of = {6: a6, 0: other if entry == 0x2d77e else parent, 5: regs['a5'], 1: (regs['a5'] + 0x538e) & 0xffffffff}
        if entry == 0x2d77e:
            regs['a0'] = other
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in (0, 4, 0xc):
                continue                                        # (A6) callback LONG and the node pointers stay declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        sp = regs['a7']
        writes.append(((sp + RET_AT.get(entry, 0)) & 0xffff, 4, ret))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                if w[0] == 'sp':
                    writes.append(((sp + w[1]) & 0xffff, 4, w[2]))
                else:
                    writes.append(w)
            regs.update(hint.get('regs', {}))
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
out_missing = []
unreachable = []
META = {}


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 220 and len(STARTS_SET) == 220, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    require(unit_of(0x3a60a) is None, '3a60a is routed: update the 3a5be error fixture')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b2d_block', ('start is not routed to b2d', hex(s), unit_of(s)))
    rng = random.Random(0xB2D)
    bases = []
    for case in SEEDS:
        frs = [f for f in U.seed_frames(case, FRAME + 1) if f['frame'] == FRAME]
        cbs = frs[0]['n']['cbs']
        for cb in BASE_CALLBACKS:
            require(cb in cbs, ('missing natural node', case, hex(cb)))
            fx = U.seed_node_fixture(case, FRAME, node=cbs.index(cb), name='base')
            require(fx is not None, ('missing node', case, hex(cb)))
            bases.append(fx)
    world = World(bases, rng)
    out = []
    names = set()
    covered = set()
    visited = set()
    cond_points = {}        # branch address -> {successor}

    def add(fx):
        require(fx.name not in names, ('duplicate', fx.name))
        names.add(fx.name)
        out.append(fx)

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
        elif mn == 'jmp' and 'pc,' in op:
            cond_points[a] = {TABLES[s] + 4 * k for k in range(9)}
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        n = len(block_instrs(entry))
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
                kept[('h', t)] = (st, tr)
                if nxt not in kept:
                    kept[nxt] = (st, tr)
            elif nxt not in kept:
                kept[nxt] = (st, tr)
            elif extra < 1 and (needed is None or len(needed) <= 1):
                extra += 1
                kept[(nxt, extra)] = (st, tr)
            if needed is not None and len(needed) > 1 and set(k for k in kept if isinstance(k, int)) >= needed and t >= len(hints):
                break
            if (needed is None or len(needed) <= 1) and len(kept) >= 2 and t >= len(hints):
                break
        require(kept, ('no world for the block', hex(entry)))
        seen_worlds = set()
        for i, key in enumerate(sorted(kept, key=lambda k: (0, k) if isinstance(k, int) else (1, str(k)))):
            st, tr = kept[key]
            if id(st) in seen_worlds:
                continue
            seen_worlds.add(id(st))
            add(U.Fixture('block-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='block', entry=entry, successor=tr['pcs'][n] if len(tr['pcs']) > n else tr['stop'])))
        if needed and len(needed) > 1:
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)))
            if missing:
                out_missing.append((entry, missing))
    chain_fixtures(world, add, record)
    node_fixtures(world, add, record)
    # ---- coverage fixtures: outcomes of any conditional branch not taken so far
    todo = [(a, t) for a, ts in sorted(cond_points.items()) for t in sorted(ts) if (a, t) not in covered]
    entries_for = {}
    for s in STARTS:
        for r in reachable_blocks(s):
            entries_for.setdefault(r, []).append(s)
    for a, t in todo:
        blk = [s for s in STARTS if any(x[0] == a for x in block_instrs(s))][0]
        done = False
        for entry in [e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS][:6]:
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
    error_fixtures(bases, add)
    negative_fixtures(out, add)
    META['carry_oracle'] = carry_oracle(out)
    META['visited_starts'] = len(set(STARTS) & visited)
    META['chain_only'] = [hex(x) for x in CONSUMERS]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('b2d spec: %d fixtures, visited %d/220, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b2d: carry oracle skipped (no harness binary)\n')
        return None
    import os
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
            tr = trace(fx.state, lambda pc, prev, size, stop=fx.stop: pc == stop, cap=U.DEFAULT_MAX_INSN)
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('b2d: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the 18 table slots and the boundary values of the compares / tests of the unit.  Every hint
    world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    if entry in TABLES:
        h += [dict(regs=dict(d0=0x55550000 | k)) for k in range(9)] + [dict(regs=dict(d0=k)) for k in (9, 0x10)]
    if entry in (0x2d480, 0x2d634):
        h += [dict(regs=dict(d0=k)) for k in (0, 8, 9, 0x10009, 0xffff)]
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    if entry == 0x3b0ac:
        h += [dict(regs=dict(d0=k), a0off=[(0x15, 1, b)]) for k in (0, 4) for b in (0, 1)]
    if entry == 0x3b090:
        h += [dict(a0off=[(0x94, 1, a), (0x15, 1, b)]) for a in (0, 0x20) for b in (0, 1)]
    if entry == 0x394fc:
        h += [dict(regs=dict(d0=d), a6off=[(0xaf, 1, af)]) for d, af in ((1, 0x10), (1, 0x0f), (0xf, 0xf0), (0xf, 0xef))]
    if entry == 0x394f2:
        h += byte(0xb0, (0, 1, 0x10))
    if entry == 0x2d684:
        h += byte(0x80, (0xbf, 0xc0, 0xc1))
    if entry in (0x2d4e6, 0x2d6ca):
        h += [dict(a6off=[(0x42, 2, v), (0x46, 2, w)]) for v in (0x14f, 0x150, 0xfff0) for w in (0x100, 0)]
    if entry in (0x2d504, 0x2d6da):
        h += [dict(a6off=[(0x46, 2, v)]) for v in (0xff, 0x100, 0x80ff, 0x8100)]
    if entry in (0x2d758, 0x2d764):
        h += [dict(regs=dict(d0=v)) for v in (0x7f, 0x80, 0x7fff, 0x8000)]
    if entry == 0x392c6:
        h += [dict(regs=dict(d0=v)) for v in (0, 4, 8, 0xc)]
    if entry == 0x39262:
        h += byte(0x97, (0, 4, 1))
    if entry == 0x3926e:
        h += [dict(regs=dict(d0=v)) for v in (4, 0x104, 5)]
    if entry in (0x393b0, 0x3941a, 0x3951e):
        h += [dict(a6off=[(0x94, 1, a), (0x15, 1, b)]) for a in (0, 0x20) for b in (0, 1)]
    if entry in (0x391e8, 0x392b0, 0x39454, 0x3955a, 0x3920e, 0x39302, 0x3947a, 0x39580):
        h += byte(0x15, (0, 0x80))
    if entry in (0x39206, 0x392fa, 0x39472, 0x39578):
        h += byte(0x9f, (0, 1))
    if entry in (0x39220, 0x39314, 0x3948c):
        h += byte(0x9d, (0, 0x40))
    if entry in (0x394b8, 0x394ce, 0x3959a, 0x395b0):
        h += byte(0x94, (0, 0x20))
    if entry in (0x2d462, 0x2d616):
        h += byte(0x15, (0, 0x80))
    if entry in (0x2d46c, 0x2d620, 0x2d4b4, 0x2d668):
        h += byte(0x61, (0, 1, 2, 3))
    if entry == 0x2d4d0:
        h += [dict(a6off=[(0x3a, 4, v)]) for v in (0, 0x80000000)]
    if entry == 0x392be:
        h += byte(0x98, (0, 0xff))
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their real producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0xb2, 0x9f, 0x15, 0x94, 0xae, 0x61)] + [(6, off, 4) for off in (0x56, 0x36)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in (0x3922a, 0x3931e, 0x39496):
                k = t % 3
                if k == 0:
                    hint = dict(a6off=[(0xb2, 1, rng.choice((1, 0x18, 0xff)))])                     # 3a4da: BYTE b2 != 0 -> 3a5b8 (Clear)
                else:
                    hint = dict(a6off=[(0xb2, 1, 0), (0x9f, 1, rng.choice((0x10, 0x11)))], writes=[(0xf001, 1, rng.choice((0, 4)))])
            st = world.make(entry, SENTINEL, flds, hint)
            if entry == 0x3b0e6:
                a6 = st['regs']['a6']
                parent = int.from_bytes(st['ram'][(a6 + 0xc) & 0xffff:((a6 + 0xc) & 0xffff) + 4], 'big')
                k = t % 3
                if k == 0:
                    st = U.with_host_writes(st, [(parent & 0xffff, 4, 0x270e)])                       # 288c: parent callback 270e -> Clear
                elif k == 1:
                    st = U.with_host_writes(st, [((a6 + 0xc) & 0xffff, 4, 0)])                        # no parent -> Set
            tr = trace(st, first_unrouted(extra=succ), cap=200000)
            if tr is None or cons not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = tr['stop']
            if key not in kept:
                kept[key] = (st, tr)
            if set(kept) >= succ:
                break
        require(kept, ('no chain world', hex(entry)))
        missing = succ - set(kept)
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (stop, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], stop, meta=dict(family='chain', entry=entry, consumer=cons, successor=stop)))


def node_fixtures(world, add, record):
    """Installed callbacks and child entries run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first
    unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            st = world.make(entry, base.stop, flds)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry), ((st['regs']['a6'] + 0x82) & 0xffff, 4, rng.choice((0x3a5d2, 0x3a5d2, 0x3a60a)))])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], len(set(tr['pcs']) & STARTS_SET) // 4)
            if key in kept:
                continue
            kept[key] = (st, tr)
            if len(kept) >= 3:
                break
        require(kept, ('no node world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('node-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='node', entry=entry, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET))))


def error_fixtures(bases, add):
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b2d PC')))
    add(U.Fixture('error-odd-pc', U.with_host_writes(st, pc=0x39367), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'objects b2d caller requires known carry')))
    a6 = st['regs']['a6']
    # 394e2: MOVEA.L 82(A6),A0; JSR 3a5be -> JSR (A0) = 3a60a (unrouted, B2c) without a stop PC there
    add(U.Fixture('error-394e2-3a5be-3a60a', U.with_host_writes(st, [((a6 + 0x82) & 0xffff, 4, 0x3a60a)], pc=0x394e2), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    # odd node: CLR.L 64(A6) / MOVE.W 2c(A6) at an odd A6
    add(U.Fixture('error-39370-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x39370), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    add(U.Fixture('error-2d4e6-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x2d4e6), [], SENTINEL, ('error', 'program bus requires even WORD/LONG address')))
    # table landing inside the JMP instruction (no limit test in the table block, as in the original)
    add(U.Fixture('error-2d488-ffff', U.with_host_writes(st, regs=dict(d0=0xffff), pc=0x2d488), [], SENTINEL, ('error', 'unsupported animation objects b2d PC')))


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x2d420, 0x3b0c2, 0x39370, 0x2d77e)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0x36) & 0xffff, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
