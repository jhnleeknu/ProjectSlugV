#ifndef MS5_PALETTE_UPLOAD_H
#define MS5_PALETTE_UPLOAD_H

#include <cstddef>
#include <cstdint>
#include <string>

namespace ms5 {

// Memory effects of the transfer kernel at 68000 CPU addresses
// 0x007320..0x00871a, not the surrounding routine or ROM file offsets.
// Both caller-owned buffers must contain at least 8192 bytes and their
// first 8192-byte regions must be disjoint. Extra bytes are preserved.
// For each of 256 32-byte blocks, clear bit 7 of its first staging byte;
// copy the cleared block to palette only if that bit was previously set.
// Null pointers or insufficient sizes return false without buffer writes.
// Registers, condition flags, and hardware side effects are not modeled.
bool upload_dirty_palette_blocks(std::uint8_t* staging,
                                 std::size_t staging_size,
                                 std::uint8_t* palette,
                                 std::size_t palette_size,
                                 std::string& error);

} // namespace ms5

#endif
