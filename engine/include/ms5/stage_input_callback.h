#ifndef MS5_STAGE_INPUT_CALLBACK_H
#define MS5_STAGE_INPUT_CALLBACK_H
#include "ms5/stage_input.h"
namespace ms5 {
// Eighteen confirmed callbacks, with borrowed fixed windows and live RAM reads.
// A6 is read only; failure preserves all RAM and thirteen registers.
// Default mapper masks are required only on paths reaching49f66.
bool step_stage_input_callback(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::string& error);
}
#endif
