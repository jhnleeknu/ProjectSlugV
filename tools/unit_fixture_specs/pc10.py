"""V1 fixture spec of the area-C unit C10 (engine/src/animation_machine_player_c10.cpp, 132 block starts; file prefix pc10 / player_c10 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c10-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 unit C-2 with the C7
table entry 252b4 -> 252ce .. 252e2 (main decision 4) and the branch target 2041a): the 28ae child callback 1c4b0 -> 1c4d2 -> 1c500 (C5 1c484; sounds
3af8, JMP 2a00), the successors 1dc8e (Set) / 1dccc (Clear) of the routed interpreter stub 1dc84 / 1dc8a (1d1d0, 1aa3a, the callback 1f3e0), the
player input state 1efd6 -> 1efe4, the record entries 1f082 / 1f3e0, the C3 table entry 20324 -> 203a0 (the BRA.W table jump 203ac, executed entry
203b0) -> 20414 / 2041a -> 204e0 (1cc1a 492c8 1c1e2 1c51c 1c356; the LONG table 20444), 20bfe, the slot-84 states 21dd0 -> 21e04 (JMP (A1) 21e10 on
the list 21b0a), 22148 (1cb08), 22286 -> 2228e (JMP (A1) 2229a) -> 22360 (JMP (A1) 22378), 223fa, the sound helper 24b78, the 2986 child callback
24ecc (the bank window LONG 200038, 49f8c, 8ebe) and the C7 table entry 252b4 -> 252ce -> 252e2.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR10, C1..C9) with declared host edits.
This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the 'natural'
family takes the frame-start states of that observation (state packs, read-only) in which a pool node holds a C10 node entry (1c4b0 1c4d2 1c500 24ecc)
or the C7 child state 25102 as its callback LONG, or a player node holds a C10 install (1efe4 1f3e0) / slot-84 value (21e04 2228e 22360) or is the
player node of a frame in which the exact-bitmap re-observation first records a C10 start; it keeps their RAM / PVC / bank and declares only the
registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return LONG, PC = the callback).  The spec reads those packs itself (io_pack
below, observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 7 C consumers and the 3 Z readers 1efee 1eff6 20508 is entered directly (the seed world with declared
            edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers and the Z readers through their flag-setting predecessors (CHAINS).  Stop: the
            successor or the first unrouted PC.
  node      the installed values and child callbacks (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers and states entered as subroutines or branch targets of other units (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 7 consumers, the jump-target guard of the three JMP (A1) and of
            the table jump 203ac (decision 2), the Z source of 1efee outside work RAM / fixed ROM (decision 3), odd node / stack / A0, failures after
            executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry
            and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR10, C1..C9
specs do).
"""
import gzip
import json
import random
import re
import struct
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR10, C1..C9)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc10'
ERROR_PC = 'unsupported animation player c10 PC'
ERROR_CARRY = 'player c10 caller requires known carry'
ERROR_JUMP = 'unsupported animation player c10 jump target'
ERROR_FLAG = 'unsupported animation player c10 flag source'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x1c4b0, 0x1c51a), (0x1dc8e, 0x1dcd0), (0x1efd6, 0x1f070), (0x1f082, 0x1f086), (0x1f3e0, 0x1f3e8), (0x20324, 0x20328), (0x203a0, 0x203b4),
          (0x20414, 0x20444), (0x204e0, 0x20516), (0x20bfe, 0x20c00), (0x21dd0, 0x21e3a), (0x22148, 0x22174), (0x22286, 0x223a0), (0x223fa, 0x22408),
          (0x24b78, 0x24b96), (0x24ecc, 0x24f18), (0x252b4, 0x252b8), (0x252ce, 0x252e6)]
STARTS = sorted(int(x, 16) for x in (
    '1c4b0 1c4b8 1c4c2 1c4d2 1c4dc 1c4e0 1c4e8 1c4ea 1c4f2 1c4f8 1c500 1c50e 1c514 1dc8e 1dc92 1dcb0 1dcb8 1dcbe 1dcc6 1dccc 1efd6 1efde 1efe4 1efe8 '
    '1efee 1eff2 1eff6 1effa 1f004 1f00c 1f016 1f01a 1f022 1f02a 1f02e 1f036 1f03e 1f048 1f052 1f056 1f05c 1f066 1f06c 1f082 1f3e0 20324 203a0 203b0 '
    '20414 2041a 20422 2042e 2043e 20440 204e0 204e4 204f6 204fa 20508 2050c 20bfe 21dd0 21dda 21dde 21de2 21de6 21dea 21dee 21df6 21e04 21e0c 21e10 '
    '21e12 21e16 21e1e 21e26 21e2e 21e36 22148 2215c 22160 22164 22168 22170 22286 2228e 22296 2229a 2229c 222a0 222a8 222b0 222ba 222c0 222c8 222d4 '
    '222d8 222e0 222ec 222f0 22300 22304 2230a 22312 22314 22322 22330 2233e 22348 2234c 22360 22364 2236c 22374 22378 2237a 2237e 22384 22396 2239e '
    '223fa 24b78 24b8a 24b94 24ecc 24ee2 24f06 24f14 252b4 252ce 252d8 252e2').split())
# the 7 C consumers: BCS 21dda 21de2 21dea (21bc6 / 21baa / 21c1c of C3), BCC 21e0c 22296 22374 (215e6 of C3), BCC 22164 (1cb08 of C2)
CONSUMERS = (0x21dda, 0x21de2, 0x21dea, 0x21e0c, 0x22164, 0x22296, 0x22374)
CLEAR_SET = ()
SET_SET = ()
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x1efe8, 0x1eff2)                 # the BTST blocks whose only successor is a Z reader (1efee / 1eff6): block fixtures stop there
INVERT_SET = ()
PASS_SET = ()
STARTS_SET = set()
# the Z readers (contract decision 3): BEQ 1efee on the BTST.B #7,15(A6) of 1efe8 (re-read BYTE), BEQ 1eff6 on the BTST #5,D0 of 1eff2 (D0), BNE 20508
# on the BTST.L D1,D7 that ends C5 1c51c (D7 / D1): never entered directly by a native run (their flag is the predecessor's)
Z_READERS = (0x1efee, 0x1eff6, 0x20508)
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
# C3 21c1c is ANDI.B #fe,CCR; RTS (ROM 023c 00fe 4e75): its C is always Clear, so the Set side 223b2 of the consumer 21dea has no real producer
STATIC_IMPOSSIBLE = {(0x21dea, 0x223b2)}
# 222f0 TST.B 9d(A6); BEQ.W 22300; BGT.W 22330; BLT.W 2233e: a BYTE that is neither 0 nor positive is negative, so the BLT at 222fc is always taken
BRANCH_IMPOSSIBLE = {(0x222fc, 0x22300)}
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# C10 blocks reach no unrouted PC by a fall-through or a branch (every exit is routed); the declared stops are the still unrouted later-unit stops of the
# C1..C9 blocks that the C10 runs pass through (pc9 EXIT_STOPS that C10 does not route: the TRAP site 4e69a of C1, the write-only callbacks 1e21c 1e8de
# of 1dcb8 / 1dcc6, ...) and the later-unit stops of the FR10 blocks (fr10 EXIT_STOPS[:11]).  Declared stops of the native runs: a straight-line
# unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6, 0x4e69a,
              0x70e42, 0x70fac, 0xcd7e2, 0xcd92e, 0xcd96c, 0x70f8e, 0xb6c58, 0x70f60, 0x70fcc, 0x70ff8, 0x71028)
UNIT_EXITS = ()                         # no C10 later-unit stop
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the Z chains 1efe8 -> 1efee, 1eff2 -> 1eff6,
# 204fa -> 20508 (C5 1c51c)
CHAINS = ((0x21dd0, 0x21dda), (0x21dde, 0x21de2), (0x21de6, 0x21dea), (0x21e04, 0x21e0c), (0x22148, 0x22164), (0x2228e, 0x22296), (0x2236c, 0x22374),
          (0x1efe8, 0x1efee), (0x1eff2, 0x1eff6), (0x204fa, 0x20508))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# computed jump (contract decision 2): JMP 203b0(PC,D0.W) 203ac, the BRA.W table 203b0..203d4 (9 entries; D0.W = 4 x BYTE 9f(A6), the ROM writers keep
# BYTE 9f 0..8); only the executed entry 203b0 is a block of the unit
JUMP_PCS = (0x203ac,)
TABLE_203B0 = tuple(0x203b0 + 4 * k for k in range(9))
JUMP_ROUTED = ()
# the JMP (A1) of C10 (contract decision 2): A1 = the handler LONG that C3 215e6 loaded from the ROM list (21b0a for 21e04 -> 21e10, 216c8 for 2228e /
# 2236c -> 2229a / 22378); any other A1 is the C++ checked jump-target error (a native run that jumps elsewhere is not a fixture world)
LIST_21B0A = (0x21602, 0x21c22, 0x21e48, 0x21e3a)
LIST_216C8 = (0x21602,)
LIST_JUMPS = {0x21e10: LIST_21B0A, 0x2229a: LIST_216C8, 0x22378: LIST_216C8}
# computed jumps that the C10 runs reach (C3 2031c table, 201a6 JSR (A4) (from the BRA 201a2 blocks), 21620 / 221de JMP (A1); C4 21c72 JMP (A1); C5
# 20792 2094e 209d6 21f7c; C7 25298; C8 21d9e 21e76; C9 21ce4 21d36 2224c 22428; C10 21e10 2229a 22378; FR4 cc7a8 cc82a): an unrouted target is a stop
# even when it is the straight-line successor
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36,
                  0x2224c, 0x22428, 0x21e10, 0x2229a, 0x22378, 0xcc7a8, 0xcc82a)
TABLE_ENTRIES = ()
# routed slot-84 states (C3, C4 21d92, C8 21e6a, C9 21cd8 21d2a 2210c 22128 22240 2241c 22452, C10 21e04 2228e 22360) for the worlds
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92, 0x21e6a, 0x21cd8, 0x21d2a, 0x2210c, 0x22128, 0x22240, 0x2241c, 0x22452,
             0x21e04, 0x2228e, 0x22360)
# installed values and child callbacks entered as node callbacks: 1c4b0 (the 28ae child of C5 1c484), 1c4d2 (1c4c2), 1c500 (1c4f8), 1efe4 (1efde),
# 1f3e0 (1dc92, C8 1f764, 1f3ce), 24ecc (the 2986 child of the C7 LONG table 22502); the callee entries (branch targets of other units' blocks, the
# interpreter stub successors, the slot-84 states of 201a6 JSR (A4), the C3 / C7 table entries, the helper 24b78, states entered as subroutines)
NODE_ENTRIES = (0x1c4b0, 0x1c4d2, 0x1c500, 0x1efe4, 0x1f3e0, 0x24ecc)
CALLEES = (0x1dc8e, 0x1dccc, 0x1efd6, 0x1f082, 0x20324, 0x203a0, 0x20414, 0x2041a, 0x204e0, 0x20bfe, 0x21dd0, 0x21e04, 0x22148, 0x22286, 0x2228e,
           0x22360, 0x223fa, 0x24b78, 0x252b4, 0x252ce, 0x22300, 0x22348, 0x1f02a, 0x2042e)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
# natural worlds of the extended observation: (config, case, frame) (scratch natscan_c10.py -> natural_c10.json: per run and key the first, a middle and
# the last frame of the pool callbacks 1c4b0 1c4d2 1c500 24ecc, the player callbacks 1efe4 1f3e0, the slot values 21e04 2228e 22360 and the frames in
# which the re-observation reobs/c10base first records a C10 start)
NATURAL = tuple(tuple(x) for x in (
    ('X1', 68, 590), ('X1', 68, 601), ('X1', 68, 602), ('X1', 68, 613), ('X1', 68, 665), ('X1', 68, 780), ('X1', 68, 825), ('X1', 94, 384),
    ('X1', 94, 395), ('X1', 94, 396), ('X1', 94, 409), ('X1', 94, 588), ('X1', 94, 592), ('X1', 94, 602), ('X2', 68, 608), ('X2', 68, 619),
    ('X2', 68, 620), ('X2', 68, 631), ('X2', 68, 632), ('X2', 68, 649), ('X2', 68, 812), ('X2', 94, 386), ('X2', 94, 397), ('X2', 94, 398),
    ('X2', 94, 409), ('X2', 94, 421), ('X2', 94, 439), ('X2', 94, 620), ('X3', 68, 591), ('X3', 68, 659), ('X3', 68, 734), ('X3', 68, 745),
    ('X3', 68, 746), ('X3', 68, 760), ('X3', 68, 761), ('X3', 68, 766), ('X3', 68, 771), ('X3', 68, 772), ('X3', 68, 774), ('X3', 68, 781),
    ('X3', 68, 809), ('X3', 68, 810), ('X3', 68, 976), ('X3', 68, 980), ('X3', 68, 1116), ('X3', 68, 1117), ('X3', 68, 1118), ('X3', 68, 1119),
    ('X3', 68, 1226), ('X3', 94, 391), ('X3', 94, 401), ('X3', 94, 467), ('X3', 94, 542), ('X3', 94, 553), ('X3', 94, 554), ('X3', 94, 576),
    ('X3', 94, 577), ('X3', 94, 579), ('X3', 94, 580), ('X3', 94, 620), ('X3', 94, 946), ('X4', 68, 520), ('X4', 68, 526), ('X4', 68, 714),
    ('X4', 68, 725), ('X4', 68, 726), ('X4', 68, 779), ('X4', 68, 800), ('X4', 68, 873), ('X4', 68, 960), ('X4', 68, 1100), ('X4', 68, 1101),
    ('X4', 68, 1103), ('X4', 68, 1104), ('X4', 68, 1148), ('X4', 94, 360), ('X4', 94, 366), ('X4', 94, 554), ('X4', 94, 565), ('X4', 94, 566),
    ('X4', 94, 621), ('X4', 94, 713), ('X4', 94, 800), ('X4', 94, 935), ('X4', 94, 940), ('X4', 94, 941), ('X4', 94, 943), ('X4', 94, 944),
    ('X4', 94, 1006),))
NATURAL_CALLBACKS = (0x1efe4, 0x1f3e0)                               # the C10 installs as callback LONG of the player node
NATURAL_SLOTS = (0x21e04, 0x2228e, 0x22360)                          # or a C10 slot-84 LONG (entered from 201a6 JSR (A4))
NATURAL_POOL = (0x1c4b0, 0x1c4d2, 0x1c500, 0x24ecc, 0x25102)          # pool node callbacks: the C10 children and the C7 child state 25102 (-> 252b4)
NATURAL_NODES = (0x100cb8, 0x100da8)    # the player nodes searched (work RAM CPU addresses)
NATURAL_PLAYER_ANY = True               # a player node with any routed callback is kept when its run reaches a C10 start (the reobs frames)
POOL = (0x100800, 0x104c00)             # the node pool searched for the pool callbacks
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
# flag-sharing Bcc chains inside one block: 222c8 TST.B; BEQ; BLT, 222e0 TST.B; BEQ; BGT, 222f0 TST.B; BEQ; BGT; BLT (the later Bcc of each chain)
BUNDLED = (0x222d0, 0x222e8, 0x222f8, 0x222fc)


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 1f082 into C9 1f086, 20bfe into C9 20c00); a Bcc followed by a BUNDLED
    Bcc continues the block."""
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
        for b, bmn, bop, bsize, _ in instrs[:-1]:
            if BCC.match(bmn) and b + bsize in BUNDLED:
                out.add(target(bop))                    # the earlier Bcc of a bundled chain
        return out
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op and '(a' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr', 'jmp'):
        return None
    return {a + size}


def block_next(entry, n, tr):
    """The PC after the entry block: the first traced PC that leaves the straight-line instruction sequence of the block (pcs[n] for a block run to
    its end; an earlier PC when a Bcc of a bundled chain is taken), or the stop."""
    pcs = tr['pcs']
    addrs = [x[0] for x in block_instrs(entry)]
    i = 1
    while i < len(pcs) and i < len(addrs) and pcs[i] == addrs[i]:
        i += 1
    return pcs[i] if len(pcs) > i else tr['stop']


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
        if seq[i] in JUMP_PCS and seq[i + 1] not in TABLE_203B0:
            return None                                 # JMP 203b0(PC,D0.W) beyond the table: the C++ checked jump-target error (decision 2)
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at an unrouted entry of the
    table jump 203ac, at an unrouted target of the computed jumps that the C10 runs reach (OTHER_JUMP_PCS: C3 / C4 / C5 / C7 / C8 / C9, FR4 and the C10
    JMP (A1) 21e10 / 2229a / 22378), or at the first unrouted PC that is not the straight-line successor of the previous instruction (a PC inside a
    block of another executor is not a block entry)."""
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it (as C1..C9): WORD 76(A6) 0..3 (the index of the ROM
        WORD tables 1b170 / 1b178 and of the C3 BYTE table 21ba6), WORD 78 mostly 0 / 1 (the player index), BYTE 9e(A6) 0..3 (the LONG tables 1cfce / 1c52c
        of C4 1cfbe / C5 1c51c), BYTE 9c 0..5 (the 215e6 key), BYTE 9f 0..8 (the table jump 203ac, decision 2), BYTE a9 0..5 (the LONG table 20444 of
        2042e), LONG 8c(A6) a record whose BYTE 4 is 0..18 (the index of the ROM LONG tables 22028 / 22074 / 220c0 of C9 2218c, 19 LONGs each), A1 a
        handler of the ROM list of the JMP (A1) (decision 2), D0 input bits, D1 / D7 small (1cec2 / ea680 / 2156a results), D0 a node pointer for a
        direct 1c50e entry (MOVEA.L D0,A0; CLR.L b2(A0)), LONG c(A6) a node pointer (the parent of the 1c4b0 child), LONG 84(A6) a routed slot-84 value
        (the C3 JSR (A4) 201a6 that the BRA 201a2 blocks reach), LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), LONG 5434(A5) = 0 (C2
        decision 2), BYTE 10fd82 = 0 (keeps the controller C1 4a974 off the BIOS call c00450, not mapped natively)."""
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
        if entry == 0x1c50e:
            regs['d0'] = self.pointer()                         # 1c500: D0 = LONG c(A6) (not 0), the parent node of the 1c4b0 child
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.3 else self.pointer()
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
            for off, size, v in hint.get('a6rec', []):
                writes.append(((a6 + off) & 0xffff, size, rec + v))   # a node field that points into the declared record
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
    require(len(STARTS) == 132 and len(STARTS_SET) == 132, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c10_block', ('start is not routed to player c10', hex(s), unit_of(s)))
    for jmp, handlers in LIST_JUMPS.items():
        require(mine(jmp) and jmp in STARTS, ('JMP (A1) block', hex(jmp)))
        for t in handlers:
            require(unit_of(t) is not None, ('list handler must be routed', hex(t)))
    # the table jump 203ac (decision 2): only the executed entry 203b0 is routed (a C10 start); the C3 / C7 table entries 20324 / 252b4 are C10 starts
    require(set(t for t in TABLE_203B0 if unit_of(t) is not None) == {0x203b0}, 'only the executed table entry 203b0 is routed')
    require(unit_of(0x20324) == unit_of(0x252b4) == 'animation_player_c10_block', 'the C3 / C7 table entries 20324 / 252b4 are C10 starts')
    for t in EXIT_STOPS:
        require(unit_of(t) is None, ('later-unit stop must stay unrouted', hex(t)))
    rng = random.Random(0xC10A)
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
    sys.stderr.write('pc10 spec: %d fixtures (%d natural), visited %d/132, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc10: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc10: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts









def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the WORD 76 / 78 and BYTE
    7a of the 1c4b0 child: TST.W, CMPI.B, the SUBQ.W result 0; the parent LONG c(A6) 0 / a node; the BYTE 15 / 9e / a7 / a5 / 7e / 9c / 9d bits of the
    player states; the D0 input bits of 1dcb0 / 1dcbe / 1f004 / 1f01a / 1f022 / 21e16 .. 21e2e / 222a0 / 222c0 / 222d8 / 22364 (LONG bits 0 1 3 4 5 6
    7); the WORD masks of 1f00c / 1f048 (AND.W #c); the BYTE compares of 1f02e / 1f036 (D1.B 1 / 2); the signed TST.B 9d of the bundled chains 222c8 /
    222e0 / 222f0; the TST.W D7 of 22304 / 2237e; the BYTE 9f of the table jump 203a0 (0..8) and a9 of 2042e (0..5); the WORD arithmetic of 24b78
    (SUB.W / ADDI.W carry); the BCHG of 22148; the BYTE 61(A2) of 252ce; the handlers of the JMP (A1) lists), the upper register bits of the WORD / BYTE
    operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    d0bits = (0, 1, 2, 3, 8, 0x10, 0x20, 0x40, 0x48, 0x80, 0x11, 0xfffffff7, 0xffffffbf, 0xffffffef, 0xfffffffe, 0xfffffffd, 0xffffff7f, 0xffffffdf,
              0x12340000, 0xffffffff)
    ffnode = dict(a6off=[(0x76, 2, 0x5555), (0x78, 2, 0xffff), (0x7a, 4, 0xffffffff), (0x7e, 1, 0xff), (0x84, 4, 0x12345678), (0x88, 1, 0xff),
                         (0x87, 1, 0xff), (0x89, 1, 0xff), (0x83, 1, 0xff), (0x9c, 1, 0xff), (0x9d, 1, 0x55), (0x9e, 1, 0xff), (0xa3, 1, 0xff),
                         (0xa4, 1, 0x55), (0xa5, 1, 0xff), (0xa6, 1, 0xff), (0xa7, 1, 0xff), (0xa8, 1, 0xff), (0xa9, 1, 0xff), (0xaa, 1, 0xff),
                         (0xab, 1, 0xff), (0x67, 1, 0xff), (0x68, 2, 0xffff), (0x6a, 1, 0xff), (0x1d, 1, 0xff), (0x1e, 2, 0xffff), (0x20, 2, 0xffff),
                         (0x1f, 1, 0xff), (0x22, 4, 0xffffffff), (0x26, 1, 0xff), (0x4, 1, 0xff), (0x79, 1, 0xff), (0x7f, 1, 0xff)])
    node = (world.pointer() if world is not None else 0x10eb00)
    if entry in (0x1c4b8, 0x1c4ea, 0x1f00c, 0x1f048, 0x1f02e, 0x1f036, 0x1f05c, 0x203a0, 0x2042e, 0x204fa, 0x2050c, 0x20bfe, 0x22304, 0x2237e, 0x24b78,
                 0x24b8a, 0x24ecc, 0x24ee2, 0x24f06, 0x252d8, 0x1dcb0, 0x1dcbe, 0x1f004, 0x1f01a, 0x1f022):
        h += [dict(regs=dict(up))]
    # ---- 1c4b0 .. 1c514 (the 28ae child of C5 1c484)
    if entry in (0x1c4b0, 0x1c4ea):
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v), (0x75, 1, 0xff), (0x78, 1, 0xff)]) for v in (0, 1, 0x100, 0x8000, 0xffff)]
    if entry == 0x1c4d2:
        h += byte(0x7a, (0, 1, 0x80, 0xff)) + [dict(a6off=[(0x7a, 1, 0), (0x79, 1, 0xff), (0x7b, 1, 0xff)])]
    if entry == 0x1c4e0:
        h += [dict(a6off=[(0x78, 2, v), (0x77, 1, 0x80), (0x7a, 1, 0x80)]) for v in (0, 1, 2, 0x100, 0x8000, 0xffff, 0x101)]
    if entry in (0x1c4c2, 0x1c4f8, 0x1dc92, 0x1dcb8, 0x1dcc6, 0x1efde, 0x20414, 0x20422, 0x2043e, 0x204e4, 0x21df6, 0x222ba, 0x2230a, 0x22396,
                 0x22168, 0x24ecc, 0x24ee2, 0x22148, 0x223fa):
        h += [dict(ffnode)] + mirror
    if entry == 0x1c500:
        h += [dict(a6off=[(0xc, 4, v)]) for v in (0, node, 0x80000000)] + [dict(a6off=[(0xc, 4, 0x10000)])]
    if entry == 0x1c50e:
        h += [dict(regs=dict(d0=v)) for v in (node, 0x10eb00, 0x10e400)]
    # ---- 1dc8e .. 1dccc (the interpreter stub successors)
    if entry == 0x1dc92:
        h += byte(0xa7, (0, 4, 0xfb, 0xff))
    if entry in (0x1dcb0, 0x1dcbe, 0x1eff2, 0x1f004, 0x1f01a, 0x1f022, 0x21e16, 0x21e1e, 0x21e26, 0x21e2e, 0x222a0, 0x222c0, 0x222d8, 0x22364):
        h += [dict(regs=dict(up, d0=v)) for v in d0bits]
    # ---- 1efd6 .. 1f06c (the input state 1efe4)
    if entry == 0x1efe8:
        h += byte(0x15, (0x80, 0x7f, 0, 0xff)) + [dict(a6off=[(0x15, 1, 0x80)], mirror=True)]
    if entry == 0x1effa:
        h += byte(0x9e, (0, 1, 0x80, 0xff))
    if entry in (0x1f00c, 0x1f048):
        h += [dict(regs=dict(up, d0=v, d1=0x9abc0000)) for v in (0, 4, 8, 0xc, 0x10000, 0xfff3, 0x12340004, 0xfffffff3)]
    if entry in (0x1f02e, 0x1f036):
        h += [dict(regs=dict(up, d1=v)) for v in (1, 2, 0x101, 0x102, 0xffff0001, 0x12345602, 0, 3, 0x81, 0x82)]
    if entry == 0x1f03e:
        h += byte(0xa7, (8, 0xf7, 0xff, 0))
    if entry == 0x1f05c:
        h += [dict(regs=dict(up), a6off=[(0x1e, 2, v)]) for v in (0, 0x8000)]
    # ---- 203a0 .. 20516 (the C3 table entry 20324 and the table jump 203ac)
    if entry == 0x203a0:
        h += [dict(regs=dict(up), a6off=[(0x9f, 1, v), (0x9e, 1, 0xff), (0xa0, 1, 0xff)]) for v in range(9)]
    if entry == 0x2041a:
        h += byte(0x9c, (0, 1, 0x80, 0xff))
    if entry == 0x2042e:
        h += [dict(regs=dict(up), a6off=[(0xa9, 1, v), (0xa8, 1, 0xff), (0xaa, 1, 0xff), (0x9c, 1, 0)]) for v in range(6)]
    if entry == 0x204fa:
        h += [dict(regs=dict(up), a6rec=[(0x8c, 4, 0x20)], rec=[(0x24, 1, v)], a6off=[(0x9e, 1, k)]) for v, k in
              ((0, 0), (18, 1), (19, 2), (31, 3), (32, 0), (0xff, 1), (0x13, 3), (0x12, 2))]
    if entry == 0x2050c:
        h += [dict(regs=dict(up), a6off=[(0x78, 2, v)]) for v in (0, 1, 0x8000, 0xffff)]
    if entry == 0x20bfe:
        h += [dict(regs=dict(up, d2=v)) for v in (0xfffffff9, 0xfffffff8, 0x7ffffffc, 0xffff, 0)]
    # ---- 21dd0 .. 21e36, 22148 .. 22170, 22286 .. 2239e, 223fa (the slot-84 states)
    if entry in (0x21dd0, 0x22148):
        h += byte(0xa7, (0x20, 0xdf, 0xff, 0, 2, 0xfd)) + mirror
    if entry in LIST_JUMPS:
        h += [dict(regs=dict(a1=v)) for v in LIST_JUMPS[entry]]
    if entry == 0x222a8:
        h += byte(0x7e, (0, 1, 0x80, 0xff))
    if entry in (0x222b0, 0x22384):
        h += byte(0xa5, (0x10, 0xef, 0xff, 0))
    if entry in (0x222c8, 0x222e0, 0x222f0):
        h += byte(0x9d, (0, 1, 0x7f, 0x80, 0xff, 0x81)) + [dict(a6off=[(0x9d, 1, 0x80)], mirror=True)]
    if entry in (0x22304, 0x2237e):
        h += [dict(regs=dict(up, d7=v)) for v in (0, 0x10000, 1, 0x8000, 0xffff0000)]
    if entry in (0x22314, 0x22322, 0x22330, 0x2233e):
        h += [dict(a6off=[(0x9d, 1, 0x55), (0x9c, 1, 0xff), (0x9e, 1, 0xff)])] + mirror
    if entry == 0x2234c:
        for a5, a6 in ((0xff, 0xff), (0x10, 0x10), (0xef, 0xef), (0, 0)):
            h.append(dict(a6off=[(0xa5, 1, a5), (0xa6, 1, a6), (0xa4, 1, 0xff), (0xa7, 1, 0xff), (0x84, 4, 0x12345678), (0x88, 1, 0xff)]))
        h += mirror
    # ---- 24b78 .. 24f14 (the sound helper, the 2986 child 24ecc)
    if entry == 0x24b78:
        for d6, d7 in ((0, 0), (0x10, 4), (0x10, 5), (0x10, 3), (0xc, 0), (0xd, 0), (0x8000, 0x7ff4), (0xffff, 0xfff3), (0xffff, 0xfff2), (0x1234, 0x1234)):
            h.append(dict(regs=dict(up), a5off=[(-0x7ff2, 2, d6), (0x547e, 2, d7), (0x547d, 1, 0xff), (0x5480, 1, 0xff)]))
    # ---- 252b4 .. 252e2 (the C7 table entry, main decision 4)
    if entry == 0x252ce:
        h += [dict(regrec=dict(a2=0x20), rec=[(0x81, 1, v), (0x80, 1, 0x55), (0x82, 1, 0x55)]) for v in (0x80, 0x7f, 0xff, 0)]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both) and the Z sources both values
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry == 0x21dd0:
        # 21bc6: CMPI.B #1,9e(A6); BNE -> Clear / BCLR.B #4,a7(A6); BEQ -> Clear / Set
        return dict(a6off=[(0x9e, 1, (1, 1, 0, 2)[t % 4]), (0xa7, 1, (0x10, 0, 0x30, 0xff)[(t // 4) % 4])])
    if entry == 0x21dde:
        # 21baa: TST.B 9f(A6); BNE -> Clear / BYTE (21ba6 + WORD 76) (ROM 0b 0b 06 06) <u BYTE a1(A6) -> Set
        return dict(a6off=[(0x9f, 1, (0, 0, 0, 1)[t % 4]), (0x76, 2, t % 4), (0xa1, 1, (0x0c, 0x0b, 0x06, 0x07, 0xff, 0)[(t // 4) % 6])])
    if entry in (0x21e04, 0x2228e, 0x2236c):
        # 215e6 on the ROM lists 21b0a (keys 0 1 3 4) / 216c8 (key 0): key BYTE 9c -> Set (A1 the handler); else Clear
        return dict(a6off=[(0x9c, 1, (0, 1, 2, 3, 4, 5, 0xff)[t % 7])])
    if entry == 0x22148:
        # 1cb08 on the ROM WORD table 1b7fc (BYTE a7 bit 1 set before the BCHG) / 1b81e (clear): W = WORD (A0 + 2 x BYTE 9f); 0 -> Clear; else C5
        # 1cb1a: TST.L (LONG 22(A6) + 4 x WORD (A0 + W))
        k = (t // 2) % 9
        a0, a7 = ((0x1b7fc, 2), (0x1b81e, 0))[(t // 18) % 2]
        w = rom_word(a0 + 2 * k)
        idx = (4 * rom_word(a0 + w)) & 0xffff if w else 0
        return dict(a6off=[(0x9f, 1, k), (0x22, 4, SCR), (0xa7, 1, a7)], writes=[((SCR + idx) & 0xffff, 4, (0, 0x12345678)[t % 2])] if idx < 0x400 else [])
    if entry == 0x1efe8:
        return dict(a6off=[(0x15, 1, (0x80, 0x7f, 0, 0xff, 0x81, 1)[t % 6])])
    if entry == 0x1eff2:
        return dict(regs=dict(d0=(0x20, 0, 0xffffffdf, 0xffffffff, 0x22, 0x12340000)[t % 6]))
    if entry == 0x204fa:
        # C5 1c51c: D7 = LONG (1c52c + 4 x BYTE 9e(A0 = A6)) (ROM 0007ffff x 4); BTST.L D1,D7 with D1.B = BYTE 4(LONG 8c(A6)): bit 0..18 set (BNE 20516)
        return dict(a6rec=[(0x8c, 4, 0x20)], rec=[(0x24, 1, (0, 18, 19, 31, 32, 0x13, 0xff, 5)[t % 8])], a6off=[(0x9e, 1, (t // 8) % 4)])
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
    """Installed values and child callbacks run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the
    first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # WORD 76 / 78, BYTE 7a, LONG c (the 1c4b0 child), BYTE 15 bit 7 / 9e / a7 bit 3 (1efe4), BYTE 1d(A6) < 4 (8ebe / 8ff4), LONG 26 (0: 49fc6 Set)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x76, 2, (0, 1, 0x1a6d, 0)[t % 4]), (0x78, 2, (1, 2, 0, 0xc)[(t // 2) % 4]),
                               (0x7a, 1, (0, 0, 1)[(t // 3) % 3]), (0xc, 4, (0, world.pointer())[(t // 5) % 2]),
                               (0x15, 1, (0, 0x80, 1, 0x81, 0xff)[t % 5]), (0x9e, 1, (0, 1)[(t // 2) % 2]), (0xa7, 1, (0, 8, 0x11, 0xff)[(t // 4) % 4])] +
                        ([(0x26, 4, 0)] if t % 5 != 4 else []))
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
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a NATURAL frame in which a node of the pool POOL holds one of NATURAL_POOL as its
    callback LONG, or a player node (NATURAL_NODES) holds one of NATURAL_CALLBACKS as its callback LONG, one of NATURAL_SLOTS as its slot-84 LONG
    84(A6) with a routed callback LONG, or any routed callback LONG (NATURAL_PLAYER_ANY: the frames in which the re-observation first records a C10
    start); declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the frame
    start.  Up to the sentinel or the first unrouted PC; kept when the run executes a C10 start."""
    count = 0
    seen = set()
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        nodes = []
        for a in range(POOL[0] & 0xffff, POOL[1] & 0xffff, 2):
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if cb in NATURAL_POOL:
                nodes.append(0x100000 + a)
        for node in NATURAL_NODES:
            a = node & 0xffff
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            sl = struct.unpack('>I', ram[a + 0x84:a + 0x88])[0]
            if cb in NATURAL_CALLBACKS or (unit_of(cb) is not None and (sl in NATURAL_SLOTS or NATURAL_PLAYER_ANY)):
                nodes.append(node)
        for node in nodes:
            a = node & 0xffff
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if (cfg, case, frame, node) in seen:
                continue
            seen.add((cfg, case, frame, node))
            regs = dict(st0['regs'])
            regs.update(a5=0x108000, a6=node, a7=0x10ef00)
            st = U.make_state(ram, regs, cb, st0['bank'], st0['pvc'])
            st = U.with_host_writes(st, [(0xef00, 4, SENTINEL)])
            tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
                continue                                    # 290e after 2986: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
            if not set(tr['pcs']) & STARTS_SET:
                continue                                    # the run does not reach C10 code
            record(tr['pcs'] + [tr['stop']])
            sl = struct.unpack('>I', ram[a + 0x84:a + 0x88])[0]
            add_run(add, 'natural-%05x-%s%03d-f%d-%x' % (cb, cfg, case, frame, node), st, tr,
                    dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], slot84=sl,
                         unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
            count += 1
    require(count >= 40, ('too few natural node fixtures', count))



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
    err('odd-pc', U.with_host_writes(st, pc=0x1c4b1), 'unaligned animation machine PC', 0x1c4b1)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    device = 'unsupported animation machine write device'
    # the JMP (A1) (contract decision 2): A1 outside the list of the jump (compared as a LONG)
    for v in (0x21d60, 0x21e49, 0, 0x121602, 0x21e52, 0x1021e48, 0x21c23):
        err('21e10-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21e10), ERROR_JUMP, 0x21e10)
    for jp in (0x2229a, 0x22378):
        for v in (0x21d60, 0x21e48, 0, 0x1021602):
            err('%x-a1-%x' % (jp, v), U.with_host_writes(st, regs=dict(a1=v), pc=jp), ERROR_JUMP, jp)
    # the table jump 203ac (contract decision 2): BYTE 9f(A6) 9 .. ff is beyond the table (checked); 1 .. 8 is an unrouted table entry (the next dispatch)
    for v in (9, 0x10, 0x80, 0xff):
        err('203a0-9f-%x' % v, U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, v)], pc=0x203a0), ERROR_JUMP, 0x203a0)
    for v in range(1, 9):
        err('203a0-9f-%x-entry' % v, U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, v)], pc=0x203a0), unrouted, 0x203b0 + 4 * v)
    # the Z source of 1efee (contract decision 3): BYTE 15(A6) outside work RAM / fixed ROM (the bank window, the device space)
    for v in (0x200000 - 0x15, 0x3c0000, 0x2ffff0):
        err('1efee-a6-%x' % v, U.with_host_writes(st, regs=dict(a6=v), pc=0x1efee), ERROR_FLAG, 0x1efee)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('1c4c2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1c4c2), odd_write, 0x1c4c2, stop=0x1c4d2)
    err('1c4e0-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1c4e0), odd_word, 0x1c4e0, stop=0x1c4e8)
    err('1c500-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1c500), odd_word, 0x1c500, stop=0x1c50e)
    err('24ecc-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x24ecc), odd_write, 0x24ecc, stop=0x24b78)
    err('2234c-rom-node', U.with_host_writes(st, regs=dict(a6=0x1b000), pc=0x2234c), device, 0x2234c, stop=0x22360)
    err('1c50e-odd-a0', U.with_host_writes(st, regs=dict(d0=0x10eb01), pc=0x1c50e), odd_write, 0x1c50e, stop=0x1c514)
    err('22312-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x22312), odd_word, 0x22312)
    err('24b94-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x24b94), odd_word, 0x24b94)
    err('1dc8e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1dc8e), odd_word, 0x1dc8e, stop=0x1d1d0)
    # failures after executed blocks: 1c4d2 (BYTE 7a = 0) -> 1c4e0 (WORD 78 = 2 -> 1) -> the RTS 1c4e8 at an odd A7; 22300 .. 22304 (D7.W = 0) -> 22312;
    # 2237e -> 2239e; the C3 table entry 20324 -> 203a0 with BYTE 9f = 3 -> the unrouted entry 203bc; the C7 table entry 252b4 -> 252ce (BYTE 61(A2) bit
    # 7 clear) -> 252d8 (JSR 3af8 at an odd A7)
    err('1c4d2-then-1c4e8', U.with_host_writes(st, [((a6 + 0x7a) & 0xffff, 1, 0), ((a6 + 0x78) & 0xffff, 2, 2)], regs=dict(a7=a7 + 1), pc=0x1c4d2),
        odd_word, 0x1c4e8)
    err('22304-then-22312', U.with_host_writes(st, regs=dict(a7=a7 + 1, d7=0x10000), pc=0x22304), odd_word, 0x22312)
    err('2237e-then-2239e', U.with_host_writes(st, regs=dict(a7=a7 + 1, d7=0), pc=0x2237e), odd_word, 0x2239e)
    err('20324-then-203bc', U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, 3)], pc=0x20324), unrouted, 0x203bc)
    err('252b4-then-252d8', U.with_host_writes(st, [((a6 + 0x61) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1, a2=a6), pc=0x252b4), odd_word, 0x252d8)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x24b78, 0x203a0, 0x2234c, 0x1c4e0)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
