"""V1 fixture spec of the animation-machine unit FR1a (engine/src/animation_machine_objects_fr1.cpp, 214 block starts).

Blocks: the first IO-frontier objects (contract docs/analysis/animation-machine-frontier-fr1-contract.md): de660 (C2 28ae child; de660..de8bc, installs
de686 de754 de778 de814 de84c de880) with the helpers ca42 / 4e146, e5324 (U02 28ae child; e5292..e5580, installs e5364 e537e e539e e5418 e5424
e543e e545e e54d8 e54e4 e5538 e5568) with the helpers 4e0de / e56c0 (DIVU), the item object b3dbc (2986 child; b3dbc..b3dfc b3ea2..b3eac
b3ec4..b3f40 b3f4c..b3f8c b3fa4..b402a, installs b4012 b3fa4; jump tables b3dcc / b3fce and JMP (A0) through the kind records b3484), the C helper
4b6f4, d131a, the U06 neighbours eb9ba / eb9e4, the HUD list 51602 / 515e0, the delete callback b7742 and the U05 end state b975e.

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as B3a..B4b) with declared host edits.  A second natural
source for node fixtures are the IO observation states (artifacts/animation_machine_io_native, states/*.pack.gz page-delta packs of the frame start):
the confirmed frontier frames (P1 case 94 frame 2 node de660, case 68 frame 222 de660, case 0 frame 99 b3dbc, case 90 frame 100 e5324, case 32 frame
181 4b6f4, case 58 frame 24 eb9ba, case 60 frame 327 d131a, case 84 frame 143 51602, case 80 frame 273 b7742, case 44 frame 120 b975e) advanced to the
frontier PC are the real entry states of this unit.  This spec does not decode those packs (the IO comparison rerun, tools/verify_animation_machine_io.py,
checks the natural path); it is noted here as the preferred source for a later natural node family.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the three consumers is entered directly (the seed world with declared edits: D0-D7, A0 / A1 := a natural node, the
            item / kind records b3894 + 12k / b3484 + 10k, a RAM WORD list or 51620, LONG c(A6) := a natural node, LONG 22(A6) := the real bank pointer,
            the node / record fields the reachable blocks read, the stack WORD / LONG that 515e2 515e8 515ec 515f8 read or pop, PC := the block start).
            Stop: the first PC outside the unit (a callee, the sentinel return LONG, JMP 2a00 / 2a24 / 3670 / 3a70 / 491b6, TRAP b3eac, a live jump target).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 1ab02 -> b97b4 (entry b97a8), 49fc6 -> b401e (b4018) b9798 (b9792); and the 4b6f4 C
            through its real consumer 5f5e6 (B2a; the return LONG of the entry 4b6f4).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the three consumers, odd node / list / stack pointers, DIVU zero divisor,
            computed targets inside the unit (b3dbc WORD 7e = 5 -> b3de0, b3fc6 WORD 7c = 3 -> b3fda), TRAP b3eac without a stop: checked error, state
            preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..B4b specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (B3a..B4b)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
LIST = 0x10fd00                         # RAM page of the declared 515e2 WORD list (outside the shared stack page and the RAM probe page 10fe00..)

RANGES = [(0xca42, 0xca48), (0x4b6f4, 0x4b702), (0x4e0de, 0x4e0f6), (0x4e146, 0x4e166), (0x515e0, 0x515fc), (0x51602, 0x51608), (0xb3dbc, 0xb3dfc),
          (0xb3ea2, 0xb3eac), (0xb3ec4, 0xb3f40), (0xb3f4c, 0xb3f8c), (0xb3fa4, 0xb402a), (0xb7742, 0xb7748), (0xb975e, 0xb97c0), (0xd131a, 0xd1348),
          (0xde660, 0xde8bc), (0xe5292, 0xe5580), (0xe56c0, 0xe5724), (0xeb9ba, 0xeba3e)]
STARTS = [int(x, 16) for x in (
    'ca42 4b6f4 4b6fc 4b700 4e0de 4e146 4e152 4e158 4e162 4e164 515e0 515e2 515e8 515ec 515f8 51602 '
    'b3dbc b3dcc b3dd0 b3dd4 b3dd8 b3ddc b3de4 b3dec b3df4 b3ea2 b3ec4 b3ed8 b3ede b3ee6 b3eea b3efc b3f02 b3f22 b3f26 b3f2c b3f3a '
    'b3f4c b3f50 b3f5c b3f68 b3fa4 b3faa b3fb2 b3fc6 b3fce b3fd2 b3fd6 b3ffe b400c b4012 b4018 b401e b4022 b4028 b7742 '
    'b975e b9786 b978c b9792 b9798 b979c b97a8 b97b4 b97b8 b97be d131a d1330 d1342 '
    'de660 de66e de674 de67a de686 de68e de690 de69a de6aa de6ba de6d0 de6e6 de6fc de712 de728 de738 de742 de754 de75c de75e de764 de772 de778 '
    'de782 de784 de78a de79a de7b0 de7c6 de7dc de7f2 de808 de814 de81a de82c de832 de838 de83a de840 de84c de854 de856 de864 de874 de880 de88a '
    'de898 de8a0 de8a2 de8ac '
    'e5292 e529e e52a2 e52b2 e52c2 e52ca e52d6 e52e6 e52ea e52f6 e5304 e5308 e5314 e5318 e5324 e533c e534c e5350 e5358 e5364 e536c e536e e5372 '
    'e537e e5386 e5388 e5392 e539e e53a6 e53b2 e53bc e53c6 e53ca e53da e53e4 e53e8 e53ec e53fc e5400 e5418 e5424 e542c e542e e5432 e543e e5446 '
    'e5448 e5452 e545e e5466 e5472 e547c e5486 e548a e549a e54a4 e54a8 e54ac e54bc e54c0 e54d8 e54e4 e54ec e54ee e54f8 e54fc e550e e5518 e552c '
    'e5538 e5540 e5542 e5552 e5568 e5570 e5572 e56c0 e56d0 e56e6 e56fe e5720 '
    'eb9ba eb9c4 eb9ce eb9d6 eb9dc eb9e2 eb9e4 eb9ec eb9fa eba02 eba08 eba28 eba2e eba3c').split()]
CONSUMERS = (0xb401e, 0xb9798, 0xb97b4)
CLEAR_SET = (0x4b6f4,)                  # TST.B clears C: the block leaves a known C Clear
SET_SET = (0x4b6fc,)                    # ORI.B #1,CCR: known C Set
PASS_SET = (0x4b700,)                   # RTS that keeps the incoming C (carry preserving, not a consumer)
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xb97a8, 0xb97b4), (0xb4018, 0xb401e), (0xb9792, 0xb9798))
CHAIN_49FC6 = (0xb4018, 0xb9792)
CHAIN_1AB02 = (0xb97a8,)
B2A_CONSUMER = 0x5f5e6                  # B2a BCC.W 5f5f0 (C of 4b6f4): Clear -> 5f5f0, Set -> 5f5ea
# callbacks and installed values (node callbacks); the callee entries
NODE_ENTRIES = (0xde660, 0xe5324, 0xb3dbc, 0xb975e, 0xb7742, 0xde686, 0xde754, 0xde778, 0xde814, 0xde84c, 0xde880, 0xe5364, 0xe537e, 0xe539e,
                0xe5418, 0xe5424, 0xe543e, 0xe545e, 0xe54d8, 0xe54e4, 0xe5538, 0xe5568, 0xb3fa4, 0xb4012, 0xb978c)
CALLEES = (0x4b6f4, 0xca42, 0x4e146, 0x4e0de, 0xe56c0, 0x51602, 0x515e0, 0xeb9ba, 0xeb9e4, 0xd131a, 0xe5292, 0xe52b2, 0xe52d6, 0xe52f6, 0xb3f4c,
           0xb3f5c, 0xb3f68)
STACK_WORD = (0x515e2, 0x515e8, 0x515ec)        # a declared WORD at A7 (the pushed D2), the return LONG above it
STACK_LONG_WORD = (0x515f8,)                    # a declared LONG (the pushed A0 = the list) and the WORD, the return LONG above them
LIST_BLOCKS = (0x515e0, 0x515e2, 0x515ec, 0x515f8)
ITEM_BLOCKS = (0xb3f50, 0xb3f68, 0xb3fb2)       # A0 = an item record b3894 + 12k
KIND_BLOCKS = (0xb3f3a,)                        # A1 = a kind record b3484 + 10j
ITEM_COUNT, KIND_COUNT = 0x6e, 104
BANK_POINTERS = (0x2cdeaa, 0x2d450e)            # the real LONGs of 2001c0 2001d0 (bank 200000)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22)           # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x11, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xe0, 0xe1, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x1e, 0x40, 0x6d, 0x6e, 0x6f, 0x80, 0xff, 0x100, 0x3e7, 0x3e8, 0x19ce, 0x19cf, 0x19d0, 0x1000, 0x7fff, 0x8000,
      0x8001, 0xfff0, 0xffff)
VL = (0, 1, 0x7fff, 0x10000, 0x7fff0000, 0x80000000, 0xffff0000, 0xffffffff)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {0xb3dbc: (0xb3dcc, 0xb3dd0, 0xb3dd4, 0xb3dd8), 0xb3fc6: (0xb3fce, 0xb3fd2)}     # transcribed jump tables (contract decision 3)

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
    """Static successors of the entry block (None = computed: RTS, the jump tables of b3dbc / b3fc6 and the JMP (A0) of b3f3a / b3fb2)."""
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
    ex = set(extra) | {SENTINEL, 0x2a00}
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
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a4'] = self.pointer()
        if entry in ITEM_BLOCKS:
            regs['a0'] = 0xb3894 + 12 * rng.randrange(ITEM_COUNT)
        if entry in KIND_BLOCKS:
            regs['a1'] = 0xb3484 + 10 * rng.randrange(KIND_COUNT)
        if entry in (0xe56d0, 0xe56e6, 0xe56fe):
            regs['d2'] = (regs['d2'] & 0xffff0000) | 0xa
        if entry in (0x4e158, 0x4e162):
            regs['a0'] = rng.choice((0x1009a8, 0x100a6c))
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        if rng.random() < 0.6:
            writes.append(((a6 + 0x22) & 0xffff, 4, rng.choice(BANK_POINTERS)))
        if entry in LIST_BLOCKS:
            regs['a0'] = LIST
            n = rng.randrange(3)
            words = []
            for _ in range(n):
                words += [rng.choice((0, 1, 0x85, 0x7fff)), rng.getrandbits(16)]
            words.append(rng.choice((0xffff, 0x8000)))
            for i, w in enumerate(words):
                writes.append(((LIST + 2 * i) & 0xffff, 2, w))
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 4: regs['a4'], 5: regs['a5']}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # item / kind indices: the original checks only WORD 76 < 6e (b3ea2); the declared worlds stay inside the transcribed tables most of the time
        if rng.random() < 0.8:
            writes.append(((a6 + 0x76) & 0xffff, 2, rng.randrange(1, ITEM_COUNT)))
            writes.append(((a6 + 0x8a) & 0xffff, 2, rng.randrange(ITEM_COUNT)))
            writes.append(((a6 + 0x7e) & 0xffff, 2, rng.randrange(4)))
            writes.append(((a6 + 0x7c) & 0xffff, 2, rng.randrange(3)))
        # stack words read / popped by the entered block (declared): 515e2 515e8 515ec a WORD, 515f8 a LONG (the list) and a WORD
        pops = []
        if entry in STACK_WORD:
            pops = [(2, rng.getrandbits(16))]
        elif entry in STACK_LONG_WORD:
            pops = [(4, LIST), (2, rng.getrandbits(16))]
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
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
            regs.update(hint.get('regs', {}))
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
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
    require(unit_of(0xb3eac) is None and not mine(0xb3eac), 'TRAP b3eac must stay unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr1_block', ('start is not routed to fr1', hex(s), unit_of(s)))
    rng = random.Random(0xF41)
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
            cond_points[a] = {target(op), a + size}
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
            if nxt in CONSUMERS or (mine(nxt) and nxt not in STARTS_SET):
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
        for entry in [e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS][:6]:
            flds = fields_of(entry)
            for _ in range(MAX_TRIES):
                st = world.make(entry, SENTINEL, flds)
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
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('fr1 spec: %d fixtures, visited %d/214, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr1: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr1: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD sign boundaries
    included).  Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry == 0x4b6f4:
        h += [dict(a5off=[(0x5b86, 1, v)]) for v in (0, 1, 0x7f, 0x80, 0xff)]
    if entry == 0x4e158:
        h += [dict(a0off=[(0x9c, 1, v)]) for v in (0, 1, 2, 0x81, 0xff)]
    if entry == 0x4e0de:
        h += regs('d0', (0, 1, 2, 3, 0xffff, 0x12340001))
    if entry == 0x515e2:
        h += [dict(writes=[(LIST & 0xffff, 2, v), ((LIST + 4) & 0xffff, 2, 0xffff)]) for v in (0, 0x7fff, 0x8000, 0xffff)]
    if entry in (0xde686, 0xde754, 0xde84c, 0xde898):
        h += word(0x76, (0, 1, 2, 0x8000, 0xffff))
    if entry in (0xe5364, 0xe537e, 0xe539e, 0xe5424, 0xe543e, 0xe545e, 0xe54e4, 0xe5538):
        h += word(0x7a, (0, 1, 2, 8, 9, 0x8000))
    if entry in (0xe53a6, 0xe5466):
        h += word(0x7a, (0, 7, 8, 0x10, 0x8000, 0xffff))
    if entry == 0xde778:
        h += byte(0x62, (0, 3, 4, 5, 0x84, 0xff))
    if entry == 0xde832:
        h += regs('d0', (0, 1, 0x80, 0xff, 0x100, 0x12345600))
    if entry == 0xde880:
        h += word(0x82, (0, 0x19c0, 0x19ce, 0x19cf, 0x19d0, 0x7fff, 0x8000, 0xffff))
    if entry in (0xe5292, 0xe52b2, 0xe52d6, 0xe5308, 0xe533c, 0xe53ec, 0xe54ac, 0xe54fc):
        h += word(0x7c, (0, 1, 0x8000, 0xffff))
    if entry == 0xe52f6:
        h += [dict(a5off=[(-0x8000, 1, v)]) for v in (0, 2, 3, 4, 0x83)]
    if entry == 0xe5324:
        h += [dict(a6off=[(0x7c, 2, k)], writes=[(0xfdb6, 1, a), (0xfdb7, 1, b)]) for k, a, b in (
            (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 0), (2, 1, 2), (0xffff, 0x81, 1), (0x8000, 1, 0xff))]
    if entry in (0xe53da, 0xe549a):
        h += regs('d1' if entry == 0xe53da else 'd2', (0, 0x3e6, 0x3e7, 0x3e8, 0x7fff, 0x8000, 0xffff, 0x123403e7))
    if entry == 0xe5568:
        h += byte(0x62, (0, 1, 0x80, 0xff))
    if entry == 0xe56c0:
        h += regs('d0', (0, 1, 9, 0xa, 0x3e7, 0x999, 0xffff, 0x10000, 0x12340000, 0x1234ffff))
    if entry in (0xe56d0, 0xe56e6, 0xe56fe):
        h += [dict(regs=dict(d0=a, d2=b)) for a, b in ((0, 0xa), (9, 0xa), (0xffff, 0xa), (0x9ffff, 0xa), (0xa0000, 0xa), (0xffffffff, 0xa), (5, 1), (0x10000, 1))]
    if entry == 0xb3dbc:
        h += word(0x7e, (0, 1, 2, 3, 4, 0x2000, 0x4000))
    if entry == 0xb3fc6:
        h += regs('d3', (0, 1, 2, 0x4000, 0x8000))
    if entry == 0xb3ea2:
        h += word(0x76, (0, 0x6d, 0x6e, 0x6f, 0x8000, 0xffff))
    if entry == 0xb3ec4:
        h += word(0x76, (0, 1, 0x6d))
    if entry == 0xb3ede:
        h += word(0x78, (0, 1, 0x8000))
    if entry == 0xb3eea:
        h += byte(0x95, (0, 4, 0xfb, 0xff))
    if entry == 0xb3f02:
        h += [dict(regs=dict(d2=v), a6off=[(0x15, 1, f)]) for v, f in ((0, 0), (3, 0xff), (0xff, 0x80), (0x1234567c, 1))]
    if entry == 0xb3f2c:
        h += [dict(regs=dict(d0=a, d3=b)) for a, b in ((0, 0), (0x8000, 1), (0x7fff, 0x10000), (0xffff, 0xffff))]
    if entry in (0xb3f5c,):
        h += regs('d0', (0, 1, 0x6d, 0xaaa, 0xaab, 0xffff, 0x12340005))
    if entry in (0xb3faa,):
        h += word(0x8a, (0, 1, 0x6d))
    if entry == 0xeb9ba:
        h += [dict(a6off=[(0x7e, 2, a), (0x7a, 2, b)]) for a, b in ((0, 3), (2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 3), (0xffff, 0), (5, 0xffff))]
    if entry == 0xeb9ce:
        h += [dict(regs=dict(d1=a), a6off=[(0x7a, 2, b)]) for a, b in ((2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 0x7fff), (0xffff, 0))]
    if entry == 0xeb9e4:
        h += [dict(a6off=[(0x7c, 2, a), (0x78, 2, b)]) for a, b in ((0, 3), (2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 3), (0xffff, 4))]
    if entry == 0xeb9fa:
        h += [dict(regs=dict(d1=a), a6off=[(0x78, 2, b)]) for a, b in ((2, 3), (3, 3), (0x7fff, 0x8000), (0x8000, 0x7fff))]
    if entry == 0xeb9dc:
        h += regs('d3', (0, 1, 0x10000, 0x8000))
    if entry == 0xeba08:
        h += word(0x7c, (0, 1, 11))
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run.  The 4b6f4 C goes
    through its real B2a consumer 5f5e6 (the return LONG of the entry 4b6f4)."""
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x61)] + [(6, off, 2) for off in (0x10, 0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in CHAIN_49FC6 and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                       # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry in CHAIN_1AB02 and t % 2:
                hint = dict(a6off=[(0x42, 4, 0x7fff0000), (0x4a, 4, 0)])               # 1ab02: far outside the screen -> Set
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
    # 4b6f4 -> RTS 4b700 -> the B2a consumer 5f5e6 (BCC.W 5f5f0): BYTE 5b86(A5) = 0 -> Clear -> 5f5f0, otherwise Set -> 5f5ea.
    for flag, value in ((0, 0), (1, 1), (2, 0x80), (3, 0xff)):
        st = world.make(0x4b6f4, B2A_CONSUMER, [], dict(a5off=[(0x5b86, 1, value)]))
        tr = trace(st, first_unrouted(extra=(0x5f5f0, 0x5f5ea)), cap=400000)
        require(tr is not None and tr['stop'] == (0x5f5f0 if value == 0 else 0x5f5ea), ('4b6f4 chain', value, tr and hex(tr['stop'])))
        record(tr['pcs'] + [tr['stop']])
        add(U.Fixture('chain-4b6f4-to-5f5e6-%d' % flag, st, [], tr['stop'], meta=dict(family='chain', entry=0x4b6f4, consumer=B2A_CONSUMER, successor=tr['stop'])))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted
    PC."""
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
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry)
        for t in range(80 + len(hints)):
            hint = hints[t] if t < len(hints) else dict(a6off=[(0x1d, 1, t % 4)])     # 8ebe: BYTE 1d(A6) < 4 (see node_fixtures)
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr1 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0xde661), 'unaligned animation machine PC', 0xde661)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr1 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    inside = 'unsupported animation objects fr1 PC'
    # odd node: MOVE.W #4,76(A6) at an odd A6 (the entry block fails)
    err('de67a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xde67a), odd_write, 0xde67a)
    # odd list pointer: MOVE.W (A0)+,D0
    err('515e2-odd-list', U.with_host_writes(st, regs=dict(a0=LIST + 1), pc=0x515e2), odd_word, 0x515e2)
    # odd stack: MOVE.W D2,-(A7) after LEA 51620(PC),A0; BRA.B 515e0
    err('51602-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x51602), odd_word, 0x515e0)
    # DIVU zero divisor
    err('e56d0-divu-zero', U.with_host_writes(st, regs=dict(d0=5, d2=0x12340000), pc=0xe56d0), 'objects fr1 DIVU zero divisor', 0xe56d0)
    # computed targets inside the unit: b3dbc WORD 7e = 5 -> b3de0, b3fc6 D3.W = 3 -> b3fda
    err('b3dbc-target-b3de0', U.with_host_writes(st, [((a6 + 0x7e) & 0xffff, 2, 5)], pc=0xb3dbc), inside, 0xb3de0)
    err('b3fc6-target-b3fda', U.with_host_writes(st, regs=dict(d3=3), pc=0xb3fc6), inside, 0xb3fda)
    # TRAP #15 boundary without a stop: b3ea2 with WORD 76 >= 6e
    err('b3ea2-trap', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 0x6e)], pc=0xb3ea2), 'unsupported animation machine PC', 0xb3eac)
    # failures after executed blocks: e5364 (WORD 7a = 2 -> 1) -> e536c RTS at an odd A7; eb9c4 -> eb9dc -> eb9e2 RTS at an odd A7
    err('e5364-odd-stack', U.with_host_writes(st, [((a6 + 0x7a) & 0xffff, 2, 2)], regs=dict(a7=a7 + 1), pc=0xe5364), odd_word, 0xe536c)
    err('eb9c4-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1, d3=0), pc=0xeb9c4), odd_word, 0xeb9e2)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xb3f02, 0xeba08, 0xe5552, 0xde880)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
