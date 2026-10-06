#ifndef MS5_ANIMATION_DRAW_H
#define MS5_ANIMATION_DRAW_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct AnimationDraw {
    bool skipped;
    std::uint32_t d0;
    std::uint32_t d1;
    std::uint32_t d5;
    std::uint32_t d7;
};

// Decode CPU 0x04a10c draw arguments before sprite submission. RAM maps
// CPU 0x100000 and must contain exactly 65536 bytes. The seven operand bytes
// are control, signed X, signed Y and a big-endian resource identifier.
// object_offset must leave 0x62 bytes in RAM. Skipped draws have zero registers.
// RAM and operand are never changed; invalid input preserves result.
bool decode_animation_draw(const std::vector<std::uint8_t>& ram,
                           std::size_t object_offset,
                           const std::vector<std::uint8_t>& operand,
                           AnimationDraw& result, std::string& error);

} // namespace ms5

#endif
