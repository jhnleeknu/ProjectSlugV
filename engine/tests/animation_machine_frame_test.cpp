#include "ms5/animation_machine_frame.h"
#include "../src/animation_machine_frame_internal.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
// Frame driver (H + declared controller skip or executed controller + N) through run_animation_machine only. All inputs are declared fixtures: the
// static scheduler list (8 nodes from 100820 at c4 steps: callback e4a / e74, c52a, six 270e; sentinel 100e98; free pool
// from 100f5c; LONG 104ca4 = SPd), the frame head state (PC = LONG (100820), A6 100820, A7 1feffc, LONG (1feffc) = 2ac2), the
// declared raster / input reads per frame and synthetic typed physical bytes (not ROM data): the 16-byte table b58..b68 read by
// b98 and the banner window bytes at 100024 / 200004 .. 200900 read by the sprite writers. The expected values are the
// harness chaining of run_animation_machine calls (manual_pass / manual_frame / manual_execute below), not an external oracle. The
// controller Execute rows (D9) run the routed controller code itself (C3a c52a / c560, fade card c364, cleanup 2a00 / 2a02); the
// BIOS boundary rows use the internal segment function run_animation_frame_segment from declared BIOS-entry states.
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
  a.node_external_reads==b.node_external_reads&&a.controller_exit_pc==b.controller_exit_pc&&same_ports(a.controller_ports,b.controller_ports)&&
  a.controller_external_reads==b.controller_external_reads;}
ms5::AnimationFrameResult sentinel_result(){
 ms5::AnimationFrameResult r;r.head_pc=1;r.controller_pc=2;r.pass_stop_pc=3;r.head_external_reads=4;r.node_external_reads=5;
 r.controller_exit_pc=10;r.controller_external_reads=11;
 ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;r.head_ports.push_back(p);r.node_ports.push_back(p);r.controller_ports.push_back(p);
 ms5::AnimationFrameWait w;w.segment=ms5::AnimationFrameNodes;w.pc=9;w.address=8;w.size=1;w.before=7;w.released=6;r.waits.push_back(w);return r;}
typedef bool (*FrameFunction)(std::vector<std::uint8_t>&,const std::vector<ms5::FixedDataResource>&,const ms5::ProgramBusState&,
 State&,Device&,std::uint8_t,const ms5::AnimationFrameOptions&,ms5::AnimationFrameResult&,std::string&);
// Failure: the checked error, and ram / state / device (pvc, bank, reads) / result exactly unchanged.
void reject(FrameFunction f,const Bytes& ram_in,const State& s_in,const Device& d_in,const char* message,bool card_resume=false,bool execute=false){
 Bytes ram(ram_in);State s(s_in);Device d(d_in);ms5::AnimationFrameResult r=sentinel_result();const ms5::AnimationFrameResult r0=sentinel_result();
 std::vector<ms5::FixedDataResource> w;const ms5::ProgramBusState bus=bus_of();std::string error;
 ms5::AnimationFrameOptions options;options.card_resume=card_resume;
 if(execute)options.controller_mode=ms5::AnimationFrameControllerExecute;
 const bool ok=f(ram,w,bus,s,d,0,options,r,error);
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
 manual_segment(ram,s,d,stop,m.node_ports,m.node_reads,m.waits);
 s.carry=ms5::AnimationCarryUnknown;}  // declared frame boundary (D1 amendment): the pass end reports C Unknown
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
Run drive(bool frame,const Bytes& ram,const State& s,const Device& d,bool card_resume=false,std::uint8_t answer=0x80,bool execute=false){
 Run x;x.ram=ram;x.s=s;x.d=d;x.ok=false;const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;
 ms5::AnimationFrameOptions options;options.card_resume=card_resume;options.card_answer=answer;
 if(execute)options.controller_mode=ms5::AnimationFrameControllerExecute;
 if(frame)x.ok=ms5::step_animation_machine_frame(x.ram,w,bus,x.s,x.d,0,options,x.r,x.error);
 else x.ok=ms5::run_animation_machine_pass(x.ram,w,bus,x.s,x.d,0,options,x.r,x.error);
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
 // Declared frame boundary (D1 amendment, P2 carry): the last node (node 7 = 100d7c) returns a known C through the C-preserving
 // dispatcher (2908 ORI #1,CCR; 290c RTS = Set, 290e ANDI #fe,CCR; 2916 RTS = Clear). The raw run reaches the head e74 with that C;
 // the pass and the frame report C Unknown (old behaviour: the known C, as in io-ext2 D1 frame 295 / D2 frame 481 via ea9f8 / ea9fe).
 {const char* puts[2]={"100d7c:00002908","100d7c:0000290e"};
  const ms5::AnimationCarryState raw[2]={ms5::AnimationCarrySet,ms5::AnimationCarryClear};
  for(unsigned int i=0;i<2;++i){
   const Bytes ram=frame_ram(0xe74,puts[i]);const State s=pass_state();const Device d=device_with(frame_reads());
   {Bytes mram(ram);State ms(s);Device md(d);Ports p;std::uint32_t n=0;unsigned int w=0;manual_segment(mram,ms,md,0xe74,p,n,w);
    assert(ms.pc==0xe74&&ms.a[6]==HEAD&&ms.carry==raw[i]);++checks;}
   const Run x=drive(false,ram,s,d);same_as_manual(false,x,ram,s,d);assert(x.s.carry==ms5::AnimationCarryUnknown);
   const Run y=frame_row(puts[i]);assert(y.s.carry==ms5::AnimationCarryUnknown);}}
}
// Declared BIOS card request: node 3 runs the fade card block c364 (pushes A6, JSR c00468 at c376).
void card(){
 const Bytes ram=frame_ram(0xe74,"100a6c:0000c364");const State pass=pass_state();const Device d=device_with(frame_reads());
 // Without card_resume the BIOS PC is the original checked error, with full preservation.
 reject(ms5::run_animation_machine_pass,ram,pass,d,"unsupported animation machine PC");
 reject(ms5::step_animation_machine_frame,ram,head_state(ram),d,"unsupported animation machine PC");
 // With card_resume the request is answered: BYTE 10fdc6 := answer, resume at c37c, the pass goes on to the head.
 const std::uint8_t answers[]={0x80,0x01};
 for(unsigned int i=0;i<2;++i){
  const Run x=drive(false,ram,pass,d,true,answers[i]);
  assert(x.r.waits.size()==1&&x.s.pc==0xe74&&get(x.ram,0x10fdc6,1)==answers[i]);
  check_wait(x.r.waits[0],ms5::AnimationFrameNodes,0xc00468,0x10fdc6,1,0,answers[i]);
  assert(get(x.ram,0x10fdc4,1)==1&&get(x.ram,0x10fdce,2)==0x268);}
 {const Run x=drive(true,ram,head_state(ram),d,true,0x80);assert(x.r.waits.size()==1&&x.r.waits[0].segment==ms5::AnimationFrameNodes&&x.r.waits[0].pc==0xc00468);}
 // card_resume with a failure that is not a card request keeps the original error and preserves everything.
 {Bytes r=frame_ram(0xe74,"100a6c:0010fe40");
  reject(ms5::run_animation_machine_pass,r,pass,d,"unsupported animation machine PC",true);
  reject(ms5::step_animation_machine_frame,r,head_state(r),d,"unsupported animation machine PC",true);}
 {Device e=device_with(std::vector<ms5::AnimationMachineExternalRead>());
  reject(ms5::step_animation_machine_frame,ram,head_state(ram),e,"animation machine external read queue empty",true);}
 // Without a failure card_resume changes nothing.
 {const Bytes plain=frame_ram(0xe74,"");const State h=head_state(plain);const Run a=drive(true,plain,h,d,false);const Run b=drive(true,plain,h,d,true);
  assert(a.ram==b.ram&&same_state(a.s,b.s)&&same_device(a.d,b.d)&&same_result(a.r,b.r));}
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
// ---- controller Execute mode (D9) and the segment BIOS boundaries
// Harness-style manual frame with the controller executed: H to LONG (1008e4), C to 2ac2, N.
void manual_execute(Bytes& ram,State& s,Device& d,Manual& m,Ports& controller_ports,std::uint32_t& controller_reads){
 const std::uint32_t controller=get(ram,CONTROLLER,4);
 manual_segment(ram,s,d,controller,m.head_ports,m.head_reads,m.waits);
 manual_segment(ram,s,d,0x2ac2,controller_ports,controller_reads,m.waits);
 manual_pass(ram,s,d,m);}
Run execute_row(const Bytes& ram,const State& s,const Device& d){
 const Run x=drive(true,ram,s,d,false,0x80,true);
 Bytes mram(ram);State ms(s);Device md(d);Manual m;m.head_reads=0;m.node_reads=0;m.waits=0;Ports cp;std::uint32_t cr=0;
 manual_execute(mram,ms,md,m,cp,cr);
 assert(x.ram==mram&&same_state(x.s,ms)&&same_device(x.d,md)&&same_ports(x.r.head_ports,m.head_ports)&&same_ports(x.r.node_ports,m.node_ports)&&
  same_ports(x.r.controller_ports,cp)&&x.r.controller_external_reads==cr&&x.r.head_external_reads==m.head_reads&&x.r.node_external_reads==m.node_reads&&
  x.r.waits.size()==m.waits);
 assert(x.r.controller_pc==get(ram,CONTROLLER,4)&&x.r.controller_exit_pc==get(x.ram,CONTROLLER,4)&&x.s.pc==get(x.ram,HEAD,4)&&x.s.a[6]==HEAD&&
  x.s.a[7]==SPD-4&&x.s.carry==ms5::AnimationCarryUnknown);
 ++checks;return x;}
void controller_execute(){
 const Device d=device_with(frame_reads());
 // Frame with the boot controller c52a executed (C3a): boot fill (PVC bank 200000 select twice), WORD 107dea := 2000, callback c560.
 const Bytes ram=frame_ram(0xe74,"1008e4:0000c52a,10095a:ffff,10095c:ffff,10095e:ffff,100960:ffff,100962:ffff,100964:ffffffff,100968:ff");
 const State h=head_state(ram);
 const Run a=execute_row(ram,h,d);
 assert(a.r.controller_pc==0xc52a&&a.r.controller_exit_pc==0xc560&&a.r.controller_ports.size()==4&&get(a.ram,0x107dea,2)==0x2000&&
  get(a.ram,0x10095a,4)==0&&get(a.ram,0x10095e,4)==0&&get(a.ram,0x100962,2)==0&&get(a.ram,0x100964,2)==0&&get(a.ram,0x100966,1)==0xff&&
  get(a.ram,0x100967,1)==0&&get(a.ram,0x100968,1)==0xff&&get(a.ram,0x100010,2)==0&&a.r.controller_external_reads==0);
 for(unsigned int i=0;i<4;++i)assert(a.r.controller_ports[i].address==(i%2==0?0x2ffff2U:0x2ffff0U)&&a.r.controller_ports[i].size==2&&
  a.r.controller_ports[i].value==(i%2==0?0x1000U:0U));
 // The next frame runs the wait callback c560 (107dea = 2000, no port), then again.
 {Device d2=a.d;d2.reads=frame_reads();const Run b=execute_row(a.ram,a.s,d2);
  assert(b.r.controller_pc==0xc560&&b.r.controller_exit_pc==0xc560&&b.r.controller_ports.empty()&&get(b.ram,SPD-8,4)==0xc566);
  // Skip / Execute: with c560 the controller changes only the stack LONG below SPd - 4 and D0.W; N gives the same ports, waits and reads.
  Device d3=a.d;d3.reads=frame_reads();const Run k=drive(true,a.ram,a.s,d3);
  assert(k.r.controller_exit_pc==0&&k.r.controller_ports.empty()&&same_ports(k.r.node_ports,b.r.node_ports)&&same_ports(k.r.head_ports,b.r.head_ports)&&
   same_waits(k.r.waits,b.r.waits)&&k.r.node_external_reads==b.r.node_external_reads&&same_device(k.d,b.d));
  for(unsigned int i=0;i<65536;++i)if(k.ram[i]!=b.ram[i])assert(i>=((SPD-8)&65535U)&&i<((SPD-4)&65535U));
  ++checks;
  // WORD 107dea = 0 opens the wait: C reaches c56e (C3b, routed) and the palette bind e7bf4 needs ROM data this frame bus does not carry ->
  // the checked error of the program bus, everything preserved.
  Bytes open(b.ram);put(open,0x107dea,2,0);Device d4=b.d;d4.reads=frame_reads();
  reject(ms5::step_animation_machine_frame,open,b.s,d4,"missing or ambiguous physical program bus ROM byte",false,true);}
 // Skip mode never runs the controller (the boot fill is not done).
 {const Run k=drive(true,ram,h,d);assert(k.r.controller_pc==0xc52a&&k.r.controller_exit_pc==0&&k.r.controller_ports.empty()&&get(k.ram,0x107dea,2)==0);}
 // A declared release inside C: the controller c364 (fade card) reaches the BIOS card request: card_resume answers it (segment 2).
 {const Bytes cr=frame_ram(0xe74,"1008e4:0000c364");const State ch=head_state(cr);
  reject(ms5::step_animation_machine_frame,cr,ch,d,"unsupported animation machine PC",false,true);
  Run x=drive(true,cr,ch,d,true,0x80,true);
  assert(x.r.waits.size()==1&&x.r.controller_exit_pc==0xc364&&get(x.ram,0x100946,1)==0xff);
  check_wait(x.r.waits[0],ms5::AnimationFrameController,0xc00468,0x10fdc6,1,0,0x80);
  // answer 01: c38e clears 62(A6) and allocates the card child c250 (parent 1008e4) from the free pool; N runs it the same frame.
  x=drive(true,cr,ch,d,true,0x01,true);
  assert(x.r.waits.size()==1&&x.r.waits[0].released==1&&get(x.ram,0x100946,1)==0&&get(x.ram,POOL0+0xc,4)==CONTROLLER&&get(x.ram,POOL0,4)!=0);}
 // Controller system return: the controller LONG c00444 (the BIOS JMP target) is a checked, preserving failure.
 {const Bytes sr=frame_ram(0xe74,"1008e4:00c00444");
  reject(ms5::step_animation_machine_frame,sr,head_state(sr),d,"animation frame controller system return",false,true);
  reject(ms5::step_animation_machine_frame,sr,head_state(sr),d,"animation frame controller system return",true,true);
  // Skip mode skips it (the controller is never entered).
  const Run k=drive(true,sr,head_state(sr),d);assert(k.r.controller_pc==0xc00444);}
 // Controller boundary: 2a02 sets A7 := LONG 104ca4 and goes to 2ac2 (a valid end when LONG 104ca4 = SPd, otherwise A7 mismatch).
 {const Bytes ok=frame_ram(0xe74,"1008e4:00002a02");const Run x=execute_row(ok,head_state(ok),d);assert(x.r.controller_exit_pc==0x2a02);
  const Bytes bad=frame_ram(0xe74,"1008e4:00002a02,104ca4:001feff8");
  reject(ms5::step_animation_machine_frame,bad,head_state(bad),d,"animation frame controller boundary mismatch",false,true);}
 // Controller LONG 2ac2: H itself stops at its own RTS target (A6 = 100820), in both modes.
 {const Bytes r=frame_ram(0xe74,"1008e4:00002ac2");
  reject(ms5::step_animation_machine_frame,r,head_state(r),d,"animation frame head boundary mismatch",false,true);
  reject(ms5::step_animation_machine_frame,r,head_state(r),d,"animation frame head boundary mismatch");}
 // Controller 2a00 (cleanup 299c resets the node callback to 270e, then A7 := LONG 104ca4 and 2ac2): a valid end.
 {const Bytes r=frame_ram(0xe74,"1008e4:00002a00");const Run x=execute_row(r,head_state(r),d);
  assert(x.r.controller_exit_pc==0x270e&&get(x.ram,CONTROLLER,4)==0x270e);}
 // Unsupported controller PC (work RAM) in Execute; the same frame in Skip mode succeeds.
 {const Bytes r=frame_ram(0xe74,"1008e4:0010fe00");
  reject(ms5::step_animation_machine_frame,r,head_state(r),d,"unsupported animation machine PC",true,true);
  const Run k=drive(true,r,head_state(r),d);assert(k.r.controller_pc==0x10fe00);}
}
// The segment function alone (internal API): declared BIOS boundaries by segment.
struct Seg {bool ok;std::string error;Bytes ram;State s;std::vector<ms5::AnimationFrameWait> waits;Ports ports;std::uint32_t reads;};
Seg segment(const Bytes& ram_in,std::uint32_t pc,std::uint32_t ret,std::uint32_t stop,ms5::AnimationFrameSegment seg,const ms5::AnimationFrameOptions& o){
 Seg x;x.ram=ram_in;x.reads=0;x.s=State();x.s.pc=pc;x.s.a[5]=0x108000;x.s.a[6]=CONTROLLER;x.s.a[7]=0x10f000;put(x.ram,0x10f000,4,ret);
 Device d=device_with(std::vector<ms5::AnimationMachineExternalRead>());const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;
 x.ok=ms5::run_animation_frame_segment(x.ram,w,bus,x.s,d,0,o,stop,seg,x.ports,x.waits,x.reads,x.error);return x;}
void bios_segments(){
 const Bytes ram=frame_ram(0xe74,"10fdc6:33,10fdb0:44556677");
 ms5::AnimationFrameOptions card;card.card_resume=true;card.card_answer=0x5a;
 ms5::AnimationFrameOptions none;
 ms5::AnimationFrameOptions credit;credit.credit_resume=true;credit.credit_answer=0x01020304;
 const ms5::AnimationFrameSegment segs[3]={ms5::AnimationFrameHead,ms5::AnimationFrameNodes,ms5::AnimationFrameController};
 for(unsigned int i=0;i<3;++i){
  // card c37c: every segment with card_resume.
  Seg x=segment(ram,0xc00468,0xc37c,0xc37c,segs[i],card);
  assert(x.ok&&x.s.pc==0xc37c&&x.s.a[7]==0x10f004&&get(x.ram,0x10fdc6,1)==0x5a&&x.waits.size()==1&&x.s.carry==ms5::AnimationCarryUnknown);
  check_wait(x.waits[0],segs[i],0xc00468,0x10fdc6,1,0x33,0x5a);
  x=segment(ram,0xc00468,0xc37c,0xc37c,segs[i],none);assert(!x.ok&&x.error=="unsupported animation machine PC"&&x.waits.empty());
  // card c316 (C2 c310): only in the controller segment.
  x=segment(ram,0xc00468,0xc316,0xc316,segs[i],card);
  if(i==2){assert(x.ok&&x.s.pc==0xc316&&x.s.a[7]==0x10f004&&get(x.ram,0x10fdc6,1)==0x5a);check_wait(x.waits[0],segs[i],0xc00468,0x10fdc6,1,0x33,0x5a);}
  else assert(!x.ok&&x.error=="unsupported animation machine PC"&&x.waits.empty());
  // card with another return: the original error.
  x=segment(ram,0xc00468,0xc318,0xc318,segs[i],card);assert(!x.ok&&x.error=="unsupported animation machine PC");
  // credit c00450 -> 4a992: controller segment with credit_resume only.
  x=segment(ram,0xc00450,0x4a992,0x4a992,segs[i],credit);
  if(i==2){assert(x.ok&&x.s.pc==0x4a992&&x.s.a[7]==0x10f004&&get(x.ram,0x10fdb0,4)==0x01020304&&x.waits.size()==1);
   check_wait(x.waits[0],segs[i],0xc00450,0x10fdb0,4,0x44556677,0x01020304);}
  else assert(!x.ok&&x.error=="unsupported animation machine PC");
  x=segment(ram,0xc00450,0x4a992,0x4a992,segs[i],none);assert(!x.ok&&x.error=="unsupported animation machine PC");
  x=segment(ram,0xc00450,0x4a998,0x4a998,segs[i],credit);assert(!x.ok&&x.error=="unsupported animation machine PC");
  // c00444: the controller system return (no resume); other segments keep the original error.
  x=segment(ram,0xc00444,0x2ac2,0x2ac2,segs[i],card);
  assert(!x.ok&&x.error==(i==2?"animation frame controller system return":"unsupported animation machine PC")&&x.waits.empty());
  ++checks;}
 // Code path to the request (c364 pushes A6, JSR c00468, the resume c37c pops A6 and RTS): the segment from c364 to 2ac2.
 {Seg x=segment(frame_ram(0xe74,""),0xc364,0x2ac2,0x2ac2,ms5::AnimationFrameController,card);
  assert(x.ok&&x.waits.size()==1&&x.s.pc==0x2ac2&&x.s.a[7]==0x10f004&&x.s.a[6]==CONTROLLER);++checks;}
}
// The external-read queue belongs to H only (E1 contract decision 2): C and N see an empty queue; the entries left by H stay queued.
// 2634 (E1, MOVE.B 300000.l,D0; ANDI.B #70; BNE 2648) reads the input BYTE; value 70 goes straight to 2648.
void held_queue(){
 std::vector<ms5::AnimationMachineExternalRead> one;one.push_back(ext(0x300000,1,0x70));
 const ms5::AnimationFrameSegment segs[3]={ms5::AnimationFrameHead,ms5::AnimationFrameNodes,ms5::AnimationFrameController};
 for(unsigned int i=0;i<3;++i){
  Bytes ram=frame_ram(0xe74,"");State s;s.pc=0x2634;s.a[5]=0x108000;s.a[6]=CONTROLLER;s.a[7]=0x10f000;Device d=device_with(one);
  const ms5::ProgramBusState bus=bus_of();std::vector<ms5::FixedDataResource> w;ms5::AnimationFrameOptions o;
  Ports ports;std::vector<ms5::AnimationFrameWait> waits;std::uint32_t reads=0;std::string error;
  const bool ok=ms5::run_animation_frame_segment(ram,w,bus,s,d,0,o,0x2648,segs[i],ports,waits,reads,error);
  if(i==0)assert(ok&&s.pc==0x2648&&(s.d[0]&255U)==0x70&&reads==1&&d.reads.empty());
  else assert(!ok&&error=="animation machine external read queue empty"&&reads==0&&same_reads(d,device_with(one)));
  ++checks;}
 // Frame, controller LONG 2634: H consumes its seven declared reads; the eighth entry is not served to C (checked, everything preserved).
 // Skip mode never enters 2634 and leaves the entry queued.
 {std::vector<ms5::AnimationMachineExternalRead> q=frame_reads();q.push_back(ext(0x300000,1,0x70));const Device d=device_with(q);
  const Bytes ram=frame_ram(0xe74,"1008e4:00002634");
  reject(ms5::step_animation_machine_frame,ram,head_state(ram),d,"animation machine external read queue empty",false,true);
  const Run k=drive(true,ram,head_state(ram),d);assert(k.r.controller_pc==0x2634&&k.d.reads.size()==1&&k.d.reads[0].address==0x300000);++checks;}
 // Pass, node callback 2634 (static node 2): N is not served the queued entry either.
 {const Bytes ram=frame_ram(0xe74,"1009a8:00002634");
  reject(ms5::run_animation_machine_pass,ram,pass_state(),device_with(one),"animation machine external read queue empty");}
}
// ---- IRQ execution (F6-D, options.irq_execution; scope decisions E1-E4, E7, E10)
// Declared vectors (only vector 64 = 20c is used) and the P2-style IRQ prep of the frame fixture: 10fd80 bit 7 (game mode), raster
// callback 3dcc, empty task queue, 10001b bit 7 = 0 (the IRQ runs the service, credit and sound/Z80 parts, not the render part).
Bytes irq_vectors(){Bytes v(128,0);put(v,0x64,4,0x20c);return v;}
const Bytes VECTORS=irq_vectors();
const char* const IRQ_PREP="10fd80:80,100006:00003dcc,10000a:00003dcc,10081c:0010081c,10001b:00";
struct IrqRun {bool ok;std::string error;Bytes ram;State s;Device d;ms5::AnimationMachinePaletteRam pal;ms5::AnimationFrameResult r;};
IrqRun irq_drive(bool frame,const Bytes& ram,const State& s,const Device& d,const ms5::AnimationFrameOptions& o,bool vectors=true,bool palette=true){
 IrqRun x;x.ram=ram;x.s=s;x.d=d;x.pal.banks[0][0x10]=0x5a;x.pal.selected=1;
 ms5::ProgramBusState bus=bus_of();if(vectors)bus.vectors=&VECTORS;std::vector<ms5::FixedDataResource> w;
 if(palette)x.ok=frame?ms5::step_animation_machine_frame(x.ram,w,bus,x.s,x.d,x.pal,0,o,x.r,x.error):ms5::run_animation_machine_pass(x.ram,w,bus,x.s,x.d,x.pal,0,o,x.r,x.error);
 else x.ok=frame?ms5::step_animation_machine_frame(x.ram,w,bus,x.s,x.d,0,o,x.r,x.error):ms5::run_animation_machine_pass(x.ram,w,bus,x.s,x.d,0,o,x.r,x.error);
 return x;}
ms5::AnimationFrameOptions irq_options(std::uint8_t z80=0,std::uint16_t video=0){
 ms5::AnimationFrameOptions o;o.irq_execution=true;o.irq_z80_reply=z80;o.irq_video_status=video;return o;}
// Independent harness chain of one IRQ at a Waiting state: push frame, run to c0044a, declared resume, run to the wait PC.
void manual_irq(Bytes& ram,State& s,Device& d,ms5::AnimationMachinePaletteRam& pal,std::uint8_t z80,std::uint16_t video,Ports& ports,std::uint32_t& reads){
 ms5::ProgramBusState bus=bus_of();bus.vectors=&VECTORS;std::vector<ms5::FixedDataResource> w;const State pre=s;
 put(ram,s.a[7]-4,4,s.pc);put(ram,s.a[7]-6,2,0x2000);s.a[7]-=6;s.pc=0x20c;s.carry=ms5::AnimationCarryUnknown;
 d.reads.insert(d.reads.begin(),ext(0x3c0006,2,video));d.reads.insert(d.reads.begin(),ext(0x320000,1,z80));
 ms5::AnimationMachineStatus st=ms5::AnimationMachineWaiting;std::string error;std::uint32_t n=0;
 Ports phase;bool ok=ms5::run_animation_machine_with_palette(ram,w,bus,s,d,pal,0xc0044a,0,n,st,phase,error);ports.insert(ports.end(),phase.begin(),phase.end());
 if(!ok)std::cerr<<"manual irq: "<<error<<"\n";
 assert(ok&&st==ms5::AnimationMachineReturned&&s.pc==0xc0044a&&get(ram,s.a[7],4)==0x248);reads+=n;n=0;
 s.pc=0x248;s.a[7]+=4;s.carry=ms5::AnimationCarryUnknown;
 ok=ms5::run_animation_machine_with_palette(ram,w,bus,s,d,pal,pre.pc,0,n,st,phase,error);ports.insert(ports.end(),phase.begin(),phase.end());
 assert(ok&&st==ms5::AnimationMachineReturned&&s.pc==pre.pc&&s.a[7]==pre.a[7]&&s.carry==ms5::AnimationCarryClear);reads+=n;}
void irq_rejected(bool frame,const Bytes& ram,const State& s,const Device& d,const ms5::AnimationFrameOptions& o,const char* message,bool vectors=true){
 const IrqRun x=irq_drive(frame,ram,s,d,o,vectors);IrqRun ref;ref.pal.banks[0][0x10]=0x5a;
 if(x.ok||x.error!=message)std::cerr<<"expected '"<<message<<"' got ok="<<x.ok<<" '"<<x.error<<"'\n";
 assert(!x.ok&&x.error==message&&x.ram==ram&&same_state(x.s,s)&&same_device(x.d,d)&&x.pal.banks[0]==ref.pal.banks[0]&&x.pal.banks[0][0x10]==0x5a&&
  x.pal.banks[1]==ref.pal.banks[1]&&x.pal.selected==1&&x.r.irqs.empty()&&x.r.irq_ports.empty()&&x.r.waits.empty());++checks;}
// Manual segment with IRQ delivery at the IRQ-effect waits (harness chaining, independent of the driver).
struct ManualIrq {Ports ports,irq_ports;std::uint32_t reads,irq_reads;unsigned int irqs;};
void manual_irq_segment(Bytes& ram,State& s,Device& d,ms5::AnimationMachinePaletteRam& pal,std::uint32_t stop,std::uint8_t z80,std::uint16_t video,ManualIrq& m){
 ms5::ProgramBusState bus=bus_of();bus.vectors=&VECTORS;std::vector<ms5::FixedDataResource> w;s.carry=ms5::AnimationCarryUnknown;
 for(unsigned int k=0;k<17;++k){
  std::uint32_t n=0;ms5::AnimationMachineStatus st=ms5::AnimationMachineReturned;std::string error;
  Ports phase;const bool ok=ms5::run_animation_machine_with_palette(ram,w,bus,s,d,pal,stop,0,n,st,phase,error);m.ports.insert(m.ports.end(),phase.begin(),phase.end());
  if(!ok)std::cerr<<"manual irq segment: "<<error<<"\n";
  assert(ok);m.reads+=n;
  if(st==ms5::AnimationMachineReturned)return;
  const std::size_t q=d.reads.size();manual_irq(ram,s,d,pal,z80,video,m.irq_ports,m.irq_reads);assert(d.reads.size()==q);++m.irqs;}
 assert(false);}
void irq_execution(){
 const std::uint8_t z80s[2]={0x37,0};const std::uint16_t videos[2]={8,0};
 // ef2 vblank (BYTE 100016 0 < BYTE 100017 2): two IRQs (the c98 saturating increment each) instead of the declared release; the driver
 // equals the manual chain (H with IRQs, the declared skip, N), the Z80 reply reaches BYTE 104d7c and video status bit 3 BYTE 100002.
 for(unsigned int v=0;v<2;++v){
  std::string puts=std::string(IRQ_PREP)+",100017:02";Bytes ram=frame_ram(0xe74,puts.c_str());const State s=head_state(ram);const Device d=device_with(frame_reads());
  const IrqRun x=irq_drive(true,ram,s,d,irq_options(z80s[v],videos[v]));
  if(!x.ok)std::cerr<<"irq frame: "<<x.error<<"\n";
  assert(x.ok&&x.r.waits.empty()&&x.r.irqs.size()==2&&x.d.reads.empty()&&x.r.head_external_reads==7);
  Bytes mram(ram);State ms(s);Device md(d);ms5::AnimationMachinePaletteRam mpal;mpal.banks[0][0x10]=0x5a;mpal.selected=1;ManualIrq hm,nm;
  hm.reads=hm.irq_reads=nm.reads=nm.irq_reads=0;hm.irqs=nm.irqs=0;
  manual_irq_segment(mram,ms,md,mpal,0xc52a,z80s[v],videos[v],hm);ms.pc=0x2ac2;ms.a[7]=SPD;manual_irq_segment(mram,ms,md,mpal,0xe74,z80s[v],videos[v],nm);
  ms.carry=ms5::AnimationCarryUnknown;
  assert(x.ram==mram&&same_state(x.s,ms)&&same_device(x.d,md)&&x.pal.banks[0]==mpal.banks[0]&&x.pal.banks[1]==mpal.banks[1]&&x.pal.selected==mpal.selected&&
   same_ports(x.r.head_ports,hm.ports)&&same_ports(x.r.node_ports,nm.ports)&&same_ports(x.r.irq_ports,hm.irq_ports)&&hm.irqs==2&&nm.irqs==0&&
   x.r.head_external_reads==hm.reads&&x.r.node_external_reads==nm.reads);
  std::uint32_t at=0;
  for(std::uint32_t k=0;k<2;++k){const ms5::AnimationFrameIrq& q=x.r.irqs[k];
   assert(q.segment==ms5::AnimationFrameHead&&q.wait_pc==0xef2&&q.sequence==k&&q.ports_begin==at&&q.ports_end>q.ports_begin&&q.external_reads==2&&
    q.bios_resumes==1&&q.rte_sr==0x2000);at=q.ports_end;}
  assert(at==x.r.irq_ports.size()&&x.r.irq_ports[0].address==0x3c000c&&x.r.irq_ports[0].size==2&&x.r.irq_ports[0].value==6);
  assert(get(x.ram,0x104d7c,1)==z80s[v]&&get(x.ram,0x100002,1)==(v==0?0xffU:0U));
  // Deterministic: the same call again gives the same outputs.
  const IrqRun y=irq_drive(true,ram,s,d,irq_options(z80s[v],videos[v]));
  assert(y.ok&&y.ram==x.ram&&same_state(y.s,x.s)&&same_ports(y.r.irq_ports,x.r.irq_ports)&&y.r.irqs.size()==2);++checks;}
 // irq_execution false (default): the palette overloads give exactly the declared-release results of the plain functions.
 {std::string puts=std::string(IRQ_PREP)+",100017:05";Bytes ram=frame_ram(0xe74,puts.c_str());const State s=head_state(ram);const Device d=device_with(frame_reads());
  ms5::AnimationFrameOptions off;const IrqRun a=irq_drive(true,ram,s,d,off,true,true);const IrqRun b=irq_drive(true,ram,s,d,off,true,false);
  assert(a.ok&&b.ok&&a.ram==b.ram&&same_state(a.s,b.s)&&same_device(a.d,b.d)&&same_result(a.r,b.r)&&a.r.irqs.empty()&&a.r.irq_ports.empty()&&
   a.r.waits.size()==1&&a.pal.banks[0][0x10]==0x5a&&a.pal.selected==1);
  check_wait(a.r.waits[0],ms5::AnimationFrameHead,0xef2,0x100016,1,0,5);
  const State p=pass_state();const IrqRun c=irq_drive(false,ram,p,d,off,true,true);const IrqRun e=irq_drive(false,ram,p,d,off,true,false);
  assert(c.ok&&e.ok&&c.ram==e.ram&&same_state(c.s,e.s)&&same_result(c.r,e.r));++checks;}
 // irq_execution without a palette device: the same IRQ results here (no palette access in this IRQ path).
 {std::string puts=std::string(IRQ_PREP)+",100017:01";Bytes ram=frame_ram(0xe74,puts.c_str());const State s=head_state(ram);const Device d=device_with(frame_reads());
  const IrqRun a=irq_drive(true,ram,s,d,irq_options(),true,true);const IrqRun b=irq_drive(true,ram,s,d,irq_options(),true,false);
  assert(a.ok&&b.ok&&a.ram==b.ram&&same_state(a.s,b.s)&&same_ports(a.r.irq_ports,b.r.irq_ports)&&a.r.irqs.size()==1&&b.r.irqs.size()==1);++checks;}
 // Checked errors with full preservation (ram, state, queue, palette, result).
 {std::string puts=std::string(IRQ_PREP)+",100017:02";const Bytes ram=frame_ram(0xe74,puts.c_str());const State s=head_state(ram);const Device d=device_with(frame_reads());
  // BYTE 10fd80 bit 7 = 0: 21e JMP c00438 (BIOS INT1 boundary).
  {Bytes r=ram;put(r,0x10fd80,1,0);irq_rejected(true,r,s,d,irq_options(),"animation irq bios int1 boundary");}
  // No vector table.
  irq_rejected(true,ram,s,d,irq_options(),"animation irq vector unavailable",false);
  // A wait the IRQ cannot release within 16 deliveries (100017 = 20: 32 increments needed).
  {Bytes r=ram;put(r,0x100017,1,0x20);irq_rejected(true,r,s,d,irq_options(),"animation irq wait not released");}
  // A raster callback that is not routed (LONG 100006 = 10fe40): the executor error inside the IRQ is returned as is.
  {Bytes r=ram;put(r,0x100006,4,0x10fe40);irq_rejected(true,r,s,d,irq_options(),"unsupported animation machine PC");}
  // Invalid palette RAM.
  {IrqRun x;x.ram=ram;x.s=s;x.d=d;x.pal.banks[1].resize(10);ms5::ProgramBusState bus=bus_of();bus.vectors=&VECTORS;std::vector<ms5::FixedDataResource> w;
   x.ok=ms5::step_animation_machine_frame(x.ram,w,bus,x.s,x.d,x.pal,0,irq_options(),x.r,x.error);
   assert(!x.ok&&x.error=="invalid animation machine palette RAM"&&x.ram==ram&&same_state(x.s,s)&&same_device(x.d,d)&&x.pal.banks[1].size()==10);
   x.ok=ms5::run_animation_machine_pass(x.ram,w,bus,x.s,x.d,x.pal,0,irq_options(),x.r,x.error);
   assert(!x.ok&&x.error=="invalid animation machine palette RAM");++checks;}}
 // N waits: cda4 (sprite queue) with 10001b bit 7 = 0 -- the IRQ does not run 16cfa, so the wait is never released.
 {Bytes ram=bc_ram();apply(ram,IRQ_PREP);irq_rejected(false,ram,pass_state(),device_with(frame_reads()),irq_options(),"animation irq wait not released");}
}
int main(){
 pass_and_frames();card();errors();controller_execute();bios_segments();held_queue();irq_execution();
 std::cout<<"animation machine frame: "<<checks<<" checks\n";
 return 0;
}
