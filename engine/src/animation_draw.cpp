#include "ms5/animation_draw.h"

namespace {

std::uint16_t read_be_word(const std::vector<std::uint8_t>& bytes,
                          std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint32_t>(bytes[offset]) << 8) | bytes[offset + 1]);
}

std::uint32_t read_be_long(const std::vector<std::uint8_t>& bytes,
                          std::size_t offset) {
    return (static_cast<std::uint32_t>(bytes[offset]) << 24) |
           (static_cast<std::uint32_t>(bytes[offset + 1]) << 16) |
           (static_cast<std::uint32_t>(bytes[offset + 2]) << 8) |
           static_cast<std::uint32_t>(bytes[offset + 3]);
}

std::int32_t signed_byte(std::uint8_t value) {
    return value < 128 ? static_cast<std::int32_t>(value) :
                        static_cast<std::int32_t>(value) - 256;
}

} // namespace

namespace ms5 {

bool decode_animation_draw(const std::vector<std::uint8_t>& ram,
                           std::size_t object_offset,
                           const std::vector<std::uint8_t>& operand,
                           AnimationDraw& result, std::string& error) {
    error.clear();
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes";
        return false;
    }
    if (object_offset > 65536 - 0x62) {
        error = "object offset must leave 0x62 bytes in RAM";
        return false;
    }
    if (operand.size() != 7) {
        error = "draw operand must contain exactly 7 bytes";
        return false;
    }
    AnimationDraw decoded = {true, 0, 0, 0, 0};
    const std::uint32_t identifier = read_be_long(operand, 3);
    if (identifier == 0x7ff800U || (ram[object_offset + 0x2a] & 128U) != 0 ||
        ((ram[object_offset + 0x61] & 8U) != 0 && (ram[0x0f] & 1U) != 0)) {
        result = decoded;
        return true;
    }

    const std::uint8_t control = operand[0];
    std::uint32_t style = read_be_long(ram, object_offset + 0x12);
    std::int32_t x = signed_byte(operand[1]) * 2 + ((control >> 1) & 1);
    std::int32_t y = signed_byte(operand[2]) * 2 + (control & 1);
    // Relative coordinates use the original style, before control flip bits.
    if ((style & 1U) != 0) {
        x = -x;
    }
    if ((style & 2U) != 0) {
        y = -y;
    }
    const std::uint8_t carry = ram[object_offset + 0x53];
    x += static_cast<std::int32_t>(read_be_word(ram, object_offset + 0x42)) -
         static_cast<std::int32_t>(carry & 1U);
    y += static_cast<std::int32_t>(read_be_word(ram, object_offset + 0x46)) -
         static_cast<std::int32_t>((carry >> 1) & 1U);
    decoded.d0 = (static_cast<std::uint32_t>(static_cast<std::uint16_t>(x)) << 16) |
                 static_cast<std::uint16_t>(y);
    style ^= static_cast<std::uint32_t>((control >> 2) & 3U);
    unsigned int selection = control >> 4;
    if (selection >= 10) {
        selection -= 10;
        style ^= 4U;
    }
    const std::uint16_t palette_word = read_be_word(ram, object_offset + 0x16);
    bool use_special;
    if (selection >= 5) {
        selection -= 5;
        use_special = false;
    } else {
        use_special = (palette_word & 1U) != 0 && (palette_word & 128U) == 0;
    }
    if (use_special) {
        style = (style & 0xffff00ffU) | (palette_word & 0xff00U);
    } else if (selection < 4) {
        style = (style & 0xffff00ffU) |
                (static_cast<std::uint32_t>(ram[object_offset + 0x19 + selection]) << 8);
    }
    decoded.skipped = false;
    decoded.d1 = style;
    decoded.d5 = read_be_word(ram, object_offset + 0x1e);
    decoded.d7 = identifier | read_be_word(ram, object_offset + 0x20);
    result = decoded;
    return true;
}

} // namespace ms5
