#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
const std::uint32_t SP=0x1feffc,STOP=0xff000,CHILD=0x103000,FRAME=0xa370,NEST=0x9b58,TRAP_N=0x38c8,TRAP_L=0x38e2,TRAP_F=0xa63c;
const std::uint32_t DESC=0x104100,TEXT=0x104800,OLD_EE=0x10a0b0c0;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
// Writes a NUL-terminated string at a RAM (mirror) or ROM vector offset.
void text(Bytes&b,std::uint32_t a,const char*t,std::uint32_t mask){unsigned int i=0;for(;t[i];++i)b[(a+i)&mask]=static_cast<std::uint8_t>(t[i]);b[(a+i)&mask]=0;}
void hex(Bytes&b,std::uint32_t a,const char*h){for(unsigned int i=0;h[2*i];++i){unsigned int v=0;for(unsigned int k=0;k<2;++k){const char x=h[2*i+k];v=v*16U+static_cast<unsigned int>(x<='9'?x-'0':x-'a'+10);}b[a+i]=static_cast<std::uint8_t>(v);}}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=CHILD;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const Physical*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
// Successful run that touched no device: no ports, no external reads, returned status.
bool quiet(const Out&o){return o.ports.empty()&&o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.error.empty()&&o.dev.pvc==Out().dev.pvc;}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message,const Physical*physical=NULL,std::uint32_t bank=0x200000){
 const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;o.dev.bank_base=bank;const ms5::AnimationMachineDevice dev=o.dev;assert(!run(ram,s,stop,o,physical));
 if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
// Synthetic typed physical bytes, not a native ROM oracle: fixed 0..fffff with a copy of the
// contract's c188..c1c4 descriptor and its three strings; bank 1000 (200000) and bank 2000 (300000)
// each hold a descriptor at 200100 whose single item string differs (3 vs 7 characters).
Physical resources(){
 Physical p(3);p[0].source_rom_offset=0;p[0].data.assign(0x100000,0);
 for(unsigned int i=1;i<3;++i){p[i].source_rom_offset=0x100000U+0x100000U*i;p[i].data.assign(0x2000,0);}
 Bytes&f=p[0].data;
 hex(f,0xc188,"0000000000000000bf2c0000000000000000be60000000000000fffffffe0000000000000000be9a0000c1c400000000bea00000bf940000ffffffff");
 text(f,0xbe60,"DATA SAVE ?  ",0xfffff);text(f,0xbe9a," YES ",0xfffff);text(f,0xbea0," NO ",0xfffff);
 for(unsigned int i=1;i<3;++i){Bytes&b=p[i].data;hex(b,0x110,"00200200");hex(b,0x11a,"ffffffff");text(b,0x200,i==1?"ABC":"ABCDEFG",0x1fff);}
 return p;
}
// Card child a29c stop output: A7 holds c2a8 above the dispatcher return 2ac2, A0=c188, D0.W=D1.W=4.
ms5::AnimationMachineState menu_state(){ms5::AnimationMachineState s=state(0xa29c);s.a[0]=0xc188;s.d[0]=0xabcd0004U;s.d[1]=0xabce0004U;s.a[7]=SP-4;return s;}
Bytes menu_ram(){Bytes ram(65536,0x5a);put(ram,SP,4,0x2ac2);put(ram,SP-4,4,0xc2a8);put(ram,0x107f12,4,OLD_EE);return ram;}
// Descriptor in RAM: title, BYTE width/height, WORD flags, then item LONG pointers (10-byte records).
void desc(Bytes&ram,std::uint32_t title,std::uint32_t w,std::uint32_t h,std::uint32_t flags,const std::uint32_t*items,unsigned int n){
 put(ram,DESC,4,title);put(ram,DESC+4,1,w);put(ram,DESC+5,1,h);put(ram,DESC+0xe,2,flags);
 for(unsigned int i=0;i<n;++i){put(ram,DESC+0x10+10*i,4,items[i]);put(ram,DESC+0x14+10*i,4,0x11223344);put(ram,DESC+0x18+10*i,2,0x5566);}
}
void natural(){
 const Physical p=resources();Bytes ram=menu_ram();const Bytes start=ram;ms5::AnimationMachineState s=menu_state();const ms5::AnimationMachineState old=s;Out o;
 assert(run(ram,s,FRAME,o,&p)&&s.pc==FRAME&&quiet(o));
 // c2ba JSR a370 leaves c2c0 above 2ac2; a1e0 RTS returned to c2a8 and c2a8/a2b8 balanced.
 assert(s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0&&get(ram,SP,4)==0x2ac2&&get(ram,SP-8,4)==OLD_EE&&get(ram,SP-10,2)==13);
 // Frame 107efe: (A2)=c188, 4=0, 5 untouched, 6=4 items, 7/8=0, 9/a=D0.B/D1.B, b=2+2+13, c=4+2, d=3, e=ff, f=0.
 const std::uint32_t frame[16]={0,0,0xc1,0x88,0,0x5a,4,0,0,4,4,0x11,6,3,0xff,0};
 for(unsigned int i=0;i<16;++i)assert(get(ram,0x107efeU+i,1)==frame[i]);
 assert(get(ram,0x107f0e,4)==0x107efe&&get(ram,0x107f12,4)==OLD_EE&&get(ram,0x107f16,4)==0xe84c8&&get(ram,0x107f1a,1)==0&&get(ram,0x107f1b,1)==1);
 assert(get(ram,CHILD,4)==0xc2ba&&s.d[0]==6&&s.d[1]==old.d[1]&&s.d[2]==(old.d[2]&0xffffff00U)&&s.d[3]==old.d[3]&&s.d[7]==old.d[7]);
 assert(s.a[0]==0xe84c8&&s.a[1]==0xa008&&s.a[2]==0x107efe&&s.a[3]==0xc188&&s.a[5]==0x108000&&s.a[6]==CHILD&&s.carry==ms5::AnimationCarryUnknown);
 // a370 now continues in the card menu open unit (its own test): the opening frame returns
 // through c2c0/c2c6 to 2ac2. A stop at the still-unsupported a63c is never reached; the
 // dispatcher then follows 8(A6)=5a5a5a5a and the whole invocation rolls back.
 {Bytes r2=start;ms5::AnimationMachineState t=old;Out to;assert(run(r2,t,0x2ac2,to,&p)&&t.pc==0x2ac2&&t.a[7]==SP+4&&quiet(to));}
 reject(start,old,TRAP_F,"unsupported program bus device address",&p);
 // Walk through every reached split checkpoint in order; equals the continuous run.
 const std::uint32_t walk[]={0xa0a0,0xa0c4,0xa104,0xa15e,0xa166,0xa17e,0x38e8,0x386e,0x3878,0x38ee,0x38f4,0x38fa,0x38fe,0xa184,0xa18a,
  0xa18c,0xa198,0xa1a6,0xa1ae,0xa1ba,0xa1be,0xa1cc,0xa1d0,0xc2a8,0xa2b8,0xa2bc,0xc2b4,0xc2ba,FRAME};
 const unsigned int n=sizeof(walk)/sizeof(walk[0]);
 Bytes split=start;ms5::AnimationMachineState t=old;Out so;
 for(unsigned int i=0;i<n;++i){assert(run(split,t,walk[i],so,&p)&&t.pc==walk[i]&&quiet(so));}
 assert(split==ram&&same(t,s));
 // Fresh split at the first occurrence of each checkpoint, then continue.
 for(unsigned int i=0;i+1<n;++i){Bytes r2=start;ms5::AnimationMachineState u=old;Out uo;
  assert(run(r2,u,walk[i],uo,&p)&&u.pc==walk[i]&&run(r2,u,FRAME,uo,&p)&&r2==ram&&same(u,s));}
}
void a5_entry(){
 const Physical p=resources();
 // a29c writes -ea/-e6 and a0a0 reads -ee through the incoming A5; later accesses use 108000.
 Bytes ram=menu_ram();put(ram,0x109f12,4,0x13572468);ms5::AnimationMachineState s=menu_state();s.a[5]=0x10a000;Out o;
 assert(run(ram,s,FRAME,o,&p)&&s.a[5]==0x108000&&get(ram,0x109f16,4)==0x3650&&get(ram,0x109f1a,1)==0&&get(ram,0x109f12,4)==0x13572468);
 assert(get(ram,0x107f12,4)==0x13572468&&get(ram,0x107f16,4)==0xe84c8&&get(ram,0x107f1a,1)==0x5a&&get(ram,0x107f1b,1)==1&&get(ram,0x107f0e,4)==0x107efe);
 // A5 in ROM: the first -ea write fails; odd A5 fails LONG alignment.
 s=menu_state();s.a[5]=0x0c0000;reject(menu_ram(),s,FRAME,"write device",&p);
 s=menu_state();s.a[5]=0x108001;reject(menu_ram(),s,FRAME,"alignment",&p);
}
// One RAM descriptor run from a29c to a370; returns the final state.
ms5::AnimationMachineState desc_run(Bytes&ram,const Physical&p,std::uint32_t bank=0x200000,std::uint32_t a0=DESC){
 ms5::AnimationMachineState s=menu_state();s.a[0]=a0;Out o;o.dev.bank_base=bank;assert(run(ram,s,FRAME,o,&p)&&s.a[7]==SP-4&&o.ports.empty()&&o.dev.bank_base==bank);return s;
}
void descriptors(){
 const Physical p=resources();
 // Title with \c and \n escapes (5 counted), flags bit 2 (AND e != 0 -> D0=0), width/height larger than computed.
 {Bytes ram=menu_ram();const std::uint32_t items[]={0x104500,0,0xfffffffeU,0x104510,0xffffffffU};desc(ram,0x104400,0x30,0x20,0x0002,items,5);
  text(ram,0x104400,"\\c" "\x07" "TI\\nTLE",65535);text(ram,0x104500,"ab",65535);text(ram,0x104510,"abcdefg",65535);
  const ms5::AnimationMachineState old=menu_state();ms5::AnimationMachineState s=desc_run(ram,p);
  assert(get(ram,0x107efe,4)==DESC&&get(ram,0x107f04,1)==4&&get(ram,0x107f09,1)==0x30&&get(ram,0x107f0a,1)==0x20&&get(ram,SP-10,2)==7);
  assert(s.d[0]==6&&s.d[1]==((old.d[1]&0xffffff00U)|7)&&s.d[3]==((old.d[3]&0xffff0000U)|((old.d[3]+1U)&65535U))&&s.a[3]==DESC);}
 // No title, flags bits outside e (AND e = 0 -> D0=2), width/height smaller than computed.
 {Bytes ram=menu_ram();const std::uint32_t items[]={0x104500,0,0xfffffffeU,0x104510,0xffffffffU};desc(ram,0,3,1,0x0011,items,5);
  text(ram,0x104500,"ab",65535);text(ram,0x104510,"abcdefg",65535);desc_run(ram,p);
  assert(get(ram,0x107f04,1)==4&&get(ram,0x107f09,1)==0x0b&&get(ram,0x107f0a,1)==6);}
 // BYTE wrap: width 2+2+fe = 102 compares as 02; 255 items -> D0.W 01ff+2 = 0201 compares as 01.
 {Bytes ram=menu_ram();std::vector<std::uint32_t> items(256,0);items[0]=0x105000;items[255]=0xffffffffU;desc(ram,0,1,0,0,&items[0],256);
  std::string wide(0xfe,'w');text(ram,0x105000,wide.c_str(),65535);ms5::AnimationMachineState s=desc_run(ram,p);
  assert(get(ram,0x107f04,1)==0xff&&get(ram,0x107f09,1)==2&&get(ram,0x107f0a,1)==1&&s.d[0]==0x201&&get(ram,SP-10,2)==0xfe);}
 // ADDQ.B wrap of the item count: 256 null items count back to 0.
 {Bytes ram=menu_ram();std::vector<std::uint32_t> items(257,0);items[256]=0xffffffffU;desc(ram,0,0,0,0,&items[0],257);
  ms5::AnimationMachineState s=desc_run(ram,p);assert(get(ram,0x107f04,1)==0&&get(ram,0x107f09,1)==4&&get(ram,0x107f0a,1)==2&&s.d[0]==2);}
 // No items at all.
 {Bytes ram=menu_ram();const std::uint32_t items[]={0xffffffffU};desc(ram,0,0,0,0,items,1);
  ms5::AnimationMachineState s=desc_run(ram,p);assert(get(ram,0x107f04,1)==0&&get(ram,0x107f09,1)==4&&get(ram,0x107f0a,1)==2&&s.d[0]==2&&get(ram,SP-10,2)==0);}
 // Banked descriptor and string read through the current bank: "ABC" (bank 1000) vs "ABCDEFG" (bank 2000).
 {Bytes ram=menu_ram();desc_run(ram,p,0x200000,0x200100);assert(get(ram,0x107efe,4)==0x200100&&get(ram,0x107f09,1)==7&&get(ram,0x107f0a,1)==3);
  ram=menu_ram();desc_run(ram,p,0x300000,0x200100);assert(get(ram,0x107f09,1)==0x0b&&get(ram,0x107f0a,1)==3);}
 // ROM-free bus: the descriptor BYTE read at a104 fails atomically.
 {ms5::AnimationMachineState s=menu_state();reject(menu_ram(),s,FRAME,"missing program bus ROM");}
}
// 38e8 entered with STOP above A7; returns the final state.
ms5::AnimationMachineState width(const char*t,ms5::AnimationMachineState s,Bytes&ram){
 ram.assign(65536,0);put(ram,SP,4,STOP);text(ram,TEXT,t,65535);s.pc=0x38e8;s.a[0]=TEXT;s.a[7]=SP;Out o;
 assert(run(ram,s,STOP,o)&&s.a[7]==SP+4&&quiet(o)&&s.carry==ms5::AnimationCarryUnknown);return s;
}
void escapes(){
 ms5::AnimationMachineState s=state(0x38e8);s.d[0]=0x55550000;s.d[1]=0x6666abcd;s.d[2]=0x99999999U;s.d[3]=0x77770010;s.d[7]=0x8888ffffU;Bytes ram;
 // \n D3.W+1, \r D0.W=D3, \c low BYTE of D1, \p nibble<<8 in D1/D7 (D7 bits 16-31 kept),
 // \l 27,30: D3=0, 27<<5=4e0, BYTE add e0+30 -> 10 without carry, +7000 = 7410; \x counts 'x'.
 ms5::AnimationMachineState r=width("A\\nB\\rC\\c" "\x12" "D\\p" "\x35" "E\\l" "\x27" "\x30" "F\\xG",s,ram);
 assert(r.d[0]==0x55550008&&r.d[1]==0x66660512&&r.d[2]==0x99999900U&&r.d[3]==0x7410&&r.d[7]==0x88880500U&&r.a[0]==TEXT+24);
 // A trailing backslash then NUL: 387a reads 0, returns at 38a4, stops the count.
 r=width("Z\\",s,ram);assert(r.d[0]==0x55550001&&r.a[0]==TEXT+3&&r.d[2]==0x99999900U);
 // Empty string: count 0.
 r=width("",s,ram);assert(r.d[0]==0x55550000&&r.a[0]==TEXT+1);
 // \n WORD wrap: ffff+1 = 0 < 7500, no TRAP; D3 upper WORD kept.
 s.d[3]=0x1234ffff;r=width("\\n",s,ram);assert(r.d[3]==0x12340000&&r.d[0]==0x55550000);
 // TRAP #f boundaries: \n with D3=74ff stops at 38c8; \l 28,01 = 7501 stops at 38e2. Other stops roll back.
 for(unsigned int k=0;k<2;++k){
  ram.assign(65536,0);put(ram,SP,4,STOP);text(ram,TEXT,k?"\\l" "\x28" "\x01":"\\n",65535);
  ms5::AnimationMachineState t=state(0x38e8);t.d[3]=0x000074ff;t.a[0]=TEXT;const std::uint32_t trap=k?TRAP_L:TRAP_N;
  reject(ram,t,STOP,"unsupported animation machine PC");reject(ram,t,k?TRAP_N:TRAP_L,"unsupported animation machine PC");
  Out o;assert(run(ram,t,trap,o)&&t.pc==trap&&t.a[7]==SP-6&&get(ram,SP-6,4)==0x38ee&&get(ram,SP-2,2)==0&&quiet(o));
  assert(t.d[3]==(k?0x7501U:0x7500U)&&t.a[0]==TEXT+(k?4U:2U)&&(t.d[0]&65535U)==0x1234);}
 // Title escapes through a29c: \p sets D7 and D1, \l loads D3.
 const Physical p=resources();Bytes m=menu_ram();const std::uint32_t items[]={0xffffffffU};desc(m,0x104400,0,0,0,items,1);
 text(m,0x104400,"\\p" "\x0f" "\\l" "\x01" "\x02" "AB",65535);ms5::AnimationMachineState u=desc_run(m,p);const ms5::AnimationMachineState o0=menu_state();
 assert(u.d[7]==((o0.d[7]&0xffff0000U)|0x0f00)&&u.d[1]==((o0.d[1]&0xffff0000U)|0x0f04)&&u.d[3]==0x7022&&get(m,0x107f09,1)==6&&get(m,0x107f0a,1)==2);
}
void push_paths(){
 // a0a0 overflow: -f2=107e14 -> A2=107e04 < 107e0e; a0c2 RTS pops the pushed old -ee (a370) as the PC.
 // a370, a662 and a698 now have executors, so the unsupported-PC rollback uses a popped a63c (TRAP #f, no executor).
 Bytes ram(65536,0);put(ram,0x107f12,4,TRAP_F);put(ram,0x107f0e,4,0x107e14);ms5::AnimationMachineState s=state(0xa0a0);
 reject(ram,s,STOP,"unsupported animation machine PC");put(ram,0x107f12,4,FRAME);
 Out o;assert(run(ram,s,FRAME,o)&&s.pc==FRAME&&s.a[7]==SP&&s.a[2]==0x107e04&&s.a[5]==0x108000&&quiet(o));
 assert(get(ram,0x107f12,4)==0x107e14&&get(ram,0x107f0e,4)==0x107e14&&get(ram,SP-4,4)==FRAME);
 // Unsigned 32-bit compare edges: 107e0e takes a0c4, 107e0c takes a0c2, fffffff8 takes a0c4.
 const std::uint32_t f2[][3]={{0x107e1e,0xa0c4,0x107e0e},{0x107e1c,0xa0c2,0x107e0c},{8,0xa0c4,0xfffffff8U}};
 for(unsigned int i=0;i<3;++i){ram.assign(65536,0);put(ram,0x107f0e,4,f2[i][0]);s=state(0xa0a0);s.a[5]=0x10a000;put(ram,0x109f12,4,0x2468ace0);o=Out();
  assert(run(ram,s,f2[i][1],o)&&s.a[2]==f2[i][2]&&s.a[5]==0x108000&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x2468ace0&&get(ram,0x107f12,4)==f2[i][0]);}
 // Nested menu (-f2=107efe): a0c4 builds 107eee, A2+10 < 107f0e, a0f8 -ee=107efe and BSR 9b58.
 ram.assign(65536,0x5a);put(ram,0x107f0e,4,0x107efe);put(ram,0x107f12,4,OLD_EE);s=state(0xa0a0);const ms5::AnimationMachineState old=s;
 // 9b58 now executes (open unit): with 4(107efe)=0 it returns at 9b64 to a100; a100 BSR 9e1a pushes a104
 // and 9e1a (4=0) returns at 9e26 to a104 with the MOVEM LONGs still on the stack.
 {Bytes r2=ram;ms5::AnimationMachineState t=s;put(r2,0x107f02,1,0);Out a;
  assert(run(r2,t,0x9e1a,a)&&t.pc==0x9e1a&&t.a[7]==SP-20&&get(r2,SP-20,4)==0xa104&&quiet(a));
  a=Out();assert(run(r2,t,0xa104,a)&&t.a[7]==SP-16&&get(r2,SP-16,4)==old.d[0]&&quiet(a));}
 o=Out();assert(run(ram,s,NEST,o)&&s.pc==NEST&&s.a[7]==SP-20&&get(ram,SP-20,4)==0xa100&&quiet(o));
 // MOVEM.L D0-D1/A0,-(A7): ascending D0, D1, A0 above the old -ee LONG.
 assert(get(ram,SP-16,4)==old.d[0]&&get(ram,SP-12,4)==old.d[1]&&get(ram,SP-8,4)==old.a[0]&&get(ram,SP-4,4)==OLD_EE);
 assert(get(ram,0x107f0e,4)==0x107eee&&get(ram,0x107f12,4)==0x107efe&&get(ram,0x107ef7,4)==0xffff0000U&&get(ram,0x107ef6,1)==0x5a&&get(ram,0x107efb,1)==0x5a);
 assert(s.a[1]==0xa008&&s.a[2]==0x107efe&&s.a[5]==0x108000&&s.d[0]==old.d[0]&&s.a[0]==old.a[0]);
 // a104 restores D0/D1/A0 from the stack in ascending order.
 const Physical p=resources();ram.assign(65536,0);put(ram,SP,4,0x11112222);put(ram,SP+4,4,0x33334444);put(ram,SP+8,4,0xc188);put(ram,0x107f0e,4,0x107efe);
 s=state(0xa104);o=Out();assert(run(ram,s,0xa15e,o,&p)&&s.d[0]==0&&s.d[1]==0x33334444&&s.a[0]==0&&s.a[3]==0xc188&&s.a[7]==SP+12);
 assert(get(ram,0x107efe,4)==0xc188&&get(ram,0x107f07,1)==0x22&&get(ram,0x107f08,1)==0x44&&get(ram,0x107f12,4)==0x107efe);
 // CMP.W (A7),D0 / BLS is unsigned: 8000 > 7fff replaces, equal keeps.
 const std::uint32_t cmp[][3]={{0x7fff,0x8000,0xa18a},{0x8000,0x7fff,0xa18c},{5,5,0xa18c}};
 for(unsigned int i=0;i<3;++i){ram.assign(65536,0);put(ram,SP,2,cmp[i][0]);s=state(0xa184);s.d[0]=0x12340000U|cmp[i][1];o=Out();assert(run(ram,s,cmp[i][2],o)&&s.a[7]==SP);}
 ram.assign(65536,0);put(ram,SP,2,0x7fff);s=state(0xa184);s.d[0]=0x12348000U;o=Out();assert(run(ram,s,0xa18c,o)&&get(ram,SP,2)==0x8000);
}
void errors(){
 const Physical p=resources();
 // Odd descriptor: the item LONG read through A3 fails. Odd A2 (-f2 odd): MOVE.L A0,(A2) fails.
 Bytes ram=menu_ram();const std::uint32_t items[]={0xffffffffU};desc(ram,0,0,0,0,items,1);
 ms5::AnimationMachineState s=menu_state();s.a[0]=DESC+1;reject(ram,s,FRAME,"even WORD/LONG",&p);
 ram.assign(65536,0);put(ram,0x107f0e,4,0x107f0f);s=state(0xa0a0);s.a[0]=0xc188;reject(ram,s,FRAME,"alignment",&p);
 // Odd A7: the a0a0 LONG push fails.
 s=menu_state();s.a[7]=SP-3;reject(menu_ram(),s,FRAME,"even WORD/LONG",&p);
 // Bundled branch PCs and interior PCs are rejected by the card menu executor.
 const std::uint32_t bundled[]={0xa0be,0xa0f4,0xa154,0xa16a,0xa172,0xa17a,0xa186,0xa1a2,0xa1b6,0xa1c8,0x3874,0x3880,0x38c4,0x38de,0x38f0,0x38fc,
  0xa0a4,0xa0aa,0xa0ae,0xa0b2,0xa0b8,0xa0c8,0xa0cc,0xa0e4,0xa0e8,0xa0ee,0xa0fc,0xa102,0xa108,0xa110,0xa14a,0xa14c,0xa14e,0xa150,0xa160,0xa164,
  0xa16e,0xa176,0xa190,0xa194,0xa196,0xa19a,0xa19e,0xa1a8,0xa1b0,0xa1b2,0xa1c2,0xa1c4,0xa1d6,0xa1dc,0xa1e0,0xa2a4,0xa2aa,0xa2b4,0xa2b6,0xa2ba,
  0x3870,0x387c,0x3884,0x3888,0x388c,0x3890,0x3894,0x3898,0x389c,0x38a0,0x38aa,0x38ac,0x38b0,0x38b2,0x38b4,0x38ba,0x38bc,0x38c0,0x38cc,
  0x38d0,0x38d2,0x38d4,0x38d6,0x38da,0x38e6,0x38ec,0x38f6,0xc2ae,0xc2b0,0xc2b2,0xc2b6,0xc2b8};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){s=state(bundled[i]);reject(menu_ram(),s,STOP,"unsupported animation card menu PC",&p);}
 // Boundaries without an executor and neighbours outside the routed ranges.
 // 10fe20 replaces e84d6 (now the objects U03 glyph writer).
 const std::uint32_t outside[]={TRAP_F,0x9ee6,TRAP_N,TRAP_L,0xc00468,0xa09e,0xa1e2,0xa29a,0x10fe20,0x386c,0x3900,0xc2a6,0xc2fa};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){s=state(outside[i]);reject(menu_ram(),s,STOP,"unsupported animation machine PC",&p);}
 s=state(0xa0a1);reject(menu_ram(),s,STOP,"unaligned animation machine PC",&p);
}
const std::uint32_t LISTED[]={0xa29c,0xa0a0,0xa0c2,0xa0c4,0xa0f8,0xa100,0xa104,0xa158,0xa15e,0xa166,0xa17e,0xa184,0xa18a,0xa18c,0xa198,0xa1a6,0xa1ac,
 0xa1ae,0xa1ba,0xa1be,0xa1cc,0xa1d0,0x386e,0x3878,0x387a,0x38a4,0x38a6,0x38b6,0x38be,0x38ca,0x38ce,0x38e4,0x38e8,0x38ee,0x38f4,0x38fa,0x38fe,
 0xc2a8,0xa2b8,0xa2bc,0xc2b4,0xc2ba};
void zero_step(){
 const Physical p=resources();
 for(unsigned int carry=0;carry<3;++carry){
  const unsigned int n=sizeof(LISTED)/sizeof(LISTED[0]);
  for(unsigned int i=0;i<n+4;++i){
   const std::uint32_t pc=i<n?LISTED[i]:(i==n?FRAME:i==n+1?NEST:i==n+2?TRAP_N:TRAP_L);
   Bytes ram(65536,0x33);const Bytes before=ram;ms5::AnimationMachineState s=state(pc);s.carry=carry_of(carry);const ms5::AnimationMachineState old=s;Out o;
   assert(run(ram,s,pc,o,&p)&&same(s,old)&&ram==before&&quiet(o));}}
}
// One block from each listed PC to its next PC, with a minimal declared fixture.
std::uint32_t one_block(std::uint32_t pc,Bytes&ram,ms5::AnimationMachineState&s){
 ram.assign(65536,0);put(ram,SP,4,STOP);text(ram,TEXT,"x",65535);s=state(pc);s.a[0]=TEXT;s.a[2]=0x107efe;s.a[3]=DESC;
 switch(pc){
 case 0xa29c:return 0xa0a0;
 case 0xa0a0:put(ram,0x107f0e,4,0x107f0e);return 0xa0c4;
 case 0xa0c2:case 0x3878:case 0x38a4:case 0xa2bc:return STOP;
 case 0xa0c4:return 0xa104;
 case 0xa0f8:return NEST;
 case 0xa100:return 0x9e1a;
 case 0xa104:put(ram,SP+8,4,0xc188);put(ram,0x107f0e,4,0x107efe);return 0xa15e;
 case 0xa158:case 0xa17e:return 0x38e8;
 case 0xa15e:put(ram,DESC+0x10,4,TEXT);return 0xa166;
 case 0xa166:return 0xa17e;
 case 0xa184:put(ram,SP,2,0);s.d[0]=5;return 0xa18a;
 case 0xa18a:return 0xa18c;
 case 0xa18c:put(ram,DESC+10,4,TEXT);return 0xa166;
 case 0xa198:put(ram,0x107efe,4,DESC);return 0xa1a6;
 case 0xa1a6:case 0xa1ac:return 0xa1ae;
 case 0xa1ae:put(ram,SP,2,5);return 0xa1ba;
 case 0xa1ba:return 0xa1be;
 case 0xa1be:return 0xa1cc;
 case 0xa1cc:return 0xa1d0;
 case 0xa1d0:put(ram,SP,4,OLD_EE);put(ram,SP+4,4,STOP);return STOP;
 case 0x386e:return 0x3878;
 case 0x387a:return 0x38a4;
 case 0x38a6:case 0x38b6:case 0x38ca:case 0x38e4:case 0x38e8:case 0x38f4:return 0x386e;
 case 0x38be:s.d[3]=0;return 0x38ca;
 case 0x38ce:put(ram,TEXT,2,0x0102);return 0x38e4;
 case 0x38ee:s.d[2]=1;return 0x38f4;
 case 0x38fa:s.d[2]=0;return 0x38fe;
 case 0x38fe:put(ram,SP,2,3);put(ram,SP+2,4,STOP);return STOP;
 case 0xc2a8:return 0xa2b8;
 case 0xa2b8:return 0xa2bc;
 case 0xc2b4:return 0xc2ba;
 case 0xc2ba:return FRAME;
 default:assert(false);return 0;
 }
}
void carry(){
 const Physical p=resources();
 // Only JSR/BSR/RTS/LEA blocks keep C; ADDA/SUBA, MOVE, MOVEQ, CMP, TST, ADDQ and logic blocks give Unknown.
 const std::uint32_t keep[]={0xa0c2,0xa158,0xa17e,0x3878,0x38a4,0xc2a8,0xa2bc,0xc2ba,0xa100};
 for(unsigned int i=0;i<sizeof(LISTED)/sizeof(LISTED[0]);++i){
  bool preserve=false;for(unsigned int k=0;k<9;++k)if(keep[k]==LISTED[i])preserve=true;
  for(unsigned int carry=0;carry<3;++carry){Bytes ram;ms5::AnimationMachineState s;const std::uint32_t stop=one_block(LISTED[i],ram,s);s.carry=carry_of(carry);Out o;
   assert(run(ram,s,stop,o,&p)&&s.pc==stop&&quiet(o));
   assert(s.carry==(preserve?carry_of(carry):ms5::AnimationCarryUnknown));}}
 // Calls push their actual return LONG.
 const std::uint32_t calls_[][3]={{0xa158,0x38e8,0xa15e},{0xa17e,0x38e8,0xa184},{0x38e8,0x386e,0x38ee},{0x38f4,0x386e,0x38fa},{0xc2a8,0xa2b8,0xc2b4},{0xc2ba,FRAME,0xc2c0},{0xa0f8,NEST,0xa100},{0xa100,0x9e1a,0xa104}};
 for(unsigned int i=0;i<8;++i){Bytes ram;ms5::AnimationMachineState s;one_block(calls_[i][0],ram,s);Out o;const std::uint32_t a7=s.a[7]-(calls_[i][0]==0x38e8?6U:4U);
  assert(run(ram,s,calls_[i][1],o,&p)&&s.a[7]==a7&&get(ram,a7,4)==calls_[i][2]);}
 // a2b8 writes -ea through the live A5; c2b4 stores c2ba at (A6).
 Bytes ram;ms5::AnimationMachineState s;one_block(0xa2b8,ram,s);s.a[5]=0x109000;s.a[0]=0x13579bdf;Out o;assert(run(ram,s,0xa2bc,o)&&get(ram,0x108f16,4)==0x13579bdf);
 one_block(0xc2b4,ram,s);o=Out();assert(run(ram,s,0xc2ba,o)&&get(ram,CHILD,4)==0xc2ba);
}
}
int main(){natural();a5_entry();descriptors();escapes();push_paths();errors();zero_step();carry();
std::cout<<"animation_machine_card_menu_test PASS "<<calls<<" API invocations\n";}
