"""V1 fixture spec of the area-D unit FR11 (engine/src/animation_machine_objects_fr11.cpp, 192 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr11-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 FR11 row): the
FR10 later-unit successors 70e42 / 70fac / cd7e2 / cd92e / cd96c, the FR4 table entries cc836 / cc842, the item-object handlers of the FR1 2986 child
b3dbc (b4030 JMP (A0) -> b403e / b41be -> b411c -> b4104 / b42b0 JMP b42b8(PC,D0.W) / b427e), the kind handler bfb5a -> bfc2a -> bfcaa -> bfcd8 /
bfdb2 -> b3e1c (TRAP #15 b3e58 boundary), the U18 install b67b2 -> b686e (28ae child b774a -> b77f4), the FR10 installs b6ca2 -> b6d6a / b6d82 ->
b6e50 -> b6e8c, the script callback b7d4a (2986 child b3dbc, MOVEM.W (A7)+,D0-D6), the FR3 install c5432 -> c5470 -> c5486 -> c54a6 JMP c54b2(PC,D0.W) /
c5540 and the 28ae child c5592 -> c5602.  Computed jumps (contract decision 2): JMP (A0) b4034 (the ROM-writer handlers of LONG 76), JMP b42b8(PC,D0.W)
b42b4 (displacement 0 / 4 / c), JMP c54b2(PC,D0.W) c54ae (index 0..1a); TRAP #15 b3e58 is a boundary outside the unit (decision 3).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR10, C1..C10) with declared host
edits.  This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the
'natural' family takes the frame-start states of that observation (state packs, read-only) in which a node of the pool 100800..104c00 holds an FR11
node entry (or the FR1 item child b3dbc, whose kind handler bfb5a is FR11) as its callback LONG, keeps their RAM / PVC / bank and declares only the
registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return LONG, PC = the callback).  The spec reads those packs itself (io_pack
below, observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 11 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the callbacks and installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers, handlers and table entries entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 11 consumers, the computed-jump targets outside decision 2, odd node /
            stack / A0, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when
            it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR10, C1..C10
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C9)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'fr11'
ERROR_PC = 'unsupported animation objects fr11 PC'
ERROR_CARRY = 'objects fr11 caller requires known carry'
ERROR_JUMP = 'unsupported animation objects fr11 jump target'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x70e42, 0x70ea2), (0x70fac, 0x70fc2), (0xb3e1c, 0xb3e58), (0xb3e70, 0xb3e74), (0xb4030, 0xb4036), (0xb403e, 0xb40f8), (0xb4104, 0xb41b2),
          (0xb41be, 0xb41f2), (0xb427e, 0xb4294), (0xb42b0, 0xb42bc), (0xb42c8, 0xb42ca), (0xb4abc, 0xb4aca), (0xb67b2, 0xb68ba), (0xb6ca2, 0xb6d90),
          (0xb6dac, 0xb6e5e), (0xb6e8c, 0xb6ec8), (0xb774a, 0xb780c), (0xb7d4a, 0xb7dd6), (0xbfb5a, 0xbfb62), (0xbfc2a, 0xbfcfa), (0xbfdb2, 0xbfdd0),
          (0xc5432, 0xc54b2), (0xc54ca, 0xc54ce), (0xc551e, 0xc5520), (0xc5540, 0xc554c), (0xc5592, 0xc5612), (0xc5618, 0xc561a), (0xcc836, 0xcc83a),
          (0xcc842, 0xcc846), (0xcd7e2, 0xcd7e4), (0xcd92e, 0xcd93c), (0xcd96c, 0xcda34)]
STARTS = sorted(int(x, 16) for x in (
    '70e42 70e4a 70e72 70e76 70e9e 70fac 70fb2 70fb4 70fbc b3e1c b3e46 b3e70 b4030 b403e b4058 b405a b4062 b4064 b4080 b4084 b408c b409e b40a2 b40a6 '
    'b40b4 b40b8 b40c0 b40d4 b40d8 b40dc b40ec b40f0 b40f6 b4104 b4116 b411c b412c b4132 b413a b4154 b4156 b4198 b419e b41a6 b41ae b41be b41c2 b41cc '
    'b41d8 b41e6 b427e b4288 b4292 b42b0 b42b8 b42c8 b4abc b4ac2 b67b2 b67b8 b67c4 b67fc b6800 b6838 b6850 b6868 b686e b6874 b687a b687e b688e b6892 '
    'b689c b68a0 b68b6 b6ca2 b6cac b6cb0 b6cbc b6cc6 b6ccc b6cd8 b6d10 b6d14 b6d4c b6d6a b6d6e b6d74 b6d78 b6d7e b6d82 b6d8c b6dac b6db8 b6df0 b6df4 '
    'b6e2c b6e50 b6e54 b6e5a b6e8c b6e94 b6e9c b6eb4 b6ec4 b774a b776e b777a b77b2 b77b6 b77ee b77f4 b77fa b7800 b7804 b780a b7d4a b7d52 b7d5a b7d8c '
    'b7d94 b7dae b7db2 b7dc6 b7dc8 b7dce b7dd4 bfb5a bfc2a bfc70 bfc80 bfc90 bfc9e bfca4 bfcaa bfcb2 bfcce bfcd0 bfcd8 bfcde bfce4 bfcea bfcf2 bfcf8 '
    'bfdb2 bfdbe bfdca c5432 c5442 c546a c5470 c5476 c547c c5480 c5486 c5492 c5496 c54a6 c54ca c551e c5540 c5592 c5598 c55a8 c55ae c55c0 c55f4 c5602 '
    'c5608 c560e c5618 cc836 cc842 cd7e2 cd92e cd96c cd974 cd98a cd98e cd996 cd9ac cd9b0 cd9b8 cd9ce cd9d2 cd9da cd9f0 cd9f4 cd9fc cda12 cda16 cda2c'
    ).split())
# the 11 C consumers: BCC b687a b6d74 b6e5a b7800 c547c c560e (49fc6), b688e (28ae), b6cac b6d8c (49392), c5492 (4b54e), b7d8c (MOVEM.W (A7)+,D0-D6;
# 2986)
CONSUMERS = (0xb687a, 0xb6d74, 0xb6e5a, 0xb7800, 0xc547c, 0xc560e, 0xb688e, 0xb6cac, 0xb6d8c, 0xc5492, 0xb7d8c)
CLEAR_SET = ()
SET_SET = (0xb689c, 0xb7dae)            # ORI.B #1,CCR (the next MOVE / MOVEQ clears it: no reader)
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()
STARTS_SET = set()
Z_READERS = ()                          # no Z / N crosses an FR11 block boundary
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# b68a0 CMPI.W #1,8e(A6); BNE.W b68b6: both outcomes are b68b6 (one successor)
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
# TRAP #15 b3e58 (b3e46 with LONG 7a = 0, decision 3) and the FR1 TRAP #15 b3eac (b3ea2 with WORD 76 >= 6e, reached from b3e70): boundaries
TRAPS = (0xb3e58, 0xb3eac)
# PCs of later units that an FR11 block reaches by a fall-through or a branch (FR12 b41f2 b6e5e c5612, FR13 b6d90 bfcfa), the still unrouted later-unit
# stops of the FR10 blocks (fr10 UNIT_EXITS that FR11 does not route: FR12 70f8e b6c58, FR13 70f60 70fcc 70ff8 71028) and of the C1..C9 blocks (pc10
# EXIT_STOPS[:12]).  Declared stops of the native runs: a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0xb41f2, 0xb6e5e, 0xc5612, 0xb6d90, 0xbfcfa,
              0x70f8e, 0xb6c58, 0x70f60, 0x70fcc, 0x70ff8, 0x71028,
              0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6, 0x4e69a)
UNIT_EXITS = EXIT_STOPS[:5]             # the FR11 later-unit stops (FR12 / FR13)
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xb6874, 0xb687a), (0xb6d6e, 0xb6d74), (0xb6e54, 0xb6e5a), (0xb77fa, 0xb7800), (0xc5476, 0xc547c), (0xc5608, 0xc560e), (0xb687e, 0xb688e),
          (0xb6ca2, 0xb6cac), (0xb6d82, 0xb6d8c), (0xc5486, 0xc5492), (0xb7d5a, 0xb7d8c))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# the computed jumps of FR11 (contract decision 2) and their allowed targets: JMP (A0) b4034 (the ROM-writer handlers of LONG 76(A6): the FR1 table
# b3dcc via b3f02, b402a after LEA b42a2 / c0924 / b4294), JMP b42b8(PC,D0.W) b42b4 (the kind-record BYTE 97: 0 / 4 / c), JMP c54b2(PC,D0.W) c54ae
# (index 0..1a after the c5496 guard).  Any other target is the C++ checked jump-target error (a native run that jumps elsewhere is not a fixture
# world); an allowed target that is not an FR11 block is a stop.
HANDLERS = (0xb41be, 0xb4036, 0xb42a2, 0xb403e, 0xc0924, 0xb4294)
TABLE_B42B8 = (0xb42b8, 0xb42bc, 0xb42c4)
TABLE_C54B2 = tuple(0xc54b2 + 4 * k for k in range(0x1b))
JUMP_TARGETS = {0xb4034: HANDLERS, 0xb42b4: TABLE_B42B8, 0xc54ae: TABLE_C54B2}
JUMP_PCS = (0xb4034, 0xb42b4, 0xc54ae)
JUMP_ROUTED = ()
LIST_JUMPS = {}
# computed jumps that the FR11 runs reach (FR1 b3dc8 b3f3e b3fc4 b3fca through b3e70 -> b3ea2 and the b3dbc children; FR4 cc7a8 / cc82a; the C3 .. C10
# list): an unrouted target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0xb3dc8, 0xb3f3e, 0xb3fc4, 0xb3fca, 0xcc7a8, 0xcc82a, 0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6,
                  0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36, 0x2224c, 0x22428, 0x21e10, 0x2229a, 0x22378, 0x203ac)
TABLE_ENTRIES = ()
# the callbacks and installed values entered as node callbacks: b6ca2 / b6d82 (FR10 b6c8a / b6c98, FR11 b6d78), b67b2 (U18 b67a8), c5432 (FR3 c541a),
# the 28ae children b774a (b687e) and c5592 (c5432), the in-range installs b686e b6d6a b6e50 b77f4 bfcaa c5470 c5602, the kind handler bfb5a (entered
# with A6 = the item node); the callee entries (branch targets of other units' blocks, the item handlers, the script callback b7d4a, table entries,
# helpers)
NODE_ENTRIES = (0xb6ca2, 0xb6d82, 0xb67b2, 0xc5432, 0xb774a, 0xc5592, 0xb686e, 0xb6d6a, 0xb6e50, 0xb77f4, 0xbfcaa, 0xc5470, 0xc5602, 0xbfb5a)
NATURAL_ENTRIES = NODE_ENTRIES + (0xb3dbc,)   # the natural family also takes the FR1 item child b3dbc (its kind handler bfb5a is FR11)
CALLEES = (0x70e42, 0x70fac, 0xcd7e2, 0xcd92e, 0xcd96c, 0xcc836, 0xcc842, 0xb4030, 0xb403e, 0xb41be, 0xb411c, 0xb4104, 0xb42b0, 0xb427e, 0xb4abc,
           0xb4ac2, 0xb7d4a, 0xb3e1c, 0xbfdb2, 0xc54a6, 0xb4084, 0xb40b8, 0xb413a, 0xbfc2a, 0xb6e8c, 0xc5496)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x76, 0x7a, 0x9e)   # node links, pointer fields, the handler LONGs 76 / 7a and the record pointer 9e
# natural worlds of the extended observation: (config, case, frame) with a pool node holding an FR11 node entry or b3dbc (scratch natscan_fr11.py: per
# run and callback the first frame, the middle one of the first eight and the last one)
NATURAL = (('X1', 68, 508), ('X1', 68, 546), ('X1', 68, 659), ('X1', 68, 660), ('X1', 68, 663), ('X1', 68, 668), ('X1', 68, 669), ('X1', 68, 672),
           ('X1', 68, 673), ('X1', 68, 674), ('X1', 68, 677), ('X1', 68, 689), ('X1', 68, 690), ('X1', 68, 693), ('X1', 68, 707), ('X1', 68, 708),
           ('X1', 68, 709), ('X1', 68, 712), ('X1', 68, 745), ('X1', 68, 796), ('X1', 68, 797), ('X1', 68, 800), ('X1', 68, 807), ('X1', 68, 818),
           ('X1', 94, 292), ('X1', 94, 330), ('X1', 94, 439), ('X1', 94, 440), ('X1', 94, 443), ('X1', 94, 444), ('X1', 94, 445), ('X1', 94, 448),
           ('X1', 94, 458), ('X1', 94, 459), ('X1', 94, 460), ('X1', 94, 462), ('X1', 94, 475), ('X1', 94, 476), ('X1', 94, 479), ('X1', 94, 488),
           ('X1', 94, 506), ('X1', 94, 507), ('X1', 94, 508), ('X1', 94, 511), ('X1', 94, 544), ('X1', 94, 605), ('X1', 94, 616), ('X1', 94, 627),
           ('X2', 68, 508), ('X2', 68, 546), ('X2', 68, 672), ('X2', 68, 673), ('X2', 68, 676), ('X2', 68, 677), ('X2', 68, 678), ('X2', 68, 681),
           ('X2', 68, 683), ('X2', 68, 684), ('X2', 68, 687), ('X2', 68, 693), ('X2', 68, 713), ('X2', 68, 731), ('X2', 68, 732), ('X2', 68, 733),
           ('X2', 68, 736), ('X2', 68, 769), ('X2', 68, 818), ('X2', 68, 819), ('X2', 68, 822), ('X2', 68, 829), ('X2', 68, 840), ('X2', 94, 286),
           ('X2', 94, 324), ('X2', 94, 464), ('X2', 94, 465), ('X2', 94, 468), ('X2', 94, 469), ('X2', 94, 470), ('X2', 94, 473), ('X2', 94, 484),
           ('X2', 94, 485), ('X2', 94, 488), ('X2', 94, 501), ('X2', 94, 512), ('X2', 94, 523), ('X3', 68, 510), ('X3', 68, 548), ('X3', 68, 628),
           ('X3', 68, 629), ('X3', 68, 632), ('X3', 68, 659), ('X3', 68, 662), ('X3', 68, 676), ('X3', 68, 677), ('X3', 68, 678), ('X3', 68, 681),
           ('X3', 68, 714), ('X3', 68, 760), ('X3', 68, 775), ('X3', 68, 776), ('X3', 68, 779), ('X3', 68, 780), ('X3', 68, 781), ('X3', 68, 784),
           ('X3', 68, 793), ('X3', 68, 794), ('X3', 68, 796), ('X3', 68, 797), ('X3', 68, 815), ('X3', 68, 1518), ('X3', 94, 290), ('X3', 94, 328),
           ('X3', 94, 432), ('X3', 94, 433), ('X3', 94, 436), ('X3', 94, 463), ('X3', 94, 466), ('X3', 94, 480), ('X3', 94, 481), ('X3', 94, 482),
           ('X3', 94, 485), ('X3', 94, 518), ('X3', 94, 573), ('X3', 94, 574), ('X3', 94, 577), ('X3', 94, 578), ('X3', 94, 579), ('X3', 94, 582),
           ('X3', 94, 584), ('X3', 94, 585), ('X3', 94, 588), ('X3', 94, 594), ('X3', 94, 600), ('X3', 94, 606), ('X3', 94, 1298), ('X4', 68, 510),
           ('X4', 68, 548), ('X4', 68, 752), ('X4', 68, 753), ('X4', 68, 756), ('X4', 68, 782), ('X4', 68, 783), ('X4', 68, 786), ('X4', 68, 800),
           ('X4', 68, 801), ('X4', 68, 802), ('X4', 68, 805), ('X4', 68, 838), ('X4', 68, 862), ('X4', 94, 350), ('X4', 94, 388), ('X4', 94, 592),
           ('X4', 94, 593), ('X4', 94, 596), ('X4', 94, 622), ('X4', 94, 623), ('X4', 94, 626), ('X4', 94, 640), ('X4', 94, 641), ('X4', 94, 642),
           ('X4', 94, 645), ('X4', 94, 678), ('X4', 94, 702))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
REINSTALL = ()

VB = (0, 1, 2, 3, 4, 5, 7, 8, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x3f, 0x40, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xef, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x21, 0x3f, 0x40, 0x62, 0x63, 0x64, 0x7f, 0x80, 0xbf, 0xc0, 0xc1, 0x100, 0x2800, 0x3000, 0x57ff,
      0x5800, 0x7fff, 0x8000, 0x8001, 0xc000, 0xffe0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x40000, 0x100000, 0x7fffffff, 0x80000000, 0xfff90000, 0xffff0000, 0xffffffe0, 0xffffffff,
      0x12345678)
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
BUNDLED = ()                            # no flag-sharing Bcc pair inside one FR11 block


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 70fbc / cd7e2 / cd92e into FR10, b3e46 into the TRAP b3e58)."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (none in FR11) would use pcs[n - 1]."""
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
        if seq[i] in JUMP_TARGETS and seq[i + 1] not in JUMP_TARGETS[seq[i]]:
            return None                                 # a computed jump outside the decision-2 targets: the C++ checked jump-target error
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
    the computed jumps that the FR11 runs reach (OTHER_JUMP_PCS: FR1, FR4 cc7a8 / cc82a and the C3 .. C10 list), at a target of the FR11
    computed jumps that is not an FR11 block (JUMP_PCS), or at the
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it: LONG 76(A6) / 7a(A6) one of the handlers of decision 2
        (b3f02 / b402a writes; LONG 7a 0 sometimes: the TRAP boundary b3e58), BYTE 97(A6) 0 / 4 / c (the kind records b3484: the b42b8 table), WORD
        8e(A6) 0..7 mostly (the index of the ROM LONG tables b7f5c / b7f64 / b7f7c / b7fc4 and the WORD table b7f14), WORD 8c(A6) 0..5 mostly (the anim
        selector cd96c), LONG 9e(A6) a record bfdee + 8k (k 0..19: bfc2a), D0.W 0..19 at bfc2a (the kind handlers bfb5a..bfc26), 0..f at bfdbe (49a84
        with D0 = f), 0 / 4 / c at b42b0, 0..1a at c54a6 (the c5496 guard), D7.W 0..80 at b4156 (MOVEQ #0; MOVE.B; NEG.B), A0 a RAM record at the bounds
        blocks b408c .. b40dc and a node at b6cb0 / b68a0 / b7d94, LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), BYTE 1d(A6) < 4 (8ebe /
        8ff4), BYTE 10fd82 = 0."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xc, 0x10, 0x1a, 0x1b, 0x2f, 0x30, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffd0, 0xffff, 0x10000,
                                     0x12340001, 0xffffffff))
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0xffff0000, 0x12345600))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.3 else self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        if entry in (0xbfc2a,):
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(0x1a)
        if entry == 0xbfdbe:
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(0x10)
        if entry == 0xb42b0 and rng.random() < 0.8:
            regs['d0'] = (regs['d0'] & 0xffffff00) | rng.choice((0, 4, 0xc))
        if entry == 0xc54a6 and rng.random() < 0.8:
            regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x1b)
        if entry == 0xb4156:
            regs['d7'] = (regs['d7'] & 0xffff0000) | rng.randrange(0x81)
        if entry == 0xb4154:
            regs['d7'] = (regs['d7'] & 0xffffff00) | rng.randrange(0x80, 0x100)
        if entry in (0xb408c, 0xb40a6, 0xb40c0, 0xb40dc):
            regs['a0'] = rec + 0x20
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e, 0xb41be, 0xb403e))))   # LONG 76(A6): a handler (decision 2)
        writes.append(((a6 + 0x7a) & 0xffff, 4, rng.choice(HANDLERS + (0, 0xb41be, 0xb403e))))      # LONG 7a(A6): b3e1c (0: the TRAP b3e58)
        writes.append(((a6 + 0x97) & 0xffff, 1, rng.choice((0, 4, 0xc, 0))))                       # BYTE 97(A6): the kind-record value 0 / 4 / c
        writes.append(((a6 + 0x8c) & 0xffff, 2, rng.choice((0, 1, 2, 3, 4, 5, 5, 0xffff))))        # WORD 8c(A6): the anim selector / the TST
        writes.append(((a6 + 0x8e) & 0xffff, 2, rng.choice((0, 0, 1, 2, 3, 4, 5, 6, 7))))         # WORD 8e(A6): the table index
        writes.append(((a6 + 0x9e) & 0xffff, 4, 0xbfdee + 8 * rng.randrange(0x1a)))               # LONG 9e(A6): the record bfdee + 8k
        if rng.random() < 0.8:
            writes.append(((a6 + 0x26) & 0xffff, 4, 0))       # 49fc6: LONG 26(A6) = 0 -> Set without the interpreter (random scripts)
        if rng.random() < 0.9:
            writes.append((0xfd82, 1, 0))                                                 # BYTE 10fd82 = 0
        if rng.random() < 0.7:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x8c, 0x8e, 0x8f, 0x97, 0x9e)):
                continue                                        # callback LONG, node links, the pointer fields and the bounded indices stay declared above
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
            for k, v in hint.get('rega5', {}).items():
                regs[k] = a5 + v                                # a register that points at an A5 field
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
        require(unit_of(s) == 'animation_objects_fr11_block', ('start is not routed to objects fr11', hex(s), unit_of(s)))
    # the computed-jump targets (decision 2): the FR11 blocks among them are b41be b403e (handlers), b42b8 (table entry 0), c54ca (table entry 6); every
    # other target stays unrouted (a stop) until a later unit routes it
    for jmp, targets in JUMP_TARGETS.items():
        require(jmp not in STARTS_SET and mine(jmp), ('the jump instruction is inside an FR11 block', hex(jmp)))
        for t in targets:
            require(t in STARTS_SET or unit_of(t) is None, ('computed-jump target must be an FR11 start or unrouted', hex(jmp), hex(t), unit_of(t)))
    require(set(t for ts in JUMP_TARGETS.values() for t in ts) & STARTS_SET == {0xb41be, 0xb403e, 0xb42b8, 0xc54ca}, 'the FR11 jump targets')
    for t in (0xcc836, 0xcc842):
        require(unit_of(t) == 'animation_objects_fr11_block', ('FR4 table entry routed to FR11', hex(t)))
    rng = random.Random(0xF11A)
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
    sys.stderr.write('fr11 spec: %d fixtures (%d natural), visited %d/192, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr11: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr11: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the signed / unsigned WORD
    compares of 70fac / 70fb4, b408c .. b40dc (BLE / BGE against 130 / 10 / 1f0), b6cb0 (CMP.W 42(A6) with 42(A0), BLE), b7d52 (TST.W 7c BLE),
    the TST.W 36 / 3a signs of b403e / b405a / b4084 / b40b8 (BGE / BGT / BMI), the LONG ASR.L #3 / #1 / #8 of b4064 / b413a / b4156 / b4288, the
    ASR.W #1 / NEG.W / MULS.W rotation of b4156 (the D7 table index 0..100), the WORD 98 + 800 BYTE sign of b413a, the BYTE 9c count of b6e8c /
    b6e94, the MULU.W #8 index of bfc2a, the a6 + 8 sine index of bfcb2, the BYTE MOVE Z of bfcd0, the BTST #2,D0 of bfcea, the BYTE 5e guard of
    c5496 (1b), the table indices of b42b0 (0 / 4 / c) and c54a6 (0..1a), the BYTE 15 / 95 bits), the upper register bits of the WORD / BYTE operations,
    the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x70e42, 0x70fac, 0xb3e1c, 0xb403e, 0xb4064, 0xb408c, 0xb40c0, 0xb4104, 0xb413a, 0xb4156, 0xb41cc, 0xb41d8, 0xb4288, 0xb4abc, 0xb6cb0,
                 0xb774a, 0xb7d5a, 0xb7db2, 0xbfc2a, 0xbfcb2, 0xbfdbe, 0xc5486, 0xc5496, 0xc5540, 0xc5598, 0xcd92e, 0xcd96c, 0xb6e2c, 0xb6d4c):
        h += [dict(regs=dict(up))] + mirror
    if entry == 0x70e42:
        h += word(0x9c, (0, 1, 0x8000, 0x100))
    if entry == 0x70fac:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 1, 0x2f, 0x30, 0x31, 0xffd1, 0xffd0, 0xffcf, 0x8000, 0x7fff, 0xffff)]
    if entry == 0x70fb2:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0x8000, 0xffff, 0xffd0, 0xffd1)]
    if entry == 0x70fb4:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0x2f, 0x30, 0xffff, 0)]
    if entry == 0xb3e1c:
        h += [dict(regs=dict(up), a6off=[(0x7a, 4, v)]) for v in (0, 0xb41be, 0xb403e, 0x10000)]
    if entry == 0xb3e46:
        h += [dict(stack=[(0, 4, v)]) for v in (0, 0xb41be, 1, 0x80000000)] + byte(0x95, (0, 0xff, 4))
    if entry == 0xb4030:
        h += [dict(a6off=[(0x76, 4, v)]) for v in HANDLERS]
    if entry == 0xb403e:
        h += word(0x36, (0, 0x7fff, 0x8000, 0xffff)) + byte(0x95, (0, 0xff, 0x10))
    if entry == 0xb405a:
        h += word(0x3a, (0, 1, 0x7fff, 0x8000, 0xffff))
    if entry == 0xb4064:
        for d0, d1, l36, l3a in ((0x40000, 0xfffc0000, 0, 0), (0xfffc0000, 0x40000, 0x7fffffff, 0x80000000), (0x40000, 0x40000, 0x40007, 0x3fff8),
                                 (0x40000, 0x40000, 0xfff00000, 0x12345678)):
            for w8c in (0, 1):
                h.append(dict(regs=dict(up, d0=d0, d1=d1), a6off=[(0x36, 4, l36), (0x3a, 4, l3a), (0x8c, 2, w8c)]))
    if entry in (0xb4084, 0xb40b8):
        h += word(0x36 if entry == 0xb4084 else 0x3a, (0, 0x7fff, 0x8000, 0xffff))
    if entry == 0xb408c:
        for a, b, w42 in ((0x100, 0x20, 0x10), (0x100, 0x20, 0x11), (0x8000, 0, 0x130), (0x7fff, 0, 0x7fff), (0x130, 0, 0), (0x131, 0, 0)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 2, a), (0x24, 2, b)], a6off=[(0x42, 2, w42)]))
    if entry == 0xb40a6:
        for a, w42 in ((0x10, 0), (0xf, 0), (0x8000, 0x10), (0, 0x10), (0xffff, 0x10)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 2, a)], a6off=[(0x42, 2, w42)]))
    if entry == 0xb40c0:
        for a, b, w46 in ((0x100, 0xf0, 0), (0x100, 0xf0, 1), (0x1f0, 0, 0x8000), (0x1f1, 0, 0), (0x7fff, 1, 0)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x22, 2, a), (0x26, 2, b)], a6off=[(0x46, 2, w46)]))
    if entry == 0xb40dc:
        for a, w46 in ((0x130, 0), (0x12f, 0), (0x100, 0x30), (0x8000, 0x130), (0xffff, 0x131)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x22, 2, a)], a6off=[(0x46, 2, w46)]))
    if entry in (0xb409e, 0xb40b4, 0xb40d4, 0xb40ec):
        h += [dict(a6off=[(0x36, 4, v), (0x3a, 4, v ^ 0x5a5a)]) for v in (0, 0x80000000, 1, 0xffffffff)]
    if entry == 0xb411c:
        h += [dict(a6off=[(0x95, 1, b95), (0x15, 1, b15)]) for b95, b15 in ((0x10, 0x80), (0xff, 0x7f), (0, 0), (0xef, 0xff))]
    if entry == 0xb4132:
        h += [dict(regs=dict(up, d0=v)) for v in (8, 0xf7, 0x108, 0xff)]
    if entry == 0xb419e:
        h += [dict(regs=dict(up, d0=v)) for v in (0x80, 0x7f, 0x180, 0xff)]
    if entry == 0xb413a:
        for l7e, w98 in ((0x10000, 0x7800), (0xffff0001, 0xf800), (0x80000000, 0x7700), (0x7fffffff, 0xff00), (0, 0x8000), (3, 0x7f00)):
            h.append(dict(regs=dict(up), a6off=[(0x7e, 4, l7e), (0x98, 2, w98), (0x3a, 4, 0x12345678)]))
    if entry == 0xb4154:
        h += [dict(regs=dict(up, d7=0x99aabb00 | v)) for v in (0x80, 0xff, 0x81, 0xc0)]
    if entry == 0xb4156:
        for d7, l36, l3a in ((0, 0x12345678, 0x9abcdef0), (0x40, 0x80000000, 0x7fffffff), (0x80, 0xffffff00, 0x100), (0x7f, 0x100, 0xffff0000),
                             (0x20, 0x01ff8000, 0xfe007f00), (0x60, 0, 0x7fff00)):
            h.append(dict(regs=dict(up, d7=0x99aa0000 | d7), a6off=[(0x36, 4, l36), (0x3a, 4, l3a)]))
    if entry == 0xb41a6:
        h += [dict(a6off=[(0x7e, 4, v), (0x3a, 4, 0x7fffffff)]) for v in (1, 0xffffffff, 0x80000000)]
    if entry in (0xb41c2,):
        h += byte(0x15, (0x20, 0xdf, 0, 0xff))
    if entry == 0xb41cc:
        h += [dict(regs=dict(up), a6off=[(0x92, 1, b92), (0x97, 1, b97)]) for b92, b97 in ((0x80, 0), (0x7f, 4), (0xff, 0xc), (0, 0))]
    if entry == 0xb41d8:
        h += [dict(regs=dict(up), a6off=[(0x8e, 2, v), (0x82, 4, 0x12345678), (0x86, 4, 0x9abcdef0)]) for v in (0, 1, 0x100, 0x8000)]
    if entry in (0xb427e,):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry == 0xb4288:
        h += [dict(a6off=[(0x36, 4, v)]) for v in (0, 7, 8, 0x80000000, 0xfffffff8, 0xffffffff, 0x7fffffff)]
    if entry == 0xb42b0:
        h += [dict(regs=dict(up, d0=v)) for v in (0x12345600, 0x12345604, 0x1234560c, 0x100, 0x10c, 0xffffff04)]
    if entry == 0xb4abc:
        h += [dict(regs=dict(up), a6off=[(0x8c, 2, v)]) for v in (0, 0x8000, 0xffff)]
    if entry in (0xb4ac2, 0xb403e, 0xb411c):
        h += mirror
    if entry in (0xb67b8, 0xb6ccc, 0xb6dac, 0xb776e):
        h += [dict(regs=dict(up), a6off=[(0x8e, 2, v)]) for v in (0, 1, 3, 0x100)]
    if entry in (0xb67c4, 0xb6cd8, 0xb6db8, 0xb777a, 0xb6800, 0xb6d14, 0xb6df4, 0xb77b6):
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 1, 2, 7)]
    if entry == 0xb6cb0:
        for w, wa in ((0x10, 0x10), (0x11, 0x10), (0x10, 0x11), (0x8000, 0x7fff), (0x7fff, 0x8000), (0xffff, 0)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0), rec=[(0x42, 2, wa)], a6off=[(0x42, 2, w)]))
    if entry in (0xb6cbc, 0xb6cc6, 0xb7db2):
        h += byte(0x15, (0, 0xff, 1, 0xfe))
    if entry == 0xb6e8c:
        h += byte(0x9c, (0, 1, 2, 0xff))
    if entry == 0xb6e94:
        h += byte(0x9c, (1, 2, 0, 0x81))
    if entry == 0xb68a0:
        h += [dict(regrec=dict(a0=0), a6off=[(0x8e, 2, v)]) for v in (0, 1, 0x101)]
    if entry == 0xb774a:
        h += [dict(regs=dict(up), a6off=[(0x8e, 2, v)]) for v in (0, 1, 2, 3)]
    if entry == 0xb7d52:
        h += word(0x7c, (0, 1, 0x7fff, 0x8000, 0xffff))
    if entry == 0xb7d5a:
        h += [dict(regs=dict(up), a6off=[(0x7c, 2, v), (0x7e, 2, w)]) for v, w in ((1, 0x8000), (0x7fff, 0xffff), (0x8000, 1))]
    if entry == 0xb7d94:
        h += [dict(regs=dict(up), regrec=dict(a0=0))]
    if entry == 0xb7dc6:
        h += [dict(regs=dict(up, d2=v)) for v in (0x12340010, 0, 0x8000)]
    if entry == 0xbfc2a:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 1, 0x19, 0xa)]
    if entry == 0xbfc70 or entry == 0xbfc80:
        h += [dict(a6off=[(0x9e, 4, 0xbfdee + 8 * k)]) for k in (0, 1, 0x19)]
    if entry == 0xbfc90:
        h += [dict(a6off=[(0x19, 1, v), (0xa8, 1, w)]) for v, w in ((0x80, 0), (0x7f, 1), (0, 0x80))]
    if entry in (0xbfcaa,):
        h += byte(0xa8, (0, 1, 0x80, 0xff))
    if entry == 0xbfcb2:
        h += [dict(regs=dict(up), a6off=[(0xa6, 2, v)]) for v in (0, 0xfff8, 0x78, 0x7f8, 0x1234, 0x38, 0xb8)]
    if entry == 0xbfcce:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (1, 0, 0x101, 0x8000)]
    if entry == 0xbfcd0:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 0x100, 1, 0xff)]
    if entry == 0xbfcea:
        h += [dict(regs=dict(up, d0=v)) for v in (4, 0xfb, 0x104, 0xfffffffb)]
    if entry == 0xbfdbe:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 1, 0xf, 7)]
    if entry == 0xc5486:
        h += [dict(regs=dict(up), a6off=[(0x54, 2, v), (0x56, 4, 0)]) for v in (0x8000, 0x1234)]
    if entry == 0xc5496:
        h += byte(0x5e, (0x1a, 0x1b, 0, 6, 0xff, 0x80))
    if entry == 0xc54a6:
        h += [dict(regs=dict(up, d0=0x12345600 | v)) for v in (0, 6, 2, 9, 0x1a, 0x19)]
    if entry == 0xc5540:
        h += [dict(regs=dict(up), a6off=[(0x80, 2, v), (0x5e, 1, 0xff)]) for v in (0x8000, 0x1234)]
    if entry == 0xc5598:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x1f, 0x20, 0xffff, 0x12340001)]
    if entry == 0xcd7e2:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x80000000, 0xffffffff, 0x12345678)]
    if entry == 0xcd96c:
        h += [dict(regs=dict(up), a6off=[(0x8c, 2, v), (0x8a, 2, 0x1234)]) for v in (0, 1, 2, 3, 4, 5, 0xffff, 0x100)]
    if entry in (0xcd98e, 0xcd9b0, 0xcd9d2, 0xcd9f4):
        h += [dict(regs=dict(up, d0=v)) for v in (1, 2, 3, 4, 5, 0x10001, 0x10002, 0x10003, 0x10004)]
    if entry == 0xc5432:
        h += [dict(writes=[(0x4ca0, 2, v)]) for v in (0, 0x40)]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry in (0xb6874, 0xb6d6e, 0xb6e54, 0xb77fa, 0xc5476, 0xc5608):
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
    if entry in (0xb6ca2, 0xb6d82):
        # 49392: BYTE 568e(A5) bit (D0 & 1) with D0.B = BYTE 9d(A6) -> Set
        return dict(a6off=[(0x9d, 1, (0, 1, 2, 0x81)[t % 4])], a5off=[(0x568e, 1, (0, 1, 2, 3)[(t // 4) % 4])])
    if entry == 0xb687e:
        return dict(writes=[(0x4ca0, 2, (0, 0x15, 0x40, 0x14)[t % 4])])              # 28ae: D0 = 14 >= the free-node count WORD 104ca0 -> 290e (Clear)
    if entry == 0xb7d5a:
        return dict(writes=[(0x4ca0, 2, (0x40, 0x15, 0, 0x14)[t % 4])], a6off=[(0x7c, 2, 1)])   # 2986 (the Clear side 290e is the C++ caller-X error)
    if entry == 0xc5486:
        # 4b54e: LONG 56(A6) = 0 -> 4b6be; else the record (A3) walk
        return dict(a6off=[(0x56, 4, (0, 0x10e900, 0x10e000, 0)[t % 4])])
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
                continue                                    # 290e after 2986: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6); a direct 28ae failure (cdd86) is kept
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 15 bits 0 / 5 / 7, BYTE 95, BYTE 9c (b6e8c count), BYTE a8 (bfcaa), WORD a6 (the sine index), WORD 8e
            # (the table index 0..3), WORD 8c (the anim selector / TST), WORD 7c (b7d52), BYTE 5e (the c5496 guard), BYTE 9d (49392), LONG 26 (0: 49fc6
            # Set), LONG 36 / 3a / 7e (the spring and rotation), the handler LONGs 76 / 7a, BYTE 97 (the b42b8 table)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 1, 0x81, 0xff, 0x20, 0xa0)[t % 7]), (0x95, 1, (0, 4, 0x10, 0xff)[(t // 2) % 4]),
                               (0x9c, 1, (0, 1, 2, 8)[(t // 3) % 4]), (0xa8, 1, (0, 1, 0x80)[(t // 2) % 3]), (0xa6, 2, (0, 0x78, 0x1234, 0xfff8)[t % 4]),
                               (0x8e, 2, (0, 1, 2, 3)[(t // 4) % 4]), (0x8c, 2, (0, 1, 2, 3, 4, 5)[(t // 3) % 6]), (0x7c, 2, (0, 1, 0xffff, 0x8000)[(t // 4) % 4]),
                               (0x5e, 1, (0, 6, 2, 0x1b, 9)[t % 5]), (0x9d, 1, (0, 1)[(t // 2) % 2]), (0x36, 4, (0, 0x80000000, 0x100, 0xffffff00)[(t // 6) % 4]),
                               (0x3a, 4, (0, 0xfffc0000, 0x12345)[(t // 4) % 3]), (0x7e, 4, (0, 0x10000, 0xffff0000)[(t // 5) % 3]),
                               (0x76, 4, (0xb41be, 0xb403e, 0xb41be, 0xb42a2)[(t // 2) % 4]), (0x7a, 4, (0xb41be, 0xb403e, 0)[(t // 3) % 3]),
                               (0x97, 1, (0, 4, 0xc, 0)[(t // 5) % 4])] +
                        ([(0x26, 4, 0)] if t % 5 != 4 else []))
            st = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
                continue                                    # 290e after 2986: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6); a direct 28ae failure (cdd86) is kept
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
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a frame in which a node of the pool NATURAL_NODES holds one of NATURAL_ENTRIES as its
    callback LONG; declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the
    frame start.  Up to the sentinel or the first unrouted PC."""
    entries = set(NATURAL_ENTRIES)
    count = 0
    seen = set()
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        for a in range(NATURAL_NODES[0] & 0xffff, NATURAL_NODES[1] & 0xffff, 2):
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if cb not in entries or (cfg, case, frame, a) in seen:
                continue
            seen.add((cfg, case, frame, a))
            regs = dict(st0['regs'])
            regs.update(a5=0x108000, a6=0x100000 + a, a7=0x10ef00)
            st = U.make_state(ram, regs, cb, st0['bank'], st0['pvc'])
            st = U.with_host_writes(st, [(0xef00, 4, SENTINEL)])
            tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
                continue                                    # 290e after 2986: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6); a direct 28ae failure (cdd86) is kept
            record(tr['pcs'] + [tr['stop']])
            add_run(add, 'natural-%05x-%s%03d-f%d-%x' % (cb, cfg, case, frame, 0x100000 + a), st, tr,
                    dict(family='natural', entry=cb, config=cfg, case=case, frame=frame, node=0x100000 + a, stop=tr['stop'],
                         unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
            count += 1
    require(count >= 60, ('too few natural node fixtures', count))


def callee_fixtures(world, add, record):
    """The helpers, script callbacks and table entries as subroutines (return LONG = sentinel)."""
    for entry in CALLEES:
        flds = fields_of(entry)
        kept = {}
        hints = hint_worlds(entry, world)
        for t in range(60 + len(hints)):
            hint = hints[t] if t < len(hints) else None
            st = world.make(entry, SENTINEL, flds, hint)
            tr = trace(st, first_unrouted(), cap=400000)
            if tr is None or (0x290e in tr['pcs'] and 0x2986 in tr['pcs']):
                continue                                    # 290e after 2986: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6); a direct 28ae failure (cdd86) is kept
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
    err('odd-pc', U.with_host_writes(st, pc=0xb403f), 'unaligned animation machine PC', 0xb403f)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the computed jumps (contract decision 2): a JMP (A0) target that no ROM writer of LONG 76 produces, a b42b8 displacement other than 0 / 4 / c, a
    # c54b2 index above 1a (direct entry past the c5496 guard)
    for v in (0, 0xb41c2, 0xb4030, 0x10b41be, 0xc0926):
        err('b4030-target-%x' % v, U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 4, v)], pc=0xb4030), ERROR_JUMP, 0xb4030)
    for v in (8, 2, 0x10, 0xff):
        err('b42b0-d0-%x' % v, U.with_host_writes(st, regs=dict(d0=0x12345600 | v), pc=0xb42b0), ERROR_JUMP, 0xb42b0)
    for v in (0x1b, 0x40, 0xff):
        err('c54a6-d0-%x' % v, U.with_host_writes(st, regs=dict(d0=0x12345600 | v), pc=0xc54a6), ERROR_JUMP, 0xc54a6)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('70e42-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70e42), odd_word, 0x70e42)
    err('b4030-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb4030), odd_word, 0xb4030)
    err('b6d4c-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb6d4c), odd_write, 0xb6d4c, stop=0xb6d6a)
    err('cd92e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xcd92e), odd_write, 0xcd92e, stop=0xcd93c)
    err('b408c-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0xb408c), odd_word, 0xb408c)
    err('b7d94-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0xb7d94), odd_write, 0xb7d94)
    err('b42c8-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb42c8), odd_word, 0xb42c8)
    err('b7d5a-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb7d5a), odd_word, 0xb7d5a, stop=0x2986)
    err('b3e1c-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb3e1c), odd_word, 0xb3e1c, stop=0x8ff4)
    # failures after executed blocks: the later-unit stops (FR12 / FR13) and the TRAP boundary reached through the unit
    err('b3e46-then-b3e58', U.with_host_writes(st, [(a7 & 0xffff, 4, 0)], pc=0xb3e46), unrouted, 0xb3e58)
    err('b41d8-then-b41f2', U.with_host_writes(st, [((a6 + 0x8e) & 0xffff, 2, 1)], pc=0xb41d8), unrouted, 0xb41f2)
    err('b6d82-then-b6d90', U.with_host_writes(st, [((a6 + 0x9d) & 0xffff, 1, 0), ((a5 + 0x568e) & 0xffff, 1, 1)], pc=0xb6d82), unrouted, 0xb6d90)
    err('bfcea-then-bfcfa', U.with_host_writes(st, regs=dict(d0=4), pc=0xbfcea), unrouted, 0xbfcfa)
    err('b4030-then-b4036', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 4, 0xb4036)], pc=0xb4030), unrouted, 0xb4036)
    err('b42b0-then-b42bc', U.with_host_writes(st, regs=dict(d0=4), pc=0xb42b0), unrouted, 0xb42bc)
    err('c54a6-then-c54b2', U.with_host_writes(st, regs=dict(d0=0), pc=0xc54a6), unrouted, 0xc54b2)
    err('c5496-then-c54ba', U.with_host_writes(st, [((a6 + 0x5e) & 0xffff, 1, 2)], pc=0xc5496), unrouted, 0xc54ba)
    err('b42b0-then-b42c4', U.with_host_writes(st, regs=dict(d0=0xc), pc=0xb42b0), unrouted, 0xb42c4)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xb4064, 0xbfcb2, 0xb6cb0, 0xb4156)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
