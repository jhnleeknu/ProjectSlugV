#include "ms5/animation_machine_frame.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
// Frame driver (H + declared controller skip + N) through run_animation_machine only. All inputs are declared fixtures: the
// static scheduler list (8 nodes from 100820 at c4 steps: callback e4a / e74, c52a, six 270e; sentinel 100e98; free pool
// from 100f5c; LONG 104ca4 = SPd), the frame head state (PC = LONG (100820), A6 100820, A7 1feffc, LONG (1feffc) = 2ac2), the
// declared raster / input reads per frame and synthetic typed physical bytes (not ROM data): the 16-byte table b58..b68 read by
// b98 and the banner window bytes at 100024 / 200004 .. 200900 read by the sprite writers. The expected values are the
// harness chaining of run_animation_machine calls (manual_pass / manual_frame below), not an external oracle.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::PhysicalRomResource> Physical;
typedef ms5::AnimationMachineState State;
typedef ms5::AnimationMachineDevice Device;
typedef std::vector<ms5::VideoPortWrite> Ports;
const std::uint32_t SPD=0x1ff000,HEAD=0x100820,CONTROLLER=0x1008e4,NODE_SIZE=0xc4,SENTINEL=0x100e98,POOL0=0x100f5c;
unsigned int checks=0;
struct Synthetic {std::uint32_t address;const char* bytes;};
const Synthetic SYNTHETIC[]={
 {0xb58,"005a010080000003ff001100007f0002"},
 {0x200004,"0010a0000010a100"},
 {0x300014,"0010a200"},
 {0x700400,"0010a300"},
 {0x20000c,"00200800"},
 {0x200010,"0010a401"},
 {0x100024,"0010a500"},
 {0x200800,"00200900"},
 {0x49ab0,"10204080"},
 {0xe8a0c,"0000000200000001000100010002000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"},
 {0x200900,"0212003000200203c83e9828bd05fd4c2faf580fb2ec8b419eaa5fd44e93bd56005000100101b7bfaf7a"},
};
unsigned int hex_digit(char c){return c<='9'?static_cast<unsigned int>(c-'0'):static_cast<unsigned int>(c-'a'+10);}
Bytes hex_bytes(const char* text){Bytes b;for(const char* p=text;p[0]&&p[1];p+=2)b.push_back(static_cast<std::uint8_t>((hex_digit(p[0])<<4)|hex_digit(p[1])));return b;}
Physical make_rom(){
 Physical p(sizeof(SYNTHETIC)/sizeof(SYNTHETIC[0]));
 for(std::size_t i=0;i<p.size();++i){p[i].source_rom_offset=SYNTHETIC[i].address;p[i].data=hex_bytes(SYNTHETIC[i].bytes);}
 return p;}
const Physical ROM=make_rom();
ms5::ProgramBusState bus_of(){ms5::ProgramBusState bus;bus.physical_rom=&ROM;return bus;}
void put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes& b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
void apply(Bytes& b,const char* text){
 const char* p=text;
 while(*p){char* end=NULL;const std::uint32_t a=static_cast<std::uint32_t>(std::strtoul(p,&end,16));assert(end&&*end==':');p=end+1;
  std::uint32_t at=a;while(*p&&*p!=','){b[at&65535U]=static_cast<std::uint8_t>((hex_digit(p[0])<<4)|hex_digit(p[1]));p+=2;++at;}if(*p==',')++p;}}
std::uint32_t static_node(unsigned int k){return HEAD+k*NODE_SIZE;}
void node_init(Bytes& ram,std::uint32_t a,std::uint32_t cb,std::uint32_t prev,std::uint32_t next,std::uint32_t parent,std::uint32_t depth){
 put(ram,a,4,cb);put(ram,a+4,4,prev);put(ram,a+8,4,next);put(ram,a+0xc,4,parent);put(ram,a+0x10,2,depth);put(ram,a+0x12,2,0xffff);put(ram,a+0x1e,2,0xffff);}
// Valid frame head start: head callback LONG, the dispatcher return LONG at SPd - 4, IRQ signal bytes and the puts.
Bytes frame_ram(std::uint32_t head,const char* puts){
 Bytes ram(65536,0);
 for(unsigned int k=0;k<8;++k)node_init(ram,static_node(k),k==0?head:(k==1?0xc52aU:0x270eU),static_node((k+7)%8),static_node((k+1)%8),0,0);
 node_init(ram,SENTINEL,0x270e,SENTINEL,SENTINEL,SENTINEL,0);
 for(unsigned int i=0;i<4;++i)put(ram,POOL0+i*NODE_SIZE+8,4,i+1<4?POOL0+(i+1)*NODE_SIZE:0);
 put(ram,0x104c9c,4,POOL0);put(ram,0x104ca0,2,4);put(ram,0x104ca4,4,SPD);put(ram,SPD-4,4,0x2ac2);
 put(ram,0x10001b,1,0x80);apply(ram,puts);return ram;}
State head_state(const Bytes& ram){State s;s.pc=get(ram,HEAD,4);s.a[5]=0x108000;s.a[6]=HEAD;s.a[7]=SPD-4;s.carry=ms5::AnimationCarryClear;return s;}
State pass_state(){State s;s.pc=0x2ac2;s.a[5]=0x108000;s.a[6]=CONTROLLER;s.a[7]=SPD;return s;}
ms5::AnimationMachineExternalRead ext(std::uint32_t address,std::uint8_t size,std::uint32_t value){
 ms5::AnimationMachineExternalRead r;r.address=address;r.size=size;r.value=value;return r;}
// One head's declared reads: raster x2 (value 0), then the input sampler order 380000, 300000, 340000, 300000, 340000.
std::vector<ms5::AnimationMachineExternalRead> frame_reads(){
 std::vector<ms5::AnimationMachineExternalRead> q;
 q.push_back(ext(0x3c0006,2,0));q.push_back(ext(0x3c0006,2,0));q.push_back(ext(0x380000,1,0xff));q.push_back(ext(0x300000,1,0xff));
 q.push_back(ext(0x340000,1,0xff));q.push_back(ext(0x300000,1,0xff));q.push_back(ext(0x340000,1,0xff));return q;}
Device device_with(const std::vector<ms5::AnimationMachineExternalRead>& q){
 Device d;d.pvc[0x1ff1]=0xa0;d.pvc[0x1ff2]=0x10;d.reads=q;return d;}
bool same_state(const State& a,const State& b){
 for(unsigned int i=0;i<8;++i){if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;}
 return a.pc==b.pc&&a.carry==b.carry;}
bool same_ports(const Ports& a,const Ports& b){
 if(a.size()!=b.size())return false;
 for(std::size_t i=0;i<a.size();++i){if(a[i].address!=b[i].address||a[i].size!=b[i].size||a[i].value!=b[i].value)return false;}
 return true;}
bool same_reads(const Device& a,const Device& b){
 if(a.reads.size()!=b.reads.size())return false;
 for(std::size_t i=0;i<a.reads.size();++i){
  if(a.reads[i].address!=b.reads[i].address||a.reads[i].size!=b.reads[i].size||a.reads[i].value!=b.reads[i].value)return false;}
 return true;}
bool same_device(const Device& a,const Device& b){return a.pvc==b.pvc&&a.bank_base==b.bank_base&&same_reads(a,b);}
bool same_waits(const std::vector<ms5::AnimationFrameWait>& a,const std::vector<ms5::AnimationFrameWait>& b){
 if(a.size()!=b.size())return false;
 for(std::size_t i=0;i<a.size();++i){
  if(a[i].segment!=b[i].segment||a[i].pc!=b[i].pc||a[i].address!=b[i].address||a[i].size!=b[i].size||
   a[i].before!=b[i].before||a[i].released!=b[i].released)return false;}
 return true;}
bool same_result(const ms5::AnimationFrameResult& a,const ms5::AnimationFrameResult& b){
 return a.head_pc==b.head_pc&&a.controller_pc==b.controller_pc&&a.pass_stop_pc==b.pass_stop_pc&&same_ports(a.head_ports,b.head_ports)&&
  same_ports(a.node_ports,b.node_ports)&&same_waits(a.waits,b.waits)&&a.head_external_reads==b.head_external_reads&&
  a.node_external_reads==b.node_external_reads;}
ms5::AnimationFrameResult sentinel_result(){
 ms5::AnimationFrameResult r;r.head_pc=1;r.controller_pc=2;r.pass_stop_pc=3;r.head_external_reads=4;r.node_external_reads=5;
 ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;r.head_ports.push_back(p);r.node_ports.push_back(p);
 ms5::AnimationFrameWait w;w.segment=ms5::AnimationFrameNodes;w.pc=9;w.address=8;w.size=1;w.before=7;w.released=6;r.waits.push_back(w);return r;}
typedef bool (*FrameFunction)(std::vector<std::uint8_t>&,const std::vector<ms5::FixedDataResource>&,const ms5::ProgramBusState&,
 State&,Device&,std::uint8_t,ms5::AnimationFrameResult&,std::string&);
// Failure: the checked error, and ram / state / device (pvc, bank, reads) / result exactly unchanged.
void reject(FrameFunction f,const Bytes& ram_in,const State& s_in,const Device& d_in,const char* message){
 Bytes ram(ram_in);State s(s_in);Device d(d_in);ms5::AnimationFrameResult r=sentinel_result();const ms5::AnimationFrameResult r0=sentinel_result();
 std::vector<ms5::FixedDataResource> w;const ms5::ProgramBusState bus=bus_of();std::string error;
 const bool ok=f(ram,w,bus,s,d,0,r,error);
 if(ok||error!=message)std::cerr<<"expected error '"<<message<<"' got ok="<<ok<<" '"<<error<<"'\n";
 assert(!ok&&error==message&&ram==ram_in&&same_state(s,s_in)&&same_device(d,d_in)&&same_result(r,r0));++checks;}
// Harness-style manual segment: run_animation_machine to the stop PC with the declared releases (independent of the driver).
struct Manual {Ports head_ports,node_ports;std::uint32_t head_reads,node_reads;unsigned int waits;};
void manual_segment(Bytes& ram,State& s,Device& d,std::uint32_t stop,Ports& ports,std::uint32_t& reads,unsigned int& waits){
 const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;s.carry=ms5::AnimationCarryUnknown;
 for(unsigned int k=0;k<65;++k){
  Ports phase;std::uint32_t n=0;ms5::AnimationMachineStatus st=ms5::AnimationMachineReturned;std::string error;
  if(!ms5::run_animation_machine(ram,w,bus,s,d,stop,0,n,st,phase,error)){std::cerr<<"manual run: "<<error<<" pc "<<std::hex<<s.pc<<" a6 "<<s.a[6]<<" a7 "<<s.a[7]<<" k "<<k<<"\n";assert(false);}
  ports.insert(ports.end(),phase.begin(),phase.end());reads+=n;
  if(st==ms5::AnimationMachineReturned)return;
  ++waits;
  if(s.pc==0xef2)put(ram,s.a[5]-0x7fea,1,get(ram,s.a[5]-0x7fe9,1));
  else if(s.pc==0x16bd0)put(ram,s.a[5]+0xd34,2,s.d[0]&0xffff);
  else if(s.pc==0x3aea)put(ram,0x104d74,2,0xffff);
  else if(s.pc==0xcda4)put(ram,0x108d34,2,s.d[4]&0xffff);
  else if((s.pc==0x47af0||s.pc==0x478de)&&get(ram,0x107dea,2)==0)put(ram,0x107ded,1,get(ram,0x107ded,1)&0x7f);
  else {std::cerr<<"manual wait "<<std::hex<<s.pc<<"\n";assert(false);}}
 assert(false);}
void manual_pass(Bytes& ram,State& s,Device& d,Manual& m){
 const std::uint32_t stop=get(ram,HEAD,4);
 manual_segment(ram,s,d,stop,m.node_ports,m.node_reads,m.waits);}
void manual_frame(Bytes& ram,State& s,Device& d,Manual& m){
 const std::uint32_t controller=get(ram,CONTROLLER,4);
 manual_segment(ram,s,d,controller,m.head_ports,m.head_reads,m.waits);
 s.pc=0x2ac2;s.a[7]=SPD;s.carry=ms5::AnimationCarryUnknown;
 manual_pass(ram,s,d,m);}
// Declared 480bc frame helper fixture (the buffer-cue test's frame-buffer-waits builder): two-sprite slot submission with a sprite queue.
void bc_frame_base(Bytes& r){
 put(r,0x100cb8,4,0);put(r,0x100cb8+0x61,1,0x7f);put(r,0x100da8,4,0x2710);put(r,0x100da8+0x61,1,0x80);
 put(r,0x10d68e,1,0xfc);put(r,0x10dc88,4,0x10db88);put(r,0x10db84,4,0x11a5225a);put(r,0x10de2e,1,1);
 for(unsigned int i=0;i<32;++i)put(r,0x10db88+2*i,2,(0x8001U+i*0x1357U)&65535U);
 for(unsigned int i=0;i<8;++i)put(r,0x10d4e6+0x2c*i+0x26,4,0xffff0000U);
 const std::uint32_t buffers[2]={0x10d746,0x10d918};
 for(unsigned int k=0;k<2;++k){const std::uint32_t b=buffers[k];put(r,b,4,0xdeadbeefU);put(r,b+0xcc,4,0x01020304);put(r,b+0xd0,2,0x5555);put(r,b+0x1ce,2,0x6666);put(r,b+0x1d0,2,0x7777);}}
void bc_queue(Bytes& r,std::uint32_t consumer,std::uint32_t prepared){
 put(r,0x109152,4,0xcd50);put(r,0x108d34,2,consumer);put(r,0x108d36,2,prepared);put(r,0x108d38,2,0);put(r,0x108d3a,2,0);put(r,0x10914e,2,0);
 for(unsigned int i=0;i<256;++i)put(r,0x108b34+2*i,2,(i*12U)&65535U);}
void bc_slot(Bytes& r,unsigned int i,bool obj,bool src,bool mismatch,std::uint32_t flags,std::uint32_t x,std::uint32_t y,std::uint32_t px,std::uint32_t py){
 const std::uint32_t o=0x102000+i*0x100,s=0x106000+i*0x10;
 put(r,0x10daf8+8*i,4,obj?o:0);put(r,0x10dafc+8*i,4,src?s-4:0);put(r,o+0x15,1,flags);put(r,o+0x6d,1,(mismatch?i+1:i)|0xf0);
 put(r,o+0x42,2,px);put(r,o+0x46,2,py);put(r,s,2,x);put(r,s+2,2,y);put(r,s+4,2,0x10);put(r,s+6,2,0x20);}
void bc_frame(Bytes& r){bc_frame_base(r);put(r,0x10f001,1,0x80);bc_slot(r,0,true,true,false,3,0x10,0x100,0x20,0x180);bc_queue(r,2,4);}

// Driver call on copies of the inputs, the same input through the harness chain, and the full comparison.
struct Run {Bytes ram;State s;Device d;ms5::AnimationFrameResult r;std::string error;bool ok;};
Run drive(bool frame,const Bytes& ram,const State& s,const Device& d){
 Run x;x.ram=ram;x.s=s;x.d=d;x.ok=false;const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;
 if(frame)x.ok=ms5::step_animation_machine_frame(x.ram,w,bus,x.s,x.d,0,x.r,x.error);
 else x.ok=ms5::run_animation_machine_pass(x.ram,w,bus,x.s,x.d,0,x.r,x.error);
 if(!x.ok)std::cerr<<"driver error: "<<x.error<<"\n";
 assert(x.ok);return x;}
// The driver equals manual chaining of run_animation_machine calls (stop PCs LONG (1008e4) and LONG (100820)).
void same_as_manual(bool frame,const Run& x,const Bytes& ram,const State& s,const Device& d){
 Bytes mram(ram);State ms(s);Device md(d);Manual m;m.head_reads=0;m.node_reads=0;m.waits=0;
 const std::uint32_t head=get(ram,HEAD,4),controller=get(ram,CONTROLLER,4);
 if(frame)manual_frame(mram,ms,md,m);else manual_pass(mram,ms,md,m);
 assert(x.ram==mram&&same_state(x.s,ms)&&same_device(x.d,md)&&same_ports(x.r.head_ports,m.head_ports)&&same_ports(x.r.node_ports,m.node_ports)&&
  x.r.head_external_reads==m.head_reads&&x.r.node_external_reads==m.node_reads&&x.r.waits.size()==m.waits);
 assert(x.r.head_pc==(frame?head:0)&&x.r.controller_pc==(frame?controller:0)&&x.r.pass_stop_pc==head);
 // Boundary shape: a valid head start of the next frame, C Unknown.
 assert(x.s.pc==get(x.ram,HEAD,4)&&x.s.a[6]==HEAD&&x.s.a[7]==SPD-4&&get(x.ram,SPD-4,4)==0x2ac2&&x.s.carry==ms5::AnimationCarryUnknown);
 ++checks;}
// Success rows: a frame from a valid head start, a pass from the seed.
Run frame_row(const char* puts,std::uint32_t d0=0){
 Bytes ram=frame_ram(0xe74,puts);State s=head_state(ram);s.d[0]=d0;Device d=device_with(frame_reads());
 const Run x=drive(true,ram,s,d);same_as_manual(true,x,ram,s,d);return x;}
Bytes bc_ram(){Bytes ram=frame_ram(0xe74,"");bc_frame(ram);apply(ram,"100a6c:000480bc,102000:0000cd50,100cb8:0000270e,100da8:0000270e");return ram;}
void check_wait(const ms5::AnimationFrameWait& w,ms5::AnimationFrameSegment segment,std::uint32_t pc,std::uint32_t address,unsigned int size,
 std::uint32_t before,std::uint32_t released){
 if(w.segment!=segment||w.pc!=pc||w.address!=address||w.size!=size||w.before!=before||w.released!=released)
  std::cerr<<std::hex<<"wait "<<w.pc<<" "<<w.address<<" "<<w.before<<" "<<w.released<<"\n";
 assert(w.segment==segment&&w.pc==pc&&w.address==address&&w.size==size&&w.before==before&&w.released==released);}
void pass_and_frames(){
 // Pass from the seed (head e74): N only, then a valid head start.
 {const Bytes ram=frame_ram(0xe74,"");State s=pass_state();s.d[0]=0x1234;const Device d=device_with(frame_reads());
  const Run x=drive(false,ram,s,d);same_as_manual(false,x,ram,s,d);
  assert(x.r.pass_stop_pc==0xe74&&x.r.head_pc==0&&x.r.controller_pc==0&&x.r.head_ports.empty()&&x.r.waits.empty()&&x.s.pc==0xe74&&x.s.a[0]==0xe74&&
   x.r.node_external_reads==0&&same_reads(x.d,d));}
 // Pass from the seed with the first-frame callback e4a: the head start is e4a (the head itself needs ROM code bytes, not run here).
 {const Bytes ram=frame_ram(0xe4a,"");const State s=pass_state();const Device d=device_with(frame_reads());
  const Run x=drive(false,ram,s,d);same_as_manual(false,x,ram,s,d);assert(x.r.pass_stop_pc==0xe4a&&x.s.pc==0xe4a&&get(x.ram,HEAD,4)==0xe4a);}
 // One frame: H (head body e74 to the dispatcher, 7 declared reads), the controller skip, N.
 {const Run x=frame_row("");
  assert(x.r.head_pc==0xe74&&x.r.controller_pc==0xc52a&&x.r.pass_stop_pc==0xe74&&x.r.waits.empty()&&x.r.head_ports.size()==13&&x.r.node_ports.empty()&&
   x.r.head_external_reads==7&&x.r.node_external_reads==0&&x.d.reads.empty()&&get(x.ram,CONTROLLER,4)==0xc52a);}
 // The controller LONG is the H stop PC: another declared controller (c66a) is skipped the same way, never run.
 {const Run x=frame_row("1008e4:0000c66a");assert(x.r.controller_pc==0xc66a&&get(x.ram,CONTROLLER,4)==0xc66a);}
 // Declared reads: the unconsumed tail stays in the queue, only consumed reads are counted.
 {Bytes ram=frame_ram(0xe74,"");State s=head_state(ram);std::vector<ms5::AnimationMachineExternalRead> q=frame_reads();q.push_back(ext(0x3c0006,2,0x1234));
  const Device d=device_with(q);const Run x=drive(true,ram,s,d);same_as_manual(true,x,ram,s,d);
  assert(x.d.reads.size()==1&&x.d.reads[0].value==0x1234&&x.r.head_external_reads==7);}
 // Frames chained from each previous end state (the queue is declared per frame), driver against the harness chain.
 {Bytes ram=frame_ram(0xe74,"");State s=head_state(ram);Device d=device_with(frame_reads());Bytes mram(ram);State ms(s);Device md(d);
  for(unsigned int f=0;f<6;++f){
   d.reads=frame_reads();md.reads=frame_reads();const Bytes before=ram;const State sbefore=s;const Device dbefore=d;
   const Run x=drive(true,before,sbefore,dbefore);same_as_manual(true,x,before,sbefore,dbefore);
   Manual m;m.head_reads=0;m.node_reads=0;m.waits=0;manual_frame(mram,ms,md,m);
   ram=x.ram;s=x.s;d=x.d;assert(ram==mram&&same_state(s,ms)&&same_device(d,md));++checks;}
  assert(s.pc==0xe74);}
 // Declared releases. ef2 vblank: BYTE 100016 := BYTE 100017.
 {const Run x=frame_row("100017:05");assert(x.r.waits.size()==1);check_wait(x.r.waits[0],ms5::AnimationFrameHead,0xef2,0x100016,1,0,5);}
 // 16bd0 sprite flush: WORD (A5+d34) := D0.W; D0 is set by the head, the released value is its low WORD.
 {const Run x=frame_row("108d34:0001");assert(x.r.waits.size()==1&&x.r.waits[0].pc==0x16bd0&&x.r.waits[0].address==0x108d34&&x.r.waits[0].size==2&&
   x.r.waits[0].before==1&&x.r.waits[0].released==get(x.ram,0x108d34,2));}
 // Two waits in one head are both recorded in the head segment.
 {const Run x=frame_row("100017:03,108d34:0001");assert(x.r.waits.size()==2);
  for(std::size_t i=0;i<x.r.waits.size();++i)assert(x.r.waits[i].segment==ms5::AnimationFrameHead);}
 // 3aea sound ring (N): WORD 104d74 := ffff. Node 3 (100a6c) runs the 3ac8 callback with a full ring.
 {const Run x=frame_row("100a6c:00003ac8,104d76:0000,104d74:0001",5);assert(x.r.waits.size()==1);
  check_wait(x.r.waits[0],ms5::AnimationFrameNodes,0x3aea,0x104d74,2,1,0xffff);}
 // The same through the pass entry.
 {Bytes ram=frame_ram(0xe74,"100a6c:00003ac8,104d76:0000,104d74:0001");State s=pass_state();s.d[0]=5;const Device d=device_with(frame_reads());
  const Run x=drive(false,ram,s,d);same_as_manual(false,x,ram,s,d);assert(x.r.waits.size()==1&&x.r.waits[0].pc==0x3aea);}
 // cda4 sprite queue (N): WORD 108d34 := D4.W, from the 480bc frame helper of node 3 with the sprite queue declared.
 {const Bytes ram=bc_ram();const State s=pass_state();const Device d=device_with(frame_reads());const Run x=drive(false,ram,s,d);
  same_as_manual(false,x,ram,s,d);assert(x.r.waits.size()==1);check_wait(x.r.waits[0],ms5::AnimationFrameNodes,0xcda4,0x108d34,2,2,4);
  assert(get(x.ram,0x108d34,2)==4);}
}
// Failure rows: the checked error with ram, state, device (queue) and result untouched.
void errors(){
 const Bytes ram=frame_ram(0xe74,"");const State head=head_state(ram);const Device d=device_with(frame_reads());
 const State pass=pass_state();
 // Head callback other than e4a / e74.
 const std::uint32_t bad[]={0x270e,0x2ac2,0xc52a,0,0xe4b,0xe76};
 for(unsigned int i=0;i<sizeof(bad)/sizeof(bad[0]);++i){
  Bytes bad_ram=frame_ram(0xe74,"");put(bad_ram,HEAD,4,bad[i]);State bad_head=head;bad_head.pc=bad[i];
  reject(ms5::step_animation_machine_frame,bad_ram,bad_head,d,"animation frame head callback unsupported");
  reject(ms5::run_animation_machine_pass,bad_ram,pass,d,"animation frame head callback unsupported");}
 // Head entry mismatch: PC, A6, A7 and the return LONG.
 {State s=head;s.pc=0xe4a;reject(ms5::step_animation_machine_frame,ram,s,d,"animation frame head entry mismatch");}
 {State s=head;s.pc=0x2ac2;reject(ms5::step_animation_machine_frame,ram,s,d,"animation frame head entry mismatch");}
 {State s=head;s.a[6]=CONTROLLER;reject(ms5::step_animation_machine_frame,ram,s,d,"animation frame head entry mismatch");}
 {State s=head;s.a[7]=SPD;reject(ms5::step_animation_machine_frame,ram,s,d,"animation frame head entry mismatch");}
 {State s=head;s.a[7]=SPD-8;reject(ms5::step_animation_machine_frame,ram,s,d,"animation frame head entry mismatch");}
 {Bytes r=ram;put(r,SPD-4,4,0x2ac6);reject(ms5::step_animation_machine_frame,r,head,d,"animation frame head entry mismatch");}
 // A pass start is not a head start and the other way round.
 reject(ms5::step_animation_machine_frame,ram,pass,d,"animation frame head entry mismatch");
 reject(ms5::run_animation_machine_pass,ram,head,d,"animation frame pass entry mismatch");
 // Pass entry mismatch: PC, A6, A7.
 {State s=pass;s.pc=0x2ab8;reject(ms5::run_animation_machine_pass,ram,s,d,"animation frame pass entry mismatch");}
 {State s=pass;s.a[6]=HEAD;reject(ms5::run_animation_machine_pass,ram,s,d,"animation frame pass entry mismatch");}
 {State s=pass;s.a[7]=SPD-4;reject(ms5::run_animation_machine_pass,ram,s,d,"animation frame pass entry mismatch");}
 // Head boundary mismatch: the controller LONG equals the head callback, so H stops at once with A6 = 100820.
 {Bytes r=frame_ram(0xe74,"1008e4:00000e74");reject(ms5::step_animation_machine_frame,r,head_state(r),d,"animation frame head boundary mismatch");}
 // Pass boundary mismatch: another node carries the callback e74, so the pass stops there (A6 = 100a6c).
 {Bytes r=frame_ram(0xe74,"100a6c:00000e74");reject(ms5::run_animation_machine_pass,r,pass,d,"animation frame pass boundary mismatch");
  // ... also in the N segment of a frame, after the head segment succeeded (the head work is rolled back).
  reject(ms5::step_animation_machine_frame,r,head_state(r),d,"animation frame pass boundary mismatch");}
 // Declared reads missing or different: H fails (nothing consumed, nothing written).
 {Device e=device_with(std::vector<ms5::AnimationMachineExternalRead>());
  reject(ms5::step_animation_machine_frame,ram,head,e,"animation machine external read queue empty");
  std::vector<ms5::AnimationMachineExternalRead> q=frame_reads();q[2]=ext(0x300000,1,0xff);
  reject(ms5::step_animation_machine_frame,ram,head,device_with(q),"animation machine external read queue mismatch");}
 // An N failure after the head segment succeeded rolls the head back (ram, PVC, queue): node 3 runs an unsupported callback.
 {Bytes r=frame_ram(0xe74,"100a6c:0010fe40");reject(ms5::step_animation_machine_frame,r,head_state(r),d,"unsupported animation machine PC");
  reject(ms5::run_animation_machine_pass,r,pass,d,"unsupported animation machine PC");}
}
}
int main(){
 pass_and_frames();errors();
 std::cout<<"animation machine frame: "<<checks<<" checks\n";
 return 0;
}
