#ifndef MS5_GAME_SCREEN_RESET_EXECUTION_H
#define MS5_GAME_SCREEN_RESET_EXECUTION_H
#include "ms5/object_restart_execution.h"
namespace ms5 {
// Full nativeca9e/caf0 fifteen-register effects and ordered watchdog/video
// writes. ca9e leaves RAM unchanged and accepts arbitrary A5. caf0 clears
// BYTE(A5-769a), requiring its actual destination in CPU100000..10ffff;
// odd BYTE destinations are supported. Incoming A5 is always preserved.
// Failure preserves RAM/state/ports. Success replaces ports with this call's
// writes. Stack/CCR/cycles and physical video mirroring are excluded.
bool reset_game_screen_full(std::vector<std::uint8_t>& ram,
    std::uint32_t entry, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
