"""V1 fixture spec of the area-C unit C8 (engine/src/animation_machine_player_c8.cpp, 99 block starts; file prefix pc8 / player_c8 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c8-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C8 spec of the
contract): the player states 1f3d8 -> 1f3ec -> 1f418 (1cab6, 1cd98, 4bfc0 / ce02 / 49fc6, 201a2; installed by 1f756 after C7 1f752), 1fa68 -> 1fafc
-> 1fb02 (1cb08, 1cab6, the motion helpers 1cfde / 1cff8 / 1d066 on the LONGs 36 / 3a(A6): ASR.L, 4be82), 201bc -> 1fcce / 1fcd4 -> 1fd12 (ea626,
4de7a, the record helper 4d1ac: MOVEM.L D0-D3/A1,2e(A6), 43e34; 484b4), the C3 helper tail 4d0cc (484b4), the C4 input branch 1ef4c, 1eb98, 1ce98,
and the slot-84 state 21e3a -> 21e52 -> 21e6a (215e6 list 21b3c, JMP (A1) 21e76) with the JMP (A1) 21d9e of C4 21d92 (list 21b0a; contract
decision 2).

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1..C7) with declared host edits.
This code runs natively only in the IO observation (boot-demo-0 frames 488..577): the 'natural' family takes the frame-start states of the IO native
observation in which a node of the pool holds a callback that runs into C8 code (the player node 100cb8 with C7 1f6da (-> 1f756) or the C8 states
1f3d8 1f418 1fb02 1fcce 1fd12), keeps their RAM / PVC / bank and declares only the registers (A5 = 108000, A6 = that node, A7 = 10ef00 with the
sentinel return LONG, PC = the callback); the 'reinstall' family enters a C8 state on the player node of a demo frame with declared BYTEs.  The frame
532 pack is not used (the Unicorn native oracle aborts on it, [U] as in C6 / C7).

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 5 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers (CHAINS).  Stop: the consumer's successor or the first unrouted PC.
  node      the installed values (NODE_ENTRIES) ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with a declared callback / BYTEs.
  callee    the helpers and states entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 5 consumers, the jump-target guard of the JMP (A1) 21d9e / 21e76
            (decision 2), odd node / stack / A0 / A4, failures after executed blocks: checked error, state preserved, every row with its failing PC (a
            paired 'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1..C7
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1..C7)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc8'
ERROR_PC = 'unsupported animation player c8 PC'
ERROR_CARRY = 'player c8 caller requires known carry'
ERROR_JUMP = 'unsupported animation player c8 jump target'

RANGES = [(0x1ce98, 0x1cea8), (0x1cfde, 0x1d086), (0x1eb98, 0x1eba0), (0x1ef4c, 0x1ef6c), (0x1f3d8, 0x1f3e0), (0x1f3ec, 0x1f48a), (0x1f756, 0x1f76a),
          (0x1fa68, 0x1fa90), (0x1fafc, 0x1fb28), (0x1fb2e, 0x1fb32), (0x1fcce, 0x1fd3c), (0x201bc, 0x201d0), (0x21d9e, 0x21da0), (0x21e3a, 0x21e48),
          (0x21e52, 0x21ea0), (0x4d0cc, 0x4d100), (0x4d1ac, 0x4d208), (0xea626, 0xea62e)]
STARTS = sorted(int(x, 16) for x in (
    '1ce98 1cea2 1cfde 1cfe8 1cfec 1cfee 1cff8 1cffa 1d018 1d01c 1d026 1d02c 1d034 1d03a 1d04e 1d058 1d064 1d066 1d070 1d076 1d080 1d084 1eb98 1ef4c '
    '1ef56 1ef5e 1ef68 1f3d8 1f3ec 1f3f0 1f418 1f41c 1f426 1f42e 1f438 1f440 1f444 1f44c 1f454 1f45c 1f466 1f46c 1f476 1f47c 1f480 1f486 1f756 1f764 '
    '1fa68 1fa70 1fa74 1fa7c 1fa80 1fafc 1fb02 1fb06 1fb0a 1fb0e 1fb18 1fb1e 1fb2e 1fcce 1fcd4 1fd12 1fd18 1fd28 1fd2e 1fd34 1fd38 201bc 201c6 201cc '
    '21d9e 21e3a 21e52 21e5e 21e62 21e6a 21e72 21e76 21e78 21e7c 21e84 21e8c 21e94 21e9c 4d0cc 4d0d4 4d0e0 4d0e6 4d0ea 4d0f6 4d1ac 4d1b4 4d1bc 4d1c0 '
    '4d1c6 4d206 ea626').split())
# the 5 C consumers: BCC 1f47c (49fc6), BCS 1fa70 (1cb08 of C2), BCC 1fd34 4d0e6 (484b4), BCC 21e72 (215e6 of C3)
CONSUMERS = (0x1f47c, 0x1fa70, 0x1fd34, 0x21e72, 0x4d0e6)
CLEAR_SET = ()
SET_SET = (0x4d0ea,)                    # MOVE.B #0,22(A4); ORI.B #1,CCR; RTS (read by C3 201b8)
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = ()
INVERT_SET = ()
PASS_SET = ()
STARTS_SET = set()
Z_READERS = ()                          # no Z crosses a C8 block boundary
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
BRANCH_IMPOSSIBLE = set()
LATER_GATED = set()
GATED_CONSUMERS = ()
TRAPS = ()
# PCs of later units that a C8 block reaches by a fall-through, a branch or a call (the deferred leaders 1f48a 1fb28 1fd3c (C11), 21ea0 21d0e 2210c (C12),
# 223a0 223d6 (C13)), and the still unrouted later-unit stops of the C1..C7 blocks that the C8 runs pass through (pc7 EXIT_STOPS that are still
# unrouted; the TRAP site 4e69a of C1; the interpreter stub successors 1dc8e / 1dccc).  Declared stops of the native runs: a straight-line unrouted PC
# after a routed block is not the interior of a routed block.
EXIT_STOPS = (0x1f48a, 0x1fb28, 0x1fd3c, 0x21ea0, 0x21d0e, 0x2210c, 0x223a0, 0x223d6,
              0x1d3e0, 0x4eb6a, 0x1dc8e, 0x1dccc, 0x208fa, 0x1efd6, 0x1f070, 0x21dd0, 0x4ef08, 0x1de3c, 0x1e21c, 0x1e8de, 0x1fc96, 0x1fd50, 0x21ca4,
              0x21fa6, 0x4e69a)
UNIT_EXITS = EXIT_STOPS[:8]             # the C8 later-unit stops (deferred leaders)
ROUTED_LATER = ()
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1f476, 0x1f47c), (0x1fa68, 0x1fa70), (0x1fd2e, 0x1fd34), (0x4d0e0, 0x4d0e6), (0x21e6a, 0x21e72))
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = ()                           # no PC-relative computed jump in C8
JUMP_ROUTED = ()
# the JMP (A1) of C8 (contract decision 2): A1 = the handler LONG that C3 215e6 loaded from the ROM list (21b0a for C4 21d92 -> 21d9e, 21b3c for C8
# 21e6a -> 21e76); any other A1 is the C++ checked jump-target error (a native run that jumps elsewhere is not a fixture world)
LIST_21B0A = (0x21602, 0x21c22, 0x21e48, 0x21e3a)
LIST_21B3C = (0x21602, 0x21c22, 0x21d60)
LIST_JUMPS = {0x21d9e: LIST_21B0A, 0x21e76: LIST_21B3C}
# computed jumps that the C8 runs reach (C3 2031c table, 201a6 JSR (A4) (from 1f486 / 1fb2e / 1fd38 BRA 201a2), 21620 / 221de JMP (A1); C4 21c72 JMP
# (A1); C5 20792 2094e 209d6 21f7c; C7 25298; C8 21d9e 21e76): an unrouted target is a stop even when it is the straight-line successor
OTHER_JUMP_PCS = (0x2031c, 0x201a6, 0x21620, 0x221de, 0x21c72, 0x20792, 0x2094e, 0x209d6, 0x21f7c, 0x25298, 0x21d9e, 0x21e76)
TABLE_ENTRIES = ()
SLOT84_C3 = (0x21602, 0x21610, 0x21c66, 0x21f70, 0x221d2, 0x21ffc, 0x21d92, 0x21e6a)   # routed slot-84 states (C3, C4 21d92, C8 21e6a) for the worlds
# installed values entered as node callbacks: 1f3d8 (1f756), 1f418 (1f3f0), 1fb02 (1fafc), 1fcce (201c6), 1fcd4 (C6 1dbca), 1fd12 (1fcd4); the callee
# entries (helpers, branch targets of other units' blocks, the slot-84 state 21e6a of 201a6 JSR (A4), states entered as subroutines)
NODE_ENTRIES = (0x1f3d8, 0x1f418, 0x1fb02, 0x1fcce, 0x1fcd4, 0x1fd12)
CALLEES = (0x1cfde, 0x1cff8, 0x1d066, 0x4d1ac, 0xea626, 0x4d0cc, 0x1ce98, 0x1ef4c, 0x1eb98, 0x1f756, 0x1fa68, 0x201bc, 0x21d9e, 0x21e3a, 0x21e6a,
           0x1cffa, 0x1d03a, 0x4d1c6)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x78, 0x84, 0x8c, 0x94, 0xb2)   # node links, pointer fields and the slot LONG 84: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                       # C2 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('boot-demo-0', None, f) for f in (488, 489, 490, 497, 503, 508, 511, 515, 516, 520)])
NATURAL_CALLBACKS = (0x1f6da,) + NODE_ENTRIES                         # C7 1f6da -> 1f756, the C8 states
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node), extra (offset, size, value) writes on the node)
REINSTALL = (('boot-demo-0', None, 489, 0x100cb8, 0x1f3d8, ((0x9e, 1, 1),)), ('boot-demo-0', None, 490, 0x100cb8, 0x1f418, ((0x9e, 1, 1),)),
             ('boot-demo-0', None, 497, 0x100cb8, 0x1fb02, ((0xa7, 1, 8),)), ('boot-demo-0', None, 497, 0x100cb8, 0x1fb02, ((0x61, 1, 3),)),
             ('boot-demo-0', None, 515, 0x100cb8, 0x1fcd4, ()), ('boot-demo-0', None, 515, 0x100cb8, 0x1fcce, ((0x78, 2, 1),)),
             ('boot-demo-0', None, 488, 0x100cb8, 0x1f756, ((0x88, 1, 1),)), ('boot-demo-0', None, 497, 0x100cb8, 0x1fa68, ()),
             ('boot-demo-0', None, 490, 0x100cb8, 0x1ef4c, ()))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xe, 0xf, 0x10, 0x13, 0x14, 0x1e, 0x1f, 0x20, 0x40, 0x50, 0x7e, 0x7f, 0x80, 0x81, 0xbf, 0xfe, 0xff)
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
BUNDLED = (0x21e5a,)                    # flag-sharing Bcc pair inside one block: BGT 21e56 / BLT 21e5a (TST.B 9d(A6) of 21e52)


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (the bundled second Bcc 21e5a stays in its block; 1cfe8 / 1d018 / 1d026 / 1d034 / 1d058 / 1d080 / 1f3f0 / 1f480 /
    1fcce / 1fcd4 / 201c6 / 21e62 / 4d1b4 / 4d1bc fall into the next start; 1cea2 into the routed C2 1cea8, 1f764 into C7 1f76a, 4d0f6 into C3
    4d100)."""
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
    """The PC after the entry block: pcs[n] (or the stop); the bundled Bcc pair (21e52) uses pcs[n - 1] when its first Bcc was taken."""
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
    the computed jumps that the C8 runs reach (OTHER_JUMP_PCS: C3 / C4 / C5 / C7 and the C8 JMP (A1) 21d9e / 21e76, whose unrouted list handler 21e48
    is a stop), or at the first unrouted PC that is not the straight-line successor of the previous instruction (a PC inside a block of another
    executor is not a block entry)."""
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
        """A world for `entry`.  The values the ROM writers / callers keep in a range stay in it (as C1..C7): WORD 76 / 78(A6) mostly 0 / 1 (the
        player index of 4d1ac / 4de7a), BYTE 9e(A6) 0..3 (the C4 LONG table 1cfce of 1cfbe: the motion record A0), the motion record A0 (LONGs 10 /
        14 / 18) of a direct 1cfee / 1cffa / 1d018 entry, A1 a handler of the ROM list of the JMP (A1) 21d9e / 21e76 (decision 2), A4 the record
        5cba / 5ce6(A5) of 4d0cc .. 4d0f6 / 4d1c0 .. 4d1c6, the stacked LONG of a direct 1d070 entry, D0 input bits, LONG 84(A6) a routed slot-84
        value (the C3 JSR (A4) 201a6 that 1f486 / 1fb2e / 1fd38 reach; C8 21e6a included), LONG 26(A6) = 0 mostly (49fc6 Set without the
        interpreter), LONG 5434(A5) = 0 (C2 decision 2), BYTE 10fd82 = 0 (keeps the controller C1 4a974 off the BIOS call c00450, not mapped
        natively)."""
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
        if rng.random() < 0.5:
            regs['d2'] = (regs['d2'] & 0xffff0000) | rng.choice((0, 1, 2, 5, 0x1f, 0x20, 0x21, 0x3f, 0x40, 0x45))
        writes = []
        rec = SCR + 0x40 * rng.randrange(4)
        regs['a0'] = rec + 0x20 if entry in (0x1cfee, 0x1cffa, 0x1d018) or rng.random() < 0.3 else self.pointer()
        regs['a1'] = self.pointer()
        if entry in LIST_JUMPS:
            regs['a1'] = rng.choice(LIST_JUMPS[entry])         # the handler LONG 215e6 loaded (decision 2)
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = rec + 0x20 if rng.random() < 0.5 else (a5 + rng.choice((0x5cba, 0x5ce6))) & 0xffffff
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, rec + 0x20 if rng.random() < 0.7 else self.pointer()))   # LONG 8c(A6): a record
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of C2 1cb08 / C5 1cb1a)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(), 0))))  # LONG 3e(A6) (C2 1a9fe..1aa20; 4be82 CMPA.W #0)
        writes.append(((a6 + 0x84) & 0xffff, 4, rng.choice(SLOT84_C3)))                  # LONG 84(A6): a routed slot-84 state of JSR (A4) 201a6
        writes.append(((a6 + 0xa0) & 0xffff, 1, rng.randrange(9)))                        # BYTE a0(A6): C3 2031c / C5 1cc1a
        writes.append(((a6 + 0xa9) & 0xffff, 1, rng.randrange(6)))                        # BYTE a9(A6): C3 206d4
        writes.append(((a6 + 0x9f) & 0xffff, 1, rng.randrange(9)))                        # BYTE 9f(A6): C2 1cb08
        writes.append(((a6 + 0x9c) & 0xffff, 1, rng.randrange(6)))                        # BYTE 9c(A6): the key of the 215e6 lists
        writes.append(((a6 + 0x7c) & 0xffff, 2, rng.choice((0, 0x80, 0x180, 0x280, 0x281, 0x7fff, 0x8000, 0xfff0))))   # WORD 7c(A6)
        writes.append(((a6 + 0x76) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x4000, 0xffff))))   # WORD 76(A6)
        writes.append(((a6 + 0x78) & 0xffff, 2, rng.choice((0, 0, 1, 1, 0x100))))        # WORD 78(A6): the player index
        writes.append(((a6 + 0x9e) & 0xffff, 1, rng.randrange(4)))                        # BYTE 9e(A6): the LONG table 1cfce (C4 1cfbe), C5 20796
        for node in (0x100cb8, 0x100da8):
            writes.append((node & 0xffff, 4, rng.choice((0x270e, 0x270e, 0x1ef0e, 0x2143c))))   # 289e: CMPI.L #270e,(A0)
            writes.append(((node + 0x9e) & 0xffff, 1, rng.randrange(4)))
            writes.append(((node + 0x78) & 0xffff, 2, rng.choice((0, 1))))
        # the declared motion record (A0 = rec + 20: LONGs 10 / 14 / 18) and the 4d0cc / 4d1ac record (A4 = rec + 20 or 5cba / 5ce6(A5): WORD 0, 2, 4,
        # 18, BYTE 22, 28, LONG c, 10, 14)
        for off in (0x30, 0x34, 0x38):
            writes.append(((rec + off) & 0xffff, 4, self.value(4)))
        for r4 in (rec + 0x20, a5 + 0x5cba, a5 + 0x5ce6):
            writes.append(((r4) & 0xffff, 2, rng.choice((0, 0, 1, 0x100, 0x8000))))
            writes.append(((r4 + 0x22) & 0xffff, 1, rng.choice((0, 1, 2, 0x80, 0xff))))
            writes.append(((r4 + 0x18) & 0xffff, 2, rng.choice((0, 1, 0x12, 0x1234, 0x8000))))
            writes.append(((r4 + 0x28) & 0xffff, 1, rng.choice((0, 0x01, 0x80, 0x81, 0x7e, 0xff))))
            writes.append(((r4 + 0xc) & 0xffff, 4, rng.choice((0, self.pointer(), 0x12345678))))
        writes.append(((a5 - 0x7ff2) & 0xffff, 2, rng.choice((0, 1, 0x12, 0x1234, 0x8000))))   # WORD -7ff2(A5): compared with WORD 18(A4) (4d0d4)
        writes.append(((a5 + 0x5683) & 0xffff, 1, rng.choice((0, 8, 0xf7, 0xff))))         # BYTE 5683(A5) bit 3: 484b4 Set / Clear
        if rng.random() < 0.8:
            writes.append(((a6 + 0x26) & 0xffff, 4, 0))       # 49fc6: LONG 26(A6) = 0 -> Set without the interpreter (random scripts)
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
            if reg == 6 and (disp in POINTERS or disp in (0xa0, 0xa9, 0x9e, 0x9f, 0x9c, 0x76, 0x78, 0x7c)):
                continue                                        # callback LONG, node links, the pointer fields and the bounded indices stay declared above
            if reg == 5 and disp in (0x5434, 0x5474, 0x5e26, 0x5734, 0x5738):
                continue
            addr = (base_of[reg] + disp) & 0xffffffff
            if not in_ram(addr, size) or (size > 1 and addr & 1):
                continue                                        # never edit the shared stack page (and never fixed ROM)
            writes.append((addr & 0xffff, size, self.value(size) & ((1 << (8 * size)) - 1)))
        writes.append((sp & 0xffff, 4, ret))
        if entry == 0x1d070:
            regs['a7'] = sp - 4                                 # the LONG that 1d066 pushed (above it the return LONG)
            writes.append(((sp - 4) & 0xffff, 4, self.value(4)))
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
            if 'a7' in hint.get('regs', {}):
                pass
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
    require(len(STARTS) == 99 and len(STARTS_SET) == 99, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c8_block', ('start is not routed to player c8', hex(s), unit_of(s)))
    for jmp, handlers in LIST_JUMPS.items():
        require(mine(jmp) and jmp in STARTS, ('JMP (A1) block', hex(jmp)))
        for t in handlers:
            require(t == 0x21e48 or unit_of(t) is not None, ('list handler must be routed (21e48: a declared stop)', hex(t)))
    require(unit_of(0x21e48) is None, 'the list handler 21e48 stays unrouted')
    rng = random.Random(0xC8A8)
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
    sys.stderr.write('pc8 spec: %d fixtures (%d natural), visited %d/99, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out




def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc8: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc8: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts







def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (the BYTE 15 / 61 / 6e /
    88 / 9d / 9e / a7 / a8 bits of the player states, the input bits of D0 and the AND.W #c / #50 masks, the LONG arithmetic of the motion helpers
    (ADD.L carries, SUB.L borrows, the ASR.L count D2 modulo 64 with 0 / 31 / 32 / 33 / 63 / 64 and the sign of the shifted LONG), the N of the popped
    LONG of 1d070, the signed TST.B of 21e52 (BGT / BLT), the WORD compare of 4d0d4 (WORD 18(A4) against WORD -7ff2(A5)), the record of 4d1c6 (BYTE 28
    mask 81, BYTE 15 merge, WORDs 2 / 4 swapped, LONG 10 / 14 carries, the MOVEM.L order), the handlers of the JMP (A1) lists), the upper register bits
    of the WORD / BYTE operations, the node in the upper RAM mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aa0002, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    mirror = [dict(mirror=True)]
    longs = (0, 1, 0x7fffffff, 0x80000000, 0xffffffff, 0x12345678, 0xfffe0000, 0x20)
    if entry in (0x1d01c, 0x1d026, 0x1d034, 0x1d04e, 0x1ef5e, 0x1f45c, 0x4d0d4, 0x4d1c6, 0x1f46c, 0x1fd18, 0x1cffa, 0x1cfee):
        h += [dict(regs=dict(up))]
    # ---- 1ce98 / 1cea2
    if entry == 0x1ce98:
        h += byte(0x15, (0, 1, 0xfe, 0xff))
    if entry == 0x1cea2:
        h += byte(0xa7, (0, 8, 0xf7, 0xff)) + mirror
    # ---- 1cfde .. 1d084 (the motion helpers)
    if entry == 0x1cfde:
        h += byte(0x6e, (8, 0x88, 9, 0, 0xff, 0x18))
    if entry == 0x1cfe8:
        h += [dict(a6off=[(0x3a, 4, 0x12345678), (0x39, 1, 0xff), (0x3e, 1, 0xff)])] + mirror
    if entry == 0x1cfee:
        for a, b in ((0xffffffff, 1), (0x7fffffff, 1), (0x80000000, 0x80000000), (0x12345678, 0), (0, 0xfffffffe)):
            h.append(dict(regrec=dict(a0=0x20), rec=[(0x30, 4, a)], a6off=[(0x3a, 4, b)]))
        h += [dict(regrec=dict(a0=0x20), rec=[(0x30, 4, 5)], mirror=True)]
    if entry == 0x1cffa:
        for v18, v3a, b61 in ((0x1000, 0, 0), (0, 0x1000, 1), (0x80000000, 0, 0), (0, 0x80000000, 1), (0x7fffffff, 0xffffffff, 0), (0x1f, 0, 0),
                              (0xffffffe0, 0, 0xfe), (0xffffffff, 0, 0xff), (0x12345678, 0x12345600, 0)):
            h.append(dict(regrec=dict(a0=0x20), rec=[(0x38, 4, v18), (0x34, 4, 0x5555)], a6off=[(0x3a, 4, v3a), (0x61, 1, b61)],
                          regs=dict(d1=0x9abcdef0, d2=0x12340077)))
    if entry == 0x1d018:
        h += [dict(regrec=dict(a0=0x20), rec=[(0x34, 4, v)]) for v in (0, 0x80000000, 0x12345678)]
    if entry in (0x1d01c, 0x1d02c):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 4, 8, 0xc, 0xfffffff3, 0x12340004, 0x10000)]
    if entry in (0x1d026, 0x1d034):
        for d1, d7 in ((1, 0), (0x80000000, 0), (0xffffffff, 1), (0x7fffffff, 0x80000000), (0x12345678, 0x9abcdef0)):
            h.append(dict(regs=dict(d1=d1, d7=d7, d2=0x12345678)))
    if entry == 0x1d03a:
        for d7, w36, d2 in ((0x1000, 0, 2), (0, 0x1000, 2), (0x80000000, 0, 5), (0x7fffffff, 0xffffffff, 2), (0x40, 0, 0), (0xfffffff0, 0, 0x1f),
                            (0x80000000, 0, 0x20), (0x80000000, 0, 0x21), (0x7fffffff, 0, 0x20), (0xffffffff, 0, 0x3f), (0x12345678, 0, 0x40),
                            (0x12345678, 0, 0x12340005), (0xc0000000, 0, 0x45), (0x40000000, 0, 0x1e)):
            h.append(dict(regs=dict(d7=d7, d2=d2), a6off=[(0x36, 4, w36), (0xa7, 1, (0, 8)[d2 & 1])]))
    if entry == 0x1d04e:
        h += [dict(regs=dict(up, d0=v, d1=0x9abcdef0)) for v in (0, 0x10, 0x40, 0x50, 0xaf, 0x10000, 0xffffffaf, 0x12340040)]
    if entry == 0x1d058:
        for b15, a7 in ((0, 8), (1, 0xff), (0xfe, 0), (0xff, 0xf7)):
            h.append(dict(a6off=[(0x15, 1, b15), (0xa7, 1, a7)]))
        h += mirror
    if entry == 0x1d066:
        h += [dict(a6off=[(0x3a, 4, v)]) for v in (0x80000000, 0x12345678)]
    if entry == 0x1d070:
        for v, b61 in ((0x80000000, 0), (0x7fffffff, 0), (0, 2), (0xffffffff, 0), (0x12345678, 0xfd), (1, 0xff)):
            h.append(dict(stack=[(-4, 4, v)], a6off=[(0x61, 1, b61)]))
    if entry == 0x1d076:
        h += byte(0x61, (0, 2, 0xfd, 0xff))
    if entry == 0x1d080:
        h += [dict(regs=dict(d0=v)) for v in (0x80000000, 0x12345678)] + mirror
    # ---- 1eb98, 1ef4c .. 1ef68
    if entry in (0x1ef4c, 0x1f42e):
        h += byte(0x9e, (0, 1, 0x80))
    if entry in (0x1ef56, 0x1f426, 0x1f438, 0x1f444, 0x1f44c, 0x1f454, 0x21e7c, 0x21e84, 0x21e8c, 0x21e94):
        h += [dict(regs=dict(up, d0=v)) for v in (0, 1, 2, 3, 0x10, 0x20, 0x22, 0x40, 0x50, 0x60, 0x12, 0xffffffdd, 0xffffffad, 0xfffffffc, 0x12340000,
                                                   0xffffffff)]
    if entry in (0x1ef5e, 0x1f45c):
        h += [dict(regs=dict(up, d0=v, d1=0x9abc0000)) for v in (0, 4, 8, 0xc, 0x10000, 0xfff3, 0x12340004, 0xfffffff3)]
    # ---- 1f3d8 .. 1f486
    if entry in (0x1f3f0, 0x1fcd4, 0x1fcce):
        h += [dict(a6off=[(0x64, 4, 0x12345678), (0x7a, 2, 0x8001), (0x9c, 1, 0xff), (0xaa, 1, 0xff), (0xa9, 1, 0xff), (0x61, 1, 0xff), (0x5e, 1, 0xff),
                          (0x56, 4, 0xffffffff), (0x90, 2, 0xffff), (0x8f, 1, 0xff), (0x92, 1, 0xff)])] + mirror
        h += [dict(a6off=[(0x61, 1, v)]) for v in (0x80, 0x7f)]
    if entry in (0x1f41c, 0x1fb1e):
        h += byte(0x15, (0x80, 0x7f, 0, 0xff))
    if entry in (0x1f46c, 0x1fb0e):
        h += [dict(regs=dict(up), a6off=[(0x1e, 2, v)]) for v in (0, 0x8000)]
    if entry == 0x1f480:
        h += mirror
    # ---- 1f756 / 1f764, 1fa68 .. 1fb2e
    if entry == 0x1f756:
        h += byte(0x88, (0, 1, 0x80, 0xff)) + mirror
    if entry in (0x1f764, 0x1fa80, 0x1fafc, 0x201c6, 0x21e62):
        h += mirror
    if entry == 0x1fa80:
        h += [dict(a6off=[(0x9c, 1, 0xff), (0xa9, 1, 0xff), (0x9b, 1, 0xff), (0x9d, 1, 0xff), (0xa8, 1, 0xff), (0xaa, 1, 0xff)])]
    # ---- 1fcce .. 1fd38, 201bc
    if entry == 0x1fd18:
        for a8, w78 in ((0, 0), (8, 1), (0xf7, 0x100), (0xff, 0x8000)):
            h.append(dict(regs=dict(up), a6off=[(0xa8, 1, a8), (0x78, 2, w78)]))
    if entry == 0x201bc:
        h += byte(0xa7, (0, 0x80, 0x7f, 0xff))
    # ---- 21d9e, 21e3a .. 21e9c
    if entry == 0x21d9e:
        h += [dict(regs=dict(a1=v)) for v in LIST_21B0A]
    if entry == 0x21e76:
        h += [dict(regs=dict(a1=v)) for v in LIST_21B3C]
    if entry == 0x21e3a:
        h += [dict(a6off=[(0xaa, 1, 0), (0xa9, 1, 0xff), (0xab, 1, 0xff), (0x9d, 1, 0)])] + mirror
    if entry == 0x21e52:
        h += byte(0x9d, (0, 1, 0x7f, 0x80, 0xff))
    if entry == 0x21e6a:
        h += byte(0x9c, (0, 1, 2, 3, 0xff))
    # ---- 4d0cc .. 4d0f6 (A4 = rec + 20), 4d1ac .. 4d206
    if entry == 0x4d0cc:
        h += [dict(regrec=dict(a4=0x20), rec=[(0x42, 1, v)]) for v in (0, 1, 0x80, 0xff)]
    if entry == 0x4d0d4:
        for w18, w7ff2 in ((0x1234, 0x1234), (0x1234, 0x1235), (0x12, 0x1212), (0x8000, 0x8000), (0, 0), (0xff00, 0x0000)):
            h.append(dict(regrec=dict(a4=0x20), rec=[(0x38, 2, w18)], a5off=[(-0x7ff2, 2, w7ff2)], regs=dict(up)))
    if entry in (0x4d0ea, 0x4d0f6):
        h += [dict(regrec=dict(a4=0x20), rec=[(0x20, 2, 0x1234), (0x42, 1, 0x55), (0x41, 1, 0xff), (0x43, 1, 0xff), (0x1f, 1, 0xff), (0x22, 1, 0xff)])]
    if entry == 0x4d1ac:
        h += [dict(a6off=[(0x78, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x4d1c0:
        h += [dict(regrec=dict(a4=0x20), rec=[(0x20, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x4d1c6:
        for b28, b15, w2, w4, l10, l14 in ((0x81, 0, 0x8000, 0xffff, 0x80000000, 0xffffffff), (0x7e, 0xff, 1, 2, 0xffff, 0x10000),
                                           (0xff, 0x7e, 0xffff, 0x8000, 0x7fffffff, 0x80000000), (0, 0x81, 0x1234, 0x5678, 0x12345678, 0xedcba988),
                                           (0x01, 0x80, 0, 0, 0, 0)):
            h.append(dict(regrec=dict(a4=0x20), rec=[(0x48, 1, b28), (0x22, 2, w2), (0x24, 2, w4), (0x30, 4, l10), (0x34, 4, l14), (0x2c, 4, 0x10e9f0)],
                          a6off=[(0x15, 1, b15)], regs=dict(up)))
        h += [dict(regrec=dict(a4=0x20), rec=[(0x48, 1, 0x81)], mirror=True)]
    if entry == 0xea626:
        h += [dict(a5off=[(0x5e50, 1, 0), (0x5e4f, 1, 0x12), (0x5e51, 1, 0x34)])]
    return h


# chain hints: let the real producers return both C values (where a routed path gives both)
def rom_word(addr):
    if not _CS:
        decode(0)
    p = _CS[1]
    return (p[addr] << 8) | p[addr + 1]





def chain_hint(entry, t, rng):
    if entry == 0x1f476:
        return dict(a6off=[(0x26, 4, 0)]) if t % 2 else None                         # 49fc6: LONG 26(A6) = 0 -> Set (else the script decides)
    if entry == 0x1fa68:
        # 1cb08 on the ROM WORD table 1b716: W = WORD (1b716 + 2 x BYTE 9f); 0 -> Clear; else C5 1cb1a: TST.L (LONG 22(A6) + 4 x WORD (1b716 + W))
        k = (0, 5, 0xc, 0xd, 0xe, 0xf, 0x10)[(t // 2) % 7]          # 1b716: the WORDs 0..b are 0 (Clear), c..10 not 0
        w = rom_word(0x1b716 + 2 * k)
        idx = (4 * rom_word(0x1b716 + w)) & 0xffff if w else 0
        return dict(a6off=[(0x9f, 1, k), (0x22, 4, SCR)], writes=[((SCR + idx) & 0xffff, 4, (0, 0x12345678)[t % 2])] if idx < 0x400 else [])
    if entry in (0x1fd2e, 0x4d0e0):
        # 484b4: BTST.B #3,5683(A5) -> Set / Clear; 4d0e6 Set -> 4d0ea writes BYTE 22(A4), Clear -> 4d0f6 writes WORD (A4) / BYTE 22(A4)
        return dict(a5off=[(0x5683, 1, (0, 8, 0xf7, 0xff)[t % 4])], regrec=dict(a4=0x20))
    if entry == 0x21e6a:
        # 215e6 on the ROM list 21b3c: key BYTE 9c 0 / 1 / 2 -> Set (A1 the handler); else Clear
        return dict(a6off=[(0x9c, 1, (0, 1, 2, 3, 0xff, 4)[t % 6])])
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
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
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
            # BYTE 1d(A6) < 4 (8ebe / 8ff4), WORD 78 (the player index), BYTE 15 bits 7 / 0 (1f41c / 1fb1e / 1ce98 / 1d058), BYTE 9e (1f42e, the
            # table 1cfce), BYTE 88 (1f756), BYTE a7 bits 3 / 7 (1d03a / 201bc), BYTE 61 bits 0 / 1 (1cffa / 1d076), BYTE 6e (1cfde), BYTE 9d (21e52),
            # LONG 26 (0: 49fc6 Set), BYTE 5683(A5) bit 3 (484b4), WORD 5cba / 5ce6(A5) (4d0a4 / 4d1c0)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x78, 2, (0, 1)[t % 2]), (0x15, 1, (0, 0x80, 1, 0x81, 0xff)[t % 5]), (0x9e, 1, (0, 1)[(t // 2) % 2]),
                               (0x88, 1, (0, 1)[(t // 3) % 2]), (0xa7, 1, (0, 8, 0x80, 0x88)[(t // 4) % 4]), (0x61, 1, (0, 1, 2, 3)[(t // 3) % 4]),
                               (0x6e, 1, (8, 0)[(t // 5) % 2]), (0x9d, 1, (0, 0, 1, 0x80)[(t // 7) % 4])] + ([(0x26, 4, 0)] if t % 5 != 4 else []),
                        a5off=[(0x5683, 1, (0, 8)[(t // 2) % 2]), (0x5cba, 2, (0, 1)[(t // 6) % 2]), (0x5ce6, 2, (1, 0)[(t // 6) % 2])])
            st = world.make(entry, base.stop, flds, hint)
            ret = base.stop
            st = U.with_host_writes(st, [((st['regs']['a6']) & 0xffff, 4, entry)])
            tr = trace(st, first_unrouted(extra=(ret,)), cap=400000)
            if tr is None or 0x290e in tr['pcs']:
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
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
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
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
    require(count >= 12, ('too few natural node fixtures', count))


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
                continue                                    # 290e: the 28ae failure inside 2986, the C++ caller-X checked error (C7 decision 6)
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
    err('odd-pc', U.with_host_writes(st, pc=0x1ce99), 'unaligned animation machine PC', 0x1ce99)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    rec = SCR
    # the JMP (A1) (contract decision 2): A1 outside the list of the jump; the unrouted handler 21e48 fails at the next dispatch (the paired row stops there)
    for v in (0x21d60, 0x21e3b, 0, 0x121602, 0x21e52, 0x1021e3a):
        err('21d9e-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21d9e), ERROR_JUMP, 0x21d9e)
    for v in (0x21e3a, 0x21e48, 0, 0x21d61, 0x1021602):
        err('21e76-a1-%x' % v, U.with_host_writes(st, regs=dict(a1=v), pc=0x21e76), ERROR_JUMP, 0x21e76)
    err('21d9e-a1-21e48-entry', U.with_host_writes(st, regs=dict(a1=0x21e48), pc=0x21d9e), unrouted, 0x21e48)
    # odd node / stack / A0 / A4: the entry block fails (the row's stop is the PC right after the failing block)
    err('1f3f0-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1f3f0), odd_write, 0x1f3f0, stop=0x1f418)
    err('1fcce-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1fcce), odd_write, 0x1fcce, stop=0x1fcd4)
    err('4d1c6-odd-node', U.with_host_writes(st, [((rec + 0x28) & 0xffff, 1, 0)], regs=dict(a6=a6 + 1, a4=rec), pc=0x4d1c6), odd_write, 0x4d1c6,
        stop=0x43e34)
    err('1cfee-odd-a0', U.with_host_writes(st, regs=dict(a0=rec + 1), pc=0x1cfee), odd_word, 0x1cfee)
    err('1cffa-odd-a0', U.with_host_writes(st, regs=dict(a0=rec + 1), pc=0x1cffa), odd_word, 0x1cffa, stop=0x1d018)
    err('4d0d4-odd-a4', U.with_host_writes(st, regs=dict(a4=rec + 1), pc=0x4d0d4), odd_word, 0x4d0d4, stop=0x4d0e0)
    err('4d1c0-odd-a4', U.with_host_writes(st, regs=dict(a4=rec + 1), pc=0x4d1c0), odd_word, 0x4d1c0, stop=0x4d1c6)
    err('1d066-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d066), odd_word, 0x1d066, stop=0x4be82)
    err('1d070-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d070), odd_word, 0x1d070, stop=0x1d076)
    err('ea626-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0xea626), odd_word, 0xea626)
    # failures after executed blocks:
    #   1f45c (D0.W & c) -> 1f48a (deferred, unrouted); 1fb1e (BYTE 15 bit 7) -> 1fb28; 21e52 (BYTE 9d 1 / 80) -> 21ea0 / 21d0e; 21e7c .. 21e94
    #   (D0 bits 0 / 1 / 4) -> 223a0 / 223d6 / 2210c
    err('1f45c-then-1f48a', U.with_host_writes(st, regs=dict(d0=4), pc=0x1f45c), unrouted, 0x1f48a)
    err('1fb1e-then-1fb28', U.with_host_writes(st, [((a6 + 0x15) & 0xffff, 1, 0x80)], pc=0x1fb1e), unrouted, 0x1fb28)
    err('21e52-then-21ea0', U.with_host_writes(st, [((a6 + 0x9d) & 0xffff, 1, 1)], pc=0x21e52), unrouted, 0x21ea0)
    err('21e52-then-21d0e', U.with_host_writes(st, [((a6 + 0x9d) & 0xffff, 1, 0x80)], pc=0x21e52), unrouted, 0x21d0e)
    err('21e7c-then-223a0', U.with_host_writes(st, regs=dict(d0=1), pc=0x21e7c), unrouted, 0x223a0)
    err('21e84-then-223d6', U.with_host_writes(st, regs=dict(d0=2), pc=0x21e84), unrouted, 0x223d6)
    err('21e8c-then-2210c', U.with_host_writes(st, regs=dict(d0=0x10), pc=0x21e8c), unrouted, 0x2210c)
    #   RTS at an odd A7 after executed blocks: 1d04e (D0 & 50 = 0) -> 1d064; 1d076 (BYTE 61 bit 1) -> 1d084; 4d1c0 (WORD (A4) = 0) -> 4d206
    err('1d04e-then-1d064', U.with_host_writes(st, regs=dict(a7=a7 + 1, d0=0), pc=0x1d04e), odd_word, 0x1d064)
    err('1d076-then-1d084', U.with_host_writes(st, [((a6 + 0x61) & 0xffff, 1, 2)], regs=dict(a7=a7 + 1), pc=0x1d076), odd_word, 0x1d084)
    err('4d1c0-then-4d206', U.with_host_writes(st, [((rec) & 0xffff, 2, 0)], regs=dict(a7=a7 + 1, a4=rec), pc=0x4d1c0), odd_word, 0x4d206)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x1d03a, 0x4d1c6, 0x1cffa, 0x4d0d4)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
