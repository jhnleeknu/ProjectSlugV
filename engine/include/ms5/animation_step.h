#ifndef MS5_ANIMATION_STEP_H
#define MS5_ANIMATION_STEP_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "ms5/fixed_data_resource.h"

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

// Adds field branch 0c, indexed draw 10 and callback 14 selectors 1d/1e.
// Callback 1d indexes with object+7c, while 1e indexes with object+7d;
// both read a big-endian longword at operand_base+index*4 into object+78.
// Data windows must be
// nonempty, nonoverlapping fixed-ROM ranges with matching CPU/ROM addresses.
// Each data read must fit a supplied window. All failures preserve RAM/carry.
// Inactive pointers retain the legacy behavior without validating windows.
bool step_animation_with_data(std::vector<std::uint8_t>& ram,
                              std::size_t object_offset,
                              const std::vector<std::uint8_t>& script,
                              std::uint32_t script_base,
                              const std::vector<FixedDataResource>& regions,
                              bool& carry, std::string& error);

} // namespace ms5

#endif
