"""V1 fixture spec of the animation-machine unit B3a (engine/src/animation_machine_objects_b3a.cpp, 216 block starts).

Blocks: the N28 range-outside installation chain 2ba50 without its middle states (B3b): the installed head 2ba50..2baf4 (17), the later states with the shared
per-frame tail 2c562 and the helper 2c71a (2c0fc..2c760, 166), the helpers 2b532 / 2b608 / 2b63e (2b532..2b668, 25) and the leaf 8d34 (8d34..8da2, 8).
Contract: docs/analysis/animation-machine-deferred-b3a-contract.md.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the ten consumers is entered directly.  The world is the natural N28 node (callback 2b99c) of the D1 seeds 116/117
            (frame 2; node A6, A5, bank, RAM and the pointer fields 78 / 94 / 9e natural) with a declared host edit of D0-D7, A1-A4, A0 := a natural node (the
            input WORD read of the 49be0 return), the node fields the reachable blocks read (values from a seeded generator), LONG 9e := natural or 2b3d0 (the
            real record), LONG 98 := 0 / 2c7a6 (the real N28 path list) and PC := the block start.  Stop: the first PC outside the unit (a callee, the sentinel
            return LONG, an exit).  Worlds are kept per entry while they add a successor of the entry block.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 28ae -> 2ba66, 4d6b4 -> 2b544, 2b418 (N28) -> 2bac8 2c1a0 2c2d0 2c382 2c43c 2c6fc,
            4d766 -> 2c618, 2b63e -> 4d418 -> 2c626.  Native branches on the real flags, the C++ branches on the known C.  Stop: the consumer's successor
            (or the first unrouted PC of the run).
  node      the installed callbacks as node callbacks ((A6) := entry, PC := entry) run through every routed callee up to the dispatcher return or the first
            unrouted PC (B3b 2bef6 / 2bfcc / 2c96a, 1c114).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the ten consumers, odd node stores: checked error, state preserved.
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b / B2d specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node: the owner of this chain (N28 2ba3e installs 2ba50)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: A0 pointers (input WORD / child)
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x8d34, 0x8da2), (0x2b532, 0x2b668), (0x2ba50, 0x2baf4), (0x2c0fc, 0x2c760)]
STARTS = [int(x, 16) for x in (
    '8d34 8d4c 8d4e 8d54 8d5c 8d72 8d92 8da0 '
    '2b532 2b53a 2b544 2b548 2b55e 2b568 2b56e 2b588 2b58a 2b5a2 2b5b2 2b5b6 2b5c6 2b5ea 2b5f0 2b5fc 2b602 2b608 2b610 2b634 2b636 2b63c 2b63e 2b660 2b662 '
    '2ba50 2ba66 2ba70 2ba7e 2ba8a 2ba8e 2ba92 2ba9c 2baac 2bab2 2bac4 2bac8 2bacc 2bad2 2badc 2baea 2baf0 '
    '2c0fc 2c106 2c11c 2c122 2c12c 2c138 2c14c 2c156 2c168 2c16a 2c172 2c174 2c180 2c188 2c190 2c198 2c19c 2c1a0 2c1a4 2c1aa 2c1ae 2c1b8 2c1d0 2c1d6 '
    '2c1e0 2c1ea 2c1ee 2c1f8 2c200 2c208 2c20e 2c212 2c220 2c226 2c230 2c236 2c250 2c274 2c298 2c29c 2c2a4 2c2a8 2c2ba 2c2be 2c2c8 2c2d0 2c2d4 2c2e4 '
    '2c2ee 2c2f6 2c2fc 2c300 2c30a 2c31a 2c328 2c332 2c33c 2c34e 2c350 2c358 2c35a 2c366 2c36e 2c376 2c37a 2c37e 2c382 2c386 2c38c 2c390 2c3a0 2c3a8 '
    '2c3b2 2c3bc 2c3c6 2c3cc 2c3d8 2c3de 2c3e8 2c3f6 2c408 2c412 2c424 2c426 2c42e 2c430 2c434 2c438 2c43c 2c440 2c456 2c45c 2c460 2c468 2c472 2c47c '
    '2c486 2c48c 2c496 2c4aa 2c4d4 2c4f8 2c4fc 2c504 2c508 2c51c 2c52a 2c532 2c53c 2c542 2c54c 2c55a 2c55e 2c562 2c56c 2c574 2c578 2c582 2c58a 2c58e '
    '2c598 2c5a2 2c5ae 2c5ba 2c5ca 2c5ce 2c5dc 2c5e6 2c5f4 2c602 2c60c 2c612 2c618 2c61c 2c622 2c626 2c62a 2c638 2c642 2c64c 2c654 2c65c 2c666 2c66c '
    '2c674 2c68a 2c690 2c69a 2c69e 2c6a8 2c6b0 2c6ba 2c6c8 2c6cc 2c6d6 2c6e6 2c6f4 2c6f8 2c6fc 2c700 2c70e 2c71a 2c728 2c72e 2c734 2c75a').split()]
CONSUMERS = (0x2b544, 0x2ba66, 0x2bac8, 0x2c1a0, 0x2c2d0, 0x2c382, 0x2c43c, 0x2c618, 0x2c626, 0x2c6fc)
TABLES = {}
RET_AT = {}
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x2ba50, 0x2ba66), (0x2b53a, 0x2b544), (0x2bac4, 0x2bac8), (0x2c19c, 0x2c1a0), (0x2c2c8, 0x2c2d0), (0x2c37e, 0x2c382), (0x2c438, 0x2c43c),
          (0x2c612, 0x2c618), (0x2c622, 0x2c626), (0x2c6f8, 0x2c6fc))
# installed callbacks (node callbacks) and the state entries reached by branches
NODE_ENTRIES = (0x2ba50, 0x2ba70, 0x2bab2, 0x2c0fc, 0x2c122, 0x2c1ae, 0x2c1d6, 0x2c212, 0x2c236, 0x2c300, 0x2c328, 0x2c390, 0x2c3f6, 0x2c4aa, 0x2c6cc,
                0x2c6f4)
RECORD = 0x2b3d0                        # the real record of LONG 9e (N28 2b7ce)
PATH = 0x2c7a6                          # the real N28 path list of LONG 98 (N28 2c818)
POINTERS = (0x78, 0x94, 0x98, 0x9e, 0x56)

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x18, 0x19, 0x20, 0x3e, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 0x10, 0x22, 0x40, 0x80, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff20000, 0xffffffff, 0x160000)
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
    require(len(_ROUTE) >= 112, ('routing rules', len(_ROUTE)))


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
    # The size Unicorn reports to the code hook is not the M68000 instruction length (287e MOVEA.L 8(A6),A0 -> 2882 was taken for a jump), so the length is decoded.
    def outside(pc, prev, size):
        if pc in ex:
            return True
        if unit_of(pc) is not None:
            return False
        ins = decode(prev)
        return pc != prev + (ins.size if ins is not None else size)
    return outside


# ---------------------------------------------------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------------------------------------------------
class World(object):
    def __init__(self, bases, pointers, rng):
        self.bases, self.rng = bases, rng
        self.nodes = sorted(set(pointers))

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
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if entry == 0x8d34 or rng.random() < 0.3:
            regs['d0'] = rng.choice((regs['d0'], rng.randrange(0x40), rng.randrange(0x100)))
            regs['d1'] = rng.choice((regs['d1'], rng.randrange(0x40), rng.randrange(0x100)))
        regs['a0'] = self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = 0x104d92 + 16 * rng.randrange(0x40)
        regs['a4'] = self.pointer()
        writes = []
        base_of = {6: a6, 0: regs['a0'], 5: regs['a5']}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp == 0 or disp in POINTERS or disp in (0x4, 0xc)):
                continue                                        # (A6) callback LONG, node links and the record / list pointers stay natural or declared below
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        if rng.random() < 0.35:
            writes.append(((a6 + 0x9e) & 0xffff, 4, RECORD))
        writes.append(((a6 + 0x98) & 0xffff, 4, rng.choice((0, 0, PATH, PATH + 4))))
        writes.append(((a6 + 0x7c) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4, 5, 6, 7, rng.getrandbits(8)))))
        writes.append(((a6 + 0x7d) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4, rng.getrandbits(8) & 0x7))))
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
    require(len(STARTS) == 216 and len(STARTS_SET) == 216, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b3a_block', ('start is not routed to b3a', hex(s), unit_of(s)))
    rng = random.Random(0xB3A)
    bases = []
    pointers = []
    for case in SEEDS:
        frs = [f for f in U.seed_frames(case, FRAME + 1) if f['frame'] == FRAME]
        cbs = frs[0]['n']['cbs']
        for cb in BASE_CALLBACKS:
            require(cb in cbs, ('missing natural node', case, hex(cb)))
            fx = U.seed_node_fixture(case, FRAME, node=cbs.index(cb), name='base')
            require(fx is not None, ('missing node', case, hex(cb)))
            bases.append(fx)
            pointers.append(fx.state['regs']['a6'])
        for cb in POINTER_NODES:
            if cb in cbs:
                fx = U.seed_node_fixture(case, FRAME, node=cbs.index(cb), name='pointer')
                if fx is not None:
                    pointers.append(fx.state['regs']['a6'])
    world = World(bases, pointers, rng)
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
                continue
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
    sys.stderr.write('b3a spec: %d fixtures, visited %d/216, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b3a: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('b3a: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests / shift counts of the unit.  Every hint world is
    kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    if entry in (0x2b532, 0x2b608, 0x2c582):
        h += [dict(a6off=[(0x92, 2, v)]) for v in (0, 1, 0x8000)]
    if entry == 0x2b58a:
        h += byte(0x84, (5, 4))
    if entry == 0x2b63e:
        h += [dict(a6off=[(0x7c, 1, k), (0x15, 1, b)]) for k in (0, 7, 0xff) for b in (0, 1)]
    if entry == 0x2c236:
        h += byte(0x7d, (0, 1, 0xff))
    if entry == 0x2ba70:
        h += byte(0x62, (0, 0xff))
    if entry == 0x2badc:
        h += [dict(a0off=[(0, 2, v)]) for v in (0x22, 0x20, 0x02)]
    if entry in (0x2c122, 0x2c328, 0x2c2e4, 0x2c69e, 0x2c71a, 0x2c390, 0x2b56e, 0x2b5c6, 0x2b610, 0x2b63e):
        h += byte(0x15, (0, 0x80, 1, 0x81))
    if entry == 0x2c12c:
        h += [dict(a6off=[(0x7e, 1, a), (0x82, 1, b)]) for a, b in ((1, 1), (1, 2))]
    if entry in (0x2c200, 0x2c2ee):
        h += [dict(a6off=[(0x3a, 4, v)]) for v in (0, 0x80000000, 1)]
    if entry in (0x2c3cc, 0x2c3f6):
        h += [dict(a6off=[(0x9e, 4, v)]) for v in (RECORD, RECORD + 2)]
    if entry in (0x2c3a0, 0x2c460, 0x2c52a):
        h += byte(0x5f, (0, 0x80))
    if entry == 0x2c440:
        h += [dict(a6off=[(0x54, 2, v)]) for v in (0, 1)]
    if entry == 0x2c562:
        h += byte(0x7f, (6, 7, 0xff))
    if entry == 0x2c58e:
        h += byte(0x61, (0, 0x40, 0xc0))
    if entry == 0x2c598:
        h += byte(0x5e, (0x18, 0x17))
    if entry in (0x2c66c, 0x2c674, 0x2c690):
        h += byte(0x5e, (0, 0x18, 0x19, 1))
    if entry == 0x2c5ae:
        h += [dict(a6off=[(0x98, 4, v)]) for v in (0, PATH, PATH + 0x54)]
    if entry == 0x2c5ba:
        h += [dict(regs=dict(a0=PATH + 0x54)), dict(regs=dict(a0=PATH))]                           # 2c7fa: WORD ffff, then the rewind WORD fff4
    if entry == 0x2c5e6:
        h += byte(0x86, (0, 1, 2))
    if entry == 0x2c5f4:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2)]
    if entry == 0x2c64c:
        h += [dict(regs=dict(d0=v)) for v in (1, 0x101, 2)]
    if entry == 0x2c6a8:
        h += [dict(a6off=[(0x64, 2, v)]) for v in (0, 1)]
    if entry in (0x2c156, 0x2c33c, 0x2c412, 0x2c274, 0x2c4d4, 0x2c1e0):
        h += [dict(a0off=[(0, 2, v)]) for v in (0, 4, 8, 0xc, 0x40, 0x80)]
    if entry == 0x8d34:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 0x102)]
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their real producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x7c, 0x7f, 0x5e, 0x61, 0x86)] + [(6, off, 2) for off in (0x88, 0x92)]
        succ = static_next(cons) if cons != 0x2ba66 else {0x2ba70}
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry == 0x2b53a:
                hint = dict(a6off=[(0x88, 2, t & 1)], writes=[(0xf001, 1, rng.choice((0, 4)))])
            elif entry in (0x2bac4, 0x2c19c, 0x2c2c8, 0x2c37e, 0x2c438, 0x2c6f8) and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                                   # 49fc6 (end of 2b418): LONG 26(A6) = 0 -> ORI Set
            elif entry == 0x2c612:
                hint = dict(writes=[(0xf000, 1, 0x80 if t % 2 else 0)])                            # 4d766: BYTE 10f000 bit 7 -> ST.B D1 -> ADD.B C Set
            elif entry == 0x2c622 and t % 2:
                hint = dict(a6off=[(0x88, 2, t & 2)], writes=[(0xdcba, 2, 0), (0xdcdc, 1, 0), (0xdce6, 2, 0), (0xdd08, 1, 0), (0x0d19, 1, 0), (0x0e09, 1, 0),
                                                                   (0x0cb8, 4, 0x2b99c), (0x0da8, 4, 0x2b99c)])   # 289e: player callback != 270e -> Set
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(extra=succ), cap=400000)
            if tr is None or cons not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = tr['stop']
            if key not in kept:
                kept[key] = (st, tr)
            if set(kept) >= succ and len(kept) >= (1 if cons == 0x2ba66 else 2):
                break
        require(kept, ('no chain world', hex(entry)))
        missing = succ - set(kept)
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (stop, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], stop, meta=dict(family='chain', entry=entry, consumer=cons, successor=stop)))


def node_fixtures(world, add, record):
    """Installed callbacks and state entries run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first
    unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            st = world.make(entry, base.stop, flds)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
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
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b3a PC')))
    add(U.Fixture('error-odd-pc', U.with_host_writes(st, pc=0x2ba51), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'objects b3a caller requires known carry')))
    a6 = st['regs']['a6']
    # odd node: MOVE.L #0,64(A6) / TST.W 92(A6) at an odd A6
    add(U.Fixture('error-2c31a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x2c31a), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    add(U.Fixture('error-2c582-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x2c582), [], SENTINEL, ('error', 'program bus requires even WORD/LONG address')))
    # odd record pointer: MOVE.L 10(A4) with LONG 9e odd
    add(U.Fixture('error-2c250-odd-record', U.with_host_writes(st, [((a6 + 0x9e) & 0xffff, 4, RECORD + 1)], pc=0x2c250), [], SENTINEL, ('error', 'program bus requires even WORD/LONG address')))


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x2c250, 0x2c2a8, 0x2b63e, 0x8d72)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0x3a) & 0xffff, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
