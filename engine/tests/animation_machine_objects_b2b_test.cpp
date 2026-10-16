#include "ms5/animation_machine.h"
#include "../src/animation_machine_internal.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
// Objects B2b (209 block starts: the orphan chains 3383c 3a4a4 3a4be 3a4da 3a5be 3b424 3b446 4bfc0 38d56 39f9c 3a0dc (27-slot table 3a0f4) 3acd6
// 4c390 4c3a2 4c3cc, the slot helpers 4d418 / 4d4b4 and the leaf helpers 4c2fa 4d6b4 4d734 4d98a 4d9ba 4eea2 (4f08a) 4ff96 d3d7c).
// Part 1 (STEPS, generated from the static decode of the original code bytes with capstone M68000, same decode as tools/unit_fixture_specs/b2b.py):
// every block start is stepped once through animation_objects_b2b_block in two declared worlds and its successor is checked against the
// static successors of the original block (branch targets, fall-through, call target + pushed return LONG, RTS to the declared return LONG,
// the 27 table slots). Part 2: declared semantic fixtures through run_animation_machine only (4d418 Set / Clear paths and slot writes, 4d4b4 computed
// carry and the seven LONG ports of 4eea2, the table, JSR (A0), the consumers, the known C of the RTS blocks), checked errors and failure
// preservation. Inputs are declared fixtures (zero RAM, node A6 = 10e000, A5 = 108000, stack 10ee00 with the return LONG ff000); the only ROM bytes
// are synthetic typed physical bytes (the sign-extended BYTE pairs read at 3a4d6 / 3a4d8 and the banked LONG 2000b4), not ROM data. The native
// equivalence of the same blocks against the original ROM is the job of tools/unit_fixture_specs/b2b.py (V1 verifier).
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef ms5::AnimationMachineState State;
using ms5::AnimationCarryClear;
using ms5::AnimationCarrySet;
using ms5::AnimationCarryUnknown;
const std::uint32_t SENT=0xff000,SP=0x10ee00,NODE=0x10e000,A5=0x108000;
const std::uint32_t P0=0x10c000,P1=0x10c100,P2=0x10c200,P3=0x10c300,SLOT0=0x10dcba,SLOT1=0x10dce6,TARGET0=0x100cb8,TARGET1=0x100da8;
unsigned int checks=0;
void check(bool ok,const char*what,std::uint32_t a=0,std::uint32_t b=0) {
    ++checks;
    if(!ok){std::cerr<<std::hex<<"FAILED "<<what<<" "<<a<<" "<<b<<"\n";std::exit(1);}
}
// ---- generated table (begin): pc, kind (0 flow, 1 call, 2 RTS, 3 table), pushed return LONG, successor count, successors.
struct Step {std::uint32_t pc;unsigned int kind;std::uint32_t ret;unsigned int n;std::uint32_t succ[27];};
const Step STEPS[]={
 {0x3383c,1,0x33846,1,{0x4ae4a}},
 {0x33846,1,0x3384e,1,{0x33940}},
 {0x3384e,1,0x33858,1,{0x4ff96}},
 {0x33858,1,0x3385e,1,{0xd3d7c}},
 {0x3385e,1,0x3387a,1,{0xd3d7c}},
 {0x3387a,1,0x33896,1,{0xd3d7c}},
 {0x33896,1,0x338b2,1,{0xd3d7c}},
 {0x338b2,1,0x338de,1,{0x2986}},
 {0x338de,1,0x338e8,1,{0x49214}},
 {0x338e8,1,0x338f2,1,{0x3af8}},
 {0x338f2,0,0x0,1,{0x2a00}},
 {0x33940,1,0x33948,1,{0x4d8d8}},
 {0x33948,0,0x0,2,{0x33950,0x33952}},
 {0x33950,2,0x0,0,{0}},
 {0x33952,0,0x0,1,{0x4d4b4}},
 {0x3a4a4,0,0x0,2,{0x3a4b6,0x3a4b8}},
 {0x3a4b6,0,0x0,1,{0x3a4b8}},
 {0x3a4b8,0,0x0,1,{0x4d418}},
 {0x3a4be,1,0x3a4c6,1,{0x4d8d8}},
 {0x3a4c6,0,0x0,2,{0x3a4ce,0x3a4d0}},
 {0x3a4ce,2,0x0,0,{0}},
 {0x3a4d0,0,0x0,1,{0x4d4b4}},
 {0x3a4da,0,0x0,2,{0x3a4e2,0x3a5b8}},
 {0x3a4e2,1,0x3a4ec,1,{0x4d6b4}},
 {0x3a4ec,0,0x0,2,{0x3a4f0,0x3a5b8}},
 {0x3a4f0,0,0x0,2,{0x3a4fa,0x3a502}},
 {0x3a4fa,0,0x0,1,{0x3a506}},
 {0x3a502,0,0x0,1,{0x3a506}},
 {0x3a506,1,0x3a51e,1,{0x28ae}},
 {0x3a51e,1,0x3a528,1,{0x49214}},
 {0x3a528,1,0x3a52e,1,{0x491b6}},
 {0x3a52e,0,0x0,2,{0x3a542,0x3a544}},
 {0x3a542,0,0x0,1,{0x3a544}},
 {0x3a544,0,0x0,2,{0x3a560,0x3a574}},
 {0x3a560,1,0x3a570,1,{0x28ae}},
 {0x3a570,0,0x0,1,{0x3a584}},
 {0x3a574,1,0x3a584,1,{0x28ae}},
 {0x3a584,0,0x0,2,{0x3a5a0,0x3a5a6}},
 {0x3a5a0,0,0x0,1,{0x3a5a6}},
 {0x3a5a6,1,0x3a5b2,1,{0x4c2fa}},
 {0x3a5b2,2,0x0,0,{0}},
 {0x3a5b8,2,0x0,0,{0}},
 {0x3a5be,1,0x3a5ca,0,{0}},
 {0x3a5ca,2,0x0,0,{0}},
 {0x3b424,1,0x3b42e,1,{0x49be0}},
 {0x3b42e,2,0x0,0,{0}},
 {0x3b446,1,0x3b448,1,{0x3b424}},
 {0x3b448,0,0x0,2,{0x3b452,0x3b456}},
 {0x3b452,0,0x0,1,{0x3b456}},
 {0x3b456,2,0x0,0,{0}},
 {0x4bfc0,1,0x4bfc4,1,{0x4bce0}},
 {0x4bfc4,1,0x4bfc8,1,{0x4c020}},
 {0x4bfc8,1,0x4bfce,1,{0x4b8e8}},
 {0x4bfce,0,0x0,2,{0x4bf0a,0x4bfd4}},
 {0x4bfd4,1,0x4bfda,1,{0x469d8}},
 {0x4bfda,0,0x0,2,{0x4bfee,0x4bffe}},
 {0x4bfee,0,0x0,1,{0x4bffe}},
 {0x4bffe,0,0x0,2,{0x4c006,0x4c016}},
 {0x4c006,0,0x0,1,{0x4c016}},
 {0x4c016,0,0x0,1,{0x4bf16}},
 {0x38d56,1,0x38d60,1,{0x3b5a6}},
 {0x38d60,1,0x38d70,1,{0x28ae}},
 {0x38d70,1,0x38d7a,1,{0x4972c}},
 {0x38d7a,0,0x0,1,{0x38d80}},
 {0x38d80,0,0x0,2,{0x38d88,0x38d9c}},
 {0x38d88,1,0x38d8c,1,{0x3b288}},
 {0x38d8c,1,0x38d90,1,{0x3b334}},
 {0x38d90,1,0x38d98,1,{0x3b2ee}},
 {0x38d98,0,0x0,1,{0x3a350}},
 {0x38d9c,1,0x38da6,1,{0x3af8}},
 {0x38da6,1,0x38db0,1,{0x3b302}},
 {0x38db0,0,0x0,1,{0x38db6}},
 {0x38db6,1,0x38dba,1,{0x3b288}},
 {0x38dba,1,0x38dbe,1,{0x3b334}},
 {0x38dbe,0,0x0,2,{0x38dc2,0x38dc8}},
 {0x38dc2,0,0x0,1,{0x38dc8}},
 {0x38dc8,1,0x38dd0,1,{0x3b2ee}},
 {0x38dd0,0,0x0,1,{0x3a350}},
 {0x39f9c,1,0x39fa6,1,{0x3c44}},
 {0x39fa6,1,0x39fb0,1,{0x4ae4a}},
 {0x39fb0,1,0x39fba,1,{0x4ff96}},
 {0x39fba,1,0x39fc0,1,{0xd3d7c}},
 {0x39fc0,1,0x39fdc,1,{0xd3d7c}},
 {0x39fdc,1,0x39ff8,1,{0xd3d7c}},
 {0x39ff8,1,0x3a014,1,{0xd3d7c}},
 {0x3a014,1,0x3a03a,1,{0x28ae}},
 {0x3a03a,1,0x3a044,1,{0x49214}},
 {0x3a044,0,0x0,1,{0x3a2f4}},
 {0x3a0dc,0,0x0,2,{0x3a0e8,0x3a160}},
 {0x3a0e8,3,0x0,27,{0x3a0f4,0x3a0f8,0x3a0fc,0x3a100,0x3a104,0x3a108,0x3a10c,0x3a110,0x3a114,0x3a118,0x3a11c,0x3a120,0x3a124,0x3a128,0x3a12c,0x3a130,0x3a134,0x3a138,0x3a13c,0x3a140,0x3a144,0x3a148,0x3a14c,0x3a150,0x3a154,0x3a158,0x3a15c}},
 {0x3a0f4,0,0x0,1,{0x3a160}},
 {0x3a0f8,0,0x0,1,{0x3a160}},
 {0x3a0fc,0,0x0,1,{0x3a160}},
 {0x3a100,0,0x0,1,{0x3a160}},
 {0x3a104,0,0x0,1,{0x3a160}},
 {0x3a108,0,0x0,1,{0x3a160}},
 {0x3a10c,0,0x0,1,{0x3a160}},
 {0x3a110,0,0x0,1,{0x3a160}},
 {0x3a114,0,0x0,1,{0x3a160}},
 {0x3a118,0,0x0,1,{0x3a160}},
 {0x3a11c,0,0x0,1,{0x3a160}},
 {0x3a120,0,0x0,1,{0x3a160}},
 {0x3a124,0,0x0,1,{0x3a160}},
 {0x3a128,0,0x0,1,{0x3a160}},
 {0x3a12c,0,0x0,1,{0x3a160}},
 {0x3a130,0,0x0,1,{0x3a160}},
 {0x3a134,0,0x0,1,{0x3a160}},
 {0x3a138,0,0x0,1,{0x3a160}},
 {0x3a13c,0,0x0,1,{0x3a160}},
 {0x3a140,0,0x0,1,{0x3a160}},
 {0x3a144,0,0x0,1,{0x3a160}},
 {0x3a148,0,0x0,1,{0x3a160}},
 {0x3a14c,0,0x0,1,{0x3a160}},
 {0x3a150,0,0x0,1,{0x3a160}},
 {0x3a154,0,0x0,1,{0x3a24c}},
 {0x3a158,0,0x0,1,{0x3a160}},
 {0x3a15c,0,0x0,1,{0x3a160}},
 {0x3a160,1,0x3a166,1,{0x4d8d8}},
 {0x3a166,0,0x0,2,{0x3a16c,0x3a1a0}},
 {0x3a16c,0,0x0,2,{0x3a176,0x3a188}},
 {0x3a176,1,0x3a180,1,{0x3b302}},
 {0x3a180,0,0x0,1,{0x3a196}},
 {0x3a188,1,0x3a192,1,{0x3b302}},
 {0x3a192,0,0x0,1,{0x3a196}},
 {0x3a196,0,0x0,1,{0x3a1b2}},
 {0x3a1a0,1,0x3a1aa,1,{0x3b302}},
 {0x3a1aa,1,0x3a1ae,1,{0x3a5d2}},
 {0x3a1ae,0,0x0,1,{0x3a1b2}},
 {0x3a1b2,1,0x3a1b8,1,{0x4db18}},
 {0x3a1b8,1,0x3a1c6,1,{0x496c2}},
 {0x3a1c6,1,0x3a1da,1,{0x3af8}},
 {0x3a1da,0,0x0,1,{0x3a1e0}},
 {0x3acd6,1,0x3ad06,1,{0x49f8c}},
 {0x3ad06,1,0x3ad14,1,{0x8ebe}},
 {0x3ad14,1,0x3ad1a,1,{0x49274}},
 {0x3ad1a,0,0x0,1,{0x3ad20}},
 {0x3ad20,1,0x3ad26,1,{0x288c}},
 {0x3ad26,0,0x0,2,{0x3ad2a,0x3ad30}},
 {0x3ad2a,0,0x0,1,{0x2a00}},
 {0x3ad30,1,0x3ad36,1,{0x43e34}},
 {0x3ad36,1,0x3ad3c,1,{0x49fc6}},
 {0x3ad3c,0,0x0,2,{0x3ad40,0x3ad46}},
 {0x3ad40,0,0x0,1,{0x2a00}},
 {0x3ad46,2,0x0,0,{0}},
 {0x4c390,1,0x4c398,1,{0x4bce0}},
 {0x4c398,0,0x0,1,{0x4c810}},
 {0x4c3a2,1,0x4c3aa,1,{0x4bc44}},
 {0x4c3aa,0,0x0,1,{0x4c810}},
 {0x4c3cc,1,0x4c3d4,1,{0x4bce0}},
 {0x4c3d4,0,0x0,1,{0x4c810}},
 {0x4d418,0,0x0,2,{0x4d41e,0x4d42a}},
 {0x4d41e,0,0x0,1,{0x4d432}},
 {0x4d42a,0,0x0,1,{0x4d432}},
 {0x4d432,1,0x4d438,1,{0x289e}},
 {0x4d438,0,0x0,2,{0x4d43c,0x4d4ac}},
 {0x4d43c,0,0x0,2,{0x4d446,0x4d4ac}},
 {0x4d446,0,0x0,2,{0x4d44e,0x4d454}},
 {0x4d44e,0,0x0,2,{0x4d454,0x4d4ac}},
 {0x4d454,0,0x0,2,{0x4d476,0x4d4ac}},
 {0x4d476,0,0x0,2,{0x4d48c,0x4d490}},
 {0x4d48c,0,0x0,1,{0x4d490}},
 {0x4d490,2,0x0,0,{0}},
 {0x4d4ac,2,0x0,0,{0}},
 {0x4d4b4,1,0x4d4c2,1,{0x4eea2}},
 {0x4d4c2,0,0x0,2,{0x4d4cc,0x4d4d8}},
 {0x4d4cc,0,0x0,1,{0x4d4e0}},
 {0x4d4d8,0,0x0,1,{0x4d4e0}},
 {0x4d4e0,0,0x0,2,{0x4d4e8,0x4d506}},
 {0x4d4e8,0,0x0,2,{0x4d502,0x4d506}},
 {0x4d502,0,0x0,1,{0x4d506}},
 {0x4d506,2,0x0,0,{0}},
 {0x4c2fa,1,0x4c2fe,1,{0x4bc44}},
 {0x4c2fe,0,0x0,2,{0x4c308,0x4c30a}},
 {0x4c308,0,0x0,1,{0x4c30a}},
 {0x4c30a,1,0x4c32a,1,{0x469d8}},
 {0x4c32a,2,0x0,0,{0}},
 {0x4d6b4,0,0x0,2,{0x4d6c0,0x4d6c6}},
 {0x4d6c0,2,0x0,0,{0}},
 {0x4d6c6,0,0x0,2,{0x4d6cc,0x4d6d4}},
 {0x4d6cc,0,0x0,1,{0x4d6d8}},
 {0x4d6d4,0,0x0,1,{0x4d6d8}},
 {0x4d6d8,0,0x0,2,{0x4d6e0,0x4d6ec}},
 {0x4d6e0,2,0x0,0,{0}},
 {0x4d6ec,2,0x0,0,{0}},
 {0x4d734,0,0x0,2,{0x4d73a,0x4d742}},
 {0x4d73a,0,0x0,1,{0x4d746}},
 {0x4d742,0,0x0,1,{0x4d746}},
 {0x4d746,0,0x0,2,{0x4d750,0x4d75e}},
 {0x4d750,0,0x0,1,{0x4d75e}},
 {0x4d75e,2,0x0,0,{0}},
 {0x4d98a,0,0x0,2,{0x4d990,0x4d998}},
 {0x4d990,0,0x0,1,{0x4d99c}},
 {0x4d998,0,0x0,1,{0x4d99c}},
 {0x4d99c,2,0x0,0,{0}},
 {0x4d9ba,0,0x0,2,{0x4d9c6,0x4d9ca}},
 {0x4d9c6,0,0x0,1,{0x4d9ca}},
 {0x4d9ca,2,0x0,0,{0}},
 {0x4eea2,0,0x0,2,{0x4eeac,0x4eeb6}},
 {0x4eeac,0,0x0,1,{0x4eebc}},
 {0x4eeb6,0,0x0,1,{0x4eebc}},
 {0x4eebc,1,0x4eeea,1,{0x4f08a}},
 {0x4eeea,2,0x0,0,{0}},
 {0x4f08a,0,0x0,1,{0x4f0a8}},
 {0x4f0a8,0,0x0,2,{0x4f0a8,0x4f0b8}},
 {0x4f0b8,2,0x0,0,{0}},
 {0x4ff96,1,0x4ffb0,1,{0x2986}},
 {0x4ffb0,2,0x0,0,{0}},
 {0xd3d7c,1,0xd3d92,1,{0x2986}},
 {0xd3d92,0,0x0,1,{0x49214}},
};
// ---- generated table (end)
const unsigned int STEP_COUNT=sizeof(STEPS)/sizeof(STEPS[0]);
const std::uint32_t RANGES[][2]={{0x3383c,0x338f8},{0x33940,0x33958},{0x38d56,0x38dd4},{0x39f9c,0x3a048},{0x3a0dc,0x3a1e0},{0x3a4a4,0x3a4d6},
 {0x3a4da,0x3a5d2},{0x3acd6,0x3ad48},{0x3b424,0x3b458},{0x4bfc0,0x4c020},{0x4c2fa,0x4c340},{0x4c390,0x4c3ba},{0x4c3cc,0x4c3de},
 {0x4d418,0x4d508},{0x4d6b4,0x4d6f2},{0x4d734,0x4d766},{0x4d98a,0x4d9a2},{0x4d9ba,0x4d9d6},{0x4eea2,0x4eef4},{0x4f08a,0x4f0c4},
 {0x4ff96,0x4ffba},{0xd3d7c,0xd3d9c}};
const unsigned int RANGE_COUNT=sizeof(RANGES)/sizeof(RANGES[0]);
// RTS blocks that pop stack data first: offset of the return LONG from A7 (the popped LONGs are valid pointers).
const std::uint32_t RET_AT[][2]={{0x33948,2},{0x3a4c6,2},{0x4c32a,4},{0x4ffb0,4},{0x4eeea,8},{0x4d4c2,8}};
// Consumers: pc, target when C is clear, target when C is set.
const std::uint32_t CONSUMERS[][3]={{0x4d438,0x4d4ac,0x4d43c},{0x3a4ec,0x3a5b8,0x3a4f0},{0x3ad26,0x3ad2a,0x3ad30},{0x3ad3c,0x3ad46,0x3ad40},
 {0x38dbe,0x38dc8,0x38dc2},{0x38d70,0x38d7a,0x38d7a}};
const unsigned int CONSUMER_COUNT=sizeof(CONSUMERS)/sizeof(CONSUMERS[0]);
// Synthetic typed physical bytes: the BYTE pairs 3a4d6 (05 fd) / 3a4d8 (81 7f) and the banked LONG 2000b4.
Physical make_rom() {
    Physical p(2);
    p[0].source_rom_offset=0x3a4d6;p[0].data.push_back(0x05);p[0].data.push_back(0xfd);p[0].data.push_back(0x81);p[0].data.push_back(0x7f);
    p[1].source_rom_offset=0x2000b4;p[1].data.push_back(0x12);p[1].data.push_back(0x34);p[1].data.push_back(0x56);p[1].data.push_back(0x78);
    return p;
}
const Physical ROM=make_rom();
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v) {for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n) {std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
std::vector<std::uint8_t> pvc_base() {std::vector<std::uint8_t> p(8192,0);p[0x1ff1]=0xa0;p[0x1ff2]=0x10;return p;}
struct Out {
    ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
    Out():reads(99),status(ms5::AnimationMachineWaiting) {
        dev.bank_base=0x200000;dev.pvc=pvc_base();ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);
    }
};
ms5::ProgramBusState bus_of() {ms5::ProgramBusState bus;bus.physical_rom=&ROM;return bus;}
std::uint32_t ret_offset(std::uint32_t pc) {for(unsigned int i=0;i<6;++i)if(RET_AT[i][0]==pc)return RET_AT[i][1];return 0;}
bool in_ranges(std::uint32_t pc) {for(unsigned int i=0;i<RANGE_COUNT;++i)if(pc>=RANGES[i][0]&&pc<RANGES[i][1])return true;return false;}
bool is_step(std::uint32_t pc) {for(unsigned int i=0;i<STEP_COUNT;++i)if(STEPS[i].pc==pc)return true;return false;}
bool is_consumer(std::uint32_t pc) {for(unsigned int i=0;i<CONSUMER_COUNT;++i)if(CONSUMERS[i][0]==pc)return true;return false;}
// Declared world. variant 0: zero RAM; variant 1: node bytes 00..c3 = 01 (flags set, WORD 0101, LONG 01010101 never dereferenced inside a block).
void world(Bytes&ram,State&s,std::uint32_t pc,unsigned int variant) {
    ram.assign(65536,0);State fresh;s=fresh;
    if(variant==1)for(unsigned int i=0;i<0xc4;++i)ram[(NODE+i)&65535U]=1;
    for(unsigned int i=0;i<8;++i)s.d[i]=0x11110000U*(i+1U)+i;
    s.a[0]=P0;s.a[1]=P1;s.a[2]=P2;s.a[3]=P3;s.a[4]=SLOT0;s.a[5]=A5;s.a[6]=NODE;s.a[7]=SP;s.pc=pc;s.carry=AnimationCarryUnknown;
    const std::uint32_t off=ret_offset(pc);
    for(std::uint32_t i=0;i+4<=off;i+=4)put(ram,SP+i,4,P0);                    // popped LONGs are valid pointers
    put(ram,SP+off,4,SENT);
    if(pc==0x3a52e || pc==0x3a584)put(ram,SP,4,0x3a4d6);                       // MOVEA.L (A7),A4 / (A7)+,A4 -> the BYTE pair in ROM
    if(pc==0x4d4c2){put(ram,SP,4,0x10);put(ram,SP+4,4,0x20);}                  // MOVEM.L (A7)+,D0-D1
}
bool step(Bytes&ram,State&s,Out&o,std::string&error) {
    std::vector<ms5::FixedDataResource> w;const ms5::ProgramBusState bus=bus_of();
    ms5::AnimationMachineContext c(ram,w,bus,s,o.dev,o.ports,0,error);
    return ms5::animation_objects_b2b_block(c);
}
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o) {
    std::vector<ms5::FixedDataResource> w;const ms5::ProgramBusState bus=bus_of();
    o.ports.clear();o.error.clear();
    return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
}
bool same(const State&a,const State&b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;
}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message) {
    const Bytes before=ram;const State old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;
    std::vector<ms5::FixedDataResource> w;const ms5::ProgramBusState bus=bus_of();
    const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
    if(ok)std::cerr<<std::hex<<"unexpected success at "<<old.pc<<"\n";
    if(o.error!=message)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
    check(!ok && o.error==message,"checked error",old.pc);
    check(ram==before && same(s,old) && dev.pvc==o.dev.pvc && dev.bank_base==o.dev.bank_base && o.reads==99 && o.status==ms5::AnimationMachineWaiting &&
        o.ports.size()==1 && o.ports[0].address==0xdeadbeef && o.ports[0].value==0x87 && o.ports[0].size==1,"failure preserves every output",old.pc);
}
// ---- Part 1: one step of every block start in two worlds.
void steps() {
    check(STEP_COUNT==209,"209 block starts",STEP_COUNT);
    for(unsigned int i=0;i<STEP_COUNT;++i) {
        const Step&t=STEPS[i];
        check(in_ranges(t.pc),"block start inside the routed ranges",t.pc);
        for(unsigned int variant=0;variant<2;++variant) {
            if(is_consumer(t.pc))continue;                                       // consumers need a known C: Part 2
            Bytes ram;State s;Out o;std::string error;world(ram,s,t.pc,variant);
            const std::uint32_t a0=s.a[0];
            const bool ok=step(ram,s,o,error);
            if(!ok)std::cerr<<std::hex<<"step "<<t.pc<<" variant "<<variant<<": "<<error<<"\n";
            check(ok,"block step succeeds",t.pc,variant);
            if(t.kind==2) {
                check(s.pc==SENT,"RTS pops the declared return LONG",t.pc,s.pc);
            } else if(t.kind==1 && t.n==0) {
                check(s.pc==a0,"JSR (A0) goes to the live A0",t.pc,s.pc);
                check(get(ram,s.a[7],4)==t.ret,"JSR pushes the return LONG",t.pc,get(ram,s.a[7],4));
            } else {
                bool found=false;for(unsigned int k=0;k<t.n;++k)if(t.succ[k]==s.pc)found=true;
                if(!found)std::cerr<<std::hex<<"step "<<t.pc<<" variant "<<variant<<" went to "<<s.pc<<"\n";
                check(found,"successor is a static successor of the original block",t.pc,s.pc);
                if(t.kind==1)check(get(ram,s.a[7],4)==t.ret,"JSR / BSR pushes the return LONG",t.pc,get(ram,s.a[7],4));
            }
        }
    }
}
// ---- Part 2 helpers.
void expect_run(Bytes&ram,State&s,Out&o,std::uint32_t stop) {
    const bool ok=run(ram,s,stop,o);
    if(!ok)std::cerr<<std::hex<<"run from stop "<<stop<<": "<<o.error<<"\n";
    check(ok && s.pc==stop,"run reaches the stop PC",stop,s.pc);
}
// 4d418 world: D0.B choice, D2/D3 offsets, node A6 fields, target node (A0 = TARGET), slot A4.
void slot_world(Bytes&ram,State&s,std::uint32_t pc,bool second) {
    world(ram,s,pc,0);
    s.d[0]=second?1U:0U;s.d[2]=0x1234;s.d[3]=0x5678;
    put(ram,NODE+0x3e,4,0x100111);put(ram,NODE+0x2e,4,0x222222);put(ram,NODE+0x32,4,0x333333);
    put(ram,NODE+0x15,1,3);put(ram,NODE+0x5e,1,7);
    const std::uint32_t target=second?TARGET1:TARGET0;
    put(ram,target,4,0x12345);put(ram,target+0x60,1,0x44);put(ram,target+0x76,2,0xabcd);   // (A0) != 270e: 289e returns Set
}
void part_4d418() {
    for(unsigned int second=0;second<2;++second) {
        const std::uint32_t slot=second?SLOT1:SLOT0;
        // Set path (4d490 ORI.B #1,CCR): every slot field written, D0.W = target WORD 76, C = Set.
        Bytes ram;State s;Out o;slot_world(ram,s,0x4d418,second!=0U);expect_run(ram,s,o,SENT);
        check(s.carry==AnimationCarrySet,"4d418 Set path returns C = Set");
        check(get(ram,slot,2)==(NODE&65535U) && get(ram,slot+2,2)==0x1234 && get(ram,slot+4,2)==0x5678,"slot owner and offsets");
        check(get(ram,slot+0xc,4)==0x100111 && get(ram,slot+0x10,4)==0x222222 && get(ram,slot+0x14,4)==0x333333,"slot position copies");
        check(get(ram,slot+0x22,1)==0xff && get(ram,slot+0x23,1)==1 && get(ram,slot+0x24,1)==7 && get(ram,slot+0x28,1)==3,"slot BYTEs");
        check(get(ram,slot+0x18,2)==get(ram,A5-0x7ff2,2),"slot WORD 18 = -7ff2(A5)");
        check((s.d[0]&65535U)==0xabcd && get(ram,NODE+0x60,1)==0x44,"D0.W = WORD 76 of the target, BYTE 60 copied");
        check(s.d[7]==NODE,"D7 = A6");
        // Clear paths (4d4ac: ANDI.B #fe,CCR; MOVEQ #0,D0).
        slot_world(ram,s,0x4d418,second!=0U);put(ram,second?TARGET1+0x61:TARGET0+0x61,1,0x80);expect_run(ram,s,o,SENT);       // target BYTE 61 bit 7
        check(s.carry==AnimationCarryClear && s.d[0]==0 && get(ram,slot,2)==0,"4d418 BYTE 61 bit 7 -> Clear, D0 = 0, slot untouched");
        slot_world(ram,s,0x4d418,second!=0U);put(ram,second?TARGET1:TARGET0,4,0x270e);expect_run(ram,s,o,SENT);               // 289e Clear (idle callback)
        check(s.carry==AnimationCarryClear && s.d[0]==0,"4d418 readiness Clear -> Clear");
        slot_world(ram,s,0x4d418,second!=0U);put(ram,slot,2,0x4444);expect_run(ram,s,o,SENT);                               // slot owned by another node
        check(s.carry==AnimationCarryClear && get(ram,slot,2)==0x4444 && get(ram,slot+2,2)==0,"4d418 slot owned by another node -> Clear, no write");
        slot_world(ram,s,0x4d418,second!=0U);put(ram,slot,2,NODE&65535U);put(ram,slot+0x22,1,9);expect_run(ram,s,o,SENT);   // own slot but BYTE 22 != 0
        check(s.carry==AnimationCarryClear && get(ram,slot+2,2)==0x1234 && get(ram,slot+0x22,1)==9,"4d418 own busy slot -> Clear after the field copies");
        slot_world(ram,s,0x4d418,second!=0U);put(ram,slot,2,NODE&65535U);expect_run(ram,s,o,SENT);                           // own free slot
        check(s.carry==AnimationCarrySet && get(ram,slot,2)==(NODE&65535U),"4d418 own free slot -> Set");
        slot_world(ram,s,0x4d418,second!=0U);put(ram,NODE+0x5e,1,0);expect_run(ram,s,o,SENT);                               // BYTE 5e == 0: 24(A4) not written
        check(s.carry==AnimationCarrySet && get(ram,slot+0x24,1)==0,"4d418 BYTE 5e = 0 leaves 24(A4)");
    }
    // The real consumers: 31a04 (N29a BCC) and 33212 (N30a BCC) branch on the returned C. Set: fall through; Clear: branch.
    const std::uint32_t consumers[2][3]={{0x31a04,0x31a10,0x31a08},{0x33212,0x3323a,0x33216}};
    for(unsigned int k=0;k<2;++k)for(unsigned int clear=0;clear<2;++clear) {
        Bytes ram;State s;Out o;slot_world(ram,s,0x4d418,false);put(ram,SP,4,consumers[k][0]);if(clear!=0U)put(ram,TARGET0+0x61,1,0x80);
        expect_run(ram,s,o,clear!=0U?consumers[k][1]:consumers[k][2]);
    }
}
// 4d4b4 world: D0 choice, D1 value, BYTE 15(A6), BYTE 5e(A6), slot (A4).W.
void part_4d4b4() {
    for(unsigned int second=0;second<2;++second) {
        const std::uint32_t slot=second?SLOT1:SLOT0;
        for(unsigned int mode=0;mode<4;++mode) {   // 0 own slot, 1 other owner above (borrow), 2 other owner below, 3 own slot with BYTE 5e = 0
            Bytes ram;State s;Out o;world(ram,s,0x4d4b4,0);
            s.d[0]=second?1U:0U;s.d[1]=9;put(ram,NODE+0x15,1,0x21);put(ram,NODE+0x5e,1,mode==3?0U:4U);
            const std::uint32_t owner=NODE&65535U;
            put(ram,slot,2,mode==1?owner+1U:(mode==2?owner-1U:owner));put(ram,slot+0x22,1,5);put(ram,slot+0x24,1,0x77);
            expect_run(ram,s,o,SENT);
            if(mode==1)check(s.carry==AnimationCarrySet && get(ram,slot,2)==owner+1U,"4d4b4 other owner above: borrow of CMP.W, Set, no write");
            else if(mode==2)check(s.carry==AnimationCarryClear && get(ram,slot,2)==owner-1U,"4d4b4 other owner below: no borrow, Clear, no write");
            else {
                check(s.carry==AnimationCarryClear && get(ram,slot,2)==0 && get(ram,slot+0x22,1)==2 && get(ram,slot+0x23,1)==9,"4d4b4 own slot is released");
                check(get(ram,slot+0x28,1)==0,"4d4b4 BYTE 28 = D2.B (D2.W = 0 after 4eea2)");
                check(get(ram,slot+0x24,1)==(mode==3?0x77U:4U),"4d4b4 BYTE 24 only for BYTE 5e != 0");
            }
            // 4eea2: the six WORD clears at 88 8a 8c 8e 90 94 of block 1009a8 (D0.W == 0) / 100a6c, then seven LONG ports 3c0000.
            const std::uint32_t block=second?0x100a6c:0x1009a8;
            for(unsigned int i=0;i<6;++i) {
                static const std::uint32_t at[6]={0x88,0x8a,0x8c,0x8e,0x90,0x94};check(get(ram,block+at[i],2)==0,"4eea2 clears the WORDs",block,at[i]);
            }
            check(o.ports.size()==7,"4f08a writes seven LONGs",static_cast<std::uint32_t>(o.ports.size()));
            for(unsigned int k=0;k<o.ports.size() && k<7;++k)
                check(o.ports[k].address==0x3c0000 && o.ports[k].size==4 && o.ports[k].value==0x320U+0x200000U*k,"port value 0320 + k*200000",k,o.ports[k].value);
        }
    }
    // Port values follow WORD 80(A6) of the selected block (SWAP) and wrap in 32 bits.
    Bytes ram;State s;Out o;world(ram,s,0x4d4b4,0);put(ram,0x1009a8+0x80,2,0xfff0);put(ram,SLOT0,2,1);expect_run(ram,s,o,SENT);
    check(o.ports.size()==7 && o.ports[0].value==0xfff00320U && o.ports[1].value==0x00100320U && o.ports[6].value==0xfff00320U+0xc00000U,"4f08a wraps modulo 2^32");
    // A real return LONG on a known-C consumer is not needed: the 4d4b4 C has no routed consumer; 4d4e0 returns the borrow, 4d506 passes it.
    Bytes r2;State s2;Out o2;world(r2,s2,0x4d4e0,0);s2.a[4]=SLOT0;put(r2,SLOT0,2,0x0001);expect_run(r2,s2,o2,SENT);
    check(s2.carry==AnimationCarryClear,"4d4e0: (A4).W 1 < D7.W e000: no borrow");
    put(r2,SLOT0,2,0xf000);world(r2,s2,0x4d4e0,0);s2.a[4]=SLOT0;put(r2,SLOT0,2,0xf000);expect_run(r2,s2,o2,SENT);
    check(s2.carry==AnimationCarrySet,"4d4e0: (A4).W f000 > D7.W e000: borrow, Set, passed by 4d506");
}
// The table 3a0e8 -> 3a0f4 + 4 * D0.B and the bound test 3a0dc.
void part_table() {
    for(unsigned int k=0;k<27;++k) {
        Bytes ram;State s;Out o;world(ram,s,0x3a0e8,0);s.d[0]=0x77770000U|k;
        expect_run(ram,s,o,k==24?0x3a24cU:0x3a160U);                               // slot 24 (3a154) goes to the N33 exit 3a24c, the others to 3a160
        check((s.d[0]&65535U)==4U*k && (s.d[0]>>16)==0x7777U,"table index is 4 * D0.B in D0.W",k,s.d[0]);
    }
    {   // D0.B = 27 lands on 3a160 itself (the original has no limit test in this block); 28 lands inside an instruction: checked error.
        Bytes ram;State s;Out o;world(ram,s,0x3a0e8,0);s.d[0]=27;expect_run(ram,s,o,0x3a160);
        world(ram,s,0x3a0e8,0);s.d[0]=28;reject(ram,s,SENT,"unsupported animation objects b2b PC");
    }
    const unsigned int bytes5e[4]={0x00,0x18,0x1a,0x1b};
    const std::uint32_t stops[4]={0x3a160,0x3a24c,0x3a160,0x3a160};
    for(unsigned int k=0;k<4;++k) {
        Bytes ram;State s;Out o;world(ram,s,0x3a0dc,0);put(ram,NODE+0x5e,1,bytes5e[k]);s.d[0]=0xabcdef00U;expect_run(ram,s,o,stops[k]);
        check(k==3 ? (s.d[0]&255U)==0x1bU : (s.d[0]&65535U)==4U*bytes5e[k],"3a0dc: BYTE 5e below 1b selects slot 5e, else 3a160",k,s.d[0]);
    }
}
// Chains with C: producers followed by consumers, the RTS blocks that keep the C, and the helper semantics.
void part_carry() {
    // Consumers (step): C clear / set go to their two targets; Unknown C is a checked error.
    for(unsigned int i=0;i<CONSUMER_COUNT;++i) {
        for(unsigned int c=0;c<2;++c) {
            Bytes ram;State s;Out o;std::string error;world(ram,s,CONSUMERS[i][0],0);s.carry=c==0?AnimationCarryClear:AnimationCarrySet;
            if(CONSUMERS[i][0]==0x38d70) {                                           // SCC.B 62(A6): ff when C is clear, then JSR 4972c
                check(step(ram,s,o,error) && s.pc==0x4972c && get(ram,NODE+0x62,1)==(c==0?0xffU:0U) && get(ram,s.a[7],4)==0x38d7a,"38d70 SCC",c);
                continue;
            }
            const bool ok=step(ram,s,o,error);
            check(ok && s.pc==CONSUMERS[i][c==0?1:2],"consumer branches on the known C",CONSUMERS[i][0],c);
        }
        Bytes ram;State s;world(ram,s,CONSUMERS[i][0],0);
        reject(ram,s,SENT,"objects b2b caller requires known carry");
    }
    // The Unknown C a plain run gives: the run clears C at a block that is not in the carry list, so a consumer entered by a run has C only from a producer.
    // 4d6b4 -> 3a4ec: Clear (BYTE 25 = 0) goes to 3a5b8 (ANDI.B #fe,CCR; RTS) and returns Clear; Set (BYTE 25 = 3) falls to 3a4f0.
    {
        Bytes ram;State s;Out o;world(ram,s,0x3a4e2,0);put(ram,NODE+0x86,2,0x1234);put(ram,0x10f001,1,0);put(ram,SLOT1+0x25,1,0);s.d[0]=0;put(ram,SLOT0+0x25,1,0);
        expect_run(ram,s,o,SENT);check(s.carry==AnimationCarryClear && (s.d[0]&65535U)==0x1200,"3a4e2 -> 4d6b4 Clear -> 3a4ec -> 3a5b8: Clear");
        world(ram,s,0x3a4e2,0);put(ram,SLOT0+0x25,1,3);expect_run(ram,s,o,0x3a4f0);
        check(s.carry==AnimationCarrySet && get(ram,SLOT0+0x25,1)==2 && (s.d[0]&255U)==2U,"4d6b4 BYTE 25 = 3: decremented, Set -> 3a4f0");
        world(ram,s,0x3a4e2,0);put(ram,0x10f001,1,4);expect_run(ram,s,o,0x3a4f0);check(s.carry==AnimationCarrySet,"4d6b4 work BYTE bit 2: Set");
        world(ram,s,0x4d6b4,0);s.d[0]=1;put(ram,SLOT1+0x25,1,1);expect_run(ram,s,o,SENT);
        check(s.carry==AnimationCarrySet && get(ram,SLOT1+0x25,1)==0 && (s.d[0]&255U)==0U,"4d6b4 D0.B != 0 selects the second slot");
    }
    // 3a4f0: BYTE 9f below 11 loads the pair 3a4d6, else 3a4d8.
    for(unsigned int k=0;k<2;++k) {
        Bytes ram;State s;Out o;world(ram,s,0x3a4f0,0);put(ram,NODE+0x9f,1,k==0?0x10U:0x11U);expect_run(ram,s,o,0x3a506);
        check(s.a[4]==(k==0?0x3a4d6U:0x3a4d8U),"3a4f0 pair address",k,s.a[4]);
    }
    // 3a52e / 3a584: the signed BYTE pair (05 fd | 81 7f); BYTE 15 bit 0 only selects the mirror blocks 3a542 / 3a5a0.
    for(unsigned int mirror=0;mirror<2;++mirror)for(unsigned int hi=0;hi<2;++hi) {
        Bytes ram;State s;Out o;std::string error;world(ram,s,0x3a52e,0);put(ram,SP,4,hi==0?0x3a4d6U:0x3a4d8U);put(ram,NODE+0x15,1,mirror);
        check(step(ram,s,o,error),"3a52e step");
        const std::uint32_t d2=hi==0?5U:0xff81U,d3=hi==0?0xfffdU:0x7fU;
        check((s.d[2]&65535U)==d2 && (s.d[3]&65535U)==d3 && s.a[4]==(hi==0?0x3a4d7U:0x3a4d9U) && s.pc==(mirror==0?0x3a544U:0x3a542U),
            "3a52e BYTE pair",mirror,hi);
        world(ram,s,0x3a584,0);put(ram,SP,4,hi==0?0x3a4d6U:0x3a4d8U);put(ram,NODE+0x15,1,mirror);put(ram,NODE+0x60,1,0x5a);
        check(step(ram,s,o,error) && get(ram,P0+0x60,1)==0x5a && s.a[7]==SP+4U && s.d[0]==0U && s.pc==(mirror==0?0x3a5a6U:0x3a5a0U),"3a584",mirror,hi);
    }
    {   // 3a542 / 3a5a0: NEG.W D2 (and ADDI.W #8000,D0).
        Bytes ram;State s;Out o;std::string error;world(ram,s,0x3a542,0);s.d[2]=0x12340005;check(step(ram,s,o,error) && s.d[2]==0x1234fffbU && s.pc==0x3a544,"3a542 NEG.W");
        world(ram,s,0x3a5a0,0);s.d[0]=0;s.d[2]=0xff81;check(step(ram,s,o,error) && s.d[0]==0x8000U && (s.d[2]&65535U)==0x7fU && s.pc==0x3a5a6,"3a5a0");
    }
    // 3a5b2 / 3a5b8 / 4d6c0 / 4d6ec: known C of ORI / ANDI + RTS.
    {
        const std::uint32_t pcs[4]={0x3a5b2,0x3a5b8,0x4d6c0,0x4d6ec};
        for(unsigned int i=0;i<4;++i) {
            Bytes ram;State s;Out o;world(ram,s,pcs[i],0);expect_run(ram,s,o,SENT);
            check(s.carry==((i&1U)==0?AnimationCarrySet:AnimationCarryClear),"ORI / ANDI + RTS known C",pcs[i]);
        }
    }
    // 33948 / 3a4c6: MOVE.B (A7)+,D1; TST.B D0; BPL -> JMP 4d4b4 / RTS (Clear, kept through the RTS block 33950 / 3a4ce).
    for(unsigned int k=0;k<2;++k) {
        const std::uint32_t pc=k==0?0x33948U:0x3a4c6U;
        Bytes ram;State s;Out o;world(ram,s,pc,0);put(ram,SP,2,0x5500);s.d[0]=0x80;s.d[1]=0x12345678;expect_run(ram,s,o,SENT);
        check(s.carry==AnimationCarryClear && (s.d[1]&255U)==0x55U && (s.d[1]>>8)==0x123456U,"RTS path keeps Clear",pc);
        world(ram,s,pc,0);s.d[0]=0x7f;expect_run(ram,s,o,0x4d4b4);check(s.carry==AnimationCarryUnknown,"BPL path: JMP 4d4b4",pc);
    }
    // 4d4e0 -> 4d506 passes the CMP borrow through the RTS block; 4d4e8 / 4d502 give Clear.
    {
        Bytes ram;State s;Out o;world(ram,s,0x4d4e8,0);s.a[4]=SLOT0;put(ram,NODE+0x5e,1,0);expect_run(ram,s,o,SENT);check(s.carry==AnimationCarryClear,"4d4e8 Clear");
        world(ram,s,0x4d502,0);s.a[4]=SLOT0;s.d[0]=0x66;expect_run(ram,s,o,SENT);check(s.carry==AnimationCarryClear && get(ram,SLOT0+0x24,1)==0x66,"4d502 Clear");
    }
    // 3b448 keeps C (BTST), 3b452 clears it (ANDI.W), 3b456 is the RTS; 3b42e returns Clear (OR.B).
    {
        Bytes ram;State s;Out o;world(ram,s,0x3b448,0);s.carry=AnimationCarrySet;std::string error;
        check(step(ram,s,o,error) && s.pc==0x3b456 && s.carry==AnimationCarrySet,"3b448 BTST keeps C");
        world(ram,s,0x3b448,0);put(ram,NODE+0x15,1,0x80);s.d[0]=0xffffffff;check(step(ram,s,o,error) && s.pc==0x3b452,"3b448 bit 7 set");
        s.pc=0x3b452;s.carry=AnimationCarrySet;check(step(ram,s,o,error) && s.pc==0x3b456 && s.d[0]==0xfffffdfdU && s.carry==AnimationCarryClear,"3b452 ANDI.W #fdfd,D0 clears C");
        world(ram,s,0x3b42e,0);put(ram,P0,4,0x00ff0f0f);put(ram,NODE+0x9e,1,0x3c);put(ram,NODE+0x9d,1,0x81);s.a[0]=P0;
        check(step(ram,s,o,error) && s.pc==SENT && s.carry==AnimationCarryClear,"3b42e RTS Clear");
        // D7 = SWAP (A0) = 0f0f00ff, D0 = ff & 3c = 3c... D0.B = (0f0f00ff.B = ff) & 3c = 3c; 9d |= 3c -> bd.
        check(get(ram,NODE+0x9d,1)==0xbdU && s.d[7]==0x0f0f00ffU && (s.d[0]&255U)==0x3cU && (s.d[1]&65535U)==0xffffU,"3b42e AND / OR");
    }
    // 4bfce ADD.B D7,D7; BCC.W 4bf0a: the carry is bit 7 of the old D7.B.
    {
        Bytes ram;State s;Out o;std::string error;world(ram,s,0x4bfce,0);s.d[7]=0x12345680;check(step(ram,s,o,error) && s.pc==0x4bfd4 && s.d[7]==0x12345600U,"4bfce C set");
        world(ram,s,0x4bfce,0);s.d[7]=0x12345640;check(step(ram,s,o,error) && s.pc==0x4bf0a && s.d[7]==0x12345680U,"4bfce C clear");
    }
    // 4c2fe: MOVE.B #2,D1; SUB.B D0,D1; BCC.W 4c30a / MOVEQ #0,D1; 4c32a: ANDI.W #3,D6, Clear.
    {
        Bytes ram;State s;Out o;std::string error;
        world(ram,s,0x4c2fe,0);s.d[0]=1;s.d[1]=0xaabbccdd;check(step(ram,s,o,error) && s.pc==0x4c30a && s.d[1]==0xaabbcc01U,"4c2fe no borrow");
        world(ram,s,0x4c2fe,0);s.d[0]=3;check(step(ram,s,o,error) && s.pc==0x4c308,"4c2fe borrow");
        world(ram,s,0x4c308,0);s.d[1]=7;check(step(ram,s,o,error) && s.d[1]==0 && s.pc==0x4c30a,"4c308 MOVEQ #0,D1");
        world(ram,s,0x4c32a,0);s.d[6]=0xffffffff;s.d[0]=0x11;s.d[1]=0x22;s.a[0]=0x4444;
        check(step(ram,s,o,error) && s.pc==SENT && s.carry==AnimationCarryClear && (s.d[6]&65535U)==3U && s.a[1]==0x4444U && s.a[0]==P0 &&
            get(ram,P0+0x2e,4)==0x11 && get(ram,P0+0x32,4)==0x22 && get(ram,P0+0x3e,4)==0x4444,"4c32a stores D0 D1 A1 through the popped A0");
    }
    // 4ffb0: BYTE then WORD popped from the stack into 78(A0) / 76(A0), Clear.
    {
        Bytes ram;State s;Out o;world(ram,s,0x4ffb0,0);put(ram,SP,2,0x9900);put(ram,SP+2,2,0x7766);expect_run(ram,s,o,SENT);
        check(s.carry==AnimationCarryClear && get(ram,P0+0x78,1)==0x99 && get(ram,P0+0x76,2)==0x7766 && s.a[7]==SP+8U,"4ffb0");
    }
    // 4d734 / 4d98a / 4d9ba: slot helpers.
    {
        Bytes ram;State s;Out o;world(ram,s,0x4d734,0);s.d[0]=0;put(ram,NODE+0x61,1,0);put(ram,SLOT0+0x1a,2,5);put(ram,NODE+0x54,2,0xfffe);expect_run(ram,s,o,SENT);
        check(s.carry==AnimationCarryClear && get(ram,NODE+0x54,2)==3 && get(ram,SLOT0+0x1a,2)==0 && get(ram,SLOT0+0x1c,2)==3,"4d734 accumulates the slot WORD 1a");
        world(ram,s,0x4d734,0);s.d[0]=2;put(ram,NODE+0x61,1,0x80);put(ram,NODE+0x54,2,0x1357);put(ram,SLOT1+0x1a,2,5);expect_run(ram,s,o,SENT);
        check(get(ram,SLOT1+0x1c,2)==0x1357 && get(ram,SLOT1+0x1a,2)==5,"4d734 BYTE 61 bit 7 skips the accumulation");
        world(ram,s,0x4d98a,0);s.d[7]=0x1234;s.d[0]=0;expect_run(ram,s,o,SENT);check(s.carry==AnimationCarryClear && get(ram,SLOT0+0x29,1)==0x34,"4d98a");
        world(ram,s,0x4d98a,0);s.d[7]=0x1234;s.d[0]=9;expect_run(ram,s,o,SENT);check(get(ram,SLOT1+0x29,1)==0x34 && get(ram,SLOT0+0x29,1)==0,"4d98a second slot");
        world(ram,s,0x4d9ba,0);s.d[0]=0;s.a[1]=0x55667788;expect_run(ram,s,o,SENT);
        check(s.carry==AnimationCarryClear && s.d[0]==NODE && get(ram,SLOT0+6,2)==(NODE&65535U) && get(ram,SLOT0+8,4)==0x55667788U,"4d9ba");
        world(ram,s,0x4d9ba,0);s.d[0]=3;expect_run(ram,s,o,SENT);check(get(ram,SLOT1+6,2)==(NODE&65535U),"4d9ba second slot");
    }
    // 3a5be: JSR (A0) with a live target; the return half restores 9a(A6).
    {
        Bytes ram;State s;Out o;world(ram,s,0x3a5be,0);s.a[0]=0xff100;put(ram,NODE+0x9a,1,0x5c);expect_run(ram,s,o,0xff100);
        check(get(ram,NODE+0x97,1)==0xff && get(ram,NODE+0x99,1)==0x5c && get(ram,s.a[7],4)==0x3a5ca,"3a5be sets 97, copies 9a to 99, pushes 3a5ca");
        world(ram,s,0x3a5ca,0);put(ram,NODE+0x99,1,0x33);put(ram,NODE+0x9a,1,0x44);expect_run(ram,s,o,SENT);
        check(get(ram,NODE+0x9a,1)==0x33 && s.carry==AnimationCarryClear,"3a5ca copies 99 back, Clear");
        world(ram,s,0x3a5be,0);s.a[0]=0x10fe00;reject(ram,s,SENT,"unsupported animation machine PC");   // work-RAM probe (3a60a is routed by B2c)
        world(ram,s,0x3a5be,0);s.a[0]=0x3a5d3;reject(ram,s,SENT,"unaligned animation machine PC");
    }
    // 3a4a4 -> JMP 4d418 (stop at 4d418): D0 = WORD 86, D2 = +2 / -2 by BYTE 15 bit 0, D3 = 1e.
    for(unsigned int k=0;k<2;++k) {
        Bytes ram;State s;Out o;world(ram,s,0x3a4a4,0);put(ram,NODE+0x86,2,0xabcd);put(ram,NODE+0x15,1,k);expect_run(ram,s,o,0x4d418);
        check((s.d[0]&65535U)==0xabcd && s.d[2]==(k==0?2U:0xfffeU) && s.d[3]==0x1e,"3a4a4",k);
    }
}
// Straight-line semantic fixtures of the chains: the child values are data and the calls stop at the first boundary.
void part_chains() {
    {   // 3383c: LEA 349ee(PC),A0; JSR 4ae4a.
        Bytes ram;State s;Out o;world(ram,s,0x3383c,0);expect_run(ram,s,o,0x4ae4a);check(s.a[0]==0x349ee && get(ram,s.a[7],4)==0x33846,"3383c");
        world(ram,s,0x3385e,0);s.a[0]=P0;expect_run(ram,s,o,0xd3d7c);
        check(get(ram,P0+0x36,4)==0xfff20000U && get(ram,P0+0x3a,4)==0x280000U && get(ram,P0+0x54,2)==0xa && get(ram,s.a[7],4)==0x3387a,"3385e row");
        world(ram,s,0x338b2,0);s.a[0]=P0;expect_run(ram,s,o,0x2986);
        check(s.a[0]==0x338f8 && (s.d[0]&65535U)==0x1e && s.a[1]==0x100bf4 && get(ram,s.a[7],4)==0x338de && get(ram,P0+0x36,4)==0x70000U &&
            get(ram,P0+0x3a,4)==0xfffc0000U && get(ram,P0+0x54,2)==5,"338b2: last row, child 338f8 through 2986");
        world(ram,s,0x338e8,0);expect_run(ram,s,o,0x3af8);check((s.d[0]&65535U)==0x18de && get(ram,s.a[7],4)==0x338f2,"338e8 sound");
        world(ram,s,0x338f2,0);expect_run(ram,s,o,0x2a00);
    }
    {   // 4ff96 / d3d7c: 2986 with the child values 4ffba / d3d9c (data).
        Bytes ram;State s;Out o;world(ram,s,0x4ff96,0);s.d[0]=0x4321;s.d[1]=0x99;expect_run(ram,s,o,0x2986);
        check(s.a[0]==0x4ffba && (s.d[0]&65535U)==0x14 && s.a[1]==0x100bf4 && get(ram,s.a[7],4)==0x4ffb0 && get(ram,s.a[7]+4,1)==0x99 && get(ram,s.a[7]+6,2)==0x4321 && s.a[7]==SP-8U,"4ff96");
        world(ram,s,0xd3d7c,0);expect_run(ram,s,o,0x2986);check(s.a[0]==0xd3d9c && (s.d[0]&65535U)==0x1e && s.a[1]==0x100bf4 && get(ram,s.a[7],4)==0xd3d92,"d3d7c");
        world(ram,s,0xd3d92,0);s.d[0]=5;s.d[1]=6;expect_run(ram,s,o,0x49214);check(s.d[0]==0 && s.d[1]==0,"d3d92 JMP 49214");
    }
    {   // 38d56: stop at 3b5a6 (routed by B2c; stop-only check); work-RAM rollback probes 10fe02 and 10fe06 (3a1b2 -> 4db18 is routed by B2e).
        Bytes ram;State s;Out o;world(ram,s,0x38d56,0);expect_run(ram,s,o,0x3b5a6);check(get(ram,NODE+0xb5,1)==0xff && get(ram,s.a[7],4)==0x38d60,"38d56");
        world(ram,s,0x10fe02,0);reject(ram,s,SENT,"unsupported animation machine PC");
        world(ram,s,0x10fe06,0);reject(ram,s,SENT,"unsupported animation machine PC");
        world(ram,s,0x38d80,0);put(ram,NODE+0x62,1,0xff);expect_run(ram,s,o,0x3af8);check((s.d[0]&65535U)==0x1a60,"38d80 BYTE 62 != 0");
        world(ram,s,0x38dc2,0);expect_run(ram,s,o,0x3b2ee);check(get(ram,NODE,4)==0x39366 && (s.d[0]&65535U)==0x1e,"38dc2 installs 39366");
        world(ram,s,0x38d7a,0);expect_run(ram,s,o,0x3b288);check(get(ram,NODE,4)==0x38d80,"38d7a installs 38d80");
    }
    {   // 3acd6: banked LONG 2000b4 (synthetic 12345678), BSET 6, WORDs, JSR 49f8c.
        Bytes ram;State s;Out o;world(ram,s,0x3acd6,0);put(ram,NODE+0x15,1,1);expect_run(ram,s,o,0x49f8c);
        check(get(ram,NODE+0x20,2)==0x122 && get(ram,NODE+0x22,4)==0x12345678U && get(ram,NODE+0x15,1)==0x41 && get(ram,NODE+0x68,2)==0xe000 &&
            get(ram,NODE+0x1e,2)==0xe000 && s.a[1]==0x3ccfc && (s.d[0]&65535U)==0x100,"3acd6");
        world(ram,s,0x3ad06,0);expect_run(ram,s,o,0x8ebe);check((s.d[0]&65535U)==0xdb3 && (s.d[1]&255U)==0,"3ad06");
    }
    {   // 39f9c family and the 4c390 fragments.
        Bytes ram;State s;Out o;world(ram,s,0x39f9c,0);expect_run(ram,s,o,0x3c44);check((s.d[0]&65535U)==0x1ac8,"39f9c");
        world(ram,s,0x3a014,0);s.a[0]=P0;expect_run(ram,s,o,0x28ae);check(s.a[0]==0x3a2fa && (s.d[0]&65535U)==0x1e,"3a014 child 3a2fa");
        world(ram,s,0x3a044,0);expect_run(ram,s,o,0x3a2f4);
        world(ram,s,0x3a1c6,0);expect_run(ram,s,o,0x3af8);check(get(ram,NODE+0xa4,1)==0 && get(ram,NODE+0xa7,1)==0x60,"3a1c6");
        world(ram,s,0x3a1da,0);expect_run(ram,s,o,0x3a1e0);check(get(ram,NODE,4)==0x3a1e0,"3a1da falls into the N33 callback 3a1e0");
        world(ram,s,0x4c390,0);s.a[0]=0x10c777;put(ram,A5+0x5c8e,4,0);expect_run(ram,s,o,0x4bce0);check(get(ram,A5+0x5c8e,4)==0x10c777U && get(ram,s.a[7],4)==0x4c398,"4c390");
        world(ram,s,0x4c3aa,0);expect_run(ram,s,o,0x4c810);check(get(ram,A5+0x549f,1)==0xff && get(ram,A5+0x5cb4,1)==0,"4c3aa");
        world(ram,s,0x4c3d4,0);expect_run(ram,s,o,0x4c810);check(get(ram,A5+0x5cb4,1)==0xff,"4c3d4");
    }
}
// Checked errors and failure preservation.
void part_errors() {
    unsigned int internal=0;
    for(unsigned int r=0;r<RANGE_COUNT;++r)for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2) {
        if(is_step(pc))continue;
        Bytes ram;State s;world(ram,s,pc,0);reject(ram,s,SENT,"unsupported animation objects b2b PC");++internal;
    }
    check(internal>300,"internal even PCs are checked errors",internal);
    // Review 0264 M-3: the probes without an executor are work-RAM PCs; the ROM neighbours / gaps (4c3ba 4c3c2 3a4d6 3a4d8 4b6f4 3a048 3a0d2 3ad48 4d9a2 338f8 4c340
    // 4eef4 4f0c4 4ffba d3d9c 4d6f2: code or data of later units) are only asserted to be outside the unit's own ranges.
    const std::uint32_t ends[]={0x4c3ba,0x4c3c2,0x3a4d6,0x3a4d8,0x4b6f4,0x3a048,0x3a0d2,0x3ad48,0x4d9a2,0x338f8,0x4c340,0x4eef4,0x4f0c4,0x4ffba,0xd3d9c,0x4d6f2};
    for(unsigned int i=0;i<sizeof(ends)/sizeof(ends[0]);++i)check(!in_ranges(ends[i]),"neighbour outside the unit ranges",ends[i]);
    std::uint32_t unrouted[19];
    for(unsigned int i=0;i<19;++i)unrouted[i]=0x10fe00U+2U*i;
    for(unsigned int i=0;i<sizeof(unrouted)/sizeof(unrouted[0]);++i) {
        Bytes ram;State s;world(ram,s,unrouted[i],0);reject(ram,s,SENT,"unsupported animation machine PC");
    }
    {
        Bytes ram;State s;world(ram,s,0x4d419,0);reject(ram,s,SENT,"unaligned animation machine PC");
        world(ram,s,0x4c390,0);s.a[5]=A5+1U;reject(ram,s,SENT,"invalid animation machine write size/alignment");          // odd LONG store 5c8e(A5)
        world(ram,s,0x4d454,0);s.a[4]=SLOT0+1U;reject(ram,s,SENT,"invalid animation machine write size/alignment");        // odd WORD store 2(A4)
    }
    {   // A failure after earlier stores: 4d454 stores WORD 2(A4), WORD 4(A4), LONG c(A4), then the LONG 10(A4) crosses 1fffff into the banked window (no write device).
        Bytes ram;State s;world(ram,s,0x4d454,0);s.a[4]=0x1fffee;put(ram,NODE+0x3e,4,0x1234);s.d[2]=0x1111;s.d[3]=0x2222;
        Out o;const Bytes saved=ram;const State old=s;
        const bool ok=run(ram,s,SENT,o);
        check(!ok && o.error=="unsupported animation machine write device" && ram==saved && same(s,old),"mid-run failure rolls back every write");
    }
}
}
int main() {
    steps();
    part_4d418();
    part_4d4b4();
    part_table();
    part_carry();
    part_chains();
    part_errors();
    std::cout<<"objects b2b: "<<checks<<" checks, "<<STEP_COUNT<<" block starts stepped in 2 worlds\n";
    return 0;
}
