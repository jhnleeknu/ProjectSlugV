"""V1 fixture spec of the area-C unit C4 (engine/src/animation_machine_player_c4.cpp, 232 block starts; file prefix pc4 / player_c4 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c4-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C4 spec of the
contract): the body of the slot callback 4e94e (4e962 / 4e986 .. 4eb4c: the slot HUD, the number output 371e / 3786 with the DIVU table 377a and
JSR (A1) = 3650 (contract decision 2), 4ee7a, 4eef4, the gauge 4f22c and 4f13c / 4f118 / 4f152 .. 4f2b8 with DIVU / MULU and the video port writes
3c0000), the slot state 4e758 (the Z of 4a974, contract decision 3; 4e538 / 4e564 and the hidden straight-line block 4e57e, contract decision 1),
the hidden straight-line block 4e8e6 after C1 4e8e0 (contract decision 1),
4e4e2, the helpers 1be3a 1bf94 1c052 1c086 4d9a2 4da08, the player state 1eeea / 1ef0e (installed at 1ef08; 1cfbe with the LONG table 1cfce, 1d09e,
1cec2, 1ceb0), the slot-84 state 21d60 / 21d92 (list 21b0a) and the JMP (A1) 21c72 of 21c66 (list 21aee, decision 2).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C3) with declared host edits.
This code runs natively only in the IO observation (P1 / boot-title-start): the 'natural' family takes the frame-start states of the IO native
observation in which the slot nodes 1009a8 / 100a6c hold the C1 callbacks 4e94e / 4e732 (whose frames run into 4e962 / 4e986 / 4e758) and the player
node 100cb8 holds the C4 callback 1ef0e, keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with
the sentinel return LONG, PC = the callback); the 'reinstall' family enters 1ef0e / 1edb0 with a declared slot-84 LONG 21d92 or a declared BYTE.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 11 C consumers and the Z reader 4e77a is entered directly (the seed world with declared edits).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS) and the Z reader 4e77a through 4e770 -> 4a974.  Stop: the consumer's
            successor or the first unrouted PC.
  node      the installed value 1ef0e ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with declared LONGs / BYTEs.
  callee    the helpers and states entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 11 consumers, computed-jump targets outside the ROM-written values
            (decision 2), the Z source of 4e77a outside the 4a974 bytes (decision 3), DIVU by zero (decision 4), odd node / stack / A0 / A4, failures
            after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the
            entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C3
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C3)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc4'
ERROR_PC = 'unsupported animation player c4 PC'
ERROR_CARRY = 'player c4 caller requires known carry'
ERROR_FLAG = 'unsupported animation player c4 flag source'
ERROR_JUMP = 'unsupported animation player c4 jump target'
ERROR_DIV = 'unsupported animation player c4 divide by zero'

RANGES = [(0x371e, 0x377a), (0x3786, 0x37e2), (0x1be3a, 0x1be6a), (0x1bf94, 0x1bfb4), (0x1c052, 0x1c072), (0x1c086, 0x1c0d2), (0x1ceb0, 0x1cec0),
          (0x1cec2, 0x1cef8), (0x1cfbe, 0x1cfce), (0x1d09e, 0x1d0c2), (0x1eeea, 0x1ef4c), (0x1ef6c, 0x1efa4), (0x1efb0, 0x1efd6), (0x21c72, 0x21c74),
          (0x21d60, 0x21d9e), (0x21da0, 0x21dd0), (0x4d9a2, 0x4d9ba), (0x4da08, 0x4da2a), (0x4e4e2, 0x4e536), (0x4e538, 0x4e572), (0x4e57a, 0x4e58a),
          (0x4e758, 0x4e7a2), (0x4e8e6, 0x4e8f0),
          (0x4e962, 0x4e97e), (0x4e986, 0x4eb50), (0x4ee7a, 0x4eea2), (0x4eef4, 0x4ef08), (0x4f118, 0x4f184), (0x4f1ac, 0x4f2ba)]
STARTS = sorted(int(x, 16) for x in (
    '371e 3722 372a 372e 373a 374e 3754 375c 3762 3766 3774 3778 3786 378a 3792 3796 37a2 37b6 37bc 37c4 37ca 37da 37dc 37e0 1be3a 1be46 1be4a 1be50 '
    '1be54 1be5e 1be64 1bf94 1bf9a 1bf9e 1bfa8 1c052 1c058 1c05c 1c05e 1c066 1c06c 1c086 1c092 1c09c 1c0a2 1c0aa 1c0b4 1c0c0 1c0c4 1ceb0 1ceba 1cec2 '
    '1cecc 1ced6 1cee0 1cee4 1cef4 1cfbe 1d09e 1d0a2 1d0a4 1d0b0 1d0b4 1d0bc 1d0c0 1eeea 1eef6 1ef08 1ef0e 1ef20 1ef30 1ef36 1ef3a 1ef44 1ef6c 1ef74 '
    '1ef7c 1ef80 1ef88 1ef90 1ef9a 1efb0 1efb4 1efb8 1efbc 1efc2 1efcc 1efd2 21c72 21d60 21d68 21d6c 21d70 21d74 21d78 21d80 21d92 21d9a 21da0 21da4 '
    '21dac 21db4 21dbc 21dc4 21dc8 21dcc 4d9a2 4d9a8 4d9b0 4d9b4 4da08 4da12 4da16 4da1c 4da20 4e4e2 4e4fe 4e51a 4e538 4e546 4e54e 4e552 4e564 4e57a '
    '4e57e 4e758 4e75e 4e768 4e770 4e77a 4e77e 4e786 4e78a 4e792 4e796 4e79a 4e79e 4e8e6 4e962 4e96c 4e976 4e97a 4e986 4e98e 4e998 4e99c 4e9a4 4e9ac 4e9b0 '
    '4e9bc 4e9c0 4e9ca 4e9d8 4e9ee 4e9f8 4e9fc 4ea04 4ea08 4ea14 4ea18 4ea24 4ea38 4ea40 4ea54 4ea5c 4ea6c 4ea76 4ea8a 4ea92 4ea9c 4eaa0 4eaa4 4eaae '
    '4eab6 4eabe 4eace 4ead2 4eadc 4eae6 4eaf0 4eaf8 4eafc 4eb18 4eb22 4eb2a 4eb44 4eb48 4eb4c 4ee7a 4eef4 4eefe 4ef06 4f118 4f126 4f130 4f13c 4f144 '
    '4f148 4f150 4f152 4f158 4f160 4f166 4f16e 4f174 4f1ac 4f1c2 4f1c4 4f1d8 4f1e0 4f1f2 4f1f4 4f20c 4f210 4f220 4f22c 4f23a 4f240 4f24a 4f24c 4f254 '
    '4f25c 4f25e 4f26c 4f278 4f280 4f28c 4f294 4f2a0 4f2a4 4f2ac 4f2b8').split())
# the 11 C consumers: BCC / BCS 1be50 1bf9a (289e), 1c058 (4da08), 1efb4 (1ed34), 21d6c (21bc6), 21d74 (21baa), 21d9a (215e6), 21dc8 (21be6), 4f144
# (4f118); SCS 4e75e (ca32), 4e96c (1be3a)
CONSUMERS = (0x1be50, 0x1bf9a, 0x1c058, 0x1efb4, 0x21d6c, 0x21d74, 0x21d9a, 0x21dc8, 0x4f144, 0x4e75e, 0x4e96c)
# 1ef9a AND.W (C := 0); 1be64 4f126 ANDI.B #fe,CCR; RTS; 4da1c MOVEQ #0,D7; RTS
CLEAR_SET = (0x1ef9a, 0x1be64, 0x4da1c, 0x4f126)
SET_SET = (0x1be5e, 0x4da20, 0x4f130)   # ORI.B #1,CCR; RTS
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = (0x1efb0,)                   # BSR 1ed34 (carry preserving: the Clear of 1ef9a reaches 1efb4 through 1ed34 / its RTS)
STARTS_SET = set()
Z_READERS = (0x4e77a,)                  # BEQ.W on the Z of 4a974 (contract decision 3): never entered directly by a native run
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# outcomes that need a producer of a later unit: the Set side of 1ed34 (1ed6c -> 1cb08 -> 1cb1a -> 1cb32, C5) for 1efb4; the Set side of 21be6
# (21c06 -> 21c12, C5) for 21dc8.  The declared-C rows of the C++ unit test and the real-ROM differential cover them.
LATER_GATED = {(0x1efb4, 0x1f126), (0x21dc8, 0x21f4c)}
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units (and deferred leaders) that a C4 block reaches by a fall-through, a branch or a call, and the still unrouted later-unit stops of the
# C1..C3 blocks that the C4 runs pass through (pc1 / pc2 / pc3 EXIT_STOPS; the TRAP site 4e69a of C1).  Declared stops of the native runs: a
# straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1ef4c, 0x1efa4, 0x1f2a4, 0x21d9e, 0x21f4c, 0x4e572,
              0x1efd6, 0x1f070, 0x21dd0, 0x2210c, 0x223a0, 0x223d6, 0x4ef08,
              0x1cb1a, 0x1cb38, 0x1cb44, 0x1ce98, 0x1cfde, 0x1d398, 0x1de3c, 0x1e21c, 0x1e8de, 0x1ebbe, 0x1fa68, 0x1fafc, 0x1fc96, 0x1fd50, 0x201bc,
              0x20240, 0x20268, 0x202ac, 0x20544, 0x206cc, 0x21662, 0x21c12, 0x21ca4, 0x21d0e, 0x21f78, 0x21fa6, 0x4838c, 0x4d0cc, 0x4e69a, 0x4e8f8,
              0x4eb58)
UNIT_EXITS = EXIT_STOPS[:13]            # the C4 later-unit stops and deferred leaders
# later-unit stops routed since (player C5: 21f4c 1cb1a 1cb38 1cb44 20240 20268 202ac 20544 21c12 21f78; player C6: 1efa4 4e572 1d398 1ebbe 206cc
# 21662 4838c 4e8f8 4eb58): still declared stops of the C4 runs
ROUTED_LATER = (0x21f4c, 0x1cb1a, 0x1cb38, 0x1cb44, 0x20240, 0x20268, 0x202ac, 0x20544, 0x21c12, 0x21f78,
                0x1efa4, 0x4e572, 0x1d398, 0x1ebbe, 0x206cc, 0x21662, 0x4838c, 0x4e8f8, 0x4eb58)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1be4a, 0x1be50), (0x1bf94, 0x1bf9a), (0x1c052, 0x1c058), (0x1ef9a, 0x1efb4), (0x21d68, 0x21d6c), (0x21d70, 0x21d74), (0x21d92, 0x21d9a),
          (0x21dc4, 0x21dc8), (0x4f13c, 0x4f144), (0x4e758, 0x4e75e), (0x4e962, 0x4e96c), (0x4e770, 0x4e77a))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# computed jumps (contract decision 2): JSR (A1) 3772 / 37d8 (A1 = 3650 from the LEA of 371e / 3786), JMP (A1) 21c72 (a handler of the list 21aee)
JUMP_PCS = (0x3772, 0x37d8, 0x21c72)
JUMP_3650 = (0x3650,)
LIST_21AEE = (0x21602, 0x21d60, 0x21e48, 0x21e3a)
JUMP_ROUTED = (0x3650, 0x21602, 0x21d60)  # routed allowed targets: the native runs continue through them (the unrouted 21e48 / 21e3a stop)
TABLE_ENTRIES = ()
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92)   # routed slot-84 states (C3 and C4 21d92) for the reinstall / callee worlds
# installed values entered as node callbacks; the callee entries (helpers and states entered as subroutines; not the pass block 1efb0: its consumer
# 1efb4 reads the C that 1efb0 brings in, so 1efb0 is entered through its producer 1ef9a (chain))
NODE_ENTRIES = (0x1ef0e,)
CALLEES = (0x371e, 0x3786, 0x1be3a, 0x1bf94, 0x1c052, 0x1c086, 0x1ceb0, 0x1cec2, 0x1cfbe, 0x1d09e, 0x1eeea, 0x21d60, 0x21d92, 0x4d9a2, 0x4da08,
           0x4e4e2, 0x4e538, 0x4e564, 0x4e758, 0x4e8e6, 0x4e962, 0x4e986, 0x4ee7a, 0x4eef4, 0x4f118, 0x4f13c, 0x4f1ac, 0x4f22c)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('P1', 94, f) for f in (217, 218, 219, 220, 260, 311)] + [('P1', 68, f) for f in (433, 434, 435)] +
                [('P1', 106, f) for f in (218, 240)] + [('boot-title-start', None, f) for f in (337, 338, 339, 400)])
NATURAL_CALLBACKS = (0x4e94e, 0x4e732) + NODE_ENTRIES                 # the C1 slot callbacks run into C4 4e962 / 4e986 / 4e758 in the same callback
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node), extra (offset, size, value) writes on the node)
REINSTALL = (('P1', 94, 260, 0x100cb8, 0x1ef0e, ((0x84, 4, 0x21d92),)), ('P1', 94, 260, 0x100cb8, 0x1ef0e, ((0x84, 4, 0x21c66), (0x9c, 1, 2))),
             ('P1', 94, 260, 0x100cb8, 0x1ef0e, ((0x9e, 1, 1),)), ('P1', 94, 260, 0x100cb8, 0x1ef0e, ((0x92, 1, 0xff), (0x6e, 1, 8))),
             ('P1', 94, 260, 0x100cb8, 0x1edb0, ((0x84, 4, 0x21d92),)), ('P1', 68, 450, 0x100cb8, 0x1ef0e, ((0x84, 4, 0x21d92),)),
             ('boot-title-start', None, 360, 0x100cb8, 0x1ef0e, ((0x84, 4, 0x21d92),)),
             ('P1', 94, 260, 0x1009a8, 0x4e94e, ((0x9a, 1, 0),)), ('P1', 94, 260, 0x1009a8, 0x4e94e, ((0xa1, 1, 0xff),)),
             ('P1', 94, 260, 0x1009a8, 0x4e94e, ((0x94, 2, 0x40), (0x92, 2, 0x10))), ('P1', 94, 260, 0x1009a8, 0x4e94e, ((0x99, 1, 0x85),)),
             ('P1', 94, 260, 0x100a6c, 0x4e732, ((0x9a, 1, 0xff),)), ('P1', 68, 450, 0x1009a8, 0x4e94e, ((0x9a, 1, 0), (0x86, 2, 0x1234))))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0xe, 0xf, 0x10, 0x11, 0x18, 0x1d, 0x1e, 0x1f, 0x20, 0x40, 0x77, 0x7f, 0x80, 0x81, 0xbf, 0xfe, 0xff)
VW = (0, 1, 2, 4, 5, 0xc, 0xd, 0xe, 0xf, 0x10, 0x1c, 0x20, 0x40, 0x7f, 0x80, 0xff, 0x100, 0x400, 0x800, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffe, 0xffff)
VL = (0, 1, 2, 0x1f, 0x20, 0x8000, 0xffff, 0x10000, 0x7fffffff, 0x80000000, 0xffea0000, 0xfff00000, 0xffffffe0, 0xffffffff, 0x12345678)
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
BUNDLED = ()                            # no flag-sharing Bcc pair in C4


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (1ceba falls to the C2 RTS 1cec0, 4e97a to C1 4e97e, 1eef6 to 1ef08 and 1ef08 to the installed 1ef0e)."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (none in C4) would use pcs[n - 1]."""
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
    jumps 3772 / 37d8 / 21c72 that is neither a block start of this unit nor a routed allowed target (3650, C3 21602; an unrouted listed target such as
    21e48: the C++ dispatch of it is the checked PC error), or at the first unrouted PC that is not the straight-line successor of the previous
    instruction (a PC inside a block of another executor is not a block entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24} | set(EXIT_STOPS) | set(TRAPS)

    def outside(pc, prev, size):
        if pc in ex:
            return True
        if prev in JUMP_PCS and pc not in STARTS_SET and pc not in JUMP_ROUTED:
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


NUMBER_LOOP = set(range(0x371e, 0x37e2, 2))     # the number output loops 371e / 3786 (A1 = 3650, D4.W the digit count)


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
        """A world for `entry`.  The values a ROM writer bounds are kept in their ROM range (contract decision 2): A1 = 3650 for a direct entry into the
        number loops 371e / 3786 (the LEA 3650(PC),A1 of 371e / 3786), A1 a handler of the list 21aee for a direct 21c72 entry, LONG 84(A6) a routed
        slot-84 value of the C3 list (the C3 JSR (A4) 201a6 that 1efd2 reaches), BYTE a0(A6) 0..8 / a9(A6) 0..5 (C3 2031c / 206a4); LONG 5434(A5) = 0
        (C2 decision 2).  The loop counters D4 (371e / 3786), D2 (4f1d8 / 4f210), D6 / D7 (4f28c / 4f2a4) and BYTE 9e (the LONG table 1cfce) are small
        in most worlds; BYTE 10fd82 = 0 keeps 4a974 off the BIOS call c00450 (not mapped natively)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x22, 0xa2, 0x400, 0xffff, 0x12345678, 0x10000))   # input summary bits
        if rng.random() < 0.85:
            regs['d4'] = (regs['d4'] & 0xffff0000) | rng.choice((1, 1, 2, 2, 3, 4, 5, 6, 7))
        if rng.random() < 0.7:
            regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 5, 9, 0xa, 0x10, 0x100, 0x2710))
        for k in ('d6', 'd7'):
            if rng.random() < 0.6:
                regs[k] = (regs[k] & 0xffff0000) | rng.choice((0, 1, 2, 3, 7, 0xd, 0xe, 0xf, 0x10, 0x28, 0x2800, 0xffff))
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = 0x3650 if entry in NUMBER_LOOP else (rng.choice(LIST_21AEE) if entry == 0x21c72 else self.pointer())
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, self.pointer()))    # LONG 8c(A6) (A4 of C2 1cd98 / C3 202b6)
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of C2 1cad4)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(),))))   # LONG 3e(A6) (C2 1a9fe..1aa20)
        writes.append(((a6 + 0x78) & 0xffff, 4, self.pointer()))    # LONG 78(A6): the player node of the slot node (4ea18 A0 of 1bf94)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): index of the C3 jump table 2031c
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): index of the C3 LONG table 206d4
        if rng.random() < 0.8:
            writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                    # BYTE 9e(A6): index of the LONG table 1cfce (4 LONGs)
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
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e)):
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
    require(len(STARTS) == 232 and len(STARTS_SET) == 232, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    require(unit_of(0x3650) == 'animation_card_menu_open_block' and unit_of(0x21602) == 'animation_player_c3_block', 'routed computed-jump targets')
    for t in LIST_21AEE:
        require(unit_of(t) in (None, 'animation_player_c3_block', 'animation_player_c4_block'), ('computed-jump target routed by another unit', hex(t)))
    require(set(t for t in LIST_21AEE if unit_of(t) is not None) | {0x3650} == set(JUMP_ROUTED), 'JUMP_ROUTED = the routed allowed targets')
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c4_block', ('start is not routed to player c4', hex(s), unit_of(s)))
    rng = random.Random(0xC4A4)
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
    sys.stderr.write('pc4 spec: %d fixtures (%d natural), visited %d/232, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc4: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc4: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (CMPI.W #1 / #6 of the
    digit loops, the DIVU quotient / remainder / overflow of 373a / 37a2 / 4f130 / 4f16e (the sign-extended table index of 377a reaches the ROM bytes
    before the table: D5.W = ffc9 -> 377a - 6e = 370c), the BYTE table 370c index, the CMP.B ties of 4e75e / 4e96c / 4e986 / 4eae6 / 4eb18 / 4f24c,
    CMP.W 86(A6),D7, CMPI.B #10,D7 (unsigned), CMP.W D6,D7 (unsigned), the BPL / BMI / BGT of 4e9d8 / 4ea8a / 4f1ac / 4f1d8 / 21d60, the BTST / BSET /
    BCLR / BCHG bits of the node BYTEs and of D0, the ADDQ.B carry / SCS / OR.B of 1ef0e, LSR.W 88, SUB.L / ADD.L 64, the ASR.W #8 / ADD.B of 4f1f4,
    the ADDI.L #200000 / ADD.L carries of the port loops, the LSL.W #2 table indices of 4ea24 / 4eafc (D.W = 2000 -> 8000: a negative index into the
    ROM before the table), the MULU.W #2800), the upper register bits of the WORD / BYTE operations, the stacked WORD / LONG of 1c092 / 4eb18 / 37da,
    the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x372a, 0x3792, 0x3754, 0x37bc, 0x3762, 0x1be3a, 0x1bf9e, 0x1bfa8, 0x1c05e, 0x1c066, 0x1c06c, 0x1c086, 0x1c0aa, 0x1c0b4, 0x1c0c4,
                 0x1cee0, 0x1cee4, 0x1cef4, 0x1cfbe, 0x1d09e, 0x1ef0e, 0x1ef9a, 0x4d9a2, 0x4d9b4, 0x4da08, 0x4da1c, 0x4da20, 0x4e4e2, 0x4e4fe, 0x4e51a,
                 0x4e538, 0x4e564, 0x4e546, 0x4e54e, 0x4e552, 0x4e57a, 0x4e57e, 0x4e9d8, 0x4ea04, 0x4ea08, 0x4ea18, 0x4ea40, 0x4ea54, 0x4ea5c, 0x4ea76,
                 0x4ea9c, 0x4ead2, 0x4eae6, 0x4eafc, 0x4eb2a, 0x4f118, 0x4f126, 0x4f13c, 0x4f158, 0x4f166, 0x4f1ac, 0x4f1c2, 0x4f1c4, 0x4f20c, 0x4f220,
                 0x4f24a, 0x4f26c, 0x4f278, 0x4f280, 0x4f2a0, 0x4e770, 0x4e962, 0x4e9c0, 0x4e9ca, 0x4eadc, 0x4eef4, 0x4ea6c):
        h += [dict(regs=dict(up))]
    # ---- the number output loops 371e / 3786 (A1 = 3650 declared by World.make)
    if entry in (0x3722, 0x378a):
        h += regs('d4', (1, 2, 0x10001, 0x10005, 0xffff, 0x10000, 0x101))
    if entry in (0x372e, 0x3796):
        h += [dict(regs=dict(up, d4=v)) for v in (5, 6, 7, 0xffff, 0x10005, 0x8000, 1)]
    if entry in (0x373a, 0x37a2):
        for d5, d7, d2 in ((1, 9, 0), (1, 0xffff, 0), (2, 10, 0), (3, 99, 0), (3, 100, 0), (4, 999, 0), (4, 1000, 0x12340000), (5, 12345, 0), (5, 65535, 0),
                           (1, 5, 0x50000), (2, 0x1234, 0xa0000), (0xffc9, 0x3031, 0), (0x10003, 777, 0), (0x8001, 7, 0)):
            h.append(dict(regs=dict(up, d5=(up['d5'] & 0xffff0000) | (d5 & 0xffff) if d5 < 0x10000 else d5, d7=(up['d7'] & 0xffff0000) | d7, d2=d2 | 0x5)))
    if entry in (0x374e, 0x37b6):
        h += regs('d2', (0, 1, 0x10000, 9, 0xffff0000, 0x100))
    if entry in (0x375c, 0x37c4):
        h += regs('d3', (0, 1, 0xff, 0x100, 0x80))
    if entry in (0x3766, 0x37ca):
        h += [dict(regs=dict(up, a1=0x3650, d2=(up['d2'] & 0xffff0000) | v)) for v in (0, 1, 9, 0xa, 0xf, 0x10, 0xfffe, 0xff00)]
    if entry in (0x3774, 0x37dc):
        h += regs('d4', (1, 2, 0x10001, 0, 0x8000, 0x101))
    if entry == 0x37da:
        h += [dict(stack=[(0, 4, v), (4, 4, SENTINEL)]) for v in (0x10dc00, 0x4e3ce, 0x80000001)]
    # ---- 1be3a .. 1c0c4
    if entry == 0x1be3a:
        h += regs('d0', (0, 1, 2, 3, 0x12340001, 0xfffe))
    if entry == 0x1be54:
        h += [dict(a0off=[(0xa8, 1, v)]) for v in (0, 0x10, 0xef, 0xff)]
    if entry == 0x1bfa8:
        h += [dict(regs=dict(up), a0off=[(0x9e, 1, b), (0x76, 2, w)]) for b, w in ((0, 0), (0x80, 0x8000), (0xff, 0xffff), (5, 1))]
    if entry == 0x1c05e:
        h += regs('d0', (0, 1, 2, 0x10001, 0xfffe))
    if entry in (0x1c066, 0x1c06c):
        h += [dict(regs=dict(up), a5off=[(0x545c, 2, 0x8001), (0x546c, 2, 0x7ffe)])]
    if entry == 0x1c086:
        h += regs('d0', (0, 1, 2, 0x10001, 0xfffe))
    if entry == 0x1c092:
        h += [dict(regs=dict(up, d0=d0), stack=[(0, 2, w), (2, 4, SENTINEL)]) for d0, w in ((0, 0), (1, 1), (0x100, 0x8000), (0xff, 0xffff), (0x12340000, 1))]
    if entry == 0x1c0a2:
        h += regs('d7', (0, 1, 2, 0x101, 0xff01))
    if entry == 0x1c0aa:
        h += [dict(regs=dict(up, d1=0x9abcdef0, d2=0x11223380))]
    if entry == 0x1c0b4:
        h += regs('d0', (0, 1, 2, 0x10001, 0xfffe))
    if entry == 0x1c0c4:
        h += [dict(regs=dict(up), a4off=[(6, 1, a), (7, 1, b)]) for a, b in ((0, 0xff), (0x80, 1), (0x7f, 0x80))]
    # ---- 1ceb0 .. 1d0c0
    if entry == 0x1ceb0:
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x1ceba:
        h += byte(0xa7, (0, 8, 0xf7, 0xff)) + mirror
    if entry == 0x1cec2:
        h += byte(0xaa, (0, 1, 2, 0x80))
    if entry == 0x1cecc:
        h += byte(0xa7, (0, 8, 0xf7, 0xff))
    if entry == 0x1ced6:
        h += byte(0xaa, (1, 0, 2, 0x81))
    if entry == 0x1cee4:
        h += [dict(regs=dict(up), a6off=[(0x15, 1, a), (0xa7, 1, b)]) for a, b in ((0, 0xff), (1, 8), (0xff, 0), (0xfe, 0xf7))] + mirror
    if entry == 0x1cfbe:
        h += [dict(regs=dict(up), a6off=[(0x9e, 1, v)]) for v in (0, 1, 2, 3)]
    if entry == 0x1d0a2:
        h += [dict(a0off=[(0, 4, v)]) for v in (0x12345678, 0x80000000, 1)]
    if entry == 0x1d0a4:
        h += [dict(regs=dict(d0=d0), a6off=[(0x64, 4, 0x12345678)]) for d0 in (0, 4, 8, 0xc, 0xfffffff3, 0x10000)] + mirror
    if entry in (0x1d0b0, 0x1d0bc):
        h += [dict(regs=dict(d1=d1, d0=0xc), a6off=[(0x64, 4, v)]) for d1, v in ((1, 0), (0x80000000, 0x7fffffff), (0xffffffff, 0xffffffff), (5, 3))]
    if entry == 0x1d0b4:
        h += regs('d0', (0, 8, 0xfff7, 0x12345608))
    # ---- 1eeea .. 1efd2
    if entry in (0x1eeea, 0x1eef6, 0x1ef08):
        h += mirror
    if entry == 0x1ef0e:
        for b92, w88, b9e in ((0, 0, 0), (0x7f, 1, 1), (0xfe, 0x8000, 2), (0xff, 0xffff, 3), (0xff, 2, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x92, 1, b92), (0x88, 2, w88), (0x9e, 1, b9e)]))
        h += mirror
    if entry == 0x1ef20:
        h += [dict(a6off=[(0x6e, 1, v)], a0off=[(0x1c, 2, 0x8001), (0x1e, 2, 0x7ffe)]) for v in (8, 7, 9, 0x88)]
    if entry == 0x1ef30:
        h += [dict(a0off=[(0x1e, 2, v)]) for v in (0, 0x8000, 0xffff)] + mirror
    if entry == 0x1ef3a:
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry == 0x1ef44:
        h += regs('d0', (0, 0x20, 0xffdf, 0x12345620))
    if entry == 0x1ef6c:
        h += regs('d0', (0, 2, 0xfffd, 0x12340002))
    if entry == 0x1ef74:
        h += regs('d0', (0, 0x80, 0xff7f, 0x12340080))
    if entry in (0x1ef80, 0x1ef88):
        h += regs('d1', (0, 1, 2, 3, 0x101, 0x102, 0xff))
    if entry == 0x1ef90:
        h += byte(0xa7, (0, 8, 0xf7, 0xff))
    if entry == 0x1ef9a:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 4, 8, 0xc, 0xfff3, 0xc0000, 0x12345673)]
    if entry == 0x1efc2:
        h += word(0x1e, (0, 0x8834, 0xffff))
    # ---- 21d60 .. 21dcc
    if entry == 0x21d60:
        h += byte(0x9d, (0, 1, 0x7f, 0x80, 0xff))
    if entry in (0x21d78, 0x21d80):
        h += byte(0xa3, (0xff,)) + mirror
    if entry == 0x21d92:
        h += byte(0x9c, (0, 1, 2, 3, 4, 0x80))
    if entry in (0x21da4, 0x21dac, 0x21db4, 0x21dbc):
        h += regs('d0', (0, 1, 2, 0x10, 0x40, 0xffae, 0x12345600, 0x53))
    # ---- 4d9a2 / 4da08
    if entry in (0x4d9a2, 0x4da08):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x100, 0xff, 0x12345600)]
    if entry == 0x4d9b4:
        h += [dict(regs=dict(up), a4off=[(0x29, 1, v)]) for v in (0, 0x80, 0xff)]
    if entry == 0x4da16:
        h += [dict(a4off=[(0, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x4da20:
        h += [dict(regs=dict(up), a4off=[(0x20, 2, v)]) for v in (0, 0x8001, 0xffff)]
    # ---- 4e4e2 .. 4e57e
    if entry in (0x4e4e2, 0x4e4fe, 0x4e51a):
        h += [dict(regs=dict(up), a6off=[(0x7c, 2, 0x8001), (0x82, 2, 0x7ffe), (0x80, 2, 0xffff)])] + mirror
    if entry in (0x4e538, 0x4e564):
        h += [dict(regs=dict(up), a6off=[(0x76, 2, w), (0x7c, 2, 0xffe0)]) for w in (0, 1, 0x8000, 0x100)]
    if entry in (0x4e546, 0x4e54e, 0x4e57a):
        h += regs('d0', (0xffe0, 0xff80, 0x12340000, 0x1234ffff))
    # ---- 4e758 .. 4e79e
    if entry == 0x4e768:
        h += regs('d0', (0, 0xff, 0x12345600, 0x100)) + mirror
    if entry == 0x4e770:
        h += [dict(regs=dict(up), a6off=[(0x76, 2, w)], writes=[(0xfd82, 1, 0), (0x0003, 1, b)]) for w, b in ((0, 0), (1, 0), (1, 1), (0x8001, 1))]
    if entry in (0x4e78a, 0x4e99c, 0x4ea38):
        h += byte(0xa1, (0, 1, 0x80))
    # ---- 4e962 .. 4eb4c
    if entry == 0x4e976:
        h += mirror
    if entry == 0x4e97a:
        h += regs('d0', (0, 0xff, 0x12345680)) + mirror
    if entry == 0x4e986:
        h += [dict(regs=dict(d0=d0), a6off=[(0x9a, 1, b)]) for d0, b in ((0, 0), (0xff, 0xff), (0x12345601, 1), (1, 0), (0, 0xff), (0x100, 0))]
    if entry in (0x4e9b0, 0x4ea40, 0x4f22c):
        h += word(0x76, (0, 1, 0x8000))
    if entry == 0x4e9d8:
        h += [dict(regs=dict(up), a6off=[(0x99, 1, v), (0x82, 2, 0xffe0)]) for v in (0, 0xf, 0x10, 0x7f, 0x80, 0xff)]
    if entry == 0x4e9fc:
        h += regs('d7', (0xf, 0x10, 0x11, 0x110, 0xf00, 0xff))
    if entry == 0x4ea04:
        h += regs('d0', (0x10, 0x20, 0, 0x12340000))
    if entry == 0x4ea54:
        h += regs('d0', (0x1234fff0, 0xffe0))
    if entry == 0x4ea24:
        h += [dict(regs=dict(up, d2=v)) for v in (0, 1, 2, 3, 0xffff, 0x4000, 0x2000, 0x12340001)]
    if entry == 0x4ea5c:
        h += [dict(regs=dict(up), a0off=[(0, 1, v)]) for v in (0x0f, 0xf0, 0xff, 0x5a)]
    if entry == 0x4ea76:
        for d7, w in ((0x1234, 0x1234), (0x56781234, 0x1234), (0x1234, 0x1235), (0xffff, 0xffff), (0, 0x8000)):
            h.append(dict(regs=dict(up, d7=d7), a6off=[(0x86, 2, w)]))
    if entry == 0x4ea8a:
        h += regs('d7', (0, 0x7fff, 0x8000, 0xffff, 0x12348000)) + mirror
    if entry in (0x4ea92, 0x4eaa4):
        h += byte(0x9d, (0, 1, 0xfe, 0xff)) + mirror
    if entry in (0x4eaae, 0x4eaf0, 0x4eb22, 0x4f254):
        h += byte(0x9a, (0, 1, 0x80))
    if entry == 0x4eab6:
        h += regs('d7', (0xffff, 0xfffe, 0x1ffff, 0))
    if entry == 0x4eabe:
        h += byte(0x9d, (0, 1, 0xff)) + mirror
    if entry == 0x4eae6:
        for d1, b in ((5, 5), (0x1234ff05, 5), (5, 6), (0x80, 0x80), (0, 0xff)):
            h.append(dict(regs=dict(up, d1=d1), a6off=[(0x9f, 1, b)]))
    if entry == 0x4eafc:
        h += [dict(regs=dict(up, d1=(up['d1'] & 0xffff0000) | v)) for v in (0, 1, 2, 3, 4, 0x10, 0xffff, 0x4000, 0x2000)] + mirror
    if entry == 0x4eb18:
        h += [dict(regs=dict(up), stack=[(0, 2, w), (2, 4, SENTINEL)], a6off=[(0x9e, 1, b)]) for w, b in ((5, 5), (0x1205, 5), (5, 6), (0xff, 0xff))]
    if entry == 0x4eb2a:
        h += [dict(regs=dict(up, d7=v)) for v in (0x12345680, 0)] + mirror
    if entry == 0x4ee7a:
        h += mirror
    if entry == 0x4eefe:
        h += regs('d0', (0, 1, 0x100, 0xff))
    # ---- 4f118 .. 4f2b8
    if entry == 0x4f118:
        h += [dict(regs=dict(up), a6off=[(0x94, 2, a), (0x92, 2, b)]) for a, b in ((0, 1), (1, 1), (0x8000, 2), (0xffff, 0xffff))]
    if entry == 0x4f130:
        for d0, w92 in ((0x1234, 1), (0xffff, 0xffff), (5, 0x10), (0xffff, 1), (0x100, 3), (0x12345678, 1), (0x12345678, 0x1235), (0x10000, 1)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x92, 2, w92)]))
    if entry == 0x4f148:
        h += word(0x8c, (0, 1, 0x8000))
    if entry == 0x4f152:
        h += regs('d6', (0, 1, 0x10000, 0xffff, 0x100))
    if entry == 0x4f160:
        h += [dict(regs=dict(up, d7=a, d6=b)) for a, b in ((5, 5), (4, 5), (6, 5), (0xffff, 1), (0x1234ffff, 0xffff), (0x10004, 5), (0x8000, 0x7fff))]
    if entry == 0x4f16e:
        for d7, d6 in ((1, 2), (0x27, 0x28), (0xffff, 1), (0xffff, 0x2800), (0x1234, 0x1235), (0x8000, 0x8001), (0x56780001, 0x28), (2, 1), (7, 3)):
            h.append(dict(regs=dict(up, d7=d7, d6=d6)))
    if entry == 0x4f174:
        h += [dict(regs=dict(up, d7=v)) for v in (0, 0x8000, 0x12342800)] + mirror
    if entry == 0x4f1ac:
        for w8c in (0, 0x7ff, 0x800, 0x1000, 0x27ff, 0x2800, 0x7fff, 0x8000, 0xffff):
            h.append(dict(regs=dict(up), a6off=[(0x8c, 2, w8c), (0x80, 2, 0x1234), (0x8e, 2, 0x5678)]))
    if entry == 0x4f1c4:
        h += regs('d0', (0x84408440, 0xfff08440, 0xffe08449, 0))
    if entry == 0x4f1d8:
        h += regs('d1', (0x800, 0x7ff, 0, 0x8800, 0x10800, 0x8000))
    if entry in (0x4f1e0, 0x4f210):
        h += [dict(regs=dict(up, d2=d2, d0=d0)) for d2, d0 in ((1, 0xffe00049), (2, 0x84408449), (5, 0x12345641), (0x10001, 0), (0x101, 0x41))]
    if entry == 0x4f1f4:
        h += [dict(regs=dict(up, d1=d1, d2=d2, d0=0x844089c0)) for d1, d2 in ((0xff00, 1), (0xf800, 2), (0x87ff, 5), (0xffff, 3), (0x7f00, 1))]
    if entry == 0x4f240:
        h += [dict(regs=dict(up), a0off=[(0, 2, v)]) for v in (0, 0xd, 0xe, 0xf, 0xffff, 0x8000)]
    if entry == 0x4f24c:
        h += [dict(regs=dict(up, d7=a), a6off=[(0xa0, 1, b)]) for a, b in ((5, 5), (5, 6), (0x105, 5), (0xe, 0xe), (0, 0))]
    if entry == 0x4f25e:
        h += [dict(regs=dict(up, d7=a, d6=0xe), a6off=[(0x76, 2, w)]) for a, w in ((0, 0), (5, 1), (0xe, 0), (0x1234000e, 0x8000))] + mirror
    if entry in (0x4f28c, 0x4f2a4):
        h += [dict(regs=dict(up, d7=v, d6=v)) for v in (0, 1, 3, 0x10000)] + [dict(regs=dict(up, d7=0x100, d6=0x100))]
    if entry in (0x4f294, 0x4f2ac):
        h += [dict(regs=dict(up, d7=v, d6=v, d0=0xffff0310, d1=d1)) for v, d1 in ((1, 0x200000), (2, 0xffe00000), (0x10001, 0x200000))]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def chain_hint(entry, t, rng):
    if entry in (0x1be4a, 0x1bf94):
        # 289e: CMPI.L #270e,(A0) (C Clear when the node at A0 holds the callback 270e, Set otherwise); 1be54 BTST #4,a8(A0)
        return dict(a0off=[(0, 4, (0x270e, 0x1ef0e, 0x270e, 0x2b99c)[t % 4]), (0xa8, 1, (0, 0x10)[(t // 4) % 2])])
    if entry == 0x1c052:
        w = (0, 1)[t % 2]
        return dict(regs=dict(d0=w), a5off=[(0x5cba + 0x2c * w, 2, (0, 1, 0x8000)[(t // 2) % 3])])                 # 4da08: WORD (A4) 0 -> Clear
    if entry == 0x1ef9a:
        return dict(regs=dict(d0=(4, 8, 0xc, 0x14, 0x1c)[t % 5]), a6off=[(0xa7, 1, (0, 1, 3)[(t // 5) % 3]), (0x6e, 1, (5, 4)[(t // 15) % 2])])
    if entry == 0x21d68:
        return dict(a6off=[(0x9e, 1, (1, 0, 1)[t % 3]), (0xa7, 1, (0x10, 0x10, 0)[t % 3])])
    if entry == 0x21d70:
        return dict(a6off=[(0x9f, 1, (0, 0, 1)[t % 3]), (0x76, 2, (0, 1)[(t // 3) % 2]), (0xa1, 1, (0xc, 0xa, 0)[t % 3])])
    if entry == 0x21d92:
        return dict(a6off=[(0x9c, 1, (0, 1, 2, 3, 4, 0xb)[t % 6])])                    # the ROM list 21b0a: (21602,0) (21c22,1) (21e48,3) (21e3a,4)
    if entry == 0x21dc4:
        return dict(a6off=[(0xa3, 1, (0, 2, 3, 0xff)[t % 4])])
    if entry == 0x4f13c:
        return dict(a6off=[(0x94, 2, (0, 0x40, 0x2800, 1)[t % 4]), (0x92, 2, (1, 0x10, 0x100, 3)[(t // 4) % 4])])
    if entry == 0x4e758:
        return dict(writes=[(0x0964, 1, (0, 0xa9, 0xaa, 0xab, 0xff)[t % 5])], a6off=[(0x9a, 1, (0, 0xff)[(t // 5) % 2])])   # ca32: CMPI.B #aa,-769c(A5)
    if entry == 0x4e962:
        return dict(a6off=[(0x76, 2, (0, 1)[t % 2]), (0xa1, 1, (0, 0xff)[(t // 2) % 2])])
    if entry == 0x4e770:
        return dict(writes=[(0xfd82, 1, 0), (0x0003, 1, (0, 1)[t % 2]), (0x0004, 1, (0, 1, 0x80)[(t // 2) % 3]), (0x0005, 1, (0, 1, 0x80)[(t // 6) % 3])],
                    a6off=[(0x76, 2, (0, 1)[(t // 18) % 2])])
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
            # BYTE 15 bit 7 (on ground [I]), BYTE 9f / 9e (the LONG table 1cfce) / 9c / a7 / a8 / 6e / 7e / 92, WORD 88, BYTE 1d(A6) < 4, the slot LONG
            # 84 (21d92 and the C3 states), WORD 104ca0 (28ae count limit), BYTE 5683 (4836e)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80)[t % 2]), (0x9f, 1, (0, 1, 2)[(t // 2) % 3]), (0xa8, 1, (0, 0x80)[(t // 3) % 2]),
                               (0xa7, 1, (0, 1, 0x20, 8)[(t // 2) % 4]), (0x6e, 1, (0, 7, 8)[(t // 5) % 3]), (0x9e, 1, (0, 1, 2, 3)[(t // 4) % 4]),
                               (0x7e, 1, (0, 1)[(t // 3) % 2]), (0x26, 4, 0), (0x9c, 1, (0, 1, 2)[(t // 7) % 3]), (0x92, 1, (0, 0xff, 0x40)[t % 3]),
                               (0x88, 2, (0x3f, 0, 0x8001)[(t // 3) % 3]), (0x84, 4, (0x21d92, 0x21c66, 0x21602)[(t // 6) % 3]), (0xaa, 1, (0, 1, 2)[t % 3])],
                        a5off=[(0x5683, 1, (0, 4)[(t // 3) % 2])],
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
    err('odd-pc', U.with_host_writes(st, pc=0x4e987), 'unaligned animation machine PC', 0x4e987)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the computed jumps (contract decision 2): JSR (A1) 3772 / 37d8 with A1 other than 3650, JMP (A1) 21c72 with A1 outside the list 21aee; a listed
    # target that is not routed yet fails at the next dispatch (the paired row stops at that target)
    for v in (0x3670, 0x3651, 0, 0x1003650, 0x36ba):
        err('3766-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v, d2=1), pc=0x3766), ERROR_JUMP, 0x3766)
        err('37ca-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v, d2=1), pc=0x37ca), ERROR_JUMP, 0x37ca)
    for v in (0x21622, 0x21c22, 0x1021602, 0, 0x21d61, 0x21610):
        err('21c72-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21c72), ERROR_JUMP, 0x21c72)
    for v in (0x21e48, 0x21e3a):
        err('21c72-a1-listed-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21c72), unrouted, v)
    #   C3 21c66 (BYTE 9c = 3) -> 215e6 on the ROM list 21aee -> Set, A1 = 21e48 -> 21c6e -> 21c72 JMP (A1): listed, unrouted
    err('21c66-then-21e48', U.with_host_writes(st, [((a6 + 0x9c) & 0xffff, 1, 3)], pc=0x21c66), unrouted, 0x21e48)
    #   3774 (D4.W = 1 -> 0) -> RTS 3778 at an odd A7
    err('3774-then-3778', U.with_host_writes(st, regs=dict(d4=1, d7=7, a7=a7 + 1), pc=0x3774), odd_word, 0x3778)
    # the Z source of 4e77a (contract decision 3): A0 outside the four 4a974 bytes
    for v in (0x10fdb2, 0x100006, 0x1ffdb0, 0, 0x100003):
        err('4e77a-a0-%x' % v, U.with_host_writes(st, regs=dict(a0=v), pc=0x4e77a), ERROR_FLAG, 0x4e77a)
    # DIVU by zero (contract decision 4): the zero-divide exception is not modelled
    for v in (0, 0x10000):
        err('4f16e-d6-%x' % v, U.with_host_writes(st, regs=dict(d6=v, d7=5), pc=0x4f16e), ERROR_DIV, 0x4f16e)
    err('4f130-92-0', U.with_host_writes(st, [((a6 + 0x92) & 0xffff, 2, 0)], regs=dict(d0=5), pc=0x4f130), ERROR_DIV, 0x4f130)
    err('4f13c-then-4f130', U.with_host_writes(st, [((a6 + 0x94) & 0xffff, 2, 5), ((a6 + 0x92) & 0xffff, 2, 0)], pc=0x4f13c), ERROR_DIV, 0x4f130)
    err('373a-d5-0', U.with_host_writes(st, regs=dict(d5=0, d7=5), pc=0x373a), ERROR_DIV, 0x373a)
    err('37a2-d5-0', U.with_host_writes(st, regs=dict(d5=0x10000, d7=5), pc=0x37a2), ERROR_DIV, 0x37a2)
    err('371e-d4-0', U.with_host_writes(st, regs=dict(d4=0, d7=5), pc=0x371e), ERROR_DIV, 0x373a)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('1ef0e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1ef0e), odd_word, 0x1ef0e, stop=0x1ef20)
    err('1ef08-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1ef08), odd_write, 0x1ef08, stop=0x1ef0e)
    err('1c086-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1c086), odd_word, 0x1c086, stop=0x4d7a6)
    err('4eae6-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x4eae6), odd_word, 0x4eae6, stop=0x4eafc)
    err('37ca-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1, a1=0x3650), pc=0x37ca), odd_word, 0x37ca, stop=0x3650)
    err('1d0a2-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x1d0a2), odd_word, 0x1d0a2, stop=0x1d0a4)
    err('4da16-odd-a4', U.with_host_writes(st, regs=dict(a4=a6 + 1), pc=0x4da16), odd_word, 0x4da16, stop=0x4da1c)
    err('4f240-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x4f240), odd_word, 0x4f240, stop=0x4f24c)
    err('1bfa8-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x1bfa8), odd_word, 0x1bfa8)
    # failures after executed blocks:
    #   1cec2 (BYTE aa = 0) -> 1cef4 RTS at an odd A7
    err('1cec2-then-1cef4', U.with_host_writes(st, [((a6 + 0xaa) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x1cec2), odd_word, 0x1cef4)
    #   1c05e (D0.W & 1 = 0) -> 1c066 RTS at an odd A7
    err('1c05e-then-1c066', U.with_host_writes(st, regs=dict(d0=2, a7=a7 + 1), pc=0x1c05e), odd_word, 0x1c066)
    #   4f22c (WORD 76 = 0, WORD 10dddc = 5 = BYTE a0, BYTE 9a set) -> 4f240 -> 4f24c -> 4f254 -> 4f25c RTS at an odd A7
    err('4f22c-then-4f25c', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 0), (0xdddc, 2, 5), ((a6 + 0xa0) & 0xffff, 1, 5), ((a6 + 0x9a) & 0xffff, 1, 1)],
                                               regs=dict(a7=a7 + 1), pc=0x4f22c), odd_word, 0x4f25c)
    #   21d60 (BYTE 9d = 1) -> BGT.W 21dd0 (C12 deferred leader, unrouted)
    err('21d60-then-21dd0', U.with_host_writes(st, [((a6 + 0x9d) & 0xffff, 1, 1)], pc=0x21d60), unrouted, 0x21dd0)
    #   4e564 (WORD 76 = 0) -> 4e572 (player C6 since; was: unrouted at 4e572, error-4e564-then-4e572) -> 4e57e -> JMP 3918 -> BSR.W 386e of 391a at
    #   an odd A7 (the native run cannot stop at a work RAM PC, so the C++ unit test's RAM return LONG 10fe40 is not used here)
    err('4e564-then-391a', U.with_host_writes(st, [((a6 + 0x76) & 0xffff, 2, 0)], regs=dict(a7=a7 + 1), pc=0x4e564), odd_word, 0x391a)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x4f16e, 0x1ef0e, 0x4ea76, 0x4f1f4)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
