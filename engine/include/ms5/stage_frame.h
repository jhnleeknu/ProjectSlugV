#ifndef MS5_STAGE_FRAME_H
#define MS5_STAGE_FRAME_H
#include "ms5/stage_buffer_frame.h"
#include "ms5/sprite_producer.h"
namespace ms5 {
struct StageFrameState {
    StageBufferFrameState buffer;
    unsigned int stage;
    SpriteSubmitStatus cue_status;
    unsigned int sound_kind, sound_phase;
    std::uint16_t sound_saved;
    StageFrameState() : stage(0), cue_status(SpriteAccepted), sound_kind(0), sound_phase(0), sound_saved(0) {}
};
// Native480bc composition. Stage1/2/3 resumes only buffer/cue/sound waits.
// buffer.registers, buffer.a6 and buffer.bank are the sole register authority.
// Buffer saved metadata is zero outside stage1; cue_status accepts0..3 and
// preserves its incoming value when no cue submission is reached.
// Successful waits retain completed effects; ports and external_reads contain
// only this call's effects. Failure preserves RAM/state/ports/external_reads.
bool step_stage_frame(std::vector<std::uint8_t>& ram,
    const FixedDataResource& tables, const std::vector<FixedDataResource>& windows,
    StageFrameState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::vector<VideoPortWrite>& ports,
    std::string& error);
}
#endif
