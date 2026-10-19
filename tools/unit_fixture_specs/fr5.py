"""V1 fixture spec of the animation-machine unit FR5 (engine/src/animation_machine_objects_fr5.cpp, 195 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr5-contract.md): the area-D IO frontier of the FR4 IO rerun 5ab82 (the 28ae child of N13
5ab3a: a thrown projectile [I]) with its installs 5ac84 / 5add8 and its 28ae child 5ad98, the fixed-point multiply 5ae66 (5ae54 / 5ae10 / 5aebe),
the fixed-point divide 5b1f8 (5aede and its 48 unrolled steps 5aeea / 5af06 + 16 k / 5af02 + 16 k) and the distance helper 4464a.  The TRAP #15
5ae0e (5ae56: product overflow, 5aee4: zero divisor) is a boundary outside the unit (contract decision 2): it is the first unrouted PC of a run.

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR4) with declared host edits.  The real entry
states of this unit are the confirmed frontier frames of the FR4 IO rerun (ms5-scratch/fr4/ioA/frontier.json: P1 / P1b frame 141 callback 5ab82) and
their natural successors (frames 142..600 of the same runs); this spec does not decode the IO packs (the IO comparison rerun checks the natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 6 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node, LONG
            c(A6) := a natural node, the node / parent / A5 fields the reachable blocks read, the stack values the entered block pops, PC := the block
            start).  Stop: the first PC outside the unit (the TRAP 5ae0e included).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 4945e -> 5abd6 (5abbe), 4b6f4 -> 5acac (5aca6), 1ab80 -> 5ad60 (5ad54) / 5ae02 (5adf6),
            28ae -> 5ad80 (5ad70), 49fc6 -> 5adf2 (5adec).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 6 consumers, odd node / stack pointers, failures after executed
            blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is
            even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR4 specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR4)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x4464a, 0x44666), (0x5ab82, 0x5ae0e), (0x5ae10, 0x5ae3e), (0x5ae54, 0x5ae98), (0x5aebe, 0x5b220)]
DIVIDE_STEPS = tuple(0x5af06 + 16 * k for k in range(47))       # ADD.L / ADDX.W / ADDX.L / CMP.L / BCS.W (the first step is inside 5aeea)
SUBTRACT_BLOCKS = tuple(0x5af02 + 16 * k for k in range(48))    # ADDQ.W #1,D0; SUB.L D2,D3
STARTS = sorted([int(x, 16) for x in (
    '4464a 4464e 44650 44654 44656 4465a 44660 '
    '5ab82 5ab9a 5aba0 5abae 5abbe 5abd6 5abda 5abe2 5abea 5abf6 5abfa 5ac14 5ac1e 5ac2e 5ac3a 5ac3e 5ac4a 5ac56 5ac68 5ac84 5ac8c 5ac9e 5aca6 5acac '
    '5acb0 5acbe 5acde 5ace8 5acfe 5ad0c 5ad12 5ad1c 5ad32 5ad40 5ad4c 5ad54 5ad60 5ad64 5ad66 5ad70 5ad80 5ad84 5ad8e 5ad92 5ad98 5adac 5adba 5adca '
    '5add8 5adec 5adf2 5adf6 5ae02 5ae06 5ae08 '
    '5ae10 5ae24 5ae26 5ae32 5ae34 '
    '5ae54 5ae56 5ae5a 5ae60 5ae64 5ae66 5ae72 5ae76 5ae7c 5ae80 5ae86 5ae8c 5ae90 5ae92 '
    '5aebe 5aec4 5aeca 5aed0 5aed6 5aed8 5aeda 5aede 5aee4 5aeea 5b1f6 5b1f8 5b200 5b204 5b20a 5b20e 5b214 5b21c 5b21e').split()]
    + list(DIVIDE_STEPS) + list(SUBTRACT_BLOCKS))
CONSUMERS = (0x5abd6, 0x5acac, 0x5ad60, 0x5ad80, 0x5adf2, 0x5ae02)
CLEAR_SET = ()                          # no ANDI.B #fe,CCR in this unit
SET_SET = (0x5ad8e,)                    # ORI.B #1,CCR (its C is not read: JMP 2a00)
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes a C in this unit
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
# 5ae22 BCC.B 5ae26 after the first ADD.L D2,2(A7) of 5ae10: the LONG at 2(A7) is 0000:(the high WORD of lo x lo) <= 0000fffe and the addend
# (hi x lo) <= fffe0001, so the sum never carries: the fall-through 5ae24 is reached only by a direct entry.
STATIC_IMPOSSIBLE = {(0x5ae22, 0x5ae24)}
TRAPS = (0x5ae0e,)                      # TRAP #15 boundary (contract decision 2): unrouted, the first unrouted PC of a run
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x5abbe, 0x5abd6), (0x5aca6, 0x5acac), (0x5ad54, 0x5ad60), (0x5ad70, 0x5ad80), (0x5adec, 0x5adf2), (0x5adf6, 0x5ae02))
PASS_CHAINS = ()
TABLE_ENTRIES = ()
# callbacks and installed values (node callbacks); the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0x5ab82, 0x5ac84, 0x5ad98, 0x5add8)
CALLEES = (0x4464a, 0x5ae66, 0x5ae54, 0x5ae10, 0x5b1f8, 0x5aede)
# values a direct entry pops or reads below the return LONG at A7, lowest address first: ('L'|'W', kind) with kind node / any / small
STACK = {0x5ac14: (('L', 'any'),), 0x5ac4a: (('L', 'any'),), 0x5ac56: (('W', 'any'), ('W', 'any')), 0x5ae24: (('L', 'any'), ('L', 'any')),
         0x5ae26: (('L', 'any'), ('L', 'any')), 0x5ae32: (('L', 'any'), ('L', 'any')), 0x5ae34: (('L', 'any'), ('L', 'any')), 0x5b214: (('W', 'any'),)}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22)   # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 7, 8, 0xf7, 0x10, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfd, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0x10, 0x3f, 0x40, 0x41, 0x5f, 0x60, 0x7f, 0x80, 0xff, 0x100, 0x11ff, 0x120, 0x121, 0x1200, 0x1201, 0x7fff, 0x8000, 0x8001, 0xffbf,
      0xffc0, 0xffc1, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x10, 0x100, 0x4900, 0x7fff, 0x8000, 0xffff, 0x10000, 0x10001, 0x500000, 0x1000000, 0x7fffffff, 0x80000000, 0xffff0000, 0xffffff00,
      0xffffffff, 0x12345678)
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
BUNDLED = ()                            # no flag-sharing Bcc pair in this unit


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


def block_next(entry, n, tr):
    """The PC after the entry block: pcs[n] (a bundled Bcc pair would take pcs[n - 1]; this unit has none)."""
    pcs = tr['pcs']
    instrs = block_instrs(entry)
    if len(instrs) > 1 and instrs[-1][0] in BUNDLED and (len(pcs) < n or pcs[n - 1] != instrs[-1][0]):
        return pcs[n - 1] if len(pcs) >= n else tr['stop']
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
        regs['a0'] = self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        # the pointer the unit follows: LONG c(A6) (parent: BYTE 61 / 80, WORD 84 / 86 of 5acb0 5ac1e 5add8 5ace8)
        par = self.pointer()
        writes.append(((a6 + 0xc) & 0xffff, 4, par))
        for off, size in ((0x61, 1), (0x80, 1), (0x84, 2), (0x86, 2)):
            if rng.random() < 0.6 and 0x100000 <= par + off < 0x110000 and not 0xee00 <= ((par + off) & 0xffff) < 0xf000:
                writes.append(((par + off) & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4 (>= 4 reaches the TRAP #15 8ec8)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # the BYTE 568e(A5) of 4945e (49370: 0 -> Set) and the BYTE 5b86(A5) of 4b6f4 (0 -> Clear, otherwise Set)
        if rng.random() < 0.5:
            writes.append(((a5 + 0x568e) & 0xffff, 1, rng.choice((0, 0, 1, 2, 3))))
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5b86) & 0xffff, 1, rng.choice((0, 0, 1, 0x80))))
        # stack values popped by the entered block (declared), the return LONG above them
        pops = []
        for size, kind in STACK.get(entry, ()):
            v = {'node': self.pointer(), 'a6': a6, 'small': rng.choice((0, 1, 2, 3)), 'any': self.value(4 if size == 'L' else 2)}[kind]
            pops.append((4 if size == 'L' else 2, v))
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
                writes.append(((a5 + off) & 0xffff, size, val))
            regs.update(hint.get('regs', {}))
            if hint.get('mirror'):
                regs['a6'] = a6 | 0xf0000                       # the node in the upper RAM mirror (1fxxxx = 10xxxx)
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
            if hint.get('stack'):
                # the WORD / LONG values right below the return LONG (replace the declared pops)
                at = regs['a7']
                for n, v in hint['stack']:
                    writes.append((at & 0xffff, n, v))
                    at += n
        state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        if hint and hint.get('parent'):
            ram = state['ram']
            par = (ram[(a6 + 0xc) & 0xffff] << 24) | (ram[(a6 + 0xd) & 0xffff] << 16) | (ram[(a6 + 0xe) & 0xffff] << 8) | ram[(a6 + 0xf) & 0xffff]
            if 0x100000 <= par < 0x110000:
                state = U.with_host_writes(state, [((par + off) & 0xffff, size, val) for off, size, val in hint['parent']])
        if hint and hint.get('parent_mirror'):
            ram = state['ram']
            par = (ram[(a6 + 0xc) & 0xffff] << 24) | (ram[(a6 + 0xd) & 0xffff] << 16) | (ram[(a6 + 0xe) & 0xffff] << 8) | ram[(a6 + 0xf) & 0xffff]
            if 0x100000 <= par < 0x110000:
                state = U.with_host_writes(state, [((a6 + 0xc) & 0xffff, 4, par | 0xf0000)])   # LONG c(A6) := the parent in the upper RAM mirror
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
    require(len(STARTS) == 195 and len(STARTS_SET) == 195, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS:
        require(unit_of(t) is None and not mine(t), ('TRAP site must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr5_block', ('start is not routed to fr5', hex(s), unit_of(s)))
    rng = random.Random(0xF53A)
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
        bundled = len(block_instrs(entry)) > 1 and block_instrs(entry)[-1][0] in BUNDLED
        needed = static_next(entry)
        flds = fields_of(entry)
        kept = {}
        extra = 0
        hints = hint_worlds(entry, world)
        for t in range(MAX_TRIES + len(hints)):
            stats['tries'] += 1
            st = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
            tr = trace(st, outside_unit())
            if tr is None or len(tr['pcs']) < n - (1 if bundled else 0):
                stats['rejected'] += 1
                continue
            record(tr['pcs'] + [tr['stop']])
            nxt = block_next(entry, n, tr)
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
            add(U.Fixture('block-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='block', entry=entry, successor=block_next(entry, n, tr))))
        if needed and len(needed) > 1:
            # a statically impossible branch and a consumer successor (any entry -> consumer, e.g. 73120 -> 73124: covered by the chain fixtures) are not block-row outcomes
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)) - set(t for a, t in STATIC_IMPOSSIBLE) - set(CONSUMERS))
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
    sys.stderr.write('fr5 spec: %d fixtures, visited %d/195, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out

def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr5: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr5: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts

def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries, equal-value ties at BLE / BLT / BLS / BCC / BCS / BEQ, sign / zero extension (EXT.L, the MOVEM.W pops, MOVEQ #0 + MOVE.W + SWAP), the
    MULU.W upper WORDs, the popped registers, the upper register bits of the WORD / BYTE operations, the X of NEG.L + NEGX.L and ADD.L + ADDX, the
    node and the parent in the upper RAM mirror, bit combinations, the TRAP boundary operands (product overflow, zero divisor)).  Every hint world is
    kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788)
    if entry == 0x4464a:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0x12348000, 0x9abc0001), (0x00008000, 0x80000000), (0x10, 0x10), (0xfff0, 0x10), (0x7fff, 0x8000),
                                                       (0, 0), (1, 0xffff), (0x80000000, 0x00007fff))]
    if entry in (0x4464e, 0x44654):
        h += [dict(regs=dict(d0=v, d1=v)) for v in (0x12348000, 0xffff0001, 0x0000ffff, 0)]
    if entry == 0x44650:
        h += regs('d1', (0x00008000, 0x80000000, 0x7fff, 0xffff7fff))
    if entry == 0x44656:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((5, 5), (5, 6), (6, 5), (0x8000, 0x7fff), (0x7fff, 0x8000), (0x12340005, 0x56780005), (0xffff0004, 5))]
    if entry in (0x4465a, 0x44660):
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0x1234ffff, 0x5678ffff), (0xffff0001, 0xffff8000), (0x8000, 0x8000), (0, 1))]
    if entry in (0x5ab82, 0x5ad98, 0x5aba0, 0x5adac, 0x5abae, 0x5adba, 0x5ad32, 0x5ad66, 0x5ad70, 0x5ad84, 0x5ac2e, 0x5ac3e, 0x5ad40, 0x5ad54, 0x5adf6):
        h += [dict(regs=dict(up))]
    if entry == 0x5abbe:
        h += byte(0x15, (0, 8, 0xf7, 0xff))
    if entry == 0x5abda:
        h += [dict(regs=dict(d0=0x12345678), a0off=[(0x42, 2, v)]) for v in (0, 0x8000, 0xffff)]
    if entry == 0x5abe2:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x42, 2, v)]) for v in (0, 0x5f, 0x60, 0x805f, 0xffff)]
    if entry == 0x5abea:
        h += [dict(regs=dict(d0=a), a6off=[(0x42, 2, b)]) for a, b in ((0x1234ffc0, 0), (0xffc1, 0), (0xffbf, 0), (0x7fff, 0xffff), (0x10, 0x50), (0, 0x40),
                                                                   (0, 0x3f), (0x8000, 1), (0x12340000, 0x8000))]
    if entry == 0x5abf6:
        h += regs('d0', (0x12345678, 0))
    if entry == 0x5abfa:
        h += [dict(regs=dict(d0=0x1234ffc0, d1=0x9abcdef0, d2=0x55667788), a6off=[(0x46, 2, v)]) for v in (0, 0x120, 0x121, 0x8120, 0xffff)]
    if entry == 0x5ac14:
        h += [dict(regs=dict(d0=d, d1=0x9abcdef0), stack=[(4, v)]) for d, v in ((0x12340080, 0x1000000), (0xffff8000, 0x80000000), (0x0000ffff, 0))]
    if entry == 0x5ac1e:
        h += [dict(parent=[(0x80, 1, v)]) for v in (0, 2, 0xfd, 0xff)]
        h += [dict(parent_mirror=True, parent=[(0x80, 1, 2)])]
    if entry == 0x5ac4a:
        h += [dict(regs=dict(d0=d, d1=0x9abcdef0), stack=[(4, v)]) for d, v in ((0x12348000, 0x10000), (0x00007fff, 0x80000000), (0xffff0000, 0x12345678),
                                                                              (0x0000ff80, 1))]
    if entry == 0x5ac56:
        h += [dict(regs=dict(d0=0x12345678, d3=0x9abcdef0), stack=[(2, a), (2, b)]) for a, b in ((0x8000, 0x7fff), (0x7fff, 0xffff), (0, 0x8001))]
    if entry == 0x5ac68:
        h += [dict(regs=dict(up), a6off=[(0x8a, 2, 0xffff), (0x88, 2, 0x1234), (0x8c, 2, 0x5678)])]
    if entry == 0x5ac84:
        h += long_(0x36, (0, 0x7fffffff, 0x80000000, 0xffffffff, 0x00008000))
        h += [dict(mirror=True, a6off=[(0x36, 4, 0x80000000)])]
    if entry == 0x5ac8c:
        h += [dict(a6off=[(0x36, 4, 0x12345678), (0x90, 4, 0x9abcdef0), (0x3a, 4, 0x5555)])]
    if entry == 0x5ac9e:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x36, 4, a), (0x90, 4, b)]) for a, b in ((0x7fffffff, 1), (0x80000000, 0xffffffff), (0xffffff00, 0x100))]
    if entry == 0x5acb0:
        h += [dict(parent=[(0x61, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)]
        h += [dict(parent_mirror=True, parent=[(0x61, 1, 0x80)])]
    if entry == 0x5acbe:
        h += [dict(a6off=[(0x1e, 2, a), (0x36, 4, b), (0x3a, 4, c), (0x94, 4, d)]) for a, b, c, d in ((0x8000, 0x80000000, 0xffffff00, 0x100),
                                                                                                  (0x7fff, 0x7fffffff, 0x7fffffff, 1), (0, 0xff, 0x80000000, 0x80000000),
                                                                                                  (0x1234, 0x12345678, 0, 0x4900))]
        h += [dict(mirror=True, a6off=[(0x36, 4, 0xfffff000)])]
    if entry == 0x5acde:
        h += [dict(regs=dict(d0=a), a6off=[(0x8a, 2, b)]) for a, b in ((0x12340001, 0xffff), (0xffff8000, 0x8000), (0, 0x1200))]
    if entry == 0x5ace8:
        h += [dict(regs=dict(d0=0x12345678), parent=[(0x86, 2, a)], a6off=[(0x32, 4, b)]) for a, b in ((0x50, 0x500000), (0x50, 0x4fffff), (0x50, 0x500001),
                                                                                                    (0x8000, 0), (0x7fff, 0x80000000), (0, 0), (0x7fff, 0x7fff0000),
                                                                                                    (0xffff, 0xffff0000), (0xffff, 0xfffeffff))]
        h += [dict(parent_mirror=True, parent=[(0x86, 2, 0x50)], a6off=[(0x32, 4, 0x500000)])]
    if entry == 0x5acfe:
        h += [dict(regs=dict(d0=v), a6off=[(0x3a, 4, 0x12345678)]) for v in (0x00500000, 0x80000000)]
    if entry == 0x5ad12:
        h += word(0x8a, (0x11ff, 0x1200, 0x1201, 0x8000, 0x7fff, 0, 0xffff))
        h += [dict(mirror=True, a6off=[(0x8a, 2, 0x1200)])]
    if entry == 0x5ad1c:
        h += [dict(regs=dict(up), a6off=[(0x8a, 2, v)]) for v in (0x1200, 0x11ff, 0x8000)]
    if entry == 0x5ad4c:
        h += regs('d0', (0, 1, 0x10000, 0xffff0000, 0x8000))
    if entry == 0x5adca:
        h += [dict(a6off=[(0x36, 4, 0x12345678), (0x3a, 4, 0x9abcdef0)])]
    if entry == 0x5add8:
        h += [dict(parent=[(0x84, 2, v)]) for v in (0, 1, 0x8000, 0xffff)]
        h += [dict(parent_mirror=True, parent=[(0x84, 2, 0)])]
    if entry == 0x5ae10:
        h += [dict(regs=dict(d0=a, d1=b, d2=0x55667788)) for a, b in ((0xffffffff, 0xffffffff), (0x12345678, 0x9abcdef0), (0x0000ffff, 0xffff0000),
                                                                     (0xffff0000, 0x0000ffff), (0x00010000, 0x00010000), (0, 0x7fffffff), (0x8000ffff, 0x00018000))]
    if entry in (0x5ae24, 0x5ae32):
        h += [dict(stack=[(2, v), (2, 0x1234), (4, 0x56789abc)]) for v in (0xffff, 0x7fff, 0)]
    if entry == 0x5ae26:
        h += [dict(regs=dict(d0=a, d1=b), stack=[(4, s1), (4, s2)]) for a, b, s1, s2 in ((0xffffffff, 0xffffffff, 0x0000fffe, 0xfffe0001),
                                                                                       (0x12345678, 0x9abcdef0, 0, 0), (0x0000ffff, 0xffff0000, 0x0000ffff, 0xffff0000),
                                                                                       (0xffff0001, 0x0001ffff, 0x0000ffff, 0xffffffff))]
    if entry == 0x5ae34:
        h += [dict(regs=dict(d0=a, d1=b), stack=[(4, s1), (4, s2)]) for a, b, s1, s2 in ((0xffffffff, 0xffffffff, 0xfffffffe, 1),
                                                                                       (0x12345678, 0x9abcdef0, 1, 0x80000000), (0x00010000, 0x00010000, 0, 0))]
    if entry == 0x5ae54:
        h += [dict(regs=dict(d0=a, d1=b, d7=c)) for a, b, c in ((0xffffffff, 0xffffffff, 0), (0x7fffffff, 0x7fffffff, 0xff), (0x10000, 0x10000, 1), (0, 5, 1))]
    if entry == 0x5ae56:
        h += regs('d1', (0x80000000, 0x7fffffff, 0, 0xffffffff, 0x00008000))
    if entry in (0x5ae5a, 0x5aed0):
        h += regs('d7', (0, 0x100, 0xff, 0x80, 0x12345601))
    if entry == 0x5ae60:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 5), (1, 5), (0x80000000, 0), (0, 0x80000000), (0xffffffff, 0xffffffff), (0, 0))]
    if entry in (0x5ae66, 0x5b1f8):
        h += [dict(regs=dict(d0=a, d1=b, d3=0x12345678, d7=0x9abcdef0)) for a, b in ((0x80000000, 1), (0xffffffff, 0x80000000), (0x00008000, 0x00010000),
                                                                                    (0x7fffffff, 0xffff0000), (0, 0), (0x00010000, 0xfffe0000))]
    if entry in (0x5ae72, 0x5ae7c, 0x5b200, 0x5b20a):
        h += [dict(regs=dict(d0=a, d1=a, d7=b)) for a, b in ((0x80000000, 0x12345600), (1, 0x123456ff), (0, 0x80))]
    if entry in (0x5ae76, 0x5b204):
        h += regs('d1', (0x80000000, 0x7fffffff, 0x00008000, 0))
    if entry in (0x5ae80, 0x5ae86):
        h += [dict(regs=dict(d0=a, d1=b, d3=0x10000)) for a, b in ((0xffff, 0xffff), (0x10000, 0), (0x10001, 0), (0, 0x10000), (0xffff, 0x10001), (0x80000000, 0))]
        h += [dict(regs=dict(d0=0x5000, d1=0x5000, d3=0x5000))]
    if entry == 0x5ae92:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0))]
    if entry in (0x5aebe, 0x5aec4):
        h += [dict(regs=dict(d0=a, d1=b, d3=0x10000)) for a, b in ((0x10000, 0x10000), (0xffff, 0x10000), (0x10000, 0xffff), (0x8000, 0x8000), (0x10001, 0xffff))]
    if entry == 0x5aeca:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0x1234ffff, 0x5678ffff), (0x8000, 0x8000), (0xffff0001, 0x0000ffff), (0x00010000, 0x00012345))]
    if entry in (0x5aed6, 0x5b21c):
        h += regs('d0', (0, 1, 0x80000000))
    if entry == 0x5aeda:
        h += regs('d1', (0x12345678,))
    if entry in (0x5aede, 0x5aee4):
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 1), (1, 0), (0x00010000, 0), (0x80000000, 0x00010000), (0x00008000, 0x00008000))]
    if entry == 0x5aeea:
        h += [dict(regs=dict(d0=a, d1=b, d3=0x12345678)) for a, b in ((0x7fffffff, 1), (0x00010000, 0x00010000), (0x80000000, 0x80000000), (0x0000ffff, 0xffffffff),
                                                                     (0x12345678, 0x00001000), (0x00008000, 3))]
    if entry in DIVIDE_STEPS:
        h += [dict(regs=dict(d0=a, d1=b, d2=c, d3=d)) for a, b, c, d in ((0x80000000, 0x12348000, 0x1000, 0x7ff), (0x7fffffff, 0x0000ffff, 0x10000, 0x8000),
                                                                         (0, 0x8000, 0x80000000, 0x40000000), (0xffffffff, 0xffffffff, 0xffffffff, 0x7fffffff),
                                                                         (0, 0x12340000, 0x1000, 0x800), (0, 0x12348000, 0x1000, 0x7ff),
                                                                         (0, 0x12348000, 0x1000, 0x800), (0x40000000, 0x4000, 3, 1))]
    if entry in SUBTRACT_BLOCKS:
        h += [dict(regs=dict(d0=a, d2=b, d3=c)) for a, b, c in ((0x1234ffff, 1, 0), (0x12340000, 0x10, 0x10), (0xfffffffe, 0x80000000, 0x7fffffff))]
    if entry == 0x5b20e:
        h += regs('d7', (0x123456ff, 0, 0x80))
    if entry == 0x5b214:
        h += [dict(regs=dict(d7=0x12345678, d0=1), stack=[(2, v)]) for v in (0, 0xff, 0xff00, 0x8001)]  # D0 = 1 (not 80000000, its own NEG.L) so 5b21c vs 5b21e differ in D0
    return h


def rng_count(t):
    return (0, 1, 0x1e, 0x1f)[(t // 2) % 4]


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d, 0x61)] + [(6, off, 2) for off in (0x42, 0x46, 0x4a, 0x4e)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry == 0x5abbe and t % 2:
                hint = dict(writes=[(0xd68e, 1, (0, 1, 2, 3)[(t // 2) % 4])])                                # 4945e -> 49370: BYTE 568e(A5) = 0 -> Set
            elif entry == 0x5aca6:
                hint = dict(writes=[(0xdb86, 1, (0, 1, 0x80)[t % 3])])                                       # 4b6f4: BYTE 5b86(A5) = 0 -> Clear, otherwise Set
            elif entry in (0x5ad54, 0x5adf6) and t % 2:
                hint = dict(a6off=[(0x42, 4, (0x00a00000, 0x7fff0000)[(t // 2) % 2]), (0x46, 4, (0x01800000, 0x7fff0000)[(t // 4) % 2]),
                                   (0x4a, 4, 0), (0x4e, 4, 0), (0x15, 1, 0)])                                    # 1ab80: on screen (Clear) / off (Set)
            elif entry == 0x5ad70 and t % 2:
                hint = dict(writes=[(0x4ca0, 2, rng_count(t))])                                                  # 28ae: WORD 104ca0 <= D0 (1e) -> 290e Clear
            elif entry == 0x5adec and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                                                # 49fc6: LONG 26(A6) = 0 -> ORI Set
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(extra=succ), cap=400000)
            if tr is None or cons not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = tr['stop']
            if key not in kept:
                kept[key] = (st, tr)
            if set(k for k in kept if isinstance(k, int)) >= succ:
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
            # 8ebe / 8ff4: BYTE 1d(A6) < 4 (>= 4 reaches the untraceable TRAP #15 8ec8); LONG 36 sign (5ac84), WORD 8a around 1200 (5ad12),
            # BYTE 5b86(A5) (4b6f4), WORD 42 / 46 (the 1ab80 screen test)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x36, 4, (0, 0x80000000, 0x100, 0xffffff00)[(t // 4) % 4]), (0x8a, 2, (0, 0x11ff, 0x1200, 0x2400)[(t // 2) % 4]),
                               (0x42, 2, (0xa0, 0x7fff)[(t // 16) % 2])],
                        writes=[(0xdb86, 1, (0, 0, 1)[(t // 8) % 3])])
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr5 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x5ab83), 'unaligned animation machine PC', 0x5ab83)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr5 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # odd node: TST.L 36(A6) of 5ac84 (read), CLR.L 36(A6) of 5ac8c (write); odd stack (5ac14 MOVE.L (A7)+,D1)
    err('5ac84-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x5ac84), odd_word, 0x5ac84, stop=0x5ac8c)
    err('5ac8c-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x5ac8c), odd_write, 0x5ac8c, stop=0x5aca6)
    err('5ac14-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x5ac14), odd_word, 0x5ac14, stop=0x5b1f8)
    # the TRAP #15 boundary 5ae0e (decision 2): zero divisor (5b1f8 -> 5b204 -> 5b20e -> 5aede -> 5aee4 -> 5ae0e), product overflow (5ae54 -> 5ae10 ->
    # 5ae26 / 5ae32 -> 5ae34 -> 5ae56 -> 5ae0e): the next dispatch fails, the failing PC is the TRAP site (the paired row stops right there)
    err('5b1f8-zero-divisor', U.with_host_writes(st, regs=dict(d0=5, d1=0), pc=0x5b1f8), unrouted, 0x5ae0e)
    err('5ae54-product-overflow', U.with_host_writes(st, regs=dict(d0=0xffffffff, d1=0xffffffff, d7=0), pc=0x5ae54), unrouted, 0x5ae0e)
    # failures after executed blocks:
    nd = base.state['regs']['a6']
    #   4464a (D0.W = 8000) -> 4464e -> 44650 -> 44656 -> 44660 RTS at an odd A7
    err('4464a-then-44660', U.with_host_writes(st, regs=dict(d0=0x8000, d1=0, a7=a7 + 1), pc=0x4464a), odd_word, 0x44660)
    #   5ac84 (LONG 36 >= 0) -> 5ac8c -> 5aca6 JSR 4b6f4 at an odd A7
    err('5ac84-then-5aca6', U.with_host_writes(st, [((nd + 0x36) & 0xffff, 4, 0)], regs=dict(a7=a7 + 1), pc=0x5ac84), odd_word, 0x5aca6, stop=0x4b6f4)
    #   5adca (MOVE.L #5add8,(A6) enters 5add8) -> 5add8 SUBQ.W #1,84(A0) with an odd parent LONG c(A6)
    err('5adca-then-5add8', U.with_host_writes(st, [((nd + 0xc) & 0xffff, 4, 0x10eb01)], pc=0x5adca), odd_word, 0x5add8, stop=0x43e34)
    #   5aede (D0 = D1 = 10000) -> 5aeea -> 47 steps / subtract blocks -> 5b1f6 RTS at an odd A7
    err('5aede-then-5b1f6', U.with_host_writes(st, regs=dict(d0=0x10000, d1=0x10000, a7=a7 + 1), pc=0x5aede), odd_word, 0x5b1f6)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x5aeca, 0x5ae10, 0x5ac4a, 0x5acbe)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
