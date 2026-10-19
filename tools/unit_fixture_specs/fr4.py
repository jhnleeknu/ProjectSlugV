"""V1 fixture spec of the animation-machine unit FR4 (engine/src/animation_machine_objects_fr4.cpp, 192 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr4-contract.md): the area-D IO-frontier objects of the FR3 IO rerun 72f8a (installed by
the N15 / FR2b family; 730a6 / 73218 / 73296 / 73304 / 73392 and the common tail 7345e that jumps into the hit entry cc778 with its helpers cca76 /
cc600 and cdc1c) and 878dc (object table 4a6b0; the 28ae child 8790c with 87982 / 87a3e / 87a50 / 87a6c), with their natural successors in the same
runs: the FR3 stop install bca2c (bca62) and the FR1c 28ae child bc7d6 (bc836).  The computed jumps cc7a8 / cc82a (27-entry BRA.W tables) leave the
unit through the routing (contract decision 2): their targets are the first unrouted PC of a run.

Seeds.  The worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR3) with declared host edits.  The real entry
states of this unit are the confirmed frontier frames of the FR3 IO rerun (ms5-scratch/fr4/ioA/frontier.json: P1 / P1b frame 496 callback 72f8a,
frame 309 callback 878dc) and their natural successors (frames 497..600 / 310..600 of the same runs); this spec does not decode the IO packs (the IO
comparison rerun checks the natural path).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 7 consumers is entered directly (the seed world with declared edits: D0-D7, A0..A4 := a natural node, LONG
            c(A6) := a natural node, the node / parent / A5 fields the reachable blocks read, the stack WORDs 7310c pops, PC := the block start).
            Stop: the first PC outside the unit (a computed table target included).
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the consumers entered through their REAL producers: 7054c -> 73124 (73120), 1ab80 -> 73468 (7345e), 28ae -> 878ec (878dc), 1ab02 -> 87a9e
            (87a94), 497a6 -> cc60c (cc606) / cc638 (cc632) / cc67c (cc676).  Stop: the consumer's successor (or the first unrouted PC).
  node      the callbacks and installed values ((A6) := entry, PC := entry; cc778 as the JMP target of a callback) up to the dispatcher return or the
            first unrouted PC.
  callee    the helpers entered as subroutines (return LONG = sentinel) up to the sentinel or the first unrouted PC.
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 7 consumers, odd node / stack pointers, computed landings inside
            the unit on a non-start PC, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired
            'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR3 specs do).
"""
import random
import re
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR3)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)

RANGES = [(0x72f8a, 0x73132), (0x73218, 0x733d0), (0x7345e, 0x7357c), (0x73582, 0x735a2), (0x735a4, 0x735a8), (0x878dc, 0x87a3c), (0x87a3e, 0x87a8c),
          (0x87a94, 0x87aaa), (0xbc7d6, 0xbc844), (0xbca2c, 0xbcaa0), (0xcc600, 0xcc696), (0xcc778, 0xcc7ac), (0xcc818, 0xcc82e), (0xcca76, 0xccade),
          (0xcdc1c, 0xcdc24)]
STARTS = [int(x, 16) for x in (
    '72f8a 72f90 72fa8 72fb0 72fd8 72fdc 73004 73008 73010 73038 7303c 73064 7306a 73080 73082 7308c 7308e 730a6 730b0 730ba 730d2 730d8 730e0 730ea '
    '730f8 730fa 7310c 73114 7311a 73120 73124 73128 7312e 73218 73220 73248 7324c 73274 73284 73286 73296 732ac 732be 732c2 732cc 732d2 732dc 732e4 '
    '732ee 732f4 732fa 73300 73304 7330e 73316 73326 73328 73338 73360 73364 7338c 73392 733b6 733bc 733c6 733cc 7345e 73468 7346c 7347a 73482 7348c '
    '73496 7349c 734a6 734ac 734b2 734b4 734bc 734be 734ce 734d0 734d8 734da 734ee 73506 7351e 73520 73538 7353c 73542 7354c 7355c 73582 735a4 878dc '
    '878ec 878f0 878fe 87900 8790a 8790c 87912 87932 87936 87954 8797c 87982 87986 879b6 879c0 879c8 879d0 879d4 879dc 879e4 879ec 879f4 879fc 87a02 '
    '87a0c 87a12 87a1c 87a22 87a28 87a30 87a38 87a3e 87a50 87a56 87a5c 87a64 87a6a 87a6c 87a78 87a84 87a88 87a8a 87a94 87a9e 87aa2 87aa8 bc7d6 bc7e4 '
    'bc7ea bc7fc bc824 bc836 bc83c bc842 bca2c bca5c bca62 bca68 bca6e bca7a bca82 bca88 bca90 bca98 bca9e cc600 cc606 cc60c cc610 cc632 cc638 cc63c '
    'cc642 cc646 cc650 cc654 cc676 cc67c cc680 cc686 cc68a cc694 cc778 cc780 cc784 cc798 cc7a0 cc818 cc81a cc822 cca76 cca80 cca9c ccaa8 ccab6 cdc1c').split()]
CONSUMERS = (0x73124, 0x73468, 0x878ec, 0x87a9e, 0xcc60c, 0xcc638, 0xcc67c)
CLEAR_SET = ()                          # no ANDI.B #fe,CCR in this unit
SET_SET = ()                            # no ORI.B #1,CCR in this unit
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes a C in this unit
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x73120, 0x73124), (0x7345e, 0x73468), (0x878dc, 0x878ec), (0x87a94, 0x87a9e), (0xcc606, 0xcc60c), (0xcc632, 0xcc638), (0xcc676, 0xcc67c))
PASS_CHAINS = ()
SOUND_ENTRIES = (0xcc610, 0xcc654)      # WORD 8c(A6): the index into the LONG table cdf3e (0..5 natural; 14 / 0e reach a negative sound WORD)
TABLE_ENTRIES = ()
# callbacks and installed values (node callbacks; cc778 is the JMP target of the callbacks 7355c / 73582 and of other units); the callee entries
NODE_ENTRIES = (0x72f8a, 0x730a6, 0x73296, 0x73392, 0x878dc, 0x8790c, 0x87982, 0x87a3e, 0x87a50, 0xbca2c, 0xbca62, 0xbc7d6, 0xbc836, 0xcc778)
CALLEES = (0xcc600, 0xcca76, 0x87a6c)
# values a direct entry pops (below the return LONG at A7), lowest address first: ('L'|'W', kind) with kind node / any / small
STACK = {0x7310c: (('W', 'any'), ('W', 'any'))}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x72)   # node links and pointer fields (72: the terrain pointer of 87a28): natural or declared below

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xe, 0xf, 0x10, 0x14, 0x1a, 0x1b, 0x1c, 0x20, 0x40, 0x7f, 0x80, 0x81, 0xc0, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 7, 8, 0xe, 0xf, 0x10, 0x14, 0x3f, 0x40, 0x41, 0x7f, 0x80, 0xff, 0x100, 0x17f, 0x180, 0x181, 0x2000, 0x7fff, 0x8000, 0x8001,
      0xe000, 0xfff0, 0xfff8, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x10, 0x2000, 0x7fff, 0x8000, 0xffff, 0x10000, 0x28000, 0x40000, 0x80000, 0x7fffffff, 0x80000000, 0xfff00000, 0xffff0000, 0xffffe000,
      0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')
TABLE_JUMPS = {}                        # cc7a0 / cc822 JMP (PC,D0.W): the targets leave the unit through the routing (contract decision 2)

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
BUNDLED = (0xcc62e, 0xcc672)            # BPL.W right after BEQ.W (flag-sharing pairs inside the blocks cc610 / cc654)


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
    """The PC after the entry block: pcs[n]; in a bundled BEQ.W / BPL.W block (cc610 cc654) a taken BEQ.W skips the BPL.W, so the successor is pcs[n - 1] (or the stop)."""
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
        if entry in SOUND_ENTRIES or rng.random() < 0.5:
            writes.append(((a6 + 0x8c) & 0xffff, 2, rng.choice((0, 1, 2, 3, 4, 5, 5, 0xe, 0x14))))
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            if reg == 6 and disp == 0x8c and entry in SOUND_ENTRIES:
                continue
            addr = (base_of[reg] + disp) & 0xffffffff
            if not (0x100000 <= addr < 0x110000) or (size > 1 and addr & 1) or 0xee00 <= (addr & 0xffff) < 0xf000:
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        # the BYTE 10fd92 of 497a6 (0: Set, otherwise Clear) and the WORD 53a2(A5) of 734ee
        if rng.random() < 0.5:
            writes.append((0xfd92, 1, rng.choice((0, 0, 1, 0x80, 0xff))))
        if rng.random() < 0.3:
            writes.append(((a5 + 0x53a2) & 0xffff, 2, self.value(2)))
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
    require(len(STARTS) == 192 and len(STARTS_SET) == 192, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in (0x87a8c, 0x72d5e):
        require(unit_of(t) is None and not mine(t), ('data / stop PC must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr4_block', ('start is not routed to fr4', hex(s), unit_of(s)))
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
    sys.stderr.write('fr4 spec: %d fixtures, visited %d/192, missing successors %s, unreachable outcomes %s\n' % (len(out), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out

def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr4: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr4: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts

def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (BYTE / WORD / LONG sign
    boundaries, equal-value ties, sign / zero extension, the sound-table index WORD 8c that reaches a negative sound WORD (14 / 0e), the popped
    MOVEM.W WORDs of 7310c, the upper register bits of the WORD / BYTE operations, the A5 RAM mirror of 734ee, bit combinations, the computed-jump
    index of cc7a0 / cc822 incl. the in-unit landings).  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788)
    if entry == 0x72f90:
        h += [dict(regs=dict(d0=d), a6off=[(0x83, 1, b)]) for d in (0xffffff7f, 0x80, 0x7f, 0, 0x12345680) for b in (0, 0xff)]
    if entry in (0x72fa8, 0x73008, 0x73218, 0x73328, 0x7354c):
        h += word(0x9c, (0, 1, 0x8000))
    if entry == 0x7306a:
        h += [dict(regs=dict(d0=d), a6off=[(0x15, 1, f)]) for d in (0xffff, 0x12340000, 0xffffffff) for f in (0, 1)]
    if entry in (0x73080, 0x7308c, 0x73284, 0x73326, 0x7351e):
        h += regs('d0', (0x80000000, 0, 1, 0x4ffff))
    if entry == 0x73082:
        h += regs('d0', (0x80000000, 0x7fffffff, 0, 0xfffbffff))
    if entry == 0x7308e:
        h += [dict(regs=dict(d0=d), a6off=[(0x42, 4, 0x12345678)]) for d in (0x4ffff, 0x40000, 0x03ffffff, 0xfc000000, 0x03ff0000)]
    if entry in (0x730a6, 0x732c2, 0x733bc, 0x87a02, 0xccab6):
        h += byte(0x15, (0, 0x7f, 0x80, 0xff))
    if entry in (0x730b0, 0x732d2, 0x87a12):
        h += byte(0x61, (0, 1, 0xfe, 0xff))
    if entry == 0x730ba:
        h += [dict(a6off=[(0x8e, 4, a), (0x42, 4, b), (0x64, 4, c)]) for a, b, c in ((0x100000, 0x100000, 0x40000), (0, 0x10000, 0xfffc0000),
                                                                                 (0x7fffffff, 0x80000000, 1), (0x10000, 0, 0xfffe0000), (0, 0, 0))]
    if entry == 0x730d8:
        h += regs('d0', (0x12345678, 0xfffffff8, 7, 8, 0x123456f0))
    if entry == 0x730e0:
        h += [dict(a6off=[(0x64, 4, v), (0x15, 1, f)]) for v in (0x80000000, 1, 0) for f in (0, 1, 0xfe, 0xff)]
    if entry in (0x730ea, 0x73274, 0x73316, 0x87912, 0x878f0, 0x879b6):
        h += [dict(regs=dict(up), a6off=[(0x15, 1, f)]) for f in (0, 1, 0xfe, 0xff)]
    if entry == 0x730f8:
        h += regs('d0', (0x12340040, 0x8000, 0))
    if entry == 0x730fa:
        h += [dict(regs=dict(d0=d, d1=0x9abcdef0), a6off=[(0x42, 2, a), (0x46, 2, b)]) for d, a, b in ((0x12340040, 0x7fff, 0x8000), (0xffffffc0, 0x8000, 0xffff),
                                                                                                    (0x40, 0xffc0, 0))]
    if entry == 0x7310c:
        h += [dict(regs=dict(d2=0x12345678, d3=0x9abcdef0), stack=[(2, a), (2, b)]) for a, b in ((0x8000, 0x7fff), (0x7fff, 0xffff), (0, 0x8001))]
    if entry == 0x73286:
        h += [dict(regs=dict(d0=d), a6off=[(0x42, 4, 0x89abcdef)]) for d in (0x10000, 0xffff0000)]
    if entry == 0x73296:
        h += [dict(regs=dict(up), a6off=[(0x64, 2, a), (0x42, 2, b)]) for a, b in ((0x4000, 0x8000), (0xc000, 0x7fff), (0x3fff, 1), (0xffff, 0xffff))]
    if entry == 0x732ac:
        h += [dict(regs=dict(up), a6off=[(0x8e, 2, a), (0x42, 2, b), (0x64, 2, c)]) for a, b, c in ((0x10, 0x10, 0x8000), (0x10, 0x11, 0), (0x8000, 0x7fff, 0),
                                                                                                (0, 0, 0xffff), (0x10, 0x11, 0x8000))]
    if entry == 0x732be:
        h += long_(0x64, (0x80000000, 1, 0))
    if entry == 0x732dc:
        h += word(0x64, (0x7fff, 0x8000, 0, 0xffff))
    if entry in (0x732e4, 0x732ee, 0x7348c, 0x73496):
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x73304:
        h += word(0x46, (0x17f, 0x180, 0x181, 0x8000, 0xffff, 0))
    if entry == 0x73392:
        h += [dict(a6off=[(0x64, 4, a), (0x36, 4, b), (0x3a, 4, c)]) for a, b, c in ((0x28000, 0, 0), (0xfffd8000, 0x7fffffff, 0x80000000), (0, 0x1f, 0xfff00000),
                                                                                (0x80000000, 0x7fffffff, 0x7fffffff), (0x20, 0, 0xfff00020))]
    if entry == 0x7347a:
        h += [dict(regs=dict(d0=0x1234ff00), a6off=[(0x62, 1, v)]) for v in (0, 1, 2, 3, 0x80, 0xff)]
    if entry == 0x73482:
        h += regs('d0', (0x12340000, 0x12340001, 0x12340002, 0xffff0000))
    if entry == 0x734ac:
        h += regs('d1', (0x12348001, 0x7fff, 0xffff, 1, 0, 0xfffe))
    if entry in (0x734b2, 0x734bc):
        h += regs('d1', (0x12348000, 1, 0))
    if entry in (0x734ce, 0x734d8):
        h += regs('d3', (0x12348000, 1, 0))
    if entry == 0x734b4:
        h += [dict(regs=dict(d0=d), a6off=[(0x8e, 2, v)]) for d, v in ((0x12340010, 0x10), (0x8000, 0x7fff), (0x7fff, 0x8000), (0, 1))]
    if entry == 0x734d0:
        h += [dict(regs=dict(d2=d), a6off=[(0x8e, 2, v)]) for d, v in ((0x12340010, 0x10), (0x8000, 0x7fff), (0x7fff, 0x8000), (0, 1))]
    if entry == 0x734be:
        h += [dict(regs=dict(d0=a, d1=b, d3=c)) for a, b, c in ((0x12347fff, 1, 0x8001), (0x8000, 0x8000, 0x7fff), (0xffff, 0xffff, 1), (0, 0, 0xffff))]
    if entry == 0x734da:
        h += [dict(regs=dict(d2=a, d3=b, d0=c), a6off=[(0x9a, 2, z)]) for a, b, c in ((0x12347fff, 1, 0x80000000), (0x8000, 0x8000, 0x7fffffff), (0, 0xffff, 0))
              for z in (0, 1)]
    if entry == 0x734ee:
        h += [dict(regs=dict(d2=0x12345678), a6off=[(0x96, 2, a), (0x42, 2, c)], a5off=[(0x53a2, 2, b)]) for a, b, c in ((0x8000, 0x8000, 0), (0x7fff, 1, 0),
                                                                                                                    (0, 0, 1))]
        h += [dict(regs=dict(a5=0x1f8000), writes=[(0xd3a2, 2, v)]) for v in (0x8000, 0x1234)]   # A5 in the upper RAM mirror: 53a2(A5) = 1fd3a2 = 10d3a2
    if entry == 0x73506:
        h += [dict(regs=dict(d2=d, d0=0x12345678), a6off=[(0x8c, 2, w), (0x92, 4, l)]) for d, w, l in ((0x80000000, 0xff88, 0x80000000), (0x7fffffff, 0xff89, 0x7fffffff),
                                                                                                    (0, 0xffff, 0), (0x40, 0x7f88, 0xffffffff), (1, 0, 0x40))]
    if entry == 0x73520:
        h += [dict(regs=dict(d0=0, d1=0, d2=a), a6off=[(0x92, 4, b), (0x8e, 4, c)]) for a, b, c in ((0x40000000, 0x3fffffff, 1), (0x40000000, 0x3fffffff, 0),
                                                                                                   (0x80000000, 0, 0xffffffff), (0x80000000, 0, 0))]
        h += [dict(regs=dict(d0=0x8000ffff, d1=0x12345678, d2=0x9abcdef0))]
    if entry == 0x73542:
        h += byte(0x61, (0, 0x7f, 0x80, 0xff))
    if entry in (0x7355c, 0x73582, 0x878dc, 0x87900, 0xbc7d6, 0xbca2c, 0x87936, 0xbc7ea):
        h += [dict(regs=dict(up))]
    if entry == 0x87932:
        h += long_(0x36, (0x80000, 0x80000000, 0))
    if entry == 0x87986:
        h += regs('d0', (0x13, 0x14, 0x17, 0x12340015))
    if entry in (0x879c0, 0x879d4):
        h += long_(0x36, (0, 0x80000000, 0x7fffffff, 0xffffe000, 0x1fff))
    if entry in (0x879c8, 0x879dc):
        h += long_(0x36, (0x7fffe000, 0x80001fff, 0))
    if entry == 0x879e4:
        h += word(0x76, (0, 1, 0xffff))
    if entry == 0x879ec:
        h += word(0x76, (0, 1, 0x8000))
    if entry == 0x879f4:
        h += long_(0x3a, (0, 0x80004900, 0x4900))
    if entry == 0x87a28:
        h += long_(0x72, (0, 0x0010e800))
    if entry == 0x87a3e:
        h += byte(0x61, (0, 8, 0xf7, 0xff))
    if entry in (0x87a5c, 0xbca7a, 0xbca90):
        h += word(0x76, (0, 1, 0x8000, 0xffff))
    if entry == 0x87a6c:
        h += [dict(regs=dict(up), a6off=[(0x3a, 2, v)]) for v in (0, 0x7fff, 0x8000, 0xfff8, 0xfff7, 0xfff6, 0xfff0, 0xffff)]
    if entry == 0x87a78:
        h += regs('d1', (0x1234fff8, 0xfff7, 0xfff6, 0x8000, 0xfffa, 0))
    if entry == 0x87a84:
        h += regs('d1', (0x12345678,))
    if entry == 0x87a88:
        h += [dict(regs=dict(d0=0x1234ffff, d1=0x9abc0004))]
    if entry == 0x878fe:
        h += regs('d0', (0x1234ffe8, 0x8000))
    if entry == 0xbca6e:
        h += [dict(parent=[(0x62, 1, v), (0x63, 1, w)]) for v in (0, 1, 0x80) for w in (0, 1)]
    if entry == 0xbca88:
        h += [dict(a0off=[(0x63, 1, v)]) for v in (0, 1, 0x80)]
    if entry in (0xcc610, 0xcc654):
        h += word(0x8c, (0, 1, 2, 3, 4, 5, 0xe, 0x14))
    if entry in (0xcc63c, 0xcc642, 0xcc680, 0xcc686):
        h += [dict(regs=dict(d0=0x12345678), a0off=[(0, 2, a), (2, 2, b)]) for a, b in ((0x8000, 0x7fff), (0x7fff, 0x8000))]
    if entry in (0xcc646, 0xcc68a):
        h += regs('d1', (0x123456ff,))
    if entry in (0xcc632, 0xcc676, 0xcc606):
        h += [dict(writes=[(0xfd92, 1, v)]) for v in (0, 1, 0x80)]
    if entry in (0xcc778, 0xcc784):
        h += [dict(regs=dict(d0=0x12345678), a6off=[(0x5e, 1, v), (0x15, 1, f)]) for v in (0, 1, 0x1a, 0x1b, 0xff) for f in (0, 0x80)]
    if entry in (0xcc798, 0xcc81a):
        h += regs('d0', (0x1a, 0x1b, 0xff, 0x12345600, 0x1234561a, 0x1234ff1b))
    if entry in (0xcc7a0, 0xcc822):
        h += regs('d0', (0, 1, 3, 0x1a, 0x12340003, 0xffffff00, 0x1b))
    if entry == 0xcca76:
        h += [dict(regs=dict(up), a6off=[(0x61, 1, v)]) for v in (0, 0x40, 0xbf, 0xff)]
    if entry == 0xcca80:
        h += [dict(regs=dict(a0=0x12345678, a1=0x9abcdef0, d1=0x9abc8001, d2=0x55550005))]
    return h


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x5e, 0x61, 0x62, 0x6f, 0x82)] + [(6, off, 2) for off in (0x42, 0x46, 0x4a, 0x4e)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            hint = None
            if entry == 0x73120 and t % 2:
                hint = dict(a6off=[(0x82, 1, (0x04, 0x20, 0x40, 0)[(t // 2) % 4]), (0x61, 1, (0, 0x20)[(t // 8) % 2]), (0x6f, 1, 0x40)])   # 7054c: Set / Clear
            elif entry in (0x7345e, 0x87a94) and t % 2:
                hint = dict(a6off=[(0x42, 4, (0x00a00000, 0x7fff0000)[(t // 2) % 2]), (0x46, 4, (0x01800000, 0x7fff0000)[(t // 4) % 2]),
                                   (0x4a, 4, 0), (0x4e, 4, 0), (0x15, 1, 0)])                                    # 1ab80 / 1ab02: on screen (Clear) / off (Set)
            elif entry in (0xcc606, 0xcc632, 0xcc676):
                hint = dict(writes=[(0xfd92, 1, (0, 1)[t % 2])])                                                 # 497a6: BYTE 10fd92 = 0 -> ORI Set
            elif entry == 0x878dc and t % 3 == 1:
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
            hint = dict(a6off=[(0x9c, 2, t % 2), (0x8c, 2, (0, 1, 2, 5)[(t // 2) % 4]), (0x15, 1, (0, 1, 0x80, 0x81)[(t // 8) % 4]),
                               (0x5e, 1, (0, 3, 0x1b, 0x0c)[(t // 4) % 4]), (0x61, 1, (0, 0x80, 0x01, 0x40)[(t // 16) % 4])])
            if entry in (0xbc7d6, 0xbc836):
                hint['a6off'].append((0x1d, 1, t % 4))                                  # 8ebe (via 49290): CMPI.B #4,1d(A6) BCS -> 8ecc; >= 4 reaches the untraceable TRAP #15 8ec8
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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), 'unsupported animation objects fr4 PC', pc)
    err('odd-pc', U.with_host_writes(st, pc=0x72f8b), 'unaligned animation machine PC', 0x72f8b)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), 'objects fr4 caller requires known carry', pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    inside = 'unsupported animation objects fr4 PC'
    # odd node: TST.W 9c(A6) of 72fa8 (read), MOVE.L #8a000,3a(A6) of 7330e (write); odd stack (7310c MOVEM.W (A7)+,D2-D3)
    err('72fa8-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x72fa8), odd_word, 0x72fa8, stop=0x72fb0)
    err('7330e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x7330e), odd_write, 0x7330e, stop=0x73316)
    err('7310c-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x7310c), odd_word, 0x7310c, stop=0x70036)
    # computed landings inside the unit on a PC that is not a block start (F1 decision 3): cc7a0 D0.B = 1c -> cc81c (inside CMPI.B of cc81a),
    # cc822 D0.B = 93 -> cca7a (inside BSET.B of cca76)
    err('cc7a0-lands-cc81c', U.with_host_writes(st, regs=dict(d0=0x1c), pc=0xcc7a0), inside, 0xcc81c)
    err('cc822-lands-cca7a', U.with_host_writes(st, regs=dict(d0=0x93), pc=0xcc822), inside, 0xcca7a)
    # failures after executed blocks:
    nd = base.state['regs']['a6']
    #   730ea (BYTE 15 bit 0 set) -> 730fa MOVEM.W D0-D1,-(A7) at an odd A7
    err('730ea-then-730fa', U.with_host_writes(st, [((nd + 0x15) & 0xffff, 1, 1)], regs=dict(a7=a7 + 1), pc=0x730ea), odd_word, 0x730fa, stop=0x4bc04)
    #   87a6c (WORD 3a negative) -> 87a78 -> 87a84 -> 87a88 -> 87a8a RTS at an odd A7
    err('87a6c-then-87a8a', U.with_host_writes(st, [((nd + 0x3a) & 0xffff, 2, 0x8000)], regs=dict(a7=a7 + 1), pc=0x87a6c), odd_word, 0x87a8a)
    #   cc778 (BYTE 5e != 0) -> cc780 JSR cca76 at an odd A7
    err('cc778-then-cc780', U.with_host_writes(st, [((nd + 0x5e) & 0xffff, 1, 3)], regs=dict(a7=a7 + 1), pc=0xcc778), odd_word, 0xcc780, stop=0xcca76)
    #   cc798 (D0.B = 1b) -> cdc1c MOVE.L #cdc24,(A6) at an odd A6
    err('cc798-then-cdc1c', U.with_host_writes(st, regs=dict(d0=0x1b, a6=a6 + 1), pc=0xcc798), odd_write, 0xcdc1c)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x73520, 0x730ba, 0x734be, 0x7310c)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
