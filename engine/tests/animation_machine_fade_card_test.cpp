#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000,OBJ=0x102000,BIOS=0xc00468;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=OBJ;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const Bytes*vectors=NULL){++calls;ms5::ProgramBusState bus;bus.vectors=vectors;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message,const Bytes*vectors=NULL){const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;assert(!run(ram,s,stop,o,vectors));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
void preserving(){
 const std::uint32_t cs[][3]={{0x48058,0x8c16,0x4805e},{0x4807e,0x8c16,0x48084},{0x4809a,0xcaf0,0x480a0},{0x480a0,0xc364,0x480a6},{0xc376,BIOS,0xc37c},{0xc39c,0x28ae,0xc3a2},{0x2a00,0x299c,0x2a02},{0x2ac0,0x4806a,0x2ac2}};
 const std::uint32_t jumps[][2]={{0x480b6,0x2a00},{0x2a06,0x2ac2},{0x2ac6,0x2ab8},{0x28ae,0x28b4},{0xc37e,0xc384},{0x2ab8,0x2abe}};
 const std::uint32_t rt[]={0x48072,0x48098,0x480b4,0xc3b6,0xc3be,0x290c,0x2916};
 for(unsigned int carry=0;carry<3;++carry){
  for(unsigned int i=0;i<sizeof(cs)/sizeof(cs[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(cs[i][0]);s.a[0]=0x4806a;s.carry=carry_of(carry);Out o;assert(run(ram,s,cs[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==cs[i][2]&&o.ports.empty());}
  for(unsigned int i=0;i<sizeof(jumps)/sizeof(jumps[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(jumps[i][0]);s.a[5]=0x87654320;s.carry=carry_of(carry);Out o;assert(run(ram,s,jumps[i][1],o)&&s.carry==carry&&s.a[7]==SP);if(jumps[i][0]==0x28ae||jumps[i][0]==0xc37e||jumps[i][0]==0x2ab8)assert(s.a[5]==0x108000);}
  for(unsigned int i=0;i<sizeof(rt)/sizeof(rt[0]);++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rt[i]);s.carry=carry_of(carry);Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  // MOVEA blocks: live LONG loads into A0/A6/A7 without touching C.
  Bytes ram(65536,0);put(ram,OBJ,4,0x480ac);put(ram,OBJ+8,4,0x102400);put(ram,SP,4,0x102600);put(ram,0x104ca4,4,0x1fe000);
  ms5::AnimationMachineState s=state(0x2abe);s.carry=carry_of(carry);Out o;assert(run(ram,s,0x2ac0,o)&&s.a[0]==0x480ac&&s.carry==carry);
  s=state(0x2ac2);s.carry=carry_of(carry);assert(run(ram,s,0x2ac6,o)&&s.a[6]==0x102400&&s.carry==carry);
  s=state(0xc37c);s.carry=carry_of(carry);assert(run(ram,s,0xc37e,o)&&s.a[6]==0x102600&&s.a[7]==SP+4&&s.carry==carry);
  s=state(0x2a02);s.carry=carry_of(carry);assert(run(ram,s,0x2a06,o)&&s.a[7]==0x1fe000&&s.carry==carry);
  // Known CCR immediates: ORI #1 sets C, LEA plus ANDI #fe clears C.
  s=state(0x2908);s.carry=carry_of(carry);assert(run(ram,s,0x290c,o)&&s.carry==ms5::AnimationCarrySet);
  s=state(0x290e);s.carry=carry_of(carry);assert(run(ram,s,0x2916,o)&&s.carry==ms5::AnimationCarryClear&&s.a[0]==0x100e98);
 }
 // MOVE/MOVEQ/CLR/SUBQ/TST/CMP blocks do not retain caller C.
 const std::uint32_t unknown[][2]={{0x4804e,0x48058},{0x4805e,0x4806a},{0x4806a,0x48072},{0x48074,0x4807e},{0x48084,0x48090},{0x48090,0x48098},{0x480a6,0x480ac},{0x480ac,0x480b4},
  {0xc364,0xc376},{0xc384,0xc38e},{0xc38e,0xc39c},{0xc3a2,0xc3b6},{0xc3b8,0xc3be},{0x28b4,0x28be},{0x28be,0x28c6},{0x28c6,0x28d2},{0x28d2,0x28da},{0x28da,0x28de},{0x28de,0x2908}};
 for(unsigned int i=0;i<sizeof(unknown)/sizeof(unknown[0]);++i){Bytes ram(65536,0);put(ram,OBJ+0x7a,2,5);put(ram,0x104ca0,2,1);put(ram,0x104c9c,4,0x103000);put(ram,OBJ+8,4,0x102200);put(ram,SP,4,0xc250);
  ms5::AnimationMachineState s=state(unknown[i][0]);s.a[0]=0x103000;s.d[0]=0;Out o;assert(run(ram,s,unknown[i][1],o)&&s.carry==ms5::AnimationCarryUnknown);}
}
void sequence(){
 // Post-map entry: MOVEQ/MOVE.W setup, actual 8c16 leaf, timer arm, first RTS.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x107dc2,2,0x100);ms5::AnimationMachineState s=state(0x4804e);const std::uint32_t d4=s.d[4];Out o;
 assert(run(ram,s,0x8c16,o)&&s.d[0]==0&&s.d[1]==0&&s.d[2]==0&&s.d[3]==0xabd00040U&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x4805e);
 assert(run(ram,s,STOP,o)&&s.pc==STOP&&s.a[7]==SP+4&&s.a[5]==0x108000&&s.d[4]==d4&&s.d[0]==0xfffc&&s.d[3]==0x40&&get(ram,0x107dce,2)==0xfffc&&get(ram,0x107dd4,1)==0x40);
 assert(get(ram,OBJ+0x7a,2)==0x7f&&get(ram,OBJ,4)==0x4806a&&o.ports.empty()&&o.status==ms5::AnimationMachineReturned&&s.carry==ms5::AnimationCarryUnknown);
 Bytes continuous(65536,0);put(continuous,SP,4,STOP);put(continuous,0x107dc2,2,0x100);ms5::AnimationMachineState whole=state(0x4804e);Out w;assert(run(continuous,whole,STOP,w)&&same(whole,s)&&continuous==ram);
}
void timers(){
 // Entry with 7a=0 wraps to ffff and returns; 7a=1 takes the second-fade path in the same call.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x4806a);Out o;assert(run(ram,s,STOP,o)&&get(ram,OBJ+0x7a,2)==0xffff&&s.a[7]==SP+4&&o.ports.empty());
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,OBJ+0x7a,2,1);s=state(0x4806a);const std::uint32_t d3=s.d[3]&0xffff0000U;o=Out();assert(run(ram,s,0x4807e,o)&&s.d[0]==0xffffffe1U&&s.d[1]==0xffffffe1U&&s.d[2]==0xffffffe1U&&s.d[3]==(d3|0x20)&&get(ram,OBJ+0x7a,2)==0);
 assert(run(ram,s,STOP,o)&&s.a[7]==SP+4&&get(ram,OBJ+0x7a,2)==0x1f&&get(ram,OBJ,4)==0x48090&&get(ram,0x107dc8,2)==0xe100&&get(ram,0x107dce,2)==0xff08&&s.d[0]==0xff08&&s.d[3]==0x20);
 // Second timer: 0/1/2 entries.
 for(unsigned int t=0;t<3;++t){ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,OBJ+0x7a,2,t);s=state(0x48090);o=Out();assert(run(ram,s,t==1?0x4809a:STOP,o)&&get(ram,OBJ+0x7a,2)==((t-1U)&65535U)&&s.a[7]==(t==1?SP:SP+4));}
}
// Full frame chain: map exit fade, 127 re-entries, second fade, 31 re-entries to the BIOS JSR.
ms5::AnimationMachineState chain(Bytes&ram){
 ram.assign(65536,0);put(ram,SP,4,0x2ac2);put(ram,OBJ+0x6c,1,255);ms5::AnimationMachineState s=state(0x4804e);Out o;
 assert(run(ram,s,0x2ac2,o)&&s.pc==0x2ac2&&s.a[7]==SP+4&&get(ram,OBJ+0x7a,2)==0x7f);
 for(unsigned int k=1;k<=127;++k){s.pc=0x2ab8;o=Out();assert(run(ram,s,0x2ac2,o)&&s.pc==0x2ac2&&s.a[7]==SP+4&&s.a[6]==OBJ&&s.a[5]==0x108000&&s.a[0]==0x4806a&&get(ram,SP,4)==0x2ac2);
  if(k<127)assert(get(ram,OBJ+0x7a,2)==0x7fU-k&&get(ram,OBJ,4)==0x4806a&&o.ports.empty());
  else assert(get(ram,OBJ+0x7a,2)==0x1f&&get(ram,OBJ,4)==0x48090&&get(ram,0x107dc8,2)==0xe100);}
 for(unsigned int k=1;k<31;++k){s.pc=0x2ab8;o=Out();assert(run(ram,s,0x2ac2,o)&&s.a[7]==SP+4&&s.a[0]==0x48090&&get(ram,OBJ+0x7a,2)==0x1fU-k);}
 s.pc=0x2ab8;
 // A stop other than the BIOS entry is a checked error with full rollback.
 reject(ram,s,0x2ac2,"unsupported animation machine PC");
 o=Out();assert(run(ram,s,BIOS,o)&&s.pc==BIOS&&s.a[7]==SP-12&&get(ram,SP-12,4)==0xc37c&&get(ram,SP-8,4)==OBJ&&get(ram,SP-4,4)==0x480a6&&get(ram,SP,4)==0x2ac2);
 assert(get(ram,0x10fdc4,1)==1&&get(ram,0x10fdce,2)==0x268&&get(ram,OBJ+0x7a,2)==0&&get(ram,OBJ,4)==0x48090&&o.ports.size()==2072&&o.status==ms5::AnimationMachineReturned);
 return s;
}
// Declared host fixture: BIOS RTS popped c37c (A7+=4) and one answer BYTE at 10fdc6. No other BIOS effects are modeled.
void resume(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t answer){s.a[7]+=4;s.pc=0xc37c;put(ram,0x10fdc6,1,answer);}
void bios(){
 Bytes base;const ms5::AnimationMachineState stopped=chain(base);
 // Answer 80: 62=ff, 480ac takes 2a00, 299c cleanup, dispatcher A7 reload, BRA 2ac2.
 Bytes ram=base;ms5::AnimationMachineState s=stopped;resume(ram,s,0x80);put(ram,0x104ca4,4,SP+4);Out o;
 assert(run(ram,s,0x2a00,o)&&s.a[6]==OBJ&&s.a[7]==SP&&get(ram,OBJ+0x62,1)==0xff&&get(ram,OBJ,4)==0x480ac&&s.a[5]==0x108000);
 assert(run(ram,s,0x2ac2,o)&&s.pc==0x2ac2&&s.a[7]==SP+4&&s.a[6]==OBJ&&get(ram,OBJ,4)==0x270e&&get(ram,SP-4,4)==0x2a02&&get(ram,OBJ+0x62,1)==0&&o.ports.size()==1&&o.ports[0].address==0x300001);
 // A distinct saved dispatcher SP proves the MOVEA load rather than the BSR return.
 ram=base;s=stopped;resume(ram,s,0x80);put(ram,0x104ca4,4,0x1fe100);o=Out();assert(run(ram,s,0x2ac2,o)&&s.a[7]==0x1fe100);
 // Answer != 80: 62 cleared, 28ae allocation success with known Set.
 for(unsigned int answer=0;answer<2;++answer){
  ram=base;s=stopped;resume(ram,s,answer?0x7f:0);put(ram,0x104ca0,2,2);put(ram,0x104c9c,4,0x103000);put(ram,0x103008,4,0x103400);put(ram,OBJ+8,4,0x102200);put(ram,OBJ+0x10,2,5);put(ram,OBJ+0x6a,1,0x33);put(ram,OBJ+0x62,1,0x44);o=Out();
  assert(run(ram,s,0xc3a2,o)&&s.carry==ms5::AnimationCarrySet&&(s.d[0]&65535U)==6&&s.a[0]==0x103000&&s.a[1]==0x102200&&s.a[6]==OBJ&&s.a[7]==SP-4&&get(ram,OBJ+0x62,1)==0);
  assert(get(ram,0x104c9c,4)==0x103400&&get(ram,0x104ca0,2)==1&&get(ram,0x10300c,4)==OBJ&&get(ram,0x103010,2)==6&&get(ram,0x103004,4)==OBJ&&get(ram,0x103008,4)==0x102200);
  assert(get(ram,0x102204,4)==0x103000&&get(ram,OBJ+8,4)==0x103000&&get(ram,0x103000,4)==0xc250&&get(ram,0x10306a,1)==0x33&&get(ram,SP-12,4)==0xc250&&get(ram,SP-8,4)==0xc3a2);
  assert(run(ram,s,0x2ac2,o)&&s.a[7]==SP+4&&get(ram,0x103076,4)==0xc188&&get(ram,0x10307a,2)==4&&get(ram,0x10307c,2)==4&&get(ram,OBJ,4)==0x480ac&&o.ports.empty());
  // Later frame re-entry at 480ac: TST.B 62 is zero, so it returns.
  s.pc=0x2ab8;const Bytes hold=ram;assert(run(ram,s,0x2ac2,o)&&s.a[0]==0x480ac&&s.a[7]==SP+4&&ram==hold&&o.ports.empty());
 }
 // Free count 0: BCC failure path, A0=100e98 known Clear, c3a2 still writes the dummy record.
 ram=base;s=stopped;resume(ram,s,0);put(ram,0x104ca0,2,0);put(ram,0x104c9c,4,0x103000);o=Out();
 assert(run(ram,s,0xc3a2,o)&&s.carry==ms5::AnimationCarryClear&&s.a[0]==0x100e98&&s.a[7]==SP-4&&get(ram,0x104c9c,4)==0x103000&&get(ram,SP-12,4)==0xc37c&&get(ram,SP-8,4)==0xc3a2);
 assert(run(ram,s,0x2ac2,o)&&get(ram,0x100f0e,4)==0xc188&&get(ram,0x100f12,2)==4&&get(ram,0x100f14,2)==4&&s.a[7]==SP+4);
 // Head 0: read8(0) from the vector view, publish free head, skip SUBQ, then fault on the ROM write c(A0).
 Bytes vectors(128,0);put(vectors,8,4,0x00c00402);
 ram=base;s=stopped;resume(ram,s,0);put(ram,0x104ca0,2,1);put(ram,0x104c9c,4,0);
 reject(ram,s,0x2ac2,"unsupported animation machine write device",&vectors);reject(ram,s,0x2ac2,"vectors");
 Bytes probe=ram;ms5::AnimationMachineState p=s;o=Out();assert(run(probe,p,0x28de,o,&vectors)&&p.a[0]==0&&get(probe,0x104c9c,4)==0x00c00402&&get(probe,0x104ca0,2)==1);
}
void allocation(){
 // A0 0 after CMPA.W #0 (full32-bit compare) fails without push.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x104ca0,2,5);ms5::AnimationMachineState s=state(0x28ae);s.a[0]=0;s.d[0]=0;Out o;assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarryClear&&s.a[0]==0x100e98&&s.a[7]==SP+4);
 s=state(0x28ae);s.a[0]=0x10000;s.d[0]=0;put(ram,0x104c9c,4,0x103000);put(ram,OBJ+8,4,0x102200);o=Out();assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarrySet&&s.a[0]==0x103000);
 // Unsigned WORD comparison ignores D0 upper bits.
 const unsigned int d0[]={0x00000004,0xffff0004,0x00008000,0x12340005};
 for(unsigned int i=0;i<4;++i){ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x104ca0,2,5);put(ram,0x104c9c,4,0x103000);put(ram,OBJ+8,4,0x102200);s=state(0x28ae);s.d[0]=d0[i];o=Out();assert(run(ram,s,STOP,o));assert(s.carry==((d0[i]&65535U)<5?ms5::AnimationCarrySet:ms5::AnimationCarryClear));}
}
void aliases(){
 // 4(A1) overwrites the pushed A0 slot before MOVE.L (A7)+,(A0) pops it.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x104ca0,2,1);put(ram,0x104c9c,4,0x103000);put(ram,OBJ+8,4,SP-8);ms5::AnimationMachineState s=state(0x28ae);s.a[0]=0xc250;s.d[0]=0;Out o;
 assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarrySet&&get(ram,0x103000,4)==0x103000&&s.a[1]==SP-8&&s.a[7]==SP+4);
 // 10(A0) WORD publication rewrites the upper WORD of 8(A6) before MOVEA.L 8(A6),A1.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x104ca0,2,1);put(ram,0x104c9c,4,OBJ-8);put(ram,OBJ,4,0x4806a);put(ram,OBJ+8,4,0x7fff3000);put(ram,OBJ+0x10,2,0xf);put(ram,OBJ+0x6a,1,0x5a);
 s=state(0x28ae);s.a[0]=0xc250;s.d[0]=0xffff0000U;o=Out();
 assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarrySet&&s.a[0]==OBJ-8&&s.a[1]==0x103000&&s.d[0]==0xffff0010U&&get(ram,0x104c9c,4)==0x4806a&&get(ram,0x104ca0,2)==0);
 assert(get(ram,0x103004,4)==OBJ-8&&get(ram,OBJ+8,4)==OBJ-8&&get(ram,OBJ,4)==0x103000&&get(ram,OBJ-8,4)==0xc250&&get(ram,OBJ-4,4)==OBJ&&get(ram,OBJ+4,4)==OBJ&&get(ram,OBJ+0x62,1)==0x5a);
 // MOVE.W 0268 to 10fdce overwrites the low WORD of the pushed A6; c37c pops it live.
 ram.assign(65536,0);put(ram,0x10fdd0,4,STOP);s=state(0xc364);s.a[7]=0x10fdd0;o=Out();
 assert(run(ram,s,BIOS,o)&&s.a[7]==0x10fdc8&&get(ram,0x10fdcc,4)==0x00100268&&get(ram,0x10fdc8,4)==0xc37c);
 resume(ram,s,0x80);o=Out();assert(run(ram,s,STOP,o)&&s.a[6]==0x00100268&&get(ram,0x1002ca,1)==0xff&&s.a[7]==0x10fdd4);
}
void errors(){
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,OBJ,4,0x4806b);
 ms5::AnimationMachineState s=state(0x2ab8);reject(ram,s,0x2ac2,"odd JSR target");
 s=state(0x2ab8);s.a[6]=OBJ+1;reject(ram,s,0x2ac2,"even WORD/LONG");
 s=state(0x4805e);s.a[6]=OBJ+1;reject(ram,s,STOP,"alignment");
 s=state(0x4806a);s.a[6]=OBJ+1;reject(ram,s,STOP,"even WORD/LONG");
 s=state(0x2ac2);s.a[6]=OBJ+1;reject(ram,s,STOP,"even WORD/LONG");
 s=state(0xc364);reject(ram,s,STOP,"unsupported animation machine PC");
 s=state(0xc364);s.a[7]=0x100002;reject(ram,s,BIOS,"RAM");
 put(ram,0x104ca0,2,1);put(ram,0x104c9c,4,0x103001);s=state(0x28ae);s.d[0]=0;reject(ram,s,STOP,"even WORD/LONG");
 const std::uint32_t bundled[]={0x4806e,0x48094,0x480b0,0xc38a,0x28ba,0x28c2,0x28d6,0x48050,0x48064,0xc366,0x28c8,0x2902};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){s=state(bundled[i]);reject(ram,s,STOP,"unsupported animation fade card PC");}
 const std::uint32_t outside[]={0x4aa88,0x2aac,0x2ab2,0x2a04,0x2a08,BIOS}; // 4aa88 has no executor (1a470 is U5 now)
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){s=state(outside[i]);reject(ram,s,STOP,"unsupported animation machine PC");}
}
}
int main(){preserving();sequence();timers();bios();allocation();aliases();errors();std::cout<<"animation_machine_fade_card_test PASS "<<calls<<" API invocations\n";}
