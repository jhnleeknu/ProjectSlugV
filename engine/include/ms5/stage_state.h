#ifndef MS5_STAGE_STATE_H
#define MS5_STAGE_STATE_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
enum StageStateAction { SelectStage=0, SelectStageArea=1, SelectNextStageArea=2 };
// RAM effects of4823a/48250/48256. Stage is an unsigned word, >=19 clamps0
// and resets area. Explicit area stores its lowbyte. Next area derives from
// RAM0bad+1 with byte wrapping. Failure preserves all RAM.
bool set_stage_state(std::vector<std::uint8_t>& ram,StageStateAction action,
                     std::uint16_t value,std::string& error);
}
#endif
