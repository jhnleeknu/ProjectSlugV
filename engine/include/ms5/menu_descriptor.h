#ifndef MS5_MENU_DESCRIPTOR_H
#define MS5_MENU_DESCRIPTOR_H

#include "ms5/fixed_data_resource.h"

namespace ms5 {

struct MenuItem {
    std::uint32_t source_cpu_address;
    std::uint32_t title_address;
    std::uint32_t callback;
    std::uint16_t argument;

    MenuItem() : source_cpu_address(0), title_address(0), callback(0), argument(0) {}
};

struct MenuDescriptor {
    std::uint32_t source_cpu_address;
    std::uint32_t title_address;
    std::uint8_t min_width;
    std::uint8_t min_height;
    std::uint32_t callback6;
    std::uint32_t callback10;
    std::uint16_t flags;
    std::vector<MenuItem> items;
    std::uint32_t consumed_bytes;
    std::uint32_t end_cpu_address;

    MenuDescriptor() : source_cpu_address(0), title_address(0), min_width(0),
        min_height(0), callback6(0), callback10(0), flags(0), consumed_bytes(0),
        end_cpu_address(0) {}
};

// Decode a big-endian fixed-ROM descriptor. The end address is exclusive and
// includes the four-byte terminator. Pointer targets are preserved, not followed.
// Failure preserves descriptor; success clears error.
bool decode_menu_descriptor(const FixedDataResource& resource,
                            std::uint32_t address, MenuDescriptor& descriptor,
                            std::string& error);

} // namespace ms5

#endif
