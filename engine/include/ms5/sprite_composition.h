#ifndef MS5_SPRITE_COMPOSITION_H
#define MS5_SPRITE_COMPOSITION_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct SpriteWrite {
    std::uint16_t address;
    std::uint16_t value;
};

// Ordered VRAM word writes from the normal rectangular branch of CPU 0x00ce82.
// data is exactly one original big-endian block: 0x0100, dx, dy, width/height,
// then column-major (attribute, tile) word pairs. Width is 1..255; height 1..32.
// dy is retained in the input but this branch does not emit a Y control word.
// Only style low-byte bits 0..2 are supported. first_slot <= limit <= 380.
// This is not a full sprite renderer: flips, animation and other branches are
// outside the contract. Success replaces writes and sets next_slot; failure
// leaves both unchanged and reports error. Registers/condition flags are omitted.
bool emit_sprite_rectangle(const std::vector<std::uint8_t>& data,
                           std::uint16_t coordinate_u, std::uint16_t style,
                           std::uint16_t first_slot, std::uint16_t limit,
                           std::vector<SpriteWrite>& writes,
                           std::uint16_t& next_slot, std::string& error);

// Normal rectangular refresh branch of CPU 0x00f246, with the same data/style
// restrictions as above. Each accepted column emits its Y control word first.
// Slots below cached_end retain their X/zoom/tile words; all accepted columns
// consume a slot. cached_end may be below first_slot but must be <= 380.
// This does not implement the flip branches or the full sprite/animation path.
// Failure leaves writes and next_slot unchanged.
bool emit_sprite_rectangle_refresh(const std::vector<std::uint8_t>& data,
                                   std::uint16_t coordinate_u,
                                   std::uint16_t coordinate_v,
                                   std::uint16_t style,
                                   std::uint16_t first_slot,
                                   std::uint16_t limit,
                                   std::uint16_t cached_end,
                                   std::vector<SpriteWrite>& writes,
                                   std::uint16_t& next_slot,
                                   std::string& error);

} // namespace ms5

#endif
