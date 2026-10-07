#ifndef MS5_SPRITE_PREPARE_QUEUE_H
#define MS5_SPRITE_PREPARE_QUEUE_H

#include "ms5/composition_resource.h"
#include "ms5/sprite_composition.h"

namespace ms5 {

struct SpritePreparePending {
    bool waiting;
    std::uint16_t cursor;
    SpritePreparePending();
};

// Execute 0x016bba through 0x016bcc: merge and sort exactly once, then
// capture the cursor held by D0 at the consumer wait (0x016bd0).
// Success always exposes that boundary with waiting=true, even if ready.
// No composition resources or output writes are needed at this boundary.
// Failure preserves RAM and pending. Calling begin while pending.waiting
// is true fails without mutation. Success clears error.
bool begin_sprite_queue(std::vector<std::uint8_t>& ram,
                        SpritePreparePending& pending, std::string& error);

// Poll the captured cursor against the live consumer cursor. While unequal,
// succeed with unchanged RAM/pending and empty writes. Once equal, use live
// direction/pools/ring data to emit WITHOUT merging or sorting again, then
// clear pending. The caller must preserve pending across consumer service.
// As with the synchronous API below, CPU scratch registers, PVC port writes
// and timing are outside this contract. Failure preserves every output.
bool resume_sprite_queue(std::vector<std::uint8_t>& ram,
                         const std::vector<CompositionResource>& resources,
                         SpritePreparePending& pending,
                         std::vector<SpriteWrite>& writes, std::string& error);

// Normal rectangle preparation at CPU 0x016bba: merge deferred entries, sort
// the pending ring, then emit without Y writes in the current traversal direction.
// RAM is exactly the 65536-byte work RAM image; resources have unique exact IDs.
// Read and prepared cursors must agree: an active consumer is rejected without
// mutation instead of simulating the original wait. Normal plus deferred entries
// must match the producer end and fit the 255-entry unambiguous pending ring.
// A pool containing four 0xffff words is disabled and emits no writes.
// Records require marker 0xffff, style low byte 0..7 and X low six bits zero.
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
