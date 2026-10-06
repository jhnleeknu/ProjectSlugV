#include "ms5/sprite_queue.h"

#include <cstddef>

namespace {

std::uint16_t read_word(const std::vector<std::uint8_t>& ram,
                        std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[offset]) << 8) | ram[offset + 1]);
}

void write_word(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

} // namespace

namespace ms5 {

bool sort_deferred_sprites(std::vector<std::uint8_t>& ram,
                           std::uint16_t new_tag, std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    const std::uint16_t count = read_word(ram, 0x914e);
    if ((count & 1U) != 0 || count > 512) {
        error = "deferred byte count must be even and at most 512";
        return false;
    }
    std::uint16_t end = read_word(ram, 0x8d38);
    if ((end & 1U) != 0 || end > 510) {
        error = "output ring end must be even and at most 510";
        return false;
    }
    bool seen[256] = {};
    for (std::size_t index = 0; index < count; index += 2) {
        const std::uint16_t offset = read_word(ram, 0x8f4e + index);
        if (offset > 3060 || offset % 12 != 0) {
            error = "deferred offset must identify one of 256 12-byte records";
            return false;
        }
        if (seen[offset / 12]) {
            error = "deferred offsets must be unique";
            return false;
        }
        seen[offset / 12] = true;
    }

    const std::uint16_t previous = read_word(ram, 0x9150);
    write_word(ram, 0x9150, new_tag);
    std::uint16_t remaining = count;
    while (remaining != 0) {
        std::size_t at = 0x8f4e + remaining - 2;
        std::uint16_t chosen = read_word(ram, at);
        std::uint16_t key = read_word(ram, 0x7f34 + chosen);
        while (at != 0x8f4e) {
            at -= 2;
            const std::uint16_t other = read_word(ram, at);
            const std::uint16_t other_key = read_word(ram, 0x7f34 + other);
            // Equality takes the same swap branch as the original CPU code.
            if (key >= other_key) {
                key = other_key;
                write_word(ram, at, chosen);
                chosen = other;
            }
        }
        write_word(ram, 0x7f34 + chosen, previous);
        write_word(ram, 0x8b34 + end, chosen);
        end = static_cast<std::uint16_t>((end + 2U) & 0x1feU);
        remaining = static_cast<std::uint16_t>(remaining - 2U);
    }
    if (count != 0) {
        write_word(ram, 0x8d38, end);
        write_word(ram, 0x914e, 0);
    }
    error.clear();
    return true;
}

bool radix_sort_sprite_queue(std::vector<std::uint8_t>& ram,
                             std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    const std::uint16_t start = read_word(ram, 0x8d36);
    const std::uint16_t end = read_word(ram, 0x8d3a);
    if ((start & 1U) != 0 || start > 510 ||
        (end & 1U) != 0 || end > 510) {
        error = "display ring cursors must be even and at most 510";
        return false;
    }
    std::uint16_t cursor = start;
    while (cursor != end) {
        const std::uint16_t offset = read_word(ram, 0x8b34 + cursor);
        if (offset > 3060 || offset % 12 != 0) {
            error = "display offset must identify one of 256 12-byte records";
            return false;
        }
        cursor = static_cast<std::uint16_t>((cursor + 2U) & 510U);
    }
    error.clear();
    if (start == end) {
        return true;
    }

    for (std::size_t at = 0x8d4e; at < 0x8f4e; ++at) {
        ram[at] = 0;
    }
    cursor = start;
    while (cursor != end) {
        const std::size_t record = 0x7f34 + read_word(ram, 0x8b34 + cursor);
        const std::size_t high_at = 0x8d4e + ram[record] * 2U;
        const std::size_t low_at = 0x8d4f + ram[record + 1] * 2U;
        ram[high_at] = static_cast<std::uint8_t>(ram[high_at] + 1U);
        ram[low_at] = static_cast<std::uint8_t>(ram[low_at] + 1U);
        cursor = static_cast<std::uint16_t>((cursor + 2U) & 510U);
    }
    // The original adds packed BE histogram words, with 16-bit wrapping.
    std::uint16_t total = read_word(ram, 0x8d4e);
    for (std::size_t index = 1; index < 256; ++index) {
        total = static_cast<std::uint16_t>(
            total + read_word(ram, 0x8d4e + index * 2));
        write_word(ram, 0x8d4e + index * 2, total);
    }
    const std::size_t count = total & 255U;
    cursor = end;
    for (std::size_t index = 0; index < count; ++index) {
        cursor = static_cast<std::uint16_t>((cursor + 510U) & 510U);
        const std::uint16_t offset = read_word(ram, 0x8b34 + cursor);
        const std::size_t at = 0x8d4f + ram[0x7f35 + offset] * 2U;
        ram[at] = static_cast<std::uint8_t>(ram[at] + 255U);
        write_word(ram, 0x8f4e + ram[at] * 2U, offset);
    }
    for (std::size_t remaining = count; remaining != 0; --remaining) {
        const std::uint16_t offset = read_word(ram, 0x8f4e + (remaining - 1) * 2);
        const std::size_t at = 0x8d4e + ram[0x7f34 + offset] * 2U;
        ram[at] = static_cast<std::uint8_t>(ram[at] + 255U);
        const std::size_t target = (start + ram[at] * 2U) & 510U;
        write_word(ram, 0x8b34 + target, offset);
    }
    return true;
}

} // namespace ms5
