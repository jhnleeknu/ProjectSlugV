#ifndef MS5_OBJECT_SOUND_LOOKUP_H
#define MS5_OBJECT_SOUND_LOOKUP_H
#include "ms5/fixed_data_resource.h"
#include "ms5/sound_word_execution.h"
namespace ms5 {
struct ObjectSoundLookupState {
    SoundWordExecutionState sound;
    std::uint32_t a5, a6;
    unsigned int phase;
    std::uint32_t saved_a0;
    ObjectSoundLookupState() : a5(0x108000), a6(0), phase(0), saved_a0(0) {}
};
// Full47672/ca70 with real3af8 continuation and reached fixed raw WORD
// lookup at4411e. phase0 is idle; phase1 retains saved A0 and a sound wait.
// Only actual sound calls/resumes require A5=108000. Other reached RAM
// accesses support checked arbitrary A5/A6. Waiting skips the prefix and
// does not consume lookup windows. RAM, fifteen registers, pending metadata
// and external_reads are preserved on failure; exact64KiB RAM is required.
bool execute_object_sound_lookup(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, ObjectSoundLookupState& state,
    std::uint8_t external_status, std::uint8_t& external_reads,
    std::string& error);
}
#endif
