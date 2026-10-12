#include "ms5/animation_machine.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
void put(Bytes& bytes,unsigned int at,unsigned int size,std::uint32_t value) {
    assert(at<=bytes.size()&&size<=bytes.size()-at);
    for(unsigned int i=0;i<size;++i)bytes[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
ms5::AnimationMachineState state(std::uint32_t pc) {
    ms5::AnimationMachineState s;
    for(unsigned int i=0;i<8;++i){s.d[i]=0x89abcdefU+i;s.a[i]=0x12340000U+i;}
    s.a[5]=0x108000;s.a[6]=0x102000;s.a[7]=0x1feffc;s.pc=pc;return s;
}
bool equal(const ms5::AnimationMachineState& a,const ms5::AnimationMachineState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;
    return a.pc==b.pc&&a.carry==b.carry;
}
bool equal(const std::vector<ms5::VideoPortWrite>& a,const std::vector<ms5::VideoPortWrite>& b) {
    if(a.size()!=b.size())return false;
    for(std::size_t i=0;i<a.size();++i)if(a[i].size!=b[i].size||a[i].address!=b[i].address||a[i].value!=b[i].value)return false;
    return true;
}
void rejection(Bytes ram,ms5::AnimationMachineState s,ms5::AnimationMachineDevice device,
    const std::vector<ms5::PhysicalRomResource>& physical,std::uint32_t stop=0xff000) {
    const Bytes before=ram;const ms5::AnimationMachineState before_s=s;
    const ms5::AnimationMachineDevice before_device=device;
    ms5::ProgramBusState bus;bus.physical_rom=&physical;
    std::vector<ms5::FixedDataResource> windows;
    ms5::VideoPortWrite sentinel;sentinel.size=1;sentinel.address=0xdeadbeef;sentinel.value=0x87;
    std::vector<ms5::VideoPortWrite> ports(1,sentinel),before_ports=ports;
    std::uint32_t reads=0x12345678;ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;
    std::string error="dirty";
    assert(!ms5::run_animation_machine(ram,windows,bus,s,device,stop,255,reads,status,ports,error));
    assert(!error.empty()&&ram==before&&equal(s,before_s));
    assert(device.pvc==before_device.pvc&&device.bank_base==before_device.bank_base);
    assert(reads==0x12345678&&status==ms5::AnimationMachineWaiting&&equal(ports,before_ports));
}
void boundaries_and_rollback() {
    Bytes ram(65536,0x5a);std::vector<ms5::PhysicalRomResource> physical;
    ms5::AnimationMachineDevice device;device.bank_base=0xffffffff;
    ms5::AnimationMachineState s=state(0xff000),before_s=s;
    ms5::ProgramBusState bus;bus.physical_rom=&physical;
    std::vector<ms5::FixedDataResource> windows;std::vector<ms5::VideoPortWrite> ports;
    std::uint32_t reads=99;ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;std::string error="dirty";
    const Bytes before=ram,before_pvc=device.pvc;
    assert(ms5::run_animation_machine(ram,windows,bus,s,device,0xff000,255,reads,status,ports,error));
    assert(equal(s,before_s)&&ram==before&&device.pvc==before_pvc&&device.bank_base==0xffffffff);
    assert(status==ms5::AnimationMachineReturned&&reads==0&&ports.empty()&&error.empty());
    // Actual RTS reads current shared RAM, with raw mirror A7 retained.
    s=state(0x4a0e2);put(ram,0xeffc,4,0xff000);before_s=s;
    assert(ms5::run_animation_machine(ram,windows,bus,s,device,0xff000,0,reads,status,ports,error));
    before_s.a[7]+=4;before_s.pc=0xff000;assert(equal(s,before_s)&&status==ms5::AnimationMachineReturned);
    // Unknown return target must roll back the preceding successful stack pop.
    s=state(0x4a0e2);put(ram,0xeffc,4,0xdeac);rejection(ram,s,device,physical);
    rejection(ram,state(0xdeac),device,physical);
    rejection(ram,state(0x49fc6),device,physical,0xff001);
    rejection(Bytes(65535),state(0xff000),device,physical);
    ms5::AnimationMachineDevice short_device=device;short_device.pvc.resize(8191);
    rejection(ram,state(0xff000),short_device,physical);
    // Final publication LONG has a valid RAM first WORD and bank second WORD.
    s=state(0x4a276);s.a[0]=0x1ffffe;rejection(ram,s,device,physical);
}
void late_source_and_write() {
    Bytes ram(65536,0);ms5::AnimationMachineDevice device;
    std::vector<ms5::PhysicalRomResource> physical;
    ms5::AnimationMachineState s=state(0x49fc6);
    put(ram,0x2026,4,0x106000);put(ram,0xeffc,4,0xff000);
    // 40 selector0 -> signed field56; first pointer viaRAMmirror1f8004.
    const unsigned char script[]={0x40,0,0x80,0,0,0,0x28};
    for(unsigned int i=0;i<sizeof(script);++i)ram[0x6000+i]=script[i];
    put(ram,0x8004,4,0x104000);put(ram,0x4000,4,0x12345678);
    rejection(ram,s,device,physical); // Entry writes shadow/PVC before missing table read.
    ms5::PhysicalRomResource table;table.source_rom_offset=0x4a76c;table.data.push_back(0);table.data.push_back(0x56);physical.push_back(table);
    s.a[6]=0x1fffa8;put(ram,0xffce,4,0x106000); // A6+26 valid; final field LONG crosses bank.
    rejection(ram,s,device,physical);
    // Complete earlier prefix effects must also roll back on a late script fetch.
    s=state(0x49fc6);put(ram,0x2026,4,0x106000);ram[0x6000]=0x08;ram[0x6001]=0;
    put(ram,0x6002,4,0x300000);rejection(ram,s,device,physical);
}
}
// Command callback (4a30c wide, 4a408 narrow): original 4a352/4a43c is a plain JSR (A1);
// the target comes from table 4a500 and routing decides (no interpreter allow list).
std::string callback_run(bool wide,std::uint32_t target,std::uint32_t stop,ms5::AnimationMachineState& out,Bytes& out_ram) {
    Bytes ram(65536,0);std::vector<ms5::PhysicalRomResource> physical;
    ms5::PhysicalRomResource table;table.source_rom_offset=0x4a500;
    table.data.assign(16,0);
    for(unsigned int i=0;i<4;++i)table.data[4+i]=static_cast<std::uint8_t>(target>>(24-8*i));
    physical.push_back(table);
    if(wide){ // WORD: skipped byte, selector WORD, 4a76c selector WORD, LONG A0
        ms5::PhysicalRomResource sel;sel.source_rom_offset=0x4a76c;sel.data.assign(4,0);physical.push_back(sel);
    }
    const unsigned char narrow[]={0,1,0x00,0x12,0x34,0x56};
    const unsigned char widescript[]={0,1,0,0,0x00,0x12,0x34,0x56};
    if(wide)for(unsigned int i=0;i<sizeof(widescript);++i)ram[0x6000+i]=widescript[i];
    else for(unsigned int i=0;i<sizeof(narrow);++i)ram[0x6000+i]=narrow[i];
    ms5::AnimationMachineState s=state(wide?0x4a30c:0x4a408);s.a[1]=wide?0x105fff:0x106001;
    s.a[7]=0x10effc;
    ms5::AnimationMachineDevice device;ms5::ProgramBusState bus;bus.physical_rom=&physical;
    std::vector<ms5::FixedDataResource> windows;std::vector<ms5::VideoPortWrite> ports;
    std::uint32_t reads=0;ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;std::string error;
    const Bytes before=ram;const ms5::AnimationMachineState before_s=s;
    if(ms5::run_animation_machine(ram,windows,bus,s,device,stop,255,reads,status,ports,error)) {
        assert(error.empty()&&status==ms5::AnimationMachineReturned);out=s;out_ram=ram;return "";
    }
    assert(ram==before&&equal(s,before_s)); // checked failure rolls back
    return error;
}
void callback_routing() {
    for(unsigned int w=0;w<2;++w) {
        ms5::AnimationMachineState s;Bytes ram;
        // Formerly allow-listed and any other routed target alike: stop at the target succeeds
        // with the call frame pushed exactly as the original (A0, A1, bank WORD, return PC).
        assert(callback_run(w!=0,0x3679e,0x3679e,s,ram).empty());
        assert(s.pc==0x3679e&&s.a[7]==0x10effcU-14U);
        const unsigned int slot=0xf000U-18U;
        const std::uint32_t ret=(static_cast<std::uint32_t>(ram[slot])<<24)|(static_cast<std::uint32_t>(ram[slot+1U])<<16)|
            (static_cast<std::uint32_t>(ram[slot+2U])<<8)|ram[slot+3U];
        assert(ret==(w?0x4a354U:0x4a43eU));
        // Targets formerly rejected by the allow list now reach routing.
        assert(callback_run(w!=0,0x10fe00,0xff000,s,ram)=="unsupported animation machine PC");
        assert(callback_run(w!=0,0x2b3ea,0xff000,s,ram)=="unsupported animation interpreter PC"); // owning-unit interior
        assert(callback_run(w!=0,0x367a0,0xff000,s,ram)=="unsupported animation machine PC");
        assert(callback_run(w!=0,0x10fe01,0xff000,s,ram)=="unaligned animation machine PC");
    }
}
int main(){boundaries_and_rollback();late_source_and_write();callback_routing();std::cout<<"animation_machine_test PASS\n";}
