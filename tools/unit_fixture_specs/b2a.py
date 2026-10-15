"""V1 fixture spec of the animation-machine unit B2a (engine/src/animation_machine_objects_b2a.cpp, 180 block starts).

Blocks: the three orphan 28ae children of the seed 32 33 objects: 5eed2 (N25 child, 28), 5f504 (N26 child, 53) and 60516 (N27 child, 99).  The Bcc blocks 5f592 5f678 60680 (a second Bcc on the flags
of the Bcc before it) and 60690 (the BLT on the flags of the two CMPI predecessors 60684 / 6068c) are folded into their predecessors and are interior PCs (checked errors).  4b6f4 (the pinned
area_clear verifier) and 44602 stay boundaries; every callee and child value outside the three ranges is a boundary or data.

Fixture families (everything is native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start is entered directly.  The world is a natural N-pass node state of the D1 seeds 32/33 (frame 2: the N25 nodes 5e940 5eb74 5f094, the N26 nodes 5f2c4 5f7ec, the N27
            nodes 5fd9a 60086; node A6, A5, bank and RAM are natural) with a declared host edit of D0-D7, A0-A4, the node and slot fields the reachable blocks of the unit read (values drawn from a
            seeded generator, boundary hints for every compare / test) and PC := the block start.  The stop is the first PC outside the unit (a callee, the sentinel return LONG, a JMP target).
            Worlds are kept per entry while they add a new successor of the entry block (both sides of every branch of the block, the three-way folded blocks 5f584 5f66a 60670 included).
  coverage  worlds that reach a conditional branch outcome (of any instruction of the unit, the folded Bcc included) that the block fixtures did not take.
  chain     the call chains whose C is produced by a routed callee and consumed inside the unit (49fc6 -> 5efc6, 1ab02 -> 5ef80 5efda, 4b54e -> 5f6c2 60880, 28ae -> 5f702 6062e 606f4 6077e 6085e
            60902, 2986 -> 60828 608cc through MOVEM.W): native branches on the real flags, the C++ branches on the known C; the 28ae count limit (WORD 104ca0) is edited for both outcomes.
  c4b6f4    the consumers 5ef6c 5f5e6 5f744 of the boundary 4b6f4: the NATIVE run starts at 4b6f4 (TST.B 5b86(A5); BEQ; ORI.B #1,CCR; RTS) with the consumer as the return LONG, the C++ run
            (cpp_state) starts at the consumer with A7 + 4 and the carry tag the native 4b6f4 leaves (Clear for BYTE 5b86(A5) = 0, Set otherwise): both outcomes of each consumer.
  error     every even non-start PC of the unit ranges (the folded Bcc 5f592 5f678 60680 60690 included), the unrouted neighbours (4b6f4 44602 5eed0 5f4b0 5f502 60514 6093a), an odd PC, Unknown C at
            the 16 consumers, an odd LONG write, the boundary stops 5ef66 -> 4b6f4 and 6064a -> 44602 without a stop PC: checked error, state preserved.
  negative  C++ input differs from the native input in one RAM bit / one register / the queue: the comparison must report it.
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (32, 33)
FRAME = 2
NODE_INDEX = (20, 18, 16, 14, 12, 8, 7)  # frame 2 of seeds 32/33: N25 5e940 5eb74 5f094, N26 5f2c4 5f7ec, N27 5fd9a 60086
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x5eed2, 0x5efe6), (0x5f504, 0x5f760), (0x60516, 0x6093a)]
STARTS = [int(x, 16) for x in (
    '5eed2 5eee2 5eef8 5ef06 5ef14 5ef3c 5ef42 5ef48 5ef4e 5ef58 5ef60 5ef66 5ef6c 5ef70 5ef76 5ef80 5ef84 5ef8a 5ef8c 5efb4 5efba 5efc0 5efc6 5efca 5efd0 '
    '5efda 5efde 5efe4 5f504 5f50a 5f520 5f54e 5f576 5f57c 5f584 5f596 5f59e 5f5a2 5f5ba 5f5c8 5f5ce 5f5da 5f5e0 5f5e6 5f5ea 5f5f0 5f5f2 5f602 5f62e 5f63c '
    '5f664 5f66a 5f67c 5f684 5f688 5f694 5f69a 5f6a8 5f6b6 5f6bc 5f6c2 5f6c6 5f6ca 5f6d4 5f6da 5f6e2 5f6ea 5f6f2 5f702 5f706 5f714 5f718 5f71e 5f728 5f738 '
    '5f73e 5f744 5f748 5f74e 5f758 5f75e 60516 6051c 6053c 60546 60554 60568 6056c 6057a 605a2 605ae 605be 605c6 605d4 605dc 605e0 605ee 605f4 605f8 60600 '
    '6060a 60616 6061e 6062e 60632 60640 60644 6064a 60670 60684 6068c 60694 6069a 6069c 606b2 606ba 606be 606c6 606d0 606dc 606e4 606f4 606f8 60706 6070a '
    '60710 60718 60720 60724 60728 60730 60734 60742 6074a 6074e 60756 60760 60766 6076e 6077e 60782 60790 60794 6079a 607a8 607b0 607b4 607c2 607d0 607d6 '
    '607de 607e6 607ee 607f6 60828 60830 6084a 6084e 6085e 60862 60870 60874 6087a 60880 60884 60888 60892 6089a 608cc 608d4 608ee 608f2 60902 60906 60914 '
    '60918 6091e 60926 60932 60938 ').split()]
FOLDED = (0x5f592, 0x5f678, 0x60680, 0x60690)
CONSUMERS = tuple(int(x, 16) for x in '5ef6c 5ef80 5efc6 5efda 5f5e6 5f6c2 5f702 5f744 6062e 606f4 6077e 6085e 60880 60902 60828 608cc'.split())
B4B6F4_CONSUMERS = (0x5ef6c, 0x5f5e6, 0x5f744)
UNROUTED_NEIGHBOURS = (0x4b6f4, 0x44602, 0x5eed0, 0x5f4b0, 0x5f502, 0x60514, 0x6093a)
# producer blocks (a JSR of a routed callee that returns the C) whose consumer is the next block: entry -> consumer
PRODUCER_CHAINS = (0x5efc0, 0x5ef76, 0x5efd0, 0x5f6bc, 0x6087a, 0x6061e, 0x606e4, 0x6076e, 0x6084e, 0x608f2, 0x5f6f2, 0x607f6, 0x6089a)

VB = (0, 1, 2, 3, 4, 5, 7, 8, 0x10, 0x11, 0x12, 0x18, 0x1a, 0x1b, 0x1c, 0x20, 0x40, 0x41, 0x60, 0x7f, 0x80, 0x81, 0xbf, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 0x10, 0x100, 0x140, 0x141, 0x1e, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffdf, 0xffe0, 0xfffe, 0xffff)
VL = (0, 1, 0x10000, 0x40000, 0x90000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfffc0000, 0xfff80000, 0xfff20000, 0xffffffff, 0xffffc000, 0x2800, 0x270e)
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


STARTS_SET = set()
FOLDED_SET = set(FOLDED)


def insn(a):
    ins = decode(a)
    require(ins is not None, ('undecodable', hex(a)))
    return (a, ins.mnemonic.split('.')[0], ins.op_str, ins.size, ins.mnemonic)


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op)
    return int(m.group(1), 16) if m else None


def walk(start):
    """Instruction records of the block at `start` (folded Bcc included) and its static outcome: ('call', target, ret) | ('rts',) | ('flow', {successors})."""
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
        if mn == 'jmp':
            return out, ('flow', {target(op)})
        if mn == 'bra':
            t = target(op)
            if t in FOLDED_SET:
                a = t
                continue
            return out, ('flow', {t})
        if BCC.match(mn):
            succ = set()
            t = target(op)
            if t in FOLDED_SET:
                succ |= walk_fold(t, out)
            else:
                succ.add(t)
            if nxt in FOLDED_SET:
                succ |= walk_fold(nxt, out)
            else:
                succ.add(nxt)
            return out, ('flow', succ)
        a = nxt
        if a in STARTS_SET:
            return out, ('flow', {a})


def walk_fold(a, out):
    recs, res = walk_from(a)
    out.extend(recs)
    return res


def walk_from(a):
    """The folded Bcc at `a` (a single Bcc instruction): its two outcomes."""
    rec = insn(a)
    _, mn, op, size, _ = rec
    require(BCC.match(mn), ('folded PC is not a Bcc', hex(a)))
    return [rec], {target(op), a + size}


def static_next(start):
    out, res = walk(start)
    if res[0] == 'call':
        return {res[1]}
    if res[0] == 'rts':
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
        sp = regs['a7']
        writes.append(((sp) & 0xffff, 4, ret))
        if hint:
            writes += [((regs['a6'] + off) & 0xffff, size, val) for off, size, val in hint.get('a6off', [])]
            for w in hint.get('writes', []):
                writes.append(w)
            regs.update(hint.get('regs', {}))
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
def all_instrs():
    """Every instruction of the three ranges (start -> record), for the conditional branch table."""
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
    global STARTS_SET
    STARTS_SET = set(STARTS)
    require(len(STARTS) == 180 and len(STARTS_SET) == 180, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for pc in UNROUTED_NEIGHBOURS:
        require(unit_of(pc) is None, ('neighbour is routed', hex(pc)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b2a_block', ('start is not routed to b2a', hex(s), unit_of(s)))
    for pc in FOLDED:
        require(pc not in STARTS_SET and unit_of(pc) == 'animation_objects_b2a_block', ('folded', hex(pc)))
    rng = random.Random(0xB2A)
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
    allins = all_instrs()

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

    # branch outcomes of the unit (both sides of each Bcc, the folded ones included)
    for a, (_, mn, op, size, _) in allins.items():
        if BCC.match(mn):
            cond_points[a] = {target(op), a + size}

    def next_block(pcs, stop):
        """The first block start (or the stop) after the entry instruction."""
        for pc in pcs[1:] + [stop]:
            if pc in STARTS_SET or not mine(pc):
                return pc
        return None

    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        needed = static_next(entry)
        flds = fields_of(entry)
        kept = {}
        extra = 0
        hints = hint_worlds(entry)
        for t in range(MAX_TRIES + len(hints)):
            stats['tries'] += 1
            st = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
            tr = trace(st, outside_unit())
            if tr is None:
                stats['rejected'] += 1
                continue
            record(tr['pcs'] + [tr['stop']])
            nxt = next_block(tr['pcs'], tr['stop'])
            if nxt is None or nxt in CONSUMERS:
                continue                                        # the native flags at a consumer entered by a jump are not a known C
            if t < len(hints):
                kept[('h', t)] = (st, tr, nxt)                  # declared boundary / table worlds are always kept
                if nxt not in kept:
                    kept[nxt] = (st, tr, nxt)
            elif nxt not in kept:
                kept[nxt] = (st, tr, nxt)
            elif extra < 1 and (needed is None or len(needed) <= 1):
                extra += 1
                kept[(nxt, extra)] = (st, tr, nxt)
            if needed is not None and len(needed) > 1 and set(k for k in kept if isinstance(k, int)) >= needed and t >= len(hints):
                break
            if (needed is None or len(needed) <= 1) and len(kept) >= 2 and t >= len(hints):
                break
        require(kept, ('no world for the block', hex(entry)))
        seen_worlds = set()
        for i, key in enumerate(sorted(kept, key=lambda k: (0, k) if isinstance(k, int) else (1, k[1]))):
            st, tr, nxt = kept[key]
            if id(st) in seen_worlds:
                continue
            seen_worlds.add(id(st))
            add(U.Fixture('block-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='block', entry=entry, successor=nxt)))
        if needed and len(needed) > 1:
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)))
            if missing:
                out_missing.append((entry, missing))
    chain_fixtures(world, add, outside_unit, record)
    b4b6f4_fixtures(world, add, outside_unit, record)
    consumer_clear_fixtures(world, add, outside_unit, record)
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
    sys.stderr.write('b2a: visited starts %d/%d, branch outcomes not reached %s, multi-successor entries missing %s, tries %d rejected %d\n' % (
        len(set(STARTS) & visited), len(STARTS), [(hex(a), hex(t)) for a, t in unreachable], [tuple(str(x) for x in m) for m in out_missing], stats['tries'], stats['rejected']))
    return out


out_missing = []
unreachable = []
META = {}


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b2a: carry oracle skipped (no harness binary)\n')
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
            tr = trace(fx.state, lambda pc, stop=fx.stop: pc == stop)
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('b2a: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit.
    Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    if entry in (0x5f584, 0x5f66a):
        h += byte(0x94, (0, 1, 0x7f, 0x80, 0xff))                                    # TST.B 94(A6): Z, positive, N
    if entry in (0x5f57c, 0x605be, 0x60616, 0x606dc, 0x60766):
        h += word(0x7e, (0, 1, 2, 0xffff))                                           # SUBQ.W #1,7e(A6): borrow only for 0
    if entry == 0x5f5ce:
        h += long_(0x36, (0xffff, 0x10000, 0x10001, 0x7fffffff, 0x80000000, 0xffffffff))
    if entry == 0x5f688:
        h += [dict(a6off=[(0x96, 4, a), (0x9a, 4, b)]) for a, b in ((1, 2), (5, 5), (6, 5), (0xfffffff0, 0x10), (0x10, 0xfffffff0), (0x80000000, 0x7fffffff), (0x7fffffff, 0x80000000))]
    if entry == 0x5f71e:
        h += word(0x42, (0x13f, 0x140, 0x141, 0x7fff, 0x8000, 0xffff))
    if entry == 0x5f728:
        h += word(0x46, (0xff, 0x100, 0x1ff, 0x200, 0x50, 0x8000, 0))
    if entry == 0x5f74e:
        h += word(0x42, (0xffdf, 0xffe0, 0xffe1, 0x10, 0x8000, 0x7fff))
    if entry in (0x5f6ea, 0x607e6):
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 0x10000, 0xffff, 0x80000000, 0xabcd0000)]
    if entry in (0x5f6da, 0x607d6):
        h += long_(0x72, (0, 0x1009a8, 0x100a6c))
    if entry in (0x5f6ca, 0x60888):
        h += byte(0x61, (0x7f, 0x80))
    if entry in (0x607ee, 0x60892, 0x60546):
        h += byte(0x8f, (0, 1))
    if entry in (0x60600, 0x606c6, 0x60756):
        h += byte(0x15, (0, 1, 0x80, 0x81, 0xfe))
    if entry == 0x605ae:
        h += [dict(a6off=[(0xc, 4, 0x1009a8)], writes=[(0x1009a8 + 0x77 & 0xffff, 1, v)]) for v in (0, 1, 2, 3, 4, 5, 6)]
    if entry in (0x605f8, 0x606be, 0x6074e, 0x6091e):
        want = {0x605f8: 2, 0x606be: 3, 0x6074e: 5, 0x6091e: 3}[entry]
        h += [dict(regs=dict(d0=v)) for v in (want - 1, want, want + 1, 0, 0xff)]
    if entry == 0x60670:
        h += [dict(regs=dict(d0=a), a6off=[(0x8e, 1, b)]) for a, b in ((0x50, 0x50), (0x60, 0x50), (0x10, 0x50), (0xff, 0), (0, 0xff), (0x1234, 0x34), (0x8000, 1), (1, 0))]
    if entry in (0x60684, 0x6068c):
        h += [dict(regs=dict(d0=v)) for v in (0x7f, 0x80, 0x81, 0x8000, 0x7fff, 0xff80, 0xff7f, 0xff81, 0, 0xffff)]
    if entry in (0x605e0, 0x6069c, 0x60734, 0x6079a):
        lim = {0x605e0: 0x40000, 0x6069c: 0xfffc0000, 0x60734: 0xfffc0000, 0x6079a: 0xfff80000}[entry]
        h += long_(0x90, (lim, (lim - 1) & 0xffffffff, (lim + 1) & 0xffffffff, 0x7fffffff, 0x80000000, 0))
    if entry in (0x605c6, 0x60710):
        h += byte(0x8e, (0, 0x7f, 0x80, 0xff))
    if entry in (0x60718, 0x60728):
        h += [dict(regs=dict(d0=v)) for v in (0x40, 0x41, 0x3f, 0x7f, 0, 0xc0, 0xbf, 0xc1, 0x80, 0xff)]
    if entry == 0x60926:
        h += word(0x42, (0x13f, 0x140, 0x141, 0, 0xffff))
    if entry == 0x6064a:
        h += [dict(a6off=[(0xc, 4, 0x1009a8)], writes=[(0x1009a8 + 0xc & 0xffff, 4, 0x1009a8 + 0xc4)])]
    if entry == 0x5f50a:
        h += [dict(regs=dict(d0=v)) for v in (0, 3, 0x1f, 0x20, 0xf, 0x12345678, 0xffffffff)]
    if entry == 0x5f602:
        h += [dict(regs=dict(d0=v)) for v in (0, 0x1fff, 0x2000, 0xabcd1234, 0xffffffff)]
    if entry == 0x6051c:
        h += [dict(regs=dict(d0=v)) for v in (0, 0x3f, 0x40, 0xffffffff)]
    if entry in (0x5f694, 0x605ee):
        h += [dict(regs=dict(d0=v), a6off=[(0x96, 4, 0x100), (0x90, 4, 0x100)]) for v in (0xfffffff0, 0x100, 0x80000000, 0x7fffffff, 0)]
    if entry == 0x5f5a2:
        h += long_(0x96, (0, 0x40000, 0xfffc0000, 0x80000000, 0x7fffffff, 1, 0x1f))
    return h


def node_of(st):
    return st['regs']['a6']


def chain_fixtures(world, add, outside_unit, record):
    """The call chains whose C is made by a routed callee and read by a consumer inside the unit."""
    rng = world.rng
    for entry in PRODUCER_CHAINS:
        flds = fields_of(entry) + [('reg', 6, off, 4) for off in (0xc, 0x82)] + [('reg', 6, off, 1) for off in (0x15, 0x61, 0x62)]
        kept = {}
        for t in range(MAX_TRIES * 3):
            hint = None
            if entry in (0x6061e, 0x606e4, 0x6076e, 0x6084e, 0x608f2, 0x5f6f2):
                hint = dict(writes=[(0x104ca0 & 0xffff, 2, rng.choice((0, 5, 0xa, 0xb, 0x14, 0x15, 0x100)))])    # 28ae: the count limit decides success (C set) / failure (C clear)
            elif entry in (0x5ef76, 0x5efd0):
                # 1ab02: the screen test of the position LONGs 46 / 4e (Y) and 42 / 4a (X); C set = off screen
                hint = dict(a6off=[(0x46, 4, rng.choice((0, 0x03000000, 0x00100000, 0xfff00000, 0x80000000))), (0x4e, 4, rng.choice((0, 0x00010000, 0x7fff0000))),
                                   (0x42, 4, rng.choice((0, 0x01500000, 0x00100000, 0xff000000))), (0x4a, 4, rng.choice((0, 0x00010000)))])
            elif entry in (0x607f6, 0x6089a):
                # 2986 (buffer_cue) accepts the success path only (its failure path needs a known X): limit above the child count 14
                hint = dict(writes=[(0x104ca0 & 0xffff, 2, rng.choice((0x15, 0x100, 0x400)))])
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, lambda pc: unit_of(pc) is None or pc == 0x2a00 or pc == SENTINEL, cap=6000)
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
            if len(kept) >= 4:
                break
        require(kept, ('no chain world', hex(entry)))
        outcomes = set(k[0] for k in kept)
        if len(outcomes) < 2 and entry not in (0x607f6, 0x6089a):
            out_missing.append((entry, 'one consumer outcome only', [hex(x) for x in outcomes]))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: (kv[0][0], kv[0][1]))):
            add(U.Fixture('chain-%05x-call-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='chain-call', entry=entry, consumer_successor=key[0])))


def b4b6f4_fixtures(world, add, outside_unit, record):
    """4b6f4 is a boundary: native starts at 4b6f4 (return LONG = the consumer), the C++ run starts at the consumer with the carry tag 4b6f4 leaves
    (TST.B 5b86(A5); BEQ 4b700 / ORI.B #1,CCR; RTS: Clear for a zero BYTE, Set otherwise)."""
    for consumer in B4B6F4_CONSUMERS:
        flds = fields_of(consumer)
        for flag in (0, 1):
            kept = 0
            seen = set()
            for t in range(MAX_TRIES * 2):
                st = world.make(0x4b6f4, consumer, flds)
                a5 = st['regs']['a5']
                st = U.with_host_writes(st, [((a5 + 0x5b86) & 0xffff, 1, 0 if flag == 0 else rng_nonzero(world))])
                tr = trace(st, outside_unit(range(0x4b6f4, 0x4b702, 2)))
                if tr is None or tr['pcs'][:1] != [0x4b6f4] or consumer not in tr['pcs']:
                    continue
                record(tr['pcs'] + [tr['stop']])
                i = tr['pcs'].index(consumer)
                succ = None
                for pc in tr['pcs'][i + 1:] + [tr['stop']]:
                    if pc in STARTS_SET or not mine(pc):
                        succ = pc
                        break
                if succ is None or succ in seen:
                    continue
                seen.add(succ)
                cpp = dict(U.with_host_writes(st, regs=dict(a7=(st['regs']['a7'] + 4) & 0xffffffff), pc=consumer), carry=1 if flag == 0 else 2)
                add(U.Fixture('c4b6f4-%05x-%d-%d' % (consumer, flag, kept), st, [], tr['stop'], cpp_state=cpp,
                              meta=dict(family='c4b6f4', consumer=consumer, byte_5b86_nonzero=flag, successor=succ)))
                kept += 1
                if kept >= 2:
                    break
            require(kept >= 1, ('no 4b6f4 world', hex(consumer), flag))


def consumer_clear_fixtures(world, add, outside_unit, record):
    """Every consumer entered directly with the carry tag Clear: the native CPU starts with CCR = 0 (C clear), so the BCC takes the clear branch on both sides.
    (The Set side comes from the real producers: the chains, and the 4b6f4 fixtures; 2986 only returns its success path, so 60828 / 608cc get their Clear side here.)"""
    for consumer in CONSUMERS:
        flds = fields_of(consumer)
        kept = 0
        seen = set()
        for t in range(MAX_TRIES):
            st = world.make(consumer, SENTINEL, flds)
            tr = trace(st, outside_unit())
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            succ = next_block_of(tr)
            if succ is None or succ in seen:
                continue
            seen.add(succ)
            add(U.Fixture('consumer-clear-%05x-%d' % (consumer, kept), dict(st, carry=1), [], tr['stop'], meta=dict(family='consumer-clear', consumer=consumer, successor=succ)))
            kept += 1
            if kept >= 2:
                break
        require(kept >= 1, ('no clear world', hex(consumer)))


# natural child spawns: the parent block that does MOVEA.L #child,A0; MOVE.W #a,D0; JSR 28ae is entered on a natural parent node (frame 2 of seeds 32 / 33); the ORIGINAL code
# runs on (28ae allocates the child node, the dispatcher reaches it) up to the child's first callback PC, from where the fixture runs the child to its first boundary or to
# the dispatcher return LONG.
SPAWNS = ((0x5eed2, (0x5ee20, 0x5ee4e), (18,)), (0x5f504, (0x5f3b4, 0x5f3da, 0x5f404, 0x5f42a), (14,)), (0x60516, (0x6018e, 0x601b8), (8, 7)))


def spawn_fixtures(add, record):
    made = {}
    for child, parents, nodes in SPAWNS:
        for case in SEEDS:
            for k in nodes:
                base = U.seed_node_fixture(case, FRAME, node=k, name='spawn-base')
                require(base is not None, ('missing node', case, k))
                for parent in parents:
                    st = U.with_host_writes(base.state, pc=parent)
                    try:
                        cst, rest, _ = U.advance_native(st, base.queue, child, external_status=base.external_status)
                    except RuntimeError:
                        continue
                    a7 = cst['regs']['a7'] & 0xffff
                    ret = int.from_bytes(cst['ram'][a7:a7 + 4], 'big')
                    tr = trace(cst, lambda pc, ret=ret: unit_of(pc) is None or pc == ret, cap=20000)
                    if tr is None:
                        continue
                    record(tr['pcs'] + [tr['stop']])
                    add(U.Fixture('spawn-%05x-from-%05x-s%d-n%d' % (child, parent, case, k), cst, rest, tr['stop'], external_status=base.external_status,
                                  meta=dict(family='spawn', child=child, parent=parent, case=case, node=k, stop=tr['stop'], ret=ret)))
                    made[child] = made.get(child, 0) + 1
    for child, _, _ in SPAWNS:
        require(made.get(child, 0) >= 1, ('no natural spawn reached the child', hex(child)))


def next_block_of(tr):
    for pc in tr['pcs'][1:] + [tr['stop']]:
        if pc in STARTS_SET or not mine(pc):
            return pc
    return None


def rng_nonzero(world):
    return world.rng.choice((1, 2, 0x7f, 0x80, 0xff))


def error_fixtures(bases, add):
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)
    # every even PC of the unit ranges that is not a block start (the folded Bcc included)
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                add(U.Fixture('error-internal-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation objects b2a PC')))
    for pc in UNROUTED_NEIGHBOURS:
        add(U.Fixture('error-unrouted-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-odd-pc', U.with_host_writes(st, pc=0x5eed3), [], SENTINEL, ('error', 'unaligned animation machine PC')))
    # Unknown C at the 16 consumers (carry tag 0)
    for pc in CONSUMERS:
        add(U.Fixture('error-unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), [], SENTINEL, ('error', 'objects b2a caller requires known carry')))
    # odd LONG write (5eee2 stores 36(A6)): A6 odd
    add(U.Fixture('error-5eee2-odd-store', U.with_host_writes(st, regs=dict(a6=st['regs']['a6'] + 1), pc=0x5eee2), [], SENTINEL, ('error', 'invalid animation machine write size/alignment')))
    # boundary stop without a stop PC: 5ef66 -> JSR 4b6f4, 6064a -> JSR 44602
    add(U.Fixture('error-boundary-4b6f4', U.with_host_writes(st, pc=0x5ef66), [], SENTINEL, ('error', 'unsupported animation machine PC')))
    add(U.Fixture('error-boundary-44602', U.with_host_writes(st, pc=0x6064a), [], SENTINEL, ('error', 'unsupported animation machine PC')))


def negative_fixtures(bases, out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.name in ('block-5f5a2-0', 'block-5f602-0', 'block-5f50a-0', 'block-6051c-0')]
    for fx in picks[:4]:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, st['regs']['a6'] & 0xffff | 0x5e)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
