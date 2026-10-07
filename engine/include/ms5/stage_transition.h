#ifndef MS5_STAGE_TRANSITION_H
#define MS5_STAGE_TRANSITION_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
struct StageTransitionState {
    std::uint32_t next_pc, d0, d1, d2, d3, a6;
    StageTransitionState() : next_pc(0x478c4), d0(0), d1(0), d2(0), d3(0), a6(0x100b30) {}
};
// Supported dispatch prefixes/callbacks stop before480bc or479b0 bodies;
// palette wait stops at478de. Exact64KiB RAM and aligned c4-byte A6 span.
// Errors preserve RAM, full state and ordered hardware writes.
bool step_stage_transition(std::vector<std::uint8_t>& ram, StageTransitionState& state,
                           std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
