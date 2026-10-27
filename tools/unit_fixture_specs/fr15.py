"""V1 fixture spec of the area-D unit FR15 (engine/src/animation_machine_objects_fr15.cpp, 192 block starts; file prefix fr15 / objects_fr15).

Blocks (contract docs/analysis/animation-machine-objects-fr15-contract.md, plan docs/analysis/area-c-completion-plan.md section 11.5 unit D-1): the
2986 callback 3ff14 -> 3ff4c (40964, 40a1c, the player node of WORD 8a, 40b60 with 4d418 / the pass RTS 40b7a, 4d508) -> 4076a / 40812 .. 40872 (4b54e,
4d766, 409e6 / 40a0a script WORDs), the 28ae children 40896 -> 408c0 (288c, 491c4) and the helper 40a5a (8ebe x 3, 4d81c, 28ae children 41fe6 /
40896), the script callbacks 40bc8 / 6f282 / 6f352, 4c2c4, the 2986 child b3dfc, the circle plotter 4fdfc / 4fe50 (VRAM port LONG 3c0000) with 4fea4
/ 4fec6 and the callback 4ff4c -> 4ff5c, the FR1 kind handler c13c0 -> c142a / c14d8 (MULU.W #8 sectors, the bundled BEQ c1540), the 2986 child e9b8a
-> e9b9a (JMP e9c72(PC,D0.W) entry 3 e9c7e) -> ea132 -> ea14c (ea2ca C, the BYTE 8f loops, ea2c6 .. ea334).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR14, C1..C11) with declared host edits.
This code runs natively only in the third IO observation (tools/observe_animation_machine_io_ext2.py, runs M1.5 M3.1 M4.0 D2 G1.94 G1.68): the
'natural' family takes the frame-start states of that observation (state packs, read-only; directory IO_EXT2 below, its compared_sha256 pinned) in which
a node holds an FR15 node entry or install as its callback LONG ('cb'), or the exact-bitmap re-observation first records an FR15 start in that frame
('any': every node of the pool with a routed callback LONG); it keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = the
node, A7 = 10ef00 with the sentinel return LONG, PC = the callback).  The spec reads those packs itself (io_pack below); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 8 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the installed values and child callbacks (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers entered as subroutines of other units and the script callbacks (return LONG = sentinel).
  error     every even non-start PC of the unit ranges (the bundled BEQ c1540 included), an odd PC, Unknown C at the 8 consumers, the jump-target guard
            of JMP e9c72(PC,D0.W) (decision 2), odd node / stack, failures after executed blocks: checked error, state preserved, every row with its
            failing PC (a paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR14, C1..C11
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR14, C1..C11)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'fr15'
ERROR_PC = 'unsupported animation objects fr15 PC'
ERROR_CARRY = 'objects fr15 caller requires known carry'
ERROR_JUMP = 'unsupported animation objects fr15 jump target'
# The third IO observation (read-only state packs of the natural family; area-C plan 11.3).  Until it is moved to the shared artifacts (plan 11.7
# decision 1) it lives in the scratch directory; MS5_IO_EXT2 overrides the directory.  Its compared_sha256 is pinned (build() checks it), so every
# location gives the same states.
IO_EXT2_COMPARED = 'd30e68d6b8c7f69181be12b00f017c4eafccb705416af7e8beea02b6d9595673'
IO_EXT2 = os.environ.get('MS5_IO_EXT2') or ('artifacts/animation_machine_io_ext2' if (ROOT / 'artifacts/animation_machine_io_ext2').is_dir() else
                                            '/Users/start/Workspce/ms5-scratch/obs3/final')

RANGES = [(0x3ff14, 0x3ffa0), (0x4076a, 0x4076e), (0x40812, 0x4083c), (0x40846, 0x40884), (0x4088e, 0x40890), (0x40896, 0x408da), (0x4095e, 0x40978),
          (0x409e6, 0x40a06), (0x40a0a, 0x40a2e), (0x40a5a, 0x40b12), (0x40b60, 0x40b7c), (0x40bc8, 0x40bce), (0x4c2c4, 0x4c2cc), (0x4fdfc, 0x4fe8a),
          (0x4fea4, 0x4ff12), (0x4ff4c, 0x4ff96), (0x6f282, 0x6f296), (0x6f352, 0x6f360), (0xb3dfc, 0xb3e1c), (0xc13c0, 0xc1560), (0xe9b8a, 0xe9b92),
          (0xe9b9a, 0xe9c72), (0xe9c7e, 0xe9c82), (0xea132, 0xea1ca), (0xea1d0, 0xea1d8), (0xea2be, 0xea2c0), (0xea2c6, 0xea34a)]
STARTS = sorted(int(x, 16) for x in (
    '3ff14 3ff24 3ff46 3ff4c 3ff50 3ff54 3ff5c 3ff64 3ff68 3ff74 3ff78 3ff7c 3ff96 3ff9c 4076a 40812 40818 40824 4082a 40846 4084c 40850 40856 '
    '4085e 40868 40872 4088e 40896 408ba 408c0 408c6 408ca 408d0 408d8 4095e 40964 40972 409e6 409f0 409fa 40a0a 40a0e 40a1c 40a26 40a2c 40a5a '
    '40a76 40a84 40a92 40aa6 40ab8 40ac8 40acc 40af6 40b06 40b0a 40b60 40b6e 40b72 40b7a 40bc8 4c2c4 4c2c8 4fdfc 4fe04 4fe0a 4fe0e 4fe14 4fe1a '
    '4fe20 4fe26 4fe2c 4fe32 4fe38 4fe40 4fe48 4fe4c 4fe4e 4fe50 4fe60 4fe74 4fe86 4fea4 4feae 4feb6 4febc 4fec4 4fec6 4fee8 4feea 4fef6 4fef8 '
    '4ff02 4ff04 4ff4c 4ff50 4ff5c 4ff64 4ff74 4ff7e 4ff84 6f282 6f352 6f358 6f35e b3dfc b3e08 b3e14 b3e18 c13c0 c13d6 c13e8 c13ee c13f2 c13f8 '
    'c141e c142a c1430 c143a c1450 c145a c1462 c146c c147c c1492 c149c c14ac c14b2 c14ba c14c0 c14c2 c14d2 c14d8 c14de c14e8 c14f2 c1502 c1518 '
    'c1522 c1536 c1544 c154a c1550 c1558 c155e e9b8a e9b9a e9bae e9bdc e9be6 e9bf2 e9bfa e9c0a e9c16 e9c1c e9c2a e9c30 e9c40 e9c46 e9c52 e9c58 '
    'e9c5e e9c64 e9c7e ea132 ea13c ea14c ea150 ea154 ea158 ea162 ea166 ea172 ea182 ea192 ea19e ea1b0 ea1b4 ea1bc ea1c2 ea1d0 ea2be ea2c6 ea2ca '
    'ea2e0 ea2e6 ea2fe ea314 ea328 ea330 ea332 ea334').split())
# the 8 C consumers: BCC 3ff78 (40b60: 4d418 Clear through 40b6e -> the RTS 40b7a, or 40b72 ORI Set), BCC 4084c (4d766), BCC 408c6 (288c), BCC 40ac8
# 40b06 (28ae), BCC 40b6e (4d418), BCC c13ee (b4304), BCS ea150 (ea2ca: CMP.W, a producer of this unit)
CONSUMERS = (0x3ff78, 0x4084c, 0x408c6, 0x40ac8, 0x40b06, 0x40b6e, 0xc13ee, 0xea150)
CLEAR_SET = ()
SET_SET = (0x40b72, 0x40acc)            # ORI.B #1,CCR (40b72 into the pass block 40b7a; 40acc without a reader)
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0xea2ca,)                   # CMP.W (A0,D1.W),D0; RTS: the C of the compare (read by ea150)
INVERT_SET = ()
PASS_SET = (0x40b7a,)                   # RTS that passes the C of 40b6e (Clear) / 40b72 (Set) to 3ff78
STARTS_SET = set()
Z_READERS = ()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
# Branch outcomes that no V1 world takes (each is checked by the unit test with declared state):
#   40ac8 BCC.W 40af6 / 40b06 BCC.W 40890: the Clear side is the 28ae failure (no free node); the seed worlds always have a free node.
MODEL_GATED = set()
TRAPS = ()
# Declared stops of the native runs: the FR15 later-unit stops (UNIT_EXITS: D-2 4083c 40884 408da ea1ca ea2c0, D-3 40890 40978 6f360) and the still
# unrouted declared stops of the earlier specs that the FR15 runs may pass through (C11 and earlier; scratch union), the written-only callbacks.
UNIT_EXITS = (0x4083c, 0x40884, 0x40890, 0x408da, 0x40978, 0x6f360, 0xea1ca, 0xea2c0)
EXIT_STOPS = UNIT_EXITS + (0xca5c, 0x1d438, 0x1d776, 0x1d940, 0x1db0a, 0x1dbf0, 0x1e648, 0x1e71e, 0x1e96c, 0x2196c, 0x21a90, 0x21aa2, 0x4ebfc,
                           0x1de3c, 0x1e21c, 0x1fc96, 0x1fd3c, 0x1fd50, 0x21ea0, 0x21fa6, 0x4e69a, 0x4ef08, 0x4002c, 0x405e2)
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x3ff74, 0x3ff78), (0x40846, 0x4084c), (0x408c0, 0x408c6), (0x40ab8, 0x40ac8), (0x40af6, 0x40b06), (0x40b60, 0x40b6e),
          (0xc13e8, 0xc13ee), (0xea14c, 0xea150))
PASS_CHAINS = ()
# the computed jump JMP e9c72(PC,D0.W) of the block e9c64 (contract decision 2): D0.W = 4 x BYTE 90(A6); the executed entry 3 e9c7e (BYTE 90 = 3,
# written by e9b8a) is the only transcribed table entry; any other index is the C++ checked jump-target error (a native run elsewhere is not a world)
TABLE_JUMPS = {0xe9c64: (0xe9c7e,)}
JUMP_PCS = (0xe9c6e,)
JUMP_TABLE = (0xe9c7e,)
JUMP_ROUTED = ()
LIST_JUMPS = {}
# computed jumps that the FR15 runs reach (fr14 OTHER_JUMP_PCS with the interpreter callbacks 4a352 / 4a43c, C11 21a82, the FR15 e9c6e): an unrouted
# target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0xcc8da, 0xb4034, 0xb42b4, 0xc54ae, 0xb3dc8, 0xb3f3e, 0xb3fc4, 0xb3fca, 0xb46aa, 0xcc7a8, 0xcc82a, 0x4a352, 0x4a43c, 0x2031c,
                  0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36, 0x2224c,
                  0x22428, 0x21e10, 0x2229a, 0x22378, 0x203ac, 0x21a82, 0xe9c6e)
TABLE_ENTRIES = ()
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92, 0x21e6a, 0x21cd8, 0x21d2a, 0x2210c, 0x22128, 0x22240, 0x2241c, 0x22452,
             0x21e04, 0x2228e, 0x22360, 0x21960, 0x21a76)
# installed values and child callbacks entered as node callbacks: 3ff14 (the 2986 child callback of C11 3fef4), 3ff4c (3ff46), 40896 (the 28ae child
# of 40af6), 408c0 (408ba), 4ff4c (the 28ae child of stage catalog 47964), 4ff5c (4ff56), b3dfc (the 2986 child of C11 e8c66), c142a (c1424), c14d8
# (c14d2), e9b8a (the 2986 child of FR2 e9b5c), ea14c (ea146), the kind handler c13c0 (FR1 record b35ce: entered with the item node as a callback);
# the callee entries (subroutines of other units and the script callbacks of the interpreter table 4a500)
NODE_ENTRIES = (0x3ff14, 0x3ff4c, 0x40896, 0x408c0, 0x4ff4c, 0x4ff5c, 0xb3dfc, 0xc142a, 0xc14d8, 0xe9b8a, 0xea14c, 0xc13c0)
CALLEES = (0x40964, 0x409e6, 0x40a1c, 0x40a5a, 0x40b60, 0x40bc8, 0x4c2c4, 0x4fdfc, 0x4fe50, 0x4fea4, 0x4fec6, 0x6f282, 0x6f352, 0xea2c6, 0xea2ca,
           0xea2e0, 0xea2fe, 0xea314, 0xea334, 0x4076a, 0x40812, 0xe9b9a, 0xea13c, 0xc141e)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x76, 0x7e, 0x84, 0x8c, 0x94, 0xa2, 0xb2)   # node links, pointer fields: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
# natural worlds of the third observation: (config, case, frame, mode) (scratch natscan_fr15.py -> natural_fr15.json: 'cb' = per run and key the first,
# a middle and the last frame of the callbacks 3ff14 3ff4c 40896 408c0 4ff4c 4ff5c b3dfc e9b8a ea14c c142a c14d8; 'any' = the frames in which the
# exact-bitmap re-observation at the C11 routing first records an FR15 start: every node of the frame is tried)
NATURAL = tuple(tuple(x) for x in (
    ('D2', 94, 553, 'any'), ('D2', 94, 554, 'any'), ('D2', 94, 558, 'any'), ('D2', 94, 560, 'any'), ('D2', 94, 561, 'any'), ('D2', 94, 579, 'cb'),
    ('D2', 94, 581, 'any'), ('D2', 94, 583, 'cb'), ('D2', 94, 587, 'any'), ('D2', 94, 588, 'any'), ('D2', 94, 591, 'any'), ('D2', 94, 600, 'cb'),
    ('D2', 94, 607, 'any'), ('D2', 94, 611, 'cb'), ('D2', 94, 1471, 'cb'), ('D2', 94, 1483, 'cb'), ('G1.68', 68, 960, 'any'),
    ('G1.68', 68, 1678, 'any'), ('G1.68', 68, 1679, 'any'), ('G1.68', 68, 1680, 'any'), ('G1.68', 68, 1692, 'cb'), ('G1.68', 68, 1698, 'any'),
    ('G1.68', 68, 1700, 'cb'), ('G1.68', 68, 1702, 'cb'), ('G1.68', 68, 1724, 'cb'), ('G1.94', 94, 768, 'any'), ('G1.94', 94, 1298, 'any'),
    ('G1.94', 94, 1299, 'any'), ('G1.94', 94, 1304, 'any'), ('G1.94', 94, 1318, 'any'), ('G1.94', 94, 1427, 'any'), ('G1.94', 94, 1428, 'any'),
    ('G1.94', 94, 1433, 'any'), ('G1.94', 94, 1435, 'cb'), ('G1.94', 94, 1442, 'any'), ('G1.94', 94, 1489, 'cb'), ('G1.94', 94, 1495, 'cb'),
    ('G1.94', 94, 1504, 'cb'), ('G1.94', 94, 1528, 'cb'), ('M1.5', 94, 190, 'any'), ('M3.1', 94, 225, 'any'), ('M3.1', 94, 226, 'any'),
    ('M3.1', 94, 236, 'cb'), ('M3.1', 94, 245, 'any'), ('M3.1', 94, 246, 'any'), ('M3.1', 94, 261, 'any'), ('M4.0', 94, 193, 'any'),
    ('M4.0', 94, 194, 'any'), ('M4.0', 94, 195, 'any'), ('M4.0', 94, 222, 'cb'), ('M4.0', 94, 248, 'any'), ('M4.0', 94, 257, 'any'),
    ('M4.0', 94, 415, 'any'), ('M4.0', 94, 512, 'cb'), ('M4.0', 94, 828, 'cb'),))
NATURAL_CALLBACKS = (0x3ff14, 0x3ff4c, 0x40896, 0x408c0, 0x4ff4c, 0x4ff5c, 0xb3dfc, 0xe9b8a, 0xea14c, 0xc142a, 0xc14d8)
NATURAL_STRIDE = 0xc4                   # the node stride of the pool 1009a8 + c4 k (the 'any' frames: every node with a routed callback LONG)
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
# the flag-sharing BEQ pair of the block c1536: CMPI.B #1,b6(A6); BEQ c1540; BEQ c0944 (the later BEQ c1540 is not a block start).  The earlier BEQ
# c1522 (-> c1540, Z set) and c1536 jump to the later BEQ with Z set: it is always taken (THREAD: c1540 -> c0944, FR12), so the native trace passes the
# non-start PC c1540 inside the block (FR12 c113a / c11ec).
BUNDLED = (0xc1540,)
THREAD = {0xc1540: 0xc0944}


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
        out = {THREAD.get(target(op), target(op)), a + size}
        for b, bmn, bop, bsize, _ in instrs[:-1]:
            if BCC.match(bmn) and b + bsize in BUNDLED:
                out.add(THREAD.get(target(bop), target(bop)))          # the earlier Bcc of a bundled pair
        return out
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op and '(a' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr', 'jmp'):
        return None
    return {a + size}


def block_next(entry, n, tr):
    """The PC after the entry block: the first traced PC that leaves the straight-line instruction sequence of the block (pcs[n] for a block run to
    its end; an earlier PC when a Bcc of a bundled chain is taken), or the stop."""
    pcs = tr['pcs'] + [tr['stop']]
    addrs = [x[0] for x in block_instrs(entry)]
    i = 1
    while i < len(pcs) - 1 and i < len(addrs) and pcs[i] == addrs[i]:
        i += 1
    while i < len(pcs) - 1 and pcs[i] in THREAD:
        i += 1
    return pcs[i] if i < len(pcs) else tr['stop']


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
            return None                                 # the computed table jump e9c6e beyond its transcribed entry (decision 2)
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
        if pc in STARTS_SET or (pc in THREAD and target(decode(prev).op_str) == pc):
            return False
        ins = decode(prev)
        return pc != prev + (ins.size if ins is not None else size)
    return outside


def first_unrouted(extra=()):
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at an unrouted target of the
    computed jumps that the FR15 runs reach (OTHER_JUMP_PCS: FR1 / FR4 / FR11 / FR13, C3 .. C11, the interpreter and FR15 e9c6e), or at the first unrouted
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
        # FR15 (the ROM writers keep these in range): WORD 88(A6) 0..2 (the index of the 3 LONGs ea3ac of e9bae and of the WORDs 5e4a(A5) of ea2ca),
        # BYTE 8f(A6) 0..4 (the counts of the e9bf2 / ea162 loops), BYTE 90(A6) = 3 mostly (the e9c72 table index), LONG 7e(A6) = the ROM record ea3cc
        # (ea3c4 entry 0) with the BYTE indices 76.. (e9b9a .. ea334); otherwise LONG 76(A6) = the declared script record (409e6: the WORD list); D2.W
        # small for the circle plotter (4fdfc / 4fea4), D0 / D1 fix cells near the screen
        if rng.random() < 0.9:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe: BYTE 1d(A6) < 4 (else the TRAP #15 of 8ec8)
        if entry == 0xe9b9a and rng.random() < 0.9:
            regs['d0'] = (regs['d0'] & 0xffffff00) | 3              # the BYTE 90 of the only transcribed e9c72 entry (e9b8a writes 3)
        if 0xe9b8a <= entry < 0xea34a:
            writes.append(((a6 + 0x88) & 0xffff, 2, rng.choice((0, 1, 2))))
            writes.append(((a6 + 0x8f) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4))))
            writes.append(((a6 + 0x90) & 0xffff, 1, rng.choice((3, 3, 3, 3, 0, 4))))
            writes.append(((a6 + 0x7e) & 0xffff, 4, 0xea3cc if rng.random() < 0.9 else 0xea4ce))
            for k in range(8):
                writes.append(((a6 + 0x76 + k) & 0xffff, 1, rng.choice((0, 1, 2, 3, 4, 5, 8, 0xa, 0x10))))
        else:
            writes.append(((a6 + 0x76) & 0xffff, 4, rec + 0x40 if rng.random() < 0.8 else 0))
            for k in range(0, 0x20, 2):
                writes.append(((rec + 0x40 + k) & 0xffff, 2, rng.choice((0, 1, 2, 0x10, 0x7fff, 0xffff, 0xfffe, 0xfffd, 0xfffc, 0x8000, 4, 6))))
        if 0xc13c0 <= entry < 0xc1560:
            # b4030 (FR11): JMP (A0) b4034 with A0 = LONG 76(A6): only the FR11 decision-2 handlers (the C++ checked jump-target error otherwise)
            writes.append(((a6 + 0x76) & 0xffff, 4, rng.choice((0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924, 0xb4036))))
        if 0x4fdfc <= entry < 0x4ff96 and rng.random() < 0.9:
            regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 5, 8, 0xd, 0xe, 0x10, 0x14, 0x20, 0xffff, 0x8000))
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1, 0x10, 0x13, 0x25, 0x26, 0xffff, 0x27))
            regs['d1'] = (regs['d1'] & 0xffff0000) | rng.choice((0, 1, 0xe, 0x1d, 0x1e, 0xffff, 0x1f))
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
    require(len(STARTS) == 192 and len(STARTS_SET) == 192, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr15_block', ('start is not routed to objects fr15', hex(s), unit_of(s)))
    for t in THREAD:
        require(mine(t) and t not in STARTS_SET and unit_of(THREAD[t]) is not None, ('bundled BEQ inside an FR15 block', hex(t)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            require(unit_of(pc) == 'animation_objects_fr15_block', ('range PC not routed to FR15', hex(pc)))
    for jmp, handlers in LIST_JUMPS.items():
        require(mine(jmp) and jmp in STARTS, ('JMP (A1) block', hex(jmp)))
        for t in handlers:
            require(unit_of(t) is not None, ('list handler must be routed', hex(t)))
    # the transcribed table entry e9c7e is an FR15 start; the other table entries e9c72 e9c76 e9c7a e9c82 stay unrouted; the third observation is
    # the pinned one (IO_EXT2)
    require(unit_of(0xe9c7e) == 'animation_objects_fr15_block' and all(unit_of(t) is None for t in (0xe9c72, 0xe9c76, 0xe9c7a, 0xe9c82)),
            'the e9c72 table entries')
    obs = json.loads((ROOT / IO_EXT2 / 'observation.json').read_text())
    require(obs.get('compared_sha256') == IO_EXT2_COMPARED, ('third IO observation pin', IO_EXT2, obs.get('compared_sha256')))
    rng = random.Random(0xF15A)
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
    sys.stderr.write('fr15 spec: %d fixtures (%d natural), visited %d/192, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr15: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr15: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (WORD 8a of 3ff54 / the
    signed WORD 2e compare of 3ff68 against the player node; BYTE 61 bit 7 / SNE of 40818; the AND.B / WORD 84 of 4082a and its bit 0 at 40872; LONG 76
    of 40856; BYTE 92(A0) of 408d0; BYTE 15 bit 7 of 40964; the script WORD list of 409e6 / 409f0 / 409fa / 40a0a (negative 1..3, 4.., positive, the
    ADDA.W offset); the circle compares of 4fdfc .. 4fe74 (D4 / D5 / D6, the columns 0..25 and rows 0..1d with their WORD wrap); the loop counter of
    4feae / 4febc; the ASR / NEG / EXG of 4fec6 .. 4ff04; WORD 7a of 4ff5c / 4ff74; the script WORDs of 6f282 / 6f358; D0.B & c0 of b3e08; the ROR / SMI
    / EOR of c13f8, the BYTE 15 bits 7 / 0, LSR.W b0, the steer / mirror and the MULU sectors of c1430 .. c1550 (D0 bit 2); BYTE 8f and the WORDs 42 / 46
    with D7 of e9bf2 .. e9c46; the stack WORD / D6 / BYTEs 92 / 93 / D1 of ea166 .. ea1c2; the WORD 8a + 4 compare of ea2ca), the upper register bits,
    the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    ffnode = dict(a6off=[(off, 1, 0xff) for off in (0x14, 0x15, 0x19, 0x1a, 0x1b, 0x5e, 0x61, 0x62, 0x7a, 0x7b, 0x7c, 0x7d, 0x7f, 0x8e, 0x92, 0x93,
                                                    0x97, 0x98, 0x9b, 0xb6)] +
                  [(off, 2, 0xffff) for off in (0x1e, 0x20, 0x2e, 0x32, 0x42, 0x46, 0x54, 0x68, 0x84, 0x86, 0x8a, 0x8c, 0xa4, 0xb0, 0xb2, 0xb4)])
    if entry in (0x3ff7c, 0x40818, 0x40872, 0x409f0, 0x40a0a, 0x40a0e, 0x40aa6, 0x4fdfc, 0x4fe0e, 0x4fe20, 0x4fe38, 0x4fe50, 0x4fe60, 0x4fe74,
                 0x4fe86, 0x4fea4, 0x4fec6, 0x4feea, 0x4fef8, 0x4ff04, 0x4ff84, 0x6f282, 0x6f358, 0xb3e08, 0xc13f8, 0xc143a, 0xc149c, 0xc1522, 0xe9bae,
                 0xe9bfa, 0xe9c0a, 0xe9c1c, 0xea166, 0xea19e, 0xea1b4, 0xea2ca, 0xea2e6, 0xea2fe, 0xea314, 0xea334, 0xe9b9a, 0xea172, 0xea182):
        h += [dict(regs=dict(up))]
    if entry in (0x3ff24, 0x3ff7c, 0x40896, 0x40a5a, 0x40a92, 0x40aa6, 0x40acc, 0x40b0a, 0x40b72, 0x4082a, 0x40850, 0x40868, 0x4085e, 0x40872,
                 0x40964, 0x409fa, 0x40a0e, 0x40bc8, 0x4fec6, 0x4ff50, 0x4ff64, 0x4ff74, 0x4ff7e, 0x6f282, 0xb3dfc, 0xc13c0, 0xc13f8, 0xc141e, 0xc143a,
                 0xc145a, 0xc146c, 0xc147c, 0xc149c, 0xc14c2, 0xc14f2, 0xc1502, 0xc1522, 0xe9b9a, 0xe9bae, 0xe9c16, 0xe9c30, 0xea132, 0xea13c,
                 0xea158, 0xea182, 0xea192, 0xea19e, 0xea1d0, 0xea2e6, 0xea2fe, 0xea334, 0x3ff46, 0x408ba, 0x4ff4c, 0xc14d2, 0x3ff96, 0x40824):
        h += [dict(ffnode)] + mirror
    # ---- 3ff14 .. 40b7a
    if entry == 0x3ff54:
        h += word(0x8a, (0, 1, 0x8000, 0x100))
    if entry in (0x3ff5c, 0x3ff64, 0x3ff68):
        node = 0x100cb8 if entry != 0x3ff64 else 0x100da8
        for a, b in ((0, 0), (1, 0), (0, 1), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0), (0, 0xffff), (0x1234, 0x1235)):
            h.append(dict(regs=dict(up, a0=node), a6off=[(0x2e, 2, b)], writes=[((node + 0x2e) & 0xffff, 2, a)]))
    if entry == 0x40818:
        h += byte(0x61, (0, 0x80, 0x7f, 0xff, 0x40))
    if entry == 0x4082a:
        for d0, b5e, w84 in ((0xff, 0x5a, 0), (0, 0xff, 1), (0x12345600, 0x81, 0x8000), (0xffffffff, 0xc3, 0x100), (0x0f, 0xff, 0xffff)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x5e, 1, b5e), (0x84, 2, w84), (0x61, 1, 0xff)]))
    if entry == 0x40856:
        h += [dict(a6off=[(0x76, 4, v)]) for v in (0, 1, 0x80000000, 0x10e960)]
    if entry == 0x40872:
        h += [dict(regs=dict(up), a6off=[(0x84, 2, v), (0x1b, 1, 0x5a)]) for v in (0, 1, 2, 3, 0xffff, 0x8000)]
    if entry == 0x408d0:
        h += [dict(regrec=dict(a0=0x20), rec=[(0x20 + 0x92, 1, v)]) for v in (0, 0x7f, 0x80, 0xff)]
    if entry == 0x40964:
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry in (0x409e6, 0x4085e):
        for w, w2 in ((0xffff, 0), (0xfffd, 0), (0xfffc, 4), (0x8000, 2), (0, 0), (0x7fff, 0), (0xfffe, 0), (0xfffb, 0xfffc)):
            h.append(dict(regs=dict(up), a6rec=[(0x76, 4, 0x40)], rec=[(0x40, 2, w), (0x42, 2, w2), (0x44, 2, 0x1234), (0x3e, 2, 0x4321)],
                          a6off=[(0x19, 1, 1), (0x1a, 1, 2), (0x1b, 1, 3), (0x1c, 1, 4), (0x14, 1, 0xff)]))
    if entry == 0x409f0:
        h += [dict(regs=dict(up, d1=v), regrec=dict(a0=0x40), a6off=[(0x19, 1, 1), (0x1a, 1, 2), (0x1b, 1, 3), (0x1c, 1, 4)])
              for v in (0xffff, 0xfffd, 0xfffc, 0, 0x8000, 0x12340001, 0xfffe)]
    if entry == 0x409fa:
        h += [dict(regs=dict(up, d1=v), regrec=dict(a0=0x40), a6off=[(0x19, 1, 1), (0x1a, 1, 2), (0x1b, 1, 3), (0x1c, 1, 4)]) for v in (0, 1, 2, 3, 0x10003)]
    if entry == 0x40a0a:
        for off, w in ((4, 0x55), (0xfffe, 0x66), (0, 0x77), (8, 0x8000), (0x10, 0xffff)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x40), rec=[(0x40, 2, off), (0x40 + (off if off < 0x8000 else off - 0x10000), 2, off),
                                                                    (0x42, 2, w), (0x44, 2, w), (0x48, 2, w), (0x50, 2, w), (0x3e, 2, w)]))
    if entry == 0x40a0e:
        h += [dict(regs=dict(up), regrec=dict(a0=v), a6off=[(0x14, 1, b)]) for v, b in ((0x40, 0), (0x42, 0x80), (0x44, 0xff))]
    if entry in (0x3ff7c, 0x40aa6):
        h += [dict(regs=dict(up, d1=d1, d2=d2, d3=d3)) for d1, d2, d3 in ((0, 0, 0), (0xff, 0x80, 0x8000), (0x12345601, 0x7f, 0xffff))]
    if entry == 0x40acc:
        h += [dict(regs=dict(up), regrec=dict(a0=0x20))]
    if entry == 0x40b72:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0xffff, 0x12348000)]
    if entry == 0x40bc8:
        h += [dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 2, v)]) for v in (0, 0x8000, 0xffff, 0x1234)]
    # ---- 4fdfc .. 4ff84 (the circle plotter and its callback)
    if entry == 0x4fdfc:
        for d0, d1, d2 in ((0x10, 0xe, 0), (0x10, 0xe, 1), (0x10, 0xe, 3), (0, 0, 4), (0x25, 0x1d, 2), (0x12340013, 0x5678000e, 0x9abc0005),
                           (0xffff, 0xffff, 1), (0x26, 0x1e, 1), (0x13, 0xf, 0xd)):
            h.append(dict(regs=dict(up, d0=d0, d1=d1, d2=d2, d3=0x4567)))
    if entry == 0x4fe04:
        h += [dict(regs=dict(up, d4=d4, d5=d5, d6=d6, d0=0x10, d1=0xe)) for d4, d5, d6 in ((0, 0, 0), (1, 0, 0), (0, 1, 0xffff), (3, 2, 1),
                                                                                             (0x10000, 0, 0), (0x8000, 0x7fff, 0))]
    if entry in (0x4fe0e, 0x4fe14, 0x4fe1a, 0x4fe20, 0x4fe26, 0x4fe2c, 0x4fe32, 0x4fe0a):
        h += [dict(regs=dict(up, d0=0x10, d1=0xe, d4=d4, d5=d5)) for d4, d5 in ((0, 0), (1, 2), (0xffff, 3), (0x12340005, 0x56780007))]
    if entry == 0x4fe38:
        h += [dict(regs=dict(up, d4=d4, d5=d5, d6=d6)) for d4, d5, d6 in ((0, 5, 0), (1, 5, 0xffff), (2, 3, 0x8000), (0x10000, 0xffff, 0x7fff))]
    if entry in (0x4fe40, 0x4fe48):
        h += [dict(regs=dict(up, d4=d4, d5=d5, d6=d6)) for d4, d5, d6 in ((0, 5, 0), (0xffff, 0, 1), (0x7fff, 0x8000, 0xffff))]
    if entry == 0x4fe50:
        for d0, d4, d1, d5 in ((0, 1, 0, 1), (0, 0, 0, 1), (0x25, 1, 0, 1), (0x26, 1, 0, 1), (0x13, 0x13, 0, 1), (0x10, 0xffff, 0x10, 0xffff),
                               (0x10, 2, 0x1d, 1), (0x10, 2, 0x1e, 1), (0x10, 2, 0, 0), (0x10, 2, 0xffff, 2), (0x12340010, 0xabcd0003, 0x5678000e, 0xef010004)):
            h.append(dict(regs=dict(up, d0=d0, d4=d4, d1=d1, d5=d5, d3=0x1234abcd)))
    if entry == 0x4fe60:
        h += [dict(regs=dict(up, d1=d1, d5=d5, d7=d7, d3=0x1234abcd)) for d1, d5, d7 in ((0, 1, 0), (0x1d, 1, 0x25), (0x1e, 1, 3), (0x10, 0xffff, 0x7ff),
                                                                                          (0, 0, 0xffff))]
    if entry == 0x4fe74:
        h += [dict(regs=dict(up, d3=d3, d7=d7)) for d3, d7 in ((0x1234abcd, 0), (0x00210000, 0x1d), (0xffffffff, 0xffff), (0x80000000, 0x8fff))]
    if entry == 0x4fe86:
        h += [dict(regs=dict(up, d3=v)) for v in (0x12345678, 0)]
    if entry == 0x4fea4:
        h += [dict(regs=dict(up, d0=0x10, d1=0xe, d2=v)) for v in (0, 0xc, 0xd, 0xe, 0xf, 0x10, 0x8000, 0xffff, 0x1234000e)]
    if entry == 0x4feae:
        h += [dict(regs=dict(up, d0=0x10, d1=0xe, d2=d2, d4=d4)) for d2, d4 in ((0xffff, 1), (0xfffe, 2), (0, 1), (0x7fff, 1))]
    if entry == 0x4feb6:
        h += [dict(regs=dict(up, d0=0x10, d1=0xe, d2=v), regrec=dict(a0=0x20), rec=[(0x20, 2, 0x4321)], stack=[(0, 2, n), (2, 4, SENTINEL)])
              for v, n in ((0, 1), (1, 1), (2, 2), (3, 1))]
    if entry == 0x4febc:
        h += [dict(regs=dict(up, d2=0xfff0), regrec=dict(a0=0x20), stack=[(0, 2, v), (2, 4, SENTINEL)]) for v in (1, 2, 3)]
    if entry == 0x4fec6:
        for w76, w78 in ((0, 0), (0xa0, 0x1ff), (0x8000, 0), (0x7fff, 0xffff), (0x50, 0x100), (0x100, 0x7f), (0xffff, 0x1fe), (0x9f, 0x17f), (0xa8, 0x180)):
            h.append(dict(regs=dict(up), a6off=[(0x76, 2, w76), (0x78, 2, w78), (0x7b, 1, 0x55), (0x7d, 1, 0x55)]))
    if entry == 0x4feea:
        h += [dict(regs=dict(up, d0=d0, d1=d1)) for d0, d1 in ((0, 0), (0xffec, 0x10), (0x10, 0xf), (0x8000, 0x8010), (0x1234fff0, 0x5678ffff))]
    if entry == 0x4fef8:
        h += [dict(regs=dict(up, d0=d0, d1=d1)) for d0, d1 in ((0, 0xfff0), (0x10, 0), (0x20, 0x10), (0x8000, 0x7ff0), (0x12340001, 0x5678fff1))]
    if entry == 0x4ff04:
        h += [dict(regs=dict(up, d0=d0, d1=d1), a6off=[(0x7b, 1, 0x55), (0x7d, 1, 0x55)]) for d0, d1 in ((0, 0), (0xffff, 0xffff), (0x1f3, 0x7), (0x12340001, 1))]
    if entry == 0x4ff5c:
        h += word(0x7a, (0, 1, 0x100, 0x8000))
    if entry == 0x4ff74:
        h += word(0x7a, (0x1ff, 0x200, 0x201, 0xffff, 1, 0x8000))
    if entry == 0x4ff84:
        h += [dict(regs=dict(up), a6off=[(0x76, 2, a), (0x78, 2, b), (0x7a, 2, c)]) for a, b, c in ((0x10, 0xe, 0x0d00), (0x12, 0x10, 0xff00), (0, 0, 0))]
    if entry == 0x4ff50:
        h += byte(0x7c, (0, 0x80, 0xff))
    # ---- 6f282 / 6f352 / b3dfc
    if entry == 0x6f282:
        h += [dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 2, v)], a6off=[(0x7c, 1, b)]) for v, b in ((0, 0), (1, 0xff), (0x2aab, 3), (0xffff, 0x80))]
    if entry == 0x6f358:
        h += [dict(regs=dict(up, d0=d0), regrec=dict(a0=0x20), rec=[(0x20, 2, w)]) for d0, w in ((5, 5), (4, 5), (6, 5), (0, 0), (0xffff, 0), (0x12340000, 1))]
    if entry == 0xb3e08:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x3f, 0x40, 0x80, 0xc0, 0xffffff3f, 0x100)]
    # ---- c13c0 .. c155e (the FR1 kind handler)
    if entry == 0xc13f8:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x8000, 0x80, 0xffff, 0x7fff, 0x1234, 0xfedc)]
    if entry in (0xc1430, 0xc1450, 0xc1462, 0xc14de, 0xc14e8):
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry == 0xc143a:
        h += [dict(regs=dict(up), a6off=[(0xb4, 2, v), (0x36, 4, w)]) for v, w in ((0, 0), (0x8000, 0x7fffffff), (0x7fff, 0x80000000), (0xfff8, 1), (8, 0xffffffff))]
    if entry == 0xc145a:
        h += [dict(a6off=[(0xb0, 2, v), (0xaf, 1, 0x55), (0xb2, 1, 0x55)]) for v in (0, 1, 2, 3, 0x8000, 0xffff)]
    if entry in (0xc146c, 0xc14f2):
        off = 0x36 if entry == 0xc146c else 0x64
        h += [dict(regs=dict(up), a6off=[(off, 4, a), (0xb4, 2, b)]) for a, b in ((0, 0), (0x7fffffff, 0x8000), (0x80000000, 0x7fff), (0x100000, 0xffff))]
    if entry in (0xc147c, 0xc1502):
        h += [dict(regs=dict(up), a6off=[(0xb4, 2, a), (0xb2, 2, b), (0x15, 1, f)]) for a, b, f in ((0, 0, 0), (0x8000, 0x8000, 1), (0x7fff, 1, 0xfe), (0xffff, 1, 0xff))]
    if entry in (0xc1492, 0xc1518):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x4000, 0x8000, 0xffff, 0x12343fff)]
    if entry in (0xc149c, 0xc1522):
        h += [dict(regs=dict(up, d0=v), a6off=[(0xb5, 1, 0x55), (0xb7, 1, 0x55)]) for v in (0, 0x1fff, 0x2000, 0x3fff, 0x4000, 0xe000, 0xffff, 0x12342000)]
    if entry == 0xc1536:
        h += byte(0xb6, (0, 1, 2, 0xff, 0x81))
    if entry in (0xc14b2, 0xc1550):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 4, 0xfffffffb, 0xffffffff, 0x40000)]
    if entry == 0xc14c2:
        h += [dict(regs=dict(up), a6off=[(0x36, 4, v)]) for v in (0, 0x80000000, 0x12345678)]
    if entry == 0xc13e8:
        h += [dict(regs=dict(up), a6off=[(0x76, 4, v)]) for v in (0xb4036, 0xb403e, 0xb41be, 0, 0xc0924)]
    # ---- e9b8a .. ea334 (the 2986 child e9b8a)
    if entry == 0xe9b9a:
        h += [dict(regs=dict(up, d0=v), a6off=[(0x88, 2, w)]) for v, w in ((3, 0), (0x12340003, 1), (0xff03, 2), (3, 1), (3, 2), (0x80000003, 0))]
    if entry == 0xe9bae:
        h += [dict(regs=dict(up, d0=0), a6off=[(0x88, 2, w)]) for w in (0, 1, 2)]
    if entry in (0xe9bf2, 0xe9be6):
        for n, d0 in ((0, 0), (1, 0), (3, 2), (2, 3), (0xff, 0), (4, 0x104)):
            h.append(dict(regs=dict(up, d0=d0, d7=0), regrec=dict(a1=0x40), a6off=[(0x8f, 1, n)] + [(0x76 + k, 1, k) for k in range(8)],
                          rec=[(0x44 + 2 * k, 2, 0x10 * k + 1) for k in range(16)]))
    if entry == 0xe9bfa:
        h += [dict(regs=dict(up, d0=d0, d7=d7), a6off=[(0x7e, 4, 0xea3cc)] + [(0x76 + k, 1, (3 * k) & 0xf) for k in range(8)])
              for d0, d7 in ((0, 0), (5, 0xfff0), (0xffff0001, 0x8000))]
    if entry in (0xe9c0a, 0xe9c1c):
        for w42, d7 in ((0, 0), (8, 0), (9, 0), (0x138, 0), (0x137, 0), (0x100, 0x38), (0x8000, 0), (0x7fff, 0xffff), (0x10, 8)):
            h.append(dict(regs=dict(up, d7=0x12340000 | d7), a6off=[(0x42, 2, w42), (0x2e, 2, 0x1234)]))
    if entry in (0xe9c30, 0xe9c46):
        for w46 in (0, 0x107, 0x108, 0x109, 0x1df, 0x1e0, 0x1e1, 0x8000, 0x7fff):
            h.append(dict(regs=dict(up, d7=0x12340010), a6off=[(0x46, 2, w46), (0x32, 2, 0x1234), (0x2e, 2, 0x4321)]))
    if entry in (0xe9c16, 0xe9c2a, 0xe9c40, 0xe9c52):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0xffff, 0x8001, 0x7fff)]
    if entry == 0xe9c64:
        h += byte(0x90, (3, 3))
    if entry in (0xea13c, 0xea132):
        h += word(0xa4, (0, 2, 0x8000))
    if entry == 0xea166:
        for sw, a4 in ((2, 2), (1, 2), (3, 2), (0x8000, 1), (0x7fff, 0xffff), (0, 0)):
            h.append(dict(regs=dict(up), stack=[(0, 2, sw), (2, 4, SENTINEL)], a6off=[(0xa4, 2, a4)]))
    if entry == 0xea172:
        h += [dict(regs=dict(up, d1=d1, d6=d6)) for d1, d6 in ((0, 0), (1, 0x13), (2, 0x14), (0xffff, 0x15), (3, 0xffff), (0x10000, 5))]
    if entry == 0xea182:
        h += [dict(regs=dict(up, d1=d1, d6=d6), regrec=dict(a0=0x20), a6off=[(0x93, 1, b)]) for d1, d6, b in ((0, 0, 0), (1, 0x13, 0), (7, 5, 0x80), (9, 2, 0xff),
                                                                                                           (0xffff, 1, 0x7f))]
    if entry == 0xea192:
        h += [dict(regs=dict(up, d1=d1), regrec=dict(a0=0x20), rec=[(0x20, 2, 0x1234)], a6off=[(0x92, 1, b)])
              for d1, b in ((0, 1), (0, 0xfe), (1, 2), (7, 0x80), (9, 2), (8, 0xfe), (0xffff, 0x80))]
    if entry == 0xea19e:
        h += [dict(regs=dict(up), a6off=[(0x82, 2, a), (0x86, 2, b), (0x84, 2, c)]) for a, b, c in ((0, 0, 0), (0xffff, 1, 0x8000), (0x7fff, 0x7fff, 1))]
    if entry == 0xea1b4:
        h += [dict(regs=dict(up, d1=d1), a6off=[(0x8f, 1, n)]) for d1, n in ((0, 1), (0, 2), (1, 2), (0xff, 0), (0xfe, 0xff), (0x1ff, 1))]
    if entry == 0xea1bc:
        h += [dict(regs=dict(up), stack=[(0, 2, v), (2, 4, SENTINEL)]) for v in (0, 0x8000, 0x7fff, 0xffff)]
    if entry == 0xea1c2:
        h += byte(0x93, (0, 1, 0x80, 0xff))
    if entry == 0xea330:
        h += [dict(regs=dict(up), stack=[(0, 2, v), (2, 4, SENTINEL)]) for v in (0, 0x8001, 0xffff)]
    if entry == 0xea2ca:
        for w8a, w88, t in ((0, 0, 4), (0, 0, 5), (0, 0, 3), (0xfffc, 1, 0), (0xfffb, 2, 0xffff), (0x10, 1, 0x15), (0x8000, 0, 0x8004)):
            h.append(dict(regs=dict(up), a6off=[(0x8a, 2, w8a), (0x88, 2, w88)], a5off=[(0x5e4a + 2 * w88, 2, t)]))
    if entry == 0xea2e6:
        h += [dict(regs=dict(up), a6off=[(0x8e, 1, v), (0x19, 1, 0x11), (0x1a, 1, 0x22)]) for v in (0, 1, 0xff, 0x7f)]
    if entry == 0xea314:
        h += [dict(regs=dict(up, d1=d1), a6rec=[(0x7e, 4, 0x40)], a6off=[(0x76 + d1, 1, b)], rec=[(0x40 + 2 * b, 4, v)])
              for d1, b, v in ((0, 0, 0), (1, 3, 0), (2, 1, 0x12345678))]
    if entry in (0xea2fe, 0xea334, 0xea314):
        for d1, b in ((0, 0), (1, 3), (7, 0x10), (0xffff, 2), (0x10002, 5)):
            h.append(dict(regs=dict(up, d1=d1), a6off=[(0x7e, 4, 0xea3cc), (0x76 + (d1 & 0xffff if d1 & 0xffff < 0x8000 else -1), 1, b), (0x86, 2, 0x1234)]))
    return h


# chain hints: let the real producers return both C values
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry == 0x3ff74:
        # 40b60 -> 4d418: TST.B D0 (WORD 8a): the player node 100cb8 / 100da8 (LONG 0 270e for 289e, BYTE 61 bit 7), the WORD (A4) slot 5cba / 5ce6(A5)
        pl = t % 2
        node = (0x100cb8, 0x100da8)[pl]
        return dict(a6off=[(0x8a, 2, pl)], writes=[(node & 0xffff, 4, (0x270e, 0x1ef0e, 0x270e)[(t // 2) % 3]),
                                                   ((node + 0x61) & 0xffff, 1, (0, 0x80, 0)[(t // 3) % 3])],
                    a5off=[(0x5cba + 0x2c * pl, 2, (0, 0, 1)[(t // 4) % 3]), (0x5cba + 0x2c * pl + 0x22, 1, (0, 1)[(t // 5) % 2])])
    if entry == 0x40b60:
        return chain_hint(0x3ff74, t, rng)
    if entry == 0x40846:
        # 4d766: 1bfb4 (D0 bit 0) then BTST #7,10f000: set -> C Set (ADD.B ff)
        return dict(regs=dict(d0=t % 2), writes=[(0xf000, 1, (0, 0x80, 0x7f, 0xff)[(t // 2) % 4])])
    if entry == 0x408c0:
        # 288c: LONG c(A6) = 0 -> Set; else 289e (CMPI.L #270e,(A0))
        return dict(a6off=[(0xc, 4, (0, 0x100cb8, 0x100da8, 0)[t % 4])], writes=[(0x0cb8, 4, (0x270e, 0x1234)[(t // 4) % 2])])
    if entry in (0x40ab8, 0x40af6):
        # 28ae: WORD 104ca0 <= D0.W (a) -> the failure 290e (Clear); else a free node -> Set
        return dict(writes=[(0x4ca0, 2, (0, 0xa, 0xb, 0x100, 5)[t % 5])])
    if entry == 0xc13e8:
        # b4304: LONG 76(A6) = b4036 / b403e -> Clear; else Set
        return dict(a6off=[(0x76, 4, (0xb4036, 0xb403e, 0xb41be, 0xc0924)[t % 4])])
    if entry == 0xea14c:
        # ea2ca: unsigned WORD 8a + 4 < WORD 5e4a(A5) + 2 x WORD 88 -> Set
        w88 = t % 3
        return dict(a6off=[(0x8a, 2, (0, 1, 2, 0xfffc)[(t // 3) % 4]), (0x88, 2, w88)], a5off=[(0x5e4a + 2 * w88, 2, (4, 5, 6, 0)[(t // 2) % 4])])
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
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
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
            # FR15: WORD 8a (3ff54 player), WORD 7a (4ff5c / 4ff74), BYTE 61 (40818), WORD b0 (c145a), LONG c (the parent of 4ff64), BYTE 15 bits 7 / 0
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x8a, 2, (0, 1, 0x8000, 0)[t % 4]), (0x7a, 2, (0, 0x100, 0xd00, 0x200, 0x1ff)[(t // 2) % 5]),
                               (0x61, 1, (0, 0x80, 0x40)[(t // 3) % 3]), (0xb0, 2, (1, 2, 7)[(t // 2) % 3]), (0xc, 4, world.pointer()),
                               (0x15, 1, (0, 0x80, 1, 0x81, 0xff)[t % 5]), (0x9e, 1, (0, 1)[(t // 2) % 2]), (0xa7, 1, (0, 8, 0x11, 0xff)[(t // 4) % 4])] +
                        ([(0x26, 4, 0)] if t % 5 != 4 else []))
            st = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
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
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a NATURAL frame; mode 'cb': the nodes of the area POOL whose callback LONG is one
    of NATURAL_CALLBACKS; mode 'any': every node 1009a8 + c4 k of the pool with a routed callback LONG (the frames in which the exact-bitmap
    re-observation first records an FR15 start).  Declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback,
    the other registers as at the frame start.  Up to the sentinel or the first unrouted PC; kept when the run executes an FR15 start (mode 'any': at
    most two nodes per frame)."""
    count = 0
    seen = set()
    for cfg, case, frame, mode in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        nodes = []
        if mode == 'cb':
            for a in range(POOL[0] & 0xffff, POOL[1] & 0xffff, 2):
                cb = struct.unpack('>I', ram[a:a + 4])[0]
                if cb in NATURAL_CALLBACKS:
                    nodes.append(0x100000 + a)
        else:
            for a in range(0x09a8, POOL[1] & 0xffff, NATURAL_STRIDE):
                cb = struct.unpack('>I', ram[a:a + 4])[0]
                if unit_of(cb) is not None:
                    nodes.append(0x100000 + a)
        kept = 0
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
                continue                                    # the run does not reach FR15 code
            record(tr['pcs'] + [tr['stop']])
            add_run(add, 'natural-%05x-%s%03d-f%d-%x' % (cb, cfg, case, frame, node), st, tr,
                    dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], mode=mode,
                         unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
            count += 1
            kept += 1
            if mode == 'any' and kept >= 2:
                break
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
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
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
    err('odd-pc', U.with_host_writes(st, pc=0x4fdfd), 'unaligned animation machine PC', 0x4fdfd)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    device = 'unsupported animation machine write device'
    # the JMP e9c72(PC,D0.W) of e9c64 (contract decision 2): BYTE 90(A6) other than 3 (the only transcribed entry e9c7e)
    for v in (0, 1, 2, 4, 5, 0x80, 0xff):
        err('e9c64-b90-%x' % v, U.with_host_writes(st, [((a6 + 0x90) & 0xffff, 1, v)], pc=0xe9c64), ERROR_JUMP, 0xe9c64)
    # odd node / stack / pointer: the entry block fails (the row's stop is the PC right after the failing block)
    err('40896-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x40896), odd_write, 0x40896, stop=0x49290)
    err('4fec6-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x4fec6), odd_word, 0x4fec6, stop=0x4feea)
    err('ea13c-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xea13c), odd_word, 0xea13c, stop=0xea14c)
    err('3ff24-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x3ff24), odd_write, 0x3ff24, stop=0x496c2)
    err('409e6-odd-list', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 4, 0x10e921)], pc=0x409e6), odd_word, 0x409e6, stop=0x40a0e)
    err('40bc8-odd-a0', U.with_host_writes(st, regs=dict(a0=0x10e921), pc=0x40bc8), odd_word, 0x40bc8)
    err('4088e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4088e), odd_word, 0x4088e)
    err('40b7a-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x40b7a), odd_word, 0x40b7a)
    err('ea2c6-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xea2c6), odd_word, 0xea2c6)
    err('4fe86-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4fe86), odd_word, 0x4fe86)
    err('ea1bc-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xea1bc), odd_word, 0xea1bc, stop=0xea1d0)
    err('4ff64-rom-parent', U.with_host_writes(st, [((a6 + 0xc) & 0xffff, 4, 0x1b000)], pc=0x4ff64), device, 0x4ff64, stop=0x2a00)
    err('c141e-rom-node', U.with_host_writes(st, regs=dict(a6=0x1b000), pc=0xc141e), device, 0xc141e, stop=0xc142a)
    # failures after executed blocks: 3ff54 (WORD 8a = 0) -> 3ff5c -> 3ff68 (WORD 2e(A0) at an odd A5 - 7348); 4ff74 (WORD 7a = 100) -> 4ff7e -> 4ff84 ->
    # 4fea4 .. (D2 = 0: every circle skipped) -> the RTS 4fec4 at an odd A7 is reached after the pushes / pops of 4feae (at an odd A7 the first push
    # fails in 4feae); 4fe48 -> 4fe4c -> 4fe04 (D5 < D4) -> the RTS 4fe4e at an odd A7; ea1c2 (BYTE 93 = 1) -> ea1d0 -> the RTS ea2be at an odd A7
    err('3ff54-then-3ff68', U.with_host_writes(st, [((a6 + 0x8a) & 0xffff, 2, 0)], regs=dict(a5=a5 + 1), pc=0x3ff54), odd_word, 0x3ff68)
    err('4fe48-then-4fe4e', U.with_host_writes(st, regs=dict(a7=a7 + 1, d4=5, d5=5, d6=0), pc=0x4fe48), odd_word, 0x4fe4e)
    err('ea1c2-then-ea2be', U.with_host_writes(st, [((a6 + 0x93) & 0xffff, 1, 1)], regs=dict(a7=a7 + 1), pc=0xea1c2), odd_word, 0xea2be)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x4fec6, 0xc13f8, 0xea2ca, 0x4fe50)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
