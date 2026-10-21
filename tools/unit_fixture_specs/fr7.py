"""V1 fixture spec of the animation-machine unit FR7 (engine/src/animation_machine_objects_fr7.cpp, 205 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr7-contract.md): the C-gated area-D roots after FR6 -- the hit test 4ad6c (BSR from the
64 N08 candidate blocks) with the damage part 4abc0 and the ground search 4c0f0, the tail e8b7e / e8b80 of the C helper e8b5a, the object cde42
(28ae child of cddee; install cded2), the table handler 36118, the objects d2776 d2782 d278e d279a with their tail d2f90 (install d3062), the object
cdd2e with cc5e8 / cc958, and the object 3ad48 (2986 child of B2E 3ac2c; install 3add4) with the sound helper 4356e.  No computed jump, no TRAP.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR6) with declared host edits.  This
code runs natively only after the first C stop of its IO runs (C-gated): besides the declared worlds the 'natural' family takes the frame-start states
of the IO native observation (artifacts/animation_machine_io_native/states, observe_animation_machine_io.read_pack) in which a node holds one of the
unit's callbacks, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the sentinel return
LONG, PC = the callback; D0-D7 / A0-A4 = the frame-start values).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 8 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node or the
            declared attack record ATK (A0), LONG 56(A2) := the declared hit record HIT (or 0 / a natural node) with its multiplier table MULT, LONG
            5e26(A5) := the declared pad record PAD, LONG 3e(A6) / 92(A6) := a natural node (or ROM 3b73e), the node / A2 / A5 fields the reachable
            blocks read, the stack values the entered block pops, PC := the block start).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 1ab80 -> 3ae78 (3ae6e) / d308e (d3084), 46d72 -> 4c128 (4c112) / 4c182 (4c16c), 49fc6
            -> cdd3c (cdd36) / cdede (cded8) / d3080 (d3072), 497a6 -> cde9c (cde96).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 8 consumers, odd node / stack / pointer, failures after executed
            blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is
            even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR6 specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR6)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x36118, 0x3614a), (0x3ad48, 0x3ae84), (0x4356e, 0x4358c), (0x4abc0, 0x4ae4a), (0x4c0f0, 0x4c1de), (0xcc5e2, 0xcc600), (0xcc958, 0xcca44),
          (0xcdd2e, 0xcdd86), (0xcde42, 0xcde6e), (0xcde96, 0xcdeea), (0xd2776, 0xd27a6), (0xd2f90, 0xd309a), (0xe8b7e, 0xe8c0e)]
STARTS = sorted([int(x, 16) for x in (
    '36118 3611e 36126 36128 3613a '
    '3ad48 3ad60 3ad78 3ad86 3ad98 3adae 3adb8 3adba 3adc6 3add4 3adec 3adf6 3adfe 3ae04 3ae12 3ae18 3ae68 3ae6e 3ae78 3ae7c 3ae82 '
    '4356e 43580 4358a '
    '4abc0 4abca 4abde 4abe6 4abf2 4abf6 4abfc 4ac00 4ac06 4ac0a 4ac10 4ac18 4ac1e 4ac2a 4ac36 4ac3a 4ac42 4ac4a 4ac56 4acb4 4acda 4ace4 4acee 4acfa '
    '4ad02 4ad0a 4ad12 4ad18 4ad22 4ad32 4ad36 4ad38 4ad42 4ad4a 4ad66 4ad6a 4ad6c 4ad78 4ad7c 4ad82 4ad8e 4ad94 4ada0 4ada4 4adb6 4adba 4adc4 4add4 '
    '4add8 4ade8 4adfa 4adfe 4ae0e 4ae2e 4ae32 4ae3a 4ae48 '
    '4c0f0 4c102 4c108 4c112 4c128 4c12c 4c132 4c13a 4c146 4c14a 4c150 4c156 4c15c 4c162 4c16c 4c182 4c186 4c18c 4c194 4c1a0 4c1a4 4c1aa 4c1b0 4c1b6 '
    '4c1be 4c1d2 4c1d6 '
    'cc5e2 cc5e8 cc5f6 cc5fe cc958 cc962 cc976 cc980 cc986 cc990 cc996 cc9a0 cc9ac cc9b8 cc9bc cc9e8 cc9f2 cc9fa cca00 cca04 cca0a cca12 cca18 cca1c '
    'cca2c cca38 '
    'cdd2e cdd32 cdd36 cdd3c cdd40 cdd46 cdd50 cdd58 cdd5e cdd68 cdd6c cdd70 cdd78 cdd7e cdd84 cde42 cde6a cde96 cde9c cdea0 cdeae cdeb2 cdec0 cded2 '
    'cded8 cdede cdee2 cdee8 '
    'd2776 d2782 d278e d279a d2f90 d2f9a d2fd2 d2fd6 d2ff4 d3008 d300a d3014 d302c d3032 d303e d3046 d3062 d3068 d3072 d3080 d3084 d308e d3092 d3094 '
    'e8b7e e8b80 e8b8a e8b92 e8ba0 e8bbe e8bc2 e8bd0 e8bd6 e8bea e8bf0 e8bfa e8c00 e8c04').split()])
CONSUMERS = (0x3ae78, 0xd308e, 0x4c128, 0x4c182, 0xcdd3c, 0xcdede, 0xd3080, 0xcde9c)
CLEAR_SET = (0x4c1b6,)                  # ADDQ.W #6,A7; ANDI.B #fe,CCR; RTS
SET_SET = (0x4c1d6,)                    # ADDQ.W #6,A7; ORI.B #1,CCR; RTS
CLEAR_AFTER = ()
SCC_VALUE = {}                          # no SCC / SCS consumer in this unit
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes a C in this unit
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
TRAPS = ()                              # no TRAP site in this unit
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x3ae6e, 0x3ae78), (0xd3084, 0xd308e), (0x4c112, 0x4c128), (0x4c16c, 0x4c182), (0xcdd36, 0xcdd3c), (0xcded8, 0xcdede), (0xd3072, 0xd3080),
          (0xcde96, 0xcde9c))
PASS_CHAINS = ()
TABLE_ENTRIES = ()
# callbacks and installed values (node callbacks); the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0x3ad48, 0x3add4, 0xcde42, 0xcded2, 0xcdd2e, 0xd2776, 0xd2782, 0xd278e, 0xd279a, 0xd3062)
CALLEES = (0x4ad6c, 0x4abc0, 0x4c0f0, 0xcc5e8, 0xcc958, 0x4356e, 0x36118, 0xd2f90, 0xe8b7e, 0xe8b80)
# values a direct entry pops or reads below the return LONG at A7, lowest address first: ('L'|'W', kind) with kind node / any / small / atk / drec
FRAME6 = (('L', 'any'), ('W', 'any'))  # 4c0f0: LONG (A7) and the WORD counter 4(A7) below the return LONG
STACK = {0x3613a: (('L', 'node'),), 0xd2f9a: (('L', 'drec'),), 0x3adec: (('L', 'any'), ('L', 'any')), 0x3adf6: (('L', 'any'), ('L', 'any')),
         0x3ae04: (('L', 'any'), ('L', 'any')),
         0x4acb4: (('L', 'small'), ('L', 'any'), ('L', 'any'), ('L', 'any'), ('L', 'any'), ('L', 'atk')),
         0x4ad66: tuple([('L', 'any')] * 12)}
for _pc in (0x4c102, 0x4c108, 0x4c112, 0x4c128, 0x4c12c, 0x4c132, 0x4c13a, 0x4c146, 0x4c14a, 0x4c150, 0x4c156, 0x4c15c, 0x4c162, 0x4c16c, 0x4c182,
            0x4c186, 0x4c18c, 0x4c194, 0x4c1a0, 0x4c1a4, 0x4c1aa, 0x4c1b0, 0x4c1b6, 0x4c1be, 0x4c1d2, 0x4c1d6):
    STACK[_pc] = FRAME6
for _pc in (0xe8b7e, 0xe8b80, 0xe8b8a, 0xe8b92, 0xe8ba0):
    STACK[_pc] = (('W', 'any'),)       # the WORD pushed by e8b6e (MOVE.W D0,-(A7)); TST.W (A7)+ of e8ba0 pops it
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x3e, 0x92)   # node links and pointer fields: natural or declared below
ATK = 0x10fb00                          # declared attack record (A0 of 4ad6c / 4abc0): WORD id, BYTE power, BYTE flags, WORDs 4 6 8, rectangles 12..
HIT = 0x10fc00                          # declared hit record (LONG 56(A2)): WORDs 8 a, BYTEs 10 11, LONG c (MULT or 0), rectangles 12..
MULT = 0x10fc80                         # declared multiplier WORD table (LONG c(HIT))
PAD = 0x10fd80                          # declared pad record (LONG 5e26(A5)): BYTEs 5 6 7
DREC = 0x10fd40                         # declared RAM record of d2f9a: LONG 92 value, LONG bank-table index
ROM_DREC = (0xd2652, 0xd265a, 0xd2662, 0xd266a)     # the natural records of d2776 d2782 d278e d279a
ROM_SCREEN = 0x3b73e                    # the natural A0 of 1ab80 (3ae6e); also a LONG 92(A6) value
NATURAL = (('P1', 94, 393), ('boot-demo-0', None, 435), ('boot-demo-0', None, 478), ('boot-demo-0', None, 482), ('boot-demo-0', None, 506),
           ('boot-demo-0', None, 538), ('boot-demo-0', None, 539), ('boot-demo-0', None, 545), ('boot-demo-0', None, 561), ('boot-demo-0', None, 577))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xb, 0x10, 0x1e, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xf3, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 0xa, 0xc, 0xf, 0x10, 0x1f, 0x20, 0x21, 0x50, 0x7f, 0x80, 0xe0, 0xfb, 0xfc, 0x100, 0x11f, 0x120, 0x17f, 0x180, 0x1001, 0x7fff,
      0x8000, 0x8001, 0xe0ed, 0xffe0, 0xfff3, 0xfff4, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x10, 0x800, 0x20000, 0x60000, 0x80000, 0x7fff, 0x8000, 0xffff, 0x10000, 0x7fffffff, 0x80000000, 0xffff0000, 0xfff40000,
      0xfffff000, 0xfffff001, 0xffffbbbc, 0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {}                        # no computed jump in this unit


def rects(rng, n, close):
    """A rectangle list of n LONG pairs ((offset high WORD, offset low WORD), (size high WORD, size low WORD)) and the LONG terminator (low WORD 8000).
    close: small offsets / sizes that overlap often."""
    out = []
    for k in range(n):
        if close:
            a = ((rng.choice((0, 1, 4, 0xf, 0x10, 0xfff0)) << 16) | rng.choice((0, 2, 8, 0xc, 0x10, 0xfff8)))
            b = ((rng.choice((0x8, 0x10, 0x20)) << 16) | rng.choice((0x8, 0x10, 0x20)))
        else:
            a = rng.getrandbits(32)
            if a & 0xffff == 0x8000:
                a ^= 1
            b = rng.getrandbits(32)
        out += [a, b]
    out.append((rng.getrandbits(16) << 16) | 0x8000)
    return out


def record_writes(rng, base, longs):
    return [((base + 4 * k) & 0xffff, 4, v & 0xffffffff) for k, v in enumerate(longs)]


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
            regs['d0'] = rng.choice((0, 1, 2, 3, 0x12340001, 0xffff, 0x8000))   # small WORD indices (49a84 result, record ids)
        writes = []
        regs['a0'] = ATK if rng.random() < 0.6 else self.pointer()
        regs['a1'] = rng.choice((HIT, MULT, self.pointer()))
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = PAD if rng.random() < 0.5 else self.pointer()
        sp = regs['a7']
        a2 = regs['a2']
        # the declared records: the attack record ATK (A0), the hit record HIT (LONG 56(A2)) with its multiplier table MULT, the pad record PAD (LONG
        # 5e26(A5)), the d2f9a record DREC; their rectangle lists end with a LONG whose low WORD is 8000
        close = rng.random() < 0.7
        writes += [(ATK & 0xffff, 2, rng.choice((0, 1, 2, 3, 0xffff, 0x8000))), ((ATK + 2) & 0xffff, 1, self.value(1)), ((ATK + 3) & 0xffff, 1, self.value(1))]
        for off in (4, 6, 8):
            writes.append(((ATK + off) & 0xffff, 2, rng.choice((0, 1, 0x10, 0x100, 0x7fff, 0xffff, self.value(2)))))
        writes += record_writes(rng, ATK + 0x12, rects(rng, rng.choice((1, 1, 2, 3)), close))
        writes += [((HIT + 8) & 0xffff, 2, self.value(2)), ((HIT + 0xa) & 0xffff, 2, rng.choice((0, 1, 2, 4, 7, 0x8001, self.value(2)))),
                   ((HIT + 0x10) & 0xffff, 1, rng.choice((0, 0, 1, 0x80, 0xff))), ((HIT + 0x11) & 0xffff, 1, rng.choice((0, 1, 1, 2))),
                   ((HIT + 0xc) & 0xffff, 4, rng.choice((MULT, MULT, 0)))]
        writes += record_writes(rng, HIT + 0x12, rects(rng, rng.choice((1, 1, 2, 3)), close))
        for k in range(8):
            writes.append(((MULT + 2 * k) & 0xffff, 2, rng.choice((0, 1, 0x80, 0x100, 0xffff, self.value(2)))))
        for off in (5, 6, 7):
            writes.append(((PAD + off) & 0xffff, 1, rng.choice((0, 1, 0x7f, 0x80, 0xff, 0xb, 0xb) if off == 7 else (0, 1, 0x7f, 0x80, 0xff))))
        writes += [(DREC & 0xffff, 4, rng.choice((ROM_SCREEN, self.pointer()))), ((DREC + 4) & 0xffff, 4, rng.choice((0x22, 0x25, 0, 0xffff, 0x4001)))]
        if in_ram(a2 + 0x56, 4):
            writes.append(((a2 + 0x56) & 0xffff, 4, rng.choice((HIT, HIT, HIT, 0, self.pointer()))))
        writes.append(((a5 + 0x5e26) & 0xffff, 4, rng.choice((PAD, PAD, self.pointer()))))
        writes.append(((a6 + 0x3e) & 0xffff, 4, self.pointer()))
        writes.append(((a6 + 0x92) & 0xffff, 4, rng.choice((ROM_SCREEN, self.pointer()))))
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe: BYTE 1d(A6) < 4 (>= 4 reaches the TRAP #15 8ec8)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: a2, 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if (reg == 6 and disp in POINTERS) or (reg == 2 and disp == 0x56) or (reg == 5 and disp == 0x5e26):
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # A5 fields: BYTE 5744 (4ad6c), WORDs 5af2 / 5b7c / 5b82 (4ac3a 4acee 4ad02), WORD 5492 and the frame counter WORD -7ff2(A5) = 10000e (4356e)
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5744) & 0xffff, 1, rng.choice((0, 0x7f, 0x80, 0xff))))
        for off in (0x5af2, 0x5b7c, 0x5b82):
            if rng.random() < 0.5:
                writes.append(((a5 + off) & 0xffff, 2, self.value(2)))
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5492) & 0xffff, 2, self.value(2)))
            writes.append(((a5 - 0x7ff2) & 0xffff, 2, self.value(2)))
        # stack values popped by the entered block (declared), the return LONG above them
        pops = []
        for size, kind in STACK.get(entry, ()):
            v = {'node': self.pointer(), 'small': rng.choice((0, 1, 2, 3)), 'atk': ATK, 'drec': rng.choice(ROM_DREC + (DREC, DREC)),
                 'any': self.value(4 if size == 'L' else 2)}[kind]
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
            if hint.get('atk') is not None:
                regs['a0'] = ATK
                for off, size, val in hint['atk']:
                    writes.append(((ATK + off) & 0xffff, size, val))
            if hint.get('hit') is not None:
                if in_ram(a2 + 0x56, 4):
                    writes.append(((a2 + 0x56) & 0xffff, 4, HIT))
                for off, size, val in hint['hit']:
                    writes.append(((HIT + off) & 0xffff, size, val))
            if hint.get('pad') is not None:
                writes.append(((a5 + 0x5e26) & 0xffff, 4, PAD))
                for off, size, val in hint['pad']:
                    writes.append(((PAD + off) & 0xffff, size, val))
            for off, size, val in hint.get('a2off', []):
                if in_ram(regs['a2'] + off, size):
                    writes.append(((regs['a2'] + off) & 0xffff, size, val))
            if hint.get('mirror'):
                regs['a6'] = a6 | 0xf0000                       # the node in the upper RAM mirror (1fxxxx = 10xxxx)
            if hint.get('a5_mirror'):
                regs['a5'] = a5 | 0xf0000                       # A5 in the upper RAM mirror (1f8000 = 108000)
            if hint.get('a2_mirror'):
                regs['a2'] = regs['a2'] | 0xf0000               # the target object in the upper RAM mirror
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
    require(len(STARTS) == 205 and len(STARTS_SET) == 205, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS:
        require(unit_of(t) is None and not mine(t), ('TRAP site must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr7_block', ('start is not routed to fr7', hex(s), unit_of(s)))
    for a in (ATK, HIT, MULT, PAD, DREC):
        require(unit_of(a) is None and in_ram(a, 0x40), ('declared record must be work RAM outside the stack page', hex(a)))
    rng = random.Random(0xF73A)
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
    sys.stderr.write('fr7 spec: %d fixtures (%d natural), visited %d/205, missing successors %s, unreachable outcomes %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') == 'natural'), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr7: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr7: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts

def geo(ax, ay, tx, ty, arect, trect, af=0, tf=0):
    """A hit-test world: attacker node A6 x / y (WORDs 42 / 46) and flags BYTE 15, target A2 x / y (WORDs 4a / 4e) and flags BYTE 15, one attack
    rectangle and one target rectangle (offset x, offset y, width, height; the high WORD of each LONG is x, the low WORD y)."""
    ox, oy, w, hh = arect
    tox, toy, tw, th = trect
    atk = [(0x12, 4, ((ox & 0xffff) << 16) | (oy & 0xffff)), (0x16, 4, ((w & 0xffff) << 16) | (hh & 0xffff)), (0x1a, 4, 0x00008000)]
    hit = [(0x12, 4, ((tox & 0xffff) << 16) | (toy & 0xffff)), (0x16, 4, ((tw & 0xffff) << 16) | (th & 0xffff)), (0x1a, 4, 0x00008000)]
    return dict(atk=atk, hit=hit, a6off=[(0x42, 2, ax), (0x46, 2, ay), (0x15, 1, af)], a2off=[(0x4a, 2, tx), (0x4e, 2, ty), (0x15, 1, tf)])


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries, equal-value ties at BCS / BLS / BHI / BCC / BLE / BMI / BPL, the SUBQ wraps, the ADDI carry of 4356e, the zero / sign extension of MOVEQ #0
    + MOVE.B and EXT.W, the WORD index wraps (negative indices) of 3ad60 / 4ac2a / 4ad4a / d2f9a, the MULU / MULS operands, the popped LONGs / WORD,
    the upper register bits of the WORD / BYTE operations, the node / A2 / A5 in the upper RAM mirror, flag-bit combinations and the hit-test geometry
    (overlap, touching edges, flips).  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0x3ad48, 0x3ad78, 0x3ad86, 0xcdea0, 0xcdeb2, 0xd2776, 0xd2782, 0xd278e, 0xd279a, 0xcde42, 0xd2fd6, 0xe8c00, 0x43580, 0xcc976, 0xcc986,
                 0xcca1c, 0xcca2c, 0xe8b92, 0x36128, 0xd2f90, 0x4c0f0, 0x4c1be):
        h += [dict(regs=dict(up))]
    # ---- 3ad48 object
    if entry == 0x3ad60:
        h += regs('d0', (0, 1, 2, 0x12340002, 0xffff, 0x4000))
    if entry == 0x3ad98:
        h += regs('d0', (0x1234ffff, 0xffe0, 0x1f, 0, 0xffffffb0))
    if entry == 0x3adae:
        h += [dict(a6off=[(0x15, 1, v)], regs=dict(d0=d, d1=0x9abcdef0)) for v, d in ((0, 1), (1, 1), (0xff, 0x80000000), (0xfe, 0))]
    if entry == 0x3adba:
        h += regs('d0', (0x80000000, 0xfffa0000))
    if entry == 0x3adc6:
        h += regs('d0', (0x123456ff, 0xfd, 2, 0))
    if entry == 0x3add4:
        h += long_(0x36, (0x80000000, 0x7fffffff, 0xffffffff, 0xf, 0x10, 0xfffffff0)) + [dict(mirror=True, a6off=[(0x36, 4, 0x100), (0x3a, 4, 0x80000000)])]
    if entry == 0x3adf6:
        h += byte(0xb6, (0, 1, 0x80, 0x81, 0xff))
    if entry in (0x3adec, 0x3ae04):
        h += [dict(a6off=[(0x15, 1, v)], stack=[(4, a), (4, b)]) for v, a, b in ((0x20, 0x12345678, 0x9abcdef0), (0, 1, 2), (0xdf, 0x80000000, 0x7fffffff),
                                                                                   (0xa0, 0, 0xffffffff))]
    if entry == 0x3ae18:
        h += [dict(regs=dict(d0=a, d2=b, d3=c, d4=d)) for a, b, c, d in ((0x1c, 0x7fffffff, 0x80000000, 0xff00), (0, 0x10000, 0xffff0000, 0x1234),
                                                                         (0x12345614, 0xffffffff, 1, 0xffff), (0x8, 0x1234567, 0x89abcdef, 0x8000),
                                                                         (0xff, 0x7f00, 0x8100, 0x00ff), (0xc, 0x01000000, 0xff000000, 0x7f00))]
    if entry == 0x4356e:
        h += [dict(regs=dict(up), a5off=[(0x5492, 2, a), (-0x7ff2, 2, b)]) for a, b in ((0, 0xc), (0, 0xd), (0xfff4, 0), (0xfff3, 0), (5, 5), (0x8000, 0x7ff4))]
        h += [dict(a5_mirror=True, a5off=[(0x5492, 2, 0), (-0x7ff2, 2, 0xc)])]
    # ---- 4abc0 damage
    if entry == 0x4abc0:
        h += [dict(regs=dict(a0=0)), dict(regs=dict(a0=0x80000000)), dict(atk=[])]
    if entry == 0x4abca:
        h += [dict(atk=[(0, 2, 1)], hit=[(0x11, 1, v), (8, 2, 0x8000)]) for v in (0, 1, 2, 0xff)]
    if entry == 0x4abde:
        h += [dict(a2off=[(0x5e, 1, v)]) for v in (0, 1, 0x80)]
    if entry == 0x4abe6:
        h += [dict(regs=dict(d2=0x12345678, d3=0x9abcdef0), atk=[(4, 2, 1), (6, 2, 0x10), (8, 2, 0x100)], hit=[(0xa, 2, v)]) for v in
              (0, 1, 2, 3, 4, 5, 6, 7, 0x8001, 0xfffe)]
    if entry in (0x4abf2, 0x4abfc, 0x4ac06):
        h += [dict(regs=dict(d2=0x1234ffff, d3=0x55660003), atk=[(4, 2, 1), (6, 2, 0xffff), (8, 2, 0x8000)])]
    if entry in (0x4abf6, 0x4ac00):
        h += regs('d3', (0x12340001, 0x12340002, 0xffff, 0x8000))
    if entry == 0x4ac0a:
        h += regs('d2', (0x10000, 0, 1, 0x8000))
    if entry in (0x4ac10, 0x4ac18):
        h += [dict(regs=dict(a1=HIT, d2=0x12345678), hit=[(0x10, 1, v)]) for v in (0, 0x80, 0xff, 1)]
    if entry == 0x4ac1e:
        h += [dict(regs=dict(a1=HIT), hit=[(0xc, 4, v)]) for v in (0, MULT, 0x80000000)]
    if entry == 0x4ac2a:
        h += [dict(regs=dict(a1=MULT, d0=d, d3=0x9abcdef0), writes=[(MULT & 0xffff, 2, 0x100), ((MULT + 2) & 0xffff, 2, 0), ((MULT - 2) & 0xffff, 2, 5)])
              for d in (0, 1, 0xffff, 0x8000, 0x12340000, 0x12340001)]
        # a ROM table base: (A1,D3.W) with D3.W = fffe/0000.. sign-extends; in work RAM the 64 KiB mirror hides a zero-extended index (mutant 4ac2a-unsigned)
        h += [dict(regs=dict(a1=0x44200, d0=d, d3=0x9abcdef0)) for d in (0xffff, 0xffc0, 0xff90)]  # inside the synthetic 4411e..4439e window: signed index -2/-80/-e0 stays in it
    if entry == 0x4ac36:
        h += [dict(regs=dict(d2=a, d3=b)) for a, b in ((0x1234ffff, 0x5678ffff), (0x8000, 2), (0, 5), (0xffff0100, 0x0100), (0x7fff, 0x7fff), (1, 0xff))]
    if entry == 0x4ac3a:
        h += [dict(regs=dict(d1=a), a5off=[(0x5af2, 2, b)]) for a, b in ((0x12340005, 5), (4, 5), (6, 5), (0x8000, 0x7fff), (0xffff, 0))]
    if entry == 0x4ac4a:
        h += [dict(atk=[(2, 1, a)], a2off=[(0x5e, 1, b)], regs=dict(d3=0x12345678)) for a, b in ((5, 5), (4, 5), (6, 5), (0x80, 0x7f), (0, 0xff))]
    if entry == 0x4ac56:
        h += [dict(regs=dict(up), a2off=[(0x42, 4, a), (0x46, 4, b), (0x4a, 4, c), (0x4e, 4, d)], a6off=[(0x42, 4, e), (0x46, 4, f), (0x4a, 4, g), (0x4e, 4, k)])
              for a, b, c, d, e, f, g, k in ((0x100000, 0x200000, 0, 0, 0x100000, 0x200000, 0, 0), (0x80000000, 0x7fffffff, 1, 0xffffffff, 0, 0, 0x7fffffff, 0x80000000),
                                             (0x7fff0000, 0x80000000, 0x10000, 0, 0x80000000, 0x7fff0000, 0xffff0000, 1), (0, 0, 0, 0, 0x8000, 0x8000, 0x7fff, 0x7fff))]
    if entry == 0x4acb4:
        h += [dict(a6off=[(0x60, 1, a)], a2off=[(0x60, 1, b), (0x5f, 1, 0x40)], stack=[(4, d0), (4, 0x9abcdef0), (4, 0x11223344), (4, 0x55667788),
                                                                                         (4, 0x99aabbcc), (4, ATK)], regs=dict(d0=e))
              for a, b, d0, e in ((0xff, 0xff, 1, 0x12345678), (0, 0, 0, 0xfffffff0), (3, 0xc, 0x80000000, 0x000000ff), (0xfc, 0xf3, 2, 0x7ffffff0),
                                 (4, 0, 1, 0x12345678), (7, 0x03, 3, 0x12345678))]  # BYTE 60(A6) bit 2 set with BYTE 60(A2) bit 4 clear: ANDI.B #3 vs #7 visible (mutant 4acb4-and3; Qwen draft, main checked)
    if entry in (0x4acda, 0x4ace4):
        h += [dict(a2off=[(0x61, 1, v)]) for v in (0, 0x80, 0x40, 0xc0, 0x3f)]
    if entry == 0x4acee:
        h += [dict(regs=dict(d3=0x12345678), a2off=[(0x54, 2, a)], a5off=[(0x5b7c, 2, b)]) for a, b in ((5, 5), (4, 5), (6, 5), (0x8000, 0x7fff))]
    if entry == 0x4ad02:
        h += [dict(regs=dict(d3=a), a5off=[(0x5b82, 2, b)]) for a, b in ((0x12340005, 5), (4, 5), (6, 5), (0x7fff, 0x8000))]
    if entry in (0x4acfa, 0x4ad0a, 0x4ac42):
        h += [dict(regs=dict(up), a2_mirror=True)]
    if entry == 0x4ad12:
        h += regs('d2', (0x10000, 0, 1))
    if entry == 0x4ad18:
        h += [dict(regs=dict(d2=a, d3=0x12345678), a2off=[(0x54, 2, b)]) for a, b in ((5, 5), (5, 4), (5, 6), (0x12340000 | 0xffff, 0xfffe), (1, 0x8000))]
    if entry == 0x4ad22:
        h += [dict(atk=[(3, 1, v)], a2off=[(0x61, 1, 0)]) for v in (0, 1, 0xfe, 0xff)]
    if entry == 0x4ad38:
        h += [dict(regs=dict(d1=a, d3=0x12345678)) for a in (0x100, 1, 0, 0x80)]
    if entry == 0x4ad42:
        h += [dict(a2off=[(0x60, 1, v)]) for v in (0x80, 0x7f, 0)]
    if entry == 0x4ad4a:
        h += [dict(regs=dict(up, d0=d), a6off=[(0x60, 1, v)]) for d, v in ((0, 1), (1, 2), (0x8000, 3), (0xffff, 0), (0x4000, 1), (0x12340002, 2))]
    if entry == 0x4ad66:
        h += [dict(stack=[(4, 0x11110000 + k) for k in range(12)])]
    if entry == 0x4ad6c:
        h += [dict(regs=dict(d4=d), a5off=[(0x5744, 1, m)], a2off=[(0x5a, 1, 3), (0x5b, 1, 4)]) for d, m in ((3, 0x80), (4, 0), (4, 0x80), (0x12345603, 0xff),
                                                                                                            (3, 0x7f))]
    if entry == 0x4ad7c:
        h += [dict(regs=dict(d4=d, a1=HIT + 0x10), hit=[(0x10, 1, 0x80)]) for d in (0x80, 0x12345680, 0x7f)]
    if entry == 0x4ad82:
        h += [dict(a2off=[(0x56, 4, v)]) for v in (0, HIT, 0x80000000)]
    if entry in (0x4ad8e, 0x4ad6c, 0x4ad94, 0x4adba, 0x4adc4, 0x4abc0):
        # geometry: overlap, touching edges (x and y), each flip bit
        g = []
        for args in ((0x100, 0x100, 0x100, 0x100, (0, 0, 0x10, 0x10), (0, 0, 0x10, 0x10)),
                     (0x100, 0x100, 0x100, 0x100, (0, 0, 0x10, 0x10), (0x10, 0, 0x10, 0x10)),
                     (0x100, 0x100, 0x100, 0x100, (0, 0, 0x10, 0x10), (0xf, 0, 0x10, 0x10)),
                     (0x100, 0x100, 0x100, 0x100, (0, 0, 0x10, 0x10), (0, 0x10, 0x10, 0x10)),
                     (0x100, 0x100, 0x100, 0x100, (0, 0, 0x10, 0x10), (0, 0xf, 0x10, 0x10)),
                     (0x7ff8, 0x100, 0x8008, 0x100, (0, 0, 0x10, 0x10), (0, 0, 0x10, 0x10))):
            for af, tf in ((0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (3, 3)):
                g.append(geo(*args, af=af, tf=tf))
        if entry in (0x4ad8e, 0x4ad6c):
            h += [dict(x, regs=dict(d4=3), a5off=[(0x5744, 1, 0)], a2off=x['a2off'] + [(0x5b, 1, 3)]) for x in g]
        elif entry == 0x4abc0:
            h += g[:3]
        else:
            h += g[::6]
    if entry in (0x4add8, 0x4adfe):
        h += [dict(regs=dict(d0=0x00100010, d1=0x00100010, d2=a, d3=b), a2off=[(0x4a, 2, 0), (0x4e, 2, 0)]) for a, b in
              ((0x00100010, 0x00100010), (0x00200020, 0x00100010), (0x001f001f, 0x00100010), (0xfff0fff0, 0x00100010), (0x12340000, 0x56780000))]
    if entry in (0x4ada0, 0x4adb6, 0x4add4, 0x4adfa):
        h += [dict(regs=dict(d0=0x12348000, d1=0x56788000, d2=0x9abc7fff, d3=0xdef00001))]
    if entry == 0x4ae0e:
        h += [dict(regs=dict(d0=a, d2=b, d1=0x11112222, d3=0x33334444)) for a, b in ((0x00010001, 0xffffffff), (0x7fff7fff, 0x80008000), (0, 1), (0x00020002, 0x00030003))]
    if entry in (0x4ae32, 0x4ae3a):
        h += [dict(regs=dict(a1=HIT + 0x12, a3=ATK + 0x12), writes=[((HIT + 0x12) & 0xffff, 4, v), ((ATK + 0x12) & 0xffff, 4, w)]) for v, w in
              ((0x8000, 0x8000), (0x12348000, 0x7fff), (0x8001, 0xffff8000), (0x80000000, 0x8000))]
    # ---- 4c0f0 ground search (the 6-BYTE frame below the return LONG)
    if entry == 0x4c0f0:
        h += regs('d0', (0x12345678, 0x80000000, 0xffff))
    if entry in (0x4c108, 0x4c162):
        h += [dict(a6off=[(0x42, 2, v)]) for v in (0x20, 0x1f, 0x120, 0x11f, 0x8020, 0, 0x7fff, 0x8000, 0x801f)]  # 8000..801f: BMI (N of the CMPI) vs a signed compare differ (mutant 4c108-signed-lt; Qwen draft, main checked)
    if entry in (0x4c12c, 0x4c186):
        h += [dict(regs=dict(d6=a), stack=[(4, b), (2, 4)]) for a, b in ((5, 5), (4, 5), (6, 5), (0x80000000, 0x7fffffff), (0, 0xffffffff))]
    if entry in (0x4c132, 0x4c18c):
        h += [dict(stack=[(4, 0x12340000), (2, v)]) for v in (0, 1, 2, 0x8000, 0xffff)]
    if entry in (0x4c13a, 0x4c194):
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x42, 2, v)]) for v in (0xfff6, 0xa, 0x7ffa, 0)]
    if entry in (0x4c150, 0x4c1aa):
        h += [dict(a6off=[(0x42, 2, v)]) for v in (0, 4, 5, 0xfffb, 0x8004)]
    if entry in (0x4c112, 0x4c16c):
        h += [dict(stack=[(4, v), (2, 4)], a6off=[(0x42, 4, 0x01000000), (0x46, 4, 0x00800000)]) for v in (0, 0x00100000, 0x80000000)]
    if entry == 0x4c1be:
        h += [dict(regs=dict(d0=a), a6off=[(0x3e, 4, ATK)], atk=[(0, 2, b)]) for a, b in ((0x12340010, 0x10), (0x5, 0x8000), (0xffff, 1))]
    # ---- cc5e8 / cc958 / cdd2e
    if entry == 0xcc5e8:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x42, 2, a), (0x46, 2, b)]) for a, b in ((0x160, 0xe0), (0x15f, 0xe0), (0x15f, 0xdf), (0xffe0, 0xe0),
                                                                                             (0xffdf, 0x100), (0x8000, 0xffff))]
    if entry == 0xcc5f6:
        h += word(0x46, (0xe0, 0xdf, 0, 0xffff, 0x8000))
    if entry in (0xcc958, 0xcc996, 0xcc9e8):
        h += byte(0x15, (0, 0x80, 0x10, 0x90, 0xff, 0x7f))
    if entry == 0xcc962:
        h += [dict(a6off=[(0x7e, 4, a), (0x64, 4, b)]) for a, b in ((0x7fffffff, 0x80000000), (0, 1), (0x80000000, 0x7fffffff), (3, 0))]
    if entry in (0xcc976, 0xcc986, 0xcca0a):
        h += regs('d6', (0x20, 0x100, 0x120, 0, 0xfffffedf, 0x12340020, 0x00010000))
    if entry == 0xcc9a0:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x6e, 1, v)]) for v in (5, 4, 6, 0x85)]
    if entry == 0xcc9ac:
        h += byte(0x15, (0xff, 0x80, 0))
    if entry == 0xcc9bc:
        h += [dict(a6off=[(0x3a, 4, a), (0x7e, 4, b), (0x36, 4, c), (0x7c, 1, d)]) for a, b, c, d in ((0, 0x7fffffff, 0x80000000, 0), (0x7fffffff, 0, 0, 1),
                                                                                                  (0xfff40000, 0x1f, 0, 0x80), (0x80000000, 0x80000000, 0x7fffffff, 0))]
    if entry == 0xcc9f2:
        h += byte(0x7a, (0, 0xff, 1))
    if entry == 0xcca38:
        h += byte(0x15, (0x80, 0x7f, 0)) + [dict(mirror=True, a6off=[(0x15, 1, 0x80)])]
    if entry == 0xcdd46:
        h += byte(0x61, (0, 8, 0xf7, 0xff))
    if entry in (0xcdd50, 0xcdd70):
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x79, 1, v)]) for v in (0, 1, 2, 0x80, 0xff)]
    if entry in (0xcdd58, 0xcdd7e):
        h += regs('d0', (0x12345601, 0x12345600, 0x12345602, 0xff))
    if entry in (0xcdd5e, 0xcdd68):
        h += [dict(regs=dict(d0=0x123456ff), a6off=[(0x61, 1, 0xf7)])]
    # ---- cde42 / d2f90 / d3062
    if entry == 0xd2f9a:
        h += [dict(regs=dict(up), stack=[(4, r)]) for r in ROM_DREC] + [dict(stack=[(4, DREC)], writes=[((DREC + 4) & 0xffff, 4, v)]) for v in
                                                                       (0, 0xffff, 0x4001, 0x8000, 0x12340022)]
    if entry == 0xd2f90:
        h += [dict(regs=dict(a0=r)) for r in ROM_DREC + (DREC,)]
    if entry == 0xd2ff4:
        h += regs('d0', (0x00010001, 0xffff0000, 0x00070000, 0x12345678, 0x80000001))
    if entry == 0xd3008:
        h += regs('d0', (0x38000, 0, 0x8000))
    if entry == 0xd3014:
        h += [dict(regs=dict(d0=a), a6off=[(0x3a, 4, b)]) for a, b in ((0, 0x00fb0000), (0, 0x00fc0000), (0x00010000, 0x00fc0000), (0xffff0000, 0x80000000),
                                                                      (0x000f0000, 0x7fffffff), (0, 0x00fb8000))]
    if entry == 0xd3032:
        h += long_(0x8e, (0xfffff000, 0xfffff001, 0xffffefff, 0x7fffffff, 0x80000000, 0))
    if entry in (0xd3046, 0xd3068):
        h += byte(0x15, (0, 0x80, 0x08, 0xff)) + [dict(mirror=True, a6off=[(0x15, 1, 0)])]
    if entry == 0xd3072:
        h += [dict(a6off=[(0x8e, 4, a), (0x3a, 4, b)]) for a, b in ((0x7fffffff, 1), (0xffffbbbc, 0x80000), (0x80000000, 0x80000000))]
    if entry == 0xd3084:
        h += long_(0x92, (ROM_SCREEN, 0))
    # ---- e8b7e / e8b80 / 36118
    if entry in (0xe8b7e, 0xe8b80, 0xe8b8a):
        h += [dict(regs=dict(up, a1=HIT, a4=PAD), pad=[(4, 1, v)], writes=[(HIT & 0xffff, 2, 0x8000), ((HIT + 4) & 0xffff, 2, 0xffff)], stack=[(2, w)])
              for v, w in ((0, 0), (1, 1), (0xfe, 0x8000), (0xff, 0xffff))]
    if entry == 0xe8ba0:
        h += [dict(pad=[(5, 1, a), (6, 1, b)], stack=[(2, w)]) for a, b, w in ((0x7f, 0x80, 0), (0x80, 0x7f, 1), (0xff, 0, 0x8000), (0, 0xff, 0xffff), (1, 1, 0))]
        h += [dict(a5_mirror=True, pad=[(5, 1, 0x80), (6, 1, 0x80)], stack=[(2, 0)])]
    if entry == 0xe8bbe:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0x00800000, 0xff800000), (0, 0x00010000))]
    if entry == 0xe8bd6:
        h += [dict(regs=dict(up), pad=[(7, 1, v)]) for v in (0xb, 0xa, 0xc, 0x8b, 0)]
    if entry == 0xe8bf0:
        h += [dict(regs=dict(up, d0=a), a6off=[(0x46, 2, b)]) for a, b in ((0x12340010, 0x10), (0x10, 0x11), (0x11, 0x10), (0x8000, 0), (0, 0x8000), (0x7fff, 0xffff))]
    if entry == 0xe8bc2:
        h += [dict(regs=dict(up), mirror=True)]
    if entry == 0x3611e:
        h += regs('d0', (4, 0xfffffffb, 0x12345604, 0))
    if entry == 0x3613a:
        h += [dict(regs=dict(a0=ATK), stack=[(4, HIT)], writes=[(HIT & 0xffff, 2, 0x8000), ((HIT + 2) & 0xffff, 2, 0xffff), ((HIT + 4) & 0xffff, 2, 1)])]
    return h


def chain_hint(entry, t, rng):
    """Edits that let the real producer of a chain return both C values."""
    if entry in (0x3ae6e, 0xd3084) and t % 2:
        on = (t // 2) % 2 == 0
        return dict(a6off=[(0x42, 4, 0x00a00000 if on else 0x7fff0000), (0x46, 4, 0x00800000 if on else 0x7fff0000), (0x4a, 4, 0), (0x4e, 4, 0), (0x15, 1, 0),
                           (0x92, 4, ROM_SCREEN)])                                  # 1ab80: on screen (Clear) / off (Set)
    if entry in (0xcdd36, 0xcded8, 0xd3072) and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                                # 49fc6: LONG 26(A6) = 0 -> ORI Set
    if entry == 0xcde96:
        return dict(writes=[(0xfd92, 1, (0, 1)[t % 2])])                                 # 497a6: BYTE 10fd92 = 0 -> ORI Set
    if entry in (0x4c112, 0x4c16c):
        return dict(stack=[(4, (0, 0x00100000, 0x80000000)[t % 3]), (2, 4)], a6off=[(0x42, 4, (0x00400000, 0x01000000, 0x00100000)[(t // 3) % 3]),
                                                                                   (0x46, 4, (0x00400000, 0x00c00000, 0x00e00000)[(t // 9) % 3])])
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d)] + [(6, 0x26, 4)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            st = world.make(entry, SENTINEL, flds, chain_hint(entry, t, rng))
            tr = trace(st, first_unrouted(extra=tuple(sorted(succ))), cap=400000)
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
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'],
                                                                                                c=tr['sr'] & 1)))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # 8ebe: BYTE 1d(A6) < 4 (>= 4 reaches the untraceable TRAP #15 8ec8); BYTE 15 (the flags tested by 3adec 3ae04 d3068 cdd46 cc958), BYTE 61
            # (cdd46), BYTE 79 (cdd50), BYTE b6 (3adf6), LONG 26 (49fc6: 0 -> Set), BYTE 10fd92 (497a6)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 0x20, 0xa0, 0x10, 0x90)[(t // 4) % 6]), (0x61, 1, (0, 8)[(t // 2) % 2]),
                               (0x79, 1, (0, 1, 2)[t % 3]), (0xb6, 1, (0, 2)[(t // 8) % 2])] + ([(0x26, 4, 0)] if t % 5 == 4 else []),
                        writes=[(0xfd92, 1, (t // 3) % 2)])
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
            add(U.Fixture('natural-%05x-%s%s-f%d-%x' % (cb, cfg, '' if case is None else '%03d' % case, frame, 0x100000 + a), st, [], tr['stop'],
                          meta=dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=0x100000 + a, stop=tr['stop'],
                                    unit_blocks=len(set(tr['pcs']) & STARTS_SET))))
            count += 1
    require(count >= 5, ('too few natural node fixtures', count))


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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr7 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x4ad6d), 'unaligned animation machine PC', 0x4ad6d)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr7 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W 42(A6),D0 of cc5e8 (read), MOVE.W #122,20(A6) of 3ad48 (write); odd stack: MOVEM.L (A7)+ of 3ae04, TST.W (A7)+ of e8ba0 (the
    # LONG 5e26(A5) and its BYTEs read first); odd record: MOVE.W (A0),D0 of 4abca, MOVE.L (A3)+ of 4ad8e (A0 + 12 odd); odd frame: MOVE.W #4,4(A7) of
    # 4c0f0 (A7 - 6 + 4 odd)
    err('cc5e8-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xcc5e8), odd_word, 0xcc5e8, stop=0xcc5f6)
    err('3ad48-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x3ad48), odd_write, 0x3ad48, stop=0x3ad60)
    err('3ae04-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x3ae04), odd_word, 0x3ae04, stop=0x3ae12)
    err('4abca-odd-a0', U.with_host_writes(st, regs=dict(a0=ATK + 1), pc=0x4abca), odd_word, 0x4abca, stop=0x4abde)
    err('4ad8e-odd-a0', U.with_host_writes(st, regs=dict(a0=ATK + 1), pc=0x4ad8e), odd_word, 0x4ad8e, stop=0x4ad94)
    err('4c0f0-odd-frame', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4c0f0), odd_write, 0x4c0f0, stop=0x4c102)
    # failures after executed blocks:
    #   4abc0 (A0 = 0) -> 4ad6a RTS at an odd A7
    err('4abc0-then-4ad6a', U.with_host_writes(st, regs=dict(a0=0, a7=a7 + 1), pc=0x4abc0), odd_word, 0x4ad6a)
    #   cdd6c (BRA) -> cdd84 RTS at an odd A7
    err('cdd6c-then-cdd84', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xcdd6c), odd_word, 0xcdd84)
    #   d2776 (D0 := 167, A0 := d2652) -> d2f90 MOVE.L A0,-(A7) at an odd A7
    err('d2776-then-d2f90', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xd2776), odd_word, 0xd2f90, stop=0xd2f9a)
    #   3adc6 ((A6) := 3add4, enters it) -> 3add4 MOVE.L 3a(A6),-(A7) at an odd A7
    err('3adc6-then-3add4', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x3adc6), odd_word, 0x3add4, stop=0x3adec)
    #   e8bbe (NEG.L) -> e8bc2 (LONGs 36 / 3a written) -> JSR 4be34 at an odd A7
    err('e8bbe-then-e8bc2', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe8bbe), odd_word, 0xe8bc2, stop=0x4be34)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x3ae18, 0x4ac56, 0xcc9bc, 0xd2ff4)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
