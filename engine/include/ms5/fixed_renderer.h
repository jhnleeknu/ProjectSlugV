#ifndef MS5_FIXED_RENDERER_H
#define MS5_FIXED_RENDERER_H

#include "ms5/tile_resource.h"

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Unbanked 40 by 32 fixed tilemap, stored as 32 words per column.
// The frame contains 320 by 256 hardware palette words, not RGB values.
// Index zero preserves the existing frame word. Failure leaves frame unchanged.
bool render_fixed_layer_words(const TileResource& tiles,
                              const std::vector<std::uint16_t>& vram,
                              const std::vector<std::uint16_t>& palette,
                              std::vector<std::uint16_t>& frame,
                              std::string& error);

} // namespace ms5

#endif
