#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
void put(Bytes& ram,std::uint32_t address,unsigned int size,std::uint32_t value) {
    for(unsigned int i=0;i<size;++i)ram[(address+i)&65535U]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
ms5::AnimationMachineState state(std::uint32_t pc,ms5::AnimationCarryState carry) {
    ms5::AnimationMachineState s;s.pc=pc;s.carry=carry;s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=SP;
    s.a[0]=0x104000;s.a[1]=0x106000;s.d[0]=0xabcd0100;s.d[7]=0x12348001;return s;
}
bool same(const ms5::AnimationMachineState& a,const ms5::AnimationMachineState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;
    return a.pc==b.pc&&a.carry==b.carry;
}
struct Outputs {
    ms5::AnimationMachineDevice device;
    std::vector<ms5::VideoPortWrite> ports;
    std::uint32_t reads;
    ms5::AnimationMachineStatus status;
    std::string error;
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
    const Bytes before=ram;const ms5::AnimationMachineState old=s;Outputs out;
    const ms5::AnimationMachineDevice device=out.device;
    assert(!run(ram,s,STOP,out));
    if(out.error.find(message)==std::string::npos)std::cerr<<"PC "<<std::hex<<old.pc<<": "<<out.error<<"; expected "<<message<<"\n";
    assert(out.error.find(message)!=std::string::npos);
    assert(ram==before&&same(s,old)&&out.device.pvc==device.pvc&&out.device.bank_base==device.bank_base);
    assert(out.reads==99&&out.status==ms5::AnimationMachineWaiting&&out.ports.size()==1);
    assert(out.ports[0].address==0xdeadbeef&&out.ports[0].value==0x87&&out.ports[0].size==1);
}
void preserving_blocks() {
    const std::uint32_t rts[]={0x49fea,0x4a0e2,0x4a124,0x4a132,0x4a148,0x3679e,0x2b3f8,0x2b40a,
        0xcd50,0xcd56,0xce00,0x3ad6,0x3af6,0x3b06,0x3b14,0x3b1e,0x3b28,0x3b3e,0x3b5e,0x3b6c,
        0x3b80,0x3b96,0x3bc8,0x3be2,0x3c06,0xca74,0x476ba};
    const std::uint32_t transitions[][2]={{0x47d0a,0x47d10},{0x47d14,0x49f8c},{0x47d1a,0x49fc6},
        {0x47f04,0x49fc6},{0x1dc84,0x49fc6},{0x210ae,0x49fc6},{0x4a104,0x4a10c},{0x4a108,0x49ffe},
        {0x4a272,0x49ffe},{0x4a270,0x49ffe},{0x4a2ec,0x4a276},{0xcd58,0xcd50},{0x3ad8,0x3adc},
        {0x3ae0,0x3ae4},{0x3b98,0x3b9c},{0x3ba8,0x3bac},{0x3bca,0x3ba0},{0x3be4,0x3be8},
        {0x3bfc,0x3ac8},{0x3c02,0x3ac8},{0xca70,0xca74},{0x47672,0xca70},{0x47688,0x3af8},
        {0x4768e,0x47690},{0x476a4,0x476aa},{0x3b82,0x3b98}};
    for(unsigned int value=0;value<3;++value) {
        const ms5::AnimationCarryState carry=static_cast<ms5::AnimationCarryState>(value);
        for(unsigned int i=0;i<sizeof(rts)/sizeof(rts[0]);++i) {
            Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(rts[i],carry);Outputs out;
            assert(run(ram,s,STOP,out)&&s.carry==carry&&s.a[7]==SP+4&&s.pc==STOP);
        }
        for(unsigned int i=0;i<sizeof(transitions)/sizeof(transitions[0]);++i) {
            Bytes ram(65536,0);put(ram,SP,4,0x104900);put(ram,SP+4,4,0x106800);put(ram,0x109152,4,0xcd50);
            ms5::AnimationMachineState s=state(transitions[i][0],carry);Outputs out;
            assert(run(ram,s,transitions[i][1],out)&&s.carry==carry);
        }
        // Stop before a writer executes, with no bank or stack effects.
        Bytes ram(65536,0x53);ms5::AnimationMachineState s=state(0x4a0ca,carry),before=s;Outputs out;
        const Bytes old=ram,pvc=out.device.pvc;const std::uint32_t bank=out.device.bank_base;
        assert(run(ram,s,s.pc,out)&&same(s,before)&&ram==old&&out.device.pvc==pvc&&out.device.bank_base==bank);
    }
}
void known_writers_and_callers() {
    const std::uint32_t values[]={0,1,0x8000,0x8001,0xffff,0x12348000,0xabcd8001};
    for(unsigned int i=0;i<7;++i) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);ms5::AnimationMachineState s=state(0x4a0ca,ms5::AnimationCarryUnknown);
        s.d[7]=values[i];Outputs out;assert(run(ram,s,STOP,out));
        assert(s.carry==((values[i]&1)?ms5::AnimationCarrySet:ms5::AnimationCarryClear));
        assert(s.d[7]==((values[i]&0xffff0000U)|((values[i]&65535U)>>1)|(values[i]&0x8000U)));
    }
    for(unsigned int kind=0;kind<2;++kind) {
        Bytes ram(65536,0);put(ram,SP,4,STOP);
        ms5::AnimationMachineState s=state(kind?0x49f8c:0x49fc6,kind?ms5::AnimationCarrySet:ms5::AnimationCarryClear);Outputs out;
        assert(run(ram,s,STOP,out));assert(s.carry==(kind?ms5::AnimationCarryClear:ms5::AnimationCarrySet));
    }
    for(unsigned int which=0;which<2;++which)for(unsigned int flag=0;flag<2;++flag) {
        const std::uint32_t pc=which?0x210b4:0x1dc8a;
        const std::uint32_t target=which?(flag?0x21564:0x210b8):(flag?0x1dc8e:0x1dccc);
        Bytes ram(65536,0);ms5::AnimationMachineState s=state(pc,flag?ms5::AnimationCarrySet:ms5::AnimationCarryClear);Outputs out;
        assert(run(ram,s,target,out)&&s.pc==target&&s.carry==(flag?ms5::AnimationCarrySet:ms5::AnimationCarryClear));
    }
    for(unsigned int which=0;which<2;++which)for(unsigned int null_script=0;null_script<2;++null_script) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=state(which?0x210ae:0x1dc84,ms5::AnimationCarryUnknown);
        if(!null_script)put(ram,s.a[6]+0x26,4,0x106000); // RAM00/duration0 yields ASR of zero.
        const std::uint32_t target=which?(null_script?0x21564:0x210b8):(null_script?0x1dc8e:0x1dccc);
        Outputs out;assert(run(ram,s,target,out)&&s.a[7]==SP);
        assert(s.carry==(null_script?ms5::AnimationCarrySet:ms5::AnimationCarryClear));
    }
    // The actual initializer overwrites its return slot, then known C survives RTS into BCC.
    Bytes ram(65536,0);ms5::AnimationMachineState s=state(0x49f8c,ms5::AnimationCarryUnknown);
    s.a[6]=SP-0x26;s.a[1]=0x1dc8a;Outputs out;assert(run(ram,s,0x1dccc,out)&&s.carry==ms5::AnimationCarryClear);
}
void unknown_and_rollback() {
    const std::uint32_t transitions[][2]={{0x47cec,0x47d0a},{0x47d10,0x47d14},{0x49fc6,0x49ffe},
        {0x4a300,0x4a276},{0x3ae4,0x3ae6},{0x3ae6,0x3aea},{0x47682,0x47684}};
    for(unsigned int i=0;i<7;++i) {
        Bytes ram(65536,0);put(ram,0x102026,4,0x106000);ms5::AnimationMachineState s=state(transitions[i][0],ms5::AnimationCarrySet);Outputs out;
        if(transitions[i][0]==0x4a300)s.a[1]=0x106001; // Post-opcode A1; padding precedes the aligned WORD.
        assert(run(ram,s,transitions[i][1],out)&&s.carry==ms5::AnimationCarryUnknown);
    }
    for(unsigned int i=0;i<2;++i) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=state(i?0xcda4:0x3aea,ms5::AnimationCarrySet);Outputs out;
        if(i)put(ram,0x108d34,2,1);
        assert(run(ram,s,STOP,out)&&out.status==ms5::AnimationMachineWaiting&&s.carry==ms5::AnimationCarryUnknown);
    }
    Bytes ram(65536,0);put(ram,SP,4,STOP);
    reject(ram,state(0x1dc8a,ms5::AnimationCarryUnknown),"known carry");
    reject(ram,state(0x210b4,ms5::AnimationCarryUnknown),"known carry");
    reject(ram,state(STOP,static_cast<ms5::AnimationCarryState>(0xffffffffU)),"carry state");
    ms5::AnimationMachineState s=state(0x4a0ca,ms5::AnimationCarrySet);s.a[7]=SP-1;reject(ram,s,"even WORD/LONG");
    s=state(0x49f8c,ms5::AnimationCarrySet);s.a[5]=0x118000;reject(ram,s,"TRAP15");
    put(ram,0x102026,4,0x489c2);reject(ram,state(0x49fc6,ms5::AnimationCarrySet),"missing program bus ROM unit");
    // An invalidating AND/CMP/queue path returns into a real carry consumer.
    put(ram,SP,4,0x1dc8a);put(ram,0x104d74,2,1);s=state(0x3ae6,ms5::AnimationCarrySet);reject(ram,s,"known carry");
}
}
int main(){preserving_blocks();known_writers_and_callers();unknown_and_rollback();std::cout<<"animation_machine_carry_test PASS\n";}
