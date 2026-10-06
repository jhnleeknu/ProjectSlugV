#ifndef MS5_FIXED_TEXT_H
#define MS5_FIXED_TEXT_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

struct FixedWrite {
    std::uint16_t address;
    std::uint16_t value;
};

// Confirmed ASCII/font-0x61 subset of the text stream at CPU 0x00386e,
// 0x003918 and 0x0e84c8. This is not a general text engine. Addresses are
// VRAM word addresses, not CPU addresses or ROM offsets. Other font paths
// and glyphs >= 0x80 are unsupported. A successful trace replaces writes;
// on failure writes is unchanged. Bytes after the first terminator are ignored.
bool trace_fixed_text(const std::vector<std::uint8_t>& script,
                      std::uint16_t initial_address,
                      std::uint16_t initial_style,
                      std::vector<FixedWrite>& writes,
                      std::string& error);

} // namespace ms5

#endif
