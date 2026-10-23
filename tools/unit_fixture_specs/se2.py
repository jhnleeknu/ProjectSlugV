"""V1 fixture spec of the area-E unit E2 (engine/src/animation_machine_select_e2.cpp, 129 block starts).

Blocks (contract docs/analysis/animation-machine-select-e2-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 E2 row): the name
entry after the last life [I] -- the 28ae child e695a of the player C6 block 4ed7c (CLR.B 8c; the score record 10de14 / 10de1c in front of the name
buffer LONG 7a sets BYTE 5e12 / 5e13(A5); the default name e6e28 by e63ec; the cursor search e6d66; the WORD 104cd2 write 3144), its entry e695e (the
BRA.W target of the unrouted 28ae child e6952 of FR2 e693a), the callback e69c0 (4836e C: wait; the input BYTE 3(A0) of the player record e6dc8
bit 4 enter (e6c26: C Set -> the end), bit 5 back (e6c96), the new-press BYTE of e6d8a bit 3 / 2 next / previous character (e6cea / e6d2e), the
counts WORD 84 / 88 / 8a), the redraw e6a4c (the rank text table e637a by e6496 - 1 or WORD 7e, the name, the cursor e6e30 with MOVEM.L
D0-D1/D7/A0, the end mark e6e25 / the 35a2 box), the end e6b24 (the bad-name list e6e32 compared by e63fa (C Set: equal) and replaced by e6e2c, the
7f -> space pass e6416, the 35a2 box, the installs e6ba0 / e6bea, the parent BYTE 62, JMP 2a00), the player selectors e6d8a / e6dc8 (D0.W > 1 signed:
the TRAP #15 boundaries e6d92 / e6dd0, outside the unit).  No computed jump; three C consumers with in-unit producers (e63fa, e6c26) and the routed
producer 4836e.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR13, C1..C10, E1) with declared
host edits (the name buffer LONG 7a(A6) in work RAM, the player WORD 76 0 / 1 mostly, the cursor WORDs 80 / 82 in range mostly).  This code runs
natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the 'natural' family takes the
frame-start states of that observation (state packs, read-only) in which a node of the pool 100800..104c00 holds an E2 callback (e69c0 e6ba0 e6bea)
as its callback LONG, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return
LONG, PC = the callback); the 'reinstall' family takes the first e69c0 frame of every X run and writes the declared callback LONG e695a (or e695e
with BYTE 8c = ff and WORD 7e, as the unrouted child e6952 would) into that natural node.  The spec reads those packs itself (io_pack below,
observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 3 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the callbacks and installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes and the reinstall worlds (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the subroutines of the unit entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 3 consumers, the TRAP #15 boundaries, odd node / stack / table
            index, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it
            differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR13, C1..C10
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR13, C1..C10, E1)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'se2'
ERROR_PC = 'unsupported animation select e2 PC'
ERROR_CARRY = 'select e2 caller requires known carry'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x3144, 0x314c), (0xe63fa, 0xe6448), (0xe695a, 0xe6d92), (0xe6db6, 0xe6dd0), (0xe6df4, 0xe6e06)]
STARTS = sorted(int(x, 16) for x in (
    '3144 e63fa e6400 e6406 e640a e6410 e6416 e641a e6422 e6426 e6430 e6432 e643a e6446 e695a e695e e6970 e6974 e697e e6982 e6996 e699a e69aa e69c0 '
    'e69c6 e69ca e69cc e69d4 e69e0 e69e8 e69ec e69f6 e69fa e6a02 e6a06 e6a0a e6a12 e6a1a e6a1e e6a22 e6a2a e6a2e e6a36 e6a3c e6a44 e6a4c e6a54 '
    'e6a60 e6a66 e6a6a e6a86 e6a96 e6a9e e6aa6 e6ab8 e6ac2 e6acc e6adc e6ae8 e6af0 e6afa e6b06 e6b14 e6b1a e6b22 e6b24 e6b2e e6b46 e6b4c e6b5a '
    'e6b64 e6b68 e6b78 e6b7c e6b84 e6b9a e6ba0 e6bae e6bbc e6bc0 e6bca e6bce e6be0 e6be4 e6bea e6bf2 e6c0c e6c10 e6c1a e6c1e e6c24 e6c26 e6c44 '
    'e6c5a e6c68 e6c6e e6c78 e6c80 e6c8c e6c90 e6c96 e6cac e6cbc e6cc4 e6cda e6ce2 e6ce6 e6cea e6cf4 e6cf6 e6d18 e6d1e e6d2e e6d38 e6d3a e6d48 '
    'e6d4e e6d66 e6d78 e6d80 e6d84 e6d8a e6db6 e6dbc e6dc2 e6dc8 e6df4 e6dfa e6e00'
    ).split())
# the 3 C consumers: BCC e69c6 (4836e), BCS e69e8 (e6c26), BCC e6b64 (e63fa)
CONSUMERS = (0xe69c6, 0xe69e8, 0xe6b64)
CLEAR_SET = (0xe6410, 0xe6c90)          # ANDI.B #fe,CCR; RTS: known C Clear (e63fa different, e6c26 accepted)
SET_SET = (0xe640a, 0xe6c44, 0xe6c68)   # ORI.B #1,CCR; RTS: known C Set (e63fa equal, e6c26 end mark / past the last column)
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()                           # no RTS of the unit passes an incoming C
STARTS_SET = set()
Z_READERS = ()                          # no Z / N crosses an E2 block boundary
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
# the TRAP #15 boundaries of the player selectors (D0.W > 1 signed): outside the unit, the dispatcher stops there (FR5 decision 2)
TRAPS = (0xe6d92, 0xe6dd0)
# E2 has no later-unit stop of its own; the still unrouted later-unit stops of earlier units (FR13 / FR12: FR14 71874 d1632 d177e 7177a 71786;
# C1..C9: pc10 EXIT_STOPS[:12]) stay declared stops of the native runs (none is reached from E2 code).
EXIT_STOPS = (0x71874, 0xd1632, 0xd177e, 0x7177a, 0x71786,
              0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6, 0x4e69a)
UNIT_EXITS = ()
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0xe69c0, 0xe69c6), (0xe69e0, 0xe69e8), (0xe6b5a, 0xe6b64))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_TARGETS = {}                       # no computed jump in E2
JUMP_PCS = ()
JUMP_ROUTED = ()
LIST_JUMPS = {}
# computed jumps of earlier units (unrouted targets are stops even when they are the straight-line successor); none is reached from E2 code
OTHER_JUMP_PCS = (0xb4034, 0xb42b4, 0xc54ae, 0xb3dc8, 0xb3f3e, 0xb3fc4, 0xb3fca, 0xb46aa, 0xcc7a8, 0xcc82a, 0x4a352, 0x4a43c, 0x2031c, 0x201a6, 0x21620,
                  0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36, 0x2224c, 0x22428, 0x21e10, 0x2229a,
                  0x22378, 0x203ac, 0xcc8da)
TABLE_ENTRIES = ()
# the callbacks entered as node callbacks: the 28ae child e695a (C6 4ed7c), e695e (the BRA.W target of the unrouted 28ae child e6952 of FR2 e693a),
# the in-range installs e69c0 / e6ba0 / e6bea (entered at once, and the next frames' callbacks)
NODE_ENTRIES = (0xe695a, 0xe695e, 0xe69c0, 0xe6ba0, 0xe6bea)
NATURAL_ROUTED = ()
NATURAL_ENTRIES = NODE_ENTRIES + NATURAL_ROUTED
# the subroutines of the unit entered as subroutines (return LONG = sentinel)
CALLEES = (0x3144, 0xe63fa, 0xe6416, 0xe6432, 0xe6a4c, 0xe6c26, 0xe6c96, 0xe6cea, 0xe6d2e, 0xe6d66, 0xe6d8a, 0xe6dc8, 0xe6ab8, 0xe6b24, 0xe6a2e,
           0xe6a0a, 0xe69cc)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x7a)   # node links, pointer fields, the name buffer LONG 7a
# natural worlds of the extended observation: (config, case, frame) with a pool node holding an E2 callback (scratch natscan_e2.py: every e69c0 frame,
# the first / 4th / 12th / last e6ba0 and e6bea frame of each run)
NATURAL = (('X1', 68, 961), ('X1', 68, 962), ('X1', 68, 963), ('X1', 68, 964), ('X1', 68, 965), ('X1', 68, 966), ('X1', 68, 967), ('X1', 68, 968),
           ('X1', 68, 969), ('X1', 68, 970), ('X1', 68, 971), ('X1', 68, 972), ('X1', 68, 973), ('X1', 68, 974), ('X1', 68, 975), ('X1', 68, 976),
           ('X1', 68, 977), ('X1', 68, 978), ('X1', 68, 979), ('X1', 68, 980), ('X1', 68, 981), ('X1', 68, 982), ('X1', 68, 983), ('X1', 68, 984),
           ('X1', 68, 985), ('X1', 68, 988), ('X1', 68, 996), ('X1', 68, 1007), ('X1', 68, 1008), ('X1', 68, 1011), ('X1', 68, 1019),
           ('X1', 68, 1043), ('X1', 94, 769), ('X1', 94, 770), ('X1', 94, 771), ('X1', 94, 772), ('X1', 94, 773), ('X1', 94, 774), ('X1', 94, 775),
           ('X1', 94, 776), ('X1', 94, 777), ('X1', 94, 778), ('X1', 94, 779), ('X1', 94, 780), ('X1', 94, 781), ('X1', 94, 782), ('X1', 94, 783),
           ('X1', 94, 784), ('X1', 94, 785), ('X1', 94, 786), ('X1', 94, 787), ('X1', 94, 788), ('X1', 94, 789), ('X1', 94, 790), ('X1', 94, 791),
           ('X1', 94, 792), ('X1', 94, 793), ('X1', 94, 796), ('X1', 94, 804), ('X1', 94, 815), ('X1', 94, 816), ('X1', 94, 819), ('X1', 94, 827),
           ('X1', 94, 851), ('X2', 68, 993), ('X2', 68, 994), ('X2', 68, 995), ('X2', 68, 996), ('X2', 68, 997), ('X2', 68, 998), ('X2', 68, 999),
           ('X2', 68, 1000), ('X2', 68, 1001), ('X2', 68, 1002), ('X2', 68, 1003), ('X2', 68, 1004), ('X2', 68, 1005), ('X2', 68, 1006),
           ('X2', 68, 1007), ('X2', 68, 1008), ('X2', 68, 1009), ('X2', 68, 1010), ('X2', 68, 1011), ('X2', 68, 1012), ('X2', 68, 1013),
           ('X2', 68, 1014), ('X2', 68, 1015), ('X2', 68, 1018), ('X2', 68, 1026), ('X2', 68, 1037), ('X2', 68, 1038), ('X2', 68, 1041),
           ('X2', 68, 1049), ('X2', 68, 1073), ('X2', 94, 801), ('X2', 94, 802), ('X2', 94, 803), ('X2', 94, 804), ('X2', 94, 805), ('X2', 94, 806),
           ('X2', 94, 807), ('X2', 94, 808), ('X2', 94, 809), ('X2', 94, 810), ('X2', 94, 811), ('X2', 94, 812), ('X2', 94, 813), ('X2', 94, 814),
           ('X2', 94, 815), ('X2', 94, 816), ('X2', 94, 817), ('X2', 94, 818), ('X2', 94, 819), ('X2', 94, 820), ('X2', 94, 821), ('X2', 94, 822),
           ('X2', 94, 823), ('X2', 94, 826), ('X2', 94, 834), ('X2', 94, 845), ('X2', 94, 846), ('X2', 94, 849), ('X2', 94, 857), ('X2', 94, 881),
           ('X3', 68, 1503), ('X3', 68, 1504), ('X3', 68, 1505), ('X3', 68, 1506), ('X3', 68, 1507), ('X3', 68, 1508), ('X3', 68, 1509),
           ('X3', 68, 1510), ('X3', 68, 1511), ('X3', 68, 1512), ('X3', 68, 1513), ('X3', 68, 1514), ('X3', 68, 1515), ('X3', 68, 1516),
           ('X3', 68, 1517), ('X3', 68, 1518), ('X3', 68, 1519), ('X3', 68, 1520), ('X3', 68, 1521), ('X3', 68, 1522), ('X3', 68, 1523),
           ('X3', 68, 1524), ('X3', 68, 1525), ('X3', 68, 1526), ('X3', 68, 1527), ('X3', 68, 1528), ('X3', 68, 1529), ('X3', 68, 1530),
           ('X3', 68, 1531), ('X3', 68, 1532), ('X3', 68, 1533), ('X3', 68, 1534), ('X3', 68, 1535), ('X3', 68, 1536), ('X3', 68, 1537),
           ('X3', 68, 1538), ('X3', 68, 1539), ('X3', 68, 1540), ('X3', 68, 1541), ('X3', 68, 1544), ('X3', 68, 1552), ('X3', 68, 1563),
           ('X3', 68, 1564), ('X3', 68, 1567), ('X3', 68, 1575), ('X3', 68, 1599), ('X3', 94, 1311), ('X3', 94, 1312), ('X3', 94, 1313),
           ('X3', 94, 1314), ('X3', 94, 1315), ('X3', 94, 1316), ('X3', 94, 1317), ('X3', 94, 1318), ('X3', 94, 1319), ('X3', 94, 1320),
           ('X3', 94, 1321), ('X3', 94, 1322), ('X3', 94, 1323), ('X3', 94, 1324), ('X3', 94, 1325), ('X3', 94, 1326), ('X3', 94, 1327),
           ('X3', 94, 1328), ('X3', 94, 1329), ('X3', 94, 1330), ('X3', 94, 1331), ('X3', 94, 1332), ('X3', 94, 1333), ('X3', 94, 1334),
           ('X3', 94, 1335), ('X3', 94, 1336), ('X3', 94, 1337), ('X3', 94, 1338), ('X3', 94, 1339), ('X3', 94, 1340), ('X3', 94, 1341),
           ('X3', 94, 1344), ('X3', 94, 1352), ('X3', 94, 1363), ('X3', 94, 1364), ('X3', 94, 1367), ('X3', 94, 1375), ('X3', 94, 1399),
           ('X4', 68, 1269), ('X4', 68, 1270), ('X4', 68, 1271), ('X4', 68, 1272), ('X4', 68, 1273), ('X4', 68, 1274), ('X4', 68, 1275),
           ('X4', 68, 1276), ('X4', 68, 1277), ('X4', 68, 1278), ('X4', 68, 1279), ('X4', 68, 1280), ('X4', 68, 1281), ('X4', 68, 1282),
           ('X4', 68, 1283), ('X4', 68, 1284), ('X4', 68, 1285), ('X4', 68, 1286), ('X4', 68, 1287), ('X4', 68, 1288), ('X4', 68, 1289),
           ('X4', 68, 1290), ('X4', 68, 1291), ('X4', 68, 1292), ('X4', 68, 1293), ('X4', 68, 1294), ('X4', 68, 1295), ('X4', 68, 1296),
           ('X4', 68, 1297), ('X4', 68, 1298), ('X4', 68, 1299), ('X4', 68, 1300), ('X4', 68, 1301), ('X4', 68, 1302), ('X4', 68, 1303),
           ('X4', 68, 1304), ('X4', 68, 1305), ('X4', 68, 1306), ('X4', 68, 1307), ('X4', 68, 1308), ('X4', 68, 1309), ('X4', 68, 1310),
           ('X4', 68, 1311), ('X4', 68, 1312), ('X4', 68, 1313), ('X4', 68, 1314), ('X4', 68, 1315), ('X4', 68, 1316), ('X4', 68, 1317),
           ('X4', 68, 1318), ('X4', 68, 1319), ('X4', 68, 1320), ('X4', 68, 1321), ('X4', 68, 1322), ('X4', 68, 1323), ('X4', 68, 1324),
           ('X4', 68, 1325), ('X4', 68, 1326), ('X4', 68, 1327), ('X4', 68, 1328), ('X4', 68, 1329), ('X4', 68, 1330), ('X4', 68, 1331),
           ('X4', 68, 1332), ('X4', 68, 1333), ('X4', 68, 1336), ('X4', 68, 1344), ('X4', 68, 1355), ('X4', 68, 1356), ('X4', 68, 1359),
           ('X4', 68, 1367), ('X4', 68, 1391), ('X4', 94, 1109), ('X4', 94, 1110), ('X4', 94, 1111), ('X4', 94, 1112), ('X4', 94, 1113),
           ('X4', 94, 1114), ('X4', 94, 1115), ('X4', 94, 1116), ('X4', 94, 1117), ('X4', 94, 1118), ('X4', 94, 1119), ('X4', 94, 1120),
           ('X4', 94, 1121), ('X4', 94, 1122), ('X4', 94, 1123), ('X4', 94, 1124), ('X4', 94, 1125), ('X4', 94, 1126), ('X4', 94, 1127),
           ('X4', 94, 1128), ('X4', 94, 1129), ('X4', 94, 1130), ('X4', 94, 1131), ('X4', 94, 1132), ('X4', 94, 1133), ('X4', 94, 1134),
           ('X4', 94, 1135), ('X4', 94, 1136), ('X4', 94, 1137), ('X4', 94, 1138), ('X4', 94, 1139), ('X4', 94, 1140), ('X4', 94, 1141),
           ('X4', 94, 1142), ('X4', 94, 1143), ('X4', 94, 1144), ('X4', 94, 1145), ('X4', 94, 1146), ('X4', 94, 1147), ('X4', 94, 1148),
           ('X4', 94, 1149), ('X4', 94, 1150), ('X4', 94, 1151), ('X4', 94, 1152), ('X4', 94, 1153), ('X4', 94, 1154), ('X4', 94, 1155),
           ('X4', 94, 1156), ('X4', 94, 1157), ('X4', 94, 1158), ('X4', 94, 1159), ('X4', 94, 1160), ('X4', 94, 1161), ('X4', 94, 1162),
           ('X4', 94, 1163), ('X4', 94, 1164), ('X4', 94, 1165), ('X4', 94, 1166), ('X4', 94, 1167), ('X4', 94, 1168), ('X4', 94, 1169),
           ('X4', 94, 1170), ('X4', 94, 1171), ('X4', 94, 1172), ('X4', 94, 1173), ('X4', 94, 1176), ('X4', 94, 1184), ('X4', 94, 1195),
           ('X4', 94, 1196), ('X4', 94, 1199), ('X4', 94, 1207), ('X4', 94, 1231))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds (scratch natscan_e2.py): the first e69c0 frame of every X run and its node; the callback LONG := e695a, or e695e with BYTE 8c = ff
# and WORD 7e (the rank that FR2 e693a gives the child e6952), written as declared host edits
_FIRST = (('X1', 68, 961, 0x101330), ('X1', 94, 769, 0x101eac), ('X2', 68, 993, 0x1014b8), ('X2', 94, 801, 0x1014b8), ('X3', 68, 1503, 0x102344),
          ('X3', 94, 1311, 0x1017c8), ('X4', 68, 1269, 0x101d24), ('X4', 94, 1109, 0x101950))
REINSTALL = tuple([(cfg, case, f, node, 0xe695a, ()) for cfg, case, f, node in _FIRST] +
                  [(cfg, case, f, node, 0xe695e, ((0x8c, 1, 0xff), (0x7e, 2, rank))) for (cfg, case, f, node), rank in zip(_FIRST, (1, 2, 3, 5, 7, 9, 10, 4))])

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xf, 0x10, 0x1a, 0x1b, 0x1f, 0x20, 0x3f, 0x40, 0x41, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xef, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x23, 0x24, 0x25, 0x3c, 0x7f, 0x80, 0x12c, 0x258, 0x7fff, 0x8000, 0x8001, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x18000, 0x40000, 0x100000, 0x7fffffff, 0x80000000, 0xffff0000, 0xffffffe0, 0xffffffff, 0x12345678)
# the name characters: the table e6e06 (space, A..Z, . ? ! &, the end mark 7f, 00) and a few that are not in the table
CHARS = tuple(range(0x41, 0x5b)) + (0x20, 0x2e, 0x3f, 0x21, 0x26, 0x7f, 0x00)
BAD_NAMES = (b'SEX', b'SM ', b'S M', b' SM', b'   ', b'AAA', b'ASS', b'GAY', b'FAG', b'\x7f  ')
NAMES = (0x10de18, 0x10de20)            # the name buffers of the two players (C6 4ed9a / 4eda4): LONG 7a(A6); the score LONG in front (10de14 / 10de1c)
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
# no flag-sharing Bcc pair inside one E2 block
BUNDLED = ()
THREAD = {}


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start); a Bcc followed by a BUNDLED Bcc continues the block (none in E2)."""
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
    the computed jumps of earlier units (OTHER_JUMP_PCS), at the TRAP #15 boundaries (TRAPS), or at
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it: LONG 7a(A6) a name buffer in work RAM (10de18 /
        10de20 of C6 4ed9a / 4eda4 mostly, or a declared record) with three name characters of the table e6e06 mostly and the score LONG in front of
        it, LONG c(A6) a parent node, WORD 76(A6) the player 0 / 1 mostly (above 1: the TRAP #15 boundary), WORD 80(A6) the cursor column 0..3
        mostly, WORD 82(A6) the character index 0..20 mostly, WORD 7e(A6) a rank 0..a (the rank text table e637a has 11 LONGs), BYTE 8c(A6) 0 mostly,
        the BYTE 5683(A5) bit 2 of 4836e and the input BYTEs of the player records (104ca8 .. 104cb3), BYTE 1d(A6) < 4."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0xc, 0x10, 0x20, 0x30, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340001,
                                     0xffffffff, 0xfffe, 0x10001))
        if rng.random() < 0.4:
            regs['d7'] = rng.choice((0, 1, 2, 3, 4, 0x24, 0x28, 0x100, 0x7fff, 0x8000, 0xffff, 0x12340003, 0xc000))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.5 else self.pointer()
        regs['a1'] = rec + 0x28 if rng.random() < 0.3 else self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = rec + 0x10 if rng.random() < 0.3 else self.pointer()
        regs['a4'] = rng.choice((0xe6e06, 0xe6e32, 0xe637a)) if rng.random() < 0.5 else self.pointer()
        sp = regs['a7']
        name = rng.choice(NAMES) if rng.random() < 0.8 else rec + 0x10
        writes.append(((a6 + 0x7a) & 0xffff, 4, name))                                  # LONG 7a(A6): the name buffer
        if rng.random() < 0.25:
            text = rng.choice(BAD_NAMES)
        else:
            text = bytes(rng.choice(CHARS) if rng.random() < 0.9 else rng.getrandbits(8) for _ in range(3))
        for k in range(3):
            writes.append(((name + k) & 0xffff, 1, text[k]))
        writes.append(((name + 3) & 0xffff, 1, 0))
        writes.append(((name - 4) & 0xffff, 4, rng.choice((0, 0x100, 0x5000, 0x99999, 0x12345678, 0xffffffff)) if rng.random() < 0.7 else rng.getrandbits(32)))
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))                         # the parent LONG c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 0, 0, 1, 1, 1, 2, 0xffff, 0x8000, 0x10)) if rng.random() < 0.95 else rng.getrandbits(16)))
        writes.append(((a6 + 0x80) & 0xffff, 2, rng.choice((0, 1, 2, 3, 0, 1, 2, 3, 4, 0xffff)) if rng.random() < 0.9 else self.value(2)))
        writes.append(((a6 + 0x82) & 0xffff, 2, rng.randrange(0x21) if rng.random() < 0.85 else rng.choice((0xffff, 0x1f, 0x20, 0x21, 0x7fff))))
        writes.append(((a6 + 0x7e) & 0xffff, 2, rng.randrange(0xb)))                    # WORD 7e(A6): a rank (the 11 LONGs of e637a)
        if rng.random() < 0.7:
            writes.append(((a6 + 0x8c) & 0xffff, 1, 0))
        writes.append((0xd683, 1, rng.choice((0, 4, 0xfb, 0xff, 0x04, 0))))            # BYTE 5683(A5) = 10d683: bit 2 decides the C of 4836e
        for off in (0x4cab, 0x4cac, 0x4cb1, 0x4cb2):                                   # the input BYTEs of the player records (-3355 / -3354 / -334f / -334e(A5))
            writes.append((off, 1, rng.choice((0, 0x10, 0x20, 0x30, 0x08, 0x04, 0x0c, 0xff, 0x14, 0x24)) if rng.random() < 0.8 else rng.getrandbits(8)))
        if rng.random() < 0.9:
            writes.append((0xfd82, 1, 0))                                                 # BYTE 10fd82 = 0
        if rng.random() < 0.7:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0x76, 0x77, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83) and rng.random() < 0.9):
                continue                                        # the name buffer, the player, the rank and the cursor stay declared above (mostly)
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
    require(len(STARTS) == 129 and len(STARTS_SET) == 129, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_select_e2_block', ('start is not routed to select e2', hex(s), unit_of(s)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            require(unit_of(pc) == 'animation_select_e2_block', ('range PC is not routed to select e2', hex(pc), unit_of(pc)))
        require(unit_of(lo - 2) != 'animation_select_e2_block' and unit_of(hi) != 'animation_select_e2_block', ('range neighbours', hex(lo), hex(hi)))
    # the unrouted 28ae child e6952 (FR2 e693a) whose BRA.W lands on the E2 start e695e stays unrouted (a later unit routes it)
    require(unit_of(0xe6952) is None and 0xe695e in STARTS_SET, 'e6952 unrouted, e695e an E2 start')
    rng = random.Random(0xE2A)
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
    sys.stderr.write('se2 spec: %d fixtures (%d natural), visited %d/129, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('se2: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('se2: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the SUBQ.W borrow and
    the CMPM / DBRA count of e63fa .. e6406, the 7f test of e641a, BYTE 8d of e6432, the score record 10de14 / 10de1c of e695e / e6bf2, the input
    BYTE bits 4 / 5 of e69d4 and the new-press bits 3 / 2 of e6a12 / e6a22, the counts WORD 84 / 88 / 8a / 86 (0 / 1 / 2, the signed 7 / 24 / 6 / 4
    limits), BYTE 8c / WORD 7e of e6a4c / e6a66, the rank index of e6a6a, the D7 / WORD 80 compares of e6ab8 / e6ae8 / e6af0 / e6b1a, the bad-name list
    end of e6b4c, the end mark 7f of e6c26, the WORD 80 limit 3 of e6c5a .. e6c78 / e6c96 / e6cea / e6d2e, the borrow of e6cbc / e6d3a, the 00 of the
    table at e6cf6, the cursor character of e6d66, the signed player compare of e6d8a / e6dc8 (1 / 2 / ffff / 8000), TST.W D0 of e6db6 / e6df4), the
    upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    nm = lambda text, ptr=NAMES[0]: [((ptr + k) & 0xffff, 1, text[k]) for k in range(len(text))]
    if entry in (0x3144, 0xe63fa, 0xe6416, 0xe695a, 0xe695e, 0xe6982, 0xe69aa, 0xe69d4, 0xe6a2e, 0xe6a3c, 0xe6a44, 0xe6a60, 0xe6a6a, 0xe6a86,
                 0xe6aa6, 0xe6ab8, 0xe6acc, 0xe6adc, 0xe6b1a, 0xe6b4c, 0xe6b78, 0xe6ba0, 0xe6bae, 0xe6bea, 0xe6bf2, 0xe6c26, 0xe6c5a, 0xe6c80, 0xe6cbc,
                 0xe6cf6, 0xe6d3a, 0xe6d66, 0xe6d78, 0xe6d80, 0xe6d8a, 0xe6dc8, 0xe6db6, 0xe6df4, 0xe6dbc, 0xe6dc2, 0xe6dfa, 0xe6e00):
        h += [dict(regs=dict(up))] + mirror
    if entry == 0xe63fa:
        for d0, a, b in ((0, b'AB', b'AB'), (0x10000, b'AB', b'AB'), (1, b'A', b'A'), (1, b'A', b'B'), (3, b'SEX', b'SEX'), (3, b'SEX', b'SEY'),
                         (3, b'XEX', b'SEX'), (0x12340003, b'GAY', b'GAY'), (0xffff, b'AB', b'AC')):
            h.append(dict(regs=dict(up, d0=d0), regrec=dict(a0=0x20, a1=0x28), rec=[(0x20 + k, 1, a[k]) for k in range(len(a))] +
                          [(0x28 + k, 1, b[k]) for k in range(len(b))]))
    if entry == 0xe6400:
        for a, b in ((0x41, 0x41), (0x41, 0x42), (0x80, 0x7f), (0, 0xff)):
            h.append(dict(regrec=dict(a0=0x20, a1=0x28), rec=[(0x20, 1, a), (0x28, 1, b)]))
    if entry == 0xe6406:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x10000, 0xffff, 0x12340002)]
    if entry in (0xe6416, 0xe641a, 0xe6426):
        for text in (b'\x7f\x7f\x7f', b'A\x7fB', b'\x7f  ', b'ABC', b'\x7e\x80\xff'):
            h.append(dict(regs=dict(up, d7=0x12340002), regrec=dict(a0=0x20), rec=[(0x20 + k, 1, text[k]) for k in range(3)]))
    if entry == 0xe6426:
        h += [dict(regs=dict(up, d7=v), regrec=dict(a0=0x20)) for v in (0, 1, 0x10000, 0xffff)]
    if entry == 0xe6432:
        h += byte(0x8d, (0, 0xff, 1, 0x80))
    if entry in (0xe695a, 0xe695e, 0xe6bf2, 0xe6a54):
        for p in (0x10de18, 0x10de20, 0x10de1c, 0x10de24, 0x10de14):
            h.append(dict(a6off=[(0x7a, 4, p)], writes=nm(b'A  ', p) + [((p + 3) & 0xffff, 1, 0)]))
    if entry in (0xe6974, 0xe6c10):
        h += [dict(regs=dict(up, a0=v)) for v in (0x10de1c, 0x10de14, 0x10de18, 0x1010de1c, 0x10de1d)]
    if entry == 0xe69d4:
        for v in (0x10, 0x20, 0x30, 0, 0xef, 0xdf, 0xff, 0x08, 0x04):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x23, 1, v)]))
    if entry == 0xe69fa:
        h += [dict(regs=dict(up, d0=v)) for v in (0x20, 0, 0xdf, 0x12345620)]
    if entry in (0xe6a12, 0xe6a22):
        h += [dict(regs=dict(up, d0=v)) for v in (0x08, 0x04, 0x0c, 0, 0xf3, 0x12345608, 0x12345604)]
    if entry in (0xe69cc, 0xe6a0a):
        h += [dict(a6off=[(0x76, 2, v)], writes=[(0x4cab, 1, b), (0x4cac, 1, b), (0x4cb1, 1, b), (0x4cb2, 1, b)])
              for v, b in ((0, 0x10), (0, 0x20), (1, 0x10), (1, 0x08), (0, 0x04), (2, 0), (0xffff, 0x10), (0x8000, 0x20), (0x10, 0))]
    if entry == 0xe6a2e:
        h += word(0x84, (1, 0, 2, 0x8000))
    if entry == 0xe6a3c:
        h += word(0x88, (1, 0, 2, 0x8001))
    if entry == 0xe6a44:
        h += word(0x8a, (1, 0, 2, 0x8001))
    if entry in (0xe6a4c, 0xe6be0, 0xe6bca):
        h += [dict(a6off=[(0x8c, 1, b), (0x7e, 2, r)]) for b, r in ((0, 0), (0xff, 0), (0xff, 0xa), (0x80, 5), (1, 3))]
    if entry == 0xe6a60:
        h += [dict(regs=dict(up, d0=v)) for v in (1, 2, 0xb, 0x10001, 0x12340005)]
    if entry == 0xe6a66:
        h += word(0x7e, (0, 1, 0xa, 5))
    if entry == 0xe6a6a:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0xa, 0x10000, 0x12340003, 0x4000)]
    if entry in (0xe6ab8, 0xe6ac2):
        for d7, w80, w84 in ((0, 0, 7), (0, 0, 8), (1, 1, 0), (3, 3, 0xffff), (2, 1, 7), (0x10000, 0, 7), (0, 0, 0x8000), (3, 0, 7)):
            h.append(dict(regs=dict(up, d7=d7), regrec=dict(a0=0x20), a6off=[(0x80, 2, w80), (0x84, 2, w84)]))
    if entry == 0xe6ae8:
        h += [dict(regs=dict(up, d7=v), a6off=[(0x80, 2, w)]) for v, w in ((3, 3), (3, 2), (2, 3), (0x10003, 3), (0xffff, 0))]
    if entry == 0xe6af0:
        h += word(0x80, (3, 2, 0x103, 0xffff))
    if entry == 0xe6b1a:
        h += [dict(regs=dict(up, d7=v), regrec=dict(a0=0x20)) for v in (2, 3, 0xffff, 0x7fff, 0x8000, 0x10002, 0x12340003)]
    if entry == 0xe6b4c:
        h += [dict(regs=dict(up, d7=v, a4=0xe6e32)) for v in (0, 0x24, 0x28, 0x10000, 0x12340024)]
    if entry in (0xe6b5a, 0xe6b46, 0xe6b2e, 0xe6b24):
        for text in BAD_NAMES[:4] + (b'SEY', b'ABC', b'GAY', b'\x7f  '):
            h.append(dict(regs=dict(up, a0=0xe6e5e), a6off=[(0x7a, 4, NAMES[0]), (0x8d, 1, (0, 0xff)[len(h) % 2])], writes=nm(text)))
    if entry == 0xe6ba0:
        h += word(0x86, (0x25, 0x26, 0x24, 0, 0x8000, 0x8001, 1))
    if entry == 0xe6bae:
        h += word(0x84, (5, 6, 4, 0x7fff, 0xffff, 3))
    if entry == 0xe6bc0:
        h += word(0x84, (3, 4, 0x8000, 0x7fff))
    if entry == 0xe6bea:
        h += word(0x86, (0, 1, 2, 0x8000))
    if entry == 0xe6c26:
        h += [dict(a6off=[(0x82, 2, v), (0x80, 2, w)]) for v, w in ((0x1f, 0), (0x1f, 2), (0, 0), (0x20, 3), (0xffff, 1), (1, 3), (2, 2), (0x1e, 0xffff))]
    if entry in (0xe6c5a, 0xe6c6e, 0xe6c78):
        h += word(0x80, (2, 3, 4, 0, 1, 0x7fff, 0xffff, 0x8000))
    if entry == 0xe6c80:
        h += [dict(regs=dict(up, d5=v)) for v in (1, 2, 3, 0x10002)]
    if entry in (0xe6c96, 0xe6cbc, 0xe6cda, 0xe6cea, 0xe6d2e):
        h += word(0x80, (3, 0, 1, 2, 0xffff, 0x8000))
    if entry in (0xe6cf6, 0xe6cea):
        h += [dict(a6off=[(0x82, 2, v), (0x80, 2, 1)]) for v in (0x1e, 0x1f, 0x20, 0, 0xffff, 0x7fff)]
    if entry in (0xe6d3a, 0xe6d2e):
        h += [dict(a6off=[(0x82, 2, v), (0x80, 2, 2)]) for v in (0, 1, 0x20, 0x8000)]
    if entry in (0xe6d66, 0xe6c8c):
        for w80, text in ((0, b'A  '), (1, b'AB '), (2, b'AB\x7f'), (0, b'&  '), (1, b'A\x00 '), (0, b'\x61  '), (2, b'AB.')):
            h.append(dict(regs=dict(up), a6off=[(0x80, 2, w80), (0x7a, 4, NAMES[0])], writes=nm(text)))
    if entry == 0xe6d78:
        h += [dict(regs=dict(up, d6=v, d7=c, a4=0xe6e06)) for v, c in ((0, 0x20), (0, 0x41), (5, 0x45), (0x10000, 0x41), (0x1f, 0x7f), (0, 0))]
    if entry in (0xe6d8a, 0xe6dc8):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 2, 0xffff, 0x8000, 0x10001, 0x7fff, 0x12340000)]
    if entry in (0xe6db6, 0xe6df4):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x10000, 0xffff)]
    return h


# chain hints: let the real producers return both C values
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry == 0xe69c0:
        return dict(writes=[(0xd683, 1, (0, 4, 0xfb, 0xff)[t % 4])])                  # 4836e: BTST #2,5683(A5): set -> Clear, clear -> Set
    if entry == 0xe69e0:
        # e6c26: WORD 82 = 1f (the end mark 7f: e6c44 Set), WORD 80 3 (past the last column: e6c68 Set), WORD 80 0..2 (e6c90 Clear)
        return dict(a6off=[(0x82, 2, (0x1f, 0, 5, 0x1f, 1)[t % 5]), (0x80, 2, (0, 3, 1, 2, 0)[(t // 5) % 5]), (0x7a, 4, NAMES[t % 2])])
    if entry == 0xe6b5a:
        text = (b'SEX', b'SEY', b'ABC', b'SEX', b'GAY')[t % 5]
        name = NAMES[(t // 5) % 2]
        return dict(regs=dict(a0=(0xe6e5e, 0xe6e5e, 0xe6e5e, 0xe6e7a, 0xe6e7a)[t % 5]), a6off=[(0x7a, 4, name)],
                    writes=[((name + k) & 0xffff, 1, text[k]) for k in range(3)])
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 8c / 8d, the player WORD 76 (0 / 1), the cursor WORDs 80 / 82, the counts WORD 84 / 86 / 88 / 8a, the
            # rank WORD 7e, the name buffer LONG 7a, BYTE 5683(A5) bit 2 (4836e) and the input BYTEs (bits 4 / 5, 3 / 2)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x8c, 1, (0, 0, 0xff)[t % 3]), (0x8d, 1, (0, 0xff)[(t // 2) % 2]), (0x76, 2, (0, 1, 0, 1, 2)[(t // 3) % 5]),
                               (0x80, 2, (0, 1, 2, 3)[(t // 2) % 4]), (0x82, 2, (0, 1, 0x1f, 0x1e, 0x20)[(t // 3) % 5]), (0x84, 2, (1, 7, 8, 5, 0)[(t // 4) % 5]),
                               (0x86, 2, (0x25, 1, 0, 0x30)[(t // 5) % 4]), (0x88, 2, (1, 0x258, 2)[(t // 2) % 3]), (0x8a, 2, (1, 0x12c, 2)[(t // 3) % 3]),
                               (0x7e, 2, (1, 3, 0xa)[(t // 4) % 3]), (0x7a, 4, NAMES[(t // 7) % 2])],
                        writes=[(0xd683, 1, (4, 0, 4)[t % 3]), (0x4cab, 1, (0x10, 0x20, 0, 0x30, 0)[(t // 2) % 5]), (0x4cac, 1, (0x08, 0x04, 0, 0x0c)[(t // 3) % 4]),
                                (0x4cb1, 1, (0x10, 0x20, 0)[(t // 2) % 3]), (0x4cb2, 1, (0x08, 0x04, 0)[(t // 3) % 3])])
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
            if len(kept) >= 4:
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
    frame start.  Up to the sentinel or the first unrouted PC.  The reinstall worlds write one declared callback LONG (and the declared fields) first
    (REINSTALL)."""
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
    for cfg, case, frame, node, cb, extra in REINSTALL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        regs = dict(st0['regs'])
        regs.update(a5=0x108000, a6=node, a7=0x10ef00)
        st = U.make_state(st0['ram'], regs, cb, st0['bank'], st0['pvc'])
        st = U.with_host_writes(st, [(0xef00, 4, SENTINEL), (node & 0xffff, 4, cb)] + [((node + off) & 0xffff, n, v) for off, n, v in extra])
        tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
        require(tr is not None, ('reinstall world failed', cfg, case, frame, hex(node), hex(cb)))
        record(tr['pcs'] + [tr['stop']])
        tag = ''.join('-%x=%x' % (off, v) for off, n, v in extra)
        add_run(add, 'reinstall-%05x-%s%03d-f%d-%x%s' % (cb, cfg, case, frame, node, tag), st, tr,
                dict(family='reinstall', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
        count += 1
    require(count >= 300, ('too few natural node fixtures', count))


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
    st = U.with_host_writes(base.state, [(base.state['regs']['a7'] & 0xffff, 4, SENTINEL), ((base.state['regs']['a6'] + 0x7a) & 0xffff, 4, NAMES[0]),
                                         (NAMES[0] & 0xffff, 4, 0x41202000)])
    starts = set(STARTS)

    def err(name, state, text, fail_pc, stop=SENTINEL):
        add(U.Fixture('error-' + name, state, [], stop, ('error', text), fail_pc=fail_pc, meta=dict(family='error', fail_pc=fail_pc)))
        if fail_pc != state['pc'] and not fail_pc & 1:
            add(U.Fixture('failpc-' + name, state, [], fail_pc, meta=dict(family='failpc', fail_pc=fail_pc)))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in starts:
                err('internal-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_PC, pc)
    err('odd-pc', U.with_host_writes(st, pc=0xe6a4d), 'unaligned animation machine PC', 0xe6a4d)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the TRAP #15 boundaries of the player selectors (D0.W > 1 signed): the selector block runs, the dispatcher stops at the TRAP PC
    err('e6d8a-then-e6d92', U.with_host_writes(st, regs=dict(d0=2), pc=0xe6d8a), unrouted, 0xe6d92)
    err('e6dc8-then-e6dd0', U.with_host_writes(st, regs=dict(d0=0x12347fff), pc=0xe6dc8), unrouted, 0xe6dd0)
    err('e6a0a-then-e6d92', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 2)], pc=0xe6a0a), unrouted, 0xe6d92)
    err('e69cc-then-e6dd0', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 3)], pc=0xe69cc), unrouted, 0xe6dd0)
    # odd node / stack / table index: the entry block fails (the row's stop is the PC right after the failing block)
    err('e695a-then-e695e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe695a), odd_word, 0xe695e)
    err('e6a2e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe6a2e), odd_word, 0xe6a2e)
    err('e69aa-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe69aa), odd_write, 0xe69aa)
    err('e6c26-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe6c26), odd_write, 0xe6c26)
    err('e6acc-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe6acc), odd_word, 0xe6acc, stop=0xe84c8)
    err('e6adc-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe6adc), odd_word, 0xe6adc)
    err('e640a-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe640a), odd_word, 0xe640a)
    err('e6b4c-odd-index', U.with_host_writes(st, regs=dict(a4=0xe6e32, d7=0x12340001), pc=0xe6b4c), odd_word, 0xe6b4c)
    err('e6bf2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xe6bf2), odd_word, 0xe6bf2)
    # failures after executed blocks: e695a (CLR.B on an odd node is a BYTE write) then the LONG read of e695e; e6ae8 .. e6b06 into the odd stack of
    # the 35a2 call
    err('e6ae8-then-e6b06-odd-stack', U.with_host_writes(st, [((a6 + 0x80) & 0xffff, 2, 0)], regs=dict(d7=3, a7=a7 + 1), pc=0xe6ae8), odd_word, 0xe6b06)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xe6a2e, 0xe6ba0, 0xe6c5a, 0xe6b1a)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
