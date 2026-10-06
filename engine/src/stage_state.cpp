#include "ms5/stage_state.h"
namespace ms5 {
bool set_stage_state(std::vector<std::uint8_t>& ram,StageStateAction action,
                     std::uint16_t value,std::string& error) {
    if(ram.size()!=65536U) {error="stage state requires exactly 65536 RAM bytes";return false;}
    if(action==SelectStage) {ram[0xd680]=static_cast<std::uint8_t>(value<19U?value:0U);ram[0xd681]=0;}
    else if(action==SelectStageArea) ram[0xd681]=static_cast<std::uint8_t>(value);
    else if(action==SelectNextStageArea) ram[0xd681]=static_cast<std::uint8_t>(ram[0x0bad]+1U);
    else {error="unknown stage state action";return false;}
    error.clear();return true;
}
}
