"""Native fixture spec of unit C2 (controller transitions / teardown / game-mode branch c76a c686 c74c c7c6 c80e, the waiting states, the card request c2fa, the input
mode 3162, game initialisation 47570, RNG 49a1a, 4e1cc, and the stage end menu child b300 / b344 with the item handlers a856 a876 a896 a8bc a75a: 164 block starts, executor
animation_controller_c2_block) for tools/verify_animation_machine_unit_fixtures.py.

Entry states are NATURAL: the D1 native reference (seed_frames) of a natural seed ends its H segment at the controller callback (A6 = 1008e4, A5 = 108000, return LONG 2ac2
at A7 = 1feffc).  The declared D9 states are host writes on that state: game mode (ii) LONG 1008e4 := c7fc with BYTE 10fdaf = 100012 = 2, demo mode (i) LONG 1008e4 := c66a with
BYTE 104cd4 = 1.  The post-transition world (child b300 / b344, the menu handlers) is the Execute-mode native run of verify_animation_machine_frame_controller.py with the
declared game writes (the controller is executed natively, the node pass follows), so those states are natural too.  Stop PCs are native-determined (`trace()` runs the
original code, never the C++).

Groups:
  nat-<mode>-s<case>-f<frame>   natural controller frames of game mode (ii) and demo mode (i); seeds 94 / 100 (idle stage controller node 100b30 from frame 1), 32 / 116 (241), 0 / 1 / 2
                                (245) reach the transition c76a (game) or c686 (demo), the others run the C1 gates to the tail.
  edge-<pc>-s<case>-<k>         every one of the 164 block starts entered directly in seeded worlds; one fixture per distinct native successor.
  chain-<kind>-<pc>-s<case>-<k> multi-block runs through the real routed callees (3dce 2a0a 2a84 ca76 caf0 28ae 289e 2a28 8bbc 9060 e7bf4 ca48 e8a1c / 47594 4a974 ...) to the first
                                boundary: the transitions, the restart and continue paths, the waiting states, the card request (BIOS c00468 stop), game initialisation, the RNG table.
  setc / clearc-<pc>            the two C consumers c87e c916 with a real Set / Clear C: the producer 289e entered with the consumer as the return LONG.
  zflag-<pc>-<n>                4a9b0 / 4a9c6 (TST.B (A0); RTS) entered with the Z consumer c964 / c97a as the return LONG: A0 in the four proven bytes, byte zero / non-zero.
  card-resume-*                 c2fe to the BIOS fetch c00468 (stop), then the frame driver's declared resume (BYTE 10fdc6 := answer, PC := c316, A7 += 4) to the next boundary.
  exec-ctl-*                    controller segments of the Execute-mode native run (transition frame c7fc -> c79a, waiting frames c79a -> c79a) with the native-declared queue.
  exec-b300 / exec-b344         the child nodes (callbacks b300 / b344) of the Execute-mode N pass; exec-hand-<pc> the menu item handlers from the natural a856 call
                                (and the same state with the PC overridden to a876 a896 a8bc); exec-b350 b344's exit through b34a with a non-zero D0 (parent byte 62 := 3, self delete 2a00).
  error-*                       checked errors with preservation: Unknown C into c87e / c916, every internal even PC and odd PCs of the 16 ranges, the flag-source guard (A0 outside the
                                four bytes), the ROM writes c690 / 31ce, odd stores, unrouted neighbours.
  negative-*                    the C++ input differs by one bit; the comparison must report it.
Boundary stops: 2ac2 (controller RTS) c00444 (BIOS system return) c00468 (BIOS card) c00450 (BIOS credit) c610 and every PC without an executor.
"""
import collections
import random
import sys

import verify_animation_machine_unit_fixtures as U

STARTS = tuple(int(x, 16) for x in (
    '100e 101c 3162 3180 3188 31c4 31ce 31d4 bbd4 bbe4 bbf4 c2fa c2fe c316 c326 c332 c346 c35c c4cc c4d2 c4d8 c4dc c4e6 c4ee c4f6 c686 c690 c69a c69e c6a2 c6a6 c6b6 c6c0 c6c8 '
    'c74c c754 c75e c766 c76a c772 c776 c77a c77e c794 c79a c7a4 c7ae c7ba c7c0 c7c6 c7ce c7d2 c7d6 c7dc c7e6 c7f6 c80e c81a c81e c826 c82e c836 c83e c846 c84a c84e c854 c85e '
    'c86e c874 c87e c882 c886 c88a c890 c896 c89c c8a4 c8aa c8b0 c8b4 c8b8 c8c4 c8ca c8ce c8e2 c8e8 c8f0 c906 c90c c916 c91a c91e c922 c926 c936 c940 c948 c952 c95c c964 c968 '
    'c972 c97a c97e c982 4755e 47566 4756e 47570 47582 47584 4758a 4823a 48242 48244 49a1a 49a26 49a34 49a3e 49a50 4e1cc 4e1f8 4e20e e62ec e62f2 e62fc e6302 b300 b306 b30c b31a '
    'b326 b330 b33e b344 b34a b350 b360 a75a a760 a76a a856 a85a a860 a868 a86c a874 a876 a87a a880 a888 a88c a894 a896 a89a a8a0 a8a8 a8ae a8ba a8bc a8c0 a8c8 a8ce').split())
STARTSET = frozenset(STARTS)
assert len(STARTS) == 164 and len(STARTSET) == 164
RANGES = ((0x100e, 0x1022), (0x3162, 0x31d6), (0xbbd4, 0xbbfa), (0xc2fa, 0xc364), (0xc4cc, 0xc4f8), (0xc686, 0xc6ce), (0xc74c, 0xc7fc), (0xc80e, 0xc988), (0x4755e, 0x47594),
          (0x4823a, 0x48250), (0x49a1a, 0x49a58), (0x4e1cc, 0x4e216), (0xe62ec, 0xe630a), (0xb300, 0xb362), (0xa75a, 0xa770), (0xa856, 0xa8d0))
CONSUMERS = (0xc87e, 0xc916)
Z_CONSUMERS = (0xc964, 0xc97a)
Z_BYTES = (0x10fdb0, 0x10fdb1, 0x100004, 0x100005)
BOUNDARY = frozenset([0x2ac2, 0xc00444, 0xc00468, 0xc00450, 0xc610])
CHILDREN = frozenset([0xe66aa, 0xde660])
NODE = 0x1008e4
CASES = (0, 94)
MAX_VARIANTS = 56
GAME_WRITES = [(0x10fdaf, 1, 2), (0x100012, 1, 2)]
DEMO_WRITES = [(0x104cd4, 1, 1)]
# (case, frames): the transition frame of each natural seed (Skip trajectory: LONG 100b30 = 270e first at the controller of that frame).
NATURAL = ((94, (1, 2, 3, 40)), (100, (1, 2, 5)), (32, (240, 241, 242, 250)), (116, (241, 244)), (0, (1, 2, 100, 244, 245, 246, 250)), (1, (245, 299)), (2, (245,)), (135, (244, 245)))
# Execute-mode native runs: (case, transition frame, frames kept after it).
EXEC = ((94, 1, 12), (0, 245, 14))

REG_VALUES = (0, 1, 2, 3, 4, 5, 7, 8, 0x12, 0x13, 0x14, 0x7f, 0x80, 0xff, 0x100, 0x1234, 0x7fff, 0x8000, 0xffff, 0x10000, 0x10001, 0x10003, 0x80000000, 0xffffffff, 0xfffffff8)
BYTE_POOL = {
    0x10fd82: (0, 1), 0x10fd8e: (0, 1, 2), 0x10fdb6: (0, 1, 2), 0x10fdb7: (0, 1, 2), 0x104cb5: (0, 1, 2, 4, 5, 0xff, 0x55), 0x10fdc6: (0, 0, 1, 0x80), 0x100012: (0, 1, 2, 3),
    0x104cd4: (0, 1), NODE + 0x62: (0, 0, 1, 2, 3, 0xff), 0x10d683: (0, 1, 0xff), 0x10d680: (0, 5, 0x13), 0x100017: (0, 1, 2)}
WORD_POOL = {0x10fdd0: (0, 1, 2, 3, 0x100, 0x101, 0xffff), 0x10f02c: (0, 1, 0x1234, 0x7fff, 0xffff), 0x10f02a: (0, 0x1234), NODE + 0x7c: (0, 0x30ff, 0x9ff, 0xffff),
             0x10000e: (0, 0x1234)}
LONG_POOL = {0x100b30: (0x270e, 0x270e, 0x47af0, 0x47bfc, 0), NODE + 8: (0x100820, 0x100b30, 0x100c00), NODE + 0xc: (0x1008e4, 0x100c00, 0x100820),
             0x104cc8: (0x100c00, 0x100d00), 0x104cc4: (0x100c00, 0xf0dfe), 0x10d722: (0, 0x10d6b4)}
A0_POOL = (0x100820, 0x100c00, 0x100e98, 0x1008e4, 0x10de14, 0x10de1c, 0x10fdb0, 0x10fdb1, 0x100004, 0x100005, 0x10d6b4, 0x10c800, 0x100b30)
A1_POOL = (0x477e4, 0x4e68e, 0xbb8e, 0x3650)
D7_POOL = (0, 1, 2, 3, 0x18, 0x36, 0x5ff, 0xffff, 0x10000, 0x10001, 0xffff0000)


def hx(pc):
    return '%x' % pc


def in_ranges(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


# ----------------------------------------------------------------------------------
# Routing (parsed once from the checked-out dispatch chain)
# ----------------------------------------------------------------------------------
ROUTING = []
TRAPS = frozenset([0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788])
ROUTED_MEMO = {}


def routed(pc):
    """True when the checked-out dispatch chain of engine/src/animation_machine.cpp has an executor for pc."""
    import re
    if not ROUTING:
        src = (U.ROOT / 'engine/src/animation_machine.cpp').read_text()
        body = src[src.index('if ((next.pc>=0x3ac8'):src.index('else return am_error(c,"unsupported animation machine PC")')]
        for m in re.finditer(r'(?:else )?if \((.*?)\)ok=(\w+)\(c\);', body, re.S):
            e = m.group(1).replace('next.pc', 'p').replace('&&', ' and ').replace('||', ' or ')
            e = re.sub(r'!stage_event_ops_trap\(p\)', 'not trap(p)', e).replace('!=', '<>').replace('!', ' not ').replace('<>', '!=')
            ROUTING.append(compile('(' + e.replace('\n', ' ') + ')', 'routing', 'eval'))
        ROUTING.append(None)
    if pc not in ROUTED_MEMO:
        env = dict(p=pc, trap=lambda x: x in TRAPS)
        ROUTED_MEMO[pc] = any(eval(r, env) for r in ROUTING if r is not None)
    return ROUTED_MEMO[pc]


def edge_rule(pc):
    return pc in STARTSET or not in_ranges(pc)


def chain_rule(pc):
    """A chain boundary: the controller RTS 2ac2, the BIOS (c00000..c0ffff), the C3b restart c610 and the two child callbacks the controller only installs (e66aa de660).
    Other PCs without an executor are interior PCs of another unit's block (e.g. the 8c2a branch target of the exit block 8c16), never a stop."""
    return pc in BOUNDARY or 0xc00000 <= pc < 0xc10000 or pc in CHILDREN


def seq_chain_rule(pc):
    """The plain continuation of an instruction is never a new block start for an unrouted PC (the instruction is inside a routed block)."""
    return pc in BOUNDARY


# ----------------------------------------------------------------------------------
# Natural controller entry states
# ----------------------------------------------------------------------------------
FRAMES = {}


def frames_of(case, count=300):
    if case not in FRAMES:
        FRAMES[case] = U.seed_frames(case, count)
    return FRAMES[case]


def entry_state(case, frame):
    """Natural controller entry (PC c52a, A6 1008e4, A5 108000, A7 1feffc with the return LONG 2ac2) of seed `case`, frame `frame`."""
    fr = [f for f in frames_of(case) if f['frame'] == frame and f.get('h')]
    U.require(fr, ('no controller entry', case, frame))
    return U.seed_state(fr[0]['h']['end'])


def declare(state, mode, extra=(), regs=None):
    """The D9 declared controller states: 'game' (c7fc, 10fdaf = 100012 = 2) and 'demo' (c66a, 104cd4 = 1)."""
    if mode == 'game':
        return U.with_host_writes(state, [(NODE, 4, 0xc7fc)] + GAME_WRITES + list(extra), regs=regs, pc=0xc7fc)
    return U.with_host_writes(state, [(NODE, 4, 0xc66a)] + DEMO_WRITES + list(extra), regs=regs, pc=0xc66a)


# ----------------------------------------------------------------------------------
# Native tracer: the original code from a declared entry to the first stop (never the C++)
# ----------------------------------------------------------------------------------
LENGTHS = {}


def insn_length(pc):
    """Length of the original instruction at pc (capstone on the canonical ROM; the Unicorn code hook does not report m68k lengths)."""
    if pc not in LENGTHS:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
        ins = next(md.disasm(U.native().program[pc:pc + 10], pc), None)
        LENGTHS[pc] = ins.size if ins is not None else 2
    return LENGTHS[pc]


def trace(state, entry, rule, after=None, limit=4000, status=0, seq_rule=None):
    """-> dict(pc, steps, visited) or None.  rule(pc) True stops BEFORE executing pc (the entry itself never stops; `after`: armed only once pc == after).  An unmapped fetch
    (BIOS) is a stop when the rule accepts it.  A PC that is the plain continuation of the previous instruction is checked with `seq_rule` (default: the rule): a
    block of the C++ never stops inside itself.  Undeclared device reads (backup RAM, inputs), odd accesses and invalid accesses make the world unusable (None)."""
    import unicorn
    nat = U.native()
    snap = dict(ram=state['ram'], regs=state['regs'], pc=entry, bank=state['bank'])
    m = nat.PB.PvcMachine(nat.program, nat.fixed, snap)
    m.install_basic_hooks()
    c = m.cpu
    for base in (0x340000, 0x380000):
        c.mem_map(base, 4096, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    c.mem_write(U.PVC_LO, state['pvc'])
    c.mem_write(U.STATUS_ADDR, bytes([status & 0xff]))
    seen = dict(pc=None, steps=0, armed=after is None, visited=[], end=None)

    def code(uc, pc, size, user):
        if seen['steps'] > 0:
            hit = (seq_rule or rule)(pc) if pc == seen['end'] else rule(pc)
            if not seen['armed']:
                seen['armed'] = pc == after
            elif hit:
                seen['pc'] = pc
                uc.emu_stop()
                return
        seen['end'] = pc + insn_length(pc) if pc < 0x100000 else None
        if pc in STARTSET:
            seen['visited'].append(pc)
        seen['steps'] += 1
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    m.fetch_unmapped = None
    try:
        c.emu_start(entry, 0xffffff, count=limit)
    except unicorn.UcError:
        pass
    if seen['pc'] is None and m.fetch_unmapped is not None and seen['armed'] and rule(m.fetch_unmapped):
        seen['pc'] = m.fetch_unmapped
    if seen['pc'] is None or m.odd is not None or m.invalid is not None or m.intr is not None:
        return None
    if any(a != U.STATUS_ADDR for a, _ in m.dev_reads):
        return None
    return dict(pc=seen['pc'], steps=seen['steps'], visited=seen['visited'])


# ----------------------------------------------------------------------------------
# Worlds (declared host writes and registers on a natural controller state)
# ----------------------------------------------------------------------------------
def world(rng, state):
    regs = dict(state['regs'])
    for k in range(8):
        regs['d%d' % k] = rng.choice(REG_VALUES) if rng.random() < 0.7 else rng.getrandbits(32)
    regs['d7'] = rng.choice(D7_POOL)
    regs['a0'] = rng.choice(A0_POOL)
    regs['a1'] = rng.choice(A1_POOL)
    writes = []
    for addr, vals in BYTE_POOL.items():
        if rng.random() < 0.6:
            writes.append((addr, 1, rng.choice(vals) if rng.random() < 0.9 else rng.getrandbits(8)))
    for addr, vals in WORD_POOL.items():
        if rng.random() < 0.6:
            writes.append((addr, 2, rng.choice(vals) if rng.random() < 0.9 else rng.getrandbits(16)))
    for addr, vals in LONG_POOL.items():
        if rng.random() < 0.7:
            writes.append((addr, 4, rng.choice(vals)))
    return writes, regs


def block_stack(pc, rng, state):
    """Declared stack content for the blocks that pop their own pushes (the natural return LONG 2ac2 stays for the rest)."""
    a7 = state['regs']['a7']
    if pc == 0xc316:                                              # MOVEA.L (A7)+,A6: a node address
        return [(a7, 4, 0x1008e4)], {}
    if pc == 0xc4ee:                                              # MOVEA.L (A7)+,A0 then 8(A0)
        return [(a7, 4, rng.choice((0x1008e4, 0x100820, 0x100b30)))], {}
    if pc == 0xa76a:                                              # ADD.W (A7)+,D0; MOVE.W (A7)+,D1; RTS
        return [(a7 - 4, 2, rng.choice((0, 1, 0x1234, 0xffff))), (a7 - 2, 2, rng.choice((0, 1, 0x4321, 0x8000)))], {'a7': a7 - 4}
    return [], {}


def edge_fixtures(rng, pc, case):
    base = entry_state(case, 2)
    out, seen = [], set()
    consumer = pc in CONSUMERS
    for v in range(MAX_VARIANTS):
        writes, regs = world(rng, base)
        extra, regpatch = block_stack(pc, rng, base)
        regs.update(regpatch)
        if pc in Z_CONSUMERS:                                    # native SR.Z = 0: only the non-zero byte is comparable; the zero side is zflag-*
            regs['a0'] = rng.choice(Z_BYTES)
            writes.append((regs['a0'], 1, rng.choice((1, 2, 0x99, 0xff))))
        st = dict(U.with_host_writes(base, writes + extra, regs=regs, pc=pc), carry=1 if consumer else 0)
        r = trace(st, pc, edge_rule)
        if r is None or r['pc'] in seen:
            continue
        seen.add(r['pc'])
        out.append(U.Fixture('edge-%x-s%d-%d' % (pc, case, len(out)), st, [], r['pc'], meta=dict(block=hx(pc), successor=hx(r['pc']), case=case, variant=v)))
    return out


# ----------------------------------------------------------------------------------
# Carry consumers with a real C, Z consumers with a real Z
# ----------------------------------------------------------------------------------
def with_return(state, ret):
    a7 = state['regs']['a7']
    return U.with_host_writes(state, [(a7, 4, ret)])


def carry_fixtures(rng, case):
    out = []
    base = entry_state(case, 2)
    for consumer in CONSUMERS:
        for kind in ('set', 'clear'):
            for k in range(2):                                   # 289e: callback LONG at A0 = 270e -> Clear, else Set
                value = rng.choice((0x47af0, 0x47bfc, 0)) if kind == 'set' else 0x270e
                regs = dict(base['regs'])
                regs['a0'] = 0x100b30
                st = dict(with_return(U.with_host_writes(base, [(0x100b30, 4, value)], regs=regs, pc=0x289e), consumer), carry=0)
                r = trace(st, 0x289e, edge_rule, after=consumer)
                if r is None:
                    continue
                out.append(U.Fixture('%sc-%x-s%d-%d' % (kind, consumer, case, k), st, [], r['pc'],
                                     meta=dict(consumer=hx(consumer), kind=kind, successor=hx(r['pc']), case=case)))
    return out


def zflag_fixtures(rng, case):
    out = []
    base = entry_state(case, 2)
    for consumer in Z_CONSUMERS:
        for entry in (0x4a9b0, 0x4a9c6):
            for a0 in Z_BYTES:
                for value in (0, 1, 0x80, 0xff):
                    regs = dict(base['regs'])
                    regs['a0'] = a0
                    st = dict(with_return(U.with_host_writes(base, [(a0, 1, value)], regs=regs, pc=entry), consumer), carry=0)
                    r = trace(st, entry, edge_rule, after=consumer)
                    if r is None:
                        continue
                    out.append(U.Fixture('zflag-%x-%x-%x-%02x-s%d' % (consumer, entry, a0, value, case), st, [], r['pc'],
                                         meta=dict(consumer=hx(consumer), entry=hx(entry), a0=hex(a0), value=value, successor=hx(r['pc']))))
    return out


# ----------------------------------------------------------------------------------
# Natural frames and chains through the real routed callees
# ----------------------------------------------------------------------------------
def natural_fixtures():
    out = []
    for case, frames in NATURAL:
        for frame in frames:
            base = entry_state(case, frame)
            for mode in ('game', 'demo'):
                st = dict(declare(base, mode), carry=0)
                r = trace(st, st['pc'], chain_rule, limit=200000, seq_rule=seq_chain_rule)
                if r is None:
                    continue
                out.append(U.Fixture('nat-%s-s%d-f%d' % (mode, case, frame), st, [], r['pc'],
                                     meta=dict(mode=mode, case=case, frame=frame, stop=hx(r['pc']), blocks=len(r['visited']))))
    return out


# (kind, entry, writes added to every world of the kind)
CHAIN_ENTRIES = (
    ('transition', 0xc76a, [(0x100b30, 4, 0x270e)]), ('transition', 0xc772, []), ('transition', 0xc77e, []),
    ('demo-end', 0xc686, []), ('demo-end', 0xc69a, []), ('demo-end', 0xc6b6, []), ('demo-end', 0xc6c0, []),
    ('start', 0xc74c, []), ('start', 0xc75e, []),
    ('wait-c79a', 0xc79a, []), ('wait-c79a', 0xc7ae, []), ('restart', 0xc7c6, []), ('restart', 0xc7ce, []), ('restart', 0xc7d6, []), ('restart', 0xc7dc, []),
    ('continue', 0xc80e, []), ('continue', 0xc81a, []), ('continue', 0xc826, []), ('wait-c82e', 0xc82e, []), ('wait-c82e', 0xc83e, []), ('wait-c82e', 0xc874, []),
    ('card', 0xc882, []), ('card', 0xc88a, []), ('card', 0xc890, []), ('wait-c89c', 0xc89c, []), ('wait-c89c', 0xc8aa, []), ('end', 0xc8b8, []), ('end', 0xc8ce, []),
    ('wait-c8e8', 0xc8e8, []), ('wait-c8e8', 0xc8f0, []), ('wait-c8e8', 0xc90c, []), ('end2', 0xc91a, []), ('wait-c940', 0xc940, []), ('wait-c940', 0xc948, []),
    ('wait-c940', 0xc952, []), ('wait-c940', 0xc95c, []), ('wait-c940', 0xc972, []),
    ('input', 0x3162, []), ('input', 0x3188, []), ('input', 0x31c4, [(0x104cc8, 4, 0x100c00)]), ('rng', 0x49a1a, []), ('rng', 0x49a34, []), ('init', 0x47570, []),
    ('init', 0x4755e, []), ('init', 0x4823a, []), ('init', 0x4e1cc, []), ('init', 0x100e, []), ('teardown', 0xc4cc, []), ('teardown', 0xc4d8, []),
    ('menu-table', 0xbbd4, []), ('card-request', 0xc2fa, []), ('card-request', 0xc332, []), ('card-request', 0xc346, []),
    ('child', 0xb300, []), ('child', 0xb344, []), ('handler', 0xa856, []), ('handler', 0xa876, []), ('handler', 0xa896, []), ('handler', 0xa8bc, []), ('handler', 0xa75a, []),
)


def chain_fixtures(rng, case):
    out = []
    base = entry_state(case, 3)
    for kind, entry, extra in CHAIN_ENTRIES:
        seen = set()
        for v in range(40):
            writes, regs = world(rng, base)
            writes += extra
            if entry >= 0xc79a and entry < 0xc988 and rng.random() < 0.3:
                writes.append((0x10fdb6, 1, 1))
            regs['a1'] = rng.choice(A1_POOL)
            st = dict(U.with_host_writes(base, writes, regs=regs, pc=entry), carry=0)
            r = trace(st, entry, chain_rule, limit=200000, seq_rule=seq_chain_rule)
            if r is None:
                continue
            key = (r['pc'], tuple(r['visited']))
            if key in seen:
                continue
            seen.add(key)
            out.append(U.Fixture('chain-%s-%x-s%d-%d' % (kind, entry, case, len(seen)), st, [], r['pc'],
                                 meta=dict(kind=kind, entry=hx(entry), stop=hx(r['pc']), blocks=len(r['visited']), case=case, variant=v)))
            if len(seen) >= 6:
                break
    return out


def card_resume_fixtures(rng, case):
    """c2fe to the BIOS card fetch c00468 (stop), then the frame driver's resume: BYTE 10fdc6 := answer, PC := the return LONG c316, A7 += 4, to the next boundary."""
    out = []
    base = entry_state(case, 2)
    for k, answer in enumerate((0x80, 0x00, 0x01)):
        for word in (0, 1, 2, 3):                                # WORD 10fdd0 bit 0 selects the card child c332
            st = dict(U.with_host_writes(base, [(0x10fdd0, 2, word)], pc=0xc2fe), carry=0)
            st1, _, _ = U.advance_native(st, [], 0xc00468)
            a7 = st1['regs']['a7']
            ret = int.from_bytes(st1['ram'][a7 & 0xffff:(a7 & 0xffff) + 4], 'big')
            U.require(ret == 0xc316, ('card return', hex(ret)))
            out.append(U.Fixture('card-resume-bios-%d-%d-s%d' % (k, word, case), st, [], 0xc00468))
            res = dict(U.with_host_writes(st1, [(0x10fdc6, 1, answer)], regs={'a7': a7 + 4}, pc=0xc316), carry=0)
            r = trace(res, 0xc316, chain_rule, seq_rule=seq_chain_rule)
            if r is None:
                continue
            out.append(U.Fixture('card-resume-step-%d-%d-s%d' % (k, word, case), res, [], r['pc'], meta=dict(answer=answer, word=word, stop=hx(r['pc']))))
    return out


# ----------------------------------------------------------------------------------
# Execute-mode natural states: the transition frame, the controller wait c79a, the child b300 / b344 and the menu handlers
# ----------------------------------------------------------------------------------
def exec_frames(case, transition, after):
    """Native Execute-mode frames (controller executed, declared game writes at frame 1) around the transition frame; -> dict frame -> record."""
    import verify_animation_machine_frame_controller as FC
    D = FC.D
    if D.FH is None:
        D.setup_native()
    if 'cls' not in FC.CTX:
        FC.CTX.update(cls=FC.make_controller_class(), answer=D.R.DEFAULT_ANSWER)
    keep = set(range(max(1, transition - 1), transition + after + 1))
    got = {}

    def on_frame(fr):
        if fr['frame'] in keep:
            got[fr['frame']] = fr
    sd, run = FC.make_run(case, transition + after + 1, on_frame, FC.DECLARE_PRESETS['game'])
    run.run()
    return got


def pass_queue(n):
    return [(a, s, v) for _, a, s, v in n['dev'] if a in (0x300000, 0x340000, 0x380000, 0x3c0006)]


def exec_fixtures():
    import verify_animation_machine_frame_driver as D
    out = []
    for case, transition, after in EXEC:
        frames = exec_frames(case, transition, after)
        for f in sorted(frames):
            fr = frames[f]
            c = fr.get('c')
            if c is None or c['reason']['reason'] != 'returned':
                continue
            if f <= transition + 2:                              # controller segments: the transition frame and the first waiting frames
                q, status, other = D.n_queue(c['dev'])
                if not other:
                    end = c['end']
                    out.append(U.Fixture('exec-ctl-s%d-f%d' % (case, f), U.seed_state(c['start']), q, end['pc'], external_status=status,
                                         reference=dict(ram=end['ram'], regs=end['regs'], pc=end['pc']),
                                         meta=dict(case=case, frame=f, entry=hx(c['entry']), exit=hx(c['exit_cb']), path=[hx(p) for p in c['path'][:12]])))
            n = fr.get('n')
            if not n or n['reason']['reason'] != 'frame-head':
                continue
            start = U.seed_state(n['start'])
            queue = pass_queue(n)
            status = fr['start']['status']
            for cb in (0xb300, 0xb344):
                if cb not in n['cbs']:
                    continue
                if cb == 0xb344 and f > transition + 6:
                    continue
                try:
                    st, rest, _ = U.advance_native(start, queue, cb, external_status=status)
                except Exception:
                    continue
                a7 = st['regs']['a7']
                ret = int.from_bytes(st['ram'][a7 & 0xffff:(a7 & 0xffff) + 4], 'big')
                out.append(U.Fixture('exec-%x-s%d-f%d' % (cb, case, f), st, rest, ret, external_status=status, meta=dict(case=case, frame=f, callback=hx(cb), return_pc=hx(ret))))
                if cb != 0xb344:
                    continue
                # b344's exit: a370 returned non-zero (b34a with D0 = 1): the parent controller node byte 62 := 3 and the self delete 2a00
                sel = U.with_host_writes(st, regs={'d0': 1}, pc=0xb34a)
                r = trace(sel, 0xb34a, chain_rule, limit=200000, seq_rule=seq_chain_rule)
                if r is not None:
                    out.append(U.Fixture('exec-b350-s%d-f%d' % (case, f), dict(sel, carry=0), rest, r['pc'], external_status=status, meta=dict(case=case, frame=f, stop=hx(r['pc']))))
                for handler in (0xa856,):
                    try:
                        hst, hrest, _ = U.advance_native(st, rest, handler, external_status=status)
                    except Exception:
                        continue
                    ha7 = hst['regs']['a7']
                    hret = int.from_bytes(hst['ram'][ha7 & 0xffff:(ha7 & 0xffff) + 4], 'big')
                    for pc in (0xa856, 0xa876, 0xa896, 0xa8bc, 0xa75a):
                        item = dict(U.with_host_writes(hst, pc=pc), carry=0)
                        rule = (lambda target: (lambda p: p == target or chain_rule(p)))(hret)
                        r = trace(item, pc, rule, limit=200000, seq_rule=lambda p: p in BOUNDARY or p == hret)
                        if r is None:
                            nat = U.native().run(item, hrest, hret, external_status=status)
                            if not nat['ok']:
                                continue
                            stop = hret
                        else:
                            stop = r['pc']
                        out.append(U.Fixture('exec-hand-%x-s%d-f%d' % (pc, case, f), item, hrest, stop, external_status=status,
                                             meta=dict(case=case, frame=f, handler=hx(pc), stop=hx(stop))))
    return out


# ----------------------------------------------------------------------------------
# Checked errors
# ----------------------------------------------------------------------------------
def error_fixtures(case):
    out = []
    probe = entry_state(case, 2)
    for consumer in CONSUMERS:
        out.append(U.Fixture('error-unknown-carry-%x' % consumer, dict(U.with_host_writes(probe, [], pc=consumer), carry=0), [], 0xffffe,
                             ('error', 'controller c2 caller requires known carry')))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in STARTSET:
                out.append(U.Fixture('error-interior-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation controller c2 PC')))
        for pc in (lo + 1, hi - 1):
            out.append(U.Fixture('error-odd-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unaligned animation machine PC')))
    # PCs without an executor: even work-RAM PCs 10fe10..10fe1e (review 0264 M-3; were the ROM range ends 1022 bbfa c6ce 48250 e630a b362 a770 a8d0, code of later units)
    # and the two BIOS entries (stay unrouted)
    for pc in (0x10fe10, 0x10fe12, 0x10fe14, 0x10fe16, 0x10fe18, 0x10fe1a, 0x10fe1c, 0x10fe1e, 0xc00444, 0xc00468):
        U.require(not routed(pc), ("probe is routed", hex(pc)))
        out.append(U.Fixture('error-outside-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation machine PC')))
    # Z flag source guard: A0 outside 10fdb0 / 10fdb1 / 100004 / 100005
    for consumer in Z_CONSUMERS:
        for a0 in (0, 0x3000, 0x10fdaf, 0x10fdb2, 0x100003, 0x100006, 0x10fe00, 0xd00034, 0x1010fdb0, 0xffffffff):
            regs = dict(probe['regs'])
            regs['a0'] = a0
            out.append(U.Fixture('error-flag-source-%x-%x' % (consumer, a0), U.with_host_writes(probe, [], regs=regs, pc=consumer), [], 0xffffe,
                                 ('error', 'unsupported animation controller flag source')))
    # ROM writes: c690 CLR.W 180.l and the recorder fill 31ce into ROM space
    out.append(U.Fixture('error-rom-write-c690', U.with_host_writes(probe, [], pc=0xc690), [], 0xffffe, ('error', 'unsupported animation machine write device')))
    for a0 in (0x100, 0x300000):
        regs = dict(probe['regs'])
        regs['a0'] = a0
        regs['d7'] = 3
        out.append(U.Fixture('error-rom-write-31ce-%x' % a0, U.with_host_writes(probe, [], regs=regs, pc=0x31ce), [], 0xffffe, ('error', 'unsupported animation machine write device')))
    # odd stores through A0
    for pc, field in ((0xe6302, 0), (0xc346, 0), (0x4e20e, 0), (0x4e1f8, 0)):
        regs = dict(probe['regs'])
        regs['a0'] = 0x100c01
        out.append(U.Fixture('error-odd-store-%x' % pc, U.with_host_writes(probe, [], regs=regs, pc=pc), [], 0xffffe, ('error', 'invalid animation machine write size/alignment')))
    # odd node A6 for the LONG install
    regs = dict(probe['regs'])
    regs['a6'] = NODE + 1
    out.append(U.Fixture('error-odd-node-install', U.with_host_writes(probe, [], regs=regs, pc=0xc794), [], 0xffffe, ('error', 'invalid animation machine write size/alignment')))
    return out


def negative_fixtures(fixtures):
    out = []
    pool = [f for f in fixtures if f.name.startswith('edge-') and f.expect == 'match']
    for f in pool[:3]:
        st = f.state
        out.append(U.Fixture('negative-ram-' + f.name, st, [], f.stop, 'mismatch', cpp_state=U.flip_ram(st, 0x10fff0)))
        out.append(U.Fixture('negative-reg-' + f.name, st, [], f.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs={'d5': st['regs']['d5'] ^ 1})))
    f = pool[0]
    out.append(U.Fixture('negative-stop-' + f.name, f.state, [], f.stop, 'mismatch', cpp_stop=0x2ac2 if f.stop != 0x2ac2 else 0xc686))
    chain = [f for f in fixtures if f.name.startswith('chain-restart') and f.expect == 'match']
    if chain:                                                    # one flipped byte of the RNG-table path
        g = chain[0]
        out.append(U.Fixture('negative-chain-' + g.name, g.state, [], g.stop, 'mismatch', cpp_state=U.flip_ram(g.state, 0x10f02d)))
    return out


def coverage(fixtures):
    got = collections.Counter()
    for f in fixtures:
        if f.name.startswith('edge-') and f.expect == 'match':
            got[int(f.meta['block'], 16)] += 1
    missing = [pc for pc in STARTS if got[pc] == 0]
    return missing


def build():
    rng = random.Random(0xc2c2)
    out = []
    for case in CASES:
        for pc in STARTS:
            out += edge_fixtures(rng, pc, case)
    missing = coverage(out)
    if missing:
        print('edge fixtures missing for: %s' % ' '.join(hx(p) for p in missing), file=sys.stderr)
    for case in CASES:
        out += carry_fixtures(rng, case)
        out += zflag_fixtures(rng, case)
        out += chain_fixtures(rng, case)
    out += natural_fixtures()
    out += card_resume_fixtures(rng, CASES[0])
    out += exec_fixtures()
    out += error_fixtures(CASES[0])
    out += negative_fixtures(out)
    return out
