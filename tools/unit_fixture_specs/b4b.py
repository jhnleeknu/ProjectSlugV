"""V1 fixture spec of the animation-machine unit B4b (engine/src/animation_machine_objects_b4b.cpp, 198 block starts).

Blocks: the 2986 child 23a3e of the child table 2282c (23a3e..23c56; installs 23ae4 23bfa 23c3e) with the helper 49636 / 4964e (49636..496a6), the
U06-neighbour script handler e74f8 and its two-entry jump table e7504 / e7508 (e74f8..e7546), the 28ae children 2b7be (sibling stage event callback
2b7b8; 2b6e6..2b7c6) and e7996 (e7996..e7a44; installs e79fe), the B4 children 22f7a (22f7a..22fe0; installs 22fc8), 23774 (23774..237ca; installs
237b2), 2334c (2334c..233bc, 233be..2347e, 23480..2353c; installs 2339c 233de 2345e 2349a 23536) and d206a (d206a..d20b0), and the 23a3e child
281ea (281ea..2822a, 2825c..28490; installs 2825c) with the helper 4439e (4439e..443b8).  Contract: docs/analysis/animation-machine-deferred-b4b-contract.md.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the nine consumers is entered directly.  The world is the natural N28 node (callback 2b99c) of the D1 seeds 116/117
            (frame 2; node A6, A5, bank, RAM natural) with a declared host edit of D0-D7, A0 := a natural node (child / parent record) or 0 (4964e),
            A1 := a ring cell 78(A6) + 8k (the 2825c ring blocks) or a natural node, A2 := a natural node, LONG c(A6) := a natural node, LONG 56(A0) := a
            natural node or 0, LONG 7c(A6) := the ROM list 2303a or 0, the script WORD (A0) of e74f8 := 0 / 4 / 8 / 30 / 40 / 42 in a RAM page, the stack
            words that 283cc / 2840a / 28456 / e7500 pop, the node / child / A5 record fields the reachable blocks read (values from a seeded generator) and
            PC := the block start.  Stop: the first PC outside the unit (a callee, the sentinel return LONG, JMP 2a00, BCC 22c82, BRA 2b8b6 / d239c).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 28ae -> 2b746 (entry 2b736) 2b788 (2b778) e7a2c (e7a1c), 288c -> 28268 (2825c), 49fc6 ->
            22fd4 (22fce) 233ea (233e4) 234c6 (234c0) 237be (237b8) 23c4a (23c44).  Native branches on the real flags, the C++ branches on the known C.
            Stop: the consumer's successor (or the first unrouted PC of the run).
  node      the child entries and the installed callbacks as node callbacks ((A6) := entry, PC := entry) run through every routed callee up to the
            dispatcher return or the first unrouted PC.
  callee    4439e 49636 4964e 2b6e6 and the script handler e74f8 (script WORD 0 / 4) entered as subroutines (return LONG = sentinel) up to the sentinel or
            the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the nine consumers, odd node / child / script / stack pointers, the
            computed e74fc targets e7506 / e750a (B4b interior) and e7505 (odd), failures after executed stores: checked error, state preserved.  Every
            error row records its failing PC (Fixture fail_pc, review 0264 L-1); when it differs from the entry and is even a paired 'match' row runs the
            same state with stop = the failing PC.
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..B4 specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (B3a..B4)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
SCRIPT = 0x10fd00                       # RAM page of the declared e74f8 script WORD (outside the shared stack page and the RAM probe page 10fe00..)

RANGES = [(0x22f7a, 0x22fe0), (0x2334c, 0x233bc), (0x233be, 0x2347e), (0x23480, 0x2353c), (0x23774, 0x237ca), (0x23a3e, 0x23c56), (0x281ea, 0x2822a),
          (0x2825c, 0x28490), (0x2b6e6, 0x2b7c6), (0x4439e, 0x443b8), (0x49636, 0x496a6), (0xd206a, 0xd20b0), (0xe74f8, 0xe7546), (0xe7996, 0xe7a44)]
STARTS = [int(x, 16) for x in (
    '22f7a 22f90 22fa0 22fa4 22fb4 22fc2 22fc8 22fce 22fd4 22fd8 22fde '
    '2334c 23360 23376 23384 23394 2339c 233a6 233ac 233b6 '
    '233be 233c4 233ca 233d4 233de 233e4 233ea 233ee 233f4 23400 23406 23416 2341c 2341e 2343a 2344a 2345e 23468 2346e 23478 '
    '23480 23486 23494 2349a 234a0 234a8 234b0 234b8 234c0 234c6 234ca 234d0 234da 234e0 234ec 234f2 23502 23508 23514 23516 23528 2352c 23536 '
    '23774 2379c 237ac 237b2 237b8 237be 237c2 237c8 '
    '23a3e 23a5c 23a72 23a80 23a8a 23aa0 23ad0 23ae4 23aee 23af4 23afe 23b12 23b18 23b26 23b36 23b3e 23b44 23b56 23b84 23bb6 23bc2 23bd2 23bd8 23bda '
    '23be4 23be8 23bf2 23bfa 23c12 23c20 23c30 23c3e 23c44 23c4a 23c4e 23c54 '
    '281ea 28206 28222 '
    '2825c 28268 2826c 28276 282a8 282bc 282be 282c6 282c8 282ce 282d0 282de 282e6 282f4 282f8 2831e 28324 2832a 2834e 28366 28376 283be 283c4 283cc '
    '283d4 28406 2840a 28456 2845c 28466 28468 28470 28478 28482 28488 2848e '
    '2b6e6 2b70a 2b718 2b726 2b736 2b746 2b74a 2b774 2b778 2b788 2b78c 2b7b6 2b7b8 2b7be 2b7c2 '
    '4439e '
    '49636 4963a 49648 4964e 49658 49662 49676 49692 49694 4969e 496a0 496a4 '
    'd206a d207c d20a4 '
    'e74f8 e7500 e7504 e7508 e750c e751c e7534 e7544 '
    'e7996 e79d0 e79f8 e79fe e7a04 e7a0e e7a14 e7a1a e7a1c e7a2c e7a30 e7a3a e7a3e').split()]
CONSUMERS = (0x22fd4, 0x233ea, 0x234c6, 0x237be, 0x23c4a, 0x28268, 0x2b746, 0x2b788, 0xe7a2c)
ORI_SET = (0x2b74a, 0x2b78c, 0xe7a3a)  # blocks ending with ORI.B #1,CCR: known C Set produced in the block
STARTS_SET = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x2b736, 0x2b746), (0x2b778, 0x2b788), (0xe7a1c, 0xe7a2c), (0x2825c, 0x28268), (0x22fce, 0x22fd4), (0x233e4, 0x233ea), (0x234c0, 0x234c6),
          (0x237b8, 0x237be), (0x23c44, 0x23c4a))
CHAIN_49FC6 = (0x22fce, 0x233e4, 0x234c0, 0x237b8, 0x23c44)
CHAIN_28AE = (0x2b736, 0x2b778, 0xe7a1c)
CHAIN_288C = (0x2825c,)
# child entries and installed callbacks (node callbacks); the callee entries
NODE_ENTRIES = (0x22f7a, 0x23774, 0x2334c, 0xd206a, 0x23a3e, 0x281ea, 0xe7996, 0x2b7be, 0x2b7b8, 0x22fc8, 0x2339c, 0x233de, 0x2345e, 0x2349a, 0x23536,
                0x237b2, 0x23ae4, 0x23bfa, 0x23c3e, 0x2825c, 0xe79fe)
CALLEES = (0x4439e, 0x49636, 0x4964e, 0x2b6e6, 0xe74f8)
RING_BLOCKS = (0x28376, 0x283be, 0x283c4, 0x283d4, 0x28406, 0x2840a, 0x2831e)   # A1 = a ring cell 78(A6) + 8k on entry
SCRIPT_WORDS = (0, 4, 8, 0x30, 0x40, 0x42)      # e74fc targets e7504 e7508 e750c e7534 e7544 (B4b starts) and e7546 (U06 block start)
BANK_POINTERS = (0x290b7e, 0x29351a, 0x2977dc, 0x2983f2, 0x2996ec, 0x29c910)   # the real LONGs of 20003c 200050 20008c 200090 200094 20009c (bank 200000)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x7c)   # node links and pointer fields: natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xf, 0x10, 0x11, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xe0, 0xe1, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 7, 8, 0x10, 0x30, 0x38, 0x40, 0x80, 0xff, 0x100, 0x13f, 0x140, 0x1ff, 0x200, 0x23f, 0x240, 0xfff, 0x1000, 0x7fff, 0x8000, 0x8001,
      0xfff0, 0xffff)
VL = (0, 1, 0x7fff, 0x10000, 0x170000, 0x180000, 0x7fff0000, 0x80000000, 0xffff0000, 0xfff80000, 0xffffffff, 0x1400000)
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
    """Static successors of the entry block (None = computed: RTS, or the indirect JSR e7504(PC,D0.W) of e74f8)."""
    a, mn, op, size, _ = block_instrs(start)[-1]
    if BCC.match(mn):
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d0.w)' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr'):
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
        if s == 0xe74f8:
            work += [0xe7504, 0xe7508]
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
    instruction (a computed e74fc target inside the unit that the C++ rejects)."""
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
            regs['d0'] = rng.choice((regs['d0'], rng.randrange(0x100), 0x80, 0xff, 0x8000, 0x10000))
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a4'] = self.pointer()
        if entry in (0x4964e,) and rng.random() < 0.3:
            regs['a0'] = 0
        if entry in RING_BLOCKS:
            regs['a1'] = (a6 + 0x78 + 8 * rng.randrange(7)) & 0xffffffff
        if entry in (0x28366, 0x2845c, 0x28468, 0x2834e):
            regs['d7'] = (regs['d7'] & 0xffff0000) | (8 * rng.randrange(7))
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))
        if rng.random() < 0.5:
            writes.append(((a6 + 0x7c) & 0xffff, 4, rng.choice((0x2303a, 0))))
        if rng.random() < 0.6:
            writes.append(((a6 + 0x22) & 0xffff, 4, rng.choice(BANK_POINTERS)))
        if entry == 0xe74f8:
            regs['a0'] = SCRIPT
            writes.append((SCRIPT & 0xffff, 2, rng.choice(SCRIPT_WORDS)))
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
        if regs['a0'] and 0x100000 <= regs['a0'] < 0x110000 and rng.random() < 0.5:
            writes.append(((regs['a0'] + 0x56) & 0xffff, 4, rng.choice((0, self.pointer()))))
        # stack words popped by the entered block (declared): 283cc A1, 2840a four LONGs, 28456 four LONGs + one WORD, e7500 A0
        pops = {0x283cc: [(4, (a6 + 0x78 + 8 * rng.randrange(7)) & 0xffffffff)], 0x2840a: [(4, rng.getrandbits(32)) for _ in range(4)],
                0x28456: [(4, rng.getrandbits(32)) for _ in range(4)] + [(2, 8 * rng.randrange(7))], 0xe7500: [(4, self.pointer())]}.get(entry, [])
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
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('a1off', []):
                writes.append(((regs['a1'] + off) & 0xffff, size, val))
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
    require(len(STARTS) == 198 and len(STARTS_SET) == 198, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_b4b_block', ('start is not routed to b4b', hex(s), unit_of(s)))
    rng = random.Random(0xB4B)
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
    sys.stderr.write('b4b spec: %d fixtures, visited %d/198, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('b4b: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('b4b: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD sign boundaries
    included).  Every hint world is kept as a fixture (forced), whatever successor it takes."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    if entry in (0x22f7a,):
        h += byte(0x8a, (0, 1, 0x80, 0xff))
    if entry in (0x23360,):
        h += byte(0x84, (0, 1, 2, 0x81, 0xff))
    if entry in (0x2339c, 0x2345e):
        h += byte(0x82, (0, 1, 0x7f, 0x80, 0xff))
    if entry in (0x233be, 0x23480):
        h += byte(0x82, (0, 1, 0x80, 0x81))
    if entry in (0x233ac, 0x2346e, 0x234d0):
        h += byte(0x15, (0, 0x7f, 0x80, 0xff))
    if entry in (0x233f4, 0x234e0, 0x23bb6):
        h += word(0x42, (0, 0x13f, 0x140, 0x8000, 0xffff))
    if entry in (0x23406, 0x234f2, 0x23bc2):
        h += word(0x46, (0, 0xff, 0x100, 0x1ff, 0x200, 0x23f, 0x240, 0x80ff))
    if entry == 0x234a0:
        h += long_(0x7c, (0, 0x2303a, 0x80000000))
    if entry == 0x234b0:
        h += regs('d0', (0, 1, 0x10000, 0x8000, 0xffff0000))
    if entry == 0x23508:
        h += byte(0x12, (0, 0x7f, 0x80, 0xfe, 0xff))
    if entry == 0x23516:
        h += regs('d1', (0, 0x1f, 0x7f, 0x80, 0xa0, 0xa1, 0xdf, 0xe0, 0xfe, 0x123456a1))
    if entry in (0x23aee, 0xe7a0e):
        h += regs('d0', (0, 1, 0x80, 0xff, 0x100, 0x8000, 0x10000))
    if entry == 0x23af4:
        h += byte(0x15, (0, 0x20, 0xdf, 0xff))
    if entry == 0x23afe:
        h += long_(0x84, (0, 0x170000, 0x178000, 0x178001, 0x180000, 0xffff8001, 0x7fffffff))
    if entry == 0x23b18:
        h += word(0x82, (0, 1, 0x8000, 0xffff))
    if entry == 0x23b26:
        h += regs('d0', (0, 1, 0x8000, 0x12340000))
    if entry == 0x23b36:
        h += regs('d0', (0, 1, 0x80, 0x100))
    if entry == 0x23b44:
        h += [dict(regs=dict(d0=d), a6off=[(0x78, 2, w)]) for d, w in ((0, 0), (0x7f, 0x7f80), (0x80, 0x1234), (0xff, 0xff7f), (0x1234ff, 0x8000))]
    if entry == 0x23b56:
        h += [dict(regs=dict(d7=d), a6off=[(0x7e, 4, a), (0x84, 4, b), (0x64, 4, c)]) for d, a, b, c in (
            (0, 0, 0, 0), (0x80000000, 0x7fffffff, 0x180000, 0), (0xfffffff8, 0x10, 0, 0x180000), (0x12345678, 0x87654321, 0x7fffffff, 0x80000000))]
    if entry == 0x23b84:
        h += [dict(regs=dict(d0=a, d1=b), a6off=[(0x36, 4, c), (0x3a, 4, d), (0x78, 2, w)]) for a, b, c, d, w in (
            (0, 0, 0, 0, 0), (0x80000000, 0x7fffffff, 0x7fffffff, 0x80000000, 0xffff), (0x10, 0xfffffff0, 0x20, 0x20, 0x7f80), (1, 2, 3, 4, 0x8000))]
    if entry == 0x23aa0:
        h += long_(0x3a, (0, 1, 0x40, 0x80000000, 0xffffffc0, 0x7fffffff))
    if entry == 0x2826c:
        h += [dict(a0off=[(0x61, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)]
    if entry == 0x28276:
        h += [dict(a0off=[(0x63, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)]
    if entry == 0x282a8:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x7fff, 0x8000), (0xffff, 1))]
    if entry in (0x282bc, 0x282c6):
        h += regs('d0' if entry == 0x282bc else 'd1', (0x80000000, 0xffffffff, 1))
    if entry == 0x282c8:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (1, 0), (0, 1), (0x80000000, 0x7fffffff), (0x7fffffff, 0x80000000), (5, 5))]
    if entry == 0x282d0:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x7fffffff, 0x7fffffff), (0xfff00000, 0x10000), (0x12345678, 0x9abcdef0))]
    if entry == 0x282de:
        h += byte(0x62, (0, 1, 2, 0x80, 0xff))
    if entry == 0x282e6:
        h += word(0xb0, (0, 7, 8, 0x30, 0x8000, 0xffff))
    if entry == 0x282f4:
        h += regs('d0', (0xfff8, 0xffff, 0x12340000))
    if entry == 0x282f8:
        h += [dict(regs=dict(d0=d), a6off=[(0x61, 1, f)]) for d, f in ((0, 0), (0x30, 0x80), (8, 0x7f), (0x18, 0xff))]
    if entry in (0x28366, 0x2845c):
        h += regs('d7', (0, 8, 0x30, 0x12340030, 0x37, 0x38))
    if entry == 0x28468:
        h += [dict(regs=dict(d7=d), a6off=[(0xb0, 2, w)]) for d, w in ((0, 0), (8, 0), (0x10008, 8), (0x30, 0x30))]
    if entry in (0x28470,):
        h += byte(0x63, (0, 1, 0x80, 0xff))
    if entry in (0x28478,):
        h += byte(0x61, (0, 0x7f, 0x80, 0xff))
    if entry == 0x28376:
        h += [dict(regs=dict(d0=a, d1=b, d2=cc, d3=d), a1off=[(0, 1, k), (4, 2, r), (6, 1, n)]) for a, b, cc, d, k, r, n in (
            (0, 0, 0, 0, 0, 0, 1), (0x10000, 0, 0, 0, 0x40, 0x100, 2), (0x7fffffff, 0x80000000, 0, 0, 0x80, 0x1000, 0x11), (0x12345678, 0x9abcdef0, 0x12340000, 0x9abc0000, 0xff, 0x8000, 0x80))]
    if entry == 0x283cc:
        h += [dict(regs=dict(d0=d)) for d in (0, 0x7f, 0x80, 0xff, 0x8000)]
    if entry == 0x283d4:
        h += [dict(regs=dict(d0=d), a1off=[(7, 1, a), (4, 2, w)], a6off=[(0x64, 1, b)]) for d, a, b, w in (
            (0, 0, 0, 0), (0x8000, 0x80, 0x80, 0xfff), (0x7fff, 0xff, 1, 0xc00), (0xffff, 0x7f, 0x80, 0x1000), (0x1234, 0xf0, 0x10, 0x8000))]
    if entry == 0x2840a:
        h += [dict(regs=dict(d4=w), a1off=[(0, 1, k)]) for w, k in ((0, 0), (0x1000, 0x40), (0xfff, 0x80), (0x8000, 0xff))]
    if entry == 0x2b726:
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x4439e:
        h += [dict(regs=dict(d0=a, d1=b)) for a, b in ((0, 0), (0x7fff, 0x40), (0x8000, 0x80), (0xffff, 0xff), (0x12340100, 0xffffff7f))]
    if entry == 0x4963a:
        h += [dict(regs=dict(d0=a, d1=b), a6off=[(0x42, 2, c), (0x46, 2, d)]) for a, b, c, d in ((0, 0, 1, 0xffff), (0x8000, 0x7fff, 0x7fff, 0x8000))]
    if entry == 0x49648:
        h += regs('d0', (0x100, 0x1ff, 0x8080, 0x12345678))
    if entry == 0x49676:
        h += [dict(a0off=[(0x15, 1, f)]) for f in (0, 1, 2, 3, 0xfc)]
    if entry in (0x49692, 0x4969e):
        h += regs('d2' if entry == 0x49692 else 'd3', (0, 1, 0x8000, 0xffff, 0x12340001))
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x61, 0x82)] + [(6, off, 2) for off in (0x10, 0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry in CHAIN_49FC6 and t % 2:
                hint = dict(a6off=[(0x26, 4, 0)])                                       # 49fc6: LONG 26(A6) = 0 -> ORI Set
            elif entry in CHAIN_28AE and t % 2:
                hint = dict(writes=[(0x4ca0, 2, 0)])                                    # 28ae: WORD 104ca0 = 0 -> D0.W >= limit -> failure (C Clear)
            elif entry in CHAIN_288C:
                kind = t % 3                                                            # 288c: parent 0 (Set) / LONG (parent) = 270e (Clear) / other (Set)
                if kind == 0:
                    hint = dict(a6off=[(0xc, 4, 0)])
                elif kind == 1:
                    p = world.pointer()
                    hint = dict(a6off=[(0xc, 4, p)], writes=[(p & 0xffff, 4, 0x270e)])
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
    unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            hint = dict(a6off=[(0x1d, 1, t % 6)]) if entry in (0x2b7be, 0x2b7b8) else None     # 8ebe: CMPI.B #4,1d(A6) BCS -> 8ecc; >= 4 reaches TRAP #15 (not traceable)
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
    """The helpers and the script handler as subroutines (return LONG = sentinel)."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry)
        for t in range(80 + len(hints)):
            if t < len(hints):
                hint = hints[t]
            else:
                hint = dict(a6off=[(0x1d, 1, t % 6)]) if entry == 0x2b6e6 else None            # 8ebe: BYTE 1d(A6) < 4 (see node_fixtures)
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects b4b PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x23a3f), 'unaligned animation machine PC', 0x23a3f)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects b4b caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # odd node: MOVE.W #e2,20(A6) at an odd A6 (the entry block fails)
    err('22f7a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x22f7a), odd_write, 0x22f7a)
    # odd child record: MOVE.W #ffff,76(A0) at an odd A0
    err('e751c-odd-child', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0xe751c), odd_write, 0xe751c)
    # odd script pointer: MOVE.W (A0)+,D0
    err('e74f8-odd-script', U.with_host_writes(st, regs=dict(a0=SCRIPT + 1), pc=0xe74f8), odd_word, 0xe74f8)
    # odd stack: MOVE.W D7,-(A7)
    err('28376-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1, a1=a6 + 0x78), pc=0x28376), odd_word, 0x28376)
    # computed e74fc targets: e7506 / e750a (inside the B4b blocks e7504 / e7508) and e7505 (odd)
    for word, name, text, fail in ((2, 'e7506', 'unsupported animation objects b4b PC', 0xe7506), (6, 'e750a', 'unsupported animation objects b4b PC', 0xe750a),
                                   (1, 'e7505', 'unaligned animation machine PC', 0xe7505)):
        err('e74f8-target-' + name, U.with_host_writes(st, [(SCRIPT & 0xffff, 2, word)], regs=dict(a0=SCRIPT), pc=0xe74f8), text, fail)
    # failures after executed blocks: 233be (BYTE 82 = 1 -> 0) -> 2339c -> 233c4 pushes at an odd A7; 2b7b8 sets BYTE 15 bit 0, then the BSR of 2b7be
    # pushes at an odd A7; 4964e (A0 = 0) -> 49658 pops at an odd A7; 282f4 -> 282f8 writes WORD b0 of an odd node
    err('233be-odd-stack', U.with_host_writes(st, [((a6 + 0x82) & 0xffff, 1, 1)], regs=dict(a7=a7 + 1), pc=0x233be), odd_word, 0x233c4)
    err('2b7b8-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x2b7b8), odd_word, 0x2b7be)
    err('4964e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1, a0=0), pc=0x4964e), odd_word, 0x49658)
    err('282f4-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x282f4), odd_write, 0x282f8)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x23b56, 0x28376, 0x2840a, 0x4439e)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, (st['regs']['a6'] + 0x36) & 0xffff, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
