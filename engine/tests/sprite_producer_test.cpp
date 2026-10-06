#include "ms5/sprite_producer.h"

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

void put(std::vector<std::uint8_t>& ram, std::size_t at, std::uint16_t value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}

std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(ram[at]) << 8) | ram[at + 1]);
}

std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram, at)) << 16) | word(ram, at + 2);
}

std::vector<std::uint8_t> initialized() {
    std::vector<std::uint8_t> ram(65536, 0x5a);
    std::string error;
    require(ms5::initialize_sprite_queue(ram, error), "initialize fixture");
    return ram;
}

void rejected(std::vector<std::uint8_t>& ram, std::uint32_t d0,
              std::uint32_t d1) {
    const std::vector<std::uint8_t> before = ram;
    std::string error;
    ms5::SpriteSubmitStatus status = ms5::SpriteWaiting;
    require(!ms5::submit_sprite(ram, d0, d1, 0, 0, status, error),
            "invalid submission rejected");
    require(!error.empty() && ram == before && status == ms5::SpriteWaiting,
            "invalid submission preserves RAM and status");
}

} // namespace

int main() {
    std::string error("stale");
    std::vector<std::uint8_t> ram(65536, 0x5a);
    std::vector<std::uint8_t> expected = ram;
    expected[0x9152] = 0; expected[0x9153] = 0;
    expected[0x9154] = 0xcd; expected[0x9155] = 0x50;
    expected[0x8d3d] = 0;
    for (std::size_t at = 0x8d34; at < 0x8d3c; ++at) {
        expected[at] = 0;
    }
    for (std::size_t at = 0x914e; at < 0x9152; ++at) {
        expected[at] = 0;
    }
    for (std::size_t index = 0; index < 256; ++index) {
        put(expected, 0x8b34 + index * 2,
            static_cast<std::uint16_t>(index * 12));
    }
    for (std::size_t at = 0x8d3e; at < 0x8d4e; ++at) {
        expected[at] = 0xff;
    }
    require(ms5::initialize_sprite_queue(ram, error) && error.empty() &&
            ram == expected && ram[0x8d3c] == 0x5a,
            "initialization changes exactly documented bytes");

    const std::size_t sizes[] = {0, 65535, 65537};
    for (std::size_t index = 0; index < 3; ++index) {
        std::vector<std::uint8_t> wrong(sizes[index], 0x5a);
        const std::vector<std::uint8_t> before = wrong;
        require(!ms5::initialize_sprite_queue(wrong, error) &&
                !error.empty() && wrong == before, "init size rejection preserves RAM");
        rejected(wrong, 64, 0);
    }
    ram = initialized();
    ram[0x9155] = 0x51;
    rejected(ram, 64, 0);
    rejected(ram, 63, 0); // callback is validated even when clipped.

    // Clipped sprites ignore all malformed queue state and preserve RAM.
    const std::uint32_t clipped[] = {63, 704, 0xfe9f0040U, 0x02a00040U};
    for (std::size_t index = 0; index < 4; ++index) {
        ram = initialized();
        put(ram, 0x8d34, 1); put(ram, 0x8d36, 512);
        put(ram, 0x8d38, 1); put(ram, 0x8d3a, 512);
        put(ram, 0x914e, 65535); put(ram, 0x8b36, 65535);
        const std::vector<std::uint8_t> before = ram;
        ms5::SpriteSubmitStatus status = ms5::SpriteAccepted;
        require(ms5::submit_sprite(ram, clipped[index], 64, 0, 0, status, error) &&
                error.empty() && status == ms5::SpriteClipped && ram == before,
                "clipping bypasses malformed queue");
    }
    const std::size_t cursors[] = {0x8d34, 0x8d36, 0x8d38, 0x8d3a};
    const std::uint16_t invalid[] = {1, 512, 65535};
    for (std::size_t index = 0; index < 4; ++index) {
        for (std::size_t value = 0; value < 3; ++value) {
            ram = initialized(); put(ram, cursors[index], invalid[value]);
            rejected(ram, 64, 0);
        }
    }
    const std::uint16_t bad_offsets[] = {1, 13, 3072, 65535};
    for (std::size_t index = 0; index < 4; ++index) {
        ram = initialized(); put(ram, 0x8b36, bad_offsets[index]);
        rejected(ram, 64, 0);
    }
    const std::uint16_t bad_counts[] = {1, 511, 512, 65535};
    for (std::size_t index = 0; index < 4; ++index) {
        ram = initialized(); put(ram, 0x914e, bad_counts[index]);
        rejected(ram, 64, 64);
    }
    for (unsigned int waiting = 0; waiting < 2; ++waiting) {
        ram = initialized(); put(ram, 0x8d34, 2);
        put(ram, 0x8d36, waiting ? 4 : 2);
        put(ram, 0x8b36, 65535); put(ram, 0x914e, 65535);
        const std::vector<std::uint8_t> before = ram;
        ms5::SpriteSubmitStatus status = ms5::SpriteAccepted;
        require(ms5::submit_sprite(ram, 64, 64, 0, 0, status, error) &&
                error.empty() && ram == before &&
                status == (waiting ? ms5::SpriteWaiting : ms5::SpriteFull),
                "full/wait return before chosen record/deferred validation");
    }
    // Normal append wraps producer and normal cursors and allows offset zero;
    // malformed deferred count is irrelevant to this branch.
    ram = initialized(); put(ram, 0x8d34, 2); put(ram, 0x8d36, 2);
    put(ram, 0x8d38, 510); put(ram, 0x8d3a, 510);
    put(ram, 0x914e, 65535);
    ms5::SpriteSubmitStatus status = ms5::SpriteWaiting;
    require(ms5::submit_sprite(ram, 0xffff02bfU, 0xabcdef07U,
                              0x1234fedcU, 0x00123456U, status, error),
            "normal submission accepted");
    require(error.empty() && status == ms5::SpriteAccepted &&
            word(ram, 0x8d3a) == 0 && word(ram, 0x8d38) == 0 &&
            word(ram, 0x8b34 + 510) == 0 && word(ram, 0x914e) == 65535 &&
            longword(ram, 0x7f34) == 0xfedcffc0U &&
            longword(ram, 0x7f38) == 0xabcdef07U &&
            longword(ram, 0x7f3c) == (0x00123456U | (703U << 23)),
            "normal record implements unsigned fixed-width packing");

    // Deferred final storage slot uses offset 3060, preserving normal cursor.
    ram = initialized(); put(ram, 0x8b36, 3060); put(ram, 0x914e, 510);
    const std::vector<std::uint8_t> before = ram;
    expected = ram;
    put(expected, 0x8d3a, 2); put(expected, 0x914e, 512);
    put(expected, 0x8f4e + 510, 3060);
    put(expected, 0x7f34 + 3060, 0xbeef);
    put(expected, 0x7f36 + 3060, 0xa800);
    // d1 mask clears all low-byte bits except bits 0..2.
    expected[0x7f38 + 3060] = 0x12; expected[0x7f39 + 3060] = 0x34;
    expected[0x7f3a + 3060] = 0x56; expected[0x7f3b + 3060] = 0x07;
    expected[0x7f3c + 3060] = 0x20; expected[0x7f3d + 3060] = 0;
    expected[0x7f3e + 3060] = 0; expected[0x7f3f + 3060] = 1;
    require(ms5::submit_sprite(ram, 0xfea00040U, 0x123456ffU,
                              0xdeadbeefU, 1, status, error) &&
            error.empty() && status == ms5::SpriteAccepted && ram == expected,
            "deferred submission modifies exactly expected bytes");
    require(word(ram, 0x8d38) == word(before, 0x8d38),
            "deferred submission preserves normal cursor");
    std::cout << "Sprite producer validation and memory tests passed\n";
    return 0;
}
