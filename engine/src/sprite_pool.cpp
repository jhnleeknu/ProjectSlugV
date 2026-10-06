#include "ms5/sprite_pool.h"

namespace ms5 {

bool configure_sprite_pool(std::vector<std::uint8_t>& ram,
                           std::uint16_t selector, std::uint16_t lower,
                           std::uint16_t upper, std::string& error) {
    if (ram.size() != 65536U) {
        error = "sprite pool configuration requires exactly 65536 RAM bytes";
        return false;
    }
    if (lower >= 380U) {
        lower = 0xffffU;
    }
    if (lower >= upper) {
        upper = 0xffffU;
    }
    const std::size_t pool = selector == 0 ? 0x8d3eU : 0x8d46U;
    for (unsigned int index = 0; index < 4; ++index) {
        const std::uint16_t value = (index & 1U) == 0 ? lower : upper;
        ram[pool + index * 2U] = static_cast<std::uint8_t>(value >> 8);
        ram[pool + index * 2U + 1U] = static_cast<std::uint8_t>(value);
    }
    error.clear();
    return true;
}

} // namespace ms5
