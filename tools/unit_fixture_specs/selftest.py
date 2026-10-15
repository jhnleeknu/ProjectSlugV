"""Self-test spec of tools/verify_animation_machine_unit_fixtures.py over ALREADY ROUTED code.

Positive fixtures (C++ == native Unicorn on the original ROM, native additionally == the D1 reference end state of the FH observer):
  H segments  frames 1..6 of three natural D1 seeds, frame-head entry (e4a/e74) to the controller stop c52a, FH's declared external queue.
  N passes    seed 0 frames 0..2 and frame 244 (the BIOS card request: card release), dispatcher 2ac2 to the next frame-head callback.
  nodes       seed 0 frame 1: native N pass advanced to the entry of nodes 0, 2, 3, 4; node to its RTS target 2ac2.
  declared host writes + register overrides on a captured node state.
Expected checked errors (state preserved): unrouted work-RAM probe PC 10fe00, undeclared wait (no releases), wait limit 0.
Negative checks (C++ input corrupted, the comparison must detect it): flipped RAM byte, flipped register, flipped PVC byte, changed bank, changed/short/extra queue.
"""
import verify_animation_machine_unit_fixtures as U

SEEDS = 3
HFRAMES = (1, 2, 3, 4, 5, 6)


def build():
    out = []
    cases = U.natural_cases(SEEDS)
    for c in cases:
        out += U.seed_h_fixtures(c, max(HFRAMES) + 1, upto=HFRAMES)
    out += U.seed_n_fixtures(cases[0], 245, upto=(0, 1, 2, 244))
    nodes = [U.seed_node_fixture(cases[0], 1, node=k) for k in (0, 2, 3, 4)]
    out += nodes
    # captured node state + declared host writes + register overrides (both sides get the same state)
    node = nodes[1]
    out.append(U.Fixture('hostwrite-node-47bfc', U.with_host_writes(node.state, [(0x10fff0, 4, 0xdeadbeef), (0x10fff6, 1, 0x5a)], regs={'d7': 0x12345678, 'a4': 0x108010}),
                         node.queue, node.stop, external_status=node.external_status, meta=dict(base=node.name)))
    # expected checked errors
    h = [f for f in out if f.name.startswith('h-seed') and f.meta['frame'] == 2][0]
    out.append(U.Fixture('error-unrouted-probe-10fe00', U.with_host_writes(h.state, pc=0x10fe00), [], 0xc52a, ('error', 'unsupported animation machine PC')))
    out.append(U.Fixture('error-undeclared-wait', h.state, h.queue, h.stop, ('error', 'undeclared wait PC'), releases=()))
    out.append(U.Fixture('error-wait-limit-0', h.state, h.queue, h.stop, ('error', 'declared wait limit'), wait_limit=0))
    out.append(U.Fixture('error-queue-empty', h.state, [], h.stop, ('error', 'external read queue empty')))
    # negative checks: the C++ input differs from the native input, the comparison must report it
    st = h.state
    pvc = bytearray(st['pvc'])
    pvc[0x100] ^= 1
    q = list(h.queue)
    out.append(U.Fixture('negative-ram-byte', st, h.queue, h.stop, 'mismatch', cpp_state=U.flip_ram(st, 0x10fff0), external_status=h.external_status))
    n0 = nodes[0]
    for reg in ('d7', 'a4'):
        out.append(U.Fixture('negative-register-' + reg, n0.state, n0.queue, n0.stop, 'mismatch', cpp_state=U.with_host_writes(n0.state, regs={reg: n0.state['regs'][reg] ^ 1})))
    out.append(U.Fixture('negative-bank', n0.state, n0.queue, n0.stop, 'mismatch',
                         cpp_state=dict(n0.state, bank=(n0.state['bank'][0] ^ 0x100000, n0.state['bank'][1], n0.state['bank'][2]))))
    out.append(U.Fixture('negative-pvc-byte', st, h.queue, h.stop, 'mismatch', cpp_state=dict(st, pvc=bytes(pvc)), external_status=h.external_status))
    out.append(U.Fixture('negative-queue-short', st, h.queue, h.stop, 'mismatch', cpp_queue=q[:-1], external_status=h.external_status))
    out.append(U.Fixture('negative-queue-extra', st, h.queue, h.stop, 'mismatch', cpp_queue=q + [(0x300000, 1, 0x5a)], external_status=h.external_status))
    out.append(U.Fixture('negative-queue-values', st, h.queue, h.stop, 'mismatch', cpp_queue=[(a, n, v ^ 0x1234 if a == 0x3c0006 else v ^ 0xff) for a, n, v in q],
                         external_status=h.external_status))
    out.append(U.Fixture('negative-stop-pc', st, h.queue, h.stop, 'mismatch', external_status=h.external_status, cpp_stop=0x2ac2))
    return out
