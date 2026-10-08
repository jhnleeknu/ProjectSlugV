#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
unsigned int calls=0;
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out {ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o,const std::vector<ms5::PhysicalRomResource>*physical=NULL){++calls;ms5::ProgramBusState bus;bus.physical_rom=physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message){const Bytes before=ram;const ms5::AnimationMachineState old=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;assert(!run(ram,s,stop,o));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";assert(o.error.find(message)!=std::string::npos&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef);}
void descriptor(Bytes&ram,unsigned int primary=0,unsigned int secondary=0){put(ram,0x104000,2,primary);put(ram,0x104002,2,secondary);put(ram,0x104004,2,4);put(ram,0x104006,2,4);put(ram,0x10202e,4,0x104000);}
ms5::AnimationMachineState transfer(std::uint32_t pc=0x183c6){ms5::AnimationMachineState s=state(pc);s.a[0]=0x102000;s.a[1]=0x104000;for(unsigned int i=0;i<6;++i)s.d[i]=i==2||i==3?1:0;return s;}
std::vector<ms5::PhysicalRomResource> resources(){std::vector<ms5::PhysicalRomResource> p(2);for(unsigned int i=0;i<2;++i){p[i].source_rom_offset=0x200000+i*0x100000;p[i].data.assign(0x2000,0);}put(p[1].data,4,4,0x200008);put(p[1].data,8,4,0x200100);put(p[1].data,0x100,2,4);put(p[1].data,0x102,2,4);for(unsigned int i=0;i<16;++i)put(p[1].data,0x104+4*i,4,0x11112222U+i);put(p[0].data,0x10,4,0x201000);put(p[0].data,0x1004,4,0x106000);return p;}
void preserving(){
 const std::uint32_t cs[][3]={{0x48042,0x1861a,0x48048},{0x48048,0x17012,0x4804e},{0x18650,0x18702,0x18654},{0x1873e,0x16f0e,0x18742},{0x18746,0x183c6,0x1874a},{0x18760,0x183c6,0x18764},{0x18778,0x16f0e,0x1877c},{0x18780,0x183c6,0x18784},{0x18796,0x183c6,0x1879a}};
 const std::uint32_t rt[]={0x17018,0x16f98,0x18654,0x18772,0x1879a,0x185f2,0x185f8};
 const std::uint32_t push[]={0x18424,0x18742,0x18758,0x1877c},pop[]={0x18530,0x1874a,0x18764,0x18784};
 for(unsigned int carry=0;carry<3;++carry){
  for(unsigned int i=0;i<sizeof(cs)/sizeof(cs[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(cs[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,cs[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==cs[i][2]);}
  for(unsigned int i=0;i<sizeof(rt)/sizeof(rt[0]);++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rt[i]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  for(unsigned int i=0;i<4;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(push[i]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,push[i]+4,o)&&s.a[7]==SP-12&&s.carry==carry);for(unsigned int j=0;j<6;++j)assert(get(ram,SP-12+2*j,2)==(s.d[j]&65535));put(ram,SP-12,2,0x8001);s.pc=pop[i];assert(run(ram,s,pop[i]+4,o)&&s.a[7]==SP&&s.d[0]==0xffff8001&&s.carry==carry);}
  Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x18702);s.a[0]=0x102000;s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,0x18720,o)&&s.carry==carry);
 }
}
void columns(){
 for(unsigned int mode=0;mode<3;++mode){Bytes ram(65536,0);put(ram,SP,4,STOP);descriptor(ram);put(ram,0x102036,4,mode==0?0:mode==1?0xffffffff:0x106000);put(ram,0x102034,2,0x12);put(ram,0x10203a,2,0xabcd);
  put(ram,0x106000,2,0);put(ram,0x106002,1,0x10);put(ram,0x106003,1,0x77);put(ram,0x106004,2,0x8000);
  ms5::AnimationMachineState s=transfer(0x16f0e);s.d[0]=0xabcd0000;s.d[4]=0x98760000;s.d[6]=0x12340000;Out o;assert(run(ram,s,STOP,o)&&s.d[0]==0xabcd0000&&s.d[4]==0x98760000&&s.d[6]==0x1234ffff&&o.ports.empty());
  assert(get(ram,0x10203a,2)==(mode==0?0x21:mode==1?0xcd:0x1877));
 }
 // Direct BYTE boundary: lower-byte publication changes the later record operand.
 Bytes ram(65536,0);put(ram,0x106003,1,0x22);put(ram,0x102035,1,0x25);
 ms5::AnimationMachineState s=transfer(0x16f72);s.a[2]=0x106000;s.a[3]=0x106001;Out o;assert(run(ram,s,0x16f88,o)&&get(ram,0x106001,2)==0x2022);
 // Backtrack then forwardwalk, with last negative sentinel stopping reads.
 ram.assign(65536,0);put(ram,SP,4,STOP);descriptor(ram);put(ram,0x102036,4,0x106008);put(ram,0x106000,4,0x00000111);put(ram,0x106004,4,0x00020222);put(ram,0x106008,4,0x00040333);put(ram,0x10600c,4,0x80000000);s=transfer(0x16f0e);s.d[0]=3;o=Out();assert(run(ram,s,STOP,o)&&get(ram,0x102036,4)==0x106004);
 // Full65536 legitimate iterations, within the explicitly raised finite budget.
 ram.assign(65536,0);put(ram,SP,4,STOP);descriptor(ram);put(ram,0x104004,2,0);s=transfer(0x16f0e);s.d[0]=0xabcd1234;s.d[4]=0x98765678;s.d[2]=0x76540000;s.d[6]=0x12340000;o=Out();assert(run(ram,s,STOP,o)&&s.d[0]==0xabcd1234&&s.d[4]==0x98765678&&s.d[6]==0x1234ffff&&o.ports.empty());
}
void transfers(){
 std::vector<ms5::PhysicalRomResource> p=resources();
 for(unsigned int slot=0;slot<2;++slot){Bytes ram(65536,0);put(ram,SP,4,STOP);descriptor(ram);put(ram,0x102026,2,slot?0xffff:0);ms5::AnimationMachineState s=transfer();Out o;assert(run(ram,s,STOP,o,&p)&&s.carry==ms5::AnimationCarrySet&&s.a[7]==SP+4&&o.dev.bank_base==0x200000&&(get(ram,0x10207a,1)&128));assert(o.ports.size()==(slot?6U:8U));if(!slot){assert(o.ports[2].address==0x3c0000&&o.ports[2].size==4&&o.ports[2].value==0x7e1111&&o.ports[3].value==0x7f2222);}assert(get(ram,SP-8,2)==1);}
 // Clip rejection precedes any push/bank/resource read and ends knownClear.
 Bytes ram(65536,0);put(ram,SP,4,STOP);descriptor(ram);ms5::AnimationMachineState s=transfer();s.d[0]=4;Out o;assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarryClear&&s.a[7]==SP+4&&o.ports.empty());
 // Secondary live RAM copy and ffffffff clear branch, with primary skipped.
 for(unsigned int empty=0;empty<2;++empty){ram.assign(65536,0x5a);put(ram,SP,4,STOP);descriptor(ram,0,1);put(ram,0x102026,2,65535);put(ram,0x106000,2,0x100);put(ram,0x106002,2,0x100);put(ram,0x106100,4,0x12345678);put(ram,0x106102,4,0x98765432);put(p[0].data,0x1004,4,empty?0xffffffff:0x106000);s=transfer();o=Out();assert(run(ram,s,STOP,o,&p)&&s.carry==ms5::AnimationCarrySet);assert(get(ram,0x1020fc,4)==(empty?0:0x12349876));}
 // Actual source/destination overlap: secondLONG reads the first publication.
 ram.assign(65536,0);put(ram,0x106000,4,0x11223344);put(ram,0x106004,4,0x55667788);s=transfer(0x1858a);s.a[3]=0x106002;s.a[4]=0x106000;s.d[0]=0;s.d[6]=2;o=Out();assert(run(ram,s,0x18598,o)&&get(ram,0x106006,4)==0x33447788);

}
void wrapping(){
 Bytes ram(65536,0);descriptor(ram);put(ram,0x104004,2,7);ms5::AnimationMachineState s=transfer(0x18714);s.d[0]=0xabcdffff;Out o;assert(run(ram,s,0x18720,o)&&s.d[0]==0x24920001);
 s=transfer(0x18732);s.d[1]=0x1234ffff;put(ram,0x104006,2,9);o=Out();assert(run(ram,s,0x1873e,o)&&s.d[1]==0x1c710006);
 // Wholeupper NULL descriptor returns actualJSR then sets node flag.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=transfer(0x48042);o=Out();assert(run(ram,s,0x4804e,o)&&s.a[7]==SP&&get(ram,SP-4,4)==0x4804e&&get(ram,0x10207a,1)==0x81&&s.carry==ms5::AnimationCarryUnknown);
 std::vector<ms5::PhysicalRomResource> p=resources();
 // Wholeupper actualnestedcalls with a valid primaryslot and liveRAM descriptor.
 ram.assign(65536,0);put(ram,SP,4,STOP);descriptor(ram);put(ram,0x102014,2,0xffa0);put(ram,0x102018,2,0x27f);s=transfer(0x48042);o=Out();assert(run(ram,s,0x4804e,o,&p)&&s.a[7]==SP&&o.ports.size()==38&&get(ram,0x10207a,1)==0x81&&s.carry==ms5::AnimationCarryUnknown);
 // Fourphase wrap path leaves the finaltransfer registers un-restored.
 for(unsigned int flags=0;flags<4;++flags){ram.assign(65536,0);put(ram,SP,4,STOP);descriptor(ram);put(ram,0x102026,2,65535);put(ram,0x10207a,1,flags*8);s=transfer(0x18702);s.d[0]=0xabcd0005;s.d[1]=0x98760005;o=Out();assert(run(ram,s,STOP,o,&p)&&s.a[7]==SP+4);}
}
void failures(){Bytes ram(65536,0);put(ram,SP,4,STOP);descriptor(ram);ms5::AnimationMachineState s=transfer(0x16f50);reject(ram,s,STOP,"unsupported animation map transfer PC");s=transfer(0x1871a);reject(ram,s,STOP,"unsupported animation map transfer PC");s=transfer(0x184d2);reject(ram,s,STOP,"unsupported animation machine PC");s=transfer(0x18714);put(ram,0x104004,2,0);reject(ram,s,STOP,"zero divisor");s=transfer(0x18424);s.a[7]=0x100006;reject(ram,s,STOP,"RAM mirror units");s=transfer(0x18530);s.a[7]=0x1ffff8;reject(ram,s,STOP,"missing program bus ROM");s=transfer(0x183c6);s.d[0]=0;s.d[2]=1;put(ram,0x104004,2,4);reject(ram,s,STOP,"missing program bus ROM");
 // Huge legitimate-width rectangle exceeds the finite block budget atomically.
 ram.assign(65536,0);s=transfer(0x18496);s.a[2]=0x100000;s.a[3]=0x10203a;s.a[4]=0x100000;s.d[2]=0;s.d[3]=0;s.d[6]=0;reject(ram,s,STOP,"budget exceeded");}

}
int main(){preserving();columns();transfers();wrapping();failures();std::cout<<"animation_machine_map_transfer_test PASS "<<calls<<" calls\n";}
