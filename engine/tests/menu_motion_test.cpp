#include "ms5/menu_motion.h"
#include <cassert>
#include <iostream>

static void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (24 - i * 8));
}
int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    put(ram, 0x7f0e, 0x107efe);
    put(ram, 0x7f12, 0x107efe);
    ram[0x7f02] = 2;
    ram[0x7f04] = 1;
    ram[0x7f09] = 1;
    ram[0x7f0a] = 8;
    const std::vector<std::uint8_t> before = ram;
    ms5::FixedDataResource invalid;
    std::vector<ms5::FixedWrite> writes(1);
    writes[0].address = 123;
    writes[0].value = 456;
    std::string error;
    assert(!ms5::open_menu_step(ram, invalid, writes, error));
    assert(ram == before && writes.size() == 1 && writes[0].value == 456);
    assert(!ms5::close_menu_step(ram, invalid, writes, error));
    assert(ram == before && writes.size() == 1 && writes[0].address == 123);
    ram[0x7f02] = 0;
    assert(ms5::open_menu_step(ram, invalid, writes, error));
    assert(writes.empty() && ram[0x7f02] == 2 && ram[0x7f03] == 0);
    ram[0x7f04] = 255;
    assert(ms5::close_menu_step(ram, invalid, writes, error));
    assert(ram[0x7f02] == 0 && ram[0x7f03] == 0 && writes.size() == 2);
    bool covered = true;
    ram.resize(3);
    assert(!ms5::menu_position_occluded(ram, 0x7000, covered, error));
    assert(covered);
    std::cout << "Menu motion transaction and zero-height resource bypass passed\n";
}
