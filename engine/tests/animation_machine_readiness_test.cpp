#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
void put(Bytes& ram,std::uint32_t at,unsigned int size,std::uint32_t value) {
    for(unsigned int i=0;i<size;++i)ram[(at+i)&65535U]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
std::uint32_t get(const Bytes& ram,std::uint32_t at,unsigned int size) {
    std::uint32_t value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[(at+i)&65535U];return value;
}
ms5::AnimationMachineState initial(std::uint32_t pc) {
    ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;
    for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654321U+i*2;}
    s.a[5]=0x108000;s.a[7]=SP;return s;
}
bool same(const ms5::AnimationMachineState& a,const ms5::AnimationMachineState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;
    return a.pc==b.pc&&a.carry==b.carry;
}
struct Outputs {
    ms5::AnimationMachineDevice device;std::vector<ms5::VideoPortWrite> ports;
    std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
    Outputs():reads(99),status(ms5::AnimationMachineWaiting) {
        device.bank_base=0x345678;device.pvc.assign(8192,0x79);
        ms5::VideoPortWrite p;p.size=1;p.address=0xdeadbeef;p.value=0x87;ports.push_back(p);
    }
};
bool run(Bytes& ram,ms5::AnimationMachineState& s,std::uint32_t stop,Outputs& out) {
    ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource> windows;
    return ms5::run_animation_machine(ram,windows,bus,s,out.device,stop,255,out.reads,out.status,out.ports,out.error);
}
void reject(Bytes ram,ms5::AnimationMachineState s,const char* message) {
    const Bytes old=ram;const ms5::AnimationMachineState before=s;Outputs out;const ms5::AnimationMachineDevice device=out.device;
    assert(!run(ram,s,STOP,out));
    if(out.error.find(message)==std::string::npos)std::cerr<<out.error<<" expected "<<message<<"\n";
    assert(out.error.find(message)!=std::string::npos&&ram==old&&same(s,before));
    assert(device.pvc==out.device.pvc&&device.bank_base==out.device.bank_base&&out.reads==99&&out.status==ms5::AnimationMachineWaiting);
    assert(out.ports.size()==1&&out.ports[0].address==0xdeadbeef&&out.ports[0].value==0x87&&out.ports[0].size==1);
}
void boundaries() {
    const std::uint32_t returns[]={0x484ac,0x484b2,0x1be32,0x1be38,0x28ac,0x4df0e,0x4df18,0x4e184};
    const std::uint32_t calls[][3]={{0x47d3e,0x4847c,0x47d42},{0x4847e,0x1bdde,0x48484},
        {0x4848a,0x1bdde,0x48490},{0x4849c,0x4e166,0x484a2},{0x1bdee,0x289e,0x1bdf4},{0x1be0c,0x4dee2,0x1be12}};
    const std::uint32_t branches[][3]={{0x47d42,0x47d72,0x47d46},{0x48484,0x484ae,0x48488},
        {0x48490,0x484ae,0x48494},{0x1bdf4,0x1be2e,0x1bdf8},{0x1be12,0x1be2e,0x1be16}};
    for(unsigned int flag=0;flag<3;++flag) {
        const ms5::AnimationCarryState carry=static_cast<ms5::AnimationCarryState>(flag);
        for(unsigned int i=0;i<8;++i) {
            Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=initial(returns[i]);s.carry=carry;Outputs out;
            assert(run(ram,s,STOP,out)&&s.carry==carry&&s.a[7]==SP+4);
        }
        for(unsigned int i=0;i<6;++i) {
            Bytes ram(65536,0);ms5::AnimationMachineState s=initial(calls[i][0]);s.carry=carry;Outputs out;
            assert(run(ram,s,calls[i][1],out)&&s.carry==carry&&s.a[7]==SP-4&&get(ram,SP-4,4)==calls[i][2]);
        }
        for(unsigned int i=0;i<5;++i) {
            Bytes ram(65536,0);ms5::AnimationMachineState s=initial(branches[i][0]);s.carry=carry;
            if(!flag)reject(ram,s,"requires known carry");
            else {Outputs out;assert(run(ram,s,branches[i][flag],out)&&s.carry==carry);}
        }
        Bytes ram(65536,0x53);ms5::AnimationMachineState s=initial(0x4847c),before=s;s.carry=before.carry=carry;Outputs out;
        const Bytes old=ram;assert(run(ram,s,s.pc,out)&&same(s,before)&&ram==old);
        s=initial(0x47d20);s.carry=carry;assert(run(ram,s,0x47d3e,out)&&s.carry==carry);
        for(unsigned int which=0;which<2;++which)for(unsigned int bit=0;bit<2;++bit) {
            ram.assign(65536,0);s=initial(which?0x1be02:0x1bdf8);s.carry=carry;s.a[0]=0x104000;
            put(ram,s.a[0]+(which?0x61:0xa8),1,bit?(which?128:16):0);
            const std::uint32_t stop=which?(bit?0x1be34:0x1be0c):(bit?0x1be2e:0x1be02);
            assert(run(ram,s,stop,out)&&s.carry==carry); // BTST updates only Z.
        }
    }
    const std::uint32_t writers[][2]={{0x484a8,2},{0x484ae,1},{0x1be2e,2},{0x1be34,1},{0x28a8,2},{0x4df0a,1}};
    for(unsigned int i=0;i<6;++i)for(unsigned int flag=0;flag<3;++flag) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=initial(writers[i][0]);s.carry=static_cast<ms5::AnimationCarryState>(flag);Outputs out;
        assert(run(ram,s,STOP,out)&&static_cast<unsigned int>(s.carry)==writers[i][1]);
    }
    const std::uint32_t invalidating[][2]={{0x4847c,0x4847e},{0x48488,0x4848a},{0x48494,0x4849c},
        {0x484a2,0x484a8},{0x1bdde,0x1bdee},{0x1be16,0x1be2e}};
    for(unsigned int i=0;i<6;++i) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=initial(invalidating[i][0]);Outputs out;
        assert(run(ram,s,invalidating[i][1],out)&&s.carry==ms5::AnimationCarryUnknown);
    }
}
void leaves() {
    const std::uint32_t markers[]={0,0x270e,0x270f,0xffffffff};
    for(unsigned int i=0;i<4;++i) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x104000,4,markers[i]);ms5::AnimationMachineState s=initial(0x289e);s.a[0]=0x1f4000;
        ms5::AnimationMachineState want=s;want.pc=STOP;want.a[7]+=4;want.carry=i==1?ms5::AnimationCarryClear:ms5::AnimationCarrySet;
        const Bytes old=ram;Outputs out;assert(run(ram,s,STOP,out)&&same(s,want)&&ram==old);
    }
    const unsigned int types[]={0,1,2,255},statuses[]={0,3,4,5,255};
    for(unsigned int player=0;player<2;++player)for(unsigned int negative=0;negative<2;++negative)
    for(unsigned int t=0;t<4;++t)for(unsigned int q=0;q<5;++q) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=initial(0x4dee2);s.d[0]=0xabcd8000U|player;
        const std::uint32_t a4=0x10dd12+6*player;put(ram,a4+4,2,negative?0x8000:0x7fff);put(ram,a4,1,types[t]);put(ram,a4+2,1,statuses[q]);
        ms5::AnimationMachineState want=s;want.d[0]=0xabcd0000U|player;want.a[4]=a4;want.pc=STOP;want.a[7]+=4;
        const bool ready=!negative&&(types[t]==1||types[t]==2);want.carry=ready?ms5::AnimationCarrySet:ms5::AnimationCarryClear;
        if(ready)want.d[1]=(want.d[1]&0xffffff00U)|statuses[q];
        const Bytes old=ram;Outputs out;assert(run(ram,s,STOP,out)&&same(s,want)&&ram==old);
    }
    for(unsigned int mask=0;mask<4;++mask) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,0x100a44,1,mask&1?2:3);put(ram,0x100b08,1,mask&2?2:1);
        ms5::AnimationMachineState s=initial(0x4e166),want=s;want.d[0]=mask;want.pc=STOP;want.a[7]+=4;want.carry=ms5::AnimationCarryUnknown;
        const Bytes old=ram;Outputs out;assert(run(ram,s,STOP,out)&&same(s,want)&&ram==old);
    }
    Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=initial(0x4df10);s.a[4]=0x104000;
    put(ram,0x104002,1,0x81);Outputs out;assert(run(ram,s,STOP,out)&&s.d[1]==0xabce1281&&s.carry==ms5::AnimationCarrySet);
}
// Controlled player fixtures; expected stack bytes include every real JSR.
void player_seed(Bytes& ram,unsigned int player,unsigned int kind) {
    const std::uint32_t a0=player?0x100da8:0x100cb8,a4=0x10dd12+6*player;
    put(ram,a0,4,kind==0?0x270e:0);put(ram,a0+0xa8,1,kind==1?16:0);put(ram,a0+0x61,1,kind==2?128:0);
    put(ram,a4+4,2,kind==5?0x8000:0);put(ram,a4,1,kind==6?0:1);put(ram,a4+2,1,kind==3?3:2);
}
bool player_expected(Bytes& ram,ms5::AnimationMachineState& want,unsigned int player,unsigned int kind) {
    put(ram,SP-4,4,player?0x48490:0x48484);put(ram,SP-8,4,0x1bdf4);want.d[0]=player;want.a[0]=player?0x100da8:0x100cb8;
    if(kind<2)return true;if(kind==2)return false;
    put(ram,SP-8,4,0x1be12);want.a[4]=0x10dd12+6*player;
    if(kind>=5)return true;want.d[1]=(want.d[1]&0xffffff00U)|(kind==3?3:2);return kind!=3;
}
void whole_chain() {
    for(unsigned int first=0;first<7;++first)for(unsigned int second=0;second<7;++second)
    for(unsigned int global=0;global<2;++global)for(unsigned int mask=0;mask<4;++mask) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);player_seed(ram,0,first);player_seed(ram,1,second);
        put(ram,0x10d684,1,global);put(ram,0x100a44,1,mask&1?2:0);put(ram,0x100b08,1,mask&2?2:0);
        ms5::AnimationMachineState s=initial(0x4847c),want=s;Bytes expected=ram;
        bool ready=player_expected(expected,want,0,first);
        if(ready)ready=player_expected(expected,want,1,second);
        if(ready&&!global){put(expected,SP-4,4,0x484a2);want.d[0]=mask;ready=mask!=0;}
        want.carry=ready?ms5::AnimationCarrySet:ms5::AnimationCarryClear;want.pc=STOP;want.a[7]+=4;
        Outputs out;assert(run(ram,s,STOP,out)&&same(s,want)&&ram==expected&&out.ports.empty()&&out.reads==0);
    }
    for(unsigned int ready=0;ready<2;++ready) {
        Bytes ram(65536,0);player_seed(ram,0,ready?0:2);player_seed(ram,1,0);put(ram,0x10d684,1,1);
        ms5::AnimationMachineState s=initial(0x47d20);Outputs out;
        assert(run(ram,s,ready?0x47d46:0x47d72,out)&&s.a[7]==SP&&s.carry==(ready?ms5::AnimationCarrySet:ms5::AnimationCarryClear));
    }
    // JSR289e overwrites the marker before the original callee reads that live alias.
    Bytes ram(65536,0);put(ram,SP,4,STOP);put(ram,SP-4,4,0x270e);put(ram,SP-4+0xa8,1,16);
    ms5::AnimationMachineState s=initial(0x1bdde);s.a[5]=SP-4+0x7348;s.d[0]=0;Outputs out;
    assert(run(ram,s,STOP,out)&&s.carry==ms5::AnimationCarrySet&&get(ram,SP-4,4)==0x1bdf4&&s.a[0]==SP-4);
}
void failures() {
    Bytes ram(65536,0);put(ram,SP,4,STOP);
    ms5::AnimationMachineState s=initial(0x484a8);s.a[7]=SP-1;reject(ram,s,"even WORD/LONG");
    s=initial(0x4847c);s.a[5]=0x207346;reject(ram,s,"program bus ROM"); // Earlier nested JSRs already wrote RAM.
    s=initial(0x4dee2);s.a[5]=0x108001;reject(ram,s,"even WORD/LONG");
    s=initial(0x4e166);s.a[5]=0x2075bb;put(ram,0x1fffff,1,2);reject(ram,s,"program bus ROM");
    s=initial(0x289e);s.a[0]=0x104000;put(ram,SP,4,0x10fe44);reject(ram,s,"unsupported animation machine PC");
    s=initial(0x1bdf8);s.a[0]=0x1fffff;reject(ram,s,"program bus ROM");
}
}
int main(){boundaries();leaves();whole_chain();failures();std::cout<<"animation_machine_readiness_test PASS\n";}
