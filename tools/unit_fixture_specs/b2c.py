"""V1 fixture spec of the animation-machine unit B2c (engine/src/animation_machine_objects_b2c.cpp, 218 block starts).

Blocks (docs/analysis/animation-machine-deferred-b2c-contract.md): the 82(A6) partner sub-state chain 3a60a..3abde (170: 27 installed re-entries, the request
dispatcher 3ab3e with the LONG table 3ab80 / WORD masks 3ab98, the input dispatcher 3aba4 with the BYTE slot table 3abde and the 7-slot BRA.W tables 3a63c 3a782 3a960,
the indirect jumps 3ab7e JMP (A0) and 3abda JMP (A0,D1.W) to the live target), the offset helper 3b48c, the partner initialisation 3b5a6, the 28ae children 3af86 and
3ae84 and the leaf helpers 1bf80 / 1d198.  The script callbacks 3abee 3b458 3b62a 3b648 3b656, 44602, 4db18 (B2c-b), the unreferenced 3b4e0 and 4b6f4 stay unrouted.

Fixture families (everything is native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start is entered directly.  The world is a natural N-pass node state of the D1 seeds 116/117 (frame 2: N31 38c36, N33 3b166, N28 2b99c, N30a 331d8,
            N29 30de4, N22 3d32c; node A6, A5, bank and RAM are natural) with a declared host edit of D0-D7, A0-A4, the node fields the reachable blocks read (seeded generator,
            boundary hints for every compare / test / table index, continuation and slot-table A0 values for the dispatchers) and PC := the block start.  The stop is the first PC
            outside the unit (a routed callee, the sentinel return LONG, a JMP target).  Worlds are kept per entry while they add a new successor of the entry block.
  coverage  worlds that reach a conditional branch outcome of the unit that the block fixtures did not take.
  substate  3a5be (B2b) JSR (A0) with A0 = every sub-state entry (3a60a and the 27 installed values) and N33 3a1e0 with 82(A6) := entry: the whole chain runs through the
            routed callees (3b398 -> interpreter, 3b446, 3b48c) and returns through 3a5ca; stop at the first unrouted PC, 2a00 or the sentinel.
  chain     3b48c / 1bf80 / 1d198 with their real return LONG (3ab34 / 3afa2 / 3af94); the C chains 49fc6 -> 3af12 3af60 3b026 (native branches on the real flags, the C++ on
            the known C); B2b 38d56 -> 3b5a6 -> N33 / N03 / B2b callees.
  spawn     the natural 28ae children: from a seed node with PC := the parent install (38d56 for 3af86, 3a4da for 3ae84) advanced natively to the child callback.
  error     every even non-start PC of the unit ranges, the unrouted neighbours, an odd PC, Unknown C at the three consumers, the indirect jumps to a work-RAM PC (10fe00..)
            and to an odd PC, an odd LONG install: checked error, state preserved.
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
UNIT = 'animation_objects_b2c_block'

RANGES = [(0x3a60a, 0x3ab80), (0x3aba4, 0x3abde), (0x3ae84, 0x3af6c), (0x3af86, 0x3b03c), (0x3b48c, 0x3b4bc), (0x3b5a6, 0x3b62a), (0x1bf80, 0x1bf94),
          (0x1d198, 0x1d1b0)]
STARTS = [int(x, 16) for x in (
    '3a60a 3a614 3a622 3a62a 3a62e 3a63c 3a640 3a644 3a648 3a64c 3a650 3a654 3a658 3a662 3a670 3a674 3a67a 3a680 3a684 3a68e 3a69c 3a6a0 3a6aa 3a6b8 '
    '3a6bc 3a6c6 3a6d4 3a6d8 3a6e0 3a6e4 3a6ee 3a6fc 3a700 3a708 3a70c 3a716 3a724 3a728 3a732 3a740 3a744 3a74e 3a75e 3a766 3a770 3a774 3a782 3a786 '
    '3a78a 3a78e 3a792 3a796 3a79a 3a79e 3a7a8 3a7b6 3a7ba 3a7c0 3a7c6 3a7ca 3a7d4 3a7e2 3a7e6 3a7f0 3a7fe 3a802 3a80c 3a81a 3a81e 3a826 3a82a 3a834 '
    '3a842 3a846 3a84e 3a852 3a85c 3a86a 3a86e 3a878 3a886 3a88a 3a894 3a8a4 3a8ac 3a8b6 3a8ba 3a8c4 3a8d2 3a8dc 3a8ec 3a8f4 3a8f8 3a902 3a910 3a91a '
    '3a92a 3a932 3a936 3a952 3a960 3a964 3a968 3a96c 3a970 3a974 3a978 3a97c 3a986 3a990 3a994 3a99e 3a9a2 3a9aa 3a9ae 3a9b4 3a9ba 3a9be 3a9c8 3a9d6 '
    '3a9da 3a9e4 3a9f2 3a9f6 3aa00 3aa08 3aa0c 3aa14 3aa18 3aa22 3aa2a 3aa2e 3aa36 3aa3a 3aa44 3aa52 3aa56 3aa60 3aa6e 3aa72 3aa7a 3aa84 3aa8e 3aa96 '
    '3aa9c 3aaa4 3aac8 3aacc 3aae4 3aae8 3aaf2 3ab00 3ab08 3ab0c 3ab16 3ab24 3ab2c 3ab30 3ab34 3ab3e 3ab4c 3ab5a 3ab6a 3ab6c 3ab72 3ab7e 3aba4 3abaa '
    '3abbc 3abc0 3b48c 3b49c 3b4a0 3b4b2 3b4b4 3b5a6 3b5aa 3b5e8 3b5fa 3b628 3af86 3af94 3afa2 3afcc 3afe8 3aff2 3aff8 3affe 3b010 3b012 3b020 3b026 '
    '3b02a 3b03a 3ae84 3aea0 3aeae 3aebe 3aec4 3aeca 3aed6 3aee4 3aefa 3aefc 3af12 3af16 3af1c 3af2e 3af4e 3af54 3af5a 3af60 3af64 3af6a 1bf80 1bf8a '
    '1bf8e 1d198').split()]
CONSUMERS = (0x3af12, 0x3af60, 0x3b026)
SUBSTATE_ENTRIES = (0x3a60a, 0x3a622, 0x3a670, 0x3a69c, 0x3a6b8, 0x3a6d4, 0x3a6fc, 0x3a724, 0x3a740, 0x3a7b6, 0x3a7e2, 0x3a7fe, 0x3a81a, 0x3a842, 0x3a86a,
                    0x3a886, 0x3a8d2, 0x3a910, 0x3a9aa, 0x3a9d6, 0x3a9f2, 0x3aa08, 0x3aa2a, 0x3aa52, 0x3aa6e, 0x3ab00, 0x3ab24)
CONTINUATIONS = (0x3a62a, 0x3a766, 0x3a8ac, 0x3a8f4, 0x3a932, 0x3aa7a, 0x3ab08, 0x3ab2c)
SLOT_TABLES = (0x3a63c, 0x3a782, 0x3a960)
STATE_ENTRIES = (0x3a62e, 0x3a774, 0x3a8ba, 0x3a8f8, 0x3aae8, 0x3ab0c)
UNROUTED_NEIGHBOURS = (0x3ab80, 0x3ab98, 0x3abde, 0x3abee, 0x3af6c, 0x3af74, 0x3b03c, 0x3b4bc, 0x3b4e0, 0x3b458, 0x3b62a, 0x3b648, 0x3b656, 0x1bf94, 0x1d1b0,
                       0x4db18, 0x44602, 0x4b6f4, 0x3ad48, 0x10fe00, 0x10fefe)
# helpers with their real return LONG inside the unit
CHAIN_RETURNS = {0x3b48c: (0x3ab34,), 0x1bf80: (0x3afa2,), 0x1d198: (0x3af94,)}
# producer blocks (JSR 49fc6) and the longer chains reaching them
PRODUCER_CHAINS = (0x3aefc, 0x3af5a, 0x3b020, 0x3aec4, 0x3af54, 0x3b012, 0x3affe)

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x10, 0x11, 0x12, 0x1b, 0x3f, 0x40, 0x7f, 0x80, 0x81, 0xbf, 0xef, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0x10, 0x100, 0x1e, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 0x10000, 0x7fff0000, 0x80000000, 0xffff0000, 0xffffffff, 0x2800, 0x270e, 0x200024)
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
    require(len(_ROUTE) >= 110, ('routing rules', len(_ROUTE)))


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


def insn(a):
    ins = decode(a)
    require(ins is not None, ('undecodable', hex(a)))
    return (a, ins.mnemonic.split('.')[0], ins.op_str, ins.size, ins.mnemonic)


def target(op):
    if op.startswith('('):
        return None                                             # JMP (A0) / JMP (A0,D1.W): computed
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
        if BCC.match(mn):
            return out, ('flow', {target(op), nxt})
        a = nxt
        if a in STARTS_SET or not mine(a):
            return out, ('flow', {a})


def static_next(start):
    out, res = walk(start)
    if res[0] == 'call':
        return {res[1]}
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
COMPUTED_JUMPS = (0x3ab7e, 0x3abda)                          # JMP (A0) / JMP (A0,D1.W): a target outside the unit is always a stop (it may be another unit's block interior)


def trace(state, outside, cap=CAP_INSN):
    """Run the original from state.pc natively until `outside(pc)` is true (checked from the second instruction on).  -> dict(pcs, stop, sr) or None."""
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
        if pcs and (outside(pc) or (pcs[-1] in COMPUTED_JUMPS and not mine(pc))):
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
    if stop is None or stop & 1 or m.odd is not None or m.invalid is not None or m.intr is not None or m.fetch_unmapped is not None or m.dev_reads:
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
        self.nodes = sorted(set(b.state['regs']['a6'] for b in bases))

    def pointer(self, a5):
        rng = self.rng
        pool = [0] + [0x1009a8 + 0xc4 * k for k in range(14)] + self.nodes + [a5 + 0x8cb8 - 0x10000, a5 + 0x8da8 - 0x10000, 0x200024, 0x200028]
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
            regs['a0'] = rng.choice(CONTINUATIONS + SLOT_TABLES + STATE_ENTRIES)        # live JMP (A0) / JMP (A0,D1.W) targets of the unit
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
        if rng.random() < 0.5:                                  # the sub-state fields in their natural ranges
            node = regs['a6']
            writes += [((node + 0x95) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4, 5, 0xff))), ((node + 0x96) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4, 5, 0xff))),
                       ((node + 0x9a) & 0xffff, 1, rng.choice((0, 1, 2, 3))), ((node + 0x9f) & 0xffff, 1, rng.choice((0, 3, 0x10, 0x11, 0x12)))]
        if rng.random() < 0.3:                                  # c(A6) -> a natural node, its 88.W / 9f.B in range
            parent = rng.choice(self.nodes)
            writes += [((regs['a6'] + 0xc) & 0xffff, 4, parent), ((parent + 0x88) & 0xffff, 2, rng.choice((0, 1, 2, 3))),
                       ((parent + 0x9f) & 0xffff, 1, rng.choice((0, 8, 0x10, 0x11, 0x12)))]
        sp = regs['a7']
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            writes += [((regs['a6'] + off) & 0xffff, size, val) for off, size, val in hint.get('a6off', [])]
            for w in hint.get('writes', []):
                if w[0] == 'sp':                                  # ('sp', offset, value): a LONG at A7 + offset
                    writes.append(((sp + w[1]) & 0xffff, 4, w[2]))
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
    require(len(STARTS) == 218 and len(STARTS_SET) == 218, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for pc in UNROUTED_NEIGHBOURS:
        require(unit_of(pc) is None, ('neighbour is routed', hex(pc)))
    for s in STARTS:
        require(unit_of(s) == UNIT, ('start is not routed to b2c', hex(s), unit_of(s)))
    rng = random.Random(0xB2C)
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
        return lambda pc: not mine(pc) and pc not in al

    def record(entry_pcs):
        visited.update(entry_pcs)
        for i in range(len(entry_pcs) - 1):
            pc = entry_pcs[i]
            if pc in cond_points:
                covered.add((pc, entry_pcs[i + 1]))

    for a, rec in all_instrs().items():
        _, mn, op, size, _ = rec
        if BCC.match(mn):
            cond_points[a] = {target(op), a + size}
    stats = dict(tries=0, rejected=0)
    # ---- block fixtures
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
    substate_fixtures(world, add, record)
    chain_fixtures(world, add, outside_unit, record)
    spawn_fixtures(add, record)
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
            unreachable.append((hex(a), hex(t)))
    never = sorted(set(STARTS) - visited)
    require(not never, ('block starts never executed by a fixture', [hex(x) for x in never]))
    error_fixtures(bases, add)
    negative_fixtures(out, add)
    META['carry_oracle'] = carry_oracle(out)
    META['visited_starts'] = len(set(STARTS) & visited)
    META['chain_only'] = [hex(x) for x in CONSUMERS]
    META['out_missing'] = out_missing
    META['unreachable'] = unreachable
    META['stats'] = stats
    sys.stderr.write('b2c: %d fixtures, visited starts %d/218, out_missing %s, unreachable %s\n' % (len(out), META['visited_starts'], out_missing, unreachable))
    return out


out_missing = []
unreachable = []
META = {}


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b2c: carry oracle skipped (no harness binary)\n')
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
            tr = trace(fx.state, lambda pc, stop=fx.stop: pc == stop, cap=fx.max_insn)
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('b2c: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the table indexes, the slot / continuation A0 values and the boundary values of every compare /
    test of the unit.  Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    if entry == 0x3ab3e:
        for v95 in (0, 1, 2, 3, 4, 5, 6, 0x7f, 0x80, 0xfe, 0xff):
            for v96 in (0xff, 0, 2, 4, 5):
                h.append(dict(a6off=[(0x95, 1, v95), (0x96, 1, v96)], regs=dict(a0=CONTINUATIONS[(v95 + v96) % len(CONTINUATIONS)], d2=0xa5a50000)))
    if entry == 0x3ab4c:
        h += [dict(a6off=[(0x96, 1, v)], regs=dict(d0=d)) for v in (0, 1, 2, 3, 4, 5, 6, 0xff) for d in (0, 3, 6)]
    if entry == 0x3ab5a:
        h += [dict(regs=dict(d0=d, d1=v, d2=0x00010000 * k)) for v in (0, 1, 2, 3, 4, 5) for d in (0, 1, 2, 3, 6, 16, 31) for k in (0, 0xffff)]
    if entry == 0x3ab6c:
        h += [dict(regs=dict(d0=v, a0=CONTINUATIONS[0])) for v in (0, 5, 0x7f, 0x80, 0xff, 0xffffff05)]
    if entry == 0x3ab72:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3, 4, 5, 6, 7, 0x10, 0x7f, 0x1234ff03)]
    if entry == 0x3ab7e:
        h += [dict(regs=dict(a0=v)) for v in CONTINUATIONS + STATE_ENTRIES]
    if entry in (0x3aba4,):
        h += [dict(regs=dict(a0=v)) for v in SLOT_TABLES]
    if entry == 0x3abaa:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3, 0xfffffffc)]
    if entry == 0x3abc0:
        for base in SLOT_TABLES:
            for d1 in (0, 1, 3):
                for v9a in (0, 1, 2, 3):
                    h.append(dict(a6off=[(0x9a, 1, v9a)], regs=dict(d1=d1, d2=0x12345678), writes=[('sp', 0, base)]))
        h.append(dict(a6off=[(0x9a, 1, 0xff)], regs=dict(d1=0xffffff07), writes=[('sp', 0, SLOT_TABLES[0])]))
    if entry in (0x3a744, 0x3a88a, 0x3a8d2, 0x3a910):
        h += byte(0x9d, (0, 0x10, 0xef, 0xff))
    if entry in (0x3a766, 0x3a8ac, 0x3aa7a, 0x3aa84):
        h += byte(0x94, (0, 1, 0x10, 0x11))
    if entry == 0x3aa8e:
        h += byte(0x97, (0, 0x7f, 0x80, 0xff))
    if entry == 0x3aa9c:
        h += byte(0xa3, (0, 1, 0xff))
    if entry == 0x3aaa4:
        h += [dict(a6off=[(0x95, 1, v), (0x96, 1, 3)]) for v in (0, 3, 0xfe, 0xff)]
    if entry in (0x3a97c, 0x3b48c):
        h += byte(0x9f, (0, 0x10, 0x11, 0x12, 0x80, 0xff))
    if entry in (0x3a674, 0x3a67a, 0x3a6d8, 0x3a700, 0x3a7ba, 0x3a7c0, 0x3a81e, 0x3a846, 0x3a9ae, 0x3a9b4, 0x3aa0c, 0x3aa2e):
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3)]
    if entry == 0x3b4a0:
        h += [dict(regs=dict(d1=v), a6off=[(0x15, 1, b)]) for v in (0, 1, 0x10, 0x11) for b in (0, 1)]
    if entry in (0x3aee4, 0x3affe):
        h += byte(0x15, (0, 1, 0x80, 0x81))
    if entry == 0x3aeca:
        h += byte(0x13, (0, 1, 0x7f, 0x80, 0xfe, 0xff))
    if entry == 0x3aed6:
        h += [dict(regs=dict(d0=d), a6off=[(0x3a, 2, w)]) for d in (1, 0x80, 0xff, 0x7fff, 0x8000) for w in (0, 1, 0x7fff, 0x8000, 0xffff)]
    if entry == 0x3af1c:
        h += byte(0x13, (0, 1, 0x7f, 0x80, 0xfe, 0xff))
    if entry == 0x3aea0:
        h += [dict(writes=[('parent', 0x9f, 1, v)]) for v in (0, 0x10, 0x11, 0x12, 0xff)]
    if entry in (0x3af86, 0x3afcc):
        h += [dict(writes=[('parent', 0x88, 2, v)]) for v in (0, 1, 2, 3)]
    if entry == 0x1bf80:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x100, 0xff)]
    if entry == 0x1d198:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3)]
    if entry == 0x3afa2:
        h += [dict(regs=dict(d0=v), a6off=[(0x22, 4, 0x200024)]) for v in (0, 1, 4, 8, 0x100)]
    return h


def substate_fixtures(world, add, record):
    """3a5be JSR (A0) with A0 = every sub-state entry, and N33 3a1e0 (MOVEA.L 82(A6),A0; JSR 3a5be) with 82(A6) := entry: the chain runs through every routed callee."""
    for via in (0x3a5be, 0x3a1e0):
        # 3a1e0 (N33): stop at its return point 3a1e8 after JSR 3a5be (the rest of the N33 callback is not this unit)
        stop_rule = (lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL) if via == 0x3a5be else \
            (lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL or pc == 0x3a1e8)
        flds = sorted(set(fields_of(0x3ab3e) + fields_of(0x3aba4) + fields_of(0x3abc0)))
        entries = SUBSTATE_ENTRIES if via == 0x3a5be else SUBSTATE_ENTRIES[::3]
        for e in entries:
            flds_e = sorted(set(flds + fields_of(e)))
            kept = {}
            for t in range(MAX_TRIES // 4):
                hint = dict(regs=dict(a0=e)) if via == 0x3a5be else dict(a6off=[(0x82, 4, e)])
                st = world.make(via, SENTINEL, flds_e, hint)
                tr = trace(st, stop_rule, cap=20000)
                if tr is None:
                    continue
                record(tr['pcs'] + [tr['stop']])
                path = tuple(pc for pc in tr['pcs'] if mine(pc) and pc in STARTS_SET)
                key = (tr['stop'], path[-1] if path else None)
                if key not in kept:
                    kept[key] = (st, tr)
                if len(kept) >= 2:
                    break
            require(kept, ('no sub-state world', hex(via), hex(e)))
            for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0))):
                add(U.Fixture('substate-%05x-%05x-%d' % (via, e, i), st, [], tr['stop'], meta=dict(family='substate', via=via, entry=e, stop=tr['stop'])))


def chain_fixtures(world, add, outside_unit, record):
    # helpers with their REAL return LONG inside the unit
    for entry, rets in sorted(CHAIN_RETURNS.items()):
        flds = fields_of(entry)
        for ret in rets:
            kept = {}
            for t in range(MAX_TRIES):
                st = world.make(entry, ret, flds + fields_of(ret))
                tr = trace(st, outside_unit())
                if tr is None:
                    continue
                record(tr['pcs'] + [tr['stop']])
                if tr['stop'] not in kept:
                    kept[tr['stop']] = (st, tr)
                if len(kept) >= 2:
                    break
            require(kept, ('no helper chain world', hex(entry)))
            for i, (stop, (st, tr)) in enumerate(sorted(kept.items())):
                add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, ret, i), st, [], stop, meta=dict(family='chain', entry=entry, consumer=ret)))
    # C produced by the routed 49fc6 and read by 3af12 / 3af60 / 3b026
    stop_rule = lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL
    for entry in PRODUCER_CHAINS:
        flds = fields_of(entry) + [('reg', 6, off, 1) for off in (0x15, 0x13)] + [('reg', 6, off, 4) for off in (0x8c, 0x90)]
        kept = {}
        for t in range(MAX_TRIES * 2):
            st = world.make(entry, SENTINEL, flds)
            tr = trace(st, stop_rule, cap=8000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            succ = None
            for i, pc in enumerate(tr['pcs'][:-1]):
                if pc in CONSUMERS:
                    succ = tr['pcs'][i + 1]
            key = (succ, tr['stop'])
            if succ is not None and key not in kept:
                kept[key] = (st, tr)
            if len(set(k[0] for k in kept)) >= 2:
                break
        require(kept, ('no chain world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items())):
            add(U.Fixture('chain-%05x-call-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='chain-call', entry=entry, consumer_successor=key[0])))
    # B2b 38d56 -> 3b5a6 (JSR 3b22a, 3a5d2, 4b82e, 4d98a) -> 38d60 (28ae child 3af86)
    kept = []
    flds = fields_of(0x3b5a6) + fields_of(0x3b5aa) + fields_of(0x3b5fa)
    for t in range(MAX_TRIES):
        st = world.make(0x38d56, SENTINEL, flds)
        tr = trace(st, stop_rule, cap=20000)
        if tr is None or 0x3b628 not in tr['pcs']:
            continue
        record(tr['pcs'] + [tr['stop']])
        kept.append((st, tr))
        if len(kept) >= 3:
            break
    require(kept, 'no 38d56 -> 3b5a6 world')
    for i, (st, tr) in enumerate(kept):
        add(U.Fixture('chain-38d56-3b5a6-%d' % i, st, [], tr['stop'], meta=dict(family='chain-call', entry=0x38d56, stop=tr['stop'])))


# 28ae children reached naturally: (child, parent PC, declared node edits of the parent, nodes)
SPAWNS = ((0x3af86, 0x38d56, ((), ((0x62, 1, 0),), ((0x62, 1, 0xff),))),
          (0x3ae84, 0x3a4da, (((0xb2, 1, 0), (0x10f001, 1, 4)), ((0xb2, 1, 0), (0x9f, 1, 0x10), (0x10f001, 1, 4)), ((0xb2, 1, 0), (0x9f, 1, 0x12), (0x10f001, 1, 4)))))
# an edit offset >= 100000 is an absolute work-RAM address (BYTE 10f001 bit 2 makes 4d6b4 return Set: 3a4da reaches the 28ae child 3ae84)


def spawn_fixtures(add, record):
    made = {}
    for child, parent, edits in SPAWNS:
        for case in SEEDS:
            for k in NODE_INDEX[:2]:
                base = U.seed_node_fixture(case, FRAME, node=k, name='spawn-base')
                require(base is not None, ('missing node', case, k))
                node = base.state['regs']['a6']
                for j, ed in enumerate(edits):
                    st = U.with_host_writes(base.state, [((off if off >= 0x100000 else node + off) & 0xffff, size, v) for off, size, v in ed], pc=parent)
                    try:
                        cst, rest, _ = U.advance_native(st, base.queue, child, external_status=base.external_status, max_insn=400000)
                    except (RuntimeError, TypeError):
                        continue
                    a7 = cst['regs']['a7'] & 0xffff
                    ret = int.from_bytes(cst['ram'][a7:a7 + 4], 'big')
                    tr = trace(cst, lambda pc, ret=ret: unit_of(pc) is None or pc == ret or pc == 0x2a00, cap=20000)
                    if tr is None:
                        continue
                    record(tr['pcs'] + [tr['stop']])
                    add(U.Fixture('spawn-%05x-from-%05x-s%d-n%d-%d' % (child, parent, case, k, j), cst, rest, tr['stop'], external_status=base.external_status,
                                  meta=dict(family='spawn', child=child, parent=parent, case=case, node=k, stop=tr['stop'], ret=ret)))
                    made[child] = made.get(child, 0) + 1
    META['spawns'] = dict((hex(k), v) for k, v in made.items())
    sys.stderr.write('b2c: natural spawns %s\n' % META['spawns'])
    require(made.get(0x3af86, 0) >= 1 and made.get(0x3ae84, 0) >= 1, ('a 28ae child was not reached naturally', META['spawns']))


def error_fixtures(bases, add):
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in STARTS_SET:
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b2c PC')))
    for pc in UNROUTED_NEIGHBOURS:
        add(U.Fixture('error-unrouted-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-odd-pc', U.with_host_writes(st, pc=0x3a60b), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'objects b2c caller requires known carry')))
    node = st['regs']['a6']
    # JMP (A0) of 3ab7e and JMP (A0,D1.W) of 3abc0: a work-RAM target (unrouted) and an odd target; the LONG table read of 3ab72 to a RAM pointer is a match fixture
    add(U.Fixture('error-3ab7e-ram-target', U.with_host_writes(st, regs=dict(a0=0x10fe00), pc=0x3ab7e), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-3ab7e-odd-target', U.with_host_writes(st, regs=dict(a0=0x3a62b), pc=0x3ab7e), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    sp = st['regs']['a7']
    add(U.Fixture('error-3abc0-ram-target', U.with_host_writes(st, [(sp & 0xffff, 4, 0x10fe40), ((node + 0x9a) & 0xffff, 1, 0)], regs=dict(d1=0), pc=0x3abc0), [], SENTINEL,
                  ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-3abc0-odd-target', U.with_host_writes(st, [(sp & 0xffff, 4, 0x3a63d), ((node + 0x9a) & 0xffff, 1, 0)], regs=dict(d1=0), pc=0x3abc0), [], SENTINEL,
                  ('error', 'unaligned animation machine PC')))
    # 3ab72 has no bound check: BYTE index 6 reads the WORD masks of the original ROM as the LONG 00010002, an interior PC of F6c (that unit's checked error)
    add(U.Fixture('error-3ab72-index-6', U.with_host_writes(st, regs=dict(d0=6), pc=0x3ab72), [], SENTINEL, ('error', 'unsupported animation irq f6c PC')))
    add(U.Fixture('error-3a5be-ram-substate', U.with_host_writes(st, regs=dict(a0=0x10fe80), pc=0x3a5be), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    # odd LONG install 82(A6) (A6 odd) and an odd LONG (A6) install
    add(U.Fixture('error-3a614-odd-install', U.with_host_writes(st, regs=dict(a6=node + 1), pc=0x3a614), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    add(U.Fixture('error-3aff8-odd-install', U.with_host_writes(st, regs=dict(a6=node + 1), pc=0x3aff8), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    want = ('block-3ab34-0', 'block-3aed6-0', 'block-3abc0-0', 'block-1d198-0')
    picks = [fx for fx in out if fx.name in want]
    require(len(picks) == len(want), ('negative picks', [f.name for f in picks]))
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0x95) & 0xffff, 0x40)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1))))
    add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
    add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
