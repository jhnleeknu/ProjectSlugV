#include "ms5/sprite_composition.h"

#include <cstddef>

namespace {

std::uint16_t read_be_word(const std::vector<std::uint8_t>& data,
                           std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint32_t>(data[offset]) << 8) | data[offset + 1]);
}

void append_write(std::vector<ms5::SpriteWrite>& writes,
                  std::uint32_t address, std::uint32_t value) {
    ms5::SpriteWrite write;
    write.address = static_cast<std::uint16_t>(address);
    write.value = static_cast<std::uint16_t>(value);
    writes.push_back(write);
}

} // namespace

namespace ms5 {

bool emit_sprite_rectangle(const std::vector<std::uint8_t>& data,
                           std::uint16_t coordinate_u, std::uint16_t style,
                           std::uint16_t first_slot, std::uint16_t limit,
                           std::vector<SpriteWrite>& writes,
                           std::uint16_t& next_slot, std::string& error) {
    error.clear();
    if (data.size() < 8 || read_be_word(data, 0) != 0x0100U) {
        error = "input must begin with one rectangular block (0x0100)";
        return false;
    }
    const std::uint32_t width = data[6];
    const std::uint32_t height = data[7];
    if (width == 0 || height == 0 || height > 32) {
        error = "rectangle width must be 1..255 and height 1..32";
        return false;
    }
    if (data.size() != 8U + width * height * 4U) {
        error = "input length must match the rectangle dimensions exactly";
        return false;
    }
    if (first_slot > limit || limit > 380) {
        error = "slots must satisfy first_slot <= limit <= 380";
        return false;
    }
    if ((style & 0x00f8U) != 0) {
        error = "style low byte supports only bits 0..2";
        return false;
    }

    std::vector<SpriteWrite> result;
    result.reserve(static_cast<std::size_t>(width * (2U + height * 2U)));
    const std::uint32_t dx = read_be_word(data, 2);
    std::uint16_t slot = first_slot;
    for (std::uint32_t column = 0; column < width; ++column) {
        // In the supported slot range the original signed BPL limit test is
        // equivalent to this comparison, and precedes horizontal clipping.
        if (slot >= limit) {
            break;
        }
        const std::uint32_t xword =
            (dx * 64U + static_cast<std::uint32_t>(coordinate_u) * 64U +
             column * 0x400U) & 0xffffU;
        if (((xword + 0x200U) & 0xffffU) >= 0x5000U) {
            continue;
        }
        append_write(result, 0x8401U + slot, (xword * 2U) & 0xffffU);
        append_write(result, 0x8001U + slot, 0xffffU);
        for (std::uint32_t row = 0; row < height; ++row) {
            const std::size_t offset = 8U + (column * height + row) * 4U;
            const std::uint32_t attribute = read_be_word(data, offset);
            const std::uint32_t address =
                (static_cast<std::uint32_t>(slot) + 1U) * 64U + row * 2U;
            append_write(result, address + 1U,
                         ((attribute + (style & 0xff00U)) & 0xffffU) ^
                         (style & 0x00ffU));
            append_write(result, address, read_be_word(data, offset + 2));
        }
        ++slot;
    }
    writes.swap(result);
    next_slot = slot;
    return true;
}

} // namespace ms5
