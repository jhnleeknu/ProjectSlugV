"""V1 fixture spec of the area-C unit C6 (engine/src/animation_machine_player_c6.cpp, 212 block starts; file prefix pc6 / player_c6 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c6-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C6 spec of the
contract): the E helpers b0c (the bit BYTEs 10f006 / 10f007, the BYTE slots 10fdb6, the fixed ROM BYTE table b58) and e6496 (the rank of LONG (A0) in the
LONG table 10f02e), the player-slot state 4eb58 -> 4ed3c -> 4edc0 / 4ee04 (4e5b0 and the BYTE table 4e4d2, the 28ae child e695a, the Z reader 4ee30 of
4a974, contract decision 3), the player body tail 1d398 (the D7 type chain) -> 1daba / 1dc1a / 1dce2 / 1dd36 / 1dd88 / 1dda8 (the 15-frame counters,
1d63a / 1d698, 43e08), 1d90a / 1d510 (the LONG table 1d468, 481b2, 2986), 1dbc6, 1dcd0 -> 1e824 (the 28ae child 1e67a, 1e60a, 1e65c, the state 1e89e),
1eba0 / 1efa4 / 1ebf6 (the input dispatch), 206cc, 21564, 21662, 4838c, 4e572, 4e8f8.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C5) with declared host edits.
This code runs natively only in the IO observation (P1 / boot-title-start / boot-demo-0): the 'natural' family takes the frame-start states of the IO
native observation in which a node of the pool holds a callback that runs into C6 code (C5 214d6 -> 21564; C4 4e94e -> 4eb58 -> 4ed3c; 4ee04; C4 1ef0e
-> 1efa4; 1ebf6), keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the sentinel return LONG,
PC = the callback); the 'reinstall' family enters a C6 callback (or C1 1d1f4, whose demo run reaches 1d398) with declared BYTEs / WORDs.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 8 C consumers and the Z reader 4ee30 is entered directly (the seed world with declared edits).  Stop: the
            first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS) and the Z reader 4ee30 through 4ee26 -> 4a974.  Stop: the consumer's
            successor or the first unrouted PC.
  node      the installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with declared BYTEs / WORDs.
  callee    the helpers and tails entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 8 consumers, the Z source of 4ee30 outside the four 4a974 BYTEs
            (decision 3), odd node / stack / A0, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired
            'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C5
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C5)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc6'
ERROR_PC = 'unsupported animation player c6 PC'
ERROR_CARRY = 'player c6 caller requires known carry'
ERROR_FLAG = 'unsupported animation player c6 flag source'

RANGES = [(0xb0c, 0xb58), (0x1d398, 0x1d3e0), (0x1d510, 0x1d582), (0x1d63a, 0x1d664), (0x1d698, 0x1d6c2), (0x1d90a, 0x1d940), (0x1daba, 0x1db0a),
          (0x1dbc6, 0x1dbd8), (0x1dc1a, 0x1dc84), (0x1dcd0, 0x1ddd0), (0x1e60a, 0x1e638), (0x1e65c, 0x1e67a), (0x1e824, 0x1e8de), (0x1eba0, 0x1ec74),
          (0x1efa4, 0x1efb0), (0x206cc, 0x206d2), (0x21564, 0x2156a), (0x21662, 0x21664), (0x481b2, 0x481de), (0x4838c, 0x48392), (0x4e572, 0x4e57a),
          (0x4e5b0, 0x4e5c2), (0x4e8f8, 0x4e8fc), (0x4eb58, 0x4eb6a), (0x4ed3c, 0x4ee7a), (0xe6496, 0xe6516)]
STARTS = sorted(int(x, 16) for x in (
    'b0c b2a b3c b40 b50 b56 1d398 1d3a0 1d3a8 1d3b0 1d3b8 1d3c0 1d3c8 1d3d0 1d3d8 1d510 1d514 1d51c 1d51e 1d52c 1d532 1d53e 1d546 1d54c 1d558 '
    '1d56a 1d574 1d580 1d63a 1d644 1d648 1d662 1d698 1d6a2 1d6a6 1d6c0 1d90a 1d914 1d91a 1d928 1d92e 1d934 1d938 1d93c 1daba 1dac2 1dace 1dad8 '
    '1dade 1dae6 1dae8 1daee 1daf2 1db06 1dbc6 1dbca 1dc1a 1dc20 1dc2a 1dc30 1dc36 1dc3a 1dc3c 1dc42 1dc62 1dc66 1dc6a 1dc70 1dc74 1dc7a 1dcd0 '
    '1dcd6 1dcde 1dce2 1dcea 1dcf6 1dd00 1dd06 1dd0e 1dd10 1dd16 1dd1a 1dd32 1dd36 1dd3e 1dd4a 1dd54 1dd5a 1dd62 1dd64 1dd6a 1dd6e 1dd84 1dd88 '
    '1dd8c 1dda4 1dda8 1ddac 1ddc4 1ddc8 1ddcc 1e60a 1e616 1e622 1e626 1e62e 1e630 1e65c 1e672 1e674 1e824 1e828 1e83e 1e87e 1e892 1e89e 1e8a8 '
    '1e8ae 1e8b4 1e8be 1e8c4 1e8c8 1e8d4 1e8da 1eba0 1eba8 1ebb2 1ebba 1ebbe 1ebc2 1ebf6 1ebfa 1ec04 1ec0c 1ec16 1ec1e 1ec28 1ec2c 1ec34 1ec3c '
    '1ec46 1ec50 1ec56 1ec60 1ec66 1ec6a 1ec70 1efa4 1efac 206cc 21564 21662 481b2 481be 481c2 4838c 4e572 4e5b0 4e8f8 4eb58 4eb60 4ed3c 4ed48 '
    '4ed4c 4ed54 4ed5e 4ed64 4ed6a 4ed70 4ed8c 4ed90 4ed9a 4eda4 4edaa 4edc0 4edc8 4edca 4edce 4edd4 4eddc 4ede6 4edec 4edf2 4ee04 4ee16 4ee1e '
    '4ee26 4ee30 4ee34 4ee3c 4ee44 4ee50 4ee5c 4ee68 4ee70 4ee78 e6496 e64a2 e64aa e64ae e64b8 e64c0 e64cc e64d2 e64de e64e6 e64f0 e64f4 e64fe '
    'e6506 e6510 e6514').split())
# the 8 C consumers: BCS 1d644 1d6a2 (49c38); BCC 1d934 (1d510 of C6), 1dc36 (4836e), 1dc62 1ebba (1cb08 of C2), 1ec66 (49fc6), 4ed8c (28ae)
CONSUMERS = (0x1d644, 0x1d6a2, 0x1d934, 0x1dc36, 0x1dc62, 0x1ebba, 0x1ec66, 0x4ed8c)
CLEAR_SET = (0x1d546, 0x1d54c)          # ANDI.B #fe,CCR; RTS / MOVE.L (A0,D1.W),D1 (MOVE clears C) of the LONG table 1d468
SET_SET = (0x1d574, 0x4838c)            # ORI.B #1,CCR; RTS
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x1d514,)                   # CMPI.W #14,D1; BCS.W 1d51e: the borrow (unsigned D1.W < 14) is the known C of both successors
INVERT_SET = ()
PASS_SET = (0x1d51c, 0x1d580)           # RTS (carry preserving: the C of 1d514 / 1d54c reaches the callers of 1d510)
STARTS_SET = set()
Z_READERS = (0x4ee30,)                  # BEQ.W on the Z of the TST.B (A0) that ends 4a974 (contract decision 3): never entered directly by a native run
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# (branch address, taken target) pairs that the original never takes: the bundled second BNE b26 repeats the Z of the first BNE b22 (the BTST of b1c);
# when b22 falls through Z = 1, so b26 never branches to b40 (its fall-through b2a is the only outcome)
BRANCH_IMPOSSIBLE = {(0xb26, 0xb40)}
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units (and deferred leaders) that a C6 block reaches by a fall-through, a branch or a call (the deferred leaders 1d3e0 4eb6a, C7 1f2a4,
# C8 1fa68 ea626), and the still unrouted later-unit stops of the C1..C5 blocks that the C6 runs pass through (pc5 EXIT_STOPS that are still unrouted;
# the TRAP site 4e69a of C1), and the two successors 1dc8e (C Set) / 1dccc (C Clear) of the routed interpreter stub 1dc84 / 1dc8a that 1dc7a returns
# to (JSR ce02 -> RTS 1dc84; outside every planned unit: the plan closure stops at the routed stub, contract "exits").  Declared stops of the native runs:
# a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1d3e0, 0x4eb6a, 0x1f2a4, 0x1fa68, 0xea626,
              0x1dc8e, 0x1dccc,
              0x208fa, 0x2210c, 0x1ef4c, 0x21d9e, 0x1efd6, 0x1f070, 0x21dd0, 0x223a0, 0x223d6, 0x4ef08, 0x1ce98, 0x1cfde, 0x1de3c, 0x1e21c, 0x1e8de,
              0x1fafc, 0x1fc96, 0x1fd50, 0x201bc, 0x21ca4, 0x21d0e, 0x21fa6, 0x4d0cc, 0x4e69a)
UNIT_EXITS = EXIT_STOPS[:5]             # the C6 later-unit stops and deferred leaders (1dc8e / 1dccc: through the stub 1dc84 only)
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to; the Z chain 4ee26 -> 4a974 -> 4ee30
CHAINS = ((0x1d63a, 0x1d644), (0x1d698, 0x1d6a2), (0x1d92e, 0x1d934), (0x1dc30, 0x1dc36), (0x1dc42, 0x1dc62), (0x1ebb2, 0x1ebba), (0x1ec60, 0x1ec66),
          (0x4ed70, 0x4ed8c), (0x4ee26, 0x4ee30))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()                           # no computed jump in C6
JUMP_ROUTED = ()
# computed jumps of C3 / C4 / C5 that the C6 runs reach (C3 2031c table, 201a6 JSR (A4) (from 1e8da / 1ec70 BRA 201a2), 21620 / 221de JMP (A1); C4
# 21c72 JMP (A1); C5 20792 2094e 209d6 21f7c): an unrouted target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c)
TABLE_ENTRIES = ()
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92)   # routed slot-84 states (C3 and C4 21d92) for the worlds
A4974 = (0x10fdb0, 0x10fdb1, 0x100004, 0x100005)                  # the BYTEs 4a974 leaves in A0 (the Z source of 4ee30)
# installed values entered as node callbacks; the callee entries (helpers and tails entered as subroutines; not the pass blocks 1d51c / 1d580: their
# readers are the callers of 1d510)
NODE_ENTRIES = (0x1dace, 0x1daee, 0x1dc20, 0x1dc70, 0x1dcf6, 0x1dd16, 0x1dd4a, 0x1dd6a, 0x1e89e, 0x1ebf6, 0x4edc0, 0x4ee04)
CALLEES = (0xb0c, 0x1d510, 0x1d63a, 0x1d698, 0x1e60a, 0x1e65c, 0x481b2, 0x4e5b0, 0xe6496, 0x1d398, 0x1d90a, 0x1daba, 0x1dbc6, 0x1dc1a, 0x1dcd0,
           0x1dce2, 0x1dd36, 0x1dd88, 0x1dda8, 0x1e824, 0x1eba0, 0x1efa4, 0x206cc, 0x21564, 0x21662, 0x4838c, 0x4e572, 0x4e8f8, 0x4eb58, 0x4ed3c)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('P1', 94, f) for f in (457, 458, 459, 490)] + [('P1', 106, f) for f in (458, 459)] +
                [('boot-title-start', None, f) for f in (577, 578, 579, 608, 610)] + [('boot-demo-0', None, f) for f in (407, 411, 492)])
NATURAL_CALLBACKS = (0x214d6, 0x4e94e, 0x1ef0e) + NODE_ENTRIES          # C5 214d6 -> 21564, C4 4e94e -> 4eb58 / 4ed3c, C4 1ef0e -> 1efa4
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node), extra (offset, size, value) writes on the node)
REINSTALL = (('boot-demo-0', None, 382, 0x100cb8, 0x1d1f4, ()),
             ('P1', 94, 459, 0x1009a8, 0x4ee04, ((0x96, 2, 0),)), ('P1', 94, 459, 0x1009a8, 0x4ee04, ((0x96, 2, 1), (0x9a, 1, 0x55))),
             ('P1', 94, 459, 0x1009a8, 0x4edc0, ((0x62, 1, 0),)), ('P1', 94, 459, 0x1009a8, 0x4edc0, ((0x62, 1, 1),)),
             ('P1', 94, 458, 0x100cb8, 0x1e89e, ((0x84, 4, 0x21602),)),
             ('P1', 94, 458, 0x100cb8, 0x1e89e, ((0x84, 4, 0x21602), (0x42, 2, 0x7fff), (0xae, 2, 0x8000))),
             ('P1', 94, 458, 0x100cb8, 0x1ebf6, ()), ('boot-demo-0', None, 411, 0x100cb8, 0x1ebf6, ((0x15, 1, 0),)),
             ('boot-demo-0', None, 411, 0x100cb8, 0x1dace, ((0xb0, 2, 0),)), ('boot-demo-0', None, 411, 0x100cb8, 0x1dcf6, ((0xb0, 2, 3),)),
             ('boot-demo-0', None, 411, 0x100cb8, 0x1dc20, ()), ('boot-demo-0', None, 411, 0x100cb8, 0x1daee, ()),
             ('boot-demo-0', None, 411, 0x100cb8, 0x1dd6a, ()), ('boot-title-start', None, 608, 0x1009a8, 0x4ee04, ((0x76, 2, 1),)))

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
BUNDLED = (0xb26, 0xe64b4)              # flag-sharing Bcc pairs inside one block: BNE b22 / BNE b26 (b0c), BHI e64b0 / BCS e64b4 (e64ae)


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the bundled second Bcc b26 / e64b4 stays in its block; 1d510 / 1dac2 / 1dcea / 1dd3e / 1dc1a / 1dc6a / 1dae8 / 1dd10 /
    1dd64 / 1e892 / 1ebc2 / 4edaa / 4edf2 / 1ec6a / 1e8d4 / e64aa / e64f0 / e6510 / b3c / b50 fall into the next start)."""
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
    """The PC after the entry block: pcs[n] (or the stop); a bundled Bcc pair (b0c, e64ae) uses pcs[n - 1] when its first Bcc was taken."""
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at an unrouted target of the
    C3 / C4 / C5 computed jumps that the C6 runs reach (OTHER_JUMP_PCS), or at the first unrouted PC that is not the straight-line successor of the
    previous instruction (a PC inside a block of another executor is not a block entry)."""
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it (as C1..C5): WORD 76 / 78(A6) mostly 0 / 1 (the
        player index: the BYTE slot 7db6(A5) + WORD 76, D0.W of b0c), D0.W 0 / 1 for a direct b0c entry and D1.B 0..3 (the request; the BYTE table
        b58 + 4 x D1.B + BYTE 10fdb6), D1.W mostly below 14 for 1d510 .. 1d54c (the LONG table 1d468) and the BYTE table 1d8ce, D7.W one of the types
        of 1d398, A0 = 10de14 / 10de1c (e6496) or the four 4a974 BYTEs, BYTE 9e(A6) 0..3 (C5 20796), LONG 84(A6) a routed slot-84 value (the C3 JSR
        (A4) 201a6 that 1e8da / 1ec70 reach), LONG 5434(A5) = 0 (C2 decision 2), BYTE 10fd82 = 0 (keeps 4a974 off the BIOS call c00450, not mapped
        natively), the BYTE slots 10fdb6 / 10fdb7 0..3, the LONG table 10f02e (10 LONGs, stride 8) and the LONGs 10de14 / 10de1c of e6496."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 8, 0x20, 0x22, 0x40, 0x80, 0xc, 0x50, 0x10, 0xffff, 0x12345678, 0x10000, 0x10001, 0x8000))   # input bits
        if rng.random() < 0.6:
            regs['d1'] = (regs['d1'] & 0xffff0000) | rng.choice((0, 1, 2, 3, 9, 0x11, 0x13, 0x14, 0xff, 0x8000))
        if rng.random() < 0.6:
            regs['d7'] = (regs['d7'] & 0xffff0000) | rng.choice((3, 5, 6, 7, 8, 9, 0xa, 0xb, 0xe, 0, 4, 0x8005))
        if entry in (0xb0c, 0xb2a, 0xb3c, 0xb40, 0xb50) and rng.random() < 0.85:
            regs['d0'] = (regs['d0'] & 0xffff0000) | rng.choice((0, 1))
            regs['d1'] = (regs['d1'] & 0xffffff00) | rng.randrange(4)
        writes = []
        regs['a0'] = self.pointer()
        if entry in (0xe6496, 0xe64d2, 0xe64de, 0xe64e6, 0xe64f0, 0xe64f4, 0xe64fe, 0xe6506) and rng.random() < 0.8:
            regs['a0'] = rng.choice((0x10de14, 0x10de1c))
        if entry in (0x1d54c, 0x1d532) and rng.random() < 0.6:
            regs['a0'] = 0x1d468                                  # the LONG table of 1d510 (ROM)
        if entry == 0x481c2 and rng.random() < 0.6:
            regs['a0'] = a5 + rng.choice((0x5694, 0x569c))
        if entry in (0xb2a, 0xb3c, 0xb40):
            regs['a0'] = 0x10fdb6
        regs['a1'] = 0xb58 if entry in (0xb2a, 0xb40) and rng.random() < 0.8 else self.pointer()
        if entry in (0xe64a2, 0xe64aa, 0xe64ae, 0xe64b8, 0xe64c0) and rng.random() < 0.7:
            regs['a1'] = 0x10f02e + 8 * rng.randrange(10)
            regs['d1'] = (regs['d1'] & 0xffff0000) | rng.randrange(1, 11)
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, self.pointer()))    # LONG 8c(A6) (A4 of C2 1cd98)
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of C2 1cb08 / C5 1cb1a / 1cb44)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(),))))   # LONG 3e(A6) (C2 1a9fe..1aa20)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): C3 2031c / C5 1cc1a
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): C3 206d4
        writes.append(((a6 + 0x9f) & 0xffff, 1, rng.randrange(9)))                        # BYTE 9f(A6): C2 1cb08
        writes.append(((a6 + 0x7c) & 0xffff, 2, rng.choice((0, 0x80, 0x180, 0x280, 0x281, 0x7fff, 0x8000, 0xfff0))))   # WORD 7c(A6): 1e626 / 4edaa
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x4000, 0xffff))))   # WORD 76(A6): the player slot
        writes.append(((a6 + 0x78) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x100))))        # WORD 78(A6): the player index
        writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                        # BYTE 9e(A6): C5 20796 (ROM writers 0..3), 1ec0c
        for node in (0x100cb8, 0x100da8):
            writes.append((node & 0xffff, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c))))   # 289e: CMPI.L #270e,(A0)
            writes.append(((node + 0x9e) & 0xffff, 1, rng.randrange(4)))
            writes.append(((node + 0x78) & 0xffff, 2, rng.choice((0, 1))))
        writes.append(((a5 + 0x5434) & 0xffff, 4, 0))                                     # LONG 5434(A5): A1 of the C2 JMP (A1) 1aa38 (0 in ROM)
        writes.append(((a5 + 0x5474) & 0xffff, 4, rng.choice((0, self.pointer()))))       # LONG 5474(A5): A0 of C2 1cd2a
        writes.append(((a5 + 0x5e26) & 0xffff, 4, self.pointer()))                        # LONG 5e26(A5): A4 of C3 e8b5a
        for k in (0, 4):
            writes.append(((a5 + 0x5734 + k) & 0xffff, 4, rng.choice((0, 0, self.pointer()))))   # 49c38: TST.L 5734(A5) + 4 x (D0.W & 1)
        for k in (0, 1):
            writes.append(((a5 + 0x7db6 + k) & 0xffff, 1, rng.choice((0, 1, 2, 3))))          # 4ee04: BYTE 7db6(A5) + WORD 76; b0c: BYTE 10fdb6 + D0.W
        writes.append((0xf006, 1, rng.getrandbits(8)))                                    # b0c: BTST.B D0,10f006.l
        writes.append((0xf007, 1, rng.getrandbits(8)))                                    # b0c: BCLR / BSET.B D0,10f007.l
        writes.append((0xfd8a, 1, rng.choice((0, 0, 1, 0x80))))                           # 4eb60: TST.B 10fd8a.l
        writes.append(((a5 + 0x7d82) & 0xffff, 1, rng.choice((0, 0, 1))))                 # 4ee1e
        writes.append(((a5 + 0x7004) & 0xffff, 1, rng.getrandbits(8)))                   # 4ee44: BTST.B D0,7004(A5)
        writes.append(((a5 + 0x5d1f) & 0xffff, 1, rng.choice((0, 0, 1, 2))))              # 4ee5c / C1 4e4da
        writes.append(((a5 + 0x5e13) & 0xffff, 1, rng.choice((0, 1))))                    # e64de / e64fe
        writes.append(((a5 + 0x5e12) & 0xffff, 1, rng.choice((0, 1))))
        long_pool = (0, 1, 0x100, 0x1000, 0x5000, 0x12345, 0x80000000, 0xffffffff)
        for k in range(10):
            writes.append(((0xf02e + 8 * k) & 0xffff, 4, rng.choice(long_pool)))          # e6496: the LONG table 10f02e (stride 8)
        for a in (0xde14, 0xde1c, (a5 + 0x5e14) & 0xffff, (a5 + 0x5e1c) & 0xffff):
            writes.append((a, 4, rng.choice(long_pool)))                                  # e6496: LONG (A0) and the LONGs 5e14 / 5e1c(A5)
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
    require(len(STARTS) == 212 and len(STARTS_SET) == 212, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c6_block', ('start is not routed to player c6', hex(s), unit_of(s)))
    for t in A4974:
        require(in_ram(t), ('4a974 BYTE in work RAM', hex(t)))
    rng = random.Random(0xC6A6)
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
    sys.stderr.write('pc6 spec: %d fixtures (%d natural), visited %d/212, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc6: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc6: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts





def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the BYTE bits and the
    BYTE table b58 index of b0c (D0 modulo 8, D1.B 0..3, BYTE 10fdb6 + D0.W; D0.W = ffff: a negative index), the CMPI.W types of 1d398, the CMPI.W #14
    borrow of 1d514, the stacked WORD / LONG of 1d532 / 1d92e, the LONG table 1d468 (D1.W = 2000: 4 x D1.W = 8000, a negative index into the ROM
    before the table), the BYTE table 1d8ce (D1.W = fff0), the SUBQ.W #1 borrow of the 15-frame counters, the BTST bits of D0 and of the node BYTEs,
    the WORD SUB.W / BMI / ADDQ.W #3 / ASR.W #2 / ADD.W of 1e626 .. 1e630, the WORD sum sign of 1e65c, the signed CMP.W / BLE of 1e8c8, the signed
    TST.B / BGT of 1eba0, the AND.W masks of 1ec1e / 1ec3c / 1ec46, the BYTE table 4e4d2 index of 4e5b0, the BYTE slot 7db6(A5) + sext(WORD 76) of
    4ee04, the WORD 96 count, the BTST.B D0,7004(A5) bit, the CMP.B / MOVE.B of 4ee5c / 4ee68, the unsigned LONG compares and the signed WORD loop bound
    of e6496 .. e6510), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture
    (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x1d648, 0x1d6a6, 0x1d51e, 0x1d532, 0x1d54c, 0x1d558, 0x1d56a, 0x1daf2, 0x1dd1a, 0x1dd6e, 0x1dd8c, 0x1ddac, 0x1e60a, 0x1e616, 0x1e622,
                 0x1e65c, 0x1e83e, 0x1e8a8, 0x1e8c8, 0x481b2, 0x481c2, 0x4e572, 0x4e5b0, 0x4eb58, 0x4ed3c, 0x4ee50, 0x4edaa, 0x4ee04, 0x4ee5c, 0xe6496):
        h += [dict(regs=dict(up))]
    # ---- b0c .. b56
    if entry == 0xb0c:
        for d0, d1, f6, f7, s0, s1 in ((0, 3, 0x00, 0xff, 0, 1), (1, 3, 0x02, 0x00, 2, 3), (0, 0, 0x01, 0x01, 1, 0), (1, 0, 0x00, 0xff, 3, 3),
                                       (7, 3, 0x80, 0x00, 0, 0), (8, 3, 0x00, 0x01, 2, 0), (0x12340001, 0x9abcde03, 0xfd, 0xfe, 1, 2),
                                       (0xffff, 2, 0x7f, 0x80, 1, 1)):
            h.append(dict(regs=dict(d0=d0, d1=d1), writes=[(0xf006, 1, f6), (0xf007, 1, f7), (0xfdb6, 1, s0), (0xfdb7, 1, s1), (0xfdb5, 1, 2)]))
    if entry in (0xb2a, 0xb40):
        for d0, d1, s in ((0, 0, 0), (0, 3, 1), (1, 3, 3), (1, 1, 2), (0, 2, 0xff), (0xffff, 0x9abcde03, 2), (0x12340001, 0x12345601, 0x80)):
            h.append(dict(regs=dict(d0=d0, d1=d1, a0=0x10fdb6, a1=0xb58, d7=0x99aabbcc), writes=[(0xfdb6 + (d0 & 0xffff) - (0x10000 if d0 & 0x8000 else 0), 1, s)]))
    if entry == 0xb3c:
        h += [dict(regs=dict(d0=d0, d1=0x12345603, a0=0x10fdb6)) for d0 in (0, 1, 0xffff, 0x10001)]
    if entry == 0xb50:
        h += [dict(regs=dict(d0=d0), writes=[(0xf007, 1, 0)]) for d0 in (0, 1, 7, 8, 0x1f)]
    # ---- 1d398 .. 1d3d8
    if entry in (0x1d398, 0x1d3a0, 0x1d3a8, 0x1d3b0, 0x1d3b8, 0x1d3c0, 0x1d3c8, 0x1d3d0, 0x1d3d8):
        h += regs('d7', (3, 5, 6, 7, 8, 9, 0xa, 0xb, 0xe, 0x10005, 0xffff0003, 0, 4, 0x8005))
    # ---- 1d510 .. 1d580
    if entry in (0x1d510, 0x1d514):
        h += regs('d1', (0, 0x13, 0x14, 0xffff, 0x10013, 0x12340014, 0x8000))
    if entry == 0x1d532:
        for w, d0 in ((9, 8), (9, 0), (0x13, 8), (0x10, 0xfffffff7), (0x8009, 8)):
            h.append(dict(regs=dict(up, d0=d0), stack=[(0, 2, w), (2, 4, 0x1d468), (6, 4, SENTINEL)]))
    if entry == 0x1d53e:
        h += regs('d1', (9, 0x10009, 0xfff9, 8))
    if entry == 0x1d54c:
        h += [dict(regs=dict(up, d1=v, a0=0x1d468)) for v in (0, 1, 4, 9, 0x11, 0x13, 0x2000, 0x4000, 0x12340001, 0x12)]
    if entry == 0x1d574:
        h += word(0x78, (0, 1, 0x8000)) + mirror
    # ---- 1d63a .. 1d6c0
    if entry in (0x1d648, 0x1d6a6):
        for v, w in ((0x100, 0x40), (0x40, 0x100), (0x8000, 1), (0, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x42, 2, v), (0x46, 2, v)], a5off=[(0x53a2, 2, w), (0x53a6, 2, w)]))
    # ---- 1d90a .. 1d93c
    if entry == 0x1d914:
        h += regs('d1', (0, 1, 0x10000, 0x8000))
    if entry == 0x1d91a:
        h += [dict(regs=dict(up, d1=v)) for v in (0, 4, 5, 9, 0xa, 0x13, 0xfff0, 0x12340005)]
    if entry == 0x1d92e:
        h += [dict(stack=[(0, 2, w), (2, 4, SENTINEL)]) for w in (0, 4, 9, 0x14, 0xffff)]
    # ---- 1daba .. 1ddcc
    if entry in (0x1daba, 0x1dce2, 0x1dd36):
        h += word(0x78, (0, 1, 0x100, 0x8000))
    if entry in (0x1dade, 0x1dd06, 0x1dd5a):
        h += word(0xb0, (0, 1, 2, 0x8000, 0xffff))
    if entry in (0x1dac2, 0x1dcea, 0x1dd3e, 0x1dae8, 0x1dd10, 0x1dd64, 0x1dc1a, 0x1dc6a, 0x1e892, 0x1ebc2, 0x4edf2, 0x1ec6a, 0x1e8d4):
        h += mirror
    if entry == 0x1dbca:
        h += byte(0xa7, (0, 0x80, 0x7f, 0xff)) + mirror
    if entry == 0x1dc42:
        h += [dict(regs=dict(up))] + mirror
    if entry == 0x1dcd6:
        h += regs('d0', (0x40, 0, 0xffffffbf, 0x12345640))
    # ---- 1e60a .. 1e674
    if entry in (0x1e60a, 0x1e616):
        h += regs('d0', (0, 1, 2, 3, 0xfffffffc, 0x12345601))
    if entry == 0x1e626:
        for d1, w in ((0x280, 0x280), (0x280, 0x281), (0x80, 0x8000), (0x180, 0x7fff), (0x9abc0180, 0x17d), (0x8000, 0)):
            h.append(dict(regs=dict(d1=d1), a6off=[(0x7c, 2, w)]))
    if entry == 0x1e62e:
        h += regs('d1', (0xfffd, 0x7ffc, 0x12340001, 0xffff))
    if entry == 0x1e630:
        for d1, w in ((0xfffd, 0x10), (0x8000, 0x7fff), (3, 0), (4, 0xffff), (0x7fff, 0x8000), (0xfffc, 1), (0x12348003, 0x100)):
            h.append(dict(regs=dict(d1=d1), a6off=[(0x7c, 2, w)]))
    if entry == 0x1e65c:
        for v42, v4a, v2, va in ((0x100, 0x80, 0x80, 0), (0x100, 0x80, 0x81, 0), (0x100, 0x80, 0x81, 1), (0x7fff, 0, 0, 1), (0, 0, 0, 0), (0x8000, 0, 0, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x42, 2, v42), (0x4a, 2, v4a)], a5off=[(0x53a2, 2, v2), (0x53aa, 2, va)]))
    if entry == 0x1e674:
        h += regs('d0', (9, 0xa, 0x12345609)) + mirror
    if entry in (0x1e828, 0x1e83e, 0x1e87e):
        h += [dict(a6off=[(0xa7, 1, 0xfb), (0x15, 1, 0xff)])] + mirror
    if entry == 0x1e8c8:
        for v, w in ((5, 5), (4, 5), (6, 5), (0x7fff, 0x8000), (0x8000, 0x7fff), (0xffff, 0), (0, 0xffff)):
            h.append(dict(regs=dict(up), a6off=[(0x42, 2, v), (0xae, 2, w)]))
    # ---- 1eba0 .. 1ec70, 1efa4
    if entry == 0x1eba0:
        h += byte(0x9d, (0, 1, 0x7f, 0x80, 0xff))
    if entry == 0x1eba8:
        h += byte(0xa7, (0x20, 0xdf, 0, 0xff))
    if entry == 0x1ebfa:
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry in (0x1ec04, 0x1ec0c, 0x1ec16, 0x1ec1e, 0x1ec2c, 0x1ec34, 0x1ec3c, 0x1ec46):
        h += [dict(regs=dict(up, d0=v)) for v in (0x20, 0x22, 0, 2, 0x80, 4, 8, 0xc, 0x10, 0x40, 0x50, 0x12340000, 0xffffffaf)]
    if entry == 0x1ec0c:
        h += [dict(regs=dict(d0=0x22), a6off=[(0x9e, 1, v)]) for v in (0, 1, 0x80)]
    if entry == 0x1efa4:
        h += word(0x88, (0, 1, 0x100, 0x8000))
    if entry == 0x206cc:
        h += byte(0xa7, (0, 0xfe, 0xff)) + mirror
    # ---- 481b2 .. 4838c, 4e572 .. 4eb60
    if entry == 0x481b2:
        h += regs('d0', (0, 1, 0x12340001, 0xfffe))
    if entry == 0x481c2:
        h += [dict(regs=dict(up, a0=0x108000 + v), writes=[((0x8000 + v) & 0xffff, 4, 0x8182ff01), ((0x8004 + v) & 0xffff, 4, 0x80017fff)]) for v in (0x5694, 0x569c)]
    if entry == 0x4e572:
        h += regs('d0', (0, 0xffe0, 0x1234ffff, 0x8000))
    if entry == 0x4e5b0:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 2, 3, 4, 7, 0x100, 0x12345603, 0x1ff)]
    if entry == 0x4eb58:
        h += byte(0x98, (0, 1, 2, 3, 7))
    if entry == 0x4eb60:
        h += [dict(writes=[(0xfd8a, 1, v)]) for v in (0, 1, 0x80)]
    # ---- 4ed3c .. 4ee78
    if entry in (0x4ed3c, 0x4ee50, 0x4ed4c, 0x4edd4):
        h += word(0x76, (0, 1, 0x8000, 0x100))
    if entry == 0x4ed6a:
        h += regs('d0', (0x8000, 0x7fff, 0xffff8000, 0x8000ffff, 0))
    if entry == 0x4ed70:
        h += [dict(writes=[(0x4ca0, 2, v)]) for v in (0x100, 0, 0x15)] + mirror
    if entry == 0x4ed90:
        h += [dict(regs=dict(a0=0x10e980), a6off=[(0x76, 2, v)]) for v in (0, 1, 0x8000)]
    if entry == 0x4edaa:
        h += [dict(regs=dict(up, a0=0x10e980, a1=0x10de20), a6off=[(0x7c, 2, v)]) for v in (0, 0xffc0, 0x7fc0, 0x1234)]
    if entry == 0x4edc0:
        h += byte(0x62, (0, 1, 0x80))
    if entry == 0x4ee04:
        for w, b in ((0, 0), (0, 1), (1, 2), (1, 0), (0xffff, 1), (0xffff, 2), (0x8000, 3)):
            h.append(dict(regs=dict(up), a6off=[(0x76, 2, w)], a5off=[((0x7db6 + w - (0x10000 if w & 0x8000 else 0)) & 0xffff, 1, b)]))
    if entry == 0x4ee16:
        h += regs('d0', (1, 0x101, 2, 0xff))
    if entry == 0x4ee1e:
        h += [dict(a5off=[(0x7d82, 1, v)]) for v in (0, 1, 0x80)]
    if entry in (0x4ee34, 0x4ee3c):
        h += word(0x96, (0, 1, 2, 0x8000))
    if entry == 0x4ee44:
        for w, b in ((0, 1), (0, 0xfe), (1, 2), (1, 0xfd), (7, 0x80), (8, 1), (0x8001, 2)):
            h.append(dict(a6off=[(0x76, 2, w)], a5off=[(0x7004, 1, b)]))
    if entry == 0x4ee5c:
        for v, w in ((0, 0), (1, 1), (1, 0), (0, 1), (0x80, 0x80), (2, 0xff)):
            h.append(dict(regs=dict(up), a6off=[(0x9a, 1, w)], a5off=[(0x5d1f, 1, v)]))
    if entry == 0x4ee68:
        h += regs('d0', (0, 0x100, 5, 0x12345600)) + mirror
    # ---- e6496 .. e6514
    if entry == 0xe6496:
        for a0, v, tab in ((0x10de14, 0x5000, (0x9000, 0x8000, 0x6000, 0x5000, 0x4000)), (0x10de1c, 0x10000, (0x10000,) * 10),
                           (0x10de14, 0, (0x100,) * 10), (0x10de1c, 0xffffffff, (0x80000000, 0x7fffffff)), (0x10de14, 0x7000, (0x9000, 0x8000))):
            ws = [((a0 & 0xffff), 4, v)] + [((0xf02e + 8 * k) & 0xffff, 4, x) for k, x in enumerate(tab)]
            h.append(dict(regs=dict(up, a0=a0), writes=ws))
    if entry in (0xe64a2, 0xe64ae):
        for d3, d4, d1 in ((5, 5, 3), (5, 5, 0xa), (6, 5, 1), (4, 5, 1), (0x80000000, 0x7fffffff, 2), (0x7fffffff, 0x80000000, 9), (5, 5, 0x10000)):
            h.append(dict(regs=dict(d3=d3, d4=d4, d1=d1, d0=0x12340001, a1=0x10f02e), writes=[(0xf02e, 4, d4)]))
    if entry in (0xe64aa, 0xe64b8):
        h += regs('d1', (9, 0xa, 0xb, 0x1000a, 0x12340003))
    if entry == 0xe64c0:
        h += [dict(regs=dict(d1=v, a1=0x10f02e)) for v in (9, 0xa, 0xb, 0x1000a, 0xfff0, 0x7fff)]
    if entry in (0xe64d2, 0xe64f4):
        for a0, d1 in ((0x10de14, 1), (0x10de1c, 0), (0x10de14, 0x10000), (0x1de14, 3), (0x10de1d, 5), (0x1010de1c, 2)):
            h.append(dict(regs=dict(a0=a0, d1=d1, d0=0x1234ffff)))
    if entry in (0xe64de, 0xe64e6, 0xe64fe, 0xe6506):
        for a0, f3, f2, v, lim in ((0x10de14, 1, 1, 5, 6), (0x10de14, 1, 1, 6, 6), (0x10de1c, 1, 1, 7, 6), (0x10de1c, 0, 1, 0x80000000, 0x7fffffff),
                                  (0x10de14, 1, 0, 0, 1), (0x10de1c, 1, 1, 0xffffffff, 0)):
            h.append(dict(regs=dict(a0=a0, d0=0x1234ffff, d1=0x5678ffff), writes=[(a0 & 0xffff, 4, v)],
                          a5off=[(0x5e13, 1, f3), (0x5e12, 1, f2), (0x5e1c, 4, lim), (0x5e14, 4, lim)]))
    if entry in (0xe64f0, 0xe6510):
        h += [dict(regs=dict(d0=d0, d1=d1)) for d0, d1 in ((0xffff, 0x1234ffff), (0x12340001, 0x7fff), (0, 0))]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry in (0x1d63a, 0x1d698):
        w = (0, 1, 0x8000, 0xffff)[t % 4]
        return dict(a6off=[(0x78, 2, w)], a5off=[(0x5734 + 4 * (w & 1), 4, (0, 0x10e400)[(t // 4) % 2])])   # 49c38: TST.L 5734(A5) + 4 (D0.W & 1)
    if entry == 0x1d92e:
        # 1d510 with D1.W = the stacked WORD: >= 14 -> Clear (1d51c); else 481b2 / 4d50e / 1aa3a and the LONG table 1d468 (ROM: 2b7c6 at 1, 330a4 at 4,
        # 3064a at 9, 38b38 at 11, 3fd0e at 13, 0 elsewhere) -> Clear (1d546 / 1d580) or Set (1d574 after 2986 / 49214)
        return dict(stack=[(0, 2, (0x14, 1, 4, 9, 2, 0x11, 0x13, 0x30, 0, 5)[t % 10]), (2, 4, SENTINEL)])
    if entry == 0x1dc30:
        return dict(a5off=[(0x5683, 1, (0, 4, 0xfb, 0xff)[t % 4])])                    # 4836e: BTST #2,5683(A5)
    if entry in (0x1dc42, 0x1ebb2):
        # 1cb08: W = WORD (table + 2 x BYTE 9f); 0 -> Clear; else C5 1cb1a: TST.L (LONG 22(A6) + 4 x WORD (table + W)) -> Clear / Set
        table = 0x1b1b0 if entry == 0x1dc42 else 0x1b1ca
        k = (t // 2) % 5
        w = rom_word(table + 2 * k)
        idx = (4 * rom_word(table + w)) & 0xffff if w else 0
        return dict(a6off=[(0x9f, 1, k), (0x22, 4, SCR)], writes=[((SCR + idx) & 0xffff, 4, (0, 0x12345678)[t % 2])] if idx < 0x400 else [])
    if entry == 0x1ec60 and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> Set
    if entry == 0x4ed70:
        return dict(writes=[(0x4ca0, 2, (0x100, 0x15, 0x40, 0)[t % 4])])                 # 28ae: D0.W 0 below the WORD 104ca0 -> a node (Set), else Clear
    if entry == 0x4ee26:
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), WORD 78 / 76 (the player index / slot), WORD b0 (the 15-frame counters), BYTE 15 bit 7 (1ebfa), BYTE 62
            # (4edc0), WORD 96 (4ee34), BYTE 9a (4ee5c), WORD 42 / ae (1e8c8), LONG 26 (0: 49fc6 Set), WORD 104ca0 (28ae count limit)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x78, 2, (0, 1)[t % 2]), (0x76, 2, (0, 1)[(t // 2) % 2]), (0xb0, 2, (0, 1, 5)[t % 3]),
                               (0x15, 1, (0, 0x80, 1, 0x81)[t % 4]), (0x62, 1, (0, 1)[(t // 3) % 2]), (0x96, 2, (0, 1)[(t // 2) % 2]),
                               (0x9a, 1, (0, 1, 0x55)[t % 3]), (0x42, 2, (0x100, 0x140)[(t // 5) % 2]), (0xae, 2, (0x100, 0x120)[(t // 7) % 2])] +
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
    err('odd-pc', U.with_host_writes(st, pc=0xb0d), 'unaligned animation machine PC', 0xb0d)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the Z source of 4ee30 (contract decision 3): A0 is not one of the four BYTEs 4a974 leaves (10fdb0 / 10fdb1 / 100004 / 100005)
    for v in (0x10fdb2, 0x100003, 0x100006, 0x11fdb0, 0x3c0000, 0x10fdaf):
        err('4ee30-a0-%x' % v, U.with_host_writes(st, regs=dict(a0=v), pc=0x4ee30), ERROR_FLAG, 0x4ee30)
    # odd node / stack / A0: the entry block fails (the row's stop is the PC right after the failing block)
    err('1d63a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1d63a), odd_word, 0x1d63a, stop=0x49c38)
    err('1e83e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1e83e), odd_write, 0x1e83e, stop=0x43e08)
    err('1dac2-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1dac2), odd_write, 0x1dac2, stop=0x1dace)
    err('1d51e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d51e), odd_word, 0x1d51e, stop=0x481b2)
    err('1d532-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d532), odd_word, 0x1d532, stop=0x1d54c)
    err('1d92e-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d92e), odd_word, 0x1d92e, stop=0x1d510)
    err('e6496-odd-a0', U.with_host_writes(st, regs=dict(a0=0x10de15), pc=0xe6496), odd_word, 0xe6496, stop=0xe64a2)
    err('4ed90-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x4ed90), odd_write, 0x4ed90, stop=0x4ed9a)
    err('481c2-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x481c2), odd_word, 0x481c2, stop=0x4d50e)
    # failures after executed blocks:
    #   1d398 (D7.W = 0) -> the type chain -> 1d3e0 (deferred leader, unrouted)
    err('1d398-then-1d3e0', U.with_host_writes(st, regs=dict(d7=0), pc=0x1d398), unrouted, 0x1d3e0)
    #   4eb58 (BYTE 10fd8a = 1) -> 4e5b0 -> 4eb60 -> 4eb6a (deferred leader, unrouted)
    err('4eb58-then-4eb6a', U.with_host_writes(st, [(0xfd8a, 1, 1)], regs=dict(d0=0), pc=0x4eb58), unrouted, 0x4eb6a)
    #   1ec2c (D0 bit 1) -> 1f2a4 (C7, unrouted); 1ec3c path: 1ec1e (D0 & c) -> 1fa68 (C8, unrouted)
    err('1ec2c-then-1f2a4', U.with_host_writes(st, regs=dict(d0=2), pc=0x1ec2c), unrouted, 0x1f2a4)
    err('1ec1e-then-1fa68', U.with_host_writes(st, regs=dict(d0=0xc), pc=0x1ec1e), unrouted, 0x1fa68)
    #   1dad8 -> JSR ea626 (C8, unrouted)
    err('1dad8-then-ea626', U.with_host_writes(st, pc=0x1dad8), unrouted, 0xea626)
    #   b0c -> ... -> b56 RTS at an odd A7
    err('b0c-then-b56', U.with_host_writes(st, regs=dict(a7=a7 + 1, d0=0, d1=0), pc=0xb0c), odd_word, 0xb56)
    #   1e60a (D0 bit 0) -> 1e626 -> 1e62e / 1e630 RTS at an odd A7
    err('1e60a-then-1e630', U.with_host_writes(st, [((a6 + 0x7c) & 0xffff, 2, 0)], regs=dict(a7=a7 + 1, d0=1), pc=0x1e60a), odd_word, 0x1e630)
    #   1d514 (D1.W = 14) -> 1d51c RTS at an odd A7
    err('1d514-then-1d51c', U.with_host_writes(st, regs=dict(a7=a7 + 1, d1=0x14), pc=0x1d514), odd_word, 0x1d51c)
    #   1d54c (A0 = 1d468, D1.W = 0: the LONG 0) -> 1d580 RTS at an odd A7
    err('1d54c-then-1d580', U.with_host_writes(st, regs=dict(a7=a7 + 1, d1=0, a0=0x1d468), pc=0x1d54c), odd_word, 0x1d580)
    #   e6496 (LONG (A0) = 0, every table LONG 0) -> the loop to D1 = a -> e64cc RTS at an odd A7
    err('e6496-then-e64cc', U.with_host_writes(st, [(0xde14, 4, 0)] + [((0xf02e + 8 * k) & 0xffff, 4, 0) for k in range(10)],
                                               regs=dict(a7=a7 + 1, a0=0x10de14), pc=0xe6496), odd_word, 0xe64cc)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x1e630, 0x1e65c, 0xe6496, 0x1ebc2)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
