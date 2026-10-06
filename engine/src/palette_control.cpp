#include "ms5/palette_control.h"

#include <cstddef>

namespace {

std::uint16_t read_be16(const std::vector<std::uint8_t>& ram,
                        std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[offset]) << 8) | ram[offset + 1]);
}

void write_be16(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

std::int32_t signed_word(std::uint16_t value) {
    return value < 0x8000U ? static_cast<std::int32_t>(value) :
        static_cast<std::int32_t>(value) - 65536;
}

std::uint16_t effect_target(std::uint16_t value) {
    std::int32_t channel = signed_word(value);
    if (channel < -31) {
        channel = -31;
    } else if (channel > 31) {
        channel = 31;
    }
    // Multiplication avoids shifting a negative signed value. Conversion
    // to unsigned reproduces the original 16-bit word modulo 65536.
    return static_cast<std::uint16_t>(channel * 256);
}

} // namespace

namespace ms5 {

bool set_palette_effect(std::vector<std::uint8_t>& ram,
                        std::uint16_t red, std::uint16_t green,
                        std::uint16_t blue, std::uint8_t duration,
                        std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    const std::uint16_t targets[3] = {
        effect_target(red), effect_target(green), effect_target(blue)
    };
    std::int32_t deltas[3];
    bool changed = false;
    for (std::size_t channel = 0; channel < 3; ++channel) {
        const std::uint16_t current = read_be16(ram, 0x7dc2 + channel * 2);
        const std::uint16_t delta = static_cast<std::uint16_t>(
            static_cast<std::uint32_t>(targets[channel]) + 65536U - current);
        deltas[channel] = signed_word(delta);
        changed = changed || deltas[channel] != 0;
        write_be16(ram, 0x7dc8 + channel * 2, targets[channel]);
    }
    const std::uint8_t ticks = duration == 0 ? 1 : duration;
    ram[0x7dd4] = changed ? ticks : 0;
    if (changed) {
        for (std::size_t channel = 0; channel < 3; ++channel) {
            const std::int32_t step = deltas[channel] / ticks;
            write_be16(ram, 0x7dce + channel * 2,
                       static_cast<std::uint16_t>(step));
        }
    }
    error.clear();
    return true;
}

bool set_palette_blend(std::vector<std::uint8_t>& ram,
                       std::uint8_t slot, std::uint16_t target,
                       std::uint8_t weight, std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    const std::size_t node = 0x4d92 + static_cast<std::size_t>(slot) * 16;
    if (read_be16(ram, node + 8) != 0) {
        const std::uint8_t capped_weight = weight > 32 ? 32 : weight;
        if (target != read_be16(ram, node + 0xc)) {
            write_be16(ram, node + 0xc, target);
            ram[node + 0xe] = capped_weight;
            ram[node + 0xf] = static_cast<std::uint8_t>(ram[node + 0xf] | 0x80U);
        } else if (capped_weight != ram[node + 0xe]) {
            ram[node + 0xe] = capped_weight;
            if (target != read_be16(ram, node + 0xa)) {
                ram[node + 0xf] = static_cast<std::uint8_t>(
                    ram[node + 0xf] | 0x80U);
            }
        }
    }
    error.clear();
    return true;
}

} // namespace ms5
