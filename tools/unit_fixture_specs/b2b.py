"""V1 fixture spec of the animation-machine unit B2b (engine/src/animation_machine_objects_b2b.cpp, 209 block starts).

Blocks: the orphan chains 3383c, 3a4a4 / 3a4be / 3a4da / 3a5be, 3b424 / 3b446, 4bfc0, 38d56, 39f9c / 3a0dc (with the 27-slot BRA.W table 3a0f4), 3acd6, 4c390 / 4c3a2 / 4c3cc,
the slot helpers 4d418 / 4d4b4 and the 38 blocks of the shared leaf helpers 4c2fa 4d6b4 4d734 4d98a 4d9ba 4eea2 (+4f08a) 4ff96 d3d7c.  4b6f4 and 4c3ba stay unrouted
(3b5a6 and the 82(A6) chain 3a60a are routed by B2c; their former unrouted probes are work-RAM PCs 10fe00..10fe04).

Fixture families (everything is native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start is entered directly.  The world is a natural N-pass node state of the D1 seeds 116/117 (frame 2: N31 38c36, N33 3b166, N28 2b99c, N30a 331d8, N29 30de4,
            N22 3d32c; the node A6, A5, bank and RAM are natural) with a declared host edit of D0-D7, A0-A4, the node and slot fields the reachable blocks of the unit read (values drawn
            from a seeded generator) and PC := the block start.  The stop is the first PC outside the unit (a callee, the sentinel return LONG, a JMP target).  Worlds are kept
            per entry while they add a new successor of the entry block (both sides of every branch of the block).
  coverage  worlds that reach a conditional branch outcome (of any block of the unit, including the 27 slots of 3a0f4) that the block fixtures did not take.
  chain     producer helpers with a REAL consumer return LONG (4d418 -> 31a04 33212 38c5e 3a384 3d358; 3a4da -> 39128 39c30; 3b424 / 3b446 -> 3902c 3a202; 4c390 -> 2c7a0) and the
            call chains whose C is produced by a routed callee and consumed inside the unit (289e -> 4d438, 4d6b4 -> 3a4ec, 288c -> 3ad26, 49fc6 -> 3ad3c, 28ae -> 38d70, 3b334 -> 38dbe):
            native branches on the real flags, the C++ branches on the known C.  Stop: the first PC outside the unit and the consumer block.
  error     every even non-start PC of the unit ranges, the PCs without an executor (work RAM 10fe04 10fe08 10fe0a..10fe16), an odd PC, Unknown C at the six consumers, a
            JSR (A0) target outside the routing (work-RAM 10fe00), an odd JSR (A0) target, an odd LONG write, a work-RAM rollback probe 10fe02: checked error, state preserved.
  negative  C++ input differs from the native input in one RAM bit / one register / the queue: the comparison must report it.
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
NODE_INDEX = (4, 6, 7, 11, 13, 18, 21)  # N31 38c36, N33 3b166, N28 2b99c, N30a 331d8, N30a 34650, N29 30de4, N22 3d32c in frame 2 of seeds 116/117
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x3383c, 0x338f8), (0x33940, 0x33958), (0x38d56, 0x38dd4), (0x39f9c, 0x3a048), (0x3a0dc, 0x3a1e0), (0x3a4a4, 0x3a4d6), (0x3a4da, 0x3a5d2),
          (0x3acd6, 0x3ad48), (0x3b424, 0x3b458), (0x4bfc0, 0x4c020), (0x4c2fa, 0x4c340), (0x4c390, 0x4c3ba), (0x4c3cc, 0x4c3de), (0x4d418, 0x4d508),
          (0x4d6b4, 0x4d6f2), (0x4d734, 0x4d766), (0x4d98a, 0x4d9a2), (0x4d9ba, 0x4d9d6), (0x4eea2, 0x4eef4), (0x4f08a, 0x4f0c4), (0x4ff96, 0x4ffba), (0xd3d7c, 0xd3d9c)]
STARTS = [int(x, 16) for x in (
    '3383c 33846 3384e 33858 3385e 3387a 33896 338b2 338de 338e8 338f2 33940 33948 33950 33952 '
    '3a4a4 3a4b6 3a4b8 3a4be 3a4c6 3a4ce 3a4d0 3a4da 3a4e2 3a4ec 3a4f0 3a4fa 3a502 3a506 3a51e 3a528 3a52e 3a542 3a544 3a560 3a570 3a574 3a584 3a5a0 3a5a6 3a5b2 3a5b8 3a5be 3a5ca '
    '3b424 3b42e 3b446 3b448 3b452 3b456 4bfc0 4bfc4 4bfc8 4bfce 4bfd4 4bfda 4bfee 4bffe 4c006 4c016 '
    '38d56 38d60 38d70 38d7a 38d80 38d88 38d8c 38d90 38d98 38d9c 38da6 38db0 38db6 38dba 38dbe 38dc2 38dc8 38dd0 '
    '39f9c 39fa6 39fb0 39fba 39fc0 39fdc 39ff8 3a014 3a03a 3a044 3a0dc 3a0e8 3a0f4 3a0f8 3a0fc 3a100 3a104 3a108 3a10c 3a110 3a114 3a118 3a11c 3a120 3a124 3a128 3a12c 3a130 3a134 3a138 '
    '3a13c 3a140 3a144 3a148 3a14c 3a150 3a154 3a158 3a15c 3a160 3a166 3a16c 3a176 3a180 3a188 3a192 3a196 3a1a0 3a1aa 3a1ae 3a1b2 3a1b8 3a1c6 3a1da '
    '3acd6 3ad06 3ad14 3ad1a 3ad20 3ad26 3ad2a 3ad30 3ad36 3ad3c 3ad40 3ad46 4c390 4c398 4c3a2 4c3aa 4c3cc 4c3d4 '
    '4d418 4d41e 4d42a 4d432 4d438 4d43c 4d446 4d44e 4d454 4d476 4d48c 4d490 4d4ac 4d4b4 4d4c2 4d4cc 4d4d8 4d4e0 4d4e8 4d502 4d506 '
    '4c2fa 4c2fe 4c308 4c30a 4c32a 4d6b4 4d6c0 4d6c6 4d6cc 4d6d4 4d6d8 4d6e0 4d6ec 4d734 4d73a 4d742 4d746 4d750 4d75e 4d98a 4d990 4d998 4d99c 4d9ba 4d9c6 4d9ca '
    '4eea2 4eeac 4eeb6 4eebc 4eeea 4f08a 4f0a8 4f0b8 4ff96 4ffb0 d3d7c d3d92').split()]
CONSUMERS = (0x4d438, 0x3a4ec, 0x3ad26, 0x3ad3c, 0x38d70, 0x38dbe)
# work-RAM PCs without an executor (review 0264 M-3; the ROM neighbours 4c3ba 4c3c2 3a4d6 3a4d8 4b6f4 3a048 3a0d2 are 10fe0a..10fe16 in this order);
# the exact range ends are asserted against the routing in build().
UNROUTED_NEIGHBOURS = (0x10fe0a, 0x10fe0c, 0x10fe0e, 0x10fe10, 0x10fe04, 0x10fe08, 0x10fe12, 0x10fe14, 0x10fe16)
TABLE = 0x3a0f4
# entries whose RTS pops stack data first: offset of the return LONG from A7 at the entry
RET_AT = {0x33948: 2, 0x3a4c6: 2, 0x4c32a: 4, 0x4ffb0: 4, 0x4eeea: 8, 0x4d4c2: 8}
STARTS_SET = set()
# producer entries with real consumer return LONGs: entry -> return PCs (the consumer block is allowed in the trace and its successors are the stop)
CHAIN_RETURNS = {0x4d418: (0x31a04, 0x33212, 0x38c5e, 0x3a384, 0x3d358), 0x4d490: (0x31a04, 0x33212, 0x38c5e, 0x3a384), 0x4d4ac: (0x31a04, 0x33212, 0x38c5e, 0x3a384),
                 0x3a4da: (0x39128, 0x39c30), 0x3a4a4: (0x38c5e, 0x3a384), 0x3b424: (0x3902c, 0x3a202), 0x3b446: (0x3902c, 0x3a202), 0x4c390: (0x2c7a0,),
                 0x3a4e2: (0x39128, 0x39c30)}
# call chains whose C is made by a routed callee and read inside the unit: entry -> description (the trace runs through every routed PC)
PRODUCER_CHAINS = (0x4d432, 0x3a4e2, 0x3ad20, 0x3ad36, 0x38d60, 0x38dba)

VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x11, 0x12, 0x18, 0x1a, 0x1b, 0x1c, 0x20, 0x40, 0x60, 0x7f, 0x80, 0x81, 0xfe, 0xff)
VW = (0, 1, 2, 0x10, 0x100, 0x1e, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 0x10000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff20000, 0xffffffff, 0x2800, 0x270e)
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
    require(len(_ROUTE) >= 99, ('routing rules', len(_ROUTE)))


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
    """Instruction records (addr, mnemonic, op_str, size) of the block at `start`: up to a branch / call / return or the next block start."""
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
    """Static successors of the entry block (None = computed: RTS / JSR (A0) / table)."""
    last = block_instrs(start)[-1]
    a, mn, op, size, _ = last
    if BCC.match(mn):
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and 'pc,' not in op:
        return {target(op)}
    if mn == 'jmp' and 'd0' in op:
        return {TABLE + 4 * k for k in range(27)}
    if mn in ('rts', 'jsr'):
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
    """Run the original from state.pc natively until `outside(pc)` is true (checked from the second instruction on).  -> dict(pcs, stop, regs) or None."""
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
    def __init__(self, bases, rng):
        self.bases, self.rng = bases, rng

    def pointer(self, a5):
        rng = self.rng
        pool = [0] + [0x1009a8 + 0xc4 * k for k in range(14)] + [a5 + 0x5cba, a5 + 0x5ce6, a5 + 0x8cb8 - 0x10000, a5 + 0x8da8 - 0x10000, a5 + 0x5c8e]
        return rng.choice(pool)

    def value(self, size, a5):
        rng = self.rng
        if size == 1:
            return rng.choice(VB)
        if size == 2:
            return rng.choice(VW + tuple(rng.randrange(65536) for _ in range(2)))
        k = rng.random()
        if k < 0.45:
            return self.pointer(a5)
        if k < 0.8:
            return rng.choice(VL)
        return rng.randrange(1 << 32)

    def make(self, entry, ret, flds, hint=None):
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4)), a5) if rng.random() < 0.9 else rng.randrange(1 << 32)
        for k in ('a0', 'a1', 'a2', 'a3', 'a4'):
            regs[k] = self.pointer(a5) if rng.random() < 0.9 else regs[k]
        if rng.random() < 0.5:
            regs['a4'] = a5 + rng.choice((0x5cba, 0x5ce6))
        if rng.random() < 0.5:
            regs['a0'] = (a5 + rng.choice((0x8cb8, 0x8da8)) - 0x10000) & 0xffffffff
        writes = []
        for kind, reg, disp, size in flds:
            if rng.random() < 0.55:
                continue
            base_addr = disp if kind == 'abs' else (regs['a%d' % reg] + disp) & 0xffffffff
            if not (0x100000 <= base_addr < 0x200000) or (size > 1 and base_addr & 1):
                continue
            if 0xee00 <= (base_addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((base_addr & 0xffff, size, self.value(size, a5) & ((1 << (8 * size)) - 1)))
        if rng.random() < 0.2 and 0x100000 <= regs['a4'] < 0x110000 and not regs['a4'] & 1:
            writes.append((regs['a4'] & 0xffff, 2, regs['a6'] & 0xffff))        # (A4).W == A6.W (4d4e0, 4d44e)
        sp = regs['a7']
        for off in range(0, RET_AT.get(entry, 0) - 3, 4):
            writes.append(((sp + off) & 0xffff, 4, self.pointer(a5)))       # stack data popped before the RTS
        writes.append(((sp + RET_AT.get(entry, 0)) & 0xffff, 4, ret))
        if hint and 'slot' in hint:
            delta = {'gt': 1, 'lt': -1, 'eq': 0}[hint['slot']]
            for off in (0x5cba, 0x5ce6):
                writes.append(((a5 + off) & 0xffff, 2, ((regs['a6'] & 0xffff) + delta) & 0xffff))        # (slot).W relative to A6.W (4d4e0 CMP.W borrow)
        if hint:
            writes += [((regs['a6'] + off) & 0xffff, size, val) for off, size, val in hint.get('a6off', [])]
            for w in hint.get('writes', []):
                if w[0] == 'sp':                                  # ('sp', offset, value): a LONG at A7 + offset
                    writes.append(((sp + w[1]) & 0xffff, 4, w[2]))
                else:
                    writes.append(w)
            if 'slot_byte' in hint:
                writes.append(((regs['a4'] + hint['slot_byte'][0]) & 0xffff, 1, hint['slot_byte'][1]))
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
    require(len(STARTS) == 209 and len(STARTS_SET) == 209, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for pc in UNROUTED_NEIGHBOURS:
        require(unit_of(pc) is None, ('probe is routed', hex(pc)))
    for lo, hi in RANGES:
        require(unit_of(hi) != 'animation_objects_b2b_block' and unit_of(lo - 2) != 'animation_objects_b2b_block', ('range end routed to b2b', hex(lo), hex(hi)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b2b_block', ('start is not routed to b2b', hex(s), unit_of(s)))
    rng = random.Random(0xB2B)
    bases = []
    for case in SEEDS:
        for k in NODE_INDEX:
            fx = U.seed_node_fixture(case, FRAME, node=k, name='base')
            require(fx is not None, ('missing node', case, k))
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

    def outside_unit(allowed=()):
        al = set(allowed)
        return lambda pc: not mine(pc) and pc not in al

    def record(entry_pcs):
        visited.update(entry_pcs)
        for i in range(len(entry_pcs) - 1):
            pc = entry_pcs[i]
            if pc in cond_points:
                covered.add((pc, entry_pcs[i + 1]))

    # branch outcomes of the unit (both sides of each Bcc, the 27 slots of the table jump)
    for s in STARTS:
        a, mn, op, size, _ = block_instrs(s)[-1]
        if BCC.match(mn):
            cond_points[a] = {target(op), a + size}
        elif mn == 'jmp' and 'd0' in op:
            cond_points[a] = {TABLE + 4 * k for k in range(27)}
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
                kept[('h', t)] = (st, tr)                       # declared boundary / table worlds are always kept
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
        for i, key in enumerate(sorted(kept, key=lambda k: (0, k) if isinstance(k, int) else (1, k[1]))):
            st, tr = kept[key]
            if id(st) in seen_worlds:
                continue
            seen_worlds.add(id(st))
            add(U.Fixture('block-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='block', entry=entry, successor=tr['pcs'][n] if len(tr['pcs']) > n else tr['stop'])))
        if needed and len(needed) > 1:
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)))
            if missing:
                out_missing.append((entry, missing))
    chain_fixtures(world, add, outside_unit, record)
    routed_target_fixtures(world, add, record)
    carry_fixtures(world, add, record)
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
    negative_fixtures(bases, out, add)
    META['carry_oracle'] = carry_oracle(out)
    META['visited_starts'] = len(set(STARTS) & visited)
    META['chain_only'] = [hex(x) for x in CONSUMERS]
    META['out_missing'] = out_missing
    META['unreachable'] = unreachable
    META['stats'] = stats
    return out


out_missing = []
unreachable = []
META = {}


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b2b: carry oracle skipped (no harness binary)\n')
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
            tr = trace(fx.state, lambda pc, stop=fx.stop: pc == stop)
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('b2b: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the 27 table slots and the boundary values of the compares / tests of the unit.
    Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    if entry == 0x3a0e8:
        h += [dict(regs=dict(d0=k)) for k in range(27)] + [dict(regs=dict(d0=0x1b)), dict(regs=dict(d0=0xff))]
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    if entry == 0x3a0dc:
        h += byte(0x5e, (0x00, 0x18, 0x1a, 0x1b, 0x1c, 0xff))                       # CMPI.B #1b,D0 / BCC (BYTE 5e)
    if entry == 0x3a4f0:
        h += byte(0x9f, (0x10, 0x11, 0x12))                                          # CMPI.B #11,9f(A6) / BCC
    if entry == 0x3a16c:
        h += byte(0x9f, (7, 8, 9))                                                    # CMPI.B #8,9f(A6) / BCC
    if entry == 0x3a166:
        h += [dict(regs=dict(d0=v)) for v in (0x7fff, 0x8000, 0x10000, 0xffff, 0x80000000)]   # TST.W D0 / BMI
    if entry == 0x4bfce:
        h += [dict(regs=dict(d7=v)) for v in (0x7f, 0x80, 0xff, 0x100, 0x12345640, 0x12345680)]   # ADD.B D7,D7 / BCC
    if entry == 0x4c2fe:
        h += [dict(regs=dict(d0=v, d1=0xa5a5a5a5)) for v in (0, 1, 2, 3, 0x102, 0xff)]    # SUB.B D0,D1 / BCC (borrow at D0.B > 2)
    if entry == 0x4d44e:
        h += [dict(regs=dict(d0=a, d7=b)) for a, b in ((0x1234, 0x1234), (0x1234, 0x1235), (0x11234, 0x21234), (0, 0))]   # CMP.W D0,D7 / BNE
    if entry in (0x4d418, 0x4d4c2, 0x4d6c6, 0x4d734, 0x4d98a, 0x4d9ba, 0x4eea2):
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x80, 0x100, 0x10000, 0xff)]        # TST.B D0 / TST.W D0 (byte zero, word non-zero)
    if entry == 0x4d4c2:
        h += [dict(writes=[('sp', 0, v)]) for v in (0, 1, 0x100, 0x80)]       # the popped D0
    if entry in (0x33948, 0x3a4c6):
        h += [dict(regs=dict(d0=v)) for v in (0x7f, 0x80, 0xff, 0)]                    # TST.B D0 / BPL
    if entry == 0x3a4a4 or entry == 0x3a4f0 or entry == 0x3a52e or entry == 0x3a584 or entry == 0x3b448:
        h += byte(0x15, (0, 1, 0x80, 0x81))                                            # BTST.B #0,15(A6) / #7,15(A6)
    if entry in (0x4d43c, 0x4d746):
        h += byte(0x61, (0x7f, 0x80))                                                   # BTST.B #7,61(A0 / A6)
    if entry == 0x4d6d8:
        h += [dict(slot_byte=(0x25, v)) for v in (0, 1, 2, 0xff)]
    if entry == 0x4d6b4:
        h += [dict(writes=[(0x10f001, 1, v)]) for v in (0, 3, 4, 5)]
    return h


def node_of(st):
    return st['regs']['a6']


def chain_fixtures(world, add, outside_unit, record):
    rng = world.rng
    # producers with REAL consumers (return LONG = consumer block)
    for entry, rets in sorted(CHAIN_RETURNS.items()):
        flds = fields_of(entry)
        for ret in rets:
            cons = block_instrs(ret)
            allowed = [a for a, _, _, _, _ in cons]
            kept = {}
            for t in range(MAX_TRIES):
                st = world.make(entry, ret, flds)
                # the consumer reads the C of the producer: more stack for MOVEM.L (A7)+,D0 consumers is natural stack content.
                tr = trace(st, outside_unit(allowed))
                if tr is None:
                    continue
                record(tr['pcs'] + [tr['stop']])
                if tr['stop'] not in kept:
                    kept[tr['stop']] = (st, tr)
                if len(kept) >= 2:
                    break
            for i, (stop, (st, tr)) in enumerate(sorted(kept.items())):
                add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, ret, i), st, [], stop, meta=dict(family='chain', entry=entry, consumer=ret)))
    # call chains: the C is produced by a routed callee and read by a consumer inside the unit
    for entry in PRODUCER_CHAINS:
        flds = fields_of(entry) + [('reg', 6, off, 4) for off in (0xc, 0x82)] + [('reg', 6, off, 1) for off in (0x15, 0x61, 0x62)]
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry == 0x3ad20 and t % 3 == 0:
                hint = dict(a6off=[(0xc, 4, rng.choice((0x1009a8, 0x100a6c)))])     # 288c: c(A6) -> an idle node (callback 270e): C clear
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL, cap=4000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            visited = tuple(sorted(set(CONSUMERS) & set(tr['pcs'])))
            succ = None
            for i, pc in enumerate(tr['pcs'][:-1]):
                if pc in CONSUMERS:
                    succ = tr['pcs'][i + 1]
            key = (succ, tr['stop'])
            if succ is not None and key not in kept:
                kept[key] = (st, tr)
            if len(kept) >= 2:
                break
        require(kept, ('no chain world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-call-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='chain-call', entry=entry, consumer_successor=key[0])))


def carry_fixtures(world, add, record):
    """4d4e0 / 4d4b4 return the borrow of CMP.W (A4),D7: both borrow outcomes and the equal case, both slots."""
    for entry, second in ((0x4d4e0, 0), (0x4d4e0, 1), (0x4d4b4, 0), (0x4d4b4, 1)):
        flds = fields_of(entry)
        for rel in ('gt', 'lt', 'eq'):
            for t in range(MAX_TRIES):
                hint = dict(slot=rel, regs=dict(d0=second))
                st = world.make(entry, SENTINEL, flds, hint)
                a5 = st['regs']['a5']
                if entry == 0x4d4e0:
                    st = U.with_host_writes(st, regs=dict(a4=a5 + (0x5ce6 if second else 0x5cba)))
                tr = trace(st, lambda pc: not mine(pc))
                if tr is None or tr['stop'] != SENTINEL:
                    continue
                record(tr['pcs'] + [tr['stop']])
                add(U.Fixture('carry-%05x-%d-%s' % (entry, second, rel), st, [], tr['stop'], meta=dict(family='carry', entry=entry, relation=rel, slot=second)))
                break
            else:
                require(False, ('no carry world', hex(entry), rel))


def routed_target_fixtures(world, add, record):
    """3a5be JSR (A0) with the routed target 3a5d2 (N33): the whole callee runs on both sides up to the sentinel."""
    kept = []
    flds = fields_of(0x3a5be)
    for t in range(MAX_TRIES):
        st = world.make(0x3a5be, SENTINEL, flds, dict(regs=dict(a0=0x3a5d2)))
        tr = trace(st, lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL, cap=4000)
        if tr is None:
            continue
        record(tr['pcs'] + [tr['stop']])
        kept.append((st, tr))
        if len(kept) >= 3:
            break
    require(kept, 'no 3a5be -> 3a5d2 world')
    for i, (st, tr) in enumerate(kept):
        add(U.Fixture('chain-3a5be-routed-3a5d2-%d' % i, st, [], tr['stop'], meta=dict(family='chain-call', entry=0x3a5be, target=0x3a5d2)))


def error_fixtures(bases, add):
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)
    # every even PC of the unit ranges that is not a block start
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b2b PC')))
    for pc in UNROUTED_NEIGHBOURS:
        add(U.Fixture('error-unrouted-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-odd-pc', U.with_host_writes(st, pc=0x4d419), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    # Unknown C at the six consumers (carry tag 0)
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'objects b2b caller requires known carry')))
    # JSR (A0) of 3a5be: unrouted target, odd target, routed target 3a5d2 (match below in the chain)
    node = st['regs']['a6']
    add(U.Fixture('error-3a5be-unrouted-10fe00', U.with_host_writes(st, regs=dict(a0=0x10fe00), pc=0x3a5be), [], SENTINEL, ('error', 'unsupported animation machine PC'), fail_pc=0x10fe00))
    add(U.Fixture('error-3a5be-odd-target', U.with_host_writes(st, regs=dict(a0=0x3a5d3), pc=0x3a5be), [], SENTINEL, ('error', 'unaligned animation machine PC'), fail_pc=0x3a5d3))
    # odd LONG write (4c390 stores A0 at 5c8e(A5): A5 odd) and an odd WORD write (4d454 stores D2 at 2(A4))
    add(U.Fixture('error-4c390-odd-store', U.with_host_writes(st, regs=dict(a5=st['regs']['a5'] + 1), pc=0x4c390), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    add(U.Fixture('error-4d454-odd-store', U.with_host_writes(st, regs=dict(a4=st['regs']['a5'] + 0x5cbb), pc=0x4d454), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    # work-RAM rollback probes 10fe02 (38d56 -> 3b5a6 is routed by B2c) and 10fe06 (3a1b2 -> 4db18 is routed by B2e)
    add(U.Fixture('error-boundary-10fe02', U.with_host_writes(st, pc=0x10fe02), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-probe-10fe06', U.with_host_writes(st, pc=0x10fe06), [], SENTINEL, ('error', 'unsupported animation machine PC')))


def negative_fixtures(bases, out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.name in ('block-4d490-0', 'block-3b42e-0', 'block-4f08a-0', 'block-3a52e-0')]
    for fx in picks[:4]:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, st['regs']['a6']  & 0xffff | 0x5e)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
