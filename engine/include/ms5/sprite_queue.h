#ifndef MS5_SPRITE_QUEUE_H
#define MS5_SPRITE_QUEUE_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Memory effects of CPU 0x00ce02: unsigned ascending deferred keys, original
// swap behavior on ties, replacement of selected keys with the previous tag,
// and appending offsets to the 256-word output ring. ram maps CPU 0x100000
// and must contain exactly 65536 bytes. Registers and consumer concurrency are
// outside this contract. All input validation precedes any RAM modification.
// Deferred offsets must identify distinct 12-byte records, including offset 0.
// A count of 512 bytes is supported by table storage; without consumer progress
// the original producer reaches at most 255 deferred records. The 256-record
// case is a storage boundary extension, not a proven original execution case.
bool sort_deferred_sprites(std::vector<std::uint8_t>& ram,
                           std::uint16_t new_tag, std::string& error);

// Memory effects of CPU 0x0166bc: stable unsigned 16-bit key sort of the
// display ring from BE word 0x8d36 to 0x8d3a, including histogram and temporary
// table mutations. RAM maps CPU 0x100000 and contains exactly 65536 bytes.
// Ring cursors are even byte offsets in 0..510. Equal cursors mean empty;
// nonempty rings contain at most 255 entries. Record offsets are multiples of
// 12 in 0..3060; repeated offsets are allowed. Invalid input preserves RAM.
bool radix_sort_sprite_queue(std::vector<std::uint8_t>& ram,
                             std::string& error);

} // namespace ms5

#endif
