"""V1 fixture spec of the area-C unit C5 (engine/src/animation_machine_player_c5.cpp, 203 block starts; file prefix pc5 / player_c5 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c5-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C5 spec of the
contract): the player state 20738 (installed by C3 2066a and 20554 / 2055e: 1cc1a, 206ec, the BRA.W table 20792 -> 20796 -> the 208d2 loop, 2092c,
the tables 2094e -> 2095a -> 212ce and 209d6, contract decision 2), the landing states 212ce / 213da / 20e18 -> 2143c / 20e3e -> 214c0 -> 214d6 ->
21520 -> 21542 / 21556, the record helper 1c356 (MULU index of the 10-byte records 1c298, the C helper 4d628 with the 16-byte records 4cf64, the bit
table 1c52c of 1c51c with its Z reader 1c3e2 (contract decision 3), the 28ae child 1c4b0), the C2 record tail 1cb1a / 1cb38 / 1cb44, the C3 tails
20240 20268 202ac 20544 21c12 21f4c 21f78 (the JMP (A1) 21f7c of the list 21b26), 1d182 (4d106, 4de7a), 20de6, 20efc / 20f04, cddee.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C4) with declared host edits.
This code runs natively only in the IO observation (P1 / boot-title-start): the 'natural' family takes the frame-start states of the IO native
observation in which the player node 100cb8 holds the callbacks 1ef0e (C4; its frame runs C3 20238 into C5 20240 / 20268 / 20544) or the C5 callbacks
20738 / 2143c / 214c0 / 214d6, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the
sentinel return LONG, PC = the callback); the 'reinstall' family enters a C5 callback with declared BYTEs (the table indices 9e / 5e, BYTE 15 / 5f /
88, WORD 42 / 46).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 7 C consumers and the Z reader 1c3e2 is entered directly (the seed world with declared edits).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS) and the Z reader 1c3e2 through 1c3dc -> 1c51c.  Stop: the consumer's
            successor or the first unrouted PC.
  node      the installed values 20738 2143c 214c0 214d6 21556 20e3e ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with declared BYTEs / WORDs.
  callee    the helpers and states entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 7 consumers, computed-jump displacements / targets outside the ROM
            ranges (decision 2), the Z source of 1c3e2 outside fixed ROM / RAM or a D7 that is not the table LONG (decision 3), odd node / stack / A0,
            failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs
            from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C4
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C4)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc5'
ERROR_PC = 'unsupported animation player c5 PC'
ERROR_CARRY = 'player c5 caller requires known carry'
ERROR_FLAG = 'unsupported animation player c5 flag source'
ERROR_JUMP = 'unsupported animation player c5 jump target'

RANGES = [(0x1c356, 0x1c4b0), (0x1c51c, 0x1c52c), (0x1cb1a, 0x1cb40), (0x1cb44, 0x1cb6a), (0x1cc1a, 0x1cce8), (0x1cd00, 0x1cd12), (0x1d182, 0x1d198),
          (0x20240, 0x2024a), (0x20268, 0x20290), (0x202ac, 0x202b6), (0x20544, 0x20578), (0x206ec, 0x20700), (0x20738, 0x2079a), (0x208d2, 0x208fa),
          (0x2092c, 0x20952), (0x2095a, 0x2095e), (0x209c2, 0x209da), (0x20de6, 0x20e64), (0x20efc, 0x20f22), (0x212ce, 0x21336), (0x213da, 0x21564),
          (0x21c12, 0x21c1a), (0x21f4c, 0x21f58), (0x21f78, 0x21fa6), (0x4d106, 0x4d126), (0x4d628, 0x4d6b4), (0x4de7a, 0x4de9c), (0xcddee, 0xcde16)]
STARTS = sorted(int(x, 16) for x in (
    '1c356 1c35e 1c36a 1c36e 1c374 1c378 1c390 1c39a 1c3a4 1c3b6 1c3bc 1c3c0 1c3ca 1c3d2 1c3d8 1c3dc 1c3e2 1c3e6 1c408 1c412 1c41e 1c42a 1c42e 1c432 '
    '1c43c 1c454 1c45c 1c462 1c476 1c480 1c494 1c4aa 1c51c 1cb1a 1cb30 1cb32 1cb38 1cb44 1cb56 1cb5c 1cc1a 1cc38 1cc54 1cc62 1cc66 1cc6a 1cc7c 1cc88 '
    '1cc9e 1ccaa 1ccb4 1ccc4 1ccd0 1cce6 1cd00 1cd0a 1cd0c 1d182 1d18c 1d196 20240 20268 20272 2027e 20288 2028c 202ac 20544 20550 20554 2055e 2056e '
    '20574 206ec 20738 20746 2074c 20768 2076c 20770 20774 20778 20796 208d2 208dc 208e4 208e8 208ec 208ee 208f2 2092c 20932 2093a 20946 2095a 209c2 '
    '209ce 20de6 20df6 20dfc 20e0a 20e10 20e18 20e20 20e3e 20e40 20e46 20e50 20e56 20e5a 20e60 20efc 20f04 20f0c 20f18 20f20 212ce 212d4 212ec 212f2 '
    '212fc 2130c 21310 21314 213da 213de 213e4 213fc 2140a 2140e 21412 21430 2143c 21446 21456 2145c 2146a 21470 2147c 21480 21494 214ac 214b2 214b6 '
    '214bc 214c0 214d6 214de 214e4 214ea 214f2 21502 21506 2150c 21516 2151c 21520 21524 21530 21540 21542 21556 2155a 21562 21c12 21f4c 21f54 21f78 '
    '21f7c 21f7e 21f82 21f8a 21f92 21f96 21f9c 21fa4 4d106 4d10e 4d116 4d11a 4d628 4d62e 4d636 4d63a 4d640 4d65c 4d668 4d670 4d676 4d67a 4d682 4d68e '
    '4d692 4d69c 4d6a8 4de7a 4de86 4de8a cddee cddfe cde02 cde10 cde14').split())
# the 7 C consumers: BCC 1c374 (289e), 1c3ca (4d628), 20e56 214b2 (49fc6), 21f78 (215e6 of C3), cddfe (28ae); BCS 20288 (49c38)
CONSUMERS = (0x1c374, 0x1c3ca, 0x20288, 0x20e56, 0x214b2, 0x21f78, 0xcddfe)
# 1cb1a TST.L (C := 0); 1c4aa 4d6a8 ANDI.B #fe,CCR; RTS
CLEAR_SET = (0x1cb1a, 0x1c4aa, 0x4d6a8)
SET_SET = (0x1cb32, 0x1c494, 0x4d69c, 0xcde10)   # ORI.B #1,CCR; RTS
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = (0x1cb30,)                   # RTS (carry preserving: the Clear of the 1cb1a TST.L reaches the callers of C2 1cb08)
STARTS_SET = set()
Z_READERS = (0x1c3e2,)                  # BEQ.W on the Z of the BTST.L D1,D7 of 1c51c (contract decision 3): never entered directly by a native run
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units (and deferred leaders) that a C5 block reaches by a fall-through or a branch (C6 21564, the deferred leaders 208fa 2210c), and the
# still unrouted later-unit stops of the C1..C4 blocks that the C5 runs pass through (pc4 EXIT_STOPS that are still unrouted; the TRAP site 4e69a of
# C1).  Declared stops of the native runs: a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x21564, 0x208fa, 0x2210c,
              0x1ef4c, 0x1efa4, 0x1f2a4, 0x21d9e, 0x4e572, 0x1efd6, 0x1f070, 0x21dd0, 0x223a0, 0x223d6, 0x4ef08, 0x1ce98, 0x1cfde, 0x1d398, 0x1de3c,
              0x1e21c, 0x1e8de, 0x1ebbe, 0x1fa68, 0x1fafc, 0x1fc96, 0x1fd50, 0x201bc, 0x206cc, 0x21662, 0x21ca4, 0x21d0e, 0x21fa6, 0x4838c, 0x4d0cc,
              0x4e69a, 0x4e8f8, 0x4eb58)
UNIT_EXITS = EXIT_STOPS[:3]             # the C5 later-unit stops and deferred leaders
# later-unit stops routed since (player C6: 21564 1efa4 4e572 1d398 1ebbe 206cc 21662 4838c 4e8f8 4eb58; player C7: 1f2a4): still declared stops of the
# C5 runs
ROUTED_LATER = (0x21564, 0x1efa4, 0x4e572, 0x1d398, 0x1ebbe, 0x206cc, 0x21662, 0x4838c, 0x4e8f8, 0x4eb58, 0x1f2a4)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the Z chain 1c3dc -> 1c51c -> 1c3e2
CHAINS = ((0x1c36e, 0x1c374), (0x1c3c0, 0x1c3ca), (0x2027e, 0x20288), (0x20e50, 0x20e56), (0x214ac, 0x214b2), (0x21f70, 0x21f78), (0xcddee, 0xcddfe),
          (0x1c3dc, 0x1c3e2))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# computed jumps (contract decision 2): the BRA.W tables JMP 20796(PC,D0.W) 20792 (4 entries, BYTE 9e 0..3), JMP 20952(PC,D0.W) 2094e and JMP
# 209da(PC,D0.W) 209d6 (the entries 0..1a that CMPI.B #1b admits), JMP (A1) 21f7c (a handler of the list 21b26)
JUMP_PCS = (0x20792, 0x2094e, 0x209d6, 0x21f7c)
LIST_21B26 = (0x21602, 0x21e48, 0x21e3a)
TABLE_20796 = tuple(0x20796 + 4 * k for k in range(4))
TABLE_20952 = tuple(0x20952 + 4 * k for k in range(0x1b))
TABLE_209DA = tuple(0x209da + 4 * k for k in range(0x1b))
JUMP_ROUTED = (0x21602,)                # routed allowed targets besides the C5 entries 20796 / 2095a: the native runs continue through them
# computed jumps of C3 / C4 that the C5 runs reach (C3 2031c table, 201a6 JSR (A4), 21620 / 221de JMP (A1); C4 21c72 JMP (A1)): an unrouted target is a
# stop even when it is the straight-line successor (the entry 0 of the C3 table, 20320, follows the JMP 2031c)
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72)
TABLE_ENTRIES = ()
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92)   # routed slot-84 states (C3 and C4 21d92) for the worlds
# installed values entered as node callbacks; the callee entries (helpers and states entered as subroutines; not the pass block 1cb30: its readers
# are the callers of C2 1cb08)
NODE_ENTRIES = (0x20738, 0x2143c, 0x214c0, 0x214d6, 0x21556, 0x20e3e)
CALLEES = (0x1c356, 0x1c51c, 0x1cb1a, 0x1cb38, 0x1cb44, 0x1cc1a, 0x1cd00, 0x1d182, 0x202ac, 0x206ec, 0x20de6, 0x20efc, 0x20f04, 0x21520, 0x21494,
           0x21c12, 0x21f4c, 0x20240, 0x20268, 0x20544, 0x4d106, 0x4d628, 0x4de7a, 0xcddee)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('P1', 94, f) for f in (311, 312, 346, 392, 393, 426, 427, 428, 457)] + [('P1', 68, f) for f in (527, 562)] +
                [('P1', 106, f) for f in (311, 393, 427)] + [('boot-title-start', None, f) for f in (431, 466, 512, 547, 577)])
NATURAL_CALLBACKS = (0x1ef0e,) + NODE_ENTRIES                         # C4 1ef0e runs C3 20238 into C5 20240 / 20268 / 20544 in the same callback
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node), extra (offset, size, value) writes on the node)
REINSTALL = (('P1', 94, 392, 0x100cb8, 0x20738, ((0x9e, 1, 1),)), ('P1', 94, 392, 0x100cb8, 0x20738, ((0x9e, 1, 3),)),
             ('P1', 94, 392, 0x100cb8, 0x20738, ((0x5f, 1, 0x80),)), ('P1', 94, 392, 0x100cb8, 0x20738, ((0x5e, 1, 0x1b),)),
             ('P1', 94, 392, 0x100cb8, 0x20738, ((0x5e, 1, 0),)), ('P1', 94, 392, 0x100cb8, 0x20738, ((0x5e, 1, 0x80),)),
             ('P1', 94, 393, 0x100cb8, 0x2143c, ((0x15, 1, 0x80),)), ('P1', 94, 428, 0x100cb8, 0x214d6, ((0x88, 1, 0),)),
             ('P1', 94, 428, 0x100cb8, 0x21556, ((0x88, 1, 3),)), ('P1', 94, 428, 0x100cb8, 0x20e3e, ()),
             ('P1', 94, 428, 0x100cb8, 0x214d6, ((0x42, 2, 0x200),)), ('P1', 94, 428, 0x100cb8, 0x214d6, ((0x46, 2, 0x10),)),
             ('boot-title-start', None, 512, 0x100cb8, 0x20738, ((0x9e, 1, 2),)), ('P1', 68, 562, 0x100cb8, 0x20738, ((0x5e, 1, 0x1a),)))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0xe, 0xf, 0x10, 0x11, 0x12, 0x13, 0x18, 0x1a, 0x1b, 0x1e, 0x1f, 0x20, 0x40, 0x77, 0x7f, 0x80, 0x81, 0xbf,
      0xfe, 0xff)
VW = (0, 1, 2, 4, 5, 0xc, 0xf, 0x10, 0x20, 0x40, 0x7f, 0x80, 0xbf, 0xc0, 0xff, 0x100, 0x13f, 0x140, 0x1ff, 0x200, 0x2bf, 0x2c0, 0x3e6, 0x3e7, 0x3e8,
      0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x30000, 0x7fffffff, 0x80000000, 0xffea0000, 0xfffe0000, 0xffffffe0, 0xffffffff, 0x12345678)
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
BUNDLED = ()                            # no flag-sharing Bcc pair in C5


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (20efc falls to 20f04, 20e20 / 21430 / 214c0 / 21542 to their installed callbacks, 21f54 to C3 21f58, 1cb38 / 1cb56 by
    BRA / straight line to 1cb44 / 1cb5c)."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (none in C5) would use pcs[n - 1]."""
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at a target of the computed
    jumps 20792 / 2094e / 209d6 / 21f7c that is neither a block start of this unit (20796 / 2095a) nor a routed allowed target (C3 21602; an unrouted
    table entry or listed target such as 2079a / 21e48: the C++ dispatch of it is the checked PC error), or at the first unrouted PC that is not the
    straight-line successor of the previous instruction (a PC inside a block of another executor is not a block entry)."""
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
        """A world for `entry`.  The values a ROM writer bounds are kept in their ROM range (contract decision 2): BYTE 9e(A6) 0..3 (the table 20796,
        C2 1c1ec), BYTE 5e(A6) mostly 0..1a (the tables 20952 / 209da; some at / above 1b and negative for the guards), D0.B 0..1a for a direct entry into
        20946 / 209ce, A1 a handler of the list 21b26 for a direct 21f7c entry, LONG 84(A6) a routed slot-84 value (the C3 JSR (A4) 201a6 that the C3
        tails reach), BYTE a0(A6) 0..8 / a9(A6) 0..5 / 9f(A6) 0..8 / 7c(A6) 0..5 (C3 / C5 tables), WORD 76 / 78(A6) mostly 0 / 1; LONG 5434(A5) = 0 (C2
        decision 2).  The player nodes 100cb8 / 100da8 that 1c356 reads (A5 - 7348 / - 7258) get a callback LONG (270e: 289e Clear), LONG 8c (a
        record), BYTE 9e 0..3 and WORD 78.  D1.B (the record type of 1c356) is mostly below 13; BYTE 10fd82 = 0 keeps the controller C1 4a974 off the
        BIOS call c00450 (not mapped natively)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x18, 0x50, 0x400, 0xffff, 0x12345678, 0x10000, 0x1a, 0x1b))   # input bits
        if rng.random() < 0.7:
            regs['d1'] = (regs['d1'] & 0xffffff00) | rng.choice((0, 0, 1, 2, 5, 0xc, 0x12, 0x13, 0x80))
        if entry in (0x20946, 0x209ce) and rng.random() < 0.85:
            regs['d0'] = (regs['d0'] & 0xffffff00) | rng.randrange(0x1b)
        if rng.random() < 0.6:
            regs['d7'] = (regs['d7'] & 0xffff0000) | rng.choice((0, 2, 4, 6, 0xc, 0x3e7, 0x8000, 0xfffe))
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = rng.choice(LIST_21B26) if entry == 0x21f7c else self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer() if rng.random() < 0.5 else 0x1c298 + 10 * rng.randrange(0x13)    # the 10-byte records of 1c298 (ROM) or RAM
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, self.pointer()))    # LONG 8c(A6) (A4 of C3 202a0 / 202b6)
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of 1cb1a / 1cb44, C2 1cad4)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(),))))   # LONG 3e(A6) (C2 1a9fe..1aa20)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xb2) & 0xffff, 4, rng.choice((0, self.pointer()))))        # LONG b2(A6): the previous child of 1c462
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): C3 2031c, C5 1cc1a / 1cc7c
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): C3 206d4, C5 1cc54 / 1ccaa / 1ccb4
        writes.append(((a6 + 0x9f) & 0xffff, 1, rng.randrange(9)))                        # BYTE 9f(A6): 1cc1a / 1cc6a, C2 1cb08
        writes.append(((a6 + 0x7c) & 0xffff, 1, rng.randrange(6)))                        # BYTE 7c(A6): the WORD pairs 1cce8
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x4000))))       # WORD 76(A6): the WORD tables 20710 / 1b128
        writes.append(((a6 + 0x78) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x100))))        # WORD 78(A6): the player index
        writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                        # BYTE 9e(A6): the table 20796 (ROM writers 0..3)
        if rng.random() < 0.8:
            writes.append(((a6 + 0x5e) & 0xffff, 1, rng.choice((0, 1, 2, 2, 7, 8, 0x11, 0x12, 0x13, 0x1a, 0x1b, 0x7f, 0x80))))   # BYTE 5e(A6)
        for node in (0x100cb8, 0x100da8):
            writes.append((node & 0xffff, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c))))   # 289e: CMPI.L #270e,(A0)
            writes.append(((node + 0x8c) & 0xffff, 4, rng.choice((SCR, SCR + 0x40, self.pointer()))))
            writes.append(((node + 0x9e) & 0xffff, 1, rng.randrange(4)))
            writes.append(((node + 0x78) & 0xffff, 2, rng.choice((0, 1))))
        for rec in (SCR, SCR + 0x40):
            writes.append(((rec + 4) & 0xffff, 1, rng.randrange(0x13)))                  # BYTE 4: the record type (1c3e6 MULU index)
            writes.append(((rec + 0xc) & 0xffff, 2, rng.choice((0, 0x3e6, 0x3e7, 0x3e8, 5))))   # WORD c (1c412)
        for off in (0x5cba, 0x5ce6):                                                      # 4d628: WORD (A4), BYTE 27 (the records 4cf64), 2a, WORD 20
            writes.append(((a5 + off) & 0xffff, 2, rng.choice((0, 1, 0x100))))
            writes.append(((a5 + off + 0x27) & 0xffff, 1, rng.randrange(4)))
        writes.append(((a5 + 0x5434) & 0xffff, 4, 0))                                     # LONG 5434(A5): A1 of the C2 JMP (A1) 1aa38 (0 in ROM)
        writes.append(((a5 + 0x5474) & 0xffff, 4, rng.choice((0, self.pointer()))))       # LONG 5474(A5): A0 of C2 1cd2a
        writes.append(((a5 + 0x5e26) & 0xffff, 4, self.pointer()))                        # LONG 5e26(A5): A4 of C3 e8b5a
        if rng.random() < 0.9:
            writes.append((0xfd82, 1, 0))                                                 # BYTE 10fd82 = 0: 4a974 reads 100003 / 100004 / 100005
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4 (callee worlds)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e, 0x9f, 0x7c, 0x5e)):
                continue                                        # callback LONG, node links, the pointer fields and the bounded indices stay declared above
            if reg == 5 and disp in (0x5434, 0x5474, 0x5e26):
                continue
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
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('a4off', []):
                writes.append(((regs['a4'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('stack', []):
                writes.append(((sp + off) & 0xffff, size, val))  # values below / at the return LONG that a direct entry pops or reads
            for w in hint.get('writes', []):
                writes.append(w)
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
    require(len(STARTS) == 203 and len(STARTS_SET) == 203, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    require(unit_of(0x21602) == 'animation_player_c3_block', 'routed computed-jump target 21602')
    for t in LIST_21B26:
        require(unit_of(t) in (None, 'animation_player_c3_block'), ('computed-jump target routed by another unit', hex(t)))
    require(set(t for t in LIST_21B26 if unit_of(t) is not None) == set(JUMP_ROUTED), 'JUMP_ROUTED = the routed allowed targets')
    for t in TABLE_20796 + TABLE_20952 + TABLE_209DA:
        require(unit_of(t) is None or t in (0x20796, 0x2095a), ('table entry routed by another unit', hex(t)))
    require(set(TABLE_20796 + TABLE_20952 + TABLE_209DA) & set(STARTS) == {0x20796, 0x2095a}, 'only the executed table entries are blocks')
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c5_block', ('start is not routed to player c5', hex(s), unit_of(s)))
    rng = random.Random(0xC5A5)
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
                cond_points[a] = set(t for t in (target(op), a + size) if (s, t) not in STATIC_IMPOSSIBLE and (s, t) not in LATER_GATED)
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
    META['gated_consumers'] = [hex(x) for x in GATED_CONSUMERS]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('pc5 spec: %d fixtures (%d natural), visited %d/203, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc5: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc5: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (CMPI.B #13,D1 of 1c356,
    the MULU.W #a / #9 / #10 indices (D1.W = d00: the product WORD 8200 is a negative index into the ROM before the records 1c298), SUB.B D2,D6, TST.W
    D5 / D7, CMPI.W #3e7 / #3e8 with ADD.W wrap, CMP.B ties, the 10-byte records of 1c298, BYTE 9e(A0) of 1c51c and the LONG table 1c52c, the WORD /
    LONG tables 20710 / 1b128 (WORD 76 = 4000: a negative index), the BRA.W table indices 9e / 5e (CMPI.B #1b) and D0.B of 20946 / 209ce, the
    SUB.L / BMI / ADDI.L #1f / ASR.L #5 / ADD.L of 20de6 / 21446 (the sign of the LONG difference, rounding toward zero), the WORD ASR.W #4 of 21494,
    the SUBQ.B #1 borrow of 214d6 / 2155a, the unsigned CMPI.W #140 / SUBI.W #c0 / CMPI.W #200 of 21524 / 21530, the BTST bits of the node BYTEs and of
    D0, the 16-byte records 4cf64 (BYTE 27, BTST.L D2) and the WORD 20 clamp of 4d628, the stacked LONGs / WORD of 1c39a / 1c3ca / 1c45c / 1c494
    (MOVEM.W sign extension)), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a
    fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    rec = lambda k: 0x1c298 + 10 * k        # the 10-byte records of 1c298 (ROM)
    if entry in (0x1c35e, 0x1c378, 0x1c3a4, 0x1c3bc, 0x1c3dc, 0x1c3e6, 0x1c412, 0x1c41e, 0x1c42a, 0x1c432, 0x1c454, 0x1c45c, 0x1c462, 0x1c480, 0x1c51c,
                 0x1cb1a, 0x1cb44, 0x1cb56, 0x1cb5c, 0x1cc1a, 0x1cc38, 0x1cc54, 0x1cc62, 0x1cc6a, 0x1cc7c, 0x1cc88, 0x1ccb4, 0x1ccc4, 0x1ccd0, 0x1cd0a,
                 0x1d182, 0x202ac, 0x20544, 0x206ec, 0x2074c, 0x20778, 0x208dc, 0x2093a, 0x209c2, 0x20de6, 0x21446, 0x212d4, 0x213e4,
                 0x21494, 0x21524, 0x21530, 0x4d640, 0x4d69c, 0x4d6a8, 0x4de7a, 0xcddee, 0xcde02):
        h += [dict(regs=dict(up))]
    # ---- 1c356 .. 1c4aa
    if entry == 0x1c356:
        h += regs('d1', (0, 1, 0x12, 0x13, 0x14, 0x80, 0xff, 0x112, 0x12345601))
    if entry == 0x1c35e:
        h += regs('d0', (0, 1, 2, 3, 0x12340001, 0xfffe))
    if entry == 0x1c378:
        h += [dict(regs=dict(up, d1=v, d7=0x77770000)) for v in (0, 1, 5, 0x12, 0x100, 0xd00, 0x1234ff03, 0x1999)]
    if entry == 0x1c39a:
        h += [dict(regs=dict(up, d0=d0), stack=[(0, 4, a0), (4, 4, a3), (8, 4, SENTINEL)]) for d0, a0, a3 in
              ((0, 0x100cb8, rec(1)), (1, 0x100da8, rec(2)), (0x100, 0x100cb8, rec(0)), (0xff, 0x100cb8, rec(5)))]
    if entry == 0x1c3a4:
        for k, d6, d5 in ((1, 1, 0), (1, 2, 0), (1, 1, 1), (2, 0x101, 0x10000), (5, 0x105, 0), (0, 0, 0), (0xc, 3, 0x8000), (0x12, 0x12345601, 7)):
            h.append(dict(regs=dict(up, a3=rec(k), d6=d6, d5=d5, a0=0x100cb8)))
    if entry == 0x1c3b6:
        h += regs('d5', (0, 1, 0x10000, 0x8000))
    if entry in (0x1c3bc, 0x1c408):
        h += [dict(regs=dict(up, a3=rec(k), a4=SCR)) for k in (0, 1, 3, 0x12)]
    if entry == 0x1c3ca:
        pass                                                # consumer: chain fixtures only
    if entry == 0x1c3d2:
        h += regs('d7', (0, 1, 0x10000, 0xffff, 0x8000))
    if entry == 0x1c3dc:
        h += [dict(regs=dict(up, a3=rec(k), a0=0x100cb8), writes=[(0x0cb8 + 0x9e, 1, b)]) for k, b in ((0, 0), (1, 1), (0x12, 3), (0x13, 2), (3, 0))]
    if entry == 0x1c3e6:
        for k, t, w in ((1, 1, 0), (1, 2, 5), (3, 3, 0x3e7), (0, 0x12, 0x3e8), (2, 0x80, 0)):
            h.append(dict(regs=dict(up, a3=rec(k), a0=0x100cb8), writes=[(0x0cb8 + 0x8c, 4, SCR), ((SCR + 4) & 0xffff, 1, t), ((SCR + 0xc) & 0xffff, 2, w)]))
    if entry == 0x1c412:
        h += [dict(regs=dict(up, a4=SCR), writes=[((SCR + 0xc) & 0xffff, 2, v)]) for v in (0, 0x3e6, 0x3e7, 0x3e8, 0xffff, 0x8000)]
    if entry == 0x1c41e:
        for d7, w in ((0x3e5, 1), (0x3e6, 1), (0x3e6, 2), (0, 0x3e7), (0xffff, 1), (0x12340010, 0xfc19), (5, 0x8000)):
            h.append(dict(regs=dict(up, d7=d7, a3=SCR + 0x40), writes=[((SCR + 0x46) & 0xffff, 2, w)]))
    if entry in (0x1c42a, 0x1c42e):
        h += [dict(regs=dict(up, d7=v, a4=SCR)) for v in (0x3e6, 0x12340001, 0xffff)]
    if entry == 0x1c432:
        for a, b in ((1, 1), (1, 2), (0x80, 0x80), (0, 0xff)):
            h.append(dict(regs=dict(up, a3=SCR + 0x40, a4=SCR), writes=[((SCR + 0x40) & 0xffff, 1, a), ((SCR + 4) & 0xffff, 1, b)]))
    if entry == 0x1c43c:
        h.append(dict(regs=dict(up, d1=0x12345681, a3=SCR + 0x40, a4=SCR, a0=0x100cb8),
                      writes=[((SCR + 0x42) & 0xffff, 1, 0x5a), ((SCR + 4) & 0xffff, 1, 0x33), ((SCR + 2) & 0xffff, 1, 0x77), (0x0cb8 + 0xa1, 1, 0xee)]))
    if entry == 0x1c45c:
        h += [dict(regs=dict(up, a0=0x100cb8), stack=[(0, 4, a3), (4, 4, SENTINEL)], writes=[(0x0cb8 + 0x78, 2, w)]) for a3, w in ((rec(1), 0), (rec(2), 0x8001))]
    if entry == 0x1c462:
        h += [dict(regs=dict(up, d0=d0, a3=rec(k)), a6off=[(0xb2, 4, b2)]) for d0, k, b2 in ((0x1234ffff, 1, 0), (1, 2, 0x10e980), (0x8000, 3, 0x1fe980))]
    if entry == 0x1c476:
        h += [dict(a6off=[(0xb2, 4, v)]) for v in (0x10e980, 0x1fe981 - 1)]
    if entry == 0x1c480:
        h += regs('d1', (0, 0x12345678, 0xffffffff))
    if entry == 0x1c494:
        for d1, w in ((0x12345678, 0x8000), (0xffff0001, 0x7fff), (5, 0xffff), (0x80000000, 1)):
            h.append(dict(regs=dict(up, a0=0x10e980), stack=[(0, 4, d1), (4, 2, w), (6, 4, SENTINEL)]))
    # ---- 1c51c / 1cb1a .. 1cb5c
    if entry == 0x1c51c:
        h += [dict(regs=dict(up, a0=0x100cb8), writes=[(0x0cb8 + 0x9e, 1, v)]) for v in (0, 1, 2, 3, 4, 0x40, 0xff)]
    if entry == 0x1cb1a:
        for d7, w2, lv in ((2, 1, 0), (2, 1, 5), (4, 0x8001, 0), (0xfffe, 2, 1), (0x10004, 0x4000, 0)):
            h.append(dict(regs=dict(up, d7=d7, a0=SCR + 0x40), a6off=[(0x22, 4, SCR + 0x80)],
                          writes=[((SCR + 0x40 + ((d7 & 0xffff) - 0x10000 if d7 & 0x8000 else d7 & 0xffff)) & 0xffff, 2, w2),
                                  ((SCR + 0x80 + (((w2 << 2) & 0xffff) - 0x10000 if (w2 << 2) & 0x8000 else (w2 << 2) & 0xffff)) & 0xffff, 4, lv)]))
    if entry == 0x1cb44:
        for w, lv in ((0, 0), (1, 0x12345678), (0x4000, 0), (0xffff, 0x1c4b0)):
            h.append(dict(regs=dict(up, a0=SCR + 0x40, a1=0x10e0a6), a6off=[(0x22, 4, SCR + 0x80)],
                          writes=[((SCR + 0x40) & 0xffff, 2, w), ((SCR + 0x80 + ((((w << 2) & 0xffff) - 0x10000) if (w << 2) & 0x8000 else (w << 2) & 0xffff)) & 0xffff, 4, lv)]))
    # ---- 1cc1a .. 1cd0c
    if entry == 0x1cc1a:
        h += [dict(regs=dict(up), a6off=[(0xa0, 1, a), (0x9f, 1, b)]) for a, b in ((0, 1), (0, 2), (1, 3), (2, 5), (8, 8), (0, 0), (3, 0x10), (0xe, 0))]
    if entry == 0x1cc38:
        h += [dict(regs=dict(up, d0=v)) for v in (1, 2, 3, 0x101, 0x40, 0xc0, 0x12345601)]
    if entry in (0x1cc54, 0x1ccaa, 0x1ccb4):
        h += byte(0xa9, (0, 1, 2, 3, 0x83))
    if entry == 0x1cc6a:
        h += byte(0x9f, (0, 4, 5, 6, 8, 0x80))
    if entry == 0x1cc7c:
        h += [dict(regs=dict(up, a1=0x1cc10, d0=d0), a6off=[(0xa0, 1, a)]) for d0, a in ((0, 0), (0, 5), (0, 6), (0x12345600, 1), (0x80000000, 0x10), (0, 0xff))]
    if entry == 0x1ccd0:
        h += [dict(regs=dict(up), a6off=[(0x7c, 1, v)]) for v in (0, 1, 3, 5, 0x40, 0xff)]
    if entry == 0x1cd00:
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x1cd0a:
        h += regs('d0', (0, 0x10, 0x8000, 0x12340001))
    # ---- 1d182 / C3 tails 20240 .. 20574
    if entry in (0x1d182, 0x1d18c, 0x4d106, 0x2027e, 0x202ac):
        h += word(0x78, (0, 1, 0x8000, 0x100))
    if entry == 0x20240:
        h += byte(0xa7, (0, 4, 0xfb, 0xff)) + mirror
    if entry == 0x20268:
        h += byte(0xa8, (0, 1, 0xfe, 0xff))
    if entry == 0x20272:
        h += [dict(writes=[(0xf000, 1, v)]) for v in (0, 0x80, 0x7f, 0xff)]
    if entry == 0x20544:
        h += [dict(regs=dict(up), a6off=[(0x9e, 1, v)]) for v in (0, 1, 0x80)] + mirror
    if entry == 0x2055e:
        h += byte(0x61, (0, 0x80, 0x7f, 0xff)) + mirror
    if entry in (0x20554, 0x2056e):
        h += mirror
    # ---- 206ec / 20738 .. 209ce
    if entry == 0x206ec:
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v)]) for v in (0, 1, 2, 3, 0x4000, 0xc000)]
    if entry == 0x20738:
        h += [dict(a6off=[(0x5f, 1, a), (0x15, 1, b)]) for a, b in ((0, 0), (0x80, 0xff), (0x7f, 0x01), (0xff, 0xfe))] + mirror
    if entry in (0x20746, 0x2074c):
        h += [dict(regs=dict(up), a6off=[(0x15, 1, a), (0x61, 1, b), (0xa7, 1, c)]) for a, b, c in ((0, 0, 0xff), (0xff, 0x7f, 0x3f), (0xfe, 0xff, 0xc0))] + mirror
    if entry == 0x20778:
        h += [dict(regs=dict(up), a6off=[(0x9e, 1, v)]) for v in (0, 1, 2, 3)] + mirror
    if entry == 0x208d2:
        h += byte(0x9e, (0, 1, 0x80))
    if entry == 0x208f2:
        h += byte(0x5e, (0, 0x7f, 0x80, 0xff))
    if entry in (0x20932, 0x214ea):
        h += regs('d0', (0, 8, 0xfff7, 0x12345608))
    if entry in (0x2093a, 0x209c2):
        h += [dict(regs=dict(up), a6off=[(0x5e, 1, v)]) for v in (0, 2, 0x1a, 0x1b, 0x1c, 0x7f, 0x80)]
    if entry in (0x20946, 0x209ce):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 2, 0x1a, 0x12345602, 0xff02, 7, 0x11)]
    # ---- 20de6 .. 20f20 / 21446 .. 21470
    if entry in (0x20de6, 0x21446):
        for v36, v3a in ((0, 0), (1, 0x30000), (0xffffffff, 0x30001), (0x80000000, 0x7fffffff), (0x20, 0xffea0000), (0x1f, 0xffe9ffff), (0x7fffffff, 0x80000000)):
            h.append(dict(regs=dict(up), a6off=[(0x36, 4, v36), (0x3a, 4, v3a)]))
    if entry in (0x20df6, 0x21456):
        h += regs('d2', (0xffffffe1, 0x7fffffff, 0, 0x7fffffe1))
    if entry in (0x20e0a, 0x2146a):
        h += regs('d3', (0xffffffe1, 0x7fffffff, 0, 0x7fffffe1))
    if entry in (0x20dfc, 0x2145c):
        for d2, d3, v36, v3a in ((0x1f, 0x30000, 0, 0x30000), (0x20, 0, 0x7fffffff, 1), (0xffffffe0, 0xffea0000, 0x10, 0xffea0001), (0x80000000, 5, 0, 0x80000000),
                                 (0x7fffffff, 0x80000000, 0x80000000, 0x7fffffff)):
            h.append(dict(regs=dict(up, d2=d2, d3=d3), a6off=[(0x36, 4, v36), (0x3a, 4, v3a)]))
    if entry in (0x20e10, 0x21470):
        h += [dict(regs=dict(up, d3=v), a6off=[(0x3a, 4, 0x12345678)]) for v in (0x1f, 0x20, 0xffffffe0, 0x80000000, 0xffffffff)]
    if entry in (0x20efc, 0x20f04):
        h += byte(0x5f, (0, 0x7f, 0x80, 0xff)) + mirror
    if entry in (0x20e20, 0x21314, 0x21412, 0x21430, 0x214c0, 0x21542, 0x20e5a, 0x214b6, 0x21f9c, 0x21f54):
        h += mirror
    # ---- 212ce .. 21562
    if entry in (0x212d4, 0x213e4):
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v)]) for v in (0, 1, 2, 0x4000)]
    if entry in (0x212f2, 0x213fc, 0x2143c, 0x21430):
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry == 0x21494:
        for w88, w2c in ((0x100, 0), (0, 0x100), (0x8000, 0x7fff), (0x20, 0x2f), (0x10, 0x11), (0xffff, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x88, 2, w88), (0x2c, 2, w2c)]))
    if entry in (0x214d6, 0x2155a):
        h += byte(0x88, (0, 1, 2, 0x80, 0xff))
    if entry == 0x214f2:
        h += long_(0x3a, (0, 0x5000, 0x4fff, 0x80000000))
    if entry == 0x21524:
        h += [dict(regs=dict(up), a6off=[(0x42, 2, v)]) for v in (0x13f, 0x140, 0x8000, 0, 0xffff)]
    if entry == 0x21530:
        h += [dict(regs=dict(up), a6off=[(0x46, 2, v)]) for v in (0xbf, 0xc0, 0x2bf, 0x2c0, 0, 0x8000)]
    # ---- 21c12 .. 21fa4
    if entry == 0x21f7c:
        h += regs('a1', LIST_21B26)
    if entry in (0x21f82, 0x21f8a):
        h += regs('d0', (0, 0x10, 0x40, 0x50, 0xffaf, 0x12345600))
    if entry == 0x21f96:
        h += regs('d7', (0, 1, 0x10000, 0x8000))
    # ---- 4d106 .. 4de8a
    if entry == 0x4d628:
        h += regs('d0', (0, 1, 0x100, 0xff, 0x12345600))
    if entry == 0x4d63a:
        h += [dict(regs=dict(a4=SCR), writes=[(SCR & 0xffff, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x4d640:
        for k, d2 in ((0, 0), (1, 1), (2, 0x1f), (3, 0x20), (0, 0x21), (0x80, 5), (0xff, 0x12345602)):
            h.append(dict(regs=dict(up, a4=SCR, d2=d2), writes=[((SCR + 0x27) & 0xffff, 1, k)]))
    if entry == 0x4d65c:
        h += [dict(regs=dict(up, a4=SCR, d2=d2), writes=[((SCR + 0x2b) & 0xffff, 1, b)]) for d2, b in ((0, 0), (0x100, 0xfb), (1, 0xff))]
    if entry == 0x4d668:
        h += [dict(regs=dict(up, a4=SCR, d2=d2), writes=[((SCR + 0x2a) & 0xffff, 1, b)]) for d2, b in ((5, 5), (0x105, 5), (5, 6), (0x80, 0x80))]
    if entry in (0x4d670, 0x4d676):
        h += [dict(regs=dict(up, a4=SCR, d2=0x12345681), writes=[((SCR + 0x20) & 0xffff, 2, 0x5555), ((SCR + 0x2a) & 0xffff, 1, 0x33)])]
    if entry == 0x4d67a:
        h += [dict(regs=dict(up, a4=SCR), writes=[((SCR + 0x20) & 0xffff, 2, v)]) for v in (0, 0x7fff, 0x8000, 0xffff)]
    if entry == 0x4d682:
        for d1, w in ((0, 0x3e7), (1, 0x3e7), (0x3e8, 0), (0xffff, 2), (0x12340001, 0x3e6), (0x8000, 0x8000)):
            h.append(dict(regs=dict(up, a4=SCR, d1=d1), writes=[((SCR + 0x20) & 0xffff, 2, w)]))
    if entry == 0x4d692:
        h += [dict(regs=dict(up, a4=SCR, d1=d1, d7=d7)) for d1, d7 in ((5, 3), (0x3e7, 0x3e8), (0x12340000, 0x56780001))]
    if entry in (0x4d69c, 0x4d6a8):
        h += [dict(regs=dict(up, a4=SCR), writes=[((SCR + 0x2a) & 0xffff, 1, v)]) for v in (0, 0x80, 0xff)]
    if entry == 0x4de7a:
        h += regs('d0', (0, 1, 2, 0x10001, 0xfffe))
    if entry in (0x4d11a, 0x4de8a, 0x4d10e, 0x4d116, 0x4de86):
        h += [dict(regs=dict(up))]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def chain_hint(entry, t, rng):
    if entry == 0x1c36e:
        # 289e: CMPI.L #270e,(A0) (C Clear when the node at A0 holds the callback 270e, Set otherwise)
        return dict(regs=dict(a0=(0x100cb8, 0x100da8)[t % 2]), writes=[((0x0cb8, 0x0da8)[t % 2], 4, (0x270e, 0x1ef0e, 0x270e, 0x2b99c)[(t // 2) % 4])])
    if entry == 0x1c3c0:
        # 4d628: TST.B D0 -> WORD (A5 + 5cba / 5ce6) 0 -> Clear; else the record 4cf64 + 16 x BYTE 27 (ROM: the LONG at +4 is 107d for record 5 and 7d
        # for record 11, 0 for 0..4), BTST.L D2 -> Set / Clear
        w = (0, 1)[t % 2]
        return dict(regs=dict(d0=w, d2=(0, 2, 4, 1, 0x1c)[(t // 2) % 5], a3=0x1c298 + 10 * (t % 3), a0=0x100cb8),
                    a5off=[(0x5cba + 0x2c * w, 2, (1, 0x100, 0)[(t // 10) % 3]), (0x5cba + 0x2c * w + 0x27, 1, (5, 11, 0, 1)[(t // 3) % 4])])
    if entry == 0x2027e:
        w = (0, 1, 0x8000, 0xffff)[t % 4]
        return dict(a6off=[(0x78, 2, w)], a5off=[(0x5734 + 4 * (w & 1), 4, (0, 0x10e400)[(t // 4) % 2])])   # 49c38: TST.L 5734(A5) + 4 (D0.W & 1)
    if entry in (0x20e50, 0x214ac) and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> Set
    if entry == 0x21f70:
        return dict(a6off=[(0x9c, 1, (0, 1, 3, 4, 5, 0xb)[t % 6])])    # the ROM list 21b26: (21602, 0) (21e48, 3) (21e3a, 4)
    if entry == 0xcddee:
        return dict(writes=[(0x4ca0, 2, (0x100, 0x15, 0x40, 0)[t % 4])])
    if entry == 0x1c3dc:
        # 1c51c: BTST.L D1,D7 with D1 = BYTE (A3) (the record type: 0..12 in the ROM records, bits 0..18 of the ROM LONG 0007ffff are set) -> the
        # Z = 1 side needs a type 13..1f (a RAM record at SCR + 40)
        if t % 3 == 2:
            return dict(regs=dict(a3=SCR + 0x40, a0=0x100cb8), writes=[((SCR + 0x40) & 0xffff, 1, 0x13 + t % 13), (0x0cb8 + 0x9e, 1, (t // 3) % 4)])
        return dict(regs=dict(a3=0x1c298 + 10 * (t % 0x13), a0=(0x100cb8, 0x100da8)[t % 2]), writes=[((0x0cb8, 0x0da8)[t % 2] + 0x9e, 1, (0, 1, 2, 3)[(t // 2) % 4])])
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
            if tr is None:
                continue
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 15 bits 0 / 7, BYTE 5f / 5e (the tables 20952 / 209da, negative: 208fa) / 9e (the table 20796),
            # BYTE 88 (the 214d6 / 2155a counters), WORD 42 / 46 (21524 / 21530), WORD 78, LONG 26 (0: 49fc6 Set), WORD 104ca0 (28ae count limit)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 1, 0x81)[t % 4]), (0x5f, 1, (0, 0x80)[(t // 2) % 2]),
                               (0x5e, 1, (2, 0, 0x1b, 0x80, 1, 0x1a)[(t // 3) % 6]), (0x9e, 1, (0, 1, 0, 3)[(t // 4) % 4]), (0x88, 1, (0, 1, 0x1e)[t % 3]),
                               (0x42, 2, (0x100, 0x140)[(t // 5) % 2]), (0x46, 2, (0x100, 0x2c0)[(t // 7) % 2]), (0x78, 2, (0, 1)[t % 2])] +
                       ([(0x26, 4, 0)] if t % 5 == 4 else []),
                        writes=[(0x4ca0, 2, (0x100, 0x15, 0x40)[(t // 11) % 3])])
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
            if len(kept) >= 3:
                break
        require(kept, ('no node world', hex(entry)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add_run(add, 'node-%05x-%d' % (entry, i), st, tr, dict(family='node', entry=entry, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))


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
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a frame in which a node of the pool NATURAL_NODES holds one of NATURAL_CALLBACKS as its
    callback LONG; declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the
    frame start.  Up to the sentinel or the first unrouted PC.  The reinstall worlds write one declared callback LONG (and declared slot-84 LONGs) first."""
    entries = set(NATURAL_CALLBACKS)
    count = 0
    for cfg, case, frame in NATURAL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        ram = st0['ram']
        for a in range(NATURAL_NODES[0] & 0xffff, NATURAL_NODES[1] & 0xffff, 2):
            cb = struct.unpack('>I', ram[a:a + 4])[0]
            if cb not in entries:
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
        add_run(add, 'reinstall-%05x-%s%s-f%d-%x%s' % (cb, cfg, '' if case is None else '%03d' % case, frame, node, tag), st, tr,
                dict(family='reinstall', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
        count += 1
    require(count >= 20, ('too few natural node fixtures', count))


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
            if tr is None:
                continue
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
    err('odd-pc', U.with_host_writes(st, pc=0x1c357), 'unaligned animation machine PC', 0x1c357)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the computed jumps (contract decision 2): the BRA.W table displacements beyond the ROM ranges (BYTE 9e above 3; D0.B at / above 1b for a direct
    # 20946 / 209ce entry), JMP (A1) 21f7c with A1 outside the list 21b26; a listed / table target that is not routed fails at the next dispatch (the
    # paired row stops at that target)
    for v in (4, 0x40, 0xff):
        err('20778-9e-%x' % v, U.with_host_writes(st, [((a6 + 0x9e) & 0xffff, 1, v)], pc=0x20778), ERROR_JUMP, 0x20778)
    for v in (1, 2, 3):
        err('20778-9e-%x-entry' % v, U.with_host_writes(st, [((a6 + 0x9e) & 0xffff, 1, v)], pc=0x20778), unrouted, 0x20796 + 4 * v)
    for v in (0x1b, 0x1c, 0xff, 0x12345640):
        err('20946-d0-%x' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x20946), ERROR_JUMP, 0x20946)
        err('209ce-d0-%x' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x209ce), ERROR_JUMP, 0x209ce)
    for v in (0, 1, 0x1a, 0x12345603):
        err('20946-d0-%x-entry' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x20946), unrouted, 0x20952 + 4 * (v & 0xff))
        err('209ce-d0-%x-entry' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x209ce), unrouted, 0x209da + 4 * (v & 0xff))
    for v in (0x21622, 0x21b26, 0, 0x1021602, 0x21603, 0x21c66, 0x21f70):
        err('21f7c-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21f7c), ERROR_JUMP, 0x21f7c)
    for v in (0x21e48, 0x21e3a):
        err('21f7c-a1-listed-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21f7c), unrouted, v)
    #   C3 21f70 (BYTE 9c = 3) -> 215e6 on the ROM list 21b26 -> Set, A1 = 21e48 -> 21f78 -> 21f7c JMP (A1): listed, unrouted
    err('21f70-then-21e48', U.with_host_writes(st, [((a6 + 0x9c) & 0xffff, 1, 3)], pc=0x21f70), unrouted, 0x21e48)
    # the Z source of 1c3e2 (contract decision 3): BYTE 9e(A0) outside work RAM / fixed ROM, D7 not the LONG of the table 1c52c (ROM 0007ffff)
    for v in (0x200000 - 0x9e, 0x3c0000, 0x2ffff0):
        err('1c3e2-a0-%x' % v, U.with_host_writes(st, regs=dict(a0=v, d7=0x7ffff), pc=0x1c3e2), ERROR_FLAG, 0x1c3e2)
    for v in (0x7fffe, 0, 0x8007ffff):
        err('1c3e2-d7-%x' % v, U.with_host_writes(st, [(0x0cb8 + 0x9e, 1, 0)], regs=dict(a0=0x100cb8, d7=v), pc=0x1c3e2), ERROR_FLAG, 0x1c3e2)
    # odd node / stack / A0 / A3 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('2027e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x2027e), odd_word, 0x2027e, stop=0x49c38)
    err('20778-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x20778), odd_write, 0x20778, stop=0x20796)
    err('20554-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x20554), odd_write, 0x20554, stop=0x20626)
    err('1c390-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1c390), odd_word, 0x1c390, stop=0x4d7a6)
    err('1c39a-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1c39a), odd_word, 0x1c39a, stop=0x1c3dc)
    err('1c462-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1, a3=0x1c2a2), pc=0x1c462), odd_word, 0x1c462, stop=0x1c480)
    err('1c494-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1c494), odd_word, 0x1c494)
    err('1cb44-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x1cb44), odd_word, 0x1cb44, stop=0x1cb56)
    err('1c412-odd-a4', U.with_host_writes(st, regs=dict(a4=a6 + 1), pc=0x1c412), odd_word, 0x1c412, stop=0x1c41e)
    err('4d63a-odd-a4', U.with_host_writes(st, regs=dict(a4=a6 + 1), pc=0x4d63a), odd_word, 0x4d63a, stop=0x4d640)
    # failures after executed blocks:
    #   20f04 (BYTE 5f = 0) -> 20f0c -> 20f20 RTS at an odd A7
    err('20f04-then-20f20', U.with_host_writes(st, [((a6 + 0x5f) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x20f04), odd_word, 0x20f20)
    #   21524 (WORD 42 = 0, WORD 46 = 100) -> 21530 -> 21540 RTS at an odd A7
    err('21524-then-21540', U.with_host_writes(st, [((a6 + 0x42) & 0xffff, 2, 0), ((a6 + 0x46) & 0xffff, 2, 0x100)], regs=dict(a7=a7 + 1), pc=0x21524),
        odd_word, 0x21540)
    #   4d628 (D0.B = 0, WORD 5cba(A5) = 0) -> 4d62e -> 4d63a -> 4d6a8 RTS at an odd A7
    err('4d628-then-4d6a8', U.with_host_writes(st, [((0x108000 + 0x5cba) & 0xffff, 2, 0)], regs=dict(d0=0, a7=a7 + 1), pc=0x4d628), odd_word, 0x4d6a8)
    #   214d6 (BYTE 88 = 0) -> SUBQ.B borrow -> 21564 (player C6 since; was: unrouted at 21564, error-214d6-then-21564) -> JMP 2a00 -> BSR.B 299c at
    #   an odd A7
    err('214d6-then-2a00', U.with_host_writes(st, [((a6 + 0x88) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x214d6), odd_word, 0x2a00)
    #   208f2 (BYTE 5e negative) -> 208fa (deferred leader, unrouted)
    err('208f2-then-208fa', U.with_host_writes(st, [((a6 + 0x5e) & 0xffff, 1, 0x80)], pc=0x208f2), unrouted, 0x208fa)
    #   21f8a (D0 bit 4) -> 2210c (deferred leader, unrouted)
    err('21f8a-then-2210c', U.with_host_writes(st, regs=dict(d0=0x10), pc=0x21f8a), unrouted, 0x2210c)
    #   2093a (BYTE 5e = 0) -> 20946 -> JMP 20952 (entry 0, unrouted)
    err('2093a-then-20952', U.with_host_writes(st, [((a6 + 0x5e) & 0xffff, 1, 0)], pc=0x2093a), unrouted, 0x20952)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x1c378, 0x4d640, 0x21494, 0x20de6)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
