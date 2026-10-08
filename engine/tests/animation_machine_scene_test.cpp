#include "ms5/animation_machine.h"
#include "ms5/physical_rom_resource.h"
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
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const std::vector<ms5::PhysicalRomResource>*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message){const Bytes old=ram;const ms5::AnimationMachineState before=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;
 assert(!run(ram,s,stop,o));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==old&&same(s,before)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base);
 assert(o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);
}
void preserving(){
 const std::uint32_t cs[][3]={{0x47fec,0x43ffc,0x47ff2},{0x44004,0x43f3e,0x44008},{0x4402c,0x43f5c,0x44030},{0x4407e,0x43f5c,0x44082},{0x44086,0x4410c,0x4408a},{0x4408e,0xcd1c,0x44094},{0x43f70,0x440c8,0x43f74},{0x43f94,0xcd1c,0x43f9a},{0x43faa,0x440c8,0x43fae},{0x43fd4,0x16f9a,0x43fda},{0x43f3e,0xccd6,0x43f44},{0x43f44,0x1ad9a,0x43f4a},{0x43f4a,0x43efa,0x43f4c},{0xccd6,0xcd48,0xccda},{0xcd0c,0xcd1c,0xcd10},{0xcd16,0xcd1c,0xcd1a},{0x1adb6,0x1adf0,0x1adba},{0x1adc0,0x1adf0,0x1adc4},{0x1adca,0x1adf0,0x1adce},{0x1add4,0x1adf0,0x1add8},{0x16f9e,0x1829a,0x16fa2},{0x16fa2,0x1701a,0x16fa6},{0x16fa6,0x182d0,0x16faa}};
 const std::uint32_t rt[]={0x44094,0x43ffa,0x440ec,0x4410a,0x4411c,0x43f5a,0xcd1a,0xcd46,0x1adee,0x43f3c,0x16faa,0x182ce,0x1724a,0x1831a};
 for(unsigned int carry=0;carry<3;++carry){
  for(unsigned int i=0;i<sizeof(cs)/sizeof(cs[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(cs[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,cs[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==cs[i][2]);}
  for(unsigned int i=0;i<sizeof(rt)/sizeof(rt[0]);++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rt[i]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  Bytes ram(65536,0);put(ram,SP,4,0x105000);ms5::AnimationMachineState s=state(0x44008);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,0x4400a,o)&&s.a[0]==0x105000&&s.a[7]==SP+4&&s.carry==carry);
  s=state(0x43f60);s.a[0]=0x105000;s.d[0]=0xfffffff8;s.carry=static_cast<ms5::AnimationCarryState>(carry);assert(run(ram,s,0x43f64,o)&&get(ram,SP-4,4)==0x104ff8&&s.carry==carry);
 }
}
void complete(){
 for(unsigned int mode=0;mode<4;++mode){Bytes ram(65536,0x5a);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x43ffc);s.a[0]=mode?0x105000:0;s.a[5]=0xffffffff;const std::uint32_t a3=s.a[3],a6=s.a[6];
  if(mode==1){put(ram,0x105000,2,8);put(ram,0x105002,2,2);put(ram,0x105004,4,0x102000);put(ram,0x105008,2,0);put(ram,0x10500a,2,3);}
  if(mode==2){put(ram,0x105000,2,4);put(ram,0x105002,2,0);put(ram,0x105004,2,6);put(ram,0x105006,2,1);put(ram,0x105008,2,1);put(ram,0x10500a,2,0x8000);put(ram,0x10500c,2,3);}
  if(mode==3){put(ram,0x105000,2,4);put(ram,0x105002,2,0);put(ram,0x105004,2,8);put(ram,0x105006,2,2);put(ram,0x105008,4,0x102000);put(ram,0x10500c,2,6);put(ram,0x10500e,2,1);put(ram,0x105010,2,1);put(ram,0x105012,2,0);put(ram,0x105014,2,3);}
  Out o;assert(run(ram,s,STOP,o)&&s.a[7]==SP+4&&s.a[5]==0x108000&&s.a[3]==a3&&s.a[6]==a6&&s.carry==ms5::AnimationCarryUnknown);
  assert(get(ram,0x109152,4)==0xcd50&&get(ram,0x108d3d,1)==0&&get(ram,0x10d496,2)==get(ram,0x10d498,2));
  assert(o.reads==0&&o.status==ms5::AnimationMachineReturned&&o.ports.size()==((mode==1||mode==3)?4398U:2284U));
  if(mode==1){assert(get(ram,0x102026,2)==348&&get(ram,0x10203a,4)==0&&get(ram,0x102079,1)==0);}
  if(mode==3)assert(get(ram,0x102026,2)==1&&s.d[7]==0x82220000&&s.a[0]==0x10500c);
  if(mode==2)assert(get(ram,0x10d496,2)==380&&get(ram,0x108d3e,4)==0x0001017c&&s.a[0]==0x10500a&&s.d[7]==0);
 }
}
void wrap_and_loops(){
 // Lower allocator wraps BEFORE unsigned clamp; upper subtraction also wraps.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10d496,2,0xfff0);put(ram,0x10d498,2,0xfff8);ms5::AnimationMachineState s=state(0x440c8);s.d[0]=0x98760020;Out o;
 assert(run(ram,s,STOP,o)&&get(ram,0x10d496,2)==0x10&&s.d[0]==0x98760000&&s.d[2]==0xabcf0010);
 put(ram,0x10d49a,1,1);put(ram,0x10d496,2,5);put(ram,0x10d498,2,0x10);s=state(0x440c8);s.d[0]=0x98760020;o=Out();assert(run(ram,s,STOP,o)&&get(ram,0x10d498,2)==0xfff0&&s.d[0]==0x98760000);
 // Negative slot path skips video; nonnegative emits2048LONGs+watchdog.
 for(unsigned int neg=0;neg<2;++neg){ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x102026,2,neg?0x8000:0);s=state(0x1829a);s.a[0]=0x102000;o=Out();assert(run(ram,s,STOP,o)&&o.ports.size()==(neg?0U:2049U)&&s.a[7]==SP+4);}
 // Direct video loop initialffff executes65536 iterations.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0x182b4);s.a[1]=0x3c0000;s.d[6]=0x1234ffff;s.d[7]=0;o=Out();assert(run(ram,s,STOP,o)&&o.ports.size()==131073&&s.d[6]==0x1234ffff&&s.d[7]==0);
 ram.assign(65536,0);s=state(0xccfc);s.a[0]=0x101000;s.d[0]=0x1234fffc;s.d[7]=0x56780000;o=Out();assert(run(ram,s,0xcd06,o)&&get(ram,0x101000,2)==0xfffc&&s.d[0]==0x12340008&&s.a[0]==0x101002&&s.d[7]==0x5678ffff);
}
void live_stack(){
 Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x43fcc);s.a[0]=0x104000;s.a[7]=0x104006;s.d[1]=0xabcd5678;put(ram,0x104004,4,0x12345678);Out o;
 assert(run(ram,s,0x43fd2,o)&&s.a[0]==0x56785678&&s.a[7]==0x104004);
 // WORDpop updatesonlyD0.low and uses the bytes justwritten bythe realpush.
 assert(run(ram,s,0x43fd4,o)&&s.d[0]==0xabcd5678&&s.a[7]==0x104006);
 ram.assign(65536,0);put(ram,SP,2,0);s=state(0x44082);s.d[7]=0x9876ffff;o=Out();assert(run(ram,s,0x44086,o)&&s.d[7]==0x98760000&&s.a[7]==SP+2);
 put(ram,SP,2,1);s=state(0x44082);s.d[7]=0x98760000;o=Out();assert(run(ram,s,0x44078,o)&&s.d[7]==0x98760001);
 // Final clear overlaps the liveRTS LONG and returns tozero, not the oldSTOP.
 ram.assign(65536,0x7a);s=state(0x182d0);s.a[0]=0x102000;s.a[7]=0x10203a;put(ram,s.a[7],4,STOP);o=Out();assert(run(ram,s,0,o)&&s.a[7]==0x10203e&&get(ram,0x10203a,4)==0&&s.a[1]==0x10207a);
 // FullA0 comparison: lowWORDzero is not a null pointer.
 ram.assign(65536,0);s=state(0x4400a);s.a[0]=0x100000;o=Out();assert(run(ram,s,0x44012,o));
}
void failures(){
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x44074);reject(ram,s,STOP,"unsupported animation scene PC");
 s=state(0x43ffc);s.a[0]=0x105000;put(ram,0x105000,2,4);put(ram,0x105002,2,9);reject(ram,s,STOP,"TRAP15");
 s=state(0x18318);s.a[1]=0x1ffffe;put(ram,SP,4,0x123);reject(ram,s,STOP,"unaligned");
 s=state(0x182d0);s.a[0]=0x1fffc0;reject(ram,s,STOP,"unsupported animation machine write device");
 s=state(0x43ffc);s.a[0]=0x48108;reject(ram,s,STOP,"missing program bus ROM");
 s=state(0xcd1c);s.a[5]=0x1ff2bc;reject(ram,s,STOP,"unsupported animation machine write device");
}
#ifdef MS5_SCENE_REAL_RESOURCE_TEST
void real_resource(const char* path){std::vector<ms5::PhysicalRomResource> physical(1);std::string error;assert(ms5::load_physical_rom_resource(path,physical[0],error));Bytes ram(65536,0x65);ms5::AnimationMachineState s=state(0x47fe8);Out o;assert(run(ram,s,0x47ff2,o,&physical)&&s.a[7]==SP&&s.a[0]==0x48110&&get(ram,0x10d256+0x26,2)==348&&o.ports.size()==4398);}
#endif
}
int main(int argc,char**argv){preserving();complete();wrap_and_loops();live_stack();failures();
#ifdef MS5_SCENE_REAL_RESOURCE_TEST
if(argc==2)real_resource(argv[1]);
#else
(void)argc;(void)argv;
#endif
std::cout<<"animation_machine_scene_test PASS calls="<<calls<<"\n";}
