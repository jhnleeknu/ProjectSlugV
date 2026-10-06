#ifndef MS5_MENU_MOTION_H
#define MS5_MENU_MOTION_H

#include "ms5/menu_border.h"

namespace ms5 {

// One confirmed CPU 0x00a348 opening step or 0x00a2be closing step.
// These do not implement the full CPU 0x00a370 menu dispatcher.
// RAM is exactly 65536 bytes; writes contain VRAM word address/value pairs.
// Success replaces RAM and writes and clears error. Failure preserves both.
bool open_menu_step(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource,
                    std::vector<FixedWrite>& writes, std::string& error);
bool close_menu_step(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::vector<FixedWrite>& writes, std::string& error);

} // namespace ms5

#endif
