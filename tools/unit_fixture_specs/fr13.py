"""V1 fixture spec of the area-D unit FR13 (engine/src/animation_machine_objects_fr13.cpp, 207 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr13-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 FR13 row): the
FR10 later-unit successors 70f60 (facing test -> BYTE 63) / 70fcc / 70ff8 (MOVE.L A0,(A6): the table 70d72 LONG written as the next callback) /
71028, the FR12 later-unit successors 71682 / 717c2, the table 70d72 callback 71622, the installs 717e8 / 71884, 719f8, 71f2c .. 72114 (705ca C, the
70302 result tested by 71fe2 TST.B D0 / 71fe4 BEQ, the signed LONG clamp 7209c .. 720c0, the EOR.W sign test 720e0), 7224c, the FR11 later-unit
successors b6d90 / bfcfa (2986 child bfd48), the FR11 table c54b2 entries c54ba / c54d6 -> c5520, c554c, the item handler b44ac (MOVEQ #5,D1; JSR
1c356; the RTS b450c passes the C), the FR4 table cc82e entry cc852, the animation tail cc8b4 (JSR cca76; JMP cc8de(PC,D0.W): the 27-entry BRA.W table,
only the executed entry cc8f6 is an FR13 block -> ccbc0), the interpreter callbacks cca5a / d159e (2986 child d15c4 .. d177a).  One computed jump of
its own (cc8da); the Z reader 71fe4 (the Z of the TST.B D0 of 71fe2, recomputed from D0.B by the C++).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR12, C1..C10) with declared host
edits.  This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the
'natural' family takes the frame-start states of that observation (state packs, read-only) in which a node of the pool 100800..104c00 holds an FR13
node entry (or a routed callback whose run reaches FR13 code: NATURAL_ENTRIES) as its callback LONG, keeps their RAM / PVC / bank and declares only
the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return LONG, PC = the callback).  The spec reads those packs itself (io_pack
below, observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 10 C consumers, the C pass b450c and the Z reader 71fe4 is entered directly (the seed world with declared
            edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers and the Z reader entered through their REAL producers (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the callbacks and installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the later-unit successors, table entries, handlers and callbacks entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 10 consumers, the jump-target error of cc8d2, odd node / stack /
            A0, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it
            differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR12, C1..C10
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR12, C1..C10)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'fr13'
ERROR_PC = 'unsupported animation objects fr13 PC'
ERROR_CARRY = 'objects fr13 caller requires known carry'
ERROR_JUMP = 'unsupported animation objects fr13 jump target'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x70f60, 0x70f84), (0x70fcc, 0x70fd2), (0x70ff8, 0x70ffa), (0x71028, 0x7102e), (0x71622, 0x716ca), (0x717c2, 0x717c8), (0x717e8, 0x71874),
          (0x71876, 0x718c8), (0x719f8, 0x71a80), (0x71f2c, 0x72118), (0x7224c, 0x722da), (0xb44ac, 0xb44b2), (0xb4506, 0xb450e), (0xb6d90, 0xb6dac),
          (0xbfcfa, 0xbfda0), (0xc54ba, 0xc54be), (0xc54d6, 0xc54da), (0xc5520, 0xc5540), (0xc554c, 0xc5592), (0xcc852, 0xcc856), (0xcc8b4, 0xcc8de),
          (0xcc8f6, 0xcc8fa), (0xcc94a, 0xcc94c), (0xcca5a, 0xcca76), (0xccbc0, 0xccc88), (0xd159e, 0xd1632), (0xd1636, 0xd177e)]
STARTS = sorted(int(x, 16) for x in (
    '70f60 70f74 70f7e 70fcc 70ff8 71028 71622 7162a 71652 71656 7167e 71682 71696 7169c 716a6 716ac 716b0 716b6 716bc 716c0 716c6 717c2 717e8 '
    '717f0 71818 7181c 71844 71858 71860 71876 71884 71888 7188e 71896 718a0 718a8 718ae 718b8 718c4 719f8 71a00 71a28 71a2c 71a54 71a62 71a68 '
    '71a6e 71a72 71a78 71a7c 71f2c 71f30 71f34 71f3a 71f42 71f4a 71f72 71f76 71f9e 71fac 71fb6 71fbc 71fc2 71fce 71fd0 71fd8 71fde 71fe2 71fe4 '
    '71fe8 71ff0 71ffa 72000 72008 7200e 72018 7201e 72026 7202c 72036 7203c 72040 72048 72070 72074 7209c 720b0 720b6 720c0 720c6 720d6 720e0 '
    '720f2 720f6 720fc 72102 72106 7210c 72114 7224c 72254 7227c 72280 722a8 722b6 722c0 722c6 722cc 722d0 722d6 b44ac b4506 b450c b6d90 b6d9c '
    'b6da6 bfcfa bfd10 bfd1a bfd2c bfd34 bfd3a bfd40 bfd42 bfd48 bfd70 bfd82 bfd88 bfd8e bfd94 bfd98 bfd9e c54ba c54d6 c5520 c5534 c553a c554c '
    'c5574 c557a c5580 c5586 c558a c5590 cc852 cc8b4 cc8bc cc8c0 cc8d2 cc8f6 cc94a cca5a cca6a cca6c ccbc0 ccbc8 ccbde ccbe2 ccbea ccc00 ccc04 '
    'ccc0c ccc22 ccc26 ccc2e ccc44 ccc48 ccc50 ccc66 ccc6a ccc80 d159e d15b4 d15be d15c4 d15fe d160c d161a d1636 d1644 d164e d1654 d166a d1670 '
    'd167c d1688 d1692 d1698 d16a2 d16a6 d16ac d16ae d16d6 d16fa d1704 d170a d170e d1724 d172a d172e d1736 d173c d1740 d1768 d176e d1774 d177a'
    ).split())
# the 10 C consumers: BCC 716bc 71a6e 72102 722cc bfd94 c5586 d172a d177a (49fc6), 71f30 (705ca), d16a2 (1ab80)
CONSUMERS = (0x716bc, 0x71a6e, 0x71f30, 0x72102, 0x722cc, 0xbfd94, 0xc5586, 0xd16a2, 0xd172a, 0xd177a)
CLEAR_SET = ()
SET_SET = ()
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x71fe2,)                   # TST.B D0 followed by the Z reader 71fe4: its block fixture stops at 71fe4 (no flag is compared at a stop)
INVERT_SET = ()
PASS_SET = (0xb450c,)                   # the RTS that returns the C of 1c356 to the FR2 item-handler consumer b46ac
STARTS_SET = set()
Z_READERS = (0x71fe4,)                  # BEQ.W on the Z of TST.B D0 (71fe2), recomputed from D0.B by the C++ (decision 4)
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
# no TRAP in FR13; the FR11 TRAP #15 b3e58 (b3e46) and the FR1 TRAP #15 b3eac that the FR11 handlers reached from FR13 (bfd34 -> b4030) may pass:
# boundaries
TRAPS = (0xb3e58, 0xb3eac)
# PCs of later units that an FR13 block reaches by a fall-through or a branch (FR14 71874 d1632 d177e), the still unrouted later-unit stops of the
# FR12 blocks (fr12 UNIT_EXITS that FR13 does not route: FR14 7177a 71786; FR11 and FR10 have none left) and of the C1..C9 blocks (pc10
# EXIT_STOPS[:12]).  Declared stops of the native runs: a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x71874, 0xd1632, 0xd177e, 0x7177a, 0x71786,
              0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6, 0x4e69a)
UNIT_EXITS = EXIT_STOPS[:3]             # the FR13 later-unit stops (FR14)
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the flag chain 71fe2 -> 71fe4 (Z of TST.B D0)
# and 71fde -> 71fe4 (D0 of 70302)
CHAINS = ((0x716b6, 0x716bc), (0x71a68, 0x71a6e), (0x71f2c, 0x71f30), (0x720fc, 0x72102), (0x722c6, 0x722cc), (0xbfd8e, 0xbfd94), (0xc5580, 0xc5586),
          (0xd1698, 0xd16a2), (0xd1724, 0xd172a), (0xd1774, 0xd177a), (0x71fe2, 0x71fe4), (0x71fde, 0x71fe4))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# the computed jump of FR13 (contract decision 2): JMP cc8de(PC,D0.W) cc8da (index 0..1a after the cc8c0 guard); any other target is the C++ checked
# jump-target error (a native run that jumps elsewhere is not a fixture world); an allowed target that is not an FR13 block (every entry but cc8f6)
# is a stop
TABLE_CC8DE = tuple(0xcc8de + 4 * k for k in range(0x1b))
JUMP_TARGETS = {0xcc8da: TABLE_CC8DE}
JUMP_PCS = (0xcc8da,)
JUMP_ROUTED = ()
LIST_JUMPS = {}
# computed jumps that the FR13 runs reach (FR11 b4034 / b42b4 / c54ae, FR1 b3dc8 b3f3e b3fc4 b3fca through the item handlers, FR2 b46aa (item
# handler JSR (A1)), FR4 cc7a8 / cc82a, the interpreter JSR (A1) 4a352 / 4a43c, the C3 .. C10 list): an unrouted target is a stop even when it is
# the straight-line successor
OTHER_JUMP_PCS = (0xb4034, 0xb42b4, 0xc54ae, 0xb3dc8, 0xb3f3e, 0xb3fc4, 0xb3fca, 0xb46aa, 0xcc7a8, 0xcc82a, 0x4a352, 0x4a43c, 0x2031c, 0x201a6, 0x21620,
                  0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36, 0x2224c, 0x22428, 0x21e10, 0x2229a,
                  0x22378, 0x203ac)
TABLE_ENTRIES = ()
# the callbacks and installed values entered as node callbacks: 71622 (the LONG table 70d72 entry 4: FR2b 70d22, N15 711e6, FR13 70ff8), the
# in-range installs entered at once 71696 71884 71a62 71fac 720d6 722b6 bfd2c bfd88 c557a d1644 d16fa d176e (also the next frame's callback), the
# written-only installs 717e8 (717c2) 719f8 (718b8, routed-out 719a4 / 719ee) 71f2c (FR12 71f22, 72106) 72040 (71fd8, U13 7093e) 7224c (71ffa / 72008
# / 72036) c554c (c5534, FR3 c542a / c568e) d16ae (d164e) d1740 (d1736), and the 2986 children bfd48 (bfcfa) / d15c4 (d159e) entered with A6 = the
# child node
NODE_ENTRIES = (0x71622, 0x71696, 0x717e8, 0x71884, 0x719f8, 0x71a62, 0x71f2c, 0x71fac, 0x72040, 0x720d6, 0x7224c, 0x722b6, 0xbfd2c, 0xbfd48, 0xbfd88,
                0xc554c, 0xc557a, 0xd15c4, 0xd1644, 0xd16ae, 0xd16fa, 0xd1740, 0xd176e)
# the natural family also takes the routed callbacks whose code leads into FR13 (NATURAL_ROUTED): the FR1 item child b3dbc (its contact handler b44ac
# and its kind handler path FR11 bfcea -> bfcfa), the FR10 nodes 70e2a / 70f3e / 71468 / 713d8 (70f4e -> 70f60, 70fc2 -> 70fcc, 70ff0 -> 70ff8, 71020
# -> 71028), the FR11 nodes c5470 / c5432 (c5496 -> the c54b2 entries c54ba / c54d6) and b6d6a / b6d82 (b6d8c -> b6d90), the FR12 nodes 71502 / 716ca
# / 7179a (7155e -> 71682, 717ae -> 717c2)
NATURAL_ROUTED = (0xb3dbc, 0x70e2a, 0x70f3e, 0x71468, 0x713d8, 0xc5470, 0xc5432, 0xb6d6a, 0xb6d82, 0x71502, 0x716ca, 0x7179a)
NATURAL_ENTRIES = NODE_ENTRIES + NATURAL_ROUTED
# the later-unit successors, table entries, handlers, callbacks and helpers entered as subroutines (return LONG = sentinel)
CALLEES = (0x70f60, 0x70fcc, 0x70ff8, 0x71028, 0x71682, 0x717c2, 0xb6d90, 0xbfcfa, 0xc54ba, 0xc54d6, 0xc5520, 0xcc852, 0xcc8f6, 0xb44ac, 0xb4506,
           0xcc8b4, 0xcc8c0, 0xcc8d2, 0xcca5a, 0xd159e, 0xccbc0, 0x7209c, 0x720b6, 0x720e0, 0x71fc2, 0x71fde, 0x71860, 0xd161a, 0xd1670, 0xd172e)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x76, 0x7a)   # node links, pointer fields, the handler LONGs 76 / 7a (FR11 b4034 through bfd34 -> b4030)
# natural worlds of the extended observation: (config, case, frame) with a pool node holding an FR13 node entry or a NATURAL_ROUTED callback (scratch
# natscan_fr13.py: per run and callback the first frame, the middle one of the first eight and the last one)
NATURAL = (('X1', 68, 508), ('X1', 68, 546), ('X1', 68, 606), ('X1', 68, 607), ('X1', 68, 610), ('X1', 68, 613), ('X1', 68, 660), ('X1', 68, 663),
           ('X1', 68, 689), ('X1', 68, 707), ('X1', 68, 708), ('X1', 68, 796), ('X1', 68, 797), ('X1', 68, 800), ('X1', 68, 807), ('X1', 68, 828),
           ('X1', 68, 852), ('X1', 68, 873), ('X1', 68, 885), ('X1', 94, 292), ('X1', 94, 330), ('X1', 94, 451), ('X1', 94, 459), ('X1', 94, 462),
           ('X1', 94, 465), ('X1', 94, 475), ('X1', 94, 476), ('X1', 94, 479), ('X1', 94, 488), ('X1', 94, 506), ('X1', 94, 507), ('X1', 94, 605),
           ('X1', 94, 616), ('X1', 94, 621), ('X1', 94, 622), ('X1', 94, 660), ('X1', 94, 678), ('X1', 94, 726), ('X2', 68, 508), ('X2', 68, 546),
           ('X2', 68, 647), ('X2', 68, 684), ('X2', 68, 687), ('X2', 68, 701), ('X2', 68, 702), ('X2', 68, 705), ('X2', 68, 713), ('X2', 68, 731),
           ('X2', 68, 732), ('X2', 68, 818), ('X2', 68, 819), ('X2', 68, 822), ('X2', 68, 829), ('X2', 68, 889), ('X2', 68, 940), ('X2', 94, 286),
           ('X2', 94, 324), ('X2', 94, 479), ('X2', 94, 480), ('X2', 94, 483), ('X2', 94, 484), ('X2', 94, 485), ('X2', 94, 488), ('X2', 94, 501),
           ('X2', 94, 506), ('X2', 94, 507), ('X2', 94, 510), ('X2', 94, 512), ('X2', 94, 513), ('X2', 94, 667), ('X2', 94, 684), ('X2', 94, 689),
           ('X2', 94, 690), ('X2', 94, 693), ('X2', 94, 705), ('X2', 94, 706), ('X2', 94, 709), ('X2', 94, 713), ('X2', 94, 715), ('X2', 94, 716),
           ('X2', 94, 717), ('X2', 94, 718), ('X2', 94, 720), ('X2', 94, 868), ('X2', 94, 869), ('X2', 94, 870), ('X2', 94, 873), ('X2', 94, 874),
           ('X3', 68, 510), ('X3', 68, 548), ('X3', 68, 629), ('X3', 68, 632), ('X3', 68, 676), ('X3', 68, 677), ('X3', 68, 761), ('X3', 68, 762),
           ('X3', 68, 765), ('X3', 68, 766), ('X3', 68, 793), ('X3', 68, 794), ('X3', 68, 795), ('X3', 68, 796), ('X3', 68, 799), ('X3', 68, 814),
           ('X3', 68, 831), ('X3', 68, 832), ('X3', 68, 835), ('X3', 68, 1078), ('X3', 68, 1241), ('X3', 68, 1242), ('X3', 68, 1245),
           ('X3', 68, 1257), ('X3', 68, 1289), ('X3', 68, 1291), ('X3', 68, 1292), ('X3', 68, 1295), ('X3', 68, 1307), ('X3', 68, 1308),
           ('X3', 68, 1311), ('X3', 68, 1315), ('X3', 68, 1317), ('X3', 68, 1321), ('X3', 68, 1322), ('X3', 68, 1323), ('X3', 68, 1326),
           ('X3', 68, 1331), ('X3', 68, 1333), ('X3', 68, 1392), ('X3', 68, 1474), ('X3', 68, 1475), ('X3', 68, 1476), ('X3', 68, 1479),
           ('X3', 68, 1480), ('X3', 68, 1518), ('X3', 94, 290), ('X3', 94, 328), ('X3', 94, 377), ('X3', 94, 433), ('X3', 94, 436), ('X3', 94, 437),
           ('X3', 94, 440), ('X3', 94, 449), ('X3', 94, 480), ('X3', 94, 481), ('X3', 94, 584), ('X3', 94, 585), ('X3', 94, 588), ('X3', 94, 589),
           ('X3', 94, 590), ('X3', 94, 593), ('X3', 94, 608), ('X3', 94, 657), ('X3', 94, 949), ('X3', 94, 958), ('X3', 94, 959), ('X3', 94, 960),
           ('X3', 94, 961), ('X3', 94, 964), ('X3', 94, 965), ('X3', 94, 1075), ('X3', 94, 1076), ('X3', 94, 1078), ('X3', 94, 1298),
           ('X4', 68, 510), ('X4', 68, 548), ('X4', 68, 597), ('X4', 68, 620), ('X4', 68, 753), ('X4', 68, 756), ('X4', 68, 773), ('X4', 68, 774),
           ('X4', 68, 775), ('X4', 68, 776), ('X4', 68, 777), ('X4', 68, 780), ('X4', 68, 782), ('X4', 68, 792), ('X4', 68, 800), ('X4', 68, 801),
           ('X4', 68, 802), ('X4', 68, 875), ('X4', 68, 880), ('X4', 68, 929), ('X4', 68, 1082), ('X4', 68, 1136), ('X4', 68, 1139),
           ('X4', 68, 1154), ('X4', 68, 1171), ('X4', 68, 1172), ('X4', 68, 1173), ('X4', 94, 350), ('X4', 94, 388), ('X4', 94, 437),
           ('X4', 94, 463), ('X4', 94, 593), ('X4', 94, 594), ('X4', 94, 595), ('X4', 94, 596), ('X4', 94, 598), ('X4', 94, 609), ('X4', 94, 610),
           ('X4', 94, 611), ('X4', 94, 613), ('X4', 94, 614), ('X4', 94, 617), ('X4', 94, 622), ('X4', 94, 632), ('X4', 94, 640), ('X4', 94, 641),
           ('X4', 94, 715), ('X4', 94, 716), ('X4', 94, 727), ('X4', 94, 921), ('X4', 94, 975), ('X4', 94, 976), ('X4', 94, 979), ('X4', 94, 994),
           ('X4', 94, 1011), ('X4', 94, 1012), ('X4', 94, 1013))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
REINSTALL = ()

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xf, 0x10, 0x1a, 0x1b, 0x1f, 0x20, 0x3f, 0x40, 0x41, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xef, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 0xa, 0xf, 0x10, 0x11, 0x18, 0x1f, 0x20, 0x3f, 0x40, 0x7f, 0x80, 0xbf, 0xc0, 0x100, 0x1800, 0x17ff, 0x7fff, 0x8000, 0x8001,
      0x9800, 0x97ff, 0xc000, 0xffe0, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x18000, 0x40000, 0x100000, 0x300000, 0x300020, 0x7fffffff, 0x80000000, 0xfff00000, 0xfffd0000,
      0xffff0000, 0xffffffe0, 0xffffffff, 0x12345678)
# the handlers that the ROM writers of LONG 76(A6) produce for the FR11 JMP (A0) b4034 (FR11 decision 2), reached through bfd34 JSR b4030
HANDLERS = (0xb41be, 0xb4036, 0xb42a2, 0xb403e, 0xc0924, 0xb4294)
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
# no flag-sharing Bcc pair inside one FR13 block (71fe2 / 71fe4 are their own blocks: decision 4)
BUNDLED = ()
THREAD = {}


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 70f7e / 70fcc / 70ff8 / 71028 into FR10, 717c2 into FR12 717c8, b6da6 into
    FR11 b6dac, 71860 / d161a into the later-unit stops); a Bcc followed by a BUNDLED Bcc continues the block (none in FR13)."""
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
    """Static successors of the entry block (None = computed: RTS, JSR (A1), JMP (A1)); a taken BEQ to a bundled BEQ continues at its target."""
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
    its end; an earlier PC when a Bcc of a bundled pair is taken), skipping a bundled BEQ reached by a taken BEQ (c113a / c11ec), or the stop."""
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
        if pc in STARTS_SET or (pc in THREAD and target(decode(prev).op_str) == pc):
            return False
        ins = decode(prev)
        return pc != prev + (ins.size if ins is not None else size)
    return outside


def first_unrouted(extra=()):
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at an unrouted target of
    the computed jumps that the FR13 runs reach (OTHER_JUMP_PCS: FR11 b4034 / b42b4 / c54ae, FR1, FR2 b46aa, FR4 cc7a8 / cc82a, the interpreter and
    the C3 .. C10 list), at a target of the FR13 computed jump cc8da that is not an FR13 block (JUMP_PCS), or at
    the first unrouted PC that is not the straight-line successor of the previous instruction (a PC inside a block of another executor is not a block
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it: LONG 76(A6) one of the handlers that the ROM writers
        of the FR11 JMP (A0) b4034 produce (FR11 decision 2; reached through bfd34 JSR b4030), BYTE 97(A6) 0 / 4 / c (the FR11 b42b8 table), the
        index D0.B of the computed jump cc8d2 0..1a mostly (a larger one is the C++ checked jump-target error and leaves the native table), A0 a RAM
        record at b6d90 (WORD 42(A0)) and cca5a (WORD (A0)), D7.W near 1800 at 70f60, LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter),
        BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 10fd82 = 0, WORD 90(A6) a multiple of 4 below 18 (the routed FR2 b4aca reads the LONG table b4ad4 by
        it after b4958; an odd index faults natively), WORD 8e(A6) 0..7 mostly (FR13 b6d90 runs on into FR11 b6dac, whose table anim reads the ROM
        LONG table b7fc4 by it; the hints of 71fc2 / 7209c set WORD / LONG 8e themselves)."""
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
                                     0x12340001, 0xffffffff, 0x3fff, 0x4000, 0xc000, 0xf000))
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0xffff0000, 0x12345600, 0xffffff00, 0xc000))
        if rng.random() < 0.4:
            regs['d4'] = rng.choice((0x40, 0xc0, 0x12345640, 0x99aa00c0, 0, 0x80, 0xff, 0x3f, 0x41, 0xbf, 0xc1, 0x7f))
        if rng.random() < 0.4:
            regs['d7'] = rng.choice((0, 1, 0x100, 0x7fff, 0x8000, 0xffff, 0x1234ff00, 0xc000))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.3 else self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        if entry == 0xcc8d2 and rng.random() < 0.8:
            regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x1b)
        if entry == 0x70f60 and rng.random() < 0.6:
            regs['d7'] = (regs['d7'] & 0xffff0000) | rng.choice((0x1800, 0x17ff, 0x9800, 0x97ff, 0, 0xffff, 0x8000))
        if entry in (0xb6d90, 0xcca5a) and rng.random() < 0.7:
            regs['a0'] = rec + 0x20
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924))))   # LONG 76(A6): a handler
        if rng.random() < 0.5:
            writes.append(((a6 + 0x7a) & 0xffff, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e))))   # LONG 7a(A6) (FR11 b3e1c)
        writes.append(((a6 + 0x97) & 0xffff, 1, rng.choice((0, 4, 0xc, 0xc))))                     # BYTE 97(A6): the kind-record value 0 / 4 / c
        writes.append(((a6 + 0x90) & 0xffff, 2, rng.choice((0, 4, 8, 0xc, 0x10, 0x14))))           # WORD 90(A6): the FR2 b4aca LONG table b4ad4 index
        if rng.random() < 0.8:
            writes.append(((a6 + 0x8e) & 0xffff, 2, rng.choice((0, 0, 1, 2, 3, 4, 5, 6, 7))))     # WORD 8e(A6): the index of the FR11 / FR12 ROM LONG tables (b6dac)
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
            if reg == 6 and (disp in POINTERS or disp in (0x76, 0x77, 0x78, 0x79, 0x8e, 0x8f, 0x90, 0x91, 0x97)):
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
    require(len(STARTS) == 207 and len(STARTS_SET) == 207, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr13_block', ('start is not routed to objects fr13', hex(s), unit_of(s)))
    for z in Z_READERS:
        require(z in STARTS_SET, ('Z reader is an FR13 start', hex(z)))
    # the computed jump of FR13 (decision 2): the only FR13 block among the 27 table entries is cc8f6 (entry 6); every other entry stays unrouted (a
    # stop) until a later unit routes it
    for jmp, targets in JUMP_TARGETS.items():
        require(jmp not in STARTS_SET and mine(jmp), ('the jump instruction is inside an FR13 block', hex(jmp)))
        for t in targets:
            require(t in STARTS_SET or unit_of(t) is None, ('computed-jump target must be an FR13 start or unrouted', hex(jmp), hex(t), unit_of(t)))
    require(set(t for ts in JUMP_TARGETS.values() for t in ts) & STARTS_SET == {0xcc8f6}, 'the FR13 jump targets')
    # the computed-jump entries of earlier units that FR13 routes: the FR11 table c54b2 entries 2 / 9 (c54ba / c54d6) and the FR4 table cc82e entry 9
    # (cc852); the other c54b2 entries stay unrouted stops (c54ca is FR11)
    for t in (0xc54ba, 0xc54d6, 0xcc852):
        require(unit_of(t) == 'animation_objects_fr13_block', ('computed-jump target routed to FR13', hex(t)))
    for t in (0xc54b2, 0xc54be, 0xc54d2):
        require(unit_of(t) is None, ('FR11 table entry stays unrouted', hex(t)))
    rng = random.Random(0xF13A)
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
    sys.stderr.write('fr13 spec: %d fixtures (%d natural), visited %d/207, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr13: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr13: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the SUBI.W #1800 / SEQ /
    EXT / EOR.W sign of 70f60, WORD 9c of the bank-anim selections, WORD 7a of 71682, the ADD.W / EXT.L / ADDI.L of 71860, the WORD 3a sign of 7188e,
    the BYTE 6 compare of 718a0, BYTE 15 bit 3 of 718b8, the WORD 88 add / count of 71f3a / 72000, the WORD 8e - 42 sign and the unsigned 10 of
    71fc2 .. 71fd0, the 70302 result BYTE of 71fe2 / 71fe8, BYTE 82 bits 0 / 7, WORD 7c, BYTE 6f (40), the signed LONG clamp of 7209c / 720b6 (18000
    / fffe8000 after ASR.L #5), the SNE / MOVE.B / EOR.W WORD sign of 720e0, WORD 8a count of 7210c, the signed WORD compare of b6d90, BYTE 1a / WORD
    a4 count of bfd1a / bfd2c, BYTE 61 bit 7 of c5520, BYTE 5e (0 / 1a / 1b) of cc8b4 / cc8c0 and the index of cc8d2, the WORD (A0) / SWAP / NEG of
    cca5a, WORD 8c (0..5) of ccbc0, WORD 32 / 2e of d161a / d1636, LONG 3a of d1654 / d170e, WORD 10000e & 3 and BYTE 14 / 19 / 1a of d1670 /
    d167c, WORD 76 count of d172e, the BYTE 15 bits), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every
    hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x70f60, 0x71682, 0x71860, 0x7188e, 0x71f3a, 0x71fc2, 0x72000, 0x7209c, 0x720c6, 0x720e0, 0x720f2, 0x7210c, 0xb6d90, 0xbfd1a, 0xbfd2c,
                 0xc5520, 0xcc8b4, 0xcc8c0, 0xcc8d2, 0xcca5a, 0xccbc0, 0xd161a, 0xd1636, 0xd1654, 0xd1670, 0xd167c, 0xd16d6, 0xd170e, 0xd172e, 0x71844,
                 0x71876, 0x70ff8):
        h += [dict(regs=dict(up))] + mirror
    if entry == 0x70f60:
        for d7, b in ((0x1800, 0), (0x1800, 1), (0x17ff, 0), (0x17ff, 1), (0x9800, 0), (0x97ff, 1), (0x12340000, 0), (0xffff, 1), (0x8000, 0)):
            h.append(dict(regs=dict(up, d7=(0x55660000 | d7) if d7 < 0x10000 else d7), a6off=[(0x15, 1, b)]))
    if entry in (0x71622, 0x717e8, 0x719f8, 0x71f42, 0x72040, 0x7224c):
        h += word(0x9c, (0, 1, 0x8000, 0x100))
    if entry == 0x71682:
        h += [dict(regs=dict(up), a6off=[(0x7a, 2, v), (0x64, 4, 0x12345678)]) for v in (0, 0x8000, 0xffff)]
    if entry in (0x7169c, 0x718ae, 0x71fac, 0x722b6, 0xd1644, 0xd16fa, 0x71876, 0x71884):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry == 0x71860:
        for d0, d1, b in ((0x7fff, 1, 0), (0xffff, 1, 1), (0x8000, 0x8000, 0), (0x12340001, 0xabcd0002, 1), (0xfffe, 0xffff, 0), (0, 0, 1)):
            h.append(dict(regs=dict(up, d0=d0, d1=d1), a6off=[(0x15, 1, b)]))
    if entry == 0x71858:
        h += [dict(regs=dict(up, d0=v)) for v in (0x8000, 0x12347fff)]
    if entry == 0x7188e:
        h += word(0x3a, (0, 0x7fff, 0x8000, 0xffff))
    if entry == 0x718a0:
        h += [dict(regs=dict(up, d0=v)) for v in (6, 0x106, 7, 0, 0xffffff06)]
    if entry == 0x718b8:
        h += byte(0x15, (0x08, 0xff, 0xf7, 0x88))
    if entry == 0x71f3a:
        for d0, w in ((0x1f, 0xffff), (0x20, 0), (0xffff, 0x7ff0), (0x12345601, 0x8000)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x88, 2, w)]))
    if entry == 0x71fc2:
        for w8e, w42 in ((0x8000, 0), (0x10, 0), (0, 0x10), (0x7fff, 0xffff), (0, 0), (0x8000, 0x7ff1), (0xf, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x8e, 2, w8e), (0x42, 2, w42)]))
    if entry == 0x71fce:
        h += [dict(regs=dict(up, d0=v)) for v in (0x8000, 0xfff0, 0x12340001, 0xfff1)]
    if entry == 0x71fd0:
        h += [dict(regs=dict(up, d0=v)) for v in (0xf, 0x10, 0xffff, 0x1234000f, 0xffff0010)]
    if entry in (0x71fe2, 0x71fe8):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 2, 0x100, 0xff, 0x101)]
    if entry == 0x72000:
        h += word(0x88, (0, 1, 0x8000, 0x8001))
    if entry == 0x7200e:
        h += byte(0x82, (0, 1, 0xfe, 0xff))
    if entry == 0x7201e:
        h += word(0x7c, (0, 1, 0x100, 0x8000))
    if entry == 0x7202c:
        h += byte(0x6f, (0x40, 0x41, 0xc0, 0))
    if entry == 0x7209c:
        for l8e, l42 in ((0x300000, 0), (0x300020, 0), (0x30001f, 0), (0, 0x300000), (0, 0x300020), (0, 0x30001f), (0x7fffffff, 0xffffffff),
                         (0x80000000, 1), (0x12345678, 0x12345678), (0xffffffe0, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x8e, 4, l8e), (0x42, 4, l42)]))
    if entry == 0x720b6:
        h += [dict(regs=dict(up, d0=v)) for v in (0xfffe8000, 0xfffe7fff, 0x7fffffff, 0x80000000, 0)]
    if entry == 0x720d6:
        h += byte(0x82, (0x80, 0x7f, 0, 0xff))
    if entry == 0x720e0:
        for b15, b64, d0, d1 in ((0, 0x80, 0x12340000, 0x56780000), (1, 0x80, 0x12340000, 0x56780000), (0, 0x7f, 0x1234ff00, 0x56780000),
                                 (1, 0x7f, 0x12348000, 0x567800ff), (0, 0, 0x00008000, 0x00008000), (1, 0xff, 0x7f00, 0x8000), (0, 0x40, 0, 0)):
            h.append(dict(regs=dict(up, d0=d0, d1=d1), a6off=[(0x15, 1, b15), (0x64, 1, b64)]))
    if entry == 0x720f2:
        h += [dict(a6off=[(0x64, 4, v)]) for v in (0, 0x80000000, 0x18000, 0xfffe8000)]
    if entry == 0x7210c:
        h += word(0x8a, (1, 0, 2, 0x8001))
    if entry == 0xb6d90:
        for w6, w0 in ((0x8000, 0x7fff), (0x7fff, 0x8000), (5, 5), (0, 0xffff), (0xffff, 0), (6, 5)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x62, 2, w0)], a6off=[(0x42, 2, w6)]))
    if entry in (0xb6d9c, 0xb6da6, 0xd161a):
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0xbfd1a:
        h += byte(0x1a, (0, 0x80, 0xff))
    if entry == 0xbfd2c:
        h += word(0xa4, (0, 1, 2, 0x8000, 0x8001))
    if entry == 0xc5520:
        h += byte(0x61, (0x80, 0x7f, 0, 0xff))
    if entry == 0xcc8b4:
        h += byte(0x5e, (0, 1, 0x1a, 0x1b, 0xff))
    if entry == 0xcc8c0:
        h += [dict(regs=dict(up), a6off=[(0x5e, 1, v), (0x5f, 1, 0x5a)]) for v in (0x1a, 0x1b, 6, 0, 0xff, 0x80)]
    if entry == 0xcc8d2:
        h += [dict(regs=dict(up, d0=v)) for v in (6, 0x12340006, 0x106, 0xffff0006, 0, 0x1a)]
    if entry == 0xcca5a:
        for w, b in ((0, 0), (0x8000, 0), (0x8000, 1), (0x7fff, 0), (1, 1), (0xffff, 0)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x20, 2, w)], a6off=[(0x15, 1, b)]))
    if entry in (0xccbc0, 0xccbe2, 0xccc04, 0xccc26, 0xccc48):
        h += [dict(regs=dict(up), a6off=[(0x8c, 2, v)]) for v in (0, 1, 2, 3, 4, 5, 0x100, 0xffff)]
        if entry != 0xccbc0:
            h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (1, 2, 3, 4, 0x101)]
    if entry == 0xd161a:
        h += [dict(regs=dict(up), a6off=[(0x32, 2, v), (0x15, 1, b)]) for v, b in ((0xffe8, 0), (0xffff, 1), (0x7ff0, 0))]
    if entry == 0xd1636:
        h += [dict(regs=dict(up, d0=v, d1=0x18000), a6off=[(0x2e, 2, w)]) for v, w in ((0x18, 0xffe8), (0x18, 0xffff), (0xffe8, 0x10))]
    if entry in (0xd1654, 0xd170e):
        h += [dict(regs=dict(up), a6off=[(0x3a, 4, v)]) for v in (0, 0xfff00000, 0xfff40000, 0x7fffffff, 0x80000000, 0xfff0001f, 0x20)]
    if entry == 0xd1670:
        h += [dict(regs=dict(up), writes=[(0x000e, 2, v)]) for v in (0, 1, 2, 3, 4, 0xfffc)]
    if entry == 0xd167c:
        for b14, b19, b1a in ((5, 5, 7), (5, 6, 7), (0x80, 0x80, 0), (0, 0xff, 1)):
            h.append(dict(regs=dict(up), a6off=[(0x14, 1, b14), (0x19, 1, b19), (0x1a, 1, b1a)]))
    if entry == 0xd172e:
        h += word(0x76, (0, 1, 0x8000, 0xffff))
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry in (0x716b6, 0x71a68, 0x720fc, 0x722c6, 0xbfd8e, 0xc5580, 0xd1724, 0xd1774):
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
    if entry == 0x71f2c:
        # 705ca: BYTE 82 bit 1, BYTE 6f = 40, then 4bc04: WORD 42 = 100 / WORD 46 = 100 select the map WORD 5b88(A5) + 72 (A5 = 108000: 10dbfa);
        # >= 40 -> Set
        return dict(a6off=[(0x82, 1, (0, 2, 2, 2)[t % 4]), (0x6f, 1, (0x40, 0x40, 0x41, 0x40)[(t // 4) % 4]), (0x42, 2, 0x100), (0x46, 2, 0x100)],
                    writes=[(0xdbfa, 2, (0x80, 0x10, 0x200, 0x3f)[(t // 2) % 4])])
    if entry == 0xd1698:
        return None                                                                  # 1ab80: the screen test of the record d13a4 (node position)
    if entry == 0x71fe2:
        return dict(regs=dict(d0=(0, 1, 2, 0x100, 0xff, 0x12345600)[t % 6]))         # TST.B D0 -> the Z of 71fe4
    if entry == 0x71fde:
        # 70302 (FR2b): WORD 78 = 0, BYTE 82 bit 3, BYTE 86 >= 0, the 494c0 box test (record 702fa against WORD 42 / 46), BYTE 87 and the random 49a84
        # decide its D0 (0 .. 7)
        return dict(a6off=[(0x78, 2, (0, 0, 1, 0)[t % 4]), (0x82, 1, (0x08, 0x48, 0x08, 0)[(t // 4) % 4]), (0x86, 1, 0), (0x87, 1, (0xff, 0x0f, 0x81)[t % 3]),
                           (0x15, 1, (0x80, 0)[(t // 2) % 2]), (0x42, 2, (0xa0, 0x100, 0x60, 0x140)[(t // 3) % 4]), (0x46, 2, (0x100, 0x180, 0xc0, 0x1c0)[(t // 5) % 4])])
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


D1XXX = (0xd15c4, 0xd1644, 0xd16ae, 0xd16fa, 0xd1740, 0xd176e)   # the d15c4 child nodes: WORD 76 is a count (d16d6 / d172e), not the b4030 handler


def node_fixtures(world, add, record):
    """Installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 15 bits 0 / 7, BYTE 61 bit 7, BYTE 82 bits 0 / 7, BYTE 6f (40), BYTE 5e, BYTE 14 / 19 / 1a, WORD 9c
            # (the bank-anim selection), WORD 7c / 88 / 8a / 8c / a4 / 76 (counts and selections), LONG 26 (0: 49fc6 Set), LONG 36 / 3a / 64 / 8e /
            # 42, the handler LONG 76 (bfd34 -> b4030), BYTE 97 (the FR11 b42b8 table)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 1, 0x81, 0xff, 0x7f, 0xfe)[t % 7]), (0x61, 1, (0, 0x80, 0xff)[(t // 2) % 3]),
                               (0x82, 1, (0, 0x80, 1, 0x81, 2)[(t // 3) % 5]), (0x6f, 1, (0x40, 0, 0x40)[(t // 2) % 3]), (0x5e, 1, (0, 6, 0x1b, 3)[(t // 3) % 4]),
                               (0x19, 1, (0, 1)[(t // 4) % 2]), (0x9c, 2, (0, 1, 0, 0x100)[(t // 5) % 4]), (0x7c, 2, (0, 1)[(t // 3) % 2]),
                               (0x88, 2, (0, 1, 0x20)[(t // 2) % 3]), (0x8a, 2, (1, 2, 0x18)[(t // 4) % 3]), (0x8c, 2, (0, 1, 2, 3, 4, 5)[(t // 2) % 6]),
                               (0xa4, 2, (0, 1, 2)[(t // 3) % 3]), (0x36, 4, (0, 0x80000000, 0x100000, 0xfff00000)[(t // 6) % 4]),
                               (0x3a, 4, (0, 0xfffc0000, 0x12345, 0x8000)[(t // 4) % 4]), (0x64, 4, (0, 0x40000, 0xfffc0000, 0x10000)[(t // 5) % 4]),
                               (0x8e, 4, (0, 0x300000, 0x10000, 0x80000000)[(t // 3) % 4]), (0x42, 4, (0, 0x100000, 0xfff00000)[(t // 4) % 3]),
                               (0x76, 4, ((0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924, 0xb4036) if entry not in D1XXX else (0, 1, 0x10000, 0xb41be))[(t // 2) % 4]),
                               (0x97, 1, (0, 4, 0xc, 0)[(t // 5) % 4])] +
                        ([(0x26, 4, 0)] if t % 5 != 4 else []), writes=[(0x4ca0, 2, (0x40, 0x40, 0x15)[t % 3]), (0xd68e, 1, (0, 1)[(t // 3) % 2]),
                                                                        (0x000e, 2, (0, 1, 3)[(t // 2) % 3])])
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
    err('odd-pc', U.with_host_writes(st, pc=0xccbc1), 'unaligned animation machine PC', 0xccbc1)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the computed jump cc8da entered at cc8d2 past the cc8c0 guard with an index above 1a: the checked jump-target error (decision 2)
    err('cc8d2-jump-target-1b', U.with_host_writes(st, regs=dict(d0=0x1b), pc=0xcc8d2), ERROR_JUMP, 0xcc8d2)
    err('cc8d2-jump-target-ff', U.with_host_writes(st, regs=dict(d0=0x123456ff), pc=0xcc8d2), ERROR_JUMP, 0xcc8d2)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('71622-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x71622), odd_word, 0x71622)
    err('71682-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x71682), odd_word, 0x71682, stop=0x71696)
    err('70fcc-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70fcc), odd_write, 0x70fcc, stop=0x70fd2)
    err('7209c-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x7209c), odd_word, 0x7209c)
    err('c5520-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xc5520), odd_write, 0xc5520)
    err('cc8c0-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xcc8c0), odd_write, 0xcc8c0)
    err('cca5a-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0xcca5a), odd_word, 0xcca5a)
    err('b6d90-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0xb6d90), odd_word, 0xb6d90)
    err('b450c-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb450c), odd_word, 0xb450c)
    err('cc8bc-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xcc8bc), odd_word, 0xcc8bc, stop=0xcca76)
    err('bfcfa-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xbfcfa), odd_word, 0xbfcfa, stop=0x2986)
    # failures after executed blocks: the later-unit stops (FR14) and an unrouted entry of the table cc8de
    err('71860-then-71874', U.with_host_writes(st, [((a6 + 0x15) & 0xffff, 1, 0)], pc=0x71860), unrouted, 0x71874)
    err('d161a-then-d1632', U.with_host_writes(st, [((a6 + 0x15) & 0xffff, 1, 0)], pc=0xd161a), unrouted, 0xd1632)
    err('cc8d2-then-cc8de', U.with_host_writes(st, regs=dict(d0=0x12345600), pc=0xcc8d2), unrouted, 0xcc8de)
    err('cc8c0-then-cc8e2', U.with_host_writes(st, [((a6 + 0x5e) & 0xffff, 1, 1)], pc=0xcc8c0), unrouted, 0xcc8e2)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x7209c, 0x720e0, 0x70f60, 0x71860)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))

