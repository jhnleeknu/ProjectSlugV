#ifndef MS5_STAGE_INPUT_LOOP_H
#define MS5_STAGE_INPUT_LOOP_H
#include "ms5/stage_input_callback.h"
namespace ms5 {
// Confirmed49b0c two-player input loop,47642 activity mask,4d7a6 player read,
// and1da60 callback. A6 is read only. Fixed windows are borrowed and RAM is live.
// Failure preserves all64KiB RAM and thirteen registers; dynamic unknown
// callbacks are rejected only when reached. Active player lookup requires the
// existing exact4cf64/4092-byte resource; default masks are supplied as data.
bool step_stage_input_loop(std::vector<std::uint8_t>& ram, std::uint32_t entry,
    const std::vector<FixedDataResource>& windows, SceneMapTransferState& state,
    std::uint32_t parent_a6, std::string& error);
}
#endif
