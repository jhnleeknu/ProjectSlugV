"""V1 fixture spec of the area-D unit FR10 (engine/src/animation_machine_objects_fr10.cpp, 211 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr10-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 FR10 row without
the C7 table entry 252b4 -> 252ce (main decision 4: C10) and with the branch target cd804 of the sibling cd7c2): the object states 70e2a (FR2b
install) -> 70ea2 / 70efe / 70f12 / 70f2c -> 70f3e .. 7102e with the C helper 70594 (also the N15 711b6 callee), 713d8 / 71468 (N15 / FR2b installs)
-> 7143a / 714ca, the U18 install b6ba0 -> b6c2c / b6c66 -> b6c72 with the helpers b7a62 (MOVEM.W D0-D1 around 49392, 4e122) and b7b30 (U19 callee;
EORI.B #1,CCR), the FR4 table entries cc7c4 / cc7d0 / cc846 -> cd94e / cd7c6 / ccaf8, the script callbacks 6f1ca / cca44 / cca52 (interpreter table
4a500), the states ccaf8 / cd7c6 .. cd8e0 -> cd8ee / cd94e -> cda34 -> cdafc with the C helper ccade, the 28ae child cdd86 -> cde6e, the U18 install
eaa00 -> eaa20 and the 28ae child eaac0 (C9 / FR3) -> eab2a.  No computed jump, no TRAP, no JSR (An).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C9) with declared host edits.
This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X1..X4 x cases 68 / 94): the 'natural'
family takes the frame-start states of that observation (state packs, read-only) in which a node of the pool 100800..104c00 holds an FR10 node entry
as its callback LONG, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return
LONG, PC = the callback).  The spec reads those packs itself (io_pack below, observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 14 C consumers (13 BCC / BCS / MOVEM+BCC and the EORI b7b40) and the flag readers 70ff4 (Z) / cd80a (N) is
            entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers and the flag readers through 70ff0 / cd804 (CHAINS).  Stop: the successor or the first
            unrouted PC.
  node      the callbacks and installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the helpers, script callbacks and table entries entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 14 consumers, the N source of cd80a outside work RAM / fixed ROM
            (decision 3), odd node / stack / A0 / A1, failures after executed blocks: checked error, state preserved, every row with its failing PC (a
            paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C9
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
UNIT_NAME = 'fr10'
ERROR_PC = 'unsupported animation objects fr10 PC'
ERROR_CARRY = 'objects fr10 caller requires known carry'
ERROR_FLAG = 'unsupported animation objects fr10 flag source'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x4e122, 0x4e132), (0x6f1ca, 0x6f1d4), (0x70594, 0x705ca), (0x70e2a, 0x70e42), (0x70ea2, 0x70f60), (0x70f84, 0x70f8e), (0x70f94, 0x70fac),
          (0x70fc2, 0x70fcc), (0x70fd2, 0x70ff8), (0x70ffa, 0x71028), (0x7102e, 0x71032), (0x713d8, 0x71502), (0xb6ba0, 0xb6c58), (0xb6c66, 0xb6ca2),
          (0xb7a62, 0xb7acc), (0xb7b30, 0xb7b4c), (0xcc7c4, 0xcc7c8), (0xcc7d0, 0xcc7d4), (0xcc846, 0xcc84a), (0xcca44, 0xcca5a), (0xccade, 0xccbc0),
          (0xcd7c6, 0xcd7e2), (0xcd7e4, 0xcd92e), (0xcd93c, 0xcd96c), (0xcda34, 0xcdb08), (0xcdd86, 0xcddba), (0xcde6e, 0xcde96), (0xeaa00, 0xeaa54),
          (0xeaac0, 0xeab42)]
STARTS = sorted(int(x, 16) for x in (
    '4e122 6f1ca 70594 705a0 705aa 705be 705c4 70e2a 70ea2 70eaa 70ed2 70ed6 70efe 70f12 70f2a 70f2c 70f3e 70f48 70f4e 70f84 70f8a 70f94 70fc2 70fd2 70fd6 '
    '70fda 70fe0 70fe4 70fe8 70fea 70fec 70ff0 70ff4 70ffa 70ffe 71002 71008 71012 71016 7101a 71020 7102e 713d8 713e0 71408 7140c 71434 7143a 7144e 71454 '
    '7145a 7145e 71464 71468 71470 71498 7149c 714c4 714ca 714d4 714e4 714ea 714ee 714f8 714fe b6ba0 b6ba8 b6bb8 b6bf0 b6bf4 b6c2c b6c46 b6c66 b6c72 b6c76 '
    'b6c7c b6c84 b6c98 b6c9e b7a62 b7a68 b7a6c b7a6e b7a78 b7a80 b7a86 b7a8c b7a9c b7aa8 b7ab2 b7ab6 b7ac0 b7ac2 b7ac8 b7aca b7b30 b7b3a b7b40 b7b46 cc7c4 '
    'cc7d0 cc846 cca44 cca4c cca52 ccade ccae6 ccaf0 ccaf6 ccaf8 ccb00 ccb16 ccb1a ccb22 ccb38 ccb3c ccb44 ccb5a ccb5e ccb66 ccb7c ccb80 ccb88 ccb9e ccba2 '
    'ccbb8 cd7c6 cd7cc cd7e4 cd7f2 cd804 cd80a cd80e cd814 cd828 cd83e cd842 cd84a cd860 cd864 cd86c cd882 cd886 cd88e cd8a4 cd8a8 cd8b0 cd8c6 cd8ca cd8e0 '
    'cd8ee cd8f8 cd8fe cd912 cd916 cd922 cd92a cd93c cd940 cd944 cd94a cd94e cd956 cd95a cda34 cda3c cda52 cda56 cda5e cda74 cda78 cda80 cda96 cda9a cdaa2 '
    'cdab8 cdabc cdac4 cdada cdade cdaf4 cdafc cdb00 cdb04 cdd86 cdd9c cdda0 cddae cddb2 cde6e eaa00 eaa1a eaa20 eaa26 eaa34 eaa3a eaa3e eaa44 eaa4c eaa52 '
    'eaac0 eaac6 eaaca eaad0 eaada eaafe eab2a eab30 eab36 eab3a eab40'
    ).split())
# the 13 C consumers: BCC 70f8a 7145a 714ea eab36 (49fc6), 70fd6 (7028e), 70ffe (705ca), 71016 (70594), b7a68 (484e2), b7a78 (MOVEM.W (A7)+,D0-D1;
# 49392), cd940 (ccade), cdd9c (28ae), eaa3a (eaa26 Clear / 49fc6), BCS eaac6 (1abda); and b7b40 (EORI.B #1,CCR; RTS: the known C of 4941e inverted)
CONSUMERS = (0x70f8a, 0x7145a, 0x714ea, 0xeab36, 0x70fd6, 0x70ffe, 0x71016, 0xb7a68, 0xb7a78, 0xcd940, 0xcdd9c, 0xeaa3a, 0xeaac6, 0xb7b40)
CLEAR_SET = (0x705c4, 0xb7b46, 0xccade, 0xeaa26, 0x70f2c)   # ANDI.B #fe,CCR (705c4 b7b46 eaa26), TST.B (ccade), MOVE.L last (70f2c)
SET_SET = (0x705be, 0xcddae)            # ORI.B #1,CCR
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x70ff0,)                   # CMPA.W #0,A0 followed by the Z reader 70ff4: its block fixture stops at 70ff4 (no flag is compared at a stop)
INVERT_SET = (0xb7b40,)
PASS_SET = (0xccae6, 0xccaf6, 0x70f3e)  # BTST+BNE / RTS / BTST+BEQ keep the incoming C (ccade Clear / 4b54e -> cd940; 70f2c Clear -> N15 71c48)
STARTS_SET = set()
Z_READERS = (0x70ff4, 0xcd80a)          # BEQ.W on the Z of CMPA.W #0,A0 (70ff0), BPL.W on the N of the 49a58 SUB.W D0,(A3) (decision 3)
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units that an FR10 block reaches by a fall-through or a branch (FR11 70e42 70fac cd7e2 cd92e cd96c, FR12 70f8e b6c58, FR13 70f60 70fcc
# 70ff8 71028), and the still unrouted later-unit stops of the C1..C9 blocks (pc9 EXIT_STOPS).  Declared stops of the native runs: a straight-line
# unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x70e42, 0x70fac, 0xcd7e2, 0xcd92e, 0xcd96c, 0x70f8e, 0xb6c58, 0x70f60, 0x70fcc, 0x70ff8, 0x71028,
              0x1f082, 0x20bfe, 0x22148, 0x22286, 0x223fa,
              0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x1dc8e, 0x1dccc, 0x1efd6, 0x21dd0, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6,
              0x4e69a,
              # player C10 routes the entries below since C10 (declared stops of the FR10 runs, as before C10)
              0x20324, 0x21e04, 0x2228e, 0x22360, 0x252b4)
UNIT_EXITS = EXIT_STOPS[:11]            # the FR10 later-unit stops (FR11 / FR12 / FR13)
ROUTED_LATER = (
    # player C10 (the C10 entries kept as declared stops)
    0x1dc8e, 0x1dccc, 0x1efd6, 0x1f082, 0x20bfe, 0x21dd0, 0x22148, 0x22286, 0x223fa, 0x20324, 0x21e04, 0x2228e, 0x22360, 0x252b4,
    # objects FR11 (the FR11 entries kept as declared stops of the FR10 runs, as before FR11)
    0x70e42, 0x70fac, 0xcd7e2, 0xcd92e, 0xcd96c)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the flag chains 70ff0 -> 70ff4, cd804 -> cd80a
CHAINS = ((0x70f84, 0x70f8a), (0x71454, 0x7145a), (0x714e4, 0x714ea), (0xeab30, 0xeab36), (0x70fd2, 0x70fd6), (0x70ffa, 0x70ffe), (0x71012, 0x71016),
          (0xb7a62, 0xb7a68), (0xb7a6e, 0xb7a78), (0xcd93c, 0xcd940), (0xcdd86, 0xcdd9c), (0xeaa26, 0xeaa3a), (0xeaa34, 0xeaa3a), (0xeaac0, 0xeaac6),
          (0xb7b3a, 0xb7b40), (0x70ff0, 0x70ff4), (0xcd804, 0xcd80a))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()                           # no computed jump in FR10
JUMP_ROUTED = ()
LIST_JUMPS = {}                         # no JMP (A1) in FR10
# computed jumps that the FR10 runs reach (FR4 cc7a8 / cc82a from cdb00 BSR.W cc778; the C9 list): an unrouted target is a stop even when it is the
# straight-line successor
OTHER_JUMP_PCS = (0xcc7a8, 0xcc82a, 0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76,
                  0x21ce4, 0x21d36, 0x2224c, 0x22428)
TABLE_ENTRIES = ()
# the callbacks and installed values entered as node callbacks: 70e2a (FR2b 70cba), 713d8 (N15 71126 71148), 71468 (FR2b 70cee, N15 71136), b6ba0
# (U18 b76c8), eaa00 (U18 ea9e4), the in-range installs 70f3e 7143a 714ca b6c72 cd8ee cdafc eaa20 eab2a, the 28ae children eaac0 (C9 20cd8 20d44, FR3
# ea6d4) and cde6e (cdd86); the callee entries (helpers, script callbacks of the interpreter table 4a500, the FR4 table entries and their states)
NODE_ENTRIES = (0x70e2a, 0x713d8, 0x71468, 0xb6ba0, 0xeaa00, 0x70f3e, 0x7143a, 0x714ca, 0xb6c72, 0xcd8ee, 0xcdafc, 0xeaa20, 0xeab2a, 0xeaac0, 0xcde6e)
CALLEES = (0x4e122, 0x6f1ca, 0x70594, 0xb7a62, 0xb7b30, 0xcc7c4, 0xcc7d0, 0xcc846, 0xcca44, 0xcca52, 0xccade, 0xcd7c6, 0xcd94e, 0xccaf8, 0xcdd86,
           0xcd804, 0x70efe, 0x70fe0)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26)   # node links and pointer fields: natural or declared below
# natural worlds of the extended observation: (config, case, frame) with a pool node holding an FR10 node entry (scratch natscan_fr10.py: per run and
# callback the first frame and a middle one of the first eight)
NATURAL = (('X1', 68, 546), ('X1', 68, 547), ('X1', 68, 551), ('X1', 68, 606), ('X1', 68, 607), ('X1', 68, 610), ('X1', 68, 614), ('X1', 68, 618), ('X1', 68, 655), ('X1', 68, 656), ('X1', 68, 657), ('X1', 68, 724), ('X1', 68, 828), ('X1', 68, 829), ('X1', 68, 833), ('X1', 68, 852), ('X1', 68, 853), ('X1', 68, 856), ('X1', 68, 874), ('X1', 94, 340), ('X1', 94, 341), ('X1', 94, 345), ('X1', 94, 410), ('X1', 94, 413), ('X1', 94, 451), ('X1', 94, 452), ('X1', 94, 454), ('X1', 94, 455), ('X1', 94, 456), ('X1', 94, 465), ('X1', 94, 466), ('X1', 94, 469), ('X1', 94, 532), ('X1', 94, 621), ('X1', 94, 622), ('X1', 94, 659), ('X1', 94, 661), ('X2', 68, 504), ('X2', 68, 505), ('X2', 68, 508), ('X2', 68, 564), ('X2', 68, 565), ('X2', 68, 569), ('X2', 68, 633), ('X2', 68, 637), ('X2', 68, 647), ('X2', 68, 648), ('X2', 68, 650), ('X2', 68, 679), ('X2', 68, 680), ('X2', 68, 681), ('X2', 68, 696), ('X2', 68, 701), ('X2', 68, 702), ('X2', 68, 706), ('X2', 68, 756), ('X2', 68, 873), ('X2', 94, 291), ('X2', 94, 292), ('X2', 94, 296), ('X2', 94, 342), ('X2', 94, 343), ('X2', 94, 347), ('X2', 94, 410), ('X2', 94, 414), ('X2', 94, 479), ('X2', 94, 480), ('X2', 94, 484), ('X2', 94, 513), ('X2', 94, 514), ('X2', 94, 518), ('X2', 94, 564), ('X2', 94, 629), ('X2', 94, 667), ('X3', 68, 592), ('X3', 68, 596), ('X3', 68, 624), ('X3', 68, 625), ('X3', 68, 626), ('X3', 68, 647), ('X3', 68, 651), ('X3', 68, 690), ('X3', 68, 691), ('X3', 68, 695), ('X3', 68, 831), ('X3', 68, 832), ('X3', 68, 836), ('X3', 68, 1118), ('X3', 68, 1119), ('X3', 68, 1121), ('X3', 68, 1170), ('X3', 68, 1262), ('X3', 68, 1289), ('X3', 68, 1290), ('X3', 68, 1291), ('X3', 68, 1392), ('X3', 68, 1393), ('X3', 68, 1397), ('X3', 94, 377), ('X3', 94, 378), ('X3', 94, 382), ('X3', 94, 387), ('X3', 94, 391), ('X3', 94, 428), ('X3', 94, 429), ('X3', 94, 430), ('X3', 94, 436), ('X3', 94, 437), ('X3', 94, 441), ('X3', 94, 498), ('X3', 94, 499), ('X3', 94, 503), ('X3', 94, 684), ('X3', 94, 688), ('X3', 94, 949), ('X3', 94, 950), ('X3', 94, 953), ('X4', 68, 597), ('X4', 68, 598), ('X4', 68, 602), ('X4', 68, 613), ('X4', 68, 617), ('X4', 68, 620), ('X4', 68, 621), ('X4', 68, 625), ('X4', 68, 670), ('X4', 68, 671), ('X4', 68, 675), ('X4', 68, 748), ('X4', 68, 749), ('X4', 68, 750), ('X4', 68, 780), ('X4', 68, 831), ('X4', 68, 875), ('X4', 68, 880), ('X4', 68, 904), ('X4', 68, 942), ('X4', 68, 1135), ('X4', 68, 1136), ('X4', 68, 1140), ('X4', 94, 437), ('X4', 94, 438), ('X4', 94, 442), ('X4', 94, 453), ('X4', 94, 457), ('X4', 94, 463), ('X4', 94, 464), ('X4', 94, 468), ('X4', 94, 510), ('X4', 94, 511), ('X4', 94, 515), ('X4', 94, 588), ('X4', 94, 589), ('X4', 94, 590), ('X4', 94, 627), ('X4', 94, 631), ('X4', 94, 691), ('X4', 94, 715), ('X4', 94, 716), ('X4', 94, 744), ('X4', 94, 776), ('X4', 94, 976), ('X4', 94, 980))
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
BUNDLED = ()                            # no flag-sharing Bcc pair inside one FR10 block (70ff4 / cd80a are their own blocks: decision 3)


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 70e2a / 70f4e / 70f94 / 70fc2 / 71020 / 713d8.. / b6c2c / cd7cc / cd8ee /
    cd95a into the later-unit PC after the range)."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (none in FR10) would use pcs[n - 1]."""
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
    the computed jumps that the FR10 runs reach (OTHER_JUMP_PCS: FR4 cc7a8 / cc82a and the C3 .. C9 list), or at the
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it: WORD 76(A6) 0..3 (the index of the ROM LONG tables
        ea732 / eaa5c of eaa00 / eaada, 4 LONGs each), WORD 8c(A6) 0..5 mostly (the anim selectors ccaf8 / cd814 / cda34), WORD 8e(A6) 0..15 (the index
        of the ROM LONG table b7f6c of b6bf4, 16 LONGs), D0.W 0..7 at 70fe8 / 70fea and 0..1c (x 4) at 70fec with A0 = 70d72 (the ROM LONG table of 70302's
        result, 8 LONGs), D0.W 0 at b6bb8 (the BNE of b6ba8), A3 a WORD of the RNG ring at cd80a (the 49a58 tail), A1 / A2 / A3 the A5 counters 5ddc..5deb
        at b7aa8 .. b7ac8, A0 a node (BYTE 61) at b7b30 and a record WORD at cca44, LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), BYTE
        10fd82 = 0."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 7, 8, 0x10, 0x1c, 0xff, 0x100, 0x7fff, 0x8000, 0xffff, 0x10000, 0x12340001, 0xffffffff))
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0xffff0000, 0x12345600))
        if rng.random() < 0.5:
            regs['d7'] = rng.choice((0x2800, 0x27ff, 0x57ff, 0x5800, 0, 0xffff, 0x12342800, 0x12345800))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.3 else self.pointer()
        regs['a1'] = self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        if entry in (0x70fe8, 0x70fea):
            regs['a0'] = 0x70d72
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(8)
        if entry == 0x70fec:
            regs['a0'] = 0x70d72
            regs['d0'] = (regs['d0'] & 0xffff0000) | (4 * rng.randrange(8))
        if entry == 0xb6bb8:
            regs['d0'] = regs['d0'] & 0xffff0000
        if entry in (0xb7aa8, 0xb7ab2, 0xb7ab6, 0xb7ac0, 0xb7ac2, 0xb7ac8, 0xb7aca):
            k = rng.choice((0x5ddc, 0x5de4))
            regs['a1'], regs['a2'], regs['a3'] = a5 + k, a5 + k + 4, a5 + k + 7
        if entry == 0xcd80a:
            regs['a3'] = 0x10d6b4 + 2 * rng.randrange(0x37)
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.randrange(4)))  # WORD 76(A6): the index of ea732 / eaa5c (4 LONGs each)
        writes.append(((a6 + 0x8c) & 0xffff, 2, rng.choice((0, 1, 2, 3, 4, 5, 5, 0xffff))))   # WORD 8c(A6): the anim selector
        writes.append(((a6 + 0x8e) & 0xffff, 2, rng.randrange(16)))  # WORD 8e(A6): the index of b7f6c (16 LONGs) at b6bf4
        if rng.random() < 0.8:
            writes.append(((a6 + 0x26) & 0xffff, 4, 0))       # 49fc6: LONG 26(A6) = 0 -> Set without the interpreter (random scripts)
        if rng.random() < 0.9:
            writes.append((0xfd82, 1, 0))                                                 # BYTE 10fd82 = 0
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0x76, 0x8c, 0x8e, 0x8f, 0x77)):
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
    require(len(STARTS) == 211 and len(STARTS_SET) == 211, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr10_block', ('start is not routed to objects fr10', hex(s), unit_of(s)))
    for t in EXIT_STOPS:
        require(unit_of(t) is None or t in ROUTED_LATER, ('later-unit stop must stay unrouted', hex(t)))
    # player C10 routes the C7 table entry 252b4 -> 252ce .. 252e2 since C10 (main decision 4; was: the four PCs stay unrouted)
    for t in (0x252b4, 0x252ce, 0x252d8, 0x252e2):
        require(unit_of(t) == 'animation_player_c10_block', ('the C7 table entry 252b4 -> 252ce is a C10 start (main decision 4)', hex(t)))
    for t in (0xcc7c4, 0xcc7d0, 0xcc846):
        require(unit_of(t) == 'animation_objects_fr10_block', ('FR4 table entry routed to FR10', hex(t)))
    rng = random.Random(0xF10A)
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
    sys.stderr.write('fr10 spec: %d fixtures (%d natural), visited %d/211, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr10: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr10: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the BYTE 15 / 61 / 82 bits,
    the signed WORD difference 8e - 42 of 70e2a / 70f94 with the SEQ / EXT / EOR of BYTE 15 bit 0, the LONG 8e - 42 ASR.L #5 of 70efe, the WORD / LONG
    arithmetic of 70f12 / 70f2a / 70f2c (ANDI.W, SUBI.W, EXT.L, ADD.L, NEG.L, LSL.L #6, SWAP, ADDI.W), the unsigned D7 compare of 70f4e, the LONG
    ASR.L #3 / #2 of 7143a / 714d4, the signed WORD compares of b6c2c (BLE) / b6c84 (BGT), the WORD borrow of b6c7c, the unsigned WORD 64 of b7aa8, the
    WORD ffff of b7ab6, the BYTEs D0 / D1 of b7a86 / b7ac2, the anim selectors (WORD 8c 0..5), the LONG / WORD arithmetic of cd7cc / cd7f2 / cd814 /
    cd8fe (CMPI.W #20 + BPL), the signed TST of BYTE 5f / LONG 3a / WORD 3a / WORD 64, the SMI / SEQ / SNE / EOR.B of 705aa / cd95a, the BCLR of
    5e50(A5), the WORD arithmetic of eaafe), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is
    kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x6f1ca, 0x70594, 0x705aa, 0x70e2a, 0x70f94, 0x70efe, 0x70f12, 0x70f2c, 0x7143a, 0x714d4, 0xb6ba8, 0xb6c2c, 0xb6c84, 0xccaf8, 0xcd814,
                 0xcda34, 0xcd7cc, 0xcd7f2, 0xcd8fe, 0xcd95a, 0xeaafe, 0xeaa00, 0xeaada, 0x4e122, 0xb6ba0, 0xcca44, 0xeaad0, 0xcdda0):
        h += [dict(regs=dict(up))] + mirror
    if entry == 0x6f1ca:
        h += word(0x3a, (0, 0x7fff, 0x8000, 0xffff)) + [dict(a6off=[(0x3a, 2, 0x8000), (0x80, 1, 0x55), (0x7f, 1, 0xff), (0x81, 1, 0xff)])]
    if entry == 0x70594:
        h += [dict(regs=dict(up), a6off=[(0x80, 2, v)]) for v in (0, 1, 0xfffe, 0xffff, 0x8001)]
    if entry == 0x705a0:
        h += byte(0x82, (0x20, 0xdf, 0, 0xff))
    if entry == 0x705aa:
        for w64, b15 in ((0, 0), (0, 1), (0x8000, 0), (0x8000, 1), (0x7fff, 0xfe), (0xffff, 0xff)):
            h.append(dict(regs=dict(up), a6off=[(0x64, 2, w64), (0x15, 1, b15)]))
    if entry in (0x70e2a, 0x70f94):
        for w8e, w42, b15 in ((0x100, 0x80, 0), (0x80, 0x100, 0), (0x100, 0x80, 1), (0x80, 0x100, 1), (0x8000, 0, 0), (0, 0x8000, 1), (0, 0, 0),
                              (0, 0, 1), (0x7fff, 0xffff, 0), (0x7fff, 0xffff, 1)):
            h.append(dict(regs=dict(up), a6off=[(0x8e, 2, w8e), (0x42, 2, w42), (0x15, 1, b15)]))
    if entry in (0x70ea2, 0x713d8, 0x71468):
        h += word(0x9c, (0, 1, 0x8000, 0x100))
    if entry == 0x70efe:
        for l8e, l42 in ((0x100000, 0x80000), (0x80000, 0x100000), (0x80000000, 0), (0, 0x80000000), (0x1f, 0), (0, 0x1f), (0x7fffffff, 0xffffffff)):
            h.append(dict(regs=dict(up), a6off=[(0x8e, 4, l8e), (0x42, 4, l42)]))
    if entry == 0x70f12:
        for d0, l64 in ((0, 0), (0x7fff, 0), (0x3fff, 0), (0x4000, 0), (0xc000, 0xffffc000), (0x8000, 0x80000000), (0x12345678, 0x7fffffff),
                        (0xffffffff, 0x4000), (0x4000, 0xffffffff)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x64, 4, l64)]))
    if entry == 0x70f2a:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x80000000, 0xffffffff, 0x12345678)]
    if entry == 0x70f2c:
        h += [dict(regs=dict(up, d0=v), a6off=[(0x2c, 2, 0x5555)]) for v in (0x03ffffff, 0x04000000, 0xffffffff, 0x12345678, 0, 0x01ff8000, 0x02000000)]
    if entry in (0x70f3e, 0x714ca, 0xcd8ee):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff)) + mirror
    if entry == 0x7143a:
        h += [dict(a6off=[(0x64, 4, v), (0x15, 1, b)]) for v, b in ((0, 0), (7, 0x80), (8, 0), (0x80000000, 0x80), (0xfffffff8, 0x7f),
                                                                       (0xffffffff, 0xff), (0x7fffffff, 0))]
    if entry == 0x714d4:
        h += [dict(a6off=[(0x64, 4, v)]) for v in (0, 3, 4, 0x80000000, 0xfffffffc, 0xffffffff, 0x7fffffff)]
    if entry == 0x70f4e:
        h += [dict(regs=dict(up, d7=v)) for v in (0x2800, 0x27ff, 0x57ff, 0x5800, 0, 0xffff, 0x12342800, 0x1235800)]
    if entry == 0x70fc2:
        h += byte(0x82, (0x80, 0x7f, 0, 0xff))
    if entry == 0x71008:
        h += byte(0x61, (1, 0xfe, 0, 0xff))
    if entry in (0x71020, 0xb6c84):
        h += word(0x7c, (0, 1, 0x7fff, 0x8000, 0xffff)) + [dict(a6off=[(0x7c, 2, 0), (0x15, 1, 0xff)]), dict(a6off=[(0x7c, 2, 0), (0x15, 1, 0)])]
    if entry == 0xb6ba8:
        h += word(0x8e, (0, 1, 0x8000, 0x100, 0xffff))
    if entry == 0xb6bb8:
        h += [dict(regs=dict(up, d0=0x12340000))]
    if entry == 0xb6bf4:
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (1, 2, 5, 7, 15)]
    if entry == 0xb6c2c:
        h += [dict(a6off=[(0x42, 2, v), (0x96, 4, 0x55555555), (0x9a, 2, 0x5555)]) for v in (0xc0, 0xc1, 0xbf, 0x8000, 0x7fff, 0xffff, 0)]
    if entry == 0xb6c7c:
        h += word(0x84, (1, 0, 2, 0x8000, 0x100))
    if entry == 0xb7a86:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 0x100, 1, 0x80, 0xffffff00)]
    if entry == 0xb7aa8:
        h += [dict(rega5=dict(a1=k, a2=k + 4, a3=k + 7), a5off=[(k, 2, v)]) for k in (0x5ddc, 0x5de4) for v in (0x62, 0x63, 0x64, 0xffff, 0)]
    if entry == 0xb7ab6:
        h += word(0x7c, (0xffff, 0xfffe, 0x7fff, 0))
    if entry == 0xb7ac2:
        h += [dict(regs=dict(up, d1=v)) for v in (0, 0x100, 1, 0xffffff00)]
    if entry in (0xb7ac0, 0xb7ac8):
        h += [dict(rega5=dict(a1=k, a2=k + 4, a3=k + 7), a5off=[(k + 4, 1, v), (k + 7, 1, v)]) for k in (0x5ddc, 0x5de4) for v in (0xff, 0x7f)]
    if entry == 0xb7b30:
        h += [dict(regrec=dict(a0=0x20), rec=[(0x81, 1, v)]) for v in (0x80, 0x7f, 0, 0xff)]
    if entry == 0xcca44:
        h += [dict(regrec=dict(a0=0x20), rec=[(0x20, 2, v)]) for v in (0, 0x10, 0x8000, 0xffff)]
    if entry == 0xccade:
        h += byte(0x7b, (0, 1, 0x80, 0xff))
    if entry == 0xccae6:
        h += byte(0x61, (8, 0xf7, 0, 0xff))
    if entry in (0xccaf8, 0xcd814, 0xcda34):
        h += [dict(regs=dict(up), a6off=[(0x8c, 2, v), (0x8a, 2, 0x1234)]) for v in (0, 1, 2, 3, 4, 5, 0xffff, 0x100)]
    if entry in (0xccb1a, 0xccb3c, 0xccb5e, 0xccb80, 0xcd842, 0xcd864, 0xcd886, 0xcd8a8, 0xcda56, 0xcda78, 0xcda9a, 0xcdabc):
        h += [dict(regs=dict(up, d0=v)) for v in (1, 2, 3, 4, 5, 0x10001, 0x10002, 0x10003, 0x10004)]
    if entry == 0xcd7cc:
        h += [dict(regs=dict(up, d0=v), a6off=[(0x5f, 1, b)]) for v, b in ((0, 0), (0x4000, 0x80), (0xffff, 0x7f), (0x12343fff, 0xff), (0x8000, 0))]
    if entry == 0xcd7f2:
        h += [dict(regs=dict(up, d0=v), a6off=[(0x3a, 4, 0x55555555)]) for v in (0, 0xffff, 0x12348000, 0xffffffff)]
    if entry == 0xcd814:
        h += [dict(regs=dict(up, d0=v), a6off=[(0x8c, 2, 0)]) for v in (0, 0x3f, 0x40, 0xffffffff)]
    if entry == 0xcd8fe:
        for d0, w2c in ((0, 0x2a), (0, 0x29), (0xf, 0x1b), (0xa, 0x16), (0xa, 0x15), (0, 0x8000), (0xfffffff0, 0x7fff), (0x12345675, 0x20)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x2c, 2, w2c)]))
    if entry == 0xcd916:
        h += [dict(regs=dict(up), a6off=[(0x3a, 4, v)]) for v in (0, 0x80000000, 0x7fffffff, 0xffffffff)]
    if entry == 0xcd94e:
        h += byte(0x76, (0, 1, 0x80))
    if entry == 0xcd95a:
        for b5f, b15 in ((0, 0), (0, 1), (0x80, 0), (0x80, 1), (0x7f, 0xff), (0xff, 0xfe)):
            h.append(dict(regs=dict(up), a6off=[(0x5f, 1, b5f), (0x15, 1, b15)]))
    if entry in (0xcd80e, 0xcdd86, 0xcddb2, 0xb6c84, 0xcca52, 0xcd8e0):
        h += byte(0x15, (0, 0xff, 1, 0x80)) + mirror
    if entry == 0xeaa26:
        h += [dict(a5off=[(0x5e50, 1, v)]) for v in (0x80, 0x7f, 0, 0xff)]
    if entry == 0xeaa44:
        h += byte(0x78, (0, 1, 0x80))
    if entry == 0xeaafe:
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v)]) for v in (0, 1, 2, 3, 5, 0x8000, 0xffff)]
    if entry in (0xeaa00, 0xeaada):
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v)]) for v in (0, 1, 2, 3)]
    if entry == 0x4e122:
        h += [dict(regs=dict(up, d0=v), a5off=[(0x5d26, 2, 0xffff), (0x5d28, 2, 0x7fff)]) for v in (0, 1, 2, 3, 0xfffffffe, 0x12340001)]
    if entry in (0x70fe8, 0x70fea):
        h += [dict(regs=dict(up, a0=0x70d72, d0=0x12340000 | v)) for v in (0, 1, 7)]
    if entry == 0x70fec:
        h += [dict(regs=dict(up, a0=0x70d72, d0=0x12340000 | v)) for v in (0, 4, 0x1c, 0x14)]
    if entry == 0x70ff0:
        h += [dict(regs=dict(up, a0=v)) for v in (0, 0x71502, 0x10000, 0x80000000)]
    if entry in (0xb7a6e,):
        h += [dict(regs=dict(up, d0=0x12348000, d1=0x56787fff))]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry in (0x70f84, 0x71454, 0x714e4, 0xeab30, 0xeaa34):
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
    if entry == 0x70fd2:
        # 7028e: BTST.B #3,15(A6); BEQ -> ANDI Clear / CMPI.W #e0 on WORD 42 - 30 (unsigned >= e0: RTS with C Clear; else 702b0 -> 4ae4a: D0.B not 0 Set)
        return dict(a6off=[(0x15, 1, (0x08, 0, 0, 0, 0xf7)[t % 5]), (0x42, 2, (0x110, 0x40, 0x80, 0xc0, 0x100, 0x30, 0x10f)[(t // 5) % 7]),
                           (0x46, 2, (0x40, 0x80, 0xc0, 0x100)[(t // 3) % 4])])
    if entry == 0x70ffa:
        # 705ca: BTST.B #1,82(A6); CMPI.B #40,6f(A6); 4bc04 (WORD 42, WORD 46 + 20) result >= 40 -> Set; else Clear
        return dict(a6off=[(0x82, 1, (2, 2, 0, 0xff)[t % 4]), (0x6f, 1, (0x40, 0x40, 0x41)[(t // 4) % 3]), (0x42, 2, (0x40, 0x80, 0xc0, 0x100)[(t // 2) % 4]),
                           (0x46, 2, (0x40, 0x80, 0xc0, 0x100, 0x180)[(t // 3) % 5])])
    if entry == 0xb7a62:
        return dict(a5off=[(0x5683, 1, (1, 0, 0xff, 0xfe)[t % 4])])                    # 484e2: BYTE 5683(A5) bit 0 -> Set
    if entry == 0xb7a6e:
        return dict(a5off=[(0x568e, 1, (3, 0, 1, 2)[t % 4])], regs=dict(d0=(0, 1)[(t // 4) % 2]))   # 49392: BYTE 568e(A5) bit (D0 & 1) -> Set
    if entry == 0xcd804:
        # 49a58 with the ring pointer 5722(A5) = 10d6b4: D0 = WORD 10d6b4 = 0, the SUB.W target WORD 10d6e4 decides the N
        return dict(writes=[(0xd722, 4, 0x10d6b4), (0xd6b4, 2, 0), (0xd6e4, 2, (0x1234, 0x8000, 0, 0xffff)[t % 4])])
    if entry == 0x71012:
        # 70594: WORD 80 bit 0, BYTE 82 bit 5, WORD 64 sign, BYTE 15 bit 0
        return dict(a6off=[(0x80, 2, (1, 1, 0, 1)[t % 4]), (0x82, 1, (0x20, 0x20, 0x20, 0)[(t // 4) % 4]), (0x64, 2, (0, 0x8000)[t % 2]),
                           (0x15, 1, (0, 1)[(t // 2) % 2])])
    if entry == 0xcd93c:
        # ccade: TST.B 7b(A6) (0 -> Clear); BTST.B #3,61(A6) (set -> Clear); 4b54e (LONG 56(A6) = 0 -> 4b6be)
        return dict(a6off=[(0x7b, 1, (0, 1, 1, 0x80)[t % 4]), (0x61, 1, (0, 8, 0, 0xf7)[(t // 4) % 4]), (0x56, 4, (0, 0x10e900, 0x10e000)[(t // 2) % 3])])
    if entry == 0xcdd86:
        return dict(writes=[(0x4ca0, 2, (0, 1, 5, 0x40)[t % 4])])                    # 28ae: the free-node count WORD 104ca0 (0: no node)
    if entry == 0xeaa26:
        return dict(a5off=[(0x5e50, 1, (0x80, 0, 0xff, 0x7f)[t % 4])], a6off=[(0x26, 4, 0)] if t % 3 else [])
    if entry == 0xeaac0:
        return dict(a5off=[(0x5430, 2, (0xffff, 0, 0xffff, 0x1234)[t % 4])])          # 1abda: WORD 5430(A5) = ffff -> its quick side
    if entry == 0x70ff0:
        return dict(regs=dict(a0=(0, 0x71502, 0, 0x716ca)[t % 4]))
    return None


def chain_fixtures(world, add, record):
    """The consumers entered through their REAL producers; the stop is the consumer's successor or the first unrouted PC of the run (b7b40 returns to
    the sentinel)."""
    rng = world.rng
    for entry, cons in CHAINS:
        flds = fields_of(entry) + [(6, off, 1) for off in (0x15, 0x1d)] + [(6, off, 4) for off in (0x36, 0x3a, 0x42, 0x46)]
        succ = static_next(cons) if cons != 0xb7b40 else {SENTINEL}
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 15 bits 0 / 7, BYTE 61 / 82, WORD 9c, WORD 7c, WORD 84 (b6c7c), WORD 42 (b6c2c), WORD 76 0..3, WORD 8c,
            # BYTE 5f / 7b / 78, LONG 26 (0: 49fc6 Set), LONG 64 / 3a
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 1, 0x81, 0xff)[t % 5]), (0x61, 1, (0, 1, 8, 0x80)[(t // 2) % 4]),
                               (0x82, 1, (0, 0x20, 0x80, 0xa0)[(t // 3) % 4]), (0x9c, 2, (0, 1)[(t // 2) % 2]), (0x7c, 2, (0, 1, 0xffff, 0x8000)[(t // 4) % 4]),
                               (0x84, 2, (1, 4, 2)[t % 3]), (0x42, 2, (0xc0, 0x100, 0x40)[(t // 5) % 3]), (0x76, 2, t % 4), (0x8c, 2, (t // 3) % 6),
                               (0x5f, 1, (0, 0x80)[(t // 7) % 2]), (0x7b, 1, (0, 1)[(t // 2) % 2]), (0x78, 1, (0, 1)[(t // 3) % 2]),
                               (0x64, 4, (0, 0x80000000, 0x100, 0xffffff00)[(t // 6) % 4]), (0x3a, 4, (0, 0xfffc0000, 0x12345)[(t // 4) % 3])] +
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
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a frame in which a node of the pool NATURAL_NODES holds one of NODE_ENTRIES as its
    callback LONG; declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the
    frame start.  Up to the sentinel or the first unrouted PC."""
    entries = set(NODE_ENTRIES)
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
    err('odd-pc', U.with_host_writes(st, pc=0x70e2b), 'unaligned animation machine PC', 0x70e2b)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rec = SCR
    # the N source of cd80a (contract decision 3): the WORD (A3) outside work RAM / fixed ROM (the bank window, the device space)
    for v in (0x200000, 0x3c0000, 0x2ffff0, 0x300000):
        err('cd80a-a3-%x' % v, U.with_host_writes(st, regs=dict(a3=v), pc=0xcd80a), ERROR_FLAG, 0xcd80a)
    # odd node / stack / A0 / A1: the entry block fails (the row's stop is the PC right after the failing block)
    err('70ea2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70ea2), odd_word, 0x70ea2)
    err('b6c66-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb6c66), odd_write, 0xb6c66, stop=0xb6c72)
    err('eaafe-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xeaafe), odd_write, 0xeaafe, stop=0xeab2a)
    err('70f2c-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x70f2c), odd_write, 0x70f2c, stop=0x70f3e)
    err('cca44-odd-a0', U.with_host_writes(st, regs=dict(a0=rec + 1), pc=0xcca44), odd_word, 0xcca44)
    err('70fec-odd-a0', U.with_host_writes(st, regs=dict(a0=0x70d73, d0=0), pc=0x70fec), odd_word, 0x70fec, stop=0x70ff0)
    err('b7aa8-odd-a1', U.with_host_writes(st, regs=dict(a1=a5 + 0x5ddd), pc=0xb7aa8), odd_word, 0xb7aa8)
    err('eab40-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xeab40), odd_word, 0xeab40)
    err('6f1ca-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x6f1ca), odd_word, 0x6f1ca)
    # failures after executed blocks: the later-unit stops (FR11 / FR12 / FR13) reached through the unit
    # objects FR11 routes 70e42 / 70fac / cd7e2 / cd92e / cd96c since FR11: the rows that failed there (unrouted) now fail on the FR11 path (FR11 contract,
    # was: 70e2a-then-70e42 / cd7cc-then-cd7e2 / cd8ee-then-cd92e / cd95a-then-cd96c / 70f94-then-70fac with 'unsupported animation machine PC')
    err('70e2a-then-70e4a', U.with_host_writes(st, [((a6 + 0x8e) & 0xffff, 2, 0), ((a6 + 0x42) & 0xffff, 2, 1), ((a6 + 0x15) & 0xffff, 1, 1),
                                                    ((a6 + 0x9c) & 0xffff, 2, 0)], regs=dict(a7=a7 + 1), pc=0x70e2a),
        odd_word, 0x70e4a)                                                              # FR11 70e42 -> 70e4a: the JSR 49f8c push on the odd A7
    err('70f4e-then-70f60', U.with_host_writes(st, regs=dict(d7=0x6000), pc=0x70f4e), unrouted, 0x70f60)
    err('70fc2-then-70fcc', U.with_host_writes(st, [((a6 + 0x82) & 0xffff, 1, 0x80)], pc=0x70fc2), unrouted, 0x70fcc)
    err('71020-then-71028', U.with_host_writes(st, [((a6 + 0x7c) & 0xffff, 2, 0)], pc=0x71020), unrouted, 0x71028)
    err('b6c2c-then-b6c58', U.with_host_writes(st, [((a6 + 0x42) & 0xffff, 2, 0)], pc=0xb6c2c), unrouted, 0xb6c58)
    err('cd7cc-then-cd7e4', U.with_host_writes(st, [((a6 + 1 + 0x5f) & 0xffff, 1, 0x80)], regs=dict(a6=a6 + 1), pc=0xcd7cc), odd_write, 0xcd7e4)   # FR11 cd7e2
    err('cd8ee-then-cd92e', U.with_host_writes(st, [((a6 + 1 + 0x15) & 0xffff, 1, 0x80)], regs=dict(a6=a6 + 1), pc=0xcd8ee), odd_write, 0xcd92e)
    err('cd95a-then-cd96c', U.with_host_writes(st, [((a6 + 1 + 0x5f) & 0xffff, 1, 0x80), ((a6 + 1 + 0x15) & 0xffff, 1, 0)], regs=dict(a6=a6 + 1), pc=0xcd95a),
        odd_word, 0xcd96c)
    err('70ff0-then-70ff8', U.with_host_writes(st, regs=dict(a0=0x71502), pc=0x70ff0), unrouted, 0x70ff8)
    err('70fe4-then-70ff8', U.with_host_writes(st, regs=dict(d0=1), pc=0x70fe4), unrouted, 0x70ff8)       # the ROM LONG 70d72 + 4 = 71502
    err('70f94-then-70fcc', U.with_host_writes(st, [((a6 + 0x8e) & 0xffff, 2, 0), ((a6 + 0x42) & 0xffff, 2, 1), ((a6 + 0x15) & 0xffff, 1, 1),
                                                    ((a6 + 0x82) & 0xffff, 1, 0x80)], pc=0x70f94),
        unrouted, 0x70fcc)                                                              # FR11 70fac -> FR10 70fc2 -> the FR13 stop 70fcc
    err('eaa52-odd-stack-after-eaa44', U.with_host_writes(st, [((a6 + 0x78) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0xeaa44), odd_word, 0xeaa52)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x70f12, 0xcd8fe, 0x705aa, 0xb7aa8)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
