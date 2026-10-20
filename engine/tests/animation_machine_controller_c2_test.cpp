#include "ms5/animation_machine.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <string>
// Controller C2 (164 block starts: the transitions / teardown / game-mode branch c4cc c686 c74c c76a c79a c7c6 c80e c82e..c982, the card request c2fa..c35c with the
// menu table bbd4, the input mode 3162, the frame counter 100e / 101c, game initialisation 47570 4755e e62ec 4823a, the RNG table 49a1a, 4e1cc, the child b300 / b344 and the
// menu item handlers a856 a876 a896 a8bc with the common a75a) through run_animation_machine only.
// Inputs are declared fixtures: zero RAM with the declared return LONG at A7 = 10f000, the controller node A6 = 1008e4, A5 = 108000, seeded registers, the fixture's RAM puts, the
// incoming C tag and synthetic typed physical bytes (not ROM data: ROM WORD 180 and the replay / recorder tables f0dfe / f1a06). Every block is entered directly and run to its
// successor (the stop PC), so one row checks one original block: the register / RAM / stack effect written out from the original instructions (docs/analysis/animation-machine-
// controller-c2-contract.md), the successor PC and the carry policy (the 72 FLOW blocks keep the incoming C, every other block ends Unknown). The same blocks are compared against
// the original ROM on native Unicorn by tools/unit_fixture_specs/c2.py (natural controller frames, the Execute-mode N pass with b300 / b344 / the handlers) and the D9
// Execute-mode frame comparison tools/verify_animation_machine_frame_controller.py --declare game.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
typedef ms5::AnimationMachineDevice Device;
typedef std::vector<ms5::VideoPortWrite> Ports;
typedef std::vector<ms5::PhysicalRomResource> Rom;
const std::uint32_t A5=0x108000,NODE=0x1008e4,SP=0x10f000,RET=0xff000,BIOS_RETURN=0xc00444,BIOS_CARD=0xc00468;
unsigned int checks=0;
std::vector<std::uint32_t> reached;
// The 72 FLOW blocks (JSR / BSR / JMP / BRA / RTS, LEA / MOVEA, conditional branches): the incoming C is kept.
const std::uint32_t FLOW[]={0x31d4,0xc2fa,0xc4cc,0xc4d2,0xc4d8,0xc4ee,0xc4f6,0xc69a,0xc69e,0xc6a2,0xc6c8,0xc766,0xc772,0xc776,0xc77a,0xc7c0,0xc7ce,0xc7d2,0xc7d6,0xc7e6,
 0xc81a,0xc846,0xc84a,0xc84e,0xc85e,0xc874,0xc87e,0xc882,0xc886,0xc88a,0xc890,0xc8aa,0xc8b0,0xc8b4,0xc8c4,0xc8ca,0xc90c,0xc916,0xc91a,0xc91e,0xc922,0xc952,0xc964,0xc968,
 0xc97a,0xc97e,0xc982,0x4756e,0x47582,0x4758a,0xe62f2,0xe62fc,0xb300,0xb306,0xb31a,0xb344,0xb360,0xa75a,0xa856,0xa868,0xa86c,0xa874,0xa876,0xa888,0xa88c,0xa894,0xa896,
 0xa8a8,0xa8ba,0xa8bc,0xa8c8,0xa8ce};
const unsigned int FLOW_COUNT=sizeof(FLOW)/sizeof(FLOW[0]);
const std::uint32_t STARTS[]={0x100e,0x101c,0x3162,0x3180,0x3188,0x31c4,0x31ce,0x31d4,0xbbd4,0xbbe4,0xbbf4,0xc2fa,0xc2fe,0xc316,0xc326,0xc332,0xc346,0xc35c,0xc4cc,0xc4d2,
 0xc4d8,0xc4dc,0xc4e6,0xc4ee,0xc4f6,0xc686,0xc690,0xc69a,0xc69e,0xc6a2,0xc6a6,0xc6b6,0xc6c0,0xc6c8,0xc74c,0xc754,0xc75e,0xc766,0xc76a,0xc772,0xc776,0xc77a,0xc77e,0xc794,
 0xc79a,0xc7a4,0xc7ae,0xc7ba,0xc7c0,0xc7c6,0xc7ce,0xc7d2,0xc7d6,0xc7dc,0xc7e6,0xc7f6,0xc80e,0xc81a,0xc81e,0xc826,0xc82e,0xc836,0xc83e,0xc846,0xc84a,0xc84e,0xc854,0xc85e,
 0xc86e,0xc874,0xc87e,0xc882,0xc886,0xc88a,0xc890,0xc896,0xc89c,0xc8a4,0xc8aa,0xc8b0,0xc8b4,0xc8b8,0xc8c4,0xc8ca,0xc8ce,0xc8e2,0xc8e8,0xc8f0,0xc906,0xc90c,0xc916,0xc91a,
 0xc91e,0xc922,0xc926,0xc936,0xc940,0xc948,0xc952,0xc95c,0xc964,0xc968,0xc972,0xc97a,0xc97e,0xc982,0x4755e,0x47566,0x4756e,0x47570,0x47582,0x47584,0x4758a,0x4823a,0x48242,
 0x48244,0x49a1a,0x49a26,0x49a34,0x49a3e,0x49a50,0x4e1cc,0x4e1f8,0x4e20e,0xe62ec,0xe62f2,0xe62fc,0xe6302,0xb300,0xb306,0xb30c,0xb31a,0xb326,0xb330,0xb33e,0xb344,0xb34a,
 0xb350,0xb360,0xa75a,0xa760,0xa76a,0xa856,0xa85a,0xa860,0xa868,0xa86c,0xa874,0xa876,0xa87a,0xa880,0xa888,0xa88c,0xa894,0xa896,0xa89a,0xa8a0,0xa8a8,0xa8ae,0xa8ba,0xa8bc,
 0xa8c0,0xa8c8,0xa8ce};
const unsigned int START_COUNT=sizeof(STARTS)/sizeof(STARTS[0]);
const std::uint32_t RANGES[][2]={{0x100e,0x1022},{0x3162,0x31d6},{0xbbd4,0xbbfa},{0xc2fa,0xc364},{0xc4cc,0xc4f8},{0xc686,0xc6ce},{0xc74c,0xc7fc},{0xc80e,0xc988},
 {0x4755e,0x47594},{0x4823a,0x48250},{0x49a1a,0x49a58},{0x4e1cc,0x4e216},{0xe62ec,0xe630a},{0xb300,0xb362},{0xa75a,0xa770},{0xa856,0xa8d0}};
const unsigned int RANGE_COUNT=sizeof(RANGES)/sizeof(RANGES[0]);
bool is_flow(std::uint32_t pc){for(unsigned int i=0;i<FLOW_COUNT;++i)if(FLOW[i]==pc)return true;return false;}
bool is_start(std::uint32_t pc){for(unsigned int i=0;i<START_COUNT;++i)if(STARTS[i]==pc)return true;return false;}
// Synthetic typed physical bytes (not ROM data): the replay table f0dfe (LONGs 100200 100300), the recorder table f1a06 (LONGs 100400 100500) and ROM WORD 180.
Rom make_rom(std::uint32_t word180){
 Rom p(3);
 p[0].source_rom_offset=0x180;p[0].data.push_back(static_cast<std::uint8_t>(word180>>8));p[0].data.push_back(static_cast<std::uint8_t>(word180));
 p[1].source_rom_offset=0xf0dfe;{const std::uint8_t b[8]={0x00,0x10,0x02,0x00,0x00,0x10,0x03,0x00};p[1].data.assign(b,b+8);}
 p[2].source_rom_offset=0xf1a06;{const std::uint8_t b[8]={0x00,0x10,0x04,0x00,0x00,0x10,0x05,0x00};p[2].data.assign(b,b+8);}
 return p;}
const Rom ROM0=make_rom(0);
const Rom ROM1=make_rom(0x1234);
void put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes& b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
Bytes base_ram(){Bytes r(65536,0);put(r,SP,4,RET);return r;}
State base_state(std::uint32_t pc){
 State s;for(unsigned int i=0;i<8;++i){s.d[i]=0x11110000U*(i+1)+i;s.a[i]=0xa0a0a0a0U+i*0x01010101U;}
 s.a[5]=A5;s.a[6]=NODE;s.a[7]=SP;s.pc=pc;s.carry=ms5::AnimationCarrySet;return s;}
Device base_device(){Device d;d.pvc[0x1ff1]=0xa0;d.pvc[0x1ff2]=0x20;d.bank_base=0x300000;return d;}
struct Out {bool ok;Bytes ram;State s;Device d;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;};
Out run(const Bytes& ram,const State& s,std::uint32_t stop,const Rom& rom){
 Out o;o.ram=ram;o.s=s;o.d=base_device();o.reads=7;o.status=ms5::AnimationMachineWaiting;
 ms5::ProgramBusState bus;bus.physical_rom=&rom;std::vector<ms5::FixedDataResource> w;
 o.ok=ms5::run_animation_machine(o.ram,w,bus,o.s,o.d,stop,0,o.reads,o.status,o.ports,o.error);return o;}
bool same_state(const State& a,const State& b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
// One block (or a short run) entered at s.pc and stopped at `next`: returned, no external read, the carry policy.
Out go(const Bytes& ram,const State& s,std::uint32_t next,const Rom& rom=ROM0){
 Out o=run(ram,s,next,rom);
 if(!o.ok)std::cerr<<"error '"<<o.error<<"' at block "<<std::hex<<s.pc<<" stop "<<next<<"\n";
 assert(o.ok&&o.status==ms5::AnimationMachineReturned&&o.s.pc==next&&o.reads==0);
 if(o.s.carry!=(is_flow(s.pc)?s.carry:ms5::AnimationCarryUnknown)){std::cerr<<"carry policy of "<<std::hex<<s.pc<<"\n";assert(false);}
 reached.push_back(s.pc);++checks;return o;}
void fail(const Bytes& ram,const State& s,std::uint32_t stop,const char* message,const Rom& rom=ROM0){
 Out o=run(ram,s,stop,rom);
 if(o.ok||o.error!=message)std::cerr<<"expected '"<<message<<"' got ok="<<o.ok<<" '"<<o.error<<"' pc "<<std::hex<<s.pc<<"\n";
 const Device d=base_device();
 assert(!o.ok&&o.error==message&&o.ram==ram&&same_state(o.s,s)&&o.d.pvc==d.pvc&&o.d.bank_base==d.bank_base&&o.ports.empty()&&o.reads==7&&
  o.status==ms5::AnimationMachineWaiting);++checks;}
// Only the listed [lo, hi) RAM ranges may differ.
void only_changed(const Bytes& a,const Bytes& b,const std::uint32_t* lo,const std::uint32_t* hi,unsigned int n){
 for(std::uint32_t i=0;i<65536;++i){bool allowed=false;for(unsigned int k=0;k<n;++k)if(0x100000U+i>=lo[k]&&0x100000U+i<hi[k])allowed=true;
  if(!allowed&&a[i]!=b[i]){std::cerr<<std::hex<<"unexpected change "<<(0x100000U+i)<<"\n";assert(false);}}}
void one(const Bytes& a,const Bytes& b,std::uint32_t lo,std::uint32_t hi){only_changed(a,b,&lo,&hi,1);}
// A call block: the return LONG on the stack, A7 down by 4, the successor is the callee.
void called(const Out& o,const State& s,std::uint32_t ret){assert(o.s.a[7]==s.a[7]-4&&get(o.ram,o.s.a[7],4)==ret);}
// The registers other than the listed ones are untouched.
void regs_kept(const Out& o,const State& s,unsigned int d_mask,unsigned int a_mask){
 for(unsigned int i=0;i<8;++i){if(!(d_mask&(1U<<i)))assert(o.s.d[i]==s.d[i]);if(!(a_mask&(1U<<i)))assert(o.s.a[i]==s.a[i]);}}

// ---- frame counter 100e / 101c, input mode 3162 3180 3188 31c4 31ce 31d4
void counters(){
 {Bytes ram=base_ram();put(ram,0x10000e,2,0x1111);put(ram,0x10089e,2,0x2222);const State s=base_state(0x100e);const Out o=go(ram,s,RET);
  assert(get(o.ram,0x10000e,2)==0&&get(o.ram,0x10089e,2)==0&&o.s.a[7]==SP+4);const std::uint32_t lo[2]={0x10000e,0x10089e},hi[2]={0x100010,0x1008a0};only_changed(ram,o.ram,lo,hi,2);
  regs_kept(o,s,0,128);}
 {Bytes ram=base_ram();put(ram,0x100017,1,0x77);State s=base_state(0x101c);s.d[0]=0x123456cdU;const Out o=go(ram,s,RET);
  assert(get(o.ram,0x100017,1)==0xcd&&o.s.a[7]==SP+4);one(ram,o.ram,0x100017,0x100018);regs_kept(o,s,0,128);}
 // 3162: A5 := 108000, 104ca8..104cb3 cleared (CLR.L / CLR.W twice), A0 = 104cb2; D0.W < 2 selects the replay branch 3188.
 const std::uint32_t d0s[8]={0,1,2,3,0x10000,0x10001,0xffff,0x12345678};
 for(unsigned int k=0;k<8;++k){
  Bytes ram=base_ram();for(std::uint32_t a=0x104ca4;a<0x104cb8;++a)put(ram,a,1,0xa5);State s=base_state(0x3162);s.d[0]=d0s[k];s.a[5]=0x12344;
  const bool replay=(d0s[k]&0xffffU)<2U;const Out o=go(ram,s,replay?0x3188U:0x3180U);
  for(std::uint32_t a=0x104ca8;a<0x104cb4;++a)assert(get(o.ram,a,1)==0);assert(get(o.ram,0x104ca7,1)==0xa5&&get(o.ram,0x104cb4,1)==0xa5);
  assert(o.s.a[5]==A5&&o.s.a[0]==0x104cb2&&o.s.d[0]==d0s[k]);one(ram,o.ram,0x104ca8,0x104cb4);regs_kept(o,s,0,0x21);}
 {Bytes ram=base_ram();put(ram,0x104cd4,1,0x55);const State s=base_state(0x3180);const Out o=go(ram,s,RET);
  assert(get(o.ram,0x104cd4,1)==0&&o.s.a[7]==SP+4);one(ram,o.ram,0x104cd4,0x104cd5);regs_kept(o,s,0,128);}
 // 3188: BYTE 104cd4 := 1, LONG 104cc4 / 104cc8 := replay / recorder table [4 * D0.W], the counters 104cc2 104cd0 104ccc 104cce cleared, D0.W := ROM WORD 180 (0 -> 31d4).
 for(unsigned int k=0;k<2;++k){
  Bytes ram=base_ram();for(std::uint32_t a=0x104cc0;a<0x104cd8;++a)put(ram,a,1,0x5a);State s=base_state(0x3188);s.d[0]=0xabcd0000U|k;
  const Out o=go(ram,s,0x31d4);
  assert(get(o.ram,0x104cd4,1)==1&&get(o.ram,0x104cc4,4)==(k?0x100300U:0x100200U)&&get(o.ram,0x104cc8,4)==(k?0x100500U:0x100400U));
  assert(get(o.ram,0x104cc2,2)==0&&get(o.ram,0x104ccc,2)==0&&get(o.ram,0x104cce,2)==0&&get(o.ram,0x104cd0,1)==0&&get(o.ram,0x104cd1,1)==0x5a);
  assert(o.s.d[0]==0xabcd0000U&&o.s.a[0]==0xf1a06);one(ram,o.ram,0x104cc2,0x104cd5);}
 {const Bytes ram=base_ram();State s=base_state(0x3188);s.d[0]=0xabcd0000U;const Out o=go(ram,s,0x31c4,ROM1);assert(o.s.d[0]==0xabcd1234U);}
 // 3188 with D0.W = 0x8000 + 1: the index is the sign extended WORD (4 * 0x8001 = 0x20004 -> WORD 0004): 4 bytes into the table.
 {const Bytes ram=base_ram();State s=base_state(0x3188);s.d[0]=0x8001;const Out o=go(ram,s,0x31d4);assert(get(o.ram,0x104cc4,4)==0x100300U);}
 // 31c4: A0 := LONG 104cc8, D1 := ffffffff, D7.W := 5ff (the upper word kept).
 {Bytes ram=base_ram();put(ram,0x104cc8,4,0x100800);State s=base_state(0x31c4);s.d[7]=0x12340000U;const Out o=go(ram,s,0x31ce);
  assert(o.s.a[0]==0x100800&&o.s.d[1]==0xffffffffU&&o.s.d[7]==0x123405ffU);one(ram,o.ram,0x100000,0x100000);}
 // 31ce: BYTE D1 at (A0)+, DBRA D7.W (a self loop: run to the exit 31d4 with D7.W = 1 (two bytes) and 0 (one byte)).
 {const Bytes ram=base_ram();State s=base_state(0x31ce);s.a[0]=0x100800;s.d[1]=0x1234ab;s.d[7]=0x50001;const Out o=go(ram,s,0x31d4);
  assert(get(o.ram,0x100800,1)==0xab&&get(o.ram,0x100801,1)==0xab&&get(o.ram,0x100802,1)==0&&o.s.a[0]==0x100802&&o.s.d[7]==0x5ffffU);one(ram,o.ram,0x100800,0x100802);
  s.d[7]=0x50000;const Out p=go(ram,s,0x31d4);assert(p.s.d[7]==0x5ffffU&&p.s.a[0]==0x100801&&get(p.ram,0x100801,1)==0);one(ram,p.ram,0x100800,0x100801);}
 // The whole recorder fill 31c4 .. 31d4: 0x600 bytes of ff.
 {Bytes ram=base_ram();put(ram,0x104cc8,4,0x100800);const State s=base_state(0x31c4);const Out o=go(ram,s,RET);
  for(std::uint32_t a=0x100800;a<0x100e00;++a)assert(get(o.ram,a,1)==0xff);assert(get(o.ram,0x100e00,1)==0&&o.s.a[0]==0x100e00&&o.s.d[7]==0x8888ffffU);}
 {const Bytes ram=base_ram();const State s=base_state(0x31d4);const Out o=go(ram,s,RET);assert(o.s.a[7]==SP+4);}
}

// ---- card menu table bbd4 bbe4 bbf4, card request c2fa c2fe c316 c326 c332 c346 c35c
void card_request(){
 {const Bytes ram=base_ram();const State s=base_state(0xbbd4);const Out o=go(ram,s,0xbbb8);called(o,s,0xbbe4);assert(o.s.a[0]==0x107f1c&&o.s.a[1]==0xbb8e&&(o.s.d[7]&0xffffU)==0x18U&&(o.s.d[7]>>16)==(s.d[7]>>16));}
 {const Bytes ram=base_ram();State s=base_state(0xbbe4);const Out o=go(ram,s,0xbb74);called(o,s,0xbbf4);
  assert(o.s.a[0]==0x107f1c&&get(o.ram,0x107f31,1)==0xff&&(o.s.d[7]&0xffffU)==0x16U);const std::uint32_t lo[2]={0x107f31,SP-4},hi[2]={0x107f32,SP};only_changed(ram,o.ram,lo,hi,2);}
 {Bytes ram=base_ram();State s=base_state(0xbbf4);s.d[0]=0xfedc4321U;const Out o=go(ram,s,RET);assert(get(o.ram,0x107f32,2)==0x4321&&o.s.a[7]==SP+4);one(ram,o.ram,0x107f32,0x107f34);}
 {const Bytes ram=base_ram();const State s=base_state(0xc2fa);const Out o=go(ram,s,0xbbd4);called(o,s,0xc2fe);}
 // c2fe: push A6, BYTE 10fdc4 := 1, WORD 10fdce := 268, JSR c00468 (the BIOS card, return c316).
 {const Bytes ram=base_ram();const State s=base_state(0xc2fe);const Out o=go(ram,s,BIOS_CARD);
  assert(o.s.a[7]==SP-8&&get(o.ram,SP-8,4)==0xc316&&get(o.ram,SP-4,4)==NODE&&get(o.ram,0x10fdc4,1)==1&&get(o.ram,0x10fdce,2)==0x268);
  const std::uint32_t lo[3]={0x10fdc4,0x10fdce,SP-8},hi[3]={0x10fdc5,0x10fdd0,SP};only_changed(ram,o.ram,lo,hi,3);}
 // c316: A6 := (A7)+, A5 := 108000, BYTE 10fdc6 != 0 -> c35c, else c326.
 for(unsigned int k=0;k<2;++k){
  Bytes ram=base_ram();put(ram,SP,4,0x1009c0);put(ram,0x10fdc6,1,k?0x80:0);State s=base_state(0xc316);s.a[5]=0x1234;const Out o=go(ram,s,k?0xc35cU:0xc326U);
  assert(o.s.a[6]==0x1009c0&&o.s.a[5]==A5&&o.s.a[7]==SP+4);one(ram,o.ram,0x100000,0x100000);}
 // c326: D0.W := WORD 10fdd0, BTST #0 (bit 0 set -> c332, clear -> c35c).
 for(unsigned int k=0;k<4;++k){
  Bytes ram=base_ram();const std::uint32_t words[4]={0x0001,0x0100,0xffff,0x0002};put(ram,0x10fdd0,2,words[k]);State s=base_state(0xc326);
  const Out o=go(ram,s,(words[k]&1U)?0xc332U:0xc35cU);assert((o.s.d[0]&0xffffU)==words[k]&&(o.s.d[0]>>16)==(s.d[0]>>16));}
 // c332: BYTE 62(A6) := 0, A0 := c250, D0.W := 0, JSR 28ae.
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,0x44);State s=base_state(0xc332);const Out o=go(ram,s,0x28ae);called(o,s,0xc346);
  assert(get(o.ram,NODE+0x62,1)==0&&o.s.a[0]==0xc250&&(o.s.d[0]&0xffffU)==0&&(o.s.d[0]>>16)==(s.d[0]>>16));}
 // c346: LONG 76(A0) := bef0, WORD 7a(A0) := 4, WORD 7c(A0) := 4, RTS (A0 is the allocation result, also the failure node 100e98).
 {Bytes ram=base_ram();State s=base_state(0xc346);s.a[0]=0x100c00;const Out o=go(ram,s,RET);
  assert(get(o.ram,0x100c76,4)==0xbef0&&get(o.ram,0x100c7a,2)==4&&get(o.ram,0x100c7c,2)==4&&o.s.a[7]==SP+4);const std::uint32_t lo[2]={0x100c76,0x100c7a},hi[2]={0x100c7a,0x100c7e};only_changed(ram,o.ram,lo,hi,2);}
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,0);const State s=base_state(0xc35c);const Out o=go(ram,s,RET);assert(get(o.ram,NODE+0x62,1)==0xff&&o.s.a[7]==SP+4);one(ram,o.ram,NODE+0x62,NODE+0x63);}
}

// ---- teardown c4cc c4d2 c4d8 c4dc c4e6 c4ee c4f6
void teardown(){
 {const Bytes ram=base_ram();const State s=base_state(0xc4cc);const Out o=go(ram,s,0x3dce);called(o,s,0xc4d2);}
 {const Bytes ram=base_ram();const State s=base_state(0xc4d2);const Out o=go(ram,s,0x2a0a);called(o,s,0xc4d8);}
 {Bytes ram=base_ram();put(ram,NODE+8,4,0x100a40);const State s=base_state(0xc4d8);const Out o=go(ram,s,0xc4dc);assert(o.s.a[0]==0x100a40);}
 // c4dc: CMPA.L #100820,A0; BEQ -> c4f6 (the list head), else c4e6.
 {const Bytes ram=base_ram();State s=base_state(0xc4dc);s.a[0]=0x100820;go(ram,s,0xc4f6);s.a[0]=0x100a40;go(ram,s,0xc4e6);s.a[0]=0x10082000U;go(ram,s,0xc4e6);}
 {const Bytes ram=base_ram();State s=base_state(0xc4e6);s.a[0]=0x100a40;const Out o=go(ram,s,0x2a84);assert(o.s.a[7]==SP-8&&get(o.ram,SP-8,4)==0xc4ee&&get(o.ram,SP-4,4)==0x100a40);}
 // c4ee: A0 := (A7)+, A0 := LONG 8(A0), BRA c4dc.
 {Bytes ram=base_ram();put(ram,SP,4,0x100a40);put(ram,0x100a48,4,0x100820);const State s=base_state(0xc4ee);const Out o=go(ram,s,0xc4dc);assert(o.s.a[0]==0x100820&&o.s.a[7]==SP+4);}
 {const Bytes ram=base_ram();const State s=base_state(0xc4f6);const Out o=go(ram,s,RET);assert(o.s.a[7]==SP+4);}
 // The loop through c4dc / c4e6 / c4ee with a declared callee-free list is exercised by the native chains (tools/unit_fixture_specs/c2.py chain-teardown).
}

// ---- demo end c686 c690 c69a c69e c6a2 c6a6 c6b6 c6c0 c6c8
void demo_end(){
 {const Bytes ram=base_ram();const State s=base_state(0xc686);go(ram,s,0xc69a,ROM0);go(ram,s,0xc690,ROM1);}
 {const Bytes ram=base_ram();const State s=base_state(0xc690);fail(ram,s,0xc610,"unsupported animation machine write device",ROM1);reached.push_back(0xc690);}
 {const Bytes ram=base_ram();State s=base_state(0xc69a);Out o=go(ram,s,0xc4cc);called(o,s,0xc69e);s.pc=0xc69e;o=go(ram,s,0xcaf0);called(o,s,0xc6a2);s.pc=0xc6a2;o=go(ram,s,0xca76);called(o,s,0xc6a6);}
 {const Bytes ram=base_ram();State s=base_state(0xc6a6);const Out o=go(ram,s,0x28ae);called(o,s,0xc6b6);assert(o.s.a[0]==0xe66aa&&(o.s.d[0]&0xffffU)==0);}
 // c6b6: BYTE 62(A6) := 0, LONG (A6) := c6c0, on into c6c0.
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,9);put(ram,NODE,4,0x1234);const State s=base_state(0xc6b6);const Out o=go(ram,s,0xc6c0);
  assert(get(o.ram,NODE+0x62,1)==0&&get(o.ram,NODE,4)==0xc6c0);const std::uint32_t lo[2]={NODE,NODE+0x62},hi[2]={NODE+4,NODE+0x63};only_changed(ram,o.ram,lo,hi,2);}
 // c6c0: BYTE 62(A6) == 0 -> c73e (C1 tail gate), else the BIOS system return; c6c8 is the JMP c00444.
 {Bytes ram=base_ram();const State s=base_state(0xc6c0);go(ram,s,0xc73e);put(ram,NODE+0x62,1,1);go(ram,s,0xc6c8);put(ram,NODE+0x62,1,0xff);go(ram,s,0xc6c8);}
 {const Bytes ram=base_ram();const State s=base_state(0xc6c8);const Out o=go(ram,s,BIOS_RETURN);assert(o.s.a[7]==SP);}
 {const Bytes ram=base_ram();const State s=base_state(0xc6c8);fail(ram,s,RET,"unsupported animation machine PC");}
}

// ---- game start c74c c754 c75e c766, stage end transition c76a..c794, waiting state c79a c7a4 c7ae c7ba c7c0
void game_branch(){
 {const Bytes ram=base_ram();State s=base_state(0xc74c);s.d[0]=0x55555555U;const Out o=go(ram,s,0x8bbc);called(o,s,0xc754);assert(o.s.d[0]==0);}
 {const Bytes ram=base_ram();State s=base_state(0xc754);s.d[0]=0x55555500U;const Out o=go(ram,s,0x101c);called(o,s,0xc75e);assert(o.s.d[0]==0x55555502U);}
 // c75e: BYTE 7d82(A5) == 0 -> the transition c76a, else c766.
 {Bytes ram=base_ram();const State s=base_state(0xc75e);go(ram,s,0xc76a);put(ram,0x10fd82,1,1);go(ram,s,0xc766);}
 {const Bytes ram=base_ram();const State s=base_state(0xc766);go(ram,s,0xc80e);}
 {const Bytes ram=base_ram();State s=base_state(0xc76a);const Out o=go(ram,s,0x3162);called(o,s,0xc772);assert(o.s.d[0]==0xffffffffU);}
 {const Bytes ram=base_ram();State s=base_state(0xc772);Out o=go(ram,s,0xc4cc);called(o,s,0xc776);s.pc=0xc776;o=go(ram,s,0xca76);called(o,s,0xc77a);s.pc=0xc77a;o=go(ram,s,0xcaf0);called(o,s,0xc77e);}
 // c77e: BYTE 62(A6) := 0, A0 := b300, D0.W := 14, JSR 28ae.
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,2);State s=base_state(0xc77e);const Out o=go(ram,s,0x28ae);called(o,s,0xc794);
  assert(get(o.ram,NODE+0x62,1)==0&&o.s.a[0]==0xb300&&(o.s.d[0]&0xffffU)==0x14U&&(o.s.d[0]>>16)==(s.d[0]>>16));}
 {Bytes ram=base_ram();put(ram,NODE,4,0x1111);const State s=base_state(0xc794);const Out o=go(ram,s,0xc79a);assert(get(o.ram,NODE,4)==0xc79a);one(ram,o.ram,NODE,NODE+4);}
 // c79a / c7a4: BYTE 10fdb6 / 10fdb7 == 1 -> the continue path c80e.
 {Bytes ram=base_ram();const State s=base_state(0xc79a);go(ram,s,0xc7a4);put(ram,0x10fdb6,1,2);go(ram,s,0xc7a4);put(ram,0x10fdb6,1,1);go(ram,s,0xc80e);}
 {Bytes ram=base_ram();const State s=base_state(0xc7a4);go(ram,s,0xc7ae);put(ram,0x10fdb7,1,0xff);go(ram,s,0xc7ae);put(ram,0x10fdb7,1,1);go(ram,s,0xc80e);}
 // c7ae: D0.B := BYTE 62(A6); == 2 -> the restart c7c6, else c7ba.
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,2);State s=base_state(0xc7ae);const Out o=go(ram,s,0xc7c6);assert(o.s.d[0]==((s.d[0]&0xffffff00U)|2U));
  put(ram,NODE+0x62,1,3);const Out p=go(ram,s,0xc7ba);assert(p.s.d[0]==((s.d[0]&0xffffff00U)|3U));put(ram,NODE+0x62,1,0);go(ram,s,0xc7ba);}
 // c7ba: TST.B D0; == 0 -> the common tail c988, else the BIOS system return c7c0.
 {const Bytes ram=base_ram();State s=base_state(0xc7ba);s.d[0]=0x12345600U;go(ram,s,0xc988);s.d[0]=0x12345601U;go(ram,s,0xc7c0);s.d[0]=0xff;go(ram,s,0xc7c0);}
 {const Bytes ram=base_ram();const State s=base_state(0xc7c0);const Out o=go(ram,s,BIOS_RETURN);assert(o.s.a[7]==SP);}
}

// ---- restart c7c6 c7ce c7d2 c7d6 c7dc c7e6 c7f6
void restart(){
 {const Bytes ram=base_ram();State s=base_state(0xc7c6);const Out o=go(ram,s,0x49a1a);called(o,s,0xc7ce);assert(o.s.d[0]==0xffffffffU);}
 {const Bytes ram=base_ram();State s=base_state(0xc7ce);Out o=go(ram,s,0xc4cc);called(o,s,0xc7d2);s.pc=0xc7d2;o=go(ram,s,0xcaf0);called(o,s,0xc7d6);s.pc=0xc7d6;o=go(ram,s,0x47570);called(o,s,0xc7dc);}
 {const Bytes ram=base_ram();State s=base_state(0xc7dc);s.d[0]=0xffffffffU;const Out o=go(ram,s,0x4823a);called(o,s,0xc7e6);assert(o.s.d[0]==0xffff0008U);}
 // c7e6: A0 := A5 - 74d0 (= 100b30, the stage controller node), A1 := 477e4, JSR 2a28.
 {const Bytes ram=base_ram();const State s=base_state(0xc7e6);const Out o=go(ram,s,0x2a28);called(o,s,0xc7f6);assert(o.s.a[0]==0x100b30&&o.s.a[1]==0x477e4);}
 {Bytes ram=base_ram();const State s=base_state(0xc7f6);const Out o=go(ram,s,0xc7fc);assert(get(o.ram,NODE,4)==0xc7fc);one(ram,o.ram,NODE,NODE+4);}
}

// ---- continue path c80e c81a c81e c826 and the waiting states c82e c836 c83e c846 c84a c84e c854 c85e c86e c874 c87e c882 c886 c88a c890 c896 c89c c8a4
void continue_path(){
 {Bytes ram=base_ram();put(ram,0x10f02a,2,0x1234);State s=base_state(0xc80e);const Out o=go(ram,s,0x3162);called(o,s,0xc81a);assert(get(o.ram,0x10f02a,2)==0&&o.s.d[0]==0xffffffffU);}
 {const Bytes ram=base_ram();const State s=base_state(0xc81a);const Out o=go(ram,s,0xc4cc);called(o,s,0xc81e);}
 {const Bytes ram=base_ram();State s=base_state(0xc81e);const Out o=go(ram,s,0x49a1a);called(o,s,0xc826);assert(o.s.d[0]==0xffffffffU);}
 {Bytes ram=base_ram();const State s=base_state(0xc826);const Out o=go(ram,s,RET);assert(get(o.ram,NODE,4)==0xc82e&&o.s.a[7]==SP+4);}
 // c82e: BYTE 7d82 == 0 -> c882; c836: BYTE 7d8e == 0 -> c882; otherwise c83e.
 {Bytes ram=base_ram();const State s=base_state(0xc82e);go(ram,s,0xc882);put(ram,0x10fd82,1,1);go(ram,s,0xc836);}
 {Bytes ram=base_ram();const State s=base_state(0xc836);go(ram,s,0xc882);put(ram,0x10fd8e,1,1);go(ram,s,0xc83e);put(ram,0x10fd8e,1,0xff);go(ram,s,0xc83e);}
 {const Bytes ram=base_ram();State s=base_state(0xc83e);const Out o=go(ram,s,0x49a1a);called(o,s,0xc846);assert(o.s.d[0]==0xffffffffU);}
 {const Bytes ram=base_ram();State s=base_state(0xc846);Out o=go(ram,s,0xc4cc);called(o,s,0xc84a);s.pc=0xc84a;o=go(ram,s,0xcaf0);called(o,s,0xc84e);s.pc=0xc84e;o=go(ram,s,0x47570);called(o,s,0xc854);}
 {const Bytes ram=base_ram();State s=base_state(0xc854);s.d[0]=0x77770000U;const Out o=go(ram,s,0x4823a);called(o,s,0xc85e);assert(o.s.d[0]==0x77770008U);}
 {const Bytes ram=base_ram();const State s=base_state(0xc85e);const Out o=go(ram,s,0x2a28);called(o,s,0xc86e);assert(o.s.a[0]==0x100b30&&o.s.a[1]==0x477e4);}
 {Bytes ram=base_ram();const State s=base_state(0xc86e);const Out o=go(ram,s,0xc874);assert(get(o.ram,NODE,4)==0xc874);}
 {const Bytes ram=base_ram();const State s=base_state(0xc874);const Out o=go(ram,s,0x289e);called(o,s,0xc87e);assert(o.s.a[0]==0x100b30);}
 // c87e: BCS on the C returned by 289e: Set -> c988 (tail), Clear -> c882; the C is kept (FLOW).
 {const Bytes ram=base_ram();State s=base_state(0xc87e);s.carry=ms5::AnimationCarrySet;go(ram,s,0xc988);s.carry=ms5::AnimationCarryClear;go(ram,s,0xc882);}
 {const Bytes ram=base_ram();State s=base_state(0xc882);Out o=go(ram,s,0xc4cc);called(o,s,0xc886);s.pc=0xc886;o=go(ram,s,0xcaf0);called(o,s,0xc88a);s.pc=0xc88a;o=go(ram,s,0x47570);called(o,s,0xc890);
  s.pc=0xc890;o=go(ram,s,0xc2fa);called(o,s,0xc896);}
 {Bytes ram=base_ram();const State s=base_state(0xc896);const Out o=go(ram,s,0xc89c);assert(get(o.ram,NODE,4)==0xc89c);}
 {Bytes ram=base_ram();const State s=base_state(0xc89c);go(ram,s,0xc988);put(ram,NODE+0x62,1,1);go(ram,s,0xc8a4);put(ram,NODE+0x62,1,0xff);go(ram,s,0xc8a4);}
 {Bytes ram=base_ram();const State s=base_state(0xc8a4);const Out o=go(ram,s,0xc8aa);assert(get(o.ram,NODE,4)==0xc8aa);}
}

// ---- next stage c8aa c8b0 c8b4 c8b8 c8c4 c8ca c8ce c8e2 c8e8 c8f0 c906 c90c c916 c91a c91e c922 c926 c936 c940 c948 c952 c95c c964 c968 c972 c97a c97e c982
void end_path(){
 {const Bytes ram=base_ram();const State s=base_state(0xc8aa);const Out o=go(ram,s,0x9060);called(o,s,0xc8b0);}
 {const Bytes ram=base_ram();State s=base_state(0xc8b0);Out o=go(ram,s,0xc4cc);called(o,s,0xc8b4);s.pc=0xc8b4;o=go(ram,s,0xcaf0);called(o,s,0xc8b8);}
 {Bytes ram=base_ram();put(ram,NODE+0x7c,2,0x1111);const State s=base_state(0xc8b8);const Out o=go(ram,s,0xe7bf4);called(o,s,0xc8c4);assert(get(o.ram,NODE+0x7c,2)==0x30ff);}
 {const Bytes ram=base_ram();State s=base_state(0xc8c4);Out o=go(ram,s,0x4e1cc);called(o,s,0xc8ca);s.pc=0xc8ca;o=go(ram,s,0xca48);called(o,s,0xc8ce);}
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,3);State s=base_state(0xc8ce);const Out o=go(ram,s,0x28ae);called(o,s,0xc8e2);assert(get(o.ram,NODE+0x62,1)==0&&o.s.a[0]==0xde660&&(o.s.d[0]&0xffffU)==0);}
 {Bytes ram=base_ram();const State s=base_state(0xc8e2);const Out o=go(ram,s,0xc8e8);assert(get(o.ram,NODE,4)==0xc8e8);}
 {Bytes ram=base_ram();const State s=base_state(0xc8e8);go(ram,s,0xc988);put(ram,NODE+0x62,1,1);go(ram,s,0xc8f0);}
 {Bytes ram=base_ram();put(ram,NODE+0x7c,2,0x1111);const State s=base_state(0xc8f0);const Out o=go(ram,s,0x2a28);called(o,s,0xc906);
  assert(get(o.ram,NODE+0x7c,2)==0x9ff&&o.s.a[0]==0x100b30&&o.s.a[1]==0x477e4);}
 {Bytes ram=base_ram();const State s=base_state(0xc906);const Out o=go(ram,s,0xc90c);assert(get(o.ram,NODE,4)==0xc90c);}
 {const Bytes ram=base_ram();const State s=base_state(0xc90c);const Out o=go(ram,s,0x289e);called(o,s,0xc916);assert(o.s.a[0]==0x100b30);}
 {const Bytes ram=base_ram();State s=base_state(0xc916);s.carry=ms5::AnimationCarrySet;go(ram,s,0xc988);s.carry=ms5::AnimationCarryClear;go(ram,s,0xc91a);}
 {const Bytes ram=base_ram();State s=base_state(0xc91a);Out o=go(ram,s,0xc4cc);called(o,s,0xc91e);s.pc=0xc91e;o=go(ram,s,0xcaf0);called(o,s,0xc922);s.pc=0xc922;o=go(ram,s,0xca76);called(o,s,0xc926);}
 {const Bytes ram=base_ram();const State s=base_state(0xc926);const Out o=go(ram,s,0x28ae);called(o,s,0xc936);assert(o.s.a[0]==0xe66aa&&(o.s.d[0]&0xffffU)==0);}
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,5);const State s=base_state(0xc936);const Out o=go(ram,s,0xc940);assert(get(o.ram,NODE+0x62,1)==0&&get(o.ram,NODE,4)==0xc940);}
 // c940: BYTE 62(A6) != 0 -> the BIOS system return c982, else c948.
 {Bytes ram=base_ram();const State s=base_state(0xc940);go(ram,s,0xc948);put(ram,NODE+0x62,1,1);go(ram,s,0xc982);}
 // c948: BYTE 10fd82 == 0 -> c97e; c952: BTST #0 of BYTE 104cb5 clear -> c968; c968: BTST #2 clear -> c97e.
 {Bytes ram=base_ram();const State s=base_state(0xc948);go(ram,s,0xc97e);put(ram,0x10fd82,1,1);go(ram,s,0xc952);}
 {Bytes ram=base_ram();const State s=base_state(0xc952);go(ram,s,0xc968);put(ram,0x104cb5,1,0xfe);go(ram,s,0xc968);put(ram,0x104cb5,1,1);go(ram,s,0xc95c);put(ram,0x104cb5,1,0xff);go(ram,s,0xc95c);}
 {Bytes ram=base_ram();const State s=base_state(0xc968);go(ram,s,0xc97e);put(ram,0x104cb5,1,0xfb);go(ram,s,0xc97e);put(ram,0x104cb5,1,4);go(ram,s,0xc972);put(ram,0x104cb5,1,0xff);go(ram,s,0xc972);}
 {const Bytes ram=base_ram();State s=base_state(0xc95c);s.d[0]=0x12345678U;const Out o=go(ram,s,0x4a974);called(o,s,0xc964);assert(o.s.d[0]==0);}
 {const Bytes ram=base_ram();State s=base_state(0xc972);s.d[0]=0x12345678U;const Out o=go(ram,s,0x4a974);called(o,s,0xc97a);assert(o.s.d[0]==1);}
 // c964 / c97a: BNE on the Z of the TST.B (A0) that ended 4a974, recomputed from BYTE (A0): non-zero -> the BIOS system return c982, zero -> c968 / c97e.
 const std::uint32_t sources[4]={0x10fdb0,0x10fdb1,0x100004,0x100005};
 for(unsigned int k=0;k<4;++k)for(unsigned int v=0;v<4;++v){
  const std::uint32_t values[4]={0,1,0x80,0xff};Bytes ram=base_ram();put(ram,sources[k],1,values[v]);State s=base_state(0xc964);s.a[0]=sources[k];
  go(ram,s,values[v]!=0?0xc982U:0xc968U);s.pc=0xc97a;go(ram,s,values[v]!=0?0xc982U:0xc97eU);}
 {const Bytes ram=base_ram();const State s=base_state(0xc97e);go(ram,s,0xc988);}
 {const Bytes ram=base_ram();const State s=base_state(0xc982);const Out o=go(ram,s,BIOS_RETURN);assert(o.s.a[7]==SP);}
}

// ---- game initialisation 4755e 47566 4756e 47570 47582 47584 4758a, e62ec e62f2 e62fc e6302, 4823a 48242 48244
void game_initialisation(){
 {const Bytes ram=base_ram();State s=base_state(0x4755e);s.d[0]=0x99;const Out o=go(ram,s,0xe62ec);called(o,s,0x47566);assert(o.s.d[0]==0);}
 {const Bytes ram=base_ram();State s=base_state(0x47566);const Out o=go(ram,s,0xe62ec);called(o,s,0x4756e);assert(o.s.d[0]==1);}
 {const Bytes ram=base_ram();const State s=base_state(0x4756e);const Out o=go(ram,s,RET);assert(o.s.a[7]==SP+4);}
 {Bytes ram=base_ram();put(ram,0x108000+0x5683,1,7);put(ram,0x108000+0x5694,1,8);put(ram,0x108000+0x569c,1,9);const State s=base_state(0x47570);const Out o=go(ram,s,0x100e);called(o,s,0x47582);
  assert(get(o.ram,0x10d683,1)==0&&get(o.ram,0x10d694,1)==0&&get(o.ram,0x10d69c,1)==0);}
 {const Bytes ram=base_ram();const State s=base_state(0x47582);const Out o=go(ram,s,0x4755e);called(o,s,0x47584);}
 {const Bytes ram=base_ram();State s=base_state(0x47584);s.d[0]=0x12345678U;const Out o=go(ram,s,0x4823a);called(o,s,0x4758a);assert(o.s.d[0]==0);}
 {const Bytes ram=base_ram();State s=base_state(0x4758a);const Out o=go(ram,s,0xe8a1c);called(o,s,0x47594);assert(o.s.a[0]==0);}
 // e62ec: TST.B D0 (the low byte only) selects 10de14 (zero) or 10de1c; e6302 clears the LONG at (A0).
 {const Bytes ram=base_ram();State s=base_state(0xe62ec);s.d[0]=0x1234ff00U;go(ram,s,0xe62f2);s.d[0]=0xff01U;go(ram,s,0xe62fc);s.d[0]=0x80;go(ram,s,0xe62fc);}
 {const Bytes ram=base_ram();const State s=base_state(0xe62f2);const Out o=go(ram,s,0xe6302);assert(o.s.a[0]==0x10de14);}
 {const Bytes ram=base_ram();const State s=base_state(0xe62fc);const Out o=go(ram,s,0xe6302);assert(o.s.a[0]==0x10de1c);}
 {Bytes ram=base_ram();put(ram,0x10de14,4,0xffffffffU);put(ram,0x10de18,4,0x5a5a5a5aU);State s=base_state(0xe6302);s.a[0]=0x10de14;const Out o=go(ram,s,RET);
  assert(get(o.ram,0x10de14,4)==0&&get(o.ram,0x10de18,4)==0x5a5a5a5aU&&o.s.a[7]==SP+4);one(ram,o.ram,0x10de14,0x10de18);}
 // 4823a: CMPI.W #13,D0; BCS -> 48244 (unsigned word below 0x13), else 48242 clears D0; 48244 stores BYTE 10d680 := D0.B and BYTE 10d681 := 0.
 {const Bytes ram=base_ram();State s=base_state(0x4823a);const std::uint32_t d0s[7]={0,0x12,0x13,0x14,0xffff,0x10005,0x10013};
  for(unsigned int k=0;k<7;++k){s.d[0]=d0s[k];go(ram,s,(d0s[k]&0xffffU)<0x13U?0x48244U:0x48242U);}}
 {const Bytes ram=base_ram();State s=base_state(0x48242);s.d[0]=0x12345678U;const Out o=go(ram,s,0x48244);assert(o.s.d[0]==0);}
 {Bytes ram=base_ram();put(ram,0x10d681,1,0x33);State s=base_state(0x48244);s.d[0]=0x123456a5U;const Out o=go(ram,s,RET);
  assert(get(o.ram,0x10d680,1)==0xa5&&get(o.ram,0x10d681,1)==0&&o.s.a[7]==SP+4);one(ram,o.ram,0x10d680,0x10d682);}
}

// ---- RNG table 49a1a 49a26 49a34 49a3e 49a50
void random_table(){
 {const Bytes ram=base_ram();State s=base_state(0x49a1a);s.a[5]=0x1234;s.d[0]=0x10000;go(ram,s,0x49a34);s.d[0]=0xabcd0000U;const Out o=go(ram,s,0x49a34);assert(o.s.a[5]==A5);
  s.d[0]=0x0001;const Out p=go(ram,s,0x49a26);assert(p.s.a[5]==A5);}
 // 49a26: WORD 10f02c += 1 (wrapping), D0.W := the new value.
 {Bytes ram=base_ram();put(ram,0x10f02c,2,0xffff);State s=base_state(0x49a26);s.d[0]=0xdddd0007U;const Out o=go(ram,s,0x49a34);assert(get(o.ram,0x10f02c,2)==0&&o.s.d[0]==0xdddd0000U);
  put(ram,0x10f02c,2,0x1234);const Out p=go(ram,s,0x49a34);assert(get(p.ram,0x10f02c,2)==0x1235&&p.s.d[0]==0xdddd1235U);one(ram,p.ram,0x10f02c,0x10f02e);}
 // 49a34: A0 := A5 + 56b4, D7.W := 36, D1.W := D0.W (the upper words kept).
 {const Bytes ram=base_ram();State s=base_state(0x49a34);s.d[0]=0xaaaa1357U;s.d[1]=0xbbbb0000U;s.d[7]=0xcccc0000U;const Out o=go(ram,s,0x49a3e);
  assert(o.s.a[0]==0x10d6b4&&o.s.d[7]==0xcccc0036U&&o.s.d[1]==0xbbbb1357U);}
 // 49a3e: ADDI.W #7925,D1; ADD.W D0,D1; MULU.W D1,D1; LSR.L #8,D1; EXG D1,D0; MOVE.W D0,(A0)+; DBRA D7 (a self loop: D7.W = 1 runs it twice; the upper words follow the EXG).
 {const Bytes ram=base_ram();State s=base_state(0x49a3e);s.d[0]=0x00001357U;s.d[1]=0x0000d00dU;s.d[7]=0x70001;s.a[0]=0x10d6b4;const Out o=go(ram,s,0x49a50);
  std::uint32_t d0=s.d[0],d1=s.d[1];std::uint32_t words[2];
  for(unsigned int i=0;i<2;++i){d1=(d1&0xffff0000U)|((d1+0x7925U)&0xffffU);d1=(d1&0xffff0000U)|((d1+d0)&0xffffU);d1=(d1&0xffffU)*(d1&0xffffU);d1>>=8;
   const std::uint32_t t=d1;d1=d0;d0=t;words[i]=d0&0xffffU;}
  assert(o.s.d[0]==d0&&o.s.d[1]==d1&&get(o.ram,0x10d6b4,2)==words[0]&&get(o.ram,0x10d6b6,2)==words[1]&&o.s.a[0]==0x10d6b8&&o.s.d[7]==0x7ffffU);one(ram,o.ram,0x10d6b4,0x10d6b8);
  State t=base_state(0x49a3e);t.d[0]=0xffffffffU;t.d[1]=0xffffffffU;t.d[7]=0x10000;t.a[0]=0x10d6b4;const Out q=go(ram,t,0x49a50);
  const std::uint32_t w2=(0xffffU+0x7925U+0xffffU)&0xffffU;const std::uint32_t sh2=((w2*w2)>>8);assert(q.s.d[0]==sh2&&q.s.d[1]==0xffffffffU&&q.s.d[7]==0x1ffffU);}
 // 49a50: A0 -= 2, LONG 5722(A5) := A0, RTS. The full table through 49a34 .. 49a50 is compared against the original in the native chains (chain-rng).
 {Bytes ram=base_ram();State s=base_state(0x49a50);s.a[0]=0x10d6e0;const Out o=go(ram,s,RET);
  assert(o.s.a[0]==0x10d6de&&get(o.ram,0x10d722,4)==0x10d6de&&o.s.a[7]==SP+4);one(ram,o.ram,0x10d722,0x10d726);}
 // The complete 55-WORD table from 49a1a with D0.W = 0 (49a34 directly): 55 words, LONG 105722 = the address of the last word, D7.W = ffff.
 {Bytes ram=base_ram();put(ram,0x10f02c,2,0x00ff);State s=base_state(0x49a1a);s.d[0]=0;const Out o=go(ram,s,RET);
  assert(o.s.a[0]==0x10d6b4+2*54&&get(o.ram,0x10d722,4)==0x10d6b4+2*54&&get(o.ram,0x10f02c,2)==0x00ff&&o.s.d[7]==0x8888ffffU);
  std::uint32_t d0=0,d1=(s.d[1]&0xffff0000U);
  for(unsigned int i=0;i<55;++i){d1=(d1&0xffff0000U)|((d1+0x7925U)&0xffffU);d1=(d1&0xffff0000U)|((d1+d0)&0xffffU);d1=(d1&0xffffU)*(d1&0xffffU);d1>>=8;
   const std::uint32_t t=d1;d1=d0;d0=t;assert(get(o.ram,0x10d6b4+2*i,2)==(d0&0xffffU));}
  assert(o.s.d[0]==d0&&o.s.d[1]==d1);}
 // D0.W != 0: WORD 10f02c is incremented first and its value seeds the table.
 {Bytes ram=base_ram();put(ram,0x10f02c,2,0x1234);State s=base_state(0x49a1a);s.d[0]=0xffff;const Out o=go(ram,s,RET);assert(get(o.ram,0x10f02c,2)==0x1235);}
}

// ---- 4e1cc 4e1f8 4e20e
void node_setup(){
 {Bytes ram=base_ram();for(std::uint32_t a=0x10dd1e;a<0x10dd2c;++a)put(ram,a,1,0x66);const State s=base_state(0x4e1cc);const Out o=go(ram,s,0x2a28);called(o,s,0x4e1f8);
  assert(get(o.ram,0x10dd1e,4)==0&&get(o.ram,0x10dd2a,1)==0xff&&get(o.ram,0x10dd2b,1)==0xff&&get(o.ram,0x10dd22,1)==0x66&&o.s.a[0]==0x1009a8&&o.s.a[1]==0x4e68e);}
 {Bytes ram=base_ram();State s=base_state(0x4e1f8);s.a[0]=0x100c00;put(ram,0x100c76,2,0x1111);const Out o=go(ram,s,0x2a28);called(o,s,0x4e20e);
  assert(get(o.ram,0x100c76,2)==0&&o.s.a[0]==0x100a6c&&o.s.a[1]==0x4e68e);}
 {Bytes ram=base_ram();State s=base_state(0x4e20e);s.a[0]=0x100c00;const Out o=go(ram,s,RET);assert(get(o.ram,0x100c76,2)==1&&o.s.a[7]==SP+4);one(ram,o.ram,0x100c76,0x100c78);}
}

// ---- child b300 b306 b30c b31a b326 b330 b33e b344 b34a b350 b360
void child_menu(){
 {const Bytes ram=base_ram();const State s=base_state(0xb300);const Out o=go(ram,s,0x3d3a);called(o,s,0xb306);}
 {const Bytes ram=base_ram();const State s=base_state(0xb306);const Out o=go(ram,s,0xde424);called(o,s,0xb30c);}
 {const Bytes ram=base_ram();State s=base_state(0xb30c);s.d[0]=0x99999999U;s.d[1]=0x88888888U;const Out o=go(ram,s,0xa29c);called(o,s,0xb31a);assert(o.s.a[0]==0xa810&&o.s.d[0]==3&&o.s.d[1]==4);}
 {const Bytes ram=base_ram();const State s=base_state(0xb31a);const Out o=go(ram,s,0xa2b8);called(o,s,0xb326);assert(o.s.a[0]==0xe84c8);}
 {const Bytes ram=base_ram();State s=base_state(0xb326);s.d[0]=0x12340000U;const Out o=go(ram,s,0xddf9a);called(o,s,0xb330);assert(o.s.d[0]==0x12347095U);}
 {const Bytes ram=base_ram();const State s=base_state(0xb330);const Out o=go(ram,s,0x8c16);called(o,s,0xb33e);assert(o.s.d[0]==0&&o.s.d[1]==0&&o.s.d[2]==0&&o.s.d[3]==0&&o.s.d[4]==s.d[4]);}
 {Bytes ram=base_ram();const State s=base_state(0xb33e);const Out o=go(ram,s,0xb344);assert(get(o.ram,NODE,4)==0xb344);one(ram,o.ram,NODE,NODE+4);}
 {const Bytes ram=base_ram();const State s=base_state(0xb344);const Out o=go(ram,s,0xa370);called(o,s,0xb34a);}
 // b34a: TST.B D0 (the low byte only): zero -> RTS b360, else b350 (parent byte 62 := 3, then JMP 2a00, the self delete).
 {const Bytes ram=base_ram();State s=base_state(0xb34a);s.d[0]=0x12345600U;go(ram,s,0xb360);s.d[0]=0x12345601U;go(ram,s,0xb350);s.d[0]=0xff;go(ram,s,0xb350);}
 {Bytes ram=base_ram();put(ram,NODE+0xc,4,0x100a40);put(ram,0x100aa2,1,0x77);const State s=base_state(0xb350);const Out o=go(ram,s,0x2a00);
  assert(get(o.ram,0x100aa2,1)==3&&o.s.a[0]==0x100a40&&o.s.a[7]==SP);one(ram,o.ram,0x100aa2,0x100aa3);}
 {const Bytes ram=base_ram();const State s=base_state(0xb360);const Out o=go(ram,s,RET);assert(o.s.a[7]==SP+4);}
}

// ---- menu item handlers a856 .. a8ce and the common a75a a760 a76a
void handlers(){
 const std::uint32_t entries[4]={0xa856,0xa876,0xa896,0xa8bc};const std::uint32_t after[4]={0xa85a,0xa87a,0xa89a,0xa8c0};
 for(unsigned int k=0;k<4;++k){const Bytes ram=base_ram();const State s=base_state(entries[k]);const Out o=go(ram,s,0xa73e);called(o,s,after[k]);}
 // The D0 tests: 3 -> the action, 2 -> the action, anything else -> the item's RTS (a8bc: only 3 acts).
 const std::uint32_t d0s[5]={3,2,0,1,0x10003};
 for(unsigned int k=0;k<5;++k){
  const Bytes ram=base_ram();State s=base_state(0xa85a);s.d[0]=d0s[k];const bool three=(d0s[k]&0xffffU)==3U,two=(d0s[k]&0xffffU)==2U;
  go(ram,s,three?0xa868U:0xa860U);
  s.pc=0xa860;go(ram,s,two?0xa868U:0xa874U);
  s.pc=0xa87a;go(ram,s,three?0xa888U:0xa880U);s.pc=0xa880;go(ram,s,two?0xa888U:0xa894U);
  s.pc=0xa89a;go(ram,s,three?0xa8a8U:0xa8a0U);s.pc=0xa8a0;go(ram,s,two?0xa8a8U:0xa8baU);
  s.pc=0xa8c0;go(ram,s,three?0xa8c8U:0xa8ceU);}
 {const Bytes ram=base_ram();const State s=base_state(0xa868);const Out o=go(ram,s,0xa75a);called(o,s,0xa86c);}
 {const Bytes ram=base_ram();const State s=base_state(0xa888);const Out o=go(ram,s,0xa75a);called(o,s,0xa88c);}
 // a86c: LEA a8f8(PC),A0; JMP a71a(PC) (no push); a88c: LEA a952(PC),A0; JSR a71a(PC); a8a8: JSR 9f36; a8ae: ADDQ.B #4,D0; SUBQ.B #2,D1; LEA aa24(PC),A0; JMP a71a(PC).
 {const Bytes ram=base_ram();const State s=base_state(0xa86c);const Out o=go(ram,s,0xa71a);assert(o.s.a[0]==0xa8f8&&o.s.a[7]==SP);}
 {const Bytes ram=base_ram();const State s=base_state(0xa88c);const Out o=go(ram,s,0xa71a);called(o,s,0xa894);assert(o.s.a[0]==0xa952);}
 {const Bytes ram=base_ram();const State s=base_state(0xa8a8);const Out o=go(ram,s,0x9f36);called(o,s,0xa8ae);}
 {const Bytes ram=base_ram();State s=base_state(0xa8ae);s.d[0]=0x123456fdU;s.d[1]=0x89abcd01U;const Out o=go(ram,s,0xa71a);
  assert(o.s.d[0]==0x12345601U&&o.s.d[1]==0x89abcdffU&&o.s.a[0]==0xaa24&&o.s.a[7]==SP);}
 {const Bytes ram=base_ram();const State s=base_state(0xa8c8);const Out o=go(ram,s,BIOS_RETURN);assert(o.s.a[7]==SP);}
 for(unsigned int k=0;k<4;++k){const std::uint32_t rts[4]={0xa874,0xa894,0xa8ba,0xa8ce};const Bytes ram=base_ram();const State s=base_state(rts[k]);const Out o=go(ram,s,RET);assert(o.s.a[7]==SP+4);}
 // a75a: JSR 9f36; a760: push D1.W then D0.W, JSR 38e8; a76a: ADD.W (A7)+,D0; MOVE.W (A7)+,D1; RTS.
 {const Bytes ram=base_ram();const State s=base_state(0xa75a);const Out o=go(ram,s,0x9f36);called(o,s,0xa760);}
 {const Bytes ram=base_ram();State s=base_state(0xa760);s.d[0]=0x1111aaaaU;s.d[1]=0x2222bbbbU;const Out o=go(ram,s,0x38e8);
  assert(o.s.a[7]==SP-8&&get(o.ram,SP-8,4)==0xa76a&&get(o.ram,SP-4,2)==0xaaaa&&get(o.ram,SP-2,2)==0xbbbb);}
 {Bytes ram=base_ram();put(ram,SP-4,2,0x0003);put(ram,SP-2,2,0x4321);put(ram,SP,4,RET);State s=base_state(0xa76a);s.a[7]=SP-4;s.d[0]=0xffff0001U;s.d[1]=0x7777ffffU;const Out o=go(ram,s,RET);
  assert(o.s.d[0]==0xffff0004U&&o.s.d[1]==0x77774321U&&o.s.a[7]==SP+4);}
 {Bytes ram=base_ram();put(ram,SP-4,2,0xffff);put(ram,SP-2,2,0x8000);State s=base_state(0xa76a);s.a[7]=SP-4;s.d[0]=0x00000001U;const Out o=go(ram,s,RET);assert(o.s.d[0]==0x00000000U&&(o.s.d[1]&0xffffU)==0x8000U);}
}

// ---- checked errors and preservation
void errors(){
 const Bytes ram=base_ram();
 // Interior even PCs of the 16 ranges are checked errors of the unit; odd PCs fail before dispatch.
 for(unsigned int r=0;r<RANGE_COUNT;++r){
  for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2)if(!is_start(pc))fail(ram,base_state(pc),RET,"unsupported animation controller c2 PC");
  fail(ram,base_state(RANGES[r][0]+1),RET,"unaligned animation machine PC");fail(ram,base_state(RANGES[r][1]-1),RET,"unaligned animation machine PC");}
 // The neighbours outside the unit are not routed here.  Review 0264 M-3: the ROM range ends 1022 bbfa c6ce 48250 e630a b362 a770 a8d0 (code of later units) are the
 // work-RAM PCs 10fe10..10fe1e; the BIOS entries stay.
 const std::uint32_t outside[]={0x10fe10,0x10fe12,0x10fe14,0x10fe16,0x10fe18,0x10fe1a,0x10fe1c,0x10fe1e,BIOS_RETURN,BIOS_CARD};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i)fail(ram,base_state(outside[i]),RET,"unsupported animation machine PC");
 // The C consumers c87e / c916 refuse an Unknown C.
 {State s=base_state(0xc87e);s.carry=ms5::AnimationCarryUnknown;fail(ram,s,RET,"controller c2 caller requires known carry");s.pc=0xc916;fail(ram,s,RET,"controller c2 caller requires known carry");}
 // The Z consumers c964 / c97a refuse an A0 that is not one of the four credit bytes.
 const std::uint32_t bad[]={0,0x3000,0x10fdaf,0x10fdb2,0x100003,0x100006,0x10fe00,0xd00034,0xffffffffU};
 for(unsigned int i=0;i<sizeof(bad)/sizeof(bad[0]);++i){State s=base_state(0xc964);s.a[0]=bad[i];fail(ram,s,RET,"unsupported animation controller flag source");s.pc=0xc97a;fail(ram,s,RET,"unsupported animation controller flag source");}
 // ROM stores: c690 CLR.W 180.l and the recorder fill into ROM space.
 {State s=base_state(0x31ce);s.a[0]=0x100;s.d[7]=3;fail(ram,s,RET,"unsupported animation machine write device");}
 // Odd stores and a failing push after earlier writes roll everything back.
 {State s=base_state(0xc6b6);s.a[6]=NODE+1;fail(ram,s,RET,"invalid animation machine write size/alignment");}
 {State s=base_state(0xc794);s.a[6]=NODE+1;fail(ram,s,RET,"invalid animation machine write size/alignment");}
 {State s=base_state(0xe6302);s.a[0]=0x10de15;fail(ram,s,RET,"invalid animation machine write size/alignment");}
 {State s=base_state(0xc346);s.a[0]=0x100c01;fail(ram,s,RET,"invalid animation machine write size/alignment");}
 {State s=base_state(0xc8b8);s.a[7]=0x200004;fail(ram,s,RET,"program bus write requires RAM mirror units");}
 {State s=base_state(0xc2fe);s.a[7]=0x200004;fail(ram,s,RET,"program bus write requires RAM mirror units");}
 {State s=base_state(0xc4e6);s.a[0]=0x100a40;s.a[7]=0x200004;fail(ram,s,RET,"program bus write requires RAM mirror units");}
 // A read of an odd LONG address.
 {State s=base_state(0xc4d8);s.a[6]=NODE+1;fail(ram,s,RET,"program bus requires even WORD/LONG address");}
 // Zero-step: a run that starts at its stop PC executes nothing.
 {State s=base_state(0xc76a);const Out o=run(ram,s,0xc76a,ROM0);assert(o.ok&&o.ram==ram&&same_state(o.s,s)&&o.ports.empty());++checks;}
}
}
int main(){
 counters();card_request();teardown();demo_end();game_branch();restart();continue_path();end_path();game_initialisation();random_table();node_setup();child_menu();handlers();errors();
 for(unsigned int i=0;i<START_COUNT;++i){bool found=false;for(std::size_t k=0;k<reached.size();++k)if(reached[k]==STARTS[i])found=true;if(!found){std::cerr<<"block not reached: "<<std::hex<<STARTS[i]<<"\n";assert(false);}}
 std::cout<<"animation machine controller c2: "<<checks<<" checks, "<<START_COUNT<<" block starts reached\n";
 return 0;
}
