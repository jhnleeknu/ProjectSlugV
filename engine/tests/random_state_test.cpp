#include "ms5/random_state.h"
#include <cassert>
#include <iostream>
namespace {
void word(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
std::uint16_t word(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return static_cast<std::uint16_t>((ram[at]<<8)|ram[at+1]);
}
void cursor(std::vector<std::uint8_t>& ram,std::uint32_t value) {
    word(ram,0xd722,static_cast<std::uint16_t>(value>>16));word(ram,0xd724,static_cast<std::uint16_t>(value));
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0x5a);std::string error;
    std::uint32_t d0=0x12340000U,d1=0xdeadbeefU;
    word(ram,0xf02c,0xffff);
    assert(ms5::seed_random(ram,d0,d1,error));
    assert(word(ram,0xf02c)==0xffff && word(ram,0xd722)==0x10 && word(ram,0xd724)==0xd720);
    assert(static_cast<std::uint16_t>(d0)==word(ram,0xd720));
    assert(static_cast<std::uint16_t>(d1)==word(ram,0xd71e));
    const std::vector<std::uint8_t> zero_seed=ram;
    const std::uint32_t zero_d0=d0,zero_d1=d1;
    d0=0xffff0001U;d1=0x12345678U;
    assert(ms5::seed_random(ram,d0,d1,error));
    assert(word(ram,0xf02c)==0 && d0==zero_d0 && d1==zero_d1);
    for(std::size_t at=0xd6b4;at<0xd722;++at)assert(ram[at]==zero_seed[at]);
    ram.assign(65536,0);cursor(ram,0x10d720);word(ram,0xd720,0xffff);word(ram,0xd6e2,1);
    d0=0xabcd1234U;
    assert(ms5::next_random(ram,d0,error));
    assert(d0==0xabcdffffU && word(ram,0xd724)==0xd6b4 && word(ram,0xd6e2)==2);
    // Scale returns swapped product halves; low16 is the bounded result.
    for(unsigned int limit_index=0;limit_index<3;++limit_index) {
        const std::uint16_t limit=limit_index==0?0U:(limit_index==1?1U:0xffffU);
        ram.assign(65536,0);cursor(ram,0x10d6b4);word(ram,0xd6b4,0xffff);
        d0=0xabcd0000U|limit;
        assert(ms5::scale_random(ram,d0,error));
        const std::uint32_t expected=limit==0?0U:(limit==1?0xffff0000U:0x0001fffeU);
        assert(d0==expected && word(ram,0xd724)==0xd6b6);
    }
    // Repeated use traverses all55 cursor positions and wraps several times.
    ram.assign(65536,0);d0=0;d1=0;
    assert(ms5::seed_random(ram,d0,d1,error));
    for(unsigned int index=0;index<220;++index) {
        d0=0xabcd0000U;
        assert(ms5::next_random(ram,d0,error));
        assert((d0&0xffff0000U)==0xabcd0000U);
    }
    assert(word(ram,0xd724)==0xd720);
    for(unsigned int index=0;index<4;++index) {
        const std::uint32_t invalid=index==0?0x10d6b3U:(index==1?0x10d6b5U:(index==2?0x10d722U:0xffffffffU));
        cursor(ram,invalid);const std::vector<std::uint8_t> before=ram;
        d0=0x12345678U;
        assert(!ms5::next_random(ram,d0,error));assert(ram==before && d0==0x12345678U);
        assert(!ms5::scale_random(ram,d0,error));assert(ram==before && d0==0x12345678U);
    }
    ram.resize(65535);const std::vector<std::uint8_t> short_before=ram;
    d0=0x12345678U;d1=0xabcdef12U;
    assert(!ms5::seed_random(ram,d0,d1,error));
    assert(ram==short_before && d0==0x12345678U && d1==0xabcdef12U);
    std::cout<<"Random seed, cursor wrap, scaled halves and rollback passed\n";
}
