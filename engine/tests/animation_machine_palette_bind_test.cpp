#include "ms5/animation_machine.h"
#ifdef MS5_PALETTE_BIND_REAL_RESOURCE_TEST
#include "ms5/physical_rom_resource.h"
#endif
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000,BASE=0x104d92;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const std::vector<ms5::PhysicalRomResource>*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message){const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;assert(!run(ram,s,stop,o));assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef);}
void preserving(){
 const std::uint32_t call[][3]={{0xe7bf4,0x8e82,0xe7bfa},{0xe7bfe,0x8da2,0xe7c04},{0xe7c36,0xe7bf4,0xe7c3a},{0x47ff2,0xe7c36,0x47ff8},{0x4801e,0x8da2,0x48024},{0x4802a,0x16fac,0x48030},{0x4803c,0x16ff8,0x48042},{0x16fac,0x43dda,0x16fb2},{0x8ea6,0x8e4a,0x8ea8}};
 const std::uint32_t rt[]={0x8e48,0x8eb4,0x16fec,0x17010};
 for(unsigned int carry=0;carry<3;++carry){
  for(unsigned int i=0;i<sizeof(call)/sizeof(call[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(call[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,call[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==call[i][2]);}
  for(unsigned int i=0;i<sizeof(rt)/sizeof(rt[0]);++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rt[i]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  Bytes ram(65536,0);ms5::AnimationMachineState s=state(0xe7c3e);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,0x8da2,o)&&s.carry==carry&&s.a[7]==SP);
 }
}
void bindings(){
 for(unsigned int disabled=0;disabled<2;++disabled){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x106000,2,1);put(ram,0x106002,2,disabled?65535:0x1234);put(ram,0x106004,1,0x25);put(ram,0x106006,2,65535);
  put(ram,BASE+0x10,2,0x10);put(ram,BASE+0x12,2,0x10);const unsigned int bucket=disabled?0xff4:0x344;put(ram,BASE+bucket+2,2,bucket);
  ms5::AnimationMachineState s=state(0x8da2);s.a[0]=0x106000;s.a[5]=0xffffffff;Out o;assert(run(ram,s,STOP,o)&&s.a[0]==0x106008&&s.a[5]==0x108000&&s.a[7]==SP+4&&s.d[0]==0xabcdffff);
  assert(get(ram,BASE+0x18,2)==65535&&get(ram,BASE+0x1a,2)==(disabled?65535:0x1234)&&get(ram,BASE+0x1c,2)==(disabled?65535:0x1234)&&get(ram,BASE+0x1f,1)==(disabled?2:0xa5));
  assert(o.ports.size()==1&&o.ports[0].address==0x300001&&o.ports[0].value==0x34&&o.reads==0);
 }
 // Slot WORDwrap 1001 becomes10 and negative signed slot1fff selects belowA1.
 const unsigned int slots[]={0x1001,0x1fff};for(unsigned int i=0;i<2;++i){Bytes ram(65536,0);put(ram,SP,4,STOP);const std::uint32_t node=i?BASE-16:BASE+16;put(ram,0x106000,2,slots[i]);put(ram,0x106002,2,0);put(ram,0x106006,2,65535);put(ram,BASE+6,2,i?0xfff0:16);ms5::AnimationMachineState s=state(0x8da2);s.a[0]=0x106000;Out o;assert(run(ram,s,STOP,o)&&s.a[2]==node&&get(ram,node+8,2)==65535);}
 // The preceding sourceWORD store changes the later BYTE operand, read live.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,BASE+0x16,2,1);put(ram,BASE+0x18,2,0x1234);put(ram,BASE+6,2,16);put(ram,BASE+0x1c,2,65535);
 ms5::AnimationMachineState s=state(0x8da2);s.a[0]=BASE+0x16;Out o;assert(run(ram,s,0x8e36,o)&&get(ram,BASE+0x1f,1)==0x92&&s.a[0]==BASE+0x16);
 // Unlink's first store changes bucket tail; later read must observe it.
 ram.assign(65536,0);s=state(0x8dde);s.a[1]=BASE;s.a[2]=BASE+16;s.a[4]=BASE+4;s.d[0]=16;s.d[4]=4;put(ram,BASE+16,2,0x40);put(ram,BASE+18,2,6);put(ram,BASE+6,2,0x80);o=Out();assert(run(ram,s,0x8df0,o)&&s.d[3]==0xabd00040&&get(ram,BASE+6,2)==0x40);
}
void release(){
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x8e82);Out o;assert(run(ram,s,STOP,o)&&s.d[0]==0x1000&&s.d[7]==0xabd4ffff&&s.a[2]==BASE+0x1000&&o.ports.size()==1);
 // One live release invokes existing8e4a and publishes its actual BSR return.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,BASE,2,0);put(ram,BASE+2,2,0);put(ram,BASE+8,2,65535);put(ram,BASE+0x1000,2,0x1000);s=state(0x8e82);o=Out();assert(run(ram,s,STOP,o)&&get(ram,SP-4,4)==0x8ea8&&get(ram,BASE+8,2)==0&&get(ram,BASE+15,1)==2);
}
void nodes(){
 const unsigned int words[]={0,0x7ff,0x800,0xfff,0x1800,0xffff};
 for(unsigned int i=0;i<6;++i){Bytes ram(65536,0x5a);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x16ff8);s.a[0]=0x102000;s.a[1]=0x12345678;s.a[2]=0x87654321;s.d[0]=0xabcd0000|words[i];s.d[1]=0x98760000|words[5-i];Out o;assert(run(ram,s,STOP,o));const unsigned int w=words[i]&0xfff;assert(s.d[0]==(0xabcd0000|(w&0x800?w|0xf000:w))&&get(ram,0x10202e,4)==0x12345678&&get(ram,0x102036,4)==0x87654321&&s.a[7]==SP+4);}
 Bytes ram(65536,0x5a);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x16fac);s.a[0]=0x102000;Out o;assert(run(ram,s,STOP,o)&&get(ram,0x102026,2)==0x5a5a&&get(ram,0x102036,4)==0xffffffff&&get(ram,0x102028,2)==0x100&&get(ram,SP-4,4)==0x16fb2);
 // Descriptor LONG overwrites the actual RTS return and is popped live.
 ram.assign(65536,0);s=state(0x16ff8);s.a[0]=0x102000;s.a[7]=0x10202e;s.a[1]=0x104000;o=Out();assert(run(ram,s,0x104000,o)&&s.a[7]==0x102032);
}
void whole(){
 // Synthetic typed physical bytes test bus/call integration; not a native ROM oracle.
 std::vector<ms5::PhysicalRomResource> physical(2);physical[0].source_rom_offset=0;physical[0].data.assign(0x100000,0);physical[1].source_rom_offset=0x200000;physical[1].data.assign(0x2000,0);
 Bytes&fixed=physical[0].data;fixed[0xe7b58]=fixed[0xe7b59]=fixed[0xe7bda]=fixed[0xe7bdb]=255;
 Bytes&bank=physical[1].data;bank[0xc]=0;bank[0xd]=0x20;bank[0xe]=3;bank[0xf]=0xd0;
 bank[0x4c0]=0;bank[0x4c1]=0x20;bank[0x4c2]=0x1e;bank[0x4c3]=0xc0;
 bank[0x1ec0]=0;bank[0x1ec1]=0x80;bank[0x1ec2]=0x14;bank[0x1ec3]=0x36;bank[0x1ec6]=bank[0x1ec7]=255;
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10d27c,2,0x789a);ms5::AnimationMachineState s=state(0x47ff2);Out o;
 assert(run(ram,s,0x48042,o,&physical)&&s.a[7]==SP&&s.a[0]==0x10d256&&s.a[1]==0x480f2&&s.a[2]==0&&s.d[0]==0&&s.d[1]==31&&o.dev.bank_base==0x200000);
 assert(get(ram,0x10d27c,2)==0x789a&&get(ram,0x10d284,4)==0x480f2&&get(ram,0x10d28c,4)==0&&get(ram,0x10d288,2)==0&&get(ram,0x10d28a,2)==31);
 assert(get(ram,BASE+0x80*16+10,2)==0x1436&&get(ram,BASE+0x80*16+15,1)==128&&get(ram,SP-4,4)==0x48042&&o.ports.size()==6);
 // Actual live32-bit logical pointer wraps onto a declared RAM mirror.
 ram.assign(65536,0);put(ram,0x100000,2,65535);put(ram,SP,4,STOP);s=state(0x8da2);s.a[0]=0xff100000;o=Out();assert(run(ram,s,STOP,o)&&s.a[0]==0xff100002);
}
#ifdef MS5_PALETTE_BIND_REAL_RESOURCE_TEST
void actual_resources(){
 std::vector<ms5::PhysicalRomResource> physical;std::string error;
 const char*files[]={"extracted/runtime/program_rom/program_rom_000000.ms5d","extracted/runtime/program_rom/program_rom_200000.ms5d"};
 for(unsigned int i=0;i<2;++i){ms5::PhysicalRomResource p;assert(ms5::load_physical_rom_resource(files[i],p,error));physical.push_back(p);}
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10d27c,2,0x4321);ms5::AnimationMachineState s=state(0x47ff2);Out o;
 assert(run(ram,s,0x48042,o,&physical)&&s.a[7]==SP&&s.pc==0x48042&&o.dev.bank_base==0x200000&&s.a[1]==0x480f2&&s.d[0]==0&&s.d[1]==31);
 assert(get(ram,0x10d27c,2)==0x4321&&get(ram,BASE+0x80*16+10,2)==0x1436&&get(ram,0x10d284,4)==0x480f2);
}
#endif
void failures(){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x8db4);reject(ram,s,STOP,"unsupported animation palette bind PC");s=state(0x16ff8);s.a[0]=0x1fffcc;reject(ram,s,STOP,"write device");s=state(0x8e48);put(ram,SP,4,3);reject(ram,s,STOP,"unaligned");s=state(0x48012);reject(ram,s,STOP,"missing program bus ROM");s=state(0x16fac);s.a[0]=0x102000;s.a[7]=0x102010;reject(ram,s,STOP,"unsupported animation machine PC");}
}
int main(){preserving();bindings();release();nodes();whole();failures();
#ifdef MS5_PALETTE_BIND_REAL_RESOURCE_TEST
actual_resources();
#endif
std::cout<<"animation_machine_palette_bind_test PASS "<<calls<<" calls\n";}
