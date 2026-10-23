"""V1 fixture spec of the animation-machine unit FR2b (engine/src/animation_machine_objects_fr2b.cpp, 214 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr2b-contract.md): the IO-frontier roots of the FR2a IO rerun 48256 (stage BYTE helper),
76852 (U09 28ae child; install 768b6, the tail 70674 / 70764 with the install 718c8 and 702cc), b336a (FR1b 28ae child; install b33bc), the card-menu
handlers a92a / a8d0 (a8dc 9ef2 bb6), and their natural successors: the install 70c0c (70c76) with 70302 (702f0) / 70606, the 28ae child 76944
(install 76984) with its makers 769ac / 769b2 / 769f4, the U01 install chain dd574..dd69c, the FR1c child bc844 up to bc93c (bc8b6 bc8f2 bc924) and the
terrain helper 4c2cc.

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR2a) with declared host edits.  The real entry
states of this unit are the confirmed frontier frames of the FR2a IO rerun (ms5-scratch/fr2/ioA/frontier.json: P1 / P1b frame 325 node 100f5c
e525a -> 48256, frame 133 node 101eac 76852, frame 120 node 101eac b336a, boot-title-start frame 117 a92a); this spec does not decode the IO packs
(the IO comparison rerun checks the natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the ten consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node, LONG
            c(A6) / 3e(A6) := a natural node, LONG 7e(A6) := a position in the WORD-pair list 76a1c..76aa0, the node / parent / A5 fields the reachable
            blocks read, the stack BYTE / WORD / LONG values the entered block pops, PC := the block start).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 494c0 (702f0) -> 7031e (7031c), 497a6 -> 7686e (76862), 288c -> 76938 (76932), 49fc6 ->
            769a0 (7699a) / bc930 (bc92a), 7054c -> 70cf8 (70cf4), 705ca -> 70d06 (70d02), 7028e -> 70d14 (70d10), 70606 -> 70d4c (70d48), 46d72 ->
            4c2e8 (4c2d0); the passing RTS 4c2ec (4c2cc) runs to the sentinel.  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the ten consumers, odd node / list / stack pointers, failures after
            executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry
            and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR2a specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR2a)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
LIST, LIST_END = 0x76a1c, 0x76aa0       # the WORD pairs 768b6 walks (LONG 7e(A6))
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0xbb6, 0xbbe), (0x9ef2, 0x9ef8), (0xa8d0, 0xa8ee), (0xa92a, 0xa952), (0x48256, 0x48262), (0x4c2cc, 0x4c2fa), (0x702cc, 0x702fa),
          (0x70302, 0x703f6), (0x70606, 0x7062a), (0x70674, 0x7086a), (0x70c0c, 0x70d72), (0x718c8, 0x718ec), (0x76852, 0x76922), (0x76926, 0x769fc),
          (0xb336a, 0xb33d8), (0xbc844, 0xbc93c), (0xdd574, 0xdd6b2)]
STARTS = [int(x, 16) for x in (
    'bb6 9ef2 a8d0 a8d4 a8dc a8e4 a8ec a92a a92e a930 a938 a93a a94a a950 48256 4c2cc 4c2d0 4c2e8 4c2ec 4c2ee 702cc 702f0 '
    '70302 7030a 70314 7031c 7031e 70322 70330 70334 7033e 70346 70350 70362 70364 7036a 70394 703a8 703b2 703bc 703c6 703d0 703da 703e4 703ee '
    '703f0 703f4 70606 70616 7061e 70624 '
    '70674 7067c 70686 7068c 70698 706a0 706c8 706cc 706f4 706fe 70706 7072e 70732 7075a 70760 70764 7076c 70776 7077c 70788 707b0 707b4 707dc '
    '707e2 707f0 707fa 70800 70806 70832 7085c 70860 '
    '70c0c 70c14 70c3c 70c40 70c68 70c76 70c80 70c86 70c8c 70c96 70cb0 70cb2 70cba 70cc0 70cc6 70cce 70cd4 70cd8 70ce0 70ce6 70cee 70cf4 70cf8 '
    '70cfc 70d02 70d06 70d0a 70d10 70d14 70d18 70d1e 70d22 70d36 70d38 70d42 70d48 70d4c 70d50 70d5a 70d60 70d68 70d6e '
    '718c8 718cc 718d2 718dc 718e8 '
    '76852 7685c 76862 7686e 76872 76880 76884 76892 768a8 768b6 768cc 768da 768dc 768ee 768f4 768f8 768fe 76904 7690a 76916 '
    '76926 76932 76938 7693c 76942 76944 76952 76974 76984 7699a 769a0 769a4 769aa 769ac 769b2 769b4 769c8 769d8 769da 769e0 769e6 769ec 769f2 769f4 '
    'b336a b3388 b33b0 b33bc b33c2 b33c8 b33d0 b33d6 '
    'bc844 bc85c bc884 bc8b6 bc8c0 bc8c6 bc8ca bc8d0 bc8dc bc8e4 bc8ea bc8f0 bc8f2 bc91e bc924 bc92a bc930 bc934 bc93a '
    'dd574 dd5a6 dd5ba dd5c0 dd5c6 dd5f8 dd60c dd612 dd618 dd64a dd65e dd664 dd66a dd69c').split()]
CONSUMERS = (0x7031e, 0x7686e, 0x76938, 0x769a0, 0xbc930, 0x70cf8, 0x70d06, 0x70d14, 0x70d4c, 0x4c2e8)
CLEAR_SET = (0x70624,)                  # ANDI.B #fe,CCR; RTS: known C Clear
SET_SET = (0x7061e, 0x4c2ee)            # ORI.B #1,CCR; RTS: known C Set
DATA_SET = ()
INVERT_SET = ()
PASS_SET = (0x4c2ec,)                   # RTS that keeps the incoming C (carry preserving, not a consumer)
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x7031c, 0x7031e), (0x76862, 0x7686e), (0x76932, 0x76938), (0x7699a, 0x769a0), (0xbc92a, 0xbc930), (0x70cf4, 0x70cf8), (0x70d02, 0x70d06),
          (0x70d10, 0x70d14), (0x70d48, 0x70d4c), (0x4c2d0, 0x4c2e8))
PASS_CHAINS = ((0x4c2cc, 0x4c2ec),)
TABLE_ENTRIES = (0x768b6,)              # LONG 7e(A6): the position in the WORD-pair list 76a1c..76aa0
# callbacks and installed values (node callbacks); the callee entries
NODE_ENTRIES = (0x76852, 0x768b6, 0x718c8, 0x70c0c, 0x70c76, 0x76944, 0x76984, 0xb336a, 0xb33bc, 0xdd574, 0xdd5a6, 0xdd5c6, 0xdd5f8, 0xdd618, 0xdd64a,
                0xdd66a, 0xdd69c, 0xbc844, 0xbc8b6, 0xbc8f2, 0xbc924)
CALLEES = (0x48256, 0xa92a, 0xa8d0, 0xa8dc, 0x9ef2, 0xbb6, 0x70302, 0x70606, 0x702cc, 0x702f0, 0x769ac, 0x769b2, 0x769f4, 0x4c2cc, 0x70674, 0x70764)
# values a direct entry pops (below the return LONG at A7): ('L'|'W'|'B', kind) with kind node / any / small; 'B' = a BYTE in the high half of a WORD slot
STACK = {0x70362: (('W', 'any'),), 0x769c8: (('L', 'node'), ('B', 'any')), 0x769d8: (('B', 'any'),), 0x769da: (('B', 'any'),), 0x769e0: (('B', 'any'),),
         0x769e6: (('B', 'any'),), 0x70832: (('B', 'any'), ('B', 'any'))}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x3e, 0x7e)     # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xe2, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x17, 0x18, 0x2f, 0x30, 0x47, 0x48, 0x7f, 0x80, 0xe0, 0xff, 0x100, 0x127, 0x128, 0x1e0, 0x7fff, 0x8000, 0x8001,
      0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 0x10, 0x7fff, 0x10000, 0x30000, 0x60000, 0x8a9ffff, 0x8aa0000, 0x148fffff, 0x14a00000, 0x7fffffff, 0x80000000, 0xfff00000, 0xfffa0000,
      0xfffe0000, 0xffff0000, 0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {}                        # no computed jump in this unit (70d22 reads a LONG table and writes it as the callback)

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
        # the pointers the unit follows: LONG c(A6) (parent: BYTE 89 / 62), LONG 3e(A6) (4c2d0 -> 46d72), LONG 7e(A6) (the 768b6 list position)
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        writes.append(((a6 + 0x3e) & 0xffff, 4, self.pointer() if rng.random() < 0.8 else 0))
        if entry in TABLE_ENTRIES or rng.random() < 0.3:
            writes.append(((a6 + 0x7e) & 0xffff, 4, rng.choice((LIST, LIST + 4, LIST_END - 8, LIST_END - 4, LIST + 4 * rng.randrange(33)))))
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
        # the parent fields BYTE 89 (7690a) / 62 (bc8d0), the 497a6 flag BYTE 10fd92, the BYTE 100014 (bb6)
        if rng.random() < 0.5:
            writes.append((0xfd92, 1, rng.choice((0, 1, 0x80))))
        # stack values popped by the entered block (declared), the return LONG above them
        pops = []
        for size, kind in STACK.get(entry, ()):
            v = {'node': self.pointer(), 'a6': a6, 'small': rng.choice((0, 1, 2, 3)), 'any': self.value(4 if size == 'L' else (2 if size == 'W' else 1))}[kind]
            if size == 'B':
                pops.append((2, (v << 8) | rng.getrandbits(8)))            # a BYTE pushed with -(A7): the high half of the WORD slot
            else:
                pops.append((4 if size == 'L' else 2, v))
        depth = sum(n for n, v in pops)
        at = sp - depth
        for n, v in pops:
            writes.append((at & 0xffff, n, v))
            at += n
        regs['a7'] = sp - depth
        writes.append((sp & 0xffff, 4, ret))
        if entry in (0x769c8,):
            regs['a1'] = self.pointer()
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
        state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        if hint and hint.get('parent'):
            ram = state['ram']
            par = (ram[(a6 + 0xc) & 0xffff] << 24) | (ram[(a6 + 0xd) & 0xffff] << 16) | (ram[(a6 + 0xe) & 0xffff] << 8) | ram[(a6 + 0xf) & 0xffff]
            if 0x100000 <= par < 0x110000:
                state = U.with_host_writes(state, [((par + off) & 0xffff, size, val) for off, size, val in hint['parent']])
        if hint and hint.get('popped'):
            # 769c8: the WORD pair behind the popped A1 (the LONG just below the return LONG)
            ram = state['ram']
            p = state['regs']['a7']
            a1 = (ram[p & 0xffff] << 24) | (ram[(p + 1) & 0xffff] << 16) | (ram[(p + 2) & 0xffff] << 8) | ram[(p + 3) & 0xffff]
            if 0x100000 <= a1 < 0x110000 and not a1 & 1:
                state = U.with_host_writes(state, [((a1 + 2 * k) & 0xffff, 2, v) for k, v in enumerate(hint['popped'])])
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
    require(len(STARTS) == 214 and len(STARTS_SET) == 214, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    # bc93c (FR2b stop install) became an FR3 block start: the check uses the FR2b stop install 70e2a instead (FR3 contract decision 6).
    # FR10 refresh: 70e2a became an FR10 block start (FR10 contract, affected tests): the list was (702fa, 70d72, 76922, 71884, 70e2a); the remaining
    # unrouted FR2b stop install is 71884.
    for t in (0x702fa, 0x70d72, 0x76922, 0x71884):
        require(unit_of(t) is None and not mine(t), ('data / stop PC must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr2b_block', ('start is not routed to fr2b', hex(s), unit_of(s)))
    rng = random.Random(0xF42B)
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
    sys.stderr.write('fr2b spec: %d fixtures, visited %d/214, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr2b: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr2b: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries, the zero / sign extension of WORD indices, the unsigned LONG limits).  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry == 0x48256:
        h += [dict(a5off=[(-0x7453, 1, v)], regs=dict(d0=0x12345600)) for v in (0, 0x7f, 0xfe, 0xff)]
    if entry == 0x9ef2:
        h += [dict(a5off=[(-0xe6, 1, v)], regs=dict(d0=0x12345678)) for v in (0, 0x80, 0xff)]
    if entry == 0xbb6:
        h += [dict(regs=dict(d0=d), writes=[(0x0014, 1, v)]) for d, v in ((0x12345680, 0x01), (0, 0x5a), (0xff, 0))]
    if entry in (0xa8d4, 0xa8dc, 0xa8e4, 0xa930):
        h += regs('d0', (0, 1, 3, 4, 0x10003, 0xffff0004, 0x12340001))
    if entry == 0x4c2d0:
        h += regs('d0', (0x8000, 0xffff, 0x12345678))
    if entry == 0x4c2ee:
        h += regs('d6', (0x80000000, 0x00010000, 0xffff0000, 0x12345678))
    if entry == 0x702cc:
        h += [dict(a6off=[(0x64, 4, a), (0x36, 4, b), (0x3a, 4, c)]) for a, b, c in
              ((0, 0, 0), (0x80000000, 0x7fffffff, 0xfff00000), (0x7fffffff, 0x80000000, 0), (0x1f, 0, 0xffefffff), (0, 0x20, 0x7fffffff))]
    if entry == 0x70302:
        h += word(0x78, (0, 1, 0x8000))
    if entry == 0x7030a:
        h += byte(0x82, (0, 8, 0xf7, 0xff))
    if entry == 0x70314:
        h += byte(0x86, (0, 0x7f, 0x80, 0xff))
    if entry == 0x70322:
        h += [dict(a6off=[(0x87, 1, b), (0x15, 1, f)]) for b in (0, 0xff, 2, 0xfd) for f in (0, 0x80)]
    if entry == 0x70330:
        h += regs('d1', (0xff, 0x12345602, 0xfffffffd))
    if entry in (0x70334, 0x70346):
        h += byte(0x82, (0, 2, 0x40, 0x42, 0xff))
    if entry == 0x7033e:
        h += regs('d1', (0, 2, 0xfd, 0x12345602, 0xfffffffd))
    if entry == 0x70364:
        h += regs('d1', (0, 0x100, 1, 0xffffff00))
    if entry == 0x7036a:
        h += regs('d1', (0xff, 0x80, 1, 0x123456a5, 0))
    if entry == 0x70394:
        h += [dict(a6off=[(0x87, 1, b)], regs=dict(d0=d)) for b in (0, 1, 0x80, 0xff, 0x55) for d in (0, 1, 7, 8, 0x12340003)]
    if entry in (0x703a8, 0x703b2, 0x703bc, 0x703c6, 0x703d0, 0x703da, 0x703e4):
        h += [dict(regs=dict(d1=a, d2=b, d3=c)) for a, b, c in ((0, 0x80, 0), (1, 0x80, 0), (0, 0x7f, 0), (0x8000, 0xff, 1), (0, 0, 0xffff), (5, 0x80, 0xffff))]
    if entry in (0x703ee, 0x703f0):
        h += regs('d0', (0, 0x12340000))
    if entry == 0x70606:
        h += word(0x42, (0x17, 0x18, 0x127, 0x128, 0x8000, 0xffff))
    if entry == 0x70616:
        h += byte(0x86, (0x7f, 0x80))
    if entry in (0x70674, 0x70764, 0x707e2):
        h += word(0x70, (0, 1, 0x8000))
    if entry == 0x7068c:
        h += byte(0x6a, (0, 1, 0x80))
    if entry in (0x70698, 0x706fe, 0x7077c, 0x70c0c):
        h += word(0x9c, (0, 1, 0x8000))
    if entry == 0x70832:
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x70c8c:
        h += byte(0x6e, (2, 3, 4, 0x83))
    if entry == 0x70c96:
        h += [dict(a6off=[(0x8e, 2, a), (0x42, 2, b), (0x15, 1, f)]) for a, b in ((0x10, 0), (0, 0x10), (0x8000, 0), (0x7fff, 0xffff), (0, 0), (0x30, 0))
              for f in (0, 1)]
    if entry == 0x70cb0:
        h += regs('d0', (0x8000, 0xffff, 0x12340001))
    if entry in (0x70cb2, 0x70cc6, 0x70cd8, 0x70ce6):
        h += regs('d0', (0xf, 0x10, 0x2f, 0x30, 0x47, 0x48, 0x8000, 0x12340010))
    if entry == 0x70cc0:
        h += regs('d1', (0, 0x7fff, 0x8000, 0x12348000))
    if entry == 0x70d22:
        h += regs('d0', (0, 1, 2, 3, 4, 5, 6, 7, 0x12340003, 0x2000))
    if entry == 0x70d38:
        h += byte(0x82, (0, 1))
    if entry == 0x70d50:
        h += byte(0x15, (0, 8))
    if entry == 0x70d60:
        h += word(0x7c, (0, 1, 0x8000))
    if entry == 0x718d2:
        h += byte(0x15, (0, 0x80, 0x88))
    if entry == 0x768b6:
        h += long_(0x7e, (LIST, LIST + 4, LIST_END - 8, LIST_END - 4, LIST_END))
    if entry == 0x768cc:
        h += byte(0x15, (0, 1))
    if entry == 0x768da:
        h += regs('d0', (0, 1, 0x8000, 0xffff, 0x12348000))
    if entry == 0x768dc:
        h += [dict(regs=dict(d0=0x12345678, d1=0x9abcdef0))]
    if entry == 0x7690a:
        h += [dict(parent=[(0x89, 1, v)]) for v in (0, 1, 0x80)]
    if entry == 0x76984:
        h += long_(0x3a, (0, 0xfffe0000, 0x80000000, 0x7fffffff, 0xffffffff, 0x10))
    if entry == 0x769c8:
        h += [dict(popped=p, a6off=[(0x15, 1, f)]) for p in ((0x8000, 0x7fff), (0, 0xffff)) for f in (0, 1)]
    if entry == 0x769d8:
        h += regs('d0', (0, 0x8000, 0x12340001))
    if entry == 0x769b4:
        h += regs('d0', (0, 1, 0x12345601))
    if entry == 0xb33c8:
        h += word(0x86, (0, 1, 0x8000, 0xffff))
    if entry == 0xbc8b6:
        h += byte(0x15, (0, 0x80))
    if entry == 0xbc8d0:
        h += [dict(parent=[(0x62, 1, v)]) for v in (0, 1, 0x80)]
    if entry == 0xbc8dc:
        h += word(0x76, (0, 1, 0x8000))
    if entry == 0xdd5a6:
        h += long_(0x76, (0x8a9ffff, 0x8aa0000, 0x8a9fffe, 0xfffa0000, 0xfff9ffff, 0xffffffff, 0))
    if entry == 0xdd5f8:
        h += long_(0x76, (0x1489ffff, 0x148a0000, 0xfffa0000, 0))
    if entry == 0xdd64a:
        h += long_(0x76, (0x1589ffff, 0x158a0000, 0xfffa0000, 0))
    if entry == 0xdd69c:
        h += long_(0x76, (0, 0xfffa0000, 0xffffffff))
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS + PASS_CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x61, 0x6f, 0x82, 0x86)] + [(6, off, 2) for off in (0x42, 0x46)]
        succ = static_next(cons) if cons not in PASS_SET else {SENTINEL}
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry == 0x7031c and t % 2:
                hint = dict(a5off=[(0x568e, 1, (0, 1, 2, 3)[(t // 2) % 4])])                # 49370: BYTE 568e(A5) = 0 -> ORI Set
            elif entry == 0x76862 and t % 2:
                hint = dict(writes=[(0xfd92, 1, (t // 2) % 2)])                                # 497a6: TST.B 10fd92 (0 -> ORI Set)
            elif entry == 0x76932 and t % 4 == 1:
                hint = dict(a6off=[(0xc, 4, 0)])                                               # 288c: LONG c(A6) = 0 -> ORI Set
            elif entry == 0x76932 and t % 4 == 3:
                hint = dict(a6off=[(0xc, 4, 0x10e600)], writes=[(0xe600, 4, 0x270e)])          # 288c: LONG (parent) = 270e -> Clear
            elif entry in (0x7699a, 0xbc92a) and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry == 0x70cf4 and t % 2:
                hint = dict(a6off=[(0x61, 1, rng.choice((0, 0x20))), (0x82, 1, rng.choice((0, 4, 0x10, 0x20, 0x40, 0x14))), (0x6f, 1, rng.choice((0x40, 0)))])
            elif entry == 0x70d02 and t % 2:
                hint = dict(a6off=[(0x82, 1, 2), (0x6f, 1, 0x40), (0x42, 2, 0x100), (0x46, 2, 0x120)], a5off=[(0x5bfc, 2, rng.choice((0x10, 0x80, 0x100)))])
            elif entry == 0x70d10 and t % 3 == 1:
                hint = dict(a6off=[(0x15, 1, 8)])                                              # 7028e: BYTE 15 bit 3 -> ANDI Clear
            elif entry == 0x70d10 and t % 3 == 2:
                hint = dict(a6off=[(0x15, 1, 0), (0x42, 2, rng.choice((0x200, 0x40, 0x100)))])
            elif entry == 0x70d48 and t % 2:
                hint = dict(a6off=[(0x42, 2, rng.choice((0x100, 0x200))), (0x86, 1, rng.choice((0x80, 0)))])
            elif entry == 0x4c2d0 and t % 3 == 1:
                hint = dict(a6off=[(0x3e, 4, 0)])
            st = world.make(entry, SENTINEL, flds, hint)
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
            hint = dict(a6off=[(0x9c, 2, t % 2), (0x86, 2, (0, 1, 2, 0xc)[(t // 2) % 4]), (0x15, 1, (0, 1, 0x80, 0x88)[(t // 8) % 4])])
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr2b PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x76853), 'unaligned animation machine PC', 0x76853)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr2b caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: TST.W 78(A6) of 70302 (read), MOVE.L #0,64(A6) of 70c68 (write); odd list LONG 7e(A6) (768b6); odd stack (70362 MOVE.W (A7)+,D1)
    err('70302-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70302), odd_word, 0x70302, stop=0x7030a)
    err('70c68-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70c68), odd_write, 0x70c68, stop=0x70c76)
    err('768b6-odd-list', U.with_host_writes(st, [((a6 + 0x7e) & 0xffff, 4, LIST + 1)], pc=0x768b6), odd_word, 0x768b6, stop=0x768cc)
    err('70362-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x70362), odd_word, 0x70362, stop=0x70364)
    # failures after executed blocks:
    #   70302 (WORD 78 != 0) -> 703f0 MOVEQ; RTS at an odd A7
    err('70302-then-703f0', U.with_host_writes(st, [((a6 + 0x78) & 0xffff, 2, 1)], regs=dict(a7=a7 + 1), pc=0x70302), odd_word, 0x703f0)
    #   70606 (WORD 42 - 18 >= 110) -> 70624 ANDI; RTS at an odd A7
    err('70606-then-70624', U.with_host_writes(st, [((a6 + 0x42) & 0xffff, 2, 0x200)], regs=dict(a7=a7 + 1), pc=0x70606), odd_word, 0x70624)
    #   b33c8 (WORD 86 = 5) -> b33d6 RTS at an odd A7
    err('b33c8-then-b33d6', U.with_host_writes(st, [((a6 + 0x86) & 0xffff, 2, 5)], regs=dict(a7=a7 + 1), pc=0xb33c8), odd_word, 0xb33d6)
    #   a8d4 (D0.W = 0) -> a8dc -> a8e4 -> a8ec RTS at an odd A7
    err('a8d4-then-a8ec', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0xa8d4), odd_word, 0xa8ec)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x70c96, 0x70394, 0x7036a, 0xdd5a6)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
