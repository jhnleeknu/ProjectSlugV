"""Native fixture spec of unit C1 (controller per-frame gates c66a / c7fc, common tail c988, credit / digit / timer helpers: 116 block starts, executor
animation_controller_c1_block) for tools/verify_animation_machine_unit_fixtures.py.

Every fixture starts from a NATURAL controller entry state: the D1 native reference (seed_frames) of a natural seed ends its H segment at the controller callback
c52a (A6 = 1008e4, A5 = 108000, return LONG 2ac2 at A7 = 1feffc).  The declared D9 states are host writes on that state: game mode (ii) LONG 1008e4 := c7fc with BYTE
10fdaf = 100012 = 2, demo mode (i) LONG 1008e4 := c66a with BYTE 104cd4 = 1, and PC := the callback; typed fixtures edit the controller node fields (+78 +7a +7e +80 +81
+82 +83), the BIOS / credit bytes and the registers.  The C++ run and the native Unicorn run of the original ROM start from the same declared state and must agree on RAM,
D0-D7 / A0-A7, PC, bank, PVC page, ports and external-read bookkeeping at the stop PC.  Stop PCs are native-determined (`trace()` runs the original code, never the C++).

Groups:
  nat-<mode>-s<case>-f<frame>   natural controller frames of game mode (ii) and demo mode (i), the declared host writes only, run to the first boundary (2ac2 = the controller
                                RTS, or C2 c686 c74c c76a, or BIOS c00450 / c00444); idle stage frames (LONG 100b30 = 270e) end at the C2 boundary c76a / c686.
  edge-<pc>-s<case>-<k>         every one of the 116 block starts entered directly in seeded worlds; one fixture per distinct native successor (both sides of every branch a
                                world can reach).  Z consumers 4a9d0 / 4a9da are entered with a non-zero byte (native SR.Z = 0 at entry), the zero side is zflag-*.
  setc / clearc-<pc>            the six C consumers with a real Set / Clear C: the producer (ca32, 289e, 314c, 30bc, 30d4) entered with the consumer as the return LONG.
  zflag-<pc>-<n>                4a9b0 / 4a9c6 (TST.B (A0); RTS) entered with the Z consumer as the return LONG: A0 in the four proven bytes, byte zero / non-zero.
  sbcd-<byte>-<x>               c9fe..ca20 for all 512 inputs (BYTE 7a(A6) 0..ff, BYTE 7b(A6) 7 = borrow in / 8 = none).
  chain-*                       multi-block runs through the real routed callees (readiness 289e, hud 35f0, card menu 3650 3918, H2 3902, ...) to the first boundary:
                                tail worlds, credit text / value / bits worlds, digit renderer worlds, BIOS credit resume (c00450 stop + declared answer + 4a992).
  error-*                       checked errors with preservation: Unknown C into the six consumers, every internal even PC and odd PCs of the 12 ranges, the flag-source
                                guard (A0 outside the four bytes), backup RAM d00034 reads, unrouted neighbours.
  negative-*                    the C++ input differs by one bit; the comparison must report it.
Boundary stops: 2ac2 c686 c74c c76a c00450 c00444 (the executor and the frame driver own the BIOS resume) and every PC without an executor.
"""
import collections
import random

import verify_animation_machine_unit_fixtures as U

STARTS = tuple(int(x, 16) for x in (
    '30bc 30c8 30ce 30d4 30e0 30e6 314c 3156 315c 3670 367a 3680 3682 3688 3690 3698 369e 36a2 36b2 36b8 36ba 36c0 36c2 36cc 36d2 36d4 36da 36e2 36e6 36ec 36fc '
    '36fe 3702 3706 c49c c4a0 c4a4 c4aa c4b6 c4ba c4f8 c50e c526 c654 c664 c66a c674 c678 c67e c682 c724 c72e c736 c73a c73e c748 c7fc c806 c80a c988 c990 c996 '
    'c99a c9ac c9b4 c9ba c9be c9c2 c9ce c9d6 c9de c9ea c9f0 c9f2 c9f6 c9fe ca06 ca14 ca18 ca20 ca32 4a88e 4a896 4a89e 4a8ac 4a8b0 4a8ba 4a8c2 4a8cc 4a8ce 4a8da '
    '4a8de 4a8e6 4a944 4a94c 4a954 4a962 4a966 4a970 4a972 4a974 4a982 4a992 4a9a4 4a9ae 4a9b0 4a9b4 4a9c4 4a9c6 4a9ca 4a9d0 4a9d4 4a9d6 4a9da 4a9de 4a9e0').split())
STARTSET = frozenset(STARTS)
assert len(STARTS) == 116 and len(STARTSET) == 116
RANGES = ((0x30bc, 0x30ec), (0x314c, 0x3162), (0x3670, 0x370c), (0xc49c, 0xc4cc), (0xc4f8, 0xc52a), (0xc654, 0xc686), (0xc724, 0xc74c), (0xc7fc, 0xc80e),
          (0xc988, 0xca22), (0xca32, 0xca3a), (0x4a88e, 0x4a8f8), (0x4a944, 0x4a9e2))
CONSUMERS = {0xc4a0: 'bcc', 0xc674: 'bcc', 0xc67e: 'bcc', 0xc806: 'bcs', 0xc996: 'bcc', 0xc9ba: 'bcc'}
PRODUCER = {0xc4a0: 0xca32, 0xc674: 0x289e, 0xc67e: 0x314c, 0xc806: 0x289e, 0xc996: 0x30bc, 0xc9ba: 0x30d4}
Z_CONSUMERS = (0x4a9d0, 0x4a9da)
Z_BYTES = (0x10fdb0, 0x10fdb1, 0x100004, 0x100005)
BOUNDARY = frozenset([0x2ac2, 0xc686, 0xc74c, 0xc76a, 0xc00450, 0xc00444])
NODE = 0x1008e4
CASES = (0, 94)
MAX_VARIANTS = 56
NATURAL_CASES = (0, 1, 2, 94, 100, 135)
NATURAL_FRAMES = (1, 2, 3, 5, 40, 100, 200, 244, 245, 250, 299)
GAME_WRITES = [(0x10fdaf, 1, 2), (0x100012, 1, 2)]
DEMO_WRITES = [(0x104cd4, 1, 1)]

REG_VALUES = (0, 1, 2, 3, 4, 5, 7, 8, 0x7f, 0x80, 0xff, 0x100, 0x1234, 0x7fff, 0x8000, 0xffff, 0x10000, 0x10001, 0x80000000, 0xffffffff, 0xfffffff8, 0xfffffff0)
BYTE_POOL = {
    0x10fd8f: (0, 1, 2, 3, 0xff), 0x100964: (0, 0xa9, 0xaa, 0xab, 0xff), 0x10fd8b: (0, 1, 9, 0xfe, 0xff), 0x100003: (0, 1, 0xff), 0x100012: (0, 1, 2, 3),
    0x104cd4: (0, 1, 2, 0xff), 0x10fe80: (0, 1), 0x100004: (0, 1, 2, 5, 0x99, 0xff), 0x100005: (0, 1, 2, 5, 0x99, 0xff), 0x10fe00: (0, 1, 2, 0x99, 0xff),
    0x10fe01: (0, 1, 2, 0x99, 0xff), 0x10fdb0: (0, 1, 2, 0xff), 0x10fdb1: (0, 1, 2, 0xff),
    NODE + 0x80: (0, 1, 0xf9, 0xfa, 0xff), NODE + 0x81: (0, 1, 0xff), NODE + 0x82: (0, 1, 0xff), NODE + 0x83: (0, 1, 0xff)}
WORD_POOL = {NODE + 0x78: (0, 1, 3, 4, 5, 0x100, 0x8000, 0xffff), NODE + 0x7a: (0, 0x0007, 0x0008, 0x0100, 0x0107, 0x1000, 0x1008, 0x99ff, 0x0a00, 0x1a05, 0xffff),
             NODE + 0x7e: (0, 1, 0x0101, 0x0a0a, 0xffff)}
LONG_POOL = {0x100b30: (0x270e, 0x270e, 0x47af0, 0x47bfc, 0), 0x100100: (0x12345678, 0x00a0b0c0, 0x01020304, 0x09090909, 0x10101010, 0x0f0f0f0f)}
A0_POOL = (0x100100, 0x100101, 0x10c800, 0x10fe00, 0x10fdb0, 0x100004, 0x4a903, 0x4a8f8, 0x3650, 0xc46e, 0x108000, 0x1008e4)
A1_POOL = (0x3650, 0x3650, 0x3650, 0x100004, 0x10fe00, 0x10fdb0, 0x10c400, 0x100100, 0x100005)
D4_POOL = (1, 2, 3, 4, 5, 0x10001, 0x10002, 0x20003, 0xffff0004, 0, 0x8001)
D2_POOL = (0, 1, 2, 9, 0xa, 0xf, 0x10, 0x1f, 0x20, 0x1234, 0x11111111, 0x100)
D7_POOL = (0, 1, 2, 3, 0x4000, 0x4001, 0x10002, 0xffff0003, 0x2000, 0x7fff)
D3_POOL = (0, 1, 0xff, 0x100, 0xffffff00, 0x1234)


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
    """A boundary or a PC without an executor: the C++ run ends in the checked error / the stop there."""
    return pc in BOUNDARY or not routed(pc)


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
        regs['d%d' % k] = rng.choice(REG_VALUES) if rng.random() < 0.6 else rng.getrandbits(32)
    regs['d2'] = rng.choice(D2_POOL) if rng.random() < 0.8 else rng.getrandbits(32)
    regs['d3'] = rng.choice(D3_POOL)
    regs['d4'] = rng.choice(D4_POOL)
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
    if rng.random() < 0.08:
        writes.append((0x10fd82, 1, 1))                         # BIOS credit path (c00450 stop) or d00034 (world dropped by the tracer)
    return writes, regs


def block_stack(pc, rng, state):
    """Declared stack content for the blocks that pop their own pushes (the natural return LONG 2ac2 stays for the rest)."""
    a7 = state['regs']['a7']
    if pc in (0x36b2, 0x36fc, 0x4a8e6):
        return [(a7, 4, rng.choice((0x100100, 0x100101, 0x10c800, 0x4a903)))], {}
    if pc == 0x4a8c2:
        return [(a7, 4, rng.choice((0x100004, 0x10fe00, 0x100100))), (a7 + 4, 2, rng.choice((0, 1, 0x1234, 0xffff)))], {'a7': a7}
    if pc == 0x4a992:
        return [(a7, 2, rng.choice((0, 1, 0x1234)))], {}
    if pc == 0xc526:
        return [(a7 + 2, 1, rng.choice((0, 1, 0xff, 0x7f)))], {'a7': a7 + 2}
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


def producer_writes(consumer, kind, rng):
    """Declared bytes that make the producer of `consumer` return C Set ('set') or Clear ('clear')."""
    if consumer == 0xc4a0:                                       # ca32: BYTE 100964 below aa -> Set
        return [(0x100964, 1, rng.choice((0, 0x10, 0xa9) if kind == 'set' else (0xaa, 0xab, 0xff)))]
    if consumer in (0xc674, 0xc806):                             # 289e: callback 270e -> Clear
        return [(0x100b30, 4, rng.choice((0x47af0, 0x47bfc, 0) if kind == 'set' else (0x270e,)))]
    if consumer == 0xc67e:                                       # 314c: BYTE 104cd4 = 1 -> Set
        return [(0x104cd4, 1, 1 if kind == 'set' else rng.choice((0, 2, 0xff)))]
    if consumer == 0xc996:                                       # 30bc: BYTE 10fd8f bit 1 -> Set
        return [(0x10fd8f, 1, rng.choice((2, 3, 0xff) if kind == 'set' else (0, 1, 0xfd)))]
    return [(0x10fd8f, 1, rng.choice((1, 3, 0xff) if kind == 'set' else (0, 2, 0xfe)))]        # c9ba: 30d4 bit 0


def carry_fixtures(rng, case):
    out = []
    base = entry_state(case, 2)
    for consumer in sorted(CONSUMERS):
        for kind in ('set', 'clear'):
            for k in range(2):
                writes = producer_writes(consumer, kind, rng)
                regs = dict(base['regs'])
                regs['a0'] = 0x100b30
                st = dict(with_return(U.with_host_writes(base, writes, regs=regs, pc=PRODUCER[consumer]), consumer), carry=0)
                r = trace(st, PRODUCER[consumer], edge_rule, after=consumer)
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


def sbcd_fixtures(case):
    """All 512 SBCD inputs of ca06 through the real tail: BYTE 7a(A6) 00..ff x BYTE 7b(A6) 07 (X = 1) / 08 (X = 0)."""
    out = []
    base = entry_state(case, 2)
    for low in (7, 8):
        for high in range(256):
            writes = [(NODE + 0x7a, 1, high), (NODE + 0x7b, 1, low), (NODE + 0x83, 1, 0)]
            st = dict(U.with_host_writes(base, writes, pc=0xc9fe), carry=0)
            r = trace(st, 0xc9fe, chain_rule, seq_rule=seq_chain_rule)
            U.require(r is not None and r['pc'] == 0x2ac2, ('sbcd trace', high, low, r))
            out.append(U.Fixture('sbcd-%02x-%d' % (high, 1 if low == 7 else 0), st, [], 0x2ac2, meta=dict(byte=high, borrow_in=low == 7)))
    return out


# ----------------------------------------------------------------------------------
# Natural frames and chains through the real routed callees
# ----------------------------------------------------------------------------------
def natural_fixtures():
    out = []
    for case in NATURAL_CASES:
        for frame in NATURAL_FRAMES:
            base = entry_state(case, frame)
            for mode in ('game', 'demo'):
                st = dict(declare(base, mode), carry=0)
                r = trace(st, st['pc'], chain_rule, limit=60000, seq_rule=seq_chain_rule)
                if r is None:
                    continue
                out.append(U.Fixture('nat-%s-s%d-f%d' % (mode, case, frame), st, [], r['pc'],
                                     meta=dict(mode=mode, case=case, frame=frame, stop=hx(r['pc']), blocks=len(r['visited']))))
    return out


CHAIN_ENTRIES = (('game', 0xc7fc), ('demo', 0xc66a), ('tail', 0xc988), ('tail', 0xc9c2), ('tail', 0xc9de), ('tail', 0xc9f6), ('credit', 0xc49c), ('credit', 0xc4f8),
                 ('credit', 0x4a88e), ('credit', 0x4a944), ('credit', 0x4a974), ('credit', 0x4a9ca), ('digits', 0x3706), ('digits', 0x36ba), ('digits', 0xc50e),
                 ('mode', 0xc724), ('mode', 0xc73e), ('mode', 0xc72e), ('mode', 0xc654))


def chain_fixtures(rng, case):
    out = []
    base = entry_state(case, 3)
    for kind, entry in CHAIN_ENTRIES:
        seen = set()
        for v in range(40):
            writes, regs = world(rng, base)
            if kind in ('game', 'demo'):
                writes += (GAME_WRITES if kind == 'game' else DEMO_WRITES)
                if rng.random() < 0.5:
                    writes.append((NODE + 0x81, 1, rng.choice((1, 0xff))))
            if kind == 'demo':
                writes.append((0x104cd4, 1, 1))
            regs['a1'] = 0x3650
            st = dict(U.with_host_writes(base, writes, regs=regs, pc=entry), carry=0)
            r = trace(st, entry, chain_rule, limit=60000, seq_rule=seq_chain_rule)
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


def credit_resume_fixtures(rng, case):
    """4a9ca with BYTE 10fd82 = 1 and 10fe80 = 1 (backup pointer 10fe00): the first BIOS call stops at c00450 (fixture), then the declared answer LONG 10fdb0 with PC := 4a992,
    A7 += 4 (what the frame driver does) runs to the second BIOS call (fixture) and, resumed again, to the controller return."""
    out = []
    base = entry_state(case, 2)
    for k, answer in enumerate((0x01010000, 0x00000000, 0x01000000, 0x00010000, 0x00ff00ff)):
        for mode2 in (0, 2):                                    # BYTE 100012 = 2 (4a9a4 BEQ 4a9b0) or not
            writes = [(0x10fd82, 1, 1), (0x10fe80, 1, 1), (0x100012, 1, mode2), (0x100003, 1, k & 1)]
            st = dict(U.with_host_writes(base, writes, pc=0x4a9ca), carry=0)
            st1, _, r1 = U.advance_native(st, [], 0xc00450)
            out.append(U.Fixture('resume-bios1-%d-%d-s%d' % (k, mode2, case), st, [], 0xc00450))
            a7 = st1['regs']['a7']
            stack_ret = int.from_bytes(st1['ram'][a7 & 0xffff:(a7 & 0xffff) + 4], 'big')
            U.require(stack_ret == 0x4a992, ('resume return', hex(stack_ret)))
            res = dict(U.with_host_writes(st1, [(0x10fdb0, 4, answer)], regs={'a7': a7 + 4}, pc=0x4a992), carry=0)
            r = trace(res, 0x4a992, chain_rule, seq_rule=seq_chain_rule)
            if r is None:
                continue
            out.append(U.Fixture('resume-step2-%d-%d-s%d' % (k, mode2, case), res, [], r['pc'], meta=dict(answer=hex(answer), stop=hx(r['pc']))))
            if r['pc'] == 0xc00450:                              # second player: resume again, now to the controller RTS
                nat = U.native()
                m = nat.run(res, [], 0xc00450)
                U.require(m['ok'], ('native step2', m))
                st3 = U.native_state(m)
                a7b = st3['regs']['a7']
                res2 = dict(U.with_host_writes(st3, [(0x10fdb0, 4, answer)], regs={'a7': a7b + 4}, pc=0x4a992), carry=0)
                r3 = trace(res2, 0x4a992, chain_rule, seq_rule=seq_chain_rule)
                if r3 is not None:
                    out.append(U.Fixture('resume-step3-%d-%d-s%d' % (k, mode2, case), res2, [], r3['pc'], meta=dict(answer=hex(answer), stop=hx(r3['pc']))))
    return out


# ----------------------------------------------------------------------------------
# Checked errors
# ----------------------------------------------------------------------------------
def error_fixtures(case):
    out = []
    probe = entry_state(case, 2)
    st = U.with_host_writes(probe, [])
    for consumer in sorted(CONSUMERS):
        out.append(U.Fixture('error-unknown-carry-%x' % consumer, dict(U.with_host_writes(probe, [], pc=consumer), carry=0), [], 0xffffe,
                             ('error', 'controller c1 caller requires known carry')))
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in STARTSET:
                out.append(U.Fixture('error-interior-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation controller c1 PC')))
        for pc in (lo + 1, hi - 1):
            out.append(U.Fixture('error-odd-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unaligned animation machine PC')))
    for pc in (0x30ec, 0x3162, 0x370c, 0xc4cc, 0xc52a, 0xc686, 0xc74c, 0xc76a, 0xc80e, 0xca22, 0xca3a, 0x4a8f8, 0x4a9e2, 0xc00450, 0xc00444):
        if not routed(pc):
            out.append(U.Fixture('error-outside-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation machine PC')))
    # Z flag source guard: A0 outside 10fdb0 / 10fdb1 / 100004 / 100005
    for consumer in Z_CONSUMERS:
        for a0 in (0, 0x3000, 0x10fdaf, 0x10fdb2, 0x100003, 0x100006, 0x10fe00, 0xd00034, 0x1010fdb0 & 0xffffffff, 0xffffffff):
            regs = dict(probe['regs'])
            regs['a0'] = a0
            out.append(U.Fixture('error-flag-source-%x-%x' % (consumer, a0), U.with_host_writes(probe, [], regs=regs, pc=consumer), [], 0xffffe,
                                 ('error', 'unsupported animation controller flag source')))
    # MVS backup RAM d00034: BYTE 10fd82 set and BYTE 10fe80 clear -> A1 = d00034
    for entry in (0x4a88e, 0x4a944, 0x4a89e, 0x4a954):
        for bit in (0, 1):
            writes = [(0x10fd82, 1, 1), (0x10fe80, 1, 0), (0x100003, 1, bit)]
            out.append(U.Fixture('error-backup-%x-%d' % (entry, bit), U.with_host_writes(probe, writes, pc=entry), [], 0xffffe,
                                 ('error', 'unsupported animation controller backup RAM read')))
    for a1, size_entry in ((0xd00034, 0x4a8ce), (0xd00035, 0x4a8ce), (0xd00034, 0x4a966), (0xd00034, 0x4a970), (0xd0ffff, 0x4a970)):
        regs = dict(probe['regs'])
        regs['a1'] = a1
        out.append(U.Fixture('error-backup-a1-%x-%x' % (a1, size_entry), U.with_host_writes(probe, [], regs=regs, pc=size_entry), [], 0xffffe,
                             ('error', 'unsupported animation controller backup RAM read')))
    # unrouted live JSR (A1) target (work RAM) and an odd one: the next dispatch step fails
    regs = dict(probe['regs'])
    regs['a1'] = 0x10fe00
    out.append(U.Fixture('error-live-jsr-unrouted', U.with_host_writes(probe, [], regs=regs, pc=0x36a2), [], 0xffffe, ('error', 'unsupported animation machine PC')))
    regs['a1'] = 0x3651
    out.append(U.Fixture('error-live-jsr-odd', U.with_host_writes(probe, [], regs=regs, pc=0x36ec), [], 0xffffe, ('error', 'unaligned animation machine PC')))
    # odd WORD address of the credit pointer
    regs = dict(probe['regs'])
    regs['a1'] = 0x100005
    out.append(U.Fixture('error-odd-word-read', U.with_host_writes(probe, [], regs=regs, pc=0x4a966), [], 0xffffe, ('error', 'program bus requires even WORD/LONG address')))
    del st
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
    return out


def coverage(fixtures):
    got = collections.Counter()
    for f in fixtures:
        if f.name.startswith('edge-') and f.expect == 'match':
            got[int(f.meta['block'], 16)] += 1
    missing = [pc for pc in STARTS if got[pc] == 0]
    U.require(not missing, ('block starts without an edge fixture', [hx(p) for p in missing]))


def build():
    rng = random.Random(0xc1c1)
    out = []
    for case in CASES:
        for pc in STARTS:
            out += edge_fixtures(rng, pc, case)
    coverage(out)
    for case in CASES:
        out += carry_fixtures(rng, case)
        out += zflag_fixtures(rng, case)
        out += chain_fixtures(rng, case)
    out += sbcd_fixtures(CASES[0])
    out += natural_fixtures()
    out += credit_resume_fixtures(rng, CASES[0])
    out += error_fixtures(CASES[0])
    out += negative_fixtures(out)
    return out
