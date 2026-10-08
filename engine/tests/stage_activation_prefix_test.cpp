#include "ms5/stage_activation_prefix.h"
#include <cassert>
#include <iostream>
namespace {
ms5::ObjectRestartState initial(std::uint32_t a5=0x108000, std::uint32_t a6=0x100b30) {
    ms5::ObjectRestartState s;
    for (unsigned int i=0;i<8;++i) s.d[i]=0xabcd1234U+i*0x10001U;
    for (unsigned int i=0;i<7;++i) s.a[i]=0x87654320U+i*2;
    s.a[5]=a5; s.a[6]=a6; return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b) {
    for (unsigned int i=0;i<8;++i) if (a.d[i]!=b.d[i]) return false;
    for (unsigned int i=0;i<7;++i) if (a.a[i]!=b.a[i]) return false;
    return true;
}
bool same_ports(const std::vector<ms5::VideoPortWrite>& a,const std::vector<ms5::VideoPortWrite>& b) {
    if (a.size()!=b.size()) return false;
    for (std::size_t i=0;i<a.size();++i)
        if (a[i].size!=b[i].size || a[i].address!=b[i].address || a[i].value!=b[i].value) return false;
    return true;
}
std::vector<ms5::VideoPortWrite> old_ports() {
    std::vector<ms5::VideoPortWrite> p(1); p[0].size=1;p[0].address=0x300001;p[0].value=0x98;return p;
}
std::vector<ms5::FixedDataResource> synthetic() {
    std::vector<ms5::FixedDataResource> windows(1);
    windows[0].source_cpu_address=windows[0].source_rom_offset=0xddfa4;
    const std::uint8_t bytes[]={0,0,0x12,0xf8,2,3,0xff,0xff};
    windows[0].data.assign(bytes,bytes+sizeof(bytes));return windows;
}
void put(std::vector<std::uint8_t>& ram,std::uint32_t base,int disp,std::uint8_t value) {
    const std::int64_t at=static_cast<std::int64_t>(base)+disp-0x100000;
    assert(at>=0 && static_cast<std::uint64_t>(at)<ram.size());
    ram[static_cast<std::size_t>(at)]=value;
}
std::uint8_t get(const std::vector<std::uint8_t>& ram,std::uint32_t base,int disp) {
    const std::int64_t at=static_cast<std::int64_t>(base)+disp-0x100000;
    assert(at>=0 && static_cast<std::uint64_t>(at)<ram.size());
    return ram[static_cast<std::size_t>(at)];
}
void fail(std::vector<std::uint8_t> ram,ms5::ObjectRestartState s,
    const std::vector<ms5::FixedDataResource>& windows) {
    const std::vector<std::uint8_t> before=ram;const ms5::ObjectRestartState saved=s;
    std::vector<ms5::VideoPortWrite> ports=old_ports(), saved_ports=ports;std::string error;
    assert(!ms5::initialize_stage_activation_prefix(ram,windows,s,ports,error));
    assert(!error.empty() && ram==before && same(s,saved) && same_ports(ports,saved_ports));
}
void no_block() {
    const std::uint32_t bases[]={0x108000,0x108002,0x108001};
    for (unsigned int j=0;j<3;++j) {
        std::vector<std::uint8_t> ram(65536,0x53),expected=ram;
        ms5::ObjectRestartState s=initial(bases[j]),want=s;
        put(ram,s.a[5],0x5684,0);put(ram,s.a[5],0x5683,0x81);
        put(ram,s.a[6],0x7c,3);put(ram,s.a[5],-0xcf,0x80);expected=ram;
        expected[0x7def]=0;put(expected,s.a[5],0x5d1f,255);put(expected,s.a[5],0x5d20,0);
        put(expected,s.a[5],-0x75be,0);put(expected,s.a[5],-0x74fa,0);
        put(expected,s.a[5],0x5683,0x95);put(expected,s.a[5],-0x769b,255);
        put(expected,s.a[5],-0x7699,0);put(expected,s.a[5],-0xcf,3);
        put(expected,s.a[6],0x7e,255);put(expected,s.a[6],0x20,0);put(expected,s.a[6],0x21,0xea);
        put(expected,s.a[6],0,0);put(expected,s.a[6],1,4);put(expected,s.a[6],2,0x7c);put(expected,s.a[6],3,0x6c);
        want.d[0]=3;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error="old";
        // Deliberately malformed/unusable resource is skipped on this branch.
        std::vector<ms5::FixedDataResource> bad(1);
        assert(ms5::initialize_stage_activation_prefix(ram,bad,s,ports,error));
        assert(error.empty() && ram==expected && same(s,want) && ports.empty());
    }
}
void block() {
    std::vector<std::uint8_t> ram(65536,0x53);ms5::ObjectRestartState s=initial();
    put(ram,s.a[5],0x5684,5);put(ram,s.a[5],0x5683,0);put(ram,s.a[6],0x7c,8);
    const std::vector<ms5::FixedDataResource> windows=synthetic();
    ms5::ObjectRestartState want=s;want.d[0]=1;std::vector<ms5::VideoPortWrite> expected_ports,ports=old_ports();std::string error;
    assert(ms5::execute_stage_block_draw(ram,0x477a2,windows,want,expected_ports,error));want.d[0]=8;
    assert(ms5::initialize_stage_activation_prefix(ram,windows,s,ports,error));
    assert(same(s,want) && same_ports(ports,expected_ports) && ports.size()==7);
    assert(ram[0x965]==0x53 && ram[0x967]==0 && ram[0xd683]==4 && ram[0x7def]==0x53);
    assert(ram[0xb30]==0 && ram[0xb31]==4 && ram[0xb32]==0x7c && ram[0xb33]==0x6c);
}
void signed_compare() {
    const std::uint8_t currents[]={0,2,3,5,0x7f,0x80,0xff};
    for (unsigned int i=0;i<sizeof(currents);++i) {
        std::vector<std::uint8_t> ram(65536,0);ms5::ObjectRestartState s=initial();
        put(ram,s.a[5],0x5684,4);put(ram,s.a[6],0x7c,3);put(ram,s.a[5],-0xcf,currents[i]);
        std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::initialize_stage_activation_prefix(ram,std::vector<ms5::FixedDataResource>(),s,ports,error));
        const std::uint8_t want=(currents[i]<3 || currents[i]>=128)?3:currents[i];
        assert(get(ram,s.a[5],-0xcf)==want && s.d[0]==3);
    }
}
void alias() {
    std::vector<std::uint8_t> ram(65536,0x53);ms5::ObjectRestartState s=initial(0x108000,0x1009c6);
    put(ram,s.a[5],0x5684,0);put(ram,s.a[6],0x7c,5);put(ram,s.a[5],-0xcf,0x80);
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::initialize_stage_activation_prefix(ram,std::vector<ms5::FixedDataResource>(),s,ports,error));
    // 4e254 clears A5-75be == A6+7c before the parent BYTE is read.
    assert(s.d[0]==0 && ram[0xa42]==0 && ram[0x7f31]==0);
    // Parent overlaps flag: final callback LONG writes the flag only after all live tests.
    ram.assign(65536,0);s=initial(0x108000,0x10d682);ram[0xd684]=4;ram[0xd6fe]=6;
    assert(ms5::initialize_stage_activation_prefix(ram,std::vector<ms5::FixedDataResource>(),s,ports,error));
    assert(s.d[0]==6 && ram[0xd684]==0x7c && ram[0xd683]==4);
}
void errors() {
    std::vector<std::uint8_t> ram(65536,0);ms5::ObjectRestartState s=initial();
    ram[0xd684]=1;fail(ram,s,std::vector<ms5::FixedDataResource>());
    // Block output already generated before actual parent WORD alignment error.
    s.a[6]=0x100b31;fail(ram,s,synthetic());
    // Every earlier parent access fits, but the final LONG begins below RAM.
    s=initial(0x108000,0xffffe);ram[0xd684]=0;fail(ram,s,synthetic());
    // Prefix branch writes cannot be published after a later parent read error.
    s=initial(0x108000,0x10fff0);fail(ram,s,synthetic());
    s=initial(0xffffffff,0x100b30);fail(ram,s,synthetic());
    s=initial(0,0x100b30);fail(ram,s,synthetic());
    s=initial(0x10a600,0x100b30);put(ram,s.a[5],0x5684,0);fail(ram,s,synthetic());
    ram.resize(65535);fail(ram,initial(),synthetic());
}
}
int main() {
    no_block();block();signed_compare();alias();errors();
    std::cout<<"stage_activation_prefix_test: passed\n";return 0;
}
