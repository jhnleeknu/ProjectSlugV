"""V1 fixture spec of the area-C unit C3 (engine/src/animation_machine_player_c3.cpp, 230 block starts; file prefix pc3 / player_c3 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c3-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C3 spec of the
contract): the second half of the player object frame (and the straight-line continuations 1cde0 / 1cdf0 / 1cdfa of C2 1cdd8 /
1cdea and 202a0 of 20290 that the IO runs execute inside one TB, contract decision 10): the state 1ee00 (fall-through of the C2 block 1edf6) with the record test 1ed22 and the turn
state 1f126 / 1f166, the common state tail 201a2 (JSR (A4) 201a6 on LONG 84(A6), contract decision 2; 4d0a4 / 4de9c; the BRA.W table jump 2031c,
decision 2; 20516; 20626 / 206a4 with the LONG table 206d4), the slot-84 states 21602 / 21610 (the (handler, key) list lookup 215e6, JMP (A1) 21620),
21c22 / 21c66 (21baa with the BYTE table 21ba6, 21bc6, 21be6 SUBX, 21c1c), 21f30 21f40 21f58 21f70, 21ffc / 221ca / 221d2 (JMP (A1) 221de), the move
helper 2156a (MOVEM.W around 49fca), the 28ae child 361e4 (bank LONG 200098), the C helpers 48350 48384 484ca 4d0a4 4de9c and the record helper e8b5a.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1, C2) with declared host edits.
This code runs natively only in the IO observation (P1 / boot-title-start / boot-demo-0): the 'natural' family takes the frame-start states of the IO
native observation in which the player node 100cb8 holds the C2 callback 1edb0 (whose frame reaches 1ee00 / 201a2 and the slot-84 state 21c66), keeps
their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the sentinel return LONG, PC = the callback); the
'reinstall' family enters 1f166 / 361e4 / 1edb0 (with a declared slot-84 LONG) on the IO nodes.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 22 C consumers and the Z reader 1ee56 is entered directly (the seed world with declared edits).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS) and the Z reader 1ee56 through 1ee4e -> 1cb08 -> 1cb18.  Stop: the consumer's
            successor or the first unrouted PC.
  node      the installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with declared callback / slot LONGs.
  callee    the helpers and the slot-84 states entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 22 consumers, computed-jump targets outside the transcribed lists
            (decision 2), the Z source of 1ee56 outside the routed path (decision 3), odd node / stack / A4, failures after executed blocks: checked
            error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1, C2
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1, C2)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc3'
ERROR_PC = 'unsupported animation player c3 PC'
ERROR_CARRY = 'player c3 caller requires known carry'
ERROR_FLAG = 'unsupported animation player c3 flag source'
ERROR_JUMP = 'unsupported animation player c3 jump target'

RANGES = [(0x1cb40, 0x1cb44), (0x1cde0, 0x1cdea), (0x1cdf0, 0x1cdfe), (0x1ed22, 0x1ed34), (0x1ee00, 0x1eee0), (0x1f126, 0x1f1d8), (0x201a2, 0x201bc), (0x201d0, 0x20240), (0x2024a, 0x20268),
          (0x20290, 0x202ac), (0x202b6, 0x20320), (0x20516, 0x20544), (0x20626, 0x206cc), (0x206d2, 0x206d4), (0x2156a, 0x21622), (0x21baa, 0x21c12),
          (0x21c1a, 0x21c72), (0x21c74, 0x21ca4), (0x21f30, 0x21f4c), (0x21f58, 0x21f78), (0x21ffc, 0x22028), (0x221ca, 0x22238), (0x361e4, 0x36292),
          (0x48350, 0x48368), (0x48384, 0x4838c), (0x48392, 0x48398), (0x484ca, 0x484d2), (0x4d0a4, 0x4d0cc), (0x4d100, 0x4d106), (0x4de9c, 0x4dee2),
          (0xe8b5a, 0xe8b7e)]
STARTS = sorted(int(x, 16) for x in (
    '1cb40 1cde0 1cdf0 1cdfa 1ed22 1ed26 1ed2a 1ed30 1ed32 1ee00 1ee04 1ee08 1ee12 1ee16 1ee1a 1ee26 1ee2a 1ee32 1ee36 1ee3c 1ee40 1ee46 1ee4e 1ee56 1ee5a 1ee64 1ee72 '
    '1ee74 1ee7a 1ee7e 1ee86 1ee8a 1ee90 1ee98 1eea4 1eea8 1eeae 1eeb6 1eec2 1eec6 1eecc 1eed6 1eedc 1f126 1f12a 1f166 1f16a 1f174 1f17c 1f186 1f18e '
    '1f198 1f19c 1f1a4 1f1b4 1f1ba 1f1c4 1f1ca 1f1ce 1f1d4 201a2 201a8 201ae 201b8 201d0 201da 201e4 201e8 201f2 201f8 201fc 20206 20210 20216 2021c '
    '20226 2022a 20238 2024a 20254 2025e 20264 20290 202a0 202b6 202c2 202d0 202da 202de 202e6 202ec 202f4 202fc 20300 2030a 20318 20516 2051e 2052c 20530 '
    '20534 2053c 20626 2062e 2063a 20640 20648 20654 2065e 20670 20674 20682 20686 2068e 2069c 206a4 206c0 206c6 206d2 2156a 21580 21582 2158c 2158e '
    '215c4 215e6 215ec 215f6 215f8 215fc 21602 21610 2161c 21620 21baa 21bb2 21bc0 21bc6 21bd0 21bda 21be0 21be6 21bfa 21c00 21c06 21c1a 21c1c 21c22 '
    '21c34 21c3a 21c3e 21c42 21c46 21c48 21c4c 21c5a 21c66 21c6e 21c74 21c78 21c80 21c88 21c90 21c98 21c9c 21ca0 21f30 21f3c 21f40 21f48 21f58 21f70 '
    '21ffc 22004 221ca 221d2 221da 221de 221e0 221e4 221ec 221f6 221fe 22208 22210 22216 2221a 22220 22228 22230 22236 361e4 3620a 36218 36228 3622c '
    '3623a 3624a 36256 3625c 36264 3626a 36272 36278 36282 36286 3628c 48350 4835a 48362 48384 48392 484ca 4d0a4 4d0ac 4d0b4 4d0b8 4d0be 4d100 4de9c '
    '4dea8 4deac 4deb4 4deba 4debc 4dec2 4deca 4ded4 e8b5a e8b6e').split())
CONSUMERS = (0x1ed26, 0x1ee04, 0x1ee16, 0x1ee26, 0x1ee32, 0x1ee3c, 0x1ee7a, 0x1ee86, 0x1eea4, 0x1eec2, 0x1f1ca, 0x201b8, 0x201e4, 0x202da, 0x2161c,
             0x21c3a, 0x21c42, 0x21c48, 0x21c6e, 0x21c9c, 0x221da, 0x36282)
# 215ec CMPA.W #0 leaves C Clear; 21bc0 21be0 21bfa 21c1c 48392 4d100 4debc 4ded4 return Clear (ANDI.B #fe,CCR; RTS)
CLEAR_SET = (0x215ec, 0x21bc0, 0x21be0, 0x21bfa, 0x21c1c, 0x48392, 0x4d100, 0x4debc, 0x4ded4)
SET_SET = (0x215fc, 0x21bda, 0x48362, 0x4deca)                 # ORI.B #1,CCR; RTS
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x1ed30, 0x21bb2, 0x21c06)  # CMP.W D1,D0 / CMP.B a1(A6),D0 (RTS) / CMP.W D1,D0 (BCC): the compare borrow
INVERT_SET = ()
PASS_SET = (0x1ee00, 0x1ed32, 0x215f6, 0x21c1a)                # BSR 1ed34 / RTS blocks that keep the incoming C (carry preserving, not consumers)
STARTS_SET = set()
Z_READERS = (0x1ee56,)                  # BNE.W on the Z of 1cb08 (contract decision 3): never entered directly by a native run (SR Z = 0 at a start)
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
# 21c48 BCS.W 21fa6 reads the C of 21c1c (ANDI.B #fe,CCR; RTS): always Clear
STATIC_IMPOSSIBLE = {(0x21c48, 0x21fa6)}
# outcomes that need a producer of a later unit: the Set side of 1cb08 (the C5 block 1cb1a / its 1cb32 ORI) for 1ed26 / 1ee32 / 1ee86 and through 1ed22
# for 1ee26 / 1eea4 / 1eec2 and through C2 1ed6c for 1ee04; the Set side of 4d0a4 (4d0cc, C8) for 201b8; the Set side of 21be6 (21c06 -> 21c12, C5) for
# 21c9c; the Z = 0 return of 1cb08 (1cb32, C5) for 1ee56.  The declared-C rows of the C++ unit test and the real-ROM differential cover them.
LATER_GATED = {(0x1ed26, 0x1ed2a), (0x1ee04, 0x1f126), (0x1ee26, 0x1eee0), (0x1ee32, 0x1eee0), (0x1ee86, 0x1eee0), (0x1eea4, 0x1eee0),
               (0x1eec2, 0x1eee0), (0x201b8, 0x201bc), (0x21c9c, 0x21f4c), (0x1ee56, 0x1eee0)}
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units (and deferred leaders) that a C3 block reaches by a fall-through, a branch, a call or a return (declared stops of the native runs:
# a straight-line unrouted PC after a C3 block is not the interior of a routed block)
EXIT_STOPS = (0x1cb44, 0x1fa68, 0x201bc, 0x20240, 0x20268, 0x202ac, 0x20544, 0x206cc, 0x21662, 0x21c12, 0x21c72, 0x21f4c, 0x21f78, 0x4838c, 0x4d0cc,
              0x1fc96, 0x1fd50, 0x21ca4, 0x21d0e, 0x21fa6, 0x2210c, 0x223a0, 0x223d6,
              # the later-unit stops of the C2 blocks that the C3 runs pass through (pc2 EXIT_STOPS that are still unrouted; the straight-line ones
              # 1ce98 1ceb0 1d398 are not interiors of a routed block; 1cde0 1cdf0 are C3 starts now, contract decision 10)
              0x1cb1a, 0x1cb38, 0x1ce98, 0x1cfde, 0x1ceb0, 0x1cec2, 0x1d398, 0x1ebbe, 0x1eeea, 0x1f2a4, 0x1fafc, 0x1de3c, 0x1e21c, 0x1e8de)
# later-unit stops routed since (player C4: 21c72 1ceb0 1cec2 1eeea; player C5: 1cb44 20240 20268 202ac 20544 21c12 21f4c 21f78 1cb1a 1cb38; player
# C6: 206cc 21662 4838c 1d398 1ebbe; player C7: 1f2a4): still declared stops of the C3 runs
ROUTED_LATER = (0x21c72, 0x1ceb0, 0x1cec2, 0x1eeea, 0x1cb44, 0x20240, 0x20268, 0x202ac, 0x20544, 0x21c12, 0x21f4c, 0x21f78, 0x1cb1a, 0x1cb38,
                0x206cc, 0x21662, 0x4838c, 0x1d398, 0x1ebbe, 0x1f2a4)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1edf6, 0x1ee04), (0x1ed22, 0x1ed26), (0x1ee12, 0x1ee16), (0x1ee1a, 0x1ee26), (0x1ee2a, 0x1ee32), (0x1ee36, 0x1ee3c), (0x1ee74, 0x1ee7a),
          (0x1ee7e, 0x1ee86), (0x1ee98, 0x1eea4), (0x1eeb6, 0x1eec2), (0x1f1c4, 0x1f1ca), (0x201ae, 0x201b8), (0x201da, 0x201e4), (0x202d0, 0x202da),
          (0x21610, 0x2161c), (0x21c34, 0x21c3a), (0x21c3e, 0x21c42), (0x21c46, 0x21c48), (0x21c66, 0x21c6e), (0x21c98, 0x21c9c), (0x221d2, 0x221da),
          (0x36278, 0x36282), (0x1ee4e, 0x1ee56))
PASS_CHAINS = ()
TABLE_JUMPS = {}
# computed jumps (contract decision 2): JSR (A4) 201a6, JMP (PC,D0.W) 2031c, JMP (A1) 21620 / 221de
JUMP_PCS = (0x201a6, 0x2031c, 0x21620, 0x221de)
TABLE_ENTRIES = ()
SLOT84 = (0x21602, 0x21610, 0x21664, 0x2173c, 0x21770, 0x217b2, 0x217e0, 0x217f6, 0x218b2, 0x2190e, 0x21960, 0x2199a, 0x219d8, 0x21a76, 0x21acc,
          0x21c66, 0x21cd8, 0x21d2a, 0x21d92, 0x21e04, 0x21e6a, 0x21eb0, 0x21f02, 0x21f70, 0x21fc6, 0x21ffc, 0x2210c, 0x22128, 0x221d2, 0x22240,
          0x2228e, 0x22360, 0x2241c, 0x22452)
LIST_21622 = (0x21c22, 0x21d60, 0x21e48, 0x21e3a, 0x21720, 0x217e0, 0x2178e, 0x2175a, 0x21950, 0x219c8)
# the slot-84 values a world uses: the routed C3 states, one unrouted listed value (2210c, C12 deferred) as a stop
SLOT_WORLD = (0x21602, 0x21610, 0x21c66, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x2210c)
# installed values entered as node callbacks; the callee entries (helpers and states entered as subroutines; not the pass block 1ee00: its consumer
# 1ee04 reads the C that 1ee00 brings in, so 1ee00 is entered through its producer C2 1edf6 (chain))
NODE_ENTRIES = (0x1f166, 0x361e4)
CALLEES = (0x1cb40, 0x1ed22, 0x1f126, 0x201a2, 0x202b6, 0x206a4, 0x2156a, 0x215e6, 0x21602, 0x21610, 0x21baa, 0x21bc6, 0x21be6, 0x21c1c,
           0x21c22, 0x21c66, 0x21f30, 0x21f40, 0x21f70, 0x21ffc, 0x221d2, 0x48350, 0x48384, 0x484ca, 0x4d0a4, 0x4de9c, 0xe8b5a)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x84, 0x8c, 0x94)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('P1', 94, f) for f in (193, 194, 200, 218)] + [('P1', 68, f) for f in (409, 410, 434)] +
                [('P1', 106, f) for f in (193, 205)] + [('boot-title-start', None, f) for f in (313, 314, 338)] + [('boot-demo-0', None, f) for f in (382, 383)])
NATURAL_CALLBACKS = (0x1edb0,) + NODE_ENTRIES                         # 1edb0 (C2) runs into 1ee00 / 201a2 (C3) in the same callback
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node), extra (offset, size, value) writes on the node)
REINSTALL = (('P1', 94, 193, 0x100cb8, 0x1f166, ()), ('P1', 68, 409, 0x100cb8, 0x1f166, ()), ('boot-title-start', None, 313, 0x100cb8, 0x1f166, ()),
             ('boot-demo-0', None, 382, 0x100cb8, 0x1f166, ()),
             ('P1', 94, 193, 0x101704, 0x361e4, ()), ('P1', 68, 409, 0x101704, 0x361e4, ()), ('boot-title-start', None, 313, 0x101704, 0x361e4, ()),
             ('P1', 94, 193, 0x100cb8, 0x1edb0, ((0x84, 4, 0x21602),)), ('P1', 94, 193, 0x100cb8, 0x1edb0, ((0x84, 4, 0x21610),)),
             ('P1', 94, 193, 0x100cb8, 0x1edb0, ((0x84, 4, 0x21f70),)), ('P1', 94, 193, 0x100cb8, 0x1edb0, ((0x84, 4, 0x221d2),)),
             ('P1', 94, 193, 0x100cb8, 0x1edb0, ((0x84, 4, 0x21ffc),)), ('P1', 94, 393, 0x100cb8, 0x1edb0, ()),
             ('P1', 94, 347, 0x100cb8, 0x1edb0, ()), ('boot-demo-0', None, 411, 0x100cb8, 0x1edb0, ()))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0x10, 0x11, 0x18, 0x1d, 0x1e, 0x1f, 0x20, 0x40, 0x77, 0x7f, 0x80, 0x81, 0xbf, 0xfe, 0xff)
VW = (0, 1, 2, 4, 0xc, 0x10, 0x1c, 0x20, 0x40, 0x7f, 0x80, 0xff, 0x100, 0x400, 0x7fff, 0x8000, 0x8001, 0xfff0, 0xfffe, 0xffff)
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
BUNDLED = (0x21c30,)                    # BLT.W 21d0e right after BGT.W 21ca4 (flag-sharing pair inside the block 21c22)


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (1cb40 falls to 1cb44 (C5), 20290 to 202a0 (C5), 1f12a to the installed 1f166)."""
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
    """Static successors of the entry block (None = computed: RTS, JSR (A4), JMP (A1), JMP (PC,D0.W))."""
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
    """The PC after the entry block: pcs[n]; in the bundled BGT.W / BLT.W block 21c22 a taken BGT.W skips the BLT.W, so the successor is pcs[n - 1]
    (or the stop)."""
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
    jumps 201a6 / 2031c / 21620 / 221de that is not a routed block start of this unit (an unrouted listed target: the C++ dispatch of it is the checked PC
    error), or at the first unrouted PC that is not the straight-line successor of the previous instruction (a PC inside a block of another executor is
    not a block entry)."""
    ex = set(extra) | {SENTINEL, 0x2a00, 0x2a24} | set(EXIT_STOPS) | set(TRAPS)

    def outside(pc, prev, size):
        if pc in ex:
            return True
        if prev in JUMP_PCS and pc not in STARTS_SET:
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
        """A world for `entry`.  The values a ROM writer bounds are kept in their ROM range (contract decision 2): LONG 84(A6) one of the listed slot
        values, BYTE a0(A6) 0..8 (the jump table 2031c), BYTE a9(A6) 0..5 (the LONG table 206d4), A1 a handler of the list of the JMP (A1) entered
        directly, D0 of a direct 20318 entry 0..8; LONG 5434(A5) = 0 (C2 decision 2: the only ROM value)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x48, 0x5e, 0x400, 0xffff, 0x12345678, 0x10000))   # input summary bits
        if entry == 0x20318:
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.randrange(9)
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = 0x21602 if entry == 0x221de else rng.choice(LIST_21622[:3])
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6) (361e4: WORD 78 of the parent)
        writes.append(((a6 + 0x8c) & 0xffff, 4, self.pointer()))    # LONG 8c(A6) (A4 of 202b6 / 202f4, C2 1cd98)
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of C2 1cad4)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(),))))   # LONG 3e(A6) (C2 1a9fe..1aa20)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT_WORLD)))                  # LONG 84(A6): the slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): index of the jump table 2031c
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): index of the LONG table 206d4
        writes.append(((a5 + 0x5434) & 0xffff, 4, 0))                                     # LONG 5434(A5): A1 of the C2 JMP (A1) 1aa38 (0 in ROM)
        writes.append(((a5 + 0x5474) & 0xffff, 4, rng.choice((0, self.pointer()))))       # LONG 5474(A5): A0 of C2 1cd2a
        writes.append(((a5 + 0x5e26) & 0xffff, 4, self.pointer()))                        # LONG 5e26(A5): A4 of e8b5a
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4 (callee worlds)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9)):
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
            for off, size, val in hint.get('a4off', []):
                writes.append(((a6 + 0x8c) & 0xffff, 4, regs['a2']))                # LONG 8c(A6) := A2's node; A4 := the same for a direct entry
                regs['a4'] = regs['a2']
                writes.append(((regs['a2'] + off) & 0xffff, size, val))
            for off, size, val in hint.get('a0off', []):
                writes.append(((regs['a0'] + off) & 0xffff, size, val))
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
    require(len(STARTS) == 230 and len(STARTS_SET) == 230, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for t in SLOT84 + LIST_21622 + tuple(range(0x20320, 0x20344, 4)):
        # player C4 routes the listed targets 21d92 (slot 84) and 21d60 (list 21622) since
        require(unit_of(t) in (None, 'animation_player_c3_block', 'animation_player_c4_block'), ('computed-jump target routed by another unit', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c3_block', ('start is not routed to player c3', hex(s), unit_of(s)))
    rng = random.Random(0xC3A3)
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
    sys.stderr.write('pc3 spec: %d fixtures (%d natural), visited %d/230, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc3: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc3: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (CMPI.B ties, the signed
    TST.B / SUB.L / SUB.W of 21c22 / 2062e / 20640, the unsigned CMP.W / CMP.B borrows of 1ed30 / 21bb2 / 21c06, the BTST / BSET / BCLR / BCHG bits of
    the node BYTEs and of D0, the SUBQ.W borrow of 202b6 and the SUBQ.W zero of 20238, the ADDQ.B wrap and SUBX of 21be6, the EXT.W / NEG.W / MOVEM.W of
    2156a, the list lookup keys of 215e6, the jump-table index of 20318, the slot-84 values of 201a2, the Z source of 1ee56 is chain-only), the upper
    register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    a5b = lambda off, vals: [dict(a5off=[(off, 1, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0x1ed30, 0x1ee1a, 0x1ee46, 0x1ee64, 0x1ee72, 0x1ee98, 0x1eeb6, 0x1eecc, 0x1f18e, 0x1f1a4, 0x1f1ba, 0x201ae, 0x201da, 0x202d0, 0x202de,
                 0x2030a, 0x20516, 0x2051e, 0x2062e, 0x20640, 0x2068e, 0x206a4, 0x2156a, 0x21580, 0x2158c, 0x2158e, 0x215c4, 0x215e6, 0x21bb2, 0x21be6,
                 0x21c06, 0x2221a, 0x3620a, 0x3622c, 0x36218, 0x3624a, 0x361e4, 0x484ca, 0x4d0be, 0x4de9c, 0xe8b5a, 0xe8b6e):
        h += [dict(regs=dict(up))]
    # ---- 1ed30: CMP.W D1,D0 (the borrow)
    if entry == 0x1ed30:
        h += [dict(regs=dict(up, d0=a, d1=b)) for a, b in ((5, 5), (5, 6), (6, 5), (0, 0xffff), (0xffff, 0), (0x12340000, 0x10001), (0x8000, 0x7fff))]
    # ---- 1ee00 .. 1eedc
    if entry in (0x1ee08,):
        h += byte(0xa7, (0, 0x20, 0xdf, 0xff))
    if entry == 0x1ee46:
        h += [dict(regs=dict(d0=d0), a6off=[(0x60, 1, b)]) for d0, b in ((0x12345601, 1), (0x12345601, 2), (0xff, 0x80), (0x100, 0xff), (0, 0xff))]
    if entry == 0x1ee5a:
        h += byte(0x6e, (2, 1, 3, 0x82))
    if entry == 0x1ee64:
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x1ee72:
        h += regs('d0', (0x10, 0x12340010, 0x8000, 0))
    if entry in (0x1ee90, 0x1eeae):
        h += regs('d0', (0, 1, 2, 3, 0xfffc, 0x12345601, 0x12345602))
    if entry in (0x1eecc, 0x1f1ba):
        h += word(0x1e, (0, 0x8834, 0xffff))
    # ---- 1f126 .. 1f1d4
    if entry == 0x1f12a:
        h += byte(0xa7, (0, 2, 0xfd, 0xff)) + [dict(mirror=True)]
    if entry == 0x1f16a:
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry in (0x1f174, 0x1f186):
        h += regs('d0', (0, 2, 0x20, 0x22, 0xffdd, 0x12345622))
    if entry == 0x1f17c:
        h += byte(0x9e, (0, 1, 0x80))
    if entry == 0x1f18e:
        h += regs('d0', (0, 4, 8, 0xc, 0xfff3, 0xc0000, 0x12345673))
    if entry == 0x1f19c:
        h += byte(0x7e, (0, 1, 0x80))
    if entry == 0x1f1a4:
        h += regs('d0', (0, 2, 4, 8, 0x10, 0x40, 0x5e, 0xffa1, 0x5e0000, 0x12345621))
    # ---- 201a2: the slot-84 values (contract decision 2)
    if entry == 0x201a2:
        h += long_(0x84, (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x2210c, 0x21664, 0x22452)) + [dict(mirror=True)]
    if entry in (0x201ae, 0x201da, 0x202d0, 0x2068e):
        h += word(0x78, (0, 1, 0x8000, 0xffff))
    if entry == 0x201d0:
        h += byte(0xa7, (0, 0x80, 0x7f, 0xff))
    if entry in (0x201e8, 0x201fc):
        h += byte(0xa7, (0, 0x40, 0xbf, 0xff))
    if entry == 0x20206:
        h += byte(0x5e, (0x18, 0x17, 0x19, 0x98))
    if entry == 0x20210:
        h += byte(0xa8, (0, 0xfd, 0xff))
    if entry == 0x2021c:
        h += byte(0x61, (0, 0x40, 0xbf, 0xff))
    if entry == 0x2022a:
        h += [dict(a6off=[(0x19, 1, v), (0x90, 2, w)]) for v, w in ((0x80, 0), (0x7f, 1), (0, 0x100), (0xff, 0x8000))]
    if entry == 0x20238:
        h += word(0x90, (1, 2, 0, 0x100, 0x8000))
    if entry == 0x2024a:
        h += byte(0xa7, (0, 4, 0xfb, 0xff))
    if entry == 0x20254:
        h += byte(0xa8, (0, 0x40, 0xbf, 0xff))
    if entry == 0x2025e:
        h += byte(0x1a, (0, 0x80, 0xff))
    if entry == 0x20290:
        h += byte(0x61, (0, 0x40, 0x80, 0xc0, 0x3f, 0xff))
    if entry == 0x202b6:
        h += [dict(a4off=[(8, 2, v)]) for v in (0, 1, 0x8000, 0xffff)]
    if entry == 0x1cdf0:
        h += [dict(a4off=[(1, 1, v)]) for v in (0, 1, 2, 3, 0x80, 0xff)]
    if entry == 0x1cdfa:
        h += regs('d0', (0xffffffff, 0x40, 0x12345678))
    if entry == 0x1cde0:
        h += byte(0x61, (0, 0x10, 0xef, 0xff))
    if entry == 0x202a0:
        h += [dict(a4off=[(0xc, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x202c2:
        h += byte(0x9e, (1, 0, 2, 0x81))
    if entry == 0x202ec:
        h += regs('d0', (0, 0x20, 0xffdf, 0x12345620))
    if entry == 0x20300:
        h += byte(0xa8, (0, 8, 0xf7, 0xff))
    if entry == 0x2030a:
        h += [dict(a6off=[(0xa0, 1, a), (0x9f, 1, b)]) for a, b in ((0, 0), (3, 3), (3, 4), (8, 0), (0, 8), (5, 0x85))]
    if entry == 0x20318:
        h += [dict(regs=dict(d0=v)) for v in (0, 1, 2, 3, 4, 5, 6, 7, 8, 0x12340005, 0x4000, 0xffff4003)]
    # ---- 20516 .. 206d2
    if entry == 0x20516:
        h += byte(0xa4, (0, 1, 2, 0x80, 0xff))
    if entry == 0x2051e:
        h += [dict(regs=dict(d0=v)) for v in (0x12345601, 0x12345602, 0x00ffff00, 0x81, 0x10000)]
    if entry == 0x2053c:
        h += byte(0x5e, (0, 1, 0x80))
    if entry == 0x20626:
        h += a5b(0x5c8d, (0, 1, 0x80))
    if entry == 0x2062e:
        for a, b in ((5, 5), (6, 5), (5, 6), (0x80000000, 0x7fffffff), (0x7fffffff, 0x80000000), (0xffffffff, 0), (0, 0xffffffff), (0x10000, 0xffff)):
            h.append(dict(regs=dict(up), a6off=[(0x46, 4, a), (0x4e, 4, b)]))
    if entry == 0x20640:
        for d0, w in ((5, 5), (6, 5), (5, 6), (0x8000, 0x7fff), (0x7fff, 0x8000), (0x1234ffff, 0), (0x5678, 0xffff), (0xabcd0000, 0)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x46, 2, w)]))
    if entry in (0x20648, 0x2065e):
        h += byte(0x61, (0, 0x80, 0x7f)) + [dict(mirror=True)]
    if entry == 0x20654:
        h += byte(0xa8, (0, 2, 0xfd, 0xff))
    if entry == 0x20674:
        h += byte(0xab, (0, 1, 0x80, 0xff))
    if entry == 0x20682:
        h += byte(0xab, (0, 1, 0x80))
    if entry == 0x20686:
        h += byte(0xac, (0, 1, 0x80))
    if entry == 0x2068e:
        h += byte(0xac, (0, 1, 0x80))
    if entry == 0x2069c:
        h += byte(0xa8, (0, 0x80, 0x7f, 0xff))
    if entry == 0x206a4:
        h += byte(0xa9, (0, 1, 2, 3, 4, 5)) + byte(0xa7, (0xff,))
    if entry == 0x206c6:
        h += regs('d0', (0, 1, 0x100, 0x12345600, 0x80))
    # ---- 2156a .. 215c4: the move helper
    if entry == 0x2156a:
        for a, b, f in ((0x7f, 0x80, 0), (0x80, 0x7f, 1), (0xff, 1, 2), (1, 0xff, 3), (0, 0, 0xff), (0x81, 0x81, 0xfc)):
            h.append(dict(regs=dict(up), a6off=[(0x7a, 1, a), (0x7b, 1, b), (0x15, 1, f)]))
    if entry in (0x21580, 0x2158c):
        h += [dict(regs=dict(up, d0=v, d1=v ^ 0x8001)) for v in (0x80, 0xff80, 0x7f, 0x12340001, 0x8000)]
    if entry == 0x21582:
        h += byte(0x15, (0, 2, 0xfd, 0xff))
    if entry == 0x2158e:
        for d0, d1 in ((0xff80, 0x7f), (0x1234007f, 0x5678ff81), (0x8000, 0x8000), (0, 1)):
            h.append(dict(regs=dict(up, d0=d0, d1=d1), a6off=[(0x2e, 2, 0xfff0), (0x32, 2, 0x10), (0x1e, 2, 0xffff), (0x42, 2, 0x8000), (0x4e, 2, 0x7fff)]))
        h += [dict(mirror=True)]
    if entry == 0x215c4:
        for a, b, c in ((0x8834, 0xff80, 0x7f), (0, 0x7fff, 0x8000), (0xffff, 1, 0xffff)):
            h.append(dict(regs=dict(up), stack=[(0, 2, a), (2, 2, b), (4, 2, c), (6, 4, SENTINEL)], a6off=[(0x2e, 2, 0x10), (0x32, 2, 0xfff0)]))
    # ---- 215e6: the key BYTE 9c and the lists (A0 = a RAM list in the worlds; the ROM lists from 21610 / 21c66 / 221d2)
    if entry == 0x215e6:
        h += byte(0x9c, (0, 1, 2, 0x80, 0xff))
    if entry == 0x215ec:
        h += [dict(a0off=[(0, 4, v)]) for v in (0, 0x10000, 0x21c22)]
    if entry in (0x21610, 0x21c66, 0x221d2):
        h += byte(0x9c, (0, 1, 2, 3, 4, 5, 0xa, 0xb, 0x80))
    if entry == 0x21602:
        h += byte(0xa7, (0, 0x20, 0xdf, 0xff)) + [dict(mirror=True)]
    if entry == 0x21620:
        h += [dict(regs=dict(a1=v)) for v in LIST_21622]
    # ---- 21baa .. 21c22
    if entry == 0x21baa:
        h += byte(0x9f, (0, 1, 0x80))
    if entry == 0x21bb2:
        for w, a1 in ((0, 0xb), (0, 0xc), (0, 0xa), (1, 0xb), (2, 6), (3, 7), (2, 5), (0, 0x80)):
            h.append(dict(regs=dict(up), a6off=[(0x76, 2, w), (0xa1, 1, a1)]))
    if entry == 0x21bc6:
        h += byte(0x9e, (1, 0, 2, 0x81))
    if entry == 0x21bd0:
        h += byte(0xa7, (0, 0x10, 0xef, 0xff))
    if entry == 0x21be6:
        h += [dict(regs=dict(up, d0=d0), a6off=[(0xa3, 1, v)]) for d0, v in ((0x12345678, 0xff), (0x1234ffff, 0xfe), (0, 2), (0, 3), (0xffff, 4), (0, 0x7f), (0, 0x80))]
    if entry == 0x21c06:
        h += [dict(regs=dict(up, d0=d0), a6off=[(0xa3, 1, v)]) for d0, v in ((5, 5), (4, 5), (6, 5), (0x12340004, 4), (0xffff, 0xff), (0x100, 0xff), (0, 0x80))]
    if entry == 0x21c22:
        h += byte(0x9d, (0, 1, 0x7f, 0x80, 0xff)) + byte(0xa7, (0xdf,))
    if entry in (0x21c34, 0x21f58, 0x22004):
        h += byte(0x9d, (0x80, 1)) + byte(0xa7, (0xff, 0))
    if entry in (0x21c78, 0x21c80, 0x21c88, 0x21c90):
        h += regs('d0', (0, 1, 2, 0x10, 0x40, 0xffae, 0x12345600, 0x53))
    if entry == 0x21c5a:
        h += byte(0xa3, (0xff,)) + [dict(mirror=True)]
    if entry == 0x22004:
        h += [dict(a6off=[(0xa5, 1, a), (0xa6, 1, b)]) for a, b in ((0xff, 0x40), (0x40, 0xff), (0xbf, 0))]
    if entry == 0x221e4:
        h += byte(0x7e, (0, 1, 0x80))
    if entry in (0x221ec, 0x221fe):
        h += byte(0xa5, (0, 0x10, 0x40, 0x50, 0xaf, 0xff))
    if entry == 0x2221a:
        h += regs('d7', (0, 1, 0x10000, 0x8000, 0x12340000))
    if entry == 0x22228:
        h += byte(0x7e, (0, 1, 0x80))
    if entry == 0x22230:
        h += byte(0xa8, (0, 4, 0xfb, 0xff))
    if entry == 0x221de:
        h += [dict(regs=dict(a1=0x21602))]
    # ---- 361e4 .. 3628c (28ae child; A0 = the parent LONG c(A6))
    if entry == 0x361e4:
        for w in (0, 1, 0x8000, 0x10):
            h.append(dict(regs=dict(up), writes=[(0xe000, 2, w)], a6off=[(0xc, 4, 0x10df88)]))
        h += [dict(mirror=True)]
    if entry in (0x3625c, 0x3626a):
        h += regs('d0', (0, 8, 0x40, 0x48, 0xffb7, 0x12345608))
    if entry == 0x36286:
        h += byte(0x76, (0, 0xff)) + [dict(mirror=True)]
    # ---- 48350 .. 484ca
    if entry == 0x48350:
        h += a5b(0x5683, (0, 0x20, 0xdf, 0xff))
    if entry == 0x4835a:
        h += a5b(0x568e, (0, 1, 0x80))
    if entry == 0x48384:
        h += a5b(0x5684, (0, 1, 0x80))
    if entry == 0x484ca:
        h += a5b(0x5682, (0, 1, 0x80, 0xff))
    # ---- 4d0a4 / 4de9c
    if entry == 0x4d0a4:
        h += word(0x78, (0, 1, 0x100, 0x8000))
    if entry == 0x4d0b8:
        h += [dict(regs=dict(a4=0x108000 + 0x5cba), writes=[(0xdcba, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x4d0be:
        h += [dict(regs=dict(up, a4=0x108000 + 0x5cba), writes=[(0xdcdc, 1, v)]) for v in (0, 1, 0x80, 0xff, 0x7f)]
    if entry == 0x4de9c:
        h += regs('d0', (0, 1, 2, 3, 0x10000, 0x12345601, 0xfffe))
    if entry == 0x4deac:
        h += [dict(regs=dict(a4=0x108000 + 0x5d12), writes=[(0xdd16, 2, v)]) for v in (0, 0x7fff, 0x8000, 0xffff)]
    if entry in (0x4deb4, 0x4deba, 0x4dec2):
        h += [dict(regs=dict(a4=0x108000 + 0x5d18), writes=[(0xdd18, 1, v)]) for v in (0, 1, 2, 0x80, 0xff)]
    if entry == 0x4ded4:
        h += [dict(regs=dict(a4=0x108000 + 0x5d12), writes=[(0xdd12, 1, 5), (0xdd13, 1, 0x77)])]
    # ---- e8b5a / e8b6e
    if entry == 0xe8b5a:
        h += [dict(regs=dict(up), a5off=[(0x5e26, 4, 0x10df00)], writes=[(0xdf00, 2, 0x8001), (0xdf02, 2, 0x7ffe)])]
    if entry == 0xe8b6e:
        h += [dict(regs=dict(up, a4=0x10df00), writes=[(0xdf04, 1, v)]) for v in (0, 2, 0xfd, 0xff)]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def chain_hint(entry, t, rng):
    if entry == 0x1edf6:
        return dict(regs=dict(d0=(0, 0x10, 0x13, 0x1234ff10)[t % 4]), a6off=[(0xa7, 1, (0, 1, 0xff)[(t // 4) % 3]), (0x6e, 1, (5, 4)[(t // 2) % 2])])
    if entry == 0x1ed22:
        return dict(regs=dict(a0=(0x1b55e, 0x1b542, 0x1b5f2)[t % 3]), a6off=[(0x9f, 1, (1, 2, 3, 4)[(t // 3) % 4])])
    if entry in (0x1ee1a, 0x1ee98, 0x1eeb6, 0x1ee7e, 0x1ee4e):
        return dict(a6off=[(0x9f, 1, (3, 4, 5, 6)[t % 4])])                           # the ROM record tables 1b55e / 1b57c / 1b598 / 1b5b6 / 1b5f2: 0 for 9f >= 3
    if entry == 0x1ee2a:
        return dict(a6off=[(0x9f, 1, (1, 2, 4)[t % 3])])                              # 1b542: 0018 0000 0000 001a 0000 ..
    if entry == 0x1ee12:
        # 1dfe6: BYTE a7 bit 5 -> 1dff6 .. 49a58 (D0.W := the WORD at the ring pointer LONG 5722(A5)) .. 1e016 SUB.W D1,D0 (borrow when D0.W < a2 - 1e)
        return dict(a6off=[(0xa7, 1, (0, 0x20)[t % 2]), (0xa2, 1, (0, 0x1d, 0x1e, 0xff)[(t // 2) % 4])], a5off=[(0x5722, 4, 0x10d6b4)],
                    writes=[(0xd6b4, 2, (0x10, 0x8000, 0xe0, 0xe1)[(t // 8) % 4])])
    if entry == 0x1ee36:
        return dict(a5off=[(0x5683, 1, (0, 1, 0xfe, 0xff)[t % 4])])                    # 484e2: bit 0 of BYTE 5683(A5)
    if entry == 0x1f1c4 and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> Set
    if entry == 0x201ae:
        w = (0, 1)[t % 2]
        return dict(a6off=[(0x78, 2, w)], a5off=[(0x5cba + 0x2c * w, 2, 0)])            # 4d0a4: WORD (A4) = 0 -> 4d0be -> 4d100 (Clear)
    if entry == 0x201da:
        w = (0, 1)[t % 2]
        base = 0x5d12 + 6 * w
        return dict(a6off=[(0x78, 2, w)], a5off=[(base + 4, 2, (0, 0x8000)[(t // 2) % 2]), (base, 1, (0, 1, 2)[(t // 4) % 3])])
    if entry == 0x202d0:
        w = (0, 1, 0x8000, 0xffff)[t % 4]
        return dict(a6off=[(0x78, 2, w)], a5off=[(0x5734 + 4 * (w & 1), 4, (0, 0x10e400)[(t // 4) % 2])])   # 49c38: TST.L 5734(A5) + 4 (D0.W & 1)
    if entry in (0x21610, 0x21c66, 0x221d2):
        return dict(a6off=[(0x9c, 1, (0, 1, 2, 3, 4, 0xb)[t % 6])])                    # the ROM lists 21622 / 21aee / 216c8
    if entry == 0x21c34:
        return dict(a6off=[(0x9e, 1, (1, 0, 1)[t % 3]), (0xa7, 1, (0x10, 0x10, 0)[t % 3])])
    if entry == 0x21c3e:
        return dict(a6off=[(0x9f, 1, (0, 0, 1)[t % 3]), (0x76, 2, (0, 1)[(t // 3) % 2]), (0xa1, 1, (0xc, 0xa, 0)[t % 3])])
    if entry == 0x21c98:
        return dict(a6off=[(0xa3, 1, (0, 2, 3, 0xff)[t % 4])])
    if entry == 0x36278:
        return dict(a5off=[(0x5683, 1, (0, 0x10, 0xef, 0xff)[t % 4])])                 # 482aa: BTST #4,5683(A5): set -> Clear, clear -> Set
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
            # BYTE 15 bit 7 (on ground [I]), BYTE 9f / 9e / 9c / a7 / a8 / 6e / 7e, BYTE 1d(A6) < 4, WORD 104ca0 (28ae count limit), BYTE 5683 (4836e)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80)[t % 2]), (0x9f, 1, (0, 1, 2)[(t // 2) % 3]), (0xa8, 1, (0, 0x80)[(t // 3) % 2]),
                               (0xa7, 1, (0, 1, 0x20)[(t // 2) % 3]), (0x6e, 1, (0, 7)[(t // 5) % 2]), (0x9e, 1, (0, 1)[(t // 4) % 2]),
                               (0x7e, 1, (0, 1)[(t // 3) % 2]), (0x26, 4, 0), (0x9c, 1, (0, 1)[(t // 7) % 2])],
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
    err('odd-pc', U.with_host_writes(st, pc=0x201a3), 'unaligned animation machine PC', 0x201a3)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the computed jumps (contract decision 2): a slot-84 LONG / A1 / table displacement outside the transcribed lists is the checked jump-target error;
    # a listed target that is not routed yet fails at the next dispatch (the paired row stops at that target)
    for v in (0, 0x21603, 0x12345678, 0x1021602, 0x1ee00, 0x21622):
        err('201a2-slot-%x' % v, U.with_host_writes(st, [((a6 + 0x84) & 0xffff, 4, v)], pc=0x201a2), ERROR_JUMP, 0x201a2)
    for v in (0x2210c, 0x22452, 0x21664):
        err('201a2-slot-listed-%x' % v, U.with_host_writes(st, [((a6 + 0x84) & 0xffff, 4, v)], pc=0x201a2), unrouted, v)
    for v in (0x21602, 0x10fe40, 0, 0x21c23):
        err('21620-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21620), ERROR_JUMP, 0x21620)
    for v in (0x21e48, 0x219c8):              # player C4 routes 21d60 since (was 0x21d60, 0x219c8)
        err('21620-a1-listed-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21620), unrouted, v)
    for v in (0x21c22, 0x21603, 0x1021602):
        err('221de-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x221de), ERROR_JUMP, 0x221de)
    for v in (9, 0x47, 0xffff, 0x12340010):
        err('20318-d0-%x' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x20318), ERROR_JUMP, 0x20318)
    for v in (0, 8, 0x4000):
        err('20318-d0-entry-%x' % v, U.with_host_writes(st, regs=dict(d0=v), pc=0x20318), unrouted, 0x20320 + 4 * (v & 0x3fff))
    #   2030a (BYTE a0 = 9 != BYTE 9f) -> 20318: displacement 24 beyond the table
    err('2030a-then-20318', U.with_host_writes(st, [((a6 + 0xa0) & 0xffff, 1, 9), ((a6 + 0x9f) & 0xffff, 1, 0)], pc=0x2030a), ERROR_JUMP, 0x20318)
    #   21610 (BYTE 9c = 3) -> 215e6 on the ROM list 21622 -> Set, A1 = 21e48 -> 2161c -> JMP (A1): listed, unrouted (player C4 routes 21d60 since:
    #   was BYTE 9c = 2 -> 21d60, error-21610-then-21d60)
    err('21610-then-21e48', U.with_host_writes(st, [((a6 + 0x9c) & 0xffff, 1, 3)], pc=0x21610), unrouted, 0x21e48)
    # the Z source of 1ee56 (contract decision 3, widened by player C5): a source outside fixed ROM and work RAM.  A WORD (A0 + 2 x BYTE 9f) that is not
    # 0 is the C5 path 1cb1a since player C5 (the row '1ee56-word', A0 = 1b5f2 with BYTE 9f = 0, expected the flag-source error before); its first
    # source A0 + sext(W) = 1f9000 + 7000 = 200000 is the error now.
    err('1ee56-path-bank', U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, 0), (0x9000, 2, 0x7000)], regs=dict(a0=0x1f9000), pc=0x1ee56), ERROR_FLAG, 0x1ee56)
    err('1ee56-bank', U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, 0)], regs=dict(a0=0x200000), pc=0x1ee56), ERROR_FLAG, 0x1ee56)
    err('1ee56-io', U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, 1)], regs=dict(a0=0x3c0004), pc=0x1ee56), ERROR_FLAG, 0x1ee56)
    # odd node / stack / A4 / A0
    err('201a2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x201a2), odd_word, 0x201a2, stop=0x201a8)
    err('1f12a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1f12a), odd_write, 0x1f12a, stop=0x1f166)
    err('2158e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x2158e), odd_word, 0x2158e, stop=0x49fca)
    err('e8b6e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xe8b6e), odd_word, 0xe8b6e, stop=0xe8b80)
    err('4d0b8-odd-a4', U.with_host_writes(st, regs=dict(a4=a6 + 1), pc=0x4d0b8), odd_word, 0x4d0b8, stop=0x4d0be)
    err('202b6-odd-a4', U.with_host_writes(st, [((a6 + 0x8c) & 0xffff, 4, a6 + 1)], pc=0x202b6), odd_word, 0x202b6, stop=0x202e6)
    err('215ec-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x215ec), odd_word, 0x215ec, stop=0x215f6)
    err('e8b5a-odd-a5', U.with_host_writes(st, regs=dict(a5=a5 + 1), pc=0xe8b5a), odd_word, 0xe8b5a, stop=0xe8b6e)
    # failures after executed blocks:
    #   21baa (BYTE 9f != 0) -> 21bc0 RTS at an odd A7
    err('21baa-then-21bc0', U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, 1)], regs=dict(a7=a7 + 1), pc=0x21baa), odd_word, 0x21bc0)
    #   48384 (BYTE 5684 = 0) -> 48392 RTS at an odd A7
    err('48384-then-48392', U.with_host_writes(st, [((a5 + 0x5684) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x48384), odd_word, 0x48392)
    #   1ee5a (BYTE 6e = 2) -> 1ee64 (BYTE 15 bit 0 clear) -> 1ee74 JSR 4c1de.l at an odd A7
    err('1ee5a-then-1ee74', U.with_host_writes(st, [((a6 + 0x6e) & 0xffff, 1, 2), ((a6 + 0x15) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x1ee5a), odd_word,
        0x1ee74, stop=0x4c1de)
    #   21c5a (MOVE.L #21c66,84(A6)) -> 21c66 BSR.W 215e6 at an odd A7
    err('21c5a-then-21c66', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x21c5a), odd_word, 0x21c66, stop=0x215e6)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x2158e, 0x2062e, 0x1f12a, 0x21be6)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
