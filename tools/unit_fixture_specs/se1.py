"""V1 fixture spec of the area-E unit E1 (engine/src/animation_machine_select_e1.cpp, 222 block starts; file prefix se1 / select_e1).

Blocks (contract docs/analysis/animation-machine-select-e1-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2): the character select
nodes of de8bc..df2c0 -- the creation callbacks de8ca (slot text, JSR ca50 + Z, 4e186, 4a974 + Z, 3918), de97e (title frame), de9e8 (cursor blink,
4e186), deb1a (portrait frame, bank-window script), deba4 (portrait slide, 28ae child defdc) with their installed states, the 28ae children defdc
(selection cursor), dedb6 (name plate) and dee36 (portrait, 4-way script choice), the shared tail de8bc, the digit marks df272 (MOVEM.L D2/A0) / df2c0
-- the map-clip helper 18364 (falls through into the routed map-transfer block 183c6) and the boot input check 2634 (BYTE 300000 through the declared
external-read queue).  No computed jump, no JSR (An), no C consumer.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9 / pc1) with declared host edits.
This code runs natively only in the IO observation (P1 / P1b / boot-title-start; fx-c/n-input-read for 2634): besides the declared worlds the 'natural'
family takes the frame-start states of the IO native observation (artifacts/animation_machine_io_native/states, observe_animation_machine_io.read_pack)
in which a node holds one of the unit's installed values, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node,
A7 = 10ef00 with the sentinel return LONG, PC = the callback); the 'reinstall' family takes the same states with one declared callback LONG ((A6) := a
creation callback / 28ae child entry on a natural node of the same kind: these entries are installed and run inside one frame).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start is entered directly (the seed world with declared edits).  The Z readers de8f4 / de938 are entered with a non-zero Z source
            only (the native start has Z = 0, contract decision 3: BYTE -7699(A5) / BYTE (A0) with A0 one of 10fdb0 10fdb1 100004 100005); their Z = 1
            side comes from the node / natural runs through ca50 / 4a974.  2634 is entered with a declared queue BYTE 300000.  Stop: the first PC
            outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds, at most NATURAL_CAP per callback) up to the sentinel or the first unrouted PC; reinstall: the same
            with a declared callback LONG.
  callee    the subroutines 2634 (with a queue BYTE) 18364 de8bc df272 df2c0 entered with the return LONG = sentinel.
  error     every even non-start PC of the unit ranges, an odd PC, the Z sources outside work RAM / the four credit BYTEs, the empty / mismatched queue at
            2634, odd node / stack / A0, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired
            'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..pc1 specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, pc1)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'se1'
ERROR_PC = 'unsupported animation select e1 PC'
ERROR_FLAG = 'unsupported animation select e1 flag source'
QUEUE_EMPTY = 'animation machine external read queue empty'
QUEUE_MISMATCH = 'animation machine external read queue mismatch'

RANGES = [(0x2634, 0x264a), (0x18364, 0x183c6), (0xde8bc, 0xdf2d0)]
STARTS = sorted(int(x, 16) for x in (
    '2634 2642 2648 18364 1837c 18384 1838a 18390 18392 183aa 183b2 183b8 183c0 183c4 de8bc de8c2 de8c8 de8ca de8d2 de8da de8de de8ee de8f4 de8f8 '
    'de90c de910 de91a de922 de92e de938 de93c de944 de948 de94c de950 de960 de964 de978 de97e de990 de99e de9b8 de9e0 de9e8 de9fa dea08 dea16 dea2a '
    'dea50 dea58 dea62 dea6c dea76 dea7c dea86 dea8e dea98 deaa0 deaae deab2 deaba deb02 deb18 deb1a deb2c deb3a deb5e deb9c deba4 debce debde debee '
    'dec10 dec16 dec1e dec26 dec2c dec30 dec38 dec46 dec56 dec5c dec66 dec6c dec6e dec76 dec78 dec8c dec9c deca4 decac decb2 decbc decc4 deccc decd2 '
    'decda decee decfe ded00 ded06 ded0e ded1e ded28 ded50 ded72 ded88 ded94 ded98 ded9c ded9e deda4 dedae dedb4 dedb6 dedc8 dedd6 dedf4 dee22 dee28 '
    'dee2e dee34 dee36 dee48 dee5e dee70 dee86 dee8a dee92 deea8 deeac deeb4 deeca deece deed6 deeec deef0 def20 def2a def32 def40 def4a def50 def56 '
    'def58 def80 def8c def92 def98 defa0 defba defc0 defce defd4 defda defdc defee df00e df01c df02a df038 df052 df06c df076 df07e df086 df08c df096 '
    'df09e df0a6 df0ac df0b0 df0be df0d2 df0ea df0f0 df0f2 df0fc df116 df11e df122 df126 df128 df132 df14c df154 df158 df15c df15e df16e df176 df17e '
    'df18c df192 df19c df1a4 df1ac df1ba df1c0 df1cc df1d6 df1de df1f6 df1fa df202 df21a df224 df22a df22e df230 df248 df254 df25c df264 df26c df270 '
    'df272 df292 df2aa df2be df2c0 df2ce').split())
CONSUMERS = ()                          # no C consumer in this unit
CLEAR_SET = ()
SET_SET = ()
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS passes an incoming C to a reader in this unit
STARTS_SET = set()
# Z readers (contract decision 3): de8f4 BEQ after JSR ca50 (TST.B -7699(A5); RTS): Z := BYTE -7699(A5) == 0; de938 BEQ after JSR 4a974 (TST.B (A0);
# RTS): Z := BYTE (A0) == 0 with A0 one of the four credit BYTEs.
Z_RECOMPUTE = {0xde8f4: 'ca50', 0xde938: 'credit'}
Z_ADDR = -0x7699
CREDIT_BYTES = (0x10fdb0, 0x10fdb1, 0x100004, 0x100005)
Z_OTHER = {0xde8f4: 0xde8f8, 0xde938: 0xde93c}          # the Z = 0 successor of each reader (the side a direct native entry takes)
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
LATER_GATED = set()
TRAPS = ()
EXIT_STOPS = ()                         # no later-unit start is reached by an E1 block (every exit is routed)
CHAINS = ()
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()
TABLE_ENTRIES = ()
INPUT_PORT = 0x300000
# callbacks, installed values and 28ae children (node callbacks); the subroutines entered with the sentinel return LONG
CREATION = (0xde8ca, 0xde97e, 0xde9e8, 0xdeb1a, 0xdeba4, 0xdefdc, 0xdedb6, 0xdee36)
INSTALLED = (0xde8bc, 0xde8ee, 0xdea50, 0xdec10, 0xdec6e, 0xdec8c, 0xded00, 0xded9e, 0xdee28, 0xdef32, 0xdef58, 0xdef8c, 0xdefc0, 0xdf06c, 0xdf0f2,
             0xdf128, 0xdf15e, 0xdf230, 0xdf254)
NODE_ENTRIES = CREATION + INSTALLED
CALLEES = (0x2634, 0x18364, 0xde8bc, 0xdf272, 0xdf2c0)
STACK = {}
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26)   # node links and pointer fields: natural or declared below
NATURAL = tuple([('P1', 94, f) for f in (6, 31, 34, 62, 66, 67, 73, 74, 75, 113, 132, 133, 136)] + [('P1', 68, f) for f in (226, 251, 290, 348)] +
                [('P1b', 94, f) for f in (6, 113)] + [('boot-title-start', None, f) for f in (126, 233)])
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
NATURAL_CAP = 4                         # natural fixtures per callback value (the frames above in order)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node)); the node held the entry's first installed state in that frame
REINSTALL = (('P1', 94, 6, 0x1011a8, 0xde8ca), ('P1', 94, 6, 0x1010e4, 0xde97e), ('P1', 94, 67, 0x101c60, 0xde9e8), ('P1', 94, 67, 0x101950, 0xdeb1a),
             ('P1', 94, 6, 0x101330, 0xdeba4), ('P1', 94, 6, 0x101640, 0xdefdc), ('P1', 94, 113, 0x101020, 0xdedb6), ('P1', 94, 113, 0x101de8, 0xdee36),
             ('boot-title-start', None, 126, 0x10126c, 0xde8ca), ('boot-title-start', None, 187, 0x101d24, 0xde9e8),
             ('P1', 68, 226, 0x10157c, 0xdeba4), ('P1', 68, 226, 0x10188c, 0xdefdc), ('P1', 68, 329, 0x10126c, 0xdedb6),
             ('P1', 68, 329, 0x101de8, 0xdee36))

VB = (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x1f, 0x20, 0x7f, 0x80, 0x81, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 0xf, 0x10, 0x1f, 0x20, 0x7f, 0x80, 0xff, 0x100, 0x12c, 0x13c, 0x13d, 0x147, 0x148, 0x165, 0x166, 0x16f, 0x170, 0x1af, 0x1b0,
      0x7fff, 0x8000, 0x8001, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x8000, 0xffff, 0x10000, 0x30000, 0x7fffffff, 0x80000000, 0xffff0000, 0xffffffff, 0x12345678)
HX = re.compile(r'(-?)\$([0-9a-f]+)\(a([0-7])\)')
BCC = re.compile(r'^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$')


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
    require(len(_ROUTE) >= 116, ('routing rules', len(_ROUTE)))


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
BUNDLED = ()                            # no bundled Bcc pair in this unit


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (183c4 falls into the routed 183c6)."""
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
        if mn in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra') or BCC.match(mn) or a in STARTS_SET or not mine(a) or len(out) > 60:
            break
    _BLK[start] = out
    return out


def target(op):
    m = re.search(r'\$([0-9a-f]+)', op.split(',')[-1])
    return int(m.group(1), 16) if m else None


def static_next(start):
    """Static successors of the entry block (None = computed: RTS)."""
    instrs = block_instrs(start)
    a, mn, op, size, _ = instrs[-1]
    if BCC.match(mn) or mn == 'dbra':
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op and '(a' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr', 'jmp'):
        return None
    return {a + size}


def block_next(entry, n, tr):
    """The PC after the entry block: pcs[n] (no bundled Bcc pair in this unit)."""
    pcs = tr['pcs']
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
            if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'abcd'):
                sz = 1
            for m in HX.finditer(op):
                disp = int(m.group(2), 16) * (-1 if m.group(1) else 1)
                out.add((int(m.group(3)), disp, sz))
    return sorted(out)


# ---------------------------------------------------------------------------------------------------------------------
# Native tracer (selection of worlds only: every kept world is re-run by the V1 verifier, native versus C++)
# ---------------------------------------------------------------------------------------------------------------------
def trace(state, outside, cap=CAP_INSN, queue=()):
    """Run the original from state.pc natively until `outside(pc, prev, size)` is true (checked from the second instruction on).  `queue` declares the
    BYTE input port reads (address, size, value) in order: each read must match the front entry.  -> dict(pcs, stop, sr, consumed) or None."""
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
    rest = list(queue)
    bad = []

    def code(uc, pc, size, user):
        if box.get('stop') == -1:
            return
        if pcs and outside(pc, pcs[-1], box.get('size', 0)):
            box['stop'] = pc
            uc.emu_stop()
            return
        pcs.append(pc)
        box['size'] = size

    def port(uc, access, address, size, value, user):
        if not (0x300000 <= address < 0x400000):
            return
        if not rest or rest[0][:2] != (address, size):
            bad.append((address, size))
            uc.emu_stop()
            return
        _, n, v = rest.pop(0)
        uc.mem_write(address, v.to_bytes(n, 'big'))
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    c.hook_add(unicorn.UC_HOOK_MEM_READ, port, begin=0x300000, end=0x3fffff)
    try:
        c.emu_start(state['pc'], 0xffffff, count=cap)
    except unicorn.UcError:
        return None
    stop = box.get('stop')
    if stop is not None and (stop & 1):
        return None
    consumed = len(queue) - len(rest)
    dev = [d for d in m.dev_reads]
    if stop is None or bad or m.odd is not None or m.invalid is not None or m.intr is not None or m.fetch_unmapped is not None:
        return None
    if dev != [tuple(q[:2]) for q in queue[:consumed]]:
        return None                                     # an undeclared device read (or one outside the queue)
    # Unicorn evaluates the M68000 condition codes lazily: reg_read(SR) returns stale flags.  MOVE SR,D0 on a scratch page forces the evaluation.
    c.mem_map(SCRATCH, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE | unicorn.UC_PROT_EXEC)
    c.mem_write(SCRATCH, b'\x40\xc0\x4e\x71')
    box['stop'] = -1
    c.emu_start(SCRATCH, SCRATCH + 2, count=1)
    return dict(pcs=pcs, stop=stop, ports=len(m.ports), sr=c.reg_read(S.UC_REG['d0']) & 0xffff, consumed=consumed)


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
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24} | set(EXIT_STOPS) | set(TRAPS)

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


def zsource(state, pc):
    """The Z source BYTE of a reader in a state, or None when the source is not one the C++ accepts."""
    if Z_RECOMPUTE[pc] == 'ca50':
        return state['ram'][(state['regs']['a5'] + Z_ADDR) & 0xffff]
    a0 = state['regs']['a0']
    return state['ram'][a0 & 0xffff] if a0 in CREDIT_BYTES else None


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
        """-> (state, queue)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d1'] = rng.choice((0xffff, 0xffffffff, 1, 0x10001, 0, 2, 0x1ffff))         # the 4e186 answer D1.W (ffff / 1 / 0)
        if rng.random() < 0.5:
            regs['d2'] = rng.choice((0, 1, 2, 3, 0x10000, 0x10001, 0xffff0003))           # the 4e186 slot D2.W
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        parent = self.pointer()
        writes.append(((a6 + 0xc) & 0xffff, 4, parent))                # the parent LONG c(A6) (dec78 / deef0 / df0b0 / df0fc / df132)
        for off, size in ((0x62, 1), (0x63, 1), (0x2e, 2)):
            if rng.random() < 0.7:
                writes.append(((parent + off) & 0xffff, size, self.value(size)))
        writes.append(((a6 + 0x7a) & 0xffff, 2, rng.choice((0, 1, 2, 3, 0, 1, self.value(2)))))   # WORD 7a: the slot / character index
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4 (callee worlds)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp == 0x7a):
                continue                                        # callback LONG, node links, pointer fields and the index stay natural or declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        writes.append((sp & 0xffff, 4, ret))
        queue = []
        if entry == 0x2634:
            queue = [(INPUT_PORT, 1, rng.choice((0, 0x10, 0x20, 0x40, 0x70, 0x8f, 0xff, rng.getrandbits(8))))]
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a5off', []):
                writes.append(((a5 + off) & 0xffff, size, val))
            regs.update(hint.get('regs', {}))
            if hint.get('mirror'):
                regs['a6'] = a6 | 0xf0000                       # the node in the upper RAM mirror (1fxxxx = 10xxxx)
            for off, size, val in hint.get('parent', []):
                writes.append(((a6 + 0xc) & 0xffff, 4, regs['a2'] | (0xf0000 if hint.get('parent_mirror') else 0)))   # the parent (A2's node)
                writes.append(((regs['a2'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for w in hint.get('writes', []):
                writes.append(w)
            at = sp
            for size, val in hint.get('stack', []):
                writes.append((at & 0xffff, size, val))         # what a block pops first (deaba / deb02 WORD, df038 LONG, df292 / df2aa MOVEM.L)
                at += size
            if 'queue' in hint:
                queue = [(INPUT_PORT, 1, hint['queue'])]
        if entry == 0xde938 and regs['a0'] not in CREDIT_BYTES:
            regs['a0'] = rng.choice(CREDIT_BYTES)               # the C++ accepts only the four credit BYTEs as the Z source (decision 3)
        state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        # the Z readers recompute the Z: the native direct entry starts with Z = 0, so the Z source must not be 0 (contract decision 3)
        if entry in Z_RECOMPUTE and zsource(state, entry) == 0:
            addr = ((state['regs']['a5'] + Z_ADDR) if Z_RECOMPUTE[entry] == 'ca50' else state['regs']['a0']) & 0xffff
            writes.append((addr, 1, rng.choice((1, 0x80, 0xff))))
            state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        return state, queue


out_missing = []
unreachable = []
META = {}


class Base(object):
    def __init__(self, state, stop):
        self.state, self.stop = state, stop


def build():
    del out_missing[:], unreachable[:]
    load_routing()
    global STARTS_SET
    STARTS_SET = set(STARTS)
    _BLK.clear()
    require(len(STARTS) == 222 and len(STARTS_SET) == 222, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for s in STARTS:
        require(unit_of(s) == 'animation_select_e1_block', ('start is not routed to select e1', hex(s), unit_of(s)))
    rng = random.Random(0xE1A1)
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
                cond_points[a] = set(t for t in (target(op), a + size) if (a, t) not in STATIC_IMPOSSIBLE and (s, t) not in LATER_GATED)
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        n = len(block_instrs(entry))
        needed = static_next(entry)
        if needed is not None and entry in Z_RECOMPUTE:
            needed = set([Z_OTHER[entry]])              # the native start has Z = 0: only the Z = 0 side; the Z = 1 side comes from the node runs
        flds = fields_of(entry)
        kept = {}
        extra = 0
        hints = hint_worlds(entry, world)
        for t in range(MAX_TRIES + len(hints)):
            stats['tries'] += 1
            st, q = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
            tr = trace(st, outside_unit(), queue=q)
            if tr is None or len(tr['pcs']) < n:
                stats['rejected'] += 1
                continue
            record(tr['pcs'] + [tr['stop']])
            nxt = block_next(entry, n, tr)
            if mine(nxt) and nxt not in STARTS_SET:
                continue
            if t < len(hints):
                kept[('h', t)] = (st, tr, q)
                if nxt not in kept:
                    kept[nxt] = (st, tr, q)
            elif nxt not in kept:
                kept[nxt] = (st, tr, q)
            elif extra < 1 and (needed is None or len(needed) <= 1):
                extra += 1
                kept[(nxt, extra)] = (st, tr, q)
            if needed is not None and len(needed) > 1 and set(k for k in kept if isinstance(k, int)) >= needed and t >= len(hints):
                break
            if (needed is None or len(needed) <= 1) and len(kept) >= 2 and t >= len(hints):
                break
        require(kept, ('no world for the block', hex(entry)))
        seen_worlds = set()
        for i, key in enumerate(sorted(kept, key=lambda k: (0, k) if isinstance(k, int) else (1, str(k)))):
            st, tr, q = kept[key]
            if id(st) in seen_worlds:
                continue
            seen_worlds.add(id(st))
            add(U.Fixture('block-%05x-%d' % (entry, i), st, q, tr['stop'], meta=dict(family='block', entry=entry, successor=block_next(entry, n, tr))))
        if needed and len(needed) > 1:
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)) - set(t for a, t in STATIC_IMPOSSIBLE))
            if missing:
                out_missing.append((entry, missing))
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
        cands = sorted(entries_for.get(blk, [blk]), key=lambda e: (e != blk, e))
        if blk in Z_RECOMPUTE:
            cands = [e for e in cands if e != blk]
        for entry in cands[:6]:
            flds = fields_of(entry)
            for k in range(MAX_TRIES):
                hs = hint_worlds(entry, world)
                chint = hs[k % len(hs)] if hs and k % 2 else None
                st, q = world.make(entry, SENTINEL, flds, chint)
                tr = trace(st, outside_unit(), queue=q)
                if tr is None:
                    continue
                record(tr['pcs'] + [tr['stop']])
                if (a, t) in covered:
                    add(U.Fixture('cover-%05x-%05x' % (a, t), st, q, tr['stop'], meta=dict(family='coverage', entry=entry, branch=a, outcome=t)))
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
    META['static_impossible'] = [(hex(a), hex(t)) for a, t in sorted(STATIC_IMPOSSIBLE)]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('se1 spec: %d fixtures (%d natural), visited %d/222, missing successors %s, unreachable outcomes %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('se1: carry oracle skipped (no harness binary)\n')
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
            tr = trace(fx.state, lambda pc, prev, size, stop=fx.stop: pc == stop, cap=U.DEFAULT_MAX_INSN, queue=fx.queue)
            require(tr is not None, ('carry oracle: native run failed', fx.name))
            require(got['carry'] == (2 if tr['sr'] & 1 else 1), ('carry tag differs from the original CPU C flag', fx.name, got['carry'], tr['sr'] & 1))
    finally:
        harness.close()
    sys.stderr.write('se1: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (signed BLT / BGT / BGE of
    CMPI.W #170 / #1b0 / #12c / #10 / #20 and CMPI.B #2, unsigned BCC of CMPI.W #148 and of the 18364 clip, SUBQ.W #1 to 0 / ffff, the WORD 7a index
    0..3 and beyond, the 4e186 answers D1.W = ffff / 1 with garbage above, D2.W = 7a or not, the Z sources (BYTE -7699(A5), the credit BYTEs), the queue
    BYTE of 2634 (bits 4..6), ASR.W #4 of negative WORDs), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every
    hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0xde8d2, 0xde8da, 0xde8f8, 0xde910, 0xde922, 0xde92e, 0xde950, 0xde964, 0xde990, 0xde99e, 0xde9b8, 0xde9fa, 0xdea16, 0xdea7c, 0xdeaba,
                 0xdeb02, 0xdeb2c, 0xdeb3a, 0xdeb5e, 0xdeba4, 0xdebce, 0xdebde, 0xdebee, 0xdec8c, 0xdecda, 0xded1e, 0xded28, 0xded50, 0xdedd6, 0xdedf4,
                 0xdee48, 0xdee5e, 0xdee70, 0xdeef0, 0xdef20, 0xdef58, 0xdefa0, 0xdefee, 0xdf00e, 0xdf038, 0xdf06c, 0xdf0d2, 0xdf116, 0xdf14c, 0xdf1c0,
                 0xdf1d6, 0xdf1de, 0xdf1fa, 0xdf230, 0xdf272, 0xdf292, 0xdf2aa, 0xdf2c0, 0x2634, 0x18364, 0x18392):
        h += [dict(regs=dict(up))]
    # ---- slot text de8ca
    if entry in (0xde8ca, 0xdee5e, 0xdecda, 0xdee48, 0xdeb3a, 0xdeb5e, 0xdeba4, 0xdedd6, 0xdefee, 0xdef58, 0xdefa0, 0xdf0d2, 0xdf1de, 0xdf202, 0xdf230,
                 0xdf272, 0xde910, 0xde92e, 0xdea7c, 0xdeaba):
        h += word(0x7a, (0, 1, 2, 3))
    if entry == 0xde8ca:
        h += word(0x7a, (0x100, 0x8000)) + [dict(mirror=True, a6off=[(0x7a, 2, 1)])]
    if entry in (0xde8ee,):
        h += [dict(a5off=[(Z_ADDR, 1, z)]) for z in (0, 1, 0x80, 0xff)]
    if entry == 0xde8f4:
        h += [dict(a5off=[(Z_ADDR, 1, z)]) for z in (1, 0x80, 0xff)] + [dict(mirror=True, a5off=[(Z_ADDR, 1, 1)])]
    if entry == 0xde938:
        h += [dict(regs=dict(a0=a), writes=[(a & 0xffff, 1, v)]) for a, v in ((0x10fdb0, 1), (0x10fdb1, 0x80), (0x100004, 0xff), (0x100005, 2))]
    if entry == 0xde91a:
        h += regs('d1', (0xffff, 0xfffe, 0x1ffff, 0, 0xffff0000, 0xffffffff))
    if entry == 0xde922:
        h += word(0x76, (0x10, 0, 0xffef, 0x1010, 0xffff, 0x8000))
    if entry == 0xde978:
        h += word(0x76, (0xffff, 0x7fff, 0))
    # ---- cursor blink de9e8 / dea50
    if entry in (0xdea50, 0xdec1e, 0xdef98, 0xdf25c, 0xded98):
        h += word(0x76, (1, 0, 2, 0x8000, 0x10))
    if entry == 0xdea58:
        h += byte(0x62, (0xff, 0x7f, 0))
    if entry == 0xdea62:
        h += byte(0x62, (0, 1, 2, 0xff, 0xfe))
    if entry in (0xdea6c, 0xdea76):
        h += [dict(a6off=[(0x19, 1, 0x81), (0x1a, 1, 0x7e)])]
    if entry in (0xdea86, 0xdf076, 0xdf096, 0xdf176, 0xdf1a4):
        h += regs('d1', (0xffff, 0xfffe, 0x1ffff, 0xffff0000, 0xffffffff, 1))
    if entry in (0xdec9c, 0xdecbc, 0xdf17e, 0xdf1ac):
        h += regs('d1', (1, 0x10001, 2, 0, 0xffff0001))
    if entry == 0xdea8e:
        h += [dict(regs=dict(d2=d), a6off=[(0x84, 1, b)]) for d, b in ((0x12340003, 0), (1, 1), (0xffff, 0x80))]
    if entry == 0xdea98:
        h += [dict(regs=dict(d2=d), a6off=[(0x82, 2, w)]) for d, w in ((0x12340003, 3), (3, 4), (0xffff0000, 0), (0x10001, 0x1))]
    if entry in (0xdeaa0, 0xdeab2):
        h += regs('d2', (0x12345678, 0xffff))
    if entry in (0xdeaba, 0xdeb02):
        h += [dict(a6off=[(0x7a, 2, k)], stack=[(2, d)]) for k, d in ((0, 0), (1, 1), (0, 2), (1, 3))]
    # ---- portrait slide deba4 / dec10 ..
    if entry == 0xdebee:
        h += regs('d0', (0, 9, 0xffec, 0x1234ffff))
    if entry == 0xdec16 or entry == 0xdecd2:
        h += byte(0x63, (0, 1, 0x80, 0xff))
    if entry == 0xdec30:
        h += word(0x78, (0, 1, 0x8000))
    if entry == 0xdec38:
        h += word(0x32, (1, 0, 0x8001))
    if entry == 0xdec46:
        h += word(0x32, (0x165, 0x166, 0x167, 0x7ffa, 0x7ff5, 0xfff0, 0x1a6, 0x1a5))
    if entry == 0xdec5c:
        h += word(0x32, (0x1af, 0x1b0, 0x8000, 0xffff, 0x7fff))
    if entry in (0xdec6e, 0xdf0be):
        h += byte(0x62, (0, 1, 0x80))
    if entry == 0xdec78:
        h += [dict(parent=[(0x62, 1, v)]) for v in (0xff, 0, 0x7f)] + [dict(parent_mirror=True, parent=[(0x62, 1, 1)])]
    if entry in (0xdeca4, 0xdecc4, 0xdf07e, 0xdf09e, 0xdf16e, 0xdf19c):
        h += [dict(regs=dict(d2=d), a6off=[(0x7a, 2, w)]) for d, w in ((0x12340001, 1), (1, 2), (0xffff0000, 0), (0x10003, 3), (0x10000, 1))]
    if entry == 0xded06 or entry == 0xdf254:
        h += word(0x76, (0, 1, 0x8000, 0x100))
    if entry == 0xded0e:
        h += word(0x32, (0x13c, 0x13d, 0x800f, 0x8010, 0xfff0, 0))
    if entry == 0xdeda4:
        h += word(0x78, (0xf, 0x10, 0x8000, 0x7fff, 0xffff))
    if entry == 0xdedae:
        h += word(0x80, (0x8001, 0x12c))
    if entry in (0xdee8a, 0xdeeac, 0xdeece):
        h += regs('d0', (1, 2, 3, 4, 0x10001, 0x10002, 0x10003, 0xffff0000))
    if entry == 0xdee5e:
        h += word(0x7a, (4, 0x100, 0xffff))
    if entry == 0xdeef0:
        h += [dict(parent=[(0x2e, 2, v)]) for v in (0x8001, 0x1234)]
    if entry == 0xdef32:
        h += [dict(a6off=[(0x3a, 4, v)]) for v in (0, 0x5000, 0x4fff, 0x80000000)]
    if entry == 0xdef40:
        h += word(0x32, (0x147, 0x148, 0x8000, 0xffff, 0x149))
    if entry == 0xdf0b0:
        h += [dict(parent=[(0x63, 1, v)]) for v in (1, 2, 0x80, 0x7f, 3)]
    if entry in (0xdf0f2, 0xdf128):
        h += word(0x78, (0x1f, 0x20, 0x8000, 0x7fff, 0xffff))
    if entry in (0xdf0fc, 0xdf132):
        h += [dict(parent=[(0x62, 1, 0x12)])]
    if entry in (0xdf116, 0xdf14c, 0xdf11e, 0xdf154):
        h += word(0x78, (0, 0x1f, 0xffff))
    if entry == 0xdf1c0:
        h += [dict(a6off=[(0x62, 1, a), (0x85, 1, b)]) for a, b in ((1, 1), (1, 2), (0, 0), (2, 0), (0x81, 1))]
    if entry == 0xdf1cc:
        h += regs('d0', (0, 0x100, 1, 0x12345602, 0xffffff00))
    if entry == 0xdf21a:
        h += byte(0x62, (2, 0x82, 1, 0))
    # ---- 18364: the clip compares (unsigned BCC / BCS) and ASR.W #4 of a negative WORD
    if entry in (0x18364, 0x1837c, 0x1838a, 0x18392, 0x183aa, 0x183b8):
        h += [dict(regs=dict(d2=0x16, d3=0x10, d4=0, d5=0x10, d0=0x12340000, d1=0x56780000), a0off=[(0x14, 2, a), (0x18, 2, b)])
              for a, b in ((0, 0), (0x8000, 0x7ff0), (0xfff0, 0x10), (0x100, 0x900), (0x200, 0xff00), (0x7fff, 0x8000), (0xa0, 0x60))]
        h += [dict(regs=dict(d2=d2, d4=d4, d7=d7, d3=d3, d5=d5)) for d2, d4, d7, d3, d5 in ((0x16, 0x16, 0x16, 0x10, 0x10), (0x10, 0xf, 0x30, 0x1, 0x2),
                                                                                         (0xffff, 0, 0x10, 0xffff, 0), (5, 4, 4, 7, 7))]
    if entry == 0x2634:
        h += [dict(queue=v) for v in (0, 0x10, 0x20, 0x40, 0x70, 0x8f, 0xff, 0x0f)]
    if entry == 0xdf038:
        h += [dict(stack=[(4, v)]) for v in (0, 4, 8, 0xc, 0xffff0008, 0x12340004)]
    if entry in (0xdf292, 0xdf2aa):
        h += [dict(stack=[(4, d2), (4, a0)], a6off=[(0x1a, 1, b1), (0x1b, 1, b2)]) for d2, a0, b1, b2 in (
            (0x12345678, 0xde5a8, 0xff, 0x7f), (0x20, 0xde5ae, 0x80, 0), (0xffff0000, 0xde5b4, 1, 0xfe), (0, 0xde5ba, 0x7f, 0x81))]
    if entry in (0xdf272, 0xdf292, 0xdf2aa, 0xdf2c0):
        h += [dict(a6off=[(0x19, 1, 0xff), (0x1a, 1, 0x80), (0x1b, 1, 0x7f), (0x7a, 2, k)]) for k in (0, 1, 2, 3)]
    if entry in (0xde8de, 0xdea2a, 0xdebee, 0xdf052, 0xdecee, 0xded88, 0xdee22, 0xdef80, 0xdefba, 0xdf248):
        h += [dict(mirror=True)]
    return h


def chain_fixtures(world, add, record):
    """No C consumer in this unit (no producer chain)."""
    return None


def add_run(add, name, st, tr, meta, queue=()):
    add(U.Fixture(name, st, queue, tr['stop'], meta=meta))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # WORD 7a (slot 0 / 1 / character 0..3), WORD 76 / 78 / 32 counters, BYTE 62 / 63 / 84 / 85, the Z sources (BYTE -7699(A5), the credit
            # BYTEs with BYTE 10fd82 = 0 so that 4a974 takes 100004 / 100005), the 4e186 slot nodes 1009a8 / 100a6c (LONG (A0) = 270e -> D1 = ffff,
            # else BYTE 9c 1 / 2 -> D1 = 0 / 1 with D2 = BYTE 98), BYTE 1d(A6) < 4, WORD 104ca0 (28ae count limit; > 0 succeeds)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x7a, 2, (0, 1, 2, 3, 0, 1)[t % 6]), (0x76, 2, (0, 1, 2, 0x10, 0x1e)[t % 5]),
                               (0x78, 2, (0, 0x1f, 0x20, 0xf, 0x10)[(t // 2) % 5]), (0x32, 2, (0x12c, 0x13c, 0x170, 0x1b0, 0x148, 0x147)[t % 6]),
                               (0x62, 1, (0, 1, 2)[(t // 3) % 3]), (0x63, 1, (0, 1, 2)[(t // 2) % 3]), (0x84, 1, (0, 0xff)[t % 2]),
                               (0x85, 1, (0, 1, 2)[t % 3]), (0x82, 2, (0xffff, 0, 1)[t % 3])],
                        a5off=[(Z_ADDR, 1, (0, 1)[(t // 7) % 2])],
                        writes=[(0x4ca0, 2, (0x100, 0x15, 0x40)[(t // 11) % 3]), (0xfd82, 1, 0), (0x0003, 1, (0, 1)[t % 2]),
                                (0x0004, 1, (0, 1)[(t // 2) % 2]), (0x0005, 1, (1, 0)[(t // 3) % 2]),
                                (0x09a8, 4, (0x270e, 0x4e94e, 0x4e94e)[t % 3]), (0x0a6c, 4, (0x270e, 0x4e94e)[(t // 3) % 2]),
                                (0x0a44, 1, (1, 2, 0)[t % 3]), (0x0b08, 1, (2, 1, 0)[(t // 2) % 3]), (0x0a40, 1, t % 4), (0x0b04, 1, (t // 2) % 4)])
            st, q = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000, queue=q)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], len(set(tr['pcs']) & STARTS_SET) // 3)
            if key in kept:
                continue
            kept[key] = (st, tr, q)
            if len(kept) >= 4:
                break
        require(kept, ('no node world', hex(entry)))
        for i, (key, (st, tr, q)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add_run(add, 'node-%05x-%d' % (entry, i), st, tr, dict(family='node', entry=entry, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)), q)


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
    callback LONG (at most NATURAL_CAP per callback value); declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the
    callback, the other registers as at the frame start.  Up to the sentinel or the first unrouted PC.  The reinstall worlds write one declared callback
    LONG first (REINSTALL)."""
    entries = set(NODE_ENTRIES)
    count = 0
    per = {}
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        for a in range(NATURAL_NODES[0] & 0xffff, NATURAL_NODES[1] & 0xffff, 2):
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if cb not in entries or per.get(cb, 0) >= NATURAL_CAP:
                continue
            regs = dict(st0['regs'])
            regs.update(a5=0x108000, a6=0x100000 + a, a7=0x10ef00)
            st = U.make_state(ram, regs, cb, st0['bank'], st0['pvc'])
            st = U.with_host_writes(st, [(0xef00, 4, SENTINEL)])
            tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            add_run(add, 'natural-%05x-%s%s-f%d-%x' % (cb, cfg, '' if case is None else '%03d' % case, frame, 0x100000 + a), st, tr,
                    dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=0x100000 + a, stop=tr['stop'],
                         unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
            per[cb] = per.get(cb, 0) + 1
            count += 1
    for cfg, case, frame, node, cb in REINSTALL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        regs = dict(st0['regs'])
        regs.update(a5=0x108000, a6=node, a7=0x10ef00)
        st = U.make_state(st0['ram'], regs, cb, st0['bank'], st0['pvc'])
        st = U.with_host_writes(st, [(0xef00, 4, SENTINEL), (node & 0xffff, 4, cb)])
        tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
        require(tr is not None, ('reinstall world failed', cfg, case, frame, hex(node)))
        record(tr['pcs'] + [tr['stop']])
        add_run(add, 'reinstall-%05x-%s%s-f%d-%x' % (cb, cfg, '' if case is None else '%03d' % case, frame, node), st, tr,
                dict(family='reinstall', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
        count += 1
    require(count >= 40, ('too few natural node fixtures', count))


def callee_fixtures(world, add, record):
    """The subroutines (return LONG = sentinel); 2634 with a declared queue BYTE."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry, world)
        for t in range(60 + len(hints)):
            hint = hints[t] if t < len(hints) else None
            st, q = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(), cap=400000, queue=q)
            if tr is None:
                continue
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], tuple(p for p in tr['pcs'] if p in STARTS_SET)[:40])
            if key in kept:
                continue
            kept[key] = (st, tr, q)
            if len(kept) >= 4 and t >= len(hints):
                break
        require(kept, ('no callee world', hex(entry)))
        for i, (key, (st, tr, q)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add_run(add, 'callee-%05x-%d' % (entry, i), st, tr, dict(family='callee', entry=entry, stop=tr['stop']), q)


def error_fixtures(bases, add):
    """Checked errors with the failing PC (Fixture fail_pc and meta, review 0264 L-1).  A failing PC that differs from the entry (and is even) gets a paired
    'match' row with stop = the failing PC (both sides stop exactly there).  The error row's stop is the PC right after the failing block."""
    base = bases[0]
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL)])
    starts = set(STARTS)

    def err(name, state, text, fail_pc, stop=SENTINEL, queue=()):
        add(U.Fixture('error-' + name, state, queue, stop, ('error', text), fail_pc=fail_pc, meta=dict(family='error', fail_pc=fail_pc)))
        if fail_pc != state['pc'] and not fail_pc & 1:
            add(U.Fixture('failpc-' + name, state, queue, fail_pc, meta=dict(family='failpc', fail_pc=fail_pc)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_PC, pc)
    err('odd-pc', U.with_host_writes(st, pc=0xde8bd), 'unaligned animation machine PC', 0xde8bd)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    # the Z sources (contract decision 3): de8f4 with A5 = 8000 (BYTE 967 of the fixed ROM) / 400000 (3f8967); de938 with A0 outside the credit BYTEs
    err('zsource-rom-de8f4', U.with_host_writes(st, regs=dict(a5=0x8000), pc=0xde8f4), ERROR_FLAG, 0xde8f4)
    err('zsource-io-de8f4', U.with_host_writes(st, regs=dict(a5=0x400000), pc=0xde8f4), ERROR_FLAG, 0xde8f4)
    for a0 in (0x10fdb2, 0x100003, 0x1ffdb0, a6):
        err('zsource-de938-%x' % a0, U.with_host_writes(st, regs=dict(a0=a0), pc=0xde938), ERROR_FLAG, 0xde938)
    #   de8ee (JSR ca50) -> ca50 (TST.B 967 of the ROM, RTS) -> de8f4: the Z source is the fixed ROM
    err('de8ee-then-de8f4', U.with_host_writes(st, regs=dict(a5=0x8000), pc=0xde8ee), ERROR_FLAG, 0xde8f4)
    # the input port of 2634: no queue entry / a queue entry of another device
    err('2634-queue-empty', U.with_host_writes(st, pc=0x2634), QUEUE_EMPTY, 0x2634)
    err('2634-queue-mismatch', U.with_host_writes(st, pc=0x2634), QUEUE_MISMATCH, 0x2634, queue=[(0x340000, 1, 0)])
    # odd node / stack / A0
    err('de8ca-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xde8ca), odd_word, 0xde8ca, stop=0xde8d2)
    err('de8de-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xde8de), odd_write, 0xde8de, stop=0xde8ee)
    err('dea8e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xdea8e), odd_word, 0xdea8e, stop=0xdea98)
    err('de97e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xde97e), odd_word, 0xde97e, stop=0x8ff4)
    err('18364-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x18364), odd_word, 0x18364)
    err('deef0-odd-parent', U.with_host_writes(st, [((a6 + 0xc) & 0xffff, 4, a6 + 1)], pc=0xdeef0), odd_word, 0xdeef0, stop=0x3c44)
    # failures after executed blocks:
    #   de8d2 -> de8de (WORD writes, MOVE.L #de8ee,(A6)) -> de8ee JSR ca50.l at an odd A7
    err('de8d2-then-de8ee', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xde8d2), odd_word, 0xde8ee, stop=0xca50)
    #   dec66 (MOVE.L #dec6e,(A6)) -> dec6c RTS at an odd A7
    err('dec66-then-dec6c', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xdec66), odd_word, 0xdec6c)
    #   df0fc -> df122 JSR de8bc at an odd A7
    err('df0fc-then-df122', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xdf0fc), odd_word, 0xdf122, stop=0xde8bc)
    #   18384 -> 1838a -> 18390 / 18392 -> 18392 reads 18(A0) at an odd A0
    err('18384-then-18392', U.with_host_writes(st, regs=dict(a0=a6 + 1, d7=0, d2=1), pc=0x18384), odd_word, 0x18392)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xdec46, 0xded0e, 0x18364, 0xdf1c0)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, fx.queue, fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, fx.queue, fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, picks[0].queue, picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, picks[0].queue, picks[0].stop, 'mismatch', cpp_queue=list(picks[0].queue) + [(0x300000, 1, 0x5a)]))
    q = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') == 0x2634 and fx.queue]
    if q:
        fx = q[0]
        v = fx.queue[0][2] ^ 0x70
        add(U.Fixture('negative-queue-value', fx.state, fx.queue, fx.stop, 'mismatch', cpp_queue=[(0x300000, 1, v)]))
