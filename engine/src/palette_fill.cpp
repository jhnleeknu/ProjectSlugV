#include "ms5/palette_fill.h"

#include <cstddef>

namespace {

void write_be16(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

} // namespace

namespace ms5 {

bool setup_palette_fill(std::vector<std::uint8_t>& ram,
                        const std::vector<PaletteRecord>& fill_catalog,
                        std::uint16_t selector,
                        std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    if (fill_catalog.size() != 2048) {
        error = "fill catalog must contain exactly 2048 records";
        return false;
    }
    for (std::size_t index = 0; index < fill_catalog.size(); ++index) {
        if (fill_catalog[index].id != index) {
            error = "fill catalog IDs must be canonical 0..2047 in ascending order";
            return false;
        }
    }
    const std::size_t selected = selector & 0x7ffU;
    for (std::size_t word = 1; word < 16; ++word) {
        write_be16(ram, 0x7da2 + word * 2,
                   fill_catalog[selected].hardware_words[word]);
    }
    write_be16(ram, 0x7dea, 0x2000);
    write_be16(ram, 0x10, 0);
    error.clear();
    return true;
}

} // namespace ms5
