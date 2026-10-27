"""V1 fixture spec of the area-C unit C7 (engine/src/animation_machine_player_c7.cpp, 214 block starts; file prefix pc7 / player_c7 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c7-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C7 spec of the
contract): the player input state 1f2a4 -> 1f2d4 / 1f538 -> 1f56a / 1f5d2 / 1f5f2 -> 1f6aa -> 1f6da (1cab6, 1cd98, 1cb08, 1cec2, 4bfc0 / ce02 / 49fc6,
201a2), the C helper 1c9ec / 1ca4c (the BYTE records 5450 / 5460(A5)), the interpreter script callbacks 22480 (4ae4a, the sounds 3af8), 22656 (the BYTE
table 22642, the LONG tables 225f6 / 225e6, the 2986 children, DIVU.W #3 / MULS.W D7,D0) and 2285c (the 2986 child 23c56, the LONG table 2284c), the
2986 child 24fb0 -> 25102 (443d2, the LONG tables 25082 / 250c2, 4ae4a, ea69c, the BRA.W table 2529c, contract decision 2) and its child 253f4 -> 25448.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C6) with declared host edits.
This code runs natively only in the IO observation (boot-demo-0 frames 431..480): the 'natural' family takes the frame-start states of the IO native
observation in which a node of the pool holds a callback that runs into C7 code (the player node 100cb8 with 1f6da, the 2986 children with 24fb0 /
253f4 / 25448), keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the sentinel return LONG,
PC = the callback); the 'reinstall' family enters a C7 state (1f2a4, 1f538, 1f5d2, 1f5f2, 1f6da) on the player node of a demo frame (the frame-start
input of 1cd98 is the previous frame's: the natural 1ebf6 of frame 431 does not reach 1f2a4 from the pack state).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 10 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the consumer's successor or the first unrouted PC.
  node      the installed values and 2986 children (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with a declared callback / BYTEs.
  callee    the helpers, script callbacks and states entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 10 consumers, the jump-target guard of 25294 (decision 2), the
            unrouted table entries, odd node / stack / A0, failures after executed blocks: checked error, state preserved, every row with its failing
            PC (a paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C6
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C6)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc7'
ERROR_PC = 'unsupported animation player c7 PC'
ERROR_CARRY = 'player c7 caller requires known carry'
ERROR_JUMP = 'unsupported animation player c7 jump target'

RANGES = [(0x1c9ec, 0x1ca74), (0x1f2a4, 0x1f33e), (0x1f538, 0x1f65e), (0x1f6aa, 0x1f756), (0x1f76a, 0x1f7a4), (0x22480, 0x22502), (0x22656, 0x22788),
          (0x2285c, 0x2291a), (0x24fb0, 0x25082), (0x25102, 0x2529c), (0x252a4, 0x252a8), (0x252c0, 0x252ce), (0x253c8, 0x25488)]
STARTS = sorted(int(x, 16) for x in (
    '1c9ec 1c9f8 1c9fc 1ca04 1ca0a 1ca0e 1ca12 1ca14 1ca20 1ca28 1ca2e 1ca3a 1ca40 1ca42 1ca46 1ca4c 1ca56 1ca5c 1ca68 1ca6a 1f2a4 1f2ac 1f2d4 1f2d8 '
    '1f2e2 1f2ea 1f2f4 1f2fc 1f306 1f30a 1f312 1f31a 1f320 1f32a 1f330 1f334 1f33a 1f538 1f546 1f56a 1f56e 1f578 1f580 1f58a 1f592 1f596 1f59e 1f5a6 '
    '1f5ae 1f5b4 1f5be 1f5c4 1f5c8 1f5ce 1f5d2 1f5f2 1f614 1f62c 1f634 1f63e 1f640 1f644 1f648 1f6aa 1f6ae 1f6da 1f6de 1f6e8 1f6f0 1f6fa 1f702 1f706 '
    '1f70a 1f712 1f71a 1f728 1f732 1f73c 1f742 1f74c 1f752 1f76a 1f76e 1f776 1f77a 1f77e 1f782 22480 224a6 224b8 224c0 224c2 224ca 224d4 224d6 224de '
    '224e8 224ea 224f4 224f6 22500 22656 22670 22674 22678 2267a 2268a 2269e 226b0 226b8 226c2 226c8 226ca 226f0 22704 2270a 2271e 22726 2273c 2274e '
    '22758 2275a 22764 22766 22772 22786 2285c 2286a 22872 2288e 22894 228ae 228b6 228b8 228bc 228ca 228cc 228e6 228e8 2290a 22912 24fb0 24fc8 24fec '
    '24ffa 25026 2503a 2503e 25054 25056 2506c 2506e 25102 25108 2511e 25122 2512c 25132 2513a 25140 25144 2514e 25158 2515e 25166 2516c 25172 2517e '
    '25184 25194 2519a 251ac 251b6 251ba 251c0 251c2 251da 251e0 251f6 251fc 25210 2521a 25220 2523a 25240 25254 2525a 25264 2526a 25276 25284 2528c '
    '25294 252a4 252c0 252ca 253c8 253de 253ee 253f4 25402 25414 25422 25428 25438 25448 2544e 25454 25458 2545e 2546a 25470 25480 25486').split())
# the 10 C consumers: BCS 1ca0e (1ca4c of C7), BCC 1f330 1f5c4 1f752 25454 (49fc6), BCS 1f644 1f776 (1cb08 of C2), BCS 22674 (1c9ec of C7), BCC 22704
# (2986, after MOVEA.L (A7)+,A1), SCS.B 83(A6) 25140 (ea69c)
CONSUMERS = (0x1ca0e, 0x1f330, 0x1f5c4, 0x1f644, 0x1f752, 0x1f776, 0x22674, 0x22704, 0x25140, 0x25454)
CLEAR_SET = (0x1ca04, 0x1ca28)          # ANDI.B #fe,CCR; RTS
SET_SET = (0x1ca46, 0x1ca56, 0x1ca6a)   # ORI.B #1,CCR; RTS
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x1ca5c,)                   # MOVE.B 2(A4),D2; CMP.B 3(A4),D2; BCS.W 1ca6a: the borrow (unsigned BYTE 2 < BYTE 3) is the known C of both successors
INVERT_SET = ()
PASS_SET = (0x1ca12, 0x1ca68)           # RTS (carry preserving: the C of 1ca0e / 1ca5c reaches the callers of 1ca4c / 1c9ec)
STARTS_SET = set()
Z_READERS = ()                          # no Z crosses a return in C7
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units that a C7 block reaches by a fall-through, a branch or a call (C8 1eb98 1f756 1fa68), and the still unrouted later-unit stops of the
# C1..C6 blocks that the C7 runs pass through (pc6 EXIT_STOPS that are still unrouted; the TRAP site 4e69a of C1; the interpreter stub successors 1dc8e /
# 1dccc).  Declared stops of the native runs: a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1eb98, 0x1f756, 0x1fa68,
              0x1d3e0, 0x4eb6a, 0xea626, 0x1dc8e, 0x1dccc,
              0x208fa, 0x2210c, 0x1ef4c, 0x21d9e, 0x1efd6, 0x1f070, 0x21dd0, 0x223a0, 0x223d6, 0x4ef08, 0x1ce98, 0x1cfde, 0x1de3c, 0x1e21c, 0x1e8de,
              0x1fafc, 0x1fc96, 0x1fd50, 0x201bc, 0x21ca4, 0x21d0e, 0x21fa6, 0x4d0cc, 0x4e69a,
              # player C10 routes the entries below since C10 (declared stops of the C7 runs, as before C10)
              0x1f082, 0x20bfe, 0x22148, 0x22286, 0x223fa, 0x20324, 0x21e04, 0x2228e, 0x22360, 0x252b4,
              # player C11 routes the C3 list handler 21950 and the slot-84 values 21960 21a76 since C11 (declared stops, as before C11)
              0x21950, 0x21960, 0x21a76)
UNIT_EXITS = EXIT_STOPS[:3]             # the C7 later-unit stops
# later-unit stops routed since (player C8: 1eb98 1f756 1fa68 ea626 1ef4c 21d9e 1ce98 1cfde 1fafc 201bc 4d0cc; player C9: 208fa 2210c 1f070 223a0
# 223d6 21ca4 21d0e): still declared stops of the C7 runs
ROUTED_LATER = (0x1eb98, 0x1f756, 0x1fa68, 0xea626, 0x1ef4c, 0x21d9e, 0x1ce98, 0x1cfde, 0x1fafc, 0x201bc, 0x4d0cc, 0x208fa, 0x2210c, 0x1f070, 0x223a0,
                0x223d6, 0x21ca4, 0x21d0e,
                # player C10 (the C10 entries kept as declared stops)
                0x1dc8e, 0x1dccc, 0x1efd6, 0x1f082, 0x20bfe, 0x21dd0, 0x22148, 0x22286, 0x223fa, 0x20324, 0x21e04, 0x2228e, 0x22360, 0x252b4,
                # player C11 (the C11 entries kept as declared stops)
                0x1d3e0, 0x4eb6a, 0x1e8de,
                # player C11 (the C3 list handler / slot-84 values kept as declared stops)
                0x21950, 0x21960, 0x21a76)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1ca0a, 0x1ca0e), (0x1f32a, 0x1f330), (0x1f5be, 0x1f5c4), (0x1f74c, 0x1f752), (0x1f640, 0x1f644), (0x1f76e, 0x1f776), (0x22670, 0x22674),
          (0x226f0, 0x22704), (0x2513a, 0x25140), (0x2544e, 0x25454))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# computed jump (contract decision 2): JMP 2529c(PC,D0.W) 25298, the BRA.W table 2529c..252c0 (9 entries; CMPI.W #9,D0; BCC.W 252c0 at 2528c); only the
# executed entry 252a4 is a block of the unit (the executed entry 252b4 is a player C10 block since C10, main decision 4: a declared stop of the C7 runs)
JUMP_PCS = (0x25298,)
TABLE_2529C = tuple(0x2529c + 4 * k for k in range(9))
JUMP_ROUTED = ()
# computed jumps of C3 / C4 / C5 that the C7 runs reach (C3 2031c table, 201a6 JSR (A4) (from 1f33a / 1f5ce / 1f76a BRA 201a2), 21620 / 221de JMP (A1);
# C4 21c72 JMP (A1); C5 20792 2094e 209d6 21f7c): an unrouted target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c)
TABLE_ENTRIES = ()
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92)   # routed slot-84 states (C3 and C4 21d92) for the worlds
# installed values entered as node callbacks (1f2d4 1f56a 1f6da 25102 25448) and the 2986 children of the unit (24fb0 from the LONG tables 22502 / 2254e,
# 253f4 from 253c8); the callee entries (helpers, script callbacks of the interpreter table 4a500 (A0 = the script LONG), states entered as subroutines;
# not the pass blocks 1ca12 / 1ca68: their readers are the callers of 1ca4c / 1c9ec)
NODE_ENTRIES = (0x1f2d4, 0x1f56a, 0x1f6da, 0x25102, 0x25448, 0x24fb0, 0x253f4)
CALLEES = (0x1c9ec, 0x1ca4c, 0x22480, 0x22656, 0x2285c, 0x1f2a4, 0x1f538, 0x1f5d2, 0x1f5f2, 0x1f648, 0x1f76e, 0x226ca, 0x22894, 0x2273c, 0x2528c,
           0x252c0, 0x25132, 0x251c2, 0x25172)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('boot-demo-0', None, f) for f in (432, 440, 441, 442, 443, 447, 448, 453, 459, 465, 480)])
NATURAL_CALLBACKS = (0x1ebf6,) + NODE_ENTRIES                         # C6 1ebf6 -> 1f2a4, the C7 states and children
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node), extra (offset, size, value) writes on the node)
REINSTALL = (('boot-demo-0', None, 431, 0x100cb8, 0x1f2a4, ()), ('boot-demo-0', None, 465, 0x100cb8, 0x1f5d2, ()),
             ('boot-demo-0', None, 440, 0x100cb8, 0x1f5f2, ()), ('boot-demo-0', None, 440, 0x100cb8, 0x1f5f2, ((0xa7, 1, 1),)),
             ('boot-demo-0', None, 440, 0x100cb8, 0x1f538, ()), ('boot-demo-0', None, 443, 0x100cb8, 0x1f6da, ((0x7e, 1, 1),)),
             ('boot-demo-0', None, 432, 0x100cb8, 0x1f6da, ((0x15, 1, 0),)), ('boot-demo-0', None, 465, 0x100cb8, 0x1f76e, ()),
             ('boot-demo-0', None, 441, 0x100cb8, 0x1f2a4, ((0x9e, 1, 1),)))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x13, 0x14, 0x1e, 0x1f, 0x20, 0x40, 0x50, 0x7f, 0x80, 0x81, 0xbf, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x13, 0x14, 0x40, 0x7f, 0x80, 0xe0, 0x140, 0x180, 0x200, 0x280, 0x7ffc, 0x7fff,
      0x8000, 0x8001, 0xe0ec, 0xffe0, 0xfffd, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x30000, 0x50000, 0x7fffffff, 0x80000000, 0xfffe0000, 0xffffffe0, 0xffffffff, 0x12345678)
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
BUNDLED = ()                            # no flag-sharing Bcc pair in C7


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (1c9f8 / 1ca3a / 1ca40 / 1ca42 / 1f2ac / 1f334 / 1f546 / 1f5c8 / 1f62c / 1f63e / 1f6ae / 226b0 / 226c8 / 2271e / 22764 /
    22772 / 228b8 / 228ca / 2290a / 2503a / 25054 / 2506c / 251b6 / 251ba / 251da / 2525a / 25438 fall into the next start; 22912 into the routed
    2291a)."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (none in C7) would use pcs[n - 1]."""
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
    jump 25298 that is not a block start of this unit (the unrouted table entries 2529c 252a0 252a8 .. 252bc: the C++ dispatch of it is the checked PC
    error), at an unrouted target of the C3 / C4 / C5 computed jumps that the C7 runs reach (OTHER_JUMP_PCS), or at the first unrouted PC that is not
    the straight-line successor of the previous instruction (a PC inside a block of another executor is not a block entry)."""
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it (as C1..C6): WORD 76 / 78(A6) mostly 0 / 1 (the
        player index), BYTE 9e(A6) 0..3 (the LONG tables 225e6 / 2284c; C5 20796), the record LONG 8c(A6) (A4) with BYTE 4(A4) mostly 0..12 (the
        BYTE table 22642, the LONG tables 225f6 / 1f65e / the sub-tables of 225e6) and BYTE 6(A4) mostly below 4, A0 a script LONG that points to a
        declared record (the interpreter callbacks 22480 / 22656 / 2285c), D0.W 0..8 for a direct 25294 entry (the BRA.W table 2529c, contract decision
        2), D0 input bits, D1.B the key of 1c9ec and the result of 1cec2, LONG 84(A6) a routed slot-84 value (the C3 JSR (A4) 201a6 that 1f33a / 1f5ce /
        1f76a reach), LONG 5434(A5) = 0 (C2 decision 2), BYTE 10fd82 = 0 (keeps the controller C1 4a974 off the BIOS call c00450, not mapped natively)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0xc, 0x10, 0x12, 0x20, 0x22, 0x30, 0x40, 0x50, 0x80, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000))
        if rng.random() < 0.6:
            regs['d1'] = (regs['d1'] & 0xffffff00) | rng.choice((0, 1, 2, 3, 5, 0xa, 0x11, 0x13, 0xff))
        if entry in (0x25294,):
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 4, 5, 6, 7, 8, 0x4002, 0x8001, 0xc008))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = self.pointer()
        if entry in (0x22480, 0x22656, 0x2285c, 0x2268a, 0x226f0, 0x22872, 0x228cc) or rng.random() < 0.3:
            regs['a0'] = rec                                    # a script LONG: the record of the interpreter callbacks (declared below)
        regs['a1'] = rec if entry in (0x2270a, 0x228e8) and rng.random() < 0.8 else self.pointer()
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = rec + 0x20 if rng.random() < 0.6 else self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, rec + 0x20 if rng.random() < 0.7 or entry in (0x2285c, 0x22894, 0x228ae, 0x228b8, 0x228bc, 0x228ca)
                       else self.pointer()))           # LONG 8c(A6): the record A4 (the 2284c lists need BYTE 6 1..3 there)
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of C2 1cb08 / C5 1cb1a / 1cb44)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(),))))   # LONG 3e(A6) (C2 1a9fe..1aa20)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): C3 2031c / C5 1cc1a
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): C3 206d4
        writes.append(((a6 + 0x9f) & 0xffff, 1, rng.randrange(9)))                        # BYTE 9f(A6): C2 1cb08
        writes.append(((a6 + 0x7c) & 0xffff, 2, rng.choice((0, 0x80, 0x180, 0x280, 0x281, 0x7fff, 0x8000, 0xfff0))))   # WORD 7c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x4000, 0xffff))))   # WORD 76(A6)
        writes.append(((a6 + 0x78) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x100))))        # WORD 78(A6): the player index
        writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                        # BYTE 9e(A6): the tables 225e6 / 2284c, C5 20796
        for node in (0x100cb8, 0x100da8):
            writes.append((node & 0xffff, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c))))   # 289e: CMPI.L #270e,(A0)
            writes.append(((node + 0x9e) & 0xffff, 1, rng.randrange(4)))
            writes.append(((node + 0x78) & 0xffff, 2, rng.choice((0, 1))))
        # the declared record (A4 = rec + 20; the script LONG at rec: rec + 10 holds three WORDs and a WORD 2 / 8 test value)
        writes.append(((rec) & 0xffff, 4, rec + 0x10))
        for k in range(3):
            writes.append(((rec + 0x10 + 2 * k) & 0xffff, 2, rng.choice((0, 2, 8, 0x10, 0x80, 0xfff0, 0x7f80, 0x8000))))
        writes.append(((rec + 0x24) & 0xffff, 1, rng.choice((0, 1, 2, 3, 5, 0xa, 0xc, 0xf, 0x10, 0x11, 0x12) if rng.random() < 0.9 else (0x13, 0x40))))
        writes.append(((rec + 0x26) & 0xffff, 1, rng.choice((1, 2, 3, 3)) if rng.random() < 0.9 else rng.choice((0, 4, 0xff))))
        # BYTE 6(A4): CMPI.B #4 (228bc); 0 / >= 4 select the LONG 0 of the 2284c lists: the 28ae failure inside 2986 (the C++ caller-X limit, decision 7)
        writes.append((0x4ca0, 2, 0x100))                     # WORD 104ca0 (the 28ae count limit of 2986): above the D0.W a / 1e of the C7 children
        writes.append(((a6 + 0x26) & 0xffff, 4, 0))           # 49fc6: LONG 26(A6) = 0 -> Set without the interpreter (random scripts: C++ dispatch limit)
        if entry == 0x2268a and rng.random() < 0.8:
            regs['d0'] = 0x24fb0                              # the child LONG of 225f6 (not 0: 28ae fails on A0 = 0)
        if entry == 0x226f0 and rng.random() < 0.8:
            regs['d7'] = 0x24fb0
        if entry == 0x228cc and rng.random() < 0.8:
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((1, 2, 3))
        writes.append(((rec + 0x27) & 0xffff, 1, rng.choice((0, 0, 1, 2, 0x80))))         # BYTE 7(A4): 228ae
        writes.append(((rec + 0x2a) & 0xffff, 2, rng.choice((0, 0, 1, 2, 0x8000))))       # WORD a(A4): 2286a
        writes.append(((rec + 0x22) & 0xffff, 1, rng.choice((0, 1, 2, 3, 0x80, 0xfe))))   # BYTE 2(A4) / 3(A4): 1ca4c / 1ca5c
        writes.append(((rec + 0x23) & 0xffff, 1, rng.choice((0, 1, 2, 3, 0x80, 0xff, 0xff))))
        writes.append(((rec + 0x2c) & 0xffff, 2, rng.choice((0, 1, 2, 0xffff, 0x8000))))  # WORD c(A4): 1ca20 / 1ca2e
        for k in (0x5450, 0x5460):
            writes.append(((a5 + k + 4) & 0xffff, 1, rng.choice((0, 1, 2, 3, 5, 0xa, 0xff))))   # 1c9fc: CMP.B 4(A4),D1
            writes.append(((a5 + k + 2) & 0xffff, 1, rng.choice((0, 1, 2, 3, 0x80))))
            writes.append(((a5 + k + 3) & 0xffff, 1, rng.choice((0, 1, 2, 3, 0xff))))
            writes.append(((a5 + k + 0xc) & 0xffff, 2, rng.choice((0, 1, 2, 0xffff, 0x8000))))
        writes.append((0xf001, 1, rng.getrandbits(8)))                                    # 1ca14 / 22894: BTST.B #3 / #2,10f001.l
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
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e, 0x9f, 0x76, 0x78, 0x7c)):
                continue                                        # callback LONG, node links, the pointer fields and the bounded indices stay declared above
            if reg == 5 and disp in (0x5434, 0x5474, 0x5e26, 0x5734, 0x5738):
                continue
            if reg == 4 and disp in (4, 6):
                continue                                        # the bounded table indices of the record
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        writes.append((sp & 0xffff, 4, ret))
        if entry in (0x2269e, 0x22704, 0x2288e, 0x228e6, 0x226c8):
            regs['a7'] = sp - 4                                 # the stacked A0 that the block reads or pops (above it the return LONG)
            writes.append(((sp - 4) & 0xffff, 4, rec + 0x10))
        if entry == 0x224a6:
            regs['a7'] = sp - 8                                 # the stacked A0, WORD 46 and WORD 42 that 224a6 pops
            writes.append(((sp - 8) & 0xffff, 4, rec + 0x10))
            writes.append(((sp - 4) & 0xffff, 2, rng.choice((0, 0x100, 0x8000))))
            writes.append(((sp - 2) & 0xffff, 2, rng.choice((0, 0x140, 0xffff))))
        if hint:
            if hint.get('rec'):
                writes.append(((a6 + 0x8c) & 0xffff, 4, rec + 0x20))   # the record A4 of the hint's 'rec' edits
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
    require(len(STARTS) == 214 and len(STARTS_SET) == 214, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c7_block', ('start is not routed to player c7', hex(s), unit_of(s)))
    # player C10 routes the executed table entry 252b4 since C10 (main decision 4; was: only 252a4 routed, by C7); the C7 runs still stop at 252b4
    # (EXIT_STOPS, ROUTED_LATER)
    for t in TABLE_2529C:
        require(unit_of(t) in (None, 'animation_player_c7_block', 'animation_player_c10_block'), ('table entry routed by another unit', hex(t)))
    require(set(t for t in TABLE_2529C if unit_of(t) is not None) == {0x252a4, 0x252b4}, 'only the executed table entries 252a4 / 252b4 are routed')
    rng = random.Random(0xC7A7)
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
    sys.stderr.write('pc7 spec: %d fixtures (%d natural), visited %d/214, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc7: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc7: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts





def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the CMP.B key of 1c9fc,
    the BTST.B #3 / #2 of 10f001, the WORD c(A4) count of 1ca20 .. 1ca42 (0, 1, ffff, the SUBQ.W borrow), the BYTE compares of 1ca4c / 1ca5c, the input
    bits of D0 and the AND.W #c mask of 1f2fc, the BYTE 15 / 9e / 7e / a5 / a7 / 6e tests of the player states, the CMPI.B #1,D1 of 1f70a, the LONG
    table 1f65e index, the signed BYTE EXT.W of 22480, the CMPI.B #6 / #8 and the WORD 2 / 8 tests of 224a6 .. 224d6, the BYTE table 22642 / LONG
    tables 225f6 / 225e6 / 2284c indices (BYTE 4(A4), BYTE 9e: bits 8..15 of 4 x BYTE 9e under MOVE.B 4(A4),D0), the mirror NEG.B / ADDI.B #80 / NEG.W
    of 226b0 / 2271e / 2290a, the BYTE 4(A4) = 5 / a and BYTE 9e = 1 of 2273c / 2275a, the ANDI.B #3f of 22766, DIVU.W #3 / SWAP / SUBQ.W / MULS.W
    D7,D0 / ADD.B of 22772 (BYTE a1 0..ff, D7.W signed), the BCLR #5 / WORD a(A4) / BYTE 6 / 7(A4) of 2285c .. 228bc, the BYTE 76 BTST #5 / ADDI.B /
    LSR.W / ANDI of 25026 .. 2506e, the BYTE 77 / 88 table index of 25108, the BYTE adds / signed BGT / unsigned BCC of 2519a .. 251ac, the BMI of
    251c2, the unsigned WORD bounds of 25172 / 25184 / 2545e / 25470, the CMPI.W #9 guard and the table displacement (WORD wrap) of 2528c / 25294,
    the ANDI.W / SUBQ.W / ADD.W jitter of 251fc .. 25438), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.
    Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x1c9ec, 0x1ca2e, 0x1ca3a, 0x1ca5c, 0x1f2fc, 0x1f648, 0x22480, 0x22656, 0x2267a, 0x226ca, 0x2269e, 0x2270a, 0x2273c, 0x22772, 0x22894,
                 0x228bc, 0x228e8, 0x25026, 0x2503e, 0x25056, 0x2506e, 0x25108, 0x251fc, 0x25428):
        h += [dict(regs=dict(up))]
    # ---- 1c9ec .. 1ca6a
    if entry == 0x1c9ec:
        for d0, d1, k0, k1 in ((0, 3, 3, 4), (1, 4, 3, 4), (2, 5, 5, 0), (0x10001, 0x12345605, 0, 5), (0xfffe, 0x100, 0, 1), (3, 0xff, 0, 0xff)):
            h.append(dict(regs=dict(d0=d0, d1=d1), a5off=[(0x5454, 1, k0), (0x5464, 1, k1)]))
    if entry in (0x1c9f8, 0x1c9fc):
        for d1, k in ((3, 3), (0x103, 3), (3, 0x83), (0x9abcde80, 0x80), (0, 0)):
            h.append(dict(regs=dict(d1=d1), regrec=dict(a4=0x20), rec=[(0x24, 1, k)]))
    if entry == 0x1ca14:
        h += [dict(writes=[(0xf001, 1, v)], regrec=dict(a4=0x20), rec=[(0x2c, 2, w)]) for v, w in ((0x08, 1), (0xf7, 0), (0xf7, 5), (0, 0xffff))]
    if entry in (0x1ca20, 0x1ca2e):
        h += [dict(regrec=dict(a4=0x20), rec=[(0x2c, 2, w)], regs=dict(d2=0x12345678)) for w in (0, 1, 2, 0xffff, 0xfffe, 0x8000, 0x100)]
    if entry == 0x1ca3a:
        h += [dict(regrec=dict(a4=0x20), regs=dict(d2=v)) for v in (0, 1, 0x10000, 0x12340000, 0xffff, 0x8000)]
    if entry in (0x1ca40, 0x1ca42):
        h += [dict(regrec=dict(a4=0x20), regs=dict(d2=v)) for v in (0x12345678, 0xffff0001)] + mirror
    if entry in (0x1ca4c, 0x1ca5c, 0x1ca6a):
        for b2, b3 in ((0, 0xff), (2, 3), (3, 3), (4, 3), (0x80, 0x7f), (0x7f, 0x80), (0xff, 0xfe), (0, 0), (0xfe, 0xff)):
            h.append(dict(regrec=dict(a4=0x20), rec=[(0x22, 1, b2), (0x23, 1, b3)], regs=dict(d2=0x12345678)))
    # ---- 1f2a4 .. 1f782
    if entry in (0x1f2d8, 0x1f56e, 0x1f6de):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry in (0x1f2e2, 0x1f2f4, 0x1f30a, 0x1f312, 0x1f578, 0x1f58a, 0x1f596, 0x1f59e, 0x1f5a6, 0x1f6e8, 0x1f6fa, 0x1f71a):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 2, 0x10, 0x20, 0x22, 0x40, 0x50, 0x60, 0x12, 0xffffffdd, 0xffffffad, 0x12340000, 0xffffffff)]
    if entry in (0x1f2ea, 0x1f580, 0x1f6f0):
        h += byte(0x9e, (0, 1, 0x80))
    if entry == 0x1f2fc:
        h += [dict(regs=dict(up, d0=v, d1=0x9abc0000)) for v in (0, 4, 8, 0xc, 0x10000, 0xfff3, 0x12340004, 0xfffffff3)]
    if entry in (0x1f2ac, 0x1f546, 0x1f6ae, 0x1f782, 0x1f334, 0x1f5c8):
        h += [dict(a6off=[(0x64, 4, 0x12345678), (0x7a, 2, 0x8001), (0x7e, 1, 0xff), (0xa9, 1, 0xff)])] + mirror
    if entry == 0x1f538:
        h += byte(0x15, (0, 1, 0xfe, 0xff)) + mirror
    if entry in (0x1f5d2, 0x1f5f2):
        for a5, a6, a7 in ((0xff, 0xff, 0), (0x40, 0x10, 1), (0, 0, 0xff), (0xbf, 0xef, 0xfe)):
            h.append(dict(a6off=[(0xa5, 1, a5), (0xa6, 1, a6), (0xa7, 1, a7), (0x88, 1, 0x55), (0xaa, 1, 0x55)]))
        h += mirror
    if entry == 0x1f614:
        h += byte(0x6e, (5, 4, 0x85, 0)) + mirror
    if entry == 0x1f634:
        h += byte(0xa7, (0, 2, 0xfd, 0xff, 1))
    if entry == 0x1f648:
        for k in (0, 1, 4, 0x12, 0x13, 0x40, 0x80, 0xff):
            h.append(dict(rec=[(0x24, 1, k)], regs=dict(d7=0x99aabbcc)))
    if entry == 0x1f70a:
        h += regs('d1', (1, 0x101, 0x12345601, 2, 0, 0x81))
    if entry == 0x1f712:
        h += byte(0x7e, (0, 1, 0x80))
    if entry in (0x1f728, 0x1f732):
        h += byte(0xa5, (0x40, 0x10, 0, 0xff, 0xaf, 0x50))
    # ---- 22480 .. 22500
    if entry == 0x22480:
        for b7a, b7b, w42, w46 in ((0x80, 0x7f, 0x100, 0x100), (0xff, 1, 0, 0), (0x7f, 0x80, 0x8000, 0x7fff), (0, 0, 0x1234, 0xfedc), (0x81, 0xfe, 0x7f, 0x80)):
            h.append(dict(regs=dict(up), a6off=[(0x7a, 1, b7a), (0x7b, 1, b7b), (0x42, 2, w42), (0x46, 2, w46)]))
    if entry in (0x224a6, 0x224b8):
        h += [dict(regs=dict(d0=v)) for v in (6, 8, 0x106, 0x12345608, 7, 0x86)]
    if entry in (0x224c2, 0x224d6):
        h += [dict(regrec=dict(a0=0x10), rec=[(0x10, 2, v)]) for v in (2, 8, 0x102, 0x8002, 0)]
    # ---- 22656 .. 22786
    if entry == 0x22656:
        for k in (0, 1, 0xf, 0x10, 0x11, 0x12, 0x13, 0x80, 0xff):
            h.append(dict(rec=[(0x24, 1, k)], regs=dict(up)))
    if entry == 0x2267a:
        h += [dict(regs=dict(up, d1=v)) for v in (0, 3, 8, 0xc, 0xf, 0x10, 0x12, 0x4003, 0xc003, 0x12340003)]
    if entry == 0x226ca:
        for b9e, k in ((0, 0), (1, 1), (2, 5), (3, 0x12), (0x40, 1), (0x41, 0x10), (0x80, 3), (0xc1, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x9e, 1, b9e)], rec=[(0x24, 1, k)]))
    if entry in (0x2269e, 0x2270a, 0x228e8):
        for b15 in (0, 1, 0xfe, 0xff):
            h.append(dict(a6off=[(0x15, 1, b15)], regrec=dict(a1=0x10),
                          rec=[(0x10, 2, 0x0080), (0x12, 2, 0x8000), (0x14, 2, 0x1234)]))
    if entry in (0x226b0, 0x2271e, 0x2290a):
        h += [dict(regs=dict(d7=d, d0=d, d2=e)) for d, e in ((0, 0), (0x80, 0x8000), (0x7f, 1), (0x12345601, 0x9abcffff), (0xff, 0x7fff), (0x181, 0x10000))]
    if entry == 0x2273c:
        for k in (5, 0xa, 0xff, 4, 0x85, 0):
            h.append(dict(rec=[(0x24, 1, k)], regs=dict(up)))
    if entry in (0x2274e,):
        h += regs('d0', (0xa, 0x10a, 0x8a, 5))
    if entry == 0x2275a:
        h += byte(0x9e, (0, 1, 2, 0x81))
    if entry == 0x22764:
        h += regs('d7', (2, 0xffff, 0x1234ffff, 0x7fff))
    if entry == 0x22766:
        h += [dict(regrec=dict(a0=0x00), rec=[(0x76, 1, v)]) for v in (0, 0x40, 0x3f, 0xc0, 0x80, 1)]
    if entry == 0x22772:
        for a1, d7 in ((0, 2), (1, 2), (2, 3), (3, 4), (4, 4), (5, 3), (0xff, 2), (0x80, 4), (0xfe, 0xffff), (0x7f, 0x8000), (1, 0x12348000), (0, 0xfffe)):
            h.append(dict(regs=dict(up, d7=d7), regrec=dict(a0=0x00), a6off=[(0xa1, 1, a1)], rec=[(0x76, 1, 0x40)]))
    # ---- 2285c .. 22912
    if entry == 0x2285c:
        for a8, w in ((0x20, 0), (0x20, 1), (0, 1), (0xff, 0x8000), (0xdf, 5)):
            h.append(dict(a6off=[(0xa8, 1, a8)], rec=[(0x2a, 2, w)]))
    if entry == 0x22894:
        for b9e, f in ((0, 0), (1, 4), (2, 0xfb), (3, 0xff), (1, 0), (2, 4)):
            h.append(dict(regs=dict(up), a6off=[(0x9e, 1, b9e)], writes=[(0xf001, 1, f)], rec=[(0x26, 1, 1 + b9e % 3)]))
    if entry in (0x228ae, 0x228b8):
        h += [dict(regrec=dict(a4=0x20), rec=[(0x27, 1, v)]) for v in (0, 1, 0x80, 0xff)]
    if entry == 0x228bc:
        h += [dict(regs=dict(up), regrec=dict(a4=0x20, a1=0x10), rec=[(0x26, 1, v)]) for v in (0, 3, 4, 0x83, 0xff)]
    if entry == 0x228cc:
        h += [dict(regs=dict(d0=v), regrec=dict(a1=0x10)) for v in (0, 1, 3, 0x4001, 0x12340002)]
    if entry == 0x22912:
        h += regs('d0', (0x12345680, 0xff, 0)) + mirror
    # ---- 24fb0 .. 2506e
    if entry in (0x24fb0, 0x24fc8, 0x24ffa):
        h += [dict(a6off=[(0x15, 1, v), (0x76, 1, 0x30)]) for v in (0, 0xff, 9, 0xf6)] + mirror
    if entry in (0x25026, 0x2503e, 0x25056, 0x2506e):
        for b in (0x20, 0x1f, 0x3f, 0xe1, 0xff, 0, 0x30, 0xdf, 0xf1, 0xfd):
            h.append(dict(regs=dict(up, d0=0x1234ff00 | b, d1=0x9abc00ff), a6off=[(0x76, 1, b)]))
    if entry in (0x2503a, 0x25054, 0x2506c):
        h += regs('d0', (0x12345ff1, 0xf9, 0xfd, 0xff, 0x8000))
    # ---- 25102 .. 25284
    if entry == 0x25108:
        for b77, b88 in ((0, 0), (0xf, 0), (0x1f, 1), (0xf3, 0x80), (7, 0xff)):
            h.append(dict(regs=dict(up), a6off=[(0x77, 1, b77), (0x88, 1, b88)]))
    if entry == 0x25122:
        h += [dict(regs=dict(d0=v, a0=0x25082)) for v in (0, 4, 0x3c, 0x1234003c)]
    if entry == 0x2512c:
        h += regs('d0', (0, 1, 0x100, 0x12345600, 0x80))
    if entry in (0x25132, 0x2515e):
        h += byte(0x83, (0, 1, 0xff, 0x80))
    if entry in (0x25144, 0x2514e):
        h += byte(0x15, (0x20, 0xdf, 0x80, 0xa0, 0, 0xff))
    if entry in (0x25172, 0x2545e):
        h += word(0x42, (0x13f, 0x140, 0xffff, 0, 0x8000, 0x7fff))
    if entry in (0x25184, 0x25470):
        h += word(0x46, (0xff, 0x100, 0x1ff, 0x200, 0, 0x8100))
    if entry == 0x2519a:
        for b8a, b8b in ((0xd, 0), (0xe, 1), (0xf, 2), (0xff, 3), (0, 0x7f), (5, 0x80), (6, 0x81), (7, 0xff)):
            h.append(dict(a6off=[(0x8a, 1, b8a), (0x8b, 1, b8b), (0x89, 1, 4)]))
    if entry in (0x251ac, 0x251b6):
        h += byte(0x89, (4, 5, 0xff, 0x80, 0))
    if entry == 0x251c2:
        h += byte(0x76, (0x3f, 0x40, 0xbf, 0xc0, 0x7f, 0x80, 0))
    if entry in (0x251e0, 0x25210):
        h += byte(0x61, (0, 1, 2, 3, 0xfc))
    if entry == 0x25240:
        h += byte(0x6f, (0x40, 0x41, 0xc0, 0))
    if entry in (0x251fc, 0x25220, 0x25240, 0x2525a, 0x25428, 0x25438):
        for d0, w in ((0, 0x7fff), (7, 0), (0xf, 0xfffa), (8, 0x8000), (0x12345670, 0x8006), (0xfff0, 0xfff9)):
            h.append(dict(regs=dict(d0=d0), a6off=[(0x2e, 2, w), (0x32, 2, w)]))
    if entry == 0x2526a:
        h += [dict(regs=dict(a0=v)) for v in (0x26112, 0x26178)]
    if entry in (0x25284, 0x25438):
        h += mirror
    if entry == 0x2528c:
        h += regs('d0', (8, 9, 0x10008, 0xffff, 0, 0x12340009))
    if entry == 0x25294:
        h += regs('d0', (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x4002, 0x12340002, 0x8000))
    if entry == 0x253de:
        h += [dict(regrec=dict(a0=0x00), a6off=[(0x84, 4, v)]) for v in (0x6f364, 0x12345678)]
    if entry == 0x25414:
        h += [dict(a6off=[(0x84, 4, v)]) for v in (0x6f364,)]
    return h



# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]



def chain_hint(entry, t, rng):
    if entry == 0x1ca0a:
        # 1ca4c on the record A4: BYTE 3 = ff -> Set; else BYTE 2 < BYTE 3 (unsigned) -> ADDQ.B, Set; else Clear (1ca68)
        b2, b3 = ((0, 0xff), (2, 3), (3, 3), (4, 3), (0x80, 0x7f), (0x7f, 0x80))[t % 6]
        return dict(regrec=dict(a4=0x20), rec=[(0x22, 1, b2), (0x23, 1, b3)])
    if entry in (0x1f32a, 0x1f5be, 0x1f74c, 0x2544e) and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> Set
    if entry in (0x1f640, 0x1f76e):
        # 1cb08: W = WORD (table + 2 x BYTE 9f); 0 -> Clear; else C5 1cb1a: TST.L (LONG 22(A6) + 4 x WORD (table + W)) -> Clear / Set
        table = (0x1b632, 0x1b610, 0x1b6a8, 0x1b68a)[(t // 10) % 4] if entry == 0x1f640 else 0x1b310
        k = (0, 1, 2, 0xc, 0xd, 0xe, 0x10)[(t // 2) % 7] if entry == 0x1f76e else (t // 2) % 5   # 1b310: the WORDs from index c on are not 0
        w = rom_word(table + 2 * k)
        idx = (4 * rom_word(table + w)) & 0xffff if w else 0
        h = dict(a6off=[(0x9f, 1, k), (0x22, 4, SCR)], writes=[((SCR + idx) & 0xffff, 4, (0, 0x12345678)[t % 2])] if idx < 0x400 else [])
        if entry == 0x1f640:
            h['regs'] = dict(a0=table)
        return h
    if entry == 0x22670:
        # 1c9ec: the record 5450 / 5460(A5) by D0.W & 1; CMP.B 4(A4),D1: not equal -> Clear; equal -> 1ca4c (Set / Clear) -> 10f001 bit 3 / WORD c
        d0 = t % 2
        key = (3, 5)[(t // 2) % 2]
        rec = 0x5450 + 0x10 * d0
        return dict(regs=dict(d0=d0, d1=key), a5off=[(rec + 4, 1, (key, key, 0)[(t // 4) % 3]), (rec + 2, 1, (0, 3, 4)[(t // 12) % 3]),
                                                     (rec + 3, 1, (3, 0xff, 3)[(t // 12) % 3]), (rec + 0xc, 2, (0, 1, 0xffff)[(t // 36) % 3])],
                    writes=[(0xf001, 1, (0, 8)[(t // 108) % 2])])
    if entry == 0x226f0:
        # 2986 / 28ae: D0.W a below the WORD 104ca0 -> Set; the Clear side (the 28ae failure) is the C++ caller-X checked error (decision 7): Set only
        return dict(regs=dict(d7=0x24fb0), writes=[(0x4ca0, 2, (0x100, 0x40)[t % 2])])
    if entry == 0x2513a:
        return dict(a6off=[(0x42, 4, (0, 0x1000000, 0xfff00000)[t % 3]), (0x46, 4, (0, 0x800000)[(t // 3) % 2])])
    return None
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
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (decision 7)
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), WORD 78 (the player index), BYTE 15 bits 7 / 5 / 0 (1f2d8 / 25144 / 2269e), BYTE 9e (1f2ea), BYTE 7e
            # (1f712), BYTE 88 / 83 (25108 / 25132), BYTE 76 (25026 / 251c2), WORD 42 / 46 (the bounds), LONG 26 (0: 49fc6 Set), WORD 104ca0 (the 28ae
            # count limit of 2986)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x78, 2, (0, 1)[t % 2]), (0x15, 1, (0, 0x80, 0x20, 0xa1, 1, 0xff)[t % 6]), (0x9e, 1, (0, 1)[(t // 2) % 2]),
                               (0x7e, 1, (0, 1)[(t // 3) % 2]), (0x88, 1, (0, 1)[(t // 4) % 2]), (0x83, 1, (0, 0xff)[(t // 5) % 2]),
                               (0x76, 1, (0x30, 0x20, 0x5f, 0xe1)[(t // 2) % 4]), (0x42, 2, (0x100, 0x140)[(t // 5) % 2]),
                               (0x46, 2, (0x180, 0x200)[(t // 7) % 2])] + ([(0x26, 4, 0)] if t % 5 == 4 else []) +
                              ([(0x84, 4, 0x6f364)] if entry == 0x253f4 else []),   # 253f4: LONG 84 is the script of 49f8c (copied by 253de)
                        writes=[(0x4ca0, 2, (0x100, 0x15, 0x40)[(t // 11) % 3])])
            st = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (decision 7)
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
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (decision 7)
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
    require(count >= 15, ('too few natural node fixtures', count))


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
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (decision 7)
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
    err('odd-pc', U.with_host_writes(st, pc=0x1c9ed), 'unaligned animation machine PC', 0x1c9ed)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the computed jump (contract decision 2): JMP 2529c(PC,D0.W) with a displacement beyond the table (D0.W 9 .. after the two ADD.W, a negative WORD); an
    # unrouted table entry fails at the next dispatch (the paired row stops at that entry)
    for v in (9, 0xa, 0x3fff, 0xffff, 0x8009, 0x12340009, 0x4009):
        err('25294-d0-%x' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x25294), ERROR_JUMP, 0x25294)
    for v in (0, 1, 3, 4, 5, 7, 8, 0x4000):
        err('25294-d0-%x-entry' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x25294), unrouted, 0x2529c + 4 * (v & 0x3fff))
    # D0.W 6 -> the entry 252b4: player C10 since C10 (previous row '25294-d0-6-entry': 'unsupported animation machine PC' at 252b4): 252b4 -> 252ce
    # (BYTE 61(A2) bit 7 clear) -> 252d8 JSR 3af8.l at an odd A7 (25294 and 252b4 / 252ce do not use the stack)
    err('25294-d0-6-then-252d8', U.with_host_writes(st, [((a6 + 0x61) & 0xffff, 1, 0)], regs=dict(d0=6, a2=a6, a7=a7 + 1), pc=0x25294), odd_word, 0x252d8)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('1f2ac-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1f2ac), odd_write, 0x1f2ac, stop=0x1f2d4)
    err('25172-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x25172), odd_word, 0x25172, stop=0x25184)
    err('22480-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x22480), odd_word, 0x22480, stop=0x4ae4a)
    err('22480-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x22480), odd_word, 0x22480, stop=0x4ae4a)
    err('224a6-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x224a6), odd_word, 0x224a6, stop=0x224b8)
    err('22704-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x22704), odd_word, 0x22704, stop=0x22786)
    err('1ca20-odd-a4', U.with_host_writes(st, regs=dict(a4=a6 + 1), pc=0x1ca20), odd_word, 0x1ca20, stop=0x1ca28)
    err('224c2-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x224c2), odd_word, 0x224c2, stop=0x224d6)
    err('2270a-odd-a1', U.with_host_writes(st, regs=dict(a1=a6 + 1), pc=0x2270a), odd_word, 0x2270a, stop=0x22726)
    err('22726-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x22726), odd_write, 0x22726, stop=0x2291a)
    err('253de-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x253de), odd_write, 0x253de, stop=0x49214)
    # failures after executed blocks:
    #   1f2fc (D0.W & c) -> 1fa68 (C8); 1f596 (D0 bit 1 clear) -> 1eb98 (C8) -> 1ebbe (C6); 1f752 (C Set) -> 1f756 (C8)
    #   (1fa68 / 1eb98 are player C8 starts since C8; previous expectation 'unsupported animation machine PC' at 1fa68 / 1eb98: the BSR.W 1cb08 of 1fa68
    #   at an odd A7 fails at 1fa68; 1eb98 (LEA; BRA.W 1ebbe) has no access, the BSR.W 1cab6 of C6 1ebbe at an odd A7 fails at 1ebbe)
    err('1f2fc-then-1fa68', U.with_host_writes(st, regs=dict(d0=4, a7=a7 + 1), pc=0x1f2fc), odd_word, 0x1fa68)
    err('1f596-then-1eb98', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0x1f596), odd_word, 0x1ebbe)
    err('1f71a-then-1eb98', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0x1f71a), odd_word, 0x1ebbe)
    #   RTS at an odd A7 after executed blocks: 1ca5c (BYTE 2 >= BYTE 3) -> 1ca68; 2512c ... ; 25172 bounds -> 25486 needs 2519a, keep the simple RTS blocks
    rec = SCR
    err('1ca4c-then-1ca68', U.with_host_writes(st, [((rec + 2) & 0xffff, 1, 4), ((rec + 3) & 0xffff, 1, 3)], regs=dict(a7=a7 + 1, a4=rec), pc=0x1ca4c),
        odd_word, 0x1ca68)
    err('1c9fc-then-1ca04', U.with_host_writes(st, [((rec + 4) & 0xffff, 1, 3)], regs=dict(a7=a7 + 1, a4=rec, d1=4), pc=0x1c9fc), odd_word, 0x1ca04)
    err('224b8-then-224c0', U.with_host_writes(st, regs=dict(a7=a7 + 1, d0=0), pc=0x224b8), odd_word, 0x224c0)
    err('2274e-then-22758', U.with_host_writes(st, regs=dict(a7=a7 + 1, d0=0), pc=0x2274e), odd_word, 0x22758)
    err('251ac-then-251c0', U.with_host_writes(st, [((a6 + 0x89) & 0xffff, 1, 7)], regs=dict(a7=a7 + 1), pc=0x251ac), odd_word, 0x251c0)
    err('25470-then-25486', U.with_host_writes(st, [((a6 + 0x46) & 0xffff, 2, 0x180)], regs=dict(a7=a7 + 1), pc=0x25470), odd_word, 0x25486)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x22772, 0x2503e, 0x1ca5c, 0x2519a)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
