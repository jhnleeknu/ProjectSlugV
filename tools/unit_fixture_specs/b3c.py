"""V1 fixture spec of the animation-machine unit B3c (engine/src/animation_machine_objects_b3c.cpp, 71 block starts).

Blocks: the 28ae children of the N28 range-outside chain 2d7be..2d8b8 (20; installs 2d810 / 2d8a0), 2d916..2d9dc (14; installs 2d98e) and 2db06..2dbda
(16; installs 2dbac), and the callee 1c114..1c1ba (15) with its shared tail 2291a..2296a (6).  Contract: docs/analysis/animation-machine-deferred-b3c-contract.md.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the six consumers is entered directly.  The world is the natural N28 node (callback 2b99c) of the D1 seeds 116/117
            (frame 2; node A6, A5, bank, RAM natural) with a declared host edit of D0-D7, A0 := a natural node (the parent: LONG c(A6) := A0 for the child
            blocks) or a player structure 100cb8 / 100da8 (the 1c114 blocks; A4 := its LONG 8c), A1 / A2 / A4 := natural nodes, the node / parent / player /
            record fields the reachable blocks read (values from a seeded generator), LONG 22(A6) := natural or a real bank-window pointer, LONG 3e(A6) := 0 or
            a natural node, and PC := the block start.  Stop: the first PC outside the unit (a callee, the sentinel return LONG, JMP 2a00 / 491b6).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 289e -> 1c128 (entry 1c122), 288c -> 2dbb2 (2dbac), 49fc6 -> 2d85e 2d8ac 2d9c6 2dbce.  Native
            branches on the real flags, the C++ branches on the known C.  Stop: the consumer's successor (or the first unrouted PC of the run).
  node      the installed callbacks and the child entries as node callbacks ((A6) := entry, PC := entry) run through every routed callee up to the dispatcher
            return or the first unrouted PC.
  callee    1c114 entered as a subroutine (return LONG = sentinel) through 289e / 2986 / 4c2fa / 491b6 up to the sentinel or the first unrouted PC.  A native
            run that passes the 28ae failure path (290e) is an expected-error fixture: the C++ 2986 wrapper stops at 298e with 'cue wrapper failure requires
            known caller X' (buffer_cue decision 1, contract decision 4), failing PC 298e.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the six consumers, odd node / parent / player / stack pointers, failures after
            executed stores (2db32 -> 2db88 with an odd A5, 2d816 -> 2d822 with an odd A6): checked error, state preserved.  Every error row records its failing
            PC (Fixture fail_pc, review 0264 L-1); when it differs from the entry a paired 'match' row runs the same state with stop = the failing PC.
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b / B2d / B3a / B3b specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node: the owner of the chain whose children / callee this unit is
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x1c114, 0x1c1ba), (0x2291a, 0x2296a), (0x2d7be, 0x2d8b8), (0x2d916, 0x2d9dc), (0x2db06, 0x2dbda)]
CALLEE_RANGES = [(0x1c114, 0x1c1ba), (0x2291a, 0x2296a)]
STARTS = [int(x, 16) for x in (
    '1c114 1c11e 1c122 1c128 1c12c 1c12e 1c13e 1c146 1c148 1c14c 1c170 1c172 1c18a 1c1a6 1c1ae '
    '2291a 22920 22934 22944 2294c 2295c '
    '2d7be 2d7da 2d7f4 2d80a 2d810 2d816 2d822 2d830 2d846 2d848 2d85e 2d862 2d868 2d87a 2d89a 2d8a0 2d8a6 2d8ac 2d8b0 2d8b6 '
    '2d916 2d924 2d932 2d95c 2d978 2d982 2d988 2d98e 2d9b0 2d9b2 2d9c0 2d9c6 2d9ca 2d9da '
    '2db06 2db24 2db32 2db58 2db6a 2db86 2db88 2dba6 2dbac 2dbb2 2dbb6 2dbbc 2dbc8 2dbce 2dbd2 2dbd8').split()]
CONSUMERS = (0x1c128, 0x2d85e, 0x2d8ac, 0x2d9c6, 0x2dbb2, 0x2dbce)
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1c122, 0x1c128), (0x2d848, 0x2d85e), (0x2d8a6, 0x2d8ac), (0x2d9c0, 0x2d9c6), (0x2dbac, 0x2dbb2), (0x2dbc8, 0x2dbce))
CHAIN_49FC6 = (0x2d848, 0x2d8a6, 0x2d9c0, 0x2dbc8)
# installed callbacks and the child entries (node callbacks); the callee entry
NODE_ENTRIES = (0x2d7be, 0x2d810, 0x2d8a0, 0x2d916, 0x2d98e, 0x2db06, 0x2dbac)
CALLEE = 0x1c114
PLAYERS = (0x100cb8, 0x100da8)          # LEA -7348(A5) / -7258(A5) with A5 = 108000
FAIL_28AE = 0x290e                      # 28ae failure path (LEA -7168(A5),A0; ANDI #fe,CCR)
BANK_POINTERS = (0x2996ec, 0x29c910)    # the real LONGs of 200094 / 20009c in the 200000 bank (LONG 22(A6))
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x3e, 0x78, 0x94, 0x98, 0x9e)   # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x16, 0x17, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0x10, 0x40, 0x80, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff20000, 0xffffffff, 0x160000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
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
    require(len(_ROUTE) >= 113, ('routing rules', len(_ROUTE)))


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


def mine(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


def in_callee(pc):
    return any(lo <= pc < hi for lo, hi in CALLEE_RANGES)


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
    """Memory fields (reg, displacement, size) read or written by the blocks reachable from `start` (An relative)."""
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
def trace(state, outside, cap=CAP_INSN):
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
def _long(ram, addr):
    o = addr & 0xffff
    return int.from_bytes(bytes(ram[o:o + 4]), 'big')


def _ram_pointer(v):
    return 0x100000 <= v < 0x110000 and not v & 1


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
        ram = st['ram']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.4:
            regs['d0'] = rng.choice((regs['d0'], rng.randrange(0x20), rng.randrange(0x100), 0x10000))
        writes = []
        if in_callee(entry):
            if entry == CALLEE:
                player = PLAYERS[0] if not regs['d0'] & 0xffff else PLAYERS[1]      # 1c114: TST.W D0 selects the record
            else:
                player = rng.choice(PLAYERS)
            regs['a0'] = player
            a4 = _long(ram, player + 0x8c)
            if not _ram_pointer(a4) or rng.random() < 0.3:
                a4 = self.pointer()
                writes.append(((player + 0x8c) & 0xffff, 4, a4))
            regs['a4'] = a4
            writes.append((player & 0xffff, 4, rng.choice((0x270e, 0x270e, _long(ram, player), 0x2b99c))))   # 289e: LONG (A0) = 270e -> C Clear
            writes.append(((player + 0x9e) & 0xffff, 1, rng.choice((0, 1, 2, 3, 3, rng.getrandbits(8) & 3))))  # 2284c index (4 LONGs)
            writes.append(((a4 + 6) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4, 5, 0xff))))                          # child table index (< 4 else 0)
        else:
            regs['a0'] = self.pointer()
            regs['a4'] = self.pointer()
            if rng.random() < 0.9:
                writes.append(((a6 + 0xc) & 0xffff, 4, regs['a0']))                         # LONG c(A6): the parent
        regs['a1'] = rng.choice((self.pointer(), self.pointer(), 0))
        regs['a2'] = self.pointer()
        if entry in (0x2d932,):
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(9)                        # 2d904 table index (9 WORDs)
        base_of = {6: a6, 0: regs['a0'], 4: regs['a4'], 5: regs['a5'], 1: regs['a1'], 2: regs['a2']}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared below
            if reg in (0, 4) and in_callee(entry) and disp in (0x8c, 0x9e, 0x6, 0x0):
                continue                                        # player record pointer / the table indices are declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice((0, 0, self.pointer()))))
        if rng.random() < 0.6:
            writes.append(((a6 + 0x22) & 0xffff, 4, rng.choice(BANK_POINTERS)))
        writes.append(((regs['a0'] + 0x7c) & 0xffff, 1, rng.choice((0, 1, 4, 8, 12, 16, rng.randrange(17)))))   # parent BYTE 7c (17-entry tables)
        writes.append(((a6 + 0x7c) & 0xffff, 1, rng.choice((0, 1, 8, 16, rng.randrange(17)))))
        writes.append(((regs['a0'] + 0x8a) & 0xffff, 2, rng.choice((0, 1, 2, 3))))                                  # parent WORD 8a (2d8fc / 1d1b0)
        sp = regs['a7']
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
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
    require(len(STARTS) == 71 and len(STARTS_SET) == 71, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b3c_block', ('start is not routed to b3c', hex(s), unit_of(s)))
    rng = random.Random(0xB3C)
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
    callee_fixtures(world, add, record)
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
    sys.stderr.write('b3c spec: %d fixtures, visited %d/71, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b3c: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('b3c: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit.  Every hint world is kept as a
    fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    pbyte = lambda off, vals: [dict(a0off=[(off, 1, v)]) for v in vals]
    if entry == 0x1c114:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x10000, 0xffff, 0x8000)]
    if entry == 0x1c12e:
        h += [dict(writes=[(0xf001, 1, v)]) for v in (0, 4, 0xfb, 0xff)]
    if entry in (0x1c13e, 0x1c148):
        h += [dict(regs=dict(a4=n), writes=[((n + 7) & 0xffff, 1, v)]) for n in (0x104d92,) for v in (0, 1, 0x80, 0xff)]
    if entry == 0x1c14c:
        h += [dict(regs=dict(a4=0x104d92), writes=[(0x4d98, 1, v)]) for v in (0, 1, 3, 4, 0xff)]
    if entry in (0x1c18a, 0x2d830, 0x2d98e, 0x2db6a):
        h += byte(0x15, (0, 1, 0x80, 0xff))
    if entry == 0x1c1a6:
        h += [dict(regs=dict(d0=v, d2=w)) for v, w in ((0x20, 0x0001), (0x80, 0x8000), (0, 0))]
    if entry == 0x22920:
        h += [dict(a6off=[(0x3e, 4, 0)]), dict(a6off=[(0x3e, 4, 0x104d92)])]
    if entry == 0x22944:
        h += [dict(regs=dict(a1=0)), dict(regs=dict(a1=0x104d92))]
    if entry == 0x2d7da:
        h += pbyte(0x15, (0, 0x7f, 0x80, 0xff))
    if entry == 0x2d816:
        h += byte(0x13, (0, 1, 0x7f, 0xfe, 0xff))
    if entry == 0x2d822:
        h += [dict(regs=dict(d0=d), a6off=[(0x3a, 2, v)]) for d, v in ((1, 0x7fff), (0xff, 0x8000), (0x80, 0xffff), (0x8000, 0x8000), (0xffff, 1))]
    if entry == 0x2d868:
        h += byte(0x13, (0, 1, 0x7f, 0x80, 0xfe, 0xff))
    if entry == 0x2d932:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 8, 0xff00)]
    if entry == 0x2d95c:
        h += [dict(a0off=[(0x8a, 2, v)]) for v in (0, 1, 2, 3)]
    if entry in (0x2d98e, 0x2db32):
        h += pbyte(0x7c, (0, 8, 16))
    if entry == 0x2db32:
        h += [dict(a0off=[(0x36, 4, v)]) for v in (0, 0x7fffffff, 0x80000000, 0xffffffff)]
    if entry == 0x2db58:
        h += byte(0x7d, (0, 1, 4, 5, 0x84, 0xff))
    if entry == 0x2db6a:
        h += byte(0x7c, (0, 1, 8, 16))
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x13, 0x7c)] + [(6, off, 2) for off in (0x88, 0x1e)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in CHAIN_49FC6 and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                       # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry == 0x2dbac:
                hint = dict(a6off=[(0xc, 4, 0)]) if t % 3 == 0 else None                 # 288c: LONG c(A6) = 0 -> ORI Set; else 289e on the parent
            st = world.make(entry, SENTINEL, flds, hint)
            if entry == 0x2dbac and t % 3 == 1:
                st = U.with_host_writes(st, [(st['regs']['a0'] & 0xffff, 4, 0x270e)])   # 289e on the parent: LONG = 270e -> Clear
            tr = trace(st, first_unrouted(extra=succ), cap=400000)
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


def callee_fixtures(world, add, record):
    """1c114 as a subroutine (return LONG = sentinel) through 289e / 2986 / 4c2fa / 491b6.  A native run through the 28ae failure path (290e) is an expected
    error of the C++ 2986 wrapper at 298e (buffer_cue decision 1)."""
    flds = fields_of(CALLEE)
    kept = {}
    for t in range(160):
        st = world.make(CALLEE, SENTINEL, flds)
        tr = trace(st, first_unrouted(), cap=400000)
        if tr is None:
            continue
        record(tr['pcs'] + [tr['stop']])
        failed = FAIL_28AE in tr['pcs']
        key = (tr['stop'], failed, 0x1c12e in tr['pcs'], 0x1c14c in tr['pcs'], 0x1c1a6 in tr['pcs'])
        if key in kept:
            continue
        kept[key] = (st, tr, failed)
        if len(kept) >= 8:
            break
    require(kept, 'no callee world')
    for i, (key, (st, tr, failed)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
        if failed:
            add(U.Fixture('callee-1c114-%d-28ae-failure' % i, st, [], SENTINEL, ('error', 'cue wrapper failure requires known caller X'), fail_pc=0x298e,
                          meta=dict(family='callee', fail_pc=0x298e, deliberate='2986 caller-X (buffer_cue decision 1)')))
            add(U.Fixture('callee-1c114-%d-to-298e' % i, st, [], 0x298e, meta=dict(family='callee', stop=0x298e)))
        else:
            add(U.Fixture('callee-1c114-%d' % i, st, [], tr['stop'], meta=dict(family='callee', stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET))))


def error_fixtures(bases, add):
    """Checked errors with the failing PC (Fixture fail_pc and meta, review 0264 L-1).  A failing PC that differs from the entry gets a paired 'match' row with stop
    = the failing PC (both sides stop exactly there)."""
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)

    def err(name, state, text, fail_pc):
        add(U.Fixture('error-' + name, state, [], SENTINEL, ('error', text), fail_pc=fail_pc, meta=dict(family='error', fail_pc=fail_pc)))
        if fail_pc != state['pc']:
            add(U.Fixture('failpc-' + name, state, [], fail_pc, meta=dict(family='failpc', fail_pc=fail_pc)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects b3c PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x2d7bf), 'unaligned animation machine PC', 0x2d7bf)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects b3c caller requires known carry', pc)
    a6 = st['regs']['a6']
    odd_word = 'program bus requires even WORD/LONG address'
    # odd node: MOVE.W #e2,20(A6) at an odd A6 (the entry block fails)
    err('2db06-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x2db06), 'invalid animation machine write size/alignment', 0x2db06)
    # odd parent: MOVE.W 8a(A0),D0 with LONG c(A6) odd
    err('2d916-odd-parent', U.with_host_writes(st, [((a6 + 0xc) & 0xffff, 4, a6 + 1)], pc=0x2d916), odd_word, 0x2d916)
    # odd player record: MOVEA.L 8c(A0),A4 with A0 odd
    err('1c12e-odd-player', U.with_host_writes(st, regs=dict(a0=PLAYERS[0] + 1), pc=0x1c12e), odd_word, 0x1c12e)
    # failures after executed blocks: 2d816 (BYTE 13 != ff) -> 2d822 reads WORD 3a of an odd A6; 2db32 stores WORD 2c / BYTE 7d 7c (and 2db58) and
    # 2db88 then reads WORD 14(A1) with A1 = an odd A5 + 538e
    st13 = U.with_host_writes(st, [((a6 + 1 + 0x13) & 0xffff, 1, 0x10)])
    err('2d816-odd-node', U.with_host_writes(st13, regs=dict(a6=a6 + 1), pc=0x2d816), odd_word, 0x2d822)
    stp = U.with_host_writes(st, [((a6 + 0xc) & 0xffff, 4, a6), ((a6 + 0x7c) & 0xffff, 1, 3)])
    err('2db32-odd-a5', U.with_host_writes(stp, regs=dict(a5=st['regs']['a5'] + 1), pc=0x2db32), odd_word, 0x2db88)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x2d822, 0x2db6a, 0x22934, 0x1c14c)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0x3a) & 0xffff, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
