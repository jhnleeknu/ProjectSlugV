#include "ms5/animation_machine.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
// 480bc frame helper U7 (frame buffer 4aa88 with the 4b784 two-sprite slot submission, cue e8a48 with the 2986
// allocation wrapper, e8ad0 stream walk and e8af4 position) and the whole 480bc->480f0 frame (U1..U7) through
// run_animation_machine only. All inputs are declared fixtures built below (zero RAM plus explicit puts, the return LONG
// at A7 and declared registers). The stack is the RAM mirror at 1feffc (RAM offset effc), the U1 observer convention;
// whole frames return to 2ac2. Synthetic typed physical bytes (not a ROM oracle): the U6 default mask row 49ab0 (contract
// bytes 10 20 40 80), the e8a0c table index 0..3 (contract bytes 0000 0002 0000 0001 0001 0001 0002 0001) and synthetic
// bytes for index 4..1f (e8a1c..e8a8c, code bytes in the ROM; only the index test reads them and derives its
// expectation from this row). The FIXTURES/PHASES/NEXT tables were produced from the original code bytes (Unicorn
// M68000 on the canonical BE ROM, stack mirrored into work RAM, no SR read) and every phase was cross-checked against
// this machine with the full physical ROM before being recorded; each fixture records the FNV-1a hash of the input RAM
// the generator used, so the builders below must reproduce it exactly. Carry after a case is machine bookkeeping.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef ms5::AnimationMachineState State;
const std::uint32_t U=0x1feffc,STOP=0xff000,A5=0x108000,RET_FRAME=0x2ac2,TABLE=0xe8a0c;
unsigned int calls=0;
struct Put {std::uint32_t address;unsigned int size;std::uint32_t value;};
struct Phase {unsigned int first_write,writes;std::uint32_t regs[16];std::uint32_t pc;unsigned int waiting,carry;std::uint32_t bank;
 const char* changes;const char* ports;};
struct Fixture {const char* name;unsigned int kind;std::uint32_t p[7];std::uint32_t entry,stop,bank;int carry_from;std::uint32_t a7;
 unsigned int carry;unsigned long long input_hash;unsigned int first_phase,phases;};
enum Kind {K_FRAME_MINIMAL,K_FRAME_CARRIED,K_FRAME_WRAP,K_FRAME_BUFFER_WAITS,K_FRAME_BUFFER_BANK3,K_FRAME_CUE_FAILURE,K_FRAME_CUE_SUCCESS,K_FRAME_CUE_DEBUG,K_FRAME_STREAM,K_BUFFER_CURSOR,K_BUFFER_BIT0,K_BUFFER_SLOTS16,K_BUFFER_SLOT15_CLIP,K_BUFFER_FIRST_WAIT,K_CUE_TAG,K_CUE_ALLOC,K_CUE_SUCCESS,K_CUE_STREAM,K_CUE_STREAM_NULL,K_CUE_DEBUG,K_CUE_DEBUG_NULL,K_CUE_ALIAS_SAME};
const Put WRITES[]={{0x108d34,2,0x4},{0x108d36,2,0x6},{0x108d34,2,0x6},{0x108d34,2,0x4},{0x106034,2,0x101},{0x106036,2,0x202},{0x102315,1,0x2},{0x108d34,2,0x4}};
const Phase PHASES[]={
{0,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d4ba,0x10dd98,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10efeb:01,10efed:01,10efef:01c030,10eff5:0b4aae,10eff9:0480f0",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{0,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d4ba,0x10dd98,0x10dd98,0x10d918,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "10d39a:00,10d3f6:01,10d3f8:02,10d744:00,10d746:00000000,10d812:00000000,10d916:0000,10db84:00,10db86:00,10dba8:5ab864646e0f77bb01660b1214bd1e69281431c03b6b45174ec2586e62196bc5,10dc8b:c8",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{0,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d4ba,0x10dd98,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "10d744:80,10dc8b:e8",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{0,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d4ba,0x10dd98,0x10dd98,0x10d918,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:00,10d746:00000000,10d812:00000000,10d916:0000,10db84:ff005a00,10dc8a:db88,10dd48:80,10dd50:80,10efeb:01,10efed:01,10efef:01c030,10eff5:0b4aae,10eff9:0480f0",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{0,0,{0x100080,0xffff0003,0x0,0x0,0xabcd0004,0xffffffff,0x2,0x122b,0xcd50,0x108b34,0x0,0xa3a3a3a3,0x10daf8,0x108000,0x102000,0x1fefd6},0xcda4,1,0,0x200000,
  "10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d68e:01,10d72a:ffff,10d730:ffff,10efd4:cd5e,10efd7:04b7da,10efdb:106004,10efe0:122bffff,10efe5:03,10efe7:10,10efe9:80,10efeb:04aad4,10eff1:10daf8,10eff5:10ab,10eff9:0480d2",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{0,0,{0x100080,0xffff0003,0x0,0x0,0xabcd0004,0xffffffff,0x2,0x122b,0xcd50,0x108b34,0x0,0xa3a3a3a3,0x10daf8,0x108000,0x102000,0x1fefd6},0xcda4,1,0,0x200000,
  "",
  ""},
{0,2,{0x60,0xffff0000,0xfff0,0xffe0,0xabcd0006,0xffffffff,0x4,0x122b,0xcd50,0x108b34,0x0,0xa3a3a3a3,0x10daf8,0x108000,0x102000,0x1fefe2},0xcda4,1,0,0x200000,
  "107f40:ffff04,107f44:ffff,107f47:0340,107f4a:122b,108b35:0c,108d39:02,108d3b:02,10efe0:cd5e0004b814,10efe8:6008",
  ""},
{2,0,{0x60,0xffff0000,0xfff0,0xffe0,0xabcd0006,0xffffffff,0x4,0x122b,0xcd50,0x108b34,0x0,0xa3a3a3a3,0x10daf8,0x108000,0x102000,0x1fefe2},0xcda4,1,0,0x200000,
  "",
  ""},
{2,1,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d4ba,0x10dd98,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "107f4c:ffff,107f50:ffff,107f54:30,107f56:122b,108b37:18,108d39:04,108d3b:04,10d67c:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10efef:01c0300000,10eff5:0b4aae,10effb:f0",
  "2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{3,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d4ba,0x10dd98,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "107f40:ffff0c,107f44:ffff,107f47:04a0,107f4a:122bffff10,107f50:ffff,107f53:07b0,107f56:122b,108b35:0c,108b37:18,108d39:04,108d3b:04,10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10efd4:cd5e,10efd7:04b7da,10efdb:106004,10efe0:cd5e,10efe3:04b814,10efe7:106008,10efeb:04aad4,10efef:01c030,10eff5:0b4aae,10eff9:0480f0",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{3,0,{0x120000,0x1340000,0x0,0x0,0x0,0x1000000,0x0,0x0,0x100f12,0xe8a10,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "100ec7:12,100ecb:34,100ed7:10d38e,100edb:12,100ede:0134,100ee3:12,100ee6:0134,100f11:02,10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10de2f:00,10efe8:298e,10efeb:102004,10efef:0e8a8a,10eff3:0e8a9c,10eff9:0480f0",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{3,0,{0xffff0000,0x1010000,0x0,0x0,0x0,0x1000000,0x0,0x0,0x10047a,0xe8a14,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf4,10042e:ffff,100433:01,10043f:10d38effff,100446:0101,10044a:ffff,10044e:0101,10046a:5a,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3bd:00,10d3c0:0000,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10de2f:00,10efe3:0d5f16,10efe8:298e,10efeb:102019,10efef:0e8a8a,10eff3:0e8a9c,10eff7:01,10eff9:0480f0",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{3,0,{0x100140,0xffff0000,0x0,0x0,0x4,0xffffffff,0x2,0xba2b,0xcd50,0x108b34,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1feff4},0xcda4,1,0,0x200000,
  "10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10efeb:01,10efed:01,10efef:01,10eff2:cd5e,10eff5:0e8b58,10eff9:0480ea",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{3,0,{0x100140,0xffff0000,0x0,0x0,0x4,0xffffffff,0x2,0xba2b,0xcd50,0x108b34,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1feff4},0xcda4,1,0,0x200000,
  "",
  ""},
{3,1,{0xffff0400,0xffff0000,0x0,0xc,0x2,0xffffffff,0x2,0xa000ba2b,0x107f40,0x108b34,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "107f40:ffff04,107f44:ffff,107f48:a0,107f4a:ba2b,108b35:0c,108d39:02,108d3b:02,10effb:f0",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x106224,0x106228,0x10dd98,0x10d746,0x10dcba,0x108000,0x10ab00,0x1ff000},0x2ac2,0,0,0x200000,
  "10d392:01,10d39a:01,10d3a6:01,10d3ae:01,10d3ce:7fff7fff80,10d3d4:80,10d3f4:0140,10d3f8:01,10d67c:ffff,10d68e:01,10d72a:ffff,10d730:ffff,10d744:80,10d918:00000000,10d9e4:00000000,10dae8:0000,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10dd48:80,10dd50:80,10de27:106228,10de2d:24,10efeb:01,10efed:01,10efef:01c030,10eff5:0e8aba,10eff9:0480f0",
  "2ffff2/2/2000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:95,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d918,0x10d746,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:15,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10db88,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:95,10db84:a5005a00,10dc68:7b0804b40e5f180b21b62b62350d3eb9486452105bbb65676f1278be02690c15,10dc8a:db88",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10db88,0x10e100,0xa2a2a2a2,0x10d918,0x10d746,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:15,10db84:a5005a00,10dc68:7b0804b40e5f180b21b62b62350d3eb9486452105bbb65676f1278be02690c15,10dc8a:db88",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10db88,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:95,10db84:a5005a00,10dc6a:04b40e5f180b21b62b62350d3eb9486452105bbb65676f1278be02690c15,10dc8a:db88",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10db88,0x10e100,0xa2a2a2a2,0x10d918,0x10d746,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:15,10db84:a5005a00,10dc6a:04b40e5f180b21b62b62350d3eb9486452105bbb65676f1278be02690c15,10dc8a:db88",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10db88,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:95,10db84:a5005a00,10dc86:0c15,10dc8a:db88",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10db88,0x10e100,0xa2a2a2a2,0x10d918,0x10d746,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:15,10db84:a5005a00,10dc86:0c15,10dc8a:db88",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x100020,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:95,10db84:a5005a00,10dc8b:20",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x100020,0x10e100,0xa2a2a2a2,0x10d918,0x10d746,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:15,10db84:a5005a00,10dc8b:20",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d764,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:8a80,10db84:a5005a00,10dc8b:64",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10d764,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:ca80,10db84:a5005a00,10dc8b:64",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba4,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:95,10db84:d2002d00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db6,10dc8b:a4",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba4,0x10e100,0xa2a2a2a2,0x10d918,0x10d746,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:15,10db84:d2002d00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db6,10dc8b:a4",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:ff005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:ff005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10eff9:10ab",
  ""},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10efd8:cd5e,10efdb:04b7da,10efdf:1060f4,10efe4:cd5e,10efe7:04b814,10efeb:1060f8,10efef:04aad4,10eff3:0f,10eff5:10db70,10eff9:10ab",
  "2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{4,0,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x10e100,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "10d744:80,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10efd8:cd5e,10efdb:04b7da,10efdf:1060f4,10efe4:cd5e,10efe7:04b814,10efeb:1060f8,10efef:04aad4,10eff3:0f,10eff5:10db70,10eff9:10ab",
  "2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{4,0,{0x100140,0xffff0001,0xabcd2222,0xabcd3333,0xabcd0004,0xffffffff,0xabcd0002,0x122b,0xcd50,0x108b34,0xa2a2a2a2,0xa3a3a3a3,0x10db10,0x108000,0x102300,0x1fefda},0xcda4,1,0,0x200000,
  "10efd8:cd5e,10efdb:04b7da,10efdf:106034,10efe4:122bffff,10efe9:01,10efeb:100140,10efef:04aad4,10eff3:03,10eff5:10db10,10eff9:10ab",
  ""},
{4,3,{0x100140,0xffff0001,0xabcd2222,0xabcd3333,0xabcd0004,0xffffffff,0xabcd0002,0x122b,0xcd50,0x108b34,0xa2a2a2a2,0xa3a3a3a3,0x10db10,0x108000,0x102300,0x1fefda},0xcda4,1,0,0x200000,
  "",
  ""},
{7,1,{0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x10dba8,0x108b34,0xa2a2a2a2,0x10d746,0x10d918,0x108000,0x10ab00,0x1ff000},0x480d2,0,0,0x200000,
  "107f40:ffff04,107f44:ffff,107f47:01a0,107f4a:122b,108b35:0c,108d39:02,108d3b:02,10d744:80,10db84:a5005a00400049ac53575d0366ae705a7a0503b10d5c170820b32a5f340a3db64761510d,10dc8b:a8,10efe4:cd5e0004b814,10efec:6038",
  "2ffff2/2/1000,2ffff0/2/0,2ffff2/2/1000,2ffff0/2/0"},
{8,0,{0xffff,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106000,0x10e100,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de2f:00",
  ""},
{8,0,{0x11110000,0x22220000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a10,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ec6:1111,100eca:2222,100ed7:10d38e1111,100ede:2222,100ee2:1111,100ee6:2222,100f11:02,10de2f:00,10efec:298e,10efef:102004,10eff3:0e8a8a,10eff7:0e8a9c",
  ""},
{8,0,{0x1111000c,0x22220000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a1c,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ec6:1111,100eca:2222,100ed7:10d38e1111,100ede:2222,100ee2:1111,100ee6:2222,100f0f:02,100f11:01,10de2f:00,10efec:298e,10efef:102004,10eff3:0e8a8a,10eff7:0e8a9c,10effb:03",
  ""},
{8,0,{0x20,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106000,0x10e100,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de2f:00",
  ""},
{8,0,{0xe3,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106000,0x10e100,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de2f:00",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ed7:10d38e,100f02:5a,100f0f:01,100f11:01,10de2f:00,10efec:298e,10efef:102004,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf41235,10043f:10d38e,10046a:5a,100477:01,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ed7:10d38e,100f02:5a,100f0f:01,100f11:01,10de2f:00,10efec:298e,10efef:102014,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf41235,10043f:10d38e,10046a:5a,100477:01,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ed7:10d38e,100f02:5a,100f0f:01,100f11:01,10de2f:00,10efec:298e,10efef:102014,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf41235,10043f:10d38e,10046a:5a,100477:01,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0xffff0000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100eca:ffff,100ed7:10d38e,100ede:ffff,100ee6:ffff,100f02:5a,100f0f:01,100f11:01,10de2f:00,10efec:298e,10efef:102004,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0xffff0000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf41235,100432:ffff,10043f:10d38e,100446:ffff,10044e:ffff,10046a:5a,100477:01,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ed7:10d38e,100f02:5a,100f0f:01,100f11:01,10de2f:00,10efec:298e,10efef:102014,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x8,0x0,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf41235,10043f:10d38e,10046a:5a,100477:01,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x7fff0008,0x80000000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100ec6:7fff,100eca:80,100ed7:10d38e7fff,100ede:80,100ee2:7fff,100ee6:80,100f02:5a,100f0f:01,100f11:01,10de2f:00,10efec:298e,10efef:102004,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x7fff0008,0x80000000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a18,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf41235,10042e:7fff,100432:80,10043f:10d38e7fff,100446:80,10044a:7fff,10044e:80,10046a:5a,100477:01,100479:01,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c,10effb:02",
  ""},
{8,0,{0x50000,0x60000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a10,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf4,10042f:05,100433:06,10043f:10d38e,100443:05,100447:06,10044b:05,10044f:06,10046a:5a,100479:02,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102015,10eff3:0e8a8a,10eff7:0e8a9c",
  ""},
{8,0,{0x50000,0x60000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a10,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf4,10042f:05,100433:06,10043f:10d38e,100443:05,100447:06,10044b:05,10044f:06,10046a:5a,100479:02,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102011,10eff3:0e8a8a,10eff7:0e8a9c",
  ""},
{8,0,{0x50000,0x60000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a10,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf4,100411:01,10042f:05,100433:06,10043f:10d38e,100443:05,100447:06,10044b:05,10044f:06,10046a:5a,100479:02,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102009,10eff3:0e8a8a,10eff7:0e8a9c",
  ""},
{8,0,{0x50000,0x60000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x10047a,0xe8a10,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "100401:0d5f16,100405:100bf4,10040a:08,10040d:100bf480,10042f:05,100433:06,10043f:10d38e,100443:05,100447:06,10044b:05,10044f:06,10046a:5a,100479:02,100806:0400,100bfe:04,104c9e:05,104ca1:03,10de2f:00,10efe7:0d5f16,10efec:298e,10efef:102001,10eff3:0e8a8a,10eff7:0e8a9c",
  ""},
{8,0,{0xabcd0002,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106218,0x10621c,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de28:621c,10de2d:18,10eff9:0e8aba",
  ""},
{8,0,{0xabcd0004,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106200,0x106204,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de28:6204,10eff9:0e8aba",
  ""},
{8,0,{0xabcdfffe,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106200,0x106204,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de28:6204,10eff9:0e8aba",
  ""},
{8,0,{0xabcd7fff,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x106200,0x106204,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de28:6204,10eff9:0e8aba",
  ""},
{8,0,{0xabcd0000,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x0,0x4,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10de27:000004,10eff9:0e8aba",
  ""},
{8,0,{0xffff0440,0xffff0000,0xabcd2222,0xabcd000c,0xabcd0002,0xffffffff,0xabcd0002,0xee80ba2b,0x107f40,0x108b34,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "107f40:ffff0440ffff,107f48:ee80ba2b,108b35:0c,108d39:02,108d3b:02,10eff6:cd5e,10eff9:0e8b58",
  ""},
{8,0,{0xffff0440,0xffff0000,0xabcd2222,0xabcd000c,0xabcd0002,0xffffffff,0xabcd0002,0xef00ba2b,0x107f40,0x108b34,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "107f40:ffff0440ffff,107f48:ef,107f4a:ba2b,108b35:0c,108d39:02,108d3b:02,10eff6:cd5e,10eff9:0e8b58",
  ""},
{8,0,{0x8000fffe,0xffff0000,0xabcd2222,0xabcd3333,0xabcd4444,0xffffffff,0xabcd6666,0xba2b,0xcd50,0x10d38e,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "10eff6:cd5e,10eff9:0e8b58",
  ""},
{8,0,{0xabcd0000,0xabcd1111,0xabcd2222,0xabcd3333,0xabcd4444,0xabcd5555,0xabcd6666,0xabcd7777,0x0,0x10d38e,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x1ff000},0x480ea,0,0,0x200000,
  "",
  ""},
{8,0,{0x70000,0x80000,0x0,0x0,0x0,0x0,0xabcd0000,0x0,0x100f12,0xe8a10,0xa2a2a2a2,0xa3a3a3a3,0x10e300,0x108000,0x10ab00,0x100f12},0x2,0,0,0x200000,
  "100ec7:07,100ecb:08,100ed7:10d38e,100edb:07,100edf:08,100ee3:07,100ee7:08,100efe:298e,100f01:102004,100f05:0e8a8a,100f09:0e8a9c,100f0f:000002,10de2f:00",
  ""}};
const Fixture FIXTURES[]={
{"frame-minimal",K_FRAME_MINIMAL,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0x0f4defd120a606c8ULL,0,1},
{"frame-carried",K_FRAME_CARRIED,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,0,0x1feffc,2,0x747c86944b93d3c4ULL,1,1},
{"frame-carried-2",K_FRAME_CARRIED,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,1,0x1feffc,2,0x0c22d04ab38d3251ULL,2,1},
{"frame-wrap-bit0",K_FRAME_WRAP,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0x77e18c87ece3be00ULL,3,1},
{"frame-buffer-waits",K_FRAME_BUFFER_WAITS,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0x381eb7665806b4bdULL,4,5},
{"frame-buffer-bank3",K_FRAME_BUFFER_BANK3,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x300000,-1,0x1feffc,2,0x3cb4eee29d20b2e2ULL,9,1},
{"frame-cue-failure",K_FRAME_CUE_FAILURE,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0xc524af79ae943c75ULL,10,1},
{"frame-cue-success",K_FRAME_CUE_SUCCESS,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0x623ffc7294397cbcULL,11,1},
{"frame-cue-debug-waits",K_FRAME_CUE_DEBUG,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0x096fefedd790d331ULL,12,3},
{"frame-stream",K_FRAME_STREAM,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x480bc,0x2ac2,0x200000,-1,0x1feffc,2,0x4ed949a35d744590ULL,15,1},
{"buffer-cursor-10db88-toggle0",K_BUFFER_CURSOR,{0x10db88,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x69a224695e697d02ULL,16,1},
{"buffer-cursor-10db88-toggle80",K_BUFFER_CURSOR,{0x10db88,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xfa33a84a8881a982ULL,17,1},
{"buffer-cursor-10dc68-toggle0",K_BUFFER_CURSOR,{0x10dc68,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x6aa100dc6e404df9ULL,18,1},
{"buffer-cursor-10dc68-toggle80",K_BUFFER_CURSOR,{0x10dc68,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x153049f58cb4d779ULL,19,1},
{"buffer-cursor-10dc6a-toggle0",K_BUFFER_CURSOR,{0x10dc6a,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xf4551057fa4567f3ULL,20,1},
{"buffer-cursor-10dc6a-toggle80",K_BUFFER_CURSOR,{0x10dc6a,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x9ee4597118b9f173ULL,21,1},
{"buffer-cursor-10dc86-toggle0",K_BUFFER_CURSOR,{0x10dc86,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x6ab3e48e585840f7ULL,22,1},
{"buffer-cursor-10dc86-toggle80",K_BUFFER_CURSOR,{0x10dc86,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x2f40f2df6b292777ULL,23,1},
{"buffer-cursor-100000-toggle0",K_BUFFER_CURSOR,{0x100000,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x91123287ff693a6dULL,24,1},
{"buffer-cursor-100000-toggle80",K_BUFFER_CURSOR,{0x100000,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xe6816fd1d60cdeedULL,25,1},
{"buffer-cursor-10d744-toggle0",K_BUFFER_CURSOR,{0x10d744,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x984a8eb204ffcd8aULL,26,1},
{"buffer-cursor-10d744-toggle80",K_BUFFER_CURSOR,{0x10d744,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x6726ade7a2b16b0aULL,27,1},
{"buffer-cursor-10db84-toggle0",K_BUFFER_CURSOR,{0x10db84,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x732a4bb5fd40a94eULL,28,1},
{"buffer-cursor-10db84-toggle80",K_BUFFER_CURSOR,{0x10db84,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x2808a5b3a695e9ceULL,29,1},
{"buffer-bit0-1-80-0",K_BUFFER_BIT0,{0x1,0x80,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xf6d92c69ea45f6f8ULL,30,1},
{"buffer-bit0-1-0-80",K_BUFFER_BIT0,{0x1,0x0,0x80,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xd4dc45fd717a82f8ULL,31,1},
{"buffer-bit0-1-7f-7f",K_BUFFER_BIT0,{0x1,0x7f,0x7f,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x63c762ad2bd22d60ULL,32,1},
{"buffer-bit0-7e-80-80",K_BUFFER_BIT0,{0x7e,0x80,0x80,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x5d50bc6eaf94998dULL,33,1},
{"buffer-bit0-ff-0-0",K_BUFFER_BIT0,{0xff,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xc3dbe9a994c3a002ULL,34,1},
{"buffer-slots16-accepted",K_BUFFER_SLOTS16,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0xb508aa4670e8e77fULL,35,1},
{"buffer-slot15-clip",K_BUFFER_SLOT15_CLIP,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x946777cb9fa996abULL,36,1},
{"buffer-first-wait-live-record",K_BUFFER_FIRST_WAIT,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0x4aa88,0x480d2,0x200000,-1,0x1feffc,2,0x19d189a4c36c51ecULL,37,3},
{"cue-tag-1b",K_CUE_TAG,{0x1b,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xf380709f9f9f605bULL,40,1},
{"cue-tag-1c",K_CUE_TAG,{0x1c,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xdfa76c6c5b2d6ddaULL,41,1},
{"cue-tag-1f",K_CUE_TAG,{0x1f,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xcafd1ab582166667ULL,42,1},
{"cue-tag-3c",K_CUE_TAG,{0x3c,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xa1fc1bf92372087aULL,43,1},
{"cue-tag-ff",K_CUE_TAG,{0xff,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xcc96dac69b3c8647ULL,44,1},
{"cue-alloc-f0-0-0-0-0-n0",K_CUE_ALLOC,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xeaeab82c0d309e67ULL,45,1},
{"cue-alloc-f0-0-0-0-0-n4",K_CUE_ALLOC,{0x0,0x0,0x0,0x0,0x0,0x4,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xd095cdfa4210d8a3ULL,46,1},
{"cue-alloc-f1-0-ffff-0-1-n0",K_CUE_ALLOC,{0x1,0x0,0xffff,0x0,0x1,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x426dd4c73a0e105bULL,47,1},
{"cue-alloc-f1-0-ffff-0-1-n4",K_CUE_ALLOC,{0x1,0x0,0xffff,0x0,0x1,0x4,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x5a120a61409a38e7ULL,48,1},
{"cue-alloc-f2-ffff-0-1-0-n0",K_CUE_ALLOC,{0x2,0xffff,0x0,0x1,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x3160773fda0cc8a8ULL,49,1},
{"cue-alloc-f2-ffff-0-1-0-n4",K_CUE_ALLOC,{0x2,0xffff,0x0,0x1,0x0,0x4,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xd6c4611c83195184ULL,50,1},
{"cue-alloc-f3-8000-8000-8000-7fff-n0",K_CUE_ALLOC,{0x3,0x8000,0x8000,0x8000,0x7fff,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xbb2abc4098887586ULL,51,1},
{"cue-alloc-f3-8000-8000-8000-7fff-n4",K_CUE_ALLOC,{0x3,0x8000,0x8000,0x8000,0x7fff,0x4,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x77b909e67d495612ULL,52,1},
{"cue-alloc-f3-ffff-ffff-1-1-n0",K_CUE_ALLOC,{0x3,0xffff,0xffff,0x1,0x1,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xecfed98b656670f8ULL,53,1},
{"cue-alloc-f3-ffff-ffff-1-1-n4",K_CUE_ALLOC,{0x3,0xffff,0xffff,0x1,0x1,0x4,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xed0b68635dab8c44ULL,54,1},
{"cue-alloc-f1-7fff-1-0-7fff-n0",K_CUE_ALLOC,{0x1,0x7fff,0x1,0x0,0x7fff,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x0ad8bcf9b9ab2d05ULL,55,1},
{"cue-alloc-f1-7fff-1-0-7fff-n4",K_CUE_ALLOC,{0x1,0x7fff,0x1,0x0,0x7fff,0x4,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x82a5b799cb3a3b41ULL,56,1},
{"cue-success-dffff-b0",K_CUE_SUCCESS,{0xffff,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x34bbd48d6a518bd1ULL,57,1},
{"cue-success-dffff-b1",K_CUE_SUCCESS,{0xffff,0x1,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x2046b6277ca41c80ULL,58,1},
{"cue-success-d0-b80",K_CUE_SUCCESS,{0x0,0x80,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x67f64906aa50065fULL,59,1},
{"cue-success-d7fff-b7f",K_CUE_SUCCESS,{0x7fff,0x7f,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x752453e64a16ccceULL,60,1},
{"cue-stream-2-0-1-2-3-ffff",K_CUE_STREAM,{0x2,0x5,0x0,0x1,0x2,0x3,0xffff},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x8eeaf0e609dd889fULL,61,1},
{"cue-stream-4-5-5-5",K_CUE_STREAM,{0x4,0x3,0x5,0x5,0x5,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x7599e1d964bbdf30ULL,62,1},
{"cue-stream-fffe-0-ffff",K_CUE_STREAM,{0xfffe,0x2,0x0,0xffff,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x7d88c125e27b27b4ULL,63,1},
{"cue-stream-7fff-0-8000-ffff",K_CUE_STREAM,{0x7fff,0x3,0x0,0x8000,0xffff,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x53912c1b0516bc03ULL,64,1},
{"cue-stream-null",K_CUE_STREAM_NULL,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x3064099c15d308fdULL,65,1},
{"cue-debug-10-1df",K_CUE_DEBUG,{0x10,0x1df,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x0cc92fe493f6da03ULL,66,1},
{"cue-debug-10-1e0",K_CUE_DEBUG,{0x10,0x1e0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0x52a3beb36a483122ULL,67,1},
{"cue-debug-7fff-40",K_CUE_DEBUG,{0x7fff,0x40,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xd3ed1a6aa07a2165ULL,68,1},
{"cue-debug-null",K_CUE_DEBUG_NULL,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x480ea,0x200000,-1,0x1feffc,2,0xc2d72c0682890d06ULL,69,1},
{"cue-image-alias-same",K_CUE_ALIAS_SAME,{0x0,0x0,0x0,0x0,0x0,0x0,0x0},0xe8a48,0x2,0x200000,-1,0x100f0e,2,0xb0fbf3c6f0778f4aULL,70,1}};
const unsigned int FIXTURE_COUNT=63;
// Successor of each block start under the generic fixture (original code, single-stepped).
const std::uint32_t NEXT[][2]={{0x2986,0x28ae},{0x298e,0xe8a8a},{0x4aa88,0x4aafe},{0x4aa94,0x4aa9e},{0x4aa9e,0x4aaee},{0x4aaac,0x4aab4},{0x4aab4,0x4aac2},{0x4aac2,0x4b784},{0x4aad4,0x4aaee},{0x4aaee,0x4aa9e},{0x4aafc,0x4aafe},{0x4aafe,0x4ab32},{0x4ab2e,0x4ab32},{0x4ab32,0x4ab74},{0x4ab5a,0x4ab74},{0x4ab6e,0x4ab74},{0x4ab74,0x4ab86},{0x4ab86,0x4ab88},{0x4ab88,0x10e800},{0x4b784,0x4b798},{0x4b794,0x4b798},{0x4b798,0x4b7ae},{0x4b7a4,0x4b7ae},{0x4b7ae,0x4b7be},{0x4b7b8,0x4b7be},{0x4b7be,0xcd58},{0x4b7da,0x4b7f6},{0x4b7f4,0x4b7f6},{0x4b7f6,0x4b802},{0x4b800,0x4b802},{0x4b802,0xcd58},{0x4b814,0x0},{0xe8a48,0xe8aae},{0xe8a50,0xe8aae},{0xe8a6a,0xe8af4},{0xe8a70,0x2986},{0xe8a8a,0x43e08},{0xe8a9c,0xe8aae},{0xe8aae,0xe8ab6},{0xe8ab6,0xe8ad0},{0xe8aba,0xe8ac2},{0xe8ac2,0xe8ace},{0xe8ace,0x10e800},{0xe8ad0,0xe8af2},{0xe8adc,0xe8ae0},{0xe8ae0,0xe8ae8},{0xe8ae8,0xe8ae0},{0xe8aee,0xe8af2},{0xe8af2,0x10e800},{0xe8af4,0xe8b08},{0xe8b04,0xe8b08},{0xe8b08,0xe8b16},{0xe8b12,0xe8b16},{0xe8b16,0x10e800},{0xe8b18,0xe8b2a},{0xe8b2a,0xe8af4},{0xe8b2e,0xe8b4a},{0xe8b46,0xe8b4a},{0xe8b4a,0xcd58},{0xe8b58,0x10e800}};
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
unsigned long long fnv(const Bytes&b){unsigned long long h=1469598103934665603ULL;for(std::size_t i=0;i<b.size();++i){h^=b[i];h*=1099511628211ULL;}return h;}
std::uint32_t row_byte(unsigned int i){return i<16?0U:((0x5aU+7U*i)&255U);}
Physical make_rom(){
 Physical p(2);p[0].source_rom_offset=0x49ab0;const std::uint8_t mask[4]={0x10,0x20,0x40,0x80};p[0].data.assign(mask,mask+4);
 const std::uint8_t table[16]={0,0,0,2,0,0,0,1,0,1,0,1,0,2,0,1};p[1].source_rom_offset=TABLE;p[1].data.assign(128,0);
 for(unsigned int i=0;i<128;++i)p[1].data[i]=i<16?table[i]:static_cast<std::uint8_t>(row_byte(i));
 return p;}
const Physical ROM=make_rom();
std::vector<std::uint8_t> pvc_for(std::uint32_t bank){std::vector<std::uint8_t> p(8192,0);p[0x1ff1]=0xa0;p[0x1ff2]=static_cast<std::uint8_t>((bank-0x100000U)>>16);
 p[0x1ff3]=static_cast<std::uint8_t>((bank-0x100000U)>>8);return p;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc=pvc_for(0x200000);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;bus.physical_rom=&ROM;std::vector<ms5::FixedDataResource> w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
 if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message,std::uint32_t bank=0x200000){
 const Bytes before=ram;const State old=s;Out o;o.dev.bank_base=bank;o.dev.pvc=pvc_for(bank);const ms5::AnimationMachineDevice dev=o.dev;++calls;
 ms5::ProgramBusState bus;bus.physical_rom=&ROM;std::vector<ms5::FixedDataResource> w;
 if(ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error)){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error.find(message)==std::string::npos)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&
  o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
unsigned int hex_digit(char c){return c<='9'?static_cast<unsigned int>(c-'0'):static_cast<unsigned int>(c-'a'+10);}
// "address:hexbytes,..." -> bytes written into b.
void apply(Bytes&b,const char*text){
 const char*p=text;while(*p){char*end=NULL;const std::uint32_t a=static_cast<std::uint32_t>(std::strtoul(p,&end,16));assert(end&&*end==':');p=end+1;
  std::uint32_t at=a;while(*p&&*p!=','){b[at&65535U]=static_cast<std::uint8_t>((hex_digit(p[0])<<4)|hex_digit(p[1]));p+=2;++at;}if(*p==',')++p;}}
// "address/size/value,..." -> ordered port writes.
std::string port_text(const std::vector<ms5::VideoPortWrite>&ports){std::string t;char buffer[64];
 for(std::size_t i=0;i<ports.size();++i){std::snprintf(buffer,sizeof(buffer),"%s%x/%u/%x",i?",":"",ports[i].address,static_cast<unsigned int>(ports[i].size),ports[i].value);t+=buffer;}return t;}

// Declared fixture builders (the generator applies the same puts in the same order).
void frame_base(Bytes&r){
 put(r,U,4,RET_FRAME);put(r,0x100cb8,4,0);put(r,0x100cb8+0x61,1,0x7f);put(r,0x100da8,4,0x2710);put(r,0x100da8+0x61,1,0x80);
 put(r,0x10d68e,1,0xfc);put(r,0x10dc88,4,0x10db88);put(r,0x10db84,4,0x11a5225a);put(r,0x10de2e,1,1);
 for(unsigned int i=0;i<32;++i)put(r,0x10db88+2*i,2,(0x8001U+i*0x1357U)&65535U);
 for(unsigned int i=0;i<8;++i)put(r,0x10d4e6+0x2c*i+0x26,4,0xffff0000U);
 const std::uint32_t buffers[2]={0x10d746,0x10d918};
 for(unsigned int k=0;k<2;++k){const std::uint32_t b=buffers[k];put(r,b,4,0xdeadbeefU);put(r,b+0xcc,4,0x01020304);put(r,b+0xd0,2,0x5555);put(r,b+0x1ce,2,0x6666);put(r,b+0x1d0,2,0x7777);}}
void queue(Bytes&r,std::uint32_t consumer,std::uint32_t prepared){
 put(r,0x109152,4,0xcd50);put(r,0x108d34,2,consumer);put(r,0x108d36,2,prepared);put(r,0x108d38,2,0);put(r,0x108d3a,2,0);put(r,0x10914e,2,0);
 for(unsigned int i=0;i<256;++i)put(r,0x108b34+2*i,2,(i*12U)&65535U);}
void cue(Bytes&r,std::uint32_t at,std::uint32_t x,std::uint32_t y,std::uint32_t flags,std::uint32_t tag){
 put(r,at,2,x);put(r,at+2,2,y);put(r,at+4,1,flags);put(r,at+5,1,8);put(r,at+6,1,0);put(r,at+7,1,tag);}
void allocator(Bytes&r,std::uint32_t depth,std::uint32_t byte6a,std::uint32_t count){
 put(r,0x104c9c,4,0x100400);put(r,0x104ca0,2,count);put(r,0x100bfc,4,0x100800);put(r,0x100c04,2,depth);put(r,0x100c5e,1,byte6a);
 put(r,0x100804,4,0x100bf4);put(r,0x10ab6a,1,0x5a);for(unsigned int i=0;i<4;++i)put(r,0x100400+i*0x100+8,4,0x100400+(i+1)*0x100);}
void slot(Bytes&r,unsigned int i,bool obj,bool src,bool mismatch,std::uint32_t flags,std::uint32_t x,std::uint32_t y,std::uint32_t px,std::uint32_t py){
 const std::uint32_t o=0x102000+i*0x100,s=0x106000+i*0x10;
 put(r,0x10daf8+8*i,4,obj?o:0);put(r,0x10dafc+8*i,4,src?s-4:0);put(r,o+0x15,1,flags);put(r,o+0x6d,1,(mismatch?i+1:i)|0xf0);
 put(r,o+0x42,2,px);put(r,o+0x46,2,py);put(r,s,2,x);put(r,s+2,2,y);put(r,s+4,2,0x10);put(r,s+6,2,0x20);}
void direct_buffer(Bytes&r){put(r,U,4,0x480d2);for(unsigned int i=0;i<128;++i)put(r,0x10db88+2*i,2,(0x8001U+i*0x1357U)&65535U);put(r,0x10db84,4,0x11a5225a);}
void direct_cue(Bytes&r){put(r,U,4,0x480ea);put(r,0x10de26,4,0x106000);}
void build(const Fixture&f,Bytes&r){
 const std::uint32_t*p=f.p;
 switch(f.kind){
 case K_FRAME_MINIMAL:frame_base(r);break;
 case K_FRAME_CARRIED:break;
 case K_FRAME_WRAP:frame_base(r);put(r,0x10dc88,4,0x10dc68);put(r,0x10f001,1,0x01);put(r,0x104cab,1,0x80);put(r,0x10d744,1,0x80);break;
 case K_FRAME_BUFFER_WAITS:frame_base(r);put(r,0x10f001,1,0x80);slot(r,0,true,true,false,3,0x10,0x100,0x20,0x180);queue(r,2,4);break;
 case K_FRAME_BUFFER_BANK3:frame_base(r);put(r,0x10f001,1,0x80);slot(r,0,true,true,false,4,0x10,0x100,0x20,0x40);queue(r,0x100,0x80);break;
 case K_FRAME_CUE_FAILURE:frame_base(r);put(r,0x10de2f,1,1);put(r,0x10de26,4,0x106000);cue(r,0x106000,0x12,0x34,0,0x1c);break;
 case K_FRAME_CUE_SUCCESS:frame_base(r);put(r,0x10de2f,1,1);put(r,0x10de26,4,0x106000);put(r,0x10d3bc,2,1);put(r,0x10d3c0,2,0xffff);
  cue(r,0x106000,0xffff,1,3,0x1d);allocator(r,0xffff,0x80,4);break;
 case K_FRAME_CUE_DEBUG:frame_base(r);put(r,0x10f001,1,2);put(r,0x10de26,4,0x106000);cue(r,0x106000,0x10,0x40,0,0x1c);queue(r,2,4);break;
 case K_FRAME_STREAM:{frame_base(r);put(r,0x10de2e,1,0);put(r,0x10de2a,4,0x106200);put(r,0x10d418,2,3);
  const std::uint32_t gates[6]={0,1,2,3,4,0xffff};for(unsigned int i=0;i<6;++i)put(r,0x106200+12*i,2,gates[i]);break;}
 case K_BUFFER_CURSOR:direct_buffer(r);put(r,0x10dc88,4,p[0]);put(r,0x10d744,1,p[1]|0x15);break;
 case K_BUFFER_BIT0:direct_buffer(r);put(r,0x10dc88,4,0x10db88);put(r,0x10f001,1,p[0]);put(r,0x104cab,1,p[1]);put(r,0x104cb1,1,p[2]);
  if(p[0]&0x80)queue(r,0x100,0x80);break;
 case K_BUFFER_SLOTS16:direct_buffer(r);put(r,0x10dc88,4,0x10db88);put(r,0x10f001,1,0x80);
  for(unsigned int i=0;i<16;++i)slot(r,i,i%4!=0,i%4!=1,i==6,i&7,0x10+i,0x100+i,0x20*i,0x40+i);
  queue(r,0x100,0x80);break;
 case K_BUFFER_SLOT15_CLIP:direct_buffer(r);put(r,0x10dc88,4,0x10db88);put(r,0x10f001,1,0x80);slot(r,15,true,true,false,7,0x7fff,0x100,0x20,0x40);
  queue(r,0x100,0x80);break;
 case K_BUFFER_FIRST_WAIT:direct_buffer(r);put(r,0x10dc88,4,0x10db88);put(r,0x10f001,1,0x80);slot(r,3,true,true,false,1,0x10,0x100,0x20,0x40);queue(r,2,4);break;
 case K_CUE_TAG:direct_cue(r);put(r,0x10de2f,1,0x80);put(r,0x10de2e,1,1);cue(r,0x106000,0x1111,0x2222,0,p[0]);break;
 case K_CUE_ALLOC:direct_cue(r);put(r,0x10de2f,1,1);put(r,0x10de2e,1,1);put(r,0x10d3bc,2,p[3]);put(r,0x10d3c0,2,p[4]);
  cue(r,0x106000,p[1],p[2],p[0],0x1e);allocator(r,0x1234,0x01,p[5]);break;
 case K_CUE_SUCCESS:direct_cue(r);put(r,0x10de2f,1,1);put(r,0x10de2e,1,1);cue(r,0x106000,5,6,0,0x1c);allocator(r,p[0],p[1],4);break;
 case K_CUE_STREAM:direct_cue(r);put(r,0x10de2a,4,0x106200);put(r,0x10d418,2,p[0]);for(unsigned int i=0;i<p[1];++i)put(r,0x106200+12*i,2,p[2+i]);break;
 case K_CUE_STREAM_NULL:direct_cue(r);break;
 case K_CUE_DEBUG:direct_cue(r);put(r,0x10f001,1,2);put(r,0x10de2e,1,1);put(r,0x10d3a2,2,1);put(r,0x10d3a6,2,0xfffe);cue(r,0x106000,p[0],p[1],3,0);
  queue(r,0x100,0x80);break;
 case K_CUE_DEBUG_NULL:put(r,U,4,0x480ea);put(r,0x10f001,1,2);put(r,0x10de2e,1,1);break;
 case K_CUE_ALIAS_SAME:put(r,0x100f0e,4,0x480ea);put(r,0x10de26,4,0x106000);put(r,0x10de2f,1,1);put(r,0x10de2e,1,1);put(r,0x10ab6a,1,0x20);
  cue(r,0x106000,7,8,0,0x1c);break;
 default:assert(false);
 }}
State base_state(std::uint32_t pc,std::uint32_t a7,unsigned int carry){State s;s.pc=pc;s.carry=carry_of(carry);
 for(unsigned int i=0;i<8;++i)s.d[i]=0xabcd0000U+i*0x1111U;
 s.a[0]=0x10e000;s.a[1]=0x10e100;s.a[2]=0xa2a2a2a2U;s.a[3]=0xa3a3a3a3U;s.a[4]=0x10e300;s.a[5]=A5;s.a[6]=0x10ab00;s.a[7]=a7;return s;}

// Every declared fixture: each phase compares all 16 registers, PC, carry, status, bank, the ordered ports and the full
// 64 KiB RAM (input plus the recorded changes; the stack mirror is part of RAM). Later phases are same-stop resumes
// after the listed host writes; the machine state (PC cda4) and live stack carry the pending sprite submission.
struct Final {Bytes ram;State s;ms5::AnimationMachineDevice dev;};
std::vector<Final> finals;
unsigned int phase_count=0,wait_count=0;
void fixtures(){
 finals.assign(FIXTURE_COUNT,Final());
 for(unsigned int k=0;k<FIXTURE_COUNT;++k){const Fixture&f=FIXTURES[k];Bytes ram(65536,0);State s;Out o;
  if(f.carry_from>=0){const Final&prev=finals[f.carry_from];ram=prev.ram;s=prev.s;s.pc=f.entry;s.a[7]=f.a7;o.dev=prev.dev;}
  else {build(f,ram);s=base_state(f.entry,f.a7,f.carry);o.dev.bank_base=f.bank;o.dev.pvc=pvc_for(f.bank);}
  if(fnv(ram)!=f.input_hash)std::cerr<<"fixture input "<<f.name<<"\n";assert(fnv(ram)==f.input_hash&&o.dev.bank_base==f.bank);
  for(unsigned int j=0;j<f.phases;++j){const Phase&ph=PHASES[f.first_phase+j];
   for(unsigned int w=0;w<ph.writes;++w)put(ram,WRITES[ph.first_write+w].address,WRITES[ph.first_write+w].size,WRITES[ph.first_write+w].value);
   Bytes expect=ram;apply(expect,ph.changes);const State before=s;
   o.ports.clear();o.error.clear();
   if(!run(ram,s,f.stop,o)){std::cerr<<f.name<<" phase "<<j<<"\n";assert(false);}
   State want=before;for(unsigned int i=0;i<8;++i){want.d[i]=ph.regs[i];want.a[i]=ph.regs[8+i];}want.pc=ph.pc;want.carry=carry_of(ph.carry);
   const bool waiting=o.status==ms5::AnimationMachineWaiting;
   if(!same(s,want)||ram!=expect||waiting!=(ph.waiting!=0)||port_text(o.ports)!=ph.ports||o.dev.bank_base!=ph.bank||o.reads!=0){
    std::cerr<<f.name<<" phase "<<j<<" mismatch "<<port_text(o.ports)<<"\n";
    for(unsigned int i=0;i<65536;++i)if(ram[i]!=expect[i]){std::cerr<<std::hex<<(0x100000+i)<<" "<<unsigned(ram[i])<<" want "<<unsigned(expect[i])<<"\n";break;}
    assert(false);}
   // The pending sprite keeps C Unknown and PC cda4; resuming with the same stop continues there.
   if(waiting){assert(s.pc==0xcda4&&s.carry==ms5::AnimationCarryUnknown);++wait_count;}
   ++phase_count;}
  finals[k].ram=ram;finals[k].s=s;finals[k].dev=o.dev;}
}
const Final& final_of(const char*name){for(unsigned int k=0;k<FIXTURE_COUNT;++k)if(std::strcmp(FIXTURES[k].name,name)==0)return finals[k];assert(false);return finals[0];}
const Phase& phase_of(const char*name,unsigned int j){for(unsigned int k=0;k<FIXTURE_COUNT;++k)if(std::strcmp(FIXTURES[k].name,name)==0){assert(j<FIXTURES[k].phases);return PHASES[FIXTURES[k].first_phase+j];}
 assert(false);return PHASES[0];}

// Readable key facts of the recorded fixtures (all already covered by the full comparison above).
void key_facts(){
 // Whole frames return through 480f0 to the dispatcher LONG with A7 = 1feffc+4.
 const char*frames[]={"frame-minimal","frame-carried","frame-carried-2","frame-wrap-bit0","frame-buffer-waits","frame-buffer-bank3",
  "frame-cue-failure","frame-cue-success","frame-cue-debug-waits","frame-stream"};
 for(unsigned int i=0;i<10;++i){const Final&f=final_of(frames[i]);assert(f.s.pc==RET_FRAME&&f.s.a[7]==U+4&&f.s.a[5]==A5);}
 // Minimal frame: cursor 10db88 -> 10dba8, sixteen LSR.W (8001 -> 4000), BYTE shifts, bit7 toggled 0 -> 1 (EXG: 10d918
 // cleared, A4 = 10d918), the 10d746 buffer untouched.
 {const Final&f=final_of("frame-minimal");assert(get(f.ram,0x10dc88,4)==0x10dba8&&get(f.ram,0x10db88,2)==0x4000&&get(f.ram,0x10db84,4)==0xa5005a00U);
  assert(get(f.ram,0x10d744,1)==0x80&&get(f.ram,0x10d918,4)==0&&get(f.ram,0x10d918+0xcc,4)==0&&get(f.ram,0x10d918+0xd0,2)==0x5555&&
   get(f.ram,0x10d918+0x1ce,2)==0x6666&&get(f.ram,0x10d918+0x1d0,2)==0&&get(f.ram,0x10d746,4)==0xdeadbeefU&&get(f.ram,0x10d746+0x1d0,2)==0x7777);
  // e8a48: no request, manual cue (10de2e=1), debug off. 10de26 unchanged (0).
  assert(get(f.ram,0x10de26,4)==0);}
 // Carried frame: cursor 10dba8 -> 10dbc8, bit7 1 -> 0 (no EXG: 10d746 cleared).
 {const Final&f=final_of("frame-carried");assert(get(f.ram,0x10dc88,4)==0x10dbc8&&get(f.ram,0x10d744,1)==0&&get(f.ram,0x10d746,4)==0&&get(f.ram,0x10d746+0x1d0,2)==0);}
 // Wrap: cursor 10dc68 -> 10dc88 -> LEA 10db88; bit0 debug with 104cab bit7 forces 10db84 = ff.
 {const Final&f=final_of("frame-wrap-bit0");assert(get(f.ram,0x10dc88,4)==0x10db88&&get(f.ram,0x10db84,1)==0xff&&get(f.ram,0x10d744,1)==0);}
 // Buffer waits: the first sprite waits with A7 = U-38 (U-4 480d2, U-8 outer A6, U-12 slot A4, U-14 slot D7.W, U-18 4aad4,
 // U-38 4b7da), the second with A7 = U-26 (U-26 4b814). Ports: two bank resets per slot then none before the frame RTS.
 {const Phase&p0=phase_of("frame-buffer-waits",0);assert(p0.waiting&&p0.pc==0xcda4&&p0.regs[15]==U-38);
  const Phase&p2=phase_of("frame-buffer-waits",2);assert(p2.waiting&&p2.regs[15]==U-26);
  const Phase&p4=phase_of("frame-buffer-waits",4);assert(!p4.waiting&&p4.pc==RET_FRAME);
  const Phase&hold=phase_of("frame-buffer-waits",1);assert(hold.waiting&&hold.changes[0]==0&&hold.ports[0]==0);}
 // Cue failure: 2986 image WORD 2004 at U-16 (S-2 with S = U-14), fallback object 100e98: 6a <- BYTE 6a(A6), +76/+78 = index 0.
 {const Final&f=final_of("frame-cue-failure");assert(get(f.ram,U-16,2)==0x2004&&get(f.ram,0x100f0e,4)==0x00000002&&get(f.ram,0x10de2f,1)==0);}
 // Cue success (flags 3, both ADD.W carry; parent +10 WORD ffff -> X=1 from ADDQ, BYTE 6a 80 -> N): image 2019.
 {const Final&f=final_of("frame-cue-success");assert(get(f.ram,U-16,2)==0x2019&&get(f.ram,0x100476,4)==0x00000001);}
 // Debug cue wait: A7 = U-8 (U-4 480ea, U-8 e8b58).
 {const Phase&p0=phase_of("frame-cue-debug-waits",0);assert(p0.waiting&&p0.regs[15]==U-8);}
 // Stream: phase 3 stops on the record whose successor gate (12(A0)) is the first above 3: 10de2a = 106224, 10de26 = 106228.
 {const Final&f=final_of("frame-stream");assert(get(f.ram,0x10de2a,4)==0x106224&&get(f.ram,0x10de26,4)==0x106228);}
 // Direct e8a48 null stream: 10de26 = 4 (LEA 4(A0) with A0 = 0).
 {const Final&f=final_of("cue-stream-null");assert(get(f.ram,0x10de26,4)==4);}
 // 16 slots (null object 0/4/8/12, null source 1/5/9/13, mismatched 6d at 6): the 7 matching slots each publish the
 // 4b816 and 4aad8 bank resets (2 WORD ports each): 28 ports.
 {const Final&f=final_of("buffer-slots16-accepted");assert(f.s.a[7]==U+4);const std::string ports=phase_of("buffer-slots16-accepted",0).ports;
  unsigned int n=1;for(std::size_t i=0;i<ports.size();++i)n+=ports[i]==',';assert(n==28);}
}

// e8a0c table index 0..1f (tag 1c..3b) on the failure path: the two WORDs at 100f0e/100f10 are e8a0c+4i read through the
// live bus (synthetic row for index 4..1f). Everything else matches the index-0 run except the tag BYTE and the index
// results (D0.W = 4i after LSL, A1 = e8a0c+4i+4).
void table_indices(){
 Bytes ref;State ref_state;
 for(unsigned int i=0;i<0x20;++i){Bytes ram(65536,0);direct_cue(ram);put(ram,0x10de2f,1,1);put(ram,0x10de2e,1,1);cue(ram,0x106000,0x1234,0x5678,0,0x1c+i);
  State s=base_state(0xe8a48,U,2);Out o;assert(run(ram,s,0x480ea,o)&&o.status==ms5::AnimationMachineReturned&&o.ports.empty());
  const std::uint32_t row=TABLE+4*i;
  std::uint32_t w0=0,w1=0;for(unsigned int b=0;b<2;++b){w0=(w0<<8)|ROM[1].data[row-TABLE+b];w1=(w1<<8)|ROM[1].data[row-TABLE+2+b];}
  assert(get(ram,0x100f0e,2)==w0&&get(ram,0x100f10,2)==w1&&(s.d[0]&65535U)==4*i&&s.a[1]==row+4&&s.a[0]==0x100f12&&s.a[7]==U+4);
  assert(get(ram,U-12,2)==0x2004); // S = U-10 for a direct entry
  if(i==0){ref=ram;ref_state=s;continue;}
  Bytes masked=ram;put(masked,0x100f0e,4,get(ref,0x100f0e,4));put(masked,0x106007,1,0x1c);put(masked,U-2,2,0);assert(masked==ref);
  State t=s;t.d[0]=ref_state.d[0];t.a[1]=ref_state.a[1];assert(same(t,ref_state));}
 // Tags outside 1c..3b skip the allocation (SUBI.W #1c then CMPI.B #20 unsigned): 10de2f is still cleared.
 const std::uint32_t skip[]={0x00,0x1b,0x3c,0x80,0xff};
 for(unsigned int i=0;i<5;++i){Bytes ram(65536,0);direct_cue(ram);put(ram,0x10de2f,1,1);put(ram,0x10de2e,1,1);cue(ram,0x106000,1,2,0,skip[i]);
  Bytes expect=ram;put(expect,0x10de2f,1,0);State s=base_state(0xe8a48,U,2);Out o;assert(run(ram,s,0x480ea,o));
  assert(ram==expect&&s.a[0]==0x106000&&(s.d[0]&65535U)==((skip[i]-0x1cU)&65535U)&&s.a[7]==U+4);}
}

// Long e8ae0 walk through RAM (5460 records) and a walk that leaves the readable bus: the read error rolls back the earlier
// 10de2f clear. The 1,000,000-block budget cannot be reached by e8ae0 alone: 12-byte steps leave the contiguous readable
// bus (vectors/fixed ROM, RAM mirror, bank window: under 3 MiB, under 262,144 iterations) first.
void stream_walks(){
 // Gate WORDs are read live on the 12-byte grid 100010+12k: the first non-zero one above D0.W=1 is the high WORD of the
 // e8ab6 BSR return LONG 000e8aba pushed at U-4 (RAM mirror 10eff8), so the walk stops at record 10efec (5118 steps).
 {Bytes ram(65536,0);put(ram,U,4,0x480ea);put(ram,0x10de2a,4,0x100004);put(ram,0x10d418,2,1);
  State s=base_state(0xe8a48,U,2);Out o;assert(run(ram,s,0x480ea,o));assert(get(ram,0x10de2a,4)==0x10efec&&get(ram,0x10de26,4)==0x10eff0&&s.a[0]==0x10efec);}
 {Bytes ram(65536,0);direct_cue(ram);put(ram,0x10de2f,1,0x40);put(ram,0x106007,1,0);put(ram,0x10de2a,4,0x1fffe8);put(ram,0x10d418,2,0xffff);
  reject(ram,base_state(0xe8a48,U,2),0x480ea,"program bus ROM");}
}

// Checked errors with full rollback.
void errors(){
 // 298e with Unknown C (the 28ae result is required for the image and the restored C).
 {Bytes ram(65536,0);put(ram,U,4,0x10e700);put(ram,U+4,4,0xe8a8a);put(ram,0x10de26,4,0x10e800);State s=base_state(0x298e,U,0);
  reject(ram,s,STOP,"cue wrapper requires known carry");
  // Known C: Clear -> 28ba image (D0.W 0 >= limit 0: Z) with the e8a48 caller X (flags 0: X=0) = 2004; Set -> success image
  // X=(D0.W==0) Z (BYTE 6a(A0)=0) C = 2015. The restored C is bit0 of the popped WORD.
  for(unsigned int c=1;c<3;++c){Bytes r=ram;State t=base_state(0x298e,U,c);t.d[0]=0xabcd0000U;t.a[0]=0x10e800;Out o;assert(run(r,t,0xe8a8a,o));
   assert(get(r,U+2,2)==(c==1?0x2004U:0x2015U)&&t.carry==carry_of(c)&&t.a[6]==0x10e700&&t.a[7]==U+8);}}
 // Failure path from another caller (return LONG not e8a8a): 28ba (count 0) and 28c2 (A0 input 0).
 {Bytes ram(65536,0);put(ram,U,4,STOP);State s=base_state(0x2986,U,2);s.a[0]=0xd5f16;s.a[1]=0x100bf4;s.d[0]=0;
  reject(ram,s,STOP,"cue wrapper failure requires known caller X");
  allocator(ram,0,0,4);s.a[0]=0;reject(ram,s,STOP,"cue wrapper failure requires known caller X");
  // The success path does not depend on the caller.
  // Success image: X = (D0.W == 0) after the 28e6 ADDQ (parent +10 WORD 0 -> D0.W 1: X=0), Z from BYTE 6a = 0, C: 2005 at S-2.
  s.a[0]=0xd5f16;Out o;Bytes r=ram;assert(run(r,s,STOP,o)&&s.carry==ms5::AnimationCarrySet&&s.a[0]==0x100400&&get(r,U-2,2)==0x2005);}
 // Re-read alias: the e8a6a index push lands on 10de26 (S+8 = 10de26), so the live LONG differs from the cue the original read.
 // The return LONG 000480ea at 10de28 shares its high WORD with the cue LONG 00100004 at 10de26.
 {Bytes ram(65536,0);put(ram,0x10de26,4,0x100004);put(ram,0x10de28,4,0x480ea);put(ram,0x10de2f,1,1);put(ram,0x10de2e,1,1);cue(ram,0x100004,1,2,0,0x1c);
  State s=base_state(0xe8a48,0x10de28,2);reject(ram,s,0x480ea,"cue wrapper caller X source overlaps the stack");}
 // 2992 overwrites the pushed WORD (stack at A0+6a-2+10) with a different BYTE: the popped WORD differs.
 {Bytes ram(65536,0);build(FIXTURES[FIXTURE_COUNT-1],ram);put(ram,0x10ab6a,1,0x5a);State s=base_state(0xe8a48,0x100f0e,2);
  assert(std::strcmp(FIXTURES[FIXTURE_COUNT-1].name,"cue-image-alias-same")==0);reject(ram,s,2,"cue wrapper status WORD overwritten");}
 // e8a48 requires A5 = 108000 (the caller-X rule re-reads absolute addresses).
 {Bytes ram(65536,0);direct_cue(ram);State s=base_state(0xe8a48,U,2);s.a[5]=0x108002;reject(ram,s,0x480ea,"cue requires A5 108000");}
 // Non-cd50 sprite callback after earlier slots published ports, and in the debug cue path.
 {Bytes ram(65536,0);direct_buffer(ram);put(ram,0x10dc88,4,0x10db88);put(ram,0x10f001,1,0x80);
  slot(ram,0,true,true,false,0,0x10,0x100,0x20,0x40);slot(ram,5,true,true,false,0,0x10,0x100,0x20,0x40);queue(ram,0x100,0x80);
  State s=base_state(0x4aa88,U,2);Out o;Bytes r=ram;assert(run(r,s,0x480d2,o)&&o.ports.size()==8);
  // Slot 0's second sprite stores its MOVEM.L record over the callback LONG 109152 (queue WORD 108b38 = 121e:
  // 107f34+121e); slot 5 then reads the live callback and fails after slot 0 published 4 ports: all rolled back.
  put(ram,0x108b38,2,0x121e);reject(ram,base_state(0x4aa88,U,2),0x480d2,"unsupported sprite callback target");}
 {Bytes ram(65536,0);direct_cue(ram);put(ram,0x10f001,1,2);put(ram,0x10de2e,1,1);cue(ram,0x106000,0x10,0x40,0,0);queue(ram,0x100,0x80);
  put(ram,0x109152,4,0x106000);reject(ram,base_state(0xe8a48,U,2),0x480ea,"unsupported sprite callback target");}
 // Odd addresses: ring cursor (A0), slot table (A4), object WORD 42(A6), record (A0), cue (A0), stream (A0), stack (A7).
 {Bytes ram(65536,0);direct_buffer(ram);put(ram,0x10dc88,4,0x10db89);reject(ram,base_state(0x4aa88,U,2),0x480d2,"even WORD/LONG");}
 {Bytes ram(65536,0);direct_buffer(ram);State s=base_state(0x4aa9e,U,2);s.a[4]=0x10daf9;reject(ram,s,0x480d2,"even WORD/LONG");}
 {Bytes ram(65536,0);direct_buffer(ram);State s=base_state(0x4b7be,U,2);s.a[6]=0x102001;reject(ram,s,0x480d2,"even WORD/LONG");}
 {Bytes ram(65536,0);direct_buffer(ram);State s=base_state(0x4b798,U,2);s.a[0]=0x106001;reject(ram,s,0x480d2,"even WORD/LONG");}
 {Bytes ram(65536,0);direct_cue(ram);State s=base_state(0xe8af4,U,2);s.a[0]=0x106001;reject(ram,s,0x480ea,"even WORD/LONG");}
 {Bytes ram(65536,0);direct_cue(ram);put(ram,0x10de2a,4,0x106201);put(ram,0x10de2e,1,0);reject(ram,base_state(0xe8a48,U,2),0x480ea,"even WORD/LONG");}
 {Bytes ram(65536,0);direct_buffer(ram);put(ram,0x10f001,1,0x80);State s=base_state(0x4aa88,U-1,2);reject(ram,s,0x480d2,"even WORD/LONG");}
 // Ring cursor in fixed ROM (readable through the physical row): the LSR.W store is not a supported write device.
 {Bytes ram(65536,0);direct_buffer(ram);put(ram,0x10dc88,4,TABLE);reject(ram,base_state(0x4aa88,U,2),0x480d2,"unsupported animation machine write device");}
 // Unreached stop: the run leaves through the return LONG into an unrouted PC.
 {Bytes ram(65536,0);direct_cue(ram);put(ram,U,4,0x4abc0);reject(ram,base_state(0xe8a48,U,2),0x480ea,"unsupported animation machine PC");}
}

// Block starts (60) and the rejected interior PCs of the four routed ranges (the 24 bundled branch PCs included).
const std::uint32_t BUNDLED[]={0x4aa90,0x4aaa8,0x4aab0,0x4aabe,0x4aafa,0x4ab2a,0x4ab56,0x4ab6a,0x4ab82,0x4b790,0x4b7a0,0x4b7b4,0x4b7f0,0x4b7fc,
 0xe8a4c,0xe8a66,0xe8ab2,0xe8aca,0xe8ad8,0xe8ae4,0xe8b00,0xe8b0e,0xe8b26,0xe8b42};
const unsigned int STARTS=sizeof(NEXT)/sizeof(NEXT[0]);
bool is_start(std::uint32_t pc){for(unsigned int i=0;i<STARTS;++i)if(NEXT[i][0]==pc)return true;return false;}
void generic(std::uint32_t pc,Bytes&ram,State&s,unsigned int carry){
 ram.assign(65536,0);
 if(pc==0x298e){put(ram,U,4,0x10e700);put(ram,U+4,4,0xe8a8a);put(ram,0x10de26,4,0x10e800);}
 else {put(ram,U,4,0x10e800);put(ram,0x10dc88,4,0x10db88);put(ram,0x10de26,4,0x10e800);}
 s=State();s.pc=pc;s.carry=carry_of(carry);for(unsigned int i=0;i<8;++i)s.d[i]=0;
 s.a[0]=0x10e800;s.a[1]=0x10e900;s.a[2]=0x10ec00;s.a[3]=0x10eb00;s.a[4]=0x10daf8;s.a[5]=A5;s.a[6]=0x10ea00;s.a[7]=U;}
void interior(){
 assert(STARTS==60);
 const std::uint32_t ranges[][2]={{0x4aa88,0x4abc0},{0x4b784,0x4b82e},{0xe8a48,0xe8b5a},{0x2986,0x299c}};
 unsigned int rejected=0,bundled=0;
 for(unsigned int r=0;r<4;++r)for(std::uint32_t pc=ranges[r][0];pc<ranges[r][1];pc+=2){
  if(is_start(pc))continue;Bytes ram;State s;generic(pc,ram,s,2);reject(ram,s,STOP,"unsupported animation buffer cue PC");++rejected;
  for(unsigned int i=0;i<24;++i)if(BUNDLED[i]==pc)++bundled;}
 assert(rejected==329&&bundled==24); // 389 even PCs minus 60 block starts
 // Neighbours and data: e8a0c..e8a1c (table) and e8a3a..e8a48 are not routed (e8a1c..e8a3a is the stage entry cue
 // install, e8a1c a block start there); the range ends are not routed (4b82e is objects N03 since F4 N03: RAM probe 10fe50).
 const std::uint32_t outside[]={0x4aa86,0x4abc0,0x4b782,0x10fe50,0xe8a0c,0xe8a1a,0xe8a3a,0xe8a46,0xe8b5a,0x2984};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram;State s;generic(outside[i],ram,s,2);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0x4aa89,ram,s,2);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int c=0;c<3;++c)for(unsigned int i=0;i<STARTS;++i){Bytes ram;State s;generic(NEXT[i][0],ram,s,c);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,NEXT[i][0],o)&&same(s,old)&&ram==before&&o.ports.empty()&&o.status==ms5::AnimationMachineReturned);}
}
// FLOW_ONLY blocks keep the incoming C; 298e consumes a known C and restores it from the popped WORD; others are Unknown.
const std::uint32_t KEEP[]={0x4aa88,0x4aafc,0x4ab2e,0x4ab74,0x4b7ae,0x4b7f6,0xe8ab6,0xe8ac2,0xe8ace,0xe8af2,0xe8b08,0xe8b16,0xe8b2a,0xe8b46,0xe8b58};
void carry(){
 unsigned int keeps=0;
 for(unsigned int i=0;i<STARTS;++i){const std::uint32_t pc=NEXT[i][0];bool keep=false;for(unsigned int k=0;k<15;++k)if(KEEP[k]==pc)keep=true;keeps+=keep;
  for(unsigned int c=0;c<3;++c){Bytes ram;State s;generic(pc,ram,s,c);
   if(pc==0x298e&&c==0){reject(ram,s,STOP,"cue wrapper requires known carry");continue;}
   Out o;if(!(run(ram,s,NEXT[i][1],o)&&s.pc==NEXT[i][1]))std::cerr<<std::hex<<"row "<<pc<<"\n";assert(s.pc==NEXT[i][1]);
   const ms5::AnimationCarryState expect=(keep||pc==0x298e)?carry_of(c):ms5::AnimationCarryUnknown;
   if(s.carry!=expect)std::cerr<<std::hex<<"carry row "<<pc<<"\n";assert(s.carry==expect);}}
 assert(keeps==15);
}
}
int main(){fixtures();key_facts();table_indices();stream_walks();errors();interior();zero_step();carry();
 std::cout<<"animation_machine_buffer_cue_test PASS "<<std::dec<<FIXTURE_COUNT<<" fixtures "<<phase_count<<" phases "<<wait_count<<" waits "<<calls<<" API invocations\n";}
