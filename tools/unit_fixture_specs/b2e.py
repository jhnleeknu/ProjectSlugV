"""V1 fixture spec of the animation-machine unit B2e (engine/src/animation_machine_objects_b2e.cpp, 109 block starts).

Blocks (docs/analysis/animation-machine-deferred-b2e-contract.md): the script callbacks of the interpreter table 4a500 (index 23 3abee, 24 3b656, 25 3b458, 26 3b648,
27 3b62a), the shared angle leaf 44602, the child-spawn helper 4db18 with its 28ae child 4dbdc (the live JSR (A1) of 4dc44), and the demo-end ranking child e66aa with
its 28ae child e68c6 and the shared text leaf e89da.  The TRAP #f sites e6836 / e6896 stay unrouted (checked boundaries); e6890 (MOVE.W #1,1.w, an odd WORD write)
is a checked C++ error (no native comparison: Unicorn has no address error).  3b4e0 and 4b6f4 stay unrouted.

Fixture families (everything is native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the five consumers and e6890 is entered directly.  The world is a natural N-pass node state of the D1 seeds 116/117 (frame 2:
            N31 38c36, N33 3b166, N28 2b99c, N30a 331d8, N29 30de4, N22 3d32c; node A6, A5, bank and RAM are natural) with a declared host edit of D0-D7, A0-A4, the
            node fields the reachable blocks read (seeded generator, boundary hints for every compare / test / table index) and PC := the block start.  The stop is the
            first PC outside the unit (a routed callee, the sentinel return LONG, a JMP target, a TRAP).  Worlds are kept per entry while they add a successor.
  coverage  worlds that reach a conditional branch outcome of the unit that the block fixtures did not take.
  callback  the interpreter callback opcodes 4a408 (narrow) / 4a30c (wide) with a work-RAM script (index 23..27, LONG argument -> work-RAM data): the real JSR (A1)
            of 4a43c / 4a352 runs the callback through the routed callees (2986, 28ae, 3b48c, 4970a, 4c2fa, 3b288, 44602); stop at the return 4a43e / 4a354.
  chain     the five consumers entered through their REAL producers (2986 -> 3ac76, 28ae -> 3b666, 49fc6 -> 4dc34, JSR (A1) = 288c -> 4dc46, 288c -> 4dc50); native
            branches on the real flags, the C++ on the known C.  44602 with its real return LONGs (3b46c, B2a 60670, N34 4c74c, N19 b1ffc), e6784 with e672e.
  caller    4db18 from its routed callers (N28 2c818, B1c 30c1c, N30 33788, B2b 3a1b2) through the 28ae allocation to the caller's return PC, and the allocated child
            node entered at 4dbdc (A6 := the new node) to its RTS / 2a00.
  demo      the D9 demo end on a natural controller entry (D1 H end, A6 = 1008e4): LONG 1008e4 := c66a, BYTE 104cd4 := 0 (not replay -> C2 c686), PC := c66a; the
            controller tears the nodes down (c4cc), resets the screen (caf0), spawns e66aa (c6a6), returns to 2ac2, and the dispatcher runs e66aa (e6756, child e68c6,
            e66cc, e66ee) and the child e68c6 up to e66ee / e6938.  From the e6938 state the display node is re-entered at e66ee with the declared progress fields
            (80 := ff, 7c 78 7a 76) through the title (e6898 -> e89da -> 3918), the rank rows (e6784 -> e84c8 / 3670) and the end request (e6748 -> 2a00).
  error     every even non-start PC of the unit ranges, the PCs without an executor (work RAM), an odd PC, Unknown C at the five consumers, e6890 / e6884 -> e6890
            (odd write), e682e -> TRAP e6836 as a stop-only fixture, the live JSR (A1) to a work-RAM PC and to an odd PC, a 2986 allocation failure (2986 caller-X limitation),
            an odd LONG install: checked error, state preserved.
  negative  C++ input differs from the native input in one RAM bit / one register / the queue / the stop: the comparison must report it.
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
NODE_INDEX = (4, 6, 7, 11, 18, 21)      # frame 2 of seeds 116/117: N31 38c36, N33 3b166, N28 2b99c, N30a 331d8, N29 30de4, N22 3d32c
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT = 'animation_objects_b2e_block'
CONTROLLER = 0x1008e4
SCRIPT = 0x10fe41                       # work-RAM interpreter script (the callback index byte sits at an odd address, the LONG argument after it is even)
ARG = 0x10fe60                          # work-RAM data the callback argument points to

RANGES = [(0x3abee, 0x3acd6), (0x3b458, 0x3b48c), (0x3b62a, 0x3b68a), (0x44602, 0x4464a), (0x4db18, 0x4db42), (0x4dbdc, 0x4dc66),
          (0xe66aa, 0xe6836), (0xe6854, 0xe6896), (0xe6898, 0xe693a), (0xe89da, 0xe89e4)]
STARTS = [int(x, 16) for x in (
    '3abee 3abf6 3ac00 3ac12 3ac1a 3ac1c 3ac2c 3ac44 3ac48 3ac56 3ac58 3ac76 3ac7c 3ac8a 3ac98 3aca0 3acb2 3acc6 3acd4 3b458 3b46c 3b62a 3b638 3b63a 3b642 3b648 '
    '3b656 3b666 3b66a 3b678 3b67c 44602 4461c 44620 44626 4462a 4463c 4db18 4db34 4dbdc 4dbfa 4dc08 4dc22 4dc28 4dc2e 4dc34 4dc38 4dc40 4dc46 4dc4a 4dc50 4dc54 '
    '4dc58 4dc5e 4dc60 '
    'e66aa e66ae e66be e66cc e66ee e66f6 e66fa e6702 e6714 e671e e6722 e6726 e672e e6738 e673e e6746 e6748 e6756 e675c e6762 e676e e6774 e6782 e6784 e678c e67b0 '
    'e67c0 e67c8 e67d0 e67fe e681e e6826 e682a e682e e6854 e6870 e6878 e687c e6882 e6884 e6890 e6898 e68aa e68b8 e68c6 e68cc e68ec e68fa e6910 e6916 e6920 e6932 '
    'e6938 e89da').split()]
CONSUMERS = (0x3ac76, 0x3b666, 0x4dc34, 0x4dc46, 0x4dc50)
ERROR_ONLY = (0xe6890,)                 # MOVE.W #1,1.w: the odd WORD write (C++ checked alignment error; Unicorn performs no address error)
TRAPS = (0xe6836, 0xe6896)
CALLBACKS = {0x23: 0x3abee, 0x24: 0x3b656, 0x25: 0x3b458, 0x26: 0x3b648, 0x27: 0x3b62a}
# work-RAM PCs without an executor (review 0264 M-3).  The ROM neighbours / TRAP sites 3abec 3b68a 44600 4464a 4db16 4dc66 e66a8 e6836 e6838 e6896 e693a e89d8 e89e4 3b4e0 4b6f4
# are 10fe10..10fe2c in this order; the exact range ends are asserted against the routing in build().
UNROUTED_NEIGHBOURS = (0x10fe10, 0x10fe12, 0x10fe14, 0x10fe16, 0x10fe18, 0x10fe1a, 0x10fe1c, 0x10fe1e, 0x10fe20, 0x10fe22, 0x10fe24, 0x10fe26, 0x10fe28, 0x10fe2a, 0x10fe2c,
                       0x10fe00, 0x10fefe)
# producer chains: entry block, the consumer it reaches
CHAINS = ((0x3ac58, 0x3ac76), (0x3b656, 0x3b666), (0x4dc28, 0x4dc34), (0x4dc40, 0x4dc46), (0x4dc4a, 0x4dc50))
# 44602 callers with their real return LONG (entry block, return PC)
ANGLE_CALLERS = ((0x3b458, 0x3b46c), (0x6064a, 0x60670), (0x4c742, 0x4c74c), (0xb1fe0, 0xb1ffc))
# 4db18 callers (routed blocks that end with JSR 4db18) and their return PCs
SPAWN_CALLERS = ((0x2c818, 0x2c82c), (0x30c1c, 0x30c3c), (0x33788, 0x3379c), (0x3a1b2, 0x3a1b8))

VB = (0, 1, 2, 3, 4, 5, 8, 9, 0x10, 0x11, 0x3f, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xef, 0xf0, 0xfe, 0xff)
VW = (0, 1, 2, 8, 9, 10, 11, 0x5a, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 0x10000, 0x7fff0000, 0x80000000, 0xffff0000, 0xffffffff, 0x12345678, 0x00fe0000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
ABS = re.compile(r'\$([0-9a-f]{5,6})\.l')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')

# ---------------------------------------------------------------------------------------------------------------------
# Routing (parsed from the C++ dispatch chain) and static decode
# ---------------------------------------------------------------------------------------------------------------------
_ROUTE = []


def require(ok, detail):
    if not ok:
        raise RuntimeError(str(detail))


def load_routing():
    if _ROUTE:
        return
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
        env = {'p': pc, 'trap': lambda x: x in (0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788)}
        _UNIT[pc] = None
        for unit, code in _ROUTE:
            if eval(code, env):
                _UNIT[pc] = unit
                break
    return _UNIT[pc]


_MINE = {}


def mine(pc):
    if pc not in _MINE:
        _MINE[pc] = any(lo <= pc < hi for lo, hi in RANGES)
    return _MINE[pc]


_CS = []
STARTS_SET = set(STARTS)


def decode(addr):
    if not _CS:
        import capstone
        _CS.append(capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000))
        _CS.append(U.native().program)
    for ins in _CS[0].disasm(_CS[1][addr:addr + 12], addr):
        return ins
    return None


# capstone 5 does not decode LEA d16(PC),A1 at e89da (43fa faec): the length is fixed here (4 bytes, LEA e84c8(PC),A1).
KNOWN = {0xe89da: (0xe89da, 'lea', '$e84c8(pc), a1', 4, 'lea.l')}


def insn(a):
    if a in KNOWN:
        return KNOWN[a]
    ins = decode(a)
    require(ins is not None, ('undecodable', hex(a)))
    return (a, ins.mnemonic.split('.')[0], ins.op_str, ins.size, ins.mnemonic)


def target(op):
    if op.startswith('('):
        return None                                             # JSR (A1): computed
    m = re.search(r'\$([0-9a-f]+)', op)
    return int(m.group(1), 16) if m else None


def walk(start):
    """Instruction records of the block at `start` and its static outcome: ('call', target, ret) | ('rts',) | ('computed',) | ('flow', {successors})."""
    out = []
    a = start
    while True:
        rec = insn(a)
        out.append(rec)
        _, mn, op, size, _ = rec
        nxt = a + size
        if mn in ('jsr', 'bsr'):
            return out, ('call', target(op), nxt)
        if mn == 'rts':
            return out, ('rts',)
        if mn in ('jmp', 'bra'):
            t = target(op)
            return out, (('computed',) if t is None else ('flow', {t}))
        if BCC.match(mn) or mn == 'dbra':
            return out, ('flow', {target(op), nxt})
        a = nxt
        if a in STARTS_SET or not mine(a):
            return out, ('flow', {a})


def static_next(start):
    out, res = walk(start)
    if res[0] == 'call':
        return {res[1]} if res[1] is not None else None
    if res[0] in ('rts', 'computed'):
        return None
    return res[1]


def block_instrs(start):
    return walk(start)[0]


def reachable_blocks(start):
    seen, work = set(), [start]
    while work:
        s = work.pop()
        if s in seen or s not in STARTS_SET:
            continue
        seen.add(s)
        out, res = walk(s)
        if res[0] == 'call':
            work.append(res[2])
        elif res[0] == 'flow':
            work += list(res[1])
    return seen


def fields_of(start):
    """Memory fields (kind, reg, displacement, size) read or written by the blocks reachable from `start`."""
    out = set()
    for s in reachable_blocks(start):
        for a, mn, op, size, full in block_instrs(s):
            if mn in ('lea', 'movem', 'jsr', 'jmp', 'bsr', 'bra', 'rts', 'dbra') or BCC.match(mn):
                continue
            sz = {'b': 1, 'w': 2, 'l': 4}.get(full.split('.')[1] if '.' in full else 'w', 2)
            for m in HX.finditer(op):
                disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
                out.add(('reg', int(m.group(3)), disp, sz))
            for m in ABS.finditer(op):
                ad = int(m.group(1), 16)
                if 0x100000 <= ad < 0x200000:
                    out.add(('abs', 0, ad, sz))
    if any(s in reachable_blocks(start) for s in (0xe6854, 0xe6870, 0xe67d0, 0xe67fe)):
        out |= set(('abs', 0, 0x10f02e + 8 * k + o, 4) for k in range(11) for o in (0, 4))      # the ranking records (LEA 10f02e.l)
    return sorted(out)


# ---------------------------------------------------------------------------------------------------------------------
# Native tracer (selection of worlds only: every kept world is re-run by the V1 verifier, native versus C++)
# ---------------------------------------------------------------------------------------------------------------------
COMPUTED_JUMPS = (0x4dc44,)                                  # JSR (A1): a target outside the unit is always a stop


def trace(state, outside, cap=CAP_INSN, queue=None, status=0, computed_stop=True):
    """Run the original from state.pc natively until `outside(pc, prev, prev_size)` is true (checked from the second instruction on).  -> dict(pcs, stop, sr)
    or None."""
    N = U.native()
    unicorn, S, PB = N.unicorn, N.S, N.PB
    snap = dict(ram=state['ram'], regs=state['regs'], pc=state['pc'], bank=state['bank'])
    m = PB.PvcMachine(N.program, N.fixed, snap)
    m.install_basic_hooks()
    c = m.cpu
    for base in (0x340000, 0x380000):
        c.mem_map(base, 4096, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    c.mem_write(U.PVC_LO, state['pvc'])
    c.mem_write(U.STATUS_ADDR, bytes([status & 0xff]))
    pcs = []
    box = {}

    def code(uc, pc, size, user):
        if box.get('stop') == -1:
            return
        if pcs and (outside(pc, pcs[-1], box['size']) or (computed_stop and pcs[-1] in COMPUTED_JUMPS and not mine(pc))):
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
    if stop is None or stop & 1 or m.odd is not None or m.invalid is not None or m.intr is not None or m.fetch_unmapped is not None or m.dev_reads:
        return None
    # Unicorn evaluates the M68000 condition codes lazily: reg_read(SR) returns stale flags.  MOVE SR,D0 on a scratch page forces the evaluation.
    c.mem_map(SCRATCH, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE | unicorn.UC_PROT_EXEC)
    c.mem_write(SCRATCH, b'\x40\xc0\x4e\x71')
    box['stop'] = -1
    c.emu_start(SCRATCH, SCRATCH + 2, count=1)
    return dict(pcs=pcs, stop=stop, ports=len(m.ports), sr=c.reg_read(S.UC_REG['d0']) & 0xffff)


def routed_stop(extra=()):
    """Stop at the sentinel, at 2a00 (object removal), at an extra PC, or at the first PC without an executor that is not the straight-line successor of the
    previous instruction (a PC inside a block of another executor is not a block entry; B2d rule)."""
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


def at_pcs(pcs):
    ps = set(pcs)
    return lambda pc, prev, size: pc in ps


# ---------------------------------------------------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------------------------------------------------
class World(object):
    def __init__(self, bases, rng):
        self.bases, self.rng = bases, rng
        self.nodes = sorted(set(b.state['regs']['a6'] for b in bases))

    def pointer(self, a5):
        rng = self.rng
        pool = [0] + [0x1009a8 + 0xc4 * k for k in range(14)] + self.nodes + [ARG, ARG + 2, 0x10f02e, 0x200024, 0x200028]
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
        # the callback argument data (3abee: three WORDs, 3b62a: a LONG, 3b648: a WORD)
        writes += [((ARG + 2 * k) & 0xffff, 2, rng.choice(VW)) for k in range(4)]
        if rng.random() < 0.4:
            parent = rng.choice(self.nodes)
            writes += [((regs['a6'] + 0xc) & 0xffff, 4, parent)]
        sp = regs['a7']
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            writes += [((regs['a6'] + off) & 0xffff, size, val) for off, size, val in hint.get('a6off', [])]
            for w in hint.get('writes', []):
                if w[0] == 'sp':                                  # ('sp', offset, size, value): data at A7 + offset
                    writes.append(((sp + w[1]) & 0xffff, w[2], w[3]))
                elif w[0] == 'parent':                            # ('parent', offset, size, value): c(A6) := the first natural node, then a field of it
                    parent = self.nodes[0]
                    writes += [((regs['a6'] + 0xc) & 0xffff, 4, parent), ((parent + w[1]) & 0xffff, w[2], w[3])]
                else:
                    writes.append(w)
            regs.update(hint.get('regs', {}))
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
def all_instrs():
    out = {}
    for lo, hi in RANGES:
        a = lo
        while a < hi:
            rec = insn(a)
            out[a] = rec
            a += rec[3]
    return out


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    require(len(STARTS) == 109 and len(STARTS_SET) == 109, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for pc in UNROUTED_NEIGHBOURS:
        require(unit_of(pc) is None, ('probe is routed', hex(pc)))
    for lo, hi in RANGES:
        require(unit_of(hi) != UNIT and unit_of(lo - 2) != UNIT, ('range end routed to b2e', hex(lo), hex(hi)))
    for s in STARTS:
        require(unit_of(s) == UNIT, ('start is not routed to b2e', hex(s), unit_of(s)))
    rng = random.Random(0xB2E)
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
    cond_points = {}

    def add(fx):
        require(fx.name not in names, ('duplicate', fx.name))
        names.add(fx.name)
        out.append(fx)

    def outside_unit(allowed=()):
        al = set(allowed)
        return lambda pc, prev, size: not mine(pc) and pc not in al

    def record(entry_pcs):
        visited.update(p for p in entry_pcs if mine(p))
        for i in range(len(entry_pcs) - 1):
            pc = entry_pcs[i]
            if pc in cond_points:
                covered.add((pc, entry_pcs[i + 1]))

    for a, rec in all_instrs().items():
        _, mn, op, size, _ = rec
        if BCC.match(mn) or mn == 'dbra':
            cond_points[a] = {target(op), a + size}
    stats = dict(tries=0, rejected=0)
    # ---- block fixtures
    for entry in STARTS:
        if entry in CONSUMERS or entry in ERROR_ONLY:
            continue                                            # a consumer needs the C of its producer: chain fixtures; e6890 is an error fixture
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
                out_missing.append((hex(entry), [hex(x) for x in missing]))
    callback_fixtures(world, add, record)
    chain_fixtures(world, add, record)
    caller_fixtures(bases, add, record)
    demo_fixtures(add, record)
    # ---- coverage fixtures: outcomes of any conditional branch not taken so far
    todo = [(a, t) for a, ts in sorted(cond_points.items()) for t in sorted(ts) if (a, t) not in covered]
    entries_for = {}
    for s in STARTS:
        for r in reachable_blocks(s):
            entries_for.setdefault(r, []).append(s)
    for a, t in todo:
        blk = [s for s in STARTS if any(x[0] == a for x in block_instrs(s))][0]
        done = False
        for entry in [e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS and e not in ERROR_ONLY][:6]:
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
            unreachable.append((hex(a), hex(t)))
    never = sorted(set(STARTS) - visited - set(ERROR_ONLY))
    require(not never, ('block starts never executed by a fixture', [hex(x) for x in never]))
    error_fixtures(bases, add)
    negative_fixtures(out, add)
    META['carry_oracle'] = carry_oracle(out)
    META['visited_starts'] = len(set(STARTS) & visited)
    META['chain_only'] = [hex(x) for x in CONSUMERS]
    META['out_missing'] = out_missing
    META['unreachable'] = unreachable
    META['stats'] = stats
    sys.stderr.write('b2e: %d fixtures, visited starts %d/109 (+ error-only e6890), out_missing %s, unreachable %s\n' % (len(out), META['visited_starts'], out_missing,
                                                                                                                      unreachable))
    return out


out_missing = []
unreachable = []
META = {}


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b2e: carry oracle skipped (no harness binary)\n')
        return None
    import os
    harness = U.Harness(exe, U.program_resources(), os.devnull)
    counts = {0: 0, 1: 0, 2: 0}
    try:
        for fx in fixtures:
            if fx.expect != 'match' or fx.cpp_state is not None:
                continue
            got = U.cpp_call(harness, fx)
            if not got['ok']:
                continue                                        # the verifier reports a C++ failure itself
            counts[got['carry']] += 1
            if got['carry'] == 0:
                continue
            tr = trace(fx.state, at_pcs((fx.stop,)), cap=fx.max_insn if fx.max_insn < 2000000 else 2000000, queue=fx.queue,
                       status=fx.external_status)
            if tr is None and fx.meta.get('family') == 'demo':
                continue                                        # demo runs pass card / wait releases the plain tracer does not model
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('b2e: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of every compare / test / table index of the unit.  Every hint world is
    kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    if entry in (0x3abee, 0x3ac12):
        h += byte(0xa6, (0, 1, 5, 0xff))
    if entry == 0x3abf6:
        h += byte(0x9d, (0, 0x10, 0xef, 0xff))
    if entry == 0x3ac1c:
        h += [dict(a6off=[(0xa6, 1, a6), (0xa8, 1, a8)]) for a6 in (0, 1) for a8 in (0, 1, 3, 4, 0xff)]
    if entry == 0x3ac7c:
        h += [dict(regs=dict(a1=ARG)), dict(regs=dict(a1=ARG + 2))]
    if entry == 0x3ac8a:
        h += [dict(regs=dict(d0=d0, d2=0xfff0), a6off=[(0x15, 1, b)]) for d0 in (0x10, 0xfff0) for b in (0, 1)]
    if entry == 0x3ac98:
        h += [dict(regs=dict(d7=v, d2=w)) for v in (0, 0x40, 0x80, 0xc0, 0xff) for w in (0, 0x8000, 0xffff)]
    if entry == 0x3aca0:
        h += [dict(regs=dict(d7=v, a0=0x1009a8)) for v in (0, 0x3f, 0x40, 0x80, 0xc1)]
    if entry == 0x3acb2:
        h += [dict(regs=dict(d7=d7, a0=0x1009a8), a6off=[(0xa8, 1, v)]) for v in (0, 1, 2, 3, 0x80, 0xff) for d7 in (2, 0xfffe)]
    if entry == 0x3b458:
        h += [dict(a6off=[(0x36, 4, x), (0x3a, 4, y)]) for x in (0, 0x80000000, 0x7fffffff, 0xffff0000, 0x12345678) for y in (0, 0xfffe0000, 0x00020000)]
    if entry == 0x3b46c:
        h += [dict(regs=dict(d0=d), a6off=[(0xa1, 1, a)]) for d in (0, 0x7f, 0x80, 0xff) for a in (0, 0x40, 0x80, 0xff)]
    if entry in (0x3b62a, 0x3b648):
        h += [dict(regs=dict(a0=ARG), a6off=[(0x15, 1, b)]) for b in (0, 1)]
    if entry == 0x44602:
        vals = (0, 1, 2, 3, 0x100, 0x1ff, 0x7fff, 0x8000, 0xfffe, 0xffff, 0x80, 0xff80)
        h += [dict(regs=dict(d0=a, d1=b)) for a in vals for b in vals[::2]]
    if entry == 0x44620:
        h += [dict(regs=dict(d0=a, d4=0xff)) for a in (0, 0x100, 1, 0xff)]
    if entry == 0x4462a:
        h += [dict(regs=dict(d0=a, d1=b)) for a in (0, 1, 0x40, 0xff) for b in (0, 1, 0x80, 0xff)]
    if entry == 0x4463c:
        h += [dict(regs=dict(d0=a, d2=b, d3=c)) for a in (0, 0x40, 0x7f) for b in (0, 0xff) for c in (0, 0xff)]
    if entry == 0x4db18:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x1234, 0x8000), (0xffffffff, 0x7fff))]
    if entry == 0x4dc38:
        h += [dict(a6off=[(0x7a, 4, v)]) for v in (0, 0x288c)]
    if entry == 0x4dc58:
        h += [dict(regs=dict(d0=v)) for v in (0, 0x7f, 0x80, 0xff)]
    if entry == 0xe66ee:
        h += byte(0x80, (0, 1, 0xff))
    if entry == 0xe66fa:
        h += word(0x7c, (0, 1, 0xffff))
    if entry == 0xe6702:
        h += word(0x7a, (0, 1, 2, 0xffff))
    if entry in (0xe6714, 0xe672e):
        h += word(0x78, (8, 9, 10))
    if entry == 0xe673e:
        h += word(0x76, (0, 1, 2))
    if entry == 0xe6916:
        h += byte(0x12, (0, 0xef, 0xf0, 0xff))
    if entry == 0xe682e:
        h += [dict(regs=dict(d7=v)) for v in (0, 9, 10, 0x7fff, 0x8000, 0xffff)]
    if entry == 0xe6854:
        h += [dict(regs=dict(d7=v)) for v in (0, 1, 5, 9)]
    if entry == 0xe6870:
        h += [dict(regs=dict(d3=d3, a1=0x10f02e), writes=[(0xf02e, 4, a)]) for d3 in (0, 5, 0x80000000) for a in (0, 5, 0x80000000)]
    if entry == 0xe687c:
        h += [dict(regs=dict(d1=a, d7=b)) for a, b in ((1, 1), (1, 2), (0x10001, 1))]
    if entry == 0xe6884:
        h += [dict(regs=dict(d1=v, a1=0x10f02e)) for v in (0, 9, 0xffff)]
    if entry == 0xe678c:
        h += [dict(regs=dict(d0=v), writes=[('sp', 0, 2, k)]) for v in (1, 2, 10, 11) for k in (0, 9)]
    if entry == 0xe6826:                                        # DBRA; the exit pops the stacked row WORD above the return LONG
        h += [dict(regs=dict(d7=v), writes=[('sp', 0, 2, 3), ('sp', 2, 4, SENTINEL)]) for v in (0, 1, 2, 0x10000)]
    if entry == 0xe68cc:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 0xffffffff)]
    if entry == 0x4db34:                                        # the three stacked values (D0.W, D1.W, LONG 0) above the return LONG
        h += [dict(regs=dict(a0=a0), writes=[('sp', 0, 2, 0x1234), ('sp', 2, 2, 0x8765), ('sp', 4, 4, 0), ('sp', 8, 4, SENTINEL)]) for a0 in (0x1009a8, 0x100a6c)]
    if entry == 0xe682a:                                        # the stacked row WORD above the return LONG
        h += [dict(writes=[('sp', 0, 2, k), ('sp', 2, 4, SENTINEL)]) for k in (0, 9)]
    return h


def callback_fixtures(world, add, record):
    """The interpreter callback opcodes with a work-RAM script: 4a408 (narrow: index BYTE, LONG argument) and 4a30c (wide: index WORD, 4a76c WORD index, LONG
    argument).  The real JSR (A1) runs the callback; stop at its return 4a43e / 4a354."""
    stop_rule = routed_stop((0x4a43e, 0x4a354))
    for index, entry in sorted(CALLBACKS.items()):
        flds = sorted(set(fields_of(entry)))
        for wide in (False, True):
            kept = {}
            for t in range(MAX_TRIES // 2):
                if wide:
                    script = [((SCRIPT + 1) & 0xffff, 2, index), ((SCRIPT + 3) & 0xffff, 2, 0), ((SCRIPT + 5) & 0xffff, 4, ARG)]
                else:
                    script = [(SCRIPT & 0xffff, 1, index), ((SCRIPT + 1) & 0xffff, 4, ARG)]
                st = world.make(0x4a30c if wide else 0x4a408, SENTINEL, flds, dict(regs=dict(a1=SCRIPT, a0=(world.nodes[0] + 0x8c) & 0xffffffff), writes=script))
                tr = trace(st, stop_rule, cap=40000)
                if tr is None or entry not in tr['pcs']:
                    continue
                record(tr['pcs'] + [tr['stop']])
                path = tuple(pc for pc in tr['pcs'] if mine(pc) and pc in STARTS_SET)
                key = (tr['stop'], path[-1] if path else None)
                if key not in kept:
                    kept[key] = (st, tr)
                if len(kept) >= (3 if index == 0x23 else 2):
                    break
            require(kept, ('no callback world', hex(entry), wide))
            for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0))):
                add(U.Fixture('callback-%s-%02x-%d' % ('wide' if wide else 'narrow', index, i), st, [], tr['stop'],
                              meta=dict(family='callback', index=index, entry=entry, stop=tr['stop'])))


def chain_fixtures(world, add, record):
    # the consumers through their real producers
    for entry, consumer in CHAINS:
        flds = fields_of(entry)
        kept = {}
        for t in range(MAX_TRIES * 2):
            # the second outcome of each producer: 28ae failure (free count WORD 104ca0 = 0), 288c Clear (parent callback 270e)
            hint = dict(a6off=[(0x7a, 4, 0x288c)]) if entry == 0x4dc40 else dict()
            if t & 1 and entry == 0x3b656:
                hint['writes'] = [(0x4ca0, 2, 0)]
            if t & 1 and entry in (0x4dc40, 0x4dc4a):
                hint['writes'] = [('parent', 0, 4, 0x270e)]
            st = world.make(entry, SENTINEL, flds, hint or None)
            tr = trace(st, routed_stop(), cap=20000, computed_stop=False)
            if tr is None or consumer not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            i = tr['pcs'].index(consumer)
            succ = tr['pcs'][i + 1] if i + 1 < len(tr['pcs']) else tr['stop']
            key = (succ, tr['stop'])
            if key not in kept:
                kept[key] = (st, tr)
            if len(set(k[0] for k in kept)) >= 2:
                break
        require(kept, ('no chain world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-%05x-%d' % (entry, consumer, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=consumer,
                                                                                                     consumer_successor=key[0])))
    # 44602 with its real return LONGs; e6784 (rank row) with e672e
    for entry, ret in ANGLE_CALLERS + ((0xe6784, 0xe672e),):
        flds = fields_of(entry) if mine(entry) else []
        kept = {}
        for t in range(MAX_TRIES):
            hint = None
            if entry == 0xe6784:
                hint = dict(regs=dict(d0=rng_pick(world, (0, 1, 5, 9))))
            st = world.make(entry, ret if entry == 0xe6784 else SENTINEL, flds + fields_of(0x44602), hint)   # e6784 is a subroutine: its return LONG
            tr = trace(st, routed_stop((ret,)), cap=40000)
            if tr is None or tr['stop'] != ret:
                continue
            record(tr['pcs'] + [tr['stop']])
            path = tuple(pc for pc in tr['pcs'] if mine(pc))
            key = path[-6:]
            if key not in kept:
                kept[key] = (st, tr)
            if len(kept) >= 3:
                break
        require(kept, ('no helper chain world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, ret, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, ret=ret)))


def rng_pick(world, values):
    return world.rng.choice(values)


def caller_fixtures(bases, add, record):
    """4db18 from its routed callers through the 28ae allocation to the caller's return PC; then the allocated node entered at its callback 4dbdc."""
    made = 0
    for caller, ret in SPAWN_CALLERS:
        for b, base in enumerate(bases[:4]):
            st = U.with_host_writes(base.state, [((base.state['regs']['a7']) & 0xffff, 4, SENTINEL)], regs=dict(d0=0x40 + b, d1=0x80 + b), pc=caller)
            tr = trace(st, routed_stop((ret, 0x4db18)), cap=20000)
            if tr is None or tr['stop'] != 0x4db18:
                continue
            tr = trace(st, routed_stop((ret,)), cap=20000)
            if tr is None or tr['stop'] != ret:
                continue
            record(tr['pcs'] + [tr['stop']])
            add(U.Fixture('caller-%05x-%d' % (caller, b), st, base.queue, ret, external_status=base.external_status, meta=dict(family='caller', caller=caller, ret=ret)))
            made += 1
            # the allocated child: native state at the caller's return (A0 = the new node, fields 76 78 7a written by 4db34), then PC := 4dbdc with A6 := the new
            # node and a pushed sentinel return LONG
            try:
                cst, rest, _ = U.advance_native(st, base.queue, ret, external_status=base.external_status, max_insn=400000)
            except (RuntimeError, TypeError):
                continue
            node = cst['regs']['a0']
            if not (0x100000 <= node < 0x110000):
                continue
            sp = (cst['regs']['a7'] - 4) & 0xffffffff
            child = U.with_host_writes(cst, [(sp & 0xffff, 4, SENTINEL)], regs=dict(a6=node, a7=sp), pc=0x4dbdc)
            tr = trace(child, routed_stop(), cap=40000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            add(U.Fixture('caller-%05x-%d-child-4dbdc' % (caller, b), child, rest, tr['stop'], external_status=base.external_status,
                          meta=dict(family='caller', caller=caller, child=node, stop=tr['stop'])))
    require(made >= 4, ('4db18 caller fixtures', made))


def demo_fixtures(add, record):
    """The natural demo end: controller entry (D1 H end of frame 1), LONG 1008e4 := c66a, BYTE 104cd4 := 0, PC := c66a, run natively through the controller, the
    dispatcher and the new nodes; then the display node re-entered at e66ee with declared progress fields."""
    made = 0
    for case in U.natural_cases(3):
        frs = [f for f in U.seed_frames(case, 2) if f['frame'] == 1 and f.get('h')]
        if not frs or frs[0]['h']['reason']['reason'] != 'controller':
            continue
        fr = frs[0]
        st = U.with_host_writes(U.seed_state(fr['h']['end']), [(CONTROLLER & 0xffff, 4, 0xc66a), (0x4cd4, 1, 0)], pc=0xc66a)
        status = fr['start']['status']
        for stop in (0xe66ee, 0xe6938):
            add(U.Fixture('demo-c66a-s%d-to-%05x' % (case, stop), st, [], stop, external_status=status, meta=dict(family='demo', case=case, stop=stop)))
            made += 1
        try:
            cst, rest, _ = U.advance_native(st, [], 0xe6938, external_status=status)
        except (RuntimeError, TypeError):
            continue
        record([0xe66aa, 0xe66ae, 0xe66be, 0xe66cc, 0xe66ee, 0xe6746, 0xe6756, 0xe675c, 0xe6762, 0xe676e, 0xe6774, 0xe6782, 0xe68c6, 0xe68cc, 0xe68ec, 0xe68fa,
                0xe6910, 0xe6916, 0xe6932, 0xe6938])
        a6 = cst['regs']['a6']
        parent = int.from_bytes(cst['ram'][(a6 + 0xc) & 0xffff:((a6 + 0xc) & 0xffff) + 4], 'big')
        sp = cst['regs']['a7'] & 0xffff
        for k, (row, sub, timer, half) in enumerate(((0, 0, 0x5a, 0), (1, 1, 0x5a, 0), (8, 1, 0x5a, 0), (9, 1, 0x5a, 0), (9, 1, 1, 0), (9, 0, 0x30, 0), (3, 0, 0x5a, 1))):
            writes = [(sp, 4, SENTINEL), ((parent + 0x80) & 0xffff, 1, 0xff), ((parent + 0x7c) & 0xffff, 2, half), ((parent + 0x78) & 0xffff, 2, row),
                      ((parent + 0x7a) & 0xffff, 2, sub), ((parent + 0x76) & 0xffff, 2, timer)]
            node = U.with_host_writes(cst, writes, regs=dict(a6=parent), pc=0xe673e if (row == 9 and timer == 1) else 0xe66ee)
            tr = trace(node, at_pcs((SENTINEL, 0x2a00)), cap=400000, status=status)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            add(U.Fixture('demo-node-s%d-%d' % (case, k), node, rest, tr['stop'], external_status=status, meta=dict(family='demo', case=case, row=row, stop=tr['stop'])))
            made += 1
    require(made >= 6, ('demo fixtures', made))


def error_fixtures(bases, add):
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in STARTS_SET:
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b2e PC')))
    for pc in UNROUTED_NEIGHBOURS:
        add(U.Fixture('error-unrouted-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-odd-pc', U.with_host_writes(st, pc=0xe66ab), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'objects b2e caller requires known carry')))
    node = st['regs']['a6']
    wr = 'invalid animation machine write size/alignment'
    add(U.Fixture('error-e6890-odd-write', U.with_host_writes(st, pc=0xe6890), [], SENTINEL, ('error', wr)))
    add(U.Fixture('error-e6884-to-e6890', U.with_host_writes(st, regs=dict(d1=10, a1=0x10f02e), pc=0xe6884), [], SENTINEL, ('error', wr)))
    # e682e falls into the TRAP #f at e6836 (a fixed ROM address): stop-only boundary check (both sides stop exactly at e6836)
    add(U.Fixture('boundary-stop-e682e-e6836', U.with_host_writes(st, regs=dict(d7=10), pc=0xe682e), [], 0xe6836))
    add(U.Fixture('error-e6854-trap-loop', U.with_host_writes(st, regs=dict(d7=0xffff), pc=0xe6854), [], SENTINEL, ('error', wr)))
    add(U.Fixture('error-4dc40-ram-target', U.with_host_writes(st, [((node + 0x7a) & 0xffff, 4, 0x10fe00)], pc=0x4dc40), [], SENTINEL,
                  ('error', 'unsupported animation machine PC'), fail_pc=0x10fe00))
    add(U.Fixture('error-4dc40-odd-target', U.with_host_writes(st, [((node + 0x7a) & 0xffff, 4, 0x4dc29)], pc=0x4dc40), [], SENTINEL,
                  ('error', 'unaligned animation machine PC'), fail_pc=0x4dc29))
    # 2986 allocation failure (D0.W = 1e >= WORD 104ca0 = 0): 298e has no known caller X for 3ac44 (buffer_cue decision 1, deliberate checked error)
    add(U.Fixture('error-3ac2c-2986-failure', U.with_host_writes(st, [(0x4ca0, 2, 0)], pc=0x3ac2c), [], SENTINEL,
                  ('error', 'cue wrapper failure requires known caller X')))
    # odd LONG installs (A6 odd)
    add(U.Fixture('error-4dc22-odd-install', U.with_host_writes(st, regs=dict(a6=node + 1), pc=0x4dc22), [], SENTINEL, ('error', wr)))
    add(U.Fixture('error-e6738-odd-install', U.with_host_writes(st, regs=dict(a6=node + 1), pc=0xe6738), [], SENTINEL, ('error', wr)))


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    want = ('block-3acb2-0', 'block-44602-0', 'block-e6854-0', 'block-4db34-0')
    picks = [fx for fx in out if fx.name in want]
    require(len(picks) == len(want), ('negative picks', [f.name for f in picks]))
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0xa8) & 0xffff, 0x40)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1))))
    add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
    add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
