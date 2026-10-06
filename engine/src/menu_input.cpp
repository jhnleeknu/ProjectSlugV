#include "ms5/menu_input.h"

namespace ms5 {

bool select_menu_input(std::vector<std::uint8_t>& ram,
                       MenuInput& out, std::string& error) {
    if (ram.size() != 65536U) {
        error = "menu input requires exactly 65536 RAM bytes";
        return false;
    }
    const std::uint32_t current_address =
        (static_cast<std::uint32_t>(ram[0x7f12U]) << 24) |
        (static_cast<std::uint32_t>(ram[0x7f13U]) << 16) |
        (static_cast<std::uint32_t>(ram[0x7f14U]) << 8) |
        static_cast<std::uint32_t>(ram[0x7f15U]);
    if (current_address < 0x00107e0eU || current_address > 0x00107efeU ||
        (current_address - 0x00107e0eU) % 16U != 0U) {
        error = "menu input requires an aligned current menu slot";
        return false;
    }
    const std::size_t current = current_address - 0x00100000U;
    const std::uint8_t enabled = ram[current + 13U];
    const std::uint8_t player1 = (enabled & 1U) != 0U ? ram[0x4cbaU] : 0U;
    const std::uint8_t player2 = (enabled & 2U) != 0U ? ram[0x4cc0U] : 0U;
    const unsigned int combined = static_cast<unsigned int>(player1) | player2;
    const unsigned int priority[6] = {0U, 1U, 2U, 3U, 5U, 4U};
    const std::uint8_t events[6] = {0U, 0U, 1U, 2U, 4U, 3U};
    MenuInput candidate;
    candidate.kind = MenuInputNone;
    candidate.event = 0U;
    candidate.sources = 0U;
    for (unsigned int index = 0U; index < 6U; ++index) {
        const unsigned int mask = 1U << priority[index];
        if ((combined & mask) == 0U) {
            continue;
        }
        candidate.kind = index == 0U ? MenuInputPrevious :
            (index == 1U ? MenuInputNext : MenuInputEvent);
        candidate.event = events[index];
        candidate.sources = static_cast<std::uint8_t>(
            ((player1 & mask) != 0U ? 1U : 0U) |
            ((player2 & mask) != 0U ? 2U : 0U));
        break;
    }
    ram[0x7f1aU] = candidate.sources;
    out = candidate;
    error.clear();
    return true;
}

} // namespace ms5
