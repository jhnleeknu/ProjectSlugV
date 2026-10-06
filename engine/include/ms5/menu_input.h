#ifndef MS5_MENU_INPUT_H
#define MS5_MENU_INPUT_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

enum MenuInputKind {
    MenuInputNone = 0,
    MenuInputPrevious = 1,
    MenuInputNext = 2,
    MenuInputEvent = 3
};

struct MenuInput {
    MenuInputKind kind;
    std::uint8_t event;
    std::uint8_t sources;
};

// Confirmed CPU 0x00a472..0x00a562 input decision phase only.
// Does not move the selection, draw the menu, or dispatch the event.
// RAM is exactly 65536 bytes. Only the current slot pointer is validated;
// this phase does not read the head pointer. Success writes the selected
// sources to RAM 0x7f1a, replaces out, and clears error. Failure preserves
// RAM and out.
bool select_menu_input(std::vector<std::uint8_t>& ram,
                       MenuInput& out, std::string& error);

} // namespace ms5

#endif
