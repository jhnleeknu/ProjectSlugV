#include "ms5/animation_machine.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
// Objects B2e (109 block starts: the script callbacks 3abee 3b656 3b458 3b648 3b62a of the interpreter table 4a500, the angle leaf 44602, the child-spawn helper
// 4db18 with its 28ae child 4dbdc (live JSR (A1) of 4dc44), and the demo-end ranking child e66aa with its child e68c6 and the text leaf e89da) through
// run_animation_machine only. Inputs are declared fixtures in a synthetic world: zero work RAM with LONG 10f000 = STOP at A7 = 10f000, node A6 = 10e000,
// A5 = 108000, parent c(A6) = 10d000, a second node 10c400, the callback argument WORDs at 10c000, the ranking records 10f02e, seeded BYTE / WORD / LONG node and
// parent fields, seeded D0-D7, A0 and A1 (generated), and the incoming C tag. Synthetic typed physical bytes (not ROM data): the angle bytes 44380..44602, the
// rank-label pointers e637a..e63a6 with their text, the script pointers e63e4..e63ec and the banked bytes 200000..200100. The ROWS table was produced from the
// ORIGINAL code bytes (Unicorn M68000 on the canonical BE ROM with the same synthetic bytes overlaid, tools/generate_animation_machine_objects_b2e_test_table.py):
// per block start and seeded world the native run from the block start to the first other block start / PC outside the ten routed ranges, one row per distinct
// successor, with the FNV-1a digest of RAM, D0-D7, A0-A7, PC, bank, reads and status (B2e writes no port). The five consumers 3ac76 3b666 4dc34 4dc46 4dc50 are
// checked per incoming C and keep it; every other block is checked with all three C tags and ends Unknown (B2e has no known-C producer). e6890 (MOVE.W #1,1.w,
// an odd WORD write) is a checked error; the TRAP #f sites e6836 / e6896 are unrouted boundaries (stop only). The native-fixture verifier
// (tools/unit_fixture_specs/b2e.py) runs natural node, callback, caller and demo states of the D1 seeds against the original ROM.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef ms5::AnimationMachineState State;
const std::uint32_t STOP=0xff000,SP=0x10f000,NODE=0x10e000,A5=0x108000,PARENT=0x10d000,CHILD=0x10c400,ARGS=0x10c000,RECORDS=0x10f02e;
unsigned int calls=0;
struct World {const char* puts;std::uint32_t d[8];std::uint32_t a0;std::uint32_t a1;};
struct Row {std::uint32_t pc;unsigned int world,c;std::uint32_t next;unsigned long long digest;};
struct Synthetic {std::uint32_t address;const char* bytes;};
// ---- generated tables (begin)
const World WORLDS[]={
 {"10e012:f0,10e015:00,10e060:03,10e098:09,10e0a1:80,10e0a2:00,10e0a6:ff,10e0a8:02,10e01e:0000,10e068:fff1,10e076:0001,10e078:0001,10e07a:0001,10e07c:ffff,10e00c:0010d000,10d062:5a,10d080:00,10c000:0000,10c002:1234,10c004:ffff,10c006:fff0,10c008:0010,10c00a:ffff,10f000:12348765,10f004:00000000,10f008:000ff000",{0x7fff,0x67ed9202,0x5,0xff,0x7f,0x5,0xffff,0x7fff},0x10c000,0x10c000},
 {"10e012:f0,10e015:01,10e09d:10,10e09e:ff,10e0a1:40,10e0a3:06,10e0a6:05,10e01e:0000,10e076:ffff,10e07a:0000,10e07c:ffff,10e07e:0005,10e064:00010000,10e07a:0000288c,10e00c:0010d000,10d062:5a,10d080:00,10c000:ffff,10c002:0010,10c004:0000,10c006:0040,10c008:ffff,10c00a:0080",{0xff,0x346ee0b9,0x42dab6d6,0x7fff,0x7f,0xa0877c89,0xb,0xff},0x10c002,0x10f02e},
 {"10e012:f0,10e080:ff,10e098:09,10e09d:00,10e0a1:80,10e0a2:00,10e0a3:00,10e068:0000,10e07c:0001,10e07e:0000,10e022:00200040,10e036:ffff0000,10c000:0040,10c002:0080,10c004:0040,10c006:0040,10c008:1234,10c00a:fff0,10f02e:00001000,10f032:41424300,10f036:00106400,10f03a:41424301,10f03e:80000000,10f042:41424302,10f046:00104400,10f04a:41424303,10f04e:00103400,10f052:41424304,10f056:00001000,10f05a:41424305,10f05e:80000000,10f062:41424306,10f066:00000005,10f06a:41424307,10f06e:000ff400,10f072:41424308,10f076:00000005,10f07a:41424309,10f07e:000fd400,10f082:4142430a",{0x3cb64097,0xbf6c6849,0x3,0x10,0x12345678,0x0,0x57e2d163,0x7fff},0x10c002,0x10c004},
 {"10e080:01,10e098:09,10e09e:10,10e0a8:02,10e020:00ea,10e068:0000,10e07a:ffff,10e07e:0005,10e022:00200040,10e036:7fffffff,10e03a:fffe0000,10e07a:00000000,10e00c:0010d000,10d062:5a,10d080:ff,10c000:ffff,10c002:1234,10c004:0010,10c006:1234,10c008:0010,10c00a:fff0",{0x2,0x10,0x7fff,0x8000,0xb5b3571d,0x100,0x12345678,0x10000},0x10c000,0x10c000},
 {"10e012:ef,10e015:00,10e060:00,10e080:01,10e09d:10,10e09e:10,10e0a1:40,10e0a2:05,10e0a6:05,10e0a8:80,10e01e:0000,10e020:00ea,10e068:fff1,10e078:0001,10e07e:0000,10e022:00200040,10c000:fff0,10c002:0080,10c004:0080,10c006:0040,10c008:0010,10c00a:1234,10f02e:00001000,10f032:41424300,10f036:00001000,10f03a:41424301,10f03e:00000000,10f042:41424302,10f046:00000000,10f04a:41424303,10f04e:00001000,10f052:41424304,10f056:80000000,10f05a:41424305,10f05e:00001000,10f062:41424306,10f066:00000000,10f06a:41424307,10f06e:00001000,10f072:41424308,10f076:00000005,10f07a:41424309,10f07e:00000000,10f082:4142430a,10f000:0005,10f002:000ff000",{0x8000,0x12345678,0x3,0x5866398c,0x12345678,0x3f,0xaece8510,0x5e57ed77},0x10c400,0x10f02e},
 {"10e012:00,10e060:00,10e09e:00,10e0a1:ff,10e0a2:05,10e0a6:05,10e020:0000,10e076:0002,10e078:0009,10e07a:ffff,10e07e:0000,10e022:00000000,10e064:00010000,10e07a:00000000,10e00c:0010d000,10d062:5a,10d080:ff,10c000:ffff,10c002:0040,10c004:fff0,10c006:fff0,10c008:fff0,10c00a:ffff,10f02e:00001000,10f032:41424300,10f036:00000005,10f03a:41424301,10f03e:00001000,10f042:41424302,10f046:00001000,10f04a:41424303,10f04e:00000005,10f052:41424304,10f056:80000000,10f05a:41424305,10f05e:00000000,10f062:41424306,10f066:00001000,10f06a:41424307,10f06e:00000005,10f072:41424308,10f076:00000000,10f07a:41424309,10f07e:00000005,10f082:4142430a",{0xffffffff,0x7f,0xffffffff,0xb1b448c2,0xffff,0x46fec1f4,0xb,0xe9caf3a9},0x10c002,0x10f02e},
 {"10e012:f0,10e015:80,10e060:03,10e080:01,10e098:09,10e09d:10,10e0a3:00,10e0a6:00,10e0a8:01,10e01e:1001,10e068:0000,10e07a:ffff,10e07c:0001,10e036:00000000,10e064:00010000,10e07a:0000288c,10c000:0000,10c002:0040,10c004:0080,10c006:ffff,10c008:0000,10c00a:0080,10f02e:00000005,10f032:41424300,10f036:80000000,10f03a:41424301,10f03e:00001000,10f042:41424302,10f046:00001000,10f04a:41424303,10f04e:00103400,10f052:41424304,10f056:00000005,10f05a:41424305,10f05e:80000000,10f062:41424306,10f066:00001000,10f06a:41424307,10f06e:00000000,10f072:41424308,10f076:80000000,10f07a:41424309,10f07e:80000000,10f082:4142430a",{0xffffff00,0x10000,0x22d82c15,0x3f,0x5ce10811,0x12345678,0x6d48a6e0,0x282d1199},0x10d000,0x10c004},
 {"10e015:81,10e060:00,10e098:09,10e0a1:40,10e0a2:00,10e0a6:05,10e0a8:ff,10e01e:1001,10e020:0000,10e068:fff1,10e078:0009,10e07a:0001,10e07c:0000,10e07e:0005,10e022:00000000,10e03a:00000000,10e00c:0010d000,10d062:00,10d080:ff,10c000:0010,10c002:1234,10c004:0000,10c006:ffff,10c008:0080,10c00a:0000,10f02e:00001000,10f032:41424300,10f036:00000000,10f03a:41424301,10f03e:00000000,10f042:41424302,10f046:00001000,10f04a:41424303,10f04e:00001000,10f052:41424304,10f056:80000000,10f05a:41424305,10f05e:80000000,10f062:41424306,10f066:00000005,10f06a:41424307,10f06e:80000000,10f072:41424308,10f076:80000000,10f07a:41424309,10f07e:00000005,10f082:4142430a",{0x8d40ab44,0x1ff,0xffff,0x10,0x12345678,0x4,0x40,0x77666344},0x10c400,0x10c004},
 {"10e080:01,10e0a1:80,10e0a2:05,10e0a6:00,10e0a8:02,10e020:00ea,10e078:0000,10e00c:0010d000,10d062:5a,10d080:ff,10c000:0080,10c002:0000,10c004:0010,10c006:0010,10c008:1234,10c00a:ffff,10f02e:00001000,10f032:41424300,10f036:00000005,10f03a:41424301,10f03e:00001000,10f042:41424302,10f046:00000000,10f04a:41424303,10f04e:00103400,10f052:41424304,10f056:00001000,10f05a:41424305,10f05e:00001000,10f062:41424306,10f066:00100400,10f06a:41424307,10f06e:80000000,10f072:41424308,10f076:000fe400,10f07a:41424309,10f07e:000fd400,10f082:4142430a",{0x4bf8b13b,0xb,0x5,0xc34638c2,0x3f,0x4,0x12345678,0xb},0x10c400,0x10c000},
 {"10e012:00,10e015:01,10e080:01,10e0a2:00,10e0a3:06,10e0a6:ff,10e020:00ea,10e068:fff1,10e076:0000,10e07a:0002,10e07c:0000,10e07e:0005,10e036:00000000,10e064:00010000,10e00c:0010d000,10d062:5a,10d080:00,10c000:0010,10c002:0010,10c004:1234,10c006:0040,10c008:0080,10c00a:0010,10f000:12348765,10f004:00000000,10f008:000ff000",{0xffff,0xffffff00,0x5ef437ba,0xa,0x0,0xbdb97bd2,0x1ff,0xffff},0x10c000,0x10f02e},
 {"10e0a6:00,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e0a6:01,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e09d:ef,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e09d:10,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e0a6:01,10e0a8:03,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e0a6:01,10e0a8:04,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x8000,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x8000,0x0,0x0,0x0,0x0,0x80},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x3f},0x10c400,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x40},0x10c400,0x10c000},
 {"10e0a8:00,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x2},0x10c400,0x10c000},
 {"10e0a8:01,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x2},0x10c400,0x10c000},
 {"10e0a8:02,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x2},0x10c400,0x10c000},
 {"10e0a8:ff,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x2},0x10c400,0x10c000},
 {"10e036:80000000,10e03a:7fff0000,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e036:7fffffff,10e03a:fffe0000,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e0a1:00,10e00c:0010d000",{0x7f,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e0a1:80,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e0a1:ff,10e00c:0010d000",{0xff,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x8000,0x1,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0xffff,0xfffe,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x100,0x200,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x2,0x1ff,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0xff,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0xff,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x40,0x40,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x40,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x40,0x0,0x0,0xff,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x40,0x0,0xff,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x40,0x0,0xff,0xff,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07a:00000000,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07a:0000288c,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x7f,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07c:0000,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07c:0001,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07a:0000,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07a:0001,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e07a:ffff,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e076:0001,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e076:0002,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e076:0000,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e012:ef,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e012:f0,10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x9},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xa},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xffff},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x9,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10f02e},
 {"10e00c:0010d000",{0x0,0xffff,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10f02e},
 {"10e00c:0010d000",{0x1,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0xb,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
 {"10e00c:0010d000",{0x1,0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x10c000,0x10c000},
};
const Row ROWS[]={
 {0x3abee,0,0,0x3ac12,0x5ebf83f0a6a5c458ULL},
 {0x3abee,2,0,0x3abf6,0x4a3ef069a562c89eULL},
 {0x3abf6,0,0,0x3ac12,0x5ebf83f0a6a5c458ULL},
 {0x3abf6,1,0,0x3ac00,0x1defd6a33b4d6803ULL},
 {0x3ac00,0,0,0x3ac12,0x18399cb0e8a8700aULL},
 {0x3ac12,0,0,0x3ac1c,0x2d7541e9a0057fc6ULL},
 {0x3ac12,2,0,0x3ac1a,0xcf1032190f86161fULL},
 {0x3ac1a,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0x3ac1c,0,0,0x3ac58,0xb9b3d5c47a33b784ULL},
 {0x3ac1c,1,0,0x3ac2c,0xd3d101bcc4da1fb7ULL},
 {0x3ac2c,0,0,0x2986,0x9df847e37c108277ULL},
 {0x3ac44,0,0,0x3b48c,0xd9b7e34c41e055d8ULL},
 {0x3ac48,0,0,0x4970a,0xaa2310591763acb9ULL},
 {0x3ac56,0,0,0x3ac58,0x79e2eea7424f8694ULL},
 {0x3ac58,0,0,0x2986,0x58b181174b660518ULL},
 {0x3ac76,0,1,0x3acd4,0xf17294a0e1292d58ULL},
 {0x3ac76,0,2,0x3ac7c,0x83c6ac95706535b0ULL},
 {0x3ac7c,0,0,0x3b48c,0xc5ea82cb02feec8fULL},
 {0x3ac8a,0,0,0x3aca0,0xe42fa931ff1a2dbcULL},
 {0x3ac8a,1,0,0x3ac98,0x8c1a3d32877f00a1ULL},
 {0x3ac98,0,0,0x3aca0,0xb5cb79b09a228737ULL},
 {0x3aca0,0,0,0x3acc6,0x1716a061a7e3f4a5ULL},
 {0x3aca0,3,0,0x3acb2,0x4cd207df7ea2090eULL},
 {0x3acb2,0,0,0x3acc6,0x900153499367829ULL},
 {0x3acc6,0,0,0x4c2fa,0x9900841a61f4ea48ULL},
 {0x3acd4,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0x3b458,0,0,0x44602,0x9391b3077f402ca1ULL},
 {0x3b46c,1,0,0xff000,0x26833a3ff99b0715ULL},
 {0x3b62a,0,0,0x3b63a,0x6420c9a0e6d6ed04ULL},
 {0x3b62a,1,0,0x3b638,0x266dccf933fc02d6ULL},
 {0x3b638,0,0,0x3b63a,0x7b7b7979d5cea987ULL},
 {0x3b63a,0,0,0x3b288,0xe0eef3d3ebf12754ULL},
 {0x3b642,1,0,0xff000,0xe26b357732079f9aULL},
 {0x3b648,1,0,0xff000,0xfd651c62fc2d4946ULL},
 {0x3b656,0,0,0x28ae,0x948deb743c3f636eULL},
 {0x3b666,0,1,0x3b67c,0x635c44bd78796780ULL},
 {0x3b666,0,2,0x3b66a,0x818d1b0ac15c59c6ULL},
 {0x3b66a,0,0,0x4970a,0x9c0fa34cd6f152cULL},
 {0x3b678,0,0,0x3b67c,0x635c44bd78796780ULL},
 {0x3b67c,1,0,0xff000,0xce71d0a063c6467ULL},
 {0x44602,0,0,0x44620,0x696d05b2586b96b5ULL},
 {0x44602,6,0,0x4461c,0xc598fbb3d5d01decULL},
 {0x4461c,0,0,0x4463c,0x5b16f827e6f559e9ULL},
 {0x44620,0,0,0x4462a,0xccef4aa643dcc0cULL},
 {0x44620,3,0,0x44626,0x9aa95ace856fdbf0ULL},
 {0x44626,0,0,0x4463c,0xe0ecfc91a5b5f4a9ULL},
 {0x4462a,3,0,0x4463c,0x3b89201f91ef237dULL},
 {0x4463c,1,0,0xff000,0xea62fc7d007dd41dULL},
 {0x4db18,0,0,0x28ae,0x8424c8396a104dccULL},
 {0x4db34,0,0,0xff000,0xbcbd26b5124552cULL},
 {0x4db34,1,0,0x0,0x61b79bc62a58b7f7ULL},
 {0x4dbdc,0,0,0x49f8c,0x302bba2406f17598ULL},
 {0x4dbfa,0,0,0x8ebe,0x69dd86d84841781dULL},
 {0x4dc08,0,0,0x49290,0x5a412d73258b6c12ULL},
 {0x4dc22,0,0,0x4dc28,0x12f41a7be6d7e995ULL},
 {0x4dc28,0,0,0x43e34,0xed4c37459fb95b88ULL},
 {0x4dc2e,0,0,0x49fc6,0x944f92142362251fULL},
 {0x4dc34,0,1,0x4dc38,0x13fd33f12c36715dULL},
 {0x4dc34,0,2,0x4dc60,0x258beaf43dacccd5ULL},
 {0x4dc38,0,0,0x4dc40,0x7b7e4921ebde8db5ULL},
 {0x4dc38,3,0,0x4dc4a,0xc115fa4a6e23470ULL},
 {0x4dc40,1,0,0x288c,0x37ba1ae026ee4bb1ULL},
 {0x4dc40,3,0,0x0,0xae9dbf2c70700f1dULL},
 {0x4dc40,7,0,0x10000,0x70e101aa10d73dc1ULL},
 {0x4dc40,9,0,0x20000,0xaab839105aee5d7ULL},
 {0x4dc46,0,1,0x4dc4a,0xe79f830cd7fdbfffULL},
 {0x4dc46,0,2,0x4dc60,0x258beaf43dacccd5ULL},
 {0x4dc4a,0,0,0x288c,0xa6ec647e79ad9df0ULL},
 {0x4dc50,0,1,0x4dc60,0x258beaf43dacccd5ULL},
 {0x4dc50,0,2,0x4dc54,0xa33bd54c13a02921ULL},
 {0x4dc54,0,0,0x4d900,0xad97c792f2e652bbULL},
 {0x4dc58,0,0,0x4dc60,0x258beaf43dacccd5ULL},
 {0x4dc58,3,0,0x4dc5e,0x25a21137c34e10c4ULL},
 {0x4dc5e,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0x4dc60,0,0,0x2a00,0x83d4cabbaeb2f937ULL},
 {0xe66aa,0,0,0xe6756,0xc4602cfa9fff8b9bULL},
 {0xe66ae,0,0,0x28ae,0x5f6ff6c6969578deULL},
 {0xe66be,0,0,0x49260,0x5679c1676bab8a0ULL},
 {0xe66cc,0,0,0xe66ee,0x53bb19442bba172dULL},
 {0xe66ee,0,0,0xe6746,0x54a11d363e2a6114ULL},
 {0xe66ee,2,0,0xe66f6,0xc73ca71a261c55c0ULL},
 {0xe66f6,0,0,0xe6898,0xc37948d92b03d7cULL},
 {0xe66fa,0,0,0xe6746,0x225f14d5baa107b5ULL},
 {0xe66fa,3,0,0xe6702,0xa6d63bcdab915a05ULL},
 {0xe6702,0,0,0xe6714,0x8a16cdc6a2abe98fULL},
 {0xe6702,1,0,0xe6726,0x8743cb98b3d8b6bcULL},
 {0xe6714,0,0,0xe671e,0xb8c055faf7b1e10cULL},
 {0xe6714,5,0,0xe6722,0x836c3e2b5aeec9aULL},
 {0xe671e,0,0,0xe6722,0xab4e9b05aa2de007ULL},
 {0xe6722,0,0,0xe6726,0x8ecd2f3c83a9926dULL},
 {0xe6726,0,0,0xe6784,0x66e83ebfaf863b75ULL},
 {0xe672e,0,0,0xe673e,0x8c1638ae1d88b26cULL},
 {0xe672e,5,0,0xe6738,0x9c1589f7c98fba50ULL},
 {0xe6738,0,0,0xe673e,0x78f08206854cf67dULL},
 {0xe673e,0,0,0xe6748,0xb0118c3adc623fc3ULL},
 {0xe673e,1,0,0xe6746,0x9a756f40b8f5f700ULL},
 {0xe6746,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0xe6748,0,0,0x2a00,0xc5e8fb4e0d1c18cULL},
 {0xe6756,0,0,0x8e82,0x57b1f6846d9064b7ULL},
 {0xe675c,0,0,0xe7c36,0x67aa4cf308ee9d39ULL},
 {0xe6762,0,0,0x1a5a4,0xaba5da759bcbeff0ULL},
 {0xe676e,0,0,0x47570,0x47c83ba22a4f9250ULL},
 {0xe6774,0,0,0x8c16,0x8208723e48991337ULL},
 {0xe6782,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0xe6784,0,0,0xe682e,0xe30d41a459c35207ULL},
 {0xe678c,3,0,0xe84c8,0x6eb2d326c1bf6224ULL},
 {0xe67b0,0,0,0xe84c8,0x9be78730d54dc498ULL},
 {0xe67c0,0,0,0xe84c8,0x917e21dde88adc39ULL},
 {0xe67c8,0,0,0xe84c8,0x3e13bd4db1673181ULL},
 {0xe67d0,0,0,0x3670,0x25796a2511c19c64ULL},
 {0xe67fe,0,0,0xe681e,0x76e603cca653fb81ULL},
 {0xe681e,0,0,0xe84c8,0x626e2b316e4dee02ULL},
 {0xe6826,0,0,0xe681e,0x5d2601920064f834ULL},
 {0xe6826,3,0,0xe682a,0xddec144e62cfe718ULL},
 {0xe682a,4,0,0xff000,0x41f22681057e9cf2ULL},
 {0xe682e,0,0,0xe6836,0x85c373c740af94e5ULL},
 {0xe682e,3,0,0xe6854,0x533f86bfa66b9280ULL},
 {0xe6854,0,0,0xe6870,0x2019cc7328b8b104ULL},
 {0xe6870,0,0,0xe6878,0xcf8617dac265702ULL},
 {0xe6870,1,0,0xe687c,0xef068aeb1cb68c11ULL},
 {0xe6878,0,0,0xe687c,0x71a6be7920f78d00ULL},
 {0xe687c,0,0,0xe6884,0xad810687901361c7ULL},
 {0xe687c,8,0,0xe6882,0x67915e5468bb0475ULL},
 {0xe6882,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0xe6884,0,0,0xe6870,0xea8d3403e5782c42ULL},
 {0xe6884,2,0,0xe6890,0x7a9954f659166fe7ULL},
 {0xe6898,0,0,0xe89da,0x81ac54a6f68bfcc8ULL},
 {0xe68aa,0,0,0xe89da,0x6244400e8308ae75ULL},
 {0xe68b8,0,0,0xe89da,0x2e3874119f1e170cULL},
 {0xe68c6,0,0,0x49a58,0x58586e467c0d28f4ULL},
 {0xe68cc,0,0,0x49f8c,0x40e2e60db1a182fULL},
 {0xe68ec,0,0,0x8ebe,0x162988e136bacd27ULL},
 {0xe68fa,0,0,0x43e34,0xa13a032f632761bULL},
 {0xe6910,0,0,0xe6916,0x334f4bc47cf624c1ULL},
 {0xe6916,0,0,0xe6920,0x91ccf4165da671a8ULL},
 {0xe6916,3,0,0xe6932,0x8084f3319a42ef4dULL},
 {0xe6920,0,0,0xe6932,0x44fe88542539e9b9ULL},
 {0xe6932,0,0,0x49fc6,0x48c328766ac72cdeULL},
 {0xe6938,1,0,0xff000,0xf765f6458b0bf0fULL},
 {0xe89da,0,0,0x3918,0x6569422d8344c7d4ULL},
 {0x3abee,10,0,0x3abf6,0xbfb5f41f60c002caULL},
 {0x3abee,11,0,0x3ac12,0x4018d879db6ee5ccULL},
 {0x3abf6,12,0,0x3ac12,0xed2a637441b2e6a4ULL},
 {0x3abf6,13,0,0x3ac00,0xc3cdfe8708255171ULL},
 {0x3ac1c,14,0,0x3ac58,0x83b2bfe99f89e0fbULL},
 {0x3ac1c,15,0,0x3ac2c,0x9ae1233f1018191ULL},
 {0x3ac98,16,0,0x3aca0,0x86089c5a7d5b7441ULL},
 {0x3ac98,17,0,0x3aca0,0x461418b2234f5bc1ULL},
 {0x3aca0,18,0,0x3acc6,0x78ae4367a64f5893ULL},
 {0x3aca0,19,0,0x3acb2,0x3368fd840662cb0dULL},
 {0x3acb2,20,0,0x3acc6,0xbceb2de6a876241aULL},
 {0x3acb2,21,0,0x3acc6,0xb03f3d53f4849e56ULL},
 {0x3acb2,22,0,0x3acc6,0xd9a30d304806c2d3ULL},
 {0x3acb2,23,0,0x3acc6,0x8dd16380e92ffc43ULL},
 {0x3b458,24,0,0x44602,0x7bc569ecbef06cddULL},
 {0x3b458,25,0,0x44602,0xc94eeeedefad5c25ULL},
 {0x3b46c,26,0,0xff000,0x7929ab4bc6ee7264ULL},
 {0x3b46c,27,0,0xff000,0xd8a707960dbb003ULL},
 {0x3b46c,28,0,0xff000,0x3effec1a4cb72067ULL},
 {0x44602,29,0,0x4461c,0x90431f51c5d5160fULL},
 {0x44602,30,0,0x4461c,0xcf7df62ce3b3d52cULL},
 {0x44602,31,0,0x44620,0x64b899fea09062e6ULL},
 {0x44602,32,0,0x4461c,0xbe9e4524eb257e8fULL},
 {0x44602,33,0,0x44620,0x168e1e130a1e050dULL},
 {0x4462a,34,0,0x4463c,0x364963ba11bad988ULL},
 {0x4462a,35,0,0x4463c,0xd1a159d6598d1471ULL},
 {0x4462a,36,0,0x4463c,0x55adc2e4e658b8aeULL},
 {0x4463c,37,0,0xff000,0x14fa037922c79e3dULL},
 {0x4463c,38,0,0xff000,0x959ebc67df7aa77aULL},
 {0x4463c,39,0,0xff000,0x53fa4758e276607aULL},
 {0x4463c,40,0,0xff000,0x569e78881fcbe53dULL},
 {0x4dc38,41,0,0x4dc4a,0x8b874e666ef46a54ULL},
 {0x4dc38,42,0,0x4dc40,0xf4d457c7f2f1c10aULL},
 {0x4dc58,43,0,0x4dc5e,0xcf275131cd230fULL},
 {0x4dc58,44,0,0x4dc60,0xaf4dd298fc4ff0ceULL},
 {0xe66fa,45,0,0xe6702,0xdef04515bfa464e1ULL},
 {0xe66fa,46,0,0xe6746,0x8ae8f8c828d246b3ULL},
 {0xe6702,47,0,0xe6726,0x1c9e4a2219fdf28aULL},
 {0xe6702,48,0,0xe6714,0xbfb31816d5d68a27ULL},
 {0xe6702,49,0,0xe6726,0x5e3edb7b4ea91813ULL},
 {0xe673e,50,0,0xe6748,0xf70a32b314f178fdULL},
 {0xe673e,51,0,0xe6746,0xd261c0b07dda03daULL},
 {0xe673e,52,0,0xe6746,0xf699231e8a2e0235ULL},
 {0xe6916,53,0,0xe6932,0xa7bc3b0a7a2be608ULL},
 {0xe6916,54,0,0xe6920,0xe565c1f084f9c00bULL},
 {0xe682e,55,0,0xe6854,0x14d3935837213175ULL},
 {0xe682e,56,0,0xe6836,0xe99c752f4a8b467cULL},
 {0xe682e,57,0,0xe6854,0x1be1c97147cef9aULL},
 {0xe6884,58,0,0xe6870,0xbfb9de04b25163acULL},
 {0xe6884,59,0,0xe6870,0x55f8df964e256ae6ULL},
 {0xe678c,60,0,0xe84c8,0xb65de9d64e204e2dULL},
 {0xe678c,61,0,0xe84c8,0xb82915c1bc121f3dULL},
 {0xe6826,62,0,0xe682a,0xba450568f7916b14ULL},
 {0xe6826,63,0,0xe681e,0xacaa5ed23137cbaeULL},
 {0xe68cc,64,0,0x49f8c,0x8e02a6127f0eb175ULL},
 {0xe68cc,65,0,0x49f8c,0x6bd3115544c8a866ULL},
};
const Synthetic SYNTHETIC[]={
 {0x44380,"1d5287bcf1265b90c5fa2f6499ce03386da2d70c4176abe0154a7fb4e91e5388bdf2275c91c6fb30659acf04396ea3d80d4277ace1164b80b5ea1f5489bef3285d92c7fc31669bd0053a6fa4d90e4378ade2174c81b6eb20558abff4295e93c8fd32679cd1063b70a5da0f4479aee3184d82b7ec21568bc0f52a5f94c9fe33689dd2073c71a6db10457aafe4194e83b8ed22578cc1f62b6095caff34699ed3083d72a7dc11467bb0e51a4f84b9ee23588dc2f72c6196cb00356a9fd4093e73a8dd12477cb1e61b5085baef24598ec3f82d6297cc01366ba0d50a3f74a9de13487db2e71c5186bbf0255a8fc4f92e6398cd02376ca1d60b4075aadf14497eb3e81d5287bcf1265b90c5fa2f6499ce03386da2d70c4176abe0154a7fb4e91e5388bdf2275c91c6fb30659acf04396ea3d80d4277ace1164b80b5ea1f5489bef3285d92c7fc31669bd0053a6fa4d90e4378ade2174c81b6eb20558abff4295e93c8fd32679cd1063b70a5da0f4479aee3184d82b7ec21568bc0f52a5f94c9fe33689dd2073c71a6db10457aafe4194e83b8ed22578cc1f62b6095caff34699ed3083d72a7dc11467bb0e51a4f84b9ee23588dc2f72c6196cb00356a9fd4093e73a8dd12477cb1e61b5085baef24598ec3f82d6297cc01366ba0d50a3f74a9de13487db2e71c5186bbf0255a8fc4f92e6398cd02376ca1d60b4075aadf14497eb3e81d5287bcf1265b90c5fa2f6499ce03386da2d70c4176abe0154a7fb4e91e5388bdf2275c91c6fb30659acf04396ea3d80d4277ace1164b80b5ea1f5489bef3285d92c7fc31669bd0053a6fa4d90e4378ade2174c81b6eb20558abff4295e93c8fd32679cd1063b70a5da0f4479aee3184d82b7ec21568bc0f52a5f94c9fe33689dd2"},
 {0xe637a,"000e63a6000e63aa000e63ae000e63b2000e63b6000e63ba000e63be000e63c2000e63c6000e63ca000e63ce"},
 {0xe63a6,"303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b"},
 {0xe63e4,"0003c0000003c100"},
 {0x200000,"0b30557a9fc4e90e33587da2c7ec11365b80a5caef14395e83a8cdf2173c6186abd0f51a3f6489aed3f81d42678cb1d6fb20456a8fb4d9fe23486d92b7dc01264b7095badf04294e7398bde2072c51769bc0e50a2f54799ec3e80d32577ca1c6eb10355a7fa4c9ee13385d82a7ccf1163b6085aacff4193e6388add2f71c41668bb0d5fa1f44698eb3d8fd22476c91b6db00254a6f94b9de03284d7297bce1062b50759abfe4092e53789dc2e70c31567ba0c5ea0f34597ea3c8ed12375c81a6cbf0153a5f84a9cef3183d6287acd1f61b40658aafd4f91e43688db2d7fc21466b90b5daff24496e93b8dd02274c7196bbe0052a4f7499bee3082d52779cc1e6"},
};
const std::uint32_t STARTS[]={0x3abee,0x3abf6,0x3ac00,0x3ac12,0x3ac1a,0x3ac1c,0x3ac2c,0x3ac44,0x3ac48,0x3ac56,0x3ac58,0x3ac76,0x3ac7c,0x3ac8a,0x3ac98,0x3aca0,0x3acb2,0x3acc6,0x3acd4,0x3b458,0x3b46c,0x3b62a,0x3b638,0x3b63a,0x3b642,0x3b648,0x3b656,0x3b666,0x3b66a,0x3b678,0x3b67c,0x44602,0x4461c,0x44620,0x44626,0x4462a,0x4463c,0x4db18,0x4db34,0x4dbdc,0x4dbfa,0x4dc08,0x4dc22,0x4dc28,0x4dc2e,0x4dc34,0x4dc38,0x4dc40,0x4dc46,0x4dc4a,0x4dc50,0x4dc54,0x4dc58,0x4dc5e,0x4dc60,0xe66aa,0xe66ae,0xe66be,0xe66cc,0xe66ee,0xe66f6,0xe66fa,0xe6702,0xe6714,0xe671e,0xe6722,0xe6726,0xe672e,0xe6738,0xe673e,0xe6746,0xe6748,0xe6756,0xe675c,0xe6762,0xe676e,0xe6774,0xe6782,0xe6784,0xe678c,0xe67b0,0xe67c0,0xe67c8,0xe67d0,0xe67fe,0xe681e,0xe6826,0xe682a,0xe682e,0xe6854,0xe6870,0xe6878,0xe687c,0xe6882,0xe6884,0xe6890,0xe6898,0xe68aa,0xe68b8,0xe68c6,0xe68cc,0xe68ec,0xe68fa,0xe6910,0xe6916,0xe6920,0xe6932,0xe6938,0xe89da};
// ---- generated tables (end)
const unsigned int WORLD_COUNT=sizeof(WORLDS)/sizeof(WORLDS[0]);
const unsigned int ROW_COUNT=sizeof(ROWS)/sizeof(ROWS[0]);
const unsigned int SYNTHETIC_COUNT=sizeof(SYNTHETIC)/sizeof(SYNTHETIC[0]);
const unsigned int START_COUNT=sizeof(STARTS)/sizeof(STARTS[0]);
const std::uint32_t CONSUMERS[]={0x3ac76,0x3b666,0x4dc34,0x4dc46,0x4dc50};
const unsigned int CONSUMER_COUNT=sizeof(CONSUMERS)/sizeof(CONSUMERS[0]);
const std::uint32_t ERROR_ONLY=0xe6890;      // MOVE.W #1,1.w (odd WORD write): no native row, a checked error
const std::uint32_t RANGES[][2]={{0x3abee,0x3acd6},{0x3b458,0x3b48c},{0x3b62a,0x3b68a},{0x44602,0x4464a},{0x4db18,0x4db42},{0x4dbdc,0x4dc66},
 {0xe66aa,0xe6836},{0xe6854,0xe6896},{0xe6898,0xe693a},{0xe89da,0xe89e4}};
const unsigned int RANGE_COUNT=sizeof(RANGES)/sizeof(RANGES[0]);
// Routed callees and exits outside the unit (the rows only stop there), the TRAP boundary e6836 and the return LONG STOP.
const std::uint32_t BOUNDARIES[]={0x2986,0x3b48c,0x4970a,0x4c2fa,0x3b288,0x28ae,0x49f8c,0x8ebe,0x49290,0x43e34,0x49fc6,0x288c,0x4d900,0x2a00,
 0x8e82,0xe7c36,0x1a5a4,0x47570,0x8c16,0xe84c8,0x3670,0x49260,0x49a58,0x3918,0xe6836,STOP};
const unsigned int BOUNDARY_COUNT=sizeof(BOUNDARIES)/sizeof(BOUNDARIES[0]);
bool in_list(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool is_start(std::uint32_t pc){return in_list(STARTS,START_COUNT,pc);}
bool is_consumer(std::uint32_t pc){return in_list(CONSUMERS,CONSUMER_COUNT,pc);}
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
// Digest: RAM, D0-D7, A0-A7, PC, bank, reads (BE LONGs), status (no port).
unsigned long long digest(const Bytes&ram,const State&s,std::uint32_t bank,std::uint32_t reads,ms5::AnimationMachineStatus status){
 Bytes tail;for(unsigned int i=0;i<8;++i)long_be(tail,s.d[i]);for(unsigned int i=0;i<8;++i)long_be(tail,s.a[i]);
 long_be(tail,s.pc);long_be(tail,bank);long_be(tail,reads);tail.push_back(static_cast<std::uint8_t>(status));
 return fnv_add(fnv_add(1469598103934665603ULL,ram),tail);}
// The synthetic world: fixed A2-A7, seeded D0-D7, A0 and A1 (or the defaults), entry PC and incoming C tag.
State state_of(const World*w,std::uint32_t pc,unsigned int carry){State s;
 for(unsigned int i=0;i<8;++i)s.d[i]=w?w->d[i]:0;
 s.a[0]=w?w->a0:ARGS;s.a[1]=w?w->a1:ARGS;s.a[2]=0x10c300;s.a[3]=0x10c200;s.a[4]=0x10c100;s.a[5]=A5;s.a[6]=NODE;s.a[7]=SP;s.pc=pc;s.carry=carry_of(carry);return s;}
// A run with declared puts and register edits to the expected stop (a checked success).
struct Run {Bytes ram;State s;};
Run go(std::uint32_t pc,const char*puts,const std::uint32_t*d,std::uint32_t a0,unsigned int carry,std::uint32_t stop){
 World w;w.puts=puts;for(unsigned int i=0;i<8;++i)w.d[i]=d?d[i]:0;w.a0=a0;w.a1=ARGS;
 Run r;r.ram=base_ram(puts);r.s=state_of(&w,pc,carry);Out o;
 if(!run(r.ram,r.s,stop,o)||r.s.pc!=stop||o.status!=ms5::AnimationMachineReturned||!o.ports.empty()||o.reads!=0){std::cerr<<std::hex<<pc<<" -> "<<stop<<" got "<<r.s.pc<<"\n";assert(false);}
 return r;}
Run go(std::uint32_t pc,const char*puts,std::uint32_t stop){return go(pc,puts,NULL,ARGS,0,stop);}
std::uint32_t ld(const Run&r,std::uint32_t address,unsigned int n){return get(r.ram,address,n);}
// A call pushed its return LONG: A7 = SP - 4 and the LONG there.
void called(const Run&r,std::uint32_t ret){assert(r.s.a[7]==SP-4&&ld(r,SP-4,4)==ret);}
// ---- generated rows: native successor and digest per block start / world / incoming C.
void rows(){
 unsigned int consumer_rows=0,boundary_hits=0;
 for(unsigned int i=0;i<ROW_COUNT;++i){const Row&r=ROWS[i];assert(r.world<WORLD_COUNT);const World&w=WORLDS[r.world];
  const bool consumer=is_consumer(r.pc);
  for(unsigned int c=0;c<3;++c){
   if(consumer&&c!=r.c)continue;
   Bytes ram=base_ram(w.puts);State s=state_of(&w,r.pc,c);Out o;
   if(!run(ram,s,r.next,o)||s.pc!=r.next){std::cerr<<std::hex<<r.pc<<" world "<<r.world<<"\n";assert(false);}
   const unsigned long long d=digest(ram,s,o.dev.bank_base,o.reads,o.status);
   if(d!=r.digest||o.status!=ms5::AnimationMachineReturned||!o.ports.empty()||o.reads!=0||o.dev.bank_base!=0x200000||o.dev.pvc!=pvc_base()){
    std::cerr<<std::hex<<r.pc<<" world "<<r.world<<" carry "<<c<<" digest "<<d<<" want "<<r.digest<<"\n";assert(false);}
   // Expected C: a consumer keeps the incoming C (its Bcc reads it, the block changes no flag the dispatcher tracks); every other block ends Unknown.
   const unsigned int expect=consumer?c:0U;
   if(s.carry!=carry_of(expect)){std::cerr<<std::hex<<r.pc<<" carry "<<s.carry<<" in "<<c<<" want "<<expect<<"\n";assert(false);}
   if(consumer)++consumer_rows;}
  if(in_list(BOUNDARIES,BOUNDARY_COUNT,r.next))++boundary_hits;
  assert(consumer==false||r.c==1U||r.c==2U);}
 assert(consumer_rows>=2*CONSUMER_COUNT&&boundary_hits>0);
}
// Every start (except the error-only e6890) is reached by at least one row; every boundary is the stop of at least one row; every consumer has both C rows.
void coverage(){
 assert(START_COUNT==109);
 for(unsigned int i=0;i<START_COUNT;++i){assert(in_ranges(STARTS[i])&&(STARTS[i]&1U)==0U);if(STARTS[i]==ERROR_ONLY)continue;bool found=false;
  for(unsigned int k=0;k<ROW_COUNT&&!found;++k)found=ROWS[k].pc==STARTS[i];
  if(!found){std::cerr<<std::hex<<"no row for "<<STARTS[i]<<"\n";assert(false);}}
 for(unsigned int b=0;b<BOUNDARY_COUNT;++b){bool found=false;for(unsigned int k=0;k<ROW_COUNT&&!found;++k)found=ROWS[k].next==BOUNDARIES[b];
  if(!found){std::cerr<<std::hex<<"no row stops at boundary "<<BOUNDARIES[b]<<"\n";assert(false);}}
 for(unsigned int c=0;c<CONSUMER_COUNT;++c){bool clear=false,set=false;std::uint32_t succ_clear=0,succ_set=0;
  for(unsigned int k=0;k<ROW_COUNT;++k)if(ROWS[k].pc==CONSUMERS[c]){if(ROWS[k].c==1){clear=true;succ_clear=ROWS[k].next;}if(ROWS[k].c==2){set=true;succ_set=ROWS[k].next;}}
  assert(clear&&set&&succ_clear!=succ_set&&is_start(succ_clear)&&is_start(succ_set));}
}
// Readable key facts (the digest rows above cover them too).
void key_facts(){
 // 3abee: BYTE a6 != 0 -> 3ac12; a6 = 0 -> 3abf6 (BTST #4,9d); 3ac12: a6 = 0 -> RTS.
 {go(0x3abee,"10e0a6:01",0x3ac12);go(0x3abee,"",0x3abf6);go(0x3ac12,"",STOP);}
 // 3ac00: 9d / 9e bit 4 cleared, a6 := 5, then 3ac12 -> 3ac1c (a6 -= 1 = 4; a8 & 3 = 0 -> 3ac2c: push A0, child 3ad48, JSR 2986).
 {const Run a=go(0x3ac00,"10e09d:ff,10e09e:10",0x3ac2c);assert(ld(a,NODE+0x9d,1)==0xef&&ld(a,NODE+0x9e,1)==0&&ld(a,NODE+0xa6,1)==4&&(a.s.d[7]&255U)==0);
  const Run b=go(0x3ac2c,"",0x2986);assert(b.s.a[0]==0x3ad48&&b.s.a[1]==0x100bf4&&(b.s.d[0]&65535U)==0x1e&&b.s.a[7]==SP-8&&ld(b,SP-8,4)==0x3ac44&&ld(b,SP-4,4)==ARGS);}
 // 3acb2: D0 = BYTE a8; DIVU.W #3; SWAP; SUBQ.W #1 (remainder - 1); MULS.W D7 (= 2); ADD.B to 76(A0).
 {const std::uint32_t d[8]={0,0,0,0,0,0,0,2};
  const Run a=go(0x3acb2,"10e0a8:03,10c476:10",d,CHILD,0,0x3acc6);assert(a.s.d[0]==0xfffffffeU&&ld(a,CHILD+0x76,1)==0x0e);     // 3 = 1*3 + 0 -> -1 * 2
  const Run b=go(0x3acb2,"10e0a8:05,10c476:10",d,CHILD,0,0x3acc6);assert(b.s.d[0]==2U&&ld(b,CHILD+0x76,1)==0x12);              // 5 = 1*3 + 2 -> 1 * 2
  const Run c=go(0x3acb2,"10e0a8:ff,10c476:10",d,CHILD,0,0x3acc6);assert(c.s.d[0]==0xfffffffeU&&ld(c,CHILD+0x76,1)==0x0e);}    // ff = 55*3 + 0
 // 3b648: D0.W := NOT WORD (A0); 9d / 9e &= D0.B.
 {const Run a=go(0x3b648,"10c000:0010,10e09d:ff,10e09e:31",STOP);assert((a.s.d[0]&65535U)==0xffef&&ld(a,NODE+0x9d,1)==0xef&&ld(a,NODE+0x9e,1)==0x21);}
 // 3b62a: D0 := LONG (A0) with the low WORD cleared, negated when BYTE 15 bit 0; LONG 64 := D0, JSR 3b288; 3b642 clears 64.
 {const Run a=go(0x3b62a,"10c000:00028765,10e015:01",0x3b288);assert(a.s.d[0]==0xfffe0000U&&ld(a,NODE+0x64,4)==0xfffe0000U);called(a,0x3b642);
  const Run b=go(0x3b642,"10e064:12345678",STOP);assert(ld(b,NODE+0x64,4)==0);}
 // 44602: (dx, dy) -> BYTE angle: (10, 0) -> 0; (0, 10) -> 40; (0, -10) -> c0; (-10, 0) -> 80 (D4.W := ff).
 {const std::uint32_t a[8]={0x10,0,0,0,0,0,0,0};const Run r=go(0x44602,"",a,ARGS,0,STOP);assert(r.s.d[0]==0&&(r.s.d[4]&65535U)==0xff);
  const std::uint32_t b[8]={0,0x10,0,0,0,0,0,0};const Run s=go(0x44602,"",b,ARGS,0,STOP);assert(s.s.d[0]==0x40);
  const std::uint32_t c[8]={0,0xfff0,0,0,0,0,0,0};const Run t=go(0x44602,"",c,ARGS,0,STOP);assert(t.s.d[0]==0xc0&&(t.s.d[3]&255U)==0xff);
  const std::uint32_t e[8]={0xfff0,0,0,0,0,0,0,0};const Run u=go(0x44602,"",e,ARGS,0,STOP);assert(u.s.d[0]==0x80&&(u.s.d[2]&255U)==0x80);}
 // 4db18: LONG 0, D1.W, D0.W stacked (D0.W lowest), A0 = 4dbdc, D0.W = a, JSR 28ae (return 4db34); 4db34 pops them into the child fields.
 {const std::uint32_t d[8]={0x11111234,0x22225678,0,0,0,0,0,0};const Run a=go(0x4db18,"",d,ARGS,0,0x28ae);
  assert(a.s.a[0]==0x4dbdc&&(a.s.d[0]&65535U)==0xa&&(a.s.d[0]>>16)==0x1111&&a.s.a[7]==SP-12&&ld(a,SP-12,4)==0x4db34&&ld(a,SP-8,2)==0x1234&&ld(a,SP-6,2)==0x5678&&
   ld(a,SP-4,4)==0);
  const Run b=go(0x4db34,"10f000:12348765,10f004:00000000,10f008:000ff000",NULL,CHILD,0,STOP);
  assert(ld(b,CHILD+0x76,2)==0x1234&&ld(b,CHILD+0x78,2)==0x8765&&ld(b,CHILD+0x7a,4)==0&&b.s.a[7]==SP+12);}
 // 4dc38: LONG 7a = 0 -> 4dc4a (JSR 288c); 4dc40: JSR (A1) with A1 = LONG 7a (live target).
 {go(0x4dc38,"",0x288c);const Run a=go(0x4dc38,"10e07a:0004d900",0x4d900);assert(a.s.a[1]==0x4d900);called(a,0x4dc46);}
 // e66cc: the display fields and the install of e66ee, which falls through (BYTE 80 = 0 -> RTS).
 {const Run a=go(0xe66cc,"10e07e:ffff,10e080:01",STOP);
  assert(ld(a,NODE+0x76,2)==0x5a&&ld(a,NODE+0x7e,2)==0&&ld(a,NODE+0x80,1)==0&&ld(a,NODE+0x7c,2)==1&&ld(a,NODE,4)==0xe66ee);}
 // e66fa: SUBQ.W #1,7c; BCC (no borrow) -> RTS; borrow -> e6702: 7c := 0, 7a += 1, 7a <= 1 -> e6726 (MOVE.W 78,D0; JSR e6784).
 {go(0xe66fa,"10e07c:0001",STOP);const Run a=go(0xe66fa,"10e078:0003",0xe6784);assert(ld(a,NODE+0x7c,2)==0&&ld(a,NODE+0x7a,2)==1&&(a.s.d[0]&65535U)==3);}
 // e673e: 76 -= 1; zero -> e6748: parent BYTE 62 := ff (the controller end request), JMP 2a00.
 {const Run a=go(0xe673e,"10e076:0001,10e00c:0010d000",0x2a00);assert(ld(a,NODE+0x76,2)==0&&ld(a,PARENT+0x62,1)==0xff&&a.s.a[0]==PARENT);}
 // e6854: rank of record D7 = 3 among the records (10f02e + 8k): one larger record before it -> D0 = 2; RTS at e6882 (D1 = D7 = 4).
 {const std::uint32_t d[8]={0,0,0,0,0,0,0,3};const Run a=go(0xe6854,"10f02e:0000000a,10f036:00000003,10f046:00000005",d,ARGS,0,STOP);
  assert((a.s.d[0]&65535U)==2&&(a.s.d[1]&65535U)==4&&(a.s.d[7]&65535U)==4&&a.s.d[3]==5);}
 // e682e: D7 >= a (signed) -> the TRAP #f at e6836 (a stop there succeeds).
 {const std::uint32_t d[8]={0,0,0,0,0,0,0,10};go(0xe682e,"",d,ARGS,0,0xe6836);}
 // e6916: BYTE 12 + 10 carries -> e6920: 12 := ff, parent BYTE 80 := ff, install e6932, JSR 49fc6 (return e6938).
 {const Run a=go(0xe6916,"10e012:f0,10e00c:0010d000",0x49fc6);assert(ld(a,NODE+0x12,1)==0xff&&ld(a,PARENT+0x80,1)==0xff&&ld(a,NODE,4)==0xe6932);called(a,0xe6938);
  const Run b=go(0xe6916,"10e012:ef",0x49fc6);assert(ld(b,NODE+0x12,1)==0xff&&ld(b,NODE,4)==0);}
 // e6826: DBRA D7 (WORD): 0 -> e682a; e682a pops the row WORD and returns.
 {const std::uint32_t d[8]={0,0,0,0,0,0,0,0x10000};const Run a=go(0xe6826,"",d,ARGS,0,0xe682a);assert(a.s.d[7]==0x1ffffU);
  const Run b=go(0xe682a,"10f000:0005000ff000",STOP);assert((b.s.d[0]&65535U)==5&&b.s.a[7]==SP+6);}
 // e6898 / e89da: title text via 3918 with A1 = e84c8.
 {const Run a=go(0xe68b8,"",0x3918);assert(a.s.a[0]==0xe63dc&&a.s.a[1]==0xe84c8&&(a.s.d[0]&65535U)==0x72c5);}
}
// Checked errors: every interior even PC of the ten ranges, odd range edges, unrouted work-RAM probe PCs (rollback), the unrouted neighbours and TRAP sites,
// the live JSR (A1) to a work-RAM PC / an odd PC, the odd WORD write of e6890, the TRAP without a stop PC, a 2986 allocation failure after earlier stores,
// and Unknown C into the five consumers.
void errors(){
 unsigned int even=0,inside=0;
 for(unsigned int r=0;r<RANGE_COUNT;++r)for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2){++even;
  if(is_start(pc))continue;Bytes ram=base_ram("");reject(ram,state_of(NULL,pc,2),STOP,"unsupported animation objects b2e PC");++inside;}
 assert(even==633&&inside==524);
 for(unsigned int r=0;r<RANGE_COUNT;++r){const std::uint32_t odd[]={RANGES[r][0]+1,RANGES[r][1]-1};
  for(unsigned int i=0;i<2;++i){Bytes ram=base_ram("");reject(ram,state_of(NULL,odd[i],2),STOP,"unaligned animation machine PC");}}
 // Rollback probes only in work RAM 10fe00..10fefe (code never executes in RAM; F4 unit test boundary convention).
 const std::uint32_t outside[]={0x10fe00,0x10fe40,0x10fefe};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram=base_ram("");reject(ram,state_of(NULL,outside[i],2),STOP,"unsupported animation machine PC");}
 // Review 0264 M-3: the probes without an executor are work-RAM PCs 10fe10..10fe2a; the ROM neighbours (data before / after the ranges, the TRAP sites e6836 / e6896,
 // the string e6838, the unreferenced 3b4e0) are only asserted to be outside the unit's own ranges.
 const std::uint32_t ends[]={0x3abec,0x3b68a,0x44600,0x4464a,0x4db16,0x4dc66,0xe66a8,0xe6836,0xe6838,0xe6896,0xe693a,0xe89d8,0xe89e4,0x3b4e0};
 for(unsigned int i=0;i<sizeof(ends)/sizeof(ends[0]);++i)assert(!in_ranges(ends[i]));
 for(unsigned int i=0;i<14;++i){Bytes ram=base_ram("");reject(ram,state_of(NULL,0x10fe10U+2U*i,2),STOP,"unsupported animation machine PC");}
 // JSR (A1) of 4dc40: a work-RAM target and an odd target (the failure keeps the pre-run state).
 {reject(base_ram("10e07a:0010fe00"),state_of(NULL,0x4dc40,0),STOP,"unsupported animation machine PC");
  reject(base_ram("10e07a:0004dc29"),state_of(NULL,0x4dc40,0),STOP,"unaligned animation machine PC");}
 // e6890: MOVE.W #1,1.w is an odd WORD write; e6884 with D1 = a reaches it; e682e with D7 = a goes to the TRAP e6836 (stop-only check, review 0264 M-3).
 {reject(base_ram(""),state_of(NULL,0xe6890,0),STOP,"invalid animation machine write size/alignment");
  State s=state_of(NULL,0xe6884,0);s.d[1]=10;s.a[1]=RECORDS;reject(base_ram(""),s,STOP,"invalid animation machine write size/alignment");
  State t=state_of(NULL,0xe682e,0);t.d[7]=0xffff000a;Bytes tr=base_ram("");Out to;assert(run(tr,t,0xe6836,to)&&t.pc==0xe6836);}
 // A failure after earlier stores: 3ac58 stores BYTE a3 and pushes A0, then 2986 / 28ae fails (WORD 104ca0 = 0 <= D0.W): the 2986 caller-X limitation is a
 // checked error and every store is rolled back.
 {reject(base_ram(""),state_of(NULL,0x3ac58,0),STOP,"cue wrapper failure requires known caller X");}
 // An odd install: 4dc22 at an odd A6.
 {State s=state_of(NULL,0x4dc22,0);s.a[6]=NODE+1U;reject(base_ram(""),s,STOP,"invalid animation machine write size/alignment");}
 // Unknown C into a consumer.
 for(unsigned int i=0;i<CONSUMER_COUNT;++i){Bytes ram=base_ram("");reject(ram,state_of(NULL,CONSUMERS[i],0),STOP,"objects b2e caller requires known carry");}
}
// Stopping at the entry PC executes nothing (state, RAM and device are unchanged) for every block start and every C tag.
void zero_step(){
 for(unsigned int c=0;c<3;++c)for(unsigned int i=0;i<START_COUNT;++i){Bytes ram=base_ram("");State s=state_of(NULL,STARTS[i],c);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,STARTS[i],o)&&same(s,old)&&ram==before&&o.ports.empty()&&o.reads==0&&
   o.status==ms5::AnimationMachineReturned&&o.dev.bank_base==0x200000);}
}
}
int main(){
 key_facts();rows();coverage();errors();zero_step();
 std::cout<<"animation machine objects b2e: "<<START_COUNT<<" blocks, "<<ROW_COUNT<<" rows, "<<calls<<" calls\n";
 return 0;
}
