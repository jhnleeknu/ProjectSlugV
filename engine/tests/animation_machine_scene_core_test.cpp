#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
// 480bc frame helper U2 (scene core 1a73c) through run_animation_machine only. All inputs are declared,
// synthetic RAM fixtures (no ROM resources are read); the return LONG of each direct entry is declared at SP.
// Field addresses are A5=108000 relative (53xx -> 10d3xx); players at -7348/-7258(A5) = 100cb8/100da8.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
const std::uint32_t SP=0x10f7fc,STOP=0xff000,A5=0x108000,P1=0x100cb8,P2=0x100da8,BANKFLAG=0x100010;
const std::uint32_t BUF=0x10e800,COND=0x10e700,MOT=0x10ea00,SCR=0x10eb00,PL=0x10e900;
unsigned int calls=0;
std::uint32_t F(std::uint32_t displacement){return 0x100000U+((A5+displacement)&0xffffU);} // d16(A5), positive d16
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void putf(Bytes&b,std::uint32_t d,unsigned int n,std::uint32_t v){put(b,F(d),n,v);}
std::uint32_t getf(const Bytes&b,std::uint32_t d,unsigned int n){return get(b,F(d),n);}
// Generic fixture: D0-D7 zero, A0=player 1, A1=RAM buffer, A5=108000, A7=SP holding the STOP return LONG.
State state(std::uint32_t pc){State s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0;s.a[i]=0;}
 s.a[0]=P1;s.a[1]=BUF;s.a[5]=A5;s.a[7]=SP;return s;}
// Upper-WORD patterns for width checks.
State patterned(std::uint32_t pc){State s=state(pc);for(unsigned int i=0;i<8;++i)s.d[i]=0xabcd0000U+i*0x10001U;return s;}
Bytes zero_ram(){Bytes ram(65536,0);put(ram,SP,4,STOP);return ram;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
void show(const State&a,const State&b){for(unsigned int i=0;i<8;++i){if(a.d[i]!=b.d[i])std::cerr<<std::hex<<"d"<<i<<" "<<a.d[i]<<" want "<<b.d[i]<<"\n";
 if(a.a[i]!=b.a[i])std::cerr<<std::hex<<"a"<<i<<" "<<a.a[i]<<" want "<<b.a[i]<<"\n";}if(a.pc!=b.pc)std::cerr<<std::hex<<"pc "<<a.pc<<" want "<<b.pc<<"\n";
 if(a.carry!=b.carry)std::cerr<<"carry "<<a.carry<<" want "<<b.carry<<"\n";}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource>w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
// Success without device effects: returned, no reads/ports/PVC/bank changes.
bool quiet(const Out&o){return o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.error.empty()&&o.ports.empty()&&o.dev.pvc==Out().dev.pvc&&o.dev.bank_base==0x200000;}
bool port(const Out&o,unsigned int i,std::uint32_t address,std::uint32_t value){return i<o.ports.size()&&o.ports[i].address==address&&o.ports[i].size==2&&o.ports[i].value==value;}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message){
 const Bytes before=ram;const State old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource>w;
 if(ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error)){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error.find(message)==std::string::npos)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&
  o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
// Stack scratch below SP is compared separately (call frames are checked explicitly where they matter).
void stack_from(Bytes&expect,const Bytes&ram){for(std::uint32_t a=SP-64;a<SP;++a)expect[a&65535U]=ram[a&65535U];}

// Natural seed shape (scene_frame canonical frames): condition, script and motion null, force 0,
// camera flags 0, shake 00080000.
Bytes natural_ram(){
 Bytes ram=zero_ram();
 putf(ram,0x541e,2,0x0100);putf(ram,0x5420,2,0x0080);putf(ram,0x5440,2,0x0200);putf(ram,0x5442,2,0x0040);
 putf(ram,0x5444,2,0x8000);putf(ram,0x5448,2,0x1111);putf(ram,0x5426,2,0x0011);putf(ram,0x542a,2,0x0022);
 putf(ram,0x5446,2,0x0033);putf(ram,0x544a,2,0x0044);
 putf(ram,0x53bc,4,0x00500000);putf(ram,0x53c0,4,0x00300000);putf(ram,0x53a2,2,0x0010);putf(ram,0x53a6,2,0x0008);
 putf(ram,0x53ce,2,0x7fff);putf(ram,0x53d2,2,0x8000);putf(ram,0x53d0,2,0x7fff);putf(ram,0x53d4,2,0x8000);
 putf(ram,0x53fc,4,0x00001000);putf(ram,0x5400,4,0xfffff000);putf(ram,0x53b8,2,0x0050);putf(ram,0x53ba,2,0x0031);
 putf(ram,0x5418,2,0x0003);putf(ram,0x5408,4,0x00080000);putf(ram,0x5404,2,0x0002);
 return ram;}
// 1a73c -> 1a2b4 (null, Set) -> 1a26a (null) -> 1a526 -> 19b96 (19be4/19c06 fixed deltas, 19832 null,
// 19c28 -> 19c40, 19978/198ee null, 19cd6) -> 19d08 (19802 null, 19d98 twice) -> 1a776 -> 1a3d6 -> 1a7a8 stop.
void natural(){
 Bytes ram=natural_ram();Bytes expect=ram;State s=state(0x1a73c);Out o;
 assert(run(ram,s,0x1a7a8,o));
 State want=state(0x1a7a8);want.a[7]=SP-4;want.a[1]=0;want.carry=ms5::AnimationCarryUnknown;
 want.d[0]=0x0000fff9;want.d[1]=0x00008000;want.d[2]=0x50;want.d[3]=0x31;want.d[4]=0x60;want.d[5]=0x01000000;want.d[6]=3;want.d[7]=0;
 if(!same(s,want))show(s,want);assert(same(s,want));
 put(expect,BANKFLAG,2,1);
 putf(expect,0x53ee,2,0x0100);putf(expect,0x53f0,2,0x0040);putf(expect,0x53d6,2,0x0011);putf(expect,0x53da,2,0x0022);
 putf(expect,0x53d8,2,0x0033);putf(expect,0x53dc,2,0x0044);putf(expect,0x53fa,2,0);
 putf(expect,0x53de,4,0x00001000);putf(expect,0x53e2,4,0xfffff000);putf(expect,0x53c4,4,0x00500000);putf(expect,0x53c8,4,0x00310000);
 putf(expect,0x53c0,4,0x00310000);putf(expect,0x53f2,2,0x0060);putf(expect,0x53f6,2,0x0039);putf(expect,0x53f4,2,0x01a0);putf(expect,0x53f8,2,0x0139);
 putf(expect,0x5408,4,0xfff88000);putf(expect,0x5406,2,0x0002);putf(expect,0x5404,2,0xfff9);
 stack_from(expect,ram);assert(ram==expect&&get(ram,SP-4,4)==0x1a78c&&get(ram,SP,4)==STOP);
 // Two ordered PVC WORD writes (2000 then 0) select physical bank 300000; no device reads.
 assert(o.ports.size()==2&&port(o,0,0x2ffff2,0x2000)&&port(o,1,0x2ffff0,0)&&o.dev.bank_base==0x300000&&o.reads==0&&o.status==ms5::AnimationMachineReturned);
 // Split at 19d08 and 1a776: same final RAM/registers.
 {Bytes r2=natural_ram();State s2=state(0x1a73c);Out o2;assert(run(r2,s2,0x19d08,o2)&&s2.a[7]==SP-4&&get(r2,SP-4,4)==0x1a76a);
  Out o3;assert(run(r2,s2,0x1a776,o3)&&o3.ports.empty());Out o4;assert(run(r2,s2,0x1a7a8,o4)&&same(s2,want)&&r2==ram);}
 // The 1a7a8 boundary with another stop rolls back everything, including the PVC writes.
 reject(natural_ram(),state(0x1a73c),STOP,"unsupported animation machine PC");
 // Phase update at 1a780: D7.W (SWAP of the 19802 result) not below the phase is stored (max).
 {Bytes r=zero_ram();putf(r,0x5418,2,0x0004);State t=state(0x1a776);t.d[7]=0x00071234;Out q;
  assert(run(r,t,0x1a784,q)&&quiet(q)&&getf(r,0x5418,2)==0x0007&&t.d[7]==0x12340007);
  t=state(0x1a776);t.d[7]=0x00031234;assert(run(r,t,0x1a784,q)&&getf(r,0x5418,2)==0x0007);}
}
// Declared re-entry after 1a7a8 returned: 1a78c -> 1a442 (null / ffff / later / due) -> 1a790 end.
void tail(){
 for(unsigned int k=0;k<4;++k){Bytes ram=zero_ram();putf(ram,0x5418,2,3);
  if(k){putf(ram,0x540e,4,PL);put(ram,PL,2,k==1?0xffff:(k==2?0x0004:0x0003));}
  Bytes expect=ram;State s=state(0x1a78c);Out o;
  if(k==3){assert(run(ram,s,0x1a470,o)&&quiet(o)&&s.a[7]==SP-8&&get(ram,SP-4,4)==0x1a790&&get(ram,SP-8,4)==0x1a46a&&s.a[0]==PL&&s.d[7]==3);
   // 1a46a after the boundary: placement pointer advanced by the callee, stored, then 1a790.
   s.pc=0x1a46a;s.a[0]=PL+6;s.a[7]=SP-4;Out q;assert(run(ram,s,STOP,q)&&getf(ram,0x540e,4)==PL+6&&s.a[7]==SP+4);
   assert(q.ports.size()==2&&port(q,0,0x2ffff2,0x1000)&&port(q,1,0x2ffff0,0)&&q.dev.bank_base==0x200000&&get(ram,BANKFLAG,2)==0);continue;}
  put(ram,BANKFLAG,2,1);put(expect,BANKFLAG,2,0);
  assert(run(ram,s,STOP,o)&&s.pc==STOP&&s.a[7]==SP+4&&s.a[0]==(k?PL:0U)&&s.d[7]==(k==1?0xffffU:(k==2?4U:0U)));
  assert(s.carry==ms5::AnimationCarryUnknown);stack_from(expect,ram);assert(ram==expect);
  assert(o.ports.size()==2&&port(o,0,0x2ffff2,0x1000)&&port(o,1,0x2ffff0,0)&&o.dev.bank_base==0x200000);}
 // Wrong stop at the 1a470 boundary rolls back.
 Bytes ram=zero_ram();putf(ram,0x540e,4,PL);reject(ram,state(0x1a78c),STOP,"unsupported animation machine PC");
}
// Terminated two-record motion path at MOT (type 14 from time 0, terminator type ffff at time 100).
void motion_path(Bytes&ram){put(ram,MOT,2,0);put(ram,MOT+2,2,0x14);put(ram,MOT+10,2,0x100);put(ram,MOT+12,2,0xffff);}
// Non-null motion: 19832 -> 19844 stop (53fa=0), 19bbe/19802 -> 19812 stop (53fa!=0); direct 19978/19d98 -> 19910.
// 19812/19844/19910 now execute (motion walk U3), so they remain valid stops; the frame continues to 1a7a8.
void motion(){
 {Bytes ram=natural_ram();putf(ram,0x53b4,4,MOT);State s=state(0x1a73c);Out o;assert(run(ram,s,0x19844,o));
  assert(s.a[7]==SP-8&&get(ram,SP-4,4)==0x1a766&&get(ram,SP-8,4)==0x19c22&&s.a[1]==MOT&&s.d[7]==0x002ff000&&getf(ram,0x53c8,4)==0x002ff000);
  assert(o.ports.size()==2&&s.carry==ms5::AnimationCarryUnknown);
  reject(natural_ram(),state(0x1a73c),0x19812,"unsupported animation machine PC");}
 {Bytes ram=natural_ram();putf(ram,0x53b4,4,MOT);putf(ram,0x543e,2,2);State s=state(0x1a73c);Out o;assert(run(ram,s,0x19812,o));
  assert(s.a[7]==SP-8&&get(ram,SP-4,4)==0x1a766&&get(ram,SP-8,4)==0x19bca&&s.a[1]==MOT&&getf(ram,0x53fa,2)==2&&s.d[0]==0x00500000&&s.d[1]==0x00300000);
  ram=natural_ram();putf(ram,0x53b4,4,MOT);putf(ram,0x543e,2,2);motion_path(ram);reject(ram,state(0x1a73c),0x19844,"unsupported animation machine PC");
  // Never-reached stops still roll back at the 1a7a8 boundary after the U3 walks.
  ram=natural_ram();putf(ram,0x53b4,4,MOT);motion_path(ram);reject(ram,state(0x1a73c),0x1a0b6,"unsupported animation machine PC");
  ram=natural_ram();putf(ram,0x53b4,4,MOT);motion_path(ram);s=state(0x1a73c);assert(run(ram,s,0x1a7a8,o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x1a78c);}
 const std::uint32_t entries[][2]={{0x19978,0x1997c},{0x19d98,0x19da0}};
 for(unsigned int i=0;i<2;++i){Bytes ram=zero_ram();putf(ram,0x53b4,4,MOT);State s=state(entries[i][0]);s.d[7]=0x12345678;Out o;
  assert(run(ram,s,0x19910,o)&&quiet(o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==entries[i][1]&&s.a[1]==MOT);
  assert(s.d[7]==(i?0x56780000U:0x12345678U));
  motion_path(ram);s=state(entries[i][0]);assert(run(ram,s,STOP,o)&&s.a[7]==SP+4);
  motion_path(ram);reject(ram,state(entries[i][0]),0x1a0b6,"unsupported animation machine PC");}
 // 10d3fa != 0 with null motion: 19bca D7 = (53fa<<8) + D6 (=0), clamped by 19c28 (53ee<<16).
 {Bytes ram=natural_ram();putf(ram,0x543e,2,0x0300);State s=state(0x1a75e);s.a[7]=SP;Out o;assert(run(ram,s,0x1a766,o)&&quiet(o));
  assert(getf(ram,0x53fa,2)==0x0300&&s.d[6]==0&&s.d[7]==0x00030000&&s.d[5]==0x01000000);
  // 19c60 TST.W 53fa != 0 skips the approval tests: 53bc/53c0 = 198ee null result.
  assert(getf(ram,0x53bc,4)==0x00500000&&getf(ram,0x53c0,4)==0x00310000&&getf(ram,0x53c4,4)==0x00500000);}
}
// Script 1a26a: gate open -> 1a0b6 stop; negative WORD -> 1a28a; wait not reached -> 1a29c; 1a296 re-entry.
void script(){
 {Bytes ram=natural_ram();putf(ram,0x5412,4,SCR);putf(ram,0x5416,2,3);put(ram,SCR,2,0x0001);State s=state(0x1a73c);Out o;
  assert(run(ram,s,0x1a0b6,o)&&s.a[7]==SP-8&&get(ram,SP-4,4)==0x1a75e&&get(ram,SP-8,4)==0x1a296&&s.a[1]==SCR&&(s.d[0]&65535U)==3);
  assert(o.ports.size()==2&&s.carry==ms5::AnimationCarryUnknown); // 1a2cc Set is consumed at 1a756; 1a26a CMPA leaves Unknown
  ram=natural_ram();putf(ram,0x5412,4,SCR);putf(ram,0x5416,2,3);put(ram,SCR,2,1);reject(ram,state(0x1a73c),0x1a7a8,"unsupported animation machine PC");}
 {Bytes ram=natural_ram();putf(ram,0x5412,4,SCR);putf(ram,0x5416,2,3);put(ram,SCR,2,0x8000);State s=state(0x1a73c);Out o;
  assert(run(ram,s,0x1a7a8,o)&&getf(ram,0x5416,2)==0xffff&&getf(ram,0x5412,4)==SCR);}
 {Bytes ram=natural_ram();putf(ram,0x5412,4,SCR);putf(ram,0x5416,2,4);put(ram,SCR,2,1);State s=state(0x1a73c);Out o;
  assert(run(ram,s,0x1a7a8,o)&&getf(ram,0x5416,2)==4);}
 {Bytes ram=zero_ram();putf(ram,0x5418,2,3);putf(ram,0x5416,2,5);State s=state(0x1a296);s.a[1]=SCR+4;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&getf(ram,0x5412,4)==SCR+4&&s.a[7]==SP+4&&s.d[0]==3);}
}
// Player fixture for 289e and the rect test: marker 270e (289e Clear) or not; 15(A0) bit 7; 42/46 WORDs.
void player(Bytes&ram,std::uint32_t p,bool marker,bool active,std::uint32_t x,std::uint32_t y){
 put(ram,p,4,marker?0x270eU:0x2710U);put(ram,p+0x15,1,active?0x80:0x7f);put(ram,p+0x42,2,(x+0x100U)&65535U);put(ram,p+0x46,2,(y+0x200U)&65535U);}
Bytes cond_ram(std::uint32_t index){Bytes ram=zero_ram();putf(ram,0x5422,4,COND);put(ram,COND,2,index);putf(ram,0x53a2,2,0x100);putf(ram,0x53a6,2,0x200);
 putf(ram,0x541e,2,0x1111);putf(ram,0x5420,2,0x2222);putf(ram,0x543e,2,0x3333);return ram;}
// rect (X<<16|Y, W<<16|H) at a.
void rect(Bytes&ram,std::uint32_t a,std::uint32_t x,std::uint32_t y,std::uint32_t w,std::uint32_t h){put(ram,a,4,(x<<16)|y);put(ram,a+4,4,(w<<16)|h);}
// Direct 1a2b4 entry (return STOP). Returns the final C; 'met' means 1a29e cleared the condition.
ms5::AnimationCarryState condition(Bytes ram,bool& met){
 State s=state(0x1a2b4);s.carry=ms5::AnimationCarryUnknown;Out o;if(!run(ram,s,STOP,o))assert(false);
 met=getf(ram,0x5422,4)==0;
 assert(quiet(o)&&s.pc==STOP&&s.a[7]==SP+4&&s.carry==(met?ms5::AnimationCarrySet:ms5::AnimationCarryClear));if(met)assert(getf(ram,0x541e,2)==0x7fff&&getf(ram,0x5420,2)==0x7fff&&getf(ram,0x543e,2)==0);
 return s.carry;}
bool met_of(const Bytes&ram){bool met=false;condition(ram,met);return met;}
void conditions(){
 // Null condition: 1a2cc Set without touching anything.
 {Bytes ram=zero_ram();const Bytes expect=ram;State s=patterned(0x1a2b4);s.carry=ms5::AnimationCarryClear;State want=s;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&ram==expect);want.pc=STOP;want.a[7]=SP+4;want.a[1]=0;want.carry=ms5::AnimationCarrySet;assert(same(s,want));}
 // Index 0 / index c (computed JSR straight to 1a2e0): 543e from the record, phase vs 541e.
 for(unsigned int c=0;c<2;++c)for(unsigned int k=0;k<2;++k){Bytes ram=cond_ram(c?0xc:0);put(ram,COND+2,2,0x1234);putf(ram,0x5418,2,k?0x1111:0x1110);
  State s=state(0x1a2b4);Out o;assert(run(ram,s,0x1a2c6,o)&&quiet(o)&&s.a[1]==COND+4&&getf(ram,0x543e,2)==0x1234&&(s.d[0]&65535U)==(k?0x1111U:0x1110U));
  assert(s.carry==(k?ms5::AnimationCarrySet:ms5::AnimationCarryClear)&&s.a[7]==SP&&get(ram,SP-4,4)==0x1a2c6); // handler RTS popped the 1a2c6 LONG
  assert(met_of(ram)==(k==1));}
 // Met with a non-null motion list: 1a29e -> 197da walks 10-byte records to the 2(A1)==ffff record.
 {Bytes ram=cond_ram(0);putf(ram,0x5418,2,0x1111);putf(ram,0x53b4,4,MOT);put(ram,MOT,2,0x10);put(ram,MOT+10,2,0x20);put(ram,MOT+12,2,1);
  put(ram,MOT+20,2,0x30);put(ram,MOT+22,2,0xffff);State s=state(0x1a2b4);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  assert(getf(ram,0x5422,4)==0&&getf(ram,0x541e,2)==0x2f&&getf(ram,0x5420,2)==0x2f&&getf(ram,0x543e,2)==0&&s.a[1]==MOT+20&&s.carry==ms5::AnimationCarrySet);}
 // Index 4 (1a334): 568e==0 -> Clear.
 {Bytes ram=cond_ram(4);player(ram,P1,true,true,0,0);player(ram,P2,true,true,0,0);assert(!met_of(ram));
  putf(ram,0x568e,1,1);assert(met_of(ram));} // both markers: 1a356 Set twice (second via the 1a348 fall-through)
 struct Case {bool m1,a1;std::uint32_t x1,y1;bool m2,a2;std::uint32_t x2,y2;bool met;};
 // rect 1 at COND+2: X 10..40, Y 20..60 (exclusive ends).
 const Case four[]={
  {true,false,0,0,false,false,0,0,false},     // P2 not ready, inactive
  {false,false,0x20,0x30,true,false,0,0,false}, // P1 inactive (BTST #7 = 0)
  {false,true,0x20,0x30,true,false,0,0,true},   // P1 inside, P2 marker
  {false,true,0x0f,0x30,true,false,0,0,false},  // X below
  {false,true,0x40,0x30,true,false,0,0,false},  // X at end
  {false,true,0x20,0x1f,true,false,0,0,false},  // Y below
  {false,true,0x20,0x60,true,false,0,0,false},  // Y at end
  {false,true,0x10,0x20,false,true,0x3f,0x5f,true}, // both inside at the corners
  {false,true,0x20,0x30,false,true,0x20,0x70,false}};
 for(unsigned int i=0;i<sizeof(four)/sizeof(four[0]);++i){Bytes ram=cond_ram(4);putf(ram,0x568e,1,0x80);rect(ram,COND+2,0x10,0x20,0x30,0x40);
  player(ram,P1,four[i].m1,four[i].a1,four[i].x1,four[i].y1);player(ram,P2,four[i].m2,four[i].a2,four[i].x2,four[i].y2);
  if(met_of(ram)!=four[i].met)std::cerr<<"index 4 case "<<i<<"\n";assert(met_of(ram)==four[i].met);}
 // ADD.L D4,D5: Y end ffff0+0020 carries into the X WORD (X end 41): X=40 is inside only with the carry.
 {Bytes ram=cond_ram(4);putf(ram,0x568e,1,1);rect(ram,COND+2,0x10,0xfff0,0x30,0x20);player(ram,P1,false,true,0x40,0);player(ram,P2,true,false,0,0);
  assert(met_of(ram));player(ram,P1,false,true,0x41,0);assert(!met_of(ram));player(ram,P1,false,true,0x40,0xfff0);assert(met_of(ram));
  player(ram,P1,false,true,0x40,0x0010);assert(!met_of(ram));}
 // Index 8 (1a2f2): both in rect 1 (1a312), else both in rect 2 (A1+8, 1a330/1a332).
 const Case eight[]={
  {true,false,0,0,true,false,0,0,true},
  {false,true,0x20,0x30,true,false,0,0,true},    // rect 1
  {false,true,0x80,0x90,true,false,0,0,true},    // rect 2 only
  {false,true,0x20,0x30,false,false,0,0,false},  // P2 inactive in both
  {false,true,0x20,0x30,false,true,0x80,0x90,false}, // split between rects
  {false,true,0x80,0x90,false,true,0x81,0x91,true},
  {false,true,0x00,0x00,true,false,0,0,false}};
 for(unsigned int i=0;i<sizeof(eight)/sizeof(eight[0]);++i){Bytes ram=cond_ram(8);putf(ram,0x568e,1,2);rect(ram,COND+2,0x10,0x20,0x30,0x40);rect(ram,COND+10,0x70,0x80,0x20,0x20);
  player(ram,P1,eight[i].m1,eight[i].a1,eight[i].x1,eight[i].y1);player(ram,P2,eight[i].m2,eight[i].a2,eight[i].x2,eight[i].y2);
  if(met_of(ram)!=eight[i].met)std::cerr<<"index 8 case "<<i<<"\n";assert(met_of(ram)==eight[i].met);
  // Final A1 shows whether rect 2 was examined (stop at the 1a2c6 consumer).
  State s=state(0x1a2b4);Out o;Bytes r=ram;assert(run(r,s,0x1a2c6,o));const bool second=!(eight[i].m1&&eight[i].m2)&&i!=1;
  assert(s.a[1]==(second?COND+10:COND+2));}
 {Bytes ram=cond_ram(8);rect(ram,COND+2,0,0,0x7fff,0x7fff);player(ram,P1,true,true,0,0);player(ram,P2,true,true,0,0);assert(!met_of(ram));}
 // Index policy: odd -> odd PC error; interior/outside PCs -> unsupported; fffe -> 1a2d2 RTS reaches 1a2c6 with the
 // C of MOVE.W (A1)+,D0, which the model leaves Unknown (checked error, not a guessed C).
 reject(cond_ram(1),state(0x1a2b4),STOP,"unaligned animation machine PC");
 reject(cond_ram(0xffff),state(0x1a2b4),STOP,"unaligned animation machine PC");
 reject(cond_ram(2),state(0x1a2b4),STOP,"unsupported animation scene core PC");
 reject(cond_ram(0x1000),state(0x1a2b4),STOP,"unsupported animation machine PC");
 reject(cond_ram(0xfffe),state(0x1a2b4),STOP,"scene core caller requires known carry");
}
// 197da direct: null (7fff, upper WORD kept), first record terminal, later record terminal.
void motion_list(){
 {Bytes ram=zero_ram();State s=patterned(0x197da);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&s.d[7]==0xabd47fffU&&s.a[1]==0);}
 {Bytes ram=zero_ram();putf(ram,0x53b4,4,MOT);put(ram,MOT,2,0);put(ram,MOT+2,2,0xffff);State s=patterned(0x197da);Out o;
  assert(run(ram,s,STOP,o)&&s.d[7]==0xabd4ffffU&&s.a[1]==MOT);}
 {Bytes ram=zero_ram();putf(ram,0x53b4,4,MOT);for(unsigned int i=0;i<40;++i)put(ram,MOT+10*i,2,i+1);put(ram,MOT+10*39+2,2,0xffff);
  State s=patterned(0x197da);Out o;assert(run(ram,s,STOP,o)&&s.d[7]==0xabd40027U&&s.a[1]==MOT+390);}
}
// 19a40/19ac8 camera axis bodies (direct entry): clamp branches, ASR rounding, ADD.L N^V, Y's store-then-average.
void axis(){
 {Bytes ram=zero_ram();putf(ram,0x53ce,2,0x100);putf(ram,0x53d2,2,0x200);putf(ram,0x53d6,2,0x80);putf(ram,0x53da,2,0x10);
  putf(ram,0x53e6,4,0x00100000);putf(ram,0x53de,4,1);State s=state(0x19a40);State want=s;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  want.pc=STOP;want.a[7]=SP+4;want.carry=ms5::AnimationCarryUnknown;want.d[0]=0x00200000;want.d[1]=0;want.d[5]=0x10;want.d[6]=0;want.d[7]=0x00080001;
  if(!same(s,want))show(s,want);assert(same(s,want)&&getf(ram,0x53de,4)==0x00080001);}
 // Negative half-sum: 19a68/19a74 zeroing, signed BLE/BGE, no +7 for negative, limit by 19aae, floor of the odd negative /2.
 {Bytes ram=zero_ram();putf(ram,0x53ce,2,0x10);putf(ram,0x53d2,2,0x20);putf(ram,0x53d6,2,0x100);putf(ram,0x53da,2,0x10);
  putf(ram,0x53e6,4,0x00100000);putf(ram,0x53de,4,3);State s=state(0x19a40);State want=s;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  want.pc=STOP;want.a[7]=SP+4;want.carry=ms5::AnimationCarryUnknown;want.d[0]=0xfff50000;want.d[1]=0x0000ff0c;want.d[5]=0x10;want.d[6]=0xff28;want.d[7]=0xfff80001;
  if(!same(s,want))show(s,want);assert(same(s,want)&&getf(ram,0x53de,4)==0xfff80001);}
 // Y: 53e2 is stored before the average, so D7 = new 53e2 and the previous 53e2 is not used.
 {Bytes ram=zero_ram();putf(ram,0x53d0,2,0x100);putf(ram,0x53d4,2,0x200);putf(ram,0x53d8,2,0x80);putf(ram,0x53dc,2,0x10);
  putf(ram,0x53ea,4,0x00100000);putf(ram,0x53e2,4,0x55);putf(ram,0x53de,4,0x77);State s=state(0x19ac8);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  assert(s.d[7]==0x00100000&&getf(ram,0x53e2,4)==0x00100000&&getf(ram,0x53de,4)==0x77&&s.d[0]==0x00200000&&s.d[1]==0);}
 // ADD.L D7,D0 signed overflow: N=1,V=1 -> BGE taken (no SUB.L).
 {Bytes ram=zero_ram();State s=state(0x19aa8);s.d[0]=0x7ff00000;s.d[7]=0x00200000;Out o;assert(run(ram,s,STOP,o)&&s.d[0]==0x80100000&&getf(ram,0x53de,4)==0x00100000);
  s=state(0x19aa8);s.d[0]=0x00100000;s.d[7]=0xffe00000;assert(run(ram,s,0x19ab0,o)&&s.d[0]==0xfff00000&&s.d[7]==0xfff00000);} // N=1,V=0: D7-=D0
 // 19ab0 rounding: odd negative difference floors, odd positive ceils.
 {Bytes ram=zero_ram();putf(ram,0x53de,4,3);State s=state(0x19ab0);Out o;assert(run(ram,s,STOP,o)&&getf(ram,0x53de,4)==1&&s.d[7]==1);
  putf(ram,0x53de,4,0);s=state(0x19ab0);s.d[7]=3;assert(run(ram,s,STOP,o)&&getf(ram,0x53de,4)==2);
  putf(ram,0x53de,4,0);s=state(0x19ab0);s.d[7]=0xfffffffd;assert(run(ram,s,STOP,o)&&getf(ram,0x53de,4)==0xfffffffe);}
}
// 19c22..19c5a: unsigned LONG clamp of D7 between D6 and 53ee<<16 / 53f0<<16, stopping at the 19978 call.
void clamp(){
 struct Row {std::uint32_t d7,d6,limit_low,limit_high,d5,result;};
 const Row rows[]={{0x00100000,0x00200000,0,0x18,0x00180000,0x00180000},{0x00100000,0x00120000,0,0x18,0x00120000,0x00120000},
  {0x00300000,0x00100000,0x20,0,0x00200000,0x00200000},{0x00300000,0x00280000,0x20,0,0x00280000,0x00280000},
  {0x00180000,0x00100000,0x20,0,0x00200000,0x00180000},{0x00200000,0x00300000,0,0x18,0x00180000,0x00200000}};
 for(unsigned int i=0;i<6;++i){Bytes ram=zero_ram();putf(ram,0x53ee,2,rows[i].limit_low);putf(ram,0x53f0,2,rows[i].limit_high);
  State s=state(0x19c22);s.d[7]=rows[i].d7;s.d[6]=rows[i].d6;Out o;assert(run(ram,s,0x19978,o)&&quiet(o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x19c60);
  if(s.d[5]!=rows[i].d5||s.d[7]!=rows[i].result)std::cerr<<"clamp "<<i<<"\n";assert(s.d[5]==rows[i].d5&&s.d[7]==rows[i].result&&s.d[6]==rows[i].d6);}
}
// 1997c with A1 != 0 (declared non-null motion return): ADD.L, CMP.L/BPL (N only), EXG, target updates.
void follow(){
 struct Row {std::uint32_t d[4],x,y,out[4],ox,oy;};
 const Row rows[]={
  {{0x00200000,0x00100000,0xfff00000,0x00050000},0x00180000,0x00080000,{0xfff80000,0x00080000,0x00080000,0x00050000},0x00180000,0x00100000},
  {{0x00100000,0x00100000,0x00050000,0x00050000},0x00080000,0x00200000,{0x00080000,0xfff00000,0x00050000,0xfff50000},0x00100000,0x00150000},
  {{0x00100000,0x00100000,0x00050000,0xfff00000},0x00300000,0x00080000,{0xffe00000,0xfff80000,0xffe50000,0x00080000},0x00150000,0x00080000}};
 for(unsigned int i=0;i<3;++i){Bytes ram=zero_ram();putf(ram,0x53c4,4,rows[i].x);putf(ram,0x53c8,4,rows[i].y);State s=state(0x1997c);s.a[1]=MOT;
  for(unsigned int k=0;k<4;++k)s.d[k]=rows[i].d[k];Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  for(unsigned int k=0;k<4;++k)if(s.d[k]!=rows[i].out[k])std::cerr<<std::hex<<"follow "<<i<<" d"<<k<<" "<<s.d[k]<<"\n";
  assert(s.d[0]==rows[i].out[0]&&s.d[1]==rows[i].out[1]&&s.d[2]==rows[i].out[2]&&s.d[3]==rows[i].out[3]);
  assert(getf(ram,0x53c4,4)==rows[i].ox&&getf(ram,0x53c8,4)==rows[i].oy);}
}
// 19d08 bounds: 19d2c WORD push and 19d4c pop, 19da0 EXG and signed min/max, 19d5e BVC saturation.
void bounds(){
 {Bytes ram=zero_ram();putf(ram,0x5418,2,0x50);putf(ram,0x53ee,2,0x40);State s=state(0x19d2c);s.d[7]=0x00200000;Out o;
  assert(run(ram,s,0x19d98,o)&&quiet(o)&&s.a[7]==SP-6&&get(ram,SP-2,2)==0x0020&&get(ram,SP-6,4)==0x19d4c&&s.d[6]==0x40&&s.d[7]==0x40);}
 {Bytes ram=zero_ram();put(ram,SP-2,2,0x0050);putf(ram,0x53f0,2,0x30);State s=state(0x19d4c);s.a[7]=SP-2;s.d[7]=0x12340000;Out o;
  assert(run(ram,s,0x19d98,o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x19d5e&&s.d[7]==0x12340030);}
 {Bytes ram=zero_ram();putf(ram,0x53f2,2,0x7fff);putf(ram,0x53f6,2,0x7fff);putf(ram,0x53f4,2,0x8000);putf(ram,0x53f8,2,0x0030);
  State s=state(0x19da0);s.d[0]=0x00100000;s.d[1]=0x00200000;s.d[2]=0xfff00000;s.d[3]=0x00050000;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  assert(s.d[0]==0&&s.d[1]==0x20&&s.d[2]==0x10&&s.d[3]==0x25);
  assert(getf(ram,0x53f2,2)==0&&getf(ram,0x53f6,2)==0x20&&getf(ram,0x53f4,2)==0x10&&getf(ram,0x53f8,2)==0x30);
  // EXG on Y as well, then no store when inside.
  s=state(0x19da0);s.d[0]=0;s.d[1]=0x00200000;s.d[2]=0;s.d[3]=0xfff00000;assert(run(ram,s,STOP,o)&&s.d[1]==0x10&&s.d[3]==0x20);
  assert(getf(ram,0x53f2,2)==0&&getf(ram,0x53f6,2)==0x10&&getf(ram,0x53f4,2)==0x10&&getf(ram,0x53f8,2)==0x30);}
 // BVC: positive and negative 16-bit overflow saturate to 7fff; mixed signs never overflow.
 {Bytes ram=zero_ram();putf(ram,0x53a2,2,0x7000);putf(ram,0x53f2,2,0x1234);putf(ram,0x53f4,2,0x7000);
  putf(ram,0x53a6,2,0x8000);putf(ram,0x53f6,2,0x0001);putf(ram,0x53f8,2,0x8000);State s=patterned(0x19d5e);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  assert(getf(ram,0x53f2,2)==0x8234&&getf(ram,0x53f4,2)==0x7fff&&getf(ram,0x53f6,2)==0x8001&&getf(ram,0x53f8,2)==0x7fff);
  assert(s.d[0]==0xabcd7fffU&&s.d[1]==0xabce7fffU);
  putf(ram,0x53a2,2,0x10);putf(ram,0x53f4,2,0x20);putf(ram,0x53a6,2,0x10);putf(ram,0x53f8,2,0xfff0);s=patterned(0x19d5e);
  assert(run(ram,s,STOP,o)&&getf(ram,0x53f4,2)==0x170&&getf(ram,0x53f8,2)==0x0100&&s.d[1]==0xabce0100U);}
}
// 1a3d6 shake amplitudes (00080000 fff80000 7fffffff 80000000) and both clamps; 1a526 substitution / unsigned min-max.
void shake(){
 const std::uint32_t rows[][4]={{0x00080000,0xfff88000,0xfff9,0x0000fff9},{0xfff80000,0x00078000,0x0008,0x00000008},
  {0x7fffffff,0x88000000,0xfff8,0xfffffff8},{0x80000000,0x78000000,0x0008,0x00000008}};
 for(unsigned int i=0;i<4;++i){Bytes ram=zero_ram();putf(ram,0x5408,4,rows[i][0]);putf(ram,0x5404,2,0x1234);State s=patterned(0x1a3d6);Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&getf(ram,0x5408,4)==rows[i][1]&&getf(ram,0x5404,2)==rows[i][2]&&getf(ram,0x5406,2)==0x1234&&s.d[0]==rows[i][3]);}
 {Bytes ram=zero_ram();putf(ram,0x541e,2,0x300);putf(ram,0x5440,2,0x200);putf(ram,0x5420,2,0x10);putf(ram,0x5442,2,0x20);
  putf(ram,0x5444,2,1);putf(ram,0x5448,2,2);putf(ram,0x5446,2,0x8000);putf(ram,0x544a,2,9);putf(ram,0x5428,2,3);putf(ram,0x542c,2,4);
  putf(ram,0x543e,2,1);putf(ram,0x544c,2,5);State s=patterned(0x1a526);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  assert(getf(ram,0x53ee,2)==0x200&&getf(ram,0x53f0,2)==0x10&&getf(ram,0x53d6,2)==1&&getf(ram,0x53da,2)==2&&getf(ram,0x53d8,2)==3&&getf(ram,0x53dc,2)==4&&getf(ram,0x53fa,2)==5);
  assert(s.d[0]==0xabcd0005U&&s.d[1]==0xabce0004U&&s.d[2]==0xabcf0020U);}
 // 19b96 memory SUB.W and the 19be4/19c06 fixed deltas (stop at the 19832 call).
 {Bytes ram=zero_ram();putf(ram,0x53bc,4,0x00500000);putf(ram,0x53c0,4,0xfff00000);putf(ram,0x53a2,2,0x10);putf(ram,0x53a6,2,0x20);
  putf(ram,0x53ce,2,0x0100);putf(ram,0x53d0,2,0x0005);putf(ram,0x53d2,2,0x8000);putf(ram,0x53d4,2,0x7fff);putf(ram,0x53fc,4,0x00018000);putf(ram,0x5400,4,0xffff0000);
  State s=patterned(0x19b96);Out o;assert(run(ram,s,0x19832,o)&&quiet(o));
  assert(getf(ram,0x53ce,2)==0x00a0&&getf(ram,0x53d0,2)==0xfff5&&getf(ram,0x53d2,2)==0x7fa0&&getf(ram,0x53d4,2)==0x7fef);
  assert(s.d[4]==0xabd10060U&&s.d[5]==0xabd20010U&&getf(ram,0x53de,4)==0x00018000&&getf(ram,0x53c4,4)==0x00518000&&getf(ram,0x53e2,4)==0xffff0000);
  assert(getf(ram,0x53c8,4)==0xffef0000&&s.d[7]==0xffef0000&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x19c22);}
 // Approval tests 19c72..19cca with null motion (19cd6 accept / 19ce6 reject).
 struct Row {std::uint32_t flags,target_x,target_y,low_x,high_x,low_y,high_y;bool accept;};
 const Row rows2[]={{1,0x51,0x30,0x2c,0,0,0,true},{1,0x51,0x30,0x2b,0,0,0,false},{1,0x4f,0x30,0,0x113,0,0,true},{1,0x4f,0x30,0,0x115,0,0,false},
  {2,0x50,0x31,0,0,0x18,0,true},{2,0x50,0x31,0,0,0x17,0,false},{2,0x50,0x2f,0,0,0,0xb7,true},{2,0x50,0x2f,0,0,0,0xb8,false},{3,0x50,0x30,0,0,0,0,true}};
 for(unsigned int i=0;i<sizeof(rows2)/sizeof(rows2[0]);++i){Bytes ram=zero_ram();putf(ram,0x53cc,1,rows2[i].flags);
  putf(ram,0x53bc,4,0x00500000);putf(ram,0x53c0,4,0x00300000);putf(ram,0x53b8,2,rows2[i].target_x);putf(ram,0x53ba,2,rows2[i].target_y);
  putf(ram,0x53de,4,0x11);putf(ram,0x53e2,4,0x22);
  putf(ram,0x53ce,2,rows2[i].low_x);putf(ram,0x53d2,2,rows2[i].high_x);putf(ram,0x53d0,2,rows2[i].low_y);putf(ram,0x53d4,2,rows2[i].high_y);
  State s=state(0x19c5c);Out o;assert(run(ram,s,0x19cee,o)&&quiet(o));
  const bool accepted=getf(ram,0x53de,4)==0x11;
  if(accepted!=rows2[i].accept)std::cerr<<"approval "<<i<<"\n";assert(accepted==rows2[i].accept);
  assert(accepted?(getf(ram,0x53e2,4)==0x22&&getf(ram,0x53bc,4)==(rows2[i].target_x<<16)&&getf(ram,0x53c0,4)==(rows2[i].target_y<<16)):
   (getf(ram,0x53e2,4)==0&&getf(ram,0x53bc,4)==0x00500000&&getf(ram,0x53c0,4)==0x00300000));}
}
// One block under the generic fixture: {pc, next with incoming C Clear, next with C Set} (from the original bytes).
const std::uint32_t TABLE[][3]={
 {0x197da,0x197e6,0x197e6},{0x197e6,STOP,STOP},{0x197ec,0x197f6,0x197f6},{0x197f6,0x197ec,0x197ec},{0x197fc,STOP,STOP},{0x19802,0x1980e,0x1980e},
 {0x1980e,STOP,STOP},{0x19832,0x1983e,0x1983e},{0x1983e,STOP,STOP},{0x198ee,0x198fa,0x198fa},{0x198fa,STOP,STOP},{0x19978,0x198ee,0x198ee},
 {0x1997c,0x1998e,0x1998e},{0x19984,STOP,STOP},{0x1998e,0x19998,0x19998},{0x19996,0x19998,0x19998},{0x19998,0x199a0,0x199a0},{0x199a0,0x199a4,0x199a4},
 {0x199a4,0x199b0,0x199b0},{0x199ac,0x199b0,0x199b0},{0x199b0,0x199ba,0x199ba},{0x199b8,0x199ba,0x199ba},{0x199ba,0x199c2,0x199c2},{0x199c2,0x199c6,0x199c6},
 {0x199c6,0x199d2,0x199d2},{0x199ce,0x199d2,0x199d2},{0x199d2,STOP,STOP},{0x19a40,0x19a60,0x19a60},{0x19a60,0x19a62,0x19a62},{0x19a62,0x19a6a,0x19a6a},
 {0x19a68,0x19a6a,0x19a6a},{0x19a6a,0x19a74,0x19a74},{0x19a74,0x19a76,0x19a76},{0x19a76,0x19a7e,0x19a7e},{0x19a7c,0x19a7e,0x19a7e},{0x19a7e,0x19a88,0x19a88},
 {0x19a86,0x19a88,0x19a88},{0x19a88,0x19a90,0x19a90},{0x19a8e,0x19a90,0x19a90},{0x19a90,0x19a98,0x19a98},{0x19a98,0x19a9a,0x19a9a},{0x19a9a,0x19aa8,0x19aa8},
 {0x19aa6,0x19aa8,0x19aa8},{0x19aa8,0x19ab0,0x19ab0},{0x19aae,0x19ab0,0x19ab0},{0x19ab0,0x19aba,0x19aba},{0x19aba,0x19abc,0x19abc},{0x19abc,STOP,STOP},
 {0x19ac8,0x19ae8,0x19ae8},{0x19ae8,0x19aea,0x19aea},{0x19aea,0x19af2,0x19af2},{0x19af0,0x19af2,0x19af2},{0x19af2,0x19afc,0x19afc},{0x19afc,0x19afe,0x19afe},
 {0x19afe,0x19b06,0x19b06},{0x19b04,0x19b06,0x19b06},{0x19b06,0x19b10,0x19b10},{0x19b0e,0x19b10,0x19b10},{0x19b10,0x19b18,0x19b18},{0x19b16,0x19b18,0x19b18},
 {0x19b18,0x19b20,0x19b20},{0x19b20,0x19b22,0x19b22},{0x19b22,0x19b30,0x19b30},{0x19b2e,0x19b30,0x19b30},{0x19b30,0x19b38,0x19b38},{0x19b36,0x19b38,0x19b38},
 {0x19b38,0x19b46,0x19b46},{0x19b46,0x19b48,0x19b48},{0x19b48,STOP,STOP},{0x19b96,0x19bda,0x19bda},{0x19bbe,0x19802,0x19802},{0x19bca,0x19c28,0x19c28},
 {0x19bda,0x19be4,0x19be4},{0x19be4,0x19bf4,0x19bf4},{0x19bf0,0x19a40,0x19a40},{0x19bf4,0x19c06,0x19c06},{0x19c06,0x19c16,0x19c16},{0x19c12,0x19ac8,0x19ac8},
 {0x19c16,0x19832,0x19832},{0x19c22,0x19c28,0x19c28},{0x19c28,0x19c36,0x19c36},{0x19c36,0x19c3c,0x19c3c},{0x19c3c,0x19c3e,0x19c3e},{0x19c3e,0x19c40,0x19c40},
 {0x19c40,0x19c5c,0x19c5c},{0x19c44,0x19c5c,0x19c5c},{0x19c52,0x19c5a,0x19c5a},{0x19c58,0x19c5a,0x19c5a},{0x19c5a,0x19c5c,0x19c5c},{0x19c5c,0x19978,0x19978},
 {0x19c60,0x19c68,0x19c68},{0x19c68,0x19ca0,0x19ca0},{0x19c72,0x19ca0,0x19ca0},{0x19c82,0x19ce6,0x19ce6},{0x19c8e,0x19ca0,0x19ca0},{0x19c92,0x19ca0,0x19ca0},
 {0x19ca0,0x19cd6,0x19cd6},{0x19caa,0x19cd6,0x19cd6},{0x19cba,0x19ce6,0x19ce6},{0x19cc6,0x19cd6,0x19cd6},{0x19cca,0x19cd6,0x19cd6},{0x19cd6,0x19cee,0x19cee},
 {0x19ce6,0x19cee,0x19cee},{0x19cee,STOP,STOP},{0x19d08,0x19802,0x19802},{0x19d2c,0x19d3c,0x19d3c},{0x19d3c,0x19d40,0x19d40},{0x19d40,0x19d48,0x19d48},
 {0x19d46,0x19d48,0x19d48},{0x19d48,0x19d98,0x19d98},{0x19d4c,0x19d56,0x19d56},{0x19d56,0x19d5a,0x19d5a},{0x19d5a,0x19d98,0x19d98},{0x19d5e,0x19d76,0x19d76},
 {0x19d72,0x19d76,0x19d76},{0x19d76,0x19d92,0x19d92},{0x19d8e,0x19d92,0x19d92},{0x19d92,STOP,STOP},{0x19d98,0x198ee,0x198ee},{0x19da0,0x19db4,0x19db4},
 {0x19db2,0x19db4,0x19db4},{0x19db4,0x19dbc,0x19dbc},{0x19dba,0x19dbc,0x19dbc},{0x19dbc,0x19dc8,0x19dc8},{0x19dc4,0x19dc8,0x19dc8},{0x19dc8,0x19dd4,0x19dd4},
 {0x19dd0,0x19dd4,0x19dd4},{0x19dd4,0x19de0,0x19de0},{0x19ddc,0x19de0,0x19de0},{0x19de0,0x19dec,0x19dec},{0x19de8,0x19dec,0x19dec},{0x19dec,STOP,STOP},
 {0x1a26a,0x1a276,0x1a276},{0x1a276,STOP,STOP},{0x1a278,0x1a284,0x1a284},{0x1a284,0x1a292,0x1a292},{0x1a28a,STOP,STOP},{0x1a292,0x1a0b6,0x1a0b6},
 {0x1a296,0x1a278,0x1a278},{0x1a29c,STOP,STOP},{0x1a29e,0x197da,0x197da},{0x1a2a6,STOP,STOP},{0x1a2b4,0x1a2cc,0x1a2cc},{0x1a2c0,0x1a2d4,0x1a2d4},
 {0x1a2c6,0x1a2d2,0x1a2ca},{0x1a2ca,0x1a29e,0x1a29e},{0x1a2cc,STOP,STOP},{0x1a2d2,STOP,STOP},{0x1a2d4,0x1a2e0,0x1a2e0},{0x1a2d8,0x1a334,0x1a334},
 {0x1a2dc,0x1a2f2,0x1a2f2},{0x1a2e0,STOP,STOP},{0x1a2f2,0x1a3a0,0x1a3a0},{0x1a2fa,0x1a34c,0x1a34c},{0x1a302,0x1a314,0x1a306},{0x1a306,0x1a34c,0x1a34c},
 {0x1a30e,0x1a314,0x1a312},{0x1a312,STOP,STOP},{0x1a314,0x1a34c,0x1a34c},{0x1a320,0x1a332,0x1a324},{0x1a324,0x1a34c,0x1a34c},{0x1a32c,0x1a332,0x1a330},
 {0x1a330,STOP,STOP},{0x1a332,STOP,STOP},{0x1a334,0x1a3a0,0x1a3a0},{0x1a33c,0x1a34c,0x1a34c},{0x1a344,0x1a3a0,0x1a348},{0x1a348,0x1a34c,0x1a34c},
 {0x1a34c,0x289e,0x289e},{0x1a352,0x1a356,0x1a35c},{0x1a356,STOP,STOP},{0x1a35c,0x1a3a0,0x1a3a0},{0x1a366,0x1a384,0x1a384},{0x1a384,0x1a3a0,0x1a3a0},
 {0x1a38a,0x1a394,0x1a394},{0x1a394,0x1a3a0,0x1a3a0},{0x1a39a,STOP,STOP},{0x1a3a0,STOP,STOP},{0x1a3d6,0x1a3f8,0x1a3f8},{0x1a3f6,0x1a3f8,0x1a3f8},
 {0x1a3f8,0x1a402,0x1a402},{0x1a400,0x1a402,0x1a402},{0x1a402,STOP,STOP},{0x1a442,0x1a44e,0x1a44e},{0x1a44e,STOP,STOP},{0x1a450,0x1a45c,0x1a45c},
 {0x1a45a,STOP,STOP},{0x1a45c,0x1a466,0x1a466},{0x1a464,STOP,STOP},{0x1a466,0x1a470,0x1a470},{0x1a46a,STOP,STOP},{0x1a526,0x1a538,0x1a538},
 {0x1a538,0x1a53a,0x1a53a},{0x1a53a,0x1a544,0x1a544},{0x1a544,0x1a546,0x1a546},{0x1a546,0x1a566,0x1a566},{0x1a55e,0x1a566,0x1a566},{0x1a566,0x1a586,0x1a586},
 {0x1a57e,0x1a586,0x1a586},{0x1a586,0x1a59e,0x1a59e},{0x1a59a,0x1a59e,0x1a59e},{0x1a59e,STOP,STOP},{0x1a73c,0x1a2b4,0x1a2b4},{0x1a756,0x1a75e,0x1a75a},
 {0x1a75a,0x1a26a,0x1a26a},{0x1a75e,0x1a526,0x1a526},{0x1a762,0x19b96,0x19b96},{0x1a766,0x19d08,0x19d08},{0x1a76a,0x19802,0x19802},{0x1a776,0x1a780,0x1a780},
 {0x1a780,0x1a784,0x1a784},{0x1a784,0x1a3d6,0x1a3d6},{0x1a788,0x1a7a8,0x1a7a8},{0x1a78c,0x1a442,0x1a442},{0x1a790,STOP,STOP}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
// FLOW_ONLY blocks (BSR/JSR/BRA/RTS/LEA/MOVEA/BTST/Bcc only) keep the incoming C.
const std::uint32_t KEEP[]={
 0x19978,0x199d2,0x19bda,0x19bf0,0x19c12,0x19c40,0x19c5c,0x19c68,0x19c8e,0x19ca0,0x19cc6,0x19d48,0x19d5a,0x19dec,0x1a276,0x1a292,
 0x1a29c,0x1a2c6,0x1a2ca,0x1a2d2,0x1a2d4,0x1a2d8,0x1a2dc,0x1a2fa,0x1a302,0x1a306,0x1a30e,0x1a312,0x1a314,0x1a320,0x1a324,0x1a32c,
 0x1a330,0x1a332,0x1a33c,0x1a344,0x1a348,0x1a34c,0x1a352,0x1a35c,0x1a44e,0x1a45a,0x1a464,0x1a466,0x1a756,0x1a75a,0x1a75e,0x1a762,
 0x1a766,0x1a784,0x1a788,0x1a78c};
const unsigned int KEEPS=sizeof(KEEP)/sizeof(KEEP[0]);
// Conditional branches bundled with their flag producer (never block starts).
const std::uint32_t BUNDLED[]={
 0x197e2,0x197f2,0x1980a,0x1983a,0x198f6,0x19980,0x19992,0x1999c,0x199a8,0x199b4,0x199be,0x199ca,0x19a5c,0x19a64,0x19a70,0x19a78,
 0x19a82,0x19a8a,0x19a94,0x19aa2,0x19aaa,0x19ab6,0x19ae4,0x19aec,0x19af8,0x19b00,0x19b0a,0x19b12,0x19b1c,0x19b2a,0x19b32,0x19b42,
 0x19bba,0x19be0,0x19c02,0x19c24,0x19c32,0x19c38,0x19c4e,0x19c54,0x19c64,0x19c6e,0x19c7a,0x19c7e,0x19c8a,0x19c9c,0x19ca6,0x19cb2,
 0x19cb6,0x19cc2,0x19cd2,0x19d38,0x19d42,0x19d52,0x19d6e,0x19d8a,0x19dae,0x19db6,0x19dc0,0x19dcc,0x19dd8,0x19de4,0x1a272,0x1a280,
 0x1a286,0x1a2bc,0x1a2f6,0x1a338,0x1a362,0x1a380,0x1a386,0x1a390,0x1a396,0x1a3f2,0x1a3fc,0x1a44a,0x1a456,0x1a460,0x1a534,0x1a540,
 0x1a55a,0x1a57a,0x1a596,0x1a77c};
const std::uint32_t CONSUMERS[]={0x1a756,0x1a2c6,0x1a302,0x1a30e,0x1a320,0x1a32c,0x1a344,0x1a352};
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
void errors(){
 for(unsigned int i=0;i<8;++i){Bytes ram=zero_ram();State s=state(CONSUMERS[i]);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"scene core caller requires known carry");}
 // Odd A0/A1/A5/A7 accesses (WORD/LONG reads, writes, stack pushes and pops).
 struct Odd {std::uint32_t pc;unsigned int reg;const char*message;};
 const Odd odd[]={{0x1a2c0,1,"even WORD/LONG"},{0x1a2e0,1,"even WORD/LONG"},{0x197ec,1,"even WORD/LONG"},{0x197fc,1,"even WORD/LONG"},
  {0x1a284,1,"even WORD/LONG"},{0x1a366,1,"even WORD/LONG"},{0x1a366,0,"even WORD/LONG"},{0x1a450,0,"even WORD/LONG"},{0x1a34c,0,"even WORD/LONG"},
  {0x1a526,5,"even WORD/LONG"},{0x1a73c,5,"alignment"},{0x1a29e,5,"alignment"},{0x1a73c,7,"even WORD/LONG"},{0x19d2c,7,"even WORD/LONG"},
  {0x19d4c,7,"even WORD/LONG"},{0x1a2d2,7,"even WORD/LONG"}};
 for(unsigned int i=0;i<sizeof(odd)/sizeof(odd[0]);++i){Bytes ram=zero_ram();State s=state(odd[i].pc);
  if(odd[i].reg==0)s.a[0]|=1U;else if(odd[i].reg==1)s.a[1]|=1U;else if(odd[i].reg==5)s.a[5]|=1U;else s.a[7]|=1U;
  reject(ram,s,STOP,odd[i].message);}
 // Odd pointers loaded from RAM, failing after earlier writes (including the 1a73c PVC writes): full rollback.
 {Bytes ram=natural_ram();putf(ram,0x5412,4,SCR+1);reject(ram,state(0x1a73c),0x1a7a8,"even WORD/LONG");}
 {Bytes ram=cond_ram(0);putf(ram,0x5418,2,0x1111);putf(ram,0x53b4,4,MOT+1);reject(ram,state(0x1a2b4),STOP,"even WORD/LONG");}
 {Bytes ram=zero_ram();putf(ram,0x540e,4,PL+1);reject(ram,state(0x1a442),STOP,"even WORD/LONG");}
 {Bytes ram=cond_ram(4);putf(ram,0x5422,4,COND+1);reject(ram,state(0x1a73c),0x1a7a8,"even WORD/LONG");}
 // A5-relative store into the fixed ROM area.
 {Bytes ram=zero_ram();State s=state(0x1a29e);s.a[5]=0x10000;reject(ram,s,STOP,"unsupported animation machine write device");}
 // Interior and bundled PCs in the routed ranges.
 const std::uint32_t ranges[][2]={{0x197da,0x19812},{0x19832,0x19844},{0x198ee,0x19910},{0x19978,0x199d4},{0x19a40,0x19b50},{0x19b96,0x19dee},
  {0x1a26a,0x1a3a6},{0x1a3d6,0x1a40e},{0x1a442,0x1a470},{0x1a526,0x1a5a4},{0x1a73c,0x1a7a8}};
 unsigned int interior=0,bytes=0;
 for(unsigned int i=0;i<11;++i){bytes+=ranges[i][1]-ranges[i][0];for(std::uint32_t pc=ranges[i][0];pc<ranges[i][1];pc+=2){
  if(listed(pc))continue;Bytes ram=zero_ram();reject(ram,state(pc),STOP,"unsupported animation scene core PC");++interior;}}
 assert(bytes==1724&&interior==647); // 862 even PCs minus 215 block starts
 const unsigned int nb=sizeof(BUNDLED)/sizeof(BUNDLED[0]);assert(nb==84);
 for(unsigned int i=0;i<nb;++i){assert(!listed(BUNDLED[i]));Bytes ram=zero_ram();reject(ram,state(BUNDLED[i]),STOP,"unsupported animation scene core PC");}
 // Neighbours outside the ranges and the remaining boundaries (19812/19844/19910 belong to U3); odd PCs are rejected first.
 const std::uint32_t outside[]={0x197d8,0x19768,0x19938,0x19976,0x199d4,0x19a3e,0x19b50,0x19b94,0x19dee,0x1a268,
  0x1a3a6,0x1a3d4,0x1a40e,0x1a440,0x1a470,0x1a524,0x1a5a4,0x1a73a,0x1a7a8,0x1a0b6};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram=zero_ram();reject(ram,state(outside[i]),STOP,"unsupported animation machine PC");}
 {Bytes ram=zero_ram();reject(ram,state(0x1a73d),STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int c=0;c<3;++c)for(unsigned int i=0;i<ROWS;++i){Bytes ram=zero_ram();State s=state(TABLE[i][0]);s.carry=carry_of(c);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,TABLE[i][0],o)&&same(s,old)&&ram==before&&quiet(o));}
}
void carry(){
 assert(ROWS==215&&KEEPS==52);unsigned int keeps=0;
 for(unsigned int i=0;i<ROWS;++i){const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,KEEPS,pc);if(keep)++keeps;
  const bool consumer=TABLE[i][1]!=TABLE[i][2];assert(consumer==member(CONSUMERS,8,pc)&&(!consumer||keep));
  for(unsigned int c=0;c<3;++c){if(consumer&&c==0)continue; // errors()
   Bytes ram=zero_ram();State s=state(pc);s.carry=carry_of(c);const std::uint32_t stop=c==2?TABLE[i][2]:TABLE[i][1];Out o;
   if(!run(ram,s,stop,o)||s.pc!=stop)std::cerr<<std::hex<<"row "<<pc<<"\n";
   assert(s.pc==stop&&o.reads==0&&o.status==ms5::AnimationMachineReturned);
   assert(o.ports.size()==((pc==0x1a73c||pc==0x1a790)?2U:0U));
   ms5::AnimationCarryState expect=keep?carry_of(c):ms5::AnimationCarryUnknown;
   if(pc==0x1a2cc||pc==0x1a356||pc==0x1a39a)expect=ms5::AnimationCarrySet;
   if(pc==0x1a3a0)expect=ms5::AnimationCarryClear;
   if(pc==0x1a2e0)expect=ms5::AnimationCarrySet; // D0.W=0 not below 541e=0: CMP C=0, EORI -> 1
   if(s.carry!=expect)std::cerr<<std::hex<<"carry row "<<pc<<"\n";assert(s.carry==expect);}}
 assert(keeps==KEEPS);
 // 1a2e0 with phase below 541e: CMP borrow 1, EORI -> Clear.
 {Bytes ram=zero_ram();putf(ram,0x541e,2,1);State s=state(0x1a2e0);Out o;assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarryClear);}
}
}
int main(){natural();tail();motion();script();conditions();motion_list();axis();clamp();follow();bounds();shake();errors();zero_step();carry();
 std::cout<<"animation_machine_scene_core_test PASS "<<std::dec<<calls<<" API invocations\n";}
