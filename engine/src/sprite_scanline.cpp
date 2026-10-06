// Behavior adapted from MAME neogeo_spr.cpp (BSD-3-Clause).
// Copyright Bryan McPhail, Ernesto Corvi, Andrew Prime, Zsolt Vasvari.
// See tools/licenses/mame-sprites.txt.
#include "ms5/sprite_scanline.h"

namespace ms5 {

bool parse_sprite_scanline(std::vector<std::uint16_t>& vram,
                           std::uint16_t scanline, std::string& error) {
    if (vram.size() != 0x8800U) {
        error = "VRAM must contain exactly 0x8800 words";
        return false;
    }
    if (scanline > 511U) {
        error = "scanline must be 0..511";
        return false;
    }

    const std::size_t list_base = (scanline & 1U) != 0U ? 0x8680U : 0x8600U;
    std::uint32_t y = 0;
    std::uint32_t rows = 0;
    std::size_t count = 0;
    for (std::uint16_t sprite = 0; sprite < 381U; ++sprite) {
        const std::uint16_t control = vram[0x8200U | sprite];
        if ((control & 0x0040U) == 0U) {
            y = 512U - (control >> 7);
            rows = control & 0x003fU;
        }
        if (rows == 0U) {
            continue;
        }
        // Unsigned subtraction followed by the 9-bit mask explicitly models
        // wraparound without relying on a signed negative bit representation.
        const std::uint32_t line = (static_cast<std::uint32_t>(scanline) - y) & 511U;
        if (rows < 32U && line >= rows * 16U) {
            continue;
        }
        vram[list_base + count] = sprite;
        ++count;
        if (count == 96U) {
            break;
        }
    }
    for (; count <= 96U; ++count) {
        vram[list_base + count] = 0;
    }
    error.clear();
    return true;
}

} // namespace ms5
