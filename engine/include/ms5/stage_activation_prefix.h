#ifndef MS5_STAGE_ACTIVATION_PREFIX_H
#define MS5_STAGE_ACTIVATION_PREFIX_H
#include "ms5/stage_block_draw.h"
namespace ms5 {
// Native47c04 prefix, stopping BEFORE47c6c fall-through. Full15registers;
// arbitrary A5/A6 supported only where each actual access fits CPU RAM.
// Reads remain live, including helper/parent aliases. Fixed block windows
// are consumed only on the selected477a2 branch. Success replaces ports;
// failure preserves all RAM/registers/ports. CCR/stack/cycles and the
// subsequent47c6c callback body are outside this API.
bool initialize_stage_activation_prefix(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
