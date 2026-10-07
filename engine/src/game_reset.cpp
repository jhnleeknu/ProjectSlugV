#include "ms5/game_reset.h"
namespace ms5 {
namespace {
void clear_bytes(std::vector<std::uint8_t>& ram,std::size_t start,std::size_t size) {
    for(std::size_t index=0;index<size;++index)ram[start+index]=0;
}
void word(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
void clear_pair_fields(std::vector<std::uint8_t>& ram,std::size_t base) {
    word(ram,base,0);ram[base+0x22U]=0;word(ram,base+6U,0);clear_bytes(ram,base+8U,4U);
}
}
bool reset_game_subsystem(std::vector<std::uint8_t>& ram,std::uint32_t entry,
                          std::uint32_t& d0,std::uint32_t& d1,
                          std::uint32_t& d3,std::string& error) {
    if(ram.size()!=65536U) {error="game reset requires exactly64KiB RAM";return false;}
    switch(entry) {
    case 0xb7a20U:
        clear_bytes(ram,0xdddcU,7U);clear_bytes(ram,0xdde4U,7U);break;
    case 0x4d126U:
    case 0x4d13cU:
        for(unsigned int index=0;index<2U;++index) {
            const std::size_t base=0xdcbaU+index*0x2cU;
            if(entry==0x4d126U) {
                ram[base+0x25U]=0;ram[base+0x26U]=4;ram[base+0x27U]=0;
                word(ram,base+0x1cU,0);word(ram,base+0x1aU,0);
                word(ram,base+0x20U,0xffffU);ram[base+0x2aU]=0;
            }
            clear_pair_fields(ram,base);
        }
        break;
    case 0x49a8eU:
        clear_bytes(ram,0xd726U,12U);clear_bytes(ram,0xd734U,8U);break;
    case 0x4aa30U:
        clear_bytes(ram,0xdb84U,4U);clear_bytes(ram,0xdaf8U,128U);
        word(ram,0xdc88U,0x10U);word(ram,0xdc8aU,0xdb88U);
        clear_bytes(ram,0xdb88U,256U);
        for(unsigned int index=0;index<2U;++index) {
            const std::size_t base=0xd746U+index*0x1d2U;
            clear_bytes(ram,base,0xd0U);word(ram,base+0x1d0U,0);
        }
        d0=0;d1=0;d3=0;break;
    case 0xb4a24U:
        for(unsigned int index=0;index<12U;++index)word(ram,0xdd5cU+index*10U,0);
        d0=0;break;
    case 0x2ef90U:
        ram[0xd487U]=0;ram[0xd48fU]=0;ram[0xd490U]=0;ram[0xd491U]=0;
        d0=1;break;
    case 0x46f2eU:
        for(unsigned int index=0;index<8U;++index) {
            const std::size_t base=0xd4e6U+index*0x2cU;
            clear_bytes(ram,base,0x26U);word(ram,base+0x26U,0xffffU);word(ram,base+0x2aU,0);
        }
        d0=0;break;
    case 0x4ddb6U:
        for(unsigned int index=0;index<2U;++index) {
            const std::size_t base=0xdd12U+index*6U;
            ram[base]=1;clear_bytes(ram,base+1U,3U);word(ram,base+4U,0xffffU);
        }
        break;
    default:error="unsupported fixed-ROM game reset entry";return false;
    }
    error.clear();return true;
}
}
