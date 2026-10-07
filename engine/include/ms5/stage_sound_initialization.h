#ifndef MS5_STAGE_SOUND_INITIALIZATION_H
#define MS5_STAGE_SOUND_INITIALIZATION_H
#include "ms5/sound_word.h"
#include "ms5/stage_catalog.h"
namespace ms5 {
struct StageSoundState {
    std::uint32_t next_pc, d0, d1, d3, a6;
    std::uint8_t phase;
    SoundWordPending word;
    SoundBytePending byte;
    StageSoundState() : next_pc(0x47a1c), d0(0), d1(0), d3(0), a6(0x100b30), phase(0) {}
};
// Native47a1c..47a94 before remaining body. Phases1/4/5/6 word waits,
// 2/3 initial bytes, 7/8 final bytes; phase9 done,3aea waits. Fresh-only
// catalog lookup; captured continuation never re-reads music/record pointer.
// Whole RAM/state/reads transactional; D3/A6 preserved, no MMIO writes.
bool initialize_stage_sound(std::vector<std::uint8_t>& ram, const StageCatalog& catalog,
                            std::uint8_t external_status, StageSoundState& state,
                            std::uint8_t& external_reads, std::string& error);
}
#endif
