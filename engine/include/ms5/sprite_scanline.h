#ifndef MS5_SPRITE_SCANLINE_H
#define MS5_SPRITE_SCANLINE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Select up to 96 sprite IDs (0..380) for a scanline, following the pinned
// Neo Geo parse_sprites reference. VRAM must contain exactly 0x8800 words;
// scanline must be 0..511. Only 97 words in the parity-selected list at
// 0x8600 (even) or 0x8680 (odd) are written. Remaining entries, including
// entry 96, are zeroed. Chained sprites inherit the previous Y and row count.
// Failure preserves VRAM and reports error; success clears error.
bool parse_sprite_scanline(std::vector<std::uint16_t>& vram,
                           std::uint16_t scanline, std::string& error);

} // namespace ms5

#endif
