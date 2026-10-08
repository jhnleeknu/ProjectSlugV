#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
unsigned int calls=0;
void put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes& b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
ms5::AnimationMachineState state(std::uint32_t pc){ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654320U+i*2;}s.a[5]=0x108000;s.a[7]=SP;return s;}
bool same(const ms5::AnimationMachineState&a,const ms5::AnimationMachineState&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
struct Out{ms5::AnimationMachineDevice dev;std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
 Out():reads(99),status(ms5::AnimationMachineWaiting){dev.bank_base=0x345678;dev.pvc.assign(8192,0x79);ms5::VideoPortWrite p;p.address=0xdeadbeef;p.size=1;p.value=0x87;ports.push_back(p);}};
bool run(Bytes&ram,ms5::AnimationMachineState&s,std::uint32_t stop,Out&o){++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource>w;return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
void reject(Bytes ram,ms5::AnimationMachineState s,std::uint32_t stop,const char*message){const Bytes old=ram;const ms5::AnimationMachineState before=s;Out o;const ms5::AnimationMachineDevice dev=o.dev;
 assert(!run(ram,s,stop,o));if(o.error.find(message)==std::string::npos)std::cerr<<o.error<<" expected "<<message<<"\n";
 assert(o.error.find(message)!=std::string::npos&&ram==old&&same(s,before)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base);
 assert(o.reads==99&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef&&o.ports[0].value==0x87&&o.ports[0].size==1);
}
void helpers(){const unsigned int values[]={0,1,2,5,128,255};
 for(unsigned int shift=0;shift<2;++shift)for(unsigned int x=0;x<6;++x)for(unsigned int y=0;y<6;++y){Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x4e216);s.a[5]+=shift;put(ram,SP,4,STOP);put(ram,s.a[5]-0x75bc,1,values[x]);put(ram,s.a[5]-0x74f8,1,values[y]);Bytes old=ram;ms5::AnimationMachineState want=s;
  bool first=values[x]==0||values[x]==5;bool set=first&&(values[y]==0||values[y]==5);want.d[0]=(want.d[0]&0xffffff00U)|(first?values[y]:values[x]);want.carry=set?ms5::AnimationCarrySet:ms5::AnimationCarryClear;want.pc=STOP;want.a[7]+=4;Out o;
  assert(run(ram,s,STOP,o)&&same(s,want)&&ram==old&&o.ports.empty()&&o.reads==0);
 }
 // First BYTE is valid at RAM's end and skips the out-of-domain second BYTE.
 for(unsigned int x=1;x<=2;++x){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x1fffff,1,x);ms5::AnimationMachineState s=state(0x4e216);s.a[5]=0x2075bb;Out o;assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarryClear&&(s.d[0]&255U)==x);}
 for(unsigned int x=0;x<6;++x)for(unsigned int y=0;y<6;++y)for(unsigned int request=0;request<2;++request){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10f004,1,request?255:0);put(ram,0x10fdb6,1,values[x]);put(ram,0x10fdb7,1,values[y]);Bytes want=ram;ms5::AnimationMachineState s=state(0xbee),expected=s;bool first=values[x]==1||values[x]==2;bool set=first||values[y]==1||values[y]==2;
  expected.d[0]=(expected.d[0]&0xffffff00U)|(request?255:0);expected.d[1]=(expected.d[1]&0xffffff00U)|(first?values[x]:values[y]);expected.a[0]=first?0x10fdb7:0x10fdb8;expected.a[7]+=4;expected.pc=STOP;expected.carry=set?ms5::AnimationCarrySet:ms5::AnimationCarryClear;if(!set)put(want,0x10f004,1,0);Out o;
  assert(run(ram,s,STOP,o)&&same(s,expected)&&ram==want&&o.ports.empty());
 }
 // The request BYTE is part of the live return LONG, not a separate fixture value.
 for(unsigned int occupied=0;occupied<2;++occupied){Bytes ram(65536,0);put(ram,0x10f002,4,0x47d34);put(ram,0x10fdb6,1,occupied);ms5::AnimationMachineState s=state(0xbee);s.a[7]=0x10f002;Out o;
  if(occupied){assert(run(ram,s,0x47d3e,o)&&s.a[7]==0x10f006&&s.carry==ms5::AnimationCarrySet&&get(ram,0x10f004,1)==0x7d);}
  else {reject(ram,s,0x47d3e,"unsupported animation machine PC");assert(run(ram,s,0x40034,o)&&s.a[7]==0x10f006&&get(ram,0x10f004,1)==0&&s.carry==ms5::AnimationCarryClear);}
 }
 // JSR's return LONG overwrites the first helper BYTE before that BYTE is read.
 Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x47d24);s.a[5]=SP-4+0x75bc;put(ram,SP-4,1,2);put(ram,s.a[5]-0x74f8,1,5);Out o;
 assert(run(ram,s,0x47d2e,o)&&s.carry==ms5::AnimationCarrySet&&s.a[7]==SP&&get(ram,SP-4,4)==0x47d2a&&(s.d[0]&255U)==5);
}
void preserving(){const std::uint32_t jsr[][3]={{0x47d24,0x4e216,0x47d2a},{0x47d2e,0xbee,0x47d34},{0x47d58,0x477ac,0x47d5c},{0x47d92,0x3af8,0x47d98}};
 const std::uint32_t rts[]={0x4e246,0x4e24c,0xc28,0xc34,0x35ee};const std::uint32_t jumps[][2]={{0x47d5c,0x477ee},{0x47d98,0x47da0},{0x47da0,0x480bc},{0x477bc,0x35a2},{0x35a8,0x35ae}};
 for(unsigned int f=0;f<3;++f){ms5::AnimationCarryState carry=static_cast<ms5::AnimationCarryState>(f);
  for(unsigned int i=0;i<4;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(jsr[i][0]);s.carry=carry;Out o;assert(run(ram,s,jsr[i][1],o)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==jsr[i][2]);}
  for(unsigned int i=0;i<5;++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rts[i]);s.carry=carry;Out o;assert(run(ram,s,STOP,o)&&s.carry==carry&&s.a[7]==SP+4);}
  for(unsigned int i=0;i<5;++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(jumps[i][0]);s.carry=carry;Out o;assert(run(ram,s,jumps[i][1],o)&&s.carry==carry);}
 }
 const std::uint32_t branches[][3]={{0x47d2a,0x47d3e,0x47d2e},{0x47d34,0x47d38,0x47d3e}};
 for(unsigned int i=0;i<2;++i)for(unsigned int f=1;f<3;++f){Bytes ram(65536,0);ms5::AnimationMachineState s=state(branches[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(f);Out o;assert(run(ram,s,branches[i][f],o)&&s.carry==static_cast<ms5::AnimationCarryState>(f));}
}
void fill(){const unsigned int lengths[]={0,1,3};
 for(unsigned int x=0;x<3;++x)for(unsigned int y=0;y<3;++y){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x35a2);s.d[0]=0xabcd7162;s.d[1]=0x89abcdef;s.d[2]=0xcccc0000|lengths[x];s.d[3]=0xdddd0000|lengths[y];const std::uint32_t d6=s.d[6],d7=s.d[7];Out o;
  assert(run(ram,s,STOP,o)&&o.ports.size()==lengths[x]*lengths[y]+3&&s.a[4]==0x3c0000&&s.a[7]==SP+4&&s.carry==ms5::AnimationCarryUnknown);
  assert(o.ports[0].address==0x300001&&o.ports[0].size==1&&o.ports[0].value==0x62);
  for(unsigned int col=0;col<lengths[x];++col)for(unsigned int row=0;row<lengths[y];++row){const ms5::VideoPortWrite&p=o.ports[1+col*lengths[y]+row];assert(p.address==0x3c0000&&p.size==4&&p.value==(((0x7162+32*col+row)<<16)|0xcdefU));}
  assert(o.ports[o.ports.size()-2].address==0x3c0004&&o.ports[o.ports.size()-2].size==2&&o.ports[o.ports.size()-2].value==0);
  assert(o.ports.back().address==0x3c0000&&o.ports.back().size==4&&o.ports.back().value==0x82000000);
  assert(s.d[0]==(0xabcd0000U|((0x7162+32*lengths[x])&65535U))&&s.d[1]==0x89abcdef&&s.d[2]==0xcccc0000U&&s.d[3]==(0xdddd0000U|lengths[y]));
  assert(s.d[6]==(lengths[x]?(d6&0xffff0000U):d6));if(!lengths[x])assert(s.d[7]==d7);
 }
 // Constants use WORD moves and retain all input high halves; tail JMP adds no frame.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x477ac);const std::uint32_t high=s.d[0]&0xffff0000U;Out o;
 assert(run(ram,s,STOP,o)&&s.d[0]==(high|0x73a2)&&o.ports.size()==147&&s.a[7]==SP+4);
 // Direct live A4 RAM destination receives two WORD bus writes, then final LONG.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0x35c0);s.a[4]=0x1f4000;s.d[7]=0x12345678;s.d[6]=1;s.d[2]=1;o=Out();
 assert(run(ram,s,STOP,o)&&get(ram,0x104000,4)==0x82000000&&o.ports.size()==1&&o.ports[0].address==0x3c0004);
 // The fill's final LONG can change its own live RTS target.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0x35e0);s.a[4]=SP;o=Out();assert(run(ram,s,0x82000000,o)&&s.a[7]==SP+4&&get(ram,SP,4)==0x82000000);
}
void upper(){
 for(unsigned int flag=0;flag<256;++flag){Bytes ram(65536,0);put(ram,0x10d684,1,flag);ms5::AnimationMachineState s=state(0x47d46);Out o;assert(run(ram,s,(flag&1)?0x47d58:0x47d5c,o)&&s.d[0]==(flag&1)&&s.carry==ms5::AnimationCarryUnknown);}
 for(unsigned int flag=0;flag<2;++flag){Bytes ram(65536,0);put(ram,0x10d684,1,flag);ms5::AnimationMachineState s=state(0x47d46);Out o;assert(run(ram,s,0x477ee,o)&&s.a[7]==SP&&o.ports.size()==(flag?147:0));if(flag)assert(get(ram,SP-4,4)==0x47d5c);}
 for(unsigned int request=0;request<2;++request)for(unsigned int bit=0;bit<2;++bit){Bytes ram(65536,0);put(ram,0x10d681,1,128);put(ram,0x10d68e,1,request);put(ram,0x10d683,1,bit);ms5::AnimationMachineState s=state(0x47d46);Out o;assert(run(ram,s,(request&&bit)?0x47da4:0x47d72,o)&&s.a[7]==SP);}
 // Full helper/caller outcomes stop at existing readiness or external boundaries.
 for(unsigned int mode=0;mode<3;++mode){Bytes ram(65536,0);put(ram,0x100a44,1,mode==0?2:0);put(ram,0x100b08,1,5);put(ram,0x10fdb6,1,mode==1?1:0);put(ram,0x10f004,1,0x91);ms5::AnimationMachineState s=state(0x47d24);Out o;assert(run(ram,s,mode==2?0x47f4a:0x47d3e,o)&&s.a[7]==SP);if(mode==2)assert(s.d[0]==0&&get(ram,0x10f004,1)==0);}
 const unsigned int pending[]={0,0x0120,0x0455,0x0455};const unsigned int timer[]={0,0,1,65535};
 for(unsigned int i=0;i<4;++i){Bytes ram(65536,0);put(ram,0x10d688,2,pending[i]);put(ram,0x10d68a,2,timer[i]);ms5::AnimationMachineState s=state(0x47d72);Out o;assert(run(ram,s,0x480bc,o)&&s.d[0]==(0xabcd0000U|pending[i])&&s.a[7]==SP);assert(get(ram,0x10d68a,2)==(timer[i]?(timer[i]-1):0));if(i==1)assert(get(ram,0x10d688,2)==0&&get(ram,0x10d686,2)==0x120&&get(ram,SP-4,4)==0x47d98);}
 Bytes ram(65536,0);put(ram,0x10d688,2,0x0455);put(ram,0x10d686,2,0x0455);ms5::AnimationMachineState s=state(0x47d72);Out o;assert(run(ram,s,0x480bc,o)&&get(ram,0x10d688,2)==0x455&&get(ram,SP-4,4)==0);
}
void waits(){
 for(unsigned int kind=0;kind<3;++kind){Bytes ram(65536,0);put(ram,0x10d688,2,0x0666);put(ram,0x104d8c,2,6);put(ram,0x104d82,2,0x0455);put(ram,0x104d74,2,kind==1?2:1);ms5::AnimationMachineState s=state(0x47d72);Out o;
  assert(run(ram,s,0x480bc,o)&&o.status==ms5::AnimationMachineWaiting&&s.pc==0x3aea&&s.a[7]==SP-(kind==1?4:10)&&get(ram,SP-4,4)==0x47d98&&get(ram,0x10d688,2)==0&&get(ram,0x10d686,2)==0x666);
  put(ram,0x10d688,2,0x9999);put(ram,0x10d686,2,0x8888);put(ram,0x10d68a,2,0x7777);put(ram,0x104d82,2,0xaaaa);put(ram,SP-4,4,0x47da0);if(kind!=1)put(ram,SP-6,1,0x77);
  ms5::AnimationMachineState before=s;Bytes hold=ram;assert(run(ram,s,0x480bc,o)&&same(s,before)&&ram==hold&&o.status==ms5::AnimationMachineWaiting);
  put(ram,0x104d74,2,kind==2?2:0xffff);assert(run(ram,s,0x480bc,o));
  if(kind==2){assert(s.pc==0x3aea&&s.a[7]==SP-4&&o.status==ms5::AnimationMachineWaiting);before=s;hold=ram;assert(run(ram,s,0x480bc,o)&&same(s,before)&&ram==hold);put(ram,0x104d74,2,0xffff);assert(run(ram,s,0x480bc,o));}
  assert(s.pc==0x480bc&&s.a[7]==SP&&o.status==ms5::AnimationMachineReturned&&get(ram,0x10d688,2)==0x9999&&get(ram,0x10d686,2)==0x8888&&get(ram,0x10d68a,2)==0x7777);
  assert(get(ram,0x104cf4,1)==4&&get(ram,0x104cf5,1)==(kind==1?0x55:0x77));
 }
}
void errors(){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x47d2a);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"requires known carry");s.pc=0x47d34;reject(ram,s,STOP,"requires known carry");
 s=state(0x35bc);s.d[6]=0;reject(ram,s,STOP,"unsupported animation transition PC"); // Incoming Z is not represented by D6.
 s=state(0x35a2);s.d[0]=0x74ff;s.d[2]=1;s.d[3]=2;reject(ram,s,STOP,"TRAP15");
 s=state(0x35e0);s.a[4]=0x1ffffe;reject(ram,s,STOP,"unsupported animation machine write device"); // First RAM WORD succeeds; next is outside RAM.
 s=state(0x35e0);s.a[4]=0x104001;reject(ram,s,STOP,"alignment");
 // This valid 65535-column, zero-height fill now fits the raised finite budget.
 s=state(0x35a2);s.d[0]=0;s.d[2]=65535;s.d[3]=0;{const Bytes old=ram;Out o;
  assert(run(ram,s,STOP,o)&&ram==old&&s.pc==STOP&&s.a[7]==SP+4&&(s.d[0]&65535U)==0xffe0&&(s.d[2]&65535U)==0);
  assert(o.ports.size()==3&&o.ports[0].address==0x300001&&o.ports[0].value==0&&o.ports[1].address==0x3c0004&&o.ports[1].value==0&&o.ports[2].address==0x3c0000&&o.ports[2].value==0x82000000U);
 }
 s=state(0x4e216);s.a[5]=0x2075bb;put(ram,0x1fffff,1,0);reject(ram,s,STOP,"program bus ROM");
 s=state(0x47d8a);s.a[5]=0x1fa978;reject(ram,s,STOP,"unsupported animation machine write device"); // First WORD at1ffffe succeeds; second at200000 fails.
 s=state(0x47d92);s.a[7]=0x100002;reject(ram,s,STOP,"RAM");
 s=state(0x35a2);s.d[0]=0x7000;s.d[2]=s.d[3]=0;put(ram,SP,4,0xff001);reject(ram,s,STOP,"unaligned animation machine PC");
}
}
int main(){helpers();preserving();fill();upper();waits();errors();std::cout<<"animation_machine_transition_test PASS "<<calls<<" API invocations\n";}
