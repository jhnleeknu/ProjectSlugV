#include "ms5/game_screen_reset.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0xa5);const std::vector<std::uint8_t> before=ram;
    std::uint32_t d0=0xffffffff,d1=0xabcdef12,d3=0x87654321;std::string error;
    std::vector<ms5::VideoPortWrite> ports;
    assert(ms5::reset_game_screen(ram,0xca9e,d0,d1,d3,ports,error));
    assert(ram==before&&d0==0x7580ff02&&d1==0&&d3==0x87654321&&ports.size()==773);
    assert(ports[0].value==0x75000000&&ports[767].value==0x77ff0000&&ports[772].value==0x7580ff02);
    assert(ms5::reset_game_screen(ram,0xcaf0,d0,d1,d3,ports,error));
    assert(d0==0x75807500&&d1==0x7000&&d3==32&&ports.size()==2072&&ram[0x966]==0);
    ram[0x966]=0xa5;assert(ram==before);
    assert(ports[773].size==1&&ports[773].address==0x300001&&ports[773].value==0x21);
    assert(ports[774].value==0x702100ff&&ports[803].value==0x703e00ff&&ports[804].value==0x704100ff);
    assert(ports[2070].size==2&&ports[2070].address==0x3c0004&&ports[2070].value==0);
    assert(ports[2071].value==0x82000000);
    const std::vector<ms5::VideoPortWrite> previous=ports;
    for(unsigned int invalid=0;invalid<2;++invalid) {
        ram.assign(invalid?65535:65536,0xa5);const std::vector<std::uint8_t> saved=ram;
        d0=1;d1=2;d3=3;
        assert(!ms5::reset_game_screen(ram,invalid?0xcaf0:0x35a2,d0,d1,d3,ports,error));
        assert(ram==saved&&d0==1&&d1==2&&d3==3&&ports.size()==previous.size());
        for(std::size_t index=0;index<ports.size();++index)
            assert(ports[index].size==previous[index].size&&ports[index].address==previous[index].address&&ports[index].value==previous[index].value);
    }
    std::cout<<"game screen reset tests passed\n";
}
