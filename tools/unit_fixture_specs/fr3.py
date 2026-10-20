"""V1 fixture spec of the animation-machine unit FR3 (engine/src/animation_machine_objects_fr3.cpp, 197 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr3-contract.md): the area-D IO-frontier objects of the FR2b IO rerun c5370 (object table
e9004; c53ec / c561a / c564e, the empty helper c579e) and bc93c (FR2b install; bc972 / bc9e0 / bca0e) with their natural successors in the same runs:
the N15 28ae children 76ff2 (7703e) and 7706a (77138, 771e6, the helpers 77284, d0fec, ea69c) with its child 77206 (77258), the U18 install ea85a
(ea8d2), the FR2b install 70d92 (70dfc), the FR1c 28ae child bc404 (bc464), and the rest of the d0fec helper module d1028 (d108a, d10b4).

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR2b) with declared host edits.  The real entry
states of this unit are the confirmed frontier frames of the FR2b IO rerun (ms5-scratch/fr2b/ioA/frontier.json: P1 / P1b frame 252 callback c5370,
frame 276 callback bc93c) and their natural successors (frames 253..496 / 277..309 of the same runs); this spec does not decode the IO packs (the IO
comparison rerun checks the natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 17 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node, LONG
            c(A6) := a natural node, the node / parent / A5 fields the reachable blocks read, the stack WORD / LONG values the entered block pops, PC :=
            the block start).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 49fc6 -> 70e12 (70e0c) / 7704a (77044) / 77264 (7725e) / bc470 (bc46a) / bca1a
            (bca14) / ea8fc (ea8f6), the ANDI of ea8e8 -> ea8fc, 1ab80 -> 7705e (77054), 1ab02 -> 77158 (7714e) / 77278 (7726e), 76f98 -> 770bc
            (770b6), ea69c -> 77170 (7716a), 28ae -> 771ca (771ba), 4b54e -> c5412 (c540c) / c5682 (c567c), 1abda -> ea6b8 (ea6b0), ea65a -> ea6cc
            (ea6bc), 4c2cc -> ea86e (ea860).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 17 consumers, odd node / stack pointers, DIVU zero divisors,
            failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs
            from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR2b specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR2b)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x70d92, 0x70e2a), (0x76ff2, 0x771de), (0x771e6, 0x772a0), (0xbc404, 0xbc47c), (0xbc93c, 0xbca2c), (0xc5370, 0xc5432), (0xc561a, 0xc5696),
          (0xc579e, 0xc57a0), (0xd0fec, 0xd10d8), (0xea69c, 0xea6a2), (0xea6b0, 0xea712), (0xea85a, 0xea908)]
STARTS = [int(x, 16) for x in (
    '70d92 70d9a 70dc2 70dc6 70dee 70dfc 70e06 70e0c 70e12 70e16 70e20 70e26 76ff2 77010 77038 7703e 77044 7704a 7704e 77054 7705e 77062 77068 7706a '
    '77088 7709e 770aa 770b6 770bc 770c0 770c2 770d4 770d6 770de 770e0 770e8 770ec 770f6 770f8 77114 77138 7714e 77158 7715c 77162 7716a 77170 77174 '
    '7717e 77186 7718c 77196 7719e 771a6 771aa 771b0 771ba 771ca 771ce 771d8 771dc 771e6 771ec 77206 7720c 7722a 77252 77258 7725e 77264 77268 7726e '
    '77278 7727c 77282 77284 77298 bc404 bc412 bc418 bc42a bc452 bc464 bc46a bc470 bc474 bc47a bc93c bc96c bc972 bc978 bc97e bc98e bc998 bc99e bc9a2 '
    'bc9ac bc9b2 bc9ba bc9c2 bc9c8 bc9d0 bc9d8 bc9de bc9e0 bca08 bca0e bca14 bca1a bca1e bca2a c5370 c5388 c538e c53a2 c53b6 c53ba c53be c53e6 c53ec '
    'c53f6 c53fc c5400 c5406 c540c c5412 c5416 c542a c5430 c561a c5648 c564e c5658 c565e c5662 c5668 c566e c5676 c567c c5682 c5686 c568e c5694 c579e '
    'd0fec d0ff2 d0ff4 d0ffc d1000 d1022 d1024 d1028 d1036 d1048 d104c d105e d106e d107c d108a d1096 d1098 d109e d10a2 d10a6 d10ac d10ae d10b4 d10ba '
    'd10bc ea69c ea6b0 ea6b8 ea6bc ea6cc ea6d0 ea6ea ea6fc ea70a ea85a ea860 ea86e ea872 ea878 ea880 ea89a ea89e ea8a4 ea8ae ea8c8 ea8d2 ea8dc ea8e2 '
    'ea8e8 ea8f6 ea8fc ea900 ea906').split()]
CONSUMERS = (0x70e12, 0x7704a, 0x77264, 0xbc470, 0xbca1a, 0xea8fc, 0x7705e, 0x77158, 0x77278, 0x770bc, 0x77170, 0x771ca, 0xc5412, 0xc5682, 0xea6b8,
             0xea6cc, 0xea86e)
CLEAR_SET = (0xea70a, 0xea8e8)          # ANDI.B #fe,CCR (+ RTS / + BCLR; BNE): known C Clear
SET_SET = (0xea6fc, 0x771d8)            # ORI.B #1,CCR (+ RTS): known C Set
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes a C in this unit
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = {(0x77192, 0x7719e)}   # LEA 772a0(PC),A0; MOVE.L A0,D0; BEQ.W 7719e: A0 is the constant 772a0
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x70e0c, 0x70e12), (0x77044, 0x7704a), (0x7725e, 0x77264), (0xbc46a, 0xbc470), (0xbca14, 0xbca1a), (0xea8f6, 0xea8fc), (0xea8e8, 0xea8fc),
          (0x77054, 0x7705e), (0x7714e, 0x77158), (0x7726e, 0x77278), (0x770b6, 0x770bc), (0x7716a, 0x77170), (0x771ba, 0x771ca), (0xc540c, 0xc5412),
          (0xc567c, 0xc5682), (0xea6b0, 0xea6b8), (0xea6bc, 0xea6cc), (0xea860, 0xea86e))
PASS_CHAINS = ()
TABLE_ENTRIES = (0xea880, 0xea8ae)      # WORD 76(A6): the index into the LONG tables ea712 / ea722
# callbacks and installed values (node callbacks); the callee entries
NODE_ENTRIES = (0xc5370, 0xc53ec, 0xc564e, 0x76ff2, 0x7703e, 0x7706a, 0x77138, 0x77206, 0x77258, 0xea85a, 0xea8d2, 0x70d92, 0x70dfc, 0xbc93c, 0xbc972,
                0xbc9e0, 0xbca0e, 0xbc404, 0xbc464)
CALLEES = (0xd0fec, 0xd1028, 0xd108a, 0xd10b4, 0xea69c, 0x77284, 0xc579e)
# values a direct entry pops (below the return LONG at A7), lowest address first: ('L'|'W', kind) with kind node / any / small
_W = (('W', 'any'),)
_LL = (('L', 'any'), ('L', 'any'))
STACK = {0x770c0: _W, 0x770c2: _W, 0x770d4: _W, 0x770d6: _W,
         0xd0ff2: (('L', 'any'),), 0xd0ff4: (('L', 'any'),), 0xd0ffc: (('L', 'any'),), 0xd1000: (('L', 'any'),),
         0xd1036: (('W', 'any'), ('W', 'any')), 0xd105e: _LL, 0xd106e: _LL, 0xd107c: _LL,
         0xd1096: _LL, 0xd1098: _LL, 0xd109e: _LL, 0xd10a2: _LL, 0xd10a6: _LL, 0xd10ac: _LL, 0xd10ae: _LL,
         0xea6bc: _W, 0xea6d0: _W, 0xea6ea: (('L', 'any'), ('L', 'any'), ('L', 'node'), ('W', 'any')), 0xea6fc: _W, 0xea70a: _W}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22)   # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x20, 0x37, 0x38, 0x39, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x3f, 0x40, 0x41, 0x7f, 0x80, 0xff, 0x100, 0x1001, 0x2000, 0x7fff, 0x8000, 0x8001, 0xe000, 0xfff0, 0xfffe,
      0xffff)
VL = (0, 1, 2, 0x10, 0x7fff, 0x8000, 0xffff, 0x10000, 0x10001, 0x30000, 0x7fffffff, 0x80000000, 0xfff00000, 0xffff0000, 0xffffac60, 0xffffffff,
      0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {}                        # no computed jump in this unit (ea880 / ea8ae read a LONG table and pass it to 49f8c)

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
        # the pointer the unit follows: LONG c(A6) (parent: WORD 42, BYTE 62 / 63 of bc97e..bc9c8)
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        if entry in TABLE_ENTRIES or rng.random() < 0.5:
            writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 1, 2, 3, 3, 0x2000, 0xe000))))
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            if reg == 6 and disp == 0x76 and entry in TABLE_ENTRIES:
                continue
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # the BYTEs 5e51 / 5e50 (A5) of ea8d2 / ea8e8
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5e51) & 0xffff, 1, rng.choice((0, 0x80, 0x7f, 0xff))))
            writes.append(((a5 + 0x5e50) & 0xffff, 1, rng.choice((0, 0x80, 0x7f, 0xff))))
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
    require(len(STARTS) == 197 and len(STARTS_SET) == 197, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in (0x772a0, 0xea712):
        require(unit_of(t) is None and not mine(t), ('data / stop PC must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr3_block', ('start is not routed to fr3', hex(s), unit_of(s)))
    rng = random.Random(0xF43A)
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
            # a statically impossible branch (77192 -> 7719e) and a consumer successor (any entry -> consumer, e.g. ea8e8 -> ea8fc: covered by the chain fixtures) are not block-row outcomes
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
    sys.stderr.write('fr3 spec: %d fixtures, visited %d/197, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out

def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr3: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr3: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts

def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries, sign / zero extension, the negative WORD index of ea880 / ea8ae, MULU / MULS / DIVU operands with nonzero upper WORDs, the popped
    registers, the A5 RAM mirror, bit combinations).  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry in (0x70d92,):
        h += word(0x9c, (0, 1, 0x8000))
    if entry in (0x70dfc, 0xc53ec, 0xc564e):
        h += byte(0x15, (0, 0x7f, 0x80, 0xff))
    if entry in (0x770c2,):
        h += [dict(a6off=[(0x42, 2, b), (0x15, 1, f)], a0off=[(0x42, 2, a)]) for a, b in ((0x10, 0), (0, 0x10), (0x8000, 0), (0x7fff, 0xffff)) for f in (0, 1)]
    if entry in (0x770d4, 0x770f6):
        h += regs('d0', (0, 1, 0x8000, 0x12340040))
    if entry == 0x770d6:
        h += [dict(regs=dict(d0=d), stack=[(2, s)]) for d, s in ((0x12340040, 0x0040), (0x12340041, 0x0040), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0))]
    if entry == 0x770e0:
        h += regs('d0', (0x3f, 0x40, 0x41, 0x8000, 0x7fff, 0xffff, 0x1234003f))
    if entry == 0x770ec:
        h += byte(0x15, (0, 1, 0xfe))
    if entry == 0x770f8:
        h += [dict(a0off=[(0x46, 2, a)], a6off=[(0x46, 2, b), (0x7a, 2, t)], regs=dict(d1=0x12345678, d3=0x9abc0000)) for a, b, t in ((0, 0x10, 5), (0xfff0, 0, 0x8000), (0x7ff8, 0x8000, 1))]
    if entry == 0x77114:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, d2=0xffffac60), a6off=[(0x15, 1, f), (0x89, 1, 0xff)]) for f in (0, 1, 0xff)]
    if entry == 0x77138:
        h += [dict(a6off=[(0x7e, 4, a), (0x36, 4, b), (0x82, 4, c), (0x3a, 4, d)]) for a, b, c, d in ((0, 0x7fffffff, 0xffffac60, 0x80000000), (1, 0xffffffff, 0x10000, 0xffff0000))]
    if entry in (0x77162, 0x7717e):
        h += byte(0x8a, (0, 1, 0xff))
    if entry == 0x77174:
        h += byte(0x15, (0, 0x20, 0xdf, 0xff))
    if entry == 0x7719e:
        h += regs('d0', (0, 1, 0x10000, 0xffff0000, 0x12340000))
    if entry == 0x771b0:
        h += byte(0x89, (0, 0x37, 0x38, 0x39, 0xff))
    if entry == 0x77284:
        h += [dict(a6off=[(0x36, 4, a), (0x3a, 4, b)]) for a, b in ((0x80000000, 0x7fffffff), (0xfff00000, 0x000fffff), (0x1000, 0xffffefff))]
    if entry == 0x77298:
        h += regs('d0', (0x123456ff, 0x80, 0x7, 0xfffffff8))
    if entry in (0x7709e, 0xbca1e, 0x77114):
        h += byte(0x15, (0, 1, 8, 0xf7, 0xfe, 0xff))
    if entry in (0xbc404,):
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0))]
    if entry == 0xbc93c:
        h += [dict(regs=dict(d0=0x12345678))]
    if entry == 0xbc97e:
        h += [dict(parent=[(0x42, 2, a)], a6off=[(0x42, 2, b)]) for a, b in ((0x10, 0x10), (0x0f, 0x10), (0x8000, 0x7fff), (0x7fff, 0x8000))]
    if entry in (0xbc98e, 0xbc9a2):
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry in (0xbc9b2, 0xbc9c8):
        h += [dict(a0off=[(0x63, 1, v), (0x62, 1, v)]) for v in (0, 1, 0x80)]
    if entry in (0xbc9ba, 0xbc9d0):
        h += word(0x76, (0, 1, 0x8000, 0xffff))
    if entry == 0xc538e:
        h += word(0x76, (0, 1, 0x8000, 0xffff))
    if entry == 0xc53a2:
        h += [dict(regs=dict(d0=d), a6off=[(0x2e, 2, a), (0x7a, 2, b)]) for d in (0x12340001, 0x8000, 0x7fff, 0xffff) for a, b in ((0x10, 0x10), (0x11, 0x10), (0x8000, 0x7fff))]
    if entry == 0xc53b6:
        h += long_(0x86, (0, 1, 0x80000000, 0xffffff00))
    if entry in (0xc5416,):
        h += byte(0x61, (0, 0x7f, 0x80, 0xff))
    if entry == 0xc566e:
        h += word(0x82, (0, 1, 0x8000))
    if entry == 0xc561a:
        h += word(0x7e, (0, 0x8000, 0xffff))
    if entry == 0xd0fec:
        h += regs('d2', (0, 1, 0x7fffffff, 0x80000000, 0xffffac60, 0xffffffff))
    if entry == 0xd0ff2:
        h += regs('d2', (0x80000000, 0xffffffff, 1))
    if entry == 0xd0ff4:
        h += regs('d3', (0, 1, 2, 3, 0x7fff, 0x8000, 0xffff, 0x12340001, 0x12340002))
    if entry == 0xd1000:
        h += [dict(regs=dict(d0=a, d1=b, d2=c, d3=d)) for a, b, c, d in ((0x12348000, 0xabcd7fff, 0x5555ac60, 0x77770002), (0x7fff, 0xffff, 0xffff0001, 0x7fff),
                                                                       (0xffff, 0x8000, 0x00010001, 3), (0x1234, 0x5678, 0x89abcdef, 0x8000), (0, 0, 0, 1),
                                                                       (0x00010000, 0xffff0000, 0x0000ffff, 0x0001ffff))]
        h += [dict(regs=dict(d3=d), stack=[(4, s)]) for d, s in ((2, 0x80000000), (5, 0x7fffffff))]
    if entry in (0xd1022, 0xd1024):
        h += [dict(regs=dict(d1=a, d3=b)) for a, b in ((0, 1), (0x80000000, 0x7fffffff), (0x12345678, 0x80000000))]
    if entry == 0xd1028:
        h += [dict(regs=dict(d0=a, d1=b, d3=c)) for a, b, c in ((0x12348000, 0xabcd7fff, 0x55555580), (0, 0xffffffff, 0x7f), (0x7fff, 0x8000, 0xff))]
    if entry == 0xd1036:
        h += [dict(regs=dict(d0=a, d1=b), stack=[(2, x), (2, y)]) for a, b, x, y in ((0x80000000, 0x7fffffff, 0x8000, 0x7fff), (0x12345678, 0xffffff00, 0, 0xffff),
                                                                                   (0x100, 0xffffff7f, 1, 0x8000))]
    if entry == 0xd104c:
        h += [dict(regs=dict(d2=a, d3=b, d0=c, d1=d)) for a, b, c, d in ((0x12348000, 0xabcd7fff, 0x10000, 0x7fff), (0xffff, 0x1, 0xffffffff, 0x8000), (0x7fff, 0x8000, 1, 0))]
    if entry in (0xd105e, 0xd106e):
        h += [dict(regs=dict(d7=a, d1=b, d2=c, d3=d, d0=e)) for a, b, c, d, e in ((0x80000001, 0x8000, 0x7fff, 0x12345678, 0x10000), (0x7fffffff, 0xffff, 0x8000, 0xffffffff, 3),
                                                                               (1, 0x12347fff, 0xabcd8000, 0x80000000, 0xffff))]
    if entry == 0xd107c:
        h += [dict(regs=dict(d4=0x12345678, d7=0x9abcdef0), stack=[(4, a), (4, b)]) for a, b in ((0x00ffffff, 0xff000001), (0x80000000, 0x7fffffff))]
    if entry == 0xd108a:
        h += [dict(regs=dict(d0=a, d7=b, d1=c)) for a, b, c in ((0x80000000, 0x7fffffff, 0x12345600), (0x00010000, 0x00050000, 0x123456ff), (0x10003, 0x80000000, 0),
                                                              (0xffff0002, 0xfffffffe, 0x80), (3, 0x100, 0xff))]
    if entry in (0xd1096, 0xd1098, 0xd109e):
        h += [dict(regs=dict(d0=a, d7=b, d1=c)) for a, b, c in ((0x80000000, 0x80000000, 0x123456ff), (1, 0x7fffffff, 0x12345600), (0xffffffff, 0xffffffff, 0x80))]
    if entry in (0xd10a6, 0xd10ac):
        h += [dict(regs=dict(d1=c, d7=b)) for b, c in ((5, 0xffffff00), (5, 0x12345601), (0x80000000, 0xff))]
    if entry in (0xd10b4, 0xd10bc):
        h += [dict(regs=dict(d0=a, d7=b, d6=0x12345678)) for a, b in ((1, 0xffffffff), (3, 0x12345678), (0xffff, 0xfffeffff), (0x10003, 0x00030005), (0x7fff, 0x80000000), (0x12340002, 0x55555555))]
    if entry == 0xea69c:
        h += [dict(regs=dict(d2=0x12345678))]
    if entry == 0xea6b0:
        h += regs('d2', (0x12340001, 0xffff, 0x8000))
    if entry == 0xea6bc:
        h += [dict(a6off=[(0x42, 4, a), (0x46, 4, b)], regs=dict(a0=0x12345678, d7=0xffffffff)) for a, b in ((0x80000000, 0x7fffffff), (0x100000, 0x2000000))]
    if entry == 0xea6d0:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0, a0=0x10e400))]
    if entry == 0xea6ea:
        h += [dict(regs=dict(a0=0x10e400, a1=0x10e800), stack=[(4, 0x11112222), (4, 0x33334444), (4, 0x10e600), (2, 0x8001)])]
    if entry == 0xea6fc:
        h += [dict(regs=dict(a0=0x10e42e), stack=[(2, v)]) for v in (0x8001, 0x7fff)]
        h += [dict(regs=dict(a0=0x1fff00), stack=[(2, 0x1234)])]              # LEA -2e(A0) in the upper RAM mirror (a zero-extended ffd2 leaves RAM)
    if entry == 0xea70a:
        h += [dict(stack=[(2, 0x1234)])]
    if entry == 0xea860:
        h += word(0x32, (0, 0x7fff, 0xffff))
    if entry in (0xea880, 0xea8ae):
        h += word(0x76, (0, 1, 2, 3))
    if entry == 0xea8a4:
        h += regs('d1', (0x12348001, 0xffffffff, 0))
    if entry == 0xea8c8:
        h += word(0x32, (0, 0x8000, 1))
    if entry in (0xea8d2, 0xea8e8):
        h += [dict(a5off=[(0x5e51, 1, v), (0x5e50, 1, w)]) for v, w in ((0, 0x80), (0x80, 0), (0x7f, 0xff), (0xff, 0x7f))]
        h += [dict(regs=dict(a5=0x1f8000), writes=[(0xde51, 1, v), (0xde50, 1, v)]) for v in (0x80, 0x01)]   # A5 in the upper RAM mirror: 5e51(A5) = 1fde51 = 10de51
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x5e, 0x61, 0x8a)] + [(6, off, 2) for off in (0x2e, 0x32, 0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in (0x70e0c, 0x77044, 0x7725e, 0xbc46a, 0xbca14, 0xea8f6) and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry == 0xea8e8 and t % 2:
                hint = dict(a5off=[(0x5e50, 1, 0x80)])                                         # BCLR old bit 7 set -> ea8fc with the Clear of the ANDI
            elif entry == 0x7716a and t % 3 == 1:
                hint = dict(a5off=[(0x5430, 2, 0xffff)])                                       # 1abda: WORD 5430(A5) = ffff -> ANDI Clear -> ea70a
            elif entry == 0xea6b0 and t % 2:
                hint = dict(a5off=[(0x5430, 2, rng.choice((0xffff, 0, 0x100)))])               # 1abda: CMPI.W #ffff,D1
            elif entry == 0x771ba and t % 3 == 1:
                hint = dict(writes=[(0x0bf4 + 0x10, 4, 0)])
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
        if entry == 0xea8e8:
            missing -= set([0xea900])                                                  # ea8e8 always sets the Clear itself: ea8fc -> ea900 (Set) is chain-ea8f6's
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
            hint = dict(a6off=[(0x9c, 2, t % 2), (0x76, 2, (0, 1, 2, 3)[(t // 2) % 4]), (0x15, 1, (0, 1, 0x80, 0x81)[(t // 8) % 4]), (0x8a, 1, (0, 0xff)[(t // 4) % 2])])
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr3 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0xc5371), 'unaligned animation machine PC', 0xc5371)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr3 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    zero = 'objects fr3 DIVU zero divisor'
    # odd node: TST.W 9c(A6) of 70d92 (read), MOVE.L #0,64(A6) of 70dee (write); odd stack (770d6 MOVE.W (A7)+,D2)
    err('70d92-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70d92), odd_word, 0x70d92, stop=0x70d9a)
    err('70dee-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70dee), odd_write, 0x70dee, stop=0x70dfc)
    err('770d6-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x770d6), odd_word, 0x770d6, stop=0x770de)
    # DIVU zero divisors: d1000 with D3.W = 0, d10bc with D0 = 10000 (D0 != 0, D0.W = 0)
    err('d1000-divu-zero', U.with_host_writes(st, [((a7 - 4) & 0xffff, 4, 0x12345678)], regs=dict(d3=0x12340000, a7=a7 - 4), pc=0xd1000), zero, 0xd1000, stop=0xd1022)
    err('d10bc-divu-zero', U.with_host_writes(st, regs=dict(d0=0x10000, d7=0x12345678), pc=0xd10bc), zero, 0xd10bc)
    # failures after executed blocks:
    #   d10b4 (D0 = 10000 != 0) -> d10bc DIVU with D0.W = 0
    err('d10b4-then-d10bc', U.with_host_writes(st, regs=dict(d0=0x10000), pc=0xd10b4), zero, 0xd10bc)
    #   d0ff4 (D3.W = 0 < 2) -> d0ffc MOVE.W #2,D3 -> d1000 MOVE.L (A7)+,D2 at an odd A7
    err('d0ff4-then-d1000', U.with_host_writes(st, regs=dict(d3=0, a7=a7 + 1), pc=0xd0ff4), odd_word, 0xd1000, stop=0xd1022)
    #   bc9b2 (BYTE 63(A0) = 0) -> bc9c8 (BYTE 62(A0) != 0) -> bc9de RTS at an odd A7
    nd = base.state['regs']['a6']
    err('bc9b2-then-bc9de', U.with_host_writes(st, [((nd + 0x63) & 0xffff, 1, 0), ((nd + 0x62) & 0xffff, 1, 1)], regs=dict(a0=nd, a7=a7 + 1), pc=0xbc9b2), odd_word, 0xbc9de)
    #   7719e (D0.W != 0) -> 771e6 JSR 8ff4 at an odd A7
    err('7719e-then-771e6', U.with_host_writes(st, regs=dict(d0=1, a7=a7 + 1), pc=0x7719e), odd_word, 0x771e6, stop=0x8ff4)
    #   770e0 (D0.W = 40) -> 770ec (BYTE 15 bit 0 set) -> 770f8 MOVE.W 46(A0),D1 at an odd A0
    err('770e0-then-770f8', U.with_host_writes(st, [((nd + 0x15) & 0xffff, 1, 1)], regs=dict(d0=0x40, a0=nd + 1), pc=0x770e0), odd_word, 0x770f8, stop=0xd0fec)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xd1000, 0x770c2, 0xc53a2, 0xd1036)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
