#include "ms5/palette_frame.h"
#include "ms5/palette_prepare.h"

#include <cstddef>
#include <new>

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

} // namespace

namespace ms5 {

bool step_palette_frame(std::vector<std::uint8_t>& ram,
                        const std::vector<PaletteRecord>& records,
                        std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    std::vector<std::uint8_t> candidate;
    try {
        candidate = ram;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate palette frame RAM";
        return false;
    }
    if (candidate[0x7dd4] != 0) {
        const std::uint8_t previous[3] = {
            candidate[0x7dc2], candidate[0x7dc4], candidate[0x7dc6]
        };
        candidate[0x7dd4] = static_cast<std::uint8_t>(
            candidate[0x7dd4] - 1U);
        bool changed = false;
        for (std::size_t channel = 0; channel < 3; ++channel) {
            const std::size_t current = 0x7dc2 + channel * 2;
            const std::uint16_t value = candidate[0x7dd4] == 0 ?
                read_be16(candidate, 0x7dc8 + channel * 2) :
                static_cast<std::uint16_t>(
                    static_cast<std::uint32_t>(read_be16(candidate, current)) +
                    read_be16(candidate, 0x7dce + channel * 2));
            write_be16(candidate, current, value);
            if (candidate[current] != previous[channel]) {
                changed = true;
            }
        }
        if (changed) {
            for (std::size_t slot = 0; slot < 256; ++slot) {
                const std::size_t flags = 0x4d92 + slot * 16 + 15;
                if ((candidate[flags] & 2U) == 0) {
                    candidate[flags] = static_cast<std::uint8_t>(
                        candidate[flags] | 0x80U);
                }
            }
        }
    }
    if ((candidate[0x7ded] & 0x80U) == 0 &&
        !prepare_palettes(candidate, records, error)) {
        return false;
    }
    ram.swap(candidate);
    error.clear();
    return true;
}

} // namespace ms5
