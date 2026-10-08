#ifndef MS5_STAGE_HUD_COUNTER_H
#define MS5_STAGE_HUD_COUNTER_H
#include "ms5/sound_word_execution.h"
namespace ms5 {
struct StageHudCounterState {
    SoundWordExecutionState sound;
    std::uint32_t a5,a6;
    unsigned int phase;
    std::uint16_t saved_d0;
    StageHudCounterState() : a5(0x108000),a6(0),phase(0),saved_d0(0) {}
};
// Whole native4e286. sound.byte.registers is the sole D0..D7/A0..A4
// authority. Phase1 resumes only captured sound work; counter/flag prefix
// is not repeated. A5/A6 are preserved. Fixed or live RAM WORD lookup reads
// require unique complete spans; resources are checked only when consumed.
// Actual sound calls/resumes require A5=108000 because the sound API has
// that implicit base. Other paths support arbitrary checked A5 accesses.
// Successful waits commit actual effects. Errors preserve RAM/state/reads/
// ports; success replaces ports with this call's ordered writes. CCR/stack/
// cycles and natural scheduling are outside this API.
bool step_stage_hud_counter(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, StageHudCounterState& state,
    std::uint8_t external_status,std::uint8_t& external_reads,
    std::vector<VideoPortWrite>& ports,std::string& error);
}
#endif
