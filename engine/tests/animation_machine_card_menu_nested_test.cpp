#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef std::vector<ms5::VideoPortWrite> Ports;
typedef ms5::AnimationMachineState State;
const std::uint32_t SP=0x1feffc,STOP=0xff000,OBJ=0x102000,NEXT=0x102200,FREE=0x103400,CHILD=0x103000,TOP=0x107efe,UP=0x107eee,LOW=0x107ede;
const std::uint32_t FRAME=0xa370,RETURN=0x2ac2,CLOSE=0xa662,NESTED=0xa698,REDRAW=0xa6da,BIOS=0xc00468,BIOS_STATUS=0xc0046e;
const std::uint32_t DESC=0x104100,DESC2=0x104200,DESC3=0x104300,TEXT=0x104800,OLD_EE=0x10a0b0c0,F2=0x107f0e,EE=0x107f12,E5=0x107f1b;
const std::uint32_t P1=0x104cba,P2=0x104cc0,CARD1=0x10fdb6,CARD2=0x10fdb7,STATUS=0x10fdc6,RING=0x104d82,RING_W=0x104d8c,RING_R=0x104d8a;
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
// Successful run: no external reads, returned status, PVC untouched (3c0000/300001 events are ports only).
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
// Expected video events (same equations as the open/input/close unit tests).
// cell: LSL.W #5 of x, ADD.B y (BYTE only), ADDI.W #7000.
std::uint32_t cell(std::uint32_t x,std::uint32_t y){return ((((x<<5)&0xff00U)|(((x<<5)+y)&0xffU))+0x7000U)&65535U;}
void port(Ports&v,unsigned int size,std::uint32_t value){ms5::VideoPortWrite p;p.address=0x3c0000;p.size=static_cast<std::uint8_t>(size);p.value=value;v.push_back(p);}
void tile_row(Ports&v,std::uint32_t a,std::uint32_t pal,std::uint32_t first,std::uint32_t mid,std::uint32_t last,unsigned int n){
 port(v,4,(a<<16)|(pal<<8)|first);for(unsigned int i=1;i<=n;++i)port(v,4,(((a+0x20U*i)&65535U)<<16)|(pal<<8)|mid);
 port(v,4,(((a+0x20U*(n+1))&65535U)<<16)|(pal<<8)|last);}
// Uncovered 9b58 box: nothing at h=0; top f4 f0.. f5, (h-2) rows f2 60.. f3, bottom f6 f1.. f7 (h=1 draws top and bottom).
void box(Ports&v,std::uint32_t x,std::uint32_t y,unsigned int w,unsigned int h,std::uint32_t pal){
 if(!h)return;const unsigned int n=w>2?w-2:0;std::uint32_t a=cell(x,y);tile_row(v,a,pal,0xf4,0xf0,0xf5,n);
 for(unsigned int r=h;r>2;--r){a=(a+1U)&65535U;tile_row(v,a,pal,0xf2,0x60,0xf3,n);}
 a=(a+1U)&65535U;tile_row(v,a,pal,0xf6,0xf1,0xf7,n);}
// Uncovered a2ec..a33c erase: rows from cell(x,y) ADD.B h, ADDQ.W per row, ff per cell.
void erase(Ports&v,std::uint32_t x,std::uint32_t y,std::uint32_t h,unsigned int w,unsigned int rows){
 const std::uint32_t base=(cell(x,y)&0xff00U)|((cell(x,y)+h)&0xffU);
 for(unsigned int r=0;r<rows;++r){const std::uint32_t row=(base+r)&65535U;for(unsigned int i=0;i<w;++i)port(v,4,((((row+0x20U*i)&65535U))<<16)|0x00ffU);}}
// 3650 per character: LONG addr|(D1 nibble-shifted)|char, then WORD 8200.
std::uint32_t text_ports(Ports&v,std::uint32_t a,std::uint32_t d1,const char*t){
 std::uint32_t w=d1&65535U;w=(w&0xff00U)|((w<<4)&0xffU);w=(w<<4)&65535U;
 for(unsigned int i=0;t[i];++i){port(v,4,(a<<16)|(w&0xff00U)|static_cast<unsigned char>(t[i]));port(v,2,0x8200);a=(a+0x20U)&65535U;}return a;}
void cursor(Ports&v,std::uint32_t a,bool selected){port(v,4,(a<<16)|(selected?0x313U:0xffU));port(v,4,(((a+0x20U)&65535U)<<16)|(selected?0x314U:0xffU));}
void separator(Ports&v,std::uint32_t a,std::uint32_t b){
 if(b<2)return;port(v,4,(a<<16)|0xbf8U);std::uint32_t d7=(b-3U)&255U;a=(a+0x20U)&65535U;
 while(d7>=2){port(v,4,(a<<16)|0xbf9U);a=(a+0x20U)&65535U;d7=(d7-1U)&65535U;}
 if(d7==1)port(v,4,(a<<16)|0xbfaU);}
// 9d4c row address: cell(x,y)+20 then ADD.B row (1+index).
std::uint32_t item_row(std::uint32_t x,std::uint32_t y,std::uint32_t index){const std::uint32_t a=(cell(x,y)+0x20U)&65535U;return (a&0xff00U)|((a+1U+index)&0xffU);}
void row(Ports&e,std::uint32_t x,std::uint32_t y,unsigned int i,bool selected,std::uint32_t pal,const char*label){
 cursor(e,item_row(x,y,i),selected);text_ports(e,(item_row(x,y,i)+0x40U)&65535U,pal,label);}
// c188 parent at -f2 (a6da redraw after the nested return): palette 0b box, all rows 0003, cursor 7=2 (YES).
Ports parent_redraw(){Ports e;box(e,4,4,0x11,6,0x0b);row(e,4,4,0,false,3,"DATA SAVE ?  ");separator(e,item_row(4,4,1),0x11);
 row(e,4,4,2,true,3," YES ");row(e,4,4,3,false,3," NO ");return e;}
// Result menu (c214 SAVE OK / c232 NO SAVE) at -f2: x=y=7, b=e, one row with the cursor.
const char* result_label(bool ok){return ok?"SAVE OK.  ":"NO SAVE.  ";}
Ports result_full(bool ok){Ports e;box(e,7,7,0x0e,3,0x0b);row(e,7,7,0,true,3,result_label(ok));return e;}
// Close frame: box at the new height then the erased rows (palette 0b: A2 = -f2).
Ports closing(std::uint32_t x,std::uint32_t y,unsigned int w,unsigned int h,unsigned int rows){Ports e;box(e,x,y,w,h,0x0b);erase(e,x,y,h,w,rows);return e;}
// Declared object-list fixture (close unit): parent OBJ (480ac, type 0, 8=CHILD) -> CHILD (4=OBJ, 8=NEXT,
// c=OBJ, type 1) -> NEXT (type 0); free list 104c9c=103400 count 1; dispatcher SP at 104ca4.
void objects(Bytes&ram){
 put(ram,OBJ,4,0x480ac);put(ram,OBJ+8,4,CHILD);put(ram,OBJ+0x10,2,0);put(ram,OBJ+0x1d,1,0);put(ram,OBJ+0x62,1,0);put(ram,OBJ+0x6c,1,0xff);
 put(ram,CHILD+4,4,OBJ);put(ram,CHILD+8,4,NEXT);put(ram,CHILD+0xc,4,OBJ);put(ram,CHILD+0x10,2,1);put(ram,CHILD+0x1d,1,0);put(ram,CHILD+0x6c,1,0xff);
 put(ram,NEXT+4,4,CHILD);put(ram,NEXT+0x10,2,0);put(ram,0x104c9c,4,FREE);put(ram,0x104ca0,2,1);put(ram,0x104ca4,4,SP+4);}
// Declared host changes before a frame: card BYTEs 10fdb6/10fdb7 and input edge BYTEs 104cba/104cc0.
void inputs(Bytes&ram,std::uint32_t card1,std::uint32_t card2,std::uint32_t p1,std::uint32_t p2){
 put(ram,CARD1,1,card1);put(ram,CARD2,1,card2);put(ram,P1,1,p1);put(ram,P2,1,p2);}
bool frame(Bytes&ram,State&s,std::uint32_t c1,std::uint32_t c2,std::uint32_t p1,std::uint32_t p2,std::uint32_t stop,Out&o){
 inputs(ram,c1,c2,p1,p2);s.pc=0x2ab8;return run(ram,s,stop,o);}
// Idle frame (no card or input change).
bool idle(Bytes&ram,State&s,Out&o){return frame(ram,s,0,0,0,0,RETURN,o);}
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
unsigned int frames=0; // natural re-entries counted from the save unit's chain end (SAVE OK branch)
// Save unit chain (same declared inputs as the save unit test): c290 entry -> opening/full frames ->
// cursor up to YES -> select (event 3) -> three BIOS stops -> 10fdc6 result -> c214/c232 push -> 2ac2.
void to_result(bool ok,Bytes&out_ram,State&out){
 Bytes ram(65536,0x5a);put(ram,SP,4,RETURN);put(ram,EE,4,OLD_EE);put(ram,TOP+5,1,0x88);
 put(ram,0x100012,1,0);put(ram,0x104d7e,1,0);put(ram,0x10f001,1,0);put(ram,RING_R,2,0);put(ram,RING_W,2,0);
 put(ram,CHILD+0x76,4,0xc188);put(ram,CHILD+0x7a,2,4);put(ram,CHILD+0x7c,2,4);objects(ram);State s=state(0xc290);
 Out o;assert(run(ram,s,RETURN,o)&&s.pc==RETURN&&get(ram,TOP+4,2)==0x0208);
 for(unsigned int k=0;k<4;++k){assert(get(ram,CHILD,4)==0xc2ba);s.pc=0x2ab8;o=Out();assert(run(ram,s,RETURN,o)&&s.pc==RETURN&&clean(o));}
 o=Out();assert(frame(ram,s,0,0,0,0,RETURN,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x012b);
 o=Out();assert(frame(ram,s,1,0,0x01,0,RETURN,o)&&clean(o)&&get(ram,TOP+7,1)==2&&get(ram,CHILD+0x7e,2)==0x012a);
 o=Out();assert(frame(ram,s,0,1,0,0x10,BIOS,o)&&quiet(o));
 resume(ram,s,0xbd60);o=Out();assert(run(ram,s,BIOS,o)&&quiet(o));
 resume(ram,s,0xbd90);o=Out();assert(run(ram,s,BIOS_STATUS,o)&&quiet(o));
 resume(ram,s,0xbe1c);put(ram,STATUS,1,ok?0:1);o=Out();assert(run(ram,s,RETURN,o)&&s.pc==RETURN&&clean(o));
 // Save unit chain end: result frame UP pushed above the c188 frame, -e5=1, sounds 1a6c and 1adb queued.
 assert(get(ram,UP,4)==(ok?0xc214U:0xc232U)&&get(ram,UP+4,2)==0x005a&&get(ram,UP+6,1)==1&&get(ram,UP+9,1)==7&&get(ram,UP+0xa,1)==7);
 assert(get(ram,UP+0xb,1)==0x0e&&get(ram,UP+0xc,1)==3&&get(ram,UP+0xd,1)==3&&get(ram,UP+0xe,1)==0xff&&get(ram,UP+0xf,1)==0);
 assert(get(ram,F2,4)==UP&&get(ram,EE,4)==TOP&&get(ram,E5,1)==1&&get(ram,TOP+4,2)==0x0600&&get(ram,TOP+7,1)==2);
 assert(get(ram,RING,2)==0x1a6c&&get(ram,RING+2,2)==0x1adb&&get(ram,RING_W,2)==4&&get(ram,CHILD+0x7e,2)==0x0129&&get(ram,CHILD+0x80,1)==0);
 assert(s.a[7]==SP+4&&s.a[6]==CHILD&&get(ram,CHILD,4)==0xc2ba&&get(ram,STATUS,1)==(ok?0U:1U));
 out_ram=ram;out=s;
}
// Natural chain from the save unit's chain end: result menu opening frames, its a5ea frame, 30 input
// frames, close frames, the a698 nested return, then the parent: bf2c 80!=0 -> a70a, parent close
// frames, c2c8 fade and timer, 2a00 child removal and the parent object re-entry.
Bytes nested_ram;State nested_state;Ports nested_ports;Bytes nested_start;State nested_old; // SAVE OK a698 frame
unsigned int chain(bool ok){
 Bytes ram;State s;to_result(ok,ram,s);unsigned int n=0;
 // 1. Opening (open unit a5d2/a348): c=3 adds c<<6=c0 to the WORD 4(A2) (residual BYTE 5 = 5a) until the
 // BYTE reaches c; c<<8=300 caps the WORD. The box is drawn first at the old BYTE height (0 draws nothing).
 const std::uint32_t grow[]={0x011a,0x01da,0x029a,0x0300};const unsigned int drawn[]={0,1,1,2};
 for(unsigned int k=0;k<4;++k){Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o));++n;
  Ports e;box(e,7,7,0x0e,drawn[k],0x0b);assert(same_ports(o.ports,e));
  assert(get(ram,UP+4,2)==grow[k]&&get(ram,E5,1)==1&&get(ram,F2,4)==UP&&get(ram,EE,4)==UP&&get(ram,TOP+4,2)==0x0600&&get(ram,TOP+7,1)==2);
  assert(get(ram,CHILD+0x7e,2)==0x0129&&s.a[7]==SP+4&&s.d[0]==0&&get(ram,CHILD,4)==0xc2ba);}
 // 2. a5ea: -e5=0, first full draw, a63e D0=6 -> bf94 7e=001e, a64c D0=0 -> a73e sound 1a6c
 // (3af8 moves the queued 1a6c behind 1adb).
 {Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o)&&same_ports(o.ports,result_full(ok)));++n;
  assert(get(ram,E5,1)==0&&get(ram,CHILD+0x7e,2)==0x001e&&get(ram,UP+4,2)==0x0300&&get(ram,UP+7,1)==0&&get(ram,UP+8,1)==0&&get(ram,UP+0xe,1)==0xff);
  assert(get(ram,RING,2)==0x1adb&&get(ram,RING+2,2)==0x1a6c&&get(ram,RING_W,2)==4&&get(ram,CHILD+0x80,1)==0);}
 // 3. Input frames: a370 walks both frames (the parent below -f2 has f bit0 clear and no a(desc) hook);
 // a406 on the result frame, hook bf2c counts 7e down; at 0, 9ff4 e=3 -> 9b3e D0=3 -> bf94 80=ff,
 // JMP a70a: sound 1a5b, a1ee -e5=2.
 for(unsigned int k=1;k<=0x1e;++k){Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&quiet(o));++n;
  assert(get(ram,CHILD+0x7e,2)==0x1eU-k&&get(ram,E5,1)==(k==0x1e?2U:0U)&&get(ram,CHILD+0x80,1)==(k==0x1e?0xffU:0U));
  assert(get(ram,UP+4,2)==0x0300&&get(ram,UP+0xe,1)==0xff&&get(ram,F2,4)==UP&&get(ram,EE,4)==UP&&s.a[7]==SP+4&&s.d[0]==0);}
 assert(get(ram,RING+4,2)==0x1a5b&&get(ram,RING_W,2)==6&&s.a[2]==UP);
 // 4. Result close frames (close unit a662/a2be): 6(A2)=1 -> WORD 4(A2) shrinks by 0040; one row is
 // erased when the low BYTE plus 40 carries. The last shrink leaves WORD 00c0 (BYTE 4 = 0).
 const std::uint32_t shrink[]={0x02c0,0x0280,0x0240,0x0200,0x01c0,0x0180,0x0140,0x0100,0x00c0};
 for(unsigned int k=0;k<9;++k){Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o));++n;
  const unsigned int rows=(shrink[k]&0xffU)==0xc0U?1U:0U;
  assert(same_ports(o.ports,closing(7,7,0x0e,shrink[k]>>8,rows))&&get(ram,UP+4,2)==shrink[k]);
  assert(get(ram,E5,1)==2&&get(ram,F2,4)==UP&&get(ram,EE,4)==UP&&get(ram,TOP+4,2)==0x0600&&s.d[0]==0&&s.a[7]==SP+4);}
 // 5. Nested return: BYTE 4 = 0 -> a67a 9e94 (no rows), -f2 += 10 = 107efe < 107f0e -> a698:
 // -e5=0, -ee=parent, 8=7(=2), D0=7 -> c1c4 (no effect); -f2 still = parent -> a6bc D0=0 -> c1c4 ->
 // a73e sound 1a6c (moved behind 1a5b); a6ce -> a6da redraws 107efe (the only frame; 107eee < pushed
 // 107efe ends the loop); a6d6 D0=0 RTS to c2c0 -> c2c6 -> 2ac2.
 {const Bytes start=ram;State old=s;old.pc=0x2ab8;assert(s.carry==ms5::AnimationCarryUnknown);Out o;
  assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o)&&same_ports(o.ports,parent_redraw()));++n;
  assert(get(ram,E5,1)==0&&get(ram,F2,4)==TOP&&get(ram,EE,4)==TOP&&get(ram,TOP+4,2)==0x0600&&get(ram,TOP+7,1)==2&&get(ram,TOP+8,1)==3);
  assert(get(ram,UP+4,2)==0x00c0&&get(ram,RING,2)==0x1adb&&get(ram,RING+2,2)==0x1a5b&&get(ram,RING+4,2)==0x1a6c&&get(ram,RING_W,2)==6);
  assert(s.d[0]==0&&s.a[2]==TOP&&s.a[7]==SP+4&&s.a[6]==CHILD&&s.a[5]==0x108000&&get(ram,CHILD,4)==0xc2ba&&get(ram,CHILD+0x80,1)==0xff);
  assert(s.carry==ms5::AnimationCarryUnknown);
  if(ok){nested_start=start;nested_old=old;nested_ram=ram;nested_state=s;nested_ports=o.ports;}
  // Stop at a698: the close unit popped the result frame; A2 = parent; c2c0 is the only pending return.
  Bytes r=start;inputs(r,0,0,0,0);State t=old;Out a;assert(run(r,t,NESTED,a)&&clean(a)&&a.ports.empty());
  assert(t.a[2]==TOP&&get(r,F2,4)==TOP&&get(r,EE,4)==UP&&get(r,E5,1)==2&&t.a[7]==SP-4&&get(r,SP-4,4)==0xc2c0);
  // Stop at a6b2 after the D0=7 callback: A2 pushed, -e5 already 0, ring unchanged.
  a=Out();assert(run(r,t,0xa6b2,a)&&a.ports.empty()&&t.a[7]==SP-8&&get(r,SP-8,4)==TOP&&get(r,E5,1)==0&&get(r,EE,4)==TOP);
  assert(get(r,TOP+8,1)==2&&(t.d[0]&65535U)==7&&get(r,RING_W,2)==6&&get(r,RING+4,2)==0x1a5b);
  // Stop at a6ce after the D0=0 callback: sound queued, A2 still the popped parent.
  a=Out();assert(run(r,t,0xa6ce,a)&&a.ports.empty()&&t.a[7]==SP-4&&get(r,RING+4,2)==0x1a6c&&(t.d[0]&65535U)==0);
  // a6da: A2=107efe, A1=a008, the pushed A2 above a6d6.
  a=Out();assert(run(r,t,0xa6ea,a)&&a.ports.empty()&&t.a[2]==TOP&&t.a[1]==0xa008&&t.a[7]==SP-12&&get(r,SP-12,4)==TOP&&get(r,SP-8,4)==0xa6d6);
  a=Out();assert(run(r,t,0xa706,a)&&same_ports(a.ports,parent_redraw())&&t.a[2]==UP&&get(r,EE,4)==TOP);}
 // 6. Parent frame: -e5=0 -> a406 (4=6 >= c=6) -> hook bf2c: 7e=0 (no decrement), 80!=0 -> bf50 JSR a70a:
 // sound 1a5b (moved behind 1a6c), a1ee -e5=2.
 {Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&quiet(o));++n;
  assert(get(ram,E5,1)==2&&get(ram,CHILD+0x7e,2)==0&&get(ram,CHILD+0x80,1)==0xff&&get(ram,TOP+4,2)==0x0600&&get(ram,F2,4)==TOP&&get(ram,EE,4)==TOP);
  assert(get(ram,RING,2)==0x1adb&&get(ram,RING+2,2)==0x1a6c&&get(ram,RING+4,2)==0x1a5b&&get(ram,RING_W,2)==6&&s.a[7]==SP+4);}
 // 7. Parent close frames: 6(A2)=4 -> 0100 per frame, one erased row each.
 for(unsigned int k=1;k<=6;++k){Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o));++n;
  const std::uint32_t h=0x0600U-0x100U*k;assert(same_ports(o.ports,closing(4,4,0x11,h>>8,1))&&get(ram,TOP+4,2)==h);
  assert(get(ram,E5,1)==2&&get(ram,F2,4)==TOP&&get(ram,EE,4)==TOP&&s.a[2]==TOP&&s.d[0]==0&&s.a[7]==SP+4&&get(ram,CHILD,4)==0xc2ba);}
 // 8. Empty stack: a67a, -f2=107f0e, a694 D0=-1 -> c2c8: fade 8c16, 7e=14, (A6)=c2e0, first SUBQ.
 {Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&quiet(o));++n;
  assert(get(ram,F2,4)==0x107f0e&&get(ram,CHILD+0x7e,2)==0x13&&get(ram,CHILD,4)==0xc2e0&&get(ram,0x107dc8,2)==0xe100&&get(ram,0x107dcc,2)==0xe100);}
 for(unsigned int k=1;k<0x13;++k){Out o;assert(idle(ram,s,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x13U-k&&s.a[7]==SP+4&&s.a[6]==CHILD);++n;}
 // 9. 7e 1 -> 0: parent 62=ff, JMP 2a00 removes the child (port 300001 = D0.B), A6=OBJ.
 {const std::uint32_t d0=s.d[0];Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o)&&o.ports.size()==1&&o.ports[0].address==0x300001&&o.ports[0].value==(d0&255U));++n;
  assert(get(ram,OBJ+0x62,1)==0xff&&get(ram,CHILD,4)==0x270e&&get(ram,CHILD+0x7e,2)==0&&s.a[6]==OBJ&&s.a[7]==SP+4);
  assert(get(ram,OBJ+8,4)==NEXT&&get(ram,NEXT+4,4)==OBJ&&get(ram,CHILD+8,4)==FREE&&get(ram,0x104c9c,4)==CHILD&&get(ram,0x104ca0,2)==2);}
 // 10. Parent object re-entry (A6=OBJ): 480ac 62=ff -> 2a00 (type 0 -> 271c reset) -> 2ac2.
 {const std::uint32_t d0=s.d[0];Out o;assert(idle(ram,s,o)&&s.pc==RETURN&&clean(o)&&o.ports.size()==1&&o.ports[0].address==0x300001&&o.ports[0].value==(d0&255U));++n;
  assert(get(ram,OBJ,4)==0x270e&&get(ram,OBJ+0x62,1)==0&&s.a[6]==OBJ&&s.a[7]==SP+4&&get(ram,OBJ+8,4)==NEXT&&get(ram,0x104ca0,2)==2);}
 // The next object and scene are outside this unit: another re-entry stops at an unsupported PC.
 {Bytes r=ram;State t=s;inputs(r,0,0,0,0);t.pc=0x2ab8;reject(r,t,RETURN,"unsupported animation machine PC");}
 // Menu text bytes untouched; the result frame record stays below the stack top.
 assert(get(ram,UP,4)==(ok?0xc214U:0xc232U)&&get(ram,STATUS,1)==(ok?0U:1U));
 return n;
}
void natural(){
 frames=chain(true);assert(frames==73);assert(chain(false)==73);
 // Walk through the nested frame: chained stops equal the continuous run.
 Bytes in=nested_start;inputs(in,0,0,0,0);
 const std::uint32_t walk[]={0x2abe,0x2ac0,0xc2ba,FRAME,0xa380,0xa388,0xa396,0xa3b8,0xa3c8,0xa380,0xa388,0xa3b8,0xa3c8,0xa3d0,0xa3e2,0xa3f2,
  CLOSE,0xa67a,0x9e94,0x9eb0,0x9ee4,0xa67e,NESTED,0x9b3e,0x9b26,0x9b42,0x9b54,0xc1c4,0xa73e,0xa754,0xc1ca,0xc1de,0xc212,0xa6b2,0xa6bc,
  0x9b3e,0x9b42,0xc1c4,0xa73e,0xa74a,0x3af8,0xa754,0xc212,0xa6ce,REDRAW,0xa6ea,0xa6f0,0x9b58,0x9b7a,0x9b82,0xa6f8,0x9e1a,0x9e28,0x9e78,
  0x9e92,0xa6fc,0xa6ea,0xa706,0xa6d6,0xc2c0,0xc2c6,RETURN};
 splits(in,nested_old,nested_ram,nested_state,nested_ports,walk,sizeof(walk)/sizeof(walk[0]));
}
// Menu frame record: (A2)=desc, WORD 4 = h<<8, 6=items, 7/8=cursor, 9/a=x/y, b=width, c=h, d=3, e=ff, f=0.
void menu(Bytes&ram,std::uint32_t at,std::uint32_t desc,std::uint32_t h,std::uint32_t items,std::uint32_t cur,std::uint32_t x,std::uint32_t y,std::uint32_t w){
 put(ram,at,4,desc);put(ram,at+4,2,h<<8);put(ram,at+6,1,items);put(ram,at+7,1,cur);put(ram,at+8,1,cur);put(ram,at+9,1,x);put(ram,at+0xa,1,y);
 put(ram,at+0xb,1,w);put(ram,at+0xc,1,h);put(ram,at+0xd,1,3);put(ram,at+0xe,1,0xff);put(ram,at+0xf,1,0);}
// Descriptor: title 0, hooks 0, flags 0, n items {TEXT "AB", callback, WORD 0}, ffffffff end.
void descriptor(Bytes&ram,std::uint32_t at,const std::uint32_t*cb,unsigned int n){
 for(unsigned int i=0;i<0x10;++i)put(ram,at+i,1,0);
 for(unsigned int i=0;i<n;++i){put(ram,at+0x10+10*i,4,TEXT);put(ram,at+0x14+10*i,4,cb[i]);put(ram,at+0x18+10*i,2,0);}
 put(ram,at+0x10+10*n,4,0xffffffffU);}
// RAM fixture: -f2=-ee=TOP, -ea=e84c8, -e5=2, sound gates and ring clear; TOP at (1,1) w=5 h=3 with
// 2 items (callbacks bf94 and 0), cursor 0; STOP LONGs on the stack; A2=TOP.
void generic(std::uint32_t pc,Bytes&ram,State&s){
 ram.assign(65536,0);for(unsigned int i=0;i<8;++i)put(ram,SP+4*i,4,STOP);
 put(ram,F2,4,TOP);put(ram,EE,4,TOP);put(ram,0x107f16,4,0xe84c8);put(ram,E5,1,2);
 const std::uint32_t cb[]={0xbf94,0};descriptor(ram,DESC,cb,2);menu(ram,TOP,DESC,3,2,0,1,1,5);text(ram,TEXT,"AB",65535);
 s=state(pc);s.a[2]=TOP;}
// Uncovered redraw of one frame (9b58 then 9e1a): rows below 4(A2); text palette 0003 for the cursor row
// or any row of the -f2 frame, 0603 otherwise (9f7c).
void redraw(Ports&e,std::uint32_t x,std::uint32_t y,unsigned int w,unsigned int h,unsigned int items,unsigned int cur,bool top){
 box(e,x,y,w,h,top?0x0b:0x6b);for(unsigned int i=0;i<items&&i+1<h;++i)row(e,x,y,i,i==cur,(top||i==cur)?3U:0x0603U,"AB");}
// Every block start {pc, next} from the generic fixture.
const std::uint32_t TABLE[][2]={
 {NESTED,0x9b3e},{0xa6b2,0xa6ce},{0xa6bc,0x9b3e},{0xa6ce,REDRAW},{0xa6d6,STOP},{REDRAW,0xa6ea},{0xa6ea,0xa6f0},
 {0xa6f0,0x9b58},{0xa6f8,0x9e1a},{0xa6fc,0xa6ea},{0xa706,STOP}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
// Blocks made only of MOVEA/BSR/RTS (capstone classification of the original opcodes). a6fc (SUBA.W),
// a6b2/a6ea (CMPA), a6da/a6f0 (MOVE.L An,...), a698/a6bc (MOVE) and a6d6 (MOVEQ) give Unknown.
const std::uint32_t KEEP[]={0xa6ce,0xa6f8,0xa706};
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
void blocks(){
 // a698: -e5 BYTE 0, -ee=A2, 8=7, MOVE.W #7 keeps D0's high WORD, A2 then a6b2 pushed.
 {Bytes ram;State s;generic(NESTED,ram,s);put(ram,TOP+7,1,1);put(ram,EE,4,0);s.d[0]=0x12345678;Out o;
  assert(run(ram,s,0x9b3e,o)&&quiet(o)&&get(ram,E5,1)==0&&get(ram,EE,4)==TOP&&get(ram,TOP+8,1)==1&&s.d[0]==0x12340007U);
  assert(s.a[7]==SP-8&&get(ram,SP-4,4)==TOP&&get(ram,SP-8,4)==0xa6b2&&s.a[2]==TOP);}
 // a6b2: full 32-bit CMPA.L against the live -f2 LONG (A5-relative).
 {const std::uint32_t popped[][2]={{TOP,0xa6bc},{TOP|0x01000000U,0xa6ce},{UP,0xa6ce},{TOP+1,0xa6ce}};
  for(unsigned int i=0;i<4;++i){Bytes ram;State s;generic(0xa6b2,ram,s);put(ram,SP,4,popped[i][0]);Out o;
   assert(run(ram,s,popped[i][1],o)&&quiet(o)&&s.a[2]==popped[i][0]&&s.a[7]==SP+4);}
  Bytes ram;State s;generic(0xa6b2,ram,s);put(ram,SP,4,UP);s.a[5]=0x109000;put(ram,0x108f0e,4,UP);Out o;assert(run(ram,s,0xa6bc,o)&&s.a[2]==UP);}
 // a6bc: MOVE.W #0 keeps D0's high WORD; 8=7; JSR 9b3e pushes a6ce.
 {Bytes ram;State s;generic(0xa6bc,ram,s);put(ram,TOP+7,1,1);put(ram,EE,4,0);s.d[0]=0x5555aaaaU;Out o;
  assert(run(ram,s,0x9b3e,o)&&quiet(o)&&s.d[0]==0x55550000U&&get(ram,EE,4)==TOP&&get(ram,TOP+8,1)==1&&get(ram,SP-4,4)==0xa6ce&&s.a[7]==SP-4);}
 // a6ce: live -ee read through A5; BSR a6da pushes a6d6.
 {Bytes ram;State s;generic(0xa6ce,ram,s);s.a[5]=0x109000;put(ram,0x108f12,4,UP);Out o;
  assert(run(ram,s,REDRAW,o)&&quiet(o)&&s.a[2]==UP&&get(ram,SP-4,4)==0xa6d6);}
 // a6d6: MOVEQ #0 clears all 32 bits.
 {Bytes ram;State s;generic(0xa6d6,ram,s);s.d[0]=0xffffffffU;Out o;assert(run(ram,s,STOP,o)&&s.d[0]==0&&s.a[7]==SP+4);}
 // a6da: push A2, A2=107f0e-10 (whole register), A1=a008.
 {Bytes ram;State s;generic(REDRAW,ram,s);s.a[2]=0xdeadbeefU;s.a[1]=0;Out o;
  assert(run(ram,s,0xa6ea,o)&&quiet(o)&&s.a[2]==TOP&&s.a[1]==0xa008&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xdeadbeefU);}
 // a6ea: unsigned 32-bit compare against the live stack LONG.
 {const std::uint32_t cmp[][3]={{0x80000000U,0x7ffffffeU,0xa6f0},{TOP,TOP,0xa6f0},{TOP,TOP+2,0xa706},{0x7ffffffeU,0x80000000U,0xa706},{UP,TOP,0xa706},{TOP,UP,0xa6f0}};
  for(unsigned int i=0;i<6;++i){Bytes ram;State s;generic(0xa6ea,ram,s);s.a[2]=cmp[i][0];put(ram,SP,4,cmp[i][1]);Out o;
   assert(run(ram,s,cmp[i][2],o)&&quiet(o)&&s.a[7]==SP&&s.a[2]==cmp[i][0]);}}
 // a6f0: -ee=A2 (A5-relative), BSR 9b58 pushes a6f8; a6f8 BSR 9e1a pushes a6fc.
 {Bytes ram;State s;generic(0xa6f0,ram,s);s.a[2]=UP;s.a[5]=0x109000;Out o;
  assert(run(ram,s,0x9b58,o)&&quiet(o)&&get(ram,0x108f12,4)==UP&&get(ram,EE,4)==TOP&&get(ram,SP-4,4)==0xa6f8);}
 {Bytes ram;State s;generic(0xa6f8,ram,s);Out o;assert(run(ram,s,0x9e1a,o)&&quiet(o)&&get(ram,SP-4,4)==0xa6fc&&s.a[7]==SP-4);}
 // a6fc: SUBA.W #10 is a 32-bit subtract of the re-read -ee (8 -> fffffff8).
 {Bytes ram;State s;generic(0xa6fc,ram,s);put(ram,EE,4,8);Out o;assert(run(ram,s,0xa6ea,o)&&s.a[2]==0xfffffff8U);}
 // a706: MOVEA.L (A7)+,A2; RTS.
 {Bytes ram;State s;generic(0xa706,ram,s);put(ram,SP,4,UP);put(ram,SP+4,4,STOP);Out o;assert(run(ram,s,STOP,o)&&s.a[2]==UP&&s.a[7]==SP+8);}
}
void stacks(){
 // Three frames remain after a pop (TOP, UP, LOW=-f2, non-overlapping, callbacks 0): a698 with A2=LOW;
 // both 9b3e calls return at 9b56; a6da draws TOP, UP, LOW (a6ea loop 3 times), oldest first.
 Bytes ram;State s;generic(NESTED,ram,s);const std::uint32_t none[]={0,0};
 descriptor(ram,DESC,none,1);descriptor(ram,DESC2,none,2);descriptor(ram,DESC3,none,1);
 menu(ram,TOP,DESC,3,1,0,1,1,5);menu(ram,UP,DESC2,3,2,0,8,1,5);menu(ram,LOW,DESC3,3,1,0,1,8,5);put(ram,F2,4,LOW);put(ram,EE,4,0);s.a[2]=LOW;
 const Bytes start=ram;const State old=s;Out o;
 assert(run(ram,s,STOP,o)&&clean(o)&&s.a[7]==SP+4&&s.a[2]==LOW&&s.d[0]==0&&s.a[1]==0xa008);
 Ports e;redraw(e,1,1,5,3,1,0,false);redraw(e,8,1,5,3,2,0,false);redraw(e,1,8,5,3,1,0,true);assert(same_ports(o.ports,e));
 assert(get(ram,EE,4)==LOW&&get(ram,E5,1)==0&&get(ram,F2,4)==LOW&&get(ram,RING_W,2)==0&&get(ram,UP+8,1)==1&&get(ram,TOP+8,1)==0);
 // Loop order through the a6f0 stops: -ee = 107efe, 107eee, 107ede, then a706 with A2 = 107ece.
 {Bytes r=start;State t=old;const std::uint32_t at[]={TOP,UP,LOW};
  for(unsigned int i=0;i<3;++i){Out a;assert(run(r,t,0xa6f0,a)&&t.a[2]==at[i]&&get(r,SP-8,4)==LOW);a=Out();assert(run(r,t,0xa6f8,a)&&get(r,EE,4)==at[i]);}
  Out a;assert(run(r,t,0xa706,a)&&t.a[2]==LOW-0x10U&&get(r,t.a[7],4)==LOW);}
 const std::uint32_t walk[]={NESTED,0x9b3e,0x9b56,0xa6b2,0xa6bc,0x9b3e,0x9b56,0xa6ce,REDRAW,0xa6ea,0xa6f0,0x9b58,0xa6f8,0x9e1a,0xa6fc,0xa6ea,
  0xa6f0,0xa6f8,0xa6fc,0xa6ea,0xa6f0,0xa6f8,0xa6fc,0xa6ea,0xa706,0xa6d6,STOP};
 splits(start,old,ram,s,o.ports,walk,sizeof(walk)/sizeof(walk[0]));
 // a6b4 mismatch: A2=TOP (cursor callback bf94) while -f2=UP: D0=7 only (no D0=0 sound), a6ce ->
 // a6da pushes TOP: only TOP is redrawn (palette 6b, A2 != -f2); UP is below the pushed A2.
 {Bytes r;State t;generic(NESTED,r,t);const std::uint32_t cb[]={0xbf94};descriptor(r,DESC,cb,1);descriptor(r,DESC2,none,1);
  menu(r,TOP,DESC,3,1,0,1,1,5);menu(r,UP,DESC2,3,1,0,8,1,5);put(r,F2,4,UP);Out a;
  assert(run(r,t,STOP,a)&&clean(a)&&get(r,RING_W,2)==0&&get(r,RING,2)==0&&get(r,EE,4)==TOP&&t.a[2]==TOP&&t.d[0]==0);
  Ports x;redraw(x,1,1,5,3,1,0,false);assert(same_ports(a.ports,x));
  // Same frame with -f2 = TOP: a6bc runs, D0=0 queues 1a6c, palette 0b.
  Bytes q;State u;generic(NESTED,q,u);descriptor(q,DESC,cb,1);menu(q,TOP,DESC,3,1,0,1,1,5);Out b;
  assert(run(q,u,STOP,b)&&clean(b)&&get(q,RING,2)==0x1a6c&&get(q,RING_W,2)==2);
  Ports y;redraw(y,1,1,5,3,1,0,true);assert(same_ports(b.ports,y));
  Bytes r2=r;State t2;generic(NESTED,r2,t2);descriptor(r2,DESC,cb,1);descriptor(r2,DESC2,none,1);menu(r2,TOP,DESC,3,1,0,1,1,5);menu(r2,UP,DESC2,3,1,0,8,1,5);put(r2,F2,4,UP);
  const std::uint32_t miss[]={NESTED,0x9b3e,0xbf94,0xa73e,0xa754,0xbf9a,0xbfa8,0xbfbc,0xa6b2,0xa6ce,REDRAW,0xa6ea,0xa6f0,0xa6f8,0xa6fc,0xa6ea,0xa706,0xa6d6,STOP};
  splits(r2,t2,r,t,a.ports,miss,sizeof(miss)/sizeof(miss[0]));}
 // D0=7 callback with an effect: the cursor item calls 9ff4 (MOVEA.L -ee(A5),A2; MOVE.B D0,e(A2); RTS),
 // which records each D0 it is called with: 7 from a698, 0 from a6bc, then 5 from the 9e08 row callback
 // of the a6da redraw (9d3a calls 9b3e with D0=5 for every drawn row). 9b26 MOVEQ #0 clears D0's high WORD
 // before 9b42 restores the pushed WORD.
 {Bytes r;State t;generic(NESTED,r,t);const std::uint32_t cb[]={0x9ff4,0};descriptor(r,DESC,cb,2);t.d[0]=0xcccc0000U;
  const Bytes start2=r;const State old2=t;Out a;
  assert(run(r,t,STOP,a)&&clean(a)&&get(r,TOP+0xe,1)==5&&get(r,RING_W,2)==0&&t.d[0]==0&&t.a[2]==TOP);
  Ports x;redraw(x,1,1,5,3,2,0,true);assert(same_ports(a.ports,x));
  Bytes q=start2;State u=old2;Out b;assert(run(q,u,0xa6b2,b)&&b.ports.empty()&&get(q,TOP+0xe,1)==7&&u.a[2]==TOP&&u.d[0]==7U);
  b=Out();assert(run(q,u,0xa6ce,b)&&b.ports.empty()&&get(q,TOP+0xe,1)==0&&u.d[0]==0U);
  b=Out();assert(run(q,u,STOP,b)&&q==r&&same(u,t)&&same_ports(b.ports,x));}
 // The same callback with the a6b4 mismatch (-f2 = UP != A2): a6bc is skipped, so e keeps 7 until the redraw.
 {Bytes r;State t;generic(NESTED,r,t);const std::uint32_t cb[]={0x9ff4},none[]={0};descriptor(r,DESC,cb,1);descriptor(r,DESC2,none,1);
  menu(r,TOP,DESC,3,1,0,1,1,5);menu(r,UP,DESC2,3,1,0,8,1,5);put(r,F2,4,UP);Out a;
  assert(run(r,t,0xa6ce,a)&&get(r,TOP+0xe,1)==7);a=Out();assert(run(r,t,STOP,a)&&get(r,TOP+0xe,1)==5);}
}
// a6da from the open unit's a3b4 (a370 frame): the older TOP (f bit0, WORD 0100, 6=1: step 40) shrinks to
// 00c0 (BYTE 0, one erased row) under the newer UP=-f2 (non-overlapping); a3ac BYTE 0 -> BSR a6da pushes TOP; 107efe >= TOP draws TOP (h=0: no box,
// no rows), 107eee < TOP ends the loop; RTS to a3b8.
void open_entry(){
 Bytes ram;State s;generic(FRAME,ram,s);const std::uint32_t none[]={0};descriptor(ram,DESC2,none,1);
 menu(ram,TOP,DESC,1,1,0,1,1,5);put(ram,TOP+0xf,1,1);menu(ram,UP,DESC2,3,1,0,8,1,5);put(ram,F2,4,UP);
 const Bytes start=ram;const State old=s;Out o;
 assert(run(ram,s,0xa3b8,o)&&clean(o)&&s.a[2]==TOP&&s.a[1]==0xa008&&s.a[7]==SP-4&&get(ram,SP-4,4)==TOP&&get(ram,EE,4)==TOP);
 Ports e;erase(e,1,1,0,5,1);assert(same_ports(o.ports,e)&&get(ram,TOP+4,2)==0x00c0&&get(ram,F2,4)==UP);
 const std::uint32_t walk[]={FRAME,0xa380,0xa388,0xa396,0xa3a0,0xa3a8,0xa2be,0xa3ac,0xa3b4,REDRAW,0xa6ea,0xa6f0,0x9b58,0x9b64,0xa6f8,0x9e1a,
  0x9e26,0xa6fc,0xa6ea,0xa706,0xa3b8};
 splits(start,old,ram,s,o.ports,walk,sizeof(walk)/sizeof(walk[0]));
}
void errors(){
 // Odd A7: LONG push (a698, a6da), pop (a6b2, a706), live CMPA.L (A7) read (a6ea), BSR push (a6f0 after the
 // -ee write), RTS pop (a6d6).
 const std::uint32_t odd7[]={NESTED,0xa6b2,REDRAW,0xa6ea,0xa6f0,0xa706,0xa6d6};
 for(unsigned int i=0;i<7;++i){Bytes ram;State s;generic(odd7[i],ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A2 at a698: -e5/-ee writes, the BYTE copy and both pushes succeed; 9b26 MOVEA.L (A2) fails; all rolled back.
 {Bytes ram;State s;generic(NESTED,ram,s);s.a[2]=TOP+1;reject(ram,s,STOP,"even WORD/LONG");
  Out o;Bytes r=ram;State t=s;assert(run(r,t,0x9b3e,o)&&get(r,EE,4)==TOP+1&&get(r,E5,1)==0);}
 // Odd A2 at a6bc (the popped A2 equal to an odd -f2) and at a6f0 (the drawn frame): 9b26 / 9b58 LONG reads fail.
 {Bytes ram;State s;generic(0xa6b2,ram,s);put(ram,SP,4,TOP+1);put(ram,F2,4,TOP+1);reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xa6f0,ram,s);s.a[2]=TOP+1;put(ram,TOP+5,1,1);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd -ee from the a6fc re-read (A2 = TOP+1 >= (A7) = 0): a6f0, then 9b58 (4(A2) = BYTE TOP+5 nonzero)
 // reads (A2) at an odd address.
 {Bytes ram;State s;generic(0xa6fc,ram,s);put(ram,EE,4,TOP+0x11);put(ram,SP,4,0);put(ram,TOP+5,1,1);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A5: -ee LONG write (a698 after the -e5 BYTE write, a6bc, a6f0), -ee LONG read (a6ce, a6fc), -f2 read (a6b2).
 const std::uint32_t odd5[]={NESTED,0xa6bc,0xa6f0,0xa6ce,0xa6fc,0xa6b2};
 for(unsigned int i=0;i<6;++i){Bytes ram;State s;generic(odd5[i],ram,s);s.a[5]=0x108001;reject(ram,s,STOP,i<3?"alignment":"even WORD/LONG");}
 // Interior and bundled PCs (CMPA.L+BNE at a6b4/a6b8, CMPA.L (A7)+BCS at a6ec, every operand word).
 unsigned int interior=0;
 for(std::uint32_t pc=0xa698;pc<=0xa708;pc+=2){if(listed(pc))continue;Bytes ram;State s;generic(pc,ram,s);
  reject(ram,s,STOP,"unsupported animation card menu nested PC");++interior;}
 assert(interior==46); // 57 even PCs in a698..a708 minus 11 block starts
 const std::uint32_t bundled[]={0xa6b4,0xa6b8,0xa6ec,0xa6e2,0xa6e6,0xa6ac,0xa6ae,0xa6d2,0xa700,0xa704,0xa708};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){assert(!listed(bundled[i]));Bytes ram;State s;generic(bundled[i],ram,s);reject(ram,s,STOP,"unsupported animation card menu nested PC");}
 // Neighbours belong to the close (a696) and input (a70a) units; odd PCs are rejected first.
 {Bytes ram;State s;generic(0xa696,ram,s);reject(ram,s,STOP,"unsupported animation card menu close PC");}
 {Bytes ram;State s;generic(0xa699,ram,s);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int carry=0;carry<3;++carry)for(unsigned int i=0;i<ROWS;++i){
  Bytes ram;State s;generic(TABLE[i][0],ram,s);s.carry=carry_of(carry);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,TABLE[i][0],o)&&same(s,old)&&ram==before&&quiet(o));}
}
// Every block start with every entry carry (Unknown included: no nested block consumes C).
void carry(){
 assert(ROWS==11);unsigned int keeps=0;
 for(unsigned int i=0;i<ROWS;++i){const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,3,pc);if(keep)++keeps;
  for(unsigned int carry=0;carry<3;++carry){Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);Out o;
   if(!(run(ram,s,TABLE[i][1],o)&&s.pc==TABLE[i][1]&&quiet(o)))std::cerr<<std::hex<<"row "<<pc<<"\n";
   assert(s.pc==TABLE[i][1]&&quiet(o)&&s.carry==(keep?carry_of(carry):ms5::AnimationCarryUnknown));}}
 assert(keeps==3);
}
}
int main(){natural();blocks();stacks();open_entry();errors();zero_step();carry();
std::cout<<"animation_machine_card_menu_nested_test PASS "<<std::dec<<frames<<" natural frames, "<<calls<<" API invocations\n";}
