#include "ms5/game_reset.h"
#include <cassert>
#include <iostream>
namespace {
void run(std::vector<std::uint8_t>& ram,std::uint32_t entry,std::uint32_t expected0,
         std::uint32_t expected1=0x87654321U,std::uint32_t expected3=0xfedcba98U) {
    std::uint32_t d0=0x12345678U,d1=0x87654321U,d3=0xfedcba98U;std::string error;
    assert(ms5::reset_game_subsystem(ram,entry,d0,d1,d3,error));
    assert(error.empty()&&d0==expected0&&d1==expected1&&d3==expected3);
}
}
int main() {
    std::vector<std::uint8_t> ram(65536U,0xa5U);
    run(ram,0xb7a20U,0x12345678U);
    assert(ram[0xdddb]==0xa5&&ram[0xdde3]==0xa5&&ram[0xddeb]==0xa5);
    assert(ram[0xdddc]==0&&ram[0xdde2]==0&&ram[0xdde4]==0&&ram[0xddea]==0);
    ram.assign(65536U,0xa5U);run(ram,0x49a8eU,0x12345678U);
    assert(ram[0xd725]==0xa5&&ram[0xd732]==0xa5&&ram[0xd733]==0xa5&&ram[0xd73c]==0xa5);
    assert(ram[0xd726]==0&&ram[0xd731]==0&&ram[0xd734]==0&&ram[0xd73b]==0);
    ram.assign(65536U,0xa5U);run(ram,0x4d13cU,0x12345678U);
    for(unsigned int i=0;i<2;++i) {
        const std::size_t base=0xdcbaU+i*0x2cU;
        assert(ram[base]==0&&ram[base+1]==0&&ram[base+6]==0&&ram[base+11]==0&&ram[base+0x22]==0);
        assert(ram[base+2]==0xa5&&ram[base+0x1a]==0xa5&&ram[base+0x20]==0xa5&&ram[base+0x25]==0xa5);
    }
    ram.assign(65536U,0xa5U);run(ram,0x4d126U,0x12345678U);
    assert(ram[0xdcba+0x26]==4&&ram[0xdce6+0x26]==4&&ram[0xdcba+0x20]==255&&ram[0xdcba+0x21]==255);
    ram.assign(65536U,0xa5U);run(ram,0x4aa30U,0,0,0);
    for(unsigned int i=0;i<2;++i) {
        const std::size_t base=0xd746U+i*0x1d2U;
        assert(ram[base]==0&&ram[base+0xcf]==0&&ram[base+0xd0]==0xa5&&ram[base+0x1cf]==0xa5);
        assert(ram[base+0x1d0]==0&&ram[base+0x1d1]==0);
    }
    assert(ram[0xdaf7]==0xa5&&ram[0xdb78]==0xa5&&ram[0xdb83]==0xa5&&ram[0xdc8c]==0xa5);
    assert(ram[0xdc88]==0&&ram[0xdc89]==0x10&&ram[0xdc8a]==0xdb&&ram[0xdc8b]==0x88);
    ram.assign(65536U,0xa5U);run(ram,0x46f2eU,0);
    for(unsigned int i=0;i<8;++i) {
        const std::size_t base=0xd4e6U+i*0x2cU;
        assert(ram[base]==0&&ram[base+0x25]==0&&ram[base+0x26]==255&&ram[base+0x27]==255);
        assert(ram[base+0x28]==0xa5&&ram[base+0x29]==0xa5&&ram[base+0x2a]==0&&ram[base+0x2b]==0);
    }
    assert(ram[0xd4e5]==0xa5&&ram[0xd646]==0xa5);
    ram.assign(65536U,0xa5U);run(ram,0xb4a24U,0);
    for(unsigned int i=0;i<12;++i)assert(ram[0xdd5c+i*10]==0&&ram[0xdd5d+i*10]==0&&ram[0xdd5eU+i*10]==0xa5);
    ram.assign(65536U,0xa5U);run(ram,0x2ef90U,1);
    assert(ram[0xd486]==0xa5&&ram[0xd487]==0&&ram[0xd48e]==0xa5&&ram[0xd48f]==0&&ram[0xd492]==0xa5);
    ram.assign(65536U,0xa5U);run(ram,0x4ddb6U,0x12345678U);
    assert(ram[0xdd11]==0xa5&&ram[0xdd12]==1&&ram[0xdd17]==255&&ram[0xdd18]==1&&ram[0xdd1e]==0xa5);
    for(unsigned int invalid=0;invalid<2;++invalid) {
        ram.assign(invalid?65535U:65536U,0xa5U);const std::vector<std::uint8_t> before=ram;
        std::uint32_t d0=1,d1=2,d3=3;std::string error;
        assert(!ms5::reset_game_subsystem(ram,invalid?0x4aa30U:0x47570U,d0,d1,d3,error));
        assert(ram==before&&d0==1&&d1==2&&d3==3&&!error.empty());
    }
    std::cout<<"game reset tests passed\n";
}
