#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
// 480bc frame helper shell (U1) through run_animation_machine only. All inputs are declared RAM
// fixtures; the return LONG of each direct entry is declared at SP. The only ROM bytes read are the U6 default mask
// row 49ab0 (contract bytes 10 20 40 80, synthetic physical row) on the paths that run 49b0c. Whole frames through U7
// (4aa88/e8a48) are covered in detail by animation_machine_buffer_cue_test.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
const std::uint32_t SP=0x10f7fc,STOP=0xff000,RETURN=0x2ac2;
const std::uint32_t P1=0x100cb8,P2=0x100da8,FLAGS=0x10d68e,SOUND_NEW=0x10d490,SOUND_OLD=0x10d491;
const std::uint32_t RING=0x104d82,RING_R=0x104d8a,RING_W=0x104d8c,QUEUE=0x104cf4,QUEUE_R=0x104d74,QUEUE_W=0x104d76;
const std::uint32_t BOX1=0x10dd48,BOX2=0x10dd50,TICK=0x10dd58,AREA1=0x10dd5c,AREA2=0x10dd98,AREA_END=0x10ddd4,BANK=0x10000e;
const std::uint32_t CARD1=0x10dcba,CARD2=0x10dce6,BINS=0x10d646,BIN_Y=0x10d656,BIN_END=0x10d66a,SLOT_COUNT=0x10d67c,SLOT0=0x10d4e6;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void fill(Bytes&b,std::uint32_t a,std::uint32_t end,std::uint32_t v){for(std::uint32_t x=a;x<end;++x)b[x&65535U]=static_cast<std::uint8_t>(v);}
State state(std::uint32_t pc){State s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}
 s.a[5]=0x108000;s.a[6]=0x0010ab00;s.a[7]=SP;return s;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource>w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
// Success: returned (not waiting), no reads/ports/PVC/bank effects.
bool quiet(const Out&o){return o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.error.empty()&&o.ports.empty()&&o.dev.pvc==Out().dev.pvc&&o.dev.bank_base==0x200000;}
// Synthetic physical row for the U6 default mask 49ab0.
std::vector<ms5::PhysicalRomResource> mask_row(){std::vector<ms5::PhysicalRomResource> p(1);p[0].source_rom_offset=0x49ab0;
 const std::uint8_t mask[4]={0x10,0x20,0x40,0x80};p[0].data.assign(mask,mask+4);return p;}
const std::vector<ms5::PhysicalRomResource> MASK_ROW=mask_row();
bool run_rom(Bytes&ram,State&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;bus.physical_rom=&MASK_ROW;std::vector<ms5::FixedDataResource>w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
// U7 needs a RAM ring cursor (10dc88) and 4701e skips every spatial slot with a negative 26 WORD.
void frame_ready(Bytes&ram){put(ram,0x10dc88,4,0x10db88);for(unsigned int i=0;i<8;++i)put(ram,SLOT0+0x2c*i+0x26,4,0xffff0000U);}
// U7 debug slot 0 (10f001 bit7) whose sprite callback LONG 109152 (0) is not the supported cd50.
void bad_callback(Bytes&ram){put(ram,0x10f001,1,0x80);put(ram,0x10daf8,4,0x10e000);put(ram,0x10dafc,4,0x10e100);}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message,const std::vector<ms5::PhysicalRomResource>*physical=NULL){
 const Bytes before=ram;const State old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;
 if(ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error)){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error.find(message)==std::string::npos)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&
  o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
// Stack scratch below SP is compared separately (callers' frames are checked explicitly where they matter).
void stack_from(Bytes&expect,const Bytes&ram){for(std::uint32_t a=SP-64;a<SP;++a)expect[a&65535U]=ram[a&65535U];}
// Player readiness fixture for 289e and 61(A0): 0 = LONG (A0)==270e (C Clear); 1 = not ready, 61 bit7 set;
// 2 = not ready, 61 bit7 clear (BSET the player bit).
void player(Bytes&ram,std::uint32_t p,unsigned int kind){put(ram,p,4,kind==0?0x270eU:(kind==1?0x2710U:0U));put(ram,p+0x61,1,kind==1?0x80:0x7f);}
Bytes natural_ram(unsigned int k1,unsigned int k2){Bytes ram(65536,0);put(ram,SP,4,RETURN);player(ram,P1,k1);player(ram,P2,k2);put(ram,FLAGS,1,0xfc);return ram;}

// 480bc entry from the dispatcher (return LONG 2ac2 at A7) -> 47642 (both players via BSR and fall-through)
// -> JSR 1a73c boundary stop.
void natural(){
 for(unsigned int k1=0;k1<3;++k1)for(unsigned int k2=0;k2<3;++k2)for(unsigned int c=0;c<3;++c){
  Bytes ram=natural_ram(k1,k2);State s=state(0x480bc);s.carry=carry_of(c);const State old=s;Bytes expect=ram;Out o;
  assert(run(ram,s,0x1a73c,o)&&quiet(o));
  State want=old;want.pc=0x1a73c;want.a[7]=SP-4;want.a[0]=P2;want.d[0]=1;want.carry=k2==0?ms5::AnimationCarryClear:ms5::AnimationCarrySet;
  assert(same(s,want));
  put(expect,FLAGS,1,(k1==2?1U:0U)|(k2==2?2U:0U));put(expect,SP-4,4,0x480c6);put(expect,SP-8,4,0x4765c);put(expect,SP-12,4,0x4765c);
  assert(ram==expect&&get(ram,SP,4)==RETURN);}
 // Split at the 47650 fall-through and at the second 47656 body: same final state.
 {Bytes ram=natural_ram(2,2);State s=state(0x480bc);Out o;assert(run(ram,s,0x47650,o)&&s.a[7]==SP-4&&s.a[0]==P1&&s.d[0]==0&&get(ram,FLAGS,1)==1&&s.carry==ms5::AnimationCarrySet);
  assert(run(ram,s,0x47656,o)&&s.a[0]==P2&&s.d[0]==1&&s.carry==ms5::AnimationCarryUnknown);
  assert(run(ram,s,0x1a73c,o)&&get(ram,FLAGS,1)==3&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x480c6);}
 // The whole frame continues through 1a73c (U2 scene core, U4 scene update 1a7a8), 49b0c (U6 input), 4aa88 and e8a48 (U7)
 // and the U1 helpers to the 480f0 RTS (return LONG 2ac2). An unsupported sprite callback in U7 rolls back everything.
 {Bytes ram=natural_ram(2,1);frame_ready(ram);State s=state(0x480bc);Out o;assert(run_rom(ram,s,RETURN,o)&&s.pc==RETURN&&s.a[7]==SP+4&&
   o.status==ms5::AnimationMachineReturned&&get(ram,0x10dc88,4)==0x10dba8&&get(ram,FLAGS,1)==1);}
 {Bytes ram=natural_ram(2,1);frame_ready(ram);bad_callback(ram);reject(ram,state(0x480bc),STOP,"unsupported sprite callback target",&MASK_ROW);}
 reject(natural_ram(2,1),state(0x480bc),STOP,"program bus ROM"); // the 49ab4 default mask read needs the ROM row
}
// Each shell JSR to a helper stops at its entry; from there the frame runs every helper (U2..U7 and the U1 helpers) to the
// 480f0 RTS. An unsupported U7 sprite callback rolls back everything.
void shell(){
 const std::uint32_t edges[][3]={{0x480c0,0x1a73c,0x480c6},{0x480c6,0x49b0c,0x480cc},{0x480cc,0x4aa88,0x480d2},{0x480e4,0xe8a48,0x480ea}};
 for(unsigned int i=0;i<4;++i){Bytes ram(65536,0);put(ram,SP,4,RETURN);State s=state(edges[i][0]);s.carry=ms5::AnimationCarryClear;State want=s;Out o;
  assert(run(ram,s,edges[i][1],o)&&quiet(o));want.pc=edges[i][1];want.a[7]=SP-4;assert(same(s,want)&&get(ram,SP-4,4)==edges[i][2]);
  Bytes full=ram;frame_ready(full);State t=state(edges[i][0]);assert(run_rom(full,t,RETURN,o)&&t.pc==RETURN&&t.a[7]==SP+4&&o.status==ms5::AnimationMachineReturned);
  if(i<3){Bytes bad=ram;frame_ready(bad);bad_callback(bad);reject(bad,state(edges[i][0]),STOP,"unsupported sprite callback target",&MASK_ROW);}}
 // 480d2..480e4: b4a2a (both players Clear), 6f1c2, 4701e (every slot skipped by a negative 26 WORD), then the e8a48 stop.
 Bytes ram(65536,0);put(ram,SP,4,RETURN);for(unsigned int i=0;i<8;++i)put(ram,SLOT0+0x2c*i+0x26,4,0xffff0000U);
 State s=state(0x480d2);Out o;assert(run(ram,s,0x480e4,o)&&quiet(o)&&s.a[7]==SP&&get(ram,SP,4)==RETURN);
 assert(get(ram,BOX1,2)==0x8000&&get(ram,BOX2,2)==0x8000&&get(ram,SLOT_COUNT,2)==0xffff&&s.a[0]==SLOT0-0x2c);
 // 480ea: 2efa6 with no change, then 480f0 RTS to the dispatcher LONG.
 s.pc=0x480ea;assert(run(ram,s,RETURN,o)&&s.a[7]==SP+4&&s.pc==RETURN);
}
// b4a2a: 49392 per player (FLAGS bit), 1c028/4d9d6 (A4 per player, TST.W (A4), 6(A4)), A1 null/non-null,
// 5d58/5d5a tick BYTEs, b481e area by bit0 of WORD 10000e (-7ff2(A5)).
void region(){
 // Case A: both players Clear; ticks 0/5; area 1 cleared.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);fill(ram,BOX1,AREA_END,0xee);put(ram,TICK,1,0);put(ram,TICK+2,1,5);put(ram,BANK,2,0x1234);put(ram,FLAGS,1,0xfc);
  Bytes expect=ram;State s=state(0xb4a2a);const State old=s;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  put(expect,BOX1,2,0x8000);put(expect,BOX2,2,0x8000);put(expect,TICK+2,1,4);for(std::uint32_t a=AREA1;a<AREA2;a+=10)put(expect,a,2,0);
  stack_from(expect,ram);assert(ram==expect);
  State want=old;want.pc=STOP;want.a[7]=SP+4;want.d[0]=0;want.a[0]=TICK+4;want.a[1]=AREA2;want.a[2]=AREA2;want.carry=ms5::AnimationCarryUnknown;assert(same(s,want));}
 // Case B: both Set. P1: TST.W (CARD1)=0 -> A0=0 -> A0=P1, A1=LONG 56(P1). P2: (CARD2)!=0, 6(CARD2)=2000 ->
 // A0=(A6 upper WORD)|2000, A1=LONG 8(CARD2). MOVEM.W sign-extends; ADD.W 42/46(A0) are WORD adds.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);fill(ram,BOX1,AREA_END,0xee);put(ram,TICK,1,1);put(ram,TICK+2,1,0);put(ram,BANK,2,0xffff);put(ram,FLAGS,1,3);
  put(ram,P1+0x56,4,0x10e100);put(ram,P1+0x42,2,0x0100);put(ram,P1+0x46,2,0x0005);put(ram,0x10e100,4,0x0010fff0);put(ram,0x10e104,4,0x00208001);
  put(ram,CARD2,2,1);put(ram,CARD2+6,2,0x2000);put(ram,CARD2+8,4,0x10e200);put(ram,0x10e200,4,0x7fff0001);put(ram,0x10e204,4,0xff000002);
  put(ram,0x102042,2,0x0001);put(ram,0x102046,2,0x7fff);
  Bytes expect=ram;State s=state(0xb4a2a);const State old=s;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  put(expect,BOX1,4,0x0110fff5);put(expect,BOX1+4,4,0x00208001);put(expect,BOX2,4,0x80008000);put(expect,BOX2+4,4,0xff000002);
  put(expect,TICK,1,0);for(std::uint32_t a=AREA2;a<AREA_END;a+=10)put(expect,a,2,0);stack_from(expect,ram);assert(ram==expect);
  State want=old;want.pc=STOP;want.a[7]=SP+4;want.d[0]=0;want.d[1]=0x8000;want.d[2]=0xffffff00U;want.d[3]=2;want.a[0]=TICK+4;want.a[1]=AREA_END;want.a[2]=AREA_END;
  want.a[4]=CARD2;want.carry=ms5::AnimationCarryUnknown;assert(same(s,want));}
 // Case C: P1 Set with (CARD1)!=0 and 6(CARD1)=0 -> A0=0 -> A1=LONG 56(P1)=0 (no store); P2 Clear.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);fill(ram,BOX1,BOX2+8,0xee);put(ram,FLAGS,1,1);put(ram,CARD1,2,0x8000);put(ram,CARD1+8,4,0x10e100);
  Bytes expect=ram;State s=state(0xb4a2a);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  put(expect,BOX1,2,0x8000);put(expect,BOX2,2,0x8000);for(std::uint32_t a=AREA1;a<AREA2;a+=10)put(expect,a,2,0);stack_from(expect,ram);
  assert(ram==expect&&s.a[4]==CARD1&&s.a[1]==AREA2);}
 // Case D: P1 Clear; P2 Set with (CARD2)!=0, 6(CARD2)!=0, LONG 8(CARD2)=0 -> CMPA.W #0,A1 equal (no store).
 {Bytes ram(65536,0);put(ram,SP,4,STOP);fill(ram,BOX1,BOX2+8,0xee);put(ram,FLAGS,1,2);put(ram,CARD2,2,0x0001);put(ram,CARD2+6,2,0x1234);put(ram,BANK,2,1);
  Bytes expect=ram;State s=state(0xb4a2a);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  put(expect,BOX1,2,0x8000);put(expect,BOX2,2,0x8000);for(std::uint32_t a=AREA2;a<AREA_END;a+=10)put(expect,a,2,0);stack_from(expect,ram);
  assert(ram==expect&&s.a[4]==CARD2&&s.a[1]==AREA_END);}
 // 1c028 direct: the D0.W push/pop keeps A6's upper WORD from 4d9d6 MOVE.L A6,D0 in D0.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,CARD2,2,1);put(ram,CARD2+6,2,0x2000);put(ram,CARD2+8,4,0x10e200);
  State s=state(0x1c028);s.d[0]=0xabcd0001;s.a[6]=0x10ab1234;State want=s;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  want.pc=STOP;want.a[7]=SP+4;want.d[0]=0x10ab0001;want.a[0]=0x10ab2000;want.a[1]=0x10e200;want.a[4]=CARD2;want.carry=ms5::AnimationCarryUnknown;
  assert(same(s,want)&&get(ram,SP-2,2)==1&&get(ram,SP-6,4)==0x1c030);}
 // 1c028 direct, 6(A4)=0: MOVEA.W D0,A0 (0) then the player fallback with D0 AND 1.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,CARD1,2,1);put(ram,P2+0x56,4,0x10e300);
  State s=state(0x1c028);s.d[0]=0x00000100;Out o;assert(run(ram,s,STOP,o)&&s.a[4]==CARD1&&s.a[0]==P1&&s.a[1]==0&&(s.d[0]&65535U)==0);
  s=state(0x1c028);s.d[0]=0x00000101;ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,P2+0x56,4,0x10e300);
  assert(run(ram,s,STOP,o)&&s.a[4]==CARD2&&s.a[0]==P2&&s.a[1]==0x10e300&&s.d[0]==0x00000001);}
}
// 49392: CMPA.L #108000,A5; ANDI.W #1,D0 (C Clear); BTST D0 mod 8; ORI CCR (Set).
void readiness(){
 const std::uint32_t d0[]={0x12340000,0xffff0003,0x00000002};const std::uint32_t flags[]={1,1,0xfe};
 const std::uint32_t want_a0[]={P1,P2,P1};const ms5::AnimationCarryState want_c[]={ms5::AnimationCarrySet,ms5::AnimationCarryClear,ms5::AnimationCarryClear};
 for(unsigned int i=0;i<3;++i)for(unsigned int c=0;c<3;++c){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,FLAGS,1,flags[i]);
  State s=state(0x49392);s.d[0]=d0[i];s.carry=carry_of(c);State want=s;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  want.pc=STOP;want.a[7]=SP+4;want.a[0]=want_a0[i];want.d[0]=(d0[i]&0xffff0000U)|(d0[i]&1U);want.carry=want_c[i];assert(same(s,want));}
 // BTST Dn on memory takes the bit number mod 8 (bit 10 -> bit 2); not mod 32.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,FLAGS,1,0x04);State s=state(0x493ae);s.d[0]=10;s.carry=ms5::AnimationCarryClear;Out o;
  assert(run(ram,s,0x493b6,o)&&s.carry==ms5::AnimationCarryClear);assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarrySet);}
 // BSET D0,568e(A5) in 4766a: bit 15 mod 8 = 7.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,FLAGS,1,0x01);State s=state(0x4766a);s.d[0]=15;Out o;assert(run(ram,s,STOP,o)&&get(ram,FLAGS,1)==0x81&&s.carry==ms5::AnimationCarrySet);}
 // A5 != 108000: TRAP #f boundary at 4939c (stop there, other stops roll back), also from b4a2a.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);State s=state(0x49392);s.a[5]=0x108002;State want=s;Out o;
  assert(run(ram,s,0x4939c,o)&&quiet(o));want.pc=0x4939c;want.carry=ms5::AnimationCarryUnknown;assert(same(s,want));
  want=state(0x49392);want.a[5]=0x108002;reject(ram,want,STOP,"unsupported animation machine PC");}
 {Bytes ram(65536,0);put(ram,SP,4,STOP);State s=state(0xb4a2a);s.a[5]=0x108100;Out o;
  assert(run(ram,s,0x4939c,o)&&get(ram,0x10de48,2)==0x8000&&get(ram,BOX1,2)==0&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xb4a38&&s.d[0]==0);
  s=state(0xb4a2a);s.a[5]=0x108100;ram.assign(65536,0);put(ram,SP,4,STOP);reject(ram,s,STOP,"unsupported animation machine PC");}
}
// 4701e/46f52: eight 2c-byte slots from 10d61a down to 10d4e6 (D7 = slot index), timer 2a(A0) with 43e38,
// rect LONG 26(A0) (negative WORD skips), sorted signed X (1c/14) and Y (20/18), DBRA BYTEs 10d668 down,
// X bins from 10d646 and Y bins from 10d656 (LSR.W #5), clipped by signed ffa0/1ff and 80/1ff.
std::uint32_t slot(unsigned int i){return SLOT0+0x2c*i;}
void rect(Bytes&ram,std::uint32_t a,std::uint32_t x,std::uint32_t y,std::uint32_t w,std::uint32_t h,std::uint32_t tag){
 put(ram,a,2,x);put(ram,a+2,2,y);put(ram,a+4,2,w);put(ram,a+6,2,h);put(ram,a+8,1,tag);}
void bounds(Bytes&ram,unsigned int i,std::uint32_t x1c,std::uint32_t x14,std::uint32_t y20,std::uint32_t y18){
 put(ram,slot(i)+0x1c,2,x1c);put(ram,slot(i)+0x14,2,x14);put(ram,slot(i)+0x20,2,y20);put(ram,slot(i)+0x18,2,y18);}
void spatial(){
 Bytes ram(65536,0);put(ram,SP,4,STOP);fill(ram,BINS,BIN_END,0xa5);put(ram,0x10d494,1,3);
 for(unsigned int i=0;i<8;++i)put(ram,slot(i)+0x26,4,0xffff0000U);
 // tag BYTE: ROL.B #2 AND 3 -> 7f:1 (2 BYTEs), 3f:0 (3), bf:2 (1), c0:3 (none).
 rect(ram,0x10e800,2,4,1,0,0x7f);rect(ram,0x10e810,0xfffe,0,3,0x30,0x3f);rect(ram,0x10e820,0,0,0,0,0xc0);rect(ram,0x10e830,0,0,0,0,0xbf);
 // Slot 7: timer 1 -> 0 with 43e38 (A1=0; 24 = 5494 so 1c/20 kept); 14/18 become LONG 0/4. X EXG (40 > 30).
 put(ram,slot(7)+0x2a,2,1);put(ram,slot(7),4,0x00300000);put(ram,slot(7)+4,4,0x00a00000);put(ram,slot(7)+0x24,1,3);
 put(ram,slot(7)+0x1c,4,0x00400000);put(ram,slot(7)+0x20,4,0x00900000);put(ram,slot(7)+0x26,4,0x10e800);
 // Slot 6: no timer; Y EXG (40 > 20); xmin -64 -> 0x20 after +60; ymin below 80 -> 0.
 bounds(ram,6,0xffd0,0x0100,0x0040,0x0020);put(ram,slot(6)+0x26,4,0x10e810);
 bounds(ram,5,0x0200,0x0300,0,0);put(ram,slot(5)+0x26,4,0x10e820);     // xmin > 1ff (BGT)
 bounds(ram,4,0x8000,0xff00,0,0);put(ram,slot(4)+0x26,4,0x10e830);     // xmax < -60 (BLT), DBRA BYTE only
 bounds(ram,3,0,0,0x0010,0x0020);put(ram,slot(3)+0x26,4,0x10e820);     // ymax < 80 (BLT)
 bounds(ram,2,0x01f0,0x01f8,0x0300,0x0400);put(ram,slot(2)+0x26,4,0x10e820); // X bin 12 overflows into Y; D1 clamp
 // Slot 1: timer 8000 -> 7fff with 43e38 (24=0: 24/1c/20 updated), rect skipped.
 put(ram,slot(1)+0x2a,2,0x8000);put(ram,slot(1),4,0x11112222);put(ram,slot(1)+4,4,0x33334444);
 Bytes expect=ram;State s=state(0x4701e);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&s.pc==STOP&&s.a[7]==SP+4&&s.a[0]==SLOT0-0x2c);
 fill(expect,BINS,BIN_END,0);put(expect,SLOT_COUNT,2,0xffff);
 put(expect,0x10d668,1,0xd0);put(expect,0x10d667,1,0xc0);put(expect,0x10d666,1,0x40);
 fill(expect,0x10d647,0x10d652,0x40);put(expect,0x10d64b,1,0xc0);
 fill(expect,BIN_Y,0x10d661,0x40);put(expect,0x10d657,1,0xc0);put(expect,0x10d658,1,0xc4);fill(expect,0x10d661,0x10d666,0x04);
 put(expect,slot(7)+0x2a,2,0);put(expect,slot(7)+0x25,1,0);put(expect,slot(7)+0x14,4,0x00300000);put(expect,slot(7)+0x18,4,0x00a00000);
 put(expect,slot(1)+0x2a,2,0x7fff);put(expect,slot(1)+0x25,1,0);put(expect,slot(1)+0x24,1,3);
 put(expect,slot(1)+0x14,4,0x11112222);put(expect,slot(1)+0x18,4,0x33334444);put(expect,slot(1)+0x1c,4,0x11112222);put(expect,slot(1)+0x20,4,0x33334444);
 stack_from(expect,ram);
 for(std::uint32_t a=0x100000;a<0x110000;++a)if(ram[a&65535U]!=expect[a&65535U])std::cerr<<std::hex<<"spatial "<<a<<" "<<unsigned(ram[a&65535U])<<" vs "<<unsigned(expect[a&65535U])<<"\n";
 assert(ram==expect);
 // 46f52 direct: Y overflow-clipped rectangle, BSET bit number mod 8 (D7=WORD 567c=f -> bit 7), DBRA counts.
 {Bytes r2(65536,0);put(r2,SP,4,STOP);put(r2,SLOT_COUNT,2,0x000f);rect(r2,0x10e800,0,0,0x7f,0x7f,0xc0);
  put(r2,0x10e900+0x26,4,0x10e800);put(r2,0x10e900+0x1c,2,0xff00);put(r2,0x10e900+0x14,2,0);put(r2,0x10e900+0x20,2,0x0000);put(r2,0x10e900+0x18,2,0);
  State t=state(0x46f52);t.a[0]=0x10e900;Out p;assert(run(r2,t,STOP,p)&&quiet(p));
  // X: D0=-100 < -60 -> 0; D2=0+3f8 -> 458 -> bin 22 (hex): 35 BYTEs 10d646..10d668 (unclamped D2 runs past the
  // X array). Y: D3=0+400 -> 380 -> 1ff: bins 0..f.
  for(std::uint32_t a=BINS;a<BINS+35;++a)assert(get(r2,a,1)==0x80);assert(get(r2,BINS+35,1)==0);
  for(std::uint32_t a=BIN_Y;a<BIN_Y+16;++a)assert(get(r2,a,1)==0x80);
  assert((t.d[2]&65535U)==0xffff&&(t.d[3]&65535U)==0xffff&&t.a[1]==BIN_Y+16&&t.d[7]==0x0000000f);}
 // An odd rect pointer in slot 3 fails at MOVEM.W (A1)+ after slots 7..4 ran: the whole run rolls back.
 {Bytes r2(65536,0);put(r2,SP,4,STOP);for(unsigned int i=0;i<8;++i)put(r2,slot(i)+0x26,4,0xffff0000U);put(r2,slot(3)+0x26,4,0x10e801);
  reject(r2,state(0x4701e),STOP,"even WORD/LONG");}
}
// 2efa6 four combinations and 3c44 ring scan / byte queue (3ac8) with the live stack BYTE.
void sound_queues(Bytes&ram){put(ram,QUEUE_R,2,0x40);put(ram,QUEUE_W,2,0);}
void sound(){
 for(unsigned int k=0;k<4;++k){const bool now=(k&1)!=0,before=(k&2)!=0;
  Bytes ram(65536,0);put(ram,SP,4,STOP);sound_queues(ram);put(ram,SOUND_NEW,1,now?0x42:0);put(ram,SOUND_OLD,1,before?0x99:0);
  put(ram,RING,4,0x1d281d28U);put(ram,RING+4,4,0x12341d28U);put(ram,RING_R,2,2);put(ram,RING_W,2,0);
  if(now&&!before){put(ram,RING_R,2,0);put(ram,RING_W,2,0);}
  Bytes expect=ram;State s=state(0x2efa6);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&s.a[7]==SP+4);
  put(expect,SOUND_OLD,1,now?0xff:0);
  if(now&&!before){put(expect,RING,2,0x1d28);put(expect,RING_W,2,2);assert((s.d[0]&65535U)==0x1d28);}   // 3af8 WORD ring push
  if(!now&&before){put(expect,RING+2,2,0);put(expect,RING+6,2,0);put(expect,QUEUE,1,0x14);put(expect,QUEUE+1,1,0x1d);put(expect,QUEUE+2,1,0x28);put(expect,QUEUE_W,2,3);
   assert((s.d[0]&65535U)==0x1d28);}
  stack_from(expect,ram);assert(ram==expect);}
 // 3c44: empty ring (R == W: no scan), miss and hit (R=6, W=2: indexes 6 then 0 after the AND #6 wrap).
 // A0 ends at the 3ac8 byte queue slot of the last BYTE (3ad8/3ae0).
 const std::uint32_t ring[][4]={{0x5555,0x5555,0x5555,0x5555},{0x1111,0x5555,0x5555,0x5554},{0x5555,0x5555,0x5555,0x5555}};
 const std::uint32_t rr[]={4,6,6},ww[]={4,2,2};
 for(unsigned int k=0;k<3;++k){Bytes ram(65536,0);put(ram,SP,4,STOP);sound_queues(ram);for(unsigned int i=0;i<4;++i)put(ram,RING+2*i,2,ring[k][i]);
  put(ram,RING_R,2,rr[k]);put(ram,RING_W,2,ww[k]);Bytes expect=ram;State s=state(0x3c44);s.d[0]=0x77775555;Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  if(k==2){put(expect,RING,2,0);put(expect,RING+6,2,0);}
  put(expect,QUEUE,1,0x14);put(expect,QUEUE+1,1,0x55);put(expect,QUEUE+2,1,0x55);put(expect,QUEUE_W,2,3);stack_from(expect,ram);
  assert(ram==expect&&s.d[0]==0x00005555&&s.a[0]==QUEUE+2&&s.a[7]==SP+4&&(s.d[1]&65535U)==3&&get(ram,SP-2,2)==0x5555);
  assert(s.a[1]==(k==0?0x87654322U:RING));}
 // Full byte queue waits inside 3ac8 after the 3c44 WORD push; MOVE.B (A7) then reads the live stack BYTE.
 {Bytes ram(65536,0);put(ram,SP,4,STOP);
  put(ram,QUEUE_R,2,1);State s=state(0x3c44);s.d[0]=0x1d28;Out o;
  assert(run(ram,s,STOP,o)&&o.status==ms5::AnimationMachineWaiting&&s.pc==0x3aea&&s.a[7]==SP-6&&get(ram,SP-2,2)==0x1d28&&get(ram,SP-6,4)==0x3c70);
  put(ram,SP-2,1,0x77);put(ram,QUEUE_R,2,0x40);o=Out();assert(run(ram,s,STOP,o)&&quiet(o)&&s.a[7]==SP+4&&s.d[0]==0x7728);
  assert(get(ram,QUEUE,3)==0x147728&&get(ram,QUEUE_W,2)==3);}
 // 6f1c2: RTS only, C preserved.
 for(unsigned int c=0;c<3;++c){Bytes ram(65536,0);put(ram,SP,4,STOP);const Bytes before=ram;State s=state(0x6f1c2);s.carry=carry_of(c);State want=s;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&ram==before);want.pc=STOP;want.a[7]=SP+4;assert(same(s,want));}
}
// Every block start with the generic fixture: the next block (clear/set successor for C consumers).
const std::uint32_t TABLE[][3]={
 {0x3c44,0x3c4e,0x3c4e},{0x3c4e,0x3c6a,0x3c6a},{0x3c56,0x3c66,0x3c66},{0x3c66,0x3c68,0x3c68},{0x3c68,0x3c4e,0x3c4e},
 {0x3c6a,0x3ac8,0x3ac8},{0x3c70,0x3ac8,0x3ac8},{0x3c76,0x3ac8,0x3ac8},
 {0x1c028,0x4d9d6,0x4d9d6},{0x1c030,0x1c03a,0x1c03a},{0x1c03a,STOP,STOP},{0x1c03c,0x1c04c,0x1c04c},{0x1c048,0x1c04c,0x1c04c},{0x1c04c,STOP,STOP},
 {0x2efa6,0x2efca,0x2efca},{0x2efb8,0x2efbe,0x2efbe},{0x2efbe,0x3af8,0x3af8},{0x2efc8,STOP,STOP},{0x2efca,0x2efda,0x2efda},
 {0x2efd0,0x3c44,0x3c44},{0x2efda,STOP,STOP},
 {0x46f52,0x46f6e,0x46f6e},{0x46f6c,0x46f6e,0x46f6e},{0x46f6e,0x46f76,0x46f76},{0x46f74,0x46f76,0x46f76},{0x46f76,0x46fa4,0x46fa4},
 {0x46fa4,0x46faa,0x46faa},{0x46faa,0x46fb0,0x46fb0},{0x46fb0,0x46fbe,0x46fbe},{0x46fbe,0x46fc4,0x46fc4},{0x46fc4,0x46fcc,0x46fcc},
 {0x46fca,0x46fcc,0x46fcc},{0x46fcc,0x46fd4,0x46fd4},{0x46fd2,0x46fd4,0x46fd4},{0x46fd4,0x46fe2,0x46fe2},{0x46fe2,0x46fe8,0x46fe8},
 {0x46fe8,0x46ff0,0x46ff0},{0x46fee,0x46ff0,0x46ff0},{0x46ff0,0x46ff8,0x46ff8},{0x46ff6,0x46ff8,0x46ff8},{0x46ff8,0x4700a,0x4700a},
 {0x4700a,0x47010,0x47010},{0x47010,0x47016,0x47016},{0x47016,0x4701c,0x4701c},{0x4701c,STOP,STOP},
 {0x4701e,0x47040,0x47040},{0x47040,0x47054,0x47054},{0x47048,0x43e38,0x43e38},{0x47054,0x4705c,0x4705c},{0x4705c,0x46f52,0x46f52},
 {0x47060,0x4706a,0x4706a},{0x4706a,STOP,STOP},
 {0x47642,0x47656,0x47656},{0x47650,0x47656,0x47656},{0x47656,0x289e,0x289e},{0x4765c,0x47670,0x47660},{0x47660,0x4766a,0x4766a},
 {0x4766a,STOP,STOP},{0x47670,STOP,STOP},
 {0x480bc,0x47642,0x47642},{0x480c0,0x1a73c,0x1a73c},{0x480c6,0x49b0c,0x49b0c},{0x480cc,0x4aa88,0x4aa88},{0x480d2,0xb4a2a,0xb4a2a},
 {0x480d8,0x6f1c2,0x6f1c2},{0x480de,0x4701e,0x4701e},{0x480e4,0xe8a48,0xe8a48},{0x480ea,0x2efa6,0x2efa6},{0x480f0,STOP,STOP},
 {0x49392,0x4939e,0x4939e},{0x4939e,0x493ae,0x493ae},{0x493aa,0x493ae,0x493ae},{0x493ae,0x493ba,0x493ba},{0x493b6,0x493ba,0x493ba},{0x493ba,STOP,STOP},
 {0x4d9d6,0x4d9e4,0x4d9e4},{0x4d9e0,0x4d9e4,0x4d9e4},{0x4d9e4,0x4d9ea,0x4d9ea},{0x4d9ea,STOP,STOP},{0x4d9f2,0x4d9fc,0x4d9fc},
 {0x4d9fc,STOP,STOP},{0x4da00,STOP,STOP},{0x6f1c2,STOP,STOP},
 {0xb481e,0xb482a,0xb482a},{0xb482a,0xb483e,0xb483e},{0xb4836,0xb483e,0xb483e},{0xb483e,0xb4840,0xb4840},{0xb4840,0xb4846,0xb4846},
 {0xb4846,0xb4840,0xb4840},{0xb484e,STOP,STOP},
 {0xb4a2a,0x49392,0x49392},{0xb4a38,0xb4a5e,0xb4a3c},{0xb4a3c,0x1c028,0x1c028},{0xb4a44,0xb4a4c,0xb4a4c},{0xb4a4c,0xb4a5e,0xb4a5e},
 {0xb4a5e,0x49392,0x49392},{0xb4a6c,0xb4a92,0xb4a70},{0xb4a70,0x1c028,0x1c028},{0xb4a78,0xb4a80,0xb4a80},{0xb4a80,0xb4a92,0xb4a92},
 {0xb4a92,0xb4a9e,0xb4a9e},{0xb4a9c,0xb4a9e,0xb4a9e},{0xb4a9e,0xb4aa8,0xb4aa8},{0xb4aa6,0xb4aa8,0xb4aa8},{0xb4aa8,0xb481e,0xb481e},{0xb4aae,STOP,STOP}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
// FLOW_ONLY blocks (JSR/BSR/BRA/RTS/LEA/MOVEA/BTST/BSET/Bcc only) keep the incoming C.
const std::uint32_t KEEP[]={0x3c68,0x1c03a,0x1c048,0x1c04c,0x2efc8,0x2efda,0x4701c,0x4705c,0x4706a,0x47656,0x4765c,0x47660,0x4766a,0x47670,
 0x480bc,0x480c0,0x480c6,0x480cc,0x480d2,0x480d8,0x480de,0x480e4,0x480ea,0x480f0,0x493aa,0x493ae,0x493ba,0x4d9e0,0x4d9ea,0x4d9fc,0x4da00,
 0x6f1c2,0xb482a,0xb4836,0xb484e,0xb4a38,0xb4a6c,0xb4aae};
const unsigned int KEEPS=sizeof(KEEP)/sizeof(KEEP[0]);
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
// Generic fixture: zero RAM, return LONG STOP at SP, D0-D7 zero, RAM pointers in A0/A1/A2/A4.
void generic(std::uint32_t pc,Bytes&ram,State&s){ram.assign(65536,0);put(ram,SP,4,STOP);s=state(pc);
 for(unsigned int i=0;i<8;++i)s.d[i]=0;s.a[0]=0x10d61a;s.a[1]=0x10e800;s.a[2]=0x10e900;s.a[4]=CARD1;}
void errors(){
 // Unknown C at each consumer, and through 493ae/493ba (C preserved, never fabricated) into b4a38.
 const std::uint32_t consumers[]={0x4765c,0xb4a38,0xb4a6c};
 for(unsigned int i=0;i<3;++i){Bytes ram;State s;generic(consumers[i],ram,s);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"frame helper caller requires known carry");}
 {Bytes ram;State s;generic(0x493ae,ram,s);put(ram,SP,4,0xb4a38);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"frame helper caller requires known carry");
  s.carry=ms5::AnimationCarryClear;Out o;assert(run(ram,s,0xb4a5e,o)&&s.carry==ms5::AnimationCarryClear&&s.a[7]==SP+4);}
 // Odd A0 (289e LONG, 2a(A0) WORD, 26(A0) LONG, 56(A0) LONG), odd A1 (MOVEM.W, MOVE.W store, ring WORD),
 // odd A4 (TST.W, 8(A4) LONG), odd A5 (MOVE.L stores, WORD 5d48), odd A7 (WORD/LONG pushes and pops).
 struct Odd {std::uint32_t pc;unsigned int reg;const char*message;};
 const Odd odd[]={{0x47656,0,"even WORD/LONG"},{0x47040,0,"even WORD/LONG"},{0x46f52,0,"even WORD/LONG"},{0x1c04c,0,"even WORD/LONG"},
  {0x3c56,0,"even WORD/LONG"},{0xb4a4c,1,"even WORD/LONG"},{0x46f76,1,"even WORD/LONG"},{0xb4846,1,"alignment"},{0x3c66,1,"alignment"},
  {0x4d9e4,4,"even WORD/LONG"},{0x4da00,4,"even WORD/LONG"},{0x4701e,5,"alignment"},{0xb4a2a,5,"alignment"},{0x4d9d6,5,"even WORD/LONG"},
  {0x3c44,7,"even WORD/LONG"},{0x1c028,7,"even WORD/LONG"},{0x480bc,7,"even WORD/LONG"},{0x6f1c2,7,"even WORD/LONG"},{0x3c76,7,"even WORD/LONG"}};
 for(unsigned int i=0;i<sizeof(odd)/sizeof(odd[0]);++i){Bytes ram;State s;generic(odd[i].pc,ram,s);
  if(odd[i].reg==0)s.a[0]|=1U;else if(odd[i].reg==1)s.a[1]|=1U;else if(odd[i].reg==4)s.a[4]|=1U;else if(odd[i].reg==5)s.a[5]|=1U;else s.a[7]|=1U;
  if(odd[i].pc==0x3c56)s.a[0]=0x104d83;
  reject(ram,s,STOP,odd[i].message);}
 // Store into the fixed ROM area from the b481e clear loop.
 {Bytes ram;State s;generic(0xb4846,ram,s);s.a[1]=0x1000;reject(ram,s,STOP,"unsupported animation machine write device");}
 // Interior/bundled PCs in the routed ranges.
 const std::uint32_t ranges[][2]={{0x480bc,0x480f0},{0x47642,0x47670},{0x6f1c2,0x6f1c2},{0x2efa6,0x2efda},{0x3c44,0x3c7a},{0xb4a2a,0xb4aae},
  {0x49392,0x493ba},{0x1c028,0x1c050},{0x4d9d6,0x4da06},{0xb481e,0xb484e},{0x46f52,0x4706a}};
 unsigned int interior=0;
 for(unsigned int i=0;i<11;++i)for(std::uint32_t pc=ranges[i][0];pc<=ranges[i][1];pc+=2){
  if(listed(pc)||pc==0x4939c)continue;Bytes ram;State s;generic(pc,ram,s);reject(ram,s,STOP,"unsupported animation frame helper PC");++interior;}
 assert(interior==300); // 406 even PCs in the routed ranges (4939c excluded) minus 106 block starts
 // Neighbours outside the ranges and the TRAP boundary (U2..U7 now execute; 49ab2 is the U6 default mask data before
 // 49ab4; 47640 2efa4 2efdc b4a28 b481c 46f50 are now stage area F1c2 PCs, and the unrouted 10fe20 10fe22 10fe24 10fe26 10fe28
 // 10fe2a, outside every unit contract, stand in for them; 4706c is an objects U09 block start and the unrouted 5f500 stands in
 // for it; 49390 is inside the objects U11 block 4938c and the unrouted 5f800 stands in for it; 493bc is an objects N15 block start
 // and the work RAM PC 10fe90 stands in for it); odd PCs are rejected first.
 const std::uint32_t outside[]={0x480f2,0x10fe20,0x6f1c0,0x6f1c4,0x10fe22,0x10fe24,0x3c42,0x3c7c,0x10fe26,0xb4ab0,0x5f800,0x4939c,0x10fe90,
  0x1c026,0x1c052,0x4d9d4,0x4da08,0x10fe28,0xb4850,0x10fe2a,0x5f500,0x49ab2};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram;State s;generic(outside[i],ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0x47657,ram,s);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int c=0;c<3;++c)for(unsigned int i=0;i<ROWS;++i){Bytes ram;State s;generic(TABLE[i][0],ram,s);s.carry=carry_of(c);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,TABLE[i][0],o)&&same(s,old)&&ram==before&&quiet(o));}
}
void carry(){
 assert(ROWS==106&&KEEPS==38);unsigned int keeps=0;
 for(unsigned int i=0;i<ROWS;++i){const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,KEEPS,pc);if(keep)++keeps;
  const bool consumer=TABLE[i][1]!=TABLE[i][2];assert(consumer==(pc==0x4765c||pc==0xb4a38||pc==0xb4a6c));
  for(unsigned int c=0;c<3;++c){if(consumer&&c==0)continue; // errors()
   Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(c);const std::uint32_t stop=c==2?TABLE[i][2]:TABLE[i][1];Out o;
   if(!(run(ram,s,stop,o)&&s.pc==stop&&quiet(o)))std::cerr<<std::hex<<"row "<<pc<<"\n";
   assert(s.pc==stop&&quiet(o));
   ms5::AnimationCarryState expect=keep?carry_of(c):ms5::AnimationCarryUnknown;
   if(pc==0x4939e)expect=ms5::AnimationCarryClear;if(pc==0x493b6)expect=ms5::AnimationCarrySet;
   if(s.carry!=expect)std::cerr<<std::hex<<"carry row "<<pc<<"\n";assert(s.carry==expect);}}
 assert(keeps==KEEPS);
}
}
int main(){natural();shell();region();readiness();spatial();sound();errors();zero_step();carry();
 std::cout<<"animation_machine_frame_helpers_test PASS "<<std::dec<<calls<<" API invocations\n";}
