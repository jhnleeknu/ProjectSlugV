#ifndef MS5_SPRITE_PRODUCER_H
#define MS5_SPRITE_PRODUCER_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

enum SpriteSubmitStatus {
    SpriteAccepted = 0,
    SpriteClipped = 1,
    SpriteFull = 2,
    SpriteWaiting = 3
};

// Memory effects of CPU 0x00ccd6. RAM maps CPU 0x100000 and must contain
// exactly 65536 bytes. Initializes the default callback, cursors, ready byte,
// record offsets and both disabled pool sentinels. Direction is preserved.
bool initialize_sprite_queue(std::vector<std::uint8_t>& ram,
                             std::string& error);

// Memory/status effects of CPU 0x00cd58 with the default RTS callback at
// 0x00cd50 only. Other callbacks are rejected. No register effects are claimed.
// SpriteWaiting observes the first spin entry at CPU 0x00cda4. It does not
// resume that wait: the original captured target is not retained in this API.
// Clipping precedes queue validation. Invalid input preserves RAM and status.
bool submit_sprite(std::vector<std::uint8_t>& ram, std::uint32_t d0,
                   std::uint32_t d1, std::uint32_t d5, std::uint32_t d7,
                   SpriteSubmitStatus& status, std::string& error);

} // namespace ms5

#endif
