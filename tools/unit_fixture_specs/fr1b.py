"""V1 fixture spec of the animation-machine unit FR1b (engine/src/animation_machine_objects_fr1b.cpp, 211 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr1b-contract.md): the IO-frontier objects 5a376 (N13 state; 5a376..5a460 5a54e..5a5ba,
installs 5a3c6 5a3e4 5a41e 5a43a 5a54e 5a574; the next state of the LONG table 5a5ba is only installed), b30f6 (b30ba..b336a b3460..b3484, installs
b31dc b3246) with the helper e9112 / e9114 (e9112..e9148), the E-area demo / title objects de024 and de376 (ddfdc..de00c de024..de260 de2b6..de31e
de376..de3e6; installs de054 de0d8 de0ee de112 de15c de1a8 de1b4 de204 de210 de2b6 de2cc de3c2; de05e writes the PVC bank ports), the U05 end state
b97c0 (b97c0..b9822, install b97ee) and the HUD list sibling 515fc (515fc..51602).

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a / B3a..B4b) with declared host edits.  A second
natural source for node fixtures are the IO observation states (artifacts/animation_machine_io_native, states/*.pack.gz page-delta packs of the frame
start): the confirmed frontier frames of the FR1a IO rerun (ms5-scratch/fr1/ioA/frontier.json: P1 frame 133 node 5a376, frame 120 b30f6, frame 249
b97c0, frame 143 515fc (return 50dac), boot-demo-0 frame 2 de024, boot-title-idle / boot-title-start frame 2 de376) advanced to the frontier PC are the
real entry states of this unit.  This spec does not decode those packs (the IO comparison rerun checks the natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the eleven consumers is entered directly (the seed world with declared edits: D0-D7, A0 / A1 / A2 / A4 := a natural
            node, LONG c(A6) / 88(A6) := a natural node (88: or a negative LONG), the 515fc / de2fe / de3c6 lists (RAM page or de3e6), the 5e30(A5)
            counters, the node fields the reachable blocks read, the stack LONG that de318 / de3e0 pop, PC := the block start).  Stop: the first PC outside
            the unit (a callee, the sentinel return LONG, JMP 2a00 / 2a24, BRA 5a9c2 / 5a802 / e932c / 515e0).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 1ab02 -> b30ea (b30e4) b335e (b3358) b9816 (b980a), 493bc -> b3470 (b3468), b3460 ->
            b31f4 (b31ec; b3474 Set / b347e Clear), 28ae -> b32d8 (b32c8) b330a (b32fa) b333c (b332c), 49fc6 -> b97fa (b97f4), 5ab5a -> 5a3f8 (5a3f4),
            4945e -> 5a58e (5a588).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  callee    the helpers 515fc b3460 ddfdc e9112 e9114 entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the eleven consumers, odd node / list / stack / A5 pointers, the TRAP
            boundary 493c6 of 493bc (A5 != 108000), failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired
            'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR1a specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (B3a..FR1a)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
LIST = 0x10fd00                         # RAM page of the declared WORD / LONG lists (outside the shared stack page and the RAM probe page 10fe00..)

RANGES = [(0x515fc, 0x51602), (0x5a376, 0x5a460), (0x5a54e, 0x5a5ba), (0xb30ba, 0xb336a), (0xb3460, 0xb3484), (0xb97c0, 0xb9822), (0xddfdc, 0xde00c),
          (0xde024, 0xde260), (0xde2b6, 0xde31e), (0xde376, 0xde3e6), (0xe9112, 0xe9148)]
STARTS = [int(x, 16) for x in (
    '515fc '
    '5a376 5a388 5a394 5a39c 5a3a8 5a3ac 5a3b2 5a3c2 5a3c6 5a3d6 5a3e4 5a3ee 5a3f4 5a3f8 5a3fc 5a402 5a414 5a41a 5a41e 5a42e 5a43a 5a444 5a44a 5a44e '
    '5a456 5a45c 5a54e 5a558 5a568 5a56e 5a574 5a57e 5a584 5a588 5a58e 5a592 5a596 5a59c 5a5ae 5a5b4 '
    'b30ba b30c0 b30ca b30d0 b30d8 b30e0 b30e4 b30ea b30ee b30f4 b30f6 b310c b3114 b3118 b3120 b3130 b314e b3156 b3164 b316e b319e b31ae b31ba b31c0 '
    'b31d0 b31d6 b31dc b31e4 b31ec b31f4 b31f8 b3208 b320c b3214 b3218 b321e b3224 b322c b3234 b323c b3242 b3246 b324c b3266 b3270 b3284 b328c b3296 '
    'b329c b32a2 b32aa b32b2 b32b6 b32be b32c8 b32d8 b32dc b32ea b32ee b32f2 b32fa b330a b330e b331c b3320 b3324 b332c b333c b3340 b334e b3352 b3358 '
    'b335e b3362 b3368 b3460 b3468 b3470 b3474 b347e '
    'b97c0 b97e8 b97ee b97f4 b97fa b97fe b980a b9816 b981a b9820 '
    'ddfdc ddfea ddfee ddff4 de00a '
    'de024 de02e de034 de03a de048 de054 de05c de05e de08a de094 de0a0 de0b2 de0b8 de0be de0cc de0d8 de0e0 de0e2 de0ee de0f6 de0f8 de106 de112 de11a '
    'de11c de126 de12c de136 de144 de15c de176 de194 de1a0 de1a6 de1a8 de1b4 de1ce de1ec de1fc de202 de204 de210 de22a de248 de258 de25e '
    'de2b6 de2c0 de2cc de2e6 de2f6 de2fe de306 de318 de31c '
    'de376 de380 de38a de390 de396 de3a0 de3ae de3b2 de3c2 de3c6 de3ce de3e0 de3e4 '
    'e9112 e9114 e9126 e912a e9132 e913e e9140').split()]
CONSUMERS = (0x5a3f8, 0x5a58e, 0xb30ea, 0xb31f4, 0xb3470, 0xb32d8, 0xb330a, 0xb333c, 0xb335e, 0xb97fa, 0xb9816)
CLEAR_SET = (0xb347e,)                  # ANDI.B #fe,CCR; RTS: the block leaves a known C Clear
SET_SET = (0xb3474, 0xb32ea, 0xb331c, 0xb334e)   # ORI.B #1,CCR: known C Set (b3474 ends in its RTS; the other three have no reader)
PASS_SET = ()                           # no RTS of this unit passes a known C to another unit
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xb30e4, 0xb30ea), (0xb3358, 0xb335e), (0xb980a, 0xb9816), (0xb3468, 0xb3470), (0xb31ec, 0xb31f4), (0xb32c8, 0xb32d8), (0xb32fa, 0xb330a),
          (0xb332c, 0xb333c), (0xb97f4, 0xb97fa), (0x5a3f4, 0x5a3f8), (0x5a588, 0x5a58e))
CHAIN_1AB02 = (0xb30e4, 0xb3358, 0xb980a)
CHAIN_493BC = (0xb3468, 0xb31ec)
CHAIN_28AE = (0xb32c8, 0xb32fa, 0xb332c)
CHAIN_49FC6 = (0xb97f4, 0x5a3f4)        # 5ab5a returns the C of 49fc6
# callbacks and installed values (node callbacks); the callee entries
NODE_ENTRIES = (0x5a376, 0xb30f6, 0xde024, 0xde376, 0xb97c0, 0x5a3c6, 0x5a3e4, 0x5a41e, 0x5a43a, 0x5a54e, 0x5a574, 0xb31dc, 0xb3246, 0xb97ee, 0xde054,
                0xde0d8, 0xde0ee, 0xde112, 0xde15c, 0xde1a8, 0xde1b4, 0xde204, 0xde210, 0xde2b6, 0xde2cc, 0xde3c2)
CALLEES = (0x515fc, 0xb3460, 0xddfdc, 0xe9112, 0xe9114)
STACK_LONG = (0xde318, 0xde3e0)                 # a declared LONG at A7 (the pushed list pointer), the return LONG above it
LIST_BLOCKS = (0xde2fe, 0xde306, 0xde3c6, 0xde3ce)
COUNTER_BLOCKS = (0xe9126, 0xe9132)             # A1 = 5e30(A5) (the counter table)
ITEM_BLOCKS = ()
KIND_BLOCKS = ()
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x88)     # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xb, 0xc, 0xd, 0xf, 0x10, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0xf, 0x10, 0x14, 0x15, 0x1e, 0x40, 0x7f, 0x80, 0xff, 0x100, 0x1000, 0x2000, 0x7fff, 0x8000, 0x8001, 0xfff0,
      0xfffc, 0xffff)
VL = (0, 1, 3, 0x4000, 0x7fff, 0x10000, 0x7fff0000, 0x7fffffff, 0x80000000, 0xc0000000, 0xffff0000, 0xfffffffd, 0xffffffff)
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
        if entry in COUNTER_BLOCKS:
            regs['a1'] = (regs['a5'] + 0x5e30) & 0xffffffff
            regs['d1'] = (regs['d1'] & 0xffffff00) | rng.randrange(0xc)
            if entry == 0xe9126:
                regs['d1'] = rng.randrange(0xc)
            if entry == 0xe9132 and rng.random() < 0.8:
                regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0xc)
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        r88 = rng.random()
        writes.append(((a6 + 0x88) & 0xffff, 4, self.pointer() if r88 < 0.6 else (rng.choice((0x80000000, 0xffffffff, 0x80100000)) if r88 < 0.8 else 0x100cb8)))
        if entry in LIST_BLOCKS or entry in STACK_LONG:
            words = []
            for _ in range(rng.randrange(3)):
                words.append(rng.choice((0, 1, 0x1400, 0x7fff)))
                lv = rng.getrandbits(32)
                words += [lv >> 16, lv & 0xffff]
            words.append(rng.choice((0xffff, 0x8000)))
            for i, w in enumerate(words):
                writes.append(((LIST + 2 * i) & 0xffff, 2, w))
            if entry in LIST_BLOCKS:
                regs['a0'] = LIST if rng.random() < 0.7 else 0xde3e6
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
        # the 5e30(A5) BYTE counters and the index fields: inside the original ranges most of the time (the hints test the edges)
        if rng.random() < 0.8:
            writes.append(((a6 + 0x6b) & 0xffff, 1, rng.choice((rng.randrange(0xc), 0xc, 0xff))))
            writes.append(((a6 + 0x78) & 0xffff, 2, rng.randrange(10)))
        # stack LONG popped by the entered block (declared): de318 / de3e0 the list pointer
        pops = []
        if entry in STACK_LONG:
            pops = [(4, rng.choice((LIST, 0xde3e6)))]
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


out_missing = []
unreachable = []
META = {}


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 211 and len(STARTS_SET) == 211, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    require(unit_of(0x493c6) is None and not mine(0x493c6), 'TRAP 493c6 (of 493bc) must stay unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr1b_block', ('start is not routed to fr1b', hex(s), unit_of(s)))
    rng = random.Random(0xF41B)
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
        for entry in sorted([e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS], key=lambda e: e != 0x5a59c)[:6]:   # 5a59c first: 49a58 is a callee stop for the entries before it
            flds = fields_of(entry)
            for k in range(MAX_TRIES):
                # 5a5ae -> 5a596 needs the table LONG chosen by the random index to equal LONG 98(A6): cycle the four installed state values
                chint = dict(a6off=[(0x98, 4, (0x5a0ae, 0x5a1c4, 0x5a376, 0x5a460)[k % 4])]) if a == 0x5a5ae else None
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
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('fr1b spec: %d fixtures, visited %d/211, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr1b: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr1b: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries included).  Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry == 0x5a376:
        h += byte(0x80, (0, 1, 2, 3, 0x80, 0xfd, 0xff))
    if entry in (0x5a3e4, 0x5a43a, 0x5a574):
        h += byte(0x80, (0, 1, 0xfe, 0xff))
    if entry == 0x5a3d6:
        h += byte(0x8c, (0, 1, 0x80, 0xff))
    if entry == 0x5a402:
        h += [dict(a6off=[(0x8c, 1, a), (0x9c, 1, b)]) for a, b in ((0, 0), (1, 0), (0, 1), (0x80, 0xff), (1, 1))]
    if entry == 0x5a44e:
        h += word(0x84, (0, 1, 2, 0x8000, 0xffff))
    if entry == 0x5a59c:
        h += [dict(regs=dict(d0=a, d7=b)) for a, b in ((0, 1), (1, 2), (2, 0), (3, 0x10001), (0xffff, 0xffff), (0x12345677, 2))]
    if entry == 0xb30f6:
        h += [dict(a6off=[(0x7c, 2, a), (0x78, 2, b)]) for a, b in ((0, 0), (1, 1), (0x7fff, 0), (0x8000, 0x8000), (0xffff, 1), (0x80, 0))]
    if entry == 0xb3118:
        h += word(0x7a, (0, 1, 0x8000))
    if entry == 0xb3120:
        h += [dict(a6off=[(0x36, 4, a), (0x15, 1, b)]) for a, b in ((0, 0), (1, 0xfe), (0x80000000, 0xff), (0xffffffff, 1))]
    if entry in (0xb314e, 0xb3284, 0xb30d0, 0xb32a2, 0xb31dc):
        h += word(0x76, (0, 1, 0x8000, 0xffff))
    if entry == 0xb31e4:
        h += word(0x80, (0, 1, 0x8000))
    if entry == 0xb316e:
        h += regs('d0', (1, 4, 0, 0x1fff, 0x12340004))
    if entry == 0xb31f8:
        h += [dict(a6off=[(0x46, 2, b)], a0off=[(0x46, 2, a)]) for a, b in ((5, 3), (3, 5), (0, 0), (0x8000, 0), (0, 0x8000), (0x7fff, 0xffff))]
    if entry == 0xb3208:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x8000, 0x80000000), (1, 1), (0x12340005, 0xfffffffb))]
    if entry == 0xb320c:
        h += [dict(regs=dict(d0=a), a6off=[(0x7e, 2, b)]) for a, b in ((5, 5), (6, 5), (4, 5), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0))]
    if entry == 0xb3224:
        h += long_(0x72, (0, 0x10000, 1, 0x80000000))
    if entry == 0xb3234:
        h += regs('d0', (0, 0x10000, 1, 0xffff))
    if entry == 0xb30c0:
        h += byte(0x61, (0, 0x7f, 0x80, 0xff))
    if entry == 0xb3266:
        h += byte(0x15, (0x7f, 0x80))
    if entry == 0xb3270:
        h += [dict(a6off=[(0x36, 4, a), (0x82, 4, b)]) for a, b in ((0, 0), (3, 0x80000000), (0x80000000, 1), (0xfffffffd, 0xffffffff), (0x7fffffff, 0))]
    if entry == 0xb324c:
        h += [dict(a6off=[(0x36, 4, a), (0x61, 1, b)]) for a, b in ((0, 0), (0x3fff, 0xf7), (0x80003fff, 8))]
    if entry == 0xb32b6:
        h += word(0x86, (0, 1, 0x15, 0xb, 6, 0x8000))
    if entry == 0xb32be:
        h += regs('d0', (0x15, 0xb, 6, 0, 0x10015, 0x14))
    if entry == 0xb32f2:
        h += regs('d0', (0xa, 0xb, 0x1000a))
    if entry == 0xb3324:
        h += regs('d0', (5, 6, 0x10005))
    if entry == 0xb3460:
        h += long_(0x88, (0x80000000, 0x7fffffff, 0x100cb8, 0x100da8))
    if entry == 0x5a5ae:
        h += [dict(a6off=[(0x98, 4, v)], regs=dict(a0=v)) for v in (0x5a376, 0x5a0ae, 0)]            # CMPA.L 98(A6),A0: equal -> 5a596
    if entry == 0xe9114:
        h += [dict(a6off=[(0x6b, 1, a)], regs=dict(d0=b)) for a, b in ((0, 0), (0xb, 0xb), (0xc, 0xc), (0x80, 0x80), (0xff, 0xff), (5, 0x1234560b))]
    if entry == 0xe912a:
        h += regs('d0', (0, 0xb, 0xc, 0x80, 0xff, 0x1234560b))
    if entry in (0xde054, 0xde0d8, 0xde0ee, 0xde112):
        h += word(0x76, (0, 1, 2, 0x8000, 0xffff))
    if entry in (0xde194, 0xde1ec, 0xde248):
        h += [dict(a6off=[(0x76, 2, a), (0x7a, 2, b), (0x7c, 2, b)]) for a, b in ((1, 0xfff8), (2, 0x7fff), (0, 0xfffc), (0x8001, 2))]
    if entry in (0xde176, 0xde1ce, 0xde22a):
        h += [dict(a6off=[(0x7a, 2, a), (0x7c, 2, b)]) for a, b in ((0x8000, 0x1234), (0, 0xffff))]
    if entry == 0xde2cc:
        h += word(0x78, (0, 1, 8, 9, 10, 0x2000))
    if entry in (0xde2fe, 0xde3c6):
        h += [dict(regs=dict(a0=LIST), writes=[(LIST & 0xffff, 2, v), ((LIST + 6) & 0xffff, 2, 0xffff)]) for v in (0, 0x7fff, 0x8000, 0xffff)]
    if entry == 0xddfdc:
        h += [dict(a5off=[(-0x7fff, 1, v)]) for v in (0, 1, 0x80, 0xff)]
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
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
            elif entry in CHAIN_28AE and t % 2:
                hint = dict(writes=[(0x4ca0, 2, rng_count(t))])                        # 28ae: WORD 104ca0 <= D0 (1e) -> allocation fails, Set
            elif entry in CHAIN_493BC and t % 3 == 1:
                # 493bc: the player record 1 (BTST 568e(A5)); the BYTE bit 0 set (odd t // 3) makes 493e8 return C Set (b3470 -> b3474, b31f4 -> b31f8)
                hint = dict(a6off=[(0x88, 4, 0x100cb8)], regs=dict(d0=0x100cb8), writes=[(0xd68e, 1, 1 if (t // 3) % 2 else 0)])   # b3468 enters with A0 := D0
            elif entry == 0x5a588 and t % 2:
                hint = dict(writes=[(0xd68e, 1, 1)])                                     # 4945e: BYTE 568e(A5) != 0 -> 4938c Clear (5a58e -> 5a592)
            elif entry == 0xb31ec and t % 3 == 2:
                hint = dict(a6off=[(0x88, 4, 0x80000000), (0x80, 2, 2)])               # b3460: negative LONG 88 -> b347e Clear
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
    return (0, 1, 0x1e, 0x1d)[(t // 2) % 4]


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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr1b PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0xb30f7), 'unaligned animation machine PC', 0xb30f7)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr1b caller requires known carry', pc)
    a6 = st['regs']['a6']
    a5 = st['regs']['a5']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W #10,84(A6) at an odd A6 (the entry block fails)
    err('5a42e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x5a42e), odd_write, 0x5a42e)
    # odd list pointer: MOVE.W (A0)+,D1
    err('de2fe-odd-list', U.with_host_writes(st, regs=dict(a0=LIST + 1), pc=0xde2fe), odd_word, 0xde2fe)
    # odd stack: MOVE.L A0,-(A7) of de306 (the list LONG read first)
    err('de306-odd-stack', U.with_host_writes(st, regs=dict(a0=LIST, a7=a7 + 1), pc=0xde306), odd_word, 0xde306)
    # odd A5: MOVE.W #0,-7ff0(A5) of de05e (before the port writes)
    err('de05e-odd-a5', U.with_host_writes(st, regs=dict(a5=a5 + 1), pc=0xde05e), odd_write, 0xde05e)
    # TRAP #15 boundary of 493bc (CMPA.L #108000,A5; BNE -> 493c6): b3468 with A5 != 108000 fails at the unrouted TRAP site 493c6
    err('b3468-493bc-trap', U.with_host_writes(st, regs=dict(a5=0x108100, d0=0x100cb8), pc=0xb3468), 'unsupported animation machine PC', 0x493c6)
    # failures after executed blocks: de054 (WORD 76 = 2 -> 1) -> de05c RTS at an odd A7; b347e (C Clear) RTS at an odd A7 entered from b3460
    err('de054-odd-stack', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 2)], regs=dict(a7=a7 + 1), pc=0xde054), odd_word, 0xde05c)
    err('b3460-odd-stack', U.with_host_writes(st, [((a6 + 0x88) & 0xffff, 4, 0x80000000)], regs=dict(a7=a7 + 1), pc=0xb3460), odd_word, 0xb347e)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x5a402, 0xb31f8, 0xde2cc, 0xe9114)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
