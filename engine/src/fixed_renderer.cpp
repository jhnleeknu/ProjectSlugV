#include "ms5/fixed_renderer.h"

namespace ms5 {

bool render_fixed_layer_words(const TileResource& tiles,
                              const std::vector<std::uint16_t>& vram,
                              const std::vector<std::uint16_t>& palette,
                              std::vector<std::uint16_t>& frame,
                              std::string& error) {
    if (tiles.kind != 2 || tiles.width != 8 || tiles.height != 8 ||
        tiles.count != 4096 || tiles.pixels.size() != 262144) {
        error = "fixed tiles must be kind 2, 8 by 8, with 4096 complete tiles";
        return false;
    }
    if (vram.size() != 1280 || palette.size() < 256 || frame.size() != 320 * 256) {
        error = "fixed renderer requires 1280 VRAM words, at least 256 palette words, and 81920 frame words";
        return false;
    }
    for (std::size_t index = 0; index < tiles.pixels.size(); ++index) {
        if (tiles.pixels[index] > 15) {
            error = "fixed tile pixel exceeds 4-bit range";
            return false;
        }
    }
    // Snapshot the palette so an aliased frame/palette also has stable reads.
    std::uint16_t palette_words[256];
    for (std::size_t index = 0; index < 256; ++index) {
        palette_words[index] = palette[index];
    }
    for (std::size_t y = 0; y < 256; ++y) {
        for (std::size_t x = 0; x < 320; ++x) {
            const std::uint16_t word = vram[(x / 8) * 32 + y / 8];
            const std::size_t tile = word & 0x0fffU;
            const std::size_t slot = word >> 12;
            const std::uint8_t pixel = tiles.pixels[tile * 64 + (y % 8) * 8 + x % 8];
            if (pixel != 0) {
                frame[y * 320 + x] = palette_words[slot * 16 + pixel];
            }
        }
    }
    error.clear();
    return true;
}

} // namespace ms5
