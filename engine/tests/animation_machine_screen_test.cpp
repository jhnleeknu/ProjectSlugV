#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
unsigned int calls=0;
void put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes& b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out{ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message){const Bytes old=ram;const ms5::AnimationMachineState before=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;
 assert(!run(ram,s,stop,o));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==old&&same(s,before)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base);
 assert(o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);
}
void port(const ms5::VideoPortWrite&p,std::uint32_t address,unsigned int size,std::uint32_t value){assert(p.address==address&&p.size==size&&p.value==value);}
void preserving(){const std::uint32_t callspec[][3]={{0xcaf0,0xca9e,0xcaf2},{0xcb08,0x35a2,0xcb0e},{0xcb1c,0x35a2,0xcb22},{0xcb30,0x35a2,0xcb36},{0xcb44,0x35a2,0xcb4a},{0xcb58,0x35a2,0xcb5e},{0x47fca,0xcaf0,0x47fd0}};
 const std::uint32_t returns[]={0xcaee,0xcb62};const std::uint32_t lea[][2]={{0xca9e,0xcaa4},{0xcaf2,0xcaf8}};
 for(unsigned int f=0;f<3;++f){ms5::AnimationCarryState carry=static_cast<ms5::AnimationCarryState>(f);
  for(unsigned int i=0;i<7;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(callspec[i][0]);s.carry=carry;Out o;assert(run(ram,s,callspec[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==callspec[i][2]);}
  for(unsigned int i=0;i<2;++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(returns[i]);s.carry=carry;Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  for(unsigned int i=0;i<2;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(lea[i][0]);s.carry=carry;Out o;assert(run(ram,s,lea[i][1],o)&&s.carry==carry&&s.a[4]==0x3c0000);}
  for(unsigned int low=0;low<2;++low){Bytes ram(65536,0);ms5::AnimationMachineState s=state(0xcab8);s.carry=carry;s.d[7]=0xface0000U|(low?65535:0);Out o;assert(run(ram,s,low?0xcab0:0xcabc,o)&&s.carry==carry&&s.d[7]==(low?0xfacefffeU:0xfaceffffU)&&o.ports.empty());}
 }
}
void reset(){const std::uint32_t highs[]={0,0x12340000,0x80000000,0xffff0000};
 for(unsigned int h=0;h<4;++h){Bytes ram(65536,0x53);put(ram,SP,4,STOP);Bytes before=ram;ms5::AnimationMachineState s=state(0xca9e),want=s;s.d[7]=want.d[7]=highs[h]|0x6789;Out o;
  want.d[0]=0x7580ff02;want.d[1]=0;want.d[7]=highs[h]|65535U;want.a[4]=0x3c0000;want.a[7]+=4;want.pc=STOP;want.carry=ms5::AnimationCarryUnknown;
  assert(run(ram,s,STOP,o)&&same(s,want)&&ram==before&&o.ports.size()==773&&o.reads==0&&o.status==ms5::AnimationMachineReturned);
  for(unsigned int i=0;i<768;++i)port(o.ports[i],0x3c0000,4,0x75000000U+i*0x10000U);
  for(unsigned int i=0;i<4;++i)port(o.ports[768+i],0x3c0000,4,0x75000200U+i*0x200000U);port(o.ports.back(),0x3c0000,4,0x7580ff02);
 }
 // DBRA countffff means65536 cells; raw additions wrap in uint32 space.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xcab0);s.a[4]=0x3c0000;s.d[0]=0xffff0001;s.d[7]=0xfaceffff;Out o;
 assert(run(ram,s,STOP,o)&&o.ports.size()==65541&&s.d[7]==0xfaceffff&&s.d[0]==0x7580ff02);port(o.ports[0],0x3c0000,4,0xffff0001);port(o.ports[1],0x3c0000,4,1);port(o.ports[65535],0x3c0000,4,0xfffe0001);
 // Direct tail setup discards arbitrary incoming D0 entirely.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0xcabc);s.a[4]=0x3c0000;s.d[0]=0xabcdef12;o=Out();assert(run(ram,s,STOP,o)&&s.d[0]==0x7580ff02&&s.d[1]==0&&o.ports.size()==5);
}
void clear_screen(){const std::uint32_t a5s[]={0x108000,0x1f8001,0x207699};
 for(unsigned int k=0;k<3;++k){Bytes ram(65536,0x53);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xcaf0);s.a[5]=a5s[k];const std::uint32_t d6=s.d[6]&0xffff0000U;Out o;
  assert(run(ram,s,STOP,o)&&s.d[0]==0x75807500&&s.d[1]==0x7000&&s.d[2]==0&&s.d[3]==32&&s.d[6]==d6&&s.d[7]==0x75007000&&s.a[4]==0x3c0000&&s.a[7]==SP+4&&get(ram,a5s[k]-0x769a,1)==0&&o.ports.size()==2072&&get(ram,SP-4,4)==0xcb5e);
  const unsigned int widths[]={38,40,40,1,1},heights[]={30,1,1,32,32};const std::uint32_t coords[]={0x7021,0x701f,0x7000,0x7000,0x74e0};unsigned int at=773;
  for(unsigned int i=0;i<5;++i){port(o.ports[at++],0x300001,1,coords[i]&255U);for(unsigned int col=0;col<widths[i];++col)for(unsigned int row=0;row<heights[i];++row)port(o.ports[at++],0x3c0000,4,((coords[i]+col*32+row)<<16)|(i?0x7000U:255U));port(o.ports[at++],0x3c0004,2,0);port(o.ports[at++],0x3c0000,4,0x82000000);}
  assert(at==o.ports.size());
 }
 // Final CLR.B aliases the outer return slot after all nested calls.
 Bytes ram(65536,0);put(ram,SP,4,0xab123456);ms5::AnimationMachineState s=state(0xcaf0);s.a[5]=SP+0x769a;Out o;assert(run(ram,s,0x123456,o)&&s.a[7]==SP+4&&get(ram,SP,4)==0x123456&&o.ports.size()==2072);
}
void live_a4(){
 // DirectA4 RAM mirror and live stack aliases cannot be collapsed to video output.
 for(unsigned int alias=0;alias<2;++alias){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xcab0);s.a[4]=alias?SP:0x1f4000;s.d[0]=0x12345678;s.d[7]=0xface0000;Out o;assert(run(ram,s,alias?0x7580ff02:STOP,o)&&get(ram,s.a[4],4)==0x7580ff02&&o.ports.empty()&&s.a[7]==SP+4);}
 // PVC fallback preserves two actual ordered WORD writes and device equations.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xcae8);s.a[4]=0x2ffff0;s.d[0]=0x12345678;Out o;assert(run(ram,s,STOP,o)&&o.ports.size()==2);port(o.ports[0],0x2ffff0,2,0x1234);port(o.ports[1],0x2ffff2,2,0xff02);assert(o.dev.bank_base==0x100000U+0xff0200U+0x12U&&get(o.dev.pvc,0x1ff0,2)==0x12a0&&get(o.dev.pvc,0x1ff2,2)==0x7f02);
}
void upper(){Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x47fca);Out o;assert(run(ram,s,0x480bc,o)&&s.a[7]==SP&&get(ram,SP-4,4)==0x47fd0&&get(ram,SP-8,4)==0xcb5e&&get(ram,0x102000,4)==0x47fdc&&get(ram,0x10207a,2)==31&&o.ports.size()==2072);
 const unsigned int timers[]={0,1,2,65535};for(unsigned int i=0;i<4;++i){ram.assign(65536,0);put(ram,0x10207a,2,timers[i]);s=state(0x47fdc);o=Out();assert(run(ram,s,timers[i]==1?0x47fe4:0x480bc,o)&&get(ram,0x10207a,2)==((timers[i]-1)&65535U)&&s.a[7]==SP&&o.ports.empty()&&s.carry==ms5::AnimationCarryUnknown);}
}
void errors(){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0xcaf0);s.a[5]=0x7699;reject(ram,s,STOP,"unsupported animation machine write device");
 s=state(0xcab0);s.a[4]=0x1ffffe;s.d[7]=0;reject(ram,s,STOP,"unsupported animation machine write device");s.a[4]=0x104001;reject(ram,s,STOP,"alignment");
 s=state(0xcaf0);s.a[7]=0x100002;reject(ram,s,STOP,"RAM");
 s=state(0xcaf0);put(ram,SP,4,0xdeac);reject(ram,s,STOP,"unsupported animation machine PC");
 s=state(0x47fd0);s.a[6]=0xffffe;reject(ram,s,STOP,"unsupported animation machine write device");
 s=state(0x47fdc);s.a[6]=0x102001;reject(ram,s,STOP,"even WORD/LONG");
 s=state(0x47fe0);reject(ram,s,STOP,"unsupported animation machine PC"); // BNE needs unrepresented incoming Z.
 s=state(0x49b0c);reject(ram,s,STOP,"unsupported animation machine PC"); // 49b0c has no executor (1a470 is U5, 1a7a8 U4 now).
}
}
int main(){preserving();reset();clear_screen();live_a4();upper();errors();std::cout<<"animation_machine_screen_test PASS "<<calls<<" API invocations\n";}
