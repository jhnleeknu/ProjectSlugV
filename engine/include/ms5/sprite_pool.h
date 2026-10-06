#ifndef MS5_SPRITE_POOL_H
#define MS5_SPRITE_POOL_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// RAM effects of CPU 0x00cd1c. RAM maps CPU 0x100000 and must have
// exactly 65536 bytes. Selector zero chooses 0x8d3e; any other value
// chooses 0x8d46. Unsigned lower >= 380 becomes 0xffff, then unsigned
// lower >= upper makes upper 0xffff. Store lower, upper, lower, upper
// as four BE words, preserving all other RAM. Mixed sentinel states are
// preserved exactly even if subsequent queue dispatch cannot accept them.
// Invalid RAM size preserves RAM; success clears error.
bool configure_sprite_pool(std::vector<std::uint8_t>& ram,
                           std::uint16_t selector, std::uint16_t lower,
                           std::uint16_t upper, std::string& error);

} // namespace ms5

#endif
