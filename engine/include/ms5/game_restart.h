#ifndef MS5_GAME_RESTART_H
#define MS5_GAME_RESTART_H
#include "ms5/game_initialization.h"
#include "ms5/video_port.h"
namespace ms5 {
struct GameRestartState {
    std::uint8_t phase;
    std::uint32_t a6;
    GameInitializationState initialization;
    GameRestartState() : phase(0), a6(0) {}
};
// Native c610..c652 return; phase0 starts, phase1 resumes a 3aea sound wait,
// phase2 is returned and cannot be resumed. Callback c654 is installed only.
// Inner next_pc475a4/phase4 remains an internal boundary, not caller return PC.
// ROM180.word=0 input initialization specialization. Errors preserve all
// RAM/state/read count/ordered ports. Other registers/CCR/stack excluded.
bool restart_game(std::vector<std::uint8_t>& ram, const FixedDataResource& records,
                  const FixedDataResource& streams, std::uint8_t external_status,
                  GameRestartState& state, std::uint8_t& external_reads,
                  std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
