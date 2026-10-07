#ifndef MS5_GAME_READY_H
#define MS5_GAME_READY_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
struct GameReadyState {
    std::uint32_t next_pc, d0, d1, d3, a6;
    GameReadyState() : next_pc(0xc654), d0(0), d1(0), d3(0), a6(0) {}
};
// Native c654/c66a/c686/c6c0 to actual c724/c73e/c00444 boundaries.
// Canonical ROM180.word=0 only; ROM mutation/restart branch excluded.
// Exact64KiB RAM, aligned c4-byte A6 object. Errors preserve RAM/state/ports.
// Installs callbacks477e4/e66aa but executes neither; no invented RTS/BIOS.
bool step_game_ready(std::vector<std::uint8_t>& ram, GameReadyState& state,
                     std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
