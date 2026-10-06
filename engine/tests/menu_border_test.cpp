#include "ms5/menu_border.h"
#include <cassert>
#include <iostream>

static void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) ram[at + i] = static_cast<std::uint8_t>(value >> (24 - i * 8));
}
int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    ms5::FixedDataResource resource;
    std::vector<ms5::FixedWrite> writes(1);
    writes[0].address = 123;
    writes[0].value = 456;
    std::string error;
    assert(!ms5::trace_menu_border(ram, resource, writes, error));
    assert(writes.size() == 1 && writes[0].address == 123 && writes[0].value == 456);
    put(ram, 0x7f0e, 0x107efe);
    put(ram, 0x7f12, 0x107efe);
    assert(ms5::trace_menu_border(ram, resource, writes, error));
    assert(writes.empty()); // zero height does not resolve descriptor.
    ram[0x7f02] = 1;
    assert(!ms5::trace_menu_border(ram, resource, writes, error));
    resource.source_cpu_address = resource.source_rom_offset = 0x200;
    resource.data.assign(20, 0);
    for (unsigned int i = 16; i < 20; ++i) resource.data[i] = 255;
    put(ram, 0x7efe, 0x200);
    ram[0x7f09] = 1;
    const std::vector<std::uint8_t> before = ram;
    assert(ms5::trace_menu_border(ram, resource, writes, error));
    assert(ram == before && writes.size() == 4);
    assert(writes[0].address == 0x7000 && writes[0].value == 0x0bf4);
    resource.data[15] = 1;
    assert(ms5::trace_menu_border(ram, resource, writes, error));
    assert(writes.size() == 1 && writes[0].value == 255);
    put(ram, 0x7f0e, 0x107eff);
    assert(!ms5::trace_menu_border(ram, resource, writes, error));
    assert(writes.size() == 1 && writes[0].value == 255);
    std::cout << "Menu border validation and output preservation passed\n";
}
