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
    std::uint16_t final_line = 0xffff;
    assert(ms5::draw_menu_text(ram, data, true, 0x7000, writes, error, &final_line));
    assert(final_line == 0x7061);
    const std::vector<std::uint8_t> before = ram;
    const std::uint32_t first = writes[0].value;
    put(data.data, 20, 0x1234);
    final_line = 0x1234;
    assert(!ms5::draw_menu_text(ram, data, true, 0x7000, writes, error, &final_line));
    assert(final_line == 0x1234);
    assert(ram == before && writes.size() == 6 && writes[0].value == first);
    put(data.data, 20, 0);
    data.data[15] = 2;
    assert(!ms5::draw_menu_text(ram, data, true, 0x7000, writes, error, &final_line));
    assert(final_line == 0x1234);
    assert(ram == before && writes.size() == 6);
    ram[0x7f02] = 0;
    assert(ms5::draw_menu_text(ram, ms5::FixedDataResource(), true, 0x7000, writes, error));
    assert(writes.empty());
    data.data[15] = 0;
    put(data.data, 16, 0xfffffffeU);
    ram[0x7f02] = 3;
    ram[0x7f06] = 0;
    const unsigned int widths[] = {0, 1, 2, 3, 4, 255};
    const unsigned int counts[] = {0, 0, 256, 1, 2, 253};
    for (unsigned int i = 0; i < 6; ++i) {
        ram[0x7f09] = static_cast<std::uint8_t>(widths[i]);
        final_line = 0x1234;
        assert(ms5::draw_menu_item(ram, data, false, writes, error, NULL, NULL, &final_line));
        assert(writes.size() == counts[i] && final_line == 0x1234);
        if (!writes.empty()) {
            assert(writes.front().size == 4 && writes.front().value == 0x70210bf8U);
            if (writes.size() > 1) {
                assert((writes.back().value & 65535U) == 0x0bfaU);
            }
        }
    }
    // Occlusion applies even when clip=false; a covered first cell keeps
    // the cursor stationary, so all remaining separator cells stay covered.
    put(ram, 0x7f0e, 0x107eee);
    ram[0x7ef2] = 1;ram[0x7ef7] = 1;ram[0x7ef8] = 1;ram[0x7ef9] = 1;
    ram[0x7efd] = 0;
    assert(ms5::draw_menu_item(ram, data, false, writes, error, NULL, NULL, &final_line));
    assert(writes.empty() && final_line == 0x1234);
    std::cout << "Menu text unsupported paths and rollback passed\n";
}
