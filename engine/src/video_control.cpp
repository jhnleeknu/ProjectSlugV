#include "ms5/video_control.h"
#include <new>
namespace ms5 {
bool query_video_control(const std::vector<std::uint8_t>& ram,
                         std::uint16_t& value,std::string& error) {
    if(ram.size()!=65536U) {error="video control requires exactly 65536 RAM bytes";return false;}
    value=(ram[0x4d91]&8U)!=0?0:static_cast<std::uint16_t>(static_cast<unsigned int>(ram[0x4d90])+1U);
    error.clear();return true;
}
bool set_video_control(std::vector<std::uint8_t>& ram,std::uint16_t value,
                       std::vector<VideoPortWrite>& writes,std::string& error) {
    if(ram.size()!=65536U) {error="video control requires exactly 65536 RAM bytes";return false;}
    const std::uint8_t high=value==0?0:static_cast<std::uint8_t>(static_cast<unsigned int>(value)-1U);
    const std::uint8_t low=value==0?static_cast<std::uint8_t>(ram[0x4d91]|8U):
                                            static_cast<std::uint8_t>(ram[0x4d91]&247U);
    try {
        std::vector<VideoPortWrite> pending(1);
        pending[0].address=0x3c0006U;pending[0].size=2;
        pending[0].value=(static_cast<std::uint32_t>(high)<<8)|low;
        // All possible allocation failures precede the RAM/output commit.
        ram[0x4d90]=high;ram[0x4d91]=low;writes.swap(pending);
    } catch(const std::bad_alloc&) {error="cannot allocate video control port write";return false;}
    error.clear();return true;
}
}
