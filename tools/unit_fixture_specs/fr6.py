"""V1 fixture spec of the animation-machine unit FR6 (engine/src/animation_machine_objects_fr6.cpp, 220 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr6-contract.md): the last C-independent area-D IO frontier of the FR5 IO rerun, the object
50dae (the install value of U14 50d82) with its installs 50dd2 50e42 50cf6 50d08 50f1a 50f80 50f9c 50ffe 51076 and its helpers 51608 51590 515a2
51178 51574 491fe, and the front of FR7 (C-gated D): the condition test 4855c, the bound helper 19a00, the object d764a (the 28ae child of stage_area
d760a; installs d7692 d76a6 d76b2 d7700 d7766 d77ba), the object 36292, the helpers 1aa66 1a988 e9148 49c38 48210, the object 72978 (install 729e2)
with 703f6, the 28ae child 4fcb8 (install 4fcc4) and the BCD add e625e / e6284.  No computed jump, no TRAP.

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR5) with declared host edits.  The real entry
states of the 50dae object are the confirmed frontier frames of the FR5 IO rerun (ms5-scratch/fr5/ioA/frontier.json: P1 / P1b frame 271 callback
50dae) and their natural successors (frames 272..600 of the same runs).  The FR7 front runs natively only after the first C stop of its IO runs
(C-gated): its fixtures stand on declared states alone (contract decision 6); this spec does not decode the IO packs.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 12 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node, LONG
            c(A6) := a natural node, LONG 80(A6) := a script (ROM 50e80 + 4 k or the RAM script 10fd00), LONG 72(A6) := 0 or a natural node, the node /
            parent / A5 / absolute RAM fields the reachable blocks read, the stack values the entered block pops, PC := the block start).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 482aa -> 362cc (362c6), 289e -> 4858e (48582), 1aa66 -> 48598 (48592), 4945e -> 50d0e
            (50d08), 28ae -> 50f62 (50f52), 51044 / 51050 -> 51054 (51044), 49fc6 -> 729ee (729e8) / d77da (d77c8), 49fca -> d7802 (d77ec), 4855c ->
            d7698 (d7692) / d76b8 (d76b2) / d770e (d7708).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 12 consumers, odd node / stack / pointer, failures after executed
            blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is
            even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR5 specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR5)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x19a00, 0x19a40), (0x1a988, 0x1a996), (0x1aa66, 0x1aa7e), (0x36292, 0x362e0), (0x48210, 0x48226), (0x4855c, 0x485a8), (0x491fe, 0x49214),
          (0x49c38, 0x49c56), (0x4fcb8, 0x4fcce), (0x50cf6, 0x50d2c), (0x50dae, 0x50e80), (0x50e94, 0x510d0), (0x51178, 0x511ae), (0x51574, 0x515e0),
          (0x51608, 0x5160e), (0x703f6, 0x70418), (0x72978, 0x72a10), (0xd764a, 0xd7828), (0xe625e, 0xe62a8), (0xe9148, 0xe9150)]
STARTS = sorted([int(x, 16) for x in (
    '19a00 19a06 19a0e 19a12 19a1a 19a1e 19a26 19a2e 19a32 19a3a 19a3e 1a988 1aa66 1aa72 1aa78 '
    '36292 362a0 362a6 362ac 362b2 362ba 362c2 362c6 362cc 362d0 362d2 362d8 362da 48210 4821c 48220 '
    '4855c 48564 4856e 48578 48582 4858e 48592 48598 4859c 485a2 491fe 4920e 49c38 49c4a 49c50 4fcb8 4fcc4 '
    '50cf6 50d02 50d08 50d0e 50d12 50d20 50d24 50d2a '
    '50dae 50dcc 50dd2 50dda 50de0 50dee 50dfc 50e06 50e22 50e34 50e42 50e4c 50e52 50e60 50e6c 50e6e 50e78 '
    '50e94 50ea4 50eb8 50ed0 50ed8 50ede 50ee4 50ef6 50f14 50f1a 50f24 50f2a 50f34 50f3e 50f44 50f50 50f52 50f62 50f74 50f7a 50f80 50f86 50f8e '
    '50f90 50f9c 50fa2 50faa 50fb0 50fb2 50fbc 50fcc 50fde 50ff0 50ffe 51010 51014 51020 51024 5102e 51032 51040 51044 51050 51054 51058 5105e '
    '51062 51064 5106a 51076 5107a 5107e 51086 5108e 5109a 510a2 510ae 510b2 510b6 510be 510c4 510c8 510cc '
    '51178 51188 51192 511a2 511ac 51574 5157a 51584 5158a 51590 5159a 515a0 515a2 515da 51608 '
    '703f6 703fe 70406 7040c 70416 72978 72980 729a8 729ac 729d4 729e2 729e8 729ee 729f2 729f8 729fc 72a06 72a0c '
    'd764a d765e d766c d767a d7692 d7698 d769c d76a4 d76a6 d76b2 d76b8 d76bc d76c4 d76da d76e0 d76e6 d76ec d76f2 d76f4 d7700 d7708 d770e d7712 '
    'd7714 d7766 d7780 d779e d77aa d77b4 d77ba d77c0 d77c8 d77da d77e0 d77e4 d77ec d7802 d7808 d780c d7812 d7820 d7826 '
    'e625e e6266 e6270 e6278 e6282 e6284 e629c e62a6 e9148').split()])
CONSUMERS = (0x362cc, 0x4858e, 0x48598, 0x50d0e, 0x50f62, 0x51054, 0x729ee, 0xd77da, 0xd7802, 0xd7698, 0xd76b8, 0xd770e)
CLEAR_SET = (0x1aa72, 0x485a2, 0x49c4a, 0x51044)    # ANDI.B #fe,CCR; RTS (1aa72 485a2 49c4a) / AND.B D3,D2 (51044: C := 0 for 51054)
SET_SET = (0x1aa78, 0x4859c, 0x49c50, 0x51050)      # ORI.B #1,CCR; RTS (1aa78 4859c 49c50) / ORI.B #1,CCR (51050, falls into 51054)
CLEAR_AFTER = (0x50f62,)                # SCC.B 62(A6) then MOVE.W #0,D0: the consumer ends with C Clear
SCC_VALUE = {0x50f62: 'scc62', 0xd77da: 'push', 0xd7802: 'd0'}   # consumers with one successor: the C shows in the BYTE they write
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes a C in this unit
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
# 5100c BMI.W 51014 after 50ffe: D0.W := WORD 2e(A6) - WORD 2e(A6) = 0, so the N flag is never set: 51014 is reached from 50ffe only through 51010.
STATIC_IMPOSSIBLE = {(0x5100c, 0x51014)}
TRAPS = ()                              # no TRAP site in this unit
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x362c6, 0x362cc), (0x48582, 0x4858e), (0x48592, 0x48598), (0x50d08, 0x50d0e), (0x50f52, 0x50f62), (0x51044, 0x51054), (0x729e8, 0x729ee),
          (0xd77c8, 0xd77da), (0xd77ec, 0xd7802), (0xd7692, 0xd7698), (0xd76b2, 0xd76b8), (0xd7708, 0xd770e))
PASS_CHAINS = ()
TABLE_ENTRIES = ()
# callbacks and installed values (node callbacks); the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0x50dae, 0x50dd2, 0x50e42, 0x50cf6, 0x50d08, 0x50f1a, 0x50f80, 0x50f9c, 0x50ffe, 0x51076, 0xd764a, 0xd7692, 0xd76b2, 0xd7700, 0xd7766,
                0xd77ba, 0x72978, 0x729e2, 0x4fcb8, 0x4fcc4, 0x36292)
CALLEES = (0x4855c, 0x1aa66, 0x1a988, 0xe9148, 0x49c38, 0x48210, 0x19a00, 0x491fe, 0x51590, 0x515a2, 0x51178, 0x51574, 0x51608, 0x703f6, 0xe625e,
           0xe6284)
# values a direct entry pops or reads below the return LONG at A7, lowest address first: ('L'|'W', kind) with kind node / any / small
# (d77e4..d780c: the BYTE pushed by d77da / d77e0 is the high byte of the declared WORD; AND.B (A7)+ pops it with A7 += 2)
STACK = {0x515da: (('L', 'any'),), 0xd77e4: (('W', 'any'),), 0xd77ec: (('W', 'any'),), 0xd7802: (('W', 'any'),), 0xd7808: (('W', 'any'),),
         0xd780c: (('W', 'any'),)}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x72, 0x80)   # node links and pointer fields: natural or declared below
SCRIPT = 0x10fd00                       # the declared RAM sound script (LONG 80(A6)): WORD sound / WORD delay pairs
ROM_SCRIPTS = (0x50e80, 0x50e84, 0x50e88, 0x50e8c, 0x50e90)   # the natural script 50e80 (1886 0020 1887 0022 1888 0024 1888 0020 ffff)

VB = (0, 1, 2, 3, 4, 7, 8, 0x10, 0x20, 0x30, 0x7f, 0x80, 0x81, 0xf7, 0xf8, 0xfb, 0xfd, 0xfe, 0xff)
VW = (0, 1, 2, 3, 0xe, 0xf, 0x10, 0x48, 0x49, 0x4b, 0x7f, 0x80, 0x96, 0xaf, 0xb0, 0xb1, 0xff, 0x100, 0x2000, 0x270e, 0x7fff, 0x8000, 0x8001, 0xffa5,
      0xffb7, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x10, 0x800, 0x2000, 0x270e, 0x7fff, 0x8000, 0xffff, 0x10000, 0x20000, 0x7ffff800, 0x7fffffff, 0x80000000, 0xffff0000, 0xfffff800,
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
        # the pointers the unit follows: LONG c(A6) (parent: WORD 78 of 36292), LONG 80(A6) (the sound script of 50de0: a natural ROM script or the
        # declared RAM script SCRIPT), LONG 72(A6) (the A0 of 4ae4a at 703fe: 0 or a natural node)
        par = self.pointer()
        writes.append(((a6 + 0xc) & 0xffff, 4, par))
        if rng.random() < 0.6 and 0x100000 <= par + 0x78 < 0x110000 and not 0xee00 <= ((par + 0x78) & 0xffff) < 0xf000:
            writes.append(((par + 0x78) & 0xffff, 2, self.value(2)))
        writes.append(((a6 + 0x80) & 0xffff, 4, rng.choice(ROM_SCRIPTS + (SCRIPT, SCRIPT))))
        writes.append((SCRIPT & 0xffff, 2, rng.choice((0xffff, 0xffff, 0x1886, 0x7fff, 0xfffe, self.value(2)))))
        writes.append(((SCRIPT + 2) & 0xffff, 2, self.value(2)))
        writes.append(((a6 + 0x72) & 0xffff, 4, rng.choice((0, 0, self.pointer()))))
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe: BYTE 1d(A6) < 4 (>= 4 reaches the TRAP #15 8ec8)
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
        # A5 fields: BYTE 568e (4855c; 4945e -> 49370: 0 -> Set), BYTE 5683 (4855c bits 0..2, 482aa bit 4), WORD 5418 / 53ee (1aa66), WORD 5df8
        # (d764a), LONG 5734 / 5738 (49c38); absolute RAM: LONG 100bf4 (289e: 270e -> Clear), WORDs 10ddec..10ddf6 (d7714; the d75ce index WORDs
        # 10ddec / 10ddf2 small), BCD BYTEs 10de14..10de1f (e6284)
        if rng.random() < 0.5:
            writes.append(((a5 + 0x568e) & 0xffff, 1, rng.choice((0, 0, 1, 2, 3))))
        if rng.random() < 0.6:
            writes.append(((a5 + 0x5683) & 0xffff, 1, rng.choice((0, 6, 7, 0x16, 0x10, 0xff, rng.getrandbits(8)))))
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5418) & 0xffff, 2, self.value(2)))
            writes.append(((a5 + 0x53ee) & 0xffff, 2, self.value(2)))
        if rng.random() < 0.5:
            writes.append(((a5 + 0x5df8) & 0xffff, 2, rng.choice((0, 1, 2, 0x96, 0xffff))))
        for off in (0x5734, 0x5738):
            if rng.random() < 0.4:
                writes.append(((a5 + off) & 0xffff, 4, rng.choice((0, 0, 1, 0x80000000, self.pointer()))))
        if rng.random() < 0.5:
            writes.append((0x0bf4, 4, rng.choice((0x270e, 0x270e, 0, 0x2710, 0x270e0000))))
        for k in range(6):
            if rng.random() < 0.5:
                writes.append((0xddec + 2 * k, 2, rng.choice((0, 1, 2, 5, 14)) if k in (0, 3) else self.value(2)))
        for k in range(12):
            if rng.random() < 0.3:
                writes.append((0xde14 + k, 1, rng.choice((0, 0x01, 0x09, 0x10, 0x50, 0x99, rng.getrandbits(8)))))
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
            if hint.get('a5_mirror'):
                regs['a5'] = a5 | 0xf0000                       # A5 in the upper RAM mirror (1f8000 = 108000)
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
    require(len(STARTS) == 220 and len(STARTS_SET) == 220, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS:
        require(unit_of(t) is None and not mine(t), ('TRAP site must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr6_block', ('start is not routed to fr6', hex(s), unit_of(s)))
    rng = random.Random(0xF63A)
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
            if nxt in CONSUMERS and entry not in DATA_SET and entry not in SET_SET + CLEAR_SET:
                continue                                        # (51044 / 51050 set the known C of the consumer 51054 themselves)
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
    sys.stderr.write('fr6 spec: %d fixtures, visited %d/220, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out

def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr6: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr6: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts

def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries, equal-value ties at BGE / BLE / BCC / BEQ / BMI, the SUBQ / ADDQ wraps, the zero / sign extension of MOVEQ #0 + MOVE.B and EXT.L, the
    WORD index wraps of the d75ce table (negative indices), the BYTE index wrap of 515a2, the popped LONG / BYTE, the upper register bits of the WORD /
    BYTE operations, the node / parent / A5 in the upper RAM mirror, bit combinations, the BCD carries and the 9999 / 99 clamp of e6284).  Every hint
    world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d7=0x99aabbcc)
    if entry == 0x19a00:
        h += [dict(regs=dict(d0=0x12340010, d1=0x5678fff0, d7=v)) for v in (0, 0x12345600, 0xff, 0xffff0000, 0x00000100)]
    for e, field, reg, ge in ((0x19a06, 0x53d0, 'd1', 1), (0x19a12, 0x53d4, 'd1', 0), (0x19a26, 0x53ce, 'd0', 1), (0x19a32, 0x53d2, 'd0', 0)):
        if entry == e:
            h += [dict(regs={reg: r}, a5off=[(field, 2, m)]) for r, m in ((0x12340005, 5), (0x12340004, 5), (0x12340006, 5), (0x8000, 0x7fff), (0x7fff, 0x8000),
                                                                         (0xffff, 0), (0, 0xffff))]
    if entry in (0x19a0e, 0x19a1a, 0x19a2e, 0x19a3a):
        h += [dict(regs=dict(up))]
    if entry == 0x19a1e:
        h += regs('d7', (0x123400ff, 0x1234ff00, 0x00000100, 0xffff00ff, 0))
    if entry == 0x1a988:
        h += [dict(regs=dict(d0=0x12345678), a5off=[(0x5432, 2, a), (0x53c0, 2, b), (0x53a6, 2, c)]) for a, b, c in ((0x8000, 0x8000, 1), (0xffff, 1, 0),
                                                                                                            (0x7fff, 1, 0), (1, 2, 3))]
    if entry == 0x1aa66:
        h += [dict(regs=dict(d0=0x12345678), a5off=[(0x5418, 2, a), (0x53ee, 2, b)]) for a, b in ((5, 5), (5, 6), (6, 5), (0x8000, 0x7fff), (0x7fff, 0x8000),
                                                                                                (0, 0), (0xffff, 0))]
        h += [dict(a5_mirror=True, a5off=[(0x5418, 2, 5), (0x53ee, 2, 5)])]
    if entry == 0x36292:
        h += [dict(regs=dict(d0=0x12345678), parent=[(0x78, 2, v)]) for v in (0, 0x8000, 0xffff)]
        h += [dict(parent_mirror=True, parent=[(0x78, 2, 1)])]
    if entry == 0x362a0:
        h += regs('d1', (0x100, 1, 0x80, 0xffffff00, 0))
    if entry == 0x362b2:
        h += byte(0x76, (0, 1, 0x80, 0xff))
    if entry == 0x362ba:
        h += byte(0x76, (1, 0, 2, 0x81))
        h += [dict(mirror=True, a6off=[(0x76, 1, 1)])]
    if entry in (0x48210, 0x4821c):
        h += [dict(regs=dict(d0=d, d1=0x9abcdef0), a5off=[(0x5694, 1, 0x80), (0x569c, 1, 0xff)]) for d in (0x12340001, 0x12340000, 0xfffe, 0xffffffff, 0x10000)]
    if entry == 0x48220:
        h += [dict(regs=dict(d1=0x9abcdef0), a0off=[(0, 1, v)]) for v in (0, 0x80, 0xff)]
    if entry == 0x4855c:
        h += [dict(a5off=[(0x568e, 1, v), (0x5683, 1, 6)]) for v in (0, 1, 0x80, 0xff)]
    if entry in (0x48564, 0x4856e, 0x48578):
        h += [dict(a5off=[(0x5683, 1, v)]) for v in (0, 1, 2, 3, 4, 5, 6, 7, 0xf6, 0xff)]
        h += [dict(a5_mirror=True, a5off=[(0x5683, 1, 6)])]
    if entry == 0x48582:
        h += [dict(regs=dict(up), writes=[(0x0bf4, 4, v)]) for v in (0x270e, 0x270f, 0x270e0000)]
    if entry == 0x491fe:
        h += regs('a0', (0, 0xffffffd0, 0x7fffffe0, 0x10e000))
    if entry == 0x4920e:
        h += regs('a0', (0x2d, 0, 0x80000010, 0x10e02e))
    if entry == 0x49c38:
        h += [dict(regs=dict(d0=d), a5off=[(0x5734, 4, a), (0x5738, 4, b)]) for d, a, b in ((0, 0, 1), (1, 0, 1), (0xffff0001, 1, 0), (0x12340003, 0, 0x80000000),
                                                                                         (0x10000, 0x00010000, 0), (2, 0x100, 0))]
        h += [dict(a5_mirror=True, regs=dict(d0=1), a5off=[(0x5734, 4, 0), (0x5738, 4, 0x8000)])]
    if entry in (0x4fcb8, 0x4fcc4, 0x50dfc, 0x50e22, 0x50e6e, 0x50ee4, 0x50ef6, 0x50f52, 0x50fb2, 0x50fde, 0x51178, 0x51188, 0x7040c, 0xd764a, 0xd765e,
                 0xd766c, 0xd77aa, 0x50e94, 0x50ea4, 0x50fbc, 0x50e06, 0xd7766, 0xd7780):
        h += [dict(regs=dict(up))]
    if entry in (0x50cf6, 0x50eb8, 0x50ed8, 0x50fcc):
        h += [dict(a6off=[(0x15, 1, v), (0x7e, 1, v ^ 0xff)]) for v in (0, 1, 0xfe, 0xff, 4, 0xfb)]
        h += [dict(mirror=True, a6off=[(0x15, 1, 0xff)])]
    if entry == 0x50d12:
        h += byte(0xa1, (0, 1, 0xff, 0xfe, 0x80))
    if entry == 0x50dae:
        h += [dict(a6off=[(0x1a, 1, a), (0x7e, 1, b), (0x8c, 2, 0x1234), (0x80, 4, 0)]) for a, b in ((0x80, 0xff), (0, 4), (0xff, 0))]
    if entry == 0x50dd2:
        h += word(0x8c, (0, 1, 0x8000, 0xffff))
        h += [dict(mirror=True, a6off=[(0x8c, 2, 0)])]
    if entry == 0x50dda:
        h += word(0x8c, (0, 1, 0x8000))
    if entry == 0x50de0:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x80, 4, SCRIPT)], writes=[(SCRIPT & 0xffff, 2, w0), ((SCRIPT + 2) & 0xffff, 2, w1)])
              for w0, w1 in ((0xffff, 1), (0xfffe, 0x20), (0x7fff, 0), (0x1886, 0xffff))]
        h += [dict(a6off=[(0x80, 4, a)]) for a in ROM_SCRIPTS]
    if entry == 0x50dee:
        h += [dict(regs=dict(a0=SCRIPT + 2), writes=[((SCRIPT + 2) & 0xffff, 2, v)]) for v in (0, 0x20, 0xffff)]
    if entry in (0x50e42, 0x50f1a):
        h += [dict(regs=dict(d2=0x12345678), a6off=[(0x8c, 2, v)]) for v in (0x2000, 0xff80, 0x0080, 0)]
    if entry == 0x50e52:
        h += long_(0x3a, (0xfffff800, 0x7ffff800, 0, 0xffff0000))
    if entry in (0x50e60, 0x50f44):
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x8e, 2, a), (0x8c, 2, b)]) for a, b in ((0xffb7, 0x2000), (0xffb7, 0x49), (0xffb7, 0x48), (1, 0x7fff),
                                                                                            (0x8000, 0x8000), (0xffa5, 0x5b), (0xffa5, 0x5a))]
    if entry == 0x50ed0:
        h += regs('d0', (0x12345601, 0x12345600, 0xfe, 0xff00ff01, 0x100))
    if entry == 0x50f2a:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x1e, 2, 0x8000)])]
    if entry == 0x50f86:
        h += byte(0x62, (0, 0xff, 1, 0x80))
    if entry == 0x50fa2:
        h += byte(0x8c, (1, 0, 2, 0x80))
    if entry == 0x50ffe:
        h += [dict(regs=dict(up), a6off=[(0x2e, 2, v)]) for v in (0, 0x8000, 0x7fff, 0xffff)]
    if entry in (0x51010, 0x5102e):
        h += regs('d0', (0x1234fff1, 0x12347ff1, 0xffffffff))
    if entry in (0x51020, 0x51040):
        h += regs('d1', (0x1234fff1, 0x12347ff1, 0xffffffff))
    if entry == 0x51014:
        h += [dict(regs=dict(d0=a, d1=0x123400b0, d3=0x55667788), a6off=[(0x32, 2, b)]) for a, b in ((0x12348000, 0xb0), (0x7fff, 0xaf), (0xfff0, 0xb1),
                                                                                                    (0xf, 0x80b0), (0x10, 0x30))]
    if entry == 0x51024:
        h += [dict(regs=dict(d0=a, d1=b), a6off=[(0x36, 2, c)]) for a, b, c in ((0, 0x8000, 0), (0, 0xffff, 1), (0x12340000, 0x7fff, 0xffff), (5, 0xf0, 0x8000),
                                                                             (0, 0x10, 0x7fff))]
    if entry == 0x51032:
        h += [dict(regs=dict(d0=a, d1=b), a6off=[(0x36, 2, c), (0x3a, 2, d)]) for a, b, c, d in ((0x7ff0, 0x10, 0x7fff, 0x10), (0x8000, 0, 0x8000, 0),
                                                                                              (0xfff1, 0xffff, 1, 0xffff), (0x1234000f, 5, 0, 0x8000))]
    if entry == 0x51044:
        h += [dict(regs=dict(d1=a, d2=b, d3=c), a6off=[(0x3a, 2, d)]) for a, b, c, d in ((0x10, 0xff, 0xff, 0x7fff), (0x7ff0, 0xff, 0, 0x7fff),
                                                                                      (0x8000, 0, 0xff, 0x8000), (0, 0x12345680, 0x9abcde01, 0),
                                                                                      (0xfff0, 0x123456ff, 0x9abcdeff, 1))]
    if entry == 0x51050:
        h += [dict(regs=dict(up))]
    if entry == 0x5106a:
        h += [dict(a6off=[(0xa4, 1, 0xff), (0xa5, 1, 0x5a)])]
    if entry == 0x5107e:
        h += byte(0xa3, (0, 1, 0xff))
    if entry == 0x51086:
        h += byte(0x9c, (0, 1, 0x80))
    if entry in (0x5109a, 0x510ae):
        h += regs('d0', (0x123456ff, 0x80, 0))
    if entry == 0x510b6:
        h += byte(0xa4, (1, 0, 2))
    if entry == 0x510c8:
        h += byte(0xa3, (0, 1, 0x80))
    if entry == 0x51192:
        h += [dict(regs=dict(d0=a, d1=0x9abcdef0)) for a in (0x1234fe66, 0x7e66, 0xfe65)]
    if entry == 0x511a2:
        h += regs('d0', (0x1234fff0, 0xfff5, 0x7ff0))
    if entry == 0x5157a:
        h += byte(0x61, (0, 0x7f, 0x80, 0xff))
        h += [dict(mirror=True, a6off=[(0x61, 1, 0x80)])]
    if entry in (0x51590, 0x5158a):
        h += [dict(regs=dict(up), a6off=[(0x1e, 2, 0x8000), (0x5e, 1, 0xff)])]
    if entry == 0x515a2:
        h += [dict(regs=dict(up), a6off=[(0xa2, 1, a), (0x3a, 4, 0x12345678)]) for a in (0, 0xf7, 0xf8, 0xff, 0x80, 0x40)]
        h += [dict(mirror=True, a6off=[(0xa2, 1, 0xfc)])]
    if entry == 0x515da:
        h += [dict(a6off=[(0x3a, 4, 0x11111111)], stack=[(4, v)]) for v in (0x80000000, 0, 0x12345678)]
    if entry == 0x703f6:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x72, 4, v)]) for v in (0, 0x100, 0x01000000, 0x10000)]
        h += [dict(mirror=True, a6off=[(0x72, 4, 0)])]
    if entry == 0x70406:
        h += regs('d0', (0x100, 1, 0xffffff00, 0x80, 0))
    if entry == 0x72978:
        h += word(0x9c, (0, 1, 0x8000))
        h += [dict(regs=dict(up), mirror=True, a6off=[(0x9c, 2, 1)])]
    if entry in (0x72980, 0x729ac):
        h += [dict(regs=dict(up), a6off=[(0x22, 4, 0x12345678)])]
    if entry == 0x729fc:
        h += byte(0x15, (0, 0x7f, 0x80, 0xff))
    if entry == 0xd767a:
        h += [dict(a6off=[(0x19, 1, v)]) for v in (0, 0x80, 0xff)]
    if entry in (0xd769c, 0xd76bc, 0xd7700):
        h += [dict(a5off=[(0x5df8, 2, v)]) for v in (0, 1, 0x8000, 0xffff)]
        h += [dict(a5_mirror=True, a5off=[(0x5df8, 2, 0)])]
    if entry == 0xd76a6:
        h += [dict(a5off=[(0x5418, 4, v)]) for v in (0x12345678, 0x80000000)]
    if entry == 0xd76c4:
        h += [dict(regs=dict(up), a5off=[(0x5df8, 2, a), (0x5418, 2, b)], a6off=[(0x76, 2, c)]) for a, b, c in ((0, 5, 5), (1, 5, 6), (2, 0x8000, 0),
                                                                                                         (0x8000, 0xffff, 0xffff))]
    if entry == 0xd76e6:
        h += regs('d0', (0, 0x10000, 1, 0xffff0000))
    if entry == 0xd7714:
        h += [dict(regs=dict(up), writes=[(0xddec, 2, a), (0xddf2, 2, b), (0xddee, 2, 0x8000), (0xddf4, 2, 0x7fff)]) for a, b in ((0, 1), (1, 14), (2, 0xffff),
                                                                                                                             (0, 0x4001), (0x3fff, 0))]
    if entry == 0xd7766:
        h += [dict(regs=dict(up), a6off=[(0x78, 2, v)]) for v in (0, 1, 14, 0xffff, 0x4001, 0x3fff)]
    if entry == 0xd7780:
        h += [dict(regs=dict(up), a6off=[(0x7e, 2, v)]) for v in (0, 2, 14, 0xffff, 0x4002)]
    if entry == 0xd779e:
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x78, 2, a), (0x7e, 2, b)]) for a, b in ((0, 0), (0, 1), (0x8000, 0), (0xff, 0xff00))]
    if entry in (0xd77c0, 0xd77e4):
        h += [dict(a6off=[(0x78, 2, v), (0x7e, 2, v)]) for v in (0, 1, 0x8000)]
    if entry in (0xd77c8, 0xd77ec):
        h += [dict(a6off=[(0x7a, 2, 0x8000), (0x7c, 2, 0xffff), (0x80, 2, 0x7fff), (0x82, 2, 1)])]
    if entry == 0xd7808:
        h += regs('d0', (0x12345600, 0xffffff00))
    if entry == 0xd780c:
        h += [dict(regs=dict(d0=d), stack=[(2, v)]) for d, v in ((0x123456ff, 0xff00), (0x123456ff, 0x0000), (0x12345680, 0x8000), (0x123456ff, 0x00ff),
                                                                 (0x12345600, 0xffff))]
    if entry == 0xd7812:
        h += byte(0x8c, (1, 2, 0))
    if entry == 0xe625e:
        h += regs('d0', (0, 1, 2, 3, 0xfffffffc, 0x100))
    if entry in (0xe6270,):
        h += regs('d0', (2, 0xfffffffd, 0x12345601))
    if entry == 0xe6284:
        for src, dst in (((0x99, 0x99), (0x99, 0x99, 0x99, 0x99)), ((0x00, 0x01), (0x00, 0x00, 0x99, 0x99)), ((0x12, 0x34), (0x00, 0x00, 0x00, 0x00)),
                         ((0xfa, 0xaf), (0x09, 0x9a, 0xa9, 0x90)), ((0x50, 0x50), (0x99, 0x99, 0x49, 0x50))):
            h += [dict(regs=dict(a1=0x10de18, d0=0x12345678), a0off=[(0, 1, src[0]), (1, 1, src[1])],
                       writes=[(0xde14 + k, 1, dst[k]) for k in range(4)])]
    if entry == 0xe629c:
        h += [dict(regs=dict(up, a1=0x10de14))]
    if entry == 0xe9148:
        h += [dict(regs=dict(d0=0x12345678), a5off=[(0x5e3c, 1, v)]) for v in (0, 0x80, 0xff)]
    return h


def chain_hint(entry, t, rng):
    """Edits that let the real producer of a chain return both C values."""
    pass4855c = dict(a5off=[(0x568e, 1, 1), (0x5683, 1, 6), (0x5418, 2, 1), (0x53ee, 2, 2)], writes=[(0x0bf4, 4, 0x2710)])
    if entry == 0x362c6:
        return dict(a5off=[(0x5683, 1, (0x10, 0, 0xff, 0xef)[t % 4])])                                     # 482aa: BTST #4,5683(A5): 1 -> Clear, 0 -> Set
    if entry == 0x48582:
        return dict(writes=[(0x0bf4, 4, (0x270e, 0x270f, 0, 0x270e0000)[t % 4])])                           # 289e: LONG (100bf4) = 270e -> Clear
    if entry == 0x48592:
        a, b = ((5, 5), (5, 6), (6, 5), (0x8000, 0x7fff))[t % 4]
        return dict(a5off=[(0x5418, 2, a), (0x53ee, 2, b)])                                                 # 1aa66: 5418 >= 53ee (unsigned) -> Set
    if entry == 0x50d08 and t % 2:
        return dict(a5off=[(0x568e, 1, (0, 1, 2, 3)[(t // 2) % 4])])                                        # 4945e -> 49370: BYTE 568e(A5) = 0 -> Set
    if entry == 0x50f52 and t % 2:
        return dict(writes=[(0x4ca0, 2, (0, 0xa, 0xb, 0x40)[(t // 2) % 4])])                                # 28ae: WORD 104ca0 <= D0 (a) -> 290e Clear
    if entry == 0x51044:
        b, c = ((0xff, 0xff), (0xff, 0), (0, 0xff), (0x80, 0x80))[t % 4]
        return dict(regs=dict(d2=b, d3=c))                                                                  # AND.B D3,D2 = 0 -> 51054 (Clear) / 51050 (Set)
    if entry in (0x729e8, 0xd77c8) and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                                                   # 49fc6: LONG 26(A6) = 0 -> ORI Set
    if entry == 0xd77ec and t % 2:
        return dict(a6off=[(0x84, 4, 0)])                                                                   # 49fca (A0 = A6 + 84): LONG (A0) = 0 -> Set
    if entry in (0xd7692, 0xd76b2, 0xd7708):
        if t % 2:
            return pass4855c                                                                                # every condition of 4855c holds -> Set
        k = (t // 2) % 4
        fail = (dict(a5off=[(0x568e, 1, 0)]), dict(a5off=[(0x568e, 1, 1), (0x5683, 1, 7)]), dict(a5off=[(0x568e, 1, 1), (0x5683, 1, 6)],
                                                                                                    writes=[(0x0bf4, 4, 0x270e)]),
                dict(a5off=[(0x568e, 1, 1), (0x5683, 1, 6), (0x5418, 2, 3), (0x53ee, 2, 2)], writes=[(0x0bf4, 4, 0x2710)]))[k]
        return fail
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run.  The SCC / SCS
    consumers (one successor) are kept per native C value (the C at the stop: SR bit 0 for d77da / d7802; 50f62 clears C with MOVE.W, so its chain is
    also run to the consumer itself, where the carry oracle compares the C++ tag of the 28ae C with the native C)."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d)] + [(6, 0x26, 4), (6, 0x84, 4)]
        succ = static_next(cons)
        variants = [(tuple(sorted(succ)), 'succ')]
        if cons == 0x50f62:
            variants.append(((cons,), 'at'))
        for extra, tag in variants:
            kept = {}
            for t in range(MAX_TRIES * 2):
                st = world.make(entry, SENTINEL, flds, chain_hint(entry, t, rng))
                tr = trace(st, first_unrouted(extra=extra), cap=400000)
                if tr is None or (tag == 'succ' and cons not in tr['pcs']) or (tag == 'at' and tr['stop'] != cons):
                    continue
                record(tr['pcs'] + [tr['stop']])
                key = (tr['stop'], tr['sr'] & 1) if (cons in SCC_VALUE and cons != 0x50f62) or tag == 'at' else tr['stop']
                if key not in kept:
                    kept[key] = (st, tr)
                stops = set(k[0] if isinstance(k, tuple) else k for k in kept)
                if stops >= set(extra) and (not isinstance(key, tuple) or len(kept) >= 2):
                    break
            require(kept, ('no chain world', hex(entry), tag))
            if tag == 'succ':
                missing = succ - set(k[0] if isinstance(k, tuple) else k for k in kept)
                if missing:
                    out_missing.append((cons, sorted(missing)))
            for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
                add(U.Fixture('chain-%05x-to-%05x-%s%d' % (entry, cons, '' if tag == 'succ' else 'at', i), st, [], tr['stop'],
                              meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'], c=tr['sr'] & 1)))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # 8ebe: BYTE 1d(A6) < 4 (>= 4 reaches the untraceable TRAP #15 8ec8); WORD 8c (50dd2 countdown, the 8c / 8e growth), BYTE 62 (50f86), WORDs
            # 78 / 7e (d77c0 / d77e4 / d779e and the d75ce indices), WORD 5df8(A5) (d769c / d7700), every condition of 4855c on every other try
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x8c, 2, (0, 1, 0x48, 0x2000)[(t // 4) % 4]), (0x62, 1, (0, 1)[(t // 2) % 2]),
                               (0x78, 2, (0, 1)[(t // 8) % 2]), (0x7e, 2, (0, 2)[(t // 16) % 2])],
                        a5off=[(0x5df8, 2, (0, 1)[(t // 2) % 2])] + ([(0x568e, 1, 1), (0x5683, 1, 6), (0x5418, 2, 1), (0x53ee, 2, 2)] if t % 2 else []),
                        writes=[(0x0bf4, 4, 0x2710)] if t % 2 else [])
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr6 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x50daf), 'unaligned animation machine PC', 0x50daf)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr6 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    nd = base.state['regs']['a6']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: TST.W 8c(A6) of 50dd2 (read), MOVE.W #ffe2,7a(A6) of 4fcb8 (write); odd stack: MOVE.L (A7)+ of 515da; odd script pointer: MOVE.W (A0)+
    # of 50de0 (LONG 80(A6) odd); odd A1: MOVE.W #9999,(A1) of e629c
    err('50dd2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x50dd2), odd_word, 0x50dd2, stop=0x50de0)
    err('4fcb8-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x4fcb8), odd_write, 0x4fcb8, stop=0x4fcc4)
    err('515da-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x515da), odd_word, 0x515da)
    err('50de0-odd-script', U.with_host_writes(st, [((nd + 0x80) & 0xffff, 4, 0x50e81)], pc=0x50de0), odd_word, 0x50de0, stop=0x50dee)
    err('e629c-odd-a1', U.with_host_writes(st, regs=dict(a1=0x10de15), pc=0xe629c), odd_write, 0xe629c, stop=0xe62a6)
    # failures after executed blocks:
    #   19a00 (D7 = 0) -> 19a1e (D7.W & ff00 = 0) -> 19a3e RTS at an odd A7
    err('19a00-then-19a3e', U.with_host_writes(st, regs=dict(d7=0, a7=a7 + 1), pc=0x19a00), odd_word, 0x19a3e)
    #   4855c (BYTE 568e(A5) = 0) -> 485a2 ANDI; RTS at an odd A7
    err('4855c-then-485a2', U.with_host_writes(st, [((st['regs']['a5'] + 0x568e) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x4855c), odd_word, 0x485a2)
    #   d76f4 (5df8 := 1, (A6) := d7700) -> d7700 (5df8 != 0) -> d7708 JSR 4855c at an odd A7
    err('d76f4-then-d7708', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xd76f4), odd_word, 0xd7708, stop=0x4855c)
    #   50e34 ((A6) := 50e42, enters it) -> 50e42 BSR 51608 at an odd A7
    err('50e34-then-50e42', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x50e34), odd_word, 0x50e42, stop=0x51608)
    #   e625e (D0 bit 0) -> e6266 BSR e6284 at an odd A7
    err('e625e-then-e6266', U.with_host_writes(st, regs=dict(d0=1, a7=a7 + 1), pc=0xe625e), odd_word, 0xe6266, stop=0xe6284)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x515a2, 0xe6284, 0x51044, 0xd7714)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
