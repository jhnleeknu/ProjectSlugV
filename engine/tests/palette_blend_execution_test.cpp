#include "ms5/palette_blend_execution.h"
#include "ms5/palette_control.h"
#include <cassert>
#include <iostream>
namespace {
ms5::ObjectRestartState initial() {
    ms5::ObjectRestartState s;
    for (unsigned int i=0;i<8;++i) s.d[i]=0xabcd1234U+i*0x10001U;
    for (unsigned int i=0;i<7;++i) s.a[i]=0xfedc9876U+i*2;
    return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b) {
    for (unsigned int i=0;i<8;++i) if (a.d[i]!=b.d[i]) return false;
    for (unsigned int i=0;i<7;++i) if (a.a[i]!=b.a[i]) return false;
    return true;
}
void word(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t value) {
    assert(at+1<ram.size());ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
void reference_widths() {
    const unsigned int slots[]={0,1,127,255},weights[]={0,31,32,33,255};
    for (unsigned int i=0;i<4;++i) for (unsigned int j=0;j<5;++j) for (unsigned int ref=0;ref<2;++ref) {
        std::vector<std::uint8_t> ram(65536,0x53),legacy=ram;
        ms5::ObjectRestartState s=initial();
        s.d[0]=0x8765ab00U|slots[i];s.d[1]=0xaabb2468;s.d[2]=0xcdefab00U|weights[j];
        const std::size_t node=0x4d92+slots[i]*16;
        // Low reference byte only: a nonzero WORD does not require bit8.
        word(ram,node+8,static_cast<std::uint16_t>(ref));legacy=ram;
        const std::vector<std::uint8_t> before=ram;
        ms5::ObjectRestartState want=s;want.d[0]=0x87650000U|slots[i]*16;
        want.a[1]=0x104d92;want.a[2]=want.a[1]+slots[i]*16;
        if (ref && weights[j]>=32) want.d[2]=32;
        std::string error="old";
        assert(ms5::set_palette_blend(legacy,static_cast<std::uint8_t>(slots[i]),0x2468,
            static_cast<std::uint8_t>(weights[j]),error));
        assert(ms5::execute_palette_blend(ram,s,error));
        assert(error.empty() && same(s,want) && ram==legacy);
        if (!ref) assert(ram==before);
        else {
            assert(ram[node+0xc]==0x24 && ram[node+0xd]==0x68);
            assert(ram[node+0xe]==(weights[j]>=32?32:weights[j]));
            assert(ram[node+0xf]==0xd3);
        }
    }
}
void dirty_paths() {
    // Distinct target, changed weight with matching current, changed weight
    // with differing current, and unchanged weight all retain unrelated bits.
    for (unsigned int path=0;path<4;++path) for (unsigned int dirty=0;dirty<2;++dirty) {
        std::vector<std::uint8_t> ram(65536,0x36);const std::size_t node=0x4d92+18*16;
        ms5::ObjectRestartState s=initial();s.d[0]=0xfacefe12;s.d[1]=0xaaaa1234;s.d[2]=0xbbbbbb1f;
        word(ram,node+8,0x8000);word(ram,node+0xa,path==1?0x1234:0x4321);
        word(ram,node+0xc,path==0?0x5678:0x1234);ram[node+0xe]=path==3?31:2;
        ram[node+0xf]=static_cast<std::uint8_t>(0x25|(dirty?0x80:0));
        std::vector<std::uint8_t> expected=ram;
        if (path==0) {word(expected,node+0xc,0x1234);expected[node+0xe]=31;expected[node+0xf]|=0x80;}
        else if (path!=3) {expected[node+0xe]=31;if(path==2)expected[node+0xf]|=0x80;}
        ms5::ObjectRestartState want=s;want.d[0]=0xface0120;want.a[1]=0x104d92;want.a[2]=0x104eb2;
        std::string error;assert(ms5::execute_palette_blend(ram,s,error));
        assert(ram==expected && same(s,want));
    }
}
void invalid_ram() {
    const unsigned int sizes[]={0,65535,65537};
    for (unsigned int i=0;i<3;++i) {
        std::vector<std::uint8_t> ram(sizes[i],0x73),before=ram;
        ms5::ObjectRestartState s=initial(),before_state=s;std::string error;
        assert(!ms5::execute_palette_blend(ram,s,error));
        assert(!error.empty() && ram==before && same(s,before_state));
    }
}
}
int main() {reference_widths();dirty_paths();invalid_ram();std::cout<<"palette_blend_execution_test: passed\n";return 0;}
