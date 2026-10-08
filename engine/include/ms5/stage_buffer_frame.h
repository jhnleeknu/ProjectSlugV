#ifndef MS5_STAGE_BUFFER_FRAME_H
#define MS5_STAGE_BUFFER_FRAME_H
#include "ms5/scene_map_transfer.h"
namespace ms5 {
struct StageBufferFrameState {
    SceneMapTransferState registers;
    std::uint32_t a6, bank, phase, saved_a6, saved_slot_a4, saved_slot_d7;
    std::uint32_t saved_d0, saved_d1, saved_d7, saved_a0;
    StageBufferFrameState() : a6(0), bank(2), phase(0), saved_a6(0), saved_slot_a4(0), saved_slot_d7(0), saved_d0(0), saved_d1(0), saved_d7(0), saved_a0(0) {}
};
// Whole4aa88 with bank2/3 mapping, sixteen debug slots and two cd58 submissions.
// Phase1/2 resumes only the captured first/second sprite wait. Pending slot
// metadata must match its index0..15; saved_slot_d7 stores that WORD value.
// Completion clears saved metadata/phase and restores the outer A6. Success
// replaces ports with this call's writes; failure preserves RAM/state/ports.
bool step_stage_buffer_frame(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, StageBufferFrameState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
