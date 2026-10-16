#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
#include <string>
// Controller C3 through run_animation_machine only: C3a (9 block starts: c52a c530 c55a c560 c566 c56c, 8b64 8b98 8bb6) and C3b (38 block
// starts: the boot after the wait c56e..c64c, the title c6da..c720 and the demo child allocation 4fb1a..4fb42).
// Inputs are declared fixtures: zero RAM, A5 = 108000, the controller node A6 = 1008e4, the stack at 10f000 holding the declared return
// RET, the fixture's RAM puts and registers, and synthetic typed physical bytes (not ROM data): the bank 200000 window LONGs 200004 /
// 200008 read by 8b64 and the ROM WORD 000180 read by c5b4. Callees of other units are stops (area_clear 9056, H3 4718, palette_bind
// e7bf4, C2 49a1a 47570 4823a 3162 c4cc, C1 36ba c724 c73e, ca7e ca76 28ae 3902) and so is the BIOS return c00444.
// Expected values follow the original instruction semantics written out in each row (the natural c52a / c560 path against the original
// ROM is checked by tools/verify_animation_machine_frame_controller.py and tools/unit_fixture_specs/d9.py).
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
typedef ms5::AnimationMachineDevice Device;
typedef std::vector<ms5::VideoPortWrite> Ports;
const std::uint32_t A5=0x108000,NODE=0x1008e4,SP=0x10f000,RET=0xff000;
unsigned int checks=0;
// Synthetic typed bytes: the bank window LONGs at 200004 / 200008 and, when with_180 is set, the ROM WORD at 000180 (value w180).
std::vector<ms5::PhysicalRomResource> make_rom(bool with_180,std::uint32_t w180){
 std::vector<ms5::PhysicalRomResource> p(with_180?2:1);p[0].source_rom_offset=0x200004;
 const std::uint8_t b[8]={0x00,0x10,0xa0,0x00,0x00,0x10,0xa1,0x00};p[0].data.assign(b,b+8);
 if(with_180){p[1].source_rom_offset=0x180;p[1].data.resize(2);p[1].data[0]=static_cast<std::uint8_t>(w180>>8);p[1].data[1]=static_cast<std::uint8_t>(w180);}
 return p;}
std::vector<ms5::PhysicalRomResource> ROM=make_rom(false,0);
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
 // 107dea = 0: BEQ -> c56e (C3b): a stop there succeeds, running on reaches the palette_bind call e7bf4 with c574 pushed.
 {Bytes ram=base_ram();put(ram,0x107dea,2,0);const State s=base_state(0xc560);
  Out o=pass(ram,s,base_device(),0xc56e);assert((o.s.d[0]&0xffffU)==0&&o.s.a[7]==SP);
  o=pass(ram,s,base_device(),0xe7bf4);assert((o.s.d[0]&0xffffU)==0&&o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc574);}
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
 // Neighbours outside the unit are not routed here.  Review 0264 M-3: c6ce (the "TIME" string data) and 4fb4a (after the demo child allocation) are the work-RAM PCs
 // 10fe10 / 10fe12.
 fail(ram,base_state(0x10fe10),base_device(),RET,"unsupported animation machine PC");
 fail(ram,base_state(0x10fe12),base_device(),RET,"unsupported animation machine PC");
 // Odd node A6: the c530 WORD clears fail and everything is rolled back (no port, no RAM write).
 {State s=base_state(0xc530);s.a[6]=NODE+1;fail(ram,s,base_device(),0x4718,"invalid animation machine write size/alignment");}
 // c55a with A6 outside work RAM: the LONG write fails (rolled back).
 {State s=base_state(0xc55a);s.a[6]=0x200000;fail(ram,s,base_device(),RET,"unsupported animation machine write device");}
 // A failure after the 8b64 bank select (the stack push into ROM space) rolls back the PVC writes and the bank.
 {State s=base_state(0x8b64);s.a[7]=0x200004;fail(ram,s,base_device(),0x4718,"program bus write requires RAM mirror units");}
}

// ---- C3b ------------------------------------------------------------------------------------------------------------------------------
const std::uint32_t C3B_STARTS[]={0xc56e,0xc574,0xc57c,0xc58a,0xc598,0xc59e,0xc5a6,0xc5ac,0xc5b4,0xc5be,0xc5c2,0xc5c8,0xc5ce,0xc5d6,0xc5da,0xc5ea,
 0xc5f4,0xc5fc,0xc608,0xc610,0xc61e,0xc622,0xc626,0xc62c,0xc642,0xc64c,0xc6da,0xc6de,0xc6ee,0xc6f4,0xc702,0xc718,0xc720,0x4fb1a,0x4fb22,0x4fb2c,
 0x4fb3c,0x4fb42};
const std::uint32_t C3A_STARTS[]={0xc52a,0xc530,0xc55a,0xc560,0xc566,0xc56c,0x8b64,0x8b98,0x8bb6};
bool is_start(std::uint32_t pc){
 for(unsigned int i=0;i<sizeof(C3B_STARTS)/sizeof(C3B_STARTS[0]);++i)if(C3B_STARTS[i]==pc)return true;
 for(unsigned int i=0;i<sizeof(C3A_STARTS)/sizeof(C3A_STARTS[0]);++i)if(C3A_STARTS[i]==pc)return true;
 return false;}
// Run one block with the callee/branch destination as the stop; the stack holds the pushed return and only the listed bytes changed.
Out block(const Bytes& ram,const State& s,std::uint32_t stop){return pass(ram,s,base_device(),stop);}
// D0..D7 and A0..A6 unchanged except the register index given (8 = none).
void regs_kept(const Out& o,const State& s,unsigned int skip_d,unsigned int skip_a){
 for(unsigned int i=0;i<8;++i){if(i!=skip_d&&o.s.d[i]!=s.d[i])assert(false);if(i!=skip_a&&i!=7&&o.s.a[i]!=s.a[i])assert(false);}}
void boot_after_wait(){
 // c56e / c574 / c57c: the three callee calls and the stack pushes; c574 MOVEQ #0,D0 clears all of D0; c57c MOVE.B #3,10f004.
 {const Bytes ram=base_ram();const State s=base_state(0xc56e);const Out o=block(ram,s,0xe7bf4);
  assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc574&&o.ports.empty());regs_kept(o,s,8,8);}
 {const Bytes ram=base_ram();const State s=base_state(0xc574);const Out o=block(ram,s,0x49a1a);
  assert(o.s.d[0]==0&&o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc57c);regs_kept(o,s,0,8);}
 {Bytes ram=base_ram();put(ram,0x10f004,1,0x77);put(ram,0x10f005,1,0x66);const State s=base_state(0xc57c);const Out o=block(ram,s,0x47570);
  assert(get(o.ram,0x10f004,1)==3&&get(o.ram,0x10f005,1)==0x66&&o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc58a);regs_kept(o,s,8,8);
  const std::uint32_t lo[2]={0x10f004,SP-4},hi[2]={0x10f005,SP};only_changed(ram,o.ram,lo,hi,2);}
 // c58a: BYTE 10fdae into D0.B (the rest of D0 kept); 0 -> c598, else c59e; then c59e 1 -> c5a6, else c5ac; c5ac 3 -> c6da, else c5b4.
 const std::uint32_t requests[7]={0,1,2,3,4,0x80,0xff};
 for(unsigned int k=0;k<7;++k){
  Bytes ram=base_ram();put(ram,0x10fdae,1,requests[k]);const State s=base_state(0xc58a);
  Out o=block(ram,s,requests[k]==0?0xc598:0xc59e);
  assert(o.s.d[0]==((s.d[0]&0xffffff00U)|requests[k])&&o.s.a[7]==SP&&o.ram==ram);regs_kept(o,s,0,8);
  const std::uint32_t dest=requests[k]<2?0xc00444:(requests[k]==3?0xc6da:0xc5b4);
  block(ram,s,dest);
  // The compare uses D0.B only: the same D0 upper bytes for c59e / c5ac entered directly.
  State t=base_state(0xc59e);t.d[0]=0xabcdef00U|requests[k];o=block(ram,t,requests[k]==1?0xc5a6:0xc5ac);assert(o.s.d[0]==t.d[0]);
  t.pc=0xc5ac;o=block(ram,t,requests[k]==3?0xc6da:0xc5b4);assert(o.s.d[0]==t.d[0]);}
 // c598 / c5a6: JMP c00444.l is a stop (no executor there); running on is the checked unsupported-PC error with the state preserved.
 {const Bytes ram=base_ram();const unsigned int pcs[2]={0xc598,0xc5a6};
  for(unsigned int i=0;i<2;++i){const State s=base_state(pcs[i]);const Out o=block(ram,s,0xc00444);assert(o.s.a[7]==SP&&o.ram==ram);
   fail(ram,s,base_device(),RET,"unsupported animation machine PC");}}
 // c5b4: TST.W 180.l (live bus; the typed ROM WORD): 0 -> c5be, any bit -> c610.
 const std::uint32_t w180[5]={0,1,0x0100,0x8000,0xffff};
 for(unsigned int k=0;k<5;++k){
  ROM=make_rom(true,w180[k]);const Bytes ram=base_ram();const State s=base_state(0xc5b4);
  const Out o=block(ram,s,w180[k]==0?0xc5be:0xc610);assert(o.ram==ram&&o.s.a[7]==SP&&o.s.d[0]==s.d[0]);}
 // The full chain from c58a with the typed ROM WORD 0: request 2 / 4 / ff reach the demo intro c5be, 3 the title c6da.
 ROM=make_rom(true,0);
 for(unsigned int k=0;k<7;++k){Bytes ram=base_ram();put(ram,0x10fdae,1,requests[k]);
  if(requests[k]>=2&&requests[k]!=3){const Out o=block(ram,base_state(0xc58a),0xc5be);assert(o.s.a[7]==SP);}}
 ROM=make_rom(true,0x0400);
 {Bytes ram=base_ram();put(ram,0x10fdae,1,2);const Out o=block(ram,base_state(0xc58a),0xc610);assert(o.s.a[7]==SP);}
 // Without the typed ROM WORD the live read is a checked error and everything is rolled back.
 ROM=make_rom(false,0);
 fail(base_ram(),base_state(0xc5b4),base_device(),RET,"missing or ambiguous physical program bus ROM byte");
 ROM=make_rom(true,0);
}
void demo_intro(){
 // c5be / c5c2: calls (ca7e, 4fb1a); c5c8: MOVE.L #c5ce,(A6) and continue at c5ce.
 {const Bytes ram=base_ram();const State s=base_state(0xc5be);const Out o=block(ram,s,0xca7e);assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc5c2);regs_kept(o,s,8,8);}
 {const Bytes ram=base_ram();const State s=base_state(0xc5c2);const Out o=block(ram,s,0x4fb1a);assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc5c8);regs_kept(o,s,8,8);}
 {Bytes ram=base_ram();put(ram,NODE,4,0x11223344);const State s=base_state(0xc5c8);const Out o=block(ram,s,0xc5ce);
  assert(get(o.ram,NODE,4)==0xc5ce&&o.s.a[7]==SP);regs_kept(o,s,8,8);const std::uint32_t lo[1]={NODE},hi[1]={NODE+4};only_changed(ram,o.ram,lo,hi,1);}
 // c5ce: BYTE 62(A6): 0 -> c73e (the C1 wait tail, no write), else c5d6.
 const std::uint32_t flags[5]={0,1,0x80,0xfe,0xff};
 for(unsigned int k=0;k<5;++k){
  Bytes ram=base_ram();put(ram,NODE+0x62,1,flags[k]);put(ram,NODE+0x63,1,0x55);const State s=base_state(0xc5ce);
  const Out o=block(ram,s,flags[k]==0?0xc73e:0xc5d6);assert(o.ram==ram&&o.s.a[7]==SP);regs_kept(o,s,8,8);
  // c5f4 has the same test with the targets c724 / c5fc.
  State t=base_state(0xc5f4);const Out q=block(ram,t,flags[k]==0?0xc724:0xc5fc);assert(q.ram==ram&&q.s.a[7]==SP);}
 // c5d6: JSR ca76; c5da: A0 = de024, D0.W = 0 (upper kept), JSR 28ae.
 {const Bytes ram=base_ram();const State s=base_state(0xc5d6);const Out o=block(ram,s,0xca76);assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc5da);regs_kept(o,s,8,8);}
 {const Bytes ram=base_ram();const State s=base_state(0xc5da);const Out o=block(ram,s,0x28ae);
  assert(o.s.a[0]==0xde024&&(o.s.d[0]&0xffffU)==0&&(o.s.d[0]>>16)==(s.d[0]>>16)&&o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc5ea);regs_kept(o,s,0,0);}
 // c5ea: CLR.B 62(A6); MOVE.L #c5f4,(A6).
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,0xff);put(ram,NODE+0x63,1,0x44);const State s=base_state(0xc5ea);const Out o=block(ram,s,0xc5f4);
  assert(get(o.ram,NODE+0x62,1)==0&&get(o.ram,NODE+0x63,1)==0x44&&get(o.ram,NODE,4)==0xc5f4);
  const std::uint32_t lo[2]={NODE,NODE+0x62},hi[2]={NODE+4,NODE+0x63};only_changed(ram,o.ram,lo,hi,2);}
 // c5fc: MOVE.W #96,76(A6); MOVE.L #c608,(A6).
 {Bytes ram=base_ram();put(ram,NODE+0x76,2,0x1234);const State s=base_state(0xc5fc);const Out o=block(ram,s,0xc608);
  assert(get(o.ram,NODE+0x76,2)==0x96&&get(o.ram,NODE,4)==0xc608);const std::uint32_t lo[2]={NODE,NODE+0x76},hi[2]={NODE+4,NODE+0x78};only_changed(ram,o.ram,lo,hi,2);}
 // c608: SUBQ.W #1,76(A6) (WORD wrap): result 0 -> c610, else c724 (count 0 -> ffff).
 const std::uint32_t counts[7]={1,2,0x96,0x8000,0,0xffff,0x0100};
 for(unsigned int k=0;k<7;++k){
  Bytes ram=base_ram();put(ram,NODE+0x76,2,counts[k]);put(ram,NODE+0x78,2,0x7777);const State s=base_state(0xc608);
  const std::uint32_t next=(counts[k]-1U)&0xffffU;const Out o=block(ram,s,next==0?0xc610:0xc724);
  assert(get(o.ram,NODE+0x76,2)==next&&get(o.ram,NODE+0x78,2)==0x7777&&o.s.a[7]==SP);regs_kept(o,s,8,8);
  const std::uint32_t lo[1]={NODE+0x76},hi[1]={NODE+0x78};only_changed(ram,o.ram,lo,hi,1);}
 // The whole intro wait through the blocks: c5fc -> c608 (150 -> 149) -> c724; one-frame count -> c610.
 {const Bytes ram=base_ram();const Out o=block(ram,base_state(0xc5fc),0xc724);assert(get(o.ram,NODE+0x76,2)==0x95&&get(o.ram,NODE,4)==0xc608);}
}
void restart(){
 // c610: MOVE.W #1,702a(A5) (10f02a); MOVEQ #0,D0; JSR 49a1a.
 {Bytes ram=base_ram();put(ram,0x10f02a,2,0xabcd);const State s=base_state(0xc610);const Out o=block(ram,s,0x49a1a);
  assert(get(o.ram,0x10f02a,2)==1&&o.s.d[0]==0&&o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc61e);regs_kept(o,s,0,8);
  const std::uint32_t lo[2]={0x10f02a,SP-4},hi[2]={0x10f02c,SP};only_changed(ram,o.ram,lo,hi,2);}
 // c61e / c622 / c626: BSR c4cc, BSR caf0, JSR 47570 (return addresses pushed).
 const std::uint32_t pcs[3]={0xc61e,0xc622,0xc626},callee[3]={0xc4cc,0xcaf0,0x47570},ret[3]={0xc622,0xc626,0xc62c};
 for(unsigned int k=0;k<3;++k){const Bytes ram=base_ram();const State s=base_state(pcs[k]);const Out o=block(ram,s,callee[k]);
  assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==ret[k]);regs_kept(o,s,8,8);}
 // c62c: D0.W = 702a & 1 written back, D0.W + 6 passed to 4823a (upper D0 kept).
 const std::uint32_t modes[7]={0,1,2,3,0x8001,0xffff,0x1234};
 for(unsigned int k=0;k<7;++k){
  Bytes ram=base_ram();put(ram,0x10f02a,2,modes[k]);put(ram,0x10f02c,2,0x9999);const State s=base_state(0xc62c);const Out o=block(ram,s,0x4823a);
  assert(get(o.ram,0x10f02a,2)==(modes[k]&1U)&&get(o.ram,0x10f02c,2)==0x9999&&(o.s.d[0]&0xffffU)==(modes[k]&1U)+6U&&(o.s.d[0]>>16)==(s.d[0]>>16)&&
   o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc642);regs_kept(o,s,0,8);
  const std::uint32_t lo[2]={0x10f02a,SP-4},hi[2]={0x10f02c,SP};only_changed(ram,o.ram,lo,hi,2);
  // c642: D0.W = 702a (unmasked) for 3162.
  Bytes r2=base_ram();put(r2,0x10f02a,2,modes[k]);State t=base_state(0xc642);const Out q=block(r2,t,0x3162);
  assert((q.s.d[0]&0xffffU)==modes[k]&&(q.s.d[0]>>16)==(t.d[0]>>16));
  assert(get(q.ram,SP-4,4)==0xc64c&&q.s.a[7]==SP-4);}
 // c64c: MOVE.L #c654,(A6); RTS to the declared return.
 {Bytes ram=base_ram();put(ram,NODE,4,0xc608);const State s=base_state(0xc64c);const Out o=block(ram,s,RET);
  assert(get(o.ram,NODE,4)==0xc654&&o.s.a[7]==SP+4);regs_kept(o,s,8,8);const std::uint32_t lo[1]={NODE},hi[1]={NODE+4};only_changed(ram,o.ram,lo,hi,1);}
}
void title(){
 // c6da: JSR ca76(PC); c6de: A0 = de376, D0.W = 0, JSR 28ae; c6ee: MOVE.L #c6f4,(A6).
 {const Bytes ram=base_ram();const State s=base_state(0xc6da);const Out o=block(ram,s,0xca76);assert(o.s.a[7]==SP-4&&get(o.ram,SP-4,4)==0xc6de);regs_kept(o,s,8,8);}
 {const Bytes ram=base_ram();const State s=base_state(0xc6de);const Out o=block(ram,s,0x28ae);
  assert(o.s.a[0]==0xde376&&(o.s.d[0]&0xffffU)==0&&(o.s.d[0]>>16)==(s.d[0]>>16)&&get(o.ram,SP-4,4)==0xc6ee);regs_kept(o,s,0,0);}
 {Bytes ram=base_ram();put(ram,NODE,4,0xc5f4);const State s=base_state(0xc6ee);const Out o=block(ram,s,0xc6f4);assert(get(o.ram,NODE,4)==0xc6f4&&o.s.a[7]==SP);regs_kept(o,s,8,8);}
 // c6f4: D0.W = 7257, A0 = c6ce ("TIME"), JSR 3902; c702: D0.W = 7278, A0 = 7dda(A5) = 10fdda, D1.W = 3, D3 = 0, D4 = 2, JSR 36ba.
 {const Bytes ram=base_ram();const State s=base_state(0xc6f4);const Out o=block(ram,s,0x3902);
  assert((o.s.d[0]&0xffffU)==0x7257&&(o.s.d[0]>>16)==(s.d[0]>>16)&&o.s.a[0]==0xc6ce&&get(o.ram,SP-4,4)==0xc702&&o.s.a[7]==SP-4);regs_kept(o,s,0,0);}
 {const Bytes ram=base_ram();const State s=base_state(0xc702);const Out o=block(ram,s,0x36ba);
  assert((o.s.d[0]&0xffffU)==0x7278&&(o.s.d[0]>>16)==(s.d[0]>>16)&&o.s.a[0]==0x10fdda&&(o.s.d[1]&0xffffU)==3&&(o.s.d[1]>>16)==(s.d[1]>>16)&&
   o.s.d[3]==0&&o.s.d[4]==2&&get(o.ram,SP-4,4)==0xc718&&o.s.a[7]==SP-4);
  for(unsigned int i=0;i<8;++i)if(i!=0&&i!=1&&i!=3&&i!=4)assert(o.s.d[i]==s.d[i]);}
 // c718: BYTE 10fdda == 0 -> c73e (C1), else c720 -> c724 (BRA.W).
 for(unsigned int v=0;v<4;++v){Bytes ram=base_ram();const std::uint32_t val[4]={0,1,0x80,0xff};put(ram,0x10fdda,1,val[v]);
  const Out o=block(ram,base_state(0xc718),val[v]==0?0xc73e:0xc720);assert(o.ram==ram&&o.s.a[7]==SP);}
 {const Bytes ram=base_ram();const Out o=block(ram,base_state(0xc720),0xc724);assert(o.ram==ram&&o.s.a[7]==SP);}
}
void demo_child(){
 // 4fb1a: BYTE 10fd82 == 0 -> 4fb42, else 4fb22; 4fb22: BYTE 100001 == 1 -> 4fb2c, else 4fb42.
 const std::uint32_t v82[3]={0,1,0xff};
 for(unsigned int k=0;k<3;++k){Bytes ram=base_ram();put(ram,0x10fd82,1,v82[k]);const Out o=block(ram,base_state(0x4fb1a),v82[k]==0?0x4fb42:0x4fb22);assert(o.ram==ram&&o.s.a[7]==SP);}
 const std::uint32_t v01[5]={0,1,2,0x80,0xff};
 for(unsigned int k=0;k<5;++k){Bytes ram=base_ram();put(ram,0x100001,1,v01[k]);const Out o=block(ram,base_state(0x4fb22),v01[k]==1?0x4fb2c:0x4fb42);assert(o.ram==ram&&o.s.a[7]==SP);}
 // 4fb2c: A0 = 4fb64, D0.W = 0, JSR 28ae (return 4fb3c).
 {const Bytes ram=base_ram();const State s=base_state(0x4fb2c);const Out o=block(ram,s,0x28ae);
  assert(o.s.a[0]==0x4fb64&&(o.s.d[0]&0xffffU)==0&&(o.s.d[0]>>16)==(s.d[0]>>16)&&get(o.ram,SP-4,4)==0x4fb3c&&o.s.a[7]==SP-4);regs_kept(o,s,0,0);}
 // 4fb3c: SCC.B 62(A6): C Set (28ae allocated) -> 00, C Clear -> ff; the carry is kept across the call-return and the RTS goes to RET.
 for(unsigned int k=0;k<2;++k){Bytes ram=base_ram();put(ram,NODE+0x62,1,k==0?0xa5:0x5a);put(ram,NODE+0x63,1,0x33);
  State s=base_state(0x4fb3c);s.carry=k==0?ms5::AnimationCarrySet:ms5::AnimationCarryClear;const Out o=block(ram,s,RET);
  assert(get(o.ram,NODE+0x62,1)==(k==0?0U:0xffU)&&get(o.ram,NODE+0x63,1)==0x33&&o.s.a[7]==SP+4&&o.s.carry==s.carry);regs_kept(o,s,8,8);
  const std::uint32_t lo[1]={NODE+0x62},hi[1]={NODE+0x63};only_changed(ram,o.ram,lo,hi,1);}
 {State s=base_state(0x4fb3c);s.carry=ms5::AnimationCarryUnknown;fail(base_ram(),s,base_device(),RET,"controller c3 caller requires known carry");}
 // 4fb42: MOVE.B #ff,62(A6); RTS. The chain 4fb1a (10fd82 = 0) -> 4fb42 -> RTS.
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,0);const Out o=block(ram,base_state(0x4fb42),RET);assert(get(o.ram,NODE+0x62,1)==0xff&&o.s.a[7]==SP+4);}
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,0);put(ram,0x10fd82,1,0);const Out o=block(ram,base_state(0x4fb1a),RET);assert(get(o.ram,NODE+0x62,1)==0xff&&o.s.a[7]==SP+4);}
 {Bytes ram=base_ram();put(ram,NODE+0x62,1,0);put(ram,0x10fd82,1,1);put(ram,0x100001,1,2);const Out o=block(ram,base_state(0x4fb1a),RET);
  assert(get(o.ram,NODE+0x62,1)==0xff&&o.s.a[7]==SP+4);}
}
void c3b_errors(){
 const Bytes ram=base_ram();
 // Every even PC of the four routed ranges that is not a block start is a checked error of the unit (odd PCs are caught earlier).
 const std::uint32_t lo[4]={0x8b64,0xc52a,0xc6da,0x4fb1a},hi[4]={0x8bbc,0xc654,0xc724,0x4fb4a};unsigned int interior=0;
 for(unsigned int r=0;r<4;++r)for(std::uint32_t pc=lo[r];pc<hi[r];pc+=2)if(!is_start(pc)){
  fail(ram,base_state(pc),base_device(),RET,"unsupported animation controller c3 PC");++interior;}
 assert(interior>60);
 fail(ram,base_state(0xc56f),base_device(),RET,"unaligned animation machine PC");
 fail(ram,base_state(0xc6db),base_device(),RET,"unaligned animation machine PC");
 fail(ram,base_state(0x4fb1b),base_device(),RET,"unaligned animation machine PC");
 // Failed writes roll back everything: an odd A6 (the LONG install), an A6 in ROM space, the RTS pop from ROM space after the install.
 {State s=base_state(0xc5ea);s.a[6]=NODE+1;fail(ram,s,base_device(),0xc5f4,"invalid animation machine write size/alignment");}
 {State s=base_state(0xc5c8);s.a[6]=NODE+1;fail(ram,s,base_device(),0xc5ce,"invalid animation machine write size/alignment");}
 {State s=base_state(0xc5fc);s.a[6]=NODE+1;fail(ram,s,base_device(),0xc608,"invalid animation machine write size/alignment");}
 {State s=base_state(0xc608);s.a[6]=NODE+1;fail(ram,s,base_device(),RET,"program bus requires even WORD/LONG address");}
 {State s=base_state(0xc64c);s.a[7]=0x200004;fail(ram,s,base_device(),RET,"missing or ambiguous physical program bus ROM byte");}
 {State s=base_state(0x4fb42);s.a[6]=0x200000;fail(ram,s,base_device(),RET,"unsupported animation machine write device");}
 {State s=base_state(0xc610);s.a[5]=0x200000;fail(ram,s,base_device(),0x49a1a,"unsupported animation machine write device");}
 {State s=base_state(0xc57c);s.a[7]=0x200004;fail(ram,s,base_device(),0x47570,"program bus write requires RAM mirror units");}
}
}
int main(){
 boot_head();boot_wait();errors();
 boot_after_wait();demo_intro();restart();title();demo_child();c3b_errors();
 std::cout<<"animation machine controller c3: "<<checks<<" checks\n";
 return 0;
}
