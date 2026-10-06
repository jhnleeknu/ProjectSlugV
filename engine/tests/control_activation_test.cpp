#include "ms5/control_activation.h"
#include <cassert>
#include <iostream>

namespace {

std::vector<std::uint8_t> inactive_ram() {
    std::vector<std::uint8_t> ram(65536, 0xa5);
    ram[0x7df0] = ram[0x7df1] = 0;
    ram[0x12] = 2;
    ram[0xfd82] = 0;
    ram[0xfdb6] = ram[0xfdb7] = 1;
    ram[0x4caa] = 0x56;
    ram[0x4cb0] = 0x78;
    return ram;
}

void verify(std::vector<std::uint8_t> ram, std::uint8_t selected) {
    std::vector<std::uint8_t> expected = ram;
    if (selected != 0) {
        expected[0x7df0] = selected;
        expected[0x7df1] = 0;
        expected[0x7df3] = 0xff;
        for (unsigned int offset = 0x7df6; offset < 0x7dfa; ++offset) {
            expected[offset] = 0;
        }
        expected[0x4cd2] = 0x10;
        expected[0x4cd3] = 2;
        expected[0x7dfc] = ram[0x4caa];
        expected[0x7dfd] = ram[0x4cb0];
    }
    std::uint8_t status = 0xa5;
    std::string error = "old error";
    assert(ms5::activate_control(ram, status, error));
    assert(error.empty());
    assert(status == (selected == 0 ? 1 : 0));
    assert(ram == expected);
}

} // namespace

int main() {
    // Every pending byte is copied verbatim, even when the gate is closed.
    for (unsigned int pending = 1; pending < 256; ++pending) {
        std::vector<std::uint8_t> ram = inactive_ram();
        ram[0x7df1] = static_cast<std::uint8_t>(pending);
        ram[0xf000] = 0;
        ram[0x7def] = 255;
        ram[0x4cb5] = 10;
        verify(ram, static_cast<std::uint8_t>(pending));
    }
    // Both request bits select 1. Gate and selector filters remain effective.
    for (unsigned int gate = 0; gate < 4; ++gate) {
        for (unsigned int request = 0; request < 256; ++request) {
            std::vector<std::uint8_t> ram = inactive_ram();
            ram[0xf000] = (gate & 1u) != 0 ? 2 : 0;
            ram[0x7def] = (gate & 2u) != 0 ? 0 : 255;
            ram[0x4cb5] = static_cast<std::uint8_t>(request);
            const std::uint8_t selected = gate == 0 ? 0 :
                (request & 2u) != 0 ? 1 : (request & 8u) != 0 ? 2 : 0;
            verify(ram, selected);
        }
    }
    std::vector<std::uint8_t> ram = inactive_ram();
    ram[0x7def] = 0;
    ram[0x4cb5] = 10;
    ram[0xfdb6] = 3;
    verify(ram, 2);
    ram[0xfdb7] = 0;
    verify(ram, 0);
    // The activation API must reject every active byte before any write.
    std::string error;
    std::uint8_t status = 0x42;
    for (unsigned int active = 1; active < 256; ++active) {
        ram = inactive_ram();
        ram[0x7df0] = static_cast<std::uint8_t>(active);
        ram[0x7df1] = 7;
        const std::vector<std::uint8_t> before = ram;
        assert(!ms5::activate_control(ram, status, error));
        assert(ram == before && status == 0x42 && !error.empty());
    }
    const unsigned int sizes[] = {0, 1, 65535, 65537};
    for (unsigned int index = 0; index < 4; ++index) {
        ram.assign(sizes[index], 0x5a);
        const std::vector<std::uint8_t> before = ram;
        assert(!ms5::activate_control(ram, status, error));
        assert(ram == before && status == 0x42 && !error.empty());
    }
    std::cout << "Control activation requests, pending bytes, idle and failure preservation passed\n";
}
