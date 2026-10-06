#ifndef MS5_ANIMATION_STEP_H
#define MS5_ANIMATION_STEP_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Execute the verified 00/04/08/28 animation subset. RAM maps CPU 0x100000
// and contains exactly 65536 bytes; object_offset leaves 0x62 bytes.
// Script bytes map script_base in the 24-bit CPU address space. Instruction
// fetches use only this script, never RAM. An inactive pointer accepts an
// empty script. Unsupported instructions, invalid fetches, producer waits
// and the 10000-instruction limit preserve both RAM and carry on failure.
bool step_animation(std::vector<std::uint8_t>& ram,
                    std::size_t object_offset,
                    const std::vector<std::uint8_t>& script,
                    std::uint32_t script_base,
                    bool& carry, std::string& error);

} // namespace ms5

#endif
