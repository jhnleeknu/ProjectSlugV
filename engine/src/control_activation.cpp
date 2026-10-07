#include "ms5/control_activation.h"
#include "ms5/control_request.h"

namespace ms5 {

bool activate_control(std::vector<std::uint8_t>& ram,
                      std::uint8_t& status, std::string& error, std::uint32_t* d1) {
    if (ram.size() != 65536u) {
        error = "RAM image must contain exactly 65536 bytes";
        return false;
    }
    if (ram[0x7df0] != 0) {
        error = "active control state is not supported";
        return false;
    }
    std::uint8_t selected = ram[0x7df1];
    if (selected == 0 && ((ram[0xf000] & 2u) != 0 || ram[0x7def] == 0)) {
        std::uint8_t request = 0;
        if (!read_control_request(ram, request, error, d1)) {
            return false;
        }
        if ((request & 2u) != 0) {
            selected = 1;
        } else if ((request & 8u) != 0) {
            selected = 2;
        }
    }
    if (selected == 0) {
        status = 1;
        error.clear();
        return true;
    }
    ram[0x7df0] = selected;
    ram[0x7df1] = 0;
    for (unsigned int offset = 0x7df6; offset < 0x7dfa; ++offset) {
        ram[offset] = 0;
    }
    // 313c writes the big-endian word 0x1002; 92a8 decrements 7df3 from 0.
    ram[0x4cd2] = 0x10;
    ram[0x4cd3] = 0x02;
    ram[0x7df3] = 0xff;
    ram[0x7dfc] = ram[0x4caa];
    ram[0x7dfd] = ram[0x4cb0];
    // The common tail compares the saved input with these same current
    // bytes, so no newly pressed bits are added to the accumulators.
    status = 0;
    error.clear();
    return true;
}

} // namespace ms5
