"""V1 fixture spec of the animation-machine unit FR9 (engine/src/animation_machine_objects_fr9.cpp, 220 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr9-contract.md): the last C-gated area-D roots -- the af990 family: the object af8cc (N09
af768 install; installs af8f2 af910), the hit-reaction selector af990 (N09 af97e install) with the 7 computed jumps af9bc / afa40 / afac4 (27-entry
BRA.W tables af9c8 / afa4c / afad0) and afb44 / afb5e / afb78 / afbaa (2 / 2 / 8 / 2 entries), the reactions afbbe (N09 af626 install) afcf2 afda6
afe0a afe98 aff00 aff52 aff86 (installs afd7c afe40 aff30 b001a) and the helper b051a (2986 child b3dbc).  No TRAP, no JSR (An), no ROM data read.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR8) with declared host edits.  This
code runs natively only after the first C stop of its IO run (C-gated, boot-demo-0 only): besides the declared worlds the 'natural' family takes the
frame-start states of the IO native observation (artifacts/animation_machine_io_native/states, observe_animation_machine_io.read_pack) in which a node
holds one of the unit's callbacks, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the
sentinel return LONG, PC = the callback; D0-D7 / A0-A4 = the frame-start values).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 5 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node, LONG
            c(A6) := a natural node, the node / A5 fields the reachable blocks read, the stack WORDs the entered block pops, PC := the block start).
            Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 49fc6 -> afd90 (afd8a) / aff3c (aff36) / b0048 (b0042), b0468 -> afe6a (afe66),
            2986 -> b0556 (b0524).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helper b051a entered as a subroutine (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 5 consumers, odd node / stack / parent, computed landings inside
            the unit / outside the routing, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired
            'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR8 specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR8)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'fr9'
ERROR_PC = 'unsupported animation objects fr9 PC'
ERROR_CARRY = 'objects fr9 caller requires known carry'

RANGES = [(0xaf8cc, 0xaf92c), (0xaf990, 0xafb3c), (0xafb3e, 0xafc16), (0xafcf2, 0xafed8), (0xaff00, 0xb005e), (0xb051a, 0xb057e)]
STARTS = sorted([int(x, 16) for x in (
    'af8cc af8d8 af8de af8f2 af8f8 af8fe af906 af90c af910 af926 '
    'af990 af996 af99c af9a6 af9b0 af9bc afa34 afa40 afab8 afac4 '
    'afb3e afb44 afb50 afb54 afb58 afb5e afb6a afb6e afb72 afb78 afb84 afb88 afb8c afb90 afb94 afb98 afb9c afba0 afba4 afbaa afbb6 afbba afbbe afbc8 '
    'afbde afbe2 afbf8 afbfe '
    'afcf2 afcfc afd00 afd16 afd1c afd2a afd38 afd42 afd48 afd5a afd68 afd76 afd7c afd8a afd90 afd94 afda2 afda6 afdbc afdc2 afdd2 afdd8 afdde afdf0 '
    'afdfe afe0a afe20 afe30 afe40 afe4e afe54 afe66 afe6a afe6e afe74 afe7a afe80 afe84 afe8e afe94 afe98 afea2 afea6 afebc afec4 afece afed4 '
    'aff00 aff0a aff0e aff24 aff2a aff30 aff36 aff3c aff40 aff4e aff52 aff56 aff5c aff6a aff78 aff82 aff86 aff8a aff90 aff9a affa0 affb2 affc0 affc6 '
    'affdc affe0 afff6 afffc b000a b0014 b001a b0024 b0032 b003c b0042 b0048 b004c b005a '
    'b051a b0524 b0556 b055e b0578 b057c').split()] + [0xaf9c8 + 4 * k for k in range(27)] + [0xafa4c + 4 * k for k in range(27)] +
    [0xafad0 + 4 * k for k in range(27)])
CONSUMERS = (0xafd90, 0xaff3c, 0xb0048, 0xafe6a, 0xb0556)
CLEAR_SET = ()
SET_SET = (0xb0578,)                    # ORI.B #1,CCR (fall-through into the RTS b057c, which is no consumer)
CLEAR_AFTER = ()
SCC_VALUE = {}                          # no SCC / SCS consumer in this unit
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes a C to a reader in this unit
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
TRAPS = ()                              # no TRAP site in this unit
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xafd8a, 0xafd90), (0xaff36, 0xaff3c), (0xb0042, 0xb0048), (0xafe66, 0xafe6a), (0xb0524, 0xb0556))
PASS_CHAINS = ()
# the 7 computed jumps (ANDI.W #m,D0; ADD.W D0,D0; ADD.W D0,D0; JMP t(PC,D0.W)) and their transcribed BRA.W tables (contract decision 2)
TABLE_JUMPS = {0xaf9bc: tuple(0xaf9c8 + 4 * k for k in range(27)), 0xafa40: tuple(0xafa4c + 4 * k for k in range(27)),
               0xafac4: tuple(0xafad0 + 4 * k for k in range(27)), 0xafb44: (0xafb50, 0xafb54), 0xafb5e: (0xafb6a, 0xafb6e),
               0xafb78: tuple(0xafb84 + 4 * k for k in range(8)), 0xafbaa: (0xafbb6, 0xafbba)}
JUMP_PCS = (0xaf9c4, 0xafa48, 0xafacc, 0xafb4c, 0xafb66, 0xafb80, 0xafbb2)   # the JMP instructions of the 7 jump blocks
TABLE_ENTRIES = tuple(sorted(e for t in TABLE_JUMPS.values() for e in t))
# callbacks and installed values (node callbacks); the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0xaf8cc, 0xaf8f2, 0xaf910, 0xaf990, 0xafbbe, 0xafd7c, 0xafe40, 0xaff00, 0xaff30, 0xb001a)
CALLEES = (0xb051a,)
# values a direct entry pops below the return LONG at A7, lowest address first: ('L'|'W', kind) with kind any / pos (the 7 WORDs of MOVEM.W of b0556)
STACK = {0xb0556: tuple(('W', 'any') for _ in range(7))}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26)   # node links and pointer fields: natural or declared below
NATURAL = tuple(('boot-demo-0', None, f) for f in (410, 411, 419, 420, 434, 435, 444, 452, 495, 496, 509, 519, 528, 529))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)

VB = (0, 1, 2, 3, 4, 7, 8, 0xa, 0xb, 0xc, 0xf, 0x10, 0x1a, 0x1b, 0x1c, 0x1f, 0x20, 0x3f, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xdf, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0x7f, 0x80, 0xff, 0x100, 0x163, 0x1ff, 0x3ff, 0x7ff, 0x1000, 0x4000, 0x7fff, 0x8000, 0x8001, 0xc000, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x3f, 0x40, 0x8000, 0xffff, 0x10000, 0x20000, 0x7fffffff, 0x80000000, 0xffff0000, 0xffffffc0, 0xffffffff, 0x12345678)
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
    the end of the unit range (afbfe / af926 fall into the N09 starts afc16 / af92c)."""
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
    """The PC after the entry block: pcs[n] (no bundled Bcc pair in this unit)."""
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
    # 4fce0 (BRA.W of 4fcc4) is a block start of the F2 scheduler executor since the FR6 verification (the tail of 4fcda; the former declared stop is gone).
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24}
    # The size Unicorn reports to the code hook is not the M68000 instruction length (287e MOVEA.L 8(A6),A0 -> 2882 was taken for a jump), so the length is decoded.
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
            regs['d0'] = rng.choice((0, 1, 2, 3, 7, 0xa, 0xb, 0x1a, 0x1b, 0x12340001, 0xffff, 0x8000, 0x10000, 0x100))   # small WORD indices / counts
        writes = []
        regs['a0'] = self.pointer()                             # A0: a child node (written through by b055e)
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))   # the parent LONG c(A6) (afd94 / aff40 / b004c: SUBQ.B #1,62(A0))
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe-style BYTE 1d(A6) < 4 (callee worlds)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # stack values popped by the entered block (declared), the return LONG above them
        pops = []
        for size, kind in STACK.get(entry, ()):
            n = 4 if size == 'L' else 2
            pops.append((n, self.value(n)))
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
            for off, size, val in hint.get('parent', []):
                writes.append(((a6 + 0xc) & 0xffff, 4, regs['a2'] | (0xf0000 if hint.get('parent_mirror') else 0)))   # the parent (A2's node)
                writes.append(((regs['a2'] + off) & 0xffff, size, val))
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
    require(len(STARTS) == 220 and len(STARTS_SET) == 220, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS:
        require(unit_of(t) is None and not mine(t), ('TRAP site must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr9_block', ('start is not routed to fr9', hex(s), unit_of(s)))
    rng = random.Random(0xF93A)
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
    sys.stderr.write('fr9 spec: %d fixtures (%d natural), visited %d/220, missing successors %s, unreachable outcomes %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') == 'natural'), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr9: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr9: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD sign
    boundaries, equal-value ties at BCC / BNE / BEQ, BMI versus BLT on the SUBQ.W overflow), every index of the 7 computed jumps (garbage in D0 bits
    8..15 / the upper WORD, indices outside the 27-entry tables), the sign extension of EXT.L / MOVEM.W, ASR versus LSR on negative LONGs, the popped
    WORDs, the upper register bits of the WORD / BYTE operations, TST.W versus TST.L / TST.B, the node / parent in the upper RAM mirror and flag-bit
    combinations with the masks after them.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0xaf8cc, 0xaf910, 0xaf990, 0xafbc8, 0xafbe2, 0xafcf2, 0xafd00, 0xafda6, 0xafe0a, 0xafe98, 0xafea6, 0xaff00, 0xaff0e, 0xaffc6, 0xaffe0,
                 0xb000a, 0xb0524, 0xafd5a, 0xafdf0, 0xaffb2, 0xb055e, 0xafe20):
        h += [dict(regs=dict(up))]
    # ---- af8cc
    if entry == 0xaf8d8:
        h += regs('d0', (0x12340000, 0x12348000, 0x12340001, 0x12340002, 0xffff, 0x10000, 0x7fff))
    if entry == 0xaf8de:
        h += regs('d0', (0x1234abcd, 0xffff8000)) + [dict(mirror=True)]
    if entry == 0xaf8fe:
        h += word(0x96, (0, 1, 2, 0x8000, 0x8001, 0xffff)) + [dict(mirror=True, a6off=[(0x96, 2, 1)])]
    # ---- af990 selector and the computed jumps
    if entry == 0xaf99c:
        h += byte(0x61, (0, 2, 0xfd, 0xff))
    if entry in (0xaf9a6, 0xafe84):
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry in (0xaf9b0, 0xafa34, 0xafab8):
        h += [dict(regs=dict(d0=0x1234ff00), a6off=[(0x5e, 1, v)]) for v in (0, 7, 0xa, 0xb, 0x1a, 0x1b, 0x80, 0xff)]
    if entry in (0xaf9bc, 0xafa40, 0xafac4):
        h += [dict(regs=dict(d0=0x1234ff00 | k)) for k in range(0x1b)] + regs('d0', (0xffff001b, 0x12340100, 0x5555ff0a))
    if entry in (0xafb44, 0xafb5e, 0xafbaa):
        h += regs('d0', (0x1234fffe, 0x1234ffff, 0, 1, 2, 3))
    if entry == 0xafb78:
        h += [dict(regs=dict(d0=0x1234fff8 | k)) for k in range(8)]
    # ---- afbbe
    if entry == 0xafbbe:
        h += byte(0x61, (0, 0x80, 0x7f, 0xff))
    if entry == 0xafbfe:
        h += [dict(regs=dict(d0=a), a6off=[(0x2c, 2, b), (0x63, 1, 0xff)]) for a, b in ((0x1234ffff, 0xffff), (0x12340080, 0x7fff), (0xffffff7f, 0x8000),
                                                                                         (0, 0))]
        h += [dict(mirror=True, a6off=[(0x2c, 2, 1)])]
    # ---- afcf2 / afe98 / aff52 / aff86: the BYTE 5f side test and the D1.B spreads
    if entry in (0xafd1c, 0xaff5c):
        h += [dict(regs=dict(d0=a, d1=0x9abcdef0), a6off=[(0x5f, 1, b)]) for a, b in ((0x123456ff, 0), (0x12345620, 0x80), (0xffffffe0, 0x7f), (0x1f, 0xff))]
    if entry == 0xafebc:
        h += byte(0x5f, (0, 0x7f, 0x80, 0xff))
    if entry in (0xafd2a, 0xafd38, 0xaff6a, 0xaff78, 0xafec4, 0xafece):
        h += [dict(regs=dict(d1=a), a6off=[(0x15, 1, b)]) for a, b in ((0x9abcdeff, 0), (0x9abcde00, 1), (0x9abcde0e, 0xfe), (0x1f, 0xff))]
        h += [dict(mirror=True, a6off=[(0x15, 1, 0x10)])]
    if entry in (0xafd48, 0xafdde, 0xaffa0):
        h += regs('d0', (0x1234ffff, 0xffff0000, 0x8000, 0x12340400, 0xfffffc00, 0x7ff))
    if entry in (0xafd5a, 0xafdf0, 0xaffb2):
        h += [dict(regs=dict(d0=0x80000000, d1=0xffffffff)), dict(mirror=True)]
    if entry in (0xafd68, 0xafffc, 0xafdfe):
        h += [dict(regs=dict(d0=a), a6off=[(0x2c, 2, b)]) for a, b in ((0x1234ffff, 0), (0x12340080, 0x7f), (0xffffff7f, 0x8000), (0x7f, 0xffff))]
    if entry in (0xafd7c, 0xafe40):
        h += long_(0x3a, (0, 0x5000, 0x8000, 0x80000000, 0x7fffffff, 0xffffffff)) + [dict(mirror=True, a6off=[(0x3a, 4, 0x10000)])]
    if entry == 0xafdc2:
        h += [dict(regs=dict(d0=a, d1=0x9abcdef0)) for a in (0x8000, 0x80, 0x80000000, 0x10000, 0x7fff, 0xffff, 0x123456c0)]
    if entry == 0xafdd2:
        h += byte(0x15, (0, 1, 0xfe, 0xff)) + [dict(mirror=True, a6off=[(0x15, 1, 1)])]
    if entry == 0xafe20:
        h += [dict(regs=dict(up), a6off=[(0x15, 1, a), (0x36, 4, 0x12345678), (0x3a, 4, 0xffffffff)]) for a in (2, 0xff, 0xfd, 0)]
    if entry == 0xafe30:
        h += [dict(a6off=[(0x15, 1, a), (0x9b, 1, b)]) for a, b in ((0, 0), (8, 0x7f), (0xf7, 1), (0xff, 0xff))]
    if entry == 0xafe54:
        h += [dict(a6off=[(0x36, 4, a), (0x9b, 1, b)]) for a, b in ((0x80000000, 1), (0xffffffc0, 0), (0xffffffff, 0x80), (0x3f, 0xff), (0x40, 0),
                                                                    (0x7fffffff, 1), (0, 0))]
    if entry in (0xafe74, 0xaffc0):
        h += regs('d0', (0x8000, 0x80, 0x80000000, 0x10000, 0xffff, 0x7fff, 0))
    if entry in (0xafe7a, 0xafe80, 0xafe8e, 0xafe30):
        h += [dict(mirror=True)]
    if entry == 0xaff90:
        h += [dict(regs=dict(d0=a, d1=0x9abcdef0)) for a in (0x123456ff, 0x1234563f, 0xffffffc0)]
    # ---- b001a
    if entry == 0xb001a:
        h += byte(0x5e, (0xa, 0xb, 0xc, 0, 0xff, 0x8b))
    if entry == 0xb0024:
        h += long_(0x36, (0x80000000, 0xfffffffc, 0xffffffff, 3, 4, 0x7fffffff))
    if entry == 0xb0032:
        h += long_(0x3a, (0x80000000, 0xfffffffc, 0xffffffff, 3, 4, 0x7fffffff))
    if entry in (0xafd94, 0xaff40, 0xb004c):
        h += [dict(parent=[(0x62, 1, v)]) for v in (0, 1, 0x80, 0xff)] + [dict(parent_mirror=True, parent=[(0x62, 1, 5)])]
    # ---- b051a
    if entry == 0xb051a:
        h += word(0x92, (0, 1, 0x100, 0x8000, 0xffff)) + [dict(mirror=True, a6off=[(0x92, 2, 0)])]
    if entry == 0xb0524:
        h += [dict(regs=dict(up), a6off=[(0x92, 2, a), (0x94, 2, b)]) for a, b in ((0x8000, 0xffff), (1, 0x7fff))]
    if entry == 0xb055e:
        h += [dict(regs=dict(d2=0x12348000, d3=0xffff7fff, d4=0x1, d5=0xffffffff, d6=0x80000000))]
    return h


CHAIN_49FC6 = (0xafd8a, 0xaff36, 0xb0042)
# natural chain worlds (IO pack boot-demo-0, the af990-family node 1017c8): b0468 with WORD 3a < 0 runs the 4ae4a search of the natural grid; frame 517
# finds a candidate (C set -> afe6e), frame 434 none (C clear -> afe84) (scratch exp/hit468n.py: 288 of 1602 frame / node / 3a worlds of 400..577 set C)
NATURAL_CHAINS = {0xafe66: (('boot-demo-0', None, 517, 0x1017c8, ((0x3a, 2, 0x8000),)), ('boot-demo-0', None, 434, 0x1017c8, ((0x3a, 2, 0x8000),)))}
FAIL_28AE_RTS = 0x2916                  # 28ae failure path RTS (290e ANDI; 2916 RTS) back into 2986
CUE_STATUS = 0x298e                     # 2986: the PC after BSR 28ae (buffer_cue bc_status)


def cue_failure(pcs):
    """True when the 28ae failure path ran inside 2986 (its RTS 2916 returns to 298e): the C++ 2986 wrapper error (2986 caller-X, contract decision 7)."""
    for i in range(len(pcs) - 1):
        if pcs[i] == FAIL_28AE_RTS and pcs[i + 1] == CUE_STATUS:
            return True
    return False


def chain_hint(entry, t, rng):
    """Edits that let the real producer of a chain return both C values."""
    if entry in CHAIN_49FC6 and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                                # 49fc6: LONG 26(A6) = 0 -> Set
    if entry == 0xafe66:
        return dict(a6off=[(0x3a, 2, (0, 0x8000, 0xffff, 0x10)[t % 4])])                 # b0468: WORD 3a >= 0 -> Clear; < 0 -> the 4ae4a search
    if entry == 0xb0524:
        return dict(writes=[(0x4ca0, 2, (0x40, 0x15, 0x100)[t % 3])], a6off=[(0x92, 2, 0x10), (0x94, 2, 0xfff0)])   # 28ae count > 14: success (Set)
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run.  A 2986 allocation
    failure is the deliberate C++ caller-X error (an error row and a match row up to 298e)."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d, 0x5e, 0x61)] + [(6, off, 4) for off in (0x36, 0x3a, 0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            st = world.make(entry, SENTINEL, flds, chain_hint(entry, t, rng))
            tr = trace(st, first_unrouted(extra=tuple(sorted(succ))), cap=400000)
            if tr is None:
                continue
            if cue_failure(tr['pcs']):
                if 'fail' not in kept:
                    kept['fail'] = (st, tr)
                continue
            if cons not in tr['pcs']:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = tr['stop']
            if key not in kept:
                kept[key] = (st, tr)
            if set(kept) >= succ:
                break
        for cfg, case, frame, node, edits in NATURAL_CHAINS.get(entry, ()):
            # the IO-pack natural state of that frame (its grid / objects), PC := the producer call, declared node edits (WORD 3a < 0: the 4ae4a search)
            st0 = io_pack(cfg, case)[frame]
            regs = dict(st0['regs'])
            regs.update(a5=0x108000, a6=node, a7=0x10ef00)
            st = U.make_state(st0['ram'], regs, entry, st0['bank'], st0['pvc'])
            st = U.with_host_writes(st, [(0xef00, 4, SENTINEL)] + [((node + off) & 0xffff, n, v) for off, n, v in edits])
            tr = trace(st, first_unrouted(extra=tuple(sorted(succ))), cap=400000)
            require(tr is not None and cons in tr['pcs'], ('natural chain world failed', hex(entry), frame))
            record(tr['pcs'] + [tr['stop']])
            kept[('natural', frame, tr['stop'])] = (st, tr)
        require(kept, ('no chain world', hex(entry)))
        missing = succ - set(k if isinstance(k, int) else k[-1] for k in kept if k != 'fail')
        if entry == 0xb0524:
            missing -= {0xb057c}                                    # the 2986 failure side (C clear) is the caller-X error, never a match
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            if key == 'fail':
                add(U.Fixture('chain-%05x-%d-2986-failure' % (entry, i), st, [], tr['stop'], ('error', 'cue wrapper failure requires known caller X'),
                              fail_pc=CUE_STATUS, meta=dict(family='chain', fail_pc=CUE_STATUS, deliberate='2986 caller-X (contract decision 7)')))
                add(U.Fixture('chain-%05x-%d-to-298e' % (entry, i), st, [], CUE_STATUS, meta=dict(family='chain', stop=CUE_STATUS)))
                continue
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'],
                                                                                                c=tr['sr'] & 1)))


def add_run(add, name, st, tr, meta):
    """A traced run as a match fixture, or (2986 allocation failure inside the run) the caller-X error row plus the match row up to 298e."""
    if cue_failure(tr['pcs']):
        m = dict(meta, fail_pc=CUE_STATUS, deliberate='2986 caller-X (contract decision 7)')
        add(U.Fixture(name + '-2986-failure', st, [], tr['stop'], ('error', 'cue wrapper failure requires known caller X'), fail_pc=CUE_STATUS, meta=m))
        add(U.Fixture(name + '-to-298e', st, [], CUE_STATUS, meta=dict(meta, stop=CUE_STATUS)))
    else:
        add(U.Fixture(name, st, [], tr['stop'], meta=meta))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # BYTE 1d(A6) < 4; BYTE 15 / 61 / 5e / 5f / 9b (the flags tested by af99c af9a6 af9b0 afbbe afd1c afe54 afe84 b001a), WORD 96 (af8fe),
            # WORD 92 (b051a), LONG 26 (49fc6: 0 -> Set), WORD 3a (b0468), WORD 104ca0 (28ae count limit; > 14 succeeds)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 0x01, 0x81)[(t // 4) % 4]), (0x61, 1, (0, 0x80, 2, 0x82)[(t // 2) % 4]),
                               (0x5e, 1, (0, 2, 5, 7, 0xa, 0xb, 0x1b)[t % 7]), (0x5f, 1, (0, 0x80)[(t // 3) % 2]), (0x96, 2, (1, 0, 3)[t % 3]),
                               (0x92, 2, (0, 0x10)[(t // 5) % 2]), (0x9b, 1, (0, 0xff)[(t // 2) % 2])],
                        writes=[(0x4ca0, 2, (0x100, 0x15, 0x40)[(t // 11) % 3])])
            if t % 4 == 3:
                hint['a6off'].append((0x26, 4, 0))
            st = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], cue_failure(tr['pcs']), len(set(tr['pcs']) & STARTS_SET) // 4)
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
    frame start.  Up to the sentinel or the first unrouted PC."""
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
    require(count >= 5, ('too few natural node fixtures', count))


def callee_fixtures(world, add, record):
    """The helper b051a as a subroutine (return LONG = sentinel)."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry, world) + [dict(a6off=[(0x92, 2, v), (0x94, 2, 0x20)], writes=[(0x4ca0, 2, n)]) for v, n in ((0x10, 0x40), (0xfff0, 0x15),
                                                                                                                              (0x10, 0))]
        for t in range(60 + len(hints)):
            hint = hints[t] if t < len(hints) else None
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], cue_failure(tr['pcs']), tuple(p for p in tr['pcs'] if p in STARTS_SET)[:40])
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
    err('odd-pc', U.with_host_writes(st, pc=0xaf8cd), 'unaligned animation machine PC', 0xaf8cd)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W 92(A6) read of b051a, MOVE.W D0,96(A6) write of af8de; odd stack: MOVE.W #0,-(A7) of b0524, MOVEM.W (A7)+ of b0556 (declared C),
    # JSR 490ba of af8cc; odd parent: MOVEA.L c(A6),A0; SUBQ.B #1,62(A0) is a BYTE (an odd parent is legal), the parent LONG read of an odd node fails
    err('b051a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb051a), odd_word, 0xb051a, stop=0xb0524)
    err('af8de-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xaf8de), odd_write, 0xaf8de, stop=0xaf8f2)
    err('b0524-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb0524), odd_word, 0xb0524, stop=0x2986)
    err('af8cc-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xaf8cc), odd_word, 0xaf8cc, stop=0x490ba)
    err('afd94-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xafd94), odd_word, 0xafd94, stop=0x2a00)
    # computed landings: af9bc D0.B = 1c -> afa38 (inside afa34), afac4 D0.B = 1c -> afb40 (inside afb3e), afac4 D0.B = 1b -> afb3c (outside the routing)
    err('af9bc-to-afa38', U.with_host_writes(st, regs=dict(d0=0x1c), pc=0xaf9bc), ERROR_PC, 0xafa38)
    err('afac4-to-afb40', U.with_host_writes(st, regs=dict(d0=0x1c), pc=0xafac4), ERROR_PC, 0xafb40)
    err('afac4-to-afb3c', U.with_host_writes(st, regs=dict(d0=0x1b), pc=0xafac4), 'unsupported animation machine PC', 0xafb3c)
    # failures after executed blocks:
    #   af9bc (D0.B = 2: entry af9d0) -> afb58 JSR 49a58.l at an odd A7
    err('af9bc-then-afb58', U.with_host_writes(st, regs=dict(d0=2, a7=a7 + 1), pc=0xaf9bc), odd_word, 0xafb58, stop=0x49a58)
    #   afb78 (D0 = 3: entry afb90) -> afcf2 JSR 3af8.l at an odd A7
    err('afb78-then-afcf2', U.with_host_writes(st, regs=dict(d0=3, a7=a7 + 1), pc=0xafb78), odd_word, 0xafcf2, stop=0x3af8)
    #   afe7a (MOVE.L #aff00,(A6)) -> afe80 SF.B 9b(A6) -> afe84 BTST: an odd A6 fails in afe7a already (LONG write); afe80 (BYTE) passes, afe84 reads
    #   a BYTE (legal), afe8e writes a LONG at the odd A6
    err('afe80-then-afe8e', U.with_host_writes(st, [((a6 + 0x16) & 0xffff, 1, 0x80)], regs=dict(a6=a6 + 1), pc=0xafe80), odd_write, 0xafe8e, stop=0xafe94)
    #   b0578 (ORI) -> b057c RTS at an odd A7
    err('b0578-then-b057c', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb0578), odd_word, 0xb057c)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xafd48, 0xafe54, 0xb0024, 0xafbfe)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
