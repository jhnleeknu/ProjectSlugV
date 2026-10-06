#include "ms5/position_state.h"

namespace {

const std::uint32_t ram_base = 0x100000U;
const std::size_t ram_size = 0x10000;

bool valid_coordinate_address(std::uint32_t address) {
    return address >= ram_base && address <= 0x110000U - 0x26U &&
           (address & 1U) == 0;
}

std::uint32_t read_be_long(const std::uint8_t* ram, std::size_t offset) {
    return (static_cast<std::uint32_t>(ram[offset]) << 24) |
           (static_cast<std::uint32_t>(ram[offset + 1]) << 16) |
           (static_cast<std::uint32_t>(ram[offset + 2]) << 8) |
           static_cast<std::uint32_t>(ram[offset + 3]);
}

void write_be_long(std::uint8_t* ram, std::size_t offset,
                   std::uint32_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 24);
    ram[offset + 1] = static_cast<std::uint8_t>(value >> 16);
    ram[offset + 2] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 3] = static_cast<std::uint8_t>(value);
}

} // namespace

namespace ms5 {

bool update_position(std::uint8_t* ram, std::size_t size,
                     std::uint32_t coordinate_address, bool advance,
                     std::string& error) {
    error.clear();
    if (ram == NULL || size < ram_size) {
        error = "RAM must contain at least 65536 bytes";
        return false;
    }
    if (!valid_coordinate_address(coordinate_address)) {
        error = "coordinate address must be even and contain 0x26 bytes in RAM";
        return false;
    }
    const std::size_t offset = coordinate_address - ram_base;
    const std::uint32_t parent_address = read_be_long(ram, offset + 0x10);
    if (parent_address != 0 && !valid_coordinate_address(parent_address)) {
        error = "parent address must be zero or an even coordinate address in RAM";
        return false;
    }

    // All validation precedes the first write, including the advance entry.
    if (advance) {
        write_be_long(ram, offset,
                      read_be_long(ram, offset) + read_be_long(ram, offset + 8));
        write_be_long(ram, offset + 4,
                      read_be_long(ram, offset + 4) +
                      read_be_long(ram, offset + 0x0c));
    }
    const std::uint32_t old_world_x = read_be_long(ram, offset + 0x14);
    const std::uint32_t old_world_y = read_be_long(ram, offset + 0x18);
    std::uint32_t world_x = read_be_long(ram, offset);
    std::uint32_t world_y = read_be_long(ram, offset + 4);
    std::uint8_t flags = 0;
    if (parent_address != 0) {
        const std::size_t parent_offset = parent_address - ram_base;
        const std::uint32_t parent_x = read_be_long(ram, parent_offset + 0x14);
        const std::uint32_t parent_y = read_be_long(ram, parent_offset + 0x18);
        const std::uint32_t carry_x =
            ((world_x & 0xffffU) + (parent_x & 0xffffU)) > 0xffffU ? 1U : 0U;
        const std::uint32_t carry_y =
            ((world_y & 0xffffU) + (parent_y & 0xffffU)) > 0xffffU ? 1U : 0U;
        world_x += parent_x;
        world_y += parent_y;
        flags = static_cast<std::uint8_t>((2U * carry_y + carry_x) |
                                         ram[parent_offset + 0x25]);
    }
    ram[offset + 0x25] = flags;
    write_be_long(ram, offset + 0x14, world_x);
    write_be_long(ram, offset + 0x18, world_y);

    // Read the global byte after the world writes: structures may overlap it.
    const std::uint8_t current_stamp = ram[0xd494];
    const std::uint8_t old_stamp = ram[offset + 0x24];
    if (old_stamp == 0) {
        ram[offset + 0x24] = current_stamp;
        write_be_long(ram, offset + 0x1c, world_x);
        write_be_long(ram, offset + 0x20, world_y);
    } else if (old_stamp != current_stamp) {
        ram[offset + 0x24] = current_stamp;
        write_be_long(ram, offset + 0x1c, old_world_x);
        write_be_long(ram, offset + 0x20, old_world_y);
    }
    return true;
}

} // namespace ms5
