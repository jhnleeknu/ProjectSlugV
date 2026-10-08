#ifndef MS5_SOUND_CANCEL_EXECUTION_H
#define MS5_SOUND_CANCEL_EXECUTION_H
#include "ms5/sound_byte_execution.h"
namespace ms5 {
struct SoundCancelExecutionState {
    SoundByteExecutionState byte;
    std::uint16_t saved_word;
    unsigned int phase;
    SoundCancelExecutionState() : saved_word(0), phase(0) {}
};
// Whole 3c44, including three independently waiting byte submissions.
// Phase 0 starts fresh; phases 1..3 resume a captured waiting byte helper.
// Actual aligned RAM WORD access is required, without a logical ring limit.
// Errors, including nonterminating scans, preserve the entire RAM and state.
bool execute_sound_cancel(std::vector<std::uint8_t>& ram,
    SoundCancelExecutionState& state, std::string& error);
}
#endif
