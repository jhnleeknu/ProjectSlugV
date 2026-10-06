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

} // namespace

int main() {
    const std::size_t addresses[] = {
        0x914e, 0x914e, 0x8d38, 0x8d38, 0x8f50, 0x8f50, 0x8f50
    };
    const std::uint16_t values[] = {1, 514, 1, 512, 13, 3072, 12};
    for (std::size_t index = 0; index < 7; ++index) {
        std::vector<std::uint8_t> ram(65536, 0x5a);
        put(ram, 0x914e, 4);
        put(ram, 0x8d38, 0);
        put(ram, 0x8f4e, 12);
        put(ram, 0x8f50, 24);
        put(ram, addresses[index], values[index]);
        const std::vector<std::uint8_t> original = ram;
        std::string error;
        require(!ms5::sort_deferred_sprites(ram, 1234, error),
                "invalid queue rejected");
        require(!error.empty() && ram == original,
                "invalid queue preserves every RAM byte");
    }
    const std::size_t sizes[] = {0, 65535, 65537};
    for (std::size_t index = 0; index < 3; ++index) {
        std::vector<std::uint8_t> ram(sizes[index], 0x5a);
        const std::vector<std::uint8_t> original = ram;
        std::string error;
        require(!ms5::sort_deferred_sprites(ram, 1234, error),
                "wrong RAM size rejected");
        require(!error.empty() && ram == original,
                "wrong RAM size preserves every byte");
    }
    std::vector<std::uint8_t> empty(65536, 0x5a);
    put(empty, 0x914e, 0);
    put(empty, 0x8d38, 510);
    std::vector<std::uint8_t> expected = empty;
    put(expected, 0x9150, 0xffff);
    std::string error("stale");
    require(ms5::sort_deferred_sprites(empty, 0xffff, error), "empty sort");
    require(error.empty() && empty == expected, "empty sort changes only tag");

    // Full storage capacity, offset zero, unsigned keys, and output-ring wrap.
    // This synthetic 256-record input is outside the proven producer cases.
    std::vector<std::uint8_t> full(65536, 0x5a);
    put(full, 0x914e, 512);
    put(full, 0x8d38, 510);
    put(full, 0x9150, 0xffff);
    for (std::size_t index = 0; index < 256; ++index) {
        put(full, 0x8f4e + index * 2,
            static_cast<std::uint16_t>(index * 12));
        put(full, 0x7f34 + index * 12,
            static_cast<std::uint16_t>(index * 257));
    }
    const std::vector<std::uint8_t> original = full;
    require(ms5::sort_deferred_sprites(full, 0, error), "full table accepted");
    require(error.empty() && word(full, 0x9150) == 0 &&
            word(full, 0x914e) == 0 && word(full, 0x8d38) == 510,
            "full table updates tag and wraps end");
    for (std::size_t index = 0; index < 256; ++index) {
        require(word(full, 0x8b34 + ((510 + index * 2) & 510)) == index * 12,
                "full table output uses unsigned ascending keys");
        require(word(full, 0x7f34 + index * 12) == 0xffff,
                "full table keys replaced with previous tag");
    }
    for (std::size_t at = 0; at < full.size(); ++at) {
        const bool record_key = at >= 0x7f34 && at < 0x8b34 &&
            (at - 0x7f34) % 12 < 2;
        const bool ring = at >= 0x8b34 && at < 0x8d34;
        const bool end = at >= 0x8d38 && at < 0x8d3a;
        const bool deferred = at >= 0x8f4e && at < 0x9152;
        if (!record_key && !ring && !end && !deferred) {
            require(full[at] == original[at], "sort preserves unrelated RAM");
        }
    }
    std::cout << "Sprite queue validation and storage boundary tests passed\n";
    return 0;
}
