#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef std::vector<ms5::VideoPortWrite> Ports;
typedef ms5::AnimationMachineState State;
const std::uint32_t SP=0x1feffc,STOP=0xff000,CHILD=0x103000,TOP=0x107efe,FRAME=0xa370,RETURN=0x2ac2,CLOSE=0xa662,CARD=0xbd26;
const std::uint32_t DESC=0x104100,TEXT=0x104800,OLD_EE=0x10a0b0c0,E5=0x107f1b,E6=0x107f1a;
const std::uint32_t P1=0x104cba,P2=0x104cc0,CARD1=0x10fdb6,CARD2=0x10fdb7;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void text(Bytes&b,std::uint32_t a,const char*t,std::uint32_t mask){unsigned int i=0;for(;t[i];++i)b[(a+i)&mask]=static_cast<std::uint8_t>(t[i]);b[(a+i)&mask]=0;}
void hex(Bytes&b,std::uint32_t a,const char*h){for(unsigned int i=0;h[2*i];++i){unsigned int v=0;for(unsigned int k=0;k<2;++k){const char x=h[2*i+k];v=v*16U+static_cast<unsigned int>(x<='9'?x-'0':x-'a'+10);}b[a+i]=static_cast<std::uint8_t>(v);}}
State state(std::uint32_t pc){State s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=CHILD;s.a[7]=SP;return s;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o,const Physical*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;
 const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" stop "<<stop<<"\n";return ok;}
// Successful run: no external reads, returned status, PVC untouched (3c0000 events are ports only).
bool clean(const Out&o){return o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.error.empty()&&o.dev.pvc==Out().dev.pvc&&o.dev.bank_base==0x200000;}
bool quiet(const Out&o){return clean(o)&&o.ports.empty();}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message,const Physical*physical=NULL){
 const Bytes before=ram;const State old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;
 if(ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error)){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error.find(message)==std::string::npos)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
bool same_ports(const Ports&a,const Ports&b){if(a.size()!=b.size()){std::cerr<<std::dec<<"ports "<<a.size()<<" vs "<<b.size()<<"\n";return false;}
 for(unsigned int i=0;i<a.size();++i)if(a[i].address!=b[i].address||a[i].size!=b[i].size||a[i].value!=b[i].value){std::cerr<<std::hex<<"port "<<i<<" "<<a[i].value<<" vs "<<b[i].value<<"\n";return false;}return true;}
void append(Ports&all,const Ports&part){for(unsigned int i=0;i<part.size();++i)all.push_back(part[i]);}
// Expected video events (same equations as the open unit test).
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
// c188 menu rows: 0 "DATA SAVE ?  " (no callback), 1 separator, 2 " YES " (c1c4), 3 " NO " (bf94).
const char* const LABEL[4]={"DATA SAVE ?  ",""," YES "," NO "};
void row(Ports&e,unsigned int i,bool selected){cursor(e,item_row(4,4,i),selected);text_ports(e,(item_row(4,4,i)+0x40U)&65535U,3,LABEL[i]);}
// a216 cursor move: a262 redraws the old row unselected, then the new row selected.
Ports moved(unsigned int from,unsigned int to){Ports e;row(e,from,false);row(e,to,true);return e;}
// Synthetic typed physical bytes (not a native ROM oracle): the c188 descriptor and its strings.
Physical resources(){
 Physical p(1);p[0].source_rom_offset=0;p[0].data.assign(0x100000,0);Bytes&f=p[0].data;
 hex(f,0xc188,"0000000000000000bf2c0000000000000000be60000000000000fffffffe0000000000000000be9a0000c1c400000000bea00000bf940000ffffffff");
 text(f,0xbe60,"DATA SAVE ?  ",0xfffff);text(f,0xbe9a," YES ",0xfffff);text(f,0xbea0," NO ",0xfffff);return p;
}
// Declared host changes before a frame: card BYTEs 10fdb6/10fdb7 and input edge BYTEs 104cba/104cc0.
void inputs(Bytes&ram,std::uint32_t card1,std::uint32_t card2,std::uint32_t p1,std::uint32_t p2){
 put(ram,CARD1,1,card1);put(ram,CARD2,1,card2);put(ram,P1,1,p1);put(ram,P2,1,p2);}
// Natural chain from the card child c290 entry (clears 80(A6), loads c188/4/4) -> a29c push ->
// opening frames -> full frame (open unit C++ outputs), ending at 2ac2 with 7e=012c, cursor 3 (NO),
// e=0 and -e5=0. Residual 5(A2)=88, sound gates clear, empty 104d82 ring as in the open unit test.
void open_chain(Bytes&ram,State&s){
 ram.assign(65536,0x5a);put(ram,SP,4,RETURN);put(ram,0x107f12,4,OLD_EE);put(ram,TOP+5,1,0x88);
 put(ram,0x100012,1,0);put(ram,0x104d7e,1,0);put(ram,0x10f001,1,0);put(ram,0x104d8a,2,0);put(ram,0x104d8c,2,0);
 put(ram,CHILD+0x76,4,0xc188);put(ram,CHILD+0x7a,2,4);put(ram,CHILD+0x7c,2,4);s=state(0xc290);
 const Physical p=resources();Out o;assert(run(ram,s,FRAME,o,&p)&&s.pc==FRAME&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0&&get(ram,CHILD+0x80,1)==0);
 o=Out();assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&get(ram,TOP+4,2)==0x0208);
 for(unsigned int k=0;k<4;++k){assert(get(ram,CHILD,4)==0xc2ba);s.pc=0x2ab8;o=Out();assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&clean(o));}
 assert(get(ram,TOP+7,1)==3&&get(ram,TOP+8,1)==3&&get(ram,TOP+0xe,1)==0&&get(ram,CHILD+0x7e,2)==0x012c&&get(ram,E5,1)==0&&get(ram,TOP+4,2)==0x0600);
 assert(get(ram,0x104d82,2)==0x1a6c&&get(ram,0x104d8c,2)==2&&s.a[7]==SP+4&&s.a[6]==CHILD&&s.a[2]==TOP);
}
// Frame re-entry (declared PC=2ab8) after declaring the four host BYTEs.
bool frame(Bytes&ram,State&s,std::uint32_t c1,std::uint32_t c2,std::uint32_t p1,std::uint32_t p2,std::uint32_t stop,Out&o){
 const Physical p=resources();inputs(ram,c1,c2,p1,p2);s.pc=0x2ab8;return run(ram,s,stop,o,&p);}
// Chained stops through a subsequence of the actual trace equal the continuous run; so does a
// fresh split at each checkpoint followed by a continuation.
void splits(const Bytes&start,const State&old,const Bytes&ram,const State&s,const Ports&ports,const std::uint32_t*walk,unsigned int n,std::uint32_t last){
 const Physical p=resources();Bytes split=start;State t=old;Ports all;
 for(unsigned int i=0;i<n;++i){Out so;if(!(run(split,t,walk[i],so,&p)&&t.pc==walk[i]&&clean(so)))std::cerr<<std::hex<<"walk "<<walk[i]<<"\n";
  assert(t.pc==walk[i]&&clean(so));append(all,so.ports);}
 assert(walk[n-1]==last&&split==ram&&same(t,s)&&same_ports(all,ports));
 for(unsigned int i=0;i+1<n;++i){Bytes r2=start;State u=old;Out a,b;
  assert(run(r2,u,walk[i],a,&p)&&u.pc==walk[i]&&run(r2,u,last,b,&p)&&r2==ram&&same(u,s));append(a.ports,b.ports);assert(same_ports(a.ports,ports));}
}
// Snapshot after the first input frame (7e=012b, e=ff), used by the input fixtures.
Bytes first_ram;State first_state;
void natural(){
 const Physical p=resources();Bytes ram;State s;open_chain(ram,s);
 // First input frame: a3e2 -e5=0 -> a406 (4=c=6) -> a41a -> hook bf2c (7e 012c -> 012b) -> 9fc4 d=0;
 // a44e delivers the pending event 0 to the cursor item (NO, bf94) -> a73e 3af8 1a6c (already pending in
 // the 4-entry ring, so 3af8 does not add it again); no input bits.
 Bytes start=ram;State old=s;inputs(start,0,0,0,0);Out o;
 assert(frame(ram,s,0,0,0,0,RETURN,o)&&s.pc==RETURN&&quiet(o));
 assert(get(ram,CHILD+0x7e,2)==0x012b&&get(ram,TOP+0xe,1)==0xff&&get(ram,TOP+0xd,1)==0&&get(ram,TOP+7,1)==3&&get(ram,TOP+8,1)==3);
 assert(get(ram,E6,1)==0&&get(ram,E5,1)==0&&get(ram,CHILD+0x80,1)==0&&get(ram,0x107f12,4)==TOP&&get(ram,TOP+0xf,1)==0);
 assert(get(ram,0x104d82,2)==0x1a6c&&get(ram,0x104d84,2)==0x5a5a&&get(ram,0x104d8c,2)==2&&get(ram,0x104d8a,2)==0);
 assert(s.d[0]==0&&s.d[1]==0&&(s.d[6]&255U)==0&&(s.d[7]&255U)==0&&s.a[2]==TOP&&s.a[3]==0xc1b6&&s.a[5]==0x108000&&s.a[6]==CHILD&&s.a[7]==SP+4);
 assert(s.carry==ms5::AnimationCarryUnknown);
 s.pc=0x2ab8;old.pc=0x2ab8;
 {const std::uint32_t walk[]={0x2abe,0x2ac0,0xc2ba,FRAME,0xa380,0xa388,0xa3b8,0xa3c8,0xa3d0,0xa3e2,0xa3f2,0xa3fa,0xa406,0xa41a,0xa42c,0xa43e,
   0xbf2c,0xbf34,0xbf48,0xbf5c,0xbf6a,0xbf76,0xbf82,0xbf8e,0x9fc4,0xa442,0xa444,0xa44e,0xa458,0x9b3e,0x9b26,0x9b42,0x9b54,0xbf94,0xa73e,
   0xa74a,0x3af8,0xa754,0xbf9a,0xbfa8,0xbfbc,0xa46a,0xa44e,0xa472,0xa488,0xa496,0xa4b8,0xa4da,0xa4fc,0xa51e,0xa540,0xa562,0xa5ce,0xc2c0,
   0xc2c6,RETURN};
  State end=s;end.pc=RETURN;splits(start,old,ram,end,o.ports,walk,sizeof(walk)/sizeof(walk[0]),RETURN);}
 s.pc=RETURN;first_ram=ram;first_state=s;
 // No-input frames: the hook counts 7e down once per declared re-entry; nothing else changes.
 for(std::uint32_t k=2;k<0x12c;++k){o=Out();
  assert(frame(ram,s,0,0,0,0,RETURN,o)&&s.pc==RETURN&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x12cU-k&&s.a[7]==SP+4);
  assert(get(ram,E5,1)==0&&get(ram,TOP+0xe,1)==0xff&&get(ram,TOP+7,1)==3&&get(ram,0x104d8c,2)==2);}
 assert(get(ram,CHILD+0x7e,2)==1);
 // Frame 300: 7e 1 -> 0, bf3e e=3 via 9ff4; the same a44e loop sends event 3 to NO (bf94):
 // 80(A6)=ff, a70a sound 1a5b, a1ee -e5=2 and A2=-f2; a46a restores A2.
 start=ram;old=s;inputs(start,0,0,0,0);o=Out();
 assert(frame(ram,s,0,0,0,0,RETURN,o)&&s.pc==RETURN&&quiet(o));
 assert(get(ram,CHILD+0x7e,2)==0&&get(ram,CHILD+0x80,1)==0xff&&get(ram,E5,1)==2&&get(ram,TOP+0xe,1)==0xff&&get(ram,TOP+0xd,1)==0);
 assert(get(ram,0x104d84,2)==0x1a5b&&get(ram,0x104d8c,2)==4&&s.a[2]==TOP&&s.d[0]==0&&s.a[7]==SP+4);
 old.pc=0x2ab8;
 {const std::uint32_t walk[]={0xa3e2,0xa406,0xa41a,0xa42c,0xa43e,0xbf2c,0xbf34,0xbf3e,0x9ff4,0xbf48,0xbf5c,0xbf6a,0xbf76,0xbf82,0xbf8e,0x9fc4,
   0xa442,0xa444,0xa44e,0xa458,0x9b3e,0x9b26,0x9b42,0x9b54,0xbf94,0xa73e,0xa754,0xbf9a,0xbfa8,0xbfb0,0xa70a,0x3af8,0xa714,0xa1ee,0xa46a,
   0xa44e,0xa472,0xa488,0xa496,0xa4b8,0xa4da,0xa4fc,0xa51e,0xa540,0xa562,0xa5ce,0xc2c0,0xc2c6,RETURN};
  State end=s;splits(start,old,ram,end,o.ports,walk,sizeof(walk)/sizeof(walk[0]),RETURN);}
 // Next re-entry: a3e2 -e5=2 -> a662 (now the close unit, its own test); the stop at its entry succeeds.
 o=Out();assert(frame(ram,s,0,0,0,0,CLOSE,o)&&s.pc==CLOSE&&quiet(o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0&&s.a[2]==TOP&&get(ram,0x107f12,4)==TOP);
}
// Input frame from the first-frame snapshot; stop at the given PC.
bool from_first(std::uint32_t c1,std::uint32_t c2,std::uint32_t p1,std::uint32_t p2,std::uint32_t stop,Bytes&ram,State&s,Out&o){
 ram=first_ram;s=first_state;return frame(ram,s,c1,c2,p1,p2,stop,o);}
void card_bits(){
 // 10fdb6/10fdb7: only BYTE 1 or 3 enables a player; D0 (ORI.W) -> d(A2) via 9fc4.
 const std::uint32_t v[]={0,1,2,3,0x11,0x81,0xff,0x13};
 for(unsigned int i=0;i<8;++i)for(unsigned int j=0;j<8;++j){Bytes ram;State s;Out o;
  assert(from_first(v[i],v[j],0,0,0xa442,ram,s,o)&&quiet(o));
  const std::uint32_t d=((v[i]==1||v[i]==3)?1U:0U)|((v[j]==1||v[j]==3)?2U:0U);
  assert(get(ram,TOP+0xd,1)==d&&s.d[0]==d&&(s.d[1]&255U)==v[j]&&s.a[2]==TOP&&s.a[7]==SP-8&&get(ram,SP-8,4)==TOP&&get(ram,SP-12,4)==0xa442);}
}
// Each decision target of a472..a562 and the -e6 value written before it.
struct Pick {std::uint32_t c1,c2,p1,p2,target,e6;};
void priority(){
 const Pick picks[]={
  {1,0,0x3f,0xff,0xa566,1},{1,0,0x3e,0xff,0xa574,1},{1,0,0x3c,0xff,0xa596,1},{1,0,0x38,0xff,0xa5a0,1},{1,0,0x30,0xff,0xa58c,1},
  {1,0,0x10,0xff,0xa582,1},{1,0,0xff,0,0xa566,1},{1,0,0xc0,0xff,0xa562,0},{1,0,0x01,0,0xa566,1},{1,0,0x02,0,0xa574,1},
  {1,0,0x04,0,0xa596,1},{1,0,0x08,0,0xa5a0,1},{1,0,0x20,0,0xa58c,1},{1,0,0x10,0,0xa582,1},
  {2,3,0xff,0x04,0xa596,2},{0,1,0,0x30,0xa58c,2},{3,1,0x04,0x04,0xa596,3},{1,1,0x04,0x01,0xa566,2},{1,3,0x20,0x10,0xa58c,1},
  {3,3,0x10,0x30,0xa58c,2},{1,1,0x13,0x13,0xa566,3},{0,0,0xff,0xff,0xa562,0},{2,2,0xff,0xff,0xa562,0},{1,1,0xc0,0xc0,0xa562,0}};
 for(unsigned int i=0;i<sizeof(picks)/sizeof(picks[0]);++i){const Pick&k=picks[i];Bytes ram;State s;Out o;
  if(!from_first(k.c1,k.c2,k.p1,k.p2,k.target,ram,s,o))std::cerr<<std::dec<<"pick "<<i<<"\n";
  assert(s.pc==k.target&&quiet(o)&&get(ram,E6,1)==k.e6&&get(ram,TOP+0xe,1)==0xff);
  const std::uint32_t d0=(k.c1==1||k.c1==3)?k.p1:0,d1=(k.c2==1||k.c2==3)?k.p2:0;assert(s.d[0]==d0&&s.d[1]==d1);
  if(k.target!=0xa562)assert((s.d[7]&255U)==k.e6&&(s.d[6]&255U)==(k.e6&1U));}
}
// Full input frames to 2ac2: cursor moves (a216), events 1/2/4 (no effect on NO), select.
void moves(){
 const Physical p=resources();
 // Up (bit0, BSET #1,f): 3 -> 2 (YES); event 0 to YES -> a73e (1a6c still pending: ring unchanged).
 Bytes ram;State s;Out o;assert(from_first(1,0,0x01,0,RETURN,ram,s,o)&&clean(o)&&same_ports(o.ports,moved(3,2)));
 assert(get(ram,TOP+7,1)==2&&get(ram,TOP+8,1)==2&&get(ram,TOP+0xf,1)==2&&get(ram,TOP+0xe,1)==0xff&&get(ram,E6,1)==1);
 assert(get(ram,0x104d8c,2)==2&&get(ram,CHILD+0x7e,2)==0x012a&&s.a[7]==SP+4&&s.d[0]==0);
 const Bytes up=ram;const State up_state=s;
 // Up again from 2: 1 (separator) and 0 (no callback) are skipped, wrap -1 -> +4 -> 3 (NO).
 o=Out();assert(frame(ram,s,1,0,0x01,0,RETURN,o)&&clean(o)&&same_ports(o.ports,moved(2,3)));
 assert(get(ram,TOP+7,1)==3&&get(ram,TOP+8,1)==3&&get(ram,TOP+0xf,1)==2);
 // Down (bit1 via P2 only, BCLR #1,f): 3 -> wrap 0 -> 1 -> 2 (YES); then 2 -> 3.
 o=Out();assert(frame(ram,s,0,1,0,0x02,RETURN,o)&&clean(o)&&same_ports(o.ports,moved(3,2)));
 assert(get(ram,TOP+7,1)==2&&get(ram,TOP+0xf,1)==0&&get(ram,E6,1)==2);
 o=Out();assert(frame(ram,s,3,3,0x02,0x02,RETURN,o)&&clean(o)&&same_ports(o.ports,moved(2,3)));
 assert(get(ram,TOP+7,1)==3&&get(ram,TOP+8,1)==3&&get(ram,TOP+0xf,1)==0&&get(ram,E6,1)==3);
 // Events 1/2/4 (bits 2/3/5) reach bf94 with D0.W=event: no sound, no 7e/80 change.
 const std::uint32_t bits[]={0x04,0x08,0x20},events[]={1,2,4};
 for(unsigned int i=0;i<3;++i){Bytes r;State t;Out a;assert(from_first(1,0,bits[i],0,0xbf94,r,t,a)&&quiet(a)&&(t.d[0]&65535U)==events[i]&&get(r,TOP+0xe,1)==0xff);
  a=Out();assert(run(r,t,RETURN,a,&p)&&quiet(a)&&get(r,0x104d8c,2)==2&&get(r,CHILD+0x7e,2)==0x012a&&get(r,CHILD+0x80,1)==0&&get(r,E5,1)==0&&get(r,E6,1)==1);}
 // Select (bit4, event 3) on NO: 80=ff, sound 1a5b, -e5=2; the next re-entry reaches a662 (close unit).
 {Bytes r;State t;Out a;assert(from_first(1,0,0x10,0,RETURN,r,t,a)&&quiet(a)&&get(r,CHILD+0x80,1)==0xff&&get(r,E5,1)==2&&get(r,0x104d84,2)==0x1a5b&&get(r,E6,1)==1);
  a=Out();assert(frame(r,t,0,0,0,0,CLOSE,a)&&t.pc==CLOSE&&quiet(a));}
 // Select on YES (after the up frame): c1c4 event 3 -> JSR bd26 (card save unit, its own test; its first
 // BIOS call c00468 has no executor, so a RETURN stop still rolls back).
 {Bytes r=up;State t=up_state;Out a;inputs(r,0,1,0,0x10);t.pc=0x2ab8;
  {const Bytes r2=r;const State t2=t;reject(r2,t2,RETURN,"unsupported animation machine PC",&p);}
  assert(run(r,t,CARD,a,&p)&&t.pc==CARD&&quiet(a)&&get(r,E6,1)==2&&get(r,TOP+0xe,1)==0xff&&get(r,CHILD+0x80,1)==0);
  // Stack: c1ea (JSR bd26) above a5c6 (BSR 9b3e) above the pushed A2.
  assert(t.a[7]==SP-16&&get(r,SP-16,4)==0xc1ea&&get(r,SP-12,4)==0xa5c6&&get(r,SP-8,4)==TOP&&get(r,SP-4,4)==0xc2c0&&(t.d[0]&65535U)==3);}
}
void hook_edges(){
 const Physical p=resources();
 // 7e=0 at entry: no decrement, no event; 7e=8000 -> 7fff.
 {Bytes ram=first_ram;State s=first_state;put(ram,CHILD+0x7e,2,0);Out o;assert(frame(ram,s,0,0,0,0,RETURN,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0&&get(ram,E5,1)==0&&get(ram,TOP+0xe,1)==0xff);}
 {Bytes ram=first_ram;State s=first_state;put(ram,CHILD+0x7e,2,0x8000);Out o;assert(frame(ram,s,0,0,0,0,RETURN,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x7fff);}
 // 80(A6)!=0: bf50 JSR a70a (sound 1a5b, -e5=2), D0=0 -> d=0 even with an enabled P1 bit.
 {Bytes ram=first_ram;State s=first_state;put(ram,CHILD+0x80,1,1);Out o;
  assert(frame(ram,s,1,0,0x04,0,0xa442,o)&&quiet(o)&&get(ram,TOP+0xd,1)==0&&s.d[0]==0&&s.a[2]==TOP&&get(ram,E5,1)==2&&get(ram,0x104d84,2)==0x1a5b);
  o=Out();assert(run(ram,s,RETURN,o,&p)&&quiet(o)&&get(ram,E6,1)==0&&get(ram,TOP+0xe,1)==0xff&&get(ram,CHILD+0x7e,2)==0x012a);
  o=Out();assert(frame(ram,s,0,0,0,0,CLOSE,o)&&s.pc==CLOSE);}
 // f bit0: a41a BCLR (BYTE RMW keeps bit1) -> a424 JSR 9e1a redraw (title LONG 0: rows only).
 // 9e1a renders through JSR (A1) (3928). The natural A1 here is the 3af8 ring-scan pointer left by
 // the previous frame's sound call (104d8x), an unrouted RAM target: a stop there succeeds after the
 // first row cursor, any other stop rolls back. Whether the game reaches a406 with f bit0 and such an
 // A1 is unconfirmed.
 {Bytes ram=first_ram;State s=first_state;put(ram,TOP+0xf,1,0x83);inputs(ram,0,0,0,0);s.pc=0x2ab8;
  assert(s.a[1]>=0x104d82&&s.a[1]<0x104d8a);reject(ram,s,RETURN,"unsupported animation machine PC",&p);
  Out o;assert(run(ram,s,first_state.a[1],o,&p)&&s.pc==first_state.a[1]&&get(ram,TOP+0xf,1)==0x82);
  Ports e;cursor(e,item_row(4,4,0),false);assert(same_ports(o.ports,e));}
 // With a declared A1=a008 (the renderer a348/a5ea install) the full row redraw completes.
 {Bytes ram=first_ram;State s=first_state;s.a[1]=0xa008;put(ram,TOP+0xf,1,0x83);Out o;assert(frame(ram,s,0,0,0,0,RETURN,o)&&clean(o));
  Ports e;row(e,0,false);separator(e,item_row(4,4,1),0x11);row(e,2,false);row(e,3,true);
  assert(same_ports(o.ports,e)&&get(ram,TOP+0xf,1)==0x82&&get(ram,TOP+8,1)==3&&get(ram,CHILD+0x7e,2)==0x012a&&s.a[1]==0xa008);}
}
// RAM fixture: -f2=-ee=107efe, -ea=e84c8, -e5=0; frame h=4=c, 4 items, cursor 3, d=3, e=ff, f=0;
// RAM descriptor with hook 6(desc)=bf2c and rows {TEXT, separator, TEXT/c1c4, TEXT/bf94}.
void generic(std::uint32_t pc,Bytes&ram,State&s){
 ram.assign(65536,0);for(unsigned int i=0;i<8;++i)put(ram,SP+4*i,4,STOP);
 put(ram,0x107f0e,4,TOP);put(ram,0x107f12,4,TOP);put(ram,0x107f16,4,0xe84c8);put(ram,E5,1,0);
 put(ram,TOP,4,DESC);put(ram,TOP+4,1,4);put(ram,TOP+6,1,4);put(ram,TOP+7,1,3);put(ram,TOP+8,1,3);put(ram,TOP+9,1,4);put(ram,TOP+0xa,1,4);
 put(ram,TOP+0xb,1,0x11);put(ram,TOP+0xc,1,4);put(ram,TOP+0xd,1,3);put(ram,TOP+0xe,1,0xff);put(ram,TOP+0xf,1,0);
 put(ram,DESC+6,4,0xbf2c);const std::uint32_t items[]={TEXT,0xfffffffeU,TEXT,TEXT},cb[]={0,0,0xc1c4,0xbf94};
 for(unsigned int i=0;i<4;++i){put(ram,DESC+0x10+10*i,4,items[i]);put(ram,DESC+0x14+10*i,4,cb[i]);}
 put(ram,DESC+0x38,4,0xffffffffU);text(ram,TEXT,"AB",65535);put(ram,CHILD+0x7e,2,0x012c);
 s=state(pc);s.a[2]=TOP;s.a[3]=0xbf2c;s.d[0]=0x12345600;s.d[1]=0x9abcde00;}
// Every block start {pc, next} from the generic fixture.
const std::uint32_t TABLE[][2]={
 {0x9fc4,STOP},{0x9ff4,STOP},{0xa1ee,STOP},{0xa406,0xa41a},{0xa412,0xa348},{0xa416,STOP},{0xa41a,0xa42c},{0xa424,0x9e1a},
 {0xa42a,0xa42c},{0xa42c,0xa43e},{0xa43e,0xbf2c},{0xa442,0xa444},{0xa444,0xa44e},{0xa44e,0xa472},{0xa458,0x9b3e},{0xa46a,0xa44e},
 {0xa472,0xa484},{0xa484,0xa488},{0xa488,0xa492},{0xa492,0xa496},{0xa496,0xa4b8},{0xa4b0,0xa566},{0xa4b8,0xa4da},{0xa4d2,0xa574},
 {0xa4da,0xa4fc},{0xa4f4,0xa596},{0xa4fc,0xa51e},{0xa516,0xa5a0},{0xa51e,0xa540},{0xa538,0xa58c},{0xa540,0xa562},{0xa55a,0xa582},
 {0xa562,0xa5ce},{0xa566,0xa216},{0xa570,0xa5aa},{0xa574,0xa216},{0xa57e,0xa5aa},{0xa582,0xa5aa},{0xa58c,0xa5aa},{0xa596,0xa5aa},
 {0xa5a0,0xa5aa},{0xa5aa,0xa5ce},{0xa5b4,0x9b3e},{0xa5c6,0xa5aa},{0xa5ce,STOP},{0xa70a,0x3af8},{0xa714,0xa1ee},{0xbf2c,0xbf34},
 {0xbf34,0xbf48},{0xbf3e,0x9ff4},{0xbf48,0xbf5c},{0xbf50,0xa70a},{0xbf56,0xbf8e},{0xbf5c,0xbf6a},{0xbf6a,0xbf76},{0xbf72,0xbf76},
 {0xbf76,0xbf82},{0xbf82,0xbf8e},{0xbf8a,0xbf8e},{0xbf8e,0x9fc4}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
const std::uint32_t BOUNDARY[]={CLOSE,CARD}; // a662/bd26 run in the close/save units; zero-step still holds.
// Blocks made only of BSR/JSR/JMP/BRA/MOVEA/BTST/BSET/BCLR and conditional branches (capstone classification).
const std::uint32_t KEEP[]={0xa412,0xa41a,0xa42a,0xa442,0xa488,0xa562,0xa566,0xa570,0xa574,0xa57e,0xa714,0xbf50,0xbf8e};
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
void fixtures(){
 // Hook 0 in the descriptor: a42c -> a444 directly; stale d=3 still gates P1/P2 reads (event 1 to NO).
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,DESC+6,4,0);put(ram,P1,1,0x04);put(ram,P2,1,0);Out o;
  assert(run(ram,s,0xa444,o)&&quiet(o)&&s.a[7]==SP&&s.a[3]==0&&get(ram,CHILD+0x7e,2)==0x012c);
  o=Out();assert(run(ram,s,0xbf94,o)&&(s.d[0]&65535U)==1);o=Out();assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,E6,1)==1&&s.d[0]==0&&s.a[7]==SP+4&&get(ram,TOP+0xe,1)==0xff);}
 // Other hook targets are boundaries (a6da has no executor; 9f36 now runs in the save unit): stop there
 // succeeds with A2 and a442 pushed; other stops roll back.
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,DESC+6,4,0xa6da);reject(ram,s,STOP,"unsupported animation machine PC");
  Out o;assert(run(ram,s,0xa6da,o)&&quiet(o)&&s.a[7]==SP-8&&get(ram,SP-8,4)==0xa442&&get(ram,SP-4,4)==TOP&&s.a[3]==0xa6da&&get(ram,0x107f12,4)==TOP);}
 // 4 < c: a412 BSR a348 (box h=2, WORD 4(A2) += c<<6), a416 MOVEQ #0 RTS; the hook does not run.
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,TOP+4,2,0x0200);Out o;assert(run(ram,s,STOP,o)&&clean(o)&&s.d[0]==0&&s.a[7]==SP+4);
  Ports e;box(e,4,4,0x11,2,0x0b);assert(same_ports(o.ports,e)&&get(ram,TOP+4,2)==0x0300&&get(ram,CHILD+0x7e,2)==0x012c&&get(ram,TOP+0xe,1)==0xff);}
 // 4 = ff >= c (unsigned): the input path.
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,TOP+4,1,0xff);Out o;assert(run(ram,s,0xa41a,o)&&quiet(o)&&(s.d[0]&255U)==0xff&&(s.d[0]>>8)==0x123456U);}
 // 7e=1 at bf2c: 9ff4 writes e(-ee)=3; the hook ends through 9fc4.
 {Bytes ram;State s;generic(0xbf2c,ram,s);put(ram,CHILD+0x7e,2,1);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0&&get(ram,TOP+0xe,1)==3&&get(ram,TOP+0xd,1)==0&&s.d[0]==0);}
 // SNE/ANDI.B/OR.B change only low BYTEs; BTST on Dn tests the LONG register bit.
 {Bytes ram;State s;generic(0xa496,ram,s);s.d[0]=0xffffff01U;s.d[1]=0x00000101U;s.d[6]=0x11223344;s.d[7]=0x55667788;Out o;
  assert(run(ram,s,0xa4b0,o)&&s.d[6]==0x11223301U&&s.d[7]==0x55667703U&&s.d[0]==0xffffff01U);
  o=Out();assert(run(ram,s,0xa566,o)&&get(ram,E6,1)==3);}
 {Bytes ram;State s;generic(0xa4b8,ram,s);s.d[0]=0xfffffffdU;s.d[1]=0x00000200;s.d[6]=0;s.d[7]=0xffffffffU;Out o;
  assert(run(ram,s,0xa4da,o)&&s.d[6]==0&&s.d[7]==0xffffff00U);}
 // BSET/BCLR #1,f are BYTE read-modify-writes that keep other bits.
 {Bytes ram;State s;generic(0xa566,ram,s);put(ram,TOP+0xf,1,0xa5);Out o;assert(run(ram,s,0xa216,o)&&get(ram,TOP+0xf,1)==0xa7&&get(ram,SP-4,4)==0xa570);}
 {Bytes ram;State s;generic(0xa574,ram,s);put(ram,TOP+0xf,1,0xa7);Out o;assert(run(ram,s,0xa216,o)&&get(ram,TOP+0xf,1)==0xa5&&get(ram,SP-4,4)==0xa57e);}
 {Bytes ram;State s;generic(0xa41a,ram,s);put(ram,TOP+0xf,1,0xfe);Out o;assert(run(ram,s,0xa42c,o)&&get(ram,TOP+0xf,1)==0xfe);}
 {Bytes ram;State s;generic(0xa41a,ram,s);put(ram,TOP+0xf,1,0xff);Out o;assert(run(ram,s,0xa424,o)&&get(ram,TOP+0xf,1)==0xfe);}
 // a1ee: BYTE 2 -> -e5, A2=-f2, RTS.
 {Bytes ram;State s;generic(0xa1ee,ram,s);put(ram,0x107f0e,4,0x12345678);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&s.a[2]==0x12345678&&get(ram,E5,1)==2&&get(ram,0x107f1a,1)==0&&s.a[7]==SP+4);}
 // a70a: D0.W=1a5b (high WORD kept) through 3af8, then a1ee.
 {Bytes ram;State s;generic(0xa70a,ram,s);Out o;assert(run(ram,s,0xa714,o)&&(s.d[0]>>16)==0x1234U&&get(ram,0x104d82,2)==0x1a5b);}
}
void errors(){
 // Odd A2: MOVEA.L (A2),A3 at a42c (after the -ee LONG write, rolled back).
 {Bytes ram;State s;generic(0xa42c,ram,s);s.a[2]=TOP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A2 from -f2 (107eff) through a370/a3e2: 4(A2)=ff >= c, BCLR f(A2) BYTE, then the LONG read fails.
 {Bytes ram;State s;generic(FRAME,ram,s);put(ram,0x107f0e,4,0x107eff);put(ram,TOP+5,1,0xff);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A3 (descriptor DESC+1): MOVEA.L 6(A3).
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,TOP,4,DESC+1);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd hook target: JSR (A3).
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,DESC+6,4,0xbf2d);reject(ram,s,STOP,"odd jump target");}
 // Odd A7: a43e LONG push, a424 push, a458 push, bf3e JSR, a566 BSR.
 {Bytes ram;State s;generic(0xa406,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xa406,ram,s);put(ram,TOP+0xf,1,1);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xa44e,ram,s);put(ram,TOP+0xe,1,0);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xbf3e,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xa566,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A6: WORD 7e(A6) read at bf2c; WORD write at bf34.
 {Bytes ram;State s;generic(0xbf2c,ram,s);s.a[6]=CHILD+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xbf34,ram,s);s.a[6]=CHILD+1;reject(ram,s,STOP,"alignment");}
 // Interior and bundled PCs inside the routed ranges.
 const std::uint32_t ranges[][2]={{0x9fc4,0x9fcc},{0x9ff4,0x9ffc},{0xa1ee,0xa1f8},{0xa406,0xa5d0},{0xa70a,0xa718},{0xbf2c,0xbf92}};
 unsigned int interior=0;
 for(unsigned int i=0;i<6;++i)for(std::uint32_t pc=ranges[i][0];pc<=ranges[i][1];pc+=2){
  if(listed(pc))continue;Bytes ram;State s;generic(pc,ram,s);reject(ram,s,STOP,"unsupported animation card menu input PC");++interior;}
 assert(interior==246);
 // Bundled flag producers/consumers: BEQ after BCLR, SNE after BTST, BEQ after OR.B, BNE after MOVE.W.
 const std::uint32_t bundled[]={0xa420,0xa40a,0xa40e,0xa49a,0xa4a2,0xa4aa,0xa4ac,0xa4ce,0xa556,0xbf30,0xbf36,0xbf3a,0xbf64,0xbf68,0xbf6e,0xa5b0,0xa454};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){Bytes ram;State s;generic(bundled[i],ram,s);reject(ram,s,STOP,"unsupported animation card menu input PC");}
 // Neighbours outside the routed ranges and the boundaries (a71a/bd26 now run in the save unit;
 // its BIOS calls c00468/c0046e have no executor).
 const std::uint32_t outside[]={0x9fce,0x9ff2,0x9ffe,0xa1e2,0xa1ec,0xa1fa,0xa708,0xa72c,0xbf2a,0xa698,0xc00468,0xc0046e};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram;State s;generic(outside[i],ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0xa407,ram,s);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int carry=0;carry<3;++carry)for(unsigned int i=0;i<ROWS+2;++i){
  const std::uint32_t pc=i<ROWS?TABLE[i][0]:BOUNDARY[i-ROWS];Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,pc,o)&&same(s,old)&&ram==before&&quiet(o));}
}
void carry(){
 assert(ROWS==60);unsigned int keeps=0;
 for(unsigned int i=0;i<ROWS;++i){
  const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,sizeof(KEEP)/sizeof(KEEP[0]),pc);if(keep)++keeps;
  for(unsigned int carry=0;carry<3;++carry){Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);Out o;
   if(!(run(ram,s,TABLE[i][1],o)&&s.pc==TABLE[i][1]&&clean(o)))std::cerr<<std::hex<<"row "<<pc<<"\n";
   assert(s.pc==TABLE[i][1]&&clean(o)&&s.carry==(keep?carry_of(carry):ms5::AnimationCarryUnknown));}}
 assert(keeps==13);
}
}
int main(){natural();card_bits();priority();moves();hook_edges();fixtures();errors();zero_step();carry();
std::cout<<"animation_machine_card_menu_input_test PASS "<<calls<<" API invocations\n";}
