#ifndef MS5_GAME_SCREEN_RESET_H
#define MS5_GAME_SCREEN_RESET_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
// Original ca9e or caf0. Ordered watchdog/video writes; full D0/D1/D3.
// Failure preserves RAM, registers and ports. Fixed caf0 rectangles avoid
// the native35a2 TRAP range; arbitrary rectangle inputs are not exposed.
// ca9e port construction also exists inside control_menu_start; unification
// is deferred so that this API does not change the existing menu-start path.
bool reset_game_screen(std::vector<std::uint8_t>& ram,std::uint32_t entry,
    std::uint32_t& d0,std::uint32_t& d1,std::uint32_t& d3,
    std::vector<VideoPortWrite>& ports,std::string& error);
}
#endif
