#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
void put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes& b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out{ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::vector<ms5::PhysicalRomResource> physical;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o){ms5::ProgramBusState bus;bus.physical_rom=&o.physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,255,o.reads,o.status,o.ports,o.error);}
void table(Out&o){ms5::PhysicalRomResource r;r.source_rom_offset=0x4e272;r.data.assign(32,0);for(unsigned int i=0;i<16;++i)put(r.data,i*2,2,0xc900+i);o.physical.push_back(r);}
void reject(Bytes ram,ms5::AnimationMachineState s,const char*message,Out o=Out()){
 const Bytes old=ram;const ms5::AnimationMachineState before=s;const ms5::AnimationMachineDevice dev=o.dev;
 assert(!run(ram,s,STOP,o));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==old&&same(s,before)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base);
 assert(o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);
}
void preserving(){const std::uint32_t calls[][3]={{0x47c7a,0x4e286,0x47c80},{0x47c88,0x4843c,0x47c8c},{0x47c8c,0xca70,0x47c92},{0x4e2c8,0x3af8,0x4e2ce},{0x4e2ea,0x8cda,0x4e2f0},{0x4e30c,0x35f0,0x4e312}};
 const std::uint32_t returns[]={0x4e330,0x4847a,0x8cf2,0x8d32,0x3628};
 for(unsigned int flag=0;flag<3;++flag){const ms5::AnimationCarryState carry=static_cast<ms5::AnimationCarryState>(flag);
  for(unsigned int i=0;i<6;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(calls[i][0]);s.carry=carry;Out o;assert(run(ram,s,calls[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==calls[i][2]);}
  for(unsigned int i=0;i<5;++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(returns[i]);s.carry=carry;Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x35f0);s.carry=carry;Out o;assert(run(ram,s,0x35f6,o)&&s.carry==carry&&s.a[4]==0x3c0000);
 }
}
void bcd(){const unsigned int lows[]={0,1,2,255};
 for(unsigned int hi=0;hi<256;++hi)for(unsigned int j=0;j<4;++j){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10d683,1,16);put(ram,0x10fdb6,1,1);put(ram,0x10d67e,2,(hi<<8)|lows[j]);
  ms5::AnimationMachineState s=state(0x4843c),want=s;Bytes expected=ram;unsigned int low=(lows[j]-2)&255U,high=hi;
  want.d[0]=(want.d[0]&0xffffff00U)|low;want.d[1]=(want.d[1]&0xffffff00U)|high;want.d[2]=0;
  if(lows[j]<2){if(!hi){low=high=0;want.d[0]=want.d[1]=0;}else{high=(hi-((hi&15)?1:7))&255U;want.d[1]=(want.d[1]&0xffffff00U)|high;}}
  put(expected,0x10d67e,1,high);put(expected,0x10d67f,1,low);want.pc=STOP;want.a[7]+=4;want.carry=ms5::AnimationCarryUnknown;
  Out o;assert(run(ram,s,STOP,o)&&same(s,want)&&ram==expected&&o.ports.empty());
 }
 for(unsigned int gate=0;gate<2;++gate)for(unsigned int p=0;p<3;++p){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10d683,1,gate?16:0);put(ram,0x10fdb6,1,p);put(ram,0x10fdb7,1,2);ms5::AnimationMachineState s=state(0x4843c);Out o;assert(run(ram,s,STOP,o));}
}
void palette(){const unsigned int weights[]={0,31,32,255};
 for(unsigned int ref=0;ref<2;++ref)for(unsigned int w=0;w<4;++w)for(unsigned int target=0;target<2;++target)for(unsigned int current=0;current<2;++current){
  Bytes ram(65536,0);put(ram,SP,4,STOP);const std::uint32_t node=0x104e52;put(ram,node+8,2,ref);put(ram,node+12,2,target?0x1234:0);put(ram,node+10,2,current?0x1234:0);put(ram,node+14,1,7);put(ram,node+15,1,0x21);
  ms5::AnimationMachineState s=state(0x8cda);s.d[0]=0xabcdff0c;s.d[1]=0x89ab1234;s.d[2]=0xabcdef00|weights[w];const std::uint32_t d2=s.d[2];Out o;
  assert(run(ram,s,STOP,o)&&s.d[0]==0xabcd00c0&&s.a[1]==0x104d92&&s.a[2]==node);
  assert(s.d[2]==(ref&&weights[w]>=32?32:d2));
  if(ref){assert(get(ram,node+12,2)==0x1234&&get(ram,node+14,1)==(weights[w]>=32?32:weights[w]));assert(get(ram,node+15,1)==((!target||!current)?0xa1:0x21));}
  else assert(get(ram,node+12,2)==(target?0x1234:0)&&get(ram,node+14,1)==7);
 }
 Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x8cda);s.d[0]=12;s.d[1]=0x1234;s.d[2]=32;s.a[7]=0x104e5e;put(ram,0x104e5a,2,1);put(ram,s.a[7],4,STOP);Out o;
 assert(run(ram,s,0x12342080,o)&&s.pc==0x12342080&&s.a[7]==0x104e62); // Target/weight/dirty writes change actual RTS LONG.
}
void rectangle(){
 for(unsigned int width=1;width<=4;++width)for(unsigned int height=1;height<=3;++height){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x35f0);s.d[0]=0xabcd7243;s.d[1]=0x89abc9f8;s.d[2]=0xaaaa0000|width;s.d[3]=height;Out o;
  assert(run(ram,s,STOP,o)&&o.ports.size()==width*height+1&&s.a[4]==0x3c0000&&(s.d[2]&65535U)==0&&(s.d[6]&65535U)==0);
  for(unsigned int x=0;x<width;++x)for(unsigned int y=0;y<height;++y){const ms5::VideoPortWrite&p=o.ports[x*height+y];assert(p.address==0x3c0000&&p.size==4&&p.value==(((0x7243+x*32+y)<<16)|0xc900U|((0xf8+x+y*16)&255U)));}
  assert(o.ports.back().size==2&&o.ports.back().value==0x8200);
 }
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x35fe);s.a[4]=0x1f4000;s.d[7]=0x12345678;s.d[6]=1;s.d[2]=1;Out o;
 assert(run(ram,s,STOP,o)&&get(ram,0x104000,4)==0x82005678&&o.ports.empty());
}
void hud(){
 for(unsigned int high=0;high<0x9a;++high){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10dd1f,1,1);put(ram,0x10dd20,1,1);ms5::AnimationMachineState s=state(0x4e286);s.d[0]=0xabcd0000|(high<<8)|0x2f;Out o;table(o);
  assert(run(ram,s,STOP,o)&&o.ports.size()==10&&s.a[7]==SP+4&&s.d[0]==(((high>>4)*2)<<16|0x72c3));
  assert(o.ports[0].size==4&&o.ports[0].value==(0x72430000U|0xc900U|(high>>4)));
  assert(o.ports[5].size==4&&o.ports[5].value==(0x72830000U|0xc900U|(high&15)));
 }
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10dd1f,1,1);ms5::AnimationMachineState s=state(0x4e286);s.d[0]=0xffff9a00;Out o;
 assert(run(ram,s,STOP,o)&&o.ports.size()==9&&s.d[0]==0xffff72c3&&o.ports[0].value==0x7243c904);
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0x4e286);ms5::AnimationMachineState want=s;want.pc=STOP;want.a[7]+=4;want.carry=ms5::AnimationCarryUnknown;
 assert(run(ram,s,STOP,o)&&same(s,want)&&o.ports.empty());
 // Saved HUD WORD and sound low BYTE remain live RAM across a high-byte wait.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x10dd1f,1,1);put(ram,0x104d8c,2,6);put(ram,0x104d82,2,0x0455);put(ram,0x104d74,2,1);
 s=state(0x4e286);s.d[0]=0;o=Out();table(o);assert(run(ram,s,STOP,o)&&s.pc==0x3aea&&s.a[7]==SP-12&&get(ram,SP-12,4)==0x3c00);
 put(ram,SP-2,2,0x0a00);put(ram,SP-8,1,0x77);put(ram,0x10dd20,1,0x55);const ms5::AnimationMachineState pending=s;const Bytes held=ram;
 assert(run(ram,s,STOP,o)&&same(s,pending)&&ram==held&&o.ports.empty());
 put(ram,0x104d74,2,0xffff);assert(run(ram,s,STOP,o)&&s.a[7]==SP+4&&get(ram,0x10dd20,1)==0x1f&&o.ports[5].value==0x7283c90a);
 // Actual WORD save aliases node12 weight/dirty; JSR LONG aliases current/target.
 ram.assign(65536,0);put(ram,0x10dd1f,1,1);put(ram,0x104e62,4,STOP);s=state(0x4e286);s.a[7]=0x104e62;s.d[0]=0x0a00;o=Out();table(o);
 assert(run(ram,s,STOP,o)&&s.a[7]==0x104e66&&get(ram,0x104e60,2)==0x000a&&get(ram,0x104e5c,4)==0x4e312&&o.ports.size()==10);
 ram.assign(65536,0);put(ram,0x10dd1f,1,1);put(ram,0x104e62,4,STOP);put(ram,0x104e5a,2,1);s=state(0x4e286);s.a[7]=0x104e62;s.d[0]=0xa00;o=Out();table(o);
 reject(ram,s,"unaligned animation machine PC",o); // Referenced-node update changes live JSR return to00040a0d.
}
void upper_and_errors(){
 const std::uint32_t cases[][2]={{0x47c6c,0x47d3e},{0x47c80,0x47eac},{0x47c92,0x47d24}};
 for(unsigned int i=0;i<3;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(cases[i][0]);s.a[0]=0x10095c;if(!i)put(ram,0x10d684,1,1);Out o;assert(run(ram,s,cases[i][1],o));}
 Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x47c92);s.a[0]=0x10095c;put(ram,s.a[0],2,1);Out o;assert(run(ram,s,0x47cae,o)&&!(s.d[1]&255));
 s=state(0x35f0);s.d[0]=0x7500;s.d[2]=s.d[3]=1;reject(ram,s,"TRAP15");
 s=state(0x35f0);s.d[0]=0x74ff;s.d[2]=1;s.d[3]=2;reject(ram,s,"TRAP15"); // One successful video event rolls back.
 s=state(0x3624);s.a[4]=0x1fffff;reject(ram,s,"alignment");
 s=state(0x4e286);s.d[0]=0xa00;put(ram,0x10dd1f,1,1);put(ram,SP,4,STOP);reject(ram,s,"program bus ROM");
 s=state(0x8cda);s.d[0]=12;s.d[2]=32;s.a[7]=SP-1;put(ram,0x104e5a,2,1);reject(ram,s,"even WORD/LONG");
 s=state(0x4843c);s.a[5]=0x1fa981;reject(ram,s,"program bus ROM");
}
}
int main(){preserving();bcd();palette();rectangle();hud();upper_and_errors();std::cout<<"animation_machine_hud_test PASS\n";}
