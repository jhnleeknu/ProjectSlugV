"""V1 native fixture spec of unit B1b (engine/src/animation_machine_objects_b1b.cpp): the deferred N22b part (154 block starts), the 3d8de chain
(9; the contract's "13" counts 4 more than its own start list) and the 3e250 28ae child (13) of the 3d32c object, and the N19b part (31) of the
stage event callbacks b1656 / b16d6 = 207 block starts.

Every fixture starts at an original PC inside natural node RAM (D1 natural seeds: 38 and 116 for the 3d32c object, 12 and 13 for the b16fc object),
runs the ORIGINAL ROM in Unicorn and the C++ machine to the same stop PC and compares RAM, D0-D7/A0-A7, PC, bank, PVC and ports.
Declared host writes (U.with_host_writes) and register overrides supply the typed world:
  exits      for every block start and every exit of the block (both branch sides, the call target, the RTS return pushed as a declared LONG,
             the fall-through) the spec searches seeded worlds (biased node bytes / registers, typed pointers and streams) until the original
             code reaches the exit as the block's OWN exit (probe budget = instructions of the block), then keeps THREE worlds per exit
             (alternating between the two natural base nodes).  A block that is only reachable through a flag set by its predecessor (3dac2)
             is started at the predecessors 3dab6 / 3dabe.
  table      3d8a0 with D0.W 0..8 (the nine BRA.W slots 3d8a8..3d8c8), and out-of-table D0.W (9, 10, 4000, 2001, ffff, 7fff, 8000, 8001).
  sweeps     boundary sweeps of the leaf blocks 3df04 (NEG.W / CMPI.W #4), 3df30, 3ddee, 3dd30 (all 10 LONG table slots), 3dd0e, 3dd1e, b1d92, b1da4,
             b1690, the table indices of b1670 / 3e29a / 3e2b6, and the D0 tests of 3d7ec 3d7f4 3d7fc 3da78 3da82 3d898 3dbe2.
  carry      the 8 C consumers (3d40a 3d478 3dbae 3dbca 3e2dc 3e2ec b16c2 b1cb4) are entered through a real producer: the ROM routine 3dd08
             (MOVE.B (A7)+,D0; LSR.B #1,D0; RTS; C = bit 0 of the pushed BYTE) with the consumer as the return LONG, for C = 0 and 1,
             and (best effort) through the natural producers 28ae 49fc6 288c b15e0 3dcf2 whose original C reaches the consumer.
  callbacks  whole callbacks as the dispatcher runs them (entry to the RTS return LONG or to JMP 2a00) over every routed callee; skipped
             when a callee of another unit is not routed yet, so a defect of this unit is never hidden.
  errors     expected checked errors with state preserved: Unknown C at the consumers, every internal even PC of the routed ranges,
             odd PCs, the boundaries 3d526 3d982 3dd42 3def2 3df1a 3e0aa 3e302, the TRAP #f b1c90 (reached from b1c82 with D0.W - 1 > 5 and
             directly) and 3d234 / 3da6c.
  negative   C++ input with one flipped RAM byte / register must be detected.
The native probe is only a search device; each kept fixture is verified again by the verifier (native must reach the stop).
"""
import random

import verify_animation_machine_unit_fixtures as U

STOP_RET = 0xff000             # RTS return target (declared LONG at A7) and the stop of every RET exit (fixed ROM filler, never routed or executed)
STREAM = 0x10fd00              # typed work RAM stream for 3defa / 3df04 / 3df1e
PROBE_INSN = 28              # a block is at most 17 instructions: the exit must be the block's own exit, never a later arrival
CONSUMER_INSN = 12          # 3dd08 (3 instructions) + the consumer block: the consumer's own exit, never a later arrival
REAL_INSN = 4000            # the natural producers (28ae 49fc6 288c b15e0 3dcf2) run many instructions before the consumer
ATTEMPTS = 160
VARIANTS = 3
N22_BASES = ((38, 2, 9), (116, 2, 21))
N19_BASES = ((12, 1, 6), (13, 1, 6))

# block start -> exits (stop PCs).  'RET' = the RTS return (stop STOP_RET), 'TABLE' = the BRA.W table jump.
EXITS = {
    0x3d3f0: (0x3e03e,),
    0x3d3fa: (0x28ae,),
    0x3d40a: (0x4972c,),
    0x3d414: (0x3d41a,),
    0x3d41a: (0x3d436,0x3d422,),
    0x3d422: (0x3de54,),
    0x3d426: (0x3dcf2,),
    0x3d42a: (0x3df30,),
    0x3d432: (0x3dbbe,),
    0x3d436: (0x49f96,),
    0x3d44a: (0x49f8c,),
    0x3d45a: (0x3af8,),
    0x3d46a: (0x3d470,),
    0x3d470: (0x3de54,),
    0x3d474: (0x3dcf2,),
    0x3d478: (0x3d48c,0x3d47c,),
    0x3d47c: (0x3d48c,0x3d486,),
    0x3d486: (0x3d48c,),
    0x3d48c: (0x3df30,),
    0x3d494: (0x3dbbe,),
    0x3d498: (0x3af8,),
    0x3d4a8: (0x49f96,),
    0x3d4c2: (0x49f8c,),
    0x3d4d2: (0x3d4e2,),
    0x3d4e2: (0x3de54,),
    0x3d4e6: (0x3dcf2,),
    0x3d4ea: (0x3d51a,0x3d4f4,),
    0x3d4f4: (0x4d4b4,),
    0x3d508: (0x3dbba,),
    0x3d51a: (0x3dbbe,),
    0x3d7e8: (0x3dde4,),
    0x3d7ec: (0x3d7fc,0x3d7f4,),
    0x3d7f4: (0x3d498,0x3d7fc,),
    0x3d7fc: (0x3d81e,0x3d804,),
    0x3d804: (0x3d812,0x3d80c,),
    0x3d80c: (0x3d812,),
    0x3d812: (0x3de54,),
    0x3d816: (0x3dcf2,),
    0x3d81a: (0x3dbbe,),
    0x3d81e: (0x3af8,),
    0x3d828: (0x3dcda,),
    0x3d836: (0x49f96,),
    0x3d856: (0x49f8c,),
    0x3d866: (0x496c2,),
    0x3d87a: (0x3d880,),
    0x3d880: (0x3de46,),
    0x3d884: (0x3dcf2,),
    0x3d888: (0x3dd0e,),
    0x3d88c: (0x4ae4a,),
    0x3d898: (0x3d8cc,0x3d8a0,),
    0x3d8a0: ('TABLE',),
    0x3d8a8: (0x3d8cc,),
    0x3d8ac: (0x3d8de,),
    0x3d8b0: (0x3d8de,),
    0x3d8b4: (0x3d8cc,),
    0x3d8b8: (0x3d8cc,),
    0x3d8bc: (0x3d8cc,),
    0x3d8c0: (0x3d8cc,),
    0x3d8c4: (0x3d8cc,),
    0x3d8c8: (0x3d8cc,),
    0x3d8cc: (0x3d8da,0x3d8d4,),
    0x3d8d4: (0x3d8da,),
    0x3d8da: (0x3dc40,),
    0x3d8de: (0x4ae4a,),
    0x3d8ea: (0x4ff96,),
    0x3d8f4: (0xd3d7c,),
    0x3d8fa: (0xd3d7c,),
    0x3d916: (0xd3d7c,),
    0x3d932: (0xd3d7c,),
    0x3d94e: (0x28ae,),
    0x3d974: (0x49214,),
    0x3d97e: (0x3db62,),
    0x3da72: (0x4d8d8,),
    0x3da78: (0x3daa4,0x3da7e,),
    0x3da7e: (0x3dde4,),
    0x3da82: (0x3da98,0x3da8a,),
    0x3da8a: (0x3dcda,),
    0x3da98: (0x3dcac,),
    0x3da9c: (0x3de54,),
    0x3daa0: (0x3daae,),
    0x3daa4: (0x3de46,),
    0x3daae: (0x3dcf2,),
    0x3dab2: (0x3dd0e,),
    0x3dab6: (0x3dac2,0x3dabe,),
    0x3dabe: (0x3dac2,),
    0x3dac2: (0x3dacc,0x3dac6,),
    0x3dac6: (0x3dacc,),
    0x3dacc: (0x3dc40,),
    0x3dad0: (0x4ae4a,),
    0x3dadc: (0x3dcda,),
    0x3dae4: (0x4ff96,),
    0x3daee: (0xd3d7c,),
    0x3daf4: (0xd3d7c,),
    0x3db10: (0xd3d7c,),
    0x3db2c: (0x28ae,),
    0x3db52: (0x49214,),
    0x3db5c: (0x2a00,),
    0x3db68: (0x3af8,),
    0x3db72: (0x8ebe,),
    0x3db80: (0x49f8c,),
    0x3db9c: (0x3dba2,),
    0x3dba2: (0x4be06,),
    0x3dba8: (0x49fc6,),
    0x3dbae: (0x3dbb8,0x3dbb2,),
    0x3dbb2: (0x2a00,),
    0x3dbb8: ('RET',),
    0x3dbbe: (0x3dd0e,),
    0x3dbc2: (0x3dd30,),
    0x3dbc6: (0x3dcac,),
    0x3dbca: (0x3dbd8,0x3dbce,),
    0x3dbce: (0x3dc24,),
    0x3dbd8: (0x4d7a6,),
    0x3dbe2: (0x3dbf2,0x3dbea,),
    0x3dbea: (0x3dbf2,),
    0x3dbf2: (0x4d734,),
    0x3dbfc: (0x3dc24,0x3dc04,),
    0x3dc04: (0x3dc24,0x3dc0e,),
    0x3dc0e: (0x3df30,),
    0x3dc16: (0x3af8,),
    0x3dc20: (0x3e0a8,),
    0x3dcac: (0x3dcc4,0x3dcbc,),
    0x3dcbc: (0x3dcc8,),
    0x3dcc4: (0x3dcc8,),
    0x3dcc8: (0x3dcd4,0x3dcd2,),
    0x3dcd2: (0x3dcd4,),
    0x3dcd4: (0x4d418,),
    0x3dcda: (0x4d8d8,),
    0x3dce2: (0x3dcec,0x3dcea,),
    0x3dcea: ('RET',),
    0x3dcec: (0x4d4b4,),
    0x3dd0e: (0x3dd1e,0x3dd18,),
    0x3dd18: (0x3dd1e,),
    0x3dd1e: (0x3dd2e,0x3dd28,),
    0x3dd28: (0x3dd2e,),
    0x3dd2e: ('RET',),
    0x3dd30: ('RET',),
    0x3dde4: (0x49be0,),
    0x3ddee: ('RET',),
    0x3de54: (0x43ea4,),
    0x3de64: (0x3de8e,0x3de8c,),
    0x3de8c: (0x3de8e,),
    0x3de8e: (0x3de9a,0x3de94,),
    0x3de94: (0x3de9a,),
    0x3de9a: (0x3deaa,0x3dea8,),
    0x3dea8: (0x3deaa,),
    0x3deaa: (0x3deb4,0x3deb0,),
    0x3deb0: (0x3deb4,),
    0x3deb4: (0x19a00,),
    0x3ded4: (0x3def0,0x3dee2,),
    0x3dee2: (0x3def0,),
    0x3def0: ('RET',),
    0x3defa: (0x3df22,0x3df04,),
    0x3df04: (0x3df1e,0x3df0e,),
    0x3df0e: ('RET',),
    0x3df1e: (0x3df22,),
    0x3df22: (0x8d34,),
    0x3df30: ('RET',),
    0x3e03e: (0x3de06,),
    0x3e042: (0x3dd30,),
    0x3e06e: (0x4b82e,),
    0x3e078: (0x4d98a,),
    0x3e0a6: ('RET',),
    0x3e0a8: ('RET',),
    0x3e250: (0x3af8,),
    0x3e268: (0x491c4,),
    0x3e280: (0x49290,),
    0x3e29a: (0x49f8c,),
    0x3e2b6: (0x8ebe,),
    0x3e2d0: (0x3e2d6,),
    0x3e2d6: (0x288c,),
    0x3e2dc: (0x3e2f2,0x3e2e0,),
    0x3e2e0: (0x43e34,),
    0x3e2e6: (0x49fc6,),
    0x3e2ec: (0x3e2f2,0x3e2f0,),
    0x3e2f0: ('RET',),
    0x3e2f2: (0x2a00,),
    0xb1656: (0xb1c82,),
    0xb165a: (0x2a00,),
    0xb1660: (0xb1c0e,),
    0xb1670: (0xb160a,),
    0xb1686: (0x49a84,),
    0xb1690: (0xb16aa,0xb16a4,),
    0xb16a4: (0xb16aa,),
    0xb16aa: (0xb16b0,),
    0xb16b0: (0xb15e0,),
    0xb16c2: (0xb19b2,0xb16c6,),
    0xb16c6: (0x43ea4,),
    0xb16cc: (0xb1b76,),
    0xb16d0: (0xb1dfa,),
    0xb16d4: ('RET',),
    0xb16d6: (0xb1c0e,),
    0xb16e6: (0xb186a,),
    0xb1c82: (0xb1c9e,0xb1c90,),
    0xb1c9e: (0xb1ca0,),
    0xb1ca0: (0x28ae,),
    0xb1cb4: (0xb1cc6,0xb1cb8,),
    0xb1cb8: (0x4970a,),
    0xb1cc2: (0xb1cc6,),
    0xb1cc6: (0xb1cf8,),
    0xb1cca: (0xb1cce,),
    0xb1cce: (0x49a84,),
    0xb1cdc: (0xb1cce,0xb1cec,),
    0xb1cec: (0xb1ca0,0xb1cf6,),
    0xb1cf6: ('RET',),
    0xb1d8c: (0x49a58,),
    0xb1d92: (0x443d2,),
    0xb1da4: ('RET',),
}
# instructions of every block (from the original decode): the probe budget of a block fixture, so that the exit is the block's OWN exit
ICOUNT = {
    0x3d3f0: 2, 0x3d3fa: 3, 0x3d40a: 2, 0x3d414: 1, 0x3d41a: 2, 0x3d422: 1, 0x3d426: 1, 0x3d42a: 2,
    0x3d432: 1, 0x3d436: 4, 0x3d44a: 3, 0x3d45a: 3, 0x3d46a: 1, 0x3d470: 1, 0x3d474: 1, 0x3d478: 1,
    0x3d47c: 2, 0x3d486: 1, 0x3d48c: 2, 0x3d494: 1, 0x3d498: 3, 0x3d4a8: 5, 0x3d4c2: 3, 0x3d4d2: 3,
    0x3d4e2: 1, 0x3d4e6: 1, 0x3d4ea: 2, 0x3d4f4: 4, 0x3d508: 3, 0x3d51a: 2, 0x3d7e8: 1, 0x3d7ec: 2,
    0x3d7f4: 2, 0x3d7fc: 2, 0x3d804: 2, 0x3d80c: 1, 0x3d812: 1, 0x3d816: 1, 0x3d81a: 1, 0x3d81e: 2,
    0x3d828: 3, 0x3d836: 6, 0x3d856: 3, 0x3d866: 3, 0x3d87a: 1, 0x3d880: 1, 0x3d884: 1, 0x3d888: 1,
    0x3d88c: 2, 0x3d898: 2, 0x3d8a0: 3, 0x3d8a8: 1, 0x3d8ac: 1, 0x3d8b0: 1, 0x3d8b4: 1, 0x3d8b8: 1,
    0x3d8bc: 1, 0x3d8c0: 1, 0x3d8c4: 1, 0x3d8c8: 1, 0x3d8cc: 2, 0x3d8d4: 1, 0x3d8da: 1, 0x3d8de: 2,
    0x3d8ea: 3, 0x3d8f4: 1, 0x3d8fa: 4, 0x3d916: 4, 0x3d932: 4, 0x3d94e: 6, 0x3d974: 3, 0x3d97e: 1,
    0x3da72: 1, 0x3da78: 2, 0x3da7e: 1, 0x3da82: 2, 0x3da8a: 3, 0x3da98: 1, 0x3da9c: 1, 0x3daa0: 1,
    0x3daa4: 2, 0x3daae: 1, 0x3dab2: 1, 0x3dab6: 2, 0x3dabe: 1, 0x3dac2: 1, 0x3dac6: 1, 0x3dacc: 1,
    0x3dad0: 2, 0x3dadc: 2, 0x3dae4: 3, 0x3daee: 1, 0x3daf4: 4, 0x3db10: 4, 0x3db2c: 6, 0x3db52: 3,
    0x3db5c: 1, 0x3db68: 2, 0x3db72: 3, 0x3db80: 5, 0x3db9c: 1, 0x3dba2: 1, 0x3dba8: 1, 0x3dbae: 1,
    0x3dbb2: 1, 0x3dbb8: 1, 0x3dbbe: 1, 0x3dbc2: 1, 0x3dbc6: 1, 0x3dbca: 1, 0x3dbce: 2, 0x3dbd8: 2,
    0x3dbe2: 2, 0x3dbea: 2, 0x3dbf2: 2, 0x3dbfc: 2, 0x3dc04: 2, 0x3dc0e: 2, 0x3dc16: 2, 0x3dc20: 1,
    0x3dcac: 4, 0x3dcbc: 2, 0x3dcc4: 1, 0x3dcc8: 2, 0x3dcd2: 1, 0x3dcd4: 1, 0x3dcda: 2, 0x3dce2: 3,
    0x3dcea: 1, 0x3dcec: 1, 0x3dd0e: 2, 0x3dd18: 1, 0x3dd1e: 2, 0x3dd28: 1, 0x3dd2e: 1, 0x3dd30: 6,
    0x3dde4: 2, 0x3ddee: 10, 0x3de54: 3, 0x3de64: 14, 0x3de8c: 1, 0x3de8e: 2, 0x3de94: 2, 0x3de9a: 5,
    0x3dea8: 1, 0x3deaa: 2, 0x3deb0: 2, 0x3deb4: 9, 0x3ded4: 4, 0x3dee2: 3, 0x3def0: 1, 0x3defa: 3,
    0x3df04: 3, 0x3df0e: 3, 0x3df1e: 2, 0x3df22: 3, 0x3df30: 6, 0x3e03e: 1, 0x3e042: 7, 0x3e06e: 2,
    0x3e078: 9, 0x3e0a6: 1, 0x3e0a8: 1, 0x3e250: 4, 0x3e268: 4, 0x3e280: 6, 0x3e29a: 7, 0x3e2b6: 6,
    0x3e2d0: 1, 0x3e2d6: 1, 0x3e2dc: 1, 0x3e2e0: 1, 0x3e2e6: 1, 0x3e2ec: 1, 0x3e2f0: 1, 0x3e2f2: 3,
    0xb1656: 1, 0xb165a: 1, 0xb1660: 3, 0xb1670: 6, 0xb1686: 2, 0xb1690: 6, 0xb16a4: 1, 0xb16aa: 1,
    0xb16b0: 3, 0xb16c2: 1, 0xb16c6: 1, 0xb16cc: 1, 0xb16d0: 1, 0xb16d4: 1, 0xb16d6: 3, 0xb16e6: 1,
    0xb1c82: 4, 0xb1c9e: 1, 0xb1ca0: 4, 0xb1cb4: 1, 0xb1cb8: 3, 0xb1cc2: 1, 0xb1cc6: 1, 0xb1cca: 1,
    0xb1cce: 3, 0xb1cdc: 5, 0xb1cec: 4, 0xb1cf6: 1, 0xb1d8c: 1, 0xb1d92: 4, 0xb1da4: 3,
}
RANGES = ((0x3d3f0, 0x3d526), (0x3d7e8, 0x3d982), (0x3da72, 0x3db62), (0x3db68, 0x3dbba), (0x3dbbe, 0x3dc24), (0x3dcac, 0x3dcf2), (0x3dd0e, 0x3dd42),
          (0x3dde4, 0x3de06), (0x3de54, 0x3def2), (0x3defa, 0x3df1a), (0x3df1e, 0x3df44), (0x3e03e, 0x3e0aa), (0x3e250, 0x3e302),
          (0xb1656, 0xb16ea), (0xb1c82, 0xb1c90), (0xb1c9e, 0xb1cf8), (0xb1d8c, 0xb1dae))
CONSUMERS = (0x3d40a, 0x3d478, 0x3dbae, 0x3dbca, 0x3e2dc, 0x3e2ec, 0xb16c2, 0xb1cb4)
PRE_POP = {0x3dce2: ((1,),), 0x3ded4: ((4,),), 0x3de64: ((4,),), 0xb1cca: ((2,), (2,)), 0xb1cdc: ((4,), (4,), (4,))}
# blocks entered through their predecessor (the flag of the predecessor is the only source of Z)
VIA = {0x3dac2: (0x3dab6, 0x3dabe)}
# node bytes the unit reads (A6 relative); every other node byte (links, parent LONG c, ...) stays natural
NODE_OFFS = (0x14, 0x15, 0x19, 0x1a, 0x1b, 0x1c, 0x1e, 0x1f, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x42, 0x43,
             0x44, 0x45, 0x46, 0x47, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5e, 0x61, 0x62, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x78, 0x79, 0x7a, 0x7b, 0x84, 0x85, 0x86,
             0x87, 0x88, 0x89, 0x8e, 0x8f, 0x92, 0x93, 0x96, 0x97, 0x9a, 0x9b, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa4, 0xa5, 0xa6, 0xac, 0xb0, 0xb3)
BYTE_POOL = (0, 0, 0, 0, 1, 2, 3, 4, 0x10, 0x12, 0x40, 0x80, 0xff, 0xff)
REG_POOL = (0, 1, 2, 3, 4, 5, 8, 9, 0x12, 0x1e, 0x20, 0x80, 0xff, 0x100, 0x980, 0x7fff, 0x8000, 0xfffb, 0xfffc, 0xfffd, 0xfffe, 0xffff, 0xffffffff, 0x7fffffff, 0x80000000)
STREAM_BLOCKS = (0x3defa, 0x3df04, 0x3df0e, 0x3df1e, 0x3df22)
STREAM_WORDS = (0, 1, 2, 4, 6, 0xfffe, 0xfffc, 0xfffd, 0xffff, 0x7fff, 0x8000, 0x8001, 0x0100)


def rbyte(rng):
    return rng.choice(BYTE_POOL) if rng.random() < 0.8 else rng.randrange(256)


def rreg(rng):
    r = rng.random()
    if r < 0.8:
        return rng.choice(REG_POOL)
    if r < 0.9:
        return rng.choice(REG_POOL) ^ (1 << rng.randrange(32))
    return rng.getrandbits(32)


class Base(object):
    def __init__(self, case, frame, node):
        fx = U.seed_node_fixture(case, frame, node=node)
        U.require(fx is not None, ('no base node', case, frame, node))
        self.fx, self.state, self.case = fx, fx.state, case
        self.a6 = fx.state['regs']['a6']
        self.a5 = fx.state['regs']['a5']
        self.a7 = fx.state['regs']['a7']
        self.queue, self.status = fx.queue, fx.external_status


class World(object):
    """Declared writes / registers / stack of one attempt."""
    def __init__(self, base):
        self.base, self.writes, self.regs, self.pc, self.carry = base, [], {}, None, 0

    def put(self, addr, size, value):
        self.writes.append((addr, size, value & ((1 << (8 * size)) - 1)))


def make_world(base, pc, rng, natural=False):
    """Typed random world for a start PC: biased node bytes, registers, valid pointers, work RAM stream."""
    w = World(base)
    a6 = base.a6
    for r in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'):
        w.regs[r] = rreg(rng)
    w.regs['a0'] = a6 + 0x100
    w.regs['a1'] = 0x3def2
    w.regs['a2'] = a6 + 0x140
    if not natural:
        for off in NODE_OFFS:
            w.put(a6 + off, 1, rbyte(rng))
        w.put(base.a5 + 0x53bc, 4, rreg(rng))
        w.put(base.a5 + 0x53a2, 4, rreg(rng))
    # work RAM stream (3defa / 3df04 / 3df1e / 3df22): words of a typed pool, LONG 80(A6) and A0 point into it
    if pc in STREAM_BLOCKS:
        for i in range(0, 0x80, 2):
            w.put(STREAM + i, 2, rng.choice(STREAM_WORDS))
    if pc in (0x3defa,):
        w.put(a6 + 0x80, 4, STREAM + 0x40)
    if pc in (0x3df04, 0x3df0e, 0x3df1e, 0x3df22):
        w.regs['a0'] = STREAM + 0x42
    # pre-popped stack items (A7 points at them); the RET exits push STOP_RET afterwards
    return w


def stack_items(w, pc, rng):
    items = PRE_POP.get(pc)
    if not items:
        return []
    out = []
    for (size,) in items:
        out.append((size, rng.choice(REG_POOL) if size == 4 else rng.randrange(1 << (8 * size))))
    return out


def realize(w, pc, exit_pc, rng, name):
    """World -> (state, stop).  Writes the stack items and, for RET, the return LONG; returns (fixture state, stop PC)."""
    base = w.base
    a7 = base.a7
    writes = list(w.writes)
    regs = dict(w.regs)
    if pc in PRE_POP:
        addr = a7
        for size, value in stack_items(w, pc, rng):
            writes.append((addr, size, value))
            addr += 2 if size == 1 else size
    if exit_pc == 'RET':
        writes.append((a7, 4, STOP_RET))
        stop = STOP_RET
    else:
        stop = exit_pc
    return U.with_host_writes(base.state, writes, regs=regs, pc=pc), stop


def probe(state, queue, status, stop, insn=PROBE_INSN):
    r = U.native().run(state, queue, stop, external_status=status, max_insn=insn)
    return bool(r['ok'])


def search(base, pc, exit_pc, seed, start=None, build=None, insn=PROBE_INSN, attempts=ATTEMPTS, natural_first=False):
    """Seeded worlds until the ORIGINAL code reaches exit_pc from start (default pc); -> (state, stop, attempt) or None."""
    start = pc if start is None else start
    for attempt in range(attempts):
        rng = random.Random((seed << 20) ^ (pc << 4) ^ attempt)
        w = make_world(base, start, rng, natural=(attempt == 0 and natural_first) or attempt == attempts - 1)
        if build is not None:
            build(w, rng, attempt)
        state, stop = realize(w, start, exit_pc, rng, 'x')
        if probe(state, base.queue, base.status, stop, insn):
            return state, stop, attempt
    return None


def block_fixtures(bases, unreached):
    out = []
    for pc in sorted(EXITS):
        if pc in CONSUMERS:
            continue                                  # entered through a real producer (consumer_fixtures)
        starts = VIA.get(pc, (pc,))
        for exit_pc in EXITS[pc][0:]:
            if exit_pc == 'TABLE':
                continue
            for start in starts:
                for k in range(VARIANTS):
                    base = bases[pc >= 0xb0000][k % len(bases[pc >= 0xb0000])]
                    seed = (k + 1) * 1009 + base.case
                    # exits of a VIA block are those of the block itself; the budget is the instructions of the start block (+ the block) + the stop fetch
                    insn = ICOUNT[start] + ((ICOUNT[pc] + 2) if start != pc else 0) + 1
                    r = search(base, pc, exit_pc, seed, start=start, insn=insn)
                    if r is None:
                        unreached.append((pc, exit_pc, start, base.case))
                        continue
                    state, stop, attempt = r
                    name = 'b1b-%x%s>%s-c%d-v%d' % (start, '' if start == pc else '-via-%x' % pc, 'ret' if exit_pc == 'RET' else '%x' % exit_pc, base.case, k)
                    out.append(U.Fixture(name, state, base.queue, stop, external_status=base.status,
                                         meta=dict(pc=pc, start=start, exit=exit_pc if exit_pc == 'RET' else hex(exit_pc), case=base.case, attempt=attempt)))
    return out


def sweep_fixtures(bases):
    """Boundary sweeps of the small leaf blocks (the native probe keeps only worlds in which the original code reaches the exit)."""
    out = []
    plan = []
    # 3df04: NEG.W D1; CMPI.W #4,D1; BCC.W 3df1e
    for d1 in (0xffff, 0xfffe, 0xfffd, 0xfffc, 0xfffb, 0x0001, 0x0004, 0x8000, 0x0000):
        neg = (0x10000 - d1) & 0xffff
        plan.append((0x3df04, 0x3df1e if neg >= 4 else 0x3df0e, dict(regs=dict(d1=0xabcd0000 | d1, a0=STREAM + 0x42), writes=[]), 'd1-%04x' % d1))
    # 3df30: D0.W & fffe | 88.W & 1 -> 88.W
    for d0, w88 in ((0, 0), (1, 1), (0xffff, 2), (0xabcd1234, 3), (0x12345678, 0x0100), (0x1234fffe, 0xff01)):
        plan.append((0x3df30, 'RET', dict(regs=dict(d0=d0, d1=0x11110000 | w88), writes=[('a6', 0x88, 2, w88)]), 'd0-%x-w88-%x' % (d0, w88)))
    # 3ddee: (A0) swapped, AND.B 9f(A6), OR.B into 9e(A6)
    for b9f, b9e, ptr in ((0x00, 0x00, 0x11223344), (0x0f, 0xa0, 0x11223344), (0xf0, 0x05, 0x8899aabb), (0xff, 0x00, 0x0000ffff), (0x55, 0xaa, 0xfedcba98), (0x80, 0x01, 0xffff0001)):
        plan.append((0x3ddee, 'RET', dict(regs={}, writes=[('a6', 0x9f, 1, b9f), ('a6', 0x9e, 1, b9e), ('a0', 0, 4, ptr)]), 'f-%02x-%02x-%08x' % (b9f, b9e, ptr)))
    # 3dd30: LONG table index 0..9
    for idx in range(10):
        plan.append((0x3dd30, 'RET', dict(regs={'d0': 0xffff0000 | idx}, writes=[('a6', 0xa1, 1, idx)]), 'idx-%d' % idx))
    # 3dd0e: bits 0/1 of 9a
    for v in (0, 1, 2, 3):
        plan.append((0x3dd0e, 0x3dd1e if v & 1 == 0 else 0x3dd18, dict(regs={}, writes=[('a6', 0x9a, 1, v)]), 'v%d' % v))
        plan.append((0x3dd1e, 0x3dd2e if v & 2 == 0 else 0x3dd28, dict(regs={}, writes=[('a6', 0x9a, 1, v)]), 'v%d' % v))
    # b1d92 / b1da4: D0.W & ff -> D1.W, D0 = 40000; LONG 36 += D0, LONG 3a += D1
    for d0 in (0x00, 0x7f, 0x80, 0xff, 0x1ff, 0xabcd1280, 0xfffffff0):
        plan.append((0xb1d92, 0x443d2, dict(regs=dict(d0=d0, d1=0x55550000), writes=[]), 'd0-%x' % d0))
    for d0, d1, l36, l3a in ((0x40000, 0x80, 0, 0), (0x40000, 0xff, 0xfffc0000, 0x7fffffff), (0x1234, 0xffffffff, 0x80000000, 1), (0, 0, 5, 6)):
        plan.append((0xb1da4, 'RET', dict(regs=dict(d0=d0, d1=d1), writes=[('a6', 0x36, 4, l36), ('a6', 0x3a, 4, l3a)]), 'v-%x-%x-%x-%x' % (d0, d1, l36, l3a)))
    # b1690: D0.W + 7a.W - f0 -> EXT.L, LSL.L #8 -> LONG 36, BMI
    for d0, w7a in ((0xf0, 0), (0xef, 0), (0x7fff, 0x7fff), (0x0100, 0x0000), (0xffffffff, 0xffff), (0x12340070, 0x0080), (0x00000100, 0x007f), (0x00000100, 0x0080)):
        plan.append((0xb1690, 0xb16aa if (((d0 + w7a - 0xf0) & 0xffff) << 8) & 0x80000000 or (((d0 + w7a - 0xf0) & 0xffff) & 0x8000) else 0xb16a4,
                     dict(regs=dict(d0=d0), writes=[('a6', 0x7a, 2, w7a)]), 'd0-%x-w7a-%x' % (d0, w7a)))
    # b1670: LONG table b15c0[w8e]; 3e29a / 3e2b6: LONG 3fc76 / WORD 3fc6e tables indexed by w86
    for w8e in (0, 1, 2, 3, 4, 7, 0x2001, 0x7fff):
        plan.append((0xb1670, 0xb160a, dict(regs={}, writes=[('a6', 0x8e, 2, w8e)]), 'w8e-%x' % w8e))
    for w86 in (0, 1, 2, 3, 4, 0xff):
        plan.append((0x3e29a, 0x49f8c, dict(regs=dict(d0=0x12340000), writes=[('a6', 0x86, 2, w86)]), 'w86-%x' % w86))
        plan.append((0x3e2b6, 0x8ebe, dict(regs=dict(d0=0x12340000), writes=[('a6', 0x86, 2, w86)]), 'w86-%x' % w86))
    # register tests on D0 (BTST #1 / #5 / #7, TST.B + BMI, CMPI.W #9, CMPI.B #12)
    for d0 in (0x00, 0x02, 0x20, 0x80, 0x22, 0xa2, 0xdd, 0xffff, 0x12345602):
        plan.append((0x3d7ec, 0x3d7f4 if d0 & 2 else 0x3d7fc, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
        plan.append((0x3d7f4, 0x3d498 if d0 & 0x20 else 0x3d7fc, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
        plan.append((0x3d7fc, 0x3d81e if d0 & 0x80 else 0x3d804, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
        plan.append((0x3da82, 0x3da8a if d0 & 0x20 else 0x3da98, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
        plan.append((0x3da78, 0x3daa4 if d0 & 0x80 else 0x3da7e, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
    for d0 in (0, 8, 9, 10, 0xffff, 0x10008, 0x10009, 0x8000, 0xabcd0003):
        plan.append((0x3d898, 0x3d8cc if (d0 & 0xffff) >= 9 else 0x3d8a0, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
    for d0 in (0x11, 0x12, 0x13, 0x112, 0xff12, 0x00, 0xffffff12):
        plan.append((0x3dbe2, 0x3dbea if (d0 & 0xff) == 0x12 else 0x3dbf2, dict(regs=dict(d0=d0), writes=[]), 'd0-%x' % d0))
    for pc, exit_pc, spec, label in plan:
        for k, base in enumerate(bases[0] if pc < 0xb0000 else bases[1]):
            if k == 1 and pc in (0x3dd30, 0xb1d92, 0xb1da4, 0xb1690, 0xb1670, 0x3e29a, 0x3e2b6, 0x3d7ec, 0x3d7f4, 0x3d7fc, 0x3da82, 0x3da78, 0x3d898, 0x3dbe2):
                continue
            w = make_world(base, pc, random.Random(pc + k), natural=True)
            w.regs.update(spec['regs'])
            for who, off, size, value in spec['writes']:
                anchor = base.a6 if who == 'a6' else w.regs['a0']
                w.put(anchor + off, size, value)
            rng = random.Random(7)
            state, stop = realize(w, pc, exit_pc, rng, 'x')
            if not probe(state, base.queue, base.status, stop):
                continue
            out.append(U.Fixture('b1b-sweep-%x-%s>%s-c%d' % (pc, label, 'ret' if exit_pc == 'RET' else '%x' % exit_pc, base.case), state, base.queue, stop,
                                 external_status=base.status, meta=dict(pc=pc, sweep=label)))
    return out


def table_fixtures(bases):
    out = []
    for k, base in enumerate(bases[0]):
        for d0, label in ((0, 'slot0'), (1, 'slot1'), (2, 'slot2'), (3, 'slot3'), (4, 'slot4'), (5, 'slot5'), (6, 'slot6'), (7, 'slot7'), (8, 'slot8'),
                          (9, 'x9'), (10, 'x10'), (0x4000, 'x4000'), (0x2001, 'x2001'), (0xffff, 'xffff'), (0x7fff, 'x7fff'), (0x8000, 'x8000'),
                          (0x8001, 'x8001')):
            if k == 1 and not label.startswith('x'):
                continue
            wide = d0 | 0xabcd0000
            # D0.W * 4 wraps in 16 bits and the displacement is sign extended
            w16 = (d0 * 4) & 0xffff
            target = (0x3d8a8 + (w16 - 0x10000 if w16 & 0x8000 else w16)) & 0xffffff
            st = U.with_host_writes(base.state, [], regs={'d0': wide}, pc=0x3d8a0)
            out.append(U.Fixture('b1b-3d8a0-table-%s-c%d' % (label, base.case), st, base.queue, target, external_status=base.status,
                                 meta=dict(pc=0x3d8a0, d0=d0, target=hex(target))))
    return out


def consumer_fixtures(bases, unreached):
    """Consumers entered through the real producer 3dd08 (C = bit 0 of the pushed BYTE) for C = 0 and 1."""
    out = []
    for pc in CONSUMERS:
        exits = EXITS[pc]
        for k, base in enumerate(bases[pc >= 0xb0000]):
            for flag in (0, 1):
                # C = 0 -> BCC taken / SCC true; the exit that corresponds is searched by probing both
                for exit_pc in exits:
                    def build(w, rng, attempt, flag=flag, base=base, pc=pc):
                        w.put(base.a7 - 8, 1, flag | (0x80 if rng.random() < 0.5 else 0))   # BYTE at (A7)
                        w.put(base.a7 - 6, 4, pc)                                           # return LONG = consumer
                        w.regs['a7'] = base.a7 - 8
                    r = search(base, pc, exit_pc, 77 + 13 * k + 5 * flag, start=0x3dd08, build=build, insn=CONSUMER_INSN)
                    if r is None:
                        continue
                    state, stop, attempt = r
                    out.append(U.Fixture('b1b-%x-carry%d>%s-c%d' % (pc, flag, 'ret' if exit_pc == 'RET' else '%x' % exit_pc, base.case), state, base.queue, stop,
                                         external_status=base.status, meta=dict(pc=pc, producer='3dd08', flag=flag, attempt=attempt)))
    return out


def real_producer_fixtures(bases):
    """Best effort: the natural producers 28ae 49fc6 288c b15e0 3dcf2 with the consumer as the return LONG."""
    out = []
    plan = (
        (0x3d40a, 0x28ae, dict(a0=0x3e250, d0=0xa)),
        (0xb1cb4, 0x28ae, dict(a0=0xb1660, d0=0x14)),
        (0x3dbae, 0x49fc6, {}),
        (0x3e2ec, 0x49fc6, {}),
        (0x3e2dc, 0x288c, {}),
        (0xb16c2, 0xb15e0, {}),
        (0x3d478, 0x3dcf2, {}),
    )
    for pc, producer, regs in plan:
        for k, base in enumerate(bases[pc >= 0xb0000]):
            for exit_pc in EXITS[pc]:
                def build(w, rng, attempt, base=base, pc=pc, regs=regs):
                    w.put(base.a7 - 4, 4, pc)
                    w.regs['a7'] = base.a7 - 4
                    for r, v in regs.items():
                        w.regs[r] = v
                r = search(base, pc, exit_pc, 31 + k, start=producer, build=build, insn=REAL_INSN, attempts=24, natural_first=True)
                if r is None:
                    continue
                state, stop, attempt = r
                out.append(U.Fixture('b1b-%x-real-%x>%s-c%d' % (pc, producer, 'ret' if exit_pc == 'RET' else '%x' % exit_pc, base.case), state, base.queue, stop,
                                     external_status=base.status, meta=dict(pc=pc, producer=hex(producer), attempt=attempt)))
    return out


_HARNESS = [None]


def cpp_harness():
    """A C++ harness for the search only (the verifier owns its own); the object cache makes the build a no-op."""
    if _HARNESS[0] is None:
        build_info = U.build_harness(2)
        _HARNESS[0] = U.Harness(build_info['exe'], U.program_resources(), U.BUILD / 'b1b_spec_probe.stderr')
    return _HARNESS[0]


def cpp_gap(state, queue, status, stop):
    """True when the C++ machine stops at a PC that no unit routes yet (a coverage gap of another unit, not a defect of this one)."""
    fx = U.Fixture('probe', state, queue, stop, external_status=status)
    got = U.cpp_call(cpp_harness(), fx)
    return (not got['ok']) and 'unsupported animation' in got['error']


# installed / table callbacks run to the dispatcher RTS (the return LONG pushed at A7) or to the final JMP 2a00
CALLBACKS = {0: (0x3d3f0, 0x3d41a, 0x3d470, 0x3d4e2, 0x3d7e8, 0x3d880, 0x3da72, 0x3dad0, 0x3d8de, 0x3dba2, 0x3db68, 0x3e250, 0x3e2d6),
             1: (0xb1656, 0xb16d6, 0xb1660, 0xb16b0, 0xb1d8c)}


def callback_fixtures(bases):
    """Whole callbacks as the dispatcher runs them: from the entry to the RTS (STOP_RET) or to JMP 2a00, over every routed callee; skipped when a callee
    of another unit is not routed yet (cpp_gap) so that a defect of this unit is never hidden."""
    out = []
    for side in (0, 1):
        for pc in CALLBACKS[side]:
            for k, base in enumerate(bases[side]):
                for stop_kind in ('RET', 0x2a00):
                    r = search(base, pc, stop_kind, 501 + 7 * k, insn=6000, attempts=14, natural_first=True)
                    if r is None:
                        continue
                    state, stop, attempt = r
                    if cpp_gap(state, base.queue, base.status, stop):
                        continue
                    out.append(U.Fixture('b1b-callback-%x>%s-c%d' % (pc, 'ret' if stop_kind == 'RET' else '%x' % stop_kind, base.case), state, base.queue, stop,
                                         external_status=base.status, meta=dict(pc=pc, callback=True, attempt=attempt)))
    return out


def error_fixtures(bases):
    out = []
    b = bases[0][0]
    starts = set(EXITS)
    # Unknown C at every consumer
    for pc in CONSUMERS:
        base = bases[pc >= 0xb0000][0]
        st = U.with_host_writes(base.state, [], pc=pc)
        out.append(U.Fixture('b1b-error-unknown-carry-%x' % pc, st, base.queue, 0x10fe40, ('error', 'objects b1b caller requires known carry'), external_status=base.status))
    # internal even PCs
    for lo, hi in RANGES:
        base = bases[lo >= 0xb0000][0]
        for pc in range(lo, hi, 2):
            if pc in starts:
                continue
            st = U.with_host_writes(base.state, [], pc=pc)
            out.append(U.Fixture('b1b-error-internal-%x' % pc, st, base.queue, 0x10fe40, ('error', 'unsupported animation objects b1b PC'), external_status=base.status))
    # odd PCs at the range ends
    for lo, hi in RANGES:
        base = bases[lo >= 0xb0000][0]
        for pc in (lo + 1, hi - 1):
            st = U.with_host_writes(base.state, [], pc=pc)
            out.append(U.Fixture('b1b-error-odd-%x' % pc, st, base.queue, 0x10fe40, ('error', 'unaligned animation machine PC'), external_status=base.status))
    # boundaries without an executor (and the TRAP #f b1c90)
    for pc in (0x3d526, 0x3d982, 0x3dd42, 0x3def2, 0x3df1a, 0x3e0aa, 0x3e302, 0xb1c90, 0xb1c92, 0xb1c9c, 0x3d234, 0x3da6c):
        base = bases[pc >= 0xb0000][0]
        if any(lo <= pc < hi for lo, hi in RANGES):
            continue
        st = U.with_host_writes(base.state, [], pc=pc)
        out.append(U.Fixture('b1b-error-boundary-%x' % pc, st, base.queue, 0x10fe40, ('error', 'unsupported animation machine PC'), external_status=base.status))
    # b1c82: D0.W - 1 > 5 falls into the TRAP #f (error), 1..6 passes
    base = bases[1][0]
    for w78, label in ((0, 'zero'), (7, 'seven'), (0x100, 'x100'), (0xffff, 'ffff')):
        st = U.with_host_writes(base.state, [(base.a6 + 0x78, 2, w78), (base.a7, 4, STOP_RET)], pc=0xb1c82)
        out.append(U.Fixture('b1b-error-trap-b1c82-%s' % label, st, base.queue, 0x10fe40, ('error', 'unsupported animation machine PC'), external_status=base.status))
    for w78 in range(1, 7):
        st = U.with_host_writes(base.state, [(base.a6 + 0x78, 2, w78), (base.a7, 4, STOP_RET)], pc=0xb1c82)
        out.append(U.Fixture('b1b-b1c82-w78-%d' % w78, st, base.queue, 0xb1ca0, external_status=base.status))
    return out


def negative_fixtures(positives):
    """The comparison must report a corrupted C++ input (one RAM byte / one register)."""
    out = []
    picks = [f for f in positives if f.name.startswith(('b1b-3dcac>', 'b1b-3de64>', 'b1b-b1cdc>', 'b1b-3d8a0-table-slot1', 'b1b-b1690>'))][:6]
    for f in picks:
        out.append(U.Fixture('negative-ram-' + f.name, f.state, f.queue, f.stop, 'mismatch', cpp_state=U.flip_ram(f.state, f.state['regs']['a6'] + 0x84),
                             external_status=f.external_status))
        out.append(U.Fixture('negative-reg-' + f.name, f.state, f.queue, f.stop, 'mismatch',
                             cpp_state=U.with_host_writes(f.state, [], regs={'d3': f.state['regs']['d3'] ^ 1}), external_status=f.external_status))
    return out


def build():
    bases = ([Base(*a) for a in N22_BASES], [Base(*a) for a in N19_BASES])
    unreached = []
    out = block_fixtures(bases, unreached)
    out += table_fixtures(bases)
    out += sweep_fixtures(bases)
    out += consumer_fixtures(bases, unreached)
    out += real_producer_fixtures(bases)
    out += callback_fixtures(bases)
    positives = list(out)
    out += error_fixtures(bases)
    out += negative_fixtures(positives)
    names = [f.name for f in out]
    U.require(len(set(names)) == len(names), 'duplicate fixture names')
    # every block start must be covered by at least one fixture starting at it (directly or through its predecessor)
    covered = set()
    for f in positives:
        covered.add(f.meta.get('pc'))
    for pc in sorted(EXITS):
        if pc not in covered and pc != 0x3d8a0:
            unreached.append((pc, 'start', None, None))
    if _HARNESS[0] is not None:
        _HARNESS[0].close()
        _HARNESS[0] = None
    if unreached:
        import sys
        for u in unreached:
            sys.stderr.write('UNREACHED %s\n' % (tuple(hex(x) if isinstance(x, int) else x for x in u),))
    return out
