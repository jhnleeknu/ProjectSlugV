"""V1 fixture spec of the animation-machine unit FR2a (engine/src/animation_machine_objects_fr2.cpp, 218 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr2-contract.md): the IO-frontier objects c0ace (the b3dbc kind handler; install c0b52) with
the shared item routines b4958 (b489e b476a b4760 b4664 b4680 b46c0 b4ab0 b4aca b4334 b442e), the b433c table tests b4354 / b437a, the item handler
b445e, the player touch helpers 1c8a4 / 1c1f4, the BCD score add e62a8 (ABCD) and the score display child e991c / e9b5a; the result-screen rank entry
e5580 (installs e5596 e55e2) with e6556 e6516 e65b0 e63ec e693a; the FR1b child b33d8 (install b342e); the card-menu draw handler a8ee with a770 /
a772 (DIVU) and 9ee6 / 9ef8 / 9f12.

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR1c) with declared host edits.  A second
natural source are the IO observation states (artifacts/animation_machine_io_native, states/*.pack.gz): the confirmed frontier frames of the FR1c IO
rerun (ms5-scratch/fr1c/ioA/frontier.json: P1 / P1b frame 99 node 1020f8 b3dbc -> c0ace, frame 245 node 1013f4 e5580, frame 120 node 101f70 b33d8,
boot-title-start frame 113 a8ee) are the real entry states of this unit.  This spec does not decode those packs (the IO comparison rerun checks the
natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the seven consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node or a
            player record, the item records b3894 + 12k, the pointers the blocks follow (LONG 8c(A0), 8c of the player records, LONG -ee(A5), LONG
            c(A6)), the node / record fields the reachable blocks read, the stack LONG / WORD values the entered block pops, PC := the block start).
            Stop: the first PC outside the unit (a callee, the sentinel return LONG, JMP 2a00 / 1aa7e / 49260 / cd58, a TRAP site, a live JSR target).
            b47f4 recomputes the C of b47de (unsigned D1.W < D0.W) and b48ba the Z of TST.W (A1) (contract decision 4): the native run starts with SR
            2000 (C = Z = 0), so a direct entry at b47f4 declares D1.W >= D0.W and at b48ba WORD (A1) != 0; the other outcomes are covered through
            their predecessors.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 288c -> b3454 (b344e), 289e -> b48e8 (b48dc), b4760 (b4aca, U01 1aa7e) -> b4a18 (b4a14),
            the table tests b4354 / b437a -> b478e (b4780) b47b2 (b47a4) b491a (b48ec), the item handler -> b46ac (b46a2); the passing RTS b433a (49fc6,
            b4334) and 1c230 (1c1f4) run to the sentinel.  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the seven consumers, odd node / record / stack pointers, DIVU zero divisor,
            failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs
            from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR1c specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR1c)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
PLAYERS = (0x100cb8, 0x100da8)          # the player records 1c8ba / b46c0 use
ITEMS = 0xb3894                         # the item records (12 bytes x 110, fixed ROM)
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x9ee6, 0x9ef2), (0x9ef8, 0x9f24), (0xa770, 0xa7e0), (0xa8ee, 0xa8f8), (0x1c1f4, 0x1c238), (0x1c8a4, 0x1c8f0), (0xb33d8, 0xb3460),
          (0xb4334, 0xb433c), (0xb4354, 0xb43de), (0xb442e, 0xb4464), (0xb4664, 0xb466c), (0xb4680, 0xb46be), (0xb46c0, 0xb46f6), (0xb4760, 0xb4806),
          (0xb489e, 0xb4a24), (0xb4ab0, 0xb4ab6), (0xb4aca, 0xb4ad4), (0xc0ace, 0xc0ba8), (0xc1d2e, 0xc1d34), (0xe5580, 0xe5614), (0xe62a8, 0xe62ec),
          (0xe63ec, 0xe63fa), (0xe6516, 0xe6570), (0xe6582, 0xe65dc), (0xe693a, 0xe6952), (0xe991c, 0xe995c), (0xe9b5a, 0xe9b8a)]
STARTS = [int(x, 16) for x in (
    '9ee6 9ef8 9f12 a770 a772 a77a a784 a788 a796 a7ac a7c0 a7c2 a8ee 1c1f4 1c230 1c232 1c8a4 1c8ac 1c8b8 1c8ba 1c8c8 1c8ce 1c8e8 1c8ee '
    'b33d8 b33e2 b3400 b3428 b342e b3434 b343a b3448 b344e b3454 b3458 b345e b4334 b433a '
    'b4354 b4364 b4374 b437a b4380 b4388 b4396 b439a b43ac b43ba b43be b43d2 b43d8 b442e b4434 b4436 b4440 b444a b444e b4458 b445e b4664 '
    'b4680 b4694 b469e b46a2 b46ac b46b4 b46bc b46c0 b46d6 b46dc '
    'b4760 b4764 b476a b4772 b4780 b478e b4792 b4796 b47a4 b47b2 b47b6 b47ba b47c2 b47ce b47d0 b47dc b47de b47e4 b47ea b47f4 b47f8 b47fe b4804 '
    'b489e b48ac b48b4 b48b8 b48ba b48be b48ca b48d2 b48d6 b48dc b48e8 b48ec b491a b4922 b4936 b4942 b494c b4950 b4958 b4962 b496c b4980 b498a '
    'b499e b49a8 b49b0 b49b8 b49be b49c2 b49c8 b49da b49e4 b49ec b49f2 b49fc b4a06 b4a0c b4a10 b4a14 b4a18 b4a1c b4a22 b4ab0 b4aca '
    'c0ace c0ad6 c0aec c0b04 c0b0e c0b12 c0b24 c0b4c c0b52 c0b58 c0b64 c0b6e c0b82 c0b8c c0b92 c0b98 c0ba0 c0ba6 c1d2e '
    'e5580 e558a e5596 e559e e55a0 e55a4 e55ae e55b8 e55c6 e55d0 e55e2 e55ea e55ec e55fa e5600 e5606 '
    'e62a8 e62b0 e62ba e62c2 e62cc e62ce e62e0 e62ea e63ec e63f2 e63f8 '
    'e6516 e6522 e652a e652e e6538 e6540 e654c e6552 e6556 e655c e6566 e6568 e6582 e6584 e658c e6596 e659a e65ae e65b0 e65b8 e65ba e65c0 e65c2 e65da '
    'e693a e694c e991c e9922 e9930 e993c e9942 e9952 e9956 e9b5a e9b72').split()]
CONSUMERS = (0xb3454, 0xb46ac, 0xb478e, 0xb47b2, 0xb48e8, 0xb491a, 0xb4a18)
CLEAR_SET = (0xb43d8, 0xb445e)          # ANDI.B #fe,CCR; RTS: known C Clear
SET_SET = (0x1c232, 0xb4374, 0xb43d2, 0xb4458)    # ORI.B #1,CCR; RTS: known C Set
DATA_SET = (0x1c1f4,)                   # CMP.B D0,D1 borrow (equal -> 1c230 with C Clear)
INVERT_SET = ()
PASS_SET = (0xb433a, 0x1c230)           # RTS that keeps the incoming C (carry preserving, not a consumer)
STARTS_SET = set()
Z_RECOMPUTE = {0xb48ba: 'a1'}           # b48ba: Z := WORD (A1) == 0 (both predecessors TST.W (A1); contract decision 4)
C_RECOMPUTE = {0xb47f4: ('d1', 'd0')}   # b47f4: C := unsigned D1.W < D0.W (only predecessor b47de CMP.W D0,D1; contract decision 4)
STATIC_IMPOSSIBLE = set()               # e6568 -> e6570 cannot follow e655c (decision 6) but a direct entry with a declared D0.W > a reaches it
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xb344e, 0xb3454), (0xb48dc, 0xb48e8), (0xb4a14, 0xb4a18), (0xb4780, 0xb478e), (0xb47a4, 0xb47b2), (0xb48ec, 0xb491a), (0xb46a2, 0xb46ac))
PASS_CHAINS = ((0xb4334, 0xb433a), (0x1c1f4, 0x1c230), (0x1c8e8, 0x1c230))
TABLE_ENTRIES = (0xb4780, 0xb47a4, 0xb48ec, 0xb4aca, 0xb4760, 0xb437a, 0xb4a14)   # WORD 90(A6): the index of the LONG tables b433c / b4ad4
# callbacks and installed values (node callbacks); the callee entries
NODE_ENTRIES = (0xc0ace, 0xc0b52, 0xe5580, 0xe5596, 0xe55e2, 0xb33d8, 0xb342e)
CALLEES = (0xa8ee, 0xa770, 0xa772, 0x9ee6, 0x9ef8, 0x9f12, 0xb4958, 0xb4334, 0xb4ab0, 0xb4aca, 0x1c8a4, 0x1c1f4, 0xe62a8, 0xe991c, 0xe6556, 0xe63ec,
           0xb4354, 0xb437a, 0xb445e, 0xb442e, 0xb489e, 0xb476a, 0xb4760, 0xe6516, 0xe65b0, 0xe693a, 0xe9b5a)
# values a direct entry pops (below the return LONG at A7): ('L'|'W', kind) with kind node / any / small
STACK = {0xb4380: (('L', 'node'),), 0xb469e: (('L', 'any'), ('L', 'item')), 0xb4440: (('W', 'any'),), 0xb4936: (('L', 'node'), ('L', 'a6'), ('W', 'any')), 0xb48d6: (('W', 'any'),),
         0xb494c: (('W', 'any'),), 0xb4950: (('W', 'any'),), 0xe655c: (('L', 'node'),), 0xe658c: (('L', 'small'), ('L', 'small'), ('L', 'node')),
         0xe694c: (('W', 'any'),), 0xe9922: (('L', 'any'),), 0xe9b72: (('W', 'small'),), 0x1c8ac: (('W', 'any'),), 0xa788: (('L', 'any'),),
         0xa7c2: (('L', 'any'), ('L', 'any'), ('W', 'any'), ('W', 'any'), ('W', 'any'))}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x8c)     # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xb, 0xc, 0xd, 0xf, 0x10, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xf, 0x10, 0x14, 0x24, 0x40, 0x6d, 0x6e, 0x7f, 0x80, 0xff, 0x100, 0x200, 0x58f, 0x590, 0x77f, 0x780,
      0x1000, 0x7fff, 0x8000, 0x8001, 0xfff6, 0xfffe, 0xffff)
VL = (0, 1, 3, 0x1f, 0x7fff, 0x10000, 0x1ffff, 0x20000, 0x27fff, 0x28000, 0x7fff0000, 0x7fffffff, 0x80000000, 0xc0000000, 0xfffd8000, 0xffff0000,
      0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {}                        # no computed jump in this unit (the JSR (A1) live targets leave the unit)

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
    require(len(_ROUTE) >= 115, ('routing rules', len(_ROUTE)))


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
BUNDLED = (0xe6534,)                    # BCS.W right after BHI.W (flag-sharing pair inside the block e652e)


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
        if BCC.match(mn) and a in BUNDLED:
            continue
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra') or BCC.match(mn) or a in STARTS_SET or len(out) > 60:
            break
    _BLK[start] = out
    return out


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op.split(',')[-1])
    return int(m.group(1), 16) if m else None


def static_next(start):
    """Static successors of the entry block (None = computed: RTS, JSR (An))."""
    instrs = block_instrs(start)
    a, mn, op, size, _ = instrs[-1]
    if BCC.match(mn) or mn == 'dbra':
        out = {target(op), a + size}
        if len(instrs) > 1 and BCC.match(instrs[-2][1]) and instrs[-1][0] in BUNDLED:
            out.add(target(instrs[-2][2]))
        return out
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op and '(a' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr', 'jmp'):
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
            if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'scs', 'abcd'):
                sz = 1
            for m in HX.finditer(op):
                disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
                out.add((int(m.group(3)), disp, sz))
    return sorted(out)


# ---------------------------------------------------------------------------------------------------------------------
# Native tracer (selection of worlds only: every kept world is re-run by the V1 verifier, native versus C++)
# ---------------------------------------------------------------------------------------------------------------------
def trace(state, outside, cap=CAP_INSN):
    """Run the original from state.pc natively until `outside(pc, prev, size)` is true (checked from the second instruction on).  -> dict(pcs, stop, sr) or None."""
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
    if stop is not None and (stop & 1):
        return None                                             # an odd live JSR (A1) target is no valid stop PC (the odd target error rows are in error_fixtures)
    if stop is None or m.odd is not None or m.invalid is not None or m.intr is not None or m.fetch_unmapped is not None or m.dev_reads:
        return None
    # Unicorn evaluates the M68000 condition codes lazily: reg_read(SR) returns stale flags.  MOVE SR,D0 on a scratch page forces the evaluation.
    c.mem_map(SCRATCH, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE | unicorn.UC_PROT_EXEC)
    c.mem_write(SCRATCH, b'\x40\xc0\x4e\x71')
    box['stop'] = -1
    c.emu_start(SCRATCH, SCRATCH + 2, count=1)
    return dict(pcs=pcs, stop=stop, ports=len(m.ports), sr=c.reg_read(S.UC_REG['d0']) & 0xffff)


def outside_unit(allowed=()):
    """Stop at the first PC outside the unit, or at a PC inside the unit that is not a block start and not the straight-line successor of the previous
    instruction (a computed target inside the unit that the C++ rejects)."""
    al = set(allowed)

    def outside(pc, prev, size):
        if pc in al:
            return False
        if not mine(pc):
            return True
        if pc in STARTS_SET:
            return False
        ins = decode(prev)
        return pc != prev + (ins.size if ins is not None else size)
    return outside


def first_unrouted(extra=()):
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, or at the first unrouted PC that is not the straight-line successor of the
    previous instruction (a PC inside a block of another executor is not a block entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24}
    # The size Unicorn reports to the code hook is not the M68000 instruction length (287e MOVEA.L 8(A6),A0 -> 2882 was taken for a jump), so the length is decoded.
    def outside(pc, prev, size):
        if pc in ex:
            return True
        if 0x8c16 < pc <= 0x8ca6:  # the routed exit leaf 8c16 (palette effect, RTS 8ca4): its branch targets 8c2a.. are interior, never stops
            return False
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

    def record(self):
        return self.rng.choice(self.nodes + list(PLAYERS) * 2)

    def item(self):
        return ITEMS + 12 * self.rng.randrange(0x6e)

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
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        writes = []
        regs['a0'] = self.record() if rng.random() < 0.7 else self.item()
        regs['a1'] = self.pointer()
        regs['a2'] = self.record()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        # the pointers the unit follows: LONG 8c of A0 / the player records (1c1f4 / 1c8ce), the menu record LONG -ee(A5) and -f2(A5)
        for p in PLAYERS + (regs['a0'],):
            if 0x100000 <= p < 0x110000:
                writes.append(((p + 0x8c) & 0xffff, 4, self.pointer()))
        writes.append(((a5 - 0xee) & 0xffff, 4, self.pointer()))
        writes.append(((a5 - 0xf2) & 0xffff, 4, self.pointer() if rng.random() < 0.7 else regs['a2']))
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            if reg == 5 and disp in (-0xee, -0xf2):
                continue
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # WORD 90(A6): the byte offset into the LONG tables b433c / b4ad4 (6 entries); the rank table and the list WORDs
        if entry in TABLE_ENTRIES or rng.random() < 0.3:
            writes.append(((a6 + 0x90) & 0xffff, 2, rng.choice((0, 4, 8, 0xc, 0x10, 0x14))))
        for a in (0x10dd48, 0x10dd50):
            if rng.random() < 0.5:
                writes.append((a & 0xffff, 2, rng.choice((0x8000, 0, 0x100, self.value(2)))))
        for p in PLAYERS:
            for off in (0x42, 0x46):
                if rng.random() < 0.4:
                    writes.append(((p + off) & 0xffff, 2, self.value(2)))
        if rng.random() < 0.5:
            writes.append((0x000e, 2, self.value(2)))
        # a list of 10-byte records at 5d5c(A5) / 5d98(A5): WORD node low, LONG rectangle pointer (a natural node), LONG handler (the sentinel)
        if rng.random() < 0.4:
            lst = a5 + rng.choice((0x5d5c, 0x5d98))
            for k in range(rng.choice((0, 1, 2))):
                node = self.pointer()
                writes.append(((lst + 10 * k) & 0xffff, 2, node & 0xffff))
                writes.append(((lst + 10 * k + 2) & 0xffff, 4, self.pointer()))
                writes.append(((lst + 10 * k + 6) & 0xffff, 4, SENTINEL))
        # stack values popped by the entered block (declared), the return LONG above them
        pops = []
        for size, kind in STACK.get(entry, ()):
            v = {'node': self.pointer(), 'a6': a6, 'item': self.item(), 'small': rng.choice((0, 1, 2, 3, 9, 0xa)),
                 'any': self.value(4 if size == 'L' else 2)}[kind]
            pops.append((4 if size == 'L' else 2, v))
        depth = sum(n for n, v in pops)
        at = sp - depth
        for n, v in pops:
            writes.append((at & 0xffff, n, v))
            at += n
        regs['a7'] = sp - depth
        writes.append((sp & 0xffff, 4, ret))
        if entry in (0xa7ac,) and (regs['d2'] & 0xffff) == 0:
            regs['d2'] |= rng.choice((1, 3, 0x10, 0xff))       # DIVU zero divisor: the native CPU takes the vector 5 exception (error fixtures)
        if entry in (0xe63f2, 0xe63ec):
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1, 2, 8))
            regs['a1'] = self.pointer()
        if entry in (0xe62ce, 0xe62e0):
            regs['a1'] = rng.choice((0x10de1c, 0x10de24, self.pointer() + 4))
        if entry in (0xe9922, 0xe9942, 0xe9956, 0xe9b72, 0xe694c, 0xe55ae, 0xe55d0):
            regs['a0'] = self.pointer()
            if entry == 0xe9942:
                regs['a1'] = self.pointer()
                regs['d7'] = (regs['d7'] & 0xffff0000) | rng.choice((0, 1, 7))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a5off', []):
                writes.append(((a5 + off) & 0xffff, size, val))
            regs.update(hint.get('regs', {}))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('a1off', []):
                writes.append(((regs['a1'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
        state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        # b47f4 / b48ba recompute a flag of their predecessor: the native run starts with C = Z = 0 (contract decision 4)
        if entry in C_RECOMPUTE:
            r = state['regs']
            if (r['d1'] & 0xffff) < (r['d0'] & 0xffff):
                regs['d1'] = (r['d1'] & 0xffff0000) | (r['d0'] & 0xffff)
                state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        if entry in Z_RECOMPUTE:
            a1 = state['regs']['a1']
            ram = state['ram']
            if 0x100000 <= a1 < 0x110000 and ram[a1 & 0xffff] == 0 and ram[(a1 + 1) & 0xffff] == 0:
                writes.append((a1 & 0xffff, 2, rng.choice((1, 0x8000, 0xffff))))
                state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        return state


out_missing = []
unreachable = []
META = {}


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 218 and len(STARTS_SET) == 218, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in (0xb466c, 0xe6570):
        require(unit_of(t) is None and not mine(t), ('TRAP site must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr2_block', ('start is not routed to fr2', hex(s), unit_of(s)))
    rng = random.Random(0xF42A)
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
        for a, mn, op, size, _ in block_instrs(s):
            if BCC.match(mn) or mn == 'dbra':
                cond_points[a] = set(t for t in (target(op), a + size) if (a, t) not in STATIC_IMPOSSIBLE)
    # a bundled pair: the first Bcc's fall-through is the second Bcc, never a successor of its own
    for b in BUNDLED:
        for a in list(cond_points):
            if b in cond_points[a] and a != b:
                cond_points[a].discard(b)
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        n = len(block_instrs(entry))
        needed = static_next(entry)
        if needed is not None:
            if entry in C_RECOMPUTE:
                needed = set([0xb47fe])                         # the native start has C = 0: D1.W >= D0.W; b47f8 is covered from b47de
            if entry in Z_RECOMPUTE:
                needed = set([0xb48be])                         # the native start has Z = 0: WORD (A1) != 0; b494c is covered from b48b8 / b4942
        flds = fields_of(entry)
        kept = {}
        extra = 0
        hints = hint_worlds(entry, world)
        for t in range(MAX_TRIES + len(hints)):
            stats['tries'] += 1
            st = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
            tr = trace(st, outside_unit())
            if tr is None or len(tr['pcs']) < n:
                stats['rejected'] += 1
                continue
            record(tr['pcs'] + [tr['stop']])
            nxt = tr['pcs'][n] if len(tr['pcs']) > n else tr['stop']
            if nxt in CONSUMERS and entry not in DATA_SET:
                continue
            if mine(nxt) and nxt not in STARTS_SET:
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
        cands = sorted([e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS], key=lambda e: (e != blk, e))
        if blk in C_RECOMPUTE or blk in Z_RECOMPUTE:
            cands = [e for e in cands if e != blk]
        for entry in cands[:6]:
            flds = fields_of(entry)
            for k in range(MAX_TRIES):
                hs = hint_worlds(entry, world)
                chint = hs[k % len(hs)] if hs and k % 2 else None
                st = world.make(entry, SENTINEL, flds, chint)
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
    META['static_impossible'] = [(hex(a), hex(t)) for a, t in sorted(STATIC_IMPOSSIBLE)]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('fr2 spec: %d fixtures, visited %d/218, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr2: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr2: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries included).  Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry == 0xe5580:
        h += word(0x80, (0, 9, 0xa, 0xb, 0x8000, 0xffff))
    if entry == 0xe5596:
        h += word(0x7a, (0, 1, 2, 0x8000))
    if entry in (0xe55e2,):
        h += byte(0x62, (0, 1, 0x80, 0xff))
    if entry in (0xe55ec, 0xe55ae):
        h += word(0x7c, (0, 1, 0x8000))
    if entry in (0xc0b04, 0xb4388, 0xb43ac):
        h += byte(0x15, (0, 1, 2, 3, 0xfe, 0xff))
    if entry == 0xc0b58:
        h += long_(0x3a, (0x1ffff, 0x20000, 0x7fffffff, 0x80000000, 0xffffffff, 0))
    if entry == 0xc0b6e:
        h += long_(0x36, (0x27fff, 0x28000, 0xfffd8000, 0xfffd7fff, 0x7fffffff, 0xffffffff))
    if entry in (0xc0b64, 0xc0b82):
        h += long_(0x3a if entry == 0xc0b64 else 0x36, (0x80000000, 0xffffffff, 0x7fffffff, 0x0000000f, 0xfffffff0))
    if entry in (0xc0b98,):
        h += regs('d0', (0, 4, 0xfb, 0x12345604))
    if entry in (0xb4958, 0xb49f2):
        h += byte(0x95, (0, 8, 0x10, 0x18, 0xff))
    if entry in (0xb4962, 0xb496c):
        h += byte(0x12, (0, 0x3f, 0x40, 0x7f, 0xc0, 0xdf, 0xe0, 0xfe, 0xff))
    if entry in (0xb4980, 0xb498a):
        h += byte(0x13, (0, 0x3f, 0x40, 0x7f, 0xc0, 0xdf, 0xe0, 0xfe, 0xff))
    if entry == 0xb499e:
        h += byte(0x96, (0, 4, 0xfb, 0xff))
    if entry in (0xb49a8, 0xb49b0):
        h += byte(0x94, (0, 1, 0x80, 0xff))
    if entry in (0xb49c2, 0xb49c8):
        h += regs('d7', (0, 1, 2, 3, 4, 0x80, 0xffffff00))
    if entry in (0xb49e4, 0xb49ec):
        h += word(0x8c, (0, 1, 2, 0x8000, 0xffff)) + regs('d0', (0, 1, 2, 0x10000))
    if entry == 0xb49fc:
        h += byte(0x61, (0, 8, 0xf7, 0xff))
    if entry == 0xb4664:
        h += regs('d1', (0, 0x6d, 0x6e, 0x8000, 0xffff, 0x1230006d))
    if entry == 0xb4680:
        h += regs('d1', (0, 1, 0x32, 0x6d, 0x12340000))
    if entry == 0xb442e:
        h += [dict(regs=dict(a0=0x10e600), writes=[(0xe600, 4, v)]) for v in (0x80000000, 0xffffffff, 0x7fffffff, 0)]     # LONG (A0) negative: b4434 RTS
    if entry in (0xb46a2, 0xb442e, 0xb4436, 0xb4440):
        h += [dict(regs=dict(a0=ITEMS + 12 * k + (8 if entry != 0xb46a2 else 0))) for k in (0, 1, 0x32, 0x6d)]
    if entry == 0xb46c0:
        h += regs('d1', (0, 7, 8, 0xffff, 0x12340003)) + regs('d0', (0, 1, 0x100))
    if entry == 0xb476a:
        h += regs('d7', (0, 4, 0xfb, 0x12345604))
    if entry in (0xb4772, 0xb4796):
        h += [dict(writes=[((0xdd48 if entry == 0xb4772 else 0xdd50), 2, v)]) for v in (0x8000, 0, 0x7fff, 0x8001)]
    if entry == 0xb47ba:
        h += regs('d7', (0, 1, 2, 3, 0x103, 0xffffff03))
    if entry in (0xb47c2, 0xb47d0):
        h += [dict(a6off=[(0x42, 2, b)], a5off=[((0x5d48 if entry == 0xb47c2 else 0x5d50), 2, a)]) for a, b in
              ((0, 0), (5, 3), (3, 5), (0x8000, 0), (0, 0x8000), (0x7fff, 0xffff))]
    if entry == 0xb47de:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (5, 5), (3, 5), (5, 3), (0x12340005, 0x56780005), (0x8000, 0x7fff))]
    if entry == 0xb47f4:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (3, 5), (0x7fff, 0x8000), (0x12340001, 0x00000001))]     # D1.W >= D0.W only
    if entry in (0xb489e, 0xb48be):
        h += [dict(writes=[(0x000e, 2, v)]) for v in (0, 1, 2, 0xffff)]
    if entry == 0xb48d6:
        h += [dict(regs=dict(a1=a, a2=b)) for a, b in ((0x10dd98, 0x10dd98), (0x10dd98, 0x10ddd4), (0x10dd5c, 0x10dd98))]
    if entry == 0xb4936:
        h += regs('d0', (0, 1, 0xffff))
    if entry in (0xb4354, 0xb4364):
        h += [dict(a6off=[(0x4a, 2, v)]) for v in (0, 1, 0x8000, 0xffff)]
    if entry in (0xb439a, 0xb43be):
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (1, 0), (0, 1), (0x8000, 0x7fff), (0xffff, 0))]
    if entry == 0x1c8ac:
        h += regs('d0', (0, 0x20, 0xffdf, 0x12340020))
    if entry == 0x1c8ba:
        h += regs('d0', (0, 1, 2, 3, 0xfffe))
    if entry == 0x1c8ce:
        for p in PLAYERS:
            h += [dict(regs=dict(a0=p))]
    if entry == 0x1c1f4:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 0x12340001)]
    if entry in (0xe62a8, 0xe62ba):
        h += regs('d0', (0, 1, 2, 3, 0xfffffffc))
    if entry in (0xe62ce,):
        h += [dict(regs=dict(a0=ITEMS + 12 * k + 8)) for k in (0, 0x32)]
        h += [dict(regs=dict(a0=0x10e600, a1=0x10e614), writes=[(0xe600, 4, 0x99999999), (0x10e610 & 0xffff, 4, 0x99999999)])]      # carry out of the last digit pair: e62e0
    if entry == 0xe62e0:
        h += [dict(regs=dict(a1=0x10e614))]
    if entry == 0xe63ec:
        h += regs('d0', (0, 1, 2, 0x10000))
    if entry in (0xe6522, 0xe652e):
        h += [dict(regs=dict(d3=a, d4=b)) for a, b in ((0, 0), (1, 0), (0, 1), (0x80000000, 0x7fffffff), (0xffffffff, 0))]
    if entry in (0xe6538, 0xe6540, 0xe65b0, 0xe65ba):
        h += regs('d1', (0, 9, 0xa, 0xb, 0x7fff, 0x8000, 0xffff, 0x1234000a))
    if entry in (0xe655c, 0xe6568):
        h += regs('d0', (0, 9, 0xa, 0xb, 0x7fff, 0x8000, 0xffff, 0x1234000a))
    if entry == 0xe658c:
        h += [dict(regs=dict(d0=a)) for a in (0, 1)]
    if entry in (0xe9930,):
        h += regs('d3', (0, 0xf0000000, 0x12345678, 0x0fffffff))
    if entry == 0xe993c:
        h += regs('d6', (0, 1, 2, 0x7f, 0x80, 0x81, 0xff))
    if entry == 0xe9952:
        h += regs('d4', (0, 1, 0x10000, 0xffff))
    if entry == 0xa77a:
        h += regs('d7', (0, 1, 0x100, 0xff))
    if entry == 0xa7ac:
        h += [dict(regs=dict(d1=a, d2=b)) for a, b in ((0xff, 1), (0x80, 0x100), (0xffff, 1), (0xffff, 0xff), (0x7f, 0x101), (0, 5))]
    if entry == 0x9ee6 and world is not None:
        same = world.pointer()
        h += [dict(a5off=[(-0xee, 4, same), (-0xf2, 4, same)])]
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    for entry, cons in CHAINS + PASS_CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15,)] + [(6, off, 2) for off in (0x42, 0x46, 0x4a, 0x4e)]
        succ = static_next(cons) if cons not in PASS_SET else {SENTINEL}
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry == 0xb344e and t % 4 == 1:
                hint = dict(a6off=[(0xc, 4, 0)])                                       # 288c: LONG c(A6) = 0 -> ORI Set
            elif entry == 0xb344e and t % 4 == 3:
                hint = dict(a6off=[(0xc, 4, 0x10e600)], writes=[(0xe600, 4, 0x270e)])  # 288c: LONG (parent) = 270e -> Clear (b3454 -> b3458)
            elif entry == 0xb48dc and t % 2:
                hint = dict(free=True)                                                  # 289e: LONG (A0) = 270e -> Clear (A0 = WORD (A1) of the A6 bank)
            elif entry in (0xb4780, 0xb47a4, 0xb48ec) and t % 2:
                hint = dict(a6off=[(0x90, 2, (0, 4)[(t // 2) % 2]), (0x4a, 2, (0, 0x100, 0xff00)[(t // 2) % 3])])
                if t % 6 < 4:
                    # a declared judged rectangle (WORD w0, LONG hi:lo, WORD w2) so that the table test b4354 / b437a reaches both outcomes
                    # (Set = overlap: 0 <= w0 + lo - WORD 4a < lo and 0 <= hi + w2 - WORD 4a < w2 modulo 2^16 as the original compares)
                    rec = {0xb4780: 0x10dd48, 0xb47a4: 0x10dd50}.get(entry, 0x10e610)
                    r4a = hint['a6off'][1][2]
                    lo = world.rng.choice((0x10, 0x40, 0x100, 0x1000))
                    hi = world.rng.choice((0x10, 0x40, 0x100, 0x1000))
                    ws = [(r4a - lo // 2) & 0xffff, hi, lo, (r4a - hi // 2) & 0xffff] if t % 6 < 2 else \
                         [world.rng.choice((0, 1, 0x10, 0x7fff, 0xffff)) for k in range(4)]
                    hint['writes'] = [((rec + 2 * k) & 0xffff, 2, ws[k]) for k in range(4)]
                    if entry != 0xb48ec:
                        hint['regs'] = dict(a0=rec)                      # the judged rectangle is read through A0 (b476a loaded A0 := 10dd48 / b4796 10dd50)
                    if entry == 0xb48ec:
                        hint['regs'] = dict(a1=0x10e5f0)
                        hint['writes'] += [(0xe5f2, 4, rec)]
            elif entry == 0xb46a2:
                hint = dict(regs=dict(a0=ITEMS + 12 * world.rng.choice((0, 0x32, 0x6d))))   # the handler b445e (item records 0 / 32 / 6d)
            elif entry in (0xb4334,) and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                       # 49fc6: LONG 26(A6) = 0 -> ORI Set
            st = world.make(entry, SENTINEL, flds, hint)
            if entry == 0xb48dc and hint:
                a1 = st['regs']['a1']
                w = (st['ram'][a1 & 0xffff] << 8) | st['ram'][(a1 + 1) & 0xffff] if 0x100000 <= a1 < 0x110000 else None
                if w is not None and not w & 1:
                    st = U.with_host_writes(st, [(w, 4, 0x270e)])
            tr = trace(st, first_unrouted(extra=succ), cap=400000)
            if tr is None or cons not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = tr['stop']
            if key not in kept:
                kept[key] = (st, tr)
            elif cons in PASS_SET and len(kept) < 3:
                kept[(key, t)] = (st, tr)
            if set(k for k in kept if isinstance(k, int)) >= succ and (cons not in PASS_SET or len(kept) >= 3):
                break
        require(kept, ('no chain world', hex(entry)))
        missing = succ - set(k for k in kept if isinstance(k, int))
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (stop, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'])))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x8c, 2, (0, 1, 2, 0x24)[t % 4]), (0x80, 2, (0, 9, 0xa, 0x14)[(t // 4) % 4])])
            st = world.make(entry, base.stop, flds, hint)
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
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('node-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='node', entry=entry, stop=tr['stop'],
                                                                                      unit_blocks=len(set(tr['pcs']) & STARTS_SET))))


def callee_fixtures(world, add, record):
    """The helpers as subroutines (return LONG = sentinel)."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry, world)
        for t in range(60 + len(hints)):
            hint = hints[t] if t < len(hints) else None
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], tuple(p for p in tr['pcs'] if p in STARTS_SET)[:40])
            if key in kept:
                continue
            kept[key] = (st, tr)
            if len(kept) >= 4 and t >= len(hints):
                break
        require(kept, ('no callee world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('callee-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='callee', entry=entry, stop=tr['stop'])))


def error_fixtures(bases, add):
    """Checked errors with the failing PC (Fixture fail_pc and meta, review 0264 L-1).  A failing PC that differs from the entry (and is even) gets a paired
    'match' row with stop = the failing PC (both sides stop exactly there).  The error row's stop is the PC right after the failing block (FR1c lesson)."""
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)

    def err(name, state, text, fail_pc, stop=SENTINEL):
        add(U.Fixture('error-' + name, state, [], stop, ('error', text), fail_pc=fail_pc, meta=dict(family='error', fail_pc=fail_pc)))
        if fail_pc != state['pc'] and not fail_pc & 1:
            add(U.Fixture('failpc-' + name, state, [], fail_pc, meta=dict(family='failpc', fail_pc=fail_pc)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr2 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0xc0acf), 'unaligned animation machine PC', 0xc0acf)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr2 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W #3c,7a(A6) of e558a at an odd A6 (write), CMPI.W #a,80(A6) of e5580 (read); odd record: TST.L (A0) of b442e; odd stack
    err('e558a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe558a), odd_write, 0xe558a, stop=0xe5596)
    err('e5580-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe5580), odd_word, 0xe5580)
    err('b442e-odd-record', U.with_host_writes(st, regs=dict(a0=0xb3895), pc=0xb442e), odd_word, 0xb442e, stop=0xb4436)
    err('e6556-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe6556), odd_word, 0xe6556, stop=0xe6516)
    # DIVU zero divisor (a7ac): D2.W = 0
    err('a7ac-divu-zero', U.with_host_writes(st, regs=dict(d2=0x12340000), pc=0xa7ac), 'objects fr2 DIVU zero divisor', 0xa7ac, stop=0xa7c2)
    # failures after executed blocks:
    #   b476a (D7 bit 2 clear) -> b4772 (10dd48 = 8000) -> b4796 (10dd50 = 8000) -> b47ba (D7.B != 3) -> b4804 RTS at an odd A7
    err('b476a-then-b4804', U.with_host_writes(st, [(0xdd48, 2, 0x8000), (0xdd50, 2, 0x8000)], regs=dict(d7=0, a7=a7 + 1), pc=0xb476a), odd_word, 0xb4804)
    #   e63ec (D0.W = 0) -> e63f8 RTS at an odd A7
    err('e63ec-then-e63f8', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0xe63ec), odd_word, 0xe63f8)
    #   c0b98 (D0 bit 2 clear) -> c0ba0 JSR b4334 at an odd A7
    err('c0b98-then-c0ba0', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0xc0b98), odd_word, 0xc0ba0, stop=0xb4334)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xc0b6e, 0xe6540, 0xb496c, 0xe62ce)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
