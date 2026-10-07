#include "ms5/control_request.h"

namespace ms5 {
namespace {

std::uint8_t read_input_bits(const std::vector<std::uint8_t>& ram) {
    std::uint8_t value = 0;
    if ((ram[0x4cb9] & 0x80u) != 0) {
        value = static_cast<std::uint8_t>(value | 0x02u);
    }
    if ((ram[0x4cbf] & 0x80u) != 0) {
        value = static_cast<std::uint8_t>(value | 0x08u);
    }
    return value;
}

} // namespace

bool read_control_request(const std::vector<std::uint8_t>& ram,
                          std::uint8_t& result, std::string& error, std::uint32_t* d1) {
    if (ram.size() != 65536u) {
        error = "RAM image must contain exactly 65536 bytes";
        return false;
    }
    std::uint8_t value = 0;
    if (ram[0x0012] == 2) {
        if (ram[0xfd82] == 0) {
            value = ram[0x4cb5];
        } else if (ram[0xf002] != 0) {
            value = static_cast<std::uint8_t>(
                read_input_bits(ram) & ram[0x4cb4] & 0x0au);
        }
        if (ram[0xfdb6] == 0 || ram[0xfdb6] == 3) {
            value = static_cast<std::uint8_t>(value & 0xfdu);
        }
        if (ram[0xfdb7] == 0 || ram[0xfdb7] == 3) {
            value = static_cast<std::uint8_t>(value & 0xf7u);
        }
    } else if (ram[0xf002] != 0) {
        value = read_input_bits(ram);
    }
    if (d1 != NULL && ram[0x12] == 2 && ram[0xfd82] != 0 && ram[0xf002] != 0) {
        *d1 = (*d1 & 0xffffff00U) | (ram[0x4cb4] & 10U);
    }
    result = value;
    error.clear();
    return true;
}

} // namespace ms5
