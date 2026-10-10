#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef std::vector<ms5::VideoPortWrite> Ports;
const std::uint32_t SP=0x1feffc,STOP=0xff000,CHILD=0x103000,TOP=0x107efe,UP=0x107eee,FRAME=0xa370,RETURN=0x2ac2;
const std::uint32_t DESC=0x104100,DESC2=0x104200,TEXT=0x104800,TEXT2=0x104840,OLD_EE=0x10a0b0c0;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void text(Bytes&b,std::uint32_t a,const char*t,std::uint32_t mask){unsigned int i=0;for(;t[i];++i)b[(a+i)&mask]=static_cast<std::uint8_t>(t[i]);b[(a+i)&mask]=0;}
void hex(Bytes&b,std::uint32_t a,const char*h){for(unsigned int i=0;h[2*i];++i){unsigned int v=0;for(unsigned int k=0;k<2;++k){const char x=h[2*i+k];v=v*16U+static_cast<unsigned int>(x<='9'?x-'0':x-'a'+10);}b[a+i]=static_cast<std::uint8_t>(v);}}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=CHILD;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x200000;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const Physical*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
// Successful run: no external reads, returned status, PVC untouched (3c0000 events are ports only).
bool clean(const Out&o){return o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.error.empty()&&o.dev.pvc==Out().dev.pvc&&o.dev.bank_base==0x200000;}
bool quiet(const Out&o){return clean(o)&&o.ports.empty();}
// Failure preserves RAM, registers, device and every output.
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message,const Physical*physical=NULL){
 const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;if(run(ram,s,stop,o,physical)){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
 if(o.error.find(message)==std::string::npos)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);}
ms5::AnimationCarryState carry_of(unsigned int i){return static_cast<ms5::AnimationCarryState>(i);}
bool same_ports(const Ports&a,const Ports&b){if(a.size()!=b.size())return false;for(unsigned int i=0;i<a.size();++i)if(a[i].address!=b[i].address||a[i].size!=b[i].size||a[i].value!=b[i].value){std::cerr<<std::hex<<"port "<<i<<" "<<a[i].value<<" vs "<<b[i].value<<"\n";return false;}return true;}
// Expected video events. cell: LSL.W #5 of x, ADD.B y (BYTE only), ADDI.W #7000.
std::uint32_t cell(std::uint32_t x,std::uint32_t y){return ((((x<<5)&0xff00U)|(((x<<5)+y)&0xffU))+0x7000U)&65535U;}
void port(Ports&v,unsigned int size,std::uint32_t value){ms5::VideoPortWrite p;p.address=0x3c0000;p.size=static_cast<std::uint8_t>(size);p.value=value;v.push_back(p);}
void tile_row(Ports&v,std::uint32_t a,std::uint32_t pal,std::uint32_t first,std::uint32_t mid,std::uint32_t last,unsigned int n){
 port(v,4,(a<<16)|(pal<<8)|first);for(unsigned int i=1;i<=n;++i)port(v,4,(((a+0x20U*i)&65535U)<<16)|(pal<<8)|mid);
 port(v,4,(((a+0x20U*(n+1))&65535U)<<16)|(pal<<8)|last);}
// Uncovered 9b58 box: top f4 f0.. f5, (h-2) rows f2 60.. f3, bottom f6 f1.. f7 (D6/D7 loops while BYTE > 2).
void box(Ports&v,std::uint32_t x,std::uint32_t y,unsigned int w,unsigned int h,std::uint32_t pal){
 const unsigned int n=w>2?w-2:0;std::uint32_t a=cell(x,y);tile_row(v,a,pal,0xf4,0xf0,0xf5,n);
 for(unsigned int r=h;r>2;--r){a=(a+1U)&65535U;tile_row(v,a,pal,0xf2,0x60,0xf3,n);}
 a=(a+1U)&65535U;tile_row(v,a,pal,0xf6,0xf1,0xf7,n);}
// 3650 per character: LONG addr|(D1 nibble-shifted)|char, then WORD 8200.
std::uint32_t text_ports(Ports&v,std::uint32_t a,std::uint32_t d1,const char*t){
 std::uint32_t w=d1&65535U;w=(w&0xff00U)|((w<<4)&0xffU);w=(w<<4)&65535U;
 for(unsigned int i=0;t[i];++i){port(v,4,(a<<16)|(w&0xff00U)|static_cast<unsigned char>(t[i]));port(v,2,0x8200);a=(a+0x20U)&65535U;}return a;}
void cursor(Ports&v,std::uint32_t a,bool selected){port(v,4,(a<<16)|(selected?0x313U:0xffU));port(v,4,(((a+0x20U)&65535U)<<16)|(selected?0x314U:0xffU));}
// Separator: SUBQ.W #2 borrow skips; bf8, then SUBQ.B, bf9 while BYTE >= 2 (SUBQ.W), bfa at BYTE 1.
void separator(Ports&v,std::uint32_t a,std::uint32_t b){
 if(b<2)return;port(v,4,(a<<16)|0xbf8U);std::uint32_t d7=(b-3U)&255U;a=(a+0x20U)&65535U;
 while(d7>=2){port(v,4,(a<<16)|0xbf9U);a=(a+0x20U)&65535U;d7=(d7-1U)&65535U;}
 if(d7==1)port(v,4,(a<<16)|0xbfaU);}
// 9d4c row address: cell(x,y)+20 then ADD.B row (1+index).
std::uint32_t item_row(std::uint32_t x,std::uint32_t y,std::uint32_t index){const std::uint32_t a=(cell(x,y)+0x20U)&65535U;return (a&0xff00U)|((a+1U+index)&0xffU);}
// Synthetic typed physical bytes (not a native ROM oracle): the c188 descriptor and its strings.
Physical resources(){
 Physical p(1);p[0].source_rom_offset=0;p[0].data.assign(0x100000,0);Bytes&f=p[0].data;
 hex(f,0xc188,"0000000000000000bf2c0000000000000000be60000000000000fffffffe0000000000000000be9a0000c1c400000000bea00000bf940000ffffffff");
 text(f,0xbe60,"DATA SAVE ?  ",0xfffff);text(f,0xbe9a," YES ",0xfffff);text(f,0xbea0," NO ",0xfffff);return p;
}
// Card child a29c stop output (push unit entry): A7 holds c2a8 above 2ac2; residual 5(A2)=88;
// sound gates 100012/104d7e/10f001 clear and an empty 104d82 WORD ring.
ms5::AnimationMachineState menu_state(){ms5::AnimationMachineState s=state(0xa29c);s.a[0]=0xc188;s.d[0]=0xabcd0004U;s.d[1]=0xabce0004U;s.a[7]=SP-4;return s;}
Bytes menu_ram(){Bytes ram(65536,0x5a);put(ram,SP,4,RETURN);put(ram,SP-4,4,0xc2a8);put(ram,0x107f12,4,OLD_EE);put(ram,TOP+5,1,0x88);
 put(ram,0x100012,1,0);put(ram,0x104d7e,1,0);put(ram,0x10f001,1,0);put(ram,0x104d8a,2,0);put(ram,0x104d8c,2,0);return ram;}
// Menu frame record: (A2)=desc, 4=height, 6=items, 7/8=cursor, 9/a=x/y, b=width, c=final height, d=3, e=ff, f=0.
void frame(Bytes&ram,std::uint32_t at,std::uint32_t desc,std::uint32_t h,std::uint32_t items,std::uint32_t cur,std::uint32_t x,std::uint32_t y,std::uint32_t w,std::uint32_t c){
 put(ram,at,4,desc);put(ram,at+4,1,h);put(ram,at+5,1,0);put(ram,at+6,1,items);put(ram,at+7,1,cur);put(ram,at+8,1,cur);
 put(ram,at+9,1,x);put(ram,at+0xa,1,y);put(ram,at+0xb,1,w);put(ram,at+0xc,1,c);put(ram,at+0xd,1,3);put(ram,at+0xe,1,0xff);put(ram,at+0xf,1,0);}
// Descriptor: title LONG, hook LONG at a, flags WORD at e, 10-byte items {text, callback, WORD 0}, ffffffff end.
void desc(Bytes&ram,std::uint32_t at,std::uint32_t title,std::uint32_t hook,std::uint32_t flags,const std::uint32_t*items,const std::uint32_t*cb,unsigned int n){
 put(ram,at,4,title);put(ram,at+0xa,4,hook);put(ram,at+0xe,2,flags);
 for(unsigned int i=0;i<n;++i){put(ram,at+0x10+10*i,4,items[i]);put(ram,at+0x14+10*i,4,cb[i]);put(ram,at+0x18+10*i,2,0);}
 put(ram,at+0x10+10*n,4,0xffffffffU);}
// Generic one-menu fixture: -f2=-ee=107efe, -ea=e84c8, -e5=1; frame h=2, 2 items "AB" (no callback) and "AB" (bf94).
void generic(std::uint32_t pc,Bytes&ram,ms5::AnimationMachineState&s){
 ram.assign(65536,0);for(unsigned int i=0;i<8;++i)put(ram,SP+4*i,4,STOP);
 put(ram,0x107f0e,4,TOP);put(ram,0x107f12,4,TOP);put(ram,0x107f16,4,0xe84c8);put(ram,0x107f1b,1,1);
 frame(ram,TOP,DESC,2,2,0,4,4,5,6);const std::uint32_t items[]={TEXT,TEXT},cb[]={0,0xbf94};desc(ram,DESC,TEXT,0,0,items,cb,2);text(ram,TEXT,"AB",65535);
 s=state(pc);s.a[0]=TEXT;s.a[1]=0xa008;s.a[2]=TOP;s.a[3]=DESC+0x10;s.a[4]=0xa6da;s.d[0]=0x00ff7084;s.d[1]=0x0003;s.d[2]=0x41;s.d[3]=0x7084;}
// Every block start {pc, next with C clear, next with C set} from the generic fixture.
const std::uint32_t TABLE[][3]={
 {0x3650,0xff000,0xff000},{0x3918,0x391a,0x391a},{0x391a,0x386e,0x386e},{0x391e,0x3928,0x3928},
 {0x3926,0xff000,0xff000},{0x3928,0xa008,0xa008},{0x392a,0x391a,0x391a},{0x9b26,0xff000,0xff000},
 {0x9b3e,0x9b26,0x9b26},{0x9b42,0x9b56,0x9b56},{0x9b54,0x104800,0x104800},{0x9b56,0xff000,0xff000},
 {0x9b58,0x9b66,0x9b66},{0x9b64,0xff000,0xff000},{0x9b66,0x9b7a,0x9b7a},{0x9b78,0xff000,0xff000},
 {0x9b7a,0x9b82,0x9b82},{0x9b82,0x9b8e,0x9b8e},{0x9b8a,0x9b8e,0x9b8e},{0x9b8e,0xa018,0xa018},{0x9ba6,0x9baa,0x9bbc},
 {0x9baa,0x9bbc,0x9bbc},{0x9bbc,0x9bc0,0x9bc0},{0x9bc0,0x9bc8,0x9bc8},{0x9bc8,0xa018,0xa018},{0x9bcc,0x9bd0,0x9be2},
 {0x9bd0,0x9be2,0x9be2},{0x9be2,0x9bc0,0x9bc0},{0x9be6,0xa018,0xa018},{0x9bea,0x9bee,0x9c00},{0x9bee,0x9c00,0x9c00},
 {0x9c00,0x9c08,0x9c08},{0x9c08,0xa018,0xa018},{0x9c10,0x9c14,0x9c26},{0x9c14,0x9c26,0x9c26},{0x9c26,0x9c2a,0x9c2a},
 {0x9c2a,0x9c32,0x9c32},{0x9c32,0xa018,0xa018},{0x9c36,0x9c3a,0x9c4c},{0x9c3a,0x9c4c,0x9c4c},{0x9c4c,0x9c2a,0x9c2a},
 {0x9c50,0xa018,0xa018},{0x9c54,0x9c58,0x9c6a},{0x9c58,0x9c6a,0x9c6a},{0x9c6a,0x9c00,0x9c00},{0x9c6e,0xa018,0xa018},
 {0x9c76,0x9c7a,0x9c8c},{0x9c7a,0x9c8c,0x9c8c},{0x9c8c,0x9c90,0x9c90},{0x9c90,0x9c98,0x9c98},{0x9c98,0xa018,0xa018},
 {0x9c9c,0x9ca0,0x9cb2},{0x9ca0,0x9cb2,0x9cb2},{0x9cb2,0x9c90,0x9c90},{0x9cb6,0xa018,0xa018},{0x9cba,0x9cbe,0x9cd0},
 {0x9cbe,0x9cd0,0x9cd0},{0x9cd0,0xff000,0xff000},{0x9cd4,0xa018,0xa018},{0x9cd8,0x9cdc,0x9cee},{0x9cdc,0x9cee,0x9cee},
 {0x9cee,0x9cf0,0x9cf0},{0x9cf0,0x9cf8,0x9cf8},{0x9cf8,0xa018,0xa018},{0x9cfc,0x9d00,0x9d12},{0x9d00,0x9d12,0x9d12},
 {0x9d12,0x9cf0,0x9cf0},{0x9d16,0x9d38,0x9d38},{0x9d1e,0xa018,0xa018},{0x9d22,0x9d26,0x9d38},{0x9d26,0x9d38,0x9d38},
 {0x9d38,0xff000,0xff000},{0x9d3a,0x9d4c,0x9d4c},{0x9d4a,0xff000,0xff000},{0x9d4c,0x9d9a,0x9d9a},
 {0x9d86,0x9d92,0x9d92},{0x9d92,0x9cd4,0x9cd4},{0x9d96,0x9e08,0x9e08},{0x9d9a,0x9df6,0x9df6},{0x9da0,0x9db6,0x9db6},
 {0x9dae,0x9dba,0x9dba},{0x9db6,0x9dba,0x9dba},{0x9dba,0xa018,0xa018},{0x9dc0,0x9dc4,0x9dce},{0x9dc4,0x9dce,0x9dce},
 {0x9dce,0xa018,0xa018},{0x9dd6,0x9dda,0x9df2},{0x9dda,0x9de8,0x9de8},{0x9de8,0x9dea,0x9dea},{0x9dea,0x9df2,0x9df2},
 {0x9df2,0x9df6,0x9df6},{0x9df6,0x9dfe,0x9dfe},{0x9dfe,0x9f7c,0x9f7c},{0x9e02,0x3918,0x3918},{0x9e08,0x9b3e,0x9b3e},
 {0x9e14,0xff000,0xff000},{0x9e1a,0x9e28,0x9e28},{0x9e26,0xff000,0xff000},{0x9e28,0x9e34,0x9e34},
 {0x9e34,0x38e8,0x38e8},{0x9e3a,0x9e5e,0x9e5e},{0x9e5e,0x9e66,0x9e66},{0x9e66,0x9e72,0x9e72},{0x9e6e,0x9e72,0x9e72},
 {0x9e72,0x3918,0x3918},{0x9e78,0x9e7a,0x9e7a},{0x9e7a,0x9e92,0x9e92},{0x9e82,0x9d3a,0x9d3a},{0x9e8a,0x9e7a,0x9e7a},
 {0x9e92,0xff000,0xff000},{0x9f7c,0x9f96,0x9f96},{0x9f84,0x9f96,0x9f96},{0x9f90,0xff000,0xff000},
 {0x9f96,0x9fbe,0x9fbe},{0x9fac,0x9fbe,0x9fbe},{0x9fb8,0xff000,0xff000},{0x9fbe,0xff000,0xff000},
 {0xa008,0xa018,0xa018},{0xa00c,0xa010,0xa016},{0xa010,0xe84c8,0xe84c8},{0xa016,0xff000,0xff000},
 {0xa018,0xa03a,0xa03a},{0xa03a,0xa040,0xa040},{0xa040,0xa04a,0xa04a},{0xa04a,0xa066,0xa066},{0xa058,0xa066,0xa066},
 {0xa066,0xa03a,0xa03a},{0xa06c,0xff000,0xff000},{0xa076,0xff000,0xff000},{0xa216,0xa21e,0xa21e},
 {0xa21e,0xa22c,0xa22c},{0xa22c,0xa236,0xa236},{0xa236,0xa238,0xa238},{0xa238,0xa246,0xa246},{0xa23c,0xa246,0xa246},
 {0xa242,0xa246,0xa246},{0xa246,0x9b26,0x9b26},{0xa252,0xa21e,0xa21e},{0xa258,0xa262,0xa262},{0xa262,0x9d3a,0x9d3a},
 {0xa26e,0x9d3a,0x9d3a},{0xa278,0xff000,0xff000},{0xa348,0x9b58,0x9b58},{0xa350,0xa36e,0xa36e},{0xa36a,0xa36e,0xa36e},
 {0xa36e,0xff000,0xff000},{0xa370,0xa380,0xa380},{0xa380,0xa388,0xa388},{0xa388,0xa3b8,0xa3b8},{0xa396,0xa3b8,0xa3b8},
 {0xa3a0,0xa3a8,0xa3a8},{0xa3a8,0xa2be,0xa2be},{0xa3ac,0xa3b8,0xa3b8},{0xa3b4,0xa6da,0xa6da},{0xa3b8,0xa3c8,0xa3c8},
 {0xa3c6,0xa6da,0xa6da},{0xa3c8,0xa380,0xa380},{0xa3d0,0xa3e2,0xa3e2},{0xa3de,0xff000,0xff000},{0xa3e2,0xa5d2,0xa5d2},
 {0xa3f2,0xa3fa,0xa3fa},{0xa3fa,0xa402,0xa402},{0xa402,0xff000,0xff000},{0xa5d2,0xa5e2,0xa5e2},{0xa5e2,0xa348,0xa348},
 {0xa5e6,0xff000,0xff000},{0xa5ea,0xa5f4,0xa5f4},{0xa5f4,0x9b26,0x9b26},{0xa5fe,0xa606,0xa606},{0xa606,0xa616,0xa616},
 {0xa614,0xa616,0xa616},{0xa616,0xa5f4,0xa5f4},{0xa61c,0x9b58,0x9b58},{0xa624,0x9e1a,0x9e1a},{0xa628,0xa63e,0xa63e},
 {0xa63e,0x9b3e,0x9b3e},{0xa64c,0x9b3e,0x9b3e},{0xa65e,0xff000,0xff000},{0xa73e,0xa754,0xa754},{0xa74a,0x3af8,0x3af8},
 {0xa754,0xff000,0xff000},{0xbf94,0xa73e,0xa73e},{0xbf9a,0xbfa8,0xbfa8},{0xbfa2,0xbfa8,0xbfa8},{0xbfa8,0xbfbc,0xbfbc},
 {0xbfb0,0xa70a,0xa70a},{0xbfbc,0xff000,0xff000},{0xc1c4,0xa73e,0xa73e},{0xc1ca,0xc1de,0xc1de},{0xc1d2,0xa216,0xa216},
 {0xc1de,0xc212,0xc212},{0xc1e6,0xbd26,0xbd26},{0xc1ee,0x9f36,0x9f36},{0xc1f4,0xa71a,0xa71a},{0xc1fe,0xc212,0xc212},
 {0xc202,0x9f36,0x9f36},{0xc208,0xa71a,0xa71a},{0xc212,0xff000,0xff000},{0xe84c8,0xe84d0,0xe84d0},
 {0xe84d0,0x3650,0x3650},{0xc2c0,0xc2c8,0xc2c8},{0xc2c6,0xff000,0xff000}};
const unsigned int ROWS=sizeof(TABLE)/sizeof(TABLE[0]);
// a406 and a70a now run in the card menu input unit, 9e94/a2be/a662/c2c8 in the close unit (their own tests).
const std::uint32_t BOUNDARY[]={0x9f36,0xa6da,0xa71a,0xbd26,0xe84d6,0xa63c};
const unsigned int BOUNDARIES=sizeof(BOUNDARY)/sizeof(BOUNDARY[0]);
// Blocks made only of LEA/MOVEA/MOVEM/BTST/BSR/JSR/JMP/BRA/RTS/conditional branches (capstone classification).
const std::uint32_t KEEP[]={0x391a,0x3926,0x3928,0x392a,0x9b54,0x9b56,0x9b64,0x9b78,0x9ba6,0x9bc8,0x9bcc,0x9be6,0x9bea,0x9c10,
 0x9c32,0x9c36,0x9c50,0x9c54,0x9c76,0x9c98,0x9c9c,0x9cb6,0x9cba,0x9cd4,0x9cd8,0x9cf8,0x9cfc,0x9d1e,0x9d22,0x9d38,0x9d4a,0x9d92,
 0x9d96,0x9dc0,0x9dd6,0x9dfe,0x9e02,0x9e14,0x9e26,0x9e34,0x9e72,0x9e92,0xa008,0xa00c,0xa016,0xa040,0xa238,0xa348,0xa36e,0xa396,
 0xa3a8,0xa3b4,0xa3c6,0xa5e2,0xa61c,0xa624,0xbf94,0xbfbc,0xc1c4,0xc1e6,0xc1ee,0xc1f4,0xc1fe,0xc202,0xc208,0xc212,0xc2c6,0xe84d0};
// a018 caller BCS return PCs (contract item 7 and a00c).
const std::uint32_t BCS[]={0x9ba6,0x9bcc,0x9bea,0x9c10,0x9c36,0x9c54,0x9c76,0x9c9c,0x9cba,0x9cd8,0x9cfc,0x9d22,0x9dc0,0x9dd6,0xa00c};
bool member(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool listed(std::uint32_t pc){for(unsigned int i=0;i<ROWS;++i)if(TABLE[i][0]==pc)return true;return false;}
void append(Ports&all,const Ports&part){for(unsigned int i=0;i<part.size();++i)all.push_back(part[i]);}
// Full-frame expectation: 6-row box, 4 item rows, then a216 redraws rows 2 (unselected) and 3 (selected).
Ports full_frame(){
 Ports e;box(e,4,4,0x11,6,0x0b);
 cursor(e,item_row(4,4,0),false);text_ports(e,(item_row(4,4,0)+0x40U)&65535U,3,"DATA SAVE ?  ");
 separator(e,item_row(4,4,1),0x11);
 cursor(e,item_row(4,4,2),true);text_ports(e,(item_row(4,4,2)+0x40U)&65535U,3," YES ");
 cursor(e,item_row(4,4,3),false);text_ports(e,(item_row(4,4,3)+0x40U)&65535U,3," NO ");
 cursor(e,item_row(4,4,2),false);text_ports(e,(item_row(4,4,2)+0x40U)&65535U,3," YES ");
 cursor(e,item_row(4,4,3),true);text_ports(e,(item_row(4,4,3)+0x40U)&65535U,3," NO ");
 return e;
}
void natural(){
 const Physical p=resources();Bytes ram=menu_ram();ms5::AnimationMachineState s=menu_state();Out o;
 // Push unit a29c -> a370 stop (same frame, c2ba JSR left c2c0 above 2ac2).
 assert(run(ram,s,FRAME,o,&p)&&s.pc==FRAME&&quiet(o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==0xc2c0&&get(ram,SP,4)==RETURN);
 assert(get(ram,TOP,4)==0xc188&&get(ram,TOP+4,2)==0x0088&&get(ram,TOP+6,1)==4&&get(ram,TOP+0xb,1)==0x11&&get(ram,TOP+0xc,1)==6&&get(ram,0x107f1b,1)==1);
 // Frame 1 continues: a5d2 4=0 < 6 -> a348 (9b58 returns at 9b64) -> WORD 0088+0180 -> a5e6 -> c2c0/c2c6 -> 2ac2.
 o=Out();assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&quiet(o)&&s.a[7]==SP+4&&s.d[0]==0&&get(ram,TOP+4,2)==0x0208);
 assert(s.a[1]==0xa008&&s.a[2]==TOP&&s.a[5]==0x108000&&s.a[6]==CHILD&&get(ram,0x107f12,4)==TOP&&s.carry==ms5::AnimationCarryUnknown);
 // Declared re-entry (PC=2ab8, A6=child with (A6)=c2ba): opening frames draw the growing box.
 const std::uint32_t words[3]={0x0388,0x0508,0x0600};const unsigned int heights[3]={2,3,5};
 for(unsigned int k=0;k<3;++k){
  assert(get(ram,CHILD,4)==0xc2ba);s.pc=0x2ab8;o=Out();
  assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&clean(o)&&s.a[7]==SP+4&&s.d[0]==0&&get(ram,TOP+4,2)==words[k]&&get(ram,0x107f1b,1)==1);
  Ports e;box(e,4,4,0x11,heights[k],0x0b);assert(same_ports(o.ports,e)&&o.ports[0].value==0x70840bf4U);
 }
 // Full frame: 4=6 >= c=6 -> a5ea. Cursor 7 advances 0 -> 2 (YES, first callback), first draw,
 // a63e D0=6 -> c1c4 (7e=012c, a216 moves to NO=3), a64c D0=0 -> bf94 -> a73e sound 1a6c.
 s.pc=0x2ab8;const Bytes start=ram;const ms5::AnimationMachineState old=s;o=Out();
 assert(run(ram,s,RETURN,o,&p)&&s.pc==RETURN&&clean(o));
 const Ports expect=full_frame();assert(expect.size()==189&&same_ports(o.ports,expect));
 assert(o.ports[102].value==((item_row(4,4,0)<<16)|0xffU)&&o.ports[104].value==0x70e50344U&&o.ports[105].size==2&&o.ports[105].value==0x8200);
 assert(get(ram,TOP+7,1)==3&&get(ram,TOP+8,1)==3&&get(ram,TOP+0xe,1)==0&&get(ram,CHILD+0x7e,2)==0x012c&&get(ram,0x107f1b,1)==0&&get(ram,TOP+4,2)==0x0600);
 assert(get(ram,0x104d82,2)==0x1a6c&&get(ram,0x104d8c,2)==2&&get(ram,0x104d8a,2)==0);
 assert(s.d[0]==0&&s.a[0]==0x104d82&&s.a[1]==0xa008&&s.a[2]==TOP&&s.a[5]==0x108000&&s.a[6]==CHILD&&s.a[7]==SP+4&&s.carry==ms5::AnimationCarryUnknown);
 // a216 BYTE push: A7-2 with 7(A2)=2 at the even address; A7+1 keeps the low BYTE of the earlier
 // JSR a73e return LONG 0000c1ca stored at A7-2.
 {Bytes r=start;ms5::AnimationMachineState t=old;Out to;assert(run(r,t,0xa21e,to,&p)&&t.a[7]==SP-10&&get(r,SP-10,2)==0x02ca&&get(r,SP-12,2)==0&&get(r,CHILD+0x7e,2)==0x012c);}
 // Split at a subsequence of the actual trace; outputs resume from the previous actual output.
 const std::uint32_t walk[]={0x2abe,0x2ac0,0xc2ba,FRAME,0xa380,0xa388,0xa3b8,0xa3c8,0xa3d0,0xa3e2,0xa5d2,0xa5ea,0xa5f4,0x9b26,0xa5fe,0xa606,0xa616,
  0xa61c,0x9b58,0x9b66,0x9b7a,0x9b82,0x9b8e,0xa018,0xa03a,0xa06c,0x9ba6,0x9baa,0x9bbc,0x9bc0,0x9bc8,0x9bcc,0x9bd0,0x9be2,0x9be6,0x9bea,
  0x9bee,0x9c00,0x9c08,0x9c10,0x9c14,0x9c26,0x9c2a,0x9c32,0x9c36,0x9c3a,0x9c4c,0x9c50,0x9c54,0x9c58,0x9c6a,0x9c6e,0x9c76,0x9c7a,0x9c8c,
  0x9c90,0x9c98,0x9c9c,0x9ca0,0x9cb2,0x9cb6,0x9cba,0x9cbe,0x9cd0,0xa624,0x9e1a,0x9e28,0x9e78,0x9e7a,0x9e82,0x9d3a,0x9d4c,0x9d9a,0x9da0,
  0x9dae,0x9dba,0x9dc0,0x9dc4,0x9dce,0x9dd6,0x9dda,0x9dea,0x9df2,0x9df6,0x9dfe,0x9f7c,0x9f96,0x9fbe,0x9e02,0x3918,0x391a,0x391e,0x3928,
  0xe84c8,0xe84d0,0x3650,0x392a,0x3926,0x9e08,0x9b3e,0x9b42,0x9b56,0x9e14,0x9e8a,0x9d86,0x9d92,0x9cd4,0x9cd8,0x9cdc,0x9cee,0x9cf0,0x9cf8,
  0x9cfc,0x9d00,0x9d12,0x9d16,0x9d1e,0x9d22,0x9d26,0x9d38,0x9d96,0x9db6,0x9de8,0x9b54,0xc1c4,0xa73e,0xa754,0xc1ca,0xc1de,0xc212,0xbf94,
  0xbf9a,0xbfa8,0xbfbc,0x9e92,0xa628,0xa63e,0xc1d2,0xa216,0xa21e,0xa22c,0xa238,0xa246,0xa252,0xa258,0xa262,0xa008,0xa00c,0xa010,0xa26e,
  0xa278,0xa64c,0xa74a,0x3af8,0xa65e,0xc2c0,0xc2c6,RETURN};
 const unsigned int n=sizeof(walk)/sizeof(walk[0]);
 Bytes split=start;ms5::AnimationMachineState t=old;Ports all;
 for(unsigned int i=0;i<n;++i){Out so;assert(run(split,t,walk[i],so,&p)&&t.pc==walk[i]&&clean(so));append(all,so.ports);}
 assert(split==ram&&same(t,s)&&same_ports(all,o.ports));
 // Fresh split at the first occurrence of each checkpoint, then continue.
 for(unsigned int i=0;i+1<n;++i){Bytes r2=start;ms5::AnimationMachineState u=old;Out a,b;
  assert(run(r2,u,walk[i],a,&p)&&u.pc==walk[i]&&run(r2,u,RETURN,b,&p)&&r2==ram&&same(u,s));append(a.ports,b.ports);assert(same_ports(a.ports,o.ports));}
 // Other stops: the full frame returns to 2ac2, the dispatcher follows 8(A6)=5a5a5a5a and rolls back.
 reject(start,old,0xa406,"unsupported program bus device address",&p);
}
// Opening frames from a declared a370 entry (return STOP) until a5ea clears -e5.
unsigned int openings(std::uint32_t residual,std::uint32_t c,std::vector<std::uint32_t>&words){
 Bytes ram;ms5::AnimationMachineState s;generic(FRAME,ram,s);put(ram,TOP+4,1,0);put(ram,TOP+5,1,residual);put(ram,TOP+0xc,1,c);words.clear();
 for(unsigned int n=0;n<16;++n){
  s.pc=FRAME;s.a[7]=SP;put(ram,SP,4,STOP);Out o;assert(run(ram,s,STOP,o)&&s.pc==STOP&&s.a[7]==SP+4&&s.d[0]==0&&clean(o));
  if(get(ram,0x107f1b,1)==0)return n;
  words.push_back(get(ram,TOP+4,2));
 }
 assert(false);return 0;
}
void opening(){
 // ADD.W c<<6 to WORD 4(A2) including the residual byte 5; clamp to c<<8 when unsigned D0 < WORD.
 std::vector<std::uint32_t> w;
 assert(openings(0,2,w)==4&&w.size()==4&&w[0]==0x80&&w[1]==0x100&&w[2]==0x180&&w[3]==0x200);
 assert(openings(0x80,2,w)==3&&w[0]==0x100&&w[1]==0x180&&w[2]==0x200);
 assert(openings(0xff,2,w)==3&&w[0]==0x17f&&w[1]==0x1ff&&w[2]==0x200);
 assert(openings(0x88,6,w)==4&&w[0]==0x208&&w[1]==0x388&&w[2]==0x508&&w[3]==0x600);
 assert(openings(0x5a,0,w)==0&&w.empty());
 // a350 alone: unsigned CMP.W (9000 >= 7000 keeps 7000), clamp (a400 -> 9000), WORD wrap (f000+3fc0 = 2fc0), 13f -> 100.
 const std::uint32_t cases[][3]={{0x90,0x4c00,0x7000},{0x90,0x8000,0x9000},{0xff,0xf000,0x2fc0},{0x01,0x00ff,0x0100}};
 for(unsigned int i=0;i<4;++i){Bytes ram;ms5::AnimationMachineState s;generic(0xa350,ram,s);put(ram,TOP+0xc,1,cases[i][0]);put(ram,TOP+4,2,cases[i][1]);
  Out o;assert(run(ram,s,0xa36e,o)&&get(ram,TOP+4,2)==cases[i][2]&&(s.d[0]&0xffffU)==((cases[i][0]<<8)&65535U)&&quiet(o));}
 // -f2 >= 107f0e (unsigned, also 80000000): a3de MOVEQ -1; -ee untouched.
 const std::uint32_t f2[]={0x107f0e,0x107f10,0x80000000U};
 for(unsigned int i=0;i<3;++i){Bytes ram;ms5::AnimationMachineState s;generic(FRAME,ram,s);put(ram,0x107f0e,4,f2[i]);put(ram,0x107f12,4,OLD_EE);Out o;
  assert(run(ram,s,STOP,o)&&s.d[0]==0xffffffffU&&s.a[2]==f2[i]&&s.a[7]==SP+4&&get(ram,0x107f12,4)==OLD_EE&&quiet(o));}
 // -e5 other than 0/1/2: a402 MOVEQ -1.
 const std::uint32_t e5[]={3,0xff,0x80};
 for(unsigned int i=0;i<3;++i){Bytes ram;ms5::AnimationMachineState s;generic(FRAME,ram,s);put(ram,0x107f1b,1,e5[i]);Out o;
  assert(run(ram,s,STOP,o)&&s.d[0]==0xffffffffU&&s.a[7]==SP+4&&get(ram,0x107f12,4)==TOP&&quiet(o));}
}
// Two frames: lower 107efe (hook) below the top 107eee (-f2). -e5=33 ends a370 with D0=-1.
void two_frames(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t hook,std::uint32_t ux,std::uint32_t uf){
 generic(FRAME,ram,s);put(ram,0x107f0e,4,UP);put(ram,0x107f1b,1,0x33);
 const std::uint32_t items[]={TEXT2,0},cb[]={0,0};
 frame(ram,TOP,DESC,3,2,0,2,2,6,3);desc(ram,DESC,TEXT,hook,0,items,cb,2);text(ram,TEXT,"XYZ",65535);text(ram,TEXT2,"AB",65535);
 frame(ram,UP,DESC2,2,1,0,ux,3,3,2);put(ram,UP+0xf,1,uf);desc(ram,DESC2,0,0,0,items,cb,1);
}
void covered(){
 // Hook 9b58 draws the lower box (6b palette) while 107eee covers x 4..6, y 3..4. A covered cell
 // skips ADDI.W #20 (BCS to the next check), so the rest of that row stays covered.
 {Bytes ram;ms5::AnimationMachineState s;two_frames(ram,s,0x9b58,4,0);Out o;
  assert(run(ram,s,STOP,o)&&clean(o)&&s.d[0]==0xffffffffU&&s.a[7]==SP+4&&s.a[2]==UP&&get(ram,0x107f12,4)==UP);
  Ports e;tile_row(e,cell(2,2),0x6b,0xf4,0xf0,0xf5,4);
  port(e,4,(cell(2,3)<<16)|0x6bf2U);port(e,4,(cell(3,3)<<16)|0x6b60U);port(e,4,(cell(2,4)<<16)|0x6bf6U);port(e,4,(cell(3,4)<<16)|0x6bf1U);
  assert(same_ports(o.ports,e));}
 // BTST #0,f(A0) set: the upper frame is skipped, the whole lower box is drawn.
 {Bytes ram;ms5::AnimationMachineState s;two_frames(ram,s,0x9b58,4,1);Out o;assert(run(ram,s,STOP,o)&&clean(o));
  Ports e;box(e,2,2,6,3,0x6b);assert(same_ports(o.ports,e));}
 // Hook 9e1a: title (D1=0603, centered), cursor through 9dc0/9dd6 and text through a008/a00c.
 for(unsigned int ux=3;ux<=6;++ux){Bytes ram;ms5::AnimationMachineState s;two_frames(ram,s,0x9e1a,ux,0);Out o;
  assert(run(ram,s,STOP,o)&&clean(o)&&s.d[0]==0xffffffffU&&s.a[1]==0xa008);
  Ports e;text_ports(e,cell(3,2),0x603,"XYZ");
  const std::uint32_t r0=item_row(2,2,0),r1=item_row(2,2,1);
  if(ux>3){port(e,4,(r0<<16)|0x313U);if(ux>4)port(e,4,(((r0+0x20U)&65535U)<<16)|0x314U);}
  if(ux>5)text_ports(e,(r0+0x40U)&65535U,3,"A");
  if(ux>3){port(e,4,(r1<<16)|0xffU);if(ux>4)port(e,4,(((r1+0x20U)&65535U)<<16)|0xffU);}
  assert(same_ports(o.ports,e));}
 // a018 alone through BCS 9ba6: top frame only -> a06c Clear; covering frame above -> a076 Set.
 for(unsigned int k=0;k<2;++k){Bytes ram;ms5::AnimationMachineState s;generic(0x9b8e,ram,s);
  if(k){put(ram,0x107f0e,4,UP);frame(ram,UP,DESC2,1,1,0,4,4,1,1);}
  const ms5::AnimationMachineState old=s;Out o;assert(run(ram,s,0x9ba6,o)&&quiet(o)&&s.carry==(k?ms5::AnimationCarrySet:ms5::AnimationCarryClear));
  assert(s.a[7]==SP&&get(ram,SP-4,4)==0x9ba6&&s.d[5]==old.d[5]&&s.d[6]==old.d[6]&&s.d[7]==old.d[7]&&s.a[0]==old.a[0]&&s.a[1]==old.a[1]);
  // MOVEM.L D5-D7/A0-A1 saved ascending below the return and restored.
  assert(get(ram,SP-24,4)==old.d[5]&&get(ram,SP-12,4)==old.a[0]&&get(ram,SP-8,4)==old.a[1]);
  o=Out();assert(run(ram,s,0x9bbc,o)&&s.carry==(k?ms5::AnimationCarrySet:ms5::AnimationCarryUnknown)&&o.ports.size()==(k?0U:1U)); // BCS block keeps C; 9baa does not
  if(!k)assert(o.ports[0].value==((cell(4,4)<<16)|0x70f4U));} // entered at 9b8e: high WORD is the old D0.W 7084
}
void draw_edges(){
 // Small boxes (BLS: no f0/60/f1 when b <= 2), BYTE-only ADD of y (e0+30 -> 10: 7010).
 const std::uint32_t boxes[][4]={{7,0x30,2,4},{7,0x30,1,1},{7,0x30,0,2},{7,0x30,3,3},{0x80,1,4,5},{4,4,0xff,1}};
 for(unsigned int i=0;i<6;++i){Bytes ram;ms5::AnimationMachineState s;generic(0x9b58,ram,s);frame(ram,TOP,DESC,boxes[i][3],2,0,boxes[i][0],boxes[i][1],boxes[i][2],6);
  Out o;assert(run(ram,s,STOP,o)&&clean(o)&&s.a[7]==SP+4);Ports e;box(e,boxes[i][0],boxes[i][1],boxes[i][2],boxes[i][3],0x0b);assert(same_ports(o.ports,e));
  if(i==0)assert(o.ports.size()==8&&o.ports[0].value==0x70100bf4U);}
 {Bytes ram;ms5::AnimationMachineState s;generic(0x9b58,ram,s);put(ram,TOP+4,1,0);Out o;assert(run(ram,s,STOP,o)&&quiet(o));}
 // Separator rows: SUBQ.W #2 borrow (b<2) draws nothing; b=2 wraps SUBQ.B to ff (256 tiles); b=3 bf8 only.
 const std::uint32_t widths[]={0,1,2,3,4,5,0x11};const unsigned int counts[]={0,0,256,1,2,3,15};
 for(unsigned int i=0;i<7;++i){Bytes ram;ms5::AnimationMachineState s;generic(0x9d3a,ram,s);put(ram,TOP+0xb,1,widths[i]);put(ram,DESC+0x10,4,0xfffffffeU);
  Out o;assert(run(ram,s,STOP,o)&&clean(o)&&o.ports.size()==counts[i]);Ports e;separator(e,item_row(4,4,0),widths[i]);assert(same_ports(o.ports,e));}
 // Row beyond 4(A2): 9d4a RTS, nothing drawn.
 {Bytes ram;ms5::AnimationMachineState s;generic(0x9d3a,ram,s);put(ram,TOP+8,1,1);Out o;assert(run(ram,s,STOP,o)&&quiet(o)&&(s.d[1]&255U)==2);}
 // Flags AND e != 0: no cursor column; palette 9f7c: top + flags 2 -> 0003 (7==8) / 0b03 (7!=8);
 // not top -> 0603 (7!=8) or 9f96 (7==8).
 const std::uint32_t pal[][5]={{2,0,TOP,0,0x003},{2,1,TOP,0,0xb03},{0,1,TOP,0,0x003},{2,1,UP,0,0x603},{2,0,UP,0,0x003},{0x0e,1,TOP,0,0x003},{4,1,UP,0,0x603}};
 for(unsigned int i=0;i<7;++i){Bytes ram;ms5::AnimationMachineState s;generic(0x9d3a,ram,s);put(ram,DESC+0xe,2,pal[i][0]);put(ram,TOP+4,1,3);put(ram,TOP+8,1,pal[i][1]);
  put(ram,0x107f0e,4,pal[i][2]);put(ram,DESC+0x14,4,0);
  Out o;assert(run(ram,s,STOP,o)&&clean(o));Ports e;const std::uint32_t row=item_row(4,4,pal[i][1]);
  if(pal[i][0]&0xeU)text_ports(e,row,pal[i][4],"AB");else{cursor(e,row,pal[i][1]==0);text_ports(e,(row+0x40U)&65535U,pal[i][4],"AB");}
  assert(same_ports(o.ports,e));}
 // Title centering: NEG.B, ADD.B b, ASR.B #1 (arithmetic), ADD.B 9 -> column; D1=0103 for the top menu.
 const char* titles[]={"XYZ","ABCDEFGHI","Q"};const std::uint32_t cols[]={3,0,4};
 for(unsigned int i=0;i<3;++i){Bytes ram;ms5::AnimationMachineState s;generic(0x9e1a,ram,s);frame(ram,TOP,DESC,2,0,0,2,4,6,6);text(ram,TEXT,titles[i],65535);
  Out o;assert(run(ram,s,STOP,o)&&clean(o));Ports e;text_ports(e,cell(cols[i],4),0x103,titles[i]);assert(same_ports(o.ports,e));}
 // Title pointer 0 and 4(A2)=0.
 {Bytes ram;ms5::AnimationMachineState s;generic(0x9e1a,ram,s);put(ram,DESC,4,0);put(ram,TOP+6,1,0);Out o;assert(run(ram,s,STOP,o)&&quiet(o));
  generic(0x9e1a,ram,s);put(ram,TOP+4,1,0);o=Out();assert(run(ram,s,STOP,o)&&quiet(o));}
 // 3650 nibble shifts: \c 0f gives D1=0b0f (< 10 renders): LSL.B #4 -> 0bf0, LSL.W #4 -> bf00, 'Z' -> bf5a.
 {Bytes ram;ms5::AnimationMachineState s;generic(0x3918,ram,s);text(ram,TEXT,"\\c" "\x0f" "Z",65535);s.a[1]=0xe84c8;s.d[1]=0x0b03;s.d[0]=0x55557123;
  Out o;assert(run(ram,s,STOP,o)&&clean(o)&&o.ports.size()==2&&o.ports[0].value==0x7123bf5aU&&o.ports[1].value==0x8200&&(s.d[0]&65535U)==0x7143&&(s.d[3]&65535U)==0x7123);}
}
void boundaries(){
 for(unsigned int i=0;i<BOUNDARIES;++i){Bytes ram;ms5::AnimationMachineState s;generic(BOUNDARY[i],ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 struct Reach {std::uint32_t pc,stop;};
 // Each boundary reached from its natural predecessor; stop there succeeds, any other stop rolls back.
 // Close-unit entries (9e94 a2be a662 c2c8) now execute: only the successful stop is checked here.
 for(unsigned int k=0;k<11;++k){Bytes ram;ms5::AnimationMachineState s;std::uint32_t stop=0;
  switch(k){
  case 0:generic(0x9b58,ram,s);put(ram,DESC+0xe,2,0x0001);stop=0x9e94;break;           // flags bit0
  case 1:generic(FRAME,ram,s);put(ram,0x107f0e,4,UP);frame(ram,UP,DESC,1,1,0,0,0,1,1);put(ram,TOP+0xf,1,1);stop=0xa2be;break; // f bit0, 4!=0
  case 2:generic(0xa3ac,ram,s);put(ram,TOP+4,1,0);stop=0xa6da;break;                    // BSR a6da
  case 3:generic(FRAME,ram,s);put(ram,DESC+0xa,4,0xa6da);stop=0xa6da;break;              // hook JSR (A4)
  case 4:generic(FRAME,ram,s);put(ram,0x107f1b,1,0);put(ram,TOP+4,1,6);put(ram,DESC+6,4,0xa6da);stop=0xa6da;break; // -e5=0: a406 input frame, descriptor hook JSR (A3)
  case 5:generic(FRAME,ram,s);put(ram,0x107f1b,1,2);stop=0xa662;break;
  case 6:generic(0xbf94,ram,s);s.d[0]=0x77770003;put(ram,SP,4,0xa662);stop=0xa662;break; // a70a/a1ee RTS to a declared a662 return
  case 7:generic(0xc1c4,ram,s);s.d[0]=0x77770003;stop=0xbd26;break;
  case 8:generic(0x3918,ram,s);text(ram,TEXT,"\\c" " A",65535);s.a[1]=0xa008;stop=0xe84d6;break;  // \c 20 -> D1.B >= 10
  case 9:generic(0xa5ea,ram,s);put(ram,DESC+0x10,4,0xffffffffU);put(ram,DESC+0x14,4,0xbf94);put(ram,TOP+6,1,0);stop=0xa63c;break; // TRAP #f
  default:generic(0xc2ba,ram,s);put(ram,0x107f0e,4,0x107f0e);stop=0xc2c8;break;         // D0=-1 after JSR a370
  }
  const Bytes start=ram;const ms5::AnimationMachineState old=s;
  if(stop!=0x9e94&&stop!=0xa2be&&stop!=0xa662&&stop!=0xc2c8)reject(start,old,STOP,"unsupported animation machine PC");
  Out o;assert(run(ram,s,stop,o)&&s.pc==stop&&clean(o));
  if(k==1)assert(s.a[7]==SP-8&&get(ram,SP-8,4)==0xa3ac&&get(ram,SP-4,4)==TOP);
  if(k==3)assert(s.a[7]==SP-8&&get(ram,SP-8,4)==0xa3c8);
  if(k==4)assert(s.a[7]==SP-8&&get(ram,SP-8,4)==0xa442&&get(ram,SP-4,4)==TOP);
  if(k==6)assert(get(ram,CHILD+0x80,1)==0xff&&s.a[7]==SP+4&&get(ram,0x107f1b,1)==2&&s.a[2]==TOP&&get(ram,0x104d82,2)==0x1a5b);
  if(k==7)assert(s.a[7]==SP-4&&get(ram,SP-4,4)==0xc1ea&&get(ram,CHILD+0x7e,2)==0);
  if(k==8)assert(o.ports.size()==0&&(s.d[1]&255U)==0x20&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x392a); // a010 pushed e84c8 and RTS used it
  if(k==9)assert(o.ports.size()==14&&get(ram,0x107f1b,1)==0); // box h=2 w=5 (10), title "AB" (4), no items
  if(k==10)assert(s.d[0]==0xffffffffU&&s.a[7]==SP);
 }
}
void callbacks(){
 // c1c4 YES: D0=6 -> 7e(A6)=012c, JMP a216; D0=5 -> RTS; D0=0 -> a73e sound 1a6c, D0/D1 WORDs restored.
 {Bytes ram;ms5::AnimationMachineState s;generic(0xc1c4,ram,s);s.d[0]=0x12340006;Out o;
  assert(run(ram,s,0xa216,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x012c&&s.a[7]==SP&&s.d[0]==0x12340006);}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xc1c4,ram,s);s.d[0]=0x12340005;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0&&s.a[7]==SP+4&&s.d[0]==0x12340005&&get(ram,0x104d82,2)==0);}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xc1c4,ram,s);s.d[0]=0x12340000;s.d[1]=0x5678abcd;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&s.d[0]==0x12340000&&s.d[1]==0x5678abcd&&get(ram,0x104d82,2)==0x1a6c&&get(ram,0x104d8c,2)==2);}
 // bf94 NO: D0=6 -> 7e=001e then CMPI 3 -> RTS; D0=0 -> sound.
 {Bytes ram;ms5::AnimationMachineState s;generic(0xbf94,ram,s);s.d[0]=0x00000006;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,CHILD+0x7e,2)==0x001e&&get(ram,CHILD+0x80,1)==0&&s.a[7]==SP+4);}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xbf94,ram,s);s.d[0]=0xffff0000U;Out o;
  assert(run(ram,s,STOP,o)&&quiet(o)&&get(ram,0x104d82,2)==0x1a6c&&s.d[0]==0xffff0000U);}
 // a216 cursor wrap: BTST #1,f set steps down (0 - 1 borrows -> +6(A2)); separators and callback-less items are skipped.
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa216,ram,s);put(ram,TOP+0xf,1,2);put(ram,TOP+7,1,0);put(ram,TOP+4,1,3);
  Out o;assert(run(ram,s,STOP,o)&&clean(o)&&get(ram,TOP+7,1)==1&&get(ram,TOP+8,1)==1&&get(ram,TOP+0xe,1)==0&&s.a[7]==SP+4);}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa216,ram,s);put(ram,TOP+7,1,1);put(ram,TOP+4,1,3);
  Out o;assert(run(ram,s,STOP,o)&&clean(o)&&get(ram,TOP+7,1)==1&&get(ram,TOP+8,1)==1);}
 // A separator with a callback is skipped by a258 (LONG (A3)=fffffffe).
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa216,ram,s);const std::uint32_t items[]={TEXT,0xfffffffeU,TEXT},cb[]={0xbf94,0xbf94,0xbf94};
  desc(ram,DESC,TEXT,0,0,items,cb,3);put(ram,TOP+6,1,3);put(ram,TOP+4,1,4);
  Out o;assert(run(ram,s,STOP,o)&&clean(o)&&get(ram,TOP+7,1)==2&&get(ram,TOP+8,1)==2&&s.a[7]==SP+4);
  Ports e;cursor(e,item_row(4,4,0),false);text_ports(e,(item_row(4,4,0)+0x40U)&65535U,3,"AB");
  cursor(e,item_row(4,4,2),true);text_ports(e,(item_row(4,4,2)+0x40U)&65535U,3,"AB");assert(same_ports(o.ports,e));}
}
void errors(){
 // Odd A2 (-f2=107eff): WORD 4(A2) at a350. Odd A3 (descriptor DESC+1): TST.L 4(A3) at a5fe.
 {Bytes ram;ms5::AnimationMachineState s;generic(FRAME,ram,s);put(ram,0x107f0e,4,0x107eff);reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa5ea,ram,s);put(ram,TOP,4,DESC+1);reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A7: a388 LONG push; a216 BYTE push succeeds at A7-2 but the later LONG push fails.
 {Bytes ram;ms5::AnimationMachineState s;generic(FRAME,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa216,ram,s);s.a[7]=SP+1;reject(ram,s,STOP,"even WORD/LONG");}
 // Odd A0/A1/A4 jump targets: callback (9b54), renderer (3928), hook (a3c6).
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa63e,ram,s);put(ram,TOP+7,1,1);put(ram,DESC+0x1e,4,0xbf95);reject(ram,s,STOP,"odd jump target");}
 {Bytes ram;ms5::AnimationMachineState s;generic(0x3918,ram,s);s.a[1]=0xa009;reject(ram,s,STOP,"odd jump target");}
 {Bytes ram;ms5::AnimationMachineState s;generic(FRAME,ram,s);put(ram,DESC+0xa,4,0x9b59);reject(ram,s,STOP,"odd jump target");}
 // Interior and bundled PCs inside the routed ranges.
 const std::uint32_t ranges[][2]={{0x3650,0x366e},{0x3918,0x392a},{0x9b26,0x9e92},{0x9f7c,0x9fc2},{0xa008,0xa07e},{0xa216,0xa27e},
  {0xa348,0xa404},{0xa5d2,0xa660},{0xa73e,0xa758},{0xbf94,0xbfbc},{0xc1c4,0xc212},{0xc2c0,0xc2c6},{0xe84c8,0xe84d0}};
 unsigned int interior=0;
 for(unsigned int i=0;i<13;++i)for(std::uint32_t pc=ranges[i][0];pc<=ranges[i][1];pc+=2){
  if(listed(pc))continue;Bytes ram;ms5::AnimationMachineState s;generic(pc,ram,s);
  reject(ram,s,STOP,pc==0xa63c?"unsupported animation machine PC":"unsupported animation card menu open PC");++interior;}
 assert(interior>=500);
 // Neighbours outside the routed ranges (a346 is now the interior RTS of the close a344 block).
 const std::uint32_t outside[]={0x364e,0x3670,0x3916,0x392c,0x9b24,0x9f7a,0xa006,0xa080,0xa214,0xa280,0xa698,0xa73c,0xa75a,
  0xbfbe,0xc1c2,0xc214,0xc2bc,0xc2be,0xe84c6};
 for(unsigned int i=0;i<sizeof(outside)/sizeof(outside[0]);++i){Bytes ram;ms5::AnimationMachineState s;generic(outside[i],ram,s);reject(ram,s,STOP,"unsupported animation machine PC");}
 {Bytes ram;ms5::AnimationMachineState s;generic(0xa371,ram,s);reject(ram,s,STOP,"unaligned animation machine PC");}
}
void zero_step(){
 for(unsigned int carry=0;carry<3;++carry)for(unsigned int i=0;i<ROWS+BOUNDARIES;++i){
  const std::uint32_t pc=i<ROWS?TABLE[i][0]:BOUNDARY[i-ROWS];Bytes ram;ms5::AnimationMachineState s;generic(pc,ram,s);s.carry=carry_of(carry);
  const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;assert(run(ram,s,pc,o)&&same(s,old)&&ram==before&&quiet(o));}
}
void carry(){
 assert(ROWS==202);unsigned int keeps=0,consumers=0;
 for(unsigned int i=0;i<ROWS;++i){
  const std::uint32_t pc=TABLE[i][0];const bool keep=member(KEEP,sizeof(KEEP)/sizeof(KEEP[0]),pc);
  const bool consumer=TABLE[i][1]!=TABLE[i][2];assert(consumer==member(BCS,15,pc));if(keep)++keeps;if(consumer){++consumers;assert(keep);}
  for(unsigned int carry=0;carry<3;++carry){Bytes ram;ms5::AnimationMachineState s;generic(pc,ram,s);s.carry=carry_of(carry);
   if(consumer&&carry==0){reject(ram,s,STOP,"card menu caller requires known carry");continue;}
   const std::uint32_t stop=carry==2?TABLE[i][2]:TABLE[i][1];Out o;assert(run(ram,s,stop,o)&&s.pc==stop&&clean(o));
   ms5::AnimationCarryState expect=keep?carry_of(carry):ms5::AnimationCarryUnknown;
   if(pc==0xa06c)expect=ms5::AnimationCarryClear;if(pc==0xa076)expect=ms5::AnimationCarrySet;
   assert(s.carry==expect);}}
 assert(keeps==68&&consumers==15);
}
}
int main(){natural();opening();covered();draw_edges();boundaries();callbacks();errors();zero_step();carry();
std::cout<<"animation_machine_card_menu_open_test PASS "<<calls<<" API invocations\n";}
