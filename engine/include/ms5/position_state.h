#ifndef MS5_POSITION_STATE_H
#define MS5_POSITION_STATE_H

#include <cstddef>
#include <cstdint>
#include <string>

namespace ms5 {

// RAM memory effects of CPU routines 0x043e38 and (advance=true) 0x043ea8.
// ram maps 64 KiB starting at CPU address 0x100000. The entry A0 value is
// coordinate_address. Coordinates and any nonzero parent pointer must be
// even addresses with a complete 0x26-byte structure inside that RAM.
// This contract covers valid coordinate structures, not arbitrary CPU maps.
// Registers, CPU condition flags, and stack effects are outside the contract.
// Invalid input returns false with an error and leaves RAM unchanged.
bool update_position(std::uint8_t* ram, std::size_t size,
                     std::uint32_t coordinate_address, bool advance,
                     std::string& error);

} // namespace ms5

#endif
