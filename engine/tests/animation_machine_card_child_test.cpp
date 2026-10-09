#include "ms5/animation_machine.h"
#ifdef MS5_CARD_CHILD_REAL_RESOURCE_TEST
#include "ms5/physical_rom_resource.h"
#endif
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
const std::uint32_t SP=0x1feffc,STOP=0xff000,OBJ=0x102000,CHILD=0x103000,NODE=0x109156,BIOS=0xc00468,MENU=0xa29c,BASE=0x104d92;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void rom(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[a+i]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=CHILD;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const Physical*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
// Failure preserves RAM, registers, device and every output, from the given device.
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message,const Physical*physical=NULL,const ms5::AnimationMachineDevice*device=NULL){
 const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;if(device)o.dev=*device;const ms5::AnimationMachineDevice dev=o.dev;assert(!run(ram,s,stop,o,physical));
 if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
// Synthetic typed physical bytes for bus/call integration, not a native ROM oracle:
// fixed 0..fffff, bank 1000 (200000) and bank 2000 (300000).
Physical resources(){
 Physical p(3);p[0].source_rom_offset=0;p[0].data.assign(0x100000,0);
 for(unsigned int i=1;i<3;++i){p[i].source_rom_offset=0x100000U+0x100000U*i;p[i].data.assign(0x2000,0);}
 Bytes&f=p[0].data;rom(f,0xe7b58,2,0xffff);
 // e7c16 list: bind slot fe to palette 0123 (flag 2), then terminator.
 rom(f,0xe7bc0,2,0xfe);rom(f,0xe7bc2,2,0x0123);rom(f,0xe7bc4,1,2);rom(f,0xe7bc6,2,0xffff);
 // de40c scene: one type-2 node record for 109156 and terminator 3.
 rom(f,0xde40c,2,8);rom(f,0xde40e,2,2);rom(f,0xde410,4,NODE);rom(f,0xde414,2,0);rom(f,0xde416,2,3);
 // de41c map descriptor: primary 0, no secondary, 4x4.
 rom(f,0xde41c,2,0);rom(f,0xde41e,2,0);rom(f,0xde420,2,4);rom(f,0xde422,2,4);
 // Bank 1000: 20000c table, entry 49 (D0<<2 = 124) -> list binding slot 10.
 Bytes&b=p[1].data;rom(b,0xc,4,0x200100);rom(b,0x224,4,0x200400);rom(b,0x400,2,0x10);rom(b,0x402,2,0x0456);rom(b,0x404,1,2);rom(b,0x406,2,0xffff);
 rom(b,0xfc,4,0x200500);rom(b,0x500,2,0xffff);
 // Bank 2000: map header table and 4x4 tile LONGs; its own 20000c table differs.
 Bytes&m=p[2].data;rom(m,4,4,0x200008);rom(m,8,4,0x200100);rom(m,0x100,2,4);rom(m,0x102,2,4);for(unsigned int i=0;i<16;++i)rom(m,0x104+4*i,4,0x11112222U+i);
 rom(m,0xc,4,0x200600);rom(m,0x724,4,0x200800);rom(m,0x800,2,0x20);rom(m,0x802,2,0x0789);rom(m,0x804,1,2);rom(m,0x806,2,0xffff);
 return p;
}
void preserving(){
 const Physical p=resources();
 const std::uint32_t cs[][3]={{0xc258,0x8c16,0xc25e},{0xc266,0xde424,0xc26c},{0xc274,0x8c16,0xc27a},{0xc2a2,MENU,0xc2a8},
  {0xde424,0xe7c16,0xde42a},{0xde450,0x8da2,0xde456},{0xde45a,0x43ffc,0xde460},{0xde466,0x16fac,0xde46c},{0xde478,0x16ff8,0xde47e},
  {0xde47e,0x1861a,0xde484},{0xde484,0x17012,0xde48a},{0xe7c16,0xe7bf4,0xe7c1a},{0xe7c1e,0x8da2,0xe7c24}};
 const std::uint32_t lea[][4]={{0xde456,0xde45a,0,0xde40c},{0xde460,0xde466,0,NODE},{0xde46c,0xde474,1,0xde41c},{0xe7c1a,0xe7c1e,0,0xe7bc0}};
 const std::uint32_t rt[]={0xc264,0xc28e,0xde48a};
 for(unsigned int carry=0;carry<3;++carry){
  for(unsigned int i=0;i<sizeof(cs)/sizeof(cs[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(cs[i][0]);s.carry=carry_of(carry);Out o;assert(run(ram,s,cs[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==cs[i][2]&&o.ports.empty());}
  for(unsigned int i=0;i<sizeof(lea)/sizeof(lea[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(lea[i][0]);const ms5::AnimationMachineState old=s;s.carry=carry_of(carry);Out o;assert(run(ram,s,lea[i][1],o)&&s.carry==carry&&s.a[7]==SP&&s.a[lea[i][2]]==lea[i][3]);
   // MOVEA.W #0,A2 sign-extends to the whole register; nothing else changes.
   if(lea[i][0]==0xde46c)assert(s.a[2]==0&&s.a[0]==old.a[0]);for(unsigned int k=0;k<8;++k)assert(s.d[k]==old.d[k]);}
  for(unsigned int i=0;i<sizeof(rt)/sizeof(rt[0]);++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rt[i]);s.carry=carry_of(carry);Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  // JMP 8cda keeps the stack and C.
  Bytes ram(65536,0);ms5::AnimationMachineState s=state(0xe7c30);s.carry=carry_of(carry);Out o;assert(run(ram,s,0x8cda,o)&&s.carry==carry&&s.a[7]==SP);
 }
 // MOVE/MOVEQ/SUBQ/LSL blocks do not retain caller C.
 const std::uint32_t unknown[][2]={{0xc250,0xc258},{0xc25e,0xc264},{0xc26c,0xc274},{0xc27a,0xc28e},{0xc286,0xc28e},{0xc290,0xc2a2},
  {0xde42a,0xde42e},{0xde42e,0xde444},{0xde444,0xde450},{0xde474,0xde478},{0xe7c24,0xe7c30}};
 for(unsigned int i=0;i<sizeof(unknown)/sizeof(unknown[0]);++i){Bytes ram(65536,0);put(ram,CHILD+0x7e,2,5);ms5::AnimationMachineState s=state(unknown[i][0]);s.d[0]=0x49;Out o;o.dev.bank_base=0x200000;assert(run(ram,s,unknown[i][1],o,&p)&&s.carry==ms5::AnimationCarryUnknown);}
}
void entry(){
 // c250: MOVEQ e1 to D0-D2 (32-bit), MOVEQ 0 to D3, actual 8c16 leaf, callback c266, RTS.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xc250);const std::uint32_t d4=s.d[4],a0=s.a[0];Out o;
 assert(run(ram,s,0x8c16,o)&&s.d[0]==0xffffffe1U&&s.d[1]==0xffffffe1U&&s.d[2]==0xffffffe1U&&s.d[3]==0&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc25e);
 assert(run(ram,s,STOP,o)&&s.pc==STOP&&s.a[7]==SP+4&&get(ram,CHILD,4)==0xc266&&s.d[4]==d4&&s.a[0]==a0&&o.ports.empty()&&s.carry==ms5::AnimationCarryUnknown);
 Bytes whole(65536,0);put(whole,SP,4,STOP);ms5::AnimationMachineState w=state(0xc250);Out wo;assert(run(whole,w,STOP,wo)&&same(w,s)&&whole==ram);
 // c26c: MOVEQ 0/0/0/14, 8c16, MOVE.W 14 to 7e, callback c286 and its first SUBQ in the same call.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0xc26c);o=Out();
 assert(run(ram,s,0x8c16,o)&&s.d[0]==0&&s.d[1]==0&&s.d[2]==0&&s.d[3]==0x14&&get(ram,SP-4,4)==0xc27a);
 assert(run(ram,s,STOP,o)&&s.a[7]==SP+4&&get(ram,CHILD+0x7e,2)==0x13&&get(ram,CHILD,4)==0xc286&&o.ports.empty());
}
void timers(){
 // Unsigned borrow only when the old WORD is 0; 8000 has no borrow.
 const std::uint32_t t[]={0,1,0x8000,0x14,0xffff};
 for(unsigned int i=0;i<5;++i){Bytes ram(65536,0x5a);put(ram,SP,4,STOP);put(ram,CHILD+0x7e,2,t[i]);put(ram,CHILD+0x76,4,0xc188);put(ram,CHILD+0x7a,2,4);put(ram,CHILD+0x7c,2,4);
  ms5::AnimationMachineState s=state(0xc286);Out o;const bool borrow=t[i]==0;
  if(borrow)reject(ram,s,STOP,"unsupported animation machine PC");
  assert(run(ram,s,borrow?MENU:STOP,o)&&get(ram,CHILD+0x7e,2)==((t[i]-1U)&65535U)&&s.carry==ms5::AnimationCarryUnknown&&o.ports.empty());
  if(borrow)assert(s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2a8&&get(ram,CHILD+0x80,1)==0&&s.a[0]==0xc188&&s.d[0]==0xabcd0004U&&s.d[1]==0xabce0004U);
  else assert(s.a[7]==SP+4&&get(ram,CHILD+0x80,1)==0x5a);}
}
void menu_boundary(){
 // c290: BYTE clear first, then live LONG/WORD loads; D0/D1 high WORDs preserved.
 Bytes ram(65536,0x5a);put(ram,CHILD+0x76,4,0x12345678);put(ram,CHILD+0x7a,2,0x8001);put(ram,CHILD+0x7c,2,0xfffe);
 ms5::AnimationMachineState s=state(0xc290);const ms5::AnimationMachineState old=s;Out o;
 reject(ram,s,STOP,"unsupported animation machine PC");reject(ram,s,0xc2a8,"unsupported animation machine PC");
 assert(run(ram,s,MENU,o)&&s.pc==MENU&&s.a[0]==0x12345678&&s.d[0]==0xabcd8001U&&s.d[1]==0xabcefffeU&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2a8);
 assert(get(ram,CHILD+0x80,1)==0&&get(ram,CHILD+0x7f,1)==0x5a&&get(ram,CHILD+0x81,1)==0x5a&&s.a[6]==old.a[6]&&s.d[2]==old.d[2]&&o.ports.empty());
}
void scene_helper(){
 const Physical p=resources();
 // e7c16: actual e7bf4 (itself ending in JMP 8cda), e7bc0 binding for slot fe, then JMP 8cda D0=fe D1=1 D2=c.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xe7c16);Out o;
 assert(run(ram,s,0xe7c30,o,&p)&&s.a[7]==SP&&get(ram,SP-4,4)==0xe7c24&&s.d[0]==0xfeU&&s.d[1]==0xabce0001U&&s.d[2]==0xabcf000cU&&s.a[0]==0xe7bc8);
 assert(get(ram,BASE+0xfe0+8,2)==0xffff&&get(ram,BASE+0xfe0+12,2)==0x0123);
 assert(run(ram,s,STOP,o,&p)&&s.a[7]==SP+4&&get(ram,BASE+0xfe0+12,2)==1&&get(ram,BASE+0xfe0+14,1)==12&&(get(ram,BASE+0xfe0+15,1)&128));
 // de42a/de42e: D0.W=49 then the zero-bank writes through live A5.
 ram.assign(65536,0x5a);s=state(0xde42a);s.a[5]=0x109000;o=Out();
 assert(run(ram,s,0xde444,o,&p)&&s.d[0]==0xabcd0049U&&get(ram,0x101010,2)==0&&o.dev.bank_base==0x200000&&o.ports.size()==2&&o.ports[0].address==0x2ffff2&&o.ports[0].value==0x1000&&o.ports[1].address==0x2ffff0);
 s=state(0xde42e);s.a[5]=0x109001;reject(ram,s,0xde444,"alignment",&p);
 // de444: LONG 20000c through the current bank, then signed WORD index.
 for(unsigned int bank=0;bank<2;++bank){ram.assign(65536,0);s=state(0xde444);s.d[0]=0x12340049;o=Out();o.dev.bank_base=bank?0x300000:0x200000;
  assert(run(ram,s,0xde450,o,&p)&&s.d[0]==0x12340124&&s.a[0]==(bank?0x200800U:0x200400U));}
 ram.assign(65536,0);s=state(0xde444);s.d[0]=0x12343fff;o=Out();o.dev.bank_base=0x200000;assert(run(ram,s,0xde450,o,&p)&&s.d[0]==0x1234fffc&&s.a[0]==0x200500);
 s=state(0xde444);reject(ram,s,0xde450,"missing program bus ROM");
 // de424 whole: e7c16, palette 49, scene, node setup and map transfer, 17012.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,NODE+0x14,2,0xffa0);put(ram,NODE+0x18,2,0x27f);put(ram,0x100010,2,0x5a5a);s=state(0xde424);s.a[5]=0x87654320;const Bytes start=ram;o=Out();
 assert(run(ram,s,STOP,o,&p)&&s.a[7]==SP+4&&s.a[5]==0x108000&&o.dev.bank_base==0x200000&&s.a[0]==NODE&&s.a[1]==0xde41c&&s.carry==ms5::AnimationCarryUnknown);
 assert(get(ram,BASE+0x100+12,2)==0x0456&&get(ram,BASE+0xfe0+12,2)==1&&get(ram,NODE+0x2e,4)==0xde41c&&get(ram,NODE+0x36,4)==0&&get(ram,NODE+0x32,2)==0&&get(ram,NODE+0x34,2)==31&&(get(ram,NODE+0x7a,1)&0x81)==0x81);
 assert(get(ram,0x109152,4)==0xcd50&&get(ram,0x100010,2)==0);
 const std::size_t ports=o.ports.size();unsigned int tiles=0;for(std::size_t i=0;i<ports;++i)if(o.ports[i].address==0x3c0000&&(o.ports[i].value&0xffffU)==0x1111)++tiles;
 // All 16 synthetic tile LONGs reach 3c0000 (first WORD 1111); scene allocated node WORD 26.
 assert(tiles==16&&ports==4442&&get(ram,NODE+0x26,2)==0x15c);
 const std::uint32_t whole_ports=static_cast<std::uint32_t>(ports);
 // Fresh split at every helper boundary equals the continuous run.
 const std::uint32_t stops[]={0xe7c16,0xe7bf4,0x8cda,0xde42a,0xde444,0xde450,0xde456,0x43ffc,0xde460,0x16fac,0xde46c,0xde478,0x16ff8,0x1861a,0xde484,0x17012,0xde48a,STOP};
 Bytes split=start;ms5::AnimationMachineState t=state(0xde424);t.a[5]=0x87654320;Out so;std::size_t total=0;
 for(unsigned int i=0;i<sizeof(stops)/sizeof(stops[0]);++i){assert(run(split,t,stops[i],so,&p)&&t.pc==stops[i]);total+=so.ports.size();}
 assert(split==ram&&same(t,s)&&so.dev.pvc==o.dev.pvc&&so.dev.bank_base==o.dev.bank_base&&total==ports&&whole_ports==4442);
 // A ROM-free bus fails atomically at the first fixed list read.
 s=state(0xde424);reject(start,s,STOP,"missing program bus ROM");
}
// Fade card native chain up to the BIOS JSR, then the declared BIOS resume with allocation success.
ms5::AnimationMachineState parent(Bytes&ram,Out&o,const Physical&p){
 ram.assign(65536,0);put(ram,SP,4,0x2ac2);put(ram,OBJ+0x6c,1,255);ms5::AnimationMachineState s=state(0x4804e);s.a[6]=OBJ;
 assert(run(ram,s,0x2ac2,o,&p)&&get(ram,OBJ+0x7a,2)==0x7f);
 for(unsigned int k=1;k<=127+30;++k){s.pc=0x2ab8;assert(run(ram,s,0x2ac2,o,&p)&&s.a[7]==SP+4&&s.a[6]==OBJ);}
 s.pc=0x2ab8;assert(run(ram,s,BIOS,o,&p)&&s.a[7]==SP-12&&get(ram,SP-12,4)==0xc37c);
 // Declared host fixture: BIOS RTS popped c37c and one answer BYTE 0 at 10fdc6; free list for 28ae.
 s.a[7]+=4;s.pc=0xc37c;put(ram,0x10fdc6,1,0);put(ram,0x104ca0,2,2);put(ram,0x104c9c,4,CHILD);put(ram,CHILD+8,4,0x103400);put(ram,OBJ+8,4,0x102200);
 assert(run(ram,s,0x2ac2,o,&p)&&s.a[7]==SP+4&&s.a[6]==OBJ&&get(ram,OBJ+8,4)==CHILD&&get(ram,CHILD,4)==0xc250&&get(ram,CHILD+8,4)==0x102200);
 assert(get(ram,CHILD+0x76,4)==0xc188&&get(ram,CHILD+0x7a,2)==4&&get(ram,CHILD+0x7c,2)==4&&get(ram,OBJ,4)==0x480ac);
 return s;
}
void chain(){
 const Physical p=resources();Bytes ram;Out o;ms5::AnimationMachineState s=parent(ram,o,p);
 // Declared frame re-entry at the parent: 480ac TST.B 62 = 0, 480b4 RTS to 2ac2.
 s.pc=0x2ab8;Bytes hold=ram;assert(run(ram,s,0x2ac2,o,&p)&&s.a[0]==0x480ac&&s.a[6]==OBJ&&s.a[7]==SP+4&&ram==hold&&o.ports.empty());
 // Natural link with no host change: 2ac2 MOVEA.L 8(A6),A6 -> child, BRA 2ab8.
 assert(run(ram,s,0x2ab8,o,&p)&&s.pc==0x2ab8&&s.a[6]==CHILD&&s.a[7]==SP+4&&ram==hold);
 // 2ab8 -> (A6)=c250 -> JSR, c250 frame, RTS to 2ac2.
 assert(run(ram,s,0x2ac2,o,&p)&&s.a[0]==0xc250&&s.a[6]==CHILD&&s.a[7]==SP+4&&get(ram,SP,4)==0x2ac2&&get(ram,CHILD,4)==0xc266);
 // Actual 8c16 leaf: targets e1<<8, duration 0 normalized to 1.
 assert(s.d[3]==1&&get(ram,0x107dd4,1)==1&&get(ram,0x107dc8,2)==0xe100&&get(ram,0x107dcc,2)==0xe100&&o.ports.empty());
 // Child frame: c266 de424 whole then c26c..c286 first SUBQ in the same call.
 put(ram,NODE+0x14,2,0xffa0);put(ram,NODE+0x18,2,0x27f); // declared node fixture for a visible map rectangle
 s.pc=0x2ab8;Bytes before=ram;const ms5::AnimationMachineState sb=s;const ms5::AnimationMachineDevice db=o.dev;
 assert(run(ram,s,0x2ac2,o,&p)&&s.a[0]==NODE&&s.a[6]==CHILD&&s.a[7]==SP+4&&get(ram,CHILD,4)==0xc286&&get(ram,CHILD+0x7e,2)==0x13);
 // Second 8c16: zero targets against zero current colors, so the leaf clears D3 and 7dd4.
 assert(s.d[0]==0&&s.d[1]==0&&s.d[2]==0&&s.d[3]==0&&get(ram,0x107dd4,1)==0&&get(ram,0x107dc8,2)==0&&o.ports.size()==4442);
 assert(get(ram,NODE+0x2e,4)==0xde41c&&(get(ram,NODE+0x7a,1)&0x81)==0x81&&o.dev.bank_base==0x200000&&get(ram,BASE+0x100+12,2)==0x0456);
 const std::size_t frame_ports=o.ports.size();
 // Split at c26c and c286 equals the continuous frame.
 {Bytes r2=before;ms5::AnimationMachineState t=sb;Out so;so.dev=db;std::size_t total=0;const std::uint32_t st[]={0xde424,0xc26c,0xc286,0x2ac2};
  for(unsigned int i=0;i<4;++i){assert(run(r2,t,st[i],so,&p));total+=so.ports.size();}
  assert(r2==ram&&same(t,s)&&so.dev.pvc==o.dev.pvc&&so.dev.bank_base==o.dev.bank_base&&total==frame_ports);}
 // Timer re-entries: 13 .. 0 return through c28e.
 for(unsigned int k=1;k<=0x13;++k){s.pc=0x2ab8;hold=ram;assert(run(ram,s,0x2ac2,o,&p)&&s.a[0]==0xc286&&s.a[7]==SP+4&&get(ram,CHILD+0x7e,2)==0x13U-k&&o.ports.empty());}
 // Borrow frame: only the a29c stop succeeds; others roll back.
 s.pc=0x2ab8;reject(ram,s,0x2ac2,"unsupported animation machine PC",&p,&o.dev);reject(ram,s,0xc2a8,"unsupported animation machine PC",&p,&o.dev);
 const std::uint32_t d0=s.d[0]&0xffff0000U,d1=s.d[1]&0xffff0000U;
 assert(run(ram,s,MENU,o,&p)&&s.pc==MENU&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2a8&&get(ram,SP,4)==0x2ac2&&s.a[0]==0xc188&&s.d[0]==(d0|4)&&s.d[1]==(d1|4));
 assert(get(ram,CHILD+0x7e,2)==0xffff&&get(ram,CHILD+0x80,1)==0&&get(ram,CHILD,4)==0xc286&&s.a[6]==CHILD&&o.ports.empty()&&s.carry==ms5::AnimationCarryUnknown);
}
void errors(){
 const Physical p=resources();Bytes ram(65536,0);put(ram,SP,4,STOP);
 // Odd A6: LONG/WORD writes fail on alignment, WORD/LONG reads on the bus.
 ms5::AnimationMachineState s=state(0xc25e);s.a[6]=CHILD+1;reject(ram,s,STOP,"alignment");
 s=state(0xc27a);s.a[6]=CHILD+1;reject(ram,s,STOP,"alignment");
 s=state(0xc286);s.a[6]=CHILD+1;reject(ram,s,STOP,"even WORD/LONG");
 s=state(0xc290);s.a[6]=CHILD+1;reject(ram,s,MENU,"even WORD/LONG");
 s=state(0xc2a2);s.a[7]=0x100002;reject(ram,s,MENU,"RAM");
 // Bundled interior entries, including c28a BCS, are rejected.
 const std::uint32_t bundled[]={0xc28a,0xc28c,0xc252,0xc254,0xc256,0xc25a,0xc260,0xc26e,0xc276,0xc292,0xc298,0xc29c,0xc2a0,
  0xde434,0xde43c,0xde44a,0xde44c,0xde452,0xde470,0xde476,0xde42c,0xe7c18,0xe7c28,0xe7c2c};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){s=state(bundled[i]);reject(ram,s,STOP,"unsupported animation card child PC",&p);}
 const std::uint32_t outside[]={MENU,0xc2a8,0xc2a4,0xc24e,0xde422,0xde48c,0xe7c12,0xe7c14,0xe7c32,0xe7c34};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){s=state(outside[i]);reject(ram,s,STOP,"unsupported animation machine PC",&p);}
 s=state(0xc251);reject(ram,s,STOP,"unaligned animation machine PC");
}
#ifdef MS5_CARD_CHILD_REAL_RESOURCE_TEST
void real_resources(char**paths){
 Physical physical;std::string error;
 for(unsigned int i=0;i<3;++i){ms5::PhysicalRomResource r;assert(ms5::load_physical_rom_resource(paths[i],r,error));physical.push_back(r);}
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,NODE+0x14,2,0xffa0);put(ram,NODE+0x18,2,0x27f);ms5::AnimationMachineState s=state(0xde424);Out o;
 assert(run(ram,s,STOP,o,&physical)&&s.a[7]==SP+4&&o.dev.bank_base==0x200000&&get(ram,NODE+0x2e,4)==0xde41c&&(get(ram,NODE+0x7a,1)&0x81)==0x81);
 // Current-implementation regression over real bytes, not a native oracle: the real de40c record takes the 44032 lower allocator.
 assert(o.ports.size()==5050&&get(ram,NODE+0x26,2)==0&&get(ram,NODE+0x34,2)==31);
 std::cout<<"real de424 ports="<<o.ports.size()<<"\n";
}
#endif
}
int main(int argc,char**argv){preserving();entry();timers();menu_boundary();scene_helper();chain();errors();
#ifdef MS5_CARD_CHILD_REAL_RESOURCE_TEST
if(argc==4)real_resources(argv+1);
#else
(void)argc;(void)argv;
#endif
std::cout<<"animation_machine_card_child_test PASS "<<calls<<" API invocations\n";}
