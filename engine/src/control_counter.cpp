#include "ms5/control_counter.h"
namespace ms5 {
bool advance_control_counter(std::vector<std::uint8_t>& ram,
                             std::uint32_t object_address,bool& trap15,
                             std::string& error) {
    if(ram.size()!=65536U || (object_address&1U)!=0 ||
       object_address<0x100000U || object_address>0x10ff80U) {
        error="control counter requires 64KiB RAM and an even complete object span";return false;
    }
    const std::size_t at=object_address-0x100000U+0x7eU;
    const unsigned int counter=(static_cast<unsigned int>(ram[at])<<8)|ram[at+1];
    const unsigned int global=(static_cast<unsigned int>(ram[0x0e])<<8)|ram[0x0f];
    if(counter!=global) {trap15=true;error.clear();return true;}
    const unsigned int next=(counter+1U)&0xffffU;
    ram[0x0e]=static_cast<std::uint8_t>(next>>8);ram[0x0f]=static_cast<std::uint8_t>(next);
    ram[at]=static_cast<std::uint8_t>(next>>8);ram[at+1]=static_cast<std::uint8_t>(next);
    ram[0xd494]=static_cast<std::uint8_t>((ram[0xd494]&1U)+1U);
    trap15=false;error.clear();return true;
}
}
