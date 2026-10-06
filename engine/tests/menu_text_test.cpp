#include "ms5/menu_text.h"
#include <cassert>
#include <iostream>

static void put(std::vector<std::uint8_t>& data, unsigned int at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) data[at + i] = static_cast<std::uint8_t>(value >> (24 - i * 8));
}
int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    put(ram, 0x7f0e, 0x107efe);
    put(ram, 0x7f12, 0x107efe);
    put(ram, 0x7f16, 0x3650);
    put(ram, 0x7efe, 0x200);
    ram[0x7f02] = 3;
    ram[0x7f04] = 1;
    ram[0x7f06] = 255;
    ram[0x7f09] = 10;
    ms5::FixedDataResource data;
    data.source_cpu_address = data.source_rom_offset = 0x200;
    data.data.assign(32, 0);
    put(data.data, 0, 0x21e);
    put(data.data, 16, 0x21e);
    put(data.data, 26, 0xffffffffU);
    data.data[30] = 'A';
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    assert(ms5::draw_menu_text(ram, data, true, 0x7000, writes, error));
    assert(ram[0x7f06] == 0 && writes.size() == 6);
    const std::vector<std::uint8_t> before = ram;
    const std::uint32_t first = writes[0].value;
    put(data.data, 20, 0x1234);
    assert(!ms5::draw_menu_text(ram, data, true, 0x7000, writes, error));
    assert(ram == before && writes.size() == 6 && writes[0].value == first);
    put(data.data, 20, 0);
    data.data[15] = 2;
    assert(!ms5::draw_menu_text(ram, data, true, 0x7000, writes, error));
    assert(ram == before && writes.size() == 6);
    ram[0x7f02] = 0;
    assert(ms5::draw_menu_text(ram, ms5::FixedDataResource(), true, 0x7000, writes, error));
    assert(writes.empty());
    std::cout << "Menu text unsupported paths and rollback passed\n";
}
