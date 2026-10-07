#include "ms5/frame_gate.h"
namespace ms5 {
bool poll_frame_gate(std::vector<std::uint8_t>& ram,std::uint16_t video,
                     bool& ready,std::string& error) {
    if(ram.size()!=65536U) {error="frame gate requires 64KiB RAM";return false;}
    ready=ram[0x16]>=ram[0x17];
    if(ready) {
        const unsigned int counter=static_cast<unsigned int>(video)>>7;
        ram[0x18]=static_cast<std::uint8_t>(counter>=0x100U ? counter-0x100U : 0);
    }
    error.clear();return true;
}
}
