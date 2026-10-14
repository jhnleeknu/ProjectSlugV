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
void preserving(){
 const std::uint32_t cs[][3]={{0x271c,0x8eb6,0x2722},{0x2722,0x43dcc,0x2728},{0x2728,0xc3dc,0x272e},{0x2782,0x8ff4,0x2788},{0x2788,0xc3fa,0x278e},{0x29a8,0x2782,0x29ac},{0x29c0,0x287e,0x29c4},{0x29c8,0x271c,0x29ce},{0x2a1a,0x299c,0x2a1c},{0x2a3c,0x299c,0x2a40},{0x2a58,0x299c,0x2a5c},{0x2a7c,0x2a0a,0x2a80},{0x2aa0,0x2a0a,0x2aa4},{0x2aa4,0x299c,0x2aa8},{0x9028,0x8e4a,0x902c},{0xc3e6,0x4aa06,0xc3ec},{0xc3ec,0xe90ca,0xc3f2},{0xc3f2,0x46eec,0xc3f8},{0xc3fa,0x46ef4,0xc400},{0x46f26,0x43e38,0x46f2c},{0x477c2,0x2a0a,0x477c8},{0x477c8,0x2a84,0x477d4},{0x477d6,0x8bbc,0x477dc},{0x477dc,0x3dce,0x477e2},{0x47fe4,0x477c2,0x47fe8}};
 const std::uint32_t rt[]={0x2780,0x278e,0x288a,0x29fe,0x2a46,0x2a5e,0x2a82,0x2aaa,0x8ebc,0x9036,0x8e80,0x43dd8,0x43e02,0x43e90,0x43ea2,0xc3f8,0xc400,0x4aa2e,0xe90d6,0x46ef2,0x46f2c,0x8bc0,0x3de4,0x477e2};
 for(unsigned int carry=0;carry<3;++carry){
  for(unsigned int i=0;i<sizeof(cs)/sizeof(cs[0]);++i){Bytes ram(65536,0);ms5::AnimationMachineState s=state(cs[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(carry);s.a[0]=0x102100;Out o;assert(run(ram,s,cs[i][1],o)&&s.a[7]==SP-4&&get(ram,SP-4,4)==cs[i][2]&&s.carry==carry);}
  for(unsigned int i=0;i<sizeof(rt)/sizeof(rt[0]);++i){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rt[i]);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;assert(run(ram,s,STOP,o)&&s.a[7]==SP+4&&s.carry==carry);}
 }
}
void palette(){
 const unsigned int refs[]={0,1,2,65535};
 for(unsigned int k=0;k<4;++k){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10201d,1,1);put(ram,0x102019,1,1);put(ram,0x104daa,2,refs[k]);put(ram,0x104da2,2,0x20);put(ram,0x104da4,2,0x30);put(ram,0x105d92,2,0x40);
  ms5::AnimationMachineState s=state(0x8ff4);Out o;assert(run(ram,s,STOP,o)&&s.d[7]==65535&&get(ram,0x10201d,1)==0&&s.a[7]==SP+4);
  assert(get(ram,0x104daa,2)==(refs[k]==2?1:refs[k]==1?0:refs[k]));
  if(refs[k]==1){assert(get(ram,SP-4,4)==0x902c&&get(ram,0x104da2,2)==0x40&&get(ram,0x104da4,2)==0x1000&&get(ram,0x105d92,2)==0x10&&get(ram,0x104dd4,2)==0x10&&get(ram,0x104dac,2)==65535&&get(ram,0x104dae,2)==65535&&get(ram,0x104db1,1)==2);}
 }
 // Zero palette count skips the invalid palette/source span entirely.
 Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x8ff4);s.a[5]=0;Out o;assert(run(ram,s,STOP,o)&&s.d[7]==65535&&s.a[1]==0x87654322);
 // Four slots descend, includingduplicateindices and live rereads.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x10201d,1,4);for(unsigned int i=0;i<4;++i)put(ram,0x102019+i,1,2);put(ram,0x104dba,2,5);s=state(0x8ff4);o=Out();assert(run(ram,s,STOP,o)&&get(ram,0x104dba,2)==1&&s.d[0]==0x20&&s.d[7]==65535);
}
void reset(){Bytes ram(65536,0x57);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x271c);s.a[0]=0x102000;Out o;assert(run(ram,s,STOP,o)&&s.a[0]==0x102000&&s.d[0]==0&&s.d[1]==0xffffffff&&s.a[7]==SP+4&&o.ports.empty());
 assert(get(ram,0x10201d,1)==0&&get(ram,0x102012,2)==65535&&get(ram,0x10201e,2)==65535&&get(ram,0x10206e,2)==0x40&&get(ram,0x10206a,2)==255&&get(ram,0x10206c,1)==255&&get(ram,0x102017,1)==255&&get(ram,0x10205a,2)==65535);
 for(unsigned int i=0;i<0x4e;++i)assert(ram[0x2076+i]==0);
 // Direct tail publication overwrites the actual RTS slot.
 ram.assign(65536,0);put(ram,SP,4,STOP);s=state(0x272e);s.a[0]=SP-0x76;o=Out();assert(run(ram,s,0,o)&&s.pc==0&&get(ram,SP,4)==0&&s.a[7]==SP+4);
}
void coordinate(){
 for(unsigned int mode=0;mode<3;++mode){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x102000,4,0xffff8000);put(ram,0x102004,4,0x1234ffff);put(ram,0x102010,4,0x103000);put(ram,0x103014,4,0x80008000);put(ram,0x103018,4,0x87650001);put(ram,0x103025,1,0x80);put(ram,0x102014,4,0x11223344);put(ram,0x102018,4,0x55667788);put(ram,0x10d494,1,7);put(ram,0x102024,1,mode==0?0:mode==1?7:8);
  ms5::AnimationMachineState s=state(0x43e38);s.a[0]=0x102000;const std::uint32_t upper=s.d[6]&0xffff0000U;Out o;assert(run(ram,s,STOP,o)&&s.d[0]==0x80000000&&s.d[1]==0x999a0000&&s.d[6]==upper&&s.d[7]==0x83&&get(ram,0x102025,1)==0x83&&get(ram,0x102014,4)==s.d[0]&&get(ram,0x102018,4)==s.d[1]);
  assert(get(ram,0x10201c,4)==(mode==0?s.d[0]:mode==1?0:0x11223344));assert(get(ram,0x102020,4)==(mode==0?s.d[1]:mode==1?0:0x55667788));
 }
 // MOVEM source reads precede publication even when parent is the samenode.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x102000,4,1);put(ram,0x102004,4,2);put(ram,0x102010,4,0x102000);put(ram,0x102014,4,3);put(ram,0x102018,4,4);ms5::AnimationMachineState s=state(0x43e38);s.a[0]=0x102000;Out o;assert(run(ram,s,STOP,o)&&s.d[0]==4&&s.d[1]==6&&get(ram,0x102014,4)==4&&get(ram,0x102018,4)==6);
 for(unsigned int i=0;i<8;++i){ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x10206c,1,i);s=state(0x46ef4);o=Out();assert(run(ram,s,STOP,o)&&s.a[0]==0x10d4e6+i*0x2c&&get(ram,s.a[0]+0x26,2)==65535&&get(ram,s.a[0]+0x2a,2)==2&&get(ram,0x10206c,1)==255&&get(ram,SP-4,4)==0x46f2c);}
}
void objects(){
 // Typezero tail-jumps to reset and returns to the originalcaller, no extra push.
 Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x10206c,1,255);ms5::AnimationMachineState s=state(0x299c);Out o;assert(run(ram,s,STOP,o)&&get(ram,0x102000,4)==0x270e&&s.a[7]==SP+4&&o.ports.size()==1&&o.ports[0].address==0x300001&&o.ports[0].value==0x34);
 // CarrySet comparison returns without unlinking typedobject.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x10206c,1,255);put(ram,0x102010,2,1);put(ram,0x102008,4,0x102200);put(ram,0x102210,2,2);s=state(0x299c);o=Out();assert(run(ram,s,STOP,o)&&s.carry==ms5::AnimationCarrySet&&s.a[6]==0x102000&&s.a[0]==0x102200&&get(ram,0x102010,2)==1);
 // Removeone typednode, updatealllive links and freehead/count, thenstopat nonmarkerprevious.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x10206c,1,255);put(ram,0x102010,2,2);put(ram,0x102004,4,0x102100);put(ram,0x102008,4,0x102200);put(ram,0x102210,2,1);put(ram,0x102100,4,0x12345678);put(ram,0x104c9c,4,0x103000);s=state(0x299c);o=Out();assert(run(ram,s,STOP,o)&&s.a[6]==0x102100&&get(ram,0x102204,4)==0x102100&&get(ram,0x102108,4)==0x102200&&get(ram,0x102008,4)==0x103000&&get(ram,0x104c9c,4)==0x102000&&get(ram,0x104ca0,2)==1);
 // Fullwrapper savesactualA6/A1/A0 LONGs; finalcallback comesfromstack.
 for(unsigned int entry=0;entry<2;++entry){ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x10206c,1,255);s=state(entry?0x2a48:0x2a28);s.a[0]=0x102000;s.a[1]=0x12345678;s.a[6]=0x103000;o=Out();assert(run(ram,s,STOP,o)&&s.a[6]==0x103000&&s.a[7]==SP+4&&get(ram,0x102000,4)==(entry?0x270e:0x12345678));}
 // Traversal removesnext typednode before restoringparent via livepreviouslink.
 ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x102000,4,0x1234);put(ram,0x102004,4,0x102000);put(ram,0x102008,4,0x102200);put(ram,0x102200,4,0x4567);put(ram,0x102204,4,0x102000);put(ram,0x102208,4,0x102400);put(ram,0x102210,2,1);put(ram,0x10226c,1,255);put(ram,0x102404,4,0x102200);s=state(0x2a0a);o=Out();assert(run(ram,s,STOP,o)&&s.a[6]==0x102000&&get(ram,0x102008,4)==0x102400&&get(ram,0x102404,4)==0x102000&&get(ram,0x104c9c,4)==0x102200);
}
void wrapper_boundaries(){
 const std::uint32_t pops[][2]={{0x2a44,0x2a46},{0x2a5c,0x2a5e},{0x2a80,0x2a82},{0x2aa8,0x2aaa}};
 for(unsigned int carry=0;carry<3;++carry){
  Bytes ram(65536,0);put(ram,SP,4,0x102000);put(ram,SP+4,4,0x12345678);ms5::AnimationMachineState s=state(0x2a40);s.carry=static_cast<ms5::AnimationCarryState>(carry);Out o;
  const Bytes before=ram;assert(run(ram,s,0x2a42,o)&&s.a[0]==0x102000&&s.a[7]==SP+4&&s.carry==carry&&ram==before);
  assert(run(ram,s,0x2a44,o)&&s.a[7]==SP+8&&s.carry==ms5::AnimationCarryUnknown&&get(ram,0x102000,4)==0x12345678);
  for(unsigned int i=0;i<4;++i){ram.assign(65536,0);put(ram,SP,4,0xffff3400);s=state(pops[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(carry);o=Out();assert(run(ram,s,pops[i][1],o)&&s.a[6]==0xffff3400&&s.a[7]==SP+4&&s.carry==carry);}
 }
 // A popped callback LONG writes one RAMWORD before failing at the nextunit;
 // the public transaction restores both RAM and the actual stackpointer.
 Bytes ram(65536,0);put(ram,SP,4,0x12345678);ms5::AnimationMachineState s=state(0x2a42);s.a[0]=0x1ffffe;reject(ram,s,0x2a44,"unsupported animation machine write device");
}
void live_aliases(){
 // Wrapper reset mutates savedA6 in sharedstack; pop must consume actualbytes.
 Bytes ram(65536,0);put(ram,SP,4,0xfff000);ms5::AnimationMachineState s=state(0x2a28);s.a[0]=SP-0x16;s.a[1]=0x12340000;s.a[6]=0x103456;put(ram,s.a[0]+0x10,2,0);put(ram,s.a[0]+0x6c,1,255);Out o;
 const Bytes initial=ram;const ms5::AnimationMachineState incoming=s;
 assert(run(ram,s,0x2a46,o)&&s.a[6]==0xffff3400&&s.a[7]==SP&&get(ram,SP-0x16,4)==0x12340000);
 assert(get(ram,SP,4)==0xfff000&&o.ports.size()==1);
 assert(run(ram,s,0xfff000,o)&&s.pc==0xfff000&&s.a[7]==SP+4&&o.ports.empty());
 Bytes continuous=initial;ms5::AnimationMachineState control=incoming;Out uninterrupted;
 assert(run(continuous,control,0xfff000,uninterrupted)&&same(s,control)&&ram==continuous&&uninterrupted.ports.size()==1);
 // Releasing a node reads the freehead from the live returnslot then publishes
 // D0 back to that slot. RTS uses the newly published LONG, not savedmetadata.
 ram.assign(65536,0);put(ram,SP,4,0x100000);s=state(0x8e4a);s.a[1]=SP-0x1000;s.a[2]=0x104000;s.d[0]=0xface1234;put(ram,s.a[2],2,0x20);put(ram,s.a[2]+2,2,0x40);o=Out();assert(run(ram,s,0x12340000,o)&&get(ram,SP,4)==0x12340000&&s.d[3]==0xabd00010&&s.a[7]==SP+4);
 // Unsigned WORD comparison ignores highregisterbits, including the signbit.
 const unsigned int lhs[]={0,0x7fff,0x8000,0xffff};
 for(unsigned int i=0;i<4;++i)for(unsigned int j=0;j<4;++j){ram.assign(65536,0);put(ram,SP,4,STOP);put(ram,0x102008,4,0x103000);put(ram,0x102010,2,lhs[i]);put(ram,0x103010,2,lhs[j]);s=state(0x287e);o=Out();assert(run(ram,s,STOP,o)&&s.d[0]==(0xabcd0000U|lhs[i])&&s.carry==(lhs[i]<lhs[j]?ms5::AnimationCarrySet:ms5::AnimationCarryClear));}
}
void upper(){Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x102004,4,0x102000);put(ram,0x102008,4,0x102000);put(ram,0x100bf8,4,0x100bf4);put(ram,0x100bfc,4,0x100bf4);put(ram,0x100c60,1,255);put(ram,0x104d91,1,255);ms5::AnimationMachineState s=state(0x47fe4);Out o;assert(run(ram,s,0x47fe8,o)&&s.a[7]==SP&&get(ram,SP-4,4)==0x47fe8&&get(ram,0x107dec,1)==0&&get(ram,0x104d91,1)==0xef&&get(ram,0x100006,4)==0x3dcc&&get(ram,0x10000a,4)==0x3dcc&&s.a[0]==0x3dcc&&s.d[0]==0);}
void errors(){Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x29c4);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"known carry");s=state(0x2a16);s.carry=ms5::AnimationCarryUnknown;reject(ram,s,STOP,"known carry");
 s=state(0x2a28);s.a[0]=0x102000;put(ram,0x102010,2,1);reject(ram,s,STOP,"TRAP15");s=state(0x46ef4);put(ram,0x10206c,1,8);reject(ram,s,STOP,"TRAP15");
 s=state(0x271c);s.a[0]=0x1fffb0;reject(ram,s,STOP,"write device");s=state(0x43e38);s.a[0]=0x1ffff0;reject(ram,s,STOP,"ROM");
 s=state(0x8ff4);put(ram,0x10201d,1,1);put(ram,0x102019,1,1);s.a[5]=0;reject(ram,s,STOP,"unsupported");
 s=state(0x8eb6);put(ram,SP,4,0x10fe44);s.a[0]=0x102000;reject(ram,s,STOP,"unsupported animation machine PC");
 s=state(0x2a34);s.a[7]=0x100008;reject(ram,s,STOP,"RAM");
 // PlainMOVE.Lpush clearsC; arbitraryentry cannot retain callerknownC.
 ram.assign(65536,0);s=state(0x2a34);s.a[0]=0x102000;Out o;assert(run(ram,s,0x2a3c,o)&&s.carry==ms5::AnimationCarryUnknown&&s.a[7]==SP-12&&get(ram,SP-12,4)==0x102000);
}
}
int main(){preserving();palette();reset();coordinate();objects();wrapper_boundaries();live_aliases();upper();errors();std::cout<<"animation_machine_cleanup_test PASS "<<calls<<" API invocations\n";}
