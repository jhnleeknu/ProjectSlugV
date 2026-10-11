#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef std::vector<ms5::VideoPortWrite> Ports;
typedef ms5::AnimationMachineState State;
const std::uint32_t SP=0x1feffc,STOP=0xff000,OBJ=0x102000,NEXT=0x102200,FREE=0x103400,CHILD=0x103000,TOP=0x107efe,UP=0x107eee;
const std::uint32_t FRAME=0xa370,RETURN=0x2ac2,CLOSE=0xa662,NESTED=0xa698,REMOVE=0x2a00,DESC=0x104100;
const std::uint32_t OLD_EE=0x10a0b0c0,E5=0x107f1b,F2=0x107f0e,EE=0x107f12,P1=0x104cba,P2=0x104cc0,CARD1=0x10fdb6,CARD2=0x10fdb7;
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
// Successful run: no external reads, returned status, PVC untouched (3c0000/300001 events are ports only).
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
// Expected video events. cell: LSL.W #5 of x, ADD.B y (BYTE only), ADDI.W #7000.
std::uint32_t cell(std::uint32_t x,std::uint32_t y){return ((((x<<5)&0xff00U)|(((x<<5)+y)&0xffU))+0x7000U)&65535U;}
void port(Ports&v,unsigned int size,std::uint32_t value){ms5::VideoPortWrite p;p.address=0x3c0000;p.size=static_cast<std::uint8_t>(size);p.value=value;v.push_back(p);}
// One newer stack frame for the a018 cover test (col 9, width b, row a, rows 4 as BYTEs); none when h=0.
struct Cover {std::uint32_t x,w,y,h;};
// a018: D7=D0.W-7000; D6=D7 LSR.W 5; D7&=1f; covered when (D6.B-x).B < w and (D7.B-y).B < h.
bool covered(const Cover&c,std::uint32_t pos){
 std::uint32_t d7=(pos-0x7000U)&65535U;const std::uint32_t d6=d7>>5;d7&=0x1fU;
 return ((d6-c.x)&255U)<c.w&&((d7-c.y)&255U)<c.h;}
// 9b58 tile: a covered cell skips both the LONG write and the ADDI.W #20 (BCS to the next block).
void tile(Ports&v,const Cover&c,std::uint32_t&d0,std::uint32_t pal,std::uint32_t t){
 if(covered(c,d0))return;port(v,4,(d0<<16)|(pal<<8)|t);d0=(d0+0x20U)&65535U;}
void tile_row(Ports&v,const Cover&c,std::uint32_t a,std::uint32_t pal,std::uint32_t first,std::uint32_t mid,std::uint32_t last,unsigned int w){
 std::uint32_t d0=a;tile(v,c,d0,pal,first);for(unsigned int d6=w;d6>2;--d6)tile(v,c,d0,pal,mid);tile(v,c,d0,pal,last);}
// 9b58 box at h rows (top, h-2 middle, bottom; h=1 still draws top and bottom).
void box(Ports&v,const Cover&c,std::uint32_t x,std::uint32_t y,unsigned int w,unsigned int h,std::uint32_t pal){
 if(!h)return;std::uint32_t a=cell(x,y);tile_row(v,c,a,pal,0xf4,0xf0,0xf5,w);
 for(unsigned int r=h;r>2;--r){a=(a+1U)&65535U;tile_row(v,c,a,pal,0xf2,0x60,0xf3,w);}
 a=(a+1U)&65535U;tile_row(v,c,a,pal,0xf6,0xf1,0xf7,w);}
// a2ec..a33c erase: rows from cell(x,y+h) (ADD.B), ADDQ.W per row; ADDI.L #20 on both BCS paths.
void erase(Ports&v,const Cover&c,std::uint32_t x,std::uint32_t y,std::uint32_t h,unsigned int w,unsigned int rows){
 const std::uint32_t base=(cell(x,y)&0xff00U)|((cell(x,y)+h)&0xffU);
 for(unsigned int r=0;r<rows;++r){const std::uint32_t row=(base+r)&65535U;
  for(unsigned int i=0;i<w;++i){const std::uint32_t pos=(row+0x20U*i)&65535U;if(!covered(c,pos))port(v,4,(pos<<16)|0x00ffU);}}}
const Cover NONE={0,0,0,0};
// Synthetic typed physical bytes (not a native ROM oracle): the c188 descriptor and its strings.
Physical resources(){
 Physical p(1);p[0].source_rom_offset=0;p[0].data.assign(0x100000,0);Bytes&f=p[0].data;
 hex(f,0xc188,"0000000000000000bf2c0000000000000000be60000000000000fffffffe0000000000000000be9a0000c1c400000000bea00000bf940000ffffffff");
 text(f,0xbe60,"DATA SAVE ?  ",0xfffff);text(f,0xbe9a," YES ",0xfffff);text(f,0xbea0," NO ",0xfffff);return p;
}
// Declared object-list fixture, as the 28ae allocation in the card child chain leaves it:
// parent OBJ (480ac, type 0, 8=CHILD) -> CHILD (4=OBJ, 8=NEXT, c=OBJ parent, type 1) -> NEXT (type 0).
// 1d=0 and 6c=ff as a recycled record (8eb6/46eec); free list 104c9c=103400 count 1; dispatcher SP at 104ca4.
void objects(Bytes&ram){
 put(ram,OBJ,4,0x480ac);put(ram,OBJ+8,4,CHILD);put(ram,OBJ+0x10,2,0);put(ram,OBJ+0x1d,1,0);put(ram,OBJ+0x62,1,0);put(ram,OBJ+0x6c,1,0xff);
 put(ram,CHILD+4,4,OBJ);put(ram,CHILD+8,4,NEXT);put(ram,CHILD+0xc,4,OBJ);put(ram,CHILD+0x10,2,1);put(ram,CHILD+0x1d,1,0);put(ram,CHILD+0x6c,1,0xff);
 put(ram,NEXT+4,4,CHILD);put(ram,NEXT+0x10,2,0);put(ram,0x104c9c,4,FREE);put(ram,0x104ca0,2,1);put(ram,0x104ca4,4,SP+4);}
void inputs(Bytes&ram,std::uint32_t card1,std::uint32_t card2,std::uint32_t p1,std::uint32_t p2){
 put(ram,CARD1,1,card1);put(ram,CARD2,1,card2);put(ram,P1,1,p1);put(ram,P2,1,p2);}
// Frame re-entry (declared PC=2ab8) with no host input.
bool frame(Bytes&ram,State&s,std::uint32_t stop,Out&o){const Physical p=resources();inputs(ram,0,0,0,0);s.pc=0x2ab8;return run(ram,s,stop,o,&p);}
// Chained stops through a subsequence of the actual trace equal the continuous run; so does a
// fresh split at each checkpoint followed by a continuation.
void splits(const Bytes&start,const State&old,const Bytes&ram,const State&s,const Ports&ports,const std::uint32_t*walk,unsigned int n){
 const Physical p=resources();Bytes split=start;State t=old;Ports all;
 for(unsigned int i=0;i<n;++i){Out so;if(!(run(split,t,walk[i],so,&p)&&t.pc==walk[i]&&clean(so)))std::cerr<<std::hex<<"walk "<<walk[i]<<"\n";
  assert(t.pc==walk[i]&&clean(so));append(all,so.ports);}
 assert(split==ram&&same(t,s)&&same_ports(all,ports));
 for(unsigned int i=0;i+1<n;++i){Bytes r2=start;State u=old;Out a,b;
  assert(run(r2,u,walk[i],a,&p)&&u.pc==walk[i]&&run(r2,u,walk[n-1],b,&p)&&r2==ram&&same(u,s));append(a.ports,b.ports);assert(same_ports(a.ports,ports));}
}
// Natural chain: card child c290 entry (clears 80(A6), loads c188/4/4) -> a29c push -> opening and
// full frames (open unit) -> 300 input frames (input unit): the c188 hook counts 7e 012c down, frame 300
// sends event 3 to NO (80=ff, sound 1a5b) and a1ee sets -e5=2. No declared 7e shortcut is used.
Bytes snap_ram;State snap;
void to_close(){
 const Physical p=resources();Bytes ram(65536,0x5a);put(ram,SP,4,RETURN);put(ram,EE,4,OLD_EE);put(ram,TOP+5,1,0x88);
 put(ram,0x100012,1,0);put(ram,0x104d7e,1,0);put(ram,0x10f001,1,0);put(ram,0x104d8a,2,0);put(ram,0x104d8c,2,0);
 put(ram,CHILD+0x76,4,0xc188);put(ram,CHILD+0x7a,2,4);put(ram,CHILD+0x7c,2,4);objects(ram);State s=state(0xc290);
 Out o;assert(run(ram,s,FRAME,o,&p)&&s.pc==FRAME&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0&&get(ram,CHILD+0x80,1)==0);
 o=Out();assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&get(ram,TOP+4,2)==0x0208);
 for(unsigned int k=0;k<4;++k){assert(get(ram,CHILD,4)==0xc2ba);s.pc=0x2ab8;o=Out();assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&clean(o));}
 assert(get(ram,TOP+4,2)==0x0600&&get(ram,CHILD+0x7e,2)==0x012c&&get(ram,E5,1)==0);
 for(unsigned int k=1;k<=0x12c;++k){o=Out();assert(frame(ram,s,RETURN,o)&&s.pc==RETURN&&quiet(o)&&s.a[7]==SP+4&&get(ram,CHILD+0x7e,2)==0x12cU-k);
  assert(get(ram,E5,1)==(k==0x12c?2U:0U));}
 assert(get(ram,CHILD+0x80,1)==0xff&&get(ram,0x104d84,2)==0x1a5b&&s.a[2]==TOP&&s.a[6]==CHILD&&get(ram,CHILD,4)==0xc2ba);
 // Frame geometry left by the push/open units: 6=4 items, c=6 (opening grew 4(A2) by c<<6=180 per frame),
 // 9=a=4, b=11; e=ff, f=0; -f2=-ee=TOP.
 assert(get(ram,TOP+6,1)==4&&get(ram,TOP+0xc,1)==6&&get(ram,TOP+0xe,1)==0xff&&get(ram,TOP+9,1)==4&&get(ram,TOP+0xa,1)==4&&get(ram,TOP+0xb,1)==0x11&&get(ram,TOP+0xf,1)==0);
 assert(get(ram,F2,4)==TOP&&get(ram,EE,4)==TOP&&get(ram,TOP,4)==0xc188);
 // Object fixture untouched by the menu frames.
 assert(get(ram,CHILD+0xc,4)==OBJ&&get(ram,CHILD+8,4)==NEXT&&get(ram,OBJ+0x62,1)==0&&get(ram,OBJ,4)==0x480ac);
 snap_ram=ram;snap=s;
}
// Expected close frame: 9b58 box at the new height (palette 0b: A2 = -f2), then the erased rows.
Ports closing(unsigned int h,unsigned int rows){Ports e;box(e,NONE,4,4,0x11,h,0x0b);erase(e,NONE,4,4,h,0x11,rows);return e;}
Bytes empty_ram;State empty_state;Bytes last_ram;State last_state;
// Close frames from the -e5=2 snapshot: a662 BSR a2be shrinks WORD 4(A2) by 6(A2)<<6 per frame.
void shrink(Bytes&ram,State&s,const std::uint32_t*heights,const unsigned int*rows,unsigned int n,bool walk_first){
 for(unsigned int k=0;k<n;++k){const Bytes start=ram;State old=s;old.pc=0x2ab8;Out o;
  assert(frame(ram,s,RETURN,o)&&s.pc==RETURN&&clean(o)&&same_ports(o.ports,closing(heights[k]>>8,rows[k])));
  assert(get(ram,TOP+4,2)==heights[k]&&s.d[0]==0&&s.a[7]==SP+4&&s.a[2]==TOP&&s.a[1]==0xa008&&get(ram,E5,1)==2&&get(ram,F2,4)==TOP&&get(ram,EE,4)==TOP);
  assert(get(ram,CHILD,4)==0xc2ba&&(s.d[1]&65535U)==rows[k]&&(s.d[7]&255U)==0&&get(ram,SP-10,2)==0&&s.carry==ms5::AnimationCarryUnknown);
  if(k==0&&walk_first){Bytes in=start;inputs(in,0,0,0,0);
   const std::uint32_t walk[]={0x2abe,0x2ac0,0xc2ba,FRAME,0xa380,0xa388,0xa3b8,0xa3c8,0xa3d0,0xa3e2,0xa3f2,CLOSE,0xa672,0xa2be,0xa2d6,0x9b58,
    0xa2ec,0xa306,0xa30e,0xa318,0xa320,0xa018,0xa324,0xa328,0xa332,0xa33c,0xa344,0xa676,0xc2c0,0xc2c6,RETURN};
   splits(in,old,ram,s,o.ports,walk,sizeof(walk)/sizeof(walk[0]));}
 }
}
void natural(){
 const Physical p=resources();Bytes ram=snap_ram;State s=snap;
 // Natural c188 frame: 6=4 items, so 100 per frame and one erased row each (byte 5 stays 0).
 // (The contract's 0600 0480 0300 0180 0000 needs 6=6; see the declared 6=6 sequence in close_edges.)
 const std::uint32_t heights[]={0x0500,0x0400,0x0300,0x0200,0x0100,0x0000};const unsigned int rows[]={1,1,1,1,1,1};
 shrink(ram,s,heights,rows,6,true);
 empty_ram=ram;empty_state=s;
 // Empty-stack frame: 4(A2)=0 -> a67a JSR 9e94 (4=0: RTS), ADDI.L #10,-f2 -> 107f0e, a694 D0=-1,
 // c2c0 BNE c2c8: fade 8c16 (e1, 14), 7e=14, (A6)=c2e0 and its first SUBQ in the same call.
 {const Bytes start=ram;State old=s;old.pc=0x2ab8;Out o;
  assert(frame(ram,s,RETURN,o)&&s.pc==RETURN&&quiet(o)&&get(ram,F2,4)==0x107f0e&&get(ram,EE,4)==TOP&&s.a[2]==0x107f0e);
  assert(get(ram,CHILD+0x7e,2)==0x13&&get(ram,CHILD,4)==0xc2e0&&s.a[7]==SP+4&&get(ram,E5,1)==2&&get(ram,TOP+4,2)==0);
  assert(get(ram,0x107dc8,2)==0xe100&&get(ram,0x107dcc,2)==0xe100);
  Bytes in=start;inputs(in,0,0,0,0);
  const std::uint32_t walk[]={0x2abe,0x2ac0,0xc2ba,FRAME,0xa3d0,0xa3e2,0xa3f2,CLOSE,0xa67a,0x9e94,0x9eb0,0x9ee4,0xa67e,0xa694,0xc2c0,0xc2c8,
   0x8c16,0xc2d6,0xc2e0,0xc2f8,RETURN};
  splits(in,old,ram,s,o.ports,walk,sizeof(walk)/sizeof(walk[0]));
  // At c2d6: MOVEQ e1 to D0-D2 then the leaf; D3=14 is stored as 7e before the first decrement.
  Bytes r2=in;State t=old;Out a;assert(run(r2,t,0xc2d6,a,&p)&&(t.d[3]&65535U)==0x14&&s.d[3]==t.d[3]);
  a=Out();assert(run(r2,t,0xc2e0,a,&p)&&get(r2,CHILD+0x7e,2)==0x14&&get(r2,CHILD,4)==0xc2e0);}
 // 7e timer frames: 13 -> 1 return through c2f8.
 for(unsigned int k=1;k<0x13;++k){Out o;assert(frame(ram,s,RETURN,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x13U-k&&s.a[7]==SP+4&&s.a[0]==0xc2e0&&s.a[6]==CHILD);}
 last_ram=ram;last_state=s;
 // 7e 1 -> 0: parent c(A6)=OBJ gets 62=ff, JMP 2a00 removes the child (299c port 300001 = D0.B,
 // 2782, type 1 > NEXT type 0: 271c reset and unlink), A7 from 104ca4, BRA 2ac2.
 {const Bytes start=ram;State old=s;old.pc=0x2ab8;const std::uint32_t d0=s.d[0];Out o;
  {Bytes r=ram;State t=s;inputs(r,0,0,0,0);t.pc=0x2ab8;reject(r,t,STOP,"unsupported animation machine PC",&p);}
  assert(frame(ram,s,RETURN,o)&&s.pc==RETURN&&clean(o)&&o.ports.size()==1&&o.ports[0].address==0x300001&&o.ports[0].size==1&&o.ports[0].value==(d0&255U));
  assert(get(ram,OBJ+0x62,1)==0xff&&get(ram,CHILD,4)==0x270e&&get(ram,CHILD+0x7e,2)==0&&s.a[6]==OBJ&&s.a[7]==SP+4&&s.a[5]==0x108000);
  assert(get(ram,OBJ+8,4)==NEXT&&get(ram,NEXT+4,4)==OBJ&&get(ram,CHILD+8,4)==FREE&&get(ram,0x104c9c,4)==CHILD&&get(ram,0x104ca0,2)==2);
  assert(get(ram,CHILD+0xc,4)==OBJ&&get(ram,CHILD+0x6c,1)==0xff&&get(ram,CHILD+0x62,1)==0);
  Bytes in=start;inputs(in,0,0,0,0);
  const std::uint32_t walk[]={0x2abe,0x2ac0,0xc2e0,0xc2e8,REMOVE,0x299c,0x2a02,0x2a06,RETURN};
  splits(in,old,ram,s,o.ports,walk,sizeof(walk)/sizeof(walk[0]));}
 // Declared parent re-entry (PC=2ab8, A6=OBJ): 480ac 62=ff -> 480b6 JMP 2a00; type 0 -> 29ba 271c reset; 2ac2.
 {assert(s.a[6]==OBJ);const std::uint32_t d0=s.d[0];Out o;s.pc=0x2ab8;
  assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&clean(o)&&o.ports.size()==1&&o.ports[0].address==0x300001&&o.ports[0].value==(d0&255U));
  assert(get(ram,OBJ,4)==0x270e&&get(ram,OBJ+0x62,1)==0&&s.a[6]==OBJ&&s.a[7]==SP+4&&get(ram,OBJ+8,4)==NEXT&&get(ram,0x104ca0,2)==2);}
}
void close_edges(){
 const Physical p=resources();
 // Borrow (a2d0): 6=19 -> 640 > WORD 4(A2). 063f borrows (D0.W=063f, D1=0); 0640 does not (BCC); both 6 rows.
 const std::uint32_t words[]={0x063f,0x0640,0x0600};
 for(unsigned int i=0;i<3;++i){Bytes ram=snap_ram;State s=snap;put(ram,TOP+6,1,0x19);put(ram,TOP+4,2,words[i]);inputs(ram,0,0,0,0);s.pc=0x2ab8;
  if(i==1)reject(ram,s,0xa2d0,"unsupported animation machine PC",&p); // never reached: 2ac2 follows 8(A6)=NEXT, (NEXT)=5a5a5a5a
  Bytes r=ram;State t=s;Out o;
  if(i!=1){assert(run(r,t,0xa2d0,o,&p)&&(t.d[1]&65535U)==((words[i]-0x640U)&65535U));o=Out();}
  assert(run(r,t,RETURN,o,&p)&&clean(o)&&get(r,TOP+4,2)==0&&(t.d[1]&65535U)==6U);
  assert(same_ports(o.ports,closing(0,6)));}
 // Declared 6=6 (as many items as the opening height c): 180 per frame; byte 5 = 80 gives 2 rows.
 {Bytes ram=snap_ram;State s=snap;put(ram,TOP+6,1,6);const std::uint32_t heights[]={0x0480,0x0300,0x0180,0x0000};const unsigned int rows[]={2,1,2,1};
  shrink(ram,s,heights,rows,4,false);Out o;assert(frame(ram,s,RETURN,o)&&quiet(o)&&get(ram,F2,4)==0x107f0e&&get(ram,CHILD,4)==0xc2e0);}
 // 6=0: no shrink, 0 rows; the box is redrawn at the same height.
 {Bytes ram=snap_ram;State s=snap;put(ram,TOP+6,1,0);Out o;assert(frame(ram,s,RETURN,o)&&same_ports(o.ports,closing(6,0))&&get(ram,TOP+4,2)==0x0600);}
 // b=0: 9b58 still writes the corner tiles; the erase rows have no cells; the row counter is popped.
 {Bytes ram=snap_ram;State s=snap;put(ram,TOP+0xb,1,0);Out o;assert(frame(ram,s,RETURN,o)&&clean(o)&&s.a[7]==SP+4);
  Ports e;box(e,NONE,4,4,0,5,0x0b);assert(same_ports(o.ports,e)&&get(ram,TOP+4,2)==0x0500);}
 // Covered cells: a declared newer frame UP=-f2 (col 8 w 4, row 6 h 4, f=0) above TOP with f bit0:
 // a396 -> a3a8 BSR a2be shrinks TOP (palette 6b: A2 != -f2). Box tiles skip the write and the
 // ADDI.W; erase cells skip only the write (ADDI.L at a332 on both paths). Stop at the a3ac return.
 {Bytes ram=snap_ram;State s=snap;put(ram,F2,4,UP);put(ram,TOP+0xf,1,1);for(unsigned int i=0;i<16;++i)put(ram,UP+i,1,0);
  put(ram,UP+4,1,4);put(ram,UP+9,1,8);put(ram,UP+0xa,1,6);put(ram,UP+0xb,1,4);inputs(ram,0,0,0,0);s.pc=0x2ab8;
  Out o;assert(run(ram,s,0xa3ac,o,&p)&&clean(o)&&s.a[7]==SP-8&&get(ram,SP-8,4)==TOP&&s.a[2]==TOP);
  const Cover up={8,4,6,4};Ports e;box(e,up,4,4,0x11,5,0x6b);erase(e,up,4,4,5,0x11,1);
  assert(same_ports(o.ports,e)&&get(ram,TOP+4,2)==0x0500&&get(ram,EE,4)==TOP);
  unsigned int skipped=0;for(unsigned int i=0;i<o.ports.size();++i)if(covered(up,o.ports[i].value>>16))++skipped;
  assert(skipped==0&&e.size()<closing(5,1).size());}
 // Nested stack: a declared older frame TOP below the closing UP=-f2 (height 0): a67e -f2=107efe < 107f0e -> a698.
 // a698 now runs in the nested unit (its own test); only the stop at its entry is checked here.
 {Bytes ram=empty_ram;State s=empty_state;for(unsigned int i=0;i<16;++i)put(ram,UP+i,1,get(ram,TOP+i,1));put(ram,F2,4,UP);inputs(ram,0,0,0,0);s.pc=0x2ab8;
  Out o;assert(run(ram,s,NESTED,o,&p)&&quiet(o)&&get(ram,F2,4)==TOP&&get(ram,EE,4)==UP&&s.a[2]==TOP&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0&&get(ram,CHILD,4)==0xc2ba);}
 // Odd A2 from -f2=107eff with byte 5 nonzero: a662 MOVE.L/MOVE.B succeed, MOVE.W 4(A2) at a2be fails.
 {Bytes ram=snap_ram;State s=snap;put(ram,F2,4,0x107eff);put(ram,TOP+5,1,0x80);inputs(ram,0,0,0,0);s.pc=0x2ab8;reject(ram,s,RETURN,"even WORD/LONG",&p);}
}
void child_edges(){
 const Physical p=resources();
 // Parent pointer change, odd parent and zero parent at the 7e 1 -> 0 frame.
 {Bytes ram=last_ram;State s=last_state;put(ram,CHILD+0xc,4,NEXT);Out o;assert(frame(ram,s,RETURN,o)&&get(ram,NEXT+0x62,1)==0xff&&get(ram,OBJ+0x62,1)==0&&s.a[6]==OBJ);
  s.pc=0x2ab8;o=Out();assert(run(ram,s,RETURN,o,&p)&&quiet(o)&&get(ram,OBJ,4)==0x480ac);} // parent 62=0: 480b4 RTS
 {Bytes ram=last_ram;State s=last_state;put(ram,CHILD+0xc,4,OBJ+1);Out o;assert(frame(ram,s,RETURN,o)&&get(ram,OBJ+0x63,1)==0xff&&get(ram,OBJ+0x62,1)==0);}
 {Bytes ram=last_ram;State s=last_state;put(ram,CHILD+0xc,4,0);inputs(ram,0,0,0,0);s.pc=0x2ab8;reject(ram,s,RETURN,"unsupported animation machine write device",&p);}
}
// RAM fixture: -f2=-ee=TOP, frame h=0480, 6=6, 9=a=4, b=11, f=0; CHILD 7e=5, c=OBJ; STOP LONGs on the stack.
void generic(std::uint32_t pc,Bytes&ram,State&s){
 ram.assign(65536,0);for(unsigned int i=0;i<8;++i)put(ram,SP+4*i,4,STOP);put(ram,F2,4,TOP);put(ram,EE,4,TOP);
 put(ram,TOP,4,DESC);put(ram,TOP+4,2,0x0480);put(ram,TOP+6,1,6);put(ram,TOP+9,1,4);put(ram,TOP+0xa,1,4);put(ram,TOP+0xb,1,0x11);
 put(ram,CHILD+0x7e,2,5);put(ram,CHILD+0xc,4,OBJ);s=state(pc);s.a[2]=TOP;if(pc==0xa344)put(ram,SP+2,4,STOP);}
// Every block start {pc, next} from the generic fixture (a324 depends on the carry).
const std::uint32_t TABLE[][2]={
 {0x9e94,0x9eb0},{0x9eb0,0x9eb8},{0x9eb8,0x9ec2},{0x9ec2,0x9eca},{0x9eca,0x9ec2},{0x9eda,0x9eb0},{0x9ee4,STOP},
 {0xa2be,0xa2d6},{0xa2d0,0xa2d6},{0xa2d6,0x9b58},{0xa2ec,0xa306},{0xa306,0xa30e},{0xa30e,0xa318},{0xa318,0xa320},{0xa320,0xa018},
 {0xa324,0xa328},{0xa328,0xa332},{0xa332,0xa318},{0xa33c,0xa306},{0xa344,STOP},
 {0xa662,0xa672},{0xa672,0xa2be},{0xa676,STOP},{0xa67a,0x9e94},{0xa67e,0xa694},{0xa694,STOP},
 {0xc2c8,0x8c16},{0xc2d6,0xc2e0},{0xc2e0,0xc2f8},{0xc2e8,REMOVE},{0xc2f8,STOP}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
// Blocks made only of JSR/BSR/RTS, BCS and ADDQ.W #2,A7 (capstone classification of the original opcodes).
// a344 (ADDQ.W #2,A7; RTS) keeps C on a 68000, but stays Unknown to match the source classifier (ADDQ is not FLOW_ONLY).
const std::uint32_t KEEP[]={0x9ee4,0xa320,0xa324,0xa672,0xa67a,0xc2f8};
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
void fixtures(){
 // 9e94 with 4(A2)=2, b=3: per row SWAP, WORD ff, b LONG writes with ADDI.L #200000; D3/D0 next row.
 {Bytes ram;State s;generic(0x9e94,ram,s);put(ram,TOP+4,1,2);put(ram,TOP+0xb,1,3);s.d[0]=0x12345678;Out o;
  assert(run(ram,s,STOP,o)&&clean(o)&&s.a[2]==TOP&&s.a[7]==SP+4&&(s.d[7]&255U)==0&&(s.d[6]&255U)==0&&(s.d[3]&65535U)==0x7086);
  Ports e;for(unsigned int r=0;r<2;++r)for(unsigned int i=0;i<3;++i)port(e,4,((0x7084U+r+0x20U*i)<<16)|0xffU);
  assert(same_ports(o.ports,e)&&s.d[0]==0x00ff7086U);} // last row: SWAP back, D0.W=D3=7086
 // 9e94 reads A2 from LONG 107f12 (absolute), not from A5: a different -ee(A5) is ignored.
 {Bytes ram;State s;generic(0x9e94,ram,s);s.a[5]=0x109000;put(ram,TOP+4,1,0);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&s.a[2]==TOP);}
 // ADDI.L #200000 is 32-bit: a high WORD ffe0 carries out of bit 31.
 {Bytes ram;State s;generic(0x9eca,ram,s);s.d[0]=0xffe000ffU;s.d[6]=1;Out o;assert(run(ram,s,0x9ec2,o)&&s.d[0]==0x000000ffU&&o.ports.size()==1&&o.ports[0].value==0xffe000ffU);}
 // ADDI.L #20,D0 is 32-bit: low WORD ffe0 carries into the high WORD.
 {Bytes ram;State s;generic(0xa332,ram,s);s.d[0]=0x00ffffe0U;s.d[7]=0x11223301U;Out o;assert(run(ram,s,0xa318,o)&&s.d[0]==0x01000000U&&s.d[7]==0x11223300U);}
 // a2be: WORD 4(A2) includes byte 5; D0 upper bits cleared by MOVEQ; D1 high WORD kept.
 {Bytes ram;State s;generic(0xa2be,ram,s);put(ram,TOP+4,2,0x0481);s.d[1]=0x55550000;Out o;assert(run(ram,s,0xa2d6,o)&&s.d[0]==0x180&&s.d[1]==0x55550301U);
  o=Out();assert(run(ram,s,0x9b58,o)&&get(ram,TOP+4,2)==0x0301&&s.d[1]==0x55550001U&&get(ram,SP-2,2)==1&&get(ram,SP-6,4)==0xa2ec&&s.a[1]==0xa008);}
 // a2d6 LSR.W #8 of a WORD sum above ffff: (ff + ff80) WORD = 007f -> 0 rows.
 {Bytes ram;State s;generic(0xa2d6,ram,s);s.d[1]=0x000000ffU;s.d[0]=0xff80;Out o;assert(run(ram,s,0x9b58,o)&&(s.d[1]&65535U)==0&&get(ram,TOP+4,2)==0xff);}
 // a2ec: CLR.W after SWAP keeps ff in the high WORD; ADD.B a and 4 are BYTE adds (no carry to bit 8).
 {Bytes ram;State s;generic(0xa2ec,ram,s);put(ram,TOP+9,1,7);put(ram,TOP+0xa,1,0xf0);put(ram,TOP+4,1,0x20);s.d[0]=0x12345678;Out o;
  assert(run(ram,s,0xa306,o)&&s.d[0]==0x00ff70f0U);} // 7<<5=e0, +f0 -> d0, +7000, +20 -> f0
 // a33c: WORD pop, ADDQ.W, WORD RMW of the counter (0 -> ffff wraps).
 {Bytes ram;State s;generic(0xa33c,ram,s);put(ram,SP,2,0x7fff);put(ram,SP+2,2,0);s.d[0]=0xabcd0000U;Out o;assert(run(ram,s,0xa306,o)&&s.d[0]==0xabcd8000U&&get(ram,SP+2,2)==0xffff&&s.a[7]==SP+2);}
 // a344: ADDQ.W #2,A7 on the whole register, then RTS.
 {Bytes ram;State s;generic(0xa344,ram,s);Out o;assert(run(ram,s,STOP,o)&&s.a[7]==SP+6);}
 // a67e: LONG read-modify-write of -f2 (carry across WORDs), unsigned compare at 107f0e.
 const std::uint32_t f2[][3]={{0x107efe,0x107f0e,0xa694},{0x107efd,0x107f0d,NESTED},{0x0000fff8,0x00010008,NESTED},{0xfffffff8U,0x00000008,NESTED},{0x107f00,0x107f10,0xa694}};
 for(unsigned int i=0;i<5;++i){Bytes ram;State s;generic(0xa67e,ram,s);put(ram,F2,4,f2[i][0]);Out o;assert(run(ram,s,f2[i][2],o)&&get(ram,F2,4)==f2[i][1]&&s.a[2]==f2[i][1]);}
 // a662 with 4(A2)=0 (WORD 00xx): BLS -> a67a; -ee written first.
 {Bytes ram;State s;generic(CLOSE,ram,s);put(ram,TOP+4,2,0x00ff);put(ram,EE,4,0);Out o;assert(run(ram,s,0xa67a,o)&&get(ram,EE,4)==TOP&&(s.d[7]&255U)==0);}
 // c2c8: MOVEQ e1 sign-extends to 32 bits; MOVEQ 14 clears D3's high WORD.
 {Bytes ram;State s;generic(0xc2c8,ram,s);Out o;assert(run(ram,s,0x8c16,o)&&s.d[0]==0xffffffe1U&&s.d[1]==0xffffffe1U&&s.d[2]==0xffffffe1U&&s.d[3]==0x14&&get(ram,SP-4,4)==0xc2d6);}
 // c2d6 stores D3.W (high WORD ignored) then falls into c2e0.
 {Bytes ram;State s;generic(0xc2d6,ram,s);s.d[3]=0xabcd0003U;Out o;assert(run(ram,s,STOP,o)&&get(ram,CHILD+0x7e,2)==2&&get(ram,CHILD,4)==0xc2e0&&s.a[7]==SP+4);}
 // 7e entry 1 -> c2e8 -> 62(parent)=ff -> 2a00; 0 -> ffff RTS; 8000 -> 7fff RTS.
 {Bytes ram;State s;generic(0xc2e0,ram,s);put(ram,CHILD+0x7e,2,1);Out o;assert(run(ram,s,REMOVE,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0&&get(ram,OBJ+0x62,1)==0xff&&s.a[0]==OBJ&&s.a[7]==SP);}
 {Bytes ram;State s;generic(0xc2e0,ram,s);put(ram,CHILD+0x7e,2,0);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0xffff&&s.a[7]==SP+4);}
 {Bytes ram;State s;generic(0xc2e0,ram,s);put(ram,CHILD+0x7e,2,0x8000);Out o;assert(run(ram,s,STOP,o)&&get(ram,CHILD+0x7e,2)==0x7fff);}
 // Odd parent: BYTE write at an odd address is legal.
 {Bytes ram;State s;generic(0xc2e8,ram,s);put(ram,CHILD+0xc,4,OBJ+1);Out o;assert(run(ram,s,REMOVE,o)&&get(ram,OBJ+0x63,1)==0xff&&s.a[0]==OBJ+1);}
 // a324 consumes the modeled a018 carry.
 for(unsigned int carry=1;carry<3;++carry){Bytes ram;State s;generic(0xa324,ram,s);s.carry=carry_of(carry);Out o;
  const std::uint32_t next=carry_of(carry)==ms5::AnimationCarryClear?0xa328:0xa332;assert(run(ram,s,next,o)&&s.carry==carry_of(carry));}
 // a320 -> a018 -> a324: the cover result reaches the consumer (uncovered: one LONG at a328).
 {Bytes ram;State s;generic(0xa320,ram,s);s.d[0]=0x00ff7084U;s.carry=ms5::AnimationCarryUnknown;Out o;assert(run(ram,s,0xa332,o)&&o.ports.size()==1&&o.ports[0].value==0x708400ffU&&s.d[0]==0x00ff7084U);}
}
void errors(){
 // Unknown carry at a324.
 {Bytes ram;State s;generic(0xa324,ram,s);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"card menu caller requires known carry");}
 // Odd A2 at a662 (byte 5 nonzero): the -ee LONG write is rolled back with the WORD read failure.
 {Bytes ram;State s;generic(CLOSE,ram,s);s.a[2]=TOP+1;put(ram,TOP+5,1,6);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A2 at a2d6: the WORD write fails.
 {Bytes ram;State s;generic(0xa2d6,ram,s);s.a[2]=TOP+1;reject(ram,s,STOP,"alignment");}
 // Odd A7: CMPI.W (A7) at a306; WORD push at a2d6.
 {Bytes ram;State s;generic(0xa306,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xa2d6,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A6: WORD read at c2e0, WORD write at c2d6; LONG read c(A6) at c2e8.
 {Bytes ram;State s;generic(0xc2e0,ram,s);s.a[6]=CHILD+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;State s;generic(0xc2d6,ram,s);s.a[6]=CHILD+1;reject(ram,s,STOP,"alignment");}
 {Bytes ram;State s;generic(0xc2e8,ram,s);s.a[6]=CHILD+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Zero parent: MOVE.B #ff,62(A0) targets the vector/ROM area.
 {Bytes ram;State s;generic(0xc2e8,ram,s);put(ram,CHILD+0xc,4,0);reject(ram,s,STOP,"unsupported animation machine write device");}
 // Odd -f2 base for ADDI.L at a67e (A5 odd).
 {Bytes ram;State s;generic(0xa67e,ram,s);s.a[5]=0x108001;reject(ram,s,STOP,"even WORD/LONG");}
 // Interior and bundled PCs inside the routed ranges (CMPI/BLS a66a, SUB/BCC a2ca, CMPI/BEQ a306/a318,
 // CMPA/BCS a68a, SUBQ/BNE c2e0, the 9e94 loop branches and every instruction operand).
 const std::uint32_t ranges[][2]={{0x9e94,0x9ee4},{0xa2be,0xa346},{0xa662,0xa696},{0xc2c8,0xc2f8}};
 unsigned int interior=0;
 for(unsigned int i=0;i<4;++i)for(std::uint32_t pc=ranges[i][0];pc<=ranges[i][1];pc+=2){
  if(listed(pc))continue;Bytes ram;State s;generic(pc,ram,s);reject(ram,s,STOP,"unsupported animation card menu close PC");++interior;}
 assert(interior==131); // 162 even PCs in the four ranges minus 31 block starts
 const std::uint32_t bundled[]={0xa66a,0xa66e,0xa2ca,0xa2cc,0xa30a,0xa31c,0xa68a,0xa690,0xc2e4,0x9eb4,0x9ec6,0x9ed6,0x9ee0,0xa338,0xa340,0xa346,0xa696};
 for(unsigned int i=0;i<sizeof(bundled)/sizeof(bundled[0]);++i){assert(!listed(bundled[i]));Bytes ram;State s;generic(bundled[i],ram,s);reject(ram,s,STOP,"unsupported animation card menu close PC");}
 // Neighbours outside the routed ranges and boundaries still without an executor
 // (a698..a708 now run in the nested unit).
 // 5f084 replaces e84d6 (now the objects U03 glyph writer).
 const std::uint32_t outside[]={0x9ee6,0xa63c,0x5f084,0xc2fa};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram;State s;generic(outside[i],ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;State s;generic(0xa663,ram,s);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int carry=0;carry<3;++carry)for(unsigned int i=0;i<ROWS+1;++i){
  const std::uint32_t pc=i<ROWS?TABLE[i][0]:NESTED;Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);
  const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,pc,o)&&same(s,old)&&ram==before&&quiet(o));}
}
void carry(){
 assert(ROWS==31);unsigned int keeps=0;
 for(unsigned int i=0;i<ROWS;++i){
  const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,sizeof(KEEP)/sizeof(KEEP[0]),pc);if(keep)++keeps;
  for(unsigned int carry=0;carry<3;++carry){
   if(pc==0xa324&&carry_of(carry)!=ms5::AnimationCarrySet&&carry_of(carry)!=ms5::AnimationCarryClear)continue; // Unknown: errors()
   Bytes ram;State s;generic(pc,ram,s);s.carry=carry_of(carry);Out o;
   const std::uint32_t next=pc==0xa324&&carry_of(carry)==ms5::AnimationCarrySet?0xa332:TABLE[i][1];
   if(!(run(ram,s,next,o)&&s.pc==next&&clean(o)))std::cerr<<std::hex<<"row "<<pc<<"\n";
   assert(s.pc==next&&clean(o)&&s.carry==(keep?carry_of(carry):ms5::AnimationCarryUnknown));}}
 assert(keeps==6);
}
}
int main(){to_close();natural();close_edges();child_edges();fixtures();errors();zero_step();carry();
std::cout<<"animation_machine_card_menu_close_test PASS "<<calls<<" API invocations\n";}
