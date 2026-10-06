#ifndef MS5_MENU_BORDER_H
#define MS5_MENU_BORDER_H

#include "ms5/fixed_data_resource.h"
#include "ms5/fixed_text.h"

namespace ms5 {

// Trace the confirmed CPU 0x009b58 border/clear routine and 0x00a018
// occlusion helper. RAM is a 65536-byte snapshot of CPU 0x100000..0x10ffff.
// Write addresses are VRAM word addresses. No RAM bytes are modified.
// Success replaces writes and clears error; failure preserves writes.
bool trace_menu_border(const std::vector<std::uint8_t>& ram,
                       const FixedDataResource& resource,
                       std::vector<FixedWrite>& writes, std::string& error);

// Query the confirmed CPU 0x00a018 helper using the same RAM/slot
// constraints as trace_menu_border. Failure preserves covered.
bool menu_position_occluded(const std::vector<std::uint8_t>& ram,
                            std::uint16_t address, bool& covered,
                            std::string& error);

} // namespace ms5

#endif
