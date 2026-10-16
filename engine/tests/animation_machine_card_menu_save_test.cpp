#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef std::vector<ms5::VideoPortWrite> Ports;
typedef ms5::AnimationMachineState State;
const std::uint32_t SP=0x1feffc,STOP=0xff000,CHILD=0x103000,TOP=0x107efe,UP=0x107eee,FRAME=0xa370,RETURN=0x2ac2,CARD=0xbd26;
const std::uint32_t BIOS=0xc00468,BIOS_STATUS=0xc0046e,NAME=0x107f1c,SUM=0x107f32,STATUS=0x10fdc6;
const std::uint32_t DESC=0x104100,TEXT=0x104800,RAMNAME=0x104900,OLD_EE=0x10a0b0c0,F2=0x107f0e,EE=0x107f12,E5=0x107f1b;
const std::uint32_t P1=0x104cba,P2=0x104cc0,CARD1=0x10fdb6,CARD2=0x10fdb7;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void text(Bytes&b,std::uint32_t a,const char*t,std::uint32_t mask){unsigned int i=0;for(;t[i];++i)b[(a+i)&mask]=static_cast<std::uint8_t>(t[i]);b[(a+i)&mask]=0;}
void hex(Bytes&b,std::uint32_t a,const char*h){for(unsigned int i=0;h[2*i];++i){unsigned int v=0;for(unsigned int k=0;k<2;++k){const char x=h[2*i+k];v=v*16U+static_cast<unsigned int>(x<='9'?x-'0':x-'a'+10);}b[a+i]=static_cast<std::uint8_t>(v);}}
State state(std::uint32_t pc){State s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=CHILD;s.a[7]=SP;return s;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
// Synthetic typed physical bytes (not a native ROM oracle): the contract's ROM rows for the c188
// descriptor and strings, the bb8e name, the be84/be8f result strings and the c214/c232 descriptors.
Physical make_resources(){
 Physical p(1);p[0].source_rom_offset=0;p[0].data.assign(0x100000,0);Bytes&f=p[0].data;
 hex(f,0xc188,"0000000000000000bf2c0000000000000000be60000000000000fffffffe0000000000000000be9a0000c1c400000000bea00000bf940000ffffffff");
 text(f,0xbe60,"DATA SAVE ?  ",0xfffff);text(f,0xbe9a," YES ",0xfffff);text(f,0xbea0," NO ",0xfffff);
 hex(f,0xbb8e,"4d4554414c20534c55472056332020202020202000");
 hex(f,0xbe84,"53415645204f4b2e2020004e4f20534156452e202000");
 hex(f,0xc214,"0000000000000000bf2c0000000000000000be840000bf940000ffffffff0000000000000000bf2c0000000000000000be8f0000bf940000ffffffff");
 return p;
}
const Physical ROM=make_resources();
struct Out {ms5::AnimationMachineDevice dev;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;bus.physical_rom=&ROM;std::vector<ms5::FixedDataResource>w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
// Successful run: no external reads, returned status, PVC untouched (3c0000 events are ports only).
bool clean(const Out&o){return o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.error.empty()&&o.dev.pvc==Out().dev.pvc&&o.dev.bank_base==0x200000;}
bool quiet(const Out&o){return clean(o)&&o.ports.empty();}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message){
 const Bytes before=ram;const State old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;++calls;ms5::ProgramBusState bus;bus.physical_rom=&ROM;std::vector<ms5::FixedDataResource>w;
 if(ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error)){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error.find(message)==std::string::npos)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
bool same_ports(const Ports&a,const Ports&b){if(a.size()!=b.size()){std::cerr<<std::dec<<"ports "<<a.size()<<" vs "<<b.size()<<"\n";return false;}
 for(unsigned int i=0;i<a.size();++i)if(a[i].address!=b[i].address||a[i].size!=b[i].size||a[i].value!=b[i].value){std::cerr<<std::hex<<"port "<<i<<" "<<a[i].value<<" vs "<<b[i].value<<"\n";return false;}return true;}
void append(Ports&all,const Ports&part){for(unsigned int i=0;i<part.size();++i)all.push_back(part[i]);}
// Independent bb74 checksum: per BYTE, sign-extend, add, double (C = old bit 15), NOT on C, add 3c5b.
std::uint32_t checksum(const Bytes&ram,std::uint32_t at,unsigned int n){
 int sum=0;
 for(unsigned int i=0;i<n;++i){int v=static_cast<int>(get(ram,at+i,1));if(v>=128)v-=256;
  sum=(sum+v+65536)%65536;const bool carry=sum>=32768;sum=(sum*2)%65536;if(carry)sum=65535-sum;sum=(sum+0x3c5b)%65536;}
 return static_cast<std::uint32_t>(sum);}
// Expected video events (same equations as the open/input unit tests).
std::uint32_t cell(std::uint32_t x,std::uint32_t y){return ((((x<<5)&0xff00U)|(((x<<5)+y)&0xffU))+0x7000U)&65535U;}
void port(Ports&v,unsigned int size,std::uint32_t value){ms5::VideoPortWrite p;p.address=0x3c0000;p.size=static_cast<std::uint8_t>(size);p.value=value;v.push_back(p);}
void tile_row(Ports&v,std::uint32_t a,std::uint32_t pal,std::uint32_t first,std::uint32_t mid,std::uint32_t last,unsigned int n){
 port(v,4,(a<<16)|(pal<<8)|first);for(unsigned int i=1;i<=n;++i)port(v,4,(((a+0x20U*i)&65535U)<<16)|(pal<<8)|mid);
 port(v,4,(((a+0x20U*(n+1))&65535U)<<16)|(pal<<8)|last);}
void box(Ports&v,std::uint32_t x,std::uint32_t y,unsigned int w,unsigned int h,std::uint32_t pal){
 const unsigned int n=w>2?w-2:0;std::uint32_t a=cell(x,y);tile_row(v,a,pal,0xf4,0xf0,0xf5,n);
 for(unsigned int r=h;r>2;--r){a=(a+1U)&65535U;tile_row(v,a,pal,0xf2,0x60,0xf3,n);}
 a=(a+1U)&65535U;tile_row(v,a,pal,0xf6,0xf1,0xf7,n);}
std::uint32_t text_ports(Ports&v,std::uint32_t a,std::uint32_t d1,const char*t){
 std::uint32_t w=d1&65535U;w=(w&0xff00U)|((w<<4)&0xffU);w=(w<<4)&65535U;
 for(unsigned int i=0;t[i];++i){port(v,4,(a<<16)|(w&0xff00U)|static_cast<unsigned char>(t[i]));port(v,2,0x8200);a=(a+0x20U)&65535U;}return a;}
void cursor(Ports&v,std::uint32_t a,bool selected){port(v,4,(a<<16)|(selected?0x313U:0xffU));port(v,4,(((a+0x20U)&65535U)<<16)|(selected?0x314U:0xffU));}
void separator(Ports&v,std::uint32_t a,std::uint32_t b){
 if(b<2)return;port(v,4,(a<<16)|0xbf8U);std::uint32_t d7=(b-3U)&255U;a=(a+0x20U)&65535U;
 while(d7>=2){port(v,4,(a<<16)|0xbf9U);a=(a+0x20U)&65535U;d7=(d7-1U)&65535U;}
 if(d7==1)port(v,4,(a<<16)|0xbfaU);}
std::uint32_t item_row(std::uint32_t x,std::uint32_t y,std::uint32_t index){const std::uint32_t a=(cell(x,y)+0x20U)&65535U;return (a&0xff00U)|((a+1U+index)&0xffU);}
const char* const LABEL[4]={"DATA SAVE ?  ",""," YES "," NO "};
// 9d3a row with the text palette from 9f7c: 0003 for the cursor row, 0603 for other rows of a menu below -f2.
void row(Ports&e,unsigned int i,bool selected,std::uint32_t pal){cursor(e,item_row(4,4,i),selected);text_ports(e,(item_row(4,4,i)+0x40U)&65535U,pal,LABEL[i]);}
// Expected nested push redraw: 9b58 box of the older c188 menu (A2=107efe != -f2=107eee: palette 6b; the new
// frame has b=0, so a018 covers nothing), then 9e1a rows (no title) with cursor 7=2 on YES.
Ports redraw(){Ports e;box(e,4,4,0x11,6,0x6b);row(e,0,false,0x0603);separator(e,item_row(4,4,1),0x11);row(e,2,true,0x0003);row(e,3,false,0x0603);return e;}
// Declared host changes before a frame: card BYTEs 10fdb6/10fdb7 and input edge BYTEs 104cba/104cc0.
void inputs(Bytes&ram,std::uint32_t card1,std::uint32_t card2,std::uint32_t p1,std::uint32_t p2){
 put(ram,CARD1,1,card1);put(ram,CARD2,1,card2);put(ram,P1,1,p1);put(ram,P2,1,p2);}
bool frame(Bytes&ram,State&s,std::uint32_t c1,std::uint32_t c2,std::uint32_t p1,std::uint32_t p2,std::uint32_t stop,Out&o){
 inputs(ram,c1,c2,p1,p2);s.pc=0x2ab8;return run(ram,s,stop,o);}
// Declared BIOS resume: PC = the JSR return LONG, A7+4, carry Unknown (10fdc6 is declared by the caller).
void resume(const Bytes&ram,State&s,std::uint32_t pc){assert(get(ram,s.a[7],4)==pc);s.pc=pc;s.a[7]+=4U;s.carry=ms5::AnimationCarryUnknown;}
// Chained stops through a subsequence of the actual trace equal the continuous run; so does a
// fresh split at each checkpoint followed by a continuation.
void splits(const Bytes&start,const State&old,const Bytes&ram,const State&s,const Ports&ports,const std::uint32_t*walk,unsigned int n){
 Bytes split=start;State t=old;Ports all;
 for(unsigned int i=0;i<n;++i){Out so;if(!(run(split,t,walk[i],so)&&t.pc==walk[i]&&clean(so)))std::cerr<<std::hex<<"walk "<<walk[i]<<"\n";
  assert(t.pc==walk[i]&&clean(so));append(all,so.ports);}
 assert(split==ram&&same(t,s)&&same_ports(all,ports));
 for(unsigned int i=0;i+1<n;++i){Bytes r2=start;State u=old;Out a,b;
  assert(run(r2,u,walk[i],a)&&u.pc==walk[i]&&run(r2,u,walk[n-1],b)&&r2==ram&&same(u,s));append(a.ports,b.ports);assert(same_ports(a.ports,ports));}
}
// Natural chain (input unit C++ outputs): card child c290 entry -> a29c push -> opening/full frames ->
// first input frame -> up frame (bit0: cursor 3 -> 2, YES). Residual 5(A2)=88, sound gates clear,
// empty 104d82 WORD ring and 0x5a RAM fill as in the open/input unit tests.
Bytes up_ram;State up_state;
void to_yes(){
 Bytes ram(65536,0x5a);put(ram,SP,4,RETURN);put(ram,EE,4,OLD_EE);put(ram,TOP+5,1,0x88);
 put(ram,0x100012,1,0);put(ram,0x104d7e,1,0);put(ram,0x10f001,1,0);put(ram,0x104d8a,2,0);put(ram,0x104d8c,2,0);
 put(ram,CHILD+0x76,4,0xc188);put(ram,CHILD+0x7a,2,4);put(ram,CHILD+0x7c,2,4);State s=state(0xc290);
 Out o;assert(run(ram,s,FRAME,o)&&s.pc==FRAME&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0);
 o=Out();assert(run(ram,s,RETURN,o)&&s.pc==RETURN&&get(ram,TOP+4,2)==0x0208);
 for(unsigned int k=0;k<4;++k){assert(get(ram,CHILD,4)==0xc2ba);s.pc=0x2ab8;o=Out();assert(run(ram,s,RETURN,o)&&s.pc==RETURN&&clean(o));}
 assert(get(ram,TOP+7,1)==3&&get(ram,CHILD+0x7e,2)==0x012c&&get(ram,TOP+4,2)==0x0600);
 o=Out();assert(frame(ram,s,0,0,0,0,RETURN,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x012b&&get(ram,TOP+0xe,1)==0xff);
 o=Out();assert(frame(ram,s,1,0,0x01,0,RETURN,o)&&clean(o)&&get(ram,TOP+7,1)==2&&get(ram,TOP+8,1)==2&&get(ram,CHILD+0x7e,2)==0x012a);
 assert(get(ram,0x104d82,2)==0x1a6c&&get(ram,0x104d8c,2)==2&&get(ram,E5,1)==0&&get(ram,F2,4)==TOP&&get(ram,EE,4)==TOP&&s.a[7]==SP+4);
 // Name area and BIOS parameter BYTEs still hold the 0x5a fill.
 for(unsigned int i=0;i<0x18;++i)assert(get(ram,NAME+i,1)==0x5a);
 up_ram=ram;up_state=s;
}
const char METAL[]="METAL SLUG V3       ";
// Select frame (P2 bit4 with 10fdb7=1: event 3) from the YES snapshot, to the first BIOS stop.
Bytes bios1_ram;State bios1;
void select_to_bios(){
 Bytes ram=up_ram;State s=up_state;inputs(ram,0,1,0,0x10);s.pc=0x2ab8;const Bytes start=ram;const State old=s;
 reject(start,old,RETURN,"unsupported animation machine PC"); // c00468 has no executor
 Out o;assert(run(ram,s,BIOS,o)&&s.pc==BIOS&&quiet(o));
 // Stack: bd60 (JSR c00468) above the saved A6, c1ea (BSR bd26), a5c6 (BSR 9b3e), pushed A2 and c2c0.
 assert(s.a[7]==SP-24&&get(ram,SP-24,4)==0xbd60&&get(ram,SP-20,4)==CHILD&&get(ram,SP-16,4)==0xc1ea&&get(ram,SP-12,4)==0xa5c6);
 assert(get(ram,SP-8,4)==TOP&&get(ram,SP-4,4)==0xc2c0&&s.a[6]==CHILD&&s.a[5]==0x108000);
 // bbb8 copied the 20 characters (no NUL: the D7 borrow ends the loop first); 107f30/31 keep the fill.
 for(unsigned int i=0;i<20;++i)assert(get(ram,NAME+i,1)==static_cast<unsigned char>(METAL[i]));
 assert(get(ram,NAME+20,2)==0x5a5a);
 // bb74 over 22 BYTEs, WORD to -ce(A5) = 107f32; independent computation.
 const std::uint32_t sum=checksum(ram,NAME,22);assert(get(ram,SUM,2)==sum&&s.d[0]==sum&&s.a[0]==NAME+22&&s.a[1]==0xbba2);
 assert((s.d[7]&65535U)==0&&(s.d[1]&65535U)==0x005a);
 assert(get(ram,0x10fdc4,1)==4&&get(ram,0x10fdce,2)==0x0268&&get(ram,0x10fdd0,1)==0&&get(ram,0x10fdc8,4)==0x5a5a5a5a&&get(ram,0x10fdcc,2)==0x5a5a);
 assert(get(ram,TOP+7,1)==2&&get(ram,TOP+8,1)==2&&get(ram,CHILD+0x80,1)==0&&get(ram,CHILD+0x7e,2)==0x0129&&get(ram,0x104d8c,2)==2);
 const std::uint32_t walk[]={0xa582,0xa5aa,0xa5b4,0x9b3e,0xc1c4,0xa73e,0xa754,0xc1ca,0xc1de,0xc1e6,CARD,0xbbb8,0xbbba,0xbbc0,0xbbba,0xbbd0,
  0xbd34,0xbb74,0xbb76,0xbb84,0xbb8c,0xbd3c,BIOS};
 splits(start,old,ram,s,o.ports,walk,sizeof(walk)/sizeof(walk[0]));
 bios1_ram=ram;bios1=s;
}
// Second and third BIOS boundaries, then the result branch.
Bytes status_ram;State status_state;
void bios_chain(){
 Bytes ram=bios1_ram;State s=bios1;resume(ram,s,0xbd60);
 reject(ram,s,RETURN,"unsupported animation machine PC");
 Out o;assert(run(ram,s,BIOS,o)&&quiet(o)&&s.a[7]==SP-24&&get(ram,SP-24,4)==0xbd90&&get(ram,SP-20,4)==CHILD);
 assert(get(ram,0x10fdc4,1)==3&&get(ram,0x10fdce,2)==0x0268&&get(ram,0x10fdd0,1)==0&&get(ram,0x10fdc8,4)==NAME&&get(ram,0x10fdcc,2)==0x0018);
 assert(s.carry==ms5::AnimationCarryUnknown);
 resume(ram,s,0xbd90);reject(ram,s,RETURN,"unsupported animation machine PC");
 {const Bytes start=ram;const State old=s;o=Out();assert(run(ram,s,BIOS_STATUS,o)&&quiet(o));
  assert(s.a[7]==SP-24&&get(ram,SP-24,4)==0xbe1c&&get(ram,SP-20,4)==CHILD&&get(ram,0x10fdc2,1)==0&&s.a[6]==CHILD);
  const std::uint32_t walk[]={0xbe0c,BIOS_STATUS};splits(start,old,ram,s,o.ports,walk,2);}
 resume(ram,s,0xbe1c);status_ram=ram;status_state=s;
}
// Result: 10fdc6=0 -> be2e Set -> c1ee SAVE OK (c214); else be34 Clear -> c202 NO SAVE (c232).
void result(std::uint32_t status,bool ok){
 Bytes ram=status_ram;State s=status_state;put(ram,STATUS,1,status);const Bytes start=ram;const State old=s;
 const std::uint32_t d0=0x00000007U;Out o;
 // 9f36 rows/columns: D0 = 2 (flags e(c188)&e = 0) + 9 + 1, D1 = a + 1 + 8 (cursor 2), A0 = YES text.
 {Bytes r=ram;State t=s;Out a;assert(run(r,t,ok?0xc1f4:0xc208,a)&&quiet(a)&&t.d[0]==d0&&t.d[1]==7&&t.d[2]==2&&t.a[0]==0xbe9a);
  assert((t.d[7]&65535U)==0x14&&t.d[7]==0x14&&t.a[2]==TOP&&t.a[3]==0xc188&&t.carry==ms5::AnimationCarryUnknown);}
 assert(run(ram,s,RETURN,o)&&s.pc==RETURN&&clean(o)&&same_ports(o.ports,redraw()));
 // New frame 107eee: (A2)=result descriptor, 9/a from 9f36, b=e (10 chars + 2 + 2), c=3, one item.
 assert(get(ram,UP,4)==(ok?0xc214U:0xc232U)&&get(ram,UP+4,1)==0&&get(ram,UP+5,1)==0x5a&&get(ram,UP+6,1)==1&&get(ram,UP+7,1)==0&&get(ram,UP+8,1)==0);
 assert(get(ram,UP+9,1)==7&&get(ram,UP+0xa,1)==7&&get(ram,UP+0xb,1)==0x0e&&get(ram,UP+0xc,1)==3&&get(ram,UP+0xd,1)==3&&get(ram,UP+0xe,1)==0xff&&get(ram,UP+0xf,1)==0);
 // -f2=107eee, -ee restored to the older 107efe by a1d0 (then a5c6), -e5=1 (open next frame).
 assert(get(ram,F2,4)==UP&&get(ram,EE,4)==TOP&&get(ram,E5,1)==1);
 // The older frame keeps its geometry; 9e1a left its 8(A2) at the last row (3).
 assert(get(ram,TOP,4)==0xc188&&get(ram,TOP+4,2)==0x0600&&get(ram,TOP+7,1)==2&&get(ram,TOP+8,1)==3&&get(ram,TOP+0xe,1)==0xff);
 // Name and checksum untouched after the BIOS stops; sound 1adb queued behind the pending 1a6c.
 for(unsigned int i=0;i<20;++i)assert(get(ram,NAME+i,1)==static_cast<unsigned char>(METAL[i]));
 assert(get(ram,SUM,2)==checksum(ram,NAME,22)&&get(ram,STATUS,1)==status);
 assert(get(ram,0x104d82,2)==0x1a6c&&get(ram,0x104d84,2)==0x1adb&&get(ram,0x104d8c,2)==4);
 assert(s.a[7]==SP+4&&s.a[6]==CHILD&&s.a[5]==0x108000&&s.a[2]==TOP&&s.d[0]==0&&get(ram,CHILD+0x80,1)==0&&get(ram,CHILD,4)==0xc2ba);
 const std::uint32_t set_walk[]={0xbe1c,0xbe2e,0xc1ea,0xc1ee,0x9f36,0x9f48,0x9f50,0xc1f4,0xa71a,0xa0a0,0xa0c4,0xa0f8,0x9b58,0xa100,0x9e1a,
  0xa104,0xa1d0,0xa720,0x3af8,0xa72a,0xc1fe,0xc212,0xa5c6,0xa5aa,0xa5ce,0xc2c0,0xc2c6,RETURN};
 const std::uint32_t clear_walk[]={0xbe1c,0xbe34,0xc1ea,0xc202,0x9f36,0x9f48,0x9f50,0xc208,0xa71a,0xa0a0,0xa0c4,0xa0f8,0x9b58,0xa100,0x9e1a,
  0xa104,0xa1d0,0xa720,0x3af8,0xa72a,0xc212,0xa5c6,0xa5aa,0xa5ce,0xc2c0,0xc2c6,RETURN};
 if(ok)splits(start,old,ram,s,o.ports,set_walk,sizeof(set_walk)/sizeof(set_walk[0]));
 else splits(start,old,ram,s,o.ports,clear_walk,sizeof(clear_walk)/sizeof(clear_walk[0]));
 // The known carry reaches c1ea: Set at the be2e RTS, Clear at the be34 RTS.
 {Bytes r=start;State t=old;Out a;assert(run(r,t,0xc1ea,a)&&t.carry==(ok?ms5::AnimationCarrySet:ms5::AnimationCarryClear)&&t.a[7]==SP-12&&t.a[5]==0x108000);}
}
void natural(){
 to_yes();select_to_bios();bios_chain();
 result(0,true);result(1,false);result(0x80,false);result(0xff,false);
}
// 107f30/31 are summed as they are in RAM: the checksum follows them (including the NOT path).
void checksum_edges(){
 const std::uint32_t tails[][2]={{0,0},{0xff,0x80},{0x7f,0x01},{0x80,0x80},{0x12,0xfe}};
 for(unsigned int i=0;i<5;++i){Bytes ram=up_ram;State s=up_state;put(ram,NAME+20,1,tails[i][0]);put(ram,NAME+21,1,tails[i][1]);inputs(ram,0,1,0,0x10);s.pc=0x2ab8;
  Out o;assert(run(ram,s,BIOS,o)&&get(ram,SUM,2)==checksum(ram,NAME,22)&&(s.d[0]&65535U)==get(ram,SUM,2));}
 // The checksum function itself against hand-derived steps: one BYTE 00 from D0=0 -> 3c5b;
 // BYTE 80: ff80 -> doubling carries (ff00), NOT 00ff, + 3c5b = 3d5a.
 Bytes b(65536,0);assert(checksum(b,0x1000,1)==0x3c5b);put(b,0x1000,1,0x80);assert(checksum(b,0x1000,1)==0x3d5a);
}
// RAM fixture: -f2=-ee=TOP (c188-like RAM descriptor: flags 0, 4 items, cursor 2), name area 104900 zero,
// "AB" at TEXT, STOP LONGs on the stack, A2=TOP, A0=RAMNAME, A1=TEXT.
void generic(std::uint32_t pc,Bytes&ram,State&s){
 ram.assign(65536,0);for(unsigned int i=0;i<8;++i)put(ram,SP+4*i,4,STOP);put(ram,F2,4,TOP);put(ram,EE,4,TOP);put(ram,0x107f16,4,0xe84c8);
 put(ram,TOP,4,DESC);put(ram,TOP+4,1,6);put(ram,TOP+6,1,4);put(ram,TOP+7,1,2);put(ram,TOP+8,1,2);put(ram,TOP+9,1,4);put(ram,TOP+0xa,1,4);
 put(ram,TOP+0xb,1,0x11);put(ram,TOP+0xc,1,6);put(ram,TOP+0xd,1,3);put(ram,TOP+0xe,1,0xff);
 const std::uint32_t items[]={TEXT,0xfffffffeU,TEXT,TEXT},cb[]={0,0,0xc1c4,0xbf94};
 for(unsigned int i=0;i<4;++i){put(ram,DESC+0x10+10*i,4,items[i]);put(ram,DESC+0x14+10*i,4,cb[i]);}
 put(ram,DESC+0x38,4,0xffffffffU);text(ram,TEXT,"AB",65535);
 s=state(pc);s.a[0]=RAMNAME;s.a[1]=TEXT;s.a[2]=TOP;}
// Every block start {pc, next with C clear, next with C set} from the generic fixture.
const std::uint32_t TABLE[][3]={
 {0x9f36,0x9f48,0x9f48},{0x9f48,0x9f50,0x9f50},{0x9f4e,0x9f50,0x9f50},{0x9f50,STOP,STOP},{0xa100,0x9e1a,0x9e1a},
 {0xa71a,0xa0a0,0xa0a0},{0xa720,0x3af8,0x3af8},{0xa72a,STOP,STOP},{0xbb74,0xbb76,0xbb76},{0xbb76,0xbb84,0xbb84},
 {0xbb82,0xbb84,0xbb84},{0xbb84,0xbb76,0xbb76},{0xbb8c,STOP,STOP},{0xbbb8,0xbbba,0xbbba},{0xbbba,0xbbc0,0xbbc0},
 {0xbbc0,0xbbba,0xbbba},{0xbbc4,0xbbca,0xbbca},{0xbbca,0xbbc4,0xbbc4},{0xbbd0,STOP,STOP},{CARD,0xbbb8,0xbbb8},
 {0xbd34,0xbb74,0xbb74},{0xbd3c,BIOS,BIOS},{0xbd60,BIOS,BIOS},{0xbd90,0xbe0c,0xbe0c},{0xbe0c,BIOS_STATUS,BIOS_STATUS},
 {0xbe1c,0xbe2e,0xbe2e},{0xbe2e,STOP,STOP},{0xbe34,STOP,STOP},{0xc1ea,0xc202,0xc1ee}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
// Blocks made only of BSR/JSR/BRA/RTS/MOVEA/BCC (capstone classification of the original opcodes).
// bbb8/be0c (MOVE.L An,-(A7)) and MOVE/MOVEQ/EXT/ADD/NOT/ADDI/SUBQ/ANDI/MULU/TST blocks give Unknown.
const std::uint32_t KEEP[]={0xa100,0xa71a,0xa72a,0xbb8c,0xbbd0,0xbd90,0xc1ea};
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
void fixtures(){
 // bbb8 D7=0: borrow at once, nothing written, A0 restored; D7 high WORD kept.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.d[7]=0x12340000U;const Bytes before=ram;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&s.d[7]==0x1234ffffU&&s.a[0]==RAMNAME&&s.a[1]==TEXT&&s.a[7]==SP+4);
  Bytes b=before;put(b,SP-4,4,RAMNAME);assert(ram==b);} // only the pushed A0 LONG changed
 // Short NUL-terminated string "AB" with D7=6: A, B and the NUL are moved, then 3 zero BYTEs; 7th BYTE untouched.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.d[7]=0x00050006U;for(unsigned int i=0;i<8;++i)put(ram,RAMNAME+i,1,0xee);Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,RAMNAME,4)==0x41420000U&&get(ram,RAMNAME+4,2)==0&&get(ram,RAMNAME+6,2)==0xeeee);
  assert(s.d[7]==0x0005ffffU&&s.a[0]==RAMNAME&&s.a[1]==TEXT+3&&s.a[7]==SP+4);}
 // Exact length: "AB" with D7=2 copies two BYTEs and no NUL.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.d[7]=2;put(ram,RAMNAME+2,1,0xee);Out o;assert(run(ram,s,STOP,o)&&get(ram,RAMNAME,2)==0x4142&&get(ram,RAMNAME+2,1)==0xee&&s.a[1]==TEXT+2);}
 // Odd A0/A1: BYTE copies are legal at odd addresses.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.d[7]=3;s.a[0]=RAMNAME+1;s.a[1]=TEXT+1;Out o;assert(run(ram,s,STOP,o)&&get(ram,RAMNAME,4)==0x00420000U&&s.a[0]==RAMNAME+1);}
 // The copy source is the live bus: ROM bb8e (fixed) and the RAM mirror read the same way.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.d[7]=0x14;s.a[1]=0xbb8e;Out o;assert(run(ram,s,STOP,o)&&s.a[1]==0xbba2);
  for(unsigned int i=0;i<20;++i)assert(get(ram,RAMNAME+i,1)==static_cast<unsigned char>(METAL[i]));assert(get(ram,RAMNAME+20,1)==0);}
 // bb76: EXT.W keeps D1's high WORD; ADD.W/ADD.W carry -> bb82 NOT.W; D0 high WORD kept; ADDI.W and SUBQ.W wrap.
 {Bytes ram;State s;generic(0xbb76,ram,s);s.d[0]=0x12348000U;s.d[1]=0x5678abcdU;put(ram,RAMNAME,1,0);Out o;
  assert(run(ram,s,0xbb82,o)&&s.d[0]==0x12340000U&&s.d[1]==0x56780000U&&s.a[0]==RAMNAME+1);
  s.d[7]=0x99990001U;o=Out();assert(run(ram,s,0xbb8c,o)&&s.d[0]==0x12343c5aU&&s.d[7]==0x99990000U);}
 {Bytes ram;State s;generic(0xbb76,ram,s);s.d[0]=0x00004000U;s.d[1]=0x5678abcdU;put(ram,RAMNAME,1,0x80);Out o;
  assert(run(ram,s,0xbb84,o)&&s.d[1]==0x5678ff80U&&s.d[0]==0x00007f00U);} // 4000+ff80=3f80, doubled 7f00, no C
 {Bytes ram;State s;generic(0xbb84,ram,s);s.d[0]=0xaaaac400U;s.d[7]=0x00000000U;Out o;assert(run(ram,s,0xbb76,o)&&s.d[0]==0xaaaa005bU&&s.d[7]==0x0000ffffU);}
 // bb74 MOVEQ #0 clears all 32 bits; a full bb74 over RAM BYTEs equals the independent checksum.
 {Bytes ram;State s;generic(0xbb74,ram,s);const std::uint32_t v[]={0x80,0x7f,0xff,0x01,0xc3,0x00,0x5a};for(unsigned int i=0;i<7;++i)put(ram,RAMNAME+i,1,v[i]);
  s.d[7]=0xffff0007U;Out o;assert(run(ram,s,STOP,o)&&s.d[0]==checksum(ram,RAMNAME,7)&&s.d[7]==0xffff0000U&&s.a[0]==RAMNAME+7);}
 // bd26/bd3c use the live A5: -e4 and -ce from A5=109000.
 {Bytes ram;State s;generic(CARD,ram,s);s.a[5]=0x109000;Out o;assert(run(ram,s,BIOS,o)&&s.a[5]==0x109000);
  for(unsigned int i=0;i<20;++i)assert(get(ram,0x108f1c+i,1)==static_cast<unsigned char>(METAL[i]));
  assert(get(ram,0x108f32,2)==checksum(ram,0x108f1c,22)&&get(ram,SUM,2)==0&&get(ram,NAME,4)==0);}
 // MOVE.W #16,D7 at bd34 keeps D7's high WORD.
 {Bytes ram;State s;generic(0xbd34,ram,s);s.d[7]=0x12345678U;Out o;assert(run(ram,s,0xbb74,o)&&s.d[7]==0x12340016U&&get(ram,SP-4,4)==0xbd3c);}
 // Direct be0c entry: the c0046e stop, then declared 10fdc6 0/1/80: be1c pops the stacked A6 and sets A5.
 const std::uint32_t st[]={0,1,0x80};
 for(unsigned int i=0;i<3;++i){Bytes ram;State s;generic(0xbe0c,ram,s);s.a[6]=0x10abcd;put(ram,0x10fdc2,1,0x77);Out o;
  assert(run(ram,s,BIOS_STATUS,o)&&quiet(o)&&get(ram,0x10fdc2,1)==0&&s.a[7]==SP-8&&get(ram,SP-8,4)==0xbe1c&&get(ram,SP-4,4)==0x10abcd);
  put(ram,SP-4,4,0x10fe00);put(ram,STATUS,1,st[i]);resume(ram,s,0xbe1c);s.a[5]=0x123456;s.carry=carry_of(i);o=Out();
  assert(run(ram,s,STOP,o)&&quiet(o)&&s.a[6]==0x10fe00&&s.a[5]==0x108000&&s.a[7]==SP+4);
  assert(s.carry==(st[i]==0?ms5::AnimationCarrySet:ms5::AnimationCarryClear));}
 // bd60: the five BIOS parameter writes in original sizes (BYTE c4/d0, WORD ce/cc, LONG c8) and nothing else.
 {Bytes ram;State s;generic(0xbd60,ram,s);for(unsigned int i=0;i<18;++i)put(ram,0x10fdc0+i,1,0xa5);Out o;assert(run(ram,s,BIOS,o)&&quiet(o));
  assert(get(ram,0x10fdc0,4)==0xa5a5a5a5U&&get(ram,0x10fdc4,4)==0x03a5a5a5U&&get(ram,0x10fdc8,4)==0x00107f1cU&&get(ram,0x10fdcc,4)==0x00180268U&&get(ram,0x10fdd0,2)==0x00a5&&get(ram,SP-4,4)==0xbd90);}
 {Bytes ram;State s;generic(0xbd3c,ram,s);for(unsigned int i=0;i<18;++i)put(ram,0x10fdc0+i,1,0xa5);s.d[0]=0xffff1357U;Out o;assert(run(ram,s,BIOS,o)&&quiet(o));
  assert(get(ram,0x10fdc0,4)==0xa5a5a5a5U&&get(ram,0x10fdc4,4)==0x04a5a5a5U&&get(ram,0x10fdc8,4)==0xa5a5a5a5U&&get(ram,0x10fdcc,4)==0xa5a50268U);
  assert(get(ram,0x10fdd0,2)==0x00a5&&get(ram,SUM,2)==0x1357&&s.a[7]==SP-8&&get(ram,SP-4,4)==CHILD&&get(ram,SP-8,4)==0xbd60);}
 // 9f36 flags e(desc)&e != 0 -> D0=0; MULU.W is 32-bit; MOVEA.L (A0,D7.W) sign-extends the WORD index.
 {Bytes ram;State s;generic(0x9f36,ram,s);put(ram,DESC+0xe,2,0xfff2);s.d[0]=0x55555555U;Out o;assert(run(ram,s,0x9f4e,o)&&s.d[0]==0x55550002U);
  o=Out();assert(run(ram,s,STOP,o)&&s.d[0]==5&&s.d[1]==7&&s.d[2]==2&&s.d[7]==20&&s.a[0]==TEXT);}
 {Bytes ram;State s;generic(0x9f50,ram,s);put(ram,TOP+8,1,0xff);put(ram,TOP+9,1,0xfe);put(ram,TOP+0xa,1,0x01);s.d[0]=0x00000002U;
  put(ram,DESC+0x10+0x9f6,4,0x13572468);Out o;
  assert(run(ram,s,STOP,o)&&s.d[0]==1&&s.d[1]==1&&s.d[2]==0xff&&s.d[7]==0x9f6&&s.a[0]==0x13572468);} // ff*a = 9f6 (positive WORD)
 {Bytes ram;State s;generic(0x9f50,ram,s);put(ram,TOP+8,1,0xd0);put(ram,TOP,4,0x105000);put(ram,0x105010+0x820,4,0x2468ace0);Out o;
  assert(run(ram,s,STOP,o)&&s.d[7]==0x820&&s.a[0]==0x2468ace0);}
 // D7.W = 8(A2)*a is at most 9f6, so the sign-extended index of MOVEA.L (A0,D7.W) is never negative here.
 // a720: D0 high WORD kept; JSR 3af8 return a72a.
 {Bytes ram;State s;generic(0xa720,ram,s);s.d[0]=0x77770000U;Out o;assert(run(ram,s,0x3af8,o)&&s.d[0]==0x77771adbU&&get(ram,SP-4,4)==0xa72a);}
 // c1ea consumes the known C and keeps it.
 for(unsigned int carry=1;carry<3;++carry){Bytes ram;State s;generic(0xc1ea,ram,s);s.carry=carry_of(carry);Out o;
  const std::uint32_t next=carry_of(carry)==ms5::AnimationCarryClear?0xc202:0xc1ee;assert(run(ram,s,next,o)&&s.carry==carry_of(carry)&&quiet(o));}
}
// Nested stack limit: a71a -> a0a0 with -f2 near 107e0e.
void nest_limit(){
 // -f2=107e1e: A2=107e0e is accepted (a0c4); -f2 -> 107e0e.
 {Bytes ram;State s;generic(0xa71a,ram,s);put(ram,F2,4,0x107e1e);Out o;assert(run(ram,s,0xa0c4,o)&&s.a[2]==0x107e0e&&get(ram,SP-4,4)==0xa720&&get(ram,SP-8,4)==TOP);}
 // -f2=107e1c: A2=107e0c overflows; a0c2 RTS pops the pushed old -ee as the PC (here the RAM -ee=STOP).
 {Bytes ram;State s;generic(0xa71a,ram,s);put(ram,F2,4,0x107e1c);put(ram,EE,4,STOP);Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xa720&&get(ram,F2,4)==0x107e1c&&get(ram,EE,4)==0x107e1c);}
 // Same overflow with -ee = TOP: the popped PC 107efe is not routed and rolls back.
 {Bytes ram;State s;generic(0xa71a,ram,s);put(ram,F2,4,0x107e1c);reject(ram,s,STOP,"unsupported animation machine PC");}
}
void errors(){
 // Unknown carry at c1ea.
 {Bytes ram;State s;generic(0xc1ea,ram,s);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"card menu caller requires known carry");}
 // Natural chain entry at c1ea with Unknown carry (declared): the consumer rejects.
 {Bytes ram=status_ram;State s=status_state;put(ram,STATUS,1,0);s.pc=0xc1ea;s.a[7]+=8U;s.carry=ms5::AnimationCarryUnknown;
  reject(ram,s,RETURN,"card menu caller requires known carry");}
 // Non-BIOS stops roll back at each BIOS call (bd5a, bd8a, be16).
 {Bytes ram;State s;generic(0xbd3c,ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0xbd60,ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0xbe0c,ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(CARD,ram,s);reject(ram,s,0xbd60,"unsupported animation machine PC");}
 // Odd A2 at 9f36 (-ee odd): MOVEA.L (A2),A3. Odd descriptor: MOVE.W e(A3). Odd A2 at 9f50: MOVEA.L (A2).
 {Bytes ram;State s;generic(0x9f36,ram,s);put(ram,EE,4,TOP+1);reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0x9f36,ram,s);put(ram,TOP,4,DESC+1);reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0x9f50,ram,s);s.a[2]=TOP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A0 base at 9f50 (descriptor odd -> A0 odd): MOVEA.L (A0,D7.W).
 {Bytes ram;State s;generic(0x9f50,ram,s);put(ram,TOP,4,DESC+1);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A5 at bd3c (MOVE.W D0,-ce(A5)) and at 9f36 (-ee).
 {Bytes ram;State s;generic(0xbd3c,ram,s);s.a[5]=0x108001;reject(ram,s,BIOS,"alignment");}
 {Bytes ram;State s;generic(0x9f36,ram,s);s.a[5]=0x108001;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A7: bbb8 LONG push; bd3c A6 push after the -ce write; be1c pop.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xbd3c,ram,s);s.a[7]=SP+1;reject(ram,s,BIOS,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xbe1c,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Copy destination outside RAM: MOVE.B to the fixed ROM area.
 {Bytes ram;State s;generic(0xbbb8,ram,s);s.d[7]=3;s.a[0]=0x1000;reject(ram,s,STOP,"unsupported animation machine write device");}
 // Interior and bundled PCs inside the routed ranges.
 const std::uint32_t ranges[][2]={{0x9f36,0x9f76},{0xa71a,0xa72a},{0xbb74,0xbb8c},{0xbbb8,0xbbd2},{0xbd26,0xbd92},{0xbe0c,0xbe38}};
 unsigned int interior=0;
 for(unsigned int i=0;i<6;++i)for(std::uint32_t pc=ranges[i][0];pc<=ranges[i][1];pc+=2){
  if(listed(pc))continue;Bytes ram;State s;generic(pc,ram,s);reject(ram,s,STOP,"unsupported animation card menu save PC");++interior;}
 assert(interior==120); // 147 even PCs in the six ranges minus 27 save block starts
 // Bundled flag producers/consumers: BNE after ANDI.W, BCC after ADD.W, BNE after SUBQ.W, BCS after SUBQ.W,
 // BNE after MOVE.B, BNE after TST.B, RTS after ORI/ANDI CCR, JSR c00468/c0046e, BRA be0c, JSR 3af8.
 const std::uint32_t bundled[]={0x9f44,0x9f4a,0x9f72,0xbb7e,0xbb8a,0xbbbc,0xbbc6,0xbbc2,0xbbce,0xbe2a,0xbe32,0xbe38,0xbd5a,0xbd8a,0xbe16,0xbd92,0xa724,0xbd30,0xbd38};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){assert(!listed(bundled[i]));Bytes ram;State s;generic(bundled[i],ram,s);reject(ram,s,STOP,"unsupported animation card menu save PC");}
 // Neighbours outside the routed ranges (data at bb8e/be3a, BRA operand bd94) and the BIOS boundaries.
 const std::uint32_t outside[]={0x9f34,0x9f78,0xa72c,0xbb72,0xbb8e,0xbbb6,0x10fe20,0xbd24,0xbd94,0xbe0a,0xbe3a,BIOS,BIOS_STATUS};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram;State s;generic(outside[i],ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0xbd27,ram,s);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 const std::uint32_t extra[]={BIOS,BIOS_STATUS};
 for(unsigned int carry=0;carry<3;++carry)for(unsigned int i=0;i<ROWS+2;++i){
  const std::uint32_t pc=i<ROWS?TABLE[i][0]:extra[i-ROWS];Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,pc,o)&&same(s,old)&&ram==before&&quiet(o));}
}
void carry(){
 assert(ROWS==29);unsigned int keeps=0;
 for(unsigned int i=0;i<ROWS;++i){
  const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,sizeof(KEEP)/sizeof(KEEP[0]),pc);if(keep)++keeps;
  const bool consumer=TABLE[i][1]!=TABLE[i][2];assert(consumer==(pc==0xc1ea));
  for(unsigned int carry=0;carry<3;++carry){Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);
   if(consumer&&carry==0)continue; // errors()
   const std::uint32_t stop=carry==2?TABLE[i][2]:TABLE[i][1];Out o;
   if(!(run(ram,s,stop,o)&&s.pc==stop&&clean(o)))std::cerr<<std::hex<<"row "<<pc<<"\n";
   assert(s.pc==stop&&clean(o));
   ms5::AnimationCarryState expect=keep?carry_of(carry):ms5::AnimationCarryUnknown;
   if(pc==0xbe2e)expect=ms5::AnimationCarrySet;if(pc==0xbe34)expect=ms5::AnimationCarryClear;
   assert(s.carry==expect);}}
 assert(keeps==7);
}
}
int main(){natural();checksum_edges();fixtures();nest_limit();errors();zero_step();carry();
std::cout<<"animation_machine_card_menu_save_test PASS "<<calls<<" API invocations\n";}
