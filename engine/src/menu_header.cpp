#include "ms5/menu_header.h"
#include "ms5/control_request.h"

namespace ms5 {

bool update_menu_header(std::vector<std::uint8_t>& ram,
                        std::uint32_t& a2, std::string& error) {
    std::uint8_t request = 0;
    if (!read_control_request(ram, request, error)) {
        return false;
    }
    if (((ram[0x7df0] & 1u) != 0 && (request & 2u) != 0) ||
        ((ram[0x7df0] & 2u) != 0 && (request & 8u) != 0)) {
        ram[0x7dfa] = 0;
        ram[0x7dfb] = 1;
        ram[0x7f1b] = 2;
        a2 = (static_cast<std::uint32_t>(ram[0x7f0e]) << 24) |
             (static_cast<std::uint32_t>(ram[0x7f0f]) << 16) |
             (static_cast<std::uint32_t>(ram[0x7f10]) << 8) |
             static_cast<std::uint32_t>(ram[0x7f11]);
    }
    error.clear();
    return true;
}

} // namespace ms5
