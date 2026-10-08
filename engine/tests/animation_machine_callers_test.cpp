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
    ms5::AnimationMachineState s;s.pc=pc;
    for(unsigned int i=0;i<8;++i){s.d[i]=0xabcd1234U+i*0x10001U;s.a[i]=0x87654321U+i*2;}
    s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=SP;return s;
}
bool same(const ms5::AnimationMachineState& a,const ms5::AnimationMachineState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i] || a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;
}
std::vector<ms5::VideoPortWrite> markers() {
    ms5::VideoPortWrite p;p.size=1;p.address=0xdeadbeef;p.value=0x87;return std::vector<ms5::VideoPortWrite>(1,p);
}
void check_ports(const std::vector<ms5::VideoPortWrite>& ports,unsigned int pairs) {
    assert(ports.size()==pairs*2);
    for(unsigned int i=0;i<pairs;++i) {
        assert(ports[2*i].size==2&&ports[2*i].address==0x2ffff2&&ports[2*i].value==0x1000);
        assert(ports[2*i+1].size==2&&ports[2*i+1].address==0x2ffff0&&ports[2*i+1].value==0);
    }
}
bool run(Bytes& ram,ms5::AnimationMachineState& s,ms5::AnimationMachineDevice& device,
    const std::vector<ms5::PhysicalRomResource>& physical,std::uint32_t stop,
    std::uint32_t& reads,ms5::AnimationMachineStatus& status,std::vector<ms5::VideoPortWrite>& ports,std::string& error) {
    ms5::ProgramBusState bus;bus.physical_rom=&physical;std::vector<ms5::FixedDataResource> windows;
    return ms5::run_animation_machine(ram,windows,bus,s,device,stop,255,reads,status,ports,error);
}
void rejected(Bytes ram,ms5::AnimationMachineState s,const char* message) {
    const Bytes before=ram;const ms5::AnimationMachineState saved=s;
    ms5::AnimationMachineDevice device;device.bank_base=0x345678;device.pvc.assign(8192,0x79);
    const ms5::AnimationMachineDevice old=device;std::vector<ms5::PhysicalRomResource> physical;
    std::vector<ms5::VideoPortWrite> ports=markers();std::uint32_t reads=123;
    ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;std::string error;
    assert(!run(ram,s,device,physical,STOP,reads,status,ports,error));
    assert(error.find(message)!=std::string::npos&&ram==before&&same(s,saved));
    assert(device.pvc==old.pvc&&device.bank_base==old.bank_base&&reads==123&&status==ms5::AnimationMachineWaiting);
    assert(ports.size()==1&&ports[0].address==0xdeadbeef&&ports[0].size==1&&ports[0].value==0x87);
}
void initializer() {
    const std::uint32_t bases[]={0x102000,0x1f2000,0xfffea,0xfffe8,0x10ffd4,0x1fffd2};
    const std::uint32_t pointers[]={0,0xffffffff,0x81234567};
    for(unsigned int i=0;i<6;++i)for(unsigned int j=0;j<3;++j) {
        Bytes ram(65536,0x53);put(ram,SP,4,STOP);ms5::AnimationMachineState s=initial(0x49f8c),want=s;
        s.a[6]=want.a[6]=bases[i];s.a[1]=want.a[1]=pointers[j];s.d[0]=want.d[0]=0xabcd8001;
        Bytes expected=ram;want.a[0]=s.a[6]+0x26U;want.a[7]+=4;want.pc=STOP;want.carry=ms5::AnimationCarryClear;
        put(expected,s.a[6]+0x18,1,0);put(expected,0x100010,2,0);put(expected,want.a[0],4,s.a[1]);
        put(expected,want.a[0]+4,2,0);put(expected,want.a[0]+6,2,s.d[0]);
        ms5::AnimationMachineDevice device;device.bank_base=0xffffffff;std::vector<ms5::PhysicalRomResource> physical;
        std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads=99;ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;std::string error;
        assert(run(ram,s,device,physical,STOP,reads,status,ports,error));
        assert(error.empty()&&ram==expected&&same(s,want)&&reads==0&&status==ms5::AnimationMachineReturned);
        assert(device.bank_base==0x200000&&get(device.pvc,0x1ff0,2)==0xa0&&get(device.pvc,0x1ff2,2)==0x1000);check_ports(ports,1);
    }
}
void live_return() {
    for(unsigned int which=0;which<2;++which) {
        Bytes ram(65536,0x53);put(ram,SP,4,0xdeac);ms5::AnimationMachineState s=initial(0x49f8c),want=s;
        s.a[6]=want.a[6]=SP-(which?0x2aU:0x26U);s.a[1]=want.a[1]=STOP;s.d[0]=want.d[0]=0xabcdf000;
        const std::uint32_t target=which?0xf000:STOP;want.a[0]=s.a[6]+0x26;want.a[7]+=4;want.pc=target;want.carry=ms5::AnimationCarryClear;
        ms5::AnimationMachineDevice device;std::vector<ms5::PhysicalRomResource> physical;
        std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads=99;ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;std::string error;
        assert(run(ram,s,device,physical,target,reads,status,ports,error));assert(same(s,want)&&get(ram,SP,4)==target);
        assert(status==ms5::AnimationMachineReturned&&reads==0);check_ports(ports,1);
    }
}
void callers() {
    const std::uint32_t entries[]={0x47cec,0x47d0a,0x47d10,0x47d14,0x47d1a,0x47f04};
    for(unsigned int i=0;i<6;++i) {
        Bytes ram(65536,0);ms5::AnimationMachineState s=initial(entries[i]),want=s;
        s.a[1]=want.a[1]=0x106000;put(ram,0x106000,1,0x28);put(ram,s.a[6]+0x26,4,0x106000);
        const bool init=i<4;const std::uint32_t stop=i==5?0x47f0a:0x47d20;
        if(i<2)want.a[1]=0x489c2;
        if(i<3)want.d[0]=(want.d[0]&0xffff0000U)|0x100;
        const std::uint32_t script=want.a[1];want.a[1]=script+1;want.a[0]=want.a[6]+0x26;want.d[7]=0xffffffff;want.pc=stop;want.carry=ms5::AnimationCarrySet;
        std::vector<ms5::PhysicalRomResource> physical;
        // Synthetic one-command input tests actual fixed-ROM resource consumption.
        ms5::PhysicalRomResource fixed;fixed.source_rom_offset=0x489c2;fixed.data.push_back(0x28);physical.push_back(fixed);
        ms5::AnimationMachineDevice device;std::vector<ms5::VideoPortWrite> ports;
        std::uint32_t reads=99;ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;std::string error;
        assert(run(ram,s,device,physical,stop,reads,status,ports,error));assert(same(s,want));
        assert(status==ms5::AnimationMachineReturned&&reads==0&&error.empty()&&get(ram,SP-4,4)==stop);
        assert(get(ram,s.a[6]+0x26,4)==script);if(init)assert(get(ram,s.a[6]+0x2c,2)==(want.d[0]&65535));
        if(i==0)assert(get(ram,s.a[6]+0x42,2)==0xa0&&get(ram,s.a[6]+0x46,2)==0x170&&get(ram,s.a[6]+0x12,3)==0xffff04);
        check_ports(ports,init?3:2);
    }
}
void failures() {
    Bytes ram(65536,0x53);put(ram,SP,4,STOP);ms5::AnimationMachineState s=initial(0x49f8c);
    s.a[5]=0x118000;rejected(ram,s,"TRAP15");s=initial(0x49f8c);
    s.a[6]=0x1fffd4;rejected(ram,s,"write device");s=initial(0x49f8c);
    s.a[6]=0x102001;rejected(ram,s,"alignment");s=initial(0x49f8c);
    s.a[7]=SP-1;rejected(ram,s,"even WORD/LONG");s=initial(0x49f8c);
    put(ram,SP,4,0xdeac);rejected(ram,s,"unsupported animation machine PC");
    // Both callerJSRs and initializer effects precede a genuine missing-script read.
    s=initial(0x47d0a);rejected(ram,s,"missing or ambiguous physical program bus ROM byte");
}
}
int main(){initializer();live_return();callers();failures();std::cout<<"animation_machine_callers_test PASS\n";}
