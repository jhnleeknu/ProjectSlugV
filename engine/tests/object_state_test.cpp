#include "ms5/object_state.h"

#include <cstdlib>
#include <iostream>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

std::uint8_t expected_byte(std::size_t offset, std::uint8_t original) {
    if (offset == 0x12 || offset == 0x13 || offset == 0x17 ||
        offset == 0x1e || offset == 0x1f || offset == 0x5a ||
        offset == 0x5b || offset == 0x6b || offset == 0x6c || offset == 0x6d) {
        return 0xff;
    }
    if (offset == 0x6f) {
        return 0x40;
    }
    if (offset == 0x15 || offset == 0x1d ||
        (offset >= 0x2e && offset < 0x5a) || offset == 0x5e ||
        (offset >= 0x60 && offset < 0x68) || offset == 0x6a ||
        offset == 0x6e || (offset >= 0x72 && offset < 0xc4)) {
        return 0;
    }
    return original;
}

} // namespace

int main() {
    // Unaligned object, prefix guard, and trailing bytes exercise byte access
    // and preservation beyond the minimum object extent.
    for (unsigned int seed = 0; seed < 256; ++seed) {
        std::vector<std::uint8_t> bytes(1 + 0xc4 + 17);
        for (std::size_t i = 0; i < bytes.size(); ++i) {
            bytes[i] = static_cast<std::uint8_t>((i * 73 + seed) & 0xffU);
        }
        const std::vector<std::uint8_t> before = bytes;
        const std::size_t supplied_size = seed % 2 == 0 ? 0xc4 : bytes.size() - 1;
        require(ms5::reset_object_fields(&bytes[1], supplied_size), "valid reset");
        require(bytes[0] == before[0], "prefix guard preserved");
        for (std::size_t offset = 0; offset < bytes.size() - 1; ++offset) {
            if (bytes[offset + 1] != expected_byte(offset, before[offset + 1])) {
                std::cerr << "FAIL: byte at object offset " << offset
                          << " with seed " << seed << '\n';
                return 1;
            }
        }
        const std::vector<std::uint8_t> reset = bytes;
        require(ms5::reset_object_fields(&bytes[1], supplied_size), "repeat reset");
        require(bytes == reset, "reset is idempotent");
    }
    std::vector<std::uint8_t> bytes(0xc4 + 16, 0xa5);
    const std::vector<std::uint8_t> before = bytes;
    for (std::size_t size = 0; size < 0xc4; ++size) {
        require(!ms5::reset_object_fields(&bytes[0], size), "short input rejected");
        require(bytes == before, "short input causes no writes");
        require(!ms5::reset_object_fields(NULL, size), "null short input rejected");
    }
    require(!ms5::reset_object_fields(NULL, 0xc4), "null valid size rejected");
    require(!ms5::reset_object_fields(NULL, static_cast<std::size_t>(-1)),
            "null maximum size rejected");
    std::cout << "object_state_test: passed\n";
    return 0;
}
