#ifndef MS5_SOUND_WORD_EXECUTION_H
#define MS5_SOUND_WORD_EXECUTION_H
#include "ms5/sound_byte_execution.h"
namespace ms5 {
struct SoundWordExecutionState {
    SoundByteExecutionState byte;
    std::uint8_t saved_low;
    unsigned int phase;
    SoundWordExecutionState() : saved_low(0), phase(0) {}
};
// Full 0x3af8 execution. phase 1/2 resumes a captured high/low byte wait.
// external_status supplies the conditional read at 0xd00046; external_reads
// reports reads in this invocation (zero on resume). Errors preserve all inputs
// except error. WORD accesses require aligned addresses in the actual 64KiB RAM.
bool execute_sound_word(std::vector<std::uint8_t>& ram,
    SoundWordExecutionState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::string& error);
}
#endif
