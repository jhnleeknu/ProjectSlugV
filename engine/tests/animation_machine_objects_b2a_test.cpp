#include "ms5/animation_machine.h"
#include "../src/animation_machine_internal.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
// Objects B2a (180 block starts: the 28ae children 5eed2 (N25, 28), 5f504 (N26, 53) and 60516 (N27, 99); the BLTs/BMIs 5f592 5f678 60680 60690 are folded
// into their predecessors). Part 1 (STEPS, generated from the static decode of the original code bytes with capstone M68000, the same decode as
// tools/unit_fixture_specs/b2a.py): every block start is stepped once through animation_objects_b2a_block in two declared worlds and its successor is
// checked against the static successors of the original block (branch targets, fall-through, call target + pushed return LONG, RTS to the declared
// return LONG). Part 2: declared semantic fixtures through run_animation_machine only (arithmetic and compare edges, the three-way folded branches,
// the ORI Set blocks, the consumers of the known C, the 2986 push / MOVEM.W pop sequence, the child installs), checked errors and failure preservation.
// Inputs are declared fixtures (zero RAM, node A6 = 10e000, parent chain P0 -> P1, A5 = 108000, stack 10ee00 with the return LONG ff000); the only ROM
// bytes are synthetic typed physical bytes (the banked LONGs 200194 / 200090 pointing into work RAM), not ROM data. The native equivalence of the same
// blocks against the original ROM is the job of tools/unit_fixture_specs/b2a.py (V1 verifier).
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef ms5::AnimationMachineState State;
using ms5::AnimationCarryClear;
using ms5::AnimationCarrySet;
using ms5::AnimationCarryUnknown;
const std::uint32_t SENT=0xff000,SP=0x10ee00,NODE=0x10e000,A5=0x108000;
const std::uint32_t P0=0x10c000,P1=0x10c100,P2=0x10c200,P3=0x10c300,BANK_A=0x10c800,BANK_B=0x10c900;
unsigned int checks=0;
void check(bool ok,const char*what,std::uint32_t a=0,std::uint32_t b=0) {
    ++checks;
    if(!ok){std::cerr<<std::hex<<"FAILED "<<what<<" "<<a<<" "<<b<<"\n";std::exit(1);}
}
// ---- generated table (begin): pc, kind (0 flow, 1 call, 2 RTS), pushed return LONG, successor count, successors.
struct Step {std::uint32_t pc;unsigned int kind;std::uint32_t ret;unsigned int n;std::uint32_t succ[3];};
const Step STEPS[]={
 {0x5eed2,1,0x5eee2,1,{0x443d2}},
 {0x5eee2,1,0x5eef8,1,{0x8ebe}},
 {0x5eef8,1,0x5ef06,1,{0x8ebe}},
 {0x5ef06,1,0x5ef14,1,{0x8ebe}},
 {0x5ef14,1,0x5ef3c,1,{0x49f8c}},
 {0x5ef3c,0,0x0,1,{0x5ef42}},
 {0x5ef42,1,0x5ef48,1,{0x43ea4}},
 {0x5ef48,1,0x5ef4e,1,{0x49fc6}},
 {0x5ef4e,1,0x5ef58,1,{0x4ae4a}},
 {0x5ef58,0,0x0,2,{0x5ef60,0x5ef66}},
 {0x5ef60,0,0x0,1,{0x5ef66}},
 {0x5ef66,1,0x5ef6c,1,{0x4b6f4}},
 {0x5ef6c,0,0x0,2,{0x5ef70,0x5ef76}},
 {0x5ef70,0,0x0,1,{0x2a00}},
 {0x5ef76,1,0x5ef80,1,{0x1ab02}},
 {0x5ef80,0,0x0,2,{0x5ef84,0x5ef8a}},
 {0x5ef84,0,0x0,1,{0x2a00}},
 {0x5ef8a,2,0x0,0,{0}},
 {0x5ef8c,1,0x5efb4,1,{0x49f8c}},
 {0x5efb4,0,0x0,1,{0x5efba}},
 {0x5efba,1,0x5efc0,1,{0x43ea4}},
 {0x5efc0,1,0x5efc6,1,{0x49fc6}},
 {0x5efc6,0,0x0,2,{0x5efca,0x5efd0}},
 {0x5efca,0,0x0,1,{0x2a00}},
 {0x5efd0,1,0x5efda,1,{0x1ab02}},
 {0x5efda,0,0x0,2,{0x5efde,0x5efe4}},
 {0x5efde,0,0x0,1,{0x2a00}},
 {0x5efe4,2,0x0,0,{0}},
 {0x5f504,1,0x5f50a,1,{0x49a58}},
 {0x5f50a,1,0x5f520,1,{0x4b702}},
 {0x5f520,1,0x5f54e,1,{0x8ebe}},
 {0x5f54e,1,0x5f576,1,{0x49f8c}},
 {0x5f576,0,0x0,1,{0x5f57c}},
 {0x5f57c,0,0x0,2,{0x5f584,0x5f5a2}},
 {0x5f584,0,0x0,3,{0x5f596,0x5f59e,0x5f5a2}},
 {0x5f596,0,0x0,1,{0x5f5a2}},
 {0x5f59e,0,0x0,1,{0x5f5a2}},
 {0x5f5a2,1,0x5f5ba,1,{0x443d2}},
 {0x5f5ba,1,0x5f5c8,1,{0x43ea4}},
 {0x5f5c8,1,0x5f5ce,1,{0x49fc6}},
 {0x5f5ce,0,0x0,2,{0x5f5da,0x5f5e0}},
 {0x5f5da,0,0x0,1,{0x5f5e0}},
 {0x5f5e0,1,0x5f5e6,1,{0x4b6f4}},
 {0x5f5e6,0,0x0,2,{0x5f5ea,0x5f5f0}},
 {0x5f5ea,0,0x0,1,{0x2a00}},
 {0x5f5f0,2,0x0,0,{0}},
 {0x5f5f2,1,0x5f602,1,{0x49a58}},
 {0x5f602,1,0x5f62e,1,{0x8ff4}},
 {0x5f62e,1,0x5f63c,1,{0x8ebe}},
 {0x5f63c,1,0x5f664,1,{0x49f8c}},
 {0x5f664,0,0x0,1,{0x5f66a}},
 {0x5f66a,0,0x0,3,{0x5f67c,0x5f684,0x5f688}},
 {0x5f67c,0,0x0,1,{0x5f688}},
 {0x5f684,0,0x0,1,{0x5f688}},
 {0x5f688,0,0x0,2,{0x5f694,0x5f69a}},
 {0x5f694,0,0x0,1,{0x5f69a}},
 {0x5f69a,1,0x5f6a8,1,{0x443d2}},
 {0x5f6a8,1,0x5f6b6,1,{0x43ea4}},
 {0x5f6b6,1,0x5f6bc,1,{0x49fc6}},
 {0x5f6bc,1,0x5f6c2,1,{0x4b54e}},
 {0x5f6c2,0,0x0,2,{0x5f6c6,0x5f6ca}},
 {0x5f6c6,0,0x0,1,{0x5f6ca}},
 {0x5f6ca,0,0x0,2,{0x5f6d4,0x5f6da}},
 {0x5f6d4,0,0x0,1,{0x5f6da}},
 {0x5f6da,0,0x0,2,{0x5f6e2,0x5f6ea}},
 {0x5f6e2,1,0x5f6ea,1,{0x4ae4a}},
 {0x5f6ea,0,0x0,2,{0x5f6f2,0x5f71e}},
 {0x5f6f2,1,0x5f702,1,{0x28ae}},
 {0x5f702,0,0x0,2,{0x5f706,0x5f718}},
 {0x5f706,1,0x5f714,1,{0x4970a}},
 {0x5f714,0,0x0,1,{0x5f718}},
 {0x5f718,0,0x0,1,{0x2a00}},
 {0x5f71e,0,0x0,2,{0x5f728,0x5f73e}},
 {0x5f728,0,0x0,2,{0x5f738,0x5f73e}},
 {0x5f738,0,0x0,1,{0x2a00}},
 {0x5f73e,1,0x5f744,1,{0x4b6f4}},
 {0x5f744,0,0x0,2,{0x5f748,0x5f74e}},
 {0x5f748,0,0x0,1,{0x2a00}},
 {0x5f74e,0,0x0,2,{0x5f758,0x5f75e}},
 {0x5f758,0,0x0,1,{0x2a00}},
 {0x5f75e,2,0x0,0,{0}},
 {0x60516,1,0x6051c,1,{0x49a58}},
 {0x6051c,1,0x6053c,1,{0x490ba}},
 {0x6053c,1,0x60546,1,{0x4b702}},
 {0x60546,0,0x0,2,{0x60554,0x6056c}},
 {0x60554,1,0x60568,1,{0x8ebe}},
 {0x60568,0,0x0,1,{0x6057a}},
 {0x6056c,1,0x6057a,1,{0x8ebe}},
 {0x6057a,1,0x605a2,1,{0x49f8c}},
 {0x605a2,0,0x0,1,{0x605ae}},
 {0x605ae,0,0x0,2,{0x605be,0x605f8}},
 {0x605be,0,0x0,2,{0x605c6,0x605f4}},
 {0x605c6,0,0x0,2,{0x605d4,0x605dc}},
 {0x605d4,0,0x0,1,{0x605e0}},
 {0x605dc,0,0x0,1,{0x605e0}},
 {0x605e0,0,0x0,2,{0x605ee,0x605f4}},
 {0x605ee,0,0x0,1,{0x605f4}},
 {0x605f4,0,0x0,1,{0x607b4}},
 {0x605f8,0,0x0,2,{0x60600,0x606be}},
 {0x60600,0,0x0,2,{0x6060a,0x60616}},
 {0x6060a,0,0x0,1,{0x60616}},
 {0x60616,0,0x0,2,{0x6061e,0x6064a}},
 {0x6061e,1,0x6062e,1,{0x28ae}},
 {0x6062e,0,0x0,2,{0x60632,0x60644}},
 {0x60632,1,0x60640,1,{0x4970a}},
 {0x60640,0,0x0,1,{0x60644}},
 {0x60644,0,0x0,1,{0x2a00}},
 {0x6064a,1,0x60670,1,{0x44602}},
 {0x60670,0,0x0,3,{0x60684,0x6068c,0x6069c}},
 {0x60684,0,0x0,2,{0x60694,0x6069a}},
 {0x6068c,0,0x0,2,{0x60694,0x6069a}},
 {0x60694,0,0x0,1,{0x6069c}},
 {0x6069a,0,0x0,1,{0x6069c}},
 {0x6069c,0,0x0,2,{0x606b2,0x606ba}},
 {0x606b2,0,0x0,1,{0x606ba}},
 {0x606ba,0,0x0,1,{0x607b4}},
 {0x606be,0,0x0,2,{0x606c6,0x6074e}},
 {0x606c6,0,0x0,2,{0x606d0,0x606dc}},
 {0x606d0,0,0x0,1,{0x606dc}},
 {0x606dc,0,0x0,2,{0x606e4,0x60710}},
 {0x606e4,1,0x606f4,1,{0x28ae}},
 {0x606f4,0,0x0,2,{0x606f8,0x6070a}},
 {0x606f8,1,0x60706,1,{0x4970a}},
 {0x60706,0,0x0,1,{0x6070a}},
 {0x6070a,0,0x0,1,{0x2a00}},
 {0x60710,0,0x0,2,{0x60718,0x60728}},
 {0x60718,0,0x0,2,{0x60720,0x60724}},
 {0x60720,0,0x0,1,{0x60724}},
 {0x60724,0,0x0,1,{0x60734}},
 {0x60728,0,0x0,2,{0x60730,0x60734}},
 {0x60730,0,0x0,1,{0x60734}},
 {0x60734,0,0x0,2,{0x60742,0x6074a}},
 {0x60742,0,0x0,1,{0x6074a}},
 {0x6074a,0,0x0,1,{0x607b4}},
 {0x6074e,0,0x0,2,{0x60756,0x607b4}},
 {0x60756,0,0x0,2,{0x60760,0x60766}},
 {0x60760,0,0x0,1,{0x60766}},
 {0x60766,0,0x0,2,{0x6076e,0x6079a}},
 {0x6076e,1,0x6077e,1,{0x28ae}},
 {0x6077e,0,0x0,2,{0x60782,0x60794}},
 {0x60782,1,0x60790,1,{0x4970a}},
 {0x60790,0,0x0,1,{0x60794}},
 {0x60794,0,0x0,1,{0x2a00}},
 {0x6079a,0,0x0,2,{0x607a8,0x607b0}},
 {0x607a8,0,0x0,1,{0x607b0}},
 {0x607b0,0,0x0,1,{0x607b4}},
 {0x607b4,1,0x607c2,1,{0x443d2}},
 {0x607c2,1,0x607d0,1,{0x43ea4}},
 {0x607d0,1,0x607d6,1,{0x49fc6}},
 {0x607d6,0,0x0,2,{0x607de,0x607e6}},
 {0x607de,1,0x607e6,1,{0x4ae4a}},
 {0x607e6,0,0x0,2,{0x607ee,0x6087a}},
 {0x607ee,0,0x0,2,{0x607f6,0x6084e}},
 {0x607f6,1,0x60828,1,{0x2986}},
 {0x60828,0,0x0,2,{0x60830,0x6084e}},
 {0x60830,1,0x6084a,1,{0x49214}},
 {0x6084a,0,0x0,1,{0x6084e}},
 {0x6084e,1,0x6085e,1,{0x28ae}},
 {0x6085e,0,0x0,2,{0x60862,0x60874}},
 {0x60862,1,0x60870,1,{0x4970a}},
 {0x60870,0,0x0,1,{0x60874}},
 {0x60874,0,0x0,1,{0x2a00}},
 {0x6087a,1,0x60880,1,{0x4b54e}},
 {0x60880,0,0x0,2,{0x60884,0x60888}},
 {0x60884,0,0x0,1,{0x60888}},
 {0x60888,0,0x0,2,{0x60892,0x6091e}},
 {0x60892,0,0x0,2,{0x6089a,0x608f2}},
 {0x6089a,1,0x608cc,1,{0x2986}},
 {0x608cc,0,0x0,2,{0x608d4,0x608f2}},
 {0x608d4,1,0x608ee,1,{0x49214}},
 {0x608ee,0,0x0,1,{0x608f2}},
 {0x608f2,1,0x60902,1,{0x28ae}},
 {0x60902,0,0x0,2,{0x60906,0x60918}},
 {0x60906,1,0x60914,1,{0x4970a}},
 {0x60914,0,0x0,1,{0x60918}},
 {0x60918,0,0x0,1,{0x2a00}},
 {0x6091e,0,0x0,2,{0x60926,0x60938}},
 {0x60926,0,0x0,2,{0x60932,0x60938}},
 {0x60932,0,0x0,1,{0x2a00}},
 {0x60938,2,0x0,0,{0}},
};
// ---- generated table (end)
const unsigned int STEP_COUNT=sizeof(STEPS)/sizeof(STEPS[0]);
const std::uint32_t RANGES[][2]={{0x5eed2,0x5efe6},{0x5f504,0x5f760},{0x60516,0x6093a}};
const unsigned int RANGE_COUNT=sizeof(RANGES)/sizeof(RANGES[0]);
// Consumers of a C returned by a callee: pc, target when C is clear, target when C is set (the Unknown C is a checked error).
const std::uint32_t CONSUMERS[][3]={{0x5ef6c,0x5ef76,0x5ef70},{0x5ef80,0x5ef8a,0x5ef84},{0x5efc6,0x5efd0,0x5efca},{0x5efda,0x5efe4,0x5efde},
 {0x5f5e6,0x5f5f0,0x5f5ea},{0x5f6c2,0x5f6ca,0x5f6c6},{0x5f702,0x5f718,0x5f706},{0x5f744,0x5f74e,0x5f748},{0x6062e,0x60644,0x60632},
 {0x606f4,0x6070a,0x606f8},{0x6077e,0x60794,0x60782},{0x6085e,0x60874,0x60862},{0x60880,0x60888,0x60884},{0x60902,0x60918,0x60906}};
const unsigned int CONSUMER_COUNT=sizeof(CONSUMERS)/sizeof(CONSUMERS[0]);
// MOVEM.W consumers (the 7 popped WORDs come first): pc, clear target, set target.
const std::uint32_t MOVEM_CONSUMERS[][3]={{0x60828,0x6084e,0x60830},{0x608cc,0x608f2,0x608d4}};
// Synthetic typed physical bytes: the banked LONGs 200194 / 200090 (work RAM pointers).
Physical make_rom() {
    Physical p(2);
    p[0].source_rom_offset=0x200194;p[0].data.push_back(0x00);p[0].data.push_back(0x10);p[0].data.push_back(0xc8);p[0].data.push_back(0x00);
    p[1].source_rom_offset=0x200090;p[1].data.push_back(0x00);p[1].data.push_back(0x10);p[1].data.push_back(0xc9);p[1].data.push_back(0x00);
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
bool in_ranges(std::uint32_t pc) {for(unsigned int i=0;i<RANGE_COUNT;++i)if(pc>=RANGES[i][0]&&pc<RANGES[i][1])return true;return false;}
bool is_step(std::uint32_t pc) {for(unsigned int i=0;i<STEP_COUNT;++i)if(STEPS[i].pc==pc)return true;return false;}
bool is_consumer(std::uint32_t pc) {
    for(unsigned int i=0;i<CONSUMER_COUNT;++i)if(CONSUMERS[i][0]==pc)return true;
    for(unsigned int i=0;i<2;++i)if(MOVEM_CONSUMERS[i][0]==pc)return true;
    return false;
}
// Declared world. variant 0: zero RAM; variant 1: node bytes 00..c3 = 01 (flags set, WORD 0101). The parent chain A6 -> P0 -> P1 is valid work RAM in both.
void world(Bytes&ram,State&s,std::uint32_t pc,unsigned int variant) {
    ram.assign(65536,0);State fresh;s=fresh;
    if(variant==1)for(unsigned int i=0;i<0xc4;++i)ram[(NODE+i)&65535U]=1;
    put(ram,NODE+0xc,4,P0);put(ram,P0+0xc,4,P1);
    for(unsigned int i=0;i<8;++i)s.d[i]=0x11110000U*(i+1U)+i;
    s.a[0]=P0;s.a[1]=P1;s.a[2]=P2;s.a[3]=P3;s.a[4]=P0;s.a[5]=A5;s.a[6]=NODE;s.a[7]=SP;s.pc=pc;s.carry=AnimationCarryUnknown;
    put(ram,SP,4,SENT);
}
bool step(Bytes&ram,State&s,Out&o,std::string&error) {
    std::vector<ms5::FixedDataResource> w;const ms5::ProgramBusState bus=bus_of();
    ms5::AnimationMachineContext c(ram,w,bus,s,o.dev,o.ports,0,error);
    return ms5::animation_objects_b2a_block(c);
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
    check(STEP_COUNT==180,"180 block starts",STEP_COUNT);
    for(unsigned int i=0;i<STEP_COUNT;++i) {
        const Step&t=STEPS[i];
        check(in_ranges(t.pc),"block start inside the routed ranges",t.pc);
        for(unsigned int variant=0;variant<2;++variant) {
            if(is_consumer(t.pc))continue;                                       // consumers need a known C: Part 2
            Bytes ram;State s;Out o;std::string error;world(ram,s,t.pc,variant);
            const bool ok=step(ram,s,o,error);
            if(!ok)std::cerr<<std::hex<<"step "<<t.pc<<" variant "<<variant<<": "<<error<<"\n";
            check(ok,"block step succeeds",t.pc,variant);
            if(t.kind==2) {
                check(s.pc==SENT,"RTS pops the declared return LONG",t.pc,s.pc);
            } else {
                bool found=false;for(unsigned int k=0;k<t.n;++k)if(t.succ[k]==s.pc)found=true;
                if(!found)std::cerr<<std::hex<<"step "<<t.pc<<" variant "<<variant<<" went to "<<s.pc<<"\n";
                check(found,"successor is a static successor of the original block",t.pc,s.pc);
                if(t.kind==1)check(get(ram,s.a[7],4)==t.ret,"JSR pushes the return LONG",t.pc,get(ram,s.a[7],4));
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
// One block from pc to its successor (the block alone): returns the PC reached.
std::uint32_t one(Bytes&ram,State&s,std::uint32_t pc) {
    Out o;std::string error;s.pc=pc;
    const bool ok=step(ram,s,o,error);
    if(!ok)std::cerr<<std::hex<<"one "<<pc<<": "<<error<<"\n";
    check(ok,"one block",pc);return s.pc;
}
// ---- Part 2a: 5eed2 (N25 child).
void part_5eed2() {
    Bytes ram;State s;Out o;
    world(ram,s,0x5eed2,0);put(ram,NODE+0x8a,2,0x4321);expect_run(ram,s,o,0x443d2);
    check(s.d[0]==0x40000 && (s.d[1]&65535U)==0x4321U && (s.d[1]>>16)==0x2222U && s.carry==AnimationCarryClear && get(ram,s.a[7],4)==0x5eee2,"5eed2 D0 D1 C");
    world(ram,s,0x5eee2,0);s.d[0]=0x11223344;s.d[1]=0x55667788;expect_run(ram,s,o,0x8ebe);
    check(get(ram,NODE+0x36,4)==0x11223344U && get(ram,NODE+0x3a,4)==0x55667788U && (s.d[0]&65535U)==0xd5f && (s.d[1]&255U)==0 && (s.d[1]>>8)==0x556677U,"5eee2 position stores, sound d5f");
    world(ram,s,0x5eef8,0);expect_run(ram,s,o,0x8ebe);check((s.d[0]&65535U)==0xd60,"5eef8 sound d60");
    world(ram,s,0x5ef06,0);expect_run(ram,s,o,0x8ebe);check((s.d[0]&65535U)==0xd61,"5ef06 sound d61");
    for(unsigned int k=0;k<2;++k) {   // 5ef14 (disp 20c) and 5ef8c (disp 210): banked LONG 200194 -> record base, then the record LONG at the displacement
        world(ram,s,k==0?0x5ef14U:0x5ef8cU,0);put(ram,BANK_A+(k==0?0x20cU:0x210U),4,0x10d000);expect_run(ram,s,o,0x49f8c);
        check(get(ram,NODE+0x20,2)==0x18b && get(ram,NODE+0x22,4)==BANK_A && s.a[0]==NODE+0x26 && s.a[1]==0x10d000U && (s.d[0]&65535U)==0x100 &&
            s.carry==AnimationCarryClear && get(ram,s.a[7],4)==(k==0?0x5ef3cU:0x5efb4U),"5ef14 / 5ef8c animation setup");
    }
    world(ram,s,0x5ef3c,0);expect_run(ram,s,o,0x43ea4);check(get(ram,NODE,4)==0x5ef42,"5ef3c installs 5ef42");
    world(ram,s,0x5efb4,0);expect_run(ram,s,o,0x43ea4);check(get(ram,NODE,4)==0x5efba,"5efb4 installs 5efba");
    world(ram,s,0x5ef4e,0);expect_run(ram,s,o,0x4ae4a);check(s.a[0]==0x5eeac,"5ef4e hit box 5eeac");
    world(ram,s,0x5ef76,0);expect_run(ram,s,o,0x1ab02);check(s.a[0]==0x5eeca && get(ram,s.a[7],4)==0x5ef80,"5ef76 hit box 5eeca");
    world(ram,s,0x5efd0,0);expect_run(ram,s,o,0x1ab02);check(s.a[0]==0x5eeca && get(ram,s.a[7],4)==0x5efda,"5efd0 hit box 5eeca");
    // 5ef58: CMPI.W #0,D0; BEQ.W 5ef66 (only the low WORD counts); 5ef60 installs 5ef8c.
    world(ram,s,0x5ef58,0);s.d[0]=0xabcd0000U;check(one(ram,s,0x5ef58)==0x5ef66 && s.carry==AnimationCarryClear,"5ef58 WORD 0 -> 5ef66");
    world(ram,s,0x5ef58,0);s.d[0]=0x0000abcdU;check(one(ram,s,0x5ef58)==0x5ef60 && s.carry==AnimationCarryClear,"5ef58 WORD != 0 -> 5ef60");
    world(ram,s,0x5ef60,0);expect_run(ram,s,o,0x4b6f4);check(get(ram,NODE,4)==0x5ef8c,"5ef60 installs 5ef8c, boundary 4b6f4");
    // 5ef6c .. 5efde end to end: C Set after 4b6f4 -> delete (2a00), C Clear -> 1ab02 -> RTS.
    world(ram,s,0x5ef6c,0);s.carry=AnimationCarrySet;expect_run(ram,s,o,0x2a00);
    world(ram,s,0x5ef6c,0);s.carry=AnimationCarryClear;expect_run(ram,s,o,0x1ab02);
    world(ram,s,0x5ef80,0);s.carry=AnimationCarryClear;expect_run(ram,s,o,SENT);check(s.carry==AnimationCarryClear,"5ef80 Clear -> RTS keeps Clear");
}
// ---- Part 2b: 5f504 (N26 child).
void part_5f504() {
    Bytes ram;State s;Out o;
    world(ram,s,0x5f504,0);expect_run(ram,s,o,0x49a58);
    // 5f50a: ((D0.W & 1f) - f) & ff -> BYTE 94(A6); the upper WORD of D0 is kept.
    world(ram,s,0x5f50a,0);s.d[0]=0x12345678U;expect_run(ram,s,o,0x4b702);
    check(s.d[0]==0x12340009U && get(ram,NODE+0x94,1)==9 && s.carry==AnimationCarryClear,"5f50a 5678 -> 9");
    world(ram,s,0x5f50a,0);s.d[0]=0xabcd0003U;expect_run(ram,s,o,0x4b702);
    check(s.d[0]==0xabcd00f4U && get(ram,NODE+0x94,1)==0xf4,"5f50a 3 - f wraps to f4");
    world(ram,s,0x5f520,0);expect_run(ram,s,o,0x8ebe);
    check(get(ram,NODE+0x96,4)==0x90000U && get(ram,NODE+0x7e,2)==8 && get(ram,NODE+0x15,1)==8 && get(ram,NODE+0x68,2)==0x1110 && get(ram,NODE+0x1e,2)==0x1110 &&
        (s.d[0]&65535U)==0xcfb && (s.d[1]&255U)==0,"5f520");
    world(ram,s,0x5f54e,0);put(ram,BANK_B+0x24,4,0x10d200);expect_run(ram,s,o,0x49f8c);
    check(get(ram,NODE+0x20,2)==0xda && get(ram,NODE+0x22,4)==BANK_B && s.a[1]==0x10d200U,"5f54e bank 200090 id da");
    world(ram,s,0x5f63c,0);put(ram,BANK_B+0x28,4,0x10d300);expect_run(ram,s,o,0x49f8c);
    check(get(ram,NODE+0x22,4)==BANK_B && s.a[1]==0x10d300U,"5f63c bank 200090 disp 28");
    world(ram,s,0x5f576,0);check(one(ram,s,0x5f576)==0x5f57c && get(ram,NODE,4)==0x5f57c,"5f576 installs 5f57c");
    world(ram,s,0x5f664,0);check(one(ram,s,0x5f664)==0x5f66a && get(ram,NODE,4)==0x5f66a,"5f664 installs 5f66a");
    // 5f57c: SUBQ.W #1,7e(A6); BCC (borrow only when the WORD was 0).
    world(ram,s,0x5f57c,0);put(ram,NODE+0x7e,2,0);check(one(ram,s,0x5f57c)==0x5f584 && get(ram,NODE+0x7e,2)==0xffff && s.carry==AnimationCarrySet,"5f57c borrow");
    world(ram,s,0x5f57c,0);put(ram,NODE+0x7e,2,1);check(one(ram,s,0x5f57c)==0x5f5a2 && get(ram,NODE+0x7e,2)==0 && s.carry==AnimationCarryClear,"5f57c no borrow");
    // 5f584 / 5f66a: Z, N of the same TST.B 94(A6) (the BMI is folded): zero / negative / positive.
    const std::uint32_t three[2][4]={{0x5f584,0x5f5a2,0x5f59e,0x5f596},{0x5f66a,0x5f688,0x5f684,0x5f67c}};
    for(unsigned int k=0;k<2;++k) {
        const unsigned int vals[3]={0,0x80,0x7f};
        for(unsigned int v=0;v<3;++v) {
            world(ram,s,three[k][0],0);put(ram,NODE+0x94,1,vals[v]);put(ram,NODE+0x7e,2,0x77);
            check(one(ram,s,three[k][0])==three[k][1+v] && get(ram,NODE+0x7e,2)==(k==0?8U:2U) && s.carry==AnimationCarryClear,"three-way TST.B 94",three[k][0],vals[v]);
        }
    }
    world(ram,s,0x5f596,0);put(ram,NODE+0x94,1,3);check(one(ram,s,0x5f596)==0x5f5a2 && get(ram,NODE+0x94,1)==2 && s.carry==AnimationCarryClear,"5f596 SUBQ.B");
    world(ram,s,0x5f59e,0);put(ram,NODE+0x94,1,0xff);check(one(ram,s,0x5f59e)==0x5f5a2 && get(ram,NODE+0x94,1)==0 && s.carry==AnimationCarrySet,"5f59e ADDQ.B carry out");
    world(ram,s,0x5f67c,0);put(ram,NODE+0x94,1,1);check(one(ram,s,0x5f67c)==0x5f688 && get(ram,NODE+0x94,1)==0,"5f67c");
    world(ram,s,0x5f684,0);put(ram,NODE+0x94,1,0x90);check(one(ram,s,0x5f684)==0x5f688 && get(ram,NODE+0x94,1)==0x91 && s.carry==AnimationCarryClear,"5f684");
    // 5f5a2: D0 = [96] - ([96] >> 5 arithmetic); then D0 = [96], D1.B = 94(A6), JSR 443d2.
    world(ram,s,0x5f5a2,0);put(ram,NODE+0x96,4,0x40000);put(ram,NODE+0x94,1,0x12);s.d[1]=0xaabbccddU;expect_run(ram,s,o,0x443d2);
    check(get(ram,NODE+0x96,4)==0x3e000U && s.d[0]==0x3e000U && s.d[1]==0xaabbcc12U && s.carry==AnimationCarryClear,"5f5a2 positive speed");
    world(ram,s,0x5f5a2,0);put(ram,NODE+0x96,4,0xfffc0000U);expect_run(ram,s,o,0x443d2);
    check(get(ram,NODE+0x96,4)==0xfffc2000U && s.d[0]==0xfffc2000U,"5f5a2 negative speed (ASR keeps the sign)");
    world(ram,s,0x5f5ba,0);s.d[0]=0x01020304;s.d[1]=0x05060708;expect_run(ram,s,o,0x43ea4);
    check(get(ram,NODE+0x36,4)==0x01020304U && get(ram,NODE+0x3a,4)==0x05060708U,"5f5ba");
    // 5f5ce: CMPI.L #10000,36(A6); BGE (signed).
    const std::uint32_t lv[4]={0x10000,0xffff,0x80000000U,0x7fffffffU};const std::uint32_t lt[4]={0x5f5e0,0x5f5da,0x5f5da,0x5f5e0};
    for(unsigned int i=0;i<4;++i){world(ram,s,0x5f5ce,0);put(ram,NODE+0x36,4,lv[i]);check(one(ram,s,0x5f5ce)==lt[i],"5f5ce signed LONG compare",lv[i]);}
    world(ram,s,0x5f5ce,0);put(ram,NODE+0x36,4,0xffff);one(ram,s,0x5f5ce);check(s.carry==AnimationCarrySet,"5f5ce borrow Set");
    world(ram,s,0x5f5da,0);expect_run(ram,s,o,0x4b6f4);check(get(ram,NODE,4)==0x5f5f2,"5f5da installs 5f5f2, falls into 5f5e0");
    world(ram,s,0x5f5f2,0);s.d[0]=0x99;expect_run(ram,s,o,0x49a58);check(get(ram,NODE+0x56,4)==0x5f4e6 && s.d[0]==0,"5f5f2 pointer 5f4e6, MOVEQ #0,D0");
    // 5f602: D0 = -((D0.W & 1fff) << 4 | upper) + 40000 chain.
    world(ram,s,0x5f602,0);s.d[0]=0xabcd1234U;expect_run(ram,s,o,0x8ff4);
    check(s.d[0]==0x432adcc0U && get(ram,NODE+0x9a,4)==0x432adcc0U && get(ram,NODE+0x96,4)==0xffffc000U && get(ram,NODE+0x68,2)==0xe0ef && get(ram,NODE+0x1e,2)==0xe0ef,"5f602");
    // 5f688: CMP.L 9a(A6),D0 with D0 = [96]; BLE (signed): below / equal / above / sign mix.
    const std::uint32_t pairs[5][3]={{1,2,0x5f69a},{5,5,0x5f69a},{6,5,0x5f694},{0xfffffff0U,0x10,0x5f69a},{0x10,0xfffffff0U,0x5f694}};
    for(unsigned int i=0;i<5;++i){world(ram,s,0x5f688,0);put(ram,NODE+0x96,4,pairs[i][0]);put(ram,NODE+0x9a,4,pairs[i][1]);check(one(ram,s,0x5f688)==pairs[i][2] && s.d[0]==pairs[i][0],"5f688 BLE",i);}
    world(ram,s,0x5f694,0);s.d[0]=0xfffffff0U;put(ram,NODE+0x96,4,0x100);check(one(ram,s,0x5f694)==0x5f69a && get(ram,NODE+0x96,4)==0xffU && s.carry==AnimationCarrySet,"5f694 ASR.L #4 then ADD.L");
    world(ram,s,0x5f69a,0);put(ram,NODE+0x96,4,0x1234);put(ram,NODE+0x94,1,0x56);expect_run(ram,s,o,0x443d2);check(s.d[0]==0x1234 && (s.d[1]&255U)==0x56,"5f69a");
    world(ram,s,0x5f6a8,0);s.d[0]=1;s.d[1]=2;expect_run(ram,s,o,0x43ea4);check(get(ram,NODE+0x36,4)==1 && get(ram,NODE+0x3a,4)==2,"5f6a8");
    world(ram,s,0x5f6bc,0);expect_run(ram,s,o,0x4b54e);check(get(ram,s.a[7],4)==0x5f6c2,"5f6bc");
    // 5f6c6: CLR.B 5e(A6); 5f6ca: BTST.B #7,61(A6) keeps C; 5f6d4: MOVE.W #1,54(A6).
    world(ram,s,0x5f6c6,0);put(ram,NODE+0x5e,1,9);check(one(ram,s,0x5f6c6)==0x5f6ca && get(ram,NODE+0x5e,1)==0 && s.carry==AnimationCarryClear,"5f6c6");
    world(ram,s,0x5f6ca,0);s.carry=AnimationCarrySet;put(ram,NODE+0x61,1,0x80);check(one(ram,s,0x5f6ca)==0x5f6d4 && s.carry==AnimationCarrySet,"5f6ca bit set keeps C");
    world(ram,s,0x5f6ca,0);put(ram,NODE+0x61,1,0x7f);check(one(ram,s,0x5f6ca)==0x5f6da,"5f6ca bit clear");
    world(ram,s,0x5f6d4,0);check(one(ram,s,0x5f6d4)==0x5f6da && get(ram,NODE+0x54,2)==1,"5f6d4");
    world(ram,s,0x5f6da,0);put(ram,NODE+0x72,4,0);check(one(ram,s,0x5f6da)==0x5f6ea && s.d[0]==0,"5f6da zero target");
    world(ram,s,0x5f6da,0);put(ram,NODE+0x72,4,0x10c555);check(one(ram,s,0x5f6da)==0x5f6e2 && s.d[0]==0x10c555U,"5f6da target");
    world(ram,s,0x5f6e2,0);s.d[0]=0x10c555;expect_run(ram,s,o,0x4ae4a);check(s.a[0]==0x10c555U && get(ram,s.a[7],4)==0x5f6ea,"5f6e2 MOVEA.L D0,A0");
    world(ram,s,0x5f6ea,0);s.d[0]=0x10000;check(one(ram,s,0x5f6ea)==0x5f71e,"5f6ea WORD 0");
    world(ram,s,0x5f6ea,0);s.d[0]=1;check(one(ram,s,0x5f6ea)==0x5f6f2,"5f6ea WORD != 0");
    world(ram,s,0x5f6f2,0);expect_run(ram,s,o,0x28ae);check(s.a[0]==0xd22e6 && (s.d[0]&65535U)==0xa && s.carry==AnimationCarryClear,"5f6f2 child d22e6 (data)");
    world(ram,s,0x5f706,0);s.d[0]=0x12345678;s.d[1]=0x9abcdef0U;expect_run(ram,s,o,0x4970a);check(s.d[0]==0x12340000U && s.d[1]==0x9abc0000U,"5f706 MOVE.W #0,D0 D1");
    world(ram,s,0x5f714,0);s.carry=AnimationCarryClear;check(one(ram,s,0x5f714)==0x5f718 && s.carry==AnimationCarrySet,"5f714 ORI.B #1,CCR");
    // 5f71e: CMPI.W #140,42(A6); BGT (signed WORD). 5f728: SUBI.W #100 / CMPI.W #100 / BCS. 5f74e: CMPI.W #ffe0 / BGE.
    const std::uint32_t w1[5]={0x140,0x141,0x8000,0x7fff,0};const std::uint32_t t1[5]={0x5f728,0x5f73e,0x5f728,0x5f73e,0x5f728};
    for(unsigned int i=0;i<5;++i){world(ram,s,0x5f71e,0);put(ram,NODE+0x42,2,w1[i]);check(one(ram,s,0x5f71e)==t1[i],"5f71e BGT",w1[i]);}
    const std::uint32_t w2[4]={0x1ff,0x200,0x50,0x100};const std::uint32_t t2[4]={0x5f73e,0x5f738,0x5f738,0x5f73e};
    for(unsigned int i=0;i<4;++i){
        world(ram,s,0x5f728,0);put(ram,NODE+0x46,2,w2[i]);s.d[0]=0xabcd0000U;
        check(one(ram,s,0x5f728)==t2[i] && s.d[0]==0xabcd0000U+((w2[i]-0x100U)&65535U) && s.carry==(t2[i]==0x5f73e?AnimationCarrySet:AnimationCarryClear),"5f728 SUBI / CMPI / BCS",w2[i]);
    }
    const std::uint32_t w3[4]={0xffe0,0xffdf,0x10,0x8000};const std::uint32_t t3[4]={0x5f75e,0x5f758,0x5f75e,0x5f758};
    for(unsigned int i=0;i<4;++i){world(ram,s,0x5f74e,0);put(ram,NODE+0x42,2,w3[i]);check(one(ram,s,0x5f74e)==t3[i],"5f74e BGE",w3[i]);}
}
// ---- Part 2c: 60516 (N27 child).
void part_60516() {
    Bytes ram;State s;Out o;
    world(ram,s,0x60516,0);expect_run(ram,s,o,0x49a58);
    world(ram,s,0x6051c,0);s.d[0]=0xaaaa00ffU;expect_run(ram,s,o,0x490ba);
    check(s.d[0]==0xaaaa009fU && get(ram,NODE+0x8e,1)==0x9f && get(ram,NODE+0x90,4)==0x30000 && s.a[0]==0x60c54U && s.carry==AnimationCarryClear,"6051c");
    world(ram,s,0x6053c,0);s.d[0]=0x13572468U;expect_run(ram,s,o,0x4b702);check(get(ram,NODE+0x54,2)==0x2468,"6053c");
    world(ram,s,0x60546,0);put(ram,NODE+0x15,1,0xff);put(ram,NODE+0x8f,1,0);check(one(ram,s,0x60546)==0x6056c && get(ram,NODE+0x15,1)==0xfe,"60546 BCLR, BYTE 8f = 0");
    world(ram,s,0x60546,0);put(ram,NODE+0x8f,1,1);check(one(ram,s,0x60546)==0x60554,"60546 BYTE 8f != 0");
    world(ram,s,0x60554,0);expect_run(ram,s,o,0x8ebe);check(get(ram,NODE+0x54,2)==1 && (s.d[0]&65535U)==0xd64,"60554");
    world(ram,s,0x60568,0);check(one(ram,s,0x60568)==0x6057a,"60568 BRA");
    world(ram,s,0x6056c,0);expect_run(ram,s,o,0x8ebe);check((s.d[0]&65535U)==0xd59,"6056c");
    world(ram,s,0x6057a,0);put(ram,BANK_A+0x12c,4,0x10d400);expect_run(ram,s,o,0x49f8c);check(get(ram,NODE+0x22,4)==BANK_A && s.a[1]==0x10d400U,"6057a bank 200194 disp 12c");
    world(ram,s,0x605a2,0);put(ram,NODE+0x7e,2,0x1234);check(one(ram,s,0x605a2)==0x605ae && get(ram,NODE+0x7e,2)==4 && get(ram,NODE,4)==0x605ae && s.carry==AnimationCarryClear,"605a2");
    // 605ae: D0.B = BYTE 77 of the parent; CMPI.B #1: equal -> 605be, else 605f8; the parent is c(A6) (valid work RAM).
    world(ram,s,0x605ae,0);put(ram,P0+0x77,1,1);check(one(ram,s,0x605ae)==0x605be && s.a[0]==P0 && (s.d[0]&255U)==1 && s.carry==AnimationCarryClear,"605ae BYTE 77 = 1");
    world(ram,s,0x605ae,0);put(ram,P0+0x77,1,0);check(one(ram,s,0x605ae)==0x605f8 && s.carry==AnimationCarrySet,"605ae BYTE 77 = 0: borrow, 605f8");
    world(ram,s,0x605ae,0);put(ram,P0+0x77,1,2);check(one(ram,s,0x605ae)==0x605f8 && s.carry==AnimationCarryClear,"605ae BYTE 77 = 2");
    // 605f8 / 606be / 6074e: CMPI.B #2 / #3 / #5,D0; the two-way branches.
    const std::uint32_t sw[3][4]={{0x605f8,2,0x60600,0x606be},{0x606be,3,0x606c6,0x6074e},{0x6074e,5,0x60756,0x607b4}};
    for(unsigned int i=0;i<3;++i)for(unsigned int hit=0;hit<2;++hit) {
        world(ram,s,sw[i][0],0);s.d[0]=0x12340000U|(hit!=0U?sw[i][1]-1U:sw[i][1]);
        check(one(ram,s,sw[i][0])==(hit!=0U?sw[i][3]:sw[i][2]),"state switch",sw[i][0],hit);
    }
    // The three timers (605be 60616 606dc 60766 = SUBQ.W #1,7e(A6); BCC), the phase bit tests and the BSET / BCLR.
    const std::uint32_t tm[4][3]={{0x605be,0x605f4,0x605c6},{0x60616,0x6064a,0x6061e},{0x606dc,0x60710,0x606e4},{0x60766,0x6079a,0x6076e}};
    for(unsigned int i=0;i<4;++i) {
        world(ram,s,tm[i][0],0);put(ram,NODE+0x7e,2,5);check(one(ram,s,tm[i][0])==tm[i][1] && get(ram,NODE+0x7e,2)==4 && s.carry==AnimationCarryClear,"timer running",tm[i][0]);
        world(ram,s,tm[i][0],0);put(ram,NODE+0x7e,2,0);check(one(ram,s,tm[i][0])==tm[i][2] && get(ram,NODE+0x7e,2)==0xffffU && s.carry==AnimationCarrySet,"timer expired",tm[i][0]);
    }
    world(ram,s,0x60600,0);put(ram,NODE+0x15,1,1);check(one(ram,s,0x60600)==0x60616,"60600 bit set");
    world(ram,s,0x60600,0);put(ram,NODE+0x15,1,0xfe);check(one(ram,s,0x60600)==0x6060a,"60600 bit clear");
    world(ram,s,0x606c6,0);put(ram,NODE+0x15,1,1);check(one(ram,s,0x606c6)==0x606dc,"606c6 bit set");
    world(ram,s,0x606c6,0);check(one(ram,s,0x606c6)==0x606d0,"606c6 bit clear");
    world(ram,s,0x60756,0);put(ram,NODE+0x15,1,1);check(one(ram,s,0x60756)==0x60760,"60756 bit set");
    world(ram,s,0x60756,0);check(one(ram,s,0x60756)==0x60766,"60756 bit clear");
    world(ram,s,0x6060a,0);s.carry=AnimationCarrySet;check(one(ram,s,0x6060a)==0x60616 && get(ram,NODE+0x15,1)==1 && get(ram,NODE+0x7e,2)==0xf0 && s.carry==AnimationCarryClear,"6060a BSET #0, timer f0");
    world(ram,s,0x606d0,0);check(one(ram,s,0x606d0)==0x606dc && get(ram,NODE+0x15,1)==1 && get(ram,NODE+0x7e,2)==0x78,"606d0 BSET #0, timer 78");
    world(ram,s,0x60760,0);put(ram,NODE+0x15,1,0xff);s.carry=AnimationCarrySet;check(one(ram,s,0x60760)==0x60766 && get(ram,NODE+0x15,1)==0xfe && s.carry==AnimationCarrySet,"60760 BCLR keeps C");
    // 605c6 / 605d4 / 605dc / 605e0 / 605ee: the shake (BYTE 8e) and the LONG speed 90(A6).
    world(ram,s,0x605c6,0);put(ram,NODE+0x8e,1,0x80);check(one(ram,s,0x605c6)==0x605dc && get(ram,NODE+0x7e,2)==4,"605c6 BYTE 8e negative");
    world(ram,s,0x605c6,0);put(ram,NODE+0x8e,1,0x7f);check(one(ram,s,0x605c6)==0x605d4,"605c6 BYTE 8e positive");
    world(ram,s,0x605d4,0);put(ram,NODE+0x8e,1,0x7f);check(one(ram,s,0x605d4)==0x605e0 && get(ram,NODE+0x8e,1)==0x80,"605d4 ADDQ.B");
    world(ram,s,0x605dc,0);put(ram,NODE+0x8e,1,0x80);check(one(ram,s,0x605dc)==0x605e0 && get(ram,NODE+0x8e,1)==0x7f,"605dc SUBQ.B");
    const std::uint32_t sp1[4]={0x40000,0x3ffff,0x80000000U,0x7fffffffU};const std::uint32_t t4[4]={0x605f4,0x605ee,0x605ee,0x605f4};
    for(unsigned int i=0;i<4;++i){world(ram,s,0x605e0,0);put(ram,NODE+0x90,4,sp1[i]);check(one(ram,s,0x605e0)==t4[i] && s.d[0]==sp1[i],"605e0 BGE signed LONG",sp1[i]);}
    world(ram,s,0x605ee,0);s.d[0]=0x80000;put(ram,NODE+0x90,4,0x80000);check(one(ram,s,0x605ee)==0x605f4 && get(ram,NODE+0x90,4)==0x90000U,"605ee ASR.L #3");
    // 6064a / 60670 / 60684 / 6068c / 60694 / 6069a / 6069c.
    world(ram,s,0x6064a,0);put(ram,P1+0x2e,2,0x300);put(ram,P1+0x32,2,0x400);put(ram,NODE+0x2e,2,0x100);put(ram,NODE+0x32,2,0x500);
    expect_run(ram,s,o,0x44602);
    check(s.a[0]==P1 && (s.d[0]&65535U)==((0x300U-0x30U-0x100U)&65535U) && (s.d[1]&65535U)==((0x400U+0x10U-0x500U)&65535U) && get(ram,s.a[7],4)==0x60670,"6064a");
    const std::uint32_t d0v[4]={0x1250,0x1260,0x1210,0x12ff};const std::uint32_t d8e[4]={0x50,0x50,0x50,0x00};const std::uint32_t t5[4]={0x6069c,0x60684,0x6068c,0x60684};
    for(unsigned int i=0;i<4;++i) {
        world(ram,s,0x60670,0);s.d[0]=d0v[i];put(ram,NODE+0x8e,1,d8e[i]);
        check(one(ram,s,0x60670)==t5[i] && s.d[1]==d8e[i] && (s.d[0]&65535U)==(((d0v[i]&0xffU)-d8e[i])&65535U),"60670 three-way SUB.W",i);
    }
    world(ram,s,0x60670,0);s.d[0]=0x10;put(ram,NODE+0x8e,1,0x50);one(ram,s,0x60670);check(s.carry==AnimationCarrySet,"60670 borrow Set");
    // 60684 (#80) and 6068c (#ff80): BLT folded; the wrap case 8000 - 80 has N = 0 and V = 1 (less).
    const std::uint32_t c1[6][3]={{0x60684,0x7f,0x6069a},{0x60684,0x80,0x60694},{0x60684,0x8000,0x6069a},{0x6068c,0xff80,0x60694},{0x6068c,0xff7f,0x6069a},{0x6068c,0x7fff,0x60694}};
    for(unsigned int i=0;i<6;++i){world(ram,s,c1[i][0],0);s.d[0]=0x55550000U|c1[i][1];check(one(ram,s,c1[i][0])==c1[i][2],"folded BLT",c1[i][0],c1[i][1]);}
    world(ram,s,0x60694,0);s.d[1]=0x9999fffeU;check(one(ram,s,0x60694)==0x6069c && s.d[1]==0x99990002U && s.carry==AnimationCarrySet,"60694 ADDQ.W #4 carry out");
    world(ram,s,0x6069a,0);s.d[1]=0x99990002U;check(one(ram,s,0x6069a)==0x6069c && s.d[1]==0x9999fffeU && s.carry==AnimationCarrySet,"6069a SUBQ.W #4 borrow");
    world(ram,s,0x6069c,0);s.d[1]=0x12345678U;put(ram,NODE+0x90,4,0xfffc0000U);check(one(ram,s,0x6069c)==0x606ba && s.d[1]==0x12340078U && get(ram,NODE+0x8e,1)==0x78 && s.carry==AnimationCarryClear,"6069c equal -> 606ba");
    world(ram,s,0x6069c,0);put(ram,NODE+0x90,4,0xfffc0001U);check(one(ram,s,0x6069c)==0x606b2,"6069c above -> 606b2");
    world(ram,s,0x6069c,0);put(ram,NODE+0x90,4,0x80000000U);check(one(ram,s,0x6069c)==0x606ba,"6069c negative -> 606ba");
    // 606b2 60742 607a8: SUBI.L #4000,90(A6); 606ba 6074a 607b0 605f4: BRA.W 607b4.
    const std::uint32_t sl[3][2]={{0x606b2,0x606ba},{0x60742,0x6074a},{0x607a8,0x607b0}};
    for(unsigned int i=0;i<3;++i){world(ram,s,sl[i][0],0);put(ram,NODE+0x90,4,0x4000);check(one(ram,s,sl[i][0])==sl[i][1] && get(ram,NODE+0x90,4)==0 && s.carry==AnimationCarryClear,"SUBI.L #4000",sl[i][0]);}
    world(ram,s,0x606b2,0);put(ram,NODE+0x90,4,0x3fff);one(ram,s,0x606b2);check(get(ram,NODE+0x90,4)==0xffffffffU && s.carry==AnimationCarrySet,"606b2 borrow");
    const std::uint32_t br[4]={0x605f4,0x606ba,0x6074a,0x607b0};
    for(unsigned int i=0;i<4;++i){world(ram,s,br[i],0);check(one(ram,s,br[i])==0x607b4,"BRA.W 607b4",br[i]);}
    // 60710 .. 60734: the BYTE 8e limiter (+-40 / c0) and the speed limiter.
    world(ram,s,0x60710,0);put(ram,NODE+0x8e,1,0x90);check(one(ram,s,0x60710)==0x60728 && (s.d[0]&255U)==0x90,"60710 negative");
    world(ram,s,0x60710,0);put(ram,NODE+0x8e,1,0x10);check(one(ram,s,0x60710)==0x60718,"60710 positive");
    const std::uint32_t b1[4]={0x40,0x41,0x00,0x7f};const std::uint32_t t6[4]={0x60724,0x60720,0x60724,0x60720};
    for(unsigned int i=0;i<4;++i){world(ram,s,0x60718,0);s.d[0]=b1[i];check(one(ram,s,0x60718)==t6[i],"60718 BLE signed BYTE",b1[i]);}
    const std::uint32_t b2[4]={0xc0,0xbf,0xff,0x80};const std::uint32_t t7[4]={0x60734,0x60730,0x60734,0x60730};
    for(unsigned int i=0;i<4;++i){world(ram,s,0x60728,0);s.d[0]=b2[i];check(one(ram,s,0x60728)==t7[i],"60728 BGE signed BYTE",b2[i]);}
    world(ram,s,0x60720,0);put(ram,NODE+0x8e,1,0x40);check(one(ram,s,0x60720)==0x60724 && get(ram,NODE+0x8e,1)==0x3f,"60720");
    world(ram,s,0x60724,0);check(one(ram,s,0x60724)==0x60734,"60724 BRA");
    world(ram,s,0x60730,0);put(ram,NODE+0x8e,1,0xc0);check(one(ram,s,0x60730)==0x60734 && get(ram,NODE+0x8e,1)==0xc1,"60730");
    world(ram,s,0x60734,0);put(ram,NODE+0x90,4,0xfffc0000U);check(one(ram,s,0x60734)==0x6074a,"60734 le");
    world(ram,s,0x60734,0);put(ram,NODE+0x90,4,0xfffc0001U);check(one(ram,s,0x60734)==0x60742,"60734 gt");
    world(ram,s,0x6079a,0);put(ram,NODE+0x90,4,0xfff80000U);check(one(ram,s,0x6079a)==0x607b0,"6079a le");
    world(ram,s,0x6079a,0);put(ram,NODE+0x90,4,0xfff80001U);check(one(ram,s,0x6079a)==0x607a8,"6079a gt");
    // 607b4 .. 607ee.
    world(ram,s,0x607b4,0);put(ram,NODE+0x90,4,0x1234);put(ram,NODE+0x8e,1,0x56);expect_run(ram,s,o,0x443d2);check(s.d[0]==0x1234 && (s.d[1]&255U)==0x56 && s.carry==AnimationCarryClear,"607b4");
    world(ram,s,0x607c2,0);s.d[0]=7;s.d[1]=8;expect_run(ram,s,o,0x43ea4);check(get(ram,NODE+0x36,4)==7 && get(ram,NODE+0x3a,4)==8,"607c2");
    world(ram,s,0x607d6,0);put(ram,NODE+0x72,4,0);check(one(ram,s,0x607d6)==0x607e6,"607d6 zero");
    world(ram,s,0x607d6,0);put(ram,NODE+0x72,4,0x10c777);check(one(ram,s,0x607d6)==0x607de,"607d6 target");
    world(ram,s,0x607de,0);s.d[0]=0x10c777;expect_run(ram,s,o,0x4ae4a);check(s.a[0]==0x10c777U && get(ram,s.a[7],4)==0x607e6,"607de");
    world(ram,s,0x607e6,0);s.d[0]=0x5550000U;check(one(ram,s,0x607e6)==0x6087a,"607e6 WORD 0");
    world(ram,s,0x607e6,0);s.d[0]=0x1;check(one(ram,s,0x607e6)==0x607ee,"607e6 WORD != 0");
    for(unsigned int k=0;k<2;++k) {
        const std::uint32_t pc=k==0?0x607eeU:0x60892U;
        world(ram,s,pc,0);put(ram,NODE+0x8f,1,0);check(one(ram,s,pc)==(k==0?0x6084eU:0x608f2U),"TST.B 8f zero",pc);
        world(ram,s,pc,0);put(ram,NODE+0x8f,1,1);check(one(ram,s,pc)==(k==0?0x607f6U:0x6089aU),"TST.B 8f non-zero",pc);
    }
    // 607f6 / 6089a: seven WORD pushes (3 0 0 0 1 0 0) then the 2986 call with the child value b3dbc (data).
    for(unsigned int k=0;k<2;++k) {
        world(ram,s,k==0?0x607f6U:0x6089aU,0);expect_run(ram,s,o,0x2986);
        check(s.a[0]==0xb3dbc && (s.d[0]&65535U)==0x14 && s.a[1]==0x100bf4U && s.a[7]==SP-18U && get(ram,s.a[7],4)==(k==0?0x60828U:0x608ccU) &&
            get(ram,SP-2,2)==3 && get(ram,SP-4,2)==0 && get(ram,SP-6,2)==0 && get(ram,SP-8,2)==0 && get(ram,SP-10,2)==1 && get(ram,SP-12,2)==0 && get(ram,SP-14,2)==0,"2986 push sequence");
    }
    // MOVEM.W (A7)+,D0-D6: sign extension, A7 += 14, C kept; the consumer then branches on the C of 2986.
    for(unsigned int k=0;k<2;++k)for(unsigned int carry=0;carry<2;++carry) {
        world(ram,s,MOVEM_CONSUMERS[k][0],0);put(ram,SP+0,2,0x8001);put(ram,SP+2,2,0x7fff);put(ram,SP+4,2,0xffff);put(ram,SP+6,2,0);put(ram,SP+8,2,0x1234);put(ram,SP+10,2,0x8000);put(ram,SP+12,2,3);
        s.carry=carry==0?AnimationCarryClear:AnimationCarrySet;
        check(one(ram,s,MOVEM_CONSUMERS[k][0])==MOVEM_CONSUMERS[k][carry==0?1:2] && s.d[0]==0xffff8001U && s.d[1]==0x7fffU && s.d[2]==0xffffffffU && s.d[3]==0 &&
            s.d[4]==0x1234U && s.d[5]==0xffff8000U && s.d[6]==3U && s.a[7]==SP+14U && s.carry==(carry==0?AnimationCarryClear:AnimationCarrySet),"MOVEM.W pop and consumer");
        world(ram,s,MOVEM_CONSUMERS[k][0],0);reject(ram,s,SENT,"objects b2a caller requires known carry");
    }
    // 60830 / 608d4: the child fields from D2..D6, JSR 49214.
    for(unsigned int k=0;k<2;++k) {
        world(ram,s,k==0?0x60830U:0x608d4U,0);s.d[2]=0xffff1111U;s.d[3]=0x2222;s.d[4]=0x3333;s.d[5]=0x4444;s.d[6]=0x5555;
        expect_run(ram,s,o,0x49214);
        check(get(ram,P0+0x76,2)==0x1111 && get(ram,P0+0x78,2)==0x2222 && get(ram,P0+0x7a,2)==0x3333 && get(ram,P0+0x7c,2)==0x4444 && get(ram,P0+0x7e,2)==0x5555 &&
            get(ram,s.a[7],4)==(k==0?0x6084aU:0x608eeU),"child fields");
    }
    // 6084e 608f2 6061e 606e4 6076e: MOVEA.L #d1cd8,A0; MOVE.W #a,D0; JSR 28ae.
    const std::uint32_t ch[5][2]={{0x6061e,0x6062e},{0x606e4,0x606f4},{0x6076e,0x6077e},{0x6084e,0x6085e},{0x608f2,0x60902}};
    for(unsigned int i=0;i<5;++i){world(ram,s,ch[i][0],0);expect_run(ram,s,o,0x28ae);check(s.a[0]==0xd1cd8 && (s.d[0]&65535U)==0xa && get(ram,s.a[7],4)==ch[i][1] && s.carry==AnimationCarryClear,"child d1cd8",ch[i][0]);}
    // 4970a spawn blocks: MOVE.W #0,D0 / D1; ORI.B #1,CCR blocks set C.
    const std::uint32_t sp[5][2]={{0x60632,0x60640},{0x606f8,0x60706},{0x60782,0x60790},{0x60862,0x60870},{0x60906,0x60914}};
    for(unsigned int i=0;i<5;++i){world(ram,s,sp[i][0],0);expect_run(ram,s,o,0x4970a);check(get(ram,s.a[7],4)==sp[i][1] && (s.d[0]&65535U)==0 && (s.d[1]&65535U)==0,"4970a spawn",sp[i][0]);}
    const std::uint32_t ori[8][2]={{0x5f714,0x5f718},{0x60640,0x60644},{0x60706,0x6070a},{0x60790,0x60794},{0x6084a,0x6084e},{0x60870,0x60874},{0x608ee,0x608f2},{0x60914,0x60918}};
    for(unsigned int i=0;i<8;++i){world(ram,s,ori[i][0],0);s.carry=AnimationCarryClear;check(one(ram,s,ori[i][0])==ori[i][1] && s.carry==AnimationCarrySet,"ORI.B #1,CCR",ori[i][0]);}
    world(ram,s,0x6087a,0);expect_run(ram,s,o,0x4b54e);check(get(ram,s.a[7],4)==0x60880,"6087a");
    world(ram,s,0x60884,0);put(ram,NODE+0x5e,1,5);check(one(ram,s,0x60884)==0x60888 && get(ram,NODE+0x5e,1)==0 && s.carry==AnimationCarryClear,"60884 CLR.B");
    world(ram,s,0x60888,0);put(ram,NODE+0x61,1,0x80);check(one(ram,s,0x60888)==0x60892,"60888 bit set");
    world(ram,s,0x60888,0);put(ram,NODE+0x61,1,0x7f);check(one(ram,s,0x60888)==0x6091e,"60888 bit clear");
    // 6091e / 60926: CMPI.B #3,D0 / MOVE.W 42(A6),D0; CMPI.W #140,D0; BCC.
    world(ram,s,0x6091e,0);s.d[0]=3;check(one(ram,s,0x6091e)==0x60926,"6091e equal");
    world(ram,s,0x6091e,0);s.d[0]=4;check(one(ram,s,0x6091e)==0x60938,"6091e not equal");
    world(ram,s,0x60926,0);put(ram,NODE+0x42,2,0x13f);check(one(ram,s,0x60926)==0x60932 && s.carry==AnimationCarrySet,"60926 below 140");
    world(ram,s,0x60926,0);put(ram,NODE+0x42,2,0x140);check(one(ram,s,0x60926)==0x60938 && s.carry==AnimationCarryClear,"60926 not below 140");
}
// ---- Part 2d: consumers of the known C, RTS / JMP blocks.
void part_carry() {
    for(unsigned int i=0;i<CONSUMER_COUNT;++i) {
        for(unsigned int c=0;c<2;++c) {
            Bytes ram;State s;world(ram,s,CONSUMERS[i][0],0);s.carry=c==0?AnimationCarryClear:AnimationCarrySet;
            check(one(ram,s,CONSUMERS[i][0])==CONSUMERS[i][c==0?1:2] && s.carry==(c==0?AnimationCarryClear:AnimationCarrySet),"consumer branches on the known C",CONSUMERS[i][0],c);
        }
        Bytes ram;State s;world(ram,s,CONSUMERS[i][0],0);
        reject(ram,s,SENT,"objects b2a caller requires known carry");
    }
    // RTS blocks keep the C of the path; JMP 2a00 blocks keep it too.
    const std::uint32_t rts[5]={0x5ef8a,0x5efe4,0x5f5f0,0x5f75e,0x60938};
    for(unsigned int i=0;i<5;++i)for(unsigned int c=0;c<3;++c) {
        Bytes ram;State s;Out o;world(ram,s,rts[i],0);s.carry=c==0?AnimationCarryUnknown:(c==1?AnimationCarryClear:AnimationCarrySet);expect_run(ram,s,o,SENT);
        check(s.carry==(c==0?AnimationCarryUnknown:(c==1?AnimationCarryClear:AnimationCarrySet)),"RTS keeps the C tag",rts[i],c);
    }
    const std::uint32_t jmp[15]={0x5ef70,0x5ef84,0x5efca,0x5efde,0x5f5ea,0x5f718,0x5f738,0x5f748,0x5f758,0x60644,0x6070a,0x60794,0x60874,0x60918,0x60932};
    for(unsigned int i=0;i<15;++i){Bytes ram;State s;world(ram,s,jmp[i],0);s.carry=AnimationCarrySet;check(one(ram,s,jmp[i])==0x2a00 && s.carry==AnimationCarrySet,"JMP 2a00.l",jmp[i]);}
}
// ---- Part 2e: checked errors and failure preservation.
void part_errors() {
    unsigned int internal=0;
    for(unsigned int r=0;r<RANGE_COUNT;++r)for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2) {
        if(is_step(pc))continue;
        Bytes ram;State s;world(ram,s,pc,0);reject(ram,s,SENT,"unsupported animation objects b2a PC");++internal;
    }
    check(internal>600,"internal even PCs are checked errors",internal);
    // The folded branches are interior PCs.
    const std::uint32_t folded[]={0x5f592,0x5f678,0x60680,0x60690};
    for(unsigned int i=0;i<4;++i){Bytes ram;State s;world(ram,s,folded[i],0);reject(ram,s,SENT,"unsupported animation objects b2a PC");}
    // Boundaries (review 0264 M-3): the probes without an executor are work-RAM PCs; the ROM neighbours 4b6f4 5eed0 5f4b0 5f502 60514 6093a (code of later units)
    // are only asserted to be outside the unit's own ranges.  The leaving call 5ef66 -> 4b6f4 is a stop-only check.
    const std::uint32_t ends[]={0x4b6f4,0x5eed0,0x5f4b0,0x5f502,0x60514,0x6093a};
    for(unsigned int i=0;i<sizeof(ends)/sizeof(ends[0]);++i)check(!in_ranges(ends[i]),"neighbour outside the unit ranges",ends[i]);
    const std::uint32_t unrouted[]={0x10fe00,0x10fe02,0x10fe04,0x10fe06,0x10fe08,0x10fe0c,0x10fe0e};
    for(unsigned int i=0;i<sizeof(unrouted)/sizeof(unrouted[0]);++i) {
        Bytes ram;State s;world(ram,s,unrouted[i],0);reject(ram,s,SENT,"unsupported animation machine PC");
    }
    {   // The call 5ef66 -> JSR 4b6f4 stops exactly at 4b6f4; the work-RAM probe 10fe0a is the rollback probe (6064a -> 44602 is routed by B2e).
        Bytes ram;State s;Out o;world(ram,s,0x5ef66,0);check(run(ram,s,0x4b6f4,o)&&s.pc==0x4b6f4,"stop at the boundary 4b6f4",s.pc);
        world(ram,s,0x10fe0a,0);reject(ram,s,SENT,"unsupported animation machine PC");
    }
    {
        Bytes ram;State s;world(ram,s,0x5eed3,0);reject(ram,s,SENT,"unaligned animation machine PC");
        world(ram,s,0x5eee2,0);s.a[6]=NODE+1U;reject(ram,s,SENT,"invalid animation machine write size/alignment");          // odd LONG store 36(A6)
        world(ram,s,0x5f520,0);s.a[6]=NODE+1U;reject(ram,s,SENT,"invalid animation machine write size/alignment");
    }
    {   // 5f5da installs 5f5f2 at (A6), then falls into 5f5e0 and calls the boundary 4b6f4: the stop at 4b6f4 commits the install (the former
        // rollback variant without a stop PC depended on 4b6f4 staying unrouted; rollback of earlier stores is covered by the work-RAM probes above).
        Bytes ram;State s;Out o;world(ram,s,0x5f5da,0);
        check(run(ram,s,0x4b6f4,o)&&s.pc==0x4b6f4&&get(ram,NODE,4)==0x5f5f2,"the install store is committed at the boundary stop",get(ram,NODE,4));
    }
}
}
int main() {
    steps();
    part_5eed2();
    part_5f504();
    part_60516();
    part_carry();
    part_errors();
    std::cout<<"objects b2a: "<<checks<<" checks, "<<STEP_COUNT<<" block starts stepped in 2 worlds\n";
    return 0;
}
