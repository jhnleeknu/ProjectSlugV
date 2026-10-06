#ifndef MS5_PALETTE_STATE_H
#define MS5_PALETTE_STATE_H

#include <cstddef>
#include <cstdint>
#include <string>

namespace ms5 {

// RAM effects of the original palette initialization at CPU 0x003ef2..0x003f96.
// ram begins at CPU 0x100000; offsets are RAM offsets, not ROM file offsets.
// Requires at least 65536 bytes. Invalid input returns false without writes.
// Success preserves bytes outside the original writes. Register, flag and
// call-stack effects are outside this function's contract.
bool initialize_palette_state(std::uint8_t* ram, std::size_t size,
                              std::string& error);

} // namespace ms5

#endif
