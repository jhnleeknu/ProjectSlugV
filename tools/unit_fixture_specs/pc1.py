"""V1 fixture spec of the area-C unit C1 (engine/src/animation_machine_player_c1.cpp, 139 block starts; file prefix pc1 / player_c1 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c1-contract.md, plan docs/analysis/area-c-completion-plan.md section 8): the player slot callback
4e68e (WORD 76 = 0 / 1; >= 2 reaches the TRAP #15 4e69a outside the routing) with its states 4e732 4e7ec 4e83c and the player creation 4e8f0..4e962 /
4e94e, the 28ae child 4f2e0 with its states 4f32e / 4f396 (bank-window LONG 2001e4), the slot helpers 4e0f6 4e4da 4e58a 4e5c2 (BYTE table 4e4d2 /
4e4d6), the player object entry 1d1f4 / 1d20c, the helpers ca3a ca50 48346 (Clear side 48368) 49bca and the leaf b7a28.  No computed jump, no JSR (An).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9) with declared host edits.  This
code runs natively only in the IO observation (P1 / P1b / boot-title-start / boot-demo-0; the D1 seeds and P0 never reach it): besides the declared
worlds the 'natural' family takes the frame-start states of the IO native observation (artifacts/animation_machine_io_native/states,
observe_animation_machine_io.read_pack) in which a node holds one of the unit's callbacks, keeps their RAM / PVC / bank and declares only the registers
(A5 = 108000, A6 = that node, A7 = 10ef00 with the sentinel return LONG, PC = the callback); the 'reinstall' family takes the same states with one
declared callback LONG ((A6) := 4e68e / 4f2e0 / 1d1f4 on the natural slot / child / player node: the entries that are installed and run inside one frame).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 3 C consumers is entered directly (the seed world with declared edits).  The Z readers 4e7da 4e7f2 4e842 are
            entered with BYTE -7699(A5) != 0 only (the native start has Z = 0, contract decision 3); their Z = 1 side comes from 4e7d4 / 4e7ec / 4e83c.
            Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers: 48346 -> 1d21c (1d216; only the Clear side 48368 is routed, the Set side 48350 is C3),
            ca32 -> 4e808 (4e802), 289e -> 4e958 (4e94e).  Stop: the consumer's successor or the first unrouted PC.
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with a declared callback LONG.
  callee    the helpers ca3a ca50 48346 49bca 4e0f6 4e4da 4e58a 4e5c2 entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 3 consumers, the Z source outside work RAM, odd node / stack / A0,
            the TRAP #15 4e69a, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match
            row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9 specs do).
"""
import gzip
import random
import re
import struct
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc1'
ERROR_PC = 'unsupported animation player c1 PC'
ERROR_CARRY = 'player c1 caller requires known carry'
ERROR_FLAG = 'unsupported animation player c1 flag source'

RANGES = [(0xca3a, 0xca42), (0xca50, 0xca56), (0x1d1f4, 0x1d222), (0x48346, 0x48350), (0x48368, 0x4836e), (0x49bca, 0x49be0), (0x4e0f6, 0x4e112),
          (0x4e4da, 0x4e4e2), (0x4e536, 0x4e538), (0x4e58a, 0x4e5b0), (0x4e5c2, 0x4e5e8), (0x4e68e, 0x4e69a), (0x4e69c, 0x4e758), (0x4e7a2, 0x4e8e6),
          (0x4e8f0, 0x4e8f8), (0x4e8fc, 0x4e962), (0x4e97e, 0x4e986), (0x4eb50, 0x4eb58), (0x4f2e0, 0x4f4ba), (0xb7a28, 0xb7a2e)]
STARTS = sorted(int(x, 16) for x in (
    'ca3a ca50 1d1f4 1d1fa 1d204 1d20c 1d216 1d21c 1d220 48346 48368 49bca 49bd6 49bda 4e0f6 4e4da 4e536 4e58a 4e596 4e59e 4e5a6 4e5c2 4e5d2 4e5de '
    '4e68e 4e69c 4e6a2 4e6cc 4e6f2 4e702 4e70c 4e70e 4e71a 4e724 4e728 4e732 4e744 4e7a2 4e7a4 4e7ac 4e7ba 4e7ca 4e7d4 4e7da 4e7e2 4e7e6 4e7ec 4e7f2 '
    '4e7fa 4e802 4e808 4e812 4e81a 4e822 4e826 4e82a 4e82c 4e832 4e836 4e83c 4e842 4e848 4e84e 4e854 4e862 4e868 4e874 4e87e 4e888 4e890 4e894 4e89e '
    '4e8ae 4e8b2 4e8b8 4e8c0 4e8d4 4e8d6 4e8e0 4e8f0 4e8fc 4e904 4e90e 4e918 4e928 4e940 4e94e 4e958 4e95a 4e97e 4eb50 4f2e0 4f304 4f322 4f328 4f32e '
    '4f33c 4f342 4f34a 4f356 4f358 4f366 4f374 4f382 4f390 4f396 4f3a4 4f3aa 4f3b2 4f3be 4f3d4 4f3e2 4f3ea 4f3f4 4f3fc 4f400 4f406 4f414 4f41c 4f426 '
    '4f42e 4f432 4f438 4f446 4f44e 4f458 4f460 4f464 4f46a 4f478 4f480 4f48a 4f492 4f496 4f49c 4f4a2 4f4b2 4f4b8 b7a28').split())
CONSUMERS = (0x1d21c, 0x4e808, 0x4e958)
CLEAR_SET = (0x48368,)                  # ANDI.B #fe,CCR; RTS (returns C Clear to the caller: 1d21c through 1d216)
SET_SET = ()
UNKNOWN_AFTER = (0x4e808,)              # SCS.B D0 consumes the C, the CMP.B after it rewrites C: Unknown after the block
CLEAR_AFTER = ()
SCC_VALUE = {0x4e808: 'd0'}             # the C shows in D0.B (SCS.B D0) as well as in the successor
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes an incoming C to a reader in this unit (48368 makes its own)
STARTS_SET = set()
# Z readers (contract decision 3): Z := BYTE -7699(A5) == 0, the TST.B of ca50 that every predecessor (4e7d4 / 4e7ec / 4e83c: JSR ca50) ran.
Z_RECOMPUTE = {0x4e7da: -0x7699, 0x4e7f2: -0x7699, 0x4e842: -0x7699}
Z_ADDR = -0x7699
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# outcomes that need a producer of a later unit: the Set side of 1d21c comes only from 48350 (C3: 48362 ORI.B #1,CCR); the declared-C rows of the C++
# unit test and the real-ROM differential cover it
LATER_GATED = {(0x1d21c, 0x1d222)}
TRAPS = (0x4e69a,)                      # TRAP #15 (WORD 76 >= 2): outside the routing, a stop
# PCs of later units that a C1 block reaches by a fall-through or a branch (declared stops of the native runs: a straight-line unrouted PC after a C1
# block is not the interior of a routed block)
EXIT_STOPS = (0x1d222, 0x48350, 0x4e4e2, 0x4e538, 0x4e564, 0x4e758, 0x4e962, 0x4e986, 0x4e8e6, 0x4e8f8, 0x4eb58, 0x4e69a)
ROUTED_LATER = (0x1d222, 0x48350)       # later-unit stops that a later unit has routed since (player C2: 1d222, player C3: 48350): still declared stops of the C1 runs
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1d216, 0x1d21c), (0x4e802, 0x4e808), (0x4e94e, 0x4e958))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()
TABLE_ENTRIES = ()
# callbacks and installed values (node callbacks); the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0x4e68e, 0x4e732, 0x4e7ec, 0x4e83c, 0x4e94e, 0x4f2e0, 0x4f32e, 0x4f396, 0x1d1f4, 0x1d20c)
CALLEES = (0xca3a, 0xca50, 0x48346, 0x49bca, 0x4e0f6, 0x4e4da, 0x4e58a, 0x4e5c2)
SLOT_FAMILY = set(range(0x4e68e, 0x4eb58))  # blocks of the slot node (LONG 78(A6) is the player record pointer there)
STACK = {}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26)   # node links and pointer fields: natural or declared below
NATURAL = tuple([('P1', 94, f) for f in (3, 4, 66, 67, 72, 73, 74, 192, 458)] + [('P1', 68, f) for f in (223, 287, 289)] +
                [('P1b', 94, f) for f in (67, 100)] + [('boot-title-start', None, f) for f in (123, 187, 193)])
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node))
REINSTALL = (('P1', 94, 3, 0x1009a8, 0x4e68e), ('P1', 94, 3, 0x100a6c, 0x4e68e), ('boot-title-start', None, 123, 0x1009a8, 0x4e68e),
             ('P1', 68, 223, 0x100a6c, 0x4e68e), ('P1', 94, 3, 0x101020, 0x4f2e0), ('P1', 68, 223, 0x10126c, 0x4f2e0),
             ('P1', 94, 73, 0x100cb8, 0x1d1f4), ('P1', 94, 192, 0x100cb8, 0x1d1f4), ('boot-title-start', None, 193, 0x100cb8, 0x1d1f4))

VB = (0, 1, 2, 3, 4, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x1f, 0x7f, 0x80, 0x81, 0xaa, 0xab, 0xa9, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0x7f, 0x80, 0xff, 0x100, 0x1ff, 0x5d5, 0x5d6, 0x600, 0x7fff, 0x8000, 0x8001, 0xffd6, 0xffe0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x270e, 0x8000, 0xffff, 0x10000, 0x7fffffff, 0x80000000, 0xffff0000, 0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')


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
BUNDLED = ()                            # no bundled Bcc pair in this unit


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (4e68e falls to the TRAP 4e69a, 4e8e0 to 4e8e6 (C6), 4f304 to 4f322)."""
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
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra') or BCC.match(mn) or a in STARTS_SET or not mine(a) or len(out) > 60:
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
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op and '(a' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr', 'jmp'):
        return None
    return {a + size}


def block_next(entry, n, tr):
    """The PC after the entry block: pcs[n] (no bundled Bcc pair in this unit)."""
    pcs = tr['pcs']
    return pcs[n] if len(pcs) > n else tr['stop']


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
            if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'abcd'):
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
        return None
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS (and the TRAP), or at the
    first unrouted PC that is not the straight-line successor of the previous instruction (a PC inside a block of another executor is not a block
    entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24} | set(EXIT_STOPS) | set(TRAPS)

    def outside(pc, prev, size):
        if pc in ex:
            return True
        if 0x16ed2 < pc <= 0x16eee:  # the routed sprite block 16ed2 (compare, set / clear BYTE 15 bit 2, RTS 16eee): its branch targets 16ee8 / 16eee are interior, never stops
            return False
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


def in_ram(addr, size=1):
    return 0x100000 <= addr and addr + size <= 0x110000 and not 0xee00 <= (addr & 0xffff) < 0xf000


def zbyte(state):
    """BYTE -7699(A5) of a state (the Z source of the readers)."""
    return state['ram'][(state['regs']['a5'] + Z_ADDR) & 0xffff]


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
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xb, 0xff, 0x100, 0x12340001, 0xffff, 0x8000, 0x10000, 0x10003))   # small slot indices / bits
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((1, 0xffffffff, 0x101, 0x1ff, 0x12345601))                                                # the 4e5d2 step
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6) (4f32e / 4f396 / 4f34a / 4f3b2)
        if entry in SLOT_FAMILY:
            writes.append(((a6 + 0x78) & 0xffff, 4, rng.choice((0x100cb8, 0x100da8, self.pointer()))))   # the player record LONG 78(A6)
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4 (callee worlds)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or (disp == 0x78 and entry in SLOT_FAMILY)):
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a5off', []):
                writes.append(((a5 + off) & 0xffff, size, val))
            regs.update(hint.get('regs', {}))
            if hint.get('mirror'):
                regs['a6'] = a6 | 0xf0000                       # the node in the upper RAM mirror (1fxxxx = 10xxxx)
            for off, size, val in hint.get('parent', []):
                writes.append(((a6 + 0xc) & 0xffff, 4, regs['a2'] | (0xf0000 if hint.get('parent_mirror') else 0)))   # the parent (A2's node)
                writes.append(((regs['a2'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
        state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        # the Z readers recompute the Z of ca50: the native direct entry starts with Z = 0, so BYTE -7699(A5) must not be 0 (contract decision 3)
        if entry in Z_RECOMPUTE and zbyte(state) == 0:
            writes.append(((state['regs']['a5'] + Z_ADDR) & 0xffff, 1, rng.choice((1, 0x80, 0xff))))
            state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        return state


out_missing = []
unreachable = []
META = {}


class Base(object):
    def __init__(self, state, stop):
        self.state, self.stop = state, stop


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 139 and len(STARTS_SET) == 139, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        # player C2 refresh: 1d222 is a C2 block start now (routed); it stays a declared stop of the C1 runs so that the C1 fixture set is unchanged
        # (was: every TRAP site / later-unit stop unrouted).  player C3 refresh: the same for 48350 (C3 block start, the Set side of 48346)
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('TRAP site / later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c1_block', ('start is not routed to player c1', hex(s), unit_of(s)))
    rng = random.Random(0xC1A1)
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
                cond_points[a] = set(t for t in (target(op), a + size) if (a, t) not in STATIC_IMPOSSIBLE and (s, t) not in LATER_GATED)
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        n = len(block_instrs(entry))
        needed = static_next(entry)
        if needed is not None and entry in Z_RECOMPUTE:
            # the native start has Z = 0: only the Z = 0 side (SNE writes ff); the Z = 1 side is covered from 4e7d4 / 4e7ec / 4e83c
            needed = set([{0x4e7da: 0x4e7e2, 0x4e7f2: 0x4e7fa, 0x4e842: 0x4e7e2}[entry]])
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
            nxt = block_next(entry, n, tr)
            if nxt in CONSUMERS:
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
            add(U.Fixture('block-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='block', entry=entry, successor=block_next(entry, n, tr))))
        if needed and len(needed) > 1:
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)) - set(t for a, t in STATIC_IMPOSSIBLE) - set(CONSUMERS))
            if missing:
                out_missing.append((entry, missing))
    chain_fixtures(world, add, record)
    node_fixtures(world, add, record)
    natural_fixtures(add, record)
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
        if blk in Z_RECOMPUTE:
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
    META['later_gated'] = [(hex(a), hex(t)) for a, t in sorted(LATER_GATED)]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('pc1 spec: %d fixtures (%d natural), visited %d/139, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc1: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc1: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (WORD 76 = 0 / 1 / 2 and
    the unsigned CMPI.W #2, the BYTE table indices 0..7 and beyond, the BSET / BCLR bit number modulo 8, all four slot bits set / clear, the
    ADD.B D1 step +1 / -1 with garbage in D1 bits 8..31, the ADDI.W #2a / CMPI.W #600 wrap, the CMPI.B #a / #f / #1 ties, the sign of ADDA.W 76, the
    Z source BYTE -7699(A5) = 0 / not 0, the input record bits 2 / 3 / 4, LONG (A0) = 270e for 289e), the upper register bits of the WORD / BYTE
    operations, the node / parent in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    a5b = lambda off, vals: [dict(a5off=[(off, 1, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0x4e68e, 0x4e6f2, 0x4e702, 0x4e70e, 0x4e71a, 0x4e728, 0x4e744, 0x4e7a4, 0x4e7ba, 0x4e888, 0x4e89e, 0x4e8c0, 0x4e928, 0x4e97e, 0x4f2e0,
                 0x4f358, 0x4f3be, 0x4f3d4, 0x4f406, 0x4f438, 0x4f46a, 0x4f3e2, 0x4f3f4, 0x4f3fc, 0x1d1fa, 0x1d20c, 0x4e868, 0x4e874, 0x4e87e):
        h += [dict(regs=dict(up))]
    # ---- slot callback
    if entry == 0x4e68e:
        h += word(0x76, (0, 1, 2, 3, 0x8000, 0xffff)) + [dict(mirror=True, a6off=[(0x76, 2, 1)])]
    if entry == 0x4e69c:
        h += regs('d0', (0, 1, 0x10000, 0x12340001, 0xffff0000))
    if entry in (0x4e6a2, 0x4e6cc, 0x4e6f2, 0x4e940):
        h += [dict(mirror=True)]
    if entry in (0x4e702, 0x4e854, 0x4e89e):
        h += word(0x76, (0, 1, 0x100, 0x8000))
    if entry == 0x4e70e:
        h += [dict(regs=dict(d0=v), a6off=[(0x76, 2, w)]) for v, w in ((0x12345603, 0), (0xffffff00, 1), (3, 0x8001))]
    if entry == 0x4e732:
        for w in (0, 1, 0xffff, 0x8000, 0x7fff):
            for b in (1, 0, 0x81):
                h.append(dict(a6off=[(0x76, 2, w)], a5off=[(0x7db6 + (w - 0x10000 if w & 0x8000 else w), 1, b)]))   # LEA 7db6(A5) + sext(WORD 76)
    if entry == 0x4e744:
        h += [dict(a6off=[(0x76, 2, w)], a5off=[(0x7004, 1, b), (0x5d1f, 1, g)]) for w, b, g in ((0, 1, 0), (0, 0xfe, 1), (1, 2, 0), (9, 2, 0x80), (8, 1, 0),
                                                                                                  (0xf, 0x7f, 0))]
    if entry == 0x4e7a4:
        h += [dict(a6off=[(0x98, 1, v)], a5off=[(0x5d1e, 1, b)]) for v, b in ((0, 0), (3, 0x8), (7, 0xe), (8, 0), (0xff, 0x7))]
    if entry == 0x4e7ac:
        h += a5b(0x5d1e, (0xf, 0xe, 0x1f, 0x8f, 0)) + [dict(regs=dict(d0=0x123456ab))]
    if entry in (0x4e7d4, 0x4e7ec, 0x4e83c, 0x4e7ca, 0x4e7e2, 0x4e7e6, 0x4e832, 0x4e836, 0x4e82c):
        h += [dict(a5off=[(Z_ADDR, 1, z), (0x5d1f, 1, g)]) for z, g in ((0, 0), (1, 0), (0x80, 1), (0xff, 0), (0, 1))]
    if entry in Z_RECOMPUTE:
        h += [dict(a5off=[(Z_ADDR, 1, z)]) for z in (1, 0x80, 0xff)] + [dict(mirror=True, a5off=[(Z_ADDR, 1, 1)])]
    if entry in (0x4e7fa, 0x4e4da, 0x4e8f0, 0x4e97e, 0x4f342, 0x4f3aa, 0x4e894, 0x4eb50):
        h += a5b(0x5d1f, (0, 1, 0x80, 0xff))
    if entry == 0x4e802:
        h += [dict(a5off=[(-0x769c, 1, v)], a6off=[(0x9a, 1, b)]) for v, b in ((0, 0), (0, 0xff), (0xa9, 0xff), (0xaa, 0), (0xab, 0xff), (0xff, 0))]
    if entry == 0x4e812:
        h += regs('d0', (0, 0xff, 0x100, 0x12345680, 0xffffff00))
    if entry == 0x4e84e:
        h += [dict(a0off=[(0, 2, v)]) for v in (0, 1, 0x8000, 0x100, 0xffff)]
    if entry == 0x4e868:
        for a0, off in ((0x104ca8, 0x4cac), (0x104cae, 0x4cb2)):
            h += [dict(regs=dict(a0=a0), writes=[(off, 1, v)]) for v in (0x10, 0x04, 0x08, 0x0c, 0, 0xef, 0x14, 0xe3)]
    if entry in (0x4e874, 0x4e87e):
        h += regs('d0', (4, 8, 0xc, 0, 0xfb, 0x12345604, 0xfffffff7, 0x400))
    if entry == 0x4e888:
        h += [dict(regs=dict(d1=d1), a6off=[(0x98, 1, v)], a5off=[(0x5d1e, 1, b)]) for d1, v, b in ((1, 0, 1), (0xffffffff, 1, 2), (0x12345601, 3, 0xb),
                                                                                                     (0xff, 2, 0x4), (1, 7, 0x7), (0x1ff, 5, 0xd))]
    if entry == 0x4e890:
        h += regs('d0', (0x12345603, 0xff)) + [dict(mirror=True)]
    if entry == 0x4e8ae:
        h += regs('d0', (0x1234fe60, 0xffff0000, 0x7fff))
    if entry == 0x4e89e:
        h += [dict(regs=dict(up), a6off=[(0x7c, 2, v), (0x76, 2, w)]) for v, w in ((0xffe0, 0), (0xfe40, 1), (0x7fff, 0), (0xffff, 1))]
    if entry == 0x4e8b8:
        h += [dict(a0off=[(0, 1, v)]) for v in (9, 0xa, 0xb, 0x80, 0xff, 0)]
    if entry == 0x4e8d6:
        h += a5b(0x7d88, (0, 1, 0x80, 0xff))
    if entry == 0x4e8fc:
        h += byte(0x99, (0, 1, 0x80, 0xff))
    if entry == 0x4e90e:
        h += byte(0x99, (0, 1, 0x80)) + [dict(mirror=True, a6off=[(0x99, 1, 0)])]
    if entry == 0x4e928:
        h += [dict(regs=dict(up), a6off=[(0x98, 1, v), (0x76, 2, w)]) for v, w in ((0xff, 0x8000), (0x80, 1), (3, 0))]
    if entry in (0x4e94e, 0x4e918):
        for rec in (0x100cb8, 0x100da8):
            h += [dict(a6off=[(0x78, 4, rec)], writes=[(rec & 0xffff, 4, v)]) for v in (0x270e, 0x270f, 0)]
    if entry == 0x4e95a:
        h += byte(0x9a, (0, 1, 0x80))
    # ---- 28ae child 4f2e0 and its states
    if entry in (0x4f32e, 0x4f396):
        h += [dict(parent=[(0x9c, 1, v)]) for v in (1, 0, 2, 0x81)] + [dict(parent_mirror=True, parent=[(0x9c, 1, 1)])]
    if entry in (0x4f34a, 0x4f3b2):
        h += [dict(parent=[(0xa1, 1, v)]) for v in (0, 1, 0x80, 0xff)]
    if entry == 0x4f3be:
        h += [dict(parent=[(0x98, 1, v)]) for v in (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xff)]
    if entry in (0x4f3d4, 0x4f406, 0x4f438, 0x4f46a):
        k = (0x4f3d4, 0x4f406, 0x4f438, 0x4f46a).index(entry)
        h += [dict(a6off=[(0x78, 1, v)]) for v in (k, k ^ 1, 0x80 | k, 0xff)]
    if entry in (0x4f3ea, 0x4f41c, 0x4f44e, 0x4f480):
        k = (0x4f3ea, 0x4f41c, 0x4f44e, 0x4f480).index(entry)
        h += a5b(0x5d1e, (1 << k, 0xff ^ (1 << k), 0, 0xff))
    if entry == 0x4f4a2:
        h += word(0x76, (0x5d5, 0x5d6, 0x5d7, 0xffd6, 0x7fff, 0xfffe, 0, 0x5ff))
    if entry == 0x4f4b2:
        h += word(0x76, (0x600, 0, 0x5ff, 0xffff))
    if entry in (0x4f304, 0x4f328, 0x4f390):
        h += [dict(mirror=True)]
    # ---- player object and helpers
    if entry in (0x1d1fa, 0x1d20c):
        h += word(0x78, (0, 1, 0x8000, 0xffff, 0x100))
    if entry == 0x48346:
        h += a5b(0x5683, (0, 2, 0xfd, 0xff))
    if entry == 0x49bca:
        h += regs('d0', (0, 1, 2, 0x10001, 0xfffe, 0x12345679))
    if entry == 0x4e0f6:
        h += regs('d0', (0, 1, 2, 3, 0xffff0001, 0x12345678))
    if entry == 0x4e58a:
        h += [dict(regs=dict(d0=d), a5off=[(0x5d1e, 1, b)]) for d, b in ((0, 0), (1, 1), (2, 0x7), (3, 0xe), (4, 0x0b), (7, 0xd), (0x100, 0), (0x1234ff03, 0xf0),
                                                                          (8, 0), (0xff, 0))]
    if entry == 0x4e596:
        h += [dict(regs=dict(d0=d), a5off=[(0x5d1e, 1, b)]) for d, b in ((0, 0), (3, 8), (8, 1), (0xb, 0), (0x10003, 0xf7), (2, 0xfb), (1, 0xd))]
    if entry == 0x4e59e:
        h += regs('d0', (3, 0xffff, 7, 0x12340002, 0xfffc))
    if entry in (0x4e5a6, 0x4e5de):
        h += regs('d0', (0, 1, 2, 3, 0x12340001, 0xffff, 0xff00ff03))
    if entry == 0x4e5c2:
        h += [dict(regs=dict(d0=d, d1=e), a5off=[(0x5d1e, 1, b)]) for d, e, b in ((0, 1, 1), (1, 0xffffffff, 4), (2, 0x101, 0x2), (3, 0x1ff, 0xf), (5, 1, 0xb),
                                                                                   (0x1234ff07, 0xff, 0x6))]
    if entry == 0x4e5d2:
        h += [dict(regs=dict(d0=d, d1=e), a5off=[(0x5d1e, 1, b)]) for d, e, b in ((0, 1, 0), (3, 1, 0x1), (0, 0xff, 0x8), (0x100ff, 0x101, 0x3), (2, 0x1ff, 0x2),
                                                                                   (1, 1, 0x4))]
    if entry == 0xb7a28:
        h += regs('d0', (0, 0x100, 1, 0x80, 0xffffff00, 0x12345600))
    if entry == 0xca3a:
        h += [dict(a5off=[(-0x76a0, 2, v)]) for v in (0, 0x8000, 0xffff)]
    if entry == 0x1d204:
        h += [dict(mirror=True)]
    return h


# chain hints: let the real producers return both C values
def chain_hint(entry, t, rng):
    if entry == 0x1d216:
        return dict(a5off=[(0x5683, 1, (0, 2, 0xfd, 0xff)[t % 4])])                    # bit 1 clear -> 48368 (C Clear); set -> 48350 (C3 stop)
    if entry == 0x4e802:
        return dict(a5off=[(-0x769c, 1, (0, 0xa9, 0xaa, 0xab, 0xff)[t % 5])], a6off=[(0x9a, 1, (0, 0xff)[(t // 5) % 2])])   # ca32: C = BYTE < aa
    if entry == 0x4e94e:
        rec = (0x100cb8, 0x100da8)[t % 2]
        return dict(a6off=[(0x78, 4, rec)], writes=[(rec & 0xffff, 4, (0x270e, 0x2b99c, 0x270e, 0)[(t // 2) % 4])])        # 289e: LONG (A0) = 270e -> Clear
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry)
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            st = world.make(entry, SENTINEL, flds, chain_hint(entry, t, rng))
            tr = trace(st, first_unrouted(extra=tuple(sorted(succ))), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            if cons not in tr['pcs']:
                if tr['stop'] == 0x48350 and 'c3' not in kept:
                    kept['c3'] = (st, tr)                       # 48346 Set side: the run stops at the C3 start 48350 (native and C++)
                continue
            key = (tr['stop'], t % 10 if cons in SCC_VALUE else 0)      # 4e808: the successor also depends on BYTE 9a; keep several hint classes
            if key not in kept:
                kept[key] = (st, tr)
            stops = set(k[0] for k in kept if isinstance(k, tuple))
            if stops >= succ and (cons not in SCC_VALUE or len([k for k in kept if isinstance(k, tuple)]) >= 6):
                break
        require(kept, ('no chain world', hex(entry)))
        missing = succ - set(k[0] for k in kept if isinstance(k, tuple))
        missing -= set(t for c, t in LATER_GATED if c == cons)
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'],
                                                                                                c=None if cons in SCC_VALUE else tr['sr'] & 1)))


def add_run(add, name, st, tr, meta):
    add(U.Fixture(name, st, [], tr['stop'], meta=meta))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # WORD 76 (slot index 0 / 1 / 2), BYTE 5d1f / 5d1e / 7d88 / 5683 (A5), BYTE -7699 (the Z source), BYTE 99 / 9a / 98 (slot), LONG 78 (record),
            # BYTE 1d(A6) < 4, WORD 104ca0 (28ae count limit; > 0 succeeds)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x76, 2, (0, 1, 0, 1, 2)[t % 5]), (0x99, 1, (0, 1, 2)[(t // 2) % 3]), (0x9a, 1, (0, 1)[(t // 3) % 2]),
                               (0x98, 1, (0, 1, 2, 3)[(t // 4) % 4])],
                        a5off=[(0x5d1f, 1, (0, 1)[(t // 2) % 2]), (0x5d1e, 1, (0, 1, 3, 0xf)[t % 4]), (0x7d88, 1, (0, 1)[(t // 5) % 2]),
                               (0x5683, 1, (0, 2)[(t // 3) % 2]), (Z_ADDR, 1, (0, 1)[(t // 7) % 2])],
                        writes=[(0x4ca0, 2, (0x100, 0x15, 0x40)[(t // 11) % 3])])
            if entry in SLOT_FAMILY:
                hint['a6off'].append((0x78, 4, (0x100cb8, 0x100da8)[t % 2]))
            if entry in (0x4f32e, 0x4f396):
                hint['parent'] = [(0x9c, 1, (1, 1, 0)[t % 3]), (0xa1, 1, (0, 1)[(t // 2) % 2]), (0x98, 1, t % 4)]
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
            add_run(add, 'node-%05x-%d' % (entry, i), st, tr, dict(family='node', entry=entry, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))


_PACKS = {}


def io_pack(cfg, case):
    """Frame-start states of one IO native run (read-only): {frame: state} decoded with observe_animation_machine_io.read_pack."""
    key = (cfg, case)
    if key not in _PACKS:
        import observe_animation_machine_io as O
        path = ROOT / 'artifacts/animation_machine_io_native/states' / cfg / ('boot.pack.gz' if case is None else '%03d.pack.gz' % case)
        _PACKS[key] = dict((fr, st) for fr, st, dg in O.read_pack(gzip.decompress(path.read_bytes())))
    return _PACKS[key]


def natural_fixtures(add, record):
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a frame in which a node of the pool NATURAL_NODES holds one of NODE_ENTRIES as its
    callback LONG; declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the
    frame start.  Up to the sentinel or the first unrouted PC.  The reinstall worlds write one declared callback LONG first (REINSTALL)."""
    entries = set(NODE_ENTRIES)
    count = 0
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        for a in range(NATURAL_NODES[0] & 0xffff, NATURAL_NODES[1] & 0xffff, 2):
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if cb not in entries:
                continue
            regs = dict(st0['regs'])
            regs.update(a5=0x108000, a6=0x100000 + a, a7=0x10ef00)
            st = U.make_state(ram, regs, cb, st0['bank'], st0['pvc'])
            st = U.with_host_writes(st, [(0xef00, 4, SENTINEL)])
            tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            add_run(add, 'natural-%05x-%s%s-f%d-%x' % (cb, cfg, '' if case is None else '%03d' % case, frame, 0x100000 + a), st, tr,
                    dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=0x100000 + a, stop=tr['stop'],
                         unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
            count += 1
    for cfg, case, frame, node, cb in REINSTALL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        regs = dict(st0['regs'])
        regs.update(a5=0x108000, a6=node, a7=0x10ef00)
        st = U.make_state(st0['ram'], regs, cb, st0['bank'], st0['pvc'])
        st = U.with_host_writes(st, [(0xef00, 4, SENTINEL), (node & 0xffff, 4, cb)])
        tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
        require(tr is not None, ('reinstall world failed', cfg, case, frame, hex(node)))
        record(tr['pcs'] + [tr['stop']])
        add_run(add, 'reinstall-%05x-%s%s-f%d-%x' % (cb, cfg, '' if case is None else '%03d' % case, frame, node), st, tr,
                dict(family='reinstall', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
        count += 1
    require(count >= 20, ('too few natural node fixtures', count))


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
            add_run(add, 'callee-%05x-%d' % (entry, i), st, tr, dict(family='callee', entry=entry, stop=tr['stop']))


def error_fixtures(bases, add):
    """Checked errors with the failing PC (Fixture fail_pc and meta, review 0264 L-1).  A failing PC that differs from the entry (and is even) gets a paired
    'match' row with stop = the failing PC (both sides stop exactly there).  The error row's stop is the PC right after the failing block."""
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_PC, pc)
    err('odd-pc', U.with_host_writes(st, pc=0x4e68f), 'unaligned animation machine PC', 0x4e68f)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the Z source outside work RAM (contract decision 3): A5 = 8000 -> BYTE 967 of the fixed ROM; A5 = 400000 -> 3f8967 (outside RAM)
    for pc in sorted(Z_RECOMPUTE):
        err('zsource-rom-%05x' % pc, U.with_host_writes(st, regs=dict(a5=0x8000), pc=pc), ERROR_FLAG, pc)
        err('zsource-io-%05x' % pc, U.with_host_writes(st, regs=dict(a5=0x400000), pc=pc), ERROR_FLAG, pc)
    #   4e7d4 (JSR ca50) -> ca50 (TST.B 967 of the ROM, RTS) -> 4e7da: the Z source is the fixed ROM
    err('4e7d4-then-4e7da', U.with_host_writes(st, regs=dict(a5=0x8000), pc=0x4e7d4), ERROR_FLAG, 0x4e7da)
    # the TRAP #15 4e69a (WORD 76 >= 2): the next dispatch fails at the TRAP site (the paired row stops right there)
    for v in (2, 0x8000, 0xffff):
        err('4e68e-trap-%04x' % v, U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, v)], pc=0x4e68e), unrouted, 0x4e69a)
    # odd node / stack / A0 / record
    err('4e68e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x4e68e), odd_word, 0x4e68e, stop=0x4e69c)
    err('4e6a2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x4e6a2), odd_write, 0x4e6a2, stop=0x4e6f2)
    err('4f32e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x4f32e), odd_word, 0x4f32e, stop=0x4f342)
    err('1d1f4-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d1f4), odd_word, 0x1d1f4, stop=0x2a0a)
    err('ca3a-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xca3a), odd_word, 0xca3a)
    err('1d204-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x1d204), odd_write, 0x1d204, stop=0x1d20c)
    err('4e84e-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x4e84e), odd_word, 0x4e84e, stop=0x4e854)
    err('4e94e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4e94e), odd_word, 0x4e94e, stop=0x289e)
    # failures after executed blocks:
    #   4e69c (D0.W = 0) -> 4e6a2 -> 4e6f2 JSR e62ec.l at an odd A7
    err('4e69c-then-4e6f2', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0x4e69c), odd_word, 0x4e6f2, stop=0xe62ec)
    #   4e58a (BYTE 5d1e = 0) -> 4e596 -> 4e5a6 RTS at an odd A7
    err('4e58a-then-4e5a6', U.with_host_writes(st, [((a5 + 0x5d1e) & 0xffff, 1, 0)], regs=dict(d0=0, a7=a7 + 1), pc=0x4e58a), odd_word, 0x4e5a6)
    #   4e7e6 (MOVE.L #4e7ec,(A6)) -> 4e7ec JSR ca50.l at an odd A7
    err('4e7e6-then-4e7ec', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4e7e6), odd_word, 0x4e7ec, stop=0xca50)
    #   48346 (BYTE 5683 bit 1 clear) -> 48368 (C Clear) RTS at an odd A7
    err('48346-then-48368', U.with_host_writes(st, [((a5 + 0x5683) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x48346), odd_word, 0x48368)
    #   4f3e2 (MOVE.W #79,D1; BRA) -> 4f400 JSR 8d34.l at an odd A7
    err('4f3e2-then-4f400', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4f3e2), odd_word, 0x4f400, stop=0x8d34)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x4e58a, 0x4e89e, 0x4f4a2, 0x4e928)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
