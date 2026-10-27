"""V1 fixture spec of the area-C unit C11 (engine/src/animation_machine_player_c11.cpp, 209 block starts; file prefix pc11 / player_c11 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c11-contract.md, plan docs/analysis/area-c-completion-plan.md sections 11.5 / 11.8 unit C-1):
the continue counter helpers ca64 / ca6a, the stage-script helper 1a952, the record animation helper 1cb72 / 1cb76, the rest of the appearance-type D7
chain 1d3e0 .. 1d434 of 1d388 with the entries 1d722 1d746 (-> callback 1d75a) 1d8e2 1d906 1d9b2 (2986 child 3fedc) 1db28 1db46 (-> callback 1db7c)
1ddd8 (-> callback 1dde8) and the helpers 1d508 1d5c4 1d5fc, the velocity helper 1e5aa (49bf2, MULS x 2, 4c2c4), 1e640 / 1e65a, the 28ae child
callback 1e67a -> 1e6c0, the state 1e8de -> 1e918 -> callback 1e92c, the slot-84 states 21950 -> 21960 and 21a42 -> 21a76 (JMP (A1) 21a82 on the list
216c8), the 2986 child callback 3fedc, the WORD table helper 49bf2, the credit reader 4a90e, the record base helper 4d196, the continue entry 4eb6a ->
callback 4ebe2 -> 4ec32 .. 4ed34 and the appearance helper e8c3a (MOVEM.W, 2986 child b3dfc).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR14, C1..C10) with declared host edits.
This code runs natively only in the third IO observation (tools/observe_animation_machine_io_ext2.py, runs M1.5 M2.0 M3.1 M4.0 G1.94 G1.68): the
'natural' family takes the frame-start states of that observation (state packs, read-only; directory IO_EXT2 below, its compared_sha256 pinned) in which
a node holds a C11 node entry or install (1e67a 1e6c0 3fedc 1d75a 1db7c 1dde8 1e92c 4ebe2, the C6 install 1e918) as its callback LONG, a player node
holds a C11 slot-84 value (21960 21a76), or the observation first records a C11 start in that frame (the player nodes, any routed callback); it keeps
their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return LONG, PC = the callback).  The
spec reads those packs itself (io_pack below); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 9 C consumers and the Z reader 4eb84 is entered directly (the seed world with declared edits).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers and the Z reader through 4eb7a (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the installed values and child callbacks (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers and states entered as subroutines or branch targets of other units (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 9 consumers, the jump-target guard of JMP (A1) 21a82 (decision 2),
            the Z source of 4eb84 outside the four 4a974 BYTEs (decision 3), odd node / stack, failures after executed blocks: checked error, state
            preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR14, C1..C10
specs do).
"""
import gzip
import json
import os
import random
import re
import struct
import sys

import verify_animation_machine_unit_fixtures as U

ROOT = U.ROOT
SENTINEL = 0xff000                      # even, outside every routed range (asserted below); the RTS of the entered block lands here.
SEEDS = (116, 117)
FRAME = 2
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR14, C1..C10)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc11'
ERROR_PC = 'unsupported animation player c11 PC'
ERROR_CARRY = 'player c11 caller requires known carry'
ERROR_JUMP = 'unsupported animation player c11 jump target'
ERROR_FLAG = 'unsupported animation player c11 flag source'
# The third IO observation (read-only state packs of the natural family; area-C plan 11.3).  Until it is moved to the shared artifacts (plan 11.7
# decision 1) it lives in the scratch directory; MS5_IO_EXT2 overrides the directory.  Its compared_sha256 is pinned (build() checks it), so every
# location gives the same states.
IO_EXT2_COMPARED = 'd30e68d6b8c7f69181be12b00f017c4eafccb705416af7e8beea02b6d9595673'
IO_EXT2 = os.environ.get('MS5_IO_EXT2') or ('artifacts/animation_machine_io_ext2' if (ROOT / 'artifacts/animation_machine_io_ext2').is_dir() else
                                            '/Users/start/Workspce/ms5-scratch/obs3/final')

RANGES = [(0xca64, 0xca70), (0x1a952, 0x1a966), (0x1cb72, 0x1cbb2), (0x1d3e0, 0x1d438), (0x1d508, 0x1d510), (0x1d5c4, 0x1d5e2), (0x1d5fc, 0x1d61a),
          (0x1d722, 0x1d776), (0x1d8e2, 0x1d90a), (0x1d9b2, 0x1da60), (0x1db28, 0x1dbc6), (0x1ddd8, 0x1ddfc), (0x1e5aa, 0x1e60a), (0x1e640, 0x1e648),
          (0x1e65a, 0x1e65c), (0x1e67a, 0x1e71e), (0x1e724, 0x1e776), (0x1e8de, 0x1e96c), (0x21950, 0x2196c), (0x2196e, 0x2197e), (0x21a42, 0x21a90),
          (0x21a98, 0x21aa2), (0x21aaa, 0x21aac), (0x3fedc, 0x3fefc), (0x49bf2, 0x49c00), (0x4a90e, 0x4a944), (0x4d196, 0x4d1ac), (0x4eb6a, 0x4ebfc),
          (0x4ec32, 0x4ed3c), (0xe8c3a, 0xe8cc0)]
STARTS = sorted(int(x, 16) for x in (
    'ca64 ca6a 1a952 1cb72 1cb76 1cb9e 1cba4 1d3e0 1d3e8 1d3f0 1d3f8 1d400 1d408 1d410 1d418 1d420 1d428 1d430 1d508 1d5c4 1d5ce 1d5d2 1d5e0 1d5fc '
    '1d606 1d60a 1d618 1d722 1d742 1d746 1d74c 1d754 1d75a 1d764 1d76a 1d770 1d774 1d8e2 1d8e6 1d8f0 1d8f6 1d8fa 1d8fe 1d902 1d906 1d9b2 1d9b8 '
    '1d9cc 1d9d8 1d9e4 1d9ee 1da04 1da18 1da38 1da4a 1da4e 1da5c 1db28 1db2c 1db42 1db46 1db5c 1db64 1db72 1db76 1db7c 1db84 1db86 1db8a 1db8e '
    '1db98 1db9c 1dba0 1dbb6 1ddd8 1dddc 1dde8 1ddf2 1ddfa 1e5aa 1e5b0 1e5ba 1e5d8 1e5ec 1e5f0 1e5fc 1e600 1e604 1e606 1e640 1e65a 1e67a 1e692 '
    '1e6a6 1e6b6 1e6c0 1e6ce 1e6e4 1e6ea 1e6fa 1e6fe 1e70e 1e724 1e72e 1e734 1e73e 1e744 1e76e 1e774 1e8de 1e8f4 1e918 1e920 1e92c 1e930 1e93a '
    '1e93e 1e946 1e94a 1e94e 1e954 1e958 1e962 1e968 21950 21958 21960 21968 2196e 21972 2197a 21a42 21a5e 21a76 21a7e 21a82 21a84 21a88 21a98 '
    '21a9c 21aaa 3fedc 3fee2 3feee 49bf2 4a90e 4a916 4a91e 4a92c 4a930 4a93c 4a93e 4d196 4d19e 4d1a6 4d1aa 4eb6a 4eb72 4eb7a 4eb84 4eb88 4eb8e '
    '4eb94 4eb9a 4eb9e 4eba4 4eba8 4ebac 4ebb6 4ebbc 4ebc6 4ebd6 4ebe2 4ebf4 4ec32 4ec3c 4ec4a 4ec50 4ec58 4ec64 4ec6a 4ec70 4ec7c 4ec80 4ec88 '
    '4ec96 4ec9c 4eca6 4ecac 4ecc4 4ecd0 4ecd4 4ecd8 4ece6 4ecec 4ed0c 4ed14 4ed18 4ed22 4ed26 4ed2e 4ed34 e8c3a e8c40 e8c7c e8c84 e8c9e e8ca2 '
    'e8cbc').split())
# the 9 C consumers: BCS 1d5ce 1d606 (49c38), BCC 1d770 (4836e), BCC 1d8fa (1d510), BCS 1db9c (1d508 -> 1d514), BCC 1e5ec (4c2c4, a later-unit stop),
# BCC 21968 21a7e (215e6), MOVEM.W (A7)+,D0-D6; BCC e8c7c (2986)
CONSUMERS = (0x1d5ce, 0x1d606, 0x1d770, 0x1d8fa, 0x1db9c, 0x1e5ec, 0x21968, 0x21a7e, 0xe8c7c)
CLEAR_SET = ()
SET_SET = ()
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()
STARTS_SET = set()
# the Z reader (contract decision 3): BNE 4eb84 on the TST.B (A0); RTS that ends 4a974 (re-read BYTE (A0)): never entered directly by a native run
Z_READERS = (0x4eb84,)
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
# 1e5ec BCC reads the C of 4c2c4 (area D, a later unit): no V1 run reaches 1e5ec (both outcomes gated by the later unit; the C++ consumer is checked by
# the unit test with a declared C)
LATER_GATED = {(0x1e5ec, 0x1e604), (0x1e5ec, 0x1e5f0)}
GATED_CONSUMERS = (0x1e5ec,)
# Branch outcomes that no V1 world takes (each is checked by the unit test with declared state):
#   4a91e TST.B 7e80(A5); BEQ.W 4a930 (MVS): the BEQ side goes on to MOVE.B (A1,D0.W),D0 with A1 = d00034, the MVS backup RAM; the native model treats
#   it as a device read (no V1 world), the C++ program bus as 'unsupported program bus device address' (unit test row);
#   e8c7c MOVEM.W; BCC.W e8ca2: the Clear side is the 2986 failure (28ae finds no free node), which the C++ 2986 executor rejects for every caller but
#   e8a84 ('cue wrapper failure requires known caller X', C7 decision 6); the V1 runs through 290e are dropped (as in every 2986 caller unit).
MODEL_GATED = {(0x4a91e, 0x4a930), (0xe8c7c, 0xe8ca2)}
TRAPS = ()
# Declared stops of the native runs (a straight-line unrouted PC after a routed block is not the interior of a routed block): the C11 later-unit stops
# (UNIT_EXITS) and the still unrouted declared stops of the earlier specs that the C11 runs pass through (C1..C10, FR10..FR14; scratch union).
UNIT_EXITS = (0xca5c, 0x1d438, 0x1d776, 0x1d940, 0x1db0a, 0x1dbf0, 0x1e648, 0x1e71e, 0x1e96c, 0x2196c, 0x21a90, 0x21aa2, 0x40a5a, 0x4c2c4, 0x4ebfc)
EXIT_STOPS = UNIT_EXITS + (0x1de3c, 0x1e21c, 0x1fc96, 0x1fd3c, 0x1fd50, 0x21ea0, 0x21fa6, 0x4e69a, 0x4ef08)
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the Z chain 4eb7a -> 4eb84 (4a974)
CHAINS = ((0x1d5c4, 0x1d5ce), (0x1d5fc, 0x1d606), (0x1d76a, 0x1d770), (0x1d8f6, 0x1d8fa), (0x1db98, 0x1db9c), (0x21960, 0x21968), (0x21a76, 0x21a7e),
          (0xe8c40, 0xe8c7c), (0x4eb7a, 0x4eb84))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()                           # no computed table jump in C11
JUMP_TABLE = ()
JUMP_ROUTED = ()
# the JMP (A1) of C11 (contract decision 2): A1 = the handler LONG that C3 215e6 loaded from the ROM list 216c8 (21a76 -> 21a82); any other A1 is the
# C++ checked jump-target error (a native run that jumps elsewhere is not a fixture world)
LIST_216C8 = (0x21602,)
LIST_JUMPS = {0x21a82: LIST_216C8}
# computed jumps that the C11 runs reach (pc10 OTHER_JUMP_PCS, the C10 table jump 203ac, C11 21a82): an unrouted target is a stop even when it is the
# straight-line successor
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36,
                  0x2224c, 0x22428, 0x21e10, 0x2229a, 0x22378, 0xcc7a8, 0xcc82a, 0x203ac, 0x21a82)
TABLE_ENTRIES = ()
# routed slot-84 states (pc10 SLOT84_C3 and the C11 values 21960 21a76) for the worlds
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92, 0x21e6a, 0x21cd8, 0x21d2a, 0x2210c, 0x22128, 0x22240, 0x2241c, 0x22452,
             0x21e04, 0x2228e, 0x22360, 0x21960, 0x21a76)
# installed values and child callbacks entered as node callbacks: 1e67a (the 28ae child of 1e8e4 / C6 1e828), 1e6c0 (1e6b6), 3fedc (the 2986 child of
# 1d9ee), 1d75a (1d754), 1db7c (1db76), 1dde8 (1dddc), 1e92c (1e920), 4ebe2 (4ebd6), 1e918 (the C6 install 1e8d4); the callee entries (branch targets
# and subroutines of other units' blocks, the C3 list handler 21950, the slot-84 values 21960 21a76)
NODE_ENTRIES = (0x1e67a, 0x1e6c0, 0x3fedc, 0x1d75a, 0x1db7c, 0x1dde8, 0x1e92c, 0x4ebe2, 0x1e918)
CALLEES = (0xca64, 0xca6a, 0x1a952, 0x1cb72, 0x1cb76, 0x1d3e0, 0x1d508, 0x1d5c4, 0x1d5fc, 0x1d722, 0x1d746, 0x1d8e2, 0x1d906, 0x1d9b2, 0x1db28,
           0x1db46, 0x1ddd8, 0x1e5aa, 0x1e640, 0x1e8de, 0x21950, 0x21960, 0x21a42, 0x21a76, 0x49bf2, 0x4a90e, 0x4d196, 0x4eb6a, 0xe8c3a, 0x4ec32)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
# natural worlds of the third observation: (config, case, frame) (scratch natscan_c11.py -> natural_c11.json: per run and key the first, a middle and
# the last frame of the callbacks 1e6c0 1e92c 1d75a 3fedc 4ebe2 1e918, the slot values 21960 21a76 and the frames in which the observation first records
# a C11 start)
NATURAL = tuple(tuple(x) for x in (
    ('G1.68', 68, 960), ('G1.68', 68, 961), ('G1.68', 68, 2255), ('G1.68', 68, 2720), ('G1.68', 68, 2999), ('G1.94', 94, 768), ('G1.94', 94, 769),
    ('G1.94', 94, 2064), ('G1.94', 94, 2651), ('G1.94', 94, 2999), ('M1.5', 94, 190), ('M1.5', 94, 191), ('M1.5', 94, 192), ('M1.5', 94, 207),
    ('M1.5', 94, 210), ('M1.5', 94, 211), ('M1.5', 94, 294), ('M1.5', 94, 991), ('M1.5', 94, 996), ('M1.5', 94, 1082), ('M1.5', 94, 1095),
    ('M1.5', 94, 1118), ('M1.5', 94, 1158), ('M1.5', 94, 1926), ('M1.5', 94, 1932), ('M1.5', 94, 1933), ('M1.5', 94, 1999), ('M2.0', 94, 190),
    ('M2.0', 94, 191), ('M2.0', 94, 203), ('M2.0', 94, 215), ('M3.1', 94, 248), ('M3.1', 94, 300), ('M4.0', 94, 192), ('M4.0', 94, 193),
    ('M4.0', 94, 475),))
NATURAL_CALLBACKS = (0x1e67a, 0x1e6c0, 0x3fedc, 0x1d75a, 0x1db7c, 0x1dde8, 0x1e92c, 0x4ebe2, 0x1e918)   # C11 entries / installs as a callback LONG
NATURAL_SLOTS = (0x21960, 0x21a76)                                   # or a C11 slot-84 LONG of a player node (entered from 201a6 JSR (A4))
NATURAL_NODES = (0x100cb8, 0x100da8)    # the player nodes searched (work RAM CPU addresses)
NATURAL_PLAYER_ANY = True               # a player node with any routed callback is kept when its run reaches a C11 start
POOL = (0x100800, 0x104c00)             # the node area searched for the callbacks
REINSTALL = ()

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x11, 0x12, 0x13, 0x14, 0x16, 0x18, 0x19, 0x1a, 0x1b, 0x1e, 0x1f, 0x20, 0x40,
      0x50, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xef, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf, 0x10, 0x11, 0x13, 0x14, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1e, 0x27, 0x40, 0x7f,
      0x80, 0xa0, 0xe0, 0x100, 0x180, 0x7ff, 0x800, 0x801, 0x7ffc, 0x7fff, 0x8000, 0x8001, 0xffb8, 0xffe0, 0xffe8, 0xfffd, 0xfffe, 0xffff)
VL = (0, 1, 2, 7, 8, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x30000, 0x50000, 0xe2000, 0x7fffffff, 0x80000000, 0xfffc0000, 0xfffd0000, 0xfffe0000,
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
BUNDLED = ()                            # no flag-sharing Bcc chain inside a C11 block


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start or out of the range, 1d430 1e640 1e70e 21968 21a88 21a9c 4ebf4); a Bcc followed by a BUNDLED
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
        if seq[i] in JUMP_PCS and seq[i + 1] not in JUMP_TABLE:
            return None                                 # a computed table jump beyond its table (none in C11)
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at an unrouted target of the
    computed jumps that the C11 runs reach (OTHER_JUMP_PCS: C3 / C4 / C5 / C7 / C8 / C9 / C10, FR4 and the C11 JMP (A1) 21a82), or at the first unrouted
    PC that is not the straight-line successor of the previous instruction (a PC inside a block of another executor is not a block entry)."""
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it (as C1..C10): WORD 76(A6) / 78(A6) mostly 0 / 1 (the
        player index: 4ebe2 ADDA.W, 4ecac BTST bit, 49bca / 48210 / 49c38 slots), LONG 8c(A6) a record whose BYTE 4 is 0..18 (the index of the ROM tables
        1c1c4 / 219f6 of 1cb76 / 21a42), BYTE 9c(A6) 0..10 (the 215e6 key: list 21930 keys 0 / a, list 216c8 key 0), D7.W one of the appearance types of
        the 1d3e0 chain, D1.W small (49bf2 / 48210 results), LONG c(A6) a node pointer (the parent of the 1e67a child), LONG 84(A6) a routed slot-84
        value, LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), LONG 5434(A5) = 0 (C2 decision 2), BYTE 10fd82 = 0 (keeps the controller C1
        4a974 off the BIOS call c00450, not mapped natively), BYTE 7d82(A5) = 0 mostly (home mode: 4a90e reads work RAM, not d00034)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x40, 0x50, 0x80, 0x800, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000))
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((0, 1, 2, 9, 0x109, 0x10001, 0xffff0001, 0x8000, 0x7fff, 0x12340000, 0x80000000))
        if rng.random() < 0.5:
            regs['d7'] = rng.choice((0xf, 0x10, 0xc, 0xd, 0x11, 0x19, 0x1a, 0x1b, 0x18, 0x14, 0x16, 0x15, 0x10016, 0, 0x17, 0xffff, 1))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.5 else self.pointer()
        regs['a1'] = self.pointer()
        if entry in LIST_JUMPS:
            regs['a1'] = rng.choice(LIST_JUMPS[entry])         # the handler LONG 215e6 loaded (decision 2)
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = rec + 0x20 if rng.random() < 0.5 else self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, rec + 0x20 if rng.random() < 0.7 else self.pointer()))   # LONG 8c(A6): a record
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of 1cb76 / C2 1cb08)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(), 0))))  # LONG 3e(A6) (C2 1a9fe..1aa20; 4be82 CMPA.W #0)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): C3 2031c / C5 1cc1a
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): C3 206d4
        writes.append(((a6 + 0x9f) & 0xffff, 1, rng.randrange(9)))                        # BYTE 9f(A6): C2 1cb08
        writes.append(((a6 + 0x9c) & 0xffff, 1, rng.choice((0, 0, 1, 3, 4, 5, 0xa))))    # BYTE 9c(A6): the key of the 215e6 lists
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 0, 1, 1, 2, 3))))         # WORD 76(A6): the player index
        writes.append(((a6 + 0x78) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x100))))        # WORD 78(A6): the player index
        writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                        # BYTE 9e(A6): C4 1cfbe / C5 1c51c tables
        for node in (0x100cb8, 0x100da8):
            writes.append((node & 0xffff, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c))))   # 289e: CMPI.L #270e,(A0)
            writes.append(((node + 0x9e) & 0xffff, 1, rng.randrange(4)))
            writes.append(((node + 0x78) & 0xffff, 2, rng.choice((0, 1))))
        # the declared record (A0 / A4 = rec + 20: BYTEs 3 / 4 0..18, LONGs 24 / 28 / 38, WORD 96; LONG 8c(A6) = rec + 20)
        for off in (0x24, 0x28, 0x38):
            writes.append(((rec + off) & 0xffff, 4, self.value(4)))
        writes.append(((rec + 0x96) & 0xffff, 2, self.value(2)))
        writes.append(((rec + 0x24) & 0xffff, 1, rng.randrange(19)))
        writes.append(((rec + 0x23) & 0xffff, 1, rng.randrange(19)))
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
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e, 0x9f, 0x9c, 0x76, 0x78)):
                continue                                        # callback LONG, node links, the pointer fields and the bounded indices stay declared above
            if reg == 5 and disp in (0x5434, 0x5474, 0x5e26, 0x5734, 0x5738, -0x7ffd + 0x10000, 0x7d82):
                continue
            if reg in (0, 4) and disp in (3, 4):
                continue                                        # BYTEs 3 / 4 of the record (the bounded table indices) stay declared above
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        if rng.random() < 0.8:
            writes.append(((a5 + 0x7d82) & 0xffff, 1, 0))                                 # BYTE 7d82(A5) = 0: 4a90e / 4eb72 home mode
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
    require(len(STARTS) == 209 and len(STARTS_SET) == 209, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c11_block', ('start is not routed to player c11', hex(s), unit_of(s)))
    for jmp, handlers in LIST_JUMPS.items():
        require(mine(jmp) and jmp in STARTS, ('JMP (A1) block', hex(jmp)))
        for t in handlers:
            require(unit_of(t) is not None, ('list handler must be routed', hex(t)))
    # the C3 21620 list handler 21950 and the C3 slot-84 values 21960 / 21a76 are C11 starts; the third observation is the pinned one (IO_EXT2)
    require(unit_of(0x21950) == unit_of(0x21960) == unit_of(0x21a76) == 'animation_player_c11_block', 'the C3 list / slot values are C11 starts')
    obs = json.loads((ROOT / IO_EXT2 / 'observation.json').read_text())
    require(obs.get('compared_sha256') == IO_EXT2_COMPARED, ('third IO observation pin', IO_EXT2, obs.get('compared_sha256')))
    rng = random.Random(0xC11A)
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
                                     (a, t) not in BRANCH_IMPOSSIBLE and (s, t) not in MODEL_GATED)
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
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)) - set(t for a, t in STATIC_IMPOSSIBLE) - set(CONSUMERS) - set(Z_READERS) -
                             set(t for a, t in MODEL_GATED if a == entry))
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
    META['model_gated'] = [(hex(a), hex(t)) for a, t in sorted(MODEL_GATED)]
    META['gated_consumers'] = [hex(x) for x in GATED_CONSUMERS]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('pc11 spec: %d fixtures (%d natural), visited %d/209, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc11: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc11: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the D7.W appearance types
    of the 1d3e0 chain with upper bits; TST.W D1 of 1d8f0; CMPI.B #9,D1 of 1db5c; the WORD 78(A6) player index of 1d9b8 / 1da38 / 1db64 / 4d196; the
    SUBQ.W counters 88 / b0 (0 / 1 / 8000); the signed TST.W D1 of 1e5b0 and the MULS operands; the NEG.W / SUBI.W sign of 1e5f0; D0 bit 6 of 1e640;
    the BTST #3 / SNE / EOR.B of 1e6ce and TST.B D0 of 1e6e4; the parent BYTEs 9e / a7 (bits 7 / 6) / 7c and WORD 76 of 1e70e .. 1e744; BYTE a7 bit 3
    of 1e930 and the CMPI.W #18,D7 of 1e93e; D0 bit 4 of 21972; BYTE 7e and TST.W D7 of 21a88 / 21a9c; the A5 BYTEs 7d82 / 7e80 / -7ffd of 4a90e; the
    continue BYTEs 5d21 / 7d82 / 5d1f / 9a / a1 / a2 / 7db6 + player, the WORD (A0) of 4ec6a, CMPI.W #800, BTST #5,3(A0) and the BTST D0,7004(A5) bit;
    the record BYTE 3 of e8c40), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a
    fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    a5byte = lambda off, vals: [dict(a5off=[(off, 1, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    ffnode = dict(a6off=[(0x76, 2, 0x5555), (0x7a, 2, 0xffff), (0x7c, 2, 0xffff), (0x7e, 1, 0xff), (0x88, 2, 0xffff), (0x8a, 2, 0xffff), (0x9a, 1, 0xff),
                         (0x9c, 1, 0xff), (0xa1, 1, 0xff), (0xa2, 1, 0xff), (0xa5, 1, 0xff), (0xa6, 1, 0xff), (0xa7, 1, 0xff), (0xa9, 1, 0xff),
                         (0xaa, 1, 0xff), (0xae, 2, 0xffff), (0xb0, 2, 0xffff), (0x15, 1, 0xff), (0x1e, 2, 0xffff), (0x20, 2, 0xffff), (0x36, 4, 0xffffffff),
                         (0x3a, 4, 0xffffffff), (0x42, 2, 0xffff), (0x68, 2, 0xffff), (0x81, 1, 0xff), (0x82, 1, 0xff)])
    if entry in (0x1a952, 0x1cb76, 0x1cba4, 0x1d722, 0x1d74c, 0x1d9b8, 0x1d9cc, 0x1da18, 0x1da38, 0x1da4e, 0x1db2c, 0x1db5c, 0x1e5b0, 0x1e5ba, 0x1e5d8,
                 0x1e5f0, 0x1e604, 0x1e606, 0x1e6ce, 0x1e744, 0x1e93e, 0x49bf2, 0x4a930, 0x4a93e, 0x4ec3c, 0x4ec80, 0x4ecac, 0x4ecd8, 0x4ecec, 0xe8c40,
                 0xe8ca2, 0x3feee, 0x4eb8e, 0x21a9c):
        h += [dict(regs=dict(up))]
    # ---- 1a952 / 1cb76 / 1cba4
    if entry == 0x1a952:
        h += [dict(regs=dict(up, d0=v), a5off=[(0x53cc, 1, b)]) for v, b in ((0, 0xff), (3, 0), (0xffff, 0x55), (0x12345601, 0xfc), (2, 3))]
    if entry == 0x1cb76:
        for k, z in ((0, 0), (1, 1), (2, 0), (5, 1), (0x12, 0)):
            h.append(dict(rec=[(0x24, 1, k), (0x60 + 2 * k, 2, z)], a6rec=[(0x8c, 4, 0x20), (0x22, 4, 0x80)], regrec=dict(a0=0x40), regs=dict(up)))
    # ---- 1d3e0 .. 1d430 (the appearance-type chain): D7.W = each type, with upper bits, and its neighbours
    if 0x1d3e0 <= entry <= 0x1d430:
        for v in (0xf, 0x10, 0xc, 0xd, 0x11, 0x19, 0x1a, 0x1b, 0x18, 0x14, 0x16, 0x15, 0x17):
            h.append(dict(regs=dict(up, d7=0x12340000 | v)))
        h += [dict(regs=dict(up, d7=v)) for v in (0x1000f, 0xffff0016, 0x16, 0x10016)]
    if entry == 0x1d8f0:
        h += [dict(regs=dict(up, d1=v)) for v in (0, 0x10000, 1, 0x8000, 0xffff0000)]
    if entry in (0x1d9b8, 0x1da38, 0x1db64, 0x4d196):
        h += [dict(regs=dict(up), a6off=[(0x78, 2, v), (0x77, 1, 0xff), (0x7a, 1, 0xff)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x1d9b8:
        h += [dict(regs=dict(up), a6off=[(0x42, 2, a), (0x78, 2, 0)], a5off=[(0x53a2, 2, b)]) for a, b in ((0, 1), (0x8000, 0x7fff), (0x1234, 0x1234))]
    if entry in (0x1d9cc, 0x1da18):
        h += [dict(ffnode), dict(a6off=[(0xae, 2, 0x48), (0x42, 2, 0x47), (0x15, 1, 1)], a5off=[(0x53a2, 2, 0xffff)])] + mirror
    if entry == 0x1db5c:
        h += [dict(regs=dict(up, d1=v)) for v in (9, 0x109, 0xffff0009, 8, 0x89)]
    if entry in (0x1db7c, 0x1ddf2):
        off = 0x88 if entry == 0x1db7c else 0xb0
        h += [dict(a6off=[(off, 2, v), (off - 1, 1, 0x55), (off + 2, 1, 0x55)]) for v in (0, 1, 2, 0x8000, 0xffff, 0x100)]
    if entry in (0x1db46, 0x1db64, 0x1db72, 0x1dba0, 0x1dbb6, 0x1dddc, 0x1e8f4, 0x1e920, 0x1e6b6, 0x1e692, 0x1e67a, 0x21a5e, 0x21958, 0x3fee2, 0x3feee,
                 0x4ebd6, 0x4ebc6, 0x4ed34, 0x1e8de, 0x21a42, 0x1d754, 0x1db76):
        h += [dict(ffnode)] + mirror
    # ---- 1e5aa .. 1e606 (the velocity helper)
    if entry == 0x1e5b0:
        h += [dict(regs=dict(up, d1=v)) for v in (0, 0x8000, 0x7fff, 0xffff, 0x10000, 0x18000, 7)]
    if entry == 0x1e5ba:
        h += [dict(regs=dict(up, d1=v, d2=0xffff0000, d3=0x12340000)) for v in (0, 1, 7, 0xf, 0x3f, 0x10003)]
    if entry == 0x1e5f0:
        h += [dict(regs=dict(up, d0=v), stack=[(0, 2, 0x8001), (2, 4, SENTINEL)]) for v in (0, 0xfff0, 0xfff1, 0xffef, 0x10, 0x8000, 0xffff, 0x12340001,
                                                                                             0x7ff0)]
    if entry in (0x1e600, 0x1e604, 0x1e5ec):
        h += [dict(regs=dict(up), stack=[(0, 2, v), (2, 4, SENTINEL)]) for v in (0, 0x8001)]
    if entry == 0x1e5fc:
        h += [dict(regs=dict(up, d0=v), a6off=[(0x3a, 2, w), (0x39, 1, 0x55), (0x3c, 1, 0x55)], stack=[(0, 2, 0x1234), (2, 4, SENTINEL)])
              for v, w in ((0xffff, 0), (0x8000, 0x7fff), (0xfff0, 0x10))]
    if entry in (0x1e606, 0x3feee):
        h += [dict(regs=dict(up), stack=[(0, 2, v), (2, 4, SENTINEL)]) for v in (0, 0x8001, 0xffff)]
    if entry == 0x1e640:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x40, 0xffffffbf, 0xffffffff, 0x12340040)]
    # ---- 1e67a .. 1e774 (the 28ae child 1e67a)
    if entry == 0x1e6ce:
        for w, b in ((0, 0), (8, 0), (0, 0xff), (8, 0xff), (0xfff7, 0xff), (0xfff7, 0), (8, 0x55), (0x8008, 0x7f)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 2, w)], a6off=[(0x88, 1, b), (0x87, 1, 0x55), (0x89, 1, 0x55)]))
    if entry == 0x1e6e4:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0xff, 0x100, 0xffffff00, 0x80)]
    if entry == 0x1e70e:
        h += [dict(a6rec=[(0xc, 4, 0x20)], rec=[(0x20 + 0x9e, 1, v)]) for v in (3, 0, 2, 0x83, 0xff, 4)]
    if entry in (0x1e724, 0x1e734):
        for v in (0, 0x80, 0x40, 0xc0, 0x3f, 0xbf, 0x7f, 0xff):
            h.append(dict(regrec=dict(a0=0x20), rec=[(0x20 + 0xa7, 1, v)]))
    if entry == 0x1e744:
        for b7c, w76, w1e, f1e in ((0, 0, 0, 0), (1, 2, 0x8000, 0x8000), (2, 3, 0xffff, 1), (1, 0, 0x1234, 0xedcc), (0, 1, 0x7fff, 0x7fff)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20 + 0x7c, 1, b7c), (0x20 + 0x76, 2, w76), (0x20 + 0x1e, 2, w1e)],
                          a6off=[(0x1e, 2, f1e), (0x32, 2, 0x5555), (0x1d, 1, 0x55), (0x20, 1, 0x55)]))
    # ---- 1e8de .. 1e968 (the state 1e8de -> 1e918 -> 1e92c)
    if entry == 0x1e930:
        h += byte(0xa7, (0, 8, 0xf7, 0xff))
    if entry == 0x1e93e:
        h += [dict(regs=dict(up, d7=v)) for v in (0x17, 0x18, 0x19, 0, 0xffff, 0x10017, 0xffff0018)]
    if entry == 0x1e958:
        h += [dict(regs=dict(up), a6off=[(0x1e, 2, v)]) for v in (0, 0x8000)]
    # ---- 21950 .. 21aaa (the slot-84 states)
    if entry == 0x21972:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x10, 0xffffffef, 0xffffffff, 0x12340010)]
    if entry == 0x21a88:
        h += byte(0x7e, (0, 1, 0x80, 0xff))
    if entry == 0x21a9c:
        h += [dict(regs=dict(up, d7=v)) for v in (0, 0x10000, 1, 0x8000, 0xffff0000)]
    if entry == 0x21a42:
        h += [dict(a6rec=[(0x8c, 4, 0x20)], rec=[(0x24, 1, v)], a6off=[(0xa7, 1, 0xff)]) for v in (0, 1, 18)]
    if entry in LIST_JUMPS:
        h += [dict(regs=dict(a1=v)) for v in LIST_JUMPS[entry]]
    # ---- 49bf2 / 4a90e .. 4a93e / 4d196
    if entry == 0x49bf2:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0xf, 0x10, 0xffff, 0x12345673, 0x8)]
    if entry == 0x4a90e:
        h += [dict(a5off=[(0x7d82, 1, a), (0x7e80, 1, b), (-0x7ffd, 1, c)]) for a, b, c in ((0, 0, 0), (0, 0, 1), (0, 1, 0xff), (1, 1, 0), (0x80, 0xff, 1))]
    if entry == 0x4a91e:
        h += [dict(a5off=[(0x7e80, 1, b), (-0x7ffd, 1, c)]) for b, c in ((1, 0), (0x80, 1), (0xff, 0xff))]
    if entry == 0x4a930:
        h += [dict(regs=dict(up, d0=v), a5off=[(-0x7ffd, 1, c)], regrec=dict(a1=0x20)) for v, c in ((0, 0), (1, 0), (1, 1), (0xffff, 0xff), (2, 1))]
    if entry == 0x4a93e:
        h += [dict(regs=dict(up, d0=v), regrec=dict(a1=0x20), rec=[(0x20, 1, 0x5a), (0x21, 1, 0xa5), (0x1f, 1, 0x3c)]) for v in (0, 1, 0xffff, 0x10001)]
    # ---- 4eb6a .. 4ed34 (the continue entry and the continue-wait callback 4ebe2)
    if entry in (0x4eb6a, 0x4ec50, 0x4ed26):
        h += a5byte(0x5d21, (0, 1, 0x80, 0xff))
    if entry == 0x4eb72:
        h += a5byte(0x7d82, (0, 1, 0xff))
    if entry == 0x4eb8e:
        h += [dict(regs=dict(up, d7=v)) for v in (0, 0x100, 1, 0xff, 0xffffff00)]
    if entry == 0x4ebe2:
        for pl, v in ((0, 3), (1, 3), (0, 1), (1, 1), (0, 2), (1, 0), (0, 0x83), (0xffff, 3)):
            h.append(dict(a6off=[(0x76, 2, pl)], a5off=[(0x7db6 + (pl if pl < 0x8000 else pl - 0x10000), 1, v)]))
    if entry == 0x4ebf4:
        h += [dict(regs=dict(up, d0=v)) for v in (1, 0x101, 0, 2, 0xffffff01)]
    if entry == 0x4ec3c:
        h += [dict(regs=dict(up, d0=d0), a6off=[(0xa2, 1, b)]) for d0, b in ((0, 0), (1, 0), (0, 1), (0xff, 0xfe), (0x7f, 0x80), (0x105, 5), (5, 4))]
    if entry == 0x4ec6a:
        h += [dict(regrec=dict(a0=0x20), rec=[(0x20, 2, v)]) for v in (0, 1, 0x800, 0x7ff, 0x8000, 0x100)]
    if entry == 0x4ec80:
        h += [dict(regs=dict(up, d0=v)) for v in (0x7ff, 0x800, 0x801, 0xffff, 0x107ff, 0)]
    if entry == 0x4ec88:
        h += [dict(a6off=[(0x76, 2, v)]) for v in (0, 1, 0x8000)]
    if entry == 0x4ec9c:
        h += [dict(regrec=dict(a0=0x20), rec=[(0x23, 1, v)]) for v in (0, 0x20, 0xdf, 0xff)]
    if entry == 0x4ecac:
        for pl, bits, f, a in ((0, 0, 0, 0), (0, 1, 0, 1), (1, 2, 5, 5), (1, 0xfd, 1, 2), (9, 2, 0x80, 0x80), (7, 0x80, 3, 4), (8, 0xfe, 0, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x76, 2, pl), (0x9a, 1, a), (0xa1, 1, 0x55)], a5off=[(0x7004, 1, bits), (0x5d1f, 1, f)]))
    if entry == 0x4ecc4:
        h += byte(0xa1, (0, 0xff, 1))
    if entry == 0x4ecd8:
        for a1, f in ((0, 0), (0, 1), (0xff, 0xff), (0xfe, 1), (0x0f, 0xf0), (0x0f, 0x0f)):
            h.append(dict(regs=dict(up), a6off=[(0xa1, 1, a1)], a5off=[(0x5d1f, 1, f)]))
    if entry == 0x4ecec:
        h += [dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 1, v)], a6off=[(0x76, 2, pl), (0x7c, 2, w)]) for v, pl, w in
              ((0, 0, 0), (1, 1, 0x8000), (2, 0, 0xffff), (3, 0x100, 0x1234))]
    # ---- e8c3a .. e8cbc (the appearance helper)
    if entry == 0xe8c40:
        h += [dict(regs=dict(up, d2=0xffff5500), regrec=dict(a0=0x20), rec=[(0x23, 1, v)]) for v in (0, 1, 0x17, 5)]
    if entry == 0xe8c84:
        h += [dict(regs=dict(up), regrec=dict(a0=0x20))]
    if entry == 0xe8ca2:
        h += [dict(regs=dict(up), stack=[(0, 4, 0x10e920), (4, 2, 0x8001)], regrec=dict(a0=0x20))]
    if entry == 0xe8cbc:
        h += [dict(regs=dict(up), stack=[(0, 4, v), (4, 4, SENTINEL)]) for v in (0x10e920, 0x1fe000)]
    return h


# chain hints: let the real producers return both C values and the Z source both values
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry in (0x1d5c4, 0x1d5fc):
        # 49c38: TST.L 5734(A5) + 4 x (D0.W & 1) with D0.W = WORD 78(A6): 0 -> Clear, else Set
        pl = t % 2
        return dict(a6off=[(0x78, 2, pl)], a5off=[(0x5734 + 4 * pl, 4, (0, 0x10e900, 0x80000000, 1)[(t // 2) % 4])])
    if entry == 0x1d76a:
        # 4836e: BTST.B #2,5683(A5): clear -> Set, set -> Clear
        return dict(a5off=[(0x5683, 1, (0, 4, 0xfb, 0xff)[t % 4])])
    if entry in (0x1d8f6, 0x1db98):
        # 1d510 / 1d508 -> 1d514: CMPI.W #14,D1: D1.W >= 14 -> Clear (RTS 1d51c); < 14 -> 1d51e .. (481b2, 1aa3a, the ROM LONG table 1d468 / 1d4b8)
        return dict(regs=dict(d1=(0x14, 0x15, 0xffff, 0, 9, 3, 0x13, 0x10014)[t % 8]))
    if entry in (0x21960, 0x21a76):
        # 215e6 on the ROM lists 21930 (keys 0 a) / 216c8 (key 0): key BYTE 9c -> Set (A1 the handler); else Clear
        return dict(a6off=[(0x9c, 1, (0, 0xa, 1, 2, 0xff, 0)[t % 6])])
    if entry == 0xe8c40:
        # 2986 (C7 / FR11): a free node -> Set; the record BYTE 3 indexes the ROM BYTE table e8c22 (24 entries)
        return dict(regrec=dict(a0=0x20), rec=[(0x23, 1, t % 24)])
    if entry == 0x4eb7a:
        # 4a974: BYTE 10fd82 = 0 -> A0 := 100004 (+ D0.W & 1 when BYTE 100003 is not 0); TST.B (A0)
        pl = t % 2
        return dict(a6off=[(0x76, 2, pl)], writes=[(0xfd82, 1, 0), (0x0003, 1, (0, 0xff)[(t // 2) % 2]), (0x0004, 1, (0, 1, 0x80)[(t // 4) % 3]),
                                                    (0x0005, 1, (0, 2, 0)[(t // 3) % 3])])
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
        missing -= set(t for c, t in MODEL_GATED if c == cons)
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
    """Frame-start states of one run of the third IO observation IO_EXT2 (read-only): {frame: state} decoded with
    observe_animation_machine_io.read_pack (the observation's state packs; this spec's own reader, the shared loader is unchanged)."""
    key = (cfg, case)
    if key not in _PACKS:
        import observe_animation_machine_io as O
        path = ROOT / IO_EXT2 / 'states' / cfg / ('%03d.pack.gz' % case)
        _PACKS[key] = dict((fr, st) for fr, st, dg in O.read_pack(gzip.decompress(path.read_bytes())))
    return _PACKS[key]


def natural_fixtures(add, record):
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a NATURAL frame in which a node of the area POOL holds one of NATURAL_CALLBACKS
    as its callback LONG, or a player node (NATURAL_NODES) holds one of NATURAL_SLOTS as its slot-84 LONG 84(A6) with a routed callback LONG, or any
    routed callback LONG (NATURAL_PLAYER_ANY: the frames in which the observation first records a C11 start); declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the frame
    start.  Up to the sentinel or the first unrouted PC; kept when the run executes a C11 start."""
    count = 0
    seen = set()
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        nodes = []
        for a in range(POOL[0] & 0xffff, POOL[1] & 0xffff, 2):
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if cb in NATURAL_CALLBACKS:
                nodes.append(0x100000 + a)
        for node in NATURAL_NODES:
            a = node & 0xffff
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            sl = struct.unpack('>I', ram[a + 0x84:a + 0x88])[0]
            if unit_of(cb) is not None and (sl in NATURAL_SLOTS or NATURAL_PLAYER_ANY):
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
                continue                                    # the run does not reach C11 code
            record(tr['pcs'] + [tr['stop']])
            sl = struct.unpack('>I', ram[a + 0x84:a + 0x88])[0]
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
    err('odd-pc', U.with_host_writes(st, pc=0x1e5ab), 'unaligned animation machine PC', 0x1e5ab)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    device = 'unsupported animation machine write device'
    # the JMP (A1) 21a82 (contract decision 2): A1 outside the list 216c8 (compared as a LONG)
    for v in (0x21d60, 0x21e48, 0, 0x21603, 0x1021602, 0x2197e):
        err('21a82-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21a82), ERROR_JUMP, 0x21a82)
    # the Z source of 4eb84 (contract decision 3): A0 outside the four BYTEs 10fdb0 10fdb1 100004 100005 that 4a974 tests
    for v in (0x100003, 0x100006, 0x10fdb2, 0x10e000, 0x200004, 0x300000):
        err('4eb84-a0-%x' % v, U.with_host_writes(st, regs=dict(a0=v), pc=0x4eb84), ERROR_FLAG, 0x4eb84)
    # odd node / stack: the entry block fails (the row's stop is the PC right after the failing block)
    err('ca64-odd-a5', U.with_host_writes(st, regs=dict(a5=a5 + 1), pc=0xca64), odd_write, 0xca64)
    err('1d9b8-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1d9b8), odd_word, 0x1d9b8, stop=0x1d9cc)
    err('1e67a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1e67a), odd_write, 0x1e67a, stop=0x49290)
    err('1e8f4-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1e8f4), odd_write, 0x1e8f4, stop=0x1e918)
    err('1e5d8-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1e5d8), odd_write, 0x1e5d8, stop=0x4c2c4)
    err('4ebe2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x4ebe2), odd_word, 0x4ebe2, stop=0x4ebf4)
    err('1e606-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1e606), odd_word, 0x1e606)
    err('4ed34-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4ed34), odd_word, 0x4ed34)
    err('e8cbc-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe8cbc), odd_word, 0xe8cbc)
    err('e8c7c-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe8c7c), odd_word, 0xe8c7c, stop=0xe8ca2)
    err('1e8f4-rom-node', U.with_host_writes(st, regs=dict(a6=0x1b000), pc=0x1e8f4), device, 0x1e8f4, stop=0x1e918)
    # failures after executed blocks: 1d3e0 (D7.W = 16) .. 1d430 -> 1d746 (JSR 48296 at an odd A7); 4ebf4 (D0.B = 2) -> 4ec32 (JSR 4a90e at an odd A7);
    # 1db7c (WORD 88 = 5) -> the RTS 1db84 at an odd A7; 1e600 -> 1e606 at an odd A7; 21a88 (BYTE 7e = 0) -> 21a98 at an odd A7
    err('1d3e0-then-1d746', U.with_host_writes(st, regs=dict(a7=a7 + 1, d7=0x16), pc=0x1d3e0), odd_word, 0x1d746)
    err('4ebf4-then-4ec32', U.with_host_writes(st, regs=dict(a7=a7 + 1, d0=2), pc=0x4ebf4), odd_word, 0x4ec32)
    err('1db7c-then-1db84', U.with_host_writes(st, [((a6 + 0x88) & 0xffff, 2, 5)], regs=dict(a7=a7 + 1), pc=0x1db7c), odd_word, 0x1db84)
    err('1e600-then-1e606', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1e600), odd_word, 0x1e606)
    err('21a88-then-21a98', U.with_host_writes(st, [((a6 + 0x7e) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x21a88), odd_word, 0x21a98)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x1e5ba, 0x1e6ce, 0x4ecac, 0x1cb76)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
