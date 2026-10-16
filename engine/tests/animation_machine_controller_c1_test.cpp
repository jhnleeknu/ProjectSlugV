#include "ms5/animation_machine.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
// Controller C1 (116 block starts: the soft-dip / replay tests 30bc 30d4 314c, the BCD digit renderer 3670..3706, the credit text c49c / c4f8 and
// the demo / game gates c654 c66a c724 c7fc, the common tail c988..ca20, the credit helpers 4a88e 4a944 4a974 4a9ca and ca32) through
// run_animation_machine only.
// Inputs are declared fixtures in a synthetic world: zero work RAM with LONG 000ff000 = STOP at A7 = 10f000, controller node A6 = 1008e4,
// A5 = 108000, seeded BYTE / WORD / LONG node and BIOS fields, seeded D0-D7 / A0 / A1 (generated) and the incoming C tag. Synthetic typed
// physical bytes (not ROM data): the digit glyph table 370c.. (T[i] = i * 23 + 45) and the credit text pointer table c48c.. (LONGs 100100 +
// 10 * i). The ROWS table was produced from the ORIGINAL code bytes (Unicorn M68000 on the canonical BE ROM, native SR.C = 0 / 1 for the
// incoming C, the synthetic tables overlaid, tools/generate_animation_machine_controller_c1_test_table.py): per block start and seeded world
// the native run from the block start to the first other block start / PC outside the 12 ranges, one row per distinct successor, with the
// native C at the stop and the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, reads and status (C1 writes no port). The six consumers are checked
// per incoming C. Every other block must be independent of the incoming C; the FLOW blocks keep it (native C is checked), the seven C
// producers (30c8 30ce 30e0 30e6 3156 315c ca32) return the native C as a known state and every other block ends Unknown. The Z consumers
// 4a9d0 / 4a9da recompute the Z of the TST.B (A0) that ended 4a974 from BYTE (A0): rows use a non-zero byte (native SR.Z = 0 at entry), the zero
// side and the flag-source guard are key facts. The native-fixture verifier (tools/unit_fixture_specs/c1.py) additionally runs natural
// controller states of the D1 seeds with the declared game / demo states.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef ms5::AnimationMachineState State;
const std::uint32_t STOP=0xff000,SP=0x10f000,NODE=0x1008e4,A5=0x108000,OBJ0=0x10c800,OBJ1=0x10c400;
unsigned int calls=0;
struct World {const char* puts;std::uint32_t d[8];std::uint32_t a[8];};
struct Row {std::uint32_t pc;unsigned int world,c;std::uint32_t next;unsigned int cout;unsigned long long digest;};
struct Synthetic {std::uint32_t address;const char* bytes;};
// ---- generated tables (begin)
const World WORLDS[]={
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:40,100964:ff,10fd8b:01,100003:01,10fe80:01,100004:99,10fe00:02,10fdb1:a2,100965:01,10095c:388a,10095e:0100,100100:09090909",{0x8,0x8,0x1f,0x100,0x5,0xeac7f76,0xde096755,0x3},{0x10c800,0x3650,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,10fd8b:09,100012:03,104cd4:ff,10fe80:01,100004:00,10fe01:01,10fdb0:00,10fdb1:02,100965:ff,100966:00,100967:ff,10095c:0100,10095e:1000,100b30:0000270e,100100:10101010",{0x337f154e,0x6becae8c,0xf,0x100,0x3,0x5da7629,0x25b09865,0x1},{0x10fe00,0x100004,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:ff,100012:01,104cd4:ff,10fe80:00,100004:00,10fe00:02,10fe01:ff,100966:ff,100967:00,10095c:0004,100962:ffff,100b30:0000270e",{0x100,0x643bea2b,0x11110011,0x1,0x8001,0x7fff,0x3a68e2e,0x1},{0x10fdb0,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:01,100964:ff,10fd8b:09,100003:01,100012:03,10fe80:00,100004:ff,100005:05,10fe01:02,10fdb0:ff,10fdb1:02,100966:00,100967:eb,10095e:1a05,100962:0101",{0x10001,0x1191bbd,0x20,0x0,0x20003,0xa77ca132,0x7f,0x2},{0x10c800,0x10fdb0,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"100964:01,10fd8b:48,104cd4:01,10fe80:00,100004:00,100005:00,10fe00:01,10fdb0:fe,10fdb1:00,100967:ff,10095e:1a05,100962:0000,100100:12345678",{0x0,0x2fd368eb,0x2,0x0,0x5,0x7fff,0x1d3ab3e8,0x4000},{0x100101,0x3650,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"100003:01,104cd4:00,100004:99,100005:ff,10fdb1:00,100965:ff,100966:ff,100b30:0000270e,100100:10101010,10fd82:01,10fe80:01",{0x2e361b45,0x10001,0x0,0x0,0x2,0xffff,0xfffffff0,0x4000},{0x10fdb0,0x100004,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:02,100964:f9,10fd8b:ff,100004:00,100005:02,10fe00:99,10fdb0:02,10fdb1:02,100965:01,100966:ff,10095c:0100,10095e:1a05,100b30:00000000",{0x9694fbdf,0x1,0x1f,0xffffff00,0x10001,0xf5fbacc1,0x80000000,0x20000},{0x100101,0x3650,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:01,10fd8b:ff,100003:00,100012:02,104cd4:01,10fe80:01,100004:05,100005:9a,10fe00:02,10fdb0:ff,100966:ff,10095c:8000,100962:4c2e,100b30:0000270e,100100:00a0b0c0",{0x80,0x1234,0xa,0x100,0x0,0x80000000,0x7f,0x4001},{0x100004,0x10fdb0,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10f000:0010c800",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:02,100964:f9,10fd8b:ff,100004:00,100005:02,10fe00:99,10fdb0:02,10fdb1:02,100965:01,100966:ff,10095c:0100,10095e:1a05,100b30:00000000,10f000:0010c800",{0x9694fbdf,0x1,0x1f,0xffffff00,0x10001,0xf5fbacc1,0x80000000,0x20000},{0x100101,0x3650,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10f000:00100101",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10effe:00",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10effe}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10f000:00100100,10f004:0000",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10f000:0010c800",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10f000:1234",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x108000,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,10fd8b:09,100012:03,104cd4:ff,10fe80:01,100004:00,10fe01:01,10fdb0:00,10fdb1:02,100965:ff,100966:00,100967:ff,10095c:0100,10095e:1000,100b30:0000270e,100100:10101010,10f000:0001",{0x337f154e,0x6becae8c,0xf,0x100,0x3,0x5da7629,0x25b09865,0x1},{0x10fe00,0x100004,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,10fdb0:ff",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x10fdb0,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
 {"10fd8f:00,100964:ff,100003:01,100012:00,104cd4:00,100004:e7,100005:05,10fe00:99,10fe01:02,10fdb0:94,100965:01,100967:00,10095c:e12a,10095e:1008,100962:0a0a,100b30:00047af0,100100:01020304,100005:ff",{0x0,0x10000,0x9,0xffffff00,0x0,0x5,0xfffffff0,0x2},{0x100005,0x10c400,0x10c300,0x10c200,0x10c100,0x108000,0x1008e4,0x10f000}},
};
const Row ROWS[]={
 {0x30bc,0,0,0x30ce,0,0x9197a983ce01b85cULL},
 {0x30bc,3,0,0x30c8,0,0xfefda59f1329530fULL},
 {0x30c8,0,0,0xff000,1,0xe27626b92bac1ef9ULL},
 {0x30ce,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x30d4,0,0,0x30e6,0,0x9fc4841ad9577774ULL},
 {0x30d4,3,0,0x30e0,0,0xf0d0cb0807d393f7ULL},
 {0x30e0,0,0,0xff000,1,0xe27626b92bac1ef9ULL},
 {0x30e6,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x314c,0,0,0x315c,0,0x777617e1cc1fd981ULL},
 {0x314c,5,0,0x3156,0,0xe10ef252b48f800eULL},
 {0x3156,0,0,0xff000,1,0xe27626b92bac1ef9ULL},
 {0x315c,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x3670,0,0,0x367a,0,0xb018ebf945e4dba7ULL},
 {0x3670,1,0,0x3680,0,0xe57363146b70d278ULL},
 {0x367a,0,0,0x3682,1,0x1f4f95e7b2342d0fULL},
 {0x3680,0,0,0x3682,0,0xde257bae41f19a57ULL},
 {0x3682,0,0,0x3690,0,0x2a6664a8eeed8c10ULL},
 {0x3682,4,0,0x3688,0,0xb36de224122f6b4bULL},
 {0x3688,0,0,0x3698,0,0xef8f6cc5096e9e58ULL},
 {0x3688,7,0,0x3690,0,0xe8d4ba5770fb0a1dULL},
 {0x3690,0,0,0x36a2,0,0x4c94103388c99401ULL},
 {0x3698,0,0,0x369e,0,0x836e32da1d4f6c0eULL},
 {0x3698,3,0,0x36a2,0,0x65c94ca21c419d73ULL},
 {0x369e,0,0,0x36a2,0,0x6c300fa4c4a9b39fULL},
 {0x36a2,1,0,0x3650,0,0xe5c947a0d3349741ULL},
 {0x36b2,9,0,0x3670,0,0x9db01b013ead1b95ULL},
 {0x36b2,10,0,0x36b8,0,0x10b8ad7446d50cf5ULL},
 {0x36b8,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x36ba,0,0,0x3670,0,0xfaac9fcc525adafeULL},
 {0x36c0,0,0,0x36c2,0,0xfaa6d75894943e52ULL},
 {0x36c2,0,0,0x36cc,0,0x689fd4cb28f95721ULL},
 {0x36c2,1,0,0x36d2,0,0xb5b3d5c4111784baULL},
 {0x36cc,0,0,0x36d4,1,0xd7d67eb99548a889ULL},
 {0x36d2,0,0,0x36d4,0,0x96ac6480250615d1ULL},
 {0x36d4,0,0,0x36e2,0,0xa4b4792ae6627d72ULL},
 {0x36d4,4,0,0x36da,0,0xfd78cc146b1e7a9ULL},
 {0x36da,0,0,0x36e6,0,0x48973af637d07e56ULL},
 {0x36da,7,0,0x36e2,0,0xf078b34c4d37d3fULL},
 {0x36e2,0,0,0x36e6,0,0xc72e911e062f02a5ULL},
 {0x36e6,0,0,0x36fe,0,0x56c4158d43263d6eULL},
 {0x36e6,3,0,0x36ec,0,0xa8a245ac34583d7dULL},
 {0x36ec,1,0,0x3650,0,0x9e6cf93bf52e60ebULL},
 {0x36fc,11,0,0x36fe,0,0xcb627c102db81815ULL},
 {0x36fe,0,0,0x36c2,0,0x6fbb50c98fab704ULL},
 {0x36fe,7,0,0x3702,0,0xb0b2ee90cd72eb0dULL},
 {0x3702,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x3706,0,0,0x36c0,0,0x1dca0dd2754791eeULL},
 {0xc49c,0,0,0xca32,0,0xc5f07c2d19b91c1bULL},
 {0xc4a0,0,1,0xc4b6,0,0x1abcc10a554da480ULL},
 {0xc4a0,0,2,0xc4a4,1,0x950ad58c4cc295e2ULL},
 {0xc4a4,0,0,0x4a9ca,0,0xcb9f36eba5e65de0ULL},
 {0xc4aa,0,0,0xc4ba,0,0xfb0da940c163f5adULL},
 {0xc4b6,0,0,0xc4ba,0,0x8990b657eb20ebc6ULL},
 {0xc4ba,0,0,0x3918,0,0x1c8504c49a56bea7ULL},
 {0xc4f8,0,0,0x35f0,0,0x84cf620afcd438e1ULL},
 {0xc50e,0,0,0x3706,0,0x5009bc693afb8795ULL},
 {0xc526,12,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0xc654,0,0,0x2a28,0,0x1b0166b6fc51e5c7ULL},
 {0xc664,0,0,0xc66a,0,0xac15fc6bad516a5aULL},
 {0xc66a,0,0,0x289e,0,0xb0ee21232170991aULL},
 {0xc674,0,1,0xc686,0,0xb1947588b5964e46ULL},
 {0xc674,0,2,0xc678,1,0x7e730bcc551c6428ULL},
 {0xc678,0,0,0x314c,0,0x268d5d545d4a2520ULL},
 {0xc67e,0,1,0xc686,0,0xb1947588b5964e46ULL},
 {0xc67e,0,2,0xc682,1,0xdb1b3bd64284d62ULL},
 {0xc682,0,0,0xc724,0,0xada1b90dc9ffaf5fULL},
 {0xc724,0,0,0xc72e,0,0x41807f22dde07d15ULL},
 {0xc724,8,0,0xc74c,0,0x78f6bcf65d9efbbULL},
 {0xc72e,0,0,0xc736,0,0x6a9873ef8618f5dULL},
 {0xc72e,3,0,0xc988,0,0x4cd2072cb4858d7cULL},
 {0xc736,0,0,0xc49c,0,0x83f66d6f8ab3e7e8ULL},
 {0xc73a,0,0,0xc988,0,0xd88a6864c8d095edULL},
 {0xc73e,0,0,0xc748,0,0x3ce05a68b1696723ULL},
 {0xc73e,8,0,0xc74c,0,0x78f6bcf65d9efbbULL},
 {0xc748,0,0,0xc988,0,0xd88a6864c8d095edULL},
 {0xc7fc,0,0,0x289e,0,0x8a340f8aeb5dff4eULL},
 {0xc806,0,1,0xc80a,0,0x23f642a3f8f4ead0ULL},
 {0xc806,0,2,0xc988,1,0xd88a6864c8d095edULL},
 {0xc80a,0,0,0xc76a,0,0xf6f1f7f140c4d971ULL},
 {0xc988,0,0,0xc990,0,0xe6b742fbd4265505ULL},
 {0xc988,3,0,0xc9c2,0,0xd0f93df410c9a546ULL},
 {0xc990,0,0,0x30bc,0,0x70085e6874a4e022ULL},
 {0xc996,0,1,0xc9ac,0,0x6151c3e6518bc3a9ULL},
 {0xc996,0,2,0xc99a,1,0x52d87ce6c045874fULL},
 {0xc99a,0,0,0x4a88e,0,0x2cf01be0ee8142c1ULL},
 {0xc9ac,0,0,0xc9b4,0,0x6f7e9e7d5ce182c1ULL},
 {0xc9ac,3,0,0xc9c2,0,0xd0f93df410c9a546ULL},
 {0xc9b4,0,0,0x30d4,0,0x9ae153d1f7abf0b6ULL},
 {0xc9ba,0,1,0xc9c2,0,0xb6f7b5ab79cd0747ULL},
 {0xc9ba,0,2,0xc9be,1,0xdb9fd8684900b50bULL},
 {0xc9be,0,0,0xc4f8,0,0x7a64950190babe36ULL},
 {0xc9c2,0,0,0x4a944,0,0xaf67086e204198f6ULL},
 {0xc9ce,0,0,0xc9d6,0,0x20037f92e5bc1a73ULL},
 {0xc9ce,5,0,0xc9de,0,0xeab4cc7294352aeeULL},
 {0xc9d6,0,0,0xc9de,0,0x4e058c250811b9caULL},
 {0xc9de,0,0,0xc9ea,0,0xa8de5c8a8d0f99ecULL},
 {0xc9de,4,0,0xc9f6,0,0x11f4051499efbe23ULL},
 {0xc9ea,0,0,0xc9f0,0,0x5bfd258a5865afc0ULL},
 {0xc9ea,1,0,0xc9f2,0,0xc92d0fb5f4de6f48ULL},
 {0xc9f0,0,0,0xc9f2,0,0x6df3e33088f85a77ULL},
 {0xc9f2,0,0,0xc9f6,0,0x82f77c8a2797642aULL},
 {0xc9f6,0,0,0xc9fe,0,0x4e819491d09474bULL},
 {0xc9f6,2,0,0xca20,0,0x10c9d3dac7e72549ULL},
 {0xc9fe,0,0,0xca06,0,0x89049fff8652478aULL},
 {0xc9fe,3,0,0xca20,0,0xd6dfedaeed72714eULL},
 {0xca06,0,0,0xca18,0,0x1423a9cb7c0e3274ULL},
 {0xca06,3,0,0xca14,1,0xa97feb12de16c864ULL},
 {0xca14,0,0,0xca18,0,0xc3c64e7a22f1cc51ULL},
 {0xca18,0,0,0xca20,0,0xed920addd7a06ecULL},
 {0xca20,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0xca32,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x4a88e,0,0,0x4a896,0,0x3b0385c109c59808ULL},
 {0x4a88e,6,0,0x4a89e,0,0x2fc80ed7707eb664ULL},
 {0x4a896,0,0,0x4a8b0,0,0x9fca10bc71d7f96eULL},
 {0x4a89e,0,0,0x4a8b0,0,0x65abfa80d47bd33eULL},
 {0x4a89e,1,0,0x4a8ac,0,0xafc9979374856dbULL},
 {0x4a8ac,0,0,0x4a8b0,0,0xc04b053ae6863740ULL},
 {0x4a8b0,0,0,0x4a8ba,0,0xc3cae1429280c5c4ULL},
 {0x4a8b0,2,0,0x4a8cc,0,0xcf7253f5edc376dbULL},
 {0x4a8ba,0,0,0x4a8ce,0,0x8b6adee1193ccaf8ULL},
 {0x4a8c2,13,0,0x4a8ce,0,0x37faac43ba2de258ULL},
 {0x4a8cc,0,0,0x4a8ce,0,0x156a3956cb18e219ULL},
 {0x4a8ce,0,0,0x4a8da,0,0x38bc9651540c56d4ULL},
 {0x4a8ce,4,0,0x4a8de,0,0x95803b040945dfafULL},
 {0x4a8da,0,0,0x4a8de,0,0x8b8caf27c6a6f4ULL},
 {0x4a8de,0,0,0x3902,0,0xdcb325618fda0d08ULL},
 {0x4a8e6,14,0,0x36ba,0,0x5485b560ab28dee1ULL},
 {0x4a944,0,0,0x4a94c,0,0x4714cb92835e5dc5ULL},
 {0x4a944,6,0,0x4a954,0,0x110651e51a839021ULL},
 {0x4a94c,0,0,0x4a966,0,0xb0c7e7b09dd8525fULL},
 {0x4a954,0,0,0x4a966,0,0xddde73a7129199cfULL},
 {0x4a954,1,0,0x4a962,0,0x4b51028eb4a4da4eULL},
 {0x4a962,0,0,0x4a966,0,0x28797c14bf6c992dULL},
 {0x4a966,0,0,0x4a972,0,0xf2f98e84076410fbULL},
 {0x4a966,2,0,0x4a970,0,0xf6a9cad3033bc24dULL},
 {0x4a970,0,0,0x4a972,0,0xf2f98e84076410fbULL},
 {0x4a972,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x4a974,0,0,0x4a9b4,0,0xc3dd3ae9ddf700dULL},
 {0x4a974,6,0,0x4a982,0,0xbce0abe1007922eULL},
 {0x4a982,0,0,0xc00450,0,0xad7d4f520b410b26ULL},
 {0x4a992,15,0,0x4a9ae,0,0x4b6536c10f5abb9dULL},
 {0x4a992,16,0,0x4a9a4,0,0x1dd13d6b8e11440dULL},
 {0x4a9a4,0,0,0x4a9ae,0,0xce516bc738306337ULL},
 {0x4a9a4,8,0,0x4a9b0,0,0x2f85c8f5c24af8d5ULL},
 {0x4a9ae,0,0,0x4a9b0,0,0xeaf78d5dd4cc5ea9ULL},
 {0x4a9b0,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x4a9b4,0,0,0x4a9c4,0,0x69ff0abf20b7af31ULL},
 {0x4a9b4,2,0,0x4a9c6,0,0xaf55d3f33f3a9964ULL},
 {0x4a9c4,0,0,0x4a9c6,0,0x5c6873f178eb48fULL},
 {0x4a9c6,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
 {0x4a9ca,0,0,0x4a974,0,0x22517fe955d1a5f5ULL},
 {0x4a9d0,17,0,0x4a9d4,0,0xa9c2f9964e00b093ULL},
 {0x4a9d4,0,0,0x4a9d6,0,0x94214ff5a5194a92ULL},
 {0x4a9d6,0,0,0x4a974,0,0x9a9055b92af96774ULL},
 {0x4a9da,18,0,0x4a9de,0,0x48872d0617d2f12cULL},
 {0x4a9de,0,0,0x4a9e0,0,0x3b1981c476b76a94ULL},
 {0x4a9e0,0,0,0xff000,0,0xe27626b92bac1ef9ULL},
};
const Synthetic SYNTHETIC[]={
 {0x370c,"45688baed1f4173a5d80a3c6e90c2f527598bbde0124476a8db0d3f6193c5f82a5c8eb0e3154779abde00326496c8fb2d5f81b3e6184a7caed103356799cbfe205284b6e91b4d7fa1d406386a9ccef1235587b9e"},
 {0xc48c,"00100100001001100010012000100130"},
};
const std::uint32_t FLOW[]={0x30bc,0x30d4,0x3680,0x36b8,0x36ba,0x36d2,0x36fc,0x3706,0xc49c,0xc4a0,0xc4a4,0xc4b6,0xc654,0xc66a,0xc674,0xc678,0xc67e,0xc682,0xc736,0xc73a,0xc748,0xc7fc,0xc806,0xc80a,0xc990,0xc996,0xc9b4,0xc9ba,0xc9be,0xca20,0x4a896,0x4a8ac,0x4a8da,0x4a94c,0x4a962,0x4a972,0x4a9ae,0x4a9c4,0x4a9d0,0x4a9d4,0x4a9da,0x4a9de,0x4a9e0};
const std::uint32_t STARTS[]={0x30bc,0x30c8,0x30ce,0x30d4,0x30e0,0x30e6,0x314c,0x3156,0x315c,0x3670,0x367a,0x3680,0x3682,0x3688,0x3690,0x3698,0x369e,0x36a2,0x36b2,0x36b8,0x36ba,0x36c0,0x36c2,0x36cc,0x36d2,0x36d4,0x36da,0x36e2,0x36e6,0x36ec,0x36fc,0x36fe,0x3702,0x3706,0xc49c,0xc4a0,0xc4a4,0xc4aa,0xc4b6,0xc4ba,0xc4f8,0xc50e,0xc526,0xc654,0xc664,0xc66a,0xc674,0xc678,0xc67e,0xc682,0xc724,0xc72e,0xc736,0xc73a,0xc73e,0xc748,0xc7fc,0xc806,0xc80a,0xc988,0xc990,0xc996,0xc99a,0xc9ac,0xc9b4,0xc9ba,0xc9be,0xc9c2,0xc9ce,0xc9d6,0xc9de,0xc9ea,0xc9f0,0xc9f2,0xc9f6,0xc9fe,0xca06,0xca14,0xca18,0xca20,0xca32,0x4a88e,0x4a896,0x4a89e,0x4a8ac,0x4a8b0,0x4a8ba,0x4a8c2,0x4a8cc,0x4a8ce,0x4a8da,0x4a8de,0x4a8e6,0x4a944,0x4a94c,0x4a954,0x4a962,0x4a966,0x4a970,0x4a972,0x4a974,0x4a982,0x4a992,0x4a9a4,0x4a9ae,0x4a9b0,0x4a9b4,0x4a9c4,0x4a9c6,0x4a9ca,0x4a9d0,0x4a9d4,0x4a9d6,0x4a9da,0x4a9de,0x4a9e0};
// SBCD.B D2,D1 (D2 = 0) after SUBQ.B #8,D0: [X][BYTE] -> result << 1 | C, X = 1 (D0.B = 7) then X = 0 (D0.B = 8).
const unsigned short SBCD[512]={0x133,0x0,0x2,0x4,0x6,0x8,0xa,0xc,0xe,0x10,0x12,0x14,0x16,0x18,0x1a,0x1c,0x12,0x20,0x22,0x24,0x26,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x34,0x36,0x38,0x3a,0x3c,0x32,0x40,0x42,0x44,0x46,0x48,0x4a,0x4c,0x4e,0x50,0x52,0x54,0x56,0x58,0x5a,0x5c,0x52,0x60,0x62,0x64,0x66,0x68,0x6a,0x6c,0x6e,0x70,0x72,0x74,0x76,0x78,0x7a,0x7c,0x72,0x80,0x82,0x84,0x86,0x88,0x8a,0x8c,0x8e,0x90,0x92,0x94,0x96,0x98,0x9a,0x9c,0x92,0xa0,0xa2,0xa4,0xa6,0xa8,0xaa,0xac,0xae,0xb0,0xb2,0xb4,0xb6,0xb8,0xba,0xbc,0xb2,0xc0,0xc2,0xc4,0xc6,0xc8,0xca,0xcc,0xce,0xd0,0xd2,0xd4,0xd6,0xd8,0xda,0xdc,0xd2,0xe0,0xe2,0xe4,0xe6,0xe8,0xea,0xec,0xee,0xf0,0xf2,0xf4,0xf6,0xf8,0xfa,0xfc,0xf2,0x100,0x102,0x104,0x106,0x108,0x10a,0x10c,0x10e,0x110,0x112,0x114,0x116,0x118,0x11a,0x11c,0x112,0x120,0x122,0x124,0x126,0x128,0x12a,0x12c,0x12e,0x130,0x132,0x134,0x136,0x138,0x13a,0x13c,0x132,0x140,0x142,0x144,0x146,0x148,0x14a,0x14c,0x14e,0x150,0x152,0x154,0x156,0x158,0x15a,0x15c,0x152,0x160,0x162,0x164,0x166,0x168,0x16a,0x16c,0x16e,0x170,0x172,0x174,0x176,0x178,0x17a,0x17c,0x172,0x180,0x182,0x184,0x186,0x188,0x18a,0x18c,0x18e,0x190,0x192,0x194,0x196,0x198,0x19a,0x19c,0x192,0x1a0,0x1a2,0x1a4,0x1a6,0x1a8,0x1aa,0x1ac,0x1ae,0x1b0,0x1b2,0x1b4,0x1b6,0x1b8,0x1ba,0x1bc,0x1b2,0x1c0,0x1c2,0x1c4,0x1c6,0x1c8,0x1ca,0x1cc,0x1ce,0x1d0,0x1d2,0x1d4,0x1d6,0x1d8,0x1da,0x1dc,0x1d2,0x1e0,0x1e2,0x1e4,0x1e6,0x1e8,0x1ea,0x1ec,0x1ee,0x1f0,0x1f2,0x1f4,0x1f6,0x1f8,0x1fa,0x1fc,0x0,0x2,0x4,0x6,0x8,0xa,0xc,0xe,0x10,0x12,0x14,0x16,0x18,0x1a,0x1c,0x1e,0x20,0x22,0x24,0x26,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x34,0x36,0x38,0x3a,0x3c,0x3e,0x40,0x42,0x44,0x46,0x48,0x4a,0x4c,0x4e,0x50,0x52,0x54,0x56,0x58,0x5a,0x5c,0x5e,0x60,0x62,0x64,0x66,0x68,0x6a,0x6c,0x6e,0x70,0x72,0x74,0x76,0x78,0x7a,0x7c,0x7e,0x80,0x82,0x84,0x86,0x88,0x8a,0x8c,0x8e,0x90,0x92,0x94,0x96,0x98,0x9a,0x9c,0x9e,0xa0,0xa2,0xa4,0xa6,0xa8,0xaa,0xac,0xae,0xb0,0xb2,0xb4,0xb6,0xb8,0xba,0xbc,0xbe,0xc0,0xc2,0xc4,0xc6,0xc8,0xca,0xcc,0xce,0xd0,0xd2,0xd4,0xd6,0xd8,0xda,0xdc,0xde,0xe0,0xe2,0xe4,0xe6,0xe8,0xea,0xec,0xee,0xf0,0xf2,0xf4,0xf6,0xf8,0xfa,0xfc,0xfe,0x100,0x102,0x104,0x106,0x108,0x10a,0x10c,0x10e,0x110,0x112,0x114,0x116,0x118,0x11a,0x11c,0x11e,0x120,0x122,0x124,0x126,0x128,0x12a,0x12c,0x12e,0x130,0x132,0x134,0x136,0x138,0x13a,0x13c,0x13e,0x140,0x142,0x144,0x146,0x148,0x14a,0x14c,0x14e,0x150,0x152,0x154,0x156,0x158,0x15a,0x15c,0x15e,0x160,0x162,0x164,0x166,0x168,0x16a,0x16c,0x16e,0x170,0x172,0x174,0x176,0x178,0x17a,0x17c,0x17e,0x180,0x182,0x184,0x186,0x188,0x18a,0x18c,0x18e,0x190,0x192,0x194,0x196,0x198,0x19a,0x19c,0x19e,0x1a0,0x1a2,0x1a4,0x1a6,0x1a8,0x1aa,0x1ac,0x1ae,0x1b0,0x1b2,0x1b4,0x1b6,0x1b8,0x1ba,0x1bc,0x1be,0x1c0,0x1c2,0x1c4,0x1c6,0x1c8,0x1ca,0x1cc,0x1ce,0x1d0,0x1d2,0x1d4,0x1d6,0x1d8,0x1da,0x1dc,0x1de,0x1e0,0x1e2,0x1e4,0x1e6,0x1e8,0x1ea,0x1ec,0x1ee,0x1f0,0x1f2,0x1f4,0x1f6,0x1f8,0x1fa,0x1fc,0x1fe};
// ---- generated tables (end)
const unsigned int ROW_COUNT=sizeof(ROWS)/sizeof(ROWS[0]);
const unsigned int SYNTHETIC_COUNT=sizeof(SYNTHETIC)/sizeof(SYNTHETIC[0]);
const unsigned int FLOW_COUNT=sizeof(FLOW)/sizeof(FLOW[0]);
const unsigned int START_COUNT=sizeof(STARTS)/sizeof(STARTS[0]);
const std::uint32_t CONSUMERS[]={0xc4a0,0xc674,0xc67e,0xc806,0xc996,0xc9ba};
const unsigned int CONSUMER_COUNT=sizeof(CONSUMERS)/sizeof(CONSUMERS[0]);
const std::uint32_t PRODUCERS[]={0x30c8,0x30ce,0x30e0,0x30e6,0x3156,0x315c,0xca32};
const unsigned int PRODUCER_COUNT=sizeof(PRODUCERS)/sizeof(PRODUCERS[0]);
const std::uint32_t RANGES[][2]={{0x30bc,0x30ec},{0x314c,0x3162},{0x3670,0x370c},{0xc49c,0xc4cc},{0xc4f8,0xc52a},{0xc654,0xc686},{0xc724,0xc74c},
 {0xc7fc,0xc80e},{0xc988,0xca22},{0xca32,0xca3a},{0x4a88e,0x4a8f8},{0x4a944,0x4a9e2}};
const unsigned int RANGE_COUNT=sizeof(RANGES)/sizeof(RANGES[0]);
// Boundaries and callees outside C1 (the rows only stop there).
const std::uint32_t BOUNDARIES[]={0x2ac2,0xc686,0xc74c,0xc76a,0xc00450,0x289e,0x2a28,0x35f0,0x3650,0x3902,0x3918};
const unsigned int BOUNDARY_COUNT=sizeof(BOUNDARIES)/sizeof(BOUNDARIES[0]);
bool in_list(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool is_flow(std::uint32_t pc){return in_list(FLOW,FLOW_COUNT,pc);}
bool is_start(std::uint32_t pc){return in_list(STARTS,START_COUNT,pc);}
bool is_consumer(std::uint32_t pc){return in_list(CONSUMERS,CONSUMER_COUNT,pc);}
bool is_producer(std::uint32_t pc){return in_list(PRODUCERS,PRODUCER_COUNT,pc);}
bool in_ranges(std::uint32_t pc){for(unsigned int i=0;i<RANGE_COUNT;++i)if(pc>=RANGES[i][0]&&pc<RANGES[i][1])return true;return false;}
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
unsigned long long fnv_add(unsigned long long h,const Bytes&b){for(std::size_t i=0;i<b.size();++i){h^=b[i];h*=1099511628211ULL;}return h;}
void long_be(Bytes&b,std::uint32_t v){for(int k=3;k>=0;--k)b.push_back(static_cast<std::uint8_t>(v>>(8*k)));}
unsigned int hex_digit(char c){return c<='9'?static_cast<unsigned int>(c-'0'):static_cast<unsigned int>(c-'a'+10);}
Bytes hex_bytes(const char*text){Bytes b;for(const char*p=text;p[0]&&p[1];p+=2)b.push_back(static_cast<std::uint8_t>((hex_digit(p[0])<<4)|hex_digit(p[1])));return b;}
Physical make_rom(){Physical p(SYNTHETIC_COUNT);
 for(unsigned int i=0;i<SYNTHETIC_COUNT;++i){p[i].source_rom_offset=SYNTHETIC[i].address;p[i].data=hex_bytes(SYNTHETIC[i].bytes);}return p;}
const Physical ROM=make_rom();
std::vector<std::uint8_t> pvc_base(){std::vector<std::uint8_t> p(8192,0);p[0x1ff1]=0xa0;p[0x1ff2]=0x10;return p;}
// "address:hexbytes,..." -> bytes written in order (24-bit addresses, work RAM mirror).
void apply(Bytes&b,const char*text){
 const char*p=text;while(*p){char*end=NULL;const std::uint32_t a=static_cast<std::uint32_t>(std::strtoul(p,&end,16));assert(end&&*end==':');p=end+1;
  std::uint32_t at=a;while(*p&&*p!=','){b[at&65535U]=static_cast<std::uint8_t>((hex_digit(p[0])<<4)|hex_digit(p[1]));p+=2;++at;}if(*p==',')++p;}}
Bytes base_ram(const char*puts){Bytes ram(65536,0);put(ram,SP,4,STOP);apply(ram,puts);return ram;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc=pvc_base();ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
ms5::ProgramBusState bus_of(){ms5::ProgramBusState bus;bus.physical_rom=&ROM;return bus;}
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o){++calls;const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;
 o.ports.clear();o.error.clear();
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
 if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message){
 const Bytes before=ram;const State old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;
 ++calls;const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
 if(ok){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error!=message)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error==message&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&
  o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
// Digest: RAM, D0-D7, A0-A7, PC, bank, reads (BE LONGs), status, ordered port bytes (none here).
unsigned long long digest(const Bytes&ram,const State&s,std::uint32_t bank,std::uint32_t reads,ms5::AnimationMachineStatus status){
 Bytes tail;for(unsigned int i=0;i<8;++i)long_be(tail,s.d[i]);for(unsigned int i=0;i<8;++i)long_be(tail,s.a[i]);
 long_be(tail,s.pc);long_be(tail,bank);long_be(tail,reads);tail.push_back(static_cast<std::uint8_t>(status));
 return fnv_add(fnv_add(1469598103934665603ULL,ram),tail);}
// The default synthetic world (typed key facts): zero D0-D7, A0 = 10c800, A1 = 10c400, A5, A6 and A7 fixed.
State dstate(std::uint32_t pc,unsigned int carry){State s;
 for(unsigned int i=0;i<8;++i)s.d[i]=0;
 s.a[0]=OBJ0;s.a[1]=OBJ1;s.a[2]=0x10c300;s.a[3]=0x10c200;s.a[4]=0x10c100;s.a[5]=A5;s.a[6]=NODE;s.a[7]=SP;s.pc=pc;s.carry=carry_of(carry);return s;}
State wstate(const World&w,std::uint32_t pc,unsigned int carry){State s;
 for(unsigned int i=0;i<8;++i){s.d[i]=w.d[i];s.a[i]=w.a[i];}s.pc=pc;s.carry=carry_of(carry);return s;}
// A block run with declared puts and registers to the expected stop (a checked success).
struct Run {Bytes ram;State s;};
Run begin(std::uint32_t pc,const char*puts,unsigned int carry){Run r;r.ram=base_ram(puts);r.s=dstate(pc,carry);return r;}
Run begin(std::uint32_t pc,const char*puts){return begin(pc,puts,0);}
void go(Run&r,std::uint32_t stop){
 Out o;const std::uint32_t pc=r.s.pc;
 if(!run(r.ram,r.s,stop,o)||r.s.pc!=stop||o.status!=ms5::AnimationMachineReturned||!o.ports.empty()||o.reads!=0||o.dev.bank_base!=0x200000){
  std::cerr<<std::hex<<pc<<" -> "<<stop<<"\n";assert(false);}}
Run go_from(std::uint32_t pc,const char*puts,std::uint32_t stop){Run r=begin(pc,puts);go(r,stop);return r;}
std::uint32_t ld(const Run&r,std::uint32_t address,unsigned int n){return get(r.ram,address,n);}
// A call pushed its return LONG: A7 = SP - 4 and the LONG there.
void called(const Run&r,std::uint32_t ret){
 if(!(r.s.a[7]==SP-4&&ld(r,SP-4,4)==ret))std::cerr<<std::hex<<"call at "<<r.s.pc<<" a7 "<<r.s.a[7]<<" ret "<<ld(r,SP-4,4)<<" want "<<ret<<"\n";
 assert(r.s.a[7]==SP-4&&ld(r,SP-4,4)==ret);}
// ---- generated rows: native successor, native C and digest per block start / world / incoming C.
void rows(){
 unsigned int consumer_rows=0,flow_rows=0,producer_rows=0,boundary_hits=0;
 for(unsigned int i=0;i<ROW_COUNT;++i){const Row&r=ROWS[i];const World&w=WORLDS[r.world];
  const bool consumer=is_consumer(r.pc),flow=is_flow(r.pc),producer=is_producer(r.pc);
  for(unsigned int c=0;c<3;++c){
   if(consumer&&c!=r.c)continue;
   Bytes ram=base_ram(w.puts);State s=wstate(w,r.pc,c);Out o;
   if(!run(ram,s,r.next,o)||s.pc!=r.next){std::cerr<<std::hex<<r.pc<<" world "<<r.world<<"\n";assert(false);}
   const unsigned long long d=digest(ram,s,o.dev.bank_base,o.reads,o.status);
   if(d!=r.digest||o.status!=ms5::AnimationMachineReturned||!o.ports.empty()||o.reads!=0||o.dev.bank_base!=0x200000||o.dev.pvc!=pvc_base()){
    std::cerr<<std::hex<<r.pc<<" world "<<r.world<<" carry "<<c<<" digest "<<d<<" want "<<r.digest<<"\n";assert(false);}
   // Expected C: FLOW blocks keep the incoming C (checked against the native C), the producers return the native C, every other block is Unknown.
   unsigned int expect=0;
   if(flow){expect=c;if(consumer)assert(r.cout==(r.c==2?1U:0U));else assert(r.cout==0U);}
   else if(producer)expect=r.cout?2U:1U;
   if(s.carry!=carry_of(expect)){std::cerr<<std::hex<<r.pc<<" carry "<<s.carry<<" in "<<c<<" want "<<expect<<"\n";assert(false);}
   if(consumer)++consumer_rows;if(flow)++flow_rows;if(producer)++producer_rows;}
  if(in_list(BOUNDARIES,BOUNDARY_COUNT,r.next))++boundary_hits;
  assert(!consumer||r.c==1U||r.c==2U);}
 assert(consumer_rows>=2*CONSUMER_COUNT&&flow_rows>0&&producer_rows>=PRODUCER_COUNT&&boundary_hits>0);
}
// Every start is reached by at least one row; every consumer has both C rows with different successors; the classification lists agree.
void coverage(){
 assert(START_COUNT==116&&FLOW_COUNT==43&&PRODUCER_COUNT==7);
 for(unsigned int i=0;i<START_COUNT;++i){assert(in_ranges(STARTS[i])&&(STARTS[i]&1U)==0U);
  bool found=false;for(unsigned int k=0;k<ROW_COUNT&&!found;++k)found=ROWS[k].pc==STARTS[i];
  if(!found){std::cerr<<std::hex<<"no row for "<<STARTS[i]<<"\n";assert(false);}}
 for(unsigned int c=0;c<CONSUMER_COUNT;++c){bool clear=false,set=false;unsigned int succ_clear=0,succ_set=0;
  for(unsigned int k=0;k<ROW_COUNT;++k)if(ROWS[k].pc==CONSUMERS[c]){if(ROWS[k].c==1){clear=true;succ_clear=ROWS[k].next;}if(ROWS[k].c==2){set=true;succ_set=ROWS[k].next;}}
  assert(clear&&set&&succ_clear!=succ_set);}
 for(unsigned int i=0;i<FLOW_COUNT;++i)assert(is_start(FLOW[i]));
 for(unsigned int i=0;i<PRODUCER_COUNT;++i)assert(is_start(PRODUCERS[i])&&!is_flow(PRODUCERS[i]));
}
// Soft-dip tests, replay-mode test, the C producers and the ca32 CMPI.
void producers() {
 // 30bc: BYTE 10fd8f bit 1 -> 30c8 (Set), else 30ce (Clear); 30d4: bit 0 -> 30e0 (Set), else 30e6 (Clear).
 go_from(0x30bc,"10fd8f:02",0x30c8);go_from(0x30bc,"10fd8f:ff",0x30c8);go_from(0x30bc,"10fd8f:00",0x30ce);go_from(0x30bc,"10fd8f:01",0x30ce);
 go_from(0x30d4,"10fd8f:01",0x30e0);go_from(0x30d4,"10fd8f:ff",0x30e0);go_from(0x30d4,"10fd8f:00",0x30e6);go_from(0x30d4,"10fd8f:02",0x30e6);
 const std::uint32_t sets[]={0x30c8,0x30e0,0x3156},clears[]={0x30ce,0x30e6,0x315c};
 for(unsigned int i=0;i<3;++i)for(unsigned int c=0;c<3;++c){
  Run a=begin(sets[i],"",c);go(a,STOP);assert(a.s.carry==ms5::AnimationCarrySet&&a.s.a[7]==SP+4);
  Run b=begin(clears[i],"",c);go(b,STOP);assert(b.s.carry==ms5::AnimationCarryClear&&b.s.a[7]==SP+4);}
 // 314c: BYTE 104cd4 (-332c(A5)) = 1 -> 3156, else 315c.
 go_from(0x314c,"104cd4:01",0x3156);go_from(0x314c,"104cd4:00",0x315c);go_from(0x314c,"104cd4:02",0x315c);go_from(0x314c,"104cd4:ff",0x315c);
 // ca32: CMPI.B #aa,-769c(A5): C = BYTE 100964 below aa (unsigned), whatever the incoming C.
 const struct {const char* put;ms5::AnimationCarryState c;} cmp[]={{"100964:00",ms5::AnimationCarrySet},{"100964:a9",ms5::AnimationCarrySet},{"100964:aa",ms5::AnimationCarryClear},
  {"100964:ab",ms5::AnimationCarryClear},{"100964:ff",ms5::AnimationCarryClear},{"100964:80",ms5::AnimationCarrySet}};
 for(unsigned int i=0;i<sizeof(cmp)/sizeof(cmp[0]);++i)for(unsigned int c=0;c<3;++c){Run a=begin(0xca32,cmp[i].put,c);go(a,STOP);assert(a.s.carry==cmp[i].c&&a.s.a[7]==SP+4);}
}
// The six consumers: BCC / BCS on the C of the callee that just returned; Unknown C is a checked error with the state preserved.
void consumers() {
 const struct {std::uint32_t pc,clear,set;} t[]={{0xc4a0,0xc4b6,0xc4a4},{0xc674,0xc686,0xc678},{0xc67e,0xc686,0xc682},{0xc806,0xc80a,0xc988},{0xc996,0xc9ac,0xc99a},{0xc9ba,0xc9c2,0xc9be}};
 for(unsigned int i=0;i<6;++i){Run a=begin(t[i].pc,"",1);go(a,t[i].clear);assert(a.s.carry==ms5::AnimationCarryClear);
  Run b=begin(t[i].pc,"",2);go(b,t[i].set);assert(b.s.carry==ms5::AnimationCarrySet);
  Bytes ram=base_ram("");reject(ram,dstate(t[i].pc,0),STOP,"controller c1 caller requires known carry");}
 // The real producers feed them: 289e (callback 270e -> Clear), 30bc / 30d4, 314c and ca32 through the return LONG.
 {Run a=begin(0x289e,"100b30:0000270e");a.s.a[0]=0x100b30;put(a.ram,SP,4,0xc674);go(a,0xc686);}
 {Run a=begin(0x289e,"100b30:00047af0");a.s.a[0]=0x100b30;put(a.ram,SP,4,0xc674);go(a,0xc678);}
 {Run a=begin(0x289e,"100b30:0000270e");a.s.a[0]=0x100b30;put(a.ram,SP,4,0xc806);go(a,0xc80a);}
 {Run a=begin(0x289e,"100b30:00047af0");a.s.a[0]=0x100b30;put(a.ram,SP,4,0xc806);go(a,0xc988);}
 {Run a=begin(0x314c,"104cd4:01");put(a.ram,SP,4,0xc67e);go(a,0xc682);}
 {Run a=begin(0x314c,"104cd4:00");put(a.ram,SP,4,0xc67e);go(a,0xc686);}
 {Run a=begin(0x30bc,"10fd8f:02");put(a.ram,SP,4,0xc996);go(a,0xc99a);}
 {Run a=begin(0x30bc,"10fd8f:00");put(a.ram,SP,4,0xc996);go(a,0xc9ac);}
 {Run a=begin(0x30d4,"10fd8f:01");put(a.ram,SP,4,0xc9ba);go(a,0xc9be);}
 {Run a=begin(0x30d4,"10fd8f:00");put(a.ram,SP,4,0xc9ba);go(a,0xc9c2);}
 {Run a=begin(0xca32,"100964:a9");put(a.ram,SP,4,0xc4a0);go(a,0xc4a4);}
 {Run a=begin(0xca32,"100964:aa");put(a.ram,SP,4,0xc4a0);go(a,0xc4b6);}
}
// The full 512 inputs of SBCD.B D2,D1 (D2 = 0) after SUBQ.B #8,D0, through the real tail c9fe..ca20: BYTE 7a(A6) x BYTE 7b(A6) = 7 (X = 1) / 8 (X = 0).
void sbcd() {
 for(unsigned int x=0;x<2;++x)for(unsigned int value=0;value<256;++value){
  const unsigned int low=x==0?7U:8U;
  Run a=begin(0xc9fe,"");put(a.ram,NODE+0x7a,2,(value<<8)|low);go(a,STOP);
  const unsigned int cell=SBCD[x*256+value],result=cell>>1,borrow=cell&1U;
  assert(a.s.pc==STOP&&a.s.a[7]==SP+4);
  if(borrow){assert(ld(a,NODE+0x7a,2)==0U&&a.s.d[0]==0U&&a.s.d[1]==0U);}
  else{assert(ld(a,NODE+0x7a,1)==result&&ld(a,NODE+0x7b,1)==((low-8U)&255U)&&(a.s.d[1]&255U)==result&&(a.s.d[0]&255U)==((low-8U)&255U));}
  // The same block entered at ca06 gives the same decision.
  Run b=begin(0xca06,"");put(b.ram,NODE+0x7a,2,(value<<8)|low);b.s.d[0]=low;go(b,borrow?0xca14U:0xca18U);
  assert((b.s.d[1]&255U)==result);}
 // Spot values: 00 - X = 99 with C, 10 - 1 = 09, 0a / 1a (non-BCD) keep the 68000 digit rule, 99 - 0 = 99.
 assert(SBCD[256+0]==((0x00U<<1)|0U)&&SBCD[0]==((0x99U<<1)|1U)&&SBCD[0x10]==((0x09U<<1)|0U)&&SBCD[256+0x99]==((0x99U<<1)|0U));
}
// Credit bits 4a9ca and the Z recompute at 4a9d0 / 4a9da; BIOS c00450 stop and the declared answer.
void credit() {
 // 100003 = 0: both players read BYTE 100004; 100003 != 0: BYTE 100004 + player.
 const struct {const char* put;std::uint32_t d7;} bits[]={{"100003:00,100004:05,100005:00",3},{"100003:00,100004:00,100005:09",0},{"100003:01,100004:05,100005:00",1},
  {"100003:01,100004:00,100005:09",2},{"100003:01,100004:01,100005:01",3},{"100003:01,100004:00,100005:00",0},{"100003:ff,100004:00,100005:80",2}};
 for(unsigned int i=0;i<sizeof(bits)/sizeof(bits[0]);++i){Run a=begin(0x4a9ca,bits[i].put);a.s.d[7]=0x12345678;go(a,STOP);
  assert(a.s.d[7]==bits[i].d7&&a.s.d[0]==1U&&a.s.a[7]==SP+4&&a.s.carry==ms5::AnimationCarryUnknown);}
 // The Z consumers read BYTE (A0): zero -> the skip target, non-zero -> the BSET block; A0 outside the four proven bytes is a checked error.
 const std::uint32_t four[]={0x10fdb0,0x10fdb1,0x100004,0x100005};
 for(unsigned int i=0;i<4;++i)for(unsigned int c=0;c<3;++c){
  Run z=begin(0x4a9d0,"",c);z.s.a[0]=four[i];go(z,0x4a9d6);assert(z.s.carry==carry_of(c));
  Run n=begin(0x4a9d0,"",c);n.s.a[0]=four[i];put(n.ram,four[i],1,0x80);go(n,0x4a9d4);assert(n.s.carry==carry_of(c));
  Run z2=begin(0x4a9da,"",c);z2.s.a[0]=four[i];go(z2,0x4a9e0);
  Run n2=begin(0x4a9da,"",c);n2.s.a[0]=four[i];put(n2.ram,four[i],1,0x01);go(n2,0x4a9de);}
 const std::uint32_t bad[]={0,0x3000,0x10fdaf,0x10fdb2,0x100003,0x100006,0x10fe00,0xd00034,0x1fdb0,0xffffffff};
 for(unsigned int i=0;i<sizeof(bad)/sizeof(bad[0]);++i){const std::uint32_t pcs[]={0x4a9d0,0x4a9da};
  for(unsigned int k=0;k<2;++k){State s=dstate(pcs[k],1);s.a[0]=bad[i];Bytes ram=base_ram("");reject(ram,s,STOP,"unsupported animation controller flag source");}}
 // BSET.B D0,D7 uses D0 modulo 32.
 {Run a=begin(0x4a9d4,"");a.s.d[0]=33;a.s.d[7]=0;go(a,0x4a9d6);assert(a.s.d[7]==2U);Run b=begin(0x4a9de,"");b.s.d[0]=1;b.s.d[7]=1;go(b,0x4a9e0);assert(b.s.d[7]==3U);}
 // 4a974 with BYTE 10fd82 set: LONG 10fdb0 = 01010000, WORD D0 & 1 pushed, JSR c00450 (return 4a992). The frame driver answers: LONG 10fdb0, PC := 4a992, A7 += 4.
 {Run a=begin(0x4a974,"10fd82:01");a.s.d[0]=0xabcd0003;go(a,0xc00450);
  assert(ld(a,0x10fdb0,4)==0x01010000U&&a.s.d[0]==0xabcd0001U&&a.s.a[7]==SP-6&&ld(a,SP-6,4)==0x4a992U&&ld(a,SP-2,2)==1U);
  put(a.ram,0x10fdb0,4,0x00010000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,STOP); // 100003 = 0, 100012 != 2: A0 = 10fdb0 + D0 -> BYTE 10fdb1
  assert(a.s.d[0]==0xabcd0001U&&a.s.a[5]==0x108000U&&a.s.a[0]==0x10fdb1U&&a.s.a[7]==SP+4);}
 {Run a=begin(0x4a974,"10fd82:01,100012:02");go(a,0xc00450);put(a.ram,0x10fdb0,4,0x01000000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,STOP); // 100012 = 2: A0 stays 10fdb0
  assert(a.s.a[0]==0x10fdb0U);}
 {Run a=begin(0x4a974,"10fd82:01,100003:01,100012:02");a.s.d[0]=1;go(a,0xc00450);put(a.ram,0x10fdb0,4,0x00010000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,STOP); // 100003 != 0: ADDA
  assert(a.s.a[0]==0x10fdb1U);}
 // Whole 4a9ca with the BIOS: two calls, answers 01000000 then 00010000 -> player 0 set (10fdb0 = 01), player 1 set (10fdb1 = 01).
 {Run a=begin(0x4a9ca,"10fd82:01");go(a,0xc00450);put(a.ram,0x10fdb0,4,0x01000000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,0xc00450);
  assert(a.s.d[0]==1U&&ld(a,0x10fdb0,4)==0x01010000U);put(a.ram,0x10fdb0,4,0x00010000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,STOP);assert(a.s.d[7]==3U);}
 {Run a=begin(0x4a9ca,"10fd82:01");go(a,0xc00450);put(a.ram,0x10fdb0,4,0x01000000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,0xc00450);
  put(a.ram,0x10fdb0,4,0x00000000);a.s.a[7]+=4;a.s.pc=0x4a992;go(a,STOP);assert(a.s.d[7]==1U);}
 // 4a974 with 10fd82 clear: A0 = 100004 (+ D0 when 100003 is set), no BIOS.
 {Run a=begin(0x4a974,"");a.s.d[0]=0xffff0003;go(a,STOP);assert(a.s.d[0]==0xffff0001U&&a.s.a[0]==0x100004U);}
 {Run a=begin(0x4a974,"100003:01");a.s.d[0]=3;go(a,STOP);assert(a.s.a[0]==0x100005U);}
 // 4a944: WORD (A1), then BYTE (A1) when 100003 is clear; A1 = 100004, or 10fe00 for BYTE 10fd82 set with 10fe80 set.
 {Run a=begin(0x4a944,"100004:1234,100003:00");go(a,STOP);assert(a.s.d[0]==0x1212U&&a.s.a[1]==0x100004U);}
 {Run a=begin(0x4a944,"100004:1234,100003:01");go(a,STOP);assert(a.s.d[0]==0x1234U);}
 {Run a=begin(0x4a944,"10fd82:01,10fe80:01,10fe00:5678,100003:01");go(a,STOP);assert(a.s.d[0]==0x5678U&&a.s.a[1]==0x10fe00U);}
 // MVS backup RAM d00034 (BYTE 10fd82 set, 10fe80 clear): checked error, state preserved.
 for(unsigned int bit=0;bit<2;++bit){const std::uint32_t entries[]={0x4a944,0x4a88e,0x4a954,0x4a89e};
  for(unsigned int i=0;i<4;++i){Bytes ram=base_ram(bit?"10fd82:01,100003:01":"10fd82:01");reject(ram,dstate(entries[i],0),STOP,"unsupported animation controller backup RAM read");}}
 {const std::uint32_t a1s[]={0xd00034,0xd00035,0xd0ffff};const std::uint32_t pcs[]={0x4a8ce,0x4a966,0x4a970};
  for(unsigned int i=0;i<3;++i)for(unsigned int k=0;k<3;++k){State s=dstate(pcs[k],0);s.a[1]=a1s[i];Bytes ram=base_ram("");reject(ram,s,STOP,"unsupported animation controller backup RAM read");}}
}
// Credit text 4a88e and the credit count c4f8 / c50e / c526 (byte push: A7 changes by 2).
void texts() {
 // 4a88e: 10fd82 = 0 -> A1 = 100004; 100003 = 0 -> D0.W = D2.W; BYTE (A1) < 2 -> A0 = 4a8f8, else 4a903; A1 pushed, JSR 3902 (return 4a8e6).
 {Run a=begin(0x4a88e,"100004:01");a.s.d[2]=0x737d;a.s.d[0]=0xffff0000;go(a,0x4a8ce);assert(a.s.a[1]==0x100004U&&(a.s.d[0]&65535U)==0x737dU);
  go(a,0x3902);assert(a.s.a[0]==0x4a8f8U&&a.s.a[7]==SP-8&&ld(a,SP-8,4)==0x4a8e6U&&ld(a,SP-4,4)==0x100004U);}
 {Run a=begin(0x4a88e,"100004:02");a.s.d[2]=0x737d;go(a,0x3902);assert(a.s.a[0]==0x4a903U);}
 // 100003 set: the first digit (BSR 4a8ce, A1 = 100004), then the second at A1 + 1 after the stack pops; D0 = D2 - 40, D3 = ffffffff, D4.W = 2, JMP 36ba.
 {Run a=begin(0x4a88e,"100003:01,100004:00,100005:05");a.s.d[2]=0x1234;go(a,0x3902);
  assert(a.s.a[7]==SP-18&&ld(a,SP-18,4)==0x4a8e6U&&ld(a,SP-14,4)==0x100004U&&ld(a,SP-10,4)==0x4a8c2U&&ld(a,SP-6,4)==0x100004U&&ld(a,SP-2,2)==0x1234U);
  Run b=begin(0x4a8e6,"");b.s.d[0]=0x1234;put(b.ram,SP,4,0x100005);go(b,0x36ba);assert(b.s.d[0]==0x11f4U&&b.s.a[0]==0x100005U&&b.s.d[3]==0xffffffffU&&(b.s.d[4]&65535U)==2U);}
 // 4a8c2: pops A1 (LONG) and D0 (WORD), A1 += 1, BRA 4a8ce.
 {Run a=begin(0x4a8c2,"");put(a.ram,SP,4,0x100004);put(a.ram,SP+4,2,0xbeef);go(a,0x4a8ce);assert(a.s.a[1]==0x100005U&&(a.s.d[0]&65535U)==0xbeefU&&a.s.a[7]==SP+6);}
 // c4f8: D0.W = 723d, D1.W = b5a, D2.W = 5, D3.W = 1, JSR 35f0 (return c50e).
 {Run a=begin(0xc4f8,"");a.s.d[0]=0x11110000;go(a,0x35f0);assert(a.s.d[0]==0x1111723dU&&(a.s.d[1]&65535U)==0xb5aU&&(a.s.d[2]&65535U)==5U&&(a.s.d[3]&65535U)==1U);called(a,0xc50e);}
 // c50e: BYTE 10fd8b is pushed as a byte (A7 -= 2), incremented through A0 = A7, D1.W = 3, D4.W = 1, JSR 3706 (return c526); the BYTE wraps at ff.
 {Run a=begin(0xc50e,"10fd8b:09");go(a,0x3706);assert(a.s.a[0]==SP-2&&a.s.a[7]==SP-6&&ld(a,SP-2,1)==0x0aU&&ld(a,SP-6,4)==0xc526U&&(a.s.d[1]&65535U)==3U&&(a.s.d[4]&65535U)==1U);
  Run b=begin(0xc50e,"10fd8b:ff");go(b,0x3706);assert(ld(b,SP-2,1)==0U);}
 // c526: MOVE.B (A7)+,D0 (A7 += 2) and RTS.
 {Run a=begin(0xc526,"");a.s.a[7]=SP-2;put(a.ram,SP-2,1,0x5a);a.s.d[0]=0x12345600;go(a,STOP);assert(a.s.d[0]==0x1234565aU&&a.s.a[7]==SP+4);}
 // c49c: JSR ca32 (return c4a0); c4a0 -> c4b6 (A0 = c46e) or c4a4 (JSR 4a9ca); c4aa: A0 = LONG c48c + 4 * D7.W (synthetic table 100100 + 10 * i); c4ba: JMP 3918.
 {Run a=begin(0xc49c,"100964:aa");a.s.d[0]=0x77770000;go(a,0x3918);assert(a.s.a[0]==0xc46eU&&a.s.a[1]==0xe84c8U&&a.s.d[0]==0x77777157U&&a.s.carry==ms5::AnimationCarryUnknown);}
 {Run a=begin(0xc49c,"100964:a9,100004:00");go(a,0x3918);assert(a.s.a[0]==0x100100U&&a.s.d[7]==0U);}
 {Run a=begin(0xc49c,"100964:a9,100003:01,100004:01,100005:01");go(a,0x3918);assert(a.s.a[0]==0x100130U&&a.s.d[7]==12U);}
 {Run a=begin(0xc49c,"100964:a9,100003:01,100004:00,100005:01");go(a,0x3918);assert(a.s.a[0]==0x100120U&&a.s.d[7]==8U);}
 {Run a=begin(0xc4aa,"");a.s.d[7]=0x4001;go(a,0x3918);assert(a.s.a[0]==0x100110U&&a.s.d[7]==0x0004U);} // ADD.W twice: 4 * 4001 wraps to 4 at WORD width
}
// The digit renderer 3670..3706: nibbles, leading zeros (3706 skips them), the glyph table and the live JSR (A1).
void digits() {
 // 3706: A1 = 3650, then 36c0: D3.B = 0.
 {Run a=begin(0x3706,"");a.s.a[1]=0x1234;go(a,0x36c0);assert(a.s.a[1]==0x3650U);Run b=begin(0x36c0,"");b.s.d[3]=0x12345678;go(b,0x36c2);assert(b.s.d[3]==0x12345600U);}
 // 36ba: A1 = 3650, BRA 3670.
 {Run a=begin(0x36ba,"");go(a,0x3670);assert(a.s.a[1]==0x3650U);}
 // 36ec / 36a2: push A0, D2.B = glyph[D2.W] (T[i] = i * 23 + 45), A0 = 3650, JSR (A1) with A1 live; the callee is the PC A1 holds.
 {Run a=begin(0x36ec,"");a.s.a[0]=0x100100;a.s.a[1]=0x3650;a.s.d[2]=0xabcd0001;go(a,0x3650);assert(a.s.d[2]==0xabcd0068U&&a.s.a[0]==0x3650U);assert(a.s.a[7]==SP-8&&ld(a,SP-8,4)==0x36fcU&&ld(a,SP-4,4)==0x100100U);}
 {Run a=begin(0x36a2,"");a.s.a[0]=0x100100;a.s.a[1]=0x10fe00;a.s.d[2]=0x10;go(a,0x10fe00);assert(a.s.a[1]==0x10fe00U&&a.s.d[2]==0x75U&&a.s.a[7]==SP-8&&ld(a,SP-8,4)==0x36b2U&&ld(a,SP-4,4)==0x100100U);}
 // Digit loop: 3706 with D4 = 2 and BCD bytes 12 34: D2 = 1, 2, 3, 4 per pass; 3706 leaves D3 = ff after the first non-zero digit.
 {Run a=begin(0x36c2,"100100:1234");a.s.a[0]=0x100100;a.s.a[1]=0x3650;a.s.d[4]=2;a.s.d[3]=0;go(a,0x36e2);assert(a.s.d[2]==0x1U&&a.s.a[0]==0x100100U);
  go(a,0x36e6);go(a,0x36ec);go(a,0x3650);assert(a.s.d[3]==0xffU&&(a.s.d[2]&255U)==0x68U);}
 // The odd digit pass takes the low nibble and advances A0 (3680 / 36d2); a zero digit is skipped by 3706 (36e6 BEQ) unless it is the last (D4.W = 1).
 {Run a=begin(0x36c2,"100100:1234");a.s.a[0]=0x100100;a.s.d[4]=1;go(a,0x36d2);assert(a.s.d[2]==0x12U);go(a,0x36d4);assert(a.s.a[0]==0x100101U);go(a,0x36e2);assert(a.s.d[2]==2U);}
 {Run a=begin(0x36c2,"100100:0000");a.s.a[0]=0x100100;a.s.d[4]=2;a.s.d[3]=0;go(a,0x36da);go(a,0x36e6);go(a,0x36fe);go(a,0x36c2);assert((a.s.d[4]&65535U)==1U);
  go(a,0x36d2);go(a,0x36d4);go(a,0x36da);go(a,0x36e2);go(a,0x36e6);assert(a.s.d[3]==0xffU);}
 // 3698: leading zeros are drawn by 3670 (D3 = 0 -> 369e sets D2.B = 10), skipped when D3 != 0 is not set... (D3 BYTE non-zero draws the zero glyph).
 {Run a=begin(0x3698,"");a.s.d[3]=0;go(a,0x369e);Run b=begin(0x3698,"");b.s.d[3]=0x100;go(b,0x369e);Run c=begin(0x3698,"");c.s.d[3]=1;go(c,0x36a2);
  Run d=begin(0x369e,"");d.s.d[2]=0x12345678;go(d,0x36a2);assert(d.s.d[2]==0x12345610U);}
 // 36b2: pops A0 (LONG), SUBQ.W #1,D4: loop to 3670 or RTS block 36b8. 3702: SWAP D0 and RTS.
 {Run a=begin(0x36b2,"");put(a.ram,SP,4,0x100100);a.s.d[4]=0x10002;go(a,0x3670);assert(a.s.a[0]==0x100100U&&a.s.d[4]==0x10001U&&a.s.a[7]==SP+4);
  Run b=begin(0x36b2,"");put(b.ram,SP,4,0x100100);b.s.d[4]=0x10001;go(b,0x36b8);assert(b.s.d[4]==0x10000U);
  Run c=begin(0x36b2,"");put(c.ram,SP,4,0x100100);c.s.d[4]=0x10000;go(c,0x3670);assert(c.s.d[4]==0x1ffffU);
  Run d=begin(0x3702,"");d.s.d[0]=0x12345678;go(d,STOP);assert(d.s.d[0]==0x56781234U);}
}
// The gates and the tail through the real routed readiness callee 289e (no ROM data): game gate c7fc, demo gate c66a, mode check, idle node.
void gates() {
 // Game gate, node callback 47af0 (not 270e): c7fc -> 289e -> c806 (Set) -> c988 -> c9c2 -> 4a944 ... -> ca20 -> RTS. 81(A6) = 0.
 {Run a=begin(0xc7fc,"100b30:00047af0");go(a,STOP);assert(a.s.carry==ms5::AnimationCarryUnknown&&a.s.a[7]==SP+4&&ld(a,NODE+0x80,1)==6U&&ld(a,NODE+0x82,1)==0U&&a.s.a[0]==0x100b30U&&a.s.a[1]==0x100004U);}
 // Idle node (callback 270e): c80a -> c76a, the C2 transition boundary.
 {Run a=begin(0xc7fc,"100b30:0000270e");go(a,0xc76a);assert(a.s.carry==ms5::AnimationCarryClear);}
 // Tail: credit change 7e <- WORD, 80 cleared; 80 += 6 wraps; 78 counts down by 4 to 0; 83 stops the timer.
 {Run a=begin(0xc9c2,"100004:0505,100003:01,10fd8f:00");put(a.ram,NODE+0x81,1,5);put(a.ram,NODE+0x80,1,0x77);put(a.ram,NODE+0x78,2,6);go(a,STOP);
  assert(ld(a,NODE+0x82,1)==5U&&ld(a,NODE+0x7e,2)==0x0505U&&ld(a,NODE+0x80,1)==6U&&ld(a,NODE+0x78,2)==2U);}
 {Run a=begin(0xc9c2,"100004:0505,100003:01");put(a.ram,NODE+0x7e,2,0x0505);put(a.ram,NODE+0x80,1,0xfc);put(a.ram,NODE+0x78,2,3);go(a,STOP);
  assert(ld(a,NODE+0x80,1)==2U&&ld(a,NODE+0x78,2)==0U);}
 {Run a=begin(0xc9f6,"");put(a.ram,NODE+0x83,1,1);put(a.ram,NODE+0x7a,2,0x1234);go(a,STOP);assert(ld(a,NODE+0x7a,2)==0x1234U);}
 // BCD timer 7a (seconds) / 7b: 01 07 -> 00 ff? D0.B = 07 - 8 = ff with X = 1, SBCD 01 - 1 = 00 (no borrow): 7b = ff, 7a = 00.
 {Run a=begin(0xc9f6,"");put(a.ram,NODE+0x7a,2,0x0107);go(a,STOP);assert(ld(a,NODE+0x7a,2)==0x00ffU);}
 {Run a=begin(0xc9f6,"");put(a.ram,NODE+0x7a,2,0x0008);go(a,STOP);assert(ld(a,NODE+0x7a,2)==0x0000U);}
 {Run a=begin(0xc9f6,"");put(a.ram,NODE+0x7a,2,0x0007);go(a,STOP);assert(ld(a,NODE+0x7a,2)==0x0000U&&a.s.d[0]==0U&&a.s.d[1]==0U);}
 // Demo gate, replay mode (BYTE 104cd4 = 1), node callback 47af0, BYTE 100012 != 2, 81(A6) = 0: c66a -> 289e -> c674 -> c678 -> 314c -> c67e -> c682 -> c724 -> c72e -> c988 ... RTS.
 {Run a=begin(0xc66a,"100b30:00047af0,104cd4:01");go(a,STOP);assert(a.s.a[7]==SP+4&&ld(a,NODE+0x80,1)==6U);}
 {Run a=begin(0xc66a,"100b30:00047af0,104cd4:01,100012:02");go(a,0xc74c);} // game start (C2)
 {Run a=begin(0xc66a,"100b30:00047af0,104cd4:00");go(a,0xc686);}            // not replay: C2 transition
 {Run a=begin(0xc66a,"100b30:0000270e,104cd4:01");go(a,0xc686);}            // idle node: C2 transition
 // c72e: 81(A6) != 0 -> c736 BSR c49c (return c73a) -> ... -> c988; c73e / c748 are the same mode check entered from the C2 side.
 {Run a=begin(0xc72e,"");put(a.ram,NODE+0x81,1,1);go(a,0xc49c);called(a,0xc73a);Run b=begin(0xc73a,"");go(b,0xc988);
  Run c=begin(0xc73e,"100012:02");go(c,0xc74c);Run d=begin(0xc73e,"100012:01");go(d,0xc748);Run e=begin(0xc748,"");go(e,0xc988);}
 // Tail with the credit text flag: 81(A6) != 0 -> 30bc (bit 1 of 10fd8f) -> 4a88e text when Set; 82(A6) clear -> 30d4 (bit 0) -> c4f8 count when Set.
 {Run a=begin(0xc988,"");put(a.ram,NODE+0x81,1,1);go(a,0x30bc);called(a,0xc996);}
 {Run a=begin(0xc99a,"");a.s.d[0]=0xaaaa0000;go(a,0x4a88e);assert(a.s.d[0]==0xaaaa709dU&&(a.s.d[2]&65535U)==0x737dU&&(a.s.d[1]&65535U)==3U);called(a,0xc9ac);}
 {Run a=begin(0xc9ac,"");put(a.ram,NODE+0x82,1,1);go(a,0xc9c2);Run b=begin(0xc9ac,"");go(b,0x30d4);called(b,0xc9ba);}
 {Run a=begin(0xc9be,"");go(a,0xc4f8);called(a,0xc9c2);}
 // c654: LEA 100b30,A0; A1 = 477e4; JSR 2a28 (cleanup, return c664); c664 installs c66a in the node.
 {Run a=begin(0xc654,"");go(a,0x2a28);assert(a.s.a[0]==0x100b30U&&a.s.a[1]==0x477e4U);called(a,0xc664);Run b=begin(0xc664,"");go(b,0xc66a);assert(ld(b,NODE,4)==0xc66aU);}
}
// Checked errors: every interior even PC of the 12 ranges, odd range edges, neighbouring PCs (rollback), unrouted JSR (A1) targets.
void errors() {
 unsigned int even=0,inside=0;
 for(unsigned int r=0;r<RANGE_COUNT;++r)for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2){++even;
  if(is_start(pc))continue;Bytes ram=base_ram("");reject(ram,dstate(pc,2),STOP,"unsupported animation controller c1 PC");++inside;}
 assert(even==429&&inside==313);
 for(unsigned int r=0;r<RANGE_COUNT;++r){const std::uint32_t odd[]={RANGES[r][0]+1,RANGES[r][1]-1};
  for(unsigned int i=0;i<2;++i){Bytes ram=base_ram("");reject(ram,dstate(odd[i],2),STOP,"unaligned animation machine PC");}}
 // c686 c74c c76a now run in the C2 unit (the rows above stop there); the BIOS entries stay boundaries (no executor): checked errors unless they are the stop.
 // Review 0264 M-3: the former ROM neighbours c6ce 1022 bbfa (code of later units) are the work-RAM PCs 10fe10 10fe12 10fe14.
 const std::uint32_t outside[]={0x10fe10,0x10fe12,0x10fe14,0xc00450,0xc00444,0x10fe00,0x10fe40,0x10fefe};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram=base_ram("");reject(ram,dstate(outside[i],2),STOP,"unsupported animation machine PC");}
 {Run a=begin(0xc686,"");go(a,0xc686);}
 // JSR (A1) follows the live target: work RAM is unrouted, an odd target is an unaligned PC.
 {State s=dstate(0x36a2,0);s.a[1]=0x10fe00;Bytes ram=base_ram("");reject(ram,s,STOP,"unsupported animation machine PC");
  State t=dstate(0x36ec,0);t.a[1]=0x3651;reject(ram,t,STOP,"unaligned animation machine PC");}
 // An odd credit pointer WORD read is a bus error.
 {State s=dstate(0x4a966,0);s.a[1]=0x100005;Bytes ram=base_ram("");reject(ram,s,STOP,"program bus requires even WORD/LONG address");}
 // A failing run in the middle of a chain preserves everything (4a9ca -> 4a974 -> BIOS call is not the stop).
 {Bytes ram=base_ram("10fd82:01");reject(ram,dstate(0x4a9ca,0),STOP,"unsupported animation machine PC");}
}
// Stopping at the entry PC executes nothing (state, RAM and device are unchanged) for every block start and every C tag.
void zero_step() {
 for(unsigned int c=0;c<3;++c)for(unsigned int i=0;i<START_COUNT;++i){Bytes ram=base_ram("");State s=dstate(STARTS[i],c);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,STARTS[i],o)&&same(s,old)&&ram==before&&o.ports.empty()&&o.reads==0&&
   o.status==ms5::AnimationMachineReturned&&o.dev.bank_base==0x200000);}
}
}
int main(){
 producers();consumers();sbcd();credit();texts();digits();gates();rows();coverage();errors();zero_step();
 std::cout<<"animation machine controller c1: "<<START_COUNT<<" blocks, "<<ROW_COUNT<<" rows, "<<calls<<" calls\n";
 return 0;
}
