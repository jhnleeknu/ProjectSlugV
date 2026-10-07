#include "ms5/palette_allocator.h"
#include "ms5/palette_state.h"
#include <cstdlib>
#include <iostream>

void check(bool value) {
    if (!value) { std::cerr << "palette allocator test failed\n"; std::exit(1); }
}

int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    std::string error;
    check(ms5::initialize_palette_state(&ram[0], ram.size(), error));
    bool allocated = false;
    check(ms5::acquire_palette(ram, 0x2000, 7, 0, allocated, error) && allocated);
    check(ms5::acquire_palette(ram, 0x2100, 7, 0, allocated, error) && allocated);
    check(ram[0x2019] == ram[0x2119] && ram[0x4d9b] == 2);
    ram[0x201d] = 4;
    const std::vector<std::uint8_t> full_object = ram;
    check(!ms5::acquire_palette(ram, 0x2000, 7, 0, allocated, error));
    check(ram == full_object && allocated);
    ram[0x201d] = 1;
    // A malformed next link encountered during bucket search must roll back.
    ram[0x4d94] = 0x12; ram[0x4d95] = 0x34;
    const std::vector<std::uint8_t> corrupt = ram;
    check(!ms5::acquire_palette(ram, 0x2200, 263, 0, allocated, error));
    check(ram == corrupt && allocated);
    // Release decrements a count before inspecting links: failure still rolls back.
    ram[0x4d9a] = 0; ram[0x4d9b] = 1;
    const std::vector<std::uint8_t> release_bad = ram;
    std::uint32_t d3=0xabcd1234U;
    check(!ms5::release_palettes(ram, 0x2000, error, &d3) && ram == release_bad);
    check(d3==0xabcd1234U);
    ram.assign(65536, 0);
    check(ms5::initialize_palette_state(&ram[0], ram.size(), error));
    // Releasing no palettes leaves the full incoming D3 intact.
    const std::vector<std::uint8_t> empty_release=ram;
    check(ms5::release_palettes(ram, 0x2000, error, &d3));
    check(ram==empty_release && d3==0xabcd1234U);
    {
        std::vector<std::uint8_t> released(65536,0);
        check(ms5::initialize_palette_state(&released[0],released.size(),error));
        check(ms5::acquire_palette(released,0x2000,7,0,allocated,error) && allocated);
        const std::uint16_t old_tail=static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(released[0x5d92])<<8)|released[0x5d93]);
        d3=0xabcd1234U;
        check(ms5::release_palettes(released,0x2000,error,&d3));
        check(d3==(0xabcd0000U|old_tail) && released[0x201d]==0);
    }
    // Empty free ring with enabled original diagnostic display is unsupported.
    ram[0x5d92] = 0x10; ram[0x5d93] = 0;
    ram[0x5d94] = 0x10; ram[0x5d95] = 0;
    ram[0xf000] = 4;
    const std::vector<std::uint8_t> diagnostic = ram;
    check(!ms5::acquire_palette(ram, 0x2000, 0, 1, allocated, error));
    check(ram == diagnostic && allocated);
    ram[0xf000] = 0;
    check(ms5::acquire_palette(ram, 0x2000, 0, 1, allocated, error) && !allocated);
    check(ram[0x2014] == 255 && ram[0x201d] == 0);
    std::cout << "palette_allocator_test: passed\n";
}
