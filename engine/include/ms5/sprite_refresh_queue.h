#ifndef MS5_SPRITE_REFRESH_QUEUE_H
#define MS5_SPRITE_REFRESH_QUEUE_H

#include "ms5/composition_resource.h"
#include "ms5/sprite_composition.h"

namespace ms5 {

// Normal rectangle dispatcher at CPU 0x016cfa: two slot pools, a 256-entry
// offset ring, alternating traversal, cached columns and trailing Y cleanup.
// RAM is exactly the 65536-byte work RAM image. Resources have unique exact IDs.
// A pool containing four 0xffff words is disabled and emits no writes.
// Ready records require marker 0xffff and style low byte 0 or 4 (pool select).
// Record X must be producer-aligned: its fixed-point word has low six bits zero.
// Success replaces writes, sets processed to the original ready bit and clears
// error. Failure preserves RAM, writes and processed. A non-ready queue skips
// all validation except RAM size. CPU registers, flags and timing are omitted.
bool refresh_sprite_queue(std::vector<std::uint8_t>& ram,
                          const std::vector<CompositionResource>& resources,
                          std::vector<SpriteWrite>& writes,
                          bool& processed, std::string& error);

} // namespace ms5

#endif
