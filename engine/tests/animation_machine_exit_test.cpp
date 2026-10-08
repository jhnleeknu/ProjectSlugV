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
struct Out{ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::vector<ms5::PhysicalRomResource> physical;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;bus.physical_rom=&o.physical;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message,Out o=Out()){const Bytes old=ram;const ms5::AnimationMachineState before=s;const ms5::AnimationMachineDevice dev=o.dev;
 assert(!run(ram,s,stop,o));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==old&&same(s,before)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base);
 assert(o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);
}
void lookup(Out&o){ms5::PhysicalRomResource r;r.source_rom_offset=0x30ec;for(unsigned int i=0;i<8;++i)r.data.push_back(static_cast<std::uint8_t>(0x60+i));o.physical.push_back(r);}
void preserving(){const std::uint32_t jsr[][3]={{0x47eb2,0x16ed2,0x47eb8},{0x47ee0,0x49f8c,0x47ee6},{0x47ef8,0x1c63c,0x47efe},{0x47f42,0x48398,0x47f46},{0x47f4e,0x3af8,0x47f54},{0x47f58,0x3af8,0x47f5e},{0x47f62,0x3af8,0x47f68},{0x47f68,0x3c84,0x47f6e},{0x47f6e,0x3d44,0x47f74},{0x47f7c,0x3af8,0x47f82},{0x47f96,0x8c16,0x47f9c},{0x47fb8,0x8c16,0x47fbe},{0x47fbe,0x4e24e,0x47fc4},{0x47fc4,0xca7e,0x47fca},{0x1c642,0x289e,0x1c648},{0x1c65e,0x289e,0x1c664},{0x48398,0x30f4,0x4839e},{0x3d48,0x3ac8,0x3d4c}};
 const std::uint32_t rts[]={0x1c674,0x483a8,0x3102,0x3c88,0x4e252,0xca82,0x8ca4,0x8cc8};const std::uint32_t jumps[][2]={{0x47ed6,0x47edc},{0x47f3e,0x480bc},{0x47f46,0x47c5a},{0x1c63c,0x1c642},{0x1c658,0x1c65e}};
 for(unsigned int f=0;f<3;++f){ms5::AnimationCarryState carry=static_cast<ms5::AnimationCarryState>(f);
  for(unsigned int i=0;i<18;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(jsr[i][0]);s.carry=carry;Out o;assert(run(ram,s,jsr[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==jsr[i][2]);}
  for(unsigned int i=0;i<8;++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rts[i]);s.carry=carry;Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  for(unsigned int i=0;i<5;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(jumps[i][0]);s.carry=carry;Out o;assert(run(ram,s,jumps[i][1],o)&&s.carry==carry);}
  Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x47f74);s.carry=carry;Out o;assert(run(ram,s,0x47f78,o)&&s.carry==carry&&get(ram,SP-4,4)==0xabcd1234&&s.a[7]==SP-4);put(ram,SP-4,4,0x87658000);s.pc=0x47f82;assert(run(ram,s,0x47f86,o)&&s.carry==carry&&s.d[0]==0x87658000&&s.a[7]==SP);
 }
 const std::uint32_t branch[][3]={{0x1c648,0x1c658,0x1c64c},{0x1c664,0x1c674,0x1c668}};
 for(unsigned int i=0;i<2;++i)for(unsigned int f=1;f<3;++f){Bytes ram(65536,0);ms5::AnimationMachineState s=state(branch[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(f);Out o;assert(run(ram,s,branch[i][f],o)&&s.carry==static_cast<ms5::AnimationCarryState>(f));}
}
void helpers(){
 for(unsigned int index=0;index<256;++index){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10fd8c,1,index);ms5::AnimationMachineState s=state(0x48398);s.d[0]=0xfacebeef;Out o;lookup(o);assert(run(ram,s,STOP,o)&&s.d[0]==(0xface0000U|0x60U|(index&7U))&&get(ram,0x10d67e,2)==(((0x60U|(index&7U))<<8)|255U)&&get(ram,SP-4,4)==0x4839e&&s.a[7]==SP+4&&s.carry==ms5::AnimationCarryUnknown);}
 for(unsigned int first=0;first<2;++first)for(unsigned int second=0;second<2;++second){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x100cb8,4,first?0:0x270e);put(ram,0x100da8,4,second?0:0x270e);put(ram,0x100d60,1,0x81);put(ram,0x100e50,1,0x81);ms5::AnimationMachineState s=state(0x1c63c);Out o;assert(run(ram,s,STOP,o)&&s.a[0]==0x100da8&&s.a[7]==SP+4&&get(ram,0x100d60,1)==(first?0x83:0x81)&&get(ram,0x100e50,1)==(second?0x83:0x81)&&get(ram,0x100d16,1)==(first?6:0)&&get(ram,0x100e06,1)==(second?6:0));}
 // Actual nested JSR overwrites the player marker before289e reads it.
 Bytes ram(65536,0);put(ram,0x100cbc,4,STOP);put(ram,0x100cb8,4,0x270e);put(ram,0x100da8,4,0x270e);ms5::AnimationMachineState s=state(0x1c63c);s.a[7]=0x100cbc;Out o;
 assert(run(ram,s,STOP,o)&&get(ram,0x100cb8,4)==0x1c664&&get(ram,0x100d60,1)==2&&get(ram,0x100d16,1)==6&&get(ram,0x100e50,1)==0&&s.a[7]==0x100cc0);
 const std::uint32_t pcs[]={0x3c84,0x4e24e,0xca7e};const std::uint32_t at[]={0x104d7e,0x10dd1f,0x100965};
 for(unsigned int i=0;i<3;++i){ram.assign(65536,0x55);put(ram,SP,4,STOP);s=state(pcs[i]);o=Out();assert(run(ram,s,STOP,o)&&get(ram,at[i],1)==0&&s.a[7]==SP+4&&s.carry==ms5::AnimationCarryUnknown);}
}
void palette(){const int vals[]={-32768,-32,-31,0,31,32,32767};
 for(unsigned int v=0;v<7;++v)for(unsigned int duration=0;duration<3;++duration){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x8c16);s.a[5]=0xffffffff;s.d[0]=0xabcd0000U|static_cast<std::uint16_t>(vals[v]);s.d[1]=s.d[2]=0;s.d[3]=0xcafe0000U|(duration==2?255:duration);const std::uint32_t d4=s.d[4],a6=s.a[6];Out o;assert(run(ram,s,STOP,o)&&s.a[5]==0x108000&&s.d[4]==d4&&s.a[6]==a6&&s.a[7]==SP+4&&s.carry==ms5::AnimationCarryUnknown);int channel=vals[v]<-31?-31:vals[v]>31?31:vals[v];assert(get(ram,0x107dc8,2)==(static_cast<std::uint32_t>(channel*256)&65535U));}
 // Target writes alias the shared caller return; the live RTS must see them.
 Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x8c16);s.a[7]=0x107dc8;s.d[0]=1;s.d[1]=2;s.d[2]=3;s.d[3]=32;Out o;assert(run(ram,s,0x01000200,o)&&s.a[7]==0x107dcc);
}
void entry_and_countdown(){
 Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x47eac);Out o;assert(run(ram,s,0x47f04,o)&&get(ram,0x102000,4)==0x47f04&&get(ram,0x102026,4)==0x48980&&get(ram,0x10202c,2)==0x100&&get(ram,0x10207a,2)==90&&get(ram,0x10201e,2)==65535&&get(ram,0x102042,2)==0xa0&&get(ram,0x102046,2)==0x180&&get(ram,0x102020,2)==0xea&&s.a[7]==SP&&o.ports.size()==2);
 // Fixed-ROM handoff at48980 uses an explicitly synthetic terminal resource.
 ms5::PhysicalRomResource script;script.source_rom_offset=0x48980;script.data.push_back(0x28);o.physical.push_back(script);assert(run(ram,s,0x47f0a,o)&&s.a[7]==SP&&o.ports.size()==4);
 for(unsigned int timer=1;timer<=2;++timer){ram.assign(65536,0);put(ram,0x10207a,2,timer==2?65535:1);s=state(0x47f0a);o=Out();assert(run(ram,s,0x480bc,o)&&get(ram,0x10207a,2)==(timer==2?65534:0)&&s.a[7]==SP);}
 for(unsigned int flags=0;flags<4;++flags){ram.assign(65536,0);put(ram,0x100d19,1,(flags&1)?128:0);put(ram,0x100e09,1,(flags&2)?128:0);s=state(0x47f0a);o=Out();lookup(o);assert(run(ram,s,flags?0x480bc:0x47c6c,o)&&s.d[7]==(flags?255:0));if(!flags)assert(get(ram,0x102000,4)==0x47c6c&&get(ram,0x10207e,1)==255&&get(ram,0x102020,2)==0xea);}
 for(unsigned int timer=0;timer<3;++timer){ram.assign(65536,0);put(ram,0x10207a,2,timer);put(ram,0x10dd1f,1,255);put(ram,0x100965,1,255);s=state(0x47fa8);o=Out();assert(run(ram,s,timer==1?0x47fca:0x480bc,o)&&get(ram,0x10207a,2)==((timer-1)&65535U));if(timer==1)assert(get(ram,0x10dd1f,1)==0&&get(ram,0x100965,1)==0&&get(ram,SP-4,4)==0x47fca);}
}
void queue_setup(Bytes&ram){put(ram,0x100012,1,0);put(ram,0x104d8a,2,0);put(ram,0x104d8c,2,0);put(ram,0x104d74,2,0xffff);put(ram,0x104d7e,1,0);}
void sequence(){Bytes ram(65536,0);queue_setup(ram);ms5::AnimationMachineState s=state(0x47f4a);Out o;assert(run(ram,s,0x480bc,o)&&s.a[7]==SP&&get(ram,0x104d7e,1)==0&&get(ram,0x102000,4)==0x47fa8&&get(ram,0x10207a,2)==31);
 assert(get(ram,0x104cf4,1)==8&&get(ram,0x104cf5,1)==0x20&&get(ram,0x104cf6,1)==0x18&&get(ram,0x104cf7,1)==0x90&&get(ram,SP-4,4)==0xabcd1820);
 // Live LONG restoration controls the subsequent BYTE comparison, including high halves.
 for(unsigned int byte=0;byte<2;++byte){ram.assign(65536,0);put(ram,SP,4,0xface8000U|byte);s=state(0x47f82);o=Out();assert(run(ram,s,0x47f9c,o)&&s.a[7]==SP+4);if(byte)assert(s.d[0]==0xface8001);else assert(get(ram,0x107dca,2)==0xe100&&get(ram,0x107dcc,2)==0xe100);}
 // Nested WORD overflow waits after the actual LONG MOVEM save.
 ram.assign(65536,0);queue_setup(ram);put(ram,0x104d8c,2,6);put(ram,0x104d82,2,0x0455);put(ram,0x104d74,2,1);s=state(0x47f74);s.d[0]=0xface8000;o=Out();assert(run(ram,s,0x480bc,o)&&s.pc==0x3aea&&s.a[7]==SP-14&&get(ram,SP-4,4)==0xface8000&&get(ram,SP-8,4)==0x47f82);
 put(ram,SP-4,4,0x87658001);put(ram,SP-10,1,0x77);put(ram,0x104d82,2,0xaaaa);ms5::AnimationMachineState before=s;Bytes hold=ram;assert(run(ram,s,0x480bc,o)&&same(s,before)&&ram==hold);
 put(ram,0x104d74,2,2);assert(run(ram,s,0x480bc,o)&&s.pc==0x3aea&&s.a[7]==SP-8);before=s;hold=ram;assert(run(ram,s,0x480bc,o)&&same(s,before)&&ram==hold);put(ram,0x104d74,2,0xffff);assert(run(ram,s,0x480bc,o)&&s.a[7]==SP&&s.d[0]==0x87658001&&get(ram,0x104cf5,1)==0x77&&get(ram,0x10207a,2)==31);
}
void errors(){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x1c648);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"requires known carry");s.pc=0x1c664;reject(ram,s,STOP,"requires known carry");
 s=state(0x48398);reject(ram,s,STOP,"program bus ROM");s=state(0x47eac);reject(ram,s,0x47f0a,"program bus ROM");
 s=state(0x47f9c);s.a[6]=0x0ffffe;reject(ram,s,STOP,"write device");
 s=state(0x8c16);s.a[7]=0x107dc8;s.d[0]=1;s.d[1]=2;s.d[2]=3;s.d[3]=32;reject(ram,s,STOP,"unsupported animation machine PC");
 s=state(0x47f74);s.a[7]=0x100002;reject(ram,s,STOP,"RAM");
 s=state(0x47f0a);s.a[6]=0x102001;reject(ram,s,STOP,"even WORD/LONG");
 s=state(0x47fa8);s.a[6]=SP-0x7a;put(ram,SP,4,1);reject(ram,s,STOP,"unsupported animation machine PC");
 s=state(0x47f8a);reject(ram,s,STOP,"unsupported animation exit PC"); // Z-only BNE is not an arbitrary entry.
 s=state(0x47fca);reject(ram,s,STOP,"unsupported animation machine PC");
}
}
int main(){preserving();helpers();palette();entry_and_countdown();sequence();errors();std::cout<<"animation_machine_exit_test PASS "<<calls<<" API invocations\n";}
