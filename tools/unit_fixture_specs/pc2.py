"""V1 fixture spec of the area-C unit C2 (engine/src/animation_machine_player_c2.cpp, 196 block starts; file prefix pc2 / player_c2 so that the
controller units C1..C3 keep their names).

Blocks (contract docs/analysis/animation-machine-player-c2-contract.md, plan docs/analysis/area-c-completion-plan.md section 4.2 and the C2 spec of the
contract): the player object main state 1d222 (the BCS side of the C1 block 1d21c: node reset, the start pose from 1aa3a, the lights 1d15a / 1d0c2,
the record e8b5a (C3) / ea5f0 / the 2986 child 6f1c4) and its later states 1ddd0..1de38, 1ed78 / 1edb0 (state machine head; 1edb0 is the installed
callback of the IO runs), 1f1d8..1f2a0, 1f7a4..1f80c, 1fa3c..1fafc, the helpers 1a9e8 (live JMP (A1) 1aa38, contract decision 2), 1c1e2 (BYTE table
1c1d8), 1cab6 / 1cabe (record table -> interpreter 49f96), 1cb08, 1cd12, 1cd98 (input summary; BYTE tables 22642 / 1cd94), 1d0c2, 1d15a (LONG tables
1d112 / 1d136), 1d1d0, 1d582, 1dbd8, 1dfe6 and 1ed34 (LONG 1ed70 / 1ed74).  No BRA.W jump table.

Seeds.  The declared worlds are the natural N28 node (callback 2b99c) of the D1 seeds 116/117 frame 2 (as FR1a..FR9, C1) with declared host edits.
This code runs natively only in the IO observation (P1 / boot-title-start / boot-demo-0): the 'natural' family takes the frame-start states of the IO
native observation in which a node holds one of the unit's callbacks (1edb0 at 100cb8), keeps their RAM / PVC / bank and declares only the registers
(A5 = 108000, A6 = that node, A7 = 10ef00 with the sentinel return LONG, PC = the callback); the 'reinstall' family takes the frame in which the C1
callback 1d20c of 100cb8 reaches 1d21c BCS 1d222 natively and enters 1d222 / 1ed78 / 1edb0 on that node with one declared callback LONG.

Fixture families (native Unicorn on the original ROM versus the C++ run, V1 comparison of RAM, D0-D7/A0-A7, PC, bank, PVC, ordered ports, waits, reads):
  block     every block start except the 8 C consumers is entered directly (the seed world with declared edits).  Stop: the first PC outside the unit.
  coverage  worlds that reach a conditional branch outcome that the block fixtures did not take.
  chain     the C consumers entered through their REAL producers: 4836e -> 1d58e (1d588), 49c38 -> 1d59c (1d592), 1cb08 / RTS 1cb18 -> 1ed80 (1ed78) and
            1fa44 (1fa3c) (Clear only: the Set side needs the C5 block 1cb1a), 49fc6 -> 1f296 / 1f802 / 1fac0 (1f290 / 1f7fc / 1faba).  1d1d6 (48384 of
            C3) has no routed producer.  Stop: the consumer's successor or the first unrouted PC.
  node      the callbacks and installed values ((A6) := entry, PC := entry) up to the dispatcher return or the first unrouted PC.
  natural   the IO-pack natural nodes (see Seeds) up to the sentinel or the first unrouted PC; reinstall: the same with a declared callback LONG.
  callee    the helpers entered as subroutines (return LONG = sentinel).
  error     every even non-start PC of the unit ranges, an odd PC, Unknown C at the 8 consumers, odd node / stack / A0 / A4, live JMP (A1) targets that
            are not routed block starts, failures after executed blocks: checked error, state preserved, every row with its failing PC (a paired
            'failpc' match row when it differs from the entry and is even).
  negative  C++ input differs from the native input in one RAM bit / one register / the stop / the queue: the comparison must report it.
Carry: the V1 comparison has no SR oracle; carry_oracle() checks the C++ known-C tags against the native C flag at the stop (as the B2b..FR9, C1 specs do).
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
BASE_CALLBACKS = (0x2b99c,)             # the natural N28 node (FR1a..FR9, C1)
POINTER_NODES = (0x38c36, 0x3b166, 0x331d8, 0x30de4, 0x3d32c)   # other natural nodes of the same frame: child / parent / record pointers
MAX_TRIES = 220
CAP_INSN = 60000
SCRATCH = 0x800000                      # native scratch page for the SR read (outside every mapped region)
UNIT_NAME = 'pc2'
ERROR_PC = 'unsupported animation player c2 PC'
ERROR_CARRY = 'player c2 caller requires known carry'

RANGES = [(0x1a9e8, 0x1aa3a), (0x1c1e2, 0x1c1f4), (0x1cab6, 0x1cafe), (0x1cb08, 0x1cb1a), (0x1cd12, 0x1cd94), (0x1cd98, 0x1cde0), (0x1cdea, 0x1cdf0),
          (0x1cdfe, 0x1ce98), (0x1cea8, 0x1ceb0), (0x1cec0, 0x1cec2), (0x1cef8, 0x1cefa), (0x1d0c2, 0x1d112), (0x1d15a, 0x1d182), (0x1d1d0, 0x1d1f4),
          (0x1d222, 0x1d398), (0x1d45a, 0x1d468), (0x1d582, 0x1d5ac), (0x1dbd8, 0x1dbf0), (0x1ddd0, 0x1ddd8), (0x1ddfc, 0x1de3c), (0x1dfe6, 0x1e01a),
          (0x1ed34, 0x1ed70), (0x1ed78, 0x1ee00), (0x1eee0, 0x1eeea), (0x1f1d8, 0x1f2a4), (0x1f7a4, 0x1f810), (0x1fa3c, 0x1fa68), (0x1fa90, 0x1fafc)]
STARTS = sorted(int(x, 16) for x in (
    '1a9e8 1a9f2 1a9fe 1aa0c 1aa16 1aa20 1aa2a 1aa2c 1c1e2 1cab6 1cabe 1cac2 1cad2 1cad4 1caea 1caf0 1cb08 1cb18 1cd12 1cd1a 1cd1c 1cd28 1cd2a 1cd4e '
    '1cd50 1cd56 1cd58 1cd6a 1cd70 1cd78 1cd7c 1cd98 1cda6 1cdb0 1cdba 1cdc8 1cdd2 1cdd8 1cdea 1cdfe 1ce08 1ce1a 1ce26 1ce2a 1ce34 1ce48 1ce4c 1ce50 '
    '1ce5a 1ce5e 1ce62 1ce6a 1ce6e 1ce80 1cea8 1cec0 1cef8 1d0c2 1d0ca 1d0e0 1d0f6 1d10a 1d15a 1d160 1d16c 1d170 1d1d0 1d1d6 1d1da 1d1e2 1d1f2 1d222 '
    '1d22a 1d2d4 1d2de 1d2e6 1d2f0 1d2f2 1d2fa 1d2fc 1d304 1d306 1d30c 1d310 1d314 1d31e 1d326 1d32e 1d344 1d352 1d364 1d380 1d390 1d45a 1d466 1d582 '
    '1d588 1d58e 1d592 1d59c 1d5a0 1d5aa 1dbd8 1dbde 1dbe8 1dbee 1ddd0 1ddd4 1ddfc 1de00 1de06 1de0a 1de28 1de30 1de38 1dfe6 1dff0 1dff6 1e006 1e014 '
    '1e016 1ed34 1ed3c 1ed3e 1ed48 1ed4a 1ed54 1ed5a 1ed68 1ed6a 1ed78 1ed80 1ed84 1ed8e 1ed96 1edb0 1edb4 1edbe 1edc6 1edd0 1edd8 1ede2 1ede6 1edee '
    '1edf6 1eee0 1f1d8 1f1e8 1f1f4 1f1f8 1f1fc 1f224 1f228 1f230 1f23a 1f244 1f254 1f25a 1f268 1f26e 1f278 1f280 1f286 1f290 1f296 1f29a 1f2a0 1f7a4 '
    '1f7ac 1f7da 1f7de 1f7e2 1f7ec 1f7f2 1f7fc 1f802 1f806 1f80c 1fa3c 1fa44 1fa48 1fa50 1fa58 1fa90 1fa94 1faa0 1faaa 1fab0 1faba 1fac0 1fac4 1fac8 '
    '1face 1fad2 1fae0 1fae8').split())
CONSUMERS = (0x1d1d6, 0x1d58e, 0x1d59c, 0x1ed80, 0x1f296, 0x1f802, 0x1fa44, 0x1fac0)
CLEAR_SET = (0x1cb08, 0x1dff0, 0x1ed54, 0x1edf6)   # 1cb08 MOVE.W / 1edf6 AND.W leave C Clear; 1dff0 1ed54 ANDI.B #fe,CCR; RTS return Clear
SET_SET = ()
UNKNOWN_AFTER = ()
CLEAR_AFTER = ()
SCC_VALUE = {}
DATA_SET = (0x1e016,)                   # SUB.W D1,D0; RTS: the borrow (unsigned D0.W < D1.W) returned to the caller
INVERT_SET = ()
PASS_SET = (0x1cb18, 0x1ed34, 0x1ed3c, 0x1ed3e, 0x1ed48)   # RTS / BTST blocks that keep the incoming C (carry preserving, not consumers)
STARTS_SET = set()
Z_RECOMPUTE = {}
C_RECOMPUTE = {}
STATIC_IMPOSSIBLE = set()
# outcomes that need a producer of a later unit: 48384 (C3) for 1d1d6, the C5 block 1cb1a (Set) for the 1cb08 callers 1ed80 / 1fa44; the declared-C rows
# of the C++ unit test and the real-ROM differential cover them
LATER_GATED = {(0x1d1d6, 0x1d1da), (0x1d1d6, 0x1d1f2), (0x1ed80, 0x1ed84), (0x1fa44, 0x1fa90)}
# consumers without a routed producer (1d1d6: only after JSR 48384, unit C3): never entered by a native V1 run; the C++ unit test enters them with a declared
# C, the real-ROM differential with a declared C and the native SR C, and the error family with an Unknown C
GATED_CONSUMERS = (0x1d1d6,)
TRAPS = ()
# PCs of later units (and deferred leaders) that a C2 block reaches by a fall-through, a branch, a call or a return (declared stops of the native runs:
# a straight-line unrouted PC after a C2 block is not the interior of a routed block)
EXIT_STOPS = (0x1cb1a, 0x1cb38, 0x1cde0, 0x1cdf0, 0x1ce98, 0x1cfde, 0x1ceb0, 0x1cec2, 0x1d398, 0x1ebbe, 0x1ee00, 0x1eeea, 0x1f2a4, 0x1fa68, 0x1fafc,
              0x201a2, 0x48384, 0xe8b5a, 0x1de3c, 0x1e21c, 0x1e8de)
# later-unit stops routed since (player C3: 1ee00 201a2 48384 e8b5a 1cde0 1cdf0; player C4: 1ceb0 1cec2 1eeea; player C5: 1cb1a 1cb38; player C6: 1d398
# 1ebbe): still declared stops of the C2 runs
ROUTED_LATER = (0x1ee00, 0x201a2, 0x48384, 0xe8b5a, 0x1cde0, 0x1cdf0, 0x1ceb0, 0x1cec2, 0x1eeea, 0x1cb1a, 0x1cb38, 0x1d398, 0x1ebbe)
# producer -> consumer chains: entry block (the call of the producer) and the consumer it returns to
CHAINS = ((0x1d588, 0x1d58e), (0x1d592, 0x1d59c), (0x1ed78, 0x1ed80), (0x1fa3c, 0x1fa44), (0x1f290, 0x1f296), (0x1f7fc, 0x1f802), (0x1faba, 0x1fac0))
CHAIN_49FC6 = (0x1f290, 0x1f7fc, 0x1faba)
PASS_CHAINS = ()
TABLE_JUMPS = {}
JUMP_PCS = (0x1aa38,)                   # JMP (A1): live target (contract decision 2)
TABLE_ENTRIES = ()
# callbacks and installed values (node callbacks); 1d222 is the C1 BCS continuation on the same node; the callee entries (helpers entered as subroutines)
NODE_ENTRIES = (0x1d222, 0x1ed78, 0x1edb0, 0x1f224, 0x1f7da, 0x1faaa, 0x1fae8, 0x1d466)
CALLEES = (0x1a9e8, 0x1c1e2, 0x1cab6, 0x1cabe, 0x1cb08, 0x1cd12, 0x1cd98, 0x1cdfe, 0x1cef8, 0x1d0c2, 0x1d15a, 0x1d1d0, 0x1d582, 0x1dbd8, 0x1dfe6,
           0x1ed34)
POINTERS = (0x0, 0x4, 0x8, 0xc, 0x22, 0x26, 0x3e, 0x8c, 0x94)   # node links and pointer fields: natural or declared below
MAPS = (0x109156, 0x10b1d6, 0x10d256, 0x10d2d6)                 # 1a9fe..1aa20: LONG 3e(A6) compared with the four map buffers
NATURAL = tuple([('P1', 94, f) for f in (193, 194, 200, 218)] + [('P1', 68, f) for f in (409, 410, 434)] +
                [('P1', 106, f) for f in (193, 205)] + [('boot-title-start', None, f) for f in (313, 314, 338)] + [('boot-demo-0', None, f) for f in (382, 383)])
NATURAL_NODES = (0x100800, 0x104c00)    # the node pool searched for callback LONGs (work RAM CPU addresses)
# reinstall worlds: (config, case, frame, node, callback LONG written into (node)); the frame is the one in which 1d21c BCS 1d222 runs natively
REINSTALL = (('P1', 94, 192, 0x100cb8, 0x1d222), ('P1', 68, 408, 0x100cb8, 0x1d222), ('boot-title-start', None, 312, 0x100cb8, 0x1d222),
             ('boot-demo-0', None, 382, 0x100cb8, 0x1d222), ('P1', 94, 192, 0x100cb8, 0x1ed78), ('P1', 68, 408, 0x100cb8, 0x1ed78),
             ('boot-title-start', None, 312, 0x100cb8, 0x1ed78), ('P1', 94, 193, 0x100cb8, 0x1f224), ('P1', 94, 193, 0x100cb8, 0x1f7da),
             ('P1', 94, 193, 0x100cb8, 0x1faaa), ('P1', 94, 193, 0x100cb8, 0x1fae8))

VB = (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xa, 0xb, 0x10, 0x11, 0x1d, 0x1e, 0x1f, 0x20, 0x77, 0x78, 0x79, 0x7f, 0x80, 0x81, 0xfe, 0xff)
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
BUNDLED = ()                            # no bundled Bcc pair in this unit


def block_instrs(start):
    """Instruction records (addr, mnemonic, op_str, size, full mnemonic) of the block at `start`: up to a branch / call / return, the next block start or
    the end of the unit range (1cdea falls to 1cdf0 (C7), 1fae0 to 1fae8, 1de00 to 1de06)."""
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
    """Static successors of the entry block (None = computed: RTS, JMP (A1))."""
    instrs = block_instrs(start)
    a, mn, op, size, _ = instrs[-1]
    if BCC.match(mn) or mn == 'dbra':
        return {target(op), a + size}
    if mn in ('bra', 'jmp', 'jsr', 'bsr') and target(op) is not None and '(pc, d' not in op and '(a' not in op:
        return {target(op)}
    if mn in ('rts', 'jsr', 'jmp'):
        return None
    return {a + size}


def block_next(entry, n, tr):
    """The PC after the entry block: pcs[n] (no bundled Bcc pair in this unit)."""
    pcs = tr['pcs']
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
    """Stop at the sentinel, at 2a00 / 2a24 (object removal), at an extra PC, at the declared later-unit stops EXIT_STOPS, at a target of the live JMP
    (A1) 1aa38 that is not a routed block start of this unit (the C++ dispatch of such a target is the checked PC error), or at the first unrouted PC
    that is not the straight-line successor of the previous instruction (a PC inside a block of another executor is not a block entry)."""
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

    def jump_target(self):
        """A value for LONG 5434(A5) (the A1 of the live JMP (A1) 1aa38): 0 (the only value the ROM writes), the routed C2 start 1c1e2, the unrouted C3
        start 1ee00, the C2 interior PC 1ce0e (contract decision 2: a non-start target is the checked PC error).  Never a RAM address: the native machine
        does not fetch from work RAM."""
        return self.rng.choice((0, 0, 0, 0x1c1e2, 0x1ee00, 0x1ce0e))

    def make(self, entry, ret, flds, hint=None):
        rng = self.rng
        base = rng.choice(self.bases)
        st = base.state
        regs = dict(st['regs'])
        a6 = regs['a6']
        a5 = regs['a5']
        for k in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
            regs[k] = self.value(rng.choice((1, 2, 4))) if rng.random() < 0.8 else rng.getrandbits(32)
        if rng.random() < 0.5:
            regs['d0'] = rng.choice((0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0xc, 0x1c, 0xc8, 0x400, 0xffff, 0x12345678, 0x10000))   # input summary bits
        writes = []
        regs['a0'] = self.pointer()
        regs['a1'] = rng.choice((0x1c1e2, 0x1ee00, 0x201a2))     # A1 is only the JMP (A1) target in this unit (1cab6 / 1d352 set their own A1)
        regs['a2'] = self.pointer()
        regs['a3'] = self.pointer()
        regs['a4'] = self.pointer()
        sp = regs['a7']
        writes.append(((a6 + 0xc) & 0xffff, 4, self.pointer()))     # the parent LONG c(A6)
        writes.append(((a6 + 0x8c) & 0xffff, 4, self.pointer()))    # LONG 8c(A6) (A4 of 1cd98 / 1d2de / 1d32e / 1f1e8)
        writes.append(((a6 + 0x22) & 0xffff, 4, self.pointer()))    # LONG 22(A6) (the LONG table of 1cad4)
        writes.append(((a6 + 0x3e) & 0xffff, 4, rng.choice(MAPS + (self.pointer(),))))   # LONG 3e(A6) (1a9fe..1aa20)
        writes.append(((a5 + 0x5434) & 0xffff, 4, self.jump_target()))                     # LONG 5434(A5): A1 of JMP (A1)
        writes.append(((a5 + 0x5474) & 0xffff, 4, rng.choice((0, self.pointer()))))       # LONG 5474(A5): A0 of 1cd2a
        if rng.random() < 0.5:
            writes.append(((a6 + 0x1d) & 0xffff, 1, rng.choice((0, 1, 2, 3))))     # 8ebe / 8ff4: BYTE 1d(A6) < 4 (callee worlds)
        base_of = {6: a6, 0: regs['a0'], 1: regs['a1'], 2: regs['a2'], 3: regs['a3'], 4: regs['a4'], 5: a5}
        for reg, disp, size in flds:
            if reg not in base_of or rng.random() < 0.4:
                continue
            if reg == 6 and disp in POINTERS:
                continue                                        # callback LONG, node links and the pointer fields stay natural or declared above
            if reg == 5 and disp in (0x5434, 0x5474):
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
    require(len(STARTS) == 196 and len(STARTS_SET) == 196, ('starts', len(STARTS), len(STARTS_SET)))
    require(unit_of(SENTINEL) is None and not mine(SENTINEL), 'sentinel must be unrouted')
    for t in TRAPS + EXIT_STOPS:
        # player C3 refresh: 1ee00 201a2 48384 e8b5a 1cde0 1cdf0 are C3 block starts now (routed); they stay declared stops of the C2 runs so that the C2 fixture set
        # is unchanged (was: every later-unit stop unrouted)
        require((unit_of(t) is None or t in ROUTED_LATER) and not mine(t), ('later-unit stop must stay unrouted', hex(t)))
    for s in STARTS:
        require(unit_of(s) == 'animation_player_c2_block', ('start is not routed to player c2', hex(s), unit_of(s)))
    rng = random.Random(0xC2A2)
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
                cond_points[a] = set(t for t in (target(op), a + size) if (a, t) not in STATIC_IMPOSSIBLE and (s, t) not in LATER_GATED)
    # ---- block fixtures
    stats = dict(tries=0, rejected=0)
    for entry in STARTS:
        if entry in CONSUMERS:
            continue                                            # a consumer needs the C of its producer: chain fixtures (a direct entry is an error fixture)
        n = len(block_instrs(entry))
        needed = static_next(entry)
        flds = fields_of(entry)
        kept = {}
        extra = 0
        hints = hint_worlds(entry, world)
        for t in range(MAX_TRIES + len(hints)):
            stats['tries'] += 1
            st = world.make(entry, SENTINEL, flds, hints[t] if t < len(hints) else None)
            tr = trace(st, outside_unit())
            if tr is None or len(tr['pcs']) < n:
                stats['rejected'] += 1
                continue
            record(tr['pcs'] + [tr['stop']])
            nxt = block_next(entry, n, tr)
            if nxt in CONSUMERS and entry not in DATA_SET and entry not in CLEAR_SET and entry not in PASS_SET:
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
            missing = sorted(needed - set(k for k in kept if isinstance(k, int)) - set(t for a, t in STATIC_IMPOSSIBLE) - set(CONSUMERS))
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
        cands = sorted([e for e in entries_for.get(blk, [blk]) if e not in CONSUMERS], key=lambda e: (e != blk, e))
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
    META['chain_only'] = [hex(x) for x in CONSUMERS]
    META['static_impossible'] = [(hex(a), hex(t)) for a, t in sorted(STATIC_IMPOSSIBLE)]
    META['later_gated'] = [(hex(a), hex(t)) for a, t in sorted(LATER_GATED)]
    META['gated_consumers'] = [hex(x) for x in GATED_CONSUMERS]
    META['out_missing'] = [(hex(e), [hex(x) for x in m]) for e, m in out_missing]
    META['unreachable'] = [(hex(a), hex(t)) for a, t in unreachable]
    META['stats'] = stats
    sys.stderr.write('pc2 spec: %d fixtures (%d natural), visited %d/196, missing successors %s, unreachable outcomes %s, later-unit gated %s\n' % (
        len(out), sum(1 for fx in out if fx.meta.get('family') in ('natural', 'reinstall')), META['visited_starts'], META['out_missing'], META['unreachable'],
        META['later_gated']))
    return out


def carry_oracle(fixtures):
    """Known-C check that the V1 comparison does not make: for every 'match' fixture the C++ run's carry tag (Clear / Set) must equal the C flag of the original
    CPU (Unicorn SR) at the stop PC.  Skipped (None) when the harness binary of this checkout is not built yet."""
    exe = U.BUILD / 'unit_fixture_acceptance'
    if not exe.exists():
        sys.stderr.write('pc2: carry oracle skipped (no harness binary)\n')
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
    sys.stderr.write('pc2: carry oracle ok, final tags Unknown/Clear/Set = %d/%d/%d\n' % (counts[0], counts[1], counts[2]))
    return counts


def hint_worlds(entry, world=None):
    """Declared edits that a random world does not reach by chance: the boundary values of the compares / tests of the unit (CMPI.B ties and the unsigned
    BCC of CMPI.B #78, the BTST / BSET / BCLR bits of the node BYTEs and of D0 / D1 (input summary: bit 10 of D1 is a register bit), the four map
    buffers of 1a9fe..1aa20 and A1 = 0, the record table WORDs 0 / not 0 and the signed LEA (A0,D7.W), the LONG table entry 0 (default script 1cafe),
    the unsigned CMP.W / CMP.B of 1cd2a / 1cd50 / 1ce1a, the SMI / SEQ / EOR.B of 1cd2a / 1cd58, the BYTE table indices of 1c1e2 / 1ce08 / 1ce6e / 1d170,
    the ADDQ.B wrap of a2 (ff saturates), SUBI.W #1e boundary, the SUB.W borrow of 1e016, the SUB.L / BMI / ASR.L #5 of 1f244..1f26e, the popped WORD
    of 1d380 (1 / 4 / other), CMPI.W #0 of D7, CMPI.B #10 / #11), the upper register bits of the WORD / BYTE operations, the node in the upper RAM
    mirror.  Every hint world is kept as a fixture (forced)."""
    h = []
    byte = lambda off, vals: [dict(a6off=[(off, 1, v)]) for v in vals]
    word = lambda off, vals: [dict(a6off=[(off, 2, v)]) for v in vals]
    long_ = lambda off, vals: [dict(a6off=[(off, 4, v)]) for v in vals]
    regs = lambda k, vals: [dict(regs={k: v}) for v in vals]
    up = dict(d0=0x12345678, d1=0x9abcdef0, d2=0x11223344, d3=0x55667788, d4=0x99aabbcc, d5=0x13572468, d6=0x24681357, d7=0x99aabbcc)
    if entry in (0x1aa2c, 0x1c1e2, 0x1cac2, 0x1cad4, 0x1cb08, 0x1cd2a, 0x1cd58, 0x1cd7c, 0x1cda6, 0x1cdb0, 0x1ce08, 0x1ce1a, 0x1ce6e, 0x1ce80, 0x1d0ca,
                 0x1d0f6, 0x1d170, 0x1d222, 0x1d2d4, 0x1d32e, 0x1d364, 0x1d380, 0x1dbde, 0x1dff6, 0x1e006, 0x1e016, 0x1edd8, 0x1edf6, 0x1f230, 0x1f244,
                 0x1caf0, 0x1d1e2, 0x1d352, 0x1f286):
        h += [dict(regs=dict(up))]
    # ---- 1a9e8: CMPI.B #6,6e; A1 = LONG 5434(A5); the four map buffers; JMP (A1) with ASR.W #4
    if entry == 0x1a9e8:
        h += byte(0x6e, (6, 5, 7, 0x86))
    if entry == 0x1a9f2:
        h += [dict(a5off=[(0x5434, 4, v)]) for v in (0, 0x10000, 0x1c1e2, 0x80000000, 0x1ee00)]
    if entry in (0x1a9fe, 0x1aa0c, 0x1aa16, 0x1aa20):
        h += long_(0x3e, MAPS + (0x109157, 0x10d2d4, 0x1109156))
        h += [dict(regs=dict(a0=v)) for v in MAPS + (0x109158,)]
    if entry == 0x1aa2c:
        for v in (0, 0x7fff, 0x8000, 0xfff0, 0x10, 0xf):
            h.append(dict(a6off=[(0x2e, 2, v), (0x32, 2, v ^ 0x8000)], regs=dict(up, a1=0x1c1e2)))
        h += [dict(regs=dict(a1=0x1ce0e)), dict(regs=dict(a1=0x1ee00)), dict(regs=dict(a1=0x1c1e2), mirror=True)]
    # ---- 1c1e2: BYTE a0 index of the ROM table 1c1d8
    if entry == 0x1c1e2:
        h += byte(0xa0, (0, 1, 5, 9, 0xa, 0x7f, 0x80, 0xff)) + [dict(mirror=True)]
    # ---- 1cab6 / 1cac2 / 1cad4: record table WORDs and the LONG table
    if entry in (0x1cac2, 0x1cb08):
        for b9f in (0, 1, 2, 0x80, 0xff):
            for w in (0, 2, 0x8000):
                h.append(dict(a6off=[(0x9f, 1, b9f)], a0off=[(2 * b9f, 2, w), (0, 2, 4)]))
    if entry == 0x1cad2:
        h += [dict(a0off=[(0, 2, v)]) for v in (0, 2, 0xfffe, 0x100)]
    if entry == 0x1cad4:
        for d7, w in ((2, 0), (4, 1), (0xfffe, 3), (0, 0x4000), (2, 0x3fff), (0, 0x8000)):
            h.append(dict(regs=dict(up, d7=0x12340000 | d7), a0off=[(d7 if d7 < 0x8000 else d7 - 0x10000, 2, w)]))
    if entry in (0x1caea, 0x1caf0):
        h += regs('d7', (0, 0x1cafe, 0x12345678, 0x10e000))
    if entry in (0x1cab6, 0x1cabe):
        h += [dict(mirror=True)]
    # ---- 1cd12 .. 1cd7c: the box test of 5474(A5)
    if entry == 0x1cd12:
        h += [dict(a4off=[(0xa, 2, v)]) for v in (0, 1, 0x100, 0x8000)]
    if entry == 0x1cd1c:
        h += [dict(a5off=[(0x5474, 4, v)]) for v in (0, 0x10000)]
    if entry == 0x1cd2a:
        for d in ((0x10, 0x20, 0, 0, 0, 0, 0, 0, 0x11, 0x21), (0x10, 0x20, 0, 0, 0, 0, 0, 0, 0x10, 0x20), (0x8000, 0, 1, 0, 0, 0, 0, 0, 0xffff, 1),
                  (0x100, 0x100, 0x80, 0x40, 0x80, 0x40, 0x10, 0x10, 0x10, 0x10), (0, 0, 0, 0, 1, 0, 0, 0, 0x8000, 0x8000)):
            h.append(dict(regs=dict(up, a0=0x10e800), a6off=[(0x42, 2, d[0]), (0x46, 2, d[1])],
                          a5off=[(0x53a2, 2, d[2]), (0x53a6, 2, d[3]), (0x5470, 2, d[4]), (0x5472, 2, d[5])],
                          writes=[(0xe800, 2, d[6]), (0xe802, 2, d[7]), (0xe804, 2, d[8]), (0xe806, 2, d[9])]))
    if entry == 0x1cd50:
        h += [dict(regs=dict(d3=d3, a0=0x10e800), writes=[(0xe800, 2, w)]) for d3, w in ((0x10, 0x11), (0x10, 0x10), (0xffff, 0), (0x12340000, 1))]
    if entry == 0x1cd58:
        for d7, b in ((0, 0), (0, 1), (0xff, 0), (0xff, 1), (0x80, 1), (0x12345600, 0)):
            h.append(dict(regs=dict(up, d7=d7, d0=0x1234ffff), a6off=[(0x15, 1, b)]))
    if entry == 0x1cd6a:
        h += regs('d6', (0, 0xff, 0x100, 0x12345600))
    if entry in (0x1cd70, 0x1cd78, 0x1cd7c):
        h += regs('d0', (0, 0xffff, 0x12340000)) + byte(0xa8, (0, 0x20, 0xff))
    # ---- 1cd98 .. 1cec0: the input summary
    if entry == 0x1cd98:
        h += byte(0xa8, (0, 0x80, 0x7f, 0xff)) + [dict(mirror=True)]
    if entry == 0x1cda6:
        h += byte(0xad, (0, 0x80, 0xff)) + [dict(regs=dict(d0=0xffffffff))]
    if entry == 0x1cdba:
        h += [dict(a0off=[(0, 2, v)]) for v in (0, 1, 2, 3, 0x80, 0x81, 0xff7f, 0xffff)] + [dict(regs=dict(d0=0x12345678), a0off=[(0, 2, 0x81)])]
    if entry in (0x1cdc8, 0x1cdd2, 0x1cdea):
        h += byte(0x61, (0, 0xff, 0x20, 0x10))
    if entry == 0x1cdd8:
        h += regs('d0', (0, 2, 0xfd, 0x10002))
    if entry == 0x1cdfe:
        h += byte(0xa7, (0, 1, 0xfe, 0xff))
    if entry == 0x1ce08:
        h += [dict(a4off=[(4, 1, v)]) for v in (0, 1, 2, 7, 0x10, 0x1f, 0x7f, 0x80, 0xff)]
    if entry == 0x1ce1a:
        h += [dict(regs=dict(d2=0x12345678), a4off=[(2, 1, a), (3, 1, b)]) for a, b in ((1, 2), (2, 2), (3, 2), (0x80, 0x7f), (0x7f, 0x80), (0, 0), (0xff, 0))]
    if entry == 0x1ce2a:
        h += byte(0x6e, (7, 6, 8, 0x87))
    if entry == 0x1ce34:
        h += [dict(regs=dict(d0=0x1234ffdd), a6off=[(0x9e, 1, v), (0xa8, 1, b)]) for v, b in ((1, 0xff), (0, 4), (2, 0), (0x81, 0xfb))]
    if entry == 0x1ce50:
        h += [dict(regs=dict(d0=0x1234ffff), a6off=[(0xa8, 1, b)]) for b in (0, 4, 0xfb, 0xff)]
    if entry in (0x1ce48, 0x1ce5a, 0x1ce6a, 0x1ce26):
        h += regs('d0', (0xffffffff, 0, 0x12340020))
    if entry == 0x1ce62:
        h += byte(0xab, (0, 1, 0x80))
    if entry == 0x1ce6e:
        h += [dict(regs=dict(d0=0x123456ff), a6off=[(0x9e, 1, v)]) for v in (0, 1, 2, 3, 4, 0x80, 0xff)]
    if entry == 0x1ce80:
        h += [dict(regs=dict(d0=d0, d1=0x12345678), a6off=[(0xa6, 1, a), (0xa5, 1, b), (0xa7, 1, 0xff)]) for d0, a, b in
              ((0xff, 0x0f, 0x30), (4, 4, 0), (8, 0xff, 0), (0x1234000c, 0xf0, 1), (0x100, 0xff, 0))]
    if entry == 0x1cea8:
        h += regs('d0', (0, 8, 0xf7, 0x108))
    # ---- 1d0c2 .. 1d10a: the lights
    if entry == 0x1d0c2:
        h += [dict(regs=dict(a0=v)) for v in (0x10e800, 0x1d112)] + [dict(mirror=True)]
    if entry in (0x1d0ca, 0x1d0e0):
        for w76 in (0, 1, 0x7fff, 0x8000, 0xffff):
            h.append(dict(regs=dict(up), stack=[(0, 4, 0x10e800)], a6off=[(0x76, 2, w76)],
                          writes=[(0xe800, 2, 0x1234), (0xe802, 2, 0x5678), ((0xe800 + 2 * w76) & 0xffff, 2, 0x9abc)]))
    if entry == 0x1d0f6:
        h += byte(0x1a, (0, 0x80, 0xff))
    if entry == 0x1d10a:
        h += byte(0x19, (0, 0x80, 0xff))
    if entry == 0x1d160:
        h += regs('d0', (0, 8, 0xf7, 0x12345608))
    if entry == 0x1d170:
        h += [dict(regs=dict(a0=0x1d112), a6off=[(0x9f, 1, v)]) for v in (0, 1, 8, 0x11)] + [dict(regs=dict(a0=0x1d136), a6off=[(0x9f, 1, v)]) for v in (0, 3, 8)]
        h += [dict(regs=dict(a0=0x10e800, d0=0xffffffff), a6off=[(0x9f, 1, 0x40)], writes=[(0xe900, 4, 0x10e400)])]
    if entry == 0x1d1da:
        h += word(0x90, (0, 1, 0x100, 0x8000))
    # ---- 1d222 / 1d22a .. 1d390
    if entry in (0x1d222, 0x1d22a):
        h += [dict(mirror=True)] + word(0x78, (0, 1, 7, 8, 0xf, 0x8003)) + byte(0x61, (0xff, 0)) + byte(0x15, (0, 0xff))
    if entry == 0x1d2d4:
        h += regs('d0', (0, 0x20, 0x8, 0x40, 0x400, 0x468, 0x12345448, 0xffbf))
    if entry in (0x1d2e6, 0x1d2f2, 0x1d2fc):
        h += regs('d1', (0, 8, 0x40, 0x400, 0x448, 0xfbb7, 0x40000, 0x12345400))
    if entry == 0x1d31e:
        h += regs('d7', (0, 1, 0x10000, 0x8000, 0x12340000))
    if entry == 0x1d326:
        h += regs('d7', (4, 0x12340001))
    if entry == 0x1d32e:
        h += [dict(regs=dict(up), a4off=[(4, 1, v)]) for v in (0x10, 0x11, 0x12, 0x90, 0)]
    if entry == 0x1d344:
        h += regs('d0', (0x11, 0x10, 0x111, 0x12345611))
    if entry == 0x1d364:
        h += [dict(regs=dict(up, a0=0x10e800), a6off=[(0x78, 2, v), (0x42, 2, v ^ 0xffff)]) for v in (0, 1, 0x8000)]
    if entry == 0x1d380:
        h += [dict(regs=dict(up), stack=[(0, 2, v)]) for v in (1, 4, 0, 0x10001 & 0xffff, 0x8004, 5, 0xffff)]
    if entry == 0x1d390:
        h += regs('d7', (4, 0x10004, 1, 0x14))
    if entry == 0x1d45a:
        h += byte(0xa8, (0, 0x10, 0xef)) + [dict(mirror=True)]
    # ---- 1dbde: MOVE.W #c8,D1; AND.W D0,D1
    if entry == 0x1dbde:
        h += regs('d0', (0, 8, 0x40, 0x80, 0x37, 0xff37, 0xc80000, 0x12345678))
    if entry == 0x1de00:
        h += byte(0xa7, (0, 4, 0xff))
    if entry in (0x1de28, 0x1de30):
        h += regs('d0', (0, 8, 0x40, 0x48, 0xffb7, 0x12345600))
    # ---- 1dfe6 .. 1e016
    if entry == 0x1dfe6:
        h += byte(0xa7, (0, 0x20, 0xdf, 0xff))
    if entry == 0x1dff6:
        h += [dict(regs=dict(up), a6off=[(0xa2, 1, v)]) for v in (0, 0x1d, 0xfe, 0xff, 0x7f)]
    if entry == 0x1e006:
        h += [dict(regs=dict(up), a6off=[(0xa2, 1, v)]) for v in (0, 0x1d, 0x1e, 0x1f, 0xff)]
    if entry == 0x1e014:
        h += regs('d1', (0xffffffff, 0x12345678))
    if entry == 0x1e016:
        h += [dict(regs=dict(up, d0=a, d1=b)) for a, b in ((5, 5), (5, 6), (6, 5), (0, 0xffff), (0xffff, 0), (0x12340000, 0x10001), (0x8000, 0x7fff))]
    # ---- 1ed34 .. 1ed6a
    if entry == 0x1ed34:
        h += regs('d0', (0, 0x10, 0xef, 0x1234ff10))
    if entry == 0x1ed3e:
        h += byte(0xa7, (0, 1, 0xfe))
    if entry == 0x1ed4a:
        h += byte(0x6e, (5, 4, 6, 0x85))
    if entry == 0x1ed5a:
        h += byte(0xa7, (0, 2, 0xfd, 0xff))
    if entry == 0x1ed68:
        h += regs('a0', (0x1ed70, 0x10e800, 0x10fffc))
    if entry == 0x1ed6a:
        h += regs('a0', (0x1ed70, 0x1ed74)) + [dict(regs=dict(a0=0x10e800), writes=[(0xe800, 4, 0x10e400)])]
    # ---- 1ed78 .. 1edf6: the state machine head
    if entry == 0x1ed84:
        h += byte(0x92, (0x77, 0x78, 0x79, 0xff, 0)) + [dict(a6off=[(0x92, 2, 0x7700)])]
    if entry in (0x1ed96, 0x1f1fc, 0x1f7ac, 0x1faa0, 0x1fa94, 0x1fa58, 0x1fae8):
        h += [dict(mirror=True)]
    if entry in (0x1edb4, 0x1f23a, 0x1f7e2):
        h += byte(0x15, (0, 0x80, 0x7f, 0xff))
    if entry in (0x1edbe, 0x1edd0, 0x1ede6, 0x1edee):
        h += regs('d0', (0, 2, 0x20, 0x22, 0x80, 0x82, 0xa0, 0xff5d, 0x12345602))
    if entry == 0x1edc6:
        h += byte(0x9e, (0, 1, 0x80))
    if entry in (0x1edd8, 0x1edf6):
        h += regs('d0', (0, 4, 8, 0xc, 0xfff3, 0xc0000, 0x12345673))
    if entry == 0x1eee0:
        h += byte(0xa7, (0, 0x20, 0xff))
    # ---- 1f1d8 .. 1f2a0
    if entry == 0x1f1d8:
        h += [dict(writes=[(0xf001, 1, v)]) for v in (0, 4, 0xfb, 0xff)]
    if entry == 0x1f1e8:
        h += [dict(a4off=[(7, 1, v)]) for v in (0, 1, 0x80)]
    if entry == 0x1f228:
        h += byte(0x7e, (0, 1, 0x80))
    if entry == 0x1f230:
        h += regs('d0', (0, 4, 8, 0x10, 0x1c, 0xffe3, 0x1c0000, 0x12345663))
    if entry == 0x1f244:
        h += long_(0x36, (0, 1, 0x1f, 0x20, 0x21, 0xffffffff, 0xffffffe0, 0x80000000, 0x7fffffff, 0x12345678))
    if entry == 0x1f254:
        h += regs('d2', (0, 0x7fffffe1, 0xffffffe1, 0x1))
    if entry == 0x1f25a:
        for d2, v36, v3a in ((0x20, 0, 0), (0xffffffe0, 0x40, 0xffea0000), (0x80000000, 0xffffffff, 0xffea0001), (0x1f, 0x10, 0x7fffffff), (0x7fffffff, 0x80000000, 0)):
            h.append(dict(regs=dict(d2=d2, d3=0xffea0000), a6off=[(0x36, 4, v36), (0x3a, 4, v3a)]))
    if entry == 0x1f268:
        h += regs('d3', (0, 0x7fffffe1, 0xffffffe1))
    if entry == 0x1f26e:
        h += [dict(regs=dict(d3=d3), a6off=[(0x3a, 4, v)]) for d3, v in ((0x20, 0), (0xffffffe0, 5), (0x80000000, 0xffffffff), (0x1f, 0x7fffffff))]
    if entry in (0x1f278, 0x1fad2, 0x1fae0, 0x1fa48):
        h += long_(0x36, (0xffffffff,)) + long_(0x3a, (0xffffffff,))
    if entry in (0x1f286, 0x1f7f2, 0x1fab0):
        h += word(0x1e, (0, 0x8834, 0xffff))
    if entry in (0x1f29a, 0x1f806, 0x1fac8):
        h += [dict(mirror=True)]
    return h


# chain hints: let the real producers return both C values
def chain_hint(entry, t, rng):
    if entry == 0x1d588:
        return dict(a5off=[(0x5683, 1, (0, 4, 0xfb, 0xff)[t % 4])])                    # 4836e: BTST #2,5683(A5): set -> 48378 (Clear), clear -> 4837e (Set)
    if entry == 0x1d592:
        w = (0, 1, 0x8000, 0xffff)[t % 4]
        val = (0, 0x10e400)[(t // 4) % 2]
        return dict(a6off=[(0x78, 2, w)], a5off=[(0x5734 + 4 * (w & 1), 4, val)])    # 49c38: TST.L 5734(A5) + 4 (D0.W & 1)
    if entry in (0x1ed78, 0x1fa3c):
        return dict(a6off=[(0x9f, 1, (0, 1, 0x80)[t % 3])])                            # 1cb08: the ROM record tables 1b230 / 1b716 (0 -> 1cb18, Clear)
    if entry in CHAIN_49FC6 and t % 2:
        return dict(a6off=[(0x26, 4, 0)])                                              # 49fc6: LONG 26(A6) = 0 -> Set
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
        if missing:
            out_missing.append((cons, sorted(missing)))
        for i, (key, (st, tr)) in enumerate(sorted(kept.items(), key=lambda kv: str(kv[0]))):
            add(U.Fixture('chain-%05x-to-%05x-%d' % (entry, cons, i), st, [], tr['stop'], meta=dict(family='chain', entry=entry, consumer=cons, successor=tr['stop'],
                                                                                                c=tr['sr'] & 1)))


def add_run(add, name, st, tr, meta):
    add(U.Fixture(name, st, [], tr['stop'], meta=meta))


def node_fixtures(world, add, record):
    """Callbacks and installed values run as node callbacks ((A6) := entry) through every routed callee up to the dispatcher return or the first unrouted PC."""
    rng = world.rng
    for entry in NODE_ENTRIES:
        flds = fields_of(entry)
        kept = {}
        for t in range(60):
            base = rng.choice(world.bases)
            # BYTE 15 bit 7 (on ground [I]), BYTE 9f (state index), a8 / a7 / 6e / 9e / 7e, BYTE 1d(A6) < 4, WORD 104ca0 (28ae count limit; > 0
            # succeeds), BYTE 5683 (4836e)
            hint = dict(a6off=[(0x1d, 1, t % 4), (0x15, 1, (0, 0x80)[t % 2]), (0x9f, 1, (0, 1, 2)[(t // 2) % 3]), (0xa8, 1, (0, 0x80)[(t // 3) % 2]),
                               (0xa7, 1, (0, 1, 0x20)[(t // 2) % 3]), (0x6e, 1, (0, 7)[(t // 5) % 2]), (0x9e, 1, (0, 1)[(t // 4) % 2]),
                               (0x7e, 1, (0, 1)[(t // 3) % 2]), (0x26, 4, 0)],
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
    """The IO-pack natural nodes: the frame-start RAM / PVC / bank of a frame in which a node of the pool NATURAL_NODES holds one of NODE_ENTRIES as its
    callback LONG; declared registers A5 = 108000, A6 = the node, A7 = 10ef00 (sentinel return LONG), PC = the callback, the other registers as at the
    frame start.  Up to the sentinel or the first unrouted PC.  The reinstall worlds write one declared callback LONG first (REINSTALL)."""
    entries = set(NODE_ENTRIES)
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
    for cfg, case, frame, node, cb in REINSTALL:
        st0 = io_pack(cfg, case).get(frame)
        require(st0 is not None, ('missing IO pack frame', cfg, case, frame))
        regs = dict(st0['regs'])
        regs.update(a5=0x108000, a6=node, a7=0x10ef00)
        st = U.make_state(st0['ram'], regs, cb, st0['bank'], st0['pvc'])
        st = U.with_host_writes(st, [(0xef00, 4, SENTINEL), (node & 0xffff, 4, cb)])
        tr = trace(st, first_unrouted(extra=(SENTINEL,)), cap=400000)
        require(tr is not None, ('reinstall world failed', cfg, case, frame, hex(node), hex(cb)))
        record(tr['pcs'] + [tr['stop']])
        add_run(add, 'reinstall-%05x-%s%s-f%d-%x' % (cb, cfg, '' if case is None else '%03d' % case, frame, node), st, tr,
                dict(family='reinstall', entry=cb, config=cfg, case=case, frame=frame, node=node, stop=tr['stop'], unit_blocks=len(set(tr['pcs']) & STARTS_SET)))
        count += 1
    require(count >= 20, ('too few natural node fixtures', count))


def callee_fixtures(world, add, record):
    """The helpers as subroutines (return LONG = sentinel)."""
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
    err('odd-pc', U.with_host_writes(st, pc=0x1d223), 'unaligned animation machine PC', 0x1d223)
    for pc in CONSUMERS:
        err('unknown-carry-%05x' % pc, U.with_host_writes(st, pc=pc), ERROR_CARRY, pc)
    a6 = st['regs']['a6']
    a7 = st['regs']['a7']
    a5 = st['regs']['a5']
    odd_word = 'program bus requires even WORD/LONG address'
    odd_write = 'invalid animation machine write size/alignment'
    unrouted = 'unsupported animation machine PC'
    # the live JMP (A1) 1aa38 (contract decision 2): a target that is not a routed block start fails at the next dispatch; an odd target is unaligned
    # player C3 refresh: the unrouted targets were the C3 starts 201a2 / 1ee00 (rows 1aa2c-jmp-201a2, 1aa2c-jmp-1ee00, 1a9e8-jmp-1ee00); C3 routes them, so
    # the unrouted targets are now the ROM data LONGs 1ed70 / 1ed74 between the C2 ranges (never code)
    for a1, text in ((0x1ed70, unrouted), (0x1ce0e, ERROR_PC), (0x1c1e3, 'unaligned animation machine PC'), (0x1ed74, unrouted)):
        err('1aa2c-jmp-%05x' % a1, U.with_host_writes(st, regs=dict(a1=a1), pc=0x1aa2c), text, a1)
    #   1a9e8 -> 1a9f2 (LONG 5434(A5) = 1ed70) -> 1a9fe (LONG 3e(A6) = 109156) -> 1aa2c -> JMP 1ed70 (ROM data, unrouted)
    err('1a9e8-jmp-1ed70', U.with_host_writes(st, [((a6 + 0x6e) & 0xffff, 1, 6), ((a5 + 0x5434) & 0xffff, 4, 0x1ed70), ((a6 + 0x3e) & 0xffff, 4, 0x109156)],
                                               pc=0x1a9e8), unrouted, 0x1ed70)
    # odd node / stack / A0 / A4
    err('1aa2c-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1aa2c), odd_word, 0x1aa2c)
    err('1cd98-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1cd98), odd_word, 0x1cd98, stop=0x1cdb0)
    err('1d22a-odd-node', U.with_host_writes(st, regs=dict(a6=a6 + 1), pc=0x1d22a), odd_write, 0x1d22a, stop=0x1aa3a)
    err('1d0c2-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d0c2), odd_word, 0x1d0c2, stop=0x8ff4)
    err('1d1d0-odd-stack', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1d1d0), odd_word, 0x1d1d0, stop=0x48384)
    err('1cd12-odd-a4', U.with_host_writes(st, regs=dict(a4=a6 + 1), pc=0x1cd12), odd_word, 0x1cd12, stop=0x1cd1c)
    err('1cdba-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x1cdba), odd_word, 0x1cdba, stop=0x1cdc8)
    err('1ed6a-odd-a0', U.with_host_writes(st, regs=dict(a0=a6 + 1), pc=0x1ed6a), odd_word, 0x1ed6a, stop=0x1cb08)
    err('1cb08-odd-a0', U.with_host_writes(st, [((a6 + 0x9f) & 0xffff, 1, 0)], regs=dict(a0=a6 + 1), pc=0x1cb08), odd_word, 0x1cb08, stop=0x1cb18)
    # failures after executed blocks:
    #   1dfe6 (BYTE a7 bit 5 clear) -> 1dff0 (C Clear) RTS at an odd A7
    err('1dfe6-then-1dff0', U.with_host_writes(st, [((a6 + 0xa7) & 0xffff, 1, 0)], regs=dict(a7=a7 + 1), pc=0x1dfe6), odd_word, 0x1dff0)
    #   1ed34 (D0 bit 4 clear) -> 1ed3c RTS at an odd A7
    err('1ed34-then-1ed3c', U.with_host_writes(st, regs=dict(d0=0, a7=a7 + 1), pc=0x1ed34), odd_word, 0x1ed3c)
    #   1d2e6 (D1 = 0) -> 1d2f2 -> 1d2fc -> 1d306 BSR 1c1f4 at an odd A7
    err('1d2e6-then-1d306', U.with_host_writes(st, regs=dict(d1=0, a7=a7 + 1), pc=0x1d2e6), odd_word, 0x1d306, stop=0x1c1f4)
    #   1ed96 (installs 1edb0) -> 1edb0 BSR 1cd98 at an odd A7
    err('1ed96-then-1edb0', U.with_host_writes(st, regs=dict(a7=a7 + 1), pc=0x1ed96), odd_word, 0x1edb0, stop=0x1cd98)


def negative_fixtures(out, add):
    """C++ input differs from the native input in one bit: the comparison must report a difference."""
    picks = [fx for fx in out if fx.meta.get('family') == 'block' and fx.meta.get('entry') in (0x1cd2a, 0x1f25a, 0x1d22a, 0x1ce80)][:4]
    for fx in picks:
        st = fx.state
        add(U.Fixture('negative-ram-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.flip_ram(st, 0xf9f0, 0x10)))
        add(U.Fixture('negative-reg-' + fx.name, st, [], fx.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs=dict(d6=st['regs']['d6'] ^ 1, d0=st['regs']['d0'] ^ 0x100, d1=st['regs']['d1'] ^ 1))))
    if picks:
        add(U.Fixture('negative-stop-pc', picks[0].state, [], picks[0].stop, 'mismatch', cpp_stop=SENTINEL ^ 0x1000))
        add(U.Fixture('negative-queue-extra', picks[0].state, [], picks[0].stop, 'mismatch', cpp_queue=[(0x300000, 1, 0x5a)]))
