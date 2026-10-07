#ifndef MS5_MENU_MOTION_H
#define MS5_MENU_MOTION_H

#include "ms5/menu_border.h"

namespace ms5 {

// One confirmed CPU 0x00a348 opening step or 0x00a2be closing step.
// These do not implement the full CPU 0x00a370 menu dispatcher.
// RAM is exactly 65536 bytes; writes contain VRAM word address/value pairs.
// Success replaces RAM and writes and clears error. Failure preserves both.
// Optional full D1/D3 are transactional. Opening preserves D1; closing
// replaces D1.lowword with the removed row count. Border output supplies D3.
bool open_menu_step(std::vector<std::uint8_t>& ram,
                    const FixedDataResource& resource,
                    std::vector<FixedWrite>& writes, std::string& error,
                    std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);
bool close_menu_step(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::vector<FixedWrite>& writes, std::string& error,
                    std::uint32_t* d1 = NULL, std::uint32_t* d3 = NULL);

} // namespace ms5

#endif
