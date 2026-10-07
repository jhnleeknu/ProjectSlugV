#ifndef MS5_PALETTE_ALLOCATOR_H
#define MS5_PALETTE_ALLOCATOR_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// RAM effects of CPU 0x008ebe (acquire) and 0x008ff4 (release).
// ram is exactly 65536 bytes beginning at CPU 0x100000; object is a RAM
// offset with at least 0x1e bytes available. Failures preserve all RAM bytes and allocated.
// Exhaustion succeeds with allocated=false unless the debug UI flag is set.
// Unsupported debug UI and the original count-four TRAP return errors.
bool acquire_palette(std::vector<std::uint8_t>& ram, std::size_t object,
                     std::uint16_t id, std::uint8_t flags,
                     bool& allocated, std::string& error);
// Release optionally returns D3: each node moved to the free ring replaces
// its low word with the old free tail; otherwise it is preserved. Errors
// preserve RAM and D3 together.
bool release_palettes(std::vector<std::uint8_t>& ram, std::size_t object,
                      std::string& error, std::uint32_t* d3 = NULL);

} // namespace ms5

#endif
