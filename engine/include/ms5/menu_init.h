#ifndef MS5_MENU_INIT_H
#define MS5_MENU_INIT_H

#include "ms5/fixed_data_resource.h"

namespace ms5 {

// Confirmed CPU 0x00a29c reset and first menu allocation. This does not
// implement nested menu allocation. RAM is one 65536-byte work-RAM image;
// title streams must be wholly available in the supplied fixed-ROM window.
// Failure preserves RAM; success clears error. The previous current-menu
// pointer at RAM offset 0x7f12 and slot byte 0x7f03 remain unchanged.
bool initialize_menu(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& resource,
                     std::uint32_t descriptor_address,
                     std::uint16_t x, std::uint16_t y,
                     std::uint16_t initial_line, std::string& error);

} // namespace ms5

#endif
