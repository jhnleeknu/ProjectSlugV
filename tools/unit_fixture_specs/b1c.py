"""Native fixture spec of unit B1c (N29b 64 + N30b 160 = 224 block starts, executor animation_objects_b1c_block) for tools/verify_animation_machine_unit_fixtures.py.

Every fixture is a typed state of a NATURAL parent node (RNG-initialised seed 116 / 117, frame 2): the N30 object of the callback 331d8 (A6 = the node) for the N30b
blocks and the N28 object of the callback 3075a for the N29b blocks.  Declared host writes edit the node fields (BYTE / WORD / LONG, in the 14..a0 window) and the
registers; the C++ run and the native Unicorn run of the original ROM start from the same declared state and must agree on RAM, D0-D7 / A0-A7, PC, bank, PVC page, ports
and the external-read bookkeeping at the stop PC.  Native-determined stop PCs: the verifier needs a stop PC that both sides reach, so `trace()` runs the original code
natively from the entry (never the C++) and reports the first PC that is another B1c block start, outside the B1c ranges, or (chains) a declared stop.

Groups:
  edge-<pc>-<k>   every one of the 224 block starts is entered directly with randomised (seeded) field / register worlds; one fixture per distinct native successor
                  (both sides of every branch a world can reach); the successor is the stop.  The C consumers use tag Clear (native SR C = 0 on start).
  bnd-<pc>-<k>    BOUNDARY_CASES: declared field / register values on both sides of every compare, bit test and table limit (one fixture each).
  setc-<pc>       the six consumers with a real Set C: the declared producer 31a08 (N29a block: MOVE.W D0,86(A6); ORI.B #1,CCR; RTS) with the consumer as the return LONG at A7;
                  clearc-<pc> the matching Clear (RTS block 31a10 with the consumer as return LONG).  49fc6-fed consumers (3328e 3352c) also run the real interpreter
                  (entry at the JSR block, LONG 26(A6) = 0 -> C Set by 49fc6, a real script -> C from the script).
  table-*         30b78 for D0.B = 0..26 and the limit 27 (the block 30bf0) and 335f6 for D0.W = 0..9, the 4 * D0.W wrap (D0.W = 4000) and the checked errors for a computed
                  PC inside a block (30b78 D0.B = 28; 335f6 D0.W = 10), in another unit's block (335f6 D0.W = 2000: 2b5fe, the B3a block 2b5fc since B3a) and in another unit's block interior.
  chain-*         multi-block runs from the installs 30b6c / 3323e / 331d8-world through the real routed callees (interpreter 49f8c / 49fc6, 3af8, 496c2, 4ae4a, 4d8d8, N30a, N29a ...)
                  to the first boundary.
  error-*         checked errors with state preservation: Unknown C into the six consumers, every internal even PC of the three ranges, unrouted work-RAM probe PCs, odd PCs.
  negative-*      the C++ input differs by one bit; the comparison must report it.
Boundary stops: 317b8 33940 33c78 33d2c 33dce 33e48 343e0 34470 34490 3453a 4c2c4 4d418 4d734 4d98a 4d9ba 4db18 4ff96 d3d7c (no executor in B1c).
"""
import random

import verify_animation_machine_unit_fixtures as U

SEEDS = (116, 117)
FRAME = 2
N30_CB, N29_CB = 0x331d8, 0x3075a
RANGES = ((0x30b6c, 0x30d6c), (0x3323e, 0x336d2), (0x3395c, 0x33a88))
N29B = ('30b6c 30b78 30b84 30b88 30b8c 30b90 30b94 30b98 30b9c 30ba0 30ba4 30ba8 30bac 30bb0 30bb4 30bb8 30bbc 30bc0 30bc4 30bc8 30bcc 30bd0 30bd4 '
        '30bd8 30bdc 30be0 30be4 30be8 30bec 30bf0 30c00 30c06 30c0c 30c16 30c1c 30c3c 30c46 30c4c 30c52 30c5e 30c64 30c68 30c70 30c78 30c7c 30c80 '
        '30c86 30c8a 30c8e 30c92 30c96 30ca4 30cae 30cb4 30cb8 30cc4 30ccc 30cd6 30cdc 30cf8 30d14 30d30 30d5c 30d66').split()
N30B = ('3323e 33248 3324c 33250 33264 33274 3327a 33280 33284 33288 3328e 33292 33298 3329c 332a6 332bc 332d0 332d6 332da 332ea 332f0 332f8 332fe '
        '33320 33324 33328 3332c 33332 33336 33358 33364 33368 33370 3337a 3337e 33386 33390 33394 333aa 333ac 333b4 333b8 333bc 333c0 333c4 333ce '
        '333d4 333dc 333e2 333e8 333f2 33408 33414 3341a 3341e 33428 33430 33434 3346a 3346e 33472 33478 33482 33498 3349e 334a8 334ac 334b4 334bc '
        '334c0 334c4 334c8 334cc 334d2 334dc 334ea 334fa 33500 33504 3350c 33516 3351a 3351e 33522 33526 3352c 33530 33536 3353a 33546 3354a 33550 '
        '3355a 33562 33580 33584 33588 3358e 3359c 335b4 335b8 335c4 335cc 335d0 335d4 335d8 335de 335ee 335f6 335fe 33602 33606 3360a 3360e 33612 '
        '33616 3361a 3361e 33622 3362c 33636 3363a 33644 3364e 33654 33670 3368c 336b8 336c2 336cc 3395c 33964 33968 33970 33974 33980 33990 33994 '
        '339a4 339aa 339b0 339bc 339c6 339d2 339dc 339e0 339ec 339f6 339fa 33a08 33a0c 33a16 33a20 33a28 33a30 33a3a 33a48 33a50 33a5a 33a76').split()
STARTS = tuple(int(x, 16) for x in N29B + N30B)
STARTSET = frozenset(STARTS)
CONSUMERS = {0x30c7c: 'bcs', 0x3328e: 'bcc', 0x33390: 'bcc', 0x3352c: 'bcc', 0x335b4: 'bcs', 0x33a08: 'bcs'}
BOUNDARY = frozenset([0x317b8, 0x33940, 0x33c78, 0x33d2c, 0x33dce, 0x33e48, 0x343e0, 0x34470, 0x34490, 0x3453a, 0x4c2c4, 0x4d418, 0x4d734, 0x4d98a, 0x4d9ba, 0x4db18, 0x4ff96, 0xd3d7c])
EXITS = frozenset([0x2a00, 0x30fa0, 0x33132, 0x33a88, 0x33aa4, 0x2ac2])
CHAIN_STOPS = BOUNDARY | EXITS
PRODUCER_SET, PRODUCER_CLEAR = 0x31a08, 0x31a10
TABLE_ENTRIES = frozenset([0x30b78, 0x335f6])      # the computed JMP blocks: table-* fixtures (a random index may land inside a block)
MAX_VARIANTS = 56
OFFSET_BYTES = {
    0x15: (0, 0x80, 0xa0, 0x20, 0xff, 0x7f), 0x5e: (0, 1, 2, 9, 0x1a, 0x1b, 0x1c, 0x18, 0xff), 0x5f: (0, 1, 0x0f, 0x35, 0xf7, 0xff),
    0x61: (0, 1, 0x40, 0x41, 0x80, 0xc1, 0xff), 0x8e: (0, 1, 5), 0x8f: (0, 0xc, 1, 0xb), 0x90: (0, 1, 2, 0xf), 0x91: (0, 1, 2, 0xf),
    0x93: (0, 3, 0xff), 0x94: (0, 1, 0xff, 4), 0x95: (0, 1, 2, 3, 0xff), 0x96: (0, 1, 2, 3, 0xff), 0x97: (0, 1, 0xf), 0x98: (0, 1, 0x60, 0xff),
    0x99: (0, 1, 9), 0x9a: (0, 1, 2), 0x9b: (0, 1, 2, 3, 4)}
OFFSET_WORDS = {
    0x42: (0, 0x10f, 0x110, 0x111, 0x8000, 0xffff, 0x7fff), 0x7a: (0, 1, 0x1234, 0x8000, 0xffff), 0x7e: (0, 1, 2, 0x1e), 0x80: (0, 5, 0xffff), 0x82: (0, 5, 0xffff),
    0x86: (0, 1, 2, 3, 0x7f, 0x8000, 0xffff, 0xfffe), 0x88: (0, 0x2d, 0xffff), 0x8a: (0, 0x8000), 0x9c: (0, 1), 0x9e: (0, 1)}
LONG_VALUES = (0, 1, 0x10000, 0x20000, 0x30000, 0x1ffff, 0x20001, 0xffff0000, 0xfffe0000, 0xfffdffff, 0xfffe0001, 0x7fffffff, 0x80000000, 0xffffffff,
               0x00040000, 0xfffc0000, 0x00080000, 0x00100000, 0x000fffff, 0x00100001)
OFFSET_LONGS = {0x36: LONG_VALUES, 0x3a: LONG_VALUES, 0x64: LONG_VALUES, 0x56: (0, 0x10c800, 0x10c900, 0x100000), 0x76: (0, 0x34966)}
REG_VALUES = (0, 1, 2, 3, 4, 0x7f, 0x80, 0xff, 0x100, 0x1234, 0x7fff, 0x8000, 0xffff, 0x10000, 0x80000000, 0xffffffff, 0xfffffff8, 0xfffffff0)
POINTERS = {'a0': 0x10c800, 'a1': 0x10c400}


# Boundary values of every compare / bit test (block, {field offset: (size, value)}, {register: value}): both sides of each threshold, used by the native fixtures here and by the rows
# of the unit test table (tools/generate_animation_machine_objects_b1c_test_table.py).
def _f(*pairs):
    return dict(pairs)


BOUNDARY_CASES = (
    (0x30b6c, {0x5e: (1, 0x1a)}, {}), (0x30b6c, {0x5e: (1, 0x1b)}, {}), (0x30b6c, {0x5e: (1, 0x1c)}, {}), (0x30b6c, {0x5e: (1, 0)}, {}),
    (0x30c06, {}, {'d0': 0x7fff}), (0x30c06, {}, {'d0': 0x8000}), (0x30c5e, {}, {'d0': 0x7f}), (0x30c5e, {}, {'d0': 0x80}), (0x30c5e, {}, {'d0': 0xff80}),
    (0x30c68, {}, {'d0': 0x1f}), (0x30c68, {}, {'d0': 0x20}), (0x30c96, {0x98: (1, 0)}, {}), (0x30c96, {0x98: (1, 1)}, {}), (0x30ca4, {0x98: (1, 1)}, {'d0': 1}),
    (0x33250, {0x8e: (1, 0)}, {}), (0x33250, {0x8e: (1, 1)}, {}), (0x33250, {0x8e: (1, 0x80)}, {}),
    (0x332da, {}, {'d0': 0x08}), (0x332da, {}, {'d0': 0x04}), (0x332da, {}, {'d0': 0x0c}), (0x332da, {}, {'d0': 0xf3}), (0x332f0, {}, {'d0': 4}), (0x332f0, {}, {'d0': 0xfb}),
    (0x332fe, {0x3a: (4, 0x30000), 0x36: (4, 0)}, {'d1': 0x40000, 'd2': 1}), (0x332fe, {0x3a: (4, 0x28000), 0x36: (4, 0)}, {'d1': 0, 'd2': 1}),
    (0x332fe, {0x3a: (4, 0x20000), 0x36: (4, 0)}, {'d1': 0, 'd2': 1}), (0x332fe, {0x3a: (4, 0xffff0000), 0x36: (4, 0)}, {'d1': 0, 'd2': 1}),
    (0x332fe, {0x3a: (4, 0x7fffffff), 0x36: (4, 0x80000000)}, {'d1': 0xfffc0000, 'd2': 0x41}), (0x332fe, {0x3a: (4, 0x80000000), 0x36: (4, 0x7fffffff)}, {'d1': 0x40000, 'd2': 0x20}),
    (0x3337e, {0x3a: (4, 0x00010000)}, {}), (0x3337e, {0x3a: (4, 0x0000ffff)}, {}), (0x3337e, {0x3a: (4, 0)}, {}), (0x3337e, {0x3a: (4, 0xffff0000)}, {}),
    (0x3337e, {0x3a: (4, 0x7fff0000)}, {}), (0x3337e, {0x3a: (4, 0x80000000)}, {}),
    (0x33368, {}, {'d0': 2}), (0x33368, {}, {'d0': 0xfd}), (0x33370, {0x15: (1, 0x80)}, {}), (0x33370, {0x15: (1, 0x7f)}, {}),
    (0x33394, {0x3a: (4, 0x20000)}, {}), (0x33394, {0x3a: (4, 0xffffffff)}, {}), (0x333ac, {}, {'d0': 0x80}), (0x333ac, {}, {'d0': 0x7f}),
    (0x333c4, {0x8f: (1, 0xc)}, {}), (0x333c4, {0x8f: (1, 0xb)}, {}), (0x333c4, {0x8f: (1, 0xd)}, {}),
    (0x333d4, {0x86: (2, 1)}, {}), (0x333d4, {0x86: (2, 0)}, {}), (0x333d4, {0x86: (2, 0x8000)}, {}), (0x333d4, {0x86: (2, 0x8001)}, {}),
    (0x3341e, {}, {'d0': 0x10}), (0x3341e, {}, {'d0': 0x0f}), (0x3341e, {}, {'d0': 0x100}), (0x3341e, {}, {'d0': 0xf0}), (0x33428, {}, {'d0': 0x80}), (0x33428, {}, {'d0': 0x7f}),
    (0x33434, {0x86: (2, 0)}, {}), (0x33434, {0x86: (2, 0xfd)}, {}), (0x33434, {0x86: (2, 0xffff)}, {}), (0x33434, {0x86: (2, 0x100)}, {}),
    (0x3349e, {0x15: (1, 0x80)}, {}), (0x3349e, {0x15: (1, 0)}, {}), (0x334ac, {}, {'d0': 0x20}), (0x334ac, {}, {'d0': 0xdf}), (0x334b4, {}, {'d0': 2}), (0x334b4, {}, {'d0': 0xfd}),
    (0x334dc, {0x8e: (1, 0)}, {}), (0x334dc, {0x8e: (1, 1)}, {}), (0x33504, {}, {'d0': 2}), (0x33504, {}, {'d0': 0xfd}), (0x3350c, {0x15: (1, 0x80)}, {}), (0x3350c, {0x15: (1, 0)}, {}),
    (0x3359c, {0x36: (4, 0xffffffff)}, {}), (0x3359c, {0x36: (4, 0x100000)}, {}), (0x3359c, {0x36: (4, 0x7fffffff)}, {}),
    (0x335b8, {0x3a: (4, 0x7ffff800)}, {}), (0x335c4, {0x3a: (4, 0x80000000)}, {}), (0x335c4, {0x3a: (4, 0xfffff7ff)}, {}),
    (0x335ee, {}, {'d0': 8}), (0x335ee, {}, {'d0': 9}), (0x335ee, {}, {'d0': 0x10008}), (0x335ee, {}, {'d0': 0xffff}),
    (0x33622, {0x42: (2, 0x110)}, {}), (0x33622, {0x42: (2, 0x111)}, {}), (0x33622, {0x42: (2, 0x10f)}, {}), (0x33622, {0x42: (2, 0x8000)}, {}), (0x33622, {0x42: (2, 0x7fff)}, {}),
    (0x3362c, {0x61: (1, 1)}, {}), (0x3362c, {0x61: (1, 0xfe)}, {}),
    (0x3395c, {0x90: (1, 0)}, {}), (0x3395c, {0x90: (1, 1)}, {}), (0x33964, {0x90: (1, 0)}, {}), (0x3395c, {0x90: (1, 0x80)}, {}),
    (0x33968, {0x91: (1, 0)}, {}), (0x33968, {0x91: (1, 1)}, {}), (0x33970, {0x91: (1, 1)}, {}),
    (0x33974, {0x95: (1, 2), 0x96: (1, 2)}, {}), (0x33974, {0x95: (1, 2), 0x96: (1, 3)}, {}), (0x33974, {0x95: (1, 0xff), 0x96: (1, 0xff)}, {}),
    (0x33994, {0x95: (1, 2)}, {}), (0x33994, {0x95: (1, 1)}, {}), (0x33994, {0x95: (1, 3)}, {}),
    (0x339b0, {0x3a: (4, 0xfffe0000)}, {}), (0x339b0, {0x3a: (4, 0xfffe0001)}, {}), (0x339b0, {0x3a: (4, 0xfffdffff)}, {}), (0x339b0, {0x3a: (4, 0x7fffffff)}, {}),
    (0x339b0, {0x3a: (4, 0x80000000)}, {}), (0x339b0, {0x3a: (4, 0)}, {}),
    (0x339c6, {0x36: (4, 0x20000)}, {}), (0x339c6, {0x36: (4, 0x1ffff)}, {}), (0x339c6, {0x36: (4, 0x20001)}, {}), (0x339c6, {0x36: (4, 0x80000000)}, {}),
    (0x339c6, {0x36: (4, 0x7fffffff)}, {}),
    (0x339e0, {0x36: (4, 0xfffe0000)}, {}), (0x339e0, {0x36: (4, 0xfffe0001)}, {}), (0x339e0, {0x36: (4, 0xfffdffff)}, {}), (0x339e0, {0x36: (4, 0x80000000)}, {}),
    (0x33a20, {}, {'d0': 3}), (0x33a20, {}, {'d0': 4}), (0x33a20, {}, {'d0': 5}), (0x33a20, {}, {'d0': 0x104}),
    (0x33a48, {0x5e: (1, 0)}, {}), (0x33a48, {0x5e: (1, 1)}, {}), (0x33a48, {0x5e: (1, 0x80)}, {}),
    (0x33a50, {0x61: (1, 0x40)}, {}), (0x33a50, {0x61: (1, 0xbf)}, {}), (0x33a50, {0x61: (1, 0x80)}, {}),
    (0x33a5a, {0x5f: (1, 0xf7)}, {'d1': 0x12345678}), (0x33a5a, {0x5f: (1, 0x10)}, {'d1': 0xffffffff}),
    (0x33a76, {0x36: (4, 0xffffffff), 0x3a: (4, 0x7fffffff)}, {'d0': 1, 'd1': 1}), (0x33a76, {0x36: (4, 0)}, {'d0': 0xffffffff, 'd1': 0x80000000}),
)


def hx(pc):
    return '%x' % pc


def in_ranges(pc):
    return any(lo <= pc < hi for lo, hi in RANGES)


# ----------------------------------------------------------------------------------
# Natural parent nodes
# ----------------------------------------------------------------------------------
NODES = {}


def parent(case, callback):
    """Natural node fixture of seed `case`, frame FRAME, whose callback is `callback` (cached)."""
    key = (case, callback)
    if key not in NODES:
        fr = [f for f in U.seed_frames(case, FRAME + 1) if f['frame'] == FRAME][0]
        index = fr['n']['cbs'].index(callback)
        NODES[key] = U.seed_node_fixture(case, FRAME, node=index)
    return NODES[key]


def n30_state(case):
    return parent(case, N30_CB).state


def n29_state(case):
    return parent(case, N29_CB).state


def base_of(pc, case):
    return n29_state(case) if pc < 0x31000 else n30_state(case)


# ----------------------------------------------------------------------------------
# Native tracer: the original code from a declared entry to the first stop (no C++)
# ----------------------------------------------------------------------------------
def trace(state, entry, rule, after=None, limit=3000, status=0):
    """-> dict(pc, steps, visited) or None.  rule(pc) -> True stops BEFORE executing pc (the entry itself never stops); `after`: the rule is armed only once pc == after."""
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
    seen = dict(pc=None, steps=0, armed=after is None, visited=[])

    def code(uc, pc, size, user):
        if seen['steps'] > 0:
            if not seen['armed']:
                seen['armed'] = pc == after              # armed AT `after`: its own block still runs
            elif rule(pc):
                seen['pc'] = pc
                uc.emu_stop()
                return
        if pc in STARTSET:
            seen['visited'].append(pc)
        seen['steps'] += 1
    c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    try:
        c.emu_start(entry, 0xffffff, count=limit)
    except unicorn.UcError:
        return None
    if seen['pc'] is None or m.odd is not None or m.invalid is not None or m.intr is not None:
        return None
    if any(a != U.STATUS_ADDR for a, _ in m.dev_reads):
        return None
    return dict(pc=seen['pc'], steps=seen['steps'], visited=seen['visited'])


def edge_rule(pc):
    return pc in STARTSET or not in_ranges(pc)


ROUTING = []


def routed(pc):
    """True when the checked-out dispatch chain of engine/src/animation_machine.cpp has an executor for pc (the chain is parsed once; stage_event_ops_trap PCs are not routed)."""
    import re
    if not ROUTING:
        src = (U.ROOT / 'engine/src/animation_machine.cpp').read_text()
        body = src[src.index('if ((next.pc>=0x3ac8'):src.index('else return am_error(c,"unsupported animation machine PC")')]
        for m in re.finditer(r'(?:else )?if \((.*?)\)ok=(\w+)\(c\);', body, re.S):
            e = m.group(1).replace('next.pc', 'p').replace('&&', ' and ').replace('||', ' or ')
            e = re.sub(r'!stage_event_ops_trap\(p\)', 'not trap(p)', e).replace('!=', '<>').replace('!', ' not ').replace('<>', '!=')
            ROUTING.append(compile('(' + e.replace('\n', ' ') + ')', 'routing', 'eval'))
        ROUTING.append(None)
    env = dict(p=pc, trap=lambda x: x in TRAPS)
    return any(eval(r, env) for r in ROUTING if r is not None)


TRAPS = frozenset([0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788])


def chain_rule(pc):
    """A declared stop (boundary / exit) or a PC without an executor: the C++ run would end in the checked error there."""
    return pc in CHAIN_STOPS or not routed(pc)


# ----------------------------------------------------------------------------------
# Worlds (declared host writes and registers on a natural node)
# ----------------------------------------------------------------------------------
def world(rng, state, reg_bias=True):
    regs = dict(state['regs'])
    for k in range(8):
        v = rng.choice(REG_VALUES) if rng.random() < 0.6 else rng.getrandbits(32)
        regs['d%d' % k] = v
    for k, v in POINTERS.items():
        regs[k] = v
    a6 = state['regs']['a6']
    writes = []
    for off, vals in OFFSET_BYTES.items():
        if rng.random() < 0.55:
            writes.append((a6 + off, 1, rng.choice(vals) if rng.random() < 0.85 else rng.getrandbits(8)))
    for off, vals in OFFSET_WORDS.items():
        if rng.random() < 0.5:
            writes.append((a6 + off, 2, rng.choice(vals) if rng.random() < 0.85 else rng.getrandbits(16)))
    for off, vals in OFFSET_LONGS.items():
        if rng.random() < 0.5:
            writes.append((a6 + off, 4, rng.choice(vals) if rng.random() < 0.85 else rng.getrandbits(32)))
    return writes, regs


def edge_fixtures(rng, start, case, carry):
    """Fixtures of block `start`: one per distinct native successor over MAX_VARIANTS seeded worlds."""
    base = base_of(start, case)
    out, seen = [], {}
    if start in TABLE_ENTRIES:
        return out
    for v in range(MAX_VARIANTS):
        writes, regs = world(rng, base)
        st = U.with_host_writes(base, writes, regs=regs, pc=start)
        st = dict(st, carry=carry)
        r = trace(st, start, edge_rule)
        if r is None or r['pc'] in seen:
            continue
        seen[r['pc']] = True
        out.append(U.Fixture('edge-%x-s%d-%d' % (start, case, len(out)), st, [], r['pc'], meta=dict(block=hx(start), successor=hx(r['pc']), case=case, variant=v)))
    return out


def boundary_fixtures(case):
    """BOUNDARY_CASES on the natural parent node: one fixture each, native-determined successor as the stop."""
    out = []
    for k, (pc, fields, regs) in enumerate(BOUNDARY_CASES):
        base = base_of(pc, case)
        a6 = base['regs']['a6']
        writes = [(a6 + off, size, value) for off, (size, value) in sorted(fields.items())]
        rr = dict(POINTERS)
        rr.update(regs)
        st = dict(U.with_host_writes(base, writes, regs=rr, pc=pc), carry=0)
        r = trace(st, pc, edge_rule)
        if r is None:
            continue
        out.append(U.Fixture('bnd-%x-s%d-%d' % (pc, case, k), st, [], r['pc'], meta=dict(block=hx(pc), successor=hx(r['pc']), case=case)))
    return out


# ----------------------------------------------------------------------------------
# Carry consumers with a real C (Set from the 31a08 producer, Clear from the RTS block 31a10, and the real interpreter 49fc6)
# ----------------------------------------------------------------------------------
def with_return(state, ret):
    """Declared return LONG `ret` at A7 (the node's dispatcher return is replaced; the fixture ends before it is used)."""
    return U.with_host_writes(state, [(state['regs']['a7'], 4, ret)])


def carry_fixtures(rng, case):
    out = []
    for consumer in CONSUMERS:
        base = base_of(consumer, case)
        for kind, producer, tag in (('setc', PRODUCER_SET, 0), ('clearc', PRODUCER_CLEAR, 1)):
            for attempt in range(8):
                writes, regs = world(rng, base)
                st = with_return(U.with_host_writes(base, writes, regs=regs, pc=producer), consumer)
                st = dict(st, carry=tag)
                r = trace(st, producer, edge_rule, after=consumer)
                if r is not None:
                    out.append(U.Fixture('%s-%x-s%d' % (kind, consumer, case), st, [], r['pc'],
                                         meta=dict(consumer=hx(consumer), kind=kind, successor=hx(r['pc']), case=case)))
                    break
    return out


def interpreter_carry_fixtures(rng, case):
    """3328e / 3352c fed by the real 49fc6 (routed interpreter): LONG 26(A6) = 0 gives C Set at once; seeded edits of the interpreter fields 16..29(A6) give the script's C.
    One fixture per consumer successor (C Set and C Clear) is kept, whatever the interpreter returns for the world."""
    out = []
    st30 = n30_state(case)
    a6 = st30['regs']['a6']
    for entry, consumer in ((0x33288, 0x3328e), (0x33526, 0x3352c)):
        seen = {}
        for attempt in range(120):
            writes, regs = world(rng, st30)
            regs['a0'] = a6 + 0x26
            if attempt == 0:
                writes.append((a6 + 0x26, 4, 0))
            else:
                for off in range(0x16, 0x2a):
                    if rng.random() < 0.4:
                        writes.append((a6 + off, 1, rng.choice((0, 1, 2, 0x10, 0x7f, 0x80, 0xff, rng.getrandbits(8)))))
            st = dict(U.with_host_writes(st30, writes, regs=regs, pc=entry), carry=0)
            r = trace(st, entry, edge_rule, after=consumer)
            if r is None or r['pc'] in seen:
                continue
            seen[r['pc']] = True
            out.append(U.Fixture('interp-%x-%x-s%d' % (consumer, r['pc'], case), st, [], r['pc'],
                                 meta=dict(consumer=hx(consumer), successor=hx(r['pc']), case=case, attempt=attempt)))
            if len(seen) == 2:
                break
    return out


# ----------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------
def table_fixtures(rng, case):
    out = []
    base29, base30 = n29_state(case), n30_state(case)
    a629, a630 = base29['regs']['a6'], base30['regs']['a6']
    for k in list(range(0, 28)) + [0x100, 0x101, 0x41b]:
        writes, regs = world(rng, base29)
        regs['d0'] = (regs['d0'] & 0xffff0000) | k
        st = U.with_host_writes(base29, writes, regs=regs, pc=0x30b78)
        r = trace(st, 0x30b78, edge_rule)
        if r is not None:
            out.append(U.Fixture('table-30b78-k%d-s%d' % (k, case), st, [], r['pc'], meta=dict(index=k, successor=hx(r['pc']))))
    for k in range(0, 10):
        writes, regs = world(rng, base30)
        regs['d0'] = (regs['d0'] & 0xffff0000) | k
        st = U.with_host_writes(base30, writes, regs=regs, pc=0x335f6)
        r = trace(st, 0x335f6, edge_rule)
        if r is not None:
            out.append(U.Fixture('table-335f6-k%d-s%d' % (k, case), st, [], r['pc'], meta=dict(index=k, successor=hx(r['pc']))))
    # 4 * D0.W wraps at 16 bit: D0.W = 4000 -> slot 0
    st = U.with_host_writes(base30, [], regs={'d0': 0x00004000}, pc=0x335f6)
    r = trace(st, 0x335f6, edge_rule)
    if r is not None:
        out.append(U.Fixture('table-335f6-wrap-s%d' % case, st, [], r['pc'], meta=dict(successor=hx(r['pc']))))
    # computed PC inside a B1c block, in unrouted code, in another unit's block interior (checked errors, state preserved)
    out.append(U.Fixture('error-table-30b78-k28-s%d' % case, U.with_host_writes(base29, [], regs={'d0': 28}, pc=0x30b78), [], 0xffffe,
                         ('error', 'unsupported animation objects b1c PC')))
    out.append(U.Fixture('error-table-335f6-k10-s%d' % case, U.with_host_writes(base30, [], regs={'d0': 10}, pc=0x335f6), [], 0xffffe,
                         ('error', 'unsupported animation objects b1c PC')))
    # D0.W = 2000: 335fe + sext(8000) = 2b5fe, inside the B3a block 2b5fc since B3a (was unrouted code before; the sign extension is still decided)
    out.append(U.Fixture('error-table-335f6-unrouted-s%d' % case, U.with_host_writes(base30, [], regs={'d0': 0x2000}, pc=0x335f6), [], 0xffffe,
                         ('error', 'unsupported animation objects b3a PC')))
    # the failing PC itself: the same state with the stop PC 2b5fe stops exactly there on both sides
    out.append(U.Fixture('table-335f6-landing-2b5fe-s%d' % case, U.with_host_writes(base30, [], regs={'d0': 0x2000}, pc=0x335f6), [], 0x2b5fe))
    out.append(U.Fixture('error-table-30b78-n29-interior-s%d' % case, U.with_host_writes(base29, [], regs={'d0': 255}, pc=0x30b78), [], 0xffffe,
                         ('error', 'unsupported animation objects n29 PC')))
    return out


# ----------------------------------------------------------------------------------
# Chains through the real routed callees
# ----------------------------------------------------------------------------------
def chain_fixtures(rng, case):
    out = []
    base29, base30 = n29_state(case), n30_state(case)
    entries = [(0x30b6c, base29), (0x3323e, base30), (0x33250, base30), (0x33280, base30), (0x332d6, base30), (0x33364, base30), (0x333f2, base30), (0x3341a, base30),
               (0x33482, base30), (0x3349e, base30), (0x33500, base30), (0x3354a, base30), (0x3359c, base30), (0x3395c, base30), (0x30c4c, base29), (0x30cb8, base29)]
    for entry, base in entries:
        seen = set()
        for v in range(24):
            writes, regs = world(rng, base)
            a6 = base['regs']['a6']
            writes.append((a6, 4, entry))
            st = dict(U.with_host_writes(base, writes, regs=regs, pc=entry), carry=0)
            r = trace(st, entry, chain_rule, limit=60000)
            if r is None or (r['pc'], tuple(r['visited'])) in seen:
                continue
            seen.add((r['pc'], tuple(r['visited'])))
            out.append(U.Fixture('chain-%x-s%d-%d' % (entry, case, len(seen)), st, [], r['pc'],
                                 meta=dict(entry=hx(entry), stop=hx(r['pc']), blocks=len(r['visited']), case=case, variant=v)))
            if len(seen) >= 4:
                break
    # natural 30b6c entry with BYTE 5e = 0..26 / limit values: every slot through the table block
    a6 = base29['regs']['a6']
    for k in tuple(range(27)) + (27, 0x1c, 0xff):
        writes = [(a6 + 0x5e, 1, k), (a6, 4, 0x30b6c)]
        st = dict(U.with_host_writes(base29, writes, pc=0x30b6c), carry=0)
        r = trace(st, 0x30b6c, chain_rule, limit=60000)
        if r is not None:
            out.append(U.Fixture('chain-30b6c-5e-%02x-s%d' % (k, case), st, [], r['pc'], meta=dict(entry='30b6c', stop=hx(r['pc']), blocks=len(r['visited']), case=case)))
    return out


# ----------------------------------------------------------------------------------
# Checked errors
# ----------------------------------------------------------------------------------
def error_fixtures(case):
    out = []
    for consumer in CONSUMERS:
        base = base_of(consumer, case)
        out.append(U.Fixture('error-unknown-carry-%x-s%d' % (consumer, case), dict(U.with_host_writes(base, [], pc=consumer), carry=0), [], 0xffffe,
                             ('error', 'objects b1c caller requires known carry')))
    if case != SEEDS[0]:
        return out
    probe = U.with_host_writes(n30_state(case), [])
    for lo, hi in RANGES:
        for pc in range(lo, hi, 2):
            if pc not in STARTSET:
                out.append(U.Fixture('error-interior-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation objects b1c PC')))
    for pc in (0x10fe00, 0x10fe40, 0x10fefe):
        out.append(U.Fixture('error-unrouted-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unsupported animation machine PC')))
    for lo, hi in RANGES:
        for pc in (lo + 1, hi - 1):
            out.append(U.Fixture('error-odd-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', 'unaligned animation machine PC')))
    # neighbouring PCs just outside the ranges stay in their own units / unrouted
    for pc, text in ((0x30d6c, 'unsupported animation machine PC'), (0x3323c, 'unsupported animation objects n30 PC'), (0x336d4, 'unsupported animation objects n30 PC'),
                    (0x3395a, 'unsupported animation objects n30 PC'), (0x33a8a, 'unsupported animation objects n30 PC')):
        out.append(U.Fixture('error-outside-%x' % pc, U.with_host_writes(probe, [], pc=pc), [], 0xffffe, ('error', text)))
    return out


def negative_fixtures(fixtures):
    """C++ input differs from the native one by one RAM byte / register / bank: the comparison must report a difference."""
    out = []
    pool = [f for f in fixtures if f.name.startswith('edge-') and f.expect == 'match']
    for f in pool[:4]:
        st = f.state
        out.append(U.Fixture('negative-ram-' + f.name, st, [], f.stop, 'mismatch', cpp_state=U.flip_ram(st, 0x10fff0)))
        out.append(U.Fixture('negative-reg-' + f.name, st, [], f.stop, 'mismatch', cpp_state=U.with_host_writes(st, regs={'d5': st['regs']['d5'] ^ 1})))
    f = pool[0]
    out.append(U.Fixture('negative-stop-' + f.name, f.state, [], f.stop, 'mismatch', cpp_stop=0x2ac2))
    return out


def build():
    rng = random.Random(0x1b1c)
    out = []
    for case in SEEDS:
        for pc in STARTS:
            out += edge_fixtures(rng, pc, case, 1 if pc in CONSUMERS else 0)
    for case in SEEDS:
        out += boundary_fixtures(case)
        out += carry_fixtures(rng, case)
        out += interpreter_carry_fixtures(rng, case)
        out += table_fixtures(rng, case)
        out += chain_fixtures(rng, case)
        out += error_fixtures(case)
    out += negative_fixtures(out)
    return out
