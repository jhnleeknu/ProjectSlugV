"""V1 fixture spec of the area-C unit C9 (engine/src/animation_machine_player_c9.cpp, 220 block starts; file prefix pc9 / player_c9 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c9-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.8): the player states
1ec74 -> 1ecb8 (1cb08, 1cab6, 1cd98, 4bfc0 / ce02 / 49fc6, 201a2; the 28ae child 36350), 1f070 / 1f086 -> 1f0ae (the motion record helper 1d092),
1f48a -> 1f4b6 (1cec2, the helper 1d086), the callbacks 1f3e8 / 1fb28 / 20720, the states 208fa (ea680, 1aa3a) -> 20a98 -> 20aec and 20b42 -> 20b96
(the settle helpers 20a4a / 20a6e: LONG SUB, ASR.L #3, ADD; ASR.W #3), 20cd8 -> 20d36 (the 28ae child eaac0, 4970a), 21370 (8ebe on the ROM WORD
tables 1b170 / 1b178, 20efc), and the slot-84 states 21ca4 / 21cd8, 21d0e / 21d2a, 21e48, 2210c -> 22128 -> 22174 (the ROM LONG tables 22074 / 220c0
/ 22028), 22238 / 22240, 223a0 .. 223e8 -> 22408 / 2241c, 22452 with the JMP (A1) 21ce4 21d36 2224c 22428 on the 215e6 lists 21aee / 216c8 (contract
decision 2).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C8) with declared host edits.
This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the 'natural'
family takes the frame-start states of that observation (state packs, read-only) in which the player node 100cb8 holds a C9 block start as its
callback LONG or as its slot-84 LONG 84(A6), keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with
the sentinel return LONG, PC = the callback).  The spec reads those packs itself (io_pack below, observation directory IO_EXT); the shared loader is
unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 14 C consumers and the N reader 22180 is entered directly (the seed world with declared edits).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers and the N reader 22180 through 22174 (CHAINS).  Stop: the successor or the first
            unrouted PC.
  node      the installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers and states entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 14 consumers, the jump-target guard of the four JMP (A1) (decision 2),
            the N source of 22180 outside work RAM / fixed ROM (decision 3), odd node / stack / A0, failures after executed blocks: checked error, state
            preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C8
specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C8)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc9'
ERROR_PC = 'unsupported animation player c9 PC'
ERROR_CARRY = 'player c9 caller requires known carry'
ERROR_JUMP = 'unsupported animation player c9 jump target'
ERROR_FLAG = 'unsupported animation player c9 flag source'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x1d086, 0x1d09e), (0x1ec74, 0x1ed22), (0x1f070, 0x1f082), (0x1f086, 0x1f126), (0x1f3e8, 0x1f3ec), (0x1f48a, 0x1f538), (0x1fb28, 0x1fb2e),
          (0x20720, 0x20738), (0x208fa, 0x2092c), (0x20a4a, 0x20bfe), (0x20c00, 0x20c30), (0x20cd8, 0x20d72), (0x21370, 0x213da), (0x21ca4, 0x21d60),
          (0x21e48, 0x21e52), (0x2210c, 0x22148), (0x22174, 0x221ca), (0x22238, 0x22286), (0x223a0, 0x223fa), (0x22408, 0x22472)]
STARTS = sorted(int(x, 16) for x in (
    '1d086 1d08a 1d092 1d096 1ec74 1ec7e 1ec8e 1ec98 1eca0 1eca4 1eca8 1ecb8 1ecbc 1ecc6 1ecce 1ecd8 1ece0 1ecea 1ecee 1ecf6 1ecfe 1ed04 1ed0e 1ed14 '
    '1ed18 1ed1e 1f070 1f086 1f08a 1f0ae 1f0b2 1f0bc 1f0c4 1f0ce 1f0d6 1f0e0 1f0e4 1f0ec 1f0f4 1f0fe 1f102 1f108 1f112 1f118 1f11c 1f122 1f3e8 1f48a '
    '1f492 1f4b6 1f4ba 1f4c4 1f4cc 1f4d6 1f4de 1f4e2 1f4ea 1f4ee 1f4f6 1f500 1f508 1f510 1f514 1f51a 1f524 1f52a 1f52e 1f534 1fb28 20720 208fa 20900 '
    '20904 2090a 20912 2091a 2091e 20924 20a4a 20a50 20a54 20a6e 20a7e 20a80 20a8e 20a90 20a98 20a9e 20aa4 20abc 20ac4 20aec 20af4 20afc 20b00 20b10 '
    '20b12 20b20 20b22 20b28 20b2e 20b38 20b3e 20b42 20b48 20b50 20b60 20b66 20b6e 20b96 20b9e 20bb4 20bb8 20bc4 20bcc 20bd2 20bd6 20be8 20bee 20c00 '
    '20c0e 20c10 20c16 20c1c 20c26 20c2c 20cd8 20ce8 20cf6 20d02 20d0a 20d36 20d3c 20d44 20d54 20d62 20d6e 21370 21376 2138e 213a6 213b4 213d0 21ca4 '
    '21cae 21cb2 21cb6 21cba 21cbe 21cc2 21cca 21cd8 21ce0 21ce4 21ce6 21cea 21cf2 21cfa 21d02 21d0a 21d0e 21d1c 21d2a 21d32 21d36 21d38 21d3c 21d44 '
    '21d4c 21d54 21d5c 21e48 2210c 22116 22128 22174 22180 22188 2218c 221a2 221b2 221ba 221c2 22238 22240 22248 2224c 2224e 22252 2225a 22262 2226c '
    '22272 22276 2227c 22284 223a0 223ae 223b2 223c0 223c4 223d2 223d6 223e4 223e8 223f6 22408 2241c 22424 22428 2242a 2242e 22436 2243e 22442 22448 '
    '22450 22452 22468 2246e').split())
# the 14 C consumers: BCC 1eca0 (1cb08 of C2), BCC 1ed14 1f118 1f52a (49fc6), BCC 20900 20a50 20bd2 (ea680), BCS 21cae 21cb6 21cbe (21bc6 / 21baa /
# 21c1c of C3), BCC 21ce0 21d32 22248 22424 (215e6 of C3)
CONSUMERS = (0x1eca0, 0x1ed14, 0x1f118, 0x1f52a, 0x20900, 0x20a50, 0x20bd2, 0x21cae, 0x21cb6, 0x21cbe, 0x21ce0, 0x21d32, 0x22248, 0x22424)
CLEAR_SET = ()
SET_SET = ()
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()
STARTS_SET = set()
Z_READERS = (0x22180,)                  # BLT.W on the N of the TST.B 9d(A6) of 22174 (contract decision 3): never entered directly by a native run
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
# C3 21c1c is ANDI.B #fe,CCR; RTS (ROM 023c 00fe 4e75): its C is always Clear, so the Set side 223b2 of the consumer 21cbe has no real producer
STATIC_IMPOSSIBLE = {(0x21cbe, 0x223b2)}
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units that a C9 block reaches by a fall-through or a branch (C10: 1f082 20bfe 22148 22286 223fa), and the still unrouted later-unit stops
# of the C1..C8 blocks that the C9 runs pass through (pc8 EXIT_STOPS that are still unrouted; the TRAP site 4e69a of C1; the interpreter stub successors
# 1dc8e / 1dccc).  Declared stops of the native runs: a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1f082, 0x20bfe, 0x22148, 0x22286, 0x223fa,
              0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x1dc8e, 0x1dccc, 0x1efd6, 0x21dd0, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6,
              0x4e69a,
              # player C10 routes the entries below since C10 (declared stops of the C9 runs, as before C10)
              0x20324, 0x21e04, 0x2228e, 0x22360, 0x252b4)
UNIT_EXITS = EXIT_STOPS[:5]             # the C9 later-unit stops (C10)
ROUTED_LATER = (
    # player C10 (the C10 entries kept as declared stops)
    0x1dc8e, 0x1dccc, 0x1efd6, 0x1f082, 0x20bfe, 0x21dd0, 0x22148, 0x22286, 0x223fa, 0x20324, 0x21e04, 0x2228e, 0x22360, 0x252b4)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the N chain 22174 -> 22180
CHAINS = ((0x1ec98, 0x1eca0), (0x1ed0e, 0x1ed14), (0x1f112, 0x1f118), (0x1f524, 0x1f52a), (0x208fa, 0x20900), (0x20a4a, 0x20a50), (0x20bcc, 0x20bd2),
          (0x21ca4, 0x21cae), (0x21cb2, 0x21cb6), (0x21cba, 0x21cbe), (0x21cd8, 0x21ce0), (0x21d2a, 0x21d32), (0x22240, 0x22248), (0x2241c, 0x22424),
          (0x22174, 0x22180))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()                           # no PC-relative computed jump in C9
JUMP_ROUTED = ()
# the JMP (A1) of C9 (contract decision 2): A1 = the handler LONG that C3 215e6 loaded from the ROM list (21aee for 21cd8 -> 21ce4, 216c8 for 21d2a /
# 22240 / 2241c -> 21d36 / 2224c / 22428); any other A1 is the C++ checked jump-target error (a native run that jumps elsewhere is not a fixture world)
LIST_21AEE = (0x21602, 0x21d60, 0x21e48, 0x21e3a)
LIST_216C8 = (0x21602,)
LIST_JUMPS = {0x21ce4: LIST_21AEE, 0x21d36: LIST_216C8, 0x2224c: LIST_216C8, 0x22428: LIST_216C8}
# computed jumps that the C9 runs reach (C3 2031c table, 201a6 JSR (A4) (from the BRA 201a2 blocks), 21620 / 221de JMP (A1); C4 21c72 JMP (A1); C5
# 20792 2094e 209d6 21f7c; C7 25298; C8 21d9e 21e76; C9 21ce4 21d36 2224c 22428): an unrouted target is a stop even when it is the straight-line
# successor
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36,
                  0x2224c, 0x22428)
TABLE_ENTRIES = ()
# routed slot-84 states (C3, C4 21d92, C8 21e6a, C9 21cd8 21d2a 2210c 22128 22240 2241c 22452) for the worlds
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92, 0x21e6a, 0x21cd8, 0x21d2a, 0x2210c, 0x22128, 0x22240, 0x2241c, 0x22452)
# installed values entered as node callbacks: 1ec74 (1fb28), 1ecb8 (1eca8), 1f0ae (1f08a), 1f3e8 (1f52e, C7 1f334 1f5c8, C8 1f480), 1f4b6 (1f492),
# 20720 (C3 2064e), 20aec (20ac4), 20b96 (20b6e), 20d36 (20d0a); the callee entries (helpers, branch targets of other units' blocks, list handlers,
# the slot-84 states of 201a6 JSR (A4), states entered as subroutines)
NODE_ENTRIES = (0x1ec74, 0x1ecb8, 0x1f0ae, 0x1f3e8, 0x1f4b6, 0x20720, 0x20aec, 0x20b96, 0x20d36)
CALLEES = (0x1d086, 0x1d092, 0x20a4a, 0x1f070, 0x1f48a, 0x1fb28, 0x208fa, 0x21370, 0x21ca4, 0x21d0e, 0x21e48, 0x2210c, 0x223a0, 0x223d6, 0x21cd8,
           0x21d2a, 0x22128, 0x22240, 0x2241c, 0x22452, 0x20a6e, 0x22174, 0x2218c, 0x20bee)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
# natural worlds of the extended observation: (config, case, frame) with the player node 100cb8 holding a C9 callback or slot-84 LONG (scratch
# natscan_c9.py: the first frames per run of the callbacks 1ec74 1f0ae 1f3e8 1f4b6 20720 20b96 and the slot values 2210c 21cd8 21d2a 2241c 22452)
NATURAL = (('X1', 68, 449), ('X1', 68, 474), ('X1', 68, 495), ('X1', 68, 496), ('X1', 94, 233), ('X1', 94, 289), ('X1', 94, 291),
           ('X2', 68, 445), ('X2', 68, 513), ('X2', 68, 650), ('X2', 94, 216), ('X2', 94, 229), ('X2', 94, 265), ('X2', 94, 270), ('X2', 94, 291),
           ('X2', 94, 292), ('X3', 68, 437), ('X3', 68, 448), ('X3', 68, 449), ('X3', 68, 485), ('X3', 68, 536), ('X3', 68, 639), ('X3', 94, 221),
           ('X3', 94, 248), ('X3', 94, 258), ('X3', 94, 259), ('X3', 94, 447), ('X4', 68, 441), ('X4', 68, 444), ('X4', 68, 445), ('X4', 68, 455),
           ('X4', 68, 466), ('X4', 68, 470), ('X4', 68, 517), ('X4', 68, 619), ('X4', 94, 281), ('X4', 94, 284), ('X4', 94, 285), ('X4', 94, 295),
           ('X4', 94, 306), ('X4', 94, 310), ('X4', 94, 357), ('X4', 94, 459), ('X4', 94, 460))
NATURAL_CALLBACKS = NODE_ENTRIES                                      # the C9 states as callback LONG of the player node
NATURAL_SLOTS = (0x21cd8, 0x21d2a, 0x2210c, 0x22128, 0x22240, 0x2241c, 0x22452)   # or a C9 slot-84 LONG (entered from 201a6 JSR (A4))
NATURAL_NODES = (0x100cb8, 0x100da8)    # the player nodes searched (work RAM CPU addresses)
REINSTALL = ()

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x12, 0x13, 0x14, 0x1e, 0x1f, 0x20, 0x40, 0x50, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xef,
      0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x13, 0x14, 0x1e, 0x27, 0x28, 0x29, 0x40, 0x48, 0x7f, 0x80, 0xa0, 0x9f, 0xe0, 0x100,
      0x140, 0x180, 0x200, 0x280, 0x7ffc, 0x7fff, 0x8000, 0x8001, 0x809f, 0x80a0, 0xe0ec, 0xffe0, 0xfffd, 0xfffe, 0xffff)
VL = (0, 1, 2, 7, 8, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x30000, 0x50000, 0xa9800, 0x7fffffff, 0x80000000, 0xfffc0000, 0xfffd0000, 0xfffe0000,
      0xfffffff8, 0xffffffe0, 0xffffffff, 0x12345678)
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
BUNDLED = ()                            # no flag-sharing Bcc pair inside one C9 block (22180 is its own block: decision 3)


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 1f3e8 into C8 1f3ec, 1fb28 into C8 1fb2e, 20720 into C5 20738, 21e48
    into C8 21e52, 1f070 / 20bee / 22128 / 221c2 into the C10 / C3 PC after the range)."""
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
    """Static successors of the entry block (None = computed: RTS, JSR (A1), JMP (A1))."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (none in C9) would use pcs[n - 1]."""
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
            if mn in ('btst', 'bset', 'bclr', 'bchg', 'st', 'seq', 'sne', 'scs', 'smi', 'abcd'):
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
        return None
    seq = pcs + ([stop] if stop is not None else [])
    for i in range(len(seq) - 1):
        if seq[i] in LIST_JUMPS and seq[i + 1] not in LIST_JUMPS[seq[i]]:
            return None                                 # JMP (A1) outside the ROM list: the C++ checked jump-target error (decision 2)
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at an unrouted target of
    the computed jumps that the C9 runs reach (OTHER_JUMP_PCS: C3 / C4 / C5 / C7 / C8 and the C9 JMP (A1) 21ce4 / 21d36 / 2224c / 22428), or at the
    first unrouted PC that is not the straight-line successor of the previous instruction (a PC inside a block of another executor is not a block
    entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24} | set(EXIT_STOPS) | set(TRAPS)

    def outside(pc, prev, size):
        if pc in ex:
            return True
        if prev in JUMP_PCS and pc not in STARTS_SET and pc not in JUMP_ROUTED:
            return True
        if prev in OTHER_JUMP_PCS and unit_of(pc) is None:
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


SCR = 0x10e900                         # declared scratch records in work RAM (zero in the seed worlds): A3 / A4 records of the hint worlds


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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it (as C1..C8): WORD 76(A6) 0..3 (the index of the ROM
        WORD tables 1b170 / 1b178 and of the C3 BYTE table 21ba6), WORD 78 mostly 0 / 1 (the player index), BYTE 9e(A6) 0..3, BYTE 9c 0..5 (the 215e6
        key), LONG 8c(A6) a record whose BYTE 4 is 0..18 (the index of the ROM LONG tables 22028 / 22074 / 220c0 of 2218c, 19 LONGs each), the record A0
        of a direct 1d08a / 1d096 / 20a54 / 20bd6 / 20cf6 / 20d62 entry (LONGs 4 / 8 / 18, WORDs 18 / 76; the A0 that C4 1cfbe / ea680 / 4970a return),
        A1 a handler of the ROM list of the JMP (A1) (decision 2), D0 input bits, D1 / D7 small (1cec2 / ea680 / 2156a results), LONG 84(A6) a routed
        slot-84 value (the C3 JSR (A4) 201a6 that the BRA 201a2 blocks reach), LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), LONG
        5434(A5) = 0 (C2 decision 2), BYTE 10fd82 = 0 (keeps the controller C1 4a974 off the BIOS call c00450, not mapped natively)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x22, 0x30, 0x40, 0x50, 0x80, 0x200, 0x800, 0xa02, 0xffff, 0x12345678,
                                     0x10000, 0x10001, 0x8000))
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((0, 1, 2, 0x10001, 0xffff0001, 0x28, 0x27, 0x12340000, 0x80000000))
        if rng.random() < 0.4:
            regs['d7'] = rng.choice((0, 0x10000, 1, 0xffff, 0x12340000))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if entry in (0x1d08a, 0x1d096, 0x20a54, 0x20bd6, 0x20cf6, 0x20d62) or rng.random() < 0.3 else self.pointer()
        regs['a1'] = self.pointer()
        if entry in LIST_JUMPS:
            regs['a1'] = rng.choice(LIST_JUMPS[entry])         # the handler LONG 215e6 loaded (decision 2)
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = rec + 0x20 if rng.random() < 0.5 else self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, rec + 0x20 if rng.random() < 0.7 else self.pointer()))   # LONG 8c(A6): a record
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of C2 1cb08 / C5 1cb1a)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(), 0))))  # LONG 3e(A6) (C2 1a9fe..1aa20; 4be82 CMPA.W #0)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): C3 2031c / C5 1cc1a
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): C3 206d4
        writes.append(((a6 + 0x9f) & 0xffff, 1, rng.randrange(9)))                        # BYTE 9f(A6): C2 1cb08
        writes.append(((a6 + 0x9c) & 0xffff, 1, rng.randrange(6)))                        # BYTE 9c(A6): the key of the 215e6 lists
        writes.append(((a6 + 0x7c) & 0xffff, 2, rng.choice((0, 0x80, 0x180, 0x280, 0x281, 0x7fff, 0x8000, 0xfff0))))   # WORD 7c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.randrange(4)))                        # WORD 76(A6): the index of 1b170 / 1b178 / 21ba6
        writes.append(((a6 + 0x78) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x100))))        # WORD 78(A6): the player index
        writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                        # BYTE 9e(A6): the LONG table 1cfce (C4 1cfbe), C5 20796
        for node in (0x100cb8, 0x100da8):
            writes.append((node & 0xffff, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c))))   # 289e: CMPI.L #270e,(A0)
            writes.append(((node + 0x9e) & 0xffff, 1, rng.randrange(4)))
            writes.append(((node + 0x78) & 0xffff, 2, rng.choice((0, 1))))
        # the declared record (A0 = rec + 20: LONGs 4 / 8 / 18, WORDs 18 / 76; LONG 8c(A6) = rec + 20: BYTE 4 0..18)
        for off in (0x24, 0x28, 0x38):
            writes.append(((rec + off) & 0xffff, 4, self.value(4)))
        writes.append(((rec + 0x96) & 0xffff, 2, self.value(2)))
        writes.append(((rec + 0x24) & 0xffff, 1, rng.randrange(19)))
        if rng.random() < 0.8:
            writes.append(((a6 + 0x26) & 0xffff, 4, 0))       # 49fc6: LONG 26(A6) = 0 -> Set without the interpreter (random scripts)
        writes.append(((a5 + 0x5434) & 0xffff, 4, 0))                                     # LONG 5434(A5): A1 of the C2 JMP (A1) 1aa38 (0 in ROM)
        writes.append(((a5 + 0x5474) & 0xffff, 4, rng.choice((0, self.pointer()))))       # LONG 5474(A5): A0 of C2 1cd2a
        writes.append(((a5 + 0x5e26) & 0xffff, 4, self.pointer()))                        # LONG 5e26(A5): A4 of C3 e8b5a
        for k in (0, 4):
            writes.append(((a5 + 0x5734 + k) & 0xffff, 4, rng.choice((0, 0, self.pointer()))))   # 49c38: TST.L 5734(A5) + 4 x (D0.W & 1)
        if rng.random() < 0.9:
            writes.append((0xfd82, 1, 0))                                                 # BYTE 10fd82 = 0: 4a974 reads 100003 / 100004 / 100005
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e, 0x9f, 0x9c, 0x76, 0x78, 0x7c)):
                continue                                        # callback LONG, node links, the pointer fields and the bounded indices stay declared above
            if reg == 5 and disp in (0x5434, 0x5474, 0x5e26, 0x5734, 0x5738):
                continue
            if reg == 4 and disp == 4:
                continue                                        # BYTE 4(A4) (2218c / 221a2): the bounded table index stays declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        writes.append((sp & 0xffff, 4, ret))
        if hint:
            for off, size, val in hint.get('a6off', []):
                writes.append(((a6 + off) & 0xffff, size, val))
            for off, size, val in hint.get('a5off', []):
                writes.append(((a5 + off) & 0xffff, size, val))
            regs.update(hint.get('regs', {}))
            if hint.get('mirror'):
                regs['a6'] = a6 | 0xf0000                       # the node in the upper RAM mirror (1fxxxx = 10xxxx)
            for off, size, val in hint.get('rec', []):
                writes.append(((rec + off) & 0xffff, size, val))
            for off, size, val in hint.get('stack', []):
                writes.append(((sp + off) & 0xffff, size, val))  # values below / at the return LONG that a direct entry pops or reads
            for w in hint.get('writes', []):
                writes.append(w)
            for k, v in hint.get('regrec', {}).items():
                regs[k] = rec + v                               # a register that points into the declared record
        state = U.with_host_writes(st, writes, regs=regs, pc=entry)
        return state


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
    require(len(STARTS) == 220 and len(STARTS_SET) == 220, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c9_block', ('start is not routed to player c9', hex(s), unit_of(s)))
    for jmp, handlers in LIST_JUMPS.items():
        require(mine(jmp) and jmp in STARTS, ('JMP (A1) block', hex(jmp)))
        for t in handlers:
            require(unit_of(t) is not None, ('list handler must be routed', hex(t)))
    require(unit_of(0x21e48) == 'animation_player_c9_block', 'the list handler 21e48 is a C9 start')
    for t in EXIT_STOPS:
        require(unit_of(t) is None or t in ROUTED_LATER, ('later-unit stop must stay unrouted', hex(t)))
    rng = random.Random(0xC9A9)
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
                cond_points[a] = set(t for t in (target(op), a + size) if (s, t) not in STATIC_IMPOSSIBLE and (s, t) not in LATER_GATED and
                                     (a, t) not in BRANCH_IMPOSSIBLE)
                if a + size in BUNDLED:
                    cond_points[a].discard(a + size)            # the taken-or-not of the first Bcc of the pair: its fall-through is the second Bcc
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS or entry in Z_READERS:
            continue                                            # a consumer needs the C / Z of its producer: chain fixtures (a direct entry is an error fixture)
        n = len(block_instrs(entry))
        bundled = n > 1 and block_instrs(entry)[-1][0] in BUNDLED
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
            if (nxt in CONSUMERS or nxt in Z_READERS) and entry not in DATA_SET and entry not in CLEAR_SET and entry not in PASS_SET and entry not in SET_SET:
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
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)) - set(t for a, t in STATIC_IMPOSSIBLE) - set(CONSUMERS) - set(Z_READERS))
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
        cands = sorted([e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS and e not in Z_READERS], key=lambda e: (e != blk, e))
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
    never = sorted(set(STARTS) - visited - set(GATED_CONSUMERS))
    require(not never, ('block starts never executed by a fixture', [hex(x) for x in never]))
    error_fixtures(bases, add)
    negative_fixtures(out, add)
    META['carry_oracle'] = carry_oracle(out)
    META['visited_starts'] = len(set(STARTS) & visited)
    META['chain_only'] = [hex(x) for x in CONSUMERS + Z_READERS]
    META['static_impossible'] = [(hex(a), hex(t)) for a, t in sorted(STATIC_IMPOSSIBLE)]
    META['later_gated'] = [(hex(a), hex(t)) for a, t in sorted(LATER_GATED)]
    META['branch_impossible'] = [(hex(a), hex(t)) for a, t in sorted(BRANCH_IMPOSSIBLE)]
    META['gated_consumers'] = [hex(x) for x in GATED_CONSUMERS]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('pc9 spec: %d fixtures (%d natural), visited %d/220, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc9: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc9: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts









def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the BYTE 15 / 9c / 9d / 9e
    / a5 / a7 / 7e bits of the player states, the input bits of D0 (1 / 4 / 5 / 6 / 7 / 9 / 11 as LONG bits) and the AND.W #c / #50 masks, the WORD
    compare of 1f4ee (D1 against 1), the signed WORD difference of 20720 (SPL), the LONG settle arithmetic of 20a54 / 20a6e .. 20c10 (SUB.L / ASR.L #3 /
    ADD.L / ADDQ.L #7 with the sign boundaries), the WORD arithmetic of 20b9e (ASR.W #3) and 20bd6 (SWAP, ADD.W / SUB.W, the unsigned CMPI.W #28), the
    SUBQ.W borrow of 20af4 / 20d3c, the sign-extended table index of 20aa4 / 21376 / 2138e (WORD 76) and 2218c (BYTE 4 of the record), the SEQ / SUB.B
    of 22116, the SEQ / OR.B of 22452, the signed TST.B of 1f070 / 22174 (BLE / BGT / BLT), the TST.W D7 of 22276 / 22442, the handlers of the JMP (A1)
    lists), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    d0bits = (0, 1, 2, 3, 0x10, 0x20, 0x22, 0x40, 0x50, 0x60, 0x80, 0x12, 0x200, 0x800, 0xa00, 0xffffffdd, 0xffffffad, 0xfffffffc, 0xfffff7ff,
              0xfffffdff, 0xffffff7f, 0x12340000, 0xffffffff)
    ffnode = dict(a6off=[(0x64, 4, 0xffffffff), (0x7a, 2, 0xffff), (0x9c, 1, 0xff), (0xaa, 1, 0xff), (0xa9, 1, 0xff), (0x84, 4, 0x12345678),
                         (0x3a, 4, 0xffffffff), (0x36, 4, 0xffffffff), (0x88, 2, 0xffff), (0x9d, 1, 0x55), (0xa8, 1, 0xff), (0x9b, 1, 0xff),
                         (0x79, 1, 0xff), (0x7c, 1, 0xff), (0x63, 1, 0xff), (0x68, 1, 0xff), (0x83, 1, 0xff), (0x89, 1, 0xff), (0x5d, 1, 0xff),
                         (0x5f, 1, 0x55), (0x60, 1, 0xff), (0x14, 1, 0x55), (0x13, 1, 0xff), (0x2b, 1, 0xff), (0x2e, 1, 0xff)])
    if entry in (0x1ec8e, 0x1ece0, 0x1f0d6, 0x1f0f4, 0x1f4f6, 0x1f4ee, 0x22116, 0x22452, 0x2218c, 0x221a2, 0x20aa4, 0x21376, 0x2138e, 0x20ce8,
                 0x20d54, 0x20b9e, 0x20bd6, 0x1ed04, 0x1f108, 0x1f51a, 0x20b2e, 0x20c1c, 0x20a54, 0x20a6e, 0x20b00, 0x20bee):
        h += [dict(regs=dict(up))]
    # ---- 1d086 .. 1d096 (the motion record of 1cfbe: LONG 8 / 4(A0))
    if entry in (0x1d08a, 0x1d096):
        h += [dict(regrec=dict(a0=0x20), rec=[(0x24, 4, v), (0x28, 4, v ^ 0xffffffff)], regs=dict(up)) for v in (0, 0x80000000, 0x12345678)]
    # ---- 1ec74 .. 1ed1e, 1f070 .. 1f122, 1f48a .. 1f534 (the input states)
    if entry in (0x1ec74,):
        h += byte(0x9e, (1, 0, 0x81, 0xff, 2)) + [dict(a6off=[(0x9d, 1, 1), (0x9f, 1, 1)])]
    if entry in (0x1ecce, 0x1f0c4, 0x1f4cc):
        h += byte(0x9e, (0, 1, 0x80)) + [dict(a6off=[(0x9d, 1, 1), (0x9f, 1, 1)])]
    if entry in (0x1eca8, 0x1f08a, 0x1f492, 0x20ac4, 0x20b6e, 0x20d0a, 0x213b4, 0x21cca, 0x21d1c, 0x22238, 0x2227c, 0x22448, 0x22408, 0x22468,
                 0x21e48, 0x20be8, 0x20d62, 0x1fb28, 0x1ed18, 0x1f11c, 0x1f52e, 0x20bb8, 0x213d0, 0x20720, 0x22128):
        h += [dict(ffnode)] + mirror
    if entry in (0x1ecbc, 0x1f0b2, 0x1f4ba):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry in (0x1ecc6, 0x1ecd8, 0x1ecee, 0x1ecf6, 0x1f0bc, 0x1f0ce, 0x1f0e4, 0x1f0ec, 0x1f4c4, 0x1f4d6, 0x1f4e2, 0x1f500, 0x1f508, 0x21cea,
                 0x21cf2, 0x21cfa, 0x21d02, 0x21d3c, 0x21d44, 0x21d4c, 0x21d54, 0x2090a, 0x20912, 0x20924, 0x20b48, 0x20bc4, 0x22252, 0x2242e,
                 0x22436):
        h += [dict(regs=dict(up, d0=v)) for v in d0bits]
    if entry in (0x1ece0, 0x1f0d6, 0x1f4f6):
        h += [dict(regs=dict(up, d0=v, d1=0x9abc0000)) for v in (0, 4, 8, 0xc, 0x10000, 0xfff3, 0x12340004, 0xfffffff3)]
    if entry == 0x1f0f4:
        h += [dict(regs=dict(up, d0=v, d1=0x9abcdef0)) for v in (0, 0x10, 0x40, 0x50, 0xaf, 0x10000, 0xffffffaf, 0x12340040)]
    if entry in (0x1ed04, 0x1f108, 0x1f51a, 0x20b2e, 0x20c1c):
        h += [dict(regs=dict(up), a6off=[(0x1e, 2, v)]) for v in (0, 0x8000)]
    if entry == 0x1f070:
        for b9d, b15 in ((0, 0), (1, 1), (0x7f, 0xfe), (0x80, 0xff), (0xff, 0x80), (0x81, 0x7f)):
            h.append(dict(a6off=[(0x9d, 1, b9d), (0x15, 1, b15), (0x9c, 1, 0x55), (0x9e, 1, 0x55)]))
        h += mirror
    if entry == 0x1f4ee:
        h += [dict(regs=dict(up, d1=v)) for v in (1, 0x10001, 0xffff0001, 0, 2, 0x10000, 0x101)]
    # ---- 20720 (SPL on the WORD difference 42(A6) - a0)
    if entry == 0x20720:
        h += [dict(a6off=[(0x42, 2, v), (0x41, 1, 0x80), (0x44, 1, 0x80), (0x5f, 1, 0x55), (0x3a, 4, 0x12345678)]) for v in
              (0xa0, 0x9f, 0x809f, 0x80a0, 0, 0xffff, 0x7fff, 0x8000, 0x209f, 0x80bf)]
    # ---- 208fa .. 20d6e (the settle arithmetic)
    if entry == 0x20a54:
        for l18, d1, l46, l36 in ((0, 0, 0, 0), (0x10, 0, 8, 0x80), (0, 0, 1, 0xfffffff8), (0x80000000, 0, 0, 0x80000000), (0x7fffffff, 1, 0, 7),
                                  (0xffffffff, 0x80000000, 0x7fffffff, 0xffffffff), (0x12345678, 0x9abcdef0, 0x11111111, 0x40000008)):
            h.append(dict(regrec=dict(a0=0x20), rec=[(0x38, 4, l18)], regs=dict(up, d1=d1), a6off=[(0x46, 4, l46), (0x36, 4, l36), (0x3a, 4, 0x55555555)]))
    if entry in (0x20a6e, 0x20b00, 0x20bee):
        for l36, l3a in ((0, 0), (1, 0xfffc0000), (7, 0xfffc0001), (8, 0xfffbffff), (0x80000000, 0x7fffffff), (0x7fffffff, 0x80000000),
                         (0xfffffff8, 0xfffd0000), (0xffffffff, 0xfffcfff9), (0xfffffff7, 0xfffd0001), (0x12345678, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x36, 4, l36), (0x3a, 4, l3a)]))
    if entry in (0x20a7e, 0x20b10):
        h += [dict(regs=dict(up, d2=v)) for v in (0xfffffff9, 0xfffffff8, 0x7ffffffc, 0xffff)]
    if entry in (0x20a8e, 0x20b20, 0x20c0e):
        h += [dict(regs=dict(up, d3=v)) for v in (0xfffffff9, 0xfffffff8, 0x7ffffffc, 0xffff)]
    if entry in (0x20a80, 0x20b12, 0x20c00):
        for d2, d3, l36, l3a in ((0x80000000, 0, 0, 1), (0x7fffffff, 0xfffc0000, 1, 0xfffc0000), (8, 0xfffc0000, 0xffffffff, 0xfffc0001),
                                 (0xfffffff8, 0x80000000, 0x80000000, 0x7fffffff), (0xf, 7, 0x7fffffff, 8), (0x12345678, 0x9abcdef0, 0, 0x9abcdef1)):
            h.append(dict(regs=dict(up, d2=d2, d3=d3), a6off=[(0x36, 4, l36), (0x3a, 4, l3a)]))
    if entry in (0x20a90, 0x20b22, 0x20c10):
        for d3, l3a in ((0x80000000, 0), (0x7fffffff, 1), (0xfffffff8, 0x80000000), (0xf, 0xffffffff), (0x12345678, 0x9abcdef0)):
            h.append(dict(regs=dict(up, d3=d3), a6off=[(0x3a, 4, l3a)]))
    if entry in (0x20aa4, 0x21376, 0x2138e):
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v)]) for v in (0, 1, 2, 3, 0xc000, 0xffff, 0x4001)]
    if entry in (0x20aec, 0x20b96):
        h += [dict(a6off=[(0x88, 2, v), (0x87, 1, 0x80), (0x8a, 1, 0x80)]) for v in (0, 1, 0x100, 0x8000)]
    if entry in (0x20af4, 0x20d3c):
        h += [dict(a6off=[(0x88, 2, v), (0x87, 1, 0x80), (0x8a, 1, 0x80)]) for v in (0, 1, 0x100, 0x8000, 0xffff)]
    if entry == 0x20b9e:
        for w88, w2c in ((1, 0x40), (1, 0x41), (1, 0x48), (1, 0x3f), (2, 0), (1, 0x8040), (0, 0xffff), (1, 0x100), (1, 0xc040), (1, 0x4040)):
            h.append(dict(regs=dict(up), a6off=[(0x88, 2, w88), (0x2c, 2, w2c), (0x2b, 1, 0x80), (0x2e, 1, 0x80)]))
    if entry == 0x20bd6:
        for d1, w18, w46 in ((0x00010000, 0x27, 0), (0x00010000, 0x28, 0), (0, 0x28, 1), (0x12340000, 0, 0x1234 - 0x28), (0x12340000, 0, 0x1234 - 0x27),
                             (0xffff0000, 0x29, 0), (0x8000, 0x28, 0x8000), (0xfffe5678, 0x8000, 0x7fff)):
            h.append(dict(regrec=dict(a0=0x20), rec=[(0x38, 2, w18)], regs=dict(up, d1=d1), a6off=[(0x46, 2, w46), (0x48, 2, 0x5555)]))
    if entry in (0x20cf6, 0x20d62):
        h += [dict(regrec=dict(a0=0x20), rec=[(0x95, 1, 0xff), (0x98, 1, 0xff), (0x96, 2, 0x5555)])]
    if entry == 0x213a6:
        h += [dict(a6off=[(0x19, 1, v), (0x14, 1, 0x55), (0x13, 1, 0xff), (0x15, 1, 0xff)]) for v in (0, 0x80, 0xff)] + mirror
    # ---- 21ca4 .. 21d5c, 2210c .. 22472 (the slot-84 states)
    if entry in (0x21ca4, 0x21d0e, 0x2210c, 0x22408):
        h += byte(0xa7, (0x20, 0xdf, 0xff, 0)) + mirror
    if entry in LIST_JUMPS:
        h += [dict(regs=dict(a1=v)) for v in LIST_JUMPS[entry]]
    if entry == 0x22116:
        for d0 in (0, 1, 2, 3, 0xfffffffc, 0x12345601, 0x12345602, 0xffffffff):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x9d, 1, 0x55), (0x9c, 1, 0xff), (0x9e, 1, 0xff)]))
    if entry == 0x22128:
        for a5, a6, a7 in ((0xff, 0xff, 0), (0x10, 0x10, 1), (0xef, 0xef, 0xfe), (0, 0, 0xff)):
            h.append(dict(a6off=[(0x7e, 1, 0xff), (0xa5, 1, a5), (0xa6, 1, a6), (0xa7, 1, a7), (0xaa, 1, 0xff), (0x7d, 1, 0xff), (0x7f, 1, 0xff)]))
    if entry == 0x22174:
        h += byte(0x9d, (0, 1, 0x7f, 0x80, 0xff)) + [dict(a6off=[(0x9d, 1, 0x80)], mirror=True)]
    if entry == 0x2218c:
        for k in (0, 1, 2, 18, 9):
            h.append(dict(regs=dict(up, a0=0x22028 + 0x4c * (k % 3)), rec=[(0x24, 1, k), (0x23, 1, 0xff), (0x25, 1, 0xff)]))
    if entry in (0x221a2, 0x221b2, 0x221ba, 0x221c2):
        for k in (5, 0xa, 6, 0xb, 0, 0x85, 0xff):
            h.append(dict(regs=dict(up, d0=0x12345600 | k), rec=[(0x24, 1, k)]))
    if entry == 0x2225a:
        h += byte(0x7e, (0, 1, 0x80, 0xff))
    if entry == 0x22262:
        h += byte(0xa5, (0x10, 0xef, 0xff, 0))
    if entry == 0x2226c:
        h += byte(0xaa, (2, 0xfd)) + mirror
    if entry in (0x22276, 0x22442):
        h += [dict(regs=dict(up, d7=v)) for v in (0, 0x10000, 1, 0x8000, 0xffff0000)]
    if entry in (0x223a0, 0x223b2, 0x223c4, 0x223d6, 0x223e8):
        h += [dict(a6off=[(0x9d, 1, 0x55), (0x9c, 1, 0xff), (0x9e, 1, 0xff)])] + mirror
    if entry == 0x22452:
        for v in (3, 4, 0, 5, 0x83, 0xff, 0x13, 0x84, 1):
            h.append(dict(regs=dict(up), a6off=[(0x9c, 1, v), (0x9b, 1, 0xff), (0x9d, 1, 0xff)]))
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]







def chain_hint(entry, t, rng):
    if entry in (0x1ed0e, 0x1f112, 0x1f524):
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
    if entry == 0x1ec98:
        # 1cb08 on the ROM WORD table 1b764: W = WORD (1b764 + 2 x BYTE 9f); 0 -> Clear; else C5 1cb1a: TST.L (LONG 22(A6) + 4 x WORD (1b764 + W))
        k = (0, 5, 0xc, 0xd, 0xe, 0xf, 0x10)[(t // 2) % 7]          # 1b764: the WORDs 0..b are 0 (Clear), c..10 not 0
        w = rom_word(0x1b764 + 2 * k)
        idx = (4 * rom_word(0x1b764 + w)) & 0xffff if w else 0
        return dict(a6off=[(0x9f, 1, k), (0x22, 4, SCR)], writes=[((SCR + idx) & 0xffff, 4, (0, 0x12345678)[t % 2])] if idx < 0x400 else [])
    if entry == 0x21ca4:
        # 21bc6: CMPI.B #1,9e(A6); BNE -> Clear / BCLR.B #4,a7(A6); BEQ -> Clear / Set
        return dict(a6off=[(0x9e, 1, (1, 1, 0, 2)[t % 4]), (0xa7, 1, (0x10, 0, 0x30, 0xff)[(t // 4) % 4])])
    if entry == 0x21cb2:
        # 21baa: TST.B 9f(A6); BNE -> Clear / BYTE (21ba6 + WORD 76) (ROM 0b 0b 06 06) <u BYTE a1(A6) -> Set
        return dict(a6off=[(0x9f, 1, (0, 0, 0, 1)[t % 4]), (0x76, 2, t % 4), (0xa1, 1, (0x0c, 0x0b, 0x06, 0x07, 0xff, 0)[(t // 4) % 6])])
    if entry in (0x21cd8, 0x21d2a, 0x22240, 0x2241c):
        # 215e6 on the ROM lists 21aee (keys 0 2 3 4) / 216c8 (key 0): key BYTE 9c -> Set (A1 the handler); else Clear
        return dict(a6off=[(0x9c, 1, (0, 1, 2, 3, 4, 5, 0xff)[t % 7])])
    if entry == 0x22174:
        return dict(a6off=[(0x9d, 1, (0, 0x80, 0xff, 1, 0x81, 0x7f)[t % 6])])
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d)] + [(6, off, 4) for off in (0x36, 0x3a, 0x42, 0x46)]
        succ = static_next(cons)
        kept = {}
        for t in range(MAX_TRIES * 2):
            st = world.make(entry, SENTINEL, flds, chain_hint(entry, t, rng))
            tr = trace(st, first_unrouted(extra=tuple(sorted(succ))), cap=400000)
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
            record(tr['pcs'] + [tr['stop']])
            if cons not in tr['pcs']:
                continue
            key = tr['stop']
            if key not in kept:
                kept[key] = (st, tr)
            if set(k for k in kept if isinstance(k, int)) >= succ:
                break
        require(kept, ('no chain world', hex(entry)))
        missing = succ - set(k for k in kept if isinstance(k, int))
        missing -= set(t for c, t in LATER_GATED if c == cons)
        missing -= set(t for c, t in STATIC_IMPOSSIBLE if c == cons)
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'],
                                                                                                c=tr['sr'] & 1)))


def add_run(add, name, st, tr, meta):
    add(U.Fixture(name, st, [], tr['stop'], meta=meta))


def node_fixtures(world, add, record):
    """Installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), WORD 78 (the player index), WORD 76 0..3 (the ROM tables 1b170 / 1b178), BYTE 15 bit 7 (1ecbc / 1f0b2 /
            # 1f4ba), BYTE 9e (1ec74 / 1ecce / 1f0c4 / 1f4cc), BYTE 9d (1f070 / 22174), BYTE a7 bits 0 / 4 / 5, WORD 88 (20aec / 20b96 / 20d3c), BYTE 7e /
            # a5 (2225a / 22262), BYTE 9c (22452), LONG 26 (0: 49fc6 Set), LONG 36 / 3a (the settle helpers)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x78, 2, (0, 1)[t % 2]), (0x76, 2, t % 4), (0x15, 1, (0, 0x80, 1, 0x81, 0xff)[t % 5]),
                               (0x9e, 1, (0, 1)[(t // 2) % 2]), (0x9d, 1, (0, 1, 0x80, 0xff)[(t // 3) % 4]), (0xa7, 1, (0, 0x20, 0x11, 0xff)[(t // 4) % 4]),
                               (0x88, 2, (0, 1, 2, 0x8000)[(t // 5) % 4]), (0x7e, 1, (0, 1)[(t // 7) % 2]), (0xa5, 1, (0, 0x10)[(t // 2) % 2]),
                               (0x9c, 1, (0, 3, 4, 1)[(t // 3) % 4]), (0x36, 4, (0, 0x80000000, 0x100, 0xffffff00)[(t // 6) % 4]),
                               (0x3a, 4, (0, 0xfffc0000, 0x12345)[(t // 4) % 3])] + ([(0x26, 4, 0)] if t % 5 != 4 else []))
            st = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], len(set(tr['pcs']) & STARTS_SET) // 4)
            if key in kept:
                continue
            kept[key] = (st, tr)
            if len(kept) >= 3:
                break
        require(kept, ('no node world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add_run(add, 'node-%05x-%d' % (entry, i), st, tr, dict(family='node', entry=entry, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))




_PACKS = {}


def io_pack(cfg, case):
    """Frame-start states of one run of the extended-input IO observation IO_EXT (read-only): {frame: state} decoded with
    observe_animation_machine_io.read_pack (the observation's state packs; this spec's own reader, the shared loader is unchanged)."""
    key = (cfg, case)
    if key not in _PACKS:
        import observe_animation_machine_io as O
        path = ROOT / IO_EXT / 'states' / cfg / ('%03d.pack.gz' % case)
        _PACKS[key] = dict((fr, st) for fr, st, dg in O.read_pack(gzip.decompress(path.read_bytes())))
    return _PACKS[key]


def natural_fixtures(add, record):
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a frame in which a player node (NATURAL_NODES) holds one of NATURAL_CALLBACKS as
    its callback LONG, or one of NATURAL_SLOTS as its slot-84 LONG 84(A6) with a routed callback LONG; declared registers A5 = 108000, A6 = the node,
    A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the frame start.  Up to the sentinel or the first unrouted PC."""
    entries = set(NATURAL_CALLBACKS)
    slots = set(NATURAL_SLOTS)
    count = 0
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        for node in NATURAL_NODES:
            a = node & 0xffff
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            sl = struct.unpack('>I', ram[a + 0x84:a + 0x88])[0]
            if cb not in entries and not (sl in slots and unit_of(cb) is not None):
                continue
            regs = dict(st0['regs'])
            regs.update(a5=0x108000, a6=node, a7=0x10ef00)
            st = U.make_state(ram, regs, cb, st0['bank'], st0['pvc'])
            st = U.with_host_writes(st, [(0xef00, 4, SENTINEL)])
            tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
            if not set(tr['pcs']) & STARTS_SET:
                continue                                    # the run does not reach C9 code (a slot-84 world whose callback leaves before 201a2)
            record(tr['pcs'] + [tr['stop']])
            add_run(add, 'natural-%05x-%s%03d-f%d-%x' % (cb, cfg, case, frame, node), st, tr,
                    dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], slot84=sl,
                         unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
            count += 1
    require(count >= 30, ('too few natural node fixtures', count))


def callee_fixtures(world, add, record):
    """The helpers and states as subroutines (return LONG = sentinel)."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry, world)
        for t in range(60 + len(hints)):
            hint = hints[t] if t < len(hints) else None
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(), cap=400000)
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
            record(tr['pcs'] + [tr['stop']])
            key = (tr['stop'], tuple(p for p in tr['pcs'] if p in STARTS_SET)[:40])
            if key in kept:
                continue
            kept[key] = (st, tr)
            if len(kept) >= 4 and t >= len(hints):
                break
        require(kept, ('no callee world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add_run(add, 'callee-%05x-%d' % (entry, i), st, tr, dict(family='callee', entry=entry, stop=tr['stop']))









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
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_PC, pc)
    err('odd-pc', U.with_host_writes(st, pc=0x1ec75), 'unaligned animation machine PC', 0x1ec75)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rec = SCR
    # the JMP (A1) (contract decision 2): A1 outside the list of the jump (compared as a LONG)
    for v in (0x21c22, 0x21e49, 0, 0x121602, 0x21e52, 0x1021e48):
        err('21ce4-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21ce4), ERROR_JUMP, 0x21ce4)
    for jp in (0x21d36, 0x2224c, 0x22428):
        for v in (0x21d60, 0x21e48, 0, 0x1021602):
            err('%x-a1-%x' % (jp, v), U.with_host_writes(st, regs=dict(a1=v), pc=jp), ERROR_JUMP, jp)
    # the N source of 22180 (contract decision 3): BYTE 9d(A6) outside work RAM / fixed ROM (the bank window, the device space)
    for v in (0x200000 - 0x9d, 0x3c0000, 0x2ffff0):
        err('22180-a6-%x' % v, U.with_host_writes(st, regs=dict(a6=v), pc=0x22180), ERROR_FLAG, 0x22180)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('1eca8-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1eca8), odd_write, 0x1eca8, stop=0x1ecb8)
    err('1f08a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1f08a), odd_write, 0x1f08a, stop=0x1f0ae)
    err('20b6e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x20b6e), odd_write, 0x20b6e, stop=0x20b96)
    err('20a6e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x20a6e), odd_word, 0x20a6e, stop=0x20a80)
    err('22128-rom-node', U.with_host_writes(st, regs=dict(a6=0x1b000), pc=0x22128), 'unsupported animation machine write device', 0x22128, stop=0x22174)
    err('1d08a-odd-a0', U.with_host_writes(st, regs=dict(a0=rec + 1), pc=0x1d08a), odd_word, 0x1d08a)
    err('20a54-odd-a0', U.with_host_writes(st, regs=dict(a0=rec + 1), pc=0x20a54), odd_word, 0x20a54)
    err('20cf6-odd-a0', U.with_host_writes(st, regs=dict(a0=rec + 1), pc=0x20cf6), odd_write, 0x20cf6, stop=0x49274)
    err('22284-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x22284), odd_word, 0x22284)
    err('1d086-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d086), odd_word, 0x1d086, stop=0x1cfbe)
    # failures after executed blocks:
    #   1f070 (BYTE 9d > 0) -> 1f082 (C10); 20bee (0 - LONG 36 not negative) -> 20bfe (C10); 22128 (BYTE a7 bit 0) -> 22148 (C10); 221a2 (BYTE 4 of the record = 5)
    #   -> 22286 (C10); 21d3c (D0 bit 0) -> 223fa (C10); the RTS at an odd A7 after executed blocks
    #   Player C10 routes 1f082 20bfe 22148 22286 223fa (previous rows '1f070-then-1f082' '20bee-then-20bfe' '22128-then-22148' '221a2-then-22286'
    #   '21d3c-then-223fa': 'unsupported animation machine PC' there): an odd A7 moves the failing PC of the first three to the first stack access
    #   after them (C9 1f086 BSR.W 1cab6, C9 20c16 JSR 43ea4.l, C10 22160 BSR.W 1cb08); 22286 / 223fa keep it with the node in fixed ROM (A6 = fff78:
    #   LONG 8c(A6) = 100004 in work RAM, the 22286 MOVE.L writes ffffc; A6 = 0: the 223fa MOVE.B writes 9d).
    err('1f070-then-1f086', U.with_host_writes(st, [((a6 + 0x9d) & 0xffff, 1, 1)], regs=dict(a7=a7 + 1), pc=0x1f070), odd_word, 0x1f086)
    err('20bee-then-20c16', U.with_host_writes(st, [((a6 + 0x36) & 0xffff, 4, 0xffffff00)], regs=dict(a7=a7 + 1), pc=0x20bee), odd_word, 0x20c16)   # D2 = 100: BPL
    err('22128-then-22160', U.with_host_writes(st, [((a6 + 0xa7) & 0xffff, 1, 1)], regs=dict(a7=a7 + 1), pc=0x22128), odd_word, 0x22160)
    err('221a2-then-22286', U.with_host_writes(st, [(0x0004, 4, rec + 0x20), ((rec + 0x24) & 0xffff, 1, 5)], regs=dict(a6=0xfff78), pc=0x221a2),
        'unsupported animation machine write device', 0x22286)
    err('21d3c-then-223fa', U.with_host_writes(st, regs=dict(d0=1, a6=0), pc=0x21d3c), 'unsupported animation machine write device', 0x223fa)
    err('20a6e-then-20a90', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x20a6e), odd_word, 0x20a90)
    err('22276-then-22284', U.with_host_writes(st, regs=dict(a7=a7 + 1, d7=0), pc=0x22276), odd_word, 0x22284)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x20a54, 0x20a80, 0x22116, 0x20bd6)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
