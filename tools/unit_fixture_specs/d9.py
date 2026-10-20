"""V1 fixture spec of controller C3a (D9): c52a c530 c55a c560 c566 c56c, 8b64 8b98 8bb6 (engine/src/animation_machine_controller_c3.cpp).

Entry states are natural D1 H end states (the controller transfer, PC = LONG (1008e4) = c52a, A6 = 1008e4, A7 = SPd - 4 holding 2ac2) of natural seeds; the controller
runs to the dispatcher return 2ac2 (the first 2ac2 reached; no callee reaches 2ac2 before the RTS).
  c52a       the natural boot head (area_clear 9056, the field clears, boot fill 8b64 -> H3 4718 -> 8b98, callback install c55a, then c560 / 8bb6 / c566 / c56c),
             frames 1 and 2 of three seeds, and with D0 high WORD overrides 0001 07ff 0800 ffff (c530 sets only D0.W).
  8b64       entered directly (declared PC override; RTS of 8b98 returns to 2ac2) with D0.W 0001 0400 07ff ffff: the LSL.L #5 / LEA (A0,D0.W) sign extension.
  c560       declared host writes LONG 1008e4 := c560, WORD 107dea in {0001, 2000, 8000, ffff} (the wait callback returns), and 107dea = 0 to the C3b boundary c56e
             (stop c56e: match; stop 2ac2: since C2/C3b the C++ run continues through the C3b blocks c56e..c598 and fails at the BIOS entry
             c00444 (JMP c00444 of c598) with the checked error 'unsupported animation machine PC', native not run; the failing PC is asserted, review 0264 L-1).
Expected checked errors: interior PC c532 / 8b6a, odd PC c52b.  Negative checks: flipped WORD 107dea byte, flipped node byte +82, wrong stop.
"""
import verify_animation_machine_unit_fixtures as U

SEEDS = 3
DISPATCH = 0x2ac2


def h_end_states(case, frames=(1, 2)):
    out = []
    for fr in U.seed_frames(case, max(frames) + 1):
        h = fr.get('h')
        if h is None or h['reason']['reason'] != 'controller' or fr['frame'] not in frames:
            continue
        out.append((fr, U.seed_state(h['end'])))
    return out


def build():
    out = []
    cases = U.natural_cases(SEEDS)
    first = None
    for c in cases:
        for fr, st in h_end_states(c):
            assert st['pc'] == 0xc52a, hex(st['pc'])
            status = fr['start']['status']
            name = 'c52a-seed%d-f%d' % (c, fr['frame'])
            out.append(U.Fixture(name, st, [], DISPATCH, external_status=status, meta=dict(case=c, frame=fr['frame'])))
            if first is None:
                first = (st, status)
    st, status = first
    for hi in (0x0001, 0x07ff, 0x0800, 0xffff):
        out.append(U.Fixture('c52a-d0hi-%04x' % hi, U.with_host_writes(st, regs={'d0': (hi << 16) | 0x1234}), [], DISPATCH, external_status=status))
    for lo in (0x0001, 0x0400, 0x07ff, 0xffff):
        out.append(U.Fixture('8b64-d0-%04x' % lo, U.with_host_writes(st, regs={'d0': 0x00030000 | lo}, pc=0x8b64), [], DISPATCH, external_status=status))
    for v in (0x0001, 0x2000, 0x8000, 0xffff):
        out.append(U.Fixture('c560-107dea-%04x' % v, U.with_host_writes(st, [(0x1008e4, 4, 0xc560), (0x107dea, 2, v)], pc=0xc560), [], DISPATCH,
                             external_status=status))
    opened = U.with_host_writes(st, [(0x1008e4, 4, 0xc560), (0x107dea, 2, 0)], pc=0xc560)
    out.append(U.Fixture('c560-107dea-0000-to-c56e', opened, [], 0xc56e, external_status=status))
    # Purpose changed with C2/C3b: it was the C3b boundary c56e (unrouted then); c56e..c598 are routed now and the run fails at the BIOS entry c00444 (fail_pc, evidence: stop c00444 succeeds).
    out.append(U.Fixture('error-c560-open-bios-c00444', opened, [], DISPATCH, ('error', 'unsupported animation machine PC'), external_status=status, fail_pc=0xc00444))
    for pc in (0xc532, 0x8b6a):
        out.append(U.Fixture('error-interior-%x' % pc, U.with_host_writes(st, pc=pc), [], DISPATCH, ('error', 'unsupported animation controller c3 PC')))
    out.append(U.Fixture('error-odd-c52b', U.with_host_writes(st, pc=0xc52b), [], DISPATCH, ('error', 'unaligned animation machine PC')))
    wait = U.with_host_writes(st, [(0x1008e4, 4, 0xc560), (0x107dea, 2, 0x2000)], pc=0xc560)
    out.append(U.Fixture('negative-107dea-byte', wait, [], DISPATCH, 'mismatch', cpp_state=U.flip_ram(wait, 0x107deb), external_status=status))
    out.append(U.Fixture('negative-node-byte-82', st, [], DISPATCH, 'mismatch', cpp_state=U.flip_ram(st, 0x100966), external_status=status))
    out.append(U.Fixture('negative-stop-pc', st, [], DISPATCH, 'mismatch', cpp_stop=0xc560, external_status=status))
    return out
