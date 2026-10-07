#include "ms5/menu_navigation.h"
#include "ms5/menu_text.h"
#include <cassert>
#include <iostream>

static void put(std::vector<std::uint8_t>& data, unsigned int at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) data[at+i] = static_cast<std::uint8_t>(value >> (24-i*8));
}
static void unchanged_failure(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& data) {
    const std::vector<std::uint8_t> before = ram;
    std::vector<ms5::VideoPortWrite> writes(1);
    writes[0].value = 0xabcdefU;
    std::string error;
    std::uint16_t line = 0x7088U;
    std::uint32_t d1 = 0xabcdef68U, d3 = 0x12347088U;
    assert(!ms5::navigate_menu(ram, data, false, 0, writes, error, NULL, NULL, &line, &d1, &d3));
    assert(line == 0x7088U && d1 == 0xabcdef68U && d3 == 0x12347088U);
    assert(!error.empty() && ram == before && writes.size() == 1 && writes[0].value == 0xabcdefU);
}
int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    put(ram, 0x7f0e, 0x107efe);
    put(ram, 0x7f12, 0x107efe);
    put(ram, 0x7f16, 0x3650);
    put(ram, 0x7efe, 0x200);
    ram[0x7f02] = 8;
    ram[0x7f04] = 2;
    ram[0x7f0c] = 0xff;
    ms5::FixedDataResource data;
    data.source_cpu_address = data.source_rom_offset = 0x200;
    data.data.assign(40, 0);
    put(data.data, 20, 0x9488);
    put(data.data, 30, 0x949a);
    put(data.data, 36, 0xffffffffU);
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    assert(ms5::navigate_menu(ram, data, false, 0, writes, error));
    assert(ram[0x7f05] == 1 && ram[0x7f06] == 1 && ram[0x7f0c] == 0 && writes.size() == 4);
    // Both invisible redraws carry the D1 byte update across navigation.
    std::uint16_t line = 0x7088U;
    std::uint32_t d1 = 0x1234ab68U, d3 = 0x56787088U;
    ram[0x7f02] = 0;
    assert(ms5::navigate_menu(ram, data, false, 0, writes, error, NULL, NULL,
                              &line, &d1, &d3));
    assert(ram[0x7f05] == 0 && writes.empty());
    assert(d1 == 0x1234ab01U && d3 == 0x56787088U && line == 0x7088U);
    ram[0x7f02] = 8;
    assert(ms5::navigate_menu(ram, data, false, 0, writes, error, NULL, NULL,
                              &line, &d1, &d3));
    assert(d1 == 0 && (d3 & 0xffff0000U) == 0x56780000U);
    assert(line == static_cast<std::uint16_t>(d3));
    const std::vector<std::uint8_t> before_mismatch = ram;
    line ^= 1U;
    const std::uint16_t mismatched_line = line;
    const std::uint32_t before_d1 = d1, before_d3 = d3;
    assert(!ms5::navigate_menu(ram, data, false, 0, writes, error, NULL, NULL,
                               &line, &d1, &d3));
    assert(ram == before_mismatch && line == mismatched_line &&
           d1 == before_d1 && d3 == before_d3);
    // A late new-row failure must also roll back the already-drawn old row.
    put(data.data, 16, 0x300);
    unchanged_failure(ram, data);
    put(data.data, 16, 0);
    put(data.data, 20, 0);
    put(data.data, 30, 0);
    unchanged_failure(ram, data); // Original infinite search, bounded rejection.
    put(data.data, 20, 0x1234);
    unchanged_failure(ram, data); // Unknown event-5 callback.
    ram[0x7f04] = 0;
    unchanged_failure(ram, data);
    ram[0x7f04] = 3;
    unchanged_failure(ram, data);
    ram[0x7f04] = 2;
    ram[0x7f05] = 2;
    unchanged_failure(ram, data);
    ram.resize(5);
    unchanged_failure(ram, data);
    // Single-row early return does not dereference an invisible item.
    ram.assign(65536, 0);
    put(ram, 0x7f0e, 0x107efe);
    put(ram, 0x7f12, 0x107efe);
    ram[0x7f06] = 0;
    assert(ms5::draw_menu_item(ram, ms5::FixedDataResource(), true, writes, error));
    assert(writes.empty());
    line = 0x7088U; d1 = 0x1234ab68U; d3 = 0x56787088U;
    ram[0x7f06] = 0x7aU;
    assert(ms5::draw_menu_item(ram, ms5::FixedDataResource(), true, writes, error,
                               NULL, NULL, &line, &d1, &d3));
    assert(d1 == 0x1234ab7bU && d3 == 0x56787088U && line == 0x7088U);
    std::cout << "Menu navigation errors preserve RAM and staged writes\n";
}
