"""V1 fixture spec of the animation-machine unit FR1c (engine/src/animation_machine_objects_fr1c.cpp, 215 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr1c-contract.md): the IO-frontier object bc08c (U17 28ae child; bc08c..bc404 bc47c..bc7d6,
34 installed values) and the FR1a 2986 child d13b4 (d13b4..d159e d2206..d224c; installs d14de d1576 d1586; d2206 is also the c6012 table entry) with
the shared helpers 4941e (4941e..4945e: rectangle test of the record A0 against A6, C returned by EORI.B #1,CCR; RTS 49458) and 494c0 (494c0..4950e:
the player choice through 49370 / 4941e that ends in N08 49462).

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a / FR1b / B3a..B4b) with declared host edits.  A
second natural source for node fixtures are the IO observation states (artifacts/animation_machine_io_native, states/*.pack.gz page-delta packs of the
frame start): the confirmed frontier frames of the FR1b IO rerun (ms5-scratch/fr1b/ioA/frontier.json: P1 / P1b frame 167 node bc08c, frame 328 node
d13b4, both returning to 2ac2) advanced to the frontier PC are the real entry states of this unit.  This spec does not decode those packs (the IO
comparison rerun checks the natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the fifteen consumers is entered directly (the seed world with declared edits: D0-D7, A0 / A1 / A2 / A3 / A4 := a
            natural node or a player record 100cb8 / 100da8, A1 := a natural node or the rectangle d13ac, LONG c(A6) := a natural node, the node and
            record fields the reachable blocks read, BYTE 568e(A5) / 5b86(A5), WORD 10000e, the stack LONG that 494ca / 49508 pop, PC := the block
            start).  Stop: the first PC outside the unit (a callee, the sentinel return LONG, JMP 2a00, BRA 49462 / d23a0).
            bc3aa recomputes the Z of its only predecessor bc398 from WORD 76(A6) (contract decision 4): the native run starts with SR 2000 (Z = 0), so
            a direct entry at bc3aa always declares WORD 76 != 0; its other outcome bc3ae is covered from bc398.
            d151c BEQ.W d1528 cannot be taken (A0 = d1c9c, a constant; contract decision 6): that outcome is not a required successor.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 28ae -> bc79e (bc78e), 49370 -> 494c6 (494c0), 4941e (49432 / 49452 -> 49458) -> 494e6
            (494e0) 494fc (494f6), 494c0 (49370, 4941e, N08 49462) -> d143c (d1432), 4b6f4 (4b700) -> d153a (d1534), 1ab80 -> d156a (d155a), 49fc6 ->
            bc1f6 (bc1f0) bc338 (bc332) bc394 (bc38e) bc6a2 (bc69c) bc6de (bc6d8) bc74e (bc748) bc78a (bc784).  Stop: the consumer's successor (or the
            first unrouted PC).  The consumer 49458 (EORI.B #1,CCR; RTS) runs inside the 494e0 / 494f6 / 4941e chains.
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC; d2206 (table entry) too.
  callee    the helpers 4941e 494c0 entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the fifteen consumers, odd node / record / rectangle / stack pointers, the
            TRAP boundary 4937c of 49370 (A5 != 108000), failures after executed blocks: checked error, state preserved, every row with its failing PC (a
            paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR1b specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (B3a..FR1b)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
PLAYERS = (0x100cb8, 0x100da8)          # the player records 494ca / 49508 / 49462 use
RECT = 0xd13ac                          # the original rectangle of d1432 (fixed ROM)
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x4941e, 0x4945e), (0x494c0, 0x4950e), (0xbc08c, 0xbc404), (0xbc47c, 0xbc7d6), (0xd13b4, 0xd159e), (0xd2206, 0xd224c)]
STARTS = [int(x, 16) for x in (
    '4941e 49430 49432 4943e 49450 49452 49458 '
    '494c0 494c6 494ca 494e0 494e6 494ea 494ee 494f6 494fc 49500 49504 49508 '
    'bc08c bc09a bc0b2 bc0ba bc0c0 bc0c2 bc0da bc102 bc132 bc13c bc142 bc146 bc14c bc154 bc15c bc16c bc17a bc182 bc192 bc1a0 bc1aa bc1b0 bc1b6 bc1b8 '
    'bc1e0 bc1ea bc1f0 bc1f6 bc1fa bc200 bc202 bc22a bc246 bc26a bc272 bc278 bc27e bc288 bc28e bc290 bc2b8 bc2be bc2e2 bc2ec bc2f6 bc2fc bc2fe bc326 '
    'bc32c bc332 bc338 bc33c bc342 bc344 bc36c bc37c bc388 bc38e bc394 bc398 bc3a0 bc3aa bc3ae bc3d6 bc3da bc402 '
    'bc47c bc4a4 bc4b0 bc4b6 bc4bc bc4c4 bc4ca bc4cc bc4f4 bc504 bc50a bc510 bc518 bc51e bc520 bc548 bc566 bc56c bc576 bc57c bc582 bc584 bc5ac bc5ca '
    'bc5d0 bc5da bc5e0 bc5e6 bc5e8 bc618 bc624 bc62a bc630 bc638 bc63e bc640 bc64a bc658 bc666 bc674 bc690 bc696 bc69c bc6a2 bc6a6 bc6ac bc6ae bc6cc '
    'bc6d2 bc6d8 bc6de bc6e2 bc6e8 bc6ea bc6fa bc700 bc706 bc70e bc714 bc716 bc726 bc73c bc742 bc748 bc74e bc752 bc758 bc75a bc778 bc77e bc784 bc78a '
    'bc78e bc79e bc7a2 bc7b0 bc7b4 bc7c0 bc7c2 bc7c8 bc7ce bc7d4 '
    'd13b4 d13c2 d13d0 d13de d1418 d1420 d1428 d1432 d143c d1440 d144c d145e d1466 d1472 d147a d1482 d1486 d1496 d1498 d14a6 d14a8 d14b8 d14d2 d14d4 '
    'd14de d14fe d1504 d150e d1514 d1520 d1528 d152e d1534 d153a d153e d1544 d1556 d155a d156a d156e d1574 d1576 d1586 d1592 d1598 '
    'd2206 d222e d2240').split()]
CONSUMERS = (0xbc1f6, 0xbc338, 0xbc394, 0xbc6a2, 0xbc6de, 0xbc74e, 0xbc78a, 0xbc79e, 0x494c6, 0x494e6, 0x494fc, 0x49458, 0xd143c, 0xd153a, 0xd156a)
CLEAR_SET = ()                          # no block leaves a constant known C Clear
SET_SET = (0xbc7b0,)                    # ORI.B #1,CCR: known C Set without a reader
DATA_SET = (0x49432, 0x49452)           # CMP.W borrow: a known C that depends on the data (49432: taken -> Clear, fall-through -> Set)
INVERT_SET = (0x49458,)                 # EORI.B #1,CCR; RTS: the consumer that returns the inverted known C
PASS_SET = ()                           # 49458 is a consumer (its RTS returns its own inverted C)
STARTS_SET = set()
Z_RECOMPUTE = {0xbc3aa: 0x76}           # bc3aa: Z := WORD 76(A6) == 0 (only predecessor bc398 SUBQ.W #1,76(A6); contract decision 4)
STATIC_IMPOSSIBLE = {(0xd151c, 0xd1528)}   # d151c BEQ.W d1528 after MOVE.L A0,D0 with A0 = d1c9c (contract decision 6)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xbc78e, 0xbc79e), (0x494c0, 0x494c6), (0x494e0, 0x494e6), (0x494f6, 0x494fc), (0xd1432, 0xd143c), (0xd1534, 0xd153a), (0xd155a, 0xd156a),
          (0xbc1f0, 0xbc1f6), (0xbc332, 0xbc338), (0xbc38e, 0xbc394), (0xbc69c, 0xbc6a2), (0xbc6d8, 0xbc6de), (0xbc748, 0xbc74e), (0xbc784, 0xbc78a))
CHAIN_49FC6 = (0xbc1f0, 0xbc332, 0xbc38e, 0xbc69c, 0xbc6d8, 0xbc748, 0xbc784)
CHAIN_28AE = (0xbc78e,)
CHAIN_RECT = (0x494e0, 0x494f6)         # 4941e through A2 / A3 (the player records) and the rectangle A1
CHAIN_494C0 = (0x494c0, 0xd1432)        # 49370 (BYTE 568e(A5)), 4941e, N08 49462
# callbacks and installed values (node callbacks), the c6012 table entry d2206; the callee entries
NODE_ENTRIES = (0xbc08c, 0xd13b4, 0xbc0b2, 0xbc0c2, 0xbc132, 0xbc1b8, 0xbc1ea, 0xbc202, 0xbc246, 0xbc290, 0xbc2be, 0xbc2fe, 0xbc32c, 0xbc344, 0xbc388,
                0xbc47c, 0xbc4b0, 0xbc4cc, 0xbc504, 0xbc520, 0xbc566, 0xbc584, 0xbc5ca, 0xbc5e8, 0xbc624, 0xbc640, 0xbc696, 0xbc6ae, 0xbc6d2, 0xbc6ea,
                0xbc6fa, 0xbc716, 0xbc742, 0xbc75a, 0xbc77e, 0xbc7c2, 0xbc7c8, 0xd14de, 0xd1576, 0xd1586, 0xd2206)
CALLEES = (0x4941e, 0x494c0)
STACK_LONG = (0x494ca, 0x49508)                 # a declared LONG at A7 (the pushed rectangle pointer), the return LONG above it
RECT_BLOCKS = (0x4941e, 0x49430, 0x49432, 0x4943e, 0x49450, 0x49452, 0x494e0, 0x494f6)   # A1 = the rectangle
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22)           # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xb, 0xc, 0xd, 0xf, 0x10, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0xf, 0x10, 0x14, 0x1e, 0x20, 0x40, 0x60, 0x61, 0x78, 0x79, 0x7f, 0x80, 0x9c, 0x9d, 0xff, 0x100, 0x140, 0x1a0,
      0x1a1, 0x200, 0x1000, 0x7fff, 0x8000, 0x8001, 0xfec0, 0xff00, 0xffbf, 0xffc0, 0xfff0, 0xffff)
VL = (0, 1, 3, 0x1f, 0x20, 0x7fff, 0x10000, 0x30000, 0x7fff0000, 0x7fffffff, 0x80000000, 0xc0000000, 0xfff00000, 0xfff40000, 0xffff0000, 0xffffffe0,
      0xffffffff)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {}                        # no computed jump in this unit

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
    require(len(_ROUTE) >= 114, ('routing rules', len(_ROUTE)))


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
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr') or BCC.match(mn) or a in STARTS_SET or len(out) > 60:
            break
    _BLK[start] = out
    return out


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op)
    return int(m.group(1), 16) if m else None


def static_next(start):
    """Static successors of the entry block (None = computed: RTS; this unit has no computed jump)."""
    a, mn, op, size, _ = block_instrs(start)[-1]
    if BCC.match(mn):
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op:
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
        work += list(TABLE_JUMPS.get(s, ()))
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
        writes = []
        regs['a0'] = self.record()
        regs['a1'] = self.pointer() if rng.random() < 0.6 else RECT
        regs['a2'] = self.record()
        regs['a3'] = self.record()
        regs['a4'] = self.pointer()
        if entry in (0xd155a,) and rng.random() < 0.8:
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(3)
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: regs['a5']}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page (and never the fixed-ROM rectangle d13ac)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # the player records (42 / 46, read by 4941e / 4943e / d144c / d1486 / N08 49462), BYTE 568e(A5) (49370), 5b86(A5) (4b6f4), WORD 10000e
        for p in PLAYERS:
            for off in (0x42, 0x46):
                if rng.random() < 0.5:
                    writes.append(((p + off) & 0xffff, 2, self.value(2)))
        if rng.random() < 0.6:
            writes.append(((regs['a5'] + 0x568e) & 0xffff, 1, rng.choice((0, 1, 2, 3, 0xff))))
        if rng.random() < 0.5:
            writes.append(((regs['a5'] + 0x5b86) & 0xffff, 1, rng.choice((0, 1, 0x80))))
        if rng.random() < 0.5:
            writes.append((0x000e, 2, self.value(2)))
        # RAM rectangles (A1 a natural node): the four WORDs (A1) 2(A1) 4(A1) 6(A1)
        if entry in RECT_BLOCKS and regs['a1'] != RECT:
            for off in (0, 2, 4, 6):
                if rng.random() < 0.7:
                    writes.append(((regs['a1'] + off) & 0xffff, 2, self.value(2)))
        # stack LONG popped by the entered block (declared): 494ca / 49508 the pushed rectangle pointer
        pops = []
        if entry in STACK_LONG:
            pops = [(4, rng.choice((RECT, self.pointer())))]
        depth = sum(n for n, v in pops)
        at = sp - depth
        for n, v in pops:
            writes.append((at & 0xffff, n, v))
            at += n
        regs['a7'] = sp - depth
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a5off', []):
                writes.append(((regs['a5'] + off) & 0xffff, size, val))
            regs.update(hint.get('regs', {}))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            if hint.get('a1off') and regs['a1'] == RECT:
                regs['a1'] = self.pointer()                     # a declared rectangle lives in RAM (d13ac is fixed ROM)
            for off, size, val in hint.get('a1off', []):
                writes.append(((regs['a1'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
        # bc3aa (Z recomputed from WORD 76): the native run starts with Z = 0, so a direct entry declares WORD 76 != 0 (contract decision 4)
        if entry in Z_RECOMPUTE:
            off = Z_RECOMPUTE[entry]
            ram = U.with_host_writes(st, writes, regs=regs, pc=entry)['ram']
            if ram[(a6 + off) & 0xffff] == 0 and ram[(a6 + off + 1) & 0xffff] == 0:
                writes.append(((a6 + off) & 0xffff, 2, rng.choice((1, 2, 0x8000, 0xffff))))
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


out_missing = []
unreachable = []
META = {}


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 215 and len(STARTS_SET) == 215, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    require(unit_of(0x4937c) is None and not mine(0x4937c), 'TRAP 4937c (of 49370) must stay unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr1c_block', ('start is not routed to fr1c', hex(s), unit_of(s)))
    rng = random.Random(0xF41C)
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
            cond_points[a] = set(t for t in (target(op), a + size) if (a, t) not in STATIC_IMPOSSIBLE)
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        n = len(block_instrs(entry))
        needed = static_next(entry)
        if needed is not None:
            last = block_instrs(entry)[-1]
            needed = set(t for t in needed if (last[0], t) not in STATIC_IMPOSSIBLE)
            if entry in Z_RECOMPUTE:
                needed = set(t for t in needed if t == target(last[2]))   # the BNE target only (WORD 76 != 0); bc3ae is covered from bc398
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
            if nxt in CONSUMERS and entry not in DATA_SET:          # 49432 / 49452 reach the consumer 49458 with their own known C
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
        # the block itself first, then the entries that reach it (bc3aa -> bc3ae only through bc398: a direct entry declares WORD 76 != 0)
        cands = sorted([e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS], key=lambda e: (e != blk, e))
        if blk in Z_RECOMPUTE:
            cands = [e for e in cands if e != blk]
        for entry in cands[:6]:
            flds = fields_of(entry)
            for k in range(MAX_TRIES):
                hs = hint_worlds(entry)
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
    sys.stderr.write('fr1c spec: %d fixtures, visited %d/215, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out



def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr1c: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr1c: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts




def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries included).  Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry in (0xbc0b2, 0xbc398, 0xbc4bc, 0xbc510, 0xbc630, 0xbc706, 0xbc17a, 0xbc14c, 0xd1418):
        h += word(0x76, (0, 1, 2, 4, 5, 0x8000, 0xffff))
    if entry == 0xbc3aa:
        h += word(0x76, (1, 0x7fff, 0x8000, 0xffff))                    # never 0 (Z of the native start is 0, decision 4)
    if entry == 0xbc154:
        h += regs('d0', (4, 5, 3, 0x10004, 0xffff0004))
    if entry == 0xd1420:
        h += regs('d0', (1, 2, 0x10001, 0xffff0001, 0))
    if entry == 0xbc1a0:
        h += word(0x42, (0, 0x78, 0x79, 0x7fff, 0x8000, 0xffff))
    if entry == 0xbc56c:
        h += word(0x42, (0x7f, 0x80, 0x7fff, 0x8000))
    if entry == 0xbc5d0:
        h += word(0x42, (0x9c, 0x9d, 0x7fff, 0x8000))
    if entry in (0xbc132, 0xbc27e, 0xbc2ec, 0xd14b8, 0xd1504, 0x4941e, 0x4943e, 0xd13de, 0xd1428, 0xbc0c2):
        h += byte(0x15, (0, 1, 2, 3, 0x20, 0x7f, 0x80, 0xff))
    if entry == 0xbc26a:
        h += long_(0x3a, (0, 0x7fffffff, 0x80000000, 0xffffffff))
    if entry in (0xbc246, 0xbc2be):
        h += [dict(a6off=[(0x64, 4, a), (0x36, 4, b), (0x3a, 4, c)]) for a, b, c in ((0, 0, 0), (0x80000000, 0x7fffffff, 0x7fffffff), (0x7fffffff, 0x80000000, 0x80000000),
                                                                                    (0x1f, 0, 0xfff00000), (0xffffffe0, 0, 0xffefffe1), (0x30000, 0xfffd8000, 0x8a000))]
    if entry == 0xd14de:
        h += [dict(a6off=[(0x3a, 4, a), (0x36, 4, b)]) for a, b in ((0, 0), (0x80000000, 0x80000000), (0x7fffffff, 0x7fffffff), (0xfff40000, 0xffffffe0), (0xfff4001f, 0x1f))]
    if entry == 0xd144c:
        h += [dict(a6off=[(0x46, 2, b)], a0off=[(0x46, 2, a)]) for a, b in ((0x1a0, 0x1a0), (0x1a1, 0x1a1), (0x1000, 0x8000), (0, 0x7fff), (0x7fff, 0x1a0))]
    if entry == 0xd1466:
        h += regs('d0', (0x60, 0x61, 0x7fff, 0x8000, 0x12340060))
    if entry == 0xd147a:
        h += regs('d0', (0xffc0, 0xffbf, 0x8000, 0x7fff, 0x1234ffc0))
    if entry == 0xd1486:
        h += [dict(regs=dict(d0=a), a6off=[(0x42, 2, c)], a0off=[(0x42, 2, b)]) for a, b, c in ((0, 0, 0), (0x8000, 0x8000, 0), (1, 0, 1), (0xffff, 0x7fff, 0x8000), (0x12348001, 5, 3))]
    if entry == 0xd1498:
        h += [dict(regs=dict(d0=a, d7=b, d1=c)) for a, b, c in ((0, 0, 0), (0x10, 0x10000, 0x40), (0xffff, 0x1fffe, 0x70), (0x8000, 0x8000, 0x50), (0x70, 0, 0x70),
                                                               (0x5f, 0x12340001, 0x40), (0x60, 0xffff0000, 0x40))]
    if entry == 0xd14a8:
        h += regs('d0', (0, 0x1f, 0x20, 0xffe0, 0xffdf, 0x12348000))
    if entry == 0xd14b8:
        h += [dict(regs=dict(d0=a, d1=b, d7=0x12345678), a6off=[(0x15, 1, c)]) for a, b, c in ((0x8000, 0xffff, 0), (0x7fff, 0x8000, 1), (0xffff, 0x50, 0), (0x40, 0, 1))]
    if entry == 0xd14d2:
        h += regs('d0', (0, 0x80000000, 1, 0xffffffff))
    if entry == 0xd1528:
        h += regs('d0', (0, 0x10000, 1, 0xffff0000))
    if entry == 0xd1544:
        h += [dict(writes=[(0x000e, 2, v)]) for v in (0, 1, 2, 3, 0xfffc, 0xffff)]
    if entry == 0xd155a:
        h += regs('d0', (0, 1, 2, 0x12340002, 0x7fff, 0x8000, 0xffff))
    if entry in (0x494ca, 0x494ee):
        h += regs('d0', (0, 1, 2, 3, 0xfffffffc, 0x12345601))
    if entry in (0x494ea, 0x49500):
        h += regs('d0', (0, 0xff, 0x12345601, 0xfffffffe))
    if entry in (0x49432, 0x49452):
        h += [dict(regs=dict(d7=d), a1off=[(lo, 2, a), (sz, 2, b)]) for lo, sz in (((2, 6),) if entry == 0x49432 else ((0, 4),))
              for d, a, b in ((0x5, 0, 5), (0x5, 0, 6), (0x5, 0, 4), (0x8000, 0x8000, 1), (0x12340000, 1, 0xffff), (0xff00, 0xff00, 0))]
    if entry in (0x4941e, 0x4943e):
        h += [dict(a6off=[(off, 2, b), (0x15, 1, f)], a0off=[(off, 2, a)]) for off in ((0x46,) if entry == 0x4941e else (0x42,))
              for a, b, f in ((5, 3, 0), (3, 5, 3), (0x8000, 0, 0), (0, 0x8000, 0xff), (0x7fff, 0xffff, 2))]
    if entry in (0x494c0, 0xd1432):
        h += [dict(a5off=[(0x568e, 1, v)]) for v in (0, 1, 2, 3)]
    if entry == 0xd1534:
        h += [dict(a5off=[(0x5b86, 1, v)]) for v in (0, 1, 0x80)]
    if entry == 0xbc6ae:
        h += [dict(a6off=[(0xc, 4, v)]) for v in PLAYERS]
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x62)] + [(6, off, 2) for off in (0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in CHAIN_49FC6 and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                       # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry in CHAIN_28AE and t % 2:
                hint = dict(writes=[(0x4ca0, 2, rng_count(t))])                        # 28ae: WORD 104ca0 <= D0 (a) -> allocation fails, Set
            elif entry in CHAIN_494C0 and t % 2:
                hint = dict(a5off=[(0x568e, 1, (0, 1, 2, 3)[(t // 2) % 4])])            # 49370: BYTE 568e(A5) = 0 -> Set (49508), else Clear
            elif entry in CHAIN_RECT and t % 2:
                # 4941e: A1 = a RAM rectangle with the widest sizes (C Set inside) or zero sizes (C Clear); A0 := the record in A2 / A3
                big = (t // 2) % 2 == 0
                hint = dict(regs=dict(a1=world.pointer()), a1off=[(0, 2, 0x8000 if big else 0), (2, 2, 0x8000 if big else 0), (4, 2, 0xffff if big else 0),
                                                                  (6, 2, 0xffff if big else 0)])
            elif entry == 0xd1534 and t % 2:
                hint = dict(a5off=[(0x5b86, 1, (t // 2) % 2)])                          # 4b6f4: BYTE 5b86(A5) != 0 -> Set
            elif entry == 0xd155a and t % 2:
                hint = dict(a6off=[(0x46, 2, 0x7fff), (0x42, 2, 0x7fff)])               # 1ab80: far outside the screen -> Set
            st = world.make(entry, SENTINEL, flds, hint)
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


def rng_count(t):
    return (0, 1, 0xa, 0x9)[(t // 2) % 4]


def node_fixtures(world, add, record):
    """Callbacks, installed values and the table entry d2206 run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher
    return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            hint = dict(a6off=[(0x1d, 1, t % 4)])                                       # 8ebe: CMPI.B #4,1d(A6) BCS -> 8ecc; >= 4 reaches TRAP #15 (not traceable)
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
        flds = fields_of(entry) + [(1, off, 2) for off in (0, 2, 4, 6)]
        kept = {}
        hints = hint_worlds(entry)
        for t in range(80 + len(hints)):
            hint = hints[t] if t < len(hints) else None
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], tuple(p for p in tr['pcs'] if p in STARTS_SET))
            if key in kept:
                continue
            kept[key] = (st, tr)
            if len(kept) >= 6 and t >= len(hints):
                break
        require(kept, ('no callee world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('callee-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='callee', entry=entry, stop=tr['stop'])))


def error_fixtures(bases, add):
    """Checked errors with the failing PC (Fixture fail_pc and meta, review 0264 L-1).  A failing PC that differs from the entry (and is even) gets a paired
    'match' row with stop = the failing PC (both sides stop exactly there)."""
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)

    def err(name, state, text, fail_pc):
        add(U.Fixture('error-' + name, state, [], SENTINEL, ('error', text), fail_pc=fail_pc, meta=dict(family='error', fail_pc=fail_pc)))
        if fail_pc != state['pc'] and not fail_pc & 1:
            add(U.Fixture('failpc-' + name, state, [], fail_pc, meta=dict(family='failpc', fail_pc=fail_pc)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr1c PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0xbc08d), 'unaligned animation machine PC', 0xbc08d)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr1c caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    rect = st['regs']['a6'] + 0x200
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W #8834,68(A6) at an odd A6 (the entry block fails)
    err('bc09a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xbc09a), odd_write, 0xbc09a)
    # odd record: MOVE.W 46(A0),D7; odd rectangle: SUB.W 2(A1),D7; odd stack: MOVE.L A0,-(A7) of 494c0
    err('4941e-odd-record', U.with_host_writes(st, regs=dict(a0=0x100cb9), pc=0x4941e), odd_word, 0x4941e)
    err('49432-odd-rect', U.with_host_writes(st, regs=dict(a1=rect + 1), pc=0x49432), odd_word, 0x49432)
    err('494c0-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x494c0), odd_word, 0x494c0)
    # TRAP #15 boundary of 49370 (CMPA.L #108000,A5; BEQ -> 4937e): 494c0 with A5 != 108000 fails at the unrouted TRAP site 4937c
    err('494c0-49370-trap', U.with_host_writes(st, regs=dict(a5=0x108100), pc=0x494c0), 'unsupported animation machine PC', 0x4937c)
    # failures after executed blocks: bc0b2 (WORD 76 = 0 -> bc0ba) -> bc0c0 RTS at an odd A7; 49432 (zero sizes: C Clear) -> 49458 RTS at an odd A7;
    # d1514 -> d1520 JSR 4ae4a at an odd A7
    err('bc0b2-odd-stack', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 0)], regs=dict(a7=a7 + 1), pc=0xbc0b2), odd_word, 0xbc0c0)
    err('49432-odd-stack', U.with_host_writes(st, [((rect + 2) & 0xffff, 2, 0), ((rect + 6) & 0xffff, 2, 0)], regs=dict(a1=rect, a7=a7 + 1), pc=0x49432),
        odd_word, 0x49458)
    err('d1514-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xd1514), odd_word, 0xd1520)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xbc14c, 0xd1498, 0x4941e, 0xbc246)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
