#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
#include <string>
// Controller C3a (9 block starts: c52a c530 c55a c560 c566 c56c, 8b64 8b98 8bb6) through run_animation_machine only.
// Inputs are declared fixtures: zero RAM, A5 = 108000, the controller node A6 = 1008e4, the stack at 10f000 holding the declared return
// RET, the fixture's RAM puts and registers, and synthetic typed physical bytes (not ROM data): the bank 200000 window LONGs 200004 /
// 200008 read by 8b64. Callees of other units are stops (area_clear 9056, H3 4718); c56e (C3b) is the boundary without an executor.
// Expected values follow the original instruction semantics written out in each row (the natural c52a / c560 path against the original
// ROM is checked by tools/verify_animation_machine_frame_controller.py and tools/unit_fixture_specs/d9.py).
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
typedef ms5::AnimationMachineDevice Device;
typedef std::vector<ms5::VideoPortWrite> Ports;
const std::uint32_t A5=0x108000,NODE=0x1008e4,SP=0x10f000,RET=0xff000;
unsigned int checks=0;
std::vector<ms5::PhysicalRomResource> make_rom(){
 std::vector<ms5::PhysicalRomResource> p(1);p[0].source_rom_offset=0x200004;
 const std::uint8_t b[8]={0x00,0x10,0xa0,0x00,0x00,0x10,0xa1,0x00};p[0].data.assign(b,b+8);return p;}
const std::vector<ms5::PhysicalRomResource> ROM=make_rom();
void put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes& b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
Bytes base_ram(){Bytes r(65536,0);put(r,SP,4,RET);return r;}
State base_state(std::uint32_t pc){
 State s;for(unsigned int i=0;i<8;++i){s.d[i]=0x11110000U*(i+1)+i;s.a[i]=0xa0a0a0a0U+i*0x01010101U;}
 s.a[5]=A5;s.a[6]=NODE;s.a[7]=SP;s.pc=pc;s.carry=ms5::AnimationCarrySet;return s;}
// Device with the bank 300000 selected (ff8 = 00a0, ff9 = 2000); 8b64 / 8b98 select bank 200000.
Device base_device(){Device d;d.pvc[0x1ff1]=0xa0;d.pvc[0x1ff2]=0x20;d.bank_base=0x300000;return d;}
struct Out {bool ok;Bytes ram;State s;Device d;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;};
Out run(const Bytes& ram,const State& s,const Device& d,std::uint32_t stop){
 Out o;o.ram=ram;o.s=s;o.d=d;o.reads=7;o.status=ms5::AnimationMachineWaiting;
 ms5::ProgramBusState bus;bus.physical_rom=&ROM;std::vector<ms5::FixedDataResource> w;
 o.ok=ms5::run_animation_machine(o.ram,w,bus,o.s,o.d,stop,0,o.reads,o.status,o.ports,o.error);return o;}
bool same_state(const State& a,const State& b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
Out pass(const Bytes& ram,const State& s,const Device& d,std::uint32_t stop){
 Out o=run(ram,s,d,stop);if(!o.ok)std::cerr<<"error "<<o.error<<" pc "<<std::hex<<o.s.pc<<"\n";
 assert(o.ok&&o.status==ms5::AnimationMachineReturned&&o.s.pc==stop&&o.reads==0);++checks;return o;}
void fail(const Bytes& ram,const State& s,const Device& d,std::uint32_t stop,const char* message){
 Out o=run(ram,s,d,stop);
 if(o.ok||o.error!=message)std::cerr<<"expected '"<<message<<"' got ok="<<o.ok<<" '"<<o.error<<"' pc "<<std::hex<<s.pc<<"\n";
 assert(!o.ok&&o.error==message&&o.ram==ram&&same_state(o.s,s)&&o.d.pvc==d.pvc&&o.d.bank_base==d.bank_base&&o.ports.empty()&&o.reads==7&&
  o.status==ms5::AnimationMachineWaiting);++checks;}
// Only the listed RAM bytes may differ.
void only_changed(const Bytes& a,const Bytes& b,const std::uint32_t* lo,const std::uint32_t* hi,unsigned int n){
 for(std::uint32_t i=0;i<65536;++i){bool allowed=false;for(unsigned int k=0;k<n;++k)if(0x100000U+i>=lo[k]&&0x100000U+i<hi[k])allowed=true;
  if(!allowed&&a[i]!=b[i]){std::cerr<<std::hex<<"unexpected change "<<(0x100000U+i)<<"\n";assert(false);}}}
void check_bank_ports(const Ports& p,std::size_t at){
 assert(p.size()>=at+2&&p[at].address==0x2ffff2&&p[at].size==2&&p[at].value==0x1000&&p[at+1].address==0x2ffff0&&p[at+1].size==2&&p[at+1].value==0);}
void boot_head(){
 // c52a: JSR 9056.l (stop at the area_clear entry; C Unknown after the block).
 {const Bytes ram=base_ram();const State s=base_state(0xc52a);const Out o=pass(ram,s,base_device(),0x9056);
  assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc530&&o.ports.empty()&&o.s.carry==ms5::AnimationCarryUnknown);
  for(unsigned int i=0;i<7;++i)assert(o.s.a[i]==s.a[i]);}
 // c530: CLR.W 76..7e, CLR.B 80 81 83 (+82, +84 kept), MOVE.W #0,D0, JSR 8b64 -> 8b64 (bank select, A0/A3/A4, LSL) -> BSR 4718.
 const std::uint32_t highs[5]={0x0000,0x0001,0x07ff,0x0800,0xffff};
 for(unsigned int k=0;k<5;++k){
  Bytes ram=base_ram();for(unsigned int i=0x76;i<=0x85;++i)put(ram,NODE+i,1,0xa5);put(ram,0x100010,2,0x1234);
  State s=base_state(0xc530);s.d[0]=(highs[k]<<16)|0x5678U;
  const Out o=pass(ram,s,base_device(),0x4718);
  for(unsigned int i=0x76;i<0x80;++i)assert(get(o.ram,NODE+i,1)==0);
  assert(get(o.ram,NODE+0x80,2)==0&&get(o.ram,NODE+0x82,1)==0xa5&&get(o.ram,NODE+0x83,1)==0&&get(o.ram,NODE+0x84,1)==0xa5&&get(o.ram,NODE+0x85,1)==0xa5);
  assert(get(o.ram,0x100010,2)==0&&o.d.bank_base==0x200000&&o.ports.size()==2);check_bank_ports(o.ports,0);
  // D0 = ((high << 16) | 0) << 5 (32-bit); A0 = LONG 200004 + sext(D0.W) = 10a000 (the low WORD is 0).
  assert(o.s.d[0]==((highs[k]<<21)&0xffffffffU)&&o.s.a[0]==0x10a000&&o.s.a[3]==0x10a100&&o.s.a[4]==0x107da2);
  assert(o.s.a[7]==SP-8&&get(o.ram,SP-4,4)==0xc55a&&get(o.ram,SP-8,4)==0x8b98&&o.s.a[6]==NODE&&o.s.a[5]==A5);
  const std::uint32_t lo[3]={NODE+0x76,0x100010,SP-8},hi[3]={NODE+0x84,0x100012,SP};only_changed(ram,o.ram,lo,hi,3);}
 // 8b64 directly: D0.W after LSL #5 is sign extended into A0 (0001 -> +20, 0400 -> 8000 = -8000, ffff -> ffe0 = -20, 07ff -> ffe0).
 const std::uint32_t lows[5]={0x0001,0x0400,0xffff,0x07ff,0x0000};
 const std::uint32_t a0s[5]={0x10a020,0x102000,0x109fe0,0x109fe0,0x10a000};
 for(unsigned int k=0;k<5;++k){
  const Bytes ram=base_ram();State s=base_state(0x8b64);s.d[0]=0x00020000U|lows[k];
  const Out o=pass(ram,s,base_device(),0x4718);
  assert(o.s.d[0]==(((0x00020000U|lows[k])<<5)&0xffffffffU)&&o.s.a[0]==a0s[k]&&o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0x8b98);}
 // 8b98: MOVE.W #2000,107dea; bank 200000 again; RTS to the declared return.
 {Bytes ram=base_ram();put(ram,0x107dea,2,0x1111);put(ram,0x100010,2,0x2222);const State s=base_state(0x8b98);
  const Out o=pass(ram,s,base_device(),RET);
  assert(get(o.ram,0x107dea,2)==0x2000&&get(o.ram,0x100010,2)==0&&o.ports.size()==2&&o.s.a[7]==SP+4&&o.d.bank_base==0x200000);check_bank_ports(o.ports,0);
  for(unsigned int i=0;i<8;++i)assert(o.s.d[i]==s.d[i]);
  const std::uint32_t lo[2]={0x107dea,0x100010},hi[2]={0x107dec,0x100012};only_changed(ram,o.ram,lo,hi,2);}
 // c55a: MOVE.L #c560,(A6), then c560 / 8bb6 / c566 / c56c (107dea = 2000): RTS to the declared return, D0.W = 2000.
 {Bytes ram=base_ram();put(ram,0x107dea,2,0x2000);const State s=base_state(0xc55a);const Out o=pass(ram,s,base_device(),RET);
  assert(get(o.ram,NODE,4)==0xc560&&(o.s.d[0]&0xffffU)==0x2000&&(o.s.d[0]>>16)==(s.d[0]>>16)&&o.s.a[7]==SP+4&&o.ports.empty()&&
   get(o.ram,SP-4,4)==0xc566);}
}
void boot_wait(){
 // c560 with WORD 107dea != 0: JSR 8bb6 (D0.W := 107dea), TST.W D0, BNE -> c56c RTS.
 const std::uint32_t values[4]={1,0x2000,0x8000,0xffff};
 for(unsigned int k=0;k<4;++k){
  Bytes ram=base_ram();put(ram,0x107dea,2,values[k]);const State s=base_state(0xc560);const Out o=pass(ram,s,base_device(),RET);
  assert((o.s.d[0]&0xffffU)==values[k]&&(o.s.d[0]>>16)==(s.d[0]>>16)&&o.s.a[7]==SP+4&&o.ports.empty()&&o.d.bank_base==0x300000&&
   o.s.carry==ms5::AnimationCarryUnknown);
  const std::uint32_t lo[1]={SP-4},hi[1]={SP};only_changed(ram,o.ram,lo,hi,1);
  assert(o.s.a[0]==s.a[0]);
  for(unsigned int i=1;i<8;++i)assert(o.s.d[i]==s.d[i]&&(i==7||o.s.a[i]==s.a[i]));}
 // 107dea = 0: BEQ -> c56e (C3b): a stop there succeeds, running on is the unsupported-PC boundary (rolled back).
 {Bytes ram=base_ram();put(ram,0x107dea,2,0);const State s=base_state(0xc560);
  const Out o=pass(ram,s,base_device(),0xc56e);assert((o.s.d[0]&0xffffU)==0&&o.s.a[7]==SP);
  fail(ram,s,base_device(),RET,"unsupported animation machine PC");}
 // c566 / c56c / 8bb6 entered directly.
 {const Bytes ram=base_ram();State s=base_state(0xc566);s.d[0]=0xffff0000U;Out o=pass(ram,s,base_device(),0xc56e);assert(o.s.a[7]==SP);
  s.d[0]=0x00000001U;o=pass(ram,s,base_device(),RET);assert(o.s.a[7]==SP+4);
  o=pass(ram,base_state(0xc56c),base_device(),RET);assert(o.s.a[7]==SP+4);
  Bytes r2=base_ram();put(r2,0x107dea,2,0xbeef);o=pass(r2,base_state(0x8bb6),base_device(),RET);assert((o.s.d[0]&0xffffU)==0xbeef);}
}
void errors(){
 const Bytes ram=base_ram();
 // Interior PCs of every block (even, not a block start) are checked errors of the unit.
 const std::uint32_t inner[]={0xc52c,0xc52e,0xc532,0xc534,0xc550,0xc554,0xc558,0xc55c,0xc55e,0xc562,0xc564,0xc568,0xc56a,
  0x8b66,0x8b6a,0x8b7a,0x8b80,0x8b86,0x8b8a,0x8b8e,0x8b90,0x8b94,0x8b96,0x8b9a,0x8b9e,0x8ba4,0x8bac,0x8bb4,0x8bb8,0x8bba};
 for(unsigned int i=0;i<sizeof(inner)/sizeof(inner[0]);++i)fail(ram,base_state(inner[i]),base_device(),RET,"unsupported animation controller c3 PC");
 // Odd PCs.
 fail(ram,base_state(0xc52b),base_device(),RET,"unaligned animation machine PC");
 fail(ram,base_state(0x8b65),base_device(),RET,"unaligned animation machine PC");
 // Neighbours outside the unit are not routed here (c56e: C3b; 8b62: before the helper).
 fail(ram,base_state(0xc56e),base_device(),RET,"unsupported animation machine PC");
 // Odd node A6: the c530 WORD clears fail and everything is rolled back (no port, no RAM write).
 {State s=base_state(0xc530);s.a[6]=NODE+1;fail(ram,s,base_device(),0x4718,"invalid animation machine write size/alignment");}
 // c55a with A6 outside work RAM: the LONG write fails (rolled back).
 {State s=base_state(0xc55a);s.a[6]=0x200000;fail(ram,s,base_device(),RET,"unsupported animation machine write device");}
 // A failure after the 8b64 bank select (the stack push into ROM space) rolls back the PVC writes and the bank.
 {State s=base_state(0x8b64);s.a[7]=0x200004;fail(ram,s,base_device(),0x4718,"program bus write requires RAM mirror units");}
}
}
int main(){
 boot_head();boot_wait();errors();
 std::cout<<"animation machine controller c3: "<<checks<<" checks\n";
 return 0;
}
