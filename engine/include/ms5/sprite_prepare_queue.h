#ifndef MS5_SPRITE_PREPARE_QUEUE_H
#define MS5_SPRITE_PREPARE_QUEUE_H

#include "ms5/composition_resource.h"
#include "ms5/sprite_composition.h"

namespace ms5 {

// Normal rectangle preparation at CPU 0x016bba: merge deferred entries, sort
// the pending ring, then emit without Y writes in the current traversal direction.
// RAM is exactly the 65536-byte work RAM image; resources have unique exact IDs.
// Read and prepared cursors must agree: an active consumer is rejected without
// mutation instead of simulating the original wait. Normal plus deferred entries
// must match the producer end and fit the 255-entry unambiguous pending ring.
// Records require marker 0xffff, style low byte 0 or 4 and X low six bits zero.
// Allocation starts at the physical pool boundary and stops at its opposite
// cached slot boundary. Success publishes producer end as prepared/normal end,
// sets ready byte to 0xff, clears RAM word 0x10 and replaces writes. Direction
// and read cursor remain unchanged; CPU flags, registers and timing are omitted.
// Failure preserves RAM and writes; success clears error.
bool prepare_sprite_queue(std::vector<std::uint8_t>& ram,
                          const std::vector<CompositionResource>& resources,
                          std::vector<SpriteWrite>& writes, std::string& error);

} // namespace ms5

#endif
