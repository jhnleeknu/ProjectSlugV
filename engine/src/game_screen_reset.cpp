#include "ms5/game_screen_reset.h"
#include <new>
namespace ms5 {
namespace {
void emit(std::vector<VideoPortWrite>& ports,std::uint8_t size,std::uint32_t address,std::uint32_t value) {
    VideoPortWrite write;write.size=size;write.address=address;write.value=value;ports.push_back(write);
}
void rectangle(std::vector<VideoPortWrite>& ports,std::uint16_t start,std::uint16_t tile,
               unsigned int width,unsigned int height) {
    emit(ports,1,0x300001,start&255U);
    for(unsigned int column=0;column<width;++column) {
        const std::uint16_t base=static_cast<std::uint16_t>(start+column*32U);
        for(unsigned int row=0;row<height;++row)
            emit(ports,4,0x3c0000,(static_cast<std::uint32_t>(static_cast<std::uint16_t>(base+row))<<16)|tile);
    }
    emit(ports,2,0x3c0004,0);emit(ports,4,0x3c0000,0x82000000);
}
}
bool reset_game_screen(std::vector<std::uint8_t>& ram,std::uint32_t entry,
    std::uint32_t& d0,std::uint32_t& d1,std::uint32_t& d3,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536U||(entry!=0xca9eU&&entry!=0xcaf0U)) {
        error="screen reset requires64KiB RAM and ca9e/caf0 entry";return false;
    }
    try {
        std::vector<VideoPortWrite> pending;pending.reserve(entry==0xca9eU?773U:2072U);
        for(unsigned int index=0;index<768U;++index)emit(pending,4,0x3c0000,(0x7500U+index)<<16);
        for(unsigned int index=0;index<4U;++index)emit(pending,4,0x3c0000,((0x7500U+index*32U)<<16)|0x200U);
        emit(pending,4,0x3c0000,0x7580ff02U);
        if(entry==0xcaf0U) {
            rectangle(pending,0x7021,0xff,38,30);rectangle(pending,0x701f,0x7000,40,1);
            rectangle(pending,0x7000,0x7000,40,1);rectangle(pending,0x7000,0x7000,1,32);
            rectangle(pending,0x74e0,0x7000,1,32);
        }
        ports.swap(pending);d0=entry==0xca9eU?0x7580ff02U:0x75807500U;d1=entry==0xca9eU?0U:0x7000U;
        if(entry==0xcaf0U){ram[0x966]=0;d3=32;}
        error.clear();return true;
    } catch(const std::bad_alloc&) {error="cannot allocate screen reset ports";return false;}
}
}
