#include "ms5/sprite_queue.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

void put(std::vector<std::uint8_t>& ram, std::size_t at,
         std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}

std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[at]) << 8) | ram[at + 1]);
}

void reject(std::vector<std::uint8_t>& ram) {
    const std::vector<std::uint8_t> original = ram;
    std::string error;
    require(!ms5::radix_sort_sprite_queue(ram, error), "invalid input rejected");
    require(!error.empty() && ram == original, "invalid input preserves all RAM");
}

// Independent insertion ordering oracle for stable full-key and low-byte sorts.
std::vector<std::uint16_t> ordered(const std::vector<std::uint8_t>& ram,
                                  const std::vector<std::uint16_t>& offsets,
                                  bool low_only) {
    std::vector<std::uint16_t> result;
    for (std::size_t index = 0; index < offsets.size(); ++index) {
        const std::uint16_t offset = offsets[index];
        const std::uint16_t key = low_only ? ram[0x7f35 + offset] :
            word(ram, 0x7f34 + offset);
        std::size_t position = result.size();
        result.push_back(offset);
        while (position != 0) {
            const std::uint16_t previous = result[position - 1];
            const std::uint16_t previous_key = low_only ? ram[0x7f35 + previous] :
                word(ram, 0x7f34 + previous);
            if (previous_key <= key) {
                break;
            }
            result[position] = previous;
            --position;
        }
        result[position] = offset;
    }
    return result;
}

void verify(std::vector<std::uint8_t> ram,
            const std::vector<std::uint16_t>& offsets, std::uint16_t start) {
    put(ram, 0x8d36, start);
    put(ram, 0x8d3a, static_cast<std::uint16_t>((start + offsets.size() * 2) & 510));
    for (std::size_t index = 0; index < offsets.size(); ++index) {
        put(ram, 0x8b34 + ((start + index * 2) & 510), offsets[index]);
    }
    const std::vector<std::uint8_t> original = ram;
    std::vector<std::uint8_t> expected = ram;
    const std::vector<std::uint16_t> sorted = ordered(ram, offsets, false);
    const std::vector<std::uint16_t> low_sorted = ordered(ram, offsets, true);
    for (std::size_t index = 0; index < offsets.size(); ++index) {
        put(expected, 0x8b34 + ((start + index * 2) & 510), sorted[index]);
        put(expected, 0x8f4e + index * 2, low_sorted[index]);
    }
    // After placement, each byte histogram contains the number of entries
    // whose corresponding key byte is strictly smaller than this bucket.
    for (unsigned int bucket = 0; bucket < 256; ++bucket) {
        unsigned int high_less = 0;
        unsigned int low_less = 0;
        for (std::size_t index = 0; index < offsets.size(); ++index) {
            high_less += original[0x7f34 + offsets[index]] < bucket ? 1U : 0U;
            low_less += original[0x7f35 + offsets[index]] < bucket ? 1U : 0U;
        }
        expected[0x8d4e + bucket * 2] = static_cast<std::uint8_t>(high_less);
        expected[0x8d4f + bucket * 2] = static_cast<std::uint8_t>(low_less);
    }
    std::string error("stale");
    require(ms5::radix_sort_sprite_queue(ram, error), "valid ring accepted");
    require(error.empty(), "success clears error");
    require(ram == expected, "stable ordering, exact scratch, unrelated RAM preservation");
}

} // namespace

int main() {
    const std::size_t sizes[] = {0, 65535, 65537};
    for (std::size_t index = 0; index < 3; ++index) {
        std::vector<std::uint8_t> ram(sizes[index], 0x5a);
        reject(ram);
    }
    const std::size_t addresses[] = {0x8d36, 0x8d36, 0x8d3a, 0x8d3a,
                                    0x8b34, 0x8b34};
    const std::uint16_t values[] = {1, 512, 1, 512, 13, 3072};
    for (std::size_t index = 0; index < 6; ++index) {
        std::vector<std::uint8_t> ram(65536, 0x5a);
        put(ram, 0x8d36, 510);
        put(ram, 0x8d3a, 2);
        put(ram, 0x8d32, 0);
        put(ram, 0x8b34, 12);
        put(ram, addresses[index], values[index]);
        reject(ram);
    }
    // Empty cursors bypass even invalid inactive entries and leave scratch.
    for (unsigned int start = 0; start <= 510; start += 510) {
        std::vector<std::uint8_t> ram(65536, 0x5a);
        put(ram, 0x8d36, static_cast<std::uint16_t>(start));
        put(ram, 0x8d3a, static_cast<std::uint16_t>(start));
        const std::vector<std::uint8_t> original = ram;
        std::string error("stale");
        require(ms5::radix_sort_sprite_queue(ram, error), "empty accepted");
        require(error.empty() && ram == original, "empty preserves every byte");
    }
    std::vector<std::uint8_t> ram(65536, 0x5a);
    const std::uint16_t keys[] = {0xffff, 0x8001, 0x8001, 0x0001,
                                  0x8000, 0x0001};
    for (std::size_t index = 0; index < 6; ++index) {
        put(ram, 0x7f34 + index * 12, keys[index]);
    }
    const std::uint16_t inputs[] = {24, 0, 12, 24, 36, 48, 60};
    const std::vector<std::uint16_t> offsets(inputs, inputs + 7);
    verify(ram, offsets, 510);
    std::vector<std::uint16_t> full;
    for (unsigned int index = 0; index < 255; ++index) {
        full.push_back(static_cast<std::uint16_t>((254 - index) * 12));
        put(ram, 0x7f34 + index * 12,
            static_cast<std::uint16_t>((index * 12345U) & 65535U));
    }
    verify(ram, full, 510);
    // Maximum offset and all 255 entries in one bucket exercise byte limits.
    full.assign(255, 3060);
    put(ram, 0x7f34 + 3060, 0xffff);
    verify(ram, full, 0);
    std::cout << "Sprite radix validation, stability, scratch and boundary tests passed\n";
    return 0;
}
