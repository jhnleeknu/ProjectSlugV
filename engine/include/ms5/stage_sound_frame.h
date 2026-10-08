#ifndef MS5_STAGE_SOUND_FRAME_H
#define MS5_STAGE_SOUND_FRAME_H
#include "ms5/sound_byte_execution.h"
namespace ms5 {
struct StageSoundFrameState {
    SoundByteExecutionState byte;
    std::uint16_t saved;
    unsigned int kind;
    unsigned int phase;
    StageSoundFrameState() : saved(0), kind(0), phase(0) {}
};
// Whole 0x2efa6 with captured word/cancel helper continuations.
// kind 0 starts fresh; kind 1/2 resumes word/cancel byte waits respectively.
// A waiting continuation does not sample d490/d491 or republish d491.
// Errors preserve RAM, state and external_reads. A5 is fixed at 0x108000.
bool step_stage_sound_frame(std::vector<std::uint8_t>& ram,
    StageSoundFrameState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::string& error);
}
#endif
