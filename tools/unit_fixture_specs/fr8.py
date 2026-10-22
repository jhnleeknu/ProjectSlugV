"""V1 fixture spec of the animation-machine unit FR8 (engine/src/animation_machine_objects_fr8.cpp, 229 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr8-contract.md): the C-gated area-D roots after FR7 except the af990 family (FR9) -- the
object 42d9c (2986 child of B2e 3ac60; install 42e68) with the computed jump 42f9a (9-entry BRA.W table 42fa2..42fc2, all block starts) and the shard
tail 430ba, the emitter object d3500 (28ae child of the helper d3802; install d3554) with d383c, the object cdc24 (FR4 cdc1c install), the object 38e92
(N32 / N32b install; installs 38eb4 38ece 38ee2 38f08), the object aea38 (LONG table e8eac) with the state machine ae930 (installs aeab0 aeb32) and the
child helpers d39f6 / d3a2e, and the FR4 table entry cc7b4.  No TRAP.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR7) with declared host edits.  This
code runs natively only after the first C stop of its IO run (C-gated, boot-demo-0 only): besides the declared worlds the 'natural' family takes the
frame-start states of the IO native observation (artifacts/animation_machine_io_native/states, observe_animation_machine_io.read_pack) in which a node
holds one of the unit's callbacks, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the
sentinel return LONG, PC = the callback; D0-D7 / A0-A4 = the frame-start values).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 6 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node or the
            declared emitter record GREC, LONG 96(A6) := GREC (or a ROM emitter record), LONG 82(A6) := a natural N32 action routine, the node / A2 / A5 fields the
            reachable blocks read, the stack values the entered block pops, PC := the block start).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 3a4da -> 38fb4 (38fa2), 4b54e -> ae936 (ae930), 1ab02 -> aea22 (aea18), 497a6 ->
            cdd0c (cdd06), 28ae -> d3814 (d3802) / d3a4c (d3a38).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 6 consumers, odd node / stack / record, a computed landing inside
            the jump block, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row
            when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR7 specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR7)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x38e92, 0x38f0c), (0x38f14, 0x38ff4), (0x42d9c, 0x4309a), (0x430ba, 0x430e6), (0xae930, 0xaeb4c), (0xcc7b4, 0xcc7b8), (0xcdc24, 0xcdd2e),
          (0xd3500, 0xd354c), (0xd354e, 0xd3580), (0xd3802, 0xd38e2), (0xd39f6, 0xd39fe), (0xd3a2e, 0xd3a70)]
STARTS = sorted([int(x, 16) for x in (
    '38e92 38ea4 38eae 38eb4 38eba 38ebe 38ec8 38ece 38ed2 38edc 38ee2 38ee8 38eec 38f02 38f08 '
    '38f14 38f1e 38f22 38f2a 38f32 38f3c 38f44 38f4c 38f56 38f5e 38f66 38f6e 38f78 38f82 38f8e 38f98 38fa2 38fb4 38fbc 38fc4 38fd0 38fd8 38fe0 38fe8 '
    '38fec 38ff0 '
    '42d9c 42da4 42dd2 42de0 42e0c 42e20 42e24 42e3a 42e3c 42e52 42e54 42e68 42e6e 42e88 42e8e 42e98 42e9e 42eaa 42eb0 42ec0 42ec6 42ec8 42ed2 42ed8 '
    '42eee 42ef4 42f08 42f12 42f18 42f32 42f38 42f4c 42f52 42f5c 42f62 42f7c 42f8a 42f92 42f9a 42fa2 42fa6 42faa 42fae 42fb2 42fb6 42fba 42fbe 42fc2 '
    '42fc6 42fd0 42fd4 42fde 42fe8 42fec 42ff0 42ffa 43002 43008 43030 43044 43048 4305e 43060 43080 43090 430ba 430d0 430e0 '
    'ae930 ae936 ae93a ae93e ae948 ae956 ae960 ae97c ae986 ae99e ae9a8 ae9b4 ae9bc ae9cc ae9d6 ae9ee ae9f8 aea04 aea08 aea12 aea18 aea22 aea26 aea36 '
    'aea38 aea4a aea54 aea68 aea72 aea78 aea8c aea92 aea9a aea9e aeaaa aeab0 aeaba aeac0 aeac4 aeaca aeb02 aeb08 aeb12 aeb1c aeb22 aeb28 aeb2c aeb32 '
    'aeb38 aeb44 aeb4a '
    'cc7b4 '
    'cdc24 cdc2c cdc42 cdc46 cdc4e cdc64 cdc68 cdc70 cdc86 cdc8a cdc92 cdca8 cdcac cdcb4 cdcca cdcce cdce4 cdd06 cdd0c cdd10 cdd16 cdd1a cdd24 '
    'd3500 d3518 d3522 d3528 d3532 d353c d3540 d3546 d354e d3554 d355a d3562 d3570 d3578 d357e '
    'd3802 d3814 d3818 d3822 d3826 d3830 d3836 d383c d384a d385c d385e d386c d387e d3880 d3892 d3898 d38a0 d38ac d38bc d38c2 d38d0 '
    'd39f6 d3a2e d3a36 d3a38 d3a4c d3a50 d3a5a d3a5e d3a6e').split()])
CONSUMERS = (0x38fb4, 0xae936, 0xaea22, 0xcdd0c, 0xd3814, 0xd3a4c)
CLEAR_SET = ()
SET_SET = (0xd3822, 0xd3a5a)            # ORI.B #1,CCR (fall-through into a non-consumer)
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
CHAINS = ((0x38fa2, 0x38fb4), (0xae930, 0xae936), (0xaea18, 0xaea22), (0xcdd06, 0xcdd0c), (0xd3802, 0xd3814), (0xd3a38, 0xd3a4c))
PASS_CHAINS = ()
JUMP_BLOCK = 0x42f9a                    # ADD.W D0,D0; ADD.W D0,D0; JMP 42fa2(PC,D0.W)
TABLE = tuple(0x42fa2 + 4 * k for k in range(9))
TABLE_ENTRIES = TABLE
# callbacks and installed values (node callbacks); the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0x42d9c, 0x42e68, 0xcdc24, 0x38e92, 0x38eb4, 0x38ece, 0x38ee2, 0x38f08, 0xd3500, 0xd3554, 0xaea38, 0xaeab0, 0xaeb32)
CALLEES = (0xd3802, 0xd383c, 0xd39f6, 0xd3a2e)
# values a direct entry pops below the return LONG at A7, lowest address first: ('L'|'W', kind) with kind node / any / grec
STACK = {0x38f8e: (('L', 'any'),), 0x38fb4: (('L', 'any'),)}
for _pc in (0xd3814, 0xd3818, 0xd3822, 0xd3826, 0xd3830, 0xd3836):
    STACK[_pc] = (('L', 'grec'),)       # the A1 pushed by d3802 (MOVE.L (A7)+,96(A0) of d3836 pops it)
for _pc in (0xd3a4c, 0xd3a50, 0xd3a5a, 0xd3a5e):
    STACK[_pc] = (('L', 'any'), ('W', 'count'))   # MOVE.L D1,-(A7) below MOVE.W D0,-(A7) of d3a38
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x82, 0x96)   # node links and pointer fields: natural or declared below
GREC = 0x10fb00                         # declared emitter record (LONG 96(A6)): BYTE 0 flag, BYTE 1 interval, WORD 2 count, WORDs 4 6 8 a, BYTE d, LONG e
GTAB = 0x10fb40                         # declared LONG table of child values (LONG e(GREC) when BYTE d != 0; index (random & 3c))
ROM_GREC = (0xbbdc0, 0xbbf04, 0x549bc, 0x5b5e6, 0x90e96)   # natural emitter records (A1 of the d3802 calls)
N32_ACTIONS = (0x3a60a, 0x3a7b6, 0x3a8d2, 0x3a9aa)   # natural LONG 82(A6) of the N32 objects (IO pack boot-demo-0): the 3a5be JSR (A0) targets
CHILD_VALUES = (0xd1d38, 0xd309a, 0x430e6, 0x3b166, 0x38c36)  # 28ae child callback values (written only by 28ae)
NATURAL = tuple(('boot-demo-0', None, f) for f in (434, 478, 481, 538, 539, 541, 546, 552, 563, 577))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xb, 0xf, 0x10, 0x1b, 0x1f, 0x20, 0x3f, 0x40, 0x41, 0x7f, 0x80, 0x81, 0xbf, 0xc0, 0xdf, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 8, 9, 0xa, 0xf, 0x10, 0x1f, 0x20, 0xff, 0x100, 0x13f, 0x140, 0x1ff, 0x200, 0x1f80, 0x2000, 0x3fff, 0x4000, 0x7fff,
      0x8000, 0x8001, 0xe000, 0xe0ed, 0xfffc, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x10, 0x8000, 0xffff, 0x10000, 0x100000, 0x6f364, 0x7fffffff, 0x80000000, 0xffff0000, 0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {JUMP_BLOCK: TABLE}       # transcribed jump table (contract decision 2)


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
BUNDLED = (0xcdd02,)                    # cdcfe BEQ.W + cdd02 BPL.W share the N / Z of MOVE.W (A0,D0.W),D0


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
    """The PC after the entry block: pcs[n] (the bundled Bcc pair of cdce4 takes pcs[n - 1] when its first Bcc is taken)."""
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
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 5, 8, 9, 0x12340001, 0xffff, 0x8000, 0x10000, 0x100))   # small WORD indices / counts
        writes = []
        regs['a0'] = self.pointer()                             # A0: a child node (written through) or a record pointer
        regs['a1'] = rng.choice((GREC, self.pointer()) + ROM_GREC)
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        # the declared emitter record GREC (LONG 96(A6)) and its child-value table GTAB
        writes += [(GREC & 0xffff, 1, rng.choice((0, 0, 1, 0xff))), ((GREC + 1) & 0xffff, 1, rng.choice((0, 1, 2, 8, 0xff))),
                   ((GREC + 2) & 0xffff, 2, rng.choice((0, 1, 2, 3, 8, 0x8000, 0xffff)))]
        for off in (4, 6, 8, 0xa):
            writes.append(((GREC + off) & 0xffff, 2, rng.choice((0, 1, 0x10, 0x20, 0x70, 0xffc8, 0x7fff, 0x8000, 0xffff, self.value(2)))))
        writes += [((GREC + 0xc) & 0xffff, 1, 0), ((GREC + 0xd) & 0xffff, 1, rng.choice((0, 0, 1, 0x80))),
                   ((GREC + 0xe) & 0xffff, 4, rng.choice(CHILD_VALUES + (GTAB, GTAB)))]
        for k in range(16):
            writes.append(((GTAB + 4 * k) & 0xffff, 4, rng.choice(CHILD_VALUES)))
        writes.append(((a6 + 0x96) & 0xffff, 4, rng.choice((GREC, GREC, GREC) + ROM_GREC)))
        writes.append(((a6 + 0x82) & 0xffff, 4, rng.choice(N32_ACTIONS)))       # 3a5be: JSR (A0) with A0 := LONG 82(A6) (the natural action routines)
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe: BYTE 1d(A6) < 4 (>= 4 reaches the TRAP #15 8ec8)
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
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5418) & 0xffff, 2, self.value(2)))           # aeb38: WORD 5418(A5)
        # stack values popped by the entered block (declared), the return LONG above them
        pops = []
        for size, kind in STACK.get(entry, ()):
            v = {'node': self.pointer(), 'grec': rng.choice((GREC,) + ROM_GREC), 'count': rng.choice((0, 1, 2, 3, 0x8000, 0x8001, 0xffff)),
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
            if hint.get('grec') is not None:
                writes.append(((a6 + 0x96) & 0xffff, 4, GREC))
                for off, size, val in hint['grec']:
                    writes.append(((GREC + off) & 0xffff, size, val))
            for off, size, val in hint.get('a2off', []):
                if in_ram(regs['a2'] + off, size):
                    writes.append(((regs['a2'] + off) & 0xffff, size, val))
            if hint.get('mirror'):
                regs['a6'] = a6 | 0xf0000                       # the node in the upper RAM mirror (1fxxxx = 10xxxx)
            if hint.get('a5_mirror'):
                regs['a5'] = a5 | 0xf0000                       # A5 in the upper RAM mirror (1f8000 = 108000)
            if hint.get('grec_mirror'):
                writes.append(((a6 + 0x96) & 0xffff, 4, GREC | 0xf0000))   # the emitter record through the upper RAM mirror
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
    require(len(STARTS) == 229 and len(STARTS_SET) == 229, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS:
        require(unit_of(t) is None and not mine(t), ('TRAP site must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr8_block', ('start is not routed to fr8', hex(s), unit_of(s)))
    for a in (GREC, GTAB):
        require(unit_of(a) is None and in_ram(a, 0x40), ('declared record must be work RAM outside the stack page', hex(a)))
    rng = random.Random(0xF83A)
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
    sys.stderr.write('fr8 spec: %d fixtures (%d natural), visited %d/229, missing successors %s, unreachable outcomes %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') == 'natural'), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr8: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr8: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD sign
    boundaries, equal-value ties at BCS / BCC / BLT / BGT, BMI versus BLT on overflow, the SUBQ wraps), the index of the computed jump 42f9a (every table
    entry and outside the table), the zero / sign extension of MOVEQ #0 + MOVE.B and of the WORD indices (negative indices of cdce4 / aeaca), the popped
    LONGs / WORD, the upper register bits of the WORD / BYTE operations, TST.W versus TST.L / TST.B, the node / record / A5 in the upper RAM mirror and
    flag-bit combinations with the masks after them.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0x42d9c, 0x42da4, 0x42dd2, 0x42f7c, 0x42fc6, 0x42fde, 0x42ff0, 0xae956, 0xae99e, 0xae9ee, 0xaea08, 0xaea38, 0xaea4a, 0xd3802, 0xd38a0,
                 0xd3a38, 0xcdc2c, 0xcdc4e, 0xcdc70, 0xcdc92, 0xcdcb4, 0xcdcce, 0xcdd1a, 0xd3518, 0xd3818, 0xd3a50, 0xae97c, 0xae9cc, 0x43080, 0x430d0,
                 0x430ba, 0xd39f6, 0x42f62, 0x38f82, 0x38fa2, 0x38fbc, 0xaeb32, 0xaea18, 0xae930):
        h += [dict(regs=dict(up))]
    # ---- 38e92 object
    if entry in (0x38e92, 0x38eb4, 0x38ee2):
        h += byte(0x99, (0, 1, 0x80, 0xff)) + [dict(mirror=True, a6off=[(0x99, 1, 0)])]
    if entry == 0x38eec:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x99, 1, v)]) for v in (0, 1, 2, 0x80, 0xff)]
    if entry in (0x38f14, 0x38f32, 0x38f4c):
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry in (0x38f22, 0x38f2a, 0x38f3c, 0x38f56, 0x38f5e, 0x38f66):
        h += regs('d0', (0, 0x80, 0x8000, 2, 0x20, 4, 8, 0xff, 0xffffff00, 0x7f, 0x100, 0x200))
    if entry == 0x38f44:
        h += byte(0x9f, (0, 1, 0x80))
    if entry == 0x38f6e:
        h += byte(0x94, (0, 4, 0xfb, 0xff))
    if entry == 0x38f78:
        h += byte(0x9d, (0, 0x10, 0xef, 0xff))
    if entry == 0x38f98:
        h += byte(0x9d, (0x40, 0xbf, 0, 0xff))
    if entry == 0x38fa2:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x9d, 1, a), (0x9e, 1, b)]) for a, b in ((0xff, 0xff), (0x40, 0x41), (0, 0xbf), (0xbf, 0x40))]
    if entry == 0x38f8e:
        h += [dict(regs=dict(d0=a), stack=[(4, b)]) for a, b in ((0x10000, 0x12345678), (0, 0x9abcdef0), (1, 0), (0xffff0000, 0xffffffff), (0x8000, 1))]
    if entry == 0x38fc4:
        h += [dict(regs=dict(d0=0x12345600), a6off=[(0x97, 1, v)]) for v in (0, 1, 2, 3, 4, 5, 0xff)]
    if entry in (0x38fd0, 0x38fd8, 0x38fe0):
        h += regs('d0', (0x12340102, 0x12340003, 0x12340204, 0x5, 0x00000302, 0x103, 0x404))
    # ---- 42d9c object
    if entry == 0x42de0:
        h += [dict(regs=dict(up), a6off=[(0x15, 1, a), (0x76, 1, b)]) for a, b in ((0, 0x20), (0xff, 0xdf), (0x09, 0x80), (0xf6, 0x7f))]
    if entry in (0x42e0c, 0x43030):
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0), a6off=[(0x76, 1, v)]) for v in (0x20, 0xdf, 0, 0xff)]
    if entry in (0x42e20, 0x43044):
        h += regs('d0', (0x123456f1, 0x12345600, 0xff, 0xf0))
    if entry in (0x42e24, 0x43048):
        h += [dict(regs=dict(d0=a), a6off=[(0x76, 1, b)]) for a, b in ((0x1234abcd, 0x20), (0xffff, 0), (0x0f0f, 0x3f), (0x12340000, 0xff))]
    if entry == 0x42e3a:
        h += regs('d0', (0x123456f9, 0x7f, 0xffffffff))
    if entry == 0x42e3c:
        h += [dict(regs=dict(d0=a), a6off=[(0x76, 1, b)]) for a, b in ((0x1234ffff, 0x20), (0x12340000, 0), (0x0007, 0xff), (0xfff8, 0x1f))]
    if entry in (0x42e52, 0x4305e):
        h += regs('d0', (0xfd, 0x123456fe, 0x1234ffff))
    if entry in (0x42e54, 0x43060):
        h += regs('d0', (0x1234ffff, 0x0fff, 0x12345603, 0xfffc))
    if entry == 0x42e6e:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x8c, 1, v)]) for v in (0, 0xf, 0x10, 0xff, 0x1f, 7)]
    if entry == 0x42e88:
        h += regs('d0', (0x100, 0, 1, 0xffffff00, 0x80))
    if entry == 0x42e8e:
        h += byte(0x15, (0x20, 0xdf, 0, 0xff))
    if entry == 0x42e9e:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x42, 2, v)]) for v in (0x13f, 0x140, 0, 0xffff, 0x8000)]
    if entry == 0x42eb0:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x46, 2, v)]) for v in (0xff, 0x100, 0x1ff, 0x200, 0, 0xffff, 0x80ff)]
    if entry == 0x42ec8:
        h += byte(0x76, (0x80, 0xbf, 0xc0, 0x3f, 0x40, 0x7f, 0, 0xff))
    if entry == 0x42ed2:
        h += byte(0x15, (0, 0xfe, 0xff)) + [dict(mirror=True, a6off=[(0x15, 1, 0x10)])]
    if entry == 0x42ed8:
        h += byte(0x61, (0, 1, 0xfe, 0xff))
    if entry == 0x42f08:
        h += byte(0x61, (0, 2, 0xfd, 0xff))
    if entry in (0x42ef4, 0x42f52):
        h += [dict(regs=dict(d0=a), a6off=[(0x32, 2, b)]) for a, b in ((0x1234fff0, 0xffff), (0x12340007, 0x7fff), (0x12340006, 0), (0xffffffff, 0x8000))]
    if entry in (0x42f18, 0x42f38):
        h += [dict(regs=dict(d0=a), a6off=[(0x2e, 2, b), (0x6f, 1, c), (0x15, 1, d)]) for a, b, c, d in
              ((0x1234fff0, 0xffff, 0x40, 0), (0x12340007, 0x7fff, 0x41, 0xfd), (0x12340006, 0, 0xc0, 0xff), (0xffffffff, 0x8000, 0x40, 2))]
    if entry == 0x42f92:
        h += regs('d0', (8, 9, 0xffff, 0x12340008, 0x00010009, 0, 0x8000))
    if entry == 0x42f9a:
        h += [dict(regs=dict(d0=0x12340000 | k)) for k in range(9)] + regs('d0', (9, 0xfffe, 0xfff7, 0xfffd))
    if entry == 0x42fd4:
        h += [dict(a2off=[(0x61, 1, v)]) for v in (0x80, 0x7f, 0, 0xff)]
    if entry == 0x42ffa:
        h += byte(0x8f, (0x80, 0, 1, 0x81, 0x7f, 0xff, 2))
    if entry == 0x43008:
        h += [dict(regs=dict(d0=a, d1=0x9abcdef0), a6off=[(0x76, 1, b)]) for a, b in ((0x1234ffff, 0), (0x12341f80, 0x80), (0x0000c000, 0xff), (0x12340000, 0x7f),
                                                                                       (0xffff3fff, 0x40))]
    if entry in (0x43080, 0x430d0):
        h += [dict(regs=dict(up), a6off=[(0x7c, 4, v)]) for v in (0x6f364, 0xffffffff)]
    # ---- ae930 / aea38
    if entry == 0xae93a:
        h += byte(0x5e, (0xff, 1))
    if entry in (0xae93e, 0xae960, 0xaea26):
        h += byte(0x61, (0, 0x80, 0x7f, 0xff)) + [dict(mirror=True, a6off=[(0x61, 1, 0x80)])]
    if entry == 0xae948:
        h += word(0x7e, (3, 4, 0xffff, 0x7fff, 0, 0x103)) + [dict(mirror=True, a6off=[(0x7e, 2, 3)])]
    if entry in (0xae986, 0xae9d6):
        h += [dict(regs=dict(up), a6off=[(0x32, 2, v)]) for v in (0xffc0, 0x7fc0, 0xff80, 0)]
    if entry in (0xae9a8, 0xae9f8):
        h += word(0x32, (0x3f, 0x40, 0x7f, 0x80, 0, 0x8000))
    if entry in (0xae9b4, 0xaea92, 0xaea54):
        h += word(0x7a, (0, 1, 0x100, 0x8000))
    if entry == 0xaea78:
        h += word(0x76, (0, 0x100, 1, 0x8000))
    if entry == 0xaea8c:
        h += byte(0x15, (0, 1, 0xfe, 0xff)) + [dict(mirror=True, a6off=[(0x15, 1, 1)])]
    if entry in (0xaeab0, 0xaeb08):
        h += byte(0x15, (0, 0x80, 1, 0x81, 0xff))
    if entry == 0xaeaca:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0), a6off=[(0x7e, 2, v)]) for v in (0, 1, 0x1fff, 0x2000, 0x3fff, 0x7fff, 0x8000, 0xffff)]
    if entry == 0xaeb38:
        h += [dict(regs=dict(d0=0x12345678), a5off=[(0x5418, 2, a)], a6off=[(0x7a, 2, b)]) for a, b in
              ((5, 5), (4, 5), (6, 5), (0x7fff, 0x8000), (0x8000, 0x7fff), (0xffff, 0), (0, 0xffff))]
        h += [dict(a5_mirror=True, a5off=[(0x5418, 2, 5)], a6off=[(0x7a, 2, 5)])]
    # ---- cdc24
    if entry in (0xcdc24, 0xcdce4):
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x8c, 2, v)]) for v in (0, 1, 2, 3, 4, 5, 0x100, 0xffff, 0x4000, 0x3fff, 0x8000)]
    if entry in (0xcdc46, 0xcdc68, 0xcdc8a, 0xcdcac):
        h += regs('d0', (1, 2, 3, 4, 5, 0x12340001, 0x12340003, 0x10002, 0x10004))
    if entry in (0xcdc2c, 0xcdc4e, 0xcdcce):
        h += word(0x8a, (0, 0xffff, 0x163))
    if entry in (0xcdd10, 0xcdd16):
        h += [dict(regs=dict(d0=0x12345678, a0=a)) for a in (0xcdf56, 0xcdf7e, 0xcdf3a, 0xcdf3e)]  # cdf3a/cdf3e: inside the synthetic cdf3a table, WORD (A0) != WORD 2(A0) (mutant cdd10-2; Qwen draft, main checked)
    # ---- d3500 / d3554 / d3802 / d383c
    if entry == 0xd3500:
        h += [dict(regs=dict(up), grec=[(0, 1, a), (1, 1, b), (2, 2, c)]) for a, b, c in ((0, 1, 8), (1, 0xff, 0), (0x80, 0, 0xffff))]
        h += [dict(grec_mirror=True, grec=[(0, 1, 1), (1, 1, 2), (2, 2, 3)])]
    if entry == 0xd3528:
        h += byte(0xa0, (0xff, 0xfe, 0, 0x7f))
    if entry in (0xd3532, 0xd3540, 0xd3570):
        h += word(0x9e, (0, 1, 2, 0x8000, 0xffff))
    if entry == 0xd355a:
        h += byte(0xa0, (1, 0, 2, 0x80, 0xff))
    if entry == 0xd3562:
        h += [dict(grec=[(1, 1, v)]) for v in (0, 1, 0xff)]
    if entry in (0xd3802, 0xd3836):
        h += [dict(regs=dict(up, a1=GREC)), dict(regs=dict(up, a1=0xbbdc0))]
    if entry == 0xd3826:
        h += byte(0x15, (0, 4, 0xfb, 0xff))
    if entry == 0xd383c:
        h += [dict(regs=dict(up), grec=[(6, 2, v)]) for v in (0, 0x10, 0xffff, 0x8000)]
    if entry in (0xd384a, 0xd386c):
        h += [dict(regs=dict(d0=a), grec=[(4, 2, b), (8, 2, b)], a6off=[(0x15, 1, f)]) for a, b, f in
              ((0x1234ffff, 1, 0), (0x12340001, 0xffff, 3), (0x8000, 0x8000, 1), (0, 0x7fff, 2))]
    if entry in (0xd385c, 0xd387e):
        h += regs('d0', (0x12340001, 0x8000, 0, 0xffff))
    if entry == 0xd385e:
        h += [dict(regs=dict(d0=0x1234abcd), grec=[(0xa, 2, v)]) for v in (0, 0xffff)]
    if entry == 0xd3880:
        h += [dict(grec=[(0xd, 1, a), (0xe, 4, b)]) for a, b in ((0, 0xd1d38), (1, GTAB), (0x80, GTAB))]
    if entry == 0xd3898:
        h += [dict(regs=dict(d0=a, a0=GTAB)) for a in (0x1234ffff, 0x3c, 0x40, 0xffc3, 0)]
    if entry == 0xd38ac:
        h += [dict(a6off=[(0x15, 1, a), (0x1e, 2, b)]) for a, b in ((0, 0xe0ed), (4, 0), (0xff, 0xffff))]
    if entry == 0xd38c2:
        h += [dict(regs=dict(up), a6off=[(0x36, 2, a), (0x3a, 2, b)]) for a, b in ((0xffff, 0x8000), (1, 2))]
    if entry in (0xd39f6, 0xd3a2e):
        h += [dict(regs=dict(d0=a, a1=0x12345678)) for a in (0, 1, 0x10000, 0x10001, 0xffff)]
    if entry == 0xd3a38:
        h += [dict(regs=dict(d0=a, d1=0x9abcdef0)) for a in (1, 0x12340002, 0x8000)]
    if entry == 0xd3a5e:
        h += [dict(regs=dict(d0=0x12345678), stack=[(4, 0x9abcdef0), (2, w)]) for w in (1, 2, 0, 0x8000, 0x8001, 0xffff)]
    return h


def chain_hint(entry, t, rng):
    """Edits that let the real producer of a chain return both C values."""
    if entry == 0x38fa2:
        return dict(a6off=[(0xb2, 1, (1, 0)[t % 2])], writes=[(0xf001, 1, (0, 4)[(t // 2) % 2])])   # 3a4da: BYTE b2 != 0 -> Clear; 4d6b4 path
    if entry == 0xae930:
        return dict(a6off=[(0x56, 4, 0 if t % 2 else rng.choice((0x10fb00, 0x100cb8)))], a5off=[(0x5744, 1, (0, 0x80)[(t // 2) % 2]), (0x5b84, 1, t % 3)])
    if entry == 0xaea18 and t % 2:
        on = (t // 2) % 2 == 0
        return dict(a6off=[(0x42, 4, 0x00a00000 if on else 0x7fff0000), (0x46, 4, 0x00800000 if on else 0x7fff0000), (0x4a, 4, 0), (0x4e, 4, 0),
                           (0x15, 1, 0)])                                                  # 1ab02: on screen (Clear) / off (Set)
    if entry == 0xcdd06:
        return dict(writes=[(0xfd92, 1, (0, 1)[t % 2])])                                 # 497a6: BYTE 10fd92 = 0 -> ORI Set
    if entry in (0xd3802, 0xd3a38):
        return dict(writes=[(0x4ca0, 2, (0, 0x100, 5, 0x15)[t % 4])])                  # 28ae: the count limit decides success / failure
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d, 0xb2)] + [(6, off, 4) for off in (0x42, 0x46, 0x4a, 0x4e, 0x56)]
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
            # 8ebe: BYTE 1d(A6) < 4 (>= 4 reaches the untraceable TRAP #15 8ec8); BYTE 15 / 61 (the flags tested by 38f14 42e8e 42ed8 ae93e aeab0 d3826),
            # BYTE 99 / 97 (38e92 38fc4), WORD 7a / 7e / 76 (ae930 aea54), WORD 8c (cdc24), BYTE a0 / WORD 9e (d3500 d3554), BYTE 10fd92 (497a6), WORD
            # 104ca0 (28ae count limit)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 0x20, 0xa0, 0x01, 0x85)[(t // 4) % 6]), (0x61, 1, (0, 0x80, 1, 2)[(t // 2) % 4]),
                               (0x99, 1, (0, 1)[t % 2]), (0x97, 1, (0, 2, 3, 5)[(t // 3) % 4]), (0x7a, 2, (0, 1)[(t // 5) % 2]), (0x7e, 2, t % 5),
                               (0x76, 2, (0, 1)[(t // 7) % 2]), (0x8c, 2, t % 6), (0xa0, 1, (0xff, 1, 2)[t % 3]), (0x9e, 2, (1, 2, 0)[(t // 3) % 3])],
                        writes=[(0xfd92, 1, (t // 3) % 2), (0x4ca0, 2, (0x100, 0, 0x15)[(t // 11) % 3])])
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr8 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x42d9d), 'unaligned animation machine PC', 0x42d9d)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr8 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W 8c(A6),D0 of cdc24 (read), MOVE.L #6f364,7c(A6) of 42da4 (write); odd stack: MOVEM.L (A7)+,D0 of 38f8e, MOVE.L (A7)+,D1 of
    # d3a5e, MOVE.L A1,-(A7) of d3802; odd record: MOVE.W 2(A0),9e(A6) of d3500 (A0 := LONG 96(A6) odd)
    err('cdc24-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xcdc24), odd_word, 0xcdc24, stop=0xcdc2c)
    err('42da4-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x42da4), odd_write, 0x42da4, stop=0x42dd2)
    err('38f8e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x38f8e), odd_word, 0x38f8e, stop=0x38f98)
    err('d3a5e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xd3a5e), odd_word, 0xd3a5e, stop=0xd3a6e)
    err('d3802-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xd3802), odd_word, 0xd3802, stop=0xd3814)
    err('d3500-odd-record', U.with_host_writes(st, [((a6 + 0x96) & 0xffff, 4, GREC + 1)], pc=0xd3500), odd_word, 0xd3500, stop=0xd3518)
    # the computed jump lands inside its own block: D0.W = ffff -> 42fa2 - 4 = 42f9e (the JMP of the block 42f9a)
    err('42f9a-to-42f9e', U.with_host_writes(st, regs=dict(d0=0xffff), pc=0x42f9a), 'unsupported animation objects fr8 PC', 0x42f9e)
    # failures after executed blocks:
    #   cc7b4 (BRA.W) -> FR4 cdc1c MOVE.L #cdc24,(A6) at an odd A6
    err('cc7b4-then-cdc1c', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xcc7b4), odd_write, 0xcdc1c)
    #   42f9a (D0.W = 1: entry 42fa6) -> 42ff0 MOVE.W #1a5e,D0; JSR 3af8.l at an odd A7
    err('42f9a-then-42ff0', U.with_host_writes(st, regs=dict(d0=1, a7=a7 + 1), pc=0x42f9a), odd_word, 0x42ff0, stop=0x3af8)
    #   42fec (BRA.W) -> 430ba JSR 2986.l at an odd A7
    err('42fec-then-430ba', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x42fec), odd_word, 0x430ba, stop=0x2986)
    #   d39f6 (LEA; BRA) -> d3a2e (D0.W = 1) -> d3a38 MOVE.W D0,-(A7) at an odd A7
    err('d39f6-then-d3a38', U.with_host_writes(st, regs=dict(d0=1, a7=a7 + 1), pc=0xd39f6), odd_word, 0xd3a38, stop=0x28ae)
    #   aeb44 (MOVE.L #aeb4c,(A6)) -> aeb4a RTS at an odd A7
    err('aeb44-then-aeb4a', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xaeb44), odd_word, 0xaeb4a)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x43008, 0xaeaca, 0xcdce4, 0xd3a5e)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
