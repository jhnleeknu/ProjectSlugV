#ifndef MS5_MENU_INIT_H
#define MS5_MENU_INIT_H

#include "ms5/fixed_data_resource.h"

namespace ms5 {

// Confirmed CPU 0x00a110..0x00a1d0 slot initialization. slot_address is
// a CPU work-RAM address from 0x107e0e through 0x107efe in steps of 16.
// Writes only that slot, preserving its byte at +5 and all menu globals.
// RAM must contain exactly 65536 bytes. Failure preserves RAM; success
// clears error. Title streams must be wholly available in the resource.
bool configure_menu_slot(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& resource,
                         std::uint32_t slot_address,
                         std::uint32_t descriptor_address,
                         std::uint16_t x, std::uint16_t y,
                         std::uint16_t initial_line, std::string& error);

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
