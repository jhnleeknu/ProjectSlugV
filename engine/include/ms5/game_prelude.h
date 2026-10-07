#ifndef MS5_GAME_PRELUDE_H
#define MS5_GAME_PRELUDE_H
#include "ms5/sound_word.h"
namespace ms5 {
struct GamePreludeState {
    std::uint32_t next_pc, d0, d1, d3;
    std::uint8_t phase;
    SoundWordPending word;
    SoundBytePending byte;
    GamePreludeState() : next_pc(0x47570), d0(0), d1(0), d3(0), phase(0) {}
};
// Native47570 prefix or47594 direct sound entry; complete at475a4 before
// its RAMd686 clear. Direct47594 skips prefix RAM stores and preserves D0.high16.
// Only47570 writes de26 with ROM pointere89e4, without dereferencing it.
// Waits stop at 3aea. Resumes never repeat the prefix or external status read.
// Errors preserve RAM, state and external_reads. No MMIO writes occur; external_reads counts the conditional d00046 read.
bool prepare_game_prelude(std::vector<std::uint8_t>& ram, std::uint8_t external_status,
                          GamePreludeState& state, std::uint8_t& external_reads,
                          std::string& error);
}
#endif
