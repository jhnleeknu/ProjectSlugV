#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
const std::uint32_t SP=0x1feffc,STOP=0xff000;
void put(Bytes& ram,std::uint32_t address,unsigned int size,std::uint32_t value) {
    for(unsigned int i=0;i<size;++i)ram[(address+i)&65535U]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
std::uint32_t get(const Bytes& ram,std::uint32_t address,unsigned int size) {
    std::uint32_t value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[(address+i)&65535U];return value;
}
ms5::AnimationMachineState initial(std::uint32_t pc) {
    ms5::AnimationMachineState s;s.pc=pc;s.carry=ms5::AnimationCarrySet;
    for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654321U+i*2;}
    s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=SP;return s;
}
bool same(const ms5::AnimationMachineState& a,const ms5::AnimationMachineState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;
    return a.pc==b.pc&&a.carry==b.carry;
}
struct Outputs {
    ms5::AnimationMachineDevice device;
    std::vector<ms5::VideoPortWrite> ports;
    std::vector<ms5::PhysicalRomResource> physical;
    std::uint32_t reads;
    ms5::AnimationMachineStatus status;
    std::string error;
    Outputs():reads(99),status(ms5::AnimationMachineWaiting) {
        device.bank_base=0x345678;device.pvc.assign(8192,0x79);
        ms5::VideoPortWrite p;p.size=1;p.address=0xdeadbeef;p.value=0x87;ports.push_back(p);
    }
};
bool run(Bytes& ram,ms5::AnimationMachineState& s,std::uint32_t stop,Outputs& out) {
    ms5::ProgramBusState bus;bus.physical_rom=&out.physical;std::vector<ms5::FixedDataResource> windows;
    return ms5::run_animation_machine(ram,windows,bus,s,out.device,stop,255,out.reads,out.status,out.ports,out.error);
}
void reject(Bytes ram,ms5::AnimationMachineState s,const char* message,Outputs out=Outputs()) {
    const Bytes before=ram;const ms5::AnimationMachineState old=s;const ms5::AnimationMachineDevice device=out.device;
    assert(!run(ram,s,STOP,out));
    if(out.error.find(message)==std::string::npos)std::cerr<<out.error<<" expected "<<message<<"\n";
    assert(out.error.find(message)!=std::string::npos&&ram==before&&same(s,old));
    assert(out.device.pvc==device.pvc&&out.device.bank_base==device.bank_base);
    assert(out.reads==99&&out.status==ms5::AnimationMachineWaiting&&out.ports.size()==1);
    assert(out.ports[0].address==0xdeadbeef&&out.ports[0].size==1&&out.ports[0].value==0x87);
}
void physical(Outputs& out,std::uint32_t address,const Bytes& data) {
    ms5::PhysicalRomResource r;r.source_rom_offset=address;r.data=data;out.physical.push_back(r);
}
void draw_seed(Bytes& ram) {
    put(ram,0x109152,4,0xcd50);put(ram,0x102042,2,0xa0);put(ram,0x102046,2,0x170);
    put(ram,SP,4,STOP);
}
void sprite_prefix() {
    const std::uint32_t bases[]={0x102000,0x1f2000,0x01102000};
    const std::uint32_t words[]={0,0x8000,0xffff};
    for(unsigned int b=0;b<3;++b)for(unsigned int j=0;j<3;++j)for(unsigned int flags=0;flags<256;++flags) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=initial(0x16ea4),want=s;
        s.a[6]=want.a[6]=bases[b];s.a[5]=0xffffffff;want.a[5]=0x108000;
        s.d[0]=0xffff8001;want.d[0]=((0xffffU+words[j]-(flags&1U))&65535U)<<16;
        want.d[0]|=(0x8001U+words[2-j]-((flags>>1)&1U))&65535U;
        put(ram,s.a[6]+0x53,1,flags);put(ram,s.a[6]+0x42,2,words[j]);put(ram,s.a[6]+0x46,2,words[2-j]);
        put(ram,s.a[6]+0x12,4,0x89abcdef);put(ram,s.a[6]+0x1e,2,0x8001);
        want.d[1]=0x89abcdef;want.d[2]=(s.d[2]&0xffffff00U)|(flags>>2);want.d[3]=0;
        want.d[5]=(s.d[5]&0xffff0000U)|0x8001;want.pc=0xcd58;want.carry=ms5::AnimationCarryUnknown;
        const Bytes before=ram;Outputs out;assert(run(ram,s,0xcd58,out)&&same(s,want)&&ram==before);
        assert(out.ports.empty()&&out.reads==0&&out.status==ms5::AnimationMachineReturned);
    }
}
void signed_gate() {
    const std::uint32_t words[]={0,0x7fff,0x8000,0xffff};
    for(unsigned int i=0;i<4;++i)for(unsigned int j=0;j<4;++j)for(unsigned int flags=0;flags<256;++flags) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=initial(0x16ed2),want=s;
        s.a[5]=want.a[5]=flags&1U?0x108002:0x108000;
        put(ram,s.a[5]+0xd3e,2,words[i]);put(ram,s.a[5]+0xd46,2,words[j]);put(ram,s.a[6]+0x15,1,flags);put(ram,SP,4,STOP);
        const bool less=(words[i]^0x8000U)<(words[j]^0x8000U);
        Bytes expected=ram;put(expected,s.a[6]+0x15,1,less?(flags|4U):(flags&~4U));
        want.d[0]=(s.d[0]&0xffff0000U)|words[i];want.pc=STOP;want.a[7]+=4;want.carry=ms5::AnimationCarryUnknown;
        Outputs out;assert(run(ram,s,STOP,out)&&same(s,want)&&ram==expected&&out.ports.empty());
    }
}
void actual_stage() {
    // All BYTE selectors select the full raw LONG table, without changing its format.
    for(unsigned int selector=0;selector<256;++selector) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=initial(0x47cca);Outputs out;Bytes table(1024,0);
        put(table,selector*4,4,0x89abcdefU^selector);physical(out,0x48a12,table);put(ram,s.a[6]+0x7e,1,selector);
        assert(run(ram,s,0x47ce6,out)&&s.d[0]==0&&s.d[7]==(0x89abcdefU^selector));
        assert(s.a[0]==0x48a12&&s.a[7]==SP&&get(ram,s.a[6]+0x14,1)==0xb&&s.carry==ms5::AnimationCarryUnknown);
    }
    const std::uint32_t calls[][3]={{0x47cc0,0x16ed2,0x47cc6},{0x47cc6,0x47672,0x47cca},{0x47ce6,0x16ea4,0x47cec}};
    for(unsigned int i=0;i<3;++i) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=initial(calls[i][0]);Outputs out;
        assert(run(ram,s,calls[i][1],out)&&s.a[7]==SP-4&&get(ram,SP-4,4)==calls[i][2]&&s.carry==ms5::AnimationCarrySet);
    }
    Bytes ram(65536,0);draw_seed(ram);ms5::AnimationMachineState s=initial(0x47cae);Outputs out;
    s.d[0]=0xffffffff;physical(out,0x4411e,Bytes(2,0));physical(out,0x48a12,Bytes(4,0));physical(out,0x489c2,Bytes(1,0x28));
    assert(run(ram,s,0x47d20,out)&&s.a[7]==SP&&s.carry==ms5::AnimationCarrySet);
    assert(get(ram,0x102042,2)==0xa0&&get(ram,0x102046,2)==0x170&&get(ram,0x10201e,2)==0xffff);
    assert(get(ram,0x102014,1)==4&&get(ram,0x102026,4)==0x489c2&&out.ports.size()==6);
}
void waits_and_failures() {
    // Direct helper tail-JMP preserves the caller return frame while cd58's callback returns.
    Bytes ram(65536,0);draw_seed(ram);put(ram,0x108d34,2,2);put(ram,0x108d36,2,4);
    ms5::AnimationMachineState s=initial(0x16ea4);s.d[0]=0;Outputs out;
    assert(run(ram,s,STOP,out)&&s.pc==0xcda4&&s.a[7]==SP&&out.status==ms5::AnimationMachineWaiting);
    const ms5::AnimationMachineState waiting=s;put(ram,0x102042,2,0xffff);put(ram,0x102046,2,0xffff);
    const Bytes poisoned=ram;assert(run(ram,s,STOP,out)&&same(s,waiting)&&ram==poisoned);
    put(ram,0x108d34,2,s.d[4]);assert(run(ram,s,STOP,out)&&s.a[7]==SP+4&&s.pc==STOP);
    // Actual stage call adds exactly its original JSR return slot, including through wait/resume.
    ram.assign(65536,0);draw_seed(ram);put(ram,0x108d34,2,2);put(ram,0x108d36,2,4);
    s=initial(0x47ce6);s.d[0]=0;assert(run(ram,s,0x47cec,out)&&s.pc==0xcda4&&s.a[7]==SP-4&&get(ram,SP-4,4)==0x47cec);
    put(ram,0x108d34,2,s.d[4]);assert(run(ram,s,0x47cec,out)&&s.a[7]==SP);
    ram.assign(65536,0);draw_seed(ram);s=initial(0x16ea4);s.a[6]=0x102001;reject(ram,s,"even WORD/LONG");
    s=initial(0x16ed2);s.a[5]=0x1ff2ba;reject(ram,s,"program bus ROM"); // FirstWORD RAM, secondWORD bank.
    s=initial(0x16ed2);s.a[6]=0x1ffff0;Outputs late_write;
    physical(late_write,0x34567d,Bytes(1,0x89));reject(ram,s,"unsupported animation machine write device",late_write);
    s=initial(0x16ed2);put(ram,SP,4,0xdeac);reject(ram,s,"unsupported animation machine PC");
    ram.assign(65536,0);draw_seed(ram);put(ram,0x109152,4,0xdeac);s=initial(0x16ea4);reject(ram,s,"unsupported sprite callback target");
    s=initial(0x47cca);reject(ram,s,"program bus ROM"); // Earlier objectBYTE mutation rolls back.
    s=initial(0x47cae);reject(ram,s,"program bus ROM"); // Earlier coordinate writes and sound stack roll back.
}
}
int main(){sprite_prefix();signed_gate();actual_stage();waits_and_failures();std::cout<<"animation_machine_activation_test PASS\n";}
