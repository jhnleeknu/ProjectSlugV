"""V1 fixture spec of the animation-machine unit B4 (= B4a; engine/src/animation_machine_objects_b4.cpp, 218 block starts).

Blocks: the 2986 child callbacks of the child tables 227fc / 2280c / 2281c (B3c 1c172) 22ad4 / 22b04 (22ad4..22c8c, 22c8e..22d64; installs 22b96 22cb0
22d06), 22d94 / 22dbc (22d94..22f7a; installs 22e48), 23058 / 2308e (23058..2334c; installs 230fa 231bc 23242 23328 23348) and 235ca (235ca..23774;
installs 23664 236d0 23726), the shared helpers 1c9b8 / 1c9ce (1c9b8..1c9ec), 22a10 / 22a4c / 22a62 (22a10..22a8a) and the shared leaf 4bb52
(4bb52..4bc04).  Contract: docs/analysis/animation-machine-deferred-b4-contract.md.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the eight consumers is entered directly.  The world is the natural N28 node (callback 2b99c) of the D1 seeds 116/117
            (frame 2; node A6, A5, bank, RAM natural) with a declared host edit of D0-D7, A0 := a natural node (the child record that 2986 / 28ae return)
            , A1 / A2 := natural nodes, A4 := a natural node or a list (the list blocks), the node / child / A5 record fields the reachable blocks read
            (values from a seeded generator), LONG 8c(A6) / 80(A6) := the ROM list 22a02 / 235b6 or a natural node, and PC := the block start.  Stop: the
            first PC outside the unit (a callee, the sentinel return LONG, JMP 2a00).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 28ae -> 23190 (entry 23180) 231de (231ce) 23284 (23270) 232be (23296), 287e -> 23336
            (23330), 1ab80 -> 236be (236b4), 49fc6 -> 22d2c (22d26) 23768 (23762).  Native branches on the real flags, the C++ branches on the known C.
            Stop: the consumer's successor (or the first unrouted PC of the run).
  node      the seven child entries and the twelve installed callbacks as node callbacks ((A6) := entry, PC := entry) run through every routed callee up
            to the dispatcher return or the first unrouted PC.  A native run that passes the 28ae failure path (290e) INSIDE 2986 (the next PC after the
            2916 RTS is 298e) is an expected-error fixture: the C++ 2986 wrapper stops at 298e with 'cue wrapper failure requires known caller X'
            (buffer_cue decision 1, contract decision 4), failing PC 298e, plus a paired 'match' row with stop = 298e.
  callee    1c9b8 1c9ce 22a10 22a4c 22a62 4bb52 entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the eight consumers, odd node / child / list / stack pointers, failures after
            executed stores (22b58 -> ... with an odd A6 later, 4bb52 pushes then reads an odd A6): checked error, state preserved.  Every error row records
            its failing PC (Fixture fail_pc, review 0264 L-1); when it differs from the entry a paired 'match' row runs the same state with stop = the
            failing PC.
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..B3c specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (B3a..B3c): the owner of the chain whose 1c114 callee creates these children
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x1c9b8, 0x1c9ec), (0x22a10, 0x22a8a), (0x22ad4, 0x22c8c), (0x22c8e, 0x22d64), (0x22d94, 0x22f7a), (0x23058, 0x2334c), (0x235ca, 0x23774),
          (0x4bb52, 0x4bc04)]
CALLEE_RANGES = [(0x1c9b8, 0x1c9ec), (0x22a10, 0x22a8a), (0x4bb52, 0x4bc04)]
STARTS = [int(x, 16) for x in (
    '1c9b8 1c9c4 1c9c8 1c9ce 1c9da 1c9de 1c9e6 1c9ea '
    '22a10 22a4c 22a54 22a5a 22a60 22a62 22a7c 22a82 '
    '22ad4 22af0 22b00 22b04 22b20 22b30 22b40 22b56 22b58 22b86 22b90 22b96 22ba0 22ba6 22bb8 22bc6 22bcc 22bde 22c42 22c46 22c64 22c70 22c80 '
    '22c82 22c86 '
    '22c8e 22c94 22c98 22cae 22cb0 22cc8 22cce 22cdc 22cf8 22d06 22d14 22d20 22d26 22d2c 22d30 22d36 22d46 22d4c 22d5c 22d62 '
    '22d94 22db8 22dbc 22de0 22de4 22df2 22e02 22e28 22e32 22e48 22e52 22e5c 22e62 22e76 22e82 22e88 22e9e 22eae 22eb8 22eca 22ed8 22ee2 22ee8 '
    '22efa 22f0c 22f22 22f32 22f3a 22f44 22f4c 22f52 22f56 22f5c 22f68 22f78 '
    '23058 23074 23084 2308e 230aa 230ba 230c0 230d0 230e8 230fa 23104 2310c 23114 2311a 2311e 23124 2312e 23134 23140 23146 23156 2315c 2315e '
    '23168 23172 23176 23180 23190 23194 2319e 231a2 231b8 231bc 231ce 231de 231e2 231ec 231f0 2320e 23224 23228 2323c 23242 23248 23256 23260 '
    '2326a 23270 23284 23288 23292 23296 232be 232c2 232cc 232d0 232f6 232fc 23308 2330e 2331e 23324 23328 23330 23336 2333a 23342 23346 23348 '
    '235ca 235e2 235ee 23604 2360a 23630 23640 23650 23664 2366e 23674 2367a 23684 2368c 236a6 236a8 236b4 236be 236c2 236c4 236c8 236d0 236da '
    '236ec 236fa 23710 23726 23730 2373c 2374e 23758 2375c 23762 23768 2376c 23772 '
    '4bb52 4bb66 4bb7c 4bb96 4bba4 4bbaa 4bbb2 4bbb8 4bbc0 4bbc6 4bbce 4bbd4 4bbdc 4bbea 4bbf0 4bbf8 4bbfe').split()]
CONSUMERS = (0x22d2c, 0x23768, 0x23190, 0x231de, 0x23284, 0x232be, 0x23336, 0x236be)
ORI_SET = (0x2319e, 0x231ec, 0x23292, 0x232cc)  # ORI.B #1,CCR: known C Set produced in the block
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x23180, 0x23190), (0x231ce, 0x231de), (0x23270, 0x23284), (0x23296, 0x232be), (0x23330, 0x23336), (0x236b4, 0x236be), (0x22d26, 0x22d2c),
          (0x23762, 0x23768))
CHAIN_49FC6 = (0x22d26, 0x23762)
CHAIN_28AE = (0x23180, 0x231ce, 0x23270, 0x23296)
# child entries and installed callbacks (node callbacks); the callee entries
NODE_ENTRIES = (0x22ad4, 0x22b04, 0x22d94, 0x22dbc, 0x23058, 0x2308e, 0x235ca, 0x22b96, 0x22cb0, 0x22d06, 0x22e48, 0x230fa, 0x231bc, 0x23242, 0x23328,
                0x23348, 0x23664, 0x236d0, 0x23726)
CALLEES = (0x1c9b8, 0x1c9ce, 0x22a10, 0x22a4c, 0x22a62, 0x4bb52)
LIST_BLOCKS = {0x22d06: 0x8c, 0x22d14: 0x8c, 0x23726: 0x80, 0x23730: 0x80}   # MOVEA.L d(A6),A4 / (A4)+ list walks
ROM_LISTS = (0x22a02, 0x235b6)
FAIL_28AE_RTS = 0x2916                  # 28ae failure path RTS (290e LEA -7168(A5),A0; ANDI #fe,CCR; RTS)
CUE_STATUS = 0x298e                     # 2986: the PC after BSR 28ae (buffer_cue bc_status)
BANK_POINTERS = (0x294282, 0x2945b4, 0x294724, 0x2977dc, 0x2996ec)   # the real LONGs of 20006c 200070 200078 20008c 200094 in the 200000 bank
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x80, 0x8c)   # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x16, 0x17, 0x18, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 0x10, 0x40, 0x80, 0xff, 0x100, 0x13f, 0x140, 0x160, 0x17f, 0x180, 0x23f, 0x240, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xffff)
VL = (0, 1, 0x10000, 0x2a000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff20000, 0xffffffff, 0x160000, 0x1400000, 0xfff00000)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')

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
    require(len(_ROUTE) >= 113, ('routing rules', len(_ROUTE)))


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


def in_callee(pc):
    return any(lo <= pc < hi for lo, hi in CALLEE_RANGES)


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
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr') or BCC.match(mn) or a in STARTS_SET or len(out) > 40:
            break
    _BLK[start] = out
    return out


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op)
    return int(m.group(1), 16) if m else None


def static_next(start):
    """Static successors of the entry block (None = computed: RTS)."""
    a, mn, op, size, _ = block_instrs(start)[-1]
    if BCC.match(mn):
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None:
        return {target(op)}
    if mn == 'rts':
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
    """Run the original from state.pc natively until `outside(pc, prev)` is true (checked from the second instruction on).  -> dict(pcs, stop, sr) or None."""
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
    al = set(allowed)
    return lambda pc, prev, size: not mine(pc) and pc not in al


def first_unrouted(extra=()):
    """Stop at the sentinel, at 2a00 (object removal), at an extra PC, or at the first unrouted PC that is not the straight-line successor of the previous
    instruction (a PC inside a block of another executor is not a block entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00}
    # The size Unicorn reports to the code hook is not the M68000 instruction length (287e MOVEA.L 8(A6),A0 -> 2882 was taken for a jump), so the length is decoded.
    def outside(pc, prev, size):
        if pc in ex:
            return True
        if unit_of(pc) is not None:
            return False
        ins = decode(prev)
        return pc != prev + (ins.size if ins is not None else size)
    return outside


# ---------------------------------------------------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------------------------------------------------
def _long(ram, addr):
    o = addr & 0xffff
    return int.from_bytes(bytes(ram[o:o + 4]), 'big')


LIST_CHOICES = (0x22a02, 0x22a06, 0x22a0a, 0x235b6, 0x235ba, 0x235be)    # the two ROM lists and their advanced cursors (22a0a / 235be: the 0 end)


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
        if rng.random() < 0.4:
            regs['d0'] = rng.choice((regs['d0'], rng.randrange(0x20), rng.randrange(0x100), 0x10000))
        if rng.random() < 0.5:
            regs['d4'] = rng.randrange(0x100)                                               # 22a10: sin / cos index (2 * D4.W)
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = rng.choice((self.pointer(), self.pointer(), 0))
        regs['a2'] = self.pointer()
        regs['a4'] = self.pointer()
        if entry in LIST_BLOCKS:
            lst = rng.choice(LIST_CHOICES)
            writes.append(((a6 + LIST_BLOCKS[entry]) & 0xffff, 4, lst))
            regs['a4'] = lst
        if entry in (0x4bb7c,):
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 2, 4, 6, 8, 0xa, 0xc, 0xe))   # 4bb7c: column (LSR.W #4 / ANDI #e done)
            regs['d1'] = (regs['d1'] & 0xffff0000) | (rng.randrange(0x200) & 0x1ff)           # 4bb7c: row source (< 200 tested before)
        base_of = {6: a6, 0: regs['a0'], 4: regs['a4'], 5: regs['a5'], 1: regs['a1'], 2: regs['a2']}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the list pointers stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        if rng.random() < 0.6:
            writes.append(((a6 + 0x22) & 0xffff, 4, rng.choice(BANK_POINTERS)))
        sp = regs['a7']
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
            regs.update(hint.get('regs', {}))
            if 'list' in hint:
                writes.append(((a6 + hint['list'][0]) & 0xffff, 4, hint['list'][1]))
                regs['a4'] = hint['list'][1]
        return U.with_host_writes(st, writes, regs=regs, pc=entry)


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
out_missing = []
unreachable = []
META = {}


def cue_failure(pcs):
    """True when the 28ae failure path ran inside 2986 (its RTS 2916 returns to 298e): the C++ 2986 wrapper error (contract decision 4)."""
    for i in range(len(pcs) - 1):
        if pcs[i] == FAIL_28AE_RTS and pcs[i + 1] == CUE_STATUS:
            return True
    return False


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 218 and len(STARTS_SET) == 218, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b4_block', ('start is not routed to b4', hex(s), unit_of(s)))
    rng = random.Random(0xB4)
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
    sys.stderr.write('b4 spec: %d fixtures, visited %d/218, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b4: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('b4: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit.  Every hint world is kept as a
    fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry in (0x1c9b8, 0x1c9ce):
        h += regs('d0', (0, 1, 0xfffe, 0xffff, 0x10001))
    if entry == 0x1c9de:
        h += [dict(writes=[((0x104d92 + 1) & 0xffff, 1, v)], regs=dict(a4=0x104d92)) for v in (0, 1, 0xff)]
    if entry == 0x22a4c:
        h += word(0x76, (0, 0x7fff, 0x8000, 0xffff))
    if entry in (0x22a62, 0x2368c):
        h += [dict(a6off=[(0x36, 4, v), (0x3a, 4, w)]) for v, w in ((0, 0), (1, 0xfff05398), (0x80000000, 0x7fffffff), (0xffffffff, 0x80000000),
                                                                    (0x7fffffff, 0xfff00000), (0xfffffff1, 0xfff00001))]
    if entry == 0x22a7c:
        h += regs('d0', (0, 0x7ffffff1, 0xfffffff1))
    if entry in (0x22a82, 0x236a8):
        h += regs('d0', (0, 0xf, 0x10, 0x80000000, 0xffffffff, 0x7fffffff))
    if entry == 0x22a10:
        h += [dict(regs=dict(d0=a, d1=b, d4=k)) for a, b, k in ((0, 0, 0), (0x7fffffff, 0x80000000, 0x40), (0x12345678, 0xfedcba98, 0x80),
                                                               (0xffffff00, 0x100, 0xff), (0x00ff0000, 0xff000000, 0xc0))]
    if entry in (0x22b40, 0x22b58):
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry in (0x22ba0, 0x22e5c, 0x2366e, 0x23104, 0x2310c):
        h += regs('d0', (0, 1, 2, 3, 0x100, 0xff, 0x102))
    if entry in (0x22bb8, 0x22eca, 0x23124, 0x2367a):
        h += byte(0x15, (0, 0x7f, 0x80, 0xff))
    if entry == 0x22bde:
        h += [dict(a6off=[(0x7c, 2, w), (0x82, 1, b), (0x80, 2, v)], regs=dict(d2=x, d3=y)) for w, b, v, x, y in (
            (0, 0, 0x280, 0x12345678, 0x9abcdef0), (1, 0x40, 0xfd80, 0x7fffffff, 0x80000000), (0xffff, 0x80, 0x8000, 0, 0), (2, 0xff, 0x7fff, 0xffffffff, 1))]
    if entry in (0x22c64, 0x22f5c, 0x23134, 0x232fc):
        h += word(0x42, (0, 0x13f, 0x140, 0xffff))
    if entry in (0x22c70, 0x22f68, 0x23146, 0x2330e, 0x22d4c):
        h += word(0x46, (0, 0xff, 0x100, 0x23f, 0x240))
    if entry == 0x22d36:
        h += word(0x42, (0xffdf, 0xffe0, 0x15f, 0x160))
    if entry in LIST_BLOCKS:
        h += [dict(list=(LIST_BLOCKS[entry], v)) for v in LIST_CHOICES]
    if entry in (0x22e48, 0x22f3a):
        h += byte(0x61, (0, 8, 0xf7, 0xff))
    if entry == 0x22e62:
        h += regs('d0', (0, 1, 4, 8, 0xff00, 0x12340003))
    if entry == 0x22e76:
        h += long_(0x3a, (0, 0x7fffffff, 0x80000000, 0xffffffff))
    if entry == 0x22efa:
        h += regs('d1', (0x20000, 0x30000, 0x2ffff, 0xffff0000, 0x80000000, 0x7fff0000))
    if entry == 0x22f44:
        h += word(0x80, (0, 1, 0xffff))
    if entry == 0x23684:
        h += word(0x7e, (0, 1, 0xffff))
    if entry in (0x2315e, 0x23256, 0x231f0):
        h += byte(0x84, (0, 1, 2, 0xff))
    if entry == 0x23248:
        h += word(0x80, (0, 1, 2, 0x8000, 0x8001, 0x7fff))
    if entry == 0x232d0:
        h += byte(0x82, (3, 4, 0x7f, 0x80, 0xff))
    if entry in (0x23328, 0x2333a):
        h += byte(0x83, (0, 1, 0x7f, 0x80, 0xff))
    if entry == 0x2374e:
        h += word(0x7c, (0, 0x13f, 0x140, 0xffff))
    if entry == 0x4bb52:
        h += word(0x46, (0xff, 0x100, 0x1ff, 0x200))
    if entry == 0x4bb66:
        h += [dict(a6off=[(0x42, 2, v)], regs=dict(d0=d)) for v, d in ((0x1f, 0), (0x20, 0xff), (0x21f, 0xe0), (0x220, 0x10))]
    if entry in (0x4bb96, 0x4bbaa, 0x4bbb8, 0x4bbc6, 0x4bbdc, 0x4bbf0):
        h += regs('d1', (0, 0xf, 0x10, 0xef, 0xf0, 0xffff))
    if entry in (0x4bb7c, 0x4bbd4):
        h += regs('d0', (0, 1, 2, 0xc, 0xd, 0xe))
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x83, 0x84)] + [(6, off, 2) for off in (0x10, 0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in CHAIN_49FC6 and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                       # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry in CHAIN_28AE and t % 2:
                hint = dict(writes=[(0x4ca0, 2, 0)])                                    # 28ae: WORD 104ca0 = 0 -> D0.W >= limit -> failure (C Clear)
            elif entry == 0x23330:
                hint = dict(a6off=[(0x10, 2, (0, 0xffff, 0x8000)[t % 3])])               # 287e: WORD 10(A6) against WORD 10(LONG 8(A6))
            elif entry == 0x236b4:
                hint = dict(a6off=[(0x46, 2, (0x180, 0x100, 0x210, 0x80)[t % 4]), (0x42, 2, (0xa0, 0x20, 0x150, 0x0)[(t // 4) % 4]),
                                   (0x15, 1, (0, 1, 2, 3)[(t // 16) % 4])])                # 1ab80: inside / outside the screen rectangle
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


def node_fixtures(world, add, record):
    """Child entries and installed callbacks run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first
    unrouted PC.  A run through the 28ae failure path inside 2986 is the expected 2986 wrapper error at 298e (contract decision 4)."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            st = world.make(entry, base.stop, flds)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            failed = cue_failure(tr['pcs'])
            key = (tr['stop'], failed, len(set(tr['pcs']) & STARTS_SET) // 4)
            if key in kept:
                continue
            kept[key] = (st, tr, failed)
            if len(kept) >= 3:
                break
        require(kept, ('no node world', hex(entry)))
        for i, (key, (st, tr, failed)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            if failed:
                add(U.Fixture('node-%05x-%d-2986-failure' % (entry, i), st, [], tr['stop'], ('error', 'cue wrapper failure requires known caller X'),
                              fail_pc=CUE_STATUS, meta=dict(family='node', fail_pc=CUE_STATUS, deliberate='2986 caller-X (buffer_cue decision 1)')))
                add(U.Fixture('node-%05x-%d-to-298e' % (entry, i), st, [], CUE_STATUS, meta=dict(family='node', stop=CUE_STATUS)))
            else:
                add(U.Fixture('node-%05x-%d' % (entry, i), st, [], tr['stop'], meta=dict(family='node', entry=entry, stop=tr['stop'],
                                                                                          unit_blocks=len(set(tr['pcs']) & STARTS_SET))))


def callee_fixtures(world, add, record):
    """The shared helpers as subroutines (return LONG = sentinel)."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry)
        for t in range(80 + len(hints)):
            st = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
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
    """Checked errors with the failing PC (Fixture fail_pc and meta, review 0264 L-1).  A failing PC that differs from the entry gets a paired 'match' row with stop
    = the failing PC (both sides stop exactly there)."""
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)

    def err(name, state, text, fail_pc):
        add(U.Fixture('error-' + name, state, [], SENTINEL, ('error', text), fail_pc=fail_pc, meta=dict(family='error', fail_pc=fail_pc)))
        if fail_pc != state['pc']:
            add(U.Fixture('failpc-' + name, state, [], fail_pc, meta=dict(family='failpc', fail_pc=fail_pc)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects b4 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x22ad5), 'unaligned animation machine PC', 0x22ad5)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects b4 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W #92,20(A6) at an odd A6 (the entry block fails)
    err('22ad4-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x22ad4), odd_write, 0x22ad4)
    # odd child record: MOVE.W #1001,68(A0) at an odd A0
    err('231a2-odd-child', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x231a2), odd_write, 0x231a2)
    # odd list cursor: CMPI.L #0,(A4) with LONG 8c(A6) odd
    err('22d06-odd-list', U.with_host_writes(st, [((a6 + 0x8c) & 0xffff, 4, a6 + 1)], pc=0x22d06), odd_word, 0x22d06)
    # odd stack: MOVEM.L D0-D1/A0,-(A7)
    err('4bb52-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4bb52), odd_word, 0x4bb52)
    # failures after executed blocks: 22ba0 (D0.B = 0) -> 22ba6 reads LONG 36 of an odd node; 23342 stores BYTE 83, then the RTS of 23346 pops at an odd
    # A7; 23260 stores WORD 80 and 23270 the BYTE 82, then the JSR 28ae push fails at an odd A7
    err('22ba0-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1, d0=0), pc=0x22ba0), odd_word, 0x22ba6)
    err('23342-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x23342), odd_word, 0x23346)
    err('23260-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x23260), odd_word, 0x23270)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x22bde, 0x22a10, 0x4bb7c, 0x2360a)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0x36) & 0xffff, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
