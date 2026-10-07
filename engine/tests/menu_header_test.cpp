#include "ms5/menu_header.h"
#include <cassert>
#include <iostream>

int main() {
    std::vector<std::uint8_t> ram(65536, 0xa5);
    ram[0x12] = 2;
    ram[0xfd82] = 0;
    ram[0xfdb6] = ram[0xfdb7] = 1;
    ram[0x7f0e] = 0xff;
    ram[0x7f0f] = 0xff;
    ram[0x7f10] = 0xff;
    ram[0x7f11] = 0xff;
    std::string error = "old error";
    for (unsigned int enabled = 0; enabled < 4; ++enabled) {
        for (unsigned int request = 0; request < 16; ++request) {
            ram[0x7df0] = static_cast<std::uint8_t>(enabled | 0xfcu);
            ram[0x4cb5] = static_cast<std::uint8_t>(request | 0xf0u);
            ram[0x7dfa] = 0x12;
            ram[0x7dfb] = 0x34;
            ram[0x7f1b] = 0xfe;
            const std::vector<std::uint8_t> before = ram;
            std::vector<std::uint8_t> expected = ram;
            const bool selected = ((enabled & 1u) && (request & 2u)) ||
                                  ((enabled & 2u) && (request & 8u));
            if (selected) {
                expected[0x7dfa] = 0;
                expected[0x7dfb] = 1;
                expected[0x7f1b] = 2;
            }
            std::uint32_t a2 = 0x12345678u;
            assert(ms5::update_menu_header(ram, a2, error));
            assert(error.empty() && ram == expected);
            assert(a2 == (selected ? 0xffffffffu : 0x12345678u));
            ram = before;
        }
    }
    // Selector filters each source independently before testing enable bits.
    ram[0x7df0] = 3;
    ram[0x4cb5] = 10;
    ram[0xfdb6] = 0;
    ram[0xfdb7] = 3;
    std::vector<std::uint8_t> before = ram;
    std::uint32_t a2 = 0xdeadbeefu;
    assert(ms5::update_menu_header(ram, a2, error));
    assert(ram == before && a2 == 0xdeadbeefu);
    ram[0xfd82]=ram[0xf002]=1;ram[0x4cb4]=255;
    std::uint32_t d1=0xabcdef12U;
    assert(ms5::update_menu_header(ram,a2,error,&d1));
    assert(d1==0xabcdef0aU && a2==0xdeadbeefU);
    const unsigned int sizes[] = {0, 1, 65535, 65537};
    for (unsigned int i = 0; i < 4; ++i) {
        ram.assign(sizes[i], 0x5a);
        before = ram;
        assert(!ms5::update_menu_header(ram, a2, error,&d1));
        assert(d1==0xabcdef0aU);
        assert(ram == before && a2 == 0xdeadbeefu && !error.empty());
    }
    std::cout << "Menu header enable/request mapping and failure preservation passed\n";
}
