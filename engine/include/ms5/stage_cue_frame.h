#ifndef MS5_STAGE_CUE_FRAME_H
#define MS5_STAGE_CUE_FRAME_H
#include "ms5/scene_map_transfer.h"
#include "ms5/sprite_producer.h"
namespace ms5 {
struct StageCueFrameState {
    SceneMapTransferState registers;
    bool waiting_for_sprite;
    StageCueFrameState() : waiting_for_sprite(false) {}
};
// Native e8a48 including2986 allocation,43e08 position, cue progression and
// default-callback debug sprite submission. Waiting resumes only cda4;
// callers retain the returned registers and RAM. A6 remains unchanged.
// Borrowed fixed windows and live RAM are read in source order. Failure
// preserves all RAM, registers, waiting and debug_status. When debug sprite
// submission is not reached, debug_status retains its incoming value.
bool step_stage_cue_frame(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, StageCueFrameState& state,
    std::uint32_t parent_a6, SpriteSubmitStatus& debug_status, std::string& error);
}
#endif
