#include "ms5/game_screen_reset_execution.h"
#include "ms5/game_screen_reset.h"
#include <cassert>
#include <iostream>
namespace {
ms5::ObjectRestartState initial(unsigned int profile) {
    ms5::ObjectRestartState s;
    for(unsigned int i=0;i<8;++i) s.d[i]=profile==0?0U:profile==1?0xffffffffU:0x81231234U+i*0x01010101U;
    for(unsigned int i=0;i<7;++i) s.a[i]=profile==0?0U:profile==1?0xffffffffU:0xabcdef01U+i*0x01010101U;
    return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b) {
    for(unsigned int i=0;i<8;++i) if(a.d[i]!=b.d[i]) return false;
    for(unsigned int i=0;i<7;++i) if(a.a[i]!=b.a[i]) return false;
    return true;
}
bool same_ports(const std::vector<ms5::VideoPortWrite>& a,const std::vector<ms5::VideoPortWrite>& b) {
    if(a.size()!=b.size()) return false;
    for(std::size_t i=0;i<a.size();++i) if(a[i].size!=b[i].size||a[i].address!=b[i].address||a[i].value!=b[i].value) return false;
    return true;
}
ms5::ObjectRestartState expected(const ms5::ObjectRestartState& before,std::uint32_t entry) {
    ms5::ObjectRestartState s=before;s.a[4]=0x3c0000;
    s.d[0]=entry==0xca9e?0x7580ff02U:0x75807500U;s.d[1]=entry==0xca9e?0:0x7000;
    if(entry==0xca9e) s.d[7]=(before.d[7]&0xffff0000U)|0xffff;
    else {s.d[2]=0;s.d[3]=32;s.d[6]=before.d[6]&0xffff0000U;s.d[7]=0x75007000;}
    return s;
}
void failure(std::vector<std::uint8_t>& ram,std::uint32_t entry,ms5::ObjectRestartState& state) {
    const std::vector<std::uint8_t> before=ram;const ms5::ObjectRestartState old=state;
    std::vector<ms5::VideoPortWrite> ports(1);ports[0].size=1;ports[0].address=7;ports[0].value=9;
    const std::vector<ms5::VideoPortWrite> saved=ports;std::string error;
    assert(!ms5::reset_game_screen_full(ram,entry,state,ports,error));
    assert(ram==before&&same(state,old)&&same_ports(ports,saved)&&!error.empty());
}
}
int main() {
    std::vector<std::uint8_t> ram;std::vector<ms5::VideoPortWrite> ports,legacy_ports;std::string error;
    const std::uint32_t entries[]={0xca9e,0xcaf0};
    for(unsigned int profile=0;profile<3;++profile) for(unsigned int e=0;e<2;++e) {
        const std::uint32_t entry=entries[e];ms5::ObjectRestartState s=initial(profile);s.a[5]=0x108000;
        const ms5::ObjectRestartState before=s;ram.assign(65536,0xa5);ram[0x966]=255;
        std::vector<std::uint8_t> legacy=ram;std::uint32_t d0=s.d[0],d1=s.d[1],d3=s.d[3];
        assert(ms5::reset_game_screen(legacy,entry,d0,d1,d3,legacy_ports,error));
        ports.resize(1);error="old";
        assert(ms5::reset_game_screen_full(ram,entry,s,ports,error));
        assert(ram==legacy&&same_ports(ports,legacy_ports)&&s.d[0]==d0&&s.d[1]==d1&&s.d[3]==d3&&error.empty());
        assert(same(s,expected(before,entry))&&ports.size()==(e==0?773U:2072U));
        // The unchanged ca9e prefix and first/last rectangle endpoints protect
        // the shared builder against truncation and column/row reversal.
        assert(ports[0].size==4&&ports[0].address==0x3c0000&&ports[0].value==0x75000000);
        assert(ports[767].value==0x77ff0000&&ports[772].value==0x7580ff02);
        if(entry==0xcaf0) {
            assert(ports[773].size==1&&ports[773].address==0x300001&&ports[773].value==0x21);
            assert(ports[774].value==0x702100ff&&ports[803].value==0x703e00ff&&ports[804].value==0x704100ff);
            assert(ports.back().value==0x82000000&&ram[0x966]==0);
        }
    }
    // caf0 supports the true BYTE destination at both RAM edges and odd
    // addresses, preserving A5 and every byte other than the selected byte.
    const std::uint32_t valid_a5[]={0x10769a,0x117699,0x108001,0x108000};
    for(unsigned int profile=0;profile<3;++profile) for(unsigned int index=0;index<4;++index) {
        ms5::ObjectRestartState s=initial(profile);s.a[5]=valid_a5[index];const ms5::ObjectRestartState before=s;
        ram.assign(65536,0xff);std::vector<std::uint8_t> changed=ram;changed[s.a[5]-0x10769a]=0;
        assert(ms5::reset_game_screen_full(ram,0xcaf0,s,ports,error));
        assert(ram==changed&&same(s,expected(before,0xcaf0))&&ports.size()==2072);
    }
    // ca9e never dereferences A5 and must accept even addresses which would
    // wrap or leave RAM in caf0's signed-displacement write.
    const std::uint32_t arbitrary_a5[]={0,1,0x7699,0x107699,0x11769a,0xffffffff};
    for(unsigned int index=0;index<6;++index) {
        ms5::ObjectRestartState s=initial(2);s.a[5]=arbitrary_a5[index];const ms5::ObjectRestartState before=s;
        ram.assign(65536,0x77);const std::vector<std::uint8_t> unchanged=ram;
        assert(ms5::reset_game_screen_full(ram,0xca9e,s,ports,error));
        assert(ram==unchanged&&same(s,expected(before,0xca9e))&&ports.size()==773);
        s=before;failure(ram,0xcaf0,s);
    }
    ms5::ObjectRestartState s=initial(2);s.a[5]=0x108000;
    for(unsigned int size=65535;size<=65537;size+=2) {ram.assign(size,0xff);failure(ram,0xcaf0,s);failure(ram,0xca9e,s);}
    ram.clear();failure(ram,0xcaf0,s);
    ram.assign(65536,0xff);failure(ram,0,s);failure(ram,0x35a2,s);failure(ram,0xffffffff,s);
    std::cout<<"game_screen_reset_execution_test passed\n";
}
