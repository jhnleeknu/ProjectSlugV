#include "ms5/palette_snapshot.h"

#include <cstddef>

namespace ms5 {

bool save_palette_effect(std::vector<std::uint8_t>& ram, std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    for (std::size_t index = 0; index < 20; ++index) {
        ram[0x7dd6 + index] = ram[0x7dc2 + index];
    }
    error.clear();
    return true;
}

bool restore_palette_effect(std::vector<std::uint8_t>& ram, std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    const std::uint8_t previous_red = ram[0x7dc2];
    const std::uint8_t previous_green = ram[0x7dc4];
    const std::uint8_t previous_blue = ram[0x7dc6];
    for (std::size_t index = 0; index < 20; ++index) {
        ram[0x7dc2 + index] = ram[0x7dd6 + index];
    }
    if (ram[0x7dd4] == 0) {
        ram[0x7dd4] = 1;
        ram[0x7dc2] = previous_red;
        ram[0x7dc4] = previous_green;
        ram[0x7dc6] = previous_blue;
    }
    error.clear();
    return true;
}

} // namespace ms5
