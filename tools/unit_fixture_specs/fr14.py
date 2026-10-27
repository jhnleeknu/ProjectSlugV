"""V1 fixture spec of the area-D unit FR14 (engine/src/animation_machine_objects_fr14.cpp, 200 block starts).

Blocks (contract docs/analysis/animation-machine-frontier-fr14-contract.md, plan docs/analysis/area-c-completion-plan.md section 10.5 FR14 row): the
last area-D code that the extended-input IO observation reaches -- the C5 2986 child 3643e (table 1cc04 entry 1: 1aa3a bit 3, the WORD 76 anim tables
363ae / 36522, the sound table 363be, the 1/16 approach 364aa / 36588 of LONG 36 / 3a (ASR.L #4), BSET #3,61, the 1ab80 screen test of the record
363a6; 3657c is also the BRA.W target of the unrouted 2986 child 365fc of C5 1cc88), the FR12 / FR13 later-unit fall-throughs 7177a / 71786 / 71874
(NEG.L D0) and d1632 (NEG.W D0; NEG.L D1), the stage-event op 08 child b5c34 (b5c60 .. b5d56, the install b5cec, the helpers b6056 / b6084 / b60c4,
the LONG table b6280 by BYTE 8a, the player test b60da (49392 / 4941e; b6128 Clear, b6146 Set) with the counters b7ae4 / b7af0 (MOVEM.L D0/A2-A3),
b6038 (1aa7e)), the FR1 kind-record handler c0d68 (signed WORD 42, c6a96, the install c0dc8 with b4958 / b4ab0 / b4334), the FR4 table cc7ac entry 3
cc7b8 (-> cd0fe: the BYTE 5f / BYTE 15 bit 0 sign test, BYTE 7a, the WORD 8c anim selection, cdd2e written) and the FR13 later-unit stop d177e
(4ae4a, 8ff4, the install d17e0).  No computed jump of its own; 12 C consumers (two with in-unit producers b6128 / b6146).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR13, C1..C10, E1, E2) with
declared host edits.  This code runs natively only in the extended-input IO observation (artifacts/animation_machine_io_ext, runs X2 94, X3 68,
X3 94): the 'natural' family takes the frame-start states of that observation (state packs, read-only) in which a node of the pool 100800..104c00
holds an FR14 node entry (or a routed callback whose run reaches FR14 code: NATURAL_ROUTED) as its callback LONG, keeps their RAM / PVC / bank and
declares only the registers (A5 = 108000, A6 = the node, A7 = 10ef00 with the sentinel return LONG, PC = the callback); the 'reinstall' family writes
the declared callback LONG of an FR14 entry that never stays at a frame start (the 2986 children 3643e / b5c34, the handler c0d68, the table entry
cc7b8, the later-unit stop d177e, the BRA.W target 3657c) into the natural node of the frame after (REINSTALL).  The spec reads those packs itself
(io_pack below, observation directory IO_EXT); the shared loader is unchanged.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 12 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the
            unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the successor or the first unrouted PC.
  node      the callbacks and installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes and the reinstall worlds (see Seeds) up to the sentinel or the first unrouted PC.
  callee    the later-unit successors, table entries, handlers and helpers entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 12 consumers, odd node / stack / A1, fixed-ROM writes, failures
            after executed blocks: checked error, state preserved, every row with its failing PC (a paired 'failpc' match row when it differs from the
            entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR13, C1..C10,
E2 specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR13, C1..C10)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'fr14'
ERROR_PC = 'unsupported animation objects fr14 PC'
ERROR_CARRY = 'objects fr14 caller requires known carry'
IO_EXT = 'artifacts/animation_machine_io_ext'   # the extended-input IO observation (read-only state packs of the natural family)

RANGES = [(0x3643e, 0x36522), (0x36532, 0x365d0), (0x365d4, 0x365fc), (0x7177a, 0x7177c), (0x71786, 0x71788), (0x71874, 0x71876), (0xb5c34, 0xb5c4c),
          (0xb5c60, 0xb5d5a), (0xb6038, 0xb604e), (0xb6056, 0xb614c), (0xb7ae4, 0xb7b30), (0xc0d68, 0xc0e2a), (0xcc7b8, 0xcc7bc), (0xcd0fe, 0xcd370),
          (0xd1632, 0xd1636), (0xd177e, 0xd17f8)]
STARTS = sorted(int(x, 16) for x in (
    '3643e 36452 3645a 36474 3648c 3649e 364a0 364aa 364ba 364c0 364ce 364d4 364e4 364f0 364fa 36500 36502 3650c 36516 3651a 36520 36532 3654c '
    '36564 36576 36578 3657c 36588 36598 3659e 365ac 365b2 365c0 365ca 365d4 365da 365e0 365e6 365f0 365f4 365fa 7177a 71786 71874 b5c34 b5c48 '
    'b5c60 b5c68 b5c78 b5c84 b5c9a b5cb2 b5ce6 b5cec b5cf0 b5cf6 b5d02 b5d2a b5d30 b5d34 b5d3a b5d3e b5d42 b5d48 b5d50 b5d56 b6038 b6042 b6046 '
    'b604c b6056 b6060 b6066 b606a b6070 b607a b6082 b6084 b608e b6092 b6098 b60a2 b60a4 b60b0 b60b4 b60c2 b60c4 b60d2 b60d4 b60da b60e4 b60ec '
    'b60f0 b60fa b60fe b6104 b610e b6112 b611c b6120 b6128 b612e b6136 b613c b6140 b6146 b7ae4 b7af0 b7af8 b7b02 b7b0a b7b10 b7b18 b7b1e b7b28 '
    'b7b2c b7b2e c0d68 c0d7a c0d82 c0d88 c0d9a c0dc2 c0dc8 c0dd2 c0dd8 c0ddc c0de2 c0de8 c0dee c0df6 c0dfc c0e00 c0e28 cc7b8 cd0fe cd110 cd118 '
    'cd12e cd132 cd13a cd150 cd154 cd15c cd172 cd176 cd17e cd194 cd198 cd1a0 cd1b6 cd1ba cd1d0 cd1d4 cd1dc cd1e4 cd1fa cd1fe cd206 cd21c cd220 '
    'cd228 cd23e cd242 cd24a cd260 cd264 cd26c cd282 cd286 cd29c cd2a0 cd2a8 cd2be cd2c2 cd2ca cd2e0 cd2e4 cd2ec cd302 cd306 cd30e cd324 cd328 '
    'cd330 cd346 cd34a cd360 d1632 d177e d178a d1792 d1798 d17cc d17da d17e0 d17e6 d17ec d17f0 d17f6'
    ).split())
# the 12 C consumers: BCC 36516 365f0 (1ab80), b5d30 (4b54e), b5d3e (b60da), b6042 (1aa7e), b60ec b610e (49392), BCS b60fa b611c (4941e), b7b02
# (MOVEM.L (A7)+ then BCC: 49392), BCC c0dfc (b4334), d17ec (49fc6)
CONSUMERS = (0x36516, 0x365f0, 0xb5d30, 0xb5d3e, 0xb6042, 0xb60ec, 0xb60fa, 0xb610e, 0xb611c, 0xb7b02, 0xc0dfc, 0xd17ec)
CLEAR_SET = (0xb6128,)                  # ANDI.B #fe,CCR; RTS (the C Clear returned by b60da)
SET_SET = (0xb6146,)                    # ORI.B #1,CCR; RTS (the C Set returned by b60da)
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()
STARTS_SET = set()
Z_READERS = ()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = {(0xd177e, 0xd1792)}    # LEA d1cba.l,A0; MOVE.L A0,D0; BEQ.W d1792: the constant d1cba is never 0
BRANCH_IMPOSSIBLE = {(0xd1786, 0xd1792)}
LATER_GATED = set()
GATED_CONSUMERS = ()
# no TRAP in FR14; the FR11 TRAP #15 b3e58 and the FR1 TRAP #15 b3eac stay declared boundaries of the routed handlers that the natural runs may pass
TRAPS = (0xb3e58, 0xb3eac)
# no later-unit stop of FR14 (the last IO unit); the still unrouted later-unit stops of the C1..C9 blocks (pc10 EXIT_STOPS[:12]).  Declared stops of the
# native runs: a straight-line unrouted PC after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1fd3c, 0x21ea0, 0x1d3e0, 0x4eb6a, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21fa6, 0x4e69a,
              # player C11 routes the C3 list handler 21950 and the slot-84 values 21960 21a76 since C11 (declared stops, as before C11)
              0x21950, 0x21960, 0x21a76)
UNIT_EXITS = ()                         # no FR14 later-unit stop
# player C11 routes 1d3e0 4eb6a 1e8de since C11 (declared stops of the FR14 runs, as before C11)
ROUTED_LATER = (0x1d3e0, 0x4eb6a, 0x1e8de,
                # player C11 (the C3 list handler / slot-84 values kept as declared stops)
                0x21950, 0x21960, 0x21a76)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x3650c, 0x36516), (0x365e6, 0x365f0), (0xb5d2a, 0xb5d30), (0xb5d3a, 0xb5d3e), (0xb6038, 0xb6042), (0xb60e4, 0xb60ec), (0xb60f0, 0xb60fa),
          (0xb6104, 0xb610e), (0xb6112, 0xb611c), (0xb7af8, 0xb7b02), (0xc0df6, 0xc0dfc), (0xd17e6, 0xd17ec))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_TARGETS = {}
JUMP_PCS = ()
JUMP_ROUTED = ()
LIST_JUMPS = {}
# computed jumps that the FR14 runs reach (FR13 cc8da, FR11 b4034 / b42b4 / c54ae, FR1 b3dc8 b3f3e b3fc4 b3fca (the item child b3dbc and its kind
# handlers), FR2 b46aa (item handler JSR (A1)), FR4 cc7a8 / cc82a (the cc778 tail: cc7b8 is an FR14 block), the interpreter JSR (A1) 4a352 / 4a43c,
# the C3 .. C10 list): an unrouted target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0xcc8da, 0xb4034, 0xb42b4, 0xc54ae, 0xb3dc8, 0xb3f3e, 0xb3fc4, 0xb3fca, 0xb46aa, 0xcc7a8, 0xcc82a, 0x4a352, 0x4a43c, 0x2031c, 0x201a6,
                  0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76, 0x21ce4, 0x21d36, 0x2224c, 0x22428, 0x21e10,
                  0x2229a, 0x22378, 0x203ac)
TABLE_ENTRIES = ()
# the callbacks and installed values entered as node callbacks: the 2986 children 3643e (C5 1cc38) / b5c34 (the stage-event op 08 table e8cc0), the
# in-range installs entered at once 364aa 36588 b5cec c0dc8 d17e0 (also the next frame's callback)
NODE_ENTRIES = (0x3643e, 0x364aa, 0x36588, 0xb5c34, 0xb5cec, 0xc0dc8, 0xd17e0)
# the natural family also takes the routed callbacks whose code leads into FR14 at the first-execution frames (NATURAL_ROUTED): FR13 d176e (d177a ->
# d177e), FR12 716ca (71776 -> 7177a, 71782 -> 71786), FR13 717e8 (71870 -> 71874), FR13 d15c4 (d162e -> d1632), and the callbacks of the frame in
# which the cc778 tail first reaches cc7b8 (76984 76d94 cd8ee cdd2e)
NATURAL_ROUTED = (0xd176e, 0x716ca, 0x717e8, 0xd15c4, 0x76984, 0x76d94, 0xcd8ee, 0xcdd2e)
NATURAL_ENTRIES = NODE_ENTRIES + NATURAL_ROUTED
# the later-unit successors, table entries, handlers, callbacks and helpers entered as subroutines (return LONG = sentinel)
CALLEES = (0x7177a, 0x71786, 0x71874, 0xd1632, 0xd177e, 0xcc7b8, 0xcd0fe, 0xc0d68, 0x3657c, 0xb6056, 0xb6084, 0xb60c4, 0xb60da, 0xb7ae4, 0xb7af0,
           0xb6038, 0x364aa, 0x36588, 0xb5c60, 0x3645a, 0x36532, 0xb5d02, 0x36502, 0xcd1d4, 0xcd2a0)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x56)   # node links, pointer fields, the contact LONG 56 (4b54e)
# natural worlds of the extended observation: (config, case, frame) with a pool node holding an FR14 node entry (first, 4th, 12th, every 20th and last
# frame per run and callback) or a NATURAL_ROUTED callback at a first-execution frame (scratch natscan_fr14.py)
NATURAL = (('X2', 94, 874), ('X2', 94, 875), ('X2', 94, 878), ('X2', 94, 883), ('X3', 68, 1120), ('X3', 68, 1121), ('X3', 68, 1123),
           ('X3', 68, 1241), ('X3', 68, 1307), ('X3', 68, 1403), ('X3', 68, 1480), ('X3', 68, 1481), ('X3', 68, 1484), ('X3', 68, 1489),
           ('X3', 68, 1497), ('X3', 68, 1498), ('X3', 68, 1501), ('X3', 68, 1509), ('X3', 68, 1518), ('X3', 68, 1538), ('X3', 68, 1558),
           ('X3', 68, 1578), ('X3', 68, 1598), ('X3', 68, 1618), ('X3', 68, 1638), ('X3', 68, 1658), ('X3', 68, 1662), ('X3', 94, 958),
           ('X3', 94, 960), ('X3', 94, 1278), ('X3', 94, 1281), ('X3', 94, 1289), ('X3', 94, 1298), ('X3', 94, 1318), ('X3', 94, 1338),
           ('X3', 94, 1358), ('X3', 94, 1378), ('X3', 94, 1398), ('X3', 94, 1418), ('X3', 94, 1438), ('X3', 94, 1458), ('X3', 94, 1462))
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds (scratch natscan_fr14.py): the natural node of the frame after an FR14 entry that never stays at a frame start (the 2986 children
# 3643e / b5c34 and the handler c0d68 run in the frame that creates them; cc7b8 is a JMP-table landing of the cc778 tail; d177e follows d177a in the
# same callback; 3657c is the BRA.W target of the unrouted 365fc), with the declared callback LONG (written as a host edit; the node was already
# initialised once: the world re-runs the entry on the same node state, native and C++ alike)
REINSTALL = (('X3', 68, 1121, 0x102590, 0x3643e, ()), ('X3', 68, 1121, 0x102590, 0x3657c, ()), ('X3', 68, 1123, 0x102590, 0x3643e, ()),
             ('X3', 68, 1498, 0x102280, 0xb5c34, ()), ('X3', 94, 1278, 0x101330, 0xb5c34, ()), ('X3', 68, 1501, 0x102280, 0xb5c34, ()),
             ('X3', 68, 1498, 0x1020f8, 0xc0d68, ()), ('X3', 94, 1278, 0x101a14, 0xc0d68, ()), ('X3', 94, 1289, 0x101a14, 0xc0d68, ()),
             ('X3', 68, 1403, 0x102280, 0xcc7b8, ()), ('X3', 68, 1403, 0x102280, 0xcc7b8, ((0x5f, 1, 0x80),)),
             ('X3', 68, 1403, 0x102280, 0xcc7b8, ((0x7a, 1, 0), (0x5f, 1, 0x80))),
             ('X2', 94, 875, 0x102654, 0xd177e, ()), ('X3', 68, 1481, 0x10126c, 0xd177e, ()))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xe, 0xf, 0x10, 0x1e, 0x1f, 0x20, 0x3f, 0x40, 0x62, 0x63, 0x64, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xf7, 0xfe, 0xff)
VW = (0, 1, 2, 3, 4, 5, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x3f, 0x40, 0x62, 0x63, 0x64, 0x7f, 0x80, 0x9f, 0xa0, 0xa1, 0x100, 0x7ffc, 0x7fff, 0x8000, 0x8001,
      0xfffc, 0xfffe, 0xffff)
VL = (0, 1, 2, 0xf, 0x10, 0x1f, 0x20, 0x8000, 0xa000, 0xffff, 0x10000, 0x20000, 0x40000, 0x100000, 0x7fffffff, 0x80000000, 0xfff00000, 0xfffc0000,
      0xffff0000, 0xfffffff0, 0xfffffff1, 0xffffffff, 0x12345678)
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
# no flag-sharing Bcc pair inside one FR14 block
BUNDLED = ()
THREAD = {}


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the blocks that fall into the next start, and 7177a / 71786 into FR12 7177c / 71788, 71874 / d1632 into FR13 71876 /
    d1636); a Bcc followed by a BUNDLED Bcc continues the block (none in FR14)."""
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
    the computed jumps that the FR14 runs reach (OTHER_JUMP_PCS: FR13 cc8da, FR11 b4034 / b42b4 / c54ae, FR1, FR2 b46aa, FR4 cc7a8 / cc82a, the
    interpreter and the C3 .. C10 list; FR14 has no computed jump of its own), or at
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it: WORD 76(A6) 0..3 mostly (the player index of the
        3643e child: the anim LONG table 363ae / 36522 and the sound WORD table 363be have 4 / 2 entries; a large index reads other ROM as an anim
        pointer, which the native run may follow anywhere), LONG 26(A6) = 0 mostly (49fc6 Set without the interpreter), LONG 56(A6) = 0 mostly (4b54e
        without the contact list), BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 10fd82 = 0, WORD 90(A6) a multiple of 4 below 18 (the routed FR2 b4aca reads
        the LONG table b4ad4 by it after b4958; an odd index faults natively), A1 / A2 RAM pointers (b7b1e / b7b2c entered directly)."""
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 3, 4, 5, 8, 0xf7, 0xfb, 0xff, 0x100, 0x7fff, 0x8000, 0xffff, 0x10000, 0x10001, 0x12340001, 0xffffffff,
                                     0x80000000, 0xfffffff7, 0xfffffffb))
        if rng.random() < 0.4:
            regs['d1'] = rng.choice((0, 1, 0x80, 0xff, 0x100, 0xffff0000, 0x12345600, 0x80000000, 0x18000))
        if rng.random() < 0.4:
            regs['d2'] = rng.choice((0, 1, 0xf, 0x10, 0x7ffffff1, 0x7fffffff, 0x80000000, 0xfffffff0, 0xfffffff1, 0xffffffff))
        if rng.random() < 0.4:
            regs['d3'] = rng.choice((0, 1, 0xf, 0x10, 0x7ffffff1, 0x7fffffff, 0x80000000, 0xfff00000, 0xfffc0000, 0xffffffff))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if rng.random() < 0.3 else self.pointer()
        regs['a1'] = rec + 0x10 if rng.random() < 0.3 else self.pointer()
        regs['a2'] = rec + 0x30 if rng.random() < 0.3 else self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        if rng.random() < 0.8:
            writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 1, 0, 1, 2, 3))))                  # WORD 76(A6): the player index
        writes.append(((a6 + 0x90) & 0xffff, 2, rng.choice((0, 4, 8, 0xc, 0x10, 0x14))))           # WORD 90(A6): the FR2 b4aca LONG table b4ad4 index
        if rng.random() < 0.8:
            writes.append(((a6 + 0x26) & 0xffff, 4, 0))       # 49fc6: LONG 26(A6) = 0 -> Set without the interpreter (random scripts)
        if rng.random() < 0.7:
            writes.append(((a6 + 0x56) & 0xffff, 4, 0))       # 4b54e: LONG 56(A6) = 0 -> the BYTE 5e test only
        if rng.random() < 0.9:
            writes.append((0xfd82, 1, 0))                                                 # BYTE 10fd82 = 0
        if rng.random() < 0.7:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and (disp in POINTERS or disp in (0x56, 0x57, 0x58, 0x59, 0x76, 0x77, 0x90, 0x91)):
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
    require(len(STARTS) == 200 and len(STARTS_SET) == 200, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_objects_fr14_block', ('start is not routed to objects fr14', hex(s), unit_of(s)))
    # every even PC of the ranges belongs to FR14 (the interior is the FR14 checked error)
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            require(unit_of(pc) == 'animation_objects_fr14_block', ('range PC not routed to objects fr14', hex(pc)))
    # the computed-jump entries of earlier units that FR14 routes: the FR4 table cc7ac entry 3 (cc7b8); the other entries that reach cd0fe (cc83a of
    # cc82e, cc8ea of FR13 cc8de) and the neighbours of cc7b8 in its table stay unrouted stops (cc7b4 is FR8); 3657c (the BRA.W target of 365fc) is a
    # start, 365fc stays unrouted
    require(unit_of(0xcc7b8) == 'animation_objects_fr14_block', 'cc7b8 routed to FR14')
    for t in (0xcc7ac, 0xcc7b0, 0xcc7bc, 0xcc83a, 0xcc8ea, 0x365fc, 0x363c6, 0x3640e, 0xb5d5a, 0xb5e46, 0xb5f00, 0xb604e):
        require(unit_of(t) is None, ('stays unrouted', hex(t)))
    require(0x3657c in STARTS_SET, '3657c is a start')
    rng = random.Random(0xF14A)
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
    sys.stderr.write('fr14 spec: %d fixtures (%d natural), visited %d/200, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('fr14: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('fr14: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the D0 bit 3 of 36452,
    the WORD 76 index of the tables 363ae / 36522 / 363be, BYTE 15 bit 0 with the WORD 3a / 36 adds of 3648c / 364a0 / 36564 / 36578, the LONG 36 /
    3a and D2 / D3 of the 1/16 approach 364aa .. 364d4 / 36588 .. 365b2 (BMI after SUB.L, ADDI.L #f, ASR.L #4), the popped LONG and BYTE 15 bit 7 of
    364e4, BYTE 61 bit 3 of 364f0 / 365c0, BYTE 7f of 365b2, WORD 76 of b5c60, WORD 7c and the D0 bits of b5c84 / b5cb2, WORD 2a of b5cf6, BYTE 8a
    of b5d02 (ADDQ.B / ANDI.B), LONG 80 of b5d48 / b60a4, BYTE 15 bits 0 / 7 of b6056 .. b60c4, LONG 64 of b6098 / b60c4, BYTE 61 bit 0 of b60da,
    BYTE 8b of b612e, D0.B of b7b0a, the WORD counter (A1) 62 / 63 / 64 / ffff of b7b1e, BYTE (A2) of b7b2c, the signed WORD 42 (a0) of c0d68, LONG
    64 of c0d7a, D0 bit 2 of c0dee, the BYTE 5f / BYTE 15 bit 0 EOR.B sign of cd0fe, WORD 8c (0..5) and BYTE 7a of cd110 .. cd2a0, the D0 / D1 of
    the NEG fall-throughs), the upper register bits of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a
    fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    if entry in (0x3643e, 0x3645a, 0x36474, 0x3648c, 0x364a0, 0x364aa, 0x364c0, 0x364d4, 0x364e4, 0x36532, 0x3654c, 0x36564, 0x36578, 0x3657c, 0x36588,
                 0x3659e, 0x365b2, 0xb5c34, 0xb5c60, 0xb5c84, 0xb5cb2, 0xb5cf6, 0xb5d02, 0xb5d48, 0xb6098, 0xb60a4, 0xb60b4, 0xb60c4, 0xb612e, 0xb7ae4,
                 0xb7af0, 0xc0d68, 0xc0d7a, 0xc0d88, 0xcd0fe, 0xcd110, 0xcd1d4, 0xcd2a0, 0xcd360, 0xd177e, 0xd1798, 0xd17cc, 0x7177a, 0xd1632):
        h += [dict(regs=dict(up))] + mirror
    if entry == 0x36452:
        h += [dict(regs=dict(up, d0=v)) for v in (8, 0xfffffff7, 0, 0xffffffff, 0x100)]
    if entry in (0x3645a, 0x36474, 0x36532, 0x3654c):
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v)]) for v in (0, 1, 2, 3)]
    if entry in (0x3648c, 0x36564):
        for w3a, b15 in ((0x7ffe, 0), (0xfffc, 1), (0xffff, 0), (0, 1), (0x8000, 0xfe)):
            h.append(dict(regs=dict(up), a6off=[(0x3a, 2, w3a), (0x3c, 2, 0x5a5a), (0x15, 1, b15)]))
    if entry in (0x3649e, 0x36576):
        h += [dict(regs=dict(up, d0=v)) for v in (4, 0x12340004, 0x8000, 0)]
    if entry in (0x364a0, 0x36578):
        for d0, w36 in ((0x1234fffc, 3), (4, 0xfffe), (0xfffc, 0x7ffe), (0x12340004, 0x8000)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x36, 2, w36), (0x38, 2, 0xa5a5)]))
    if entry in (0x364aa, 0x36588):
        for l36, l3a in ((0, 0), (1, 0xfff00000), (0x10, 0xfffc0000), (0xfffffff0, 0), (0x80000000, 0x7fffffff), (0x7fffffff, 0x80000000), (0xf, 0xfff00010),
                         (0xfffffff1, 0xffefffff), (0x12345, 0xfffbffff)):
            h.append(dict(regs=dict(up), a6off=[(0x36, 4, l36), (0x3a, 4, l3a)]))
    if entry in (0x364ba, 0x36598, 0x364ce, 0x365ac):
        h += [dict(regs=dict(up, d2=v, d3=v)) for v in (0, 1, 0x7ffffff1, 0x7fffffff, 0xfffffff0, 0x10)]
    if entry in (0x364c0, 0x3659e):
        for d2, l3a in ((0x1f, 0), (0xffffffe1, 0x80000000), (0x80000000, 0xfff00000), (0xf, 0xfffc0000), (0x7fffffff, 1)):
            h.append(dict(regs=dict(up, d2=d2, d3=0xfff00000), a6off=[(0x3a, 4, l3a), (0x36, 4, 0x100)]))
    if entry in (0x364d4, 0x365b2):
        for d3, l3a in ((0x1f, 0), (0xffffffe1, 0x80000000), (0x80000000, 0xfff00000), (0xf, 0x7fffffff)):
            h.append(dict(regs=dict(up, d3=d3), a6off=[(0x3a, 4, l3a)]))
    if entry == 0x364e4:
        for v, b15 in ((0x12345678, 0x80), (0x80000000, 0x7f), (0, 0xff), (1, 0)):
            h.append(dict(regs=dict(up), stack=[(0, 4, v), (4, 4, SENTINEL)], a6off=[(0x15, 1, b15), (0x61, 1, 0)]))
    if entry in (0x364f0, 0x365c0):
        h += byte(0x61, (0, 8, 0xf7, 0xff))
    if entry == 0x36500:
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x80000000, 0xffffffff)]
    if entry == 0x365b2:
        h += [dict(regs=dict(up), a6off=[(0x7f, 1, v), (0x80, 1, 0x5a)]) for v in (0, 1, 0xff, 0x80)]
    if entry == 0x3657c:
        h += byte(0x7f, (0, 0xff))
    if entry == 0xb5c60:
        h += [dict(regs=dict(up), a6off=[(0x76, 2, v), (0x15, 1, b)]) for v, b in ((0, 0xff), (1, 0), (0x100, 0xfe), (0x8000, 1))]
    if entry in (0xb5c68, 0xb5c78):
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0xb5c84:
        h += [dict(regs=dict(up, d0=d0), a6off=[(0x7c, 2, w)]) for d0, w in ((0xffff8000, 0x8000), (0x8000, 0xffff), (0x12345678, 1), (0, 0))]
    if entry == 0xb5cb2:
        h += [dict(regs=dict(up, d0=v)) for v in (0x12348000, 0xffff, 0)]
    if entry == 0xb5cf6:
        h += [dict(regs=dict(up), a6off=[(0x2a, 2, v), (0x8a, 1, 3)]) for v in (0, 1, 0x8000, 0x100)]
    if entry == 0xb5d02:
        h += [dict(regs=dict(up), a6off=[(0x8a, 1, v)]) for v in (0, 0xe, 0xf, 0xff, 0x10, 0x7f, 0x8f)]
    if entry == 0xb5d48:
        h += [dict(regs=dict(up), a6off=[(0x80, 4, v)]) for v in (0, 1, 0x80000000, 0x10000)]
    if entry in (0xb6056, 0xb6070, 0xb6084, 0xc0dc8):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry == 0xb6098:
        h += [dict(regs=dict(up), a6off=[(0x64, 4, v), (0x80, 4, 0x20000)]) for v in (0, 0x80000000, 1, 0xffffffff, 0x10000)]
    if entry == 0xb60a4:
        for d0, l80 in ((0x10, 0x20), (0x20, 0x10), (1, 0x80000000), (0, 0), (0x80000000, 0), (0x10, 0x10)):
            h.append(dict(regs=dict(up, d0=d0), a6off=[(0x80, 4, l80)]))
    if entry == 0xb60c4:
        for l64, b15 in ((0x8000, 1), (0x8000, 0), (0x80000000, 1), (0, 0xff), (0xffff8000, 0xfe)):
            h.append(dict(regs=dict(up), a6off=[(0x64, 4, l64), (0x15, 1, b15)]))
    if entry == 0xb60da:
        h += byte(0x61, (1, 0, 0xfe, 0xff))
    if entry == 0xb612e:
        h += byte(0x8b, (0, 1, 0x80))
    if entry == 0xb7b0a:
        h += [dict(regs=dict(up, d0=v), rega5=dict(a2=0x5dde, a3=0x5de6)) for v in (0, 1, 0x100, 0xff)]
    if entry == 0xb7b1e:
        for w in (0x62, 0x63, 0x64, 0xffff, 0x7fff, 0):
            h.append(dict(regs=dict(up), rega5=dict(a1=0x5ddc, a2=0x5dde), a5off=[(0x5ddc, 2, w)]))
    if entry == 0xb7b2c:
        h += [dict(regs=dict(up), rega5=dict(a2=0x5dde), a5off=[(0x5dde, 1, v)]) for v in (0xff, 0x7f, 0)]
    if entry == 0xc0d68:
        h += [dict(regs=dict(up), a6off=[(0x42, 2, v), (0x15, 1, 0xfe)]) for v in (0x9f, 0xa0, 0x8000, 0x7fff, 0xffff, 0xa1)]
    if entry == 0xc0d7a:
        h += [dict(regs=dict(up), a6off=[(0x64, 4, v)]) for v in (0xa000, 0, 0x80000000)]
    if entry == 0xc0dee:
        h += [dict(regs=dict(up, d0=v)) for v in (4, 0xfffffffb, 0, 0x104)]
    if entry == 0xcd0fe:
        for b5f, b15 in ((0x80, 0), (0x80, 1), (0x7f, 0), (0x7f, 1), (0, 0), (0xff, 1), (0, 1), (0xff, 0)):
            h.append(dict(regs=dict(up), a6off=[(0x5f, 1, b5f), (0x15, 1, b15), (0x7a, 1, 1)]))
    if entry in (0xcd110, 0xcd1dc, 0xcd2a0):
        h += [dict(regs=dict(up), a6off=[(0x8c, 2, v), (0x8a, 2, 0x1234)]) for v in (0, 1, 2, 3, 4, 5, 0x100, 0xffff, 0x101)]
    if entry in (0xcd132, 0xcd154, 0xcd176, 0xcd198, 0xcd1fe, 0xcd220, 0xcd242, 0xcd264, 0xcd2c2, 0xcd2e4, 0xcd306, 0xcd328):
        h += [dict(regs=dict(up, d0=0x12340000 | v)) for v in (1, 2, 3, 4, 5, 0x101, 0x104)]
    if entry == 0xcd1d4:
        h += byte(0x7a, (0, 1, 0x80, 0xff))
    if entry in (0x7177a, 0x71786, 0x71874):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 0x80000000, 0xffffffff, 0x40000)]
    if entry == 0xd1632:
        h += [dict(regs=dict(up, d0=d0, d1=d1)) for d0, d1 in ((0x12340018, 0x18000), (0x8000, 0x80000000), (0, 0), (0xffff0001, 1))]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]


def chain_hint(entry, t, rng):
    if entry in (0x3650c, 0x365e6):
        # 1ab80 (N05): the record 363a6 against the node position (WORD 42 / 46) and the camera; BYTE 15 bits 0 / 1 flip the box
        return dict(a6off=[(0x42, 2, (0, 0x40, 0xa0, 0x120, 0x200, 0xffc0, 0x400)[t % 7]), (0x46, 2, (0, 0xc0, 0x100, 0x180, 0x1f0, 0x300, 0x600)[(t // 2) % 7]),
                           (0x15, 1, (0, 1, 2, 3)[(t // 3) % 4])])
    if entry == 0xb5d2a:
        # 4b54e (U01): LONG 56(A6) = 0 -> the BYTE 5e test (0 Clear, else Set)
        return dict(a6off=[(0x56, 4, 0), (0x5e, 1, (0, 1, 0, 0x80)[t % 4])])
    if entry == 0xb5d3a:
        # b60da: BYTE 61 bit 0 -> Set; else 49392 (BYTE 568e(A5) bit D0) / 4941e (the box b6278 of A0 = the player record against the node)
        return dict(a6off=[(0x61, 1, (0, 1, 0, 0)[t % 4]), (0x8b, 1, (0, 1)[(t // 2) % 2])], writes=[(0xd68e, 1, (0, 1, 2, 3)[(t // 4) % 4])])
    if entry == 0xb6038:
        # 1aa7e (U01): the record b6270 against the node position and the camera
        return dict(a6off=[(0x42, 2, (0, 0x40, 0xa0, 0x120, 0x200, 0xffc0, 0x400)[t % 7]), (0x46, 2, (0, 0xc0, 0x100, 0x180, 0x1f0, 0x300, 0x600)[(t // 2) % 7]),
                           (0x15, 1, (0, 2)[(t // 3) % 2])])
    if entry in (0xb60e4, 0xb6104, 0xb7af8):
        # 49392: BYTE 568e(A5) bit D0.W & 1 -> Set
        return dict(writes=[(0xd68e, 1, (0, 1, 2, 3)[t % 4])], regs=dict(d0=(0, 1, 0x10000, 0x10001)[(t // 4) % 4]))
    if entry in (0xb60f0, 0xb6112):
        # 4941e: the box b6278 of A0 (the player record 100cb8 / 100da8) against the node: WORD 42 / 46 of both
        return dict(regs=dict(a0=(0x108000 - 0x7348, 0x108000 - 0x7258)[t % 2]),
                    a6off=[(0x42, 2, (0x100, 0x110, 0x140, 0x80)[(t // 2) % 4]), (0x46, 2, (0x100, 0x108, 0x130, 0xc0)[(t // 4) % 4]), (0x15, 1, (0, 3)[(t // 8) % 2])],
                    writes=[(0x0cb8 + 0x42, 2, 0x100), (0x0cb8 + 0x46, 2, 0x100), (0x0da8 + 0x42, 2, 0x100), (0x0da8 + 0x46, 2, 0x100)])
    if entry in (0xc0df6, 0xd17e6):
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), BYTE 15 bits 0 / 7, BYTE 61 bits 0 / 3, BYTE 5e (4b54e), BYTE 7f / 8a / 8b, WORD 76 (the player index),
            # WORD 2a / 42 / 46, LONG 26 (0: 49fc6 Set), LONG 36 / 3a / 64 / 80, LONG 56 = 0 (4b54e without the contact list), BYTE 568e(A5) (49392),
            # WORD 10000e
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80, 1, 0x81, 0xff, 0x7f, 0xfe)[t % 7]), (0x61, 1, (0, 8, 1, 0xff)[(t // 2) % 4]),
                               (0x5e, 1, (0, 1)[(t // 3) % 2]), (0x7f, 1, (0, 1, 0x1e)[(t // 2) % 3]), (0x8a, 1, (0, 0xf, 3)[(t // 3) % 3]),
                               (0x8b, 1, (0, 1)[(t // 4) % 2]), (0x76, 2, (0, 1, 0, 1, 2, 3)[(t // 2) % 6]), (0x2a, 2, (0, 1)[(t // 5) % 2]),
                               (0x42, 2, (0x100, 0xa0, 0x9f, 0x200)[(t // 3) % 4]), (0x46, 2, (0x100, 0x180, 0xc0)[(t // 4) % 3]),
                               (0x36, 4, (0, 0x80000000, 0x100000, 0xfff00000)[(t // 6) % 4]), (0x3a, 4, (0, 0xfffc0000, 0x12345, 0x8000)[(t // 4) % 4]),
                               (0x64, 4, (0, 0x40000, 0xfffc0000, 0x10000)[(t // 5) % 4]), (0x80, 4, (0, 0x10000, 0x80000)[(t // 3) % 3]), (0x56, 4, 0)] +
                        ([(0x26, 4, 0)] if t % 5 != 4 else []), writes=[(0x4ca0, 2, (0x40, 0x40, 0x15)[t % 3]), (0xd68e, 1, (0, 1, 2, 3)[(t // 3) % 4]),
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
    err('odd-pc', U.with_host_writes(st, pc=0xcd0ff), 'unaligned animation machine PC', 0xcd0ff)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    device = 'unsupported animation machine write device'
    # odd node / stack / A1: the entry block fails (the row's stop is the PC right after the failing block)
    err('3643e-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x3643e), odd_write, 0x3643e, stop=0x1aa3a)
    err('364aa-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x364aa), odd_word, 0x364aa)
    err('b5c60-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb5c60), odd_word, 0xb5c60)
    err('c0d68-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xc0d68), odd_write, 0xc0d68)
    err('b5d02-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xb5d02), odd_write, 0xb5d02, stop=0xb6084)
    err('cd360-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0xcd360), odd_write, 0xcd360)
    err('b7b1e-odd-a1', U.with_host_writes(st, regs=dict(a1=a5 + 0x5ddd), pc=0xb7b1e), odd_word, 0xb7b1e)
    err('364e4-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x364e4), odd_word, 0x364e4)
    err('b7af8-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb7af8), odd_word, 0xb7af8, stop=0x49392)
    err('b7b02-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb7b02), odd_word, 0xb7b02)
    err('b6146-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb6146), odd_word, 0xb6146)
    # fixed ROM writes: the node in fixed ROM
    err('rom-write-3657c', U.with_host_writes(st, regs=dict(a6=0x1000), pc=0x3657c), device, 0x3657c)
    err('rom-write-b60b4', U.with_host_writes(st, regs=dict(a6=0x1000), pc=0xb60b4), device, 0xb60b4)
    # failures after executed blocks (rollback; the failing PC differs from the entry)
    err('cc7b8-then-cd110-odd-node', U.with_host_writes(st, [((a6 + 1 + 0x5f) & 0xffff, 1, 0), ((a6 + 1 + 0x15) & 0xffff, 1, 0)], regs=dict(a6=a6 + 1),
                                                        pc=0xcc7b8), odd_word, 0xcd110)
    err('b7ae4-then-b7af8-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xb7ae4), odd_word, 0xb7af8, stop=0x49392)
    err('36576-then-36578-rom-write', U.with_host_writes(st, regs=dict(a6=0x1000), pc=0x36576), device, 0x36578)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x364aa, 0x364c0, 0xcd0fe, 0xb60a4)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
