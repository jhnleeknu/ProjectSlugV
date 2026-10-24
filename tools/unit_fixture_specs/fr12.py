"""V1 fixture spec of the area-D unit FR12 (engine/src/animation_machine_objects_fr12.cpp, 212 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr12-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 FR12 row): the
FR10 later-unit successors 70f8e / b6c58, the FR4 table entry cc7c0, the FR11 later-unit successors b41f2 (MULS rotation, the c000 dead zone), b6e5e
(49392 -> b518c), c5612 (JMP 2a00), the FR11 table entry b42c4 (b42ea random D4 step), the item handlers b42a2 / b4294 / c0924 (targets of the FR11
JMP (A0) b4034) with b40f8 / b41b2 / b402a, the kind handler c1036 (b4304 C -> c1064, c106e random angle, c1cf2, c1094 .. c115a turn and sector by
MULU.W #10, the three 2986 children b3dbc with MOVEM.W (A7)+,D0-D6 of c120c / c128a / c131a, c1d06), the installs b6ed8 / b6fa4 / b7096, 71502 / 716ca
(the LONG table 70d72), 4d84e (MULU.W #10 record 4cf64 -> C), 7179a (4945e C), 717c8, 71e8c / 71f08, 722da / 72352.  No computed jump of its own; the
bundled BEQ c113a / c11ec (the same Z as the BEQ that reaches them) belong to the blocks c1130 / c11e2.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR11, C1..C10) with declared host
edits.  This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the
'natural' family takes the frame-start states of that observation (state packs, read-only) in which a node of the pool 100800..104c00 holds an FR12
node entry (or the FR1 item child b3dbc, whose kind handler c1036 is FR12, or the FR11 installs b6e50 / c5602 that reach b6e5e / c5612) as its
callback LONG, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return LONG,
PC = the callback).  The spec reads those packs itself (io_pack below, observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 8 C consumers and the C pass 4d86c is entered directly (the seed world with declared edits).  Stop: the first
            PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the callbacks and installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers, handlers and table entries entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 8 consumers, odd node / stack / A0, failures after executed
            blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is
            even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR11, C1..C10
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR11, C1..C10)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'fr12'
ERROR_PC = 'unsupported animation objects fr12 PC'
ERROR_CARRY = 'objects fr12 caller requires known carry'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x4d84e, 0x4d86e), (0x70f8e, 0x70f94), (0x71502, 0x71562), (0x716ca, 0x7177a), (0x7177c, 0x71786), (0x71788, 0x717c2), (0x717c8, 0x717e8),
          (0x71e8c, 0x71f2c), (0x722da, 0x72390), (0xb402a, 0xb4030), (0xb40f8, 0xb4104), (0xb41b2, 0xb41be), (0xb41f2, 0xb427e), (0xb4294, 0xb42b0),
          (0xb42c4, 0xb42c8), (0xb42ea, 0xb4328), (0xb518c, 0xb5198), (0xb6c58, 0xb6c66), (0xb6e5e, 0xb6e8c), (0xb6ed8, 0xb6fc2), (0xb6ff4, 0xb7100),
          (0xc0924, 0xc0986), (0xc1036, 0xc13c0), (0xc1cf2, 0xc1d2e), (0xc5612, 0xc5618), (0xcc7c0, 0xcc7c4)]
STARTS = sorted(int(x, 16) for x in (
    '4d84e 4d868 4d86c 70f8e 71502 7150a 71532 71536 7155e 716ca 716d6 716da 716ea 716f4 716fa 716fe 71706 7172e 71732 7175a 71764 7176a 7177c '
    '71788 7179a 717a4 717aa 717ae 717c8 717ce 717d4 717de 717e4 71e8c 71e94 71ebc 71ec0 71ee8 71eee 71f08 71f12 71f18 71f1e 71f22 71f28 722da '
    '722e2 7230a 7230e 72336 72352 72376 7237c 72386 7238c b402a b40f8 b40fe b41b2 b41b8 b41f2 b4200 b4208 b4212 b4250 b425e b4260 b4266 b426a '
    'b4272 b4274 b427a b4294 b429e b42a2 b42ac b42c4 b42ea b42f0 b42f6 b42f8 b4304 b4312 b431c b4322 b518c b6c58 b6e5e b6e6e b6e7c b6e80 b6ed8 '
    'b6ee2 b6eee b6f26 b6f2a b6f62 b6f82 b6f88 b6f9a b6f9e b6fa4 b6fa8 b6fae b6fb8 b6fbe b6ff4 b7000 b7038 b703c b7074 b7096 b70ac b70b2 b70b8 '
    'b70c0 b70ce b70d8 b70e4 b70ee b70f6 b70fc c0924 c0944 c0950 c0956 c095c c0966 c096a c0970 c0976 c097e c0984 c1036 c1048 c105e c1064 c1068 '
    'c106e c1094 c10a0 c10a6 c10b0 c10c6 c10d0 c10d8 c10e2 c10f2 c1108 c1112 c1126 c1130 c113e c1144 c114a c1152 c1158 c115a c116a c1170 c1176 '
    'c1180 c118a c119a c11b0 c11ba c11ce c11d8 c11e2 c11f0 c11f6 c11fc c1204 c120a c120c c123e c1246 c1260 c1264 c126a c127a c127c c128a c12cc '
    'c12d4 c12ee c12f2 c12f8 c130a c130c c131a c135c c1364 c137e c1382 c1388 c139a c139c c13aa c1cf2 c1cf8 c1cfe c1d04 c1d06 c1d0c c1d12 c1d18 '
    'c1d1e c1d26 c1d2c c5612 cc7c0'
    ).split())
# the 8 C consumers: BCC 716fa (4d84e), BCS 717aa (4945e), BCC 71f1e (49fc6), b6e7c (49392), c1064 (b4304), c123e c12cc c135c (MOVEM.W (A7)+,D0-D6;
# BCC, 2986)
CONSUMERS = (0x716fa, 0x717aa, 0x71f1e, 0xb6e7c, 0xc1064, 0xc123e, 0xc12cc, 0xc135c)
CLEAR_SET = (0x4d84e, 0xb4322)          # TST.W a(A2) (Clear; BNE to the RTS 4d86c), ANDI.B #fe,CCR; RTS
SET_SET = (0x4d868, 0xb431c, 0xc1260, 0xc12ee, 0xc137e)   # ORI.B #1,CCR (4d868 -> the RTS 4d86c, b431c; RTS; c1260 c12ee c137e: no reader)
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = (0x4d86c,)                   # the RTS that returns the C of 4d84e / 4d868 to 716fa
STARTS_SET = set()
Z_READERS = ()                          # no Z / N crosses an FR12 block boundary
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = {(0x716da, 0x71502)}   # 716da: D0.W = WORD 46 - WORD 46 = 0 is never > 30 (BGT 71502 never taken)
# 716da MOVE.W 46(A6),D0; SUB.W 46(A6),D0 (the same RAM WORD twice: D0.W = 0); CMPI.W #30,D0; BGT.W 71502: never taken
BRANCH_IMPOSSIBLE = {(0x716e6, 0x71502)}
LATER_GATED = set()
GATED_CONSUMERS = ()
# no TRAP in FR12; the FR11 TRAP #15 b3e58 (b3e46) and the FR1 TRAP #15 b3eac that the FR11 handlers reached from FR12 (b4030) may pass: boundaries
TRAPS = (0xb3e58, 0xb3eac)
# PCs of later units that an FR12 block reaches by a fall-through or a branch (FR13 71682 717c2, FR14 7177a 71786), the still unrouted later-unit stops
# of the FR11 blocks (fr11 UNIT_EXITS that FR12 does not route: FR13 b6d90 bfcfa), of the FR10 blocks (FR13 70f60 70fcc 70ff8 71028) and of the
# C1..C9 blocks (pc10 EXIT_STOPS[:12]).  Declared stops of the native runs: a straight-line unrouted PC after a routed block is not the interior of a
# routed block.
EXIT_STOPS = (0x71682, 0x717c2, 0x7177a, 0x71786,
              0xb6d90, 0xbfcfa, 0x70f60, 0x70fcc, 0x70ff8, 0x71028,
              0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6, 0x4e69a)
UNIT_EXITS = EXIT_STOPS[:4]             # the FR12 later-unit stops (FR13 / FR14)
# objects FR13 routes the FR12 later-unit stops 71682 717c2, the FR11 ones b6d90 bfcfa and the FR10 ones 70f60 70fcc 70ff8 71028 since FR13 (declared
# stops of the FR12 runs, as before FR13)
ROUTED_LATER = (0x71682, 0x717c2, 0xb6d90, 0xbfcfa, 0x70f60, 0x70fcc, 0x70ff8, 0x71028)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x716f4, 0x716fa), (0x716ea, 0x716fa), (0x717a4, 0x717aa), (0x71f18, 0x71f1e), (0xb6e6e, 0xb6e7c), (0xc105e, 0xc1064), (0xc120c, 0xc123e),
          (0xc128a, 0xc12cc), (0xc131a, 0xc135c))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# FR12 has no computed jump of its own (JUMP_PCS empty); the FR11 computed jumps that the FR12 runs reach are in OTHER_JUMP_PCS
JUMP_TARGETS = {}
JUMP_PCS = ()
JUMP_ROUTED = ()
LIST_JUMPS = {}
# computed jumps that the FR12 runs reach (FR11 b4034 / b42b4 / c54ae, FR1 b3dc8 b3f3e b3fc4 b3fca through the item handlers, FR4 cc7a8 / cc82a; the
# C3 .. C10 list): an unrouted target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0xb4034, 0xb42b4, 0xc54ae, 0xb3dc8, 0xb3f3e, 0xb3fc4, 0xb3fca, 0xcc7a8, 0xcc82a, 0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72,
                  0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36, 0x2224c, 0x22428, 0x21e10, 0x2229a, 0x22378,
                  0x203ac)
TABLE_ENTRIES = ()
# the callbacks and installed values entered as node callbacks: 71502 / 716ca (the LONG table 70d72 of FR2b 70d22, N15 711e6, FR13 70ff8), the
# in-range installs 7179a 71f08 72352 b6fa4 b7096 c0956 c10a0 c1170 c1d0c (entered at once and as the next frame's callback), 71e8c (N15 71e82; FR12
# 72386 writes it), b6ed8 (FR12 b6e5e writes it), c1094 (c0966 MOVE.L a2(A6),(A6) with LONG a2 = c1094 from c1088), the kind handler c1036 (record
# b3484 + 140, LONG 6; entered with A6 = the item node); the callee entries (branch targets of other units' blocks, the item handlers, table entries,
# helpers)
NODE_ENTRIES = (0x71502, 0x716ca, 0x7179a, 0x71e8c, 0x71f08, 0x72352, 0xb6ed8, 0xb6fa4, 0xb7096, 0xc0956, 0xc10a0, 0xc1170, 0xc1d0c, 0xc1094,
                0xc1036)
# the natural family also takes the FR1 item child b3dbc (its kind handler c1036 is FR12) and the FR11 installs b6e50 / c5602 (-> b6e5e / c5612)
NATURAL_ENTRIES = (0x71502, 0x716ca, 0x7179a, 0x71e8c, 0x71f08, 0x72352, 0xb6ed8, 0xb6fa4, 0xb7096, 0xc0956, 0xc10a0, 0xc1170, 0xc1d0c, 0xb6e50,
                   0xc5602, 0xb3dbc)
CALLEES = (0x70f8e, 0xb6c58, 0xcc7c0, 0xb41f2, 0xb6e5e, 0xc5612, 0xb42c4, 0xb42a2, 0xb4294, 0xc0924, 0xb402a, 0xb4304, 0x4d84e, 0xc1cf2, 0xb518c,
           0xb40f8, 0xb41b2, 0xc0944, 0xc115a, 0xc120c, 0xc1126, 0xc11ba, 0xc10b0, 0xc10d0, 0xb4212, 0xb4250, 0x716da, 0x717ae, 0xb42ea)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x76, 0x7a, 0xa2)   # node links, pointer fields, the handler LONGs 76 / 7a and the callback LONG a2
# natural worlds of the extended observation: (config, case, frame) with a pool node holding an FR12 node entry, b3dbc, b6e50 or c5602 (scratch
# natscan_fr12.py: per run and callback the first frame, the middle one of the first eight and the last one)
NATURAL = (('X1', 68, 508), ('X1', 68, 546), ('X1', 68, 689), ('X1', 68, 709), ('X1', 68, 712), ('X1', 68, 745), ('X1', 68, 746), ('X1', 68, 747),
           ('X1', 68, 750), ('X1', 68, 767), ('X1', 68, 797), ('X1', 68, 800), ('X1', 68, 818), ('X1', 94, 292), ('X1', 94, 330), ('X1', 94, 476),
           ('X1', 94, 479), ('X1', 94, 488), ('X1', 94, 489), ('X1', 94, 492), ('X1', 94, 504), ('X1', 94, 505), ('X1', 94, 507), ('X1', 94, 508),
           ('X1', 94, 511), ('X1', 94, 544), ('X1', 94, 545), ('X1', 94, 546), ('X1', 94, 549), ('X1', 94, 569), ('X1', 94, 614), ('X1', 94, 627),
           ('X2', 68, 508), ('X2', 68, 546), ('X2', 68, 713), ('X2', 68, 714), ('X2', 68, 717), ('X2', 68, 728), ('X2', 68, 729), ('X2', 68, 732),
           ('X2', 68, 733), ('X2', 68, 734), ('X2', 68, 736), ('X2', 68, 737), ('X2', 68, 769), ('X2', 68, 770), ('X2', 68, 771), ('X2', 68, 774),
           ('X2', 68, 793), ('X2', 68, 819), ('X2', 68, 822), ('X2', 68, 838), ('X2', 68, 840), ('X2', 94, 286), ('X2', 94, 324), ('X2', 94, 485),
           ('X2', 94, 488), ('X2', 94, 506), ('X2', 94, 507), ('X2', 94, 510), ('X2', 94, 513), ('X2', 94, 523), ('X3', 68, 510), ('X3', 68, 548),
           ('X3', 68, 678), ('X3', 68, 681), ('X3', 68, 714), ('X3', 68, 715), ('X3', 68, 716), ('X3', 68, 719), ('X3', 68, 745), ('X3', 68, 794),
           ('X3', 68, 797), ('X3', 68, 815), ('X3', 68, 1077), ('X3', 68, 1241), ('X3', 68, 1242), ('X3', 68, 1245), ('X3', 68, 1257),
           ('X3', 68, 1518), ('X3', 94, 290), ('X3', 94, 328), ('X3', 94, 482), ('X3', 94, 485), ('X3', 94, 518), ('X3', 94, 519), ('X3', 94, 520),
           ('X3', 94, 523), ('X3', 94, 543), ('X3', 94, 585), ('X3', 94, 588), ('X3', 94, 606), ('X3', 94, 958), ('X3', 94, 959), ('X3', 94, 1298),
           ('X4', 68, 510), ('X4', 68, 548), ('X4', 68, 775), ('X4', 68, 782), ('X4', 68, 802), ('X4', 68, 805), ('X4', 68, 838), ('X4', 68, 839),
           ('X4', 68, 840), ('X4', 68, 843), ('X4', 68, 846), ('X4', 68, 1172), ('X4', 68, 1173), ('X4', 94, 350), ('X4', 94, 388), ('X4', 94, 592),
           ('X4', 94, 622), ('X4', 94, 642), ('X4', 94, 645), ('X4', 94, 678), ('X4', 94, 679), ('X4', 94, 680), ('X4', 94, 683), ('X4', 94, 686),
           ('X4', 94, 1012), ('X4', 94, 1013))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
REINSTALL = ()

VB = (0, 1, 2, 3, 4, 5, 7, 8, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x3f, 0x40, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xef, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x21, 0x3f, 0x40, 0x62, 0x63, 0x64, 0x7f, 0x80, 0xbf, 0xc0, 0xc1, 0x100, 0x2800, 0x3000, 0x57ff,
      0x5800, 0x7fff, 0x8000, 0x8001, 0xc000, 0xffe0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x40000, 0x100000, 0x7fffffff, 0x80000000, 0xfff90000, 0xffff0000, 0xffffffe0, 0xffffffff,
      0x12345678)
# the handlers that the ROM writers of LONG 76(A6) produce for the FR11 JMP (A0) b4034 (FR11 decision 2); b42a2 / b4294 / c0924 are FR12 blocks
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
# flag-sharing Bcc pairs inside one block: c1130 CMPI.B #2,b6(A6); BEQ c113a; BEQ c120c and c11e2 CMPI.B #3,b6(A6); BEQ c11ec; BEQ c0944 (the later Bcc
# of each pair).  The earlier BEQ c1126 / c1130 (-> c113a) and c11ba / c11ce / c11d8 / c11e2 (-> c11ec) jump to the later BEQ with Z set: it is
# always taken (THREAD: c113a -> c120c, c11ec -> c0944), so the native trace passes the non-start PC c113a / c11ec inside the block.
BUNDLED = (0xc113a, 0xc11ec)
THREAD = {0xc113a: 0xc120c, 0xc11ec: 0xc0944}


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 70f8e / b6c58 / cc7c0 into FR10, b427a into FR11 b427e, 7176a / 7177c /
    717ae into the later-unit stops); a Bcc followed by a BUNDLED Bcc continues the block."""
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
    the computed jumps that the FR12 runs reach (OTHER_JUMP_PCS: FR11 b4034 / b42b4 / c54ae, FR1, FR4 cc7a8 / cc82a and the C3 .. C10 list), or at
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
        of the FR11 JMP (A0) b4034 produce (FR11 decision 2: b41be b4036 b42a2 b403e c0924 b4294; b4304 compares it with b4036 / b403e), BYTE 97(A6)
        0 / 4 / c (the FR11 b42b8 table), WORD 8e(A6) 0..7 mostly (the index of the ROM LONG tables b7fbc / b7fcc), D0.W 0..7 at the table anims
        b6eee / b6f2a / b7000 / b703c, the record index D0.B of 4d84e small mostly (the records 4cf64 + 16k), A0 a RAM record / node at 717ae
        (WORD 42(A0)) and at the child blocks c1246 .. c13aa (the 2986 child), LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), BYTE 1d(A6)
        < 4 (8ebe / 8ff4), BYTE 10fd82 = 0, WORD 90(A6) a multiple of 4 below 18 (the routed FR2 b4aca reads the LONG table b4ad4 by it after
        b4958; an odd index faults natively)."""
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
        if entry in (0xb6eee, 0xb6f2a, 0xb7000, 0xb703c):
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(8)
        if entry == 0x4d84e and rng.random() < 0.8:
            regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x20)
        if entry in (0x717ae, 0xc1246, 0xc12d4, 0xc1364, 0xc127c, 0xc128a, 0xc130c, 0xc131a, 0xc139c, 0xc13aa) and rng.random() < 0.7:
            regs['a0'] = rec + 0x20
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924))))   # LONG 76(A6): a handler
        if rng.random() < 0.5:
            writes.append(((a6 + 0x7a) & 0xffff, 4, rng.choice(HANDLERS + (0xb41be, 0xb403e))))   # LONG 7a(A6) (FR11 b3e1c)
        writes.append(((a6 + 0x97) & 0xffff, 1, rng.choice((0, 4, 0xc, 0xc))))                     # BYTE 97(A6): the kind-record value 0 / 4 / c
        writes.append(((a6 + 0x8e) & 0xffff, 2, rng.choice((0, 0, 1, 2, 3, 4, 5, 6, 7))))         # WORD 8e(A6): the table index
        writes.append(((a6 + 0x90) & 0xffff, 2, rng.choice((0, 4, 8, 0xc, 0x10, 0x14))))           # WORD 90(A6): the FR2 b4aca LONG table b4ad4 index
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
    require(len(STARTS) == 212 and len(STARTS_SET) == 212, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr12_block', ('start is not routed to objects fr12', hex(s), unit_of(s)))
    for t in THREAD:
        require(mine(t) and t not in STARTS_SET and THREAD[t] in STARTS_SET, ('bundled BEQ inside an FR12 block', hex(t)))
    # the FR11 computed-jump targets that FR12 routes (the handlers b42a2 / b4294 / c0924 of the JMP (A0) b4034, the table b42b8 entry c b42c4) and the
    # FR4 table cc7a8 entry cc7c0; the other FR11 targets (b4036, b42bc, the c54b2 entries) stay unrouted stops
    for t in (0xb42a2, 0xb4294, 0xc0924, 0xb42c4, 0xcc7c0):
        require(unit_of(t) == 'animation_objects_fr12_block', ('computed-jump target routed to FR12', hex(t)))
    for t in (0xb4036, 0xb42bc):
        require(unit_of(t) is None, ('FR11 computed-jump target stays unrouted', hex(t)))
    rng = random.Random(0xF12A)
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
    sys.stderr.write('fr12 spec: %d fixtures (%d natural), visited %d/212, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr12: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr12: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the record index of 4d84e,
    the BYTE 86 of 716ca, the same-WORD SUB of 716da, the LONG sign of 7177c, the LSL.L / SWAP of 71788, the unsigned WORD compare of 717ae (80),
    the ASR.L #5 of 72352 / b7096, the MULS.W rotation of b41f2 / b4212 (D4 40 / c0 / the table index, D7), the c000 dead zone of b4250 .. b427a,
    the BYTE step of b42f0 / b42f8, the handler compare of b4304, WORD 7c ffff of b6e5e, WORD 82 = 1 of b6f62, BYTE 9c / WORD 84 counts of b70b8 /
    b70ee, the WORD 64 sign of c0924, the ROR / SMI / EOR of c106e, the ASR.W / EXT / LSL of c10b0, the LSR.W b0 of c10d0, the mirror and MULU.W
    #10 sector of c1108 .. c11e2, the random WORD bounds of c126a .. c13aa, the BYTE 15 / 61 / 9f bits), the upper register bits of the WORD / BYTE
    operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x4d84e, 0x71502, 0x716ca, 0x716da, 0x7177c, 0x71788, 0x717ae, 0x71eee, 0x72336, 0x72352, 0xb402a, 0xb40fe, 0xb41f2, 0xb4212, 0xb4250,
                 0xb42f8, 0xb4304, 0xb518c, 0xb6c58, 0xb6e5e, 0xb6e6e, 0xb6f62, 0xb7074, 0xb7096, 0xb70b8, 0xb70ee, 0xc0924, 0xc0966, 0xc1036, 0xc1048,
                 0xc106e, 0xc1094, 0xc10b0, 0xc10d0, 0xc10e2, 0xc10f2, 0xc1112, 0xc115a, 0xc118a, 0xc11ba, 0xc120c, 0xc126a, 0xc127c, 0xc128a, 0xc13aa):
        h += [dict(regs=dict(up))] + mirror
    if entry == 0x4d84e:
        h += [dict(regs=dict(up, d0=0x12345600 | v)) for v in (0, 1, 2, 3, 4, 7, 8, 0xf, 0x10, 0x1f, 0x80, 0xff)]
    if entry == 0x716ca:
        h += byte(0x86, (0, 1, 0x80, 0xff))
    if entry == 0x716da:
        h += word(0x46, (0, 0x30, 0x31, 0x8000, 0xffff, 0x7fff))
    if entry in (0x71502, 0x716fe, 0x71e8c, 0x722da):
        h += word(0x9c, (0, 1, 0x8000, 0x100))
    if entry in (0x7175a,):
        h += byte(0x82, (0, 1, 0xfe, 0xff))
    if entry in (0x71764, 0x7176a, 0xb6c58, 0xb6f88, 0xc1cfe, 0xc10f2, 0xc119a, 0xc126a, 0xc12f8, 0xc1388):
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x7177c:
        h += [dict(regs=dict(up, d0=v)) for v in (0x40000, 0xfffc0000, 0, 0x80000000, 0x7fffffff)]
    if entry == 0x71788:
        h += [dict(regs=dict(up, d0=v)) for v in (0x40000, 0x3ffffff, 0x12345678, 0xffffffff, 0x0200fe00)]
    if entry in (0x7179a, 0x71f08, 0x7237c, 0xb4294, 0xb42a2, 0xc095c, 0xc10a6, 0xc10c6, 0xc10d8, 0xc1112, 0xc1176, 0xc1180):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry == 0x717ae:
        for w0, w6 in ((0x40, 0), (0x3f, 0), (0, 0x41), (0, 0x40), (0x8000, 0x7fc0), (0x7fff, 0x8000), (0xffc0, 0)):
            h.append(dict(regs=dict(up), regrec=dict(a0=0x20), rec=[(0x62, 2, w0)], a6off=[(0x42, 2, w6)]))
    if entry in (0x717d4, 0xb6fae, 0xb70ce, 0xb70e4):
        h += byte(0x61, (0, 1, 2, 8, 0xff, 0xf7, 0xfd, 0xfe))
    if entry == 0x71eee:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x3f, 0x40, 0xffff, 0x12340030)]
    if entry == 0x72336:
        h += [dict(a6off=[(0x64, 4, v), (0x36, 4, 0x5a5a5a5a), (0x3a, 4, 0x12345678)]) for v in (0, 0x80000000, 0xfffc0000)]
    if entry == 0x72352:
        for l64, l36, l3a in ((0, 0, 0), (0x40000, 0, 0xfff00000), (0, 0x40000, 0), (0x80000000, 0x7fffffff, 0x7fffffff), (0xffffffe0, 0x1f, 0xffefffff)):
            h.append(dict(regs=dict(up), a6off=[(0x64, 4, l64), (0x36, 4, l36), (0x3a, 4, l3a)]))
    if entry == 0xb402a:
        h += [dict(regs=dict(up, a0=v)) for v in (0xb42a2, 0xc0924, 0xb4294)]
    if entry in (0xb40fe, 0xb41b8):
        h += [dict(regs=dict(up, d4=v)) for v in (0x12348000, 0xffff, 0)]
    if entry == 0xb41f2:
        for d0, d1, d4, d7 in ((0x12345678, 0x9abcdef0, 0x40, 0x7fff), (0x80000000, 0x7fffffff, 0xc0, 0x8000), (0xff00, 0xffffff00, 0x12345641, 0x1234ffff),
                               (0x40000, 0xfffc0000, 0x99aa00c0, 0x100), (0x7fff00, 0x800000, 0x80, 0x8001), (0, 0x100, 0, 0)):
            h.append(dict(regs=dict(up, d0=d0, d1=d1, d4=d4, d7=d7)))
    if entry == 0xb4200:
        h += [dict(regs=dict(up, d4=v)) for v in (0xc0, 0x40, 0x12345600, 0xc1, 0x1c0)]
    if entry == 0xb4212:
        for d0, d1, d4 in ((0x12345678, 0x9abcdef0, 0), (0x7fff0000, 0x80000000, 0xff), (0xffff8000, 0x00800000, 0x80), (0x40000000, 0xc0000000, 0x7f),
                           (0x100, 0xffffff00, 0x12345640), (0, 0, 0x99aa0020), (0x3ffffff, 0xfc000000, 0x1ff)):
            h.append(dict(regs=dict(up, d0=d0, d1=d1, d4=d4)))
    if entry == 0xb4250:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0xc000, 0xbfff, 0xffff4000, 0xffff4001, 0x80000000, 0xffffffff)]
    if entry in (0xb4260, 0xb4274):
        for v in (0xc000, 0xbfff, 0xc001, 0, 0x80000000, 0xffffffff):
            h.append(dict(regs=dict(up, d0=v, d1=v, d7=0xc000)))
    if entry in (0xb426a,):
        h += [dict(regs=dict(up, d1=v)) for v in (0, 0x80000000, 0xffff4000, 0x7fffffff)]
    if entry in (0xb425e, 0xb4272):
        h += [dict(regs=dict(up, d0=v, d1=v)) for v in (0x80000000, 0xffffffff, 0xffff4000)]
    if entry == 0xb42f0:
        h += [dict(regs=dict(up, d0=v)) for v in (0x80, 0x7f, 0x12345680, 0xff00)]
    if entry == 0xb42f8:
        for d0, d4 in ((0x80, 0x40), (0xff, 0xff), (0x9c, 0x12345600), (0x8c, 0xfe), (0x90, 0x80), (0xe3, 0x7f)):
            h.append(dict(regs=dict(up, d0=d0, d4=d4)))
    if entry == 0xb4304:
        h += [dict(regs=dict(up), a6off=[(0x76, 4, v)]) for v in (0xb4036, 0xb403e, 0xb41be, 0, 0x10b4036, 0xb4037, 0xc0924)]
    if entry == 0xb4312:
        h += [dict(regs=dict(up, d0=v)) for v in (0xb403e, 0xb4036, 0x10b403e, 0xb403f)]
    if entry == 0xb518c:
        h += [dict(regs=dict(up, a0=v)) for v in (0, 0x80000000, 0x10e900)]
    if entry == 0xb6e5e:
        h += word(0x7c, (0xffff, 0xfffe, 0, 0x7fff, 0x8000))
    if entry == 0xb6e6e:
        h += byte(0x9d, (0, 1, 0x81, 0xff))
    if entry == 0xb6ed8:
        h += byte(0x9f, (0, 2, 0xfd, 0xff))
    if entry in (0xb6ee2, 0xb6ff4):
        h += [dict(regs=dict(up), a6off=[(0x8e, 2, v)]) for v in (0, 1, 3, 0x100)]
    if entry in (0xb6eee, 0xb6f2a, 0xb7000, 0xb703c):
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 1, 2, 7)]
    if entry == 0xb6f62:
        h += [dict(regs=dict(up), a6off=[(0x82, 2, v), (0x15, 1, b)]) for v, b in ((1, 0), (0, 0xff), (0x101, 1), (0xffff, 0xfe), (0x8001, 0))]
    if entry == 0xb6f9a:
        h += [dict(a6off=[(0x64, 4, v)]) for v in (0x40000, 0, 0x80000000)]
    if entry == 0xb7096:
        h += [dict(regs=dict(up), a6off=[(0x3a, 4, v)]) for v in (0, 0xfffe0000, 0x7fffffff, 0x80000000, 0xfffe0007, 0x60000)]
    if entry == 0xb70b8:
        h += byte(0x9c, (1, 2, 0, 0x81))
    if entry == 0xb70ee:
        h += word(0x84, (0, 1, 0x8000, 0x8001, 0xffff))
    if entry == 0xc0924:
        h += [dict(regs=dict(up), a6off=[(0x64, 4, v)]) for v in (0, 1, 0x10000, 0xffff0000, 0x80000000, 0x7fffffff, 0xffffffff, 0x00008000)]
    if entry == 0xc0966:
        h += [dict(a6off=[(0xa2, 4, v)]) for v in (0xc1094, 0, 0x12345678)]
    if entry == 0xc0976 or entry in (0xc114a, 0xc11fc, 0xc1d1e):
        h += [dict(regs=dict(up, d0=v)) for v in (4, 0xfb, 0x104, 0xfffffffb)]
    if entry == 0xc106e:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0x0080, 0x007f, 0xff80, 0x1234, 0xffff, 0x0300, 0x8000, 0)]
    if entry == 0xc10b0:
        for b4, l36 in ((0, 0), (7, 0x10000), (8, 0x7fffffff), (0x8000, 0), (0x7fff, 0x80000000), (0xfff8, 0xffffffff), (0xfff9, 0x12345678)):
            h.append(dict(regs=dict(up), a6off=[(0xb4, 2, b4), (0x36, 4, l36)]))
    if entry == 0xc10d0:
        h += word(0xb0, (0, 1, 2, 3, 0x8000, 0xffff))
    if entry in (0xc10e2, 0xc118a):
        disp = 0x36 if entry == 0xc10e2 else 0x64
        for l, b4 in ((0, 0), (0x100000, 0x8000), (0xfff00000, 0x7fff), (0x7fffffff, 0x1234), (0x80000000, 0xffff), (0x3f, 1)):
            h.append(dict(regs=dict(up), a6off=[(disp, 4, l), (0xb4, 2, b4)]))
    if entry in (0xc10f2, 0xc119a):
        h += [dict(regs=dict(up), a6off=[(0xb4, 2, a), (0xb2, 2, b), (0x15, 1, f)]) for a, b, f in ((0x8000, 0x8000, 0), (0x7fff, 1, 1), (0xffff, 1, 0xff))]
    if entry in (0xc1108, 0xc11b0):
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0x4000, 0, 0x8000, 0xc000, 0x4001, 0xffff)]
    if entry in (0xc1112, 0xc11ba):
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0x0fff, 0x1000, 0x2000, 0x2fff, 0x3000, 0x3fff, 0xffff, 0)]
    if entry in (0xc1126, 0xc1130, 0xc11ce, 0xc11d8, 0xc11e2):
        h += byte(0xb6, (0, 1, 2, 3, 4, 0xff))
    if entry in (0xc126a, 0xc12f8, 0xc1388):
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (0, 0x1ff, 0x200, 0xffff, 0xfeff)]
    if entry in (0xc127a, 0xc130a, 0xc139a):
        h += [dict(regs=dict(up, d0=v)) for v in (0x12340000, 0x12348000, 0x1234ffff)]
    if entry in (0xc127c, 0xc130c, 0xc139c, 0xc128a, 0xc131a, 0xc13aa):
        h += [dict(regs=dict(up, d0=0x12340000 | v), regrec=dict(a0=0x20)) for v in (0x8000, 0x7fff, 0xffff, 0, 0x1ff)]
    if entry in (0xc1246, 0xc12d4, 0xc1364):
        h += [dict(regs=dict(up, d2=0x21, d3=0xffffffff, d4=0, d5=0x8000, d6=0x7fff), regrec=dict(a0=0x20))]
    if entry == 0xc1cf8:
        h += [dict(regs=dict(up, d0=v)) for v in (0x80, 0x7f, 0xff00, 0x12345680)]
    if entry in (0xc120c, 0xc128a, 0xc131a):
        h += [dict(writes=[(0x4ca0, 2, v)]) for v in (0x40, 0x15)]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry == 0x716f4:
        return dict(regs=dict(d0=0x12345600 | (t % 0x40)))                         # 4d84e: the record 4cf64 + 16 x D0.B, WORD a = 0 -> Set
    if entry == 0x716ea:
        return dict(a6off=[(0x86, 1, (0, 1, 2, 3, 4, 5, 6, 7)[t % 8])])              # 4d7a6 (D0 = BYTE 86) -> 4d84e
    if entry == 0x717a4:
        return dict(writes=[(0xd68e, 1, (0, 1)[t % 2])])                           # 4945e: BYTE 568e(A5) != 0 -> Clear (FR1b 5a588)
    if entry == 0x71f18:
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
    if entry == 0xb6e6e:
        # 49392: BYTE 568e(A5) bit (D0 & 1) with D0.B = BYTE 9d(A6) -> Set
        return dict(a6off=[(0x9d, 1, (0, 1, 2, 0x81)[t % 4])], a5off=[(0x568e, 1, (0, 1, 2, 3)[(t // 4) % 4])])
    if entry == 0xc105e:
        return dict(a6off=[(0x76, 4, (0xb4036, 0xb403e, 0xb41be, 0xc0924)[t % 4])])   # b4304: LONG 76 = b4036 / b403e -> Clear
    if entry in (0xc120c, 0xc128a, 0xc131a):
        return dict(writes=[(0x4ca0, 2, (0x40, 0x15, 0x40, 0x14)[t % 4])])          # 2986 (the Clear side 290e is the C++ caller-X error)
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 15 bits 0 / 7, BYTE 61 bits 0 / 1 / 3, BYTE 9c / 9f / 86 / 9d / b6, WORD 8e (the table index 0..3), WORD
            # 7c (b6e5e), WORD 82 (b6f62), WORD 84 (b70ee), WORD b0 / b2 / b4 (the turn), LONG 26 (0: 49fc6 Set), LONG 36 / 3a / 64, the
            # handler LONG 76, BYTE 97 (the FR11 b42b8 table), LONG a2 (c0966)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 1, 0x81, 0xff, 0x7f, 0xfe)[t % 7]), (0x61, 1, (0, 1, 2, 8, 0xb, 0xff)[(t // 2) % 6]),
                               (0x9c, 1, (0, 1, 2, 8)[(t // 3) % 4]), (0x9f, 1, (0, 2)[(t // 2) % 2]), (0x86, 1, (0, 1)[(t // 5) % 2]),
                               (0x9d, 1, (0, 1)[(t // 2) % 2]), (0x8e, 2, (0, 1, 2, 3)[(t // 4) % 4]), (0x7c, 2, (0xffff, 0, 1, 0xffff)[(t // 3) % 4]),
                               (0x82, 2, (1, 0, 1, 2)[(t // 2) % 4]), (0x84, 2, (0, 1, 0x1e)[(t // 3) % 3]),
                               (0xb0, 2, (0xf, 1, 0, 2)[(t // 2) % 4]), (0xb4, 2, (0, 0x800, 0xf800, 0x3ff)[(t // 3) % 4]),
                               (0xb2, 2, (0, 0x4000, 0x8000, 0xc000)[(t // 5) % 4]), (0x36, 4, (0, 0x80000000, 0x100000, 0xfff00000)[(t // 6) % 4]),
                               (0x3a, 4, (0, 0xfffc0000, 0x12345)[(t // 4) % 3]), (0x64, 4, (0, 0x40000, 0xfffc0000, 0x10000)[(t // 5) % 4]),
                               (0x76, 4, (0xb41be, 0xb403e, 0xb42a2, 0xb4294, 0xc0924, 0xb4036)[(t // 2) % 6]), (0x97, 1, (0, 4, 0xc, 0)[(t // 5) % 4]),
                               (0xa2, 4, (0xc1094, 0xc1094, 0)[(t // 3) % 3])] +
                        ([(0x26, 4, 0)] if t % 5 != 4 else []), writes=[(0x4ca0, 2, (0x40, 0x40, 0x15)[t % 3]), (0xd68e, 1, (0, 1)[(t // 3) % 2])])
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
    err('odd-pc', U.with_host_writes(st, pc=0xc1037), 'unaligned animation machine PC', 0xc1037)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('71502-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x71502), odd_word, 0x71502)
    err('c0924-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xc0924), odd_word, 0xc0924)
    err('b6e5e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb6e5e), odd_write, 0xb6e5e)
    err('b4250-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb4250), odd_write, 0xb4250)
    err('c1094-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xc1094), odd_write, 0xc1094, stop=0xc10a0)
    err('b6c58-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb6c58), odd_write, 0xb6c58, stop=0xb6c66)
    err('717ae-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0x717ae), odd_word, 0x717ae)
    err('c1246-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0xc1246), odd_write, 0xc1246, stop=0x49214)
    err('c127c-odd-a0', U.with_host_writes(st, regs=dict(a0=SCR + 1), pc=0xc127c), odd_write, 0xc127c, stop=0x49a58)
    err('b402a-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb402a), odd_word, 0xb402a)
    err('b42f6-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb42f6), odd_word, 0xb42f6)
    err('c120c-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xc120c), odd_word, 0xc120c, stop=0x2986)
    # failures after executed blocks: the later-unit stops (FR13 / FR14) and the unrouted FR11 handler b4036 reached through the unit
    err('7176a-then-7177a', U.with_host_writes(st, [((a6 + 0x15) & 0xffff, 1, 0)], pc=0x7176a), unrouted, 0x7177a)
    err('7177c-then-71786', U.with_host_writes(st, regs=dict(d0=0x80000000), pc=0x7177c), unrouted, 0x71786)
    # objects FR13 routes 71682 / 717c2 since FR13 (FR13 contract; was: 71532-then-71682 / 717ae-then-717c2 with 'unsupported animation machine PC' at
    # the FR13 PC): 71682 reads WORD 7a of the odd node; 717c2 runs on to FR12 717c8 (the JSR 4bfa4 push on the odd A7)
    err('71532-then-71682', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x71532), odd_word, 0x71682)
    err('717ae-then-717c8-odd-stack', U.with_host_writes(st, [((SCR + 0x62) & 0xffff, 2, 0), ((a6 + 0x42) & 0xffff, 2, 0)], regs=dict(a0=SCR + 0x20, a7=a7 + 1),
                                                            pc=0x717ae), odd_word, 0x717c8)
    err('c1d06-then-b4036', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 4, 0xb4036)], pc=0xc1d06), unrouted, 0xb4036)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0xb4212, 0xc106e, 0xc0924, 0x72352)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
