#include "ms5/palette_state.h"

namespace {

void write_be16(std::uint8_t* bytes, std::uint16_t value) {
    bytes[0] = static_cast<std::uint8_t>(value >> 8);
    bytes[1] = static_cast<std::uint8_t>(value);
}

} // namespace

namespace ms5 {

bool initialize_palette_state(std::uint8_t* ram, std::size_t size,
                              std::string& error) {
    if (ram == NULL || size < 65536) {
        error = "RAM must contain at least 65536 bytes at CPU 0x100000";
        return false;
    }
    const std::size_t node_base = 0x4d92;
    for (std::size_t i = 0; i < 256; ++i) {
        std::uint8_t* node = ram + node_base + i * 16;
        write_be16(node, static_cast<std::uint16_t>(
            i == 0 ? 0x1000 : (i - 1) * 16));
        write_be16(node + 2, static_cast<std::uint16_t>(
            i == 255 ? 0x1000 : (i + 1) * 16));
        const std::uint16_t data_offset =
            static_cast<std::uint16_t>(i * 16 + 4);
        write_be16(node + 4, data_offset);
        write_be16(node + 6, data_offset);
        write_be16(node + 8, 0);
        write_be16(node + 0xa, 0xffff);
        write_be16(node + 0xc, 0xffff);
        node[0xe] = 0;
        node[0xf] = 2;
    }
    write_be16(ram + node_base + 0x1000, 0xff0);
    write_be16(ram + node_base + 0x1002, 0);
    for (std::size_t i = 0; i < 256; ++i) {
        write_be16(ram + 0x5da2 + i * 32, 0);
    }
    for (std::size_t offset = 0x7dc2; offset <= 0x7dcc; offset += 2) {
        write_be16(ram + offset, 0);
    }
    ram[0x7dd4] = 0;
    write_be16(ram + 0x7dea, 0);
    ram[0x7dec] = 0;
    ram[0x7ded] = 0;
    error.clear();
    return true;
}

} // namespace ms5
